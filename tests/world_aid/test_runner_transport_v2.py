"""Adversarial tests for the non-executing v2 runner transport foundation."""

from __future__ import annotations

import copy
import fcntl
import hashlib
import json
import os
import tempfile
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

import scripts.run_world_aid_duckdb_bootstrap as g040
import scripts.run_world_aid_siwe_bootstrap as g038
import scripts.run_world_aid_zkp_bootstrap as g039
import scripts.verify_world_aid_gate_first_receipt as receipt_verifier
import scripts.world_aid_runner_transport_v2 as transport
from scripts.world_aid_runner_transport_v2 import (
    CanonicalResultWriter,
    ExpectedRunnerBindings,
    RunnerTransportV2Error,
    build_success_result,
    canonical_json_bytes,
    decode_canonical_result,
    decode_sealed_request,
)

APPROVAL = "sha256:" + "a" * 64
BOUNDARY = "sha256:" + "b" * 64
OTHER_DIGEST = "sha256:" + "c" * 64
SCHEMA_ROOT = Path(__file__).resolve().parents[2] / "docs/schemas/world_aid"


def _g038_plan() -> g038.SIWEExecutionPlan:
    cache_entries = (
        g038.SIWECacheEntry(
            path="content",
            kind="directory",
            size=0,
            sha256=None,
        ),
        g038.SIWECacheEntry(
            path="content/package.tgz",
            kind="file",
            size=7,
            sha256=OTHER_DIGEST,
        ),
    )

    def bound(role: str, destination: str) -> g038.SIWEBoundInput:
        return g038.SIWEBoundInput(
            source_path=Path(f"/opt/world-aid/g038/{role}"),
            sha256=OTHER_DIGEST,
            max_bytes=4096,
            workspace_relative_path=destination,
        )

    return g038.SIWEExecutionPlan(
        schema_version=g038.PLAN_SCHEMA,
        goal_id=g038.GOAL_ID,
        authorization_sha256=APPROVAL,
        selection_record_id="gate-0b-selection-transport-test",
        network_policy="external-deny-all",
        network_boundary=g038.SIWENetworkBoundary(
            attestation_sha256=BOUNDARY,
            namespace="net:[4026533000]",
            apparmor_profile="world-aid-gate (enforce)",
            network_deny_canary_sha256=OTHER_DIGEST,
            egress_policy_sha256="sha256:" + "d" * 64,
        ),
        platform="linux",
        architecture="x86_64",
        toolchain_archive_sha256="sha256:" + "e" * 64,
        node=g038.SIWEToolBinding(
            source_path=Path("/opt/world-aid/g038/node"),
            sha256="sha256:" + "f" * 64,
            max_bytes=4096,
            version="22.23.1",
        ),
        npm_cli=g038.SIWEToolBinding(
            source_path=Path("/opt/world-aid/g038/npm-cli.js"),
            sha256="sha256:" + "1" * 64,
            max_bytes=4096,
            version="10.9.8",
        ),
        manifest=bound("manifest", "package.json"),
        lockfile=bound("lockfile", "package-lock.json"),
        adapter=bound("adapter", "index.mjs"),
        smoke_source=bound("smoke", "g038-smoke.mjs"),
        cache=g038.SIWECacheArchive(
            source_path=Path("/opt/world-aid/g038/cache.tar"),
            sha256="sha256:" + "2" * 64,
            max_archive_bytes=8192,
            archive_format="tar",
            max_entries=16,
            max_extracted_bytes=8192,
            tree_sha256=g038.cache_tree_sha256(cache_entries),
            entries=cache_entries,
        ),
        resource_bounds=g038.SIWEResourceBounds(
            max_seconds=30,
            max_memory_mb=256,
            max_output_bytes=65536,
            max_file_bytes=65536,
            max_workspace_entries=256,
            max_workspace_bytes=1024 * 1024,
        ),
        expires_at="2099-01-01T00:00:00Z",
    )


