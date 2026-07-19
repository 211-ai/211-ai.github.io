"""Route factory for notifications endpoints."""

from __future__ import annotations

from typing import Any

try:  # pragma: no cover - exercised when optional dependency is installed.
    from fastapi import APIRouter, Header, HTTPException, Request
except ImportError:  # pragma: no cover
    APIRouter = None  # type: ignore[assignment]
    class HTTPException(Exception):  # type: ignore[assignment]
        def __init__(self, status_code: int = 500, detail: str = "") -> None:
            super().__init__(detail)
            self.status_code = status_code
            self.detail = detail
    Header = None  # type: ignore[assignment]
    Request = None  # type: ignore[assignment]

from ..app_service import WalletInterfaceService
from ..helpers import (
    OPS_DEAD_DROP_ACTOR_DID,
    _extract_bearer_token,
    _normalize_phone_number,
    _ops_health_shared_secret,
    _require_internal_webhook_auth,
    _send_phone_call_notification,
    _send_sms_notification,
    _sms_inbound_actor_did,
)
from ..schemas import (
    InboundSmsForwardRequest,
    PhoneCallNotificationDispatchRequest,
    PhoneCallNotificationQueueRequest,
    SmsNotificationDispatchRequest,
    SmsNotificationQueueRequest,
)


def create_router(service: WalletInterfaceService):
    if APIRouter is None:  # pragma: no cover
        raise RuntimeError("FastAPI is required to create the wallet interface API")
    router = APIRouter()
    app_service = service

    @router.post("/wallets/{wallet_id}/notifications/sms/queue")
    def queue_sms_notification(wallet_id: str, request: SmsNotificationQueueRequest) -> dict[str, Any]:
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


    @router.get("/wallets/{wallet_id}/notifications/sms")
    def list_sms_notifications(wallet_id: str) -> dict[str, Any]:
        try:
            notifications = app_service.list_sms_notifications(wallet_id)
            return {
                "wallet_id": wallet_id,
                "count": len(notifications),
                "notifications": [record.to_dict() for record in notifications],
            }
        except Exception as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc


    @router.get("/wallets/{wallet_id}/messages/sms/inbound")
    def list_inbound_sms_messages(wallet_id: str) -> dict[str, Any]:
        try:
            messages = app_service.list_inbound_sms_messages(wallet_id)
            return {
                "wallet_id": wallet_id,
                "count": len(messages),
                "messages": [record.to_dict() for record in messages],
            }
        except Exception as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc


    @router.post("/messages/sms/inbound")
    def receive_inbound_sms_message(http_request: Request, payload: InboundSmsForwardRequest) -> dict[str, Any]:
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


    @router.post("/wallets/{wallet_id}/notifications/sms/{notification_id}/dispatch")
    def dispatch_sms_notification(
        wallet_id: str,
        notification_id: str,
        request: SmsNotificationDispatchRequest,
    ) -> dict[str, Any]:
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


    @router.post("/ops/notifications/sms/process-due")
    def process_due_sms_notifications(
        authorization: str | None = Header(default=None),
        x_wallet_ops_shared_secret: str | None = Header(default=None),
    ) -> dict[str, Any]:
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
        results: list[dict[str, Any]] = []
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


    @router.post("/wallets/{wallet_id}/notifications/calls/queue")
    def queue_phone_call_notification(wallet_id: str, request: PhoneCallNotificationQueueRequest) -> dict[str, Any]:
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


    @router.get("/wallets/{wallet_id}/notifications/calls")
    def list_phone_call_notifications(wallet_id: str) -> dict[str, Any]:
        try:
            notifications = app_service.list_phone_call_notifications(wallet_id)
            return {
                "wallet_id": wallet_id,
                "count": len(notifications),
                "notifications": [record.to_dict() for record in notifications],
            }
        except Exception as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc


    @router.post("/wallets/{wallet_id}/notifications/calls/{notification_id}/dispatch")
    def dispatch_phone_call_notification(
        wallet_id: str,
        notification_id: str,
        request: PhoneCallNotificationDispatchRequest,
    ) -> dict[str, Any]:
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


    @router.post("/ops/notifications/calls/process-due")
    def process_due_phone_call_notifications(
        authorization: str | None = Header(default=None),
        x_wallet_ops_shared_secret: str | None = Header(default=None),
    ) -> dict[str, Any]:
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
        results: list[dict[str, Any]] = []
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


    return router
