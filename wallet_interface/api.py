"""FastAPI surface for 211-AI wallet workflows."""

from __future__ import annotations

import base64
import hashlib
import io
import json
import math
import mimetypes
import os
import re
import smtplib
import struct
import time
import uuid
import wave
from email.message import EmailMessage
from email.utils import make_msgid
from typing import Any, Dict, List, Mapping, Sequence
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

from .app_service import WalletInterfaceService

try:  # pragma: no cover - exercised when optional dependency is installed.
    from fastapi import FastAPI, File, Form, Header, HTTPException, Request, Response, UploadFile
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel, Field
except ImportError:  # pragma: no cover
    FastAPI = None  # type: ignore[assignment]
    CORSMiddleware = None  # type: ignore[assignment]
    File = None  # type: ignore[assignment]
    Form = None  # type: ignore[assignment]
    Header = None  # type: ignore[assignment]
    HTTPException = None  # type: ignore[assignment]
    Request = object  # type: ignore[assignment,misc]
    Response = object  # type: ignore[assignment,misc]
    UploadFile = object  # type: ignore[assignment,misc]
    BaseModel = object  # type: ignore[assignment,misc]

    def Field(default: Any = None, **_: Any) -> Any:  # type: ignore[no-redef]
        return default

from ._vendor import ensure_ipfs_datasets_py_path

ensure_ipfs_datasets_py_path()

from ipfs_datasets_py.ipfs_backend_router import get_ipfs_backend  # noqa: E402
from ipfs_datasets_py.utils.secrets import resolve_secret  # noqa: E402
from ipfs_datasets_py.wallet.ucan import invocation_from_token, invocation_to_token  # noqa: E402


PORTLAND_POLICE_MISSING_EMAIL = "missing@police.portlandoregon.gov"
OPS_DEAD_DROP_ACTOR_DID = "did:wallet:ops"
_IPFS_CID_PATTERN = re.compile(r"^(?:bafy[a-z0-9]{20,}|Qm[1-9A-HJ-NP-Za-km-z]{44})$")
_AI_ROUTER_RATE_LIMITS: Dict[str, Dict[str, Any]] = {}


class FilecoinPinHandoffError(RuntimeError):
    """Raised when the optional Filecoin Pin sidecar handoff fails."""


def _cors_origins_from_env() -> list[str]:
    origins = [
        origin.strip()
        for origin in os.environ.get("WALLET_API_CORS_ORIGINS", "").split(",")
        if origin.strip()
    ]
    return origins


