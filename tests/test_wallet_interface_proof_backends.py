from __future__ import annotations

from wallet_interface.app_service import _proof_backend_from_env
from wallet_interface.proof_backends import HttpLocationRegionProofBackend


def test_http_location_region_proof_backend_round_trip() -> None:
    calls: list[tuple[str, str, dict[str, object], dict[str, str], float]] = []

    def fake_request_json(
        method: str,
        url: str,
        payload: dict[str, object],
        headers: dict[str, str],
        timeout_seconds: float,
    ) -> dict[str, object]:
        calls.append((method, url, payload, headers, timeout_seconds))
        if url.endswith("/prove/location-region"):
            return {
                "proof_id": "proof-http-1",
                "wallet_id": str(payload["wallet_id"]),
                "proof_type": "location_region",
                "statement": payload["statement"],
                "verifier_id": "verifier-http-v1",
                "public_inputs": payload["public_inputs"],
                "proof_hash": "proof-hash-1",
                "witness_record_ids": payload["witness_record_ids"],
                "is_simulated": False,
                "proof_system": "groth16",
                "circuit_id": "location-region-v1",
                "verification_status": "verified",
                "proof_artifact_ref": "https://verifier.example.test/proofs/proof-http-1",
            }
        if url.endswith("/health"):
            return {"ok": True, "status": "ready", "version": "2026.05.04"}
        return {"verified": True}

    backend = HttpLocationRegionProofBackend(
        base_url="https://verifier.example.test",
        verifier_id="verifier-http-v1",
        proof_system="groth16",
        circuit_id="location-region-v1",
        bearer_token="verifier-secret",
        extra_headers={"x-wallet-proof-key": "shared"},
        request_json=fake_request_json,
    )

    receipt = backend.prove_location_region(
        wallet_id="wallet-123",
        statement={"claim": "location_in_region"},
        public_inputs={"region_id": "multnomah"},
        witness={"lat": 45.5, "lon": -122.6},
        witness_record_ids=["record-1"],
    )

    assert receipt.wallet_id == "wallet-123"
    assert receipt.verifier_id == "verifier-http-v1"
    assert receipt.proof_system == "groth16"
    assert receipt.circuit_id == "location-region-v1"
    assert receipt.is_simulated is False
    assert backend.verify(receipt) is True

    prove_call, verify_call = calls
    assert prove_call[0] == "POST"
    assert prove_call[1] == "https://verifier.example.test/prove/location-region"
    assert prove_call[3]["authorization"] == "Bearer verifier-secret"
    assert prove_call[3]["x-wallet-proof-key"] == "shared"
    assert verify_call[1] == "https://verifier.example.test/verify"
    assert verify_call[2]["receipt"]["proof_id"] == "proof-http-1"
    health = backend.healthcheck()
    assert health["ok"] is True
    assert health["status"] == "ready"


def test_http_location_distance_proof_backend_round_trip() -> None:
    calls: list[tuple[str, str, dict[str, object], dict[str, str], float]] = []

    def fake_request_json(
        method: str,
        url: str,
        payload: dict[str, object],
        headers: dict[str, str],
        timeout_seconds: float,
    ) -> dict[str, object]:
        calls.append((method, url, payload, headers, timeout_seconds))
        if url.endswith("/prove/location-distance"):
            return {
                "proof_id": "proof-http-distance-1",
                "wallet_id": str(payload["wallet_id"]),
                "proof_type": "location_distance",
                "statement": payload["statement"],
                "verifier_id": "verifier-http-v1",
                "public_inputs": payload["public_inputs"],
                "proof_hash": "proof-hash-distance-1",
                "witness_record_ids": payload["witness_record_ids"],
                "is_simulated": False,
                "proof_system": "groth16",
                "circuit_id": "location-distance-v1",
                "verification_status": "verified",
                "proof_artifact_ref": "https://verifier.example.test/proofs/proof-http-distance-1",
            }
        return {"verified": True}

    backend = HttpLocationRegionProofBackend(
        base_url="https://verifier.example.test",
        verifier_id="verifier-http-v1",
        proof_system="groth16",
        circuit_id="location-distance-v1",
        request_json=fake_request_json,
    )

    receipt = backend.prove_location_distance(
        wallet_id="wallet-123",
        statement={"claim": "location_within_distance"},
        public_inputs={"target_id": "shelter-west", "max_distance_km": 1.0},
        witness={"lat": 45.5, "lon": -122.6, "target_lat": 45.51, "target_lon": -122.61},
        witness_record_ids=["record-1"],
    )

    assert receipt.wallet_id == "wallet-123"
    assert receipt.proof_type == "location_distance"
    assert receipt.verifier_id == "verifier-http-v1"
    assert receipt.proof_system == "groth16"
    assert receipt.circuit_id == "location-distance-v1"
    assert receipt.is_simulated is False
    assert backend.verify(receipt) is True

    prove_call, verify_call = calls
    assert prove_call[0] == "POST"
    assert prove_call[1] == "https://verifier.example.test/prove/location-distance"
    assert prove_call[2]["proof_type"] == "location_distance"
    assert verify_call[1] == "https://verifier.example.test/verify"


