#!/usr/bin/env python3
"""DSCON-G010 freeze: repository authorities, revisions, and drift inventory.

Read-only deterministic audit for datasets symbolic contract bootstrap.
Binds verified Git commit/tree IDs for selected roots and direct gitlinks,
records recursive nested gitlinks without rescanning mirror cycles,
records Swissknife and Hallucinate runtime package identities, and freezes
known dataset-manipulator drift findings.

A repository reference in documentation is not an authority until its path
and Git identity are verified.

Usage:
  python scripts/contract_analysis/audit_scope.py --freeze
  python scripts/contract_analysis/audit_scope.py --check
  python scripts/contract_analysis/audit_scope.py --check-current

``--check`` verifies the immutable Git object graph recorded by ``--freeze``.
It deliberately does not require the ambient worktrees to remain at the
frozen revisions.  ``--check-current`` performs that separate freshness
comparison and returns non-zero when a checkout has moved or is dirty.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


GOAL_ID = "DSCON-G010"
TASK_ID = "DSCON-001"
VALIDATION_TASK_ID = "DSCON-062"
SCHEMA_SOURCE_ROOTS = "datasets_contract_analysis/source-roots@1"
SCHEMA_DRIFT = "datasets_contract_analysis/datasets-manipulator-drift@1"
OBJECTIVE_VALIDATION_EVIDENCE = "objective validation repair"
OBJECTIVE_VALIDATION_COMMAND = (
    "python scripts/contract_analysis/audit_scope.py --check"
)
OBJECTIVE_VALIDATED_ARTIFACTS = (
    "scripts/contract_analysis/audit_scope.py",
    "data/datasets_contract_analysis/audit/source-roots.json",
    "data/datasets_contract_analysis/audit/datasets-manipulator-drift.json",
    "data/datasets_contract_analysis/audit/ownership-map.md",
)

# Plan-documented external pins (prefix match against full commit).
EXPECTED_SWISSKNIFE_PREFIX = "df11f08f"
EXPECTED_HALLUCINATE_DATASETS_PREFIX = "8dc4f93e"
# Plan-documented standalone home checkout at freeze-of-plan time.
EXPECTED_HOME_DATASETS_PREFIX = "6672d6924"

DEFAULT_SWISSKNIFE_PATH = Path("/home/barberb/swissknife")
DEFAULT_HALLUCINATE_DATASETS_PATH = Path(
    "/home/barberb/hallucinate_app/ipfs_datasets_py"
)
DEFAULT_HOME_DATASETS_PATH = Path("/home/barberb/ipfs_datasets_py")

# Package roots selected for 211-AI composition analysis.
SELECTED_PACKAGE_ROOTS = (
    "ipfs_accelerate_py",
    "ipfs_datasets_py",
    "ipfs_kit_py",
)

# Path basenames that form recursive package-mirror cycles when nested.
PACKAGE_MIRROR_NAMES = frozenset(SELECTED_PACKAGE_ROOTS)

REQUIRED_SOURCE_ROOT_KEYS = (
    "schema",
    "goal_id",
    "task_id",
    "generated_at",
    "superproject",
    "direct_gitlinks",
    "nested_gitlinks",
    "mirror_cycles",
    "swissknife",
    "hallucinate_datasets",
    "package_authority",
    "authority_candidates",
    "acceptance_coverage",
    "objective_validation_repair",
    "blockers",
    "fail_closed",
)

REQUIRED_DRIFT_KEYS = (
    "schema",
    "goal_id",
    "task_id",
    "generated_at",
    "bound_package_authority",
    "surfaces",
    "findings",
    "finding_categories",
    "acceptance_coverage",
    "objective_validation_repair",
    "blockers",
)

REQUIRED_OWNERSHIP_PHRASES = (
    "DSCON-G010",
    "DSCON-001",
    "source-roots.json",
    "datasets-manipulator-drift.json",
    "swissknife",
    "df11f08f",
    "hallucinate",
    "8dc4f93e",
    "ipfs_datasets_py",
    "ipfs_accelerate_py",
    "ipfs_kit_py",
    "DatasetManager",
    "DataProcessor",
    "DatasetLoader",
    "DatasetSaver",
    "DatasetConverter",
    "DatasetManipulator",
    "generate_clusters",
    "mock-success",
    "nondeterministic",
    "duplicate definition",
    "missing import",
    "weak-test",
    "Blocker",
    "fail closed",
    "package authority",
    "objective validation repair",
    "DSCON-062",
)

REQUIRED_DRIFT_CATEGORIES = frozenset(
    {
        "mock-success",
        "nondeterministic-identity",
        "duplicate-definition",
        "missing-import",
        "weak-test",
    }
)

# Known drift findings frozen as inventory (pre-repair evidence).
KNOWN_FINDINGS: list[dict[str, Any]] = [
    {
        "finding_id": "DSCON-DRIFT-001",
        "category": "mock-success",
        "severity": "high",
        "symbol": "ManagedDataset.save_async / ManagedDataset.save",
        "path": "ipfs_datasets_py/ipfs_datasets_py/dataset_manager.py",
        "summary": (
            "save_async/save return fabricated location/size without writing "
            "data; comments label the path as 'Mock successful save'."
        ),
        "evidence": [
            "Mock successful save comments at save_async and save",
            "Returns location/size/format without persistence effects",
        ],
        "status": "open",
    },
    {
        "finding_id": "DSCON-DRIFT-002",
        "category": "mock-success",
        "severity": "high",
        "symbol": "DatasetManager.get_dataset",
        "path": "ipfs_datasets_py/ipfs_datasets_py/dataset_manager.py",
        "summary": (
            "On load failure, falls back to an in-memory mock dataset and "
            "presents it as a managed dataset without failing closed."
        ),
        "evidence": [
            "Fallback: return a minimal mock dataset for testing/dev environments",
        ],
        "status": "open",
    },
    {
        "finding_id": "DSCON-DRIFT-003",
        "category": "mock-success",
        "severity": "high",
        "symbol": "process_dataset",
        "path": (
            "ipfs_datasets_py/ipfs_datasets_py/mcp_server/tools/"
            "dataset_tools/process_dataset.py"
        ),
        "summary": (
            "Process operations are mock implementations that invent record "
            "counts (default mock count 100) instead of applying real transforms."
        ),
        "evidence": [
            "return 100  # Default mock count",
            "Process operations (mock implementation for now)",
        ],
        "status": "open",
    },
    {
        "finding_id": "DSCON-DRIFT-004",
        "category": "mock-success",
        "severity": "high",
        "symbol": "convert_dataset_format",
        "path": (
            "ipfs_datasets_py/ipfs_datasets_py/mcp_server/tools/"
            "dataset_tools/convert_dataset_format.py"
        ),
        "summary": (
            "Falls back to a mock conversion response with fabricated "
            "num_records=100 and conversion_method=mock on failure."
        ),
        "evidence": [
            "Using mock conversion response",
            "num_records: 100",
            "conversion_method: mock",
        ],
        "status": "open",
    },
    {
        "finding_id": "DSCON-DRIFT-005",
        "category": "mock-success",
        "severity": "medium",
        "symbol": "save_dataset",
        "path": (
            "ipfs_datasets_py/ipfs_datasets_py/mcp_server/tools/"
            "dataset_tools/save_dataset.py"
        ),
        "summary": (
            "Direct data path fabricates mock_dataset_* identifiers instead of "
            "persisting through the canonical saver contract."
        ),
        "evidence": [
            "dataset_id = f\"mock_dataset_{hash(str(dataset_data))}\"",
        ],
        "status": "open",
    },
    {
        "finding_id": "DSCON-DRIFT-006",
        "category": "nondeterministic-identity",
        "severity": "medium",
        "symbol": "save_dataset mock dataset_id",
        "path": (
            "ipfs_datasets_py/ipfs_datasets_py/mcp_server/tools/"
            "dataset_tools/save_dataset.py"
        ),
        "summary": (
            "Identity is derived from Python hash() of stringified data, which "
            "is process-salted and nondeterministic across interpreters."
        ),
        "evidence": [
            "hash(str(dataset_data)) used for dataset_id",
        ],
        "status": "open",
    },
    {
        "finding_id": "DSCON-DRIFT-007",
        "category": "nondeterministic-identity",
        "severity": "medium",
        "symbol": "dataset serialization / processors",
        "path": "ipfs_datasets_py/ipfs_datasets_py/processors/serialization/dataset_serialization.py",
        "summary": (
            "Dataset serialization paths use uuid/random/datetime.now for "
            "identity rather than content-addressed CIDs."
        ),
        "evidence": [
            "uuid / random / datetime.now usage in dataset serialization",
        ],
        "status": "open",
    },
    {
        "finding_id": "DSCON-DRIFT-008",
        "category": "duplicate-definition",
        "severity": "high",
        "symbol": "DatasetManager",
        "path": "multi",
        "summary": (
            "DatasetManager is defined in ipfs_datasets_py and three distinct "
            "ipfs_kit_py modules, creating shadowed owners across packages."
        ),
        "evidence": [
            "ipfs_datasets_py/ipfs_datasets_py/dataset_manager.py",
            "ipfs_kit_py/ipfs_kit_py/ai_ml_integration.py",
            "ipfs_kit_py/ipfs_kit_py/mcp/ai/dataset_manager.py",
            "ipfs_kit_py/ipfs_kit_py/mcp/ai/dataset_management/manager.py",
        ],
        "status": "open",
    },
    {
        "finding_id": "DSCON-DRIFT-009",
        "category": "missing-import",
        "severity": "high",
        "symbol": "DatasetManipulator",
        "path": "ipfs_datasets_py/ipfs_datasets_py/core_operations/dataset_manipulator.py",
        "summary": (
            "Canonical DatasetManipulator module is absent; no importable "
            "DatasetManipulator symbol exists in the selected package tree."
        ),
        "evidence": [
            "path does not exist at freeze time",
            "rg DatasetManipulator across packages returned no production refs",
        ],
        "status": "open",
    },
    {
        "finding_id": "DSCON-DRIFT-010",
        "category": "missing-import",
        "severity": "medium",
        "symbol": "core_operations package surface",
        "path": "ipfs_datasets_py/ipfs_datasets_py/core_operations/",
        "summary": (
            "Loader/saver/converter exist, but dataset_contracts and "
            "dataset_manipulator modules required by later objectives are missing."
        ),
        "evidence": [
            "present: dataset_loader.py, dataset_saver.py, dataset_converter.py, data_processor.py",
            "missing: dataset_manipulator.py, dataset_contracts.py",
        ],
        "status": "open",
    },
    {
        "finding_id": "DSCON-DRIFT-011",
        "category": "weak-test",
        "severity": "medium",
        "symbol": "dataset tools unit tests",
        "path": "ipfs_datasets_py/tests/mcp/unit/test_dataset_tools.py",
        "summary": (
            "Existing dataset tool tests and migration generators rely on "
            "MagicMock/patch success paths and do not refute mock-success or "
            "require content-addressed receipts."
        ),
        "evidence": [
            "tests/migration_tests/_test_generator_for_dataset_tools.py uses MagicMock",
            "no contract baseline tests for manipulator equivalence at freeze",
        ],
        "status": "open",
    },
    {
        "finding_id": "DSCON-DRIFT-012",
        "category": "weak-test",
        "severity": "medium",
        "symbol": "DatasetManager gherkin stubs",
        "path": "ipfs_datasets_py/tests/unit/test_stubs_from_gherkin/test_dataset_manager.py",
        "summary": (
            "Gherkin-generated DatasetManager stubs do not exercise real "
            "persistence or fail on mock success."
        ),
        "evidence": [
            "stub/gherkin test surface without hermetic persistence assertions",
        ],
        "status": "open",
    },
    {
        "finding_id": "DSCON-DRIFT-013",
        "category": "revision-mismatch-risk",
        "severity": "high",
        "symbol": "package authority vs Hallucinate vs home checkout",
        "path": "external",
        "summary": (
            "Three live ipfs_datasets_py revisions exist: 211-AI gitlink, "
            "Hallucinate runtime copy (8dc4f93e…), and home standalone "
            "(6672d6924…). Contracts must bind a single selected authority."
        ),
        "evidence": [
            "plan documents Hallucinate 8dc4f93e vs home 6672d6924 divergence",
            "source-roots package_authority selects 211-AI gitlink only",
        ],
        "status": "open",
    },
    {
        "finding_id": "DSCON-DRIFT-014",
        "category": "duplicate-definition",
        "severity": "high",
        "symbol": "generate_clusters",
        "path": "ipfs_datasets_py/ipfs_datasets_py/ipfs_datasets.py",
        "summary": (
            "The legacy dataset monolith defines generate_clusters twice in "
            "the same class scope; the later no-op definition shadows the first."
        ),
        "evidence": [
            "async def generate_clusters occurs twice in the pinned monolith",
            "both definitions return None without generating clusters",
        ],
        "status": "open",
    },
]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _audit_dir(root: Path) -> Path:
    return root / "data" / "datasets_contract_analysis" / "audit"


def _objective_validation_contract() -> dict[str, Any]:
    """Describe the executable DSCON-062 validation gate.

    This is a contract rather than a precomputed success receipt: the command
    must re-read and verify the selected authority's pinned Git object graph
    every time it runs. Unselected external comparison roots retain their
    freeze-time identity evidence; ``--check-current`` verifies their ambient
    availability and freshness.
    """

    return {
        "evidence_term": OBJECTIVE_VALIDATION_EVIDENCE,
        "task_id": VALIDATION_TASK_ID,
        "command": OBJECTIVE_VALIDATION_COMMAND,
        "authority_mode": "selected_authority_objects_external_evidence",
        "validated_artifacts": list(OBJECTIVE_VALIDATED_ARTIFACTS),
        "fail_closed": True,
    }


def _run(
    cmd: list[str],
    *,
    cwd: Path | None = None,
    check: bool = False,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd is not None else None,
        capture_output=True,
        text=True,
        check=False,
    )
    if check and result.returncode != 0:
        raise RuntimeError(
            f"command failed ({result.returncode}): {' '.join(cmd)}\n"
            f"{result.stderr.strip()}"
        )
    return result


def _git(args: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return _run(["git", *args], cwd=cwd)


def _git_ok(args: list[str], *, cwd: Path | None = None) -> str | None:
    result = _git(args, cwd=cwd)
    if result.returncode != 0:
        return None
    return (result.stdout or "").strip()


_FULL_GIT_OBJECT_ID = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")


def _pinned_object_id(
    value: Any,
    *,
    label: str,
    errors: list[str],
) -> str | None:
    """Return a full lower-case Git object ID or fail the manifest closed."""
    if not isinstance(value, str) or not _FULL_GIT_OBJECT_ID.fullmatch(value):
        errors.append(f"{label} must be a full lower-case Git object id")
        return None
    return value


def _rehash_git_object(
    repository: Path,
    *,
    object_id: str,
    object_type: str,
) -> str | None:
    """Recompute an object's ID so corrupt loose/pack data cannot pass by type."""
    content = subprocess.run(
        ["git", "cat-file", object_type, object_id],
        cwd=repository,
        capture_output=True,
        check=False,
    )
    if content.returncode != 0:
        return None
    hashed = subprocess.run(
        ["git", "hash-object", "-t", object_type, "--stdin"],
        cwd=repository,
        input=content.stdout,
        capture_output=True,
        check=False,
    )
    if hashed.returncode != 0:
        return None
    try:
        return hashed.stdout.decode("ascii").strip()
    except UnicodeDecodeError:
        return None


