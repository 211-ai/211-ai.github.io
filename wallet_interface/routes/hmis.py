"""Route factory for hmis endpoints."""

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

    @router.post("/wallets/{wallet_id}/hmis/lookup-clients")
    def lookup_hmis_clients(wallet_id: str, request: HmisClientLookupRequest) -> Dict[str, Any]:
        try:
            return app_service.lookup_hmis_clients(
                wallet_id,
                actor_did=request.actor_did,
                name=request.name,
                date_of_birth=request.date_of_birth,
                program_ref=request.program_ref,
            )
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


    @router.post("/wallets/{wallet_id}/hmis/lookup-households")
    def lookup_hmis_households(wallet_id: str, request: HmisHouseholdLookupRequest) -> Dict[str, Any]:
        try:
            return app_service.lookup_hmis_households(
                wallet_id,
                actor_did=request.actor_did,
                name=request.name,
                program_ref=request.program_ref,
            )
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


    @router.post("/wallets/{wallet_id}/hmis/program-links")
    def list_hmis_program_links(wallet_id: str, request: HmisProgramLinkListRequest) -> Dict[str, Any]:
        try:
            return app_service.list_hmis_program_links(
                wallet_id,
                actor_did=request.actor_did,
                name=request.name,
                program_ref=request.program_ref,
            )
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


    @router.get("/wallets/{wallet_id}/hmis/referral-drafts")
    def list_hmis_referral_drafts(wallet_id: str, status: str | None = None) -> Dict[str, Any]:
        try:
            return {
                "referral_drafts": [
                    draft.to_dict() for draft in app_service.list_hmis_referral_drafts(wallet_id, status=status)
                ]
            }
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


    @router.post("/wallets/{wallet_id}/hmis/referral-drafts")
    def create_hmis_referral_draft(wallet_id: str, request: HmisReferralDraftRequest) -> Dict[str, Any]:
        try:
            return app_service.create_hmis_referral_draft(
                wallet_id,
                actor_did=request.actor_did,
                local_subject_ref=request.local_subject_ref,
                destination_program_ref=request.destination_program_ref,
                service_plan_id=request.service_plan_id,
                service_doc_id=request.service_doc_id,
                provider_name=request.provider_name,
                program_name=request.program_name,
                summary=request.summary,
                eligibility_notes=request.eligibility_notes,
                contact_notes=request.contact_notes,
                source_content_cid=request.source_content_cid,
                source_page_cid=request.source_page_cid,
                metadata=request.metadata,
            ).to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


    @router.patch("/wallets/{wallet_id}/hmis/referral-drafts/{referral_draft_id}")
    def update_hmis_referral_draft(
        wallet_id: str,
        referral_draft_id: str,
        request: HmisReferralDraftUpdateRequest,
    ) -> Dict[str, Any]:
        try:
            return app_service.update_hmis_referral_draft(
                wallet_id,
                referral_draft_id,
                actor_did=request.actor_did,
                local_subject_ref=request.local_subject_ref,
                destination_program_ref=request.destination_program_ref,
                service_plan_id=request.service_plan_id,
                service_doc_id=request.service_doc_id,
                provider_name=request.provider_name,
                program_name=request.program_name,
                summary=request.summary,
                eligibility_notes=request.eligibility_notes,
                contact_notes=request.contact_notes,
                source_content_cid=request.source_content_cid,
                source_page_cid=request.source_page_cid,
                metadata=request.metadata,
            ).to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


    @router.post("/wallets/{wallet_id}/hmis/referral-drafts/{referral_draft_id}/validate")
    def validate_hmis_referral_draft(
        wallet_id: str,
        referral_draft_id: str,
        request: HmisReferralDraftValidationRequest,
    ) -> Dict[str, Any]:
        try:
            return app_service.validate_hmis_referral_draft(
                wallet_id,
                referral_draft_id,
                actor_did=request.actor_did,
            )
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


    @router.post("/wallets/{wallet_id}/hmis/referral-drafts/{referral_draft_id}/submit")
    def submit_hmis_referral_draft(
        wallet_id: str,
        referral_draft_id: str,
        request: HmisReferralDraftSubmitRequest,
    ) -> Dict[str, Any]:
        try:
            return app_service.submit_hmis_referral_draft(
                wallet_id,
                referral_draft_id,
                actor_did=request.actor_did,
            )
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


    return router
