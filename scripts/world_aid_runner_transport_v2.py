#!/usr/bin/env python3
"""Non-executing v2 transport foundation for the World Aid bootstrap runners.

This module is deliberately separate from the installed, verify-only v1
Gate-first launcher.  It does not parse command-line arguments, discover file
descriptors, grant execution authority, establish a sandbox, or invoke a
runner.  A future independently deployed launcher may use these codecs only
after it has authenticated the Gate selection and established the external
deny-all boundary.

The input codec accepts one canonical JSON object from an inherited anonymous
Linux memfd only when all write/grow/shrink operations and further seal changes
are prohibited.  It reconstructs the exact immutable G038, G039, or G040 plan
type and checks its native plan digest plus approval and boundary bindings.

The output codec wraps one successful G039 or G040 native receipt in a
canonical, binding-complete result.  G038 output is deliberately unavailable:
its frozen receipt schema has no native execution-plan or boundary-attestation
digest, and comparing selected reported fields cannot make it replay-safe.
``CanonicalResultWriter`` consumes a fresh pipe, is one-shot, and writes no
diagnostics to it.  Runner failure is represented by a non-zero process exit
with no result object; this module never turns an exception into apparently
valid evidence.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import stat
import struct
import termios
import unicodedata
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Final, TypeAlias

import scripts.run_world_aid_duckdb_bootstrap as g040
import scripts.run_world_aid_siwe_bootstrap as g038
import scripts.run_world_aid_zkp_bootstrap as g039
import scripts.verify_world_aid_gate_first_receipt as receipt_verifier

TRANSPORT_PROTOCOL_ID: Final = "world-aid-runner-transport/v2"
INPUT_SCHEMA: Final = "world-human-aid-runner-input-envelope/v2"
SEALED_INPUT_PROTOCOL: Final = "sealed-fd-json/v2"
RESULT_SCHEMA: Final = "world-human-aid-runner-result-envelope/v2"
RESULT_PROTOCOL: Final = "stdout-json/v2"
EXPECTED_GOAL_IDS: Final = (
    "WORLDCOIN-G038",
    "WORLDCOIN-G039",
    "WORLDCOIN-G040",
)
RESULT_GOAL_IDS: Final = (
    "WORLDCOIN-G039",
    "WORLDCOIN-G040",
)
MAX_INPUT_BYTES: Final = 8 * 1024 * 1024
MAX_RESULT_BYTES: Final = 8 * 1024 * 1024
MAX_JSON_DEPTH: Final = 24
MAX_JSON_NODES: Final = 250_000
MAX_STRING_BYTES: Final = 256 * 1024

_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_NETWORK_NAMESPACE_RE = re.compile(r"^net:\[[0-9]+\]$")
_REQUIRED_MEMFD_SEALS: Final = (
    getattr(fcntl, "F_SEAL_SEAL", 0x0001)
    | getattr(fcntl, "F_SEAL_SHRINK", 0x0002)
    | getattr(fcntl, "F_SEAL_GROW", 0x0004)
    | getattr(fcntl, "F_SEAL_WRITE", 0x0008)
)
_INPUT_KEYS: Final = {
    "schema_version",
    "protocol",
    "goal_id",
    "approval_sha256",
    "network_boundary_sha256",
    "execution_plan_sha256",
    "plan",
}
_RESULT_KEYS: Final = {
    "schema_version",
    "protocol",
    "goal_id",
    "status",
    "approval_sha256",
    "network_boundary_sha256",
    "execution_plan_sha256",
    "native_receipt_sha256",
    "aggregate_receipt_object_sha256",
    "native_receipt",
}

RunnerPlan: TypeAlias = g038.SIWEExecutionPlan | g039.NativeSmokeExecutionPlan | g040.DuckDBBootstrapPlan


class RunnerTransportV2Error(RuntimeError):
    """Raised whenever a v2 transport condition fails closed."""


def _fail(message: str) -> None:
    raise RunnerTransportV2Error(message)


def _digest(value: object, label: str) -> str:
    if not isinstance(value, str) or _DIGEST_RE.fullmatch(value) is None:
        _fail(f"{label} must be a lowercase sha256 digest")
    return value


def _text(
    value: object,
    label: str,
    *,
    minimum: int = 1,
    maximum_bytes: int = 4096,
) -> str:
    if not isinstance(value, str):
        _fail(f"{label} must be a string")
    try:
        encoded = value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise RunnerTransportV2Error(f"{label} is not valid Unicode") from exc
    if not minimum <= len(encoded) <= maximum_bytes:
        _fail(f"{label} must contain {minimum}..{maximum_bytes} UTF-8 bytes")
    if unicodedata.normalize("NFC", value) != value:
        _fail(f"{label} must use NFC Unicode normalization")
    if any(
        ord(character) < 32 or 0x7F <= ord(character) <= 0x9F or 0xD800 <= ord(character) <= 0xDFFF
        for character in value
    ):
        _fail(f"{label} contains a forbidden control or surrogate character")
    return value


def _plain_int(
    value: object,
    label: str,
    *,
    minimum: int = 0,
    maximum: int = 8 * 1024 * 1024 * 1024,
) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        _fail(f"{label} must be an integer from {minimum} through {maximum}")
    return value


def _object(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail(f"{label} must be a JSON object")
    return value


def _exact_object(
    value: object,
    expected: set[str],
    label: str,
) -> dict[str, Any]:
    result = _object(value, label)
    observed = set(result)
    if observed != expected:
        _fail(f"{label} keys differ: missing={sorted(expected - observed)}, unexpected={sorted(observed - expected)}")
    return result


def _array(
    value: object,
    label: str,
    *,
    minimum: int = 0,
    maximum: int,
) -> list[Any]:
    if not isinstance(value, list) or not minimum <= len(value) <= maximum:
        _fail(f"{label} must be an array with {minimum}..{maximum} entries")
    return value


def _absolute_path(value: object, label: str) -> Path:
    text = _text(value, label)
    path = Path(text)
    if text == "/" or not path.is_absolute() or path.as_posix() != text or ".." in path.parts or "." in path.parts:
        _fail(f"{label} must be a normalized absolute POSIX path")
    return path


def _relative_path(value: object, label: str) -> str:
    text = _text(value, label)
    path = PurePosixPath(text)
    if path.is_absolute() or path.as_posix() != text or any(part in {"", ".", ".."} for part in path.parts):
        _fail(f"{label} must be a normalized relative POSIX path")
    return text


def _network_namespace(value: object, label: str) -> str:
    text = _text(value, label, maximum_bytes=256)
    if _NETWORK_NAMESPACE_RE.fullmatch(text) is None:
        _fail(f"{label} must use the exact net:[digits] form")
    return text


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _fail(f"duplicate JSON key is forbidden: {key}")
        result[key] = value
    return result


def _reject_float(value: str) -> None:
    _fail(f"floating-point JSON number is forbidden: {value}")


def _reject_constant(value: str) -> None:
    _fail(f"non-finite JSON number is forbidden: {value}")


def _parse_int(value: str) -> int:
    maximum_digits = 19 if not value.startswith("-") else 20
    if len(value) > maximum_digits:
        _fail("JSON integer exceeds the signed 64-bit lexical bound")
    try:
        parsed = int(value, 10)
    except (TypeError, ValueError) as exc:
        raise RunnerTransportV2Error("JSON integer is invalid") from exc
    if not -(2**63) <= parsed <= 2**63 - 1:
        _fail("JSON integer exceeds the signed 64-bit value bound")
    return parsed


def _validate_json_tree(value: object, *, label: str) -> None:
    nodes = 0

    def visit(item: object, depth: int, location: str) -> None:
        nonlocal nodes
        nodes += 1
        if nodes > MAX_JSON_NODES:
            _fail(f"{label} exceeds the JSON node bound")
        if depth > MAX_JSON_DEPTH:
            _fail(f"{label} exceeds the JSON depth bound")
        if item is None or isinstance(item, bool):
            return
        if isinstance(item, int):
            if not -(2**63) <= item <= 2**63 - 1:
                _fail(f"{location} exceeds the signed 64-bit integer bound")
            return
        if isinstance(item, str):
            _text(item, location, minimum=0, maximum_bytes=MAX_STRING_BYTES)
            return
        if isinstance(item, list):
            for index, child in enumerate(item):
                visit(child, depth + 1, f"{location}[{index}]")
            return
        if isinstance(item, dict):
            for key, child in item.items():
                _text(key, f"{location} key", maximum_bytes=4096)
                visit(child, depth + 1, f"{location}.{key}")
            return
        _fail(f"{location} contains a non-JSON value")

    visit(value, 0, label)


def canonical_json_bytes(payload: object) -> bytes:
    """Encode the transport's deterministic one-object JSON representation."""

    _validate_json_tree(payload, label="JSON payload")
    try:
        return (
            json.dumps(
                payload,
                ensure_ascii=True,
                allow_nan=False,
                separators=(",", ":"),
                sort_keys=True,
            )
            + "\n"
        ).encode("ascii")
    except (TypeError, ValueError, RecursionError) as exc:
        raise RunnerTransportV2Error("payload cannot be canonically encoded") from exc