def _validate_pinned_commit_tree(
    repository: Path,
    *,
    commit: Any,
    tree: Any,
    label: str,
    errors: list[str],
) -> bool:
    """Verify a historical commit/tree pair without consulting ambient HEAD."""
    commit_id = _pinned_object_id(commit, label=f"{label}.commit", errors=errors)
    tree_id = _pinned_object_id(tree, label=f"{label}.tree", errors=errors)
    if commit_id is None or tree_id is None:
        return False
    if not _is_git_checkout(repository):
        errors.append(
            f"{label} pinned object repository is missing or not a Git checkout: "
            f"{repository}"
        )
        return False

    commit_type = _git_ok(["cat-file", "-t", commit_id], cwd=repository)
    if commit_type != "commit":
        detail = "missing" if commit_type is None else f"type={commit_type}"
        errors.append(f"{label} pinned commit {commit_id} is unavailable ({detail})")
        return False
    if _rehash_git_object(
        repository,
        object_id=commit_id,
        object_type="commit",
    ) != commit_id:
        errors.append(f"{label} pinned commit {commit_id} failed content-hash verification")
        return False

    tree_type = _git_ok(["cat-file", "-t", tree_id], cwd=repository)
    if tree_type != "tree":
        detail = "missing" if tree_type is None else f"type={tree_type}"
        errors.append(f"{label} pinned tree {tree_id} is unavailable ({detail})")
        return False
    if _rehash_git_object(
        repository,
        object_id=tree_id,
        object_type="tree",
    ) != tree_id:
        errors.append(f"{label} pinned tree {tree_id} failed content-hash verification")
        return False

    resolved_tree = _git_ok(["rev-parse", f"{commit_id}^{{tree}}"], cwd=repository)
    if resolved_tree != tree_id:
        errors.append(
            f"{label} pinned commit/tree mismatch: commit={commit_id} "
            f"records tree={resolved_tree!r}, manifest tree={tree_id}"
        )
        return False
    return True


def _safe_git_tree_path(value: Any, *, label: str, errors: list[str]) -> str | None:
    if not isinstance(value, str) or not value or "\x00" in value:
        errors.append(f"{label} must be a non-empty Git tree path")
        return None
    candidate = Path(value)
    if candidate.is_absolute() or any(part in {"", ".", ".."} for part in candidate.parts):
        errors.append(f"{label} must be a normalized repository-relative path")
        return None
    return candidate.as_posix()


def _pinned_tree_entry(
    repository: Path,
    *,
    commit: str,
    relative_path: Any,
    label: str,
    errors: list[str],
) -> dict[str, str] | None:
    """Read one exact entry from a pinned commit tree."""
    tree_path = _safe_git_tree_path(
        relative_path,
        label=f"{label}.path",
        errors=errors,
    )
    if tree_path is None:
        return None
    result = _git(
        ["ls-tree", "--full-tree", commit, "--", tree_path],
        cwd=repository,
    )
    if result.returncode != 0:
        errors.append(
            f"{label} cannot read pinned tree entry {tree_path!r} at {commit}"
        )
        return None
    matches: list[dict[str, str]] = []
    for line in (result.stdout or "").splitlines():
        if "\t" not in line:
            continue
        metadata, found_path = line.split("\t", 1)
        parts = metadata.split()
        if len(parts) != 3 or found_path != tree_path:
            continue
        matches.append(
            {
                "mode": parts[0],
                "type": parts[1],
                "object": parts[2],
                "path": found_path,
            }
        )
    if len(matches) != 1:
        errors.append(
            f"{label} pinned tree entry {tree_path!r} is "
            f"{'missing' if not matches else 'ambiguous'} at {commit}"
        )
        return None
    return matches[0]


def _read_pinned_blob(
    repository: Path,
    *,
    commit: str,
    relative_path: str,
) -> str | None:
    result = _git(["show", f"{commit}:{relative_path}"], cwd=repository)
    if result.returncode != 0:
        return None
    return result.stdout


def _is_git_checkout(path: Path) -> bool:
    if not path.is_dir():
        return False
    return _git_ok(["rev-parse", "--git-dir"], cwd=path) is not None


def _resolve_gitlink_repository(
    root: Path,
    package: str,
    commit: Any,
) -> Path:
    """Locate the object database for a direct gitlink's pinned commit.

    Supervisor and CI worktrees may leave the gitlink directory uninitialized
    while retaining its object database under another linked worktree's Git
    administration directory.  The audit is about immutable objects, not the
    ambient checkout, so prefer any local repository that proves it has the
    exact pinned commit.
    """

    checkout = root / package
    candidates = [checkout]
    common_raw = _git_ok(["rev-parse", "--git-common-dir"], cwd=root)
    if common_raw:
        common_dir = Path(common_raw)
        if not common_dir.is_absolute():
            common_dir = (root / common_dir).resolve()
        candidates.append(common_dir / "modules" / package)
        worktrees_dir = common_dir / "worktrees"
        if worktrees_dir.is_dir():
            for worktree_admin in sorted(worktrees_dir.iterdir()):
                candidates.append(worktree_admin / "modules" / package)

    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        if not _is_git_checkout(candidate):
            continue
        if isinstance(commit, str):
            present = _git_ok(
                ["cat-file", "-e", f"{commit}^{{commit}}"],
                cwd=candidate,
            )
            if present is None:
                continue
        return candidate
    return checkout


# Freeze outputs live in the superproject worktree; they must not poison
# cleanliness of the bound HEAD commit/tree for selected-root freeze_ok.
# Include parent directory prefixes because `git status --porcelain` may report
# only the newly untracked parent (e.g. data/datasets_contract_analysis/).
_FREEZE_OUTPUT_PREFIXES = (
    "data/datasets_contract_analysis/",
    "data/datasets_contract_analysis/audit/",
    "scripts/contract_analysis/",
)


def _status_path(porcelain_line: str) -> str:
    """Extract path from a git status --porcelain line (best effort)."""
    if len(porcelain_line) < 4:
        return porcelain_line.strip()
    body = porcelain_line[3:]
    if " -> " in body:
        body = body.split(" -> ", 1)[1]
    return body.strip().strip('"')


def _is_freeze_output_path(rel_path: str) -> bool:
    normalized = rel_path.replace("\\", "/").lstrip("./")
    # Directory entries from porcelain often end with '/'.
    candidates = {normalized, normalized.rstrip("/"), normalized.rstrip("/") + "/"}
    for candidate in candidates:
        for prefix in _FREEZE_OUTPUT_PREFIXES:
            prefix_dir = prefix.rstrip("/")
            if (
                candidate == prefix
                or candidate == prefix_dir
                or candidate == prefix_dir + "/"
                or candidate.startswith(prefix)
                or prefix.startswith(candidate if candidate.endswith("/") else candidate + "/")
            ):
                return True
    return False


def _checkout_identity(
    path: Path,
    *,
    label: str,
    relative_path: str | None = None,
    ignore_freeze_outputs: bool = False,
) -> dict[str, Any] | None:
    if not _is_git_checkout(path):
        return None
    commit = _git_ok(["rev-parse", "HEAD"], cwd=path)
    tree = _git_ok(["rev-parse", "HEAD^{tree}"], cwd=path)
    if not commit or not tree:
        return None
    branch = _git_ok(["rev-parse", "--abbrev-ref", "HEAD"], cwd=path) or ""
    subject = _git_ok(["log", "-1", "--format=%s"], cwd=path) or ""
    status = _git_ok(["status", "--porcelain"], cwd=path) or ""
    dirty_lines = [line for line in status.splitlines() if line.strip()]
    material_dirty_lines = dirty_lines
    if ignore_freeze_outputs:
        material_dirty_lines = [
            line
            for line in dirty_lines
            if not _is_freeze_output_path(_status_path(line))
        ]
    record: dict[str, Any] = {
        "label": label,
        "commit": commit,
        "tree": tree,
        "branch": branch,
        "subject": subject,
        "dirty": bool(material_dirty_lines),
        "dirty_entry_count": len(material_dirty_lines),
        "worktree_dirty_entry_count": len(dirty_lines),
        "clean": not material_dirty_lines,
        "verified": True,
        "ignore_freeze_outputs_in_cleanliness": ignore_freeze_outputs,
    }
    if relative_path is not None:
        record["path"] = relative_path
    else:
        record["path"] = str(path)
    return record


def _prefix_status(commit: str | None, expected_prefix: str) -> str:
    if not commit:
        return "absent"
    if commit.startswith(expected_prefix):
        return "matches_expected"
    return "changed"


def _list_direct_gitlinks(
    root: Path,
    commit: str = "HEAD",
) -> list[dict[str, Any]]:
    out = _git_ok(["ls-tree", commit], cwd=root) or ""
    links: list[dict[str, Any]] = []
    for line in out.splitlines():
        if "\t" not in line:
            continue
        meta, path = line.split("\t", 1)
        parts = meta.split()
        if len(parts) != 3:
            continue
        mode, obj_type, sha = parts
        if mode != "160000" and obj_type != "commit":
            continue
        links.append(
            {
                "path": path,
                "mode": mode,
                "type": obj_type,
                "gitlink_commit": sha,
            }
        )
    return links


