"""Scored HMIS identity matching helpers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal


MatchDecision = Literal["no_match", "single_match", "ambiguous", "rejected_only"]


def _normalized(value: Any) -> str:
    return str(value or "").strip().lower()


@dataclass(slots=True)
class HmisMatchCandidate:
    external_id: str
    score: float
    matched_fields: tuple[str, ...]
    record: dict[str, Any]
    rejected: bool = False
    reasons: tuple[str, ...] = ()


@dataclass(slots=True)
class HmisMatchResult:
    decision: MatchDecision
    candidates: tuple[HmisMatchCandidate, ...] = ()
    rejected_candidates: tuple[HmisMatchCandidate, ...] = ()
    auto_verified_candidate_id: str | None = None



def _score_client_candidate(query: Mapping[str, Any], candidate: Mapping[str, Any]) -> HmisMatchCandidate | None:
    score = 0.0
    matched_fields: list[str] = []
    reasons: list[str] = []

    query_name = _normalized(query.get("name"))
    candidate_name = _normalized(candidate.get("name"))
    if query_name:
        if query_name == candidate_name:
            score += 0.6
            matched_fields.append("name")
            reasons.append("exact name match")
        elif query_name in candidate_name or candidate_name in query_name:
            score += 0.35
            matched_fields.append("name")
            reasons.append("partial name match")

    query_dob = _normalized(query.get("date_of_birth"))
    candidate_dob = _normalized(candidate.get("date_of_birth"))
    if query_dob and candidate_dob and query_dob == candidate_dob:
        score += 0.25
        matched_fields.append("date_of_birth")
        reasons.append("date of birth match")

    query_program = _normalized(query.get("program_ref"))
    candidate_programs = {
        _normalized(candidate.get("program_ref")),
        _normalized(candidate.get("local_program_ref")),
        _normalized(candidate.get("external_program_id")),
        _normalized(candidate.get("external_project_id")),
    }
    candidate_programs.discard("")
    if query_program and query_program in candidate_programs:
        score += 0.15
        matched_fields.append("program_ref")
        reasons.append("program link match")

    if score <= 0:
        return None

    external_id = str(candidate.get("external_client_id") or candidate.get("external_id") or candidate.get("id") or "")
    return HmisMatchCandidate(
        external_id=external_id,
        score=round(min(score, 0.99), 3),
        matched_fields=tuple(matched_fields),
        record=dict(candidate),
        reasons=tuple(reasons),
    )



def _score_household_candidate(query: Mapping[str, Any], candidate: Mapping[str, Any]) -> HmisMatchCandidate | None:
    score = 0.0
    matched_fields: list[str] = []
    reasons: list[str] = []

    query_name = _normalized(query.get("name"))
    candidate_name = _normalized(candidate.get("household_name") or candidate.get("name"))
    if query_name:
        if query_name == candidate_name:
            score += 0.65
            matched_fields.append("name")
            reasons.append("exact household name match")
        elif query_name in candidate_name or candidate_name in query_name:
            score += 0.35
            matched_fields.append("name")
            reasons.append("partial household name match")

    query_program = _normalized(query.get("program_ref"))
    candidate_program = _normalized(candidate.get("program_ref"))
    if query_program and query_program == candidate_program:
        score += 0.2
        matched_fields.append("program_ref")
        reasons.append("program link match")

    member_count = int(candidate.get("member_count") or 0)
    if member_count > 0:
        score += 0.05
        matched_fields.append("member_count")
        reasons.append("household member count present")

    if score <= 0:
        return None

    external_id = str(candidate.get("external_household_id") or candidate.get("external_id") or candidate.get("id") or "")
    return HmisMatchCandidate(
        external_id=external_id,
        score=round(min(score, 0.99), 3),
        matched_fields=tuple(matched_fields),
        record=dict(candidate),
        reasons=tuple(reasons),
    )



def _finalize_match_result(
    candidates: Sequence[HmisMatchCandidate],
    *,
    rejected_candidate_ids: Sequence[str] = (),
) -> HmisMatchResult:
    rejected_ids = {str(item) for item in rejected_candidate_ids}
    ordered = sorted(candidates, key=lambda item: (-item.score, item.external_id))
    active: list[HmisMatchCandidate] = []
    rejected: list[HmisMatchCandidate] = []
    for candidate in ordered:
        if candidate.external_id in rejected_ids:
            rejected.append(
                HmisMatchCandidate(
                    external_id=candidate.external_id,
                    score=candidate.score,
                    matched_fields=candidate.matched_fields,
                    record=dict(candidate.record),
                    rejected=True,
                    reasons=candidate.reasons,
                )
            )
        else:
            active.append(candidate)

    if not active:
        return HmisMatchResult(
            decision="rejected_only" if rejected else "no_match",
            rejected_candidates=tuple(rejected),
        )

    top = active[0]
    if rejected and any(abs(top.score - candidate.score) < 0.1 for candidate in rejected):
        return HmisMatchResult(
            decision="ambiguous",
            candidates=tuple(active),
            rejected_candidates=tuple(rejected),
        )
    if len(active) == 1 and top.score >= 0.85:
        return HmisMatchResult(
            decision="single_match",
            candidates=tuple(active),
            rejected_candidates=tuple(rejected),
            auto_verified_candidate_id=top.external_id,
        )
    if len(active) > 1 and abs(active[0].score - active[1].score) < 0.1:
        return HmisMatchResult(
            decision="ambiguous",
            candidates=tuple(active),
            rejected_candidates=tuple(rejected),
        )
    if top.score < 0.85:
        return HmisMatchResult(
            decision="ambiguous",
            candidates=tuple(active),
            rejected_candidates=tuple(rejected),
        )
    return HmisMatchResult(
        decision="single_match",
        candidates=tuple(active),
        rejected_candidates=tuple(rejected),
        auto_verified_candidate_id=top.external_id,
    )



def match_hmis_clients(
    query: Mapping[str, Any],
    candidates: Sequence[Mapping[str, Any]],
    *,
    rejected_candidate_ids: Sequence[str] = (),
) -> HmisMatchResult:
    scored = [candidate for item in candidates if (candidate := _score_client_candidate(query, item)) is not None]
    return _finalize_match_result(scored, rejected_candidate_ids=rejected_candidate_ids)



def match_hmis_households(
    query: Mapping[str, Any],
    candidates: Sequence[Mapping[str, Any]],
    *,
    rejected_candidate_ids: Sequence[str] = (),
) -> HmisMatchResult:
    scored = [candidate for item in candidates if (candidate := _score_household_candidate(query, item)) is not None]
    return _finalize_match_result(scored, rejected_candidate_ids=rejected_candidate_ids)


__all__ = [
    "HmisMatchCandidate",
    "HmisMatchResult",
    "match_hmis_clients",
    "match_hmis_households",
]
