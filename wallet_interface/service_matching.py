"""211 service matching from wallet-derived facts."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence


@dataclass(frozen=True)
class ServiceRecord:
    id: str
    name: str
    description: str
    categories: str = ""
    city: str = ""
    state: str = ""
    zip: str = ""
    phone: str = ""
    website: str = ""
    source_url: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ServiceRecord":
        return cls(
            id=str(data.get("id", "")),
            name=str(data.get("name", "")),
            description=str(data.get("description", "")),
            categories=str(data.get("categories", "")),
            city=str(data.get("city", "")),
            state=str(data.get("state", "")),
            zip=str(data.get("zip", "")),
            phone=str(data.get("phone", "")),
            website=str(data.get("website", "")),
            source_url=str(data.get("source_url", "")),
        )


@dataclass(frozen=True)
class ServiceMatch:
    service: ServiceRecord
    score: float
    reasons: List[str]


def load_services_jsonl(path: str | Path) -> List[ServiceRecord]:
    records: List[ServiceRecord] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            records.append(ServiceRecord.from_dict(json.loads(line)))
    return records


def match_services(
    services: Iterable[ServiceRecord],
    *,
    need_terms: Sequence[str],
    location_claim: Dict[str, Any] | None = None,
    limit: int = 10,
) -> List[ServiceMatch]:
    """Rank 211 services using need terms and coarse wallet-derived location.

    `location_claim` must be a public/coarse claim. This function intentionally
    does not accept precise latitude/longitude fields directly.
    """

    normalized_terms = [_normalize(term) for term in need_terms if _normalize(term)]
    claim = location_claim or {}
    _reject_precise_location(claim)

    matches: List[ServiceMatch] = []
    for service in services:
        score, reasons = _score_service(service, normalized_terms, claim)
        if score > 0:
            matches.append(ServiceMatch(service=service, score=score, reasons=reasons))
    matches.sort(key=lambda item: (-item.score, item.service.name.lower()))
    return matches[: max(0, limit)]


def _score_service(
    service: ServiceRecord,
    terms: Sequence[str],
    location_claim: Dict[str, Any],
) -> tuple[float, List[str]]:
    haystack = _normalize(" ".join([service.name, service.description, service.categories]))
    score = 0.0
    reasons: List[str] = []

    for term in terms:
        if not term:
            continue
        if term in haystack:
            score += 5.0 if term in _normalize(service.categories) else 3.0
            reasons.append(f"matches need:{term}")

    claim_value = location_claim.get("public_value", location_claim)
    zip_code = str(claim_value.get("zip", "")).strip()
    city = _normalize(str(claim_value.get("city", "")))
    state = _normalize(str(claim_value.get("state", "")))
    if zip_code and service.zip == zip_code:
        score += 4.0
        reasons.append("matches coarse zip")
    if city and city == _normalize(service.city):
        score += 2.0
        reasons.append("matches coarse city")
    if state and state == _normalize(service.state):
        score += 1.0
        reasons.append("matches coarse state")

    return score, reasons


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _reject_precise_location(location_claim: Dict[str, Any]) -> None:
    claim_value = location_claim.get("public_value", location_claim)
    if "lat" in claim_value and "lon" in claim_value:
        precision = str(location_claim.get("precision", ""))
        if not precision.startswith("rounded:"):
            raise ValueError("service matching requires coarse or derived location, not precise coordinates")
