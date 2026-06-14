from __future__ import annotations

import base64
import hashlib
import io
import json
import zipfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from ipfs_datasets_py.wallet import DeterministicLocationRegionProofBackend, ProofReceipt
from wallet_interface import ServiceRecord, WalletInterfaceService, create_app
from wallet_interface.app_service import phone_identity_cid
import wallet_interface.api as wallet_api_module
from ipfs_datasets_py.wallet.crypto import random_key
from ipfs_datasets_py.wallet.proofs import verifier_digest
from ipfs_datasets_py.wallet.ucan import resource_for_export, resource_for_record, resource_for_wallet


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


def _client_with_service(service: WalletInterfaceService) -> TestClient:
    return TestClient(create_app(service=service))


PROVEKIT_PRIVATE_WITNESS_SENTINEL = "PRIVATE_WITNESS_SENTINEL_TDFOL_AXIOM_DO_NOT_RENDER"
PROVEKIT_FORBIDDEN_PUBLIC_TOKENS = (
    PROVEKIT_PRIVATE_WITNESS_SENTINEL,
    "private_axiom_text",
    "Prover.toml",
    "witness_theorem_hash_field",
    "prover_key_path",
    "pkp_path",
    "45.515232",
    "-122.678385",
)


def _provekit_public_inputs() -> dict[str, Any]:
    return {
        "theorem": "eligible_for_housing_support(abby)",
        "theorem_hash": "1" * 64,
        "axioms_commitment": "2" * 64,
        "circuit_ref": "provekit_knowledge_of_axioms@v1",
        "circuit_version": 1,
        "ruleset_id": "TDFOL_v1",
        "compiler_guidance_ref": "a" * 64,
        "compiler_guidance_version": 1,
        "attestation_ref": "3" * 64,
        "attestation_view_version": 1,
    }


def _provekit_metadata(cache_status: str = "miss", **overrides: Any) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "backend": "provekit",
        "proof_system": "ProveKit-WHIR",
        "provekit_branch": "v1",
        "provekit_commit": "provekit-v1-fixture-commit",
        "hash_backend": "sha256",
        "pkp_sha256": "5" * 64,
        "pkv_sha256": "4" * 64,
        "noir_package_hash": "6" * 64,
        "artifact_manifest_sha256": "6" * 64,
        "cache_status": cache_status,
        "public_artifact_refs": {
            "proof": "ipfs://bafyprovekitwhirfixture/proof.np",
            "verifier_key": "ipfs://bafyprovekitwhirfixture/verification-key.pkv",
            "manifest": "ipfs://bafyprovekitwhirfixture/provekit-artifacts.json",
        },
    }
    metadata.update(overrides)
    return metadata


