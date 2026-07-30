#!/usr/bin/env python3
"""Parse Retry-After values and turn checkpoint state into a restart decision."""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any


_DURATION_RE = re.compile(
    r"^(?:(?P<days>\d+)\s*(?:d|day|days)[,\s]+)?"
    r"(?P<hours>\d+):(?P<minutes>[0-5]\d):(?P<seconds>[0-5]\d(?:\.\d+)?)$",
    flags=re.IGNORECASE,
)
_SECONDS_RE = re.compile(r"^\d+(?:\.\d+)?$")


@dataclass(frozen=True)
class RetryAfterSchedule:
    """A parsed relative or absolute Retry-After value."""

    raw_value: str
    retry_at_epoch: float
    value_kind: str


@dataclass(frozen=True)
class RetryAfterDecision:
    """The bounded delay a supervisor should apply before its next attempt."""

    raw_value: str
    delay_seconds: float
    retry_at_epoch: float
    value_kind: str
    used_fallback: bool

    @property
    def retry_at_utc(self) -> str:
        return format_utc_timestamp(self.retry_at_epoch)


def format_utc_timestamp(epoch_seconds: float) -> str:
    return datetime.fromtimestamp(float(epoch_seconds), tz=timezone.utc).isoformat().replace("+00:00", "Z")


def parse_timestamp(value: Any) -> float | None:
    """Parse an ISO-8601 or HTTP-date timestamp as UTC epoch seconds."""
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = parsedate_to_datetime(text)
        except (TypeError, ValueError, OverflowError):
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    try:
        epoch_seconds = parsed.timestamp()
    except (OverflowError, OSError, ValueError):
        return None
    return epoch_seconds if math.isfinite(epoch_seconds) else None


def parse_relative_seconds(value: Any) -> float | None:
    """Parse seconds or the HF ``HH:MM:SS`` countdown format."""
    text = str(value or "").strip()
    if not text:
        return None
    if _SECONDS_RE.fullmatch(text):
        seconds = float(text)
        return seconds if math.isfinite(seconds) else None
    match = _DURATION_RE.fullmatch(text)
    if match is None:
        return None
    days = int(match.group("days") or 0)
    hours = int(match.group("hours"))
    minutes = int(match.group("minutes"))
    seconds = float(match.group("seconds"))
    return days * 86400.0 + hours * 3600.0 + minutes * 60.0 + seconds


def parse_retry_after(
    value: Any,
    *,
    now_epoch: float,
    relative_anchor_epoch: float | None = None,
) -> RetryAfterSchedule | None:
    """Parse numeric, HF countdown, ISO-8601, or HTTP Retry-After values.

    Relative values are anchored to the checkpoint's ``updatedAt`` timestamp
    when available. This avoids sleeping for the full countdown again after a
    host reboot or delayed service restart.
    """
    text = str(value or "").strip()
    if not text:
        return None
    relative_seconds = parse_relative_seconds(text)
    if relative_seconds is not None:
        anchor = float(now_epoch) if relative_anchor_epoch is None else float(relative_anchor_epoch)
        return RetryAfterSchedule(
            raw_value=text,
            retry_at_epoch=anchor + relative_seconds,
            value_kind="relative",
        )
    retry_at_epoch = parse_timestamp(text)
    if retry_at_epoch is None:
        return None
    return RetryAfterSchedule(
        raw_value=text,
        retry_at_epoch=retry_at_epoch,
        value_kind="absolute",
    )


def retry_after_decision_from_state(
    state: dict[str, Any] | None,
    *,
    now_epoch: float,
    fallback_seconds: float,
    minimum_seconds: float,
    grace_seconds: float,
) -> RetryAfterDecision:
    """Return a safe delay from a batch checkpoint.

    Missing or malformed values use ``fallback_seconds``. A small minimum
    prevents a stale checkpoint from becoming a hot loop, while grace allows a
    provider's quota window to settle before the next request.
    """
    fallback = max(0.0, float(fallback_seconds))
    minimum = max(0.0, float(minimum_seconds))
    grace = max(0.0, float(grace_seconds))
    payload = state if isinstance(state, dict) else {}
    raw_value = str(payload.get("retryAfter") or "").strip()
    anchor_epoch = parse_timestamp(payload.get("updatedAt"))
    schedule = parse_retry_after(
        raw_value,
        now_epoch=float(now_epoch),
        relative_anchor_epoch=anchor_epoch,
    )
    if schedule is None:
        delay_seconds = max(minimum, fallback)
        return RetryAfterDecision(
            raw_value=raw_value,
            delay_seconds=delay_seconds,
            retry_at_epoch=float(now_epoch) + delay_seconds,
            value_kind="fallback",
            used_fallback=True,
        )

    provider_retry_at = schedule.retry_at_epoch + grace
    delay_seconds = max(minimum, provider_retry_at - float(now_epoch))
    return RetryAfterDecision(
        raw_value=schedule.raw_value,
        delay_seconds=delay_seconds,
        retry_at_epoch=float(now_epoch) + delay_seconds,
        value_kind=schedule.value_kind,
        used_fallback=False,
    )
