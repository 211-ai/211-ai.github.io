from __future__ import annotations

from fastapi.testclient import TestClient

from ipfs_datasets_py.wallet.crypto import random_key
from ipfs_datasets_py.wallet.ucan import resource_for_record
from wallet_interface import ServiceRecord, WalletInterfaceService, create_app


def _client() -> TestClient:
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


def test_wallet_api_private_analytics_flow() -> None:
    client = _client()
    wallet_ids = []
    for owner in ["did:key:owner1", "did:key:owner2"]:
        response = client.post("/wallets", json={"owner_did": owner})
        assert response.status_code == 200
        wallet_ids.append(response.json()["wallet_id"])

    response = client.post(
        "/analytics/templates",
        json={
            "template_id": "api_housing_gap_v1",
            "title": "Housing service gaps",
            "purpose": "County-level planning",
            "allowed_record_types": ["location", "need"],
            "allowed_derived_fields": ["county", "need_category"],
            "min_cohort_size": 2,
            "epsilon_budget": 0.5,
            "created_by": "did:key:analyst",
        },
    )
    assert response.status_code == 200

    consent_ids = []
    for wallet_id, owner in zip(wallet_ids, ["did:key:owner1", "did:key:owner2"]):
        response = client.post(
            f"/wallets/{wallet_id}/analytics/consents/from-template",
            json={"actor_did": owner, "template_id": "api_housing_gap_v1"},
        )
        assert response.status_code == 200
        consent_ids.append(response.json()["consent_id"])

    for wallet_id, owner, consent_id in zip(wallet_ids, ["did:key:owner1", "did:key:owner2"], consent_ids):
        response = client.post(
            f"/wallets/{wallet_id}/analytics/contributions",
            json={
                "actor_did": owner,
                "consent_id": consent_id,
                "template_id": "api_housing_gap_v1",
                "fields": {"county": "Multnomah", "need_category": "housing"},
            },
        )
        assert response.status_code == 200

    response = client.post("/analytics/api_housing_gap_v1/count", json={"epsilon": 0.25})
    assert response.status_code == 200
    result = response.json()
    assert result["released"] is True
    assert result["count"] is None
    assert result["noisy_count"] is not None
    assert result["privacy_budget_spent"] == 0.25


def test_wallet_api_matches_services_from_wallet_location_and_audit() -> None:
    client = _client()
    wallet = client.post("/wallets", json={"owner_did": "did:key:owner"}).json()
    response = client.post(
        f"/wallets/{wallet['wallet_id']}/locations",
        json={"actor_did": "did:key:owner", "lat": 45.515232, "lon": -122.678385},
    )
    assert response.status_code == 200
    location = response.json()
    assert location["data_type"] == "location"

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/services/match",
        json={
            "location_record_id": location["record_id"],
            "actor_did": "did:key:owner",
            "need_terms": ["housing"],
        },
    )
    assert response.status_code == 200
    matches = response.json()["matches"]
    assert matches[0]["service"]["id"] == "housing-1"
    assert "matches need:housing" in matches[0]["reasons"]

    response = client.get(f"/wallets/{wallet['wallet_id']}/audit")
    assert response.status_code == 200
    actions = [event["action"] for event in response.json()["events"]]
    assert "location/read_coarse" in actions


def test_wallet_api_delegate_matches_services_with_coarse_location_invocation() -> None:
    client = _client()
    delegate_key = random_key().hex()
    wallet = client.post("/wallets", json={"owner_did": "did:key:owner"}).json()
    location = client.post(
        f"/wallets/{wallet['wallet_id']}/locations",
        json={"actor_did": "did:key:owner", "lat": 45.515232, "lon": -122.678385},
    ).json()

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/locations/{location['record_id']}/coarse-grants",
        json={
            "issuer_did": "did:key:owner",
            "audience_did": "did:key:delegate",
            "audience_key_hex": delegate_key,
        },
    )
    assert response.status_code == 200
    grant = response.json()

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/locations/{location['record_id']}/coarse-invocations",
        json={
            "grant_id": grant["grant_id"],
            "actor_did": "did:key:delegate",
            "actor_key_hex": delegate_key,
        },
    )
    assert response.status_code == 200
    token = response.json()["token"]

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/services/match",
        json={
            "location_record_id": location["record_id"],
            "actor_did": "did:key:delegate",
            "actor_key_hex": delegate_key,
            "invocation_token": token,
            "need_terms": ["housing"],
        },
    )
    assert response.status_code == 200
    assert response.json()["matches"][0]["service"]["id"] == "housing-1"

    actions = [event["action"] for event in client.get(f"/wallets/{wallet['wallet_id']}/audit").json()["events"]]
    assert "invocation/issue" in actions
    assert "invocation/verify" in actions
    assert "location/read_coarse" in actions


