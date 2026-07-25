"""Tests for the immutable Gate 0B operator selection-profile builder."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

import scripts.build_world_aid_gate0b_selection_profile as profile_builder
import scripts.verify_world_aid_gate_0b as gate_verifier
from scripts.build_world_aid_gate0b_selection_profile import (
    EXECUTION_AUTHORITY,
    EXPECTED_BUNDLES,
    PREPARATION_GOALS,
    PROFILE_NAME,
    SELECTED_GOALS,
    SelectionProfileError,
    build_profile_artifacts,
    build_selection_profile,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
REVIEW_BUNDLE = "worldcoin-human-aid/review-work"
EXTERNAL_BUNDLE_FIELDS = {
    "execution_authority",
    "active_member_task_cids",
    "blocked_member_task_cids",
    "execution_slice_task_cids",
    "execution_slice_task_ids",
}


def _goal_id(number: int) -> str:
    return f"WORLDCOIN-G{number:03d}"


def _task(number: int, suffix: str = "main") -> dict[str, Any]:
    goal_id = _goal_id(number)
    selected = goal_id in SELECTED_GOALS
    return {
        "goal_id": goal_id,
        "task_id": f"WORLDCOIN-AUTO-G{number:03d}-{suffix}",
        "canonical_task_cid": f"bafy-g{number:03d}-{suffix}",
        "status": "reopened" if selected else "todo",
        "is_schedulable": True,
        "review_only": False,
        "preserved_task_metadata": {"goal_number": number, "suffix": suffix},
    }


def _canonical_index() -> dict[str, Any]:
    selected_bundle_by_goal = {
        _goal_id(38): "worldcoin-human-aid/siwe-offline-bootstrap",
        _goal_id(39): "worldcoin-human-aid/zkp-toolchain-bootstrap",
        _goal_id(40): "worldcoin-human-aid/duckdb-bootstrap",
    }
    bundles: dict[str, dict[str, Any]] = {
        REVIEW_BUNDLE: {
            "bundle_key": REVIEW_BUNDLE,
            "preserved_bundle_metadata": "review",
            "tasks": [],
        }
    }
    for bundle_key in sorted(EXPECTED_BUNDLES):
        bundles[bundle_key] = {
            "bundle_key": bundle_key,
            "is_schedulable": True,
            "review_only": False,
            "preserved_bundle_metadata": bundle_key,
            "tasks": [],
        }

    for number in range(1, 43):
        goal_id = _goal_id(number)
        if number in {35, 36}:
            continue
        suffix = "z" if number == 38 else "main"
        bundle_key = selected_bundle_by_goal.get(goal_id, REVIEW_BUNDLE)
        bundles[bundle_key]["tasks"].append(_task(number, suffix))

    # A canonical goal may legitimately materialize as multiple globally
    # unique tasks. These exercise exact slices and exact receipt projection.
    bundles[selected_bundle_by_goal[_goal_id(38)]]["tasks"].append(_task(38, "a"))
    bundles[REVIEW_BUNDLE]["tasks"].append(_task(2, "secondary"))
    return {
        "schema": "ipfs_accelerate_py.agent_supervisor.bundle_index@1",
        "generated_at": "2026-07-24T00:00:00Z",
        "preserved_top_level_metadata": {"source": "canonical"},
        "bundles": bundles,
    }


def _tasks_for_goal(payload: dict[str, Any], goal_id: str) -> list[dict[str, Any]]:
    return [task for bundle in payload["bundles"].values() for task in bundle["tasks"] if task["goal_id"] == goal_id]


def _one_task(payload: dict[str, Any], goal_id: str) -> dict[str, Any]:
    tasks = _tasks_for_goal(payload, goal_id)
    assert tasks
    return tasks[0]


def _remove_goal(payload: dict[str, Any], goal_id: str) -> list[dict[str, Any]]:
    removed: list[dict[str, Any]] = []
    for bundle in payload["bundles"].values():
        retained = []
        for task in bundle["tasks"]:
            (removed if task["goal_id"] == goal_id else retained).append(task)
        bundle["tasks"] = retained
    return removed


def _identity_sets(
    payload: dict[str, Any],
    goals: frozenset[str],
) -> tuple[list[str], list[str]]:
    tasks = [task for goal_id in goals for task in _tasks_for_goal(payload, goal_id)]
    return (
        sorted(task["task_id"] for task in tasks),
        sorted(task["canonical_task_cid"] for task in tasks),
    )


def test_builds_exact_deterministic_authority_and_preparation_projection() -> None:
    canonical = _canonical_index()
    original = deepcopy(canonical)
    canonical_path = "data/worldcoin_human_aid/agent_supervisor/regenerations/review-1/objective_bundles/index.json"

    for bundle_key in EXPECTED_BUNDLES:
        source_bundle = canonical["bundles"][bundle_key]
        assert source_bundle["is_schedulable"] is True
        assert source_bundle["review_only"] is False
        assert EXTERNAL_BUNDLE_FIELDS.isdisjoint(source_bundle)
        for task in source_bundle["tasks"]:
            assert task["status"] == "reopened"
            assert task["is_schedulable"] is True
            assert task["review_only"] is False
            assert "execution_authority" not in task

    profile = build_selection_profile(
        canonical,
        canonical_path=canonical_path,
    )
    assert profile == build_selection_profile(
        canonical,
        canonical_path=canonical_path,
    )
    assert canonical == original

    for bundle_key, source_bundle in canonical["bundles"].items():
        projected_bundle = profile["bundles"][bundle_key]
        expected_bundle = deepcopy(source_bundle)
        for task in expected_bundle["tasks"]:
            if task["goal_id"] in PREPARATION_GOALS:
                task["status"] = "completed"
            if task["goal_id"] in SELECTED_GOALS:
                task["execution_authority"] = EXECUTION_AUTHORITY
        if bundle_key in EXPECTED_BUNDLES:
            expected_cids = sorted(task["canonical_task_cid"] for task in source_bundle["tasks"])
            expected_ids = sorted(task["task_id"] for task in source_bundle["tasks"])
            expected_bundle.update(
                {
                    "status": "reopened",
                    "execution_authority": EXECUTION_AUTHORITY,
                    "active_member_task_cids": expected_cids,
                    "blocked_member_task_cids": [],
                    "execution_slice_task_cids": expected_cids,
                    "execution_slice_task_ids": expected_ids,
                }
            )
        assert projected_bundle == expected_bundle

    completed_ids, completed_cids = _identity_sets(canonical, PREPARATION_GOALS)
    assert profile["profile_id"] == "gate0b-selection-reopened"
    assert profile["derived_from_bundle_index"] == canonical_path
    assert profile["execution_goal_ids"] == sorted(SELECTED_GOALS)
    assert profile["execution_allowlist"] == sorted(EXPECTED_BUNDLES)
    assert profile["excluded_bundle_keys"] == [REVIEW_BUNDLE]
    assert profile["review_only_goal_ids"] == []
    assert profile["review_projection_goal_ids"] == []
    assert profile["completed_prerequisite_goal_ids"] == sorted(PREPARATION_GOALS)
    assert profile["receipt_backed_completed_goal_ids"] == sorted(PREPARATION_GOALS)
    assert profile["receipt_backed_completed_task_ids"] == completed_ids
    assert profile["receipt_backed_completed_task_cids"] == completed_cids


@pytest.mark.parametrize(
    ("case", "message"),
    [
        ("missing_goal", "canonical goal set"),
        ("extra_goal", "canonical goal set"),
        ("missing_selected_bundle", "selected bundle set drifted"),
        ("extra_selected_bundle", "selected bundle set drifted"),
        ("mixed_bundle", "selected bundle mixes"),
    ],
)
def test_refuses_missing_extra_or_mixed_goals_and_bundles(
    case: str,
    message: str,
) -> None:
    canonical = _canonical_index()
    if case == "missing_goal":
        _remove_goal(canonical, _goal_id(2))
    elif case == "extra_goal":
        canonical["bundles"][REVIEW_BUNDLE]["tasks"].append(_task(43))
    elif case == "missing_selected_bundle":
        old_key = "worldcoin-human-aid/siwe-offline-bootstrap"
        new_key = "worldcoin-human-aid/siwe-renamed"
        canonical["bundles"][new_key] = canonical["bundles"].pop(old_key)
        canonical["bundles"][new_key]["bundle_key"] = new_key
    elif case == "extra_selected_bundle":
        source_key = "worldcoin-human-aid/siwe-offline-bootstrap"
        extra_key = "worldcoin-human-aid/unexpected-bootstrap"
        extra_task = canonical["bundles"][source_key]["tasks"].pop()
        canonical["bundles"][extra_key] = {
            "bundle_key": extra_key,
            "is_schedulable": True,
            "review_only": False,
            "tasks": [extra_task],
        }
    else:
        moved = _remove_goal(canonical, _goal_id(1))
        canonical["bundles"]["worldcoin-human-aid/siwe-offline-bootstrap"]["tasks"].extend(moved)

    with pytest.raises(SelectionProfileError, match=message):
        build_selection_profile(canonical, canonical_path="canonical.json")


@pytest.mark.parametrize(
    ("scope", "status"),
    [
        ("task", "blocked"),
        ("task", "failed"),
        ("bundle", "blocked"),
        ("bundle", "failed"),
    ],
)
def test_refuses_blocked_or_failed_selected_statuses(
    scope: str,
    status: str,
) -> None:
    canonical = _canonical_index()
    bundle = canonical["bundles"]["worldcoin-human-aid/zkp-toolchain-bootstrap"]
    if scope == "task":
        bundle["tasks"][0]["status"] = status
    else:
        bundle["status"] = status

    with pytest.raises(SelectionProfileError, match="exactly reopened"):
        build_selection_profile(canonical, canonical_path="canonical.json")


@pytest.mark.parametrize(
    ("scope", "field", "value"),
    [
        ("task", "is_schedulable", False),
        ("task", "review_only", True),
        ("bundle", "is_schedulable", False),
        ("bundle", "review_only", True),
    ],
)
def test_refuses_false_selected_scheduling_contract(
    scope: str,
    field: str,
    value: bool,
) -> None:
    canonical = _canonical_index()
    bundle = canonical["bundles"]["worldcoin-human-aid/duckdb-bootstrap"]
    target = bundle["tasks"][0] if scope == "task" else bundle
    target[field] = value

    with pytest.raises(SelectionProfileError, match=field):
        build_selection_profile(canonical, canonical_path="canonical.json")


@pytest.mark.parametrize("identity_field", ["task_id", "canonical_task_cid"])
def test_refuses_duplicate_global_task_identities(identity_field: str) -> None:
    canonical = _canonical_index()
    first = _one_task(canonical, _goal_id(1))
    second = _one_task(canonical, _goal_id(3))
    second[identity_field] = first[identity_field]

    with pytest.raises(SelectionProfileError, match="duplicate canonical task"):
        build_selection_profile(canonical, canonical_path="canonical.json")


def test_refuses_conflicting_canonical_and_fallback_cids() -> None:
    canonical = _canonical_index()
    task = _one_task(canonical, _goal_id(38))
    task["task_cid"] = "bafy-conflicting"

    with pytest.raises(SelectionProfileError, match="conflicting CID"):
        build_selection_profile(canonical, canonical_path="canonical.json")


def _write_bound_json(
    repo_root: Path,
    relative_path: str,
    payload: dict[str, Any],
) -> dict[str, str]:
    path = repo_root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()
    path.write_bytes(raw)
    return {
        "path": relative_path,
        "sha256": f"sha256:{hashlib.sha256(raw).hexdigest()}",
    }


def test_profile_passes_exact_operator_gate_derived_profile_semantics(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    canonical = _canonical_index()
    canonical_relative = "artifacts/canonical.index.json"
    profile = build_selection_profile(
        canonical,
        canonical_path=canonical_relative,
    )
    canonical_artifact = _write_bound_json(
        repo_root,
        canonical_relative,
        canonical,
    )
    derived_artifact = _write_bound_json(
        repo_root,
        "artifacts/g038-g040.index.json",
        profile,
    )

    projected_cids, allowed_bundles = gate_verifier._validate_derived_bundle_profile(
        repo_root.resolve(),
        canonical_artifact,
        derived_artifact,
        context="selection profile",
        expected_goals=SELECTED_GOALS,
        completed_prerequisite_goals=PREPARATION_GOALS,
        exact_allowed_bundles=EXPECTED_BUNDLES,
        require_operator_gate_contract=True,
    )

    expected_cids = {
        task["canonical_task_cid"]
        for bundle_key in EXPECTED_BUNDLES
        for task in canonical["bundles"][bundle_key]["tasks"]
    }
    assert projected_cids == expected_cids
    assert allowed_bundles == set(EXPECTED_BUNDLES)


def _artifact_layout(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    repo_root = tmp_path / "repo"
    generated_root = repo_root / "data/worldcoin_human_aid/agent_supervisor/regenerations/review-1"
    source = generated_root / "objective_bundles/index.json"
    source.parent.mkdir(parents=True)
    objective = repo_root / "docs/objective.md"
    objective.parent.mkdir(parents=True)
    objective.write_text("# Objective\n", encoding="utf-8")
    return repo_root, generated_root, source, objective


def test_publishes_paired_nested_artifacts_without_replacing_siblings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root, generated_root, source, objective = _artifact_layout(tmp_path)
    read_artifact, write_artifact = profile_builder._artifact_api(REPOSITORY_ROOT)
    write_artifact(source, _canonical_index())
    launch_profiles = generated_root / "launch_profiles"
    launch_profiles.mkdir()
    sibling = launch_profiles / "existing-profile.json"
    sibling.write_text('{"preserve":true}\n', encoding="utf-8")
    monkeypatch.setattr(profile_builder, "verify_generated_board", lambda **_: None)
    monkeypatch.setattr(
        profile_builder,
        "_artifact_api",
        lambda _: (read_artifact, write_artifact),
    )

    json_path, duckdb_path = build_profile_artifacts(
        repo_root=repo_root,
        objective_path=objective,
        generated_root=generated_root,
    )

    assert json_path == launch_profiles / PROFILE_NAME
    assert duckdb_path == json_path.with_suffix(".duckdb")
    assert json_path.is_file()
    assert duckdb_path.is_file()
    assert sibling.read_text(encoding="utf-8") == '{"preserve":true}\n'
    from_json = read_artifact(json_path)
    from_duckdb = read_artifact(duckdb_path)
    assert from_json == from_duckdb
    assert from_json["query_store"]["duckdb_path"] == duckdb_path.name
    assert from_json["execution_goal_ids"] == sorted(SELECTED_GOALS)

    before = (json_path.read_bytes(), duckdb_path.read_bytes())
    with pytest.raises(SelectionProfileError, match="refusing to replace"):
        build_profile_artifacts(
            repo_root=repo_root,
            objective_path=objective,
            generated_root=generated_root,
        )
    assert (json_path.read_bytes(), duckdb_path.read_bytes()) == before


@pytest.mark.parametrize("existing_suffix", [".json", ".duckdb"])
def test_no_replace_refuses_either_existing_target_before_artifact_access(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    existing_suffix: str,
) -> None:
    repo_root, generated_root, source, objective = _artifact_layout(tmp_path)
    source.write_text('{"bundles":{}}\n', encoding="utf-8")
    launch_profiles = generated_root / "launch_profiles"
    launch_profiles.mkdir()
    target = launch_profiles / (
        PROFILE_NAME if existing_suffix == ".json" else Path(PROFILE_NAME).with_suffix(".duckdb").name
    )
    target.write_bytes(b"do-not-replace")
    monkeypatch.setattr(profile_builder, "verify_generated_board", lambda **_: None)
    monkeypatch.setattr(
        profile_builder,
        "_artifact_api",
        lambda _: pytest.fail("artifact API must not run after no-replace refusal"),
    )

    with pytest.raises(SelectionProfileError, match="refusing to replace"):
        build_profile_artifacts(
            repo_root=repo_root,
            objective_path=objective,
            generated_root=generated_root,
        )
    assert target.read_bytes() == b"do-not-replace"


def test_refuses_generated_root_outside_repository(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    objective = repo_root / "objective.md"
    objective.write_text("# Objective\n", encoding="utf-8")
    generated_root = tmp_path / "outside"
    generated_root.mkdir()

    with pytest.raises(SelectionProfileError, match="inside the repository"):
        build_profile_artifacts(
            repo_root=repo_root,
            objective_path=objective,
            generated_root=generated_root,
        )


def test_refuses_objective_outside_repository(
    tmp_path: Path,
) -> None:
    repo_root, generated_root, _, _ = _artifact_layout(tmp_path)
    objective = tmp_path / "outside-objective.md"
    objective.write_text("# Outside\n", encoding="utf-8")

    with pytest.raises(SelectionProfileError, match="objective path"):
        build_profile_artifacts(
            repo_root=repo_root,
            objective_path=objective,
            generated_root=generated_root,
        )


def test_refuses_symlinked_launch_profile_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root, generated_root, source, objective = _artifact_layout(tmp_path)
    source.write_text('{"bundles":{}}\n', encoding="utf-8")
    outside = tmp_path / "outside-launch-profiles"
    outside.mkdir()
    (generated_root / "launch_profiles").symlink_to(
        outside,
        target_is_directory=True,
    )
    monkeypatch.setattr(profile_builder, "verify_generated_board", lambda **_: None)

    with pytest.raises(SelectionProfileError, match="cannot be a symlink"):
        build_profile_artifacts(
            repo_root=repo_root,
            objective_path=objective,
            generated_root=generated_root,
        )
