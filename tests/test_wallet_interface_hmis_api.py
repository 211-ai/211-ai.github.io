from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from wallet_interface import WalletInterfaceService, create_app



def _client(tmp_path) -> TestClient:
    service = WalletInterfaceService(repository_root=tmp_path / "wallet-repository")
    return TestClient(create_app(service=service))



def _wallet_id(client: TestClient) -> str:
    response = client.post("/wallets", json={"owner_did": "did:key:worker"})
    assert response.status_code == 200
    return response.json()["wallet_id"]



def test_hmis_lookup_and_referral_draft_endpoints(tmp_path) -> None:
    client = _client(tmp_path)
    wallet_id = _wallet_id(client)

    lookup = client.post(
        f"/wallets/{wallet_id}/hmis/lookup-clients",
        json={
            "actor_did": "did:key:worker",
            "name": "Jane Doe",
            "date_of_birth": "1990-04-05",
            "program_ref": "shelter-a",
        },
    )
    assert lookup.status_code == 200
    lookup_payload = lookup.json()
    assert lookup_payload["clients"][0]["name"] == "J*** D***"
    assert lookup_payload["clients"][0]["masked"] is True

    programs = client.post(
        f"/wallets/{wallet_id}/hmis/program-links",
        json={"actor_did": "did:key:worker", "program_ref": "shelter-a"},
    )
    assert programs.status_code == 200
    assert programs.json()["program_links"][0]["external_project_id"] == "HMIS-PROJECT-100"

    created = client.post(
        f"/wallets/{wallet_id}/hmis/referral-drafts",
        json={
            "actor_did": "did:key:worker",
            "local_subject_ref": "wallet:subject-1",
            "destination_program_ref": "shelter-a",
            "provider_name": "Safe Harbor Shelter",
            "program_name": "Emergency Shelter",
            "summary": "Client requests emergency shelter placement.",
        },
    )
    assert created.status_code == 200
    draft = created.json()
    assert draft["status"] == "ready"

    validated = client.post(
        f"/wallets/{wallet_id}/hmis/referral-drafts/{draft['referral_draft_id']}/validate",
        json={"actor_did": "did:key:worker"},
    )
    assert validated.status_code == 200
    assert validated.json()["status"] == "ready"

    submitted = client.post(
        f"/wallets/{wallet_id}/hmis/referral-drafts/{draft['referral_draft_id']}/submit",
        json={"actor_did": "did:key:worker"},
    )
    assert submitted.status_code == 200
    assert submitted.json()["status"] == "submitted"

    listed = client.get(f"/wallets/{wallet_id}/hmis/referral-drafts")
    assert listed.status_code == 200
    assert listed.json()["referral_drafts"][0]["status"] == "submitted"


def test_hmis_enrollment_draft_endpoints(tmp_path) -> None:
    """Phase 5: enrollment draft list, create, and submit endpoints."""
    client = _client(tmp_path)
    wallet_id = _wallet_id(client)

    # List should be empty initially
    listed_empty = client.get(f"/wallets/{wallet_id}/hmis/enrollment-drafts")
    assert listed_empty.status_code == 200
    assert listed_empty.json()["enrollment_drafts"] == []

    # Create a draft with required fields
    created = client.post(
        f"/wallets/{wallet_id}/hmis/enrollment-drafts",
        json={
            "actor_did": "did:key:worker",
            "local_subject_ref": "wallet:subject-1",
            "destination_program_ref": "shelter-a",
            "entry_date": "2026-02-01",
            "summary": "Client enrolling in emergency shelter program.",
        },
    )
    assert created.status_code == 200
    draft = created.json()
    assert draft["status"] == "ready"
    assert "enrollment_draft_id" in draft

    # List should now return the draft
    listed = client.get(f"/wallets/{wallet_id}/hmis/enrollment-drafts")
    assert listed.status_code == 200
    assert len(listed.json()["enrollment_drafts"]) == 1
    assert listed.json()["enrollment_drafts"][0]["status"] == "ready"

    # Filter by status
    listed_ready = client.get(
        f"/wallets/{wallet_id}/hmis/enrollment-drafts", params={"status": "ready"}
    )
    assert listed_ready.status_code == 200
    assert len(listed_ready.json()["enrollment_drafts"]) == 1

    listed_submitted = client.get(
        f"/wallets/{wallet_id}/hmis/enrollment-drafts", params={"status": "submitted"}
    )
    assert listed_submitted.status_code == 200
    assert listed_submitted.json()["enrollment_drafts"] == []

    # Submit the draft
    submitted = client.post(
        f"/wallets/{wallet_id}/hmis/enrollment-drafts/{draft['enrollment_draft_id']}/submit",
        json={"actor_did": "did:key:worker"},
    )
    assert submitted.status_code == 200
    result = submitted.json()
    assert result["status"] == "submitted"
    assert "enrollment_draft" in result

    # List after submission should show submitted status
    listed_after = client.get(f"/wallets/{wallet_id}/hmis/enrollment-drafts")
    assert listed_after.status_code == 200
    assert listed_after.json()["enrollment_drafts"][0]["status"] == "submitted"


def test_hmis_enrollment_draft_missing_fields_error(tmp_path) -> None:
    """Phase 5: creating an enrollment draft with missing required fields returns validation errors."""
    client = _client(tmp_path)
    wallet_id = _wallet_id(client)

    # Missing local_subject_ref
    created = client.post(
        f"/wallets/{wallet_id}/hmis/enrollment-drafts",
        json={
            "actor_did": "did:key:worker",
            "local_subject_ref": "",
            "destination_program_ref": "shelter-a",
        },
    )
    assert created.status_code == 200
    draft = created.json()
    assert draft["status"] == "draft"
    assert "missing local_subject_ref" in draft["validation_errors"]


def test_hmis_enrollment_draft_submit_invalid_raises(tmp_path) -> None:
    """Phase 5: submitting a draft with validation errors returns 400."""
    client = _client(tmp_path)
    wallet_id = _wallet_id(client)

    created = client.post(
        f"/wallets/{wallet_id}/hmis/enrollment-drafts",
        json={
            "actor_did": "did:key:worker",
            "local_subject_ref": "",
            "destination_program_ref": "shelter-a",
        },
    )
    assert created.status_code == 200
    draft_id = created.json()["enrollment_draft_id"]

    submitted = client.post(
        f"/wallets/{wallet_id}/hmis/enrollment-drafts/{draft_id}/submit",
        json={"actor_did": "did:key:worker"},
    )
    assert submitted.status_code == 400


def test_hmis_enrollment_draft_submit_not_found_raises(tmp_path) -> None:
    """Phase 5: submitting a non-existent enrollment draft returns 400."""
    client = _client(tmp_path)
    wallet_id = _wallet_id(client)

    submitted = client.post(
        f"/wallets/{wallet_id}/hmis/enrollment-drafts/hmis-enrollment-draft-does-not-exist/submit",
        json={"actor_did": "did:key:worker"},
    )
    assert submitted.status_code == 400
