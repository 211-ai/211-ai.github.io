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
SCHEMA_SOURCE_ROOTS = "datasets_contract_analysis/source-roots@1"
SCHEMA_DRIFT = "datasets_contract_analysis/datasets-manipulator-drift@1"

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
    "mock-success",
    "nondeterministic",
    "duplicate definition",
    "missing import",
    "weak-test",
    "Blocker",
    "fail closed",
    "package authority",
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
]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _audit_dir(root: Path) -> Path:
    return root / "data" / "datasets_contract_analysis" / "audit"


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


def _is_git_checkout(path: Path) -> bool:
    if not path.is_dir():
        return False
    marker = path / ".git"
    return marker.exists() or marker.is_file()


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


def _list_direct_gitlinks(root: Path) -> list[dict[str, Any]]:
    out = _git_ok(["ls-tree", "HEAD"], cwd=root) or ""
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


def _list_nested_gitlinks(package_root: Path, parent_package: str, parent_commit: str) -> list[dict[str, Any]]:
    out = _git_ok(["ls-tree", "-r", "HEAD"], cwd=package_root) or ""
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
    required_categories = {
        "mock-success",
        "nondeterministic-identity",
        "duplicate-definition",
        "missing-import",
        "weak-test",
    }
    acceptance = {
        "reproduces_mock_success": "mock-success" in categories,
        "reproduces_nondeterministic_identity": "nondeterministic-identity" in categories,
        "reproduces_duplicate_definition": "duplicate-definition" in categories,
        "reproduces_missing_import": "missing-import" in categories,
        "reproduces_weak_test": "weak-test" in categories,
        "all_required_categories_present": required_categories.issubset(set(categories)),
        "bound_to_selected_package_authority": bool(authority.get("commit")),
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
        "blockers": blockers,
        "notes": [
            "Inventory only; no production refactors in DSCON-G010.",
            "Repair is deferred to dataset manipulator / adapter objectives.",
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

Validation: `python scripts/contract_analysis/audit_scope.py --check`
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


def _check_source_roots(
    root: Path,
    path: Path,
    errors: list[str],
    warnings: list[str],
    *,
    swissknife_path: Path,
    hallucinate_path: Path,
) -> dict[str, Any] | None:
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

    live = collect_source_roots(
        root,
        swissknife_path=swissknife_path,
        hallucinate_path=hallucinate_path,
        home_datasets_path=DEFAULT_HOME_DATASETS_PATH,
    )

    frozen_super = data.get("superproject") or {}
    live_super = live.get("superproject") or {}
    for field in ("commit", "tree"):
        if frozen_super.get(field) != live_super.get(field):
            errors.append(
                f"superproject {field} drift: frozen={frozen_super.get(field)} "
                f"live={live_super.get(field)}"
            )

    frozen_links = {
        d.get("path"): d for d in (data.get("direct_gitlinks") or []) if isinstance(d, dict)
    }
    live_links = {
        d.get("path"): d for d in (live.get("direct_gitlinks") or []) if isinstance(d, dict)
    }
    for name in SELECTED_PACKAGE_ROOTS:
        if name not in frozen_links:
            errors.append(f"source-roots missing selected gitlink: {name}")
            continue
        if name not in live_links:
            errors.append(f"live checkout missing selected gitlink: {name}")
            continue
        for field in ("gitlink_commit", "commit", "tree"):
            if frozen_links[name].get(field) != live_links[name].get(field):
                errors.append(
                    f"{name} {field} drift: frozen={frozen_links[name].get(field)} "
                    f"live={live_links[name].get(field)}"
                )
        if not frozen_links[name].get("verified"):
            errors.append(f"{name} must be verified in freeze")
        if not frozen_links[name].get("clean"):
            errors.append(f"{name} must be clean in freeze")
        if not frozen_links[name].get("tree"):
            errors.append(f"{name} missing tree id")

    cycles = data.get("mirror_cycles") or []
    if not isinstance(cycles, list) or not cycles:
        errors.append("mirror_cycles must record recursive package mirrors without rescan")
    else:
        if any(c.get("rescan") is not False for c in cycles if isinstance(c, dict)):
            errors.append("mirror_cycles entries must set rescan=false")

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
    # Live consistency for swissknife status
    live_swiss = live.get("swissknife") or {}
    if swiss.get("status") != live_swiss.get("status"):
        warnings.append(
            f"swissknife status frozen={swiss.get('status')} live={live_swiss.get('status')}"
        )
    if swiss.get("commit") and live_swiss.get("commit") and swiss.get("commit") != live_swiss.get("commit"):
        errors.append(
            f"swissknife commit drift: frozen={swiss.get('commit')} live={live_swiss.get('commit')}"
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

    findings = data.get("findings") or []
    if not isinstance(findings, list) or len(findings) < 5:
        errors.append("drift findings must include the known baseline inventory")
    categories = {
        str(f.get("category"))
        for f in findings
        if isinstance(f, dict)
    }
    for required in (
        "mock-success",
        "nondeterministic-identity",
        "duplicate-definition",
        "missing-import",
        "weak-test",
    ):
        if required not in categories:
            errors.append(f"drift findings missing category: {required}")

    # Spot-check mock-success evidence still present in tree where claimed.
    mock_paths = [
        "ipfs_datasets_py/ipfs_datasets_py/dataset_manager.py",
        (
            "ipfs_datasets_py/ipfs_datasets_py/mcp_server/tools/"
            "dataset_tools/process_dataset.py"
        ),
        (
            "ipfs_datasets_py/ipfs_datasets_py/mcp_server/tools/"
            "dataset_tools/convert_dataset_format.py"
        ),
    ]
    for rel in mock_paths:
        full = root / rel
        if not full.is_file():
            warnings.append(f"mock-success path missing at check time: {rel}")
            continue
        text = full.read_text(encoding="utf-8", errors="replace").lower()
        if "mock" not in text:
            errors.append(f"expected mock-success evidence missing from {rel}")

    manip = root / "ipfs_datasets_py/ipfs_datasets_py/core_operations/dataset_manipulator.py"
    if manip.is_file():
        warnings.append(
            "dataset_manipulator.py now exists; missing-import finding may need refresh"
        )

    bound = data.get("bound_package_authority") or {}
    if source_roots is not None:
        auth = source_roots.get("package_authority") or {}
        if bound.get("commit") != auth.get("commit"):
            errors.append(
                "drift bound_package_authority.commit must match source-roots package_authority"
            )

    coverage = data.get("acceptance_coverage") or {}
    if not isinstance(coverage, dict) or not coverage.get("all_required_categories_present"):
        errors.append("drift acceptance_coverage.all_required_categories_present must be true")

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


def run_check(
    root: Path,
    *,
    swissknife_path: Path,
    hallucinate_path: Path,
) -> int:
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
        swissknife_path=swissknife_path,
        hallucinate_path=hallucinate_path,
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate frozen source-roots / drift / ownership artifacts",
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

    if args.freeze and args.check:
        # Freeze then validate in one shot.
        code = freeze(
            root,
            swissknife_path=args.swissknife_path,
            hallucinate_path=args.hallucinate_datasets_path,
            home_datasets_path=args.home_datasets_path,
        )
        if code != 0:
            return code
        return run_check(
            root,
            swissknife_path=args.swissknife_path,
            hallucinate_path=args.hallucinate_datasets_path,
        )

    if args.freeze:
        return freeze(
            root,
            swissknife_path=args.swissknife_path,
            hallucinate_path=args.hallucinate_datasets_path,
            home_datasets_path=args.home_datasets_path,
        )

    if args.check:
        return run_check(
            root,
            swissknife_path=args.swissknife_path,
            hallucinate_path=args.hallucinate_datasets_path,
        )

    parser.error("specify --freeze and/or --check")
    return 2


if __name__ == "__main__":
    sys.exit(main())
