from __future__ import annotations

import copy
import errno
import hashlib
import inspect
import json
import os
import platform
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

import scripts.verify_world_aid_gate_0b as gate_0b
from scripts.verify_world_aid_gate_0b import (
    BOOTSTRAP_RECEIPT_PATHS,
    CANONICAL_APPROVAL_PATHS,
    LAUNCH,
    REQUIRED_FEATURE_FLAGS,
    REQUIRED_FORBIDDEN_ACTIONS,
    REQUIRED_ROLES,
    SELECTION,
    SIGNATURE_NAMESPACES,
    ApprovalVerificationError,
    verify_approval,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 7, 24, 12, 0, 0, tzinfo=UTC)
SYNTHETIC_HEAP = """\
# Synthetic World human-aid heap

## WORLDCOIN-G001 First synthetic goal

- Status: active
- Validation: python -m pytest -q tests/synthetic_g001_validation.py

## WORLDCOIN-G003 Second synthetic goal

- Status: active
- Validation: python -m pytest -q tests/synthetic_g003_validation.py

## WORLDCOIN-G038 Synthetic SIWE bootstrap

- Status: active
- Validation: python scripts/verify_world_siwe_offline_bootstrap.py --approval data/worldcoin_human_aid/approvals/gate-0b-selection/approval.json --offline

## WORLDCOIN-G039 Synthetic ZKP bootstrap

- Status: active
- Validation: python scripts/verify_world_aid_zkp_toolchain.py --approval data/worldcoin_human_aid/approvals/gate-0b-selection/approval.json --offline

## WORLDCOIN-G040 Synthetic DuckDB bootstrap

- Status: active
- Validation: python scripts/verify_world_aid_duckdb_bootstrap.py --approval data/worldcoin_human_aid/approvals/gate-0b-selection/approval.json --offline

## WORLDCOIN-G035 Terminal synthetic gate

- Status: blocked
- Validation: python synthetic-terminal-validation.py
"""
SYNTHETIC_BUNDLES = {
    "WORLDCOIN-G001": "worldcoin-human-aid/core",
    "WORLDCOIN-G002": "worldcoin-human-aid/integration-audit",
    "WORLDCOIN-G003": "worldcoin-human-aid/policy",
    "WORLDCOIN-G037": "worldcoin-human-aid/siwe-dependency-lock",
    "WORLDCOIN-G038": "worldcoin-human-aid/siwe-offline-bootstrap",
    "WORLDCOIN-G039": "worldcoin-human-aid/zkp-toolchain-bootstrap",
    "WORLDCOIN-G040": "worldcoin-human-aid/duckdb-bootstrap",
    "WORLDCOIN-G041": "worldcoin-human-aid/zkp-toolchain-preparation",
    "WORLDCOIN-G042": "worldcoin-human-aid/duckdb-preparation",
}
SELECTION_PREPARATION_GOALS = {
    "WORLDCOIN-G002",
    "WORLDCOIN-G037",
    "WORLDCOIN-G041",
    "WORLDCOIN-G042",
}
LAUNCH_PREREQUISITE_GOALS = SELECTION_PREPARATION_GOALS | {
    "WORLDCOIN-G038",
    "WORLDCOIN-G039",
    "WORLDCOIN-G040",
}


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


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def _artifact(root: Path, relative: str, content: bytes | str | None = None) -> dict[str, str]:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    if content is None:
        content = f"synthetic fixture for {relative}\n"
    if isinstance(content, str):
        path.write_text(content, encoding="utf-8")
    else:
        path.write_bytes(content)
    return {"path": relative, "sha256": _sha256(path)}


def _existing_artifact(root: Path, relative: str) -> dict[str, str]:
    return {"path": relative, "sha256": _sha256(root / relative)}


def _json_artifact(root: Path, relative: str, value: dict[str, Any]) -> dict[str, str]:
    return _artifact(root, relative, json.dumps(value, indent=2, sort_keys=True) + "\n")


