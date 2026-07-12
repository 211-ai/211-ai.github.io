"""Route factory for auth endpoints."""

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

    @router.get("/health")
    def health() -> Dict[str, Any]:
        warnings = _voice_proxy_runtime_warnings()
        response: Dict[str, Any] = {"status": "ok"}
        if warnings:
            response["warnings"] = warnings
        return response


    @router.post("/auth/magic-link/request")
    def request_magic_login_link(request: MagicLoginRequest) -> Dict[str, Any]:
        try:
            payload = _magic_login_payload_from_request(request)
            token = _sign_magic_login_token(payload)
            magic_link = _build_magic_login_link(token=token, base_url=_magic_login_base_url(request.base_url))
            expires_in_minutes = max(1, math.ceil((int(payload["expiresAt"]) - int(time.time() * 1000)) / 60000))
            metadata = {
                "message_type": "magic_login",
                "portal": payload["portal"],
                "wallet_id": str(payload.get("walletId") or ""),
                "nonce": str(payload.get("nonce") or ""),
            }
            if _is_email_contact(payload["contact"]):
                delivery = _send_auth_email_notification(
                    to_email=payload["contact"],
                    subject="Your 211 AI / Abby sign-in link",
                    body=(
                        "Use this link to sign in to 211 AI / Abby:\n\n"
                        f"{magic_link}\n\n"
                        f"This link expires in {expires_in_minutes} minutes. "
                        "If you did not request it, you can ignore this email."
                    ),
                    metadata=metadata,
                )
                channel = "email"
            else:
                delivery = _send_sms_notification(
                    to_phone=payload["contact"],
                    message=(
                        f"211 AI / Abby login: open {magic_link} "
                        f"This link expires in {expires_in_minutes} minutes. "
                        "Reply HELP for help or STOP to opt out."
                    ),
                    wallet_id=str(payload.get("walletId") or ""),
                    external_reference=str(payload.get("nonce") or ""),
                    metadata=metadata,
                )
                channel = "sms"
            return {
                "status": "sent",
                "channel": channel,
                "expires_at": int(payload["expiresAt"]),
                "wallet_config": _wallet_config_from_magic_payload(payload),
                **delivery,
            }
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


    @router.post("/auth/magic-link/verify")
    def verify_magic_login_link(request: MagicLoginVerifyRequest) -> Dict[str, Any]:
        try:
            payload = _verify_magic_login_token(request.token)
            return {
                "valid": True,
                "portal": str(payload["portal"]),
                "contact": str(payload["contact"]),
                "expires_at": int(payload["expiresAt"]),
                "wallet_config": _wallet_config_from_magic_payload(payload),
                "ucan": _issue_magic_ucan(payload),
            }
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


    return router