def test_wallet_api_delegate_creates_location_region_proof() -> None:
    client = _client()
    wallet = client.post("/wallets", json={"owner_did": "did:key:owner"}).json()
    location = client.post(
        f"/wallets/{wallet['wallet_id']}/locations",
        json={"actor_did": "did:key:owner", "lat": 45.515232, "lon": -122.678385},
    ).json()

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/locations/{location['record_id']}/region-proof-grants",
        json={
            "issuer_did": "did:key:owner",
            "audience_did": "did:key:delegate",
        },
    )
    assert response.status_code == 200
    grant = response.json()

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/locations/{location['record_id']}/region-proofs",
        json={
            "actor_did": "did:key:delegate",
            "grant_id": grant["grant_id"],
            "region_id": "multnomah_county",
        },
    )
    assert response.status_code == 200
    proof = response.json()
    assert proof["proof_type"] == "location_region"
    assert proof["is_simulated"] is True
    assert proof["public_inputs"] == {"region_id": "multnomah_county", "claim": "location_in_region"}
    assert "lat" not in str(proof["public_inputs"]).lower()
    assert "lon" not in str(proof["public_inputs"]).lower()

    actions = [event["action"] for event in client.get(f"/wallets/{wallet['wallet_id']}/audit").json()["events"]]
    assert "proof/create" in actions

    response = client.get(f"/wallets/{wallet['wallet_id']}/proofs")
    assert response.status_code == 200
    proofs = response.json()["proofs"]
    assert [item["proof_id"] for item in proofs] == [proof["proof_id"]]
    assert proofs[0]["public_inputs"] == proof["public_inputs"]
    assert proofs[0]["witness_record_ids"] == [location["record_id"]]


def test_wallet_api_document_analysis_invocation_flow() -> None:
    client = _client()
    owner_key = random_key().hex()
    delegate_key = random_key().hex()
    wallet = client.post("/wallets", json={"owner_did": "did:key:owner"}).json()

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/documents/text",
        json={
            "actor_did": "did:key:owner",
            "key_hex": owner_key,
            "filename": "benefits.txt",
            "title": "Benefits letter",
            "text": "SNAP approval letter and utility shutoff risk.",
        },
    )
    assert response.status_code == 200
    record = response.json()

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/records/{record['record_id']}/analysis-grants",
        json={
            "issuer_did": "did:key:owner",
            "audience_did": "did:key:delegate",
            "issuer_key_hex": owner_key,
            "audience_key_hex": delegate_key,
        },
    )
    assert response.status_code == 200
    grant = response.json()

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/records/{record['record_id']}/analysis-invocations",
        json={
            "grant_id": grant["grant_id"],
            "actor_did": "did:key:delegate",
            "actor_key_hex": delegate_key,
        },
    )
    assert response.status_code == 200
    token = response.json()["token"]

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/records/{record['record_id']}/analyze",
        json={
            "actor_did": "did:key:delegate",
            "actor_key_hex": delegate_key,
            "invocation_token": token,
        },
    )
    assert response.status_code == 200
    artifact = response.json()
    assert artifact["artifact_type"] == "summary"
    assert artifact["output_policy"] == "derived_only"

    response = client.get(f"/wallets/{wallet['wallet_id']}/audit")
    actions = [event["action"] for event in response.json()["events"]]
    assert "invocation/issue" in actions
    assert "invocation/verify" in actions
    assert "record/analyze" in actions