def _git_init(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    _run("git", "init", "-q", cwd=path)
    _run("git", "config", "user.email", "gate0b-tests@example.invalid", cwd=path)
    _run("git", "config", "user.name", "Gate 0B Tests", cwd=path)


def _commit_all(path: Path, message: str) -> str:
    _run("git", "add", "-A", cwd=path)
    _run("git", "commit", "-q", "-m", message, cwd=path)
    return _run("git", "rev-parse", "HEAD", cwd=path)


def _public_key_fingerprint(public_key_line: str) -> str:
    key_blob = public_key_line.split()[1]
    decoded = __import__("base64").b64decode(key_blob)
    encoded = __import__("base64").b64encode(hashlib.sha256(decoded).digest()).decode("ascii").rstrip("=")
    return f"SHA256:{encoded}"


@dataclass
class SignedGateEnvironment:
    root: Path
    allowed_signers: Path
    identities: dict[str, str]
    private_keys: dict[str, Path]
    fingerprints: dict[str, str]
    selection_record: dict[str, Any]
    selection_path: Path
    launch_record: dict[str, Any] | None = None
    launch_path: Path | None = None
    read_only_directories: tuple[Path, ...] = ()

    def restore_directory_modes(self) -> None:
        for path in self.read_only_directories:
            if path.exists():
                for entry in path.rglob("*"):
                    entry.chmod(0o755 if entry.is_dir() else 0o644)
                path.chmod(0o755)


def _generate_trust_store(root: Path) -> tuple[Path, dict[str, str], dict[str, Path], dict[str, str]]:
    roles = sorted(REQUIRED_ROLES[LAUNCH])
    key_root = root.parent / f"{root.name}-operator-keys"
    key_root.mkdir(parents=True, exist_ok=True)
    identities: dict[str, str] = {}
    private_keys: dict[str, Path] = {}
    fingerprints: dict[str, str] = {}
    allowed_lines: list[str] = []
    for role in roles:
        identity = f"{role}@example.invalid"
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
        public_line = private_key.with_suffix(".pub").read_text(encoding="utf-8").strip()
        key_type, key_blob, *_ = public_line.split()
        allowed_lines.append(f"{identity} {key_type} {key_blob}\n")
        identities[role] = identity
        private_keys[role] = private_key
        fingerprints[role] = _public_key_fingerprint(public_line)
    allowed_signers = key_root / "allowed_signers"
    allowed_signers.write_text("".join(allowed_lines), encoding="utf-8")
    allowed_signers.chmod(0o444)
    return allowed_signers, identities, private_keys, fingerprints


def _timestamps() -> tuple[str, str, str]:
    issued = (NOW - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    not_before = issued
    expires = (NOW + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return issued, not_before, expires


def _reviewers(phase: str, identities: dict[str, str]) -> list[dict[str, str]]:
    issued, _, expires = _timestamps()
    return [
        {
            "role": role,
            "identity": identities[role],
            "decision": "approved",
            "reviewed_at": issued,
            "expires_at": expires,
        }
        for role in sorted(REQUIRED_ROLES[phase])
    ]


def _trust(
    phase: str,
    identities: dict[str, str],
    fingerprints: dict[str, str],
    allowed_signers: Path,
) -> dict[str, Any]:
    return {
        "signature_namespace": SIGNATURE_NAMESPACES[phase],
        "allowed_signers_sha256": _sha256(allowed_signers),
        "signatures": [
            {
                "role": role,
                "identity": identities[role],
                "key_fingerprint": fingerprints[role],
                "file": f"{role}.sshsig",
            }
            for role in sorted(REQUIRED_ROLES[phase])
        ],
    }


def _scope(phase: str) -> dict[str, Any]:
    if phase == SELECTION:
        goals = sorted(("WORLDCOIN-G038", "WORLDCOIN-G039", "WORLDCOIN-G040"))
        validation_commands = [
            "python scripts/verify_world_siwe_offline_bootstrap.py --approval "
            "data/worldcoin_human_aid/approvals/gate-0b-selection/approval.json --offline",
            "python scripts/verify_world_aid_zkp_toolchain.py --approval "
            "data/worldcoin_human_aid/approvals/gate-0b-selection/approval.json --offline",
            "python scripts/verify_world_aid_duckdb_bootstrap.py --approval "
            "data/worldcoin_human_aid/approvals/gate-0b-selection/approval.json --offline",
        ]
    else:
        goals = ["WORLDCOIN-G001", "WORLDCOIN-G003"]
        validation_commands = [
            "python -m pytest -q tests/synthetic_g001_validation.py",
            "python -m pytest -q tests/synthetic_g003_validation.py",
        ]
    writable_paths = (
        [
            BOOTSTRAP_RECEIPT_PATHS["siwe"],
            BOOTSTRAP_RECEIPT_PATHS["zkp"],
            BOOTSTRAP_RECEIPT_PATHS["duckdb"],
            "docs/reports",
        ]
        if phase == SELECTION
        else ["wallet_interface/world_aid"]
    )
    return {
        "goal_ids": goals,
        "validation_commands": validation_commands,
        "writable_paths": writable_paths,
        "network": {
            "default_deny": True,
            "registry_access": False,
            "allowed_destinations": [],
        },
        "feature_flags": dict(REQUIRED_FEATURE_FLAGS),
        "live_secrets_present": False,
        "forbidden_actions": sorted(REQUIRED_FORBIDDEN_ACTIONS),
    }


def _canonical_bundle_index() -> dict[str, Any]:
    bundles: dict[str, Any] = {}
    for goal_id, bundle_key in SYNTHETIC_BUNDLES.items():
        task_id = f"WORLDCOIN-AUTO-{goal_id[-3:]}"
        task_cid = f"synthetic-cid-{goal_id.lower()}"
        bundles[bundle_key] = {
            "bundle_key": bundle_key,
            "shard_path": f"synthetic/{bundle_key.replace('/', '-')}.todo.md",
            "tasks": [
                {
                    "task_id": task_id,
                    "goal_id": goal_id,
                    "canonical_task_cid": task_cid,
                    "task_cid": task_cid,
                    "depends_on": [],
                }
            ],
        }
    return {"schema": "synthetic-bundle-index/v1", "bundles": bundles}


def _derived_bundle_index(
    canonical: dict[str, Any],
    canonical_path: str,
    *,
    execution_goals: set[str],
    completed_goals: set[str],
) -> dict[str, Any]:
    derived = copy.deepcopy(canonical)
    allowed = {bundle_key for goal_id, bundle_key in SYNTHETIC_BUNDLES.items() if goal_id in execution_goals}
    for bundle in derived["bundles"].values():
        for task in bundle["tasks"]:
            if task["goal_id"] in completed_goals:
                task["status"] = "completed"
    derived.update(
        {
            "derived_from_bundle_index": canonical_path,
            "execution_allowlist": sorted(allowed),
            "excluded_bundle_keys": sorted(set(derived["bundles"]) - allowed),
            "execution_goal_ids": sorted(execution_goals),
            "completed_prerequisite_goal_ids": sorted(completed_goals),
        }
    )
    return derived


def _network_canary_receipt() -> dict[str, Any]:
    issued, _, _ = _timestamps()
    return {
        "schema": "world-human-aid-egress-canary/v2",
        "generated_at": issued,
        "synthetic_fixture": True,
        "human_approval": False,
        "contains_secrets": False,
        "offline": True,
        "passed": True,
        "boundary": {
            "apparmor": {
                "label": "linux-sandbox (enforce)",
                "profile": "linux-sandbox",
                "mode": "enforce",
                "expected_profile": "linux-sandbox",
                "matches_reviewed_profile": True,
            },
            "network_namespace": {
                "identity": "net:[4026533000]",
                "expected_identity": "net:[4026533000]",
                "host_identity": "net:[4026532000]",
                "matches_reviewed_namespace": True,
                "host_identity_valid": True,
                "separated_from_host": True,
            },
            "interfaces": ["lo"],
            "loopback_only": True,
            "ipv4_routes": [],
            "ipv6_routes": [],
            "no_external_route": True,
            "errors": [],
            "passed": True,
        },
        "results": [
            {
                "surface": "ipv4_tcp_connect",
                "target_class": "RFC5737_TEST_NET",
                "outcome": "policy_denied",
                "errno": errno.ENETUNREACH,
                "errno_name": "ENETUNREACH",
                "error_type": "OSError",
            },
            {
                "surface": "dns_resolution",
                "outcome": "not_used_as_policy_evidence",
                "attempted": False,
                "accepted_as_policy_evidence": False,
                "reason": "DNS failure is not accepted as externally enforced policy evidence.",
            },
        ],
        "interpretation": (
            "Synthetic canary evidence proves only that the reviewed external boundary blocked "
            "and reported a bounded TEST-NET connection; it is not human approval."
        ),
    }


def _security_evidence(
    root: Path,
    phase: str,
    *,
    selection_approval_sha256: str | None = None,
) -> dict[str, dict[str, str]]:
    issued, _, expires = _timestamps()
    common: dict[str, Any] = {
        "phase": phase,
        "status": "passed",
        "checked_at": issued,
        "valid_until": expires,
        "offline": True,
        "live_actions_authorized": False,
    }
    if phase == LAUNCH:
        assert selection_approval_sha256 is not None
        common["selection_approval_sha256"] = selection_approval_sha256
    base = f"data/worldcoin_human_aid/gate_evidence/gate-0b-{phase}"
    return {
        "network_deny_canary": _json_artifact(
            root,
            f"{base}/network-deny-canary.json",
            _network_canary_receipt(),
        ),
        "egress_policy": _json_artifact(
            root,
            f"{base}/egress-policy-attestation.json",
            {
                **common,
                "schema_version": "world-human-aid-egress-policy-attestation/v1",
                "external_enforcement": True,
                "default_deny": True,
                "registry_access": False,
                "allowed_destinations": [],
            },
        ),
        "no_live_secrets_attestation": _json_artifact(
            root,
            f"{base}/no-live-secrets-attestation.json",
            {
                **common,
                "schema_version": "world-human-aid-no-live-secrets-attestation/v1",
                "live_secrets_present": False,
                "signing_material_present": False,
                "production_credentials_present": False,
                "treasury_access_present": False,
            },
        ),
    }


def _preflight_artifact_record(root: Path, relative: str, role: str) -> dict[str, Any]:
    path = root / relative
    return {
        "path": relative,
        "role": role,
        "sha256": _sha256(path),
        "size": path.stat().st_size,
    }


def _build_generated_artifacts(root: Path) -> dict[str, dict[str, str]]:
    generated_root = Path("data/worldcoin_human_aid/agent_supervisor/regenerations/synthetic-reviewed")
    canonical_path = (generated_root / "objective_bundles/index.json").as_posix()
    canonical = _canonical_bundle_index()
    artifacts: dict[str, dict[str, str]] = {
        "full_board": _artifact(
            root,
            (generated_root / "WORLDCOIN_HUMAN_AID_TODO.md").as_posix(),
            "# Synthetic immutable full board\n",
        ),
        "objective_graph": _json_artifact(
            root,
            (generated_root / "objective_graph.json").as_posix(),
            {
                "schema": "ipfs_accelerate_py.agent_supervisor.objective_graph",
                "goals": sorted(SYNTHETIC_BUNDLES),
            },
        ),
        "bundle_index": _json_artifact(root, canonical_path, canonical),
    }
    generated_files: list[tuple[str, str]] = [
        (artifacts["full_board"]["path"], "full_board"),
        (artifacts["objective_graph"]["path"], "objective_graph"),
        (artifacts["bundle_index"]["path"], "bundle_index_json"),
    ]
    for relative, role, content in (
        (
            (generated_root / "objective_bundles/index.duckdb").as_posix(),
            "bundle_index_duckdb",
            b"synthetic paired DuckDB index",
        ),
        (
            (generated_root / "objective_bundles/todo_vector_index.json").as_posix(),
            "todo_vector_index",
            "{}\n",
        ),
        (
            (generated_root / "plan_evaluations.json").as_posix(),
            "plan_evaluations",
            "{}\n",
        ),
        (
            (generated_root / "objective_generation.json").as_posix(),
            "objective_generation",
            "{}\n",
        ),
        (
            (generated_root / "discovery/synthetic.md").as_posix(),
            "discovery",
            "synthetic discovery\n",
        ),
        (
            (generated_root / "objective_bundles/synthetic.todo.md").as_posix(),
            "bundle_shard",
            "synthetic shard\n",
        ),
    ):
        generated_files.append((_artifact(root, relative, content)["path"], role))

    profiles = {
        "g002-only": _derived_bundle_index(
            canonical,
            canonical_path,
            execution_goals={"WORLDCOIN-G002"},
            completed_goals=set(),
        ),
        "gate0b-preparation": _derived_bundle_index(
            canonical,
            canonical_path,
            execution_goals=SELECTION_PREPARATION_GOALS,
            completed_goals={"WORLDCOIN-G002"},
        ),
        "g038-g040": _derived_bundle_index(
            canonical,
            canonical_path,
            execution_goals={"WORLDCOIN-G038", "WORLDCOIN-G039", "WORLDCOIN-G040"},
            completed_goals=SELECTION_PREPARATION_GOALS,
        ),
        "implementation": _derived_bundle_index(
            canonical,
            canonical_path,
            execution_goals={"WORLDCOIN-G001", "WORLDCOIN-G003"},
            completed_goals=LAUNCH_PREREQUISITE_GOALS,
        ),
    }
    for name, profile in profiles.items():
        json_relative = (generated_root / f"launch_profiles/{name}.index.json").as_posix()
        duckdb_relative = (generated_root / f"launch_profiles/{name}.index.duckdb").as_posix()
        profile_artifact = _json_artifact(root, json_relative, profile)
        paired_artifact = _artifact(root, duckdb_relative, f"synthetic {name} DuckDB projection\n")
        generated_files.extend(
            [
                (profile_artifact["path"], "launch_profile_json"),
                (paired_artifact["path"], "launch_profile_duckdb"),
            ]
        )
        if name == "g038-g040":
            artifacts["restricted_bundle_index"] = profile_artifact
            artifacts["restricted_bundle_index_duckdb"] = paired_artifact
        elif name == "implementation":
            artifacts["implementation_bundle_index"] = profile_artifact
            artifacts["implementation_bundle_index_duckdb"] = paired_artifact

    verifier_artifacts: dict[str, dict[str, Any]] = {}
    for key, relative in {
        "generated_board": "scripts/verify_world_aid_generated_board.py",
        "preflight_receipt": "scripts/verify_world_aid_preflight_receipt.py",
    }.items():
        artifact = _artifact(root, relative, f"# synthetic {key} verifier\n")
        verifier_artifacts[key] = {
            **artifact,
            "size": (root / relative).stat().st_size,
        }
    for key, relative in {
        "siwe_adapter": "wallet_interface/services/world_siwe_verifier/index.mjs",
        "siwe_proposal": "data/worldcoin_human_aid/bootstrap/world-siwe-dependency-proposal.json",
        "siwe_static_test": "tests/world_aid/test_siwe_dependency_lock.py",
        "siwe_verifier": "scripts/verify_world_siwe_offline_bootstrap.py",
        "siwe_runtime_test": "tests/world_aid/test_siwe_offline_bootstrap.py",
        "zkp_verifier": "scripts/verify_world_aid_zkp_toolchain.py",
        "zkp_runtime_test": "tests/world_aid/test_zkp_toolchain_bootstrap.py",
        "duckdb_verifier": "scripts/verify_world_aid_duckdb_bootstrap.py",
        "duckdb_runtime_test": "tests/world_aid/test_duckdb_bootstrap.py",
    }.items():
        artifacts[key] = _artifact(root, relative, f"# synthetic {key} contract\n")

    preflight = {
        "schema": "world_aid.generated_board_preflight_receipt@1",
        "status": "passed",
        "passed": True,
        "offline": True,
        "no_start": True,
        "generated_root": generated_root.as_posix(),
        "objective_path": "docs/planning/WORLDCOIN_HUMAN_AID_OBJECTIVE_HEAP.md",
        "summary": {
            "status": "passed",
            "source_goal_count": len(SYNTHETIC_BUNDLES),
            "schedulable_goal_count": len(SYNTHETIC_BUNDLES),
            "task_count": len(SYNTHETIC_BUNDLES),
            "bundle_count": len(SYNTHETIC_BUNDLES),
            "dag_count": 1,
        },
        "verifiers": verifier_artifacts,
        "artifacts": sorted(
            (_preflight_artifact_record(root, relative, role) for relative, role in generated_files),
            key=lambda item: (item["role"], item["path"]),
        ),
    }
    artifacts["preflight_receipt"] = _json_artifact(
        root,
        (generated_root / "preflight-receipt.json").as_posix(),
        preflight,
    )
    return artifacts


def _bootstrap_receipt(
    goal_id: str,
    selection_record: dict[str, Any],
    selection_sha256: str,
    *,
    duckdb: bool = False,
) -> dict[str, Any]:
    receipt: dict[str, Any] = {
        "goal_id": goal_id,
        "status": "passed",
        "completed_at": selection_record["issued_at"],
        "valid_until": selection_record["expires_at"],
        "offline": True,
        "live_actions_authorized": False,
        "selection_record_id": selection_record["record_id"],
        "selection_approval_sha256": selection_sha256,
        "real_execution": True,
        "cache_mutated": False,
    }
    if goal_id == "WORLDCOIN-G038":
        siwe = selection_record["dependency_sets"]["siwe"]
        toolchain = siwe["runtime_toolchain"]
        canary_artifact = selection_record["security_evidence"]["network_deny_canary"]
        policy_artifact = selection_record["security_evidence"]["egress_policy"]
        boundary = {
            "namespace": "net:[4026533000]",
            "apparmor_profile": "linux-sandbox (enforce)",
            "interfaces": ["lo"],
            "no_external_route": True,
            "network_deny_canary_sha256": canary_artifact["sha256"],
            "egress_policy_sha256": policy_artifact["sha256"],
        }
        cache_digest = siwe["cache"]["tree_sha256"]
        receipt.update(
            {
                "schema_version": "world-human-aid-siwe-bootstrap-verification-receipt/v2",
                "toolchain": {
                    "platform": toolchain["platform"],
                    "architecture": toolchain["architecture"],
                    "archive_sha256": toolchain["archive"]["sha256"],
                    "node_sha256": toolchain["node"]["sha256"],
                    "node_version": toolchain["node"]["version"],
                    "npm_cli_sha256": toolchain["npm_cli"]["sha256"],
                    "npm_version": toolchain["npm_cli"]["version"],
                },
                "inputs": {
                    "manifest_sha256": siwe["manifest"]["sha256"],
                    "lock_sha256": siwe["lockfile"]["sha256"],
                    "adapter_sha256": selection_record["reviewed_state"]["siwe_adapter"]["sha256"],
                },
                "cache": {
                    "reviewed_before_sha256": cache_digest,
                    "reviewed_after_sha256": cache_digest,
                    "local_before_sha256": cache_digest,
                    "local_after_sha256": cache_digest,
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
        )
        return receipt
    receipt.update(
        {
            "schema_version": "world-human-aid-bootstrap-verification-receipt/v1",
            "network_attempts": 0,
        }
    )
    if duckdb:
        receipt.update({"single_writer_enforced": True, "external_access": False})
    return receipt


def _dry_run_manifest(
    implementation_index: dict[str, Any],
    implementation_duckdb_path: str,
) -> dict[str, Any]:
    lanes = [
        {
            "bundle_key": bundle_key,
            "queue_payload": {
                "tasks": copy.deepcopy(implementation_index["bundles"][bundle_key]["tasks"]),
            },
        }
        for bundle_key in implementation_index["execution_allowlist"]
    ]
    return {
        "schema": "ipfs_accelerate_py.agent_supervisor.bundle_supervisor",
        "bundle_index_path": implementation_duckdb_path,
        "planned_count": len(lanes),
        "started_count": 0,
        "running_count": 0,
        "active_worker_count": 0,
        "started": [],
        "active_worker_pids": [],
        "launched_task_cids": [],
        "lanes": lanes,
    }


def _sign_record(
    root: Path,
    phase: str,
    record: dict[str, Any],
    private_keys: dict[str, Path],
) -> Path:
    approval_path = root / CANONICAL_APPROVAL_PATHS[phase]
    _write_json(approval_path, record)
    signature_dir = approval_path.parent / "signatures"
    signature_dir.mkdir(parents=True, exist_ok=True)
    for role in sorted(REQUIRED_ROLES[phase]):
        generated_signature = Path(f"{approval_path}.sig")
        if generated_signature.exists():
            generated_signature.unlink()
        _run(
            "ssh-keygen",
            "-Y",
            "sign",
            "-f",
            str(private_keys[role]),
            "-n",
            SIGNATURE_NAMESPACES[phase],
            str(approval_path),
            cwd=root,
        )
        generated_signature.replace(signature_dir / f"{role}.sshsig")
    return approval_path


def _selection_record(
    root: Path,
    root_commit: str,
    submodule_commits: dict[str, str],
    allowed_signers: Path,
    identities: dict[str, str],
    fingerprints: dict[str, str],
) -> tuple[dict[str, Any], tuple[Path, Path]]:
    generated = _build_generated_artifacts(root)
    reviewed_state = {
        "root_commit": root_commit,
        "submodule_commits": submodule_commits,
        "objective_heap": _artifact(
            root,
            "docs/planning/WORLDCOIN_HUMAN_AID_OBJECTIVE_HEAP.md",
            SYNTHETIC_HEAP,
        ),
        "implementation_plan": _artifact(
            root,
            "docs/planning/WORLDCOIN_HUMAN_AID_IMPLEMENTATION_PLAN.md",
        ),
        "runbook": _artifact(
            root,
            "docs/planning/WORLDCOIN_HUMAN_AID_AGENT_SUPERVISOR_RUNBOOK.md",
        ),
        "storage_adr": _artifact(root, "docs/adr/WORLD_AID_DUCKDB_STORAGE_ADR.md"),
        **{
            key: generated[key]
            for key in (
                "full_board",
                "objective_graph",
                "bundle_index",
                "restricted_bundle_index",
                "restricted_bundle_index_duckdb",
                "siwe_adapter",
                "siwe_proposal",
                "siwe_static_test",
                "siwe_verifier",
                "siwe_runtime_test",
                "zkp_verifier",
                "zkp_runtime_test",
                "duckdb_verifier",
                "duckdb_runtime_test",
                "preflight_receipt",
            )
        },
    }

    npm_cache = root / "data/worldcoin_human_aid/offline/npm"
    wheelhouse = root / "data/worldcoin_human_aid/offline/wheels"
    dependencies = {
        "siwe": {
            "runtime_toolchain": {
                "platform": "linux",
                "architecture": {"amd64": "x86_64", "arm64": "aarch64"}.get(
                    platform.machine().lower(),
                    platform.machine().lower(),
                ),
                "archive_format": "tar.xz",
                "archive": _artifact(
                    root,
                    "data/worldcoin_human_aid/offline/node/node-synthetic.tar.xz",
                    b"synthetic toolchain archive",
                ),
                "root": "node-synthetic",
                "node": {
                    "path": "node-synthetic/bin/node",
                    "sha256": "sha256:" + hashlib.sha256(b"synthetic node").hexdigest(),
                    "version": "22.23.1",
                },
                "npm_cli": {
                    "path": "node-synthetic/lib/node_modules/npm/bin/npm-cli.js",
                    "sha256": "sha256:" + hashlib.sha256(b"synthetic npm cli").hexdigest(),
                    "version": "10.9.8",
                },
            },
            "manifest": _artifact(root, "wallet_interface/services/world_siwe_verifier/package.json", "{}\n"),
            "lockfile": _artifact(root, "wallet_interface/services/world_siwe_verifier/package-lock.json", "{}\n"),
            "tarballs": [_artifact(root, "data/worldcoin_human_aid/offline/npm/siwe.tgz", b"synthetic tgz")],
            "cache": {
                "path": "data/worldcoin_human_aid/offline/npm",
                "read_only": True,
                "tree_sha256": "sha256:" + "0" * 64,
            },
            "licenses": _artifact(root, "data/worldcoin_human_aid/bootstrap/siwe-licenses.json", "{}\n"),
            "provenance": _artifact(root, "data/worldcoin_human_aid/bootstrap/siwe-provenance.json", "{}\n"),
            "sbom": _artifact(root, "data/worldcoin_human_aid/bootstrap/siwe-sbom.json", "{}\n"),
            "vulnerability_review": _artifact(
                root,
                "data/worldcoin_human_aid/bootstrap/siwe-vulnerability-review.json",
                "{}\n",
            ),
            "lifecycle_scripts": [],
        },
        "zkp": {
            "architecture": {"amd64": "x86_64", "arm64": "aarch64"}.get(
                platform.machine().lower(),
                platform.machine().lower(),
            ),
            "backend": "synthetic-test-backend",
            "version": "1.2.3",
            "tool": _artifact(root, "data/worldcoin_human_aid/offline/zkp/tool", b"synthetic tool"),
            "smoke_source": _artifact(root, "tests/world_aid/fixtures/zkp_smoke/main.nr"),
            "smoke_lock": _artifact(root, "tests/world_aid/fixtures/zkp_smoke/Nargo.lock"),
            "licenses": _artifact(root, "data/worldcoin_human_aid/bootstrap/zkp-licenses.json", "{}\n"),
            "provenance": _artifact(root, "data/worldcoin_human_aid/bootstrap/zkp-provenance.json", "{}\n"),
            "sbom": _artifact(root, "data/worldcoin_human_aid/bootstrap/zkp-sbom.json", "{}\n"),
            "vulnerability_review": _artifact(
                root,
                "data/worldcoin_human_aid/bootstrap/zkp-vulnerability-review.json",
                "{}\n",
            ),
            "deterministic_flags": ["--synthetic-deterministic"],
            "resource_bounds": {
                "max_seconds": 60,
                "max_memory_mb": 1024,
                "max_output_bytes": 1048576,
            },
        },
        "duckdb": {
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "duckdb_version": "1.4.3",
            "wheels": [_artifact(root, "data/worldcoin_human_aid/offline/wheels/duckdb.whl", b"synthetic wheel")],
            "wheelhouse": {
                "path": "data/worldcoin_human_aid/offline/wheels",
                "read_only": True,
            },
            "requirements_lock": _artifact(root, "requirements-world-aid.lock"),
            "runtime_policy": _artifact(root, "wallet_interface/deploy/world-aid-duckdb-runtime.yml"),
            "backup_policy": _artifact(root, "docs/specs/WORLD_AID_DUCKDB_BACKUP.md"),
            "licenses": _artifact(root, "data/worldcoin_human_aid/bootstrap/duckdb-licenses.json", "{}\n"),
            "provenance": _artifact(root, "data/worldcoin_human_aid/bootstrap/duckdb-provenance.json", "{}\n"),
            "sbom": _artifact(root, "data/worldcoin_human_aid/bootstrap/duckdb-sbom.json", "{}\n"),
            "vulnerability_review": _artifact(
                root,
                "data/worldcoin_human_aid/bootstrap/duckdb-vulnerability-review.json",
                "{}\n",
            ),
            "topology": "single-host-single-writer-coordinator",
            "database_file_encryption": "encrypted-volume-plus-application-envelope-encryption",
            "extension_auto_install": False,
            "extension_auto_load": False,
            "external_access": False,
            "community_extensions": False,
            "extension_directory": {
                "mode": "disabled",
                "path": "",
                "allowlist": [],
            },
        },
    }
    issued, not_before, expires = _timestamps()
    return (
        {
            "schema_version": "world-human-aid-gate-0b-selection/v1",
            "gate_id": "gate-0b-selection",
            "record_id": "gate-0b-selection-synthetic-test-001",
            "decision": "approved",
            "issued_at": issued,
            "not_before": not_before,
            "expires_at": expires,
            "reviewed_state": reviewed_state,
            "scope": _scope(SELECTION),
            "reviewers": _reviewers(SELECTION, identities),
            "exceptions": [],
            "trust": _trust(SELECTION, identities, fingerprints, allowed_signers),
            "dependency_sets": dependencies,
            "security_evidence": _security_evidence(root, SELECTION),
        },
        (npm_cache, wheelhouse),
    )


def _build_selection_environment(tmp_path: Path, request: pytest.FixtureRequest) -> SignedGateEnvironment:
    root = tmp_path / "repo"
    _git_init(root)
    submodule_commits: dict[str, str] = {}
    for name in ("ipfs_accelerate_py", "ipfs_datasets_py"):
        submodule = root / name
        _git_init(submodule)
        (submodule / "marker.txt").write_text(f"{name}\n", encoding="utf-8")
        submodule_commits[name] = _commit_all(submodule, f"Initialize {name}")

    allowed_signers, identities, private_keys, fingerprints = _generate_trust_store(root)
    record, read_only_directories = _selection_record(
        root,
        "0" * 40,
        submodule_commits,
        allowed_signers,
        identities,
        fingerprints,
    )
    for directory in read_only_directories:
        for entry in directory.rglob("*"):
            entry.chmod(0o555 if entry.is_dir() else 0o444)
        directory.chmod(0o555)
    record["dependency_sets"]["siwe"]["cache"]["tree_sha256"] = gate_0b._read_only_tree_digest(
        read_only_directories[0],
        "synthetic SIWE cache",
    )
    (root / "tracked-marker.txt").write_text("reviewed\n", encoding="utf-8")
    root_commit = _commit_all(root, "Prepare selection evidence")
    record["reviewed_state"]["root_commit"] = root_commit
    selection_path = _sign_record(root, SELECTION, record, private_keys)
    environment = SignedGateEnvironment(
        root=root,
        allowed_signers=allowed_signers,
        identities=identities,
        private_keys=private_keys,
        fingerprints=fingerprints,
        selection_record=record,
        selection_path=selection_path,
        read_only_directories=read_only_directories,
    )
    request.addfinalizer(environment.restore_directory_modes)
    return environment


@pytest.fixture()
def selection_environment(tmp_path: Path, request: pytest.FixtureRequest) -> SignedGateEnvironment:
    return _build_selection_environment(tmp_path, request)


@pytest.fixture()
def launch_environment(tmp_path: Path, request: pytest.FixtureRequest) -> SignedGateEnvironment:
    environment = _build_selection_environment(tmp_path, request)
    root = environment.root
    selection_state = environment.selection_record["reviewed_state"]
    generated_root = Path(selection_state["full_board"]["path"]).parent
    implementation_index_path = (generated_root / "launch_profiles/implementation.index.json").as_posix()
    implementation_duckdb_path = (generated_root / "launch_profiles/implementation.index.duckdb").as_posix()
    implementation_index = json.loads((root / implementation_index_path).read_text(encoding="utf-8"))
    dry_run_artifact = _json_artifact(
        root,
        (generated_root / "dry_run/lane-manifest.json").as_posix(),
        _dry_run_manifest(implementation_index, implementation_duckdb_path),
    )
    reviewed_state = {
        "root_commit": "0" * 40,
        "submodule_commits": {
            name: _run("git", "rev-parse", "HEAD", cwd=root / name)
            for name in ("ipfs_accelerate_py", "ipfs_datasets_py")
        },
        **{
            key: copy.deepcopy(selection_state[key])
            for key in (
                "objective_heap",
                "implementation_plan",
                "runbook",
                "storage_adr",
                "full_board",
                "objective_graph",
                "bundle_index",
                "preflight_receipt",
            )
        },
        "implementation_bundle_index": _existing_artifact(root, implementation_index_path),
        "implementation_bundle_index_duckdb": _existing_artifact(root, implementation_duckdb_path),
        "dry_run_receipt": dry_run_artifact,
    }
    selection_signature_artifacts = [
        {
            "path": (CANONICAL_APPROVAL_PATHS[SELECTION].parent / "signatures" / f"{role}.sshsig").as_posix(),
            "sha256": _sha256(root / CANONICAL_APPROVAL_PATHS[SELECTION].parent / "signatures" / f"{role}.sshsig"),
        }
        for role in sorted(REQUIRED_ROLES[SELECTION])
    ]
    issued, not_before, expires = _timestamps()
    selection_sha256 = _sha256(environment.selection_path)
    bootstrap_receipts = {
        "siwe": _json_artifact(
            root,
            "data/worldcoin_human_aid/bootstrap/world-siwe-offline-smoke.fixture.json",
            _bootstrap_receipt("WORLDCOIN-G038", environment.selection_record, selection_sha256),
        ),
        "zkp": _json_artifact(
            root,
            "data/worldcoin_human_aid/bootstrap/zkp-toolchain-smoke.fixture.json",
            _bootstrap_receipt("WORLDCOIN-G039", environment.selection_record, selection_sha256),
        ),
        "duckdb": _json_artifact(
            root,
            "data/worldcoin_human_aid/bootstrap/duckdb-offline-smoke.fixture.json",
            _bootstrap_receipt(
                "WORLDCOIN-G040",
                environment.selection_record,
                selection_sha256,
                duckdb=True,
            ),
        ),
    }
    security_evidence = _security_evidence(
        root,
        LAUNCH,
        selection_approval_sha256=selection_sha256,
    )
    launch_record = {
        "schema_version": "world-human-aid-gate-0b-launch/v1",
        "gate_id": "gate-0b-launch",
        "record_id": "gate-0b-launch-synthetic-test-001",
        "decision": "approved",
        "issued_at": issued,
        "not_before": not_before,
        "expires_at": expires,
        "reviewed_state": reviewed_state,
        "scope": _scope(LAUNCH),
        "reviewers": _reviewers(LAUNCH, environment.identities),
        "exceptions": [],
        "trust": _trust(
            LAUNCH,
            environment.identities,
            environment.fingerprints,
            environment.allowed_signers,
        ),
        "selection_evidence": {
            "approval": {
                "path": CANONICAL_APPROVAL_PATHS[SELECTION].as_posix(),
                "sha256": selection_sha256,
            },
            "signatures": selection_signature_artifacts,
        },
        "bootstrap_receipts": bootstrap_receipts,
        "security_evidence": security_evidence,
    }
    launch_commit = _commit_all(root, "Prepare launch evidence")
    launch_record["reviewed_state"]["root_commit"] = launch_commit
    launch_path = _sign_record(root, LAUNCH, launch_record, environment.private_keys)
    environment.launch_record = launch_record
    environment.launch_path = launch_path
    return environment


def _verify(environment: SignedGateEnvironment, phase: str) -> dict[str, Any]:
    approval_path = environment.selection_path if phase == SELECTION else environment.launch_path
    assert approval_path is not None
    return verify_approval(
        repo_root=environment.root,
        phase=phase,
        approval_path=approval_path,
        allowed_signers_path=environment.allowed_signers,
        now=NOW,
    )


def _mutate_bound_json(
    environment: SignedGateEnvironment,
    phase: str,
    section: str,
    key: str,
    mutation,
) -> None:
    source = environment.selection_record if phase == SELECTION else environment.launch_record
    assert source is not None
    record = copy.deepcopy(source)
    artifact = record[section][key]
    path = environment.root / artifact["path"]
    payload = json.loads(path.read_text(encoding="utf-8"))
    mutation(payload)
    _write_json(path, payload)
    artifact["sha256"] = _sha256(path)
    approval_path = environment.selection_path if phase == SELECTION else environment.launch_path
    assert approval_path is not None
    _write_json(approval_path, record)


def _mutate_generated_profile(
    environment: SignedGateEnvironment,
    phase: str,
    reviewed_key: str,
    mutation,
) -> None:
    source = environment.selection_record if phase == SELECTION else environment.launch_record
    assert source is not None
    record = copy.deepcopy(source)
    profile_artifact = record["reviewed_state"][reviewed_key]
    profile_path = environment.root / profile_artifact["path"]
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    mutation(profile)
    _write_json(profile_path, profile)
    profile_artifact["sha256"] = _sha256(profile_path)

    preflight_artifact = record["reviewed_state"]["preflight_receipt"]
    preflight_path = environment.root / preflight_artifact["path"]
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    bound = next(artifact for artifact in preflight["artifacts"] if artifact["path"] == profile_artifact["path"])
    bound["sha256"] = profile_artifact["sha256"]
    bound["size"] = profile_path.stat().st_size
    _write_json(preflight_path, preflight)
    preflight_artifact["sha256"] = _sha256(preflight_path)

    approval_path = environment.selection_path if phase == SELECTION else environment.launch_path
    assert approval_path is not None
    _write_json(approval_path, record)


def test_gate_0b_schemas_are_strict_and_templates_are_unsigned() -> None:
    for phase in (SELECTION, LAUNCH):
        schema_path = REPO_ROOT / f"docs/schemas/world_aid/gate-0b-{phase}.schema.json"
        template_path = REPO_ROOT / f"docs/governance/templates/gate-0b-{phase}.template.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        template = json.loads(template_path.read_text(encoding="utf-8"))

        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["additionalProperties"] is False
        assert schema["$defs"]["artifact"]["additionalProperties"] is False
        assert schema["$defs"]["scope"]["additionalProperties"] is False
        assert schema["$defs"]["trust"]["additionalProperties"] is False
        assert template["decision"] == "pending"
        assert "REPLACE-WITH" in template["record_id"]
        assert "approvals" not in template_path.parts
        assert len(template["reviewers"]) == 9
        assert len(template["trust"]["signatures"]) == 9
        assert set(schema["$defs"]["reviewer"]["properties"]["role"]["enum"]) == REQUIRED_ROLES[phase]
        assert {reviewer["role"] for reviewer in template["reviewers"]} == REQUIRED_ROLES[phase]
        assert {signature["role"] for signature in template["trust"]["signatures"]} == REQUIRED_ROLES[phase]

    launch_schema = json.loads(
        (REPO_ROOT / "docs/schemas/world_aid/gate-0b-launch.schema.json").read_text(encoding="utf-8")
    )
    launch_template = json.loads(
        (REPO_ROOT / "docs/governance/templates/gate-0b-launch.template.json").read_text(encoding="utf-8")
    )
    assert launch_schema["properties"]["selection_evidence"]["properties"]["signatures"]["minItems"] == 9
    assert len(launch_template["selection_evidence"]["signatures"]) == 9
    assert {
        Path(signature["path"]).stem for signature in launch_template["selection_evidence"]["signatures"]
    } == REQUIRED_ROLES[SELECTION]
    selection_schema = json.loads(
        (REPO_ROOT / "docs/schemas/world_aid/gate-0b-selection.schema.json").read_text(encoding="utf-8")
    )
    selection_template = json.loads(
        (REPO_ROOT / "docs/governance/templates/gate-0b-selection.template.json").read_text(encoding="utf-8")
    )
    selection_state_keys = set(selection_schema["properties"]["reviewed_state"]["required"])
    assert {
        "siwe_adapter",
        "siwe_proposal",
        "siwe_static_test",
        "full_board",
        "objective_graph",
        "restricted_bundle_index",
        "restricted_bundle_index_duckdb",
        "siwe_verifier",
        "siwe_runtime_test",
        "zkp_verifier",
        "zkp_runtime_test",
        "duckdb_verifier",
        "duckdb_runtime_test",
    } <= selection_state_keys
    assert "security_evidence" in selection_schema["required"]
    assert "security_evidence" in selection_template
    siwe_properties = selection_schema["$defs"]["siweDependencies"]["properties"]
    assert "runtime_toolchain" in selection_schema["$defs"]["siweDependencies"]["required"]
    assert siwe_properties["runtime_toolchain"] == {"$ref": "#/$defs/siweRuntimeToolchain"}
    assert selection_template["dependency_sets"]["siwe"]["runtime_toolchain"]["archive_format"] == "tar.xz"
    assert {
        "implementation_bundle_index",
        "implementation_bundle_index_duckdb",
    } <= set(launch_schema["properties"]["reviewed_state"]["required"])
    duckdb_properties = selection_schema["$defs"]["duckdbDependencies"]["properties"]
    assert duckdb_properties["external_access"]["const"] is False
    assert duckdb_properties["community_extensions"]["const"] is False
    assert selection_template["dependency_sets"]["duckdb"]["extension_directory"] == {
        "mode": "disabled",
        "path": "",
        "allowlist": [],
    }


def test_selection_approval_verifies_with_exact_real_detached_signatures(
    selection_environment: SignedGateEnvironment,
) -> None:
    summary = _verify(selection_environment, SELECTION)

    assert summary["status"] == "verified"
    assert summary["phase"] == SELECTION
    assert summary["signature_count"] == len(REQUIRED_ROLES[SELECTION])
    assert summary["verified_approval_sha256"] == (
        "sha256:" + hashlib.sha256(selection_environment.selection_path.read_bytes()).hexdigest()
    )
    assert summary["offline"] is True
    assert summary["live_actions_authorized"] is False


def test_read_only_dependency_cache_rejects_writable_nested_entries(
    selection_environment: SignedGateEnvironment,
) -> None:
    tarball = selection_environment.root / "data/worldcoin_human_aid/offline/npm/siwe.tgz"
    tarball.chmod(0o644)

    with pytest.raises(ApprovalVerificationError, match="mode-writable entry"):
        _verify(selection_environment, SELECTION)


def test_tree_digest_validates_the_opened_file_after_path_substitution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache = tmp_path / "reviewed-cache"
    cache.mkdir()
    entry = cache / "package.tgz"
    entry.write_bytes(b"x")
    entry.chmod(0o444)
    cache.chmod(0o555)
    original_open = os.open
    substituted = False

    def substitute_before_open(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal substituted
        if path == entry.name and dir_fd is not None and not substituted:
            substituted = True
            cache.chmod(0o755)
            entry.unlink()
            entry.write_bytes(b"attacker-controlled replacement")
            entry.chmod(0o644)
            cache.chmod(0o555)
        return original_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(gate_0b.os, "open", substitute_before_open)
    try:
        with pytest.raises(ApprovalVerificationError, match="mode-writable entry"):
            gate_0b._read_only_tree_digest(cache, "test cache")
    finally:
        cache.chmod(0o755)
        entry.chmod(0o644)


def test_tree_digest_stops_directory_enumeration_at_the_entry_cap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache = tmp_path / "reviewed-cache"
    cache.mkdir()
    cache.chmod(0o555)
    yielded = 0

    class SyntheticEntry:
        def __init__(self, name: str) -> None:
            self.name = name

    class SyntheticScandir:
        def __enter__(self) -> SyntheticScandir:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def __iter__(self):
            nonlocal yielded
            for index in range(1_000_000):
                yielded += 1
                yield SyntheticEntry(f"entry-{index:07d}")

    monkeypatch.setattr(gate_0b, "MAX_REVIEWED_TREE_ENTRIES", 3)
    monkeypatch.setattr(gate_0b.os, "scandir", lambda _descriptor: SyntheticScandir())
    try:
        with pytest.raises(ApprovalVerificationError, match="tree exceeds the entry limit"):
            gate_0b._read_only_tree_digest(cache, "test cache")
    finally:
        cache.chmod(0o755)
    assert yielded == 3


def test_tree_digest_applies_one_global_cap_across_nested_enumeration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache = tmp_path / "reviewed-cache"
    cache.mkdir()
    children = [cache / name for name in ("a", "b", "c")]
    for child in children:
        child.mkdir()
        child.chmod(0o555)
    cache.chmod(0o555)
    root_inode = cache.stat().st_ino
    yielded = 0

    class SyntheticEntry:
        def __init__(self, name: str) -> None:
            self.name = name

    class SyntheticScandir:
        def __init__(self, names: tuple[str, ...]) -> None:
            self.names = names

        def __enter__(self) -> SyntheticScandir:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def __iter__(self):
            nonlocal yielded
            for name in self.names:
                yielded += 1
                yield SyntheticEntry(name)

    def synthetic_scandir(descriptor: int) -> SyntheticScandir:
        names = ("a", "b", "c") if os.fstat(descriptor).st_ino == root_inode else ("one", "two", "three")
        return SyntheticScandir(names)

    monkeypatch.setattr(gate_0b, "MAX_REVIEWED_TREE_ENTRIES", 4)
    monkeypatch.setattr(gate_0b.os, "scandir", synthetic_scandir)
    try:
        with pytest.raises(ApprovalVerificationError, match="tree exceeds the entry limit"):
            gate_0b._read_only_tree_digest(cache, "test cache")
    finally:
        cache.chmod(0o755)
        for child in children:
            child.chmod(0o755)
    assert yielded == 4


def test_caller_captured_approval_bytes_are_the_verified_bytes(
    selection_environment: SignedGateEnvironment,
) -> None:
    captured = selection_environment.selection_path.read_bytes()

    summary = verify_approval(
        repo_root=selection_environment.root,
        phase=SELECTION,
        approval_path=selection_environment.selection_path,
        allowed_signers_path=selection_environment.allowed_signers,
        now=NOW,
        expected_approval_bytes=captured,
    )
    assert summary["verified_approval_sha256"] == (
        "sha256:" + hashlib.sha256(captured).hexdigest()
    )

    with pytest.raises(ApprovalVerificationError, match="caller-captured snapshot"):
        verify_approval(
            repo_root=selection_environment.root,
            phase=SELECTION,
            approval_path=selection_environment.selection_path,
            allowed_signers_path=selection_environment.allowed_signers,
            now=NOW,
            expected_approval_bytes=b'{"different":true}\n',
        )


def test_approval_mutation_during_verification_is_rejected(
    selection_environment: SignedGateEnvironment,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = gate_0b._verify_signatures

    def verify_then_mutate(*args: Any, **kwargs: Any) -> None:
        original(*args, **kwargs)
        selection_environment.selection_path.write_bytes(b'{"changed":true}\n')

    monkeypatch.setattr(gate_0b, "_verify_signatures", verify_then_mutate)
    captured = selection_environment.selection_path.read_bytes()
    with pytest.raises(ApprovalVerificationError, match="changed during verification"):
        verify_approval(
            repo_root=selection_environment.root,
            phase=SELECTION,
            approval_path=selection_environment.selection_path,
            allowed_signers_path=selection_environment.allowed_signers,
            now=NOW,
            expected_approval_bytes=captured,
        )


def test_launch_approval_verifies_and_reverifies_bound_selection(
    launch_environment: SignedGateEnvironment,
) -> None:
    summary = _verify(launch_environment, LAUNCH)

    assert summary["status"] == "verified"
    assert summary["phase"] == LAUNCH
    assert summary["signature_count"] == len(REQUIRED_ROLES[LAUNCH])
    assert summary["live_actions_authorized"] is False


def test_launch_rejects_linked_selection_swap_before_recursive_verification(
    launch_environment: SignedGateEnvironment,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = gate_0b._verify_approval

    def swap_linked_selection(**kwargs: Any) -> dict[str, Any]:
        if kwargs["historical_link"]:
            launch_environment.selection_path.write_bytes(b'{"swapped":true}\n')
        return original(**kwargs)

    monkeypatch.setattr(gate_0b, "_verify_approval", swap_linked_selection)
    with pytest.raises(ApprovalVerificationError, match="caller-captured snapshot"):
        verify_approval(
            repo_root=launch_environment.root,
            phase=LAUNCH,
            approval_path=launch_environment.launch_path,
            allowed_signers_path=launch_environment.allowed_signers,
            now=NOW,
        )


def test_launch_requires_exact_implementation_profile_objective_set(
    launch_environment: SignedGateEnvironment,
) -> None:
    record = copy.deepcopy(launch_environment.launch_record)
    record["scope"]["goal_ids"] = ["WORLDCOIN-G001"]
    _write_json(launch_environment.launch_path, record)

    with pytest.raises(ApprovalVerificationError, match="exact implementation profile goal set"):
        _verify(launch_environment, LAUNCH)


def test_duplicate_json_keys_fail_before_signature_validation(
    selection_environment: SignedGateEnvironment,
) -> None:
    original = selection_environment.selection_path.read_text(encoding="utf-8")
    selection_environment.selection_path.write_text(
        original.replace("{", '{"decision":"approved",', 1),
        encoding="utf-8",
    )

    with pytest.raises(ApprovalVerificationError, match="duplicate JSON key"):
        _verify(selection_environment, SELECTION)


def test_artifact_path_escape_is_rejected(
    selection_environment: SignedGateEnvironment,
) -> None:
    record = copy.deepcopy(selection_environment.selection_record)
    record["reviewed_state"]["objective_heap"]["path"] = "../outside"
    _write_json(selection_environment.selection_path, record)

    with pytest.raises(ApprovalVerificationError, match="escapes|normalized"):
        _verify(selection_environment, SELECTION)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("expires_at", "2026-07-24T11:59:59Z", "stale or expired"),
        ("issued_at", "2026-07-24T12:00:01Z", "issued in the future"),
        ("not_before", "2026-07-24T12:00:01Z", "not yet valid"),
    ],
)
def test_stale_and_future_records_fail_closed(
    selection_environment: SignedGateEnvironment,
    field: str,
    value: str,
    message: str,
) -> None:
    record = copy.deepcopy(selection_environment.selection_record)
    record[field] = value
    _write_json(selection_environment.selection_path, record)

    with pytest.raises(ApprovalVerificationError, match=message):
        _verify(selection_environment, SELECTION)


def test_missing_exact_reviewer_role_is_rejected(
    selection_environment: SignedGateEnvironment,
) -> None:
    record = copy.deepcopy(selection_environment.selection_record)
    record["reviewers"] = record["reviewers"][:-1]
    _write_json(selection_environment.selection_path, record)

    with pytest.raises(ApprovalVerificationError, match="exactly 9"):
        _verify(selection_environment, SELECTION)


def test_selection_requires_full_nine_role_set(
    selection_environment: SignedGateEnvironment,
) -> None:
    assert REQUIRED_ROLES[SELECTION] == REQUIRED_ROLES[LAUNCH]
    assert len(REQUIRED_ROLES[SELECTION]) == 9
    assert {reviewer["role"] for reviewer in selection_environment.selection_record["reviewers"]} == (
        REQUIRED_ROLES[SELECTION]
    )


def test_signing_key_fingerprints_must_be_unique_across_roles(
    selection_environment: SignedGateEnvironment,
) -> None:
    record = copy.deepcopy(selection_environment.selection_record)
    record["trust"]["signatures"][1]["key_fingerprint"] = record["trust"]["signatures"][0]["key_fingerprint"]
    _write_json(selection_environment.selection_path, record)

    with pytest.raises(ApprovalVerificationError, match="fingerprints must be distinct"):
        _verify(selection_environment, SELECTION)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("forbidden-goal", "terminal human-gated"),
        ("live-flag", "feature flags"),
        ("live-secret", "live_secrets_present"),
        ("duckdb-multi-writer", "multi-writer"),
        ("duckdb-extension", "auto-install"),
        ("duckdb-external-access", "external access"),
        ("duckdb-community-extensions", "community extensions"),
        ("duckdb-extension-directory", "disabled DuckDB extension_directory"),
    ],
)
def test_forbidden_scope_and_unsafe_duckdb_modes_are_rejected(
    selection_environment: SignedGateEnvironment,
    mutation: str,
    message: str,
) -> None:
    record = copy.deepcopy(selection_environment.selection_record)
    if mutation == "forbidden-goal":
        record["scope"]["goal_ids"] = ["WORLDCOIN-G035", "WORLDCOIN-G039", "WORLDCOIN-G040"]
    elif mutation == "live-flag":
        record["scope"]["feature_flags"]["WORLD_AID_EXTERNAL_CALLS_ENABLED"] = "1"
    elif mutation == "live-secret":
        record["scope"]["live_secrets_present"] = True
    elif mutation == "duckdb-multi-writer":
        record["dependency_sets"]["duckdb"]["topology"] = "multi-writer"
    elif mutation == "duckdb-extension":
        record["dependency_sets"]["duckdb"]["extension_auto_install"] = True
    elif mutation == "duckdb-external-access":
        record["dependency_sets"]["duckdb"]["external_access"] = True
    elif mutation == "duckdb-community-extensions":
        record["dependency_sets"]["duckdb"]["community_extensions"] = True
    else:
        record["dependency_sets"]["duckdb"]["extension_directory"]["path"] = "data/extensions"
    _write_json(selection_environment.selection_path, record)

    with pytest.raises(ApprovalVerificationError, match=message):
        _verify(selection_environment, SELECTION)


def test_selection_binds_full_generated_root_and_bootstrap_contracts(
    selection_environment: SignedGateEnvironment,
) -> None:
    state = selection_environment.selection_record["reviewed_state"]
    generated_root = Path(state["full_board"]["path"]).parent

    assert Path(state["objective_graph"]["path"]) == generated_root / "objective_graph.json"
    assert Path(state["restricted_bundle_index"]["path"]) == generated_root / "launch_profiles/g038-g040.index.json"
    assert Path(state["preflight_receipt"]["path"]) == generated_root / "preflight-receipt.json"
    for key in (
        "siwe_adapter",
        "siwe_proposal",
        "siwe_static_test",
        "siwe_verifier",
        "siwe_runtime_test",
        "zkp_verifier",
        "zkp_runtime_test",
        "duckdb_verifier",
        "duckdb_runtime_test",
    ):
        assert state[key]["sha256"].startswith("sha256:")


def test_selection_rejects_preflight_outside_the_immutable_generated_root(
    selection_environment: SignedGateEnvironment,
) -> None:
    record = copy.deepcopy(selection_environment.selection_record)
    record["reviewed_state"]["preflight_receipt"]["path"] = (
        "data/worldcoin_human_aid/agent_supervisor/regenerations/other/preflight-receipt.json"
    )
    _write_json(selection_environment.selection_path, record)

    with pytest.raises(ApprovalVerificationError, match="preflight_receipt.path must be under"):
        _verify(selection_environment, SELECTION)


def test_selection_rejects_noncanonical_verifier_contract_path(
    selection_environment: SignedGateEnvironment,
) -> None:
    record = copy.deepcopy(selection_environment.selection_record)
    record["reviewed_state"]["siwe_verifier"]["path"] = "scripts/other.py"
    _write_json(selection_environment.selection_path, record)

    with pytest.raises(ApprovalVerificationError, match="siwe_verifier.path must be"):
        _verify(selection_environment, SELECTION)


def test_restricted_profile_rejects_goal_projection_drift(
    selection_environment: SignedGateEnvironment,
) -> None:
    _mutate_generated_profile(
        selection_environment,
        SELECTION,
        "restricted_bundle_index",
        lambda profile: profile.__setitem__(
            "execution_goal_ids",
            ["WORLDCOIN-G038", "WORLDCOIN-G039", "WORLDCOIN-G041"],
        ),
    )

    with pytest.raises(ApprovalVerificationError, match="execution_goal_ids"):
        _verify(selection_environment, SELECTION)


def test_restricted_profile_allows_only_exact_prerequisite_status_projection(
    selection_environment: SignedGateEnvironment,
) -> None:
    def mutate(profile: dict[str, Any]) -> None:
        profile["bundles"]["worldcoin-human-aid/siwe-offline-bootstrap"]["tasks"][0]["status"] = "completed"

    _mutate_generated_profile(
        selection_environment,
        SELECTION,
        "restricted_bundle_index",
        mutate,
    )

    with pytest.raises(ApprovalVerificationError, match="only set status='completed'"):
        _verify(selection_environment, SELECTION)


@pytest.mark.parametrize(
    ("section", "replacement", "message"),
    [
        (
            "validation_commands",
            [
                "python scripts/verify_world_siwe_offline_bootstrap.py --offline --start",
                "python scripts/verify_world_aid_zkp_toolchain.py --offline",
                "python scripts/verify_world_aid_duckdb_bootstrap.py --offline",
            ],
            "start, live, network, or package substitution",
        ),
        (
            "validation_commands",
            [
                "python scripts/verify_world_siwe_offline_bootstrap.py --offline "
                "$(touch data/worldcoin_human_aid/command-injection)",
                "python scripts/verify_world_aid_zkp_toolchain.py --offline",
                "python scripts/verify_world_aid_duckdb_bootstrap.py --offline",
            ],
            "shell expansion or substitution",
        ),
        (
            "validation_commands",
            [
                "python scripts/verify_world_siwe_offline_bootstrap.py --offline; "
                "touch data/worldcoin_human_aid/command-injection",
                "python scripts/verify_world_aid_zkp_toolchain.py --offline",
                "python scripts/verify_world_aid_duckdb_bootstrap.py --offline",
            ],
            "shell control operator",
        ),
        (
            "writable_paths",
            ["data/worldcoin_human_aid/approvals"],
            "approval records",
        ),
        (
            "writable_paths",
            ["scripts"],
            "signed immutable input",
        ),
        (
            "writable_paths",
            ["data/worldcoin_human_aid/agent_supervisor/regenerations/synthetic-reviewed"],
            "signed immutable input",
        ),
        (
            "writable_paths",
            ["data/worldcoin_human_aid/bootstrap"],
            "signed immutable input",
        ),
        (
            "writable_paths",
            ["data/worldcoin_human_aid/gate_evidence/gate-0b-selection"],
            "signed immutable input",
        ),
    ],
)
def test_scope_rejects_command_substitution_and_immutable_writes(
    selection_environment: SignedGateEnvironment,
    section: str,
    replacement: list[str],
    message: str,
) -> None:
    record = copy.deepcopy(selection_environment.selection_record)
    record["scope"][section] = replacement
    _write_json(selection_environment.selection_path, record)

    with pytest.raises(ApprovalVerificationError, match=message):
        _verify(selection_environment, SELECTION)


def test_writable_path_rejects_a_dangling_symlink_component(
    selection_environment: SignedGateEnvironment,
) -> None:
    dangling = selection_environment.root / "future-writable-link"
    dangling.symlink_to("future-writable-target")
    record = copy.deepcopy(selection_environment.selection_record)
    record["scope"]["writable_paths"] = ["future-writable-link/output.json"]
    _write_json(selection_environment.selection_path, record)

    with pytest.raises(ApprovalVerificationError, match="traverses a symlink"):
        _verify(selection_environment, SELECTION)


def test_repository_fsmonitor_hook_cannot_execute_during_verification(
    selection_environment: SignedGateEnvironment,
    tmp_path: Path,
) -> None:
    hook = tmp_path / "fsmonitor-hook"
    marker = tmp_path / "fsmonitor-executed"
    hook.write_text(
        '#!/bin/sh\n: > "$(dirname "$0")/fsmonitor-executed"\nexit 1\n',
        encoding="utf-8",
    )
    hook.chmod(0o755)
    _run("git", "config", "core.fsmonitor", str(hook), cwd=selection_environment.root)

    # Prove the repository-local configuration is executable in an ordinary
    # Git process, then ensure the verifier's fixed Git invocation disables it.
    _run("git", "status", "--porcelain", cwd=selection_environment.root)
    assert marker.is_file()
    marker.unlink()

    assert _verify(selection_environment, SELECTION)["status"] == "verified"
    assert not marker.exists()


@pytest.mark.parametrize(
    ("key", "mutation", "message"),
    [
        (
            "network_deny_canary",
            lambda receipt: receipt["boundary"]["apparmor"].__setitem__("mode", "complain"),
            "enforcing AppArmor",
        ),
        (
            "egress_policy",
            lambda receipt: receipt.__setitem__("external_enforcement", False),
            "externally enforced",
        ),
        (
            "no_live_secrets_attestation",
            lambda receipt: receipt.__setitem__("signing_material_present", True),
            "signing_material_present",
        ),
    ],
)
def test_selection_security_receipts_fail_closed(
    selection_environment: SignedGateEnvironment,
    key: str,
    mutation,
    message: str,
) -> None:
    _mutate_bound_json(
        selection_environment,
        SELECTION,
        "security_evidence",
        key,
        mutation,
    )

    with pytest.raises(ApprovalVerificationError, match=message):
        _verify(selection_environment, SELECTION)


@pytest.mark.parametrize(
    ("receipt_key", "field", "value", "message"),
    [
        ("siwe", "status", "failed", "status must be passed"),
        ("siwe", "offline", False, "offline must be true"),
        ("siwe", "live_actions_authorized", True, "cannot authorize live actions"),
        ("siwe", "real_execution", False, "prove real execution"),
        ("zkp", "goal_id", "WORLDCOIN-G040", "exact goal WORLDCOIN-G039"),
        ("zkp", "network_attempts", 1, "zero network attempts"),
        ("zkp", "cache_mutated", True, "cache was not mutated"),
        (
            "siwe",
            "selection_approval_sha256",
            "sha256:" + "0" * 64,
            "exact selection approval digest",
        ),
        ("duckdb", "single_writer_enforced", False, "single_writer_enforced=true"),
        ("duckdb", "external_access", True, "external_access=false"),
    ],
)
def test_launch_bootstrap_receipt_semantics_fail_closed(
    launch_environment: SignedGateEnvironment,
    receipt_key: str,
    field: str,
    value: Any,
    message: str,
) -> None:
    _mutate_bound_json(
        launch_environment,
        LAUNCH,
        "bootstrap_receipts",
        receipt_key,
        lambda receipt: receipt.__setitem__(field, value),
    )

    with pytest.raises(ApprovalVerificationError, match=message):
        _verify(launch_environment, LAUNCH)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda receipt: receipt["toolchain"].__setitem__(
                "node_sha256",
                "sha256:" + "0" * 64,
            ),
            "toolchain differs",
        ),
        (
            lambda receipt: receipt["inputs"].__setitem__(
                "adapter_sha256",
                "sha256:" + "0" * 64,
            ),
            "inputs differ",
        ),
        (
            lambda receipt: receipt["cache"].__setitem__(
                "reviewed_after_sha256",
                "sha256:" + "0" * 64,
            ),
            "signed reviewed tree",
        ),
        (
            lambda receipt: receipt["network"].__setitem__("attempt_count", 0),
            "truthfully describe",
        ),
        (
            lambda receipt: receipt["network"]["boundary_after"].__setitem__(
                "namespace",
                "net:[1]",
            ),
            "differs from the signed canary",
        ),
        (
            lambda receipt: receipt["network"].__setitem__(
                "external_network_succeeded",
                True,
            ),
            "no external network success",
        ),
        (
            lambda receipt: receipt["smoke_result"].__setitem__("eoa", False),
            "both exact SIWE paths",
        ),
    ],
)
def test_siwe_v2_bootstrap_receipt_fails_closed(
    launch_environment: SignedGateEnvironment,
    mutation,
    message: str,
) -> None:
    _mutate_bound_json(
        launch_environment,
        LAUNCH,
        "bootstrap_receipts",
        "siwe",
        mutation,
    )

    with pytest.raises(ApprovalVerificationError, match=message):
        _verify(launch_environment, LAUNCH)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("started_count", 1, "workers were started"),
        ("active_worker_pids", [1234], "active_worker_pids must be empty"),
        ("launched_task_cids", ["synthetic-launched-cid"], "launched_task_cids must be empty"),
        (
            "bundle_index_path",
            (
                "data/worldcoin_human_aid/agent_supervisor/regenerations/"
                "synthetic-reviewed/launch_profiles/implementation.index.json"
            ),
            "implementation DuckDB index",
        ),
    ],
)
def test_launch_dry_run_manifest_proves_no_start_pids_or_launched_cids(
    launch_environment: SignedGateEnvironment,
    field: str,
    value: Any,
    message: str,
) -> None:
    _mutate_bound_json(
        launch_environment,
        LAUNCH,
        "reviewed_state",
        "dry_run_receipt",
        lambda manifest: manifest.__setitem__(field, value),
    )

    with pytest.raises(ApprovalVerificationError, match=message):
        _verify(launch_environment, LAUNCH)


