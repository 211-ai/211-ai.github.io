"""Route factory for analytics endpoints."""

from __future__ import annotations

from typing import Any

try:  # pragma: no cover - exercised when optional dependency is installed.
    from fastapi import APIRouter, HTTPException, status
except ImportError:  # pragma: no cover
    APIRouter = None  # type: ignore[assignment]
    class HTTPException(Exception):  # type: ignore[assignment]
        def __init__(self, status_code: int = 500, detail: str = "") -> None:
            super().__init__(detail)
            self.status_code = status_code
            self.detail = detail
    status = None  # type: ignore[assignment]

from ..app_service import WalletInterfaceService
from ..helpers import (
    _match_to_dict,
)
from ..schemas import (
    AnalyticsConsentFromTemplateRequest,
    AnalyticsConsentRevokeRequest,
    AnalyticsContributionRequest,
    AnalyticsTemplateRequest,
    DerivedServiceMatchRequest,
    PrivateAggregateCohortCountRequest,
    PrivateAggregateCountRequest,
)


def create_router(service: WalletInterfaceService):
    if APIRouter is None:  # pragma: no cover
        raise RuntimeError("FastAPI is required to create the wallet interface API")
    router = APIRouter()
    app_service = service

    @router.post("/analytics/templates")
    def create_analytics_template(request: AnalyticsTemplateRequest) -> dict[str, Any]:
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


    @router.get("/analytics/templates")
    def list_analytics_templates(include_inactive: bool = False) -> dict[str, Any]:
        return {
            "templates": [
                template.to_dict()
                for template in app_service.list_analytics_templates(include_inactive=include_inactive)
            ]
        }


    @router.get("/wallets/{wallet_id}/analytics/consents")
    def list_analytics_consents(wallet_id: str, status: str = "all") -> dict[str, Any]:
        try:
            return {
                "consents": [
                    consent.to_dict()
                    for consent in app_service.list_analytics_consents(wallet_id, status=status)
                ]
            }
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


    @router.post("/wallets/{wallet_id}/analytics/consents/from-template")
    def create_analytics_consent_from_template(
        wallet_id: str,
        request: AnalyticsConsentFromTemplateRequest,
    ) -> dict[str, Any]:
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


    @router.post("/wallets/{wallet_id}/analytics/consents/{consent_id}/revoke")
    def revoke_analytics_consent(
        wallet_id: str,
        consent_id: str,
        request: AnalyticsConsentRevokeRequest,
    ) -> dict[str, Any]:
        try:
            consent = app_service.revoke_analytics_consent(
                wallet_id,
                consent_id,
                actor_did=request.actor_did,
            )
            return consent.to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


    @router.post("/wallets/{wallet_id}/analytics/contributions")
    def create_analytics_contribution(
        wallet_id: str,
        request: AnalyticsContributionRequest,
    ) -> dict[str, Any]:
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


    @router.post("/analytics/{template_id}/count")
    def run_private_aggregate_count(
        template_id: str,
        request: PrivateAggregateCountRequest,
    ) -> dict[str, Any]:
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


    @router.post("/analytics/{template_id}/count-by-fields")
    def run_private_aggregate_count_by_fields(
        template_id: str,
        request: PrivateAggregateCohortCountRequest,
    ) -> dict[str, Any]:
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


    @router.post("/services/match-derived")
    def match_services_from_derived(request: DerivedServiceMatchRequest) -> dict[str, Any]:
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


    return router
