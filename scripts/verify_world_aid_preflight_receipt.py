#!/usr/bin/env python3
"""Create or verify a deterministic, offline World-aid preflight receipt.

The receipt content-binds every generated artifact that can direct or evidence
supervisor execution.  Creation writes only the new receipt and refuses to
replace an existing one.  Verification performs filesystem reads only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

if __package__:
    from scripts.verify_world_aid_generated_board import (
        BLOCKED_REVIEW_CONTRACT,
        GATE0B_REOPENED_CONTRACT,
        BoardVerificationError,
        VerificationSummary,
        verify_generated_board,
    )
else:
    from verify_world_aid_generated_board import (  # type: ignore[no-redef]
        BLOCKED_REVIEW_CONTRACT,
        GATE0B_REOPENED_CONTRACT,
        BoardVerificationError,
        VerificationSummary,
        verify_generated_board,
    )

SCHEMAS_BY_BOARD_CONTRACT = {
    BLOCKED_REVIEW_CONTRACT: "world_aid.generated_board_preflight_receipt@1",
    GATE0B_REOPENED_CONTRACT: "world_aid.generated_board_preflight_receipt@2",
}
RECEIPT_NAME = "preflight-receipt.json"
CANONICAL_OBJECTIVE_PATH = Path("docs/planning/WORLDCOIN_HUMAN_AID_OBJECTIVE_HEAP.md")
REGENERATION_PARENT = Path("data/worldcoin_human_aid/agent_supervisor/regenerations")
GENERATED_BOARD_VERIFIER = Path("scripts/verify_world_aid_generated_board.py")
PREFLIGHT_RECEIPT_VERIFIER = Path("scripts/verify_world_aid_preflight_receipt.py")
EXPECTED_LAUNCH_PROFILE_JSON = frozenset(
    {
        "g002-only.index.json",
        "gate0b-preparation.index.json",
        "g038-g040.index.json",
        "implementation.index.json",
    }
)


class PreflightReceiptError(ValueError):
    """Raised when a preflight receipt cannot be created or verified safely."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _repo_relative_file(repo_root: Path, path: Path, *, label: str) -> str:
    if path.is_symlink() or not path.is_file():
        raise PreflightReceiptError(f"{label} must be a regular, non-symlink file: {path}")
    try:
        return path.resolve().relative_to(repo_root).as_posix()
    except ValueError as exc:
        raise PreflightReceiptError(f"{label} escapes the repository: {path}") from exc


def _artifact_record(repo_root: Path, path: Path, *, role: str) -> dict[str, Any]:
    relative = _repo_relative_file(repo_root, path, label=role)
    return {
        "path": relative,
        "role": role,
        "sha256": _sha256(path),
        "size": path.stat().st_size,
    }


def _verifier_record(repo_root: Path, path: Path) -> dict[str, Any]:
    relative = _repo_relative_file(repo_root, path, label="preflight verifier")
    return {
        "path": relative,
        "sha256": _sha256(path),
        "size": path.stat().st_size,
    }


def _validated_paths(
    *,
    repo_root: Path,
    objective_path: Path,
    generated_root: Path,
) -> tuple[Path, Path]:
    root = repo_root.resolve()
    objective = objective_path if objective_path.is_absolute() else root / objective_path
    objective = objective.resolve()
    generated_input = generated_root if generated_root.is_absolute() else root / generated_root
    generated_is_symlink = generated_input.is_symlink()
    generated = generated_input.resolve()
    expected_objective = (root / CANONICAL_OBJECTIVE_PATH).resolve()
    expected_parent = (root / REGENERATION_PARENT).resolve()
    if objective != expected_objective:
        raise PreflightReceiptError(f"objective path must be {CANONICAL_OBJECTIVE_PATH.as_posix()}")
    if generated.parent != expected_parent:
        raise PreflightReceiptError(
            f"generated root must be one direct review directory below {REGENERATION_PARENT.as_posix()}"
        )
    if generated_is_symlink or not generated.is_dir():
        raise PreflightReceiptError(f"generated root must be a regular, non-symlink directory: {generated}")
    return objective, generated


