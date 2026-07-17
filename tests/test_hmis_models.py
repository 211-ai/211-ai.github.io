from __future__ import annotations

from typing import cast

from wallet_interface.hmis import (
    HmisAdapterCapabilities,
    HmisAdapterResult,
    HmisClientLink,
    HmisConsentRecord,
    HmisEnrollmentRecord,
    HmisHouseholdLink,
    HmisProgramLink,
    HmisReferralRecord,
    HmisSyncEvent,
)
from wallet_interface.hmis.adapters.base import HmisAdapter


class DummyAdapter:
    name = "dummy"

    def capabilities(self) -> HmisAdapterCapabilities:
        return HmisAdapterCapabilities(supports_lookup=True)

    def execute(self, *, action_type, payload, context=None):
        return HmisAdapterResult.success(action_type=action_type, adapter_name=self.name, summary="ok")



def test_models_use_expected_defaults() -> None:
    assert HmisClientLink(local_subject_ref="wallet:1").status == "proposed"
    assert HmisHouseholdLink(local_household_ref="home:1").metadata == {}
    assert HmisProgramLink(local_program_ref="program:1").match_confidence is None
    assert HmisReferralRecord(
        local_referral_ref="ref:1",
        local_subject_ref="wallet:1",
        destination_program_ref="program:1",
    ).status == "draft"
    assert HmisEnrollmentRecord(
        local_enrollment_ref="enrollment:1",
        local_subject_ref="wallet:1",
        destination_program_ref="program:1",
    ).status == "draft"
    assert HmisConsentRecord(
        consent_id="consent-1",
        subject_ref="wallet:1",
        status="active",
        basis="client_consent",
        purpose="lookup",
    ).authorized_scopes == ()
    assert HmisSyncEvent(event_id="evt-1", action_type="lookup_client", actor_id="did:key:actor").retry_count == 0



def test_adapter_result_builders_capture_normalized_state() -> None:
    success = HmisAdapterResult.success(
        action_type="lookup_client",
        adapter_name="manual-review",
        summary="lookup ok",
        external_refs={"external_id": "abc"},
        normalized_payload={"candidates": []},
        warnings=("fixture",),
    )
    failure = HmisAdapterResult.failure(
        action_type="submit_referral",
        adapter_name="vendor-api",
        summary="temporary error",
        errors=("timeout",),
        retryable=True,
    )

    assert success.ok is True
    assert success.status == "success"
    assert success.external_refs["external_id"] == "abc"
    assert failure.ok is False
    assert failure.retryable is True
    assert failure.status == "retryable"



def test_adapter_protocol_is_runtime_compatible() -> None:
    adapter = DummyAdapter()
    typed = cast(HmisAdapter, adapter)
    result = typed.execute(action_type="lookup_client", payload={"name": "Jane"})

    assert isinstance(adapter.capabilities(), HmisAdapterCapabilities)
    assert result.summary == "ok"
