"""Repository-only acceptance contract for WORLDCOIN-G041.

The guarded G041 command reads committed files and exercises in-memory
validation only. It never imports or executes Nargo, Noir, ProveKit, ``bb``,
Cargo, Rust, a proof backend, or a container; it never downloads, contacts a
registry, mutates a cache, looks up a secret, builds a circuit, generates a
proof, verifies a proof, or generates setup parameters.
"""

from __future__ import annotations

import ast
import copy
import json
from pathlib import Path
from typing import Any, Callable

from scripts.verify_world_aid_zkp_toolchain import (
    ZkpToolchainVerificationError,
    _validate_zkp_selection,
    verify_world_aid_zkp_toolchain,
)

ROOT = Path(__file__).resolve().parents[2]
PROPOSAL = ROOT / "data/worldcoin_human_aid/bootstrap/zkp-toolchain-dependency-proposal.json"
G002 = ROOT / "data/worldcoin_human_aid/audit/offline-bootstrap-proposal.json"
DISCOVERY = ROOT / "data/worldcoin_human_aid/agent_supervisor/discovery/2026-07-24-worldcoin-auto-006-zkp-bootstrap.md"
HEAP = ROOT / "docs/planning/WORLDCOIN_HUMAN_AID_OBJECTIVE_HEAP.md"
VERIFIER = ROOT / "scripts/verify_world_aid_zkp_toolchain.py"
RUNTIME_CONTRACT = ROOT / "tests/world_aid/test_zkp_toolchain_bootstrap.py"


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _selection() -> dict[str, Any]:
    artifact = lambda path: {"path": path, "sha256": "sha256:" + "1" * 64}
    return {
        "reviewed_state": {
            "zkp_verifier": artifact("scripts/verify_world_aid_zkp_toolchain.py"),
            "zkp_runtime_test": artifact("tests/world_aid/test_zkp_toolchain_bootstrap.py"),
        },
        "dependency_sets": {
            "siwe": {},
            "zkp": {
                "architecture": "x86_64",
                "backend": "nargo-native",
                "version": "0.36.0",
                "tool": artifact("data/worldcoin_human_aid/offline/zkp/nargo-0.36.0-x86_64.bin"),
                "smoke_source": artifact("tests/world_aid/fixtures/zkp_toolchain_smoke/src/main.nr"),
                "smoke_lock": artifact("tests/world_aid/fixtures/zkp_toolchain_smoke/Nargo.lock"),
                "licenses": artifact("data/worldcoin_human_aid/bootstrap/zkp-licenses.json"),
                "provenance": artifact("data/worldcoin_human_aid/bootstrap/zkp-provenance.json"),
                "sbom": artifact("data/worldcoin_human_aid/bootstrap/zkp-sbom.json"),
                "vulnerability_review": artifact("data/worldcoin_human_aid/bootstrap/zkp-vulnerability-review.json"),
                "deterministic_flags": ["--offline", "--locked", "--deterministic", "--target-cpu=x86-64"],
                "resource_bounds": {"max_seconds": 300, "max_memory_mb": 4096, "max_output_bytes": 67108864},
            },
            "duckdb": {},
        },
    }


def _assert_selection_rejected(mutate: Callable[[dict[str, Any]], None], message: str) -> None:
    approval = copy.deepcopy(_selection())
    mutate(approval)
    try:
        _validate_zkp_selection(approval)
    except ZkpToolchainVerificationError as exc:
        assert message in str(exc)
    else:
        raise AssertionError("unsafe or conflicting ZKP selection was accepted")


def test_proposal_preserves_g002_inventory_and_human_selection() -> None:
    proposal = _read_json(PROPOSAL)
    assert proposal["status"] == "unapproved-inventory-only"
    assert proposal["goal_id"] == "WORLDCOIN-G041"
    assert "NOT APPROVED" in proposal["authority_statement"]
    dependency = proposal["dependency"]
    assert dependency["selection_is_human_owned"] is True
    assert all(dependency[key] is None for key in ("architecture", "backend", "version", "binary_or_image", "binary_or_image_digest", "licenses", "provenance", "sbom", "vulnerability_disposition", "resource_bounds", "offline_location", "expiry"))
    assert dependency["smoke_inputs"]["lock"].endswith("/Nargo.lock")
    assert "binary/image digest" in dependency["expected_evidence"]
    assert proposal["inventory"]["source_goal"] == "WORLDCOIN-G002"
    assert "Cargo command" in json.dumps(proposal["inventory"]["qualified_inventory"])
    assert "observed-wrong-architecture-non-aid" in json.dumps(proposal["inventory"]["qualified_inventory"])
    assert "1.93.1" in json.dumps(_read_json(G002)["inventory"]["zkp"])


def test_repository_only_verifier_passes_unapproved_preparation() -> None:
    result = verify_world_aid_zkp_toolchain(ROOT)
    assert result.status == "unapproved-inventory-only"
    assert result.architecture is None
    assert result.backend is None
    assert result.version is None
    assert result.tool_digest is None
    assert result.execution_owner == "G039"


