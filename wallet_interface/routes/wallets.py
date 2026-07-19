"""Route factory for wallets endpoints."""

from __future__ import annotations

from typing import Any

try:  # pragma: no cover - exercised when optional dependency is installed.
    from fastapi import APIRouter, Header, HTTPException
except ImportError:  # pragma: no cover
    APIRouter = None  # type: ignore[assignment]
    class HTTPException(Exception):  # type: ignore[assignment]
        def __init__(self, status_code: int = 500, detail: str = "") -> None:
            super().__init__(detail)
            self.status_code = status_code
            self.detail = detail
    Header = None  # type: ignore[assignment]

from ..app_service import WalletInterfaceService
from ..helpers import (
    _key_from_optional_hex,
    _require_magic_ucan,
)
from ..schemas import (
    AddLocationRequest,
    CreateWalletRequest,
    WalletControllerRecoveryRequest,
    WalletControllerRequest,
    WalletDeviceRequest,
    WalletRecoveryBundleRequest,
    WalletRecoveryPolicyRequest,
)


def create_router(service: WalletInterfaceService):
    if APIRouter is None:  # pragma: no cover
        raise RuntimeError("FastAPI is required to create the wallet interface API")
    router = APIRouter()
    app_service = service

    @router.post("/wallets")
    def create_wallet(request: CreateWalletRequest) -> dict[str, Any]:
        wallet = app_service.create_wallet(
            request.owner_did,
            controller_dids=request.controller_dids or None,
            approval_threshold=request.approval_threshold,
        )
        return wallet.to_dict()


    @router.get("/wallets/{wallet_id}")
    def get_wallet(wallet_id: str) -> dict[str, Any]:
        try:
            return app_service.get_wallet(wallet_id).to_dict()
        except Exception as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc


    @router.post("/wallets/{wallet_id}/controllers")
    def add_wallet_controller(wallet_id: str, request: WalletControllerRequest) -> dict[str, Any]:
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


    @router.post("/wallets/{wallet_id}/controllers/remove")
    def remove_wallet_controller(wallet_id: str, request: WalletControllerRequest) -> dict[str, Any]:
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


    @router.post("/wallets/{wallet_id}/devices")
    def add_wallet_device(wallet_id: str, request: WalletDeviceRequest) -> dict[str, Any]:
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


    @router.post("/wallets/{wallet_id}/devices/revoke")
    def revoke_wallet_device(wallet_id: str, request: WalletDeviceRequest) -> dict[str, Any]:
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


    @router.post("/wallets/{wallet_id}/recovery-policy")
    def set_wallet_recovery_policy(wallet_id: str, request: WalletRecoveryPolicyRequest) -> dict[str, Any]:
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


    @router.post("/wallets/{wallet_id}/recovery-bundles")
    def store_wallet_recovery_bundle(wallet_id: str, request: WalletRecoveryBundleRequest) -> dict[str, Any]:
        try:
            bundle = app_service.store_recovery_bundle(
                wallet_id,
                actor_did=request.actor_did,
                encrypted_bundle=request.encrypted_bundle,
                wrapping_method=request.wrapping_method,
                kdf=request.kdf,
                recovery_hint=request.recovery_hint,
                public_metadata=request.public_metadata,
            )
            return {
                "bundle": bundle.to_dict(),
                "privacy": {
                    "server_can_decrypt": False,
                    "plaintext_wallet_key_received": False,
                    "authorization_model": "wallet actor creates encrypted recovery material; magic-login UCAN can only read encrypted bundles",
                },
            }
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


    @router.get("/wallets/{wallet_id}/recovery-bundles/latest")
    def get_latest_wallet_recovery_bundle(
        wallet_id: str,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        resource = f"wallet://{wallet_id}/recovery-bundles/latest"
        ucan = _require_magic_ucan(
            authorization=authorization,
            wallet_id=wallet_id,
            ability="wallet/recovery/read_encrypted",
            resource=resource,
        )
        try:
            bundle = app_service.latest_recovery_bundle(wallet_id)
            return {
                "bundle": bundle.to_dict(),
                "ucan": {
                    "profile": str(ucan.get("profile") or ""),
                    "audience": str(ucan.get("aud") or ""),
                    "capabilities": ucan.get("capabilities") or [],
                    "expires_at": int(ucan.get("expiresAt") or 0),
                },
                "privacy": {
                    "server_can_decrypt": False,
                    "plaintext_wallet_key_returned": False,
                },
            }
        except Exception as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc


    @router.get("/wallets/{wallet_id}/recovery-bundles/{bundle_id}")
    def get_wallet_recovery_bundle(
        wallet_id: str,
        bundle_id: str,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        resource = f"wallet://{wallet_id}/recovery-bundles/{bundle_id}"
        ucan = _require_magic_ucan(
            authorization=authorization,
            wallet_id=wallet_id,
            ability="wallet/recovery/read_encrypted",
            resource=resource,
        )
        try:
            bundle = app_service.get_recovery_bundle(wallet_id, bundle_id)
            return {
                "bundle": bundle.to_dict(),
                "ucan": {
                    "profile": str(ucan.get("profile") or ""),
                    "audience": str(ucan.get("aud") or ""),
                    "capabilities": ucan.get("capabilities") or [],
                    "expires_at": int(ucan.get("expiresAt") or 0),
                },
                "privacy": {
                    "server_can_decrypt": False,
                    "plaintext_wallet_key_returned": False,
                },
            }
        except Exception as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc


    @router.post("/wallets/{wallet_id}/controllers/recover")
    def recover_wallet_controller(wallet_id: str, request: WalletControllerRecoveryRequest) -> dict[str, Any]:
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


    @router.post("/wallets/{wallet_id}/snapshot")
    def save_wallet_snapshot(wallet_id: str) -> dict[str, Any]:
        try:
            path = app_service.save_wallet_snapshot(wallet_id)
            return {"wallet_id": wallet_id, "path": str(path)}
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


    @router.get("/wallets/{wallet_id}/snapshot")
    def verify_wallet_snapshot(wallet_id: str) -> dict[str, Any]:
        try:
            return app_service.verify_wallet_snapshot(wallet_id)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


    @router.post("/wallets/{wallet_id}/snapshot/load")
    def load_wallet_snapshot(wallet_id: str) -> dict[str, Any]:
        try:
            app_service.load_wallet_snapshot(wallet_id)
            return {"wallet_id": wallet_id, "loaded": True}
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


    @router.post("/wallets/{wallet_id}/locations")
    def add_location(wallet_id: str, request: AddLocationRequest) -> dict[str, Any]:
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


    return router
