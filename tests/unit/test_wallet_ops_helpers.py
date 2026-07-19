"""Unit tests for wallet_interface/ops.py pure utility functions.

Exercises stateless helpers that require no network access or optional deps.
"""

from __future__ import annotations

import pytest


def _import_ops_helpers():
    try:
        from wallet_interface.ops import (
            _bool_env,
            _env,
            _is_placeholder,
            _missing_or_placeholder_fields,
            _report_status,
        )
        return _bool_env, _env, _is_placeholder, _missing_or_placeholder_fields, _report_status
    except ImportError:
        pytest.skip("wallet_interface.ops not importable (missing optional deps)")


# ---------------------------------------------------------------------------
# _is_placeholder
# ---------------------------------------------------------------------------

class TestIsPlaceholder:
    def test_empty_string_is_placeholder(self):
        _, _, is_ph, *_ = _import_ops_helpers()
        assert is_ph("")
        assert is_ph("   ")

    def test_real_value_not_placeholder(self):
        _, _, is_ph, *_ = _import_ops_helpers()
        assert not is_ph("https://real-domain.org")
        assert not is_ph("prod-api-key-abc")

    def test_example_com_is_placeholder(self):
        _, _, is_ph, *_ = _import_ops_helpers()
        assert is_ph("admin@example.com")
        assert is_ph("https://example.com/callback")

    def test_replace_prefix_is_placeholder(self):
        _, _, is_ph, *_ = _import_ops_helpers()
        assert is_ph("replace-this-value")
        assert is_ph("REPLACE-ME-NOW")

    def test_tbd_is_placeholder(self):
        _, _, is_ph, *_ = _import_ops_helpers()
        assert is_ph("tbd")
        assert is_ph("TBD")

    def test_todo_is_placeholder(self):
        _, _, is_ph, *_ = _import_ops_helpers()
        assert is_ph("TODO: fill in")

    def test_changeme_is_placeholder(self):
        _, _, is_ph, *_ = _import_ops_helpers()
        assert is_ph("changeme")
        assert is_ph("CHANGEME")


# ---------------------------------------------------------------------------
# _env
# ---------------------------------------------------------------------------

class TestEnv:
    def test_reads_from_explicit_mapping(self):
        bool_env, env, *_ = _import_ops_helpers()
        assert env({"MY_KEY": "my_val"}, "MY_KEY") == "my_val"

    def test_missing_key_returns_empty(self):
        bool_env, env, *_ = _import_ops_helpers()
        assert env({"OTHER": "x"}, "MISSING_KEY") == ""

    def test_none_falls_back_to_os_environ(self, monkeypatch):
        bool_env, env, *_ = _import_ops_helpers()
        monkeypatch.setenv("TEST_OPS_ENV_VAR", "fromenv")
        assert env(None, "TEST_OPS_ENV_VAR") == "fromenv"

    def test_none_value_returns_empty(self):
        bool_env, env, *_ = _import_ops_helpers()
        assert env({"KEY": None}, "KEY") == ""

    def test_strips_whitespace(self):
        bool_env, env, *_ = _import_ops_helpers()
        assert env({"K": "  trimmed  "}, "K") == "trimmed"


# ---------------------------------------------------------------------------
# _bool_env
# ---------------------------------------------------------------------------

class TestBoolEnv:
    def test_true_values(self):
        bool_env, *_ = _import_ops_helpers()
        for val in ("1", "true", "yes", "on"):
            assert bool_env({"K": val}, "K") is True

    def test_false_values(self):
        bool_env, *_ = _import_ops_helpers()
        for val in ("0", "false", "no", "off"):
            assert bool_env({"K": val}, "K") is False

    def test_empty_returns_none(self):
        bool_env, *_ = _import_ops_helpers()
        assert bool_env({"K": ""}, "K") is None

    def test_missing_returns_none(self):
        bool_env, *_ = _import_ops_helpers()
        assert bool_env({}, "K") is None

    def test_unrecognized_value_returns_none(self):
        bool_env, *_ = _import_ops_helpers()
        assert bool_env({"K": "maybe"}, "K") is None

    def test_case_insensitive(self):
        bool_env, *_ = _import_ops_helpers()
        assert bool_env({"K": "TRUE"}, "K") is True
        assert bool_env({"K": "FALSE"}, "K") is False


# ---------------------------------------------------------------------------
# _report_status
# ---------------------------------------------------------------------------

class TestReportStatus:
    def test_all_ok(self):
        *_, report_status = _import_ops_helpers()
        checks = [{"status": "ok"}, {"status": "ok"}]
        assert report_status(checks) == "ok"

    def test_one_warning(self):
        *_, report_status = _import_ops_helpers()
        checks = [{"status": "ok"}, {"status": "warning"}]
        assert report_status(checks) == "warning"

    def test_error_overrides_warning(self):
        *_, report_status = _import_ops_helpers()
        checks = [{"status": "warning"}, {"status": "error"}, {"status": "ok"}]
        assert report_status(checks) == "error"

    def test_empty_checks_is_ok(self):
        *_, report_status = _import_ops_helpers()
        assert report_status([]) == "ok"


# ---------------------------------------------------------------------------
# _missing_or_placeholder_fields
# ---------------------------------------------------------------------------

class TestMissingOrPlaceholderFields:
    def test_all_fields_present(self):
        _, _, _, missing, _ = _import_ops_helpers()
        payload = {"name": "Alice", "token": "real-prod-token"}
        assert missing(payload, ["name", "token"]) == []

    def test_missing_field_reported(self):
        _, _, _, missing, _ = _import_ops_helpers()
        payload = {"name": "Alice"}
        result = missing(payload, ["name", "email"])
        assert "email" in result

    def test_placeholder_field_reported(self):
        _, _, _, missing, _ = _import_ops_helpers()
        payload = {"url": "https://example.com/path"}
        result = missing(payload, ["url"])
        assert "url" in result

    def test_empty_string_field_reported(self):
        _, _, _, missing, _ = _import_ops_helpers()
        payload = {"key": ""}
        result = missing(payload, ["key"])
        assert "key" in result

    def test_none_value_reported(self):
        _, _, _, missing, _ = _import_ops_helpers()
        payload = {"key": None}
        result = missing(payload, ["key"])
        assert "key" in result