def test_http_location_region_proof_backend_validates_contract() -> None:
    calls: list[str] = []

    def fake_request_json(
        method: str,
        url: str,
        payload: dict[str, object],
        headers: dict[str, str],
        timeout_seconds: float,
    ) -> dict[str, object]:
        calls.append(url)
        if url.endswith("/health"):
            return {"ok": True, "status": "ready", "version": "2026.05.05"}
        if url.endswith("/prove/location-region"):
            return {
                "receipt": {
                    "proof_id": "proof-contract-1",
                    "wallet_id": str(payload["wallet_id"]),
                    "proof_type": "location_region",
                    "statement": payload["statement"],
                    "verifier_id": "verifier-http-v1",
                    "public_inputs": payload["public_inputs"],
                    "proof_hash": "proof-hash-1",
                    "witness_record_ids": payload["witness_record_ids"],
                    "is_simulated": False,
                    "proof_system": "groth16",
                    "circuit_id": "location-region-v1",
                    "verification_status": "verified",
                    "proof_artifact_ref": "https://verifier.example.test/proofs/proof-contract-1",
                }
            }
        return {"verified": True}

    backend = HttpLocationRegionProofBackend(
        base_url="https://verifier.example.test",
        verifier_id="verifier-http-v1",
        proof_system="groth16",
        circuit_id="location-region-v1",
        request_json=fake_request_json,
    )

    result = backend.validate_contract()

    assert result["status"] == "ok"
    assert result["receipt"]["proof_id"] == "proof-contract-1"
    assert [check["status"] for check in result["checks"]] == ["ok", "ok", "ok", "ok"]
    assert calls == [
        "https://verifier.example.test/health",
        "https://verifier.example.test/prove/location-region",
        "https://verifier.example.test/verify",
    ]


def test_http_location_distance_proof_backend_validates_contract() -> None:
    calls: list[str] = []

    def fake_request_json(
        method: str,
        url: str,
        payload: dict[str, object],
        headers: dict[str, str],
        timeout_seconds: float,
    ) -> dict[str, object]:
        calls.append(url)
        if url.endswith("/health"):
            return {"ok": True, "status": "ready", "version": "2026.05.05"}
        if url.endswith("/prove/location-distance"):
            return {
                "receipt": {
                    "proof_id": "proof-distance-contract-1",
                    "wallet_id": str(payload["wallet_id"]),
                    "proof_type": "location_distance",
                    "statement": payload["statement"],
                    "verifier_id": "verifier-http-v1",
                    "public_inputs": payload["public_inputs"],
                    "proof_hash": "proof-hash-distance-1",
                    "witness_record_ids": payload["witness_record_ids"],
                    "is_simulated": False,
                    "proof_system": "groth16",
                    "circuit_id": "location-distance-v1",
                    "verification_status": "verified",
                    "proof_artifact_ref": "https://verifier.example.test/proofs/proof-distance-contract-1",
                }
            }
        return {"verified": True}

    backend = HttpLocationRegionProofBackend(
        base_url="https://verifier.example.test",
        verifier_id="verifier-http-v1",
        proof_system="groth16",
        circuit_id="location-distance-v1",
        request_json=fake_request_json,
    )

    result = backend.validate_distance_contract()

    assert result["status"] == "ok"
    assert result["receipt"]["proof_id"] == "proof-distance-contract-1"
    assert [check["status"] for check in result["checks"]] == ["ok", "ok", "ok", "ok"]
    assert calls == [
        "https://verifier.example.test/health",
        "https://verifier.example.test/prove/location-distance",
        "https://verifier.example.test/verify",
    ]


def test_http_location_region_proof_backend_contract_validation_detects_witness_leak() -> None:
    def fake_request_json(
        method: str,
        url: str,
        payload: dict[str, object],
        headers: dict[str, str],
        timeout_seconds: float,
    ) -> dict[str, object]:
        if url.endswith("/health"):
            return {"ok": True, "status": "ready"}
        if url.endswith("/prove/location-region"):
            public_inputs = dict(payload["public_inputs"])
            public_inputs["lat"] = 45.5152
            return {
                "proof_id": "proof-contract-leak",
                "wallet_id": str(payload["wallet_id"]),
                "proof_type": "location_region",
                "statement": payload["statement"],
                "verifier_id": "verifier-http-v1",
                "public_inputs": public_inputs,
                "proof_hash": "proof-hash-1",
                "witness_record_ids": payload["witness_record_ids"],
                "is_simulated": False,
                "proof_system": "groth16",
                "circuit_id": "location-region-v1",
                "verification_status": "verified",
            }
        return {"verified": True}

    backend = HttpLocationRegionProofBackend(
        base_url="https://verifier.example.test",
        verifier_id="verifier-http-v1",
        proof_system="groth16",
        circuit_id="location-region-v1",
        request_json=fake_request_json,
    )

    result = backend.validate_contract()
    checks = {check["name"]: check for check in result["checks"]}

    assert result["status"] == "error"
    assert checks["public_input_safety"]["status"] == "error"


