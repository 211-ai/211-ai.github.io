#!/usr/bin/env python3
"""Fail-closed, verify-only reference for the World-aid Gate-first launcher.

This file is reviewable source, not an authority merely because it exists in
the repository.  The authoritative copy must be installed outside the
repository, owned by the operator, content-bound by the fixed operator policy,
and invoked with ``python -I -S -B`` in a clean environment.

There is deliberately no run-selection command.  G038, G039, and G040 remain
non-executable until dedicated sealed-input runners and an externally enforced
process/network sandbox are installed and reviewed.
"""

from __future__ import annotations

import argparse
import ctypes
import fcntl
import hashlib
import json
import os
import re
import selectors
import signal
import stat
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

POLICY_SCHEMA = "world-aid-gate-first-operator-policy/v1"
VERIFY_RESULT_SCHEMA = "world-aid-gate-first-verify-only/v1"
FIXED_OPERATOR_POLICY_PATH = Path("/etc/world-aid/gate-first-policy.json")
FIXED_INSTALLED_LAUNCHER_PATH = Path("/usr/local/libexec/world-aid-gate-first-launcher")
FIXED_SSH_KEYGEN_PATH = Path("/usr/bin/ssh-keygen")
CANONICAL_GATE_VERIFIER = "scripts/verify_world_aid_gate_0b.py"
CANONICAL_SELECTION_APPROVAL = (
    "data/worldcoin_human_aid/approvals/gate-0b-selection/approval.json"
)
EXPECTED_GOAL_IDS = (
    "WORLDCOIN-G038",
    "WORLDCOIN-G039",
    "WORLDCOIN-G040",
)
EXPECTED_RUNNERS = {
    "WORLDCOIN-G038": "scripts/run_world_aid_siwe_bootstrap.py",
    "WORLDCOIN-G039": "scripts/run_world_aid_zkp_bootstrap.py",
    "WORLDCOIN-G040": "scripts/run_world_aid_duckdb_bootstrap.py",
}
EXECUTION_BOUND_ARTIFACT_PATHS = {
    "gate_verifier": CANONICAL_GATE_VERIFIER,
    "gate_launcher": "scripts/world_aid_gate_first_launcher.py",
    "gate_launcher_protocol": "docs/specs/WORLD_AID_GATE_FIRST_LAUNCHER.md",
    "gate_receipt_verifier": "scripts/verify_world_aid_gate_first_receipt.py",
    "selection_profile_builder": (
        "scripts/build_world_aid_gate0b_selection_profile.py"
    ),
    "siwe_bootstrap_runner": EXPECTED_RUNNERS["WORLDCOIN-G038"],
    "zkp_bootstrap_runner": EXPECTED_RUNNERS["WORLDCOIN-G039"],
    "duckdb_bootstrap_runner": EXPECTED_RUNNERS["WORLDCOIN-G040"],
}
RUNNER_REVIEWED_ARTIFACT_KEYS = {
    "WORLDCOIN-G038": "siwe_bootstrap_runner",
    "WORLDCOIN-G039": "zkp_bootstrap_runner",
    "WORLDCOIN-G040": "duckdb_bootstrap_runner",
}
SELECTION_APPROVAL_SCHEMA = "world-human-aid-gate-0b-selection/v2"
SELECTION_GATE_ID = "gate-0b-selection"
GATE_FIRST_PROTOCOL_ID = "world-aid-gate-first-launcher/v1"
GATE_FIRST_EXECUTION_AUTHORITY = "operator-gate-first/v1"
SELECTION_OPERATION = "run-selection/v1"
SEALED_INPUT_PROTOCOL = "sealed-fd-json/v1"
RESULT_PROTOCOL = "stdout-json/v1"
DEPLOYMENT_ATTESTATION_ID_RE = re.compile(
    r"^gate-first-deployment-[a-z0-9][a-z0-9._-]{7,95}$"
)
EXPECTED_CLEAN_ENVIRONMENT = {
    "LANG": "C.UTF-8",
    "LC_ALL": "C.UTF-8",
    "PATH": "/usr/bin:/bin",
    "TZ": "UTC",
}
AUTHORITY_ENVIRONMENT_NAMES = frozenset(EXPECTED_CLEAN_ENVIRONMENT)
DANGEROUS_ENVIRONMENT_PREFIXES = ("DYLD_", "LD_", "PYTHON")
MAX_POLICY_BYTES = 256 * 1024
MAX_APPROVAL_BYTES = 2 * 1024 * 1024
MAX_VERIFIER_BYTES = 2 * 1024 * 1024
MAX_PROFILE_BYTES = 128 * 1024 * 1024
MIN_GATE_TIMEOUT_SECONDS = 1
MAX_GATE_TIMEOUT_SECONDS = 300
MIN_OUTPUT_BYTES = 1024
MAX_OUTPUT_BYTES = 4 * 1024 * 1024
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
FINGERPRINT_RE = re.compile(r"^SHA256:[A-Za-z0-9+/]{43}$")
VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")


class GateFirstLauncherError(RuntimeError):
    """Raised when a launcher trust or verification condition fails closed."""


@dataclass(frozen=True)
class ExternalSecurityContext:
    """Ownership boundary used for operator-controlled filesystem objects.

    Production always uses ``trusted_root=/`` and ``expected_owner_uid=0``.
    A narrower non-root boundary exists solely so unit tests and deployment
    packaging checks can exercise the same descriptor-relative primitives.
    The CLI never accepts either value from its caller.
    """

    trusted_root: Path = Path("/")
    expected_owner_uid: int = 0


ROOT_OPERATOR_CONTEXT = ExternalSecurityContext()


@dataclass(frozen=True)
class RunnerPolicy:
    goal_id: str
    path: str
    sha256: str
    input_mode: str
    output_mode: str


@dataclass(frozen=True)
class OperatorPolicy:
    raw_sha256: str
    launcher_path: Path
    launcher_sha256: str
    python_path: Path
    python_sha256: str
    python_version: str
    ssh_keygen_path: Path
    ssh_keygen_sha256: str
    authority_uid: int
    repo_root: Path
    gate_verifier_path: str
    gate_verifier_sha256: str
    selection_approval_path: str
    profile_json_path: str
    profile_json_sha256: str
    profile_duckdb_path: str
    profile_duckdb_sha256: str
    allowed_signers_path: Path
    allowed_signers_sha256: str
    run_selection_enabled: bool
    runners: tuple[RunnerPolicy, ...]
    receipt_root: Path
    receipt_allowed_signers_path: Path
    receipt_allowed_signers_sha256: str
    receipt_signer_identity: str
    receipt_signer_fingerprint: str
    receipt_signature_namespace: str
    apparmor_profile: str
    network_namespace: str
    gate_timeout_seconds: int
    max_child_output_bytes: int


