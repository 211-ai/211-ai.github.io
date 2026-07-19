"""Route factory for proofs endpoints."""

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

from ipfs_datasets_py.wallet.ucan import invocation_to_token

from ..app_service import WalletInterfaceService
from ..helpers import (
    _key_from_optional_hex,
)
from ..schemas import (
    CoarseLocationGrantRequest,
    CoarseLocationInvocationRequest,
    DocumentPrivacyProfileProofRequest,
    LocationDistanceProofGrantRequest,
    LocationDistanceProofRequest,
    LocationRegionProofGrantRequest,
    LocationRegionProofRequest,
)


def create_router(service: WalletInterfaceService):
    if APIRouter is None:  # pragma: no cover
        raise RuntimeError("FastAPI is required to create the wallet interface API")
    router = APIRouter()
    app_service = service

    @router.post("/wallets/{wallet_id}/locations/{location_record_id}/coarse-grants")
    def create_coarse_location_grant(
        wallet_id: str,
        location_record_id: str,
        request: CoarseLocationGrantRequest,
    ) -> dict[str, Any]:
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


    @router.post("/wallets/{wallet_id}/locations/{location_record_id}/coarse-invocations")
    def issue_coarse_location_invocation(
        wallet_id: str,
        location_record_id: str,
        request: CoarseLocationInvocationRequest,
    ) -> dict[str, Any]:
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


    @router.post("/wallets/{wallet_id}/locations/{location_record_id}/region-proof-grants")
    def create_location_region_proof_grant(
        wallet_id: str,
        location_record_id: str,
        request: LocationRegionProofGrantRequest,
    ) -> dict[str, Any]:
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


    @router.post("/wallets/{wallet_id}/locations/{location_record_id}/region-proofs")
    def create_location_region_proof(
        wallet_id: str,
        location_record_id: str,
        request: LocationRegionProofRequest,
    ) -> dict[str, Any]:
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


    @router.post("/wallets/{wallet_id}/locations/{location_record_id}/distance-proof-grants")
    def create_location_distance_proof_grant(
        wallet_id: str,
        location_record_id: str,
        request: LocationDistanceProofGrantRequest,
    ) -> dict[str, Any]:
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


    @router.post("/wallets/{wallet_id}/locations/{location_record_id}/distance-proofs")
    def create_location_distance_proof(
        wallet_id: str,
        location_record_id: str,
        request: LocationDistanceProofRequest,
    ) -> dict[str, Any]:
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


    @router.post("/wallets/{wallet_id}/records/{record_id}/document-profile-proofs")
    def create_document_profile_proof(
        wallet_id: str,
        record_id: str,
        request: DocumentPrivacyProfileProofRequest,
    ) -> dict[str, Any]:
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


    @router.get("/wallets/{wallet_id}/proofs")
    def list_proof_receipts(wallet_id: str) -> dict[str, Any]:
        try:
            return {"proofs": [proof.to_dict() for proof in app_service.list_proof_receipts(wallet_id)]}
        except Exception as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc


    return router
