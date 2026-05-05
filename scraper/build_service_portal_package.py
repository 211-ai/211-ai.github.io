from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import quote_plus

import duckdb
import pandas as pd

from .utils import clean_text, setup_logging


logger = setup_logging()

DEFAULT_PACKAGE_DIR = Path("data/retrieval_package")
DEFAULT_OUTPUT_DIR = Path("data/portal")
DEFAULT_WAREHOUSE_PATH = Path("data/live/state/etl_warehouse.duckdb")

EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_RE = re.compile(
    r"(?:(?:\+?1[\s.\-]*)?(?:\(\d{3}\)|\d{3})[\s.\-]*)\d{3}[\s.\-]*\d{4}(?:\s*(?:x|ext\.?)\s*\d+)?",
    re.IGNORECASE,
)
ADDRESS_RE = re.compile(
    r"\b\d{1,6}\s+[A-Za-z0-9 .#'/:-]{3,140}?\s+[A-Za-z .'-]+,\s*(?:[A-Z]{2})\s+\d{5}(?:-\d{4})?\b"
)
SERVICE_LABEL_PATTERN = re.compile(
    r"(?P<label>"
    r"OTHER SERVICES OFFERED AT THIS LOCATION|TRAVEL/LOCATION INFORMATION|INTAKE PROCEDURE|PHONE/FAX NUMBERS|EMAIL ADDRESS|SITE HOURS|AREA SERVED|ACCESSIBILITY|LANGUAGES|DOCUMENTS|ELIGIBILITY|SERVICES|HOURS|FEES"
    r")\s*:",
    re.IGNORECASE,
)

