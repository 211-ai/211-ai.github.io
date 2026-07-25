#!/usr/bin/env python3
"""Sealed, fail-closed execution primitive for future WORLDCOIN-G038.

This module performs no Gate verification and grants no authority.  An
operator-controlled Gate-first launcher must authenticate and freeze the
``SIWEExecutionPlan`` and establish its externally enforced deny-all network
boundary before importing this module.  There is intentionally no CLI,
environment-variable authority, package download, registry fallback, or
caller-selected command.

The literal-false fence in ``tests/world_aid/test_siwe_offline_bootstrap.py``
remains closed.  This is only the capability-injection seam for a future
operator-owned launcher.
"""

from __future__ import annotations

import hashlib
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
import tarfile
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Final

PLAN_SCHEMA: Final = "world-human-aid-g038-siwe-offline-plan/v1"
RECEIPT_SCHEMA: Final = "world-human-aid-siwe-bootstrap-verification-receipt/v2"
RECEIPT_NAME: Final = "world-siwe-offline-smoke.fixture.json"
GOAL_ID: Final = "WORLDCOIN-G038"

_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,255}$")
_READ_CHUNK = 64 * 1024
_MAX_FILE_BINDING_BYTES = 4 * 1024 * 1024 * 1024
_MAX_PROCESS_OUTPUT_BYTES = 64 * 1024 * 1024
_MAX_CACHE_ENTRIES = 200_000
_MAX_CACHE_BYTES = 4 * 1024 * 1024 * 1024
_MAX_WORKSPACE_ENTRIES = 500_000
_MAX_WORKSPACE_BYTES = 8 * 1024 * 1024 * 1024
_FIXED_NOFILE_LIMIT = 128


class G038SIWERunnerError(RuntimeError):
    """Raised when G038 cannot produce exact offline bootstrap evidence."""


@dataclass(frozen=True, slots=True)
class SIWEToolBinding:
    source_path: Path
    sha256: str
    max_bytes: int
    version: str

    def __post_init__(self) -> None:
        _validate_absolute_path(self.source_path, "tool source_path")
        _require_digest(self.sha256, "tool sha256")
        _require_int(self.max_bytes, "tool max_bytes", 1, _MAX_FILE_BINDING_BYTES)
        if not isinstance(self.version, str) or _VERSION_RE.fullmatch(self.version) is None:
            _fail("tool version must be an exact semantic version")


@dataclass(frozen=True, slots=True)
class SIWEBoundInput:
    source_path: Path
    sha256: str
    max_bytes: int
    workspace_relative_path: str

    def __post_init__(self) -> None:
        _validate_absolute_path(self.source_path, "input source_path")
        _require_digest(self.sha256, "input sha256")
        _require_int(self.max_bytes, "input max_bytes", 1, _MAX_FILE_BINDING_BYTES)
        _validate_relative_path(self.workspace_relative_path, "input workspace_relative_path")


@dataclass(frozen=True, slots=True)
class SIWECacheEntry:
    path: str
    kind: str
    size: int
    sha256: str | None

    def __post_init__(self) -> None:
        _validate_relative_path(self.path, "cache entry path")
        if self.kind not in {"directory", "file"}:
            _fail("cache entry kind must be 'directory' or 'file'")
        if self.kind == "directory":
            if self.size != 0 or self.sha256 is not None:
                _fail("cache directory entries require size=0 and sha256=null")
        else:
            _require_int(self.size, "cache file size", 0, _MAX_CACHE_BYTES)
            _require_digest(self.sha256, "cache file sha256")


@dataclass(frozen=True, slots=True)
class SIWECacheArchive:
    source_path: Path
    sha256: str
    max_archive_bytes: int
    archive_format: str
    max_entries: int
    max_extracted_bytes: int
    tree_sha256: str
    entries: tuple[SIWECacheEntry, ...]

    def __post_init__(self) -> None:
        _validate_absolute_path(self.source_path, "cache archive source_path")
        _require_digest(self.sha256, "cache archive sha256")
        _require_int(
            self.max_archive_bytes,
            "cache max_archive_bytes",
            1,
            _MAX_CACHE_BYTES,
        )
        if self.archive_format != "tar":
            _fail("cache archive_format must be exactly 'tar'")
        _require_int(self.max_entries, "cache max_entries", 1, _MAX_CACHE_ENTRIES)
        _require_int(
            self.max_extracted_bytes,
            "cache max_extracted_bytes",
            1,
            _MAX_CACHE_BYTES,
        )
        _require_digest(self.tree_sha256, "cache tree_sha256")
        if not isinstance(self.entries, tuple) or not self.entries:
            _fail("cache entries must be a non-empty tuple")
        if len(self.entries) > self.max_entries:
            _fail("cache manifest exceeds max_entries")
        if any(not isinstance(entry, SIWECacheEntry) for entry in self.entries):
            _fail("cache entries must contain only SIWECacheEntry values")
        paths = [entry.path for entry in self.entries]
        if paths != sorted(paths) or len(paths) != len(set(paths)):
            _fail("cache manifest paths must be unique and sorted")
        if sum(entry.size for entry in self.entries) > self.max_extracted_bytes:
            _fail("cache manifest exceeds max_extracted_bytes")
        file_paths = {entry.path for entry in self.entries if entry.kind == "file"}
        for entry in self.entries:
            parents = PurePosixPath(entry.path).parents
            if any(parent.as_posix() in file_paths for parent in parents if parent.as_posix() != "."):
                _fail("cache manifest places an entry beneath a file")
        if cache_tree_sha256(self.entries) != self.tree_sha256:
            _fail("cache tree_sha256 differs from the exact manifest")


@dataclass(frozen=True, slots=True)
class SIWENetworkBoundary:
    attestation_sha256: str
    namespace: str
    apparmor_profile: str
    network_deny_canary_sha256: str
    egress_policy_sha256: str

    def __post_init__(self) -> None:
        _require_digest(self.attestation_sha256, "network attestation_sha256")
        _require_digest(
            self.network_deny_canary_sha256,
            "network network_deny_canary_sha256",
        )
        _require_digest(self.egress_policy_sha256, "network egress_policy_sha256")
        if not isinstance(self.namespace, str) or not self.namespace.startswith("net:["):
            _fail("network namespace must be an externally attested namespace identity")
        if not isinstance(self.apparmor_profile, str) or not self.apparmor_profile.endswith(" (enforce)"):
            _fail("network apparmor_profile must name an enforcing profile")