def test_review_schemas_match_codec_constants_and_close_nested_objects() -> None:
    input_schema = json.loads((SCHEMA_ROOT / "runner-transport-v2-input.schema.json").read_text(encoding="utf-8"))
    result_schema = json.loads((SCHEMA_ROOT / "runner-transport-v2-result.schema.json").read_text(encoding="utf-8"))
    assert input_schema["properties"]["schema_version"]["const"] == (transport.INPUT_SCHEMA)
    assert input_schema["properties"]["protocol"]["const"] == (transport.SEALED_INPUT_PROTOCOL)
    assert result_schema["properties"]["schema_version"]["const"] == (transport.RESULT_SCHEMA)
    assert result_schema["properties"]["protocol"]["const"] == (transport.RESULT_PROTOCOL)
    assert result_schema["properties"]["aggregate_receipt_object_sha256"] == {"$ref": "#/$defs/digest"}
    assert "aggregate_receipt_object_sha256" in result_schema["required"]
    assert result_schema["properties"]["goal_id"]["enum"] == list(transport.RESULT_GOAL_IDS)
    assert "WORLDCOIN-G038" not in json.dumps(
        result_schema,
        sort_keys=True,
    )
    goal_plan_couplings = {
        clause["if"]["properties"]["goal_id"]["const"]: clause["then"]["properties"]["plan"]["$ref"]
        for clause in input_schema["allOf"]
    }
    assert goal_plan_couplings == {
        "WORLDCOIN-G038": "#/$defs/g038_plan",
        "WORLDCOIN-G039": "#/$defs/g039_plan",
        "WORLDCOIN-G040": "#/$defs/g040_plan",
    }
    goal_receipt_couplings = {
        clause["if"]["properties"]["goal_id"]["const"]: clause["then"]["properties"]["native_receipt"]["$ref"]
        for clause in result_schema["allOf"]
    }
    assert goal_receipt_couplings == {
        "WORLDCOIN-G039": "#/$defs/g039_receipt",
        "WORLDCOIN-G040": "#/$defs/g040_receipt",
    }
    assert input_schema["additionalProperties"] is False
    assert result_schema["additionalProperties"] is False
    for schema in (input_schema, result_schema):
        definitions = schema["$defs"]
        pending: list[object] = [schema]
        while pending:
            item = pending.pop()
            if isinstance(item, dict):
                reference = item.get("$ref")
                if isinstance(reference, str) and reference.startswith("#/$defs/"):
                    assert reference.removeprefix("#/$defs/") in definitions
                pending.extend(item.values())
            elif isinstance(item, list):
                pending.extend(item)
    for name in (
        "g039_commands",
        "g039_input",
        "g039_resources",
        "g039_tool",
        "g040_checks",
        "g040_cleanup",
        "g040_deny_settings",
        "g040_python",
        "g040_resources",
        "g040_reviewed_inputs",
        "g040_second_writer",
        "g040_wheel",
    ):
        assert result_schema["$defs"][name]["additionalProperties"] is False


def _g039_plan() -> g039.NativeSmokeExecutionPlan:
    build = (
        "{tool}",
        "build",
        "--input-root",
        "{input_root}",
        "--output",
        "{artifact}",
    )
    prove = (
        "{tool}",
        "prove",
        "--input-root",
        "{input_root}",
        "--artifact",
        "{artifact}",
        "--proof",
        "{proof}",
    )
    verify = (
        "{tool}",
        "verify",
        "--input-root",
        "{input_root}",
        "--artifact",
        "{artifact}",
        "--proof",
        "{proof}",
    )
    return g039.NativeSmokeExecutionPlan(
        schema_version=g039.PLAN_SCHEMA,
        goal_id="WORLDCOIN-G039",
        authorization_sha256=APPROVAL,
        network_boundary_sha256=BOUNDARY,
        network_policy="external-deny-all",
        tool_path=Path("/opt/world-aid/g039/nargo"),
        tool_sha256=OTHER_DIGEST,
        tool_max_bytes=4096,
        build_a_argv=build,
        build_b_argv=build,
        prove_argv=prove,
        verify_argv=verify,
        fixed_env=(("EXPECTED_VALUE", "fixed"),),
        inputs=(
            g039.NativeSmokeInput(
                source_path=Path("/opt/world-aid/g039/Nargo.toml"),
                sha256="sha256:" + "d" * 64,
                max_bytes=4096,
                workspace_relative_path="Nargo.toml",
            ),
        ),
        resource_bounds=g039.NativeSmokeResourceBounds(
            max_seconds=30,
            max_memory_mb=256,
            max_output_bytes=65536,
        ),
        artifact_relative_path="target/artifact.bin",
        proof_relative_path="target/proof.bin",
        expires_at="2099-01-01T00:00:00Z",
    )


