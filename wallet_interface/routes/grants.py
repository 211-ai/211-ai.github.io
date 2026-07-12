"""Route factory for grants endpoints."""

from __future__ import annotations

try:  # pragma: no cover - exercised when optional dependency is installed.
    from fastapi import APIRouter
except ImportError:  # pragma: no cover
    APIRouter = None  # type: ignore[assignment]

from ..app_service import WalletInterfaceService
from ..helpers import *  # noqa: F401,F403
from ..schemas import *  # noqa: F401,F403

def create_router(service: WalletInterfaceService):
    if APIRouter is None:  # pragma: no cover
        raise RuntimeError("FastAPI is required to create the wallet interface API")
    router = APIRouter()
    app_service = service

    @router.post("/wallets/{wallet_id}/portal/plans/{plan_id}/share-grants")
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


    @router.post("/wallets/{wallet_id}/services/{service_doc_id}/share-grants")
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


    @router.post("/wallets/{wallet_id}/records/{record_id}/analysis-grants")
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


    @router.post("/wallets/{wallet_id}/records/{record_id}/grants")
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


    @router.post("/wallets/{wallet_id}/records/{record_id}/analysis-invocations")
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


    @router.post("/wallets/{wallet_id}/records/{record_id}/decrypt-invocations")
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


    @router.post("/wallets/{wallet_id}/access-requests")
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


    @router.get("/wallets/{wallet_id}/access-requests")
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


    @router.post("/wallets/{wallet_id}/access-requests/{request_id}/approve")
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


    @router.post("/wallets/{wallet_id}/access-requests/{request_id}/reject")
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


    @router.post("/wallets/{wallet_id}/access-requests/{request_id}/revoke")
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


    @router.post("/wallets/{wallet_id}/approvals")
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


    @router.get("/wallets/{wallet_id}/approvals")
    def list_threshold_approvals(wallet_id: str, status: str = "all") -> Dict[str, Any]:
        try:
            normalized_status = None if status == "all" else status
            approvals = app_service.list_threshold_approvals(wallet_id, status=normalized_status)
            return {"approvals": [approval.to_dict() for approval in approvals]}
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


    @router.post("/wallets/{wallet_id}/approvals/{approval_id}/approve")
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


    @router.post("/wallets/{wallet_id}/grants/{grant_id}/revoke")
    def revoke_grant(wallet_id: str, grant_id: str, request: RevokeGrantRequest) -> Dict[str, Any]:
        try:
            grant = app_service.revoke_grant(wallet_id, grant_id, actor_did=request.actor_did)
            return grant.to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


    @router.post("/wallets/{wallet_id}/emergency-revoke")
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


    @router.post("/wallets/{wallet_id}/grants/{parent_grant_id}/delegate")
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


    @router.get("/wallets/{wallet_id}/grant-receipts")
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


    return router
