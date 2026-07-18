"""Service orchestration helpers for canonical HMIS adapter execution."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any
from uuid import uuid4

from .adapters.base import HmisAdapter
from .audit import HmisAuditStore
from .consent import HmisConsentDecision, evaluate_hmis_consent
from .errors import HmisPolicyError
from .models import HmisActionType, HmisAdapterResult, HmisConsentRecord, HmisSyncEvent


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()



def _payload_hash(payload: Mapping[str, Any]) -> str:
    try:
        normalized = json.loads(json.dumps(dict(payload), sort_keys=True, default=str))
    except TypeError:
        normalized = {key: str(value) for key, value in dict(payload).items()}
    encoded = json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(encoded).hexdigest()



def _action_supported(adapter: HmisAdapter, action_type: HmisActionType) -> bool:
    capabilities = adapter.capabilities()
    if action_type in {"lookup_client", "lookup_household", "list_program_links"}:
        return capabilities.supports_lookup
    if action_type in {"submit_referral"}:
        return capabilities.supports_referral_submit
    if action_type in {"submit_enrollment"}:
        return capabilities.supports_enrollment_submit
    if action_type in {"sync_referral_status", "resolve_reconciliation_item"}:
        return capabilities.supports_status_sync or capabilities.supports_reconciliation
    if action_type in {"create_referral_draft", "validate_referral_draft", "create_enrollment_draft"}:
        return capabilities.supports_manual_review_packets or capabilities.supports_referral_submit
    if action_type in {"link_external_record", "reject_match"}:
        return capabilities.supports_lookup
    return False


@dataclass(slots=True)
class HmisExecutionResult:
    adapter_result: HmisAdapterResult
    sync_event: HmisSyncEvent
    consent_decision: HmisConsentDecision | None = None


@dataclass(slots=True)
class HmisReferralDraftRecord:
    referral_draft_id: str
    wallet_id: str
    actor_id: str
    local_subject_ref: str
    destination_program_ref: str
    service_plan_id: str = ""
    service_doc_id: str = ""
    provider_name: str = ""
    program_name: str = ""
    summary: str = ""
    eligibility_notes: str = ""
    contact_notes: str = ""
    source_content_cid: str = ""
    source_page_cid: str = ""
    status: str = "draft"
    created_at: str = ""
    updated_at: str = ""
    validation_errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    external_referral_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "referral_draft_id": self.referral_draft_id,
            "wallet_id": self.wallet_id,
            "actor_id": self.actor_id,
            "local_subject_ref": self.local_subject_ref,
            "destination_program_ref": self.destination_program_ref,
            "service_plan_id": self.service_plan_id,
            "service_doc_id": self.service_doc_id,
            "provider_name": self.provider_name,
            "program_name": self.program_name,
            "summary": self.summary,
            "eligibility_notes": self.eligibility_notes,
            "contact_notes": self.contact_notes,
            "source_content_cid": self.source_content_cid,
            "source_page_cid": self.source_page_cid,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "validation_errors": list(self.validation_errors),
            "warnings": list(self.warnings),
            "external_referral_id": self.external_referral_id,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> HmisReferralDraftRecord:
        return cls(
            referral_draft_id=str(payload.get("referral_draft_id") or ""),
            wallet_id=str(payload.get("wallet_id") or ""),
            actor_id=str(payload.get("actor_id") or ""),
            local_subject_ref=str(payload.get("local_subject_ref") or ""),
            destination_program_ref=str(payload.get("destination_program_ref") or ""),
            service_plan_id=str(payload.get("service_plan_id") or ""),
            service_doc_id=str(payload.get("service_doc_id") or ""),
            provider_name=str(payload.get("provider_name") or ""),
            program_name=str(payload.get("program_name") or ""),
            summary=str(payload.get("summary") or ""),
            eligibility_notes=str(payload.get("eligibility_notes") or ""),
            contact_notes=str(payload.get("contact_notes") or ""),
            source_content_cid=str(payload.get("source_content_cid") or ""),
            source_page_cid=str(payload.get("source_page_cid") or ""),
            status=str(payload.get("status") or "draft"),
            created_at=str(payload.get("created_at") or ""),
            updated_at=str(payload.get("updated_at") or ""),
            validation_errors=[str(item) for item in payload.get("validation_errors") or []],
            warnings=[str(item) for item in payload.get("warnings") or []],
            external_referral_id=str(payload.get("external_referral_id") or ""),
            metadata=dict(payload.get("metadata") or {}),
        )


@dataclass(slots=True)
class HmisReconciliationItem:
    item_id: str
    wallet_id: str
    referral_draft_id: str
    local_ref: str
    status: str = "open"
    reason: str = ""
    retry_count: int = 0
    last_error: str = ""
    created_at: str = ""
    updated_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "wallet_id": self.wallet_id,
            "referral_draft_id": self.referral_draft_id,
            "local_ref": self.local_ref,
            "status": self.status,
            "reason": self.reason,
            "retry_count": self.retry_count,
            "last_error": self.last_error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> HmisReconciliationItem:
        return cls(
            item_id=str(payload.get("item_id") or ""),
            wallet_id=str(payload.get("wallet_id") or ""),
            referral_draft_id=str(payload.get("referral_draft_id") or ""),
            local_ref=str(payload.get("local_ref") or ""),
            status=str(payload.get("status") or "open"),
            reason=str(payload.get("reason") or ""),
            retry_count=int(payload.get("retry_count") or 0),
            last_error=str(payload.get("last_error") or ""),
            created_at=str(payload.get("created_at") or ""),
            updated_at=str(payload.get("updated_at") or ""),
            metadata=dict(payload.get("metadata") or {}),
        )


@dataclass(slots=True)
class HmisService:
    adapter: HmisAdapter
    audit_store: HmisAuditStore | None = None
    submission_results_by_hash: dict[str, HmisExecutionResult] = field(default_factory=dict)
    reconciliation_queue: list[HmisReconciliationItem] = field(default_factory=list)

    def execute(
        self,
        *,
        action_type: HmisActionType,
        payload: Mapping[str, Any],
        actor_id: str,
        consent: HmisConsentRecord | None = None,
        required_scope: str | None = None,
        program_ref: str | None = None,
        context: Mapping[str, Any] | None = None,
    ) -> HmisExecutionResult:
        if not _action_supported(self.adapter, action_type):
            raise HmisPolicyError(f"adapter {self.adapter.name} does not support action {action_type}")

        consent_decision = None
        if consent and required_scope:
            consent_decision = evaluate_hmis_consent(
                consent,
                required_scope=required_scope,
                program_ref=program_ref,
            )

        adapter_result = self.adapter.execute(action_type=action_type, payload=payload, context=context)
        sync_event = HmisSyncEvent(
            event_id=str(uuid4()),
            action_type=action_type,
            actor_id=actor_id,
            local_ref=str(payload.get("local_ref") or payload.get("local_subject_ref") or "") or None,
            external_ref=(
                adapter_result.external_refs.get("external_id")
                or adapter_result.external_refs.get("referral_id")
                or adapter_result.external_refs.get("batch_id")
            ),
            adapter_name=self.adapter.name,
            status=adapter_result.status,
            request_payload_hash=_payload_hash(payload),
            response_summary=adapter_result.summary,
            occurred_at=_utc_now(),
            metadata={
                "retryable": adapter_result.retryable,
                "warnings": list(adapter_result.warnings),
                **({"wallet_id": str(payload["wallet_id"])} if payload.get("wallet_id") else {}),
            },
        )
        if self.audit_store is not None:
            self.audit_store.emit(sync_event)
        return HmisExecutionResult(
            adapter_result=adapter_result,
            sync_event=sync_event,
            consent_decision=consent_decision,
        )

    def validate_referral_draft(
        self,
        draft: HmisReferralDraftRecord,
        *,
        required_fields: Sequence[str] = ("local_subject_ref", "destination_program_ref", "summary"),
    ) -> tuple[list[str], list[str]]:
        errors: list[str] = []
        warnings: list[str] = []
        for field_name in required_fields:
            if not str(getattr(draft, field_name, "") or "").strip():
                errors.append(f"missing {field_name}")
        if not draft.provider_name:
            warnings.append("provider_name is recommended for staff review")
        if not draft.program_name:
            warnings.append("program_name is recommended for staff review")
        return errors, warnings

    def submit_referral(
        self,
        draft: HmisReferralDraftRecord,
        *,
        actor_id: str,
        consent: HmisConsentRecord | None = None,
        required_scope: str | None = None,
        max_retries: int = 1,
        context: Mapping[str, Any] | None = None,
    ) -> HmisExecutionResult:
        payload = {
            "wallet_id": draft.wallet_id,
            "local_ref": draft.referral_draft_id,
            "local_subject_ref": draft.local_subject_ref,
            "destination_program_ref": draft.destination_program_ref,
            "service_plan_id": draft.service_plan_id,
            "service_doc_id": draft.service_doc_id,
            "provider_name": draft.provider_name,
            "program_name": draft.program_name,
            "summary": draft.summary,
            "eligibility_notes": draft.eligibility_notes,
            "contact_notes": draft.contact_notes,
            "submitted_at": _utc_now(),
            "metadata": dict(draft.metadata),
        }
        payload_hash = _payload_hash(payload)
        if payload_hash in self.submission_results_by_hash:
            existing = self.submission_results_by_hash[payload_hash]
            return HmisExecutionResult(
                adapter_result=HmisAdapterResult.success(
                    action_type="submit_referral",
                    adapter_name=existing.adapter_result.adapter_name,
                    summary="duplicate submission prevented; returning prior result",
                    external_refs=existing.adapter_result.external_refs,
                    normalized_payload=existing.adapter_result.normalized_payload,
                    warnings=("duplicate payload prevented",),
                ),
                sync_event=existing.sync_event,
                consent_decision=existing.consent_decision,
            )

        last_result: HmisExecutionResult | None = None
        for attempt in range(max_retries + 1):
            result = self.execute(
                action_type="submit_referral",
                payload=payload,
                actor_id=actor_id,
                consent=consent,
                required_scope=required_scope,
                program_ref=draft.destination_program_ref,
                context=context,
            )
            result.sync_event.retry_count = attempt
            if self.audit_store is not None:
                self.audit_store.emit(result.sync_event)
            last_result = result
            if result.adapter_result.ok or not result.adapter_result.retryable:
                break
        assert last_result is not None
        self.submission_results_by_hash[payload_hash] = last_result
        if last_result.adapter_result.reconciliation_required or last_result.adapter_result.retryable:
            self.enqueue_reconciliation(
                wallet_id=draft.wallet_id,
                referral_draft_id=draft.referral_draft_id,
                local_ref=draft.referral_draft_id,
                reason=last_result.adapter_result.summary,
                metadata={"errors": list(last_result.adapter_result.errors)},
            )
        return last_result

    def enqueue_reconciliation(
        self,
        *,
        wallet_id: str,
        referral_draft_id: str,
        local_ref: str,
        reason: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> HmisReconciliationItem:
        now = _utc_now()
        item = HmisReconciliationItem(
            item_id=f"recon-{uuid4().hex}",
            wallet_id=wallet_id,
            referral_draft_id=referral_draft_id,
            local_ref=local_ref,
            reason=reason,
            created_at=now,
            updated_at=now,
            metadata=dict(metadata or {}),
        )
        self.reconciliation_queue.append(item)
        return item

    def list_reconciliation_items(self, *, status: str | None = None) -> list[HmisReconciliationItem]:
        items = list(self.reconciliation_queue)
        if status is not None:
            items = [item for item in items if item.status == status]
        return sorted(items, key=lambda item: (item.updated_at, item.item_id))

    def retry_reconciliation_item(
        self,
        item: HmisReconciliationItem,
        *,
        actor_id: str,
        context: Mapping[str, Any] | None = None,
    ) -> HmisExecutionResult:
        payload = {"local_ref": item.local_ref, "local_referral_ref": item.local_ref}
        result = self.execute(
            action_type="sync_referral_status",
            payload=payload,
            actor_id=actor_id,
            context=context,
        )
        item.retry_count += 1
        item.updated_at = _utc_now()
        if result.adapter_result.ok:
            item.status = "resolved"
            item.last_error = ""
        else:
            item.status = "open" if result.adapter_result.retryable else "needs_review"
            item.last_error = "; ".join(result.adapter_result.errors)
        return result


__all__ = [
    "HmisExecutionResult",
    "HmisReferralDraftRecord",
    "HmisReconciliationItem",
    "HmisService",
]
