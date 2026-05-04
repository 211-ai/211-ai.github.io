"""Operations worker for wallet health checks."""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, IO, Sequence

from .app_service import WalletInterfaceService


@dataclass
class OpsHealthRunResult:
    """Summary returned by a bounded ops-health worker run."""

    report_count: int
    statuses: list[str] = field(default_factory=list)
    exit_code: int = 0


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
        self.output = output or sys.stdout
        self.sleep = sleep

    def run_once(self) -> dict[str, Any]:
        report = self.service.ops_health(verify_storage=self.verify_storage)
        self._write_report(report)
        return report

    def run(self) -> OpsHealthRunResult:
        statuses: list[str] = []
        report_count = 0
        try:
            while self.max_runs is None or report_count < self.max_runs:
                report = self.run_once()
                statuses.append(str(report.get("status", "unknown")))
                report_count += 1
                if self.max_runs is not None and report_count >= self.max_runs:
                    break
                self.sleep(self.interval_seconds)
        except KeyboardInterrupt:  # pragma: no cover - interactive shutdown path.
            pass
        return OpsHealthRunResult(
            report_count=report_count,
            statuses=statuses,
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
        service = WalletInterfaceService(repository_root=args.repository_root)
        worker = WalletOpsHealthWorker(
            service=service,
            verify_storage=args.verify_storage,
            interval_seconds=args.interval_seconds,
            max_runs=max_runs,
            fail_on_error=args.fail_on_error,
            fail_on_warning=args.fail_on_warning,
            output=output or sys.stdout,
        )
        return worker.run().exit_code
    finally:
        if output is not None:
            output.close()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