@dataclass
class SealedFileSnapshot:
    """Immutable bytes captured from a descriptor-relative regular file."""

    fd: int
    source_path: str
    sha256: str
    size: int
    source_device: int
    source_inode: int
    source_mtime_ns: int
    source_ctime_ns: int
    closed: bool = False

    def read_bytes(self) -> bytes:
        if self.closed:
            raise GateFirstLauncherError(f"sealed snapshot is closed: {self.source_path}")
        chunks: list[bytes] = []
        offset = 0
        while offset < self.size:
            chunk = os.pread(self.fd, min(1024 * 1024, self.size - offset), offset)
            if not chunk:
                raise GateFirstLauncherError(
                    f"sealed snapshot ended early: {self.source_path}"
                )
            chunks.append(chunk)
            offset += len(chunk)
        return b"".join(chunks)

    def close(self) -> None:
        if not self.closed:
            os.close(self.fd)
            self.closed = True

    def __enter__(self) -> SealedFileSnapshot:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()


def _fail(message: str) -> None:
    raise GateFirstLauncherError(message)


def _sha256_bytes(raw: bytes) -> str:
    return f"sha256:{hashlib.sha256(raw).hexdigest()}"


def _reject_constant(value: str) -> None:
    raise GateFirstLauncherError(f"non-finite JSON number is forbidden: {value}")


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _fail(f"duplicate JSON key is forbidden: {key}")
        result[key] = value
    return result


def load_json_strict(raw: bytes, *, label: str) -> Any:
    """Decode UTF-8 JSON while rejecting duplicate keys and non-finite values."""

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        _fail(f"{label} is not UTF-8: {exc}")
    try:
        return json.loads(
            text,
            object_pairs_hook=_strict_object,
            parse_constant=_reject_constant,
        )
    except GateFirstLauncherError:
        raise
    except (json.JSONDecodeError, RecursionError) as exc:
        _fail(f"{label} is not strict JSON: {exc}")


