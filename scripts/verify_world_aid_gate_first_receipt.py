#!/usr/bin/env python3
"""Verify an immutable, externally signed World-aid Gate-first run receipt.

The verifier accepts a run identifier only.  Receipt roots, signer identity,
signer fingerprint, trust stores, goals, runners, and tools all come from the
fixed operator policy.  It never creates or signs a receipt and never executes
a bootstrap goal.

This repository copy is review material.  It becomes authoritative only when
its exact bytes are pinned and invoked by the externally installed launcher.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import os
import re
import subprocess
import sys
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

if __package__:
    from scripts.world_aid_gate_first_launcher import (
        EXPECTED_CLEAN_ENVIRONMENT,
        EXPECTED_GOAL_IDS,
        FIXED_OPERATOR_POLICY_PATH,
        ROOT_OPERATOR_CONTEXT,
        ExternalSecurityContext,
        GateFirstLauncherError,
        OperatorPolicy,
        SealedFileSnapshot,
        _communicate_bounded,
        _new_sealed_memfd,
        _open_directory_no_symlink,
        _secure_external_snapshot,
        _sha256_bytes,
        load_json_strict,
        load_operator_policy,
        snapshot_regular_file_at,
        validate_authority_environment,
        validate_isolated_interpreter,
    )
else:
    from world_aid_gate_first_launcher import (  # type: ignore[no-redef]
        EXPECTED_CLEAN_ENVIRONMENT,
        EXPECTED_GOAL_IDS,
        FIXED_OPERATOR_POLICY_PATH,
        ROOT_OPERATOR_CONTEXT,
        ExternalSecurityContext,
        GateFirstLauncherError,
        OperatorPolicy,
        SealedFileSnapshot,
        _communicate_bounded,
        _new_sealed_memfd,
        _open_directory_no_symlink,
        _secure_external_snapshot,
        _sha256_bytes,
        load_json_strict,
        load_operator_policy,
        snapshot_regular_file_at,
        validate_authority_environment,
        validate_isolated_interpreter,
    )

RUN_RECEIPT_SCHEMA = "world-aid-gate-first-run-receipt/v1"
GOAL_RESULT_SCHEMA = "world-aid-gate-first-goal-result/v1"
VERIFY_RESULT_SCHEMA = "world-aid-gate-first-receipt-verification/v1"
RECEIPT_FILENAME = "receipt.json"
SIGNATURE_FILENAME = "receipt.sshsig"
RUN_ID_RE = re.compile(r"^gate-first-[a-z0-9][a-z0-9._-]{7,95}$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
RECORD_ID_RE = re.compile(r"^gate-0b-selection-[a-z0-9][a-z0-9._-]{7,95}$")
TIMESTAMP_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"
)
MAX_RECEIPT_BYTES = 2 * 1024 * 1024
MAX_GOAL_RESULT_BYTES = 8 * 1024 * 1024
MAX_SIGNATURE_BYTES = 64 * 1024
MAX_ALLOWED_SIGNERS_BYTES = 256 * 1024
G038_RECEIPT_SCHEMA = "world-human-aid-siwe-bootstrap-verification-receipt/v2"
G039_RECEIPT_SCHEMA = "world-human-aid-g039-native-smoke-receipt/v1"
G040_RECEIPT_SCHEMA = "world-human-aid-g040-duckdb-bootstrap-receipt/v1"
G040_REQUIRED_CHECKS = (
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
G040_DENY_SETTINGS = {
    "allow_community_extensions": "false",
    "autoinstall_known_extensions": "false",
    "autoload_known_extensions": "false",
    "enable_external_access": "false",
    "lock_configuration": "true",
}
G040_EXCLUDED_CONTROLS = [
    "application_envelope_encryption",
    "plaintext_marker_absence",
    "encrypted_authenticated_production_backup",
    "key_rotation_retention_and_deletion",
]


class GateFirstReceiptError(RuntimeError):
    """Raised when signed launcher evidence fails closed."""


def _fail(message: str) -> None:
    raise GateFirstReceiptError(message)


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


def _digest(value: Any, label: str) -> str:
    text = _string(value, label, maximum=71)
    if not DIGEST_RE.fullmatch(text):
        _fail(f"{label} must be a lowercase sha256 digest")
    return text


def _matches_exact_type(value: Any, expected: Any) -> bool:
    if isinstance(expected, bool):
        return value is expected
    return value == expected


def _plain_int(
    value: Any,
    label: str,
    *,
    minimum: int = 0,
    maximum: int = 2**63 - 1,
) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        _fail(f"{label} must be an integer")
    if not minimum <= value <= maximum:
        _fail(f"{label} must be an integer from {minimum} through {maximum}")
    return value


def _timestamp(value: Any, label: str) -> datetime:
    text = _string(value, label, minimum=20, maximum=20)
    if not TIMESTAMP_RE.fullmatch(text):
        _fail(f"{label} must be a second-precision UTC timestamp")
    try:
        parsed = datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except ValueError as exc:
        _fail(f"{label} is not a real timestamp: {exc}")
    return parsed


def canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    """Return the exact byte representation accepted for signed receipts."""

    try:
        rendered = json.dumps(
            payload,
            ensure_ascii=True,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (RecursionError, TypeError, ValueError) as exc:
        _fail(f"receipt cannot be encoded canonically: {exc}")
    return (rendered + "\n").encode("utf-8")


def _load_canonical_json(raw: bytes, *, label: str) -> Mapping[str, Any]:
    try:
        payload = _object(load_json_strict(raw, label=label), label)
    except GateFirstLauncherError as exc:
        _fail(str(exc))
    if canonical_json_bytes(payload) != raw:
        _fail(f"{label} is not in the required canonical JSON representation")
    return payload


def _safe_result_path(value: Any, goal_id: str) -> str:
    text = _string(value, f"{goal_id} result_path", maximum=256)
    expected = f"goals/{goal_id}.json"
    path = PurePosixPath(text)
    if (
        text != expected
        or path.is_absolute()
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        _fail(f"{goal_id} result_path must be {expected}")
    return text


def _validate_command_evidence(value: Any, label: str) -> None:
    command = _object(value, label)
    _exact_keys(
        command,
        {
            "exit_code",
            "elapsed_ms",
            "stdout_sha256",
            "stdout_bytes",
            "stderr_sha256",
            "stderr_bytes",
        },
        label,
    )
    if command["exit_code"] != 0 or isinstance(command["exit_code"], bool):
        _fail(f"{label}.exit_code must be the integer zero")
    _plain_int(command["elapsed_ms"], f"{label}.elapsed_ms")
    _digest(command["stdout_sha256"], f"{label}.stdout_sha256")
    _plain_int(command["stdout_bytes"], f"{label}.stdout_bytes")
    _digest(command["stderr_sha256"], f"{label}.stderr_sha256")
    _plain_int(command["stderr_bytes"], f"{label}.stderr_bytes")


def _validate_native_completed_at(
    native: Mapping[str, Any],
    *,
    label: str,
    started_at: datetime,
    completed_at: datetime,
) -> datetime:
    native_completed = _timestamp(native.get("completed_at"), f"{label}.completed_at")
    if not started_at <= native_completed <= completed_at:
        _fail(f"{label}.completed_at is outside the enclosing goal result interval")
    return native_completed


def _validate_g038_native_receipt(
    native: Mapping[str, Any],
    *,
    selection_approval_sha256: str,
    started_at: datetime,
    completed_at: datetime,
) -> None:
    label = "WORLDCOIN-G038 native receipt"
    _exact_keys(
        native,
        {
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
            "cache_mutated",
            "toolchain",
            "inputs",
            "cache",
            "network",
            "smoke_result",
        },
        label,
    )
    expected = {
        "schema_version": G038_RECEIPT_SCHEMA,
        "goal_id": "WORLDCOIN-G038",
        "status": "passed",
        "offline": True,
        "live_actions_authorized": False,
        "selection_approval_sha256": selection_approval_sha256,
        "real_execution": True,
        "cache_mutated": False,
    }
    for key, expected_value in expected.items():
        if not _matches_exact_type(native[key], expected_value):
            _fail(f"{label} has invalid {key}")
    _string(native["selection_record_id"], f"{label}.selection_record_id", maximum=112)
    native_completed = _validate_native_completed_at(
        native,
        label=label,
        started_at=started_at,
        completed_at=completed_at,
    )
    if _timestamp(native["valid_until"], f"{label}.valid_until") <= native_completed:
        _fail(f"{label}.valid_until must follow completed_at")

    toolchain = _object(native["toolchain"], f"{label}.toolchain")
    _exact_keys(
        toolchain,
        {
            "platform",
            "architecture",
            "archive_sha256",
            "node_sha256",
            "node_version",
            "npm_cli_sha256",
            "npm_version",
        },
        f"{label}.toolchain",
    )
    _string(toolchain["platform"], f"{label}.toolchain.platform", maximum=128)
    _string(toolchain["architecture"], f"{label}.toolchain.architecture", maximum=128)
    for key in ("archive_sha256", "node_sha256", "npm_cli_sha256"):
        _digest(toolchain[key], f"{label}.toolchain.{key}")
    _string(toolchain["node_version"], f"{label}.toolchain.node_version", maximum=32)
    _string(toolchain["npm_version"], f"{label}.toolchain.npm_version", maximum=32)

    inputs = _object(native["inputs"], f"{label}.inputs")
    _exact_keys(inputs, {"manifest_sha256", "lock_sha256", "adapter_sha256"}, f"{label}.inputs")
    for key in inputs:
        _digest(inputs[key], f"{label}.inputs.{key}")

    cache = _object(native["cache"], f"{label}.cache")
    _exact_keys(
        cache,
        {
            "reviewed_before_sha256",
            "reviewed_after_sha256",
            "local_before_sha256",
            "local_after_sha256",
        },
        f"{label}.cache",
    )
    for key in cache:
        _digest(cache[key], f"{label}.cache.{key}")
    if cache["reviewed_before_sha256"] != cache["reviewed_after_sha256"]:
        _fail(f"{label} reports mutation of the reviewed cache")

    network = _object(native["network"], f"{label}.network")
    _exact_keys(
        network,
        {
            "enforcement",
            "attempt_monitor",
            "attempt_count",
            "external_network_succeeded",
            "boundary_before",
            "boundary_after",
        },
        f"{label}.network",
    )
    if (
        network["enforcement"] != "signed-namespace-plus-apparmor"
        or network["attempt_monitor"] != "not-configured"
        or network["attempt_count"] is not None
        or network["external_network_succeeded"] is not False
    ):
        _fail(f"{label} does not prove the exact no-external-network outcome")
    before = _object(network["boundary_before"], f"{label}.network.boundary_before")
    after = _object(network["boundary_after"], f"{label}.network.boundary_after")
    boundary_keys = {
        "namespace",
        "apparmor_profile",
        "interfaces",
        "no_external_route",
        "network_deny_canary_sha256",
        "egress_policy_sha256",
    }
    _exact_keys(before, boundary_keys, f"{label}.network.boundary_before")
    _exact_keys(after, boundary_keys, f"{label}.network.boundary_after")
    if before != after:
        _fail(f"{label} network boundary changed during execution")
    if before["interfaces"] != ["lo"] or before["no_external_route"] is not True:
        _fail(f"{label} network boundary is not loopback-only with no external route")
    _string(before["namespace"], f"{label}.network.boundary_before.namespace", maximum=256)
    _string(
        before["apparmor_profile"],
        f"{label}.network.boundary_before.apparmor_profile",
        maximum=256,
    )
    for key in ("network_deny_canary_sha256", "egress_policy_sha256"):
        _digest(before[key], f"{label}.network.boundary_before.{key}")

    smoke = _object(native["smoke_result"], f"{label}.smoke_result")
    _exact_keys(smoke, {"eoa", "eip1271", "contractReads"}, f"{label}.smoke_result")
    if (
        smoke["eoa"] is not True
        or smoke["eip1271"] is not True
        or isinstance(smoke["contractReads"], bool)
        or smoke["contractReads"] != 1
    ):
        _fail(f"{label} does not prove exact EOA and EIP-1271 smoke success")


def _validate_g039_native_receipt(
    native: Mapping[str, Any],
    *,
    selection_approval_sha256: str,
    execution_plan_sha256: str,
    network_boundary_attestation_sha256: str,
    started_at: datetime,
    completed_at: datetime,
) -> None:
    label = "WORLDCOIN-G039 native receipt"
    _exact_keys(
        native,
        {
            "schema_version",
            "goal_id",
            "execution_plan_sha256",
            "authorization_sha256",
            "tool",
            "inputs",
            "repeat_build_hashes",
            "proof_sha256",
            "proof_result",
            "verify_result",
            "network_registry_denied",
            "network_boundary",
            "resource_bounds",
            "expiry",
            "commands",
            "production_trust",
            "completed_at",
        },
        label,
    )
    expected = {
        "schema_version": G039_RECEIPT_SCHEMA,
        "goal_id": "WORLDCOIN-G039",
        "execution_plan_sha256": execution_plan_sha256,
        "authorization_sha256": selection_approval_sha256,
        "proof_result": True,
        "verify_result": True,
        "network_registry_denied": True,
        "production_trust": False,
    }
    for key, expected_value in expected.items():
        if not _matches_exact_type(native[key], expected_value):
            _fail(f"{label} has invalid {key}")
    native_completed = _validate_native_completed_at(
        native,
        label=label,
        started_at=started_at,
        completed_at=completed_at,
    )
    if _timestamp(native["expiry"], f"{label}.expiry") <= native_completed:
        _fail(f"{label}.expiry must follow completed_at")

    tool = _object(native["tool"], f"{label}.tool")
    _exact_keys(tool, {"path", "sha256", "max_bytes"}, f"{label}.tool")
    _string(tool["path"], f"{label}.tool.path", maximum=4096)
    _digest(tool["sha256"], f"{label}.tool.sha256")
    _plain_int(tool["max_bytes"], f"{label}.tool.max_bytes", minimum=1)

    raw_inputs = native["inputs"]
    if not isinstance(raw_inputs, list) or not raw_inputs:
        _fail(f"{label}.inputs must be a non-empty JSON array")
    for index, raw_input in enumerate(raw_inputs):
        item_label = f"{label}.inputs[{index}]"
        item = _object(raw_input, item_label)
        _exact_keys(
            item,
            {"source_path", "sha256", "max_bytes", "workspace_relative_path"},
            item_label,
        )
        _string(item["source_path"], f"{item_label}.source_path", maximum=4096)
        _digest(item["sha256"], f"{item_label}.sha256")
        _plain_int(item["max_bytes"], f"{item_label}.max_bytes", minimum=1)
        _string(
            item["workspace_relative_path"],
            f"{item_label}.workspace_relative_path",
            maximum=1024,
        )

    repeat_hashes = native["repeat_build_hashes"]
    if (
        not isinstance(repeat_hashes, list)
        or len(repeat_hashes) != 2
        or repeat_hashes[0] != repeat_hashes[1]
    ):
        _fail(f"{label} does not prove two reproducible native builds")
    for index, value in enumerate(repeat_hashes):
        _digest(value, f"{label}.repeat_build_hashes[{index}]")
    _digest(native["proof_sha256"], f"{label}.proof_sha256")

    boundary = _object(native["network_boundary"], f"{label}.network_boundary")
    _exact_keys(boundary, {"policy", "attestation_sha256", "authority"}, f"{label}.network_boundary")
    if (
        boundary["policy"] != "external-deny-all"
        or boundary["attestation_sha256"] != network_boundary_attestation_sha256
        or boundary["authority"] != "external-gate-first-launcher"
    ):
        _fail(f"{label} has invalid network boundary binding")

    resources = _object(native["resource_bounds"], f"{label}.resource_bounds")
    _exact_keys(
        resources,
        {
            "max_seconds",
            "max_memory_mb",
            "max_output_bytes",
            "max_open_files",
            "observed_process_output_bytes",
        },
        f"{label}.resource_bounds",
    )
    for key in ("max_seconds", "max_memory_mb", "max_output_bytes", "max_open_files"):
        _plain_int(resources[key], f"{label}.resource_bounds.{key}", minimum=1)
    observed = _plain_int(
        resources["observed_process_output_bytes"],
        f"{label}.resource_bounds.observed_process_output_bytes",
    )
    if observed > resources["max_output_bytes"]:
        _fail(f"{label} observed output exceeds its authenticated bound")

    commands = _object(native["commands"], f"{label}.commands")
    _exact_keys(commands, {"build_a", "build_b", "prove", "verify"}, f"{label}.commands")
    for command_name in ("build_a", "build_b", "prove", "verify"):
        _validate_command_evidence(commands[command_name], f"{label}.commands.{command_name}")


def _validate_g040_second_writer(value: Any, label: str) -> None:
    writer = _object(value, label)
    _exact_keys(
        writer,
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
        label,
    )
    if (
        writer["schema_version"] != "world-human-aid-g040-second-writer/v1"
        or writer["import_succeeded"] is not True
        or writer["connect_attempted"] is not True
        or writer["rejected"] is not True
        or writer["exception_module"] != "_duckdb"
        or writer["exception_type"] != "IOException"
    ):
        _fail(f"{label} does not prove an independent DuckDB lock rejection")
    stage = writer["rejection_stage"]
    connected = writer["connect_succeeded"]
    write_attempted = writer["write_attempted"]
    if (
        not isinstance(connected, bool)
        or not isinstance(write_attempted, bool)
        or not (
            stage == "connect" and connected is False and write_attempted is False
            or stage == "write" and connected is True and write_attempted is True
        )
    ):
        _fail(f"{label} has inconsistent rejection-stage flags")
    if writer["lock_marker"] not in {
        "could not set lock",
        "conflicting lock",
        "database is locked",
        "lock on file",
        "cannot acquire lock",
        "failed to acquire lock",
    }:
        _fail(f"{label} lacks an accepted lock-conflict marker")
    message_sha256 = _string(writer["message_sha256"], f"{label}.message_sha256", maximum=64)
    if re.fullmatch(r"[0-9a-f]{64}", message_sha256) is None:
        _fail(f"{label}.message_sha256 must be a lowercase unprefixed SHA-256 digest")
    _plain_int(writer["message_bytes"], f"{label}.message_bytes", minimum=1, maximum=4096)
    if not isinstance(writer["message_truncated"], bool):
        _fail(f"{label}.message_truncated must be a boolean")


def _validate_g040_native_receipt(
    native: Mapping[str, Any],
    *,
    selection_approval_sha256: str,
    execution_plan_sha256: str,
    network_boundary_attestation_sha256: str,
    started_at: datetime,
    completed_at: datetime,
) -> None:
    label = "WORLDCOIN-G040 native receipt"
    _exact_keys(
        native,
        {
            "schema_version",
            "goal_id",
            "status",
            "execution_plan_sha256",
            "authorization_sha256",
            "network_boundary",
            "python",
            "wheel",
            "reviewed_inputs",
            "smoke_bootstrap_sha256",
            "checks",
            "cleanup",
            "deny_settings",
            "loaded_dynamic_extensions",
            "network_attempts",
            "single_writer_enforced",
            "second_writer_evidence",
            "g033_excluded_controls",
            "resource_bounds",
            "command",
            "offline",
            "live_actions_authorized",
            "production_trust",
            "expires_at",
            "completed_at",
        },
        label,
    )
    expected = {
        "schema_version": G040_RECEIPT_SCHEMA,
        "goal_id": "WORLDCOIN-G040",
        "status": "passed",
        "execution_plan_sha256": execution_plan_sha256,
        "authorization_sha256": selection_approval_sha256,
        "loaded_dynamic_extensions": [],
        "network_attempts": 0,
        "single_writer_enforced": True,
        "g033_excluded_controls": G040_EXCLUDED_CONTROLS,
        "offline": True,
        "live_actions_authorized": False,
        "production_trust": False,
    }
    for key, expected_value in expected.items():
        if not _matches_exact_type(native[key], expected_value):
            _fail(f"{label} has invalid {key}")
    if isinstance(native["network_attempts"], bool):
        _fail(f"{label}.network_attempts must be the integer zero")
    native_completed = _validate_native_completed_at(
        native,
        label=label,
        started_at=started_at,
        completed_at=completed_at,
    )
    if _timestamp(native["expires_at"], f"{label}.expires_at") <= native_completed:
        _fail(f"{label}.expires_at must follow completed_at")

    boundary = _object(native["network_boundary"], f"{label}.network_boundary")
    _exact_keys(boundary, {"policy", "attestation_sha256", "authority"}, f"{label}.network_boundary")
    if (
        boundary["policy"] != "external-deny-all"
        or boundary["attestation_sha256"] != network_boundary_attestation_sha256
        or boundary["authority"] != "external-gate-first-launcher"
    ):
        _fail(f"{label} has invalid network boundary binding")

    python = _object(native["python"], f"{label}.python")
    _exact_keys(python, {"path", "sha256", "size", "version", "flags"}, f"{label}.python")
    _string(python["path"], f"{label}.python.path", maximum=4096)
    _digest(python["sha256"], f"{label}.python.sha256")
    _plain_int(python["size"], f"{label}.python.size", minimum=1)
    _string(python["version"], f"{label}.python.version", maximum=32)
    if python["flags"] != ["-I", "-S", "-B"]:
        _fail(f"{label}.python.flags do not prove an isolated interpreter")

    wheel = _object(native["wheel"], f"{label}.wheel")
    _exact_keys(
        wheel,
        {
            "path",
            "filename",
            "sha256",
            "size",
            "duckdb_version",
            "python_tag",
            "abi_tag",
            "platform_tag",
            "validation",
        },
        f"{label}.wheel",
    )
    for key in ("path", "filename", "duckdb_version", "python_tag", "abi_tag", "platform_tag"):
        _string(wheel[key], f"{label}.wheel.{key}", maximum=4096)
    _digest(wheel["sha256"], f"{label}.wheel.sha256")
    _plain_int(wheel["size"], f"{label}.wheel.size", minimum=1)
    validation = _object(wheel["validation"], f"{label}.wheel.validation")
    _exact_keys(
        validation,
        {
            "entry_count",
            "file_count",
            "uncompressed_bytes",
            "record_count",
            "metadata_name",
            "metadata_version",
            "wheel_tag",
        },
        f"{label}.wheel.validation",
    )
    for key in ("entry_count", "file_count", "uncompressed_bytes", "record_count"):
        _plain_int(validation[key], f"{label}.wheel.validation.{key}", minimum=1)
    for key in ("metadata_name", "metadata_version", "wheel_tag"):
        _string(validation[key], f"{label}.wheel.validation.{key}", maximum=256)

    reviewed_inputs = _object(native["reviewed_inputs"], f"{label}.reviewed_inputs")
    _exact_keys(
        reviewed_inputs,
        {"requirements_lock", "runtime_policy", "backup_policy", "storage_adr"},
        f"{label}.reviewed_inputs",
    )
    for role, raw_artifact in reviewed_inputs.items():
        artifact = _object(raw_artifact, f"{label}.reviewed_inputs.{role}")
        _exact_keys(artifact, {"source_path", "sha256", "size"}, f"{label}.reviewed_inputs.{role}")
        _string(artifact["source_path"], f"{label}.reviewed_inputs.{role}.source_path", maximum=4096)
        _digest(artifact["sha256"], f"{label}.reviewed_inputs.{role}.sha256")
        _plain_int(artifact["size"], f"{label}.reviewed_inputs.{role}.size", minimum=1)
    _digest(native["smoke_bootstrap_sha256"], f"{label}.smoke_bootstrap_sha256")

    checks = _object(native["checks"], f"{label}.checks")
    _exact_keys(checks, set(G040_REQUIRED_CHECKS), f"{label}.checks")
    for check_name in G040_REQUIRED_CHECKS:
        if checks[check_name] is not True:
            _fail(f"{label}.checks.{check_name} did not pass")

    cleanup = _object(native["cleanup"], f"{label}.cleanup")
    exact_cleanup = {
        "database_exists": False,
        "temporary_data_exists": False,
        "wal_exists": False,
        "isolated_site_removed_before_publication": True,
        "workspace_removed_before_publication": True,
    }
    _exact_keys(cleanup, set(exact_cleanup), f"{label}.cleanup")
    for key, expected_value in exact_cleanup.items():
        if cleanup[key] is not expected_value:
            _fail(f"{label}.cleanup.{key} does not prove complete teardown")

    deny_settings = _object(native["deny_settings"], f"{label}.deny_settings")
    _exact_keys(deny_settings, set(G040_DENY_SETTINGS), f"{label}.deny_settings")
    if dict(deny_settings) != G040_DENY_SETTINGS:
        _fail(f"{label}.deny_settings do not prove locked extension/network denial")
    _validate_g040_second_writer(
        native["second_writer_evidence"],
        f"{label}.second_writer_evidence",
    )

    resources = _object(native["resource_bounds"], f"{label}.resource_bounds")
    resource_keys = {
        "max_seconds",
        "max_memory_mb",
        "max_output_bytes",
        "max_file_bytes",
        "max_workspace_bytes",
        "max_wheel_entries",
        "max_entry_bytes",
        "max_uncompressed_bytes",
        "max_open_files",
        "observed_process_output_bytes",
        "observed_workspace_bytes_before_cleanup",
    }
    _exact_keys(resources, resource_keys, f"{label}.resource_bounds")
    for key in resource_keys - {
        "observed_process_output_bytes",
        "observed_workspace_bytes_before_cleanup",
    }:
        _plain_int(resources[key], f"{label}.resource_bounds.{key}", minimum=1)
    observed_output = _plain_int(
        resources["observed_process_output_bytes"],
        f"{label}.resource_bounds.observed_process_output_bytes",
    )
    observed_workspace = _plain_int(
        resources["observed_workspace_bytes_before_cleanup"],
        f"{label}.resource_bounds.observed_workspace_bytes_before_cleanup",
    )
    if observed_output > resources["max_output_bytes"]:
        _fail(f"{label} observed output exceeds its authenticated bound")
    if observed_workspace > resources["max_workspace_bytes"]:
        _fail(f"{label} observed workspace exceeds its authenticated bound")
    _validate_command_evidence(native["command"], f"{label}.command")


def _validate_goal_evidence(
    value: Any,
    *,
    goal_id: str,
    selection_approval_sha256: str,
    started_at: datetime,
    completed_at: datetime,
) -> None:
    label = f"{goal_id} result.evidence"
    evidence = _object(value, label)
    _exact_keys(
        evidence,
        {
            "native_receipt",
            "native_receipt_sha256",
            "execution_plan_sha256",
            "network_boundary_attestation_sha256",
        },
        label,
    )
    native = _object(evidence["native_receipt"], f"{label}.native_receipt")
    declared_native_digest = _digest(
        evidence["native_receipt_sha256"],
        f"{label}.native_receipt_sha256",
    )
    observed_native_digest = _sha256_bytes(canonical_json_bytes(native))
    if declared_native_digest != observed_native_digest:
        _fail(f"{label}.native_receipt_sha256 differs from the canonical native receipt")
    plan_digest = _digest(evidence["execution_plan_sha256"], f"{label}.execution_plan_sha256")
    boundary_digest = _digest(
        evidence["network_boundary_attestation_sha256"],
        f"{label}.network_boundary_attestation_sha256",
    )
    if goal_id == "WORLDCOIN-G038":
        # The legacy Gate-compatible G038 v2 native receipt has a frozen exact
        # shape and cannot gain plan or boundary-attestation fields.  Those two
        # digests therefore remain exact launcher-produced wrapper bindings:
        # the signed aggregate binds this whole goal result by its digest.  Do
        # not mistake them for native cross-fields or relax their envelope.
        _validate_g038_native_receipt(
            native,
            selection_approval_sha256=selection_approval_sha256,
            started_at=started_at,
            completed_at=completed_at,
        )
    elif goal_id == "WORLDCOIN-G039":
        _validate_g039_native_receipt(
            native,
            selection_approval_sha256=selection_approval_sha256,
            execution_plan_sha256=plan_digest,
            network_boundary_attestation_sha256=boundary_digest,
            started_at=started_at,
            completed_at=completed_at,
        )
    elif goal_id == "WORLDCOIN-G040":
        _validate_g040_native_receipt(
            native,
            selection_approval_sha256=selection_approval_sha256,
            execution_plan_sha256=plan_digest,
            network_boundary_attestation_sha256=boundary_digest,
            started_at=started_at,
            completed_at=completed_at,
        )
    else:
        _fail(f"{label} belongs to an unsupported goal")


def _validate_goal_result(
    raw: bytes,
    *,
    run_id: str,
    goal_id: str,
    runner_sha256: str,
    selection_approval_sha256: str,
) -> Mapping[str, Any]:
    result = _load_canonical_json(raw, label=f"{goal_id} result")
    _exact_keys(
        result,
        {
            "schema",
            "run_id",
            "goal_id",
            "status",
            "offline",
            "live_actions_authorized",
            "runner_sha256",
            "selection_approval_sha256",
            "started_at",
            "completed_at",
            "evidence",
        },
        f"{goal_id} result",
    )
    expected_values = {
        "schema": GOAL_RESULT_SCHEMA,
        "run_id": run_id,
        "goal_id": goal_id,
        "status": "passed",
        "offline": True,
        "live_actions_authorized": False,
        "runner_sha256": runner_sha256,
        "selection_approval_sha256": selection_approval_sha256,
    }
    for key, expected in expected_values.items():
        if not _matches_exact_type(result[key], expected):
            _fail(f"{goal_id} result has invalid {key}")
    started = _timestamp(result["started_at"], f"{goal_id} result.started_at")
    completed = _timestamp(result["completed_at"], f"{goal_id} result.completed_at")
    if completed < started:
        _fail(f"{goal_id} result completion precedes its start")
    _validate_goal_evidence(
        result["evidence"],
        goal_id=goal_id,
        selection_approval_sha256=selection_approval_sha256,
        started_at=started,
        completed_at=completed,
    )
    return result


def _parse_selection_approval(raw: bytes) -> tuple[str, str]:
    try:
        approval = _object(load_json_strict(raw, label="selection approval"), "selection approval")
    except GateFirstLauncherError as exc:
        _fail(str(exc))
    record_id = _string(approval.get("record_id"), "selection approval.record_id", maximum=112)
    if not RECORD_ID_RE.fullmatch(record_id):
        _fail("selection approval record id is invalid")
    reviewed = _object(approval.get("reviewed_state"), "selection approval.reviewed_state")
    root_commit = _string(
        reviewed.get("root_commit"), "selection approval.reviewed_state.root_commit", maximum=40
    )
    if not COMMIT_RE.fullmatch(root_commit):
        _fail("selection approval root commit is invalid")
    return record_id, root_commit


def _key_fingerprint(key_blob: str) -> str:
    try:
        decoded = base64.b64decode(key_blob.encode("ascii"), validate=True)
    except (UnicodeEncodeError, binascii.Error) as exc:
        _fail(f"receipt attestation key is not valid base64: {exc}")
    if not decoded:
        _fail("receipt attestation key blob is empty")
    encoded = base64.b64encode(hashlib.sha256(decoded).digest()).decode("ascii").rstrip("=")
    return f"SHA256:{encoded}"


def _exact_allowed_signer_line(
    raw: bytes,
    *,
    identity: str,
    fingerprint: str,
) -> bytes:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        _fail(f"receipt allowed-signers store is not UTF-8: {exc}")
    lines = [line for line in text.splitlines() if line]
    if len(lines) != 1:
        _fail("receipt allowed-signers store must contain exactly one non-empty key line")
    fields = lines[0].split()
    if len(fields) != 3:
        _fail("receipt allowed-signers line must be '<identity> ssh-ed25519 <key>'")
    observed_identity, key_type, key_blob = fields
    if observed_identity != identity or "," in observed_identity:
        _fail("receipt allowed-signers identity differs from operator policy")
    if key_type != "ssh-ed25519":
        _fail("receipt attestation key must be ssh-ed25519")
    if _key_fingerprint(key_blob) != fingerprint:
        _fail("receipt attestation key fingerprint differs from operator policy")
    return f"{observed_identity} {key_type} {key_blob}\n".encode("ascii")


def _verify_signature(
    *,
    policy: OperatorPolicy,
    receipt_raw: bytes,
    signature: SealedFileSnapshot,
    allowed_signers_raw: bytes,
) -> None:
    exact_line = _exact_allowed_signer_line(
        allowed_signers_raw,
        identity=policy.receipt_signer_identity,
        fingerprint=policy.receipt_signer_fingerprint,
    )
    trust_fd = _new_sealed_memfd("world-aid-receipt-signer", exact_line)
    receipt_fd = _new_sealed_memfd("world-aid-signed-receipt", receipt_raw)
    try:
        command = [
            policy.ssh_keygen_path.as_posix(),
            "-Y",
            "verify",
            "-f",
            f"/proc/self/fd/{trust_fd}",
            "-I",
            policy.receipt_signer_identity,
            "-n",
            policy.receipt_signature_namespace,
            "-s",
            f"/proc/self/fd/{signature.fd}",
        ]
        process = subprocess.Popen(
            command,
            stdin=receipt_fd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=dict(EXPECTED_CLEAN_ENVIRONMENT),
            close_fds=True,
            pass_fds=(trust_fd, signature.fd),
            start_new_session=True,
        )
        stdout, stderr = _communicate_bounded(
            process,
            timeout_seconds=policy.gate_timeout_seconds,
            maximum_bytes=policy.max_child_output_bytes,
            label="receipt signature verification",
        )
        if process.returncode != 0:
            detail = stderr.decode("utf-8", errors="replace").strip()
            _fail(f"receipt signature is invalid: {detail[:1000]}")
    finally:
        os.close(receipt_fd)
        os.close(trust_fd)


def _secure_policy_file(
    path: Path,
    expected_sha256: str | None,
    *,
    context: ExternalSecurityContext,
    label: str,
    maximum_bytes: int,
    write_mask: int,
    single_link: bool,
) -> SealedFileSnapshot:
    try:
        snapshot = _secure_external_snapshot(
            path,
            context=context,
            maximum_bytes=maximum_bytes,
            label=label,
            leaf_write_mask=write_mask,
            require_single_link=single_link,
        )
    except GateFirstLauncherError as exc:
        _fail(str(exc))
    if expected_sha256 is not None and snapshot.sha256 != expected_sha256:
        snapshot.close()
        _fail(f"{label} digest differs from operator policy")
    return snapshot


def verify_gate_first_receipt(
    *,
    policy: OperatorPolicy,
    run_id: str,
    context: ExternalSecurityContext = ROOT_OPERATOR_CONTEXT,
) -> dict[str, Any]:
    """Verify one immutable signed run and all three content-bound results."""

    if not RUN_ID_RE.fullmatch(run_id):
        _fail("run id is invalid")
    if not policy.run_selection_enabled:
        _fail("operator policy does not enable externally injected runners")
    runner_by_goal = {runner.goal_id: runner for runner in policy.runners}
    if set(runner_by_goal) != set(EXPECTED_GOAL_IDS):
        _fail("operator policy does not bind all three dedicated runners")

    snapshots: list[SealedFileSnapshot] = []
    repo_fd = _open_directory_no_symlink(policy.repo_root)
    try:
        approval = snapshot_regular_file_at(
            repo_fd,
            policy.selection_approval_path,
            maximum_bytes=MAX_RECEIPT_BYTES,
        )
        snapshots.append(approval)
        selection_record_id, selection_root_commit = _parse_selection_approval(
            approval.read_bytes()
        )

        receipt_path = policy.receipt_root / run_id / RECEIPT_FILENAME
        signature_path = policy.receipt_root / run_id / SIGNATURE_FILENAME
        receipt = _secure_policy_file(
            receipt_path,
            None,
            context=context,
            label="Gate-first aggregate receipt",
            maximum_bytes=MAX_RECEIPT_BYTES,
            write_mask=0o222,
            single_link=True,
        )
        # Aggregate receipts are bound by the detached signature rather than a
        # digest stored in their own policy.
        snapshots.append(receipt)
        signature = _secure_policy_file(
            signature_path,
            None,
            context=context,
            label="Gate-first aggregate receipt signature",
            maximum_bytes=MAX_SIGNATURE_BYTES,
            write_mask=0o222,
            single_link=True,
        )
        snapshots.append(signature)
        allowed_signers = _secure_policy_file(
            policy.receipt_allowed_signers_path,
            policy.receipt_allowed_signers_sha256,
            context=context,
            label="receipt allowed-signers store",
            maximum_bytes=MAX_ALLOWED_SIGNERS_BYTES,
            write_mask=0o222,
            single_link=True,
        )
        snapshots.append(allowed_signers)
        ssh_keygen = _secure_policy_file(
            policy.ssh_keygen_path,
            policy.ssh_keygen_sha256,
            context=context,
            label="receipt ssh-keygen",
            maximum_bytes=128 * 1024 * 1024,
            write_mask=0o022,
            single_link=False,
        )
        snapshots.append(ssh_keygen)

        receipt_raw = receipt.read_bytes()
        payload = _load_canonical_json(receipt_raw, label="Gate-first aggregate receipt")
        _exact_keys(
            payload,
            {
                "schema",
                "run_id",
                "status",
                "offline",
                "live_actions_authorized",
                "started_at",
                "completed_at",
                "selection",
                "launcher",
                "boundary",
                "goals",
            },
            "Gate-first aggregate receipt",
        )
        expected_top = {
            "schema": RUN_RECEIPT_SCHEMA,
            "run_id": run_id,
            "status": "passed",
            "offline": True,
            "live_actions_authorized": False,
        }
        for key, expected in expected_top.items():
            if not _matches_exact_type(payload[key], expected):
                _fail(f"Gate-first aggregate receipt has invalid {key}")
        started_at = _timestamp(payload["started_at"], "receipt.started_at")
        completed_at = _timestamp(payload["completed_at"], "receipt.completed_at")
        if completed_at < started_at:
            _fail("aggregate receipt completion precedes its start")

        selection = _object(payload["selection"], "receipt.selection")
        _exact_keys(
            selection,
            {"approval_sha256", "record_id", "reviewed_root_commit"},
            "receipt.selection",
        )
        if selection["approval_sha256"] != approval.sha256:
            _fail("receipt selection approval digest differs from current pinned approval")
        if selection["record_id"] != selection_record_id:
            _fail("receipt selection record id differs from current pinned approval")
        if selection["reviewed_root_commit"] != selection_root_commit:
            _fail("receipt reviewed root commit differs from current pinned approval")

        launcher = _object(payload["launcher"], "receipt.launcher")
        _exact_keys(
            launcher,
            {
                "launcher_sha256",
                "policy_sha256",
                "python_sha256",
                "gate_verifier_sha256",
            },
            "receipt.launcher",
        )
        launcher_expected = {
            "launcher_sha256": policy.launcher_sha256,
            "policy_sha256": policy.raw_sha256,
            "python_sha256": policy.python_sha256,
            "gate_verifier_sha256": policy.gate_verifier_sha256,
        }
        for key, expected in launcher_expected.items():
            if launcher[key] != expected:
                _fail(f"receipt launcher binding has invalid {key}")

        boundary = _object(payload["boundary"], "receipt.boundary")
        _exact_keys(
            boundary,
            {
                "apparmor_profile",
                "network_namespace",
                "loopback_only",
                "no_external_route",
                "clean_environment_sha256",
            },
            "receipt.boundary",
        )
        environment_digest = _sha256_bytes(
            canonical_json_bytes(EXPECTED_CLEAN_ENVIRONMENT)
        )
        boundary_expected = {
            "apparmor_profile": policy.apparmor_profile,
            "network_namespace": policy.network_namespace,
            "loopback_only": True,
            "no_external_route": True,
            "clean_environment_sha256": environment_digest,
        }
        for key, expected in boundary_expected.items():
            if not _matches_exact_type(boundary[key], expected):
                _fail(f"receipt boundary has invalid {key}")

        raw_goals = payload["goals"]
        if not isinstance(raw_goals, list) or len(raw_goals) != len(EXPECTED_GOAL_IDS):
            _fail("receipt must contain exactly three ordered goal results")
        observed_goals: list[str] = []
        goal_result_digests: dict[str, str] = {}
        for index, raw_goal in enumerate(raw_goals):
            goal = _object(raw_goal, f"receipt.goals[{index}]")
            _exact_keys(
                goal,
                {
                    "goal_id",
                    "status",
                    "runner_sha256",
                    "result_path",
                    "result_sha256",
                },
                f"receipt.goals[{index}]",
            )
            goal_id = _string(goal["goal_id"], f"receipt.goals[{index}].goal_id")
            if goal_id not in runner_by_goal:
                _fail("receipt contains an unexpected goal")
            observed_goals.append(goal_id)
            if goal["status"] != "passed":
                _fail(f"{goal_id} did not pass")
            runner = runner_by_goal[goal_id]
            if goal["runner_sha256"] != runner.sha256:
                _fail(f"{goal_id} runner digest differs from operator policy")
            result_path = _safe_result_path(goal["result_path"], goal_id)
            result_digest = _digest(
                goal["result_sha256"], f"receipt.goals[{index}].result_sha256"
            )
            result = _secure_policy_file(
                policy.receipt_root / run_id / result_path,
                result_digest,
                context=context,
                label=f"{goal_id} result",
                maximum_bytes=MAX_GOAL_RESULT_BYTES,
                write_mask=0o222,
                single_link=True,
            )
            snapshots.append(result)
            _validate_goal_result(
                result.read_bytes(),
                run_id=run_id,
                goal_id=goal_id,
                runner_sha256=runner.sha256,
                selection_approval_sha256=approval.sha256,
            )
            goal_result_digests[goal_id] = result.sha256
        if tuple(observed_goals) != EXPECTED_GOAL_IDS:
            _fail(f"receipt goal order must be exactly {list(EXPECTED_GOAL_IDS)}")

        _verify_signature(
            policy=policy,
            receipt_raw=receipt_raw,
            signature=signature,
            allowed_signers_raw=allowed_signers.read_bytes(),
        )
        return {
            "schema": VERIFY_RESULT_SCHEMA,
            "status": "verified",
            "run_id": run_id,
            "receipt_sha256": receipt.sha256,
            "selection_approval_sha256": approval.sha256,
            "selection_record_id": selection_record_id,
            "reviewed_root_commit": selection_root_commit,
            "goal_result_sha256": goal_result_digests,
            "offline": True,
            "live_actions_authorized": False,
        }
    except GateFirstLauncherError as exc:
        _fail(str(exc))
    finally:
        for snapshot in snapshots:
            snapshot.close()
        os.close(repo_fd)


def verify_from_fixed_policy(
    *,
    run_id: str,
    policy_path: Path = FIXED_OPERATOR_POLICY_PATH,
    context: ExternalSecurityContext = ROOT_OPERATOR_CONTEXT,
    enforce_authority_runtime: bool = True,
) -> dict[str, Any]:
    """Load the fixed operator policy and verify one direct child run id."""

    if enforce_authority_runtime:
        validate_isolated_interpreter()
        validate_authority_environment(os.environ)
        if os.geteuid() != 0:
            _fail("authoritative receipt verification requires effective uid 0")
    try:
        policy = load_operator_policy(policy_path, context=context)
    except GateFirstLauncherError as exc:
        _fail(str(exc))
    return verify_gate_first_receipt(policy=policy, run_id=run_id, context=context)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run-id",
        required=True,
        help="One immutable direct-child run id below the policy-fixed receipt root.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        summary = verify_from_fixed_policy(
            run_id=args.run_id,
            policy_path=FIXED_OPERATOR_POLICY_PATH,
            context=ROOT_OPERATOR_CONTEXT,
            enforce_authority_runtime=True,
        )
    except (GateFirstLauncherError, GateFirstReceiptError, OSError, subprocess.SubprocessError) as exc:
        print(f"World-aid Gate-first receipt REJECTED: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(summary, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