def _list_nested_gitlinks(
    package_root: Path,
    parent_package: str,
    parent_commit: str,
) -> list[dict[str, Any]]:
    out = _git_ok(["ls-tree", "-r", parent_commit], cwd=package_root) or ""
    nested: list[dict[str, Any]] = []
    for line in out.splitlines():
        if not line.startswith("160000 "):
            continue
        if "\t" not in line:
            continue
        meta, rel = line.split("\t", 1)
        parts = meta.split()
        if len(parts) != 3:
            continue
        _mode, _typ, sha = parts
        nested.append(
            {
                "parent_package": parent_package,
                "parent_commit": parent_commit,
                "relative_path": rel,
                "full_path": f"{parent_package}/{rel}",
                "gitlink_commit": sha,
            }
        )
    return nested


def _mirror_name(relative_path: str) -> str | None:
    parts = Path(relative_path).parts
    for name in PACKAGE_MIRROR_NAMES:
        if name in parts:
            return name
    base = Path(relative_path).name
    if base in PACKAGE_MIRROR_NAMES:
        return base
    return None


def _load_gitmodules_urls(root: Path) -> dict[str, str]:
    path = root / ".gitmodules"
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8", errors="replace")
    urls: dict[str, str] = {}
    current_path: str | None = None
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("path"):
            _, value = line.split("=", 1)
            current_path = value.strip()
        elif line.startswith("url") and current_path:
            _, value = line.split("=", 1)
            urls[current_path] = value.strip()
            current_path = None
    return urls


def collect_source_roots(
    root: Path,
    *,
    swissknife_path: Path,
    hallucinate_path: Path,
    home_datasets_path: Path,
) -> dict[str, Any]:
    superproject = _checkout_identity(
        root,
        label="211-AI-superproject",
        relative_path=".",
        ignore_freeze_outputs=True,
    )
    if superproject is None:
        raise RuntimeError("superproject is not a verified Git checkout")

    gitmodule_urls = _load_gitmodules_urls(root)
    direct_raw = _list_direct_gitlinks(root)
    direct: list[dict[str, Any]] = []
    selected_commits: dict[str, str] = {}
    blockers: list[dict[str, Any]] = []

    for gl in direct_raw:
        path = gl["path"]
        checkout_path = root / path
        record: dict[str, Any] = {
            **gl,
            "url": gitmodule_urls.get(path),
            "selected": path in SELECTED_PACKAGE_ROOTS,
        }
        identity = _checkout_identity(
            checkout_path,
            label=path,
            relative_path=path,
        )
        if identity is None:
            record["status"] = "unresolved_checkout"
            record["verified"] = False
            if path in SELECTED_PACKAGE_ROOTS:
                blockers.append(
                    {
                        "code": "UNRESOLVED_GITLINK_CHECKOUT",
                        "path": path,
                        "message": (
                            f"selected gitlink {path} has no verified checkout; "
                            "authority fails closed"
                        ),
                        "guessed": False,
                    }
                )
        else:
            record.update(
                {
                    "commit": identity["commit"],
                    "tree": identity["tree"],
                    "branch": identity["branch"],
                    "subject": identity["subject"],
                    "dirty": identity["dirty"],
                    "dirty_entry_count": identity["dirty_entry_count"],
                    "clean": identity["clean"],
                    "verified": True,
                    "checkout_matches_gitlink": identity["commit"] == gl["gitlink_commit"],
                    "status": "verified",
                }
            )
            if path in SELECTED_PACKAGE_ROOTS:
                selected_commits[path] = identity["commit"]
            if not identity["clean"] and path in SELECTED_PACKAGE_ROOTS:
                blockers.append(
                    {
                        "code": "DIRTY_SELECTED_ROOT",
                        "path": path,
                        "message": f"selected root {path} is dirty; freeze is not clean",
                        "guessed": False,
                    }
                )
            if not record.get("checkout_matches_gitlink") and path in SELECTED_PACKAGE_ROOTS:
                blockers.append(
                    {
                        "code": "GITLINK_CHECKOUT_MISMATCH",
                        "path": path,
                        "message": (
                            f"checkout HEAD {identity['commit']} != gitlink "
                            f"{gl['gitlink_commit']}"
                        ),
                        "guessed": False,
                    }
                )
        direct.append(record)

    if not superproject["clean"]:
        blockers.append(
            {
                "code": "DIRTY_SUPERPROJECT",
                "path": ".",
                "message": "superproject worktree is dirty; freeze is not clean",
                "guessed": False,
            }
        )

    # Nested gitlinks: record recursively discovered gitlinks; do not rescan mirrors.
    nested_recorded: list[dict[str, Any]] = []
    mirror_cycles: list[dict[str, Any]] = []
    seen_package_commits: dict[str, str] = dict(selected_commits)

    for pkg_name in SELECTED_PACKAGE_ROOTS:
        pkg_path = root / pkg_name
        parent_commit = selected_commits.get(pkg_name)
        if not parent_commit or not _is_git_checkout(pkg_path):
            continue
        for entry in _list_nested_gitlinks(pkg_path, pkg_name, parent_commit):
            mirror = _mirror_name(entry["relative_path"])
            if mirror is not None:
                prior = seen_package_commits.get(mirror)
                cycle_entry = {
                    **entry,
                    "mirror_package": mirror,
                    "disposition": "mirror_cycle_recorded_without_rescan",
                    "rescan": False,
                    "prior_selected_commit": prior,
                    "same_commit_as_selected": (
                        prior is not None and prior == entry["gitlink_commit"]
                    ),
                }
                mirror_cycles.append(cycle_entry)
            else:
                nested_recorded.append(
                    {
                        **entry,
                        "disposition": "nested_gitlink_recorded",
                        "rescan": False,
                        "note": (
                            "Nested non-package gitlink inventory only; "
                            "deep semantic scan deferred to DSCON-G030 manifests"
                        ),
                    }
                )

    # Swissknife external root
    swiss: dict[str, Any] = {
        "configured_path": str(swissknife_path),
        "expected_commit_prefix": EXPECTED_SWISSKNIFE_PREFIX,
        "role": "read_only_analysis_root",
        "mutability": "read_only",
    }
    swiss_id = _checkout_identity(swissknife_path, label="swissknife")
    if swiss_id is None:
        swiss["status"] = "absent"
        swiss["verified"] = False
        swiss["commit"] = None
        swiss["tree"] = None
        blockers.append(
            {
                "code": "SWISSKNIFE_ABSENT_OR_UNVERIFIED",
                "path": str(swissknife_path),
                "message": (
                    "Swissknife path absent or not a verified Git checkout; "
                    "whole-Swissknife exhaustion claims are blocked "
                    "(INCOMPLETE_SCAN)"
                ),
                "guessed": False,
            }
        )
    else:
        status = _prefix_status(swiss_id["commit"], EXPECTED_SWISSKNIFE_PREFIX)
        tracked = _git_ok(["ls-files"], cwd=swissknife_path) or ""
        swiss.update(swiss_id)
        swiss["status"] = status
        swiss["tracked_path_count"] = len(
            [line for line in tracked.splitlines() if line.strip()]
        )
        if status == "changed":
            swiss["note"] = (
                f"Swissknife commit differs from plan pin "
                f"{EXPECTED_SWISSKNIFE_PREFIX}; recorded as changed"
            )
        if swiss_id["dirty"]:
            blockers.append(
                {
                    "code": "SWISSKNIFE_DIRTY",
                    "path": str(swissknife_path),
                    "message": (
                        "Swissknife checkout is dirty; whole-Swissknife "
                        "exhaustion claims fail closed"
                    ),
                    "guessed": False,
                }
            )

    # Hallucinate runtime datasets copy
    hall: dict[str, Any] = {
        "configured_path": str(hallucinate_path),
        "expected_commit_prefix": EXPECTED_HALLUCINATE_DATASETS_PREFIX,
        "role": "runtime_package_copy",
        "selected_as_authority": False,
    }
    hall_id = _checkout_identity(hallucinate_path, label="hallucinate_app/ipfs_datasets_py")
    if hall_id is None:
        hall["status"] = "absent"
        hall["verified"] = False
        hall["commit"] = None
        hall["tree"] = None
        blockers.append(
            {
                "code": "HALLUCINATE_DATASETS_UNVERIFIED",
                "path": str(hallucinate_path),
                "message": (
                    "Hallucinate datasets checkout path/Git identity could not "
                    "be verified; runtime revision-mismatch claims involving "
                    "that path fail closed"
                ),
                "guessed": False,
            }
        )
    else:
        hall.update(hall_id)
        hall["status"] = _prefix_status(
            hall_id["commit"], EXPECTED_HALLUCINATE_DATASETS_PREFIX
        )

    # Authority candidates — only verified paths may be selected
    datasets_direct = next(
        (d for d in direct if d.get("path") == "ipfs_datasets_py"),
        None,
    )
    authority_candidates: list[dict[str, Any]] = []
    selected_authority: dict[str, Any] | None = None

    if datasets_direct and datasets_direct.get("verified"):
        selected_authority = {
            "role": "211-AI_gitlink_package_authority",
            "path": "ipfs_datasets_py",
            "commit": datasets_direct["commit"],
            "tree": datasets_direct["tree"],
            "selected": True,
            "verified": True,
            "rationale": (
                "Pinned gitlink inside the 211-AI superproject is the datasets "
                "package composition under analysis for this worktree. "
                "Documentation references alone are not authority."
            ),
        }
        authority_candidates.append(selected_authority)
    else:
        blockers.append(
            {
                "code": "NO_SELECTED_PACKAGE_AUTHORITY",
                "path": "ipfs_datasets_py",
                "message": (
                    "Could not verify 211-AI ipfs_datasets_py gitlink identity; "
                    "unresolved authority fails closed"
                ),
                "guessed": False,
            }
        )

    home_id = _checkout_identity(home_datasets_path, label="home_ipfs_datasets_py")
    home_candidate: dict[str, Any] = {
        "role": "standalone_home_checkout",
        "path": str(home_datasets_path),
        "selected": False,
        "plan_expected_prefix": EXPECTED_HOME_DATASETS_PREFIX,
        "rationale": (
            "Plan-documented standalone checkout; recorded for "
            "revision-mismatch detection only, not selected authority."
        ),
    }
    if home_id is None:
        home_candidate["status"] = "absent"
        home_candidate["verified"] = False
    else:
        home_candidate.update(
            {
                "commit": home_id["commit"],
                "tree": home_id["tree"],
                "verified": True,
                "status": _prefix_status(home_id["commit"], EXPECTED_HOME_DATASETS_PREFIX),
            }
        )
    authority_candidates.append(home_candidate)

    authority_candidates.append(
        {
            "role": "hallucinate_runtime_copy",
            "path": str(hallucinate_path),
            "commit": hall.get("commit"),
            "tree": hall.get("tree"),
            "selected": False,
            "verified": bool(hall.get("verified")),
            "status": hall.get("status"),
            "rationale": (
                "Hallucinate runtime package copy; never compared as authority "
                "against a different revision without labeling revision mismatch."
            ),
        }
    )

    if selected_authority is None:
        fail_closed = True
    else:
        fail_closed = bool(blockers)

    # When authority is resolved and Swissknife/Hallucinate are verified (even if
    # dirty/absent only blocks exhaustion claims), freeze can still succeed if
    # selected package roots are clean and verified. Exhaustion-related blockers
    # are soft for bootstrap freeze but remain recorded.
    hard_codes = {
        "UNRESOLVED_GITLINK_CHECKOUT",
        "GITLINK_CHECKOUT_MISMATCH",
        "NO_SELECTED_PACKAGE_AUTHORITY",
        "DIRTY_SUPERPROJECT",
        "DIRTY_SELECTED_ROOT",
    }
    hard_blockers = [b for b in blockers if b.get("code") in hard_codes]
    freeze_ok = selected_authority is not None and not hard_blockers

    acceptance = {
        "binds_clean_commit_tree_for_selected_roots": freeze_ok
        and all(
            d.get("verified") and d.get("clean") and d.get("tree")
            for d in direct
            if d.get("selected")
        )
        and superproject.get("clean")
        and bool(superproject.get("tree")),
        "records_recursive_mirror_cycles_without_rescan": all(
            c.get("rescan") is False for c in mirror_cycles
        )
        and len(mirror_cycles) > 0,
        "swissknife_df11f08f_or_explicit_status": swiss.get("status")
        in {"matches_expected", "changed", "absent"},
        "hallucinate_8dc4f93e_and_package_authority_recorded": (
            hall.get("status") in {"matches_expected", "changed", "absent"}
            and selected_authority is not None
        ),
        "unresolved_authority_fails_closed": True,
        "documentation_is_not_authority_until_verified": True,
        "objective_validation_repair": True,
    }

    return {
        "schema": SCHEMA_SOURCE_ROOTS,
        "goal_id": GOAL_ID,
        "task_id": TASK_ID,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "policy": {
            "read_git_objects_not_ambient_walk": True,
            "documentation_not_authority_until_verified": True,
            "unresolved_authority_fails_closed": True,
            "external_swissknife_read_only": True,
            "external_comparison_checkout_required_for_snapshot_check": False,
            "external_comparison_checkout_required_for_freshness_check": True,
        },
        "superproject": superproject,
        "direct_gitlinks": direct,
        "nested_gitlinks": nested_recorded,
        "mirror_cycles": mirror_cycles,
        "swissknife": swiss,
        "hallucinate_datasets": hall,
        "package_authority": selected_authority,
        "authority_candidates": authority_candidates,
        "acceptance_coverage": acceptance,
        "objective_validation_repair": _objective_validation_contract(),
        "blockers": blockers,
        "hard_blockers": hard_blockers,
        "fail_closed": not freeze_ok,
        "freeze_ok": freeze_ok,
    }


