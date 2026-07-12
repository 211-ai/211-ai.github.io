"""Portal interaction helpers for WalletInterfaceService."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timezone
from typing import Any, Dict, List
from uuid import uuid4

from .._vendor import ensure_ipfs_datasets_py_path

ensure_ipfs_datasets_py_path()

from ipfs_datasets_py.wallet.ucan import resource_for_wallet

from ..schemas.app_schemas import SavedServiceRecord, ServiceInteractionRecord, ServicePlanRecord


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()

def _portal_now() -> str:
    return _utc_now()

def _portal_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex}"

def _unique_strings(values: Sequence[str] | None) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values or []:
        item = str(value or "").strip()
        if not item or item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result

def _portal_resource(wallet_id: str, collection: str, entry_id: str) -> str:
    return f"{resource_for_wallet(wallet_id)}/portal/{collection}/{entry_id}"

class InteractionDomainServiceMixin:
    def save_service_for_wallet(
        self,
        wallet_id: str,
        *,
        actor_did: str,
        service_doc_id: str,
        source_content_cid: str,
        source_page_cid: str = "",
        title: str = "",
        provider_name: str = "",
        program_name: str = "",
        source_url: str = "",
        label: str = "",
        reason: str = "",
        priority: str = "normal",
        status: str = "saved",
        private_notes_record_id: str = "",
        metadata: Mapping[str, Any] | None = None,
    ) -> SavedServiceRecord:
        self._require_portal_actor(wallet_id, actor_did)
        service_doc = str(service_doc_id or "").strip()
        content_cid = str(source_content_cid or "").strip()
        if not service_doc:
            raise ValueError("service_doc_id is required")
        if not content_cid:
            raise ValueError("source_content_cid is required")
        now = _portal_now()
        existing = next(
            (
                record
                for record in self.saved_services.values()
                if record.wallet_id == wallet_id and record.service_doc_id == service_doc
            ),
            None,
        )
        record = SavedServiceRecord(
            saved_service_id=existing.saved_service_id if existing is not None else _portal_id("saved-service"),
            wallet_id=wallet_id,
            service_doc_id=service_doc,
            source_content_cid=content_cid,
            source_page_cid=str(source_page_cid or (existing.source_page_cid if existing else "")),
            title=str(title or (existing.title if existing else "")),
            provider_name=str(provider_name or (existing.provider_name if existing else "")),
            program_name=str(program_name or (existing.program_name if existing else "")),
            source_url=str(source_url or (existing.source_url if existing else "")),
            label=str(label or (existing.label if existing else "")),
            reason=str(reason or (existing.reason if existing else "")),
            priority=str(priority or (existing.priority if existing else "normal")),
            status=str(status or (existing.status if existing else "saved")),
            created_at=existing.created_at if existing is not None else now,
            updated_at=now,
            private_notes_record_id=str(
                private_notes_record_id or (existing.private_notes_record_id if existing else "")
            ),
            metadata={**(existing.metadata if existing else {}), **dict(metadata or {})},
        )
        self.saved_services[record.saved_service_id] = record
        self._portal_audit(
            wallet_id,
            actor_did=actor_did,
            action="service/save" if existing is None else "service/update",
            resource=_portal_resource(wallet_id, "saved-services", record.saved_service_id),
            details={
                "service_doc_id": record.service_doc_id,
                "status": record.status,
                "priority": record.priority,
            },
        )
        self._persist_wallet_if_configured(wallet_id)
        return record


    def update_saved_service(
        self,
        wallet_id: str,
        saved_service_id: str,
        *,
        actor_did: str,
        source_content_cid: str | None = None,
        source_page_cid: str | None = None,
        title: str | None = None,
        provider_name: str | None = None,
        program_name: str | None = None,
        source_url: str | None = None,
        label: str | None = None,
        reason: str | None = None,
        priority: str | None = None,
        status: str | None = None,
        private_notes_record_id: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> SavedServiceRecord:
        self._require_portal_actor(wallet_id, actor_did)
        record = self.saved_services.get(saved_service_id)
        if record is None or record.wallet_id != wallet_id:
            raise ValueError("saved service not found")
        if source_content_cid is not None:
            record.source_content_cid = str(source_content_cid or "")
        if source_page_cid is not None:
            record.source_page_cid = str(source_page_cid or "")
        if title is not None:
            record.title = str(title or "")
        if provider_name is not None:
            record.provider_name = str(provider_name or "")
        if program_name is not None:
            record.program_name = str(program_name or "")
        if source_url is not None:
            record.source_url = str(source_url or "")
        if label is not None:
            record.label = str(label or "")
        if reason is not None:
            record.reason = str(reason or "")
        if priority is not None:
            record.priority = str(priority or "")
        if status is not None:
            record.status = str(status or "")
        if private_notes_record_id is not None:
            record.private_notes_record_id = str(private_notes_record_id or "")
        if metadata is not None:
            record.metadata = {**record.metadata, **dict(metadata)}
        record.updated_at = _portal_now()
        self._portal_audit(
            wallet_id,
            actor_did=actor_did,
            action="service/update",
            resource=_portal_resource(wallet_id, "saved-services", record.saved_service_id),
            details={"service_doc_id": record.service_doc_id, "status": record.status},
        )
        self._persist_wallet_if_configured(wallet_id)
        return record


    def list_saved_services(self, wallet_id: str, *, status: str | None = None) -> list[SavedServiceRecord]:
        self.wallet_service._wallet(wallet_id)
        records = [record for record in self.saved_services.values() if record.wallet_id == wallet_id]
        if status is not None:
            records = [record for record in records if record.status == status]
        return sorted(records, key=lambda item: (item.updated_at or item.created_at, item.saved_service_id))


    def create_service_plan(
        self,
        wallet_id: str,
        *,
        actor_did: str,
        service_doc_id: str,
        source_content_cid: str = "",
        source_page_cid: str = "",
        service_title: str = "",
        provider_name: str = "",
        goal: str = "",
        steps: Sequence[str] | None = None,
        documents_needed: Sequence[str] | None = None,
        questions_to_ask: Sequence[str] | None = None,
        appointment_at: str = "",
        reminder_at: str = "",
        travel_target: str = "",
        assigned_worker_recipient_id: str = "",
        status: str = "active",
        related_interaction_ids: Sequence[str] | None = None,
        private_notes_record_id: str = "",
    ) -> ServicePlanRecord:
        self._require_portal_actor(wallet_id, actor_did)
        if not str(service_doc_id or "").strip():
            raise ValueError("service_doc_id is required")
        now = _portal_now()
        record = ServicePlanRecord(
            plan_id=_portal_id("service-plan"),
            wallet_id=wallet_id,
            service_doc_id=str(service_doc_id),
            source_content_cid=str(source_content_cid or ""),
            source_page_cid=str(source_page_cid or ""),
            service_title=str(service_title or ""),
            provider_name=str(provider_name or ""),
            goal=str(goal or ""),
            steps=_unique_strings(steps),
            documents_needed=_unique_strings(documents_needed),
            questions_to_ask=_unique_strings(questions_to_ask),
            appointment_at=str(appointment_at or ""),
            reminder_at=str(reminder_at or ""),
            travel_target=str(travel_target or ""),
            assigned_worker_recipient_id=str(assigned_worker_recipient_id or ""),
            status=str(status or "active"),
            related_interaction_ids=_unique_strings(related_interaction_ids),
            private_notes_record_id=str(private_notes_record_id or ""),
            created_at=now,
            updated_at=now,
        )
        self.service_plans[record.plan_id] = record
        self._portal_audit(
            wallet_id,
            actor_did=actor_did,
            action="service_plan/create",
            resource=_portal_resource(wallet_id, "plans", record.plan_id),
            details={"service_doc_id": record.service_doc_id, "status": record.status},
        )
        self._persist_wallet_if_configured(wallet_id)
        return record


    def update_service_plan(
        self,
        wallet_id: str,
        plan_id: str,
        *,
        actor_did: str,
        source_content_cid: str | None = None,
        source_page_cid: str | None = None,
        service_title: str | None = None,
        provider_name: str | None = None,
        goal: str | None = None,
        steps: Sequence[str] | None = None,
        documents_needed: Sequence[str] | None = None,
        questions_to_ask: Sequence[str] | None = None,
        appointment_at: str | None = None,
        reminder_at: str | None = None,
        travel_target: str | None = None,
        assigned_worker_recipient_id: str | None = None,
        status: str | None = None,
        related_interaction_ids: Sequence[str] | None = None,
        private_notes_record_id: str | None = None,
    ) -> ServicePlanRecord:
        self._require_portal_actor(wallet_id, actor_did)
        record = self.service_plans.get(plan_id)
        if record is None or record.wallet_id != wallet_id:
            raise ValueError("service plan not found")
        if source_content_cid is not None:
            record.source_content_cid = str(source_content_cid or "")
        if source_page_cid is not None:
            record.source_page_cid = str(source_page_cid or "")
        if service_title is not None:
            record.service_title = str(service_title or "")
        if provider_name is not None:
            record.provider_name = str(provider_name or "")
        if goal is not None:
            record.goal = str(goal or "")
        if steps is not None:
            record.steps = _unique_strings(steps)
        if documents_needed is not None:
            record.documents_needed = _unique_strings(documents_needed)
        if questions_to_ask is not None:
            record.questions_to_ask = _unique_strings(questions_to_ask)
        if appointment_at is not None:
            record.appointment_at = str(appointment_at or "")
        if reminder_at is not None:
            record.reminder_at = str(reminder_at or "")
        if travel_target is not None:
            record.travel_target = str(travel_target or "")
        if assigned_worker_recipient_id is not None:
            record.assigned_worker_recipient_id = str(assigned_worker_recipient_id or "")
        if status is not None:
            record.status = str(status or "")
        if related_interaction_ids is not None:
            record.related_interaction_ids = _unique_strings(related_interaction_ids)
        if private_notes_record_id is not None:
            record.private_notes_record_id = str(private_notes_record_id or "")
        record.updated_at = _portal_now()
        self._portal_audit(
            wallet_id,
            actor_did=actor_did,
            action="service_plan/update",
            resource=_portal_resource(wallet_id, "plans", record.plan_id),
            details={"service_doc_id": record.service_doc_id, "status": record.status},
        )
        self._persist_wallet_if_configured(wallet_id)
        return record


    def list_service_plans(
        self,
        wallet_id: str,
        *,
        service_doc_id: str | None = None,
        status: str | None = None,
    ) -> list[ServicePlanRecord]:
        self.wallet_service._wallet(wallet_id)
        records = [record for record in self.service_plans.values() if record.wallet_id == wallet_id]
        if service_doc_id is not None:
            records = [record for record in records if record.service_doc_id == service_doc_id]
        if status is not None:
            records = [record for record in records if record.status == status]
        return sorted(records, key=lambda item: (item.updated_at or item.created_at, item.plan_id))


    def create_service_interaction(
        self,
        wallet_id: str,
        *,
        actor_did: str,
        service_doc_id: str,
        source_content_cid: str = "",
        source_page_cid: str = "",
        provider_name: str = "",
        program_name: str = "",
        interaction_type: str,
        channel: str = "",
        counterparty_name: str = "",
        counterparty_contact: str = "",
        timestamp: str = "",
        status: str = "",
        outcome: str = "",
        notes_record_id: str = "",
        next_action: str = "",
        next_follow_up_at: str = "",
        source_action_url: str = "",
        related_grant_ids: Sequence[str] | None = None,
        related_record_ids: Sequence[str] | None = None,
        privacy_level: str = "private",
        metadata: Mapping[str, Any] | None = None,
    ) -> ServiceInteractionRecord:
        self._require_portal_actor(wallet_id, actor_did)
        if not str(service_doc_id or "").strip():
            raise ValueError("service_doc_id is required")
        if not str(interaction_type or "").strip():
            raise ValueError("interaction_type is required")
        now = _portal_now()
        record = ServiceInteractionRecord(
            interaction_id=_portal_id("interaction"),
            wallet_id=wallet_id,
            service_doc_id=str(service_doc_id),
            source_content_cid=str(source_content_cid or ""),
            source_page_cid=str(source_page_cid or ""),
            provider_name=str(provider_name or ""),
            program_name=str(program_name or ""),
            interaction_type=str(interaction_type),
            channel=str(channel or ""),
            actor_did=str(actor_did),
            counterparty_name=str(counterparty_name or ""),
            counterparty_contact=str(counterparty_contact or ""),
            timestamp=str(timestamp or now),
            status=str(status or ""),
            outcome=str(outcome or ""),
            notes_record_id=str(notes_record_id or ""),
            next_action=str(next_action or ""),
            next_follow_up_at=str(next_follow_up_at or ""),
            source_action_url=str(source_action_url or ""),
            related_grant_ids=_unique_strings(related_grant_ids),
            related_record_ids=_unique_strings(related_record_ids),
            privacy_level=str(privacy_level or "private"),
            created_at=now,
            updated_at=now,
            metadata=dict(metadata or {}),
        )
        self.service_interactions[record.interaction_id] = record
        self._portal_audit(
            wallet_id,
            actor_did=actor_did,
            action="interaction/create",
            resource=_portal_resource(wallet_id, "interactions", record.interaction_id),
            details={
                "service_doc_id": record.service_doc_id,
                "interaction_type": record.interaction_type,
                "channel": record.channel,
            },
        )
        self._persist_wallet_if_configured(wallet_id)
        return record


    def update_service_interaction(
        self,
        wallet_id: str,
        interaction_id: str,
        *,
        actor_did: str,
        source_content_cid: str | None = None,
        source_page_cid: str | None = None,
        provider_name: str | None = None,
        program_name: str | None = None,
        channel: str | None = None,
        counterparty_name: str | None = None,
        counterparty_contact: str | None = None,
        timestamp: str | None = None,
        status: str | None = None,
        outcome: str | None = None,
        notes_record_id: str | None = None,
        next_action: str | None = None,
        next_follow_up_at: str | None = None,
        source_action_url: str | None = None,
        related_grant_ids: Sequence[str] | None = None,
        related_record_ids: Sequence[str] | None = None,
        privacy_level: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> ServiceInteractionRecord:
        self._require_portal_actor(wallet_id, actor_did)
        record = self.service_interactions.get(interaction_id)
        if record is None or record.wallet_id != wallet_id:
            raise ValueError("service interaction not found")
        if source_content_cid is not None:
            record.source_content_cid = str(source_content_cid or "")
        if source_page_cid is not None:
            record.source_page_cid = str(source_page_cid or "")
        if provider_name is not None:
            record.provider_name = str(provider_name or "")
        if program_name is not None:
            record.program_name = str(program_name or "")
        if channel is not None:
            record.channel = str(channel or "")
        if counterparty_name is not None:
            record.counterparty_name = str(counterparty_name or "")
        if counterparty_contact is not None:
            record.counterparty_contact = str(counterparty_contact or "")
        if timestamp is not None:
            record.timestamp = str(timestamp or "")
        if status is not None:
            record.status = str(status or "")
        if outcome is not None:
            record.outcome = str(outcome or "")
        if notes_record_id is not None:
            record.notes_record_id = str(notes_record_id or "")
        if next_action is not None:
            record.next_action = str(next_action or "")
        if next_follow_up_at is not None:
            record.next_follow_up_at = str(next_follow_up_at or "")
        if source_action_url is not None:
            record.source_action_url = str(source_action_url or "")
        if related_grant_ids is not None:
            record.related_grant_ids = _unique_strings(related_grant_ids)
        if related_record_ids is not None:
            record.related_record_ids = _unique_strings(related_record_ids)
        if privacy_level is not None:
            record.privacy_level = str(privacy_level or "")
        if metadata is not None:
            record.metadata = {**record.metadata, **dict(metadata)}
        record.updated_at = _portal_now()
        self._portal_audit(
            wallet_id,
            actor_did=actor_did,
            action="interaction/update",
            resource=_portal_resource(wallet_id, "interactions", record.interaction_id),
            details={"service_doc_id": record.service_doc_id, "interaction_type": record.interaction_type},
        )
        self._persist_wallet_if_configured(wallet_id)
        return record


    def list_service_interactions(
        self,
        wallet_id: str,
        *,
        service_doc_id: str | None = None,
        interaction_type: str | None = None,
        status: str | None = None,
    ) -> list[ServiceInteractionRecord]:
        self.wallet_service._wallet(wallet_id)
        records = [record for record in self.service_interactions.values() if record.wallet_id == wallet_id]
        if service_doc_id is not None:
            records = [record for record in records if record.service_doc_id == service_doc_id]
        if interaction_type is not None:
            records = [record for record in records if record.interaction_type == interaction_type]
        if status is not None:
            records = [record for record in records if record.status == status]
        return sorted(records, key=lambda item: (item.timestamp or item.created_at, item.interaction_id))