def test_wallet_api_access_request_review_flow() -> None:
    client = _client()
    owner_key = random_key().hex()
    delegate_key = random_key().hex()
    wallet = client.post("/wallets", json={"owner_did": "did:key:owner"}).json()
    record = client.post(
        f"/wallets/{wallet['wallet_id']}/documents/text",
        json={
            "actor_did": "did:key:owner",
            "key_hex": owner_key,
            "filename": "case-note.txt",
            "text": "Housing instability and SNAP recertification.",
        },
    ).json()

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/access-requests",
        json={
            "record_id": record["record_id"],
            "requester_did": "did:key:delegate",
            "purpose": "benefits_screening",
        },
    )
    assert response.status_code == 200
    access_request = response.json()
    assert access_request["status"] == "pending"

    response = client.get(f"/wallets/{wallet['wallet_id']}/access-requests")
    assert response.status_code == 200
    assert [item["request_id"] for item in response.json()["requests"]] == [access_request["request_id"]]

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/access-requests/{access_request['request_id']}/approve",
        json={
            "actor_did": "did:key:owner",
            "issuer_key_hex": owner_key,
            "audience_key_hex": delegate_key,
            "issue_invocation": True,
        },
    )
    assert response.status_code == 200
    approved = response.json()
    assert approved["status"] == "approved"
    assert approved["grant_id"].startswith("grant-")
    assert approved["invocation_token"].startswith("wallet-ucan-v1.")

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/records/{record['record_id']}/analyze",
        json={
            "actor_did": "did:key:delegate",
            "actor_key_hex": delegate_key,
            "invocation_token": approved["invocation_token"],
        },
    )
    assert response.status_code == 200
    assert response.json()["artifact_type"] == "summary"


def test_wallet_api_access_request_can_delegate_document_view() -> None:
    client = _client()
    owner_key = random_key().hex()
    delegate_key = random_key().hex()
    wallet = client.post("/wallets", json={"owner_did": "did:key:owner"}).json()
    record = client.post(
        f"/wallets/{wallet['wallet_id']}/documents/text",
        json={
            "actor_did": "did:key:owner",
            "key_hex": owner_key,
            "filename": "identity.txt",
            "text": "Delegate may view this identity document.",
        },
    ).json()

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/access-requests",
        json={
            "record_id": record["record_id"],
            "requester_did": "did:key:delegate",
            "ability": "record/decrypt",
            "purpose": "identity_verification",
        },
    )
    assert response.status_code == 200
    access_request = response.json()
    assert access_request["abilities"] == ["record/decrypt"]

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/access-requests/{access_request['request_id']}/approve",
        json={
            "actor_did": "did:key:owner",
            "issuer_key_hex": owner_key,
            "audience_key_hex": delegate_key,
            "issue_invocation": True,
        },
    )
    assert response.status_code == 200
    approved = response.json()
    assert approved["invocation_token"].startswith("wallet-ucan-v1.")

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/records/{record['record_id']}/decrypt",
        json={
            "actor_did": "did:key:delegate",
            "actor_key_hex": delegate_key,
            "invocation_token": approved["invocation_token"],
        },
    )
    assert response.status_code == 200
    decrypted = response.json()
    assert decrypted["text"] == "Delegate may view this identity document."
    assert decrypted["size_bytes"] == len("Delegate may view this identity document.")