def _g040_plan() -> g040.DuckDBBootstrapPlan:
    def artifact(role: str) -> g040.DuckDBBoundArtifact:
        return g040.DuckDBBoundArtifact(
            source_path=Path(f"/opt/world-aid/g040/{role}.json"),
            sha256=(APPROVAL if role == "authorization" else BOUNDARY if role == "network-boundary" else OTHER_DIGEST),
            size=4096,
        )

    platform_tag = "manylinux_2_28_x86_64"
    filename = f"duckdb-1.4.3-cp312-cp312-{platform_tag}.whl"
    return g040.DuckDBBootstrapPlan(
        schema_version=g040.PLAN_SCHEMA,
        goal_id=g040.GOAL_ID,
        authorization=artifact("authorization"),
        network_boundary_attestation=artifact("network-boundary"),
        network_policy="external-deny-all",
        python_path=Path("/opt/world-aid/g040/python"),
        python_sha256="sha256:" + "d" * 64,
        python_size=4096,
        python_version="3.12.1",
        wheel_path=Path(f"/opt/world-aid/g040/{filename}"),
        wheel_sha256="sha256:" + "e" * 64,
        wheel_size=8192,
        wheel_filename=filename,
        duckdb_version="1.4.3",
        python_tag="cp312",
        abi_tag="cp312",
        platform_tag=platform_tag,
        requirements_lock=artifact("requirements-lock"),
        runtime_policy=artifact("runtime-policy"),
        backup_policy=artifact("backup-policy"),
        storage_adr=artifact("storage-adr"),
        smoke_bootstrap_sha256=g040.fixed_smoke_bootstrap_sha256(),
        resource_bounds=g040.DuckDBResourceBounds(
            max_seconds=30,
            max_memory_mb=256,
            max_output_bytes=65536,
            max_file_bytes=1024 * 1024,
            max_workspace_bytes=4 * 1024 * 1024,
            max_wheel_entries=128,
            max_entry_bytes=1024 * 1024,
            max_uncompressed_bytes=2 * 1024 * 1024,
        ),
        run_directory=Path("/var/lib/world-aid/g040-runs"),
        expires_at="2099-01-01T00:00:00Z",
    )


def _payload_for_plan(
    plan: transport.RunnerPlan,
) -> tuple[dict[str, Any], ExpectedRunnerBindings]:
    if isinstance(plan, g038.SIWEExecutionPlan):
        plan_payload = g038._plan_payload(plan)
        plan_digest = g038.execution_plan_sha256(plan)
        approval = plan.authorization_sha256
        boundary = plan.network_boundary.attestation_sha256
    elif isinstance(plan, g039.NativeSmokeExecutionPlan):
        plan_payload = g039._plan_payload(plan)
        plan_digest = g039.execution_plan_sha256(plan)
        approval = plan.authorization_sha256
        boundary = plan.network_boundary_sha256
    elif isinstance(plan, g040.DuckDBBootstrapPlan):
        plan_payload = g040._plan_payload(plan)
        plan_digest = g040.execution_plan_sha256(plan)
        approval = plan.authorization.sha256
        boundary = plan.network_boundary_attestation.sha256
    else:
        raise AssertionError(type(plan))
    bindings = ExpectedRunnerBindings(
        goal_id=plan.goal_id,
        approval_sha256=approval,
        network_boundary_sha256=boundary,
        execution_plan_sha256=plan_digest,
    )
    return (
        {
            "schema_version": transport.INPUT_SCHEMA,
            "protocol": transport.SEALED_INPUT_PROTOCOL,
            "goal_id": plan.goal_id,
            "approval_sha256": approval,
            "network_boundary_sha256": boundary,
            "execution_plan_sha256": plan_digest,
            "plan": plan_payload,
        },
        bindings,
    )


def _payload_and_bindings(
    goal_id: str,
) -> tuple[dict[str, Any], ExpectedRunnerBindings]:
    plans = {
        g038.GOAL_ID: _g038_plan,
        g039.GOAL_ID: _g039_plan,
        g040.GOAL_ID: _g040_plan,
    }
    try:
        plan = plans[goal_id]()
    except KeyError as exc:
        raise AssertionError(goal_id) from exc
    return _payload_for_plan(plan)


def _sealed_memfd(raw: bytes, *, seals: int | None = None) -> int:
    descriptor = os.memfd_create(
        "world-aid-runner-input-v2",
        os.MFD_ALLOW_SEALING,
    )
    os.write(descriptor, raw)
    if seals is None:
        seals = fcntl.F_SEAL_SEAL | fcntl.F_SEAL_SHRINK | fcntl.F_SEAL_GROW | fcntl.F_SEAL_WRITE
    if seals:
        fcntl.fcntl(descriptor, fcntl.F_ADD_SEALS, seals)
    return descriptor


def _decoded_request(goal_id: str) -> transport.DecodedRunnerRequest:
    payload, bindings = _payload_and_bindings(goal_id)
    descriptor = _sealed_memfd(canonical_json_bytes(payload))
    try:
        return decode_sealed_request(descriptor, bindings)
    finally:
        os.close(descriptor)


def _decoded_plan_request(
    plan: transport.RunnerPlan,
) -> transport.DecodedRunnerRequest:
    payload, bindings = _payload_for_plan(plan)
    descriptor = _sealed_memfd(canonical_json_bytes(payload))
    try:
        return decode_sealed_request(descriptor, bindings)
    finally:
        os.close(descriptor)


