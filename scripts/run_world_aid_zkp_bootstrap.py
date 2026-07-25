#!/usr/bin/env python3
"""Fail-closed native smoke execution for the future WORLDCOIN-G039 launcher.

This module is an execution primitive, not an authorization primitive.  Its
caller must be the operator-controlled Gate-first launcher and must supply an
immutable plan whose approval and deny-all network-boundary attestations were
already authenticated outside repository Python.  There is intentionally no
CLI, environment-variable authority, backend selection, download path, or
package-manager fallback here.

The runtime fence in ``tests/world_aid/test_zkp_toolchain_bootstrap.py`` remains
closed.  A future launcher can inject a verified ``NativeSmokeExecutionPlan``
into ``run_approved_native_smoke`` after it has established the signed Gate
selection and the external deny-all execution boundary.
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
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Final

PLAN_SCHEMA: Final = "world-human-aid-g039-native-smoke-plan/v1"
RECEIPT_SCHEMA: Final = "world-human-aid-g039-native-smoke-receipt/v1"
RECEIPT_NAME: Final = "g039-native-smoke-receipt.json"
GOAL_ID: Final = "WORLDCOIN-G039"

_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_ENV_KEY_RE = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")
_PLACEHOLDER_RE = re.compile(r"\{[a-z_]+\}")
_MAX_ARGV_ITEMS = 128
_MAX_ARG_BYTES = 128 * 1024
_MAX_ENV_ITEMS = 64
_MAX_ENV_BYTES = 64 * 1024
_MAX_INPUTS = 32
_MAX_INPUT_BYTES = 1024 * 1024 * 1024
_MAX_TOOL_BYTES = 4 * 1024 * 1024 * 1024
_READ_CHUNK = 64 * 1024
_FIXED_NOFILE_LIMIT = 64

_REQUIRED_OFFLINE_ENV: Final[dict[str, str]] = {
    "CARGO_NET_OFFLINE": "true",
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_TERMINAL_PROMPT": "0",
    "HOME": "",  # Replaced with a command-private directory.
    "LANG": "C",
    "LC_ALL": "C",
    "NPM_CONFIG_OFFLINE": "true",
    "PIP_DISABLE_PIP_VERSION_CHECK": "1",
    "PIP_NO_INDEX": "1",
    "PYTHONHASHSEED": "0",
    "SOURCE_DATE_EPOCH": "0",
    "TMPDIR": "",  # Replaced with a command-private directory.
    "TZ": "UTC",
    "http_proxy": "",
    "https_proxy": "",
    "no_proxy": "*",
}
_RESERVED_ENV_KEYS = frozenset(_REQUIRED_OFFLINE_ENV) | {
    "ALL_PROXY",
    "BASH_ENV",
    "CDPATH",
    "ENV",
    "GIT_CONFIG",
    "GIT_CONFIG_GLOBAL",
    "GIT_CONFIG_SYSTEM",
    "IFS",
    "PATH",
    "PYTHONHOME",
    "PYTHONPATH",
    "SHELL",
}
_RESERVED_ENV_PREFIXES = (
    "CARGO_",
    "DYLD_",
    "GIT_",
    "HTTP_",
    "HTTPS_",
    "LD_",
    "NPM_",
    "PIP_",
    "RUSTUP_",
    "WORLD_AID_G039_",
)
_FORBIDDEN_ARG_TOKENS = frozenset(
    {
        "curl",
        "download",
        "fetch",
        "install",
        "npm",
        "pip",
        "pip3",
        "update",
        "wget",
    }
)
_FORBIDDEN_ARG_PREFIXES = (
    "--allow-network",
    "--index-url",
    "--network",
    "--online",
    "--proxy",
    "--registry",
    "--repository",
)
_FORBIDDEN_URI_MARKERS = (
    "ftp://",
    "git://",
    "http://",
    "https://",
    "ssh://",
)


class G039NativeSmokeError(RuntimeError):
    """Raised whenever the native smoke cannot produce trustworthy evidence."""


@dataclass(frozen=True, slots=True)
class NativeSmokeResourceBounds:
    """Signed bounds copied into the already-verified execution plan."""

    max_seconds: int
    max_memory_mb: int
    max_output_bytes: int

    def __post_init__(self) -> None:
        _require_plain_int("resource_bounds.max_seconds", self.max_seconds, 1, 3600)
        _require_plain_int("resource_bounds.max_memory_mb", self.max_memory_mb, 64, 65536)
        _require_plain_int(
            "resource_bounds.max_output_bytes",
            self.max_output_bytes,
            1,
            1024 * 1024 * 1024,
        )


@dataclass(frozen=True, slots=True)
class NativeSmokeInput:
    """One approval-bound file copied from a sealed descriptor into each workspace."""

    source_path: Path
    sha256: str
    max_bytes: int
    workspace_relative_path: str

    def __post_init__(self) -> None:
        if not isinstance(self.source_path, Path) or not self.source_path.is_absolute():
            _fail("input source_path must be an absolute pathlib.Path")
        if "\x00" in os.fspath(self.source_path) or ".." in self.source_path.parts:
            _fail("input source_path must be normalized and traversal-free")
        _require_digest("input sha256", self.sha256)
        _require_plain_int("input max_bytes", self.max_bytes, 1, _MAX_INPUT_BYTES)
        _validate_relative_output(self.workspace_relative_path, "input workspace_relative_path")


@dataclass(frozen=True, slots=True)
class NativeSmokeExecutionPlan:
    """Immutable handoff produced only after external Gate-first verification.

    ``authorization_sha256`` binds the authenticated authorization object.
    ``network_boundary_sha256`` binds the launcher-owned deny-all boundary
    attestation.  This runner records those bindings but deliberately does not
    attempt to mint or discover either authority itself.
    """

    schema_version: str
    goal_id: str
    authorization_sha256: str
    network_boundary_sha256: str
    network_policy: str
    tool_path: Path
    tool_sha256: str
    tool_max_bytes: int
    build_a_argv: tuple[str, ...]
    build_b_argv: tuple[str, ...]
    prove_argv: tuple[str, ...]
    verify_argv: tuple[str, ...]
    fixed_env: tuple[tuple[str, str], ...]
    inputs: tuple[NativeSmokeInput, ...]
    resource_bounds: NativeSmokeResourceBounds
    artifact_relative_path: str
    proof_relative_path: str
    expires_at: str

    def __post_init__(self) -> None:
        if self.schema_version != PLAN_SCHEMA:
            _fail(f"schema_version must be {PLAN_SCHEMA!r}")
        if self.goal_id != GOAL_ID:
            _fail(f"goal_id must be {GOAL_ID!r}")
        _require_digest("authorization_sha256", self.authorization_sha256)
        _require_digest("network_boundary_sha256", self.network_boundary_sha256)
        _require_digest("tool_sha256", self.tool_sha256)
        _require_plain_int("tool_max_bytes", self.tool_max_bytes, 1, _MAX_TOOL_BYTES)
        if self.network_policy != "external-deny-all":
            _fail("network_policy must be exactly 'external-deny-all'")
        if not isinstance(self.tool_path, Path) or not self.tool_path.is_absolute():
            _fail("tool_path must be an absolute pathlib.Path")
        if "\x00" in os.fspath(self.tool_path) or ".." in self.tool_path.parts:
            _fail("tool_path must be a normalized absolute path without traversal")
        if not isinstance(self.resource_bounds, NativeSmokeResourceBounds):
            _fail("resource_bounds must be NativeSmokeResourceBounds")
        _validate_inputs(self.inputs)
        _validate_relative_output(self.artifact_relative_path, "artifact_relative_path")
        _validate_relative_output(self.proof_relative_path, "proof_relative_path")
        _validate_argv(
            self.build_a_argv,
            "build_a_argv",
            {"tool", "work_dir", "input_root", "artifact"},
            {"tool", "input_root", "artifact"},
        )
        _validate_argv(
            self.build_b_argv,
            "build_b_argv",
            {"tool", "work_dir", "input_root", "artifact"},
            {"tool", "input_root", "artifact"},
        )
        _validate_argv(
            self.prove_argv,
            "prove_argv",
            {"tool", "work_dir", "input_root", "artifact", "proof"},
            {"tool", "input_root", "artifact", "proof"},
        )
        _validate_argv(
            self.verify_argv,
            "verify_argv",
            {"tool", "work_dir", "input_root", "artifact", "proof"},
            {"tool", "input_root", "artifact", "proof"},
        )
        _validate_fixed_env(self.fixed_env)
        _parse_expiry(self.expires_at)


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


@dataclass(frozen=True, slots=True)
class _SealedInput:
    binding: NativeSmokeInput
    descriptor: int
    metadata: tuple[int, ...]


def _fail(message: str) -> None:
    raise G039NativeSmokeError(message)


def _require_plain_int(name: str, value: object, minimum: int, maximum: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        _fail(f"{name} must be an integer from {minimum} through {maximum}")


def _require_digest(name: str, value: object) -> None:
    if not isinstance(value, str) or _DIGEST_RE.fullmatch(value) is None:
        _fail(f"{name} must be a lowercase sha256 digest")


def _validate_relative_output(value: object, name: str) -> None:
    if not isinstance(value, str) or not value or len(value.encode("utf-8")) > 4096:
        _fail(f"{name} must be a non-empty bounded POSIX relative path")
    if "\x00" in value or "\\" in value:
        _fail(f"{name} contains a forbidden path character")
    path = PurePosixPath(value)
    if path.is_absolute() or path.as_posix() != value or any(part in {"", ".", ".."} for part in path.parts):
        _fail(f"{name} must be a normalized POSIX relative path without traversal")


def _validate_inputs(inputs: object) -> None:
    if not isinstance(inputs, tuple) or not 1 <= len(inputs) <= _MAX_INPUTS:
        _fail(f"inputs must be a non-empty tuple with at most {_MAX_INPUTS} entries")
    source_paths: list[Path] = []
    destinations: list[PurePosixPath] = []
    total_max_bytes = 0
    for index, binding in enumerate(inputs):
        if not isinstance(binding, NativeSmokeInput):
            _fail(f"inputs[{index}] must be NativeSmokeInput")
        source_paths.append(binding.source_path)
        destinations.append(PurePosixPath(binding.workspace_relative_path))
        total_max_bytes += binding.max_bytes
    if len(source_paths) != len(set(source_paths)):
        _fail("input source paths must be unique")
    if total_max_bytes > _MAX_INPUT_BYTES:
        _fail(f"combined input max_bytes exceeds {_MAX_INPUT_BYTES}")
    for index, destination in enumerate(destinations):
        for other in destinations[index + 1 :]:
            if destination == other or destination in other.parents or other in destination.parents:
                _fail("input workspace destinations must be unique and non-overlapping")


def _validate_argv(
    argv: object,
    name: str,
    allowed_placeholders: set[str],
    required_placeholders: set[str],
) -> None:
    if not isinstance(argv, tuple) or not argv or len(argv) > _MAX_ARGV_ITEMS:
        _fail(f"{name} must be a non-empty tuple with at most {_MAX_ARGV_ITEMS} entries")
    if argv[0] != "{tool}":
        _fail(f"{name}[0] must be exactly '{{tool}}'")
    total_bytes = 0
    observed_placeholders: set[str] = set()
    for index, argument in enumerate(argv):
        if not isinstance(argument, str) or not argument or "\x00" in argument:
            _fail(f"{name}[{index}] must be a non-empty NUL-free string")
        total_bytes += len(argument.encode("utf-8"))
        lowered = argument.lower()
        if any(marker in lowered for marker in _FORBIDDEN_URI_MARKERS):
            _fail(f"{name}[{index}] contains a network URI")
        normalized = lowered.lstrip("-").split("=", 1)[0]
        if normalized in _FORBIDDEN_ARG_TOKENS or any(
            lowered == prefix or lowered.startswith(prefix + "=") for prefix in _FORBIDDEN_ARG_PREFIXES
        ):
            _fail(f"{name}[{index}] requests network or download behavior")
        if index > 0 and "{tool}" in argument:
            _fail(f"{name}[{index}] may not reference the tool descriptor")
        if re.search(r"(^|[^A-Za-z0-9_.-])\.\.($|[/])", argument):
            _fail(f"{name}[{index}] contains path traversal")
        without_placeholders = _PLACEHOLDER_RE.sub("BOUND", argument)
        if without_placeholders.startswith("/") or re.search(
            r"[^A-Za-z0-9_.-]/",
            without_placeholders,
        ):
            _fail(f"{name}[{index}] contains an arbitrary absolute path")
        for match in _PLACEHOLDER_RE.finditer(argument):
            placeholder = match.group(0)
            placeholder_name = placeholder[1:-1]
            if placeholder_name not in allowed_placeholders:
                _fail(f"{name}[{index}] contains unsupported placeholder {placeholder!r}")
            observed_placeholders.add(placeholder_name)
            if placeholder_name != "tool":
                start, end = match.span()
                if (start and argument[start - 1] not in {"=", ":"}) or (end < len(argument) and argument[end] != "/"):
                    _fail(f"{name}[{index}] uses {placeholder!r} outside a path boundary")
        residue = _PLACEHOLDER_RE.sub("", argument)
        if "{" in residue or "}" in residue:
            _fail(f"{name}[{index}] contains malformed placeholder syntax")
    if total_bytes > _MAX_ARG_BYTES:
        _fail(f"{name} exceeds the {_MAX_ARG_BYTES}-byte limit")
    missing_placeholders = required_placeholders - observed_placeholders
    if missing_placeholders:
        _fail(f"{name} is missing required placeholders: {sorted(missing_placeholders)}")


def _validate_fixed_env(fixed_env: object) -> None:
    if not isinstance(fixed_env, tuple) or len(fixed_env) > _MAX_ENV_ITEMS:
        _fail(f"fixed_env must be a tuple with at most {_MAX_ENV_ITEMS} entries")
    keys: list[str] = []
    total_bytes = 0
    for index, item in enumerate(fixed_env):
        if not isinstance(item, tuple) or len(item) != 2:
            _fail(f"fixed_env[{index}] must be a (key, value) tuple")
        key, value = item
        if not isinstance(key, str) or _ENV_KEY_RE.fullmatch(key) is None:
            _fail(f"fixed_env[{index}] has an invalid key")
        if key in _RESERVED_ENV_KEYS or any(key.startswith(prefix) for prefix in _RESERVED_ENV_PREFIXES):
            _fail(f"fixed_env[{index}] attempts to override runner-controlled key {key!r}")
        if not isinstance(value, str) or "\x00" in value:
            _fail(f"fixed_env[{index}] value must be a NUL-free string")
        if any(marker in value.lower() for marker in _FORBIDDEN_URI_MARKERS):
            _fail(f"fixed_env[{index}] contains a network URI")
        keys.append(key)
        total_bytes += len(key.encode("utf-8")) + len(value.encode("utf-8"))
    if len(keys) != len(set(keys)):
        _fail("fixed_env keys must be unique")
    if keys != sorted(keys):
        _fail("fixed_env keys must be sorted")
    if total_bytes > _MAX_ENV_BYTES:
        _fail(f"fixed_env exceeds the {_MAX_ENV_BYTES}-byte limit")


def _parse_expiry(value: object) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        _fail("expires_at must be an RFC 3339 UTC timestamp ending in Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise G039NativeSmokeError("expires_at is not a valid RFC 3339 timestamp") from exc
    if parsed.tzinfo != UTC or parsed.isoformat(timespec="seconds").replace("+00:00", "Z") != value:
        _fail("expires_at must use canonical second-precision UTC form")
    return parsed


def _require_unexpired(plan: NativeSmokeExecutionPlan) -> None:
    if datetime.now(UTC) >= _parse_expiry(plan.expires_at):
        _fail("the immutable G039 execution plan has expired")


def _require_within_execution_deadline(deadline: float, max_seconds: int) -> None:
    if time.monotonic() >= deadline:
        _fail(f"native smoke exceeded the {max_seconds}-second approved wall-clock bound")


def _canonical_json_bytes(payload: object) -> bytes:
    return (json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def _plan_payload(plan: NativeSmokeExecutionPlan) -> dict[str, object]:
    return {
        "schema_version": plan.schema_version,
        "goal_id": plan.goal_id,
        "authorization_sha256": plan.authorization_sha256,
        "network_boundary_sha256": plan.network_boundary_sha256,
        "network_policy": plan.network_policy,
        "tool_path": os.fspath(plan.tool_path),
        "tool_sha256": plan.tool_sha256,
        "tool_max_bytes": plan.tool_max_bytes,
        "build_a_argv": list(plan.build_a_argv),
        "build_b_argv": list(plan.build_b_argv),
        "prove_argv": list(plan.prove_argv),
        "verify_argv": list(plan.verify_argv),
        "fixed_env": [[key, value] for key, value in plan.fixed_env],
        "inputs": [
            {
                "source_path": os.fspath(binding.source_path),
                "sha256": binding.sha256,
                "max_bytes": binding.max_bytes,
                "workspace_relative_path": binding.workspace_relative_path,
            }
            for binding in plan.inputs
        ],
        "resource_bounds": {
            "max_seconds": plan.resource_bounds.max_seconds,
            "max_memory_mb": plan.resource_bounds.max_memory_mb,
            "max_output_bytes": plan.resource_bounds.max_output_bytes,
        },
        "artifact_relative_path": plan.artifact_relative_path,
        "proof_relative_path": plan.proof_relative_path,
        "expires_at": plan.expires_at,
    }


def execution_plan_sha256(plan: NativeSmokeExecutionPlan) -> str:
    """Return the canonical digest a trusted launcher can bind in its seal."""

    return "sha256:" + hashlib.sha256(_canonical_json_bytes(_plan_payload(plan))).hexdigest()


def _metadata_snapshot(metadata: os.stat_result) -> tuple[int, ...]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
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
        raise G039NativeSmokeError(f"cannot open {context} without following symlinks: {exc}") from exc


def _open_tool(plan: NativeSmokeExecutionPlan) -> tuple[int, tuple[int, ...]]:
    parent_descriptor = _open_directory_without_symlinks(plan.tool_path.parent, "tool_path parent")
    descriptor = -1
    try:
        descriptor = os.open(
            plan.tool_path.name,
            os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0),
            dir_fd=parent_descriptor,
        )
    except OSError as exc:
        raise G039NativeSmokeError(f"cannot open tool_path without following symlinks: {exc}") from exc
    finally:
        os.close(parent_descriptor)
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            _fail("tool_path must identify a regular file")
        if metadata.st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH):
            _fail("tool_path must be mode-immutable before execution")
        if metadata.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH) == 0:
            _fail("tool_path is not executable")
        observed = _hash_open_file(descriptor, plan.tool_max_bytes)
        if observed != plan.tool_sha256:
            _fail(f"tool_path digest mismatch: expected {plan.tool_sha256}, observed {observed}")
        proc_path = Path(f"/proc/self/fd/{descriptor}")
        if not proc_path.exists():
            _fail("descriptor-pinned execution requires /proc/self/fd")
        return descriptor, _metadata_snapshot(metadata)
    except BaseException:
        os.close(descriptor)
        raise


def _hash_open_file(descriptor: int, max_bytes: int) -> str:
    before = os.fstat(descriptor)
    if not stat.S_ISREG(before.st_mode):
        _fail("evidence path is not a regular file")
    if before.st_size > max_bytes:
        _fail("evidence file exceeds the approved byte bound")
    digest = hashlib.sha256()
    observed_bytes = 0
    os.lseek(descriptor, 0, os.SEEK_SET)
    while chunk := os.read(descriptor, _READ_CHUNK):
        observed_bytes += len(chunk)
        if observed_bytes > max_bytes:
            _fail("evidence file exceeds the approved byte bound")
        digest.update(chunk)
    after = os.fstat(descriptor)
    if _metadata_snapshot(before) != _metadata_snapshot(after):
        _fail("evidence file changed while being hashed")
    return "sha256:" + digest.hexdigest()


def _verify_tool_path_still_pinned(
    plan: NativeSmokeExecutionPlan,
    pinned_descriptor: int,
    pinned_metadata: tuple[int, ...],
) -> None:
    if _metadata_snapshot(os.fstat(pinned_descriptor)) != pinned_metadata:
        _fail("pinned tool changed during G039 execution")
    parent_descriptor = _open_directory_without_symlinks(plan.tool_path.parent, "tool_path parent")
    reopened = -1
    try:
        reopened = os.open(
            plan.tool_path.name,
            os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0),
            dir_fd=parent_descriptor,
        )
        if _metadata_snapshot(os.fstat(reopened)) != pinned_metadata:
            _fail("tool_path no longer identifies the pinned executable")
        if _hash_open_file(reopened, plan.tool_max_bytes) != plan.tool_sha256:
            _fail("tool_path digest changed during G039 execution")
    except OSError as exc:
        raise G039NativeSmokeError(f"cannot revalidate tool_path: {exc}") from exc
    finally:
        if reopened >= 0:
            os.close(reopened)
        os.close(parent_descriptor)


def _open_input(binding: NativeSmokeInput) -> _SealedInput:
    parent_descriptor = _open_directory_without_symlinks(binding.source_path.parent, "input source parent")
    descriptor = -1
    try:
        descriptor = os.open(
            binding.source_path.name,
            os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0),
            dir_fd=parent_descriptor,
        )
    except OSError as exc:
        raise G039NativeSmokeError(
            f"cannot open input {binding.workspace_relative_path!r} without following symlinks: {exc}"
        ) from exc
    finally:
        os.close(parent_descriptor)
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            _fail(f"input {binding.workspace_relative_path!r} must be a regular file")
        observed = _hash_open_file(descriptor, binding.max_bytes)
        if observed != binding.sha256:
            _fail(
                f"input {binding.workspace_relative_path!r} digest mismatch: "
                f"expected {binding.sha256}, observed {observed}"
            )
        return _SealedInput(
            binding=binding,
            descriptor=descriptor,
            metadata=_metadata_snapshot(metadata),
        )
    except BaseException:
        os.close(descriptor)
        raise


def _open_inputs(plan: NativeSmokeExecutionPlan) -> tuple[_SealedInput, ...]:
    sealed: list[_SealedInput] = []
    try:
        for binding in plan.inputs:
            sealed.append(_open_input(binding))
        return tuple(sealed)
    except BaseException:
        for item in sealed:
            os.close(item.descriptor)
        raise


def _verify_input_still_pinned(item: _SealedInput) -> None:
    binding = item.binding
    if _metadata_snapshot(os.fstat(item.descriptor)) != item.metadata:
        _fail(f"sealed input {binding.workspace_relative_path!r} changed during execution")
    if _hash_open_file(item.descriptor, binding.max_bytes) != binding.sha256:
        _fail(f"sealed input {binding.workspace_relative_path!r} digest drifted during execution")
    parent_descriptor = _open_directory_without_symlinks(binding.source_path.parent, "input source parent")
    reopened = -1
    try:
        reopened = os.open(
            binding.source_path.name,
            os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0),
            dir_fd=parent_descriptor,
        )
        if _metadata_snapshot(os.fstat(reopened)) != item.metadata:
            _fail(f"input source path {binding.workspace_relative_path!r} no longer identifies its seal")
        if _hash_open_file(reopened, binding.max_bytes) != binding.sha256:
            _fail(f"input source path {binding.workspace_relative_path!r} digest drifted")
    except OSError as exc:
        raise G039NativeSmokeError(
            f"cannot revalidate input source {binding.workspace_relative_path!r}: {exc}"
        ) from exc
    finally:
        if reopened >= 0:
            os.close(reopened)
        os.close(parent_descriptor)


def _verify_inputs_still_pinned(inputs: tuple[_SealedInput, ...]) -> None:
    for item in inputs:
        _verify_input_still_pinned(item)


def _copy_sealed_input(item: _SealedInput, input_root: Path) -> None:
    binding = item.binding
    destination = input_root.joinpath(*PurePosixPath(binding.workspace_relative_path).parts)
    destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    destination_descriptor = -1
    try:
        destination_descriptor = os.open(
            destination,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0),
            0o600,
        )
        source_before = os.fstat(item.descriptor)
        if _metadata_snapshot(source_before) != item.metadata:
            _fail(f"sealed input {binding.workspace_relative_path!r} changed before materialization")
        os.lseek(item.descriptor, 0, os.SEEK_SET)
        digest = hashlib.sha256()
        copied = 0
        while chunk := os.read(item.descriptor, _READ_CHUNK):
            copied += len(chunk)
            if copied > binding.max_bytes:
                _fail(f"sealed input {binding.workspace_relative_path!r} exceeds its byte bound")
            digest.update(chunk)
            offset = 0
            while offset < len(chunk):
                offset += os.write(destination_descriptor, chunk[offset:])
        if "sha256:" + digest.hexdigest() != binding.sha256:
            _fail(f"sealed input {binding.workspace_relative_path!r} changed while being copied")
        if _metadata_snapshot(os.fstat(item.descriptor)) != item.metadata:
            _fail(f"sealed input {binding.workspace_relative_path!r} changed while being copied")
        os.fchmod(destination_descriptor, 0o444)
        os.fsync(destination_descriptor)
    except OSError as exc:
        raise G039NativeSmokeError(
            f"cannot materialize sealed input {binding.workspace_relative_path!r}: {exc}"
        ) from exc
    finally:
        if destination_descriptor >= 0:
            os.close(destination_descriptor)


def _materialize_inputs(inputs: tuple[_SealedInput, ...], work_dir: Path) -> Path:
    input_root = work_dir / "inputs"
    input_root.mkdir(mode=0o700)
    for item in inputs:
        _copy_sealed_input(item, input_root)
    return input_root


def _verify_materialized_inputs(inputs: tuple[_SealedInput, ...], input_root: Path) -> None:
    for item in inputs:
        binding = item.binding
        descriptor = _open_relative_regular_file(
            input_root,
            binding.workspace_relative_path,
            binding.max_bytes,
            f"materialized input {binding.workspace_relative_path!r}",
        )
        try:
            metadata = os.fstat(descriptor)
            if metadata.st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH):
                _fail(f"materialized input {binding.workspace_relative_path!r} became writable")
            if _hash_open_file(descriptor, binding.max_bytes) != binding.sha256:
                _fail(f"materialized input {binding.workspace_relative_path!r} digest drifted")
        finally:
            os.close(descriptor)


def _open_relative_regular_file(root: Path, relative: str, max_bytes: int, context: str) -> int:
    root_descriptor = _open_directory_without_symlinks(root, f"{context} root")
    descriptor = root_descriptor
    try:
        parts = PurePosixPath(relative).parts
        for component in parts[:-1]:
            child = os.open(
                component,
                os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=descriptor,
            )
            if descriptor != root_descriptor:
                os.close(descriptor)
            descriptor = child
        file_descriptor = os.open(
            parts[-1],
            os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0),
            dir_fd=descriptor,
        )
        metadata = os.fstat(file_descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            os.close(file_descriptor)
            _fail(f"{context} must be a regular file")
        if metadata.st_size > max_bytes:
            os.close(file_descriptor)
            _fail(f"{context} exceeds the approved byte bound")
        return file_descriptor
    except OSError as exc:
        raise G039NativeSmokeError(f"cannot open {context} without following symlinks: {exc}") from exc
    finally:
        if descriptor != root_descriptor:
            os.close(descriptor)
        os.close(root_descriptor)


def _hash_relative_file(root: Path, relative: str, max_bytes: int, context: str) -> str:
    descriptor = _open_relative_regular_file(root, relative, max_bytes, context)
    try:
        return _hash_open_file(descriptor, max_bytes)
    finally:
        os.close(descriptor)


def _expand_argv(
    template: tuple[str, ...],
    *,
    tool_descriptor: int,
    work_dir: Path,
    input_root: Path,
    artifact: Path,
    proof: Path,
) -> tuple[str, ...]:
    replacements = {
        "{tool}": f"/proc/self/fd/{tool_descriptor}",
        "{work_dir}": os.fspath(work_dir),
        "{input_root}": os.fspath(input_root),
        "{artifact}": os.fspath(artifact),
        "{proof}": os.fspath(proof),
    }
    expanded: list[str] = []
    for argument in template:
        value = argument
        for placeholder, replacement in replacements.items():
            value = value.replace(placeholder, replacement)
        if "{" in value or "}" in value or "\x00" in value:
            _fail("argv expansion produced an invalid argument")
        expanded.append(value)
    return tuple(expanded)


def _bounded_rlimit(kind: int, requested: int) -> tuple[int, int]:
    _, current_hard = resource.getrlimit(kind)
    effective = requested if current_hard == resource.RLIM_INFINITY else min(requested, current_hard)
    return effective, effective


def _resource_limiter(bounds: NativeSmokeResourceBounds):
    def apply_limits() -> None:
        os.umask(0o077)
        memory_bytes = bounds.max_memory_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        resource.setrlimit(resource.RLIMIT_CPU, _bounded_rlimit(resource.RLIMIT_CPU, bounds.max_seconds))
        resource.setrlimit(resource.RLIMIT_AS, _bounded_rlimit(resource.RLIMIT_AS, memory_bytes))
        resource.setrlimit(
            resource.RLIMIT_FSIZE,
            _bounded_rlimit(resource.RLIMIT_FSIZE, bounds.max_output_bytes),
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
        process.wait(timeout=1)
    except subprocess.TimeoutExpired:
        _fail("unable to reap bounded native process group")


def _run_command(
    *,
    argv: tuple[str, ...],
    work_dir: Path,
    environment: dict[str, str],
    bounds: NativeSmokeResourceBounds,
    tool_descriptor: int,
    command_name: str,
    execution_deadline: float,
    output_byte_limit: int,
) -> _CommandEvidence:
    if time.monotonic() >= execution_deadline:
        _fail(f"{command_name} cannot start after the approved wall-clock bound")
    if output_byte_limit <= 0:
        _fail(f"{command_name} cannot start after exhausting the approved output bound")
    started = time.monotonic()
    try:
        process = subprocess.Popen(
            argv,
            cwd=work_dir,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            close_fds=True,
            pass_fds=(tool_descriptor,),
            start_new_session=True,
            preexec_fn=_resource_limiter(bounds),
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise G039NativeSmokeError(f"{command_name} could not start: {exc}") from exc

    streams = {
        process.stdout: (hashlib.sha256(), 0),
        process.stderr: (hashlib.sha256(), 0),
    }
    selector = selectors.DefaultSelector()
    for stream in streams:
        if stream is None:
            _terminate_process_group(process)
            _fail(f"{command_name} output pipe was not created")
        os.set_blocking(stream.fileno(), False)
        selector.register(stream, selectors.EVENT_READ)
    failure: G039NativeSmokeError | None = None
    try:
        while selector.get_map():
            remaining = execution_deadline - time.monotonic()
            if remaining <= 0:
                failure = G039NativeSmokeError(
                    f"{command_name} exceeded the {bounds.max_seconds}-second approved wall-clock bound"
                )
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
                digest, size = streams[stream]
                size += len(chunk)
                streams[stream] = (digest, size)
                if sum(item[1] for item in streams.values()) > output_byte_limit:
                    failure = G039NativeSmokeError(
                        f"{command_name} exceeded the remaining {output_byte_limit}-byte approved output bound"
                    )
                    break
                digest.update(chunk)
            if failure is not None:
                break
        if failure is None:
            remaining = max(0.0, execution_deadline - time.monotonic())
            try:
                return_code = process.wait(timeout=remaining)
            except subprocess.TimeoutExpired:
                failure = G039NativeSmokeError(
                    f"{command_name} exceeded the {bounds.max_seconds}-second approved wall-clock bound"
                )
            else:
                if return_code != 0:
                    failure = G039NativeSmokeError(f"{command_name} failed with exit code {return_code}")
    finally:
        selector.close()
        for stream in streams:
            if stream is not None:
                stream.close()
        _terminate_process_group(process)
    if failure is not None:
        raise failure
    stdout_digest, stdout_size = streams[process.stdout]
    stderr_digest, stderr_size = streams[process.stderr]
    return _CommandEvidence(
        exit_code=0,
        elapsed_ms=max(0, math.ceil((time.monotonic() - started) * 1000)),
        stdout_sha256="sha256:" + stdout_digest.hexdigest(),
        stdout_bytes=stdout_size,
        stderr_sha256="sha256:" + stderr_digest.hexdigest(),
        stderr_bytes=stderr_size,
    )


def _command_environment(plan: NativeSmokeExecutionPlan, work_dir: Path) -> dict[str, str]:
    environment = {key: value for key, value in _REQUIRED_OFFLINE_ENV.items() if key not in {"HOME", "TMPDIR"}}
    environment["PATH"] = "/nonexistent"
    environment.update(dict(plan.fixed_env))
    home = work_dir / "home"
    temporary = work_dir / "tmp"
    home.mkdir(mode=0o700)
    temporary.mkdir(mode=0o700)
    environment["HOME"] = os.fspath(home)
    environment["TMPDIR"] = os.fspath(temporary)
    return environment


def _ensure_output_parent(work_dir: Path, relative: str) -> Path:
    output = work_dir.joinpath(*PurePosixPath(relative).parts)
    output.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    return output


def _validate_run_directory(run_directory: Path) -> tuple[int, tuple[int, ...]]:
    if not isinstance(run_directory, Path) or not run_directory.is_absolute():
        _fail("run_directory must be an absolute pathlib.Path")
    descriptor = _open_directory_without_symlinks(run_directory, "run_directory")
    metadata = os.fstat(descriptor)
    if not stat.S_ISDIR(metadata.st_mode):
        os.close(descriptor)
        _fail("run_directory must be a directory")
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
        raise G039NativeSmokeError(f"cannot inspect receipt destination: {exc}") from exc
    else:
        os.close(descriptor)
        _fail(f"receipt destination already exists: {RECEIPT_NAME}")
    return descriptor, (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_uid,
    )


def _publish_receipt(run_descriptor: int, run_metadata: tuple[int, ...], payload: dict[str, object]) -> None:
    current = os.fstat(run_descriptor)
    if (current.st_dev, current.st_ino, current.st_mode, current.st_uid) != run_metadata:
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
        temporary_identity = (temporary_metadata.st_dev, temporary_metadata.st_ino)
        os.link(
            temporary_name,
            RECEIPT_NAME,
            src_dir_fd=run_descriptor,
            dst_dir_fd=run_descriptor,
            follow_symlinks=False,
        )
        linked_identity = temporary_identity
        published_metadata = os.stat(RECEIPT_NAME, dir_fd=run_descriptor, follow_symlinks=False)
        published_identity = (published_metadata.st_dev, published_metadata.st_ino)
        if published_identity != temporary_identity or not stat.S_ISREG(published_metadata.st_mode):
            _fail("published receipt does not identify the pinned temporary file")
        os.fsync(run_descriptor)
    except FileExistsError as exc:
        publication_error = G039NativeSmokeError(f"receipt destination already exists: {RECEIPT_NAME}: {exc}")
    except G039NativeSmokeError as exc:
        publication_error = exc
    except OSError as exc:
        publication_error = G039NativeSmokeError(f"cannot publish atomic no-follow receipt: {exc}")
    finally:
        if descriptor >= 0:
            try:
                os.close(descriptor)
            except OSError as exc:
                if publication_error is None:
                    publication_error = G039NativeSmokeError(f"cannot close receipt temporary file: {exc}")
        try:
            os.unlink(temporary_name, dir_fd=run_descriptor)
        except FileNotFoundError:
            pass
        except OSError as exc:
            if publication_error is None:
                publication_error = G039NativeSmokeError(f"cannot remove receipt temporary file: {exc}")
        if publication_error is not None and linked_identity is not None:
            try:
                receipt_metadata = os.stat(
                    RECEIPT_NAME,
                    dir_fd=run_descriptor,
                    follow_symlinks=False,
                )
                if (receipt_metadata.st_dev, receipt_metadata.st_ino) == linked_identity:
                    os.unlink(RECEIPT_NAME, dir_fd=run_descriptor)
                    os.fsync(run_descriptor)
            except FileNotFoundError:
                pass
            except OSError as exc:
                publication_error = G039NativeSmokeError(f"receipt publication failed and rollback also failed: {exc}")
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
        raise G039NativeSmokeError(f"cannot clean native smoke workspace: {exc}") from exc


def run_approved_native_smoke(
    plan: NativeSmokeExecutionPlan,
    *,
    run_directory: Path,
) -> dict[str, object]:
    """Execute an externally authorized, offline G039 plan and publish evidence.

    The caller-owned ``run_directory`` must already exist, be an absolute
    non-symlink directory owned by the effective user, and not contain a prior
    receipt.  All transient build and proof material is removed before the
    receipt is atomically linked into that directory.  Any validation,
    execution, cleanup, or publication failure leaves no successful receipt.
    """

    if not isinstance(plan, NativeSmokeExecutionPlan):
        _fail("plan must be an immutable NativeSmokeExecutionPlan")
    _require_unexpired(plan)
    execution_started = time.monotonic()
    execution_deadline = execution_started + plan.resource_bounds.max_seconds
    remaining_output_bytes = plan.resource_bounds.max_output_bytes
    run_descriptor, run_metadata = _validate_run_directory(run_directory)
    tool_descriptor = -1
    sealed_inputs: tuple[_SealedInput, ...] = ()
    workspace_descriptor = -1
    workspace_name = f".g039-native-smoke.{os.getpid()}.{secrets.token_hex(8)}"
    workspace_created = False
    evidence: dict[str, object] | None = None
    execution_error: BaseException | None = None
    try:
        sealed_inputs = _open_inputs(plan)
        tool_descriptor, tool_metadata = _open_tool(plan)
        os.mkdir(workspace_name, 0o700, dir_fd=run_descriptor)
        workspace_created = True
        workspace_descriptor = os.open(
            workspace_name,
            os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=run_descriptor,
        )
        workspace_root = run_directory / workspace_name
        workspaces = {name: workspace_root / name for name in ("build-a", "build-b", "prove", "verify")}
        for directory in workspaces.values():
            directory.mkdir(mode=0o700)
        input_roots = {name: _materialize_inputs(sealed_inputs, directory) for name, directory in workspaces.items()}
        _verify_inputs_still_pinned(sealed_inputs)
        for input_root in input_roots.values():
            _verify_materialized_inputs(sealed_inputs, input_root)

        artifact_a = _ensure_output_parent(workspaces["build-a"], plan.artifact_relative_path)
        artifact_b = _ensure_output_parent(workspaces["build-b"], plan.artifact_relative_path)
        proof = _ensure_output_parent(workspaces["prove"], plan.proof_relative_path)

        command_evidence: dict[str, dict[str, int | str]] = {}
        command_specs = (
            (
                "build_a",
                plan.build_a_argv,
                workspaces["build-a"],
                input_roots["build-a"],
                artifact_a,
                proof,
            ),
            (
                "build_b",
                plan.build_b_argv,
                workspaces["build-b"],
                input_roots["build-b"],
                artifact_b,
                proof,
            ),
            (
                "prove",
                plan.prove_argv,
                workspaces["prove"],
                input_roots["prove"],
                artifact_a,
                proof,
            ),
            (
                "verify",
                plan.verify_argv,
                workspaces["verify"],
                input_roots["verify"],
                artifact_a,
                proof,
            ),
        )
        artifact_hashes: list[str] = []
        proof_sha256 = ""
        for command_name, template, work_dir, input_root, artifact, proof_path in command_specs:
            _require_unexpired(plan)
            _verify_tool_path_still_pinned(plan, tool_descriptor, tool_metadata)
            _verify_inputs_still_pinned(sealed_inputs)
            for materialized_root in input_roots.values():
                _verify_materialized_inputs(sealed_inputs, materialized_root)
            argv = _expand_argv(
                template,
                tool_descriptor=tool_descriptor,
                work_dir=work_dir,
                input_root=input_root,
                artifact=artifact,
                proof=proof_path,
            )
            observed_command = _run_command(
                argv=argv,
                work_dir=work_dir,
                environment=_command_environment(plan, work_dir),
                bounds=plan.resource_bounds,
                tool_descriptor=tool_descriptor,
                command_name=command_name,
                execution_deadline=execution_deadline,
                output_byte_limit=remaining_output_bytes,
            )
            command_evidence[command_name] = observed_command.as_dict()
            remaining_output_bytes -= observed_command.stdout_bytes + observed_command.stderr_bytes
            _verify_tool_path_still_pinned(plan, tool_descriptor, tool_metadata)
            _verify_inputs_still_pinned(sealed_inputs)
            for materialized_root in input_roots.values():
                _verify_materialized_inputs(sealed_inputs, materialized_root)
            if command_name == "build_a":
                artifact_hashes.append(
                    _hash_relative_file(
                        workspaces["build-a"],
                        plan.artifact_relative_path,
                        plan.resource_bounds.max_output_bytes,
                        "build A artifact",
                    )
                )
            elif command_name == "build_b":
                artifact_hashes.append(
                    _hash_relative_file(
                        workspaces["build-b"],
                        plan.artifact_relative_path,
                        plan.resource_bounds.max_output_bytes,
                        "build B artifact",
                    )
                )
                if artifact_hashes[0] != artifact_hashes[1]:
                    _fail("repeat-build artifact hashes differ")
                if (
                    _hash_relative_file(
                        workspaces["build-a"],
                        plan.artifact_relative_path,
                        plan.resource_bounds.max_output_bytes,
                        "build A artifact",
                    )
                    != artifact_hashes[0]
                ):
                    _fail("build A artifact changed during repeat-build execution")
            elif command_name == "prove":
                proof_sha256 = _hash_relative_file(
                    workspaces["prove"],
                    plan.proof_relative_path,
                    plan.resource_bounds.max_output_bytes,
                    "proof artifact",
                )
                if (
                    _hash_relative_file(
                        workspaces["build-a"],
                        plan.artifact_relative_path,
                        plan.resource_bounds.max_output_bytes,
                        "build A artifact",
                    )
                    != artifact_hashes[0]
                ):
                    _fail("build artifact changed during proof generation")
            elif command_name == "verify":
                if (
                    _hash_relative_file(
                        workspaces["build-a"],
                        plan.artifact_relative_path,
                        plan.resource_bounds.max_output_bytes,
                        "build A artifact",
                    )
                    != artifact_hashes[0]
                ):
                    _fail("build artifact changed during proof verification")
                if (
                    _hash_relative_file(
                        workspaces["prove"],
                        plan.proof_relative_path,
                        plan.resource_bounds.max_output_bytes,
                        "proof artifact",
                    )
                    != proof_sha256
                ):
                    _fail("proof artifact changed during proof verification")
            _require_within_execution_deadline(
                execution_deadline,
                plan.resource_bounds.max_seconds,
            )

        _require_unexpired(plan)
        _require_within_execution_deadline(
            execution_deadline,
            plan.resource_bounds.max_seconds,
        )
        evidence = {
            "schema_version": RECEIPT_SCHEMA,
            "goal_id": GOAL_ID,
            "execution_plan_sha256": execution_plan_sha256(plan),
            "authorization_sha256": plan.authorization_sha256,
            "tool": {
                "path": os.fspath(plan.tool_path),
                "sha256": plan.tool_sha256,
                "max_bytes": plan.tool_max_bytes,
            },
            "inputs": [
                {
                    "source_path": os.fspath(item.binding.source_path),
                    "sha256": item.binding.sha256,
                    "max_bytes": item.binding.max_bytes,
                    "workspace_relative_path": item.binding.workspace_relative_path,
                }
                for item in sealed_inputs
            ],
            "repeat_build_hashes": artifact_hashes,
            "proof_sha256": proof_sha256,
            "proof_result": True,
            "verify_result": True,
            "network_registry_denied": True,
            "network_boundary": {
                "policy": plan.network_policy,
                "attestation_sha256": plan.network_boundary_sha256,
                "authority": "external-gate-first-launcher",
            },
            "resource_bounds": {
                "max_seconds": plan.resource_bounds.max_seconds,
                "max_memory_mb": plan.resource_bounds.max_memory_mb,
                "max_output_bytes": plan.resource_bounds.max_output_bytes,
                "max_open_files": _FIXED_NOFILE_LIMIT,
                "observed_process_output_bytes": (plan.resource_bounds.max_output_bytes - remaining_output_bytes),
            },
            "expiry": plan.expires_at,
            "commands": command_evidence,
            "production_trust": False,
            "completed_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        }
    except BaseException as exc:
        execution_error = exc
    finally:
        if workspace_descriptor >= 0:
            os.close(workspace_descriptor)
        if tool_descriptor >= 0:
            os.close(tool_descriptor)
        for item in sealed_inputs:
            os.close(item.descriptor)
        if workspace_created:
            try:
                _cleanup_workspace(run_descriptor, workspace_name)
            except BaseException as cleanup_exc:
                if execution_error is not None:
                    execution_error = G039NativeSmokeError(
                        f"native smoke failed and workspace cleanup also failed: {cleanup_exc}"
                    )
                else:
                    execution_error = cleanup_exc
    try:
        if execution_error is not None:
            raise execution_error
        if evidence is None:
            _fail("native smoke produced no evidence")
        _publish_receipt(run_descriptor, run_metadata, evidence)
        return evidence
    finally:
        os.close(run_descriptor)


__all__ = [
    "G039NativeSmokeError",
    "NativeSmokeExecutionPlan",
    "NativeSmokeInput",
    "NativeSmokeResourceBounds",
    "PLAN_SCHEMA",
    "RECEIPT_NAME",
    "RECEIPT_SCHEMA",
    "execution_plan_sha256",
    "run_approved_native_smoke",
]