def _decode_canonical_json(raw: bytes, *, label: str, maximum_bytes: int) -> Any:
    if not isinstance(raw, bytes) or not 0 < len(raw) <= maximum_bytes:
        _fail(f"{label} must contain 1..{maximum_bytes} bytes")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RunnerTransportV2Error(f"{label} is not UTF-8") from exc
    try:
        payload = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_float=_reject_float,
            parse_int=_parse_int,
            parse_constant=_reject_constant,
        )
    except RunnerTransportV2Error:
        raise
    except (ValueError, RecursionError) as exc:
        raise RunnerTransportV2Error(f"{label} is not strict JSON") from exc
    _validate_json_tree(payload, label=label)
    if canonical_json_bytes(payload) != raw:
        _fail(f"{label} is not canonical transport JSON")
    return payload


@dataclass(frozen=True, slots=True)
class ExpectedRunnerBindings:
    """Independent authority values that the sealed envelope must match."""

    goal_id: str
    approval_sha256: str
    network_boundary_sha256: str
    execution_plan_sha256: str

    def __post_init__(self) -> None:
        if self.goal_id not in EXPECTED_GOAL_IDS:
            _fail("goal_id is not a v2 transport goal")
        _digest(self.approval_sha256, "approval_sha256")
        _digest(self.network_boundary_sha256, "network_boundary_sha256")
        _digest(self.execution_plan_sha256, "execution_plan_sha256")


@dataclass(frozen=True, slots=True)
class DecodedRunnerRequest:
    """A fully decoded request that still carries no execution authority."""

    bindings: ExpectedRunnerBindings
    plan: RunnerPlan
    envelope_sha256: str
    memfd_device: int
    memfd_inode: int
    memfd_size: int
    memfd_seals: int


