"""Route factory for exports endpoints."""

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

    @router.post("/wallets/{wallet_id}/exports/grants")
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


    @router.post("/wallets/{wallet_id}/exports/invocations")
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


    @router.post("/wallets/{wallet_id}/exports")
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


    @router.post("/exports/verify")
    def verify_export_bundle(request: ExportBundleVerifyRequest) -> Dict[str, Any]:
        try:
            return app_service.verify_export_bundle(request.bundle)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


    @router.post("/exports/import")
    def import_export_bundle(request: ExportBundleImportRequest) -> Dict[str, Any]:
        try:
            return app_service.import_export_bundle(request.bundle)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


    @router.post("/exports/storage")
    def verify_export_bundle_storage(request: ExportBundleStorageRequest) -> Dict[str, Any]:
        try:
            return app_service.verify_export_bundle_storage(request.bundle)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


    return router