@dataclass(frozen=True, slots=True)
class SIWEResourceBounds:
    max_seconds: int
    max_memory_mb: int
    max_output_bytes: int
    max_file_bytes: int
    max_workspace_entries: int
    max_workspace_bytes: int

    def __post_init__(self) -> None:
        _require_int(self.max_seconds, "resource max_seconds", 1, 3600)
        _require_int(self.max_memory_mb, "resource max_memory_mb", 64, 65536)
        _require_int(
            self.max_output_bytes,
            "resource max_output_bytes",
            1,
            _MAX_PROCESS_OUTPUT_BYTES,
        )
        _require_int(
            self.max_file_bytes,
            "resource max_file_bytes",
            1,
            _MAX_WORKSPACE_BYTES,
        )
        _require_int(
            self.max_workspace_entries,
            "resource max_workspace_entries",
            1,
            _MAX_WORKSPACE_ENTRIES,
        )
        _require_int(
            self.max_workspace_bytes,
            "resource max_workspace_bytes",
            1,
            _MAX_WORKSPACE_BYTES,
        )


@dataclass(frozen=True, slots=True)
class SIWEExecutionPlan:
    schema_version: str
    goal_id: str
    authorization_sha256: str
    selection_record_id: str
    network_policy: str
    network_boundary: SIWENetworkBoundary
    platform: str
    architecture: str
    toolchain_archive_sha256: str
    node: SIWEToolBinding
    npm_cli: SIWEToolBinding
    manifest: SIWEBoundInput
    lockfile: SIWEBoundInput
    adapter: SIWEBoundInput
    smoke_source: SIWEBoundInput
    cache: SIWECacheArchive
    resource_bounds: SIWEResourceBounds
    expires_at: str

    def __post_init__(self) -> None:
        if self.schema_version != PLAN_SCHEMA:
            _fail(f"schema_version must be {PLAN_SCHEMA!r}")
        if self.goal_id != GOAL_ID:
            _fail(f"goal_id must be {GOAL_ID!r}")
        _require_digest(self.authorization_sha256, "authorization_sha256")
        if not isinstance(self.selection_record_id, str) or _IDENTIFIER_RE.fullmatch(self.selection_record_id) is None:
            _fail("selection_record_id is invalid")
        if self.network_policy != "external-deny-all":
            _fail("network_policy must be exactly 'external-deny-all'")
        if not isinstance(self.network_boundary, SIWENetworkBoundary):
            _fail("network_boundary must be SIWENetworkBoundary")
        for name, value in (("platform", self.platform), ("architecture", self.architecture)):
            if not isinstance(value, str) or _IDENTIFIER_RE.fullmatch(value) is None:
                _fail(f"{name} is invalid")
        _require_digest(self.toolchain_archive_sha256, "toolchain_archive_sha256")
        if not isinstance(self.node, SIWEToolBinding) or not isinstance(
            self.npm_cli,
            SIWEToolBinding,
        ):
            _fail("node and npm_cli must be SIWEToolBinding values")
        expected_inputs = (
            ("manifest", self.manifest, "package.json"),
            ("lockfile", self.lockfile, "package-lock.json"),
            ("adapter", self.adapter, "index.mjs"),
            ("smoke_source", self.smoke_source, "g038-smoke.mjs"),
        )
        for name, binding, destination in expected_inputs:
            if not isinstance(binding, SIWEBoundInput):
                _fail(f"{name} must be SIWEBoundInput")
            if binding.workspace_relative_path != destination:
                _fail(f"{name} destination must be exactly {destination!r}")
        if not isinstance(self.cache, SIWECacheArchive):
            _fail("cache must be SIWECacheArchive")
        source_paths = [
            self.node.source_path,
            self.npm_cli.source_path,
            *(binding.source_path for _, binding, _ in expected_inputs),
            self.cache.source_path,
        ]
        if len(source_paths) != len(set(source_paths)):
            _fail("all SIWE tool, input, and cache source paths must be unique")
        if not isinstance(self.resource_bounds, SIWEResourceBounds):
            _fail("resource_bounds must be SIWEResourceBounds")
        _parse_expiry(self.expires_at)


@dataclass(frozen=True, slots=True)
class _SealedFile:
    source_path: Path
    sha256: str
    max_bytes: int
    descriptor: int
    metadata: tuple[int, ...]
    label: str


@dataclass(frozen=True, slots=True)
class _ObservedEntry:
    kind: str
    size: int
    sha256: str | None


@dataclass(frozen=True, slots=True)
class _CommandResult:
    stdout: bytes
    stderr_sha256: str
    stdout_sha256: str
    stderr_bytes: int
    elapsed_ms: int


def _fail(message: str) -> None:
    raise G038SIWERunnerError(message)


def _require_int(value: object, name: str, minimum: int, maximum: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        _fail(f"{name} must be an integer from {minimum} through {maximum}")


def _require_digest(value: object, name: str) -> None:
    if not isinstance(value, str) or _DIGEST_RE.fullmatch(value) is None:
        _fail(f"{name} must be a lowercase sha256 digest")


def _validate_absolute_path(path: object, name: str) -> None:
    if not isinstance(path, Path) or not path.is_absolute() or "\x00" in os.fspath(path) or ".." in path.parts:
        _fail(f"{name} must be a normalized absolute pathlib.Path")


def _validate_relative_path(value: object, name: str) -> None:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        _fail(f"{name} must be a normalized relative POSIX path")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or path.as_posix() != value
        or any(part in {"", ".", ".."} for part in path.parts)
        or any(any(ord(character) < 32 or ord(character) == 127 for character in part) for part in path.parts)
    ):
        _fail(f"{name} must be a normalized relative POSIX path")


