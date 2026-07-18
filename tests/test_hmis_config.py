from __future__ import annotations

import pytest

from wallet_interface.hmis.config import load_hmis_config_from_env
from wallet_interface.hmis.errors import HmisConfigError


def test_hmis_config_defaults_to_disabled(monkeypatch) -> None:
    monkeypatch.delenv("HMIS_MODE", raising=False)

    config = load_hmis_config_from_env()

    assert config.mode == "disabled"
    assert config.is_enabled is False
    assert config.feature_flags.lookup_enabled is False



def test_hmis_config_reads_modes_and_flags(monkeypatch) -> None:
    monkeypatch.setenv("HMIS_MODE", "sandbox")
    monkeypatch.setenv("HMIS_COC_ID", "OR-500")
    monkeypatch.setenv("HMIS_ADAPTER", "file-exchange")
    monkeypatch.setenv("HMIS_SUBMISSION_ENABLED", "true")

    config = load_hmis_config_from_env()

    assert config.mode == "sandbox"
    assert config.coc_id == "OR-500"
    assert config.adapter == "file-exchange"
    assert config.feature_flags.submission_enabled is True
    assert config.feature_flags.reconciliation_enabled is True



def test_hmis_config_rejects_unknown_mode(monkeypatch) -> None:
    monkeypatch.setenv("HMIS_MODE", "qa")

    with pytest.raises(HmisConfigError, match="HMIS mode"):
        load_hmis_config_from_env()