@pytest.mark.parametrize("goal_id", transport.EXPECTED_GOAL_IDS)
def test_sealed_request_decodes_exact_native_plan(goal_id: str) -> None:
    payload, bindings = _payload_and_bindings(goal_id)
    descriptor = _sealed_memfd(canonical_json_bytes(payload))
    try:
        request = decode_sealed_request(descriptor, bindings)
    finally:
        os.close(descriptor)

    assert request.bindings == bindings
    assert request.plan.goal_id == goal_id
    assert request.memfd_size > 0
    assert request.memfd_seals & fcntl.F_SEAL_WRITE
    assert request.envelope_sha256.startswith("sha256:")


def test_input_descriptor_is_pinned_before_original_number_is_replaced(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload, bindings = _payload_and_bindings(g039.GOAL_ID)
    descriptor = _sealed_memfd(canonical_json_bytes(payload))
    real_read = transport._read_sealed_memfd
    observed_pinned = -1
    replacement_descriptor = -1

    def replace_original(pinned_descriptor: int):
        nonlocal observed_pinned, replacement_descriptor
        observed_pinned = pinned_descriptor
        assert pinned_descriptor != descriptor
        os.close(descriptor)
        replacement_descriptor = os.open("/dev/null", os.O_RDONLY)
        return real_read(pinned_descriptor)

    monkeypatch.setattr(transport, "_read_sealed_memfd", replace_original)
    try:
        request = decode_sealed_request(descriptor, bindings)
        assert request.bindings == bindings
        assert replacement_descriptor == descriptor
        with pytest.raises(OSError):
            os.fstat(observed_pinned)
    finally:
        if replacement_descriptor >= 0:
            os.close(replacement_descriptor)


@pytest.mark.parametrize(
    "namespace",
    [
        "net:[abc]",
        "net:[4026533000",
        "net:[]",
        "net:[4026533000]suffix",
    ],
)
def test_g038_request_requires_fully_formed_numeric_namespace(
    namespace: str,
) -> None:
    payload, bindings = _payload_and_bindings(g038.GOAL_ID)
    payload["plan"]["network_boundary"]["namespace"] = namespace
    descriptor = _sealed_memfd(canonical_json_bytes(payload))
    try:
        with pytest.raises(RunnerTransportV2Error, match=r"net:\[digits\]"):
            decode_sealed_request(descriptor, bindings)
    finally:
        os.close(descriptor)


def test_g040_request_rejects_four_component_python_version() -> None:
    plan = replace(_g040_plan(), python_version="3.12.1.4")
    with pytest.raises(
        RunnerTransportV2Error,
        match="exactly three numeric components",
    ):
        _decoded_plan_request(plan)


def test_request_absolute_paths_reject_filesystem_root() -> None:
    payload, bindings = _payload_and_bindings(g039.GOAL_ID)
    payload["plan"]["tool_path"] = "/"
    descriptor = _sealed_memfd(canonical_json_bytes(payload))
    try:
        with pytest.raises(
            RunnerTransportV2Error,
            match="normalized absolute POSIX path",
        ):
            decode_sealed_request(descriptor, bindings)
    finally:
        os.close(descriptor)


def test_parser_rejects_huge_integer_depth_and_node_bombs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(RunnerTransportV2Error, match="lexical bound"):
        transport._decode_canonical_json(
            b'{"value":' + b"9" * 10_000 + b"}\n",
            label="huge integer",
            maximum_bytes=transport.MAX_INPUT_BYTES,
        )

    nested = b"[" * (transport.MAX_JSON_DEPTH + 1) + b"0" + b"]" * (transport.MAX_JSON_DEPTH + 1) + b"\n"
    with pytest.raises(RunnerTransportV2Error, match="depth bound"):
        transport._decode_canonical_json(
            nested,
            label="deep JSON",
            maximum_bytes=transport.MAX_INPUT_BYTES,
        )

    node_bomb = b"[" + b",".join(b"0" for _index in range(transport.MAX_JSON_NODES)) + b"]\n"
    with pytest.raises(RunnerTransportV2Error, match="node bound"):
        transport._decode_canonical_json(
            node_bomb,
            label="node bomb",
            maximum_bytes=transport.MAX_INPUT_BYTES,
        )

    def raise_value_error(*_args: object, **_kwargs: object) -> object:
        raise ValueError("synthetic decoder failure")

    monkeypatch.setattr(transport.json, "loads", raise_value_error)
    with pytest.raises(RunnerTransportV2Error, match="not strict JSON"):
        transport._decode_canonical_json(
            b"{}\n",
            label="synthetic failure",
            maximum_bytes=transport.MAX_INPUT_BYTES,
        )

    assert transport.MAX_INPUT_BYTES == 8 * 1024 * 1024
    assert transport.MAX_RESULT_BYTES == 8 * 1024 * 1024


@pytest.mark.parametrize(
    ("seals", "message"),
    [
        (0, "must carry"),
        (
            fcntl.F_SEAL_SHRINK | fcntl.F_SEAL_GROW | fcntl.F_SEAL_WRITE,
            "must carry",
        ),
        (
            fcntl.F_SEAL_SEAL | fcntl.F_SEAL_SHRINK | fcntl.F_SEAL_GROW,
            "must carry",
        ),
    ],
)
def test_request_rejects_incomplete_memfd_seals(
    seals: int,
    message: str,
) -> None:
    payload, bindings = _payload_and_bindings(g039.GOAL_ID)
    descriptor = _sealed_memfd(canonical_json_bytes(payload), seals=seals)
    try:
        with pytest.raises(RunnerTransportV2Error, match=message):
            decode_sealed_request(descriptor, bindings)
    finally:
        os.close(descriptor)


def test_request_rejects_unlinked_regular_file_that_is_not_memfd() -> None:
    payload, bindings = _payload_and_bindings(g039.GOAL_ID)
    with tempfile.NamedTemporaryFile() as source:
        source.write(canonical_json_bytes(payload))
        source.flush()
        os.unlink(source.name)
        with pytest.raises(RunnerTransportV2Error, match="not an anonymous Linux memfd"):
            decode_sealed_request(source.fileno(), bindings)


@pytest.mark.parametrize(
    "mutation",
    [
        "binding",
        "envelope_unknown",
        "plan_unknown",
        "plan_approval",
        "noncanonical",
        "duplicate",
    ],
)
def test_request_rejects_binding_schema_and_canonical_drift(
    mutation: str,
) -> None:
    payload, bindings = _payload_and_bindings(g039.GOAL_ID)
    if mutation == "binding":
        bindings = ExpectedRunnerBindings(
            goal_id=bindings.goal_id,
            approval_sha256="sha256:" + "9" * 64,
            network_boundary_sha256=bindings.network_boundary_sha256,
            execution_plan_sha256=bindings.execution_plan_sha256,
        )
    elif mutation == "envelope_unknown":
        payload["caller_default"] = True
    elif mutation == "plan_unknown":
        payload["plan"]["allow_network"] = True
    elif mutation == "plan_approval":
        payload["plan"]["authorization_sha256"] = "sha256:" + "9" * 64

    raw = canonical_json_bytes(payload)
    if mutation == "noncanonical":
        raw = json.dumps(payload, indent=2, sort_keys=True).encode() + b"\n"
    elif mutation == "duplicate":
        raw = raw.replace(
            b'"goal_id":"WORLDCOIN-G039"',
            (b'"goal_id":"WORLDCOIN-G039","goal_id":"WORLDCOIN-G039"'),
            1,
        )
    descriptor = _sealed_memfd(raw)
    try:
        with pytest.raises(RunnerTransportV2Error):
            decode_sealed_request(descriptor, bindings)
    finally:
        os.close(descriptor)


def _command_evidence() -> dict[str, Any]:
    return {
        "exit_code": 0,
        "elapsed_ms": 1,
        "stdout_sha256": OTHER_DIGEST,
        "stdout_bytes": 0,
        "stderr_sha256": OTHER_DIGEST,
        "stderr_bytes": 0,
    }


def _native_receipt(
    request: transport.DecodedRunnerRequest,
) -> dict[str, Any]:
    bindings = request.bindings
    plan = request.plan
    if isinstance(plan, g038.SIWEExecutionPlan):
        boundary = {
            "namespace": plan.network_boundary.namespace,
            "apparmor_profile": plan.network_boundary.apparmor_profile,
            "interfaces": ["lo"],
            "no_external_route": True,
            "network_deny_canary_sha256": (plan.network_boundary.network_deny_canary_sha256),
            "egress_policy_sha256": (plan.network_boundary.egress_policy_sha256),
        }
        return {
            "schema_version": g038.RECEIPT_SCHEMA,
            "goal_id": bindings.goal_id,
            "status": "passed",
            "completed_at": "2098-01-01T00:00:00Z",
            "valid_until": "2099-01-01T00:00:00Z",
            "offline": True,
            "live_actions_authorized": False,
            "selection_record_id": plan.selection_record_id,
            "selection_approval_sha256": bindings.approval_sha256,
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
                "local_before_sha256": OTHER_DIGEST,
                "local_after_sha256": OTHER_DIGEST,
            },
            "network": {
                "enforcement": "signed-namespace-plus-apparmor",
                "attempt_monitor": "not-configured",
                "attempt_count": None,
                "external_network_succeeded": False,
                "boundary_before": boundary,
                "boundary_after": copy.deepcopy(boundary),
            },
            "smoke_result": {
                "eoa": True,
                "eip1271": True,
                "contractReads": 1,
            },
        }
    if isinstance(plan, g039.NativeSmokeExecutionPlan):
        return {
            "schema_version": g039.RECEIPT_SCHEMA,
            "goal_id": bindings.goal_id,
            "execution_plan_sha256": bindings.execution_plan_sha256,
            "authorization_sha256": bindings.approval_sha256,
            "tool": {
                "path": os.fspath(plan.tool_path),
                "sha256": plan.tool_sha256,
                "max_bytes": plan.tool_max_bytes,
            },
            "inputs": [
                {
                    "source_path": os.fspath(item.source_path),
                    "sha256": item.sha256,
                    "max_bytes": item.max_bytes,
                    "workspace_relative_path": item.workspace_relative_path,
                }
                for item in plan.inputs
            ],
            "repeat_build_hashes": [OTHER_DIGEST, OTHER_DIGEST],
            "proof_sha256": OTHER_DIGEST,
            "proof_result": True,
            "verify_result": True,
            "network_registry_denied": True,
            "network_boundary": {
                "policy": "external-deny-all",
                "attestation_sha256": bindings.network_boundary_sha256,
                "authority": "external-gate-first-launcher",
            },
            "resource_bounds": {
                "max_seconds": plan.resource_bounds.max_seconds,
                "max_memory_mb": plan.resource_bounds.max_memory_mb,
                "max_output_bytes": plan.resource_bounds.max_output_bytes,
                "max_open_files": 64,
                "observed_process_output_bytes": 0,
            },
            "expiry": plan.expires_at,
            "commands": {name: _command_evidence() for name in ("build_a", "build_b", "prove", "verify")},
            "production_trust": False,
            "completed_at": "2098-01-01T00:00:00Z",
        }
    if isinstance(plan, g040.DuckDBBootstrapPlan):
        plan_resources = g040._plan_payload(plan)["resource_bounds"]
        reviewed_inputs = {
            role: {
                "source_path": os.fspath(artifact.source_path),
                "sha256": artifact.sha256,
                "size": artifact.size,
            }
            for role, artifact in (
                ("requirements_lock", plan.requirements_lock),
                ("runtime_policy", plan.runtime_policy),
                ("backup_policy", plan.backup_policy),
                ("storage_adr", plan.storage_adr),
            )
        }
        return {
            "schema_version": g040.RECEIPT_SCHEMA,
            "goal_id": bindings.goal_id,
            "status": "passed",
            "execution_plan_sha256": bindings.execution_plan_sha256,
            "authorization_sha256": bindings.approval_sha256,
            "network_boundary": {
                "policy": "external-deny-all",
                "attestation_sha256": bindings.network_boundary_sha256,
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
                "validation": {
                    "entry_count": 4,
                    "file_count": 4,
                    "uncompressed_bytes": 4096,
                    "record_count": 4,
                    "metadata_name": "duckdb",
                    "metadata_version": plan.duckdb_version,
                    "wheel_tag": (f"{plan.python_tag}-{plan.abi_tag}-{plan.platform_tag}"),
                },
            },
            "reviewed_inputs": reviewed_inputs,
            "smoke_bootstrap_sha256": plan.smoke_bootstrap_sha256,
            "checks": {name: True for name in g040.REQUIRED_G040_CHECKS},
            "cleanup": {
                "database_exists": False,
                "temporary_data_exists": False,
                "wal_exists": False,
                "isolated_site_removed_before_publication": True,
                "workspace_removed_before_publication": True,
            },
            "deny_settings": {
                "allow_community_extensions": "false",
                "autoinstall_known_extensions": "false",
                "autoload_known_extensions": "false",
                "enable_external_access": "false",
                "lock_configuration": "true",
            },
            "loaded_dynamic_extensions": [],
            "network_attempts": 0,
            "single_writer_enforced": True,
            "second_writer_evidence": {
                "schema_version": ("world-human-aid-g040-second-writer/v1"),
                "import_succeeded": True,
                "connect_attempted": True,
                "connect_succeeded": False,
                "write_attempted": False,
                "rejected": True,
                "rejection_stage": "connect",
                "exception_module": "_duckdb",
                "exception_type": "IOException",
                "lock_marker": "could not set lock",
                "message_sha256": "f" * 64,
                "message_bytes": 16,
                "message_truncated": False,
            },
            "g033_excluded_controls": list(g040.G033_EXCLUDED_CONTROLS),
            "resource_bounds": {
                **plan_resources,
                "max_open_files": 128,
                "observed_process_output_bytes": 0,
                "observed_workspace_bytes_before_cleanup": 0,
            },
            "command": _command_evidence(),
            "offline": True,
            "live_actions_authorized": False,
            "production_trust": False,
            "expires_at": plan.expires_at,
            "completed_at": "2098-01-01T00:00:00Z",
        }
    raise AssertionError(type(plan))


