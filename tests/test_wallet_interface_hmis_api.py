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