def _parse_expiry(value: object) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        _fail("expires_at must be a canonical UTC timestamp ending in Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise G038SIWERunnerError("expires_at is invalid") from exc
    if parsed.tzinfo != UTC or parsed.isoformat(timespec="seconds").replace("+00:00", "Z") != value:
        _fail("expires_at must use canonical second-precision UTC form")
    return parsed


def _require_unexpired(plan: SIWEExecutionPlan) -> None:
    if datetime.now(UTC) >= _parse_expiry(plan.expires_at):
        _fail("the immutable G038 execution plan has expired")


def _canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def cache_tree_sha256(entries: tuple[SIWECacheEntry, ...]) -> str:
    """Compute the Gate-compatible, path-and-content cache tree digest."""

    digest = hashlib.sha256()

    def add(kind: bytes, path: str, file_digest: str | None = None) -> None:
        encoded = path.encode("utf-8")
        digest.update(kind)
        digest.update(len(encoded).to_bytes(8, "big"))
        digest.update(encoded)
        if file_digest is not None:
            digest.update(bytes.fromhex(file_digest.removeprefix("sha256:")))

    by_path = {entry.path: entry for entry in entries}
    children: dict[str, list[SIWECacheEntry]] = {".": []}
    for entry in entries:
        parent = PurePosixPath(entry.path).parent.as_posix()
        if parent != ".":
            parent_entry = by_path.get(parent)
            if parent_entry is None or parent_entry.kind != "directory":
                _fail(f"cache manifest omits directory parent {parent!r}")
        children.setdefault(parent, []).append(entry)
        if entry.kind == "directory":
            children.setdefault(entry.path, [])

    add(b"D", ".")

    def walk(parent: str) -> None:
        for entry in sorted(
            children[parent],
            key=lambda value: PurePosixPath(value.path).name.encode("utf-8"),
        ):
            add(
                b"D" if entry.kind == "directory" else b"F",
                entry.path,
                entry.sha256 if entry.kind == "file" else None,
            )
            if entry.kind == "directory":
                walk(entry.path)

    walk(".")
    return "sha256:" + digest.hexdigest()


def _plan_payload(plan: SIWEExecutionPlan) -> dict[str, object]:
    def tool(value: SIWEToolBinding) -> dict[str, object]:
        return {
            "source_path": os.fspath(value.source_path),
            "sha256": value.sha256,
            "max_bytes": value.max_bytes,
            "version": value.version,
        }

    def bound_input(value: SIWEBoundInput) -> dict[str, object]:
        return {
            "source_path": os.fspath(value.source_path),
            "sha256": value.sha256,
            "max_bytes": value.max_bytes,
            "workspace_relative_path": value.workspace_relative_path,
        }

    return {
        "schema_version": plan.schema_version,
        "goal_id": plan.goal_id,
        "authorization_sha256": plan.authorization_sha256,
        "selection_record_id": plan.selection_record_id,
        "network_policy": plan.network_policy,
        "network_boundary": {
            "attestation_sha256": plan.network_boundary.attestation_sha256,
            "namespace": plan.network_boundary.namespace,
            "apparmor_profile": plan.network_boundary.apparmor_profile,
            "network_deny_canary_sha256": plan.network_boundary.network_deny_canary_sha256,
            "egress_policy_sha256": plan.network_boundary.egress_policy_sha256,
        },
        "platform": plan.platform,
        "architecture": plan.architecture,
        "toolchain_archive_sha256": plan.toolchain_archive_sha256,
        "node": tool(plan.node),
        "npm_cli": tool(plan.npm_cli),
        "manifest": bound_input(plan.manifest),
        "lockfile": bound_input(plan.lockfile),
        "adapter": bound_input(plan.adapter),
        "smoke_source": bound_input(plan.smoke_source),
        "cache": {
            "source_path": os.fspath(plan.cache.source_path),
            "sha256": plan.cache.sha256,
            "max_archive_bytes": plan.cache.max_archive_bytes,
            "archive_format": plan.cache.archive_format,
            "max_entries": plan.cache.max_entries,
            "max_extracted_bytes": plan.cache.max_extracted_bytes,
            "tree_sha256": plan.cache.tree_sha256,
            "entries": [
                {
                    "path": entry.path,
                    "kind": entry.kind,
                    "size": entry.size,
                    "sha256": entry.sha256,
                }
                for entry in plan.cache.entries
            ],
        },
        "resource_bounds": {
            "max_seconds": plan.resource_bounds.max_seconds,
            "max_memory_mb": plan.resource_bounds.max_memory_mb,
            "max_output_bytes": plan.resource_bounds.max_output_bytes,
            "max_file_bytes": plan.resource_bounds.max_file_bytes,
            "max_workspace_entries": plan.resource_bounds.max_workspace_entries,
            "max_workspace_bytes": plan.resource_bounds.max_workspace_bytes,
        },
        "expires_at": plan.expires_at,
    }


def execution_plan_sha256(plan: SIWEExecutionPlan) -> str:
    return "sha256:" + hashlib.sha256(_canonical_bytes(_plan_payload(plan))).hexdigest()


def _snapshot(metadata: os.stat_result) -> tuple[int, ...]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def _open_directory_no_symlink(path: Path, label: str) -> int:
    _validate_absolute_path(path, label)
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open("/", flags)
    try:
        for component in path.parts[1:]:
            child = os.open(component, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        return descriptor
    except OSError as exc:
        os.close(descriptor)
        raise G038SIWERunnerError(f"cannot open {label} without symlinks: {exc}") from exc


def _hash_descriptor(descriptor: int, max_bytes: int, label: str) -> str:
    before = os.fstat(descriptor)
    if not stat.S_ISREG(before.st_mode) or before.st_size > max_bytes:
        _fail(f"{label} must be a bounded regular file")
    os.lseek(descriptor, 0, os.SEEK_SET)
    digest = hashlib.sha256()
    total = 0
    while chunk := os.read(descriptor, _READ_CHUNK):
        total += len(chunk)
        if total > max_bytes:
            _fail(f"{label} exceeds its byte bound")
        digest.update(chunk)
    if _snapshot(os.fstat(descriptor)) != _snapshot(before):
        _fail(f"{label} changed while being hashed")
    return "sha256:" + digest.hexdigest()


def _seal_file(
    source_path: Path,
    expected_sha256: str,
    max_bytes: int,
    label: str,
    *,
    executable: bool,
) -> _SealedFile:
    parent = _open_directory_no_symlink(source_path.parent, f"{label} parent")
    descriptor = -1
    try:
        descriptor = os.open(
            source_path.name,
            os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0),
            dir_fd=parent,
        )
    except OSError as exc:
        raise G038SIWERunnerError(f"cannot seal {label}: {exc}") from exc
    finally:
        os.close(parent)
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            _fail(f"{label} must be a regular file")
        if executable and metadata.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH) == 0:
            _fail(f"{label} must be executable")
        if executable and metadata.st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH):
            _fail(f"{label} must be mode-immutable")
        observed = _hash_descriptor(descriptor, max_bytes, label)
        if observed != expected_sha256:
            _fail(f"{label} digest mismatch: expected {expected_sha256}, observed {observed}")
        return _SealedFile(
            source_path=source_path,
            sha256=expected_sha256,
            max_bytes=max_bytes,
            descriptor=descriptor,
            metadata=_snapshot(metadata),
            label=label,
        )
    except BaseException:
        os.close(descriptor)
        raise