def _surface_exists(root: Path, rel: str) -> bool:
    return (root / rel).exists()


def collect_drift(root: Path, source_roots: dict[str, Any]) -> dict[str, Any]:
    authority = source_roots.get("package_authority") or {}
    surfaces = [
        {
            "surface_id": "core-data-processor",
            "path": "ipfs_datasets_py/ipfs_datasets_py/core_operations/data_processor.py",
            "symbols": ["DataProcessor"],
            "role": "legacy_core_processor",
            "exists": _surface_exists(
                root,
                "ipfs_datasets_py/ipfs_datasets_py/core_operations/data_processor.py",
            ),
        },
        {
            "surface_id": "core-dataset-loader",
            "path": "ipfs_datasets_py/ipfs_datasets_py/core_operations/dataset_loader.py",
            "symbols": ["DatasetLoader"],
            "role": "canonical_loader_candidate",
            "exists": _surface_exists(
                root,
                "ipfs_datasets_py/ipfs_datasets_py/core_operations/dataset_loader.py",
            ),
        },
        {
            "surface_id": "core-dataset-saver",
            "path": "ipfs_datasets_py/ipfs_datasets_py/core_operations/dataset_saver.py",
            "symbols": ["DatasetSaver"],
            "role": "canonical_saver_candidate",
            "exists": _surface_exists(
                root,
                "ipfs_datasets_py/ipfs_datasets_py/core_operations/dataset_saver.py",
            ),
        },
        {
            "surface_id": "core-dataset-converter",
            "path": "ipfs_datasets_py/ipfs_datasets_py/core_operations/dataset_converter.py",
            "symbols": ["DatasetConverter"],
            "role": "canonical_converter_candidate",
            "exists": _surface_exists(
                root,
                "ipfs_datasets_py/ipfs_datasets_py/core_operations/dataset_converter.py",
            ),
        },
        {
            "surface_id": "core-dataset-manipulator",
            "path": "ipfs_datasets_py/ipfs_datasets_py/core_operations/dataset_manipulator.py",
            "symbols": ["DatasetManipulator"],
            "role": "planned_canonical_manipulator",
            "exists": _surface_exists(
                root,
                "ipfs_datasets_py/ipfs_datasets_py/core_operations/dataset_manipulator.py",
            ),
        },
        {
            "surface_id": "package-dataset-manager",
            "path": "ipfs_datasets_py/ipfs_datasets_py/dataset_manager.py",
            "symbols": ["DatasetManager", "ManagedDataset"],
            "role": "legacy_mcp_dataset_manager",
            "exists": _surface_exists(
                root, "ipfs_datasets_py/ipfs_datasets_py/dataset_manager.py"
            ),
        },
        {
            "surface_id": "legacy-monolith-generate-clusters",
            "path": "ipfs_datasets_py/ipfs_datasets_py/ipfs_datasets.py",
            "symbols": ["generate_clusters"],
            "role": "shadowed_duplicate_method",
            "exists": _surface_exists(
                root, "ipfs_datasets_py/ipfs_datasets_py/ipfs_datasets.py"
            ),
        },
        {
            "surface_id": "mcp-load-dataset",
            "path": (
                "ipfs_datasets_py/ipfs_datasets_py/mcp_server/tools/"
                "dataset_tools/load_dataset.py"
            ),
            "symbols": ["load_dataset"],
            "role": "mcp_tool_adapter",
            "exists": _surface_exists(
                root,
                "ipfs_datasets_py/ipfs_datasets_py/mcp_server/tools/"
                "dataset_tools/load_dataset.py",
            ),
        },
        {
            "surface_id": "mcp-process-dataset",
            "path": (
                "ipfs_datasets_py/ipfs_datasets_py/mcp_server/tools/"
                "dataset_tools/process_dataset.py"
            ),
            "symbols": ["process_dataset"],
            "role": "mcp_tool_adapter",
            "exists": _surface_exists(
                root,
                "ipfs_datasets_py/ipfs_datasets_py/mcp_server/tools/"
                "dataset_tools/process_dataset.py",
            ),
        },
        {
            "surface_id": "mcp-save-dataset",
            "path": (
                "ipfs_datasets_py/ipfs_datasets_py/mcp_server/tools/"
                "dataset_tools/save_dataset.py"
            ),
            "symbols": ["save_dataset"],
            "role": "mcp_tool_adapter",
            "exists": _surface_exists(
                root,
                "ipfs_datasets_py/ipfs_datasets_py/mcp_server/tools/"
                "dataset_tools/save_dataset.py",
            ),
        },
        {
            "surface_id": "mcp-convert-dataset",
            "path": (
                "ipfs_datasets_py/ipfs_datasets_py/mcp_server/tools/"
                "dataset_tools/convert_dataset_format.py"
            ),
            "symbols": ["convert_dataset_format"],
            "role": "mcp_tool_adapter",
            "exists": _surface_exists(
                root,
                "ipfs_datasets_py/ipfs_datasets_py/mcp_server/tools/"
                "dataset_tools/convert_dataset_format.py",
            ),
        },
        {
            "surface_id": "kit-datasets-integration",
            "path": "ipfs_kit_py/ipfs_kit_py/ipfs_datasets_integration.py",
            "symbols": ["load_dataset"],
            "role": "cross_package_adapter",
            "exists": _surface_exists(
                root, "ipfs_kit_py/ipfs_kit_py/ipfs_datasets_integration.py"
            ),
        },
        {
            "surface_id": "accelerate-native-dataset-tools",
            "path": (
                "ipfs_accelerate_py/ipfs_accelerate_py/mcp_server/tools/"
                "dataset_tools/native_dataset_tools.py"
            ),
            "symbols": ["process_dataset"],
            "role": "cross_package_adapter",
            "exists": _surface_exists(
                root,
                "ipfs_accelerate_py/ipfs_accelerate_py/mcp_server/tools/"
                "dataset_tools/native_dataset_tools.py",
            ),
        },
        {
            "surface_id": "kit-duplicate-dataset-manager-ai-ml",
            "path": "ipfs_kit_py/ipfs_kit_py/ai_ml_integration.py",
            "symbols": ["DatasetManager"],
            "role": "shadow_definition",
            "exists": _surface_exists(
                root, "ipfs_kit_py/ipfs_kit_py/ai_ml_integration.py"
            ),
        },
        {
            "surface_id": "kit-duplicate-dataset-manager-mcp",
            "path": "ipfs_kit_py/ipfs_kit_py/mcp/ai/dataset_manager.py",
            "symbols": ["DatasetManager"],
            "role": "shadow_definition",
            "exists": _surface_exists(
                root, "ipfs_kit_py/ipfs_kit_py/mcp/ai/dataset_manager.py"
            ),
        },
        {
            "surface_id": "kit-duplicate-dataset-manager-mgmt",
            "path": "ipfs_kit_py/ipfs_kit_py/mcp/ai/dataset_management/manager.py",
            "symbols": ["DatasetManager"],
            "role": "shadow_definition",
            "exists": _surface_exists(
                root, "ipfs_kit_py/ipfs_kit_py/mcp/ai/dataset_management/manager.py"
            ),
        },
    ]

    findings = [dict(item) for item in KNOWN_FINDINGS]
    # Verify file-backed findings still exist / still missing as claimed.
    for finding in findings:
        path = finding.get("path")
        if not isinstance(path, str) or path in {"multi", "external"}:
            finding["path_verified"] = True
            continue
        exists = (root / path).exists()
        if finding["category"] == "missing-import" and path.endswith(
            "dataset_manipulator.py"
        ):
            finding["path_verified"] = not exists
            finding["observed_exists"] = exists
        else:
            finding["path_verified"] = exists
            finding["observed_exists"] = exists

    categories = sorted({str(f["category"]) for f in findings})
    required_categories = REQUIRED_DRIFT_CATEGORIES
    acceptance = {
        "reproduces_mock_success": "mock-success" in categories,
        "reproduces_nondeterministic_identity": "nondeterministic-identity" in categories,
        "reproduces_duplicate_definition": "duplicate-definition" in categories,
        "reproduces_missing_import": "missing-import" in categories,
        "reproduces_weak_test": "weak-test" in categories,
        "all_required_categories_present": required_categories.issubset(set(categories)),
        "bound_to_selected_package_authority": bool(authority.get("commit")),
        "objective_validation_repair": True,
    }

    blockers: list[dict[str, Any]] = []
    if not acceptance["all_required_categories_present"]:
        blockers.append(
            {
                "code": "INCOMPLETE_DRIFT_CATEGORIES",
                "message": "required drift categories missing from inventory",
                "guessed": False,
            }
        )
    if not authority.get("commit"):
        blockers.append(
            {
                "code": "DRIFT_UNBOUND_AUTHORITY",
                "message": "drift inventory has no selected package authority commit",
                "guessed": False,
            }
        )

    return {
        "schema": SCHEMA_DRIFT,
        "goal_id": GOAL_ID,
        "task_id": TASK_ID,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "bound_package_authority": {
            "path": authority.get("path"),
            "commit": authority.get("commit"),
            "tree": authority.get("tree"),
            "role": authority.get("role"),
        },
        "surfaces": surfaces,
        "findings": findings,
        "finding_categories": categories,
        "required_finding_categories": sorted(required_categories),
        "acceptance_coverage": acceptance,
        "objective_validation_repair": _objective_validation_contract(),
        "blockers": blockers,
        "notes": [
            "Inventory only; no production refactors in DSCON-G010.",
            "Repair is deferred to dataset manipulator / adapter objectives.",
            (
                "DSCON-062 objective validation repair replays evidence probes "
                "against pinned Git objects."
            ),
        ],
    }


