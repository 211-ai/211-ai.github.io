"""Offline tests for exact-key, immutable Gate-first run receipts."""

from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

import scripts.verify_world_aid_gate_first_receipt as receipt_verifier
import scripts.world_aid_gate_first_launcher as launcher
from scripts.verify_world_aid_gate_first_receipt import (
    GateFirstReceiptError,
    _build_parser,
    _key_fingerprint,
    canonical_json_bytes,
    verify_gate_first_receipt,
)
from tests.world_aid.test_gate_first_launcher import (
    _context,
    _policy_payload,
    _sha256,
    _write_bytes,
    _write_policy,
)


@dataclass
class SignedReceiptFixture:
    operator_root: Path
    context: launcher.ExternalSecurityContext
    policy: launcher.OperatorPolicy
    run_id: str
    run_dir: Path
    receipt_path: Path
    signature_path: Path
    private_key: Path


def _run(*args: str, cwd: Path, input_bytes: bytes | None = None) -> None:
    subprocess.run(
        list(args),
        cwd=cwd,
        check=True,
        input=input_bytes,
        capture_output=True,
        env={
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "PATH": "/usr/bin:/bin",
            "TZ": "UTC",
        },
    )


def _generate_key(tmp_path: Path, name: str) -> tuple[Path, str, str]:
    private_key = tmp_path / name
    _run(
        "/usr/bin/ssh-keygen",
        "-q",
        "-t",
        "ed25519",
        "-N",
        "",
        "-f",
        str(private_key),
        cwd=tmp_path,
    )
    public_line = private_key.with_suffix(".pub").read_text(encoding="utf-8").strip()
    _, key_blob, *_ = public_line.split()
    return private_key, public_line, _key_fingerprint(key_blob)


def _sign_receipt(private_key: Path, receipt_path: Path, signature_path: Path) -> None:
    if signature_path.exists():
        signature_path.chmod(0o600)
        signature_path.unlink()
    generated = Path(str(receipt_path) + ".sig")
    if generated.exists():
        generated.unlink()
    _run(
        "/usr/bin/ssh-keygen",
        "-Y",
        "sign",
        "-f",
        str(private_key),
        "-n",
        "world-aid-gate-first-launch-v1",
        str(receipt_path),
        cwd=receipt_path.parent,
    )
    generated.rename(signature_path)
    signature_path.chmod(0o400)


def _write_canonical(path: Path, payload: dict[str, Any]) -> Path:
    return _write_bytes(path, canonical_json_bytes(payload), mode=0o400)


def _fake_digest(seed: int) -> str:
    return f"sha256:{seed:064x}"