def test_approved_mode_requires_canonical_approval_and_external_trust() -> None:
    try:
        verify_world_aid_zkp_toolchain(ROOT, require_approval=True)
    except ZkpToolchainVerificationError as exc:
        assert "approval" in str(exc)
    else:
        raise AssertionError("approved mode accepted without an approval")

    try:
        verify_world_aid_zkp_toolchain(ROOT, approval=Path("data/worldcoin_human_aid/approvals/gate-0b-selection/approval.json"))
    except ZkpToolchainVerificationError as exc:
        assert "allowed-signers" in str(exc)
    else:
        raise AssertionError("approved mode accepted without signature trust")


def test_future_selection_cross_binds_exact_architecture_paths_and_digests() -> None:
    selected = _validate_zkp_selection(_selection())
    assert selected["architecture"] == "x86_64"
    assert selected["backend"] == "nargo-native"
    assert selected["version"] == "0.36.0"
    assert selected["tool_digest"] == "sha256:" + "1" * 64

    _assert_selection_rejected(lambda item: item["dependency_sets"]["zkp"].update(architecture="aarch64"), "architecture")
    _assert_selection_rejected(lambda item: item["dependency_sets"]["zkp"]["tool"].update(sha256="not-a-digest"), "sha256")
    _assert_selection_rejected(lambda item: item["dependency_sets"]["zkp"]["smoke_lock"].update(path="tests/world_aid/fixtures/other/Nargo.lock"), "conflicting path")
    _assert_selection_rejected(lambda item: item["dependency_sets"]["zkp"].update(version="<SELECT>"), "exact")
    _assert_selection_rejected(lambda item: item["dependency_sets"]["zkp"].update(deterministic_flags=["--allow-network"]), "network")
    _assert_selection_rejected(lambda item: item["dependency_sets"]["zkp"].update(resource_bounds={"max_seconds": 0, "max_memory_mb": 4096, "max_output_bytes": 1}), "max_seconds")
    _assert_selection_rejected(lambda item: item["reviewed_state"]["zkp_verifier"].update(path="scripts/other.py"), "conflicting path")


def test_static_verifier_has_no_tool_or_side_effecting_imports() -> None:
    source = VERIFIER.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {alias.name for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom)) for alias in node.names}
    assert not imported & {"nargo", "noir", "provekit", "bb", "cargo", "rust", "subprocess", "socket", "urllib", "requests", "httpx", "pytest"}
    for forbidden in (".write_text(", ".write_bytes(", "Popen(", "run(", "check_call(", "pip install", "import_module(", "__import__(\"nargo\")", "__import__(\"duckdb\")", "connect("):
        assert forbidden not in source


def test_runtime_contract_is_future_g039_and_fail_closed() -> None:
    source = RUNTIME_CONTRACT.read_text(encoding="utf-8")
    assert "WORLDCOIN-G039" in source
    assert "WORLD_AID_G039_REAL_EXECUTION" in source
    assert "absent or skipped execution fails closed" in source
    assert "signed Gate 0B-selection" in source
    assert "repeat_build" in source
    assert "proof" in source and "verify" in source
    assert "network and registry denial" in source
    assert "production trust" in source
    assert "G041" in source


def test_fixture_is_locked_bounded_and_not_production_trust() -> None:
    spec = (ROOT / "tests/world_aid/fixtures/zkp_toolchain_smoke/SMOKE_SPEC.md").read_text(encoding="utf-8")
    toml = (ROOT / "tests/world_aid/fixtures/zkp_toolchain_smoke/Nargo.toml").read_text(encoding="utf-8")
    lock = (ROOT / "tests/world_aid/fixtures/zkp_toolchain_smoke/Nargo.lock").read_text(encoding="utf-8")
    source = (ROOT / "tests/world_aid/fixtures/zkp_toolchain_smoke/src/main.nr").read_text(encoding="utf-8")
    assert "NOT APPROVED" in spec
    assert "compiler_version = \"0.36.0\"" in toml
    assert "[[package]]" in lock and "source = \"local\"" in lock
    assert "assert(input == 7)" in source and "assert(witness == input)" in source
    for term in ("repeat-build", "proof", "verify", "network", "registry", "production trust", "G039"):
        assert term.lower() in spec.lower()


def test_objective_heap_and_discovery_link_the_validation_repair() -> None:
    heap = HEAP.read_text(encoding="utf-8")
    discovery = DISCOVERY.read_text(encoding="utf-8")
    assert "Objective-validation evidence (WORLDCOIN-AUTO-006)" in heap
    assert DISCOVERY.relative_to(ROOT).as_posix() in heap
    assert "WORLDCOIN-AUTO-006" in discovery
    assert "WORLDCOIN-G041" in discovery
    assert "Canonical command" in discovery
    assert "unapproved" in discovery.lower()
