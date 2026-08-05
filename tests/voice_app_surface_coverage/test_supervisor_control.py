"""Tests for voice-app-surface-coverage supervisor control (VAS-001)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTROL = REPO_ROOT / "scripts" / "voice_app_surface_coverage" / "supervisor_control.py"
PROFILE = REPO_ROOT / "docs" / "planning" / "voice_app_surface_coverage.supervisor.json"
RUNTIME_POLICY = REPO_ROOT / "docs" / "voice_app_surface_coverage" / "runtime-policy.json"
VALIDATOR = REPO_ROOT / "scripts" / "validate_voice_app_surface_coverage_plan.py"
STATE_DOC = REPO_ROOT / "docs" / "voice_app_surface_coverage" / "AGENT_SUPERVISOR_STATE.md"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        (sys.executable, str(CONTROL), *args),
        cwd=str(REPO_ROOT),
        check=False,
        capture_output=True,
        text=True,
    )


def test_control_artifacts_exist() -> None:
    assert CONTROL.is_file()
    assert PROFILE.is_file()
    assert RUNTIME_POLICY.is_file()
    assert VALIDATOR.is_file()
    assert STATE_DOC.is_file()


def test_validate_config_ok() -> None:
    result = _run("validate-config")
    assert result.returncode == 0, result.stderr or result.stdout
    payload = json.loads(result.stdout)
    assert payload["valid"] is True
    assert payload["program_id"] == "voice-app-surface-coverage-v1"
    assert payload["refill_owner_lane_id"] == "vas-grok-0"
    assert payload["state_root_env"] == "VOICE_APP_SURFACE_COVERAGE_SUPERVISOR_STATE_ROOT"


def test_print_lane_plan_has_four_shards() -> None:
    result = _run("print-lane-plan")
    assert result.returncode == 0, result.stderr or result.stdout
    payload = json.loads(result.stdout)
    assert payload["task_shard_count"] == 4
    assert len(payload["lanes"]) == 4
    owners = [
        lane["lane_id"]
        for lane in payload["lanes"]
        if lane.get("objective_refill_owner")
    ]
    assert owners == ["vas-grok-0"]


def test_runtime_policy_denies_live_side_effects() -> None:
    policy = json.loads(RUNTIME_POLICY.read_text(encoding="utf-8"))
    for key in (
        "network",
        "credentials",
        "publication",
        "live_telephony",
        "live_sms",
        "hf_publish",
        "live_tts_space",
    ):
        assert policy[key] == "deny"
    assert policy["require_fake_adapters"] is True


def test_state_doc_names_env_and_merge_target() -> None:
    text = STATE_DOC.read_text(encoding="utf-8")
    assert "VOICE_APP_SURFACE_COVERAGE_SUPERVISOR_STATE_ROOT" in text
    assert "agent/voice-app-surface-coverage" in text
