from __future__ import annotations

from wallet_interface.hmis.adapters.vendor_api import VendorApiHmisAdapter


def test_vendor_api_adapter_uses_fixture_responses() -> None:
    adapter = VendorApiHmisAdapter(
        auth_token="secret",
        fixture_responses={
            "lookup_client": {
                "summary": "lookup ok",
                "external_refs": {"external_id": "client-1"},
                "normalized_payload": {"candidates": [{"external_client_id": "client-1"}]},
            }
        },
    )

    result = adapter.execute(action_type="lookup_client", payload={"name": "Jane Doe"})

    assert "authorization" in adapter.build_auth_headers()
    assert result.ok is True
    assert result.external_refs["external_id"] == "client-1"



def test_vendor_api_adapter_normalizes_retryable_failures() -> None:
    adapter = VendorApiHmisAdapter(
        fixture_responses={
            "submit_referral": {
                "ok": False,
                "summary": "temporary outage",
                "errors": ["gateway timeout"],
                "retryable": True,
            }
        }
    )

    result = adapter.execute(action_type="submit_referral", payload={"local_ref": "ref-1"})

    assert result.ok is False
    assert result.retryable is True
    assert result.status == "retryable"
