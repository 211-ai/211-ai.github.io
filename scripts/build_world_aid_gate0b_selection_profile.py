#!/usr/bin/env python3
"""Build the immutable external-authority Gate 0B selection profile.

This is a deterministic projection tool, not an approval or launcher.  It
accepts only a freshly generated board that passes the reopened-board
contract, preserves every canonical bundle/task byte-for-byte except for the
explicit projection fields below, and writes a paired JSON/DuckDB profile
without replacing an existing artifact.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Mapping, Sequence
from copy import deepcopy
from pathlib import Path
from typing import Any

from scripts.verify_world_aid_generated_board import (
    GATE0B_REOPENED_CONTRACT,
    verify_generated_board,
)

PROFILE_NAME = "g038-g040.index.json"
EXECUTION_AUTHORITY = "operator-gate-first/v1"
SELECTED_GOALS = frozenset({"WORLDCOIN-G038", "WORLDCOIN-G039", "WORLDCOIN-G040"})
PREPARATION_GOALS = frozenset(
    {
        "WORLDCOIN-G002",
        "WORLDCOIN-G037",
        "WORLDCOIN-G041",
        "WORLDCOIN-G042",
    }
)
HUMAN_ONLY_GOALS = frozenset({"WORLDCOIN-G035", "WORLDCOIN-G036"})
EXPECTED_REVIEW_GOALS = frozenset(f"WORLDCOIN-G{number:03d}" for number in range(1, 43)) - HUMAN_ONLY_GOALS
EXPECTED_BUNDLES = frozenset(
    {
        "worldcoin-human-aid/siwe-offline-bootstrap",
        "worldcoin-human-aid/zkp-toolchain-bootstrap",
        "worldcoin-human-aid/duckdb-bootstrap",
    }
)


class SelectionProfileError(ValueError):
    """Raised when the source cannot produce the exact Gate profile."""


def _fail(message: str) -> None:
    raise SelectionProfileError(message)


def _normalized_status(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def _plain_bool(value: Any, expected: bool, label: str) -> None:
    if type(value) is not bool or value is not expected:
        _fail(f"{label} must be {str(expected).lower()}")


def build_selection_profile(
    canonical: Mapping[str, Any],
    *,
    canonical_path: str,
) -> dict[str, Any]:
    """Return the one allowed G038-G040 external-authority projection."""

    if not isinstance(canonical, Mapping):
        _fail("canonical bundle index must be an object")
    raw_bundles = canonical.get("bundles")
    if not isinstance(raw_bundles, Mapping) or not raw_bundles:
        _fail("canonical bundle index contains no bundles")

    goal_records: dict[str, list[tuple[str, str, str]]] = {}
    seen_task_ids: set[str] = set()
    seen_task_cids: set[str] = set()
    selected_bundles: set[str] = set()
    for raw_bundle_key, raw_bundle in raw_bundles.items():
        if not isinstance(raw_bundle_key, str) or not raw_bundle_key or not isinstance(raw_bundle, Mapping):
            _fail("canonical bundle key/payload is invalid")
        bundle_key = raw_bundle_key
        tasks = raw_bundle.get("tasks")
        if not isinstance(tasks, list) or not tasks:
            _fail(f"canonical bundle has no tasks: {bundle_key}")
        bundle_goals: set[str] = set()
        for index, raw_task in enumerate(tasks):
            if not isinstance(raw_task, Mapping):
                _fail(f"canonical task is not an object: {bundle_key}[{index}]")
            goal_id = raw_task.get("goal_id")
            task_id = raw_task.get("task_id")
            canonical_cid = raw_task.get("canonical_task_cid")
            fallback_cid = raw_task.get("task_cid")
            if not isinstance(goal_id, str) or not goal_id or not isinstance(task_id, str) or not task_id:
                _fail(f"canonical task identity is invalid: {bundle_key}[{index}]")
            if canonical_cid and fallback_cid and canonical_cid != fallback_cid:
                _fail(f"canonical task has conflicting CID fields: {bundle_key}[{index}]")
            task_cid = canonical_cid or fallback_cid
            if not isinstance(task_cid, str) or not task_cid:
                _fail(f"canonical task CID is invalid: {bundle_key}[{index}]")
            if task_id in seen_task_ids:
                _fail(f"duplicate canonical task ID: {task_id}")
            if task_cid in seen_task_cids:
                _fail(f"duplicate canonical task CID: {task_cid}")
            seen_task_ids.add(task_id)
            seen_task_cids.add(task_cid)
            goal_records.setdefault(goal_id, []).append((bundle_key, task_id, task_cid))
            bundle_goals.add(goal_id)
            if goal_id in SELECTED_GOALS:
                if _normalized_status(raw_task.get("status")) != "reopened":
                    _fail(f"{goal_id} canonical task must be exactly reopened")
                _plain_bool(
                    raw_task.get("is_schedulable"),
                    True,
                    f"{goal_id}.is_schedulable",
                )
                _plain_bool(
                    raw_task.get("review_only"),
                    False,
                    f"{goal_id}.review_only",
                )
        if bundle_goals & SELECTED_GOALS:
            if not bundle_goals <= SELECTED_GOALS:
                _fail(f"selected bundle mixes Gate and non-Gate goals: {bundle_key}")
            _plain_bool(
                raw_bundle.get("is_schedulable"),
                True,
                f"{bundle_key}.is_schedulable",
            )
            _plain_bool(
                raw_bundle.get("review_only"),
                False,
                f"{bundle_key}.review_only",
            )
            if "status" in raw_bundle and _normalized_status(raw_bundle.get("status")) != "reopened":
                _fail(f"{bundle_key} canonical bundle must be exactly reopened")
            selected_bundles.add(bundle_key)

    observed_goals = set(goal_records)
    if observed_goals != EXPECTED_REVIEW_GOALS:
        _fail(
            "canonical goal set is not the exact 40-goal reopened review "
            f"universe; missing={sorted(EXPECTED_REVIEW_GOALS - observed_goals)}, "
            f"unexpected={sorted(observed_goals - EXPECTED_REVIEW_GOALS)}"
        )
    if selected_bundles != EXPECTED_BUNDLES:
        _fail(f"selected bundle set drifted; observed={sorted(selected_bundles)}")

    profile = deepcopy(dict(canonical))
    profile_bundles = profile.get("bundles")
    if not isinstance(profile_bundles, dict):
        _fail("deep-copied bundle index lost its bundle map")

    completed_task_ids = {task_id for goal_id in PREPARATION_GOALS for _, task_id, _ in goal_records[goal_id]}
    completed_task_cids = {task_cid for goal_id in PREPARATION_GOALS for _, _, task_cid in goal_records[goal_id]}
    for bundle_key, bundle in profile_bundles.items():
        if not isinstance(bundle, dict):
            _fail(f"projected bundle is not an object: {bundle_key}")
        tasks = bundle.get("tasks")
        if not isinstance(tasks, list):
            _fail(f"projected bundle tasks are invalid: {bundle_key}")
        selected_tasks: list[dict[str, Any]] = []
        for task in tasks:
            if not isinstance(task, dict):
                _fail(f"projected task is not an object: {bundle_key}")
            goal_id = str(task.get("goal_id") or "")
            if goal_id in PREPARATION_GOALS:
                task["status"] = "completed"
            if goal_id in SELECTED_GOALS:
                task["execution_authority"] = EXECUTION_AUTHORITY
                selected_tasks.append(task)
        if selected_tasks:
            selected_cids = sorted(
                str(task.get("canonical_task_cid") or task.get("task_cid") or "") for task in selected_tasks
            )
            selected_ids = sorted(str(task.get("task_id") or "") for task in selected_tasks)
            if not all(selected_cids) or not all(selected_ids):
                _fail(f"selected bundle has an incomplete task identity: {bundle_key}")
            bundle.update(
                {
                    "status": "reopened",
                    "execution_authority": EXECUTION_AUTHORITY,
                    "active_member_task_cids": selected_cids,
                    "blocked_member_task_cids": [],
                    "execution_slice_task_cids": selected_cids,
                    "execution_slice_task_ids": selected_ids,
                }
            )

    profile.update(
        {
            "profile_id": "gate0b-selection-reopened",
            "derived_from_bundle_index": canonical_path,
            "execution_goal_ids": sorted(SELECTED_GOALS),
            "execution_allowlist": sorted(selected_bundles),
            "excluded_bundle_keys": sorted(set(profile_bundles) - selected_bundles),
            "review_only_goal_ids": [],
            "review_projection_goal_ids": [],
            "completed_prerequisite_goal_ids": sorted(PREPARATION_GOALS),
            "receipt_backed_completed_goal_ids": sorted(PREPARATION_GOALS),
            "receipt_backed_completed_task_ids": sorted(completed_task_ids),
            "receipt_backed_completed_task_cids": sorted(completed_task_cids),
        }
    )
    return profile


def _artifact_api(repo_root: Path):
    nested = repo_root / "ipfs_accelerate_py"
    if nested.is_dir() and str(nested) not in sys.path:
        sys.path.insert(0, str(nested))
    previous_skip_core = os.environ.get("IPFS_ACCEL_SKIP_CORE")
    os.environ["IPFS_ACCEL_SKIP_CORE"] = "1"
    try:
        from ipfs_accelerate_py.agent_supervisor.artifact_store import (
            read_bundle_index_artifact,
            write_bundle_index_artifact,
        )
    except ImportError as exc:  # pragma: no cover - deployment packaging error.
        _fail(f"agent-supervisor artifact API is unavailable: {exc}")
    finally:
        if previous_skip_core is None:
            os.environ.pop("IPFS_ACCEL_SKIP_CORE", None)
        else:
            os.environ["IPFS_ACCEL_SKIP_CORE"] = previous_skip_core
    return read_bundle_index_artifact, write_bundle_index_artifact


def build_profile_artifacts(
    *,
    repo_root: Path,
    objective_path: Path,
    generated_root: Path,
) -> tuple[Path, Path]:
    """Verify, build, and atomically create the paired profile artifacts."""

    root = repo_root.resolve(strict=True)
    if not root.is_dir():
        _fail("repository root must be a directory")
    if generated_root.is_symlink():
        _fail("generated root cannot be a symlink")
    generated = generated_root.resolve(strict=True)
    try:
        generated.relative_to(root)
    except ValueError:
        _fail("generated root must remain inside the repository")
    if not generated.is_dir():
        _fail("generated root must be a directory")
    if generated.parent != (root / "data/worldcoin_human_aid/agent_supervisor/regenerations"):
        _fail("generated root must be one immutable direct regeneration child")

    if objective_path.is_symlink():
        _fail("objective path cannot be a symlink")
    objective = objective_path.resolve(strict=True)
    try:
        objective.relative_to(root)
    except ValueError:
        _fail("objective path must remain inside the repository")
    if not objective.is_file():
        _fail("objective path must be a regular file")

    verify_generated_board(
        repo_root=root,
        objective_path=objective,
        generated_root=generated,
        board_contract=GATE0B_REOPENED_CONTRACT,
    )
    source = generated / "objective_bundles/index.json"
    if source.is_symlink() or not source.is_file():
        _fail("canonical bundle index must be a regular, non-symlink file")
    try:
        source.resolve(strict=True).relative_to(generated)
    except (OSError, RuntimeError, ValueError):
        _fail("canonical bundle index escapes the generated root")

    destination_dir = generated / "launch_profiles"
    destination = destination_dir / PROFILE_NAME
    paired_duckdb = destination.with_suffix(".duckdb")
    if destination_dir.is_symlink():
        _fail("launch_profiles cannot be a symlink")
    if destination_dir.exists():
        if not destination_dir.is_dir():
            _fail("launch_profiles must be a directory")
        try:
            destination_dir.resolve(strict=True).relative_to(generated)
        except (OSError, RuntimeError, ValueError):
            _fail("launch_profiles escapes the generated root")
    else:
        destination_dir.mkdir(mode=0o700)
    if destination.exists() or destination.is_symlink() or paired_duckdb.exists() or paired_duckdb.is_symlink():
        _fail("selection profile already exists; refusing to replace it")

    read_bundle_index, write_bundle_index = _artifact_api(root)
    canonical = read_bundle_index(source)
    source_relative = source.relative_to(root).as_posix()
    profile = build_selection_profile(
        canonical,
        canonical_path=source_relative,
    )

    reserved: list[Path] = []
    try:
        for target in (destination, paired_duckdb):
            descriptor = os.open(
                target,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0),
                0o600,
            )
            os.close(descriptor)
            reserved.append(target)
    except FileExistsError:
        for target in reserved:
            target.unlink(missing_ok=True)
        _fail("selection profile already exists; refusing to replace it")

    try:
        published = write_bundle_index(destination, profile)
        if not destination.is_file() or not paired_duckdb.is_file():
            _fail("writer did not publish both JSON and DuckDB profile artifacts")
        rendered_json = read_bundle_index(destination)
        rendered_duckdb = read_bundle_index(paired_duckdb)
        if rendered_json != published or rendered_duckdb != published:
            _fail("written JSON/DuckDB profile does not round-trip exactly")
    except BaseException:
        # The writer's individual file replacement is atomic, but a failed
        # pair is not a valid publication. Leave diagnosis to the operator and
        # never retry into this immutable regeneration root.
        raise
    return destination, paired_duckdb


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--objective-path", type=Path, required=True)
    parser.add_argument("--generated-root", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    try:
        json_path, duckdb_path = build_profile_artifacts(
            repo_root=args.repo_root,
            objective_path=args.objective_path,
            generated_root=args.generated_root,
        )
    except (OSError, SelectionProfileError, ValueError) as exc:
        print(f"World-aid Gate 0B profile build REFUSED: {exc}", file=sys.stderr)
        return 1
    print(json_path)
    print(duckdb_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