class _ProveKitWalletProofBackend:
    mode = "production"
    verifier_id = "provekit-whir-eligibility-v1"
    proof_system = "ProveKit-WHIR"
    circuit_id = "provekit_knowledge_of_axioms@v1"

    def __init__(
        self,
        *,
        cache_status: str = "miss",
        error: str | None = None,
        is_simulated: bool = False,
        metadata_overrides: dict[str, Any] | None = None,
        proof_system: str | None = None,
        verification_status: str = "verified",
        verify_result: bool = True,
    ) -> None:
        self.cache_status = cache_status
        self.error = error
        self.is_simulated = is_simulated
        self.metadata_overrides = dict(metadata_overrides or {})
        self.proof_system = proof_system or self.proof_system
        self.verification_status = verification_status
        self.verify_result = verify_result
        self.private_axiom = PROVEKIT_PRIVATE_WITNESS_SENTINEL

    def prove_location_region(
        self,
        *,
        wallet_id: str,
        statement: dict[str, Any],
        public_inputs: dict[str, Any],
        witness: dict[str, Any],
        witness_record_ids: list[str],
    ) -> ProofReceipt:
        if self.error:
            raise RuntimeError(self.error)
        assert witness["lat"] == 45.515232
        assert witness["lon"] == -122.678385
        digest = verifier_digest(self.verifier_id, self.proof_system)
        provekit_inputs = _provekit_public_inputs()
        proof_hash = hashlib.sha256(
            json.dumps(
                {
                    "proof_system": self.proof_system,
                    "public_inputs": provekit_inputs,
                    "statement": statement,
                    "verifier_digest": digest,
                },
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()
        return ProofReceipt(
            proof_id=f"proof-provekit-{self.cache_status}-{self.verification_status}",
            wallet_id=wallet_id,
            proof_type="provider_eligibility",
            statement={
                "claim": "eligible_for_housing_support",
                "circuit_ref": "provekit_knowledge_of_axioms@v1",
            },
            verifier_id=self.verifier_id,
            public_inputs=provekit_inputs,
            proof_hash=proof_hash,
            witness_record_ids=list(witness_record_ids),
            is_simulated=self.is_simulated,
            proof_system=self.proof_system,
            circuit_id=self.circuit_id,
            verifier_digest=digest,
            proof_artifact_ref="ipfs://bafyprovekitwhirfixture/proof.np",
            verification_status=self.verification_status,
            metadata=_provekit_metadata(self.cache_status, **self.metadata_overrides),
        )

    def prove_location_distance(self, **_: Any) -> ProofReceipt:
        raise NotImplementedError("ProveKit wallet fixture only supports location_region")

    def verify(self, receipt: ProofReceipt) -> bool:
        return self.verify_result and receipt.verification_status == "verified"


def _assert_no_provekit_private_leak(payload: Any) -> None:
    serialized = json.dumps(payload, sort_keys=True)
    for token in PROVEKIT_FORBIDDEN_PUBLIC_TOKENS:
        assert token not in serialized


def _create_wallet_location(client: TestClient) -> tuple[dict[str, Any], dict[str, Any]]:
    wallet = client.post("/wallets", json={"owner_did": "did:key:owner"}).json()
    location = client.post(
        f"/wallets/{wallet['wallet_id']}/locations",
        json={"actor_did": "did:key:owner", "lat": 45.515232, "lon": -122.678385},
    ).json()
    return wallet, location


def test_wallet_api_cors_allows_configured_browser_origin(monkeypatch) -> None:
    origin = "http://127.0.0.1:5185"
    monkeypatch.setenv("WALLET_API_CORS_ORIGINS", origin)
    client = _client()

    response = client.options(
        "/wallets",
        headers={
            "Access-Control-Request-Headers": "content-type",
            "Access-Control-Request-Method": "POST",
            "Origin": origin,
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin


def test_magic_login_request_sends_signed_sms_and_verify_connects_wallet(monkeypatch) -> None:
    monkeypatch.setenv("WALLET_MAGIC_LOGIN_SECRET", "test-magic-login-secret")
    deliveries: list[dict[str, object]] = []

    def fake_sms_delivery(**kwargs):
        deliveries.append(kwargs)
        return {"provider": "mock", "provider_status": "queued", "provider_message_id": "SM-login"}

    monkeypatch.setattr(wallet_api_module, "_send_sms_notification", fake_sms_delivery)
    client = _client()

    response = client.post(
        "/auth/magic-link/request",
        json={
            "contact": "(503) 555-0199",
            "portal": "client",
            "wallet_id": "wallet-abc",
            "wallet_api_base_url": "https://211-ai.com",
            "actor_did": "did:key:abby-test",
            "base_url": "https://211-ai.com/",
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["channel"] == "sms"
    assert deliveries
    message = str(deliveries[0]["message"])
    assert "211 AI / Abby login" in message
    token = message.split("abbyLogin=", 1)[1].split("#", 1)[0]

    verify_response = client.post("/auth/magic-link/verify", json={"token": token})
    assert verify_response.status_code == 200, verify_response.text
    body = verify_response.json()
    assert body["valid"] is True
    assert body["contact"] == "5035550199"
    assert body["wallet_config"] == {
        "apiBaseUrl": "https://211-ai.com",
        "walletId": "wallet-abc",
        "actorDid": "did:key:abby-test",
    }
    assert body["ucan"]["profile"] == "abby-magic-ucan-v1"
    assert body["ucan"]["token"].startswith("abby-magic-ucan-v1.")
    assert {"with": "wallet://wallet-abc", "can": "wallet/recovery/start"} in body["ucan"]["capabilities"]
    assert {"with": "wallet://wallet-abc/recovery-bundles/*", "can": "wallet/recovery/read_encrypted"} in body[
        "ucan"
    ]["capabilities"]
    assert body["ucan"]["caveats"]["server_can_decrypt"] is False
    assert body["ucan"]["caveats"]["no_plaintext_key_access"] is True
    assert deliveries[0]["metadata"]["message_type"] == "magic_login"
    assert deliveries[0]["metadata"]["portal"] == "client"
    assert deliveries[0]["metadata"]["wallet_id"] == "wallet-abc"
    assert deliveries[0]["metadata"]["nonce"]
    assert "test-magic-login-secret" not in message


def test_magic_ucan_reads_encrypted_recovery_bundle_without_plaintext_key(monkeypatch) -> None:
    monkeypatch.setenv("WALLET_MAGIC_LOGIN_SECRET", "test-magic-login-secret")
    deliveries: list[dict[str, object]] = []

    def fake_sms_delivery(**kwargs):
        deliveries.append(kwargs)
        return {"provider": "mock", "provider_status": "queued"}

    monkeypatch.setattr(wallet_api_module, "_send_sms_notification", fake_sms_delivery)
    client = _client()
    wallet = client.post("/wallets", json={"owner_did": "did:key:owner"}).json()
    wallet_id = wallet["wallet_id"]

    store_response = client.post(
        f"/wallets/{wallet_id}/recovery-bundles",
        json={
            "actor_did": "did:key:owner",
            "encrypted_bundle": {
                "schema": "211-ai-wallet-recovery-bundle-v1",
                "ciphertext": "encrypted-only",
                "plaintextKeySentToServer": False,
            },
            "wrapping_method": "device-local-key",
            "public_metadata": {"serverCanDecrypt": False},
        },
    )
    assert store_response.status_code == 200, store_response.text
    assert store_response.json()["privacy"]["server_can_decrypt"] is False

    request_response = client.post(
        "/auth/magic-link/request",
        json={
            "contact": "(503) 555-0199",
            "portal": "client",
            "wallet_id": wallet_id,
            "wallet_api_base_url": "https://211-ai.com",
            "actor_did": "did:key:owner",
            "base_url": "https://211-ai.com/",
        },
    )
    assert request_response.status_code == 200, request_response.text
    token = str(deliveries[0]["message"]).split("abbyLogin=", 1)[1].split("#", 1)[0]
    verify_response = client.post("/auth/magic-link/verify", json={"token": token})
    assert verify_response.status_code == 200, verify_response.text
    ucan_token = verify_response.json()["ucan"]["token"]

    bundle_response = client.get(
        f"/wallets/{wallet_id}/recovery-bundles/latest",
        headers={"authorization": f"Bearer {ucan_token}"},
    )
    assert bundle_response.status_code == 200, bundle_response.text
    payload = bundle_response.json()
    assert payload["privacy"]["server_can_decrypt"] is False
    assert payload["privacy"]["plaintext_wallet_key_returned"] is False
    assert payload["bundle"]["encrypted_bundle"]["ciphertext"] == "encrypted-only"
    assert "walletContentKey" not in json.dumps(payload)

    bundle_id = payload["bundle"]["bundle_id"]
    qr_scoped_response = client.get(
        f"/wallets/{wallet_id}/recovery-bundles/{bundle_id}",
        headers={"authorization": f"Bearer {ucan_token}"},
    )
    assert qr_scoped_response.status_code == 200, qr_scoped_response.text
    assert qr_scoped_response.json()["bundle"]["bundle_id"] == bundle_id


def test_magic_ucan_recovery_bundle_scope_rejects_missing_invalid_and_wrong_wallet_tokens(monkeypatch) -> None:
    monkeypatch.setenv("WALLET_MAGIC_LOGIN_SECRET", "test-magic-login-secret")
    deliveries: list[dict[str, object]] = []

    def fake_sms_delivery(**kwargs):
        deliveries.append(kwargs)
        return {"provider": "mock", "provider_status": "queued"}

    monkeypatch.setattr(wallet_api_module, "_send_sms_notification", fake_sms_delivery)
    client = _client()
    wallet = client.post("/wallets", json={"owner_did": "did:key:owner"}).json()
    wallet_id = wallet["wallet_id"]
    store_response = client.post(
        f"/wallets/{wallet_id}/recovery-bundles",
        json={
            "actor_did": "did:key:owner",
            "encrypted_bundle": {"ciphertext": "encrypted-only"},
            "wrapping_method": "passphrase",
            "public_metadata": {"serverCanDecrypt": False},
        },
    )
    assert store_response.status_code == 200, store_response.text

    missing_response = client.get(f"/wallets/{wallet_id}/recovery-bundles/latest")
    assert missing_response.status_code == 401

    invalid_response = client.get(
        f"/wallets/{wallet_id}/recovery-bundles/latest",
        headers={"authorization": "Bearer not-a-real-ucan"},
    )
    assert invalid_response.status_code == 401

    request_response = client.post(
        "/auth/magic-link/request",
        json={
            "contact": "(503) 555-0100",
            "portal": "client",
            "wallet_id": "wallet-other",
            "wallet_api_base_url": "https://211-ai.com",
            "actor_did": "did:key:owner",
            "base_url": "https://211-ai.com/",
        },
    )
    assert request_response.status_code == 200, request_response.text
    token = str(deliveries[0]["message"]).split("abbyLogin=", 1)[1].split("#", 1)[0]
    verify_response = client.post("/auth/magic-link/verify", json={"token": token})
    assert verify_response.status_code == 200, verify_response.text
    wrong_wallet_ucan = verify_response.json()["ucan"]["token"]

    wrong_wallet_response = client.get(
        f"/wallets/{wallet_id}/recovery-bundles/latest",
        headers={"authorization": f"Bearer {wrong_wallet_ucan}"},
    )
    assert wrong_wallet_response.status_code == 403


def test_magic_login_request_sends_signed_email(monkeypatch) -> None:
    monkeypatch.setenv("WALLET_MAGIC_LOGIN_SECRET", "test-magic-login-secret")
    deliveries: list[dict[str, object]] = []

    def fake_email_delivery(**kwargs):
        deliveries.append(kwargs)
        return {"provider": "mock-email", "provider_status": "queued", "provider_message_id": "email-login"}

    monkeypatch.setattr(wallet_api_module, "_send_auth_email_notification", fake_email_delivery)
    client = _client()

    response = client.post(
        "/auth/magic-link/request",
        json={
            "contact": "Abby.User@example.org",
            "portal": "provider",
            "base_url": "https://211-ai.com/",
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["channel"] == "email"
    assert deliveries[0]["to_email"] == "abby.user@example.org"
    body = str(deliveries[0]["body"])
    assert "abbyLogin=" in body
    assert deliveries[0]["metadata"]["message_type"] == "magic_login"
    assert deliveries[0]["metadata"]["portal"] == "provider"
    token = body.split("abbyLogin=", 1)[1].split("#", 1)[0].split("\n", 1)[0]
    verify_response = client.post("/auth/magic-link/verify", json={"token": token})
    assert verify_response.status_code == 200, verify_response.text
    verify_payload = verify_response.json()
    assert verify_payload["contact"] == "abby.user@example.org"
    assert verify_payload["portal"] == "provider"
    assert verify_payload["ucan"]["caveats"]["server_can_decrypt"] is False


def test_filecoin_upload_bridge_backs_up_encrypted_wallet_recovery_artifact_without_secret_material(monkeypatch) -> None:
    client = _client()
    added: list[bytes] = []
    passphrase = "correct horse battery staple"
    plaintext_wallet_key = "plain-wallet-content-key"
    encrypted_recovery_backup = json.dumps(
        {
            "schema": "211-ai-wallet-recovery-backup-v1",
            "walletId": "wallet-backup",
            "bundleId": "bundle-backup",
            "containsPassphrase": False,
            "containsPlaintextWalletKey": False,
            "encryptedBundle": {"ciphertext": "encrypted-wallet-recovery-only"},
            "serverCanDecrypt": False,
        },
        separators=(",", ":"),
    ).encode("utf-8")
    assert passphrase.encode("utf-8") not in encrypted_recovery_backup
    assert plaintext_wallet_key.encode("utf-8") not in encrypted_recovery_backup

    class FakeIpfsBackend:
        def add_bytes(self, data: bytes, *, pin: bool = True) -> str:
            assert pin is True
            added.append(data)
            return "bafy-recovery-backup"

    monkeypatch.setattr(wallet_api_module, "get_ipfs_backend", lambda: FakeIpfsBackend())
    monkeypatch.setenv("WALLET_FILECOIN_PIN_SERVICE_URL", "mock")

    response = client.post(
        "/filecoin-upload",
        data={
            "metadata": json.dumps(
                {
                    "fileName": "wallet-recovery-bundle.json",
                    "mimeType": "application/vnd.211-ai.wallet.recovery+json",
                    "sha256": hashlib.sha256(encrypted_recovery_backup).hexdigest(),
                    "walletId": "wallet-backup",
                }
            )
        },
        files={
            "file": (
                "wallet-recovery-bundle.json",
                encrypted_recovery_backup,
                "application/vnd.211-ai.wallet.recovery+json",
            )
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["ipfsCid"] == "bafy-recovery-backup"
    assert payload["filecoinPinStatus"] == "queued"
    assert payload["statusUrl"].startswith("/filecoin-upload/status/")
    assert added == [encrypted_recovery_backup]
    added_text = added[0].decode("utf-8")
    assert passphrase not in added_text
    assert plaintext_wallet_key not in added_text


def test_filecoin_upload_bridge_accepts_multipart(monkeypatch) -> None:
    client = _client()
    added: list[bytes] = []

    class FakeIpfsBackend:
        def add_bytes(self, data: bytes, *, pin: bool = True) -> str:
            assert pin is True
            added.append(data)
            return "bafy-uploaded-file"

    monkeypatch.setattr(wallet_api_module, "get_ipfs_backend", lambda: FakeIpfsBackend())

    response = client.post(
        "/filecoin-upload",
        data={"metadata": json.dumps({"sha256": hashlib.sha256(b"proof-bundle").hexdigest(), "walletId": "wallet-demo"})},
        files={"file": ("proofs.json", b"proof-bundle", "application/json")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ipfsCid"] == "bafy-uploaded-file"
    assert payload["gatewayUrl"] == "https://w3s.link/ipfs/bafy-uploaded-file"
    assert payload["provider"] == "ipfs-filecoin"
    assert payload["walletId"] == "wallet-demo"
    assert added == [b"proof-bundle"]


def test_filecoin_upload_bridge_can_publish_existing_wallet_record(monkeypatch) -> None:
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
    client = _client_with_service(service)
    wallet = client.post("/wallets", json={"owner_did": "did:key:owner"}).json()
    record = client.post(
        f"/wallets/{wallet['wallet_id']}/documents/text",
        json={"actor_did": "did:key:owner", "text": "Encrypted-but-exportable proof bundle", "filename": "proof.txt"},
    ).json()

    added: list[bytes] = []

    class FakeIpfsBackend:
        def add_bytes(self, data: bytes, *, pin: bool = True) -> str:
            assert pin is True
            added.append(data)
            return "bafy-record-upload"

    monkeypatch.setattr(wallet_api_module, "get_ipfs_backend", lambda: FakeIpfsBackend())

    response = client.post(
        "/filecoin-upload",
        json={
            "actorDid": "did:key:owner",
            "fileName": "proof.txt",
            "recordId": record["record_id"],
            "walletId": wallet["wallet_id"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ipfsCid"] == "bafy-record-upload"
    assert payload["recordId"] == record["record_id"]
    assert payload["walletId"] == wallet["wallet_id"]
    assert added == [b"Encrypted-but-exportable proof bundle"]


def test_filecoin_upload_bridge_can_handoff_to_filecoin_pin_sidecar(monkeypatch) -> None:
    client = _client()
    added: list[bytes] = []
    handoff_request: dict[str, object] = {}

    class FakeIpfsBackend:
        def add_bytes(self, data: bytes, *, pin: bool = True) -> str:
            assert pin is True
            added.append(data)
            return "bafy-uploaded-file"

    class FakeResponse:
        headers = {"content-type": "application/json"}

        def read(self) -> bytes:
            return json.dumps({"requestid": "pin-123", "status": "queued", "info": {"provider": "filecoin-pin"}}).encode(
                "utf-8"
            )

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

    def fake_urlopen(req, timeout: float):
        handoff_request["url"] = req.full_url
        handoff_request["timeout"] = timeout
        handoff_request["headers"] = {key.lower(): value for key, value in req.header_items()}
        handoff_request["body"] = json.loads(req.data.decode("utf-8"))
        return FakeResponse()

    monkeypatch.setattr(wallet_api_module, "get_ipfs_backend", lambda: FakeIpfsBackend())
    monkeypatch.setattr(wallet_api_module.urllib_request, "urlopen", fake_urlopen)
    monkeypatch.setenv("WALLET_FILECOIN_PIN_SERVICE_URL", "http://filecoin-pin:3456")
    monkeypatch.setenv("WALLET_FILECOIN_PIN_BEARER_TOKEN", "sidecar-token")
    monkeypatch.setenv(
        "WALLET_FILECOIN_PIN_ORIGINS",
        "/dns/kubo/tcp/4001/p2p/12D3KooWExample,/dns/kubo-2/tcp/4001/p2p/12D3KooWExampleTwo",
    )
    monkeypatch.setenv("WALLET_FILECOIN_PIN_TIMEOUT_SECONDS", "9")

    response = client.post(
        "/filecoin-upload",
        data={"metadata": json.dumps({"walletId": "wallet-demo"})},
        files={"file": ("proofs.json", b"proof-bundle", "application/json")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ipfsCid"] == "bafy-uploaded-file"
    assert payload["requestId"] == "pin-123"
    assert payload["filecoinPinRequestId"] == "pin-123"
    assert payload["filecoinPinStatus"] == "queued"
    assert payload["statusUrl"] == "/filecoin-upload/status/pin-123"
    assert "queued for Filecoin persistence" in payload["message"]
    assert added == [b"proof-bundle"]
    assert handoff_request["url"] == "http://filecoin-pin:3456/pins"
    assert handoff_request["timeout"] == 9.0
    assert handoff_request["headers"] == {
        "authorization": "Bearer sidecar-token",
        "content-type": "application/json",
    }
    assert handoff_request["body"] == {
        "cid": "bafy-uploaded-file",
        "meta": {
            "fileName": "proofs.json",
            "mimeType": "application/json",
            "source": "211-ai-wallet",
            "walletId": "wallet-demo",
        },
        "name": "proofs.json",
        "origins": [
            "/dns/kubo/tcp/4001/p2p/12D3KooWExample",
            "/dns/kubo-2/tcp/4001/p2p/12D3KooWExampleTwo",
        ],
    }


def test_hmis_client_lookup_returns_fixture_candidates_and_audits() -> None:
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
        ],
        hmis_lookup_fixtures=[
            {
                "entity_type": "client",
                "external_client_id": "hmis-client-001",
                "name": "Alex Johnson",
                "date_of_birth": "1989-02-14",
                "program_ref": "rosehaven-day-center",
                "status": "active",
            },
            {
                "entity_type": "household",
                "external_household_id": "hmis-household-001",
                "household_name": "Johnson Household",
                "program_ref": "rosehaven-day-center",
                "status": "active",
            },
            {
                "entity_type": "program",
                "local_program_ref": "rosehaven-day-center",
                "external_program_id": "hmis-program-rosehaven",
                "external_project_id": "hmis-project-001",
                "program_name": "Rose Haven Day Center",
                "status": "verified",
            }
        ],
    )
    client = _client_with_service(service)
    wallet = client.post("/wallets", json={"owner_did": "did:key:owner"}).json()

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/hmis/lookup-clients",
        json={
            "actor_did": "did:key:owner",
            "name": "alex",
            "date_of_birth": "1989-02-14",
            "program_ref": "rosehaven-day-center",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["adapter_result"]["ok"] is True
    assert payload["adapter_result"]["normalized_payload"]["candidate_count"] == 1
    assert payload["adapter_result"]["normalized_payload"]["candidates"][0]["external_client_id"] == "hmis-client-001"

    audit_response = client.get(f"/wallets/{wallet['wallet_id']}/audit-events")
    assert audit_response.status_code == 200
    actions = [event["action"] for event in audit_response.json()["audit_events"]]
    assert "hmis/lookup_client" in actions


def test_hmis_household_lookup_and_program_links_return_fixture_results() -> None:
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
        ],
        hmis_lookup_fixtures=[
            {
                "entity_type": "household",
                "external_household_id": "hmis-household-001",
                "household_name": "Johnson Household",
                "program_ref": "rosehaven-day-center",
                "status": "active",
            },
            {
                "entity_type": "program",
                "local_program_ref": "rosehaven-day-center",
                "external_program_id": "hmis-program-rosehaven",
                "external_project_id": "hmis-project-001",
                "program_name": "Rose Haven Day Center",
                "status": "verified",
            },
        ],
    )
    client = _client_with_service(service)
    wallet = client.post("/wallets", json={"owner_did": "did:key:owner"}).json()

    household_response = client.post(
        f"/wallets/{wallet['wallet_id']}/hmis/lookup-households",
        json={
            "actor_did": "did:key:owner",
            "name": "johnson",
            "program_ref": "rosehaven-day-center",
        },
    )
    assert household_response.status_code == 200
    household_payload = household_response.json()
    assert household_payload["adapter_result"]["normalized_payload"]["candidate_count"] == 1
    assert (
        household_payload["adapter_result"]["normalized_payload"]["candidates"][0]["external_household_id"]
        == "hmis-household-001"
    )

    program_response = client.post(
        f"/wallets/{wallet['wallet_id']}/hmis/program-links",
        json={
            "actor_did": "did:key:owner",
            "name": "rose haven",
            "program_ref": "rosehaven-day-center",
        },
    )
    assert program_response.status_code == 200
    program_payload = program_response.json()
    assert program_payload["adapter_result"]["normalized_payload"]["candidate_count"] == 1
    assert (
        program_payload["adapter_result"]["normalized_payload"]["candidates"][0]["external_program_id"]
        == "hmis-program-rosehaven"
    )

    audit_response = client.get(f"/wallets/{wallet['wallet_id']}/audit-events")
    assert audit_response.status_code == 200
    actions = [event["action"] for event in audit_response.json()["audit_events"]]
    assert "hmis/lookup_household" in actions
    assert "hmis/list_program_links" in actions


def test_hmis_referral_draft_create_and_list_persists_manual_review_packet() -> None:
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
    client = _client_with_service(service)
    wallet = client.post("/wallets", json={"owner_did": "did:key:owner"}).json()

    create_response = client.post(
        f"/wallets/{wallet['wallet_id']}/hmis/referral-drafts",
        json={
            "actor_did": "did:key:owner",
            "local_subject_ref": "wallet:user-1",
            "destination_program_ref": "rosehaven-day-center",
            "service_plan_id": "plan-1",
            "service_doc_id": "service-doc-1",
            "provider_name": "Rose Haven",
            "program_name": "Day Center",
            "summary": "Client needs same-day shelter intake.",
            "eligibility_notes": "Adult individual seeking shelter.",
            "contact_notes": "Call ahead before arrival.",
        },
    )

    assert create_response.status_code == 200
    create_payload = create_response.json()
    assert create_payload["status"] == "draft"
    assert create_payload["destination_program_ref"] == "rosehaven-day-center"
    assert create_payload["packet"]["review_mode"] == "manual"
    assert create_payload["metadata"]["adapter_name"] == "manual-review"

    list_response = client.get(f"/wallets/{wallet['wallet_id']}/hmis/referral-drafts")
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert len(list_payload["referral_drafts"]) == 1
    assert list_payload["referral_drafts"][0]["referral_draft_id"] == create_payload["referral_draft_id"]

    audit_response = client.get(f"/wallets/{wallet['wallet_id']}/audit-events")
    assert audit_response.status_code == 200
    actions = [event["action"] for event in audit_response.json()["audit_events"]]
    assert "hmis/create_referral_draft" in actions


def test_hmis_referral_draft_validate_marks_validated_and_returns_warnings() -> None:
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
    client = _client_with_service(service)
    wallet = client.post("/wallets", json={"owner_did": "did:key:owner"}).json()

    create_response = client.post(
        f"/wallets/{wallet['wallet_id']}/hmis/referral-drafts",
        json={
            "actor_did": "did:key:owner",
            "local_subject_ref": "wallet:user-1",
            "destination_program_ref": "rosehaven-day-center",
            "summary": "Client needs same-day shelter intake.",
        },
    )
    assert create_response.status_code == 200
    draft_id = create_response.json()["referral_draft_id"]

    validate_response = client.post(
        f"/wallets/{wallet['wallet_id']}/hmis/referral-drafts/{draft_id}/validate",
        json={"actor_did": "did:key:owner"},
    )

    assert validate_response.status_code == 200
    payload = validate_response.json()
    assert payload["validation"]["ok"] is True
    assert "provider_name or program_name should be supplied for manual review" in payload["validation"]["warnings"]
    assert payload["referral_draft"]["status"] == "validated"
    assert payload["referral_draft"]["metadata"]["last_validated_by"] == "did:key:owner"

    audit_response = client.get(f"/wallets/{wallet['wallet_id']}/audit-events")
    assert audit_response.status_code == 200
    actions = [event["action"] for event in audit_response.json()["audit_events"]]
    assert "hmis/validate_referral_draft" in actions


def test_filecoin_upload_bridge_supports_mock_filecoin_pin_mode(monkeypatch) -> None:
    client = _client()
    added: list[bytes] = []
    expected_request_id = f"mock-pin-{hashlib.sha256(b'bafy-uploaded-file').hexdigest()[:12]}"

    class FakeIpfsBackend:
        def add_bytes(self, data: bytes, *, pin: bool = True) -> str:
            assert pin is True
            added.append(data)
            return "bafy-uploaded-file"

    def fail_urlopen(*args, **kwargs):
        raise AssertionError("mock Filecoin Pin mode should not call urllib_request.urlopen")

    monkeypatch.setattr(wallet_api_module, "get_ipfs_backend", lambda: FakeIpfsBackend())
    monkeypatch.setattr(wallet_api_module.urllib_request, "urlopen", fail_urlopen)
    monkeypatch.setenv("WALLET_FILECOIN_PIN_SERVICE_URL", "mock")
    monkeypatch.setenv("WALLET_FILECOIN_PIN_MOCK_STATUS", "pinned")

    response = client.post(
        "/filecoin-upload",
        data={"metadata": json.dumps({"walletId": "wallet-demo"})},
        files={"file": ("proofs.json", b"proof-bundle", "application/json")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ipfsCid"] == "bafy-uploaded-file"
    assert payload["filecoinPinStatus"] == "queued"
    assert payload["requestId"] == expected_request_id
    assert payload["filecoinPinRequestId"] == expected_request_id
    assert payload["statusUrl"] == f"/filecoin-upload/status/{expected_request_id}"


def test_ipfs_proxy_returns_allowlisted_cid(monkeypatch) -> None:
    client = _client()

    class FakeIpfsBackend:
        def cat(self, cid: str) -> bytes:
            assert cid == "bafybeigdyrztproxyallowedcid1234567890abcd"
            return json.dumps({"proofs": [{"claim": "Proxy loaded proof"}]}).encode("utf-8")

    monkeypatch.setenv("WALLET_IPFS_PROXY_ALLOWED_CIDS", "bafybeigdyrztproxyallowedcid1234567890abcd")
    monkeypatch.setattr(wallet_api_module, "get_ipfs_backend", lambda: FakeIpfsBackend())

    response = client.get("/ipfs-proxy/bafybeigdyrztproxyallowedcid1234567890abcd")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {"proofs": [{"claim": "Proxy loaded proof"}]}


def test_ipfs_proxy_rejects_non_allowlisted_cid(monkeypatch) -> None:
    client = _client()
    monkeypatch.setenv("WALLET_IPFS_PROXY_ALLOWED_CIDS", "bafybeigdyrztproxyallowedcid1234567890abcd")

    response = client.get("/ipfs-proxy/bafybeigdyrztnotallowedcid1234567890abcd")

    assert response.status_code == 403
    assert response.json()["detail"] == "CID is not allowed by WALLET_IPFS_PROXY_ALLOWED_CIDS"


def test_filecoin_upload_bridge_supports_mock_ipfs_and_mock_filecoin_without_external_backends(monkeypatch) -> None:
    client = _client()
    expected_cid = f"bafybeimock{hashlib.sha256(b'proof-bundle').hexdigest()[:24]}"
    expected_request_id = f"mock-pin-{hashlib.sha256(expected_cid.encode('utf-8')).hexdigest()[:12]}"

    def fail_get_ipfs_backend():
        raise AssertionError("mock IPFS upload mode should not resolve a real IPFS backend")

    def fail_urlopen(*args, **kwargs):
        raise AssertionError("mock Filecoin Pin mode should not call urllib_request.urlopen")

    monkeypatch.setattr(wallet_api_module, "get_ipfs_backend", fail_get_ipfs_backend)
    monkeypatch.setattr(wallet_api_module.urllib_request, "urlopen", fail_urlopen)
    monkeypatch.setenv("WALLET_IPFS_UPLOAD_BACKEND", "mock")
    monkeypatch.setenv("WALLET_FILECOIN_PIN_SERVICE_URL", "mock")
    monkeypatch.setenv("WALLET_FILECOIN_PIN_MOCK_STATUS", "pinned")

    response = client.post(
        "/filecoin-upload",
        data={"metadata": json.dumps({"walletId": "wallet-demo"})},
        files={"file": ("proofs.json", b"proof-bundle", "application/json")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ipfsCid"] == expected_cid
    assert payload["gatewayUrl"] == f"https://w3s.link/ipfs/{expected_cid}"
    assert payload["filecoinPinStatus"] == "queued"
    assert payload["requestId"] == expected_request_id
    assert payload["filecoinPinRequestId"] == expected_request_id
    assert payload["statusUrl"] == f"/filecoin-upload/status/{expected_request_id}"
    assert payload["filecoinPinInfo"] == {
        "provider": "mock-filecoin-pin",
        "cid": expected_cid,
        "mock": True,
    }


def test_filecoin_upload_status_proxy_returns_sidecar_status(monkeypatch) -> None:
    client = _client()
    observed_request: dict[str, object] = {}

    class FakeResponse:
        headers = {"content-type": "application/json"}

        def read(self) -> bytes:
            return json.dumps({"requestid": "pin-123", "status": "pinned", "info": {"pin_duration": "25"}}).encode(
                "utf-8"
            )

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

    def fake_urlopen(req, timeout: float):
        observed_request["url"] = req.full_url
        observed_request["method"] = req.get_method()
        observed_request["headers"] = {key.lower(): value for key, value in req.header_items()}
        observed_request["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(wallet_api_module.urllib_request, "urlopen", fake_urlopen)
    monkeypatch.setenv("WALLET_FILECOIN_PIN_SERVICE_URL", "http://filecoin-pin:3456")
    monkeypatch.setenv("WALLET_FILECOIN_PIN_BEARER_TOKEN", "sidecar-token")
    monkeypatch.setenv("WALLET_FILECOIN_PIN_TIMEOUT_SECONDS", "7")

    response = client.get("/filecoin-upload/status/pin-123")

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "filecoinPinInfo": {"pin_duration": "25"},
        "info": {"pin_duration": "25"},
        "requestId": "pin-123",
        "requestid": "pin-123",
        "status": "pinned",
        "statusUrl": "/filecoin-upload/status/pin-123",
    }
    assert observed_request == {
        "headers": {"authorization": "Bearer sidecar-token"},
        "method": "GET",
        "timeout": 7.0,
        "url": "http://filecoin-pin:3456/pins/pin-123",
    }


def test_filecoin_upload_status_proxy_supports_mock_filecoin_pin_mode(monkeypatch) -> None:
    client = _client()
    request_id = f"mock-pin-{hashlib.sha256(b'bafy-uploaded-file').hexdigest()[:12]}"
    expected_piece_cid = f"baga6ea4seaq{hashlib.sha256(request_id.encode('utf-8')).hexdigest()[:16]}"

    def fail_urlopen(*args, **kwargs):
        raise AssertionError("mock Filecoin Pin mode should not call urllib_request.urlopen")

    monkeypatch.setattr(wallet_api_module.urllib_request, "urlopen", fail_urlopen)
    monkeypatch.setenv("WALLET_FILECOIN_PIN_SERVICE_URL", "mock")
    monkeypatch.setenv("WALLET_FILECOIN_PIN_MOCK_STATUS", "pinned")

    response = client.get(f"/filecoin-upload/status/{request_id}")

    assert response.status_code == 200
    assert response.json() == {
        "filecoinPinInfo": {
            "mock": True,
            "pieceCid": expected_piece_cid,
            "provider": "mock-filecoin-pin",
        },
        "info": {
            "mock": True,
            "pieceCid": expected_piece_cid,
            "provider": "mock-filecoin-pin",
        },
        "requestId": request_id,
        "requestid": request_id,
        "status": "pinned",
        "statusUrl": f"/filecoin-upload/status/{request_id}",
    }


def test_filecoin_upload_status_proxy_requires_sidecar_configuration() -> None:
    client = _client()

    response = client.get("/filecoin-upload/status/pin-123")

    assert response.status_code == 503
    assert response.json()["detail"] == "WALLET_FILECOIN_PIN_SERVICE_URL is not configured"


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


def test_hmis_referral_draft_submit_moves_validated_draft_to_manual_review_queue() -> None:
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
    client = _client_with_service(service)
    wallet = client.post("/wallets", json={"owner_did": "did:key:owner"}).json()

    create_response = client.post(
        f"/wallets/{wallet['wallet_id']}/hmis/referral-drafts",
        json={
            "actor_did": "did:key:owner",
            "local_subject_ref": "wallet:user-1",
            "destination_program_ref": "rosehaven-day-center",
            "provider_name": "Rose Haven",
            "summary": "Client needs same-day shelter intake.",
        },
    )
    assert create_response.status_code == 200
    draft_id = create_response.json()["referral_draft_id"]

    validate_response = client.post(
        f"/wallets/{wallet['wallet_id']}/hmis/referral-drafts/{draft_id}/validate",
        json={"actor_did": "did:key:owner"},
    )
    assert validate_response.status_code == 200
    assert validate_response.json()["referral_draft"]["status"] == "validated"

    submit_response = client.post(
        f"/wallets/{wallet['wallet_id']}/hmis/referral-drafts/{draft_id}/submit",
        json={"actor_did": "did:key:owner"},
    )

    assert submit_response.status_code == 200
    payload = submit_response.json()
    assert payload["submission"]["ok"] is True
    assert payload["submission"]["mode"] == "manual_review_queue"
    assert payload["referral_draft"]["status"] == "queued_manual_review"
    assert payload["referral_draft"]["metadata"]["submitted_by"] == "did:key:owner"
    assert payload["referral_draft"]["metadata"]["submission_mode"] == "manual_review_queue"

    audit_response = client.get(f"/wallets/{wallet['wallet_id']}/audit-events")
    assert audit_response.status_code == 200
    actions = [event["action"] for event in audit_response.json()["audit_events"]]
    assert "hmis/submit_referral_draft" in actions


def test_hmis_referral_draft_submit_requires_validated_status() -> None:
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
    client = _client_with_service(service)
    wallet = client.post("/wallets", json={"owner_did": "did:key:owner"}).json()

    create_response = client.post(
        f"/wallets/{wallet['wallet_id']}/hmis/referral-drafts",
        json={
            "actor_did": "did:key:owner",
            "local_subject_ref": "wallet:user-1",
            "destination_program_ref": "rosehaven-day-center",
        },
    )
    assert create_response.status_code == 200
    draft_id = create_response.json()["referral_draft_id"]

    submit_response = client.post(
        f"/wallets/{wallet['wallet_id']}/hmis/referral-drafts/{draft_id}/submit",
        json={"actor_did": "did:key:owner"},
    )

    assert submit_response.status_code == 400
    assert submit_response.json()["detail"] == "HMIS referral draft must be validated before submission"


def test_hmis_referral_draft_update_resets_status_and_rebuilds_packet() -> None:
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
    client = _client_with_service(service)
    wallet = client.post("/wallets", json={"owner_did": "did:key:owner"}).json()

    create_response = client.post(
        f"/wallets/{wallet['wallet_id']}/hmis/referral-drafts",
        json={
            "actor_did": "did:key:owner",
            "local_subject_ref": "wallet:user-1",
            "destination_program_ref": "rosehaven-day-center",
            "summary": "Initial summary.",
        },
    )
    assert create_response.status_code == 200
    draft_id = create_response.json()["referral_draft_id"]

    validate_response = client.post(
        f"/wallets/{wallet['wallet_id']}/hmis/referral-drafts/{draft_id}/validate",
        json={"actor_did": "did:key:owner"},
    )
    assert validate_response.status_code == 200
    assert validate_response.json()["referral_draft"]["status"] == "validated"

    update_response = client.patch(
        f"/wallets/{wallet['wallet_id']}/hmis/referral-drafts/{draft_id}",
        json={
            "actor_did": "did:key:owner",
            "provider_name": "Rose Haven",
            "program_name": "Day Center",
            "contact_notes": "Bring ID and arrive before 5 PM.",
            "metadata": {"edited_in_ui": True},
        },
    )

    assert update_response.status_code == 200
    payload = update_response.json()
    assert payload["status"] == "draft"
    assert payload["provider_name"] == "Rose Haven"
    assert payload["program_name"] == "Day Center"
    assert payload["packet"]["provider_name"] == "Rose Haven"
    assert payload["packet"]["contact_notes"] == "Bring ID and arrive before 5 PM."
    assert payload["metadata"]["edited_in_ui"] is True
    assert "last_validated_by" not in payload["metadata"]

    audit_response = client.get(f"/wallets/{wallet['wallet_id']}/audit-events")
    assert audit_response.status_code == 200
    actions = [event["action"] for event in audit_response.json()["audit_events"]]
    assert "hmis/update_referral_draft" in actions


def test_wallet_api_multi_dimensional_analytics_suppresses_sparse_cells() -> None:
    client = _client()
    response = client.post(
        "/analytics/templates",
        json={
            "template_id": "api_multi_sparse_v1",
            "title": "Sparse service gaps",
            "purpose": "County and need planning",
            "allowed_record_types": ["location", "need"],
            "allowed_derived_fields": ["county", "need_category"],
            "min_cohort_size": 2,
            "epsilon_budget": 0.5,
            "created_by": "did:key:analyst",
        },
    )
    assert response.status_code == 200
    rows = [
        ("did:key:api-cohort-owner1", {"county": "Multnomah", "need_category": "housing"}),
        ("did:key:api-cohort-owner2", {"county": "Multnomah", "need_category": "housing"}),
        ("did:key:api-cohort-owner3", {"county": "Lane", "need_category": "food"}),
        ("did:key:api-cohort-owner4", {"county": "Lane", "need_category": "food"}),
        ("did:key:api-cohort-owner5", {"county": "Clackamas", "need_category": "rare-need"}),
    ]

    for owner, fields in rows:
        wallet = client.post("/wallets", json={"owner_did": owner}).json()
        response = client.post(
            f"/wallets/{wallet['wallet_id']}/analytics/consents/from-template",
            json={"actor_did": owner, "template_id": "api_multi_sparse_v1"},
        )
        assert response.status_code == 200
        consent = response.json()
        response = client.post(
            f"/wallets/{wallet['wallet_id']}/analytics/contributions",
            json={
                "actor_did": owner,
                "consent_id": consent["consent_id"],
                "template_id": "api_multi_sparse_v1",
                "fields": fields,
            },
        )
        assert response.status_code == 200

    response = client.post(
        "/analytics/api_multi_sparse_v1/count-by-fields",
        json={"group_by": ["county", "need_category"], "min_cohort_size": 2},
    )
    assert response.status_code == 200
    result = response.json()
    serialized = json.dumps(result)

    assert result["metric"] == "count_by_fields"
    assert result["released"] is True
    assert result["suppressed"] is True
    assert result["count"] == 4
    assert result["group_by"] == ["county", "need_category"]
    assert result["suppressed_cohort_count"] == 1
    assert len(result["cohorts"]) == 2
    assert "rare-need" not in serialized
    assert "Clackamas" not in serialized


def test_wallet_api_draft_analytics_template_is_not_consentable() -> None:
    client = _client()
    wallet = client.post("/wallets", json={"owner_did": "did:key:owner"}).json()

    response = client.post(
        "/analytics/templates",
        json={
            "template_id": "draft_housing_gap_v1",
            "title": "Draft housing service gaps",
            "purpose": "Template review",
            "allowed_record_types": ["location"],
            "allowed_derived_fields": ["county"],
            "min_cohort_size": 2,
            "epsilon_budget": 0.5,
            "created_by": "did:key:analyst",
            "status": "draft",
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "draft"

    response = client.get("/analytics/templates")
    assert response.status_code == 200
    assert response.json()["templates"] == []

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/analytics/consents/from-template",
        json={"actor_did": "did:key:owner", "template_id": "draft_housing_gap_v1"},
    )
    assert response.status_code == 400
    assert "not active" in response.json()["detail"]


def test_wallet_api_lists_and_revokes_analytics_consent() -> None:
    client = _client()
    wallet = client.post("/wallets", json={"owner_did": "did:key:owner"}).json()
    response = client.post(
        "/analytics/templates",
        json={
            "template_id": "consent_controls_v1",
            "title": "Consent controls",
            "purpose": "UI consent controls",
            "allowed_record_types": ["location", "need"],
            "allowed_derived_fields": ["county", "need_category"],
            "min_cohort_size": 2,
            "epsilon_budget": 0.5,
            "created_by": "did:key:analyst",
        },
    )
    assert response.status_code == 200

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/analytics/consents/from-template",
        json={
            "actor_did": "did:key:owner",
            "template_id": "consent_controls_v1",
            "expires_at": "2026-06-30T00:00:00+00:00",
        },
    )
    assert response.status_code == 200
    consent = response.json()

    response = client.get(f"/wallets/{wallet['wallet_id']}/analytics/consents")
    assert response.status_code == 200
    listed = response.json()["consents"]
    assert listed[0]["consent_id"] == consent["consent_id"]
    assert listed[0]["expires_at"] == "2026-06-30T00:00:00+00:00"
    assert listed[0]["allowed_derived_fields"] == ["county", "need_category"]

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/analytics/consents/{consent['consent_id']}/revoke",
        json={"actor_did": "did:key:owner"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "revoked"

    response = client.get(f"/wallets/{wallet['wallet_id']}/analytics/consents?status=active")
    assert response.status_code == 200
    assert response.json()["consents"] == []


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
    assert proof["proof_system"] == "simulated"
    assert proof["verification_status"] == "verified"
    assert proof["public_inputs"]["region_id"] == "multnomah_county"
    assert proof["public_inputs"]["claim"] == "location_in_region"
    assert proof["public_inputs"]["region_policy_hash"]
    assert "lat" not in str(proof["public_inputs"]).lower()
    assert "lon" not in str(proof["public_inputs"]).lower()
    assert "witness" not in str(proof["public_inputs"]).lower()

    actions = [event["action"] for event in client.get(f"/wallets/{wallet['wallet_id']}/audit").json()["events"]]
    assert "proof/create" in actions

    response = client.get(f"/wallets/{wallet['wallet_id']}/proofs")
    assert response.status_code == 200
    proofs = response.json()["proofs"]
    assert [item["proof_id"] for item in proofs] == [proof["proof_id"]]
    assert proofs[0]["public_inputs"] == proof["public_inputs"]
    assert proofs[0]["witness_record_ids"] == [location["record_id"]]


def test_wallet_api_delegate_creates_location_distance_proof() -> None:
    client = _client()
    wallet = client.post("/wallets", json={"owner_did": "did:key:owner"}).json()
    location = client.post(
        f"/wallets/{wallet['wallet_id']}/locations",
        json={"actor_did": "did:key:owner", "lat": 45.515232, "lon": -122.678385},
    ).json()

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/locations/{location['record_id']}/distance-proof-grants",
        json={
            "issuer_did": "did:key:owner",
            "audience_did": "did:key:delegate",
            "target_id": "shelter-west",
            "max_distance_km": 1.0,
        },
    )
    assert response.status_code == 200
    grant = response.json()

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/locations/{location['record_id']}/distance-proofs",
        json={
            "actor_did": "did:key:delegate",
            "grant_id": grant["grant_id"],
            "target_id": "shelter-west",
            "target_lat": 45.516,
            "target_lon": -122.679,
            "max_distance_km": 1.0,
        },
    )
    assert response.status_code == 200
    proof = response.json()
    assert proof["proof_type"] == "location_distance"
    assert proof["is_simulated"] is True
    assert proof["proof_system"] == "simulated"
    assert proof["verification_status"] == "verified"
    assert proof["public_inputs"]["claim"] == "location_within_distance"
    assert proof["public_inputs"]["target_id"] == "shelter-west"
    assert proof["public_inputs"]["max_distance_km"] == 1.0
    assert proof["public_inputs"]["target_policy_hash"]
    serialized = str(proof)
    for secret in ("45.515232", "-122.678385", "45.516", "-122.679"):
        assert secret not in serialized


def test_wallet_api_location_distance_grant_enforces_target_and_threshold_caveats() -> None:
    client = _client()
    wallet = client.post("/wallets", json={"owner_did": "did:key:owner"}).json()
    location = client.post(
        f"/wallets/{wallet['wallet_id']}/locations",
        json={"actor_did": "did:key:owner", "lat": 45.515232, "lon": -122.678385},
    ).json()
    grant = client.post(
        f"/wallets/{wallet['wallet_id']}/locations/{location['record_id']}/distance-proof-grants",
        json={
            "issuer_did": "did:key:owner",
            "audience_did": "did:key:delegate",
            "target_id": "shelter-west",
            "max_distance_km": 1.0,
        },
    ).json()

    wrong_target = client.post(
        f"/wallets/{wallet['wallet_id']}/locations/{location['record_id']}/distance-proofs",
        json={
            "actor_did": "did:key:delegate",
            "grant_id": grant["grant_id"],
            "target_id": "shelter-east",
            "target_lat": 45.516,
            "target_lon": -122.679,
            "max_distance_km": 1.0,
        },
    )
    assert wrong_target.status_code == 400
    assert "target_id" in wrong_target.json()["detail"]

    wider_threshold = client.post(
        f"/wallets/{wallet['wallet_id']}/locations/{location['record_id']}/distance-proofs",
        json={
            "actor_did": "did:key:delegate",
            "grant_id": grant["grant_id"],
            "target_id": "shelter-west",
            "target_lat": 45.516,
            "target_lon": -122.679,
            "max_distance_km": 2.0,
        },
    )
    assert wider_threshold.status_code == 400
    assert "max_distance_km" in wider_threshold.json()["detail"]


def test_wallet_api_production_proof_mode_rejects_simulated_receipts() -> None:
    client = _client_with_service(WalletInterfaceService(allow_simulated_proofs=False))
    wallet = client.post("/wallets", json={"owner_did": "did:key:owner"}).json()
    location = client.post(
        f"/wallets/{wallet['wallet_id']}/locations",
        json={"actor_did": "did:key:owner", "lat": 45.515232, "lon": -122.678385},
    ).json()

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/locations/{location['record_id']}/region-proofs",
        json={"actor_did": "did:key:owner", "region_id": "multnomah_county"},
    )

    assert response.status_code == 400
    assert "Simulated proofs are disabled" in response.json()["detail"]
    response = client.get(f"/wallets/{wallet['wallet_id']}/proofs")
    assert response.status_code == 200
    assert response.json()["proofs"] == []


def test_wallet_api_production_proof_mode_accepts_configured_backend() -> None:
    client = _client_with_service(
        WalletInterfaceService(
            proof_backend=DeterministicLocationRegionProofBackend(),
            allow_simulated_proofs=False,
        )
    )
    wallet = client.post("/wallets", json={"owner_did": "did:key:owner"}).json()
    location = client.post(
        f"/wallets/{wallet['wallet_id']}/locations",
        json={"actor_did": "did:key:owner", "lat": 45.515232, "lon": -122.678385},
    ).json()

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/locations/{location['record_id']}/region-proofs",
        json={"actor_did": "did:key:owner", "region_id": "multnomah_county"},
    )

    assert response.status_code == 200
    proof = response.json()
    assert proof["is_simulated"] is False
    assert proof["proof_system"] == "deterministic-test-proof"
    assert proof["verification_status"] == "verified"
    assert proof["proof_artifact_ref"].startswith("deterministic-proof://")
    assert "lat" not in str(proof["public_inputs"]).lower()
    assert "lon" not in str(proof["public_inputs"]).lower()
    assert "witness" not in str(proof["public_inputs"]).lower()
    serialized = json.dumps(proof)
    assert "45.515232" not in serialized
    assert "-122.678385" not in serialized


def test_wallet_api_provekit_receipt_metadata_export_qr_and_audit_are_sanitized() -> None:
    client = _client_with_service(
        WalletInterfaceService(
            proof_backend=_ProveKitWalletProofBackend(cache_status="miss"),
            allow_simulated_proofs=False,
        )
    )
    wallet, location = _create_wallet_location(client)

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/locations/{location['record_id']}/region-proofs",
        json={"actor_did": "did:key:owner", "region_id": "multnomah_county"},
    )

    assert response.status_code == 200, response.text
    proof = response.json()
    assert proof["proof_type"] == "provider_eligibility"
    assert proof["is_simulated"] is False
    assert proof["proof_system"] == "ProveKit-WHIR"
    assert proof["verification_status"] == "verified"
    assert proof["circuit_id"] == "provekit_knowledge_of_axioms@v1"
    assert proof["public_inputs"] == _provekit_public_inputs()
    assert proof["metadata"]["backend"] == "provekit"
    assert proof["metadata"]["proof_system"] == "ProveKit-WHIR"
    assert proof["metadata"]["provekit_branch"] == "v1"
    assert proof["metadata"]["cache_status"] == "miss"
    assert proof["metadata"]["public_artifact_refs"]["proof"].endswith("/proof.np")
    _assert_no_provekit_private_leak(proof)

    list_response = client.get(f"/wallets/{wallet['wallet_id']}/proofs")
    assert list_response.status_code == 200
    listed_proof = list_response.json()["proofs"][0]
    assert listed_proof["proof_id"] == proof["proof_id"]
    assert listed_proof["metadata"] == proof["metadata"]
    _assert_no_provekit_private_leak(listed_proof)

    audit_response = client.get(f"/wallets/{wallet['wallet_id']}/audit-events")
    assert audit_response.status_code == 200
    proof_event = next(event for event in audit_response.json()["audit_events"] if event["action"] == "proof/create")
    assert proof_event["details"]["proof_id"] == proof["proof_id"]
    assert proof_event["details"]["proof_system"] == "ProveKit-WHIR"
    assert proof_event["details"]["verifier_id"] == "provekit-whir-eligibility-v1"
    assert proof_event["details"]["circuit_id"] == "provekit_knowledge_of_axioms@v1"
    assert proof_event["details"]["verification_status"] == "verified"
    assert proof_event["details"]["cache_status"] == "miss"
    _assert_no_provekit_private_leak(proof_event)

    export_response = client.post(
        f"/wallets/{wallet['wallet_id']}/exports",
        json={"actor_did": "did:key:owner", "record_ids": [location["record_id"]]},
    )
    assert export_response.status_code == 200, export_response.text
    bundle = export_response.json()
    assert bundle["proofs"][0]["metadata"] == proof["metadata"]
    _assert_no_provekit_private_leak(bundle)

    qr_payload = {
        "schemaVersion": "211-ai-wallet-root-ipld-v1",
        "title": "ProveKit wallet proof bundle",
        "proofs": bundle["proofs"],
    }
    _assert_no_provekit_private_leak(qr_payload)


def test_wallet_api_provekit_cache_hit_and_miss_metadata_round_trip() -> None:
    for cache_status in ("miss", "hit"):
        client = _client_with_service(
            WalletInterfaceService(
                proof_backend=_ProveKitWalletProofBackend(cache_status=cache_status),
                allow_simulated_proofs=False,
            )
        )
        wallet, location = _create_wallet_location(client)

        response = client.post(
            f"/wallets/{wallet['wallet_id']}/locations/{location['record_id']}/region-proofs",
            json={"actor_did": "did:key:owner", "region_id": "multnomah_county"},
        )

        assert response.status_code == 200, response.text
        proof = response.json()
        assert proof["metadata"]["cache_status"] == cache_status
        assert client.get(f"/wallets/{wallet['wallet_id']}/proofs").json()["proofs"][0]["metadata"][
            "cache_status"
        ] == cache_status
        audit_event = next(
            event
            for event in client.get(f"/wallets/{wallet['wallet_id']}/audit").json()["events"]
            if event["action"] == "proof/create"
        )
        assert audit_event["details"]["cache_status"] == cache_status


def test_wallet_api_provekit_disabled_unavailable_and_integrity_errors_fail_closed() -> None:
    for message in (
        "ProveKit backend disabled; no simulated fallback was created.",
        "ProveKit backend unavailable.",
        "artifact_hash_mismatch: Prepared ProveKit artifact digest does not match the pinned manifest.",
        "stale_verifier_key: Verifier key digest is stale and must be rotated.",
    ):
        client = _client_with_service(
            WalletInterfaceService(
                proof_backend=_ProveKitWalletProofBackend(error=message),
                allow_simulated_proofs=False,
            )
        )
        wallet, location = _create_wallet_location(client)

        response = client.post(
            f"/wallets/{wallet['wallet_id']}/locations/{location['record_id']}/region-proofs",
            json={"actor_did": "did:key:owner", "region_id": "multnomah_county"},
        )

        assert response.status_code == 400
        assert message in response.json()["detail"]
        assert client.get(f"/wallets/{wallet['wallet_id']}/proofs").json()["proofs"] == []


def test_wallet_api_provekit_verification_failure_fails_closed_without_receipt() -> None:
    client = _client_with_service(
        WalletInterfaceService(
            proof_backend=_ProveKitWalletProofBackend(verify_result=False),
            allow_simulated_proofs=False,
        )
    )
    wallet, location = _create_wallet_location(client)

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/locations/{location['record_id']}/region-proofs",
        json={"actor_did": "did:key:owner", "region_id": "multnomah_county"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Proof verification failed"
    assert client.get(f"/wallets/{wallet['wallet_id']}/proofs").json()["proofs"] == []


def test_wallet_api_rejects_simulated_provekit_overclaim() -> None:
    client = _client_with_service(
        WalletInterfaceService(
            proof_backend=_ProveKitWalletProofBackend(
                is_simulated=True,
                proof_system="ProveKit-WHIR",
                metadata_overrides={"production_evidence": True},
            ),
            allow_simulated_proofs=True,
        )
    )
    wallet, location = _create_wallet_location(client)

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/locations/{location['record_id']}/region-proofs",
        json={"actor_did": "did:key:owner", "region_id": "multnomah_county"},
    )

    assert response.status_code == 400
    assert "Simulated proofs cannot claim" in response.json()["detail"]
    assert client.get(f"/wallets/{wallet['wallet_id']}/proofs").json()["proofs"] == []


def test_wallet_api_env_selects_deterministic_proof_backend(monkeypatch) -> None:
    monkeypatch.setenv("WALLET_PROOF_MODE", "production")
    monkeypatch.setenv("WALLET_PROOF_BACKEND", "deterministic-location-region")
    client = _client_with_service(WalletInterfaceService())
    wallet = client.post("/wallets", json={"owner_did": "did:key:owner"}).json()
    location = client.post(
        f"/wallets/{wallet['wallet_id']}/locations",
        json={"actor_did": "did:key:owner", "lat": 45.515232, "lon": -122.678385},
    ).json()

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/locations/{location['record_id']}/region-proofs",
        json={"actor_did": "did:key:owner", "region_id": "multnomah_county"},
    )

    assert response.status_code == 200
    proof = response.json()
    assert proof["is_simulated"] is False
    assert proof["proof_system"] == "deterministic-test-proof"
    assert proof["circuit_id"] == "deterministic-location-region-v0.1"


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

    response = client.get(f"/wallets/{wallet['wallet_id']}/records", params={"data_type": "document"})
    assert response.status_code == 200
    records = response.json()["records"]
    assert [item["record_id"] for item in records] == [record["record_id"]]
    assert records[0]["data_type"] == "document"

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

    response = client.get(
        f"/wallets/{wallet['wallet_id']}/grant-receipts",
        params={"audience_did": "did:key:delegate"},
    )
    assert response.status_code == 200
    receipt = response.json()["receipts"][0]
    assert receipt["grant_id"] == grant["grant_id"]
    assert receipt["status"] == "active"
    assert receipt["receipt_hash"]

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


def test_wallet_api_redacted_and_vector_document_analysis_outputs_are_safe() -> None:
    client = _client()
    owner_key = random_key().hex()
    delegate_key = random_key().hex()
    wallet = client.post("/wallets", json={"owner_did": "did:key:owner"}).json()
    record = client.post(
        f"/wallets/{wallet['wallet_id']}/documents/text",
        json={
            "actor_did": "did:key:owner",
            "key_hex": owner_key,
            "filename": "intake.txt",
            "text": (
                "Jane Example can be reached at jane@example.org or 503-555-1212. "
                "SSN 123-45-6789. Needs rent, SNAP, and clinic help."
            ),
        },
    ).json()
    grant = client.post(
        f"/wallets/{wallet['wallet_id']}/records/{record['record_id']}/grants",
        json={
            "issuer_did": "did:key:owner",
            "audience_did": "did:key:delegate",
            "issuer_key_hex": owner_key,
            "audience_key_hex": delegate_key,
            "abilities": ["record/analyze"],
            "output_types": ["redacted_derived_only", "vector_profile", "redacted_graphrag"],
        },
    ).json()

    redacted_invocation = client.post(
        f"/wallets/{wallet['wallet_id']}/records/{record['record_id']}/analysis-invocations",
        json={
            "grant_id": grant["grant_id"],
            "actor_did": "did:key:delegate",
            "actor_key_hex": delegate_key,
            "output_types": ["redacted_derived_only"],
        },
    ).json()
    response = client.post(
        f"/wallets/{wallet['wallet_id']}/records/{record['record_id']}/analyze/redacted",
        json={
            "actor_did": "did:key:delegate",
            "actor_key_hex": delegate_key,
            "invocation_token": redacted_invocation["token"],
        },
    )
    assert response.status_code == 200
    redacted = response.json()
    redacted_output = json.dumps(redacted["output"])
    assert redacted["artifact"]["artifact_type"] == "redacted_document_analysis"
    assert redacted["output"]["output_policy"] == "redacted_derived_only"
    assert "jane@example.org" not in redacted_output
    assert "503-555-1212" not in redacted_output
    assert "123-45-6789" not in redacted_output
    assert "Jane Example" not in redacted_output
    assert set(redacted["output"]["derived_facts"]["need_categories"]) >= {"housing", "food", "health"}

    vector_invocation = client.post(
        f"/wallets/{wallet['wallet_id']}/records/{record['record_id']}/analysis-invocations",
        json={
            "grant_id": grant["grant_id"],
            "actor_did": "did:key:delegate",
            "actor_key_hex": delegate_key,
            "output_types": ["vector_profile"],
        },
    ).json()
    response = client.post(
        f"/wallets/{wallet['wallet_id']}/records/{record['record_id']}/vector-profile",
        json={
            "actor_did": "did:key:delegate",
            "actor_key_hex": delegate_key,
            "invocation_token": vector_invocation["token"],
            "chunk_size_words": 8,
        },
    )
    assert response.status_code == 200
    vector = response.json()
    vector_output = json.dumps(vector["output"])
    assert vector["artifact"]["artifact_type"] == "redacted_document_vector_profile"
    assert vector["output"]["output_policy"] == "encrypted_vector_profile"
    assert "jane@example.org" not in vector_output
    assert "503-555-1212" not in vector_output
    assert vector["output"]["profile"]["profile_type"] == "redacted_lexical_hash_vector"

    graphrag_invocation = client.post(
        f"/wallets/{wallet['wallet_id']}/records/{record['record_id']}/analysis-invocations",
        json={
            "grant_id": grant["grant_id"],
            "actor_did": "did:key:delegate",
            "actor_key_hex": delegate_key,
            "output_types": ["redacted_graphrag"],
        },
    ).json()
    response = client.post(
        f"/wallets/{wallet['wallet_id']}/records/graphrag/redacted",
        json={
            "actor_did": "did:key:delegate",
            "actor_key_hex": delegate_key,
            "invocation_token": graphrag_invocation["token"],
            "record_ids": [record["record_id"]],
        },
    )
    assert response.status_code == 200
    graph = response.json()
    graph_output = json.dumps(graph["output"])
    assert graph["artifact"]["artifact_type"] == "redacted_document_graphrag"
    assert graph["output"]["output_policy"] == "redacted_graphrag"
    assert graph["output"]["graph"]["graph_type"] == "redacted_category_entity_graph"
    assert set(graph["output"]["graph"]["category_record_counts"]) >= {"housing", "food", "health"}
    assert "jane@example.org" not in graph_output
    assert "503-555-1212" not in graph_output
    assert "123-45-6789" not in graph_output

    actions = [event["action"] for event in client.get(f"/wallets/{wallet['wallet_id']}/audit").json()["events"]]
    assert "record/analyze_redacted" in actions
    assert "record/vector_profile" in actions
    assert "record/graphrag_redacted" in actions


def test_wallet_api_owner_can_create_cross_record_redacted_analysis() -> None:
    client = _client()
    owner_key = random_key().hex()
    wallet = client.post("/wallets", json={"owner_did": "did:key:owner"}).json()
    first = client.post(
        f"/wallets/{wallet['wallet_id']}/documents/text",
        json={
            "actor_did": "did:key:owner",
            "key_hex": owner_key,
            "filename": "first.txt",
            "text": "Email jane@example.org about rent assistance.",
        },
    ).json()
    second = client.post(
        f"/wallets/{wallet['wallet_id']}/documents/text",
        json={
            "actor_did": "did:key:owner",
            "key_hex": owner_key,
            "filename": "second.txt",
            "text": "Call 503-555-1212 about SNAP and clinic referrals.",
        },
    ).json()

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/records/analyze/redacted",
        json={
            "actor_did": "did:key:owner",
            "actor_key_hex": owner_key,
            "record_ids": [first["record_id"], second["record_id"]],
        },
    )

    assert response.status_code == 200
    analysis = response.json()
    serialized = json.dumps(analysis["output"])
    assert analysis["artifact"]["artifact_type"] == "redacted_cross_document_analysis"
    assert analysis["output"]["source_record_count"] == 2
    assert "jane@example.org" not in serialized
    assert "503-555-1212" not in serialized


def test_wallet_api_owner_can_create_redacted_graphrag() -> None:
    client = _client()
    owner_key = random_key().hex()
    wallet = client.post("/wallets", json={"owner_did": "did:key:owner"}).json()
    first = client.post(
        f"/wallets/{wallet['wallet_id']}/documents/text",
        json={
            "actor_did": "did:key:owner",
            "key_hex": owner_key,
            "filename": "first.txt",
            "text": "Jane Example emailed jane@example.org about rent and utility assistance.",
        },
    ).json()
    second = client.post(
        f"/wallets/{wallet['wallet_id']}/documents/text",
        json={
            "actor_did": "did:key:owner",
            "key_hex": owner_key,
            "filename": "second.txt",
            "text": "Call 503-555-1212 about SNAP and medical clinic referrals.",
        },
    ).json()

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/records/graphrag/redacted",
        json={
            "actor_did": "did:key:owner",
            "actor_key_hex": owner_key,
            "record_ids": [first["record_id"], second["record_id"]],
        },
    )

    assert response.status_code == 200
    graph = response.json()
    serialized = json.dumps(graph["output"])
    assert graph["artifact"]["artifact_type"] == "redacted_document_graphrag"
    assert graph["output"]["output_policy"] == "redacted_graphrag"
    assert graph["output"]["graph"]["graph_type"] == "redacted_category_entity_graph"
    assert graph["output"]["graph"]["category_record_counts"]["housing"] == 1
    assert graph["output"]["graph"]["category_record_counts"]["food"] == 1
    assert graph["output"]["graph"]["category_record_counts"]["health"] == 1
    assert "Jane Example" not in serialized
    assert "jane@example.org" not in serialized
    assert "503-555-1212" not in serialized
    actions = [event["action"] for event in client.get(f"/wallets/{wallet['wallet_id']}/audit").json()["events"]]
    assert "record/graphrag_redacted" in actions


def test_wallet_api_redacted_text_extraction_and_form_analysis_outputs_are_safe() -> None:
    client = _client()
    owner_key = random_key().hex()
    delegate_key = random_key().hex()
    wallet = client.post("/wallets", json={"owner_did": "did:key:owner"}).json()
    record = client.post(
        f"/wallets/{wallet['wallet_id']}/documents/text",
        json={
            "actor_did": "did:key:owner",
            "key_hex": owner_key,
            "filename": "intake-form.txt",
            "text": (
                "Full name: Jane Example\n"
                "Email: jane@example.org\n"
                "Phone: 503-555-1212\n"
                "Rent assistance required: yes\n"
                "SNAP enrollment: yes\n"
            ),
        },
    ).json()
    grant = client.post(
        f"/wallets/{wallet['wallet_id']}/records/{record['record_id']}/grants",
        json={
            "issuer_did": "did:key:owner",
            "audience_did": "did:key:delegate",
            "issuer_key_hex": owner_key,
            "audience_key_hex": delegate_key,
            "abilities": ["record/analyze"],
            "output_types": ["redacted_extracted_text", "redacted_form_analysis"],
        },
    ).json()

    extraction_invocation = client.post(
        f"/wallets/{wallet['wallet_id']}/records/{record['record_id']}/analysis-invocations",
        json={
            "grant_id": grant["grant_id"],
            "actor_did": "did:key:delegate",
            "actor_key_hex": delegate_key,
            "output_types": ["redacted_extracted_text"],
        },
    ).json()
    extraction_response = client.post(
        f"/wallets/{wallet['wallet_id']}/records/{record['record_id']}/extract-text/redacted",
        json={
            "actor_did": "did:key:delegate",
            "actor_key_hex": delegate_key,
            "invocation_token": extraction_invocation["token"],
        },
    )
    assert extraction_response.status_code == 200
    extraction = extraction_response.json()
    extraction_output = json.dumps(extraction["output"])
    assert extraction["artifact"]["artifact_type"] == "redacted_document_text_extraction"
    assert extraction["output"]["output_policy"] == "redacted_extracted_text"
    assert "jane@example.org" not in extraction_output
    assert "503-555-1212" not in extraction_output
    assert "[REDACTED_EMAIL]" in extraction["output"]["text"]

    form_invocation = client.post(
        f"/wallets/{wallet['wallet_id']}/records/{record['record_id']}/analysis-invocations",
        json={
            "grant_id": grant["grant_id"],
            "actor_did": "did:key:delegate",
            "actor_key_hex": delegate_key,
            "output_types": ["redacted_form_analysis"],
        },
    ).json()
    form_response = client.post(
        f"/wallets/{wallet['wallet_id']}/records/{record['record_id']}/forms/analyze/redacted",
        json={
            "actor_did": "did:key:delegate",
            "actor_key_hex": delegate_key,
            "invocation_token": form_invocation["token"],
        },
    )
    assert form_response.status_code == 200
    form = form_response.json()
    form_output = json.dumps(form["output"])
    assert form["artifact"]["artifact_type"] == "redacted_document_form_analysis"
    assert form["output"]["output_policy"] == "redacted_form_analysis"
    assert form["output"]["form"]["field_count"] >= 5
    assert form["output"]["form"]["data_type_counts"]["email"] == 1
    assert form["output"]["form"]["data_type_counts"]["phone"] == 1
    assert "Jane Example" not in form_output
    assert "jane@example.org" not in form_output
    assert "503-555-1212" not in form_output

    actions = [event["action"] for event in client.get(f"/wallets/{wallet['wallet_id']}/audit").json()["events"]]
    assert "record/extract_text_redacted" in actions
    assert "record/analyze_form_redacted" in actions


def test_wallet_api_binary_document_upload_lists_record_and_storage() -> None:
    client = _client()
    owner_key = random_key().hex()
    wallet = client.post("/wallets", json={"owner_did": "did:key:owner"}).json()

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/documents",
        data={
            "actor_did": "did:key:owner",
            "key_hex": owner_key,
            "title": "Binary identity scan",
        },
        files={"file": ("identity.bin", b"\x00\x01private document bytes", "application/octet-stream")},
    )
    assert response.status_code == 200
    record = response.json()
    assert record["data_type"] == "document"

    response = client.get(f"/wallets/{wallet['wallet_id']}/records", params={"data_type": "document"})
    assert response.status_code == 200
    assert [item["record_id"] for item in response.json()["records"]] == [record["record_id"]]

    response = client.get(f"/wallets/{wallet['wallet_id']}/records/{record['record_id']}/storage")
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_wallet_api_owner_can_decrypt_document_without_grant() -> None:
    client = _client()
    owner_key = random_key().hex()
    wallet = client.post("/wallets", json={"owner_did": "did:key:owner"}).json()
    record = client.post(
        f"/wallets/{wallet['wallet_id']}/documents/text",
        json={
            "actor_did": "did:key:owner",
            "key_hex": owner_key,
            "filename": "owner-preview.txt",
            "text": "Owner can preview this stored document.",
        },
    ).json()

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/records/{record['record_id']}/decrypt",
        json={"actor_did": "did:key:owner", "actor_key_hex": owner_key},
    )

    assert response.status_code == 200
    decrypted = response.json()
    assert decrypted["text"] == "Owner can preview this stored document."
    assert decrypted["size_bytes"] == len("Owner can preview this stored document.")


def test_wallet_api_owner_creates_record_view_grant() -> None:
    client = _client()
    owner_key = random_key().hex()
    delegate_key = random_key().hex()
    wallet = client.post("/wallets", json={"owner_did": "did:key:owner"}).json()
    record = client.post(
        f"/wallets/{wallet['wallet_id']}/documents/text",
        json={
            "actor_did": "did:key:owner",
            "key_hex": owner_key,
            "filename": "share.txt",
            "text": "Owner shared this document directly.",
        },
    ).json()

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/records/{record['record_id']}/grants",
        json={
            "issuer_did": "did:key:owner",
            "audience_did": "did:key:delegate",
            "issuer_key_hex": owner_key,
            "audience_key_hex": delegate_key,
            "abilities": ["record/analyze", "record/decrypt"],
            "purpose": "benefits_application",
        },
    )
    assert response.status_code == 200
    grant = response.json()
    assert grant["abilities"] == ["record/analyze", "record/decrypt"]
    assert grant["caveats"]["purpose"] == "benefits_application"
    assert set(grant["caveats"]["output_types"]) == {"summary", "plaintext"}

    response = client.get(
        f"/wallets/{wallet['wallet_id']}/grant-receipts",
        params={"audience_did": "did:key:delegate"},
    )
    assert response.status_code == 200
    receipt = response.json()["receipts"][0]
    assert receipt["grant_id"] == grant["grant_id"]
    assert receipt["status"] == "active"

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/records/{record['record_id']}/decrypt",
        json={
            "actor_did": "did:key:delegate",
            "actor_key_hex": delegate_key,
            "grant_id": grant["grant_id"],
        },
    )
    assert response.status_code == 200
    assert response.json()["text"] == "Owner shared this document directly."


def test_wallet_api_rotates_document_key() -> None:
    service = WalletInterfaceService(services=[])
    client = _client_with_service(service)
    owner_key = random_key()
    wallet = client.post("/wallets", json={"owner_did": "did:key:owner"}).json()
    record = client.post(
        f"/wallets/{wallet['wallet_id']}/documents/text",
        json={
            "actor_did": "did:key:owner",
            "key_hex": owner_key.hex(),
            "filename": "rotation.txt",
            "text": "api rotation plaintext",
        },
    ).json()
    old_version_id = service.wallet_service.records[record["record_id"]].current_version_id

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/records/{record['record_id']}/rotate-key",
        json={"actor_did": "did:key:owner", "actor_key_hex": owner_key.hex()},
    )

    assert response.status_code == 200
    rotated = response.json()
    assert rotated["version_id"] != old_version_id
    assert rotated["record_id"] == record["record_id"]
    plaintext = service.wallet_service.decrypt_record(
        wallet["wallet_id"],
        record["record_id"],
        actor_did="did:key:owner",
        actor_secret=owner_key,
    )
    assert plaintext == b"api rotation plaintext"


def test_wallet_api_delegates_grant_with_attenuation() -> None:
    service = WalletInterfaceService(services=[])
    client = _client_with_service(service)
    wallet = client.post("/wallets", json={"owner_did": "did:key:owner"}).json()
    record = client.post(
        f"/wallets/{wallet['wallet_id']}/documents/text",
        json={
            "actor_did": "did:key:owner",
            "filename": "delegation.txt",
            "text": "api delegated analysis content",
        },
    ).json()
    resource = resource_for_record(wallet["wallet_id"], record["record_id"])
    parent = service.wallet_service.create_grant(
        wallet_id=wallet["wallet_id"],
        issuer_did="did:key:owner",
        audience_did="did:key:advocate",
        resources=[resource],
        abilities=["record/analyze", "record/share"],
        caveats={"purpose": "case_review", "max_delegation_depth": 1},
    )

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/grants/{parent.grant_id}/delegate",
        json={
            "issuer_did": "did:key:advocate",
            "audience_did": "did:key:case-manager",
            "resources": [resource],
            "abilities": ["record/analyze"],
            "caveats": {"purpose": "case_review"},
        },
    )

    assert response.status_code == 200
    child = response.json()
    assert child["proof_chain"] == [parent.grant_id]

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/records/{record['record_id']}/analyze",
        json={
            "actor_did": "did:key:case-manager",
            "grant_id": child["grant_id"],
            "max_chars": 30,
        },
    )
    assert response.status_code == 200
    assert response.json()["artifact_type"] == "summary"

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/grants/{parent.grant_id}/delegate",
        json={
            "issuer_did": "did:key:advocate",
            "audience_did": "did:key:case-manager",
            "resources": [resource],
            "abilities": ["record/decrypt"],
            "caveats": {"purpose": "case_review"},
        },
    )
    assert response.status_code == 400
    assert "exceeds parent" in response.json()["detail"]


def test_wallet_api_emergency_revoke_revokes_grants_and_rotates_records() -> None:
    service = WalletInterfaceService(services=[])
    client = _client_with_service(service)
    wallet = client.post("/wallets", json={"owner_did": "did:key:owner"}).json()
    record = client.post(
        f"/wallets/{wallet['wallet_id']}/documents/text",
        json={
            "actor_did": "did:key:owner",
            "filename": "emergency.txt",
            "text": "api emergency revoke content",
        },
    ).json()
    old_version_id = service.wallet_service.records[record["record_id"]].current_version_id
    grant = service.wallet_service.create_grant(
        wallet_id=wallet["wallet_id"],
        issuer_did="did:key:owner",
        audience_did="did:key:advocate",
        resources=[resource_for_record(wallet["wallet_id"], record["record_id"])],
        abilities=["record/analyze"],
        caveats={"purpose": "case_review"},
    )

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/emergency-revoke",
        json={"actor_did": "did:key:owner", "reason": "lost_device"},
    )

    assert response.status_code == 200
    report = response.json()
    assert report["revoked_grant_ids"] == [grant.grant_id]
    assert report["rotated_record_ids"] == [record["record_id"]]
    assert report["rotation_errors"] == {}
    assert service.wallet_service.grants[grant.grant_id].status == "revoked"
    assert service.wallet_service.records[record["record_id"]].current_version_id != old_version_id


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
            "grant_id": approved["grant_id"],
        },
    )
    assert response.status_code == 200
    decrypted = response.json()
    assert decrypted["text"] == "Delegate may view this identity document."
    assert decrypted["size_bytes"] == len("Delegate may view this identity document.")

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/records/{record['record_id']}/decrypt-invocations",
        json={
            "actor_did": "did:key:delegate",
            "actor_key_hex": delegate_key,
            "grant_id": approved["grant_id"],
        },
    )
    assert response.status_code == 200
    decrypt_invocation_token = response.json()["token"]
    assert decrypt_invocation_token.startswith("wallet-ucan-v1.")

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/records/{record['record_id']}/decrypt",
        json={
            "actor_did": "did:key:delegate",
            "actor_key_hex": delegate_key,
            "invocation_token": decrypt_invocation_token,
        },
    )
    assert response.status_code == 200
    decrypted = response.json()
    assert decrypted["text"] == "Delegate may view this identity document."
    assert decrypted["size_bytes"] == len("Delegate may view this identity document.")


