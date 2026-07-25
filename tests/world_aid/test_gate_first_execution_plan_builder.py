"""Adversarial tests for unauthorizing Gate-first candidate plans v2."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import pytest

import scripts.build_world_aid_gate_first_execution_plans as builder
import scripts.world_aid_runner_transport_v2 as transport

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / builder.SCHEMA_PATH
TEMPLATE = ROOT / "docs/governance/templates/gate-first-execution-plan-set.template.json"


def _digest(seed: int) -> str:
    return "sha256:" + hashlib.sha256(f"seed-{seed}".encode()).hexdigest()


def _sha256(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _canonical(value: object, *, ensure_ascii: bool = True) -> bytes:
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=ensure_ascii,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode()


def _policy(
    runner_digests: dict[str, str],
    *,
    run_enabled: bool = False,
) -> dict[str, Any]:
    return {
        "schema": builder.POLICY_SCHEMA,
        "mode": "verify-only",
        "installation": {},
        "repository": {},
        "gate": {},
        "trust": {},
        "execution": {
            "run_selection_enabled": run_enabled,
            "expected_goal_ids": list(builder.EXPECTED_GOAL_IDS),
            "runners": []
            if not run_enabled
            else [
                {
                    "goal_id": goal_id,
                    "path": builder.EXPECTED_RUNNERS[goal_id],
                    "sha256": runner_digests[goal_id],
                    "input_mode": builder.CURRENT_INPUT_PROTOCOL,
                    "output_mode": builder.CURRENT_OUTPUT_PROTOCOL,
                }
                for goal_id in builder.EXPECTED_GOAL_IDS
            ],
        },
        "receipts": {},
        "runtime": {},
    }


def _attestation(
    policy_sha256: str,
    reviewed_artifacts: dict[str, str],
    *,
    updates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    value = {
        "schema": builder.DEPLOYMENT_SCHEMA,
        "attestation_id": "gate-first-deployment-test-0001",
        "issued_at": "2026-07-24T00:00:00Z",
        "independently_administered": True,
        "administrator_identity": "independent-operator@example.test",
        "deployed": True,
        "conformant": True,
        "protocol_id": builder.PROTOCOL_ID,
        "protocol_sha256": reviewed_artifacts["gate_launcher_protocol"],
        "launcher_sha256": reviewed_artifacts["gate_launcher"],
        "gate_verifier_id": "world-aid-gate-0b-verifier/v1",
        "gate_verifier_sha256": reviewed_artifacts["gate_verifier"],
        "trust_policy_id": builder.POLICY_SCHEMA,
        "trust_policy_sha256": policy_sha256,
        "target_commit": "a" * 40,
        "target_heap_id": _digest(13),
        "runtime_authorized": False,
    }
    value.update(updates or {})
    return value


def _approval(
    *,
    policy_sha256: str,
    attestation_sha256: str,
    reviewed_artifacts: dict[str, str],
) -> dict[str, Any]:
    return {
        "schema_version": builder.SELECTION_SCHEMA,
        "gate_id": "gate-0b-selection",
        "record_id": "gate-0b-selection-test-0001",
        "decision": "approved",
        "issued_at": "2026-07-24T01:00:00Z",
        "not_before": "2026-07-24T01:00:00Z",
        "expires_at": "2099-01-01T00:00:00Z",
        "execution_boundary": {
            "protocol_id": builder.PROTOCOL_ID,
            "execution_authority": builder.EXECUTION_AUTHORITY,
            "operation": builder.OPERATION,
            "sealed_input_protocol": builder.CURRENT_INPUT_PROTOCOL,
            "result_protocol": builder.CURRENT_OUTPUT_PROTOCOL,
            "installed_launcher_path": ("/usr/local/libexec/world-aid-gate-first-launcher"),
            "operator_policy_id": builder.POLICY_SCHEMA,
            "operator_policy_sha256": policy_sha256,
            "deployment_attestation_id": ("gate-first-deployment-test-0001"),
            "deployment_attestation_sha256": attestation_sha256,
            "reviewed_artifacts": reviewed_artifacts,
        },
        "reviewed_state": {
            "root_commit": "a" * 40,
            "objective_heap": {
                "path": "docs/governance/world-aid-objective-heap.json",
                "sha256": _digest(13),
            },
        },
        "trust": {
            "signature_namespace": "world-aid-gate-0b-selection-v2",
            "signatures": [{"role": f"role-{index}"} for index in range(9)],
        },
    }


def _bound(path: str, digest: str, size: int = 100) -> dict[str, Any]:
    return {"source_path": path, "sha256": digest, "size": size}


def _tool(path: str, seed: int, version: str) -> dict[str, Any]:
    return {
        "source_path": path,
        "sha256": _digest(seed),
        "max_bytes": 4096,
        "version": version,
    }


def _input(path: str, seed: int, destination: str) -> dict[str, Any]:
    return {
        "source_path": path,
        "sha256": _digest(seed),
        "max_bytes": 4096,
        "workspace_relative_path": destination,
    }


def _g038(approval_sha256: str, boundary_sha256: str) -> dict[str, Any]:
    cache_entry = transport.g038.SIWECacheEntry(
        path="content",
        kind="directory",
        size=0,
        sha256=None,
    )
    return {
        "schema_version": builder.NATIVE_PLAN_SCHEMAS["WORLDCOIN-G038"],
        "goal_id": "WORLDCOIN-G038",
        "authorization_sha256": approval_sha256,
        "selection_record_id": "gate-0b-selection-test-0001",
        "network_policy": "external-deny-all",
        "network_boundary": {
            "attestation_sha256": boundary_sha256,
            "namespace": "net:[4026533000]",
            "apparmor_profile": "world-aid-gate-first (enforce)",
            "network_deny_canary_sha256": _digest(30),
            "egress_policy_sha256": _digest(31),
        },
        "platform": "linux",
        "architecture": "x86_64",
        "toolchain_archive_sha256": _digest(32),
        "node": _tool("/opt/world-aid/node", 33, "22.23.1"),
        "npm_cli": _tool("/opt/world-aid/npm-cli.js", 34, "10.9.8"),
        "manifest": _input(
            "/srv/world-aid/inputs/package.json",
            35,
            "package.json",
        ),
        "lockfile": _input(
            "/srv/world-aid/inputs/package-lock.json",
            36,
            "package-lock.json",
        ),
        "adapter": _input(
            "/srv/world-aid/inputs/index.mjs",
            37,
            "index.mjs",
        ),
        "smoke_source": _input(
            "/srv/world-aid/inputs/g038-smoke.mjs",
            38,
            "g038-smoke.mjs",
        ),
        "cache": {
            "source_path": "/srv/world-aid/inputs/npm-cache.tar",
            "sha256": _digest(39),
            "max_archive_bytes": 4096,
            "archive_format": "tar",
            "max_entries": 8,
            "max_extracted_bytes": 16384,
            "tree_sha256": transport.g038.cache_tree_sha256((cache_entry,)),
            "entries": [
                {
                    "path": "content",
                    "kind": "directory",
                    "size": 0,
                    "sha256": None,
                }
            ],
        },
        "resource_bounds": {
            "max_seconds": 30,
            "max_memory_mb": 512,
            "max_output_bytes": 65536,
            "max_file_bytes": 1048576,
            "max_workspace_entries": 1024,
            "max_workspace_bytes": 16777216,
        },
        "expires_at": "2099-01-01T00:00:00Z",
    }


def _g039(approval_sha256: str, boundary_sha256: str) -> dict[str, Any]:
    return {
        "schema_version": builder.NATIVE_PLAN_SCHEMAS["WORLDCOIN-G039"],
        "goal_id": "WORLDCOIN-G039",
        "authorization_sha256": approval_sha256,
        "network_boundary_sha256": boundary_sha256,
        "network_policy": "external-deny-all",
        "tool_path": "/opt/world-aid/bin/nargo",
        "tool_sha256": _digest(50),
        "tool_max_bytes": 1048576,
        "build_a_argv": [
            "{tool}",
            "build",
            "--input-root",
            "{input_root}",
            "--output",
            "{artifact}",
        ],
        "build_b_argv": [
            "{tool}",
            "build",
            "--input-root",
            "{input_root}",
            "--output",
            "{artifact}",
        ],
        "prove_argv": [
            "{tool}",
            "prove",
            "--input-root",
            "{input_root}",
            "--artifact",
            "{artifact}",
            "--proof",
            "{proof}",
        ],
        "verify_argv": [
            "{tool}",
            "verify",
            "--input-root",
            "{input_root}",
            "--artifact",
            "{artifact}",
            "--proof",
            "{proof}",
        ],
        "fixed_env": [["EXPECTED_VALUE", "fixed"]],
        "inputs": [
            _input(
                "/srv/world-aid/inputs/smoke-input.txt",
                51,
                "locked/smoke-input.txt",
            )
        ],
        "resource_bounds": {
            "max_seconds": 30,
            "max_memory_mb": 512,
            "max_output_bytes": 65536,
        },
        "artifact_relative_path": "target/smoke.bin",
        "proof_relative_path": "proofs/smoke.proof",
        "expires_at": "2099-01-01T00:00:00Z",
    }


def _g040(
    approval_sha256: str,
    approval_size: int,
    boundary_sha256: str,
) -> dict[str, Any]:
    return {
        "schema_version": builder.NATIVE_PLAN_SCHEMAS["WORLDCOIN-G040"],
        "goal_id": "WORLDCOIN-G040",
        "authorization": _bound(
            "/srv/world-aid/authority/selection.json",
            approval_sha256,
            approval_size,
        ),
        "network_boundary_attestation": _bound(
            "/run/world-aid/network-boundary.json",
            boundary_sha256,
        ),
        "network_policy": "external-deny-all",
        "python": {
            "path": "/opt/world-aid/python/bin/python3",
            "sha256": _digest(60),
            "size": 1048576,
            "version": "3.12.8",
        },
        "wheel": {
            "path": ("/srv/world-aid/wheels/duckdb-1.4.3-cp312-cp312-manylinux_2_17_x86_64.whl"),
            "sha256": _digest(61),
            "size": 1048576,
            "filename": ("duckdb-1.4.3-cp312-cp312-manylinux_2_17_x86_64.whl"),
            "duckdb_version": "1.4.3",
            "python_tag": "cp312",
            "abi_tag": "cp312",
            "platform_tag": "manylinux_2_17_x86_64",
        },
        "requirements_lock": _bound(
            "/srv/world-aid/inputs/requirements.lock",
            _digest(62),
        ),
        "runtime_policy": _bound(
            "/srv/world-aid/inputs/runtime-policy.json",
            _digest(63),
        ),
        "backup_policy": _bound(
            "/srv/world-aid/inputs/backup-policy.json",
            _digest(64),
        ),
        "storage_adr": _bound(
            "/srv/world-aid/inputs/storage-adr.md",
            _digest(65),
        ),
        "smoke_bootstrap_sha256": transport.g040.fixed_smoke_bootstrap_sha256(),
        "resource_bounds": {
            "max_seconds": 30,
            "max_memory_mb": 512,
            "max_output_bytes": 65536,
            "max_file_bytes": 16777216,
            "max_workspace_bytes": 33554432,
            "max_wheel_entries": 10000,
            "max_entry_bytes": 4194304,
            "max_uncompressed_bytes": 16777216,
        },
        "run_directory": "/var/lib/world-aid/gate-first-runs/test-0001",
        "expires_at": "2099-01-01T00:00:00Z",
    }


def _fixture(
    *,
    run_enabled: bool = False,
    attestation_updates: dict[str, Any] | None = None,
    runner_digest_override: tuple[str, str] | None = None,
) -> dict[str, Any]:
    runner_digests = {
        goal_id: _sha256((ROOT / builder.EXPECTED_RUNNERS[goal_id]).read_bytes())
        for goal_id in builder.EXPECTED_GOAL_IDS
    }
    if runner_digest_override is not None:
        runner_digests[runner_digest_override[0]] = runner_digest_override[1]
    reviewed_artifacts = {
        "gate_launcher_protocol": _sha256((ROOT / builder.GATE_LAUNCHER_PROTOCOL_PATH).read_bytes()),
        "gate_launcher": _sha256((ROOT / builder.GATE_LAUNCHER_PATH).read_bytes()),
        "gate_verifier": _sha256((ROOT / builder.GATE_VERIFIER_PATH).read_bytes()),
        **{builder.RUNNER_REVIEW_KEYS[goal_id]: runner_digests[goal_id] for goal_id in builder.EXPECTED_GOAL_IDS},
    }
    policy_bytes = _canonical(_policy(runner_digests, run_enabled=run_enabled))
    policy_sha256 = _sha256(policy_bytes)
    attestation_bytes = _canonical(
        _attestation(
            policy_sha256,
            reviewed_artifacts,
            updates=attestation_updates,
        )
    )
    attestation_sha256 = _sha256(attestation_bytes)
    approval_bytes = _canonical(
        _approval(
            policy_sha256=policy_sha256,
            attestation_sha256=attestation_sha256,
            reviewed_artifacts=reviewed_artifacts,
        )
    )
    approval_sha256 = _sha256(approval_bytes)
    boundary_digests = {goal_id: _digest(200 + index) for index, goal_id in enumerate(builder.EXPECTED_GOAL_IDS)}
    payloads = {
        "WORLDCOIN-G038": _g038(
            approval_sha256,
            boundary_digests["WORLDCOIN-G038"],
        ),
        "WORLDCOIN-G039": _g039(
            approval_sha256,
            boundary_digests["WORLDCOIN-G039"],
        ),
        "WORLDCOIN-G040": _g040(
            approval_sha256,
            len(approval_bytes),
            boundary_digests["WORLDCOIN-G040"],
        ),
    }
    profile = {
        "schema": builder.PROFILE_SCHEMA,
        "profile_id": "gate-first-execution-plans-test-0001",
        "status": "candidate-ready-for-external-authentication",
        "candidate_validation_enabled": True,
        "runtime_authorized": False,
        "contract": {
            "contract_id": builder.CONTRACT_ID,
            "builder_path": builder.BUILDER_PATH,
            "builder_sha256": _sha256((ROOT / builder.BUILDER_PATH).read_bytes()),
            "schema_path": builder.SCHEMA_PATH,
            "schema_sha256": _sha256(SCHEMA.read_bytes()),
            "transport_codec_path": builder.TRANSPORT_CODEC_PATH,
            "transport_codec_sha256": _sha256((ROOT / builder.TRANSPORT_CODEC_PATH).read_bytes()),
            "transport_input_schema_path": builder.TRANSPORT_INPUT_SCHEMA_PATH,
            "transport_input_schema_sha256": _sha256((ROOT / builder.TRANSPORT_INPUT_SCHEMA_PATH).read_bytes()),
            "transport_result_schema_path": builder.TRANSPORT_RESULT_SCHEMA_PATH,
            "transport_result_schema_sha256": _sha256((ROOT / builder.TRANSPORT_RESULT_SCHEMA_PATH).read_bytes()),
            "transport_spec_path": builder.TRANSPORT_SPEC_PATH,
            "transport_spec_sha256": _sha256((ROOT / builder.TRANSPORT_SPEC_PATH).read_bytes()),
            "receipt_verifier_path": builder.RECEIPT_VERIFIER_PATH,
            "receipt_verifier_sha256": _sha256((ROOT / builder.RECEIPT_VERIFIER_PATH).read_bytes()),
        },
        "authority": {
            "selection_approval": {
                "schema": builder.SELECTION_SCHEMA,
                "record_id": "gate-0b-selection-test-0001",
                "sha256": approval_sha256,
            },
            "operator_policy": {
                "schema": builder.POLICY_SCHEMA,
                "sha256": policy_sha256,
            },
            "deployment_attestation": {
                "schema": builder.DEPLOYMENT_SCHEMA,
                "attestation_id": "gate-first-deployment-test-0001",
                "sha256": attestation_sha256,
            },
        },
        "protocol": {
            "gate_protocol_id": builder.PROTOCOL_ID,
            "execution_authority": builder.EXECUTION_AUTHORITY,
            "operation": builder.OPERATION,
            "transport_protocol_id": builder.FUTURE_TRANSPORT_ID,
            "input_schema": builder.FUTURE_INPUT_SCHEMA,
            "input_protocol": builder.FUTURE_INPUT_PROTOCOL,
            "result_schema": builder.FUTURE_RESULT_SCHEMA,
            "output_protocol": builder.FUTURE_OUTPUT_PROTOCOL,
        },
        "plans": [
            {
                "goal_id": goal_id,
                "runner_path": builder.EXPECTED_RUNNERS[goal_id],
                "runner_sha256": runner_digests[goal_id],
                "native_plan_schema": builder.NATIVE_PLAN_SCHEMAS[goal_id],
                "canonicalization": builder.NATIVE_CANONICALIZATION[goal_id],
                "native_plan_sha256": _sha256(
                    _canonical(
                        payloads[goal_id],
                        ensure_ascii=(builder.NATIVE_CANONICALIZATION[goal_id] == "sorted-compact-ascii-lf/v1"),
                    )
                ),
                "network_boundary_attestation_sha256": boundary_digests[goal_id],
                "plan_payload": payloads[goal_id],
            }
            for goal_id in builder.EXPECTED_GOAL_IDS
        ],
    }
    gate_summary = {
        "status": "verified",
        "phase": "selection",
        "gate_id": "gate-0b-selection",
        "record_id": "gate-0b-selection-test-0001",
        "verified_approval_sha256": approval_sha256,
        "expires_at": "2099-01-01T00:00:00Z",
        "reviewed_root_commit": "a" * 40,
        "execution_authority": builder.EXECUTION_AUTHORITY,
        "approved_operation": builder.OPERATION,
        "operator_policy_sha256": policy_sha256,
        "deployment_attestation_id": "gate-first-deployment-test-0001",
        "deployment_attestation_sha256": attestation_sha256,
        "execution_boundary_verified": True,
        "artifact_count": 42,
        "signature_count": 9,
        "offline": True,
        "live_actions_authorized": False,
    }
    return {
        "profile": profile,
        "profile_bytes": _canonical(profile),
        "gate_summary": gate_summary,
        "approval_bytes": approval_bytes,
        "policy_bytes": policy_bytes,
        "attestation_bytes": attestation_bytes,
        "payloads": payloads,
    }


def _replace_profile(values: dict[str, Any], profile: dict[str, Any]) -> None:
    values["profile"] = profile
    values["profile_bytes"] = _canonical(profile)


def _refresh_native_plan_digest(
    profile: dict[str, Any],
    goal_id: str,
) -> None:
    index = builder.EXPECTED_GOAL_IDS.index(goal_id)
    plan = profile["plans"][index]
    plan["native_plan_sha256"] = _sha256(
        _canonical(
            plan["plan_payload"],
            ensure_ascii=(builder.NATIVE_CANONICALIZATION[goal_id] == "sorted-compact-ascii-lf/v1"),
        )
    )


def _build(
    values: dict[str, Any],
) -> builder.ValidatedCandidateExecutionPlanSet:
    return builder.build_validated_candidate_execution_plans(
        values["profile_bytes"],
        expected_profile_sha256=_sha256(values["profile_bytes"]),
        gate_verifier_summary=values["gate_summary"],
        selection_approval_bytes=values["approval_bytes"],
        operator_policy_bytes=values["policy_bytes"],
        deployment_attestation_bytes=values["attestation_bytes"],
        repo_root=ROOT,
    )


def test_schema_is_strict_and_disabled_template_is_nonconformant() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    template = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    transport_input_schema = json.loads((ROOT / builder.TRANSPORT_INPUT_SCHEMA_PATH).read_text(encoding="utf-8"))

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["additionalProperties"] is False
    assert schema["properties"]["candidate_validation_enabled"]["const"] is True
    assert schema["properties"]["runtime_authorized"]["const"] is False
    assert schema["$defs"]["protocol"]["additionalProperties"] is False
    assert schema["$defs"]["protocol"]["properties"]["input_protocol"]["const"] == "sealed-fd-json/v2"
    assert schema["$defs"]["protocol"]["properties"]["output_protocol"]["const"] == "stdout-json/v2"
    assert {
        "transport_codec_path",
        "transport_input_schema_path",
        "transport_result_schema_path",
        "transport_spec_path",
        "receipt_verifier_path",
    } <= set(schema["$defs"]["contract"]["required"])
    assert schema["$defs"]["g038CacheEntry"]["additionalProperties"] is False
    assert schema["$defs"]["g040Payload"]["properties"]["smoke_bootstrap_sha256"]["const"] == (
        transport.g040.fixed_smoke_bootstrap_sha256()
    )
    assert (
        transport_input_schema["$defs"]["g038_plan"]["properties"]["network_boundary"]["properties"]["namespace"][
            "pattern"
        ]
        == r"^net:\[[0-9]+\]$"
    )
    assert (
        transport_input_schema["$defs"]["g040_plan"]["properties"]["python"]["properties"]["version"]["pattern"]
        == r"^[0-9]+\.[0-9]+\.[0-9]+$"
    )
    for pattern in (
        schema["$defs"]["absolutePath"]["pattern"],
        transport_input_schema["$defs"]["absolute_path"]["pattern"],
    ):
        compiled = re.compile(pattern)
        assert compiled.fullmatch("/opt/world-aid/input.json")
        for invalid in ("/./x", "/../x", "/.", "/..", "/x/./y", "/x/../y"):
            assert compiled.fullmatch(invalid) is None
    assert len(schema["properties"]["plans"]["prefixItems"]) == 3
    assert template["candidate_validation_enabled"] is False
    assert template["runtime_authorized"] is False
    assert template["contract"]["transport_spec_path"] == builder.TRANSPORT_SPEC_PATH
    assert template["plans"] == []


def test_candidate_profile_uses_exact_reviewed_runner_transport_v2_ids() -> None:
    assert builder.FUTURE_TRANSPORT_ID == transport.TRANSPORT_PROTOCOL_ID
    assert builder.FUTURE_INPUT_SCHEMA == transport.INPUT_SCHEMA
    assert builder.FUTURE_INPUT_PROTOCOL == transport.SEALED_INPUT_PROTOCOL
    assert builder.FUTURE_RESULT_SCHEMA == transport.RESULT_SCHEMA
    assert builder.FUTURE_OUTPUT_PROTOCOL == transport.RESULT_PROTOCOL


def test_builds_only_exact_digest_bound_candidate_bytes_without_authority() -> None:
    values = _fixture()

    result = _build(values)

    assert result.runtime_authorized is False
    assert result.authority.approval_sha256 == _sha256(values["approval_bytes"])
    assert tuple(plan.goal_id for plan in result.plans) == (builder.EXPECTED_GOAL_IDS)
    for plan in result.plans:
        assert _sha256(plan.payload_bytes) == plan.native_plan_sha256
        assert plan.payload() == values["payloads"][plan.goal_id]
        native = transport._decode_plan(plan.goal_id, plan.payload())
        native_modules = {
            "WORLDCOIN-G038": transport.g038,
            "WORLDCOIN-G039": transport.g039,
            "WORLDCOIN-G040": transport.g040,
        }
        native_module = native_modules[plan.goal_id]
        assert native_module._plan_payload(native) == plan.payload()
        assert native_module.execution_plan_sha256(native) == plan.native_plan_sha256


@pytest.mark.parametrize(
    ("goal_id", "mutate", "message"),
    [
        (
            "WORLDCOIN-G038",
            lambda payload: payload["cache"]["entries"].__setitem__(0, {}),
            "cache.entries\\[0\\] fields differ",
        ),
        (
            "WORLDCOIN-G038",
            lambda payload: payload["cache"]["entries"][0].__setitem__(
                "kind",
                "device",
            ),
            "kind must be directory or file",
        ),
        (
            "WORLDCOIN-G038",
            lambda payload: payload["cache"].__setitem__(
                "tree_sha256",
                _digest(998),
            ),
            "cache tree_sha256 differs",
        ),
        (
            "WORLDCOIN-G039",
            lambda payload: payload["build_a_argv"].__setitem__(1, "curl"),
            "requests network or download behavior",
        ),
        (
            "WORLDCOIN-G039",
            lambda payload: payload["build_a_argv"].append("--value={caller}"),
            "unsupported placeholder",
        ),
        (
            "WORLDCOIN-G039",
            lambda payload: payload.__setitem__("fixed_env", [["HOME", "evil"]]),
            "runner-controlled key",
        ),
        (
            "WORLDCOIN-G039",
            lambda payload: payload.__setitem__(
                "fixed_env",
                [["Z_VALUE", "1"], ["A_VALUE", "2"]],
            ),
            "keys must be sorted",
        ),
        (
            "WORLDCOIN-G039",
            lambda payload: payload.__setitem__(
                "fixed_env",
                [["EXPECTED_VALUE", "https://example.test/evil"]],
            ),
            "contains a network URI",
        ),
        (
            "WORLDCOIN-G040",
            lambda payload: payload["wheel"].__setitem__(
                "filename",
                "duckdb-1.4.3-cp312-cp312-manylinux.whl.evil",
            ),
            "wheel filename",
        ),
        (
            "WORLDCOIN-G040",
            lambda payload: payload.__setitem__(
                "smoke_bootstrap_sha256",
                _digest(997),
            ),
            "fixed runner bootstrap",
        ),
        (
            "WORLDCOIN-G040",
            lambda payload: payload["python"].__setitem__(
                "version",
                "3.12.8.1",
            ),
            "exactly three numeric components",
        ),
        (
            "WORLDCOIN-G038",
            lambda payload: payload["resource_bounds"].__setitem__(
                "max_memory_mb",
                1,
            ),
            "max_memory_mb must be an integer from 64",
        ),
        (
            "WORLDCOIN-G039",
            lambda payload: payload["resource_bounds"].__setitem__(
                "max_output_bytes",
                1024 * 1024 * 1024 + 1,
            ),
            "max_output_bytes must be an integer",
        ),
        (
            "WORLDCOIN-G040",
            lambda payload: payload["resource_bounds"].__setitem__(
                "max_wheel_entries",
                1,
            ),
            "max_wheel_entries must be an integer from 4",
        ),
    ],
)
def test_rejects_native_constructor_and_transport_invariant_drift(
    goal_id: str,
    mutate: Any,
    message: str,
) -> None:
    values = _fixture()
    profile = copy.deepcopy(values["profile"])
    index = builder.EXPECTED_GOAL_IDS.index(goal_id)
    mutate(profile["plans"][index]["plan_payload"])
    _refresh_native_plan_digest(profile, goal_id)
    _replace_profile(values, profile)

    with pytest.raises(builder.ExecutionPlanContractError, match=message):
        _build(values)


@pytest.mark.parametrize(
    ("updates", "message"),
    [
        ({"protocol_sha256": _digest(900)}, "protocol_sha256 drift"),
        ({"launcher_sha256": _digest(901)}, "launcher_sha256 drift"),
        ({"gate_verifier_sha256": _digest(902)}, "gate_verifier_sha256 drift"),
        ({"target_commit": "b" * 40}, "target_commit drift"),
        ({"target_heap_id": _digest(903)}, "target_heap_id drift"),
        (
            {"administrator_identity": " invalid identity"},
            "administrator_identity is invalid",
        ),
        (
            {"issued_at": "2026-07-24T02:00:00Z"},
            "postdates the signed selection approval",
        ),
    ],
)
def test_rejects_signed_but_semantically_drifting_deployment_attestation(
    updates: dict[str, Any],
    message: str,
) -> None:
    values = _fixture(attestation_updates=updates)

    with pytest.raises(builder.ExecutionPlanContractError, match=message):
        _build(values)


@pytest.mark.parametrize(
    "digest_key",
    [
        "transport_codec_sha256",
        "transport_input_schema_sha256",
        "transport_result_schema_sha256",
        "transport_spec_sha256",
        "receipt_verifier_sha256",
    ],
)
def test_rejects_contract_dependency_digest_drift_before_transport_import(
    digest_key: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    values = _fixture()
    profile = copy.deepcopy(values["profile"])
    profile["contract"][digest_key] = _digest(904)
    _replace_profile(values, profile)
    imported = False
    original_import = __import__

    def track_import(
        name: str,
        globals: Any = None,
        locals: Any = None,
        fromlist: Any = (),
        level: int = 0,
    ) -> Any:
        nonlocal imported
        if name == "scripts.world_aid_runner_transport_v2":
            imported = True
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr("builtins.__import__", track_import)
    with pytest.raises(
        builder.ExecutionPlanContractError,
        match="plan contract .* digest drift",
    ):
        _build(values)
    assert imported is False


def test_rejects_signed_runner_digest_that_differs_from_repository_file() -> None:
    values = _fixture(
        runner_digest_override=("WORLDCOIN-G039", _digest(905)),
    )

    with pytest.raises(
        builder.ExecutionPlanContractError,
        match="signed repository artifact digest drift: scripts/run_world_aid_zkp_bootstrap.py",
    ):
        _build(values)


@pytest.mark.parametrize(
    ("goal_id", "mutate"),
    [
        (
            "WORLDCOIN-G038",
            lambda payload: payload["node"].__setitem__("source_path", "/caller/node"),
        ),
        (
            "WORLDCOIN-G039",
            lambda payload: payload["build_a_argv"].append("--caller-command"),
        ),
        (
            "WORLDCOIN-G040",
            lambda payload: payload["resource_bounds"].__setitem__("max_seconds", 31),
        ),
    ],
)
def test_rejects_caller_authored_plan_drift(
    goal_id: str,
    mutate: Any,
) -> None:
    values = _fixture()
    result = _build(values)
    candidates = copy.deepcopy(values["payloads"])
    mutate(candidates[goal_id])

    with pytest.raises(
        builder.ExecutionPlanContractError,
        match=rf"caller plan payload drift for {goal_id}",
    ):
        builder.validate_candidate_plans(result, candidates)


@pytest.mark.parametrize(
    ("target", "message"),
    [
        ("operator_policy", "operator policy binding drift"),
        ("deployment_attestation", "deployment attestation binding drift"),
    ],
)
def test_rejects_profile_authority_drift(target: str, message: str) -> None:
    values = _fixture()
    profile = copy.deepcopy(values["profile"])
    profile["authority"][target]["sha256"] = _digest(999)
    values["profile_bytes"] = _canonical(profile)

    with pytest.raises(builder.ExecutionPlanContractError, match=message):
        _build(values)


def test_rejects_native_plan_digest_or_resource_bound_drift() -> None:
    values = _fixture()
    profile = copy.deepcopy(values["profile"])
    g039 = profile["plans"][1]
    g039["plan_payload"]["resource_bounds"]["max_seconds"] = 31
    values["profile_bytes"] = _canonical(profile)

    with pytest.raises(
        builder.ExecutionPlanContractError,
        match="WORLDCOIN-G039 native plan digest drift",
    ):
        _build(values)


def test_rejects_impossible_enabled_v1_policy_combination() -> None:
    values = _fixture(run_enabled=True)

    with pytest.raises(
        builder.ExecutionPlanContractError,
        match="current v1 operator policy must remain verify-only",
    ):
        _build(values)


def test_rejects_profile_digest_not_bound_by_external_authority() -> None:
    values = _fixture()

    with pytest.raises(
        builder.ExecutionPlanContractError,
        match="profile digest differs from external authority",
    ):
        builder.build_validated_candidate_execution_plans(
            values["profile_bytes"],
            expected_profile_sha256=_digest(999),
            gate_verifier_summary=values["gate_summary"],
            selection_approval_bytes=values["approval_bytes"],
            operator_policy_bytes=values["policy_bytes"],
            deployment_attestation_bytes=values["attestation_bytes"],
            repo_root=ROOT,
        )


def test_rejects_noncanonical_profile_and_duplicate_keys() -> None:
    values = _fixture()
    pretty = json.dumps(values["profile"], indent=2).encode()
    with pytest.raises(
        builder.ExecutionPlanContractError,
        match="execution plan profile is not canonical JSON",
    ):
        builder.build_validated_candidate_execution_plans(
            pretty,
            expected_profile_sha256=_sha256(pretty),
            gate_verifier_summary=values["gate_summary"],
            selection_approval_bytes=values["approval_bytes"],
            operator_policy_bytes=values["policy_bytes"],
            deployment_attestation_bytes=values["attestation_bytes"],
            repo_root=ROOT,
        )

    duplicate = b'{"schema":"x","schema":"y"}\n'
    with pytest.raises(
        builder.ExecutionPlanContractError,
        match="duplicate JSON key",
    ):
        builder.build_validated_candidate_execution_plans(
            duplicate,
            expected_profile_sha256=_sha256(duplicate),
            gate_verifier_summary=values["gate_summary"],
            selection_approval_bytes=values["approval_bytes"],
            operator_policy_bytes=values["policy_bytes"],
            deployment_attestation_bytes=values["attestation_bytes"],
            repo_root=ROOT,
        )
