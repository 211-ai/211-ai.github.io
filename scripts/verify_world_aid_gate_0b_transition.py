#!/usr/bin/env python3
"""Verify the signed Gate 0B blocked-to-reopened transition contract.

This verifier authorizes only a reviewed source-state transition.  It never
authorizes runtime execution, starts a supervisor, regenerates a board, signs a
record, or treats the pending template as an approval.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import ctypes
import fcntl
import hashlib
import json
import os
import re
import shlex
import stat
import subprocess
import sys
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path, PurePosixPath
from typing import Any

SCHEMA_VERSION = "world-human-aid-gate-0b-transition/v1"
GATE_ID = "gate-0b-transition"
SIGNATURE_NAMESPACE = "world-aid-gate-0b-transition-v1"
SIGNER_POLICY_ID = "world-aid-gate-0b-transition-signers/v1"
SOURCE_BOARD_CONTRACT = "blocked-review-v1"
TARGET_BOARD_CONTRACT = "gate0b-selection-reopened-v1"
LAUNCHER_PROTOCOL_ID = "world-aid-gate-first-launcher/v1"
DEPLOYMENT_ATTESTATION_SCHEMA = (
    "world-aid-gate-first-deployment-conformance-attestation/v1"
)
GATE_VERIFIER_ID = "world-aid-gate-0b-verifier/v1"
TRUST_POLICY_ID = "world-aid-gate-first-operator-policy/v1"
TRUST_POLICY_DEPLOYMENT_PATH = "/etc/world-aid/gate-first-policy.json"

CANONICAL_RECORD_PATH = Path(
    "data/worldcoin_human_aid/approvals/gate-0b-transition/transition.json"
)
CANONICAL_TARGET_HEAP_PATH = (
    "docs/planning/WORLDCOIN_HUMAN_AID_OBJECTIVE_HEAP.md"
)
GENERATED_ROOT_PARENT = PurePosixPath(
    "data/worldcoin_human_aid/agent_supervisor/regenerations"
)
CANONICAL_LAUNCHER_PATH = "scripts/world_aid_gate_first_launcher.py"
CANONICAL_LAUNCHER_PROTOCOL_PATH = (
    "docs/specs/WORLD_AID_GATE_FIRST_LAUNCHER.md"
)
CANONICAL_GATE_VERIFIER_PATH = "scripts/verify_world_aid_gate_0b.py"
CANONICAL_DEPLOYMENT_ATTESTATION_PATH = (
    "data/worldcoin_human_aid/gate_evidence/gate-0b-transition/"
    "deployment-conformance-attestation.json"
)
TRUSTED_SSH_KEYGEN = Path("/usr/bin/ssh-keygen")
TRUSTED_GIT = Path("/usr/bin/git")

TRANSITION_GOALS = (
    "WORLDCOIN-G038",
    "WORLDCOIN-G039",
    "WORLDCOIN-G040",
)
REQUIRED_SIGNER_ROLES = frozenset(
    {
        "governance-owner",
        "independent-operator",
        "repository-maintainer",
        "security-reviewer",
    }
)
GENERATED_ARTIFACT_PATHS = {
    "taskboard": "WORLDCOIN_HUMAN_AID_TODO.md",
    "task_index": "objective_bundles/todo_vector_index.json",
    "bundle_index": "objective_bundles/index.json",
    "dependency_dag": "objective_graph.json",
    "preflight_receipt": "preflight-receipt.json",
}

COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
RECORD_ID_RE = re.compile(
    r"^gate-0b-transition-[a-z0-9][a-z0-9._-]{7,95}$"
)
ATTESTATION_ID_RE = re.compile(
    r"^gate-first-deployment-[a-z0-9][a-z0-9._-]{7,95}$"
)
IDENTITY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9@._+-]{2,253}$")
FINGERPRINT_RE = re.compile(r"^SHA256:[A-Za-z0-9+/]{43}$")
TIMESTAMP_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"
)
MAX_JSON_BYTES = 16 * 1024 * 1024
MAX_ARTIFACT_BYTES = 128 * 1024 * 1024
MAX_TRUST_BYTES = 16 * 1024 * 1024
MAX_SIGNATURE_BYTES = 64 * 1024


class TransitionVerificationError(ValueError):
    """Raised when a Gate 0B transition record fails closed."""


class _DuplicateKeyError(ValueError):
    pass


def _fail(message: str) -> None:
    raise TransitionVerificationError(message)


def _sha256_bytes(raw: bytes) -> str:
    return f"sha256:{hashlib.sha256(raw).hexdigest()}"


def canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    """Return the only record representation accepted for signatures."""

    try:
        rendered = json.dumps(
            payload,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as exc:
        _fail(f"transition record cannot be encoded canonically: {exc}")
    return (rendered + "\n").encode("utf-8")


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON number {value}")


def _pairs_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKeyError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def _load_json_bytes(
    raw: bytes,
    label: str,
    *,
    require_canonical: bool = False,
) -> dict[str, Any]:
    if len(raw) > MAX_JSON_BYTES:
        _fail(f"{label} exceeds the JSON size limit")
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_pairs_without_duplicates,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        _fail(f"{label} is not strict JSON: {exc}")
    if not isinstance(value, dict):
        _fail(f"{label} root must be an object")
    if require_canonical and canonical_json_bytes(value) != raw:
        _fail(f"{label} is not canonical JSON")
    return value


def _object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail(f"{label} must be an object")
    return value


def _array(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        _fail(f"{label} must be an array")
    return value


def _string(
    value: Any,
    label: str,
    *,
    minimum: int = 1,
    maximum: int = 4096,
) -> str:
    if not isinstance(value, str) or not minimum <= len(value) <= maximum:
        _fail(f"{label} must be a string of length {minimum}..{maximum}")
    if "\x00" in value:
        _fail(f"{label} contains NUL")
    return value


def _bool(value: Any, label: str) -> bool:
    if type(value) is not bool:
        _fail(f"{label} must be a boolean")
    return value


def _exact_keys(
    value: Mapping[str, Any],
    expected: set[str] | frozenset[str],
    label: str,
) -> None:
    observed = set(value)
    missing = sorted(set(expected) - observed)
    extra = sorted(observed - set(expected))
    if missing or extra:
        _fail(f"{label} keys differ; missing={missing}, extra={extra}")


def _digest(value: Any, label: str) -> str:
    text = _string(value, label, minimum=71, maximum=71)
    if not DIGEST_RE.fullmatch(text):
        _fail(f"{label} must be a lowercase sha256 digest")
    return text


def _commit(value: Any, label: str) -> str:
    text = _string(value, label, minimum=40, maximum=40)
    if not COMMIT_RE.fullmatch(text):
        _fail(f"{label} must be a full lowercase Git commit ID")
    return text


def _timestamp(value: Any, label: str) -> datetime:
    text = _string(value, label, minimum=20, maximum=20)
    if not TIMESTAMP_RE.fullmatch(text):
        _fail(f"{label} must be a second-precision UTC timestamp")
    try:
        return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=UTC
        )
    except ValueError as exc:
        _fail(f"{label} is not a real timestamp: {exc}")


def _relative_path(value: Any, label: str) -> str:
    text = _string(value, label, maximum=512)
    if (
        "\\" in text
        or "//" in text
        or any(ord(character) < 32 or ord(character) == 127 for character in text)
    ):
        _fail(f"{label} must be a normalized POSIX repository-relative path")
    pure = PurePosixPath(text)
    if (
        pure.is_absolute()
        or text != pure.as_posix()
        or not pure.parts
        or any(part in {"", ".", ".."} for part in pure.parts)
    ):
        _fail(f"{label} escapes or is not normalized")
    return text


def _generated_root(value: Any, label: str) -> str:
    text = _relative_path(value, label)
    pure = PurePosixPath(text)
    if pure.parent != GENERATED_ROOT_PARENT:
        _fail(f"{label} must be one direct immutable generated root")
    return text


def _read_repo_file(repo_root: Path, relative: str, label: str) -> bytes:
    root = repo_root.resolve()
    pure = PurePosixPath(_relative_path(relative, label))
    candidate = root.joinpath(*pure.parts)
    current = root
    for part in pure.parts[:-1]:
        current = current / part
        if current.is_symlink():
            _fail(f"{label} traverses a symlink")
    descriptor = -1
    try:
        descriptor = os.open(
            candidate,
            os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0),
        )
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            _fail(f"{label} must be a regular file")
        if before.st_size > MAX_ARTIFACT_BYTES:
            _fail(f"{label} exceeds the artifact size limit")
        chunks: list[bytes] = []
        remaining = MAX_ARTIFACT_BYTES + 1
        while remaining:
            chunk = os.read(descriptor, min(1024 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
        if len(raw) > MAX_ARTIFACT_BYTES:
            _fail(f"{label} exceeds the artifact size limit")
        after = os.fstat(descriptor)
    except OSError as exc:
        _fail(f"cannot read {label}: {exc}")
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
        before.st_ctime_ns,
    ) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
    ):
        _fail(f"{label} changed while being read")
    try:
        candidate.resolve(strict=True).relative_to(root)
    except (OSError, RuntimeError, ValueError):
        _fail(f"{label} escapes the repository")
    return raw


def _verify_artifact(
    repo_root: Path,
    value: Any,
    label: str,
    *,
    expected_path: str | None = None,
    must_not_reuse: bool = False,
) -> tuple[str, str, bytes]:
    artifact = _object(value, label)
    expected_keys = {"path", "sha256"}
    if must_not_reuse:
        expected_keys.add("reuse_policy")
    _exact_keys(artifact, expected_keys, label)
    path = _relative_path(artifact["path"], f"{label}.path")
    if expected_path is not None and path != expected_path:
        _fail(f"{label}.path must be {expected_path}")
    digest = _digest(artifact["sha256"], f"{label}.sha256")
    if must_not_reuse and artifact["reuse_policy"] != "must_not_reuse":
        _fail(f"{label}.reuse_policy must be must_not_reuse")
    raw = _read_repo_file(repo_root, path, label)
    if _sha256_bytes(raw) != digest:
        _fail(f"{label} digest drift")
    return path, digest, raw


def _heap_binding(value: Any, label: str) -> tuple[str, str]:
    artifact = _object(value, label)
    _exact_keys(artifact, {"path", "sha256"}, label)
    path = _relative_path(artifact["path"], f"{label}.path")
    if path != CANONICAL_TARGET_HEAP_PATH:
        _fail(f"{label}.path must be {CANONICAL_TARGET_HEAP_PATH}")
    return path, _digest(artifact["sha256"], f"{label}.sha256")


def _trusted_git_environment() -> dict[str, str]:
    return {
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_SYSTEM": "/dev/null",
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "LANG": "C",
        "LC_ALL": "C",
        "PATH": "/usr/bin:/bin",
    }


def _run_git(
    repo_root: Path,
    *arguments: str,
    check: bool = True,
) -> subprocess.CompletedProcess[bytes]:
    if (
        not TRUSTED_GIT.is_file()
        or TRUSTED_GIT.is_symlink()
        or TRUSTED_GIT.stat().st_mode & (stat.S_IWGRP | stat.S_IWOTH)
    ):
        _fail("trusted Git executable is unavailable or unsafe")
    try:
        result = subprocess.run(
            [
                str(TRUSTED_GIT),
                "-c",
                "core.fsmonitor=false",
                "-c",
                "core.hooksPath=/dev/null",
                "-C",
                str(repo_root),
                *arguments,
            ],
            check=False,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=15,
            env=_trusted_git_environment(),
        )
    except (OSError, subprocess.SubprocessError) as exc:
        _fail(f"trusted Git operation failed to run: {exc}")
    if check and result.returncode != 0:
        _fail(
            "trusted Git operation rejected the transition history: "
            + result.stderr.decode("utf-8", errors="replace").strip()
        )
    return result


def _committed_heap_bytes(
    repo_root: Path,
    *,
    source_commit: str,
    target_commit: str,
) -> tuple[bytes, bytes]:
    for label, commit in (
        ("source", source_commit),
        ("target", target_commit),
    ):
        resolved = _run_git(
            repo_root,
            "rev-parse",
            "--verify",
            f"{commit}^{{commit}}",
        ).stdout.decode("ascii", errors="strict").strip()
        if resolved != commit:
            _fail(f"{label} commit does not resolve to its exact declared ID")
    if (
        _run_git(
            repo_root,
            "merge-base",
            "--is-ancestor",
            source_commit,
            target_commit,
            check=False,
        ).returncode
        != 0
    ):
        _fail("source commit is not an ancestor of target commit")
    head = _run_git(repo_root, "rev-parse", "--verify", "HEAD").stdout.decode(
        "ascii",
        errors="strict",
    ).strip()
    if head != target_commit:
        _fail("target commit must equal the exact current HEAD")
    heaps: list[bytes] = []
    for label, commit in (
        ("source", source_commit),
        ("target", target_commit),
    ):
        result = _run_git(
            repo_root,
            "show",
            "--no-ext-diff",
            "--no-textconv",
            f"{commit}:{CANONICAL_TARGET_HEAP_PATH}",
        )
        if len(result.stdout) > MAX_ARTIFACT_BYTES:
            _fail(f"{label} committed objective heap exceeds the size limit")
        heaps.append(result.stdout)
    return heaps[0], heaps[1]


def _normalize_status(value: Any, label: str) -> str:
    return (
        _string(value, label, maximum=64)
        .strip()
        .lower()
        .replace("-", "_")
        .replace(" ", "_")
    )


def _heap_statuses(raw: bytes, label: str) -> dict[str, str]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        _fail(f"{label} is not UTF-8: {exc}")
    headings = list(
        re.finditer(
            r"^## (WORLDCOIN-G[0-9]{3}) .+$",
            text,
            flags=re.MULTILINE,
        )
    )
    if not headings:
        _fail(f"{label} contains no objective goals")
    statuses: dict[str, str] = {}
    for index, heading in enumerate(headings):
        goal_id = heading.group(1)
        if goal_id in statuses:
            _fail(f"{label} duplicates {goal_id}")
        end = (
            headings[index + 1].start()
            if index + 1 < len(headings)
            else len(text)
        )
        block = text[heading.end() : end]
        status = re.search(r"^- Status: (.+)$", block, flags=re.MULTILINE)
        if status is None:
            _fail(f"{label} omits status for {goal_id}")
        statuses[goal_id] = _normalize_status(
            status.group(1),
            f"{label} {goal_id} status",
        )
    return statuses


def _taskboard_statuses(raw: bytes, label: str) -> dict[str, list[str]]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        _fail(f"{label} is not UTF-8: {exc}")
    headings = list(re.finditer(r"^## .+$", text, flags=re.MULTILINE))
    statuses: dict[str, list[str]] = {}
    for index, heading in enumerate(headings):
        end = (
            headings[index + 1].start()
            if index + 1 < len(headings)
            else len(text)
        )
        block = text[heading.end() : end]
        goal = re.search(
            r"^- Goal id: (WORLDCOIN-G[0-9]{3})$",
            block,
            flags=re.IGNORECASE | re.MULTILINE,
        )
        status = re.search(r"^- Status: (.+)$", block, flags=re.MULTILINE)
        if goal is None or status is None:
            continue
        goal_id = goal.group(1).upper()
        statuses.setdefault(goal_id, []).append(
            _normalize_status(status.group(1), f"{label} {goal_id} status")
        )
    return statuses


def _require_blocked_taskboard(raw: bytes) -> None:
    statuses = _taskboard_statuses(raw, "source generated taskboard")
    for goal_id in TRANSITION_GOALS:
        projected = statuses.get(goal_id, [])
        if not projected or set(projected) != {"blocked"}:
            _fail(
                "source generated taskboard must project every transition goal "
                f"only as blocked; {goal_id}={projected}"
            )


def _require_blocked_bundle_index(raw: bytes) -> None:
    payload = _load_json_bytes(raw, "source bundle index")
    bundles = _object(payload.get("bundles"), "source bundle index.bundles")
    statuses: dict[str, list[str]] = {}
    for bundle_key, raw_bundle in bundles.items():
        bundle = _object(
            raw_bundle,
            f"source bundle index.bundles[{bundle_key!r}]",
        )
        for index, raw_task in enumerate(
            _array(bundle.get("tasks"), f"source bundle {bundle_key!r}.tasks")
        ):
            task = _object(raw_task, f"source bundle {bundle_key!r}.tasks[{index}]")
            goal_id = task.get("goal_id")
            if goal_id not in TRANSITION_GOALS:
                continue
            statuses.setdefault(goal_id, []).append(
                _normalize_status(
                    task.get("status"),
                    f"source bundle task {goal_id} status",
                )
            )
    for goal_id in TRANSITION_GOALS:
        projected = statuses.get(goal_id, [])
        if not projected or set(projected) != {"blocked"}:
            _fail(
                "source bundle index must project every transition goal only "
                f"as blocked; {goal_id}={projected}"
            )


def _require_blocked_dependency_dag(raw: bytes) -> None:
    payload = _load_json_bytes(raw, "source dependency DAG")
    goals = _array(payload.get("goals"), "source dependency DAG.goals")
    statuses: dict[str, str] = {}
    for index, raw_goal in enumerate(goals):
        goal = _object(raw_goal, f"source dependency DAG.goals[{index}]")
        goal_id = goal.get("goal_id")
        if goal_id not in TRANSITION_GOALS:
            continue
        if goal_id in statuses:
            _fail(f"source dependency DAG duplicates {goal_id}")
        statuses[goal_id] = _normalize_status(
            goal.get("status"),
            f"source dependency DAG {goal_id} status",
        )
    if statuses != {goal_id: "blocked" for goal_id in TRANSITION_GOALS}:
        _fail(
            "source dependency DAG must contain the exact blocked transition "
            f"projection; observed={statuses}"
        )


def _require_blocked_preflight(raw: bytes, source_root: str) -> None:
    payload = _load_json_bytes(raw, "source preflight receipt")
    if payload.get("schema") != "world_aid.generated_board_preflight_receipt@1":
        _fail("source preflight receipt must be the blocked-board @1 receipt")
    if payload.get("status") != "passed" or payload.get("passed") is not True:
        _fail("source preflight receipt must be passed")
    if payload.get("generated_root") != source_root:
        _fail("source preflight receipt generated_root drift")


def _validate_transitions(
    value: Any,
    source_statuses: Mapping[str, str],
    target_statuses: Mapping[str, str],
) -> None:
    transitions = _array(value, "transitions")
    expected = [
        {
            "goal_id": goal_id,
            "from_status": "blocked",
            "to_status": "reopened",
        }
        for goal_id in TRANSITION_GOALS
    ]
    for index, transition in enumerate(transitions):
        _exact_keys(
            _object(transition, f"transitions[{index}]"),
            {"goal_id", "from_status", "to_status"},
            f"transitions[{index}]",
        )
    if transitions != expected:
        _fail(
            "transitions must contain exactly sorted G038/G039/G040 "
            "blocked-to-reopened records"
        )
    if set(source_statuses) != set(target_statuses):
        _fail("source and target heaps must contain the exact same goal set")
    for goal_id in TRANSITION_GOALS:
        if source_statuses.get(goal_id) != "blocked":
            _fail(f"source heap {goal_id} status must be exactly blocked")
        if target_statuses.get(goal_id) != "reopened":
            _fail(f"target heap {goal_id} status must be exactly reopened")
    for goal_id in sorted(set(source_statuses) - set(TRANSITION_GOALS)):
        if source_statuses[goal_id] != target_statuses[goal_id]:
            _fail(f"transition changes out-of-scope source goal {goal_id}")


def _validate_approval_descriptors(
    value: Any,
) -> dict[str, dict[str, str]]:
    approvals = _array(value, "approvals")
    if len(approvals) != len(REQUIRED_SIGNER_ROLES):
        _fail("approvals must contain exactly one signature per required role")
    by_role: dict[str, dict[str, str]] = {}
    identities: set[str] = set()
    fingerprints: set[str] = set()
    for index, raw_approval in enumerate(approvals):
        label = f"approvals[{index}]"
        approval = _object(raw_approval, label)
        _exact_keys(
            approval,
            {"role", "identity", "key_fingerprint", "signature_file"},
            label,
        )
        role = _string(approval["role"], f"{label}.role", maximum=64)
        identity = _string(
            approval["identity"],
            f"{label}.identity",
            maximum=254,
        )
        fingerprint = _string(
            approval["key_fingerprint"],
            f"{label}.key_fingerprint",
            minimum=50,
            maximum=50,
        )
        signature_file = _relative_path(
            approval["signature_file"],
            f"{label}.signature_file",
        )
        if role not in REQUIRED_SIGNER_ROLES or role in by_role:
            _fail(f"{label}.role is missing, unexpected, or duplicated")
        if not IDENTITY_RE.fullmatch(identity) or identity in identities:
            _fail(f"{label}.identity is invalid or duplicated")
        if (
            not FINGERPRINT_RE.fullmatch(fingerprint)
            or fingerprint in fingerprints
        ):
            _fail(f"{label}.key_fingerprint is invalid or duplicated")
        if signature_file != f"signatures/{role}.sshsig":
            _fail(f"{label}.signature_file is not the canonical role path")
        normalized = {
            "role": role,
            "identity": identity,
            "key_fingerprint": fingerprint,
            "signature_file": signature_file,
        }
        by_role[role] = normalized
        identities.add(identity)
        fingerprints.add(fingerprint)
    if set(by_role) != REQUIRED_SIGNER_ROLES:
        _fail("approval roles do not match the exact transition signer set")
    if [item["role"] for item in approvals] != sorted(REQUIRED_SIGNER_ROLES):
        _fail("approvals must use canonical sorted role order")
    return by_role


def _validate_controls(
    repo_root: Path,
    value: Any,
    *,
    target_commit: str,
    target_heap_id: str,
    issued_at: datetime,
    independent_operator_identity: str,
) -> None:
    controls = _object(value, "controls")
    _exact_keys(
        controls,
        {"external_launcher", "gate_verifier", "trust_policy"},
        "controls",
    )

    launcher = _object(controls["external_launcher"], "controls.external_launcher")
    _exact_keys(
        launcher,
        {
            "protocol_id",
            "protocol",
            "launcher",
            "deployment_attestation_id",
            "deployment_attestation",
        },
        "controls.external_launcher",
    )
    if launcher["protocol_id"] != LAUNCHER_PROTOCOL_ID:
        _fail("external launcher protocol_id drift")
    _, protocol_digest, _ = _verify_artifact(
        repo_root,
        launcher["protocol"],
        "controls.external_launcher.protocol",
        expected_path=CANONICAL_LAUNCHER_PROTOCOL_PATH,
    )
    _, launcher_digest, _ = _verify_artifact(
        repo_root,
        launcher["launcher"],
        "controls.external_launcher.launcher",
        expected_path=CANONICAL_LAUNCHER_PATH,
    )
    attestation_id = _string(
        launcher["deployment_attestation_id"],
        "controls.external_launcher.deployment_attestation_id",
        maximum=128,
    )
    if not ATTESTATION_ID_RE.fullmatch(attestation_id):
        _fail("deployment attestation ID is invalid")
    _, _, attestation_raw = _verify_artifact(
        repo_root,
        launcher["deployment_attestation"],
        "controls.external_launcher.deployment_attestation",
        expected_path=CANONICAL_DEPLOYMENT_ATTESTATION_PATH,
    )

    gate = _object(controls["gate_verifier"], "controls.gate_verifier")
    _exact_keys(gate, {"verifier_id", "artifact"}, "controls.gate_verifier")
    if gate["verifier_id"] != GATE_VERIFIER_ID:
        _fail("gate verifier ID drift")
    _, gate_digest, _ = _verify_artifact(
        repo_root,
        gate["artifact"],
        "controls.gate_verifier.artifact",
        expected_path=CANONICAL_GATE_VERIFIER_PATH,
    )

    trust_policy = _object(controls["trust_policy"], "controls.trust_policy")
    _exact_keys(
        trust_policy,
        {"policy_id", "deployment_path", "sha256"},
        "controls.trust_policy",
    )
    if trust_policy["policy_id"] != TRUST_POLICY_ID:
        _fail("trust policy ID drift")
    if trust_policy["deployment_path"] != TRUST_POLICY_DEPLOYMENT_PATH:
        _fail("trust policy deployment path drift")
    trust_policy_digest = _digest(
        trust_policy["sha256"],
        "controls.trust_policy.sha256",
    )

    attestation = _load_json_bytes(
        attestation_raw,
        "deployment/conformance attestation",
    )
    _exact_keys(
        attestation,
        {
            "schema",
            "attestation_id",
            "issued_at",
            "independently_administered",
            "administrator_identity",
            "deployed",
            "conformant",
            "protocol_id",
            "protocol_sha256",
            "launcher_sha256",
            "gate_verifier_id",
            "gate_verifier_sha256",
            "trust_policy_id",
            "trust_policy_sha256",
            "target_commit",
            "target_heap_id",
            "runtime_authorized",
        },
        "deployment/conformance attestation",
    )
    expected = {
        "schema": DEPLOYMENT_ATTESTATION_SCHEMA,
        "attestation_id": attestation_id,
        "independently_administered": True,
        "administrator_identity": independent_operator_identity,
        "deployed": True,
        "conformant": True,
        "protocol_id": LAUNCHER_PROTOCOL_ID,
        "protocol_sha256": protocol_digest,
        "launcher_sha256": launcher_digest,
        "gate_verifier_id": GATE_VERIFIER_ID,
        "gate_verifier_sha256": gate_digest,
        "trust_policy_id": TRUST_POLICY_ID,
        "trust_policy_sha256": trust_policy_digest,
        "target_commit": target_commit,
        "target_heap_id": target_heap_id,
        "runtime_authorized": False,
    }
    for key, expected_value in expected.items():
        if attestation.get(key) != expected_value:
            _fail(f"deployment/conformance attestation {key} drift")
    attested_at = _timestamp(
        attestation["issued_at"],
        "deployment/conformance attestation.issued_at",
    )
    if attested_at > issued_at:
        _fail("deployment/conformance attestation postdates the transition record")


def _read_trust_snapshot(path: Path) -> bytes:
    descriptor = -1
    try:
        descriptor = os.open(
            path,
            os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0),
        )
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH)
            or before.st_size > MAX_TRUST_BYTES
        ):
            _fail("allowed signers must be a bounded read-only regular file")
        chunks: list[bytes] = []
        remaining = MAX_TRUST_BYTES + 1
        while remaining:
            chunk = os.read(descriptor, min(1024 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
        if len(raw) > MAX_TRUST_BYTES:
            _fail("allowed signers exceeds the size limit")
        after = os.fstat(descriptor)
    except OSError as exc:
        _fail(f"cannot read allowed signers: {exc}")
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
        before.st_ctime_ns,
    ) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
    ):
        _fail("allowed signers changed while being read")
    return raw


def _parse_allowed_signers(
    raw: bytes,
) -> dict[str, dict[str, tuple[bytes, ...]]]:
    try:
        lines = raw.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        _fail(f"allowed signers is not UTF-8: {exc}")
    principals: dict[str, dict[str, list[bytes]]] = {}
    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        line_match = re.fullmatch(
            r"(?P<principals>\S+)(?P<suffix>[ \t]+.+)",
            stripped,
        )
        if line_match is None:
            _fail(f"allowed signers line {line_number} is invalid")
        try:
            fields = shlex.split(stripped, comments=True, posix=True)
        except ValueError as exc:
            _fail(f"allowed signers line {line_number} is invalid: {exc}")
        key_index = next(
            (
                index
                for index, field in enumerate(fields)
                if field.startswith(
                    ("ssh-", "ecdsa-", "sk-ssh-", "sk-ecdsa-")
                )
            ),
            None,
        )
        if key_index is None or key_index == 0 or key_index + 1 >= len(fields):
            _fail(f"allowed signers line {line_number} has no public key")
        identities = fields[0]
        if identities != line_match.group("principals"):
            _fail(f"allowed signers line {line_number} principal is invalid")
        try:
            key_blob = base64.b64decode(
                fields[key_index + 1].encode("ascii"),
                validate=True,
            )
        except (UnicodeEncodeError, binascii.Error) as exc:
            _fail(f"allowed signers line {line_number} key is invalid: {exc}")
        fingerprint = "SHA256:" + base64.b64encode(
            hashlib.sha256(key_blob).digest()
        ).decode("ascii").rstrip("=")
        for identity in identities.split(","):
            if not IDENTITY_RE.fullmatch(identity):
                _fail(f"allowed signers line {line_number} identity is invalid")
            selected = f"{identity}{line_match.group('suffix')}\n".encode()
            by_fingerprint = principals.setdefault(identity, {})
            selected_lines = by_fingerprint.setdefault(fingerprint, [])
            if selected not in selected_lines:
                selected_lines.append(selected)
    if not principals:
        _fail("allowed signers contains no principals")
    return {
        identity: {
            fingerprint: tuple(lines_for_key)
            for fingerprint, lines_for_key in keys.items()
        }
        for identity, keys in principals.items()
    }


def _sealed_snapshot_fd(raw: bytes) -> int:
    flags = getattr(os, "MFD_ALLOW_SEALING", 0x0002) | getattr(
        os,
        "MFD_CLOEXEC",
        0x0001,
    )
    descriptor = -1
    try:
        if hasattr(os, "memfd_create"):
            descriptor = os.memfd_create(
                "world-aid-transition-snapshot",
                flags,
            )
        else:
            libc = ctypes.CDLL(None, use_errno=True)
            memfd_create = libc.memfd_create
            memfd_create.argtypes = (ctypes.c_char_p, ctypes.c_uint)
            memfd_create.restype = ctypes.c_int
            descriptor = int(
                memfd_create(b"world-aid-transition-snapshot", flags)
            )
            if descriptor < 0:
                error_number = ctypes.get_errno()
                raise OSError(error_number, os.strerror(error_number))
        view = memoryview(raw)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("short write")
            view = view[written:]
        os.fchmod(descriptor, 0o400)
        required_seals = (
            getattr(fcntl, "F_SEAL_SEAL", 0x0001)
            | getattr(fcntl, "F_SEAL_SHRINK", 0x0002)
            | getattr(fcntl, "F_SEAL_GROW", 0x0004)
            | getattr(fcntl, "F_SEAL_WRITE", 0x0008)
        )
        add_seals = getattr(fcntl, "F_ADD_SEALS", 1033)
        get_seals = getattr(fcntl, "F_GET_SEALS", 1034)
        fcntl.fcntl(
            descriptor,
            add_seals,
            required_seals,
        )
        observed_seals = int(fcntl.fcntl(descriptor, get_seals))
        if observed_seals & required_seals != required_seals:
            _fail("snapshot memfd did not acquire every required seal")
        os.lseek(descriptor, 0, os.SEEK_SET)
        return descriptor
    except TransitionVerificationError:
        if descriptor >= 0:
            os.close(descriptor)
        raise
    except (AttributeError, OSError, UnicodeEncodeError) as exc:
        if descriptor >= 0:
            os.close(descriptor)
        _fail(f"cannot seal allowed signers snapshot: {exc}")


def _read_signature_snapshot(
    signature_path: Path,
    signature_root: Path,
    role: str,
) -> bytes:
    descriptor = -1
    directory_descriptor = -1
    try:
        if signature_root.is_symlink() or not signature_root.is_dir():
            _fail("transition signature directory is missing or unsafe")
        directory_descriptor = os.open(
            signature_root,
            os.O_RDONLY
            | os.O_CLOEXEC
            | getattr(os, "O_DIRECTORY", 0)
            | getattr(os, "O_NOFOLLOW", 0),
        )
        descriptor = os.open(
            signature_path.name,
            os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=directory_descriptor,
        )
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or before.st_size > MAX_SIGNATURE_BYTES
        ):
            _fail(f"{role} detached signature is not a bounded regular file")
        chunks: list[bytes] = []
        remaining = MAX_SIGNATURE_BYTES + 1
        while remaining:
            chunk = os.read(descriptor, min(16 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
        if len(raw) > MAX_SIGNATURE_BYTES:
            _fail(f"{role} detached signature exceeds the size limit")
        after = os.fstat(descriptor)
    except OSError as exc:
        _fail(f"cannot snapshot {role} detached signature: {exc}")
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if directory_descriptor >= 0:
            os.close(directory_descriptor)
    if (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
        before.st_ctime_ns,
    ) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
    ):
        _fail(f"{role} detached signature changed while being captured")
    try:
        signature_path.resolve(strict=True).relative_to(
            signature_root.resolve(strict=True)
        )
    except (OSError, RuntimeError, ValueError):
        _fail(f"{role} detached signature escapes its canonical directory")
    return raw


def _verify_signatures(
    record_path: Path,
    record_raw: bytes,
    approvals: Mapping[str, Mapping[str, str]],
    allowed_signers: Mapping[str, Mapping[str, Sequence[bytes]]],
) -> None:
    if (
        not TRUSTED_SSH_KEYGEN.is_file()
        or TRUSTED_SSH_KEYGEN.is_symlink()
        or TRUSTED_SSH_KEYGEN.stat().st_mode
        & (stat.S_IWGRP | stat.S_IWOTH)
    ):
        _fail("trusted ssh-keygen executable is unavailable or unsafe")
    signature_root = record_path.parent
    signature_directory = signature_root / "signatures"
    env = {
        "LANG": "C",
        "LC_ALL": "C",
        "PATH": "/usr/bin:/bin",
    }
    for role in sorted(REQUIRED_SIGNER_ROLES):
        approval = approvals[role]
        identity = approval["identity"]
        fingerprint = approval["key_fingerprint"]
        selected = allowed_signers.get(identity, {}).get(fingerprint)
        if not selected:
            _fail(
                f"{role} declared identity/fingerprint is absent from trust"
            )
        signature_relative = approval["signature_file"]
        signature_path = signature_root.joinpath(
            *PurePosixPath(signature_relative).parts
        )
        if signature_path.is_symlink() or not signature_path.is_file():
            _fail(f"{role} detached signature is missing or unsafe")
        signature_raw = _read_signature_snapshot(
            signature_path,
            signature_directory,
            role,
        )
        trust_descriptor = _sealed_snapshot_fd(b"".join(selected))
        signature_descriptor = _sealed_snapshot_fd(signature_raw)
        try:
            try:
                result = subprocess.run(
                    [
                        str(TRUSTED_SSH_KEYGEN),
                        "-Y",
                        "verify",
                        "-f",
                        f"/proc/self/fd/{trust_descriptor}",
                        "-I",
                        identity,
                        "-n",
                        SIGNATURE_NAMESPACE,
                        "-s",
                        f"/proc/self/fd/{signature_descriptor}",
                    ],
                    input=record_raw,
                    check=False,
                    capture_output=True,
                    pass_fds=(trust_descriptor, signature_descriptor),
                    timeout=10,
                    env=env,
                )
            except (OSError, subprocess.SubprocessError) as exc:
                _fail(f"{role} signature verification could not run: {exc}")
        finally:
            os.close(signature_descriptor)
            os.close(trust_descriptor)
        if result.returncode != 0:
            _fail(f"{role} detached signature is malformed or rejected")


def verify_transition(
    *,
    repo_root: Path,
    record_path: Path,
    allowed_signers_path: Path,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Verify one transition record without mutating repository state."""

    root = repo_root.resolve()
    expected_record = root / CANONICAL_RECORD_PATH
    candidate_record = (
        record_path if record_path.is_absolute() else root / record_path
    )
    try:
        if (
            candidate_record.is_symlink()
            or candidate_record.resolve(strict=True)
            != expected_record.resolve(strict=True)
        ):
            _fail(f"record path must be {CANONICAL_RECORD_PATH.as_posix()}")
    except OSError as exc:
        _fail(f"cannot resolve transition record: {exc}")
    record_raw = _read_repo_file(
        root,
        CANONICAL_RECORD_PATH.as_posix(),
        "transition record",
    )
    record = _load_json_bytes(
        record_raw,
        "transition record",
        require_canonical=True,
    )
    _exact_keys(
        record,
        {
            "schema_version",
            "gate_id",
            "record_id",
            "decision",
            "transition_authorized",
            "runtime_authorized",
            "issued_at",
            "expires_at",
            "source_state",
            "target_state",
            "transitions",
            "controls",
            "regeneration",
            "trust",
            "approvals",
        },
        "transition record",
    )
    expected_scalars = {
        "schema_version": SCHEMA_VERSION,
        "gate_id": GATE_ID,
        "decision": "approved",
        "transition_authorized": True,
        "runtime_authorized": False,
    }
    for key, expected in expected_scalars.items():
        if record[key] != expected:
            _fail(f"transition record {key} must be {expected!r}")
    record_id = _string(
        record["record_id"],
        "record_id",
        maximum=115,
    )
    if not RECORD_ID_RE.fullmatch(record_id):
        _fail("record_id is invalid")
    issued_at = _timestamp(record["issued_at"], "issued_at")
    expires_at = _timestamp(record["expires_at"], "expires_at")
    verification_time = now or datetime.now(UTC)
    if verification_time.tzinfo is None:
        verification_time = verification_time.replace(tzinfo=UTC)
    verification_time = verification_time.astimezone(UTC)
    if (
        issued_at > verification_time
        or verification_time >= expires_at
        or expires_at <= issued_at
        or expires_at - issued_at > timedelta(days=7)
    ):
        _fail("transition record is not currently valid within its bounded window")

    approvals = _validate_approval_descriptors(record["approvals"])

    source = _object(record["source_state"], "source_state")
    _exact_keys(
        source,
        {
            "root_commit",
            "heap_id",
            "objective_heap",
            "board_contract",
            "generated_root",
            "generated_artifacts",
        },
        "source_state",
    )
    source_commit = _commit(source["root_commit"], "source_state.root_commit")
    source_heap_id = _digest(source["heap_id"], "source_state.heap_id")
    if source["board_contract"] != SOURCE_BOARD_CONTRACT:
        _fail("source_state.board_contract must be blocked-review-v1")
    source_root = _generated_root(
        source["generated_root"],
        "source_state.generated_root",
    )
    _, source_heap_digest = _heap_binding(
        source["objective_heap"],
        "source_state.objective_heap",
    )
    if source_heap_id != source_heap_digest:
        _fail("source heap ID must equal its exact artifact digest")

    target = _object(record["target_state"], "target_state")
    _exact_keys(
        target,
        {
            "root_commit",
            "heap_id",
            "objective_heap",
            "board_contract",
        },
        "target_state",
    )
    target_commit = _commit(target["root_commit"], "target_state.root_commit")
    target_heap_id = _digest(target["heap_id"], "target_state.heap_id")
    if target["board_contract"] != TARGET_BOARD_CONTRACT:
        _fail(
            "target_state.board_contract must be "
            "gate0b-selection-reopened-v1"
        )
    _, target_heap_digest = _heap_binding(
        target["objective_heap"],
        "target_state.objective_heap",
    )
    if target_heap_id != target_heap_digest:
        _fail("target heap ID must equal its exact artifact digest")
    if source_commit == target_commit:
        _fail("source and target commit IDs must be distinct")
    if source_heap_id == target_heap_id:
        _fail("source and target heap IDs/digests must be distinct")
    source_heap_raw, target_heap_raw = _committed_heap_bytes(
        root,
        source_commit=source_commit,
        target_commit=target_commit,
    )
    if _sha256_bytes(source_heap_raw) != source_heap_id:
        _fail("source committed objective heap digest/content mismatch")
    if _sha256_bytes(target_heap_raw) != target_heap_id:
        _fail("target committed objective heap digest/content mismatch")

    generated = _object(
        source["generated_artifacts"],
        "source_state.generated_artifacts",
    )
    _exact_keys(
        generated,
        set(GENERATED_ARTIFACT_PATHS),
        "source_state.generated_artifacts",
    )
    generated_paths: set[str] = set()
    generated_digests: dict[str, str] = {}
    generated_raw: dict[str, bytes] = {}
    for artifact_id, suffix in GENERATED_ARTIFACT_PATHS.items():
        path, digest, raw = _verify_artifact(
            root,
            generated[artifact_id],
            f"source_state.generated_artifacts.{artifact_id}",
            expected_path=f"{source_root}/{suffix}",
            must_not_reuse=True,
        )
        if path in generated_paths:
            _fail("pre-transition generated artifact paths are duplicated")
        if digest in generated_digests.values():
            _fail("pre-transition generated artifact digests are reused")
        generated_paths.add(path)
        generated_digests[artifact_id] = digest
        generated_raw[artifact_id] = raw
    if target_heap_id in generated_digests.values():
        _fail("target heap reuses a pre-transition generated artifact digest")

    _require_blocked_taskboard(generated_raw["taskboard"])
    _load_json_bytes(generated_raw["task_index"], "source task index")
    _require_blocked_bundle_index(generated_raw["bundle_index"])
    _require_blocked_dependency_dag(generated_raw["dependency_dag"])
    _require_blocked_preflight(
        generated_raw["preflight_receipt"],
        source_root,
    )

    source_statuses = _heap_statuses(source_heap_raw, "source objective heap")
    target_statuses = _heap_statuses(target_heap_raw, "target objective heap")
    _validate_transitions(
        record["transitions"],
        source_statuses,
        target_statuses,
    )

    regeneration = _object(record["regeneration"], "regeneration")
    _exact_keys(
        regeneration,
        {
            "required",
            "mode",
            "source_generated_root",
            "target_generated_root",
            "must_not_reuse_artifact_ids",
            "must_not_reuse_sha256",
        },
        "regeneration",
    )
    if _bool(regeneration["required"], "regeneration.required") is not True:
        _fail("fresh post-transition regeneration must be required")
    if regeneration["mode"] != "fresh-post-transition":
        _fail("regeneration.mode must be fresh-post-transition")
    if regeneration["source_generated_root"] != source_root:
        _fail("regeneration source root does not bind source_state")
    target_root = _generated_root(
        regeneration["target_generated_root"],
        "regeneration.target_generated_root",
    )
    if target_root == source_root:
        _fail("post-transition regeneration may not reuse the source root")
    artifact_ids = _array(
        regeneration["must_not_reuse_artifact_ids"],
        "regeneration.must_not_reuse_artifact_ids",
    )
    if artifact_ids != sorted(GENERATED_ARTIFACT_PATHS):
        _fail(
            "regeneration.must_not_reuse_artifact_ids must name every exact "
            "pre-transition generated artifact"
        )
    prohibited_digests = _array(
        regeneration["must_not_reuse_sha256"],
        "regeneration.must_not_reuse_sha256",
    )
    if any(
        _digest(item, f"regeneration.must_not_reuse_sha256[{index}]") != item
        for index, item in enumerate(prohibited_digests)
    ):
        _fail("regeneration prohibited digest is invalid")
    if (
        len(prohibited_digests) != len(set(prohibited_digests))
        or prohibited_digests != sorted(generated_digests.values())
    ):
        _fail(
            "regeneration.must_not_reuse_sha256 must contain every exact "
            "unique pre-transition generated artifact digest"
        )

    _validate_controls(
        root,
        record["controls"],
        target_commit=target_commit,
        target_heap_id=target_heap_id,
        issued_at=issued_at,
        independent_operator_identity=approvals["independent-operator"][
            "identity"
        ],
    )

    trust = _object(record["trust"], "trust")
    _exact_keys(
        trust,
        {"policy_id", "signature_namespace", "allowed_signers_sha256"},
        "trust",
    )
    if trust["policy_id"] != SIGNER_POLICY_ID:
        _fail("transition signer policy ID drift")
    if trust["signature_namespace"] != SIGNATURE_NAMESPACE:
        _fail("transition signature namespace drift")
    expected_trust_digest = _digest(
        trust["allowed_signers_sha256"],
        "trust.allowed_signers_sha256",
    )
    trust_raw = _read_trust_snapshot(allowed_signers_path)
    if _sha256_bytes(trust_raw) != expected_trust_digest:
        _fail("allowed signers digest drift")
    allowed_signers = _parse_allowed_signers(trust_raw)
    _verify_signatures(
        expected_record,
        record_raw,
        approvals,
        allowed_signers,
    )

    return {
        "status": "verified",
        "gate_id": GATE_ID,
        "record_id": record_id,
        "source_commit": source_commit,
        "target_commit": target_commit,
        "source_heap_id": source_heap_id,
        "target_heap_id": target_heap_id,
        "transition_goal_ids": list(TRANSITION_GOALS),
        "signature_count": len(approvals),
        "runtime_authorized": False,
        "fresh_regeneration_required": True,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument(
        "--record",
        type=Path,
        default=CANONICAL_RECORD_PATH,
    )
    parser.add_argument("--allowed-signers", type=Path, required=True)
    parser.add_argument("--offline", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if not args.offline:
        print(
            "Gate 0B transition verification rejected: --offline is required",
            file=sys.stderr,
        )
        return 2
    try:
        summary = verify_transition(
            repo_root=args.repo_root,
            record_path=args.record,
            allowed_signers_path=args.allowed_signers,
        )
    except TransitionVerificationError as exc:
        print(
            f"Gate 0B transition verification rejected: {exc}",
            file=sys.stderr,
        )
        return 1
    print(json.dumps(summary, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
