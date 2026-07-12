# ruff: noqa: E501
"""App-level constants, IPFS CID utilities, and service factory."""

from __future__ import annotations

import json
import os
import re
from typing import Any
from urllib import parse as urllib_parse
from urllib import request as urllib_request

from .._vendor import ensure_ipfs_datasets_py_path
from ..app_service import WalletInterfaceService

ensure_ipfs_datasets_py_path()

from ipfs_datasets_py.utils.secrets import resolve_secret  # noqa: E402

PORTLAND_POLICE_MISSING_EMAIL = "missing@police.portlandoregon.gov"
OPS_DEAD_DROP_ACTOR_DID = "did:wallet:ops"
_IPFS_CID_PATTERN = re.compile(r"^(?:bafy[a-z0-9]{20,}|Qm[1-9A-HJ-NP-Za-km-z]{44})$")


class FilecoinPinHandoffError(RuntimeError):
    """Raised when the optional Filecoin Pin sidecar handoff fails."""


def _cors_origins_from_env() -> list[str]:
    origins = [
        origin.strip()
        for origin in os.environ.get("WALLET_API_CORS_ORIGINS", "").split(",")
        if origin.strip()
    ]
    return origins


def _prepare_hf_router_environment(kwargs: dict[str, Any] | None = None) -> dict[str, Any]:
    """Make encrypted HF credentials visible to ipfs_datasets_py router helpers."""
    token = (
        resolve_secret(
            "IPFS_DATASETS_PY_HF_API_TOKEN",
            "HF_TOKEN",
            "HUGGINGFACEHUB_API_TOKEN",
            "HUGGINGFACE_API_TOKEN",
            "HUGGINGFACE_HUB_TOKEN",
            "HF_API_TOKEN",
        )
        or ""
    ).strip()
    if token:
        for key in ("IPFS_DATASETS_PY_HF_API_TOKEN", "HF_TOKEN", "HUGGINGFACEHUB_API_TOKEN"):
            if not os.getenv(key, "").strip():
                os.environ[key] = token
    bill_to = (
        os.getenv("IPFS_DATASETS_PY_HF_BILL_TO")
        or os.getenv("HUGGINGFACE_BILL_TO")
        or os.getenv("HF_BILL_TO")
        or "publicus"
    ).strip()
    if bill_to:
        os.environ.setdefault("IPFS_DATASETS_PY_HF_BILL_TO", bill_to)
        os.environ.setdefault("HUGGINGFACE_BILL_TO", bill_to)
    router_kwargs = dict(kwargs or {})
    if bill_to:
        router_kwargs.setdefault("bill_to", bill_to)
        router_kwargs.setdefault("organization", bill_to)
    router_kwargs.setdefault("hf_provider", os.getenv("IPFS_DATASETS_PY_HF_PROVIDER", "auto"))
    return router_kwargs


def _normalize_ipfs_cid(value: str) -> str:
    normalized = str(value or "").strip()
    normalized = normalized.replace("ipfs://", "")
    normalized = re.sub(r"^/?ipfs/", "", normalized)
    normalized = normalized.split("/", 1)[0].strip()
    return normalized


def _valid_ipfs_cid(value: str) -> bool:
    return bool(_IPFS_CID_PATTERN.match(_normalize_ipfs_cid(value)))


def _ipfs_proxy_allowed_cids_from_env() -> set[str]:
    raw = str(os.getenv("WALLET_IPFS_PROXY_ALLOWED_CIDS") or "")
    return {
        normalized
        for part in re.split(r"[\s,]+", raw)
        if (normalized := _normalize_ipfs_cid(part))
    }


def _ipfs_proxy_allows_cid(cid: str) -> bool:
    normalized = _normalize_ipfs_cid(cid)
    allowed = _ipfs_proxy_allowed_cids_from_env()
    if not allowed:
        return True
    return normalized in allowed


def _ipfs_proxy_media_type(data: bytes) -> str:
    try:
        decoded = data.decode("utf-8")
        json.loads(decoded)
        return "application/json"
    except Exception:
        return "application/octet-stream"


def _ipfs_proxy_fallback_gateways() -> list[str]:
    configured = [
        gateway.strip().rstrip("/")
        for gateway in os.getenv("WALLET_IPFS_PROXY_FALLBACK_GATEWAYS", "").split(",")
        if gateway.strip()
    ]
    if configured:
        return configured
    return [
        "https://w3s.link/ipfs",
        "https://ipfs.io/ipfs",
        "https://dweb.link/ipfs",
    ]


def _fetch_ipfs_cid_via_gateway(cid: str) -> bytes:
    last_error: Exception | None = None
    for gateway in _ipfs_proxy_fallback_gateways():
        url = f"{gateway.rstrip('/')}/{urllib_parse.quote(cid, safe='')}"
        try:
            req = urllib_request.Request(url, headers={"Accept": "application/octet-stream,*/*"})
            with urllib_request.urlopen(req, timeout=30) as response:
                return response.read()
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"Unable to fetch CID from fallback gateways: {last_error}") from last_error


def _wallet_interface_service_from_env() -> WalletInterfaceService:
    services_jsonl = str(os.environ.get("WALLET_SERVICES_JSONL") or "").strip()
    if services_jsonl:
        return WalletInterfaceService.from_services_jsonl(services_jsonl)
    return WalletInterfaceService()




def _ops_health_shared_secret() -> str:
    return str(os.getenv("WALLET_OPS_HEALTH_SHARED_SECRET") or "").strip()

