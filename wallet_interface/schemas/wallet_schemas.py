"""Wallet interface request schemas."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .base import BaseModel, Field

PORTLAND_POLICE_MISSING_EMAIL = "missing@police.portlandoregon.gov"

class CreateWalletRequest(BaseModel):
    owner_did: str
    controller_dids: list[str] = Field(default_factory=list)
    approval_threshold: int | None = None


class WalletControllerRequest(BaseModel):
    actor_did: str
    controller_did: str
    controller_key_hex: str | None = None
    approval_id: str | None = None


class WalletDeviceRequest(BaseModel):
    actor_did: str
    device_did: str
    device_key_hex: str | None = None
    approval_id: str | None = None


class WalletRecoveryPolicyRequest(BaseModel):
    actor_did: str
    contact_dids: list[str] = Field(default_factory=list)
    threshold: int = 1
    approval_id: str | None = None


class WalletControllerRecoveryRequest(BaseModel):
    actor_did: str
    controller_did: str
    controller_key_hex: str | None = None
    approval_id: str | None = None


class AddLocationRequest(BaseModel):
    actor_did: str
    lat: float
    lon: float


class HmisClientLookupRequest(BaseModel):
    actor_did: str
    name: str = ""
    date_of_birth: str = ""
    program_ref: str = ""


class HmisHouseholdLookupRequest(BaseModel):
    actor_did: str
    name: str = ""
    program_ref: str = ""


class HmisProgramLinkListRequest(BaseModel):
    actor_did: str
    name: str = ""
    program_ref: str = ""


class HmisReferralDraftRequest(BaseModel):
    actor_did: str
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
    metadata: dict[str, Any] = Field(default_factory=dict)


class HmisReferralDraftUpdateRequest(BaseModel):
    actor_did: str
    local_subject_ref: str | None = None
    destination_program_ref: str | None = None
    service_plan_id: str | None = None
    service_doc_id: str | None = None
    provider_name: str | None = None
    program_name: str | None = None
    summary: str | None = None
    eligibility_notes: str | None = None
    contact_notes: str | None = None
    source_content_cid: str | None = None
    source_page_cid: str | None = None
    metadata: dict[str, Any] | None = None


class HmisReferralDraftValidationRequest(BaseModel):
    actor_did: str


class HmisReferralDraftSubmitRequest(BaseModel):
    actor_did: str


class WalletRouterBaseRequest(BaseModel):
    actor_did: str
    actor_key_hex: str | None = None
    wallet_cid: str | None = None
    provider: str | None = "hf_inference_api"
    model_name: str | None = None
    kwargs: dict[str, Any] = Field(default_factory=dict)


class WalletEmbeddingsRouterRequest(WalletRouterBaseRequest):
    text: str | None = None
    texts: list[str] = Field(default_factory=list)


class WalletLlmRouterRequest(WalletRouterBaseRequest):
    prompt: str
    system_prompt: str | None = None
    max_new_tokens: int | None = 350


class WalletMultimodalRouterRequest(WalletRouterBaseRequest):
    prompt: str
    image_urls: list[str] = Field(default_factory=list)
    additional_text_blocks: list[str] = Field(default_factory=list)
    messages: list[dict[str, Any]] = Field(default_factory=list)
    image_detail: str | None = "auto"
    max_new_tokens: int | None = 350


class MissingPersonDeadDropEmailRequest(BaseModel):
    actor_did: str
    to_email: str = PORTLAND_POLICE_MISSING_EMAIL
    subject: str = "Missing person report dead drop bundle"
    body: str
    bundle: dict[str, Any]
    bundle_filename: str = "abby-missing-person-wallet-dead-drop.json"


class MissingPersonDeadDropConfigRequest(BaseModel):
    actor_did: str
    enabled: bool = False
    to_email: str = PORTLAND_POLICE_MISSING_EMAIL
    subject: str = "Missing person report dead drop bundle"
    body: str = ""
    bundle: dict[str, Any] = Field(default_factory=dict)
    bundle_filename: str = "abby-missing-person-wallet-dead-drop.json"
    due_at: str = ""
    last_check_in_at: str = ""


class MissingPersonDeadDropDispatchRequest(BaseModel):
    actor_did: str


class SmsNotificationQueueRequest(BaseModel):
    actor_did: str
    to_phone: str
    message: str
    due_at: str = ""
    reason: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class SmsNotificationDispatchRequest(BaseModel):
    actor_did: str


class InboundSmsForwardRequest(BaseModel):
    wallet_id: str
    from_phone: str
    message: str
    to_phone: str = ""
    provider: str = "unknown"
    status: str = "received"
    message_id: str = ""
    provider_message_id: str = ""
    external_reference: str = ""
    created_at: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class PhoneCallNotificationQueueRequest(BaseModel):
    actor_did: str
    to_phone: str
    script: str
    due_at: str = ""
    reason: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class PhoneCallNotificationDispatchRequest(BaseModel):
    actor_did: str


class MagicLoginRequest(BaseModel):
    contact: str
    portal: str = "client"
    wallet_id: str = ""
    wallet_api_base_url: str = ""
    actor_did: str = ""
    base_url: str = ""


class MagicLoginVerifyRequest(BaseModel):
    token: str


class WalletRecoveryBundleRequest(BaseModel):
    actor_did: str
    encrypted_bundle: dict[str, Any]
    wrapping_method: str = "passphrase"
    kdf: dict[str, Any] = Field(default_factory=dict)
    recovery_hint: str = ""
    public_metadata: dict[str, Any] = Field(default_factory=dict)


__all__ = [
    "CreateWalletRequest",
    "WalletControllerRequest",
    "WalletDeviceRequest",
    "WalletRecoveryPolicyRequest",
    "WalletControllerRecoveryRequest",
    "AddLocationRequest",
    "HmisClientLookupRequest",
    "HmisHouseholdLookupRequest",
    "HmisProgramLinkListRequest",
    "HmisReferralDraftRequest",
    "HmisReferralDraftUpdateRequest",
    "HmisReferralDraftValidationRequest",
    "HmisReferralDraftSubmitRequest",
    "WalletRouterBaseRequest",
    "WalletEmbeddingsRouterRequest",
    "WalletLlmRouterRequest",
    "WalletMultimodalRouterRequest",
    "MissingPersonDeadDropEmailRequest",
    "MissingPersonDeadDropConfigRequest",
    "MissingPersonDeadDropDispatchRequest",
    "SmsNotificationQueueRequest",
    "SmsNotificationDispatchRequest",
    "InboundSmsForwardRequest",
    "PhoneCallNotificationQueueRequest",
    "PhoneCallNotificationDispatchRequest",
    "MagicLoginRequest",
    "MagicLoginVerifyRequest",
    "WalletRecoveryBundleRequest",
]