@pytest.mark.parametrize("goal_id", transport.RESULT_GOAL_IDS)
def test_one_shot_writer_emits_one_bound_canonical_result(goal_id: str) -> None:
    request = _decoded_request(goal_id)
    read_descriptor, write_descriptor = os.pipe()
    replacement_descriptor = -1
    try:
        consumed_descriptor = write_descriptor
        writer = CanonicalResultWriter(write_descriptor, request)
        write_descriptor = -1
        with pytest.raises(OSError):
            os.fstat(consumed_descriptor)
        replacement_descriptor = os.open("/dev/null", os.O_WRONLY)
        assert replacement_descriptor == consumed_descriptor
        expected_result = build_success_result(
            _native_receipt(request),
            request,
        )
        assert writer.emit(_native_receipt(request)) == len(canonical_json_bytes(expected_result))
        with pytest.raises(RunnerTransportV2Error, match="already been consumed"):
            writer.emit(_native_receipt(request))
        raw = os.read(read_descriptor, transport.MAX_RESULT_BYTES + 1)
    finally:
        os.close(read_descriptor)
        if write_descriptor >= 0:
            os.close(write_descriptor)
        if replacement_descriptor >= 0:
            os.close(replacement_descriptor)

    assert raw == canonical_json_bytes(expected_result)
    assert decode_canonical_result(raw, request) == _native_receipt(request)


