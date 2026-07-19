"""Unit tests for wallet_interface/hmis/mapper.py and consent.py."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest


def _import_mapper():
    from wallet_interface.hmis.mapper import HmisFieldMapping, HmisMappingRegistry
    return HmisFieldMapping, HmisMappingRegistry


def _import_consent():
    from wallet_interface.hmis.consent import HmisConsentDecision, _parse_utc, evaluate_hmis_consent
    from wallet_interface.hmis.models import HmisConsentRecord
    return HmisConsentDecision, evaluate_hmis_consent, _parse_utc, HmisConsentRecord


# ---------------------------------------------------------------------------
# HmisFieldMapping
# ---------------------------------------------------------------------------


class TestHmisFieldMapping:
    def _cls(self):
        cls, _ = _import_mapper()
        return cls

    def test_source_and_target_fields(self):
        cls = self._cls()
        mapping = cls(source_field="src", target_field="dst")
        assert mapping.source_field == "src"
        assert mapping.target_field == "dst"

    def test_default_not_required(self):
        cls = self._cls()
        m = cls(source_field="s", target_field="t")
        assert m.required is False

    def test_default_none_value(self):
        cls = self._cls()
        m = cls(source_field="s", target_field="t")
        assert m.default_value is None

    def test_frozen(self):
        cls = self._cls()
        m = cls(source_field="s", target_field="t")
        with pytest.raises(Exception):
            m.source_field = "changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# HmisMappingRegistry
# ---------------------------------------------------------------------------


class TestHmisMappingRegistry:
    def _mk(self):
        FieldMapping, RegistryCls = _import_mapper()
        registry = RegistryCls(version="1.0")
        return registry, FieldMapping

    def test_register_and_retrieve(self):
        registry, FM = self._mk()
        registry.register("client", [FM(source_field="id", target_field="clientId")])
        assert "client" in registry.mappings

    def test_map_simple_payload(self):
        registry, FM = self._mk()
        registry.register("client", [FM(source_field="id", target_field="clientId")])
        result = registry.map_payload("client", {"id": "abc123"})
        assert result["clientId"] == "abc123"

    def test_required_field_missing_raises(self):
        from wallet_interface.hmis.errors import HmisMappingError
        registry, FM = self._mk()
        registry.register("strict", [FM(source_field="required_id", target_field="id", required=True)])
        with pytest.raises(HmisMappingError, match="required_id"):
            registry.map_payload("strict", {})

    def test_default_value_used_when_missing(self):
        registry, FM = self._mk()
        registry.register("defaults", [FM(source_field="status", target_field="state", default_value="pending")])
        result = registry.map_payload("defaults", {})
        assert result["state"] == "pending"

    def test_source_overrides_default(self):
        registry, FM = self._mk()
        registry.register("override", [FM(source_field="status", target_field="state", default_value="pending")])
        result = registry.map_payload("override", {"status": "active"})
        assert result["state"] == "active"

    def test_unknown_mapping_raises(self):
        from wallet_interface.hmis.errors import HmisMappingError
        registry, _ = self._mk()
        with pytest.raises(HmisMappingError, match="unknown"):
            registry.map_payload("nonexistent", {})

    def test_empty_mapping_name_raises(self):
        from wallet_interface.hmis.errors import HmisMappingError
        registry, FM = self._mk()
        with pytest.raises(HmisMappingError):
            registry.register("", [FM(source_field="x", target_field="y")])

    def test_empty_fields_raises(self):
        from wallet_interface.hmis.errors import HmisMappingError
        registry, _ = self._mk()
        with pytest.raises(HmisMappingError):
            registry.register("empty", [])

    def test_multiple_fields_mapped(self):
        registry, FM = self._mk()
        registry.register("multi", [
            FM(source_field="first_name", target_field="firstName"),
            FM(source_field="last_name", target_field="lastName"),
        ])
        result = registry.map_payload("multi", {"first_name": "Jane", "last_name": "Doe"})
        assert result["firstName"] == "Jane"
        assert result["lastName"] == "Doe"

    def test_null_value_treated_as_missing(self):
        registry, FM = self._mk()
        registry.register("nulls", [FM(source_field="val", target_field="out", default_value="default")])
        result = registry.map_payload("nulls", {"val": None})
        assert result["out"] == "default"


# ---------------------------------------------------------------------------
# _parse_utc
# ---------------------------------------------------------------------------


class TestParseUtc:
    def _fn(self):
        (_, _, fn, _) = _import_consent()
        return fn

    def test_none_returns_none(self):
        assert self._fn()(None) is None

    def test_empty_returns_none(self):
        assert self._fn()("") is None

    def test_utc_z_suffix(self):
        fn = self._fn()
        result = fn("2024-01-15T10:30:00Z")
        assert result is not None
        assert result.year == 2024
        assert result.month == 1

    def test_iso_with_offset(self):
        fn = self._fn()
        result = fn("2024-06-01T12:00:00+00:00")
        assert result is not None
        assert result.hour == 12


# ---------------------------------------------------------------------------
# evaluate_hmis_consent
# ---------------------------------------------------------------------------


def _make_consent(**overrides):
    (_, _, _, ConsentRecord) = _import_consent()
    defaults = {
        "consent_id": "c1",
        "subject_ref": "sub1",
        "status": "active",
        "basis": "client_consent",
        "purpose": "referral",
        "authorized_scopes": ("referral",),
    }
    defaults.update(overrides)
    return ConsentRecord(**defaults)


class TestEvaluateHmisConsent:
    def _fn(self):
        (_, fn, _, _) = _import_consent()
        return fn

    def test_active_consent_returns_decision(self):
        fn = self._fn()
        consent = _make_consent()
        decision = fn(consent, required_scope="referral")
        assert decision.allowed is True
        assert decision.scope == "referral"

    def test_inactive_consent_raises(self):
        fn = self._fn()
        from wallet_interface.hmis.errors import HmisConsentError
        consent = _make_consent(status="expired")
        with pytest.raises(HmisConsentError, match="not active"):
            fn(consent, required_scope="referral")

    def test_wrong_scope_raises(self):
        fn = self._fn()
        from wallet_interface.hmis.errors import HmisConsentError
        consent = _make_consent(authorized_scopes=("enrollment",))
        with pytest.raises(HmisConsentError, match="does not authorize"):
            fn(consent, required_scope="referral")

    def test_disallowed_basis_raises(self):
        fn = self._fn()
        from wallet_interface.hmis.errors import HmisPolicyError
        consent = _make_consent(basis="court_order")
        with pytest.raises(HmisPolicyError, match="not allowed"):
            fn(consent, required_scope="referral")

    def test_expired_consent_raises(self):
        fn = self._fn()
        from wallet_interface.hmis.errors import HmisConsentError
        now = datetime(2024, 1, 15, tzinfo=UTC)
        consent = _make_consent(expires_at="2024-01-10T00:00:00Z")
        with pytest.raises(HmisConsentError, match="expired"):
            fn(consent, required_scope="referral", now=now)

    def test_not_yet_effective_raises(self):
        fn = self._fn()
        from wallet_interface.hmis.errors import HmisConsentError
        now = datetime(2024, 1, 5, tzinfo=UTC)
        consent = _make_consent(effective_at="2024-01-10T00:00:00Z")
        with pytest.raises(HmisConsentError, match="not effective"):
            fn(consent, required_scope="referral", now=now)

    def test_revoked_consent_raises(self):
        fn = self._fn()
        from wallet_interface.hmis.errors import HmisConsentError
        now = datetime(2024, 1, 15, tzinfo=UTC)
        consent = _make_consent(revoked_at="2024-01-12T00:00:00Z")
        with pytest.raises(HmisConsentError, match="revoked"):
            fn(consent, required_scope="referral", now=now)

    def test_decision_includes_basis(self):
        fn = self._fn()
        consent = _make_consent()
        decision = fn(consent, required_scope="referral")
        assert decision.basis == "client_consent"

    def test_no_program_refs_adds_warning(self):
        fn = self._fn()
        consent = _make_consent(authorized_program_refs=())
        decision = fn(consent, required_scope="referral")
        assert any("program" in w.lower() for w in decision.warnings)

    def test_program_scope_enforced(self):
        fn = self._fn()
        from wallet_interface.hmis.errors import HmisConsentError
        consent = _make_consent(authorized_program_refs=("prog-1",))
        with pytest.raises(HmisConsentError, match="does not authorize program"):
            fn(consent, required_scope="referral", program_ref="prog-2")

    def test_program_scope_allowed(self):
        fn = self._fn()
        consent = _make_consent(authorized_program_refs=("prog-1",))
        decision = fn(consent, required_scope="referral", program_ref="prog-1")
        assert decision.allowed is True
