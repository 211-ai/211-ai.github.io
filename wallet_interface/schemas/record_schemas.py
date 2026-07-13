"""Wallet interface request schemas."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .base import BaseModel, Field
from .wallet_schemas import WalletRouterBaseRequest


class AddTextDocumentRequest(BaseModel):
    actor_did: str
    text: str
    filename: str = "document.txt"
    title: str | None = None
    key_hex: str | None = None


class AnalysisGrantRequest(BaseModel):
    issuer_did: str
    audience_did: str
    issuer_key_hex: str | None = None
    audience_key_hex: str | None = None
    expires_at: str | None = None


class RecordGrantRequest(BaseModel):
    issuer_did: str
    audience_did: str
    abilities: list[str] = Field(default_factory=lambda: ["record/analyze"])
    purpose: str = "service_matching"
    output_types: list[str] = Field(default_factory=list)
    user_presence_required: bool = False
    caveats: dict[str, Any] = Field(default_factory=dict)
    issuer_key_hex: str | None = None
    audience_key_hex: str | None = None
    approval_id: str | None = None
    expires_at: str | None = None
    max_delegation_depth: int | None = None


class AnalysisInvocationRequest(BaseModel):
    grant_id: str
    actor_did: str
    actor_key_hex: str | None = None
    expires_at: str | None = None
    purpose: str | None = None
    output_types: list[str] = Field(default_factory=list)
    user_present: bool = False


class AccessRequestCreateRequest(BaseModel):
    record_id: str
    requester_did: str
    ability: str = "record/analyze"
    audience_did: str | None = None
    purpose: str = "service_matching"
    expires_at: str | None = None


class AccessRequestDecisionRequest(BaseModel):
    actor_did: str
    issuer_key_hex: str | None = None
    audience_key_hex: str | None = None
    approval_id: str | None = None
    issue_invocation: bool = False
    invocation_expires_at: str | None = None
    reason: str | None = None


class ThresholdApprovalCreateRequest(BaseModel):
    requested_by: str
    operation: str = "grant/create"
    resources: list[str] = Field(default_factory=list)
    abilities: list[str] = Field(default_factory=list)
    expires_at: str | None = None


class ThresholdApprovalDecisionRequest(BaseModel):
    approver_did: str


class RevokeGrantRequest(BaseModel):
    actor_did: str


class EmergencyRevokeRequest(BaseModel):
    actor_did: str
    actor_key_hex: str | None = None
    approval_id: str | None = None
    rotate_keys: bool = True
    reason: str | None = None


class DelegateGrantRequest(BaseModel):
    issuer_did: str
    audience_did: str
    resources: list[str] = Field(default_factory=list)
    abilities: list[str] = Field(default_factory=list)
    caveats: dict[str, Any] = Field(default_factory=dict)
    expires_at: str | None = None
    issuer_key_hex: str | None = None
    audience_key_hex: str | None = None


class AnalyzeRecordRequest(BaseModel):
    actor_did: str
    actor_key_hex: str | None = None
    grant_id: str | None = None
    invocation_token: str | None = None
    max_chars: int = 200


class WalletRecordMetadataRequest(BaseModel):
    actor_did: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class DeleteWalletRecordRequest(BaseModel):
    actor_did: str
    unpin_ipfs: bool = True


class SavedServiceRequest(BaseModel):
    actor_did: str
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
    private_notes_record_id: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class SavedServiceUpdateRequest(BaseModel):
    actor_did: str
    source_content_cid: str | None = None
    source_page_cid: str | None = None
    title: str | None = None
    provider_name: str | None = None
    program_name: str | None = None
    source_url: str | None = None
    label: str | None = None
    reason: str | None = None
    priority: str | None = None
    status: str | None = None
    private_notes_record_id: str | None = None
    metadata: dict[str, Any] | None = None


class ServicePlanRequest(BaseModel):
    actor_did: str
    service_doc_id: str
    source_content_cid: str = ""
    source_page_cid: str = ""
    service_title: str = ""
    provider_name: str = ""
    goal: str = ""
    steps: list[str] = Field(default_factory=list)
    documents_needed: list[str] = Field(default_factory=list)
    questions_to_ask: list[str] = Field(default_factory=list)
    appointment_at: str = ""
    reminder_at: str = ""
    travel_target: str = ""
    assigned_worker_recipient_id: str = ""
    status: str = "active"
    related_interaction_ids: list[str] = Field(default_factory=list)
    private_notes_record_id: str = ""


class ServicePlanUpdateRequest(BaseModel):
    actor_did: str
    source_content_cid: str | None = None
    source_page_cid: str | None = None
    service_title: str | None = None
    provider_name: str | None = None
    goal: str | None = None
    steps: list[str] | None = None
    documents_needed: list[str] | None = None
    questions_to_ask: list[str] | None = None
    appointment_at: str | None = None
    reminder_at: str | None = None
    travel_target: str | None = None
    assigned_worker_recipient_id: str | None = None
    status: str | None = None
    related_interaction_ids: list[str] | None = None
    private_notes_record_id: str | None = None


class ServicePlanShareGrantRequest(BaseModel):
    actor_did: str = ""
    issuer_did: str = ""
    audience_did: str = ""
    worker_did: str = ""
    scopes: list[str] = Field(default_factory=lambda: ["service_summary"])
    purpose: str = "service_plan_collaboration"
    worker_recipient_id: str = ""
    worker_name: str = ""
    expires_at: str | None = None
    approval_id: str | None = None
    issuer_key_hex: str | None = None
    audience_key_hex: str | None = None
    caveats: dict[str, Any] = Field(default_factory=dict)


class ServiceInteractionRequest(BaseModel):
    actor_did: str
    service_doc_id: str
    source_content_cid: str = ""
    source_page_cid: str = ""
    provider_name: str = ""
    program_name: str = ""
    interaction_type: str
    channel: str = ""
    counterparty_name: str = ""
    counterparty_contact: str = ""
    timestamp: str = ""
    status: str = ""
    outcome: str = ""
    notes_record_id: str = ""
    next_action: str = ""
    next_follow_up_at: str = ""
    source_action_url: str = ""
    related_grant_ids: list[str] = Field(default_factory=list)
    related_record_ids: list[str] = Field(default_factory=list)
    privacy_level: str = "private"
    metadata: dict[str, Any] = Field(default_factory=dict)


class ServiceInteractionUpdateRequest(BaseModel):
    actor_did: str
    source_content_cid: str | None = None
    source_page_cid: str | None = None
    provider_name: str | None = None
    program_name: str | None = None
    channel: str | None = None
    counterparty_name: str | None = None
    counterparty_contact: str | None = None
    timestamp: str | None = None
    status: str | None = None
    outcome: str | None = None
    notes_record_id: str | None = None
    next_action: str | None = None
    next_follow_up_at: str | None = None
    source_action_url: str | None = None
    related_grant_ids: list[str] | None = None
    related_record_ids: list[str] | None = None
    privacy_level: str | None = None
    metadata: dict[str, Any] | None = None


class RedactedAnalyzeRecordRequest(BaseModel):
    actor_did: str
    actor_key_hex: str | None = None
    grant_id: str | None = None
    invocation_token: str | None = None
    max_chars: int = 500


class VectorProfileRequest(BaseModel):
    actor_did: str
    actor_key_hex: str | None = None
    grant_id: str | None = None
    invocation_token: str | None = None
    chunk_size_words: int = 80


class RedactedTextExtractionRequest(BaseModel):
    actor_did: str
    actor_key_hex: str | None = None
    grant_id: str | None = None
    invocation_token: str | None = None
    max_chars: int = 20_000
    max_bytes: int = 200_000
    use_ocr: bool = True


class RedactedFormAnalysisRequest(BaseModel):
    actor_did: str
    actor_key_hex: str | None = None
    grant_id: str | None = None
    invocation_token: str | None = None
    max_fields: int = 100
    use_ocr: bool = False


class RedactedAnalyzeRecordsRequest(BaseModel):
    actor_did: str
    actor_key_hex: str | None = None
    grant_id: str | None = None
    record_ids: list[str] = Field(default_factory=list)


class RedactedGraphRAGRequest(BaseModel):
    actor_did: str
    actor_key_hex: str | None = None
    grant_id: str | None = None
    invocation_token: str | None = None
    record_ids: list[str] = Field(default_factory=list)
    max_chars_per_record: int = 20_000
    max_bytes_per_record: int = 200_000
    use_ocr: bool = True


class WalletRecordMetadataGenerationRequest(WalletRouterBaseRequest):
    grant_id: str | None = None
    invocation_token: str | None = None
    file_name: str | None = None
    mime_type: str | None = None
    max_chars_per_record: int = 20_000
    max_bytes_per_record: int = 200_000
    use_ocr: bool = True


class DecryptRecordRequest(BaseModel):
    actor_did: str
    actor_key_hex: str | None = None
    grant_id: str | None = None
    invocation_token: str | None = None


class RotateRecordKeyRequest(BaseModel):
    actor_did: str
    actor_key_hex: str | None = None


class FilecoinRecordUploadRequest(BaseModel):
    actorDid: str
    actorKeyHex: str | None = None
    fileName: str | None = None
    grantId: str | None = None
    recordId: str
    walletId: str


class RepairStorageRequest(BaseModel):
    actor_did: str


class WalletServiceMatchRequest(BaseModel):
    location_record_id: str
    actor_did: str
    need_terms: Sequence[str] = Field(default_factory=list)
    grant_id: str | None = None
    invocation_token: str | None = None
    actor_key_hex: str | None = None
    limit: int = 10


class AnalyticsTemplateRequest(BaseModel):
    template_id: str
    title: str
    purpose: str
    allowed_record_types: list[str] = Field(default_factory=list)
    allowed_derived_fields: list[str] = Field(default_factory=list)
    min_cohort_size: int = 10
    epsilon_budget: float = 1.0
    created_by: str
    status: str = "approved"
    expires_at: str | None = None


class AnalyticsConsentFromTemplateRequest(BaseModel):
    actor_did: str
    template_id: str
    expires_at: str | None = None


class AnalyticsConsentRevokeRequest(BaseModel):
    actor_did: str


class AnalyticsContributionRequest(BaseModel):
    actor_did: str
    consent_id: str
    template_id: str
    fields: dict[str, Any]


class PrivateAggregateCountRequest(BaseModel):
    epsilon: float
    min_cohort_size: int | None = None
    budget_key: str | None = None
    budget_limit: float | None = None
    actor_did: str = "did:service:211-ai-api"


class PrivateAggregateCohortCountRequest(BaseModel):
    group_by: list[str] = Field(default_factory=list)
    epsilon: float | None = None
    min_cohort_size: int | None = None
    budget_key: str | None = None
    budget_limit: float | None = None
    actor_did: str = "did:service:211-ai-api"


class DerivedServiceMatchRequest(BaseModel):
    need_terms: Sequence[str] = Field(default_factory=list)
    location_claim: dict[str, Any] | None = None
    limit: int = 10


__all__ = [
    "AddTextDocumentRequest",
    "AnalysisGrantRequest",
    "RecordGrantRequest",
    "AnalysisInvocationRequest",
    "AccessRequestCreateRequest",
    "AccessRequestDecisionRequest",
    "ThresholdApprovalCreateRequest",
    "ThresholdApprovalDecisionRequest",
    "RevokeGrantRequest",
    "EmergencyRevokeRequest",
    "DelegateGrantRequest",
    "AnalyzeRecordRequest",
    "WalletRecordMetadataRequest",
    "DeleteWalletRecordRequest",
    "SavedServiceRequest",
    "SavedServiceUpdateRequest",
    "ServicePlanRequest",
    "ServicePlanUpdateRequest",
    "ServicePlanShareGrantRequest",
    "ServiceInteractionRequest",
    "ServiceInteractionUpdateRequest",
    "RedactedAnalyzeRecordRequest",
    "VectorProfileRequest",
    "RedactedTextExtractionRequest",
    "RedactedFormAnalysisRequest",
    "RedactedAnalyzeRecordsRequest",
    "RedactedGraphRAGRequest",
    "WalletRecordMetadataGenerationRequest",
    "DecryptRecordRequest",
    "RotateRecordKeyRequest",
    "FilecoinRecordUploadRequest",
    "RepairStorageRequest",
    "WalletServiceMatchRequest",
    "AnalyticsTemplateRequest",
    "AnalyticsConsentFromTemplateRequest",
    "AnalyticsConsentRevokeRequest",
    "AnalyticsContributionRequest",
    "PrivateAggregateCountRequest",
    "PrivateAggregateCohortCountRequest",
    "DerivedServiceMatchRequest",
]
