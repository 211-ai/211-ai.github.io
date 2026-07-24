#!/usr/bin/env python3
"""Verify a human-signed World Human Aid Gate 0B approval offline.

The verifier is deliberately dependency-free. It validates the strict record
contract, repository-relative artifact digests, the reviewed local git state,
and one detached OpenSSH signature per required role. It never creates an
approval and never treats an unsigned template as approval.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import errno
import hashlib
import json
import os
import platform
import re
import shlex
import stat
import subprocess
import sys
from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path, PurePosixPath
from typing import Any

SELECTION = "selection"
LAUNCH = "launch"

CANONICAL_APPROVAL_PATHS = {
    SELECTION: Path("data/worldcoin_human_aid/approvals/gate-0b-selection/approval.json"),
    LAUNCH: Path("data/worldcoin_human_aid/approvals/gate-0b-launch/approval.json"),
}

SCHEMA_VERSIONS = {
    SELECTION: "world-human-aid-gate-0b-selection/v1",
    LAUNCH: "world-human-aid-gate-0b-launch/v1",
}

GATE_IDS = {
    SELECTION: "gate-0b-selection",
    LAUNCH: "gate-0b-launch",
}

SIGNATURE_NAMESPACES = {
    SELECTION: "world-aid-gate-0b-selection-v1",
    LAUNCH: "world-aid-gate-0b-launch-v1",
}

REQUIRED_ROLES = {
    SELECTION: frozenset(
        {
            "product-owner",
            "privacy-reviewer",
            "program-policy-owner",
            "accessibility-reviewer",
            "repository-maintainer",
            "supply-chain-maintainer",
            "cryptography-reviewer",
            "storage-security-reviewer",
            "security-reviewer",
        }
    ),
    LAUNCH: frozenset(
        {
            "product-owner",
            "security-reviewer",
            "privacy-reviewer",
            "program-policy-owner",
            "accessibility-reviewer",
            "repository-maintainer",
            "supply-chain-maintainer",
            "cryptography-reviewer",
            "storage-security-reviewer",
        }
    ),
}

SELECTION_GOALS = frozenset({"WORLDCOIN-G038", "WORLDCOIN-G039", "WORLDCOIN-G040"})
FORBIDDEN_GOALS = frozenset({"WORLDCOIN-G035", "WORLDCOIN-G036"})
LAUNCH_PREREQUISITE_GOALS = frozenset(
    {
        "WORLDCOIN-G002",
        "WORLDCOIN-G037",
        "WORLDCOIN-G038",
        "WORLDCOIN-G039",
        "WORLDCOIN-G040",
        "WORLDCOIN-G041",
        "WORLDCOIN-G042",
    }
)
SELECTION_PREPARATION_GOALS = frozenset(
    {
        "WORLDCOIN-G002",
        "WORLDCOIN-G037",
        "WORLDCOIN-G041",
        "WORLDCOIN-G042",
    }
)
RESTRICTED_BOOTSTRAP_BUNDLES = frozenset(
    {
        "worldcoin-human-aid/siwe-offline-bootstrap",
        "worldcoin-human-aid/zkp-toolchain-bootstrap",
        "worldcoin-human-aid/duckdb-bootstrap",
    }
)
CANONICAL_SOURCE_PATHS = {
    "objective_heap": "docs/planning/WORLDCOIN_HUMAN_AID_OBJECTIVE_HEAP.md",
    "implementation_plan": "docs/planning/WORLDCOIN_HUMAN_AID_IMPLEMENTATION_PLAN.md",
    "runbook": "docs/planning/WORLDCOIN_HUMAN_AID_AGENT_SUPERVISOR_RUNBOOK.md",
    "storage_adr": "docs/adr/WORLD_AID_DUCKDB_STORAGE_ADR.md",
}
SELECTION_VERIFIER_CONTRACT_PATHS = {
    "siwe_verifier": "scripts/verify_world_siwe_offline_bootstrap.py",
    "siwe_runtime_test": "tests/world_aid/test_siwe_offline_bootstrap.py",
    "zkp_verifier": "scripts/verify_world_aid_zkp_toolchain.py",
    "zkp_runtime_test": "tests/world_aid/test_zkp_toolchain_bootstrap.py",
    "duckdb_verifier": "scripts/verify_world_aid_duckdb_bootstrap.py",
    "duckdb_runtime_test": "tests/world_aid/test_duckdb_bootstrap.py",
}
PROTECTED_WRITABLE_PATHS = frozenset(
    {
        *CANONICAL_SOURCE_PATHS.values(),
        *SELECTION_VERIFIER_CONTRACT_PATHS.values(),
        "data/worldcoin_human_aid/approvals",
        "wallet_interface/services/world_siwe_verifier/package.json",
        "wallet_interface/services/world_siwe_verifier/package-lock.json",
        "requirements-world-aid.lock",
        "wallet_interface/deploy/world-aid-duckdb-runtime.yml",
        "docs/specs/WORLD_AID_DUCKDB_BACKUP.md",
        "tests/world_aid/fixtures/zkp_toolchain_smoke/Nargo.lock",
        "tests/world_aid/fixtures/zkp_toolchain_smoke/src/main.nr",
    }
)
BOOTSTRAP_RECEIPT_PATHS = {
    "siwe": "data/worldcoin_human_aid/bootstrap/world-siwe-offline-smoke.fixture.json",
    "zkp": "data/worldcoin_human_aid/bootstrap/zkp-toolchain-smoke.fixture.json",
    "duckdb": "data/worldcoin_human_aid/bootstrap/duckdb-offline-smoke.fixture.json",
}
BOOTSTRAP_GOALS = {
    "siwe": "WORLDCOIN-G038",
    "zkp": "WORLDCOIN-G039",
    "duckdb": "WORLDCOIN-G040",
}
SECURITY_EVIDENCE_FILENAMES = {
    "network_deny_canary": "network-deny-canary.json",
    "egress_policy": "egress-policy-attestation.json",
    "no_live_secrets_attestation": "no-live-secrets-attestation.json",
}
GENERATED_ROOT_PREFIX = Path("data/worldcoin_human_aid/agent_supervisor/regenerations")
PREFLIGHT_RECEIPT_SCHEMA = "world_aid.generated_board_preflight_receipt@1"
DRY_RUN_SCHEMAS = frozenset(
    {
        "ipfs_accelerate_py.agent_supervisor.bundle_supervisor",
        "ipfs_accelerate_py.agent_supervisor.dynamic_bundle_scheduler@1",
    }
)
SCHEDULABLE_GOAL_STATES = frozenset({"active", "provisionally_complete", "analysis_inconclusive", "reopened"})
REQUIRED_FORBIDDEN_ACTIONS = frozenset(
    {
        "world-api-call",
        "chain-broadcast",
        "token-transfer",
        "contract-deployment",
        "allowance-change",
        "live-secret-access",
        "package-registry-access",
        "container-registry-access",
    }
)
REQUIRED_FEATURE_FLAGS = {
    "WORLD_ID_ENABLED": "0",
    "WORLD_AID_EXTERNAL_CALLS_ENABLED": "0",
    "WORLD_AID_WLD_TRANSFERS_ENABLED": "0",
}

UTC_TIMESTAMP_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
GOAL_RE = re.compile(r"^WORLDCOIN-G[0-9]{3}$")
RECORD_ID_RE = {
    SELECTION: re.compile(r"^gate-0b-selection-[a-z0-9][a-z0-9._-]{7,95}$"),
    LAUNCH: re.compile(r"^gate-0b-launch-[a-z0-9][a-z0-9._-]{7,95}$"),
}
IDENTITY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9@._+-]{2,253}$")
FINGERPRINT_RE = re.compile(r"^SHA256:[A-Za-z0-9+/]{43}$")
SIGNATURE_FILE_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,63}\.sshsig$")
EXCEPTION_ID_RE = re.compile(r"^EX-[A-Z0-9][A-Z0-9_-]{2,31}$")
DUCKDB_EXTENSION_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
TRUSTED_GIT = Path("/usr/bin/git")
TRUSTED_SSH_KEYGEN = Path("/usr/bin/ssh-keygen")
ALLOWED_VALIDATION_EXECUTABLES = frozenset({"npm", "python", "test"})
ALLOWED_VALIDATION_ENV_ASSIGNMENTS = frozenset(
    {
        "PYTHONDONTWRITEBYTECODE=1",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD=1",
    }
)
ALLOWED_VALIDATION_PYTHON_SCRIPTS = frozenset(
    {
        "scripts/build_world_aid_eligibility_circuit.py",
        *(path for key, path in SELECTION_VERIFIER_CONTRACT_PATHS.items() if key.endswith("_verifier")),
    }
)
ALLOWED_VALIDATION_NPM_PREFIXES = frozenset(
    {
        "wallet_interface/services/world_siwe_verifier",
        "wallet_interface/ui",
    }
)
HOST_RE = re.compile(
    r"^(?:localhost|(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)(?:\.(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?))*|\[[0-9A-Fa-f:]+\])(?::[0-9]{1,5})?$"
)

FORBIDDEN_DESTINATION_FRAGMENTS = (
    "worldcoin",
    "world.org",
    "alchemy",
    "infura",
    "etherscan",
    "blockscout",
    "ipfs",
    "huggingface",
    "npmjs",
    "pypi",
    "docker.io",
    "ghcr.io",
    "quay.io",
)

MAX_RECORD_VALIDITY = timedelta(days=31)
MAX_EVIDENCE_AGE = timedelta(hours=24)


class ApprovalVerificationError(ValueError):
    """Raised when an approval fails closed."""


def _fail(message: str) -> None:
    raise ApprovalVerificationError(message)


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _fail(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _load_json_strict(path: Path, context: str = "approval") -> tuple[dict[str, Any], bytes]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        _fail(f"cannot read {context}: {exc}")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_pairs)
    except UnicodeDecodeError as exc:
        _fail(f"{context} is not UTF-8: {exc}")
    except json.JSONDecodeError as exc:
        _fail(f"{context} is not valid JSON: {exc}")
    if not isinstance(value, dict):
        _fail(f"{context} root must be an object")
    return value, raw


def _expect_object(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail(f"{context} must be an object")
    return value


def _expect_array(value: Any, context: str) -> list[Any]:
    if not isinstance(value, list):
        _fail(f"{context} must be an array")
    return value


def _expect_string(value: Any, context: str, *, minimum: int = 1, maximum: int = 4096) -> str:
    if not isinstance(value, str):
        _fail(f"{context} must be a string")
    if not minimum <= len(value) <= maximum:
        _fail(f"{context} has an invalid length")
    if "\x00" in value:
        _fail(f"{context} contains NUL")
    return value


def _expect_bool(value: Any, context: str) -> bool:
    if type(value) is not bool:
        _fail(f"{context} must be a boolean")
    return value


def _expect_int(value: Any, context: str, minimum: int, maximum: int) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        _fail(f"{context} must be an integer between {minimum} and {maximum}")
    return value


def _exact_keys(value: Mapping[str, Any], expected: Iterable[str], context: str) -> None:
    expected_set = set(expected)
    actual_set = set(value)
    missing = sorted(expected_set - actual_set)
    unknown = sorted(actual_set - expected_set)
    if missing or unknown:
        _fail(f"{context} keys differ; missing={missing}, unknown={unknown}")


def _unique_strings(
    value: Any,
    context: str,
    *,
    minimum_items: int = 0,
    maximum_items: int | None = None,
) -> list[str]:
    items = _expect_array(value, context)
    if len(items) < minimum_items or (maximum_items is not None and len(items) > maximum_items):
        _fail(f"{context} has an invalid item count")
    strings = [_expect_string(item, f"{context}[{index}]") for index, item in enumerate(items)]
    if len(strings) != len(set(strings)):
        _fail(f"{context} contains duplicates")
    return strings


def _parse_timestamp(value: Any, context: str) -> datetime:
    text = _expect_string(value, context, minimum=20, maximum=20)
    if not UTC_TIMESTAMP_RE.fullmatch(text):
        _fail(f"{context} must be an RFC 3339 UTC timestamp ending in Z")
    try:
        parsed = datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except ValueError as exc:
        _fail(f"{context} is not a real timestamp: {exc}")
    return parsed


def _sha256_bytes(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
    except OSError as exc:
        _fail(f"cannot hash {path}: {exc}")
    return f"sha256:{digest.hexdigest()}"


def _validate_relative_path_text(value: Any, context: str) -> str:
    text = _expect_string(value, context, maximum=512)
    if any(ord(character) < 32 or ord(character) == 127 for character in text):
        _fail(f"{context} cannot contain control characters")
    if "\\" in text or "//" in text:
        _fail(f"{context} must use a normalized POSIX repository-relative path")
    pure = PurePosixPath(text)
    if (
        not pure.parts
        or pure.is_absolute()
        or text.startswith("/")
        or text != pure.as_posix()
        or any(part in {"", ".", ".."} for part in pure.parts)
    ):
        _fail(f"{context} escapes or does not identify a normalized repository-relative path")
    return text


def _safe_repo_path(
    repo_root: Path,
    value: Any,
    context: str,
    *,
    must_exist: bool,
    require_file: bool = False,
    require_directory: bool = False,
) -> Path:
    text = _validate_relative_path_text(value, context)
    candidate = repo_root.joinpath(*Path(text).parts)

    current = repo_root
    for part in Path(text).parts:
        current = current / part
        # Path.exists() is false for a dangling symlink, so testing it first
        # would permit a committed dangling link in a future writable path.
        if current.is_symlink():
            _fail(f"{context} traverses a symlink")

    try:
        resolved = candidate.resolve(strict=must_exist)
        resolved.relative_to(repo_root)
    except (OSError, RuntimeError, ValueError) as exc:
        _fail(f"{context} escapes the repository or cannot be resolved: {exc}")

    if must_exist and not resolved.exists():
        _fail(f"{context} does not exist")
    if require_file and (not resolved.is_file() or resolved.is_symlink()):
        _fail(f"{context} must be a regular, non-symlink file")
    if require_directory and (not resolved.is_dir() or resolved.is_symlink()):
        _fail(f"{context} must be a regular, non-symlink directory")
    return resolved


def _canonical_approval_path(repo_root: Path, phase: str, approval_path: Path) -> Path:
    expected = repo_root / CANONICAL_APPROVAL_PATHS[phase]
    try:
        supplied_absolute = approval_path.absolute()
        expected_absolute = expected.absolute()
    except OSError as exc:
        _fail(f"cannot resolve approval path: {exc}")
    if supplied_absolute != expected_absolute:
        _fail(f"approval must use canonical path {CANONICAL_APPROVAL_PATHS[phase].as_posix()}")
    relative = CANONICAL_APPROVAL_PATHS[phase].as_posix()
    return _safe_repo_path(repo_root, relative, "approval path", must_exist=True, require_file=True)


def _validate_artifact_shape(value: Any, context: str) -> dict[str, str]:
    artifact = _expect_object(value, context)
    _exact_keys(artifact, {"path", "sha256"}, context)
    path = _validate_relative_path_text(artifact["path"], f"{context}.path")
    digest = _expect_string(artifact["sha256"], f"{context}.sha256", minimum=71, maximum=71)
    if not DIGEST_RE.fullmatch(digest):
        _fail(f"{context}.sha256 must be a lowercase sha256 digest")
    return {"path": path, "sha256": digest}


def _verify_artifact(
    repo_root: Path,
    artifact: dict[str, str],
    context: str,
    seen: dict[str, str],
    approval_path: Path,
) -> Path:
    path_text = artifact["path"]
    if path_text in seen:
        _fail(f"artifact path is bound more than once: {path_text}")
    seen[path_text] = context
    path = _safe_repo_path(repo_root, path_text, f"{context}.path", must_exist=True, require_file=True)
    if path == approval_path:
        _fail(f"{context} cannot bind the approval to itself")
    observed = _sha256_file(path)
    if observed != artifact["sha256"]:
        _fail(f"digest drift for {path_text}")
    return path


def _validate_submodule_commits(value: Any) -> dict[str, str]:
    commits = _expect_object(value, "reviewed_state.submodule_commits")
    expected = {"ipfs_accelerate_py", "ipfs_datasets_py"}
    _exact_keys(commits, expected, "reviewed_state.submodule_commits")
    result: dict[str, str] = {}
    for name in sorted(expected):
        commit = _expect_string(commits[name], f"reviewed_state.submodule_commits.{name}", minimum=40, maximum=40)
        if not COMMIT_RE.fullmatch(commit):
            _fail(f"reviewed_state.submodule_commits.{name} is not a full lowercase commit")
        result[name] = commit
    return result


def _verify_trusted_executable(path: Path, label: str) -> None:
    if not path.is_absolute():
        _fail(f"trusted {label} path must be absolute")
    try:
        metadata = path.lstat()
    except OSError as exc:
        _fail(f"trusted {label} executable cannot be inspected: {exc}")
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        _fail(f"trusted {label} executable must be a regular, non-symlink file")
    if metadata.st_uid != 0 or metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
        _fail(f"trusted {label} executable must be root-owned and not group/other writable")
    if not os.access(path, os.X_OK):
        _fail(f"trusted {label} executable is not executable")


def _trusted_process_environment(extra: Mapping[str, str] | None = None) -> dict[str, str]:
    """Return a minimal environment that cannot inject loaders or Git config."""

    environment = {
        "PATH": "/usr/bin:/bin",
        "LANG": "C",
        "LC_ALL": "C",
        "TZ": "UTC",
    }
    if extra is not None:
        environment.update(extra)
    return environment


def _trusted_git_command(repo: Path, *arguments: str) -> list[str]:
    """Build one fixed Git invocation with executable hook surfaces disabled."""

    return [
        str(TRUSTED_GIT),
        "-c",
        "core.fsmonitor=false",
        "-c",
        "core.hooksPath=/dev/null",
        "-c",
        "diff.external=",
        "-C",
        str(repo),
        *arguments,
    ]


def _trusted_git_environment() -> dict[str, str]:
    return _trusted_process_environment(
        {
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_ATTR_NOSYSTEM": "1",
            "GIT_NO_LAZY_FETCH": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_ASKPASS": "",
        }
    )


def _offline_git(repo: Path, *arguments: str, preserve_output: bool = False) -> str:
    try:
        result = subprocess.run(
            _trusted_git_command(repo, *arguments),
            check=False,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=10,
            env=_trusted_git_environment(),
        )
    except (OSError, subprocess.SubprocessError) as exc:
        _fail(f"local git verification failed: {exc}")
    if result.returncode != 0:
        detail = result.stderr.strip().splitlines()
        suffix = f": {detail[-1]}" if detail else ""
        _fail(f"local git verification rejected {repo}{suffix}")
    return result.stdout if preserve_output else result.stdout.strip()


def _verify_root_worktree(repo_root: Path, phase: str) -> None:
    status_output = _offline_git(
        repo_root,
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
        preserve_output=True,
    )
    allowed_approval = CANONICAL_APPROVAL_PATHS[phase].as_posix()
    allowed_signature_prefix = (CANONICAL_APPROVAL_PATHS[phase].parent / "signatures").as_posix() + "/"
    drift: list[str] = []
    for line in status_output.splitlines():
        if not line:
            continue
        if len(line) < 4 or line[2] != " ":
            _fail("root worktree status output was malformed")
        path_text = line[3:]
        if path_text.startswith('"') or path_text.endswith('"'):
            drift.append(path_text)
            continue
        paths = path_text.split(" -> ")
        if any(path != allowed_approval and not path.startswith(allowed_signature_prefix) for path in paths):
            drift.append(path_text)
    if drift:
        _fail(f"root worktree drift outside canonical approval paths: {sorted(drift)}")


def _verify_git_state(
    repo_root: Path,
    root_commit: str,
    submodule_commits: Mapping[str, str],
    phase: str,
    *,
    historical_link: bool = False,
) -> None:
    resolved_commit = _offline_git(repo_root, "rev-parse", "--verify", f"{root_commit}^{{commit}}")
    if resolved_commit != root_commit:
        _fail("reviewed_state.root_commit did not resolve exactly")

    current_root = _offline_git(repo_root, "rev-parse", "HEAD")
    if historical_link:
        try:
            ancestor_result = subprocess.run(
                _trusted_git_command(
                    repo_root,
                    "merge-base",
                    "--is-ancestor",
                    root_commit,
                    current_root,
                ),
                check=False,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=10,
                env=_trusted_git_environment(),
            )
        except (OSError, subprocess.SubprocessError) as exc:
            _fail(f"local git ancestry verification failed: {exc}")
        if ancestor_result.returncode != 0:
            _fail("linked selection root_commit is not an ancestor of the current local HEAD")
    elif root_commit != current_root:
        _fail("reviewed_state.root_commit must equal the exact current HEAD")
    else:
        _verify_root_worktree(repo_root, phase)

    for name, expected_commit in sorted(submodule_commits.items()):
        recorded_commit = _offline_git(repo_root, "rev-parse", f"{root_commit}:{name}")
        if recorded_commit != expected_commit:
            _fail(f"reviewed root gitlink does not match the approved submodule commit for {name}")
        if historical_link:
            continue
        submodule_path = _safe_repo_path(
            repo_root,
            name,
            f"reviewed_state.submodule_commits.{name} path",
            must_exist=True,
            require_directory=True,
        )
        observed_commit = _offline_git(submodule_path, "rev-parse", "HEAD")
        if observed_commit != expected_commit:
            _fail(f"submodule commit drift for {name}")
        dirty = _offline_git(submodule_path, "status", "--porcelain", "--untracked-files=no")
        if dirty:
            _fail(f"submodule has tracked dirty state: {name}")


def _validate_reviewed_state(
    value: Any,
    phase: str,
) -> tuple[str, dict[str, str], list[tuple[str, dict[str, str]]], Path]:
    state = _expect_object(value, "reviewed_state")
    common = {
        "root_commit",
        "submodule_commits",
        "objective_heap",
        "implementation_plan",
        "runbook",
        "storage_adr",
    }
    if phase == SELECTION:
        artifact_keys = {
            "objective_heap",
            "implementation_plan",
            "runbook",
            "storage_adr",
            "full_board",
            "objective_graph",
            "bundle_index",
            "restricted_bundle_index",
            "restricted_bundle_index_duckdb",
            "preflight_receipt",
            *SELECTION_VERIFIER_CONTRACT_PATHS,
        }
    else:
        artifact_keys = {
            "objective_heap",
            "implementation_plan",
            "runbook",
            "storage_adr",
            "full_board",
            "objective_graph",
            "bundle_index",
            "implementation_bundle_index",
            "implementation_bundle_index_duckdb",
            "preflight_receipt",
            "dry_run_receipt",
        }
    _exact_keys(state, common | artifact_keys, "reviewed_state")

    root_commit = _expect_string(state["root_commit"], "reviewed_state.root_commit", minimum=40, maximum=40)
    if not COMMIT_RE.fullmatch(root_commit):
        _fail("reviewed_state.root_commit must be a full lowercase commit")
    submodules = _validate_submodule_commits(state["submodule_commits"])
    artifacts = [
        (f"reviewed_state.{name}", _validate_artifact_shape(state[name], f"reviewed_state.{name}"))
        for name in sorted(artifact_keys)
    ]
    for name, expected_path in CANONICAL_SOURCE_PATHS.items():
        if state[name]["path"] != expected_path:
            _fail(f"reviewed_state.{name}.path must be {expected_path}")

    board_key = "full_board"
    board_path = Path(state[board_key]["path"])
    if board_path.name != "WORLDCOIN_HUMAN_AID_TODO.md" or GENERATED_ROOT_PREFIX not in board_path.parents:
        _fail(f"reviewed_state.{board_key}.path must name an immutable regenerated WORLDCOIN_HUMAN_AID_TODO.md")
    generated_root = board_path.parent
    if generated_root.parent != GENERATED_ROOT_PREFIX:
        _fail("reviewed generated root must be one immutable direct child of the regeneration directory")
    if Path(state["objective_graph"]["path"]) != generated_root / "objective_graph.json":
        _fail("reviewed_state.objective_graph.path does not match the reviewed board root")
    if Path(state["bundle_index"]["path"]) != generated_root / "objective_bundles/index.json":
        _fail("reviewed_state.bundle_index.path does not match the reviewed board root")
    if Path(state["preflight_receipt"]["path"]) != generated_root / "preflight-receipt.json":
        _fail("reviewed_state.preflight_receipt.path must be under the reviewed board root")
    if phase == SELECTION:
        if Path(state["restricted_bundle_index"]["path"]) != generated_root / "launch_profiles/g038-g040.index.json":
            _fail("reviewed_state.restricted_bundle_index.path must bind the G038-G040 launch profile")
        if (
            Path(state["restricted_bundle_index_duckdb"]["path"])
            != generated_root / "launch_profiles/g038-g040.index.duckdb"
        ):
            _fail("reviewed_state.restricted_bundle_index_duckdb.path must bind the paired DuckDB index")
        for key, expected_path in SELECTION_VERIFIER_CONTRACT_PATHS.items():
            if state[key]["path"] != expected_path:
                _fail(f"reviewed_state.{key}.path must be {expected_path}")
    else:
        if (
            Path(state["implementation_bundle_index"]["path"])
            != generated_root / "launch_profiles/implementation.index.json"
        ):
            _fail("reviewed_state.implementation_bundle_index.path must bind the implementation launch profile")
        if (
            Path(state["implementation_bundle_index_duckdb"]["path"])
            != generated_root / "launch_profiles/implementation.index.duckdb"
        ):
            _fail("reviewed_state.implementation_bundle_index_duckdb.path must bind the paired DuckDB index")
        if Path(state["dry_run_receipt"]["path"]) != generated_root / "dry_run/lane-manifest.json":
            _fail("reviewed_state.dry_run_receipt.path must bind the no-start manifest")
    return root_commit, submodules, artifacts, generated_root


def _schedulable_goals_from_heap(repo_root: Path) -> set[str]:
    heap_path = repo_root / CANONICAL_SOURCE_PATHS["objective_heap"]
    try:
        text = heap_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        _fail(f"cannot read canonical objective heap: {exc}")
    headings = list(re.finditer(r"^## (WORLDCOIN-G[0-9]{3}) .+$", text, flags=re.MULTILINE))
    if not headings:
        _fail("canonical objective heap contains no goals")
    schedulable: set[str] = set()
    seen: set[str] = set()
    for index, heading in enumerate(headings):
        goal_id = heading.group(1)
        if goal_id in seen:
            _fail(f"canonical objective heap contains duplicate goal {goal_id}")
        seen.add(goal_id)
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        block = text[heading.end() : end]
        status_match = re.search(r"^- Status: (.+)$", block, flags=re.MULTILINE)
        if status_match is None:
            _fail(f"canonical objective heap goal {goal_id} has no status")
        status = status_match.group(1).strip().lower().replace("-", "_").replace(" ", "_")
        if status in SCHEDULABLE_GOAL_STATES:
            schedulable.add(goal_id)
    if not schedulable:
        _fail("canonical objective heap contains no schedulable goals")
    return schedulable


def _validation_commands_from_heap(repo_root: Path, goal_ids: set[str]) -> set[str]:
    heap_path = repo_root / CANONICAL_SOURCE_PATHS["objective_heap"]
    try:
        text = heap_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        _fail(f"cannot read canonical objective heap validation commands: {exc}")
    headings = list(re.finditer(r"^## (WORLDCOIN-G[0-9]{3}) .+$", text, flags=re.MULTILINE))
    commands: dict[str, str] = {}
    for index, heading in enumerate(headings):
        goal_id = heading.group(1)
        if goal_id not in goal_ids:
            continue
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        block = text[heading.end() : end]
        matches = re.findall(r"^- Validation: (.+)$", block, flags=re.MULTILINE)
        if len(matches) != 1 or not matches[0].strip():
            _fail(f"canonical objective heap goal {goal_id} must have exactly one Validation command")
        commands[goal_id] = matches[0].strip()
    missing = goal_ids - set(commands)
    if missing:
        _fail(f"canonical objective heap omits Validation commands for goals: {sorted(missing)}")
    if len(set(commands.values())) != len(commands):
        _fail("canonical objective heap validation commands must be distinct per selected goal")
    return set(commands.values())


def _validate_validation_command(command: str, repo_root: Path) -> None:
    """Accept only the reviewed, offline validation command grammar.

    The supervisor's validation scheduler executes board commands through
    ``bash -lc``.  Exact equality with the signed heap prevents record-level
    substitution, while this grammar prevents a compromised heap entry from
    introducing shell expansion, redirection, pipelines, or a new executable.
    """

    if "\n" in command or "\r" in command:
        _fail("scope.validation_commands must contain one command per item")
    if any(character in command for character in "$`\\*?[]{}~#"):
        _fail("scope.validation_commands contains shell expansion or substitution")

    lexer = shlex.shlex(
        command,
        posix=True,
        punctuation_chars="&|;<>()",
    )
    lexer.whitespace_split = True
    lexer.commenters = ""
    try:
        tokens = list(lexer)
    except ValueError as exc:
        _fail(f"scope.validation_commands is not valid shell text: {exc}")
    if not tokens:
        _fail("scope.validation_commands cannot be empty")

    segments: list[list[str]] = [[]]
    for token in tokens:
        if token == "&&":
            if not segments[-1]:
                _fail("scope.validation_commands contains an empty command segment")
            segments.append([])
            continue
        if any(character in token for character in "&|;<>()"):
            _fail("scope.validation_commands contains a forbidden shell control operator")
        segments[-1].append(token)
    if not segments[-1]:
        _fail("scope.validation_commands contains an empty command segment")

    for segment in segments:
        while segment and "=" in segment[0]:
            assignment = segment.pop(0)
            if assignment not in ALLOWED_VALIDATION_ENV_ASSIGNMENTS:
                _fail("scope.validation_commands contains an unapproved environment assignment")
        if not segment or segment[0] not in ALLOWED_VALIDATION_EXECUTABLES:
            _fail("scope.validation_commands contains an executable outside the validation allowlist")

        executable, *arguments = segment
        if executable == "python":
            if len(arguments) >= 3 and arguments[:2] == ["-m", "pytest"]:
                continue
            if arguments and arguments[0] in ALLOWED_VALIDATION_PYTHON_SCRIPTS:
                _safe_repo_path(
                    repo_root,
                    arguments[0],
                    "scope.validation_commands Python script",
                    must_exist=False,
                )
                continue
            _fail("scope.validation_commands Python invocation is outside the validation allowlist")

        if executable == "npm":
            if len(arguments) < 3 or arguments[0] != "--prefix" or arguments[1] not in ALLOWED_VALIDATION_NPM_PREFIXES:
                _fail("scope.validation_commands npm prefix is outside the validation allowlist")
            _safe_repo_path(
                repo_root,
                arguments[1],
                "scope.validation_commands npm prefix",
                must_exist=False,
            )
            action, remainder = arguments[2], arguments[3:]
            if action == "ci":
                if remainder != ["--offline", "--ignore-scripts"]:
                    _fail("scope.validation_commands npm ci must be offline with lifecycle scripts disabled")
                continue
            if action == "test":
                if remainder:
                    if remainder[0] != "--" or len(remainder) == 1:
                        _fail("scope.validation_commands npm test arguments are not canonical")
                    for index, target in enumerate(remainder[1:]):
                        _validate_relative_path_text(
                            target,
                            f"scope.validation_commands npm test target[{index}]",
                        )
                continue
            _fail("scope.validation_commands npm action is outside the validation allowlist")

        if executable == "test":
            if len(arguments) != 2 or arguments[0] != "-f":
                _fail("scope.validation_commands test invocation is outside the validation allowlist")
            _safe_repo_path(
                repo_root,
                arguments[1],
                "scope.validation_commands test target",
                must_exist=False,
            )


def _paths_overlap(left: Path, right: Path) -> bool:
    return left == right or left in right.parents or right in left.parents


def _validate_scope(
    value: Any,
    phase: str,
    repo_root: Path,
    generated_root: Path,
    immutable_artifact_paths: Iterable[Path],
) -> None:
    scope = _expect_object(value, "scope")
    keys = {
        "goal_ids",
        "validation_commands",
        "writable_paths",
        "network",
        "feature_flags",
        "live_secrets_present",
        "forbidden_actions",
    }
    _exact_keys(scope, keys, "scope")

    goals = set(_unique_strings(scope["goal_ids"], "scope.goal_ids", minimum_items=1))
    if not all(GOAL_RE.fullmatch(goal) for goal in goals):
        _fail("scope.goal_ids contains an invalid goal ID")
    if goals & FORBIDDEN_GOALS:
        _fail("scope.goal_ids contains a terminal human-gated goal")
    if phase == SELECTION and goals != SELECTION_GOALS:
        _fail("selection scope must contain exactly WORLDCOIN-G038, G039, and G040")
    if phase == LAUNCH:
        expected_goals = _schedulable_goals_from_heap(repo_root) - LAUNCH_PREREQUISITE_GOALS
        if not expected_goals:
            _fail("launch objective projection is empty after removing completed prerequisites")
        if goals != expected_goals:
            _fail(
                "launch scope must contain the exact implementation profile goal set; "
                f"missing={sorted(expected_goals - goals)}, "
                f"unexpected={sorted(goals - expected_goals)}"
            )

    commands = _unique_strings(scope["validation_commands"], "scope.validation_commands", minimum_items=1)
    for command in commands:
        _validate_validation_command(command, repo_root)
        lowered = command.lower()
        forbidden_fragments = (
            "--start",
            "world_id_enabled=1",
            "world_aid_external_calls_enabled=1",
            "world_aid_wld_transfers_enabled=1",
            "curl ",
            "wget ",
            "npm install",
            "npm ci ",
            "pip install",
            "uv pip",
            "git clone",
            "docker ",
            "podman ",
        )
        if any(fragment in lowered for fragment in forbidden_fragments):
            _fail("scope.validation_commands contains a start, live, network, or package substitution")
    expected_commands = _validation_commands_from_heap(repo_root, goals)
    if set(commands) != expected_commands:
        _fail(
            "scope.validation_commands must exactly match the canonical objective Validation fields; "
            f"missing={sorted(expected_commands - set(commands))}, "
            f"unexpected={sorted(set(commands) - expected_commands)}"
        )

    protected_paths = (
        {Path(path) for path in PROTECTED_WRITABLE_PATHS} | {generated_root} | set(immutable_artifact_paths)
    )
    writable_paths = _unique_strings(scope["writable_paths"], "scope.writable_paths", minimum_items=1)
    for index, path_text in enumerate(writable_paths):
        normalized = _validate_relative_path_text(path_text, f"scope.writable_paths[{index}]")
        if normalized == ".git" or normalized.startswith(".git/"):
            _fail("scope.writable_paths cannot include git metadata")
        if normalized == "data/worldcoin_human_aid/approvals" or normalized.startswith(
            "data/worldcoin_human_aid/approvals/"
        ):
            _fail("scope.writable_paths cannot include human approval records")
        normalized_path = Path(normalized)
        if any(_paths_overlap(normalized_path, protected) for protected in protected_paths):
            _fail(f"scope.writable_paths overlaps a signed immutable input: {normalized}")
        if any(part in {"allowed_signers", "trust", "trust-store"} for part in normalized_path.parts):
            _fail("scope.writable_paths cannot include operator trust material")
        _safe_repo_path(
            repo_root,
            normalized,
            f"scope.writable_paths[{index}]",
            must_exist=False,
        )

    network = _expect_object(scope["network"], "scope.network")
    _exact_keys(network, {"default_deny", "registry_access", "allowed_destinations"}, "scope.network")
    if _expect_bool(network["default_deny"], "scope.network.default_deny") is not True:
        _fail("scope.network.default_deny must be true")
    if _expect_bool(network["registry_access"], "scope.network.registry_access") is not False:
        _fail("scope.network.registry_access must be false")
    destinations = _unique_strings(network["allowed_destinations"], "scope.network.allowed_destinations")
    for destination in destinations:
        lowered = destination.lower()
        if not HOST_RE.fullmatch(destination) or "*" in destination or "://" in destination or "/" in destination:
            _fail(f"scope.network.allowed_destinations is not an exact host or host:port: {destination}")
        if any(fragment in lowered for fragment in FORBIDDEN_DESTINATION_FRAGMENTS):
            _fail(f"scope.network.allowed_destinations contains a forbidden external service: {destination}")
        if ":" in destination and not destination.startswith("["):
            port_text = destination.rsplit(":", 1)[1]
            if port_text.isdigit() and not 1 <= int(port_text) <= 65535:
                _fail(f"scope.network.allowed_destinations has an invalid port: {destination}")

    flags = _expect_object(scope["feature_flags"], "scope.feature_flags")
    _exact_keys(flags, REQUIRED_FEATURE_FLAGS, "scope.feature_flags")
    if flags != REQUIRED_FEATURE_FLAGS:
        _fail("all live feature flags must be the string value '0'")

    if _expect_bool(scope["live_secrets_present"], "scope.live_secrets_present") is not False:
        _fail("scope.live_secrets_present must be false")

    forbidden_actions = set(
        _unique_strings(
            scope["forbidden_actions"],
            "scope.forbidden_actions",
            minimum_items=len(REQUIRED_FORBIDDEN_ACTIONS),
            maximum_items=len(REQUIRED_FORBIDDEN_ACTIONS),
        )
    )
    if forbidden_actions != REQUIRED_FORBIDDEN_ACTIONS:
        _fail("scope.forbidden_actions must contain the exact required deny set")


def _validate_reviewers(
    value: Any,
    phase: str,
    issued_at: datetime,
    record_expires_at: datetime,
    now: datetime,
) -> dict[str, str]:
    reviewers = _expect_array(value, "reviewers")
    required_roles = REQUIRED_ROLES[phase]
    if len(reviewers) != len(required_roles):
        _fail(f"reviewers must contain exactly {len(required_roles)} entries")

    identities: set[str] = set()
    by_role: dict[str, str] = {}
    for index, raw_reviewer in enumerate(reviewers):
        context = f"reviewers[{index}]"
        reviewer = _expect_object(raw_reviewer, context)
        _exact_keys(reviewer, {"role", "identity", "decision", "reviewed_at", "expires_at"}, context)
        role = _expect_string(reviewer["role"], f"{context}.role", maximum=64)
        identity = _expect_string(reviewer["identity"], f"{context}.identity", minimum=3, maximum=254)
        if role not in required_roles:
            _fail(f"{context}.role is not allowed for {phase}")
        if role in by_role:
            _fail(f"duplicate reviewer role: {role}")
        if not IDENTITY_RE.fullmatch(identity):
            _fail(f"{context}.identity is invalid")
        if identity in identities:
            _fail("reviewer identities must be distinct for separation of duties")
        if reviewer["decision"] != "approved":
            _fail(f"{context}.decision must be approved")
        reviewed_at = _parse_timestamp(reviewer["reviewed_at"], f"{context}.reviewed_at")
        reviewer_expires_at = _parse_timestamp(reviewer["expires_at"], f"{context}.expires_at")
        if not issued_at <= reviewed_at <= now:
            _fail(f"{context}.reviewed_at is stale relative to issuance or lies in the future")
        if reviewer_expires_at != record_expires_at or reviewer_expires_at <= now:
            _fail(f"{context}.expires_at must equal the current record expiry")
        by_role[role] = identity
        identities.add(identity)

    if set(by_role) != required_roles:
        _fail(f"reviewer roles differ; missing={sorted(required_roles - set(by_role))}")
    return by_role


def _validate_exceptions(value: Any, issued_at: datetime, record_expires_at: datetime, now: datetime) -> None:
    exceptions = _expect_array(value, "exceptions")
    ids: set[str] = set()
    for index, raw_exception in enumerate(exceptions):
        context = f"exceptions[{index}]"
        exception = _expect_object(raw_exception, context)
        _exact_keys(
            exception,
            {"id", "owner", "rationale", "compensating_controls", "expires_at"},
            context,
        )
        exception_id = _expect_string(exception["id"], f"{context}.id", minimum=4, maximum=35)
        if not EXCEPTION_ID_RE.fullmatch(exception_id) or exception_id in ids:
            _fail(f"{context}.id is invalid or duplicated")
        _expect_string(exception["owner"], f"{context}.owner", minimum=3, maximum=254)
        _expect_string(exception["rationale"], f"{context}.rationale", minimum=20, maximum=2000)
        controls = _unique_strings(
            exception["compensating_controls"],
            f"{context}.compensating_controls",
            minimum_items=1,
        )
        if any(len(control) < 10 or len(control) > 1000 for control in controls):
            _fail(f"{context}.compensating_controls entries must be substantive")
        expires_at = _parse_timestamp(exception["expires_at"], f"{context}.expires_at")
        if not issued_at <= now < expires_at <= record_expires_at:
            _fail(f"{context}.expires_at is not current and bounded by the record")
        ids.add(exception_id)


def _parse_allowed_signers(path: Path) -> dict[str, set[str]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        _fail(f"cannot read allowed signers trust store: {exc}")
    principals: dict[str, set[str]] = {}
    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        try:
            fields = shlex.split(stripped, comments=True, posix=True)
        except ValueError as exc:
            _fail(f"allowed signers line {line_number} is invalid: {exc}")
        key_index = next(
            (
                index
                for index, field in enumerate(fields)
                if field.startswith(("ssh-", "ecdsa-", "sk-ssh-", "sk-ecdsa-"))
            ),
            None,
        )
        if key_index is None or key_index == 0 or key_index + 1 >= len(fields):
            _fail(f"allowed signers line {line_number} has no supported public key")
        identity_field = fields[0]
        key_blob_text = fields[key_index + 1]
        try:
            key_blob = base64.b64decode(key_blob_text.encode("ascii"), validate=True)
        except (UnicodeEncodeError, binascii.Error) as exc:
            _fail(f"allowed signers line {line_number} has invalid key data: {exc}")
        fingerprint = "SHA256:" + base64.b64encode(hashlib.sha256(key_blob).digest()).decode("ascii").rstrip("=")
        for identity in identity_field.split(","):
            if not IDENTITY_RE.fullmatch(identity):
                _fail(f"allowed signers line {line_number} has an invalid identity")
            principals.setdefault(identity, set()).add(fingerprint)
    if not principals:
        _fail("allowed signers trust store contains no principals")
    return principals


def _validate_trust_shape(
    value: Any,
    phase: str,
    reviewer_identities: Mapping[str, str],
) -> list[dict[str, str]]:
    trust = _expect_object(value, "trust")
    _exact_keys(trust, {"signature_namespace", "allowed_signers_sha256", "signatures"}, "trust")
    if trust["signature_namespace"] != SIGNATURE_NAMESPACES[phase]:
        _fail("trust.signature_namespace does not match the gate phase")
    trust_digest = _expect_string(
        trust["allowed_signers_sha256"],
        "trust.allowed_signers_sha256",
        minimum=71,
        maximum=71,
    )
    if not DIGEST_RE.fullmatch(trust_digest):
        _fail("trust.allowed_signers_sha256 must be a lowercase sha256 digest")

    raw_signatures = _expect_array(trust["signatures"], "trust.signatures")
    if len(raw_signatures) != len(REQUIRED_ROLES[phase]):
        _fail("trust.signatures must have exactly one entry per required role")
    signatures: list[dict[str, str]] = []
    roles: set[str] = set()
    files: set[str] = set()
    fingerprints: set[str] = set()
    for index, raw_signature in enumerate(raw_signatures):
        context = f"trust.signatures[{index}]"
        signature = _expect_object(raw_signature, context)
        _exact_keys(signature, {"role", "identity", "key_fingerprint", "file"}, context)
        role = _expect_string(signature["role"], f"{context}.role", maximum=64)
        identity = _expect_string(signature["identity"], f"{context}.identity", minimum=3, maximum=254)
        fingerprint = _expect_string(
            signature["key_fingerprint"],
            f"{context}.key_fingerprint",
            minimum=50,
            maximum=50,
        )
        filename = _expect_string(signature["file"], f"{context}.file", minimum=9, maximum=71)
        if role not in REQUIRED_ROLES[phase] or role in roles:
            _fail(f"{context}.role is invalid or duplicated")
        if reviewer_identities.get(role) != identity:
            _fail(f"{context}.identity does not match the reviewer for role {role}")
        if not FINGERPRINT_RE.fullmatch(fingerprint):
            _fail(f"{context}.key_fingerprint is invalid")
        if fingerprint in fingerprints:
            _fail("signing key fingerprints must be distinct across reviewer roles")
        if not SIGNATURE_FILE_RE.fullmatch(filename) or filename != f"{role}.sshsig" or filename in files:
            _fail(f"{context}.file must be the unique canonical role filename")
        signatures.append(
            {
                "role": role,
                "identity": identity,
                "key_fingerprint": fingerprint,
                "file": filename,
            }
        )
        roles.add(role)
        files.add(filename)
        fingerprints.add(fingerprint)
    if roles != REQUIRED_ROLES[phase]:
        _fail("trust.signatures roles do not match the exact required role set")
    return signatures


def _verify_signatures(
    approval_path: Path,
    approval_bytes: bytes,
    phase: str,
    signatures: Sequence[Mapping[str, str]],
    allowed_signers_path: Path,
    allowed_principals: Mapping[str, set[str]],
) -> None:
    signature_dir = approval_path.parent / "signatures"
    if not signature_dir.exists() or not signature_dir.is_dir() or signature_dir.is_symlink():
        _fail("canonical signatures directory is missing or unsafe")

    env = _trusted_process_environment(
        {
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_ASKPASS": "",
            "HF_HUB_OFFLINE": "1",
            "HF_DATASETS_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "WORLD_ID_ENABLED": "0",
            "WORLD_AID_EXTERNAL_CALLS_ENABLED": "0",
            "WORLD_AID_WLD_TRANSFERS_ENABLED": "0",
        }
    )
    for signature in sorted(signatures, key=lambda item: item["role"]):
        identity = signature["identity"]
        fingerprint = signature["key_fingerprint"]
        if identity not in allowed_principals:
            _fail(f"signature identity is absent from the operator trust store: {identity}")
        if fingerprint not in allowed_principals[identity]:
            _fail(f"signature key fingerprint is not trusted for identity: {identity}")
        signature_path = signature_dir / signature["file"]
        if not signature_path.exists() or not signature_path.is_file() or signature_path.is_symlink():
            _fail(f"detached signature is missing or unsafe for role {signature['role']}")
        try:
            signature_path.resolve(strict=True).relative_to(signature_dir.resolve(strict=True))
        except (OSError, RuntimeError, ValueError):
            _fail(f"detached signature escapes the canonical signature directory for role {signature['role']}")
        try:
            result = subprocess.run(
                [
                    str(TRUSTED_SSH_KEYGEN),
                    "-Y",
                    "verify",
                    "-f",
                    str(allowed_signers_path),
                    "-I",
                    identity,
                    "-n",
                    SIGNATURE_NAMESPACES[phase],
                    "-s",
                    str(signature_path),
                ],
                check=False,
                input=approval_bytes,
                capture_output=True,
                timeout=10,
                env=env,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            _fail(f"OpenSSH signature verification failed to run: {exc}")
        if result.returncode != 0:
            _fail(f"detached signature rejected for role {signature['role']}")


def _validate_read_only_directory(
    value: Any,
    context: str,
    repo_root: Path,
) -> None:
    directory = _expect_object(value, context)
    _exact_keys(directory, {"path", "read_only"}, context)
    if _expect_bool(directory["read_only"], f"{context}.read_only") is not True:
        _fail(f"{context}.read_only must be true")
    path = _safe_repo_path(
        repo_root,
        directory["path"],
        f"{context}.path",
        must_exist=True,
        require_directory=True,
    )
    try:
        mode = path.stat().st_mode
    except OSError as exc:
        _fail(f"cannot inspect {context}.path mode: {exc}")
    if mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH):
        _fail(f"{context}.path is not mode-read-only")


def _artifact_list(
    value: Any,
    context: str,
    *,
    minimum_items: int,
    maximum_items: int | None = None,
) -> list[tuple[str, dict[str, str]]]:
    items = _expect_array(value, context)
    if len(items) < minimum_items or (maximum_items is not None and len(items) > maximum_items):
        _fail(f"{context} has an invalid item count")
    return [
        (f"{context}[{index}]", _validate_artifact_shape(item, f"{context}[{index}]"))
        for index, item in enumerate(items)
    ]


def _validate_selection_dependencies(
    value: Any,
    repo_root: Path,
) -> list[tuple[str, dict[str, str]]]:
    dependencies = _expect_object(value, "dependency_sets")
    _exact_keys(dependencies, {"siwe", "zkp", "duckdb"}, "dependency_sets")
    artifacts: list[tuple[str, dict[str, str]]] = []

    siwe = _expect_object(dependencies["siwe"], "dependency_sets.siwe")
    siwe_keys = {
        "manifest",
        "lockfile",
        "tarballs",
        "cache",
        "licenses",
        "provenance",
        "sbom",
        "vulnerability_review",
        "lifecycle_scripts",
    }
    _exact_keys(siwe, siwe_keys, "dependency_sets.siwe")
    for key in ("manifest", "lockfile", "licenses", "provenance", "sbom", "vulnerability_review"):
        artifacts.append(
            (
                f"dependency_sets.siwe.{key}",
                _validate_artifact_shape(siwe[key], f"dependency_sets.siwe.{key}"),
            )
        )
    artifacts.extend(_artifact_list(siwe["tarballs"], "dependency_sets.siwe.tarballs", minimum_items=1))
    _validate_read_only_directory(siwe["cache"], "dependency_sets.siwe.cache", repo_root)
    lifecycle_scripts = _unique_strings(siwe["lifecycle_scripts"], "dependency_sets.siwe.lifecycle_scripts")
    if any("\n" in script or "\r" in script for script in lifecycle_scripts):
        _fail("dependency_sets.siwe.lifecycle_scripts contains a multiline value")

    zkp = _expect_object(dependencies["zkp"], "dependency_sets.zkp")
    zkp_keys = {
        "architecture",
        "backend",
        "version",
        "tool",
        "smoke_source",
        "smoke_lock",
        "licenses",
        "provenance",
        "sbom",
        "vulnerability_review",
        "deterministic_flags",
        "resource_bounds",
    }
    _exact_keys(zkp, zkp_keys, "dependency_sets.zkp")
    architecture = _expect_string(zkp["architecture"], "dependency_sets.zkp.architecture", maximum=16)
    machine = platform.machine().lower()
    normalized_machine = {"amd64": "x86_64", "arm64": "aarch64"}.get(machine, machine)
    if architecture not in {"x86_64", "aarch64"} or architecture != normalized_machine:
        _fail("dependency_sets.zkp.architecture does not match the verifier host")
    _expect_string(zkp["backend"], "dependency_sets.zkp.backend", maximum=64)
    _expect_string(zkp["version"], "dependency_sets.zkp.version", maximum=128)
    for key in ("tool", "smoke_source", "smoke_lock", "licenses", "provenance", "sbom", "vulnerability_review"):
        artifacts.append(
            (
                f"dependency_sets.zkp.{key}",
                _validate_artifact_shape(zkp[key], f"dependency_sets.zkp.{key}"),
            )
        )
    _unique_strings(
        zkp["deterministic_flags"],
        "dependency_sets.zkp.deterministic_flags",
        minimum_items=1,
    )
    bounds = _expect_object(zkp["resource_bounds"], "dependency_sets.zkp.resource_bounds")
    _exact_keys(bounds, {"max_seconds", "max_memory_mb", "max_output_bytes"}, "dependency_sets.zkp.resource_bounds")
    _expect_int(bounds["max_seconds"], "dependency_sets.zkp.resource_bounds.max_seconds", 1, 3600)
    _expect_int(bounds["max_memory_mb"], "dependency_sets.zkp.resource_bounds.max_memory_mb", 64, 65536)
    _expect_int(
        bounds["max_output_bytes"],
        "dependency_sets.zkp.resource_bounds.max_output_bytes",
        1,
        1073741824,
    )

    duckdb = _expect_object(dependencies["duckdb"], "dependency_sets.duckdb")
    duckdb_keys = {
        "python_version",
        "platform",
        "duckdb_version",
        "wheels",
        "wheelhouse",
        "requirements_lock",
        "runtime_policy",
        "backup_policy",
        "licenses",
        "provenance",
        "sbom",
        "vulnerability_review",
        "topology",
        "database_file_encryption",
        "extension_auto_install",
        "extension_auto_load",
        "external_access",
        "community_extensions",
        "extension_directory",
    }
    _exact_keys(duckdb, duckdb_keys, "dependency_sets.duckdb")
    python_version = _expect_string(duckdb["python_version"], "dependency_sets.duckdb.python_version", maximum=32)
    if python_version != platform.python_version():
        _fail("dependency_sets.duckdb.python_version does not match the verifier interpreter")
    _expect_string(duckdb["platform"], "dependency_sets.duckdb.platform", minimum=3, maximum=128)
    duckdb_version = _expect_string(duckdb["duckdb_version"], "dependency_sets.duckdb.duckdb_version", maximum=128)
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:[-+][A-Za-z0-9.]+)?", duckdb_version):
        _fail("dependency_sets.duckdb.duckdb_version must be exact")
    artifacts.extend(_artifact_list(duckdb["wheels"], "dependency_sets.duckdb.wheels", minimum_items=1))
    _validate_read_only_directory(duckdb["wheelhouse"], "dependency_sets.duckdb.wheelhouse", repo_root)
    for key in (
        "requirements_lock",
        "runtime_policy",
        "backup_policy",
        "licenses",
        "provenance",
        "sbom",
        "vulnerability_review",
    ):
        artifacts.append(
            (
                f"dependency_sets.duckdb.{key}",
                _validate_artifact_shape(duckdb[key], f"dependency_sets.duckdb.{key}"),
            )
        )
    if duckdb["topology"] != "single-host-single-writer-coordinator":
        _fail("dependency_sets.duckdb.topology must reject multi-writer deployment")
    if duckdb["database_file_encryption"] != "encrypted-volume-plus-application-envelope-encryption":
        _fail("dependency_sets.duckdb.database_file_encryption is not sufficient")
    if _expect_bool(duckdb["extension_auto_install"], "dependency_sets.duckdb.extension_auto_install") is not False:
        _fail("DuckDB extension auto-install must be false")
    if _expect_bool(duckdb["extension_auto_load"], "dependency_sets.duckdb.extension_auto_load") is not False:
        _fail("DuckDB extension auto-load must be false")
    if _expect_bool(duckdb["external_access"], "dependency_sets.duckdb.external_access") is not False:
        _fail("DuckDB external access must be false")
    if _expect_bool(duckdb["community_extensions"], "dependency_sets.duckdb.community_extensions") is not False:
        _fail("DuckDB community extensions must be false")

    extension_directory = _expect_object(
        duckdb["extension_directory"],
        "dependency_sets.duckdb.extension_directory",
    )
    _exact_keys(
        extension_directory,
        {"mode", "path", "allowlist"},
        "dependency_sets.duckdb.extension_directory",
    )
    mode = _expect_string(
        extension_directory["mode"],
        "dependency_sets.duckdb.extension_directory.mode",
        maximum=16,
    )
    allowlist = _expect_array(
        extension_directory["allowlist"],
        "dependency_sets.duckdb.extension_directory.allowlist",
    )
    if mode == "disabled":
        if extension_directory["path"] != "" or allowlist:
            _fail("disabled DuckDB extension_directory must have an empty path and allowlist")
    elif mode == "allowlist":
        extension_path_text = _validate_relative_path_text(
            extension_directory["path"],
            "dependency_sets.duckdb.extension_directory.path",
        )
        extension_path = _safe_repo_path(
            repo_root,
            extension_path_text,
            "dependency_sets.duckdb.extension_directory.path",
            must_exist=True,
            require_directory=True,
        )
        if extension_path.stat().st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH):
            _fail("DuckDB extension_directory allowlist path must be mode-read-only")
        if not allowlist:
            _fail("DuckDB extension_directory allowlist mode requires exact extension artifacts")
        names: set[str] = set()
        paths: set[str] = set()
        for index, raw_extension in enumerate(allowlist):
            context = f"dependency_sets.duckdb.extension_directory.allowlist[{index}]"
            extension = _expect_object(raw_extension, context)
            _exact_keys(extension, {"name", "path", "sha256"}, context)
            name = _expect_string(extension["name"], f"{context}.name", maximum=64)
            if not DUCKDB_EXTENSION_NAME_RE.fullmatch(name) or name in names:
                _fail(f"{context}.name is invalid or duplicated")
            artifact = _validate_artifact_shape(
                {"path": extension["path"], "sha256": extension["sha256"]},
                context,
            )
            artifact_path = Path(artifact["path"])
            if Path(extension_path_text) not in artifact_path.parents:
                _fail(f"{context}.path must be inside the reviewed extension_directory")
            if artifact["path"] in paths:
                _fail("DuckDB extension_directory allowlist paths must be unique")
            artifacts.append((context, artifact))
            names.add(name)
            paths.add(artifact["path"])
    else:
        _fail("DuckDB extension_directory.mode must be disabled or allowlist")

    return artifacts


def _validate_security_evidence_shape(
    value: Any,
    phase: str,
) -> tuple[list[tuple[str, dict[str, str]]], dict[str, dict[str, str]]]:
    security = _expect_object(value, "security_evidence")
    _exact_keys(security, SECURITY_EVIDENCE_FILENAMES, "security_evidence")
    artifacts: list[tuple[str, dict[str, str]]] = []
    by_key: dict[str, dict[str, str]] = {}
    base = Path("data/worldcoin_human_aid/gate_evidence") / f"gate-0b-{phase}"
    for key, filename in SECURITY_EVIDENCE_FILENAMES.items():
        context = f"security_evidence.{key}"
        artifact = _validate_artifact_shape(security[key], context)
        if artifact["path"] != (base / filename).as_posix():
            _fail(f"{context}.path must use the canonical phase-specific evidence path")
        artifacts.append((context, artifact))
        by_key[key] = artifact
    return artifacts, by_key


def _validate_launch_evidence(
    record: Mapping[str, Any],
) -> tuple[
    list[tuple[str, dict[str, str]]],
    dict[str, str],
    dict[str, dict[str, str]],
    dict[str, dict[str, str]],
]:
    artifacts: list[tuple[str, dict[str, str]]] = []
    selection = _expect_object(record["selection_evidence"], "selection_evidence")
    _exact_keys(selection, {"approval", "signatures"}, "selection_evidence")
    selection_approval = _validate_artifact_shape(selection["approval"], "selection_evidence.approval")
    expected_selection_path = CANONICAL_APPROVAL_PATHS[SELECTION].as_posix()
    if selection_approval["path"] != expected_selection_path:
        _fail("selection_evidence.approval must use the canonical selection approval path")
    artifacts.append(("selection_evidence.approval", selection_approval))
    selection_signatures = _artifact_list(
        selection["signatures"],
        "selection_evidence.signatures",
        minimum_items=len(REQUIRED_ROLES[SELECTION]),
        maximum_items=len(REQUIRED_ROLES[SELECTION]),
    )
    expected_signature_paths = {
        (CANONICAL_APPROVAL_PATHS[SELECTION].parent / "signatures" / f"{role}.sshsig").as_posix()
        for role in REQUIRED_ROLES[SELECTION]
    }
    observed_signature_paths = {artifact["path"] for _, artifact in selection_signatures}
    if observed_signature_paths != expected_signature_paths:
        _fail("selection_evidence.signatures does not bind the exact selection signature set")
    artifacts.extend(selection_signatures)

    receipts = _expect_object(record["bootstrap_receipts"], "bootstrap_receipts")
    _exact_keys(receipts, {"siwe", "zkp", "duckdb"}, "bootstrap_receipts")
    bootstrap_by_key: dict[str, dict[str, str]] = {}
    for key in ("siwe", "zkp", "duckdb"):
        artifact = _validate_artifact_shape(receipts[key], f"bootstrap_receipts.{key}")
        if artifact["path"] != BOOTSTRAP_RECEIPT_PATHS[key]:
            _fail(f"bootstrap_receipts.{key}.path must use the canonical {BOOTSTRAP_GOALS[key]} receipt")
        artifacts.append(
            (
                f"bootstrap_receipts.{key}",
                artifact,
            )
        )
        bootstrap_by_key[key] = artifact

    security_artifacts, security_by_key = _validate_security_evidence_shape(
        record["security_evidence"],
        LAUNCH,
    )
    artifacts.extend(security_artifacts)
    return artifacts, selection_approval, bootstrap_by_key, security_by_key


def _load_bound_json(
    repo_root: Path,
    artifact: Mapping[str, str],
    context: str,
) -> dict[str, Any]:
    path = _safe_repo_path(
        repo_root,
        artifact["path"],
        f"{context}.path",
        must_exist=True,
        require_file=True,
    )
    value, _ = _load_json_strict(path, context)
    return value


def _validate_evidence_window(
    receipt: Mapping[str, Any],
    context: str,
    *,
    checked_key: str,
    record_issued_at: datetime,
    record_expires_at: datetime,
    verification_time: datetime,
) -> datetime:
    checked_at = _parse_timestamp(receipt[checked_key], f"{context}.{checked_key}")
    valid_until = _parse_timestamp(receipt["valid_until"], f"{context}.valid_until")
    if checked_at > record_issued_at or checked_at > verification_time:
        _fail(f"{context} was not completed before the approval was issued")
    if verification_time - checked_at > MAX_EVIDENCE_AGE:
        _fail(f"{context} is older than the maximum 24-hour evidence age")
    if valid_until < record_expires_at or valid_until <= verification_time:
        _fail(f"{context} does not remain current through the approval expiry")
    if valid_until - checked_at > MAX_RECORD_VALIDITY:
        _fail(f"{context} validity exceeds 31 days")
    return checked_at


def _parse_generated_at(value: Any, context: str) -> datetime:
    text = _expect_string(value, context, minimum=20, maximum=35)
    if not text.endswith("Z"):
        _fail(f"{context} must be a UTC timestamp ending in Z")
    try:
        parsed = datetime.fromisoformat(text[:-1] + "+00:00")
    except ValueError as exc:
        _fail(f"{context} is not a real ISO 8601 timestamp: {exc}")
    if parsed.utcoffset() != timedelta(0):
        _fail(f"{context} must be UTC")
    return parsed.astimezone(UTC)


def _validate_network_canary_receipt(
    receipt: Mapping[str, Any],
    context: str,
    *,
    record_issued_at: datetime,
    verification_time: datetime,
) -> None:
    _exact_keys(
        receipt,
        {
            "schema",
            "generated_at",
            "synthetic_fixture",
            "human_approval",
            "contains_secrets",
            "offline",
            "passed",
            "boundary",
            "results",
            "interpretation",
        },
        context,
    )
    if receipt["schema"] != "world-human-aid-egress-canary/v2":
        _fail("network deny canary must use world-human-aid-egress-canary/v2")
    generated_at = _parse_generated_at(receipt["generated_at"], f"{context}.generated_at")
    if generated_at > record_issued_at or generated_at > verification_time:
        _fail("network deny canary was not completed before approval issuance")
    if verification_time - generated_at > MAX_EVIDENCE_AGE:
        _fail("network deny canary is older than the maximum 24-hour evidence age")
    expected_booleans = {
        "synthetic_fixture": True,
        "human_approval": False,
        "contains_secrets": False,
        "offline": True,
        "passed": True,
    }
    for key, expected in expected_booleans.items():
        if _expect_bool(receipt[key], f"{context}.{key}") is not expected:
            _fail(f"network deny canary {key} must be {str(expected).lower()}")
    _expect_string(receipt["interpretation"], f"{context}.interpretation", minimum=40, maximum=4000)

    boundary = _expect_object(receipt["boundary"], f"{context}.boundary")
    required_boundary_keys = {
        "apparmor",
        "network_namespace",
        "interfaces",
        "loopback_only",
        "ipv4_routes",
        "ipv6_routes",
        "no_external_route",
        "errors",
        "passed",
    }
    if not required_boundary_keys <= set(boundary):
        _fail("network deny canary boundary omits required enforcement evidence")
    if _expect_bool(boundary["passed"], f"{context}.boundary.passed") is not True:
        _fail("network deny canary boundary must pass")
    apparmor = _expect_object(boundary["apparmor"], f"{context}.boundary.apparmor")
    profile = _expect_string(apparmor.get("profile"), f"{context}.boundary.apparmor.profile", maximum=256)
    if (
        profile == "unconfined"
        or apparmor.get("expected_profile") != profile
        or apparmor.get("mode") != "enforce"
        or _expect_bool(
            apparmor.get("matches_reviewed_profile"),
            f"{context}.boundary.apparmor.matches_reviewed_profile",
        )
        is not True
    ):
        _fail("network deny canary does not prove the reviewed enforcing AppArmor profile")
    namespace = _expect_object(
        boundary["network_namespace"],
        f"{context}.boundary.network_namespace",
    )
    identity = _expect_string(
        namespace.get("identity"),
        f"{context}.boundary.network_namespace.identity",
        maximum=64,
    )
    if (
        namespace.get("expected_identity") != identity
        or namespace.get("host_identity") == identity
        or _expect_bool(
            namespace.get("matches_reviewed_namespace"),
            f"{context}.boundary.network_namespace.matches_reviewed_namespace",
        )
        is not True
        or _expect_bool(
            namespace.get("host_identity_valid"),
            f"{context}.boundary.network_namespace.host_identity_valid",
        )
        is not True
        or _expect_bool(
            namespace.get("separated_from_host"),
            f"{context}.boundary.network_namespace.separated_from_host",
        )
        is not True
    ):
        _fail("network deny canary does not prove an exact reviewed namespace separated from the host")
    interfaces = _unique_strings(boundary["interfaces"], f"{context}.boundary.interfaces")
    if interfaces != ["lo"]:
        _fail("network deny canary boundary must expose loopback only")
    if _expect_bool(boundary["loopback_only"], f"{context}.boundary.loopback_only") is not True:
        _fail("network deny canary boundary loopback_only must be true")
    if _expect_bool(boundary["no_external_route"], f"{context}.boundary.no_external_route") is not True:
        _fail("network deny canary boundary must prove no external route")
    if _expect_array(boundary["errors"], f"{context}.boundary.errors"):
        _fail("network deny canary boundary errors must be empty")
    for route_family in ("ipv4_routes", "ipv6_routes"):
        for index, raw_route in enumerate(_expect_array(boundary[route_family], f"{context}.boundary.{route_family}")):
            route = _expect_object(raw_route, f"{context}.boundary.{route_family}[{index}]")
            if (
                _expect_bool(
                    route.get("loopback_only"),
                    f"{context}.boundary.{route_family}[{index}].loopback_only",
                )
                is not True
            ):
                _fail("network deny canary includes a non-loopback route")

    results = _expect_array(receipt["results"], f"{context}.results")
    if len(results) != 2:
        _fail("network deny canary must contain exactly the bounded connect and DNS-policy results")
    ipv4_result = _expect_object(results[0], f"{context}.results[0]")
    if (
        ipv4_result.get("surface") != "ipv4_tcp_connect"
        or ipv4_result.get("target_class") != "RFC5737_TEST_NET"
        or ipv4_result.get("outcome") != "policy_denied"
        or ipv4_result.get("errno") not in {errno.EACCES, errno.EPERM, errno.ENETUNREACH}
    ):
        _fail("network deny canary did not record a policy-denied bounded TEST-NET connect")
    dns_result = _expect_object(results[1], f"{context}.results[1]")
    if (
        dns_result.get("surface") != "dns_resolution"
        or dns_result.get("outcome") != "not_used_as_policy_evidence"
        or _expect_bool(dns_result.get("attempted"), f"{context}.results[1].attempted") is not False
        or _expect_bool(
            dns_result.get("accepted_as_policy_evidence"),
            f"{context}.results[1].accepted_as_policy_evidence",
        )
        is not False
    ):
        _fail("network deny canary improperly used DNS as policy evidence")


def _validate_security_receipts(
    repo_root: Path,
    artifacts: Mapping[str, Mapping[str, str]],
    phase: str,
    scope: Mapping[str, Any],
    *,
    record_issued_at: datetime,
    record_expires_at: datetime,
    verification_time: datetime,
    selection_approval_sha256: str | None,
) -> None:
    common_keys = {
        "schema_version",
        "phase",
        "status",
        "checked_at",
        "valid_until",
        "offline",
        "live_actions_authorized",
    }
    if phase == LAUNCH:
        common_keys.add("selection_approval_sha256")

    for key in SECURITY_EVIDENCE_FILENAMES:
        context = f"security_evidence.{key} receipt"
        receipt = _load_bound_json(repo_root, artifacts[key], context)
        if key == "network_deny_canary":
            _validate_network_canary_receipt(
                receipt,
                context,
                record_issued_at=record_issued_at,
                verification_time=verification_time,
            )
            continue
        if key == "egress_policy":
            expected_keys = common_keys | {
                "external_enforcement",
                "default_deny",
                "registry_access",
                "allowed_destinations",
            }
            expected_schema = "world-human-aid-egress-policy-attestation/v1"
        else:
            expected_keys = common_keys | {
                "live_secrets_present",
                "signing_material_present",
                "production_credentials_present",
                "treasury_access_present",
            }
            expected_schema = "world-human-aid-no-live-secrets-attestation/v1"
        _exact_keys(receipt, expected_keys, context)
        if receipt["schema_version"] != expected_schema:
            _fail(f"{context}.schema_version is not the strict expected receipt schema")
        if receipt["phase"] != phase or receipt["status"] != "passed":
            _fail(f"{context} must be a passed receipt for gate-0b-{phase}")
        if _expect_bool(receipt["offline"], f"{context}.offline") is not True:
            _fail(f"{context}.offline must be true")
        if (
            _expect_bool(
                receipt["live_actions_authorized"],
                f"{context}.live_actions_authorized",
            )
            is not False
        ):
            _fail(f"{context} cannot authorize live actions")
        _validate_evidence_window(
            receipt,
            context,
            checked_key="checked_at",
            record_issued_at=record_issued_at,
            record_expires_at=record_expires_at,
            verification_time=verification_time,
        )
        if phase == LAUNCH and receipt["selection_approval_sha256"] != selection_approval_sha256:
            _fail(f"{context} does not bind the exact Gate 0B selection approval digest")

        if key == "egress_policy":
            if _expect_bool(receipt["external_enforcement"], f"{context}.external_enforcement") is not True:
                _fail("egress policy must be externally enforced")
            if _expect_bool(receipt["default_deny"], f"{context}.default_deny") is not True:
                _fail("egress policy receipt must prove default deny")
            if _expect_bool(receipt["registry_access"], f"{context}.registry_access") is not False:
                _fail("egress policy receipt must prove registry access is disabled")
            destinations = _unique_strings(
                receipt["allowed_destinations"],
                f"{context}.allowed_destinations",
            )
            scope_network = _expect_object(scope["network"], "scope.network")
            if set(destinations) != set(scope_network["allowed_destinations"]):
                _fail("egress policy receipt allowed destinations differ from the signed scope")
        else:
            for field in (
                "live_secrets_present",
                "signing_material_present",
                "production_credentials_present",
                "treasury_access_present",
            ):
                if _expect_bool(receipt[field], f"{context}.{field}") is not False:
                    _fail(f"no-live-secrets receipt must prove {field} is false")


def _validate_bootstrap_receipts(
    repo_root: Path,
    artifacts: Mapping[str, Mapping[str, str]],
    selection_approval: Mapping[str, str],
    *,
    launch_issued_at: datetime,
    launch_expires_at: datetime,
    verification_time: datetime,
) -> None:
    selection_record = _load_bound_json(
        repo_root,
        selection_approval,
        "selection_evidence.approval",
    )
    selection_record_id = _expect_string(
        selection_record.get("record_id"),
        "selection_evidence.approval.record_id",
        minimum=16,
        maximum=112,
    )
    selection_issued_at = _parse_timestamp(
        selection_record.get("issued_at"),
        "selection_evidence.approval.issued_at",
    )
    selection_expires_at = _parse_timestamp(
        selection_record.get("expires_at"),
        "selection_evidence.approval.expires_at",
    )
    if launch_expires_at > selection_expires_at:
        _fail("launch approval cannot outlive its bound selection approval")

    common_keys = {
        "schema_version",
        "goal_id",
        "status",
        "completed_at",
        "valid_until",
        "offline",
        "live_actions_authorized",
        "selection_record_id",
        "selection_approval_sha256",
        "real_execution",
        "network_attempts",
        "cache_mutated",
    }
    for key, expected_goal in BOOTSTRAP_GOALS.items():
        context = f"bootstrap_receipts.{key} receipt"
        receipt = _load_bound_json(repo_root, artifacts[key], context)
        expected_keys = set(common_keys)
        if key == "duckdb":
            expected_keys.update({"single_writer_enforced", "external_access"})
        _exact_keys(receipt, expected_keys, context)
        if receipt["schema_version"] != "world-human-aid-bootstrap-verification-receipt/v1":
            _fail(f"{context}.schema_version is not the strict expected receipt schema")
        if receipt["goal_id"] != expected_goal:
            _fail(f"{context} must bind exact goal {expected_goal}")
        if receipt["status"] != "passed":
            _fail(f"{context}.status must be passed")
        completed_at = _validate_evidence_window(
            receipt,
            context,
            checked_key="completed_at",
            record_issued_at=launch_issued_at,
            record_expires_at=launch_expires_at,
            verification_time=verification_time,
        )
        if completed_at < selection_issued_at:
            _fail(f"{context} predates the bound Gate 0B selection")
        if receipt["valid_until"] != selection_record["expires_at"]:
            _fail(f"{context}.valid_until must equal the selection approval expiry")
        if receipt["selection_record_id"] != selection_record_id:
            _fail(f"{context} does not bind the exact selection record ID")
        if receipt["selection_approval_sha256"] != selection_approval["sha256"]:
            _fail(f"{context} does not bind the exact selection approval digest")
        if _expect_bool(receipt["offline"], f"{context}.offline") is not True:
            _fail(f"{context}.offline must be true")
        if (
            _expect_bool(
                receipt["live_actions_authorized"],
                f"{context}.live_actions_authorized",
            )
            is not False
        ):
            _fail(f"{context} cannot authorize live actions")
        if _expect_bool(receipt["real_execution"], f"{context}.real_execution") is not True:
            _fail(f"{context} must prove real execution")
        if _expect_int(receipt["network_attempts"], f"{context}.network_attempts", 0, 1000000) != 0:
            _fail(f"{context} must record zero network attempts")
        if _expect_bool(receipt["cache_mutated"], f"{context}.cache_mutated") is not False:
            _fail(f"{context} must prove the reviewed cache was not mutated")
        if key == "duckdb":
            if (
                _expect_bool(
                    receipt["single_writer_enforced"],
                    f"{context}.single_writer_enforced",
                )
                is not True
            ):
                _fail("DuckDB receipt must prove single_writer_enforced=true")
            if _expect_bool(receipt["external_access"], f"{context}.external_access") is not False:
                _fail("DuckDB receipt must prove external_access=false")


def _bundle_task_projection(
    payload: Mapping[str, Any],
    context: str,
) -> tuple[dict[str, Any], dict[str, set[str]], dict[str, set[str]]]:
    bundles = _expect_object(payload.get("bundles"), f"{context}.bundles")
    if not bundles:
        _fail(f"{context}.bundles must not be empty")
    goals_by_bundle: dict[str, set[str]] = {}
    cids_by_bundle: dict[str, set[str]] = {}
    seen_cids: set[str] = set()
    seen_task_ids: set[str] = set()
    for bundle_key, raw_bundle in sorted(bundles.items()):
        _expect_string(bundle_key, f"{context}.bundles key", maximum=256)
        bundle = _expect_object(raw_bundle, f"{context}.bundles[{bundle_key!r}]")
        if "bundle_key" in bundle and bundle["bundle_key"] != bundle_key:
            _fail(f"{context}.bundles[{bundle_key!r}].bundle_key differs from its key")
        tasks = _expect_array(bundle.get("tasks"), f"{context}.bundles[{bundle_key!r}].tasks")
        if not tasks:
            _fail(f"{context}.bundles[{bundle_key!r}].tasks must not be empty")
        goals: set[str] = set()
        cids: set[str] = set()
        for index, raw_task in enumerate(tasks):
            task_context = f"{context}.bundles[{bundle_key!r}].tasks[{index}]"
            task = _expect_object(raw_task, task_context)
            goal_id = _expect_string(task.get("goal_id"), f"{task_context}.goal_id", maximum=32)
            if not GOAL_RE.fullmatch(goal_id):
                _fail(f"{task_context}.goal_id is invalid")
            task_id = _expect_string(task.get("task_id"), f"{task_context}.task_id", maximum=256)
            canonical_cid = task.get("canonical_task_cid")
            fallback_cid = task.get("task_cid")
            if canonical_cid and fallback_cid and canonical_cid != fallback_cid:
                _fail(f"{task_context} has conflicting task CID fields")
            cid = _expect_string(canonical_cid or fallback_cid, f"{task_context}.canonical_task_cid", maximum=256)
            if task_id in seen_task_ids or cid in seen_cids:
                _fail(f"{task_context} duplicates a task ID or canonical CID")
            seen_task_ids.add(task_id)
            seen_cids.add(cid)
            goals.add(goal_id)
            cids.add(cid)
        goals_by_bundle[bundle_key] = goals
        cids_by_bundle[bundle_key] = cids
    return bundles, goals_by_bundle, cids_by_bundle


def _validate_derived_bundle_profile(
    repo_root: Path,
    canonical_artifact: Mapping[str, str],
    derived_artifact: Mapping[str, str],
    *,
    context: str,
    expected_goals: set[str] | frozenset[str],
    completed_prerequisite_goals: set[str] | frozenset[str],
    exact_allowed_bundles: set[str] | frozenset[str] | None,
) -> tuple[set[str], set[str]]:
    canonical = _load_bound_json(repo_root, canonical_artifact, "reviewed canonical bundle index")
    derived = _load_bound_json(repo_root, derived_artifact, context)
    canonical_bundles, goals_by_bundle, cids_by_bundle = _bundle_task_projection(
        canonical,
        "reviewed canonical bundle index",
    )
    derived_bundles, _, _ = _bundle_task_projection(derived, context)
    if set(derived_bundles) != set(canonical_bundles):
        _fail(f"{context} must preserve the exact canonical bundle-key set")
    for bundle_key, canonical_bundle in canonical_bundles.items():
        derived_bundle = derived_bundles[bundle_key]
        canonical_without_tasks = {key: value for key, value in canonical_bundle.items() if key != "tasks"}
        derived_without_tasks = {key: value for key, value in derived_bundle.items() if key != "tasks"}
        if derived_without_tasks != canonical_without_tasks:
            _fail(f"{context} may not mutate canonical bundle metadata")
        canonical_tasks = canonical_bundle["tasks"]
        derived_tasks = derived_bundle["tasks"]
        if len(derived_tasks) != len(canonical_tasks):
            _fail(f"{context} may not add or remove canonical tasks")
        for index, canonical_task in enumerate(canonical_tasks):
            expected_task = dict(canonical_task)
            if canonical_task.get("goal_id") in completed_prerequisite_goals:
                expected_task["status"] = "completed"
            if derived_tasks[index] != expected_task:
                _fail(
                    f"{context} may only set status='completed' on exact completed-prerequisite tasks; "
                    "all other task fields and CIDs must remain canonical"
                )

    if exact_allowed_bundles is None:
        allowed_bundles: set[str] = set()
        for bundle_key, goals in goals_by_bundle.items():
            if goals & set(expected_goals):
                if not goals <= set(expected_goals):
                    _fail(f"{context} cannot safely isolate a bundle containing prerequisite or excluded goals")
                allowed_bundles.add(bundle_key)
    else:
        allowed_bundles = set(exact_allowed_bundles)
    if not allowed_bundles or not allowed_bundles <= set(canonical_bundles):
        _fail(f"{context} is missing one or more required execution bundles")

    projected_goals = set().union(*(goals_by_bundle[key] for key in allowed_bundles))
    if projected_goals != set(expected_goals):
        _fail(
            f"{context} goal projection differs; "
            f"missing={sorted(set(expected_goals) - projected_goals)}, "
            f"unexpected={sorted(projected_goals - set(expected_goals))}"
        )
    execution_goal_ids = _unique_strings(
        derived.get("execution_goal_ids"),
        f"{context}.execution_goal_ids",
        minimum_items=len(expected_goals),
        maximum_items=len(expected_goals),
    )
    if execution_goal_ids != sorted(expected_goals):
        _fail(f"{context}.execution_goal_ids must be the exact sorted execution goal set")
    completed_goal_ids = _unique_strings(
        derived.get("completed_prerequisite_goal_ids"),
        f"{context}.completed_prerequisite_goal_ids",
        minimum_items=len(completed_prerequisite_goals),
        maximum_items=len(completed_prerequisite_goals),
    )
    if completed_goal_ids != sorted(completed_prerequisite_goals):
        _fail(f"{context}.completed_prerequisite_goal_ids must be the exact sorted prerequisite set")
    execution_allowlist = _unique_strings(
        derived.get("execution_allowlist"),
        f"{context}.execution_allowlist",
        minimum_items=len(allowed_bundles),
        maximum_items=len(allowed_bundles),
    )
    if execution_allowlist != sorted(allowed_bundles):
        _fail(f"{context}.execution_allowlist must be the exact sorted bundle set")
    expected_excluded = set(canonical_bundles) - allowed_bundles
    excluded = set(
        _unique_strings(
            derived.get("excluded_bundle_keys"),
            f"{context}.excluded_bundle_keys",
            minimum_items=len(expected_excluded),
            maximum_items=len(expected_excluded),
        )
    )
    if excluded != expected_excluded:
        _fail(f"{context}.excluded_bundle_keys does not fence every other canonical bundle")
    if derived.get("derived_from_bundle_index") != canonical_artifact["path"]:
        _fail(f"{context}.derived_from_bundle_index does not bind the canonical bundle index")
    projected_cids = set().union(*(cids_by_bundle[key] for key in allowed_bundles))
    return projected_cids, allowed_bundles


def _validate_preflight_receipt(
    repo_root: Path,
    reviewed_state: Mapping[str, Any],
    generated_root: Path,
) -> None:
    receipt = _load_bound_json(
        repo_root,
        reviewed_state["preflight_receipt"],
        "reviewed_state.preflight_receipt",
    )
    _exact_keys(
        receipt,
        {
            "schema",
            "status",
            "passed",
            "offline",
            "no_start",
            "generated_root",
            "objective_path",
            "summary",
            "verifiers",
            "artifacts",
        },
        "reviewed_state.preflight_receipt",
    )
    if receipt["schema"] != PREFLIGHT_RECEIPT_SCHEMA:
        _fail("preflight receipt schema is not the deterministic generated-board receipt")
    if receipt["status"] != "passed":
        _fail("preflight receipt status must be passed")
    for key in ("passed", "offline", "no_start"):
        if _expect_bool(receipt[key], f"preflight receipt.{key}") is not True:
            _fail(f"preflight receipt.{key} must be true")
    if receipt["generated_root"] != generated_root.as_posix():
        _fail("preflight receipt generated_root differs from the immutable reviewed root")
    if receipt["objective_path"] != CANONICAL_SOURCE_PATHS["objective_heap"]:
        _fail("preflight receipt objective_path differs from the canonical objective heap")
    summary = _expect_object(receipt["summary"], "preflight receipt summary")
    _exact_keys(
        summary,
        {
            "status",
            "source_goal_count",
            "schedulable_goal_count",
            "task_count",
            "bundle_count",
            "dag_count",
        },
        "preflight receipt summary",
    )
    if summary["status"] != "passed":
        _fail("preflight receipt summary.status must be passed")
    for key in (
        "source_goal_count",
        "schedulable_goal_count",
        "task_count",
        "bundle_count",
        "dag_count",
    ):
        _expect_int(summary[key], f"preflight receipt summary.{key}", 1, 1000000000)

    verifiers = _expect_object(receipt["verifiers"], "preflight receipt verifiers")
    _exact_keys(
        verifiers,
        {"generated_board", "preflight_receipt"},
        "preflight receipt verifiers",
    )
    expected_verifier_paths = {
        "generated_board": "scripts/verify_world_aid_generated_board.py",
        "preflight_receipt": "scripts/verify_world_aid_preflight_receipt.py",
    }
    for key, expected_path in expected_verifier_paths.items():
        context = f"preflight receipt verifiers.{key}"
        verifier = _expect_object(verifiers[key], context)
        _exact_keys(verifier, {"path", "sha256", "size"}, context)
        artifact = _validate_artifact_shape(
            {"path": verifier["path"], "sha256": verifier["sha256"]},
            context,
        )
        if artifact["path"] != expected_path:
            _fail(f"{context}.path must be {expected_path}")
        expected_size = _expect_int(verifier["size"], f"{context}.size", 1, 1073741824)
        verifier_path = _safe_repo_path(
            repo_root,
            artifact["path"],
            f"{context}.path",
            must_exist=True,
            require_file=True,
        )
        if verifier_path.stat().st_size != expected_size or _sha256_file(verifier_path) != artifact["sha256"]:
            _fail(f"preflight receipt verifier digest drift for {artifact['path']}")

    artifacts = _expect_array(receipt["artifacts"], "preflight receipt artifacts")
    if not artifacts:
        _fail("preflight receipt artifacts must not be empty")
    by_path: dict[str, dict[str, Any]] = {}
    for index, raw_artifact in enumerate(artifacts):
        context = f"preflight receipt artifacts[{index}]"
        artifact = _expect_object(raw_artifact, context)
        _exact_keys(artifact, {"role", "path", "size", "sha256"}, context)
        _expect_string(artifact["role"], f"{context}.role", maximum=128)
        path_text = _validate_relative_path_text(artifact["path"], f"{context}.path")
        if generated_root not in Path(path_text).parents:
            _fail(f"{context}.path must remain under the immutable generated root")
        if path_text in by_path:
            _fail("preflight receipt artifact paths must be unique")
        digest = _expect_string(artifact["sha256"], f"{context}.sha256", minimum=71, maximum=71)
        if not DIGEST_RE.fullmatch(digest):
            _fail(f"{context}.sha256 must be a lowercase sha256 digest")
        size = _expect_int(artifact["size"], f"{context}.size", 0, 1099511627776)
        path = _safe_repo_path(
            repo_root,
            path_text,
            f"{context}.path",
            must_exist=True,
            require_file=True,
        )
        if path.stat().st_size != size or _sha256_file(path) != digest:
            _fail(f"preflight receipt artifact drift for {path_text}")
        by_path[path_text] = artifact

    required_paths = {
        (generated_root / "WORLDCOIN_HUMAN_AID_TODO.md").as_posix(),
        (generated_root / "objective_graph.json").as_posix(),
        (generated_root / "objective_bundles/index.json").as_posix(),
        (generated_root / "objective_bundles/index.duckdb").as_posix(),
        (generated_root / "objective_bundles/todo_vector_index.json").as_posix(),
        (generated_root / "plan_evaluations.json").as_posix(),
        (generated_root / "objective_generation.json").as_posix(),
        (generated_root / "launch_profiles/g002-only.index.json").as_posix(),
        (generated_root / "launch_profiles/g002-only.index.duckdb").as_posix(),
        (generated_root / "launch_profiles/gate0b-preparation.index.json").as_posix(),
        (generated_root / "launch_profiles/gate0b-preparation.index.duckdb").as_posix(),
        (generated_root / "launch_profiles/g038-g040.index.json").as_posix(),
        (generated_root / "launch_profiles/g038-g040.index.duckdb").as_posix(),
        (generated_root / "launch_profiles/implementation.index.json").as_posix(),
        (generated_root / "launch_profiles/implementation.index.duckdb").as_posix(),
    }
    missing = required_paths - set(by_path)
    if missing:
        _fail(f"preflight receipt omits required immutable generated artifacts: {sorted(missing)}")
    for key in ("full_board", "objective_graph", "bundle_index"):
        artifact = reviewed_state[key]
        receipt_artifact = by_path.get(artifact["path"])
        if receipt_artifact is None or receipt_artifact["sha256"] != artifact["sha256"]:
            _fail(f"preflight receipt does not exactly bind reviewed_state.{key}")
    roles = [artifact["role"] for artifact in by_path.values()]
    required_roles = {
        "full_board",
        "objective_graph",
        "bundle_index_json",
        "bundle_index_duckdb",
        "todo_vector_index",
        "plan_evaluations",
        "objective_generation",
        "launch_profile_json",
        "launch_profile_duckdb",
    }
    if not required_roles <= set(roles) or "discovery" not in roles or "bundle_shard" not in roles:
        _fail("preflight receipt omits required generated artifact roles")


def _validate_dry_run_manifest(
    repo_root: Path,
    manifest_artifact: Mapping[str, str],
    implementation_index_duckdb_artifact: Mapping[str, str],
    *,
    expected_goals: set[str],
    expected_cids: set[str],
    expected_bundles: set[str],
) -> None:
    manifest = _load_bound_json(repo_root, manifest_artifact, "reviewed_state.dry_run_receipt")
    schema = _expect_string(manifest.get("schema"), "dry-run manifest.schema", maximum=128)
    if schema not in DRY_RUN_SCHEMAS:
        _fail("dry-run manifest schema is not a supported bundle-supervisor schema")
    if manifest.get("bundle_index_path") != implementation_index_duckdb_artifact["path"]:
        _fail("dry-run manifest does not bind the signed implementation DuckDB index")
    planned_count = _expect_int(manifest.get("planned_count"), "dry-run manifest.planned_count", 1, 1000000)
    if planned_count != len(expected_bundles):
        _fail("dry-run manifest planned_count differs from the implementation bundle projection")
    if _expect_int(manifest.get("started_count"), "dry-run manifest.started_count", 0, 1000000) != 0:
        _fail("dry-run manifest proves that workers were started")
    for key in ("running_count", "active_worker_count"):
        value = manifest.get(key, 0)
        if _expect_int(value, f"dry-run manifest.{key}", 0, 1000000) != 0:
            _fail(f"dry-run manifest.{key} must be zero")
    for key in ("started", "active_worker_pids", "launched_task_cids"):
        values = _expect_array(manifest.get(key, []), f"dry-run manifest.{key}")
        if values:
            _fail(f"dry-run manifest.{key} must be empty")

    planned_tasks: list[Mapping[str, Any]] = []
    if schema == "ipfs_accelerate_py.agent_supervisor.bundle_supervisor":
        lanes = _expect_array(manifest.get("lanes"), "dry-run manifest.lanes")
        if len(lanes) != planned_count:
            _fail("dry-run manifest lane count differs from planned_count")
        observed_bundles: set[str] = set()
        for index, raw_lane in enumerate(lanes):
            lane = _expect_object(raw_lane, f"dry-run manifest.lanes[{index}]")
            bundle_key = _expect_string(
                lane.get("bundle_key"),
                f"dry-run manifest.lanes[{index}].bundle_key",
                maximum=256,
            )
            observed_bundles.add(bundle_key)
            queue_payload = _expect_object(
                lane.get("queue_payload"),
                f"dry-run manifest.lanes[{index}].queue_payload",
            )
            planned_tasks.extend(
                _expect_array(
                    queue_payload.get("tasks"),
                    f"dry-run manifest.lanes[{index}].queue_payload.tasks",
                )
            )
    else:
        task_states = _expect_array(manifest.get("tasks"), "dry-run manifest.tasks")
        observed_bundles = set()
        for index, raw_state in enumerate(task_states):
            state = _expect_object(raw_state, f"dry-run manifest.tasks[{index}]")
            bundle = _expect_object(state.get("bundle"), f"dry-run manifest.tasks[{index}].bundle")
            bundle_key = _expect_string(
                bundle.get("bundle_key"),
                f"dry-run manifest.tasks[{index}].bundle.bundle_key",
                maximum=256,
            )
            observed_bundles.add(bundle_key)
            planned_tasks.extend(
                _expect_array(
                    bundle.get("tasks"),
                    f"dry-run manifest.tasks[{index}].bundle.tasks",
                )
            )
    if observed_bundles != expected_bundles:
        _fail("dry-run manifest bundle set differs from the implementation profile")

    observed_goals: set[str] = set()
    observed_cids: set[str] = set()
    for index, raw_task in enumerate(planned_tasks):
        task = _expect_object(raw_task, f"dry-run manifest planned task[{index}]")
        goal_id = _expect_string(task.get("goal_id"), f"dry-run manifest planned task[{index}].goal_id")
        cid = _expect_string(
            task.get("canonical_task_cid") or task.get("task_cid"),
            f"dry-run manifest planned task[{index}].canonical_task_cid",
        )
        if cid in observed_cids:
            _fail("dry-run manifest planned task CIDs must be unique")
        observed_goals.add(goal_id)
        observed_cids.add(cid)
    if observed_goals != expected_goals or observed_cids != expected_cids:
        _fail("dry-run manifest task goal/CID projection differs from the implementation profile")


def _verify_approval(
    *,
    repo_root: Path,
    phase: str,
    approval_path: Path,
    allowed_signers_path: Path,
    now: datetime | None,
    verify_linked_selection: bool,
    historical_link: bool,
) -> dict[str, Any]:
    if phase not in {SELECTION, LAUNCH}:
        _fail("phase must be selection or launch")
    _verify_trusted_executable(TRUSTED_GIT, "git")
    _verify_trusted_executable(TRUSTED_SSH_KEYGEN, "ssh-keygen")
    try:
        root = repo_root.resolve(strict=True)
    except OSError as exc:
        _fail(f"repository root cannot be resolved: {exc}")
    if not root.is_dir():
        _fail("repository root must be a directory")
    canonical_approval = _canonical_approval_path(root, phase, approval_path)

    try:
        if allowed_signers_path.is_symlink():
            _fail("allowed signers trust store cannot be a symlink")
        trust_path = allowed_signers_path.resolve(strict=True)
    except OSError as exc:
        _fail(f"allowed signers trust store cannot be resolved: {exc}")
    if not trust_path.is_file() or trust_path.is_symlink():
        _fail("allowed signers trust store must be a regular, non-symlink file")
    try:
        trust_path.relative_to(root)
    except ValueError:
        pass
    else:
        _fail("allowed signers trust store must be outside the repository")
    try:
        trust_mode = trust_path.stat().st_mode
    except OSError as exc:
        _fail(f"allowed signers trust store cannot be inspected: {exc}")
    if trust_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH):
        _fail("allowed signers trust store must be read-only")

    verification_time = now or datetime.now(UTC)
    if verification_time.tzinfo is None or verification_time.utcoffset() != timedelta(0):
        _fail("verification time must be timezone-aware UTC")
    verification_time = verification_time.astimezone(UTC).replace(microsecond=0)

    record, raw = _load_json_strict(canonical_approval)
    common_keys = {
        "schema_version",
        "gate_id",
        "record_id",
        "decision",
        "issued_at",
        "not_before",
        "expires_at",
        "reviewed_state",
        "scope",
        "reviewers",
        "exceptions",
        "trust",
    }
    if phase == SELECTION:
        phase_keys = {"dependency_sets", "security_evidence"}
    else:
        phase_keys = {"selection_evidence", "bootstrap_receipts", "security_evidence"}
    _exact_keys(record, common_keys | phase_keys, "approval")

    if record["schema_version"] != SCHEMA_VERSIONS[phase]:
        _fail("schema_version does not match the selected phase")
    if record["gate_id"] != GATE_IDS[phase]:
        _fail("gate_id does not match the selected phase")
    record_id = _expect_string(record["record_id"], "record_id", minimum=16, maximum=112)
    if not RECORD_ID_RE[phase].fullmatch(record_id):
        _fail("record_id is invalid for the selected phase")
    if record["decision"] != "approved":
        _fail("decision must be approved; templates and pending records are not approval")

    issued_at = _parse_timestamp(record["issued_at"], "issued_at")
    not_before = _parse_timestamp(record["not_before"], "not_before")
    expires_at = _parse_timestamp(record["expires_at"], "expires_at")
    if issued_at > verification_time:
        _fail("record was issued in the future")
    if not issued_at <= not_before <= verification_time:
        _fail("record is not yet valid or has inconsistent issuance")
    if expires_at <= verification_time:
        _fail("record is stale or expired")
    if not_before >= expires_at:
        _fail("record validity interval is empty")
    if expires_at - issued_at > MAX_RECORD_VALIDITY:
        _fail("record validity exceeds 31 days")

    root_commit, submodule_commits, artifacts, generated_root = _validate_reviewed_state(
        record["reviewed_state"],
        phase,
    )
    reviewer_identities = _validate_reviewers(record["reviewers"], phase, issued_at, expires_at, verification_time)
    _validate_exceptions(record["exceptions"], issued_at, expires_at, verification_time)
    signatures = _validate_trust_shape(record["trust"], phase, reviewer_identities)

    if phase == SELECTION:
        artifacts.extend(_validate_selection_dependencies(record["dependency_sets"], root))
        security_artifacts, security_by_key = _validate_security_evidence_shape(
            record["security_evidence"],
            SELECTION,
        )
        artifacts.extend(security_artifacts)
        selection_approval_artifact: dict[str, str] | None = None
        bootstrap_by_key: dict[str, dict[str, str]] = {}
    else:
        (
            launch_artifacts,
            selection_approval_artifact,
            bootstrap_by_key,
            security_by_key,
        ) = _validate_launch_evidence(record)
        artifacts.extend(launch_artifacts)

    seen_artifacts: dict[str, str] = {}
    for context, artifact in artifacts:
        _verify_artifact(root, artifact, context, seen_artifacts, canonical_approval)

    # Never parse or otherwise act on a bound artifact until every declared
    # digest has been verified.  Besides preserving a clear fail-closed error
    # boundary, this prevents tampered heap content from influencing semantic
    # scope validation before its integrity failure is reported.
    _validate_scope(
        record["scope"],
        phase,
        root,
        generated_root,
        (Path(artifact["path"]) for _, artifact in artifacts),
    )
    _validate_preflight_receipt(root, record["reviewed_state"], generated_root)
    if phase == SELECTION:
        _validate_derived_bundle_profile(
            root,
            record["reviewed_state"]["bundle_index"],
            record["reviewed_state"]["restricted_bundle_index"],
            context="reviewed_state.restricted_bundle_index",
            expected_goals=SELECTION_GOALS,
            completed_prerequisite_goals=SELECTION_PREPARATION_GOALS,
            exact_allowed_bundles=RESTRICTED_BOOTSTRAP_BUNDLES,
        )
        _validate_security_receipts(
            root,
            security_by_key,
            SELECTION,
            record["scope"],
            record_issued_at=issued_at,
            record_expires_at=expires_at,
            verification_time=verification_time,
            selection_approval_sha256=None,
        )
    else:
        if selection_approval_artifact is None:
            _fail("launch approval omitted selection evidence")
        implementation_goals = _schedulable_goals_from_heap(root) - LAUNCH_PREREQUISITE_GOALS
        implementation_cids, implementation_bundles = _validate_derived_bundle_profile(
            root,
            record["reviewed_state"]["bundle_index"],
            record["reviewed_state"]["implementation_bundle_index"],
            context="reviewed_state.implementation_bundle_index",
            expected_goals=implementation_goals,
            completed_prerequisite_goals=LAUNCH_PREREQUISITE_GOALS,
            exact_allowed_bundles=None,
        )
        _validate_dry_run_manifest(
            root,
            record["reviewed_state"]["dry_run_receipt"],
            record["reviewed_state"]["implementation_bundle_index_duckdb"],
            expected_goals=implementation_goals,
            expected_cids=implementation_cids,
            expected_bundles=implementation_bundles,
        )
        _validate_bootstrap_receipts(
            root,
            bootstrap_by_key,
            selection_approval_artifact,
            launch_issued_at=issued_at,
            launch_expires_at=expires_at,
            verification_time=verification_time,
        )
        _validate_security_receipts(
            root,
            security_by_key,
            LAUNCH,
            record["scope"],
            record_issued_at=issued_at,
            record_expires_at=expires_at,
            verification_time=verification_time,
            selection_approval_sha256=selection_approval_artifact["sha256"],
        )

    _verify_git_state(
        root,
        root_commit,
        submodule_commits,
        phase,
        historical_link=historical_link,
    )

    observed_trust_digest = _sha256_file(trust_path)
    if observed_trust_digest != record["trust"]["allowed_signers_sha256"]:
        _fail("allowed signers trust-store digest drift")
    allowed_principals = _parse_allowed_signers(trust_path)

    _verify_signatures(
        canonical_approval,
        raw,
        phase,
        signatures,
        trust_path,
        allowed_principals,
    )

    if phase == LAUNCH and verify_linked_selection:
        if selection_approval_artifact is None:
            _fail("launch approval omitted selection evidence")
        _verify_approval(
            repo_root=root,
            phase=SELECTION,
            approval_path=root / selection_approval_artifact["path"],
            allowed_signers_path=trust_path,
            now=verification_time,
            verify_linked_selection=False,
            historical_link=True,
        )

    return {
        "status": "verified",
        "phase": phase,
        "gate_id": GATE_IDS[phase],
        "record_id": record_id,
        "expires_at": record["expires_at"],
        "reviewed_root_commit": root_commit,
        "artifact_count": len(seen_artifacts),
        "signature_count": len(signatures),
        "offline": True,
        "live_actions_authorized": False,
    }


def verify_approval(
    *,
    repo_root: Path,
    phase: str,
    approval_path: Path,
    allowed_signers_path: Path,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Verify one approval and return a non-secret summary.

    Raises:
        ApprovalVerificationError: If any structural, temporal, digest, git,
            trust-store, or detached-signature check fails.
    """

    return _verify_approval(
        repo_root=repo_root,
        phase=phase,
        approval_path=approval_path,
        allowed_signers_path=allowed_signers_path,
        now=now,
        verify_linked_selection=True,
        historical_link=False,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=(SELECTION, LAUNCH), required=True)
    parser.add_argument("--approval", type=Path, required=True)
    parser.add_argument("--allowed-signers", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Required acknowledgement that verification runs with external access denied.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not args.offline:
        print("Gate 0B verification rejected: --offline is required", file=sys.stderr)
        return 2
    try:
        summary = verify_approval(
            repo_root=args.repo_root,
            phase=args.phase,
            approval_path=args.approval,
            allowed_signers_path=args.allowed_signers,
        )
    except ApprovalVerificationError as exc:
        print(f"Gate 0B verification rejected: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(summary, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
