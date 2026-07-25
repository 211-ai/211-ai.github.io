#!/usr/bin/env python3
"""Operator-only, fail-closed WORLDCOIN-G040 DuckDB smoke primitive.

This module is an execution primitive, never an authorization primitive.  It
has no CLI and reads no ambient configuration.  A trusted Gate-first launcher
must authenticate the frozen ``DuckDBBootstrapPlan`` and externally enforce
the plan's deny-all network boundary before calling
``run_approved_duckdb_bootstrap``.

The legacy runtime fence in ``tests/world_aid/test_duckdb_bootstrap.py`` stays
closed.  This runner never uses pip, an index, wheel lifecycle code, or an
already-installed DuckDB distribution.  It validates and extracts the exact
approved wheel into a fresh private site root, invokes the exact approved
Python through its pinned descriptor with ``-I -S -B``, removes all transient
state, and only then publishes one no-replace external receipt.
"""

from __future__ import annotations

import base64
import binascii
import csv
import ctypes
import email.policy
import fcntl
import hashlib
import io
import json
import math
import os
import re
import resource
import secrets
import selectors
import shutil
import signal
import stat
import subprocess
import sys
import time
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from email.parser import BytesParser
from pathlib import Path, PurePosixPath
from typing import Final

PLAN_SCHEMA: Final = "world-human-aid-g040-duckdb-bootstrap-plan/v1"
RECEIPT_SCHEMA: Final = "world-human-aid-g040-duckdb-bootstrap-receipt/v1"
CHILD_RESULT_SCHEMA: Final = "world-human-aid-g040-duckdb-smoke-child/v1"
RECEIPT_NAME: Final = "g040-duckdb-bootstrap-receipt.json"
GOAL_ID: Final = "WORLDCOIN-G040"

REQUIRED_G040_CHECKS: Final = (
    "empty_isolated_environment",
    "hash_required_read_only_wheelhouse_install",
    "index_extension_registry_dns_http_denied",
    "local_filesystem_database",
    "transaction_commit",
    "rollback",
    "uniqueness",
    "compare_and_swap",
    "atomic_outbox",
    "direct_second_writer_rejected",
    "checkpoint",
    "crash_and_reopen",
    "raw_opaque_backup_and_restore",
    "corruption_detected",
    "opaque_synthetic_payload_round_trip",
    "extensions_absent_and_deny_settings_locked",
    "database_wal_and_temporary_data_torn_down",
)
G033_EXCLUDED_CONTROLS: Final = (
    "application_envelope_encryption",
    "plaintext_marker_absence",
    "encrypted_authenticated_production_backup",
    "key_rotation_retention_and_deletion",
)

_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_VERSION_RE = re.compile(r"^[0-9]+(?:\.[0-9]+){2,3}$")
_PYTHON_TAG_RE = re.compile(r"^cp[0-9]{2,3}$")
_ABI_TAG_RE = re.compile(r"^cp[0-9]{2,3}(?:[a-z0-9_]*)$")
_PLATFORM_TAG_RE = re.compile(r"^[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)*$")
_WHEEL_NAME_RE = re.compile(
    r"^duckdb-(?P<version>[0-9]+(?:\.[0-9]+){2,3})-"
    r"(?P<python>cp[0-9]{2,3})-(?P<abi>cp[0-9]{2,3}[a-z0-9_]*)-"
    r"(?P<platform>[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)*)\.whl$"
)
_MAX_BOUND_ARTIFACT_BYTES = 2 * 1024 * 1024 * 1024
_MAX_PYTHON_BYTES = 256 * 1024 * 1024
_MAX_WHEEL_BYTES = 2 * 1024 * 1024 * 1024
_MAX_PATH_BYTES = 4096
_READ_CHUNK = 64 * 1024
_FIXED_NOFILE_LIMIT = 128
_ALLOWED_COMPRESSION = frozenset({zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED})
_REQUIRED_INPUT_ROLES = (
    "authorization",
    "network_boundary_attestation",
    "requirements_lock",
    "runtime_policy",
    "backup_policy",
    "storage_adr",
)
_CLEAN_ENVIRONMENT: Final[dict[str, str]] = {
    "HOME": "",  # Replaced by a workspace-private directory.
    "LANG": "C",
    "LC_ALL": "C",
    "PATH": "/nonexistent",
    "PIP_DISABLE_PIP_VERSION_CHECK": "1",
    "PIP_NO_INDEX": "1",
    "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONHASHSEED": "0",
    "PYTHONNOUSERSITE": "1",
    "SOURCE_DATE_EPOCH": "0",
    "TMPDIR": "",  # Replaced by a workspace-private directory.
    "TZ": "UTC",
    "http_proxy": "",
    "https_proxy": "",
    "no_proxy": "*",
}


class G040DuckDBBootstrapError(RuntimeError):
    """Raised when G040 cannot produce trustworthy smoke evidence."""


@dataclass(frozen=True, slots=True)
class DuckDBResourceBounds:
    """Authenticated execution, extraction, and output bounds."""

    max_seconds: int
    max_memory_mb: int
    max_output_bytes: int
    max_file_bytes: int
    max_workspace_bytes: int
    max_wheel_entries: int
    max_entry_bytes: int
    max_uncompressed_bytes: int

    def __post_init__(self) -> None:
        _plain_int("resource_bounds.max_seconds", self.max_seconds, 1, 3600)
        _plain_int("resource_bounds.max_memory_mb", self.max_memory_mb, 64, 65536)
        _plain_int(
            "resource_bounds.max_output_bytes",
            self.max_output_bytes,
            1,
            1024 * 1024 * 1024,
        )
        _plain_int(
            "resource_bounds.max_file_bytes",
            self.max_file_bytes,
            1024,
            4 * 1024 * 1024 * 1024,
        )
        _plain_int(
            "resource_bounds.max_workspace_bytes",
            self.max_workspace_bytes,
            1024,
            8 * 1024 * 1024 * 1024,
        )
        _plain_int(
            "resource_bounds.max_wheel_entries",
            self.max_wheel_entries,
            4,
            100_000,
        )
        _plain_int(
            "resource_bounds.max_entry_bytes",
            self.max_entry_bytes,
            1,
            2 * 1024 * 1024 * 1024,
        )
        _plain_int(
            "resource_bounds.max_uncompressed_bytes",
            self.max_uncompressed_bytes,
            1,
            4 * 1024 * 1024 * 1024,
        )
        if self.max_entry_bytes > self.max_uncompressed_bytes:
            _fail("max_entry_bytes cannot exceed max_uncompressed_bytes")
        if self.max_uncompressed_bytes > self.max_workspace_bytes:
            _fail("max_uncompressed_bytes cannot exceed max_workspace_bytes")


@dataclass(frozen=True, slots=True)
class DuckDBBoundArtifact:
    """One exact regular file authenticated outside repository Python."""

    source_path: Path
    sha256: str
    size: int

    def __post_init__(self) -> None:
        _absolute_path("bound artifact source_path", self.source_path)
        _digest("bound artifact sha256", self.sha256)
        _plain_int(
            "bound artifact size",
            self.size,
            1,
            _MAX_BOUND_ARTIFACT_BYTES,
        )


@dataclass(frozen=True, slots=True)
class DuckDBBootstrapPlan:
    """Frozen operator handoff created only after Gate-first verification."""

    schema_version: str
    goal_id: str
    authorization: DuckDBBoundArtifact
    network_boundary_attestation: DuckDBBoundArtifact
    network_policy: str
    python_path: Path
    python_sha256: str
    python_size: int
    python_version: str
    wheel_path: Path
    wheel_sha256: str
    wheel_size: int
    wheel_filename: str
    duckdb_version: str
    python_tag: str
    abi_tag: str
    platform_tag: str
    requirements_lock: DuckDBBoundArtifact
    runtime_policy: DuckDBBoundArtifact
    backup_policy: DuckDBBoundArtifact
    storage_adr: DuckDBBoundArtifact
    smoke_bootstrap_sha256: str
    resource_bounds: DuckDBResourceBounds
    run_directory: Path
    expires_at: str

    def __post_init__(self) -> None:
        if self.schema_version != PLAN_SCHEMA:
            _fail(f"schema_version must be {PLAN_SCHEMA!r}")
        if self.goal_id != GOAL_ID:
            _fail(f"goal_id must be {GOAL_ID!r}")
        for role in _REQUIRED_INPUT_ROLES:
            value = getattr(self, role)
            if not isinstance(value, DuckDBBoundArtifact):
                _fail(f"{role} must be DuckDBBoundArtifact")
        if self.network_policy != "external-deny-all":
            _fail("network_policy must be exactly 'external-deny-all'")
        _absolute_path("python_path", self.python_path)
        _digest("python_sha256", self.python_sha256)
        _plain_int("python_size", self.python_size, 1, _MAX_PYTHON_BYTES)
        if not isinstance(self.python_version, str) or not _VERSION_RE.fullmatch(self.python_version):
            _fail("python_version must be an exact numeric X.Y.Z version")
        _absolute_path("wheel_path", self.wheel_path)
        _digest("wheel_sha256", self.wheel_sha256)
        _plain_int("wheel_size", self.wheel_size, 1, _MAX_WHEEL_BYTES)
        if not isinstance(self.resource_bounds, DuckDBResourceBounds):
            _fail("resource_bounds must be DuckDBResourceBounds")
        if self.wheel_size > self.resource_bounds.max_workspace_bytes:
            _fail("wheel_size exceeds the authenticated workspace byte bound")
        _validate_wheel_selection(self)
        _digest("smoke_bootstrap_sha256", self.smoke_bootstrap_sha256)
        if self.smoke_bootstrap_sha256 != fixed_smoke_bootstrap_sha256():
            _fail("smoke_bootstrap_sha256 differs from the fixed runner bootstrap")
        _absolute_path("run_directory", self.run_directory)
        for role in _REQUIRED_INPUT_ROLES:
            artifact = getattr(self, role)
            if _paths_overlap(artifact.source_path, self.run_directory):
                _fail(f"{role} must not overlap the external run directory")
        for label, path in (
            ("python_path", self.python_path),
            ("wheel_path", self.wheel_path),
        ):
            if _paths_overlap(path, self.run_directory):
                _fail(f"{label} must not overlap the external run directory")
        _parse_expiry(self.expires_at)


