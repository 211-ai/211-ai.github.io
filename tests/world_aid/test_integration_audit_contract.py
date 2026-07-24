"""Static contract for the WORLDCOIN-G002 integration audit.

This suite intentionally reads repository text and JSON only. It must not
import or initialize wallet, World ID, database, package-core, or ZKP runtime
code.
"""

from __future__ import annotations

import json
import re
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
AUDIT_PATH = REPOSITORY_ROOT / "docs/reports/WORLD_HUMAN_AID_INTEGRATION_AUDIT.md"
MAP_PATH = REPOSITORY_ROOT / "data/worldcoin_human_aid/audit/component-map.json"
BOOTSTRAP_PATH = REPOSITORY_ROOT / "data/worldcoin_human_aid/audit/offline-bootstrap-proposal.json"
DISCOVERY_PATH = (
    REPOSITORY_ROOT
    / "data/worldcoin_human_aid/agent_supervisor/discovery"
    / "2026-07-24-worldcoin-auto-001-integration-audit.md"
)
HEAP_PATH = REPOSITORY_ROOT / "docs/planning/WORLDCOIN_HUMAN_AID_OBJECTIVE_HEAP.md"


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_all_expected_audit_outputs_exist_and_are_aligned() -> None:
    for path in (AUDIT_PATH, MAP_PATH, BOOTSTRAP_PATH, DISCOVERY_PATH, HEAP_PATH):
        assert path.is_file(), path.relative_to(REPOSITORY_ROOT)

    discovery = DISCOVERY_PATH.read_text(encoding="utf-8")
    heap = HEAP_PATH.read_text(encoding="utf-8")
    for text in (discovery, heap):
        assert "WORLDCOIN-G002" in text
        assert "WORLDCOIN-AUTO-001" in text
        assert "3acfa404134f3aa1" in text
        assert "objective_validation_repair" in text
    assert str(DISCOVERY_PATH.relative_to(REPOSITORY_ROOT)) in heap


def test_audit_records_every_required_confirmed_finding_with_source_citations() -> None:
    audit = AUDIT_PATH.read_text(encoding="utf-8")
    required_findings = {
        "simulated profile receipt is **not eligibility**": (
            "ipfs_datasets_py/ipfs_datasets_py/wallet/service.py::create_document_profile_proof"
        ),
        "Provider signal context is therefore **unenforced**": (
            "wallet_interface/app_service.py::register_world_id_verification"
        ),
        "snapshots plaintext principal secrets and raw\nWorld bindings": (
            "ipfs_datasets_py/ipfs_datasets_py/wallet/service.py::export_wallet_snapshot"
        ),
        "unauthenticated status returns full bindings": "wallet_interface/routes/world_id.py::get_world_id_status",
        "Legacy acceptance therefore defaults on": "wallet_interface/world_id.py::load_world_id_config",
        "Receipts can therefore mislabel accepted v3 evidence as v4": (
            "ipfs_datasets_py/ipfs_datasets_py/wallet/service.py::_create_world_id_proof_receipt"
        ),
    }
    for finding, citation in required_findings.items():
        assert finding in audit
        assert citation in audit

    assert "World Developer Portal verify API v4" in " ".join(audit.split())
    assert "## Speculation register" in audit
    assert audit.count("**Speculation") >= 3


def test_audit_identifies_all_missing_boundaries_and_freezes_compatibility() -> None:
    audit = AUDIT_PATH.read_text(encoding="utf-8")
    for heading_or_term in (
        "**EIP-1271 SIWE.**",
        "**Issuer credential lifecycle.**",
        "**Encrypted transactional storage.**",
        "**Payout.**",
        "**Reconciliation.**",
        "## Compatibility boundary freeze",
        "deletion-prohibited",
        "additive adapter",
    ):
        assert heading_or_term in audit

    for path_citation in (
        "wallet_interface/app_service.py::_require_portal_actor",
        "ipfs_datasets_py/ipfs_datasets_py/wallet/models.py::WorldIdBinding",
        "ipfs_datasets_py/ipfs_datasets_py/wallet/repository.py::LocalWalletRepository",
        "docs/planning/WORLDCOIN_HUMAN_AID_OBJECTIVE_HEAP.md::WORLDCOIN-G023",
        "docs/planning/WORLDCOIN_HUMAN_AID_OBJECTIVE_HEAP.md::WORLDCOIN-G026",
    ):
        assert path_citation in audit


def test_component_map_has_stable_owners_interfaces_risks_goals_and_conflicts() -> None:
    component_map = read_json(MAP_PATH)
    assert component_map["schema_version"] == "world-human-aid-component-map/v1"
    assert component_map["goal_id"] == "WORLDCOIN-G002"
    assert component_map["task_id"] == "WORLDCOIN-AUTO-001"

    audit_mode = component_map["audit_mode"]
    assert isinstance(audit_mode, dict)
    assert audit_mode["read_only"] is True
    assert all(value is False for key, value in audit_mode.items() if key != "read_only")

    components = component_map["components"]
    assert isinstance(components, list)
    assert len(components) >= 10
    component_ids = [component["id"] for component in components]
    assert len(component_ids) == len(set(component_ids))
    assert {
        "world-id-config-verifier",
        "world-id-wallet-binding",
        "wallet-status-api",
        "local-wallet-repository",
        "wallet-principal-auth",
        "document-profile-receipt",
        "provider-context",
        "issuer-lifecycle",
        "payout-reconciliation",
    }.issubset(component_ids)

    statuses = set(component_map["status_vocabulary"])
    for component in components:
        assert re.fullmatch(r"[a-z0-9-]+", component["id"])
        assert re.fullmatch(r"WORLDCOIN-G\d{3}", component["owner"])
        assert component["status"] in statuses
        for required_array in ("interfaces", "risks", "goals", "conflict_surfaces", "evidence"):
            assert isinstance(component[required_array], list)
            assert component[required_array], (component["id"], required_array)
        assert component["owner"] in component["goals"]
        assert all(re.fullmatch(r"WORLDCOIN-G\d{3}", goal) for goal in component["goals"])
        assert all("::" in citation for citation in component["evidence"])


