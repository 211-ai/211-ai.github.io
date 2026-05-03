"""FastAPI surface for 211-AI wallet workflows."""

from __future__ import annotations

import base64
from typing import Any, Dict, List, Sequence

from .app_service import WalletInterfaceService

try:  # pragma: no cover - exercised when optional dependency is installed.
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel, Field
except ImportError:  # pragma: no cover
    FastAPI = None  # type: ignore[assignment]
    HTTPException = None  # type: ignore[assignment]
    BaseModel = object  # type: ignore[assignment,misc]

    def Field(default: Any = None, **_: Any) -> Any:  # type: ignore[no-redef]
        return default

from ._vendor import ensure_ipfs_datasets_py_path

ensure_ipfs_datasets_py_path()

from ipfs_datasets_py.wallet.ucan import invocation_from_token, invocation_to_token  # noqa: E402


class CreateWalletRequest(BaseModel):
    owner_did: str
    controller_dids: List[str] = Field(default_factory=list)
    approval_threshold: int | None = None


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


class LocationRegionProofGrantRequest(BaseModel):
    issuer_did: str
    audience_did: str
    expires_at: str | None = None


class LocationRegionProofRequest(BaseModel):
    actor_did: str
    region_id: str
    grant_id: str | None = None


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


class AnalysisInvocationRequest(BaseModel):
    grant_id: str
    actor_did: str
    actor_key_hex: str | None = None
    expires_at: str | None = None


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


class AnalyzeRecordRequest(BaseModel):
    actor_did: str
    actor_key_hex: str | None = None
    grant_id: str | None = None
    invocation_token: str | None = None
    max_chars: int = 200


class DecryptRecordRequest(BaseModel):
    actor_did: str
    actor_key_hex: str | None = None
    invocation_token: str


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
    expires_at: str | None = None


class AnalyticsConsentFromTemplateRequest(BaseModel):
    actor_did: str
    template_id: str
    expires_at: str | None = None


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


class DerivedServiceMatchRequest(BaseModel):
    need_terms: Sequence[str] = Field(default_factory=list)
    location_claim: Dict[str, Any] | None = None
    limit: int = 10


def create_app(*, service: WalletInterfaceService | None = None):
    """Create the wallet API app.

    The API stays deliberately thin: all authorization, crypto, proofs,
    analytics privacy, and audit behavior remains in `ipfs_datasets_py.wallet`.
    """

    if FastAPI is None:  # pragma: no cover
        raise RuntimeError("FastAPI is required to create the wallet interface API")

    app_service = service or WalletInterfaceService()
    app = FastAPI(title="211-AI Wallet Interface", version="0.1.0")

    @app.get("/health")
    def health() -> Dict[str, str]:
        return {"status": "ok"}

    @app.post("/wallets")
    def create_wallet(request: CreateWalletRequest) -> Dict[str, Any]:
        wallet = app_service.create_wallet(
            request.owner_did,
            controller_dids=request.controller_dids or None,
            approval_threshold=request.approval_threshold,
        )
        return wallet.to_dict()

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
            requests = app_service.list_access_requests(
                wallet_id,
                status=normalized_status,
                requester_did=requester_did,
                audience_did=audience_did,
            )
            return {"requests": [request.to_dict() for request in requests]}
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

    @app.post("/wallets/{wallet_id}/records/{record_id}/decrypt")
    def decrypt_record(
        wallet_id: str,
        record_id: str,
        request: DecryptRecordRequest,
    ) -> Dict[str, Any]:
        try:
            plaintext = app_service.decrypt_record_with_invocation(
                wallet_id,
                record_id,
                actor_did=request.actor_did,
                invocation=invocation_from_token(request.invocation_token),
                actor_secret=_key_from_optional_hex(request.actor_key_hex),
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

    @app.get("/wallets/{wallet_id}/records/{record_id}/storage")
    def verify_record_storage(wallet_id: str, record_id: str) -> Dict[str, Any]:
        try:
            report = app_service.verify_record_storage(wallet_id, record_id)
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
                expires_at=request.expires_at,
            )
            return template.to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/analytics/templates")
    def list_analytics_templates() -> Dict[str, Any]:
        return {"templates": [template.to_dict() for template in app_service.list_analytics_templates()]}

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


def _key_from_optional_hex(value: str | None) -> bytes | None:
    if value is None:
        return None
    key = bytes.fromhex(value)
    if len(key) != 32:
        raise ValueError("wallet key must decode to 32 bytes")
    return key
