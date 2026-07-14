# ruff: noqa: E501
"""Auth, magic-login, UCAN, and outbound notification helpers."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import smtplib
import time
from collections.abc import Mapping
from email.message import EmailMessage
from email.utils import make_msgid
from typing import TYPE_CHECKING, Any
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

if TYPE_CHECKING:
    from ..schemas.wallet_schemas import MagicLoginRequest

try:
    from .._vendor import ensure_ipfs_datasets_py_path

    ensure_ipfs_datasets_py_path()

    from ipfs_datasets_py.utils.secrets import resolve_secret  # noqa: E402

    from ._app import PORTLAND_POLICE_MISSING_EMAIL  # noqa: E402
    _OPTIONAL_DEPS_AVAILABLE = True
except ImportError:
    resolve_secret = None  # type: ignore[assignment]
    PORTLAND_POLICE_MISSING_EMAIL = "missing@police.portlandoregon.gov"
    _OPTIONAL_DEPS_AVAILABLE = False

try:  # pragma: no cover
    from fastapi import HTTPException
except ImportError:  # pragma: no cover
    HTTPException = None  # type: ignore[assignment]


def _extract_bearer_token(authorization: str | None) -> str:
    raw = str(authorization or "").strip()
    if not raw:
        return ""
    scheme, _, token = raw.partition(" ")
    if scheme.lower() != "bearer":
        return ""
    return token.strip()


def _require_portland_police_missing_email(to_email: str) -> str:
    normalized = str(to_email or "").strip().lower()
    if normalized != PORTLAND_POLICE_MISSING_EMAIL:
        raise ValueError(
            f"missing-person dead drop recipient must be {PORTLAND_POLICE_MISSING_EMAIL}"
        )
    return PORTLAND_POLICE_MISSING_EMAIL


def _normalize_phone_number(phone: str) -> str:
    raw = str(phone or "").strip()
    if not raw:
        raise ValueError("to_phone is required")
    digits = re.sub(r"\D", "", raw)
    if len(digits) < 10:
        raise ValueError("to_phone must include at least 10 digits")
    return f"+{digits}" if raw.startswith("+") else digits


def _normalize_login_contact(value: str) -> str:
    normalized = str(value or "").strip()
    if "@" in normalized:
        normalized = normalized.lower()
        _parts = normalized.split("@")
        if len(_parts) != 2 or not _parts[0] or not _parts[1] or "." not in _parts[1]:
            raise ValueError("contact must be a valid email address or telephone number")
        return normalized
    return _normalize_phone_number(normalized)


def _is_email_contact(value: str) -> bool:
    return "@" in str(value or "")


def _sms_inbound_actor_did() -> str:
    return str(os.getenv("WALLET_SMS_INBOUND_ACTOR_DID") or "did:wallet:sms-bridge").strip()


def _require_internal_webhook_auth(
    *,
    env_prefix: str,
    authorization: str | None,
    headers: Mapping[str, str],
    error_detail: str,
) -> None:
    expected_bearer = str(os.getenv(f"{env_prefix}_BEARER_TOKEN") or "").strip()
    header_name = str(os.getenv(f"{env_prefix}_HTTP_HEADER_NAME") or "").strip()
    header_value = str(os.getenv(f"{env_prefix}_HTTP_HEADER_VALUE") or "").strip()
    if header_name and not header_value:
        raise RuntimeError(f"{env_prefix}_HTTP_HEADER_VALUE is required when header name is set")

    supplied_bearer = _extract_bearer_token(authorization)
    if expected_bearer and supplied_bearer == expected_bearer:
        return
    if header_name and str(headers.get(header_name) or "").strip() == header_value:
        return
    if not expected_bearer and not header_name:
        raise RuntimeError(
            f"{env_prefix}_BEARER_TOKEN or {env_prefix}_HTTP_HEADER_NAME must be configured for inbound webhook delivery"
        )
    raise HTTPException(status_code=401, detail=error_detail)


def _send_webhook_notification(
    *,
    env_prefix: str,
    required_key: str,
    required_value: str,
    extra_payload: dict[str, Any] | None = None,
) -> dict[str, str]:
    webhook_url = str(os.getenv(f"{env_prefix}_WEBHOOK_URL") or "").strip()
    backend = str(os.getenv(f"{env_prefix}_BACKEND") or ("http" if webhook_url else "")).strip().lower()
    if not backend or not webhook_url:
        raise RuntimeError(
            f"{env_prefix}_WEBHOOK_URL environment variable is required for delivery but is not configured"
        )
    if backend != "http":
        raise RuntimeError(f"{env_prefix}_BACKEND must be http when delivery is enabled")

    extra_headers: dict[str, str] = {}
    if bearer_token := str(os.getenv(f"{env_prefix}_BEARER_TOKEN") or "").strip():
        extra_headers["authorization"] = f"Bearer {bearer_token}"
    if header_name := str(os.getenv(f"{env_prefix}_HTTP_HEADER_NAME") or "").strip():
        header_value = str(os.getenv(f"{env_prefix}_HTTP_HEADER_VALUE") or "").strip()
        if not header_value:
            raise RuntimeError(f"{env_prefix}_HTTP_HEADER_VALUE is required when header name is set")
        extra_headers[header_name] = header_value

    timeout_seconds = float(str(os.getenv(f"{env_prefix}_TIMEOUT_SECONDS") or "15").strip())
    if timeout_seconds <= 0:
        raise RuntimeError(f"{env_prefix}_TIMEOUT_SECONDS must be positive")

    payload = {
        required_key: required_value,
        **dict(extra_payload or {}),
    }

    request_headers = {"content-type": "application/json", **extra_headers}
    body = json.dumps(payload, sort_keys=True).encode("utf-8")
    req = urllib_request.Request(
        webhook_url,
        data=body,
        headers=request_headers,
        method="POST",
    )
    with urllib_request.urlopen(req, timeout=timeout_seconds) as response:
        raw = response.read().decode("utf-8")
        content_type = str(getattr(response, "headers", {}).get("content-type", ""))
        status = str(getattr(response, "status", getattr(response, "code", 200)))

    response_payload: dict[str, Any] = {}
    if raw:
        if "json" in content_type.lower() or raw.lstrip().startswith("{"):
            parsed = json.loads(raw)
            if not isinstance(parsed, dict):
                raise ValueError("SMS delivery response must be a JSON object")
            response_payload = parsed

    provider_message_id = str(
        response_payload.get("provider_message_id")
        or response_payload.get("provider_call_id")
        or response_payload.get("message_id")
        or response_payload.get("call_id")
        or response_payload.get("email_id")
        or response_payload.get("id")
        or ""
    )
    result = {
        "provider": str(response_payload.get("provider") or "http"),
        "provider_status": str(response_payload.get("status") or status),
    }
    if provider_message_id:
        result["provider_message_id"] = provider_message_id
    return result


def _send_sms_notification(
    *,
    to_phone: str,
    message: str,
    wallet_id: str = "",
    external_reference: str = "",
    metadata: dict[str, Any] | None = None,
) -> dict[str, str]:
    normalized_phone = _normalize_phone_number(to_phone)
    normalized_message = str(message or "").strip()
    if not normalized_message:
        raise ValueError("message is required")
    return _send_webhook_notification(
        env_prefix="WALLET_SMS",
        required_key="to_phone",
        required_value=normalized_phone,
        extra_payload={
            "message": normalized_message,
            "wallet_id": str(wallet_id or "").strip(),
            "external_reference": str(external_reference or "").strip(),
            "metadata": dict(metadata or {}),
        },
    )


def _send_auth_email_notification(
    *,
    to_email: str,
    subject: str,
    body: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, str]:
    normalized_to_email = str(to_email or "").strip().lower()
    _email_parts = normalized_to_email.split("@")
    if len(_email_parts) != 2 or not _email_parts[0] or not _email_parts[1] or "." not in _email_parts[1]:
        raise ValueError("to_email must be a valid email address")
    return _send_webhook_notification(
        env_prefix="WALLET_AUTH_EMAIL",
        required_key="to_email",
        required_value=normalized_to_email,
        extra_payload={
            "subject": str(subject or "").strip(),
            "body": str(body or ""),
            "from_email": str(os.getenv("WALLET_AUTH_EMAIL_FROM_EMAIL") or "no-reply@211-ai.com").strip(),
            "metadata": dict(metadata or {}),
        },
    )


_MAGIC_LOGIN_CONTEXT = "abby-login-token-v1"
_MAGIC_LOGIN_PARAM = "abbyLogin"
_MAGIC_UCAN_CONTEXT = "abby-magic-ucan-v1"
_MAGIC_UCAN_ISSUER = "did:web:211-ai.com"


def _magic_login_secret() -> str:
    return resolve_secret("WALLET_MAGIC_LOGIN_SECRET", "MAGIC_LOGIN_SECRET").strip()


def _base64url_encode_bytes(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _base64url_decode_to_bytes(value: str) -> bytes:
    padded = str(value or "").strip()
    padded += "=" * (-len(padded) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii"))


def _hmac_base64url(secret: str, value: str) -> str:
    return _base64url_encode_bytes(hmac.new(secret.encode("utf-8"), value.encode("utf-8"), hashlib.sha256).digest())


def _sign_magic_login_token(payload: dict[str, Any]) -> str:
    secret = _magic_login_secret()
    if not secret:
        raise RuntimeError("WALLET_MAGIC_LOGIN_SECRET is required for passwordless login")
    payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    payload_encoded = _base64url_encode_bytes(payload_json)
    signature = _hmac_base64url(secret, f"{_MAGIC_LOGIN_CONTEXT}.{payload_encoded}")
    return f"{payload_encoded}.{signature}"


def _verify_magic_login_token(token: str) -> dict[str, Any]:
    secret = _magic_login_secret()
    if not secret:
        raise RuntimeError("WALLET_MAGIC_LOGIN_SECRET is required for passwordless login")
    parts = str(token or "").strip().split(".")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError("magic link token is malformed")
    payload_encoded, signature = parts
    expected = _hmac_base64url(secret, f"{_MAGIC_LOGIN_CONTEXT}.{payload_encoded}")
    if not hmac.compare_digest(signature, expected):
        raise ValueError("magic link signature is invalid")
    try:
        payload = json.loads(_base64url_decode_to_bytes(payload_encoded).decode("utf-8"))
    except Exception as exc:
        raise ValueError("magic link payload is malformed") from exc
    if not isinstance(payload, dict):
        raise ValueError("magic link payload is malformed")
    if payload.get("v") != 1 or payload.get("portal") not in {"client", "provider"}:
        raise ValueError("magic link payload is malformed")
    contact = str(payload.get("contact") or "").strip()
    nonce = str(payload.get("nonce") or "").strip()
    issued_at = int(payload.get("issuedAt") or 0)
    expires_at = int(payload.get("expiresAt") or 0)
    now_ms = int(time.time() * 1000)
    if not contact or not nonce or not issued_at or not expires_at:
        raise ValueError("magic link payload is malformed")
    if issued_at > now_ms + 5 * 60 * 1000:
        raise ValueError("magic link was issued in the future")
    if expires_at <= now_ms:
        raise ValueError("magic link is expired")
    return payload


def _allowed_magic_login_hosts() -> set[str]:
    raw = str(os.getenv("WALLET_MAGIC_LOGIN_ALLOWED_HOSTS") or "").strip()
    values = raw.split(",") if raw else ["211-ai.com", "www.211-ai.com", "211-ai.github.io", "localhost", "127.0.0.1"]
    return {value.strip().lower() for value in values if value.strip()}


def _magic_login_base_url(requested: str) -> str:
    fallback = str(os.getenv("WALLET_MAGIC_LOGIN_BASE_URL") or "https://211-ai.com/").strip()
    value = str(requested or fallback).strip()
    parsed = urllib_parse.urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("base_url must be an absolute http(s) URL")
    if str(parsed.hostname or "").lower() not in _allowed_magic_login_hosts():
        raise ValueError("base_url host is not allowed")
    return value


def _build_magic_login_link(*, token: str, base_url: str) -> str:
    parsed = urllib_parse.urlparse(base_url)
    query = dict(urllib_parse.parse_qsl(parsed.query, keep_blank_values=True))
    query[_MAGIC_LOGIN_PARAM] = token
    return urllib_parse.urlunparse(
        parsed._replace(
            query=urllib_parse.urlencode(query),
            fragment=parsed.fragment or "/",
        )
    )


def _magic_login_payload_from_request(request: MagicLoginRequest) -> dict[str, Any]:
    portal = str(request.portal or "client").strip().lower()
    if portal not in {"client", "provider"}:
        raise ValueError("portal must be client or provider")
    issued_at = int(time.time() * 1000)
    ttl_seconds = int(str(os.getenv("WALLET_MAGIC_LOGIN_TTL_SECONDS") or "600").strip() or "600")
    ttl_seconds = max(60, min(ttl_seconds, 3600))
    return {
        "v": 1,
        "portal": portal,
        "contact": _normalize_login_contact(request.contact),
        "issuedAt": issued_at,
        "expiresAt": issued_at + ttl_seconds * 1000,
        "nonce": secrets.token_urlsafe(18),
        "walletId": str(request.wallet_id or "").strip(),
        "walletApiBaseUrl": str(request.wallet_api_base_url or "").strip(),
        "actorDid": str(request.actor_did or "").strip(),
    }


def _wallet_config_from_magic_payload(payload: Mapping[str, Any]) -> dict[str, str]:
    wallet_id = str(payload.get("walletId") or "").strip()
    api_base_url = str(payload.get("walletApiBaseUrl") or "").strip()
    actor_did = str(payload.get("actorDid") or "").strip()
    wallet_config: dict[str, str] = {}
    if wallet_id:
        wallet_config["walletId"] = wallet_id
    if api_base_url:
        wallet_config["apiBaseUrl"] = api_base_url
    if actor_did:
        wallet_config["actorDid"] = actor_did
    return wallet_config


def _magic_contact_subject_did(contact: str) -> str:
    digest = hashlib.sha256(str(contact or "").strip().lower().encode("utf-8")).hexdigest()[:32]
    return f"did:abby:contact:{digest}"


def _magic_ucan_capabilities(wallet_id: str) -> list[dict[str, str]]:
    wallet = str(wallet_id or "").strip()
    capabilities = [{"with": "wallet://*", "can": "wallet/login"}]
    if wallet:
        resource = f"wallet://{wallet}"
        capabilities.extend(
            [
                {"with": resource, "can": "wallet/recovery/start"},
                {"with": f"{resource}/recovery-bundles/*", "can": "wallet/recovery/read_encrypted"},
                {"with": f"{resource}/records/*", "can": "wallet/encrypted/read"},
            ]
        )
    return capabilities


def _sign_magic_ucan(payload: dict[str, Any]) -> str:
    secret = _magic_login_secret()
    if not secret:
        raise RuntimeError("WALLET_MAGIC_LOGIN_SECRET is required for passwordless login")
    payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    payload_encoded = _base64url_encode_bytes(payload_json)
    signature = _hmac_base64url(secret, f"{_MAGIC_UCAN_CONTEXT}.{payload_encoded}")
    return f"{_MAGIC_UCAN_CONTEXT}.{payload_encoded}.{signature}"


def _verify_magic_ucan(token: str) -> dict[str, Any]:
    secret = _magic_login_secret()
    if not secret:
        raise RuntimeError("WALLET_MAGIC_LOGIN_SECRET is required for passwordless login")
    parts = str(token or "").strip().split(".")
    if len(parts) != 3 or parts[0] != _MAGIC_UCAN_CONTEXT:
        raise ValueError("UCAN token is malformed")
    _, payload_encoded, signature = parts
    expected = _hmac_base64url(secret, f"{_MAGIC_UCAN_CONTEXT}.{payload_encoded}")
    if not hmac.compare_digest(signature, expected):
        raise ValueError("UCAN signature is invalid")
    try:
        payload = json.loads(_base64url_decode_to_bytes(payload_encoded).decode("utf-8"))
    except Exception as exc:
        raise ValueError("UCAN payload is malformed") from exc
    if not isinstance(payload, dict) or payload.get("profile") != _MAGIC_UCAN_CONTEXT:
        raise ValueError("UCAN payload is malformed")
    expires_at = int(payload.get("expiresAt") or 0)
    if not expires_at or expires_at <= int(time.time() * 1000):
        raise ValueError("UCAN token is expired")
    return payload


def _issue_magic_ucan(payload: Mapping[str, Any]) -> dict[str, Any]:
    contact = str(payload.get("contact") or "").strip()
    wallet_id = str(payload.get("walletId") or "").strip()
    issued_at = int(time.time() * 1000)
    expires_at = min(int(payload.get("expiresAt") or issued_at), issued_at + 15 * 60 * 1000)
    ucan_payload = {
        "profile": _MAGIC_UCAN_CONTEXT,
        "iss": _MAGIC_UCAN_ISSUER,
        "aud": _magic_contact_subject_did(contact),
        "walletId": wallet_id,
        "contactHash": hashlib.sha256(contact.lower().encode("utf-8")).hexdigest(),
        "capabilities": _magic_ucan_capabilities(wallet_id),
        "issuedAt": issued_at,
        "expiresAt": expires_at,
        "nonce": secrets.token_urlsafe(18),
        "caveats": {
            "no_plaintext_key_access": True,
            "server_can_decrypt": False,
            "purpose": "passwordless_wallet_login_and_recovery",
        },
    }
    token = _sign_magic_ucan(ucan_payload)
    return {
        "profile": _MAGIC_UCAN_CONTEXT,
        "issuer": ucan_payload["iss"],
        "audience": ucan_payload["aud"],
        "token": token,
        "capabilities": ucan_payload["capabilities"],
        "expires_at": expires_at,
        "caveats": ucan_payload["caveats"],
    }


def _capability_resource_matches(pattern: str, resource: str) -> bool:
    if pattern == "*" or pattern == resource:
        return True
    if pattern.endswith("/*") and resource.startswith(pattern[:-1]):
        return True
    return False


def _require_magic_ucan(
    *,
    authorization: str | None,
    wallet_id: str,
    ability: str,
    resource: str,
) -> dict[str, Any]:
    token = _extract_bearer_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="recovery UCAN authorization required")
    try:
        payload = _verify_magic_ucan(token)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    if str(payload.get("walletId") or "") != str(wallet_id):
        raise HTTPException(status_code=403, detail="UCAN wallet scope does not match")
    capabilities = payload.get("capabilities")
    if not isinstance(capabilities, list):
        raise HTTPException(status_code=403, detail="UCAN has no capabilities")
    for capability in capabilities:
        if not isinstance(capability, Mapping):
            continue
        if str(capability.get("can") or "") != ability:
            continue
        if _capability_resource_matches(str(capability.get("with") or ""), resource):
            return payload
    raise HTTPException(status_code=403, detail="UCAN does not allow this recovery action")


def _send_phone_call_notification(*, to_phone: str, script: str) -> dict[str, str]:
    normalized_phone = _normalize_phone_number(to_phone)
    normalized_script = str(script or "").strip()
    if not normalized_script:
        raise ValueError("script is required")
    return _send_webhook_notification(
        env_prefix="WALLET_CALL",
        required_key="to_phone",
        required_value=normalized_phone,
        extra_payload={"script": normalized_script},
    )




