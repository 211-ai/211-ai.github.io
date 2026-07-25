from __future__ import annotations

import base64
import copy
import hashlib
import json
import os
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

import scripts.verify_world_aid_gate_0b_transition as transition
from scripts.verify_world_aid_gate_0b_transition import (
    CANONICAL_RECORD_PATH,
    REQUIRED_SIGNER_ROLES,
    SIGNATURE_NAMESPACE,
    TransitionVerificationError,
    canonical_json_bytes,
    verify_transition,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 7, 24, 12, 0, 0, tzinfo=UTC)
ISSUED_AT = "2026-07-24T11:00:00Z"
EXPIRES_AT = "2026-07-25T11:00:00Z"
SOURCE_ROOT = (
    "data/worldcoin_human_aid/agent_supervisor/regenerations/"
    "synthetic-blocked-review"
)
TARGET_ROOT = (
    "data/worldcoin_human_aid/agent_supervisor/regenerations/"
    "synthetic-reopened-review"
)


@dataclass
class TransitionEnvironment:
    root: Path
    record_path: Path
    allowed_signers: Path
    record: dict[str, Any]
    private_keys: dict[str, Path]


def _run(*args: str, cwd: Path) -> str:
    result = subprocess.run(
        list(args),
        cwd=cwd,
        check=True,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_ASKPASS": "",
        },
    )
    return result.stdout.strip()


def _git_init(root: Path) -> None:
    _run("git", "init", "-q", cwd=root)
    _run("git", "config", "user.email", "transition-tests@example.invalid", cwd=root)
    _run("git", "config", "user.name", "Transition Tests", cwd=root)


def _commit_all(root: Path, message: str) -> str:
    _run("git", "add", "-A", cwd=root)
    _run("git", "commit", "-q", "-m", message, cwd=root)
    return _run("git", "rev-parse", "HEAD", cwd=root)