def test_wallet_api_decrypt_invocation_satisfies_user_presence_caveat() -> None:
    client = _client()
    owner_key = random_key().hex()
    delegate_key = random_key().hex()
    wallet = client.post("/wallets", json={"owner_did": "did:key:owner"}).json()
    record = client.post(
        f"/wallets/{wallet['wallet_id']}/documents/text",
        json={
            "actor_did": "did:key:owner",
            "key_hex": owner_key,
            "filename": "presence.txt",
            "text": "User presence protected document.",
        },
    ).json()

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/records/{record['record_id']}/grants",
        json={
            "issuer_did": "did:key:owner",
            "audience_did": "did:key:delegate",
            "issuer_key_hex": owner_key,
            "audience_key_hex": delegate_key,
            "abilities": ["record/decrypt"],
            "purpose": "identity_verification",
            "user_presence_required": True,
        },
    )
    assert response.status_code == 200
    grant = response.json()
    assert grant["caveats"]["user_presence_required"] is True

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/records/{record['record_id']}/decrypt",
        json={
            "actor_did": "did:key:delegate",
            "actor_key_hex": delegate_key,
            "grant_id": grant["grant_id"],
        },
    )
    assert response.status_code == 400
    assert "user presence" in response.json()["detail"]

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/records/{record['record_id']}/decrypt-invocations",
        json={
            "actor_did": "did:key:delegate",
            "actor_key_hex": delegate_key,
            "grant_id": grant["grant_id"],
        },
    )
    assert response.status_code == 400
    assert "user presence" in response.json()["detail"]

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/records/{record['record_id']}/decrypt-invocations",
        json={
            "actor_did": "did:key:delegate",
            "actor_key_hex": delegate_key,
            "grant_id": grant["grant_id"],
            "purpose": "identity_verification",
            "user_present": True,
        },
    )
    assert response.status_code == 200
    invocation = response.json()["invocation"]
    invocation_token = response.json()["token"]
    assert invocation["caveats"]["purpose"] == "identity_verification"
    assert invocation["caveats"]["user_present"] is True

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/records/{record['record_id']}/decrypt",
        json={
            "actor_did": "did:key:delegate",
            "actor_key_hex": delegate_key,
            "invocation_token": invocation_token,
        },
    )
    assert response.status_code == 200
    assert response.json()["text"] == "User presence protected document."


