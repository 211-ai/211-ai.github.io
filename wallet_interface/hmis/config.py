"""Configuration helpers for HMIS integration."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Literal

from .errors import HmisConfigError

HmisMode = Literal["disabled", "sandbox", "uat", "production"]
_VALID_MODES = {"disabled", "sandbox", "uat", "production"}


def _flag_from_env(name: str, *, default: bool) -> bool:
    explicit = os.getenv(name)
    if explicit is None:
        return default
    return explicit.strip().lower() not in {"0", "false", "no", "off"}


@dataclass(slots=True)
class HmisFeatureFlags:
    lookup_enabled: bool = True
    referral_drafts_enabled: bool = True
    submission_enabled: bool = False
    reconciliation_enabled: bool = False
    enrollment_enabled: bool = False
    ui_enabled: bool = True


@dataclass(slots=True)
class HmisConfig:
    mode: HmisMode = "disabled"
    coc_id: str = ""
    environment_name: str = ""
    adapter: str = "manual-review"
    state_root: str = "data/hmis"
    feature_flags: HmisFeatureFlags = field(default_factory=HmisFeatureFlags)

    @property
    def is_enabled(self) -> bool:
        return self.mode != "disabled"

    @property
    def is_production(self) -> bool:
        return self.mode == "production"



def load_hmis_config_from_env(prefix: str = "HMIS_") -> HmisConfig:
    raw_mode = str(os.getenv(f"{prefix}MODE") or "disabled").strip().lower()
    if raw_mode not in _VALID_MODES:
        raise HmisConfigError(f"HMIS mode must be one of {', '.join(sorted(_VALID_MODES))}")

    return HmisConfig(
        mode=raw_mode,
        coc_id=str(os.getenv(f"{prefix}COC_ID") or "").strip(),
        environment_name=str(os.getenv(f"{prefix}ENVIRONMENT") or raw_mode).strip(),
        adapter=str(os.getenv(f"{prefix}ADAPTER") or "manual-review").strip() or "manual-review",
        state_root=str(os.getenv(f"{prefix}STATE_ROOT") or "data/hmis").strip() or "data/hmis",
        feature_flags=HmisFeatureFlags(
            lookup_enabled=_flag_from_env(f"{prefix}LOOKUP_ENABLED", default=raw_mode != "disabled"),
            referral_drafts_enabled=_flag_from_env(
                f"{prefix}REFERRAL_DRAFTS_ENABLED", default=raw_mode != "disabled"
            ),
            submission_enabled=_flag_from_env(
                f"{prefix}SUBMISSION_ENABLED", default=raw_mode in {"uat", "production"}
            ),
            reconciliation_enabled=_flag_from_env(
                f"{prefix}RECONCILIATION_ENABLED", default=raw_mode in {"sandbox", "uat", "production"}
            ),
            enrollment_enabled=_flag_from_env(f"{prefix}ENROLLMENT_ENABLED", default=False),
            ui_enabled=_flag_from_env(f"{prefix}UI_ENABLED", default=True),
        ),
    )


__all__ = ["HmisConfig", "HmisFeatureFlags", "HmisMode", "load_hmis_config_from_env"]