@dataclass(frozen=True, slots=True)
class _PinnedFile:
    role: str
    path: Path
    sha256: str
    size: int
    descriptor: int
    metadata: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class _WheelEvidence:
    entry_count: int
    file_count: int
    uncompressed_bytes: int
    record_count: int
    metadata_name: str
    metadata_version: str
    wheel_tag: str

    def as_dict(self) -> dict[str, int | str]:
        return {
            "entry_count": self.entry_count,
            "file_count": self.file_count,
            "uncompressed_bytes": self.uncompressed_bytes,
            "record_count": self.record_count,
            "metadata_name": self.metadata_name,
            "metadata_version": self.metadata_version,
            "wheel_tag": self.wheel_tag,
        }


@dataclass(frozen=True, slots=True)
class _CommandEvidence:
    exit_code: int
    elapsed_ms: int
    stdout_sha256: str
    stdout_bytes: int
    stderr_sha256: str
    stderr_bytes: int

    def as_dict(self) -> dict[str, int | str]:
        return {
            "exit_code": self.exit_code,
            "elapsed_ms": self.elapsed_ms,
            "stdout_sha256": self.stdout_sha256,
            "stdout_bytes": self.stdout_bytes,
            "stderr_sha256": self.stderr_sha256,
            "stderr_bytes": self.stderr_bytes,
        }


def _fail(message: str) -> None:
    raise G040DuckDBBootstrapError(message)