def _generated_artifacts(
    *,
    repo_root: Path,
    generated_root: Path,
) -> list[dict[str, Any]]:
    fixed = {
        generated_root / "WORLDCOIN_HUMAN_AID_TODO.md": "full_board",
        generated_root / "objective_graph.json": "objective_graph",
        generated_root / "objective_bundles/index.json": "bundle_index_json",
        generated_root / "objective_bundles/index.duckdb": "bundle_index_duckdb",
        generated_root / "objective_bundles/todo_vector_index.json": "todo_vector_index",
        generated_root / "plan_evaluations.json": "plan_evaluations",
        generated_root / "objective_generation.json": "objective_generation",
    }
    optional = {
        generated_root / "analysis_escalation.json": "analysis_escalation",
    }
    selected: dict[Path, str] = {}
    for path, role in fixed.items():
        if not path.is_file() or path.is_symlink():
            raise PreflightReceiptError(f"missing required regular generated artifact {role}: {path}")
        selected[path.resolve()] = role
    for path, role in optional.items():
        if path.exists():
            if not path.is_file() or path.is_symlink():
                raise PreflightReceiptError(f"optional generated artifact is not a regular file: {path}")
            selected[path.resolve()] = role

    discovery_dir = generated_root / "discovery"
    if not discovery_dir.is_dir() or discovery_dir.is_symlink():
        raise PreflightReceiptError(f"missing regular discovery directory: {discovery_dir}")
    discovery_files = sorted(path for path in discovery_dir.rglob("*") if path.is_file())
    if not discovery_files:
        raise PreflightReceiptError("generated discovery directory contains no files")
    for path in discovery_files:
        if path.is_symlink():
            raise PreflightReceiptError(f"discovery artifact must not be a symlink: {path}")
        selected[path.resolve()] = "discovery"

    bundle_dir = generated_root / "objective_bundles"
    shard_files = sorted(bundle_dir.rglob("*.todo.md"))
    if not shard_files:
        raise PreflightReceiptError("generated objective bundle directory contains no shards")
    for path in shard_files:
        if not path.is_file() or path.is_symlink():
            raise PreflightReceiptError(f"bundle shard must be a regular file: {path}")
        selected[path.resolve()] = "bundle_shard"

    dataset_dir = generated_root / "objective_datasets"
    if dataset_dir.exists():
        if not dataset_dir.is_dir() or dataset_dir.is_symlink():
            raise PreflightReceiptError(f"objective dataset root must be a regular directory: {dataset_dir}")
        for path in sorted(dataset_dir.rglob("*.manifest.json")):
            if not path.is_file() or path.is_symlink():
                raise PreflightReceiptError(f"dataset manifest must be a regular file: {path}")
            selected[path.resolve()] = "dataset_manifest"

    profile_dir = generated_root / "launch_profiles"
    if not profile_dir.is_dir() or profile_dir.is_symlink():
        raise PreflightReceiptError(f"missing regular launch-profile directory: {profile_dir}")
    profile_json = {path.name: path for path in profile_dir.glob("*.json") if path.is_file() or path.is_symlink()}
    if set(profile_json) != EXPECTED_LAUNCH_PROFILE_JSON:
        raise PreflightReceiptError(
            "launch-profile JSON set differs from the reviewed stage contract: "
            f"missing={sorted(EXPECTED_LAUNCH_PROFILE_JSON - set(profile_json))}, "
            f"unexpected={sorted(set(profile_json) - EXPECTED_LAUNCH_PROFILE_JSON)}"
        )
    profile_duckdb = {path.name: path for path in profile_dir.glob("*.duckdb") if path.is_file() or path.is_symlink()}
    expected_duckdb_names = {Path(name).with_suffix(".duckdb").name for name in EXPECTED_LAUNCH_PROFILE_JSON}
    if set(profile_duckdb) != expected_duckdb_names:
        raise PreflightReceiptError(
            "launch-profile DuckDB set differs from the reviewed paired contract: "
            f"missing={sorted(expected_duckdb_names - set(profile_duckdb))}, "
            f"orphan={sorted(set(profile_duckdb) - expected_duckdb_names)}"
        )
    for path in [*profile_json.values(), *profile_duckdb.values()]:
        if not path.is_file() or path.is_symlink():
            raise PreflightReceiptError(f"launch profile must be a regular, non-symlink file: {path}")
        role = "launch_profile_json" if path.suffix == ".json" else "launch_profile_duckdb"
        selected[path.resolve()] = role

    return [
        _artifact_record(repo_root, path, role=selected[path])
        for path in sorted(selected, key=lambda item: item.relative_to(repo_root).as_posix())
    ]


def build_preflight_receipt(
    *,
    repo_root: Path,
    objective_path: Path,
    generated_root: Path,
    board_contract: str = BLOCKED_REVIEW_CONTRACT,
) -> dict[str, Any]:
    """Build the canonical receipt in memory without writing any file."""

    root = repo_root.resolve()
    objective, generated = _validated_paths(
        repo_root=root,
        objective_path=objective_path,
        generated_root=generated_root,
    )
    summary: VerificationSummary = verify_generated_board(
        repo_root=root,
        objective_path=objective,
        generated_root=generated,
        board_contract=board_contract,
    )
    try:
        schema = SCHEMAS_BY_BOARD_CONTRACT[board_contract]
    except KeyError as exc:
        raise PreflightReceiptError(
            f"unsupported board contract {board_contract!r}"
        ) from exc
    if board_contract == GATE0B_REOPENED_CONTRACT:
        expected_counts = {
            "source_goal_count": 42,
            "schedulable_goal_count": 40,
            "task_count": 40,
            "bundle_count": 40,
        }
        observed_counts = {
            key: getattr(summary, key)
            for key in expected_counts
        }
        if observed_counts != expected_counts:
            raise PreflightReceiptError(
                "reopened Gate 0B board counts differ from the exact "
                f"selection contract: {observed_counts!r}"
            )
    payload = {
        "schema": schema,
        "status": "passed",
        "passed": True,
        "offline": True,
        "no_start": True,
        "generated_root": generated.relative_to(root).as_posix(),
        "objective_path": objective.relative_to(root).as_posix(),
        "summary": summary.to_dict(),
        "verifiers": {
            "generated_board": _verifier_record(root, root / GENERATED_BOARD_VERIFIER),
            "preflight_receipt": _verifier_record(root, root / PREFLIGHT_RECEIPT_VERIFIER),
        },
        "artifacts": _generated_artifacts(
            repo_root=root,
            generated_root=generated,
        ),
    }
    if board_contract == GATE0B_REOPENED_CONTRACT:
        payload["board_contract"] = board_contract
    return payload