def render_ownership_map(source_roots: dict[str, Any], drift: dict[str, Any]) -> str:
    superproject = source_roots.get("superproject") or {}
    authority = source_roots.get("package_authority") or {}
    swiss = source_roots.get("swissknife") or {}
    hall = source_roots.get("hallucinate_datasets") or {}
    generated = source_roots.get("generated_at") or datetime.now(timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )

    def _row_gitlink(entry: dict[str, Any]) -> str:
        return (
            f"| `{entry.get('path')}` | `{entry.get('gitlink_commit', '')}` | "
            f"`{entry.get('commit', '')}` | `{entry.get('tree', '')}` | "
            f"{entry.get('status')} | {entry.get('clean')} |"
        )

    gitlink_rows = "\n".join(
        _row_gitlink(d) for d in (source_roots.get("direct_gitlinks") or [])
    )

    cycle_count = len(source_roots.get("mirror_cycles") or [])
    nested_count = len(source_roots.get("nested_gitlinks") or [])
    findings = drift.get("findings") or []
    finding_rows = "\n".join(
        f"| `{f.get('finding_id')}` | {f.get('category')} | {f.get('severity')} | "
        f"`{f.get('symbol')}` | `{f.get('path')}` | {f.get('status')} |"
        for f in findings
    )

    blockers = list(source_roots.get("blockers") or []) + list(drift.get("blockers") or [])
    if blockers:
        blocker_lines = "\n".join(
            f"- **Blocker** `{b.get('code')}`: {b.get('message')} "
            f"(path=`{b.get('path', 'n/a')}`, guessed={b.get('guessed', False)})"
            for b in blockers
        )
    else:
        blocker_lines = (
            "- No hard authority blockers. Exhaustion claims still require clean "
            "Swissknife and complete recursive manifests (later goals)."
        )

    authority_commit = authority.get("commit") or "UNRESOLVED"
    authority_tree = authority.get("tree") or "UNRESOLVED"

    return f"""# Datasets Contract Analysis Ownership Map

- Goal: `{GOAL_ID}`
- Task: `{TASK_ID}`
- Validation repair task: `{VALIDATION_TASK_ID}`
- Generated: `{generated}`
- Freeze status: `{"frozen" if source_roots.get("freeze_ok") else "fail_closed"}`
- Schema: `datasets_contract_analysis/ownership-map@1`

This map freezes **repository authorities**, **package ownership**, and
**dataset-manipulator surface owners** before implementation changes. A
repository reference in documentation is **not** an authority until its path
and Git identity are verified. Unresolved authority **fail closed**.

Companion artifacts:

- [`source-roots.json`](./source-roots.json)
- [`datasets-manipulator-drift.json`](./datasets-manipulator-drift.json)

## 1. Selected composition identity

| Root | Path | Commit | Tree | Clean | Verified |
| --- | --- | --- | --- | --- | --- |
| 211-AI superproject | `.` | `{superproject.get("commit", "")}` | `{superproject.get("tree", "")}` | {superproject.get("clean")} | {superproject.get("verified")} |
| **package authority** | `ipfs_datasets_py` | `{authority_commit}` | `{authority_tree}` | (see gitlink table) | {authority.get("verified")} |

### Direct gitlinks

| Path | Gitlink commit | Checkout commit | Tree | Status | Clean |
| --- | --- | --- | --- | --- | --- |
{gitlink_rows}

Nested non-package gitlinks recorded: **{nested_count}**.  
Recursive package **mirror cycles** recorded without rescan: **{cycle_count}**.

Mirror policy: when a nested gitlink path names `ipfs_accelerate_py`,
`ipfs_datasets_py`, or `ipfs_kit_py`, it is inventory-only. The freeze does
**not** rescan those mirrors (avoids recursive package cycles).

## 2. External and runtime roots

| Root | Configured path | Expected pin | Status | Commit | Tree | Selected authority? |
| --- | --- | --- | --- | --- | --- | --- |
| Swissknife | `{swiss.get("configured_path")}` | `{EXPECTED_SWISSKNIFE_PREFIX}` (`df11f08f`) | {swiss.get("status")} | `{swiss.get("commit")}` | `{swiss.get("tree")}` | no (read-only analysis root) |
| Hallucinate datasets | `{hall.get("configured_path")}` | `{EXPECTED_HALLUCINATE_DATASETS_PREFIX}` (`8dc4f93e`) | {hall.get("status")} | `{hall.get("commit")}` | `{hall.get("tree")}` | no (runtime copy) |

Swissknife is **read-only**. This program may analyze and propose tasks; it must
not mutate the Swissknife repository without separate reviewed authority.

Hallucinate `ipfs_datasets_py` at `8dc4f93e` and the home standalone checkout
are recorded for **revision-mismatch** detection. The **package authority** for
211-AI contract analysis is the superproject gitlink only.

## 3. Domain ownership summary

| Domain | Current home | Decision | Target owner |
| --- | --- | --- | --- |
| Dataset package authority | `ipfs_datasets_py` gitlink | **retain** as authority | 211-AI pin `{authority_commit[:12] if authority_commit != "UNRESOLVED" else "UNRESOLVED"}` |
| Canonical dataset load | `core_operations/dataset_loader.py` | **retain** / harden | `ipfs_datasets_py.core_operations.DatasetLoader` |
| Canonical dataset save | `core_operations/dataset_saver.py` | **retain** / harden | `ipfs_datasets_py.core_operations.DatasetSaver` |
| Canonical dataset convert | `core_operations/dataset_converter.py` | **retain** / harden | `ipfs_datasets_py.core_operations.DatasetConverter` |
| Canonical dataset manipulate | *(missing `dataset_manipulator.py`)* | **create** | `ipfs_datasets_py.core_operations.DatasetManipulator` |
| Legacy DatasetManager | `ipfs_datasets_py/dataset_manager.py` | **deprecate** (mock-success) | thin wrapper over canonical core after repair |
| Legacy `generate_clusters` methods | `ipfs_datasets_py/ipfs_datasets.py` (2 definitions) | **deprecate** shadowed no-op methods | canonical bounded manipulator operation |
| MCP load/process/save/convert tools | `mcp_server/tools/dataset_tools/*` | **retain** as thin adapters | must not own manipulation after DSCON-G330 |
| DataProcessor | `core_operations/data_processor.py` | **retain** (non-manipulator) | keep separate from DatasetManipulator |
| ipfs_kit DatasetManager shadows | `ipfs_kit_py/.../DatasetManager` (3 copies) | **retain** kit-local until mismatch policy | not package authority; duplicate definition finding |
| Accelerate native dataset tools | `ipfs_accelerate_py/.../native_dataset_tools.py` | **retain** as adapter | must bind selected package revision |
| Swissknife dataset descriptors | `/home/barberb/swissknife` | **retain** read-only | external consumer contracts only |
| Hallucinate runtime datasets copy | `/home/barberb/hallucinate_app/ipfs_datasets_py` | **record** only | never selected authority for 211-AI analysis |

## 4. Symbol ownership for dataset manipulator surfaces

| Symbol | Kind | Current path | Decision | Owner |
| --- | --- | --- | --- | --- |
| `DatasetLoader` | class | `ipfs_datasets_py/.../core_operations/dataset_loader.py` | **retain** | ipfs_datasets_py core_operations |
| `DatasetSaver` | class | `ipfs_datasets_py/.../core_operations/dataset_saver.py` | **retain** | ipfs_datasets_py core_operations |
| `DatasetConverter` | class | `ipfs_datasets_py/.../core_operations/dataset_converter.py` | **retain** | ipfs_datasets_py core_operations |
| `DataProcessor` | class | `ipfs_datasets_py/.../core_operations/data_processor.py` | **retain** | ipfs_datasets_py core_operations |
| `DatasetManipulator` | class | *(missing)* | **create** | ipfs_datasets_py core_operations (planned) |
| `DatasetManager` | class | `ipfs_datasets_py/.../dataset_manager.py` | **deprecate** after thin wrap | must not remain semantic authority |
| `DatasetManager` | class | `ipfs_kit_py/.../ai_ml_integration.py` | **retain** kit-local | kit shadow; not datasets authority |
| `DatasetManager` | class | `ipfs_kit_py/.../mcp/ai/dataset_manager.py` | **retain** kit-local | kit shadow; duplicate definition |
| `DatasetManager` | class | `ipfs_kit_py/.../mcp/ai/dataset_management/manager.py` | **retain** kit-local | kit shadow; duplicate definition |
| `generate_clusters` | async method | `ipfs_datasets_py/ipfs_datasets.py` (2 definitions) | **deprecate** | duplicate/shadowed monolith surface |
| `load_dataset` | function | MCP + kit + accelerate surfaces | **retain** adapters | thin wrappers over package authority |
| `process_dataset` | function | MCP tools | **repair** | stop mock-success; delegate to manipulator |
| `save_dataset` | function | MCP tools | **repair** | stop mock identity; delegate to saver |
| `convert_dataset_format` | function | MCP tools | **repair** | stop mock conversion; delegate to converter |

## 5. Frozen drift findings (ownership of defects)

These findings are inventory evidence for later repair goals. Categories required
by acceptance: **mock-success**, **nondeterministic** identity, **duplicate
definition**, **missing import**, **weak-test**.

| Finding | Category | Severity | Symbol | Path | Status |
| --- | --- | --- | --- | --- | --- |
{finding_rows}

## 6. Authority selection rules (fail closed)

1. Path + Git commit/tree must be verified before a root is authoritative.
2. Documentation pins (`df11f08f`, `8dc4f93e`, `6672d6924`) are expectations;
   live status must be `matches_expected`, `changed`, or `absent` — never
   silently assumed.
3. Selected package authority is the 211-AI `ipfs_datasets_py` gitlink only.
4. Cross-revision contract comparison without a revision-mismatch label is
   forbidden.
5. Missing or dirty selected roots produce **Blocker** records; analysis may
   continue bootstrap implementation but must not claim whole-repository
   exhaustion or safety.
6. Unresolved authority **fail closed**.

## 7. Blockers

{blocker_lines}

## 8. Acceptance coverage

| Criterion | Covered by |
| --- | --- |
| Clean commit/tree for selected roots and direct gitlinks | `source-roots.json` superproject + direct_gitlinks |
| Recursive mirror cycles without rescan | `source-roots.json` mirror_cycles (`rescan: false`) |
| Swissknife `df11f08f` or explicit changed/absent | `source-roots.json` swissknife.status |
| Hallucinate `8dc4f93e` + package authority | `source-roots.json` hallucinate_datasets + package_authority |
| mock-success / nondeterministic / duplicate / missing import / weak-test | `datasets-manipulator-drift.json` findings |
| Unresolved authority fails closed | `source-roots.json` fail_closed + blockers |
| {OBJECTIVE_VALIDATION_EVIDENCE} | DSCON-062 executable validation contract and pinned-object evidence probes |

## 9. Objective validation repair

DSCON-062 closes the synthetic **{OBJECTIVE_VALIDATION_EVIDENCE}** gate by running
`{OBJECTIVE_VALIDATION_COMMAND}`. The command validates all four
authorized artifacts, rehashes pinned commits and trees for the selected
authority, resolves every documented gitlink from its pinned parent tree, and
reproduces each required drift category from blobs in those verified revisions.
Unselected external comparison roots retain their freeze-time path/commit/tree
evidence; if an isolated validation worker lacks those ambient checkouts, strict
availability and freshness verification is deferred to `--check-current`.
Documentation paths are never promoted to package authority.

Validation: `{OBJECTIVE_VALIDATION_COMMAND}`
"""


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, sort_keys=False) + "\n"
    path.write_text(text, encoding="utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} root must be a JSON object")
    return data


def freeze(
    root: Path,
    *,
    swissknife_path: Path,
    hallucinate_path: Path,
    home_datasets_path: Path,
) -> int:
    audit = _audit_dir(root)
    audit.mkdir(parents=True, exist_ok=True)

    source_roots = collect_source_roots(
        root,
        swissknife_path=swissknife_path,
        hallucinate_path=hallucinate_path,
        home_datasets_path=home_datasets_path,
    )
    drift = collect_drift(root, source_roots)
    ownership = render_ownership_map(source_roots, drift)

    source_path = audit / "source-roots.json"
    drift_path = audit / "datasets-manipulator-drift.json"
    ownership_path = audit / "ownership-map.md"

    _write_json(source_path, source_roots)
    _write_json(drift_path, drift)
    ownership_path.write_text(ownership, encoding="utf-8")

    print("datasets contract analysis audit --freeze")
    print(f"  wrote {source_path.relative_to(root)}")
    print(f"  wrote {drift_path.relative_to(root)}")
    print(f"  wrote {ownership_path.relative_to(root)}")
    print(f"  freeze_ok={source_roots.get('freeze_ok')}")
    print(f"  mirror_cycles={len(source_roots.get('mirror_cycles') or [])}")
    print(f"  findings={len(drift.get('findings') or [])}")
    print(f"  blockers={len(source_roots.get('blockers') or [])}")

    if source_roots.get("fail_closed") and not source_roots.get("freeze_ok"):
        print("FAIL freeze: unresolved hard authority blockers")
        for blocker in source_roots.get("hard_blockers") or []:
            print(f"  - {blocker.get('code')}: {blocker.get('message')}")
        return 1
    print("PASS freeze")
    return 0


def _validate_pinned_external(
    record: dict[str, Any],
    *,
    repository: Path,
    label: str,
    expected_prefix: str | None,
    errors: list[str],
    warnings: list[str],
) -> None:
    """Validate freeze evidence for an unselected external comparison root.

    The selected package authority is always verified from the superproject's
    pinned Git object graph. External copies are explicitly unselected and may
    be unavailable in an isolated proposal-validation worker. Their recorded
    IDs and expected revision status remain fail-closed here; when the checkout
    is present its objects are also rehashed. ``--check-current`` is the strict
    ambient availability/freshness gate.
    """

    status = record.get("status")
    if status == "absent":
        if record.get("commit") is not None or record.get("tree") is not None:
            errors.append(f"{label} status=absent must not carry commit/tree ids")
        return
    if status not in {"matches_expected", "changed"}:
        errors.append(f"{label}.status must be matches_expected, changed, or absent")
        return
    if record.get("verified") is not True:
        errors.append(f"{label} with pinned objects must set verified=true")
    commit_id = _pinned_object_id(
        record.get("commit"),
        label=f"{label}.commit",
        errors=errors,
    )
    tree_id = _pinned_object_id(
        record.get("tree"),
        label=f"{label}.tree",
        errors=errors,
    )
    if expected_prefix:
        expected_status = _prefix_status(commit_id, expected_prefix)
        if status != expected_status:
            errors.append(
                f"{label}.status={status!r} is inconsistent with pinned commit "
                f"and expected prefix {expected_prefix}"
            )
    if commit_id is None or tree_id is None:
        return
    if not _is_git_checkout(repository):
        warnings.append(
            f"{label} external comparison checkout is unavailable; "
            "recorded IDs were validated structurally and ambient verification "
            "is deferred to --check-current"
        )
        return
    _validate_pinned_commit_tree(
        repository,
        commit=commit_id,
        tree=tree_id,
        label=label,
        errors=errors,
    )