def _decode_g038_plan(value: object) -> g038.SIWEExecutionPlan:
    plan = _exact_object(
        value,
        {
            "schema_version",
            "goal_id",
            "authorization_sha256",
            "selection_record_id",
            "network_policy",
            "network_boundary",
            "platform",
            "architecture",
            "toolchain_archive_sha256",
            "node",
            "npm_cli",
            "manifest",
            "lockfile",
            "adapter",
            "smoke_source",
            "cache",
            "resource_bounds",
            "expires_at",
        },
        "G038 plan",
    )

    def tool(name: str) -> g038.SIWEToolBinding:
        payload = _exact_object(
            plan[name],
            {"source_path", "sha256", "max_bytes", "version"},
            f"G038 plan.{name}",
        )
        return g038.SIWEToolBinding(
            source_path=_absolute_path(
                payload["source_path"],
                f"G038 plan.{name}.source_path",
            ),
            sha256=_digest(payload["sha256"], f"G038 plan.{name}.sha256"),
            max_bytes=_plain_int(
                payload["max_bytes"],
                f"G038 plan.{name}.max_bytes",
                minimum=1,
            ),
            version=_text(payload["version"], f"G038 plan.{name}.version"),
        )

    def bound_input(name: str) -> g038.SIWEBoundInput:
        payload = _exact_object(
            plan[name],
            {"source_path", "sha256", "max_bytes", "workspace_relative_path"},
            f"G038 plan.{name}",
        )
        return g038.SIWEBoundInput(
            source_path=_absolute_path(
                payload["source_path"],
                f"G038 plan.{name}.source_path",
            ),
            sha256=_digest(payload["sha256"], f"G038 plan.{name}.sha256"),
            max_bytes=_plain_int(
                payload["max_bytes"],
                f"G038 plan.{name}.max_bytes",
                minimum=1,
            ),
            workspace_relative_path=_relative_path(
                payload["workspace_relative_path"],
                f"G038 plan.{name}.workspace_relative_path",
            ),
        )

    boundary = _exact_object(
        plan["network_boundary"],
        {
            "attestation_sha256",
            "namespace",
            "apparmor_profile",
            "network_deny_canary_sha256",
            "egress_policy_sha256",
        },
        "G038 plan.network_boundary",
    )
    cache = _exact_object(
        plan["cache"],
        {
            "source_path",
            "sha256",
            "max_archive_bytes",
            "archive_format",
            "max_entries",
            "max_extracted_bytes",
            "tree_sha256",
            "entries",
        },
        "G038 plan.cache",
    )
    entries: list[g038.SIWECacheEntry] = []
    for index, item in enumerate(
        _array(
            cache["entries"],
            "G038 plan.cache.entries",
            minimum=1,
            maximum=200_000,
        )
    ):
        entry = _exact_object(
            item,
            {"path", "kind", "size", "sha256"},
            f"G038 plan.cache.entries[{index}]",
        )
        entry_digest = entry["sha256"]
        if entry_digest is not None:
            entry_digest = _digest(
                entry_digest,
                f"G038 plan.cache.entries[{index}].sha256",
            )
        entries.append(
            g038.SIWECacheEntry(
                path=_relative_path(
                    entry["path"],
                    f"G038 plan.cache.entries[{index}].path",
                ),
                kind=_text(
                    entry["kind"],
                    f"G038 plan.cache.entries[{index}].kind",
                ),
                size=_plain_int(
                    entry["size"],
                    f"G038 plan.cache.entries[{index}].size",
                ),
                sha256=entry_digest,
            )
        )
    bounds = _exact_object(
        plan["resource_bounds"],
        {
            "max_seconds",
            "max_memory_mb",
            "max_output_bytes",
            "max_file_bytes",
            "max_workspace_entries",
            "max_workspace_bytes",
        },
        "G038 plan.resource_bounds",
    )
    try:
        return g038.SIWEExecutionPlan(
            schema_version=_text(plan["schema_version"], "G038 plan.schema_version"),
            goal_id=_text(plan["goal_id"], "G038 plan.goal_id"),
            authorization_sha256=_digest(
                plan["authorization_sha256"],
                "G038 plan.authorization_sha256",
            ),
            selection_record_id=_text(
                plan["selection_record_id"],
                "G038 plan.selection_record_id",
            ),
            network_policy=_text(
                plan["network_policy"],
                "G038 plan.network_policy",
            ),
            network_boundary=g038.SIWENetworkBoundary(
                attestation_sha256=_digest(
                    boundary["attestation_sha256"],
                    "G038 plan.network_boundary.attestation_sha256",
                ),
                namespace=_network_namespace(
                    boundary["namespace"],
                    "G038 plan.network_boundary.namespace",
                ),
                apparmor_profile=_text(
                    boundary["apparmor_profile"],
                    "G038 plan.network_boundary.apparmor_profile",
                ),
                network_deny_canary_sha256=_digest(
                    boundary["network_deny_canary_sha256"],
                    "G038 plan.network_boundary.network_deny_canary_sha256",
                ),
                egress_policy_sha256=_digest(
                    boundary["egress_policy_sha256"],
                    "G038 plan.network_boundary.egress_policy_sha256",
                ),
            ),
            platform=_text(plan["platform"], "G038 plan.platform"),
            architecture=_text(plan["architecture"], "G038 plan.architecture"),
            toolchain_archive_sha256=_digest(
                plan["toolchain_archive_sha256"],
                "G038 plan.toolchain_archive_sha256",
            ),
            node=tool("node"),
            npm_cli=tool("npm_cli"),
            manifest=bound_input("manifest"),
            lockfile=bound_input("lockfile"),
            adapter=bound_input("adapter"),
            smoke_source=bound_input("smoke_source"),
            cache=g038.SIWECacheArchive(
                source_path=_absolute_path(
                    cache["source_path"],
                    "G038 plan.cache.source_path",
                ),
                sha256=_digest(cache["sha256"], "G038 plan.cache.sha256"),
                max_archive_bytes=_plain_int(
                    cache["max_archive_bytes"],
                    "G038 plan.cache.max_archive_bytes",
                    minimum=1,
                ),
                archive_format=_text(
                    cache["archive_format"],
                    "G038 plan.cache.archive_format",
                ),
                max_entries=_plain_int(
                    cache["max_entries"],
                    "G038 plan.cache.max_entries",
                    minimum=1,
                    maximum=200_000,
                ),
                max_extracted_bytes=_plain_int(
                    cache["max_extracted_bytes"],
                    "G038 plan.cache.max_extracted_bytes",
                    minimum=1,
                ),
                tree_sha256=_digest(
                    cache["tree_sha256"],
                    "G038 plan.cache.tree_sha256",
                ),
                entries=tuple(entries),
            ),
            resource_bounds=g038.SIWEResourceBounds(
                max_seconds=_plain_int(
                    bounds["max_seconds"],
                    "G038 plan.resource_bounds.max_seconds",
                    minimum=1,
                    maximum=3600,
                ),
                max_memory_mb=_plain_int(
                    bounds["max_memory_mb"],
                    "G038 plan.resource_bounds.max_memory_mb",
                    minimum=64,
                    maximum=65536,
                ),
                max_output_bytes=_plain_int(
                    bounds["max_output_bytes"],
                    "G038 plan.resource_bounds.max_output_bytes",
                    minimum=1,
                ),
                max_file_bytes=_plain_int(
                    bounds["max_file_bytes"],
                    "G038 plan.resource_bounds.max_file_bytes",
                    minimum=1,
                ),
                max_workspace_entries=_plain_int(
                    bounds["max_workspace_entries"],
                    "G038 plan.resource_bounds.max_workspace_entries",
                    minimum=1,
                    maximum=500_000,
                ),
                max_workspace_bytes=_plain_int(
                    bounds["max_workspace_bytes"],
                    "G038 plan.resource_bounds.max_workspace_bytes",
                    minimum=1,
                ),
            ),
            expires_at=_text(plan["expires_at"], "G038 plan.expires_at"),
        )
    except g038.G038SIWERunnerError as exc:
        raise RunnerTransportV2Error(f"G038 plan is invalid: {exc}") from exc