def test_launch_profile_projects_only_implementation_goals_and_completed_prerequisites(
    launch_environment: SignedGateEnvironment,
) -> None:
    profile_path = (
        launch_environment.root
        / launch_environment.launch_record["reviewed_state"]["implementation_bundle_index"]["path"]
    )
    profile = json.loads(profile_path.read_text(encoding="utf-8"))

    assert profile["execution_goal_ids"] == ["WORLDCOIN-G001", "WORLDCOIN-G003"]
    assert profile["completed_prerequisite_goal_ids"] == sorted(LAUNCH_PREREQUISITE_GOALS)
    for bundle in profile["bundles"].values():
        for task in bundle["tasks"]:
            if task["goal_id"] in LAUNCH_PREREQUISITE_GOALS:
                assert task["status"] == "completed"


def test_digest_drift_is_rejected(
    selection_environment: SignedGateEnvironment,
) -> None:
    objective_path = (
        selection_environment.root / selection_environment.selection_record["reviewed_state"]["objective_heap"]["path"]
    )
    objective_path.write_text("drift\n", encoding="utf-8")

    with pytest.raises(ApprovalVerificationError, match="digest drift"):
        _verify(selection_environment, SELECTION)


def test_scope_uses_one_digest_bound_objective_heap_snapshot(
    selection_environment: SignedGateEnvironment,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    objective_path = (
        selection_environment.root / selection_environment.selection_record["reviewed_state"]["objective_heap"]["path"]
    )
    expected = objective_path.read_bytes()
    original = gate_0b._validate_scope

    def mutate_path_after_snapshot(*args: Any, **kwargs: Any) -> None:
        assert args[5] == expected.decode("utf-8")
        objective_path.write_text("# attacker-controlled replacement\n", encoding="utf-8")
        try:
            original(*args, **kwargs)
        finally:
            objective_path.write_bytes(expected)

    monkeypatch.setattr(gate_0b, "_validate_scope", mutate_path_after_snapshot)
    assert _verify(selection_environment, SELECTION)["status"] == "verified"


def test_untrusted_or_tampered_signature_is_rejected(
    selection_environment: SignedGateEnvironment,
) -> None:
    role = sorted(REQUIRED_ROLES[SELECTION])[0]
    signature_path = selection_environment.selection_path.parent / "signatures" / f"{role}.sshsig"
    signature_path.write_bytes(b"not an ssh signature")

    with pytest.raises(ApprovalVerificationError, match="detached signature rejected"):
        _verify(selection_environment, SELECTION)


def test_unknown_fields_and_noncanonical_actual_path_are_rejected(
    selection_environment: SignedGateEnvironment,
) -> None:
    record = copy.deepcopy(selection_environment.selection_record)
    record["agent_approved"] = True
    _write_json(selection_environment.selection_path, record)
    with pytest.raises(ApprovalVerificationError, match="unknown=.*agent_approved"):
        _verify(selection_environment, SELECTION)

    alternate = selection_environment.root / "approval.json"
    alternate.write_text("{}", encoding="utf-8")
    with pytest.raises(ApprovalVerificationError, match="canonical path"):
        verify_approval(
            repo_root=selection_environment.root,
            phase=SELECTION,
            approval_path=alternate,
            allowed_signers_path=selection_environment.allowed_signers,
            now=NOW,
        )


def test_launch_rejects_selection_digest_drift(
    launch_environment: SignedGateEnvironment,
) -> None:
    launch_environment.selection_path.write_text("{}\n", encoding="utf-8")

    with pytest.raises(ApprovalVerificationError, match="digest drift"):
        _verify(launch_environment, LAUNCH)


def test_operator_trust_store_digest_drift_is_rejected(
    selection_environment: SignedGateEnvironment,
) -> None:
    selection_environment.allowed_signers.chmod(0o644)
    selection_environment.allowed_signers.write_text(
        selection_environment.allowed_signers.read_text(encoding="utf-8") + "# changed\n",
        encoding="utf-8",
    )
    selection_environment.allowed_signers.chmod(0o444)

    with pytest.raises(ApprovalVerificationError, match="trust-store digest drift"):
        _verify(selection_environment, SELECTION)


def test_signature_checks_use_one_sealed_allowed_signers_snapshot(
    selection_environment: SignedGateEnvironment,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = selection_environment.allowed_signers.read_bytes()
    original = gate_0b._verify_signatures

    def mutate_path_after_snapshot(*args: Any, **kwargs: Any) -> None:
        descriptor = args[4]
        assert os.pread(descriptor, len(expected) + 1, 0) == expected
        selection_environment.allowed_signers.chmod(0o644)
        selection_environment.allowed_signers.write_text(
            "attacker@example.invalid ssh-ed25519 AAAA\n",
            encoding="utf-8",
        )
        selection_environment.allowed_signers.chmod(0o444)
        original(*args, **kwargs)

    monkeypatch.setattr(gate_0b, "_verify_signatures", mutate_path_after_snapshot)
    assert _verify(selection_environment, SELECTION)["status"] == "verified"


def test_reviewed_root_must_equal_exact_current_head(
    selection_environment: SignedGateEnvironment,
) -> None:
    (selection_environment.root / "post-review.txt").write_text("later commit\n", encoding="utf-8")
    _commit_all(selection_environment.root, "Advance beyond reviewed root")

    with pytest.raises(ApprovalVerificationError, match="exact current HEAD"):
        _verify(selection_environment, SELECTION)


@pytest.mark.parametrize("drift_kind", ["tracked", "untracked"])
def test_root_worktree_drift_outside_canonical_approval_paths_is_rejected(
    selection_environment: SignedGateEnvironment,
    drift_kind: str,
) -> None:
    if drift_kind == "tracked":
        (selection_environment.root / "tracked-marker.txt").write_text("modified\n", encoding="utf-8")
    else:
        (selection_environment.root / "unexpected-untracked.txt").write_text("unexpected\n", encoding="utf-8")

    with pytest.raises(ApprovalVerificationError, match="root worktree drift"):
        _verify(selection_environment, SELECTION)


def test_in_repository_allowed_signers_store_is_rejected(
    selection_environment: SignedGateEnvironment,
) -> None:
    in_repo_store = selection_environment.root / "operator-trust" / "allowed_signers"
    in_repo_store.parent.mkdir(parents=True)
    in_repo_store.write_bytes(selection_environment.allowed_signers.read_bytes())
    in_repo_store.chmod(0o444)

    with pytest.raises(ApprovalVerificationError, match="outside the repository"):
        verify_approval(
            repo_root=selection_environment.root,
            phase=SELECTION,
            approval_path=selection_environment.selection_path,
            allowed_signers_path=in_repo_store,
            now=NOW,
        )


def test_writable_allowed_signers_store_is_rejected(
    selection_environment: SignedGateEnvironment,
) -> None:
    selection_environment.allowed_signers.chmod(0o644)

    with pytest.raises(ApprovalVerificationError, match="read-only"):
        _verify(selection_environment, SELECTION)


def test_path_cannot_override_trusted_git_or_ssh_keygen(
    selection_environment: SignedGateEnvironment,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    for executable in ("git", "ssh-keygen"):
        fake = fake_bin / executable
        fake.write_text("#!/bin/sh\nexit 99\n", encoding="utf-8")
        fake.chmod(0o755)
    monkeypatch.setenv("PATH", f"{fake_bin}{os.pathsep}{os.environ.get('PATH', '')}")

    assert _verify(selection_environment, SELECTION)["status"] == "verified"
    public_parameters = inspect.signature(verify_approval).parameters
    assert "ssh_keygen" not in public_parameters
    assert "historical_link" not in public_parameters
    assert "verify_linked_selection" not in public_parameters


def test_verification_does_not_modify_bound_inputs(
    selection_environment: SignedGateEnvironment,
) -> None:
    paths = [
        selection_environment.selection_path,
        selection_environment.allowed_signers,
        *[
            selection_environment.selection_path.parent / "signatures" / f"{role}.sshsig"
            for role in REQUIRED_ROLES[SELECTION]
        ],
    ]
    before = {path: _sha256(path) for path in paths}

    _verify(selection_environment, SELECTION)

    assert {path: _sha256(path) for path in paths} == before
