#!/usr/bin/env python3
"""Static, non-executing verifier for the World Aid DuckDB proposal.

This module is intentionally dependency-free.  It reads repository files and
JSON only.  It never imports the database package, opens a database, installs a
wheel, runs pip, consults a registry/cache/secret store, or performs a smoke.
The approved runtime verifier is owned by G040 and must be bound by a signed
Gate 0B-selection record before it can execute.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_APPROVAL = Path("data/worldcoin_human_aid/approvals/gate-0b-selection/approval.json")
PROPOSAL = Path("data/worldcoin_human_aid/bootstrap/duckdb-dependency-proposal.json")
G002_INVENTORY = Path("data/worldcoin_human_aid/audit/offline-bootstrap-proposal.json")
DISCOVERY = Path(
    "data/worldcoin_human_aid/agent_supervisor/discovery/"
    "2026-07-24-worldcoin-auto-007-duckdb-bootstrap.md"
)
ADR = Path("docs/adr/WORLD_AID_DUCKDB_STORAGE_ADR.md")
LOCK = Path("requirements-world-aid.lock")
POLICY = Path("wallet_interface/deploy/world-aid-duckdb-runtime.yml")
BACKUP = Path("docs/specs/WORLD_AID_DUCKDB_BACKUP.md")
STATIC_TEST = Path("tests/world_aid/test_duckdb_bootstrap_static.py")
RUNTIME_TEST = Path("tests/world_aid/test_duckdb_bootstrap.py")
HEAP = Path("docs/planning/WORLDCOIN_HUMAN_AID_OBJECTIVE_HEAP.md")

SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
EXACT_VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:[-+][A-Za-z0-9.]+)?$")
WHEEL_RE = re.compile(
    r"^duckdb-(?P<version>[0-9]+\.[0-9]+\.[0-9]+(?:[+][A-Za-z0-9.]+)?)"
    r"-(?P<python>cp[0-9]+)-(?P<abi>cp[0-9]+)"
    r"-(?P<platform>[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)*)\.whl$"
)


class BootstrapVerificationError(ValueError):
    """Raised for any missing, mutable, conflicting, or unsafe contract."""


@dataclass(frozen=True)
class DuckDBRuntimePolicy:
    host: str
    writers: int
    boundary: str
    external_access: bool
    autoinstall: bool
    autoload: bool
    community_extensions: bool
    network: str
    index: str
    shared_filesystem: bool
    multi_host: bool
    direct_worker_writes: bool
    raw_database_path_exposed: bool
    wheelhouse_mutable: bool
    lock_mutable: bool
    path_policy: str
    application_encryption: str


@dataclass(frozen=True)
class DuckDBSelectionProposal:
    status: str
    version: str | None
    wheel_filename: str | None
    sha256: str | None
    cpython_abi: str | None
    platform_tag: str | None
    policy: DuckDBRuntimePolicy


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise BootstrapVerificationError(f"cannot read {path}: {exc}") from exc


def _json_bytes(raw: bytes, context: str) -> dict[str, Any]:
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            _require(key not in result, f"duplicate JSON key in {context}: {key}")
            result[key] = value
        return result

    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=reject_duplicates)
    except UnicodeDecodeError as exc:
        raise BootstrapVerificationError(f"invalid UTF-8 in {context}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise BootstrapVerificationError(f"invalid JSON in {context}: {exc}") from exc
    if not isinstance(value, dict):
        raise BootstrapVerificationError(f"{context} must contain an object")
    return value


def _json(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise BootstrapVerificationError(f"cannot read {path}: {exc}") from exc
    return _json_bytes(raw, str(path))


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise BootstrapVerificationError(message)


def _exact_keys(value: Any, expected: set[str], context: str) -> dict[str, Any]:
    _require(isinstance(value, dict), f"{context} must be an object")
    actual = set(value)
    _require(
        actual == expected,
        f"{context} keys differ; missing={sorted(expected - actual)}, "
        f"unknown={sorted(actual - expected)}",
    )
    return value


def _yaml_scalar(text: str, key: str) -> str | None:
    matches = re.findall(rf"(?m)^\s*{re.escape(key)}:\s*([^#\n]+)", text)
    return matches[-1].strip().strip("'\"") if matches else None


def _policy(text: str) -> DuckDBRuntimePolicy:
    def boolean(key: str) -> bool:
        value = _yaml_scalar(text, key)
        _require(value in {"true", "false"}, f"runtime policy has invalid {key}")
        return value == "true"

    return DuckDBRuntimePolicy(
        host=_yaml_scalar(text, "host") or "",
        writers=int(_yaml_scalar(text, "expected") or "-1"),
        boundary=_yaml_scalar(text, "kind") or "",
        external_access=boolean("enable_external_access"),
        autoinstall=boolean("autoinstall_known_extensions"),
        autoload=boolean("autoload_known_extensions"),
        community_extensions=boolean("allow_community_extensions"),
        network=_yaml_scalar(text, "network") or "",
        index=_yaml_scalar(text, "index") or "",
        shared_filesystem=boolean("shared_filesystem"),
        multi_host=boolean("multi_host"),
        direct_worker_writes=boolean("direct_worker_writes"),
        raw_database_path_exposed=boolean("raw_database_path_exposed_to_clients"),
        wheelhouse_mutable=boolean("wheelhouse_mutable"),
        lock_mutable=boolean("lock_mutable"),
        path_policy=_yaml_scalar(text, "path_policy") or "",
        application_encryption=_yaml_scalar(text, "database_file_is_application_encryption") or "",
    )


def _validate_duckdb_selection(approval: dict[str, Any]) -> dict[str, str]:
    """Apply the G042-specific checks missing from the canonical gate schema."""
    dependencies = _exact_keys(
        approval.get("dependency_sets"),
        {"siwe", "zkp", "duckdb"},
        "approval.dependency_sets",
    )
    selection = _exact_keys(
        dependencies.get("duckdb"),
        {
            "python_version",
            "platform",
            "duckdb_version",
            "wheels",
            "wheelhouse",
            "requirements_lock",
            "runtime_policy",
            "backup_policy",
            "licenses",
            "provenance",
            "sbom",
            "vulnerability_review",
            "topology",
            "database_file_encryption",
            "extension_auto_install",
            "extension_auto_load",
            "external_access",
            "community_extensions",
            "extension_directory",
        },
        "approval.dependency_sets.duckdb",
    )
    version = selection["duckdb_version"]
    _require(isinstance(version, str) and EXACT_VERSION_RE.fullmatch(version) is not None, "DuckDB version is not exact")
    python_version = selection["python_version"]
    _require(
        isinstance(python_version, str)
        and re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", python_version) is not None,
        "approval has an invalid exact Python version",
    )
    expected_abi = "cp" + "".join(python_version.split(".")[:2])
    platform_tag = selection["platform"]
    _require(
        isinstance(platform_tag, str)
        and re.fullmatch(r"[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)*", platform_tag) is not None,
        "approval platform must be one exact wheel platform tag",
    )

    wheels = selection["wheels"]
    _require(isinstance(wheels, list) and len(wheels) == 1, "DuckDB approval must bind exactly one wheel")
    wheel = _exact_keys(wheels[0], {"path", "sha256"}, "approval.dependency_sets.duckdb.wheels[0]")
    wheel_path = wheel["path"]
    _require(isinstance(wheel_path, str), "approved wheel path must be a string")
    match = WHEEL_RE.fullmatch(Path(wheel_path).name)
    _require(match is not None, "approved wheel filename is not an exact DuckDB CPython wheel")
    assert match is not None
    _require(match.group("version") == version, "DuckDB wheel filename/version conflict")
    _require(match.group("python") == expected_abi, "DuckDB wheel Python tag does not match exact CPython version")
    _require(match.group("abi") == expected_abi, "DuckDB wheel ABI tag does not match exact CPython ABI")
    _require(match.group("platform") == platform_tag, "DuckDB wheel platform tag conflicts with approval.platform")
    _require(SHA256_RE.fullmatch(str(wheel["sha256"])) is not None, "DuckDB wheel has no exact SHA-256")

    wheelhouse = _exact_keys(
        selection["wheelhouse"],
        {"path", "read_only"},
        "approval.dependency_sets.duckdb.wheelhouse",
    )
    _require(wheelhouse["read_only"] is True, "approved wheelhouse is mutable")
    wheelhouse_path = wheelhouse["path"]
    _require(isinstance(wheelhouse_path, str), "approved wheelhouse path must be a string")
    _require(
        Path(wheelhouse_path) in Path(wheel_path).parents,
        "approved DuckDB wheel is outside the read-only wheelhouse",
    )

    for key, expected_path in (
        ("requirements_lock", LOCK.as_posix()),
        ("runtime_policy", POLICY.as_posix()),
        ("backup_policy", BACKUP.as_posix()),
    ):
        artifact = _exact_keys(selection[key], {"path", "sha256"}, f"approval.dependency_sets.duckdb.{key}")
        _require(artifact["path"] == expected_path, f"conflicting DuckDB approval path for {key}")
        _require(SHA256_RE.fullmatch(str(artifact["sha256"])) is not None, f"invalid {key} digest")

    reviewed = approval["reviewed_state"]
    for key, expected_path in (
        ("storage_adr", ADR.as_posix()),
        ("duckdb_verifier", Path("scripts/verify_world_aid_duckdb_bootstrap.py").as_posix()),
        ("duckdb_runtime_test", RUNTIME_TEST.as_posix()),
    ):
        artifact = reviewed[key]
        _require(artifact["path"] == expected_path, f"conflicting reviewed_state path for {key}")

    _require(selection["topology"] == "single-host-single-writer-coordinator", "approval permits multiple writers")
    _require(
        selection["database_file_encryption"] == "encrypted-volume-plus-application-envelope-encryption",
        "approval incorrectly treats DuckDB as application encryption",
    )
    for key in ("extension_auto_install", "extension_auto_load", "external_access", "community_extensions"):
        _require(selection[key] is False, f"approval enables prohibited setting: {key}")
    _require(
        selection["extension_directory"] == {"mode": "disabled", "path": "", "allowlist": []},
        "G042 requires the DuckDB extension directory to be strictly disabled",
    )
    return {
        "version": version,
        "wheel_filename": Path(wheel_path).name,
        "sha256": wheel["sha256"],
        "cpython_abi": f"{expected_abi}-{expected_abi}",
        "platform_tag": platform_tag,
    }


def _validate_approval(
    root: Path,
    path: Path,
    allowed_signers: Path,
    *,
    now: datetime | None,
) -> dict[str, str]:
    """Verify the canonical signed record, then cross-bind DuckDB specifics."""
    try:
        from scripts.verify_world_aid_gate_0b import (
            SELECTION,
            ApprovalVerificationError,
            verify_approval,
        )
    except ImportError as exc:
        raise BootstrapVerificationError(f"canonical Gate 0B verifier is unavailable: {exc}") from exc

    canonical = root / CANONICAL_APPROVAL
    _require(path.absolute() == canonical.absolute(), f"approval must use canonical path {CANONICAL_APPROVAL}")
    try:
        before = path.read_bytes()
    except OSError as exc:
        raise BootstrapVerificationError(f"cannot read canonical approval: {exc}") from exc
    try:
        verify_approval(
            repo_root=root,
            phase=SELECTION,
            approval_path=path,
            allowed_signers_path=allowed_signers,
            now=now,
        )
    except ApprovalVerificationError as exc:
        raise BootstrapVerificationError(f"canonical Gate 0B approval rejected: {exc}") from exc
    try:
        after = path.read_bytes()
    except OSError as exc:
        raise BootstrapVerificationError(f"cannot re-read canonical approval: {exc}") from exc
    _require(before == after, "canonical Gate 0B approval changed during verification")
    return _validate_duckdb_selection(_json_bytes(before, str(path)))


def verify_world_aid_duckdb_bootstrap(
    root: Path | None = None,
    *,
    approval: Path | None = None,
    allowed_signers: Path | None = None,
    require_approval: bool = False,
    now: datetime | None = None,
) -> DuckDBSelectionProposal:
    """Validate the proposal contract without performing any runtime action."""
    root = (root or ROOT).resolve()
    files = {
        p: root / p
        for p in (
            PROPOSAL,
            G002_INVENTORY,
            DISCOVERY,
            ADR,
            LOCK,
            POLICY,
            BACKUP,
            STATIC_TEST,
            RUNTIME_TEST,
            HEAP,
        )
    }
    for relative, path in files.items():
        _require(path.is_file(), f"required contract file is missing: {relative}")

    selected: dict[str, str] | None = None
    if require_approval or approval is not None:
        _require(approval is not None, "signed Gate 0B-selection approval is required")
        _require(
            allowed_signers is not None,
            "canonical signature verification requires an external read-only allowed-signers store",
        )
        approval_path = approval if approval.is_absolute() else root / approval
        selected = _validate_approval(
            root,
            approval_path,
            allowed_signers if allowed_signers.is_absolute() else allowed_signers.absolute(),
            now=now,
        )
    else:
        _require(allowed_signers is None, "allowed-signers is invalid without a Gate 0B approval")

    proposal = _json(files[PROPOSAL])
    _exact_keys(
        proposal,
        {
            "schema_version",
            "status",
            "goal_id",
            "authority_statement",
            "approval",
            "dependency",
            "inventory",
            "inputs",
            "runtime_policy",
            "tests",
            "non_execution_receipt",
        },
        "proposal",
    )
    _require(proposal["schema_version"] == "world-aid-duckdb-dependency-proposal/v1", "wrong proposal schema")
    _require(proposal.get("status") == "unapproved-inventory-only", "proposal must remain explicitly unapproved")
    _require(proposal["goal_id"] == "WORLDCOIN-G042", "proposal has conflicting goal ownership")
    _require("NOT APPROVED" in proposal["authority_statement"], "proposal authority limit is not prominent")
    approval_contract = _exact_keys(
        proposal["approval"],
        {
            "required",
            "binding",
            "canonical_path",
            "canonical_schema",
            "selection_owner",
            "expires_at",
            "exceptions",
        },
        "proposal.approval",
    )
    _require(approval_contract["required"] is True, "proposal does not require approval")
    _require(approval_contract["canonical_path"] == CANONICAL_APPROVAL.as_posix(), "proposal names a conflicting approval")
    _require(
        approval_contract["canonical_schema"] == "world-human-aid-gate-0b-selection/v1",
        "proposal names a conflicting approval schema",
    )
    _require(approval_contract["expires_at"] is None, "proposal manufactured an approval expiry")
    _require(
        approval_contract["exceptions"]
        == {
            "required_fields": [
                "id",
                "owner",
                "rationale",
                "compensating_controls",
                "expires_at",
            ],
            "selected": [],
        },
        "proposal manufactured or under-specified an exception",
    )
    dependency = proposal.get("dependency")
    _exact_keys(
        dependency,
        {
            "name",
            "version",
            "wheel_filename",
            "sha256",
            "cpython_abi",
            "platform_tag",
            "license_evidence",
            "provenance_evidence",
            "sbom_evidence",
            "vulnerability_disposition",
            "selection_is_human_owned",
        },
        "proposal.dependency",
    )
    _require(dependency.get("selection_is_human_owned") is True, "DuckDB selection is not human-owned")
    for key in ("version", "wheel_filename", "sha256", "cpython_abi", "platform_tag"):
        _require(dependency.get(key) is None, f"proposal manufactured a DuckDB selection: {key}")

    inventory = _exact_keys(
        proposal["inventory"],
        {
            "source_goal",
            "source_artifact",
            "declarations",
            "observed_metadata",
            "version_conflict",
            "not_observed_or_unselected",
            "note",
        },
        "proposal.inventory",
    )
    _require(inventory["source_goal"] == "WORLDCOIN-G002", "proposal does not carry G002 inventory")
    declarations = inventory["declarations"]
    _require(
        isinstance(declarations, list)
        and any(
            item.get("version") == ">=1.4.0"
            and item.get("state") == "declared-unapproved"
            and item.get("evidence") == "pyproject.toml::project.dependencies[duckdb]"
            for item in declarations
        ),
        "proposal omits the qualified root DuckDB declaration",
    )
    observed = inventory["observed_metadata"]
    observed_versions = {
        item.get("version"): item.get("state")
        for item in observed
        if isinstance(item, dict)
    }
    _require(
        observed_versions == {
            "1.4.3": "observed-install-metadata-unapproved",
            "1.5.2": "observed-alternate-environment-metadata-unapproved",
        },
        "proposal omits or changes G002's conflicting observed DuckDB metadata",
    )
    _require(
        inventory["version_conflict"] == {
            "present": True,
            "values": [
                "declared >=1.4.0",
                "observed system-user-site 1.4.3",
                "observed inactive workspace 1.5.2",
            ],
            "disposition": "unresolved-human-selection-required",
            "must_not_infer": "No observed or declared version is the approved DuckDB selection.",
        },
        "proposal does not leave the G002 version conflict human-owned",
    )
    upstream = _json(files[G002_INVENTORY])["inventory"]["python_duckdb"]
    upstream_text = json.dumps(upstream, sort_keys=True)
    for required_fact in (
        ">=1.4.0",
        "1.4.3",
        "1.5.2",
        "observed-install-metadata",
        "observed-alternate-environment-metadata",
    ):
        _require(required_fact in upstream_text, f"G002 upstream inventory lacks required fact: {required_fact}")

    inputs = _exact_keys(
        proposal["inputs"],
        {
            "read_only_wheelhouse",
            "requirements_lock",
            "reviewed_adr",
            "runtime_policy",
            "backup_policy",
            "storage_policy",
            "encryption_policy",
        },
        "proposal.inputs",
    )
    _require(inputs["read_only_wheelhouse"] == {"path": None, "read_only": True, "selection_owner": "human-reviewers"}, "wheelhouse proposal is mutable or selected")
    for key, path in (
        ("requirements_lock", LOCK),
        ("reviewed_adr", ADR),
        ("runtime_policy", POLICY),
        ("backup_policy", BACKUP),
    ):
        _require(inputs[key] == {"path": path.as_posix(), "sha256": None}, f"proposal manufactured or changed {key}")
    policy_data = _exact_keys(
        proposal.get("runtime_policy"),
        {
            "enable_external_access",
            "autoinstall_known_extensions",
            "autoload_known_extensions",
            "allow_community_extensions",
            "extension_directory",
            "network",
            "index",
            "dns",
            "http",
            "extension_registry",
            "topology",
            "client_boundary",
            "database_paths",
            "direct_worker_writes",
            "shared_filesystem",
            "application_encryption",
        },
        "proposal.runtime_policy",
    )
    _require(policy_data.get("enable_external_access") is False, "external access is enabled")
    for key in ("autoinstall_known_extensions", "autoload_known_extensions", "allow_community_extensions"):
        _require(policy_data.get(key) is False, f"extension setting enabled: {key}")
    for key in ("network", "index", "dns", "http", "extension_registry"):
        _require(policy_data.get(key) == "denied", f"proposal does not deny {key}")
    _require(
        policy_data.get("extension_directory") == {"mode": "disabled", "path": "", "allowlist": []},
        "proposal does not disable the extension directory",
    )
    _require(policy_data.get("topology") == "single-host-exactly-one-writer", "topology is not exactly one local writer")
    _require(policy_data.get("client_boundary") == "authenticated-local-ipc", "client boundary is not local IPC")
    _require(policy_data.get("direct_worker_writes") is False and policy_data.get("shared_filesystem") is False, "unsafe writer/path policy")
    _require("G033" in str(policy_data.get("application_encryption")), "encryption ownership is not handed to G033")

    tests = _exact_keys(
        proposal["tests"],
        {
            "static",
            "runtime_contract",
            "approved_execution_owner",
            "required_real_smoke_boundary",
            "fail_closed_on",
            "g033_exclusions",
        },
        "proposal.tests",
    )
    _require(tests["static"] == STATIC_TEST.as_posix(), "proposal names a conflicting static contract")
    _require(tests["runtime_contract"] == RUNTIME_TEST.as_posix(), "proposal names a conflicting runtime contract")
    _require(tests["approved_execution_owner"] == "G040", "proposal assigns runtime execution outside G040")
    for term in (
        "transaction commit",
        "rollback",
        "uniqueness",
        "compare-and-swap",
        "atomic outbox",
        "direct second-writer rejection",
        "checkpoint",
        "crash and reopen",
        "raw opaque backup and restore",
        "corruption detection",
        "opaque synthetic payload round trip",
        "database WAL and temporary-data teardown",
    ):
        _require(term in tests["required_real_smoke_boundary"], f"proposal omits G040 smoke check: {term}")
    _require("skipped real DuckDB execution" in tests["fail_closed_on"], "proposal permits skipped execution")
    _require(
        set(tests["g033_exclusions"])
        == {
            "application envelope-encryption implementation",
            "plaintext-marker absence",
            "encrypted authenticated backup",
            "key rotation retention and deletion",
        },
        "proposal blurs the G040/G033 boundary",
    )
    non_execution = _exact_keys(
        proposal["non_execution_receipt"],
        {"performed", "prohibited", "owner"},
        "proposal.non_execution_receipt",
    )
    _require(non_execution["performed"] is False and non_execution["owner"] == "G042", "invalid non-execution receipt")
    for prohibited in (
        "DuckDB import or execution",
        "database creation or open",
        "wheel install",
        "pip execution",
        "index or extension request",
        "cache access or mutation",
        "secret lookup",
        "runtime smoke",
    ):
        _require(prohibited in non_execution["prohibited"], f"non-execution receipt omits: {prohibited}")

    policy = _policy(_read(files[POLICY]))
    _require(policy.host == "single-local-host" and policy.writers == 1, "runtime policy does not enforce one local writer")
    _require(policy.boundary == "authenticated-local-ipc", "runtime boundary is not authenticated local IPC")
    _require(not any((policy.external_access, policy.autoinstall, policy.autoload, policy.community_extensions)), "runtime enables external or extension access")
    _require(policy.network == "denied" and policy.index == "denied", "runtime index/network policy is unsafe")
    _require(
        not any(
            (
                policy.shared_filesystem,
                policy.multi_host,
                policy.direct_worker_writes,
                policy.raw_database_path_exposed,
                policy.wheelhouse_mutable,
                policy.lock_mutable,
            )
        ),
        "runtime exposes mutable, shared, direct, or multi-host paths",
    )
    _require(policy.path_policy == "local-approved-encrypted-volume-only", "runtime permits a non-local database path")
    _require(policy.application_encryption == "false", "DuckDB was incorrectly claimed to provide application encryption")

    lock = _read(files[LOCK])
    _require("--no-index" in lock and "--require-hashes" in lock and "HUMAN_SELECTION_REQUIRED" in lock, "lock is not an unapproved offline hash contract")
    _require("duckdb==<GATE-0B-SELECTION-REQUIRED>" in lock, "lock manufactured an exact DuckDB version")
    adr = _read(files[ADR])
    backup = _read(files[BACKUP])
    for text, terms, label in (
        (adr, ("single-host", "single-writer", "Gate 0B", "not approve a DuckDB version", "envelope-encrypted"), "ADR"),
        (
            backup,
            (
                "NOT APPROVED",
                "raw opaque",
                "backup",
                "restore",
                "G033",
                "plaintext-marker",
                "DuckDB file storage is never described as application encryption",
            ),
            "backup policy",
        ),
    ):
        for term in terms:
            _require(term in text, f"{label} omits required term: {term}")
    discovery = _read(files[DISCOVERY])
    for term in ("WORLDCOIN-AUTO-007", "WORLDCOIN-G042", "Canonical command", "unapproved"):
        _require(term in discovery, f"objective discovery evidence omits: {term}")
    heap = _read(files[HEAP])
    _require(DISCOVERY.as_posix() in heap, "objective heap does not link canonical G042 discovery evidence")

    return DuckDBSelectionProposal(
        status=str(proposal["status"]),
        version=selected["version"] if selected else None,
        wheel_filename=selected["wheel_filename"] if selected else None,
        sha256=selected["sha256"] if selected else None,
        cpython_abi=selected["cpython_abi"] if selected else None,
        platform_tag=selected["platform_tag"] if selected else None,
        policy=policy,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approval", type=Path)
    parser.add_argument("--allowed-signers", type=Path)
    parser.add_argument("--offline", action="store_true", help="assert repository-only validation; never runs a database")
    args = parser.parse_args(argv)
    if not args.offline:
        print("FAIL CLOSED: --offline is required", file=sys.stderr)
        return 2
    allowed_signers = args.allowed_signers
    if args.approval is not None and allowed_signers is None:
        configured_trust = os.environ.get("WORLD_AID_GATE_0B_ALLOWED_SIGNERS")
        if configured_trust:
            allowed_signers = Path(configured_trust)
    try:
        result = verify_world_aid_duckdb_bootstrap(
            approval=args.approval,
            allowed_signers=allowed_signers,
            require_approval=args.approval is not None,
        )
    except BootstrapVerificationError as exc:
        print(f"FAIL CLOSED: {exc}", file=sys.stderr)
        return 1
    print(f"PASS: {result.status}; no DuckDB runtime action performed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
