#!/usr/bin/env python3
"""Fail closed until a Hugging Face Space is ready on expected hardware."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Callable, Mapping

EXIT_TIMEOUT = 75
EXIT_HARDWARE_DRIFT = 78


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--space-repo-id",
        default=os.getenv(
            "ABBY_TTS_SPACE_REPO_ID",
            "Publicus/IndexTTS-2-Demo",
        ),
    )
    parser.add_argument(
        "--expected-hardware",
        default=os.getenv("ABBY_TTS_EXPECTED_HARDWARE", "l40sx1"),
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=float(
            os.getenv("ABBY_TTS_HARDWARE_WAIT_SECONDS", "1800") or "1800"
        ),
    )
    parser.add_argument(
        "--poll-interval-seconds",
        type=float,
        default=float(
            os.getenv("ABBY_TTS_HARDWARE_POLL_SECONDS", "15") or "15"
        ),
    )
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=None,
        help="Exit successfully without waking the Space when this queue is complete.",
    )
    parser.add_argument(
        "--wake-sleeping",
        action="store_true",
        help="Restart a sleeping Space only when its requested hardware matches.",
    )
    return parser.parse_args(argv)


def queue_complete(path: Path | None) -> bool:
    if path is None or not path.is_file():
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        next_offset = int(payload.get("nextOffset", 0))
        total = int(payload.get("totalResponses", 0))
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return False
    return total > 0 and next_offset >= total


def runtime_snapshot(runtime: Any) -> dict[str, Any]:
    raw = runtime.raw if isinstance(getattr(runtime, "raw", None), Mapping) else {}
    domains = raw.get("domains") if isinstance(raw, Mapping) else []
    domain_stages = [
        str(item.get("stage") or "").strip().upper()
        for item in domains or []
        if isinstance(item, Mapping)
    ]
    return {
        "stage": str(getattr(runtime, "stage", "") or "").strip().upper(),
        "hardware": str(getattr(runtime, "hardware", "") or "").strip().lower(),
        "requestedHardware": str(
            getattr(runtime, "requested_hardware", "") or ""
        )
        .strip()
        .lower(),
        "domainStages": domain_stages,
    }


def runtime_ready(snapshot: Mapping[str, Any], expected_hardware: str) -> bool:
    expected = expected_hardware.strip().lower()
    domain_stages = list(snapshot.get("domainStages") or [])
    domain_ready = not domain_stages or "READY" in domain_stages
    return (
        snapshot.get("stage") == "RUNNING"
        and snapshot.get("hardware") == expected
        and snapshot.get("requestedHardware") == expected
        and domain_ready
    )


def requested_hardware_drifted(
    snapshot: Mapping[str, Any],
    expected_hardware: str,
) -> bool:
    requested = str(snapshot.get("requestedHardware") or "").strip().lower()
    return bool(requested and requested != expected_hardware.strip().lower())


def wait_for_hardware(
    api: Any,
    *,
    space_repo_id: str,
    expected_hardware: str,
    timeout_seconds: float,
    poll_interval_seconds: float,
    checkpoint: Path | None = None,
    wake_sleeping: bool = False,
    clock: Callable[[], float] = time.monotonic,
    sleeper: Callable[[float], None] = time.sleep,
) -> int:
    if queue_complete(checkpoint):
        print("[hardware-gate] queue already complete; no Space wake required")
        return 0

    started = clock()
    last_status = ""
    wake_requested = False
    while True:
        try:
            runtime = api.get_space_runtime(space_repo_id)
            snapshot = runtime_snapshot(runtime)
        except Exception as exc:
            snapshot = {"error": f"{type(exc).__name__}: {exc}"}

        status = json.dumps(snapshot, sort_keys=True)
        if status != last_status:
            print(f"[hardware-gate] {status}", flush=True)
            last_status = status

        if "error" not in snapshot:
            if requested_hardware_drifted(snapshot, expected_hardware):
                print(
                    "[hardware-gate] requested hardware drift: "
                    f"expected={expected_hardware!r} "
                    f"observed={snapshot.get('requestedHardware')!r}",
                    file=sys.stderr,
                )
                return EXIT_HARDWARE_DRIFT
            if runtime_ready(snapshot, expected_hardware):
                return 0
            if (
                wake_sleeping
                and not wake_requested
                and snapshot.get("stage") in {"PAUSED", "SLEEPING"}
                and snapshot.get("hardware") == expected_hardware.strip().lower()
                and snapshot.get("requestedHardware")
                == expected_hardware.strip().lower()
            ):
                api.restart_space(space_repo_id)
                wake_requested = True
                print("[hardware-gate] requested Space restart", flush=True)

        elapsed = clock() - started
        if timeout_seconds > 0 and elapsed >= timeout_seconds:
            print(
                f"[hardware-gate] timed out after {elapsed:.1f}s",
                file=sys.stderr,
            )
            return EXIT_TIMEOUT
        sleeper(max(0.1, poll_interval_seconds))


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        from huggingface_hub import HfApi
    except ImportError as exc:
        print(f"[hardware-gate] huggingface_hub unavailable: {exc}", file=sys.stderr)
        return EXIT_HARDWARE_DRIFT
    return wait_for_hardware(
        HfApi(),
        space_repo_id=str(args.space_repo_id),
        expected_hardware=str(args.expected_hardware),
        timeout_seconds=max(0.0, float(args.timeout_seconds)),
        poll_interval_seconds=max(0.1, float(args.poll_interval_seconds)),
        checkpoint=args.checkpoint,
        wake_sleeping=bool(args.wake_sleeping),
    )


if __name__ == "__main__":
    raise SystemExit(main())
