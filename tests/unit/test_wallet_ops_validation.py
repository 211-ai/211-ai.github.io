"""Unit tests for wallet_interface.ops validation functions."""

import json
import os
import tempfile
from pathlib import Path

import pytest


class TestValidateTargetSignoffPacket:
    """Tests for validate_target_signoff_packet."""

    def _validate(self, data):
        from wallet_interface.ops import validate_target_signoff_packet

        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            json.dump(data, f)
            fname = f.name
        try:
            return validate_target_signoff_packet(fname)
        finally:
            os.unlink(fname)

    def test_nonexistent_file_returns_error_status(self):
        from wallet_interface.ops import validate_target_signoff_packet

        result = validate_target_signoff_packet("/tmp/does_not_exist_12345.json")
        assert result["status"] == "error"
        assert "could not be read" in result["summary"]

    def test_non_object_json_returns_error(self):
        result = self._validate([1, 2, 3])
        assert result["status"] == "error"
        assert "JSON object" in result["summary"]

    def test_empty_object_fails_checks(self):
        result = self._validate({})
        assert result["status"] == "error"
        check_names = [c["name"] for c in result["checks"]]
        assert "environment_record" in check_names

    def test_result_has_required_keys(self):
        result = self._validate({})
        for key in ("source", "generated_at", "status", "checks"):
            assert key in result, f"missing key: {key}"

    def test_result_source_is_wallet_interface_ops(self):
        result = self._validate({})
        assert result["source"] == "wallet_interface.ops"

    def test_checks_list_items_have_name_status_summary(self):
        result = self._validate({})
        for check in result["checks"]:
            assert "name" in check
            assert "status" in check
            assert "summary" in check

    def test_template_packet_fails_validation(self):
        """The template (placeholder) packet should fail — it has no real values."""
        tpl_path = (
            Path(__file__).resolve().parents[2]
            / "docs"
            / "planning"
            / "WALLET_TARGET_PRODUCTION_SIGNOFF_PACKET.template.json"
        )
        if not tpl_path.exists():
            pytest.skip("template packet not found")
        from wallet_interface.ops import validate_target_signoff_packet

        result = validate_target_signoff_packet(tpl_path)
        assert result["status"] == "error"


class TestValidateTargetSignoffPacketTemplate:
    """Tests for validate_target_signoff_packet_template."""

    def test_template_file_present_validates_without_crash(self):
        from wallet_interface.ops import validate_target_signoff_packet_template

        result = validate_target_signoff_packet_template()
        # Should always return a dict with status
        assert "status" in result

    def test_result_source_matches(self):
        from wallet_interface.ops import validate_target_signoff_packet_template

        result = validate_target_signoff_packet_template()
        assert result["source"] == "wallet_interface.ops"


class TestOpsConstants:
    """Tests for module-level constants used by validation logic."""

    def test_required_environment_fields_non_empty(self):
        from wallet_interface.ops import _SIGNOFF_REQUIRED_ENVIRONMENT_FIELDS

        assert len(_SIGNOFF_REQUIRED_ENVIRONMENT_FIELDS) > 5

    def test_required_environment_fields_contains_expected_keys(self):
        from wallet_interface.ops import _SIGNOFF_REQUIRED_ENVIRONMENT_FIELDS

        assert "environment_name" in _SIGNOFF_REQUIRED_ENVIRONMENT_FIELDS
        assert "deployment_owner" in _SIGNOFF_REQUIRED_ENVIRONMENT_FIELDS

    def test_required_secret_refs_non_empty(self):
        from wallet_interface.ops import _SIGNOFF_REQUIRED_SECRET_REFS

        assert len(_SIGNOFF_REQUIRED_SECRET_REFS) >= 3

    def test_required_artifact_refs_non_empty(self):
        from wallet_interface.ops import _SIGNOFF_REQUIRED_ARTIFACT_REFS

        assert len(_SIGNOFF_REQUIRED_ARTIFACT_REFS) >= 3

    def test_placeholder_markers_non_empty(self):
        from wallet_interface.ops import _PRODUCTION_PLACEHOLDER_MARKERS

        assert len(_PRODUCTION_PLACEHOLDER_MARKERS) > 0
        assert "example.com" in _PRODUCTION_PLACEHOLDER_MARKERS

    def test_false_values_set(self):
        from wallet_interface.ops import _FALSE_VALUES

        assert "false" in _FALSE_VALUES
        assert "0" in _FALSE_VALUES

    def test_true_values_set(self):
        from wallet_interface.ops import _TRUE_VALUES

        assert "true" in _TRUE_VALUES
        assert "1" in _TRUE_VALUES


class TestOpsHelperFunctions:
    """Tests for _missing_or_placeholder_fields and _is_placeholder from ops.py."""

    def test_is_placeholder_detects_example_com(self):
        import wallet_interface.ops as ops

        fn = ops._is_placeholder
        assert fn("https://example.com/api")
        assert fn("replace-this-value")
        assert fn("changeme")
        assert not fn("https://wallet.my-org.com/api")

    def test_missing_or_placeholder_fields_detects_empty(self):
        import wallet_interface.ops as ops

        result = ops._missing_or_placeholder_fields({"name": ""}, ["name"])
        assert "name" in result

    def test_missing_or_placeholder_fields_detects_none(self):
        import wallet_interface.ops as ops

        result = ops._missing_or_placeholder_fields({"name": None}, ["name"])
        assert "name" in result

    def test_missing_or_placeholder_fields_ok_for_real_value(self):
        import wallet_interface.ops as ops

        result = ops._missing_or_placeholder_fields({"name": "production"}, ["name"])
        assert result == []

    def test_missing_or_placeholder_fields_missing_key(self):
        import wallet_interface.ops as ops

        result = ops._missing_or_placeholder_fields({}, ["name"])
        assert "name" in result