def _revalidate_seal(seal: _SealedFile) -> None:
    if _snapshot(os.fstat(seal.descriptor)) != seal.metadata:
        _fail(f"{seal.label} changed after sealing")
    if _hash_descriptor(seal.descriptor, seal.max_bytes, seal.label) != seal.sha256:
        _fail(f"{seal.label} digest drifted after sealing")
    parent = _open_directory_no_symlink(seal.source_path.parent, f"{seal.label} parent")
    reopened = -1
    try:
        reopened = os.open(
            seal.source_path.name,
            os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0),
            dir_fd=parent,
        )
        if _snapshot(os.fstat(reopened)) != seal.metadata:
            _fail(f"{seal.label} source path no longer identifies the sealed file")
        if _hash_descriptor(reopened, seal.max_bytes, seal.label) != seal.sha256:
            _fail(f"{seal.label} source path digest drifted")
    except OSError as exc:
        raise G038SIWERunnerError(f"cannot revalidate {seal.label}: {exc}") from exc
    finally:
        if reopened >= 0:
            os.close(reopened)
        os.close(parent)


def _copy_seal(seal: _SealedFile, destination: Path, *, mode: int) -> None:
    destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor = -1
    try:
        descriptor = os.open(
            destination,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0),
            0o600,
        )
        if _snapshot(os.fstat(seal.descriptor)) != seal.metadata:
            _fail(f"{seal.label} changed before materialization")
        os.lseek(seal.descriptor, 0, os.SEEK_SET)
        digest = hashlib.sha256()
        total = 0
        while chunk := os.read(seal.descriptor, _READ_CHUNK):
            total += len(chunk)
            if total > seal.max_bytes:
                _fail(f"{seal.label} exceeds its byte bound")
            digest.update(chunk)
            offset = 0
            while offset < len(chunk):
                offset += os.write(descriptor, chunk[offset:])
        if "sha256:" + digest.hexdigest() != seal.sha256:
            _fail(f"{seal.label} changed while being materialized")
        if _snapshot(os.fstat(seal.descriptor)) != seal.metadata:
            _fail(f"{seal.label} changed while being materialized")
        os.fchmod(descriptor, mode)
        os.fsync(descriptor)
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _safe_extract_cache(
    archive: _SealedFile,
    cache: SIWECacheArchive,
    destination: Path,
) -> None:
    destination.mkdir(mode=0o700)
    _revalidate_seal(archive)
    duplicate = os.dup(archive.descriptor)
    total_entries = 0
    total_bytes = 0
    seen: set[str] = set()
    try:
        os.lseek(duplicate, 0, os.SEEK_SET)
        with os.fdopen(duplicate, "rb") as source:
            duplicate = -1
            with tarfile.open(fileobj=source, mode="r:") as tar:
                for member in tar:
                    total_entries += 1
                    if total_entries > cache.max_entries:
                        _fail("cache archive exceeds its entry limit")
                    normalized = member.name.rstrip("/") if member.isdir() else member.name
                    _validate_relative_path(normalized, "cache archive member")
                    if normalized in seen:
                        _fail("cache archive contains a duplicate member")
                    seen.add(normalized)
                    if member.issym() or member.islnk():
                        _fail("cache archive contains a symlink or hardlink")
                    if not (member.isdir() or member.isfile()) or member.issparse():
                        _fail("cache archive contains a device, FIFO, sparse, or unsupported member")
                    target = destination.joinpath(*PurePosixPath(normalized).parts)
                    if member.isdir():
                        if member.size != 0:
                            _fail("cache archive directory contains a hidden payload")
                        target.mkdir(mode=0o700, parents=True, exist_ok=False)
                        continue
                    if member.size < 0 or member.size > cache.max_extracted_bytes:
                        _fail("cache archive member has an invalid size")
                    total_bytes += member.size
                    if total_bytes > cache.max_extracted_bytes:
                        _fail("cache archive exceeds its extracted-byte limit")
                    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                    output = os.open(
                        target,
                        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0),
                        0o600,
                    )
                    try:
                        extracted = tar.extractfile(member)
                        if extracted is None:
                            _fail("cache archive regular member has no payload")
                        remaining = member.size
                        while remaining:
                            chunk = extracted.read(min(_READ_CHUNK, remaining))
                            if not chunk:
                                _fail("cache archive member is truncated")
                            offset = 0
                            while offset < len(chunk):
                                offset += os.write(output, chunk[offset:])
                            remaining -= len(chunk)
                        if extracted.read(1):
                            _fail("cache archive member exceeds its declared size")
                        os.fchmod(output, 0o400)
                        os.fsync(output)
                    finally:
                        os.close(output)
    except (tarfile.TarError, OSError) as exc:
        raise G038SIWERunnerError(f"cannot safely extract cache archive: {exc}") from exc
    finally:
        if duplicate >= 0:
            os.close(duplicate)
    _revalidate_seal(archive)


