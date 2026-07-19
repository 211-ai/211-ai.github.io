"""Route factory for World ID wallet binding endpoints."""

from __future__ import annotations

from typing import Any

try:  # pragma: no cover - exercised when optional dependency is installed.
    from fastapi import APIRouter, HTTPException
except ImportError:  # pragma: no cover
    APIRouter = None  # type: ignore[assignment]

    class HTTPException(Exception):  # type: ignore[assignment]
        def __init__(self, status_code: int = 500, detail: str = "") -> None:
            super().__init__(detail)
            self.status_code = status_code
            self.detail = detail

from ..app_service import WalletInterfaceService
from ..schemas.base import BaseModel, Field
from ..world_id import WorldIdConfigError, WorldIdPayloadError, WorldIdSignatureError, WorldIdVerificationError

WORLD_ID_ROUTE_ERRORS = (
    ValueError,
    WorldIdConfigError,
    WorldIdPayloadError,
    WorldIdSignatureError,
    WorldIdVerificationError,
)


class WorldIdRpSignatureRequest(BaseModel):
    actor_did: str
    action: str | None = None


class ProviderStaffWorldIdRpSignatureRequest(BaseModel):
    actor_did: str
    provider_id: str
    provider_staff_id: str


class WorldIdVerificationRequest(BaseModel):
    actor_did: str
    idkit_payload: dict[str, Any] = Field(default_factory=dict)


class WorldIdRevokeBindingRequest(BaseModel):
    actor_did: str
    reason: str | None = None


def _http_status_for_world_id_error(exc: Exception) -> int:
    detail = str(exc).lower()
    if "already" in detail and ("nullifier" in detail or "world id" in detail or "world-id" in detail):
        return 409
    if "not found" in detail or "does not exist" in detail:
        return 404
    return 400


def create_router(service: WalletInterfaceService):
    if APIRouter is None:  # pragma: no cover
        raise RuntimeError("FastAPI is required to create the wallet interface API")
    router = APIRouter()
    app_service = service

    @router.get("/wallets/{wallet_id}/world-id/config")
    def get_world_id_config(wallet_id: str) -> dict[str, Any]:
        try:
            app_service.get_wallet(wallet_id)
            return app_service.get_world_id_config()
        except WORLD_ID_ROUTE_ERRORS as exc:
            raise HTTPException(status_code=_http_status_for_world_id_error(exc), detail=str(exc)) from exc

    @router.get("/wallets/{wallet_id}/world-id/status")
    def get_world_id_status(wallet_id: str, actor_did: str | None = None) -> dict[str, Any]:
        try:
            return app_service.get_world_id_status(wallet_id, actor_did=actor_did)
        except WORLD_ID_ROUTE_ERRORS as exc:
            raise HTTPException(status_code=_http_status_for_world_id_error(exc), detail=str(exc)) from exc

    @router.post("/wallets/{wallet_id}/world-id/rp-signature")
    def create_world_id_rp_signature(wallet_id: str, request: WorldIdRpSignatureRequest) -> dict[str, Any]:
        try:
            return app_service.create_world_id_rp_signature(
                wallet_id,
                actor_did=request.actor_did,
                action=request.action,
            )
        except WORLD_ID_ROUTE_ERRORS as exc:
            raise HTTPException(status_code=_http_status_for_world_id_error(exc), detail=str(exc)) from exc

    @router.post("/wallets/{wallet_id}/world-id/provider-staff/rp-signature")
    def create_provider_staff_world_id_rp_signature(
        wallet_id: str,
        request: ProviderStaffWorldIdRpSignatureRequest,
    ) -> dict[str, Any]:
        try:
            return app_service.create_provider_staff_world_id_rp_signature(
                wallet_id,
                actor_did=request.actor_did,
                provider_id=request.provider_id,
                provider_staff_id=request.provider_staff_id,
            )
        except WORLD_ID_ROUTE_ERRORS as exc:
            raise HTTPException(status_code=_http_status_for_world_id_error(exc), detail=str(exc)) from exc

    @router.post("/wallets/{wallet_id}/world-id/verifications")
    def register_world_id_verification(wallet_id: str, request: WorldIdVerificationRequest) -> dict[str, Any]:
        try:
            return app_service.register_world_id_verification(
                wallet_id,
                actor_did=request.actor_did,
                idkit_payload=request.idkit_payload,
            )
        except WORLD_ID_ROUTE_ERRORS as exc:
            raise HTTPException(status_code=_http_status_for_world_id_error(exc), detail=str(exc)) from exc

    @router.post("/wallets/{wallet_id}/world-id/bindings/{binding_id}/revoke")
    def revoke_world_id_binding(
        wallet_id: str,
        binding_id: str,
        request: WorldIdRevokeBindingRequest,
    ) -> dict[str, Any]:
        try:
            return app_service.revoke_world_id_binding(
                wallet_id,
                binding_id,
                actor_did=request.actor_did,
                reason=request.reason,
            ).to_dict()
        except WORLD_ID_ROUTE_ERRORS as exc:
            raise HTTPException(status_code=_http_status_for_world_id_error(exc), detail=str(exc)) from exc

    return router
