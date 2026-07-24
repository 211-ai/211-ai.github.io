"""Static contract for the WORLDCOIN-G002 integration audit.

This suite intentionally reads repository text and JSON only. It must not
import or initialize wallet, World ID, database, package-core, npm, container,
or ZKP runtime code.
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
IGNORE_PATH = REPOSITORY_ROOT / ".gitignore"

GUARDED_VALIDATION = (
    "PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 "
    "python -m pytest -q -s -p no:cacheprovider -c /dev/null "
    "--confcutdir=tests/world_aid tests/world_aid/test_integration_audit_contract.py"
)


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_all_expected_audit_outputs_exist_and_are_aligned() -> None:
    for path in (AUDIT_PATH, MAP_PATH, BOOTSTRAP_PATH, DISCOVERY_PATH, HEAP_PATH, IGNORE_PATH):
        assert path.is_file(), path.relative_to(REPOSITORY_ROOT)

    discovery = DISCOVERY_PATH.read_text(encoding="utf-8")
    heap = HEAP_PATH.read_text(encoding="utf-8")
    for text in (discovery, heap):
        assert "WORLDCOIN-G002" in text
        assert "WORLDCOIN-AUTO-001" in text
        assert "3acfa404134f3aa1" in text
        assert "objective_validation_repair" in text
        assert GUARDED_VALIDATION in text
    assert str(DISCOVERY_PATH.relative_to(REPOSITORY_ROOT)) in heap

    ignore = IGNORE_PATH.read_text(encoding="utf-8")
    assert "!data/worldcoin_human_aid/audit/*.json" not in ignore
    assert "!data/worldcoin_human_aid/agent_supervisor/discovery/*.md" not in ignore
    assert "!data/worldcoin_human_aid/audit/component-map.json" in ignore
    assert "!data/worldcoin_human_aid/audit/offline-bootstrap-proposal.json" in ignore
    assert (
        "!data/worldcoin_human_aid/agent_supervisor/discovery/2026-07-24-worldcoin-auto-001-integration-audit.md"
    ) in ignore


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
        "the cross-wallet raw-nullifier replay index is\nprocess-local and is lost after restart": (
            "ipfs_datasets_py/ipfs_datasets_py/wallet/service.py::import_wallet_snapshot"
        ),
    }
    for finding, citation in required_findings.items():
        assert finding in audit
        assert citation in audit

    assert "`world_id_private_nullifiers`" in audit
    assert "`world_id_raw_nullifier_index`" in audit
    assert "World Developer Portal verify API v4" in " ".join(audit.split())
    assert "## Speculation register" in audit
    assert audit.count("**Speculation") >= 3


def test_audit_identifies_missing_boundaries_with_correct_goal_ownership() -> None:
    audit = AUDIT_PATH.read_text(encoding="utf-8")
    for heading_or_term in (
        "**EIP-1271 SIWE.**",
        "**Issuer credential lifecycle.**",
        "**Encrypted transactional storage.**",
        "**Payout.**",
        "**Reconciliation.**",
        "**Eligibility composition.**",
        "## Compatibility boundary freeze",
        "deletion-prohibited",
        "additive adapter",
    ):
        assert heading_or_term in audit

    for path_citation in (
        "docs/planning/WORLDCOIN_HUMAN_AID_OBJECTIVE_HEAP.md::WORLDCOIN-G006",
        "docs/planning/WORLDCOIN_HUMAN_AID_OBJECTIVE_HEAP.md::WORLDCOIN-G009",
        "docs/planning/WORLDCOIN_HUMAN_AID_OBJECTIVE_HEAP.md::WORLDCOIN-G034",
        "docs/planning/WORLDCOIN_HUMAN_AID_OBJECTIVE_HEAP.md::WORLDCOIN-G033",
        "docs/planning/WORLDCOIN_HUMAN_AID_OBJECTIVE_HEAP.md::WORLDCOIN-G040",
        "docs/planning/WORLDCOIN_HUMAN_AID_OBJECTIVE_HEAP.md::WORLDCOIN-G016",
        "docs/planning/WORLDCOIN_HUMAN_AID_OBJECTIVE_HEAP.md::WORLDCOIN-G021",
        "docs/planning/WORLDCOIN_HUMAN_AID_OBJECTIVE_HEAP.md::WORLDCOIN-G022",
        "docs/planning/WORLDCOIN_HUMAN_AID_OBJECTIVE_HEAP.md::WORLDCOIN-G014",
    ):
        assert path_citation in audit

    assert "G026 owns that boundary" not in audit
    assert "G005/G022" not in audit
    assert "G023–G025" not in audit
    assert "G007 owns encrypted transactional replacement" not in audit
    assert "WorldIdSurfaceStatus` carries the essential-service/manual-path statement" in audit


def test_component_map_semantically_matches_the_objective_heap() -> None:
    component_map = read_json(MAP_PATH)
    assert component_map["schema_version"] == "world-human-aid-component-map/v2"
    assert component_map["goal_id"] == "WORLDCOIN-G002"
    assert component_map["task_id"] == "WORLDCOIN-AUTO-001"

    audit_mode = component_map["audit_mode"]
    assert isinstance(audit_mode, dict)
    assert audit_mode["read_only"] is True
    assert all(value is False for key, value in audit_mode.items() if key != "read_only")

    components = component_map["components"]
    assert isinstance(components, list)
    by_id = {component["id"]: component for component in components}
    assert len(by_id) == len(components)

    expected_owners = {
        "world-id-config-verifier": "WORLDCOIN-G004",
        "world-id-wallet-binding": "WORLDCOIN-G007",
        "wallet-status-api": "WORLDCOIN-G007",
        "local-wallet-repository": "WORLDCOIN-G033",
        "wallet-principal-auth": "WORLDCOIN-G006",
        "document-profile-receipt": "WORLDCOIN-G012",
        "zkp-backends": "WORLDCOIN-G012",
        "provider-context": "WORLDCOIN-G017",
        "issuer-lifecycle": "WORLDCOIN-G034",
        "aid-trust-composition": "WORLDCOIN-G014",
        "payout-intent": "WORLDCOIN-G016",
        "treasury-custody": "WORLDCOIN-G018",
        "world-chain-client": "WORLDCOIN-G019",
        "provider-minikit-transaction": "WORLDCOIN-G020",
        "direct-wld-payout": "WORLDCOIN-G021",
        "chain-reconciliation": "WORLDCOIN-G022",
        "world-id-ui": "WORLDCOIN-G025",
    }
    assert set(by_id) == set(expected_owners)

    expected_goals = {
        "world-id-config-verifier": {"WORLDCOIN-G004", "WORLDCOIN-G007"},
        "world-id-wallet-binding": {
            "WORLDCOIN-G004",
            "WORLDCOIN-G007",
            "WORLDCOIN-G008",
            "WORLDCOIN-G014",
        },
        "wallet-status-api": {"WORLDCOIN-G007", "WORLDCOIN-G024", "WORLDCOIN-G033"},
        "local-wallet-repository": {
            "WORLDCOIN-G008",
            "WORLDCOIN-G033",
            "WORLDCOIN-G040",
            "WORLDCOIN-G042",
        },
        "wallet-principal-auth": {"WORLDCOIN-G006", "WORLDCOIN-G037", "WORLDCOIN-G038"},
        "document-profile-receipt": {"WORLDCOIN-G012", "WORLDCOIN-G013", "WORLDCOIN-G014"},
        "zkp-backends": {
            "WORLDCOIN-G012",
            "WORLDCOIN-G013",
            "WORLDCOIN-G039",
            "WORLDCOIN-G041",
        },
        "provider-context": {
            "WORLDCOIN-G006",
            "WORLDCOIN-G007",
            "WORLDCOIN-G014",
            "WORLDCOIN-G017",
        },
        "issuer-lifecycle": {"WORLDCOIN-G009", "WORLDCOIN-G034"},
        "aid-trust-composition": {"WORLDCOIN-G014"},
        "payout-intent": {"WORLDCOIN-G016"},
        "treasury-custody": {"WORLDCOIN-G018"},
        "world-chain-client": {"WORLDCOIN-G019"},
        "provider-minikit-transaction": {"WORLDCOIN-G020"},
        "direct-wld-payout": {"WORLDCOIN-G021"},
        "chain-reconciliation": {"WORLDCOIN-G022"},
        "world-id-ui": {
            "WORLDCOIN-G004",
            "WORLDCOIN-G007",
            "WORLDCOIN-G024",
            "WORLDCOIN-G025",
            "WORLDCOIN-G027",
            "WORLDCOIN-G028",
        },
    }

    heap = HEAP_PATH.read_text(encoding="utf-8")
    heap_goals = {
        goal_id: title for goal_id, title in re.findall(r"^## (WORLDCOIN-G\d{3}) (.+)$", heap, flags=re.MULTILINE)
    }
    statuses = set(component_map["status_vocabulary"])
    for component_id, component in by_id.items():
        assert re.fullmatch(r"[a-z0-9-]+", component_id)
        assert component["owner"] == expected_owners[component_id]
        assert set(component["goals"]) == expected_goals[component_id]
        assert component["owner"] in component["goals"]
        assert component["owner"] in heap_goals
        assert component["status"] in statuses
        for required_array in ("interfaces", "risks", "goals", "conflict_surfaces", "evidence"):
            assert isinstance(component[required_array], list)
            assert component[required_array], (component_id, required_array)
        assert all(goal in heap_goals for goal in component["goals"])
        assert all("::" in citation for citation in component["evidence"])

    assert "secure" in heap_goals["WORLDCOIN-G033"].lower() or "transactional" in heap_goals["WORLDCOIN-G033"].lower()
    assert "siwe" in heap_goals["WORLDCOIN-G006"].lower()
    assert "issuer" in heap_goals["WORLDCOIN-G034"].lower()
    assert "reconcile" in heap_goals["WORLDCOIN-G022"].lower()


def test_component_map_classifies_unsafe_and_missing_boundaries_without_overclaim() -> None:
    component_map = read_json(MAP_PATH)
    by_id = {component["id"]: component for component in component_map["components"]}

    assert by_id["document-profile-receipt"]["status"] == "simulated"
    assert by_id["local-wallet-repository"]["status"] == "unsafe-to-reuse"
    assert by_id["wallet-status-api"]["status"] == "unsafe-to-reuse"
    assert by_id["world-id-wallet-binding"]["status"] == "unsafe-to-reuse"
    for component_id in (
        "issuer-lifecycle",
        "aid-trust-composition",
        "payout-intent",
        "treasury-custody",
        "world-chain-client",
        "provider-minikit-transaction",
        "direct-wld-payout",
        "chain-reconciliation",
    ):
        assert by_id[component_id]["status"] == "missing"

    rendered = json.dumps(component_map, sort_keys=True)
    for exact_risk in (
        "Legacy proof acceptance defaults on.",
        "Accepted v3 evidence can be labeled world_id_idkit_v4 in a receipt.",
        "Status authentication is optional.",
        "Principal secrets are hex-encoded into plaintext JSON.",
        "DuckDB native file mode permits only one external writer process; uncoordinated direct opens by wallet, API, payout, or reconciliation workers cannot satisfy the cross-worker transaction boundary.",
        "Direct access to a DuckDB file would bypass the authenticated single-writer service, domain authorization, and minimum-necessary projection boundary.",
        "The receipt proves no aid-program eligibility statement.",
        "The registration verifier does not require or compare provider signal context.",
        "No EIP-1271 contract-wallet signature validation boundary exists in the audited path.",
        "No idempotent payout boundary exists.",
        "No confirmation, reorganization, replacement, or accounting reconciliation state exists.",
    ):
        assert exact_risk in rendered


def test_offline_bootstrap_uses_qualified_observed_and_unknown_states() -> None:
    proposal = read_json(BOOTSTRAP_PATH)
    assert proposal["schema_version"] == "world-human-aid-offline-bootstrap-proposal/v2"
    assert proposal["proposal_status"] == "human-selection-required"
    assert "not approval" in proposal["authority_statement"]

    vocabulary = proposal["state_vocabulary"]
    assert {
        "observed-command-on-path",
        "observed-workspace-package",
        "observed-install-metadata",
        "locked",
        "declared",
        "source-present",
        "recorded-prior-smoke-only",
        "observed-not-on-path",
        "not-observed-not-proven-missing",
        "unknown-not-inspected",
        "missing-required-artifact",
    } <= set(vocabulary)

    inventory = proposal["inventory"]
    assert set(inventory) == {"npm", "python_duckdb", "zkp"}
    for family_name, family in inventory.items():
        assert family["observed_environment"], family_name
        assert family["locked_or_declared"], family_name
        assert family["not_observed_or_unselected"], family_name
        assert family["unknown_or_not_inspected"], family_name
        for bucket in family.values():
            assert isinstance(bucket, list)
            for item in bucket:
                assert item["state"] in vocabulary
                assert "::" in item["evidence"]
        for item in family["not_observed_or_unselected"] + family["unknown_or_not_inspected"]:
            assert item["selection_owner"] == "humans"
            assert item["state"] != "missing"

    npm = inventory["npm"]
    observed_npm = {(item["input"], item["version"], item["state"]) for item in npm["observed_environment"]}
    assert ("@worldcoin/idkit", "4.1.8", "observed-workspace-package") in observed_npm
    assert ("@worldcoin/idkit-core", "4.1.8", "observed-workspace-package") in observed_npm
    assert ("@worldcoin/idkit-server", "1.1.1", "observed-workspace-package") in observed_npm
    assert ("ethers npm cache entry", "5.8.0", "observed-unapproved-cache") in observed_npm
    assert any(
        item["input"] == "@worldcoin/idkit" and item["version"] == "^4.1.8" and item["state"] == "declared"
        for item in npm["locked_or_declared"]
    )
    assert "npm cache not inspected" not in json.dumps(npm).lower()

    rendered = json.dumps(inventory, sort_keys=True).lower()
    for required_input in (
        "eip-4361 siwe",
        "eip-1271",
        "world chain",
        "duckdb",
        "single-writer",
        "migration",
        "provekit",
        "noir/nargo",
        "aid-eligibility circuit",
        "proving key",
        "verifier key",
    ):
        assert required_input in rendered
    assert "manifest absence" not in rendered
    assert "postgresql" not in rendered
    assert "psycopg" not in rendered
    assert "optional signed duckdb extension" not in rendered
    assert "native-extension cache" not in rendered

    duckdb_unknowns = json.dumps(inventory["python_duckdb"]["unknown_or_not_inspected"]).lower()
    assert "approved duckdb wheelhouse" in duckdb_unknowns
    assert "database, wal, temporary-file, and backup locations" in duckdb_unknowns
    assert "unknown-not-inspected" in duckdb_unknowns

    python_observed = json.dumps(inventory["python_duckdb"]["observed_environment"], sort_keys=True)
    for exact_fact in (
        "historical-environment-not-recorded",
        "3.12.3-1ubuntu0.15",
        "3.12.12",
        "FastAPI system-user-site distribution metadata",
        "0.138.2",
        "Miniforge FastAPI distribution metadata",
        "0.101.1",
        "Miniforge SQLAlchemy distribution metadata",
        "2.0.50",
        "inactive workspace virtual environment",
        "DuckDB system-user-site distribution metadata",
        "1.4.3",
        "DuckDB 1.5.2 distribution metadata",
    ):
        assert exact_fact in python_observed
    duckdb_declared = inventory["python_duckdb"]["locked_or_declared"]
    assert any(
        item["input"] == "DuckDB Python dependency" and item["version"] == ">=1.4.0" and item["state"] == "declared"
        for item in duckdb_declared
    )
    assert (
        "exact approved duckdb python wheel"
        in json.dumps(inventory["python_duckdb"]["not_observed_or_unselected"]).lower()
    )

    supersession = proposal["historical_supersession"]
    assert supersession["status"] == "superseded-selection-retained-as-history"
    assert supersession["superseded_selection_target"] == "Python/PostgreSQL"
    assert supersession["current_selection_target"] == "Python/DuckDB"
    assert "not a signed Gate 0B" in supersession["authority_limit"]
    assert "direct multi-process access" in supersession["authority_limit"]

    zkp_observed = json.dumps(inventory["zkp"]["observed_environment"], sort_keys=True)
    for exact_fact in (
        "1.93.1",
        "1.96.0-nightly",
        "partial ProveKit Cargo crate cache",
        "observed-unapproved-cache",
        "observed-wrong-architecture-non-aid",
        "7cd14c97f321c0b4220cfc881c424800f2da288b3056c49c2a6bf7a030bb02dc",
        "present-non-aid-unapproved",
        "0efdaa9a518082122df987297fcd05b0ce411aa859d42cbe88a1b33d3be8c0a3",
        "3c5d85cf1ac5d305237704e1b26714ee89140fc46b3f87cbd0a9695a5a65d76d",
    ):
        assert exact_fact in zkp_observed
    zkp_gaps = json.dumps(inventory["zkp"]["not_observed_or_unselected"], sort_keys=True)
    assert "provekit-cli" in zkp_gaps
    assert "Nargo.lock" in zkp_gaps
    assert "WORLDCOIN-G012" in zkp_gaps
    assert "WORLDCOIN-G013" in zkp_gaps
    assert "WORLDCOIN-G028" in zkp_gaps


def test_offline_bootstrap_reserves_every_selection_for_humans_and_routes_families() -> None:
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
    assert set(gate["required_human_records"]) == {question["required_record"] for question in questions}
    assert gate["next_owners"] == {
        "siwe_dependency_lock_proposal": "WORLDCOIN-G037",
        "siwe_offline_verification": "WORLDCOIN-G038",
        "zkp_verifier_and_smoke_proposal": "WORLDCOIN-G041",
        "zkp_offline_verification": "WORLDCOIN-G039",
        "duckdb_verifier_lock_and_policy_proposal": "WORLDCOIN-G042",
        "duckdb_offline_verification": "WORLDCOIN-G040",
        "world_chain_client_selection": "WORLDCOIN-G019",
    }


def test_contract_body_and_declared_audit_are_static_and_side_effect_free() -> None:
    proposal = read_json(BOOTSTRAP_PATH)
    observation = proposal["audit_observation"]
    assert observation["method"].startswith("Read repository manifests, lockfiles, source")
    assert set(observation["performed"]) == {
        "filesystem reads",
        "static manifest and lockfile inspection",
        "static installed-package metadata inspection",
        "static operating-system and environment metadata inspection",
        "static finite package-cache index and archive-name inspection",
        "non-executing PATH name resolution",
    }
    assert set(observation["not_performed"]) == {
        "network call",
        "download",
        "secret lookup",
        "package install",
        "container pull",
        "container start",
        "container image listing",
        "toolchain execution",
        "audited World, wallet, database, npm, container, or ZKP package import by the inventory or contract body",
        "package-core initialization",
    }
    assert len(observation["limitations"]) >= 5
    transparency = "\n".join(observation["review_transparency"])
    assert "npm cache verify" in transparency
    assert "approximately 4.53 GB" in transparency
    assert "recoverable only by re-download" in transparency
    assert "post-incident observation" in transparency
    assert "/tmp/g002_no_write_guard" in transparency

    source = Path(__file__).read_text(encoding="utf-8")
    forbidden_runtime_imports = (
        "wallet_interface",
        "ipfs_datasets_py",
        "requests",
        "httpx",
        "urllib",
        "socket",
        "subprocess",
        "duckdb",
        "psycopg",
        "sqlalchemy",
        "pytest",
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
    discovery = DISCOVERY_PATH.read_text(encoding="utf-8")
    assert "Python and pytest\nnecessarily execute the test runner" in discovery
    normalized_discovery = " ".join(discovery.split())
    assert "The no-toolchain claim is limited to the audited integration body" in normalized_discovery