def test_wallet_api_revoked_access_blocks_invocation() -> None:
    client = _client()
    owner_key = random_key().hex()
    delegate_key = random_key().hex()
    wallet = client.post("/wallets", json={"owner_did": "did:key:owner"}).json()
    record = client.post(
        f"/wallets/{wallet['wallet_id']}/documents/text",
        json={
            "actor_did": "did:key:owner",
            "key_hex": owner_key,
            "filename": "revoked.txt",
            "text": "Delegate access should be revoked.",
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
    approved = client.post(
        f"/wallets/{wallet['wallet_id']}/access-requests/{access_request['request_id']}/approve",
        json={
            "actor_did": "did:key:owner",
            "issuer_key_hex": owner_key,
            "audience_key_hex": delegate_key,
            "issue_invocation": True,
        },
    ).json()

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/access-requests/{access_request['request_id']}/revoke",
        json={"actor_did": "did:key:owner", "reason": "user withdrew consent"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "revoked"

    response = client.get(f"/wallets/{wallet['wallet_id']}/access-requests?status=revoked")
    assert response.status_code == 200
    assert response.json()["requests"][0]["request_id"] == access_request["request_id"]

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/records/{record['record_id']}/decrypt",
        json={
            "actor_did": "did:key:delegate",
            "actor_key_hex": delegate_key,
            "invocation_token": approved["invocation_token"],
        },
    )
    assert response.status_code == 400
    assert "not active" in response.json()["detail"]


def test_wallet_api_grant_revoke_updates_access_request_status() -> None:
    client = _client()
    owner_key = random_key().hex()
    delegate_key = random_key().hex()
    wallet = client.post("/wallets", json={"owner_did": "did:key:owner"}).json()
    record = client.post(
        f"/wallets/{wallet['wallet_id']}/documents/text",
        json={
            "actor_did": "did:key:owner",
            "key_hex": owner_key,
            "filename": "grant-revoke.txt",
            "text": "Grant revoke should update access request.",
        },
    ).json()
    access_request = client.post(
        f"/wallets/{wallet['wallet_id']}/access-requests",
        json={
            "record_id": record["record_id"],
            "requester_did": "did:key:delegate",
            "ability": "record/analyze",
            "purpose": "benefits_screening",
        },
    ).json()
    approved = client.post(
        f"/wallets/{wallet['wallet_id']}/access-requests/{access_request['request_id']}/approve",
        json={
            "actor_did": "did:key:owner",
            "issuer_key_hex": owner_key,
            "audience_key_hex": delegate_key,
        },
    ).json()

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/grants/{approved['grant_id']}/revoke",
        json={"actor_did": "did:key:owner"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "revoked"

    response = client.get(f"/wallets/{wallet['wallet_id']}/access-requests?status=revoked")
    assert response.status_code == 200
    assert response.json()["requests"][0]["request_id"] == access_request["request_id"]


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
    response = client.get(f"/wallets/{wallet['wallet_id']}/access-requests")
    assert response.status_code == 200
    review_item = response.json()["requests"][0]
    assert review_item["approval_required"] is True
    assert review_item["approval_id"] is None
    assert review_item["approval_count"] == 0
    assert review_item["grant_status"] is None

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

    response = client.get(f"/wallets/{wallet['wallet_id']}/access-requests")
    assert response.status_code == 200
    review_item = response.json()["requests"][0]
    assert review_item["approval_id"] == approval["approval_id"]
    assert review_item["approval_status"] == "pending"
    assert review_item["approval_threshold"] == 2
    assert review_item["approval_count"] == 0

    for approver in ["did:key:owner", "did:key:second-controller"]:
        response = client.post(
            f"/wallets/{wallet['wallet_id']}/approvals/{approval['approval_id']}/approve",
            json={"approver_did": approver},
        )
        assert response.status_code == 200
        approval_status = response.json()["status"]
    assert approval_status == "approved"

    response = client.get(f"/wallets/{wallet['wallet_id']}/access-requests")
    assert response.status_code == 200
    review_item = response.json()["requests"][0]
    assert review_item["approval_status"] == "approved"
    assert review_item["approval_count"] == 2

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


def test_wallet_api_wallet_admin_controller_and_device_routes() -> None:
    client = _client()
    wallet = client.post(
        "/wallets",
        json={
            "owner_did": "did:key:owner",
            "controller_dids": ["did:key:owner", "did:key:second-controller"],
            "approval_threshold": 2,
        },
    ).json()
    response = client.get(f"/wallets/{wallet['wallet_id']}")
    assert response.status_code == 200
    assert response.json()["governance_policy"]["threshold"] == 2

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/controllers",
        json={"actor_did": "did:key:owner", "controller_did": "did:key:new-controller"},
    )
    assert response.status_code == 400
    assert "approval_id is required" in response.json()["detail"]

    approval = client.post(
        f"/wallets/{wallet['wallet_id']}/approvals",
        json={
            "requested_by": "did:key:owner",
            "operation": "wallet/controller_add",
            "resources": [resource_for_wallet(wallet["wallet_id"])],
            "abilities": ["wallet/admin"],
        },
    ).json()
    for approver in ["did:key:owner", "did:key:second-controller"]:
        response = client.post(
            f"/wallets/{wallet['wallet_id']}/approvals/{approval['approval_id']}/approve",
            json={"approver_did": approver},
        )
        assert response.status_code == 200

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/controllers",
        json={
            "actor_did": "did:key:owner",
            "controller_did": "did:key:new-controller",
            "approval_id": approval["approval_id"],
        },
    )
    assert response.status_code == 200
    updated = response.json()
    assert "did:key:new-controller" in updated["controller_dids"]
    assert "did:key:new-controller" in updated["governance_policy"]["approver_dids"]

    device_wallet = client.post("/wallets", json={"owner_did": "did:key:device-owner"}).json()
    response = client.post(
        f"/wallets/{device_wallet['wallet_id']}/devices",
        json={"actor_did": "did:key:device-owner", "device_did": "did:key:phone"},
    )
    assert response.status_code == 200
    assert "did:key:phone" in response.json()["device_dids"]
    response = client.post(
        f"/wallets/{device_wallet['wallet_id']}/devices/revoke",
        json={"actor_did": "did:key:device-owner", "device_did": "did:key:phone"},
    )
    assert response.status_code == 200
    assert "did:key:phone" not in response.json()["device_dids"]


def test_wallet_api_recovery_policy_and_controller_recovery() -> None:
    client = _client()
    wallet = client.post(
        "/wallets",
        json={
            "owner_did": "did:key:owner",
            "controller_dids": ["did:key:owner", "did:key:second-controller"],
            "approval_threshold": 2,
        },
    ).json()
    wallet_resource = resource_for_wallet(wallet["wallet_id"])
    recovery_contacts = ["did:key:recovery-a", "did:key:recovery-b"]

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/recovery-policy",
        json={
            "actor_did": "did:key:owner",
            "contact_dids": recovery_contacts,
            "threshold": 2,
        },
    )
    assert response.status_code == 400
    assert "approval_id is required" in response.json()["detail"]

    approval = client.post(
        f"/wallets/{wallet['wallet_id']}/approvals",
        json={
            "requested_by": "did:key:owner",
            "operation": "wallet/recovery_policy_set",
            "resources": [wallet_resource],
            "abilities": ["wallet/admin"],
        },
    ).json()
    for approver in ["did:key:owner", "did:key:second-controller"]:
        response = client.post(
            f"/wallets/{wallet['wallet_id']}/approvals/{approval['approval_id']}/approve",
            json={"approver_did": approver},
        )
        assert response.status_code == 200

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/recovery-policy",
        json={
            "actor_did": "did:key:owner",
            "contact_dids": recovery_contacts,
            "threshold": 2,
            "approval_id": approval["approval_id"],
        },
    )
    assert response.status_code == 200
    assert response.json()["governance_policy"]["recovery_policy"]["contact_dids"] == recovery_contacts

    recovery_approval = client.post(
        f"/wallets/{wallet['wallet_id']}/approvals",
        json={
            "requested_by": recovery_contacts[0],
            "operation": "wallet/controller_recover",
            "resources": [wallet_resource],
            "abilities": ["wallet/admin"],
        },
    ).json()
    assert recovery_approval["threshold"] == 2
    assert recovery_approval["approver_dids"] == recovery_contacts

    for approver in recovery_contacts:
        response = client.post(
            f"/wallets/{wallet['wallet_id']}/approvals/{recovery_approval['approval_id']}/approve",
            json={"approver_did": approver},
        )
        assert response.status_code == 200

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/controllers/recover",
        json={
            "actor_did": recovery_contacts[0],
            "controller_did": "did:key:recovered-controller",
            "approval_id": recovery_approval["approval_id"],
        },
    )
    assert response.status_code == 200
    assert "did:key:recovered-controller" in response.json()["controller_dids"]


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

    response = client.get(f"/wallets/{wallet['wallet_id']}/storage")
    assert response.status_code == 200
    wallet_report = response.json()
    assert wallet_report["ok"] is True
    assert wallet_report["record_count"] == 1
    assert wallet_report["replica_count"] == 2
    assert wallet_report["storage_types"] == {"memory": 2}
    assert wallet_report["reports"][0]["record_id"] == record["record_id"]

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/storage/repair",
        json={"actor_did": "did:key:owner"},
    )
    assert response.status_code == 200
    wallet_repair = response.json()
    assert wallet_repair["ok"] is True
    assert wallet_repair["repaired_replica_count"] == 0

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/records/{record['record_id']}/storage/repair",
        json={"actor_did": "did:key:owner"},
    )
    assert response.status_code == 200
    repair = response.json()
    assert repair["ok"] is True

    response = client.get(f"/wallets/{wallet['wallet_id']}/audit")
    actions = [event["action"] for event in response.json()["events"]]
    assert "storage/verify_wallet" in actions
    assert "storage/repair_wallet" in actions
    assert "storage/repair" in actions


