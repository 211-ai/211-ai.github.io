from __future__ import annotations

import json
from io import StringIO

from wallet_interface import WalletInterfaceService
from wallet_interface.ops import (
    WalletOpsHealthWorker,
    main,
    validate_distance_proof_contract,
    validate_production_readiness,
    validate_proof_contract,
)
from wallet_interface.proof_backends import HttpLocationRegionProofBackend


def test_ops_health_worker_emits_jsonl_report() -> None:
    service = WalletInterfaceService()
    output = StringIO()

    result = WalletOpsHealthWorker(
        service=service,
        verify_storage=False,
        max_runs=1,
        output=output,
    ).run()

    lines = output.getvalue().strip().splitlines()
    report = json.loads(lines[0])

    assert result.report_count == 1
    assert result.exit_code == 0
    assert report["status"] in {"ok", "warning"}
    assert {check["name"] for check in report["checks"]} >= {
        "repository",
        "storage_availability",
        "proof_registry",
        "revocation_propagation",
        "privacy_budget",
    }


def test_ops_health_worker_can_fail_on_error_status() -> None:
    service = WalletInterfaceService()
    service.wallet_service.analytics_query_budget_spent["bad-budget"] = -0.5
    output = StringIO()

    result = WalletOpsHealthWorker(
        service=service,
        verify_storage=False,
        max_runs=1,
        fail_on_error=True,
        output=output,
    ).run()
    report = json.loads(output.getvalue())

    assert result.exit_code == 2
    assert report["status"] == "error"
    checks = {check["name"]: check for check in report["checks"]}
    assert checks["privacy_budget"]["status"] == "error"


def test_ops_health_cli_writes_jsonl_file(tmp_path) -> None:
    output_path = tmp_path / "ops" / "health.jsonl"

    exit_code = main(
        [
            "--repository-root",
            str(tmp_path / "wallet-repository"),
            "--skip-storage-verify",
            "--output-jsonl",
            str(output_path),
        ]
    )

    assert exit_code == 0
    report = json.loads(output_path.read_text(encoding="utf-8"))
    assert report["check_count"] >= 5


def test_ops_health_worker_sends_webhook_alert_for_error_status() -> None:
    service = WalletInterfaceService()
    service.wallet_service.analytics_query_budget_spent["bad-budget"] = -0.5
    output = StringIO()
    sent: list[tuple[str, dict[str, object], dict[str, str]]] = []

    result = WalletOpsHealthWorker(
        service=service,
        verify_storage=False,
        max_runs=1,
        output=output,
        alert_webhook_url="https://ops.example.test/hooks/wallet",
        alert_on="error",
        alert_sender=lambda url, payload, headers: sent.append((url, payload, headers)),
    ).run()

    assert result.alert_count == 1
    assert len(sent) == 1
    url, payload, headers = sent[0]
    assert url == "https://ops.example.test/hooks/wallet"
    assert payload["status"] == "error"
    assert payload["source"] == "wallet_interface.ops"
    assert headers == {}
    assert any(check["name"] == "privacy_budget" for check in payload["checks"])


def test_ops_health_worker_does_not_send_webhook_alert_below_threshold() -> None:
    service = WalletInterfaceService()
    output = StringIO()
    sent: list[tuple[str, dict[str, object], dict[str, str]]] = []

    result = WalletOpsHealthWorker(
        service=service,
        verify_storage=False,
        max_runs=1,
        output=output,
        alert_webhook_url="https://ops.example.test/hooks/wallet",
        alert_on="error",
        alert_sender=lambda url, payload, headers: sent.append((url, payload, headers)),
    ).run()

    report = json.loads(output.getvalue())
    assert report["status"] == "warning"
    assert result.alert_count == 0
    assert sent == []


def test_ops_health_worker_reads_alert_auth_headers_from_env(monkeypatch) -> None:
    service = WalletInterfaceService()
    service.wallet_service.analytics_query_budget_spent["bad-budget"] = -0.5
    output = StringIO()
    sent: list[tuple[str, dict[str, object], dict[str, str]]] = []
    monkeypatch.setenv("WALLET_OPS_ALERT_BEARER_TOKEN", "alert-token")
    monkeypatch.setenv("WALLET_OPS_ALERT_HEADER_NAME", "x-wallet-alert-key")
    monkeypatch.setenv("WALLET_OPS_ALERT_HEADER_VALUE", "shared-header")

    WalletOpsHealthWorker(
        service=service,
        verify_storage=False,
        max_runs=1,
        output=output,
        alert_webhook_url="https://ops.example.test/hooks/wallet",
        alert_on="error",
        alert_sender=lambda url, payload, headers: sent.append((url, payload, headers)),
    ).run()

    assert len(sent) == 1
    _, _, headers = sent[0]
    assert headers["authorization"] == "Bearer alert-token"
    assert headers["x-wallet-alert-key"] == "shared-header"


def test_validate_proof_contract_reports_error_for_non_http_backend() -> None:
    report = validate_proof_contract(WalletInterfaceService())

    assert report["status"] == "error"
    assert report["checks"][0]["name"] == "backend"


