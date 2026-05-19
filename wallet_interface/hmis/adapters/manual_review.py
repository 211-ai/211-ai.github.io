"""Manual-review HMIS adapter backed by local fixtures."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from ..models import HmisActionType, HmisAdapterCapabilities, HmisAdapterResult


def _normalized_text(value: Any) -> str:
    return str(value or "").strip().lower()


@dataclass(slots=True)
class ManualReviewHmisAdapter:
    """Local fixture adapter for early HMIS lookup and review workflows."""

    fixtures: list[dict[str, Any]] = field(default_factory=list)
    name: str = "manual-review"

    def capabilities(self) -> HmisAdapterCapabilities:
        return HmisAdapterCapabilities(
            supports_lookup=True,
            supports_manual_review_packets=True,
        )

    def execute(
        self,
        *,
        action_type: HmisActionType,
        payload: Mapping[str, Any],
        context: Mapping[str, Any] | None = None,
    ) -> HmisAdapterResult:
        if action_type not in {"lookup_client", "lookup_household", "list_program_links"}:
            return HmisAdapterResult.failure(
                action_type=action_type,
                adapter_name=self.name,
                summary=f"manual review adapter does not implement {action_type}",
                errors=(f"unsupported action: {action_type}",),
            )

        matches = self._lookup_candidates(payload)
        return HmisAdapterResult.success(
            action_type=action_type,
            adapter_name=self.name,
            summary=f"found {len(matches)} HMIS fixture candidate(s)",
            normalized_payload={"candidates": matches, "candidate_count": len(matches)},
            warnings=("results are from manual-review fixtures, not a live HMIS",),
        )

    def _lookup_candidates(self, payload: Mapping[str, Any]) -> list[dict[str, Any]]:
        criteria = payload.get("criteria")
        if not isinstance(criteria, Mapping):
            criteria = payload

        name_query = _normalized_text(criteria.get("name"))
        dob_query = _normalized_text(criteria.get("date_of_birth"))
        program_query = _normalized_text(criteria.get("program_ref"))

        matches: list[dict[str, Any]] = []
        for fixture in self.fixtures:
            candidate_name = _normalized_text(fixture.get("name"))
            candidate_dob = _normalized_text(fixture.get("date_of_birth"))
            candidate_program = _normalized_text(fixture.get("program_ref"))

            if name_query and name_query not in candidate_name:
                continue
            if dob_query and dob_query != candidate_dob:
                continue
            if program_query and program_query != candidate_program:
                continue
            matches.append(dict(fixture))
        return matches