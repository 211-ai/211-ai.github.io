#!/usr/bin/env python3
"""Fail-closed preflight for the reusable voice-workflow planning program."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path, PurePosixPath

REPO_ROOT = Path(__file__).resolve().parents[1]
ACCELERATE_ROOT = REPO_ROOT / "ipfs_accelerate_py"
for import_root in (ACCELERATE_ROOT, REPO_ROOT):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from ipfs_accelerate_py.agent_supervisor.objectives.objective_graph import (  # noqa: E402
    materialize_task_dependency_dag,
    parse_goal_heap,
)
from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import (  # noqa: E402
    parse_task_file,
)

PLAN_PATH = (
    REPO_ROOT
    / "docs"
    / "planning"
    / "REUSABLE_VOICE_WORKFLOW_DAG_CLIENT_CARE_PLAN.md"
)
OBJECTIVE_PATH = (
    REPO_ROOT
    / "docs"
    / "planning"
    / "reusable_voice_workflow_dag_client_care.objectives.md"
)
TODO_PATH = (
    REPO_ROOT
    / "docs"
    / "planning"
    / "reusable_voice_workflow_dag_client_care.todo.md"
)
PROFILE_PATH = (
    REPO_ROOT
    / "docs"
    / "planning"
    / "reusable_voice_workflow_dag_client_care.supervisor.json"
)
VALIDATOR_PATH = Path(__file__).resolve()

PROGRAM_ID = "reusable-voice-workflow-dag-client-care-v1"
BOARD_NAMESPACE = "voice-care-workflow-dag-v1"
TASK_PREFIX = "## VOICE-CARE-"
MERGE_TARGET = "agent/voice-care-workflow-dag"
PINNED_BASE_COMMIT = "ad369c36e258133ad43abfe272e7f69460d9f572"
PROFILE_SCHEMA = "211-ai/voice-care-supervisor-launch-profile@1"
GOAL_STATES = frozenset(
    {
        "active",
        "provisionally_complete",
        "verified_complete",
        "analysis_inconclusive",
        "blocked",
        "reopened",
    }
)
TASK_STATES = frozenset({"todo", "in_progress", "blocked", "completed"})
REQUIRED_GOAL_FIELDS = (
    "status",
    "parent",
    "fib_priority",
    "track",
    "priority",
    "bundle",
    "goal",
    "evidence",
    "outputs",
    "validation",
    "acceptance",
    "gap_task",
    "refinement",
    "embedding_query",
    "ast_query",
)
REQUIRED_TASK_FIELDS = (
    "status",
    "completion",
    "priority",
    "track",
    "depends on",
    "goal id",
    "outputs",
    "validation",
    "board namespace",
    "bundle",
    "parallel lane",
    "resource class",
    "predicted files",
    "conflict policy",
    "symbolic first",
    "llm context budget bytes",
    "acceptance",
)
EXPECTED_PROFILE_PATHS = {
    "plan_path": "docs/planning/REUSABLE_VOICE_WORKFLOW_DAG_CLIENT_CARE_PLAN.md",
    "objectives_path": (
        "docs/planning/reusable_voice_workflow_dag_client_care.objectives.md"
    ),
    "taskboard_path": (
        "docs/planning/reusable_voice_workflow_dag_client_care.todo.md"
    ),
    "validator_path": "scripts/validate_voice_workflow_dag_client_care_plan.py",
}
EXPECTED_SUBMODULES = {
    "ipfs_accelerate_py",
    "ipfs_datasets_py",
    "ipfs_kit_py",
}
EXPECTED_PROTECTED_PATHS = {
    *EXPECTED_PROFILE_PATHS.values(),
    "docs/planning/reusable_voice_workflow_dag_client_care.supervisor.json",
}


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_sha256(value: object) -> str:
    encoded = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _csv(value: object) -> tuple[str, ...]:
    return tuple(
        item.strip()
        for item in re.split(r"[,;]", str(value or ""))
        if item.strip()
    )


def _safe_relative_paths(values: Iterable[str], *, field: str) -> list[str]:
    errors: list[str] = []
    for raw in values:
        value = str(raw).strip().replace("\\", "/")
        path = PurePosixPath(value)
        if (
            not value
            or "\x00" in value
            or path.is_absolute()
            or ".." in path.parts
            or path.as_posix() in {".", ".."}
            or (path.parts and path.parts[0].endswith(":"))
        ):
            errors.append(f"{field} contains unsafe path {raw!r}")
    return errors


def _cycle_nodes(edges: dict[str, tuple[str, ...]]) -> tuple[str, ...]:
    visiting: set[str] = set()
    visited: set[str] = set()
    cycle: set[str] = set()

    def visit(node: str, lineage: tuple[str, ...]) -> None:
        if node in visited:
            return
        if node in visiting:
            if node in lineage:
                cycle.update(lineage[lineage.index(node) :])
            cycle.add(node)
            return
        visiting.add(node)
        for parent in edges.get(node, ()):
            visit(parent, (*lineage, node))
        visiting.remove(node)
        visited.add(node)

    for item in sorted(edges):
        visit(item, ())
    return tuple(sorted(cycle))


def _positive_int(
    value: object,
    *,
    field: str,
    errors: list[str],
    maximum: int | None = None,
) -> int | None:
    try:
        result = int(str(value))
        if result < 1 or (maximum is not None and result > maximum):
            raise ValueError
    except (TypeError, ValueError):
        suffix = f" and <= {maximum}" if maximum is not None else ""
        errors.append(f"{field} must be an integer >= 1{suffix}")
        return None
    return result


def _load_profile(profile_path: Path, errors: list[str]) -> dict[str, object]:
    try:
        payload = json.loads(profile_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        errors.append(f"cannot read launch profile: {exc}")
        return {}
    if not isinstance(payload, dict):
        errors.append("launch profile must be a JSON object")
        return {}
    return payload


def _git(
    *args: str,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ("git", "-C", str(REPO_ROOT), *args),
        check=False,
        capture_output=True,
        text=True,
    )


def _validate_profile(
    profile: dict[str, object],
    *,
    errors: list[str],
) -> None:
    expected_scalars = {
        "schema": PROFILE_SCHEMA,
        "program_id": PROGRAM_ID,
        "profile_kind": "planned-control-wrapper-input",
        "consumer_status": "planned-by-VOICE-CARE-001",
        "repo_root": ".",
        "task_prefix": TASK_PREFIX,
        "board_namespace": BOARD_NAMESPACE,
        "merge_target_branch": MERGE_TARGET,
        "max_lanes": 4,
        "task_shard_count": 4,
    }
    for field, expected in expected_scalars.items():
        if profile.get(field) != expected:
            errors.append(
                f"launch profile {field} must be {expected!r}, "
                f"got {profile.get(field)!r}"
            )
    for field, expected in EXPECTED_PROFILE_PATHS.items():
        if profile.get(field) != expected:
            errors.append(
                f"launch profile {field} must be {expected!r}, "
                f"got {profile.get(field)!r}"
            )

    target_creation = profile.get("merge_target_creation")
    if not isinstance(target_creation, dict):
        errors.append("launch profile merge_target_creation must be an object")
    else:
        expected_target_creation = {
            "required_before_worker_start": True,
            "base_ref": "origin/main",
            "expected_base_commit": PINNED_BASE_COMMIT,
            "require_clean_recursive_tree": True,
            "fast_forward_merges_only": True,
        }
        for field, expected in expected_target_creation.items():
            if target_creation.get(field) != expected:
                errors.append(
                    f"launch profile merge_target_creation.{field} must be "
                    f"{expected!r}, got {target_creation.get(field)!r}"
                )
        base_result = _git("rev-parse", "--verify", "origin/main^{commit}")
        if base_result.returncode != 0:
            errors.append("launch profile pinned base ref origin/main is unavailable")
        elif base_result.stdout.strip() != PINNED_BASE_COMMIT:
            errors.append(
                "launch profile pinned base no longer matches origin/main: "
                f"expected {PINNED_BASE_COMMIT}, "
                f"got {base_result.stdout.strip()!r}"
            )
        object_result = _git(
            "cat-file",
            "-e",
            f"{PINNED_BASE_COMMIT}^{{commit}}",
        )
        if object_result.returncode != 0:
            errors.append("launch profile pinned base commit is unavailable")
        target_result = _git(
            "show-ref",
            "--verify",
            "--quiet",
            f"refs/heads/{MERGE_TARGET}",
        )
        if target_result.returncode == 0:
            ancestry_result = _git(
                "merge-base",
                "--is-ancestor",
                PINNED_BASE_COMMIT,
                MERGE_TARGET,
            )
            if ancestry_result.returncode != 0:
                errors.append(
                    "existing merge target does not descend from the pinned base"
                )
        elif target_result.returncode not in {1}:
            errors.append("cannot determine whether the merge target exists")

    for field in (
        "poll_interval_seconds",
        "daemon_interval_seconds",
        "check_interval_seconds",
        "stale_seconds",
        "max_restarts",
        "max_task_attempts",
        "implementation_timeout_seconds",
    ):
        _positive_int(
            profile.get(field),
            field=f"launch profile {field}",
            errors=errors,
        )

    submodules = profile.get("worktree_submodule_paths")
    if not isinstance(submodules, list) or set(submodules) != EXPECTED_SUBMODULES:
        errors.append(
            "launch profile worktree_submodule_paths must contain exactly "
            f"{sorted(EXPECTED_SUBMODULES)}"
        )
    protected = profile.get("protected_paths")
    if not isinstance(protected, list) or not EXPECTED_PROTECTED_PATHS.issubset(
        set(str(item) for item in protected)
    ):
        errors.append(
            "launch profile protected_paths does not protect every planning "
            "and validation artifact"
        )
    elif _safe_relative_paths(protected, field="protected_paths"):
        errors.extend(_safe_relative_paths(protected, field="protected_paths"))

    state_layout = profile.get("state_layout")
    if not isinstance(state_layout, dict):
        errors.append("launch profile state_layout must be an object")
    else:
        if state_layout.get("external_state_required") is not True:
            errors.append("launch profile must require external supervisor state")
        if state_layout.get("secrets_in_argv_allowed") is not False:
            errors.append("launch profile must prohibit secrets in argv")
        if state_layout.get("state_root_env") != "VOICE_CARE_SUPERVISOR_STATE_ROOT":
            errors.append("launch profile has an unexpected state-root variable")
        for field in (
            "worktree_root",
            "lane_state_root",
            "log_root",
            "projection_root",
            "shared_merge_queue",
        ):
            value = state_layout.get(field)
            if not isinstance(value, str):
                errors.append(f"launch profile state_layout.{field} is missing")
            else:
                errors.extend(
                    _safe_relative_paths(
                        (value,),
                        field=f"state_layout.{field}",
                    )
                )

    refill = profile.get("refill")
    if not isinstance(refill, dict):
        errors.append("launch profile refill must be an object")
        refill = {}
    if refill.get("initially_enabled") is not False:
        errors.append("refill must remain disabled until bootstrap evidence exists")
    if refill.get("enable_after_task_id") != "VOICE-CARE-001":
        errors.append("refill may be enabled only after VOICE-CARE-001")
    expected_bootstrap_receipts = {
        "protected-path-policy",
        "semantic-deduplication",
        "bounded-refill-budget",
        "sole-refill-owner",
    }
    bootstrap_receipts = refill.get("required_bootstrap_receipts")
    if (
        not isinstance(bootstrap_receipts, list)
        or set(bootstrap_receipts) != expected_bootstrap_receipts
    ):
        errors.append(
            "refill required_bootstrap_receipts must contain exactly "
            f"{sorted(expected_bootstrap_receipts)}"
        )
    if refill.get("owner_lane_id") != "voice-care-grok-0":
        errors.append("launch profile refill owner must be voice-care-grok-0")
    if refill.get("transfer_authority_on_provider_failure") is not False:
        errors.append("refill authority must not transfer on provider failure")
    if refill.get("deduplicate_by_semantic_fingerprint") is not True:
        errors.append("refill must deduplicate by semantic fingerprint")
    if refill.get("defer_codebase_refill_after_objective_generation") is not True:
        errors.append("codebase refill must defer after objective work is generated")
    for field in (
        "minimum_open_tasks",
        "objective_max_findings",
        "codebase_max_findings",
        "max_child_goals_per_refinement",
        "max_refinement_depth",
        "surplus_findings_per_goal",
        "objective_cooldown_seconds",
        "codebase_cooldown_seconds",
        "objective_timeout_seconds",
        "codebase_timeout_seconds",
    ):
        _positive_int(
            refill.get(field),
            field=f"launch profile refill.{field}",
            errors=errors,
        )

    proof_cache = profile.get("proof_cache")
    if not isinstance(proof_cache, dict):
        errors.append("launch profile proof_cache must be an object")
    else:
        if proof_cache.get("module") != (
            "ipfs_accelerate_py.agent_supervisor.proof."
            "formal_verification_cache"
        ):
            errors.append("launch profile proof_cache.module is not admitted")
        for field in (
            "enabled",
            "prefer_cache_before_provider",
            "single_flight",
            "rederive_assurance_on_hit",
        ):
            if proof_cache.get(field) is not True:
                errors.append(f"launch profile proof_cache.{field} must be true")
        if proof_cache.get("allow_simulated_zk_attested") is not False:
            errors.append("simulated ZK evidence must not be treated as attested")

    lanes = profile.get("lanes")
    if not isinstance(lanes, list) or len(lanes) != 4:
        errors.append("launch profile must define exactly four lanes")
        return
    lane_ids: list[str] = []
    shard_indices: list[int] = []
    objective_refill_owners: list[str] = []
    codebase_refill_owners: list[str] = []
    git_gc_owners: list[str] = []
    providers: list[str] = []
    for index, lane in enumerate(lanes):
        if not isinstance(lane, dict):
            errors.append(f"launch profile lane {index} must be an object")
            continue
        lane_id = str(lane.get("lane_id") or "")
        lane_ids.append(lane_id)
        providers.append(str(lane.get("provider") or ""))
        try:
            shard_indices.append(int(lane.get("task_shard_index")))
        except (TypeError, ValueError):
            errors.append(f"launch profile lane {lane_id!r} has invalid shard")
        if lane.get("objective_refill_owner") is True:
            objective_refill_owners.append(lane_id)
        if lane.get("codebase_refill_owner") is True:
            codebase_refill_owners.append(lane_id)
        if lane.get("repo_git_gc_owner") is True:
            git_gc_owners.append(lane_id)
        if not str(lane.get("resource_class") or "").strip():
            errors.append(f"launch profile lane {lane_id!r} has no resource class")
    if len(set(lane_ids)) != len(lane_ids) or any(not item for item in lane_ids):
        errors.append("launch profile lane IDs must be nonempty and unique")
    if sorted(shard_indices) != [0, 1, 2, 3]:
        errors.append("launch profile shard indices must be exactly 0, 1, 2, 3")
    if providers != ["grok-build", "codex", "grok-build", "codex"]:
        errors.append("launch profile must alternate Grok and Codex lanes")
    if objective_refill_owners != ["voice-care-grok-0"]:
        errors.append("exactly voice-care-grok-0 may own objective refill")
    if codebase_refill_owners != ["voice-care-grok-0"]:
        errors.append("exactly voice-care-grok-0 may own codebase refill")
    if git_gc_owners != ["voice-care-grok-0"]:
        errors.append("exactly shard-zero Grok lane may own repository Git GC")


def validate(
    plan_path: Path,
    objective_path: Path,
    todo_path: Path,
    profile_path: Path,
) -> dict[str, object]:
    errors: list[str] = []
    required_files = {
        "human plan": plan_path,
        "objective heap": objective_path,
        "task board": todo_path,
        "launch profile": profile_path,
        "validator": VALIDATOR_PATH,
    }
    for label, path in required_files.items():
        if not path.is_file():
            errors.append(f"{label} is missing: {path}")
    if errors:
        return {
            "schema": "voice-care/supervisor-plan-preflight@1",
            "valid": False,
            "errors": errors,
        }

    profile = _load_profile(profile_path, errors)
    if profile:
        _validate_profile(profile, errors=errors)

    objective_text = objective_path.read_text(encoding="utf-8")
    objective_heading_ids = re.findall(r"(?m)^##\s+(\S+)", objective_text)
    invalid_goal_headings = [
        item
        for item in objective_heading_ids
        if not re.fullmatch(r"VOICE-CARE-G\d{3}", item)
    ]
    if invalid_goal_headings:
        errors.append(f"invalid objective record headings: {invalid_goal_headings}")

    goals = parse_goal_heap(objective_text)
    goal_ids = [goal.goal_id for goal in goals]
    if objective_heading_ids != goal_ids:
        errors.append(
            "objective parser did not materialize headings exactly: "
            f"headings={objective_heading_ids}, parsed={goal_ids}"
        )
    goal_id_set = set(goal_ids)
    if len(goal_ids) != len(goal_id_set):
        duplicate_ids = sorted(
            item for item in goal_id_set if goal_ids.count(item) > 1
        )
        errors.append(f"duplicate goal IDs: {duplicate_ids}")
    if len(goals) < 14:
        errors.append(f"expected at least 14 goals/subgoals, got {len(goals)}")

    goal_edges: dict[str, tuple[str, ...]] = {}
    for goal in goals:
        if not re.fullmatch(r"VOICE-CARE-G\d{3}", goal.goal_id):
            errors.append(f"invalid goal ID: {goal.goal_id}")
        missing = [
            field for field in REQUIRED_GOAL_FIELDS if field not in goal.fields
        ]
        if missing:
            errors.append(f"{goal.goal_id} missing fields: {missing}")
        status = str(goal.fields.get("status") or "").strip()
        if status not in GOAL_STATES:
            errors.append(f"{goal.goal_id} has noncanonical status {status!r}")
        priority = str(goal.fields.get("priority") or "").strip()
        if priority not in {"P0", "P1", "P2", "P3"}:
            errors.append(f"{goal.goal_id} has invalid priority {priority!r}")
        parent = str(goal.fields.get("parent") or "").strip()
        parents = (parent,) if parent else ()
        goal_edges[goal.goal_id] = parents
        if parent and parent not in goal_id_set:
            errors.append(f"{goal.goal_id} has unknown parent {parent}")
        _positive_int(
            goal.fields.get("fib_priority"),
            field=f"{goal.goal_id} fib priority",
            errors=errors,
        )
        outputs = _csv(goal.fields.get("outputs"))
        if not outputs:
            errors.append(f"{goal.goal_id} has no outputs")
        errors.extend(
            f"{goal.goal_id}: {item}"
            for item in _safe_relative_paths(outputs, field="outputs")
        )
        for field in (
            "track",
            "bundle",
            "goal",
            "evidence",
            "validation",
            "acceptance",
            "gap_task",
            "refinement",
            "embedding_query",
            "ast_query",
        ):
            if not str(goal.fields.get(field) or "").strip():
                errors.append(f"{goal.goal_id} has empty {field}")

    goal_cycles = _cycle_nodes(goal_edges)
    if goal_cycles:
        errors.append(f"goal parent cycle: {list(goal_cycles)}")
    roots = sorted(goal_id for goal_id, parents in goal_edges.items() if not parents)
    if roots != ["VOICE-CARE-G000"]:
        errors.append(f"expected only VOICE-CARE-G000 as root, got {roots}")

    todo_text = todo_path.read_text(encoding="utf-8")
    task_heading_ids = re.findall(r"(?m)^##\s+(\S+)", todo_text)
    invalid_task_headings = [
        item
        for item in task_heading_ids
        if not re.fullmatch(r"VOICE-CARE-\d{3}", item)
    ]
    if invalid_task_headings:
        errors.append(f"invalid task record headings: {invalid_task_headings}")

    tasks = parse_task_file(todo_path, TASK_PREFIX)
    task_ids = [task.task_id for task in tasks]
    if task_heading_ids != task_ids:
        errors.append(
            "task parser did not materialize headings exactly: "
            f"headings={task_heading_ids}, parsed={task_ids}"
        )
    task_id_set = set(task_ids)
    if len(task_ids) != len(task_id_set):
        duplicate_ids = sorted(
            item for item in task_id_set if task_ids.count(item) > 1
        )
        errors.append(f"duplicate task IDs: {duplicate_ids}")
    if len(tasks) < 52:
        errors.append(f"expected at least 52 executable tasks, got {len(tasks)}")

    task_edges: dict[str, tuple[str, ...]] = {}
    task_records: list[dict[str, object]] = []
    goals_with_tasks: set[str] = set()
    shard_population = {index: 0 for index in range(4)}
    for task in tasks:
        if not re.fullmatch(r"VOICE-CARE-\d{3}", task.task_id):
            errors.append(f"invalid task ID: {task.task_id}")
        else:
            shard_population[int(task.task_id.rsplit("-", 1)[1]) % 4] += 1
        missing = [
            field for field in REQUIRED_TASK_FIELDS if field not in task.metadata
        ]
        if missing:
            errors.append(f"{task.task_id} missing fields: {missing}")
        raw_status = str(task.metadata.get("status") or "").strip()
        if raw_status not in TASK_STATES:
            errors.append(
                f"{task.task_id} has noncanonical source status {raw_status!r}"
            )
        if task.status not in TASK_STATES:
            errors.append(
                f"{task.task_id} has noncanonical normalized status "
                f"{task.status!r}"
            )
        if task.priority not in {"P0", "P1", "P2", "P3"}:
            errors.append(f"{task.task_id} has invalid priority {task.priority!r}")
        if str(task.metadata.get("completion") or "").strip() != "manual":
            errors.append(f"{task.task_id} completion must be manual")
        goal_id = str(task.metadata.get("goal id") or "").strip()
        if goal_id not in goal_id_set:
            errors.append(f"{task.task_id} has unknown goal ID {goal_id!r}")
        else:
            goals_with_tasks.add(goal_id)
        dependencies = tuple(task.depends_on)
        task_edges[task.task_id] = tuple(
            item for item in dependencies if item in task_id_set
        )
        for dependency in dependencies:
            if dependency == task.task_id:
                errors.append(f"{task.task_id} depends on itself")
            elif dependency not in task_id_set and dependency not in goal_id_set:
                errors.append(
                    f"{task.task_id} has unknown dependency {dependency!r}"
                )
        if not task.outputs:
            errors.append(f"{task.task_id} has no outputs")
        errors.extend(
            f"{task.task_id}: {item}"
            for item in _safe_relative_paths(task.outputs, field="outputs")
        )
        predicted_files = _csv(task.metadata.get("predicted files"))
        if not predicted_files:
            errors.append(f"{task.task_id} has no predicted files")
        errors.extend(
            f"{task.task_id}: {item}"
            for item in _safe_relative_paths(
                predicted_files,
                field="predicted files",
            )
        )
        if set(predicted_files) != set(task.outputs):
            errors.append(
                f"{task.task_id} outputs and predicted files differ: "
                f"outputs={sorted(task.outputs)}, "
                f"predicted={sorted(predicted_files)}"
            )
        if not task.validation:
            errors.append(f"{task.task_id} has no validation command")
        if not task.acceptance:
            errors.append(f"{task.task_id} has empty acceptance")
        if task.board_namespace != BOARD_NAMESPACE:
            errors.append(
                f"{task.task_id} has unexpected board namespace "
                f"{task.board_namespace!r}"
            )
        for field in (
            "track",
            "bundle",
            "parallel lane",
            "resource class",
            "conflict policy",
        ):
            if not str(task.metadata.get(field) or "").strip():
                errors.append(f"{task.task_id} has empty {field}")
        if str(task.metadata.get("symbolic first") or "").strip().lower() != "true":
            errors.append(f"{task.task_id} must set Symbolic first: true")
        _positive_int(
            task.metadata.get("llm context budget bytes"),
            field=f"{task.task_id} LLM context budget bytes",
            errors=errors,
            maximum=32768,
        )
        task_records.append(
            {
                "task_id": task.task_id,
                "title": task.title,
                "status": task.status,
                "goal_id": goal_id,
                "depends_on": list(task.depends_on),
                "outputs": list(task.outputs),
                "acceptance": task.acceptance,
                "board_namespace": task.board_namespace,
                "canonical_task_cid": task.canonical_task_cid,
            }
        )

    task_cycles = _cycle_nodes(task_edges)
    if task_cycles:
        errors.append(f"task dependency cycle: {list(task_cycles)}")
    if tasks and any(count == 0 for count in shard_population.values()):
        errors.append(
            "task IDs do not populate all four deterministic shards: "
            f"{shard_population}"
        )
    uncovered_goals = sorted(
        goal_id_set.difference(goals_with_tasks).difference({"VOICE-CARE-G000"})
    )
    if uncovered_goals:
        errors.append(f"goals without an executable task: {uncovered_goals}")

    dependency_graph = materialize_task_dependency_dag(task_records)
    if dependency_graph.invalid_task_cids:
        errors.append(
            "typed dependency graph has invalid task CIDs: "
            f"{list(dependency_graph.invalid_task_cids)}"
        )
    if dependency_graph.repair_evidence:
        errors.append(
            "typed dependency graph requires repair: "
            + json.dumps(
                [item.to_dict() for item in dependency_graph.repair_evidence],
                sort_keys=True,
            )
        )

    return {
        "schema": "voice-care/supervisor-plan-preflight@1",
        "valid": not errors,
        "errors": errors,
        "program_id": PROGRAM_ID,
        "plan_path": str(plan_path),
        "plan_sha256": _sha256(plan_path),
        "objective_path": str(objective_path),
        "objective_sha256": _sha256(objective_path),
        "goal_count": len(goals),
        "root_goal_ids": roots,
        "todo_path": str(todo_path),
        "todo_sha256": _sha256(todo_path),
        "task_count": len(tasks),
        "ready_task_count": sum(task.status == "todo" for task in tasks),
        "task_shard_population": shard_population,
        "profile_path": str(profile_path),
        "profile_sha256": _sha256(profile_path),
        "dependency_graph_id": _canonical_sha256(dependency_graph.to_dict()),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan-path", type=Path, default=PLAN_PATH)
    parser.add_argument("--objective-path", type=Path, default=OBJECTIVE_PATH)
    parser.add_argument("--todo-path", type=Path, default=TODO_PATH)
    parser.add_argument("--profile-path", type=Path, default=PROFILE_PATH)
    args = parser.parse_args()
    result = validate(
        args.plan_path.resolve(),
        args.objective_path.resolve(),
        args.todo_path.resolve(),
        args.profile_path.resolve(),
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
