"""Tests for the Abby voice action DAG supervisor control wrapper."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTROL = REPO_ROOT / "scripts" / "voice_action_dag" / "supervisor_control.py"
PROFILE = REPO_ROOT / "docs" / "planning" / "voice_action_dag_abby.supervisor.json"
RUNTIME_POLICY = REPO_ROOT / "docs" / "voice_action_dag" / "runtime-policy.json"
STATE_DOC = REPO_ROOT / "docs" / "voice_action_dag" / "AGENT_SUPERVISOR_STATE.md"
VALIDATOR = REPO_ROOT / "scripts" / "validate_voice_action_dag_abby_plan.py"

_SPEC = importlib.util.spec_from_file_location(
    "voice_action_dag_supervisor_control",
    CONTROL,
)
assert _SPEC is not None and _SPEC.loader is not None
sc = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(sc)

PINNED = "12a7ef36645bf597de329dbfabe0ce5b2e0c4df9"
MERGE_BRANCH = "agent/voice-action-dag-abby"
PROTECTED = {
    "docs/planning/VOICE_ACTION_DAG_ABBY_INTEGRATION_PLAN.md",
    "docs/planning/voice_action_dag_abby.objectives.md",
    "docs/planning/voice_action_dag_abby.todo.md",
    "docs/planning/voice_action_dag_abby.supervisor.json",
    "scripts/validate_voice_action_dag_abby_plan.py",
}


def _run_control(
    *args: str,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CONTROL), *args],
        check=False,
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        env=env,
    )


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def _init_repo_with_pinned_base(tmp_path: Path) -> Path:
    """Create a minimal git repo used as a stand-in merge-target authority."""

    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "voice-action@example.test")
    _git(repo, "config", "user.name", "Voice Action Test")
    (repo / "README").write_text("base\n", encoding="utf-8")
    _git(repo, "add", "README")
    _git(repo, "commit", "-m", "base")
    return repo


def test_declared_outputs_exist() -> None:
    assert CONTROL.is_file()
    assert RUNTIME_POLICY.is_file()
    assert STATE_DOC.is_file()
    assert PROFILE.is_file()
    assert VALIDATOR.is_file()


def test_runtime_policy_denies_publication_and_credentials() -> None:
    policy = json.loads(RUNTIME_POLICY.read_text(encoding="utf-8"))
    constraints = policy["worker_constraints"]
    assert constraints["credentials"] == "deny"
    assert constraints["publication"] == "deny"
    assert constraints["network"] == "deny"
    assert constraints["live_telephony"] == "deny"
    assert constraints["live_sms"] == "deny"
    assert constraints["hf_publish"] == "deny"
    assert constraints["require_fake_adapters"] is True
    defaults = policy["defaults"]
    assert defaults["publication_enabled"] is False
    assert defaults["credentials_enabled"] is False
    assert defaults["refill_enabled"] is False
    assert set(policy["protected_paths"]) >= PROTECTED
    assert policy["merge_target"]["branch"] == MERGE_BRANCH
    assert policy["merge_target"]["expected_base_commit"] == PINNED
    assert policy["merge_target"]["create_only_from_pinned_base"] is True
    assert policy["shards"]["task_shard_count"] == 4
    assert policy["shards"]["refill_owner_lane_id"] == "voice-action-grok-0"
    owners = [
        lane["lane_id"]
        for lane in policy["shards"]["lanes"]
        if lane.get("objective_refill_owner")
    ]
    assert owners == ["voice-action-grok-0"]


def test_validate_config_cli_passes() -> None:
    result = _run_control("validate-config")
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["valid"] is True
    assert payload["program_id"] == "voice-action-dag-abby-v1"
    assert payload["task_shard_count"] == 4
    assert payload["refill_owner_lane_id"] == "voice-action-grok-0"
    assert payload["publication_enabled"] is False
    assert payload["credentials_enabled"] is False
    assert payload["refill_enabled"] is False
    assert set(payload["protected_paths"]) >= PROTECTED
    assert payload["plan_preflight"]["valid"] is True
    assert payload["lane_count"] == 4


def test_profile_and_runtime_policy_invariants() -> None:
    paths = sc.Paths.from_repo(REPO_ROOT)
    profile = sc.load_profile(paths)
    policy = sc.load_runtime_policy(paths)
    assert sc.validate_profile_invariants(profile) == []
    assert sc.validate_runtime_policy(policy, profile) == []


def test_lane_plan_has_four_shards_and_one_refill_owner() -> None:
    paths = sc.Paths.from_repo(REPO_ROOT)
    profile = sc.load_profile(paths)
    policy = sc.load_runtime_policy(paths)
    plan = sc.build_lane_plan(
        profile,
        policy,
        state_root=Path("/tmp/voice-action-state"),
        repo_root=REPO_ROOT,
    )
    assert plan["schema"] == "voice-action/supervisor-lane-plan@1"
    assert len(plan["lanes"]) == 4
    assert plan["refill_owner_lane_id"] == "voice-action-grok-0"
    assert plan["refill_initially_enabled"] is False
    assert plan["publication_enabled"] is False
    assert plan["credentials_enabled"] is False
    shards = sorted(lane["task_shard_index"] for lane in plan["lanes"])
    assert shards == [0, 1, 2, 3]
    owners = [
        lane["lane_id"]
        for lane in plan["lanes"]
        if lane["objective_refill_owner"]
    ]
    assert owners == ["voice-action-grok-0"]
    for lane in plan["lanes"]:
        argv = lane["supervisor_argv"]
        assert "--implementation-protected-path" in argv
        for protected in PROTECTED:
            assert protected in argv
        assert "--merge-target-branch" in argv
        assert MERGE_BRANCH in argv
        assert "--task-shard-count" in argv
        assert "4" in argv
        assert "--strict-task-sharding" in argv
        # No secret-like assignments in argv.
        assert not any("=" in token and "key" in token.lower() for token in argv)


def test_protected_paths_present_in_state_doc() -> None:
    text = STATE_DOC.read_text(encoding="utf-8")
    for path in PROTECTED:
        assert path in text
    assert "VOICE_ACTION_DAG_SUPERVISOR_STATE_ROOT" in text
    assert MERGE_BRANCH in text
    assert "voice-action-grok-0" in text


def test_ensure_merge_target_creates_only_from_pinned_base(tmp_path: Path) -> None:
    repo = _init_repo_with_pinned_base(tmp_path)
    tip = _git(repo, "rev-parse", "HEAD").stdout.strip()
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    profile["merge_target_creation"]["expected_base_commit"] = tip
    profile["merge_target_creation"]["base_ref"] = "HEAD"

    # Monkeypatch constants used by resolve_pinned_base for this process.
    original = sc.PINNED_BASE_COMMIT
    sc.PINNED_BASE_COMMIT = tip
    try:
        first = sc.ensure_merge_target(repo, profile, dry_run=False, require_clean=True)
        assert first["created"] is True
        assert first["tip"] == tip
        assert first["branch"] == MERGE_BRANCH
        second = sc.ensure_merge_target(repo, profile, dry_run=False, require_clean=True)
        assert second["created"] is False
        assert second["action"] == "unchanged"
        branch_tip = _git(repo, "rev-parse", MERGE_BRANCH).stdout.strip()
        assert branch_tip == tip
    finally:
        sc.PINNED_BASE_COMMIT = original


def test_ensure_merge_target_rejects_non_descendant(tmp_path: Path) -> None:
    repo = _init_repo_with_pinned_base(tmp_path)
    base = _git(repo, "rev-parse", "HEAD").stdout.strip()
    # Create an unrelated branch tip that does not contain the pinned base as ancestor
    # by creating a second root commit and pointing the merge branch at it.
    _git(repo, "checkout", "--orphan", "orphan-root")
    (repo / "OTHER").write_text("other\n", encoding="utf-8")
    _git(repo, "add", "OTHER")
    _git(repo, "commit", "-m", "orphan")
    orphan = _git(repo, "rev-parse", "HEAD").stdout.strip()
    _git(repo, "branch", "-f", MERGE_BRANCH, orphan)
    _git(repo, "checkout", "-B", "main", base)

    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    profile["merge_target_creation"]["expected_base_commit"] = base
    original = sc.PINNED_BASE_COMMIT
    sc.PINNED_BASE_COMMIT = base
    try:
        with pytest.raises(sc.ControlError, match="does not descend"):
            sc.ensure_merge_target(repo, profile, dry_run=False, require_clean=True)
    finally:
        sc.PINNED_BASE_COMMIT = original


def test_ensure_merge_target_rejects_dirty_tree(tmp_path: Path) -> None:
    repo = _init_repo_with_pinned_base(tmp_path)
    tip = _git(repo, "rev-parse", "HEAD").stdout.strip()
    (repo / "dirty.txt").write_text("dirty\n", encoding="utf-8")
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    profile["merge_target_creation"]["expected_base_commit"] = tip
    original = sc.PINNED_BASE_COMMIT
    sc.PINNED_BASE_COMMIT = tip
    try:
        with pytest.raises(sc.ControlError, match="dirty recursive tree"):
            sc.ensure_merge_target(repo, profile, dry_run=False, require_clean=True)
    finally:
        sc.PINNED_BASE_COMMIT = original


def test_start_status_stop_idempotent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state_root = tmp_path / "state"
    paths = sc.Paths.from_repo(REPO_ROOT)

    # Avoid mutating the real repo merge target during this test.
    def _fake_ensure(*_a, **_k):
        return {
            "schema": "voice-action/merge-target-ensure@1",
            "action": "unchanged",
            "branch": MERGE_BRANCH,
            "tip": PINNED,
            "pinned_base_commit": PINNED,
            "created": False,
            "dry_run": False,
        }

    monkeypatch.setattr(sc, "ensure_merge_target", _fake_ensure)
    monkeypatch.setattr(
        sc,
        "run_plan_preflight",
        lambda _paths: {
            "valid": True,
            "goal_count": 16,
            "task_count": 32,
        },
    )

    first = sc.start_control(paths, state_root=state_root, dry_run=False)
    assert first["mode"] == "running"
    assert first["action"] == "started"
    assert first["task_shard_count"] == 4
    assert first["refill_owner_lane_id"] == "voice-action-grok-0"
    assert first["publication_enabled"] is False
    assert first["credentials_enabled"] is False
    assert first["refill_enabled"] is False
    assert len(first["lanes"]) == 4
    owners = [
        lane_id
        for lane_id, lane in first["lanes"].items()
        if lane.get("objective_refill_owner")
    ]
    assert owners == ["voice-action-grok-0"]
    assert (state_root / "projection" / "lane-plan.json").is_file()
    assert (state_root / "projection" / "bootstrap-receipts.json").is_file()
    for lane_id in first["lanes"]:
        assert (state_root / "lanes" / lane_id).is_dir()
        assert (state_root / "worktrees" / lane_id).is_dir()

    second = sc.start_control(paths, state_root=state_root, dry_run=False)
    assert second["mode"] == "running"
    assert second["action"] == "unchanged"

    status = sc.status_control(state_root)
    assert status["mode"] == "running"
    assert status["task_shard_count"] == 4

    stopped = sc.stop_control(state_root)
    assert stopped["mode"] == "stopped"
    again = sc.stop_control(state_root)
    assert again["mode"] == "stopped"
    assert again["action"] == "unchanged"


def test_start_requires_state_root_env() -> None:
    env = os.environ.copy()
    env.pop("VOICE_ACTION_DAG_SUPERVISOR_STATE_ROOT", None)
    result = _run_control("start", env=env)
    assert result.returncode == 2
    assert "VOICE_ACTION_DAG_SUPERVISOR_STATE_ROOT" in (result.stderr + result.stdout)


def test_validate_config_fails_when_credentials_or_publication_allowed() -> None:
    paths = sc.Paths.from_repo(REPO_ROOT)
    profile = sc.load_profile(paths)
    policy = sc.load_runtime_policy(paths)

    bad_credentials = json.loads(json.dumps(policy))
    bad_credentials["worker_constraints"]["credentials"] = "allow"
    errors = sc.validate_runtime_policy(bad_credentials, profile)
    assert any("credentials" in item for item in errors)

    bad_publication = json.loads(json.dumps(policy))
    bad_publication["defaults"]["publication_enabled"] = True
    errors = sc.validate_runtime_policy(bad_publication, profile)
    assert any("publication_enabled" in item for item in errors)

    bad_owner = json.loads(json.dumps(policy))
    bad_owner["shards"]["lanes"][1]["objective_refill_owner"] = True
    errors = sc.validate_runtime_policy(bad_owner, profile)
    assert any("refill owner" in item for item in errors)


def test_bootstrap_receipts_include_required_set() -> None:
    paths = sc.Paths.from_repo(REPO_ROOT)
    profile = sc.load_profile(paths)
    policy = sc.load_runtime_policy(paths)
    plan = sc.build_lane_plan(
        profile,
        policy,
        state_root=None,
        repo_root=REPO_ROOT,
    )
    receipts = sc.bootstrap_receipts_payload(plan)
    assert set(receipts["receipts"]) == {
        "protected-path-policy",
        "semantic-deduplication",
        "bounded-refill-budget",
        "sole-refill-owner",
    }
    assert receipts["all_passed"] is True
    assert receipts["refill_enabled"] is False
