"""Voice/phone surface exposure gate (VAS-006 / VAS2-012).

Standalone-compatible: prefer accelerate action_runtime.surface_exposure when
importable so policy and client binding stay in lockstep.
Keep SURFACE_EXPOSURE_CLASS aligned with
data/voice_app_surface_full_coverage/baseline/voice-exposure-matrix.json
(and the v1 matrix of the same shape).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final

try:
    from ipfs_accelerate_py.action_runtime.surface_exposure import (
        NEVER_VOICE_CLASSES as _NEVER,
        STAFF_DENY_CHANNELS as _STAFF_CH,
        STAFF_ONLY_CLASSES as _STAFF,
        SURFACE_EXPOSURE_CLASS as _SURFACE_MAP,
        get_surface_exposure_class as _get_class,
        surface_exposure_deny_reason as _deny_reason,
    )

    SURFACE_EXPOSURE_CLASS: Final[Mapping[str, str]] = _SURFACE_MAP
    STAFF_DENY_CHANNELS: Final[frozenset[str]] = _STAFF_CH
    NEVER_VOICE_CLASSES: Final[frozenset[str]] = _NEVER
    STAFF_ONLY_CLASSES: Final[frozenset[str]] = _STAFF

    def get_surface_exposure_class(surface_id: str) -> str | None:
        return _get_class(surface_id)

    def surface_exposure_error(
        surface_id: object | None,
        *,
        channel: object | None = "voice",
        role: str = "client",
        resolve=None,
    ) -> str | None:
        if surface_id is None or str(surface_id).strip() == "":
            return "surface_id_required"
        resolved = (
            resolve(surface_id) if resolve is not None else str(surface_id).strip()
        )
        if resolved is None:
            return "surface_not_allowlisted"
        return _deny_reason(resolved, channel=channel, role=role)

except ImportError:  # pragma: no cover - lean envs without accelerate on path
    SURFACE_EXPOSURE_CLASS = {
        "home": "voice_navigable",
        "register": "voice_navigable",
        "check-in": "voice_navigable",
        "calendar": "voice_actionable",
        "messages": "voice_actionable",
        "contacts": "voice_navigable",
        "social-services": "voice_actionable",
        "interactions": "voice_navigable",
        "uploads": "voice_actionable",
        "settings": "voice_navigable",
        "analytics": "voice_read_only",
        "proof-center": "voice_read_only",
        "audit": "never_voice",
        "security": "never_voice",
        "exports": "never_voice",
        "recipient-access": "never_voice",
        "sharing-rules": "never_voice",
        "benefits-protection": "never_voice",
        "shelter": "staff_only",
        "provider-clients": "staff_only",
        "provider-cases": "staff_only",
        "provider-messages": "staff_only",
        "provider-analytics": "staff_only",
        "provider-proofs": "staff_only",
        "provider-operations": "staff_only",
    }
    STAFF_DENY_CHANNELS = frozenset({"voice", "phone", "telephony", "chat"})
    NEVER_VOICE_CLASSES = frozenset({"never_voice"})
    STAFF_ONLY_CLASSES = frozenset({"staff_only"})

    def get_surface_exposure_class(surface_id: str) -> str | None:
        return SURFACE_EXPOSURE_CLASS.get(surface_id)

    def surface_exposure_error(
        surface_id: object | None,
        *,
        channel: object | None = "voice",
        role: str = "client",
        resolve=None,
    ) -> str | None:
        if surface_id is None or str(surface_id).strip() == "":
            return "surface_id_required"
        resolved = (
            resolve(surface_id) if resolve is not None else str(surface_id).strip()
        )
        if resolved is None:
            return "surface_not_allowlisted"
        klass = SURFACE_EXPOSURE_CLASS.get(str(resolved), "never_voice")
        channel_norm = str(channel or "voice").strip().lower() or "voice"
        role_norm = str(role or "client").strip().lower() or "client"
        if klass in NEVER_VOICE_CLASSES:
            return "surface_never_voice"
        if klass in STAFF_ONLY_CLASSES:
            if role_norm != "staff" and channel_norm in STAFF_DENY_CHANNELS:
                return "surface_staff_only"
        if klass == "voice_read_only" and channel_norm in {
            "voice",
            "phone",
            "telephony",
        }:
            return "surface_voice_read_only"
        return None