def _prepare_hf_router_environment(kwargs: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Make encrypted HF credentials visible to ipfs_datasets_py router helpers."""
    token = (
        resolve_secret(
            "IPFS_DATASETS_PY_HF_API_TOKEN",
            "HF_TOKEN",
            "HUGGINGFACEHUB_API_TOKEN",
            "HUGGINGFACE_API_TOKEN",
            "HUGGINGFACE_HUB_TOKEN",
            "HF_API_TOKEN",
        )
        or ""
    ).strip()
    if token:
        for key in ("IPFS_DATASETS_PY_HF_API_TOKEN", "HF_TOKEN", "HUGGINGFACEHUB_API_TOKEN"):
            if not os.getenv(key, "").strip():
                os.environ[key] = token
    bill_to = (
        os.getenv("IPFS_DATASETS_PY_HF_BILL_TO")
        or os.getenv("HUGGINGFACE_BILL_TO")
        or os.getenv("HF_BILL_TO")
        or "publicus"
    ).strip()
    if bill_to:
        os.environ.setdefault("IPFS_DATASETS_PY_HF_BILL_TO", bill_to)
        os.environ.setdefault("HUGGINGFACE_BILL_TO", bill_to)
    router_kwargs = dict(kwargs or {})
    if bill_to:
        router_kwargs.setdefault("bill_to", bill_to)
        router_kwargs.setdefault("organization", bill_to)
    router_kwargs.setdefault("hf_provider", os.getenv("IPFS_DATASETS_PY_HF_PROVIDER", "auto"))
    return router_kwargs


def _normalize_ipfs_cid(value: str) -> str:
    normalized = str(value or "").strip()
    normalized = normalized.replace("ipfs://", "")
    normalized = re.sub(r"^/?ipfs/", "", normalized)
    normalized = normalized.split("/", 1)[0].strip()
    return normalized


def _valid_ipfs_cid(value: str) -> bool:
    return bool(_IPFS_CID_PATTERN.match(_normalize_ipfs_cid(value)))


def _ipfs_proxy_allowed_cids_from_env() -> set[str]:
    raw = str(os.getenv("WALLET_IPFS_PROXY_ALLOWED_CIDS") or "")
    return {
        normalized
        for part in re.split(r"[\s,]+", raw)
        if (normalized := _normalize_ipfs_cid(part))
    }


def _ipfs_proxy_allows_cid(cid: str) -> bool:
    normalized = _normalize_ipfs_cid(cid)
    allowed = _ipfs_proxy_allowed_cids_from_env()
    if not allowed:
        return True
    return normalized in allowed


def _ipfs_proxy_media_type(data: bytes) -> str:
    try:
        decoded = data.decode("utf-8")
        json.loads(decoded)
        return "application/json"
    except Exception:
        return "application/octet-stream"


def _ipfs_proxy_fallback_gateways() -> list[str]:
    configured = [
        gateway.strip().rstrip("/")
        for gateway in os.getenv("WALLET_IPFS_PROXY_FALLBACK_GATEWAYS", "").split(",")
        if gateway.strip()
    ]
    if configured:
        return configured
    return [
        "https://w3s.link/ipfs",
        "https://ipfs.io/ipfs",
        "https://dweb.link/ipfs",
    ]


def _fetch_ipfs_cid_via_gateway(cid: str) -> bytes:
    last_error: Exception | None = None
    for gateway in _ipfs_proxy_fallback_gateways():
        url = f"{gateway.rstrip('/')}/{urllib_parse.quote(cid, safe='')}"
        try:
            req = urllib_request.Request(url, headers={"Accept": "application/octet-stream,*/*"})
            with urllib_request.urlopen(req, timeout=30) as response:
                return response.read()
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"Unable to fetch CID from fallback gateways: {last_error}") from last_error


def _wallet_interface_service_from_env() -> WalletInterfaceService:
    services_jsonl = str(os.environ.get("WALLET_SERVICES_JSONL") or "").strip()
    if services_jsonl:
        return WalletInterfaceService.from_services_jsonl(services_jsonl)
    return WalletInterfaceService()


class CreateWalletRequest(BaseModel):
    owner_did: str
    controller_dids: List[str] = Field(default_factory=list)
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
    contact_dids: List[str] = Field(default_factory=list)
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


class CoarseLocationGrantRequest(BaseModel):
    issuer_did: str
    audience_did: str
    issuer_key_hex: str | None = None
    audience_key_hex: str | None = None
    expires_at: str | None = None


class CoarseLocationInvocationRequest(BaseModel):
    grant_id: str
    actor_did: str
    actor_key_hex: str | None = None
    expires_at: str | None = None
    purpose: str | None = None
    user_present: bool = False


class LocationRegionProofGrantRequest(BaseModel):
    issuer_did: str
    audience_did: str
    expires_at: str | None = None


class LocationRegionProofRequest(BaseModel):
    actor_did: str
    region_id: str
    grant_id: str | None = None


class LocationDistanceProofGrantRequest(BaseModel):
    issuer_did: str
    audience_did: str
    target_id: str
    max_distance_km: float
    expires_at: str | None = None


class LocationDistanceProofRequest(BaseModel):
    actor_did: str
    target_id: str
    target_lat: float
    target_lon: float
    max_distance_km: float
    grant_id: str | None = None


class DocumentPrivacyProfileProofRequest(BaseModel):
    actor_did: str
    public_inputs: Dict[str, Any] = Field(default_factory=dict)


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
    abilities: List[str] = Field(default_factory=lambda: ["record/analyze"])
    purpose: str = "service_matching"
    output_types: List[str] = Field(default_factory=list)
    user_presence_required: bool = False
    caveats: Dict[str, Any] = Field(default_factory=dict)
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
    output_types: List[str] = Field(default_factory=list)
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
    resources: List[str] = Field(default_factory=list)
    abilities: List[str] = Field(default_factory=list)
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
    resources: List[str] = Field(default_factory=list)
    abilities: List[str] = Field(default_factory=list)
    caveats: Dict[str, Any] = Field(default_factory=dict)
    expires_at: str | None = None
    issuer_key_hex: str | None = None
    audience_key_hex: str | None = None


class ExportGrantRequest(BaseModel):
    issuer_did: str
    audience_did: str
    record_ids: List[str] = Field(default_factory=list)
    issuer_key_hex: str | None = None
    audience_key_hex: str | None = None
    purpose: str = "user_export"
    expires_at: str | None = None
    approval_id: str | None = None
    output_types: List[str] = Field(default_factory=list)


class ExportBundleRequest(BaseModel):
    actor_did: str
    actor_key_hex: str | None = None
    grant_id: str | None = None
    invocation_token: str | None = None
    record_ids: List[str] = Field(default_factory=list)
    include_proofs: bool = True
    include_derived_artifacts: bool = True


class ExportBundleVerifyRequest(BaseModel):
    bundle: Dict[str, Any]


class ExportBundleImportRequest(BaseModel):
    bundle: Dict[str, Any]


class ExportBundleStorageRequest(BaseModel):
    bundle: Dict[str, Any]


class ExportInvocationRequest(BaseModel):
    grant_id: str
    actor_did: str
    actor_key_hex: str | None = None
    record_ids: List[str] = Field(default_factory=list)
    expires_at: str | None = None
    purpose: str | None = None
    output_types: List[str] = Field(default_factory=list)
    user_present: bool = False


class AnalyzeRecordRequest(BaseModel):
    actor_did: str
    actor_key_hex: str | None = None
    grant_id: str | None = None
    invocation_token: str | None = None
    max_chars: int = 200


class WalletRecordMetadataRequest(BaseModel):
    actor_did: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


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
    metadata: Dict[str, Any] = Field(default_factory=dict)


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
    metadata: Dict[str, Any] | None = None


class ServicePlanRequest(BaseModel):
    actor_did: str
    service_doc_id: str
    source_content_cid: str = ""
    source_page_cid: str = ""
    service_title: str = ""
    provider_name: str = ""
    goal: str = ""
    steps: List[str] = Field(default_factory=list)
    documents_needed: List[str] = Field(default_factory=list)
    questions_to_ask: List[str] = Field(default_factory=list)
    appointment_at: str = ""
    reminder_at: str = ""
    travel_target: str = ""
    assigned_worker_recipient_id: str = ""
    status: str = "active"
    related_interaction_ids: List[str] = Field(default_factory=list)
    private_notes_record_id: str = ""


class ServicePlanUpdateRequest(BaseModel):
    actor_did: str
    source_content_cid: str | None = None
    source_page_cid: str | None = None
    service_title: str | None = None
    provider_name: str | None = None
    goal: str | None = None
    steps: List[str] | None = None
    documents_needed: List[str] | None = None
    questions_to_ask: List[str] | None = None
    appointment_at: str | None = None
    reminder_at: str | None = None
    travel_target: str | None = None
    assigned_worker_recipient_id: str | None = None
    status: str | None = None
    related_interaction_ids: List[str] | None = None
    private_notes_record_id: str | None = None


class ServicePlanShareGrantRequest(BaseModel):
    actor_did: str = ""
    issuer_did: str = ""
    audience_did: str = ""
    worker_did: str = ""
    scopes: List[str] = Field(default_factory=lambda: ["service_summary"])
    purpose: str = "service_plan_collaboration"
    worker_recipient_id: str = ""
    worker_name: str = ""
    expires_at: str | None = None
    approval_id: str | None = None
    issuer_key_hex: str | None = None
    audience_key_hex: str | None = None
    caveats: Dict[str, Any] = Field(default_factory=dict)


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
    related_grant_ids: List[str] = Field(default_factory=list)
    related_record_ids: List[str] = Field(default_factory=list)
    privacy_level: str = "private"
    metadata: Dict[str, Any] = Field(default_factory=dict)


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
    related_grant_ids: List[str] | None = None
    related_record_ids: List[str] | None = None
    privacy_level: str | None = None
    metadata: Dict[str, Any] | None = None


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
    record_ids: List[str] = Field(default_factory=list)


class RedactedGraphRAGRequest(BaseModel):
    actor_did: str
    actor_key_hex: str | None = None
    grant_id: str | None = None
    invocation_token: str | None = None
    record_ids: List[str] = Field(default_factory=list)
    max_chars_per_record: int = 20_000
    max_bytes_per_record: int = 200_000
    use_ocr: bool = True


class WalletRouterBaseRequest(BaseModel):
    actor_did: str
    actor_key_hex: str | None = None
    wallet_cid: str | None = None
    provider: str | None = "hf_inference_api"
    model_name: str | None = None
    kwargs: Dict[str, Any] = Field(default_factory=dict)


class WalletEmbeddingsRouterRequest(WalletRouterBaseRequest):
    text: str | None = None
    texts: List[str] = Field(default_factory=list)


class WalletLlmRouterRequest(WalletRouterBaseRequest):
    prompt: str
    system_prompt: str | None = None
    max_new_tokens: int | None = 350


class WalletMultimodalRouterRequest(WalletRouterBaseRequest):
    prompt: str
    image_urls: List[str] = Field(default_factory=list)
    additional_text_blocks: List[str] = Field(default_factory=list)
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    image_detail: str | None = "auto"
    max_new_tokens: int | None = 350


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
    allowed_record_types: List[str] = Field(default_factory=list)
    allowed_derived_fields: List[str] = Field(default_factory=list)
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
    fields: Dict[str, Any]


class PrivateAggregateCountRequest(BaseModel):
    epsilon: float
    min_cohort_size: int | None = None
    budget_key: str | None = None
    budget_limit: float | None = None
    actor_did: str = "did:service:211-ai-api"


class PrivateAggregateCohortCountRequest(BaseModel):
    group_by: List[str] = Field(default_factory=list)
    epsilon: float | None = None
    min_cohort_size: int | None = None
    budget_key: str | None = None
    budget_limit: float | None = None
    actor_did: str = "did:service:211-ai-api"


class DerivedServiceMatchRequest(BaseModel):
    need_terms: Sequence[str] = Field(default_factory=list)
    location_claim: Dict[str, Any] | None = None
    limit: int = 10


class MissingPersonDeadDropEmailRequest(BaseModel):
    actor_did: str
    to_email: str = PORTLAND_POLICE_MISSING_EMAIL
    subject: str = "Missing person report dead drop bundle"
    body: str
    bundle: Dict[str, Any]
    bundle_filename: str = "abby-missing-person-wallet-dead-drop.json"


class MissingPersonDeadDropConfigRequest(BaseModel):
    actor_did: str
    enabled: bool = False
    to_email: str = PORTLAND_POLICE_MISSING_EMAIL
    subject: str = "Missing person report dead drop bundle"
    body: str = ""
    bundle: Dict[str, Any] = Field(default_factory=dict)
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
    metadata: Dict[str, Any] = Field(default_factory=dict)


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
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PhoneCallNotificationQueueRequest(BaseModel):
    actor_did: str
    to_phone: str
    script: str
    due_at: str = ""
    reason: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PhoneCallNotificationDispatchRequest(BaseModel):
    actor_did: str


def _ops_health_shared_secret() -> str:
    return str(os.getenv("WALLET_OPS_HEALTH_SHARED_SECRET") or "").strip()


def _extract_bearer_token(authorization: str | None) -> str:
    raw = str(authorization or "").strip()
    if not raw:
        return ""
    scheme, _, token = raw.partition(" ")
    if scheme.lower() != "bearer":
        return ""
    return token.strip()


def _require_portland_police_missing_email(to_email: str) -> str:
    normalized = str(to_email or "").strip().lower()
    if normalized != PORTLAND_POLICE_MISSING_EMAIL:
        raise ValueError(
            f"missing-person dead drop recipient must be {PORTLAND_POLICE_MISSING_EMAIL}"
        )
    return PORTLAND_POLICE_MISSING_EMAIL


def _normalize_phone_number(phone: str) -> str:
    raw = str(phone or "").strip()
    if not raw:
        raise ValueError("to_phone is required")
    digits = re.sub(r"\D", "", raw)
    if len(digits) < 10:
        raise ValueError("to_phone must include at least 10 digits")
    return f"+{digits}" if raw.startswith("+") else digits


def _sms_inbound_actor_did() -> str:
    return str(os.getenv("WALLET_SMS_INBOUND_ACTOR_DID") or "did:wallet:sms-bridge").strip()


def _require_internal_webhook_auth(
    *,
    env_prefix: str,
    authorization: str | None,
    headers: Mapping[str, str],
    error_detail: str,
) -> None:
    expected_bearer = str(os.getenv(f"{env_prefix}_BEARER_TOKEN") or "").strip()
    header_name = str(os.getenv(f"{env_prefix}_HTTP_HEADER_NAME") or "").strip()
    header_value = str(os.getenv(f"{env_prefix}_HTTP_HEADER_VALUE") or "").strip()
    if header_name and not header_value:
        raise RuntimeError(f"{env_prefix}_HTTP_HEADER_VALUE is required when header name is set")

    supplied_bearer = _extract_bearer_token(authorization)
    if expected_bearer and supplied_bearer == expected_bearer:
        return
    if header_name and str(headers.get(header_name) or "").strip() == header_value:
        return
    if not expected_bearer and not header_name:
        raise RuntimeError(
            f"{env_prefix}_BEARER_TOKEN or {env_prefix}_HTTP_HEADER_NAME must be configured for inbound webhook delivery"
        )
    raise HTTPException(status_code=401, detail=error_detail)


def _send_webhook_notification(
    *,
    env_prefix: str,
    required_key: str,
    required_value: str,
    extra_payload: Dict[str, Any] | None = None,
) -> Dict[str, str]:
    webhook_url = str(os.getenv(f"{env_prefix}_WEBHOOK_URL") or "").strip()
    backend = str(os.getenv(f"{env_prefix}_BACKEND") or ("http" if webhook_url else "")).strip().lower()
    if not backend or not webhook_url:
        raise RuntimeError(
            f"{env_prefix}_WEBHOOK_URL environment variable is required for delivery but is not configured"
        )
    if backend != "http":
        raise RuntimeError(f"{env_prefix}_BACKEND must be http when delivery is enabled")

    extra_headers: Dict[str, str] = {}
    if bearer_token := str(os.getenv(f"{env_prefix}_BEARER_TOKEN") or "").strip():
        extra_headers["authorization"] = f"Bearer {bearer_token}"
    if header_name := str(os.getenv(f"{env_prefix}_HTTP_HEADER_NAME") or "").strip():
        header_value = str(os.getenv(f"{env_prefix}_HTTP_HEADER_VALUE") or "").strip()
        if not header_value:
            raise RuntimeError(f"{env_prefix}_HTTP_HEADER_VALUE is required when header name is set")
        extra_headers[header_name] = header_value

    timeout_seconds = float(str(os.getenv(f"{env_prefix}_TIMEOUT_SECONDS") or "15").strip())
    if timeout_seconds <= 0:
        raise RuntimeError(f"{env_prefix}_TIMEOUT_SECONDS must be positive")

    payload = {
        required_key: required_value,
        **dict(extra_payload or {}),
    }

    request_headers = {"content-type": "application/json", **extra_headers}
    body = json.dumps(payload, sort_keys=True).encode("utf-8")
    req = urllib_request.Request(
        webhook_url,
        data=body,
        headers=request_headers,
        method="POST",
    )
    with urllib_request.urlopen(req, timeout=timeout_seconds) as response:
        raw = response.read().decode("utf-8")
        content_type = str(getattr(response, "headers", {}).get("content-type", ""))
        status = str(getattr(response, "status", getattr(response, "code", 200)))

    response_payload: Dict[str, Any] = {}
    if raw:
        if "json" in content_type.lower() or raw.lstrip().startswith("{"):
            parsed = json.loads(raw)
            if not isinstance(parsed, dict):
                raise ValueError("SMS delivery response must be a JSON object")
            response_payload = parsed

    provider_message_id = str(
        response_payload.get("provider_message_id")
        or response_payload.get("provider_call_id")
        or response_payload.get("message_id")
        or response_payload.get("call_id")
        or response_payload.get("email_id")
        or response_payload.get("id")
        or ""
    )
    result = {
        "provider": str(response_payload.get("provider") or "http"),
        "provider_status": str(response_payload.get("status") or status),
    }
    if provider_message_id:
        result["provider_message_id"] = provider_message_id
    return result


def _send_sms_notification(
    *,
    to_phone: str,
    message: str,
    wallet_id: str = "",
    external_reference: str = "",
    metadata: Dict[str, Any] | None = None,
) -> Dict[str, str]:
    normalized_phone = _normalize_phone_number(to_phone)
    normalized_message = str(message or "").strip()
    if not normalized_message:
        raise ValueError("message is required")
    return _send_webhook_notification(
        env_prefix="WALLET_SMS",
        required_key="to_phone",
        required_value=normalized_phone,
        extra_payload={
            "message": normalized_message,
            "wallet_id": str(wallet_id or "").strip(),
            "external_reference": str(external_reference or "").strip(),
            "metadata": dict(metadata or {}),
        },
    )


def _send_phone_call_notification(*, to_phone: str, script: str) -> Dict[str, str]:
    normalized_phone = _normalize_phone_number(to_phone)
    normalized_script = str(script or "").strip()
    if not normalized_script:
        raise ValueError("script is required")
    return _send_webhook_notification(
        env_prefix="WALLET_CALL",
        required_key="to_phone",
        required_value=normalized_phone,
        extra_payload={"script": normalized_script},
    )


def create_app(*, service: WalletInterfaceService | None = None):
    """Create the wallet API app.

    The API stays deliberately thin: all authorization, crypto, proofs,
    analytics privacy, and audit behavior remains in `ipfs_datasets_py.wallet`.
    """

    if FastAPI is None:  # pragma: no cover
        raise RuntimeError("FastAPI is required to create the wallet interface API")

    app_service = service or _wallet_interface_service_from_env()
    app = FastAPI(title="211-AI Wallet Interface", version="0.1.0")
    cors_origins = _cors_origins_from_env()
    if cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
            allow_headers=["authorization", "content-type", "x-wallet-ops-shared-secret"],
        )

    @app.get("/health")
    def health() -> Dict[str, str]:
        return {"status": "ok"}

    @app.get("/ops/health")
    def ops_health(
        verify_storage: bool = False,
        authorization: str | None = Header(default=None),
        x_wallet_ops_shared_secret: str | None = Header(default=None),
    ) -> Dict[str, Any]:
        expected_secret = _ops_health_shared_secret()
        if expected_secret:
            supplied_secret = _extract_bearer_token(authorization) or str(x_wallet_ops_shared_secret or "").strip()
            if supplied_secret != expected_secret:
                raise HTTPException(status_code=401, detail="ops health authorization required")
        try:
            return app_service.ops_health(verify_storage=verify_storage)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.get("/wallets/snapshots")
    def list_wallet_snapshots() -> Dict[str, Any]:
        return {"wallet_ids": app_service.list_wallet_snapshots()}

    @app.post("/wallets/snapshots/save-all")
    def save_all_wallet_snapshots() -> Dict[str, Any]:
        try:
            paths = app_service.save_all_wallet_snapshots()
            return {"paths": [str(path) for path in paths], "count": len(paths)}
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/wallets/snapshots/load-all")
    def load_all_wallet_snapshots() -> Dict[str, Any]:
        try:
            wallet_ids = app_service.load_all_wallet_snapshots()
            return {"wallet_ids": wallet_ids, "count": len(wallet_ids)}
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/wallets")
    def create_wallet(request: CreateWalletRequest) -> Dict[str, Any]:
        wallet = app_service.create_wallet(
            request.owner_did,
            controller_dids=request.controller_dids or None,
            approval_threshold=request.approval_threshold,
        )
        return wallet.to_dict()

    @app.get("/wallets/{wallet_id}")
    def get_wallet(wallet_id: str) -> Dict[str, Any]:
        try:
            return app_service.get_wallet(wallet_id).to_dict()
        except Exception as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/controllers")
    def add_wallet_controller(wallet_id: str, request: WalletControllerRequest) -> Dict[str, Any]:
        try:
            wallet = app_service.add_controller(
                wallet_id,
                actor_did=request.actor_did,
                controller_did=request.controller_did,
                controller_secret=_key_from_optional_hex(request.controller_key_hex),
                approval_id=request.approval_id,
            )
            return wallet.to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/controllers/remove")
    def remove_wallet_controller(wallet_id: str, request: WalletControllerRequest) -> Dict[str, Any]:
        try:
            wallet = app_service.remove_controller(
                wallet_id,
                actor_did=request.actor_did,
                controller_did=request.controller_did,
                approval_id=request.approval_id,
            )
            return wallet.to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/devices")
    def add_wallet_device(wallet_id: str, request: WalletDeviceRequest) -> Dict[str, Any]:
        try:
            wallet = app_service.add_device(
                wallet_id,
                actor_did=request.actor_did,
                device_did=request.device_did,
                device_secret=_key_from_optional_hex(request.device_key_hex),
                approval_id=request.approval_id,
            )
            return wallet.to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/devices/revoke")
    def revoke_wallet_device(wallet_id: str, request: WalletDeviceRequest) -> Dict[str, Any]:
        try:
            wallet = app_service.revoke_device(
                wallet_id,
                actor_did=request.actor_did,
                device_did=request.device_did,
                approval_id=request.approval_id,
            )
            return wallet.to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/recovery-policy")
    def set_wallet_recovery_policy(wallet_id: str, request: WalletRecoveryPolicyRequest) -> Dict[str, Any]:
        try:
            wallet = app_service.set_recovery_policy(
                wallet_id,
                actor_did=request.actor_did,
                contact_dids=request.contact_dids,
                threshold=request.threshold,
                approval_id=request.approval_id,
            )
            return wallet.to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/controllers/recover")
    def recover_wallet_controller(wallet_id: str, request: WalletControllerRecoveryRequest) -> Dict[str, Any]:
        try:
            wallet = app_service.recover_controller(
                wallet_id,
                actor_did=request.actor_did,
                controller_did=request.controller_did,
                controller_secret=_key_from_optional_hex(request.controller_key_hex),
                approval_id=request.approval_id,
            )
            return wallet.to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/snapshot")
    def save_wallet_snapshot(wallet_id: str) -> Dict[str, Any]:
        try:
            path = app_service.save_wallet_snapshot(wallet_id)
            return {"wallet_id": wallet_id, "path": str(path)}
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/wallets/{wallet_id}/snapshot")
    def verify_wallet_snapshot(wallet_id: str) -> Dict[str, Any]:
        try:
            return app_service.verify_wallet_snapshot(wallet_id)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/snapshot/load")
    def load_wallet_snapshot(wallet_id: str) -> Dict[str, Any]:
        try:
            app_service.load_wallet_snapshot(wallet_id)
            return {"wallet_id": wallet_id, "loaded": True}
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/locations")
    def add_location(wallet_id: str, request: AddLocationRequest) -> Dict[str, Any]:
        try:
            record = app_service.add_location(
                wallet_id,
                actor_did=request.actor_did,
                lat=request.lat,
                lon=request.lon,
            )
            return record.to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/dead-drops/missing-person")
    def send_missing_person_dead_drop_email(
        wallet_id: str, request: MissingPersonDeadDropEmailRequest
    ) -> Dict[str, Any]:
        try:
            app_service.get_wallet(wallet_id)
            app_service._require_portal_actor(wallet_id, request.actor_did)
        except Exception as exc:
            status_code = 404 if "not found" in str(exc).lower() else 400
            raise HTTPException(status_code=status_code, detail=str(exc)) from exc
        try:
            to_email = _require_portland_police_missing_email(request.to_email)
            envelope = _send_dead_drop_email(
                to_email=to_email,
                subject=request.subject,
                body=request.body,
                bundle=request.bundle,
                bundle_filename=request.bundle_filename,
            )
            return {
                "wallet_id": wallet_id,
                "status": "sent",
                "to_email": to_email,
                "subject": request.subject,
                "bundle_filename": request.bundle_filename,
                **envelope,
            }
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @app.get("/wallets/{wallet_id}/dead-drops/missing-person")
    def get_missing_person_dead_drop(wallet_id: str) -> Dict[str, Any]:
        try:
            return app_service.get_missing_person_dead_drop(wallet_id).to_dict()
        except Exception as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.put("/wallets/{wallet_id}/dead-drops/missing-person")
    def save_missing_person_dead_drop(wallet_id: str, request: MissingPersonDeadDropConfigRequest) -> Dict[str, Any]:
        try:
            record = app_service.save_missing_person_dead_drop(
                wallet_id,
                actor_did=request.actor_did,
                enabled=request.enabled,
                to_email=_require_portland_police_missing_email(request.to_email),
                subject=request.subject,
                body=request.body,
                bundle=request.bundle,
                bundle_filename=request.bundle_filename,
                due_at=request.due_at,
                last_check_in_at=request.last_check_in_at,
            )
            return record.to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/dead-drops/missing-person/dispatch")
    def dispatch_missing_person_dead_drop(
        wallet_id: str, request: MissingPersonDeadDropDispatchRequest
    ) -> Dict[str, Any]:
        try:
            record = app_service.get_missing_person_dead_drop_for_dispatch(
                wallet_id,
                actor_did=request.actor_did,
            )
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        try:
            envelope = _send_dead_drop_email(
                to_email=_require_portland_police_missing_email(record.to_email),
                subject=record.subject,
                body=record.body,
                bundle=record.bundle,
                bundle_filename=record.bundle_filename,
            )
            updated = app_service.mark_missing_person_dead_drop_sent(
                wallet_id,
                actor_did=request.actor_did,
                message_id=str(envelope.get("message_id") or ""),
                dispatched_reason="manual",
            )
            return {
                "wallet_id": wallet_id,
                "status": "sent",
                "to_email": updated.to_email,
                "subject": updated.subject,
                "bundle_filename": updated.bundle_filename,
                **envelope,
            }
        except RuntimeError as exc:
            app_service.mark_missing_person_dead_drop_failed(
                wallet_id,
                actor_did=request.actor_did,
                error=str(exc),
                dispatched_reason="manual",
            )
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except Exception as exc:
            app_service.mark_missing_person_dead_drop_failed(
                wallet_id,
                actor_did=request.actor_did,
                error=str(exc),
                dispatched_reason="manual",
            )
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @app.post("/ops/dead-drops/missing-person/process-due")
    def process_due_missing_person_dead_drops(
        authorization: str | None = Header(default=None),
        x_wallet_ops_shared_secret: str | None = Header(default=None),
    ) -> Dict[str, Any]:
        expected_secret = _ops_health_shared_secret()
        if not expected_secret:
            raise HTTPException(
                status_code=503,
                detail="WALLET_OPS_HEALTH_SHARED_SECRET environment variable is required for due dead-drop processing",
            )
        supplied_secret = _extract_bearer_token(authorization) or str(x_wallet_ops_shared_secret or "").strip()
        if supplied_secret != expected_secret:
            raise HTTPException(status_code=401, detail="dead-drop processing authorization required")
        try:
            due_records = app_service.list_due_missing_person_dead_drops()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        results: List[Dict[str, Any]] = []
        sent = 0
        failed = 0
        for record in due_records:
            try:
                envelope = _send_dead_drop_email(
                    to_email=_require_portland_police_missing_email(record.to_email),
                    subject=record.subject,
                    body=record.body,
                    bundle=record.bundle,
                    bundle_filename=record.bundle_filename,
                )
                app_service.mark_missing_person_dead_drop_sent(
                    record.wallet_id,
                    actor_did=OPS_DEAD_DROP_ACTOR_DID,
                    message_id=str(envelope.get("message_id") or ""),
                    dispatched_reason="due",
                )
                sent += 1
                results.append(
                    {
                        "wallet_id": record.wallet_id,
                        "status": "sent",
                        "message_id": str(envelope.get("message_id") or ""),
                    }
                )
            except Exception as exc:
                failed += 1
                app_service.mark_missing_person_dead_drop_failed(
                    record.wallet_id,
                    actor_did=OPS_DEAD_DROP_ACTOR_DID,
                    error=str(exc),
                    dispatched_reason="due",
                )
                results.append(
                    {
                        "wallet_id": record.wallet_id,
                        "status": "failed",
                        "detail": "dead-drop dispatch failed",
                    }
                )
        return {
            "status": "ok",
            "due_count": len(due_records),
            "sent_count": sent,
            "failed_count": failed,
            "results": results,
        }

    @app.post("/wallets/{wallet_id}/notifications/sms/queue")
    def queue_sms_notification(wallet_id: str, request: SmsNotificationQueueRequest) -> Dict[str, Any]:
        try:
            record = app_service.queue_sms_notification(
                wallet_id,
                actor_did=request.actor_did,
                to_phone=_normalize_phone_number(request.to_phone),
                message=request.message,
                due_at=request.due_at,
                reason=request.reason,
                metadata=request.metadata,
            )
            return record.to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/wallets/{wallet_id}/notifications/sms")
    def list_sms_notifications(wallet_id: str) -> Dict[str, Any]:
        try:
            notifications = app_service.list_sms_notifications(wallet_id)
            return {
                "wallet_id": wallet_id,
                "count": len(notifications),
                "notifications": [record.to_dict() for record in notifications],
            }
        except Exception as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/wallets/{wallet_id}/messages/sms/inbound")
    def list_inbound_sms_messages(wallet_id: str) -> Dict[str, Any]:
        try:
            messages = app_service.list_inbound_sms_messages(wallet_id)
            return {
                "wallet_id": wallet_id,
                "count": len(messages),
                "messages": [record.to_dict() for record in messages],
            }
        except Exception as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/messages/sms/inbound")
    def receive_inbound_sms_message(http_request: Request, payload: InboundSmsForwardRequest) -> Dict[str, Any]:
        try:
            _require_internal_webhook_auth(
                env_prefix="WALLET_SMS_INBOUND",
                authorization=http_request.headers.get("authorization"),
                headers=http_request.headers,
                error_detail="sms inbound authorization required",
            )
            record = app_service.record_inbound_sms_message(
                str(payload.wallet_id or "").strip(),
                actor_did=_sms_inbound_actor_did(),
                from_phone=_normalize_phone_number(payload.from_phone),
                to_phone=_normalize_phone_number(payload.to_phone) if payload.to_phone else "",
                message=payload.message,
                provider=payload.provider,
                status=payload.status,
                provider_message_id=payload.provider_message_id,
                bridge_message_id=payload.message_id,
                external_reference=payload.external_reference,
                received_at=payload.created_at,
                metadata=payload.metadata,
            )
            return {"status": "ok", "message": record.to_dict()}
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/notifications/sms/{notification_id}/dispatch")
    def dispatch_sms_notification(
        wallet_id: str,
        notification_id: str,
        request: SmsNotificationDispatchRequest,
    ) -> Dict[str, Any]:
        try:
            record = app_service.get_sms_notification_for_dispatch(
                wallet_id,
                notification_id,
                actor_did=request.actor_did,
            )
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        try:
            delivery = _send_sms_notification(
                to_phone=record.to_phone,
                message=record.message,
                wallet_id=record.wallet_id,
                external_reference=record.notification_id,
                metadata={**dict(record.metadata), "notification_id": record.notification_id, "reason": record.reason},
            )
            updated = app_service.mark_sms_notification_sent(
                wallet_id,
                notification_id,
                actor_did=request.actor_did,
                provider_message_id=str(delivery.get("provider_message_id") or ""),
                dispatched_reason="manual",
            )
            return {
                "wallet_id": wallet_id,
                "status": "sent",
                "notification": updated.to_dict(),
                **delivery,
            }
        except RuntimeError as exc:
            app_service.mark_sms_notification_failed(
                wallet_id,
                notification_id,
                actor_did=request.actor_did,
                error=str(exc),
                dispatched_reason="manual",
            )
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except ValueError as exc:
            app_service.mark_sms_notification_failed(
                wallet_id,
                notification_id,
                actor_did=request.actor_did,
                error=str(exc),
                dispatched_reason="manual",
            )
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            app_service.mark_sms_notification_failed(
                wallet_id,
                notification_id,
                actor_did=request.actor_did,
                error=str(exc),
                dispatched_reason="manual",
            )
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @app.post("/ops/notifications/sms/process-due")
    def process_due_sms_notifications(
        authorization: str | None = Header(default=None),
        x_wallet_ops_shared_secret: str | None = Header(default=None),
    ) -> Dict[str, Any]:
        expected_secret = _ops_health_shared_secret()
        if not expected_secret:
            raise HTTPException(
                status_code=503,
                detail="WALLET_OPS_HEALTH_SHARED_SECRET environment variable is required for due SMS processing",
            )
        supplied_secret = _extract_bearer_token(authorization) or str(x_wallet_ops_shared_secret or "").strip()
        if supplied_secret != expected_secret:
            raise HTTPException(status_code=401, detail="sms processing authorization required")
        try:
            due_records = app_service.list_due_sms_notifications()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        results: List[Dict[str, Any]] = []
        sent = 0
        failed = 0
        for record in due_records:
            try:
                delivery = _send_sms_notification(
                    to_phone=record.to_phone,
                    message=record.message,
                    wallet_id=record.wallet_id,
                    external_reference=record.notification_id,
                    metadata={**dict(record.metadata), "notification_id": record.notification_id, "reason": record.reason},
                )
                app_service.mark_sms_notification_sent(
                    record.wallet_id,
                    record.notification_id,
                    actor_did=OPS_DEAD_DROP_ACTOR_DID,
                    provider_message_id=str(delivery.get("provider_message_id") or ""),
                    dispatched_reason="due",
                )
                sent += 1
                results.append(
                    {
                        "wallet_id": record.wallet_id,
                        "notification_id": record.notification_id,
                        "status": "sent",
                        "provider_message_id": str(delivery.get("provider_message_id") or ""),
                    }
                )
            except Exception as exc:
                failed += 1
                app_service.mark_sms_notification_failed(
                    record.wallet_id,
                    record.notification_id,
                    actor_did=OPS_DEAD_DROP_ACTOR_DID,
                    error=str(exc),
                    dispatched_reason="due",
                )
                results.append(
                    {
                        "wallet_id": record.wallet_id,
                        "notification_id": record.notification_id,
                        "status": "failed",
                        "detail": "sms dispatch failed",
                    }
                )
        return {
            "status": "ok",
            "due_count": len(due_records),
            "sent_count": sent,
            "failed_count": failed,
            "results": results,
        }

    @app.post("/wallets/{wallet_id}/notifications/calls/queue")
    def queue_phone_call_notification(wallet_id: str, request: PhoneCallNotificationQueueRequest) -> Dict[str, Any]:
        try:
            record = app_service.queue_phone_call_notification(
                wallet_id,
                actor_did=request.actor_did,
                to_phone=_normalize_phone_number(request.to_phone),
                script=request.script,
                due_at=request.due_at,
                reason=request.reason,
                metadata=request.metadata,
            )
            return record.to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/wallets/{wallet_id}/notifications/calls")
    def list_phone_call_notifications(wallet_id: str) -> Dict[str, Any]:
        try:
            notifications = app_service.list_phone_call_notifications(wallet_id)
            return {
                "wallet_id": wallet_id,
                "count": len(notifications),
                "notifications": [record.to_dict() for record in notifications],
            }
        except Exception as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/notifications/calls/{notification_id}/dispatch")
    def dispatch_phone_call_notification(
        wallet_id: str,
        notification_id: str,
        request: PhoneCallNotificationDispatchRequest,
    ) -> Dict[str, Any]:
        try:
            record = app_service.get_phone_call_notification_for_dispatch(
                wallet_id,
                notification_id,
                actor_did=request.actor_did,
            )
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        try:
            delivery = _send_phone_call_notification(to_phone=record.to_phone, script=record.script)
            updated = app_service.mark_phone_call_notification_sent(
                wallet_id,
                notification_id,
                actor_did=request.actor_did,
                provider_call_id=str(delivery.get("provider_message_id") or ""),
                dispatched_reason="manual",
            )
            return {
                "wallet_id": wallet_id,
                "status": "sent",
                "notification": updated.to_dict(),
                **delivery,
            }
        except RuntimeError as exc:
            app_service.mark_phone_call_notification_failed(
                wallet_id,
                notification_id,
                actor_did=request.actor_did,
                error=str(exc),
                dispatched_reason="manual",
            )
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except ValueError as exc:
            app_service.mark_phone_call_notification_failed(
                wallet_id,
                notification_id,
                actor_did=request.actor_did,
                error=str(exc),
                dispatched_reason="manual",
            )
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            app_service.mark_phone_call_notification_failed(
                wallet_id,
                notification_id,
                actor_did=request.actor_did,
                error=str(exc),
                dispatched_reason="manual",
            )
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @app.post("/ops/notifications/calls/process-due")
    def process_due_phone_call_notifications(
        authorization: str | None = Header(default=None),
        x_wallet_ops_shared_secret: str | None = Header(default=None),
    ) -> Dict[str, Any]:
        expected_secret = _ops_health_shared_secret()
        if not expected_secret:
            raise HTTPException(
                status_code=503,
                detail="WALLET_OPS_HEALTH_SHARED_SECRET environment variable is required for due call processing",
            )
        supplied_secret = _extract_bearer_token(authorization) or str(x_wallet_ops_shared_secret or "").strip()
        if supplied_secret != expected_secret:
            raise HTTPException(status_code=401, detail="call processing authorization required")
        try:
            due_records = app_service.list_due_phone_call_notifications()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        results: List[Dict[str, Any]] = []
        sent = 0
        failed = 0
        for record in due_records:
            try:
                delivery = _send_phone_call_notification(to_phone=record.to_phone, script=record.script)
                app_service.mark_phone_call_notification_sent(
                    record.wallet_id,
                    record.notification_id,
                    actor_did=OPS_DEAD_DROP_ACTOR_DID,
                    provider_call_id=str(delivery.get("provider_message_id") or ""),
                    dispatched_reason="due",
                )
                sent += 1
                results.append(
                    {
                        "wallet_id": record.wallet_id,
                        "notification_id": record.notification_id,
                        "status": "sent",
                        "provider_call_id": str(delivery.get("provider_message_id") or ""),
                    }
                )
            except Exception as exc:
                failed += 1
                app_service.mark_phone_call_notification_failed(
                    record.wallet_id,
                    record.notification_id,
                    actor_did=OPS_DEAD_DROP_ACTOR_DID,
                    error=str(exc),
                    dispatched_reason="due",
                )
                results.append(
                    {
                        "wallet_id": record.wallet_id,
                        "notification_id": record.notification_id,
                        "status": "failed",
                        "detail": "phone call dispatch failed",
                    }
                )
        return {
            "status": "ok",
            "due_count": len(due_records),
            "sent_count": sent,
            "failed_count": failed,
            "results": results,
        }

    @app.post("/wallets/{wallet_id}/locations/{location_record_id}/coarse-grants")
    def create_coarse_location_grant(
        wallet_id: str,
        location_record_id: str,
        request: CoarseLocationGrantRequest,
    ) -> Dict[str, Any]:
        try:
            grant = app_service.create_coarse_location_grant(
                wallet_id,
                location_record_id,
                issuer_did=request.issuer_did,
                audience_did=request.audience_did,
                issuer_secret=_key_from_optional_hex(request.issuer_key_hex),
                audience_secret=_key_from_optional_hex(request.audience_key_hex),
                expires_at=request.expires_at,
            )
            return grant.to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/locations/{location_record_id}/coarse-invocations")
    def issue_coarse_location_invocation(
        wallet_id: str,
        location_record_id: str,
        request: CoarseLocationInvocationRequest,
    ) -> Dict[str, Any]:
        try:
            invocation = app_service.issue_coarse_location_invocation(
                wallet_id,
                location_record_id,
                grant_id=request.grant_id,
                actor_did=request.actor_did,
                actor_secret=_key_from_optional_hex(request.actor_key_hex),
                expires_at=request.expires_at,
                purpose=request.purpose,
                user_present=request.user_present,
            )
            return {"invocation": invocation.to_dict(), "token": invocation_to_token(invocation)}
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/locations/{location_record_id}/region-proof-grants")
    def create_location_region_proof_grant(
        wallet_id: str,
        location_record_id: str,
        request: LocationRegionProofGrantRequest,
    ) -> Dict[str, Any]:
        try:
            grant = app_service.create_location_region_proof_grant(
                wallet_id,
                location_record_id,
                issuer_did=request.issuer_did,
                audience_did=request.audience_did,
                expires_at=request.expires_at,
            )
            return grant.to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/locations/{location_record_id}/region-proofs")
    def create_location_region_proof(
        wallet_id: str,
        location_record_id: str,
        request: LocationRegionProofRequest,
    ) -> Dict[str, Any]:
        try:
            proof = app_service.create_location_region_proof(
                wallet_id,
                location_record_id,
                actor_did=request.actor_did,
                region_id=request.region_id,
                grant_id=request.grant_id,
            )
            return proof.to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/locations/{location_record_id}/distance-proof-grants")
    def create_location_distance_proof_grant(
        wallet_id: str,
        location_record_id: str,
        request: LocationDistanceProofGrantRequest,
    ) -> Dict[str, Any]:
        try:
            grant = app_service.create_location_distance_proof_grant(
                wallet_id,
                location_record_id,
                issuer_did=request.issuer_did,
                audience_did=request.audience_did,
                target_id=request.target_id,
                max_distance_km=request.max_distance_km,
                expires_at=request.expires_at,
            )
            return grant.to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/locations/{location_record_id}/distance-proofs")
    def create_location_distance_proof(
        wallet_id: str,
        location_record_id: str,
        request: LocationDistanceProofRequest,
    ) -> Dict[str, Any]:
        try:
            proof = app_service.create_location_distance_proof(
                wallet_id,
                location_record_id,
                actor_did=request.actor_did,
                target_id=request.target_id,
                target_lat=request.target_lat,
                target_lon=request.target_lon,
                max_distance_km=request.max_distance_km,
                grant_id=request.grant_id,
            )
            return proof.to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/records/{record_id}/document-profile-proofs")
    def create_document_profile_proof(
        wallet_id: str,
        record_id: str,
        request: DocumentPrivacyProfileProofRequest,
    ) -> Dict[str, Any]:
        try:
            proof = app_service.create_document_profile_proof(
                wallet_id,
                record_id,
                actor_did=request.actor_did,
                public_inputs=request.public_inputs,
            )
            return proof.to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/ai-router/embeddings")
    def proxy_wallet_embeddings_router(
        wallet_id: str,
        request: WalletEmbeddingsRouterRequest,
    ) -> Dict[str, Any]:
        try:
            _require_wallet_router_actor(app_service, wallet_id, request.actor_did)
            wallet_cid = _wallet_router_subject(wallet_id, request.wallet_cid)
            limit = _check_wallet_router_rate_limit(wallet_cid, cost=max(1, len(request.texts) or 1))
            texts = list(request.texts or [])
            if request.text:
                texts.insert(0, request.text)
            if not texts:
                raise ValueError("text or texts is required")
            kwargs = _prepare_hf_router_environment(request.kwargs)
            from ipfs_datasets_py import embeddings_router  # noqa: WPS433

            embeddings = [
                embeddings_router.embed_text(
                    text,
                    model_name=request.model_name,
                    provider=request.provider,
                    **kwargs,
                )
                for text in texts
            ]
            return {
                "router": "embeddings_router",
                "wallet_id": wallet_id,
                "wallet_cid": wallet_cid,
                "provider": request.provider,
                "model_name": request.model_name,
                "rate_limit": limit,
                "embeddings": embeddings,
            }
        except ValueError as exc:
            raise HTTPException(status_code=429 if "rate limit" in str(exc).lower() else 400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/ai-router/llm")
    def proxy_wallet_llm_router(
        wallet_id: str,
        request: WalletLlmRouterRequest,
    ) -> Dict[str, Any]:
        try:
            _require_wallet_router_actor(app_service, wallet_id, request.actor_did)
            wallet_cid = _wallet_router_subject(wallet_id, request.wallet_cid)
            limit = _check_wallet_router_rate_limit(wallet_cid)
            prompt = request.prompt
            if request.system_prompt:
                prompt = f"system: {request.system_prompt}\nuser: {request.prompt}"
            kwargs = _prepare_hf_router_environment(request.kwargs)
            from ipfs_datasets_py import llm_router  # noqa: WPS433

            if request.max_new_tokens is not None:
                kwargs.setdefault("max_new_tokens", request.max_new_tokens)
            model_name = request.model_name or os.getenv("WALLET_AI_ROUTER_LLM_MODEL", "Qwen/Qwen3.5-2B")
            text = llm_router.generate_text(
                prompt,
                model_name=model_name,
                provider=request.provider,
                **kwargs,
            )
            return {
                "router": "llm_router",
                "wallet_id": wallet_id,
                "wallet_cid": wallet_cid,
                "provider": request.provider,
                "model_name": model_name,
                "rate_limit": limit,
                "text": text,
            }
        except ValueError as exc:
            raise HTTPException(status_code=429 if "rate limit" in str(exc).lower() else 400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/ai-router/multimodal")
    def proxy_wallet_multimodal_router(
        wallet_id: str,
        request: WalletMultimodalRouterRequest,
    ) -> Dict[str, Any]:
        try:
            _require_wallet_router_actor(app_service, wallet_id, request.actor_did)
            wallet_cid = _wallet_router_subject(wallet_id, request.wallet_cid)
            limit = _check_wallet_router_rate_limit(wallet_cid)
            kwargs = _prepare_hf_router_environment(request.kwargs)
            from ipfs_datasets_py import multimodal_router  # noqa: WPS433

            if request.max_new_tokens is not None:
                kwargs.setdefault("max_new_tokens", request.max_new_tokens)
            model_name = request.model_name or os.getenv("WALLET_AI_ROUTER_MULTIMODAL_MODEL")
            text = multimodal_router.generate_multimodal_text(
                request.prompt,
                model_name=model_name,
                provider=request.provider,
                image_urls=request.image_urls,
                system_prompt=None,
                additional_text_blocks=request.additional_text_blocks,
                messages=request.messages or None,
                image_detail=request.image_detail,
                **kwargs,
            )
            return {
                "router": "multimodal_router",
                "wallet_id": wallet_id,
                "wallet_cid": wallet_cid,
                "provider": request.provider,
                "model_name": model_name,
                "rate_limit": limit,
                "text": text,
            }
        except ValueError as exc:
            raise HTTPException(status_code=429 if "rate limit" in str(exc).lower() else 400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @app.post("/voice/indextts/tts")
    def indextts_voice_tts(
        text: str = Form(default=""),
        voice_description: str | None = Form(default=None),
    ) -> Dict[str, Any]:
        try:
            audio = _run_indextts_gradio_tts(
                text=text,
                voice_description=voice_description,
            )
            return audio
        except Exception as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @app.post("/voice/indextts/infer")
    async def indextts_voice_infer(
        audio: UploadFile | None = File(default=None),
        text: str = Form(default=""),
        fallback_text: str | None = Form(default=None),
        voice_description: str | None = Form(default=None),
    ) -> Dict[str, Any]:
        try:
            reference_audio = await audio.read() if audio is not None else None
            reference_name = getattr(audio, "filename", None) if audio is not None else None
            reference_type = getattr(audio, "content_type", None) if audio is not None else None
            reply_text = (text or fallback_text or "").strip()
            audio_payload = _run_indextts_gradio_tts(
                text=reply_text,
                voice_description=voice_description,
                reference_audio=reference_audio,
                reference_audio_name=reference_name,
                reference_audio_mime_type=reference_type,
            )
            audio_payload["text"] = reply_text
            return audio_payload
        except Exception as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/documents/text")
    def add_text_document(wallet_id: str, request: AddTextDocumentRequest) -> Dict[str, Any]:
        try:
            metadata = {"title": request.title} if request.title else {}
            record = app_service.add_text_document(
                wallet_id,
                actor_did=request.actor_did,
                actor_secret=_key_from_optional_hex(request.key_hex),
                text=request.text,
                filename=request.filename,
                metadata=metadata,
            )
            return record.to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/documents")
    async def add_binary_document(
        wallet_id: str,
        actor_did: str = Form(...),
        key_hex: str | None = Form(default=None),
        title: str | None = Form(default=None),
        file: UploadFile = File(...),
    ) -> Dict[str, Any]:
        try:
            metadata = {"title": title} if title else {}
            data = await file.read()
            record = app_service.add_binary_document(
                wallet_id,
                actor_did=actor_did,
                actor_secret=_key_from_optional_hex(key_hex),
                data=data,
                filename=file.filename or "document.bin",
                content_type=file.content_type,
                metadata=metadata,
            )
            return record.to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/filecoin-upload")
    async def upload_to_ipfs_bridge(
        request: Request,
        file: UploadFile | None = File(default=None),
        metadata: str | None = Form(default=None),
    ) -> Dict[str, Any]:
        try:
            content_type = request.headers.get("content-type", "")
            if "application/json" in content_type:
                payload = FilecoinRecordUploadRequest(**(await request.json()))
                encrypted_record = app_service.export_record_encrypted_blobs(
                    payload.walletId,
                    payload.recordId,
                    actor_did=payload.actorDid,
                )
                return _publish_encrypted_record_graph_to_ipfs(
                    encrypted_record,
                    file_name=payload.fileName,
                )

            if file is None:
                raise ValueError("multipart uploads require a file field")
            upload_metadata = _parse_upload_metadata(metadata)
            data = await file.read()
            expected_sha256 = str(upload_metadata.get("sha256") or "").strip()
            if expected_sha256:
                actual_sha256 = hashlib.sha256(data).hexdigest()
                if actual_sha256 != expected_sha256:
                    raise ValueError("uploaded file SHA-256 does not match metadata")
            return _publish_bytes_to_ipfs(
                data,
                file_name=str(upload_metadata.get("fileName") or file.filename or "").strip() or None,
                mime_type=str(upload_metadata.get("mimeType") or file.content_type or "").strip() or None,
                source_record_id=str(upload_metadata.get("recordId") or "").strip() or None,
                wallet_id=str(upload_metadata.get("walletId") or "").strip() or None,
            )
        except FilecoinPinHandoffError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/ipfs-proxy/{cid}")
    def proxy_ipfs_cid(cid: str) -> Response:
        normalized_cid = _normalize_ipfs_cid(cid)
        if not _valid_ipfs_cid(normalized_cid):
            raise HTTPException(status_code=400, detail="invalid IPFS CID")
        if not _ipfs_proxy_allows_cid(normalized_cid):
            raise HTTPException(status_code=403, detail="CID is not allowed by WALLET_IPFS_PROXY_ALLOWED_CIDS")
        try:
            payload = get_ipfs_backend().cat(normalized_cid)
        except Exception as local_exc:
            try:
                payload = _fetch_ipfs_cid_via_gateway(normalized_cid)
            except Exception as fallback_exc:
                raise HTTPException(
                    status_code=502,
                    detail=f"Unable to fetch CID from local IPFS or fallback gateways: {local_exc}; {fallback_exc}",
                ) from fallback_exc
        return Response(
            content=payload,
            media_type=_ipfs_proxy_media_type(payload),
            headers={"Cache-Control": "public, max-age=300"},
        )

    @app.get("/filecoin-upload/status/{request_id}")
    def get_filecoin_upload_status(request_id: str) -> Dict[str, Any]:
        try:
            payload = _fetch_filecoin_pin_status(request_id)
            normalized_request_id = str(
                payload.get("requestId") or payload.get("requestid") or request_id
            ).strip()
            if normalized_request_id:
                payload["requestId"] = normalized_request_id
            if isinstance(payload.get("info"), dict) and not isinstance(payload.get("filecoinPinInfo"), dict):
                payload["filecoinPinInfo"] = payload["info"]
            status_url = _filecoin_upload_status_url(request_id)
            if status_url:
                payload["statusUrl"] = status_url
            return payload
        except FilecoinPinHandoffError as exc:
            status_code = 503 if "not configured" in str(exc).lower() else 502
            raise HTTPException(status_code=status_code, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/wallets/{wallet_id}/records")
    def list_records(wallet_id: str, data_type: str | None = None) -> Dict[str, Any]:
        try:
            records = app_service.list_records(wallet_id, data_type=data_type)
            return {"records": [app_service.record_to_dict(record) for record in records]}
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.patch("/wallets/{wallet_id}/records/{record_id}/metadata")
    def update_record_metadata(
        wallet_id: str,
        record_id: str,
        request: WalletRecordMetadataRequest,
    ) -> Dict[str, Any]:
        try:
            record = app_service.update_record_metadata(
                wallet_id,
                record_id,
                actor_did=request.actor_did,
                metadata=request.metadata,
            )
            if _should_publish_record_metadata_ipld(request.metadata):
                metadata_patch = _publish_record_metadata_ipld(record)
                if metadata_patch:
                    record = app_service.update_record_metadata(
                        wallet_id,
                        record_id,
                        actor_did=request.actor_did,
                        metadata=metadata_patch,
                    )
            return record
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.delete("/wallets/{wallet_id}/records/{record_id}")
    def delete_record(
        wallet_id: str,
        record_id: str,
        request: DeleteWalletRecordRequest,
    ) -> Dict[str, Any]:
        try:
            return app_service.delete_record(
                wallet_id,
                record_id,
                actor_did=request.actor_did,
                unpin_ipfs=request.unpin_ipfs,
            )
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/wallets/{wallet_id}/portal/saved-services")
    def list_saved_services(wallet_id: str, status: str | None = None) -> Dict[str, Any]:
        try:
            return {
                "saved_services": [
                    record.to_dict() for record in app_service.list_saved_services(wallet_id, status=status)
                ]
            }
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/portal/saved-services")
    def save_service(wallet_id: str, request: SavedServiceRequest) -> Dict[str, Any]:
        try:
            record = app_service.save_service_for_wallet(
                wallet_id,
                actor_did=request.actor_did,
                service_doc_id=request.service_doc_id,
                source_content_cid=request.source_content_cid,
                source_page_cid=request.source_page_cid,
                title=request.title,
                provider_name=request.provider_name,
                program_name=request.program_name,
                source_url=request.source_url,
                label=request.label,
                reason=request.reason,
                priority=request.priority,
                status=request.status,
                private_notes_record_id=request.private_notes_record_id,
                metadata=request.metadata,
            )
            return record.to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.patch("/wallets/{wallet_id}/portal/saved-services/{saved_service_id}")
    def update_saved_service(wallet_id: str, saved_service_id: str, request: SavedServiceUpdateRequest) -> Dict[str, Any]:
        try:
            record = app_service.update_saved_service(
                wallet_id,
                saved_service_id,
                actor_did=request.actor_did,
                source_content_cid=request.source_content_cid,
                source_page_cid=request.source_page_cid,
                title=request.title,
                provider_name=request.provider_name,
                program_name=request.program_name,
                source_url=request.source_url,
                label=request.label,
                reason=request.reason,
                priority=request.priority,
                status=request.status,
                private_notes_record_id=request.private_notes_record_id,
                metadata=request.metadata,
            )
            return record.to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/wallets/{wallet_id}/portal/plans")
    def list_service_plans(
        wallet_id: str,
        service_doc_id: str | None = None,
        status: str | None = None,
    ) -> Dict[str, Any]:
        try:
            return {
                "plans": [
                    record.to_dict()
                    for record in app_service.list_service_plans(
                        wallet_id,
                        service_doc_id=service_doc_id,
                        status=status,
                    )
                ]
            }
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/portal/plans")
    def create_service_plan(wallet_id: str, request: ServicePlanRequest) -> Dict[str, Any]:
        try:
            record = app_service.create_service_plan(
                wallet_id,
                actor_did=request.actor_did,
                service_doc_id=request.service_doc_id,
                source_content_cid=request.source_content_cid,
                source_page_cid=request.source_page_cid,
                service_title=request.service_title,
                provider_name=request.provider_name,
                goal=request.goal,
                steps=request.steps,
                documents_needed=request.documents_needed,
                questions_to_ask=request.questions_to_ask,
                appointment_at=request.appointment_at,
                reminder_at=request.reminder_at,
                travel_target=request.travel_target,
                assigned_worker_recipient_id=request.assigned_worker_recipient_id,
                status=request.status,
                related_interaction_ids=request.related_interaction_ids,
                private_notes_record_id=request.private_notes_record_id,
            )
            return record.to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.patch("/wallets/{wallet_id}/portal/plans/{plan_id}")
    def update_service_plan(wallet_id: str, plan_id: str, request: ServicePlanUpdateRequest) -> Dict[str, Any]:
        try:
            record = app_service.update_service_plan(
                wallet_id,
                plan_id,
                actor_did=request.actor_did,
                source_content_cid=request.source_content_cid,
                source_page_cid=request.source_page_cid,
                service_title=request.service_title,
                provider_name=request.provider_name,
                goal=request.goal,
                steps=request.steps,
                documents_needed=request.documents_needed,
                questions_to_ask=request.questions_to_ask,
                appointment_at=request.appointment_at,
                reminder_at=request.reminder_at,
                travel_target=request.travel_target,
                assigned_worker_recipient_id=request.assigned_worker_recipient_id,
                status=request.status,
                related_interaction_ids=request.related_interaction_ids,
                private_notes_record_id=request.private_notes_record_id,
            )
            return record.to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/portal/plans/{plan_id}/share-grants")
    def create_service_plan_share_grant(
        wallet_id: str,
        plan_id: str,
        request: ServicePlanShareGrantRequest,
    ) -> Dict[str, Any]:
        try:
            result = app_service.create_service_plan_share_grant(
                wallet_id,
                plan_id,
                issuer_did=request.actor_did or request.issuer_did,
                audience_did=request.audience_did or request.worker_did,
                scopes=request.scopes,
                purpose=request.purpose,
                worker_recipient_id=request.worker_recipient_id,
                worker_name=request.worker_name,
                expires_at=request.expires_at,
                approval_id=request.approval_id,
                issuer_secret=_key_from_optional_hex(request.issuer_key_hex),
                audience_secret=_key_from_optional_hex(request.audience_key_hex),
                extra_caveats=request.caveats,
            )
            return result.to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/services/{service_doc_id}/share-grants")
    def create_service_share_grant(
        wallet_id: str,
        service_doc_id: str,
        request: ServicePlanShareGrantRequest,
    ) -> Dict[str, Any]:
        try:
            result = app_service.create_service_share_grant(
                wallet_id,
                service_doc_id,
                issuer_did=request.actor_did or request.issuer_did,
                audience_did=request.audience_did or request.worker_did,
                scopes=request.scopes,
                purpose=request.purpose,
                worker_recipient_id=request.worker_recipient_id,
                worker_name=request.worker_name,
                expires_at=request.expires_at,
                approval_id=request.approval_id,
                issuer_secret=_key_from_optional_hex(request.issuer_key_hex),
                audience_secret=_key_from_optional_hex(request.audience_key_hex),
                extra_caveats=request.caveats,
            )
            return result.to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/wallets/{wallet_id}/portal/interactions")
    def list_service_interactions(
        wallet_id: str,
        service_doc_id: str | None = None,
        interaction_type: str | None = None,
        status: str | None = None,
    ) -> Dict[str, Any]:
        try:
            return {
                "interactions": [
                    record.to_dict()
                    for record in app_service.list_service_interactions(
                        wallet_id,
                        service_doc_id=service_doc_id,
                        interaction_type=interaction_type,
                        status=status,
                    )
                ]
            }
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/portal/interactions")
    def create_service_interaction(wallet_id: str, request: ServiceInteractionRequest) -> Dict[str, Any]:
        try:
            record = app_service.create_service_interaction(
                wallet_id,
                actor_did=request.actor_did,
                service_doc_id=request.service_doc_id,
                source_content_cid=request.source_content_cid,
                source_page_cid=request.source_page_cid,
                provider_name=request.provider_name,
                program_name=request.program_name,
                interaction_type=request.interaction_type,
                channel=request.channel,
                counterparty_name=request.counterparty_name,
                counterparty_contact=request.counterparty_contact,
                timestamp=request.timestamp,
                status=request.status,
                outcome=request.outcome,
                notes_record_id=request.notes_record_id,
                next_action=request.next_action,
                next_follow_up_at=request.next_follow_up_at,
                source_action_url=request.source_action_url,
                related_grant_ids=request.related_grant_ids,
                related_record_ids=request.related_record_ids,
                privacy_level=request.privacy_level,
                metadata=request.metadata,
            )
            return record.to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.patch("/wallets/{wallet_id}/portal/interactions/{interaction_id}")
    def update_service_interaction(
        wallet_id: str,
        interaction_id: str,
        request: ServiceInteractionUpdateRequest,
    ) -> Dict[str, Any]:
        try:
            record = app_service.update_service_interaction(
                wallet_id,
                interaction_id,
                actor_did=request.actor_did,
                source_content_cid=request.source_content_cid,
                source_page_cid=request.source_page_cid,
                provider_name=request.provider_name,
                program_name=request.program_name,
                channel=request.channel,
                counterparty_name=request.counterparty_name,
                counterparty_contact=request.counterparty_contact,
                timestamp=request.timestamp,
                status=request.status,
                outcome=request.outcome,
                notes_record_id=request.notes_record_id,
                next_action=request.next_action,
                next_follow_up_at=request.next_follow_up_at,
                source_action_url=request.source_action_url,
                related_grant_ids=request.related_grant_ids,
                related_record_ids=request.related_record_ids,
                privacy_level=request.privacy_level,
                metadata=request.metadata,
            )
            return record.to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/records/{record_id}/analysis-grants")
    def create_analysis_grant(
        wallet_id: str,
        record_id: str,
        request: AnalysisGrantRequest,
    ) -> Dict[str, Any]:
        try:
            grant = app_service.create_record_analysis_grant(
                wallet_id,
                record_id,
                issuer_did=request.issuer_did,
                audience_did=request.audience_did,
                issuer_secret=_key_from_optional_hex(request.issuer_key_hex),
                audience_secret=_key_from_optional_hex(request.audience_key_hex),
                expires_at=request.expires_at,
            )
            return grant.to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/records/{record_id}/grants")
    def create_record_grant(
        wallet_id: str,
        record_id: str,
        request: RecordGrantRequest,
    ) -> Dict[str, Any]:
        try:
            grant = app_service.create_record_grant(
                wallet_id,
                record_id,
                issuer_did=request.issuer_did,
                audience_did=request.audience_did,
                abilities=request.abilities,
                purpose=request.purpose,
                issuer_secret=_key_from_optional_hex(request.issuer_key_hex),
                audience_secret=_key_from_optional_hex(request.audience_key_hex),
                approval_id=request.approval_id,
                expires_at=request.expires_at,
                max_delegation_depth=request.max_delegation_depth,
                output_types=request.output_types or None,
                user_presence_required=request.user_presence_required,
                extra_caveats=request.caveats,
            )
            return grant.to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/records/{record_id}/analysis-invocations")
    def issue_analysis_invocation(
        wallet_id: str,
        record_id: str,
        request: AnalysisInvocationRequest,
    ) -> Dict[str, Any]:
        try:
            invocation = app_service.issue_record_analysis_invocation(
                wallet_id,
                record_id,
                grant_id=request.grant_id,
                actor_did=request.actor_did,
                actor_secret=_key_from_optional_hex(request.actor_key_hex),
                expires_at=request.expires_at,
                purpose=request.purpose,
                output_types=request.output_types or None,
                user_present=request.user_present,
            )
            return {"invocation": invocation.to_dict(), "token": invocation_to_token(invocation)}
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/records/{record_id}/decrypt-invocations")
    def issue_decrypt_invocation(
        wallet_id: str,
        record_id: str,
        request: AnalysisInvocationRequest,
    ) -> Dict[str, Any]:
        try:
            invocation = app_service.issue_record_decrypt_invocation(
                wallet_id,
                record_id,
                grant_id=request.grant_id,
                actor_did=request.actor_did,
                actor_secret=_key_from_optional_hex(request.actor_key_hex),
                expires_at=request.expires_at,
                purpose=request.purpose,
                output_types=request.output_types or None,
                user_present=request.user_present,
            )
            return {"invocation": invocation.to_dict(), "token": invocation_to_token(invocation)}
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/access-requests")
    def request_access(wallet_id: str, request: AccessRequestCreateRequest) -> Dict[str, Any]:
        try:
            access_request = app_service.request_record_access(
                wallet_id,
                request.record_id,
                requester_did=request.requester_did,
                ability=request.ability,
                audience_did=request.audience_did,
                purpose=request.purpose,
                expires_at=request.expires_at,
            )
            return access_request.to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/wallets/{wallet_id}/access-requests")
    def list_access_requests(
        wallet_id: str,
        status: str = "pending",
        requester_did: str | None = None,
        audience_did: str | None = None,
    ) -> Dict[str, Any]:
        try:
            normalized_status = None if status == "all" else status
            requests = app_service.access_request_review_items(
                wallet_id,
                status=normalized_status,
                requester_did=requester_did,
                audience_did=audience_did,
            )
            return {"requests": requests}
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/access-requests/{request_id}/approve")
    def approve_access_request(
        wallet_id: str,
        request_id: str,
        request: AccessRequestDecisionRequest,
    ) -> Dict[str, Any]:
        try:
            access_request = app_service.approve_access_request(
                wallet_id,
                request_id=request_id,
                actor_did=request.actor_did,
                issuer_secret=_key_from_optional_hex(request.issuer_key_hex),
                audience_secret=_key_from_optional_hex(request.audience_key_hex),
                approval_id=request.approval_id,
                issue_invocation=request.issue_invocation,
                invocation_expires_at=request.invocation_expires_at,
            )
            response = access_request.to_dict()
            if access_request.invocation_id:
                invocation = app_service.wallet_service.invocations[access_request.invocation_id]
                response["invocation_token"] = invocation_to_token(invocation)
            return response
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/access-requests/{request_id}/reject")
    def reject_access_request(
        wallet_id: str,
        request_id: str,
        request: AccessRequestDecisionRequest,
    ) -> Dict[str, Any]:
        try:
            access_request = app_service.reject_access_request(
                wallet_id,
                request_id=request_id,
                actor_did=request.actor_did,
                reason=request.reason,
            )
            return access_request.to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/access-requests/{request_id}/revoke")
    def revoke_access_request(
        wallet_id: str,
        request_id: str,
        request: AccessRequestDecisionRequest,
    ) -> Dict[str, Any]:
        try:
            access_request = app_service.revoke_access_request(
                wallet_id,
                request_id=request_id,
                actor_did=request.actor_did,
                reason=request.reason,
            )
            return access_request.to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/approvals")
    def request_threshold_approval(
        wallet_id: str,
        request: ThresholdApprovalCreateRequest,
    ) -> Dict[str, Any]:
        try:
            approval = app_service.request_threshold_approval(
                wallet_id,
                requested_by=request.requested_by,
                operation=request.operation,
                resources=request.resources,
                abilities=request.abilities,
                expires_at=request.expires_at,
            )
            return approval.to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/wallets/{wallet_id}/approvals")
    def list_threshold_approvals(wallet_id: str, status: str = "all") -> Dict[str, Any]:
        try:
            normalized_status = None if status == "all" else status
            approvals = app_service.list_threshold_approvals(wallet_id, status=normalized_status)
            return {"approvals": [approval.to_dict() for approval in approvals]}
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/approvals/{approval_id}/approve")
    def approve_threshold_approval(
        wallet_id: str,
        approval_id: str,
        request: ThresholdApprovalDecisionRequest,
    ) -> Dict[str, Any]:
        try:
            approval = app_service.approve_threshold_approval(
                wallet_id,
                approval_id=approval_id,
                approver_did=request.approver_did,
            )
            return approval.to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/grants/{grant_id}/revoke")
    def revoke_grant(wallet_id: str, grant_id: str, request: RevokeGrantRequest) -> Dict[str, Any]:
        try:
            grant = app_service.revoke_grant(wallet_id, grant_id, actor_did=request.actor_did)
            return grant.to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/emergency-revoke")
    def emergency_revoke(wallet_id: str, request: EmergencyRevokeRequest) -> Dict[str, Any]:
        try:
            return app_service.emergency_revoke(
                wallet_id,
                actor_did=request.actor_did,
                actor_secret=_key_from_optional_hex(request.actor_key_hex),
                approval_id=request.approval_id,
                rotate_keys=request.rotate_keys,
                reason=request.reason,
            )
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/grants/{parent_grant_id}/delegate")
    def delegate_grant(
        wallet_id: str,
        parent_grant_id: str,
        request: DelegateGrantRequest,
    ) -> Dict[str, Any]:
        try:
            grant = app_service.delegate_grant(
                wallet_id,
                parent_grant_id=parent_grant_id,
                issuer_did=request.issuer_did,
                audience_did=request.audience_did,
                resources=request.resources,
                abilities=request.abilities,
                caveats=request.caveats,
                expires_at=request.expires_at,
                issuer_secret=_key_from_optional_hex(request.issuer_key_hex),
                audience_secret=_key_from_optional_hex(request.audience_key_hex),
            )
            return grant.to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/wallets/{wallet_id}/grant-receipts")
    def list_grant_receipts(
        wallet_id: str,
        audience_did: str | None = None,
        status: str = "all",
    ) -> Dict[str, Any]:
        try:
            normalized_status = None if status == "all" else status
            receipts = app_service.list_grant_receipts(
                wallet_id,
                audience_did=audience_did,
                status=normalized_status,
            )
            return {"receipts": [receipt.to_dict() for receipt in receipts]}
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/exports/grants")
    def create_export_grant(wallet_id: str, request: ExportGrantRequest) -> Dict[str, Any]:
        try:
            if not request.record_ids:
                raise ValueError("export grants require at least one record_id")
            grant = app_service.create_export_grant(
                wallet_id,
                issuer_did=request.issuer_did,
                audience_did=request.audience_did,
                record_ids=request.record_ids,
                issuer_secret=_key_from_optional_hex(request.issuer_key_hex),
                audience_secret=_key_from_optional_hex(request.audience_key_hex),
                purpose=request.purpose,
                expires_at=request.expires_at,
                approval_id=request.approval_id,
                output_types=request.output_types or None,
            )
            return grant.to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/exports/invocations")
    def issue_export_invocation(wallet_id: str, request: ExportInvocationRequest) -> Dict[str, Any]:
        try:
            invocation = app_service.issue_export_invocation(
                wallet_id,
                grant_id=request.grant_id,
                actor_did=request.actor_did,
                actor_secret=_key_from_optional_hex(request.actor_key_hex),
                record_ids=request.record_ids or None,
                expires_at=request.expires_at,
                purpose=request.purpose,
                output_types=request.output_types or None,
                user_present=request.user_present,
            )
            return {
                **invocation.to_dict(),
                "invocation_token": invocation_to_token(invocation),
            }
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/exports")
    def create_export_bundle(wallet_id: str, request: ExportBundleRequest) -> Dict[str, Any]:
        try:
            if request.invocation_token:
                return app_service.create_export_bundle_with_invocation(
                    wallet_id,
                    actor_did=request.actor_did,
                    invocation=invocation_from_token(request.invocation_token),
                    actor_secret=_key_from_optional_hex(request.actor_key_hex),
                    record_ids=request.record_ids or None,
                    include_proofs=request.include_proofs,
                    include_derived_artifacts=request.include_derived_artifacts,
                )
            return app_service.create_export_bundle(
                wallet_id,
                actor_did=request.actor_did,
                grant_id=request.grant_id,
                record_ids=request.record_ids or None,
                include_proofs=request.include_proofs,
                include_derived_artifacts=request.include_derived_artifacts,
            )
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/exports/verify")
    def verify_export_bundle(request: ExportBundleVerifyRequest) -> Dict[str, Any]:
        try:
            return app_service.verify_export_bundle(request.bundle)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/exports/import")
    def import_export_bundle(request: ExportBundleImportRequest) -> Dict[str, Any]:
        try:
            return app_service.import_export_bundle(request.bundle)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/exports/storage")
    def verify_export_bundle_storage(request: ExportBundleStorageRequest) -> Dict[str, Any]:
        try:
            return app_service.verify_export_bundle_storage(request.bundle)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/records/{record_id}/decrypt")
    def decrypt_record(
        wallet_id: str,
        record_id: str,
        request: DecryptRecordRequest,
    ) -> Dict[str, Any]:
        try:
            actor_secret = _key_from_optional_hex(request.actor_key_hex)
            if request.invocation_token:
                plaintext = app_service.decrypt_record_with_invocation(
                    wallet_id,
                    record_id,
                    actor_did=request.actor_did,
                    invocation=invocation_from_token(request.invocation_token),
                    actor_secret=actor_secret,
                )
            else:
                plaintext = app_service.decrypt_record_for_delegate(
                    wallet_id,
                    record_id,
                    actor_did=request.actor_did,
                    grant_id=request.grant_id,
                    actor_secret=actor_secret,
                )
            return {
                "size_bytes": len(plaintext),
                "text": plaintext.decode("utf-8", errors="replace"),
                "base64": base64.b64encode(plaintext).decode("ascii"),
            }
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/records/{record_id}/analyze")
    def analyze_record(
        wallet_id: str,
        record_id: str,
        request: AnalyzeRecordRequest,
    ) -> Dict[str, Any]:
        try:
            actor_secret = _key_from_optional_hex(request.actor_key_hex)
            if request.invocation_token:
                artifact = app_service.analyze_record_with_invocation(
                    wallet_id,
                    record_id,
                    actor_did=request.actor_did,
                    invocation=invocation_from_token(request.invocation_token),
                    actor_secret=actor_secret,
                    max_chars=request.max_chars,
                )
            else:
                artifact = app_service.analyze_record_for_delegate(
                    wallet_id,
                    record_id,
                    actor_did=request.actor_did,
                    grant_id=request.grant_id or "",
                    actor_secret=actor_secret,
                    max_chars=request.max_chars,
                )
            return artifact.to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/records/{record_id}/analyze/redacted")
    def analyze_record_redacted(
        wallet_id: str,
        record_id: str,
        request: RedactedAnalyzeRecordRequest,
    ) -> Dict[str, Any]:
        try:
            actor_secret = _key_from_optional_hex(request.actor_key_hex)
            if request.invocation_token:
                result = app_service.analyze_record_redacted_with_invocation(
                    wallet_id,
                    record_id,
                    actor_did=request.actor_did,
                    invocation=invocation_from_token(request.invocation_token),
                    actor_secret=actor_secret,
                    max_chars=request.max_chars,
                )
            else:
                result = app_service.analyze_record_redacted(
                    wallet_id,
                    record_id,
                    actor_did=request.actor_did,
                    grant_id=request.grant_id,
                    actor_secret=actor_secret,
                    max_chars=request.max_chars,
                )
            return _analysis_result_to_dict(result)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/records/{record_id}/vector-profile")
    def create_document_vector_profile(
        wallet_id: str,
        record_id: str,
        request: VectorProfileRequest,
    ) -> Dict[str, Any]:
        try:
            actor_secret = _key_from_optional_hex(request.actor_key_hex)
            if request.invocation_token:
                result = app_service.create_document_vector_profile_with_invocation(
                    wallet_id,
                    record_id,
                    actor_did=request.actor_did,
                    invocation=invocation_from_token(request.invocation_token),
                    actor_secret=actor_secret,
                    chunk_size_words=request.chunk_size_words,
                )
            else:
                result = app_service.create_document_vector_profile(
                    wallet_id,
                    record_id,
                    actor_did=request.actor_did,
                    grant_id=request.grant_id,
                    actor_secret=actor_secret,
                    chunk_size_words=request.chunk_size_words,
                )
            return _analysis_result_to_dict(result)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/records/{record_id}/extract-text/redacted")
    def extract_record_text_redacted(
        wallet_id: str,
        record_id: str,
        request: RedactedTextExtractionRequest,
    ) -> Dict[str, Any]:
        try:
            actor_secret = _key_from_optional_hex(request.actor_key_hex)
            if request.invocation_token:
                result = app_service.extract_record_text_redacted_with_invocation(
                    wallet_id,
                    record_id,
                    actor_did=request.actor_did,
                    invocation=invocation_from_token(request.invocation_token),
                    actor_secret=actor_secret,
                    max_chars=request.max_chars,
                    max_bytes=request.max_bytes,
                    use_ocr=request.use_ocr,
                )
            else:
                result = app_service.extract_record_text_redacted(
                    wallet_id,
                    record_id,
                    actor_did=request.actor_did,
                    grant_id=request.grant_id,
                    actor_secret=actor_secret,
                    max_chars=request.max_chars,
                    max_bytes=request.max_bytes,
                    use_ocr=request.use_ocr,
                )
            return _analysis_result_to_dict(result)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/records/{record_id}/forms/analyze/redacted")
    def analyze_record_form_redacted(
        wallet_id: str,
        record_id: str,
        request: RedactedFormAnalysisRequest,
    ) -> Dict[str, Any]:
        try:
            actor_secret = _key_from_optional_hex(request.actor_key_hex)
            if request.invocation_token:
                result = app_service.analyze_record_form_redacted_with_invocation(
                    wallet_id,
                    record_id,
                    actor_did=request.actor_did,
                    invocation=invocation_from_token(request.invocation_token),
                    actor_secret=actor_secret,
                    max_fields=request.max_fields,
                    use_ocr=request.use_ocr,
                )
            else:
                result = app_service.analyze_record_form_redacted(
                    wallet_id,
                    record_id,
                    actor_did=request.actor_did,
                    grant_id=request.grant_id,
                    actor_secret=actor_secret,
                    max_fields=request.max_fields,
                    use_ocr=request.use_ocr,
                )
            return _analysis_result_to_dict(result)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/records/analyze/redacted")
    def analyze_records_redacted(
        wallet_id: str,
        request: RedactedAnalyzeRecordsRequest,
    ) -> Dict[str, Any]:
        try:
            if not request.record_ids:
                raise ValueError("redacted cross-record analysis requires at least one record_id")
            result = app_service.analyze_records_redacted(
                wallet_id,
                request.record_ids,
                actor_did=request.actor_did,
                grant_id=request.grant_id,
                actor_secret=_key_from_optional_hex(request.actor_key_hex),
            )
            return _analysis_result_to_dict(result)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/records/graphrag/redacted")
    def create_redacted_graphrag(
        wallet_id: str,
        request: RedactedGraphRAGRequest,
    ) -> Dict[str, Any]:
        try:
            if not request.record_ids:
                raise ValueError("redacted GraphRAG creation requires at least one record_id")
            actor_secret = _key_from_optional_hex(request.actor_key_hex)
            if request.invocation_token:
                result = app_service.create_redacted_graphrag_with_invocation(
                    wallet_id,
                    request.record_ids,
                    actor_did=request.actor_did,
                    invocation=invocation_from_token(request.invocation_token),
                    actor_secret=actor_secret,
                    max_chars_per_record=request.max_chars_per_record,
                    max_bytes_per_record=request.max_bytes_per_record,
                    use_ocr=request.use_ocr,
                )
            else:
                result = app_service.create_redacted_graphrag(
                    wallet_id,
                    request.record_ids,
                    actor_did=request.actor_did,
                    grant_id=request.grant_id,
                    actor_secret=actor_secret,
                    max_chars_per_record=request.max_chars_per_record,
                    max_bytes_per_record=request.max_bytes_per_record,
                    use_ocr=request.use_ocr,
                )
            return _analysis_result_to_dict(result)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/records/{record_id}/metadata/generate")
    def generate_wallet_record_metadata(
        wallet_id: str,
        record_id: str,
        request: WalletRecordMetadataGenerationRequest,
    ) -> Dict[str, Any]:
        try:
            wallet_cid = _wallet_router_subject(wallet_id, request.wallet_cid)
            limit = _check_wallet_router_rate_limit(wallet_cid, cost=4)
            actor_secret = _key_from_optional_hex(request.actor_key_hex)
            invocation = invocation_from_token(request.invocation_token) if request.invocation_token else None
            metadata_status = app_service.update_record_metadata(
                wallet_id,
                record_id,
                actor_did=request.actor_did,
                metadata={
                    "privacyProfileMessage": "Creating redacted GraphRAG, vector metadata, and wallet router labels.",
                    "privacyProfileStatus": "profiling",
                    **({"privacyProfileMimeType": request.mime_type} if request.mime_type else {}),
                },
            )

            derived_results: List[Dict[str, Any]] = []
            result_errors: List[str] = []
            for create_result in (
                lambda: app_service.analyze_record_redacted_with_invocation(
                    wallet_id,
                    record_id,
                    actor_did=request.actor_did,
                    invocation=invocation,
                    actor_secret=actor_secret,
                    max_chars=500,
                )
                if invocation
                else app_service.analyze_record_redacted(
                    wallet_id,
                    record_id,
                    actor_did=request.actor_did,
                    grant_id=request.grant_id,
                    actor_secret=actor_secret,
                    max_chars=500,
                ),
                lambda: app_service.create_document_vector_profile_with_invocation(
                    wallet_id,
                    record_id,
                    actor_did=request.actor_did,
                    invocation=invocation,
                    actor_secret=actor_secret,
                    chunk_size_words=80,
                )
                if invocation
                else app_service.create_document_vector_profile(
                    wallet_id,
                    record_id,
                    actor_did=request.actor_did,
                    grant_id=request.grant_id,
                    actor_secret=actor_secret,
                    chunk_size_words=80,
                ),
                lambda: app_service.create_redacted_graphrag_with_invocation(
                    wallet_id,
                    [record_id],
                    actor_did=request.actor_did,
                    invocation=invocation,
                    actor_secret=actor_secret,
                    max_chars_per_record=request.max_chars_per_record,
                    max_bytes_per_record=request.max_bytes_per_record,
                    use_ocr=request.use_ocr,
                )
                if invocation
                else app_service.create_redacted_graphrag(
                    wallet_id,
                    [record_id],
                    actor_did=request.actor_did,
                    grant_id=request.grant_id,
                    actor_secret=actor_secret,
                    max_chars_per_record=request.max_chars_per_record,
                    max_bytes_per_record=request.max_bytes_per_record,
                    use_ocr=request.use_ocr,
                ),
                lambda: app_service.extract_record_text_redacted_with_invocation(
                    wallet_id,
                    record_id,
                    actor_did=request.actor_did,
                    invocation=invocation,
                    actor_secret=actor_secret,
                    max_chars=12_000,
                    max_bytes=request.max_bytes_per_record,
                    use_ocr=request.use_ocr,
                )
                if invocation
                else app_service.extract_record_text_redacted(
                    wallet_id,
                    record_id,
                    actor_did=request.actor_did,
                    grant_id=request.grant_id,
                    actor_secret=actor_secret,
                    max_chars=12_000,
                    max_bytes=request.max_bytes_per_record,
                    use_ocr=request.use_ocr,
                ),
                lambda: app_service.analyze_record_form_redacted_with_invocation(
                    wallet_id,
                    record_id,
                    actor_did=request.actor_did,
                    invocation=invocation,
                    actor_secret=actor_secret,
                    max_fields=100,
                    use_ocr=request.use_ocr,
                )
                if invocation
                else app_service.analyze_record_form_redacted(
                    wallet_id,
                    record_id,
                    actor_did=request.actor_did,
                    grant_id=request.grant_id,
                    actor_secret=actor_secret,
                    max_fields=100,
                    use_ocr=request.use_ocr,
                ),
            ):
                try:
                    derived_results.append(create_result())
                except Exception as exc:
                    result_errors.append(str(exc))

            outputs = [_derived_output(result) for result in derived_results if _derived_output(result)]
            if not outputs:
                outputs.append(
                    _fallback_document_profile_output(
                        file_name=request.file_name or record_id,
                        mime_type=request.mime_type or _record_metadata_value(metadata_status, "privacyProfileMimeType") or "application/octet-stream",
                    )
                )
            organizer_profile = _generate_wallet_organizer_profile(
                wallet_id=wallet_id,
                wallet_cid=wallet_cid,
                file_name=request.file_name or _record_metadata_value(metadata_status, "fileName") or record_id,
                mime_type=request.mime_type or _record_metadata_value(metadata_status, "privacyProfileMimeType") or "application/octet-stream",
                outputs=outputs,
                provider=request.provider,
                model_name=request.model_name,
                kwargs=request.kwargs,
            )
            if organizer_profile:
                outputs.append(
                    {
                        "openrouter_organizer_profile": organizer_profile,
                        "output_policy": "redacted_wallet_router_organizer",
                    }
                )
            artifact_ids = [_derived_artifact_id(result) for result in derived_results]
            artifact_ids = [artifact_id for artifact_id in artifact_ids if artifact_id]
            public_inputs = _build_document_profile_public_inputs(
                artifact_ids=artifact_ids,
                file_name=request.file_name or _record_metadata_value(metadata_status, "fileName") or record_id,
                mime_type=request.mime_type or _record_metadata_value(metadata_status, "privacyProfileMimeType") or "application/octet-stream",
                outputs=outputs,
            )
            proof = app_service.create_document_profile_proof(
                wallet_id,
                record_id,
                actor_did=request.actor_did,
                public_inputs=public_inputs,
            )
            metadata_patch = {
                "privacyProfileArtifactIds": artifact_ids,
                "privacyProfileClassification": _classify_document_profile(public_inputs),
                "privacyProfileLabels": _read_string_list(public_inputs.get("organizer_labels")) or _default_labels_for_mime_type(str(public_inputs.get("mime_type") or "")),
                "privacyProfileMessage": "Safe document profile and proof are attached to this wallet record.",
                "privacyProfileMimeType": public_inputs.get("mime_type"),
                "privacyProfileNeedsRefresh": False,
                "privacyProfileProofId": proof.proof_id,
                "privacyProfilePublicInputs": public_inputs,
                "privacyProfileSearchText": _build_privacy_search_text(outputs, public_inputs),
                "privacyProfileStatus": "profiled",
                "privacyProfileSummary": _summarize_document_profile(public_inputs),
                "privacyProfileVectorTerms": _build_privacy_vector_terms(outputs, public_inputs),
                "walletRouterRateLimit": limit,
            }
            if result_errors:
                metadata_patch["privacyProfileWarnings"] = result_errors[:5]
            record = app_service.update_record_metadata(
                wallet_id,
                record_id,
                actor_did=request.actor_did,
                metadata=metadata_patch,
            )
            metadata_ipld_patch = _publish_record_metadata_ipld(record)
            if metadata_ipld_patch:
                record = app_service.update_record_metadata(
                    wallet_id,
                    record_id,
                    actor_did=request.actor_did,
                    metadata=metadata_ipld_patch,
                )
            return {
                "record": record,
                "metadata": record.get("metadata", {}),
                "proof": proof.to_dict(),
                "router": {
                    "wallet_id": wallet_id,
                    "wallet_cid": wallet_cid,
                    "provider": request.provider,
                    "model_name": request.model_name,
                    "rate_limit": limit,
                },
            }
        except ValueError as exc:
            raise HTTPException(status_code=429 if "rate limit" in str(exc).lower() else 400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/records/{record_id}/rotate-key")
    def rotate_record_key(
        wallet_id: str,
        record_id: str,
        request: RotateRecordKeyRequest,
    ) -> Dict[str, Any]:
        try:
            version = app_service.rotate_record_key(
                wallet_id,
                record_id,
                actor_did=request.actor_did,
                actor_secret=_key_from_optional_hex(request.actor_key_hex),
            )
            return version.to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/wallets/{wallet_id}/records/{record_id}/storage")
    def verify_record_storage(wallet_id: str, record_id: str) -> Dict[str, Any]:
        try:
            report = app_service.verify_record_storage(wallet_id, record_id)
            return report.to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/wallets/{wallet_id}/storage")
    def verify_wallet_storage(wallet_id: str) -> Dict[str, Any]:
        try:
            report = app_service.verify_wallet_storage(wallet_id)
            return report.to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/storage/repair")
    def repair_wallet_storage(wallet_id: str, request: RepairStorageRequest) -> Dict[str, Any]:
        try:
            report = app_service.repair_wallet_storage(wallet_id, actor_did=request.actor_did)
            return report.to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/records/{record_id}/storage/repair")
    def repair_record_storage(
        wallet_id: str,
        record_id: str,
        request: RepairStorageRequest,
    ) -> Dict[str, Any]:
        try:
            report = app_service.repair_record_storage(
                wallet_id,
                record_id,
                actor_did=request.actor_did,
            )
            return report.to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/services/match")
    def match_services_for_wallet(wallet_id: str, request: WalletServiceMatchRequest) -> Dict[str, Any]:
        try:
            if request.invocation_token:
                matches = app_service.match_services_for_wallet_with_invocation(
                    wallet_id,
                    request.location_record_id,
                    actor_did=request.actor_did,
                    invocation=invocation_from_token(request.invocation_token),
                    actor_secret=_key_from_optional_hex(request.actor_key_hex),
                    need_terms=list(request.need_terms),
                    limit=request.limit,
                )
            else:
                matches = app_service.match_services_for_wallet(
                    wallet_id,
                    request.location_record_id,
                    actor_did=request.actor_did,
                    grant_id=request.grant_id,
                    need_terms=list(request.need_terms),
                    limit=request.limit,
                )
            return {"matches": [_match_to_dict(match) for match in matches]}
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/wallets/{wallet_id}/audit")
    def audit_timeline(wallet_id: str) -> Dict[str, Any]:
        try:
            return {"events": app_service.audit_timeline(wallet_id)}
        except Exception as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/wallets/{wallet_id}/proofs")
    def list_proof_receipts(wallet_id: str) -> Dict[str, Any]:
        try:
            return {"proofs": [proof.to_dict() for proof in app_service.list_proof_receipts(wallet_id)]}
        except Exception as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/analytics/templates")
    def create_analytics_template(request: AnalyticsTemplateRequest) -> Dict[str, Any]:
        try:
            template = app_service.create_analytics_template(
                template_id=request.template_id,
                title=request.title,
                purpose=request.purpose,
                allowed_record_types=request.allowed_record_types,
                allowed_derived_fields=request.allowed_derived_fields,
                min_cohort_size=request.min_cohort_size,
                epsilon_budget=request.epsilon_budget,
                created_by=request.created_by,
                status=request.status,
                expires_at=request.expires_at,
            )
            return template.to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/analytics/templates")
    def list_analytics_templates(include_inactive: bool = False) -> Dict[str, Any]:
        return {
            "templates": [
                template.to_dict()
                for template in app_service.list_analytics_templates(include_inactive=include_inactive)
            ]
        }

    @app.get("/wallets/{wallet_id}/analytics/consents")
    def list_analytics_consents(wallet_id: str, status: str = "all") -> Dict[str, Any]:
        try:
            return {
                "consents": [
                    consent.to_dict()
                    for consent in app_service.list_analytics_consents(wallet_id, status=status)
                ]
            }
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/analytics/consents/from-template")
    def create_analytics_consent_from_template(
        wallet_id: str,
        request: AnalyticsConsentFromTemplateRequest,
    ) -> Dict[str, Any]:
        try:
            consent = app_service.create_analytics_consent_from_template(
                wallet_id,
                actor_did=request.actor_did,
                template_id=request.template_id,
                expires_at=request.expires_at,
            )
            return consent.to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/analytics/consents/{consent_id}/revoke")
    def revoke_analytics_consent(
        wallet_id: str,
        consent_id: str,
        request: AnalyticsConsentRevokeRequest,
    ) -> Dict[str, Any]:
        try:
            consent = app_service.revoke_analytics_consent(
                wallet_id,
                consent_id,
                actor_did=request.actor_did,
            )
            return consent.to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/wallets/{wallet_id}/analytics/contributions")
    def create_analytics_contribution(
        wallet_id: str,
        request: AnalyticsContributionRequest,
    ) -> Dict[str, Any]:
        try:
            contribution = app_service.contribute_analytics_facts(
                wallet_id,
                actor_did=request.actor_did,
                consent_id=request.consent_id,
                template_id=request.template_id,
                fields=request.fields,
            )
            return contribution.to_dict()
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/analytics/{template_id}/count")
    def run_private_aggregate_count(
        template_id: str,
        request: PrivateAggregateCountRequest,
    ) -> Dict[str, Any]:
        try:
            result = app_service.run_private_aggregate_count(
                template_id,
                epsilon=request.epsilon,
                min_cohort_size=request.min_cohort_size,
                budget_key=request.budget_key,
                budget_limit=request.budget_limit,
                actor_did=request.actor_did,
            )
            return app_service.summarize_aggregate_result(result)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/analytics/{template_id}/count-by-fields")
    def run_private_aggregate_count_by_fields(
        template_id: str,
        request: PrivateAggregateCohortCountRequest,
    ) -> Dict[str, Any]:
        try:
            result = app_service.run_private_aggregate_count_by_fields(
                template_id,
                group_by=request.group_by,
                epsilon=request.epsilon,
                min_cohort_size=request.min_cohort_size,
                budget_key=request.budget_key,
                budget_limit=request.budget_limit,
                actor_did=request.actor_did,
            )
            return app_service.summarize_aggregate_result(result)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/services/match-derived")
    def match_services_from_derived(request: DerivedServiceMatchRequest) -> Dict[str, Any]:
        try:
            matches = app_service.match_services_from_derived_facts(
                derived_facts={
                    "need_terms": list(request.need_terms),
                    "location_claim": request.location_claim,
                },
                limit=request.limit,
            )
            return {
                "matches": [_match_to_dict(match) for match in matches]
            }
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    return app


def _match_to_dict(match) -> Dict[str, Any]:
    return {
        "service": match.service.__dict__,
        "score": match.score,
        "reasons": list(match.reasons),
    }


def _analysis_result_to_dict(result: Dict[str, Any]) -> Dict[str, Any]:
    artifact = result["artifact"]
    artifact_data = artifact.to_dict() if hasattr(artifact, "to_dict") else dict(artifact)
    return {
        "artifact": artifact_data,
        "output": result["output"],
    }


def _wallet_router_subject(wallet_id: str, wallet_cid: str | None) -> str:
    normalized_cid = _normalize_ipfs_cid(str(wallet_cid or ""))
    if normalized_cid and _valid_ipfs_cid(normalized_cid):
        return normalized_cid
    if str(wallet_cid or "").strip():
        return re.sub(r"[^a-zA-Z0-9:._-]+", "-", str(wallet_cid).strip())[:160]
    return re.sub(r"[^a-zA-Z0-9:._-]+", "-", str(wallet_id or "unknown-wallet").strip())[:160]


def _require_wallet_router_actor(
    app_service: WalletInterfaceService,
    wallet_id: str,
    actor_did: str,
) -> None:
    wallet = app_service.get_wallet(wallet_id)
    actor = str(actor_did or "").strip()
    principals = {
        str(wallet.owner_did),
        *[str(item) for item in getattr(wallet, "controller_dids", [])],
        *[str(item) for item in getattr(wallet, "device_dids", [])],
    }
    if not actor:
        raise ValueError("actor_did is required")
    if actor not in principals:
        raise ValueError("actor_did is not authorized for this wallet")


def _wallet_router_rate_limit_per_minute() -> int:
    try:
        return max(1, int(os.getenv("WALLET_AI_ROUTER_RATE_LIMIT_PER_MINUTE", "30")))
    except Exception:
        return 30


def _wallet_router_rate_limit_per_day() -> int:
    try:
        return max(1, int(os.getenv("WALLET_AI_ROUTER_RATE_LIMIT_PER_DAY", "500")))
    except Exception:
        return 500


def _check_wallet_router_rate_limit(wallet_subject: str, *, cost: int = 1) -> Dict[str, Any]:
    subject = wallet_subject or "unknown-wallet"
    now = time.time()
    minute_window = int(now // 60)
    day_window = int(now // 86400)
    state = _AI_ROUTER_RATE_LIMITS.setdefault(
        subject,
        {"minute_window": minute_window, "minute_count": 0, "day_window": day_window, "day_count": 0},
    )
    if state.get("minute_window") != minute_window:
        state["minute_window"] = minute_window
        state["minute_count"] = 0
    if state.get("day_window") != day_window:
        state["day_window"] = day_window
        state["day_count"] = 0
    per_minute = _wallet_router_rate_limit_per_minute()
    per_day = _wallet_router_rate_limit_per_day()
    next_minute = int(state.get("minute_count") or 0) + max(1, int(cost or 1))
    next_day = int(state.get("day_count") or 0) + max(1, int(cost or 1))
    if next_minute > per_minute:
        raise ValueError(f"wallet router rate limit exceeded for {subject}: {per_minute} requests per minute")
    if next_day > per_day:
        raise ValueError(f"wallet router rate limit exceeded for {subject}: {per_day} requests per day")
    state["minute_count"] = next_minute
    state["day_count"] = next_day
    return {
        "subject": subject,
        "cost": max(1, int(cost or 1)),
        "minuteLimit": per_minute,
        "minuteRemaining": max(0, per_minute - next_minute),
        "dayLimit": per_day,
        "dayRemaining": max(0, per_day - next_day),
    }


def _derived_output(result: Mapping[str, Any]) -> Dict[str, Any]:
    output = result.get("output")
    return dict(output) if isinstance(output, Mapping) else {}


def _derived_artifact_id(result: Mapping[str, Any]) -> str:
    artifact = result.get("artifact")
    if hasattr(artifact, "artifact_id"):
        return str(getattr(artifact, "artifact_id") or "")
    if hasattr(artifact, "id"):
        return str(getattr(artifact, "id") or "")
    if isinstance(artifact, Mapping):
        return str(artifact.get("artifact_id") or artifact.get("id") or "")
    return ""


def _record_metadata_value(record: Mapping[str, Any], key: str) -> str:
    metadata = record.get("metadata")
    if isinstance(metadata, Mapping):
        value = metadata.get(key)
        if isinstance(value, str):
            return value
    return ""


def _safe_short_text(value: Any, *, limit: int = 240) -> str:
    text = str(value or "")
    text = re.sub(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", "[email]", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:\+?1[\s.-]?)?(?:\(\d{3}\)|\d{3})[\s.-]?\d{3}[\s.-]?\d{4}\b", "[phone]", text)
    text = re.sub(r"\b\d{4,}\b", "[number]", text)
    return text.strip()[:limit]


def _safe_organizer_signal(output: Mapping[str, Any]) -> Dict[str, Any]:
    signal: Dict[str, Any] = {
        "output_policy": _safe_short_text(output.get("output_policy")),
        "summary": _safe_short_text(output.get("summary")),
        "text": _safe_short_text(output.get("text")),
    }
    profile = output.get("profile")
    if isinstance(profile, Mapping):
        signal["profile"] = {
            key: profile.get(key)
            for key in ("profile_type", "chunk_count")
            if profile.get(key) is not None
        }
    graph = output.get("graph")
    if isinstance(graph, Mapping):
        signal["graph"] = {
            key: graph.get(key)
            for key in ("graph_type", "node_count", "edge_count")
            if graph.get(key) is not None
        }
    return {key: value for key, value in signal.items() if value not in ("", None, {})}


def _redacted_file_name(file_name: str) -> str:
    _, dot, extension = str(file_name or "").rpartition(".")
    return f"document.{extension.lower()}" if dot and extension else "document"


def _generate_wallet_organizer_profile(
    *,
    wallet_id: str,
    wallet_cid: str,
    file_name: str,
    mime_type: str,
    outputs: Sequence[Mapping[str, Any]],
    provider: str | None,
    model_name: str | None,
    kwargs: Mapping[str, Any] | None,
) -> Dict[str, Any] | None:
    safe_signals = [_safe_organizer_signal(output) for output in outputs]
    safe_signals = [signal for signal in safe_signals if signal]
    if not safe_signals:
        return None
    try:
        _check_wallet_router_rate_limit(wallet_cid or wallet_id)
        from ipfs_datasets_py import llm_router  # noqa: WPS433

        prompt = "\n".join(
            [
                "Create privacy-preserving organizer metadata from redacted wallet document signals.",
                "Return only one JSON object with keys: summary, labels, browseHints, riskSignals.",
                "Use generic non-identifying language only.",
                json.dumps(
                    {
                        "fileName": _redacted_file_name(file_name),
                        "mimeType": mime_type,
                        "redactedSignals": safe_signals[:8],
                    },
                    sort_keys=True,
                ),
            ]
        )
        text = llm_router.generate_text(
            prompt,
            model_name=model_name,
            provider=provider or "hf_inference_api",
            **dict(kwargs or {}),
        )
        parsed = _parse_first_json_object(text)
        if not parsed:
            return None
        return {
            "summary": _safe_short_text(parsed.get("summary")),
            "labels": _read_string_list(parsed.get("labels"), limit=8),
            "browseHints": _read_string_list(parsed.get("browseHints"), limit=8),
            "riskSignals": _read_string_list(parsed.get("riskSignals"), limit=8),
            "model": model_name or provider or "wallet-router",
        }
    except Exception:
        return None


def _parse_first_json_object(text: str) -> Dict[str, Any] | None:
    trimmed = str(text or "").strip()
    start = trimmed.find("{")
    end = trimmed.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        parsed = json.loads(trimmed[start : end + 1])
    except Exception:
        return None
    return dict(parsed) if isinstance(parsed, Mapping) else None


def _read_string_list(value: Any, *, limit: int = 12) -> List[str]:
    if not isinstance(value, list):
        return []
    return [_safe_short_text(item, limit=80) for item in value if _safe_short_text(item, limit=80)][:limit]


def _read_number(record: Mapping[str, Any] | None, key: str) -> int | float | None:
    if not isinstance(record, Mapping):
        return None
    value = record.get(key)
    return value if isinstance(value, (int, float)) else None


def _read_string(record: Mapping[str, Any] | None, key: str) -> str:
    if not isinstance(record, Mapping):
        return ""
    value = record.get(key)
    return str(value).strip() if isinstance(value, str) else ""


def _default_labels_for_mime_type(mime_type: str) -> List[str]:
    normalized = str(mime_type or "").lower()
    if normalized == "application/pdf":
        return ["pdf", "document"]
    if normalized.startswith("image/"):
        return ["image", "visual file"]
    if normalized.startswith("text/"):
        return ["text", "document"]
    if "json" in normalized:
        return ["json", "structured data"]
    if "spreadsheet" in normalized or "excel" in normalized or "csv" in normalized:
        return ["spreadsheet", "tabular data"]
    if "wordprocessing" in normalized or "msword" in normalized:
        return ["word document", "document"]
    if normalized.startswith("audio/"):
        return ["audio"]
    if normalized.startswith("video/"):
        return ["video"]
    return ["wallet file"]


def _display_mime_type(mime_type: str) -> str:
    normalized = str(mime_type or "").strip().lower()
    if not normalized:
        return "Unknown file"
    if normalized == "application/pdf":
        return "PDF document"
    if normalized.startswith("image/"):
        return f"{normalized.split('/', 1)[1].upper()} image"
    if normalized.startswith("text/"):
        return "Text document"
    if "json" in normalized:
        return "JSON data"
    if "spreadsheet" in normalized or "excel" in normalized or "csv" in normalized:
        return "Spreadsheet"
    if "wordprocessing" in normalized or "msword" in normalized:
        return "Word document"
    if normalized.startswith("audio/"):
        return "Audio file"
    if normalized.startswith("video/"):
        return "Video file"
    if normalized == "application/octet-stream":
        return "Encrypted/binary file"
    return normalized


def _fallback_document_profile_output(*, file_name: str, mime_type: str) -> Dict[str, Any]:
    return {
        "output_policy": "local_metadata_only",
        "profile": {"chunk_count": 0, "profile_type": "metadata fallback"},
        "summary": f"{_display_mime_type(mime_type)} wallet file queued for redacted profiling.",
        "upload_state": {"fileName": _redacted_file_name(file_name), "mimeType": mime_type},
    }


def _build_document_profile_public_inputs(
    *,
    artifact_ids: Sequence[str],
    file_name: str,
    mime_type: str,
    outputs: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    graphs = [output.get("graph") for output in outputs]
    graph = next((item for item in graphs if isinstance(item, Mapping)), {})
    profiles = [output.get("profile") for output in outputs]
    profile = next((item for item in profiles if isinstance(item, Mapping)), {})
    organizer_profiles = [output.get("openrouter_organizer_profile") for output in outputs]
    organizer = next((item for item in organizer_profiles if isinstance(item, Mapping)), {})
    redaction_count = 0
    for output in outputs:
        counts = output.get("redaction_counts")
        if isinstance(counts, Mapping):
            redaction_count += sum(value for value in counts.values() if isinstance(value, (int, float)))
    public_mime_type = mime_type or "application/octet-stream"
    labels = _read_string_list(organizer.get("labels")) or _default_labels_for_mime_type(public_mime_type)
    return {
        "artifact_ids": list(artifact_ids),
        "chunk_count": _read_number(profile, "chunk_count"),
        "edge_count": _read_number(graph, "edge_count"),
        "file_name_profile": _redacted_file_name(file_name),
        "graph_type": _read_string(graph, "graph_type"),
        "mime_family": public_mime_type.split("/", 1)[0] or "application",
        "mime_type": public_mime_type,
        "node_count": _read_number(graph, "node_count"),
        "openrouter_model": _read_string(organizer, "model"),
        "organizer_labels": labels,
        "organizer_summary": _read_string(organizer, "summary") or _display_mime_type(public_mime_type),
        "output_policies": sorted({str(output.get("output_policy")) for output in outputs if output.get("output_policy")}),
        "privacy_policy": "no_plaintext_public_inputs",
        "profile_methods": sorted({str(output.get("output_policy")) for output in outputs if output.get("output_policy")}),
        "redaction_count": redaction_count,
        "size_bucket": "server-side",
        "summary": "Redacted GraphRAG, vector metadata, and derived descriptors created inside the wallet boundary.",
    }


def _classify_document_profile(public_inputs: Mapping[str, Any]) -> str:
    summary = _read_string(public_inputs, "organizer_summary")
    if summary:
        return summary
    labels = _read_string_list(public_inputs.get("organizer_labels"), limit=3)
    if labels:
        return ", ".join(labels[:3])
    return _display_mime_type(str(public_inputs.get("mime_type") or ""))


def _summarize_document_profile(public_inputs: Mapping[str, Any]) -> str:
    mime_type = str(public_inputs.get("mime_type") or "document")
    graph_type = str(public_inputs.get("graph_type") or "redacted graph")
    nodes = public_inputs.get("node_count")
    chunks = public_inputs.get("chunk_count")
    nodes_text = f"{nodes} nodes" if isinstance(nodes, (int, float)) else "safe graph"
    chunks_text = f"{chunks} chunks" if isinstance(chunks, (int, float)) else "vector metadata"
    return f"{mime_type} · {graph_type} · {nodes_text} · {chunks_text}"


def _build_privacy_search_text(outputs: Sequence[Mapping[str, Any]], public_inputs: Mapping[str, Any]) -> str:
    parts: List[str] = [
        _classify_document_profile(public_inputs),
        _summarize_document_profile(public_inputs),
        " ".join(_read_string_list(public_inputs.get("organizer_labels"), limit=12)),
        " ".join(str(policy) for policy in public_inputs.get("output_policies", []) if isinstance(policy, str)),
    ]
    for output in outputs:
        parts.append(_safe_short_text(output.get("summary")))
        parts.append(_safe_short_text(output.get("text")))
    return " ".join(part for part in parts if part).strip()


def _build_privacy_vector_terms(outputs: Sequence[Mapping[str, Any]], public_inputs: Mapping[str, Any]) -> List[str]:
    terms: List[str] = []
    terms.extend(_read_string_list(public_inputs.get("organizer_labels"), limit=12))
    for key in ("mime_type", "mime_family", "graph_type", "organizer_summary"):
        value = public_inputs.get(key)
        if isinstance(value, str) and value.strip():
            terms.append(value.strip())
    for output in outputs:
        policy = output.get("output_policy")
        if isinstance(policy, str) and policy.strip():
            terms.append(policy.strip())
    normalized: List[str] = []
    seen = set()
    for term in terms:
        safe = _safe_short_text(term, limit=80).lower()
        if safe and safe not in seen:
            normalized.append(safe)
            seen.add(safe)
    return normalized[:24]


def _indextts_space_base_url() -> str:
    return os.getenv("WALLET_INDEXTTS_SPACE_URL", "https://indexteam-indextts-2-demo.hf.space").strip().rstrip("/")


def _indextts_api_name() -> str:
    return os.getenv("WALLET_INDEXTTS_API_NAME", "gen_single").strip()


def _indextts_timeout_seconds() -> float:
    try:
        return max(5.0, float(os.getenv("WALLET_INDEXTTS_TIMEOUT_SECONDS", "180")))
    except Exception:
        return 180.0


def _indextts_headers(*, accept: str = "application/json") -> Dict[str, str]:
    headers = {"Accept": accept}
    token = (
        resolve_secret(
            "WALLET_INDEXTTS_HF_TOKEN",
            "HF_TOKEN",
            "HUGGINGFACEHUB_API_TOKEN",
            "IPFS_DATASETS_PY_HF_API_TOKEN",
            "HUGGINGFACE_API_TOKEN",
            "HUGGINGFACE_HUB_TOKEN",
        )
        or ""
    ).strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    bill_to = (
        os.getenv("WALLET_INDEXTTS_HF_BILL_TO")
        or os.getenv("IPFS_DATASETS_PY_HF_BILL_TO")
        or "publicus"
    ).strip()
    if bill_to:
        headers["X-HF-Bill-To"] = bill_to
    return headers


def _http_json(method: str, url: str, payload: Mapping[str, Any] | None = None) -> Dict[str, Any]:
    data = None
    headers = _indextts_headers()
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib_request.Request(url, data=data, headers=headers, method=method)
    with urllib_request.urlopen(request, timeout=_indextts_timeout_seconds()) as response:
        raw = response.read()
    parsed = json.loads(raw.decode("utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError(f"{url} did not return a JSON object")
    return parsed


def _http_bytes(url: str) -> tuple[bytes, str]:
    request = urllib_request.Request(url, headers=_indextts_headers(accept="audio/*, application/octet-stream"))
    with urllib_request.urlopen(request, timeout=_indextts_timeout_seconds()) as response:
        return response.read(), response.headers.get("Content-Type") or "audio/wav"


def _indextts_config() -> Dict[str, Any]:
    return _http_json("GET", f"{_indextts_space_base_url()}/config")


def _indextts_fn_index(config: Mapping[str, Any]) -> int:
    raw = os.getenv("WALLET_INDEXTTS_FN_INDEX", "").strip()
    if raw:
        return int(raw)
    api_name = _indextts_api_name()
    dependencies = config.get("dependencies")
    if not isinstance(dependencies, list):
        raise ValueError("IndexTTS Gradio config does not include dependencies")
    candidates: List[Mapping[str, Any]] = [dep for dep in dependencies if isinstance(dep, Mapping)]
    if api_name:
        normalized = api_name if api_name.startswith("/") else f"/{api_name}"
        for dep in candidates:
            if str(dep.get("api_name") or "") in {api_name, normalized, normalized.lstrip("/")}:
                return int(dep.get("id"))
        raise ValueError(f"IndexTTS api_name {api_name!r} was not found in Gradio config")
    for dep in candidates:
        name = str(dep.get("api_name") or "").lower()
        if any(marker in name for marker in ("tts", "synth", "generate", "infer", "predict")):
            return int(dep.get("id"))
    for dep in candidates:
        if dep.get("api_name"):
            return int(dep.get("id"))
    raise ValueError("could not discover an IndexTTS Gradio fn_index")


def _run_indextts_gradio_tts(
    *,
    text: str,
    voice_description: str | None = None,
    reference_audio: bytes | None = None,
    reference_audio_name: str | None = None,
    reference_audio_mime_type: str | None = None,
) -> Dict[str, Any]:
    prompt = str(text or "").strip()
    if not prompt:
        raise ValueError("text is required")
    config = _indextts_config()
    uploaded_reference = _indextts_upload_reference_audio(reference_audio, reference_audio_name, reference_audio_mime_type)
    data = _indextts_request_data(
        text=prompt,
        voice_description=voice_description,
        reference_audio=uploaded_reference,
    )
    session_hash = uuid.uuid4().hex
    join_payload = {
        "data": data,
        "fn_index": _indextts_fn_index(config),
        "session_hash": session_hash,
    }
    _http_json("POST", f"{_indextts_space_base_url()}/gradio_api/queue/join", join_payload)
    result = _indextts_wait_for_result(session_hash)
    audio_ref = _find_gradio_audio_reference(result)
    if not audio_ref:
        raise ValueError("IndexTTS completed without an audio file in the Gradio output")
    audio_bytes, mime_type = _fetch_gradio_file(audio_ref)
    return {
        "audioBase64": base64.b64encode(audio_bytes).decode("ascii"),
        "mimeType": mime_type or "audio/wav",
        "model": os.getenv("WALLET_INDEXTTS_MODEL_NAME", "IndexTeam/IndexTTS-2-Demo"),
        "provider": "huggingface-zero-gpu-gradio",
        "billTo": os.getenv("WALLET_INDEXTTS_HF_BILL_TO") or os.getenv("IPFS_DATASETS_PY_HF_BILL_TO") or "publicus",
        "text": prompt,
    }


def _indextts_upload_reference_audio(
    audio: bytes | None,
    file_name: str | None,
    mime_type: str | None = None,
) -> Dict[str, Any] | None:
    if audio:
        guessed_type = mime_type or mimetypes.guess_type(file_name or "")[0] or "audio/wav"
        return _gradio_upload_file(audio, file_name or "reference.wav", guessed_type)
    path = os.getenv("WALLET_INDEXTTS_REFERENCE_AUDIO_PATH", "").strip()
    if path and os.path.exists(path):
        with open(path, "rb") as handle:
            data = handle.read()
        mime_type = mimetypes.guess_type(path)[0] or "audio/wav"
        return _gradio_upload_file(data, os.path.basename(path), mime_type)
    remote_path = os.getenv("WALLET_INDEXTTS_REFERENCE_AUDIO_REMOTE_PATH", "").strip()
    if remote_path:
        return {"path": remote_path, "meta": {"_type": "gradio.FileData"}, "orig_name": os.path.basename(remote_path) or "reference.wav"}
    return _gradio_upload_file(_default_indextts_reference_wav(), "abby-reference.wav", "audio/wav")


def _default_indextts_reference_wav() -> bytes:
    sample_rate = 24_000
    duration_seconds = 1.5
    frames = int(sample_rate * duration_seconds)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        for index in range(frames):
            envelope = min(1.0, index / 2_400, (frames - index) / 2_400)
            value = int(10_000 * envelope * math.sin(2.0 * math.pi * 220.0 * index / sample_rate))
            wav.writeframesraw(struct.pack("<h", value))
    return buffer.getvalue()


def _gradio_upload_file(data: bytes, file_name: str, mime_type: str) -> Dict[str, Any]:
    boundary = f"----211AiIndexTts{uuid.uuid4().hex}"
    safe_name = os.path.basename(file_name or "reference.wav")
    body = b"".join(
        [
            f"--{boundary}\r\n".encode("utf-8"),
            f'Content-Disposition: form-data; name="files"; filename="{safe_name}"\r\n'.encode("utf-8"),
            f"Content-Type: {mime_type or 'application/octet-stream'}\r\n\r\n".encode("utf-8"),
            data,
            f"\r\n--{boundary}--\r\n".encode("utf-8"),
        ]
    )
    headers = _indextts_headers()
    headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    request = urllib_request.Request(
        f"{_indextts_space_base_url()}/gradio_api/upload",
        data=body,
        headers=headers,
        method="POST",
    )
    with urllib_request.urlopen(request, timeout=_indextts_timeout_seconds()) as response:
        parsed = json.loads(response.read().decode("utf-8"))
    upload_path = _first_upload_path(parsed)
    if not upload_path:
        raise ValueError("IndexTTS upload did not return a Gradio file path")
    return {"path": upload_path, "meta": {"_type": "gradio.FileData"}, "orig_name": safe_name}


def _first_upload_path(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        for item in value:
            found = _first_upload_path(item)
            if found:
                return found
    if isinstance(value, Mapping):
        for key in ("path", "name"):
            item = value.get(key)
            if isinstance(item, str) and item.strip():
                return item.strip()
        for item in value.values():
            found = _first_upload_path(item)
            if found:
                return found
    return ""


def _indextts_request_data(
    *,
    text: str,
    voice_description: str | None,
    reference_audio: Mapping[str, Any] | None,
) -> List[Any]:
    raw_template = os.getenv("WALLET_INDEXTTS_DATA_TEMPLATE", "").strip()
    if raw_template:
        rendered = (
            raw_template.replace("{text}", text)
            .replace("{voice_description}", voice_description or "")
            .replace("{reference_audio}", json.dumps(reference_audio) if reference_audio else "null")
        )
        parsed = json.loads(rendered)
        if not isinstance(parsed, list):
            raise ValueError("WALLET_INDEXTTS_DATA_TEMPLATE must render to a JSON array")
        return parsed
    # IndexTeam/IndexTTS-2-Demo /gen_single Gradio input order.
    return [
        "Same as the voice reference",
        reference_audio,
        text,
        None,
        0.8,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        voice_description or "",
        False,
        120,
        True,
        0.8,
        30,
        0.8,
        0.0,
        3,
        10.0,
        1500,
    ]


def _indextts_wait_for_result(session_hash: str) -> Dict[str, Any]:
    deadline = time.time() + _indextts_timeout_seconds()
    url = f"{_indextts_space_base_url()}/gradio_api/queue/data?session_hash={urllib_parse.quote(session_hash)}"
    while time.time() < deadline:
        request = urllib_request.Request(url, headers=_indextts_headers())
        with urllib_request.urlopen(request, timeout=min(30.0, _indextts_timeout_seconds())) as response:
            for raw_line in response:
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line.startswith("data:"):
                    continue
                payload_text = line.removeprefix("data:").strip()
                if not payload_text:
                    continue
                event = json.loads(payload_text)
                if not isinstance(event, dict):
                    continue
                message = str(event.get("msg") or "")
                if message == "process_completed":
                    if event.get("success") is False:
                        output = event.get("output")
                        if isinstance(output, Mapping):
                            detail = output.get("error") or output.get("title") or output
                        else:
                            detail = output or event
                        raise ValueError(f"IndexTTS Gradio queue failed: {detail}")
                    output = event.get("output")
                    if isinstance(output, Mapping):
                        return dict(output)
                    return event
                if message in {"process_starts", "estimation", "heartbeat", "send_data"}:
                    continue
                if message in {"process_failed", "queue_full"}:
                    raise ValueError(f"IndexTTS Gradio queue failed: {event}")
        time.sleep(0.5)
    raise TimeoutError("IndexTTS Gradio queue timed out")


def _find_gradio_audio_reference(value: Any) -> Any:
    if isinstance(value, Mapping):
        if str(value.get("mime_type") or value.get("mimeType") or "").startswith("audio/"):
            return value
        if any(key in value for key in ("path", "url", "name")) and not value.get("is_stream"):
            pathish = str(value.get("path") or value.get("url") or value.get("name") or "")
            if pathish and (pathish.endswith((".wav", ".mp3", ".flac", ".ogg")) or "/file=" in pathish or "/gradio_api/file=" in pathish):
                return value
        for item in value.values():
            found = _find_gradio_audio_reference(item)
            if found:
                return found
    if isinstance(value, list):
        for item in value:
            found = _find_gradio_audio_reference(item)
            if found:
                return found
    if isinstance(value, str) and (value.endswith((".wav", ".mp3", ".flac", ".ogg")) or "/file=" in value or "/gradio_api/file=" in value):
        return value
    return None


def _fetch_gradio_file(reference: Any) -> tuple[bytes, str]:
    if isinstance(reference, Mapping):
        url = str(reference.get("url") or "").strip()
        path = str(reference.get("path") or reference.get("name") or "").strip()
        mime_type = str(reference.get("mime_type") or reference.get("mimeType") or "").strip()
    else:
        url = ""
        path = str(reference or "").strip()
        mime_type = ""
    if not url:
        if path.startswith("http://") or path.startswith("https://"):
            url = path
        else:
            encoded_path = urllib_parse.quote(path, safe="/:=._-")
            url = f"{_indextts_space_base_url()}/gradio_api/file={encoded_path}"
    data, detected_type = _http_bytes(url)
    return data, mime_type or detected_type or mimetypes.guess_type(path)[0] or "audio/wav"


def _parse_upload_metadata(metadata: str | None) -> Dict[str, Any]:
    if not metadata:
        return {}
    parsed = json.loads(metadata)
    if not isinstance(parsed, dict):
        raise ValueError("upload metadata must decode to an object")
    return parsed


def _publish_bytes_to_ipfs(
    data: bytes,
    *,
    file_name: str | None = None,
    mime_type: str | None = None,
    source_record_id: str | None = None,
    wallet_id: str | None = None,
) -> Dict[str, Any]:
    cid = _publish_bytes_via_ipfs_backend(data)
    gateway_base_url = os.environ.get("WALLET_IPFS_PUBLIC_GATEWAY_BASE_URL", "/ipfs-proxy").rstrip("/")
    payload: Dict[str, Any] = {
        "cid": cid,
        "gatewayUrl": f"{gateway_base_url}/{cid}",
        "ipfsCid": cid,
        "message": "Pinned to IPFS through the wallet upload bridge.",
        "provider": "ipfs-filecoin",
        "status": "stored",
    }
    sidecar_result = _submit_ipfs_cid_to_filecoin_pin(
        cid,
        file_name=file_name,
        mime_type=mime_type,
        source_record_id=source_record_id,
        wallet_id=wallet_id,
    )
    if sidecar_result is not None:
        payload["message"] = "Pinned to IPFS and queued for Filecoin persistence through the wallet upload bridge."
        request_id = str(sidecar_result.get("requestid") or sidecar_result.get("requestId") or "").strip()
        handoff_status = str(sidecar_result.get("status") or "").strip()
        if request_id:
            payload["requestId"] = request_id
            payload["filecoinPinRequestId"] = request_id
            payload["statusUrl"] = _filecoin_upload_status_url(request_id)
        if handoff_status:
            payload["filecoinPinStatus"] = handoff_status
        if isinstance(sidecar_result.get("info"), dict):
            payload["filecoinPinInfo"] = sidecar_result["info"]
    if file_name:
        payload["fileName"] = file_name
    if mime_type:
        payload["mimeType"] = mime_type
    if source_record_id:
        payload["recordId"] = source_record_id
    if wallet_id:
        payload["walletId"] = wallet_id
    return payload


def _publish_encrypted_record_graph_to_ipfs(
    encrypted_record: Mapping[str, Any],
    *,
    file_name: str | None = None,
) -> Dict[str, Any]:
    record = dict(encrypted_record["record"])
    version = dict(encrypted_record["version"])
    wallet_id = str(record.get("wallet_id") or "")
    record_id = str(record.get("record_id") or "")
    version_id = str(version.get("version_id") or record.get("current_version_id") or "")
    payload_result = _publish_bytes_to_ipfs(
        encrypted_record["encrypted_payload"],
        file_name=f"{file_name or record_id}.encrypted-payload.json",
        mime_type="application/vnd.211-ai.wallet.encrypted-payload+json",
        source_record_id=record_id,
        wallet_id=wallet_id,
    )
    payload_cid = str(payload_result.get("ipfsCid") or payload_result.get("cid") or "")
    metadata_result = None
    metadata_cid = ""
    if encrypted_record.get("encrypted_metadata") is not None:
        metadata_result = _publish_bytes_to_ipfs(
            encrypted_record["encrypted_metadata"],
            file_name=f"{file_name or record_id}.encrypted-metadata.json",
            mime_type="application/vnd.211-ai.wallet.encrypted-metadata+json",
            source_record_id=record_id,
            wallet_id=wallet_id,
        )
        metadata_cid = str(metadata_result.get("ipfsCid") or metadata_result.get("cid") or "")
    encrypted_payload_ref = dict(version.get("encrypted_payload_ref") or {})
    encrypted_metadata_ref = dict(version.get("encrypted_metadata_ref") or {}) if version.get("encrypted_metadata_ref") else None
    graph = {
        "schemaVersion": "211-ai-wallet-encrypted-record-ipld-v1",
        "walletId": wallet_id,
        "recordId": record_id,
        "versionId": version_id,
        "dataType": record.get("data_type"),
        "sensitivity": record.get("sensitivity"),
        "publicDescriptor": record.get("public_descriptor"),
        "ciphertextHash": version.get("ciphertext_hash"),
        "encryptionSuite": version.get("encryption_suite"),
        "encryptedPayload": {
            "/": payload_cid,
            "storageRef": encrypted_payload_ref,
            "filecoin": payload_result,
        },
        "encryptedMetadata": (
            {
                "/": metadata_cid,
                "storageRef": encrypted_metadata_ref,
                "filecoin": metadata_result,
            }
            if metadata_result is not None
            else None
        ),
        "walletMetadata": None,
        "links": [
            {"name": "encrypted_payload", "/": payload_cid, "mediaType": "application/vnd.211-ai.wallet.encrypted-payload+json"},
            *(
                [{"name": "encrypted_metadata", "/": metadata_cid, "mediaType": "application/vnd.211-ai.wallet.encrypted-metadata+json"}]
                if metadata_result is not None
                else []
            ),
        ],
    }
    wallet_metadata_cid = _record_metadata_cid(encrypted_record)
    if wallet_metadata_cid:
        graph["walletMetadata"] = {
            "/": wallet_metadata_cid,
            "mediaType": "application/vnd.211-ai.wallet.record-metadata+json",
        }
        graph["links"].append(
            {
                "name": "wallet_metadata",
                "/": wallet_metadata_cid,
                "mediaType": "application/vnd.211-ai.wallet.record-metadata+json",
            }
        )
    graph_result = _publish_bytes_to_ipfs(
        json.dumps(graph, sort_keys=True, separators=(",", ":")).encode("utf-8"),
        file_name=f"{file_name or record_id}.ipld-wallet-record.json",
        mime_type="application/vnd.ipld.dag-json",
        source_record_id=record_id,
        wallet_id=wallet_id,
    )
    graph_cid = str(graph_result.get("ipfsCid") or graph_result.get("cid") or "")
    return {
        **graph_result,
        "message": "Pinned encrypted wallet record graph to IPFS/Filecoin.",
        "encryptedPayloadCid": payload_cid,
        "encryptedMetadataCid": metadata_cid or None,
        "metadataCid": wallet_metadata_cid or None,
        "metadataIpldCid": wallet_metadata_cid or None,
        "ipldLinks": graph["links"],
        "recordId": record_id,
        "versionId": version_id,
        "root": {"/": graph_cid},
        "walletId": wallet_id,
    }


def _record_metadata_cid(encrypted_record: Mapping[str, Any]) -> str:
    metadata = encrypted_record.get("metadata")
    if isinstance(metadata, Mapping):
        for key in ("metadataCid", "metadataIpldCid"):
            value = str(metadata.get(key) or "").strip()
            if value:
                return value
    record = encrypted_record.get("record")
    if isinstance(record, Mapping):
        metadata = record.get("metadata")
        if isinstance(metadata, Mapping):
            for key in ("metadataCid", "metadataIpldCid"):
                value = str(metadata.get(key) or "").strip()
                if value:
                    return value
    return ""


def _should_publish_record_metadata_ipld(metadata: Mapping[str, Any]) -> bool:
    generated_keys = {
        "decryptedClassification",
        "decryptedLabels",
        "decryptedMimeType",
        "privacyProfileArtifactIds",
        "privacyProfileClassification",
        "privacyProfileLabels",
        "privacyProfileMimeType",
        "privacyProfileProofId",
        "privacyProfilePublicInputs",
        "privacyProfileSearchText",
        "privacyProfileStatus",
        "privacyProfileSummary",
        "privacyProfileVectorTerms",
    }
    return any(key in metadata for key in generated_keys)


def _publish_record_metadata_ipld(record: Mapping[str, Any]) -> Dict[str, Any]:
    metadata = record.get("metadata")
    if not isinstance(metadata, Mapping):
        return {}
    generated_metadata = _generated_wallet_metadata(metadata)
    if not generated_metadata:
        return {}
    record_id = str(record.get("record_id") or "")
    wallet_id = str(record.get("wallet_id") or metadata.get("walletId") or "")
    graph = {
        "schemaVersion": "211-ai-wallet-record-metadata-ipld-v1",
        "walletId": wallet_id,
        "recordId": record_id,
        "dataType": record.get("data_type"),
        "sensitivity": record.get("sensitivity"),
        "metadata": generated_metadata,
        "privacyPolicy": "proof_backed_metadata_no_plaintext_payload",
        "links": [
            *(
                [
                    {
                        "name": "document_privacy_profile_proof",
                        "proofId": str(generated_metadata["privacyProfileProofId"]),
                        "mediaType": "application/vnd.211-ai.wallet.proof-receipt+json",
                    }
                ]
                if generated_metadata.get("privacyProfileProofId")
                else []
            ),
            *(
                [
                    {
                        "name": "derived_artifact",
                        "artifactId": artifact_id,
                        "mediaType": "application/vnd.211-ai.wallet.derived-artifact+json",
                    }
                    for artifact_id in generated_metadata.get("privacyProfileArtifactIds", [])
                    if isinstance(artifact_id, str) and artifact_id.strip()
                ]
            ),
        ],
    }
    result = _publish_bytes_to_ipfs(
        json.dumps(graph, sort_keys=True, separators=(",", ":")).encode("utf-8"),
        file_name=f"{record_id or 'wallet-record'}.wallet-metadata.ipld.json",
        mime_type="application/vnd.211-ai.wallet.record-metadata+json",
        source_record_id=record_id or None,
        wallet_id=wallet_id or None,
    )
    cid = str(result.get("ipfsCid") or result.get("cid") or "")
    if not cid:
        return {}
    existing_links = metadata.get("ipldLinks") if isinstance(metadata.get("ipldLinks"), list) else []
    metadata_link = {
        "name": "wallet_metadata",
        "/": cid,
        "mediaType": "application/vnd.211-ai.wallet.record-metadata+json",
    }
    links = [
        link
        for link in existing_links
        if not (isinstance(link, Mapping) and str(link.get("name") or "") == "wallet_metadata")
    ]
    links.append(metadata_link)
    patch: Dict[str, Any] = {
        "metadataCid": cid,
        "metadataGatewayUrl": result.get("gatewayUrl") or result.get("url"),
        "metadataIpldCid": cid,
        "metadataIpldLink": metadata_link,
        "metadataStorageMessage": result.get("message") or "Pinned wallet metadata IPLD to IPFS/Filecoin.",
        "ipldLinks": links,
    }
    for key in ("filecoinPinRequestId", "filecoinPinStatus", "filecoinPinStatusUrl"):
        value = result.get(key)
        if value:
            patch[f"metadata{key[0].upper()}{key[1:]}"] = value
    return patch


def _generated_wallet_metadata(metadata: Mapping[str, Any]) -> Dict[str, Any]:
    allowed = {
        "decryptedClassification",
        "decryptedLabels",
        "decryptedMimeType",
        "fileName",
        "privacyProfileArtifactIds",
        "privacyProfileClassification",
        "privacyProfileLabels",
        "privacyProfileMimeType",
        "privacyProfileProofId",
        "privacyProfilePublicInputs",
        "privacyProfileSearchText",
        "privacyProfileStatus",
        "privacyProfileSummary",
        "privacyProfileVectorTerms",
    }
    generated = {key: metadata[key] for key in sorted(allowed) if key in metadata}
    return _json_safe_metadata(generated)


def _json_safe_metadata(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): _json_safe_metadata(item)
            for key, item in value.items()
            if item is not None
        }
    if isinstance(value, list):
        return [_json_safe_metadata(item) for item in value if item is not None]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _publish_bytes_via_ipfs_backend(data: bytes) -> str:
    backend_mode = str(os.getenv("WALLET_IPFS_UPLOAD_BACKEND") or "").strip().lower()
    if backend_mode == "mock":
        return _mock_ipfs_cid_for_bytes(data)
    backend = get_ipfs_backend()
    return backend.add_bytes(data, pin=True)


def _mock_ipfs_cid_for_bytes(data: bytes) -> str:
    digest = hashlib.sha256(data).hexdigest()
    return f"bafybeimock{digest[:24]}"


def _submit_ipfs_cid_to_filecoin_pin(
    cid: str,
    *,
    file_name: str | None = None,
    mime_type: str | None = None,
    source_record_id: str | None = None,
    wallet_id: str | None = None,
) -> Dict[str, Any] | None:
    if not _filecoin_pin_service_url():
        return None

    origins = [
        origin.strip()
        for origin in str(os.getenv("WALLET_FILECOIN_PIN_ORIGINS") or "").split(",")
        if origin.strip()
    ]
    metadata: Dict[str, str] = {"source": "211-ai-wallet"}
    if wallet_id:
        metadata["walletId"] = wallet_id
    if source_record_id:
        metadata["recordId"] = source_record_id
    if file_name:
        metadata["fileName"] = file_name
    if mime_type:
        metadata["mimeType"] = mime_type

    payload: Dict[str, Any] = {
        "cid": cid,
        "meta": metadata,
    }
    if file_name:
        payload["name"] = file_name
    if origins:
        payload["origins"] = origins
    return _filecoin_pin_request("POST", "/pins", payload=payload)


def _fetch_filecoin_pin_status(request_id: str) -> Dict[str, Any]:
    if not request_id.strip():
        raise ValueError("request ID is required")
    return _filecoin_pin_request("GET", f"/pins/{request_id}")


def _filecoin_pin_request(method: str, path: str, *, payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    service_url = _filecoin_pin_service_url()
    if not service_url:
        raise FilecoinPinHandoffError("WALLET_FILECOIN_PIN_SERVICE_URL is not configured")
    if service_url == "mock":
        return _mock_filecoin_pin_request(method, path, payload=payload)

    endpoint = f"{service_url}{path}"
    body = json.dumps(payload, sort_keys=True).encode("utf-8") if payload is not None else None
    req = urllib_request.Request(
        endpoint,
        data=body,
        headers=_filecoin_pin_request_headers(include_json_content_type=payload is not None),
        method=method,
    )
    try:
        with urllib_request.urlopen(req, timeout=_filecoin_pin_timeout_seconds()) as response:
            raw = response.read().decode("utf-8")
            content_type = str(getattr(response, "headers", {}).get("content-type", ""))
    except urllib_error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        detail = _response_message_from_raw_json(error_body) or f"Filecoin Pin sidecar rejected the request with HTTP {exc.code}"
        raise FilecoinPinHandoffError(detail) from exc
    except urllib_error.URLError as exc:
        raise FilecoinPinHandoffError(f"Unable to reach Filecoin Pin sidecar at {endpoint}: {exc.reason}") from exc

    if not raw:
        return {}
    if "json" not in content_type.lower() and not raw.lstrip().startswith("{"):
        raise FilecoinPinHandoffError("Filecoin Pin sidecar returned a non-JSON response")
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise FilecoinPinHandoffError("Filecoin Pin sidecar returned a non-object response")
    return parsed


def _filecoin_pin_service_url() -> str:
    return str(os.getenv("WALLET_FILECOIN_PIN_SERVICE_URL") or "").strip().rstrip("/")


def _filecoin_pin_mock_status() -> str:
    return str(os.getenv("WALLET_FILECOIN_PIN_MOCK_STATUS") or "pinned").strip() or "pinned"


def _mock_filecoin_pin_request(method: str, path: str, *, payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    normalized_method = str(method or "").strip().upper()
    normalized_path = str(path or "").strip()

    if normalized_method == "POST" and normalized_path == "/pins":
        cid = str((payload or {}).get("cid") or "").strip()
        if not cid:
            raise FilecoinPinHandoffError("mock Filecoin Pin request requires a cid")
        request_id = f"mock-pin-{hashlib.sha256(cid.encode('utf-8')).hexdigest()[:12]}"
        return {
            "requestid": request_id,
            "status": "queued",
            "info": {
                "provider": "mock-filecoin-pin",
                "cid": cid,
                "mock": True,
            },
        }

    if normalized_method == "GET" and normalized_path.startswith("/pins/"):
        request_id = normalized_path.rsplit("/", 1)[-1].strip()
        if not request_id:
            raise FilecoinPinHandoffError("mock Filecoin Pin status requires a request ID")
        return {
            "requestid": request_id,
            "status": _filecoin_pin_mock_status(),
            "info": {
                "provider": "mock-filecoin-pin",
                "mock": True,
                "pieceCid": f"baga6ea4seaq{hashlib.sha256(request_id.encode('utf-8')).hexdigest()[:16]}",
            },
        }

    raise FilecoinPinHandoffError(f"mock Filecoin Pin does not support {normalized_method} {normalized_path}")


def _filecoin_pin_timeout_seconds() -> float:
    timeout_seconds = float(str(os.getenv("WALLET_FILECOIN_PIN_TIMEOUT_SECONDS") or "30").strip())
    if timeout_seconds <= 0:
        raise FilecoinPinHandoffError("WALLET_FILECOIN_PIN_TIMEOUT_SECONDS must be positive")
    return timeout_seconds


def _filecoin_pin_request_headers(*, include_json_content_type: bool) -> Dict[str, str]:
    request_headers: Dict[str, str] = {}
    if include_json_content_type:
        request_headers["content-type"] = "application/json"
    if bearer_token := str(os.getenv("WALLET_FILECOIN_PIN_BEARER_TOKEN") or "").strip():
        request_headers["authorization"] = f"Bearer {bearer_token}"
    if header_name := str(os.getenv("WALLET_FILECOIN_PIN_HTTP_HEADER_NAME") or "").strip():
        header_value = str(os.getenv("WALLET_FILECOIN_PIN_HTTP_HEADER_VALUE") or "").strip()
        if not header_value:
            raise FilecoinPinHandoffError(
                "WALLET_FILECOIN_PIN_HTTP_HEADER_VALUE is required when WALLET_FILECOIN_PIN_HTTP_HEADER_NAME is set"
            )
        request_headers[header_name] = header_value
    return request_headers


def _response_message_from_raw_json(raw: str) -> str:
    if not raw.strip():
        return ""
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return raw.strip()
    if not isinstance(parsed, dict):
        return raw.strip()
    return str(parsed.get("error") or parsed.get("message") or "").strip()


def _filecoin_pin_status_url(request_id: str) -> str:
    service_url = _filecoin_pin_service_url()
    return f"{service_url}/pins/{request_id}" if service_url else ""


def _filecoin_upload_status_url(request_id: str) -> str:
    return f"/filecoin-upload/status/{request_id}"


def _key_from_optional_hex(value: str | None) -> bytes | None:
    if value is None:
        return None
    key = bytes.fromhex(value)
    if len(key) != 32:
        raise ValueError("wallet key must decode to 32 bytes")
    return key


def _send_dead_drop_email(
    *,
    to_email: str,
    subject: str,
    body: str,
    bundle: Dict[str, Any],
    bundle_filename: str,
) -> Dict[str, Any]:
    normalized_to_email = str(to_email or "").strip()
    normalized_subject = str(subject or "").strip()
    normalized_body = str(body or "")
    bundle_json = json.dumps(bundle, indent=2, sort_keys=True)
    sender = str(os.getenv("WALLET_DEAD_DROP_FROM_EMAIL") or "no-reply@211-ai.org").strip()

    webhook_url = str(os.getenv("WALLET_DEAD_DROP_WEBHOOK_URL") or "").strip()
    backend = str(os.getenv("WALLET_DEAD_DROP_BACKEND") or ("http" if webhook_url else "")).strip().lower()
    if backend or webhook_url:
        if backend != "http" or not webhook_url:
            raise RuntimeError(
                "WALLET_DEAD_DROP_WEBHOOK_URL environment variable is required for dead-drop delivery when WALLET_DEAD_DROP_BACKEND is enabled"
            )
        delivery = _send_webhook_notification(
            env_prefix="WALLET_DEAD_DROP",
            required_key="to_email",
            required_value=normalized_to_email,
            extra_payload={
                "subject": normalized_subject,
                "body": normalized_body,
                "from_email": sender,
                "attachment_base64": base64.b64encode(bundle_json.encode("utf-8")).decode("ascii"),
                "attachment_filename": str(bundle_filename or "abby-missing-person-wallet-dead-drop.json"),
                "attachment_mime_type": "application/json",
            },
        )
        return {"message_id": str(delivery.get("provider_message_id") or "")}

    smtp_host = str(os.getenv("WALLET_DEAD_DROP_SMTP_HOST") or "").strip()
    if not smtp_host:
        raise RuntimeError(
            "WALLET_DEAD_DROP_SMTP_HOST environment variable is required for dead-drop email delivery but is not configured"
        )
    smtp_port = int(str(os.getenv("WALLET_DEAD_DROP_SMTP_PORT") or "587").strip())
    smtp_use_ssl = str(os.getenv("WALLET_DEAD_DROP_SMTP_USE_SSL") or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    smtp_starttls = str(os.getenv("WALLET_DEAD_DROP_SMTP_STARTTLS") or "true").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    smtp_username = str(os.getenv("WALLET_DEAD_DROP_SMTP_USERNAME") or "").strip()
    smtp_password = str(os.getenv("WALLET_DEAD_DROP_SMTP_PASSWORD") or "")

    message = EmailMessage()
    message["From"] = sender
    message["To"] = normalized_to_email
    message["Subject"] = normalized_subject
    sender_domain = sender.rsplit("@", 1)[-1].strip() if "@" in sender else ""
    message["Message-Id"] = make_msgid(domain=sender_domain or None)
    message.set_content(normalized_body)
    message.add_attachment(
        bundle_json.encode("utf-8"),
        maintype="application",
        subtype="json",
        filename=bundle_filename,
    )

    smtp_factory = smtplib.SMTP_SSL if smtp_use_ssl else smtplib.SMTP
    with smtp_factory(smtp_host, smtp_port, timeout=20) as smtp:
        if not smtp_use_ssl and smtp_starttls:
            smtp.starttls()
        if smtp_username:
            smtp.login(smtp_username, smtp_password)
        rejected = smtp.send_message(message)
    if rejected:
        raise RuntimeError(f"Dead-drop email delivery rejected recipients: {sorted(rejected)}")
    return {"message_id": str(message.get("Message-Id") or "")}