def _decode_g039_plan(value: object) -> g039.NativeSmokeExecutionPlan:
    plan = _exact_object(
        value,
        {
            "schema_version",
            "goal_id",
            "authorization_sha256",
            "network_boundary_sha256",
            "network_policy",
            "tool_path",
            "tool_sha256",
            "tool_max_bytes",
            "build_a_argv",
            "build_b_argv",
            "prove_argv",
            "verify_argv",
            "fixed_env",
            "inputs",
            "resource_bounds",
            "artifact_relative_path",
            "proof_relative_path",
            "expires_at",
        },
        "G039 plan",
    )

    def argv(name: str) -> tuple[str, ...]:
        return tuple(
            _text(item, f"G039 plan.{name}[{index}]")
            for index, item in enumerate(_array(plan[name], f"G039 plan.{name}", minimum=1, maximum=128))
        )

    fixed_env: list[tuple[str, str]] = []
    for index, item in enumerate(_array(plan["fixed_env"], "G039 plan.fixed_env", maximum=64)):
        pair = _array(
            item,
            f"G039 plan.fixed_env[{index}]",
            minimum=2,
            maximum=2,
        )
        fixed_env.append(
            (
                _text(pair[0], f"G039 plan.fixed_env[{index}][0]"),
                _text(
                    pair[1],
                    f"G039 plan.fixed_env[{index}][1]",
                    minimum=0,
                ),
            )
        )

    inputs: list[g039.NativeSmokeInput] = []
    for index, item in enumerate(_array(plan["inputs"], "G039 plan.inputs", minimum=1, maximum=32)):
        binding = _exact_object(
            item,
            {"source_path", "sha256", "max_bytes", "workspace_relative_path"},
            f"G039 plan.inputs[{index}]",
        )
        inputs.append(
            g039.NativeSmokeInput(
                source_path=_absolute_path(
                    binding["source_path"],
                    f"G039 plan.inputs[{index}].source_path",
                ),
                sha256=_digest(
                    binding["sha256"],
                    f"G039 plan.inputs[{index}].sha256",
                ),
                max_bytes=_plain_int(
                    binding["max_bytes"],
                    f"G039 plan.inputs[{index}].max_bytes",
                    minimum=1,
                ),
                workspace_relative_path=_relative_path(
                    binding["workspace_relative_path"],
                    f"G039 plan.inputs[{index}].workspace_relative_path",
                ),
            )
        )
    bounds = _exact_object(
        plan["resource_bounds"],
        {"max_seconds", "max_memory_mb", "max_output_bytes"},
        "G039 plan.resource_bounds",
    )
    try:
        return g039.NativeSmokeExecutionPlan(
            schema_version=_text(plan["schema_version"], "G039 plan.schema_version"),
            goal_id=_text(plan["goal_id"], "G039 plan.goal_id"),
            authorization_sha256=_digest(
                plan["authorization_sha256"],
                "G039 plan.authorization_sha256",
            ),
            network_boundary_sha256=_digest(
                plan["network_boundary_sha256"],
                "G039 plan.network_boundary_sha256",
            ),
            network_policy=_text(
                plan["network_policy"],
                "G039 plan.network_policy",
            ),
            tool_path=_absolute_path(plan["tool_path"], "G039 plan.tool_path"),
            tool_sha256=_digest(plan["tool_sha256"], "G039 plan.tool_sha256"),
            tool_max_bytes=_plain_int(
                plan["tool_max_bytes"],
                "G039 plan.tool_max_bytes",
                minimum=1,
            ),
            build_a_argv=argv("build_a_argv"),
            build_b_argv=argv("build_b_argv"),
            prove_argv=argv("prove_argv"),
            verify_argv=argv("verify_argv"),
            fixed_env=tuple(fixed_env),
            inputs=tuple(inputs),
            resource_bounds=g039.NativeSmokeResourceBounds(
                max_seconds=_plain_int(
                    bounds["max_seconds"],
                    "G039 plan.resource_bounds.max_seconds",
                    minimum=1,
                    maximum=3600,
                ),
                max_memory_mb=_plain_int(
                    bounds["max_memory_mb"],
                    "G039 plan.resource_bounds.max_memory_mb",
                    minimum=64,
                    maximum=65536,
                ),
                max_output_bytes=_plain_int(
                    bounds["max_output_bytes"],
                    "G039 plan.resource_bounds.max_output_bytes",
                    minimum=1,
                    maximum=1024 * 1024 * 1024,
                ),
            ),
            artifact_relative_path=_relative_path(
                plan["artifact_relative_path"],
                "G039 plan.artifact_relative_path",
            ),
            proof_relative_path=_relative_path(
                plan["proof_relative_path"],
                "G039 plan.proof_relative_path",
            ),
            expires_at=_text(plan["expires_at"], "G039 plan.expires_at"),
        )
    except g039.G039NativeSmokeError as exc:
        raise RunnerTransportV2Error(f"G039 plan is invalid: {exc}") from exc