def test_http_location_distance_contract_validation_detects_target_coordinate_leak() -> None:
    def fake_request_json(
        method: str,
        url: str,
        payload: dict[str, object],
        headers: dict[str, str],
        timeout_seconds: float,
    ) -> dict[str, object]:
        if url.endswith("/health"):
            return {"ok": True, "status": "ready"}
        if url.endswith("/prove/location-distance"):
            public_inputs = dict(payload["public_inputs"])
            public_inputs["target_lat"] = 45.52
            return {
                "receipt": {
                    "proof_id": "proof-distance-contract-leak",
                    "wallet_id": str(payload["wallet_id"]),
                    "proof_type": "location_distance",
                    "statement": payload["statement"],
                    "verifier_id": "verifier-http-v1",
                    "public_inputs": public_inputs,
                    "proof_hash": "proof-hash-distance-1",
                    "witness_record_ids": payload["witness_record_ids"],
                    "is_simulated": False,
                    "proof_system": "groth16",
                    "circuit_id": "location-distance-v1",
                    "verification_status": "verified",
                }
            }
        return {"verified": True}

    backend = HttpLocationRegionProofBackend(
        base_url="https://verifier.example.test",
        verifier_id="verifier-http-v1",
        proof_system="groth16",
        circuit_id="location-distance-v1",
        request_json=fake_request_json,
    )

    result = backend.validate_distance_contract()
    checks = {check["name"]: check for check in result["checks"]}

    assert result["status"] == "error"
    assert checks["public_input_safety"]["status"] == "error"


def test_proof_backend_from_env_selects_http_backend(monkeypatch) -> None:
    monkeypatch.setenv("WALLET_PROOF_BACKEND", "http-location-region")
    monkeypatch.setenv("WALLET_PROOF_SERVICE_URL", "https://verifier.example.test")
    monkeypatch.setenv("WALLET_PROOF_VERIFIER_ID", "verifier-http-v1")
    monkeypatch.setenv("WALLET_PROOF_SYSTEM", "groth16")
    monkeypatch.setenv("WALLET_PROOF_CIRCUIT_ID", "location-region-v1")
    monkeypatch.setenv("WALLET_PROOF_PROVE_PATH", "/prove/location-region")
    monkeypatch.setenv("WALLET_PROOF_DISTANCE_PROVE_PATH", "/prove/location-distance")
    monkeypatch.setenv("WALLET_PROOF_VERIFY_PATH", "/verify")
    monkeypatch.setenv("WALLET_PROOF_BEARER_TOKEN", "verifier-secret")
    monkeypatch.setenv("WALLET_PROOF_HTTP_HEADER_NAME", "x-wallet-proof-key")
    monkeypatch.setenv("WALLET_PROOF_HTTP_HEADER_VALUE", "shared")
    monkeypatch.setenv("WALLET_PROOF_TIMEOUT_SECONDS", "12.5")

    backend = _proof_backend_from_env()

    assert isinstance(backend, HttpLocationRegionProofBackend)
    assert backend.base_url == "https://verifier.example.test"
    assert backend.verifier_id == "verifier-http-v1"
    assert backend.proof_system == "groth16"
    assert backend.circuit_id == "location-region-v1"
    assert backend.distance_prove_path == "/prove/location-distance"
    assert backend.timeout_seconds == 12.5
    assert backend.extra_headers["authorization"] == "Bearer verifier-secret"
    assert backend.extra_headers["x-wallet-proof-key"] == "shared"


def test_proof_backend_from_env_requires_header_value(monkeypatch) -> None:
    monkeypatch.setenv("WALLET_PROOF_BACKEND", "http-location-region")
    monkeypatch.setenv("WALLET_PROOF_SERVICE_URL", "https://verifier.example.test")
    monkeypatch.setenv("WALLET_PROOF_HTTP_HEADER_NAME", "x-wallet-proof-key")
    monkeypatch.delenv("WALLET_PROOF_HTTP_HEADER_VALUE", raising=False)

    try:
        _proof_backend_from_env()
    except ValueError as exc:
        assert "WALLET_PROOF_HTTP_HEADER_VALUE" in str(exc)
    else:
        assert False, "expected ValueError when proof header value is missing"