def _write(path: Path, content: str | bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding="utf-8")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    _write(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _write_record(path: Path, payload: dict[str, Any]) -> None:
    _write(path, canonical_json_bytes(payload))


def _digest_bytes(raw: bytes) -> str:
    return f"sha256:{hashlib.sha256(raw).hexdigest()}"


def _digest(path: Path) -> str:
    return _digest_bytes(path.read_bytes())


def _artifact(
    root: Path,
    relative: str,
    *,
    must_not_reuse: bool = False,
) -> dict[str, str]:
    artifact = {"path": relative, "sha256": _digest(root / relative)}
    if must_not_reuse:
        artifact["reuse_policy"] = "must_not_reuse"
    return artifact


def _heap(status: str) -> str:
    return f"""\
# Synthetic World aid objective heap

## WORLDCOIN-G001 Unrelated source goal

- Status: active

## WORLDCOIN-G038 SIWE bootstrap

- Status: {status}

## WORLDCOIN-G039 ZKP bootstrap

- Status: {status}

## WORLDCOIN-G040 DuckDB bootstrap

- Status: {status}
"""


def _taskboard() -> str:
    blocks = []
    for index, goal_id in enumerate(transition.TRANSITION_GOALS, start=1):
        blocks.append(
            f"""\
## WORLDCOIN-AUTO-{index:03d} Synthetic blocked task

- Status: blocked
- Goal id: {goal_id}
"""
        )
    return "# Synthetic blocked taskboard\n\n" + "\n".join(blocks)


def _bundle_index() -> dict[str, Any]:
    return {
        "schema": "synthetic-bundle-index/v1",
        "bundles": {
            f"world-aid/{goal_id.lower()}": {
                "bundle_key": f"world-aid/{goal_id.lower()}",
                "tasks": [
                    {
                        "task_id": f"TASK-{goal_id[-3:]}",
                        "goal_id": goal_id,
                        "status": "blocked",
                        "canonical_task_cid": f"cid-{goal_id.lower()}",
                    }
                ],
            }
            for goal_id in transition.TRANSITION_GOALS
        },
    }


def _dependency_dag() -> dict[str, Any]:
    return {
        "schema": "synthetic-objective-graph/v1",
        "goals": [
            {"goal_id": "WORLDCOIN-G001", "status": "active"},
            *[
                {"goal_id": goal_id, "status": "blocked"}
                for goal_id in transition.TRANSITION_GOALS
            ],
        ],
        "graph": {"edges": []},
    }


def _fingerprint(public_key_line: str) -> str:
    key_blob = base64.b64decode(public_key_line.split()[1], validate=True)
    encoded = base64.b64encode(hashlib.sha256(key_blob).digest()).decode(
        "ascii"
    )
    return f"SHA256:{encoded.rstrip('=')}"


def _generate_signers(
    root: Path,
) -> tuple[Path, dict[str, Path], list[dict[str, str]]]:
    key_root = root / "transition-keys"
    key_root.mkdir(parents=True)
    private_keys: dict[str, Path] = {}
    approvals: list[dict[str, str]] = []
    trust_lines: list[str] = []
    for role in sorted(REQUIRED_SIGNER_ROLES):
        identity = f"{role}@transition.test"
        private_key = key_root / role
        _run(
            "ssh-keygen",
            "-q",
            "-t",
            "ed25519",
            "-N",
            "",
            "-C",
            identity,
            "-f",
            str(private_key),
            cwd=root,
        )
        public_line = private_key.with_suffix(".pub").read_text(
            encoding="utf-8"
        ).strip()
        key_type, key_blob, *_ = public_line.split()
        trust_lines.append(f"{identity} {key_type} {key_blob}\n")
        approvals.append(
            {
                "role": role,
                "identity": identity,
                "key_fingerprint": _fingerprint(public_line),
                "signature_file": f"signatures/{role}.sshsig",
            }
        )
        private_keys[role] = private_key
    allowed_signers = key_root / "allowed_signers"
    allowed_signers.write_text("".join(trust_lines), encoding="utf-8")
    allowed_signers.chmod(0o444)
    return allowed_signers, private_keys, approvals


def _sign_record(environment: TransitionEnvironment) -> None:
    signature_root = environment.record_path.parent / "signatures"
    signature_root.mkdir(parents=True, exist_ok=True)
    for role in sorted(REQUIRED_SIGNER_ROLES):
        generated = Path(f"{environment.record_path}.sig")
        generated.unlink(missing_ok=True)
        _run(
            "ssh-keygen",
            "-Y",
            "sign",
            "-f",
            str(environment.private_keys[role]),
            "-n",
            SIGNATURE_NAMESPACE,
            str(environment.record_path),
            cwd=environment.root,
        )
        generated.replace(signature_root / f"{role}.sshsig")


def _build_environment(tmp_path: Path) -> TransitionEnvironment:
    root = tmp_path / "repo"
    root.mkdir()
    _git_init(root)

    target_heap_path = transition.CANONICAL_TARGET_HEAP_PATH
    _write(root / target_heap_path, _heap("blocked"))
    _write(root / f"{SOURCE_ROOT}/WORLDCOIN_HUMAN_AID_TODO.md", _taskboard())
    _write_json(
        root / f"{SOURCE_ROOT}/objective_bundles/todo_vector_index.json",
        {"schema": "synthetic-task-index/v1", "tasks": ["unique-task-index"]},
    )
    _write_json(
        root / f"{SOURCE_ROOT}/objective_bundles/index.json",
        _bundle_index(),
    )
    _write_json(
        root / f"{SOURCE_ROOT}/objective_graph.json",
        _dependency_dag(),
    )
    _write_json(
        root / f"{SOURCE_ROOT}/preflight-receipt.json",
        {
            "schema": "world_aid.generated_board_preflight_receipt@1",
            "status": "passed",
            "passed": True,
            "generated_root": SOURCE_ROOT,
            "marker": "unique-preflight",
        },
    )

    _write(
        root / transition.CANONICAL_LAUNCHER_PROTOCOL_PATH,
        "# Synthetic externally administered launcher protocol\n",
    )
    _write(
        root / transition.CANONICAL_LAUNCHER_PATH,
        "#!/usr/bin/env python3\n# synthetic external launcher\n",
    )
    _write(
        root / transition.CANONICAL_GATE_VERIFIER_PATH,
        "#!/usr/bin/env python3\n# synthetic pinned Gate verifier\n",
    )

    source_heap_digest = _digest(root / target_heap_path)
    source_commit = _commit_all(root, "Create blocked Gate 0B source state")
    _write(root / target_heap_path, _heap("reopened"))
    target_heap_digest = _digest(root / target_heap_path)
    target_commit = _commit_all(root, "Reopen exact Gate 0B transition goals")

    allowed_signers, private_keys, approvals = _generate_signers(root)
    source_artifacts = {
        artifact_id: _artifact(
            root,
            f"{SOURCE_ROOT}/{suffix}",
            must_not_reuse=True,
        )
        for artifact_id, suffix in transition.GENERATED_ARTIFACT_PATHS.items()
    }
    source_heap = {
        "path": target_heap_path,
        "sha256": source_heap_digest,
    }
    target_heap = {
        "path": target_heap_path,
        "sha256": target_heap_digest,
    }
    protocol = _artifact(
        root,
        transition.CANONICAL_LAUNCHER_PROTOCOL_PATH,
    )
    launcher = _artifact(root, transition.CANONICAL_LAUNCHER_PATH)
    gate_verifier = _artifact(
        root,
        transition.CANONICAL_GATE_VERIFIER_PATH,
    )
    trust_policy_digest = _digest_bytes(b"synthetic external operator policy")
    independent_identity = next(
        item["identity"]
        for item in approvals
        if item["role"] == "independent-operator"
    )
    attestation_id = "gate-first-deployment-synthetic-001"
    attestation = {
        "schema": transition.DEPLOYMENT_ATTESTATION_SCHEMA,
        "attestation_id": attestation_id,
        "issued_at": ISSUED_AT,
        "independently_administered": True,
        "administrator_identity": independent_identity,
        "deployed": True,
        "conformant": True,
        "protocol_id": transition.LAUNCHER_PROTOCOL_ID,
        "protocol_sha256": protocol["sha256"],
        "launcher_sha256": launcher["sha256"],
        "gate_verifier_id": transition.GATE_VERIFIER_ID,
        "gate_verifier_sha256": gate_verifier["sha256"],
        "trust_policy_id": transition.TRUST_POLICY_ID,
        "trust_policy_sha256": trust_policy_digest,
        "target_commit": target_commit,
        "target_heap_id": target_heap["sha256"],
        "runtime_authorized": False,
    }
    _write_json(
        root / transition.CANONICAL_DEPLOYMENT_ATTESTATION_PATH,
        attestation,
    )
    deployment_attestation = _artifact(
        root,
        transition.CANONICAL_DEPLOYMENT_ATTESTATION_PATH,
    )

    record = {
        "schema_version": transition.SCHEMA_VERSION,
        "gate_id": transition.GATE_ID,
        "record_id": "gate-0b-transition-synthetic-001",
        "decision": "approved",
        "transition_authorized": True,
        "runtime_authorized": False,
        "issued_at": ISSUED_AT,
        "expires_at": EXPIRES_AT,
        "source_state": {
            "root_commit": source_commit,
            "heap_id": source_heap["sha256"],
            "objective_heap": source_heap,
            "board_contract": transition.SOURCE_BOARD_CONTRACT,
            "generated_root": SOURCE_ROOT,
            "generated_artifacts": source_artifacts,
        },
        "target_state": {
            "root_commit": target_commit,
            "heap_id": target_heap["sha256"],
            "objective_heap": target_heap,
            "board_contract": transition.TARGET_BOARD_CONTRACT,
        },
        "transitions": [
            {
                "goal_id": goal_id,
                "from_status": "blocked",
                "to_status": "reopened",
            }
            for goal_id in transition.TRANSITION_GOALS
        ],
        "controls": {
            "external_launcher": {
                "protocol_id": transition.LAUNCHER_PROTOCOL_ID,
                "protocol": protocol,
                "launcher": launcher,
                "deployment_attestation_id": attestation_id,
                "deployment_attestation": deployment_attestation,
            },
            "gate_verifier": {
                "verifier_id": transition.GATE_VERIFIER_ID,
                "artifact": gate_verifier,
            },
            "trust_policy": {
                "policy_id": transition.TRUST_POLICY_ID,
                "deployment_path": transition.TRUST_POLICY_DEPLOYMENT_PATH,
                "sha256": trust_policy_digest,
            },
        },
        "regeneration": {
            "required": True,
            "mode": "fresh-post-transition",
            "source_generated_root": SOURCE_ROOT,
            "target_generated_root": TARGET_ROOT,
            "must_not_reuse_artifact_ids": sorted(
                transition.GENERATED_ARTIFACT_PATHS
            ),
            "must_not_reuse_sha256": sorted(
                artifact["sha256"] for artifact in source_artifacts.values()
            ),
        },
        "trust": {
            "policy_id": transition.SIGNER_POLICY_ID,
            "signature_namespace": SIGNATURE_NAMESPACE,
            "allowed_signers_sha256": _digest(allowed_signers),
        },
        "approvals": approvals,
    }
    record_path = root / CANONICAL_RECORD_PATH
    _write_record(record_path, record)
    environment = TransitionEnvironment(
        root=root,
        record_path=record_path,
        allowed_signers=allowed_signers,
        record=record,
        private_keys=private_keys,
    )
    _sign_record(environment)
    return environment


@pytest.fixture()
def environment(tmp_path: Path) -> TransitionEnvironment:
    return _build_environment(tmp_path)


def _verify(environment: TransitionEnvironment) -> dict[str, Any]:
    return verify_transition(
        repo_root=environment.root,
        record_path=environment.record_path,
        allowed_signers_path=environment.allowed_signers,
        now=NOW,
    )


def _mutate_record(
    environment: TransitionEnvironment,
    mutation: Callable[[dict[str, Any]], None],
) -> None:
    record = copy.deepcopy(environment.record)
    mutation(record)
    _write_record(environment.record_path, record)


def test_transition_contract_verifies_exact_signed_transition(
    environment: TransitionEnvironment,
) -> None:
    summary = _verify(environment)

    assert summary["status"] == "verified"
    assert summary["transition_goal_ids"] == list(transition.TRANSITION_GOALS)
    assert summary["signature_count"] == len(REQUIRED_SIGNER_ROLES)
    assert summary["runtime_authorized"] is False
    assert summary["fresh_regeneration_required"] is True


def test_schema_is_strict_and_template_is_plainly_pending_without_approvals() -> None:
    schema = json.loads(
        (
            REPO_ROOT
            / "docs/schemas/world_aid/gate-0b-transition.schema.json"
        ).read_text(encoding="utf-8")
    )
    template = json.loads(
        (
            REPO_ROOT
            / "docs/governance/templates/gate-0b-transition.template.json"
        ).read_text(encoding="utf-8")
    )

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["additionalProperties"] is False
    assert schema["properties"]["decision"]["const"] == "approved"
    assert schema["properties"]["runtime_authorized"]["const"] is False
    assert schema["properties"]["approvals"]["minItems"] == 4
    assert template["decision"] == "pending"
    assert template["transition_authorized"] is False
    assert template["runtime_authorized"] is False
    assert template["approvals"] == []
    assert "REPLACE-WITH" in template["record_id"]


def test_deployment_attestation_schema_is_strict_and_template_is_nonconformant() -> None:
    schema = json.loads(
        (
            REPO_ROOT
            / "docs/schemas/world_aid/"
            "gate-first-deployment-conformance-attestation.schema.json"
        ).read_text(encoding="utf-8")
    )
    template = json.loads(
        (
            REPO_ROOT
            / "docs/governance/templates/"
            "gate-first-deployment-conformance-attestation.template.json"
        ).read_text(encoding="utf-8")
    )

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"])
    assert schema["properties"]["independently_administered"]["const"] is True
    assert schema["properties"]["deployed"]["const"] is True
    assert schema["properties"]["conformant"]["const"] is True
    assert schema["properties"]["runtime_authorized"]["const"] is False
    assert template["independently_administered"] is False
    assert template["deployed"] is False
    assert template["conformant"] is False
    assert template["runtime_authorized"] is False
    assert "REPLACE-WITH" in template["attestation_id"]


@pytest.mark.parametrize("mutation", ["missing", "extra", "active"])
def test_transition_rejects_missing_extra_or_active_goal_records(
    environment: TransitionEnvironment,
    mutation: str,
) -> None:
    def mutate(record: dict[str, Any]) -> None:
        if mutation == "missing":
            record["transitions"].pop()
        elif mutation == "extra":
            record["transitions"].append(
                {
                    "goal_id": "WORLDCOIN-G041",
                    "from_status": "blocked",
                    "to_status": "reopened",
                }
            )
        else:
            record["transitions"][0]["to_status"] = "active"

    _mutate_record(environment, mutate)

    with pytest.raises(TransitionVerificationError, match="exactly sorted"):
        _verify(environment)


def test_transition_rejects_active_target_heap(
    environment: TransitionEnvironment,
) -> None:
    target_path = (
        environment.root
        / environment.record["target_state"]["objective_heap"]["path"]
    )
    target_path.write_text(
        target_path.read_text(encoding="utf-8").replace(
            "- Status: reopened",
            "- Status: active",
            1,
        ),
        encoding="utf-8",
    )
    _run(
        "git",
        "add",
        transition.CANONICAL_TARGET_HEAP_PATH,
        cwd=environment.root,
    )
    _run(
        "git",
        "commit",
        "-q",
        "-m",
        "Attempt an active target",
        cwd=environment.root,
    )
    target_commit = _run("git", "rev-parse", "HEAD", cwd=environment.root)

    def mutate(record: dict[str, Any]) -> None:
        digest = _digest(target_path)
        record["target_state"]["root_commit"] = target_commit
        record["target_state"]["objective_heap"]["sha256"] = digest
        record["target_state"]["heap_id"] = digest

    _mutate_record(environment, mutate)

    with pytest.raises(
        TransitionVerificationError,
        match="target heap WORLDCOIN-G038 status must be exactly reopened",
    ):
        _verify(environment)


def test_transition_never_authorizes_runtime(
    environment: TransitionEnvironment,
) -> None:
    _mutate_record(
        environment,
        lambda record: record.__setitem__("runtime_authorized", True),
    )

    with pytest.raises(
        TransitionVerificationError,
        match="runtime_authorized must be False",
    ):
        _verify(environment)


def test_transition_rejects_reused_generated_root(
    environment: TransitionEnvironment,
) -> None:
    _mutate_record(
        environment,
        lambda record: record["regeneration"].__setitem__(
            "target_generated_root",
            SOURCE_ROOT,
        ),
    )

    with pytest.raises(TransitionVerificationError, match="may not reuse"):
        _verify(environment)


def test_transition_rejects_reused_heap_digest(
    environment: TransitionEnvironment,
) -> None:
    _mutate_record(
        environment,
        lambda record: record["target_state"].__setitem__(
            "heap_id",
            record["source_state"]["heap_id"],
        ),
    )

    with pytest.raises(TransitionVerificationError, match="target heap ID"):
        _verify(environment)


@pytest.mark.parametrize("state", ["source", "target"])
def test_transition_rejects_nonexistent_commits(
    environment: TransitionEnvironment,
    state: str,
) -> None:
    _mutate_record(
        environment,
        lambda record: record[f"{state}_state"].__setitem__(
            "root_commit",
            "f" * 40,
        ),
    )

    with pytest.raises(
        TransitionVerificationError,
        match="trusted Git operation rejected",
    ):
        _verify(environment)


def test_transition_rejects_unrelated_source_and_target_commits(
    environment: TransitionEnvironment,
) -> None:
    tree = _run("git", "rev-parse", "HEAD^{tree}", cwd=environment.root)
    unrelated = _run(
        "git",
        "commit-tree",
        tree,
        "-m",
        "unrelated transition target",
        cwd=environment.root,
    )
    _mutate_record(
        environment,
        lambda record: record["target_state"].__setitem__(
            "root_commit",
            unrelated,
        ),
    )

    with pytest.raises(TransitionVerificationError, match="not an ancestor"):
        _verify(environment)


def test_transition_rejects_stale_target_commit(
    environment: TransitionEnvironment,
) -> None:
    _run(
        "git",
        "commit",
        "--allow-empty",
        "-q",
        "-m",
        "Advance current HEAD",
        cwd=environment.root,
    )

    with pytest.raises(
        TransitionVerificationError,
        match="target commit must equal the exact current HEAD",
    ):
        _verify(environment)


@pytest.mark.parametrize("state", ["source", "target"])
def test_transition_rejects_committed_heap_digest_content_mismatch(
    environment: TransitionEnvironment,
    state: str,
) -> None:
    mismatched = "sha256:" + ("a" if state == "source" else "b") * 64

    def mutate(record: dict[str, Any]) -> None:
        record[f"{state}_state"]["heap_id"] = mismatched
        record[f"{state}_state"]["objective_heap"]["sha256"] = mismatched

    _mutate_record(environment, mutate)

    with pytest.raises(
        TransitionVerificationError,
        match=rf"{state} committed objective heap digest/content mismatch",
    ):
        _verify(environment)


def test_transition_heap_binding_uses_committed_bytes_not_dirty_worktree(
    environment: TransitionEnvironment,
) -> None:
    heap_path = (
        environment.root
        / environment.record["target_state"]["objective_heap"]["path"]
    )
    heap_path.write_text("# uncommitted attacker replacement\n", encoding="utf-8")

    assert _verify(environment)["status"] == "verified"


def test_transition_rejects_artifact_path_escape(
    environment: TransitionEnvironment,
) -> None:
    _mutate_record(
        environment,
        lambda record: record["source_state"]["generated_artifacts"][
            "taskboard"
        ].__setitem__("path", "../outside"),
    )

    with pytest.raises(TransitionVerificationError, match="escapes|normalized"):
        _verify(environment)


@pytest.mark.parametrize("duplicate", ["role", "key"])
def test_transition_requires_distinct_roles_and_signing_keys(
    environment: TransitionEnvironment,
    duplicate: str,
) -> None:
    def mutate(record: dict[str, Any]) -> None:
        if duplicate == "role":
            record["approvals"][-1]["role"] = record["approvals"][0]["role"]
        else:
            record["approvals"][-1]["key_fingerprint"] = record["approvals"][0][
                "key_fingerprint"
            ]

    _mutate_record(environment, mutate)

    with pytest.raises(
        TransitionVerificationError,
        match="duplicated|approval roles",
    ):
        _verify(environment)


def test_transition_rejects_bound_artifact_digest_drift(
    environment: TransitionEnvironment,
) -> None:
    taskboard_path = (
        environment.root
        / environment.record["source_state"]["generated_artifacts"][
            "taskboard"
        ]["path"]
    )
    taskboard_path.write_text(
        taskboard_path.read_text(encoding="utf-8") + "\ndrift\n",
        encoding="utf-8",
    )

    with pytest.raises(TransitionVerificationError, match="digest drift"):
        _verify(environment)


def test_transition_rejects_malformed_detached_signature(
    environment: TransitionEnvironment,
) -> None:
    role = sorted(REQUIRED_SIGNER_ROLES)[0]
    signature = environment.record_path.parent / f"signatures/{role}.sshsig"
    signature.write_bytes(b"not an OpenSSH signature\n")

    with pytest.raises(
        TransitionVerificationError,
        match="malformed or rejected",
    ):
        _verify(environment)


def test_transition_signature_verification_uses_sealed_descriptor_snapshot(
    environment: TransitionEnvironment,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first_role = sorted(REQUIRED_SIGNER_ROLES)[0]
    signature = (
        environment.record_path.parent
        / f"signatures/{first_role}.sshsig"
    )
    original = transition._sealed_snapshot_fd
    calls = 0

    def seal_then_swap_path(raw: bytes) -> int:
        nonlocal calls
        descriptor = original(raw)
        calls += 1
        if calls == 2:
            signature.write_bytes(b"attacker path replacement\n")
        return descriptor

    monkeypatch.setattr(
        transition,
        "_sealed_snapshot_fd",
        seal_then_swap_path,
    )

    assert _verify(environment)["status"] == "verified"


def test_sealed_snapshot_has_libc_and_constant_fallbacks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delattr(transition.os, "memfd_create", raising=False)
    monkeypatch.delattr(transition.os, "MFD_ALLOW_SEALING", raising=False)
    monkeypatch.delattr(transition.os, "MFD_CLOEXEC", raising=False)
    for name in (
        "F_ADD_SEALS",
        "F_GET_SEALS",
        "F_SEAL_SEAL",
        "F_SEAL_SHRINK",
        "F_SEAL_GROW",
        "F_SEAL_WRITE",
    ):
        monkeypatch.delattr(transition.fcntl, name, raising=False)

    descriptor = transition._sealed_snapshot_fd(b"sealed fallback")
    try:
        assert os.pread(descriptor, 64, 0) == b"sealed fallback"
        assert transition.fcntl.fcntl(descriptor, 1034) & 0x000F == 0x000F
    finally:
        os.close(descriptor)


def test_transition_cross_binds_external_trust_policy_digest(
    environment: TransitionEnvironment,
) -> None:
    _mutate_record(
        environment,
        lambda record: record["controls"]["trust_policy"].__setitem__(
            "sha256",
            "sha256:" + "f" * 64,
        ),
    )

    with pytest.raises(
        TransitionVerificationError,
        match="attestation trust_policy_sha256 drift",
    ):
        _verify(environment)


def test_transition_requires_independently_administered_conformance_attestation(
    environment: TransitionEnvironment,
) -> None:
    attestation_artifact = environment.record["controls"]["external_launcher"][
        "deployment_attestation"
    ]
    attestation_path = environment.root / attestation_artifact["path"]
    attestation = json.loads(attestation_path.read_text(encoding="utf-8"))
    attestation["independently_administered"] = False
    _write_json(attestation_path, attestation)

    def mutate(record: dict[str, Any]) -> None:
        record["controls"]["external_launcher"]["deployment_attestation"][
            "sha256"
        ] = _digest(attestation_path)

    _mutate_record(environment, mutate)

    with pytest.raises(
        TransitionVerificationError,
        match="independently_administered drift",
    ):
        _verify(environment)


@pytest.mark.parametrize("field", ["must_not_reuse_artifact_ids", "must_not_reuse_sha256"])
def test_transition_requires_every_pretransition_artifact_to_be_nonreusable(
    environment: TransitionEnvironment,
    field: str,
) -> None:
    _mutate_record(
        environment,
        lambda record: record["regeneration"][field].pop(),
    )

    with pytest.raises(
        TransitionVerificationError,
        match="must_not_reuse",
    ):
        _verify(environment)
