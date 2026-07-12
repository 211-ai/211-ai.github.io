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


def _make_client() -> "TestClient":
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
