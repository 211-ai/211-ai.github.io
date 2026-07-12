"""Application record dataclasses for wallet interface state."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Sequence

def _unique_strings(values: Sequence[str] | None) -> List[str]:
    seen: set[str] = set()
    result: List[str] = []
    for value in values or []:
        item = str(value or "").strip()
        if not item or item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result

class SavedServiceRecord:
    saved_service_id: str
    wallet_id: str
    service_doc_id: str
    source_content_cid: str
    source_page_cid: str = ""
    title: str = ""
    provider_name: str = ""
    program_name: str = ""
    source_url: str = ""
    label: str = ""
    reason: str = ""
    priority: str = "normal"
    status: str = "saved"
    created_at: str = ""
    updated_at: str = ""
    private_notes_record_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "saved_service_id": self.saved_service_id,
            "wallet_id": self.wallet_id,
            "service_doc_id": self.service_doc_id,
            "source_content_cid": self.source_content_cid,
            "source_page_cid": self.source_page_cid,
            "title": self.title,
            "provider_name": self.provider_name,
            "program_name": self.program_name,
            "source_url": self.source_url,
            "label": self.label,
            "reason": self.reason,
            "priority": self.priority,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "private_notes_record_id": self.private_notes_record_id,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SavedServiceRecord":
        return cls(
            saved_service_id=str(payload.get("saved_service_id") or ""),
            wallet_id=str(payload.get("wallet_id") or ""),
            service_doc_id=str(payload.get("service_doc_id") or ""),
            source_content_cid=str(payload.get("source_content_cid") or ""),
            source_page_cid=str(payload.get("source_page_cid") or ""),
            title=str(payload.get("title") or ""),
            provider_name=str(payload.get("provider_name") or ""),
            program_name=str(payload.get("program_name") or ""),
            source_url=str(payload.get("source_url") or ""),
            label=str(payload.get("label") or ""),
            reason=str(payload.get("reason") or ""),
            priority=str(payload.get("priority") or "normal"),
            status=str(payload.get("status") or "saved"),
            created_at=str(payload.get("created_at") or ""),
            updated_at=str(payload.get("updated_at") or ""),
            private_notes_record_id=str(payload.get("private_notes_record_id") or ""),
            metadata=dict(payload.get("metadata") or {}),
        )


class ServicePlanRecord:
    plan_id: str
    wallet_id: str
    service_doc_id: str
    source_content_cid: str = ""
    source_page_cid: str = ""
    service_title: str = ""
    provider_name: str = ""
    goal: str = ""
    steps: List[str] = field(default_factory=list)
    documents_needed: List[str] = field(default_factory=list)
    questions_to_ask: List[str] = field(default_factory=list)
    appointment_at: str = ""
    reminder_at: str = ""
    travel_target: str = ""
    assigned_worker_recipient_id: str = ""
    status: str = "active"
    related_interaction_ids: List[str] = field(default_factory=list)
    private_notes_record_id: str = ""
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "wallet_id": self.wallet_id,
            "service_doc_id": self.service_doc_id,
            "source_content_cid": self.source_content_cid,
            "source_page_cid": self.source_page_cid,
            "service_title": self.service_title,
            "provider_name": self.provider_name,
            "goal": self.goal,
            "steps": list(self.steps),
            "documents_needed": list(self.documents_needed),
            "questions_to_ask": list(self.questions_to_ask),
            "appointment_at": self.appointment_at,
            "reminder_at": self.reminder_at,
            "travel_target": self.travel_target,
            "assigned_worker_recipient_id": self.assigned_worker_recipient_id,
            "status": self.status,
            "related_interaction_ids": list(self.related_interaction_ids),
            "private_notes_record_id": self.private_notes_record_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ServicePlanRecord":
        return cls(
            plan_id=str(payload.get("plan_id") or ""),
            wallet_id=str(payload.get("wallet_id") or ""),
            service_doc_id=str(payload.get("service_doc_id") or ""),
            source_content_cid=str(payload.get("source_content_cid") or ""),
            source_page_cid=str(payload.get("source_page_cid") or ""),
            service_title=str(payload.get("service_title") or ""),
            provider_name=str(payload.get("provider_name") or ""),
            goal=str(payload.get("goal") or ""),
            steps=_unique_strings(payload.get("steps") or []),
            documents_needed=_unique_strings(payload.get("documents_needed") or []),
            questions_to_ask=_unique_strings(payload.get("questions_to_ask") or []),
            appointment_at=str(payload.get("appointment_at") or ""),
            reminder_at=str(payload.get("reminder_at") or ""),
            travel_target=str(payload.get("travel_target") or ""),
            assigned_worker_recipient_id=str(payload.get("assigned_worker_recipient_id") or ""),
            status=str(payload.get("status") or "active"),
            related_interaction_ids=_unique_strings(payload.get("related_interaction_ids") or []),
            private_notes_record_id=str(payload.get("private_notes_record_id") or ""),
            created_at=str(payload.get("created_at") or ""),
            updated_at=str(payload.get("updated_at") or ""),
        )


class ServiceInteractionRecord:
    interaction_id: str
    wallet_id: str
    service_doc_id: str
    source_content_cid: str = ""
    source_page_cid: str = ""
    provider_name: str = ""
    program_name: str = ""
    interaction_type: str = ""
    channel: str = ""
    actor_did: str = ""
    counterparty_name: str = ""
    counterparty_contact: str = ""
    timestamp: str = ""
    status: str = ""
    outcome: str = ""
    notes_record_id: str = ""
    next_action: str = ""
    next_follow_up_at: str = ""
    source_action_url: str = ""
    related_grant_ids: List[str] = field(default_factory=list)
    related_record_ids: List[str] = field(default_factory=list)
    privacy_level: str = "private"
    created_at: str = ""
    updated_at: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "interaction_id": self.interaction_id,
            "wallet_id": self.wallet_id,
            "service_doc_id": self.service_doc_id,
            "source_content_cid": self.source_content_cid,
            "source_page_cid": self.source_page_cid,
            "provider_name": self.provider_name,
            "program_name": self.program_name,
            "interaction_type": self.interaction_type,
            "channel": self.channel,
            "actor_did": self.actor_did,
            "counterparty_name": self.counterparty_name,
            "counterparty_contact": self.counterparty_contact,
            "timestamp": self.timestamp,
            "status": self.status,
            "outcome": self.outcome,
            "notes_record_id": self.notes_record_id,
            "next_action": self.next_action,
            "next_follow_up_at": self.next_follow_up_at,
            "source_action_url": self.source_action_url,
            "related_grant_ids": list(self.related_grant_ids),
            "related_record_ids": list(self.related_record_ids),
            "privacy_level": self.privacy_level,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ServiceInteractionRecord":
        return cls(
            interaction_id=str(payload.get("interaction_id") or ""),
            wallet_id=str(payload.get("wallet_id") or ""),
            service_doc_id=str(payload.get("service_doc_id") or ""),
            source_content_cid=str(payload.get("source_content_cid") or ""),
            source_page_cid=str(payload.get("source_page_cid") or ""),
            provider_name=str(payload.get("provider_name") or ""),
            program_name=str(payload.get("program_name") or ""),
            interaction_type=str(payload.get("interaction_type") or ""),
            channel=str(payload.get("channel") or ""),
            actor_did=str(payload.get("actor_did") or ""),
            counterparty_name=str(payload.get("counterparty_name") or ""),
            counterparty_contact=str(payload.get("counterparty_contact") or ""),
            timestamp=str(payload.get("timestamp") or ""),
            status=str(payload.get("status") or ""),
            outcome=str(payload.get("outcome") or ""),
            notes_record_id=str(payload.get("notes_record_id") or ""),
            next_action=str(payload.get("next_action") or ""),
            next_follow_up_at=str(payload.get("next_follow_up_at") or ""),
            source_action_url=str(payload.get("source_action_url") or ""),
            related_grant_ids=_unique_strings(payload.get("related_grant_ids") or []),
            related_record_ids=_unique_strings(payload.get("related_record_ids") or []),
            privacy_level=str(payload.get("privacy_level") or "private"),
            created_at=str(payload.get("created_at") or ""),
            updated_at=str(payload.get("updated_at") or ""),
            metadata=dict(payload.get("metadata") or {}),
        )


__all__ = ["SavedServiceRecord", "ServicePlanRecord", "ServiceInteractionRecord"]