def test_writer_rejects_regular_read_only_and_prepopulated_descriptors() -> None:
    request = _decoded_request(g039.GOAL_ID)
    with tempfile.TemporaryFile() as regular:
        with pytest.raises(RunnerTransportV2Error, match="FIFO or anonymous pipe"):
            CanonicalResultWriter(regular.fileno(), request)

    read_descriptor, write_descriptor = os.pipe()
    try:
        with pytest.raises(RunnerTransportV2Error, match="write-only"):
            CanonicalResultWriter(read_descriptor, request)
        os.write(write_descriptor, b"preexisting")
        with pytest.raises(RunnerTransportV2Error, match="fresh"):
            CanonicalResultWriter(write_descriptor, request)
        assert os.read(read_descriptor, len(b"preexisting")) == b"preexisting"
    finally:
        os.close(read_descriptor)
        os.close(write_descriptor)


def test_g038_success_results_fail_closed_against_receipt_replay() -> None:
    request_a = _decoded_request(g038.GOAL_ID)
    plan_a = _g038_plan()
    plan_b = replace(
        plan_a,
        network_boundary=replace(
            plan_a.network_boundary,
            attestation_sha256="sha256:" + "9" * 64,
        ),
    )
    request_b = _decoded_plan_request(plan_b)
    receipt = _native_receipt(request_a)

    assert receipt == _native_receipt(request_b)
    assert request_a.bindings.execution_plan_sha256 != (request_b.bindings.execution_plan_sha256)
    assert request_a.bindings.network_boundary_sha256 != (request_b.bindings.network_boundary_sha256)
    for request in (request_a, request_b):
        with pytest.raises(
            RunnerTransportV2Error,
            match="G038 stdout results are disabled",
        ):
            build_success_result(receipt, request)
        crafted = {
            "schema_version": transport.RESULT_SCHEMA,
            "protocol": transport.RESULT_PROTOCOL,
            "goal_id": g038.GOAL_ID,
            "status": "passed",
            "approval_sha256": request.bindings.approval_sha256,
            "network_boundary_sha256": (request.bindings.network_boundary_sha256),
            "execution_plan_sha256": request.bindings.execution_plan_sha256,
            "native_receipt_sha256": OTHER_DIGEST,
            "aggregate_receipt_object_sha256": OTHER_DIGEST,
            "native_receipt": receipt,
        }
        with pytest.raises(
            RunnerTransportV2Error,
            match="G038 stdout results are disabled",
        ):
            decode_canonical_result(canonical_json_bytes(crafted), request)
        read_descriptor, write_descriptor = os.pipe()
        try:
            with pytest.raises(
                RunnerTransportV2Error,
                match="G038 stdout results are disabled",
            ):
                CanonicalResultWriter(write_descriptor, request)
            os.fstat(write_descriptor)
        finally:
            os.close(read_descriptor)
            os.close(write_descriptor)


