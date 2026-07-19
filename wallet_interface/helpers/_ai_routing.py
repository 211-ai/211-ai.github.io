# ruff: noqa: E501
"""AI-router rate-limiting and match-result helpers."""

from __future__ import annotations

import os
import re
import time
from typing import TYPE_CHECKING, Any

from ._app import _normalize_ipfs_cid, _valid_ipfs_cid

if TYPE_CHECKING:
    from ..app_service import WalletInterfaceService

_AI_ROUTER_RATE_LIMITS: dict[str, dict[str, Any]] = {}


def _match_to_dict(match) -> dict[str, Any]:
    return {
        "service": match.service.__dict__,
        "score": match.score,
        "reasons": list(match.reasons),
    }


def _analysis_result_to_dict(result: dict[str, Any]) -> dict[str, Any]:
    artifact = result["artifact"]
    artifact_data = artifact.to_dict() if hasattr(artifact, "to_dict") else dict(artifact)
    return {
        "artifact": artifact_data,
        "output": result["output"],
    }


def _wallet_router_subject(wallet_id: str, wallet_cid: str | None) -> str:
    normalized_cid = _normalize_ipfs_cid(str(wallet_cid or ""))
    if normalized_cid and _valid_ipfs_cid(normalized_cid):
        return normalized_cid
    if str(wallet_cid or "").strip():
        return re.sub(r"[^a-zA-Z0-9:._-]+", "-", str(wallet_cid).strip())[:160]
    return re.sub(r"[^a-zA-Z0-9:._-]+", "-", str(wallet_id or "unknown-wallet").strip())[:160]


def _require_wallet_router_actor(
    app_service: WalletInterfaceService,
    wallet_id: str,
    actor_did: str,
) -> None:
    wallet = app_service.get_wallet(wallet_id)
    actor = str(actor_did or "").strip()
    principals = {
        str(wallet.owner_did),
        *[str(item) for item in getattr(wallet, "controller_dids", [])],
        *[str(item) for item in getattr(wallet, "device_dids", [])],
    }
    if not actor:
        raise ValueError("actor_did is required")
    if actor not in principals:
        raise ValueError("actor_did is not authorized for this wallet")


def _wallet_router_rate_limit_per_minute() -> int:
    try:
        return max(1, int(os.getenv("WALLET_AI_ROUTER_RATE_LIMIT_PER_MINUTE", "30")))
    except Exception:
        return 30


def _wallet_router_rate_limit_per_day() -> int:
    try:
        return max(1, int(os.getenv("WALLET_AI_ROUTER_RATE_LIMIT_PER_DAY", "500")))
    except Exception:
        return 500


def _check_wallet_router_rate_limit(wallet_subject: str, *, cost: int = 1) -> dict[str, Any]:
    subject = wallet_subject or "unknown-wallet"
    now = time.time()
    minute_window = int(now // 60)
    day_window = int(now // 86400)
    state = _AI_ROUTER_RATE_LIMITS.setdefault(
        subject,
        {"minute_window": minute_window, "minute_count": 0, "day_window": day_window, "day_count": 0},
    )
    if state.get("minute_window") != minute_window:
        state["minute_window"] = minute_window
        state["minute_count"] = 0
    if state.get("day_window") != day_window:
        state["day_window"] = day_window
        state["day_count"] = 0
    per_minute = _wallet_router_rate_limit_per_minute()
    per_day = _wallet_router_rate_limit_per_day()
    next_minute = int(state.get("minute_count") or 0) + max(1, int(cost or 1))
    next_day = int(state.get("day_count") or 0) + max(1, int(cost or 1))
    if next_minute > per_minute:
        raise ValueError(f"wallet router rate limit exceeded for {subject}: {per_minute} requests per minute")
    if next_day > per_day:
        raise ValueError(f"wallet router rate limit exceeded for {subject}: {per_day} requests per day")
    state["minute_count"] = next_minute
    state["day_count"] = next_day
    return {
        "subject": subject,
        "cost": max(1, int(cost or 1)),
        "minuteLimit": per_minute,
        "minuteRemaining": max(0, per_minute - next_minute),
        "dayLimit": per_day,
        "dayRemaining": max(0, per_day - next_day),
    }