def test_wallet_api_decrypt_access_request_respects_threshold_approval() -> None:
    client = _client()
    owner_key = random_key().hex()
    delegate_key = random_key().hex()
    wallet = client.post(
        "/wallets",
        json={
            "owner_did": "did:key:owner",
            "controller_dids": ["did:key:owner", "did:key:second-controller"],
            "approval_threshold": 2,
        },
    ).json()
    record = client.post(
        f"/wallets/{wallet['wallet_id']}/documents/text",
        json={
            "actor_did": "did:key:owner",
            "key_hex": owner_key,
            "filename": "threshold-identity.txt",
            "text": "Threshold protected identity document.",
        },
    ).json()

    access_request = client.post(
        f"/wallets/{wallet['wallet_id']}/access-requests",
        json={
            "record_id": record["record_id"],
            "requester_did": "did:key:delegate",
            "ability": "record/decrypt",
            "purpose": "identity_verification",
        },
    ).json()
    response = client.post(
        f"/wallets/{wallet['wallet_id']}/access-requests/{access_request['request_id']}/approve",
        json={
            "actor_did": "did:key:owner",
            "issuer_key_hex": owner_key,
            "audience_key_hex": delegate_key,
        },
    )
    assert response.status_code == 400
    assert "approval_id is required" in response.json()["detail"]

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/approvals",
        json={
            "requested_by": "did:key:owner",
            "operation": "grant/create",
            "resources": [resource_for_record(wallet["wallet_id"], record["record_id"])],
            "abilities": ["record/decrypt"],
        },
    )
    assert response.status_code == 200
    approval = response.json()
    assert approval["threshold"] == 2

    for approver in ["did:key:owner", "did:key:second-controller"]:
        response = client.post(
            f"/wallets/{wallet['wallet_id']}/approvals/{approval['approval_id']}/approve",
            json={"approver_did": approver},
        )
        assert response.status_code == 200
        approval_status = response.json()["status"]
    assert approval_status == "approved"

    response = client.get(f"/wallets/{wallet['wallet_id']}/approvals?status=approved")
    assert response.status_code == 200
    assert response.json()["approvals"][0]["approval_id"] == approval["approval_id"]

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/access-requests/{access_request['request_id']}/approve",
        json={
            "actor_did": "did:key:owner",
            "issuer_key_hex": owner_key,
            "audience_key_hex": delegate_key,
            "approval_id": approval["approval_id"],
            "issue_invocation": True,
        },
    )
    assert response.status_code == 200
    approved_access = response.json()
    assert approved_access["status"] == "approved"
    assert approved_access["invocation_token"].startswith("wallet-ucan-v1.")


def test_wallet_api_storage_health_and_repair() -> None:
    client = _client()
    wallet = client.post("/wallets", json={"owner_did": "did:key:owner"}).json()
    response = client.post(
        f"/wallets/{wallet['wallet_id']}/documents/text",
        json={
            "actor_did": "did:key:owner",
            "filename": "storage.txt",
            "text": "storage health document",
        },
    )
    assert response.status_code == 200
    record = response.json()

    response = client.get(f"/wallets/{wallet['wallet_id']}/records/{record['record_id']}/storage")
    assert response.status_code == 200
    report = response.json()
    assert report["ok"] is True
    assert report["payload"][0]["role"] == "primary"

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/records/{record['record_id']}/storage/repair",
        json={"actor_did": "did:key:owner"},
    )
    assert response.status_code == 200
    repair = response.json()
    assert repair["ok"] is True

    response = client.get(f"/wallets/{wallet['wallet_id']}/audit")
    actions = [event["action"] for event in response.json()["events"]]
    assert "storage/repair" in actions


def test_wallet_api_rejects_precise_analytics_fields() -> None:
    client = _client()
    wallet = client.post("/wallets", json={"owner_did": "did:key:owner"}).json()
    client.post(
        "/analytics/templates",
        json={
            "template_id": "api_unsafe_location_v1",
            "title": "Unsafe location",
            "purpose": "Should reject precise fields",
            "allowed_record_types": ["location"],
            "allowed_derived_fields": ["lat"],
            "min_cohort_size": 2,
            "epsilon_budget": 0.5,
            "created_by": "did:key:analyst",
        },
    )
    consent = client.post(
        f"/wallets/{wallet['wallet_id']}/analytics/consents/from-template",
        json={"actor_did": "did:key:owner", "template_id": "api_unsafe_location_v1"},
    ).json()

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/analytics/contributions",
        json={
            "actor_did": "did:key:owner",
            "consent_id": consent["consent_id"],
            "template_id": "api_unsafe_location_v1",
            "fields": {"lat": 45.515232},
        },
    )
    assert response.status_code == 422


def test_wallet_api_service_matching_rejects_precise_location() -> None:
    client = _client()
    response = client.post(
        "/services/match-derived",
        json={
            "need_terms": ["housing"],
            "location_claim": {"public_value": {"lat": 45.515232, "lon": -122.678385}, "precision": "precise"},
        },
    )
    assert response.status_code == 422
