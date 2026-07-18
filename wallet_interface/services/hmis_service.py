"""HMIS domain service mixin for WalletInterfaceService."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import uuid4

if TYPE_CHECKING:
    pass

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

HMIS_STATE_TYPE = "wallet_repository_hmis_state_v1"
HMIS_STATE_FILENAME = "hmis-state.json"
HMIS_AUDIT_FILENAME = "hmis-audit.jsonl"


DEFAULT_HMIS_FIXTURES: dict[str, list[dict[str, Any]]] = {
    "clients": [
        {
            "entity_type": "client",
            "external_client_id": "client-100",
            "name": "Jane Doe",
            "date_of_birth": "1990-04-05",
            "program_ref": "shelter-a",
            "phone": "503-555-0100",
            "email": "jane@example.org",
            "last_sync_at": "2026-07-01T10:00:00+00:00",
        },
        {
            "entity_type": "client",
            "external_client_id": "client-200",
            "name": "Alex Smith",
            "date_of_birth": "1984-01-02",
            "program_ref": "rapid-rehousing",
            "phone": "503-555-0200",
            "email": "alex@example.org",
            "last_sync_at": "2026-07-02T10:00:00+00:00",
        },
    ],
    "households": [
        {
            "entity_type": "household",
            "external_household_id": "household-100",
            "household_name": "Doe Household",
            "program_ref": "shelter-a",
            "member_count": 2,
            "last_sync_at": "2026-07-01T10:00:00+00:00",
        },
        {
            "entity_type": "household",
            "external_household_id": "household-200",
            "household_name": "Rivera Household",
            "program_ref": "rapid-rehousing",
            "member_count": 3,
            "last_sync_at": "2026-07-02T10:00:00+00:00",
        },
    ],
    "programs": [
        {
            "entity_type": "program",
            "local_program_ref": "shelter-a",
            "program_name": "Emergency Shelter",
            "provider_name": "Safe Harbor Shelter",
            "external_program_id": "HMIS-PROGRAM-100",
            "external_project_id": "HMIS-PROJECT-100",
            "last_sync_at": "2026-07-01T10:00:00+00:00",
        },
        {
            "entity_type": "program",
            "local_program_ref": "rapid-rehousing",
            "program_name": "Rapid Rehousing",
            "provider_name": "Bridge Housing Network",
            "external_program_id": "HMIS-PROGRAM-200",
            "external_project_id": "HMIS-PROJECT-200",
            "last_sync_at": "2026-07-02T10:00:00+00:00",
        },
    ],
}


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _hmis_now() -> str:
    return datetime.now(UTC).isoformat()


def _mask_name(value: str) -> str:
    parts = [part for part in str(value or "").strip().split() if part]
    return " ".join(f"{part[:1]}***" for part in parts)


def _mask_hmis_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    masked = dict(candidate)
    if "name" in masked:
        masked["name"] = _mask_name(str(masked.get("name") or ""))
    if "household_name" in masked:
        masked["household_name"] = _mask_name(str(masked.get("household_name") or ""))
    if "phone" in masked:
        masked["phone"] = "***-***-" + str(masked.get("phone") or "")[-4:]
    if "email" in masked:
        local, _, domain = str(masked.get("email") or "").partition("@")
        masked["email"] = (local[:1] + "***@" + domain) if domain else "***"
    if masked.get("date_of_birth"):
        masked["date_of_birth"] = str(masked["date_of_birth"])[:4]
    masked["masked"] = True
    return masked


def _empty_hmis_state() -> dict[str, Any]:
    return {
        "snapshot_type": HMIS_STATE_TYPE,
        "referral_drafts": [],
        "enrollment_drafts": [],
        "verified_links": [],
        "rejected_matches": [],
        "reconciliation_items": [],
        "submissions": {},
    }


# ---------------------------------------------------------------------------
# Mixin
# ---------------------------------------------------------------------------


class HmisDomainServiceMixin:
    """HMIS workflow methods mixed into WalletInterfaceService."""

    # ------------------------------------------------------------------
    # Private helpers (access self.repository, caches, etc.)
    # ------------------------------------------------------------------

    def _hmis_repository_root(self) -> Path:
        if self.repository is not None:  # type: ignore[attr-defined]
            return self.repository.root  # type: ignore[attr-defined]
        return Path.cwd()

    def _hmis_state_path(self) -> Path:
        return self._hmis_repository_root() / HMIS_STATE_FILENAME

    def _hmis_audit_path(self) -> Path:
        return self._hmis_repository_root() / HMIS_AUDIT_FILENAME

    def _ensure_hmis_state(self) -> dict[str, Any]:
        cached = getattr(self, "_hmis_state_cache", None)
        if isinstance(cached, dict):
            return cached
        path = self._hmis_state_path()
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            if str(payload.get("snapshot_type") or "") != HMIS_STATE_TYPE:
                raise ValueError("Unsupported HMIS state snapshot type")
        else:
            payload = _empty_hmis_state()
        setattr(self, "_hmis_state_cache", payload)
        return payload

    def _save_hmis_state(self) -> Path:
        payload = self._ensure_hmis_state()
        path = self._hmis_state_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_name(f".{path.name}.tmp")
        tmp_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        tmp_path.replace(path)
        return path

    def _hmis_audit_store(self):
        from ..hmis.audit import HmisAuditStore

        store = getattr(self, "_hmis_audit_store_cache", None)
        if store is None:
            store = HmisAuditStore(path=self._hmis_audit_path())
            setattr(self, "_hmis_audit_store_cache", store)
        return store

    def _load_hmis_fixture_group(self, name: str) -> list[dict[str, Any]]:
        root = self._hmis_repository_root()
        path = root / "tests" / "fixtures" / "hmis" / f"{name}.json"
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, list):
                return [dict(item) for item in payload if isinstance(item, Mapping)]
        return [dict(item) for item in DEFAULT_HMIS_FIXTURES[name]]

    def _load_program_links(self) -> list[dict[str, Any]]:
        path = Path("state/hmis/program_links.json")
        if not path.exists():
            return []
        payload = json.loads(path.read_text(encoding="utf-8"))
        return [dict(item) for item in payload.get("program_links", []) if isinstance(item, Mapping)]

    def _hmis_manual_adapter(self):
        from ..hmis.adapters.manual_review import ManualReviewHmisAdapter

        fixtures = [
            *self._load_hmis_fixture_group("clients"),
            *self._load_hmis_fixture_group("households"),
            *self._load_hmis_fixture_group("programs"),
        ]
        return ManualReviewHmisAdapter(fixtures=fixtures)

    def _hmis_submission_service(self):
        from ..hmis import FileExchangeHmisAdapter, HmisService
        from ..hmis.service import HmisReconciliationItem

        service = getattr(self, "_hmis_submission_service_cache", None)
        if service is None:
            adapter = FileExchangeHmisAdapter(
                staging_dir=self._hmis_repository_root() / "data" / "hmis",
                fixture_imports=getattr(self, "_hmis_fixture_imports", ()),
            )
            service = HmisService(adapter=adapter, audit_store=self._hmis_audit_store())
            state = self._ensure_hmis_state()
            service.reconciliation_queue = [
                HmisReconciliationItem.from_dict(item)
                for item in state.get("reconciliation_items", [])
                if isinstance(item, Mapping)
            ]
            setattr(self, "_hmis_submission_service_cache", service)
        return service

    def _store_reconciliation_queue(self) -> None:
        service = self._hmis_submission_service()
        state = self._ensure_hmis_state()
        state["reconciliation_items"] = [item.to_dict() for item in service.list_reconciliation_items()]
        self._save_hmis_state()

    # ------------------------------------------------------------------
    # Public HMIS methods
    # ------------------------------------------------------------------

    def lookup_hmis_clients(
        self,
        wallet_id: str,
        *,
        actor_did: str,
        name: str = "",
        date_of_birth: str = "",
        program_ref: str = "",
    ) -> dict[str, Any]:
        from ..hmis.matching import match_hmis_clients

        self._require_portal_actor(wallet_id, actor_did)  # type: ignore[attr-defined]
        query = {"name": name, "date_of_birth": date_of_birth, "program_ref": program_ref}
        adapter_result = self._hmis_manual_adapter().execute(action_type="lookup_client", payload=query)
        candidates = adapter_result.normalized_payload.get("candidates", [])
        state = self._ensure_hmis_state()
        rejected = [
            item.get("external_id", "")
            for item in state.get("rejected_matches", [])
            if item.get("wallet_id") == wallet_id and item.get("entity_type") == "client"
        ]
        match_result = match_hmis_clients(query, candidates, rejected_candidate_ids=rejected)
        self._hmis_audit_store().record(
            action_type="lookup_client",
            actor_id=actor_did,
            local_ref=wallet_id,
            adapter_name="manual-review",
            status="success",
            response_summary=adapter_result.summary,
            metadata={"candidate_count": len(match_result.candidates), "decision": match_result.decision},
        )
        return {
            "status": "ok",
            "summary": adapter_result.summary,
            "clients": [
                {
                    **_mask_hmis_candidate(candidate.record),
                    "external_id": candidate.external_id,
                    "score": candidate.score,
                    "matched_fields": list(candidate.matched_fields),
                    "reasons": list(candidate.reasons),
                }
                for candidate in match_result.candidates
            ],
            "rejected_candidates": [
                {
                    **_mask_hmis_candidate(candidate.record),
                    "external_id": candidate.external_id,
                    "score": candidate.score,
                    "matched_fields": list(candidate.matched_fields),
                }
                for candidate in match_result.rejected_candidates
            ],
            "decision": match_result.decision,
            "last_sync_at": _hmis_now(),
        }

    def lookup_hmis_households(
        self,
        wallet_id: str,
        *,
        actor_did: str,
        name: str = "",
        program_ref: str = "",
    ) -> dict[str, Any]:
        from ..hmis.matching import match_hmis_households

        self._require_portal_actor(wallet_id, actor_did)  # type: ignore[attr-defined]
        query = {"name": name, "program_ref": program_ref}
        adapter_result = self._hmis_manual_adapter().execute(action_type="lookup_household", payload=query)
        candidates = adapter_result.normalized_payload.get("candidates", [])
        state = self._ensure_hmis_state()
        rejected = [
            item.get("external_id", "")
            for item in state.get("rejected_matches", [])
            if item.get("wallet_id") == wallet_id and item.get("entity_type") == "household"
        ]
        match_result = match_hmis_households(query, candidates, rejected_candidate_ids=rejected)
        self._hmis_audit_store().record(
            action_type="lookup_household",
            actor_id=actor_did,
            local_ref=wallet_id,
            adapter_name="manual-review",
            status="success",
            response_summary=adapter_result.summary,
            metadata={"candidate_count": len(match_result.candidates), "decision": match_result.decision},
        )
        return {
            "status": "ok",
            "summary": adapter_result.summary,
            "households": [
                {
                    **_mask_hmis_candidate(candidate.record),
                    "external_id": candidate.external_id,
                    "score": candidate.score,
                    "matched_fields": list(candidate.matched_fields),
                }
                for candidate in match_result.candidates
            ],
            "decision": match_result.decision,
            "last_sync_at": _hmis_now(),
        }

    def list_hmis_program_links(
        self,
        wallet_id: str,
        *,
        actor_did: str,
        name: str = "",
        program_ref: str = "",
    ) -> dict[str, Any]:
        self._require_portal_actor(wallet_id, actor_did)  # type: ignore[attr-defined]
        results = []
        name_query = str(name or "").strip().lower()
        program_query = str(program_ref or "").strip().lower()
        for item in self._load_program_links():
            haystacks = [
                str(item.get("program_name") or "").lower(),
                str(item.get("provider_name") or "").lower(),
                str(item.get("local_program_ref") or "").lower(),
            ]
            if name_query and not any(name_query in hay for hay in haystacks):
                continue
            if program_query and not any(program_query in hay for hay in haystacks):
                continue
            results.append(item)
        self._hmis_audit_store().record(
            action_type="list_program_links",
            actor_id=actor_did,
            local_ref=wallet_id,
            adapter_name="registry",
            status="success",
            response_summary=f"returned {len(results)} HMIS program link(s)",
        )
        return {
            "status": "ok",
            "program_links": results,
            "programs": results,
            "summary": f"returned {len(results)} program links",
        }

    def list_hmis_referral_drafts(self, wallet_id: str, *, status: str | None = None):
        from ..hmis.service import HmisReferralDraftRecord

        self.wallet_service._wallet(wallet_id)  # type: ignore[attr-defined]
        drafts = [
            HmisReferralDraftRecord.from_dict(item)
            for item in self._ensure_hmis_state().get("referral_drafts", [])
            if isinstance(item, Mapping) and str(item.get("wallet_id") or "") == wallet_id
        ]
        if status is not None:
            drafts = [draft for draft in drafts if draft.status == status]
        return sorted(drafts, key=lambda item: (item.updated_at or item.created_at, item.referral_draft_id))

    def create_hmis_referral_draft(
        self,
        wallet_id: str,
        *,
        actor_did: str,
        local_subject_ref: str,
        destination_program_ref: str,
        service_plan_id: str = "",
        service_doc_id: str = "",
        provider_name: str = "",
        program_name: str = "",
        summary: str = "",
        eligibility_notes: str = "",
        contact_notes: str = "",
        source_content_cid: str = "",
        source_page_cid: str = "",
        metadata: Mapping[str, Any] | None = None,
    ):
        from ..hmis.service import HmisReferralDraftRecord

        self._require_portal_actor(wallet_id, actor_did)  # type: ignore[attr-defined]
        now = _hmis_now()
        state = self._ensure_hmis_state()
        draft = HmisReferralDraftRecord(
            referral_draft_id=f"hmis-referral-draft-{uuid4().hex}",
            wallet_id=wallet_id,
            actor_id=actor_did,
            local_subject_ref=str(local_subject_ref or "").strip(),
            destination_program_ref=str(destination_program_ref or "").strip(),
            service_plan_id=str(service_plan_id or ""),
            service_doc_id=str(service_doc_id or ""),
            provider_name=str(provider_name or ""),
            program_name=str(program_name or ""),
            summary=str(summary or ""),
            eligibility_notes=str(eligibility_notes or ""),
            contact_notes=str(contact_notes or ""),
            source_content_cid=str(source_content_cid or ""),
            source_page_cid=str(source_page_cid or ""),
            status="draft",
            created_at=now,
            updated_at=now,
            metadata=dict(metadata or {}),
        )
        validator = self._hmis_submission_service()
        errors, warnings = validator.validate_referral_draft(draft)
        draft.validation_errors = errors
        draft.warnings = warnings
        if not errors:
            draft.status = "ready"
        state["referral_drafts"].append(draft.to_dict())
        self._save_hmis_state()
        self._hmis_audit_store().record(
            action_type="create_referral_draft",
            actor_id=actor_did,
            local_ref=draft.referral_draft_id,
            adapter_name="manual-review",
            status="success",
            response_summary="created HMIS referral draft",
            metadata={"wallet_id": wallet_id, "status": draft.status},
        )
        return draft

    def update_hmis_referral_draft(
        self,
        wallet_id: str,
        referral_draft_id: str,
        *,
        actor_did: str,
        local_subject_ref: str | None = None,
        destination_program_ref: str | None = None,
        service_plan_id: str | None = None,
        service_doc_id: str | None = None,
        provider_name: str | None = None,
        program_name: str | None = None,
        summary: str | None = None,
        eligibility_notes: str | None = None,
        contact_notes: str | None = None,
        source_content_cid: str | None = None,
        source_page_cid: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ):
        self._require_portal_actor(wallet_id, actor_did)  # type: ignore[attr-defined]
        drafts = self.list_hmis_referral_drafts(wallet_id)
        draft = next((item for item in drafts if item.referral_draft_id == referral_draft_id), None)
        if draft is None:
            raise ValueError("HMIS referral draft not found")
        for field_name, value in {
            "local_subject_ref": local_subject_ref,
            "destination_program_ref": destination_program_ref,
            "service_plan_id": service_plan_id,
            "service_doc_id": service_doc_id,
            "provider_name": provider_name,
            "program_name": program_name,
            "summary": summary,
            "eligibility_notes": eligibility_notes,
            "contact_notes": contact_notes,
            "source_content_cid": source_content_cid,
            "source_page_cid": source_page_cid,
        }.items():
            if value is not None:
                setattr(draft, field_name, str(value or ""))
        if metadata is not None:
            draft.metadata = {**draft.metadata, **dict(metadata)}
        draft.updated_at = _hmis_now()
        errors, warnings = self._hmis_submission_service().validate_referral_draft(draft)
        draft.validation_errors = errors
        draft.warnings = warnings
        draft.status = "ready" if not errors else "draft"
        state = self._ensure_hmis_state()
        state["referral_drafts"] = [
            draft.to_dict() if item.get("referral_draft_id") == referral_draft_id else item
            for item in state.get("referral_drafts", [])
        ]
        self._save_hmis_state()
        self._hmis_audit_store().record(
            action_type="validate_referral_draft",
            actor_id=actor_did,
            local_ref=referral_draft_id,
            adapter_name="manual-review",
            status="success",
            response_summary="updated HMIS referral draft",
            metadata={"status": draft.status},
        )
        return draft

    def validate_hmis_referral_draft(
        self,
        wallet_id: str,
        referral_draft_id: str,
        *,
        actor_did: str,
    ) -> dict[str, Any]:
        self._require_portal_actor(wallet_id, actor_did)  # type: ignore[attr-defined]
        draft = next(
            (item for item in self.list_hmis_referral_drafts(wallet_id) if item.referral_draft_id == referral_draft_id),
            None,
        )
        if draft is None:
            raise ValueError("HMIS referral draft not found")
        errors, warnings = self._hmis_submission_service().validate_referral_draft(draft)
        draft.validation_errors = errors
        draft.warnings = warnings
        draft.status = "ready" if not errors else "draft"
        state = self._ensure_hmis_state()
        state["referral_drafts"] = [
            draft.to_dict() if item.get("referral_draft_id") == referral_draft_id else item
            for item in state.get("referral_drafts", [])
        ]
        self._save_hmis_state()
        self._hmis_audit_store().record(
            action_type="validate_referral_draft",
            actor_id=actor_did,
            local_ref=referral_draft_id,
            adapter_name="manual-review",
            status="success",
            response_summary="validated HMIS referral draft",
            metadata={"validation_errors": list(errors), "warnings": list(warnings)},
        )
        return {"status": draft.status, "errors": errors, "warnings": warnings, "referral_draft": draft.to_dict()}

    def submit_hmis_referral_draft(
        self,
        wallet_id: str,
        referral_draft_id: str,
        *,
        actor_did: str,
    ) -> dict[str, Any]:
        from ..hmis.models import HmisConsentRecord

        self._require_portal_actor(wallet_id, actor_did)  # type: ignore[attr-defined]
        draft = next(
            (item for item in self.list_hmis_referral_drafts(wallet_id) if item.referral_draft_id == referral_draft_id),
            None,
        )
        if draft is None:
            raise ValueError("HMIS referral draft not found")
        errors, warnings = self._hmis_submission_service().validate_referral_draft(draft)
        if errors:
            raise ValueError("HMIS referral draft has validation errors")
        consent = HmisConsentRecord(
            consent_id=f"consent-{wallet_id}",
            subject_ref=draft.local_subject_ref,
            status="active",
            basis="client_consent",
            purpose="HMIS referral submission",
            authorized_scopes=("hmis_submit_referral",),
            authorized_program_refs=(draft.destination_program_ref,),
            effective_at="2026-01-01T00:00:00+00:00",
        )
        result = self._hmis_submission_service().submit_referral(
            draft,
            actor_id=actor_did,
            consent=consent,
            required_scope="hmis_submit_referral",
            context={"imports": getattr(self, "_hmis_fixture_imports", ())},
        )
        draft.updated_at = _hmis_now()
        if result.adapter_result.ok:
            draft.status = "submitted"
            draft.external_referral_id = (
                result.adapter_result.external_refs.get("referral_id")
                or result.adapter_result.external_refs.get("batch_id")
                or ""
            )
        else:
            draft.status = "retryable" if result.adapter_result.retryable else "needs_review"
        draft.warnings = [*warnings, *list(result.adapter_result.warnings)]
        state = self._ensure_hmis_state()
        state["referral_drafts"] = [
            draft.to_dict() if item.get("referral_draft_id") == referral_draft_id else item
            for item in state.get("referral_drafts", [])
        ]
        state.setdefault("submissions", {})[referral_draft_id] = {
            "status": draft.status,
            "summary": result.adapter_result.summary,
            "external_refs": dict(result.adapter_result.external_refs),
        }
        self._store_reconciliation_queue()
        return {
            "status": draft.status,
            "summary": result.adapter_result.summary,
            "referral_draft": draft.to_dict(),
            "external_refs": dict(result.adapter_result.external_refs),
        }

    def verify_hmis_match(
        self,
        wallet_id: str,
        *,
        actor_did: str,
        entity_type: str,
        local_ref: str,
        external_id: str,
        confidence: float,
    ) -> dict[str, Any]:
        self._require_portal_actor(wallet_id, actor_did)  # type: ignore[attr-defined]
        state = self._ensure_hmis_state()
        link = {
            "wallet_id": wallet_id,
            "entity_type": entity_type,
            "local_ref": local_ref,
            "external_id": external_id,
            "confidence": float(confidence),
            "status": "verified",
            "reviewed_by": actor_did,
            "reviewed_at": _hmis_now(),
        }
        state["verified_links"] = [
            item
            for item in state.get("verified_links", [])
            if not (
                item.get("wallet_id") == wallet_id
                and item.get("entity_type") == entity_type
                and item.get("local_ref") == local_ref
            )
        ]
        state["verified_links"].append(link)
        self._save_hmis_state()
        self._hmis_audit_store().record(
            action_type="link_external_record",
            actor_id=actor_did,
            local_ref=local_ref,
            external_ref=external_id,
            adapter_name="manual-review",
            status="success",
            response_summary="verified HMIS record link",
        )
        return link

    def reject_hmis_match(
        self,
        wallet_id: str,
        *,
        actor_did: str,
        entity_type: str,
        local_ref: str,
        external_id: str,
        reason: str,
    ) -> dict[str, Any]:
        self._require_portal_actor(wallet_id, actor_did)  # type: ignore[attr-defined]
        state = self._ensure_hmis_state()
        record = {
            "wallet_id": wallet_id,
            "entity_type": entity_type,
            "local_ref": local_ref,
            "external_id": external_id,
            "reason": reason,
            "rejected_by": actor_did,
            "rejected_at": _hmis_now(),
        }
        state.setdefault("rejected_matches", []).append(record)
        self._save_hmis_state()
        self._hmis_audit_store().record(
            action_type="reject_match",
            actor_id=actor_did,
            local_ref=local_ref,
            external_ref=external_id,
            adapter_name="manual-review",
            status="success",
            response_summary="rejected HMIS match candidate",
            metadata={"reason": reason},
        )
        return record

    def list_hmis_sync_timeline(self, wallet_id: str, *, local_ref: str | None = None) -> dict[str, Any]:
        self.wallet_service._wallet(wallet_id)  # type: ignore[attr-defined]
        events = self._hmis_audit_store().list_events(local_ref=local_ref or None)
        return {
            "status": "ok",
            "events": [
                {
                    "event_id": event.event_id,
                    "action_type": event.action_type,
                    "actor_id": event.actor_id,
                    "local_ref": event.local_ref,
                    "external_ref": event.external_ref,
                    "adapter_name": event.adapter_name,
                    "status": event.status,
                    "response_summary": event.response_summary,
                    "occurred_at": event.occurred_at,
                    "retry_count": event.retry_count,
                    "metadata": dict(event.metadata),
                }
                for event in events
            ],
        }

    def list_hmis_reconciliation_queue(self, wallet_id: str, *, status: str | None = None) -> dict[str, Any]:
        self.wallet_service._wallet(wallet_id)  # type: ignore[attr-defined]
        items = [
            item
            for item in self._hmis_submission_service().list_reconciliation_items(status=status)
            if item.wallet_id == wallet_id
        ]
        return {"status": "ok", "items": [item.to_dict() for item in items]}

    def retry_hmis_reconciliation_item(self, wallet_id: str, item_id: str, *, actor_did: str) -> dict[str, Any]:
        self._require_portal_actor(wallet_id, actor_did)  # type: ignore[attr-defined]
        service = self._hmis_submission_service()
        item = next(
            (row for row in service.list_reconciliation_items() if row.item_id == item_id and row.wallet_id == wallet_id),
            None,
        )
        if item is None:
            raise ValueError("HMIS reconciliation item not found")
        result = service.retry_reconciliation_item(
            item,
            actor_id=actor_did,
            context={"imports": getattr(self, "_hmis_fixture_imports", ())},
        )
        self._store_reconciliation_queue()
        return {
            "status": item.status,
            "summary": result.adapter_result.summary,
            "item": item.to_dict(),
            "external_refs": dict(result.adapter_result.external_refs),
        }

    def run_hmis_reconciliation_job(self, *, dry_run: bool = False) -> dict[str, Any]:
        service = self._hmis_submission_service()
        open_items = [item for item in service.list_reconciliation_items() if item.status == "open"]
        resolved = 0
        reviewed = 0
        for item in open_items:
            if dry_run:
                continue
            result = service.retry_reconciliation_item(
                item,
                actor_id="did:wallet:hmis-reconciliation",
                context={"imports": getattr(self, "_hmis_fixture_imports", ())},
            )
            if result.adapter_result.ok:
                resolved += 1
                draft = next(
                    (
                        row
                        for row in self.list_hmis_referral_drafts(item.wallet_id)
                        if row.referral_draft_id == item.referral_draft_id
                    ),
                    None,
                )
                if draft is not None:
                    draft.status = "reconciled"
                    draft.updated_at = _hmis_now()
                    state = self._ensure_hmis_state()
                    state["referral_drafts"] = [
                        draft.to_dict() if row.get("referral_draft_id") == draft.referral_draft_id else row
                        for row in state.get("referral_drafts", [])
                    ]
            elif item.status == "needs_review":
                reviewed += 1
        if not dry_run:
            self._store_reconciliation_queue()
        queue_items = service.list_reconciliation_items()
        return {
            "status": "dry-run" if dry_run else "ok",
            "queue_depth": len(queue_items),
            "open_count": sum(1 for item in queue_items if item.status == "open"),
            "resolved_count": sum(1 for item in queue_items if item.status == "resolved") if dry_run else resolved,
            "needs_review_count": sum(1 for item in queue_items if item.status == "needs_review") if dry_run else reviewed,
        }

    # ------------------------------------------------------------------
    # Phase 5: Enrollment draft flows
    # ------------------------------------------------------------------

    def list_hmis_enrollment_drafts(
        self,
        wallet_id: str,
        *,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        self.wallet_service._wallet(wallet_id)  # type: ignore[attr-defined]
        drafts = [
            item
            for item in self._ensure_hmis_state().get("enrollment_drafts", [])
            if isinstance(item, Mapping) and str(item.get("wallet_id") or "") == wallet_id
        ]
        if status is not None:
            drafts = [item for item in drafts if item.get("status") == status]
        return sorted(drafts, key=lambda item: (item.get("updated_at") or item.get("created_at") or "", item.get("enrollment_draft_id") or ""))

    def create_hmis_enrollment_draft(
        self,
        wallet_id: str,
        *,
        actor_did: str,
        local_subject_ref: str,
        destination_program_ref: str,
        entry_date: str = "",
        household_ref: str = "",
        summary: str = "",
        metadata: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._require_portal_actor(wallet_id, actor_did)  # type: ignore[attr-defined]
        now = _hmis_now()
        draft: dict[str, Any] = {
            "enrollment_draft_id": f"hmis-enrollment-draft-{uuid4().hex}",
            "wallet_id": wallet_id,
            "actor_id": actor_did,
            "local_subject_ref": str(local_subject_ref or "").strip(),
            "destination_program_ref": str(destination_program_ref or "").strip(),
            "entry_date": str(entry_date or ""),
            "household_ref": str(household_ref or ""),
            "summary": str(summary or ""),
            "status": "draft",
            "external_enrollment_id": None,
            "created_at": now,
            "updated_at": now,
            "metadata": dict(metadata or {}),
        }
        errors: list[str] = []
        if not draft["local_subject_ref"]:
            errors.append("missing local_subject_ref")
        if not draft["destination_program_ref"]:
            errors.append("missing destination_program_ref")
        draft["validation_errors"] = errors
        if not errors:
            draft["status"] = "ready"
        state = self._ensure_hmis_state()
        state.setdefault("enrollment_drafts", []).append(draft)
        self._save_hmis_state()
        self._hmis_audit_store().record(
            action_type="create_enrollment_draft",
            actor_id=actor_did,
            local_ref=draft["enrollment_draft_id"],
            adapter_name="manual-review",
            status="success",
            response_summary="created HMIS enrollment draft",
            metadata={"wallet_id": wallet_id, "status": draft["status"]},
        )
        return draft

    def submit_hmis_enrollment_draft(
        self,
        wallet_id: str,
        enrollment_draft_id: str,
        *,
        actor_did: str,
    ) -> dict[str, Any]:
        from ..hmis.models import HmisConsentRecord

        self._require_portal_actor(wallet_id, actor_did)  # type: ignore[attr-defined]
        state = self._ensure_hmis_state()
        draft = next(
            (
                item
                for item in state.get("enrollment_drafts", [])
                if isinstance(item, Mapping) and item.get("enrollment_draft_id") == enrollment_draft_id and item.get("wallet_id") == wallet_id
            ),
            None,
        )
        if draft is None:
            raise ValueError("HMIS enrollment draft not found")
        errors = list(draft.get("validation_errors") or [])
        if errors:
            raise ValueError("HMIS enrollment draft has validation errors")
        consent = HmisConsentRecord(
            consent_id=f"consent-enroll-{wallet_id}",
            subject_ref=str(draft.get("local_subject_ref") or ""),
            status="active",
            basis="client_consent",
            purpose="HMIS enrollment submission",
            authorized_scopes=("hmis_submit_enrollment",),
            authorized_program_refs=(str(draft.get("destination_program_ref") or ""),),
            effective_at="2026-01-01T00:00:00+00:00",
        )
        result = self._hmis_submission_service().execute(
            action_type="submit_enrollment",
            payload={
                "local_ref": enrollment_draft_id,
                "local_subject_ref": draft.get("local_subject_ref"),
                "destination_program_ref": draft.get("destination_program_ref"),
                "entry_date": draft.get("entry_date"),
                "household_ref": draft.get("household_ref"),
                "summary": draft.get("summary"),
            },
            actor_id=actor_did,
            consent=consent,
            required_scope="hmis_submit_enrollment",
        )
        now = _hmis_now()
        draft["updated_at"] = now
        if result.adapter_result.ok:
            draft["status"] = "submitted"
            draft["external_enrollment_id"] = (
                result.adapter_result.external_refs.get("enrollment_id")
                or result.adapter_result.external_refs.get("external_id")
                or ""
            )
        else:
            draft["status"] = "retryable" if result.adapter_result.retryable else "needs_review"
        state["enrollment_drafts"] = [
            draft if item.get("enrollment_draft_id") == enrollment_draft_id else item
            for item in state.get("enrollment_drafts", [])
        ]
        self._save_hmis_state()
        return {
            "status": draft["status"],
            "summary": result.adapter_result.summary,
            "enrollment_draft": dict(draft),
            "external_refs": dict(result.adapter_result.external_refs),
        }