def _decode_g040_plan(value: object) -> g040.DuckDBBootstrapPlan:
    plan = _exact_object(
        value,
        {
            "schema_version",
            "goal_id",
            "authorization",
            "network_boundary_attestation",
            "network_policy",
            "python",
            "wheel",
            "requirements_lock",
            "runtime_policy",
            "backup_policy",
            "storage_adr",
            "smoke_bootstrap_sha256",
            "resource_bounds",
            "run_directory",
            "expires_at",
        },
        "G040 plan",
    )

    def artifact(name: str) -> g040.DuckDBBoundArtifact:
        payload = _exact_object(
            plan[name],
            {"source_path", "sha256", "size"},
            f"G040 plan.{name}",
        )
        return g040.DuckDBBoundArtifact(
            source_path=_absolute_path(
                payload["source_path"],
                f"G040 plan.{name}.source_path",
            ),
            sha256=_digest(payload["sha256"], f"G040 plan.{name}.sha256"),
            size=_plain_int(
                payload["size"],
                f"G040 plan.{name}.size",
                minimum=1,
                maximum=2 * 1024 * 1024 * 1024,
            ),
        )

    python = _exact_object(
        plan["python"],
        {"path", "sha256", "size", "version"},
        "G040 plan.python",
    )
    wheel = _exact_object(
        plan["wheel"],
        {
            "path",
            "sha256",
            "size",
            "filename",
            "duckdb_version",
            "python_tag",
            "abi_tag",
            "platform_tag",
        },
        "G040 plan.wheel",
    )
    bounds = _exact_object(
        plan["resource_bounds"],
        {
            "max_seconds",
            "max_memory_mb",
            "max_output_bytes",
            "max_file_bytes",
            "max_workspace_bytes",
            "max_wheel_entries",
            "max_entry_bytes",
            "max_uncompressed_bytes",
        },
        "G040 plan.resource_bounds",
    )
    python_version = _text(
        python["version"],
        "G040 plan.python.version",
    )
    if re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", python_version) is None:
        _fail("G040 plan.python.version must have exactly three numeric components")
    try:
        return g040.DuckDBBootstrapPlan(
            schema_version=_text(plan["schema_version"], "G040 plan.schema_version"),
            goal_id=_text(plan["goal_id"], "G040 plan.goal_id"),
            authorization=artifact("authorization"),
            network_boundary_attestation=artifact("network_boundary_attestation"),
            network_policy=_text(
                plan["network_policy"],
                "G040 plan.network_policy",
            ),
            python_path=_absolute_path(python["path"], "G040 plan.python.path"),
            python_sha256=_digest(
                python["sha256"],
                "G040 plan.python.sha256",
            ),
            python_size=_plain_int(
                python["size"],
                "G040 plan.python.size",
                minimum=1,
                maximum=256 * 1024 * 1024,
            ),
            python_version=python_version,
            wheel_path=_absolute_path(wheel["path"], "G040 plan.wheel.path"),
            wheel_sha256=_digest(
                wheel["sha256"],
                "G040 plan.wheel.sha256",
            ),
            wheel_size=_plain_int(
                wheel["size"],
                "G040 plan.wheel.size",
                minimum=1,
                maximum=2 * 1024 * 1024 * 1024,
            ),
            wheel_filename=_text(
                wheel["filename"],
                "G040 plan.wheel.filename",
            ),
            duckdb_version=_text(
                wheel["duckdb_version"],
                "G040 plan.wheel.duckdb_version",
            ),
            python_tag=_text(
                wheel["python_tag"],
                "G040 plan.wheel.python_tag",
            ),
            abi_tag=_text(wheel["abi_tag"], "G040 plan.wheel.abi_tag"),
            platform_tag=_text(
                wheel["platform_tag"],
                "G040 plan.wheel.platform_tag",
            ),
            requirements_lock=artifact("requirements_lock"),
            runtime_policy=artifact("runtime_policy"),
            backup_policy=artifact("backup_policy"),
            storage_adr=artifact("storage_adr"),
            smoke_bootstrap_sha256=_digest(
                plan["smoke_bootstrap_sha256"],
                "G040 plan.smoke_bootstrap_sha256",
            ),
            resource_bounds=g040.DuckDBResourceBounds(
                max_seconds=_plain_int(
                    bounds["max_seconds"],
                    "G040 plan.resource_bounds.max_seconds",
                    minimum=1,
                    maximum=3600,
                ),
                max_memory_mb=_plain_int(
                    bounds["max_memory_mb"],
                    "G040 plan.resource_bounds.max_memory_mb",
                    minimum=64,
                    maximum=65536,
                ),
                max_output_bytes=_plain_int(
                    bounds["max_output_bytes"],
                    "G040 plan.resource_bounds.max_output_bytes",
                    minimum=1,
                    maximum=1024 * 1024 * 1024,
                ),
                max_file_bytes=_plain_int(
                    bounds["max_file_bytes"],
                    "G040 plan.resource_bounds.max_file_bytes",
                    minimum=1024,
                ),
                max_workspace_bytes=_plain_int(
                    bounds["max_workspace_bytes"],
                    "G040 plan.resource_bounds.max_workspace_bytes",
                    minimum=1024,
                ),
                max_wheel_entries=_plain_int(
                    bounds["max_wheel_entries"],
                    "G040 plan.resource_bounds.max_wheel_entries",
                    minimum=4,
                    maximum=100_000,
                ),
                max_entry_bytes=_plain_int(
                    bounds["max_entry_bytes"],
                    "G040 plan.resource_bounds.max_entry_bytes",
                    minimum=1,
                ),
                max_uncompressed_bytes=_plain_int(
                    bounds["max_uncompressed_bytes"],
                    "G040 plan.resource_bounds.max_uncompressed_bytes",
                    minimum=1,
                ),
            ),
            run_directory=_absolute_path(
                plan["run_directory"],
                "G040 plan.run_directory",
            ),
            expires_at=_text(plan["expires_at"], "G040 plan.expires_at"),
        )
    except g040.G040DuckDBBootstrapError as exc:
        raise RunnerTransportV2Error(f"G040 plan is invalid: {exc}") from exc


def _decode_plan(goal_id: str, value: object) -> RunnerPlan:
    if goal_id == "WORLDCOIN-G038":
        return _decode_g038_plan(value)
    if goal_id == "WORLDCOIN-G039":
        return _decode_g039_plan(value)
    if goal_id == "WORLDCOIN-G040":
        return _decode_g040_plan(value)
    _fail("goal_id is not a v2 transport goal")


def _plan_bindings(plan: RunnerPlan) -> tuple[str, str, str, str]:
    if isinstance(plan, g038.SIWEExecutionPlan):
        return (
            plan.goal_id,
            plan.authorization_sha256,
            plan.network_boundary.attestation_sha256,
            g038.execution_plan_sha256(plan),
        )
    if isinstance(plan, g039.NativeSmokeExecutionPlan):
        return (
            plan.goal_id,
            plan.authorization_sha256,
            plan.network_boundary_sha256,
            g039.execution_plan_sha256(plan),
        )
    if isinstance(plan, g040.DuckDBBootstrapPlan):
        return (
            plan.goal_id,
            plan.authorization.sha256,
            plan.network_boundary_attestation.sha256,
            g040.execution_plan_sha256(plan),
        )
    _fail("decoded plan has an unsupported type")


def _memfd_snapshot(metadata: os.stat_result) -> tuple[int, ...]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_nlink,
        metadata.st_uid,
        metadata.st_gid,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def _duplicate_cloexec(
    descriptor: object,
    *,
    label: str,
    minimum: int = 3,
) -> int:
    if isinstance(descriptor, bool) or not isinstance(descriptor, int) or descriptor < 0:
        _fail(f"{label} must be an open integer descriptor")
    duplicate_command = getattr(fcntl, "F_DUPFD_CLOEXEC", None)
    if duplicate_command is None:
        _fail("this platform cannot atomically pin descriptors with close-on-exec")
    try:
        duplicate = int(fcntl.fcntl(descriptor, duplicate_command, minimum))
    except OSError as exc:
        raise RunnerTransportV2Error(f"{label} cannot be pinned") from exc
    if os.get_inheritable(duplicate):
        os.close(duplicate)
        _fail(f"{label} pinned duplicate is unexpectedly inheritable")
    return duplicate


