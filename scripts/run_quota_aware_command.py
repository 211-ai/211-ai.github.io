#!/usr/bin/env python3
"""Run a command persistently while honoring exit 75 and state.retryAfter."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.retry_after_policy import retry_after_decision_from_state  # noqa: E402


EXIT_RATE_LIMITED = 75


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, required=True, help="Checkpoint containing updatedAt and retryAfter.")
    parser.add_argument(
        "--status",
        type=Path,
        default=None,
        help="Observable launcher status JSON. Defaults to <state>.quota-retry.json.",
    )
    parser.add_argument("--rate-limit-exit-code", type=int, default=EXIT_RATE_LIMITED)
    parser.add_argument(
        "--quota-fallback-delay-seconds",
        type=float,
        default=300.0,
        help="Delay when exit 75 has no parseable state.retryAfter.",
    )
    parser.add_argument(
        "--quota-minimum-delay-seconds",
        type=float,
        default=60.0,
        help="Minimum delay after any quota exit, including an expired checkpoint.",
    )
    parser.add_argument(
        "--quota-grace-seconds",
        type=float,
        default=15.0,
        help="Extra delay after the provider's advertised retry time.",
    )
    parser.add_argument(
        "--max-quota-retries",
        type=int,
        default=0,
        help="Maximum quota retries in this process; 0 waits persistently.",
    )
    parser.add_argument("command", nargs=argparse.REMAINDER, help="Command to run after --.")
    args = parser.parse_args(argv)
    if args.command[:1] == ["--"]:
        args.command = args.command[1:]
    if not args.command:
        parser.error("a command is required after --")
    if not 1 <= args.rate_limit_exit_code <= 255:
        parser.error("--rate-limit-exit-code must be between 1 and 255")
    if args.quota_fallback_delay_seconds < 0:
        parser.error("--quota-fallback-delay-seconds must be at least 0")
    if args.quota_minimum_delay_seconds < 0:
        parser.error("--quota-minimum-delay-seconds must be at least 0")
    if args.quota_grace_seconds < 0:
        parser.error("--quota-grace-seconds must be at least 0")
    if args.max_quota_retries < 0:
        parser.error("--max-quota-retries must be at least 0")
    if args.status is None:
        args.status = Path(f"{args.state}.quota-retry.json")
    return args


def read_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}
    return payload if isinstance(payload, dict) else {}


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def write_status(path: Path, *, phase: str, attempt: int, quota_exit_count: int, **fields: Any) -> None:
    write_json_atomic(
        path,
        {
            "schemaVersion": 1,
            "updatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "phase": phase,
            "attempt": attempt,
            "quotaExitCount": quota_exit_count,
            **fields,
        },
    )


def normalized_exit_code(returncode: int) -> int:
    if returncode < 0:
        return min(255, 128 + abs(returncode))
    return min(255, returncode)


def wait_for_quota(
    args: argparse.Namespace,
    *,
    state: dict[str, Any],
    attempt: int,
    quota_exit_count: int,
    child_exit_code: int | None,
    resumed_from_checkpoint: bool,
) -> None:
    decision = retry_after_decision_from_state(
        state,
        now_epoch=time.time(),
        fallback_seconds=args.quota_fallback_delay_seconds,
        minimum_seconds=args.quota_minimum_delay_seconds,
        grace_seconds=args.quota_grace_seconds,
    )
    write_status(
        args.status,
        phase="waiting_for_quota",
        attempt=attempt,
        quota_exit_count=quota_exit_count,
        statePath=str(args.state),
        stateUpdatedAt=str(state.get("updatedAt") or ""),
        **({"childExitCode": child_exit_code} if child_exit_code is not None else {}),
        retryAfter=decision.raw_value,
        retryAt=decision.retry_at_utc,
        delaySeconds=round(decision.delay_seconds, 3),
        retryValueKind=decision.value_kind,
        usedFallback=decision.used_fallback,
        resumedFromCheckpoint=resumed_from_checkpoint,
    )
    source = "checkpoint" if resumed_from_checkpoint else f"exit {child_exit_code}"
    print(
        f"[quota-launcher] {source}; waiting {decision.delay_seconds:.1f}s "
        f"until {decision.retry_at_utc} "
        f"(retryAfter={decision.raw_value!r}, fallback={decision.used_fallback})",
        flush=True,
    )
    time.sleep(decision.delay_seconds)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    attempt = 0
    quota_exit_count = 0
    initial_state = read_json_object(args.state)
    if str(initial_state.get("retryAfter") or "").strip():
        wait_for_quota(
            args,
            state=initial_state,
            attempt=attempt,
            quota_exit_count=quota_exit_count,
            child_exit_code=None,
            resumed_from_checkpoint=True,
        )

    while True:
        attempt += 1
        write_status(
            args.status,
            phase="running",
            attempt=attempt,
            quota_exit_count=quota_exit_count,
            statePath=str(args.state),
        )
        print(f"[quota-launcher] starting attempt {attempt}", flush=True)
        try:
            completed = subprocess.run(args.command, check=False)
        except OSError as exc:
            write_status(
                args.status,
                phase="launch_failed",
                attempt=attempt,
                quota_exit_count=quota_exit_count,
                statePath=str(args.state),
                error=f"{type(exc).__name__}: {exc}",
            )
            print(f"[quota-launcher] command launch failed: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
            return 1

        returncode = normalized_exit_code(int(completed.returncode))
        if returncode == 0:
            write_status(
                args.status,
                phase="complete",
                attempt=attempt,
                quota_exit_count=quota_exit_count,
                statePath=str(args.state),
                childExitCode=returncode,
            )
            print(f"[quota-launcher] command completed on attempt {attempt}", flush=True)
            return 0

        if returncode != args.rate_limit_exit_code:
            write_status(
                args.status,
                phase="failed",
                attempt=attempt,
                quota_exit_count=quota_exit_count,
                statePath=str(args.state),
                childExitCode=returncode,
            )
            print(
                f"[quota-launcher] non-quota failure exit={returncode}; returning control to the service manager",
                file=sys.stderr,
                flush=True,
            )
            return returncode

        quota_exit_count += 1
        if args.max_quota_retries > 0 and quota_exit_count > args.max_quota_retries:
            write_status(
                args.status,
                phase="quota_retry_exhausted",
                attempt=attempt,
                quota_exit_count=quota_exit_count,
                statePath=str(args.state),
                childExitCode=returncode,
            )
            print(
                f"[quota-launcher] quota retry budget exhausted after {quota_exit_count - 1} retries",
                file=sys.stderr,
                flush=True,
            )
            return returncode

        wait_for_quota(
            args,
            state=read_json_object(args.state),
            attempt=attempt,
            quota_exit_count=quota_exit_count,
            child_exit_code=returncode,
            resumed_from_checkpoint=False,
        )


if __name__ == "__main__":
    raise SystemExit(main())
