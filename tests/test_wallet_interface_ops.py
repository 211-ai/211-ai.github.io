from __future__ import annotations

import json
from io import StringIO

from wallet_interface import WalletInterfaceService
from wallet_interface.ops import WalletOpsHealthWorker, main


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