def _scan_tree(
    root: Path,
    *,
    max_entries: int,
    max_bytes: int,
    max_file_bytes: int,
    require_read_only: bool,
) -> tuple[str, dict[str, _ObservedEntry]]:
    root_descriptor = _open_directory_no_symlink(root, "tree root")
    digest = hashlib.sha256()
    observed: dict[str, _ObservedEntry] = {}
    entry_count = 0
    total_bytes = 0

    def add(kind: bytes, relative: str, file_digest: bytes | None = None) -> None:
        encoded = relative.encode("utf-8")
        digest.update(kind)
        digest.update(len(encoded).to_bytes(8, "big"))
        digest.update(encoded)
        if file_digest is not None:
            digest.update(file_digest)

    def walk(directory_descriptor: int, relative: str) -> None:
        nonlocal entry_count, total_bytes
        metadata = os.fstat(directory_descriptor)
        if not stat.S_ISDIR(metadata.st_mode):
            _fail("tree traversal reached a non-directory")
        if require_read_only and metadata.st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH):
            _fail("reviewed cache contains a writable directory")
        add(b"D", relative)
        names: list[tuple[bytes, str]] = []
        with os.scandir(directory_descriptor) as entries:
            for entry in entries:
                name = entry.name
                _validate_relative_path(name, "tree entry name")
                names.append((name.encode("utf-8"), name))
        for _, name in sorted(names):
            entry_count += 1
            if entry_count > max_entries:
                _fail("tree exceeds its entry limit")
            child_relative = name if relative == "." else f"{relative}/{name}"
            descriptor = os.open(
                name,
                os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0),
                dir_fd=directory_descriptor,
            )
            try:
                child = os.fstat(descriptor)
                if stat.S_ISDIR(child.st_mode):
                    observed[child_relative] = _ObservedEntry("directory", 0, None)
                    walk(descriptor, child_relative)
                elif stat.S_ISREG(child.st_mode):
                    if require_read_only and child.st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH):
                        _fail("reviewed cache contains a writable file")
                    if child.st_size > max_file_bytes:
                        _fail("tree contains a file above the file-size limit")
                    total_bytes += child.st_size
                    if total_bytes > max_bytes:
                        _fail("tree exceeds its byte limit")
                    file_sha256 = _hash_descriptor(descriptor, max_file_bytes, child_relative)
                    observed[child_relative] = _ObservedEntry(
                        "file",
                        child.st_size,
                        file_sha256,
                    )
                    add(
                        b"F",
                        child_relative,
                        bytes.fromhex(file_sha256.removeprefix("sha256:")),
                    )
                else:
                    _fail("tree contains a symlink, device, FIFO, socket, or unsupported entry")
            finally:
                os.close(descriptor)

    try:
        try:
            walk(root_descriptor, ".")
        except OSError as exc:
            raise G038SIWERunnerError(f"cannot scan bounded tree safely: {exc}") from exc
    finally:
        os.close(root_descriptor)
    return "sha256:" + digest.hexdigest(), observed


def _verify_cache_manifest(
    cache: SIWECacheArchive,
    observed_digest: str,
    observed: dict[str, _ObservedEntry],
) -> None:
    expected = {entry.path: _ObservedEntry(entry.kind, entry.size, entry.sha256) for entry in cache.entries}
    if observed != expected:
        _fail("extracted cache tree differs from its exact manifest")
    if observed_digest != cache.tree_sha256:
        _fail("extracted cache tree digest differs from the approved tree")


def _make_cache_read_only(root: Path) -> None:
    paths = (root, *root.rglob("*"))
    for path in sorted(paths, key=lambda item: len(item.parts), reverse=True):
        metadata = path.lstat()
        if stat.S_ISDIR(metadata.st_mode):
            os.chmod(path, 0o500, follow_symlinks=False)
        elif stat.S_ISREG(metadata.st_mode):
            os.chmod(path, 0o400, follow_symlinks=False)
        else:
            _fail("extracted cache contains an unsafe entry before mode sealing")


def _make_cache_writable(root: Path, observed: dict[str, _ObservedEntry]) -> None:
    for relative, entry in sorted(
        observed.items(),
        key=lambda item: len(PurePosixPath(item[0]).parts),
    ):
        path = root.joinpath(*PurePosixPath(relative).parts)
        os.chmod(path, 0o700 if entry.kind == "directory" else 0o600, follow_symlinks=False)
    os.chmod(root, 0o700, follow_symlinks=False)


def _bounded_rlimit(kind: int, requested: int) -> tuple[int, int]:
    _, hard = resource.getrlimit(kind)
    effective = requested if hard == resource.RLIM_INFINITY else min(requested, hard)
    return effective, effective


def _resource_limiter(bounds: SIWEResourceBounds):
    def apply() -> None:
        os.umask(0o077)
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        resource.setrlimit(
            resource.RLIMIT_CPU,
            _bounded_rlimit(resource.RLIMIT_CPU, bounds.max_seconds),
        )
        resource.setrlimit(
            resource.RLIMIT_AS,
            _bounded_rlimit(resource.RLIMIT_AS, bounds.max_memory_mb * 1024 * 1024),
        )
        resource.setrlimit(
            resource.RLIMIT_FSIZE,
            _bounded_rlimit(resource.RLIMIT_FSIZE, bounds.max_file_bytes),
        )
        resource.setrlimit(
            resource.RLIMIT_NOFILE,
            _bounded_rlimit(resource.RLIMIT_NOFILE, _FIXED_NOFILE_LIMIT),
        )

    return apply


