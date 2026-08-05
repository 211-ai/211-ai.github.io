#!/usr/bin/env python3
"""Control wrapper for voice-app-surface-coverage supervisor bootstrap (VAS2-001)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
PROFILE_PATH = (
    REPO_ROOT / "docs" / "planning" / "voice_app_surface_full_coverage.supervisor.json"
)
RUNTIME_POLICY_PATH = (
    REPO_ROOT / "docs" / "voice_app_surface_full_coverage" / "runtime-policy.json"
)
VALIDATOR = REPO_ROOT / "scripts" / "validate_voice_app_surface_full_coverage_plan.py"
PROGRAM_ID = "voice-app-surface-full-coverage-v2"
BOARD_NAMESPACE = "voice-app-surface-full-coverage-v2"
STATE_ROOT_ENV = "VOICE_APP_SURFACE_FULL_COVERAGE_SUPERVISOR_STATE_ROOT"


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must be a JSON object")
    return payload


def validate_config() -> dict[str, Any]:
    errors: list[str] = []
    if not PROFILE_PATH.is_file():
        errors.append(f"missing launch profile: {PROFILE_PATH}")
    if not RUNTIME_POLICY_PATH.is_file():
        errors.append(f"missing runtime policy: {RUNTIME_POLICY_PATH}")
    if not VALIDATOR.is_file():
        errors.append(f"missing validator: {VALIDATOR}")

    profile: dict[str, Any] = {}
    policy: dict[str, Any] = {}
    if PROFILE_PATH.is_file():
        try:
            profile = _load_json(PROFILE_PATH)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            errors.append(f"profile unreadable: {exc}")
    if RUNTIME_POLICY_PATH.is_file():
        try:
            policy = _load_json(RUNTIME_POLICY_PATH)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            errors.append(f"runtime policy unreadable: {exc}")

    if profile:
        if profile.get("program_id") != PROGRAM_ID:
            errors.append("profile program_id mismatch")
        if profile.get("board_namespace") != BOARD_NAMESPACE:
            errors.append("profile board_namespace mismatch")
        layout = profile.get("state_layout") or {}
        if isinstance(layout, dict) and layout.get("state_root_env") != STATE_ROOT_ENV:
            errors.append("profile state_root_env mismatch")
        if profile.get("max_lanes") != 4 or profile.get("task_shard_count") != 4:
            errors.append("expected 4 lanes / 4 shards")
        lanes = profile.get("lanes")
        if not isinstance(lanes, list) or len(lanes) != 4:
            errors.append("expected exactly 4 lanes")
        else:
            owners = [
                lane.get("lane_id")
                for lane in lanes
                if isinstance(lane, dict) and lane.get("objective_refill_owner")
            ]
            if owners != ["vas2-grok-0"]:
                errors.append("refill owner must be only vas2-grok-0")

    if policy:
        if policy.get("program_id") != PROGRAM_ID:
            errors.append("runtime policy program_id mismatch")
        for key in (
            "network",
            "credentials",
            "publication",
            "live_telephony",
            "live_sms",
            "hf_publish",
            "live_tts_space",
        ):
            if policy.get(key) != "deny":
                errors.append(f"runtime policy {key} must be deny")
        if policy.get("require_fake_adapters") is not True:
            errors.append("runtime policy require_fake_adapters must be true")
        if policy.get("refill_owner_lane_id") != "vas2-grok-0":
            errors.append("runtime policy refill owner mismatch")

    return {
        "schema": "voice-app-surface-full-coverage/supervisor-control-validate@1",
        "program_id": PROGRAM_ID,
        "board_namespace": BOARD_NAMESPACE,
        "valid": not errors,
        "errors": errors,
        "profile_path": str(PROFILE_PATH.relative_to(REPO_ROOT)),
        "runtime_policy_path": str(RUNTIME_POLICY_PATH.relative_to(REPO_ROOT)),
        "validator_path": str(VALIDATOR.relative_to(REPO_ROOT)),
        "state_root_env": STATE_ROOT_ENV,
        "refill_owner_lane_id": "vas2-grok-0",
    }


def print_lane_plan() -> dict[str, Any]:
    profile = _load_json(PROFILE_PATH)
    lanes = profile.get("lanes") or []
    return {
        "schema": "voice-app-surface-full-coverage/supervisor-lane-plan@1",
        "program_id": PROGRAM_ID,
        "board_namespace": BOARD_NAMESPACE,
        "merge_target_branch": profile.get("merge_target_branch"),
        "task_shard_count": profile.get("task_shard_count"),
        "refill_owner_lane_id": (profile.get("refill") or {}).get("owner_lane_id"),
        "state_root_env": STATE_ROOT_ENV,
        "lanes": lanes,
        "parallel_lane_hints": profile.get("parallel_lane_hints"),
        "default_worker_constraints": profile.get("default_worker_constraints"),
        "human_gated_exceptions": profile.get("human_gated_exceptions"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate-config", help="Validate launch profile + runtime policy")
    sub.add_parser("print-lane-plan", help="Print lane/shard plan JSON")
    args = parser.parse_args()

    if args.command == "validate-config":
        result = validate_config()
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["valid"] else 1
    if args.command == "print-lane-plan":
        print(json.dumps(print_lane_plan(), indent=2, sort_keys=True))
        return 0
    parser.error(f"unknown command {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