def _validate_memfd(descriptor: object) -> tuple[os.stat_result, int]:
    if isinstance(descriptor, bool) or not isinstance(descriptor, int) or descriptor <= 2:
        _fail("input descriptor must be an inherited descriptor greater than 2")
    try:
        metadata = os.fstat(descriptor)
    except OSError as exc:
        raise RunnerTransportV2Error("input descriptor is not open") from exc
    if not stat.S_ISREG(metadata.st_mode):
        _fail("input descriptor must identify a regular memfd")
    if metadata.st_nlink != 0:
        _fail("input descriptor must identify an anonymous unlinked memfd")
    if not 0 < metadata.st_size <= MAX_INPUT_BYTES:
        _fail(f"input memfd must contain 1..{MAX_INPUT_BYTES} bytes")
    try:
        target = os.readlink(f"/proc/self/fd/{descriptor}")
    except OSError as exc:
        raise RunnerTransportV2Error("input descriptor identity cannot be verified through procfs") from exc
    if not target.startswith("/memfd:") or not target.endswith(" (deleted)"):
        _fail("input descriptor is not an anonymous Linux memfd")
    get_seals = getattr(fcntl, "F_GET_SEALS", None)
    if get_seals is None:
        _fail("this platform cannot verify memfd seals")
    try:
        seals = int(fcntl.fcntl(descriptor, get_seals))
    except OSError as exc:
        raise RunnerTransportV2Error("input memfd seals cannot be read") from exc
    if seals & _REQUIRED_MEMFD_SEALS != _REQUIRED_MEMFD_SEALS:
        _fail("input memfd must carry F_SEAL_SEAL, F_SEAL_SHRINK, F_SEAL_GROW, and F_SEAL_WRITE")
    return metadata, seals


def _read_sealed_memfd(descriptor: int) -> tuple[bytes, os.stat_result, int]:
    before, before_seals = _validate_memfd(descriptor)
    chunks: list[bytes] = []
    offset = 0
    try:
        while offset < before.st_size:
            chunk = os.pread(
                descriptor,
                min(1024 * 1024, before.st_size - offset),
                offset,
            )
            if not chunk:
                _fail("input memfd ended before its sealed size")
            chunks.append(chunk)
            offset += len(chunk)
    except OSError as exc:
        raise RunnerTransportV2Error("input memfd cannot be read") from exc
    after, after_seals = _validate_memfd(descriptor)
    if _memfd_snapshot(after) != _memfd_snapshot(before):
        _fail("input memfd metadata changed while it was read")
    if after_seals != before_seals:
        _fail("input memfd seal set changed while it was read")
    return b"".join(chunks), before, before_seals


def decode_sealed_request(
    descriptor: int,
    expected: ExpectedRunnerBindings,
) -> DecodedRunnerRequest:
    """Decode one fully sealed request against independent exact bindings."""

    if not isinstance(expected, ExpectedRunnerBindings):
        _fail("expected bindings must be ExpectedRunnerBindings")
    if isinstance(descriptor, bool) or not isinstance(descriptor, int) or descriptor <= 2:
        _fail("input descriptor must be an inherited descriptor greater than 2")
    pinned_descriptor = _duplicate_cloexec(
        descriptor,
        label="input descriptor",
    )
    try:
        raw, metadata, seals = _read_sealed_memfd(pinned_descriptor)
    finally:
        os.close(pinned_descriptor)
    envelope = _exact_object(
        _decode_canonical_json(
            raw,
            label="runner input envelope",
            maximum_bytes=MAX_INPUT_BYTES,
        ),
        _INPUT_KEYS,
        "runner input envelope",
    )
    if envelope["schema_version"] != INPUT_SCHEMA:
        _fail(f"runner input schema_version must be {INPUT_SCHEMA!r}")
    if envelope["protocol"] != SEALED_INPUT_PROTOCOL:
        _fail(f"runner input protocol must be {SEALED_INPUT_PROTOCOL!r}")
    observed = ExpectedRunnerBindings(
        goal_id=_text(envelope["goal_id"], "runner input goal_id"),
        approval_sha256=_digest(
            envelope["approval_sha256"],
            "runner input approval_sha256",
        ),
        network_boundary_sha256=_digest(
            envelope["network_boundary_sha256"],
            "runner input network_boundary_sha256",
        ),
        execution_plan_sha256=_digest(
            envelope["execution_plan_sha256"],
            "runner input execution_plan_sha256",
        ),
    )
    if observed != expected:
        _fail("runner input bindings differ from independent launcher bindings")
    try:
        plan = _decode_plan(expected.goal_id, envelope["plan"])
    except RunnerTransportV2Error:
        raise
    except (
        g038.G038SIWERunnerError,
        g039.G039NativeSmokeError,
        g040.G040DuckDBBootstrapError,
        TypeError,
        ValueError,
    ) as exc:
        raise RunnerTransportV2Error(f"{expected.goal_id} native plan is invalid: {exc}") from exc
    plan_bindings = _plan_bindings(plan)
    expected_tuple = (
        expected.goal_id,
        expected.approval_sha256,
        expected.network_boundary_sha256,
        expected.execution_plan_sha256,
    )
    if plan_bindings != expected_tuple:
        _fail("decoded native plan bindings differ from the sealed envelope")
    return DecodedRunnerRequest(
        bindings=expected,
        plan=plan,
        envelope_sha256="sha256:" + hashlib.sha256(raw).hexdigest(),
        memfd_device=metadata.st_dev,
        memfd_inode=metadata.st_ino,
        memfd_size=metadata.st_size,
        memfd_seals=seals,
    )


def _command_payload(command: object) -> dict[str, Any]:
    return _exact_object(
        command,
        {
            "exit_code",
            "elapsed_ms",
            "stdout_sha256",
            "stdout_bytes",
            "stderr_sha256",
            "stderr_bytes",
        },
        "native command evidence",
    )


def _g039_plan_receipt_bindings(
    receipt: dict[str, Any],
    plan: g039.NativeSmokeExecutionPlan,
) -> None:
    expected_tool = {
        "path": os.fspath(plan.tool_path),
        "sha256": plan.tool_sha256,
        "max_bytes": plan.tool_max_bytes,
    }
    if receipt["tool"] != expected_tool:
        _fail("G039 native receipt tool differs from the decoded plan")
    expected_inputs = [
        {
            "source_path": os.fspath(item.source_path),
            "sha256": item.sha256,
            "max_bytes": item.max_bytes,
            "workspace_relative_path": item.workspace_relative_path,
        }
        for item in plan.inputs
    ]
    if receipt["inputs"] != expected_inputs:
        _fail("G039 native receipt inputs differ from the decoded plan")
    resources = _object(
        receipt["resource_bounds"],
        "G039 native receipt.resource_bounds",
    )
    expected_resources = {
        "max_seconds": plan.resource_bounds.max_seconds,
        "max_memory_mb": plan.resource_bounds.max_memory_mb,
        "max_output_bytes": plan.resource_bounds.max_output_bytes,
        "max_open_files": 64,
    }
    for key, expected_value in expected_resources.items():
        if resources[key] != expected_value or isinstance(resources[key], bool):
            _fail(f"G039 native receipt.resource_bounds.{key} differs from the decoded plan")
    if receipt["expiry"] != plan.expires_at:
        _fail("G039 native receipt expiry differs from the decoded plan")
    for command in _object(
        receipt["commands"],
        "G039 native receipt.commands",
    ).values():
        _command_payload(command)