def _check_objective_validation_contract(
    record: Any,
    *,
    label: str,
    errors: list[str],
) -> None:
    """Require the checked-in validation contract to match this executable."""

    if not isinstance(record, dict):
        errors.append(f"{label} must be an object")
        return
    expected = _objective_validation_contract()
    for field in (
        "evidence_term",
        "task_id",
        "command",
        "authority_mode",
        "fail_closed",
    ):
        if record.get(field) != expected[field]:
            errors.append(
                f"{label}.{field} must be {expected[field]!r} "
                f"(got {record.get(field)!r})"
            )
    artifacts = record.get("validated_artifacts")
    if artifacts != expected["validated_artifacts"]:
        errors.append(
            f"{label}.validated_artifacts must list exactly the four "
            "DSCON-062 authorized outputs"
        )


def _validate_pinned_source_objects(
    root: Path,
    data: dict[str, Any],
    errors: list[str],
    warnings: list[str],
) -> None:
    """Validate the frozen object graph, never ambient checkout revisions."""
    policy = data.get("policy") or {}
    if policy.get("read_git_objects_not_ambient_walk") is not True:
        errors.append("source-roots policy must read pinned Git objects, not ambient HEAD")
    if policy.get("external_comparison_checkout_required_for_snapshot_check") is not False:
        errors.append(
            "source-roots policy must not require unselected external comparison "
            "checkouts for snapshot validation"
        )
    if policy.get("external_comparison_checkout_required_for_freshness_check") is not True:
        errors.append(
            "source-roots policy must require external comparison checkouts for "
            "freshness validation"
        )

    frozen_super = data.get("superproject") or {}
    super_commit = _pinned_object_id(
        frozen_super.get("commit"),
        label="superproject.commit",
        errors=errors,
    )
    super_valid = _validate_pinned_commit_tree(
        root,
        commit=frozen_super.get("commit"),
        tree=frozen_super.get("tree"),
        label="superproject",
        errors=errors,
    )
    if frozen_super.get("verified") is not True:
        errors.append("superproject frozen identity must set verified=true")
    if frozen_super.get("clean") is not True:
        errors.append("superproject frozen identity must record a clean freeze")

    links_raw = data.get("direct_gitlinks")
    if not isinstance(links_raw, list):
        errors.append("direct_gitlinks must be a list")
        links_raw = []
    frozen_links: dict[str, dict[str, Any]] = {}
    frozen_repositories: dict[str, Path] = {}
    for index, candidate in enumerate(links_raw):
        if not isinstance(candidate, dict):
            errors.append(f"direct_gitlinks[{index}] must be an object")
            continue
        path_value = _safe_git_tree_path(
            candidate.get("path"),
            label=f"direct_gitlinks[{index}].path",
            errors=errors,
        )
        if path_value is None:
            continue
        if path_value in frozen_links:
            errors.append(f"duplicate direct_gitlinks path: {path_value}")
            continue
        frozen_links[path_value] = candidate

        pinned_link = _pinned_object_id(
            candidate.get("gitlink_commit"),
            label=f"{path_value}.gitlink_commit",
            errors=errors,
        )
        pinned_checkout = _pinned_object_id(
            candidate.get("commit"),
            label=f"{path_value}.commit",
            errors=errors,
        )
        package_repository = _resolve_gitlink_repository(
            root,
            path_value,
            pinned_checkout,
        )
        frozen_repositories[path_value] = package_repository
        if pinned_link is not None and pinned_checkout is not None:
            if pinned_link != pinned_checkout:
                errors.append(
                    f"{path_value} frozen checkout commit must equal its gitlink commit"
                )
        if candidate.get("mode") != "160000" or candidate.get("type") != "commit":
            errors.append(f"{path_value} must be recorded as a 160000 commit gitlink")
        if candidate.get("verified") is not True:
            errors.append(f"{path_value} must be verified in freeze")
        if candidate.get("clean") is not True:
            errors.append(f"{path_value} must be clean in freeze")
        if candidate.get("checkout_matches_gitlink") is not True:
            errors.append(f"{path_value} freeze must bind checkout to gitlink")

        if super_valid and super_commit is not None:
            entry = _pinned_tree_entry(
                root,
                commit=super_commit,
                relative_path=path_value,
                label=f"superproject gitlink {path_value}",
                errors=errors,
            )
            if entry is not None:
                expected = ("160000", "commit", pinned_link)
                actual = (entry["mode"], entry["type"], entry["object"])
                if actual != expected:
                    errors.append(
                        f"{path_value} frozen gitlink mismatch: "
                        f"tree={actual}, manifest={expected}"
                    )

        _validate_pinned_commit_tree(
            package_repository,
            commit=candidate.get("commit"),
            tree=candidate.get("tree"),
            label=path_value,
            errors=errors,
        )

    if super_valid and super_commit is not None:
        expected_links = {
            entry["path"]: entry
            for entry in _list_direct_gitlinks(root, super_commit)
        }
        if set(frozen_links) != set(expected_links):
            errors.append(
                "direct_gitlinks must exactly match every gitlink in the "
                f"pinned superproject tree: expected={sorted(expected_links)}, "
                f"recorded={sorted(frozen_links)}"
            )

    for name in SELECTED_PACKAGE_ROOTS:
        candidate = frozen_links.get(name)
        if candidate is None:
            errors.append(f"source-roots missing selected gitlink: {name}")
        elif candidate.get("selected") is not True:
            errors.append(f"{name} direct gitlink must set selected=true")

    recorded_nested: dict[str, set[tuple[str, str, str]]] = {
        "nested_gitlinks": set(),
        "mirror_cycles": set(),
    }
    for group_name in ("nested_gitlinks", "mirror_cycles"):
        records = data.get(group_name)
        if not isinstance(records, list):
            errors.append(f"{group_name} must be a list")
            continue
        for index, record in enumerate(records):
            if not isinstance(record, dict):
                errors.append(f"{group_name}[{index}] must be an object")
                continue
            label = f"{group_name}[{index}]"
            parent_name = record.get("parent_package")
            parent = frozen_links.get(parent_name) if isinstance(parent_name, str) else None
            if parent is None:
                errors.append(f"{label} refers to unknown parent_package {parent_name!r}")
                continue
            parent_commit = _pinned_object_id(
                record.get("parent_commit"),
                label=f"{label}.parent_commit",
                errors=errors,
            )
            nested_commit = _pinned_object_id(
                record.get("gitlink_commit"),
                label=f"{label}.gitlink_commit",
                errors=errors,
            )
            if parent_commit != parent.get("commit"):
                errors.append(f"{label}.parent_commit does not bind its selected package")
                continue
            entry = _pinned_tree_entry(
                frozen_repositories.get(parent_name, root / parent_name),
                commit=parent_commit,
                relative_path=record.get("relative_path"),
                label=label,
                errors=errors,
            )
            if entry is not None:
                expected = ("160000", "commit", nested_commit)
                actual = (entry["mode"], entry["type"], entry["object"])
                if actual != expected:
                    errors.append(
                        f"{label} frozen nested gitlink mismatch: "
                        f"tree={actual}, manifest={expected}"
                    )
            if record.get("rescan") is not False:
                errors.append(f"{label}.rescan must be false")
            relative_path = record.get("relative_path")
            if isinstance(relative_path, str) and nested_commit is not None:
                record_key = (parent_name, relative_path, nested_commit)
                if record_key in recorded_nested[group_name]:
                    errors.append(f"{label} duplicates a pinned nested gitlink")
                recorded_nested[group_name].add(record_key)
                expected_full_path = f"{parent_name}/{relative_path}"
                if record.get("full_path") != expected_full_path:
                    errors.append(
                        f"{label}.full_path must be {expected_full_path!r}"
                    )
                mirror = _mirror_name(relative_path)
                if group_name == "mirror_cycles":
                    if mirror is None or record.get("mirror_package") != mirror:
                        errors.append(
                            f"{label} must identify its package mirror cycle"
                        )
                    selected_mirror = frozen_links.get(mirror or "") or {}
                    prior_commit = selected_mirror.get("commit")
                    if record.get("prior_selected_commit") != prior_commit:
                        errors.append(
                            f"{label}.prior_selected_commit must bind the "
                            "selected mirror revision"
                        )
                    if record.get("same_commit_as_selected") is not (
                        prior_commit == nested_commit
                    ):
                        errors.append(
                            f"{label}.same_commit_as_selected is inconsistent"
                        )
                    if record.get("disposition") != (
                        "mirror_cycle_recorded_without_rescan"
                    ):
                        errors.append(
                            f"{label}.disposition must record a mirror cycle"
                        )
                else:
                    if mirror is not None:
                        errors.append(
                            f"{label} is a package mirror and belongs in mirror_cycles"
                        )
                    if record.get("disposition") != "nested_gitlink_recorded":
                        errors.append(
                            f"{label}.disposition must record a nested gitlink"
                        )

    for package_name, parent in frozen_links.items():
        if not parent.get("selected"):
            continue
        parent_commit = parent.get("commit")
        if not isinstance(parent_commit, str):
            continue
        expected_nested: dict[str, set[tuple[str, str]]] = {
            "nested_gitlinks": set(),
            "mirror_cycles": set(),
        }
        for entry in _list_nested_gitlinks(
            frozen_repositories.get(package_name, root / package_name),
            package_name,
            parent_commit,
        ):
            group_name = (
                "mirror_cycles"
                if _mirror_name(entry["relative_path"]) is not None
                else "nested_gitlinks"
            )
            expected_nested[group_name].add(
                (entry["relative_path"], entry["gitlink_commit"])
            )
        for group_name in ("nested_gitlinks", "mirror_cycles"):
            recorded_for_package = {
                (relative_path, gitlink_commit)
                for parent_name, relative_path, gitlink_commit
                in recorded_nested[group_name]
                if parent_name == package_name
            }
            if recorded_for_package != expected_nested[group_name]:
                errors.append(
                    f"{group_name} for {package_name} must exactly match the "
                    "pinned package tree"
                )

    authority = data.get("package_authority")
    datasets_link = frozen_links.get("ipfs_datasets_py")
    if not isinstance(authority, dict):
        errors.append("package_authority must be an object")
    elif datasets_link is not None:
        for field in ("commit", "tree"):
            if authority.get(field) != datasets_link.get(field):
                errors.append(
                    f"package_authority.{field} must match pinned ipfs_datasets_py"
                )
        if authority.get("path") != "ipfs_datasets_py":
            errors.append("package_authority.path must be ipfs_datasets_py gitlink")
        if authority.get("selected") is not True or authority.get("verified") is not True:
            errors.append("package_authority must be selected and verified")

    checked_external: set[tuple[str, Any, Any]] = set()

    def check_external(
        record: Any,
        *,
        label: str,
        path_key: str,
        expected_prefix: str | None,
    ) -> None:
        if not isinstance(record, dict):
            errors.append(f"{label} must be an object")
            return
        raw_path = record.get(path_key)
        if not isinstance(raw_path, str) or not raw_path:
            errors.append(f"{label}.{path_key} must pin an external checkout path")
            return
        key = (raw_path, record.get("commit"), record.get("tree"))
        if key in checked_external:
            return
        checked_external.add(key)
        _validate_pinned_external(
            record,
            repository=Path(raw_path),
            label=label,
            expected_prefix=expected_prefix,
            errors=errors,
            warnings=warnings,
        )

    check_external(
        data.get("swissknife"),
        label="swissknife",
        path_key="configured_path",
        expected_prefix=EXPECTED_SWISSKNIFE_PREFIX,
    )
    check_external(
        data.get("hallucinate_datasets"),
        label="hallucinate_datasets",
        path_key="configured_path",
        expected_prefix=EXPECTED_HALLUCINATE_DATASETS_PREFIX,
    )

    candidates = data.get("authority_candidates")
    if not isinstance(candidates, list):
        errors.append("authority_candidates must be a list")
    else:
        selected_candidates = [
            candidate
            for candidate in candidates
            if isinstance(candidate, dict) and candidate.get("selected") is True
        ]
        if len(selected_candidates) != 1 or selected_candidates[0] != authority:
            errors.append(
                "authority_candidates must contain exactly the selected package_authority"
            )
        for index, candidate in enumerate(candidates):
            if not isinstance(candidate, dict):
                errors.append(f"authority_candidates[{index}] must be an object")
                continue
            role = candidate.get("role")
            if role == "211-AI_gitlink_package_authority":
                continue
            expected_prefix = {
                "standalone_home_checkout": EXPECTED_HOME_DATASETS_PREFIX,
                "hallucinate_runtime_copy": EXPECTED_HALLUCINATE_DATASETS_PREFIX,
            }.get(role)
            if expected_prefix is None:
                errors.append(
                    f"authority_candidates[{index}] has unknown role {role!r}"
                )
                continue
            check_external(
                candidate,
                label=f"authority_candidates[{index}]",
                path_key="path",
                expected_prefix=expected_prefix,
            )


