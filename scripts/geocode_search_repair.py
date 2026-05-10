from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
IPFS_DATASETS_ROOT = REPO_ROOT / "ipfs_datasets_py"
for import_root in (IPFS_DATASETS_ROOT, REPO_ROOT):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))
os.environ.setdefault("IPFS_DATASETS_AUTO_INSTALL", "false")
os.environ.setdefault("IPFS_AUTO_INSTALL", "false")
os.environ.setdefault("IPFS_DATASETS_PY_MINIMAL_IMPORTS", "1")

from scraper.enrich_service_addresses import (  # noqa: E402
    AddressQuery,
    DEFAULT_CACHE_PATH,
    DEFAULT_PORTAL_DIR,
    NominatimGeocoder,
    clean_text,
    enrich_service_addresses,
    load_cache,
    utc_now,
    write_json_atomic,
)
from scripts.geocode_address_daemon import build_search_handoff  # noqa: E402


BRAVE_CLIENT_PATH = REPO_ROOT / "ipfs_datasets_py" / "ipfs_datasets_py" / "processors" / "web_archiving" / "brave_search_client.py"
DEFAULT_HANDOFF_JSON = DEFAULT_PORTAL_DIR / "geocode_search_handoff.json"
DEFAULT_REPORT_PATH = DEFAULT_PORTAL_DIR / "geocode_search_repair_report.json"
DEFAULT_BRAVE_SEARCH_CACHE = REPO_ROOT / "data" / "portal_geocoding" / "state" / "brave_search_cache.json"

STATE_NAME_TO_ABBREV = {
    "ALABAMA": "AL", "ALASKA": "AK", "ARIZONA": "AZ", "ARKANSAS": "AR", "CALIFORNIA": "CA",
    "COLORADO": "CO", "CONNECTICUT": "CT", "DELAWARE": "DE", "DISTRICT OF COLUMBIA": "DC",
    "FLORIDA": "FL", "GEORGIA": "GA", "HAWAII": "HI", "IDAHO": "ID", "ILLINOIS": "IL",
    "INDIANA": "IN", "IOWA": "IA", "KANSAS": "KS", "KENTUCKY": "KY", "LOUISIANA": "LA",
    "MAINE": "ME", "MARYLAND": "MD", "MASSACHUSETTS": "MA", "MICHIGAN": "MI", "MINNESOTA": "MN",
    "MISSISSIPPI": "MS", "MISSOURI": "MO", "MONTANA": "MT", "NEBRASKA": "NE", "NEVADA": "NV",
    "NEW HAMPSHIRE": "NH", "NEW JERSEY": "NJ", "NEW MEXICO": "NM", "NEW YORK": "NY",
    "NORTH CAROLINA": "NC", "NORTH DAKOTA": "ND", "OHIO": "OH", "OKLAHOMA": "OK", "OREGON": "OR",
    "PENNSYLVANIA": "PA", "RHODE ISLAND": "RI", "SOUTH CAROLINA": "SC", "SOUTH DAKOTA": "SD",
    "TENNESSEE": "TN", "TEXAS": "TX", "UTAH": "UT", "VERMONT": "VT", "VIRGINIA": "VA",
    "WASHINGTON": "WA", "WEST VIRGINIA": "WV", "WISCONSIN": "WI", "WYOMING": "WY",
}
STATE_ABBREVS = set(STATE_NAME_TO_ABBREV.values())
ADDRESS_RESULT_RE = re.compile(
    r"\b(?P<street>\d[0-9A-Za-z#./&' -]{2,96}?),\s*(?P<city>[A-Za-z][A-Za-z .'-]{1,64}),\s*(?P<state>[A-Za-z]{2,32})\s+(?P<postal>\d{5}(?:-\d{4})?)\b",
    re.IGNORECASE,
)


