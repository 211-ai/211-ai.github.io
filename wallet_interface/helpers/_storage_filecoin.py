# ruff: noqa: E501
"""Filecoin pin sidecar helpers (stdlib-only, no optional deps required)."""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request

from ._app import FilecoinPinHandoffError


def _response_message_from_raw_json(raw: str) -> str:
    if not raw.strip():
        return ""
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return raw.strip()
    if not isinstance(parsed, dict):
        return raw.strip()
    return str(parsed.get("error") or parsed.get("message") or "").strip()


def _filecoin_pin_service_url() -> str:
    return str(os.getenv("WALLET_FILECOIN_PIN_SERVICE_URL") or "").strip().rstrip("/")


def _filecoin_pin_mock_status() -> str:
    return str(os.getenv("WALLET_FILECOIN_PIN_MOCK_STATUS") or "pinned").strip() or "pinned"


def _filecoin_pin_timeout_seconds() -> float:
    timeout_seconds = float(str(os.getenv("WALLET_FILECOIN_PIN_TIMEOUT_SECONDS") or "30").strip())
    if timeout_seconds <= 0:
        raise FilecoinPinHandoffError("WALLET_FILECOIN_PIN_TIMEOUT_SECONDS must be positive")
    return timeout_seconds


def _filecoin_pin_request_headers(*, include_json_content_type: bool) -> dict[str, str]:
    request_headers: dict[str, str] = {}
    if include_json_content_type:
        request_headers["content-type"] = "application/json"
    if bearer_token := str(os.getenv("WALLET_FILECOIN_PIN_BEARER_TOKEN") or "").strip():
        request_headers["authorization"] = f"Bearer {bearer_token}"
    if header_name := str(os.getenv("WALLET_FILECOIN_PIN_HTTP_HEADER_NAME") or "").strip():
        header_value = str(os.getenv("WALLET_FILECOIN_PIN_HTTP_HEADER_VALUE") or "").strip()
        if not header_value:
            raise FilecoinPinHandoffError(
                "WALLET_FILECOIN_PIN_HTTP_HEADER_VALUE is required when WALLET_FILECOIN_PIN_HTTP_HEADER_NAME is set"
            )
        request_headers[header_name] = header_value
    return request_headers


def _filecoin_pin_status_url(request_id: str) -> str:
    service_url = _filecoin_pin_service_url()
    return f"{service_url}/pins/{request_id}" if service_url else ""


def _filecoin_upload_status_url(request_id: str) -> str:
    return f"/filecoin-upload/status/{request_id}"


def _mock_filecoin_pin_request(method: str, path: str, *, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    normalized_method = str(method or "").strip().upper()
    normalized_path = str(path or "").strip()

    if normalized_method == "POST" and normalized_path == "/pins":
        cid = str((payload or {}).get("cid") or "").strip()
        if not cid:
            raise FilecoinPinHandoffError("mock Filecoin Pin request requires a cid")
        request_id = f"mock-pin-{hashlib.sha256(cid.encode('utf-8')).hexdigest()[:12]}"
        return {
            "requestid": request_id,
            "status": "queued",
            "info": {
                "provider": "mock-filecoin-pin",
                "cid": cid,
                "mock": True,
            },
        }

    if normalized_method == "GET" and normalized_path.startswith("/pins/"):
        request_id = normalized_path.rsplit("/", 1)[-1].strip()
        if not request_id:
            raise FilecoinPinHandoffError("mock Filecoin Pin status requires a request ID")
        return {
            "requestid": request_id,
            "status": _filecoin_pin_mock_status(),
            "info": {
                "provider": "mock-filecoin-pin",
                "mock": True,
                "pieceCid": f"baga6ea4seaq{hashlib.sha256(request_id.encode('utf-8')).hexdigest()[:16]}",
            },
        }

    raise FilecoinPinHandoffError(f"mock Filecoin Pin does not support {normalized_method} {normalized_path}")


def _filecoin_pin_request(method: str, path: str, *, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    service_url = _filecoin_pin_service_url()
    if not service_url:
        raise FilecoinPinHandoffError("WALLET_FILECOIN_PIN_SERVICE_URL is not configured")
    if service_url == "mock":
        return _mock_filecoin_pin_request(method, path, payload=payload)

    endpoint = f"{service_url}{path}"
    body = json.dumps(payload, sort_keys=True).encode("utf-8") if payload is not None else None
    req = urllib_request.Request(
        endpoint,
        data=body,
        headers=_filecoin_pin_request_headers(include_json_content_type=payload is not None),
        method=method,
    )
    try:
        with urllib_request.urlopen(req, timeout=_filecoin_pin_timeout_seconds()) as response:
            raw = response.read().decode("utf-8")
            content_type = str(getattr(response, "headers", {}).get("content-type", ""))
    except urllib_error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        detail = _response_message_from_raw_json(error_body) or f"Filecoin Pin sidecar rejected the request with HTTP {exc.code}"
        raise FilecoinPinHandoffError(detail) from exc
    except urllib_error.URLError as exc:
        raise FilecoinPinHandoffError(f"Unable to reach Filecoin Pin sidecar at {endpoint}: {exc.reason}") from exc

    if not raw:
        return {}
    if "json" not in content_type.lower() and not raw.lstrip().startswith("{"):
        raise FilecoinPinHandoffError("Filecoin Pin sidecar returned a non-JSON response")
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise FilecoinPinHandoffError("Filecoin Pin sidecar returned a non-object response")
    return parsed


def _fetch_filecoin_pin_status(request_id: str) -> dict[str, Any]:
    if not request_id.strip():
        raise ValueError("request ID is required")
    return _filecoin_pin_request("GET", f"/pins/{request_id}")


def _submit_ipfs_cid_to_filecoin_pin(
    cid: str,
    *,
    file_name: str | None = None,
    mime_type: str | None = None,
    source_record_id: str | None = None,
    wallet_id: str | None = None,
) -> dict[str, Any] | None:
    if not _filecoin_pin_service_url():
        return None

    origins = [
        origin.strip()
        for origin in str(os.getenv("WALLET_FILECOIN_PIN_ORIGINS") or "").split(",")
        if origin.strip()
    ]
    metadata: dict[str, str] = {"source": "211-ai-wallet"}
    if wallet_id:
        metadata["walletId"] = wallet_id
    if source_record_id:
        metadata["recordId"] = source_record_id
    if file_name:
        metadata["fileName"] = file_name
    if mime_type:
        metadata["mimeType"] = mime_type

    payload: dict[str, Any] = {
        "cid": cid,
        "meta": metadata,
    }
    if file_name:
        payload["name"] = file_name
    if origins:
        payload["origins"] = origins
    return _filecoin_pin_request("POST", "/pins", payload=payload)