def _native_digest(payload: dict[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def _command_evidence(seed: int) -> dict[str, Any]:
    return {
        "exit_code": 0,
        "elapsed_ms": seed,
        "stdout_sha256": _fake_digest(seed),
        "stdout_bytes": seed,
        "stderr_sha256": _fake_digest(seed + 1),
        "stderr_bytes": 0,
    }


def _g038_native_receipt(approval_sha256: str) -> dict[str, Any]:
    boundary = {
        "namespace": "world-aid-offline",
        "apparmor_profile": "world-aid-gate-first",
        "interfaces": ["lo"],
        "no_external_route": True,
        "network_deny_canary_sha256": _fake_digest(38),
        "egress_policy_sha256": _fake_digest(39),
    }
    return {
        "schema_version": receipt_verifier.G038_RECEIPT_SCHEMA,
        "goal_id": "WORLDCOIN-G038",
        "status": "passed",
        "completed_at": "2026-07-24T12:00:01Z",
        "valid_until": "2026-07-24T13:00:00Z",
        "offline": True,
        "live_actions_authorized": False,
        "selection_record_id": "gate-0b-selection-synthetic01",
        "selection_approval_sha256": approval_sha256,
        "real_execution": True,
        "cache_mutated": False,
        "toolchain": {
            "platform": "linux",
            "architecture": "x86_64",
            "archive_sha256": _fake_digest(40),
            "node_sha256": _fake_digest(41),
            "node_version": "22.23.1",
            "npm_cli_sha256": _fake_digest(42),
            "npm_version": "10.9.8",
        },
        "inputs": {
            "manifest_sha256": _fake_digest(43),
            "lock_sha256": _fake_digest(44),
            "adapter_sha256": _fake_digest(45),
        },
        "cache": {
            "reviewed_before_sha256": _fake_digest(46),
            "reviewed_after_sha256": _fake_digest(46),
            "local_before_sha256": _fake_digest(47),
            "local_after_sha256": _fake_digest(48),
        },
        "network": {
            "enforcement": "signed-namespace-plus-apparmor",
            "attempt_monitor": "not-configured",
            "attempt_count": None,
            "external_network_succeeded": False,
            "boundary_before": boundary,
            "boundary_after": dict(boundary),
        },
        "smoke_result": {"eoa": True, "eip1271": True, "contractReads": 1},
    }


def _g039_native_receipt(
    approval_sha256: str,
    plan_sha256: str,
    boundary_sha256: str,
) -> dict[str, Any]:
    build_sha256 = _fake_digest(51)
    return {
        "schema_version": receipt_verifier.G039_RECEIPT_SCHEMA,
        "goal_id": "WORLDCOIN-G039",
        "execution_plan_sha256": plan_sha256,
        "authorization_sha256": approval_sha256,
        "tool": {
            "path": "/opt/world-aid/zkp-tool",
            "sha256": _fake_digest(52),
            "max_bytes": 1048576,
        },
        "inputs": [
            {
                "source_path": "/opt/world-aid/circuit.json",
                "sha256": _fake_digest(53),
                "max_bytes": 4096,
                "workspace_relative_path": "inputs/circuit.json",
            }
        ],
        "repeat_build_hashes": [build_sha256, build_sha256],
        "proof_sha256": _fake_digest(54),
        "proof_result": True,
        "verify_result": True,
        "network_registry_denied": True,
        "network_boundary": {
            "policy": "external-deny-all",
            "attestation_sha256": boundary_sha256,
            "authority": "external-gate-first-launcher",
        },
        "resource_bounds": {
            "max_seconds": 60,
            "max_memory_mb": 512,
            "max_output_bytes": 1048576,
            "max_open_files": 128,
            "observed_process_output_bytes": 128,
        },
        "expiry": "2026-07-24T13:00:00Z",
        "commands": {
            "build_a": _command_evidence(55),
            "build_b": _command_evidence(56),
            "prove": _command_evidence(57),
            "verify": _command_evidence(58),
        },
        "production_trust": False,
        "completed_at": "2026-07-24T12:00:01Z",
    }


def _g040_native_receipt(
    approval_sha256: str,
    plan_sha256: str,
    boundary_sha256: str,
) -> dict[str, Any]:
    reviewed_inputs = {
        role: {
            "source_path": f"/opt/world-aid/{role}.json",
            "sha256": _fake_digest(seed),
            "size": 512,
        }
        for seed, role in enumerate(
            ("requirements_lock", "runtime_policy", "backup_policy", "storage_adr"),
            start=61,
        )
    }
    return {
        "schema_version": receipt_verifier.G040_RECEIPT_SCHEMA,
        "goal_id": "WORLDCOIN-G040",
        "status": "passed",
        "execution_plan_sha256": plan_sha256,
        "authorization_sha256": approval_sha256,
        "network_boundary": {
            "policy": "external-deny-all",
            "attestation_sha256": boundary_sha256,
            "authority": "external-gate-first-launcher",
        },
        "python": {
            "path": "/usr/bin/python3",
            "sha256": _fake_digest(65),
            "size": 1000000,
            "version": "3.12.4",
            "flags": ["-I", "-S", "-B"],
        },
        "wheel": {
            "path": "/opt/world-aid/duckdb-1.3.2-cp312-cp312-manylinux_x86_64.whl",
            "filename": "duckdb-1.3.2-cp312-cp312-manylinux_x86_64.whl",
            "sha256": _fake_digest(66),
            "size": 1048576,
            "duckdb_version": "1.3.2",
            "python_tag": "cp312",
            "abi_tag": "cp312",
            "platform_tag": "manylinux_x86_64",
            "validation": {
                "entry_count": 4,
                "file_count": 4,
                "uncompressed_bytes": 2048,
                "record_count": 4,
                "metadata_name": "duckdb",
                "metadata_version": "1.3.2",
                "wheel_tag": "cp312-cp312-manylinux_x86_64",
            },
        },
        "reviewed_inputs": reviewed_inputs,
        "smoke_bootstrap_sha256": _fake_digest(67),
        "checks": {name: True for name in receipt_verifier.G040_REQUIRED_CHECKS},
        "cleanup": {
            "database_exists": False,
            "temporary_data_exists": False,
            "wal_exists": False,
            "isolated_site_removed_before_publication": True,
            "workspace_removed_before_publication": True,
        },
        "deny_settings": dict(receipt_verifier.G040_DENY_SETTINGS),
        "loaded_dynamic_extensions": [],
        "network_attempts": 0,
        "single_writer_enforced": True,
        "second_writer_evidence": {
            "schema_version": "world-human-aid-g040-second-writer/v1",
            "import_succeeded": True,
            "connect_attempted": True,
            "connect_succeeded": False,
            "write_attempted": False,
            "rejected": True,
            "rejection_stage": "connect",
            "exception_module": "_duckdb",
            "exception_type": "IOException",
            "lock_marker": "could not set lock",
            "message_sha256": "a" * 64,
            "message_bytes": 64,
            "message_truncated": False,
        },
        "g033_excluded_controls": list(receipt_verifier.G040_EXCLUDED_CONTROLS),
        "resource_bounds": {
            "max_seconds": 60,
            "max_memory_mb": 512,
            "max_output_bytes": 1048576,
            "max_file_bytes": 1048576,
            "max_workspace_bytes": 8388608,
            "max_wheel_entries": 1000,
            "max_entry_bytes": 1048576,
            "max_uncompressed_bytes": 4194304,
            "max_open_files": 128,
            "observed_process_output_bytes": 128,
            "observed_workspace_bytes_before_cleanup": 4096,
        },
        "command": _command_evidence(68),
        "offline": True,
        "live_actions_authorized": False,
        "production_trust": False,
        "expires_at": "2026-07-24T13:00:00Z",
        "completed_at": "2026-07-24T12:00:01Z",
    }


def _goal_evidence(goal_id: str, approval_sha256: str) -> dict[str, Any]:
    seed = {"WORLDCOIN-G038": 71, "WORLDCOIN-G039": 72, "WORLDCOIN-G040": 73}[goal_id]
    plan_sha256 = _fake_digest(seed)
    boundary_sha256 = _fake_digest(seed + 10)
    if goal_id == "WORLDCOIN-G038":
        native = _g038_native_receipt(approval_sha256)
    elif goal_id == "WORLDCOIN-G039":
        native = _g039_native_receipt(approval_sha256, plan_sha256, boundary_sha256)
    else:
        native = _g040_native_receipt(approval_sha256, plan_sha256, boundary_sha256)
    return {
        "native_receipt": native,
        "native_receipt_sha256": _native_digest(native),
        "execution_plan_sha256": plan_sha256,
        "network_boundary_attestation_sha256": boundary_sha256,
    }


def _signed_fixture(tmp_path: Path) -> SignedReceiptFixture:
    operator_root = tmp_path / "operator"
    operator_root.mkdir(mode=0o700)
    context = _context(operator_root)
    repo_root = operator_root / "repository"
    repo_root.mkdir(mode=0o700)

    copied_ssh_keygen = operator_root / "bin/ssh-keygen"
    copied_ssh_keygen.parent.mkdir(mode=0o700)
    shutil.copy2(Path("/usr/bin/ssh-keygen"), copied_ssh_keygen)
    copied_ssh_keygen.chmod(0o500)

    key_dir = tmp_path / "private-keys"
    key_dir.mkdir(mode=0o700)
    private_key, public_line, fingerprint = _generate_key(key_dir, "launcher")
    identity = "launcher@example.invalid"
    key_type, key_blob, *_ = public_line.split()
    allowed_signers = _write_bytes(
        operator_root / "etc/receipt.allowed_signers",
        f"{identity} {key_type} {key_blob}\n".encode(),
        mode=0o400,
    )

    approval_payload = {
        "record_id": "gate-0b-selection-synthetic01",
        "reviewed_state": {"root_commit": "2" * 40},
    }
    approval_path = repo_root / launcher.CANONICAL_SELECTION_APPROVAL
    _write_canonical(approval_path, approval_payload)

    runner_digests = {
        goal_id: f"sha256:{index:064x}"
        for index, goal_id in enumerate(launcher.EXPECTED_GOAL_IDS, start=1)
    }
    policy_payload = _policy_payload(operator_root, run_enabled=True)
    policy_payload["installation"]["ssh_keygen_sha256"] = _sha256(copied_ssh_keygen)
    policy_payload["receipts"].update(
        {
            "allowed_signers_sha256": _sha256(allowed_signers),
            "signer_identity": identity,
            "signer_fingerprint": fingerprint,
        }
    )
    for runner in policy_payload["execution"]["runners"]:
        runner["sha256"] = runner_digests[runner["goal_id"]]
    policy_path = _write_policy(operator_root, policy_payload)
    policy = launcher.load_operator_policy(policy_path, context=context)

    run_id = "gate-first-synthetic-run-0001"
    run_dir = operator_root / "var/runs" / run_id
    goals_dir = run_dir / "goals"
    goals_dir.mkdir(parents=True, mode=0o700)
    for directory in (
        operator_root / "var",
        operator_root / "var/runs",
        run_dir,
        goals_dir,
    ):
        directory.chmod(0o700)
    goal_records: list[dict[str, str]] = []
    for goal_id in launcher.EXPECTED_GOAL_IDS:
        result_path = goals_dir / f"{goal_id}.json"
        result_payload = {
            "schema": receipt_verifier.GOAL_RESULT_SCHEMA,
            "run_id": run_id,
            "goal_id": goal_id,
            "status": "passed",
            "offline": True,
            "live_actions_authorized": False,
            "runner_sha256": runner_digests[goal_id],
            "selection_approval_sha256": _sha256(approval_path),
            "started_at": "2026-07-24T12:00:00Z",
            "completed_at": "2026-07-24T12:00:01Z",
            "evidence": _goal_evidence(goal_id, _sha256(approval_path)),
        }
        _write_canonical(result_path, result_payload)
        goal_records.append(
            {
                "goal_id": goal_id,
                "status": "passed",
                "runner_sha256": runner_digests[goal_id],
                "result_path": f"goals/{goal_id}.json",
                "result_sha256": _sha256(result_path),
            }
        )

    environment_digest = f"sha256:{hashlib.sha256(canonical_json_bytes(launcher.EXPECTED_CLEAN_ENVIRONMENT)).hexdigest()}"
    aggregate = {
        "schema": receipt_verifier.RUN_RECEIPT_SCHEMA,
        "run_id": run_id,
        "status": "passed",
        "offline": True,
        "live_actions_authorized": False,
        "started_at": "2026-07-24T12:00:00Z",
        "completed_at": "2026-07-24T12:00:03Z",
        "selection": {
            "approval_sha256": _sha256(approval_path),
            "record_id": approval_payload["record_id"],
            "reviewed_root_commit": approval_payload["reviewed_state"]["root_commit"],
        },
        "launcher": {
            "launcher_sha256": policy.launcher_sha256,
            "policy_sha256": policy.raw_sha256,
            "python_sha256": policy.python_sha256,
            "gate_verifier_sha256": policy.gate_verifier_sha256,
        },
        "boundary": {
            "apparmor_profile": policy.apparmor_profile,
            "network_namespace": policy.network_namespace,
            "loopback_only": True,
            "no_external_route": True,
            "clean_environment_sha256": environment_digest,
        },
        "goals": goal_records,
    }
    receipt_path = _write_canonical(run_dir / receipt_verifier.RECEIPT_FILENAME, aggregate)
    signature_path = run_dir / receipt_verifier.SIGNATURE_FILENAME
    _sign_receipt(private_key, receipt_path, signature_path)

    return SignedReceiptFixture(
        operator_root=operator_root,
        context=context,
        policy=policy,
        run_id=run_id,
        run_dir=run_dir,
        receipt_path=receipt_path,
        signature_path=signature_path,
        private_key=private_key,
    )


def _make_run_writable(fixture: SignedReceiptFixture) -> None:
    (fixture.operator_root / "var").chmod(0o700)
    (fixture.operator_root / "var/runs").chmod(0o700)
    fixture.run_dir.chmod(0o700)
    (fixture.run_dir / "goals").chmod(0o700)


def _replace_goal_result(
    fixture: SignedReceiptFixture,
    goal_id: str,
    transform: Any,
) -> None:
    _make_run_writable(fixture)
    result_path = fixture.run_dir / "goals" / f"{goal_id}.json"
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    transform(payload)
    result_path.chmod(0o600)
    result_path.write_bytes(canonical_json_bytes(payload))
    result_path.chmod(0o400)

    aggregate = json.loads(fixture.receipt_path.read_text(encoding="utf-8"))
    matching = [goal for goal in aggregate["goals"] if goal["goal_id"] == goal_id]
    assert len(matching) == 1
    matching[0]["result_sha256"] = _sha256(result_path)
    fixture.receipt_path.chmod(0o600)
    fixture.receipt_path.write_bytes(canonical_json_bytes(aggregate))
    fixture.receipt_path.chmod(0o400)
    _sign_receipt(fixture.private_key, fixture.receipt_path, fixture.signature_path)


def test_receipt_verifies_exact_signature_and_all_three_goal_results(
    tmp_path: Path,
) -> None:
    fixture = _signed_fixture(tmp_path)

    summary = verify_gate_first_receipt(
        policy=fixture.policy,
        run_id=fixture.run_id,
        context=fixture.context,
    )

    assert summary["schema"] == receipt_verifier.VERIFY_RESULT_SCHEMA
    assert summary["status"] == "verified"
    assert summary["run_id"] == fixture.run_id
    assert list(summary["goal_result_sha256"]) == list(launcher.EXPECTED_GOAL_IDS)
    assert summary["offline"] is True
    assert summary["live_actions_authorized"] is False


def test_receipt_rejects_wrong_declared_key_even_if_signature_is_valid(
    tmp_path: Path,
) -> None:
    fixture = _signed_fixture(tmp_path)
    wrong_policy = dataclasses.replace(
        fixture.policy,
        receipt_signer_fingerprint="SHA256:" + ("A" * 43),
    )
    with pytest.raises(GateFirstReceiptError, match="fingerprint"):
        verify_gate_first_receipt(
            policy=wrong_policy,
            run_id=fixture.run_id,
            context=fixture.context,
        )


def test_receipt_rejects_tampered_result_and_symlink_replacement(
    tmp_path: Path,
) -> None:
    fixture = _signed_fixture(tmp_path)
    result_path = fixture.run_dir / "goals/WORLDCOIN-G039.json"
    _make_run_writable(fixture)
    result_path.chmod(0o600)
    original = result_path.read_bytes()
    result_path.write_bytes(original.replace(b'"passed"', b'"failed"', 1))
    result_path.chmod(0o400)

    with pytest.raises(GateFirstReceiptError, match="digest differs"):
        verify_gate_first_receipt(
            policy=fixture.policy,
            run_id=fixture.run_id,
            context=fixture.context,
        )

    _make_run_writable(fixture)
    result_path.unlink()
    result_path.symlink_to(fixture.run_dir / "goals/WORLDCOIN-G038.json")
    with pytest.raises(GateFirstReceiptError, match="securely open"):
        verify_gate_first_receipt(
            policy=fixture.policy,
            run_id=fixture.run_id,
            context=fixture.context,
        )


def test_receipt_rejects_signature_from_an_untrusted_key(tmp_path: Path) -> None:
    fixture = _signed_fixture(tmp_path)
    second_key_dir = tmp_path / "second-key"
    second_key_dir.mkdir(mode=0o700)
    second_key, _, _ = _generate_key(second_key_dir, "untrusted")
    _make_run_writable(fixture)
    fixture.receipt_path.chmod(0o400)
    _sign_receipt(second_key, fixture.receipt_path, fixture.signature_path)

    with pytest.raises(GateFirstReceiptError, match="signature is invalid"):
        verify_gate_first_receipt(
            policy=fixture.policy,
            run_id=fixture.run_id,
            context=fixture.context,
        )


def test_receipt_rejects_integer_in_place_of_security_boolean(
    tmp_path: Path,
) -> None:
    fixture = _signed_fixture(tmp_path)
    payload = json.loads(fixture.receipt_path.read_text(encoding="utf-8"))
    payload["offline"] = 1
    fixture.receipt_path.chmod(0o600)
    fixture.receipt_path.write_bytes(canonical_json_bytes(payload))
    fixture.receipt_path.chmod(0o400)
    _sign_receipt(
        fixture.private_key,
        fixture.receipt_path,
        fixture.signature_path,
    )

    with pytest.raises(GateFirstReceiptError, match="invalid offline"):
        verify_gate_first_receipt(
            policy=fixture.policy,
            run_id=fixture.run_id,
            context=fixture.context,
        )


def test_receipt_rejects_arbitrary_nonempty_goal_evidence(tmp_path: Path) -> None:
    fixture = _signed_fixture(tmp_path)

    def replace(payload: dict[str, Any]) -> None:
        payload["evidence"] = {"synthetic_contract_test": True}

    _replace_goal_result(fixture, "WORLDCOIN-G038", replace)
    with pytest.raises(GateFirstReceiptError, match="evidence keys differ"):
        verify_gate_first_receipt(
            policy=fixture.policy,
            run_id=fixture.run_id,
            context=fixture.context,
        )


def test_receipt_rejects_native_receipt_digest_drift(tmp_path: Path) -> None:
    fixture = _signed_fixture(tmp_path)

    def replace(payload: dict[str, Any]) -> None:
        payload["evidence"]["native_receipt"]["smoke_result"]["eoa"] = False

    _replace_goal_result(fixture, "WORLDCOIN-G038", replace)
    with pytest.raises(GateFirstReceiptError, match="canonical native receipt"):
        verify_gate_first_receipt(
            policy=fixture.policy,
            run_id=fixture.run_id,
            context=fixture.context,
        )


def test_g038_plan_and_boundary_digests_are_exact_signed_wrapper_bindings(
    tmp_path: Path,
) -> None:
    fixture = _signed_fixture(tmp_path)
    result_path = fixture.run_dir / "goals/WORLDCOIN-G038.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    evidence = result["evidence"]
    native = evidence["native_receipt"]

    # G038's legacy Gate-compatible v2 native schema is frozen without these
    # fields.  The launcher records them in the exact goal-result envelope,
    # whose digest is in the signed aggregate receipt.
    assert "execution_plan_sha256" not in native
    assert "network_boundary_attestation_sha256" not in native
    assert receipt_verifier.DIGEST_RE.fullmatch(evidence["execution_plan_sha256"])
    assert receipt_verifier.DIGEST_RE.fullmatch(
        evidence["network_boundary_attestation_sha256"]
    )
    aggregate = json.loads(fixture.receipt_path.read_text(encoding="utf-8"))
    g038 = next(goal for goal in aggregate["goals"] if goal["goal_id"] == "WORLDCOIN-G038")
    assert g038["result_sha256"] == _sha256(result_path)
    assert verify_gate_first_receipt(
        policy=fixture.policy,
        run_id=fixture.run_id,
        context=fixture.context,
    )["status"] == "verified"


@pytest.mark.parametrize(
    "field",
    ("execution_plan_sha256", "network_boundary_attestation_sha256"),
)
def test_g038_rejects_malformed_signed_wrapper_binding(
    tmp_path: Path,
    field: str,
) -> None:
    fixture = _signed_fixture(tmp_path)

    def replace(payload: dict[str, Any]) -> None:
        payload["evidence"][field] = "sha256:" + ("A" * 64)

    _replace_goal_result(fixture, "WORLDCOIN-G038", replace)
    with pytest.raises(GateFirstReceiptError, match="lowercase sha256 digest"):
        verify_gate_first_receipt(
            policy=fixture.policy,
            run_id=fixture.run_id,
            context=fixture.context,
        )


@pytest.mark.parametrize(
    ("goal_id", "mutation", "message"),
    [
        (
            "WORLDCOIN-G038",
            lambda evidence: evidence["native_receipt"].__setitem__(
                "schema_version", "world-human-aid-siwe-bootstrap-verification-receipt/v1"
            ),
            "invalid schema_version",
        ),
        (
            "WORLDCOIN-G039",
            lambda evidence: evidence["native_receipt"].__setitem__(
                "authorization_sha256", _fake_digest(900)
            ),
            "invalid authorization_sha256",
        ),
        (
            "WORLDCOIN-G039",
            lambda evidence: evidence["native_receipt"].__setitem__(
                "execution_plan_sha256", _fake_digest(901)
            ),
            "invalid execution_plan_sha256",
        ),
        (
            "WORLDCOIN-G040",
            lambda evidence: evidence["native_receipt"]["network_boundary"].__setitem__(
                "attestation_sha256", _fake_digest(902)
            ),
            "invalid network boundary binding",
        ),
        (
            "WORLDCOIN-G040",
            lambda evidence: evidence["native_receipt"]["checks"].__setitem__(
                "transaction_commit", False
            ),
            "transaction_commit did not pass",
        ),
    ],
)
def test_receipt_rejects_goal_specific_native_evidence_drift(
    tmp_path: Path,
    goal_id: str,
    mutation: Any,
    message: str,
) -> None:
    fixture = _signed_fixture(tmp_path)

    def replace(payload: dict[str, Any]) -> None:
        evidence = payload["evidence"]
        mutation(evidence)
        evidence["native_receipt_sha256"] = _native_digest(evidence["native_receipt"])

    _replace_goal_result(fixture, goal_id, replace)
    with pytest.raises(GateFirstReceiptError, match=message):
        verify_gate_first_receipt(
            policy=fixture.policy,
            run_id=fixture.run_id,
            context=fixture.context,
        )


def test_disabled_policy_and_cli_overrides_fail_closed(tmp_path: Path) -> None:
    operator_root = tmp_path / "operator"
    operator_root.mkdir(mode=0o700)
    context = _context(operator_root)
    policy_path = _write_policy(operator_root, _policy_payload(operator_root))
    policy = launcher.load_operator_policy(policy_path, context=context)
    with pytest.raises(GateFirstReceiptError, match="does not enable"):
        verify_gate_first_receipt(
            policy=policy,
            run_id="gate-first-synthetic-run-0001",
            context=context,
        )

    assert _build_parser().parse_args(["--run-id", "gate-first-synthetic-run-0001"]).run_id
    for arguments in (
        ["--receipt", "/tmp/receipt.json"],
        ["--run-id", "gate-first-synthetic-run-0001", "--allowed-signers", "/tmp/key"],
        ["--run-id", "gate-first-synthetic-run-0001", "--goal", "WORLDCOIN-G038"],
    ):
        with pytest.raises(SystemExit) as raised:
            _build_parser().parse_args(arguments)
        assert raised.value.code == 2


def test_direct_cli_loads_sibling_launcher_under_isolated_python(
    tmp_path: Path,
) -> None:
    script_path = Path(receipt_verifier.__file__).resolve()
    completed = subprocess.run(
        [
            "/usr/bin/python3",
            "-I",
            "-S",
            "-B",
            str(script_path),
            "--help",
        ],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        env={
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "PATH": "/usr/bin:/bin",
            "TZ": "UTC",
        },
        text=True,
    )

    assert completed.returncode == 0
    assert "--run-id" in completed.stdout
    assert completed.stderr == ""
