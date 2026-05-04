"""Operations worker for wallet health checks."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, IO, Sequence
from urllib import request as urllib_request

from .app_service import WalletInterfaceService


@dataclass
class OpsHealthRunResult:
    """Summary returned by a bounded ops-health worker run."""

    report_count: int
    statuses: list[str] = field(default_factory=list)
    alert_count: int = 0
    exit_code: int = 0


def _alert_rank(status: str) -> int:
    if status == "error":
        return 2
    if status == "warning":
        return 1
    return 0


def _alert_headers_from_env() -> dict[str, str]:
    headers: dict[str, str] = {}
    bearer_token = str(os.getenv("WALLET_OPS_ALERT_BEARER_TOKEN") or "").strip()
    if bearer_token:
        headers["authorization"] = f"Bearer {bearer_token}"
    header_name = str(os.getenv("WALLET_OPS_ALERT_HEADER_NAME") or "").strip()
    header_value = str(os.getenv("WALLET_OPS_ALERT_HEADER_VALUE") or "").strip()
    if header_name and header_value:
        headers[header_name] = header_value
    return headers


def _default_alert_sender(url: str, payload: dict[str, Any], headers: dict[str, str] | None = None) -> None:
    body = json.dumps(payload, sort_keys=True).encode("utf-8")
    request_headers = {"content-type": "application/json"}
    if headers:
        request_headers.update(headers)
    req = urllib_request.Request(
        url,
        data=body,
        headers=request_headers,
        method="POST",
    )
    with urllib_request.urlopen(req, timeout=10) as response:
        if response.status >= 400:
            raise RuntimeError(f"alert webhook returned HTTP {response.status}")


class WalletOpsHealthWorker:
    """Run wallet ops-health checks on a schedule and emit JSONL reports."""

    def __init__(
        self,
        *,
        service: WalletInterfaceService | None = None,
        verify_storage: bool = True,
        interval_seconds: float = 300.0,
        max_runs: int | None = 1,
        fail_on_error: bool = False,
        fail_on_warning: bool = False,
        alert_webhook_url: str | None = None,
        alert_on: str = "error",
        alert_headers: dict[str, str] | None = None,
        alert_sender: Callable[[str, dict[str, Any], dict[str, str]], None] | None = None,
        output: IO[str] | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if interval_seconds < 0:
            raise ValueError("interval_seconds must be non-negative")
        if max_runs is not None and max_runs < 1:
            raise ValueError("max_runs must be at least 1")
        self.service = service or WalletInterfaceService()
        self.verify_storage = verify_storage
        self.interval_seconds = interval_seconds
        self.max_runs = max_runs
        self.fail_on_error = fail_on_error
        self.fail_on_warning = fail_on_warning
        self.alert_webhook_url = str(
            alert_webhook_url or os.getenv("WALLET_OPS_ALERT_WEBHOOK_URL") or ""
        ).strip() or None
        normalized_alert_on = str(alert_on or os.getenv("WALLET_OPS_ALERT_ON") or "error").strip().lower()
        if normalized_alert_on not in {"warning", "error"}:
            raise ValueError("alert_on must be warning or error")
        self.alert_on = normalized_alert_on
        self.alert_headers = dict(alert_headers or _alert_headers_from_env())
        self.alert_sender = alert_sender or _default_alert_sender
        self.output = output or sys.stdout
        self.sleep = sleep

    def run_once(self) -> dict[str, Any]:
        report = self.service.ops_health(verify_storage=self.verify_storage)
        self._write_report(report)
        self._send_alert_if_needed(report)
        return report

    def run(self) -> OpsHealthRunResult:
        statuses: list[str] = []
        report_count = 0
        alert_count = 0
        try:
            while self.max_runs is None or report_count < self.max_runs:
                report = self.run_once()
                statuses.append(str(report.get("status", "unknown")))
                report_count += 1
                if self._should_alert(str(report.get("status", "unknown"))):
                    alert_count += 1
                if self.max_runs is not None and report_count >= self.max_runs:
                    break
                self.sleep(self.interval_seconds)
        except KeyboardInterrupt:  # pragma: no cover - interactive shutdown path.
            pass
        return OpsHealthRunResult(
            report_count=report_count,
            statuses=statuses,
            alert_count=alert_count,
            exit_code=self._exit_code(statuses),
        )

    def _exit_code(self, statuses: list[str]) -> int:
        if self.fail_on_error and "error" in statuses:
            return 2
        if self.fail_on_warning and any(status in {"warning", "error"} for status in statuses):
            return 1
        return 0

    def _write_report(self, report: dict[str, Any]) -> None:
        self.output.write(json.dumps(report, sort_keys=True))
        self.output.write("\n")
        self.output.flush()

    def _should_alert(self, status: str) -> bool:
        return bool(self.alert_webhook_url) and _alert_rank(status) >= _alert_rank(self.alert_on)

    def _send_alert_if_needed(self, report: dict[str, Any]) -> None:
        status = str(report.get("status", "unknown"))
        if not self._should_alert(status):
            return
        check_summaries = [
            {
                "name": str(check.get("name")),
                "status": str(check.get("status")),
                "summary": str(check.get("summary")),
            }
            for check in report.get("checks", [])
            if isinstance(check, dict) and str(check.get("status")) in {"warning", "error"}
        ]
        payload = {
            "source": "wallet_interface.ops",
            "status": status,
            "generated_at": report.get("generated_at"),
            "wallet_count": report.get("wallet_count"),
            "check_count": report.get("check_count"),
            "checks": check_summaries,
            "report": report,
        }
        assert self.alert_webhook_url is not None
        self.alert_sender(self.alert_webhook_url, payload, dict(self.alert_headers))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run 211-AI wallet ops-health checks.")
    parser.add_argument(
        "--repository-root",
        help="Wallet repository root. Defaults to WALLET_REPOSITORY_ROOT.",
    )
    parser.add_argument(
        "--interval-seconds",
        type=float,
        default=300.0,
        help="Delay between checks in watch mode. Default: 300.",
    )
    parser.add_argument(
        "--max-runs",
        type=int,
        help="Bounded number of checks to run. Default: 1 unless --watch is set.",
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Run until interrupted instead of exiting after one check.",
    )
    parser.add_argument(
        "--skip-storage-verify",
        action="store_false",
        dest="verify_storage",
        default=True,
        help="Do not read encrypted blob replicas during the health check.",
    )
    parser.add_argument(
        "--fail-on-error",
        action="store_true",
        help="Exit 2 when any emitted report has status=error.",
    )
    parser.add_argument(
        "--fail-on-warning",
        action="store_true",
        help="Exit 1 when any emitted report has status=warning or status=error.",
    )
    parser.add_argument(
        "--output-jsonl",
        help="Append JSONL reports to this file instead of stdout.",
    )
    parser.add_argument(
        "--alert-webhook-url",
        help="POST matching warning/error reports to this webhook. Defaults to WALLET_OPS_ALERT_WEBHOOK_URL.",
    )
    parser.add_argument(
        "--alert-on",
        choices=("warning", "error"),
        default=os.getenv("WALLET_OPS_ALERT_ON", "error"),
        help="Minimum report status that triggers webhook alerts. Default: error.",
    )
    parser.add_argument(
        "--alert-bearer-token",
        help="Bearer token for the alert webhook. Defaults to WALLET_OPS_ALERT_BEARER_TOKEN.",
    )
    parser.add_argument(
        "--alert-header-name",
        help="Custom header name for the alert webhook. Defaults to WALLET_OPS_ALERT_HEADER_NAME.",
    )
    parser.add_argument(
        "--alert-header-value",
        help="Custom header value for the alert webhook. Defaults to WALLET_OPS_ALERT_HEADER_VALUE.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    max_runs = args.max_runs
    if args.watch and max_runs is None:
        max_runs = None
    elif max_runs is None:
        max_runs = 1

    output: IO[str] | None = None
    try:
        if args.output_jsonl:
            output_path = Path(args.output_jsonl)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output = output_path.open("a", encoding="utf-8")
        alert_headers = _alert_headers_from_env()
        if args.alert_bearer_token:
            alert_headers["authorization"] = f"Bearer {args.alert_bearer_token}"
        if args.alert_header_name and args.alert_header_value:
            alert_headers[args.alert_header_name] = args.alert_header_value
        service = WalletInterfaceService(repository_root=args.repository_root)
        worker = WalletOpsHealthWorker(
            service=service,
            verify_storage=args.verify_storage,
            interval_seconds=args.interval_seconds,
            max_runs=max_runs,
            fail_on_error=args.fail_on_error,
            fail_on_warning=args.fail_on_warning,
            alert_webhook_url=args.alert_webhook_url,
            alert_on=args.alert_on,
            alert_headers=alert_headers,
            output=output or sys.stdout,
        )
        return worker.run().exit_code
    finally:
        if output is not None:
            output.close()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