def test_wallet_api_ops_health_reports_repository_storage_and_audits(tmp_path) -> None:
    service = WalletInterfaceService(repository_root=tmp_path / "wallet-repository")
    client = _client_with_service(service)
    wallet = client.post("/wallets", json={"owner_did": "did:key:owner"}).json()
    response = client.post(
        f"/wallets/{wallet['wallet_id']}/documents/text",
        json={
            "actor_did": "did:key:owner",
            "filename": "ops-health.txt",
            "text": "ops health document",
        },
    )
    assert response.status_code == 200

    response = client.get("/ops/health", params={"verify_storage": "true"})
    assert response.status_code == 200
    report = response.json()
    checks = {check["name"]: check for check in report["checks"]}

    assert report["status"] in {"ok", "warning"}
    assert checks["repository"]["status"] == "ok"
    assert checks["storage_availability"]["status"] == "ok"
    assert checks["storage_availability"]["details"]["verified"] is True
    assert checks["revocation_propagation"]["status"] == "ok"
    assert checks["privacy_budget"]["status"] == "ok"

    response = client.get(f"/wallets/{wallet['wallet_id']}/audit")
    actions = [event["action"] for event in response.json()["events"]]
    assert "ops/health" in actions

    restored = WalletInterfaceService(
        repository_root=tmp_path / "wallet-repository",
        auto_load_repository=True,
    )
    restored_actions = [
        event.action for event in restored.wallet_service.get_audit_log(wallet["wallet_id"])
    ]
    assert "ops/health" in restored_actions