def _g040_artifact_payload(
    artifact: g040.DuckDBBoundArtifact,
) -> dict[str, object]:
    return {
        "source_path": os.fspath(artifact.source_path),
        "sha256": artifact.sha256,
        "size": artifact.size,
    }


def _g040_plan_receipt_bindings(
    receipt: dict[str, Any],
    plan: g040.DuckDBBootstrapPlan,
) -> None:
    python = _object(receipt["python"], "G040 native receipt.python")
    expected_python = {
        "path": os.fspath(plan.python_path),
        "sha256": plan.python_sha256,
        "size": plan.python_size,
        "version": plan.python_version,
        "flags": ["-I", "-S", "-B"],
    }
    if python != expected_python:
        _fail("G040 native receipt Python binding differs from the decoded plan")
    wheel = _object(receipt["wheel"], "G040 native receipt.wheel")
    expected_wheel = {
        "path": os.fspath(plan.wheel_path),
        "filename": plan.wheel_filename,
        "sha256": plan.wheel_sha256,
        "size": plan.wheel_size,
        "duckdb_version": plan.duckdb_version,
        "python_tag": plan.python_tag,
        "abi_tag": plan.abi_tag,
        "platform_tag": plan.platform_tag,
    }
    for key, expected_value in expected_wheel.items():
        if wheel[key] != expected_value:
            _fail(f"G040 native receipt.wheel.{key} differs from the decoded plan")
    expected_reviewed_inputs = {
        "requirements_lock": _g040_artifact_payload(plan.requirements_lock),
        "runtime_policy": _g040_artifact_payload(plan.runtime_policy),
        "backup_policy": _g040_artifact_payload(plan.backup_policy),
        "storage_adr": _g040_artifact_payload(plan.storage_adr),
    }
    if receipt["reviewed_inputs"] != expected_reviewed_inputs:
        _fail("G040 reviewed inputs differ from the decoded plan")
    if receipt["smoke_bootstrap_sha256"] != plan.smoke_bootstrap_sha256:
        _fail("G040 smoke bootstrap digest differs from the decoded plan")
    resources = _object(
        receipt["resource_bounds"],
        "G040 native receipt.resource_bounds",
    )
    plan_resources = {
        "max_seconds": plan.resource_bounds.max_seconds,
        "max_memory_mb": plan.resource_bounds.max_memory_mb,
        "max_output_bytes": plan.resource_bounds.max_output_bytes,
        "max_file_bytes": plan.resource_bounds.max_file_bytes,
        "max_workspace_bytes": plan.resource_bounds.max_workspace_bytes,
        "max_wheel_entries": plan.resource_bounds.max_wheel_entries,
        "max_entry_bytes": plan.resource_bounds.max_entry_bytes,
        "max_uncompressed_bytes": plan.resource_bounds.max_uncompressed_bytes,
        "max_open_files": 128,
    }
    for key, expected_value in plan_resources.items():
        if resources[key] != expected_value or isinstance(resources[key], bool):
            _fail(f"G040 native receipt.resource_bounds.{key} differs from the decoded plan")
    if receipt["expires_at"] != plan.expires_at:
        _fail("G040 native receipt expiry differs from the decoded plan")
    _command_payload(receipt["command"])


def _require_result_request(request: object) -> DecodedRunnerRequest:
    if not isinstance(request, DecodedRunnerRequest):
        _fail("result context must be a DecodedRunnerRequest")
    if request.bindings.goal_id == "WORLDCOIN-G038":
        _fail(
            "G038 stdout results are disabled: its frozen native receipt does "
            "not bind the execution-plan and boundary-attestation digests"
        )
    if request.bindings.goal_id not in RESULT_GOAL_IDS:
        _fail("result context carries an unsupported goal")
    return request


def _validate_native_receipt(
    receipt_value: object,
    request: DecodedRunnerRequest,
) -> dict[str, Any]:
    request = _require_result_request(request)
    receipt = _object(receipt_value, "native receipt")
    _validate_json_tree(receipt, label="native receipt")
    completed_text = receipt.get("completed_at")
    try:
        completed_at = receipt_verifier._timestamp(
            completed_text,
            f"{request.bindings.goal_id} native receipt.completed_at",
        )
        receipt_digest = "sha256:" + hashlib.sha256(canonical_json_bytes(receipt)).hexdigest()
        receipt_verifier._validate_goal_evidence(
            {
                "native_receipt": receipt,
                "native_receipt_sha256": receipt_digest,
                "execution_plan_sha256": (request.bindings.execution_plan_sha256),
                "network_boundary_attestation_sha256": (request.bindings.network_boundary_sha256),
            },
            goal_id=request.bindings.goal_id,
            selection_approval_sha256=request.bindings.approval_sha256,
            started_at=completed_at,
            completed_at=completed_at,
        )
    except receipt_verifier.GateFirstReceiptError as exc:
        raise RunnerTransportV2Error(f"native receipt fails strict Gate-first validation: {exc}") from exc
    if isinstance(request.plan, g039.NativeSmokeExecutionPlan):
        _g039_plan_receipt_bindings(receipt, request.plan)
    elif isinstance(request.plan, g040.DuckDBBootstrapPlan):
        _g040_plan_receipt_bindings(receipt, request.plan)
    else:
        _fail("result context carries an unsupported native plan")
    return receipt


def _native_receipt_canonical_bytes(
    receipt: dict[str, Any],
    request: DecodedRunnerRequest,
) -> bytes:
    request = _require_result_request(request)
    ensure_ascii = isinstance(request.plan, g040.DuckDBBootstrapPlan)
    try:
        rendered = json.dumps(
            receipt,
            ensure_ascii=ensure_ascii,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError, RecursionError) as exc:
        raise RunnerTransportV2Error("native receipt cannot be canonically encoded") from exc
    raw = (rendered + "\n").encode("utf-8")
    if not 0 < len(raw) <= MAX_RESULT_BYTES:
        _fail("native receipt exceeds the fixed result byte bound")
    return raw