def test_native_receipt_digest_matches_each_runner_canonical_encoding() -> None:
    g039_plan = _g039_plan()
    unicode_input = replace(
        g039_plan.inputs[0],
        source_path=Path("/opt/world-aid/g039/café.toml"),
    )
    g039_request = _decoded_plan_request(replace(g039_plan, inputs=(unicode_input,)))
    g039_receipt = _native_receipt(g039_request)
    g039_result = build_success_result(g039_receipt, g039_request)
    g039_native_raw = g039._canonical_json_bytes(g039_receipt)
    g039_aggregate_raw = receipt_verifier.canonical_json_bytes(g039_receipt)
    assert g039_native_raw != canonical_json_bytes(g039_receipt)
    assert g039_aggregate_raw == canonical_json_bytes(g039_receipt)
    assert g039_result["native_receipt_sha256"] == ("sha256:" + hashlib.sha256(g039_native_raw).hexdigest())
    assert g039_result["aggregate_receipt_object_sha256"] == (
        "sha256:" + hashlib.sha256(g039_aggregate_raw).hexdigest()
    )
    assert g039_result["aggregate_receipt_object_sha256"] != g039_result["native_receipt_sha256"]
    assert (
        decode_canonical_result(
            canonical_json_bytes(g039_result),
            g039_request,
        )
        == g039_receipt
    )

    g040_request = _decoded_request(g040.GOAL_ID)
    g040_receipt = _native_receipt(g040_request)
    g040_result = build_success_result(g040_receipt, g040_request)
    g040_aggregate_raw = receipt_verifier.canonical_json_bytes(g040_receipt)
    assert g040_result["native_receipt_sha256"] == (
        "sha256:" + hashlib.sha256(g040._canonical_json_bytes(g040_receipt)).hexdigest()
    )
    assert g040_result["aggregate_receipt_object_sha256"] == (
        "sha256:" + hashlib.sha256(g040_aggregate_raw).hexdigest()
    )