def test_wallet_api_ops_health_requires_shared_secret_when_configured(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("WALLET_OPS_HEALTH_SHARED_SECRET", "top-secret")
    service = WalletInterfaceService(repository_root=tmp_path / "wallet-repository")
    client = _client_with_service(service)

    unauthorized = client.get("/ops/health")
    assert unauthorized.status_code == 401
    assert "authorization required" in unauthorized.json()["detail"]

    wrong_secret = client.get(
        "/ops/health",
        headers={"authorization": "Bearer wrong-secret"},
    )
    assert wrong_secret.status_code == 401

    authorized = client.get(
        "/ops/health",
        headers={"authorization": "Bearer top-secret"},
    )
    assert authorized.status_code == 200
    assert authorized.json()["status"] in {"ok", "warning"}


def test_wallet_api_ops_health_accepts_shared_secret_header(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("WALLET_OPS_HEALTH_SHARED_SECRET", "edge-secret")
    service = WalletInterfaceService(repository_root=tmp_path / "wallet-repository")
    client = _client_with_service(service)

    response = client.get(
        "/ops/health",
        headers={"x-wallet-ops-shared-secret": "edge-secret"},
    )
    assert response.status_code == 200
    assert response.json()["check_count"] >= 1


def test_wallet_api_missing_person_dead_drop_email_uses_server_smtp(monkeypatch) -> None:
    class FakeSmtpClient:
        sent_messages = []

        def __init__(self, host: str, port: int, timeout: int) -> None:
            self.host = host
            self.port = port
            self.timeout = timeout
            self.starttls_called = False

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def starttls(self) -> None:
            self.starttls_called = True

        def login(self, username: str, password: str) -> None:
            return None

        def send_message(self, message):
            self.__class__.sent_messages.append(message)
            return {}

    monkeypatch.delenv("WALLET_DEAD_DROP_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("WALLET_DEAD_DROP_BACKEND", raising=False)
    monkeypatch.setenv("WALLET_DEAD_DROP_SMTP_HOST", "smtp.example.org")
    monkeypatch.setenv("WALLET_DEAD_DROP_FROM_EMAIL", "abby@example.org")
    monkeypatch.setattr(wallet_api_module.smtplib, "SMTP", FakeSmtpClient)
    client = _client()
    wallet = client.post("/wallets", json={"owner_did": "did:key:owner"}).json()

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/dead-drops/missing-person",
        json={
            "actor_did": "did:key:owner",
            "to_email": "missing@police.portlandoregon.gov",
            "subject": "Missing person report dead drop bundle",
            "body": "Please review attached wallet bundle.",
            "bundle": {"schemaVersion": "abby-missing-person-dead-drop-v1", "walletContents": []},
            "bundle_filename": "dead-drop.json",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "sent"
    assert payload["to_email"] == "missing@police.portlandoregon.gov"
    assert payload["bundle_filename"] == "dead-drop.json"
    assert payload["message_id"]
    assert len(FakeSmtpClient.sent_messages) == 1
    sent_message = FakeSmtpClient.sent_messages[0]
    attachment = next(sent_message.iter_attachments())
    assert sent_message["To"] == "missing@police.portlandoregon.gov"
    assert sent_message["Subject"] == "Missing person report dead drop bundle"
    assert attachment.get_filename() == "dead-drop.json"


def test_wallet_api_missing_person_dead_drop_email_uses_http_bridge(monkeypatch) -> None:
    captured_requests = []

    class FakeResponse:
        def __init__(self, payload: dict[str, object]) -> None:
            self.payload = payload
            self.headers = {"content-type": "application/json"}
            self.status = 202

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps(self.payload).encode("utf-8")

    def fake_urlopen(request, timeout: float):
        captured_requests.append(
            {
                "url": request.full_url,
                "headers": dict(request.header_items()),
                "payload": json.loads(request.data.decode("utf-8")),
                "timeout": timeout,
            }
        )
        return FakeResponse({"provider_message_id": "email-123", "provider": "bridge", "status": "accepted"})

    monkeypatch.setenv("WALLET_DEAD_DROP_BACKEND", "http")
    monkeypatch.setenv("WALLET_DEAD_DROP_WEBHOOK_URL", "https://bridge.example/messages/email/outbound")
    monkeypatch.setenv("WALLET_DEAD_DROP_FROM_EMAIL", "abby@example.org")
    monkeypatch.setattr(wallet_api_module.urllib_request, "urlopen", fake_urlopen)
    client = _client()
    wallet = client.post("/wallets", json={"owner_did": "did:key:owner"}).json()

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/dead-drops/missing-person",
        json={
            "actor_did": "did:key:owner",
            "to_email": "missing@police.portlandoregon.gov",
            "subject": "Missing person report dead drop bundle",
            "body": "Please review attached wallet bundle.",
            "bundle": {"schemaVersion": "abby-missing-person-dead-drop-v1", "walletContents": []},
            "bundle_filename": "dead-drop.json",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "sent"
    assert payload["message_id"] == "email-123"
    assert len(captured_requests) == 1
    request_payload = captured_requests[0]["payload"]
    assert captured_requests[0]["url"] == "https://bridge.example/messages/email/outbound"
    assert request_payload["to_email"] == "missing@police.portlandoregon.gov"
    assert request_payload["from_email"] == "abby@example.org"
    assert request_payload["subject"] == "Missing person report dead drop bundle"
    assert request_payload["attachment_filename"] == "dead-drop.json"
    assert request_payload["attachment_mime_type"] == "application/json"
    decoded_attachment = json.loads(base64.b64decode(request_payload["attachment_base64"]).decode("utf-8"))
    assert decoded_attachment["schemaVersion"] == "abby-missing-person-dead-drop-v1"


def test_wallet_api_missing_person_dead_drop_email_requires_smtp_config(monkeypatch) -> None:
    monkeypatch.delenv("WALLET_DEAD_DROP_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("WALLET_DEAD_DROP_BACKEND", raising=False)
    monkeypatch.delenv("WALLET_DEAD_DROP_SMTP_HOST", raising=False)
    client = _client()
    wallet = client.post("/wallets", json={"owner_did": "did:key:owner"}).json()

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/dead-drops/missing-person",
        json={
            "actor_did": "did:key:owner",
            "to_email": "missing@police.portlandoregon.gov",
            "subject": "Missing person report dead drop bundle",
            "body": "Please review attached wallet bundle.",
            "bundle": {"schemaVersion": "abby-missing-person-dead-drop-v1", "walletContents": []},
            "bundle_filename": "dead-drop.json",
        },
    )

    assert response.status_code == 503
    assert "WALLET_DEAD_DROP_SMTP_HOST" in response.json()["detail"]


def test_wallet_api_missing_person_dead_drop_config_processes_due_and_persists(tmp_path, monkeypatch) -> None:
    class FakeSmtpClient:
        sent_messages = []

        def __init__(self, host: str, port: int, timeout: int) -> None:
            self.host = host
            self.port = port
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def starttls(self) -> None:
            return None

        def login(self, username: str, password: str) -> None:
            return None

        def send_message(self, message):
            self.__class__.sent_messages.append(message)
            return {}

    monkeypatch.delenv("WALLET_DEAD_DROP_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("WALLET_DEAD_DROP_BACKEND", raising=False)
    monkeypatch.setenv("WALLET_DEAD_DROP_SMTP_HOST", "smtp.example.org")
    monkeypatch.setenv("WALLET_DEAD_DROP_FROM_EMAIL", "abby@example.org")
    monkeypatch.setenv("WALLET_OPS_HEALTH_SHARED_SECRET", "ops-secret")
    monkeypatch.setattr(wallet_api_module.smtplib, "SMTP", FakeSmtpClient)
    service = WalletInterfaceService(repository_root=tmp_path / "wallet-repository", services=[])
    client = _client_with_service(service)
    wallet = client.post("/wallets", json={"owner_did": "did:key:owner"}).json()

    configure_response = client.put(
        f"/wallets/{wallet['wallet_id']}/dead-drops/missing-person",
        json={
            "actor_did": "did:key:owner",
            "enabled": True,
            "to_email": "missing@police.portlandoregon.gov",
            "subject": "Missing person report dead drop bundle",
            "body": "Please review attached wallet bundle.",
            "bundle": {"schemaVersion": "abby-missing-person-dead-drop-v1", "walletContents": []},
            "bundle_filename": "dead-drop.json",
            "due_at": "2024-01-01T00:00:00Z",
            "last_check_in_at": "2023-12-30T00:00:00Z",
        },
    )

    assert configure_response.status_code == 200
    assert configure_response.json()["enabled"] is True

    process_response = client.post(
        "/ops/dead-drops/missing-person/process-due",
        headers={"x-wallet-ops-shared-secret": "ops-secret"},
    )

    assert process_response.status_code == 200
    payload = process_response.json()
    assert payload["due_count"] == 1
    assert payload["sent_count"] == 1
    assert payload["failed_count"] == 0
    assert len(FakeSmtpClient.sent_messages) == 1

    state_response = client.get(f"/wallets/{wallet['wallet_id']}/dead-drops/missing-person")
    assert state_response.status_code == 200
    state_payload = state_response.json()
    assert state_payload["last_sent_for_check_in_at"] == "2023-12-30T00:00:00Z"
    assert state_payload["last_message_id"]

    snapshot_response = client.post(f"/wallets/{wallet['wallet_id']}/snapshot")
    assert snapshot_response.status_code == 200

    restored_service = WalletInterfaceService(repository_root=tmp_path / "wallet-repository", services=[])
    restored_client = _client_with_service(restored_service)
    load_response = restored_client.post("/wallets/snapshots/load-all")
    assert load_response.status_code == 200

    restored_state = restored_client.get(f"/wallets/{wallet['wallet_id']}/dead-drops/missing-person")
    assert restored_state.status_code == 200
    assert restored_state.json()["last_message_id"] == state_payload["last_message_id"]
    assert restored_state.json()["enabled"] is True


def test_wallet_api_sms_notification_queue_and_manual_dispatch_uses_http_webhook(monkeypatch) -> None:
    captured_requests = []

    class FakeResponse:
        def __init__(self, payload: dict[str, object]) -> None:
            self.payload = payload
            self.headers = {"content-type": "application/json"}
            self.status = 202

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps(self.payload).encode("utf-8")

    def fake_urlopen(request, timeout: float):
        captured_requests.append(
            {
                "url": request.full_url,
                "headers": dict(request.header_items()),
                "payload": json.loads(request.data.decode("utf-8")),
                "timeout": timeout,
            }
        )
        return FakeResponse({"message_id": "sms-123", "provider": "test-webhook", "status": "accepted"})

    monkeypatch.setenv("WALLET_SMS_WEBHOOK_URL", "https://sms.example.org/send")
    monkeypatch.setenv("WALLET_SMS_BEARER_TOKEN", "sms-secret")
    monkeypatch.setattr(wallet_api_module.urllib_request, "urlopen", fake_urlopen)
    client = _client()
    wallet = client.post("/wallets", json={"owner_did": "did:key:owner"}).json()

    queue_response = client.post(
        f"/wallets/{wallet['wallet_id']}/notifications/sms/queue",
        json={
            "actor_did": "did:key:owner",
            "to_phone": "(503) 555-0123",
            "message": "Bring your ID to the front desk.",
            "reason": "intake-reminder",
        },
    )

    assert queue_response.status_code == 200
    queued = queue_response.json()
    assert queued["status"] == "queued"
    assert queued["to_phone"] == "5035550123"

    dispatch_response = client.post(
        f"/wallets/{wallet['wallet_id']}/notifications/sms/{queued['notification_id']}/dispatch",
        json={"actor_did": "did:key:owner"},
    )

    assert dispatch_response.status_code == 200
    payload = dispatch_response.json()
    assert payload["status"] == "sent"
    assert payload["provider"] == "test-webhook"
    assert payload["provider_message_id"] == "sms-123"
    assert payload["notification"]["status"] == "sent"
    assert len(captured_requests) == 1
    assert captured_requests[0]["url"] == "https://sms.example.org/send"
    assert captured_requests[0]["headers"]["Authorization"] == "Bearer sms-secret"
    assert captured_requests[0]["payload"] == {
        "to_phone": "5035550123",
        "message": "Bring your ID to the front desk.",
        "wallet_id": wallet["wallet_id"],
        "external_reference": queued["notification_id"],
        "metadata": {
            "notification_id": queued["notification_id"],
            "reason": "intake-reminder",
        },
    }

    list_response = client.get(f"/wallets/{wallet['wallet_id']}/notifications/sms")
    assert list_response.status_code == 200
    assert list_response.json()["count"] == 1
    assert list_response.json()["notifications"][0]["last_provider_message_id"] == "sms-123"


def test_wallet_api_sms_notification_processes_due_and_persists(tmp_path, monkeypatch) -> None:
    class FakeResponse:
        def __init__(self, payload: dict[str, object]) -> None:
            self.payload = payload
            self.headers = {"content-type": "application/json"}
            self.status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps(self.payload).encode("utf-8")

    delivery_ids: list[str] = []

    def fake_urlopen(request, timeout: float):
        delivery_ids.append(json.loads(request.data.decode("utf-8"))["to_phone"])
        return FakeResponse({"message_id": f"sms-{len(delivery_ids)}", "status": "accepted"})

    monkeypatch.setenv("WALLET_SMS_WEBHOOK_URL", "https://sms.example.org/send")
    monkeypatch.setenv("WALLET_OPS_HEALTH_SHARED_SECRET", "ops-secret")
    monkeypatch.setattr(wallet_api_module.urllib_request, "urlopen", fake_urlopen)
    service = WalletInterfaceService(repository_root=tmp_path / "wallet-repository", services=[])
    client = _client_with_service(service)
    wallet = client.post("/wallets", json={"owner_did": "did:key:owner"}).json()

    queue_response = client.post(
        f"/wallets/{wallet['wallet_id']}/notifications/sms/queue",
        json={
            "actor_did": "did:key:owner",
            "to_phone": "+1 (503) 555-0123",
            "message": "Please reply YES to confirm your safety check-in.",
            "due_at": "2024-01-01T00:00:00Z",
            "reason": "safety-check-in",
        },
    )

    assert queue_response.status_code == 200

    process_response = client.post(
        "/ops/notifications/sms/process-due",
        headers={"x-wallet-ops-shared-secret": "ops-secret"},
    )

    assert process_response.status_code == 200
    payload = process_response.json()
    assert payload["due_count"] == 1
    assert payload["sent_count"] == 1
    assert payload["failed_count"] == 0
    assert delivery_ids == ["+15035550123"]

    state_response = client.get(f"/wallets/{wallet['wallet_id']}/notifications/sms")
    assert state_response.status_code == 200
    state_payload = state_response.json()["notifications"][0]
    assert state_payload["status"] == "sent"
    assert state_payload["last_provider_message_id"] == "sms-1"

    restored_service = WalletInterfaceService(repository_root=tmp_path / "wallet-repository", services=[])
    restored_client = _client_with_service(restored_service)
    load_response = restored_client.post("/wallets/snapshots/load-all")
    assert load_response.status_code == 200

    restored_state = restored_client.get(f"/wallets/{wallet['wallet_id']}/notifications/sms")
    assert restored_state.status_code == 200
    restored_payload = restored_state.json()["notifications"][0]
    assert restored_payload["status"] == "sent"
    assert restored_payload["last_provider_message_id"] == "sms-1"


def test_wallet_api_inbound_sms_bridge_records_message_and_persists(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("WALLET_SMS_INBOUND_BEARER_TOKEN", "bridge-secret")
    service = WalletInterfaceService(repository_root=tmp_path / "wallet-repository", services=[])
    client = _client_with_service(service)
    wallet = client.post("/wallets", json={"owner_did": "did:key:owner"}).json()

    queue_response = client.post(
        f"/wallets/{wallet['wallet_id']}/notifications/sms/queue",
        json={
            "actor_did": "did:key:owner",
            "to_phone": "+1 (503) 555-0123",
            "message": "Please reply YES to confirm your safety check-in.",
            "reason": "safety-check-in",
        },
    )
    assert queue_response.status_code == 200
    queued = queue_response.json()

    inbound_response = client.post(
        "/messages/sms/inbound",
        headers={"authorization": "Bearer bridge-secret"},
        json={
            "message_id": "sms-bridge-1",
            "wallet_id": wallet["wallet_id"],
            "from_phone": "+15035550123",
            "to_phone": "+15035550100",
            "message": "YES",
            "provider": "twilio",
            "provider_message_id": "SM-inbound-1",
            "external_reference": queued["notification_id"],
            "created_at": "2026-05-13T00:00:00+00:00",
            "metadata": {"account_sid": "AC123"},
        },
    )

    assert inbound_response.status_code == 200
    inbound_message = inbound_response.json()["message"]
    assert inbound_message["wallet_id"] == wallet["wallet_id"]
    assert inbound_message["bridge_message_id"] == "sms-bridge-1"
    assert inbound_message["provider_message_id"] == "SM-inbound-1"
    assert inbound_message["related_notification_id"] == queued["notification_id"]
    assert inbound_message["received_at"] == "2026-05-13T00:00:00+00:00"
    phone_cid = phone_identity_cid("+15035550123")
    assert inbound_message["metadata"]["phoneIdentityCids"]["from_phone"] == phone_cid
    assert phone_cid in service.phone_identity_links
    assert wallet["wallet_id"] in service.phone_identity_links[phone_cid]

    list_response = client.get(f"/wallets/{wallet['wallet_id']}/messages/sms/inbound")
    assert list_response.status_code == 200
    assert list_response.json()["count"] == 1
    assert list_response.json()["messages"][0]["message"] == "YES"

    restored_service = WalletInterfaceService(repository_root=tmp_path / "wallet-repository", services=[])
    restored_client = _client_with_service(restored_service)
    load_response = restored_client.post("/wallets/snapshots/load-all")
    assert load_response.status_code == 200

    restored_list = restored_client.get(f"/wallets/{wallet['wallet_id']}/messages/sms/inbound")
    assert restored_list.status_code == 200
    assert restored_list.json()["count"] == 1
    assert restored_list.json()["messages"][0]["related_notification_id"] == queued["notification_id"]


def test_wallet_api_inbound_sms_bridge_accepts_unclaimed_public_sms(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("WALLET_SMS_INBOUND_BEARER_TOKEN", "bridge-secret")
    service = WalletInterfaceService(repository_root=tmp_path / "wallet-repository", services=[])
    client = _client_with_service(service)

    inbound_response = client.post(
        "/messages/sms/inbound",
        headers={"authorization": "Bearer bridge-secret"},
        json={
            "message_id": "sms-bridge-unclaimed-1",
            "wallet_id": "",
            "from_phone": "+15035550123",
            "to_phone": "+15036838900",
            "message": "I need help finding food nearby.",
            "provider": "twilio",
            "provider_message_id": "SM-unclaimed-1",
            "created_at": "2026-05-18T21:00:00+00:00",
            "metadata": {"account_sid": "AC123"},
        },
    )

    assert inbound_response.status_code == 200
    inbound_message = inbound_response.json()["message"]
    assert inbound_message["wallet_id"] == ""
    assert inbound_message["bridge_message_id"] == "sms-bridge-unclaimed-1"
    assert inbound_message["provider_message_id"] == "SM-unclaimed-1"
    assert inbound_message["metadata"]["phoneIdentityCids"]["from_phone"] == phone_identity_cid("+15035550123")

    restored_service = WalletInterfaceService(repository_root=tmp_path / "wallet-repository", services=[])
    assert any(
        record.provider_message_id == "SM-unclaimed-1"
        for record in restored_service.inbound_sms_messages.values()
    )


def test_wallet_api_inbound_sms_bridge_resolves_wallet_by_phone_identity_cid(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("WALLET_SMS_INBOUND_BEARER_TOKEN", "bridge-secret")
    service = WalletInterfaceService(repository_root=tmp_path / "wallet-repository", services=[])
    client = _client_with_service(service)
    wallet = client.post("/wallets", json={"owner_did": "did:key:owner"}).json()

    queue_response = client.post(
        f"/wallets/{wallet['wallet_id']}/notifications/sms/queue",
        json={
            "actor_did": "did:key:owner",
            "to_phone": "+1 (503) 555-0199",
            "message": "Initial opt-in message.",
            "reason": "identity-link",
        },
    )
    assert queue_response.status_code == 200
    phone_cid = phone_identity_cid("+15035550199")
    assert queue_response.json()["metadata"]["phoneIdentityCids"]["to_phone"] == phone_cid

    inbound_response = client.post(
        "/messages/sms/inbound",
        headers={"authorization": "Bearer bridge-secret"},
        json={
            "message_id": "sms-bridge-resolved-1",
            "wallet_id": "",
            "from_phone": "+15035550199",
            "to_phone": "+15036838900",
            "message": "This should attach to my wallet.",
            "provider": "twilio",
            "provider_message_id": "SM-resolved-1",
        },
    )

    assert inbound_response.status_code == 200
    inbound_message = inbound_response.json()["message"]
    assert inbound_message["wallet_id"] == wallet["wallet_id"]
    assert inbound_message["metadata"]["phoneIdentityCids"]["from_phone"] == phone_cid

    restored_service = WalletInterfaceService(repository_root=tmp_path / "wallet-repository", services=[])
    assert restored_service.phone_identity_links[phone_cid] == [wallet["wallet_id"]]


def test_indextts_proxy_caches_config_fn_index_and_default_reference(monkeypatch) -> None:
    wallet_api_module._INDEXTTS_CONFIG_CACHE.clear()
    wallet_api_module._INDEXTTS_FN_INDEX_CACHE.clear()
    wallet_api_module._INDEXTTS_REFERENCE_CACHE.clear()

    calls = {"config": 0, "join": 0, "upload": 0, "wait": 0, "fetch": 0}

    class FakeClient:
        def get_config(self) -> dict[str, object]:
            calls["config"] += 1
            return {"dependencies": [{"id": 17, "api_name": "/gen_single"}]}

        def resolve_fn_index(self, api_name: str, config: Mapping[str, object], *, fallback_markers=()):
            return 17

        def upload_file(self, file_name: str, data: bytes, mime_type: str) -> dict[str, object]:
            calls["upload"] += 1
            return {"path": "/tmp/abby-reference.wav", "meta": {"_type": "gradio.FileData"}, "orig_name": file_name}

        def queue_join(self, fn_index: int, data: Sequence[object], *, session_hash: str | None = None) -> str:
            calls["join"] += 1
            assert fn_index == 17
            return session_hash or "session-123"

        def wait_for_queue_result(self, session_hash: str, *, timeout_seconds: float | None = None, poll_interval_seconds: float = 0.5) -> dict[str, object]:
            calls["wait"] += 1
            return {"path": "/tmp/out.wav"}

        def fetch_file(self, reference: object, *, accept: str = "audio/*, application/octet-stream") -> tuple[bytes, str]:
            calls["fetch"] += 1
            return b"RIFFstubWAVE", "audio/wav"

    monkeypatch.setenv("WALLET_INDEXTTS_SPACE_URL", "https://example.test")
    monkeypatch.setenv("WALLET_INDEXTTS_API_NAME", "gen_single")
    monkeypatch.setattr(wallet_api_module, "_indextts_space_client", lambda: FakeClient())

    first = wallet_api_module._run_indextts_gradio_tts(text="hello")
    second = wallet_api_module._run_indextts_gradio_tts(text="again")

    assert first["latency"]["total_ms"] >= 0
    assert second["latency"]["config_ms"] == 0
    assert calls == {"config": 1, "join": 2, "upload": 1, "wait": 2, "fetch": 2}


def test_indextts_spoken_text_normalizes_numbers_and_address_abbreviations() -> None:
    assert wallet_api_module._normalize_indextts_spoken_text("Call 911, then ask 211-ai.") == (
        "Call nine one one, then ask two one one AI."
    )
    assert wallet_api_module._normalize_indextts_spoken_text("Meet at SE 32nd ave, apt #4.") == (
        "Meet at South East thirty second Avenue, Apartment 4."
    )
    assert wallet_api_module._normalize_indextts_spoken_text("Shelter: S.E. 82nd Ave Ste 10") == (
        "Shelter: South East eighty second Avenue Suite 10"
    )
    assert wallet_api_module._normalize_indextts_spoken_text(
        "Write this down: 8800 Southeast 8 0th Avenue, Portland."
    ) == "Write this down: 8800 Southeast eightieth Avenue, Portland."
    assert wallet_api_module._normalize_indextts_spoken_text("Food help near N.W. 23rd Pl and SW 4th St.") == (
        "Food help near North West twenty third Place and South West fourth Street."
    )
    assert wallet_api_module._normalize_indextts_spoken_text(
        "Source: https://www.211info.org/agency/1439/14182/. Confirm details before traveling."
    ) == "Confirm details before traveling."
    assert wallet_api_module._normalize_indextts_spoken_text(
        "Visit https://gethelp.211info.org/get-help/food/ or call 211."
    ) == "Visit the two one one info website or call two one one."
    assert wallet_api_module._normalize_indextts_spoken_text(
        "Phone: phone not listed in this record. Eligibility: eligibility not listed in this record. Visit website."
    ) == ""
    assert wallet_api_module._normalize_indextts_spoken_text(
        "A grounded 211 match is FOOD PANTRY. Source: https://www.211info.org/agency/1439/14182/. Confirm details before traveling."
    ) == "I found Food Pantry. Confirm details before traveling."
    assert wallet_api_module._normalize_indextts_spoken_text(
        "A grounded 211 match is EYE CLINIC. The record lists 120 minutes. 222 SE 8th Avenue Suite 110 Hillsboro, OR 97123. Phone: (503) 352-7300."
    ) == "I found Eye Clinic. The address is 222 South East eighth Avenue Suite 110, Hillsboro, Oregon. ZIP code nine seven one two three. You can call five zero three, three five two, seven three zero zero."
    assert wallet_api_module._normalize_indextts_spoken_text(
        "Mail goes to Portland, OR 97206-1234 or use 97204."
    ) == "Mail goes to Portland, Oregon. ZIP code nine seven two zero six dash one two three four or use nine seven two zero four."
    assert wallet_api_module._normalize_indextts_spoken_text(
        "Try 450 Highway 99 N Eugene, OR 97402, 1400 Queen Avenue SE Suite 201 Albany, OR 97322, or 15325 NW Central Drive Suite J-8 Portland, OR 97229."
    ) == (
        "Try 450 Highway ninety nine North Eugene, Oregon. ZIP code nine seven four zero two, "
        "1400 Queen Avenue South East Suite 201, Albany, Oregon. ZIP code nine seven three two two, "
        "or 15325 North West Central Drive Suite J-8, Portland, Oregon. ZIP code nine seven two two nine."
    )
    assert wallet_api_module._normalize_indextts_spoken_text(
        "Ages 18-24 who are fleeing domestic violence."
    ) == "Ages eighteen to twenty four who are fleeing domestic violence."
    assert wallet_api_module._normalize_indextts_spoken_text(
        "The office is at 101 E Broadway Suite 200 Eugene, OR 97401."
    ) == "The office is at 101 East Broadway Suite 200, Eugene, Oregon. ZIP code nine seven four zero one."
    assert wallet_api_module._normalize_indextts_spoken_text(
        "Monday/Wednesday 8:30am - 4:30pm, call (503) 771-7914, income 80-100% AMI, up to $500."
    ) == (
        "Monday, Wednesday 8:30 AM to 4:30 PM, call five zero three, seven seven one, seven nine one four, "
        "income eighty to one hundred percent AMI, up to five hundred dollars."
    )
    assert wallet_api_module._normalize_indextts_spoken_text(
        "Monday/Wednesday/Thursday 1:15pm-3:45pm"
    ) == "Monday, Wednesday, Thursday 1:15 PM to 3:45 PM"
    assert wallet_api_module._normalize_indextts_spoken_text(
        "-Drop-in Center: 7 days per week 8:30am-5pm"
    ) == "Drop-in Center: 7 days per week 8:30 AM to 5 PM"
    assert wallet_api_module._normalize_indextts_spoken_text(
        "Must have served post 9/11 and be eligible."
    ) == "Must have served post September eleventh and be eligible."
    assert wallet_api_module._normalize_indextts_spoken_text(
        "223 SE M Street Grants Pass, OR 97526"
    ) == "223 South East M Street, Grants Pass, Oregon. ZIP code nine seven five two six"
    assert wallet_api_module._normalize_indextts_spoken_text(
        "6329 NE Martin Luther King Jr Boulevard Portland, OR 97211"
    ) == "6329 North East Martin Luther King Jr Boulevard, Portland, Oregon. ZIP code nine seven two one one"
    assert wallet_api_module._normalize_indextts_spoken_text(
        "51 W Washington Burns, OR 97720"
    ) == "51 West Washington Burns, Oregon. ZIP code nine seven seven two zero"
    assert wallet_api_module._normalize_indextts_spoken_text(
        "Laundry Facilities * Homeless Youth - 211info"
    ) == "Laundry Facilities for Homeless Youth"
    assert wallet_api_module._normalize_indextts_spoken_text(
        "24 hours per day / 7 days a week"
    ) == "24 hours per day, 7 days a week"
    assert wallet_api_module._normalize_indextts_spoken_text(
        "29796 SW Town Center Loop E Wilsonville, OR 97070"
    ) == "29796 South West Town Center Loop East, Wilsonville, Oregon. ZIP code nine seven zero seven zero"
    assert wallet_api_module._normalize_indextts_spoken_text(
        "ST VINCENT DE PAUL Email (541) 536-1956 Get Directions Visit Website More Details Print & Share X Print & Share Print PDF"
    ) == "Saint VINCENT DE PAUL"
    assert wallet_api_module._normalize_indextts_spoken_text(
        "ST VINCENT DE PAUL OF LANE COUNTY"
    ) == "Saint VINCENT DE PAUL OF LANE COUNTY"
    assert wallet_api_module._normalize_indextts_spoken_text(
        "The record lists latitude: 45.5152 longitude: -122.6784. Source: https://example.org/a."
    ) == ""
    assert wallet_api_module._normalize_indextts_spoken_text(
        "Phone: (541) 485-1017, (541) 485-1017 ext 100."
    ) == "You can call five four one, four eight five, one zero one seven, extension one zero zero."
    assert wallet_api_module._normalize_indextts_spoken_text(
        "Eligibility: Unrestricted. Varies by program."
    ) == "Eligibility varies by program."
    assert wallet_api_module._normalize_indextts_spoken_text(
        "Eligibility: Low income individuals age 18 and older. Unrestricted."
    ) == "Eligibility: Low income individuals age eighteen and older."


def test_indextts_proxy_sends_normalized_speech_text(monkeypatch) -> None:
    wallet_api_module._INDEXTTS_CONFIG_CACHE.clear()
    wallet_api_module._INDEXTTS_FN_INDEX_CACHE.clear()
    wallet_api_module._INDEXTTS_REFERENCE_CACHE.clear()

    queued_payloads: list[tuple[int, list[object]]] = []

    class FakeClient:
        def get_config(self) -> dict[str, object]:
            return {"dependencies": [{"id": 17, "api_name": "/gen_single"}]}

        def resolve_fn_index(self, api_name: str, config: Mapping[str, object], *, fallback_markers=()):
            return 17

        def upload_file(self, file_name: str, data: bytes, mime_type: str) -> dict[str, object]:
            return {"path": "/tmp/abby-reference.wav", "meta": {"_type": "gradio.FileData"}, "orig_name": file_name}

        def queue_join(self, fn_index: int, data: Sequence[object], *, session_hash: str | None = None) -> str:
            queued_payloads.append((fn_index, list(data)))
            return session_hash or "session-123"

        def wait_for_queue_result(self, session_hash: str, *, timeout_seconds: float | None = None, poll_interval_seconds: float = 0.5) -> dict[str, object]:
            return {"path": "/tmp/out.wav"}

        def fetch_file(self, reference: object, *, accept: str = "audio/*, application/octet-stream") -> tuple[bytes, str]:
            return b"RIFFstubWAVE", "audio/wav"

    monkeypatch.setenv("WALLET_INDEXTTS_SPACE_URL", "https://example.test")
    monkeypatch.setenv("WALLET_INDEXTTS_API_NAME", "gen_single")
    monkeypatch.setattr(wallet_api_module, "_indextts_space_client", lambda: FakeClient())

    result = wallet_api_module._run_indextts_gradio_tts(text="Visit SE 32nd ave or call 211.")

    assert result["text"] == "Visit South East thirty second Avenue or call two one one."
    assert result["originalText"] == "Visit SE 32nd ave or call 211."
    assert queued_payloads
    assert queued_payloads[0][0] == 17
    assert queued_payloads[0][1][2] == "Visit South East thirty second Avenue or call two one one."


def test_indextts_batch_proxy_uses_batch_endpoint(monkeypatch) -> None:
    wallet_api_module._INDEXTTS_CONFIG_CACHE.clear()
    wallet_api_module._INDEXTTS_FN_INDEX_CACHE.clear()
    wallet_api_module._INDEXTTS_REFERENCE_CACHE.clear()

    queued_payloads: list[tuple[int, list[object]]] = []

    class FakeClient:
        def get_config(self) -> dict[str, object]:
            return {"dependencies": [{"id": 17, "api_name": "/gen_single"}, {"id": 23, "api_name": "/gen_batch"}]}

        def resolve_fn_index(self, api_name: str, config: Mapping[str, object], *, fallback_markers=()):
            return 23 if "batch" in api_name else 17

        def upload_file(self, file_name: str, data: bytes, mime_type: str) -> dict[str, object]:
            return {"path": "/tmp/abby-reference.wav", "meta": {"_type": "gradio.FileData"}, "orig_name": file_name}

        def queue_join(self, fn_index: int, data: Sequence[object], *, session_hash: str | None = None) -> str:
            queued_payloads.append((fn_index, list(data)))
            return session_hash or "session-123"

        def wait_for_queue_result(self, session_hash: str, *, timeout_seconds: float | None = None, poll_interval_seconds: float = 0.5) -> dict[str, object]:
            return {
                "data": [
                    {"__type__": "update", "value": {"path": "/tmp/preview.wav"}},
                    {"__type__": "update", "value": [{"path": "/tmp/one.wav"}, {"path": "/tmp/two.wav"}]},
                    {"__type__": "update", "value": None},
                ]
            }

        def fetch_file(self, reference: object, *, accept: str = "audio/*, application/octet-stream") -> tuple[bytes, str]:
            return b"RIFFstubWAVE", "audio/wav"

    monkeypatch.setenv("WALLET_INDEXTTS_SPACE_URL", "https://example.test")
    monkeypatch.setenv("WALLET_INDEXTTS_BATCH_API_NAME", "gen_batch")
    monkeypatch.setattr(wallet_api_module, "_indextts_space_client", lambda: FakeClient())

    result = wallet_api_module._run_indextts_gradio_batch_tts(texts=["Call 211.", "Meet at SE 32nd ave."])

    assert result["mode"] == "batch"
    assert result["batchSize"] == 2
    assert queued_payloads[0][0] == 23
    assert queued_payloads[0][1][2] == '["Call two one one.", "Meet at South East thirty second Avenue."]'
    assert queued_payloads[0][1][16] == 2
    assert [item["text"] for item in result["items"]] == ["Call two one one.", "Meet at South East thirty second Avenue."]


def test_indextts_batch_prefers_generated_file_list_over_preview(monkeypatch) -> None:
    result = {
        "data": [
            {"__type__": "update", "value": {"path": "/tmp/preview.wav"}},
            {
                "__type__": "update",
                "value": [
                    {"path": "/tmp/item-1.wav"},
                    {"path": "/tmp/item-2.wav"},
                ],
            },
            {"__type__": "update", "value": None},
        ]
    }

    assert wallet_api_module._indextts_batch_audio_references(result) == [
        {"path": "/tmp/item-1.wav"},
        {"path": "/tmp/item-2.wav"},
    ]


def test_indextts_batch_extracts_audio_from_zip_output(monkeypatch) -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("spk-item-1.wav", b"RIFFoneWAVE")
        archive.writestr("spk-item-2.wav", b"RIFFtwoWAVE")
    monkeypatch.setattr(wallet_api_module, "_fetch_gradio_file", lambda ref: (buffer.getvalue(), "application/zip"))
    result = {
        "data": [
            {"__type__": "update", "value": {"path": "/tmp/preview.wav"}},
            {"__type__": "update", "value": []},
            {"__type__": "update", "value": {"path": "/tmp/batch.zip"}},
        ]
    }

    refs = wallet_api_module._indextts_batch_audio_references(result)

    assert [ref["name"] for ref in refs] == ["spk-item-1.wav", "spk-item-2.wav"]
    assert refs[0]["_inline_bytes"] == b"RIFFoneWAVE"


def test_indextts_voice_reply_generates_llm_text_before_tts(monkeypatch) -> None:
    from ipfs_datasets_py import llm_router

    prompts: list[dict[str, object]] = []

    def fake_generate_text(prompt: str, **kwargs: object) -> str:
        prompts.append({"prompt": prompt, **kwargs})
        return "Assistant: Food pantries near Portland may be open today. What ZIP code should I search around?"

    monkeypatch.setattr(llm_router, "generate_text", fake_generate_text)
    monkeypatch.setattr(
        wallet_api_module,
        "_run_indextts_gradio_tts",
        lambda **kwargs: {
            "audioBase64": base64.b64encode(b"RIFFstubWAVE").decode("ascii"),
            "mimeType": "audio/wav",
            "model": "IndexTTS",
            "provider": "test",
            "latency": {"total_ms": 3},
        },
    )
    monkeypatch.setenv("WALLET_VOICE_LLM_MODEL", "Qwen/Qwen3.5-2B")

    response = _client().post(
        "/voice/indextts/infer",
        data={
            "mode": "voice-reply",
            "text": "system: concise\nuser: I need food help in Portland today",
            "systemPrompt": "Be concise.",
            "userPrompt": "I need food help in Portland today",
            "fallbackText": "Abby here. I can help with food support.",
        },
        files={"audio": ("input.wav", b"RIFFmockWAVE", "audio/wav")},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["text"] == "Food pantries near Portland may be open today. What ZIP code should I search around?"
    assert body["latency"]["llm_request_ms"] >= 0
    assert body["latency"]["llm_model"] == "Qwen/Qwen3.5-2B"
    assert prompts and "I need food help" in str(prompts[0]["prompt"])


def test_wallet_api_phone_call_notification_queue_and_manual_dispatch_uses_http_webhook(monkeypatch) -> None:
    captured_requests = []

    class FakeResponse:
        def __init__(self, payload: dict[str, object]) -> None:
            self.payload = payload
            self.headers = {"content-type": "application/json"}
            self.status = 202

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps(self.payload).encode("utf-8")

    def fake_urlopen(request, timeout: float):
        captured_requests.append(
            {
                "url": request.full_url,
                "headers": dict(request.header_items()),
                "payload": json.loads(request.data.decode("utf-8")),
                "timeout": timeout,
            }
        )
        return FakeResponse({"call_id": "call-123", "provider": "test-call-webhook", "status": "accepted"})

    monkeypatch.setenv("WALLET_CALL_WEBHOOK_URL", "https://voice.example.org/call")
    monkeypatch.setenv("WALLET_CALL_BEARER_TOKEN", "call-secret")
    monkeypatch.setattr(wallet_api_module.urllib_request, "urlopen", fake_urlopen)
    client = _client()
    wallet = client.post("/wallets", json={"owner_did": "did:key:owner"}).json()

    queue_response = client.post(
        f"/wallets/{wallet['wallet_id']}/notifications/calls/queue",
        json={
            "actor_did": "did:key:owner",
            "to_phone": "(503) 555-0100",
            "script": "This is Abby calling with an intake reminder.",
            "reason": "intake-call",
        },
    )

    assert queue_response.status_code == 200
    queued = queue_response.json()
    assert queued["status"] == "queued"
    assert queued["to_phone"] == "5035550100"

    dispatch_response = client.post(
        f"/wallets/{wallet['wallet_id']}/notifications/calls/{queued['notification_id']}/dispatch",
        json={"actor_did": "did:key:owner"},
    )

    assert dispatch_response.status_code == 200
    payload = dispatch_response.json()
    assert payload["status"] == "sent"
    assert payload["provider"] == "test-call-webhook"
    assert payload["provider_message_id"] == "call-123"
    assert payload["notification"]["status"] == "sent"
    assert len(captured_requests) == 1
    assert captured_requests[0]["url"] == "https://voice.example.org/call"
    assert captured_requests[0]["headers"]["Authorization"] == "Bearer call-secret"
    assert captured_requests[0]["payload"] == {
        "to_phone": "5035550100",
        "script": "This is Abby calling with an intake reminder.",
    }


def test_wallet_api_phone_call_notification_processes_due_and_persists(tmp_path, monkeypatch) -> None:
    class FakeResponse:
        def __init__(self, payload: dict[str, object]) -> None:
            self.payload = payload
            self.headers = {"content-type": "application/json"}
            self.status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps(self.payload).encode("utf-8")

    delivery_ids: list[str] = []

    def fake_urlopen(request, timeout: float):
        delivery_ids.append(json.loads(request.data.decode("utf-8"))["to_phone"])
        return FakeResponse({"call_id": f"call-{len(delivery_ids)}", "status": "accepted"})

    monkeypatch.setenv("WALLET_CALL_WEBHOOK_URL", "https://voice.example.org/call")
    monkeypatch.setenv("WALLET_OPS_HEALTH_SHARED_SECRET", "ops-secret")
    monkeypatch.setattr(wallet_api_module.urllib_request, "urlopen", fake_urlopen)
    service = WalletInterfaceService(repository_root=tmp_path / "wallet-repository", services=[])
    client = _client_with_service(service)
    wallet = client.post("/wallets", json={"owner_did": "did:key:owner"}).json()

    queue_response = client.post(
        f"/wallets/{wallet['wallet_id']}/notifications/calls/queue",
        json={
            "actor_did": "did:key:owner",
            "to_phone": "+1 (503) 555-0199",
            "script": "This is Abby calling to remind you about tonight's shelter bed hold.",
            "due_at": "2024-01-01T00:00:00Z",
            "reason": "bed-hold-call",
        },
    )

    assert queue_response.status_code == 200

    process_response = client.post(
        "/ops/notifications/calls/process-due",
        headers={"x-wallet-ops-shared-secret": "ops-secret"},
    )

    assert process_response.status_code == 200
    payload = process_response.json()
    assert payload["due_count"] == 1
    assert payload["sent_count"] == 1
    assert payload["failed_count"] == 0
    assert delivery_ids == ["+15035550199"]

    state_response = client.get(f"/wallets/{wallet['wallet_id']}/notifications/calls")
    assert state_response.status_code == 200
    state_payload = state_response.json()["notifications"][0]
    assert state_payload["status"] == "sent"
    assert state_payload["last_provider_call_id"] == "call-1"

    restored_service = WalletInterfaceService(repository_root=tmp_path / "wallet-repository", services=[])
    restored_client = _client_with_service(restored_service)
    load_response = restored_client.post("/wallets/snapshots/load-all")
    assert load_response.status_code == 200

    restored_state = restored_client.get(f"/wallets/{wallet['wallet_id']}/notifications/calls")
    assert restored_state.status_code == 200
    restored_payload = restored_state.json()["notifications"][0]
    assert restored_payload["status"] == "sent"
    assert restored_payload["last_provider_call_id"] == "call-1"


def test_wallet_api_snapshot_save_list_and_load(tmp_path) -> None:
    storage_config = {"type": "local", "root": tmp_path / "wallet-blobs"}
    repository_root = tmp_path / "wallet-repository"
    service = WalletInterfaceService(
        services=[],
        storage_config=storage_config,
        repository_root=repository_root,
    )
    client = _client_with_service(service)
    wallet = client.post("/wallets", json={"owner_did": "did:key:owner"}).json()
    record = client.post(
        f"/wallets/{wallet['wallet_id']}/documents/text",
        json={
            "actor_did": "did:key:owner",
            "filename": "snapshot.txt",
            "text": "snapshot round trip document",
        },
    ).json()

    response = client.post(f"/wallets/{wallet['wallet_id']}/snapshot")

    assert response.status_code == 200
    assert Path(response.json()["path"]).exists()
    response = client.get(f"/wallets/{wallet['wallet_id']}/snapshot")
    assert response.status_code == 200
    assert response.json()["valid"] is True
    assert response.json()["snapshot_hash"] == response.json()["computed_hash"]
    response = client.get("/wallets/snapshots")
    assert response.status_code == 200
    assert response.json()["wallet_ids"] == [wallet["wallet_id"]]
    response = client.post("/wallets/snapshots/save-all")
    assert response.status_code == 200
    assert response.json()["count"] == 1

    restored_service = WalletInterfaceService(
        services=[],
        storage_config=storage_config,
        repository_root=repository_root,
        auto_load_repository=False,
    )
    restored_client = _client_with_service(restored_service)
    response = restored_client.post("/wallets/snapshots/load-all")

    assert response.status_code == 200
    assert response.json()["wallet_ids"] == [wallet["wallet_id"]]
    response = restored_client.get(f"/wallets/{wallet['wallet_id']}/records", params={"data_type": "document"})
    assert response.status_code == 200
    assert [item["record_id"] for item in response.json()["records"]] == [record["record_id"]]


def test_wallet_api_portal_saved_services_plans_and_interactions_round_trip() -> None:
    client = _client()
    wallet = client.post("/wallets", json={"owner_did": "did:key:owner"}).json()

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/portal/saved-services",
        json={
            "actor_did": "did:key:owner",
            "service_doc_id": "service:abc123",
            "source_content_cid": "bafk-service",
            "source_page_cid": "bafk-page",
            "title": "Energy Assistance",
            "provider_name": "Community Action",
            "program_name": "Energy Assistance",
            "source_url": "https://example.test/services/energy",
            "label": "Call this week",
            "reason": "Utility shutoff risk",
            "priority": "high",
            "status": "saved",
        },
    )
    assert response.status_code == 200
    saved = response.json()
    assert saved["saved_service_id"].startswith("saved-service-")
    assert saved["service_doc_id"] == "service:abc123"

    response = client.patch(
        f"/wallets/{wallet['wallet_id']}/portal/saved-services/{saved['saved_service_id']}",
        json={
            "actor_did": "did:key:owner",
            "status": "contacted",
            "private_notes_record_id": "record-private-notes-1",
        },
    )
    assert response.status_code == 200
    saved = response.json()
    assert saved["status"] == "contacted"
    assert saved["private_notes_record_id"] == "record-private-notes-1"

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/portal/plans",
        json={
            "actor_did": "did:key:owner",
            "service_doc_id": "service:abc123",
            "source_content_cid": "bafk-service",
            "source_page_cid": "bafk-page",
            "service_title": "Energy Assistance",
            "provider_name": "Community Action",
            "goal": "Avoid utility disconnection",
            "steps": ["Call provider", "Gather bill", "Complete intake"],
            "documents_needed": ["Photo ID", "Utility bill"],
            "questions_to_ask": ["Do they cover reconnect fees?"],
            "reminder_at": "2026-05-06T09:00:00+00:00",
            "travel_target": "Phone call",
            "status": "active",
        },
    )
    assert response.status_code == 200
    plan = response.json()
    assert plan["plan_id"].startswith("service-plan-")
    assert plan["steps"] == ["Call provider", "Gather bill", "Complete intake"]

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/portal/plans/{plan['plan_id']}/share-grants",
        json={
            "actor_did": "did:key:owner",
            "audience_did": "did:key:worker",
            "worker_recipient_id": "rec-worker-1",
            "worker_name": "Case Worker Desk",
            "scopes": ["service_summary", "checklist"],
        },
    )
    assert response.status_code == 200
    share = response.json()
    assert share["grant_id"].startswith("grant-")
    assert share["grant"]["abilities"] == ["service_plan/read"]
    assert share["grant"]["resources"] == [f"wallet://{wallet['wallet_id']}/portal/plans/{plan['plan_id']}"]
    assert share["grant"]["caveats"]["service_plan_scopes"] == ["service_summary", "checklist"]
    assert "private_notes_record_id" not in share["grant"]["caveats"]["allowed_fields"]
    assert share["receipt"]["grant_id"] == share["grant_id"]
    assert share["interaction"]["interaction_type"] == "shared_service_plan"
    assert share["interaction"]["related_grant_ids"] == [share["grant_id"]]
    assert share["plan"]["assigned_worker_recipient_id"] == "rec-worker-1"

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/portal/interactions",
        json={
            "actor_did": "did:key:owner",
            "service_doc_id": "service:abc123",
            "source_content_cid": "bafk-service",
            "source_page_cid": "bafk-page",
            "provider_name": "Community Action",
            "program_name": "Energy Assistance",
            "interaction_type": "called_provider",
            "channel": "phone",
            "counterparty_name": "Front Desk",
            "counterparty_contact": "(503) 555-0100",
            "status": "completed",
            "outcome": "Left voicemail",
            "next_action": "Try again tomorrow",
            "next_follow_up_at": "2026-05-06T16:00:00+00:00",
            "related_record_ids": [saved["private_notes_record_id"]],
            "privacy_level": "restricted",
        },
    )
    assert response.status_code == 200
    interaction = response.json()
    assert interaction["interaction_id"].startswith("interaction-")
    assert interaction["privacy_level"] == "restricted"

    response = client.patch(
        f"/wallets/{wallet['wallet_id']}/portal/plans/{plan['plan_id']}",
        json={
            "actor_did": "did:key:owner",
            "status": "in_progress",
            "related_interaction_ids": [interaction["interaction_id"]],
        },
    )
    assert response.status_code == 200
    updated_plan = response.json()
    assert updated_plan["related_interaction_ids"] == [interaction["interaction_id"]]

    response = client.patch(
        f"/wallets/{wallet['wallet_id']}/portal/interactions/{interaction['interaction_id']}",
        json={
            "actor_did": "did:key:owner",
            "outcome": "Appointment scheduled",
            "status": "scheduled",
        },
    )
    assert response.status_code == 200
    interaction = response.json()
    assert interaction["status"] == "scheduled"
    assert interaction["outcome"] == "Appointment scheduled"

    response = client.get(f"/wallets/{wallet['wallet_id']}/portal/saved-services")
    assert response.status_code == 200
    assert [item["saved_service_id"] for item in response.json()["saved_services"]] == [saved["saved_service_id"]]

    response = client.get(
        f"/wallets/{wallet['wallet_id']}/portal/plans",
        params={"service_doc_id": "service:abc123"},
    )
    assert response.status_code == 200
    assert [item["plan_id"] for item in response.json()["plans"]] == [plan["plan_id"]]

    response = client.get(
        f"/wallets/{wallet['wallet_id']}/portal/interactions",
        params={"interaction_type": "called_provider"},
    )
    assert response.status_code == 200
    assert [item["interaction_id"] for item in response.json()["interactions"]] == [interaction["interaction_id"]]

    response = client.get(f"/wallets/{wallet['wallet_id']}/audit")
    actions = [event["action"] for event in response.json()["events"]]
    assert "service/save" in actions
    assert "service/update" in actions
    assert "service_plan/create" in actions
    assert "service_plan/update" in actions
    assert "service_plan/share" in actions
    assert "grant/create" in actions
    assert "interaction/create" in actions
    assert "interaction/update" in actions


def test_wallet_api_worker_service_plan_redaction_and_revocation_audit() -> None:
    client = _client()
    wallet = client.post("/wallets", json={"owner_did": "did:key:owner"}).json()

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/portal/plans",
        json={
            "actor_did": "did:key:owner",
            "service_doc_id": "service:redaction-1",
            "source_content_cid": "bafk-redaction-service",
            "source_page_cid": "bafk-redaction-page",
            "service_title": "Shelter Intake",
            "provider_name": "Shelter Network",
            "goal": "Complete intake before Friday",
            "steps": ["Call intake line", "Confirm bed availability"],
            "documents_needed": ["Photo ID", "Proof of income"],
            "questions_to_ask": ["Are walk-ins accepted?"],
            "appointment_at": "2026-05-08T17:00:00+00:00",
            "reminder_at": "2026-05-08T15:00:00+00:00",
            "travel_target": "123 Main St",
            "assigned_worker_recipient_id": "rec-worker-1",
            "status": "active",
            "private_notes_record_id": "record-private-redaction-notes",
        },
    )
    assert response.status_code == 200
    plan = response.json()

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/portal/plans/{plan['plan_id']}/share-grants",
        json={
            "actor_did": "did:key:owner",
            "audience_did": "did:key:worker",
            "worker_recipient_id": "rec-worker-1",
            "worker_name": "Case Worker Desk",
            "scopes": ["service_summary", "checklist"],
        },
    )
    assert response.status_code == 200
    share = response.json()
    grant_id = share["grant_id"]
    allowed_fields = share["grant"]["caveats"]["allowed_fields"]

    assert allowed_fields == [
        "service_doc_id",
        "source_content_cid",
        "source_page_cid",
        "service_title",
        "provider_name",
        "goal",
        "status",
        "steps",
        "documents_needed",
        "questions_to_ask",
    ]
    assert "appointment_at" not in allowed_fields
    assert "reminder_at" not in allowed_fields
    assert "travel_target" not in allowed_fields
    assert "assigned_worker_recipient_id" not in allowed_fields
    assert "private_notes_record_id" not in allowed_fields

    worker_visible_plan = {field: share["plan"][field] for field in allowed_fields}
    assert worker_visible_plan["service_title"] == "Shelter Intake"
    assert worker_visible_plan["steps"] == ["Call intake line", "Confirm bed availability"]
    assert "123 Main St" not in json.dumps(worker_visible_plan)
    assert "record-private-redaction-notes" not in json.dumps(worker_visible_plan)

    response = client.get(
        f"/wallets/{wallet['wallet_id']}/grant-receipts",
        params={"audience_did": "did:key:worker", "status": "active"},
    )
    assert response.status_code == 200
    assert [receipt["grant_id"] for receipt in response.json()["receipts"]] == [grant_id]

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/grants/{grant_id}/revoke",
        json={"actor_did": "did:key:owner"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "revoked"

    response = client.get(
        f"/wallets/{wallet['wallet_id']}/grant-receipts",
        params={"audience_did": "did:key:worker", "status": "active"},
    )
    assert response.status_code == 200
    assert response.json()["receipts"] == []

    response = client.get(
        f"/wallets/{wallet['wallet_id']}/grant-receipts",
        params={"audience_did": "did:key:worker", "status": "revoked"},
    )
    assert response.status_code == 200
    revoked_receipts = response.json()["receipts"]
    assert [receipt["grant_id"] for receipt in revoked_receipts] == [grant_id]
    assert revoked_receipts[0]["caveats"]["allowed_fields"] == allowed_fields

    response = client.get(
        f"/wallets/{wallet['wallet_id']}/portal/interactions",
        params={"interaction_type": "shared_service_plan"},
    )
    assert response.status_code == 200
    interactions = response.json()["interactions"]
    assert [interaction["related_grant_ids"] for interaction in interactions] == [[grant_id]]

    response = client.get(f"/wallets/{wallet['wallet_id']}/audit")
    assert response.status_code == 200
    events = response.json()["events"]
    actions = [event["action"] for event in events]
    assert "service_plan/share" in actions
    assert "grant/create" in actions
    assert "grant/revoke" in actions
    assert [event["action"] for event in events if event["grant_id"] == grant_id] == ["grant/create", "grant/revoke"]


def test_wallet_api_portal_state_persists_through_snapshot_load(tmp_path) -> None:
    repository_root = tmp_path / "wallet-repository"
    service = WalletInterfaceService(repository_root=repository_root, services=[])
    client = _client_with_service(service)
    wallet = client.post("/wallets", json={"owner_did": "did:key:owner"}).json()

    saved = client.post(
        f"/wallets/{wallet['wallet_id']}/portal/saved-services",
        json={
            "actor_did": "did:key:owner",
            "service_doc_id": "service:persist-1",
            "source_content_cid": "bafk-persist",
            "title": "Shelter Intake",
            "provider_name": "Shelter Network",
            "status": "saved",
        },
    ).json()
    plan = client.post(
        f"/wallets/{wallet['wallet_id']}/portal/plans",
        json={
            "actor_did": "did:key:owner",
            "service_doc_id": "service:persist-1",
            "service_title": "Shelter Intake",
            "goal": "Complete shelter intake",
            "steps": ["Call first", "Bring ID"],
        },
    ).json()
    interaction = client.post(
        f"/wallets/{wallet['wallet_id']}/portal/interactions",
        json={
            "actor_did": "did:key:owner",
            "service_doc_id": "service:persist-1",
            "interaction_type": "saved_service",
            "status": "recorded",
        },
    ).json()

    response = client.post(f"/wallets/{wallet['wallet_id']}/snapshot")
    assert response.status_code == 200

    restored_service = WalletInterfaceService(
        repository_root=repository_root,
        services=[],
        auto_load_repository=False,
    )
    restored_client = _client_with_service(restored_service)
    response = restored_client.post("/wallets/snapshots/load-all")
    assert response.status_code == 200

    response = restored_client.get(f"/wallets/{wallet['wallet_id']}/portal/saved-services")
    assert response.status_code == 200
    assert [item["saved_service_id"] for item in response.json()["saved_services"]] == [saved["saved_service_id"]]

    response = restored_client.get(f"/wallets/{wallet['wallet_id']}/portal/plans")
    assert response.status_code == 200
    assert [item["plan_id"] for item in response.json()["plans"]] == [plan["plan_id"]]

    response = restored_client.get(f"/wallets/{wallet['wallet_id']}/portal/interactions")
    assert response.status_code == 200
    assert [item["interaction_id"] for item in response.json()["interactions"]] == [interaction["interaction_id"]]

    response = restored_client.get(f"/wallets/{wallet['wallet_id']}/audit")
    assert response.status_code == 200
    actions = [event["action"] for event in response.json()["events"]]
    assert "service/save" in actions
    assert "service_plan/create" in actions
    assert "interaction/create" in actions


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


def test_wallet_api_export_bundle_uses_export_grant_without_plaintext() -> None:
    client = _client()
    delegate_key = random_key().hex()
    wallet = client.post("/wallets", json={"owner_did": "did:key:owner"}).json()
    document = client.post(
        f"/wallets/{wallet['wallet_id']}/documents/text",
        json={
            "actor_did": "did:key:owner",
            "filename": "notice.txt",
            "text": "Confidential export document",
        },
    ).json()
    location = client.post(
        f"/wallets/{wallet['wallet_id']}/locations",
        json={"actor_did": "did:key:owner", "lat": 45.515232, "lon": -122.678385},
    ).json()

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/exports",
        json={
            "actor_did": "did:key:delegate",
            "record_ids": [document["record_id"], location["record_id"]],
        },
    )
    assert response.status_code == 400
    assert "requires" in response.json()["detail"]

    grant = client.post(
        f"/wallets/{wallet['wallet_id']}/exports/grants",
        json={
            "issuer_did": "did:key:owner",
            "audience_did": "did:key:delegate",
            "audience_key_hex": delegate_key,
            "record_ids": [document["record_id"], location["record_id"]],
        },
    ).json()
    assert grant["caveats"]["output_types"] == ["encrypted_export_bundle"]
    invocation = client.post(
        f"/wallets/{wallet['wallet_id']}/exports/invocations",
        json={
            "actor_did": "did:key:delegate",
            "actor_key_hex": delegate_key,
            "grant_id": grant["grant_id"],
            "record_ids": [document["record_id"]],
        },
    ).json()
    response = client.post(
        f"/wallets/{wallet['wallet_id']}/exports",
        json={
            "actor_did": "did:key:delegate",
            "actor_key_hex": delegate_key,
            "invocation_token": invocation["invocation_token"],
            "record_ids": [document["record_id"]],
        },
    )
    assert response.status_code == 200
    bundle = response.json()
    assert bundle["bundle_type"] == "wallet_export_v1"
    assert bundle["bundle_id"] == f"export-{bundle['bundle_hash'][:24]}"
    assert "controller_dids" not in bundle["wallet"]
    assert "device_dids" not in bundle["wallet"]
    assert [record["data_type"] for record in bundle["records"]] == ["document"]
    public_bundle = json.dumps(bundle)
    assert "Confidential export document" not in public_bundle
    assert "45.515232" not in public_bundle
    assert "-122.678385" not in public_bundle
    response = client.post("/exports/verify", json={"bundle": bundle})
    assert response.status_code == 200
    verified = response.json()
    assert verified["valid"] is True
    assert verified["hash_valid"] is True
    assert verified["schema_valid"] is True
    assert verified["computed_hash"] == bundle["bundle_hash"]
    response = client.post("/exports/import", json={"bundle": bundle})
    assert response.status_code == 200
    imported = response.json()
    assert imported["record_count"] == 1
    assert imported["bundle_hash"] == bundle["bundle_hash"]
    response = client.post("/exports/storage", json={"bundle": bundle})
    assert response.status_code == 200
    storage = response.json()
    assert storage["record_count"] == 1
    assert "ok" in storage
    tampered = {**bundle, "records": []}
    response = client.post("/exports/verify", json={"bundle": tampered})
    assert response.status_code == 200
    assert response.json()["valid"] is False
    response = client.post("/exports/import", json={"bundle": tampered})
    assert response.status_code == 400
    assert "verification failed" in response.json()["detail"]
    malformed = {**bundle, "bundle_type": "not_wallet_export"}
    verify = client.post("/exports/verify", json={"bundle": malformed}).json()
    malformed["bundle_hash"] = verify["computed_hash"]
    malformed["bundle_id"] = f"export-{malformed['bundle_hash'][:24]}"
    response = client.post("/exports/verify", json={"bundle": malformed})
    assert response.status_code == 200
    malformed_verification = response.json()
    assert malformed_verification["valid"] is False
    assert malformed_verification["hash_valid"] is True
    assert malformed_verification["schema_valid"] is False
    assert "Unsupported" in malformed_verification["schema_error"]
    response = client.post("/exports/import", json={"bundle": malformed})
    assert response.status_code == 400
    assert "Unsupported" in response.json()["detail"]

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/exports",
        json={
            "actor_did": "did:key:delegate",
            "actor_key_hex": delegate_key,
            "invocation_token": invocation["invocation_token"],
            "record_ids": [location["record_id"]],
        },
    )
    assert response.status_code == 400
    assert "invocation" in response.json()["detail"]


def test_wallet_api_revoked_export_grant_blocks_invocation() -> None:
    client = _client()
    delegate_key = random_key().hex()
    wallet = client.post("/wallets", json={"owner_did": "did:key:owner"}).json()
    document = client.post(
        f"/wallets/{wallet['wallet_id']}/documents/text",
        json={
            "actor_did": "did:key:owner",
            "filename": "revoked-export.txt",
            "text": "Export must stop after revocation.",
        },
    ).json()
    grant = client.post(
        f"/wallets/{wallet['wallet_id']}/exports/grants",
        json={
            "issuer_did": "did:key:owner",
            "audience_did": "did:key:delegate",
            "audience_key_hex": delegate_key,
            "record_ids": [document["record_id"]],
        },
    ).json()
    invocation = client.post(
        f"/wallets/{wallet['wallet_id']}/exports/invocations",
        json={
            "actor_did": "did:key:delegate",
            "actor_key_hex": delegate_key,
            "grant_id": grant["grant_id"],
            "record_ids": [document["record_id"]],
        },
    ).json()

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/grants/{grant['grant_id']}/revoke",
        json={"actor_did": "did:key:owner"},
    )
    assert response.status_code == 200
    response = client.post(
        f"/wallets/{wallet['wallet_id']}/exports",
        json={
            "actor_did": "did:key:delegate",
            "actor_key_hex": delegate_key,
            "invocation_token": invocation["invocation_token"],
            "record_ids": [document["record_id"]],
        },
    )

    assert response.status_code == 400
    assert "not active" in response.json()["detail"]


def test_wallet_api_export_grant_respects_threshold_approval() -> None:
    client = _client()
    wallet = client.post(
        "/wallets",
        json={
            "owner_did": "did:key:owner",
            "controller_dids": ["did:key:owner", "did:key:second-controller"],
            "approval_threshold": 2,
        },
    ).json()
    document = client.post(
        f"/wallets/{wallet['wallet_id']}/documents/text",
        json={
            "actor_did": "did:key:owner",
            "filename": "export-approval.txt",
            "text": "API export approval document",
        },
    ).json()

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/exports/grants",
        json={
            "issuer_did": "did:key:owner",
            "audience_did": "did:key:delegate",
            "record_ids": [document["record_id"]],
        },
    )
    assert response.status_code == 400
    assert "approval_id is required" in response.json()["detail"]

    approval = client.post(
        f"/wallets/{wallet['wallet_id']}/approvals",
        json={
            "requested_by": "did:key:owner",
            "operation": "grant/create",
            "resources": [resource_for_export(wallet["wallet_id"])],
            "abilities": ["export/create"],
        },
    ).json()
    for approver in ["did:key:owner", "did:key:second-controller"]:
        response = client.post(
            f"/wallets/{wallet['wallet_id']}/approvals/{approval['approval_id']}/approve",
            json={"approver_did": approver},
        )
        assert response.status_code == 200
    response = client.post(
        f"/wallets/{wallet['wallet_id']}/exports/grants",
        json={
            "issuer_did": "did:key:owner",
            "audience_did": "did:key:delegate",
            "record_ids": [document["record_id"]],
            "approval_id": approval["approval_id"],
        },
    )

    assert response.status_code == 200
    assert response.json()["abilities"] == ["export/create"]


# ---------------------------------------------------------------------------
# CLZKML-280: Wallet/API Optional Consensus Integration tests
# ---------------------------------------------------------------------------


def test_wallet_ai_router_llm_returns_text_without_consensus_field(monkeypatch) -> None:
    """Non-consensus path is preserved when no consensus options are provided."""
    from ipfs_datasets_py import llm_router

    monkeypatch.setattr(llm_router, "generate_text", lambda prompt, **kw: "Housing help available.")
    client = _client()
    wallet = client.post("/wallets", json={"owner_did": "did:key:owner"}).json()

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/ai-router/llm",
        json={
            "actor_did": "did:key:owner",
            "prompt": "What housing help is available in Portland?",
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["text"] == "Housing help available."
    assert body["router"] == "llm_router"
    assert "consensus" not in body


def test_wallet_ai_router_llm_consensus_mode_via_request_field(monkeypatch) -> None:
    """Consensus mode is enabled by the request consensus field and receipt metadata is returned."""
    import ipfs_accelerate_py.llm_router as accel_llm_router
    from ipfs_accelerate_py.llm_consensus import ConsensusReceipt

    captured: list[dict] = []

    class _FakeReceipt:
        text = "Consensus answer."

        def to_dict(self):
            return {
                "schema_version": "llm-router-consensus-receipt-v1",
                "request": {"metadata": {"mode": "receipt_only"}},
                "responses": [{"operator_id": "local-router"}],
                "consensus": {"quorum_reached": True},
                "proof": {"mode": "receipt_only"},
                "text": self.text,
                "created_at": "2026-06-13T00:00:00Z",
            }

    def fake_consensus(prompt, *, consensus=None, proof_policy=None, **kw):
        captured.append({"prompt": prompt, "consensus": consensus, "proof_policy": proof_policy})
        return _FakeReceipt()

    monkeypatch.setattr(accel_llm_router, "generate_text_consensus", fake_consensus)
    client = _client()
    wallet = client.post("/wallets", json={"owner_did": "did:key:owner"}).json()

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/ai-router/llm",
        json={
            "actor_did": "did:key:owner",
            "prompt": "Find shelter for a family of four.",
            "consensus": {"mode": "receipt_only", "fail_closed": False},
            "proof_policy": {"mode": "receipt_only"},
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["text"] == "Consensus answer."
    assert body["router"] == "llm_router"
    assert "consensus" in body
    consensus_meta = body["consensus"]
    assert consensus_meta["quorum_reached"] is True
    assert consensus_meta["operator_count"] == 1
    assert consensus_meta["proof_mode"] == "receipt_only"
    assert captured and captured[0]["consensus"]["mode"] == "receipt_only"


def test_wallet_ai_router_llm_consensus_mode_via_env_policy(monkeypatch) -> None:
    """Consensus mode can be activated via environment policy without a request field."""
    import ipfs_accelerate_py.llm_router as accel_llm_router

    class _FakeReceipt:
        text = "Env-policy consensus answer."

        def to_dict(self):
            return {
                "schema_version": "llm-router-consensus-receipt-v1",
                "request": {"metadata": {"mode": "receipt_only"}},
                "responses": [],
                "consensus": {"quorum_reached": True},
                "proof": {"mode": "receipt_only"},
                "text": self.text,
                "created_at": "2026-06-13T00:00:00Z",
            }

    monkeypatch.setattr(accel_llm_router, "generate_text_consensus", lambda *a, **kw: _FakeReceipt())
    monkeypatch.setenv("WALLET_AI_ROUTER_CONSENSUS_MODE", "receipt_only")
    monkeypatch.setenv("WALLET_AI_ROUTER_CONSENSUS_FAIL_CLOSED", "false")
    client = _client()
    wallet = client.post("/wallets", json={"owner_did": "did:key:owner"}).json()

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/ai-router/llm",
        json={
            "actor_did": "did:key:owner",
            "prompt": "Help with food access near downtown.",
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["text"] == "Env-policy consensus answer."
    assert "consensus" in body
    assert body["consensus"]["quorum_reached"] is True


def test_wallet_ai_router_llm_no_consensus_when_env_not_set(monkeypatch) -> None:
    """When no env policy and no request consensus field, the standard path is used."""
    from ipfs_datasets_py import llm_router

    monkeypatch.delenv("WALLET_AI_ROUTER_CONSENSUS_MODE", raising=False)
    monkeypatch.setattr(llm_router, "generate_text", lambda prompt, **kw: "Standard path answer.")
    client = _client()
    wallet = client.post("/wallets", json={"owner_did": "did:key:owner"}).json()

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/ai-router/llm",
        json={
            "actor_did": "did:key:owner",
            "prompt": "What food pantries are open?",
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["text"] == "Standard path answer."
    assert "consensus" not in body


def test_wallet_ai_router_llm_consensus_fail_closed_propagated(monkeypatch) -> None:
    """When consensus fails and fail_closed is True, an error is raised."""
    import ipfs_accelerate_py.llm_router as accel_llm_router
    from ipfs_accelerate_py.llm_consensus import LLMConsensusError

    def fail_consensus(prompt, *, consensus=None, **kw):
        raise LLMConsensusError("No quorum reached")

    monkeypatch.setattr(accel_llm_router, "generate_text_consensus", fail_consensus)
    client = _client()
    wallet = client.post("/wallets", json={"owner_did": "did:key:owner"}).json()

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/ai-router/llm",
        json={
            "actor_did": "did:key:owner",
            "prompt": "Is the shelter open tonight?",
            "consensus": {"mode": "receipt_only", "fail_closed": True},
        },
    )

    assert response.status_code == 502
    assert "quorum" in response.json()["detail"].lower() or "consensus" in response.json()["detail"].lower()


def test_wallet_ai_router_llm_consensus_request_fields_are_validated(monkeypatch) -> None:
    """Consensus dict with recognized fields passes validation; unknown keys are forwarded."""
    import ipfs_accelerate_py.llm_router as accel_llm_router

    captured: list[dict] = []

    class _FakeReceipt:
        text = "Validated consensus."

        def to_dict(self):
            return {
                "schema_version": "llm-router-consensus-receipt-v1",
                "request": {"metadata": {"mode": "receipt_only"}},
                "responses": [],
                "consensus": {"quorum_reached": True},
                "proof": {"mode": "receipt_only"},
                "text": self.text,
                "created_at": "2026-06-13T00:00:00Z",
            }

    def capture_consensus(prompt, *, consensus=None, **kw):
        captured.append({"consensus": consensus})
        return _FakeReceipt()

    monkeypatch.setattr(accel_llm_router, "generate_text_consensus", capture_consensus)
    client = _client()
    wallet = client.post("/wallets", json={"owner_did": "did:key:owner"}).json()

    response = client.post(
        f"/wallets/{wallet['wallet_id']}/ai-router/llm",
        json={
            "actor_did": "did:key:owner",
            "prompt": "Check eligibility for housing subsidy.",
            "consensus": {
                "mode": "receipt_only",
                "comparison": "canonical_json",
                "quorum": 1,
                "min_operators": 1,
                "fail_closed": False,
            },
        },
    )

    assert response.status_code == 200, response.text
    assert captured
    opts = captured[0]["consensus"]
    assert opts["mode"] == "receipt_only"
    assert opts["comparison"] == "canonical_json"
