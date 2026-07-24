"""Repository-only acceptance contract for WORLDCOIN-G042.

The guarded G042 command runs this file, not the G040 runtime contract. These
tests read repository files and exercise in-memory validation only. They never
import DuckDB, create a database, inspect caches/secrets, install a wheel, run
pip, or execute the G040 smoke.
"""

from __future__ import annotations

import ast
import copy
import json
from pathlib import Path
from typing import Any, Callable

from scripts.verify_world_aid_duckdb_bootstrap import (
    BootstrapVerificationError,
    _validate_duckdb_selection,
    verify_world_aid_duckdb_bootstrap,
)

ROOT = Path(__file__).resolve().parents[2]
PROPOSAL = ROOT / "data/worldcoin_human_aid/bootstrap/duckdb-dependency-proposal.json"
G002 = ROOT / "data/worldcoin_human_aid/audit/offline-bootstrap-proposal.json"
DISCOVERY = (
    ROOT
    / "data/worldcoin_human_aid/agent_supervisor/discovery"
    / "2026-07-24-worldcoin-auto-007-duckdb-bootstrap.md"
)
HEAP = ROOT / "docs/planning/WORLDCOIN_HUMAN_AID_OBJECTIVE_HEAP.md"
VERIFIER = ROOT / "scripts/verify_world_aid_duckdb_bootstrap.py"
RUNTIME_CONTRACT = ROOT / "tests/world_aid/test_duckdb_bootstrap.py"


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _selection() -> dict[str, Any]:
    wheel = (
        "data/worldcoin_human_aid/offline/wheels/"
        "duckdb-1.4.3-cp312-cp312-manylinux_2_28_x86_64.whl"
    )
    artifact = lambda path: {"path": path, "sha256": "sha256:" + "1" * 64}
    return {
        "reviewed_state": {
            "storage_adr": artifact("docs/adr/WORLD_AID_DUCKDB_STORAGE_ADR.md"),
            "duckdb_verifier": artifact("scripts/verify_world_aid_duckdb_bootstrap.py"),
            "duckdb_runtime_test": artifact("tests/world_aid/test_duckdb_bootstrap.py"),
        },
        "dependency_sets": {
            "siwe": {},
            "zkp": {},
            "duckdb": {
                "python_version": "3.12.3",
                "platform": "manylinux_2_28_x86_64",
                "duckdb_version": "1.4.3",
                "wheels": [artifact(wheel)],
                "wheelhouse": {
                    "path": "data/worldcoin_human_aid/offline/wheels",
                    "read_only": True,
                },
                "requirements_lock": artifact("requirements-world-aid.lock"),
                "runtime_policy": artifact(
                    "wallet_interface/deploy/world-aid-duckdb-runtime.yml"
                ),
                "backup_policy": artifact("docs/specs/WORLD_AID_DUCKDB_BACKUP.md"),
                "licenses": artifact(
                    "data/worldcoin_human_aid/bootstrap/duckdb-licenses.json"
                ),
                "provenance": artifact(
                    "data/worldcoin_human_aid/bootstrap/duckdb-provenance.json"
                ),
                "sbom": artifact(
                    "data/worldcoin_human_aid/bootstrap/duckdb-sbom.json"
                ),
                "vulnerability_review": artifact(
                    "data/worldcoin_human_aid/bootstrap/duckdb-vulnerability-review.json"
                ),
                "topology": "single-host-single-writer-coordinator",
                "database_file_encryption": (
                    "encrypted-volume-plus-application-envelope-encryption"
                ),
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
        },
    }


def _assert_selection_rejected(
    mutate: Callable[[dict[str, Any]], None],
    message: str,
) -> None:
    approval = copy.deepcopy(_selection())
    mutate(approval)
    try:
        _validate_duckdb_selection(approval)
    except BootstrapVerificationError as exc:
        assert message in str(exc)
    else:
        raise AssertionError("unsafe or conflicting DuckDB selection was accepted")


def test_proposal_carries_exact_qualified_g002_inventory_without_selecting() -> None:
    proposal = _read_json(PROPOSAL)
    assert proposal["status"] == "unapproved-inventory-only"
    assert proposal["goal_id"] == "WORLDCOIN-G042"
    assert "NOT APPROVED" in proposal["authority_statement"]
    dependency = proposal["dependency"]
    assert dependency["selection_is_human_owned"] is True
    assert all(
        dependency[key] is None
        for key in (
            "version",
            "wheel_filename",
            "sha256",
            "cpython_abi",
            "platform_tag",
            "license_evidence",
            "provenance_evidence",
            "sbom_evidence",
            "vulnerability_disposition",
        )
    )

    inventory = proposal["inventory"]
    assert inventory["source_goal"] == "WORLDCOIN-G002"
    assert inventory["declarations"][0]["version"] == ">=1.4.0"
    assert inventory["declarations"][0]["state"] == "declared-unapproved"
    assert {
        (item["version"], item["state"]) for item in inventory["observed_metadata"]
    } == {
        ("1.4.3", "observed-install-metadata-unapproved"),
        ("1.5.2", "observed-alternate-environment-metadata-unapproved"),
    }
    assert inventory["version_conflict"]["present"] is True
    assert inventory["version_conflict"]["disposition"] == (
        "unresolved-human-selection-required"
    )

    upstream = json.dumps(
        _read_json(G002)["inventory"]["python_duckdb"],
        sort_keys=True,
    )
    for fact in (
        ">=1.4.0",
        "DuckDB system-user-site distribution metadata",
        "1.4.3",
        "inactive workspace virtual environment",
        "DuckDB 1.5.2 distribution metadata",
        "observed-install-metadata",
        "observed-alternate-environment-metadata",
    ):
        assert fact in upstream


def test_repository_only_verifier_passes_unapproved_preparation() -> None:
    result = verify_world_aid_duckdb_bootstrap(ROOT)
    assert result.status == "unapproved-inventory-only"
    assert result.version is None
    assert result.wheel_filename is None
    assert result.sha256 is None
    assert result.cpython_abi is None
    assert result.platform_tag is None
    assert result.policy.writers == 1
    assert result.policy.boundary == "authenticated-local-ipc"
    assert result.policy.path_policy == "local-approved-encrypted-volume-only"


def test_approved_mode_requires_both_canonical_record_and_external_trust() -> None:
    try:
        verify_world_aid_duckdb_bootstrap(ROOT, require_approval=True)
    except BootstrapVerificationError as exc:
        assert "approval" in str(exc)
    else:
        raise AssertionError("approved mode accepted without an approval")

    try:
        verify_world_aid_duckdb_bootstrap(
            ROOT,
            approval=Path(
                "data/worldcoin_human_aid/approvals/gate-0b-selection/approval.json"
            ),
        )
    except BootstrapVerificationError as exc:
        assert "allowed-signers" in str(exc)
    else:
        raise AssertionError("approved mode accepted without signature trust")


def test_exact_wheel_name_hash_abi_platform_and_paths_are_cross_bound() -> None:
    selected = _validate_duckdb_selection(_selection())
    assert selected == {
        "version": "1.4.3",
        "wheel_filename": (
            "duckdb-1.4.3-cp312-cp312-manylinux_2_28_x86_64.whl"
        ),
        "sha256": "sha256:" + "1" * 64,
        "cpython_abi": "cp312-cp312",
        "platform_tag": "manylinux_2_28_x86_64",
    }

    _assert_selection_rejected(
        lambda approval: approval["dependency_sets"]["duckdb"]["wheels"][0].update(
            path=(
                "data/worldcoin_human_aid/offline/wheels/"
                "duckdb-1.4.3-cp311-cp311-manylinux_2_28_x86_64.whl"
            )
        ),
        "Python tag",
    )
    _assert_selection_rejected(
        lambda approval: approval["dependency_sets"]["duckdb"].update(
            platform="manylinux_2_27_x86_64"
        ),
        "platform tag conflicts",
    )
    _assert_selection_rejected(
        lambda approval: approval["dependency_sets"]["duckdb"].update(
            requirements_lock={
                "path": "requirements.txt",
                "sha256": "sha256:" + "1" * 64,
            }
        ),
        "conflicting DuckDB approval path",
    )
    _assert_selection_rejected(
        lambda approval: approval["dependency_sets"]["duckdb"]["wheelhouse"].update(
            read_only=False
        ),
        "mutable",
    )


def test_canonical_gate_verifier_owns_signatures_expiry_digests_and_git_state() -> None:
    source = VERIFIER.read_text(encoding="utf-8")
    tree = ast.parse(source)
    calls = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "verify_approval" in calls
    assert "allowed_signers_path" in source
    assert "phase=SELECTION" in source
    assert "before == after" in source
    assert "CANONICAL_APPROVAL" in source

    canonical = (
        ROOT / "scripts/verify_world_aid_gate_0b.py"
    ).read_text(encoding="utf-8")
    for term in (
        "_validate_submodule_commits",
        "_verify_artifact",
        "_validate_reviewers",
        "_validate_exceptions",
        "_verify_signatures",
        "record is stale or expired",
        "root_commit must equal the exact current HEAD",
    ):
        assert term in canonical


def test_static_lane_has_no_duckdb_or_side_effecting_runtime_imports_calls() -> None:
    source = VERIFIER.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert "duckdb" not in imported
    assert "subprocess" not in imported
    assert "socket" not in imported
    assert "urllib" not in imported
    assert "requests" not in imported
    assert "httpx" not in imported
    for forbidden in (
        ".write_text(",
        ".write_bytes(",
        "pip install",
        "CREATE TABLE",
        "connect(",
        "import_module(",
        "metadata(",
        "site-packages",
    ):
        assert forbidden not in source


def test_runtime_contract_is_blocked_fail_closed_and_exactly_bounded() -> None:
    source = RUNTIME_CONTRACT.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert "duckdb" not in imported
    assert "pytest" not in imported
    assert "duckdb-g040-runtime-evidence.json" not in source
    assert "duckdb-offline-smoke.fixture.json" in source
    assert "TRUSTED_GATE_FIRST_LAUNCHER_IMPLEMENTED = False" in source
    fence_offset = source.index(
        "    if TRUSTED_GATE_FIRST_LAUNCHER_IMPLEMENTED is not True:"
    )
    environment_offset = source.index(
        "    allowed_signers, work_root = _require_g040_environment()"
    )
    gate_offset = source.index("    selected = verify_world_aid_duckdb_bootstrap(")
    import_offset = source.rindex('    duckdb_module = __import__("duckdb")')
    assert fence_offset < environment_offset < gate_offset < import_offset
    assert "operator-controlled Gate-first supervisor launcher" in source
    assert "descriptor-backed read-only wheelhouse" in source
    assert "process-group time/resource/output bounds" in source
    assert "atomic no-follow receipt" in source
    assert "WORLD_AID_G040_REAL_EXECUTION" in source
    assert "absent or skipped execution fails closed" in source
    assert "verify_world_aid_duckdb_bootstrap(" in source
    assert 'duckdb_module = __import__("duckdb")' in source
    assert "_exercise_real_duckdb(duckdb_module, work_root)" in source
    assert '"real_execution": True' in source
    assert "CANONICAL_RECEIPT.write_text(" in source
    for check in (
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
    ):
        assert f'"{check}"' in source


def test_policy_backup_and_runtime_contract_keep_g040_separate_from_g033() -> None:
    policy = (
        ROOT / "wallet_interface/deploy/world-aid-duckdb-runtime.yml"
    ).read_text(encoding="utf-8")
    backup = (
        ROOT / "docs/specs/WORLD_AID_DUCKDB_BACKUP.md"
    ).read_text(encoding="utf-8")
    for term in (
        "enable_external_access: false",
        "autoinstall_known_extensions: false",
        "autoload_known_extensions: false",
        "allow_community_extensions: false",
        "multi_host: false",
        "shared_filesystem: false",
        "direct_worker_writes: false",
        "raw_database_path_exposed_to_clients: false",
        "wheelhouse_mutable: false",
        "lock_mutable: false",
        "skipped_real_execution: fail",
    ):
        assert term in policy
    assert "raw opaque backup" in backup
    assert "G040 does not create an application envelope" in backup
    assert "G033 separately owns authenticated envelope encryption" in backup
    assert "plaintext-marker absence" in backup


def test_every_g042_artifact_is_unapproved_and_objective_evidence_is_linked() -> None:
    artifacts = (
        PROPOSAL,
        ROOT / "requirements-world-aid.lock",
        ROOT / "wallet_interface/deploy/world-aid-duckdb-runtime.yml",
        ROOT / "docs/specs/WORLD_AID_DUCKDB_BACKUP.md",
        ROOT / "docs/adr/WORLD_AID_DUCKDB_STORAGE_ADR.md",
        VERIFIER,
        RUNTIME_CONTRACT,
        DISCOVERY,
    )
    for path in artifacts:
        text = path.read_text(encoding="utf-8").lower()
        assert "not approved" in text or "unapproved" in text

    discovery_path = DISCOVERY.relative_to(ROOT).as_posix()
    heap = HEAP.read_text(encoding="utf-8")
    discovery = DISCOVERY.read_text(encoding="utf-8")
    assert discovery_path in heap
    assert "Objective-validation evidence (WORLDCOIN-AUTO-007)" in heap
    assert "WORLDCOIN-AUTO-007" in discovery
    assert "WORLDCOIN-G042" in discovery
    assert "Canonical command" in discovery
