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


class TestRecordGrantRevokeContract:
    """Record grant/revoke lifecycle contract."""

    def _create_wallet_with_record(self, client):
        create_resp = client.post("/wallets", json={"owner_did": "did:key:grant-owner"})
        assert create_resp.status_code == 200
        wallet_id = create_resp.json()["wallet_id"]

        doc_resp = client.post(
            f"/wallets/{wallet_id}/documents/text",
            json={
                "actor_did": "did:key:grant-owner",
                "text": "I need help with housing in Portland.",
                "filename": "intake.txt",
            },
        )
        assert doc_resp.status_code == 200
        record_id = doc_resp.json()["record_id"]
        return wallet_id, record_id

    def test_create_record_grant_returns_grant_id(self):
        client = _make_client()
        wallet_id, record_id = self._create_wallet_with_record(client)

        resp = client.post(
            f"/wallets/{wallet_id}/records/{record_id}/grants",
            json={
                "issuer_did": "did:key:grant-owner",
                "audience_did": "did:key:grant-audience",
                "abilities": ["record/analyze"],
                "purpose": "service_matching",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "grant_id" in data

    def test_revoke_record_grant(self):
        client = _make_client()
        wallet_id, record_id = self._create_wallet_with_record(client)

        grant_resp = client.post(
            f"/wallets/{wallet_id}/records/{record_id}/grants",
            json={
                "issuer_did": "did:key:grant-owner",
                "audience_did": "did:key:grant-audience",
                "abilities": ["record/analyze"],
            },
        )
        assert grant_resp.status_code == 200
        grant_id = grant_resp.json()["grant_id"]

        revoke_resp = client.post(
            f"/wallets/{wallet_id}/grants/{grant_id}/revoke",
            json={"actor_did": "did:key:grant-owner"},
        )
        assert revoke_resp.status_code == 200

    def test_grant_receipt_list_includes_issued_grant(self):
        client = _make_client()
        wallet_id, record_id = self._create_wallet_with_record(client)

        client.post(
            f"/wallets/{wallet_id}/records/{record_id}/grants",
            json={
                "issuer_did": "did:key:grant-owner",
                "audience_did": "did:key:grant-audience",
                "abilities": ["record/analyze"],
            },
        )

        receipts_resp = client.get(f"/wallets/{wallet_id}/grant-receipts")
        assert receipts_resp.status_code == 200
        receipts = receipts_resp.json()
        assert isinstance(receipts, list)
        assert len(receipts) >= 1

    def test_grant_requires_record_in_wallet(self):
        client = _make_client()
        create_resp = client.post("/wallets", json={"owner_did": "did:key:no-record-owner"})
        wallet_id = create_resp.json()["wallet_id"]

        resp = client.post(
            f"/wallets/{wallet_id}/records/nonexistent-record-id/grants",
            json={
                "issuer_did": "did:key:no-record-owner",
                "audience_did": "did:key:grant-audience",
                "abilities": ["record/analyze"],
            },
        )
        assert resp.status_code in (400, 404)


class TestExportBundleContract:
    """Export bundle create / verify / import round-trip contract."""

    def _wallet_with_record(self, client):
        wallet_resp = client.post("/wallets", json={"owner_did": "did:key:export-owner"})
        wallet_id = wallet_resp.json()["wallet_id"]
        doc_resp = client.post(
            f"/wallets/{wallet_id}/documents/text",
            json={
                "actor_did": "did:key:export-owner",
                "text": "Shelter inquiry for downtown Portland.",
                "filename": "shelter.txt",
            },
        )
        record_id = doc_resp.json()["record_id"]
        return wallet_id, record_id

    def test_create_export_grant_returns_grant_id(self):
        client = _make_client()
        wallet_id, record_id = self._wallet_with_record(client)

        resp = client.post(
            f"/wallets/{wallet_id}/exports/grants",
            json={
                "issuer_did": "did:key:export-owner",
                "audience_did": "did:key:export-audience",
                "record_ids": [record_id],
                "purpose": "user_export",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "grant_id" in data

    def test_create_export_bundle_returns_bundle(self):
        client = _make_client()
        wallet_id, record_id = self._wallet_with_record(client)

        grant_resp = client.post(
            f"/wallets/{wallet_id}/exports/grants",
            json={
                "issuer_did": "did:key:export-owner",
                "audience_did": "did:key:export-audience",
                "record_ids": [record_id],
            },
        )
        grant_id = grant_resp.json()["grant_id"]

        bundle_resp = client.post(
            f"/wallets/{wallet_id}/exports",
            json={
                "actor_did": "did:key:export-owner",
                "grant_id": grant_id,
                "record_ids": [record_id],
                "include_proofs": False,
                "include_derived_artifacts": False,
            },
        )
        assert bundle_resp.status_code == 200
        bundle = bundle_resp.json()
        assert "records" in bundle or "wallet_id" in bundle

    def test_verify_export_bundle(self):
        client = _make_client()
        wallet_id, record_id = self._wallet_with_record(client)

        grant_resp = client.post(
            f"/wallets/{wallet_id}/exports/grants",
            json={
                "issuer_did": "did:key:export-owner",
                "audience_did": "did:key:export-audience",
                "record_ids": [record_id],
            },
        )
        grant_id = grant_resp.json()["grant_id"]

        bundle_resp = client.post(
            f"/wallets/{wallet_id}/exports",
            json={
                "actor_did": "did:key:export-owner",
                "grant_id": grant_id,
                "record_ids": [record_id],
                "include_proofs": False,
                "include_derived_artifacts": False,
            },
        )
        bundle = bundle_resp.json()

        verify_resp = client.post("/exports/verify", json={"bundle": bundle})
        assert verify_resp.status_code == 200

    def test_import_export_bundle(self):
        client = _make_client()
        wallet_id, record_id = self._wallet_with_record(client)

        grant_resp = client.post(
            f"/wallets/{wallet_id}/exports/grants",
            json={
                "issuer_did": "did:key:export-owner",
                "audience_did": "did:key:export-audience",
                "record_ids": [record_id],
            },
        )
        grant_id = grant_resp.json()["grant_id"]

        bundle_resp = client.post(
            f"/wallets/{wallet_id}/exports",
            json={
                "actor_did": "did:key:export-owner",
                "grant_id": grant_id,
                "record_ids": [record_id],
                "include_proofs": False,
                "include_derived_artifacts": False,
            },
        )
        bundle = bundle_resp.json()

        import_resp = client.post("/exports/import", json={"bundle": bundle})
        assert import_resp.status_code == 200

    def test_export_grant_requires_record_ids(self):
        client = _make_client()
        wallet_resp = client.post("/wallets", json={"owner_did": "did:key:export-empty"})
        wallet_id = wallet_resp.json()["wallet_id"]

        resp = client.post(
            f"/wallets/{wallet_id}/exports/grants",
            json={
                "issuer_did": "did:key:export-empty",
                "audience_did": "did:key:export-audience",
                "record_ids": [],
            },
        )
        assert resp.status_code == 400


class TestProofGrantContract:
    """Proof grant/invocation contract for location-region proofs."""

    def test_location_region_proof_grant_and_invocation(self):
        client = _make_client()
        wallet_resp = client.post("/wallets", json={"owner_did": "did:key:proof-owner"})
        wallet_id = wallet_resp.json()["wallet_id"]

        loc_resp = client.post(
            f"/wallets/{wallet_id}/locations",
            json={
                "actor_did": "did:key:proof-owner",
                "latitude": 45.5231,
                "longitude": -122.6765,
                "city": "Portland",
                "state": "OR",
                "zip": "97201",
            },
        )
        assert loc_resp.status_code == 200
        location_record_id = loc_resp.json()["record_id"]

        grant_resp = client.post(
            f"/wallets/{wallet_id}/locations/{location_record_id}/region-proof-grants",
            json={
                "issuer_did": "did:key:proof-owner",
                "audience_did": "did:key:proof-audience",
            },
        )
        assert grant_resp.status_code == 200
        assert "grant_id" in grant_resp.json()

        proof_resp = client.post(
            f"/wallets/{wallet_id}/locations/{location_record_id}/region-proofs",
            json={
                "actor_did": "did:key:proof-owner",
                "grant_id": grant_resp.json()["grant_id"],
            },
        )
        assert proof_resp.status_code == 200
        proof = proof_resp.json()
        assert "proof_id" in proof or "region" in proof

    def test_list_wallet_proofs(self):
        client = _make_client()
        wallet_resp = client.post("/wallets", json={"owner_did": "did:key:proof-list"})
        wallet_id = wallet_resp.json()["wallet_id"]

        resp = client.get(f"/wallets/{wallet_id}/proofs")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


class TestHmisReferralDraftContract:
    """HMIS referral draft lifecycle contract."""

    def test_list_referral_drafts_empty_wallet(self):
        client = _make_client()
        wallet_resp = client.post("/wallets", json={"owner_did": "did:key:hmis-owner"})
        wallet_id = wallet_resp.json()["wallet_id"]

        resp = client.get(f"/wallets/{wallet_id}/hmis/referral-drafts")
        assert resp.status_code == 200
        data = resp.json()
        assert "referral_drafts" in data
        assert isinstance(data["referral_drafts"], list)

    def test_create_referral_draft(self):
        client = _make_client()
        wallet_resp = client.post("/wallets", json={"owner_did": "did:key:hmis-create"})
        wallet_id = wallet_resp.json()["wallet_id"]

        resp = client.post(
            f"/wallets/{wallet_id}/hmis/referral-drafts",
            json={
                "actor_did": "did:key:hmis-create",
                "local_subject_ref": "client-local-001",
                "destination_program_ref": "program-001",
                "provider_name": "Portland Housing Authority",
                "program_name": "Emergency Shelter Placement",
                "summary": "Client needs emergency shelter tonight.",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "referral_draft_id" in data

    def test_update_referral_draft(self):
        client = _make_client()
        wallet_resp = client.post("/wallets", json={"owner_did": "did:key:hmis-update"})
        wallet_id = wallet_resp.json()["wallet_id"]

        create_resp = client.post(
            f"/wallets/{wallet_id}/hmis/referral-drafts",
            json={
                "actor_did": "did:key:hmis-update",
                "local_subject_ref": "client-local-002",
                "destination_program_ref": "program-002",
                "summary": "Initial summary.",
            },
        )
        assert create_resp.status_code == 200
        draft_id = create_resp.json()["referral_draft_id"]

        patch_resp = client.patch(
            f"/wallets/{wallet_id}/hmis/referral-drafts/{draft_id}",
            json={
                "actor_did": "did:key:hmis-update",
                "local_subject_ref": "client-local-002",
                "destination_program_ref": "program-002",
                "summary": "Updated with intake notes.",
            },
        )
        assert patch_resp.status_code == 200

    def test_list_drafts_after_create_includes_new_draft(self):
        client = _make_client()
        wallet_resp = client.post("/wallets", json={"owner_did": "did:key:hmis-list"})
        wallet_id = wallet_resp.json()["wallet_id"]

        client.post(
            f"/wallets/{wallet_id}/hmis/referral-drafts",
            json={
                "actor_did": "did:key:hmis-list",
                "local_subject_ref": "client-local-003",
                "destination_program_ref": "program-003",
            },
        )

        list_resp = client.get(f"/wallets/{wallet_id}/hmis/referral-drafts")
        assert list_resp.status_code == 200
        drafts = list_resp.json()["referral_drafts"]
        assert len(drafts) >= 1

    def test_validate_referral_draft(self):
        client = _make_client()
        wallet_resp = client.post("/wallets", json={"owner_did": "did:key:hmis-validate"})
        wallet_id = wallet_resp.json()["wallet_id"]

        create_resp = client.post(
            f"/wallets/{wallet_id}/hmis/referral-drafts",
            json={
                "actor_did": "did:key:hmis-validate",
                "local_subject_ref": "client-local-004",
                "destination_program_ref": "program-004",
                "summary": "Needs food pantry access.",
            },
        )
        draft_id = create_resp.json()["referral_draft_id"]

        validate_resp = client.post(
            f"/wallets/{wallet_id}/hmis/referral-drafts/{draft_id}/validate",
            json={"actor_did": "did:key:hmis-validate"},
        )
        assert validate_resp.status_code == 200
