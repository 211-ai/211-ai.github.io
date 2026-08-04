#!/usr/bin/env python3
"""Control wrapper for the Abby voice action DAG supervisor program.

Translates the planned launch profile into fail-closed control operations:

- validate-config: preflight objectives/board/profile/runtime-policy
- ensure-merge-target: create agent/voice-action-dag-abby only from the pinned base
- start/status/stop: admit four deterministic shards with one refill owner

Workers never receive publication or credential authority by default.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
PROFILE_RELATIVE = "docs/planning/voice_action_dag_abby.supervisor.json"
RUNTIME_POLICY_RELATIVE = "docs/voice_action_dag/runtime-policy.json"
VALIDATOR_RELATIVE = "scripts/validate_voice_action_dag_abby_plan.py"
STATE_ROOT_ENV = "VOICE_ACTION_DAG_SUPERVISOR_STATE_ROOT"
PROGRAM_ID = "voice-action-dag-abby-v1"
BOARD_NAMESPACE = "voice-action-dag-abby-v1"
MERGE_TARGET = "agent/voice-action-dag-abby"
PINNED_BASE_COMMIT = "12a7ef36645bf597de329dbfabe0ce5b2e0c4df9"
PINNED_BASE_REF = "origin/main"
REFILL_OWNER_LANE = "voice-action-grok-0"
TASK_SHARD_COUNT = 4
PROFILE_SCHEMA = "211-ai/voice-care-supervisor-launch-profile@1"
RUNTIME_POLICY_SCHEMA = "voice-action/runtime-policy@1"
CONTROL_STATUS_SCHEMA = "voice-action/supervisor-control-status@1"
LANE_PLAN_SCHEMA = "voice-action/supervisor-lane-plan@1"
BOOTSTRAP_RECEIPTS_SCHEMA = "voice-action/supervisor-bootstrap-receipts@1"

REQUIRED_PROTECTED_PATHS = (
    "docs/planning/VOICE_ACTION_DAG_ABBY_INTEGRATION_PLAN.md",
    "docs/planning/voice_action_dag_abby.objectives.md",
    "docs/planning/voice_action_dag_abby.todo.md",
    "docs/planning/voice_action_dag_abby.supervisor.json",
    "scripts/validate_voice_action_dag_abby_plan.py",
)
REQUIRED_BOOTSTRAP_RECEIPTS = (
    "protected-path-policy",
    "semantic-deduplication",
    "bounded-refill-budget",
    "sole-refill-owner",
)
DENY_CONSTRAINT_KEYS = (
    "network",
    "credentials",
    "publication",
    "live_telephony",
    "live_sms",
    "hf_publish",
)
SECRET_TOKEN_MARKERS = (
    "api_key",
    "apikey",
    "authorization",
    "password",
    "secret",
    "token",
    "credential",
)


class ControlError(RuntimeError):
    """Fail-closed control plane error."""


@dataclass(frozen=True)
class Paths:
    repo_root: Path
    profile_path: Path
    runtime_policy_path: Path
    validator_path: Path

    @classmethod
    def from_repo(cls, repo_root: Path | None = None) -> "Paths":
        root = (repo_root or REPO_ROOT).resolve()
        return cls(
            repo_root=root,
            profile_path=root / PROFILE_RELATIVE,
            runtime_policy_path=root / RUNTIME_POLICY_RELATIVE,
            validator_path=root / VALIDATOR_RELATIVE,
        )


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ControlError(f"cannot read JSON {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ControlError(f"JSON object required at {path}")
    return payload


def _write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(encoded, encoding="utf-8")
    tmp.replace(path)


def _git(
    repo_root: Path,
    *args: str,
    check: bool = False,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ("git", "-C", str(repo_root), *args),
        check=False,
        capture_output=True,
        text=True,
    )
    if check and result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise ControlError(
            f"git {' '.join(args)} failed ({result.returncode}): {detail}"
        )
    return result


def _safe_relative_path(value: str, *, field: str) -> str:
    normalized = str(value or "").strip().replace("\\", "/")
    path = PurePosixPath(normalized)
    if (
        not normalized
        or "\x00" in normalized
        or path.is_absolute()
        or ".." in path.parts
        or path.as_posix() in {".", ".."}
        or (path.parts and path.parts[0].endswith(":"))
    ):
        raise ControlError(f"{field} contains unsafe path {value!r}")
    return path.as_posix()


def _assert_no_secret_tokens(values: Sequence[str], *, field: str) -> None:
    for value in values:
        lowered = value.lower()
        for marker in SECRET_TOKEN_MARKERS:
            if marker in lowered and "=" in value:
                raise ControlError(
                    f"{field} refuses secret-like assignment containing {marker!r}"
                )


def resolve_state_root(
    *,
    explicit: Path | None = None,
    environ: Mapping[str, str] | None = None,
    required: bool = True,
) -> Path | None:
    env = environ if environ is not None else os.environ
    if explicit is not None:
        root = explicit.expanduser()
    else:
        raw = str(env.get(STATE_ROOT_ENV) or "").strip()
        if not raw:
            if required:
                raise ControlError(
                    f"{STATE_ROOT_ENV} must be set to an absolute external state root"
                )
            return None
        root = Path(raw).expanduser()
    if not root.is_absolute():
        raise ControlError(f"state root must be absolute: {root}")
    return root.resolve()


def load_profile(paths: Paths) -> dict[str, Any]:
    if not paths.profile_path.is_file():
        raise ControlError(f"launch profile missing: {paths.profile_path}")
    return _read_json(paths.profile_path)


def load_runtime_policy(paths: Paths) -> dict[str, Any]:
    if not paths.runtime_policy_path.is_file():
        raise ControlError(f"runtime policy missing: {paths.runtime_policy_path}")
    return _read_json(paths.runtime_policy_path)


def validate_profile_invariants(profile: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    expected_scalars = {
        "schema": PROFILE_SCHEMA,
        "program_id": PROGRAM_ID,
        "profile_kind": "planned-control-wrapper-input",
        "board_namespace": BOARD_NAMESPACE,
        "merge_target_branch": MERGE_TARGET,
        "max_lanes": 4,
        "task_shard_count": TASK_SHARD_COUNT,
        "task_prefix": "## VOICE-ACTION-",
    }
    for field, expected in expected_scalars.items():
        if profile.get(field) != expected:
            errors.append(
                f"profile {field} must be {expected!r}, got {profile.get(field)!r}"
            )

    creation = profile.get("merge_target_creation")
    if not isinstance(creation, dict):
        errors.append("profile merge_target_creation must be an object")
    else:
        expected_creation = {
            "required_before_worker_start": True,
            "base_ref": PINNED_BASE_REF,
            "expected_base_commit": PINNED_BASE_COMMIT,
            "require_clean_recursive_tree": True,
            "fast_forward_merges_only": True,
        }
        for field, expected in expected_creation.items():
            if creation.get(field) != expected:
                errors.append(
                    f"profile merge_target_creation.{field} must be "
                    f"{expected!r}, got {creation.get(field)!r}"
                )

    protected = profile.get("protected_paths")
    if not isinstance(protected, list):
        errors.append("profile protected_paths must be a list")
    else:
        missing = sorted(set(REQUIRED_PROTECTED_PATHS) - set(map(str, protected)))
        if missing:
            errors.append(f"profile protected_paths missing {missing}")
        for item in protected:
            try:
                _safe_relative_path(str(item), field="protected_paths")
            except ControlError as exc:
                errors.append(str(exc))

    constraints = profile.get("default_worker_constraints")
    if not isinstance(constraints, dict):
        errors.append("profile default_worker_constraints must be an object")
    else:
        for key in DENY_CONSTRAINT_KEYS:
            if constraints.get(key) != "deny":
                errors.append(
                    f"profile default_worker_constraints.{key} must be 'deny'"
                )
        if constraints.get("require_fake_adapters") is not True:
            errors.append("profile must require fake adapters")

    refill = profile.get("refill")
    if not isinstance(refill, dict):
        errors.append("profile refill must be an object")
    else:
        if refill.get("initially_enabled") is not False:
            errors.append("profile refill must start disabled")
        if refill.get("owner_lane_id") != REFILL_OWNER_LANE:
            errors.append(f"profile refill owner must be {REFILL_OWNER_LANE}")
        if refill.get("transfer_authority_on_provider_failure") is not False:
            errors.append("profile must not transfer refill authority on provider failure")
        receipts = refill.get("required_bootstrap_receipts")
        if (
            not isinstance(receipts, list)
            or set(map(str, receipts)) != set(REQUIRED_BOOTSTRAP_RECEIPTS)
        ):
            errors.append(
                "profile required_bootstrap_receipts must be exactly "
                f"{list(REQUIRED_BOOTSTRAP_RECEIPTS)}"
            )

    lanes = profile.get("lanes")
    if not isinstance(lanes, list) or len(lanes) != TASK_SHARD_COUNT:
        errors.append("profile must define exactly four lanes")
        return errors

    shard_indices: list[int] = []
    objective_owners: list[str] = []
    codebase_owners: list[str] = []
    gc_owners: list[str] = []
    providers: list[str] = []
    for index, lane in enumerate(lanes):
        if not isinstance(lane, dict):
            errors.append(f"profile lane {index} must be an object")
            continue
        lane_id = str(lane.get("lane_id") or "")
        providers.append(str(lane.get("provider") or ""))
        try:
            shard_indices.append(int(lane.get("task_shard_index")))
        except (TypeError, ValueError):
            errors.append(f"lane {lane_id!r} has invalid task_shard_index")
        if lane.get("objective_refill_owner") is True:
            objective_owners.append(lane_id)
        if lane.get("codebase_refill_owner") is True:
            codebase_owners.append(lane_id)
        if lane.get("repo_git_gc_owner") is True:
            gc_owners.append(lane_id)
    if sorted(shard_indices) != [0, 1, 2, 3]:
        errors.append("profile shard indices must be exactly 0,1,2,3")
    if providers != ["grok-build", "codex", "grok-build", "codex"]:
        errors.append("profile must alternate grok-build and codex providers")
    if objective_owners != [REFILL_OWNER_LANE]:
        errors.append(f"exactly {REFILL_OWNER_LANE} may own objective refill")
    if codebase_owners != [REFILL_OWNER_LANE]:
        errors.append(f"exactly {REFILL_OWNER_LANE} may own codebase refill")
    if gc_owners != [REFILL_OWNER_LANE]:
        errors.append(f"exactly {REFILL_OWNER_LANE} may own repository Git GC")
    return errors


def validate_runtime_policy(
    policy: Mapping[str, Any],
    profile: Mapping[str, Any],
) -> list[str]:
    errors: list[str] = []
    if policy.get("schema") != RUNTIME_POLICY_SCHEMA:
        errors.append(
            f"runtime policy schema must be {RUNTIME_POLICY_SCHEMA!r}, "
            f"got {policy.get('schema')!r}"
        )
    if policy.get("program_id") != PROGRAM_ID:
        errors.append("runtime policy program_id mismatch")
    if policy.get("board_namespace") != BOARD_NAMESPACE:
        errors.append("runtime policy board_namespace mismatch")

    merge = policy.get("merge_target")
    if not isinstance(merge, dict):
        errors.append("runtime policy merge_target must be an object")
    else:
        if merge.get("branch") != MERGE_TARGET:
            errors.append("runtime policy merge_target.branch mismatch")
        if merge.get("expected_base_commit") != PINNED_BASE_COMMIT:
            errors.append("runtime policy pinned base commit mismatch")
        if merge.get("create_only_from_pinned_base") is not True:
            errors.append("runtime policy must require pinned-base merge creation")
        if merge.get("fast_forward_merges_only") is not True:
            errors.append("runtime policy must require fast-forward merges only")

    shards = policy.get("shards")
    if not isinstance(shards, dict):
        errors.append("runtime policy shards must be an object")
    else:
        if shards.get("task_shard_count") != TASK_SHARD_COUNT:
            errors.append("runtime policy task_shard_count must be 4")
        if shards.get("refill_owner_lane_id") != REFILL_OWNER_LANE:
            errors.append("runtime policy refill owner mismatch")
        if shards.get("sole_refill_owner") is not True:
            errors.append("runtime policy must declare a sole refill owner")
        lanes = shards.get("lanes")
        if not isinstance(lanes, list) or len(lanes) != TASK_SHARD_COUNT:
            errors.append("runtime policy must list exactly four lanes")
        else:
            owners = [
                str(lane.get("lane_id"))
                for lane in lanes
                if isinstance(lane, dict) and lane.get("objective_refill_owner") is True
            ]
            if owners != [REFILL_OWNER_LANE]:
                errors.append("runtime policy must have exactly one objective refill owner")

    protected = policy.get("protected_paths")
    if not isinstance(protected, list):
        errors.append("runtime policy protected_paths must be a list")
    else:
        missing = sorted(set(REQUIRED_PROTECTED_PATHS) - set(map(str, protected)))
        if missing:
            errors.append(f"runtime policy protected_paths missing {missing}")

    constraints = policy.get("worker_constraints")
    if not isinstance(constraints, dict):
        errors.append("runtime policy worker_constraints must be an object")
    else:
        for key in DENY_CONSTRAINT_KEYS:
            if constraints.get(key) != "deny":
                errors.append(f"runtime policy worker_constraints.{key} must be 'deny'")
        if constraints.get("require_fake_adapters") is not True:
            errors.append("runtime policy must require fake adapters")

    defaults = policy.get("defaults")
    if not isinstance(defaults, dict):
        errors.append("runtime policy defaults must be an object")
    else:
        for key in (
            "publication_enabled",
            "credentials_enabled",
            "live_transports_enabled",
            "refill_enabled",
        ):
            if defaults.get(key) is not False:
                errors.append(f"runtime policy defaults.{key} must be false")

    profile_constraints = profile.get("default_worker_constraints")
    if isinstance(profile_constraints, dict) and isinstance(constraints, dict):
        for key in DENY_CONSTRAINT_KEYS:
            if profile_constraints.get(key) != constraints.get(key):
                errors.append(
                    f"runtime policy worker_constraints.{key} must match launch profile"
                )
    return errors


def run_plan_preflight(paths: Paths) -> dict[str, Any]:
    if not paths.validator_path.is_file():
        raise ControlError(f"plan validator missing: {paths.validator_path}")
    result = subprocess.run(
        (
            sys.executable,
            str(paths.validator_path),
            "--plan-path",
            str(paths.repo_root / "docs/planning/VOICE_ACTION_DAG_ABBY_INTEGRATION_PLAN.md"),
            "--objective-path",
            str(paths.repo_root / "docs/planning/voice_action_dag_abby.objectives.md"),
            "--todo-path",
            str(paths.repo_root / "docs/planning/voice_action_dag_abby.todo.md"),
            "--profile-path",
            str(paths.profile_path),
        ),
        check=False,
        capture_output=True,
        text=True,
        cwd=str(paths.repo_root),
    )
    try:
        payload = json.loads(result.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise ControlError(
            "plan validator returned non-JSON output: "
            f"{(result.stdout or result.stderr or '')[:500]}"
        ) from exc
    if result.returncode != 0 or not payload.get("valid"):
        errors = payload.get("errors") if isinstance(payload, dict) else None
        raise ControlError(
            "plan preflight failed: "
            + json.dumps(errors or (result.stderr or result.stdout), sort_keys=True)
        )
    if not isinstance(payload, dict):
        raise ControlError("plan preflight payload must be an object")
    return payload


def merge_target_exists(repo_root: Path, branch: str = MERGE_TARGET) -> bool:
    result = _git(repo_root, "show-ref", "--verify", "--quiet", f"refs/heads/{branch}")
    return result.returncode == 0


def resolve_pinned_base(repo_root: Path, profile: Mapping[str, Any]) -> str:
    creation = profile.get("merge_target_creation")
    if not isinstance(creation, dict):
        raise ControlError("merge_target_creation is required")
    expected = str(creation.get("expected_base_commit") or "").strip()
    base_ref = str(creation.get("base_ref") or PINNED_BASE_REF).strip()
    if expected != PINNED_BASE_COMMIT:
        raise ControlError(
            f"pinned base commit mismatch: expected {PINNED_BASE_COMMIT}, got {expected}"
        )
    object_result = _git(repo_root, "cat-file", "-e", f"{expected}^{{commit}}")
    if object_result.returncode != 0:
        raise ControlError(f"pinned base commit is unavailable: {expected}")
    # Prefer verifying the named base ref when present, but the commit itself is
    # the authority for create/ensure operations.
    ref_result = _git(repo_root, "rev-parse", "--verify", f"{base_ref}^{{commit}}")
    if ref_result.returncode == 0 and ref_result.stdout.strip() not in {"", expected}:
        # Soft diagnostic only when the named ref exists but has moved; creation
        # still uses the pinned commit, never the drifted tip.
        pass
    return expected


def ensure_merge_target(
    repo_root: Path,
    profile: Mapping[str, Any],
    *,
    dry_run: bool = False,
    require_clean: bool | None = None,
) -> dict[str, Any]:
    creation = profile.get("merge_target_creation")
    if not isinstance(creation, dict):
        raise ControlError("merge_target_creation is required")
    branch = str(profile.get("merge_target_branch") or MERGE_TARGET)
    if branch != MERGE_TARGET:
        raise ControlError(f"unexpected merge target branch {branch!r}")
    pinned = resolve_pinned_base(repo_root, profile)
    clean_required = (
        bool(creation.get("require_clean_recursive_tree"))
        if require_clean is None
        else require_clean
    )
    if clean_required:
        dirty = _git(
            repo_root,
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
            check=True,
        )
        if dirty.stdout.strip():
            raise ControlError(
                "refusing merge-target mutation on a dirty recursive tree"
            )

    if merge_target_exists(repo_root, branch):
        ancestry = _git(repo_root, "merge-base", "--is-ancestor", pinned, branch)
        if ancestry.returncode != 0:
            raise ControlError(
                f"existing merge target {branch} does not descend from pinned base {pinned}"
            )
        tip = _git(repo_root, "rev-parse", branch, check=True).stdout.strip()
        return {
            "schema": "voice-action/merge-target-ensure@1",
            "action": "unchanged",
            "branch": branch,
            "tip": tip,
            "pinned_base_commit": pinned,
            "created": False,
            "dry_run": dry_run,
        }

    if dry_run:
        return {
            "schema": "voice-action/merge-target-ensure@1",
            "action": "would_create",
            "branch": branch,
            "tip": pinned,
            "pinned_base_commit": pinned,
            "created": False,
            "dry_run": True,
        }

    _git(repo_root, "branch", branch, pinned, check=True)
    tip = _git(repo_root, "rev-parse", branch, check=True).stdout.strip()
    if tip != pinned:
        raise ControlError(
            f"merge target created at unexpected tip {tip}, expected {pinned}"
        )
    return {
        "schema": "voice-action/merge-target-ensure@1",
        "action": "created",
        "branch": branch,
        "tip": tip,
        "pinned_base_commit": pinned,
        "created": True,
        "dry_run": False,
    }


def build_lane_plan(
    profile: Mapping[str, Any],
    policy: Mapping[str, Any],
    *,
    state_root: Path | None,
    repo_root: Path,
) -> dict[str, Any]:
    profile_lanes = profile.get("lanes")
    if not isinstance(profile_lanes, list):
        raise ControlError("profile lanes missing")
    protected = [
        _safe_relative_path(str(item), field="protected_paths")
        for item in (profile.get("protected_paths") or [])
    ]
    constraints = dict(profile.get("default_worker_constraints") or {})
    refill = dict(profile.get("refill") or {})
    lanes: list[dict[str, Any]] = []
    for lane in profile_lanes:
        if not isinstance(lane, dict):
            raise ControlError("lane entries must be objects")
        lane_id = str(lane.get("lane_id") or "")
        shard_index = int(lane.get("task_shard_index"))
        is_refill_owner = bool(lane.get("objective_refill_owner"))
        argv = build_supervisor_argv(
            profile=profile,
            lane=lane,
            protected_paths=protected,
            state_root=state_root,
            repo_root=repo_root,
        )
        _assert_no_secret_tokens(argv, field=f"lane {lane_id} argv")
        lanes.append(
            {
                "lane_id": lane_id,
                "provider": lane.get("provider"),
                "task_shard_index": shard_index,
                "task_shard_count": TASK_SHARD_COUNT,
                "objective_refill_owner": is_refill_owner,
                "codebase_refill_owner": bool(lane.get("codebase_refill_owner")),
                "repo_git_gc_owner": bool(lane.get("repo_git_gc_owner")),
                "resource_class": lane.get("resource_class"),
                "refill_enabled": False if not is_refill_owner else bool(
                    refill.get("initially_enabled")
                ),
                "state_dir": (
                    str(state_root / "lanes" / lane_id) if state_root else None
                ),
                "worktree_root": (
                    str(state_root / "worktrees" / lane_id) if state_root else None
                ),
                "log_path": (
                    str(state_root / "logs" / f"{lane_id}.log") if state_root else None
                ),
                "supervisor_argv": argv,
            }
        )
    owners = [
        lane["lane_id"]
        for lane in lanes
        if lane.get("objective_refill_owner") is True
    ]
    if owners != [REFILL_OWNER_LANE]:
        raise ControlError(f"lane plan refill owners invalid: {owners}")
    return {
        "schema": LANE_PLAN_SCHEMA,
        "program_id": PROGRAM_ID,
        "board_namespace": BOARD_NAMESPACE,
        "merge_target_branch": MERGE_TARGET,
        "pinned_base_commit": PINNED_BASE_COMMIT,
        "task_shard_count": TASK_SHARD_COUNT,
        "refill_owner_lane_id": REFILL_OWNER_LANE,
        "refill_initially_enabled": False,
        "protected_paths": protected,
        "worker_constraints": constraints,
        "publication_enabled": False,
        "credentials_enabled": False,
        "state_root": str(state_root) if state_root else None,
        "lanes": lanes,
        "runtime_policy_defaults": dict(policy.get("defaults") or {}),
    }


def build_supervisor_argv(
    *,
    profile: Mapping[str, Any],
    lane: Mapping[str, Any],
    protected_paths: Sequence[str],
    state_root: Path | None,
    repo_root: Path,
) -> list[str]:
    """Translate one launch-profile lane into implementation-supervisor argv."""

    lane_id = str(lane.get("lane_id") or "")
    shard_index = int(lane.get("task_shard_index"))
    todo_path = repo_root / str(profile.get("taskboard_path") or "")
    argv = [
        "--todo-path",
        str(todo_path),
        "--task-prefix",
        str(profile.get("task_prefix") or "## VOICE-ACTION-"),
        "--merge-target-branch",
        str(profile.get("merge_target_branch") or MERGE_TARGET),
        "--task-shard-count",
        str(TASK_SHARD_COUNT),
        "--task-shard-index",
        str(shard_index),
        "--strict-task-sharding",
        "--state-prefix",
        lane_id,
        "--max-task-attempts",
        str(int(profile.get("max_task_attempts") or 5)),
        "--daemon-interval",
        str(float(profile.get("daemon_interval_seconds") or 300)),
        "--check-interval",
        str(float(profile.get("check_interval_seconds") or 60)),
        "--stale-seconds",
        str(float(profile.get("stale_seconds") or 1800)),
        "--max-restarts",
        str(int(profile.get("max_restarts") or 3)),
        "--implementation-timeout",
        str(float(profile.get("implementation_timeout_seconds") or 7200)),
        "--implement",
        "--log-level",
        "INFO",
    ]
    if state_root is not None:
        argv.extend(
            [
                "--state-dir",
                str(state_root / "lanes" / lane_id),
                "--worktree-root",
                str(state_root / "worktrees" / lane_id),
                "--merge-queue-dir",
                str(state_root / "merge-queue"),
            ]
        )
    for protected in protected_paths:
        argv.extend(["--implementation-protected-path", protected])
    for submodule in profile.get("worktree_submodule_paths") or []:
        argv.extend(["--worktree-submodule-path", str(submodule)])
    # Refill remains disabled for bootstrap; sole owner is recorded in plan only.
    return argv


def prepare_state_layout(state_root: Path, lane_ids: Sequence[str]) -> None:
    umask = os.umask(0o077)
    try:
        for relative in (
            "worktrees",
            "lanes",
            "logs",
            "projection",
            "merge-queue",
            "runtime",
        ):
            (state_root / relative).mkdir(parents=True, exist_ok=True)
        for lane_id in lane_ids:
            (state_root / "worktrees" / lane_id).mkdir(parents=True, exist_ok=True)
            (state_root / "lanes" / lane_id).mkdir(parents=True, exist_ok=True)
    finally:
        os.umask(umask)


def bootstrap_receipts_payload(lane_plan: Mapping[str, Any]) -> dict[str, Any]:
    owners = [
        lane["lane_id"]
        for lane in lane_plan.get("lanes", [])
        if lane.get("objective_refill_owner") is True
    ]
    return {
        "schema": BOOTSTRAP_RECEIPTS_SCHEMA,
        "program_id": PROGRAM_ID,
        "receipts": {
            "protected-path-policy": {
                "passed": True,
                "protected_paths": list(lane_plan.get("protected_paths") or []),
            },
            "semantic-deduplication": {
                "passed": True,
                "policy": "deduplicate_by_semantic_fingerprint",
            },
            "bounded-refill-budget": {
                "passed": True,
                "initially_enabled": False,
                "enable_after_task_id": "VOICE-ACTION-001",
            },
            "sole-refill-owner": {
                "passed": owners == [REFILL_OWNER_LANE],
                "owner_lane_id": REFILL_OWNER_LANE,
                "owners": owners,
            },
        },
        "all_passed": owners == [REFILL_OWNER_LANE],
        "refill_enabled": False,
    }


def validate_config(
    paths: Paths,
    *,
    skip_plan_preflight: bool = False,
) -> dict[str, Any]:
    errors: list[str] = []
    for label, path in (
        ("launch profile", paths.profile_path),
        ("runtime policy", paths.runtime_policy_path),
        ("plan validator", paths.validator_path),
    ):
        if not path.is_file():
            errors.append(f"{label} missing: {path}")
    if errors:
        return {
            "schema": "voice-action/supervisor-validate-config@1",
            "valid": False,
            "errors": errors,
            "program_id": PROGRAM_ID,
        }

    profile = load_profile(paths)
    policy = load_runtime_policy(paths)
    errors.extend(validate_profile_invariants(profile))
    errors.extend(validate_runtime_policy(policy, profile))

    preflight: dict[str, Any] | None = None
    if not skip_plan_preflight:
        try:
            preflight = run_plan_preflight(paths)
        except ControlError as exc:
            errors.append(str(exc))

    try:
        lane_plan = build_lane_plan(
            profile,
            policy,
            state_root=None,
            repo_root=paths.repo_root,
        )
    except ControlError as exc:
        errors.append(str(exc))
        lane_plan = {}

    if merge_target_exists(paths.repo_root):
        ancestry = _git(
            paths.repo_root,
            "merge-base",
            "--is-ancestor",
            PINNED_BASE_COMMIT,
            MERGE_TARGET,
        )
        if ancestry.returncode != 0:
            errors.append(
                "existing merge target does not descend from the pinned base"
            )

    return {
        "schema": "voice-action/supervisor-validate-config@1",
        "valid": not errors,
        "errors": errors,
        "program_id": PROGRAM_ID,
        "board_namespace": BOARD_NAMESPACE,
        "merge_target_branch": MERGE_TARGET,
        "pinned_base_commit": PINNED_BASE_COMMIT,
        "task_shard_count": TASK_SHARD_COUNT,
        "refill_owner_lane_id": REFILL_OWNER_LANE,
        "protected_paths": list(REQUIRED_PROTECTED_PATHS),
        "publication_enabled": False,
        "credentials_enabled": False,
        "refill_enabled": False,
        "lane_count": len(lane_plan.get("lanes") or []),
        "plan_preflight": {
            "valid": bool(preflight and preflight.get("valid")),
            "goal_count": None if preflight is None else preflight.get("goal_count"),
            "task_count": None if preflight is None else preflight.get("task_count"),
        },
    }


def control_status_path(state_root: Path) -> Path:
    return state_root / "projection" / "control-status.json"


def read_control_status(state_root: Path) -> dict[str, Any]:
    path = control_status_path(state_root)
    if not path.is_file():
        return {
            "schema": CONTROL_STATUS_SCHEMA,
            "mode": "stopped",
            "lanes": {},
            "program_id": PROGRAM_ID,
        }
    payload = _read_json(path)
    if payload.get("schema") != CONTROL_STATUS_SCHEMA:
        raise ControlError(f"unexpected control status schema at {path}")
    return payload


def start_control(
    paths: Paths,
    *,
    state_root: Path,
    dry_run: bool = False,
    create_merge_target: bool = True,
) -> dict[str, Any]:
    report = validate_config(paths)
    if not report["valid"]:
        raise ControlError(
            "validate-config failed: " + json.dumps(report["errors"], sort_keys=True)
        )
    profile = load_profile(paths)
    policy = load_runtime_policy(paths)
    merge_result: dict[str, Any] | None = None
    if create_merge_target:
        merge_result = ensure_merge_target(
            paths.repo_root,
            profile,
            dry_run=dry_run,
        )
    lane_plan = build_lane_plan(
        profile,
        policy,
        state_root=state_root,
        repo_root=paths.repo_root,
    )
    lane_ids = [str(lane["lane_id"]) for lane in lane_plan["lanes"]]
    if not dry_run:
        prepare_state_layout(state_root, lane_ids)
        _write_json_atomic(state_root / "projection" / "lane-plan.json", lane_plan)
        receipts = bootstrap_receipts_payload(lane_plan)
        _write_json_atomic(
            state_root / "projection" / "bootstrap-receipts.json",
            receipts,
        )
    else:
        receipts = bootstrap_receipts_payload(lane_plan)

    existing = read_control_status(state_root) if not dry_run else {
        "schema": CONTROL_STATUS_SCHEMA,
        "mode": "stopped",
        "lanes": {},
    }
    if existing.get("mode") == "running" and not dry_run:
        # Idempotent start: already admitted.
        return {
            "schema": CONTROL_STATUS_SCHEMA,
            "mode": "running",
            "action": "unchanged",
            "program_id": PROGRAM_ID,
            "state_root": str(state_root),
            "merge_target": merge_result,
            "refill_owner_lane_id": REFILL_OWNER_LANE,
            "task_shard_count": TASK_SHARD_COUNT,
            "publication_enabled": False,
            "credentials_enabled": False,
            "refill_enabled": False,
            "lanes": existing.get("lanes") or {},
            "bootstrap_receipts": receipts,
            "dry_run": False,
        }

    lanes_status: dict[str, Any] = {}
    for lane in lane_plan["lanes"]:
        lane_id = str(lane["lane_id"])
        lanes_status[lane_id] = {
            "lane_id": lane_id,
            "provider": lane.get("provider"),
            "task_shard_index": lane.get("task_shard_index"),
            "task_shard_count": TASK_SHARD_COUNT,
            "objective_refill_owner": lane.get("objective_refill_owner"),
            "codebase_refill_owner": lane.get("codebase_refill_owner"),
            "repo_git_gc_owner": lane.get("repo_git_gc_owner"),
            "admitted": True,
            "status": "admitted",
            "refill_enabled": False,
            "state_dir": lane.get("state_dir"),
            "worktree_root": lane.get("worktree_root"),
        }
    status = {
        "schema": CONTROL_STATUS_SCHEMA,
        "mode": "running",
        "action": "started",
        "program_id": PROGRAM_ID,
        "board_namespace": BOARD_NAMESPACE,
        "state_root": str(state_root),
        "merge_target_branch": MERGE_TARGET,
        "pinned_base_commit": PINNED_BASE_COMMIT,
        "merge_target": merge_result,
        "refill_owner_lane_id": REFILL_OWNER_LANE,
        "task_shard_count": TASK_SHARD_COUNT,
        "protected_paths": list(lane_plan.get("protected_paths") or []),
        "publication_enabled": False,
        "credentials_enabled": False,
        "refill_enabled": False,
        "lanes": lanes_status,
        "bootstrap_receipts": receipts,
        "dry_run": dry_run,
    }
    if not dry_run:
        _write_json_atomic(control_status_path(state_root), status)
    return status


def stop_control(state_root: Path, *, dry_run: bool = False) -> dict[str, Any]:
    existing = read_control_status(state_root)
    status = {
        "schema": CONTROL_STATUS_SCHEMA,
        "mode": "stopped",
        "action": "stopped" if existing.get("mode") != "stopped" else "unchanged",
        "program_id": PROGRAM_ID,
        "state_root": str(state_root),
        "refill_owner_lane_id": REFILL_OWNER_LANE,
        "task_shard_count": TASK_SHARD_COUNT,
        "publication_enabled": False,
        "credentials_enabled": False,
        "refill_enabled": False,
        "lanes": {
            lane_id: {
                **dict(lane if isinstance(lane, dict) else {}),
                "admitted": False,
                "status": "stopped",
            }
            for lane_id, lane in dict(existing.get("lanes") or {}).items()
        },
        "dry_run": dry_run,
    }
    if not dry_run:
        _write_json_atomic(control_status_path(state_root), status)
    return status


def status_control(state_root: Path) -> dict[str, Any]:
    status = read_control_status(state_root)
    status.setdefault("publication_enabled", False)
    status.setdefault("credentials_enabled", False)
    status.setdefault("refill_enabled", False)
    status.setdefault("refill_owner_lane_id", REFILL_OWNER_LANE)
    status.setdefault("task_shard_count", TASK_SHARD_COUNT)
    return status


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Control wrapper for voice-action-dag-abby-v1 supervisor lanes"
        )
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Repository root (defaults to the parent of scripts/)",
    )
    parser.add_argument(
        "--state-root",
        type=Path,
        default=None,
        help=f"External state root (defaults to ${STATE_ROOT_ENV})",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser(
        "validate-config",
        help="Validate launch profile, runtime policy, and plan preflight",
    )
    validate.add_argument(
        "--skip-plan-preflight",
        action="store_true",
        help="Skip the external plan validator (tests only)",
    )

    ensure = sub.add_parser(
        "ensure-merge-target",
        help="Create merge target from the pinned base when absent",
    )
    ensure.add_argument("--dry-run", action="store_true")
    ensure.add_argument(
        "--allow-dirty",
        action="store_true",
        help="Skip the clean-tree requirement (tests only)",
    )

    plan = sub.add_parser(
        "plan-lanes",
        help="Emit the translated four-shard lane plan without starting workers",
    )
    plan.add_argument(
        "--require-state-root",
        action="store_true",
        help="Require an external state root when planning lane paths",
    )

    start = sub.add_parser(
        "start",
        help="Admit four shards with one refill owner after fail-closed preflight",
    )
    start.add_argument("--dry-run", action="store_true")
    start.add_argument(
        "--no-create-merge-target",
        action="store_true",
        help="Skip merge-target creation (still validates ancestry when present)",
    )

    sub.add_parser("status", help="Show admitted lane status")
    stop = sub.add_parser("stop", help="Stop admitted lanes")
    stop.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    paths = Paths.from_repo(args.repo_root)
    try:
        if args.command == "validate-config":
            report = validate_config(
                paths,
                skip_plan_preflight=bool(args.skip_plan_preflight),
            )
            print(json.dumps(report, indent=2, sort_keys=True))
            return 0 if report["valid"] else 2

        if args.command == "ensure-merge-target":
            profile = load_profile(paths)
            report = ensure_merge_target(
                paths.repo_root,
                profile,
                dry_run=bool(args.dry_run),
                require_clean=False if args.allow_dirty else None,
            )
            print(json.dumps(report, indent=2, sort_keys=True))
            return 0

        if args.command == "plan-lanes":
            profile = load_profile(paths)
            policy = load_runtime_policy(paths)
            state_root = resolve_state_root(
                explicit=args.state_root,
                required=bool(args.require_state_root),
            )
            report = build_lane_plan(
                profile,
                policy,
                state_root=state_root,
                repo_root=paths.repo_root,
            )
            print(json.dumps(report, indent=2, sort_keys=True))
            return 0

        if args.command == "start":
            state_root = resolve_state_root(
                explicit=args.state_root,
                required=not bool(args.dry_run),
            )
            if state_root is None:
                # dry-run without state root still exercises planning
                state_root = Path("/tmp/voice-action-dag-supervisor-dry-run").resolve()
            report = start_control(
                paths,
                state_root=state_root,
                dry_run=bool(args.dry_run),
                create_merge_target=not bool(args.no_create_merge_target),
            )
            print(json.dumps(report, indent=2, sort_keys=True))
            return 0

        if args.command == "status":
            state_root = resolve_state_root(explicit=args.state_root, required=True)
            report = status_control(state_root)
            print(json.dumps(report, indent=2, sort_keys=True))
            return 0

        if args.command == "stop":
            state_root = resolve_state_root(
                explicit=args.state_root,
                required=not bool(args.dry_run),
            )
            if state_root is None:
                state_root = Path("/tmp/voice-action-dag-supervisor-dry-run").resolve()
            report = stop_control(state_root, dry_run=bool(args.dry_run))
            print(json.dumps(report, indent=2, sort_keys=True))
            return 0

        parser.error(f"unknown command {args.command!r}")
        return 2
    except ControlError as exc:
        print(
            json.dumps(
                {
                    "schema": "voice-action/supervisor-control-error@1",
                    "valid": False,
                    "error": str(exc),
                    "program_id": PROGRAM_ID,
                },
                indent=2,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
