#!/usr/bin/env python3
"""Validate and materialize exact candidate Gate-first execution-plan bytes.

This module is a plan-construction foundation, not an execution entrypoint.
It has no CLI, writes no files, starts no runner, and never grants runtime
authority.  After all externally bound repository artifacts have been
validated, it lazily imports the reviewed v2 transport solely to prove that
every candidate passes the transport decoder and native plan constructors.
A future independently installed launcher may call
``build_validated_candidate_execution_plans`` only with:

* the direct in-memory summary returned by the signed Gate 0B verifier;
* the exact raw selection approval, operator policy, and independently
  administered deployment attestation bytes; and
* a canonical v2 candidate plan profile; and
* its expected digest from a separately authenticated external channel.

The current signed Gate selection, v1 operator policy, and v1 deployment
attestation do not bind a v2 plan-profile digest.  Consequently this module
does not claim the profile is authenticated merely because those three inputs
cross-bind one another.  ``expected_profile_sha256`` must come from a future
independently authenticated governance/deployment channel, never from the
profile, task, CLI, or caller being checked.

The externally digest-bound profile supplies every native plan field.
Optional caller candidate plans are accepted only for equality validation and
must be byte-identical after the native runner's canonicalization.  This makes
tool path, command, environment, input, and resource-bound drift fail closed.

The profile advertises the future v2 runner transport while separately
validating the current v1 Gate authority.  The repository template is
deliberately disabled.  The current v1 launcher remains verify-only and does
not call this module.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any, Final

PROFILE_SCHEMA: Final = "world-aid-gate-first-execution-plan-set/v2"
CONTRACT_ID: Final = "world-aid-gate-first-plan-construction/v2"
SELECTION_SCHEMA: Final = "world-human-aid-gate-0b-selection/v2"
POLICY_SCHEMA: Final = "world-aid-gate-first-operator-policy/v1"
DEPLOYMENT_SCHEMA: Final = "world-aid-gate-first-deployment-conformance-attestation/v1"
PROTOCOL_ID: Final = "world-aid-gate-first-launcher/v1"
EXECUTION_AUTHORITY: Final = "operator-gate-first/v1"
OPERATION: Final = "run-selection/v1"
CURRENT_INPUT_PROTOCOL: Final = "sealed-fd-json/v1"
CURRENT_OUTPUT_PROTOCOL: Final = "stdout-json/v1"
FUTURE_TRANSPORT_ID: Final = "world-aid-runner-transport/v2"
FUTURE_INPUT_SCHEMA: Final = "world-human-aid-runner-input-envelope/v2"
FUTURE_INPUT_PROTOCOL: Final = "sealed-fd-json/v2"
FUTURE_RESULT_SCHEMA: Final = "world-human-aid-runner-result-envelope/v2"
FUTURE_OUTPUT_PROTOCOL: Final = "stdout-json/v2"

BUILDER_PATH: Final = "scripts/build_world_aid_gate_first_execution_plans.py"
SCHEMA_PATH: Final = "docs/schemas/world_aid/gate-first-execution-plan-set.schema.json"
TRANSPORT_CODEC_PATH: Final = "scripts/world_aid_runner_transport_v2.py"
TRANSPORT_INPUT_SCHEMA_PATH: Final = "docs/schemas/world_aid/runner-transport-v2-input.schema.json"
TRANSPORT_RESULT_SCHEMA_PATH: Final = "docs/schemas/world_aid/runner-transport-v2-result.schema.json"
TRANSPORT_SPEC_PATH: Final = "docs/specs/WORLD_AID_RUNNER_TRANSPORT_V2.md"
RECEIPT_VERIFIER_PATH: Final = "scripts/verify_world_aid_gate_first_receipt.py"
GATE_LAUNCHER_PATH: Final = "scripts/world_aid_gate_first_launcher.py"
GATE_VERIFIER_PATH: Final = "scripts/verify_world_aid_gate_0b.py"
GATE_LAUNCHER_PROTOCOL_PATH: Final = "docs/specs/WORLD_AID_GATE_FIRST_LAUNCHER.md"

EXPECTED_GOAL_IDS: Final = (
    "WORLDCOIN-G038",
    "WORLDCOIN-G039",
    "WORLDCOIN-G040",
)
EXPECTED_RUNNERS: Final = {
    "WORLDCOIN-G038": "scripts/run_world_aid_siwe_bootstrap.py",
    "WORLDCOIN-G039": "scripts/run_world_aid_zkp_bootstrap.py",
    "WORLDCOIN-G040": "scripts/run_world_aid_duckdb_bootstrap.py",
}
RUNNER_REVIEW_KEYS: Final = {
    "WORLDCOIN-G038": "siwe_bootstrap_runner",
    "WORLDCOIN-G039": "zkp_bootstrap_runner",
    "WORLDCOIN-G040": "duckdb_bootstrap_runner",
}
NATIVE_PLAN_SCHEMAS: Final = {
    "WORLDCOIN-G038": "world-human-aid-g038-siwe-offline-plan/v1",
    "WORLDCOIN-G039": "world-human-aid-g039-native-smoke-plan/v1",
    "WORLDCOIN-G040": "world-human-aid-g040-duckdb-bootstrap-plan/v1",
}
NATIVE_CANONICALIZATION: Final = {
    "WORLDCOIN-G038": "sorted-compact-utf8-lf/v1",
    "WORLDCOIN-G039": "sorted-compact-utf8-lf/v1",
    "WORLDCOIN-G040": "sorted-compact-ascii-lf/v1",
}
PLAN_KEYS: Final = {
    "WORLDCOIN-G038": frozenset(
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
        }
    ),
    "WORLDCOIN-G039": frozenset(
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
        }
    ),
    "WORLDCOIN-G040": frozenset(
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
        }
    ),
}
PLAN_RESOURCE_KEYS: Final = {
    "WORLDCOIN-G038": frozenset(
        {
            "max_seconds",
            "max_memory_mb",
            "max_output_bytes",
            "max_file_bytes",
            "max_workspace_entries",
            "max_workspace_bytes",
        }
    ),
    "WORLDCOIN-G039": frozenset({"max_seconds", "max_memory_mb", "max_output_bytes"}),
    "WORLDCOIN-G040": frozenset(
        {
            "max_seconds",
            "max_memory_mb",
            "max_output_bytes",
            "max_file_bytes",
            "max_workspace_bytes",
            "max_wheel_entries",
            "max_entry_bytes",
            "max_uncompressed_bytes",
        }
    ),
}

_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_PROFILE_ID_RE = re.compile(r"^gate-first-execution-plans-[a-z0-9][a-z0-9._-]{7,95}$")
_ATTESTATION_ID_RE = re.compile(r"^gate-first-deployment-[a-z0-9][a-z0-9._-]{7,95}$")
_IDENTITY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9@._+-]{2,253}$")
_UTC_RE = re.compile(
    r"^[0-9]{4}-(0[1-9]|1[0-2])-([0-2][0-9]|3[01])"
    r"T([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]Z$"
)

MAX_PROFILE_BYTES: Final = 8 * 1024 * 1024
MAX_AUTHORITY_BYTES: Final = 4 * 1024 * 1024
MAX_PLAN_BYTES: Final = 2 * 1024 * 1024
MAX_JSON_DEPTH: Final = 24
MAX_JSON_NODES: Final = 100_000
MAX_STRING_BYTES: Final = 1024 * 1024
MAX_SEQUENCE_ITEMS: Final = 200_000

_G038_MAX_BINDING_BYTES: Final = 4 * 1024 * 1024 * 1024
_G038_MAX_OUTPUT_BYTES: Final = 64 * 1024 * 1024
_G038_MAX_CACHE_ENTRIES: Final = 200_000
_G038_MAX_CACHE_BYTES: Final = 4 * 1024 * 1024 * 1024
_G038_MAX_WORKSPACE_ENTRIES: Final = 500_000
_G038_MAX_WORKSPACE_BYTES: Final = 8 * 1024 * 1024 * 1024
_G038_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,255}$")

_G039_MAX_ARGV_ITEMS: Final = 128
_G039_MAX_ARG_BYTES: Final = 128 * 1024
_G039_MAX_ENV_ITEMS: Final = 64
_G039_MAX_ENV_BYTES: Final = 64 * 1024
_G039_MAX_INPUTS: Final = 32
_G039_MAX_INPUT_BYTES: Final = 1024 * 1024 * 1024
_G039_MAX_TOOL_BYTES: Final = 4 * 1024 * 1024 * 1024
_G039_ENV_KEY_RE = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")
_G039_PLACEHOLDER_RE = re.compile(r"\{[a-z_]+\}")
_G039_RESERVED_ENV_KEYS: Final = frozenset(
    {
        "ALL_PROXY",
        "BASH_ENV",
        "CARGO_NET_OFFLINE",
        "CDPATH",
        "ENV",
        "GIT_CONFIG",
        "GIT_CONFIG_GLOBAL",
        "GIT_CONFIG_NOSYSTEM",
        "GIT_CONFIG_SYSTEM",
        "GIT_TERMINAL_PROMPT",
        "HOME",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "IFS",
        "LANG",
        "LC_ALL",
        "NPM_CONFIG_OFFLINE",
        "PATH",
        "PIP_DISABLE_PIP_VERSION_CHECK",
        "PIP_NO_INDEX",
        "PYTHONHASHSEED",
        "PYTHONHOME",
        "PYTHONPATH",
        "SHELL",
        "SOURCE_DATE_EPOCH",
        "TMPDIR",
        "TZ",
        "http_proxy",
        "https_proxy",
        "no_proxy",
    }
)
_G039_RESERVED_ENV_PREFIXES: Final = (
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
_G039_FORBIDDEN_ARG_TOKENS: Final = frozenset(
    {"curl", "download", "fetch", "install", "npm", "pip", "pip3", "update", "wget"}
)
_G039_FORBIDDEN_ARG_PREFIXES: Final = (
    "--allow-network",
    "--index-url",
    "--network",
    "--online",
    "--proxy",
    "--registry",
    "--repository",
)
_FORBIDDEN_URI_MARKERS: Final = (
    "ftp://",
    "git://",
    "http://",
    "https://",
    "ssh://",
)

_G040_MAX_ARTIFACT_BYTES: Final = 2 * 1024 * 1024 * 1024
_G040_MAX_PYTHON_BYTES: Final = 256 * 1024 * 1024
_G040_MAX_WHEEL_BYTES: Final = 2 * 1024 * 1024 * 1024
_G040_WHEEL_NAME_RE = re.compile(
    r"^duckdb-(?P<version>[0-9]+(?:\.[0-9]+){2,3})-"
    r"(?P<python>cp[0-9]{2,3})-(?P<abi>cp[0-9]{2,3}[a-z0-9_]*)-"
    r"(?P<platform>[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)*)\.whl$"
)


class ExecutionPlanContractError(RuntimeError):
    """Raised when execution-plan authority or exact plan bytes drift."""


@dataclass(frozen=True, slots=True)
class ValidatedCandidateAuthority:
    """Cross-bound current authority values; not plan-profile authority."""

    approval_sha256: str
    selection_record_id: str
    approval_expires_at: str
    operator_policy_sha256: str
    deployment_attestation_id: str
    deployment_attestation_sha256: str
    gate_launcher_protocol_sha256: str
    gate_launcher_sha256: str
    gate_verifier_sha256: str
    runner_sha256: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class ValidatedCandidateExecutionPlan:
    """One immutable, externally digest-bound candidate plan representation.

    ``payload_bytes`` are the only bytes a future transport may seal.  The
    parsed mapping is intentionally not retained.
    """

    goal_id: str
    runner_path: str
    runner_sha256: str
    native_plan_schema: str
    canonicalization: str
    native_plan_sha256: str
    network_boundary_attestation_sha256: str
    payload_bytes: bytes

    def payload(self) -> dict[str, Any]:
        """Return a new parsed copy for a reviewed transport adapter."""

        value = _load_json(
            self.payload_bytes,
            label=f"{self.goal_id} validated candidate payload",
            maximum_bytes=MAX_PLAN_BYTES,
            require_canonical=True,
            ensure_ascii=self.canonicalization.endswith("ascii-lf/v1"),
        )
        return _object(value, f"{self.goal_id} validated candidate payload")


@dataclass(frozen=True, slots=True)
class ValidatedCandidateExecutionPlanSet:
    """Unauthorizing result; current Gate v2 cannot authenticate its profile."""

    profile_id: str
    profile_sha256: str
    authority: ValidatedCandidateAuthority
    plans: tuple[ValidatedCandidateExecutionPlan, ...]
    runtime_authorized: bool = False


def _fail(message: str) -> None:
    raise ExecutionPlanContractError(message)


def _pairs_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _fail(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    _fail(f"non-finite JSON number is forbidden: {value}")


def _canonical_json_bytes(value: object, *, ensure_ascii: bool) -> bytes:
    try:
        text = json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=ensure_ascii,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as exc:
        _fail(f"value is not canonical JSON: {exc}")
    return (text + "\n").encode("utf-8")


def _validate_json_bounds(value: object, *, label: str) -> None:
    remaining = MAX_JSON_NODES

    def visit(item: object, depth: int) -> None:
        nonlocal remaining
        remaining -= 1
        if remaining < 0:
            _fail(f"{label} exceeds the JSON node limit")
        if depth > MAX_JSON_DEPTH:
            _fail(f"{label} exceeds the JSON depth limit")
        if item is None or isinstance(item, bool):
            return
        if isinstance(item, int):
            return
        if isinstance(item, float):
            if not math.isfinite(item):
                _fail(f"{label} contains a non-finite number")
            return
        if isinstance(item, str):
            if len(item.encode("utf-8")) > MAX_STRING_BYTES:
                _fail(f"{label} contains an oversized string")
            return
        if isinstance(item, list):
            if len(item) > MAX_SEQUENCE_ITEMS:
                _fail(f"{label} contains an oversized array")
            for child in item:
                visit(child, depth + 1)
            return
        if isinstance(item, dict):
            if len(item) > MAX_SEQUENCE_ITEMS:
                _fail(f"{label} contains an oversized object")
            for key, child in item.items():
                if not isinstance(key, str):
                    _fail(f"{label} contains a non-string object key")
                visit(key, depth + 1)
                visit(child, depth + 1)
            return
        _fail(f"{label} contains a non-JSON value")

    visit(value, 0)


def _load_json(
    raw: bytes,
    *,
    label: str,
    maximum_bytes: int,
    require_canonical: bool = False,
    ensure_ascii: bool = False,
) -> Any:
    if not isinstance(raw, bytes) or not 1 <= len(raw) <= maximum_bytes:
        _fail(f"{label} bytes must be non-empty and at most {maximum_bytes}")
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_pairs_no_duplicates,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        _fail(f"{label} is not strict UTF-8 JSON: {exc}")
    _validate_json_bounds(value, label=label)
    if require_canonical and raw != _canonical_json_bytes(value, ensure_ascii=ensure_ascii):
        _fail(f"{label} is not canonical JSON")
    return value


def _object(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail(f"{label} must be an object")
    return value


def _array(value: object, label: str) -> list[Any]:
    if not isinstance(value, list):
        _fail(f"{label} must be an array")
    return value


def _exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    observed = set(value)
    if observed != expected:
        _fail(f"{label} fields differ: missing={sorted(expected - observed)}, extra={sorted(observed - expected)}")


def _string(value: object, label: str, *, maximum: int = 4096) -> str:
    if not isinstance(value, str) or not value or len(value.encode("utf-8")) > maximum or "\x00" in value:
        _fail(f"{label} must be a non-empty bounded string")
    return value


def _digest(value: object, label: str) -> str:
    text = _string(value, label, maximum=71)
    if _DIGEST_RE.fullmatch(text) is None:
        _fail(f"{label} must be a lowercase sha256 digest")
    return text


def _plain_int(
    value: object,
    label: str,
    *,
    minimum: int = 1,
    maximum: int = 8 * 1024 * 1024 * 1024,
) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        _fail(f"{label} must be an integer from {minimum} through {maximum}")
    return value


def _timestamp(value: object, label: str) -> str:
    text = _string(value, label, maximum=20)
    if _UTC_RE.fullmatch(text) is None:
        _fail(f"{label} must be canonical second-precision UTC")
    try:
        parsed = datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except ValueError as exc:
        _fail(f"{label} is not a real UTC timestamp: {exc}")
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != text:
        _fail(f"{label} must be canonical second-precision UTC")
    return text


def _absolute_path(value: object, label: str) -> str:
    text = _string(value, label)
    path = PurePosixPath(text)
    if (
        not path.is_absolute()
        or path.as_posix() != text
        or any(part in {"", ".", ".."} for part in path.parts[1:])
        or "\\" in text
    ):
        _fail(f"{label} must be a normalized absolute POSIX path")
    return text


def _relative_path(value: object, label: str) -> str:
    text = _string(value, label)
    path = PurePosixPath(text)
    if (
        path.is_absolute()
        or path.as_posix() != text
        or any(part in {"", ".", ".."} for part in path.parts)
        or "\\" in text
    ):
        _fail(f"{label} must be a normalized relative POSIX path")
    return text


def _sha256_bytes(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _validate_gate_summary(
    summary_value: Mapping[str, Any],
    *,
    approval: Mapping[str, Any],
    approval_sha256: str,
) -> None:
    summary = _object(summary_value, "Gate verifier summary")
    _exact_keys(
        summary,
        {
            "status",
            "phase",
            "gate_id",
            "record_id",
            "verified_approval_sha256",
            "expires_at",
            "reviewed_root_commit",
            "execution_authority",
            "approved_operation",
            "operator_policy_sha256",
            "deployment_attestation_id",
            "deployment_attestation_sha256",
            "execution_boundary_verified",
            "artifact_count",
            "signature_count",
            "offline",
            "live_actions_authorized",
        },
        "Gate verifier summary",
    )
    fixed = {
        "status": "verified",
        "phase": "selection",
        "gate_id": "gate-0b-selection",
        "record_id": approval["record_id"],
        "verified_approval_sha256": approval_sha256,
        "expires_at": approval["expires_at"],
        "execution_authority": EXECUTION_AUTHORITY,
        "approved_operation": OPERATION,
        "execution_boundary_verified": True,
        "signature_count": 9,
        "offline": True,
        "live_actions_authorized": False,
    }
    for key, expected in fixed.items():
        if summary[key] != expected:
            _fail(f"Gate verifier summary {key} is not the verified selection value")
    _plain_int(summary["artifact_count"], "Gate verifier summary artifact_count")
    commit = _string(
        summary["reviewed_root_commit"],
        "Gate verifier summary reviewed_root_commit",
        maximum=40,
    )
    if re.fullmatch(r"[0-9a-f]{40}", commit) is None:
        _fail("Gate verifier summary reviewed_root_commit is invalid")


def _validate_authority(
    *,
    gate_verifier_summary: Mapping[str, Any],
    selection_approval_bytes: bytes,
    operator_policy_bytes: bytes,
    deployment_attestation_bytes: bytes,
) -> tuple[ValidatedCandidateAuthority, dict[str, Any], dict[str, Any]]:
    approval = _object(
        _load_json(
            selection_approval_bytes,
            label="selection approval",
            maximum_bytes=MAX_AUTHORITY_BYTES,
        ),
        "selection approval",
    )
    policy = _object(
        _load_json(
            operator_policy_bytes,
            label="operator policy",
            maximum_bytes=MAX_AUTHORITY_BYTES,
        ),
        "operator policy",
    )
    attestation = _object(
        _load_json(
            deployment_attestation_bytes,
            label="deployment attestation",
            maximum_bytes=MAX_AUTHORITY_BYTES,
        ),
        "deployment attestation",
    )
    approval_sha256 = _sha256_bytes(selection_approval_bytes)
    policy_sha256 = _sha256_bytes(operator_policy_bytes)
    attestation_sha256 = _sha256_bytes(deployment_attestation_bytes)

    for key in (
        "schema_version",
        "gate_id",
        "record_id",
        "decision",
        "issued_at",
        "not_before",
        "expires_at",
        "execution_boundary",
        "reviewed_state",
        "trust",
    ):
        if key not in approval:
            _fail(f"selection approval is missing {key}")
    if approval["schema_version"] != SELECTION_SCHEMA:
        _fail("selection approval schema is not v2")
    if approval["gate_id"] != "gate-0b-selection" or approval["decision"] != "approved":
        _fail("selection approval is not approved Gate 0B selection")
    record_id = _string(approval["record_id"], "selection approval record_id", maximum=112)
    issued_at = _timestamp(approval["issued_at"], "selection approval issued_at")
    not_before = _timestamp(approval["not_before"], "selection approval not_before")
    expires_at = _timestamp(approval["expires_at"], "selection approval expires_at")
    issued_time = datetime.strptime(issued_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    not_before_time = datetime.strptime(not_before, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    expires_time = datetime.strptime(expires_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    if not issued_time <= not_before_time < expires_time:
        _fail("selection approval validity timestamps are inconsistent")

    trust = _object(approval["trust"], "selection approval trust")
    if (
        trust.get("signature_namespace") != "world-aid-gate-0b-selection-v2"
        or len(_array(trust.get("signatures"), "selection approval signatures")) != 9
    ):
        _fail("selection approval does not bind the exact nine-signature v2 trust set")
    _validate_gate_summary(
        gate_verifier_summary,
        approval=approval,
        approval_sha256=approval_sha256,
    )

    boundary = _object(approval["execution_boundary"], "selection approval execution_boundary")
    boundary_fixed = {
        "protocol_id": PROTOCOL_ID,
        "execution_authority": EXECUTION_AUTHORITY,
        "operation": OPERATION,
        "sealed_input_protocol": CURRENT_INPUT_PROTOCOL,
        "result_protocol": CURRENT_OUTPUT_PROTOCOL,
        "operator_policy_id": POLICY_SCHEMA,
    }
    for key, expected in boundary_fixed.items():
        if boundary.get(key) != expected:
            _fail(f"selection approval execution_boundary.{key} drift")
    if boundary.get("installed_launcher_path") != ("/usr/local/libexec/world-aid-gate-first-launcher"):
        _fail("selection approval installed launcher path drift")
    if boundary.get("operator_policy_sha256") != policy_sha256:
        _fail("selection approval does not bind the supplied operator policy")
    if boundary.get("deployment_attestation_sha256") != attestation_sha256:
        _fail("selection approval does not bind the supplied deployment attestation")
    reviewed = _object(
        boundary.get("reviewed_artifacts"),
        "selection approval reviewed execution artifacts",
    )
    reviewed_state = _object(
        approval["reviewed_state"],
        "selection approval reviewed_state",
    )
    reviewed_commit = _string(
        reviewed_state.get("root_commit"),
        "selection approval reviewed_state.root_commit",
        maximum=40,
    )
    if re.fullmatch(r"[0-9a-f]{40}", reviewed_commit) is None:
        _fail("selection approval reviewed root commit is invalid")
    objective_heap = _object(
        reviewed_state.get("objective_heap"),
        "selection approval reviewed_state.objective_heap",
    )
    objective_heap_sha256 = _digest(
        objective_heap.get("sha256"),
        "selection approval reviewed_state.objective_heap.sha256",
    )
    if gate_verifier_summary["reviewed_root_commit"] != reviewed_commit:
        _fail("Gate verifier summary reviewed root commit drift")

    _exact_keys(
        policy,
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
    if policy["schema"] != POLICY_SCHEMA or policy["mode"] != "verify-only":
        _fail("operator policy is not the immutable v1 verify-only policy")
    execution = _object(policy["execution"], "operator policy execution")
    _exact_keys(
        execution,
        {"run_selection_enabled", "expected_goal_ids", "runners"},
        "operator policy execution",
    )
    if execution["run_selection_enabled"] is not False:
        _fail("current v1 operator policy must remain verify-only")
    if tuple(_array(execution["expected_goal_ids"], "expected_goal_ids")) != (EXPECTED_GOAL_IDS):
        _fail("operator policy expected_goal_ids drift")
    runners = _array(execution["runners"], "operator policy runners")
    if runners:
        _fail("current v1 verify-only policy must have no injected runners")

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
        "deployment attestation",
    )
    gate_launcher_protocol_sha256 = _digest(
        reviewed.get("gate_launcher_protocol"),
        "signed approval Gate launcher protocol digest",
    )
    gate_launcher_sha256 = _digest(
        reviewed.get("gate_launcher"),
        "signed approval Gate launcher digest",
    )
    gate_verifier_sha256 = _digest(
        reviewed.get("gate_verifier"),
        "signed approval Gate verifier digest",
    )
    attestation_fixed = {
        "schema": DEPLOYMENT_SCHEMA,
        "independently_administered": True,
        "deployed": True,
        "conformant": True,
        "protocol_id": PROTOCOL_ID,
        "protocol_sha256": gate_launcher_protocol_sha256,
        "launcher_sha256": gate_launcher_sha256,
        "gate_verifier_id": "world-aid-gate-0b-verifier/v1",
        "gate_verifier_sha256": gate_verifier_sha256,
        "trust_policy_id": POLICY_SCHEMA,
        "trust_policy_sha256": policy_sha256,
        "target_commit": reviewed_commit,
        "target_heap_id": objective_heap_sha256,
        "runtime_authorized": False,
    }
    for key, expected in attestation_fixed.items():
        if attestation[key] != expected:
            _fail(f"deployment attestation {key} drift")
    attestation_id = _string(attestation["attestation_id"], "deployment attestation id", maximum=112)
    if _ATTESTATION_ID_RE.fullmatch(attestation_id) is None:
        _fail("deployment attestation id is invalid")
    administrator_identity = _string(
        attestation["administrator_identity"],
        "deployment attestation administrator_identity",
        maximum=254,
    )
    if _IDENTITY_RE.fullmatch(administrator_identity) is None:
        _fail("deployment attestation administrator_identity is invalid")
    attestation_issued_at = _timestamp(
        attestation["issued_at"],
        "deployment attestation issued_at",
    )
    attestation_issued_time = datetime.strptime(
        attestation_issued_at,
        "%Y-%m-%dT%H:%M:%SZ",
    ).replace(tzinfo=UTC)
    if attestation_issued_time > issued_time:
        _fail("deployment attestation postdates the signed selection approval")
    if boundary.get("deployment_attestation_id") != attestation_id:
        _fail("selection approval deployment attestation id drift")

    summary = _object(gate_verifier_summary, "Gate verifier summary")
    if (
        summary["operator_policy_sha256"] != policy_sha256
        or summary["deployment_attestation_id"] != attestation_id
        or summary["deployment_attestation_sha256"] != attestation_sha256
    ):
        _fail("Gate verifier summary authority binding drift")

    reviewed_runners: dict[str, str] = {}
    for goal_id in EXPECTED_GOAL_IDS:
        review_key = RUNNER_REVIEW_KEYS[goal_id]
        reviewed_runners[goal_id] = _digest(
            reviewed.get(review_key),
            f"signed approval runner digest for {goal_id}",
        )

    authority = ValidatedCandidateAuthority(
        approval_sha256=approval_sha256,
        selection_record_id=record_id,
        approval_expires_at=expires_at,
        operator_policy_sha256=policy_sha256,
        deployment_attestation_id=attestation_id,
        deployment_attestation_sha256=attestation_sha256,
        gate_launcher_protocol_sha256=gate_launcher_protocol_sha256,
        gate_launcher_sha256=gate_launcher_sha256,
        gate_verifier_sha256=gate_verifier_sha256,
        runner_sha256=tuple((goal_id, reviewed_runners[goal_id]) for goal_id in EXPECTED_GOAL_IDS),
    )
    return authority, approval, policy


def _validate_contract_files(
    profile: Mapping[str, Any],
    repo_root: Path,
) -> dict[str, str]:
    contract = _object(profile["contract"], "plan profile contract")
    _exact_keys(
        contract,
        {
            "contract_id",
            "builder_path",
            "builder_sha256",
            "schema_path",
            "schema_sha256",
            "transport_codec_path",
            "transport_codec_sha256",
            "transport_input_schema_path",
            "transport_input_schema_sha256",
            "transport_result_schema_path",
            "transport_result_schema_sha256",
            "transport_spec_path",
            "transport_spec_sha256",
            "receipt_verifier_path",
            "receipt_verifier_sha256",
        },
        "plan profile contract",
    )
    if contract["contract_id"] != CONTRACT_ID:
        _fail("plan profile contract_id drift")
    verified: dict[str, str] = {}
    for key, expected_path in (
        ("builder", BUILDER_PATH),
        ("schema", SCHEMA_PATH),
        ("transport_codec", TRANSPORT_CODEC_PATH),
        ("transport_input_schema", TRANSPORT_INPUT_SCHEMA_PATH),
        ("transport_result_schema", TRANSPORT_RESULT_SCHEMA_PATH),
        ("transport_spec", TRANSPORT_SPEC_PATH),
        ("receipt_verifier", RECEIPT_VERIFIER_PATH),
    ):
        path_key = f"{key}_path"
        digest_key = f"{key}_sha256"
        if contract[path_key] != expected_path:
            _fail(f"plan profile {path_key} drift")
        path = repo_root / expected_path
        try:
            raw = path.read_bytes()
        except OSError as exc:
            _fail(f"cannot read plan contract {key}: {exc}")
        observed_digest = _sha256_bytes(raw)
        if observed_digest != _digest(contract[digest_key], digest_key):
            _fail(f"plan contract {key} digest drift")
        verified[key] = observed_digest
    return verified


def _validate_signed_repository_artifacts(
    *,
    authority: ValidatedCandidateAuthority,
    repo_root: Path,
) -> None:
    expected = {
        GATE_LAUNCHER_PROTOCOL_PATH: authority.gate_launcher_protocol_sha256,
        GATE_LAUNCHER_PATH: authority.gate_launcher_sha256,
        GATE_VERIFIER_PATH: authority.gate_verifier_sha256,
        **{EXPECTED_RUNNERS[goal_id]: digest for goal_id, digest in authority.runner_sha256},
    }
    for relative_path, expected_digest in expected.items():
        try:
            observed_digest = _sha256_bytes((repo_root / relative_path).read_bytes())
        except OSError as exc:
            _fail(f"cannot read signed repository artifact {relative_path}: {exc}")
        if observed_digest != expected_digest:
            _fail(f"signed repository artifact digest drift: {relative_path}")


def _load_verified_transport_codec(
    *,
    profile: Mapping[str, Any],
    repo_root: Path,
    verified_contract_digests: Mapping[str, str],
) -> Any:
    """Import the codec only after every external candidate binding is checked."""

    import scripts.world_aid_runner_transport_v2 as transport

    module_path_text = getattr(transport, "__file__", None)
    if not isinstance(module_path_text, str):
        _fail("verified runner transport module has no source path")
    expected_path = (repo_root / TRANSPORT_CODEC_PATH).resolve(strict=True)
    if Path(module_path_text).resolve(strict=True) != expected_path:
        _fail("imported runner transport codec path differs from the bound artifact")
    try:
        observed_digest = _sha256_bytes(expected_path.read_bytes())
    except OSError as exc:
        _fail(f"cannot revalidate imported runner transport codec: {exc}")
    if observed_digest != verified_contract_digests["transport_codec"]:
        _fail("runner transport codec changed after contract validation")

    protocol = _object(profile["protocol"], "plan profile protocol")
    expected_constants = {
        "TRANSPORT_PROTOCOL_ID": protocol["transport_protocol_id"],
        "INPUT_SCHEMA": protocol["input_schema"],
        "SEALED_INPUT_PROTOCOL": protocol["input_protocol"],
        "RESULT_SCHEMA": protocol["result_schema"],
        "RESULT_PROTOCOL": protocol["output_protocol"],
    }
    for name, expected in expected_constants.items():
        if getattr(transport, name, None) != expected:
            _fail(f"runner transport codec constant {name} drift")
    return transport


def _validate_profile_authority(profile: Mapping[str, Any], authority: ValidatedCandidateAuthority) -> None:
    value = _object(profile["authority"], "plan profile authority")
    _exact_keys(
        value,
        {
            "selection_approval",
            "operator_policy",
            "deployment_attestation",
        },
        "plan profile authority",
    )
    selection = _object(value["selection_approval"], "plan profile selection approval")
    _exact_keys(
        selection,
        {"schema", "record_id", "sha256"},
        "plan profile selection approval",
    )
    expected_selection = {
        "schema": SELECTION_SCHEMA,
        "record_id": authority.selection_record_id,
        "sha256": authority.approval_sha256,
    }
    if selection != expected_selection:
        _fail("plan profile signed selection approval binding drift")

    policy = _object(value["operator_policy"], "plan profile operator policy")
    _exact_keys(policy, {"schema", "sha256"}, "plan profile operator policy")
    if policy != {
        "schema": POLICY_SCHEMA,
        "sha256": authority.operator_policy_sha256,
    }:
        _fail("plan profile operator policy binding drift")

    attestation = _object(
        value["deployment_attestation"],
        "plan profile deployment attestation",
    )
    _exact_keys(
        attestation,
        {"schema", "attestation_id", "sha256"},
        "plan profile deployment attestation",
    )
    if attestation != {
        "schema": DEPLOYMENT_SCHEMA,
        "attestation_id": authority.deployment_attestation_id,
        "sha256": authority.deployment_attestation_sha256,
    }:
        _fail("plan profile deployment attestation binding drift")


def _validate_protocol(profile: Mapping[str, Any]) -> None:
    protocol = _object(profile["protocol"], "plan profile protocol")
    _exact_keys(
        protocol,
        {
            "gate_protocol_id",
            "execution_authority",
            "operation",
            "transport_protocol_id",
            "input_schema",
            "input_protocol",
            "result_schema",
            "output_protocol",
        },
        "plan profile protocol",
    )
    expected = {
        "gate_protocol_id": PROTOCOL_ID,
        "execution_authority": EXECUTION_AUTHORITY,
        "operation": OPERATION,
        "transport_protocol_id": FUTURE_TRANSPORT_ID,
        "input_schema": FUTURE_INPUT_SCHEMA,
        "input_protocol": FUTURE_INPUT_PROTOCOL,
        "result_schema": FUTURE_RESULT_SCHEMA,
        "output_protocol": FUTURE_OUTPUT_PROTOCOL,
    }
    if protocol != expected:
        _fail("plan profile execution protocol drift")


def _validate_bound_artifact(value: object, label: str) -> dict[str, Any]:
    artifact = _object(value, label)
    _exact_keys(artifact, {"source_path", "sha256", "size"}, label)
    _absolute_path(artifact["source_path"], f"{label}.source_path")
    _digest(artifact["sha256"], f"{label}.sha256")
    _plain_int(
        artifact["size"],
        f"{label}.size",
        minimum=1,
        maximum=_G040_MAX_ARTIFACT_BYTES,
    )
    return artifact


def _validate_tool_or_input(
    value: object,
    label: str,
    *,
    version: bool = False,
    maximum_bytes: int,
) -> None:
    item = _object(value, label)
    fourth_key = "version" if version else "workspace_relative_path"
    _exact_keys(item, {"source_path", "sha256", "max_bytes", fourth_key}, label)
    _absolute_path(item["source_path"], f"{label}.source_path")
    _digest(item["sha256"], f"{label}.sha256")
    _plain_int(
        item["max_bytes"],
        f"{label}.max_bytes",
        minimum=1,
        maximum=maximum_bytes,
    )
    if version:
        version_text = _string(item["version"], f"{label}.version", maximum=64)
        if re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version_text) is None:
            _fail(f"{label}.version must be an exact semantic version")
    else:
        _relative_path(
            item["workspace_relative_path"],
            f"{label}.workspace_relative_path",
        )


def _validate_resource_bounds(value: object, *, goal_id: str) -> None:
    bounds = _object(value, f"{goal_id} resource_bounds")
    _exact_keys(
        bounds,
        set(PLAN_RESOURCE_KEYS[goal_id]),
        f"{goal_id} resource_bounds",
    )
    if goal_id == "WORLDCOIN-G038":
        ranges = {
            "max_seconds": (1, 3600),
            "max_memory_mb": (64, 65536),
            "max_output_bytes": (1, _G038_MAX_OUTPUT_BYTES),
            "max_file_bytes": (1, _G038_MAX_WORKSPACE_BYTES),
            "max_workspace_entries": (1, _G038_MAX_WORKSPACE_ENTRIES),
            "max_workspace_bytes": (1, _G038_MAX_WORKSPACE_BYTES),
        }
    elif goal_id == "WORLDCOIN-G039":
        ranges = {
            "max_seconds": (1, 3600),
            "max_memory_mb": (64, 65536),
            "max_output_bytes": (1, 1024 * 1024 * 1024),
        }
    else:
        ranges = {
            "max_seconds": (1, 3600),
            "max_memory_mb": (64, 65536),
            "max_output_bytes": (1, 1024 * 1024 * 1024),
            "max_file_bytes": (1024, 4 * 1024 * 1024 * 1024),
            "max_workspace_bytes": (1024, 8 * 1024 * 1024 * 1024),
            "max_wheel_entries": (4, 100_000),
            "max_entry_bytes": (1, 2 * 1024 * 1024 * 1024),
            "max_uncompressed_bytes": (1, 4 * 1024 * 1024 * 1024),
        }
    for key, (minimum, maximum) in ranges.items():
        _plain_int(
            bounds[key],
            f"{goal_id} resource_bounds.{key}",
            minimum=minimum,
            maximum=maximum,
        )
    if goal_id == "WORLDCOIN-G040":
        if bounds["max_entry_bytes"] > bounds["max_uncompressed_bytes"]:
            _fail("G040 max_entry_bytes cannot exceed max_uncompressed_bytes")
        if bounds["max_uncompressed_bytes"] > bounds["max_workspace_bytes"]:
            _fail("G040 max_uncompressed_bytes cannot exceed max_workspace_bytes")


def _validate_argv(
    value: object,
    label: str,
    *,
    allowed_placeholders: set[str],
    required_placeholders: set[str],
) -> None:
    argv = _array(value, label)
    if not 1 <= len(argv) <= _G039_MAX_ARGV_ITEMS:
        _fail(f"{label} must contain 1 through {_G039_MAX_ARGV_ITEMS} arguments")
    if argv[0] != "{tool}":
        _fail(f"{label}[0] must be exactly '{{tool}}'")
    total_bytes = 0
    observed_placeholders: set[str] = set()
    for index, argument in enumerate(argv):
        argument = _string(argument, f"{label}[{index}]", maximum=4096)
        total_bytes += len(argument.encode("utf-8"))
        lowered = argument.lower()
        if any(marker in lowered for marker in _FORBIDDEN_URI_MARKERS):
            _fail(f"{label}[{index}] contains a network URI")
        normalized = lowered.lstrip("-").split("=", 1)[0]
        if normalized in _G039_FORBIDDEN_ARG_TOKENS or any(
            lowered == prefix or lowered.startswith(prefix + "=") for prefix in _G039_FORBIDDEN_ARG_PREFIXES
        ):
            _fail(f"{label}[{index}] requests network or download behavior")
        if index > 0 and "{tool}" in argument:
            _fail(f"{label}[{index}] may not reference the tool descriptor")
        if re.search(r"(^|[^A-Za-z0-9_.-])\.\.($|[/])", argument):
            _fail(f"{label}[{index}] contains path traversal")
        without_placeholders = _G039_PLACEHOLDER_RE.sub("BOUND", argument)
        if without_placeholders.startswith("/") or re.search(
            r"[^A-Za-z0-9_.-]/",
            without_placeholders,
        ):
            _fail(f"{label}[{index}] contains an arbitrary absolute path")
        for match in _G039_PLACEHOLDER_RE.finditer(argument):
            placeholder = match.group(0)
            placeholder_name = placeholder[1:-1]
            if placeholder_name not in allowed_placeholders:
                _fail(f"{label}[{index}] contains unsupported placeholder {placeholder!r}")
            observed_placeholders.add(placeholder_name)
            if placeholder_name != "tool":
                start, end = match.span()
                if start and argument[start - 1] not in {"=", ":"} or end < len(argument) and argument[end] != "/":
                    _fail(f"{label}[{index}] uses {placeholder!r} outside a path boundary")
        residue = _G039_PLACEHOLDER_RE.sub("", argument)
        if "{" in residue or "}" in residue:
            _fail(f"{label}[{index}] contains malformed placeholder syntax")
    if total_bytes > _G039_MAX_ARG_BYTES:
        _fail(f"{label} exceeds the {_G039_MAX_ARG_BYTES}-byte limit")
    missing = required_placeholders - observed_placeholders
    if missing:
        _fail(f"{label} is missing required placeholders: {sorted(missing)}")


def _g038_cache_tree_sha256(entries: Sequence[Mapping[str, Any]]) -> str:
    digest = hashlib.sha256()

    def add(kind: bytes, path: str, file_digest: str | None = None) -> None:
        encoded = path.encode("utf-8")
        digest.update(kind)
        digest.update(len(encoded).to_bytes(8, "big"))
        digest.update(encoded)
        if file_digest is not None:
            digest.update(bytes.fromhex(file_digest.removeprefix("sha256:")))

    by_path = {entry["path"]: entry for entry in entries}
    children: dict[str, list[Mapping[str, Any]]] = {".": []}
    for entry in entries:
        parent = PurePosixPath(entry["path"]).parent.as_posix()
        if parent != ".":
            parent_entry = by_path.get(parent)
            if parent_entry is None or parent_entry["kind"] != "directory":
                _fail(f"G038 cache manifest omits directory parent {parent!r}")
        children.setdefault(parent, []).append(entry)
        if entry["kind"] == "directory":
            children.setdefault(entry["path"], [])

    add(b"D", ".")

    def walk(parent: str) -> None:
        for entry in sorted(
            children[parent],
            key=lambda item: PurePosixPath(item["path"]).name.encode("utf-8"),
        ):
            add(
                b"D" if entry["kind"] == "directory" else b"F",
                entry["path"],
                entry["sha256"] if entry["kind"] == "file" else None,
            )
            if entry["kind"] == "directory":
                walk(entry["path"])

    walk(".")
    return "sha256:" + digest.hexdigest()


def _validate_g038_cache_entries(
    cache: Mapping[str, Any],
    raw_entries: Sequence[Any],
) -> None:
    if not 1 <= len(raw_entries) <= _G038_MAX_CACHE_ENTRIES or len(raw_entries) > cache["max_entries"]:
        _fail("G038 cache entries exceed the exact max_entries bound")
    entries: list[dict[str, Any]] = []
    for index, raw_entry in enumerate(raw_entries):
        label = f"G038 cache.entries[{index}]"
        entry = _object(raw_entry, label)
        _exact_keys(entry, {"path", "kind", "size", "sha256"}, label)
        _relative_path(entry["path"], f"{label}.path")
        if entry["kind"] not in {"directory", "file"}:
            _fail(f"{label}.kind must be directory or file")
        if entry["kind"] == "directory":
            if entry["size"] != 0 or entry["sha256"] is not None:
                _fail(f"{label} directory requires size=0 and sha256=null")
        else:
            _plain_int(
                entry["size"],
                f"{label}.size",
                minimum=0,
                maximum=_G038_MAX_CACHE_BYTES,
            )
            _digest(entry["sha256"], f"{label}.sha256")
        entries.append(entry)
    paths = [entry["path"] for entry in entries]
    if paths != sorted(paths) or len(paths) != len(set(paths)):
        _fail("G038 cache entry paths must be unique and sorted")
    if sum(entry["size"] for entry in entries) > cache["max_extracted_bytes"]:
        _fail("G038 cache entries exceed max_extracted_bytes")
    file_paths = {entry["path"] for entry in entries if entry["kind"] == "file"}
    for entry in entries:
        if any(
            parent.as_posix() in file_paths
            for parent in PurePosixPath(entry["path"]).parents
            if parent.as_posix() != "."
        ):
            _fail("G038 cache manifest places an entry beneath a file")
    if _g038_cache_tree_sha256(entries) != cache["tree_sha256"]:
        _fail("G038 cache tree_sha256 differs from the exact manifest")


def _validate_g038_payload(payload: Mapping[str, Any]) -> str:
    for key in ("node", "npm_cli"):
        _validate_tool_or_input(
            payload[key],
            f"G038 {key}",
            version=True,
            maximum_bytes=_G038_MAX_BINDING_BYTES,
        )
    for key in ("manifest", "lockfile", "adapter", "smoke_source"):
        _validate_tool_or_input(
            payload[key],
            f"G038 {key}",
            maximum_bytes=_G038_MAX_BINDING_BYTES,
        )
    expected_destinations = {
        "manifest": "package.json",
        "lockfile": "package-lock.json",
        "adapter": "index.mjs",
        "smoke_source": "g038-smoke.mjs",
    }
    for key, expected in expected_destinations.items():
        if payload[key]["workspace_relative_path"] != expected:
            _fail(f"G038 {key} workspace destination drift")
    source_paths = [
        payload[key]["source_path"]
        for key in (
            "node",
            "npm_cli",
            "manifest",
            "lockfile",
            "adapter",
            "smoke_source",
        )
    ]
    network = _object(payload["network_boundary"], "G038 network_boundary")
    _exact_keys(
        network,
        {
            "attestation_sha256",
            "namespace",
            "apparmor_profile",
            "network_deny_canary_sha256",
            "egress_policy_sha256",
        },
        "G038 network_boundary",
    )
    for key in (
        "attestation_sha256",
        "network_deny_canary_sha256",
        "egress_policy_sha256",
    ):
        _digest(network[key], f"G038 network_boundary.{key}")
    namespace = _string(
        network["namespace"],
        "G038 network_boundary.namespace",
        maximum=255,
    )
    if re.fullmatch(r"net:\[[0-9]+\]", namespace) is None:
        _fail("G038 network namespace must be a closed namespace identity")
    apparmor_profile = _string(
        network["apparmor_profile"],
        "G038 network_boundary.apparmor_profile",
        maximum=255,
    )
    if not apparmor_profile.endswith(" (enforce)"):
        _fail("G038 AppArmor profile must be enforcing")
    for key in ("selection_record_id", "platform", "architecture"):
        text = _string(payload[key], f"G038 {key}", maximum=256)
        if _G038_IDENTIFIER_RE.fullmatch(text) is None:
            _fail(f"G038 {key} is invalid")
    _digest(payload["toolchain_archive_sha256"], "G038 toolchain_archive_sha256")
    cache = _object(payload["cache"], "G038 cache")
    _exact_keys(
        cache,
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
        "G038 cache",
    )
    _absolute_path(cache["source_path"], "G038 cache.source_path")
    source_paths.append(cache["source_path"])
    if len(source_paths) != len(set(source_paths)):
        _fail("G038 tool, input, and cache source paths must be unique")
    for key in ("sha256", "tree_sha256"):
        _digest(cache[key], f"G038 cache.{key}")
    for key in ("max_archive_bytes", "max_entries", "max_extracted_bytes"):
        maximum = {
            "max_archive_bytes": _G038_MAX_CACHE_BYTES,
            "max_entries": _G038_MAX_CACHE_ENTRIES,
            "max_extracted_bytes": _G038_MAX_CACHE_BYTES,
        }[key]
        _plain_int(
            cache[key],
            f"G038 cache.{key}",
            minimum=1,
            maximum=maximum,
        )
    if cache["archive_format"] != "tar":
        _fail("G038 cache archive_format drift")
    entries = _array(cache["entries"], "G038 cache.entries")
    _validate_g038_cache_entries(cache, entries)
    _validate_resource_bounds(payload["resource_bounds"], goal_id="WORLDCOIN-G038")
    return _digest(network["attestation_sha256"], "G038 network boundary attestation")


def _validate_g039_payload(payload: Mapping[str, Any]) -> str:
    _absolute_path(payload["tool_path"], "G039 tool_path")
    _digest(payload["tool_sha256"], "G039 tool_sha256")
    _plain_int(
        payload["tool_max_bytes"],
        "G039 tool_max_bytes",
        minimum=1,
        maximum=_G039_MAX_TOOL_BYTES,
    )
    for key in ("build_a_argv", "build_b_argv"):
        _validate_argv(
            payload[key],
            f"G039 {key}",
            allowed_placeholders={"tool", "work_dir", "input_root", "artifact"},
            required_placeholders={"tool", "input_root", "artifact"},
        )
    for key in ("prove_argv", "verify_argv"):
        _validate_argv(
            payload[key],
            f"G039 {key}",
            allowed_placeholders={
                "tool",
                "work_dir",
                "input_root",
                "artifact",
                "proof",
            },
            required_placeholders={"tool", "input_root", "artifact", "proof"},
        )
    fixed_env = _array(payload["fixed_env"], "G039 fixed_env")
    if len(fixed_env) > _G039_MAX_ENV_ITEMS:
        _fail(f"G039 fixed_env exceeds {_G039_MAX_ENV_ITEMS} entries")
    env_keys: list[str] = []
    env_total_bytes = 0
    for index, item in enumerate(fixed_env):
        pair = _array(item, f"G039 fixed_env[{index}]")
        if len(pair) != 2:
            _fail(f"G039 fixed_env[{index}] must be a key/value pair")
        key = _string(pair[0], f"G039 fixed_env[{index}][0]", maximum=64)
        if _G039_ENV_KEY_RE.fullmatch(key) is None:
            _fail(f"G039 fixed_env[{index}] has an invalid key")
        if key in _G039_RESERVED_ENV_KEYS or any(key.startswith(prefix) for prefix in _G039_RESERVED_ENV_PREFIXES):
            _fail(f"G039 fixed_env[{index}] overrides runner-controlled key")
        value = pair[1]
        if not isinstance(value, str) or "\x00" in value:
            _fail(f"G039 fixed_env[{index}][1] must be a NUL-free string")
        if any(marker in value.lower() for marker in _FORBIDDEN_URI_MARKERS):
            _fail(f"G039 fixed_env[{index}] contains a network URI")
        env_keys.append(key)
        env_total_bytes += len(key.encode("utf-8")) + len(value.encode("utf-8"))
    if len(env_keys) != len(set(env_keys)):
        _fail("G039 fixed_env keys must be unique")
    if env_keys != sorted(env_keys):
        _fail("G039 fixed_env keys must be sorted")
    if env_total_bytes > _G039_MAX_ENV_BYTES:
        _fail(f"G039 fixed_env exceeds {_G039_MAX_ENV_BYTES} bytes")
    inputs = _array(payload["inputs"], "G039 inputs")
    if not 1 <= len(inputs) <= _G039_MAX_INPUTS:
        _fail(f"G039 inputs must contain 1 through {_G039_MAX_INPUTS} bindings")
    source_paths: list[str] = []
    destinations: list[PurePosixPath] = []
    total_input_bytes = 0
    for index, item in enumerate(inputs):
        _validate_tool_or_input(
            item,
            f"G039 inputs[{index}]",
            maximum_bytes=_G039_MAX_INPUT_BYTES,
        )
        source_paths.append(item["source_path"])
        destinations.append(PurePosixPath(item["workspace_relative_path"]))
        total_input_bytes += item["max_bytes"]
    if len(source_paths) != len(set(source_paths)):
        _fail("G039 input source paths must be unique")
    if total_input_bytes > _G039_MAX_INPUT_BYTES:
        _fail(f"G039 combined input max_bytes exceeds {_G039_MAX_INPUT_BYTES}")
    for index, destination in enumerate(destinations):
        for other in destinations[index + 1 :]:
            if destination == other or destination in other.parents or other in destination.parents:
                _fail("G039 input destinations must be unique and non-overlapping")
    _validate_resource_bounds(payload["resource_bounds"], goal_id="WORLDCOIN-G039")
    _relative_path(payload["artifact_relative_path"], "G039 artifact_relative_path")
    _relative_path(payload["proof_relative_path"], "G039 proof_relative_path")
    return _digest(
        payload["network_boundary_sha256"],
        "G039 network_boundary_sha256",
    )


def _validate_g040_payload(payload: Mapping[str, Any]) -> str:
    authorization = _validate_bound_artifact(payload["authorization"], "G040 authorization")
    network = _validate_bound_artifact(
        payload["network_boundary_attestation"],
        "G040 network_boundary_attestation",
    )
    for key in (
        "requirements_lock",
        "runtime_policy",
        "backup_policy",
        "storage_adr",
    ):
        _validate_bound_artifact(payload[key], f"G040 {key}")
    python = _object(payload["python"], "G040 python")
    _exact_keys(python, {"path", "sha256", "size", "version"}, "G040 python")
    _absolute_path(python["path"], "G040 python.path")
    _digest(python["sha256"], "G040 python.sha256")
    _plain_int(
        python["size"],
        "G040 python.size",
        minimum=1,
        maximum=_G040_MAX_PYTHON_BYTES,
    )
    python_version = _string(python["version"], "G040 python.version", maximum=32)
    if re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", python_version) is None:
        _fail("G040 python.version must have exactly three numeric components")
    wheel = _object(payload["wheel"], "G040 wheel")
    _exact_keys(
        wheel,
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
        "G040 wheel",
    )
    _absolute_path(wheel["path"], "G040 wheel.path")
    _digest(wheel["sha256"], "G040 wheel.sha256")
    _plain_int(
        wheel["size"],
        "G040 wheel.size",
        minimum=1,
        maximum=_G040_MAX_WHEEL_BYTES,
    )
    for key in (
        "filename",
        "duckdb_version",
        "python_tag",
        "abi_tag",
        "platform_tag",
    ):
        _string(wheel[key], f"G040 wheel.{key}", maximum=255)
    if PurePosixPath(wheel["path"]).name != wheel["filename"]:
        _fail("G040 wheel filename must exactly equal wheel path basename")
    wheel_match = _G040_WHEEL_NAME_RE.fullmatch(wheel["filename"])
    if wheel_match is None:
        _fail("G040 wheel filename is not an exact native CPython DuckDB wheel")
    expected_wheel_fields = (
        wheel["duckdb_version"],
        wheel["python_tag"],
        wheel["abi_tag"],
        wheel["platform_tag"],
    )
    observed_wheel_fields = (
        wheel_match.group("version"),
        wheel_match.group("python"),
        wheel_match.group("abi"),
        wheel_match.group("platform"),
    )
    if observed_wheel_fields != expected_wheel_fields:
        _fail("G040 wheel filename version/ABI/platform fields drift")
    expected_python_tag = "cp" + "".join(python_version.split(".")[:2])
    if wheel["python_tag"] != expected_python_tag or not wheel["abi_tag"].startswith(expected_python_tag):
        _fail("G040 Python version conflicts with wheel CPython/ABI tags")
    _digest(payload["smoke_bootstrap_sha256"], "G040 smoke_bootstrap_sha256")
    _validate_resource_bounds(payload["resource_bounds"], goal_id="WORLDCOIN-G040")
    if wheel["size"] > payload["resource_bounds"]["max_workspace_bytes"]:
        _fail("G040 wheel size exceeds max_workspace_bytes")
    _absolute_path(payload["run_directory"], "G040 run_directory")
    if authorization["sha256"] == network["sha256"]:
        _fail("G040 approval and network-boundary artifacts must be distinct")
    return _digest(network["sha256"], "G040 network boundary attestation")


def _validate_native_plan(
    *,
    goal_id: str,
    payload: Mapping[str, Any],
    authority: ValidatedCandidateAuthority,
) -> str:
    _exact_keys(payload, set(PLAN_KEYS[goal_id]), f"{goal_id} native plan")
    if payload["schema_version"] != NATIVE_PLAN_SCHEMAS[goal_id]:
        _fail(f"{goal_id} native plan schema drift")
    if payload["goal_id"] != goal_id:
        _fail(f"{goal_id} native plan goal drift")
    if payload["network_policy"] != "external-deny-all":
        _fail(f"{goal_id} native plan network policy drift")
    if _timestamp(payload["expires_at"], f"{goal_id} expires_at") != (authority.approval_expires_at):
        _fail(f"{goal_id} expiry differs from the signed approval")

    if goal_id == "WORLDCOIN-G038":
        if (
            payload["authorization_sha256"] != authority.approval_sha256
            or payload["selection_record_id"] != authority.selection_record_id
        ):
            _fail("G038 signed approval binding drift")
        return _validate_g038_payload(payload)
    if goal_id == "WORLDCOIN-G039":
        if payload["authorization_sha256"] != authority.approval_sha256:
            _fail("G039 signed approval binding drift")
        return _validate_g039_payload(payload)
    authorization = _object(payload["authorization"], "G040 authorization")
    if authorization.get("sha256") != authority.approval_sha256:
        _fail("G040 signed approval binding drift")
    return _validate_g040_payload(payload)


def _validate_and_build_plans(
    profile: Mapping[str, Any],
    *,
    authority: ValidatedCandidateAuthority,
    transport: Any,
) -> tuple[ValidatedCandidateExecutionPlan, ...]:
    raw_plans = _array(profile["plans"], "plan profile plans")
    if len(raw_plans) != len(EXPECTED_GOAL_IDS):
        _fail("plan profile must contain exactly three plans")
    policy_digests = dict(authority.runner_sha256)
    result: list[ValidatedCandidateExecutionPlan] = []
    for index, raw_plan in enumerate(raw_plans):
        label = f"plan profile plans[{index}]"
        plan = _object(raw_plan, label)
        _exact_keys(
            plan,
            {
                "goal_id",
                "runner_path",
                "runner_sha256",
                "native_plan_schema",
                "canonicalization",
                "native_plan_sha256",
                "network_boundary_attestation_sha256",
                "plan_payload",
            },
            label,
        )
        goal_id = EXPECTED_GOAL_IDS[index]
        if plan["goal_id"] != goal_id:
            _fail("plan profile plans must use exact deterministic goal order")
        if plan["runner_path"] != EXPECTED_RUNNERS[goal_id]:
            _fail(f"{goal_id} runner path drift")
        if plan["runner_sha256"] != policy_digests[goal_id]:
            _fail(f"{goal_id} runner digest differs from signed operator authority")
        if plan["native_plan_schema"] != NATIVE_PLAN_SCHEMAS[goal_id]:
            _fail(f"{goal_id} native plan schema envelope drift")
        canonicalization = NATIVE_CANONICALIZATION[goal_id]
        if plan["canonicalization"] != canonicalization:
            _fail(f"{goal_id} canonicalization drift")
        payload = _object(plan["plan_payload"], f"{goal_id} plan_payload")
        boundary_sha256 = _validate_native_plan(
            goal_id=goal_id,
            payload=payload,
            authority=authority,
        )
        if plan["network_boundary_attestation_sha256"] != boundary_sha256:
            _fail(f"{goal_id} network-boundary envelope drift")
        payload_bytes = _canonical_json_bytes(
            payload,
            ensure_ascii=canonicalization.endswith("ascii-lf/v1"),
        )
        if len(payload_bytes) > MAX_PLAN_BYTES:
            _fail(f"{goal_id} native plan exceeds {MAX_PLAN_BYTES} bytes")
        plan_sha256 = _sha256_bytes(payload_bytes)
        if plan["native_plan_sha256"] != plan_sha256:
            _fail(f"{goal_id} native plan digest drift")
        try:
            native_plan = transport._decode_plan(goal_id, payload)
        except transport.RunnerTransportV2Error as exc:
            _fail(f"{goal_id} candidate is rejected by runner transport v2: {exc}")
        if goal_id == "WORLDCOIN-G038":
            reconstructed = transport.g038._plan_payload(native_plan)
            native_sha256 = transport.g038.execution_plan_sha256(native_plan)
        elif goal_id == "WORLDCOIN-G039":
            reconstructed = transport.g039._plan_payload(native_plan)
            native_sha256 = transport.g039.execution_plan_sha256(native_plan)
        else:
            reconstructed = transport.g040._plan_payload(native_plan)
            native_sha256 = transport.g040.execution_plan_sha256(native_plan)
        if reconstructed != payload:
            _fail(f"{goal_id} transport/native constructor round-trip drift")
        if native_sha256 != plan_sha256:
            _fail(f"{goal_id} native constructor plan digest drift")
        result.append(
            ValidatedCandidateExecutionPlan(
                goal_id=goal_id,
                runner_path=plan["runner_path"],
                runner_sha256=plan["runner_sha256"],
                native_plan_schema=plan["native_plan_schema"],
                canonicalization=canonicalization,
                native_plan_sha256=plan_sha256,
                network_boundary_attestation_sha256=boundary_sha256,
                payload_bytes=payload_bytes,
            )
        )
    return tuple(result)


def validate_candidate_plans(
    validated: ValidatedCandidateExecutionPlanSet,
    candidate_plans: Mapping[str, Mapping[str, Any]],
) -> None:
    """Reject every caller-authored deviation from digest-bound candidate bytes."""

    if not isinstance(validated, ValidatedCandidateExecutionPlanSet):
        _fail("validated must be ValidatedCandidateExecutionPlanSet")
    if not isinstance(candidate_plans, Mapping):
        _fail("candidate_plans must be a goal-keyed mapping")
    if set(candidate_plans) != set(EXPECTED_GOAL_IDS):
        _fail("candidate_plans must contain exactly G038, G039, and G040")
    for plan in validated.plans:
        candidate = candidate_plans[plan.goal_id]
        if not isinstance(candidate, Mapping):
            _fail(f"caller plan for {plan.goal_id} must be an object")
        candidate_bytes = _canonical_json_bytes(
            dict(candidate),
            ensure_ascii=plan.canonicalization.endswith("ascii-lf/v1"),
        )
        if candidate_bytes != plan.payload_bytes:
            _fail(
                f"caller plan payload drift for {plan.goal_id}; tool paths, "
                "commands, inputs, environments, and resource limits are "
                "operator-profile-owned"
            )


def build_validated_candidate_execution_plans(
    profile_bytes: bytes,
    *,
    expected_profile_sha256: str,
    gate_verifier_summary: Mapping[str, Any],
    selection_approval_bytes: bytes,
    operator_policy_bytes: bytes,
    deployment_attestation_bytes: bytes,
    repo_root: Path,
    candidate_plans: Mapping[str, Mapping[str, Any]] | None = None,
) -> ValidatedCandidateExecutionPlanSet:
    """Build exact candidate bytes after strict authority and drift validation.

    ``gate_verifier_summary`` must be the direct in-memory return value from
    ``verify_world_aid_gate_0b.verify_approval`` in the same sealed launcher
    operation.  Deserializing a caller-supplied summary would not establish a
    signed approval and is outside this contract.

    ``expected_profile_sha256`` must arrive over a separately authenticated
    external channel.  Current Gate 0B selection v2, operator policy v1, and
    deployment attestation v1 cannot supply it.  Passing a digest calculated
    from caller-controlled ``profile_bytes`` defeats this contract.
    """

    if not isinstance(repo_root, Path) or not repo_root.is_absolute():
        _fail("repo_root must be an absolute pathlib.Path")
    expected_profile_digest = _digest(
        expected_profile_sha256,
        "externally authenticated expected_profile_sha256",
    )
    observed_profile_digest = _sha256_bytes(profile_bytes)
    if observed_profile_digest != expected_profile_digest:
        _fail("execution plan profile digest differs from external authority")
    profile = _object(
        _load_json(
            profile_bytes,
            label="execution plan profile",
            maximum_bytes=MAX_PROFILE_BYTES,
            require_canonical=True,
            ensure_ascii=True,
        ),
        "execution plan profile",
    )
    _exact_keys(
        profile,
        {
            "schema",
            "profile_id",
            "status",
            "candidate_validation_enabled",
            "runtime_authorized",
            "contract",
            "authority",
            "protocol",
            "plans",
        },
        "execution plan profile",
    )
    if profile["schema"] != PROFILE_SCHEMA:
        _fail(f"execution plan profile schema must be {PROFILE_SCHEMA}")
    profile_id = _string(profile["profile_id"], "profile_id", maximum=128)
    if _PROFILE_ID_RE.fullmatch(profile_id) is None:
        _fail("execution plan profile_id is invalid")
    if (
        profile["status"] != "candidate-ready-for-external-authentication"
        or profile["candidate_validation_enabled"] is not True
    ):
        _fail("execution plan candidate profile is pending or disabled")
    if profile["runtime_authorized"] is not False:
        _fail("execution plan profile must never grant runtime authority")

    authority, _, _ = _validate_authority(
        gate_verifier_summary=gate_verifier_summary,
        selection_approval_bytes=selection_approval_bytes,
        operator_policy_bytes=operator_policy_bytes,
        deployment_attestation_bytes=deployment_attestation_bytes,
    )
    verified_contract_digests = _validate_contract_files(profile, repo_root)
    _validate_profile_authority(profile, authority)
    _validate_protocol(profile)
    _validate_signed_repository_artifacts(
        authority=authority,
        repo_root=repo_root,
    )
    transport = _load_verified_transport_codec(
        profile=profile,
        repo_root=repo_root,
        verified_contract_digests=verified_contract_digests,
    )
    plans = _validate_and_build_plans(
        profile,
        authority=authority,
        transport=transport,
    )
    result = ValidatedCandidateExecutionPlanSet(
        profile_id=profile_id,
        profile_sha256=observed_profile_digest,
        authority=authority,
        plans=plans,
        runtime_authorized=False,
    )
    if candidate_plans is not None:
        validate_candidate_plans(result, candidate_plans)
    return result


__all__ = [
    "ValidatedCandidateAuthority",
    "ValidatedCandidateExecutionPlan",
    "ValidatedCandidateExecutionPlanSet",
    "BUILDER_PATH",
    "CONTRACT_ID",
    "ExecutionPlanContractError",
    "EXPECTED_GOAL_IDS",
    "EXPECTED_RUNNERS",
    "NATIVE_CANONICALIZATION",
    "NATIVE_PLAN_SCHEMAS",
    "PROFILE_SCHEMA",
    "SCHEMA_PATH",
    "build_validated_candidate_execution_plans",
    "validate_candidate_plans",
]