def build_success_result(
    native_receipt: object,
    request: DecodedRunnerRequest,
) -> dict[str, Any]:
    """Build the only valid stdout result form: a bound successful receipt."""

    request = _require_result_request(request)
    expected = request.bindings
    receipt = _validate_native_receipt(native_receipt, request)
    receipt_raw = _native_receipt_canonical_bytes(receipt, request)
    aggregate_receipt_raw = receipt_verifier.canonical_json_bytes(receipt)
    result = {
        "schema_version": RESULT_SCHEMA,
        "protocol": RESULT_PROTOCOL,
        "goal_id": expected.goal_id,
        "status": "passed",
        "approval_sha256": expected.approval_sha256,
        "network_boundary_sha256": expected.network_boundary_sha256,
        "execution_plan_sha256": expected.execution_plan_sha256,
        "native_receipt_sha256": ("sha256:" + hashlib.sha256(receipt_raw).hexdigest()),
        "aggregate_receipt_object_sha256": ("sha256:" + hashlib.sha256(aggregate_receipt_raw).hexdigest()),
        "native_receipt": receipt,
    }
    if len(canonical_json_bytes(result)) > MAX_RESULT_BYTES:
        _fail("runner result exceeds the fixed byte bound")
    return result


def decode_canonical_result(
    raw: bytes,
    request: DecodedRunnerRequest,
) -> dict[str, Any]:
    """Validate one complete stdout capture and return its native receipt."""

    request = _require_result_request(request)
    expected = request.bindings
    result = _exact_object(
        _decode_canonical_json(
            raw,
            label="runner stdout result",
            maximum_bytes=MAX_RESULT_BYTES,
        ),
        _RESULT_KEYS,
        "runner stdout result",
    )
    if result["schema_version"] != RESULT_SCHEMA:
        _fail(f"runner result schema_version must be {RESULT_SCHEMA!r}")
    if result["protocol"] != RESULT_PROTOCOL:
        _fail(f"runner result protocol must be {RESULT_PROTOCOL!r}")
    if result["status"] != "passed":
        _fail("runner result status must be exactly 'passed'")
    observed = ExpectedRunnerBindings(
        goal_id=_text(result["goal_id"], "runner result goal_id"),
        approval_sha256=_digest(
            result["approval_sha256"],
            "runner result approval_sha256",
        ),
        network_boundary_sha256=_digest(
            result["network_boundary_sha256"],
            "runner result network_boundary_sha256",
        ),
        execution_plan_sha256=_digest(
            result["execution_plan_sha256"],
            "runner result execution_plan_sha256",
        ),
    )
    if observed != expected:
        _fail("runner result bindings differ from independent launcher bindings")
    receipt = _validate_native_receipt(result["native_receipt"], request)
    expected_receipt_digest = "sha256:" + hashlib.sha256(_native_receipt_canonical_bytes(receipt, request)).hexdigest()
    if (
        _digest(
            result["native_receipt_sha256"],
            "runner result native_receipt_sha256",
        )
        != expected_receipt_digest
    ):
        _fail("runner result native receipt digest differs")
    expected_aggregate_digest = "sha256:" + hashlib.sha256(receipt_verifier.canonical_json_bytes(receipt)).hexdigest()
    if (
        _digest(
            result["aggregate_receipt_object_sha256"],
            "runner result aggregate_receipt_object_sha256",
        )
        != expected_aggregate_digest
    ):
        _fail("runner result aggregate receipt object digest differs")
    return receipt


class CanonicalResultWriter:
    """Consume a fresh pipe descriptor and write exactly one canonical result.

    Successful construction consumes the caller's descriptor after atomically
    pinning the same pipe with ``F_DUPFD_CLOEXEC``.  The pinned duplicate is
    always closed by ``emit`` or ``close``.
    """

    __slots__ = ("_closed", "_descriptor", "_emitted", "_request")

    def __init__(
        self,
        descriptor: int,
        request: DecodedRunnerRequest,
    ) -> None:
        request = _require_result_request(request)
        pinned_descriptor = _duplicate_cloexec(
            descriptor,
            label="result descriptor",
        )
        try:
            metadata = os.fstat(pinned_descriptor)
            flags = fcntl.fcntl(pinned_descriptor, fcntl.F_GETFL)
            if not stat.S_ISFIFO(metadata.st_mode):
                _fail("result descriptor must identify a FIFO or anonymous pipe")
            if flags & os.O_ACCMODE != os.O_WRONLY:
                _fail("result pipe descriptor must be write-only")
            try:
                available_raw = fcntl.ioctl(
                    pinned_descriptor,
                    termios.FIONREAD,
                    struct.pack("I", 0),
                )
                available = struct.unpack("I", available_raw)[0]
            except (OSError, struct.error) as exc:
                raise RunnerTransportV2Error("result pipe freshness cannot be verified") from exc
            if available != 0:
                _fail("result pipe must be fresh and contain zero bytes")
            os.close(descriptor)
        except BaseException:
            os.close(pinned_descriptor)
            raise
        self._descriptor = pinned_descriptor
        self._request = request
        self._emitted = False
        self._closed = False

    def close(self) -> None:
        if not getattr(self, "_closed", True):
            os.close(self._descriptor)
            self._closed = True

    def __enter__(self) -> CanonicalResultWriter:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def __del__(self) -> None:
        try:
            self.close()
        except (AttributeError, OSError):
            pass

    def emit(self, native_receipt: object) -> int:
        """Attempt one result write; every later call fails, even after error."""

        if self._emitted:
            _fail("canonical result writer has already been consumed")
        if self._closed:
            _fail("canonical result writer is closed")
        self._emitted = True
        try:
            raw = canonical_json_bytes(build_success_result(native_receipt, self._request))
            if len(raw) > MAX_RESULT_BYTES:
                _fail("runner result exceeds the fixed byte bound")
            view = memoryview(raw)
            offset = 0
            while offset < len(view):
                written = os.write(self._descriptor, view[offset:])
                if written <= 0:
                    _fail("result descriptor accepted a zero-byte write")
                offset += written
        except OSError as exc:
            raise RunnerTransportV2Error("canonical runner result could not be written") from exc
        finally:
            self.close()
        return len(raw)


__all__ = [
    "CanonicalResultWriter",
    "DecodedRunnerRequest",
    "EXPECTED_GOAL_IDS",
    "ExpectedRunnerBindings",
    "INPUT_SCHEMA",
    "MAX_INPUT_BYTES",
    "MAX_RESULT_BYTES",
    "RESULT_GOAL_IDS",
    "RESULT_PROTOCOL",
    "RESULT_SCHEMA",
    "RunnerTransportV2Error",
    "SEALED_INPUT_PROTOCOL",
    "TRANSPORT_PROTOCOL_ID",
    "build_success_result",
    "canonical_json_bytes",
    "decode_canonical_result",
    "decode_sealed_request",
]
