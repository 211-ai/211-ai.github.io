"""Unit tests for wallet_interface/hmis/models.py and errors.py."""

from __future__ import annotations

import pytest


def _import_models():
    from wallet_interface.hmis.models import (
        HmisAdapterResult,
        HmisClientLink,
        HmisConsentRecord,
        HmisEnrollmentRecord,
        HmisHouseholdLink,
        HmisProgramLink,
        HmisReferralRecord,
        HmisSyncEvent,
    )
    return (
        HmisAdapterResult, HmisClientLink, HmisConsentRecord,
        HmisEnrollmentRecord, HmisHouseholdLink, HmisProgramLink,
        HmisReferralRecord, HmisSyncEvent,
    )


def _import_errors():
    from wallet_interface.hmis.errors import (
        HmisAdapterError,
        HmisConfigError,
        HmisConsentError,
        HmisIntegrationError,
        HmisMatchError,
        HmisMappingError,
        HmisPolicyError,
    )
    return (
        HmisAdapterError, HmisConfigError, HmisConsentError,
        HmisIntegrationError, HmisMatchError, HmisMappingError, HmisPolicyError,
    )


# ---------------------------------------------------------------------------
# HmisClientLink
# ---------------------------------------------------------------------------


class TestHmisClientLink:
    def _cls(self):
        _, cls, *_ = _import_models()
        return cls

    def test_required_field(self):
        cls = self._cls()
        link = cls(local_subject_ref="sub1")
        assert link.local_subject_ref == "sub1"

    def test_default_status(self):
        cls = self._cls()
        link = cls(local_subject_ref="sub1")
        assert link.status == "proposed"

    def test_default_match_confidence_none(self):
        cls = self._cls()
        link = cls(local_subject_ref="sub1")
        assert link.match_confidence is None

    def test_default_empty_metadata(self):
        cls = self._cls()
        link = cls(local_subject_ref="sub1")
        assert link.metadata == {}

    def test_custom_fields(self):
        cls = self._cls()
        link = cls(
            local_subject_ref="sub1",
            external_client_id="ext-123",
            status="verified",
            match_confidence=0.95,
        )
        assert link.external_client_id == "ext-123"
        assert link.status == "verified"
        assert link.match_confidence == 0.95

    def test_default_empty_tuples(self):
        cls = self._cls()
        link = cls(local_subject_ref="sub1")
        assert link.matched_fields == ()
        assert link.candidate_ids == ()


# ---------------------------------------------------------------------------
# HmisAdapterResult
# ---------------------------------------------------------------------------


class TestHmisAdapterResult:
    def _cls(self):
        cls, *_ = _import_models()
        return cls

    def _make(self, **overrides):
        cls = self._cls()
        defaults = {
            "ok": True,
            "action_type": "lookup_client",
            "adapter_name": "test-adapter",
            "status": "success",
            "summary": "OK",
        }
        defaults.update(overrides)
        return cls(**defaults)

    def test_ok_field(self):
        r = self._make(ok=True)
        assert r.ok is True

    def test_failure_state(self):
        r = self._make(ok=False, status="failed", summary="Network error")
        assert r.ok is False
        assert r.status == "failed"

    def test_default_empty_errors(self):
        r = self._make()
        assert r.errors == ()

    def test_default_retryable_false(self):
        r = self._make()
        assert r.retryable is False

    def test_custom_external_refs(self):
        r = self._make(external_refs={"client_id": "c123"})
        assert r.external_refs["client_id"] == "c123"

    def test_custom_warnings(self):
        r = self._make(warnings=("low confidence", "partial match"))
        assert "low confidence" in r.warnings


# ---------------------------------------------------------------------------
# Error hierarchy
# ---------------------------------------------------------------------------


