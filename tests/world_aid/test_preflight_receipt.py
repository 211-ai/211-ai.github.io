"""Offline contract tests for immutable World-aid preflight receipts."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from scripts.verify_world_aid_generated_board import (
    BLOCKED_REVIEW_CONTRACT,
    GATE0B_REOPENED_CONTRACT,
    BoardVerificationError,
)
from scripts.verify_world_aid_preflight_receipt import (
    PreflightReceiptError,
    build_preflight_receipt,
    verify_preflight_receipt,
    write_preflight_receipt,
)
from tests.world_aid.test_generated_board_verifier import _write_fixture

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPOSITORY_ROOT / "scripts/verify_world_aid_preflight_receipt.py"


def _prepare_fixture(
    tmp_path: Path,
    *,
    board_contract: str = BLOCKED_REVIEW_CONTRACT,
) -> tuple[Path, Path, Path, Path]:
    repo_root, objective_path, generated_root = _write_fixture(
        tmp_path,
        board_contract=board_contract,
    )
    scripts_dir = repo_root / "scripts"
    scripts_dir.mkdir()
    for name in (
        "verify_world_aid_generated_board.py",
        "verify_world_aid_preflight_receipt.py",
    ):
        (scripts_dir / name).write_bytes((REPOSITORY_ROOT / "scripts" / name).read_bytes())
    discovery_dir = generated_root / "discovery"
    discovery_dir.mkdir()
    (discovery_dir / "WORLDCOIN-AUTO-001.md").write_text(
        "Synthetic discovery evidence.\n",
        encoding="utf-8",
    )
    (generated_root / "plan_evaluations.json").write_text(
        '{"schema":"fixture-plan-evaluations"}\n',
        encoding="utf-8",
    )
    (generated_root / "objective_generation.json").write_text(
        '{"schema":"fixture-objective-generation"}\n',
        encoding="utf-8",
    )
    profile_dir = generated_root / "launch_profiles"
    profile_dir.mkdir()
    for name in (
        "g002-only.index.json",
        "gate0b-preparation.index.json",
        "g038-g040.index.json",
        "implementation.index.json",
    ):
        path = profile_dir / name
        path.write_text('{"schema":"fixture-launch-profile"}\n', encoding="utf-8")
        path.with_suffix(".duckdb").write_bytes(b"fixture-launch-profile-duckdb")
    receipt_path = generated_root / "preflight-receipt.json"
    return repo_root, objective_path, generated_root, receipt_path


def _file_snapshot(root: Path) -> dict[str, bytes]:
    return {path.relative_to(root).as_posix(): path.read_bytes() for path in root.rglob("*") if path.is_file()}


def test_create_and_verify_receipt_bind_every_planning_input_without_mutation(
    tmp_path: Path,
) -> None:
    repo_root, objective_path, generated_root, receipt_path = _prepare_fixture(tmp_path)
    before = _file_snapshot(generated_root)

    payload = write_preflight_receipt(
        repo_root=repo_root,
        objective_path=objective_path,
        generated_root=generated_root,
        receipt_path=receipt_path,
    )

    after = _file_snapshot(generated_root)
    assert {key: value for key, value in after.items() if key != receipt_path.name} == before
    assert set(payload) == {
        "artifacts",
        "generated_root",
        "objective_path",
        "no_start",
        "offline",
        "passed",
        "schema",
        "status",
        "summary",
        "verifiers",
    }
    assert payload["schema"] == "world_aid.generated_board_preflight_receipt@1"
    assert payload["status"] == "passed"
    assert payload["passed"] is True
    assert payload["offline"] is True
    assert payload["no_start"] is True
    assert payload["summary"]["source_goal_count"] == 42
    assert payload["summary"]["schedulable_goal_count"] == 37
    assert payload["summary"]["task_count"] == 40
    roles = [record["role"] for record in payload["artifacts"]]
    assert roles.count("bundle_shard") == 40
    assert roles.count("launch_profile_json") == 4
    assert roles.count("launch_profile_duckdb") == 4
    assert {
        "bundle_index_duckdb",
        "bundle_index_json",
        "discovery",
        "full_board",
        "objective_generation",
        "objective_graph",
        "plan_evaluations",
        "todo_vector_index",
    } <= set(roles)
    assert set(payload["verifiers"]) == {
        "generated_board",
        "preflight_receipt",
    }
    assert (
        verify_preflight_receipt(
            repo_root=repo_root,
            objective_path=objective_path,
            generated_root=generated_root,
            receipt_path=receipt_path,
        )
        == payload
    )


def test_reopened_gate0b_receipt_uses_v2_and_binds_board_contract(
    tmp_path: Path,
) -> None:
    repo_root, objective_path, generated_root, receipt_path = _prepare_fixture(
        tmp_path,
        board_contract=GATE0B_REOPENED_CONTRACT,
    )
    payload = write_preflight_receipt(
        repo_root=repo_root,
        objective_path=objective_path,
        generated_root=generated_root,
        receipt_path=receipt_path,
        board_contract=GATE0B_REOPENED_CONTRACT,
    )
    assert payload["schema"] == "world_aid.generated_board_preflight_receipt@2"
    assert payload["board_contract"] == GATE0B_REOPENED_CONTRACT
    assert payload["summary"]["source_goal_count"] == 42
    assert payload["summary"]["schedulable_goal_count"] == 40
    assert payload["summary"]["task_count"] == 40
    assert payload["summary"]["bundle_count"] == 40
    assert (
        verify_preflight_receipt(
            repo_root=repo_root,
            objective_path=objective_path,
            generated_root=generated_root,
            receipt_path=receipt_path,
            board_contract=GATE0B_REOPENED_CONTRACT,
        )
        == payload
    )
    with pytest.raises(BoardVerificationError, match="blocked-goal set differs"):
        verify_preflight_receipt(
            repo_root=repo_root,
            objective_path=objective_path,
            generated_root=generated_root,
            receipt_path=receipt_path,
        )


def test_receipt_creation_refuses_overwrite_and_verification_detects_drift(
    tmp_path: Path,
) -> None:
    repo_root, objective_path, generated_root, receipt_path = _prepare_fixture(tmp_path)
    write_preflight_receipt(
        repo_root=repo_root,
        objective_path=objective_path,
        generated_root=generated_root,
        receipt_path=receipt_path,
    )
    with pytest.raises(PreflightReceiptError, match="already exists"):
        write_preflight_receipt(
            repo_root=repo_root,
            objective_path=objective_path,
            generated_root=generated_root,
            receipt_path=receipt_path,
        )

    discovery_path = generated_root / "discovery/WORLDCOIN-AUTO-001.md"
    discovery_path.write_text("Drifted discovery evidence.\n", encoding="utf-8")
    with pytest.raises(PreflightReceiptError, match="differs from current immutable inputs"):
        verify_preflight_receipt(
            repo_root=repo_root,
            objective_path=objective_path,
            generated_root=generated_root,
            receipt_path=receipt_path,
        )


def test_build_receipt_is_read_only_and_rejects_noncanonical_roots(
    tmp_path: Path,
) -> None:
    repo_root, objective_path, generated_root, _ = _prepare_fixture(tmp_path)
    before = _file_snapshot(generated_root)
    payload = build_preflight_receipt(
        repo_root=repo_root,
        objective_path=objective_path,
        generated_root=generated_root,
    )
    assert payload["summary"]["status"] == "passed"
    assert _file_snapshot(generated_root) == before

    with pytest.raises(PreflightReceiptError, match="one direct review directory"):
        build_preflight_receipt(
            repo_root=repo_root,
            objective_path=objective_path,
            generated_root=repo_root / "generated",
        )


def test_receipt_rejects_missing_launch_profile_pair(
    tmp_path: Path,
) -> None:
    repo_root, objective_path, generated_root, _ = _prepare_fixture(tmp_path)
    (generated_root / "launch_profiles/g038-g040.index.duckdb").unlink()
    with pytest.raises(PreflightReceiptError, match="DuckDB set differs"):
        build_preflight_receipt(
            repo_root=repo_root,
            objective_path=objective_path,
            generated_root=generated_root,
        )


def test_receipt_rejects_orphan_launch_profile_pair(tmp_path: Path) -> None:
    repo_root, objective_path, generated_root, _ = _prepare_fixture(tmp_path)
    profile_dir = generated_root / "launch_profiles"
    (profile_dir / "unexpected.index.json").write_text(
        '{"schema":"unexpected"}\n',
        encoding="utf-8",
    )
    (profile_dir / "unexpected.index.duckdb").write_bytes(b"unexpected")

    with pytest.raises(PreflightReceiptError, match="JSON set differs"):
        build_preflight_receipt(
            repo_root=repo_root,
            objective_path=objective_path,
            generated_root=generated_root,
        )


def test_receipt_rejects_symlink_launch_profile_pair(tmp_path: Path) -> None:
    repo_root, objective_path, generated_root, _ = _prepare_fixture(tmp_path)
    profile_dir = generated_root / "launch_profiles"
    linked = profile_dir / "g002-only.index.json"
    linked.unlink()
    linked.symlink_to(profile_dir / "implementation.index.json")

    with pytest.raises(PreflightReceiptError, match="non-symlink"):
        build_preflight_receipt(
            repo_root=repo_root,
            objective_path=objective_path,
            generated_root=generated_root,
        )


def test_receipt_tool_has_no_network_or_subprocess_imports() -> None:
    tree = ast.parse(SCRIPT_PATH.read_text(encoding="utf-8"))
    imported_roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".", 1)[0])
    assert not imported_roots & {
        "aiohttp",
        "httpx",
        "requests",
        "socket",
        "subprocess",
        "urllib",
    }
