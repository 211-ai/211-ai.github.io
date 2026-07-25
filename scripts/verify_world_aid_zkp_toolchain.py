#!/usr/bin/env python3
"""Verify the unapproved, repository-only WORLDCOIN-G041 ZKP packet.

This verifier is a preparation boundary.  It reads committed text and JSON
only; it never imports or invokes a ZKP implementation, a compiler, a proof
backend, a package manager, a container, or a network client.  A later G039
run may use this contract only after the canonical, human-signed Gate 0B
selection binds every tool and artifact digest.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import sys
import tomllib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_APPROVAL = Path("data/worldcoin_human_aid/approvals/gate-0b-selection/approval.json")
PROPOSAL = Path("data/worldcoin_human_aid/bootstrap/zkp-toolchain-dependency-proposal.json")
G002_INVENTORY = Path("data/worldcoin_human_aid/audit/offline-bootstrap-proposal.json")
DISCOVERY = Path(
    "data/worldcoin_human_aid/agent_supervisor/discovery/"
    "2026-07-24-worldcoin-auto-006-zkp-bootstrap.md"
)
SMOKE_ROOT = Path("tests/world_aid/fixtures/zkp_toolchain_smoke")
SMOKE_SPEC = SMOKE_ROOT / "SMOKE_SPEC.md"
SMOKE_TOML = SMOKE_ROOT / "Nargo.toml"
SMOKE_LOCK = SMOKE_ROOT / "Nargo.lock"
SMOKE_SOURCE = SMOKE_ROOT / "src/main.nr"
STATIC_TEST = Path("tests/world_aid/test_zkp_toolchain_bootstrap_static.py")
RUNTIME_TEST = Path("tests/world_aid/test_zkp_toolchain_bootstrap.py")
HEAP = Path("docs/planning/WORLDCOIN_HUMAN_AID_OBJECTIVE_HEAP.md")

SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:[-+][A-Za-z0-9.]+)?$")
ARCHITECTURES = frozenset({"x86_64", "aarch64"})
FORBIDDEN_PLACEHOLDER = re.compile(r"(?:REPLACE|TODO|TBD|<GATE|<SELECT)", re.IGNORECASE)


class ZkpToolchainVerificationError(ValueError):
    """Raised for any absent, mutable, conflicting, or unsafe contract."""


@dataclass(frozen=True)
class ZkpToolchainSelectionProposal:
    status: str
    architecture: str | None
    backend: str | None
    version: str | None
    tool_digest: str | None
    proposal_digest: str | None
    static_test_digest: str | None
    verifier_digest: str | None
    runtime_test_digest: str | None
    smoke_spec_digest: str | None
    smoke_toml_digest: str | None
    smoke_source_digest: str | None
    smoke_lock_digest: str | None
    execution_owner: str


@dataclass(frozen=True)
class ZkpSmokeSpecification:
    """The locked, bounded smoke contract; it contains no trust decision."""

    status: str
    source: str
    lock: str
    public_input: str
    private_input: str
    max_witness_fields: int
    network: str
    registries: str
    repeat_build: str
    proof_and_verify: str


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ZkpToolchainVerificationError(message)


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ZkpToolchainVerificationError(f"cannot read {path}: {exc}") from exc


def _json_bytes(raw: bytes, context: str) -> dict[str, Any]:
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            _require(key not in result, f"duplicate JSON key in {context}: {key}")
            result[key] = value
        return result

    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=reject_duplicates)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ZkpToolchainVerificationError(
            f"invalid JSON in {context}: {exc}"
        ) from exc
    _require(isinstance(value, dict), f"{context} must contain an object")
    return value


def _json(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ZkpToolchainVerificationError(f"cannot read {path}: {exc}") from exc
    return _json_bytes(raw, str(path))


def _toml(path: Path) -> dict[str, Any]:
    try:
        value = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise ZkpToolchainVerificationError(f"invalid TOML in {path}: {exc}") from exc
    _require(isinstance(value, dict), f"{path} must contain a table")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
    except OSError as exc:
        raise ZkpToolchainVerificationError(f"cannot hash {path}: {exc}") from exc
    return f"sha256:{digest.hexdigest()}"


def _exact_keys(value: Any, expected: set[str], context: str) -> dict[str, Any]:
    _require(isinstance(value, dict), f"{context} must be an object")
    actual = set(value)
    _require(
        actual == expected,
        f"{context} keys differ; missing={sorted(expected - actual)}, "
        f"unknown={sorted(actual - expected)}",
    )
    return value


def _artifact(value: Any, context: str, *, expected_path: Path | None = None) -> dict[str, str]:
    item = _exact_keys(value, {"path", "sha256"}, context)
    path = item["path"]
    digest = item["sha256"]
    _require(isinstance(path, str) and path, f"{context}.path must be non-empty")
    _require(isinstance(digest, str) and SHA256_RE.fullmatch(digest) is not None, f"{context}.sha256 is not exact")
    pure = PurePosixPath(path)
    _require(not pure.is_absolute() and ".." not in pure.parts, f"{context}.path escapes the repository")
    _require("\\" not in path and "\x00" not in path, f"{context}.path is not a repository-relative path")
    if expected_path is not None:
        _require(path == expected_path.as_posix(), f"conflicting path for {context}")
    return {"path": path, "sha256": digest}


def _host_architecture() -> str:
    machine = platform.machine().lower()
    return {"amd64": "x86_64", "arm64": "aarch64"}.get(machine, machine)


def _validate_zkp_selection(
    approval: dict[str, Any],
    root: Path = ROOT,
) -> dict[str, str]:
    """Validate the G041-specific portion of a future Gate 0B record."""
    dependencies = _exact_keys(
        approval.get("dependency_sets"), {"siwe", "zkp", "duckdb"}, "approval.dependency_sets"
    )
    selection = _exact_keys(
        dependencies.get("zkp"),
        {
            "architecture", "backend", "version", "tool", "smoke_source", "smoke_lock",
            "smoke_spec", "smoke_toml",
            "licenses", "provenance", "sbom", "vulnerability_review",
            "deterministic_flags", "resource_bounds",
        },
        "approval.dependency_sets.zkp",
    )
    architecture = selection["architecture"]
    _require(architecture in ARCHITECTURES, "approval has an unsupported ZKP architecture")
    _require(architecture == _host_architecture(), "ZKP architecture does not match the verifier host")
    backend = selection["backend"]
    _require(isinstance(backend, str) and backend and not FORBIDDEN_PLACEHOLDER.search(backend), "ZKP backend is not an exact human selection")
    version = selection["version"]
    _require(isinstance(version, str) and VERSION_RE.fullmatch(version) is not None, "ZKP version is not exact")

    tool = _artifact(selection["tool"], "approval.dependency_sets.zkp.tool")
    tool_path = PurePosixPath(tool["path"])
    _require(tool_path.parts[:4] == ("data", "worldcoin_human_aid", "offline", "zkp"), "ZKP tool is not in the offline tool location")
    _require(tool_path.suffix in {".bin", ".img", ".oci", ".tar", ".gz", ".squashfs"}, "ZKP tool is not a binary or immutable image archive")
    fixture_artifacts: dict[str, dict[str, str]] = {}
    for key, expected in (
        ("smoke_spec", SMOKE_SPEC),
        ("smoke_toml", SMOKE_TOML),
        ("smoke_lock", SMOKE_LOCK),
        ("smoke_source", SMOKE_SOURCE),
    ):
        fixture_artifacts[key] = _artifact(
            selection[key],
            f"approval.dependency_sets.zkp.{key}",
            expected_path=expected,
        )
        _require(
            fixture_artifacts[key]["sha256"] == _sha256(root / expected),
            f"approval.dependency_sets.zkp.{key}.sha256 does not match "
            "the reviewed repository input",
        )
    for key in ("licenses", "provenance", "sbom", "vulnerability_review"):
        item = _artifact(selection[key], f"approval.dependency_sets.zkp.{key}")
        _require(item["path"].startswith("data/worldcoin_human_aid/bootstrap/"), f"ZKP {key} evidence is outside the reviewed bootstrap directory")

    flags = selection["deterministic_flags"]
    _require(isinstance(flags, list) and flags and all(isinstance(flag, str) and flag and not FORBIDDEN_PLACEHOLDER.search(flag) for flag in flags), "ZKP deterministic flags are missing or unpinned")
    flag_text = " ".join(flags).lower()
    _require(not any(term in flag_text for term in ("network", "registry", "download", "update")), "ZKP flags permit network or registry behavior")
    bounds = _exact_keys(selection["resource_bounds"], {"max_seconds", "max_memory_mb", "max_output_bytes"}, "approval.dependency_sets.zkp.resource_bounds")
    for key, lower, upper in (("max_seconds", 1, 3600), ("max_memory_mb", 64, 65536), ("max_output_bytes", 1, 1073741824)):
        _require(isinstance(bounds[key], int) and lower <= bounds[key] <= upper, f"ZKP resource bound {key} is invalid")

    reviewed = approval.get("reviewed_state")
    _require(isinstance(reviewed, dict), "approval.reviewed_state is missing")
    reviewed_artifacts: dict[str, dict[str, str]] = {}
    for key, expected in (
        ("zkp_proposal", PROPOSAL),
        ("zkp_static_test", STATIC_TEST),
        ("zkp_verifier", Path("scripts/verify_world_aid_zkp_toolchain.py")),
        ("zkp_runtime_test", RUNTIME_TEST),
        ("zkp_smoke_spec", SMOKE_SPEC),
        ("zkp_smoke_toml", SMOKE_TOML),
        ("zkp_smoke_lock", SMOKE_LOCK),
        ("zkp_smoke_source", SMOKE_SOURCE),
    ):
        reviewed_artifacts[key] = _artifact(
            reviewed.get(key),
            f"approval.reviewed_state.{key}",
            expected_path=expected,
        )
        _require(
            reviewed_artifacts[key]["sha256"] == _sha256(root / expected),
            f"approval.reviewed_state.{key}.sha256 does not match "
            "the reviewed repository artifact",
        )
    return {
        "architecture": architecture,
        "backend": backend,
        "version": version,
        "tool_digest": tool["sha256"],
        "proposal_digest": reviewed_artifacts["zkp_proposal"]["sha256"],
        "static_test_digest": reviewed_artifacts["zkp_static_test"]["sha256"],
        "verifier_digest": reviewed_artifacts["zkp_verifier"]["sha256"],
        "runtime_test_digest": reviewed_artifacts["zkp_runtime_test"]["sha256"],
        "smoke_spec_digest": fixture_artifacts["smoke_spec"]["sha256"],
        "smoke_toml_digest": fixture_artifacts["smoke_toml"]["sha256"],
        "smoke_source_digest": fixture_artifacts["smoke_source"]["sha256"],
        "smoke_lock_digest": fixture_artifacts["smoke_lock"]["sha256"],
    }


def _validate_approval(root: Path, path: Path, allowed_signers: Path, *, now: datetime | None) -> dict[str, str]:
    """Delegate signatures, expiry, repository state, and digests to Gate 0B."""
    try:
        from scripts.verify_world_aid_gate_0b import SELECTION, ApprovalVerificationError, verify_approval
    except ImportError as exc:
        raise ZkpToolchainVerificationError(f"canonical Gate 0B verifier is unavailable: {exc}") from exc
    canonical = root / CANONICAL_APPROVAL
    _require(path.absolute() == canonical.absolute(), f"approval must use canonical path {CANONICAL_APPROVAL}")
    try:
        before = path.read_bytes()
    except OSError as exc:
        raise ZkpToolchainVerificationError(f"cannot read canonical approval: {exc}") from exc
    try:
        verify_approval(repo_root=root, phase=SELECTION, approval_path=path, allowed_signers_path=allowed_signers, now=now, expected_approval_bytes=before)
    except ApprovalVerificationError as exc:
        raise ZkpToolchainVerificationError(f"canonical Gate 0B approval rejected: {exc}") from exc
    try:
        after = path.read_bytes()
    except OSError as exc:
        raise ZkpToolchainVerificationError(
            f"cannot re-read canonical approval: {exc}"
        ) from exc
    _require(after == before, "canonical Gate 0B approval changed during verification")
    return _validate_zkp_selection(
        _json_bytes(before, str(path)),
        root,
    )


def verify_world_aid_zkp_toolchain(
    root: Path | None = None,
    *,
    approval: Path | None = None,
    allowed_signers: Path | None = None,
    require_approval: bool = False,
    now: datetime | None = None,
) -> ZkpToolchainSelectionProposal:
    """Validate only the committed proposal and smoke-input contract."""
    root = (root or ROOT).resolve()
    required = (PROPOSAL, G002_INVENTORY, DISCOVERY, SMOKE_SPEC, SMOKE_TOML, SMOKE_LOCK, SMOKE_SOURCE, STATIC_TEST, RUNTIME_TEST, HEAP)
    for relative in required:
        _require((root / relative).is_file(), f"required contract file is missing: {relative}")

    selected: dict[str, str] | None = None
    if require_approval or approval is not None:
        _require(approval is not None, "signed Gate 0B-selection approval is required")
        _require(allowed_signers is not None, "canonical signature verification requires an external read-only allowed-signers store")
        selected = _validate_approval(root, approval if approval.is_absolute() else root / approval, allowed_signers if allowed_signers.is_absolute() else root / allowed_signers, now=now)
    else:
        _require(allowed_signers is None, "allowed-signers is invalid without a Gate 0B approval")

    proposal = _json(root / PROPOSAL)
    _exact_keys(proposal, {"schema_version", "status", "goal_id", "authority_statement", "approval", "dependency", "inventory", "inputs", "smoke", "tests", "non_execution_receipt"}, "proposal")
    _require(proposal["schema_version"] == "world-aid-zkp-toolchain-dependency-proposal/v1", "wrong ZKP proposal schema")
    _require(proposal["status"] == "unapproved-inventory-only", "ZKP proposal must remain explicitly unapproved")
    _require(proposal["goal_id"] == "WORLDCOIN-G041", "proposal has conflicting goal ownership")
    _require("NOT APPROVED" in proposal["authority_statement"], "proposal authority limit is not prominent")

    approval_contract = _exact_keys(proposal["approval"], {"required", "binding", "canonical_path", "canonical_schema", "selection_owner", "expires_at", "exceptions"}, "proposal.approval")
    _require(approval_contract == {
        "required": True,
        "binding": "signed Gate 0B-selection",
        "canonical_path": CANONICAL_APPROVAL.as_posix(),
        "canonical_schema": "world-human-aid-gate-0b-selection/v2",
        "selection_owner": "human Gate 0B reviewers",
        "expires_at": None,
        "exceptions": {"required_fields": ["id", "owner", "rationale", "compensating_controls", "expires_at"], "selected": []},
    }, "proposal approval contract is missing human ownership or expiry controls")

    dependency = _exact_keys(proposal["dependency"], {"name", "architecture", "backend", "version", "binary_or_image", "binary_or_image_digest", "licenses", "provenance", "sbom", "vulnerability_disposition", "deterministic_flags", "resource_bounds", "offline_location", "smoke_inputs", "expected_evidence", "expiry", "selection_is_human_owned"}, "proposal.dependency")
    _require(dependency["name"] == "native-zkp-toolchain", "proposal names a conflicting dependency")
    _require(dependency["selection_is_human_owned"] is True, "ZKP selection is not human-owned")
    for key in ("architecture", "backend", "version", "binary_or_image", "binary_or_image_digest", "licenses", "provenance", "sbom", "vulnerability_disposition", "resource_bounds", "offline_location", "expiry"):
        _require(dependency[key] is None, f"proposal manufactured a ZKP selection: {key}")
    _require(dependency["deterministic_flags"] == [], "proposal preselected deterministic flags")
    _require(dependency["smoke_inputs"] == {
        "spec": SMOKE_SPEC.as_posix(),
        "toml": SMOKE_TOML.as_posix(),
        "lock": SMOKE_LOCK.as_posix(),
        "source": SMOKE_SOURCE.as_posix(),
    }, "proposal changed locked smoke inputs")
    _require(len(dependency["expected_evidence"]) >= 5 and all(isinstance(item, str) for item in dependency["expected_evidence"]), "proposal under-specifies expected evidence")

    inventory = _exact_keys(proposal["inventory"], {"source_goal", "source_artifact", "qualified_inventory", "selection_questions", "note"}, "proposal.inventory")
    _require(inventory["source_goal"] == "WORLDCOIN-G002", "proposal does not carry G002 inventory")
    _require(inventory["source_artifact"] == "data/worldcoin_human_aid/audit/offline-bootstrap-proposal.json::inventory.zkp", "proposal has conflicting G002 source")
    source_inventory = _json(root / G002_INVENTORY)["inventory"]["zkp"]
    qualified_text = json.dumps(inventory["qualified_inventory"], sort_keys=True)
    source_text = json.dumps(source_inventory, sort_keys=True)
    for fact in (
        "Cargo command",
        "Rust compiler command",
        "1.93.1",
        "1.96.0-nightly",
        "recorded-prior-smoke-only",
        "observed-unapproved-cache",
        "observed-wrong-architecture-non-aid",
        "Noir/nargo, noirup, and bb commands",
        "missing-required-artifact",
        "unknown-not-inspected",
    ):
        _require(fact in qualified_text and fact in source_text, f"proposal omits qualified G002 ZKP fact: {fact}")
    _require(len(inventory["selection_questions"]) >= 7, "proposal omits required human ZKP selection questions")
    _require("not approval" in inventory["note"].lower(), "inventory note does not preserve the authority boundary")

    inputs = _exact_keys(proposal["inputs"], {"architecture", "tool", "licenses", "provenance", "sbom", "vulnerability_review", "smoke_spec", "smoke_toml", "smoke_lock", "smoke_source", "offline_root", "mutable_paths"}, "proposal.inputs")
    _require(inputs["architecture"] == {"required": True, "selected": None, "allowed": ["x86_64", "aarch64"]}, "architecture requirement is not human-owned")
    for key in ("tool", "licenses", "provenance", "sbom", "vulnerability_review"):
        _require(inputs[key] == {"path": None, "sha256": None, "status": "human evidence required before Gate 0B"}, f"proposal selected {key}")
    for key, expected in (("smoke_spec", SMOKE_SPEC), ("smoke_toml", SMOKE_TOML), ("smoke_lock", SMOKE_LOCK), ("smoke_source", SMOKE_SOURCE)):
        _require(inputs[key] == {
            "path": expected.as_posix(),
            "sha256": _sha256(root / expected),
            "locked": True,
        }, f"proposal changed {key}")
    _require(inputs["offline_root"] == {"path": "data/worldcoin_human_aid/offline/zkp", "read_only": True, "selection_owner": "human Gate 0B reviewers"}, "offline location is mutable or selected")
    _require(inputs["mutable_paths"] == [], "proposal permits mutable selection-bound paths")

    smoke = _exact_keys(proposal["smoke"], {"status", "circuit", "bounded_inputs", "network", "registries", "determinism", "repeat_build", "proof_and_verify", "production_trust"}, "proposal.smoke")
    _require(smoke["status"] == "locked-input-only; not executed", "proposal claims smoke execution")
    _require(smoke["circuit"] == {"toml": SMOKE_TOML.as_posix(), "lock": SMOKE_LOCK.as_posix(), "source": SMOKE_SOURCE.as_posix()}, "smoke circuit paths drifted")
    _require(smoke["bounded_inputs"] == {"public": "7", "private": "7", "max_witness_fields": 2}, "smoke inputs are not locked and bounded")
    _require(smoke["network"] == "denied" and smoke["registries"] == "denied", "smoke does not require network and registry denial")
    _require(smoke["determinism"] == "fixed compiler/backend flags, locale, timezone, and stable output ordering", "smoke determinism contract is incomplete")
    _require(smoke["repeat_build"] == "two isolated builds with byte-identical artifact hashes", "repeat-build evidence is incomplete")
    _require(smoke["proof_and_verify"] == "bounded proof and verify evidence using locked inputs", "proof/verify evidence is incomplete")
    _require("not production trust" in smoke["production_trust"].lower(), "smoke artifact is presented as production trust")
    smoke_specification = ZkpSmokeSpecification(
        status=smoke["status"],
        source=smoke["circuit"]["source"],
        lock=smoke["circuit"]["lock"],
        public_input=smoke["bounded_inputs"]["public"],
        private_input=smoke["bounded_inputs"]["private"],
        max_witness_fields=smoke["bounded_inputs"]["max_witness_fields"],
        network=smoke["network"],
        registries=smoke["registries"],
        repeat_build=smoke["repeat_build"],
        proof_and_verify=smoke["proof_and_verify"],
    )
    _require(smoke_specification.status == "locked-input-only; not executed", "smoke specification is not locked")

    tests = _exact_keys(proposal["tests"], {"static", "runtime_contract", "approved_execution_owner", "fail_closed_on", "forbidden_static_actions", "required_g039_evidence"}, "proposal.tests")
    _require(tests["static"] == STATIC_TEST.as_posix() and tests["runtime_contract"] == RUNTIME_TEST.as_posix(), "proposal names conflicting test contracts")
    _require(tests["approved_execution_owner"] == "G039", "proposal assigns approved execution outside G039")
    for term in ("missing approval", "conflicting approval", "wrong architecture", "digest drift", "unpinned inputs", "unexpected network", "registry configuration", "mutable paths", "production-trust claims", "nondeterminism", "resource-limit breach"):
        _require(term in tests["fail_closed_on"], f"proposal omits fail-closed condition: {term}")
    for term in ("tool import", "tool execution", "package or container action", "subprocess smoke", "download", "secret lookup", "cache mutation", "circuit build", "proof", "verification", "parameter generation"):
        _require(term in tests["forbidden_static_actions"], f"proposal omits static prohibition: {term}")
    _require(set(tests["required_g039_evidence"]) >= {
        "architecture",
        "binary/image digest",
        "selected-backend manifest/lock compatibility",
        "repeat-build hashes",
        "proof result",
        "verify result",
        "network/registry deny",
        "resource bounds",
        "expiry",
    }, "proposal under-specifies G039 evidence")

    non_execution = _exact_keys(proposal["non_execution_receipt"], {"performed", "prohibited", "owner", "status"}, "proposal.non_execution_receipt")
    _require(non_execution["performed"] is False and non_execution["owner"] == "G041" and non_execution["status"] == "not approved", "invalid non-execution receipt")
    for term in ("ZKP tool import or execution", "package or container action", "subprocess smoke", "download", "registry contact", "secret lookup", "cache mutation", "circuit build", "proof generation", "verification", "parameter generation"):
        _require(term in non_execution["prohibited"], f"non-execution receipt omits: {term}")

    spec = _read(root / SMOKE_SPEC)
    toml = _read(root / SMOKE_TOML)
    lock = _read(root / SMOKE_LOCK)
    source = _read(root / SMOKE_SOURCE)
    for text, terms, label in (
        (spec, ("NOT APPROVED", "bounded", "locked", "repeat-build", "proof", "verify", "network", "registry", "G039", "Groth16", "production trust"), "smoke specification"),
        (toml, ("world_aid_zkp_toolchain_smoke", "[dependencies]"), "Nargo.toml"),
        (lock, ("world-aid-zkp-smoke-input-lock/v1", "unapproved-repository-contract", "human-selection-required", "world_aid_zkp_toolchain_smoke"), "Nargo.lock"),
        (source, ("fn main", "assert", "input", "witness"), "smoke source"),
    ):
        for term in terms:
            _require(term.lower() in text.lower(), f"{label} omits required term: {term}")
    _require("<" not in lock and "REPLACE" not in lock.upper(), "smoke lock contains an unpinned placeholder")
    _require("network" not in toml.lower() and "registry" not in toml.lower(), "Nargo.toml adds network or registry configuration")
    manifest = _exact_keys(_toml(root / SMOKE_TOML), {"package", "dependencies"}, "Nargo.toml")
    _require(manifest["dependencies"] == {}, "Nargo.toml must not resolve dependencies")
    _require(
        _exact_keys(
            manifest["package"],
            {"name", "type", "authors"},
            "Nargo.toml.package",
        )
        == {
            "name": "world_aid_zkp_toolchain_smoke",
            "type": "bin",
            "authors": ["211-AI"],
        },
        "Nargo.toml preselects or changes the smoke package contract",
    )
    lock_contract = _exact_keys(
        _toml(root / SMOKE_LOCK),
        {"lock_schema", "status", "tool_lock_format", "package"},
        "Nargo.lock",
    )
    _require(
        {
            "lock_schema": lock_contract["lock_schema"],
            "status": lock_contract["status"],
            "tool_lock_format": lock_contract["tool_lock_format"],
        }
        == {
            "lock_schema": "world-aid-zkp-smoke-input-lock/v1",
            "status": "unapproved-repository-contract",
            "tool_lock_format": "human-selection-required",
        },
        "Nargo.lock claims a selected or tool-generated lock format",
    )
    _require(
        _exact_keys(
            lock_contract["package"],
            {"name", "version", "source", "dependencies"},
            "Nargo.lock.package",
        )
        == {
            "name": "world_aid_zkp_toolchain_smoke",
            "version": "0.1.0",
            "source": "local",
            "dependencies": [],
        },
        "Nargo.lock package contract drifted",
    )
    _require(
        "fn main(input: pub Field, witness: Field)" in source,
        "smoke source does not expose the documented public input",
    )
    _require("production" not in source.lower(), "smoke circuit makes a production-trust claim")

    discovery = _read(root / DISCOVERY)
    for term in ("WORLDCOIN-AUTO-006", "WORLDCOIN-G041", "Canonical command", "unapproved", "G039"):
        _require(term.lower() in discovery.lower(), f"objective discovery evidence omits: {term}")
    heap = _read(root / HEAP)
    _require(DISCOVERY.as_posix() in heap, "objective heap does not link canonical G041 discovery evidence")
    _require("Objective-validation evidence (WORLDCOIN-AUTO-006)" in heap, "objective heap omits G041 validation evidence")

    return ZkpToolchainSelectionProposal(
        status=str(proposal["status"]),
        architecture=selected["architecture"] if selected else None,
        backend=selected["backend"] if selected else None,
        version=selected["version"] if selected else None,
        tool_digest=selected["tool_digest"] if selected else None,
        proposal_digest=selected["proposal_digest"] if selected else None,
        static_test_digest=selected["static_test_digest"] if selected else None,
        verifier_digest=selected["verifier_digest"] if selected else None,
        runtime_test_digest=selected["runtime_test_digest"] if selected else None,
        smoke_spec_digest=selected["smoke_spec_digest"] if selected else None,
        smoke_toml_digest=selected["smoke_toml_digest"] if selected else None,
        smoke_source_digest=selected["smoke_source_digest"] if selected else None,
        smoke_lock_digest=selected["smoke_lock_digest"] if selected else None,
        execution_owner="G039",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approval", type=Path)
    parser.add_argument("--allowed-signers", type=Path)
    parser.add_argument("--offline", action="store_true", help="require repository-only validation")
    args = parser.parse_args(argv)
    if not args.offline:
        print("FAIL CLOSED: --offline is required", file=sys.stderr)
        return 2
    allowed_signers = args.allowed_signers
    if args.approval is not None and allowed_signers is None:
        configured = os.environ.get("WORLD_AID_GATE_0B_ALLOWED_SIGNERS")
        if configured:
            allowed_signers = Path(configured)
    try:
        result = verify_world_aid_zkp_toolchain(approval=args.approval, allowed_signers=allowed_signers, require_approval=args.approval is not None)
    except ZkpToolchainVerificationError as exc:
        print(f"FAIL CLOSED: {exc}", file=sys.stderr)
        return 1
    print(f"PASS: {result.status}; no ZKP runtime action performed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