class TestHmisErrorHierarchy:
    def _errs(self):
        return _import_errors()

    def test_base_is_runtime_error(self):
        errs = self._errs()
        HmisIntegrationError = errs[3]
        assert issubclass(HmisIntegrationError, RuntimeError)

    def test_config_error_is_integration_error(self):
        _, HmisConfigError, *_ = self._errs()
        HmisIntegrationError = self._errs()[3]
        assert issubclass(HmisConfigError, HmisIntegrationError)

    def test_policy_error_is_integration_error(self):
        errs = self._errs()
        HmisPolicyError = errs[6]
        HmisIntegrationError = errs[3]
        assert issubclass(HmisPolicyError, HmisIntegrationError)

    def test_consent_error_is_policy_error(self):
        errs = self._errs()
        HmisConsentError = errs[2]
        HmisPolicyError = errs[6]
        assert issubclass(HmisConsentError, HmisPolicyError)

    def test_adapter_error_is_integration_error(self):
        errs = self._errs()
        HmisAdapterError = errs[0]
        HmisIntegrationError = errs[3]
        assert issubclass(HmisAdapterError, HmisIntegrationError)

    def test_raise_and_catch_as_base(self):
        errs = self._errs()
        HmisConsentError = errs[2]
        HmisIntegrationError = errs[3]
        with pytest.raises(HmisIntegrationError):
            raise HmisConsentError("consent expired")

    def test_error_message_preserved(self):
        errs = self._errs()
        HmisConfigError = errs[1]
        try:
            raise HmisConfigError("invalid adapter URL")
        except HmisConfigError as exc:
            assert "invalid adapter URL" in str(exc)

    def test_match_error_is_integration_error(self):
        errs = self._errs()
        HmisMatchError = errs[4]
        HmisIntegrationError = errs[3]
        assert issubclass(HmisMatchError, HmisIntegrationError)

    def test_mapping_error_is_integration_error(self):
        errs = self._errs()
        HmisMappingError = errs[5]
        HmisIntegrationError = errs[3]
        assert issubclass(HmisMappingError, HmisIntegrationError)


# ---------------------------------------------------------------------------
# HmisHouseholdLink
# ---------------------------------------------------------------------------


class TestHmisHouseholdLink:
    def _cls(self):
        (_, _, _, _, cls, *_) = _import_models()
        return cls

    def test_required_fields(self):
        cls = self._cls()
        link = cls(local_household_ref="hh1")
        assert link.local_household_ref == "hh1"

    def test_default_status_proposed(self):
        cls = self._cls()
        link = cls(local_household_ref="hh1")
        assert link.status == "proposed"


# ---------------------------------------------------------------------------
# HmisSyncEvent
# ---------------------------------------------------------------------------


class TestHmisSyncEvent:
    def _cls(self):
        (_, _, _, _, _, _, _, cls) = _import_models()
        return cls

    def test_required_fields(self):
        cls = self._cls()
        event = cls(
            event_id="evt1",
            action_type="lookup_client",
            actor_id="actor1",
        )
        assert event.action_type == "lookup_client"
        assert event.event_id == "evt1"

    def test_default_status_pending(self):
        cls = self._cls()
        event = cls(
            event_id="evt1",
            action_type="submit_referral",
            actor_id="actor1",
        )
        assert event.status == "pending"

    def test_default_retry_count_zero(self):
        cls = self._cls()
        event = cls(event_id="evt1", action_type="lookup_client", actor_id="actor1")
        assert event.retry_count == 0

    def test_custom_status(self):
        cls = self._cls()
        event = cls(event_id="evt1", action_type="lookup_client", actor_id="actor1", status="success")
        assert event.status == "success"


# ---------------------------------------------------------------------------
# HmisAdapterCapabilities
# ---------------------------------------------------------------------------


class TestHmisAdapterCapabilities:
    def _cls(self):
        from wallet_interface.hmis.models import HmisAdapterCapabilities
        return HmisAdapterCapabilities

    def test_all_defaults_false(self):
        cls = self._cls()
        caps = cls()
        assert caps.supports_lookup is False
        assert caps.supports_referral_submit is False
        assert caps.supports_enrollment_submit is False
        assert caps.supports_status_sync is False
        assert caps.supports_reconciliation is False
        assert caps.supports_manual_review_packets is False

    def test_custom_capabilities(self):
        cls = self._cls()
        caps = cls(supports_lookup=True, supports_referral_submit=True)
        assert caps.supports_lookup is True
        assert caps.supports_referral_submit is True
        assert caps.supports_enrollment_submit is False


# ---------------------------------------------------------------------------
# ManualReviewHmisAdapter (pure functions)
# ---------------------------------------------------------------------------


class TestManualReviewAdapter:
    def _import(self):
        from wallet_interface.hmis.adapters.manual_review import (
            ManualReviewHmisAdapter,
            _normalized_text,
        )
        return ManualReviewHmisAdapter, _normalized_text

    def test_normalized_text_lowercases(self):
        _, fn = self._import()
        assert fn("HELLO") == "hello"

    def test_normalized_text_strips_whitespace(self):
        _, fn = self._import()
        assert fn("  hello  ") == "hello"

    def test_normalized_text_collapses_spaces(self):
        _, fn = self._import()
        assert fn("hello  world") == "hello  world"

    def test_adapter_capabilities(self):
        cls, _ = self._import()
        adapter = cls()
        caps = adapter.capabilities()
        assert caps.supports_manual_review_packets is True

    def test_adapter_capabilities_no_referral_submit_by_default(self):
        cls, _ = self._import()
        adapter = cls()
        caps = adapter.capabilities()
        assert caps.supports_referral_submit is False
