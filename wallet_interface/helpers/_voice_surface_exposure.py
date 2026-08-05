"""Voice/phone surface exposure gate (VAS-006 / VAS-010).

Standalone so it can be tested even when other modules thrash.
Keep SURFACE_EXPOSURE_CLASS in lockstep with
data/voice_app_surface_coverage/baseline/voice-exposure-matrix.json.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final

SURFACE_EXPOSURE_CLASS: Final[Mapping[str, str]] = {
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

STAFF_DENY_CHANNELS: Final[frozenset[str]] = frozenset(
    {"voice", "phone", "telephony", "chat"}
)
NEVER_VOICE_CLASSES: Final[frozenset[str]] = frozenset({"never_voice"})
STAFF_ONLY_CLASSES: Final[frozenset[str]] = frozenset({"staff_only"})


def surface_exposure_error(
    surface_id: object | None,
    *,
    channel: object | None = "voice",
    role: str = "client",
    resolve=None,
) -> str | None:
    """Return deny code for client channels, or None if allowed.

    ``resolve`` optional callable surface_id -> allowlisted id (defaults to identity).
    """

    if surface_id is None or str(surface_id).strip() == "":
        return "surface_id_required"
    resolved = resolve(surface_id) if resolve is not None else str(surface_id).strip()
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
    if klass == "voice_read_only" and channel_norm in {"voice", "phone", "telephony"}:
        return "surface_voice_read_only"
    return None


def get_surface_exposure_class(surface_id: str) -> str | None:
    return SURFACE_EXPOSURE_CLASS.get(surface_id)