def _canonical_bytes(payload: Mapping[str, Any]) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def write_preflight_receipt(
    *,
    repo_root: Path,
    objective_path: Path,
    generated_root: Path,
    receipt_path: Path,
    board_contract: str = BLOCKED_REVIEW_CONTRACT,
) -> dict[str, Any]:
    """Create a receipt exactly once without replacing any existing path."""

    root = repo_root.resolve()
    _, generated = _validated_paths(
        repo_root=root,
        objective_path=objective_path,
        generated_root=generated_root,
    )
    expected_receipt = generated / RECEIPT_NAME
    supplied_receipt = (receipt_path if receipt_path.is_absolute() else root / receipt_path).absolute()
    if supplied_receipt != expected_receipt.absolute():
        raise PreflightReceiptError(f"receipt path must be {expected_receipt.relative_to(root).as_posix()}")
    payload = build_preflight_receipt(
        repo_root=root,
        objective_path=objective_path,
        generated_root=generated,
        board_contract=board_contract,
    )
    temporary = generated / f".{RECEIPT_NAME}.{os.getpid()}.tmp"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor: int | None = None
    try:
        descriptor = os.open(temporary, flags, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = None
            handle.write(_canonical_bytes(payload))
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, expected_receipt)
    except FileExistsError as exc:
        raise PreflightReceiptError(
            f"receipt already exists; use a fresh regeneration root: {expected_receipt}"
        ) from exc
    except OSError as exc:
        raise PreflightReceiptError(f"cannot create preflight receipt {expected_receipt}: {exc}") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
    return payload


def verify_preflight_receipt(
    *,
    repo_root: Path,
    objective_path: Path,
    generated_root: Path,
    receipt_path: Path,
    board_contract: str = BLOCKED_REVIEW_CONTRACT,
) -> dict[str, Any]:
    """Recompute and compare a receipt without writing to the generated root."""

    root = repo_root.resolve()
    _, generated = _validated_paths(
        repo_root=root,
        objective_path=objective_path,
        generated_root=generated_root,
    )
    expected_path = generated / RECEIPT_NAME
    supplied = receipt_path if receipt_path.is_absolute() else root / receipt_path
    if supplied.resolve() != expected_path.resolve():
        raise PreflightReceiptError(f"receipt path must be {expected_path.relative_to(root).as_posix()}")
    if supplied.is_symlink() or not supplied.is_file():
        raise PreflightReceiptError(f"receipt must be a regular, non-symlink file: {supplied}")
    try:
        observed = json.loads(supplied.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PreflightReceiptError(f"cannot read preflight receipt: {exc}") from exc
    if not isinstance(observed, dict):
        raise PreflightReceiptError("preflight receipt must contain a JSON object")
    expected = build_preflight_receipt(
        repo_root=root,
        objective_path=objective_path,
        generated_root=generated,
        board_contract=board_contract,
    )
    if observed != expected:
        observed_records = {
            str(item.get("path")): item for item in observed.get("artifacts", []) if isinstance(item, Mapping)
        }
        expected_records = {str(item.get("path")): item for item in expected["artifacts"] if isinstance(item, Mapping)}
        changed = sorted(
            path
            for path in set(observed_records) | set(expected_records)
            if observed_records.get(path) != expected_records.get(path)
        )
        raise PreflightReceiptError(
            "preflight receipt differs from current immutable inputs" + (f": {changed}" if changed else "")
        )
    return expected


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--create", action="store_true")
    action.add_argument("--verify", action="store_true")
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--objective-path", type=Path, required=True)
    parser.add_argument("--generated-root", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument(
        "--board-contract",
        choices=tuple(sorted(SCHEMAS_BY_BOARD_CONTRACT)),
        default=BLOCKED_REVIEW_CONTRACT,
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.create:
            payload = write_preflight_receipt(
                repo_root=args.repo_root,
                objective_path=args.objective_path,
                generated_root=args.generated_root,
                receipt_path=args.receipt,
                board_contract=args.board_contract,
            )
            action = "created"
        else:
            payload = verify_preflight_receipt(
                repo_root=args.repo_root,
                objective_path=args.objective_path,
                generated_root=args.generated_root,
                receipt_path=args.receipt,
                board_contract=args.board_contract,
            )
            action = "verified"
    except (BoardVerificationError, OSError, PreflightReceiptError) as exc:
        print(f"World-aid preflight receipt FAILED: {exc}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "action": action,
                "artifact_count": len(payload["artifacts"]),
                "receipt": str(args.receipt),
                "schema": payload["schema"],
                "status": "passed",
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