def _terminate_group(process: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        process.poll()
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
        process.wait(timeout=1)
    except subprocess.TimeoutExpired:
        _fail("could not reap the bounded SIWE process group")


def _run_process(
    *,
    argv: tuple[str, ...],
    cwd: Path,
    environment: dict[str, str],
    pass_fds: tuple[int, ...],
    bounds: SIWEResourceBounds,
    deadline: float,
    output_limit: int,
    label: str,
) -> _CommandResult:
    if time.monotonic() >= deadline:
        _fail(f"{label} cannot start after the whole-run deadline")
    if output_limit <= 0:
        _fail(f"{label} cannot start after the output bound is exhausted")
    started = time.monotonic()
    try:
        process = subprocess.Popen(
            argv,
            cwd=cwd,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            close_fds=True,
            pass_fds=pass_fds,
            start_new_session=True,
            preexec_fn=_resource_limiter(bounds),
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise G038SIWERunnerError(f"{label} could not start: {exc}") from exc
    streams = {
        process.stdout: [hashlib.sha256(), bytearray()],
        process.stderr: [hashlib.sha256(), bytearray()],
    }
    selector = selectors.DefaultSelector()
    for stream in streams:
        if stream is None:
            _terminate_group(process)
            _fail(f"{label} output pipe was not created")
        os.set_blocking(stream.fileno(), False)
        selector.register(stream, selectors.EVENT_READ)
    failure: G038SIWERunnerError | None = None
    try:
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                failure = G038SIWERunnerError(f"{label} exceeded the {bounds.max_seconds}-second whole-run timeout")
                break
            events = selector.select(min(remaining, 0.1))
            if not events and process.poll() is not None:
                events = [(key, selectors.EVENT_READ) for key in selector.get_map().values()]
            for key, _ in events:
                stream = key.fileobj
                try:
                    chunk = os.read(stream.fileno(), _READ_CHUNK)
                except BlockingIOError:
                    continue
                if not chunk:
                    selector.unregister(stream)
                    continue
                total = sum(len(value[1]) for value in streams.values()) + len(chunk)
                if total > output_limit:
                    failure = G038SIWERunnerError(f"{label} exceeded the remaining {output_limit}-byte output bound")
                    break
                streams[stream][0].update(chunk)
                streams[stream][1].extend(chunk)
            if failure is not None:
                break
        if failure is None:
            try:
                return_code = process.wait(timeout=max(0.0, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                failure = G038SIWERunnerError(f"{label} exceeded the {bounds.max_seconds}-second whole-run timeout")
            else:
                if return_code != 0:
                    failure = G038SIWERunnerError(f"{label} failed with exit code {return_code}")
    finally:
        selector.close()
        for stream in streams:
            if stream is not None:
                stream.close()
        _terminate_group(process)
    if failure is not None:
        raise failure
    stdout_digest, stdout = streams[process.stdout]
    stderr_digest, stderr = streams[process.stderr]
    return _CommandResult(
        stdout=bytes(stdout),
        stdout_sha256="sha256:" + stdout_digest.hexdigest(),
        stderr_sha256="sha256:" + stderr_digest.hexdigest(),
        stderr_bytes=len(stderr),
        elapsed_ms=max(0, math.ceil((time.monotonic() - started) * 1000)),
    )


def _command_environment(workspace: Path, cache: Path) -> dict[str, str]:
    home = workspace / "home"
    temporary = workspace / "tmp"
    home.mkdir(mode=0o700)
    temporary.mkdir(mode=0o700)
    npmrc = workspace / "npmrc"
    npmrc.write_text(
        "audit=false\nfund=false\nignore-scripts=true\noffline=true\n"
        "registry=file:///nonexistent-world-aid-registry\nupdate-notifier=false\n",
        encoding="utf-8",
    )
    npmrc.chmod(0o400)
    return {
        "CARGO_NET_OFFLINE": "true",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_TERMINAL_PROMPT": "0",
        "HOME": os.fspath(home),
        "LANG": "C",
        "LC_ALL": "C",
        "NPM_CONFIG_USERCONFIG": os.fspath(npmrc),
        "PATH": "/nonexistent",
        "PIP_NO_INDEX": "1",
        "TMPDIR": os.fspath(temporary),
        "TZ": "UTC",
        "http_proxy": "",
        "https_proxy": "",
        "no_proxy": "*",
        "npm_config_audit": "false",
        "npm_config_cache": os.fspath(cache),
        "npm_config_fetch_retries": "0",
        "npm_config_fund": "false",
        "npm_config_ignore_scripts": "true",
        "npm_config_offline": "true",
        "npm_config_registry": "file:///nonexistent-world-aid-registry",
        "npm_config_script_shell": "/nonexistent",
        "npm_config_update_notifier": "false",
    }


def _verify_materialized_inputs(
    service_root: Path,
    bindings: tuple[tuple[SIWEBoundInput, _SealedFile], ...],
) -> None:
    for binding, _ in bindings:
        path = service_root.joinpath(*PurePosixPath(binding.workspace_relative_path).parts)
        descriptor = os.open(
            path,
            os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0),
        )
        try:
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode):
                _fail(f"materialized {binding.workspace_relative_path} is not regular")
            if metadata.st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH):
                _fail(f"materialized {binding.workspace_relative_path} became writable")
            if (
                _hash_descriptor(
                    descriptor,
                    binding.max_bytes,
                    f"materialized {binding.workspace_relative_path}",
                )
                != binding.sha256
            ):
                _fail(f"materialized {binding.workspace_relative_path} digest drifted")
        finally:
            os.close(descriptor)


def _strict_smoke_result(raw: bytes) -> dict[str, object]:
    def strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                _fail(f"smoke output contains duplicate key {key!r}")
            result[key] = value
        return result

    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=strict_object,
            parse_constant=lambda constant: _fail(f"smoke output contains {constant}"),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise G038SIWERunnerError(f"smoke output is not strict UTF-8 JSON: {exc}") from exc
    expected = {"eoa": True, "eip1271": True, "contractReads": 1}
    if (
        not isinstance(value, dict)
        or set(value) != set(expected)
        or value["eoa"] is not True
        or value["eip1271"] is not True
        or isinstance(value["contractReads"], bool)
        or not isinstance(value["contractReads"], int)
        or value["contractReads"] != 1
    ):
        _fail("smoke output does not prove exact EOA and injected EIP-1271 paths")
    return expected


def _validate_run_directory(run_directory: Path) -> tuple[int, tuple[int, ...]]:
    _validate_absolute_path(run_directory, "run_directory")
    descriptor = _open_directory_no_symlink(run_directory, "run_directory")
    metadata = os.fstat(descriptor)
    if metadata.st_uid != os.geteuid() or metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
        os.close(descriptor)
        _fail("run_directory must be caller-owned and not group/other writable")
    try:
        os.stat(RECEIPT_NAME, dir_fd=descriptor, follow_symlinks=False)
    except FileNotFoundError:
        pass
    except OSError as exc:
        os.close(descriptor)
        raise G038SIWERunnerError(f"cannot inspect receipt destination: {exc}") from exc
    else:
        os.close(descriptor)
        _fail(f"receipt destination already exists: {RECEIPT_NAME}")
    return descriptor, (metadata.st_dev, metadata.st_ino, metadata.st_mode, metadata.st_uid)


def _publish_receipt(
    run_descriptor: int,
    run_identity: tuple[int, ...],
    receipt: dict[str, object],
) -> None:
    metadata = os.fstat(run_descriptor)
    if (metadata.st_dev, metadata.st_ino, metadata.st_mode, metadata.st_uid) != run_identity:
        _fail("run_directory changed before receipt publication")
    temporary = f".{RECEIPT_NAME}.{os.getpid()}.{secrets.token_hex(8)}.tmp"
    descriptor = -1
    linked_identity: tuple[int, int] | None = None
    error: BaseException | None = None
    try:
        descriptor = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0),
            0o600,
            dir_fd=run_descriptor,
        )
        raw = _canonical_bytes(receipt)
        offset = 0
        while offset < len(raw):
            offset += os.write(descriptor, raw[offset:])
        os.fsync(descriptor)
        temporary_metadata = os.fstat(descriptor)
        temporary_identity = (temporary_metadata.st_dev, temporary_metadata.st_ino)
        os.link(
            temporary,
            RECEIPT_NAME,
            src_dir_fd=run_descriptor,
            dst_dir_fd=run_descriptor,
            follow_symlinks=False,
        )
        linked_identity = temporary_identity
        published = os.stat(RECEIPT_NAME, dir_fd=run_descriptor, follow_symlinks=False)
        if (published.st_dev, published.st_ino) != linked_identity or not stat.S_ISREG(published.st_mode):
            _fail("published receipt does not identify the pinned temporary")
        os.fsync(run_descriptor)
    except BaseException as exc:
        error = exc
    finally:
        if descriptor >= 0:
            try:
                os.close(descriptor)
            except OSError as exc:
                error = error or exc
        try:
            os.unlink(temporary, dir_fd=run_descriptor)
        except FileNotFoundError:
            pass
        except OSError as exc:
            error = error or exc
        if error is not None and linked_identity is not None:
            try:
                published = os.stat(
                    RECEIPT_NAME,
                    dir_fd=run_descriptor,
                    follow_symlinks=False,
                )
                if (published.st_dev, published.st_ino) == linked_identity:
                    os.unlink(RECEIPT_NAME, dir_fd=run_descriptor)
                    os.fsync(run_descriptor)
            except FileNotFoundError:
                pass
            except OSError as rollback:
                error = G038SIWERunnerError(f"receipt publication failed and rollback failed: {rollback}")
    if error is not None:
        if isinstance(error, G038SIWERunnerError):
            raise error
        raise G038SIWERunnerError(f"cannot publish atomic no-replace receipt: {error}") from error