def _object(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail(f"{label} must be a JSON object")
    return value


def _exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    observed = set(value)
    if observed != expected:
        _fail(
            f"{label} keys differ: missing={sorted(expected - observed)}, "
            f"unexpected={sorted(observed - expected)}"
        )


def _string(value: Any, label: str, *, minimum: int = 1, maximum: int = 4096) -> str:
    if not isinstance(value, str) or not minimum <= len(value) <= maximum:
        _fail(f"{label} must be a string of length {minimum}..{maximum}")
    return value


def _boolean(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        _fail(f"{label} must be a boolean")
    return value


def _integer(value: Any, label: str, *, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        _fail(f"{label} must be an integer in {minimum}..{maximum}")
    return value


def _digest(value: Any, label: str) -> str:
    text = _string(value, label, maximum=71)
    if not DIGEST_RE.fullmatch(text):
        _fail(f"{label} must be a lowercase sha256 digest")
    return text


def _absolute_path(value: Any, label: str) -> Path:
    text = _string(value, label)
    path = Path(text)
    if not path.is_absolute() or path.as_posix() != text or ".." in path.parts:
        _fail(f"{label} must be a normalized absolute POSIX path")
    return path


def _relative_path(value: Any, label: str) -> str:
    text = _string(value, label)
    path = PurePosixPath(text)
    if (
        path.is_absolute()
        or text != path.as_posix()
        or not path.parts
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        _fail(f"{label} must be a normalized repository-relative POSIX path")
    return text


def _assert_profile_path(path: str, filename: str, label: str) -> None:
    parts = PurePosixPath(path).parts
    expected_prefix = (
        "data",
        "worldcoin_human_aid",
        "agent_supervisor",
        "regenerations",
    )
    if (
        len(parts) != 7
        or tuple(parts[:4]) != expected_prefix
        or not parts[4]
        or parts[5] != "launch_profiles"
        or parts[6] != filename
    ):
        _fail(
            f"{label} must identify one immutable regeneration's "
            f"launch_profiles/{filename}"
        )


def _open_directory_no_symlink(path: Path) -> int:
    """Open an absolute directory while refusing every symlink component."""

    if not path.is_absolute():
        _fail(f"directory path is not absolute: {path}")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open("/", flags)
    try:
        for component in path.parts[1:]:
            next_descriptor = os.open(
                component,
                flags | nofollow,
                dir_fd=descriptor,
            )
            os.close(descriptor)
            descriptor = next_descriptor
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _assert_secure_metadata(
    metadata: os.stat_result,
    *,
    label: str,
    expected_owner_uid: int,
    directory: bool,
    leaf_write_mask: int | None = None,
    require_single_link: bool = False,
) -> None:
    expected_kind = stat.S_ISDIR if directory else stat.S_ISREG
    if not expected_kind(metadata.st_mode):
        _fail(f"{label} is not a {'directory' if directory else 'regular file'}")
    if metadata.st_uid != expected_owner_uid:
        _fail(f"{label} is not owned by uid {expected_owner_uid}")
    if directory and metadata.st_mode & 0o022:
        _fail(f"{label} is group/world writable")
    if leaf_write_mask is not None and metadata.st_mode & leaf_write_mask:
        _fail(f"{label} has forbidden write permission bits")
    if require_single_link and metadata.st_nlink != 1:
        _fail(f"{label} must have exactly one hard link")


def _new_sealed_memfd(name: str, raw: bytes) -> int:
    # Python builds do not consistently expose the Linux constants even when
    # the kernel and libc provide memfd_create.
    flags = getattr(os, "MFD_ALLOW_SEALING", 0x0002) | getattr(
        os, "MFD_CLOEXEC", 0x0001
    )
    if hasattr(os, "memfd_create"):
        descriptor = os.memfd_create(name, flags)
    else:
        try:
            libc = ctypes.CDLL(None, use_errno=True)
            memfd_create = libc.memfd_create
            memfd_create.argtypes = (ctypes.c_char_p, ctypes.c_uint)
            memfd_create.restype = ctypes.c_int
            descriptor = int(memfd_create(name.encode("ascii"), flags))
        except (AttributeError, OSError, UnicodeEncodeError) as exc:
            _fail(f"Linux memfd sealing is required: {exc}")
        if descriptor < 0:
            error_number = ctypes.get_errno()
            raise OSError(error_number, os.strerror(error_number))
    try:
        view = memoryview(raw)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                _fail("cannot write sealed snapshot")
            view = view[written:]
        os.fchmod(descriptor, 0o400)
        required = (
            getattr(fcntl, "F_SEAL_SEAL", 0x0001)
            | getattr(fcntl, "F_SEAL_SHRINK", 0x0002)
            | getattr(fcntl, "F_SEAL_GROW", 0x0004)
            | getattr(fcntl, "F_SEAL_WRITE", 0x0008)
        )
        add_seals = getattr(fcntl, "F_ADD_SEALS", 1033)
        get_seals = getattr(fcntl, "F_GET_SEALS", 1034)
        fcntl.fcntl(descriptor, add_seals, required)
        observed = int(fcntl.fcntl(descriptor, get_seals))
        if observed & required != required:
            _fail("memfd snapshot did not acquire every required seal")
        os.lseek(descriptor, 0, os.SEEK_SET)
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _snapshot_from_open_fd(
    descriptor: int,
    *,
    source_path: str,
    maximum_bytes: int,
) -> SealedFileSnapshot:
    before = os.fstat(descriptor)
    if not stat.S_ISREG(before.st_mode):
        _fail(f"snapshot source must be a regular file: {source_path}")
    if before.st_size <= 0 or before.st_size > maximum_bytes:
        _fail(
            f"snapshot source size must be 1..{maximum_bytes} bytes: {source_path}"
        )
    chunks: list[bytes] = []
    remaining = before.st_size
    while remaining:
        chunk = os.read(descriptor, min(1024 * 1024, remaining))
        if not chunk:
            _fail(f"snapshot source ended early: {source_path}")
        chunks.append(chunk)
        remaining -= len(chunk)
    raw = b"".join(chunks)
    after = os.fstat(descriptor)
    identity_before = (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
        before.st_ctime_ns,
    )
    identity_after = (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
    )
    if identity_after != identity_before:
        _fail(f"snapshot source changed while being read: {source_path}")
    sealed_fd = _new_sealed_memfd("world-aid-snapshot", raw)
    return SealedFileSnapshot(
        fd=sealed_fd,
        source_path=source_path,
        sha256=_sha256_bytes(raw),
        size=len(raw),
        source_device=before.st_dev,
        source_inode=before.st_ino,
        source_mtime_ns=before.st_mtime_ns,
        source_ctime_ns=before.st_ctime_ns,
    )


def snapshot_regular_file_at(
    root_fd: int,
    relative_path: str,
    *,
    maximum_bytes: int,
) -> SealedFileSnapshot:
    """Capture a regular file below ``root_fd`` without following symlinks."""

    normalized = _relative_path(relative_path, "snapshot path")
    parts = PurePosixPath(normalized).parts
    directory_fd = os.dup(root_fd)
    flags = os.O_RDONLY | os.O_CLOEXEC
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    try:
        for component in parts[:-1]:
            next_fd = os.open(
                component,
                flags | os.O_DIRECTORY | nofollow,
                dir_fd=directory_fd,
            )
            os.close(directory_fd)
            directory_fd = next_fd
        file_fd = os.open(parts[-1], flags | nofollow, dir_fd=directory_fd)
        try:
            return _snapshot_from_open_fd(
                file_fd,
                source_path=normalized,
                maximum_bytes=maximum_bytes,
            )
        finally:
            os.close(file_fd)
    except OSError as exc:
        _fail(f"cannot snapshot {normalized} without following symlinks: {exc}")
    finally:
        os.close(directory_fd)


def revalidate_regular_file_at(root_fd: int, snapshot: SealedFileSnapshot) -> None:
    """Require the named source still to be the exact captured file and bytes."""

    with snapshot_regular_file_at(
        root_fd,
        snapshot.source_path,
        maximum_bytes=max(snapshot.size, 1),
    ) as observed:
        expected_identity = (
            snapshot.source_device,
            snapshot.source_inode,
            snapshot.size,
            snapshot.source_mtime_ns,
            snapshot.source_ctime_ns,
            snapshot.sha256,
        )
        observed_identity = (
            observed.source_device,
            observed.source_inode,
            observed.size,
            observed.source_mtime_ns,
            observed.source_ctime_ns,
            observed.sha256,
        )
        if observed_identity != expected_identity:
            _fail(f"captured source changed after snapshot: {snapshot.source_path}")


def _secure_external_snapshot(
    path: Path,
    *,
    context: ExternalSecurityContext,
    maximum_bytes: int,
    label: str,
    leaf_write_mask: int,
    require_single_link: bool,
) -> SealedFileSnapshot:
    trusted_root = context.trusted_root
    if not trusted_root.is_absolute() or not path.is_absolute():
        _fail(f"{label} path and trusted root must be absolute")
    try:
        relative = path.relative_to(trusted_root)
    except ValueError:
        _fail(f"{label} is outside the operator trust root")
    if not relative.parts:
        _fail(f"{label} cannot be the trust-root directory")

    directory_fd = _open_directory_no_symlink(trusted_root)
    flags = os.O_RDONLY | os.O_CLOEXEC
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    try:
        _assert_secure_metadata(
            os.fstat(directory_fd),
            label=f"{label} trusted root",
            expected_owner_uid=context.expected_owner_uid,
            directory=True,
        )
        for component in relative.parts[:-1]:
            next_fd = os.open(
                component,
                flags | os.O_DIRECTORY | nofollow,
                dir_fd=directory_fd,
            )
            _assert_secure_metadata(
                os.fstat(next_fd),
                label=f"{label} parent {component}",
                expected_owner_uid=context.expected_owner_uid,
                directory=True,
            )
            os.close(directory_fd)
            directory_fd = next_fd
        file_fd = os.open(relative.parts[-1], flags | nofollow, dir_fd=directory_fd)
        try:
            _assert_secure_metadata(
                os.fstat(file_fd),
                label=label,
                expected_owner_uid=context.expected_owner_uid,
                directory=False,
                leaf_write_mask=leaf_write_mask,
                require_single_link=require_single_link,
            )
            return _snapshot_from_open_fd(
                file_fd,
                source_path=path.as_posix(),
                maximum_bytes=maximum_bytes,
            )
        finally:
            os.close(file_fd)
    except OSError as exc:
        _fail(f"cannot securely open {label}: {exc}")
    finally:
        os.close(directory_fd)


def _validate_policy_payload(payload: Any, raw_sha256: str) -> OperatorPolicy:
    root = _object(payload, "operator policy")
    _exact_keys(
        root,
        {
            "schema",
            "mode",
            "installation",
            "repository",
            "gate",
            "trust",
            "execution",
            "receipts",
            "runtime",
        },
        "operator policy",
    )
    if root["schema"] != POLICY_SCHEMA:
        _fail(f"operator policy schema must be {POLICY_SCHEMA}")
    if root["mode"] != "verify-only":
        _fail("operator policy mode must remain verify-only")

    installation = _object(root["installation"], "installation")
    _exact_keys(
        installation,
        {
            "launcher_path",
            "launcher_sha256",
            "python_path",
            "python_sha256",
            "python_version",
            "ssh_keygen_path",
            "ssh_keygen_sha256",
            "authority_uid",
        },
        "installation",
    )
    launcher_path = _absolute_path(installation["launcher_path"], "installation.launcher_path")
    python_path = _absolute_path(installation["python_path"], "installation.python_path")
    ssh_keygen_path = _absolute_path(
        installation["ssh_keygen_path"], "installation.ssh_keygen_path"
    )
    authority_uid = _integer(
        installation["authority_uid"],
        "installation.authority_uid",
        minimum=0,
        maximum=2**31 - 1,
    )
    python_version = _string(
        installation["python_version"], "installation.python_version", maximum=32
    )
    if not VERSION_RE.fullmatch(python_version):
        _fail("installation.python_version must be an exact X.Y.Z version")

    repository = _object(root["repository"], "repository")
    _exact_keys(repository, {"root"}, "repository")
    repo_root = _absolute_path(repository["root"], "repository.root")

    gate = _object(root["gate"], "gate")
    _exact_keys(
        gate,
        {
            "phase",
            "verifier_path",
            "verifier_sha256",
            "approval_path",
            "profile_json_path",
            "profile_json_sha256",
            "profile_duckdb_path",
            "profile_duckdb_sha256",
        },
        "gate",
    )
    if gate["phase"] != "selection":
        _fail("only Gate 0B selection verification is supported")
    verifier_path = _relative_path(gate["verifier_path"], "gate.verifier_path")
    approval_path = _relative_path(gate["approval_path"], "gate.approval_path")
    if verifier_path != CANONICAL_GATE_VERIFIER:
        _fail(f"gate.verifier_path must be {CANONICAL_GATE_VERIFIER}")
    if approval_path != CANONICAL_SELECTION_APPROVAL:
        _fail(f"gate.approval_path must be {CANONICAL_SELECTION_APPROVAL}")
    profile_json_path = _relative_path(
        gate["profile_json_path"], "gate.profile_json_path"
    )
    profile_duckdb_path = _relative_path(
        gate["profile_duckdb_path"], "gate.profile_duckdb_path"
    )
    _assert_profile_path(profile_json_path, "g038-g040.index.json", "gate.profile_json_path")
    _assert_profile_path(
        profile_duckdb_path,
        "g038-g040.index.duckdb",
        "gate.profile_duckdb_path",
    )
    if PurePosixPath(profile_json_path).parent != PurePosixPath(profile_duckdb_path).parent:
        _fail("Gate profile JSON and DuckDB paths must be one reviewed pair")

    trust = _object(root["trust"], "trust")
    _exact_keys(trust, {"allowed_signers_path", "allowed_signers_sha256"}, "trust")
    allowed_signers_path = _absolute_path(
        trust["allowed_signers_path"], "trust.allowed_signers_path"
    )

    execution = _object(root["execution"], "execution")
    _exact_keys(
        execution,
        {"run_selection_enabled", "expected_goal_ids", "runners"},
        "execution",
    )
    goal_ids = execution["expected_goal_ids"]
    if not isinstance(goal_ids, list) or tuple(goal_ids) != EXPECTED_GOAL_IDS:
        _fail(f"execution.expected_goal_ids must be exactly {list(EXPECTED_GOAL_IDS)}")
    run_enabled = _boolean(
        execution["run_selection_enabled"], "execution.run_selection_enabled"
    )
    raw_runners = execution["runners"]
    if not isinstance(raw_runners, list):
        _fail("execution.runners must be an array")
    runners: list[RunnerPolicy] = []
    seen_goals: set[str] = set()
    for index, raw_runner in enumerate(raw_runners):
        runner = _object(raw_runner, f"execution.runners[{index}]")
        _exact_keys(
            runner,
            {"goal_id", "path", "sha256", "input_mode", "output_mode"},
            f"execution.runners[{index}]",
        )
        goal_id = _string(runner["goal_id"], f"execution.runners[{index}].goal_id")
        if goal_id in seen_goals or goal_id not in EXPECTED_RUNNERS:
            _fail("execution.runners contains an unexpected or duplicate goal")
        seen_goals.add(goal_id)
        path = _relative_path(runner["path"], f"execution.runners[{index}].path")
        if path != EXPECTED_RUNNERS[goal_id]:
            _fail(f"runner path for {goal_id} must be {EXPECTED_RUNNERS[goal_id]}")
        if runner["input_mode"] != "sealed-fd-json/v1":
            _fail(f"runner input mode for {goal_id} must be sealed-fd-json/v1")
        if runner["output_mode"] != "stdout-json/v1":
            _fail(f"runner output mode for {goal_id} must be stdout-json/v1")
        runners.append(
            RunnerPolicy(
                goal_id=goal_id,
                path=path,
                sha256=_digest(
                    runner["sha256"], f"execution.runners[{index}].sha256"
                ),
                input_mode=runner["input_mode"],
                output_mode=runner["output_mode"],
            )
        )
    if run_enabled:
        if seen_goals != set(EXPECTED_GOAL_IDS):
            _fail("enabled run selection requires all three dedicated runners")
    elif raw_runners:
        _fail("verify-only execution policy must not inject dormant runners")

    receipts = _object(root["receipts"], "receipts")
    _exact_keys(
        receipts,
        {
            "root",
            "allowed_signers_path",
            "allowed_signers_sha256",
            "signer_identity",
            "signer_fingerprint",
            "signature_namespace",
        },
        "receipts",
    )
    receipt_fingerprint = _string(
        receipts["signer_fingerprint"], "receipts.signer_fingerprint", maximum=80
    )
    if not FINGERPRINT_RE.fullmatch(receipt_fingerprint):
        _fail("receipts.signer_fingerprint must be an OpenSSH SHA256 fingerprint")
    receipt_namespace = _string(
        receipts["signature_namespace"], "receipts.signature_namespace", maximum=128
    )
    if receipt_namespace != "world-aid-gate-first-launch-v1":
        _fail("receipt signature namespace is not the fixed launch namespace")

    runtime = _object(root["runtime"], "runtime")
    _exact_keys(
        runtime,
        {
            "require_isolated_python",
            "require_no_site",
            "require_dont_write_bytecode",
            "clean_environment",
            "apparmor_profile",
            "network_namespace",
            "gate_timeout_seconds",
            "max_child_output_bytes",
        },
        "runtime",
    )
    for flag in (
        "require_isolated_python",
        "require_no_site",
        "require_dont_write_bytecode",
    ):
        if _boolean(runtime[flag], f"runtime.{flag}") is not True:
            _fail(f"runtime.{flag} cannot be disabled")
    clean_environment = _object(runtime["clean_environment"], "runtime.clean_environment")
    if dict(clean_environment) != EXPECTED_CLEAN_ENVIRONMENT:
        _fail("runtime.clean_environment must equal the compiled minimal environment")

    return OperatorPolicy(
        raw_sha256=raw_sha256,
        launcher_path=launcher_path,
        launcher_sha256=_digest(
            installation["launcher_sha256"], "installation.launcher_sha256"
        ),
        python_path=python_path,
        python_sha256=_digest(
            installation["python_sha256"], "installation.python_sha256"
        ),
        python_version=python_version,
        ssh_keygen_path=ssh_keygen_path,
        ssh_keygen_sha256=_digest(
            installation["ssh_keygen_sha256"], "installation.ssh_keygen_sha256"
        ),
        authority_uid=authority_uid,
        repo_root=repo_root,
        gate_verifier_path=verifier_path,
        gate_verifier_sha256=_digest(
            gate["verifier_sha256"], "gate.verifier_sha256"
        ),
        selection_approval_path=approval_path,
        profile_json_path=profile_json_path,
        profile_json_sha256=_digest(
            gate["profile_json_sha256"], "gate.profile_json_sha256"
        ),
        profile_duckdb_path=profile_duckdb_path,
        profile_duckdb_sha256=_digest(
            gate["profile_duckdb_sha256"], "gate.profile_duckdb_sha256"
        ),
        allowed_signers_path=allowed_signers_path,
        allowed_signers_sha256=_digest(
            trust["allowed_signers_sha256"], "trust.allowed_signers_sha256"
        ),
        run_selection_enabled=run_enabled,
        runners=tuple(sorted(runners, key=lambda item: item.goal_id)),
        receipt_root=_absolute_path(receipts["root"], "receipts.root"),
        receipt_allowed_signers_path=_absolute_path(
            receipts["allowed_signers_path"], "receipts.allowed_signers_path"
        ),
        receipt_allowed_signers_sha256=_digest(
            receipts["allowed_signers_sha256"], "receipts.allowed_signers_sha256"
        ),
        receipt_signer_identity=_string(
            receipts["signer_identity"], "receipts.signer_identity", maximum=254
        ),
        receipt_signer_fingerprint=receipt_fingerprint,
        receipt_signature_namespace=receipt_namespace,
        apparmor_profile=_string(
            runtime["apparmor_profile"], "runtime.apparmor_profile", maximum=255
        ),
        network_namespace=_string(
            runtime["network_namespace"], "runtime.network_namespace", maximum=255
        ),
        gate_timeout_seconds=_integer(
            runtime["gate_timeout_seconds"],
            "runtime.gate_timeout_seconds",
            minimum=MIN_GATE_TIMEOUT_SECONDS,
            maximum=MAX_GATE_TIMEOUT_SECONDS,
        ),
        max_child_output_bytes=_integer(
            runtime["max_child_output_bytes"],
            "runtime.max_child_output_bytes",
            minimum=MIN_OUTPUT_BYTES,
            maximum=MAX_OUTPUT_BYTES,
        ),
    )


def _paths_overlap(first: Path, second: Path) -> bool:
    return (
        first == second
        or first in second.parents
        or second in first.parents
    )


def _assert_policy_authority_separation(
    policy: OperatorPolicy,
    *,
    policy_path: Path,
    context: ExternalSecurityContext,
) -> None:
    """Keep operator trust and publication state outside repository authority."""

    if context == ROOT_OPERATOR_CONTEXT:
        if policy_path != FIXED_OPERATOR_POLICY_PATH:
            _fail(f"production policy path must be {FIXED_OPERATOR_POLICY_PATH}")
        if policy.launcher_path != FIXED_INSTALLED_LAUNCHER_PATH:
            _fail(
                f"production launcher path must be {FIXED_INSTALLED_LAUNCHER_PATH}"
            )
        if policy.ssh_keygen_path != FIXED_SSH_KEYGEN_PATH:
            _fail(f"production ssh-keygen path must be {FIXED_SSH_KEYGEN_PATH}")

    external_files = {
        "operator policy": policy_path,
        "installed launcher": policy.launcher_path,
        "isolated Python interpreter": policy.python_path,
        "ssh-keygen": policy.ssh_keygen_path,
        "Gate allowed-signers store": policy.allowed_signers_path,
        "receipt allowed-signers store": policy.receipt_allowed_signers_path,
    }
    for label, path in external_files.items():
        if _paths_overlap(path, policy.repo_root):
            _fail(f"{label} must be outside repository authority")
    if _paths_overlap(policy.receipt_root, policy.repo_root):
        _fail("receipt root must be outside repository authority")
    for label, path in external_files.items():
        if _paths_overlap(path, policy.receipt_root):
            _fail(f"{label} must not overlap the receipt publication root")
    if policy.allowed_signers_path == policy.receipt_allowed_signers_path:
        _fail("Gate and receipt allowed-signers stores must be distinct")


def load_operator_policy(
    policy_path: Path = FIXED_OPERATOR_POLICY_PATH,
    *,
    context: ExternalSecurityContext = ROOT_OPERATOR_CONTEXT,
) -> OperatorPolicy:
    """Load a policy through the operator-owned, no-symlink trust boundary.

    The production CLI always uses the compiled path and root context.
    """

    with _secure_external_snapshot(
        policy_path,
        context=context,
        maximum_bytes=MAX_POLICY_BYTES,
        label="operator policy",
        leaf_write_mask=0o222,
        require_single_link=True,
    ) as snapshot:
        payload = load_json_strict(snapshot.read_bytes(), label="operator policy")
        policy = _validate_policy_payload(payload, snapshot.sha256)
        _assert_policy_authority_separation(
            policy,
            policy_path=policy_path,
            context=context,
        )
        return policy


def validate_authority_environment(environ: Mapping[str, str]) -> None:
    """Reject ambient configuration and secrets; children use a fixed env."""

    names = set(environ)
    dangerous = sorted(
        name
        for name in names
        if any(name.startswith(prefix) for prefix in DANGEROUS_ENVIRONMENT_PREFIXES)
    )
    if dangerous:
        _fail(f"dangerous authority environment variables are present: {dangerous}")
    unexpected = sorted(names - AUTHORITY_ENVIRONMENT_NAMES)
    if unexpected:
        _fail(f"unexpected authority environment variables are present: {unexpected}")
    if dict(environ) != EXPECTED_CLEAN_ENVIRONMENT:
        _fail("authority environment does not equal the compiled minimal environment")


def validate_isolated_interpreter() -> None:
    """Require the launcher itself to have been invoked with ``-I -S -B``."""

    if sys.flags.isolated != 1:
        _fail("launcher must be invoked with Python -I")
    if sys.flags.no_site != 1:
        _fail("launcher must be invoked with Python -S")
    if sys.flags.dont_write_bytecode != 1:
        _fail("launcher must be invoked with Python -B")


def _require_digest(snapshot: SealedFileSnapshot, expected: str, label: str) -> None:
    if snapshot.sha256 != expected:
        _fail(f"{label} digest differs from the operator policy")


def _validate_approval_binding(raw: bytes, policy: OperatorPolicy) -> None:
    approval = _object(
        load_json_strict(raw, label="selection approval"),
        "selection approval",
    )
    if approval.get("schema_version") != SELECTION_APPROVAL_SCHEMA:
        _fail("selection approval uses the wrong schema")
    if approval.get("gate_id") != SELECTION_GATE_ID:
        _fail("selection approval uses the wrong gate id")

    scope = _object(approval.get("scope"), "selection approval.scope")
    goals = scope.get("goal_ids")
    if not isinstance(goals, list) or tuple(goals) != EXPECTED_GOAL_IDS:
        _fail("selection approval goal set/order differs from the fixed policy")

    reviewed = _object(
        approval.get("reviewed_state"), "selection approval.reviewed_state"
    )
    reviewed_artifact_paths: dict[str, str] = {}
    reviewed_artifact_digests: dict[str, str] = {}
    expected_records = {
        "restricted_bundle_index": (
            policy.profile_json_path,
            policy.profile_json_sha256,
        ),
        "restricted_bundle_index_duckdb": (
            policy.profile_duckdb_path,
            policy.profile_duckdb_sha256,
        ),
        **{
            key: (path, None)
            for key, path in EXECUTION_BOUND_ARTIFACT_PATHS.items()
        },
    }
    for key, (expected_path, expected_digest) in expected_records.items():
        label = f"selection approval.reviewed_state.{key}"
        record = _object(reviewed.get(key), label)
        _exact_keys(record, {"path", "sha256"}, label)
        path = _relative_path(record["path"], f"{label}.path")
        digest = _digest(record["sha256"], f"{label}.sha256")
        if path != expected_path:
            _fail(f"selection approval {key} uses the wrong canonical path")
        if expected_digest is not None and digest != expected_digest:
            _fail(f"selection approval {key} differs from the operator policy")
        if key in EXECUTION_BOUND_ARTIFACT_PATHS:
            reviewed_artifact_paths[key] = path
            reviewed_artifact_digests[key] = digest

    boundary = _object(
        approval.get("execution_boundary"),
        "selection approval.execution_boundary",
    )
    _exact_keys(
        boundary,
        {
            "protocol_id",
            "execution_authority",
            "operation",
            "sealed_input_protocol",
            "result_protocol",
            "installed_launcher_path",
            "operator_policy_id",
            "operator_policy_sha256",
            "deployment_attestation_id",
            "deployment_attestation_sha256",
            "reviewed_artifacts",
        },
        "selection approval.execution_boundary",
    )
    expected_literals = {
        "protocol_id": GATE_FIRST_PROTOCOL_ID,
        "execution_authority": GATE_FIRST_EXECUTION_AUTHORITY,
        "operation": SELECTION_OPERATION,
        "sealed_input_protocol": SEALED_INPUT_PROTOCOL,
        "result_protocol": RESULT_PROTOCOL,
        "installed_launcher_path": policy.launcher_path.as_posix(),
        "operator_policy_id": POLICY_SCHEMA,
    }
    for key, expected in expected_literals.items():
        observed = _string(
            boundary[key],
            f"selection approval.execution_boundary.{key}",
            maximum=256,
        )
        if observed != expected:
            _fail(
                "selection approval execution boundary "
                f"{key} differs from the operator policy"
            )

    policy_digest = _digest(
        boundary["operator_policy_sha256"],
        "selection approval.execution_boundary.operator_policy_sha256",
    )
    if policy_digest != policy.raw_sha256:
        _fail(
            "selection approval execution boundary policy digest differs "
            "from the loaded operator policy"
        )
    attestation_id = _string(
        boundary["deployment_attestation_id"],
        "selection approval.execution_boundary.deployment_attestation_id",
        minimum=30,
        maximum=128,
    )
    if not DEPLOYMENT_ATTESTATION_ID_RE.fullmatch(attestation_id):
        _fail("selection approval deployment attestation id is invalid")
    _digest(
        boundary["deployment_attestation_sha256"],
        "selection approval.execution_boundary.deployment_attestation_sha256",
    )

    boundary_artifacts = _object(
        boundary["reviewed_artifacts"],
        "selection approval.execution_boundary.reviewed_artifacts",
    )
    _exact_keys(
        boundary_artifacts,
        set(EXECUTION_BOUND_ARTIFACT_PATHS),
        "selection approval.execution_boundary.reviewed_artifacts",
    )
    for key, reviewed_digest in reviewed_artifact_digests.items():
        boundary_digest = _digest(
            boundary_artifacts[key],
            (
                "selection approval.execution_boundary."
                f"reviewed_artifacts.{key}"
            ),
        )
        if boundary_digest != reviewed_digest:
            _fail(
                "selection approval execution boundary artifact "
                f"{key} does not bind its reviewed-state digest"
            )

    policy_bound_artifacts = {
        "gate_launcher": policy.launcher_sha256,
        "gate_verifier": policy.gate_verifier_sha256,
    }
    for key, expected_digest in policy_bound_artifacts.items():
        if reviewed_artifact_digests[key] != expected_digest:
            _fail(
                f"selection approval {key} digest differs from the operator policy"
            )

    if policy.run_selection_enabled:
        runners = {runner.goal_id: runner for runner in policy.runners}
        if set(runners) != set(EXPECTED_GOAL_IDS):
            _fail("operator policy does not bind all selection runners")
        for goal_id in EXPECTED_GOAL_IDS:
            runner = runners[goal_id]
            artifact_key = RUNNER_REVIEWED_ARTIFACT_KEYS[goal_id]
            if runner.path != reviewed_artifact_paths[artifact_key]:
                _fail(
                    f"operator policy runner path for {goal_id} differs "
                    "from the reviewed artifact"
                )
            if runner.sha256 != reviewed_artifact_digests[artifact_key]:
                _fail(
                    f"operator policy runner digest for {goal_id} differs "
                    "from the reviewed artifact"
                )

    trust = _object(approval.get("trust"), "selection approval.trust")
    trust_digest = _digest(
        trust.get("allowed_signers_sha256"),
        "selection approval.trust.allowed_signers_sha256",
    )
    if trust_digest != policy.allowed_signers_sha256:
        _fail("selection approval trust-store digest differs from operator policy")


def _kill_process_group(process: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def _communicate_bounded(
    process: subprocess.Popen[bytes],
    *,
    timeout_seconds: int,
    maximum_bytes: int,
    label: str,
) -> tuple[bytes, bytes]:
    """Drain stdout/stderr with a real memory bound and group-wide timeout."""

    if process.stdout is None or process.stderr is None:
        _kill_process_group(process)
        _fail(f"{label} was not created with output pipes")
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ, "stdout")
    selector.register(process.stderr, selectors.EVENT_READ, "stderr")
    output = {"stdout": bytearray(), "stderr": bytearray()}
    deadline = time.monotonic() + timeout_seconds
    try:
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                _kill_process_group(process)
                _fail(f"{label} exceeded its operator timeout")
            events = selector.select(min(remaining, 0.25))
            if not events:
                continue
            for key, _mask in events:
                name = str(key.data)
                chunk = os.read(key.fd, 64 * 1024)
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                output[name].extend(chunk)
                if len(output["stdout"]) + len(output["stderr"]) > maximum_bytes:
                    _kill_process_group(process)
                    _fail(f"{label} exceeded its output bound")
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            _kill_process_group(process)
            _fail(f"{label} exceeded its operator timeout")
        try:
            process.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            _kill_process_group(process)
            _fail(f"{label} exceeded its operator timeout")
        return bytes(output["stdout"]), bytes(output["stderr"])
    finally:
        selector.close()
        process.stdout.close()
        process.stderr.close()


_GATE_CHILD_BOOTSTRAP = r"""
import json
import os
import sys
from pathlib import Path

if sys.flags.isolated != 1 or sys.flags.no_site != 1 or sys.flags.dont_write_bytecode != 1:
    raise SystemExit("isolated interpreter flags are missing")

def read_all(fd):
    size = os.fstat(fd).st_size
    chunks = []
    offset = 0
    while offset < size:
        chunk = os.pread(fd, min(1024 * 1024, size - offset), offset)
        if not chunk:
            raise RuntimeError("sealed input ended early")
        chunks.append(chunk)
        offset += len(chunk)
    return b"".join(chunks)

verifier_fd = int(sys.argv[1])
approval_fd = int(sys.argv[2])
repo_root = Path(sys.argv[3])
approval_path = Path(sys.argv[4])
allowed_signers_path = Path(sys.argv[5])
source = read_all(verifier_fd)
approval = read_all(approval_fd)
namespace = {
    "__name__": "_world_aid_gate_verifier_snapshot",
    "__file__": "<sealed-world-aid-gate-verifier>",
    "__package__": None,
}
exec(compile(source, namespace["__file__"], "exec"), namespace)
verify = namespace.get("verify_approval")
if not callable(verify):
    raise RuntimeError("pinned Gate verifier has no verify_approval API")
summary = verify(
    repo_root=repo_root,
    phase="selection",
    approval_path=approval_path,
    allowed_signers_path=allowed_signers_path,
    expected_approval_bytes=approval,
)
sys.stdout.write(json.dumps(summary, sort_keys=True, separators=(",", ":")) + "\n")
"""


def _run_pinned_gate(
    *,
    policy: OperatorPolicy,
    verifier: SealedFileSnapshot,
    approval: SealedFileSnapshot,
) -> Mapping[str, Any]:
    command = [
        policy.python_path.as_posix(),
        "-I",
        "-S",
        "-B",
        "-c",
        _GATE_CHILD_BOOTSTRAP,
        str(verifier.fd),
        str(approval.fd),
        policy.repo_root.as_posix(),
        policy.selection_approval_path,
        policy.allowed_signers_path.as_posix(),
    ]
    process = subprocess.Popen(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=dict(EXPECTED_CLEAN_ENVIRONMENT),
        close_fds=True,
        pass_fds=(verifier.fd, approval.fd),
        start_new_session=True,
    )
    stdout, stderr = _communicate_bounded(
        process,
        timeout_seconds=policy.gate_timeout_seconds,
        maximum_bytes=policy.max_child_output_bytes,
        label="pinned Gate verifier",
    )
    if process.returncode != 0:
        detail = stderr.decode("utf-8", errors="replace").strip()
        _fail(f"pinned Gate verifier rejected the selection approval: {detail[:1000]}")
    if stderr:
        _fail("pinned Gate verifier emitted unexpected stderr")
    summary = _object(
        load_json_strict(stdout, label="Gate verifier output"), "Gate verifier output"
    )
    expected = {
        "status": "verified",
        "phase": "selection",
        "gate_id": "gate-0b-selection",
        "offline": True,
        "live_actions_authorized": False,
    }
    for key, value in expected.items():
        observed = summary.get(key)
        if (
            observed is not value
            if isinstance(value, bool)
            else observed != value
        ):
            _fail(f"Gate verifier output has invalid {key}")
    return summary


def _verify_external_installation(
    *,
    policy: OperatorPolicy,
    actual_launcher_path: Path,
    context: ExternalSecurityContext,
) -> None:
    if policy.authority_uid != context.expected_owner_uid:
        _fail("operator policy authority uid differs from the installation boundary")
    if actual_launcher_path != policy.launcher_path:
        _fail(
            "this source copy is not the operator-policy-attested installed launcher; "
            "the in-repository copy is never an authority"
        )
    checks = (
        (
            policy.launcher_path,
            policy.launcher_sha256,
            "installed launcher",
            0o222,
            True,
            4 * 1024 * 1024,
        ),
        (
            policy.python_path,
            policy.python_sha256,
            "isolated Python interpreter",
            0o022,
            False,
            128 * 1024 * 1024,
        ),
        (
            policy.ssh_keygen_path,
            policy.ssh_keygen_sha256,
            "ssh-keygen",
            0o022,
            False,
            128 * 1024 * 1024,
        ),
        (
            policy.allowed_signers_path,
            policy.allowed_signers_sha256,
            "Gate allowed-signers store",
            0o222,
            True,
            2 * 1024 * 1024,
        ),
    )
    for path, digest, label, write_mask, single_link, maximum in checks:
        with _secure_external_snapshot(
            path,
            context=context,
            maximum_bytes=maximum,
            label=label,
            leaf_write_mask=write_mask,
            require_single_link=single_link,
        ) as snapshot:
            _require_digest(snapshot, digest, label)
    if Path(sys.executable).as_posix() != policy.python_path.as_posix():
        _fail("running Python path differs from the operator policy")
    running_version = ".".join(str(value) for value in sys.version_info[:3])
    if running_version != policy.python_version:
        _fail("running Python version differs from the operator policy")


def verify_only(
    *,
    policy_path: Path = FIXED_OPERATOR_POLICY_PATH,
    actual_launcher_path: Path | None = None,
    context: ExternalSecurityContext = ROOT_OPERATOR_CONTEXT,
    enforce_authority_runtime: bool = True,
) -> dict[str, Any]:
    """Verify the pinned selection approval without authorizing any runner.

    Non-default arguments are packaging/unit-test hooks.  The CLI supplies no
    path, trust, goal, command, ownership, or runtime override.
    """

    if enforce_authority_runtime:
        validate_isolated_interpreter()
        validate_authority_environment(os.environ)
        if os.geteuid() != 0:
            _fail("authoritative launcher requires effective uid 0")
    policy = load_operator_policy(policy_path, context=context)
    launcher_path = actual_launcher_path or Path(__file__).absolute()
    _verify_external_installation(
        policy=policy,
        actual_launcher_path=launcher_path,
        context=context,
    )

    repo_fd = _open_directory_no_symlink(policy.repo_root)
    snapshots: list[SealedFileSnapshot] = []
    try:
        verifier = snapshot_regular_file_at(
            repo_fd,
            policy.gate_verifier_path,
            maximum_bytes=MAX_VERIFIER_BYTES,
        )
        snapshots.append(verifier)
        approval = snapshot_regular_file_at(
            repo_fd,
            policy.selection_approval_path,
            maximum_bytes=MAX_APPROVAL_BYTES,
        )
        snapshots.append(approval)
        profile_json = snapshot_regular_file_at(
            repo_fd,
            policy.profile_json_path,
            maximum_bytes=MAX_PROFILE_BYTES,
        )
        snapshots.append(profile_json)
        profile_duckdb = snapshot_regular_file_at(
            repo_fd,
            policy.profile_duckdb_path,
            maximum_bytes=MAX_PROFILE_BYTES,
        )
        snapshots.append(profile_duckdb)

        _require_digest(verifier, policy.gate_verifier_sha256, "Gate verifier")
        _require_digest(profile_json, policy.profile_json_sha256, "profile JSON")
        _require_digest(profile_duckdb, policy.profile_duckdb_sha256, "profile DuckDB")
        _validate_approval_binding(approval.read_bytes(), policy)

        summary = _run_pinned_gate(
            policy=policy,
            verifier=verifier,
            approval=approval,
        )
        for snapshot in snapshots:
            revalidate_regular_file_at(repo_fd, snapshot)
        return {
            "schema": VERIFY_RESULT_SCHEMA,
            "status": "verified",
            "phase": "selection",
            "gate_summary": dict(summary),
            "policy_sha256": policy.raw_sha256,
            "launcher_sha256": policy.launcher_sha256,
            "gate_verifier_sha256": verifier.sha256,
            "approval_sha256": approval.sha256,
            "profile_json_sha256": profile_json.sha256,
            "profile_duckdb_sha256": profile_duckdb.sha256,
            "expected_goal_ids": list(EXPECTED_GOAL_IDS),
            "run_selection_authorized": False,
            "live_actions_authorized": False,
            "offline": True,
        }
    finally:
        for snapshot in snapshots:
            snapshot.close()
        os.close(repo_fd)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--verify-only",
        action="store_true",
        required=True,
        help="Verify the fixed operator policy and Gate 0B selection; never run goals.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if not args.verify_only:  # pragma: no cover - argparse enforces this.
        return 2
    try:
        result = verify_only(
            policy_path=FIXED_OPERATOR_POLICY_PATH,
            actual_launcher_path=Path(__file__).absolute(),
            context=ROOT_OPERATOR_CONTEXT,
            enforce_authority_runtime=True,
        )
    except (GateFirstLauncherError, OSError, subprocess.SubprocessError) as exc:
        print(f"World-aid Gate-first launcher REFUSED: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
