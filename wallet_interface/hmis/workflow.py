"""Fallback HMIS workflow service used when full wallet dependencies are unavailable."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

try:  # pragma: no cover
    from fastapi import FastAPI, HTTPException
except Exception:  # pragma: no cover
    FastAPI = None  # type: ignore[assignment]
    HTTPException = None  # type: ignore[assignment]

from .adapters.file_exchange import FileExchangeHmisAdapter
from .adapters.manual_review import ManualReviewHmisAdapter
from .audit import HmisAuditStore
from .matching import match_hmis_clients, match_hmis_households
from .models import HmisConsentRecord
from .service import HmisReconciliationItem, HmisReferralDraftRecord, HmisService


def _now() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).isoformat()


DEFAULT_FIXTURE_ROOT = Path("tests/fixtures/hmis")
PROGRAM_LINKS_PATH = Path("state/hmis/program_links.json")


@dataclass(slots=True)
class SimpleWallet:
    wallet_id: str
    owner_did: str
    controller_dids: list[str] = field(default_factory=list)
    device_dids: list[str] = field(default_factory=list)


class HmisWorkflowService:
    def __init__(self, *, repository_root: str | Path | None = None) -> None:
        self.repository_root = Path(repository_root or Path.cwd())
        self.repository_root.mkdir(parents=True, exist_ok=True)
        self.wallets: dict[str, SimpleWallet] = {}
        self.audit_store = HmisAuditStore(path=self.repository_root / "hmis-audit.jsonl")
        self.submission_service = HmisService(
            adapter=FileExchangeHmisAdapter(staging_dir=self.repository_root / "data" / "hmis"),
            audit_store=self.audit_store,
        )
        self._fixture_imports: list[dict[str, Any]] = []
        self._state = self._load_state()
        self.submission_service.reconciliation_queue = [
            HmisReconciliationItem.from_dict(item)
            for item in self._state.get("reconciliation_items", [])
            if isinstance(item, Mapping)
        ]

    def _state_path(self) -> Path:
        return self.repository_root / "hmis-state.json"

    def _load_state(self) -> dict[str, Any]:
        path = self._state_path()
        if not path.exists():
            return {
                "wallets": [],
                "referral_drafts": [],
                "verified_links": [],
                "rejected_matches": [],
                "reconciliation_items": [],
                "enrollment_drafts": [],
            }
        payload = json.loads(path.read_text(encoding="utf-8"))
        for item in payload.get("wallets", []):
            wallet = SimpleWallet(**item)
            self.wallets[wallet.wallet_id] = wallet
        return payload

    def _save_state(self) -> None:
        self._state["wallets"] = [asdict(wallet) for wallet in self.wallets.values()]
        self._state["reconciliation_items"] = [item.to_dict() for item in self.submission_service.list_reconciliation_items()]
        self._state_path().write_text(json.dumps(self._state, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def _load_fixtures(self, name: str) -> list[dict[str, Any]]:
        path = DEFAULT_FIXTURE_ROOT / f"{name}.json"
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            return [dict(item) for item in payload if isinstance(item, Mapping)]
        return []

    def _manual_adapter(self) -> ManualReviewHmisAdapter:
        return ManualReviewHmisAdapter(fixtures=[*self._load_fixtures("clients"), *self._load_fixtures("households"), *self._load_fixtures("programs")])

    def _program_links(self) -> list[dict[str, Any]]:
        if not PROGRAM_LINKS_PATH.exists():
            return []
        payload = json.loads(PROGRAM_LINKS_PATH.read_text(encoding="utf-8"))
        return [dict(item) for item in payload.get("program_links", []) if isinstance(item, Mapping)]

    def create_wallet(self, owner_did: str, *, controller_dids: list[str] | None = None, approval_threshold: int | None = None) -> SimpleWallet:
        del approval_threshold
        wallet = SimpleWallet(wallet_id=f"wallet-{uuid4().hex}", owner_did=owner_did, controller_dids=list(controller_dids or []))
        self.wallets[wallet.wallet_id] = wallet
        self._save_state()
        return wallet

    def _wallet(self, wallet_id: str) -> SimpleWallet:
        if wallet_id not in self.wallets:
            raise ValueError("wallet not found")
        return self.wallets[wallet_id]

    def _require_portal_actor(self, wallet_id: str, actor_did: str) -> None:
        wallet = self._wallet(wallet_id)
        allowed = {wallet.owner_did, *wallet.controller_dids, *wallet.device_dids}
        if actor_did not in allowed:
            raise ValueError("actor_did is not authorized for this wallet")

    def _mask(self, record: Mapping[str, Any]) -> dict[str, Any]:
        masked = dict(record)
        if masked.get("name"):
            masked["name"] = " ".join(f"{part[:1]}***" for part in str(masked["name"]).split())
        if masked.get("household_name"):
            masked["household_name"] = " ".join(f"{part[:1]}***" for part in str(masked["household_name"]).split())
        if masked.get("phone"):
            masked["phone"] = "***-***-" + str(masked["phone"])[-4:]
        if masked.get("email"):
            local, _, domain = str(masked["email"]).partition("@")
            masked["email"] = f"{local[:1]}***@{domain}" if domain else "***"
        if masked.get("date_of_birth"):
            masked["date_of_birth"] = str(masked["date_of_birth"])[:4]
        masked["masked"] = True
        return masked

    def lookup_hmis_clients(self, wallet_id: str, *, actor_did: str, name: str = "", date_of_birth: str = "", program_ref: str = "") -> dict[str, Any]:
        self._require_portal_actor(wallet_id, actor_did)
        query = {"name": name, "date_of_birth": date_of_birth, "program_ref": program_ref}
        result = self._manual_adapter().execute(action_type="lookup_client", payload=query)
        rejected = [
            item["external_id"]
            for item in self._state.get("rejected_matches", [])
            if item.get("wallet_id") == wallet_id and item.get("entity_type") == "client"
        ]
        match = match_hmis_clients(query, result.normalized_payload.get("candidates", []), rejected_candidate_ids=rejected)
        self.audit_store.record(action_type="lookup_client", actor_id=actor_did, local_ref=wallet_id, status="success", response_summary=result.summary)
        return {
            "status": "ok",
            "summary": result.summary,
            "clients": [
                {**self._mask(item.record), "external_id": item.external_id, "score": item.score, "matched_fields": list(item.matched_fields)}
                for item in match.candidates
            ],
            "rejected_candidates": [
                {**self._mask(item.record), "external_id": item.external_id, "score": item.score, "matched_fields": list(item.matched_fields)}
                for item in match.rejected_candidates
            ],
            "decision": match.decision,
            "last_sync_at": _now(),
        }

    def lookup_hmis_households(self, wallet_id: str, *, actor_did: str, name: str = "", program_ref: str = "") -> dict[str, Any]:
        self._require_portal_actor(wallet_id, actor_did)
        query = {"name": name, "program_ref": program_ref}
        result = self._manual_adapter().execute(action_type="lookup_household", payload=query)
        match = match_hmis_households(query, result.normalized_payload.get("candidates", []))
        self.audit_store.record(action_type="lookup_household", actor_id=actor_did, local_ref=wallet_id, status="success", response_summary=result.summary)
        return {
            "status": "ok",
            "summary": result.summary,
            "households": [
                {**self._mask(item.record), "external_id": item.external_id, "score": item.score, "matched_fields": list(item.matched_fields)}
                for item in match.candidates
            ],
            "decision": match.decision,
            "last_sync_at": _now(),
        }

    def list_hmis_program_links(self, wallet_id: str, *, actor_did: str, name: str = "", program_ref: str = "") -> dict[str, Any]:
        self._require_portal_actor(wallet_id, actor_did)
        rows = []
        for item in self._program_links():
            if name and name.lower() not in json.dumps(item).lower():
                continue
            if program_ref and program_ref.lower() not in json.dumps(item).lower():
                continue
            rows.append(item)
        self.audit_store.record(action_type="list_program_links", actor_id=actor_did, local_ref=wallet_id, status="success", response_summary=f"returned {len(rows)} program links")
        return {"status": "ok", "summary": f"returned {len(rows)} program links", "program_links": rows, "programs": rows}

    def list_hmis_referral_drafts(self, wallet_id: str, *, status: str | None = None) -> list[HmisReferralDraftRecord]:
        self._wallet(wallet_id)
        drafts = [
            HmisReferralDraftRecord.from_dict(item)
            for item in self._state.get("referral_drafts", [])
            if isinstance(item, Mapping) and str(item.get("wallet_id") or "") == wallet_id
        ]
        if status is not None:
            drafts = [draft for draft in drafts if draft.status == status]
        return drafts

    def create_hmis_referral_draft(self, wallet_id: str, *, actor_did: str, local_subject_ref: str, destination_program_ref: str, service_plan_id: str = "", service_doc_id: str = "", provider_name: str = "", program_name: str = "", summary: str = "", eligibility_notes: str = "", contact_notes: str = "", source_content_cid: str = "", source_page_cid: str = "", metadata: Mapping[str, Any] | None = None) -> HmisReferralDraftRecord:
        self._require_portal_actor(wallet_id, actor_did)
        now = _now()
        draft = HmisReferralDraftRecord(
            referral_draft_id=f"hmis-referral-draft-{uuid4().hex}",
            wallet_id=wallet_id,
            actor_id=actor_did,
            local_subject_ref=local_subject_ref,
            destination_program_ref=destination_program_ref,
            service_plan_id=service_plan_id,
            service_doc_id=service_doc_id,
            provider_name=provider_name,
            program_name=program_name,
            summary=summary,
            eligibility_notes=eligibility_notes,
            contact_notes=contact_notes,
            source_content_cid=source_content_cid,
            source_page_cid=source_page_cid,
            created_at=now,
            updated_at=now,
            metadata=dict(metadata or {}),
        )
        errors, warnings = self.submission_service.validate_referral_draft(draft)
        draft.validation_errors = errors
        draft.warnings = warnings
        draft.status = "ready" if not errors else "draft"
        self._state.setdefault("referral_drafts", []).append(draft.to_dict())
        self._save_state()
        self.audit_store.record(action_type="create_referral_draft", actor_id=actor_did, local_ref=draft.referral_draft_id, status="success", response_summary="created HMIS referral draft")
        return draft

    def update_hmis_referral_draft(self, wallet_id: str, referral_draft_id: str, *, actor_did: str, local_subject_ref: str | None = None, destination_program_ref: str | None = None, service_plan_id: str | None = None, service_doc_id: str | None = None, provider_name: str | None = None, program_name: str | None = None, summary: str | None = None, eligibility_notes: str | None = None, contact_notes: str | None = None, source_content_cid: str | None = None, source_page_cid: str | None = None, metadata: Mapping[str, Any] | None = None) -> HmisReferralDraftRecord:
        draft = next((item for item in self.list_hmis_referral_drafts(wallet_id) if item.referral_draft_id == referral_draft_id), None)
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
                setattr(draft, field_name, value)
        if metadata is not None:
            draft.metadata = {**draft.metadata, **dict(metadata)}
        draft.updated_at = _now()
        errors, warnings = self.submission_service.validate_referral_draft(draft)
        draft.validation_errors = errors
        draft.warnings = warnings
        draft.status = "ready" if not errors else "draft"
        self._state["referral_drafts"] = [draft.to_dict() if item.get("referral_draft_id") == referral_draft_id else item for item in self._state.get("referral_drafts", [])]
        self._save_state()
        return draft

    def validate_hmis_referral_draft(self, wallet_id: str, referral_draft_id: str, *, actor_did: str) -> dict[str, Any]:
        draft = next((item for item in self.list_hmis_referral_drafts(wallet_id) if item.referral_draft_id == referral_draft_id), None)
        if draft is None:
            raise ValueError("HMIS referral draft not found")
        errors, warnings = self.submission_service.validate_referral_draft(draft)
        draft.validation_errors = errors
        draft.warnings = warnings
        draft.status = "ready" if not errors else "draft"
        self._state["referral_drafts"] = [draft.to_dict() if item.get("referral_draft_id") == referral_draft_id else item for item in self._state.get("referral_drafts", [])]
        self._save_state()
        self.audit_store.record(action_type="validate_referral_draft", actor_id=actor_did, local_ref=referral_draft_id, status="success", response_summary="validated HMIS referral draft")
        return {"status": draft.status, "errors": errors, "warnings": warnings, "referral_draft": draft.to_dict()}

    def submit_hmis_referral_draft(self, wallet_id: str, referral_draft_id: str, *, actor_did: str) -> dict[str, Any]:
        draft = next((item for item in self.list_hmis_referral_drafts(wallet_id) if item.referral_draft_id == referral_draft_id), None)
        if draft is None:
            raise ValueError("HMIS referral draft not found")
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
        result = self.submission_service.submit_referral(
            draft,
            actor_id=actor_did,
            consent=consent,
            required_scope="hmis_submit_referral",
            context={"imports": self._fixture_imports},
        )
        draft.status = "submitted" if result.adapter_result.ok else "retryable"
        draft.updated_at = _now()
        draft.external_referral_id = result.adapter_result.external_refs.get("referral_id") or result.adapter_result.external_refs.get("batch_id") or ""
        self._state["referral_drafts"] = [draft.to_dict() if item.get("referral_draft_id") == referral_draft_id else item for item in self._state.get("referral_drafts", [])]
        self._save_state()
        return {"status": draft.status, "summary": result.adapter_result.summary, "referral_draft": draft.to_dict(), "external_refs": dict(result.adapter_result.external_refs)}

    def verify_hmis_match(self, wallet_id: str, *, actor_did: str, entity_type: str, local_ref: str, external_id: str, confidence: float) -> dict[str, Any]:
        self._require_portal_actor(wallet_id, actor_did)
        record = {"wallet_id": wallet_id, "entity_type": entity_type, "local_ref": local_ref, "external_id": external_id, "confidence": confidence, "status": "verified", "reviewed_by": actor_did, "reviewed_at": _now()}
        self._state.setdefault("verified_links", []).append(record)
        self._save_state()
        self.audit_store.record(action_type="link_external_record", actor_id=actor_did, local_ref=local_ref, external_ref=external_id, status="success", response_summary="verified HMIS record link")
        return record

    def reject_hmis_match(self, wallet_id: str, *, actor_did: str, entity_type: str, local_ref: str, external_id: str, reason: str) -> dict[str, Any]:
        self._require_portal_actor(wallet_id, actor_did)
        record = {"wallet_id": wallet_id, "entity_type": entity_type, "local_ref": local_ref, "external_id": external_id, "reason": reason, "rejected_by": actor_did, "rejected_at": _now()}
        self._state.setdefault("rejected_matches", []).append(record)
        self._save_state()
        self.audit_store.record(action_type="reject_match", actor_id=actor_did, local_ref=local_ref, external_ref=external_id, status="success", response_summary="rejected HMIS match candidate")
        return record

    def list_hmis_sync_timeline(self, wallet_id: str, *, local_ref: str | None = None) -> dict[str, Any]:
        self._wallet(wallet_id)
        return {
            "status": "ok",
            "events": [asdict(event) for event in self.audit_store.list_events(local_ref=local_ref)]
        }

    def list_hmis_reconciliation_queue(self, wallet_id: str, *, status: str | None = None) -> dict[str, Any]:
        self._wallet(wallet_id)
        return {"status": "ok", "items": [item.to_dict() for item in self.submission_service.list_reconciliation_items(status=status) if item.wallet_id == wallet_id]}

    def retry_hmis_reconciliation_item(self, wallet_id: str, item_id: str, *, actor_did: str) -> dict[str, Any]:
        item = next((row for row in self.submission_service.list_reconciliation_items() if row.item_id == item_id and row.wallet_id == wallet_id), None)
        if item is None:
            raise ValueError("HMIS reconciliation item not found")
        result = self.submission_service.retry_reconciliation_item(item, actor_id=actor_did, context={"imports": self._fixture_imports})
        self._save_state()
        return {"status": item.status, "summary": result.adapter_result.summary, "item": item.to_dict(), "external_refs": dict(result.adapter_result.external_refs)}

    def run_hmis_reconciliation_job(self, *, dry_run: bool = False) -> dict[str, Any]:
        open_items = [item for item in self.submission_service.list_reconciliation_items() if item.status == "open"]
        resolved = 0
        reviewed = 0
        for item in open_items:
            if dry_run:
                continue
            result = self.submission_service.retry_reconciliation_item(item, actor_id="did:wallet:hmis-reconciliation", context={"imports": self._fixture_imports})
            if result.adapter_result.ok:
                resolved += 1
            elif item.status == "needs_review":
                reviewed += 1
        if not dry_run:
            self._save_state()
        queue_items = self.submission_service.list_reconciliation_items()
        return {
            "status": "dry-run" if dry_run else "ok",
            "queue_depth": len(queue_items),
            "open_count": sum(1 for item in queue_items if item.status == "open"),
            "resolved_count": sum(1 for item in queue_items if item.status == "resolved") if dry_run else resolved,
            "needs_review_count": sum(1 for item in queue_items if item.status == "needs_review") if dry_run else reviewed,
        }

    # Phase 5: Enrollment draft flows

    def list_hmis_enrollment_drafts(
        self, wallet_id: str, *, status: str | None = None
    ) -> list[dict[str, Any]]:
        self._wallet(wallet_id)  # ensure wallet exists
        drafts = [
            item
            for item in self._state.get("enrollment_drafts", [])
            if isinstance(item, Mapping) and item.get("wallet_id") == wallet_id
        ]
        if status is not None:
            drafts = [d for d in drafts if d.get("status") == status]
        return sorted(
            drafts,
            key=lambda d: (d.get("updated_at") or d.get("created_at") or "", d.get("enrollment_draft_id") or ""),
        )

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
        self._require_portal_actor(wallet_id, actor_did)
        now = _now()
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
        self._state.setdefault("enrollment_drafts", []).append(draft)
        self._save_state()
        return draft

    def submit_hmis_enrollment_draft(
        self,
        wallet_id: str,
        enrollment_draft_id: str,
        *,
        actor_did: str,
    ) -> dict[str, Any]:
        self._require_portal_actor(wallet_id, actor_did)
        draft = next(
            (
                d
                for d in self._state.get("enrollment_drafts", [])
                if isinstance(d, Mapping)
                and d.get("enrollment_draft_id") == enrollment_draft_id
                and d.get("wallet_id") == wallet_id
            ),
            None,
        )
        if draft is None:
            raise ValueError("HMIS enrollment draft not found")
        errors = list(draft.get("validation_errors") or [])
        if errors:
            raise ValueError("HMIS enrollment draft has validation errors")
        from .models import HmisConsentRecord
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
        result = self.submission_service.execute(
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
        now = _now()
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
        self._state["enrollment_drafts"] = [
            draft if d.get("enrollment_draft_id") == enrollment_draft_id else d
            for d in self._state.get("enrollment_drafts", [])
        ]
        self._save_state()
        return {
            "status": draft["status"],
            "summary": result.adapter_result.summary,
            "enrollment_draft": dict(draft),
            "external_refs": dict(result.adapter_result.external_refs),
        }


def create_app(*, service: HmisWorkflowService | None = None):
    if FastAPI is None:  # pragma: no cover
        raise RuntimeError("FastAPI is required to create the wallet interface API")
    app_service = service or HmisWorkflowService()
    app = FastAPI(title="211-AI HMIS Fallback API", version="0.1.0")

    @app.post("/wallets")
    def create_wallet(payload: dict[str, Any]) -> dict[str, Any]:
        wallet = app_service.create_wallet(str(payload.get("owner_did") or ""))
        return {"wallet_id": wallet.wallet_id}

    @app.post("/wallets/{wallet_id}/hmis/lookup-clients")
    def lookup_clients(wallet_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return app_service.lookup_hmis_clients(wallet_id, actor_did=str(payload.get("actor_did") or ""), name=str(payload.get("name") or ""), date_of_birth=str(payload.get("date_of_birth") or ""), program_ref=str(payload.get("program_ref") or ""))
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/hmis/lookup-households")
    def lookup_households(wallet_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return app_service.lookup_hmis_households(wallet_id, actor_did=str(payload.get("actor_did") or ""), name=str(payload.get("name") or ""), program_ref=str(payload.get("program_ref") or ""))
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/hmis/program-links")
    def program_links(wallet_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return app_service.list_hmis_program_links(wallet_id, actor_did=str(payload.get("actor_did") or ""), name=str(payload.get("name") or ""), program_ref=str(payload.get("program_ref") or ""))
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/wallets/{wallet_id}/hmis/referral-drafts")
    def referral_drafts(wallet_id: str, status: str | None = None) -> dict[str, Any]:
        try:
            return {"referral_drafts": [draft.to_dict() for draft in app_service.list_hmis_referral_drafts(wallet_id, status=status)]}
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/hmis/referral-drafts")
    def create_referral_draft(wallet_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return app_service.create_hmis_referral_draft(wallet_id, actor_did=str(payload.get("actor_did") or ""), local_subject_ref=str(payload.get("local_subject_ref") or ""), destination_program_ref=str(payload.get("destination_program_ref") or ""), service_plan_id=str(payload.get("service_plan_id") or ""), service_doc_id=str(payload.get("service_doc_id") or ""), provider_name=str(payload.get("provider_name") or ""), program_name=str(payload.get("program_name") or ""), summary=str(payload.get("summary") or ""), eligibility_notes=str(payload.get("eligibility_notes") or ""), contact_notes=str(payload.get("contact_notes") or ""), source_content_cid=str(payload.get("source_content_cid") or ""), source_page_cid=str(payload.get("source_page_cid") or ""), metadata=dict(payload.get("metadata") or {})).to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.patch("/wallets/{wallet_id}/hmis/referral-drafts/{referral_draft_id}")
    def update_referral_draft(wallet_id: str, referral_draft_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return app_service.update_hmis_referral_draft(wallet_id, referral_draft_id, actor_did=str(payload.get("actor_did") or ""), local_subject_ref=payload.get("local_subject_ref"), destination_program_ref=payload.get("destination_program_ref"), service_plan_id=payload.get("service_plan_id"), service_doc_id=payload.get("service_doc_id"), provider_name=payload.get("provider_name"), program_name=payload.get("program_name"), summary=payload.get("summary"), eligibility_notes=payload.get("eligibility_notes"), contact_notes=payload.get("contact_notes"), source_content_cid=payload.get("source_content_cid"), source_page_cid=payload.get("source_page_cid"), metadata=payload.get("metadata")).to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/hmis/referral-drafts/{referral_draft_id}/validate")
    def validate_referral_draft(wallet_id: str, referral_draft_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return app_service.validate_hmis_referral_draft(wallet_id, referral_draft_id, actor_did=str(payload.get("actor_did") or ""))
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/hmis/referral-drafts/{referral_draft_id}/submit")
    def submit_referral_draft(wallet_id: str, referral_draft_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return app_service.submit_hmis_referral_draft(wallet_id, referral_draft_id, actor_did=str(payload.get("actor_did") or ""))
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Phase 5: Enrollment draft endpoints

    @app.get("/wallets/{wallet_id}/hmis/enrollment-drafts")
    def list_enrollment_drafts(wallet_id: str, status: str | None = None) -> dict[str, Any]:
        try:
            return {"enrollment_drafts": app_service.list_hmis_enrollment_drafts(wallet_id, status=status)}
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/hmis/enrollment-drafts")
    def create_enrollment_draft(wallet_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return app_service.create_hmis_enrollment_draft(
                wallet_id,
                actor_did=str(payload.get("actor_did") or ""),
                local_subject_ref=str(payload.get("local_subject_ref") or ""),
                destination_program_ref=str(payload.get("destination_program_ref") or ""),
                entry_date=str(payload.get("entry_date") or ""),
                household_ref=str(payload.get("household_ref") or ""),
                summary=str(payload.get("summary") or ""),
                metadata=dict(payload.get("metadata") or {}),
            )
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/hmis/enrollment-drafts/{enrollment_draft_id}/submit")
    def submit_enrollment_draft(wallet_id: str, enrollment_draft_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return app_service.submit_hmis_enrollment_draft(wallet_id, enrollment_draft_id, actor_did=str(payload.get("actor_did") or ""))
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return app


__all__ = ["HmisWorkflowService", "SimpleWallet", "create_app"]
