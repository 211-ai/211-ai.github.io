"""Contract tests for the wallet interface API.

These tests validate the API surface against published contracts using
FastAPI's TestClient. They require ``ipfs_datasets_py`` to be installed.

Run with:
    python -m pytest tests/contract/ -q
"""

from __future__ import annotations

import pytest

# Skip the entire module if the required dependencies are not installed
try:
    from fastapi.testclient import TestClient  # noqa: F401
    from ipfs_datasets_py.wallet import DeterministicLocationRegionProofBackend  # noqa: F401

    from wallet_interface import ServiceRecord, WalletInterfaceService, create_app  # noqa: F401
    _DEPS_AVAILABLE = True
except ImportError:
    _DEPS_AVAILABLE = False

pytestmark = pytest.mark.skipif(not _DEPS_AVAILABLE, reason="ipfs_datasets_py or fastapi not installed")


def _make_client() -> TestClient:
    from fastapi.testclient import TestClient

    from wallet_interface import ServiceRecord, WalletInterfaceService, create_app

    service = WalletInterfaceService(
        services=[
            ServiceRecord(
                id="housing-1",
                name="Portland Housing Help",
                description="Rent assistance and emergency shelter navigation.",
                categories="housing shelter rent",
                city="Portland",
                state="OR",
            )
        ]
    )
    return TestClient(create_app(service=service))


class TestHealthContract:
    def test_health_returns_ok(self):
        client = _make_client()
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok"

    def test_health_response_shape(self):
        client = _make_client()
        response = client.get("/health")
        data = response.json()
        assert "status" in data


class TestWalletCRUDContract:
    def test_create_wallet_returns_wallet_id(self):
        client = _make_client()
        response = client.post("/wallets", json={"owner_did": "did:key:test-owner"})
        assert response.status_code == 200
        data = response.json()
        assert "wallet_id" in data

    def test_get_wallet_after_create(self):
        client = _make_client()
        create_resp = client.post("/wallets", json={"owner_did": "did:key:test-owner"})
        assert create_resp.status_code == 200
        wallet_id = create_resp.json()["wallet_id"]

        get_resp = client.get(f"/wallets/{wallet_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["wallet_id"] == wallet_id

    def test_get_nonexistent_wallet_returns_404(self):
        client = _make_client()
        response = client.get("/wallets/does-not-exist-abc123")
        assert response.status_code == 404


class TestPortalSavedServicesContract:
    def test_list_saved_services_empty_wallet(self):
        client = _make_client()
        create_resp = client.post("/wallets", json={"owner_did": "did:key:test-portal"})
        assert create_resp.status_code == 200
        wallet_id = create_resp.json()["wallet_id"]

        resp = client.get(f"/wallets/{wallet_id}/portal/saved-services")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_create_saved_service(self):
        client = _make_client()
        create_resp = client.post("/wallets", json={"owner_did": "did:key:test-portal"})
        assert create_resp.status_code == 200
        wallet_id = create_resp.json()["wallet_id"]

        payload = {
            "actor_did": "did:key:test-portal",
            "service_doc_id": "svc-001",
            "source_content_cid": "bafybeigdyrzt5sfp7udm7hu76uh7y26nf3efuylqabf3oclgtqy55fbzdi",
            "title": "Portland Housing Help",
        }
        resp = client.post(f"/wallets/{wallet_id}/portal/saved-services", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "saved_service_id" in data

    def test_list_saved_services_after_create(self):
        client = _make_client()
        create_resp = client.post("/wallets", json={"owner_did": "did:key:test-list"})
        wallet_id = create_resp.json()["wallet_id"]

        client.post(
            f"/wallets/{wallet_id}/portal/saved-services",
            json={
                "actor_did": "did:key:test-list",
                "service_doc_id": "svc-002",
                "source_content_cid": "bafybeigdyrzt5sfp7udm7hu76uh7y26nf3efuylqabf3oclgtqy55fbzdi",
                "title": "Food Bank",
            },
        )
        resp = client.get(f"/wallets/{wallet_id}/portal/saved-services")
        assert resp.status_code == 200
        services = resp.json()
        assert len(services) >= 1
        ids = [s["saved_service_id"] for s in services]
        assert len(set(ids)) == len(ids)


class TestPortalServicePlansContract:
    def test_list_plans_empty_wallet(self):
        client = _make_client()
        create_resp = client.post("/wallets", json={"owner_did": "did:key:test-plans"})
        wallet_id = create_resp.json()["wallet_id"]

        resp = client.get(f"/wallets/{wallet_id}/portal/plans")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_create_plan(self):
        client = _make_client()
        create_resp = client.post("/wallets", json={"owner_did": "did:key:test-plans2"})
        wallet_id = create_resp.json()["wallet_id"]

        payload = {
            "actor_did": "did:key:test-plans2",
            "service_doc_id": "svc-001",
            "source_content_cid": "bafybeigdyrzt5sfp7udm7hu76uh7y26nf3efuylqabf3oclgtqy55fbzdi",
            "service_title": "Housing Assistance",
            "goal": "Find stable housing",
        }
        resp = client.post(f"/wallets/{wallet_id}/portal/plans", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "plan_id" in data


class TestPortalInteractionsContract:
    def test_list_interactions_empty_wallet(self):
        client = _make_client()
        create_resp = client.post("/wallets", json={"owner_did": "did:key:test-interactions"})
        wallet_id = create_resp.json()["wallet_id"]

        resp = client.get(f"/wallets/{wallet_id}/portal/interactions")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_create_interaction(self):
        client = _make_client()
        create_resp = client.post("/wallets", json={"owner_did": "did:key:test-int2"})
        wallet_id = create_resp.json()["wallet_id"]

        payload = {
            "actor_did": "did:key:test-int2",
            "service_doc_id": "svc-001",
            "source_content_cid": "bafybeigdyrzt5sfp7udm7hu76uh7y26nf3efuylqabf3oclgtqy55fbzdi",
            "interaction_type": "phone_call",
            "channel": "phone",
            "outcome": "Scheduled appointment",
        }
        resp = client.post(f"/wallets/{wallet_id}/portal/interactions", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "interaction_id" in data


class TestWalletSnapshotContract:
    def test_get_snapshot_returns_200(self):
        client = _make_client()
        create_resp = client.post("/wallets", json={"owner_did": "did:key:test-snap"})
        wallet_id = create_resp.json()["wallet_id"]

        resp = client.get(f"/wallets/{wallet_id}/snapshot")
        assert resp.status_code == 200

    def test_snapshot_nonexistent_wallet_returns_404(self):
        client = _make_client()
        resp = client.get("/wallets/nonexistent-snap-abc123/snapshot")
        assert resp.status_code == 404
