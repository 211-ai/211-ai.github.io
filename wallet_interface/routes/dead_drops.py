"""Route factory for dead drops endpoints."""

from __future__ import annotations

from typing import Any
from urllib import error as urllib_error

try:  # pragma: no cover - exercised when optional dependency is installed.
    from fastapi import APIRouter, Header, HTTPException
except ImportError:  # pragma: no cover
    APIRouter = None  # type: ignore[assignment]
    HTTPException = None  # type: ignore[assignment]
    Header = None  # type: ignore[assignment]

from ..app_service import WalletInterfaceService
from ..helpers import (
    OPS_DEAD_DROP_ACTOR_DID,
    _extract_bearer_token,
    _ops_health_shared_secret,
    _require_portland_police_missing_email,
    _send_dead_drop_email,
)
from ..schemas import (
    MissingPersonDeadDropConfigRequest,
    MissingPersonDeadDropDispatchRequest,
    MissingPersonDeadDropEmailRequest,
)


def create_router(service: WalletInterfaceService):
    if APIRouter is None:  # pragma: no cover
        raise RuntimeError("FastAPI is required to create the wallet interface API")
    router = APIRouter()
    app_service = service

    @router.post("/wallets/{wallet_id}/dead-drops/missing-person")
    def send_missing_person_dead_drop_email(
        wallet_id: str, request: MissingPersonDeadDropEmailRequest
    ) -> dict[str, Any]:
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
        except urllib_error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace").strip() or str(exc)
            raise HTTPException(status_code=502, detail=detail) from exc
        except urllib_error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace").strip() or str(exc)
            raise HTTPException(status_code=502, detail=detail) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc


    @router.get("/wallets/{wallet_id}/dead-drops/missing-person")
    def get_missing_person_dead_drop(wallet_id: str) -> dict[str, Any]:
        try:
            return app_service.get_missing_person_dead_drop(wallet_id).to_dict()
        except Exception as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc


    @router.put("/wallets/{wallet_id}/dead-drops/missing-person")
    def save_missing_person_dead_drop(wallet_id: str, request: MissingPersonDeadDropConfigRequest) -> dict[str, Any]:
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


    @router.post("/wallets/{wallet_id}/dead-drops/missing-person/dispatch")
    def dispatch_missing_person_dead_drop(
        wallet_id: str, request: MissingPersonDeadDropDispatchRequest
    ) -> dict[str, Any]:
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


    @router.post("/ops/dead-drops/missing-person/process-due")
    def process_due_missing_person_dead_drops(
        authorization: str | None = Header(default=None),
        x_wallet_ops_shared_secret: str | None = Header(default=None),
    ) -> dict[str, Any]:
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
        results: list[dict[str, Any]] = []
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


    return router
