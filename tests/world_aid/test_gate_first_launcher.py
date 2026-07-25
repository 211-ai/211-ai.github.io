"""Offline tests for the repository-side Gate-first launcher reference."""

from __future__ import annotations

import copy
import errno
import hashlib
import json
import os
import shutil
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

import scripts.world_aid_gate_first_launcher as launcher
from scripts.world_aid_gate_first_launcher import (
    EXPECTED_CLEAN_ENVIRONMENT,
    ExternalSecurityContext,
    GateFirstLauncherError,
    _build_parser,
    load_json_strict,
    load_operator_policy,
    snapshot_regular_file_at,
    validate_authority_environment,
    verify_only,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPOSITORY_ROOT / "scripts/world_aid_gate_first_launcher.py"
ZERO_DIGEST = "sha256:" + ("0" * 64)


def _sha256(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def _write_bytes(path: Path, raw: bytes, *, mode: int = 0o400) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.write_bytes(raw)
    path.chmod(mode)
    return path


def _policy_payload(operator_root: Path, *, run_enabled: bool = False) -> dict[str, Any]:
    review_id = "review-20260724"
    runners: list[dict[str, str]] = []
    if run_enabled:
        runners = [
            {
                "goal_id": goal_id,
                "path": launcher.EXPECTED_RUNNERS[goal_id],
                "sha256": ZERO_DIGEST,
                "input_mode": "sealed-fd-json/v1",
                "output_mode": "stdout-json/v1",
            }
            for goal_id in launcher.EXPECTED_GOAL_IDS
        ]
    return {
        "schema": launcher.POLICY_SCHEMA,
        "mode": "verify-only",
        "installation": {
            "launcher_path": str(operator_root / "libexec/launcher"),
            "launcher_sha256": ZERO_DIGEST,
            "python_path": str(operator_root / "bin/python"),
            "python_sha256": ZERO_DIGEST,
            "python_version": ".".join(str(value) for value in sys.version_info[:3]),
            "ssh_keygen_path": str(operator_root / "bin/ssh-keygen"),
            "ssh_keygen_sha256": ZERO_DIGEST,
            "authority_uid": os.getuid(),
        },
        "repository": {"root": str(operator_root / "repository")},
        "gate": {
            "phase": "selection",
            "verifier_path": launcher.CANONICAL_GATE_VERIFIER,
            "verifier_sha256": ZERO_DIGEST,
            "approval_path": launcher.CANONICAL_SELECTION_APPROVAL,
            "profile_json_path": (
                "data/worldcoin_human_aid/agent_supervisor/regenerations/"
                f"{review_id}/launch_profiles/g038-g040.index.json"
            ),
            "profile_json_sha256": ZERO_DIGEST,
            "profile_duckdb_path": (
                "data/worldcoin_human_aid/agent_supervisor/regenerations/"
                f"{review_id}/launch_profiles/g038-g040.index.duckdb"
            ),
            "profile_duckdb_sha256": ZERO_DIGEST,
        },
        "trust": {
            "allowed_signers_path": str(operator_root / "etc/gate.allowed_signers"),
            "allowed_signers_sha256": ZERO_DIGEST,
        },
        "execution": {
            "run_selection_enabled": run_enabled,
            "expected_goal_ids": list(launcher.EXPECTED_GOAL_IDS),
            "runners": runners,
        },
        "receipts": {
            "root": str(operator_root / "var/runs"),
            "allowed_signers_path": str(operator_root / "etc/receipt.allowed_signers"),
            "allowed_signers_sha256": ZERO_DIGEST,
            "signer_identity": "launcher@example.invalid",
            "signer_fingerprint": "SHA256:" + ("A" * 43),
            "signature_namespace": "world-aid-gate-first-launch-v1",
        },
        "runtime": {
            "require_isolated_python": True,
            "require_no_site": True,
            "require_dont_write_bytecode": True,
            "clean_environment": dict(EXPECTED_CLEAN_ENVIRONMENT),
            "apparmor_profile": "world-aid-gate-first",
            "network_namespace": "world-aid-gate-first-offline",
            "gate_timeout_seconds": 10,
            "max_child_output_bytes": 65536,
        },
    }


def _write_policy(
    operator_root: Path,
    payload: dict[str, Any],
    *,
    name: str = "gate-first-policy.json",
) -> Path:
    policy_path = operator_root / "etc" / name
    return _write_bytes(
        policy_path,
        (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode(),
    )


def _context(operator_root: Path) -> ExternalSecurityContext:
    operator_root.chmod(0o700)
    return ExternalSecurityContext(
        trusted_root=operator_root,
        expected_owner_uid=os.getuid(),
    )


def _synthetic_digest(label: str) -> str:
    return f"sha256:{hashlib.sha256(label.encode()).hexdigest()}"


def _binding_approval(
    policy: launcher.OperatorPolicy,
) -> dict[str, Any]:
    reviewed_state: dict[str, Any] = {
        "restricted_bundle_index": {
            "path": policy.profile_json_path,
            "sha256": policy.profile_json_sha256,
        },
        "restricted_bundle_index_duckdb": {
            "path": policy.profile_duckdb_path,
            "sha256": policy.profile_duckdb_sha256,
        },
    }
    runner_digests = {
        launcher.RUNNER_REVIEWED_ARTIFACT_KEYS[runner.goal_id]: runner.sha256
        for runner in policy.runners
    }
    for key, path in launcher.EXECUTION_BOUND_ARTIFACT_PATHS.items():
        if key == "gate_launcher":
            digest = policy.launcher_sha256
        elif key == "gate_verifier":
            digest = policy.gate_verifier_sha256
        else:
            digest = runner_digests.get(key, _synthetic_digest(key))
        reviewed_state[key] = {"path": path, "sha256": digest}

    return {
        "schema_version": launcher.SELECTION_APPROVAL_SCHEMA,
        "gate_id": launcher.SELECTION_GATE_ID,
        "record_id": "gate-0b-selection-synthetic01",
        "scope": {"goal_ids": list(launcher.EXPECTED_GOAL_IDS)},
        "reviewed_state": reviewed_state,
        "execution_boundary": {
            "protocol_id": launcher.GATE_FIRST_PROTOCOL_ID,
            "execution_authority": launcher.GATE_FIRST_EXECUTION_AUTHORITY,
            "operation": launcher.SELECTION_OPERATION,
            "sealed_input_protocol": launcher.SEALED_INPUT_PROTOCOL,
            "result_protocol": launcher.RESULT_PROTOCOL,
            "installed_launcher_path": policy.launcher_path.as_posix(),
            "operator_policy_id": launcher.POLICY_SCHEMA,
            "operator_policy_sha256": policy.raw_sha256,
            "deployment_attestation_id": (
                "gate-first-deployment-synthetic-approval-001"
            ),
            "deployment_attestation_sha256": _synthetic_digest(
                "deployment attestation"
            ),
            "reviewed_artifacts": {
                key: reviewed_state[key]["sha256"]
                for key in launcher.EXECUTION_BOUND_ARTIFACT_PATHS
            },
        },
        "trust": {"allowed_signers_sha256": policy.allowed_signers_sha256},
    }


def _binding_fixture(
    tmp_path: Path,
    *,
    run_enabled: bool = False,
) -> tuple[launcher.OperatorPolicy, dict[str, Any]]:
    operator_root = tmp_path / "operator"
    operator_root.mkdir(mode=0o700)
    policy_path = _write_policy(
        operator_root,
        _policy_payload(operator_root, run_enabled=run_enabled),
    )
    policy = load_operator_policy(policy_path, context=_context(operator_root))
    return policy, _binding_approval(policy)


def _validate_binding(
    approval: dict[str, Any],
    policy: launcher.OperatorPolicy,
) -> None:
    launcher._validate_approval_binding(
        (json.dumps(approval, sort_keys=True) + "\n").encode(),
        policy,
    )


def test_cli_exposes_verify_only_without_path_command_or_goal_overrides() -> None:
    assert _build_parser().parse_args(["--verify-only"]).verify_only is True
    for arguments in (
        ["--run-selection"],
        ["--verify-only", "--policy", "/tmp/policy.json"],
        ["--verify-only", "--command", "touch /tmp/unsafe"],
        ["--verify-only", "--goal", "WORLDCOIN-G038"],
        ["--verify-only", "--repo-root", "/tmp/repo"],
    ):
        with pytest.raises(SystemExit) as raised:
            _build_parser().parse_args(arguments)
        assert raised.value.code == 2


def test_strict_json_and_environment_reject_injection() -> None:
    with pytest.raises(GateFirstLauncherError, match="duplicate JSON key"):
        load_json_strict(b'{"schema":"one","schema":"two"}', label="fixture")
    with pytest.raises(GateFirstLauncherError, match="non-finite"):
        load_json_strict(b'{"value":NaN}', label="fixture")

    validate_authority_environment(dict(EXPECTED_CLEAN_ENVIRONMENT))
    for injected in (
        {"PYTHONPATH": "/tmp/attacker"},
        {"LD_PRELOAD": "/tmp/attacker.so"},
        {"WORLD_AID_SECRET": "secret"},
    ):
        with pytest.raises(GateFirstLauncherError, match="environment"):
            validate_authority_environment(
                {**EXPECTED_CLEAN_ENVIRONMENT, **injected}
            )


def test_snapshot_is_sealed_and_refuses_symlink_components(tmp_path: Path) -> None:
    root = tmp_path / "repository"
    (root / "safe").mkdir(parents=True)
    target = root / "safe/input.json"
    target.write_text('{"safe":true}\n', encoding="utf-8")
    root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    try:
        with snapshot_regular_file_at(
            root_fd,
            "safe/input.json",
            maximum_bytes=1024,
        ) as snapshot:
            assert snapshot.read_bytes() == b'{"safe":true}\n'
            with pytest.raises(OSError) as raised:
                os.write(snapshot.fd, b"tamper")
            assert raised.value.errno in {errno.EPERM, errno.EBADF}

        (root / "linked").symlink_to(root / "safe", target_is_directory=True)
        with pytest.raises(GateFirstLauncherError, match="without following symlinks"):
            snapshot_regular_file_at(
                root_fd,
                "linked/input.json",
                maximum_bytes=1024,
            )
        target.unlink()
        target.symlink_to(root / "other.json")
        (root / "other.json").write_text("{}\n", encoding="utf-8")
        with pytest.raises(GateFirstLauncherError, match="without following symlinks"):
            snapshot_regular_file_at(
                root_fd,
                "safe/input.json",
                maximum_bytes=1024,
            )
    finally:
        os.close(root_fd)


def test_policy_is_strict_read_only_and_run_selection_needs_all_runners(
    tmp_path: Path,
) -> None:
    operator_root = tmp_path / "operator"
    operator_root.mkdir(mode=0o700)
    context = _context(operator_root)
    payload = _policy_payload(operator_root)
    policy_path = _write_policy(operator_root, payload)

    policy = load_operator_policy(policy_path, context=context)
    assert policy.run_selection_enabled is False
    assert policy.runners == ()

    policy_path.chmod(0o600)
    with pytest.raises(GateFirstLauncherError, match="write permission"):
        load_operator_policy(policy_path, context=context)

    policy_path.unlink()
    incomplete = _policy_payload(operator_root, run_enabled=True)
    incomplete["execution"]["runners"].pop()
    policy_path = _write_policy(operator_root, incomplete)
    with pytest.raises(GateFirstLauncherError, match="all three dedicated runners"):
        load_operator_policy(policy_path, context=context)

    policy_path.unlink()
    unexpected = _policy_payload(operator_root)
    unexpected["caller_command"] = "python attacker.py"
    policy_path = _write_policy(operator_root, unexpected)
    with pytest.raises(GateFirstLauncherError, match="unexpected"):
        load_operator_policy(policy_path, context=context)

    policy_path.unlink()
    overlapping = _policy_payload(operator_root)
    overlapping["receipts"]["root"] = str(
        Path(overlapping["repository"]["root"]) / "agent-controlled-runs"
    )
    policy_path = _write_policy(operator_root, overlapping)
    with pytest.raises(GateFirstLauncherError, match="outside repository authority"):
        load_operator_policy(policy_path, context=context)


def test_selection_v2_execution_boundary_binds_loaded_policy(
    tmp_path: Path,
) -> None:
    policy, approval = _binding_fixture(tmp_path)
    _validate_binding(approval, policy)


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("protocol_id", "world-aid-gate-first-launcher/v999"),
        ("execution_authority", "agent-supervisor/v1"),
        ("operation", "run-implementation/v1"),
        ("sealed_input_protocol", "repository-path-json/v1"),
        ("result_protocol", "tracked-fixture-json/v1"),
        ("installed_launcher_path", "/tmp/repository-launcher"),
        ("operator_policy_id", "world-aid-operator-policy/unreviewed"),
    ],
)
def test_selection_v2_execution_boundary_rejects_wrong_literals(
    tmp_path: Path,
    field: str,
    replacement: str,
) -> None:
    policy, approval = _binding_fixture(tmp_path)
    approval["execution_boundary"][field] = replacement
    with pytest.raises(
        GateFirstLauncherError,
        match=f"execution boundary {field} differs",
    ):
        _validate_binding(approval, policy)


@pytest.mark.parametrize("mutation", ["missing", "extra"])
def test_selection_v2_execution_boundary_rejects_key_drift(
    tmp_path: Path,
    mutation: str,
) -> None:
    policy, approval = _binding_fixture(tmp_path)
    if mutation == "missing":
        approval["execution_boundary"].pop("protocol_id")
    else:
        approval["execution_boundary"]["caller_command"] = "python attacker.py"
    with pytest.raises(GateFirstLauncherError, match="execution_boundary keys differ"):
        _validate_binding(approval, policy)


@pytest.mark.parametrize(
    ("field", "replacement", "message"),
    [
        (
            "operator_policy_sha256",
            ZERO_DIGEST,
            "policy digest differs from the loaded operator policy",
        ),
        (
            "deployment_attestation_id",
            "gate-first-deployment-INVALID-uppercase-0001",
            "deployment attestation id is invalid",
        ),
        (
            "deployment_attestation_sha256",
            "sha256:" + ("G" * 64),
            "must be a lowercase sha256 digest",
        ),
    ],
)
def test_selection_v2_execution_boundary_rejects_unbound_policy_or_attestation(
    tmp_path: Path,
    field: str,
    replacement: str,
    message: str,
) -> None:
    policy, approval = _binding_fixture(tmp_path)
    approval["execution_boundary"][field] = replacement
    with pytest.raises(GateFirstLauncherError, match=message):
        _validate_binding(approval, policy)


def test_selection_v2_execution_boundary_requires_exact_reviewed_artifacts(
    tmp_path: Path,
) -> None:
    policy, source = _binding_fixture(tmp_path)
    reviewed_key = "gate_launcher_protocol"

    missing = copy.deepcopy(source)
    missing["execution_boundary"]["reviewed_artifacts"].pop(reviewed_key)
    with pytest.raises(GateFirstLauncherError, match="reviewed_artifacts keys differ"):
        _validate_binding(missing, policy)

    extra = copy.deepcopy(source)
    extra["execution_boundary"]["reviewed_artifacts"]["unreviewed_runner"] = ZERO_DIGEST
    with pytest.raises(GateFirstLauncherError, match="reviewed_artifacts keys differ"):
        _validate_binding(extra, policy)

    malformed = copy.deepcopy(source)
    malformed["execution_boundary"]["reviewed_artifacts"][reviewed_key] = (
        "sha256:" + ("G" * 64)
    )
    with pytest.raises(
        GateFirstLauncherError,
        match="must be a lowercase sha256 digest",
    ):
        _validate_binding(malformed, policy)

    mismatched = copy.deepcopy(source)
    mismatched["execution_boundary"]["reviewed_artifacts"][reviewed_key] = ZERO_DIGEST
    with pytest.raises(
        GateFirstLauncherError,
        match="does not bind its reviewed-state digest",
    ):
        _validate_binding(mismatched, policy)


@pytest.mark.parametrize("key", ["gate_launcher", "gate_verifier"])
def test_selection_v2_execution_boundary_binds_launcher_and_verifier_to_policy(
    tmp_path: Path,
    key: str,
) -> None:
    policy, approval = _binding_fixture(tmp_path)
    replacement = _synthetic_digest(f"unreviewed {key}")
    approval["reviewed_state"][key]["sha256"] = replacement
    approval["execution_boundary"]["reviewed_artifacts"][key] = replacement
    with pytest.raises(
        GateFirstLauncherError,
        match=f"{key} digest differs from the operator policy",
    ):
        _validate_binding(approval, policy)


@pytest.mark.parametrize(
    "key",
    [
        "siwe_bootstrap_runner",
        "zkp_bootstrap_runner",
        "duckdb_bootstrap_runner",
    ],
)
def test_enabled_selection_binds_each_runner_digest_to_policy(
    tmp_path: Path,
    key: str,
) -> None:
    policy, approval = _binding_fixture(tmp_path, run_enabled=True)
    _validate_binding(approval, policy)

    replacement = _synthetic_digest(f"unreviewed {key}")
    approval["reviewed_state"][key]["sha256"] = replacement
    approval["execution_boundary"]["reviewed_artifacts"][key] = replacement
    with pytest.raises(
        GateFirstLauncherError,
        match="operator policy runner digest .* differs from the reviewed artifact",
    ):
        _validate_binding(approval, policy)


def test_enabled_selection_compares_runner_path_directly_with_reviewed_state(
    tmp_path: Path,
) -> None:
    policy, approval = _binding_fixture(tmp_path, run_enabled=True)
    changed_runner = replace(
        policy.runners[0],
        path="scripts/unreviewed_runner.py",
    )
    changed_policy = replace(
        policy,
        runners=(changed_runner, *policy.runners[1:]),
    )
    with pytest.raises(
        GateFirstLauncherError,
        match="operator policy runner path .* differs from the reviewed artifact",
    ):
        _validate_binding(approval, changed_policy)


def test_selection_v2_reviewed_artifact_records_are_exact_and_canonical(
    tmp_path: Path,
) -> None:
    policy, source = _binding_fixture(tmp_path)

    extra = copy.deepcopy(source)
    extra["reviewed_state"]["selection_profile_builder"]["mutable"] = True
    with pytest.raises(GateFirstLauncherError, match="keys differ"):
        _validate_binding(extra, policy)

    wrong_path = copy.deepcopy(source)
    wrong_path["reviewed_state"]["siwe_bootstrap_runner"]["path"] = (
        "scripts/unreviewed_runner.py"
    )
    with pytest.raises(GateFirstLauncherError, match="wrong canonical path"):
        _validate_binding(wrong_path, policy)


def test_child_output_is_bounded_while_it_is_collected() -> None:
    process = subprocess.Popen(
        [
            sys.executable,
            "-c",
            (
                "import sys; "
                "sys.stdout.buffer.write(b'x' * 768); "
                "sys.stderr.buffer.write(b'y' * 768); "
                "sys.stdout.flush(); sys.stderr.flush()"
            ),
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    with pytest.raises(GateFirstLauncherError, match="output bound"):
        launcher._communicate_bounded(
            process,
            timeout_seconds=5,
            maximum_bytes=1024,
            label="synthetic bounded child",
        )
    assert process.poll() is not None


def test_in_repository_copy_cannot_claim_installed_authority(tmp_path: Path) -> None:
    operator_root = tmp_path / "operator"
    operator_root.mkdir(mode=0o700)
    context = _context(operator_root)
    policy_path = _write_policy(operator_root, _policy_payload(operator_root))
    policy = load_operator_policy(policy_path, context=context)

    with pytest.raises(
        GateFirstLauncherError,
        match="in-repository copy is never an authority",
    ):
        launcher._verify_external_installation(
            policy=policy,
            actual_launcher_path=SCRIPT_PATH,
            context=context,
        )

    production_shaped = replace(
        policy,
        launcher_path=launcher.FIXED_INSTALLED_LAUNCHER_PATH,
    )
    with pytest.raises(GateFirstLauncherError, match="production ssh-keygen path"):
        launcher._assert_policy_authority_separation(
            production_shaped,
            policy_path=launcher.FIXED_OPERATOR_POLICY_PATH,
            context=launcher.ROOT_OPERATOR_CONTEXT,
        )


def test_verify_only_executes_captured_verifier_and_never_authorizes_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    operator_root = tmp_path / "operator"
    operator_root.mkdir(mode=0o700)
    context = _context(operator_root)
    repo_root = operator_root / "repository"
    repo_root.mkdir(mode=0o700)

    installed_launcher = _write_bytes(
        operator_root / "libexec/launcher",
        SCRIPT_PATH.read_bytes(),
        mode=0o500,
    )
    # A copied interpreter is sufficient for this isolated synthetic contract
    # and keeps every policy-controlled executable inside the test trust root.
    copied_python = operator_root / "bin/python"
    copied_python.parent.mkdir(mode=0o700)
    shutil.copy2(Path(sys.executable), copied_python)
    copied_python.chmod(0o500)
    copied_ssh_keygen = operator_root / "bin/ssh-keygen"
    shutil.copy2(Path("/usr/bin/ssh-keygen"), copied_ssh_keygen)
    copied_ssh_keygen.chmod(0o500)
    trust_store = _write_bytes(
        operator_root / "etc/gate.allowed_signers",
        b"synthetic@example.invalid ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFixtureOnly\n",
    )

    verifier_source = b"""\
def verify_approval(*, repo_root, phase, approval_path, allowed_signers_path,
                    now=None, expected_approval_bytes=None):
    assert phase == "selection"
    assert (repo_root / approval_path).read_bytes() == expected_approval_bytes
    return {
        "status": "verified",
        "phase": "selection",
        "gate_id": "gate-0b-selection",
        "record_id": "gate-0b-selection-synthetic01",
        "verified_approval_sha256": "sha256:" + ("1" * 64),
        "expires_at": "2099-01-01T00:00:00Z",
        "reviewed_root_commit": "2" * 40,
        "artifact_count": 2,
        "signature_count": 9,
        "offline": True,
        "live_actions_authorized": False,
    }
"""
    verifier_path = repo_root / launcher.CANONICAL_GATE_VERIFIER
    _write_bytes(verifier_path, verifier_source, mode=0o600)

    review_id = "review-20260724"
    profile_dir = (
        repo_root
        / "data/worldcoin_human_aid/agent_supervisor/regenerations"
        / review_id
        / "launch_profiles"
    )
    profile_json = _write_bytes(
        profile_dir / "g038-g040.index.json",
        b'{"tasks":[]}\n',
        mode=0o600,
    )
    profile_duckdb = _write_bytes(
        profile_dir / "g038-g040.index.duckdb",
        b"synthetic-duckdb-profile",
        mode=0o600,
    )
    payload = _policy_payload(operator_root)
    payload["installation"].update(
        {
            "launcher_sha256": _sha256(installed_launcher),
            "python_sha256": _sha256(copied_python),
            "ssh_keygen_sha256": _sha256(copied_ssh_keygen),
        }
    )
    payload["trust"]["allowed_signers_sha256"] = _sha256(trust_store)
    payload["gate"].update(
        {
            "verifier_sha256": _sha256(verifier_path),
            "profile_json_sha256": _sha256(profile_json),
            "profile_duckdb_sha256": _sha256(profile_duckdb),
        }
    )
    policy_path = _write_policy(operator_root, payload)
    policy = load_operator_policy(policy_path, context=context)
    approval_payload = _binding_approval(policy)
    approval_path = repo_root / launcher.CANONICAL_SELECTION_APPROVAL
    _write_bytes(
        approval_path,
        (json.dumps(approval_payload, sort_keys=True) + "\n").encode(),
        mode=0o600,
    )

    monkeypatch.setattr(sys, "executable", str(copied_python))
    result = verify_only(
        policy_path=policy_path,
        actual_launcher_path=installed_launcher,
        context=context,
        enforce_authority_runtime=False,
    )

    assert result["schema"] == launcher.VERIFY_RESULT_SCHEMA
    assert result["status"] == "verified"
    assert result["expected_goal_ids"] == list(launcher.EXPECTED_GOAL_IDS)
    assert result["run_selection_authorized"] is False
    assert result["live_actions_authorized"] is False
    assert result["offline"] is True