def test_result_rejects_extra_output_unknown_keys_and_binding_drift() -> None:
    request = _decoded_request(g039.GOAL_ID)
    result = build_success_result(_native_receipt(request), request)

    with pytest.raises(RunnerTransportV2Error, match="not strict JSON"):
        decode_canonical_result(canonical_json_bytes(result) + b"noise", request)

    unknown = copy.deepcopy(result)
    unknown["diagnostic"] = "caller-authored"
    with pytest.raises(RunnerTransportV2Error, match="keys differ"):
        decode_canonical_result(canonical_json_bytes(unknown), request)

    aggregate_drift = copy.deepcopy(result)
    aggregate_drift["aggregate_receipt_object_sha256"] = "sha256:" + "9" * 64
    with pytest.raises(
        RunnerTransportV2Error,
        match="aggregate receipt object digest differs",
    ):
        decode_canonical_result(canonical_json_bytes(aggregate_drift), request)

    drifted = copy.deepcopy(result)
    drifted["native_receipt"]["network_boundary"]["attestation_sha256"] = "sha256:" + "9" * 64
    drifted["native_receipt_sha256"] = (
        "sha256:" + hashlib.sha256(g039._canonical_json_bytes(drifted["native_receipt"])).hexdigest()
    )
    with pytest.raises(RunnerTransportV2Error, match="network boundary binding"):
        decode_canonical_result(canonical_json_bytes(drifted), request)


@pytest.mark.parametrize(
    ("goal_id", "path", "replacement"),
    [
        (
            g039.GOAL_ID,
            ("resource_bounds", "max_seconds"),
            31,
        ),
        (
            g039.GOAL_ID,
            ("commands", "build_a", "unexpected"),
            0,
        ),
        (
            g040.GOAL_ID,
            ("checks", g040.REQUIRED_G040_CHECKS[0]),
            False,
        ),
        (
            g040.GOAL_ID,
            ("cleanup", "database_exists"),
            True,
        ),
        (
            g040.GOAL_ID,
            ("wheel", "sha256"),
            "sha256:" + "9" * 64,
        ),
        (
            g040.GOAL_ID,
            ("resource_bounds", "max_workspace_bytes"),
            4 * 1024 * 1024 + 1,
        ),
    ],
)
def test_result_rejects_nested_native_evidence_drift(
    goal_id: str,
    path: tuple[str, ...],
    replacement: object,
) -> None:
    request = _decoded_request(goal_id)
    receipt = _native_receipt(request)
    target: dict[str, Any] = receipt
    for component in path[:-1]:
        target = target[component]
    target[path[-1]] = replacement

    with pytest.raises(RunnerTransportV2Error):
        build_success_result(receipt, request)


def test_failed_result_construction_consumes_writer_without_fallback() -> None:
    request = _decoded_request(g039.GOAL_ID)
    read_descriptor, write_descriptor = os.pipe()
    try:
        writer = CanonicalResultWriter(write_descriptor, request)
        write_descriptor = -1
        invalid = _native_receipt(request)
        invalid["proof_result"] = False
        with pytest.raises(RunnerTransportV2Error, match="strict Gate-first"):
            writer.emit(invalid)
        with pytest.raises(RunnerTransportV2Error, match="already been consumed"):
            writer.emit(_native_receipt(request))
        assert os.read(read_descriptor, 1) == b""
    finally:
        os.close(read_descriptor)
        if write_descriptor >= 0:
            os.close(write_descriptor)