def _cleanup_workspace(run_descriptor: int, name: str) -> None:
    if not shutil.rmtree.avoids_symlink_attacks:
        _fail("descriptor-safe workspace cleanup is unavailable")
    try:
        shutil.rmtree(name, dir_fd=run_descriptor)
    except FileNotFoundError:
        return
    except OSError as exc:
        try:
            metadata = os.stat(name, dir_fd=run_descriptor, follow_symlinks=False)
            if not stat.S_ISDIR(metadata.st_mode):
                os.unlink(name, dir_fd=run_descriptor)
                return
        except FileNotFoundError:
            return
        except OSError:
            pass
        raise G038SIWERunnerError(f"cannot clean SIWE workspace: {exc}") from exc


def run_approved_siwe_bootstrap(
    plan: SIWEExecutionPlan,
    *,
    run_directory: Path,
) -> dict[str, object]:
    """Run the exact offline install and dual-path SIWE smoke.

    The immutable plan and external deny-all boundary must already have been
    authenticated by the Gate-first launcher.  Transient artifacts are removed
    before an exact v2 receipt is linked into the caller-owned run directory.
    """

    if not isinstance(plan, SIWEExecutionPlan):
        _fail("plan must be an immutable SIWEExecutionPlan")
    _require_unexpired(plan)
    deadline = time.monotonic() + plan.resource_bounds.max_seconds
    remaining_output = plan.resource_bounds.max_output_bytes
    run_descriptor, run_identity = _validate_run_directory(run_directory)
    workspace_name = f".g038-siwe.{os.getpid()}.{secrets.token_hex(8)}"
    workspace_created = False
    workspace_descriptor = -1
    seals: list[_SealedFile] = []
    receipt: dict[str, object] | None = None
    execution_error: BaseException | None = None
    try:
        node = _seal_file(
            plan.node.source_path,
            plan.node.sha256,
            plan.node.max_bytes,
            "Node executable",
            executable=True,
        )
        seals.append(node)
        npm = _seal_file(
            plan.npm_cli.source_path,
            plan.npm_cli.sha256,
            plan.npm_cli.max_bytes,
            "npm CLI entrypoint",
            executable=False,
        )
        seals.append(npm)
        input_bindings = (
            (plan.manifest, "manifest"),
            (plan.lockfile, "lockfile"),
            (plan.adapter, "adapter"),
            (plan.smoke_source, "smoke source"),
        )
        sealed_inputs: list[tuple[SIWEBoundInput, _SealedFile]] = []
        for binding, label in input_bindings:
            seal = _seal_file(
                binding.source_path,
                binding.sha256,
                binding.max_bytes,
                label,
                executable=False,
            )
            seals.append(seal)
            sealed_inputs.append((binding, seal))
        archive = _seal_file(
            plan.cache.source_path,
            plan.cache.sha256,
            plan.cache.max_archive_bytes,
            "offline cache archive",
            executable=False,
        )
        seals.append(archive)

        os.mkdir(workspace_name, 0o700, dir_fd=run_descriptor)
        workspace_created = True
        workspace_descriptor = os.open(
            workspace_name,
            os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=run_descriptor,
        )
        workspace = run_directory / workspace_name
        service = workspace / "service"
        service.mkdir(mode=0o700)
        for binding, seal in sealed_inputs:
            destination = service.joinpath(*PurePosixPath(binding.workspace_relative_path).parts)
            _copy_seal(seal, destination, mode=0o400)

        local_cache = workspace / "npm-cache"
        _safe_extract_cache(archive, plan.cache, local_cache)
        _make_cache_read_only(local_cache)
        local_before, observed_cache = _scan_tree(
            local_cache,
            max_entries=plan.cache.max_entries,
            max_bytes=plan.cache.max_extracted_bytes,
            max_file_bytes=plan.resource_bounds.max_file_bytes,
            require_read_only=True,
        )
        _verify_cache_manifest(plan.cache, local_before, observed_cache)
        _make_cache_writable(local_cache, observed_cache)
        environment = _command_environment(workspace, local_cache)
        node_path = f"/proc/self/fd/{node.descriptor}"
        npm_path = f"/proc/self/fd/{npm.descriptor}"
        pass_fds = (node.descriptor, npm.descriptor)

        command_summaries: dict[str, dict[str, object]] = {}

        def execute(label: str, argv: tuple[str, ...]) -> _CommandResult:
            nonlocal remaining_output
            _require_unexpired(plan)
            for seal in seals:
                _revalidate_seal(seal)
            _verify_materialized_inputs(service, tuple(sealed_inputs))
            result = _run_process(
                argv=argv,
                cwd=service,
                environment=environment,
                pass_fds=pass_fds,
                bounds=plan.resource_bounds,
                deadline=deadline,
                output_limit=remaining_output,
                label=label,
            )
            remaining_output -= len(result.stdout) + result.stderr_bytes
            for seal in seals:
                _revalidate_seal(seal)
            _verify_materialized_inputs(service, tuple(sealed_inputs))
            _scan_tree(
                workspace,
                max_entries=plan.resource_bounds.max_workspace_entries,
                max_bytes=plan.resource_bounds.max_workspace_bytes,
                max_file_bytes=plan.resource_bounds.max_file_bytes,
                require_read_only=False,
            )
            command_summaries[label] = {
                "stdout_sha256": result.stdout_sha256,
                "stderr_sha256": result.stderr_sha256,
                "elapsed_ms": result.elapsed_ms,
            }
            return result

        npm_version_raw = execute("npm_version", (node_path, npm_path, "--version")).stdout
        node_version_raw = execute("node_version", (node_path, "--version")).stdout
        try:
            npm_version = npm_version_raw.decode("utf-8").strip()
            node_version = node_version_raw.decode("utf-8").strip()
        except UnicodeDecodeError as exc:
            raise G038SIWERunnerError(f"tool version output is not UTF-8: {exc}") from exc
        if npm_version != plan.npm_cli.version:
            _fail(f"npm version differs: expected {plan.npm_cli.version!r}, observed {npm_version!r}")
        if node_version != f"v{plan.node.version}":
            _fail(f"Node version differs: expected v{plan.node.version!r}, observed {node_version!r}")

        execute(
            "npm_ci",
            (
                node_path,
                npm_path,
                "ci",
                "--offline",
                "--ignore-scripts",
                "--audit=false",
                "--fund=false",
                "--cache",
                os.fspath(local_cache),
            ),
        )
        smoke_path = service / plan.smoke_source.workspace_relative_path
        smoke_raw = execute("siwe_smoke", (node_path, os.fspath(smoke_path))).stdout
        smoke_result = _strict_smoke_result(smoke_raw)
        local_after, _ = _scan_tree(
            local_cache,
            max_entries=plan.resource_bounds.max_workspace_entries,
            max_bytes=plan.resource_bounds.max_workspace_bytes,
            max_file_bytes=plan.resource_bounds.max_file_bytes,
            require_read_only=False,
        )
        if time.monotonic() >= deadline:
            _fail("SIWE bootstrap exceeded the whole-run timeout")
        for seal in seals:
            _revalidate_seal(seal)

        boundary = {
            "namespace": plan.network_boundary.namespace,
            "apparmor_profile": plan.network_boundary.apparmor_profile,
            "interfaces": ["lo"],
            "no_external_route": True,
            "network_deny_canary_sha256": plan.network_boundary.network_deny_canary_sha256,
            "egress_policy_sha256": plan.network_boundary.egress_policy_sha256,
        }
        receipt = {
            "schema_version": RECEIPT_SCHEMA,
            "goal_id": GOAL_ID,
            "status": "passed",
            "completed_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "valid_until": plan.expires_at,
            "offline": True,
            "live_actions_authorized": False,
            "selection_record_id": plan.selection_record_id,
            "selection_approval_sha256": plan.authorization_sha256,
            "real_execution": True,
            "cache_mutated": False,
            "toolchain": {
                "platform": plan.platform,
                "architecture": plan.architecture,
                "archive_sha256": plan.toolchain_archive_sha256,
                "node_sha256": plan.node.sha256,
                "node_version": plan.node.version,
                "npm_cli_sha256": plan.npm_cli.sha256,
                "npm_version": plan.npm_cli.version,
            },
            "inputs": {
                "manifest_sha256": plan.manifest.sha256,
                "lock_sha256": plan.lockfile.sha256,
                "adapter_sha256": plan.adapter.sha256,
            },
            "cache": {
                "reviewed_before_sha256": plan.cache.tree_sha256,
                "reviewed_after_sha256": plan.cache.tree_sha256,
                "local_before_sha256": local_before,
                "local_after_sha256": local_after,
            },
            "network": {
                "enforcement": "signed-namespace-plus-apparmor",
                "attempt_monitor": "not-configured",
                "attempt_count": None,
                "external_network_succeeded": False,
                "boundary_before": boundary,
                "boundary_after": dict(boundary),
            },
            "smoke_result": smoke_result,
        }
        # Retained only in the return value until the strict receipt schema can
        # evolve; the v2 file remains exactly Gate-compatible.
        _ = command_summaries, execution_plan_sha256(plan), plan.network_boundary.attestation_sha256
    except BaseException as exc:
        execution_error = exc
    finally:
        if workspace_descriptor >= 0:
            os.close(workspace_descriptor)
        for seal in seals:
            os.close(seal.descriptor)
        if workspace_created:
            try:
                _cleanup_workspace(run_descriptor, workspace_name)
            except BaseException as cleanup_exc:
                if execution_error is None:
                    execution_error = cleanup_exc
                else:
                    execution_error = G038SIWERunnerError(
                        f"SIWE execution failed and cleanup also failed: {cleanup_exc}"
                    )
    try:
        if execution_error is not None:
            raise execution_error
        if receipt is None:
            _fail("SIWE bootstrap produced no receipt")
        _publish_receipt(run_descriptor, run_identity, receipt)
        return receipt
    finally:
        os.close(run_descriptor)


__all__ = [
    "G038SIWERunnerError",
    "GOAL_ID",
    "PLAN_SCHEMA",
    "RECEIPT_NAME",
    "RECEIPT_SCHEMA",
    "SIWEBoundInput",
    "SIWECacheArchive",
    "SIWECacheEntry",
    "SIWEExecutionPlan",
    "SIWENetworkBoundary",
    "SIWEResourceBounds",
    "SIWEToolBinding",
    "cache_tree_sha256",
    "execution_plan_sha256",
    "run_approved_siwe_bootstrap",
]