def test_validate_proof_contract_reports_http_backend_success() -> None:
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
            return {
                "proof_id": "proof-contract-ops",
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
            }
        return {"verified": True}

    service = WalletInterfaceService(
        proof_backend=HttpLocationRegionProofBackend(
            base_url="https://verifier.example.test",
            verifier_id="verifier-http-v1",
            proof_system="groth16",
            circuit_id="location-region-v1",
            request_json=fake_request_json,
        ),
        allow_simulated_proofs=False,
    )

    report = validate_proof_contract(service)

    assert report["status"] == "ok"
    assert report["receipt"]["proof_id"] == "proof-contract-ops"
    assert {check["name"] for check in report["checks"]} == {
        "health",
        "prove",
        "public_input_safety",
        "verify",
    }


def test_validate_distance_proof_contract_reports_error_for_non_http_backend() -> None:
    report = validate_distance_proof_contract(WalletInterfaceService())

    assert report["status"] == "error"
    assert report["checks"][0]["name"] == "backend"


def test_validate_distance_proof_contract_reports_http_backend_success() -> None:
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
            return {
                "proof_id": "proof-distance-contract-ops",
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
            }
        return {"verified": True}

    service = WalletInterfaceService(
        proof_backend=HttpLocationRegionProofBackend(
            base_url="https://verifier.example.test",
            verifier_id="verifier-http-v1",
            proof_system="groth16",
            circuit_id="location-distance-v1",
            request_json=fake_request_json,
        ),
        allow_simulated_proofs=False,
    )

    report = validate_distance_proof_contract(service)

    assert report["status"] == "ok"
    assert report["receipt"]["proof_id"] == "proof-distance-contract-ops"
    assert {check["name"] for check in report["checks"]} == {
        "health",
        "prove",
        "public_input_safety",
        "verify",
    }


def test_ops_cli_accepts_distance_proof_contract_validation_flag(tmp_path) -> None:
    output_path = tmp_path / "ops" / "distance-proof-contract.jsonl"

    exit_code = main(
        [
            "--validate-distance-proof-contract",
            "--output-jsonl",
            str(output_path),
        ]
    )

    report = json.loads(output_path.read_text(encoding="utf-8"))
    assert exit_code == 2
    assert report["status"] == "error"
    assert report["checks"][0]["name"] == "backend"


def test_validate_production_readiness_reports_missing_target_environment() -> None:
    report = validate_production_readiness(
        WalletInterfaceService(),
        env={},
        run_proof_contract=False,
        verify_storage=False,
    )

    checks = {check["name"]: check for check in report["checks"]}
    assert report["status"] == "error"
    assert checks["persistence_environment"]["status"] == "error"
    assert checks["proof_environment"]["status"] == "error"
    assert checks["proof_credentials"]["status"] == "error"
    assert checks["ops_credentials"]["status"] == "error"


def test_validate_production_readiness_passes_with_configured_http_verifier(tmp_path) -> None:
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
            return {
                "proof_id": "proof-contract-ready",
                "wallet_id": str(payload["wallet_id"]),
                "proof_type": "location_region",
                "statement": payload["statement"],
                "verifier_id": "verifier-http-v1",
                "public_inputs": payload["public_inputs"],
                "proof_hash": "proof-hash-ready",
                "witness_record_ids": payload["witness_record_ids"],
                "is_simulated": False,
                "proof_system": "groth16",
                "circuit_id": "location-region-v1",
                "verification_status": "verified",
            }
        return {"verified": True}

    repository_root = tmp_path / "wallet-repository"
    storage_root = tmp_path / "wallet-blobs"
    service = WalletInterfaceService(
        repository_root=repository_root,
        storage_config={"primary": {"type": "local", "root": str(storage_root)}},
        proof_backend=HttpLocationRegionProofBackend(
            base_url="https://verifier.staging.211.local",
            verifier_id="verifier-http-v1",
            proof_system="groth16",
            circuit_id="location-region-v1",
            request_json=fake_request_json,
        ),
        allow_simulated_proofs=False,
    )
    env = {
        "WALLET_REPOSITORY_ROOT": str(repository_root),
        "WALLET_STORAGE_CONFIG": json.dumps({"primary": {"type": "local", "root": str(storage_root)}}),
        "WALLET_AUTO_LOAD_REPOSITORY": "true",
        "WALLET_AUTO_PERSIST": "true",
        "WALLET_PROOF_MODE": "production",
        "WALLET_PROOF_BACKEND": "http-location-region",
        "WALLET_PROOF_SERVICE_URL": "https://verifier.staging.211.local",
        "WALLET_PROOF_VERIFIER_ID": "verifier-http-v1",
        "WALLET_PROOF_SYSTEM": "groth16",
        "WALLET_PROOF_CIRCUIT_ID": "location-region-v1",
        "WALLET_PROOF_BEARER_TOKEN": "proof-service-token",
        "WALLET_OPS_HEALTH_SHARED_SECRET": "ops-health-secret",
        "WALLET_OPS_ALERT_WEBHOOK_URL": "https://ops.staging.211.local/hooks/wallet",
        "WALLET_OPS_ALERT_BEARER_TOKEN": "ops-alert-token",
    }

    report = validate_production_readiness(
        service,
        env=env,
        run_proof_contract=True,
        verify_storage=False,
    )

    assert report["status"] == "ok"
    assert {check["name"]: check["status"] for check in report["checks"]} == {
        "persistence_environment": "ok",
        "proof_environment": "ok",
        "proof_credentials": "ok",
        "ops_credentials": "ok",
        "ops_health": "ok",
        "proof_contract": "ok",
    }
    rendered = json.dumps(report)
    assert "proof-service-token" not in rendered
    assert "ops-alert-token" not in rendered
    assert "ops-health-secret" not in rendered