def test_component_map_classifies_unsafe_and_missing_boundaries_without_overclaim() -> None:
    component_map = read_json(MAP_PATH)
    by_id = {component["id"]: component for component in component_map["components"]}

    assert by_id["document-profile-receipt"]["status"] == "simulated"
    assert by_id["local-wallet-repository"]["status"] == "unsafe-to-reuse"
    assert by_id["wallet-status-api"]["status"] == "unsafe-to-reuse"
    assert by_id["world-id-wallet-binding"]["status"] == "unsafe-to-reuse"
    assert by_id["issuer-lifecycle"]["status"] == "missing"
    assert by_id["payout-reconciliation"]["status"] == "missing"

    rendered = json.dumps(component_map, sort_keys=True)
    for exact_risk in (
        "Legacy proof acceptance defaults on.",
        "Accepted v3 evidence can be labeled world_id_idkit_v4 in a receipt.",
        "Status authentication is optional.",
        "Principal secrets are hex-encoded into plaintext JSON.",
        "The receipt proves no aid-program eligibility statement.",
        "The registration verifier does not require or compare provider signal context.",
        "No EIP-1271 contract-wallet signature validation boundary exists in the audited path.",
        "No idempotent payout boundary exists.",
    ):
        assert exact_risk in rendered


def test_offline_bootstrap_inventories_all_input_families() -> None:
    proposal = read_json(BOOTSTRAP_PATH)
    assert proposal["schema_version"] == "world-human-aid-offline-bootstrap-proposal/v1"
    assert proposal["proposal_status"] == "human-selection-required"
    assert "not approval" in proposal["authority_statement"]

    inventory = proposal["inventory"]
    assert set(inventory) == {"npm", "python_postgresql", "zkp"}
    for family in inventory.values():
        assert (
            family.get("installed_or_locked")
            or family.get("installed_or_declared")
            or family.get("installed_or_recorded")
        )
        assert family["missing_or_unselected"]
        for item in family["missing_or_unselected"]:
            assert item["selection_owner"] == "humans"
            assert "::" in item["evidence"]

    rendered = json.dumps(inventory, sort_keys=True)
    for required_input in (
        "@worldcoin/idkit",
        "EIP-4361 SIWE",
        "EIP-1271",
        "PostgreSQL",
        "migration",
        "ProveKit",
        "Noir/nargo",
        "aid-eligibility circuit",
        "proving key",
        "verifier key",
    ):
        assert required_input.lower() in rendered.lower()


def test_offline_bootstrap_reserves_every_selection_for_human_approval() -> None:
    proposal = read_json(BOOTSTRAP_PATH)
    questions = proposal["human_approval_questions"]
    assert {question["id"] for question in questions} == {
        "versions",
        "checksums",
        "licenses",
        "provenance",
        "sbom",
        "cache-image-locations",
        "smoke-tests",
    }
    assert all(question["question"].endswith("?") for question in questions)

    gate = proposal["approval_gate"]
    assert gate["default"] == "blocked"
    assert gate["agent_selections_are_approval"] is False
    assert gate["next_owner"] == "WORLDCOIN-G037"
    assert set(gate["required_human_records"]) == {question["required_record"] for question in questions}


def test_contract_and_declared_audit_are_static_and_side_effect_free() -> None:
    proposal = read_json(BOOTSTRAP_PATH)
    observation = proposal["audit_observation"]
    assert observation["method"] == "Read repository manifests, lockfiles, source, and recorded artifacts only."
    assert set(observation["performed"]) == {
        "filesystem reads",
        "static manifest inspection",
        "static source inspection",
    }
    assert set(observation["not_performed"]) == {
        "network call",
        "download",
        "secret lookup",
        "package install",
        "container pull",
        "container start",
        "toolchain execution",
        "package-core initialization",
    }

    source = Path(__file__).read_text(encoding="utf-8")
    forbidden_runtime_imports = (
        "wallet_interface",
        "ipfs_datasets_py",
        "requests",
        "httpx",
        "urllib",
        "socket",
        "subprocess",
        "psycopg",
        "sqlalchemy",
    )
    import_lines = [
        line.strip()
        for line in source.splitlines()
        if line.lstrip().startswith("import ") or line.lstrip().startswith("from ")
    ]
    assert not any(name in line for line in import_lines for name in forbidden_runtime_imports)

    mutation_calls = re.findall(
        r"\.(write_text|write_bytes|mkdir|touch|unlink|rename|replace|rmdir)\s*\(",
        source,
    )
    assert mutation_calls == []