def _plain_int(name: str, value: object, minimum: int, maximum: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        _fail(f"{name} must be an integer from {minimum} through {maximum}")


def _digest(name: str, value: object) -> None:
    if not isinstance(value, str) or _DIGEST_RE.fullmatch(value) is None:
        _fail(f"{name} must be a lowercase sha256 digest")


def _absolute_path(name: str, value: object) -> None:
    if not isinstance(value, Path) or not value.is_absolute():
        _fail(f"{name} must be an absolute pathlib.Path")
    text = os.fspath(value)
    if "\x00" in text or ".." in value.parts or value.as_posix() != text:
        _fail(f"{name} must be normalized, NUL-free, and traversal-free")


def _paths_overlap(first: Path, second: Path) -> bool:
    return first == second or first in second.parents or second in first.parents


def _parse_expiry(value: object) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        _fail("expires_at must be a canonical UTC timestamp ending in Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise G040DuckDBBootstrapError("expires_at is not a real timestamp") from exc
    if parsed.tzinfo != UTC or parsed.isoformat(timespec="seconds").replace("+00:00", "Z") != value:
        _fail("expires_at must use canonical second-precision UTC form")
    return parsed


def _require_unexpired(plan: DuckDBBootstrapPlan) -> None:
    if datetime.now(UTC) >= _parse_expiry(plan.expires_at):
        _fail("the immutable G040 execution plan has expired")


def _require_deadline(deadline: float, bounds: DuckDBResourceBounds) -> None:
    if time.monotonic() >= deadline:
        _fail(f"DuckDB bootstrap exceeded the {bounds.max_seconds}-second bound")


def _validate_wheel_selection(plan: DuckDBBootstrapPlan) -> None:
    if not isinstance(plan.wheel_filename, str) or plan.wheel_filename != plan.wheel_path.name:
        _fail("wheel_filename must exactly equal wheel_path.name")
    match = _WHEEL_NAME_RE.fullmatch(plan.wheel_filename)
    if match is None:
        _fail("wheel_filename is not an exact native CPython DuckDB wheel")
    if not isinstance(plan.duckdb_version, str) or not _VERSION_RE.fullmatch(plan.duckdb_version):
        _fail("duckdb_version must be an exact numeric version")
    if not isinstance(plan.python_tag, str) or not _PYTHON_TAG_RE.fullmatch(plan.python_tag):
        _fail("python_tag must be an exact CPython tag")
    if not isinstance(plan.abi_tag, str) or not _ABI_TAG_RE.fullmatch(plan.abi_tag):
        _fail("abi_tag must be an exact CPython ABI tag")
    if not isinstance(plan.platform_tag, str) or not _PLATFORM_TAG_RE.fullmatch(plan.platform_tag):
        _fail("platform_tag is invalid")
    selected = (
        match.group("version"),
        match.group("python"),
        match.group("abi"),
        match.group("platform"),
    )
    expected = (
        plan.duckdb_version,
        plan.python_tag,
        plan.abi_tag,
        plan.platform_tag,
    )
    if selected != expected:
        _fail("wheel filename version/ABI/platform tags conflict with the plan")
    version_parts = plan.python_version.split(".")
    expected_python_tag = f"cp{version_parts[0]}{version_parts[1]}"
    if plan.python_tag != expected_python_tag or not plan.abi_tag.startswith(expected_python_tag):
        _fail("Python executable version conflicts with wheel CPython/ABI tags")


def _canonical_json_bytes(payload: object) -> bytes:
    return (
        json.dumps(
            payload,
            ensure_ascii=True,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _artifact_payload(artifact: DuckDBBoundArtifact) -> dict[str, object]:
    return {
        "source_path": os.fspath(artifact.source_path),
        "sha256": artifact.sha256,
        "size": artifact.size,
    }


def _plan_payload(plan: DuckDBBootstrapPlan) -> dict[str, object]:
    return {
        "schema_version": plan.schema_version,
        "goal_id": plan.goal_id,
        "authorization": _artifact_payload(plan.authorization),
        "network_boundary_attestation": _artifact_payload(plan.network_boundary_attestation),
        "network_policy": plan.network_policy,
        "python": {
            "path": os.fspath(plan.python_path),
            "sha256": plan.python_sha256,
            "size": plan.python_size,
            "version": plan.python_version,
        },
        "wheel": {
            "path": os.fspath(plan.wheel_path),
            "sha256": plan.wheel_sha256,
            "size": plan.wheel_size,
            "filename": plan.wheel_filename,
            "duckdb_version": plan.duckdb_version,
            "python_tag": plan.python_tag,
            "abi_tag": plan.abi_tag,
            "platform_tag": plan.platform_tag,
        },
        "requirements_lock": _artifact_payload(plan.requirements_lock),
        "runtime_policy": _artifact_payload(plan.runtime_policy),
        "backup_policy": _artifact_payload(plan.backup_policy),
        "storage_adr": _artifact_payload(plan.storage_adr),
        "smoke_bootstrap_sha256": plan.smoke_bootstrap_sha256,
        "resource_bounds": {
            "max_seconds": plan.resource_bounds.max_seconds,
            "max_memory_mb": plan.resource_bounds.max_memory_mb,
            "max_output_bytes": plan.resource_bounds.max_output_bytes,
            "max_file_bytes": plan.resource_bounds.max_file_bytes,
            "max_workspace_bytes": plan.resource_bounds.max_workspace_bytes,
            "max_wheel_entries": plan.resource_bounds.max_wheel_entries,
            "max_entry_bytes": plan.resource_bounds.max_entry_bytes,
            "max_uncompressed_bytes": plan.resource_bounds.max_uncompressed_bytes,
        },
        "run_directory": os.fspath(plan.run_directory),
        "expires_at": plan.expires_at,
    }


def execution_plan_sha256(plan: DuckDBBootstrapPlan) -> str:
    """Return the deterministic plan digest bound into the receipt."""

    if not isinstance(plan, DuckDBBootstrapPlan):
        _fail("plan must be DuckDBBootstrapPlan")
    return "sha256:" + hashlib.sha256(_canonical_json_bytes(_plan_payload(plan))).hexdigest()


_FIXED_SMOKE_BOOTSTRAP = r"""#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

CHECKS = (
    "empty_isolated_environment",
    "hash_required_read_only_wheelhouse_install",
    "index_extension_registry_dns_http_denied",
    "local_filesystem_database",
    "transaction_commit",
    "rollback",
    "uniqueness",
    "compare_and_swap",
    "atomic_outbox",
    "direct_second_writer_rejected",
    "checkpoint",
    "crash_and_reopen",
    "raw_opaque_backup_and_restore",
    "corruption_detected",
    "opaque_synthetic_payload_round_trip",
    "extensions_absent_and_deny_settings_locked",
    "database_wal_and_temporary_data_torn_down",
)
CHILD_SCHEMA = "world-human-aid-g040-duckdb-smoke-child/v1"
SECOND_WRITER_SCHEMA = "world-human-aid-g040-second-writer/v1"
DENY_CONFIG = {
    "enable_external_access": "false",
    "autoinstall_known_extensions": "false",
    "autoload_known_extensions": "false",
    "allow_community_extensions": "false",
    "lock_configuration": "true",
}
LOCK_EXCEPTION_TYPES = {"IOException"}
LOCK_MARKERS = (
    "could not set lock",
    "conflicting lock",
    "database is locked",
    "lock on file",
    "cannot acquire lock",
    "failed to acquire lock",
)
MAX_LOCK_MESSAGE_BYTES = 4096
MAX_LOCK_EXCERPT_BYTES = 1024

def require(condition, message):
    if not condition:
        raise RuntimeError(message)

def canonical(payload):
    return (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()

def write_exclusive_json(path, payload):
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
        0o600,
    )
    try:
        raw = canonical(payload)
        offset = 0
        while offset < len(raw):
            offset += os.write(descriptor, raw[offset:])
        os.fsync(descriptor)
    finally:
        os.close(descriptor)

def read_bounded_canonical_json(path, maximum):
    descriptor = os.open(
        path,
        os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
    )
    try:
        metadata = os.fstat(descriptor)
        require(0 < metadata.st_size <= maximum, "writer evidence size is invalid")
        raw = os.read(descriptor, maximum + 1)
    finally:
        os.close(descriptor)
    require(len(raw) == metadata.st_size, "writer evidence changed while read")
    payload = json.loads(raw.decode("utf-8"))
    require(isinstance(payload, dict), "writer evidence is not an object")
    require(canonical(payload) == raw, "writer evidence is not canonical")
    return payload

def within(path, root):
    Path(path).resolve(strict=True).relative_to(root.resolve(strict=True))

def load_duckdb(site_root, expected_version):
    require(sys.flags.isolated == 1, "Python -I missing")
    require(sys.flags.no_site == 1, "Python -S missing")
    require(sys.flags.dont_write_bytecode == 1, "Python -B missing")
    require(os.environ.get("PYTHONPATH") is None, "PYTHONPATH crossed boundary")
    sys.path.insert(0, str(site_root))
    import duckdb
    import _duckdb
    require(str(duckdb.__version__) == expected_version, "DuckDB version mismatch")
    within(duckdb.__file__, site_root)
    within(_duckdb.__file__, site_root)
    return duckdb

def connect(duckdb, path):
    return duckdb.connect(str(path), config=DENY_CONFIG)

def audit_dynamic_extensions(duckdb, extension_root):
    extension_root.mkdir(mode=0o700)
    audit = duckdb.connect(
        ":memory:",
        config={
            "autoinstall_known_extensions": "false",
            "autoload_known_extensions": "false",
            "allow_community_extensions": "false",
            "extension_directory": str(extension_root),
            "lock_configuration": "true",
        },
    )
    try:
        loaded = audit.execute(
            "SELECT extension_name FROM duckdb_extensions() "
            "WHERE loaded AND install_mode <> 'STATICALLY_LINKED'"
        ).fetchall()
    finally:
        audit.close()
    require(loaded == [], "unexpected dynamic extension loaded at preflight")
    require(
        list(extension_root.iterdir()) == [],
        "extension preflight created local extension state",
    )
    return []

def prove_deny_settings_locked(connection):
    for name in DENY_CONFIG:
        target = "false" if name == "lock_configuration" else "true"
        try:
            connection.execute(f"SET {name}={target}")
        except Exception as exc:
            require(type(exc).__module__ == "_duckdb", "lock error was not DuckDB")
            require(
                type(exc).__name__ == "InvalidInputException",
                "lock error had an unexpected class",
            )
            require(
                "configuration has been locked" in str(exc).lower(),
                "configuration lock was not the rejection reason",
            )
        else:
            raise RuntimeError(f"deny setting was mutable: {name}")
    setting_names = tuple(DENY_CONFIG)
    placeholders = ", ".join("?" for _name in setting_names)
    rows = connection.execute(
        "SELECT name, value FROM duckdb_settings() "
        f"WHERE name IN ({placeholders})",
        list(setting_names),
    ).fetchall()
    settings = {str(name): str(value).lower() for name, value in rows}
    require(settings == DENY_CONFIG, "DuckDB deny settings were not locked")
    return settings

def child_command(
    python_fd, bootstrap_fd, mode, site_root, version, database, *extra
):
    command = [
        f"/proc/self/fd/{python_fd}", "-I", "-S", "-B",
        f"/proc/self/fd/{bootstrap_fd}", mode,
        str(site_root), version, str(database),
    ]
    command.extend(str(item) for item in extra)
    return command

def second_writer(site_root, version, database, evidence_path):
    duckdb = load_duckdb(site_root, version)
    connection = None
    stage = "connect"
    try:
        connection = connect(duckdb, database)
        stage = "write"
        connection.execute("INSERT INTO writer_guard VALUES ('independent-writer')")
    except Exception as exc:
        raw_message = str(exc).encode("utf-8", "backslashreplace")
        excerpt = raw_message[:MAX_LOCK_EXCERPT_BYTES].decode(
            "utf-8", "backslashreplace"
        )
        lowered = excerpt.lower()
        marker = next((item for item in LOCK_MARKERS if item in lowered), None)
        exception_module = type(exc).__module__
        expected = (
            type(exc).__name__ in LOCK_EXCEPTION_TYPES
            and exception_module == "_duckdb"
            and marker is not None
            and len(raw_message) <= MAX_LOCK_MESSAGE_BYTES
        )
        evidence = {
            "schema_version": SECOND_WRITER_SCHEMA,
            "import_succeeded": True,
            "connect_attempted": True,
            "connect_succeeded": stage == "write",
            "write_attempted": stage == "write",
            "rejected": expected,
            "rejection_stage": stage,
            "exception_module": exception_module,
            "exception_type": type(exc).__name__,
            "lock_marker": marker,
            "message_sha256": hashlib.sha256(raw_message).hexdigest(),
            "message_bytes": len(raw_message),
            "message_truncated": len(raw_message) > MAX_LOCK_EXCERPT_BYTES,
            "message_excerpt": excerpt,
        }
        write_exclusive_json(evidence_path, evidence)
        return 42 if expected else 43
    finally:
        if connection is not None:
            connection.close()
    return 0

def validate_second_writer_evidence(path):
    evidence = read_bounded_canonical_json(path, 8192)
    expected_keys = {
        "schema_version",
        "import_succeeded",
        "connect_attempted",
        "connect_succeeded",
        "write_attempted",
        "rejected",
        "rejection_stage",
        "exception_module",
        "exception_type",
        "lock_marker",
        "message_sha256",
        "message_bytes",
        "message_truncated",
        "message_excerpt",
    }
    require(set(evidence) == expected_keys, "writer evidence keys differ")
    require(
        evidence["schema_version"] == SECOND_WRITER_SCHEMA,
        "writer evidence schema differs",
    )
    require(evidence["import_succeeded"] is True, "writer import was not proven")
    require(evidence["connect_attempted"] is True, "writer connect was not attempted")
    require(evidence["rejected"] is True, "writer rejection was not classified")
    stage = evidence["rejection_stage"]
    require(stage in {"connect", "write"}, "writer rejection stage is invalid")
    connected = evidence["connect_succeeded"]
    attempted = evidence["write_attempted"]
    require(type(connected) is bool, "writer connected flag is invalid")
    require(type(attempted) is bool, "writer attempted flag is invalid")
    require(
        (stage == "connect" and not connected and not attempted)
        or (stage == "write" and connected and attempted),
        "writer stage flags conflict",
    )
    require(
        evidence["exception_type"] in LOCK_EXCEPTION_TYPES,
        "writer exception class is not a DuckDB lock class",
    )
    module = evidence["exception_module"]
    require(
        isinstance(module, str) and module == "_duckdb",
        "writer exception did not originate in DuckDB",
    )
    marker = evidence["lock_marker"]
    require(marker in LOCK_MARKERS, "writer error lacks an approved lock marker")
    excerpt = evidence["message_excerpt"]
    require(
        isinstance(excerpt, str)
        and len(excerpt.encode("utf-8")) <= MAX_LOCK_EXCERPT_BYTES * 2
        and marker in excerpt.lower(),
        "writer message excerpt does not prove a lock conflict",
    )
    digest = evidence["message_sha256"]
    require(
        isinstance(digest, str)
        and len(digest) == 64
        and all(character in "0123456789abcdef" for character in digest),
        "writer message digest is invalid",
    )
    message_bytes = evidence["message_bytes"]
    require(
        type(message_bytes) is int and 0 < message_bytes <= MAX_LOCK_MESSAGE_BYTES,
        "writer message byte count is invalid",
    )
    require(
        type(evidence["message_truncated"]) is bool,
        "writer message truncation flag is invalid",
    )
    return {
        key: value
        for key, value in evidence.items()
        if key != "message_excerpt"
    }

def crash_writer(site_root, version, database):
    duckdb = load_duckdb(site_root, version)
    connection = connect(duckdb, database)
    connection.execute("BEGIN TRANSACTION")
    connection.execute(
        "INSERT INTO crash_probe VALUES ('must-not-survive-uncommitted-crash')"
    )
    os._exit(23)

def run_smoke(args):
    site_root = Path(args[0])
    work_root = Path(args[1])
    result_path = Path(args[2])
    expected_python_version = args[3]
    expected_version = args[4]
    expected_python_tag = args[5]
    expected_platform_tag = args[6]
    python_fd = int(args[7])
    bootstrap_fd = int(args[8])
    require(".".join(str(item) for item in sys.version_info[:3]) == expected_python_version,
            "Python version mismatch")
    require(sys.implementation.cache_tag == "cpython-" + expected_python_tag[2:],
            "Python implementation tag mismatch")
    machine = os.uname().machine.lower()
    require(expected_platform_tag.lower().endswith("_" + machine),
            "wheel platform architecture mismatch")
    duckdb = load_duckdb(site_root, expected_version)

    checks = {name: False for name in CHECKS}
    smoke_root = work_root / "smoke"
    database = smoke_root / "world-aid.duckdb"
    wal = smoke_root / "world-aid.duckdb.wal"
    temporary = smoke_root / "tmp"
    backup = smoke_root / "world-aid.raw.backup"
    restored = smoke_root / "restored.duckdb"
    corrupted = smoke_root / "corrupted.duckdb"
    extension_root = smoke_root / "extensions"
    opaque_payload = bytes(range(256)) + b"\x00world-aid-opaque\xff"
    connection = None
    settings = {}
    loaded = []
    cleanup = {}
    second_writer_evidence = None
    smoke_root.mkdir(mode=0o700)
    temporary.mkdir(mode=0o700)
    try:
        checks["empty_isolated_environment"] = True
        checks["hash_required_read_only_wheelhouse_install"] = True
        checks["index_extension_registry_dns_http_denied"] = True
        checks["local_filesystem_database"] = True
        loaded = audit_dynamic_extensions(duckdb, extension_root)
        connection = connect(duckdb, database)
        connection.execute(
            "CREATE TABLE aid_state (state_key VARCHAR PRIMARY KEY, "
            "version INTEGER NOT NULL, payload BLOB NOT NULL UNIQUE)"
        )
        connection.execute(
            "CREATE TABLE aid_outbox (event_key VARCHAR PRIMARY KEY, "
            "state_key VARCHAR NOT NULL, payload BLOB NOT NULL)"
        )
        connection.execute("CREATE TABLE writer_guard (writer_id VARCHAR PRIMARY KEY)")
        connection.execute("CREATE TABLE crash_probe (value VARCHAR PRIMARY KEY)")

        connection.execute("BEGIN TRANSACTION")
        connection.execute(
            "INSERT INTO aid_state VALUES (?, 0, ?)",
            ["commit-probe", opaque_payload],
        )
        connection.execute("COMMIT")
        require(
            connection.execute(
                "SELECT version FROM aid_state WHERE state_key='commit-probe'"
            ).fetchone() == (0,),
            "committed row missing",
        )
        checks["transaction_commit"] = True
        require(
            connection.execute(
                "SELECT payload FROM aid_state WHERE state_key='commit-probe'"
            ).fetchone() == (opaque_payload,),
            "opaque payload mismatch",
        )
        checks["opaque_synthetic_payload_round_trip"] = True

        connection.execute("BEGIN TRANSACTION")
        connection.execute(
            "INSERT INTO aid_state VALUES ('rollback-probe', 0, ?)", [b"rollback"]
        )
        connection.execute("ROLLBACK")
        require(
            connection.execute(
                "SELECT count(*) FROM aid_state WHERE state_key='rollback-probe'"
            ).fetchone() == (0,),
            "rollback row survived",
        )
        checks["rollback"] = True

        try:
            connection.execute(
                "INSERT INTO aid_state VALUES ('commit-probe', 0, ?)",
                [b"unique-conflict"],
            )
        except BaseException:
            checks["uniqueness"] = True
        require(checks["uniqueness"], "uniqueness conflict accepted")

        connection.execute(
            "UPDATE aid_state SET version=1 "
            "WHERE state_key='commit-probe' AND version=0"
        )
        connection.execute(
            "UPDATE aid_state SET version=2 "
            "WHERE state_key='commit-probe' AND version=0"
        )
        require(
            connection.execute(
                "SELECT version FROM aid_state WHERE state_key='commit-probe'"
            ).fetchone() == (1,),
            "compare-and-swap failed",
        )
        checks["compare_and_swap"] = True

        connection.execute("BEGIN TRANSACTION")
        connection.execute(
            "INSERT INTO aid_state VALUES ('outbox-probe', 0, ?)", [b"state"]
        )
        connection.execute(
            "INSERT INTO aid_outbox VALUES ('event-1', 'outbox-probe', ?)",
            [b"event"],
        )
        connection.execute("COMMIT")
        require(
            connection.execute(
                "SELECT "
                "(SELECT count(*) FROM aid_state WHERE state_key='outbox-probe'), "
                "(SELECT count(*) FROM aid_outbox WHERE event_key='event-1')"
            ).fetchone() == (1, 1),
            "state/outbox commit was not atomic",
        )
        checks["atomic_outbox"] = True

        connection.execute("BEGIN TRANSACTION")
        connection.execute(
            "INSERT INTO writer_guard VALUES ('coordinator-holds-transaction')"
        )
        writer_evidence_path = smoke_root / "second-writer-result.json"
        second = subprocess.run(
            child_command(
                python_fd, bootstrap_fd, "second-writer",
                site_root, expected_version, database, writer_evidence_path,
            ),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=dict(os.environ),
            close_fds=True,
            pass_fds=(python_fd, bootstrap_fd),
            timeout=15,
        )
        connection.execute("ROLLBACK")
        require(second.returncode == 42, "independent second writer was not rejected")
        second_writer_evidence = validate_second_writer_evidence(
            writer_evidence_path
        )
        checks["direct_second_writer_rejected"] = True

        connection.execute("CHECKPOINT")
        checks["checkpoint"] = True
        connection.close()
        connection = None
        crash = subprocess.run(
            child_command(
                python_fd, bootstrap_fd, "crash-writer",
                site_root, expected_version, database,
            ),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=dict(os.environ),
            close_fds=True,
            pass_fds=(python_fd, bootstrap_fd),
            timeout=15,
        )
        require(crash.returncode == 23, "crash probe did not terminate as expected")
        connection = connect(duckdb, database)
        require(
            connection.execute(
                "SELECT count(*) FROM crash_probe "
                "WHERE value='must-not-survive-uncommitted-crash'"
            ).fetchone() == (0,),
            "uncommitted crash row survived",
        )
        checks["crash_and_reopen"] = True

        settings = prove_deny_settings_locked(connection)
        checks["extensions_absent_and_deny_settings_locked"] = True
        connection.execute("CHECKPOINT")
        connection.close()
        connection = None

        shutil.copyfile(database, backup)
        backup_digest = hashlib.sha256(backup.read_bytes()).hexdigest()
        shutil.copyfile(backup, restored)
        require(
            hashlib.sha256(restored.read_bytes()).hexdigest() == backup_digest,
            "raw restore digest mismatch",
        )
        restored_connection = connect(duckdb, restored)
        require(
            restored_connection.execute(
                "SELECT payload FROM aid_state WHERE state_key='commit-probe'"
            ).fetchone() == (opaque_payload,),
            "raw restore payload mismatch",
        )
        restored_connection.close()
        checks["raw_opaque_backup_and_restore"] = True

        shutil.copyfile(backup, corrupted)
        with corrupted.open("r+b") as handle:
            handle.truncate(128)
        try:
            corrupt_connection = connect(duckdb, corrupted)
            corrupt_connection.execute("SELECT * FROM aid_state").fetchall()
        except BaseException:
            checks["corruption_detected"] = True
        else:
            corrupt_connection.close()
        require(checks["corruption_detected"], "truncated backup was accepted")
    finally:
        if connection is not None:
            connection.close()
        shutil.rmtree(smoke_root, ignore_errors=False)
        cleanup = {
            "database_exists": database.exists(),
            "wal_exists": wal.exists(),
            "temporary_data_exists": smoke_root.exists() or temporary.exists(),
        }
        checks["database_wal_and_temporary_data_torn_down"] = not any(cleanup.values())

    require(all(checks.values()), "one or more required G040 checks did not pass")
    payload = {
        "schema_version": CHILD_SCHEMA,
        "duckdb_version": expected_version,
        "checks": checks,
        "cleanup": cleanup,
        "settings": settings,
        "loaded_dynamic_extensions": loaded,
        "network_attempts": 0,
        "single_writer_enforced": True,
        "second_writer_evidence": second_writer_evidence,
        "g033_excluded_controls": [
            "application_envelope_encryption",
            "plaintext_marker_absence",
            "encrypted_authenticated_production_backup",
            "key_rotation_retention_and_deletion",
        ],
    }
    write_exclusive_json(result_path, payload)
    return 0

if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "run":
        raise SystemExit(run_smoke(sys.argv[2:]))
    if mode == "second-writer":
        raise SystemExit(
            second_writer(
                Path(sys.argv[2]),
                sys.argv[3],
                Path(sys.argv[4]),
                Path(sys.argv[5]),
            )
        )
    if mode == "crash-writer":
        raise SystemExit(crash_writer(Path(sys.argv[2]), sys.argv[3], Path(sys.argv[4])))
    raise SystemExit(64)
"""


def fixed_smoke_bootstrap_sha256() -> str:
    """Digest of the bootstrap captured into a sealed descriptor at runtime."""

    return "sha256:" + hashlib.sha256(_FIXED_SMOKE_BOOTSTRAP.encode("utf-8")).hexdigest()


def _metadata_snapshot(metadata: os.stat_result) -> tuple[int, ...]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_uid,
        metadata.st_gid,
        metadata.st_nlink,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def _open_directory_without_symlinks(path: Path, context: str) -> int:
    if not path.is_absolute():
        _fail(f"{context} must be absolute")
    flags = os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = -1
    try:
        descriptor = os.open("/", flags)
        for component in path.parts[1:]:
            child = os.open(component, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        return descriptor
    except OSError as exc:
        if descriptor >= 0:
            os.close(descriptor)
        raise G040DuckDBBootstrapError(f"cannot open {context} without following symlinks: {exc}") from exc


def _current_identity_can_write(metadata: os.stat_result) -> bool:
    mode = metadata.st_mode
    if mode & stat.S_IWOTH:
        return True
    if metadata.st_uid == os.geteuid() and mode & stat.S_IWUSR:
        return True
    groups = {os.getegid(), *os.getgroups()}
    return metadata.st_gid in groups and bool(mode & stat.S_IWGRP)


def _hash_open_file(descriptor: int, maximum_bytes: int) -> str:
    metadata = os.fstat(descriptor)
    if metadata.st_size <= 0 or metadata.st_size > maximum_bytes:
        _fail(f"pinned file size must be 1..{maximum_bytes} bytes")
    digest = hashlib.sha256()
    offset = 0
    while offset < metadata.st_size:
        chunk = os.pread(
            descriptor,
            min(_READ_CHUNK, metadata.st_size - offset),
            offset,
        )
        if not chunk:
            _fail("pinned file ended before its approved size")
        digest.update(chunk)
        offset += len(chunk)
    if _metadata_snapshot(os.fstat(descriptor)) != _metadata_snapshot(metadata):
        _fail("pinned file changed while being hashed")
    return "sha256:" + digest.hexdigest()


def _open_pinned_file(
    *,
    role: str,
    path: Path,
    expected_sha256: str,
    expected_size: int,
    maximum_bytes: int,
    executable: bool = False,
) -> _PinnedFile:
    parent = _open_directory_without_symlinks(path.parent, f"{role} parent")
    descriptor = -1
    try:
        descriptor = os.open(
            path.name,
            os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0),
            dir_fd=parent,
        )
    except OSError as exc:
        raise G040DuckDBBootstrapError(f"cannot open {role} without following symlinks: {exc}") from exc
    finally:
        os.close(parent)
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            _fail(f"{role} must be a regular file")
        if metadata.st_size != expected_size or expected_size > maximum_bytes:
            _fail(f"{role} size differs from the immutable plan")
        if metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
            _fail(f"{role} must not be group- or world-writable")
        if _current_identity_can_write(metadata):
            _fail(f"{role} must be mode-immutable to the effective caller")
        if executable and not metadata.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH):
            _fail(f"{role} must have an executable mode bit")
        observed_sha256 = _hash_open_file(descriptor, maximum_bytes)
        if observed_sha256 != expected_sha256:
            _fail(f"{role} digest differs from the immutable plan")
        return _PinnedFile(
            role=role,
            path=path,
            sha256=observed_sha256,
            size=metadata.st_size,
            descriptor=descriptor,
            metadata=_metadata_snapshot(metadata),
        )
    except BaseException:
        os.close(descriptor)
        raise


def _revalidate_pinned_file(item: _PinnedFile, maximum_bytes: int) -> None:
    if _metadata_snapshot(os.fstat(item.descriptor)) != item.metadata:
        _fail(f"{item.role} descriptor metadata drifted")
    if _hash_open_file(item.descriptor, maximum_bytes) != item.sha256:
        _fail(f"{item.role} descriptor digest drifted")
    parent = _open_directory_without_symlinks(item.path.parent, f"{item.role} parent")
    reopened = -1
    try:
        reopened = os.open(
            item.path.name,
            os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0),
            dir_fd=parent,
        )
        if _metadata_snapshot(os.fstat(reopened)) != item.metadata:
            _fail(f"{item.role} path no longer identifies its pinned descriptor")
        if _hash_open_file(reopened, maximum_bytes) != item.sha256:
            _fail(f"{item.role} path digest drifted")
    except OSError as exc:
        raise G040DuckDBBootstrapError(f"cannot revalidate {item.role} without following symlinks: {exc}") from exc
    finally:
        if reopened >= 0:
            os.close(reopened)
        os.close(parent)


def _plan_artifacts(plan: DuckDBBootstrapPlan) -> tuple[tuple[str, DuckDBBoundArtifact], ...]:
    return tuple((role, getattr(plan, role)) for role in _REQUIRED_INPUT_ROLES)


def _open_plan_files(plan: DuckDBBootstrapPlan) -> tuple[_PinnedFile, ...]:
    paths = [
        plan.python_path,
        plan.wheel_path,
        *(artifact.source_path for _, artifact in _plan_artifacts(plan)),
    ]
    if len(paths) != len(set(paths)):
        _fail("all plan-bound source paths must be distinct")
    opened: list[_PinnedFile] = []
    try:
        opened.append(
            _open_pinned_file(
                role="isolated Python executable",
                path=plan.python_path,
                expected_sha256=plan.python_sha256,
                expected_size=plan.python_size,
                maximum_bytes=_MAX_PYTHON_BYTES,
                executable=True,
            )
        )
        opened.append(
            _open_pinned_file(
                role="DuckDB wheel",
                path=plan.wheel_path,
                expected_sha256=plan.wheel_sha256,
                expected_size=plan.wheel_size,
                maximum_bytes=_MAX_WHEEL_BYTES,
            )
        )
        for role, artifact in _plan_artifacts(plan):
            opened.append(
                _open_pinned_file(
                    role=role,
                    path=artifact.source_path,
                    expected_sha256=artifact.sha256,
                    expected_size=artifact.size,
                    maximum_bytes=_MAX_BOUND_ARTIFACT_BYTES,
                )
            )
        return tuple(opened)
    except BaseException:
        for item in opened:
            os.close(item.descriptor)
        raise


def _maximum_for_role(item: _PinnedFile) -> int:
    if item.role == "isolated Python executable":
        return _MAX_PYTHON_BYTES
    if item.role == "DuckDB wheel":
        return _MAX_WHEEL_BYTES
    return _MAX_BOUND_ARTIFACT_BYTES


def _revalidate_plan_files(items: tuple[_PinnedFile, ...]) -> None:
    for item in items:
        _revalidate_pinned_file(item, _maximum_for_role(item))


def _new_sealed_memfd(name: str, raw: bytes) -> int:
    flags = getattr(os, "MFD_ALLOW_SEALING", 0x0002) | getattr(os, "MFD_CLOEXEC", 0x0001)
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
            raise G040DuckDBBootstrapError(f"sealed Linux memfds are required: {exc}") from exc
        if descriptor < 0:
            error_number = ctypes.get_errno()
            raise OSError(error_number, os.strerror(error_number))
    try:
        offset = 0
        while offset < len(raw):
            offset += os.write(descriptor, raw[offset:])
        os.fchmod(descriptor, 0o400)
        required_seals = (
            getattr(fcntl, "F_SEAL_SEAL", 0x0001)
            | getattr(fcntl, "F_SEAL_SHRINK", 0x0002)
            | getattr(fcntl, "F_SEAL_GROW", 0x0004)
            | getattr(fcntl, "F_SEAL_WRITE", 0x0008)
        )
        fcntl.fcntl(
            descriptor,
            getattr(fcntl, "F_ADD_SEALS", 1033),
            required_seals,
        )
        observed = int(fcntl.fcntl(descriptor, getattr(fcntl, "F_GET_SEALS", 1034)))
        if observed & required_seals != required_seals:
            _fail("smoke bootstrap memfd did not acquire every required seal")
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _zip_member_path(info: zipfile.ZipInfo) -> PurePosixPath:
    name = info.filename
    if (
        not name
        or len(name.encode("utf-8")) > _MAX_PATH_BYTES
        or "\x00" in name
        or "\\" in name
        or name.startswith("/")
        or "//" in name
    ):
        _fail(f"wheel contains an unsafe member path: {name!r}")
    normalized_text = name[:-1] if info.is_dir() and name.endswith("/") else name
    path = PurePosixPath(normalized_text)
    if (
        not path.parts
        or path.is_absolute()
        or path.as_posix() != normalized_text
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        _fail(f"wheel member path is not normalized: {name!r}")
    lowered_parts = tuple(part.lower() for part in path.parts)
    if (
        path.name.endswith(".pth")
        or path.name in {"sitecustomize.py", "usercustomize.py"}
        or "__pycache__" in lowered_parts
        or any(part.endswith(".pyc") for part in lowered_parts)
        or (len(lowered_parts) >= 2 and lowered_parts[0].endswith(".data") and lowered_parts[1] == "scripts")
    ):
        _fail(f"wheel contains executable site/lifecycle content: {name!r}")
    return path


def _validate_zip_type(info: zipfile.ZipInfo) -> None:
    mode = (info.external_attr >> 16) & 0xFFFF
    file_type = stat.S_IFMT(mode)
    if info.is_dir():
        if file_type not in {0, stat.S_IFDIR}:
            _fail(f"wheel directory has a special file type: {info.filename!r}")
    elif file_type not in {0, stat.S_IFREG}:
        _fail(f"wheel contains a symlink or special file: {info.filename!r}")
    if info.flag_bits & 0x1:
        _fail(f"wheel contains an encrypted member: {info.filename!r}")
    if info.compress_type not in _ALLOWED_COMPRESSION:
        _fail(f"wheel uses an unsupported compression type: {info.filename!r}")


def _read_zip_entry(
    archive: zipfile.ZipFile,
    info: zipfile.ZipInfo,
    *,
    maximum_bytes: int,
) -> bytes:
    if info.file_size > maximum_bytes:
        _fail(f"wheel member exceeds its byte bound: {info.filename!r}")
    chunks: list[bytes] = []
    observed = 0
    with archive.open(info, "r") as source:
        while True:
            chunk = source.read(_READ_CHUNK)
            if not chunk:
                break
            observed += len(chunk)
            if observed > maximum_bytes or observed > info.file_size:
                _fail(f"wheel member expanded beyond its declared size: {info.filename!r}")
            chunks.append(chunk)
    if observed != info.file_size:
        _fail(f"wheel member size differs from the central directory: {info.filename!r}")
    return b"".join(chunks)


def _record_hash(encoded: str, context: str) -> bytes:
    if not encoded.startswith("sha256="):
        _fail(f"{context} must use a sha256 RECORD hash")
    value = encoded.removeprefix("sha256=")
    try:
        decoded = base64.b64decode(
            value + ("=" * ((4 - len(value) % 4) % 4)),
            altchars=b"-_",
            validate=True,
        )
    except (ValueError, binascii.Error) as exc:
        raise G040DuckDBBootstrapError(f"{context} is not valid URL-safe base64: {exc}") from exc
    if len(decoded) != hashlib.sha256().digest_size:
        _fail(f"{context} is not a SHA-256 digest")
    return decoded


def _parse_record(
    raw: bytes,
    *,
    record_path: str,
    files: dict[str, zipfile.ZipInfo],
) -> dict[str, tuple[bytes | None, int | None]]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise G040DuckDBBootstrapError(f"wheel RECORD is not UTF-8: {exc}") from exc
    records: dict[str, tuple[bytes | None, int | None]] = {}
    try:
        rows = csv.reader(io.StringIO(text, newline=""))
        for index, row in enumerate(rows):
            if len(row) != 3:
                _fail(f"wheel RECORD row {index} must contain exactly three fields")
            path_text, hash_text, size_text = row
            synthetic = zipfile.ZipInfo(path_text)
            normalized = _zip_member_path(synthetic).as_posix()
            if normalized != path_text or normalized in records:
                _fail("wheel RECORD contains a non-normalized or duplicate path")
            if normalized == record_path:
                if hash_text or size_text:
                    _fail("wheel RECORD must leave its own hash and size empty")
                records[normalized] = (None, None)
                continue
            if not hash_text or not size_text or not size_text.isdecimal():
                _fail(f"wheel RECORD entry is incomplete: {normalized!r}")
            records[normalized] = (
                _record_hash(hash_text, f"RECORD hash for {normalized!r}"),
                int(size_text),
            )
    except csv.Error as exc:
        raise G040DuckDBBootstrapError(f"wheel RECORD is invalid CSV: {exc}") from exc
    if set(records) != set(files):
        missing = sorted(set(files) - set(records))
        extra = sorted(set(records) - set(files))
        _fail(f"wheel RECORD/file set differs: missing={missing}, extra={extra}")
    if record_path not in records:
        _fail("wheel RECORD does not describe itself")
    return records


def _open_or_create_directory(root_fd: int, parts: tuple[str, ...]) -> int:
    descriptor = os.dup(root_fd)
    flags = os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        for part in parts:
            try:
                os.mkdir(part, 0o700, dir_fd=descriptor)
            except FileExistsError:
                pass
            child = os.open(part, flags, dir_fd=descriptor)
            if not stat.S_ISDIR(os.fstat(child).st_mode):
                os.close(child)
                _fail("wheel extraction destination component is not a directory")
            os.close(descriptor)
            descriptor = child
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _extract_entry(
    archive: zipfile.ZipFile,
    info: zipfile.ZipInfo,
    path: PurePosixPath,
    root_fd: int,
    expected_hash: bytes | None,
    expected_size: int | None,
    bounds: DuckDBResourceBounds,
) -> None:
    if info.is_dir():
        directory = _open_or_create_directory(root_fd, tuple(path.parts))
        os.close(directory)
        return
    parent = _open_or_create_directory(root_fd, tuple(path.parts[:-1]))
    destination = -1
    digest = hashlib.sha256()
    observed = 0
    try:
        destination = os.open(
            path.name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0),
            0o600,
            dir_fd=parent,
        )
        with archive.open(info, "r") as source:
            while True:
                chunk = source.read(_READ_CHUNK)
                if not chunk:
                    break
                observed += len(chunk)
                if observed > info.file_size or observed > bounds.max_entry_bytes:
                    _fail(f"wheel member exceeded its extraction bound: {info.filename!r}")
                digest.update(chunk)
                offset = 0
                while offset < len(chunk):
                    offset += os.write(destination, chunk[offset:])
        if observed != info.file_size or expected_size != observed:
            _fail(f"wheel member size differs from RECORD: {info.filename!r}")
        if expected_hash is None or digest.digest() != expected_hash:
            _fail(f"wheel member digest differs from RECORD: {info.filename!r}")
        os.fchmod(destination, 0o400)
        os.fsync(destination)
    finally:
        if destination >= 0:
            os.close(destination)
        os.close(parent)


def _validate_and_extract_wheel(
    *,
    plan: DuckDBBootstrapPlan,
    wheel: _PinnedFile,
    site_root: Path,
    deadline: float,
) -> _WheelEvidence:
    duplicate = os.dup(wheel.descriptor)
    os.lseek(duplicate, 0, os.SEEK_SET)
    file_object = os.fdopen(duplicate, "rb", closefd=True)
    try:
        with zipfile.ZipFile(file_object, "r") as archive:
            infos = archive.infolist()
            if not 4 <= len(infos) <= plan.resource_bounds.max_wheel_entries:
                _fail("wheel entry count is outside the authenticated bound")
            entries: dict[str, tuple[zipfile.ZipInfo, PurePosixPath]] = {}
            files: dict[str, zipfile.ZipInfo] = {}
            total_uncompressed = 0
            for info in infos:
                _require_deadline(deadline, plan.resource_bounds)
                path = _zip_member_path(info)
                normalized = path.as_posix()
                if normalized in entries:
                    _fail(f"wheel contains a duplicate path: {normalized!r}")
                _validate_zip_type(info)
                if info.file_size < 0 or info.file_size > plan.resource_bounds.max_entry_bytes:
                    _fail(f"wheel member size is outside its bound: {normalized!r}")
                total_uncompressed += info.file_size
                if total_uncompressed > plan.resource_bounds.max_uncompressed_bytes:
                    _fail("wheel uncompressed size exceeds the authenticated bound")
                entries[normalized] = (info, path)
                if not info.is_dir():
                    files[normalized] = info

            dist_info = f"duckdb-{plan.duckdb_version}.dist-info"
            metadata_path = f"{dist_info}/METADATA"
            wheel_metadata_path = f"{dist_info}/WHEEL"
            record_path = f"{dist_info}/RECORD"
            for required in (metadata_path, wheel_metadata_path, record_path):
                if required not in files:
                    _fail(f"wheel is missing required metadata: {required}")

            metadata_raw = _read_zip_entry(
                archive,
                files[metadata_path],
                maximum_bytes=min(plan.resource_bounds.max_entry_bytes, 8 * 1024 * 1024),
            )
            message = BytesParser(policy=email.policy.compat32).parsebytes(metadata_raw)
            names = message.get_all("Name", [])
            versions = message.get_all("Version", [])
            if names != ["duckdb"] or versions != [plan.duckdb_version]:
                _fail("wheel METADATA name/version differs from the plan")

            wheel_raw = _read_zip_entry(
                archive,
                files[wheel_metadata_path],
                maximum_bytes=min(plan.resource_bounds.max_entry_bytes, 1024 * 1024),
            )
            try:
                wheel_text = wheel_raw.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise G040DuckDBBootstrapError(f"wheel WHEEL metadata is not UTF-8: {exc}") from exc
            expected_tag = f"{plan.python_tag}-{plan.abi_tag}-{plan.platform_tag}"
            expanded_tags = {
                f"{plan.python_tag}-{plan.abi_tag}-{platform}" for platform in plan.platform_tag.split(".")
            }
            tags = [line.removeprefix("Tag:").strip() for line in wheel_text.splitlines() if line.startswith("Tag:")]
            if len(tags) != len(set(tags)) or set(tags) != expanded_tags:
                _fail("wheel WHEEL tags differ from the selected ABI/platform set")

            record_raw = _read_zip_entry(
                archive,
                files[record_path],
                maximum_bytes=min(plan.resource_bounds.max_entry_bytes, 32 * 1024 * 1024),
            )
            records = _parse_record(
                record_raw,
                record_path=record_path,
                files=files,
            )
            root_fd = _open_directory_without_symlinks(site_root, "isolated site root")
            try:
                for normalized, (info, path) in entries.items():
                    _require_deadline(deadline, plan.resource_bounds)
                    if info.is_dir():
                        _extract_entry(
                            archive,
                            info,
                            path,
                            root_fd,
                            None,
                            None,
                            plan.resource_bounds,
                        )
                    else:
                        expected_hash, expected_size = records[normalized]
                        if normalized == record_path:
                            # RECORD is authenticated by the wheel digest and
                            # parsed structurally; by definition it cannot
                            # contain its own digest.
                            expected_hash = hashlib.sha256(record_raw).digest()
                            expected_size = len(record_raw)
                        _extract_entry(
                            archive,
                            info,
                            path,
                            root_fd,
                            expected_hash,
                            expected_size,
                            plan.resource_bounds,
                        )
                os.fsync(root_fd)
            finally:
                os.close(root_fd)
            return _WheelEvidence(
                entry_count=len(entries),
                file_count=len(files),
                uncompressed_bytes=total_uncompressed,
                record_count=len(records),
                metadata_name=names[0],
                metadata_version=versions[0],
                wheel_tag=expected_tag,
            )
    except (OSError, zipfile.BadZipFile, zipfile.LargeZipFile) as exc:
        raise G040DuckDBBootstrapError(f"DuckDB wheel validation failed: {exc}") from exc


def _bounded_rlimit(kind: int, requested: int) -> tuple[int, int]:
    _, hard = resource.getrlimit(kind)
    effective = requested if hard == resource.RLIM_INFINITY else min(requested, hard)
    return effective, effective


def _resource_limiter(bounds: DuckDBResourceBounds):
    def apply_limits() -> None:
        os.umask(0o077)
        memory_bytes = bounds.max_memory_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        resource.setrlimit(
            resource.RLIMIT_CPU,
            _bounded_rlimit(resource.RLIMIT_CPU, bounds.max_seconds),
        )
        resource.setrlimit(
            resource.RLIMIT_AS,
            _bounded_rlimit(resource.RLIMIT_AS, memory_bytes),
        )
        resource.setrlimit(
            resource.RLIMIT_FSIZE,
            _bounded_rlimit(resource.RLIMIT_FSIZE, bounds.max_file_bytes),
        )
        resource.setrlimit(
            resource.RLIMIT_NOFILE,
            _bounded_rlimit(resource.RLIMIT_NOFILE, _FIXED_NOFILE_LIMIT),
        )

    return apply_limits


def _terminate_process_group(process: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        try:
            process.wait(timeout=0)
        except subprocess.TimeoutExpired:
            pass
        return
    try:
        process.wait(timeout=0.1)
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        _fail("unable to reap the bounded DuckDB process group")


def _child_environment(workspace: Path) -> dict[str, str]:
    environment = dict(_CLEAN_ENVIRONMENT)
    home = workspace / "home"
    temporary = workspace / "tmp"
    home.mkdir(mode=0o700)
    temporary.mkdir(mode=0o700)
    environment["HOME"] = os.fspath(home)
    environment["TMPDIR"] = os.fspath(temporary)
    return environment


def _run_smoke_child(
    *,
    plan: DuckDBBootstrapPlan,
    python: _PinnedFile,
    bootstrap_fd: int,
    workspace: Path,
    site_root: Path,
    result_path: Path,
    deadline: float,
) -> _CommandEvidence:
    command = (
        f"/proc/self/fd/{python.descriptor}",
        "-I",
        "-S",
        "-B",
        f"/proc/self/fd/{bootstrap_fd}",
        "run",
        os.fspath(site_root),
        os.fspath(workspace),
        os.fspath(result_path),
        plan.python_version,
        plan.duckdb_version,
        plan.python_tag,
        plan.platform_tag,
        str(python.descriptor),
        str(bootstrap_fd),
    )
    started = time.monotonic()
    if started >= deadline:
        _fail("DuckDB smoke child cannot start after the execution deadline")
    try:
        process = subprocess.Popen(
            command,
            cwd=workspace,
            env=_child_environment(workspace),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            close_fds=True,
            pass_fds=(python.descriptor, bootstrap_fd),
            start_new_session=True,
            preexec_fn=_resource_limiter(plan.resource_bounds),
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise G040DuckDBBootstrapError(f"DuckDB smoke child could not start: {exc}") from exc

    if process.stdout is None or process.stderr is None:
        _terminate_process_group(process)
        _fail("DuckDB smoke child output pipes were not created")
    streams = {
        process.stdout: (hashlib.sha256(), 0),
        process.stderr: (hashlib.sha256(), 0),
    }
    selector = selectors.DefaultSelector()
    for stream in streams:
        os.set_blocking(stream.fileno(), False)
        selector.register(stream, selectors.EVENT_READ)
    failure: G040DuckDBBootstrapError | None = None
    return_code: int | None = None
    try:
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                failure = G040DuckDBBootstrapError(
                    f"DuckDB smoke child exceeded the {plan.resource_bounds.max_seconds}-second bound"
                )
                break
            events = selector.select(min(remaining, 0.1))
            if not events and process.poll() is not None:
                events = [(key, selectors.EVENT_READ) for key in selector.get_map().values()]
            for key, _mask in events:
                stream = key.fileobj
                try:
                    chunk = os.read(stream.fileno(), _READ_CHUNK)
                except BlockingIOError:
                    continue
                if not chunk:
                    selector.unregister(stream)
                    continue
                digest, size = streams[stream]
                digest.update(chunk)
                streams[stream] = (digest, size + len(chunk))
                if sum(item[1] for item in streams.values()) > plan.resource_bounds.max_output_bytes:
                    failure = G040DuckDBBootstrapError("DuckDB smoke child exceeded the aggregate output bound")
                    break
            if failure is not None:
                break
        if failure is None:
            try:
                return_code = process.wait(timeout=max(0.0, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                failure = G040DuckDBBootstrapError(
                    f"DuckDB smoke child exceeded the {plan.resource_bounds.max_seconds}-second bound"
                )
            else:
                if return_code != 0:
                    stderr_digest, stderr_size = streams[process.stderr]
                    failure = G040DuckDBBootstrapError(
                        "DuckDB smoke child failed with exit code "
                        f"{return_code} (stderr_bytes={stderr_size}, "
                        f"stderr_sha256=sha256:{stderr_digest.hexdigest()})"
                    )
    finally:
        selector.close()
        for stream in streams:
            stream.close()
        _terminate_process_group(process)
    if failure is not None:
        raise failure
    stdout_digest, stdout_size = streams[process.stdout]
    stderr_digest, stderr_size = streams[process.stderr]
    return _CommandEvidence(
        exit_code=int(return_code),
        elapsed_ms=max(0, math.ceil((time.monotonic() - started) * 1000)),
        stdout_sha256="sha256:" + stdout_digest.hexdigest(),
        stdout_bytes=stdout_size,
        stderr_sha256="sha256:" + stderr_digest.hexdigest(),
        stderr_bytes=stderr_size,
    )


def _open_relative_regular_file(
    root: Path,
    relative: str,
    *,
    maximum_bytes: int,
    context: str,
) -> int:
    path = PurePosixPath(relative)
    if path.is_absolute() or path.as_posix() != relative or any(part in {"", ".", ".."} for part in path.parts):
        _fail(f"{context} path is not a normalized relative path")
    descriptor = _open_directory_without_symlinks(root, f"{context} root")
    root_descriptor = descriptor
    try:
        for part in path.parts[:-1]:
            child = os.open(
                part,
                os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=descriptor,
            )
            if descriptor != root_descriptor:
                os.close(descriptor)
            descriptor = child
        file_descriptor = os.open(
            path.name,
            os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0),
            dir_fd=descriptor,
        )
        metadata = os.fstat(file_descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size <= 0 or metadata.st_size > maximum_bytes:
            os.close(file_descriptor)
            _fail(f"{context} is not a bounded regular file")
        return file_descriptor
    except OSError as exc:
        raise G040DuckDBBootstrapError(f"cannot open {context} without following symlinks: {exc}") from exc
    finally:
        if descriptor != root_descriptor:
            os.close(descriptor)
        os.close(root_descriptor)


def _read_fd(descriptor: int, maximum_bytes: int, context: str) -> bytes:
    metadata = os.fstat(descriptor)
    if metadata.st_size <= 0 or metadata.st_size > maximum_bytes:
        _fail(f"{context} exceeds its byte bound")
    chunks: list[bytes] = []
    offset = 0
    while offset < metadata.st_size:
        chunk = os.pread(
            descriptor,
            min(_READ_CHUNK, metadata.st_size - offset),
            offset,
        )
        if not chunk:
            _fail(f"{context} ended early")
        chunks.append(chunk)
        offset += len(chunk)
    return b"".join(chunks)


def _strict_json_bytes(raw: bytes, context: str) -> dict[str, object]:
    def reject_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                _fail(f"{context} contains duplicate JSON key {key!r}")
            result[key] = value
        return result

    try:
        payload = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=reject_duplicates,
            parse_constant=lambda value: _fail(f"{context} contains non-finite number {value}"),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise G040DuckDBBootstrapError(f"{context} is not strict JSON: {exc}") from exc
    if not isinstance(payload, dict):
        _fail(f"{context} must contain a JSON object")
    if _canonical_json_bytes(payload) != raw:
        _fail(f"{context} is not canonical JSON")
    return payload


def _exact_keys(value: dict[str, object], expected: set[str], context: str) -> None:
    observed = set(value)
    if observed != expected:
        _fail(f"{context} keys differ: missing={sorted(expected - observed)}, unexpected={sorted(observed - expected)}")


def _validate_child_result(
    payload: dict[str, object],
    plan: DuckDBBootstrapPlan,
) -> None:
    _exact_keys(
        payload,
        {
            "schema_version",
            "duckdb_version",
            "checks",
            "cleanup",
            "settings",
            "loaded_dynamic_extensions",
            "network_attempts",
            "single_writer_enforced",
            "second_writer_evidence",
            "g033_excluded_controls",
        },
        "DuckDB child result",
    )
    if payload["schema_version"] != CHILD_RESULT_SCHEMA:
        _fail("DuckDB child result schema is invalid")
    if payload["duckdb_version"] != plan.duckdb_version:
        _fail("DuckDB child result version differs from the plan")
    checks = payload["checks"]
    if not isinstance(checks, dict) or set(checks) != set(REQUIRED_G040_CHECKS):
        _fail("DuckDB child result check set is invalid")
    if any(checks[name] is not True for name in REQUIRED_G040_CHECKS):
        _fail("DuckDB child result contains a failed smoke check")
    cleanup = payload["cleanup"]
    if cleanup != {
        "database_exists": False,
        "temporary_data_exists": False,
        "wal_exists": False,
    }:
        _fail("DuckDB child result does not prove database/WAL/temp teardown")
    expected_settings = {
        "allow_community_extensions": "false",
        "autoinstall_known_extensions": "false",
        "autoload_known_extensions": "false",
        "enable_external_access": "false",
        "lock_configuration": "true",
    }
    if payload["settings"] != expected_settings:
        _fail("DuckDB child result does not prove exact deny settings")
    if payload["loaded_dynamic_extensions"] != []:
        _fail("DuckDB child result reports a dynamically loaded extension")
    if payload["network_attempts"] != 0 or isinstance(payload["network_attempts"], bool):
        _fail("DuckDB child result reports a network attempt")
    if payload["single_writer_enforced"] is not True:
        _fail("DuckDB child result does not prove single-writer enforcement")
    writer_evidence = payload["second_writer_evidence"]
    if not isinstance(writer_evidence, dict):
        _fail("DuckDB child result lacks structured second-writer evidence")
    _exact_keys(
        writer_evidence,
        {
            "schema_version",
            "import_succeeded",
            "connect_attempted",
            "connect_succeeded",
            "write_attempted",
            "rejected",
            "rejection_stage",
            "exception_module",
            "exception_type",
            "lock_marker",
            "message_sha256",
            "message_bytes",
            "message_truncated",
        },
        "DuckDB second-writer evidence",
    )
    if writer_evidence["schema_version"] != ("world-human-aid-g040-second-writer/v1"):
        _fail("DuckDB second-writer evidence schema is invalid")
    if (
        writer_evidence["import_succeeded"] is not True
        or writer_evidence["connect_attempted"] is not True
        or writer_evidence["rejected"] is not True
    ):
        _fail("DuckDB second-writer evidence did not reach the lock boundary")
    stage = writer_evidence["rejection_stage"]
    connected = writer_evidence["connect_succeeded"]
    write_attempted = writer_evidence["write_attempted"]
    if (
        not isinstance(connected, bool)
        or not isinstance(write_attempted, bool)
        or not (
            stage == "connect"
            and not connected
            and not write_attempted
            or stage == "write"
            and connected
            and write_attempted
        )
    ):
        _fail("DuckDB second-writer evidence has inconsistent stage flags")
    if writer_evidence["exception_type"] != "IOException":
        _fail("DuckDB second-writer evidence has a non-lock exception class")
    exception_module = writer_evidence["exception_module"]
    if exception_module != "_duckdb":
        _fail("DuckDB second-writer evidence exception is not from DuckDB")
    if writer_evidence["lock_marker"] not in {
        "could not set lock",
        "conflicting lock",
        "database is locked",
        "lock on file",
        "cannot acquire lock",
        "failed to acquire lock",
    }:
        _fail("DuckDB second-writer evidence lacks a lock/conflict marker")
    message_sha256 = writer_evidence["message_sha256"]
    if not isinstance(message_sha256, str) or re.fullmatch(r"[0-9a-f]{64}", message_sha256) is None:
        _fail("DuckDB second-writer message digest is invalid")
    message_bytes = writer_evidence["message_bytes"]
    if (
        isinstance(message_bytes, bool)
        or not isinstance(message_bytes, int)
        or not 0 < message_bytes <= 4096
        or not isinstance(writer_evidence["message_truncated"], bool)
    ):
        _fail("DuckDB second-writer message bounds are invalid")
    if payload["g033_excluded_controls"] != list(G033_EXCLUDED_CONTROLS):
        _fail("DuckDB child result misstates excluded G033 controls")


def _validate_workspace_tree(root: Path, maximum_bytes: int) -> int:
    total = 0
    stack = [root]
    while stack:
        directory = stack.pop()
        with os.scandir(directory) as entries:
            for entry in entries:
                metadata = entry.stat(follow_symlinks=False)
                if stat.S_ISLNK(metadata.st_mode):
                    _fail("DuckDB workspace contains a symlink")
                if stat.S_ISDIR(metadata.st_mode):
                    stack.append(Path(entry.path))
                elif stat.S_ISREG(metadata.st_mode):
                    total += metadata.st_size
                    if total > maximum_bytes:
                        _fail("DuckDB workspace exceeds the aggregate byte bound")
                else:
                    _fail("DuckDB workspace contains a special file")
    return total


def _validate_run_directory(plan: DuckDBBootstrapPlan) -> tuple[int, tuple[int, ...]]:
    descriptor = _open_directory_without_symlinks(plan.run_directory, "external run_directory")
    metadata = os.fstat(descriptor)
    if metadata.st_uid != os.geteuid():
        os.close(descriptor)
        _fail("run_directory must be owned by the effective caller")
    if metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
        os.close(descriptor)
        _fail("run_directory must not be group- or world-writable")
    try:
        os.stat(RECEIPT_NAME, dir_fd=descriptor, follow_symlinks=False)
    except FileNotFoundError:
        pass
    except OSError as exc:
        os.close(descriptor)
        raise G040DuckDBBootstrapError(f"cannot inspect receipt destination: {exc}") from exc
    else:
        os.close(descriptor)
        _fail(f"receipt destination already exists: {RECEIPT_NAME}")
    return descriptor, (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_uid,
    )


def _publish_receipt(
    run_descriptor: int,
    run_metadata: tuple[int, ...],
    payload: dict[str, object],
) -> None:
    current = os.fstat(run_descriptor)
    if (
        current.st_dev,
        current.st_ino,
        current.st_mode,
        current.st_uid,
    ) != run_metadata:
        _fail("run_directory changed before receipt publication")
    temporary_name = f".{RECEIPT_NAME}.{os.getpid()}.{secrets.token_hex(8)}.tmp"
    descriptor = -1
    linked_identity: tuple[int, int] | None = None
    publication_error: BaseException | None = None
    try:
        descriptor = os.open(
            temporary_name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0),
            0o600,
            dir_fd=run_descriptor,
        )
        receipt_bytes = _canonical_json_bytes(payload)
        offset = 0
        while offset < len(receipt_bytes):
            offset += os.write(descriptor, receipt_bytes[offset:])
        os.fsync(descriptor)
        temporary_metadata = os.fstat(descriptor)
        temporary_identity = (
            temporary_metadata.st_dev,
            temporary_metadata.st_ino,
        )
        os.link(
            temporary_name,
            RECEIPT_NAME,
            src_dir_fd=run_descriptor,
            dst_dir_fd=run_descriptor,
            follow_symlinks=False,
        )
        linked_identity = temporary_identity
        published = os.stat(
            RECEIPT_NAME,
            dir_fd=run_descriptor,
            follow_symlinks=False,
        )
        if not stat.S_ISREG(published.st_mode) or (published.st_dev, published.st_ino) != temporary_identity:
            _fail("published receipt does not identify the pinned temporary file")
        os.fsync(run_descriptor)
    except FileExistsError as exc:
        publication_error = G040DuckDBBootstrapError(f"receipt destination already exists: {RECEIPT_NAME}: {exc}")
    except G040DuckDBBootstrapError as exc:
        publication_error = exc
    except OSError as exc:
        publication_error = G040DuckDBBootstrapError(f"cannot publish atomic no-follow receipt: {exc}")
    finally:
        if descriptor >= 0:
            try:
                os.close(descriptor)
            except OSError as exc:
                if publication_error is None:
                    publication_error = G040DuckDBBootstrapError(f"cannot close receipt temporary file: {exc}")
        try:
            os.unlink(temporary_name, dir_fd=run_descriptor)
        except FileNotFoundError:
            pass
        except OSError as exc:
            if publication_error is None:
                publication_error = G040DuckDBBootstrapError(f"cannot remove receipt temporary file: {exc}")
        if publication_error is not None and linked_identity is not None:
            try:
                receipt_metadata = os.stat(
                    RECEIPT_NAME,
                    dir_fd=run_descriptor,
                    follow_symlinks=False,
                )
                if (
                    receipt_metadata.st_dev,
                    receipt_metadata.st_ino,
                ) == linked_identity:
                    os.unlink(RECEIPT_NAME, dir_fd=run_descriptor)
                    os.fsync(run_descriptor)
            except FileNotFoundError:
                pass
            except OSError as exc:
                publication_error = G040DuckDBBootstrapError(f"receipt publication and rollback failed: {exc}")
    if publication_error is not None:
        raise publication_error


def _cleanup_workspace(run_descriptor: int, workspace_name: str) -> None:
    if not shutil.rmtree.avoids_symlink_attacks:
        _fail("descriptor-safe workspace cleanup is unavailable")
    try:
        shutil.rmtree(workspace_name, dir_fd=run_descriptor)
    except FileNotFoundError:
        return
    except OSError as exc:
        try:
            metadata = os.stat(
                workspace_name,
                dir_fd=run_descriptor,
                follow_symlinks=False,
            )
            if not stat.S_ISDIR(metadata.st_mode):
                os.unlink(workspace_name, dir_fd=run_descriptor)
                return
        except FileNotFoundError:
            return
        except OSError:
            pass
        raise G040DuckDBBootstrapError(f"cannot clean DuckDB bootstrap workspace: {exc}") from exc


def run_approved_duckdb_bootstrap(
    plan: DuckDBBootstrapPlan,
) -> dict[str, object]:
    """Run one externally authorized G040 plan and publish immutable evidence."""

    if not isinstance(plan, DuckDBBootstrapPlan):
        _fail("plan must be an immutable DuckDBBootstrapPlan")
    _require_unexpired(plan)
    if plan.smoke_bootstrap_sha256 != fixed_smoke_bootstrap_sha256():
        _fail("fixed smoke bootstrap changed after plan construction")
    deadline = time.monotonic() + plan.resource_bounds.max_seconds
    run_descriptor, run_metadata = _validate_run_directory(plan)
    pinned: tuple[_PinnedFile, ...] = ()
    bootstrap_fd = -1
    workspace_descriptor = -1
    workspace_name = f".g040-duckdb-bootstrap.{os.getpid()}.{secrets.token_hex(8)}"
    workspace_created = False
    execution_error: BaseException | None = None
    evidence: dict[str, object] | None = None
    try:
        pinned = _open_plan_files(plan)
        python = pinned[0]
        wheel = pinned[1]
        bootstrap_raw = _FIXED_SMOKE_BOOTSTRAP.encode("utf-8")
        if "sha256:" + hashlib.sha256(bootstrap_raw).hexdigest() != plan.smoke_bootstrap_sha256:
            _fail("captured smoke bootstrap digest differs from the plan")
        bootstrap_fd = _new_sealed_memfd("world-aid-g040-smoke", bootstrap_raw)
        os.mkdir(workspace_name, 0o700, dir_fd=run_descriptor)
        workspace_created = True
        workspace_descriptor = os.open(
            workspace_name,
            os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=run_descriptor,
        )
        workspace = plan.run_directory / workspace_name
        site_root = workspace / "site"
        site_root.mkdir(mode=0o700)
        result_path = workspace / "smoke-result.json"

        _revalidate_plan_files(pinned)
        wheel_evidence = _validate_and_extract_wheel(
            plan=plan,
            wheel=wheel,
            site_root=site_root,
            deadline=deadline,
        )
        _revalidate_plan_files(pinned)
        command_evidence = _run_smoke_child(
            plan=plan,
            python=python,
            bootstrap_fd=bootstrap_fd,
            workspace=workspace,
            site_root=site_root,
            result_path=result_path,
            deadline=deadline,
        )
        _require_deadline(deadline, plan.resource_bounds)
        _revalidate_plan_files(pinned)
        result_descriptor = _open_relative_regular_file(
            workspace,
            "smoke-result.json",
            maximum_bytes=min(
                plan.resource_bounds.max_output_bytes,
                8 * 1024 * 1024,
            ),
            context="DuckDB smoke result",
        )
        try:
            result_raw = _read_fd(
                result_descriptor,
                min(plan.resource_bounds.max_output_bytes, 8 * 1024 * 1024),
                "DuckDB smoke result",
            )
        finally:
            os.close(result_descriptor)
        child_result = _strict_json_bytes(result_raw, "DuckDB smoke result")
        _validate_child_result(child_result, plan)
        observed_workspace_bytes = _validate_workspace_tree(
            workspace,
            plan.resource_bounds.max_workspace_bytes,
        )
        if list(workspace.rglob("*.duckdb")) or list(workspace.rglob("*.wal")):
            _fail("DuckDB child left database or WAL state behind")
        _revalidate_plan_files(pinned)
        _require_unexpired(plan)
        _require_deadline(deadline, plan.resource_bounds)
        evidence = {
            "schema_version": RECEIPT_SCHEMA,
            "goal_id": GOAL_ID,
            "status": "passed",
            "execution_plan_sha256": execution_plan_sha256(plan),
            "authorization_sha256": plan.authorization.sha256,
            "network_boundary": {
                "policy": plan.network_policy,
                "attestation_sha256": plan.network_boundary_attestation.sha256,
                "authority": "external-gate-first-launcher",
            },
            "python": {
                "path": os.fspath(plan.python_path),
                "sha256": plan.python_sha256,
                "size": plan.python_size,
                "version": plan.python_version,
                "flags": ["-I", "-S", "-B"],
            },
            "wheel": {
                "path": os.fspath(plan.wheel_path),
                "filename": plan.wheel_filename,
                "sha256": plan.wheel_sha256,
                "size": plan.wheel_size,
                "duckdb_version": plan.duckdb_version,
                "python_tag": plan.python_tag,
                "abi_tag": plan.abi_tag,
                "platform_tag": plan.platform_tag,
                "validation": wheel_evidence.as_dict(),
            },
            "reviewed_inputs": {
                role: _artifact_payload(artifact)
                for role, artifact in _plan_artifacts(plan)
                if role not in {"authorization", "network_boundary_attestation"}
            },
            "smoke_bootstrap_sha256": plan.smoke_bootstrap_sha256,
            "checks": child_result["checks"],
            "cleanup": {
                **child_result["cleanup"],
                "isolated_site_removed_before_publication": True,
                "workspace_removed_before_publication": True,
            },
            "deny_settings": child_result["settings"],
            "loaded_dynamic_extensions": [],
            "network_attempts": 0,
            "single_writer_enforced": True,
            "second_writer_evidence": child_result["second_writer_evidence"],
            "g033_excluded_controls": list(G033_EXCLUDED_CONTROLS),
            "resource_bounds": {
                **_plan_payload(plan)["resource_bounds"],
                "max_open_files": _FIXED_NOFILE_LIMIT,
                "observed_process_output_bytes": (command_evidence.stdout_bytes + command_evidence.stderr_bytes),
                "observed_workspace_bytes_before_cleanup": observed_workspace_bytes,
            },
            "command": command_evidence.as_dict(),
            "offline": True,
            "live_actions_authorized": False,
            "production_trust": False,
            "expires_at": plan.expires_at,
            "completed_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        }
    except BaseException as exc:
        execution_error = exc
    finally:
        if workspace_descriptor >= 0:
            os.close(workspace_descriptor)
        if bootstrap_fd >= 0:
            os.close(bootstrap_fd)
        for item in pinned:
            os.close(item.descriptor)
        if workspace_created:
            try:
                _cleanup_workspace(run_descriptor, workspace_name)
            except BaseException as cleanup_exc:
                if execution_error is not None:
                    execution_error = G040DuckDBBootstrapError(
                        f"DuckDB bootstrap failed and workspace cleanup also failed: {cleanup_exc}"
                    )
                else:
                    execution_error = cleanup_exc
        try:
            os.stat(workspace_name, dir_fd=run_descriptor, follow_symlinks=False)
        except FileNotFoundError:
            pass
        except OSError as cleanup_check_exc:
            execution_error = G040DuckDBBootstrapError(f"cannot verify workspace teardown: {cleanup_check_exc}")
        else:
            execution_error = G040DuckDBBootstrapError("DuckDB bootstrap workspace survived cleanup")
    try:
        if execution_error is not None:
            raise execution_error
        if evidence is None:
            _fail("DuckDB bootstrap produced no evidence")
        _publish_receipt(run_descriptor, run_metadata, evidence)
        return evidence
    finally:
        os.close(run_descriptor)


__all__ = [
    "CHILD_RESULT_SCHEMA",
    "G033_EXCLUDED_CONTROLS",
    "GOAL_ID",
    "PLAN_SCHEMA",
    "RECEIPT_NAME",
    "RECEIPT_SCHEMA",
    "REQUIRED_G040_CHECKS",
    "DuckDBBootstrapPlan",
    "DuckDBBoundArtifact",
    "DuckDBResourceBounds",
    "G040DuckDBBootstrapError",
    "execution_plan_sha256",
    "fixed_smoke_bootstrap_sha256",
    "run_approved_duckdb_bootstrap",
]