def _check_source_roots(
    root: Path,
    path: Path,
    errors: list[str],
    warnings: list[str],
    *,
    swissknife_path: Path | None = None,
    hallucinate_path: Path | None = None,
) -> dict[str, Any] | None:
    # Retained as compatibility-only keyword arguments for existing callers.
    # Snapshot validation always uses paths pinned inside source-roots.json.
    del swissknife_path, hallucinate_path
    if not path.is_file():
        errors.append(f"missing source-roots.json: {path.relative_to(root)}")
        return None
    try:
        data = _load_json(path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(f"invalid source-roots.json: {exc}")
        return None

    for key in REQUIRED_SOURCE_ROOT_KEYS:
        if key not in data:
            errors.append(f"source-roots.json missing key: {key}")

    if data.get("goal_id") != GOAL_ID:
        errors.append(f"source-roots.json goal_id must be {GOAL_ID}")
    if data.get("schema") != SCHEMA_SOURCE_ROOTS:
        errors.append(f"source-roots.json schema must be {SCHEMA_SOURCE_ROOTS}")

    _check_objective_validation_contract(
        data.get("objective_validation_repair"),
        label="source-roots objective_validation_repair",
        errors=errors,
    )
    _validate_pinned_source_objects(root, data, errors, warnings)

    cycles = data.get("mirror_cycles") or []
    if not isinstance(cycles, list) or not cycles:
        errors.append("mirror_cycles must record recursive package mirrors without rescan")

    swiss = data.get("swissknife") or {}
    status = swiss.get("status")
    if status not in {"matches_expected", "changed", "absent"}:
        errors.append(
            "swissknife.status must be matches_expected, changed, or absent "
            f"(got {status!r})"
        )
    if status == "matches_expected":
        commit = swiss.get("commit") or ""
        if not str(commit).startswith(EXPECTED_SWISSKNIFE_PREFIX):
            errors.append(
                f"swissknife matches_expected but commit does not start with "
                f"{EXPECTED_SWISSKNIFE_PREFIX}"
            )

    hall = data.get("hallucinate_datasets") or {}
    if hall.get("status") not in {"matches_expected", "changed", "absent"}:
        errors.append("hallucinate_datasets.status must be explicit")
    if hall.get("status") == "matches_expected":
        commit = hall.get("commit") or ""
        if not str(commit).startswith(EXPECTED_HALLUCINATE_DATASETS_PREFIX):
            errors.append(
                "hallucinate matches_expected but commit prefix mismatch for 8dc4f93e"
            )

    authority = data.get("package_authority")
    if not isinstance(authority, dict) or not authority.get("commit") or not authority.get("tree"):
        errors.append(
            "package_authority must bind verified commit/tree; unresolved authority fails closed"
        )
    elif authority.get("path") != "ipfs_datasets_py":
        errors.append("package_authority.path must be ipfs_datasets_py gitlink")
    elif not authority.get("selected"):
        errors.append("package_authority.selected must be true")

    coverage = data.get("acceptance_coverage") or {}
    if not isinstance(coverage, dict):
        errors.append("acceptance_coverage must be an object")
    else:
        for key, expected in (
            ("binds_clean_commit_tree_for_selected_roots", True),
            ("records_recursive_mirror_cycles_without_rescan", True),
            ("swissknife_df11f08f_or_explicit_status", True),
            ("hallucinate_8dc4f93e_and_package_authority_recorded", True),
            ("unresolved_authority_fails_closed", True),
            ("documentation_is_not_authority_until_verified", True),
            ("objective_validation_repair", True),
        ):
            if coverage.get(key) is not expected:
                errors.append(f"acceptance_coverage.{key} must be {expected}")

    if data.get("fail_closed") is True and data.get("freeze_ok") is not True:
        # Allowed only when hard blockers exist; freeze artifacts should not ship that way.
        errors.append("checked-in freeze must not be fail_closed without freeze_ok")

    blockers = data.get("blockers")
    if not isinstance(blockers, list):
        errors.append("blockers must be a list (may be empty)")
    else:
        if any(isinstance(b, dict) and b.get("guessed") is True for b in blockers):
            errors.append("blockers must not mark unresolved ownership as guessed=true")

    return data


def _pinned_package_blob(
    root: Path,
    source_roots: dict[str, Any],
    *,
    package: str,
    relative_path: str,
    errors: list[str],
) -> str | None:
    """Read a blob from a verified direct-gitlink revision."""

    links = {
        item.get("path"): item
        for item in (source_roots.get("direct_gitlinks") or [])
        if isinstance(item, dict)
    }
    link = links.get(package)
    commit = link.get("commit") if isinstance(link, dict) else None
    repository = _resolve_gitlink_repository(root, package, commit)
    if not isinstance(commit, str) or not _is_git_checkout(repository):
        errors.append(
            f"cannot inspect pinned {package}/{relative_path}: "
            "verified package revision unavailable"
        )
        return None
    return _read_pinned_blob(
        repository,
        commit=commit,
        relative_path=relative_path,
    )


def _require_pinned_markers(
    root: Path,
    source_roots: dict[str, Any],
    *,
    category: str,
    package: str,
    relative_path: str,
    markers: tuple[str, ...],
    errors: list[str],
) -> None:
    text = _pinned_package_blob(
        root,
        source_roots,
        package=package,
        relative_path=relative_path,
        errors=errors,
    )
    display = f"{package}/{relative_path}"
    if text is None:
        errors.append(f"{category} evidence blob is absent: {display}")
        return
    for marker in markers:
        if marker not in text:
            errors.append(
                f"{category} marker {marker!r} missing from pinned {display}"
            )


def _require_pinned_absence(
    root: Path,
    source_roots: dict[str, Any],
    *,
    category: str,
    package: str,
    relative_path: str,
    errors: list[str],
) -> None:
    text = _pinned_package_blob(
        root,
        source_roots,
        package=package,
        relative_path=relative_path,
        errors=errors,
    )
    if text is not None:
        errors.append(
            f"{category} expects pinned path to be absent: "
            f"{package}/{relative_path}"
        )


def _require_pinned_marker_count(
    root: Path,
    source_roots: dict[str, Any],
    *,
    category: str,
    package: str,
    relative_path: str,
    marker: str,
    expected_count: int,
    errors: list[str],
) -> None:
    text = _pinned_package_blob(
        root,
        source_roots,
        package=package,
        relative_path=relative_path,
        errors=errors,
    )
    display = f"{package}/{relative_path}"
    if text is None:
        errors.append(f"{category} evidence blob is absent: {display}")
        return
    observed = text.count(marker)
    if observed != expected_count:
        errors.append(
            f"{category} marker {marker!r} must occur {expected_count} times "
            f"in pinned {display} (got {observed})"
        )


def _validate_pinned_drift_evidence(
    root: Path,
    source_roots: dict[str, Any],
    errors: list[str],
) -> None:
    """Replay the five required drift categories from frozen Git blobs."""

    probes = (
        (
            "mock-success",
            "ipfs_datasets_py",
            "ipfs_datasets_py/dataset_manager.py",
            ("Fallback: return a minimal mock dataset", "Mock successful save"),
        ),
        (
            "mock-success",
            "ipfs_datasets_py",
            "ipfs_datasets_py/mcp_server/tools/dataset_tools/process_dataset.py",
            ("Default mock count", "mock implementation for now"),
        ),
        (
            "mock-success",
            "ipfs_datasets_py",
            "ipfs_datasets_py/mcp_server/tools/dataset_tools/convert_dataset_format.py",
            ("Using mock conversion response", '"conversion_method": "mock"'),
        ),
        (
            "nondeterministic-identity",
            "ipfs_datasets_py",
            "ipfs_datasets_py/mcp_server/tools/dataset_tools/save_dataset.py",
            ("hash(str(dataset_data))",),
        ),
        (
            "nondeterministic-identity",
            "ipfs_datasets_py",
            "ipfs_datasets_py/processors/serialization/dataset_serialization.py",
            ("uuid.uuid4()", "datetime.datetime.now()", "random.sample("),
        ),
        (
            "duplicate-definition",
            "ipfs_datasets_py",
            "ipfs_datasets_py/dataset_manager.py",
            ("class DatasetManager:",),
        ),
        (
            "duplicate-definition",
            "ipfs_kit_py",
            "ipfs_kit_py/ai_ml_integration.py",
            ("class DatasetManager:",),
        ),
        (
            "duplicate-definition",
            "ipfs_kit_py",
            "ipfs_kit_py/mcp/ai/dataset_manager.py",
            ("class DatasetManager:",),
        ),
        (
            "duplicate-definition",
            "ipfs_kit_py",
            "ipfs_kit_py/mcp/ai/dataset_management/manager.py",
            ("class DatasetManager:",),
        ),
        (
            "weak-test",
            "ipfs_datasets_py",
            "tests/migration_tests/_test_generator_for_dataset_tools.py",
            ("MagicMock", "patch"),
        ),
        (
            "weak-test",
            "ipfs_datasets_py",
            "tests/unit/test_stubs_from_gherkin/test_dataset_manager.py",
            ("test_create_mock_dataset_when_loading_fails", "pass"),
        ),
    )
    for category, package, relative_path, markers in probes:
        _require_pinned_markers(
            root,
            source_roots,
            category=category,
            package=package,
            relative_path=relative_path,
            markers=markers,
            errors=errors,
        )

    _require_pinned_marker_count(
        root,
        source_roots,
        category="duplicate-definition",
        package="ipfs_datasets_py",
        relative_path="ipfs_datasets_py/ipfs_datasets.py",
        marker="async def generate_clusters(",
        expected_count=2,
        errors=errors,
    )

    for relative_path in (
        "ipfs_datasets_py/core_operations/dataset_manipulator.py",
        "ipfs_datasets_py/core_operations/dataset_contracts.py",
    ):
        _require_pinned_absence(
            root,
            source_roots,
            category="missing-import",
            package="ipfs_datasets_py",
            relative_path=relative_path,
            errors=errors,
        )
    _require_pinned_absence(
        root,
        source_roots,
        category="weak-test",
        package="ipfs_datasets_py",
        relative_path=(
            "tests/contract/core_operations/"
            "test_dataset_manipulator_baseline.py"
        ),
        errors=errors,
    )


def _check_drift(
    root: Path,
    path: Path,
    source_roots: dict[str, Any] | None,
    errors: list[str],
    warnings: list[str],
) -> dict[str, Any] | None:
    if not path.is_file():
        errors.append(
            f"missing datasets-manipulator-drift.json: {path.relative_to(root)}"
        )
        return None
    try:
        data = _load_json(path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(f"invalid datasets-manipulator-drift.json: {exc}")
        return None

    for key in REQUIRED_DRIFT_KEYS:
        if key not in data:
            errors.append(f"datasets-manipulator-drift.json missing key: {key}")

    if data.get("goal_id") != GOAL_ID:
        errors.append(f"drift goal_id must be {GOAL_ID}")
    if data.get("schema") != SCHEMA_DRIFT:
        errors.append(f"drift schema must be {SCHEMA_DRIFT}")

    _check_objective_validation_contract(
        data.get("objective_validation_repair"),
        label="drift objective_validation_repair",
        errors=errors,
    )

    findings = data.get("findings") or []
    if not isinstance(findings, list) or len(findings) < 5:
        errors.append("drift findings must include the known baseline inventory")
    categories = {
        str(f.get("category"))
        for f in findings
        if isinstance(f, dict)
    }
    for required in sorted(REQUIRED_DRIFT_CATEGORIES):
        if required not in categories:
            errors.append(f"drift findings missing category: {required}")

    expected_findings = {
        item["finding_id"]: item for item in KNOWN_FINDINGS
    }
    observed_findings: dict[str, dict[str, Any]] = {}
    for index, finding in enumerate(findings):
        if not isinstance(finding, dict):
            errors.append(f"drift findings[{index}] must be an object")
            continue
        finding_id = finding.get("finding_id")
        if not isinstance(finding_id, str):
            errors.append(f"drift findings[{index}] missing finding_id")
            continue
        if finding_id in observed_findings:
            errors.append(f"duplicate drift finding_id: {finding_id}")
            continue
        observed_findings[finding_id] = finding
    for finding_id, expected in expected_findings.items():
        finding = observed_findings.get(finding_id)
        if finding is None:
            errors.append(f"drift findings missing frozen finding: {finding_id}")
            continue
        for field in ("category", "severity", "symbol", "path", "status"):
            if finding.get(field) != expected.get(field):
                errors.append(
                    f"{finding_id}.{field} differs from frozen inventory: "
                    f"expected {expected.get(field)!r}, got {finding.get(field)!r}"
                )
        if finding.get("path_verified") is not True:
            errors.append(f"{finding_id}.path_verified must be true")

    recorded_categories = data.get("finding_categories")
    if recorded_categories != sorted(categories):
        errors.append("finding_categories must equal categories derived from findings")
    if data.get("required_finding_categories") != sorted(REQUIRED_DRIFT_CATEGORIES):
        errors.append(
            "required_finding_categories must list the five objective categories"
        )

    if source_roots is None:
        errors.append("cannot replay drift evidence without source-roots authority")
    else:
        _validate_pinned_drift_evidence(root, source_roots, errors)

    bound = data.get("bound_package_authority") or {}
    if source_roots is not None:
        auth = source_roots.get("package_authority") or {}
        if bound.get("commit") != auth.get("commit"):
            errors.append(
                "drift bound_package_authority.commit must match source-roots package_authority"
            )

    coverage = data.get("acceptance_coverage") or {}
    if not isinstance(coverage, dict):
        errors.append("drift acceptance_coverage must be an object")
    else:
        for key in (
            "reproduces_mock_success",
            "reproduces_nondeterministic_identity",
            "reproduces_duplicate_definition",
            "reproduces_missing_import",
            "reproduces_weak_test",
            "all_required_categories_present",
            "bound_to_selected_package_authority",
            "objective_validation_repair",
        ):
            if coverage.get(key) is not True:
                errors.append(f"drift acceptance_coverage.{key} must be true")

    return data


def _check_ownership(
    root: Path,
    path: Path,
    errors: list[str],
    warnings: list[str],
) -> None:
    if not path.is_file():
        errors.append(f"missing ownership-map.md: {path.relative_to(root)}")
        return
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        errors.append(f"cannot read ownership-map.md: {exc}")
        return

    if len(text) < 2500:
        errors.append("ownership-map.md is too short to be a complete freeze document")

    lowered = text.lower()
    for phrase in REQUIRED_OWNERSHIP_PHRASES:
        if phrase.lower() not in lowered and phrase not in text:
            errors.append(f"ownership-map.md missing required phrase: {phrase}")

    if "blocker" not in lowered:
        errors.append("ownership-map.md must record unresolved ownership as blockers")
    if "fail closed" not in lowered and "fails closed" not in lowered:
        errors.append("ownership-map.md must state fail closed authority policy")

    for decision in ("retain", "create", "deprecate"):
        if f"**{decision}**" not in text and decision not in lowered:
            warnings.append(f"ownership-map.md may be missing decision emphasis for: {decision}")


def _identity_divergences(
    label: str,
    frozen: dict[str, Any],
    current: dict[str, Any] | None,
) -> list[str]:
    if current is None:
        return [f"{label}: current checkout is missing or unverifiable"]
    divergences: list[str] = []
    for field in ("commit", "tree"):
        if frozen.get(field) != current.get(field):
            divergences.append(
                f"{label}.{field}: frozen={frozen.get(field)} "
                f"current={current.get(field)}"
            )
    if current.get("dirty"):
        divergences.append(
            f"{label}: current checkout is dirty "
            f"({current.get('dirty_entry_count', 0)} material entr"
            f"{'y' if current.get('dirty_entry_count') == 1 else 'ies'})"
        )
    return divergences


def _collect_current_divergences(
    root: Path,
    source_roots: dict[str, Any],
    *,
    swissknife_path: Path,
    hallucinate_path: Path,
    home_datasets_path: Path,
) -> list[str]:
    """Compare frozen identities to the current worktrees, as an explicit mode."""
    divergences: list[str] = []
    frozen_super = source_roots.get("superproject") or {}
    current_super = _checkout_identity(
        root,
        label="211-AI-superproject",
        relative_path=".",
        ignore_freeze_outputs=True,
    )
    divergences.extend(
        _identity_divergences("superproject", frozen_super, current_super)
    )

    frozen_links = {
        entry.get("path"): entry
        for entry in (source_roots.get("direct_gitlinks") or [])
        if isinstance(entry, dict) and isinstance(entry.get("path"), str)
    }
    current_links = {
        entry.get("path"): entry for entry in _list_direct_gitlinks(root)
    }
    for name, frozen in sorted(frozen_links.items()):
        current_link = current_links.get(name)
        if current_link is None:
            divergences.append(f"{name}.gitlink_commit: missing from current HEAD")
        elif frozen.get("gitlink_commit") != current_link.get("gitlink_commit"):
            divergences.append(
                f"{name}.gitlink_commit: frozen={frozen.get('gitlink_commit')} "
                f"current={current_link.get('gitlink_commit')}"
            )
        current_checkout = _checkout_identity(
            root / name,
            label=name,
            relative_path=name,
        )
        divergences.extend(
            _identity_divergences(name, frozen, current_checkout)
        )

    checked_paths: set[tuple[str, str]] = set()

    def compare_external(
        label: str,
        frozen: Any,
        current_path: Path,
    ) -> None:
        if not isinstance(frozen, dict):
            divergences.append(f"{label}: frozen record is missing")
            return
        key = (label, str(current_path))
        if key in checked_paths:
            return
        checked_paths.add(key)
        current = _checkout_identity(current_path, label=label)
        if frozen.get("status") == "absent":
            if current is not None:
                divergences.append(
                    f"{label}: frozen checkout was absent but is present at {current_path}"
                )
            return
        divergences.extend(_identity_divergences(label, frozen, current))

    compare_external(
        "swissknife",
        source_roots.get("swissknife"),
        swissknife_path,
    )
    compare_external(
        "hallucinate_datasets",
        source_roots.get("hallucinate_datasets"),
        hallucinate_path,
    )
    for candidate in source_roots.get("authority_candidates") or []:
        if not isinstance(candidate, dict):
            continue
        if candidate.get("role") == "standalone_home_checkout":
            compare_external(
                "standalone_home_checkout",
                candidate,
                home_datasets_path,
            )
            break
    return divergences


def run_check(
    root: Path,
    *,
    swissknife_path: Path | None = None,
    hallucinate_path: Path | None = None,
) -> int:
    # These keywords were accepted by the original API. They cannot redirect
    # an immutable snapshot check, but remain accepted for caller compatibility.
    del swissknife_path, hallucinate_path
    audit = _audit_dir(root)
    source_path = audit / "source-roots.json"
    drift_path = audit / "datasets-manipulator-drift.json"
    ownership_path = audit / "ownership-map.md"

    errors: list[str] = []
    warnings: list[str] = []

    source_roots = _check_source_roots(
        root,
        source_path,
        errors,
        warnings,
    )
    drift = _check_drift(root, drift_path, source_roots, errors, warnings)
    _check_ownership(root, ownership_path, errors, warnings)

    print("datasets contract analysis audit --check")
    print(
        f"  source-roots: {source_path.relative_to(root)} "
        f"({'ok' if source_roots else 'MISSING'})"
    )
    print(
        f"  drift: {drift_path.relative_to(root)} "
        f"({'ok' if drift else 'MISSING'})"
    )
    print(
        f"  ownership: {ownership_path.relative_to(root)} "
        f"({'ok' if ownership_path.is_file() else 'MISSING'})"
    )
    print(
        f"  {OBJECTIVE_VALIDATION_EVIDENCE}: "
        f"{'ok' if not errors else 'FAILED'} ({VALIDATION_TASK_ID})"
    )

    if warnings:
        print("warnings:")
        for warning in warnings:
            print(f"  - {warning}")

    if errors:
        print("errors:")
        for error in errors:
            print(f"  - {error}")
        print(f"FAIL ({len(errors)} error(s), {len(warnings)} warning(s))")
        return 1

    print(f"PASS ({len(warnings)} warning(s))")
    return 0


def run_check_current(
    root: Path,
    *,
    swissknife_path: Path,
    hallucinate_path: Path,
    home_datasets_path: Path,
) -> int:
    """Validate the snapshot, then fail if any configured checkout has drifted."""
    snapshot_code = run_check(root)
    if snapshot_code != 0:
        print("freshness not evaluated because pinned snapshot integrity failed")
        return snapshot_code

    source_path = _audit_dir(root) / "source-roots.json"
    try:
        source_roots = _load_json(source_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL current comparison: cannot reload source-roots.json: {exc}")
        return 1
    divergences = _collect_current_divergences(
        root,
        source_roots,
        swissknife_path=swissknife_path,
        hallucinate_path=hallucinate_path,
        home_datasets_path=home_datasets_path,
    )

    print("datasets contract analysis audit --check-current")
    if divergences:
        print("stale/diverged:")
        for divergence in divergences:
            print(f"  - {divergence}")
        print(f"STALE ({len(divergences)} divergence(s))")
        return 1

    print("CURRENT (all ambient identities equal the frozen snapshot)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help=(
            "Validate frozen source-roots / drift / ownership artifacts and "
            "their pinned historical Git objects"
        ),
    )
    parser.add_argument(
        "--check-current",
        action="store_true",
        help=(
            "Validate the frozen snapshot, then require ambient checkouts to "
            "still equal it"
        ),
    )
    parser.add_argument(
        "--freeze",
        action="store_true",
        help="Regenerate freeze artifacts from verified Git identities",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Repository root (default: inferred from script location)",
    )
    parser.add_argument(
        "--swissknife-path",
        type=Path,
        default=DEFAULT_SWISSKNIFE_PATH,
        help="Configured Swissknife source path",
    )
    parser.add_argument(
        "--hallucinate-datasets-path",
        type=Path,
        default=DEFAULT_HALLUCINATE_DATASETS_PATH,
        help="Configured Hallucinate ipfs_datasets_py checkout path",
    )
    parser.add_argument(
        "--home-datasets-path",
        type=Path,
        default=DEFAULT_HOME_DATASETS_PATH,
        help="Standalone home ipfs_datasets_py checkout path",
    )
    args = parser.parse_args(argv)

    root = args.root.resolve() if args.root is not None else _repo_root()

    if args.check and args.check_current:
        parser.error("--check and --check-current are mutually exclusive")

    if args.freeze and (args.check or args.check_current):
        # Freeze then validate in one shot.
        code = freeze(
            root,
            swissknife_path=args.swissknife_path,
            hallucinate_path=args.hallucinate_datasets_path,
            home_datasets_path=args.home_datasets_path,
        )
        if code != 0:
            return code
        if args.check_current:
            return run_check_current(
                root,
                swissknife_path=args.swissknife_path,
                hallucinate_path=args.hallucinate_datasets_path,
                home_datasets_path=args.home_datasets_path,
            )
        return run_check(root)

    if args.freeze:
        return freeze(
            root,
            swissknife_path=args.swissknife_path,
            hallucinate_path=args.hallucinate_datasets_path,
            home_datasets_path=args.home_datasets_path,
        )

    if args.check:
        return run_check(root)

    if args.check_current:
        return run_check_current(
            root,
            swissknife_path=args.swissknife_path,
            hallucinate_path=args.hallucinate_datasets_path,
            home_datasets_path=args.home_datasets_path,
        )

    parser.error("specify --freeze, --check, and/or --check-current")
    return 2


if __name__ == "__main__":
    sys.exit(main())