def _load_brave_module() -> Any:
    spec = importlib.util.spec_from_file_location("brave_search_client_direct", BRAVE_CLIENT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load Brave search client module from {BRAVE_CLIENT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BraveSearchRepairClient:
    def __init__(
        self,
        *,
        cache_path: Path | None = None,
        api_key: str | None = None,
        min_delay_seconds: float = 1.2,
        retry_attempts: int = 3,
    ) -> None:
        os.environ.setdefault("BRAVE_SEARCH_CACHE_PATH", str((cache_path or DEFAULT_BRAVE_SEARCH_CACHE).resolve()))
        module = _load_brave_module()
        resolved_key = str(api_key or module.resolve_brave_search_api_key(None) or "").strip()
        if not resolved_key:
            raise RuntimeError("Brave search API key could not be resolved")
        self._client = module.BraveSearchClient(api_key=resolved_key)
        self._min_delay_seconds = max(0.0, float(min_delay_seconds))
        self._retry_attempts = max(1, int(retry_attempts))
        self._last_request_at = 0.0

    def search(self, query: str, *, count: int) -> list[dict[str, Any]]:
        attempt = 0
        while attempt < self._retry_attempts:
            attempt += 1
            now = time.monotonic()
            wait_seconds = self._min_delay_seconds - (now - self._last_request_at)
            if wait_seconds > 0:
                time.sleep(wait_seconds)
            self._last_request_at = time.monotonic()
            try:
                results = self._client.search(query=query, count=count)
                if isinstance(results, list):
                    return [item for item in results if isinstance(item, dict)]
                if isinstance(results, dict):
                    web = results.get("web")
                    if isinstance(web, dict):
                        nested = web.get("results")
                        if isinstance(nested, list):
                            return [item for item in nested if isinstance(item, dict)]
                return []
            except RuntimeError as exc:
                if "HTTP 429" in str(exc) and attempt < self._retry_attempts:
                    time.sleep(max(2.0, self._min_delay_seconds) * attempt)
                    continue
                raise
        return []


def normalize_state_token(token: str) -> str:
    value = clean_text(token).upper()
    if value in STATE_ABBREVS:
        return value
    return STATE_NAME_TO_ABBREV.get(value, value)


def extract_candidate_address_strings(text: str) -> list[str]:
    value = clean_text(text.replace("·", " ").replace("|", " ").replace(" - ", " "))
    candidates: list[str] = []
    seen: set[str] = set()
    for match in ADDRESS_RESULT_RE.finditer(value):
        street = clean_text(match.group("street"))
        city = clean_text(match.group("city"))
        state = normalize_state_token(match.group("state"))
        postal = clean_text(match.group("postal"))
        if not street or not city or len(state) != 2 or not postal:
            continue
        candidate = f"{street}, {city}, {state} {postal}"
        signature = candidate.lower()
        if signature in seen:
            continue
        seen.add(signature)
        candidates.append(candidate)
    return candidates


def build_query_from_address_string(text: str) -> AddressQuery | None:
    matches = extract_candidate_address_strings(text)
    if not matches:
        return None
    match = ADDRESS_RESULT_RE.search(matches[0])
    if not match:
        return None
    street = clean_text(match.group("street"))
    city = clean_text(match.group("city"))
    state = normalize_state_token(match.group("state"))
    postal = clean_text(match.group("postal"))
    if not street or not city or len(state) != 2:
        return None
    return AddressQuery(
        address=street,
        street=street,
        city=city,
        state=state,
        postal_code=postal,
    )


def build_search_queries(row: dict[str, Any]) -> list[str]:
    queries: list[str] = []
    seen: set[str] = set()
    for value in (
        row.get("search_query_quoted"),
        row.get("search_query"),
        row.get("normalized_address"),
        row.get("address"),
    ):
        query = clean_text(str(value or ""))
        if not query:
            continue
        signature = query.lower()
        if signature in seen:
            continue
        seen.add(signature)
        queries.append(query)
    return queries


def repair_handoff_batch(
    *,
    source_dir: Path,
    cache_path: Path,
    handoff_json_path: Path,
    report_path: Path,
    max_rows: int,
    classifications: set[str] | None = None,
    search_results_per_query: int = 5,
) -> dict[str, Any]:
    handoff = json.loads(handoff_json_path.read_text(encoding="utf-8"))
    rows = handoff.get("rows") if isinstance(handoff.get("rows"), list) else []
    cache = load_cache(cache_path)
    brave = BraveSearchRepairClient()
    geocoder = NominatimGeocoder(min_delay_seconds=1.1, timeout_seconds=12.0, max_retries=2)

    attempted = 0
    repaired = 0
    unrepaired = 0
    updated_keys: list[str] = []
    processed_rows: list[dict[str, Any]] = []

    allowed = classifications or {"likely_provider_or_coverage_miss", "likely_malformed_input"}
    for row in rows:
        if attempted >= max(0, int(max_rows)):
            break
        if not isinstance(row, dict):
            continue
        cache_key = str(row.get("cache_key") or "")
        if not cache_key:
            continue
        current = cache.get(cache_key)
        if isinstance(current, dict) and current.get("status") == "ok":
            continue
        classification = str(row.get("classification") or "")
        if classification not in allowed:
            continue

        attempted += 1
        search_queries = build_search_queries(row)
        search_results_meta: list[dict[str, Any]] = []
        candidate_addresses: list[str] = []
        seen_candidates: set[str] = set()
        success_record: dict[str, Any] | None = None
        success_query: str = ""
        search_error = ""

        for search_query in search_queries:
            try:
                results = brave.search(search_query, count=search_results_per_query)
            except Exception as exc:
                search_error = f"{type(exc).__name__}: {exc}"
                search_results_meta.append({"query": search_query, "result_count": 0, "error": search_error})
                continue
            search_results_meta.append({"query": search_query, "result_count": len(results)})
            for result in results:
                for text in (result.get("title"), result.get("description")):
                    for candidate in extract_candidate_address_strings(str(text or "")):
                        signature = candidate.lower()
                        if signature in seen_candidates:
                            continue
                        seen_candidates.add(signature)
                        candidate_addresses.append(candidate)
            for candidate in candidate_addresses:
                address_query = build_query_from_address_string(candidate)
                if address_query is None:
                    continue
                record = geocoder.geocode(address_query)
                if record.get("status") == "ok":
                    original_query = current.get("query") if isinstance(current, dict) and isinstance(current.get("query"), dict) else {
                        "address": row.get("address") or "",
                        "street": row.get("street") or "",
                        "city": row.get("city") or "",
                        "state": row.get("state") or "",
                        "postal_code": row.get("postal_code") or "",
                        "country_code": "us",
                    }
                    record["query"] = original_query
                    record["repair_strategy"] = "brave_search_extract"
                    record["repair_query"] = {
                        "address": address_query.address,
                        "street": address_query.street,
                        "city": address_query.city,
                        "state": address_query.state,
                        "postal_code": address_query.postal_code,
                        "country_code": address_query.country_code,
                    }
                    record["search_repair"] = {
                        "engine": "brave",
                        "selected_search_query": search_query,
                        "candidate_address": candidate,
                        "attempted_at": utc_now(),
                        "search_results": search_results_meta,
                    }
                    success_record = record
                    success_query = search_query
                    break
            if success_record is not None:
                break

        processed_entry = {
            "cache_key": cache_key,
            "classification": classification,
            "search_queries": search_queries,
            "candidate_addresses": candidate_addresses[:10],
            "selected_search_query": success_query,
            "status": "ok" if success_record is not None else "miss",
            "search_error": search_error,
        }
        processed_rows.append(processed_entry)

        if success_record is not None:
            cache[cache_key] = success_record
            repaired += 1
            updated_keys.append(cache_key)
        else:
            unrepaired += 1
            existing = dict(current or {})
            existing["search_repair"] = {
                "engine": "brave",
                "attempted_at": utc_now(),
                "search_results": search_results_meta,
                "candidate_addresses": candidate_addresses[:10],
                "status": "miss",
            }
            cache[cache_key] = existing
        write_json_atomic(cache_path, cache)

    refresh_result = enrich_service_addresses(
        source_dir=source_dir,
        cache_path=cache_path,
        refresh_only=True,
    )
    refreshed_handoff = build_search_handoff(source_dir, cache_path)
    report = {
        "generated_at": utc_now(),
        "attempted_rows": attempted,
        "repaired_rows": repaired,
        "unrepaired_rows": unrepaired,
        "updated_cache_keys": updated_keys,
        "processed_rows": processed_rows,
        "refresh_result": refresh_result,
        "refreshed_handoff": refreshed_handoff,
    }
    write_json_atomic(report_path, report)
    return report


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Repair geocode search handoff rows using Brave search result extraction")
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_PORTAL_DIR)
    parser.add_argument("--cache-path", type=Path, default=DEFAULT_CACHE_PATH)
    parser.add_argument("--handoff-json", type=Path, default=DEFAULT_HANDOFF_JSON)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--max-rows", type=int, default=25)
    parser.add_argument(
        "--classification",
        action="append",
        dest="classifications",
        default=[],
        help="Classification to include; may be passed multiple times",
    )
    parser.add_argument("--search-results-per-query", type=int, default=5)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    classifications = set(args.classifications) if args.classifications else None
    report = repair_handoff_batch(
        source_dir=args.source_dir,
        cache_path=args.cache_path,
        handoff_json_path=args.handoff_json,
        report_path=args.report_path,
        max_rows=args.max_rows,
        classifications=classifications,
        search_results_per_query=args.search_results_per_query,
    )
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