LABEL_TO_FIELD = {
    "ELIGIBILITY": "eligibility",
    "HOURS": "hours",
    "SITE HOURS": "hours",
    "INTAKE PROCEDURE": "intake_steps",
    "FEES": "fees",
    "DOCUMENTS": "required_documents",
    "LANGUAGES": "languages",
    "ACCESSIBILITY": "accessibility",
    "TRAVEL/LOCATION INFORMATION": "travel_info",
    "AREA SERVED": "area_served",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def bootstrap_local_ipfs_datasets() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    local_ipfs = repo_root / "ipfs_datasets_py"
    if local_ipfs.exists() and str(local_ipfs) not in sys.path:
        sys.path.insert(0, str(local_ipfs))


def cid_for_bytes(data: bytes) -> str:
    try:
        bootstrap_local_ipfs_datasets()
        from ipfs_datasets_py.utils.cid_utils import cid_for_bytes as inner_cid_for_bytes

        return str(inner_cid_for_bytes(data))
    except Exception:
        return f"sha256:{hashlib.sha256(data).hexdigest()}"


def cid_for_obj(payload: Any) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    try:
        bootstrap_local_ipfs_datasets()
        from ipfs_datasets_py.utils.cid_utils import cid_for_obj as inner_cid_for_obj

        return str(inner_cid_for_obj(payload))
    except Exception:
        return cid_for_bytes(encoded)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def unique_nonempty(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        cleaned = clean_text(str(value or ""))
        lowered = cleaned.lower()
        if not cleaned or lowered in seen:
            continue
        seen.add(lowered)
        result.append(cleaned)
    return result


def normalize_phone(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    ext_match = re.search(r"(?:x|ext\.?)\s*(\d+)", value or "", re.IGNORECASE)
    ext = ext_match.group(1) if ext_match else ""
    return f"{digits}x{ext}" if ext else digits


def infer_confidence(method: str, value: str, *, has_span: bool) -> float:
    if not value:
        return 0.0
    if method == "service_metadata":
        return 0.99 if has_span else 0.95
    if method == "page_label":
        return 0.97 if has_span else 0.92
    if method == "page_regex":
        return 0.88 if has_span else 0.82
    return 0.7 if has_span else 0.55


def maps_urls(query: str) -> dict[str, str]:
    encoded = quote_plus(query)
    return {
        "maps_query": query,
        "apple_maps_url": f"https://maps.apple.com/?q={encoded}",
        "google_maps_url": f"https://www.google.com/maps/search/?api=1&query={encoded}",
        "geo_url": f"geo:0,0?q={encoded}",
    }


@dataclass
class SpanValue:
    value: str
    source_text: str
    span_start: int
    span_end: int
    source_field: str
    extraction_method: str
    confidence: float
    label: str = ""

    def as_provenance(
        self,
        *,
        source_url: str,
        source_content_cid: str,
        source_page_cid: str,
    ) -> dict[str, Any]:
        return {
            "value": self.value,
            "label": self.label,
            "source_text": self.source_text,
            "source_span_start": self.span_start,
            "source_span_end": self.span_end,
            "source_field": self.source_field,
            "source_url": source_url,
            "source_content_cid": source_content_cid,
            "source_page_cid": source_page_cid,
            "extraction_method": self.extraction_method,
            "confidence": self.confidence,
        }


def find_value_span(text: str, value: str) -> tuple[int, int]:
    if not text or not value:
        return -1, -1
    start = text.lower().find(value.lower())
    if start < 0:
        return -1, -1
    return start, start + len(value)


def parse_address_parts(address: str, fallback_city: str = "", fallback_state: str = "") -> dict[str, str]:
    cleaned = clean_text(address)
    if not cleaned:
        return {
            "address": "",
            "street": "",
            "city": clean_text(fallback_city),
            "state": clean_text(fallback_state),
            "postal_code": "",
        }
    match = re.match(
        r"^(?P<street_city>.+?),\s*(?P<state>[A-Z]{2})\s+(?P<zip>\d{5}(?:-\d{4})?)$",
        cleaned,
    )
    if match:
        street_city = clean_text(match.group("street_city"))
        city = clean_text(fallback_city)
        street = street_city
        street_suffix_matches = list(
            re.finditer(
                r"\b(?:Avenue|Ave|Street|St|Road|Rd|Drive|Dr|Boulevard|Blvd|Lane|Ln|Court|Ct|Place|Pl|Way|Highway|Hwy|Circle|Cir|Parkway|Pkwy|Terrace|Ter)\b\.?",
                street_city,
                re.IGNORECASE,
            )
        )
        if street_suffix_matches:
            suffix = street_suffix_matches[-1]
            street = clean_text(street_city[: suffix.end()])
            city = clean_text(street_city[suffix.end() :])
        elif " " in street_city:
            prefix, candidate_city = street_city.rsplit(" ", 1)
            if candidate_city and not any(char.isdigit() for char in candidate_city):
                street = clean_text(prefix)
                city = clean_text(candidate_city)
        return {
            "address": cleaned,
            "street": street,
            "city": city,
            "state": clean_text(match.group("state")),
            "postal_code": clean_text(match.group("zip")),
        }
    match = re.match(
        r"^(?P<street>.+?)\s+(?P<city>[A-Za-z .'-]+),\s*(?P<state>[A-Z]{2})\s+(?P<zip>\d{5}(?:-\d{4})?)$",
        cleaned,
    )
    if match:
        return {
            "address": cleaned,
            "street": clean_text(match.group("street")),
            "city": clean_text(match.group("city")),
            "state": clean_text(match.group("state")),
            "postal_code": clean_text(match.group("zip")),
        }
    zip_match = re.search(r"(?P<zip>\d{5}(?:-\d{4})?)$", cleaned)
    return {
        "address": cleaned,
        "street": cleaned,
        "city": clean_text(fallback_city),
        "state": clean_text(fallback_state),
        "postal_code": clean_text(zip_match.group("zip")) if zip_match else "",
    }


def labeled_sections(text: str) -> list[dict[str, Any]]:
    matches = list(SERVICE_LABEL_PATTERN.finditer(text or ""))
    sections: list[dict[str, Any]] = []
    for index, match in enumerate(matches):
        label = clean_text(match.group("label")).upper()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        raw_value = trim_section_value(
            LABEL_TO_FIELD.get(label, label.lower()),
            clean_text((text or "")[start:end]),
        )
        if not raw_value:
            continue
        sections.append(
            {
                "field": LABEL_TO_FIELD.get(label, label.lower()),
                "label": label,
                "value": raw_value,
                "span_start": start,
                "span_end": end,
                "source_text": (text or "")[start:end].strip(),
            }
        )
    return sections


def trim_section_value(field: str, value: str) -> str:
    trimmed = clean_text(value)
    terminators: list[str] = []
    if field in {"hours", "eligibility"}:
        terminators.extend(
            [
                " Email ",
                " Get Directions ",
                " Visit Website ",
                " Phone/FAX Numbers ",
                " Email Address ",
                " Other Services Offered At This Location ",
                " If you represent this agency ",
                " Services ",
            ]
        )
    elif field in {"fees", "required_documents", "languages", "accessibility", "travel_info", "area_served"}:
        terminators.extend(
            [
                " Get Directions ",
                " Visit Website ",
                " Phone/FAX Numbers ",
                " Email Address ",
                " Other Services Offered At This Location ",
                " If you represent this agency ",
                " Services ",
            ]
        )
    best = len(trimmed)
    lowered = f" {trimmed.lower()} "
    for terminator in terminators:
        position = lowered.find(terminator.lower())
        if position >= 0:
            best = min(best, position)
    return clean_text(trimmed[:best])


def section_values_by_field(text: str) -> dict[str, list[SpanValue]]:
    values: dict[str, list[SpanValue]] = {}
    for section in labeled_sections(text):
        span = SpanValue(
            value=section["value"],
            source_text=section["source_text"],
            span_start=int(section["span_start"]),
            span_end=int(section["span_end"]),
            source_field="page_text",
            extraction_method="page_label",
            confidence=infer_confidence("page_label", section["value"], has_span=True),
            label=str(section["label"]),
        )
        values.setdefault(str(section["field"]), []).append(span)
    return values


def extract_email_candidates(page_text: str, service_text: str, metadata_email: str) -> list[SpanValue]:
    results: list[SpanValue] = []
    for value, source_name, method in [
        (clean_text(metadata_email), "service_text", "service_metadata"),
    ]:
        if value:
            start, end = find_value_span(service_text, value)
            source_text = service_text[start:end] if start >= 0 else value
            results.append(
                SpanValue(
                    value=value,
                    source_text=source_text,
                    span_start=start,
                    span_end=end,
                    source_field=source_name,
                    extraction_method=method,
                    confidence=infer_confidence(method, value, has_span=start >= 0),
                    label="email",
                )
            )
    seen = {item.value.lower() for item in results}
    for match in EMAIL_RE.finditer(page_text or ""):
        value = clean_text(match.group(0))
        if not value or value.lower() in seen:
            continue
        seen.add(value.lower())
        results.append(
            SpanValue(
                value=value,
                source_text=match.group(0),
                span_start=match.start(),
                span_end=match.end(),
                source_field="page_text",
                extraction_method="page_regex",
                confidence=infer_confidence("page_regex", value, has_span=True),
                label="email",
            )
        )
    return results


def extract_phone_candidates(page_text: str, service_text: str, metadata_phone: str) -> list[SpanValue]:
    results: list[SpanValue] = []
    if clean_text(metadata_phone):
        value = clean_text(metadata_phone)
        start, end = find_value_span(service_text, value)
        source_text = service_text[start:end] if start >= 0 else value
        results.append(
            SpanValue(
                value=value,
                source_text=source_text,
                span_start=start,
                span_end=end,
                source_field="service_text",
                extraction_method="service_metadata",
                confidence=infer_confidence("service_metadata", value, has_span=start >= 0),
                label="main",
            )
        )
    seen = {normalize_phone(item.value) for item in results}
    for match in PHONE_RE.finditer(page_text or ""):
        value = clean_text(match.group(0))
        normalized = normalize_phone(value)
        if not value or not normalized or normalized in seen:
            continue
        seen.add(normalized)
        window = (page_text or "")[max(0, match.start() - 32) : min(len(page_text or ""), match.end() + 48)].lower()
        label = "intake" if "intake" in window else "fax" if "fax" in window else "main" if "main" in window else "phone"
        results.append(
            SpanValue(
                value=value,
                source_text=match.group(0),
                span_start=match.start(),
                span_end=match.end(),
                source_field="page_text",
                extraction_method="page_regex",
                confidence=infer_confidence("page_regex", value, has_span=True),
                label=label,
            )
        )
    return results


def extract_address_candidates(
    page_text: str,
    service_text: str,
    metadata_address: str,
    fallback_city: str,
    fallback_state: str,
) -> list[SpanValue]:
    results: list[SpanValue] = []
    value = clean_text(metadata_address)
    if value:
        start, end = find_value_span(service_text, value)
        source_text = service_text[start:end] if start >= 0 else value
        parsed = parse_address_parts(value, fallback_city=fallback_city, fallback_state=fallback_state)
        results.append(
            SpanValue(
                value=parsed["address"],
                source_text=source_text,
                span_start=start,
                span_end=end,
                source_field="service_text",
                extraction_method="service_metadata",
                confidence=infer_confidence("service_metadata", parsed["address"], has_span=start >= 0),
                label="service_address",
            )
        )
    seen = {item.value.lower() for item in results}
    for match in ADDRESS_RE.finditer(page_text or ""):
        value = clean_text(match.group(0))
        if not value or value.lower() in seen:
            continue
        seen.add(value.lower())
        results.append(
            SpanValue(
                value=value,
                source_text=match.group(0),
                span_start=match.start(),
                span_end=match.end(),
                source_field="page_text",
                extraction_method="page_regex",
                confidence=infer_confidence("page_regex", value, has_span=True),
                label="service_address",
            )
        )
    return results


def primary_span_value(
    values: list[SpanValue],
    *,
    page_values: list[SpanValue] | None = None,
    metadata_value: str = "",
    prefer_page_when_metadata_empty: bool = True,
) -> list[SpanValue]:
    if values:
        return values
    if page_values:
        return page_values
    if metadata_value and prefer_page_when_metadata_empty:
        return [
            SpanValue(
                value=clean_text(metadata_value),
                source_text=clean_text(metadata_value),
                span_start=-1,
                span_end=-1,
                source_field="service_metadata",
                extraction_method="service_metadata",
                confidence=infer_confidence("service_metadata", clean_text(metadata_value), has_span=False),
            )
        ]
    return []


def value_or_empty(items: list[SpanValue]) -> str:
    return items[0].value if items else ""


def load_updated_at_by_service_id(warehouse_path: Path) -> dict[str, str]:
    if not warehouse_path.exists():
        return {}
    con = duckdb.connect(str(warehouse_path), read_only=True)
    try:
        rows = con.execute(
            """
            SELECT id, MAX(processed_at) AS processed_at
            FROM canonical_processed_services
            GROUP BY id
            """
        ).fetchall()
    finally:
        con.close()
    result: dict[str, str] = {}
    for service_id, processed_at in rows:
        if service_id:
            result[str(service_id)] = processed_at.isoformat() if processed_at is not None else ""
    return result


def load_retrieval_documents(package_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    service_frame = pd.read_parquet(package_dir / "content" / "documents.parquet").fillna("")
    page_frame = service_frame[service_frame["doc_type"] == "page"].copy()
    service_frame = service_frame[service_frame["doc_type"] == "service"].copy()
    manifest_path = package_dir / "manifest" / "build_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    return service_frame, page_frame, manifest


def artifact_record(path: Path, *, row_count: int) -> dict[str, Any]:
    return {
        "path": path.name,
        "size_bytes": int(path.stat().st_size),
        "row_count": int(row_count),
        "cid": cid_for_bytes(path.read_bytes()),
        "sha256": sha256_file(path),
    }


def build_service_portal_package(
    *,
    package_dir: Path = DEFAULT_PACKAGE_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    warehouse_path: Path = DEFAULT_WAREHOUSE_PATH,
) -> dict[str, Any]:
    package_dir = package_dir.resolve()
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    service_docs, page_docs, retrieval_manifest = load_retrieval_documents(package_dir)
    page_lookup = {
        str(row["source_content_cid"]): row
        for row in page_docs.to_dict(orient="records")
        if str(row.get("source_content_cid") or "")
    }
    updated_at_by_service_id = load_updated_at_by_service_id(warehouse_path)

    portal_rows: list[dict[str, Any]] = []
    contact_rows: list[dict[str, Any]] = []
    location_rows: list[dict[str, Any]] = []
    hours_rows: list[dict[str, Any]] = []
    requirement_rows: list[dict[str, Any]] = []
    action_rows: list[dict[str, Any]] = []

    coverage = Counter()

    for row in service_docs.to_dict(orient="records"):
        metadata = json.loads(str(row.get("metadata_json") or "{}")) if str(row.get("metadata_json") or "").strip() else {}
        page_doc = page_lookup.get(str(row.get("source_page_cid") or ""), {})
        page_text = clean_text(str(page_doc.get("text") or ""))
        service_text = clean_text(str(row.get("text") or ""))
        doc_id = str(row.get("doc_id") or "")
        source_url = str(row.get("source_url") or "")
        source_content_cid = str(row.get("source_content_cid") or "")
        source_page_cid = str(row.get("source_page_cid") or "")
        title = clean_text(str(row.get("title") or ""))
        primary_service_id = doc_id.split(":", 1)[1] if ":" in doc_id else doc_id

        labeled_fields = section_values_by_field(page_text)
        phone_values = extract_phone_candidates(page_text, service_text, str(metadata.get("phone") or ""))
        email_values = extract_email_candidates(page_text, service_text, str(metadata.get("email") or ""))
        address_values = extract_address_candidates(
            page_text,
            service_text,
            str(metadata.get("address") or ""),
            fallback_city=str(metadata.get("city") or row.get("city") or ""),
            fallback_state=str(metadata.get("state") or row.get("state") or ""),
        )

        hours_values = primary_span_value(
            [],
            page_values=labeled_fields.get("hours", []),
            metadata_value=str(metadata.get("hours") or ""),
        )
        eligibility_values = primary_span_value(
            [],
            page_values=labeled_fields.get("eligibility", []),
            metadata_value=str(metadata.get("eligibility") or ""),
        )
        intake_values = primary_span_value(
            [],
            page_values=labeled_fields.get("intake_steps", []),
        )
        required_documents_values = primary_span_value(
            [],
            page_values=labeled_fields.get("required_documents", []),
        )
        fees_values = primary_span_value([], page_values=labeled_fields.get("fees", []))
        languages_values = primary_span_value(
            [],
            page_values=labeled_fields.get("languages", []),
            metadata_value=str(metadata.get("languages") or ""),
        )
        accessibility_values = primary_span_value(
            [],
            page_values=labeled_fields.get("accessibility", []),
            metadata_value=str(metadata.get("accessibility") or ""),
        )
        travel_values = primary_span_value([], page_values=labeled_fields.get("travel_info", []))
        area_served_values = primary_span_value([], page_values=labeled_fields.get("area_served", []))

        provider_name = clean_text(
            str(metadata.get("provider_name") or row.get("provider_name") or title)
        )
        program_name = clean_text(str(metadata.get("program_name") or row.get("program_name") or ""))
        description = clean_text(str(metadata.get("description") or ""))
        categories = unique_nonempty(
            re.split(r"[|,]", " | ".join(filter(None, [str(metadata.get("categories") or ""), str(row.get("categories") or "")])))
        )

        primary_address_value = value_or_empty(address_values)
        parsed_address = parse_address_parts(
            primary_address_value,
            fallback_city=str(metadata.get("city") or row.get("city") or ""),
            fallback_state=str(metadata.get("state") or row.get("state") or ""),
        )
        derived_city = parsed_address["city"] or clean_text(str(row.get("city") or metadata.get("city") or ""))
        derived_state = parsed_address["state"] or clean_text(str(row.get("state") or metadata.get("state") or ""))
        address_objects: list[dict[str, Any]] = []
        for index, item in enumerate(address_values):
            parts = parse_address_parts(
                item.value,
                fallback_city=derived_city,
                fallback_state=derived_state,
            )
            query = clean_text(" ".join(part for part in [parts["address"], parts["city"], parts["state"], parts["postal_code"]] if part))
            map_urls = maps_urls(query) if query else {
                "maps_query": "",
                "apple_maps_url": "",
                "google_maps_url": "",
                "geo_url": "",
            }
            address_objects.append(
                {
                    "location_id": f"{doc_id}:location:{index}",
                    **parts,
                    "label": item.label or "service_address",
                    "geo": {"lat": None, "lon": None, "precision": "address_query"},
                    **map_urls,
                    "confidence": item.confidence,
                }
            )
            location_rows.append(
                {
                    "service_doc_id": doc_id,
                    "location_id": f"{doc_id}:location:{index}",
                    "label": item.label or "service_address",
                    "address": parts["address"],
                    "street": parts["street"],
                    "city": parts["city"],
                    "state": parts["state"],
                    "postal_code": parts["postal_code"],
                    "source_url": source_url,
                    "source_content_cid": source_content_cid,
                    "source_page_cid": source_page_cid,
                    "source_text": item.source_text,
                    "source_span_start": int(item.span_start),
                    "source_span_end": int(item.span_end),
                    "source_field": item.source_field,
                    "extraction_method": item.extraction_method,
                    "confidence": float(item.confidence),
                    **map_urls,
                    "geo_json": compact_json({"lat": None, "lon": None, "precision": "address_query"}),
                }
            )
            if query:
                action_rows.append(
                    {
                        "service_doc_id": doc_id,
                        "action_id": f"{doc_id}:action:maps:{index}",
                        "action_type": "open_maps",
                        "label": "Get directions",
                        "channel": "maps",
                        "target": query,
                        "action_url": maps_urls(query)["google_maps_url"],
                        "related_contact_id": "",
                        "related_location_id": f"{doc_id}:location:{index}",
                        "source_url": source_url,
                        "source_content_cid": source_content_cid,
                        "source_page_cid": source_page_cid,
                        "confidence": float(item.confidence),
                    }
                )

        phone_objects: list[dict[str, Any]] = []
        for index, item in enumerate(phone_values):
            digits = normalize_phone(item.value).split("x", 1)[0]
            tel_url = f"tel:+1{digits}" if len(digits) == 10 else ""
            sms_url = f"sms:+1{digits}" if len(digits) == 10 else ""
            contact_id = f"{doc_id}:contact:phone:{index}"
            phone_objects.append(
                {
                    "contact_id": contact_id,
                    "type": "phone",
                    "label": item.label or "phone",
                    "value": item.value,
                    "tel_url": tel_url,
                    "sms_url": sms_url,
                    "confidence": item.confidence,
                }
            )
            contact_rows.append(
                {
                    "service_doc_id": doc_id,
                    "contact_id": contact_id,
                    "contact_type": "phone",
                    "label": item.label or "phone",
                    "value": item.value,
                    "action_url": tel_url,
                    "alternate_action_url": sms_url,
                    "source_url": source_url,
                    "source_content_cid": source_content_cid,
                    "source_page_cid": source_page_cid,
                    "source_text": item.source_text,
                    "source_span_start": int(item.span_start),
                    "source_span_end": int(item.span_end),
                    "source_field": item.source_field,
                    "extraction_method": item.extraction_method,
                    "confidence": float(item.confidence),
                }
            )
            if tel_url:
                action_rows.append(
                    {
                        "service_doc_id": doc_id,
                        "action_id": f"{doc_id}:action:call:{index}",
                        "action_type": "call",
                        "label": f"Call {item.label or 'phone'}".strip(),
                        "channel": "phone",
                        "target": item.value,
                        "action_url": tel_url,
                        "related_contact_id": contact_id,
                        "related_location_id": "",
                        "source_url": source_url,
                        "source_content_cid": source_content_cid,
                        "source_page_cid": source_page_cid,
                        "confidence": float(item.confidence),
                    }
                )
            if sms_url:
                action_rows.append(
                    {
                        "service_doc_id": doc_id,
                        "action_id": f"{doc_id}:action:text:{index}",
                        "action_type": "text",
                        "label": f"Text {item.label or 'phone'}".strip(),
                        "channel": "sms",
                        "target": item.value,
                        "action_url": sms_url,
                        "related_contact_id": contact_id,
                        "related_location_id": "",
                        "source_url": source_url,
                        "source_content_cid": source_content_cid,
                        "source_page_cid": source_page_cid,
                        "confidence": float(item.confidence),
                    }
                )

        email_objects: list[dict[str, Any]] = []
        for index, item in enumerate(email_values):
            action_url = f"mailto:{item.value}"
            contact_id = f"{doc_id}:contact:email:{index}"
            email_objects.append(
                {
                    "contact_id": contact_id,
                    "type": "email",
                    "label": item.label or "email",
                    "value": item.value,
                    "mailto_url": action_url,
                    "confidence": item.confidence,
                }
            )
            contact_rows.append(
                {
                    "service_doc_id": doc_id,
                    "contact_id": contact_id,
                    "contact_type": "email",
                    "label": item.label or "email",
                    "value": item.value,
                    "action_url": action_url,
                    "alternate_action_url": "",
                    "source_url": source_url,
                    "source_content_cid": source_content_cid,
                    "source_page_cid": source_page_cid,
                    "source_text": item.source_text,
                    "source_span_start": int(item.span_start),
                    "source_span_end": int(item.span_end),
                    "source_field": item.source_field,
                    "extraction_method": item.extraction_method,
                    "confidence": float(item.confidence),
                }
            )
            action_rows.append(
                {
                    "service_doc_id": doc_id,
                    "action_id": f"{doc_id}:action:email:{index}",
                    "action_type": "email",
                    "label": "Email provider",
                    "channel": "email",
                    "target": item.value,
                    "action_url": action_url,
                    "related_contact_id": contact_id,
                    "related_location_id": "",
                    "source_url": source_url,
                    "source_content_cid": source_content_cid,
                    "source_page_cid": source_page_cid,
                    "confidence": float(item.confidence),
                }
            )

        website_values = unique_nonempty(
            [
                str(metadata.get("website") or ""),
                source_url,
            ]
        )
        website_objects: list[dict[str, Any]] = []
        for index, website in enumerate(website_values):
            label = "provider_website" if website != source_url else "source_listing"
            contact_id = f"{doc_id}:contact:website:{index}"
            website_objects.append(
                {
                    "contact_id": contact_id,
                    "type": "website",
                    "label": label,
                    "value": website,
                    "url": website,
                    "confidence": 0.99 if website == source_url else 0.95,
                }
            )
            contact_rows.append(
                {
                    "service_doc_id": doc_id,
                    "contact_id": contact_id,
                    "contact_type": "website",
                    "label": label,
                    "value": website,
                    "action_url": website,
                    "alternate_action_url": "",
                    "source_url": source_url,
                    "source_content_cid": source_content_cid,
                    "source_page_cid": source_page_cid,
                    "source_text": website,
                    "source_span_start": -1,
                    "source_span_end": -1,
                    "source_field": "service_metadata" if website != source_url else "source_url",
                    "extraction_method": "service_metadata" if website != source_url else "document_row",
                    "confidence": 0.99 if website == source_url else 0.95,
                }
            )
            action_rows.append(
                {
                    "service_doc_id": doc_id,
                    "action_id": f"{doc_id}:action:website:{index}",
                    "action_type": "open_website",
                    "label": "Open website" if website != source_url else "Open source page",
                    "channel": "web",
                    "target": website,
                    "action_url": website,
                    "related_contact_id": contact_id,
                    "related_location_id": "",
                    "source_url": source_url,
                    "source_content_cid": source_content_cid,
                    "source_page_cid": source_page_cid,
                    "confidence": 0.99 if website == source_url else 0.95,
                }
            )

        for field_name, items in {
            "hours": hours_values,
            "eligibility": eligibility_values,
            "intake_steps": intake_values,
            "required_documents": required_documents_values,
            "fees": fees_values,
            "languages": languages_values,
            "accessibility": accessibility_values,
            "travel_info": travel_values,
            "area_served": area_served_values,
        }.items():
            if items:
                coverage[field_name] += 1

        for field_name, items in {
            "hours": hours_values,
            "eligibility": eligibility_values,
            "intake_steps": intake_values,
            "required_documents": required_documents_values,
            "fees": fees_values,
            "languages": languages_values,
            "accessibility": accessibility_values,
            "travel_info": travel_values,
            "area_served": area_served_values,
        }.items():
            for index, item in enumerate(items):
                row_id = f"{doc_id}:requirement:{field_name}:{index}"
                if field_name == "hours":
                    hours_rows.append(
                        {
                            "service_doc_id": doc_id,
                            "hours_id": row_id,
                            "label": item.label or "hours",
                            "hours_text": item.value,
                            "normalized_text": item.value,
                            "source_url": source_url,
                            "source_content_cid": source_content_cid,
                            "source_page_cid": source_page_cid,
                            "source_text": item.source_text,
                            "source_span_start": int(item.span_start),
                            "source_span_end": int(item.span_end),
                            "source_field": item.source_field,
                            "extraction_method": item.extraction_method,
                            "confidence": float(item.confidence),
                        }
                    )
                else:
                    requirement_rows.append(
                        {
                            "service_doc_id": doc_id,
                            "requirement_id": row_id,
                            "requirement_type": field_name,
                            "label": item.label or field_name,
                            "value": item.value,
                            "source_url": source_url,
                            "source_content_cid": source_content_cid,
                            "source_page_cid": source_page_cid,
                            "source_text": item.source_text,
                            "source_span_start": int(item.span_start),
                            "source_span_end": int(item.span_end),
                            "source_field": item.source_field,
                            "extraction_method": item.extraction_method,
                            "confidence": float(item.confidence),
                        }
                    )

        portal_source_extracts: dict[str, Any] = {
            "addresses": [
                item.as_provenance(
                    source_url=source_url,
                    source_content_cid=source_content_cid,
                    source_page_cid=source_page_cid,
                )
                for item in address_values
            ],
            "phones": [
                item.as_provenance(
                    source_url=source_url,
                    source_content_cid=source_content_cid,
                    source_page_cid=source_page_cid,
                )
                for item in phone_values
            ],
            "emails": [
                item.as_provenance(
                    source_url=source_url,
                    source_content_cid=source_content_cid,
                    source_page_cid=source_page_cid,
                )
                for item in email_values
            ],
            "hours": [
                item.as_provenance(
                    source_url=source_url,
                    source_content_cid=source_content_cid,
                    source_page_cid=source_page_cid,
                )
                for item in hours_values
            ],
            "eligibility": [
                item.as_provenance(
                    source_url=source_url,
                    source_content_cid=source_content_cid,
                    source_page_cid=source_page_cid,
                )
                for item in eligibility_values
            ],
            "intake_steps": [
                item.as_provenance(
                    source_url=source_url,
                    source_content_cid=source_content_cid,
                    source_page_cid=source_page_cid,
                )
                for item in intake_values
            ],
            "required_documents": [
                item.as_provenance(
                    source_url=source_url,
                    source_content_cid=source_content_cid,
                    source_page_cid=source_page_cid,
                )
                for item in required_documents_values
            ],
            "fees": [
                item.as_provenance(
                    source_url=source_url,
                    source_content_cid=source_content_cid,
                    source_page_cid=source_page_cid,
                )
                for item in fees_values
            ],
            "languages": [
                item.as_provenance(
                    source_url=source_url,
                    source_content_cid=source_content_cid,
                    source_page_cid=source_page_cid,
                )
                for item in languages_values
            ],
            "accessibility": [
                item.as_provenance(
                    source_url=source_url,
                    source_content_cid=source_content_cid,
                    source_page_cid=source_page_cid,
                )
                for item in accessibility_values
            ],
        }
        field_confidence = {
            "provider_name": 0.99 if provider_name else 0.0,
            "program_name": 0.97 if program_name else 0.0,
            "description": 0.96 if description else 0.0,
            "categories": 0.92 if categories else 0.0,
            "addresses": max((item.confidence for item in address_values), default=0.0),
            "phones": max((item.confidence for item in phone_values), default=0.0),
            "emails": max((item.confidence for item in email_values), default=0.0),
            "hours": max((item.confidence for item in hours_values), default=0.0),
            "eligibility": max((item.confidence for item in eligibility_values), default=0.0),
            "intake_steps": max((item.confidence for item in intake_values), default=0.0),
            "required_documents": max((item.confidence for item in required_documents_values), default=0.0),
            "fees": max((item.confidence for item in fees_values), default=0.0),
            "languages": max((item.confidence for item in languages_values), default=0.0),
            "accessibility": max((item.confidence for item in accessibility_values), default=0.0),
            "geo": max((item.confidence for item in address_values), default=0.0),
        }

        geo_payload = address_objects[0]["geo"] if address_objects else {"lat": None, "lon": None, "precision": "none"}
        portal_rows.append(
            {
                "service_doc_id": doc_id,
                "doc_type": str(row.get("doc_type") or "service"),
                "title": title,
                "provider_name": provider_name,
                "program_name": program_name,
                "description": description,
                "categories": compact_json(categories),
                "source_url": source_url,
                "source_content_cid": source_content_cid,
                "source_page_cid": source_page_cid,
                "host": clean_text(str(row.get("host") or "")),
                "city": derived_city,
                "state": derived_state,
                "addresses": compact_json(address_objects),
                "phones": compact_json(phone_objects),
                "emails": compact_json(email_objects),
                "websites": compact_json(website_objects),
                "hours": compact_json([item.as_provenance(source_url=source_url, source_content_cid=source_content_cid, source_page_cid=source_page_cid) for item in hours_values]),
                "eligibility": compact_json([item.as_provenance(source_url=source_url, source_content_cid=source_content_cid, source_page_cid=source_page_cid) for item in eligibility_values]),
                "intake_steps": compact_json([item.as_provenance(source_url=source_url, source_content_cid=source_content_cid, source_page_cid=source_page_cid) for item in intake_values]),
                "required_documents": compact_json([item.as_provenance(source_url=source_url, source_content_cid=source_content_cid, source_page_cid=source_page_cid) for item in required_documents_values]),
                "fees": compact_json([item.as_provenance(source_url=source_url, source_content_cid=source_content_cid, source_page_cid=source_page_cid) for item in fees_values]),
                "languages": compact_json([item.as_provenance(source_url=source_url, source_content_cid=source_content_cid, source_page_cid=source_page_cid) for item in languages_values]),
                "accessibility": compact_json([item.as_provenance(source_url=source_url, source_content_cid=source_content_cid, source_page_cid=source_page_cid) for item in accessibility_values]),
                "geo": compact_json(geo_payload),
                "source_extracts": compact_json(portal_source_extracts),
                "field_confidence": compact_json(field_confidence),
                "updated_at": updated_at_by_service_id.get(primary_service_id, retrieval_manifest.get("generated_at", utc_now())),
                "travel_info": compact_json([item.as_provenance(source_url=source_url, source_content_cid=source_content_cid, source_page_cid=source_page_cid) for item in travel_values]),
                "area_served": compact_json([item.as_provenance(source_url=source_url, source_content_cid=source_content_cid, source_page_cid=source_page_cid) for item in area_served_values]),
            }
        )

        action_rows.append(
            {
                "service_doc_id": doc_id,
                "action_id": f"{doc_id}:action:share",
                "action_type": "share",
                "label": "Share service",
                "channel": "share",
                "target": title or provider_name or source_url,
                "action_url": source_url,
                "related_contact_id": "",
                "related_location_id": "",
                "source_url": source_url,
                "source_content_cid": source_content_cid,
                "source_page_cid": source_page_cid,
                "confidence": 0.99,
            }
        )

        coverage["service_doc_id"] += 1 if doc_id else 0
        coverage["provider_name"] += 1 if provider_name else 0
        coverage["program_name"] += 1 if program_name else 0
        coverage["source_url"] += 1 if source_url else 0
        coverage["source_content_cid"] += 1 if source_content_cid else 0
        coverage["source_page_cid"] += 1 if source_page_cid else 0
        coverage["addresses"] += 1 if address_values else 0
        coverage["phones"] += 1 if phone_values else 0
        coverage["emails"] += 1 if email_values else 0

    services_frame = pd.DataFrame(portal_rows).sort_values(["title", "service_doc_id"]).reset_index(drop=True)
    contacts_frame = pd.DataFrame(contact_rows).sort_values(["service_doc_id", "contact_type", "contact_id"]).reset_index(drop=True)
    locations_frame = pd.DataFrame(location_rows).sort_values(["service_doc_id", "location_id"]).reset_index(drop=True)
    hours_frame = pd.DataFrame(hours_rows).sort_values(["service_doc_id", "hours_id"]).reset_index(drop=True)
    requirements_frame = pd.DataFrame(requirement_rows).sort_values(["service_doc_id", "requirement_type", "requirement_id"]).reset_index(drop=True)
    actions_frame = pd.DataFrame(action_rows).sort_values(["service_doc_id", "action_type", "action_id"]).reset_index(drop=True)

    output_files = {
        "services.parquet": services_frame,
        "documents.portal.parquet": services_frame,
        "service_contacts.parquet": contacts_frame,
        "service_locations.parquet": locations_frame,
        "service_hours.parquet": hours_frame,
        "service_requirements.parquet": requirements_frame,
        "service_actions.parquet": actions_frame,
    }
    artifact_rows: list[dict[str, Any]] = []
    for filename, frame in output_files.items():
        path = output_dir / filename
        frame.to_parquet(path, index=False)
        artifact_rows.append(artifact_record(path, row_count=len(frame)))

    service_count = len(services_frame)
    coverage_report = {
        "service_count": service_count,
        "coverage": {
            field: {
                "count": int(count),
                "pct": float(count / service_count) if service_count else 0.0,
            }
            for field, count in sorted(coverage.items())
        },
    }
    coverage_path = output_dir / "extraction_coverage_report.json"
    coverage_path.write_text(json.dumps(coverage_report, indent=2, ensure_ascii=False), encoding="utf-8")
    artifact_rows.append(artifact_record(coverage_path, row_count=service_count))

    manifest = {
        "schemaVersion": 1,
        "generated_at": utc_now(),
        "source_package": {
            "path": str(package_dir),
            "build_manifest_cid": retrieval_manifest.get("build_manifest_cid", ""),
            "document_count": int(retrieval_manifest.get("document_count", 0)),
            "service_document_count": int(retrieval_manifest.get("service_document_count", len(service_docs))),
            "page_document_count": int(retrieval_manifest.get("page_document_count", len(page_docs))),
        },
        "warehouse_path": str(warehouse_path),
        "service_count": int(service_count),
        "contact_count": int(len(contacts_frame)),
        "location_count": int(len(locations_frame)),
        "hours_count": int(len(hours_frame)),
        "requirement_count": int(len(requirements_frame)),
        "action_count": int(len(actions_frame)),
        "coverage": coverage_report["coverage"],
        "artifacts": artifact_rows,
    }
    manifest["portal_manifest_cid"] = cid_for_obj(manifest)

    manifest_path = output_dir / "service_portal_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    extraction_manifest_path = output_dir / "extraction_manifest.json"
    extraction_manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(
        "Portal package built: %d services, %d contacts, %d locations, %d requirements",
        service_count,
        len(contacts_frame),
        len(locations_frame),
        len(requirements_frame),
    )
    return manifest


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a structured portal package from the 211 retrieval corpus")
    parser.add_argument("--package-dir", type=Path, default=DEFAULT_PACKAGE_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--warehouse-path", type=Path, default=DEFAULT_WAREHOUSE_PATH)
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    setup_logging(getattr(logging, args.log_level))
    manifest = build_service_portal_package(
        package_dir=args.package_dir,
        output_dir=args.output_dir,
        warehouse_path=args.warehouse_path,
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
