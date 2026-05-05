from __future__ import annotations

import re
from pathlib import Path


PLAN = Path("docs/UCAN_ZK_DATA_WALLET_IMPLEMENTATION_PLAN.md")
RETENTION_POLICY = Path("docs/WALLET_RETENTION_POLICY.md")
TARGET_SIGNOFF = Path("docs/WALLET_TARGET_PRODUCTION_SIGNOFF.md")
TARGET_SIGNOFF_PACKET = Path("docs/WALLET_TARGET_PRODUCTION_SIGNOFF_PACKET.template.json")
UI_APP = Path("wallet_interface/ui/src/app/App.tsx")
UI_API = Path("wallet_interface/ui/src/services/walletApi.ts")


def test_ucan_zk_wallet_plan_has_no_unresolved_open_decisions() -> None:
    text = PLAN.read_text(encoding="utf-8")

    assert "## Open Decisions" not in text
    assert "## Resolved Decisions" in text
    assert "docs/WALLET_PRODUCTION_DECISIONS_ADR.md" in text
    assert "docs/WALLET_UCAN_PROFILE.md" in text
    assert "docs/WALLET_RETENTION_POLICY.md" in text
    assert "docs/WALLET_TARGET_PRODUCTION_SIGNOFF.md" in text
    assert "docs/WALLET_TARGET_PRODUCTION_SIGNOFF_PACKET.template.json" in text
    assert "complete conformance fixture validation" in text
    assert "python -m wallet_interface.ops --validate-production-readiness" in text
    assert "python -m wallet_interface.ops --validate-distance-proof-contract" in text
    assert "python -m wallet_interface.ops --validate-target-signoff-packet" in text


def test_ucan_zk_wallet_phase_table_tracks_gates_not_missing_mvp_work() -> None:
    text = PLAN.read_text(encoding="utf-8")
    table_start = text.index("| Phase | Status | Remaining Gate |")
    table_end = text.index("### Phase 0", table_start)
    phase_table = text[table_start:table_end]

    assert "partial" not in phase_table
    assert "MVP implemented" not in phase_table
    assert "Main Gap" not in phase_table
    assert phase_table.count("implementation complete") == 10


def test_ucan_zk_wallet_milestones_are_written_as_implemented_work() -> None:
    text = PLAN.read_text(encoding="utf-8")

    assert "Define final UCAN token profile" not in text
    assert "Choose one first production proof family" not in text
    assert text.count("Implemented scope:") == 5


def test_ucan_zk_wallet_implemented_scopes_are_not_future_tense_backlog() -> None:
    text = PLAN.read_text(encoding="utf-8")
    implemented_scopes = re.findall(
        r"Implemented scope:\n\n(?P<block>.*?)(?=\nExit criteria:)",
        text,
        flags=re.DOTALL,
    )
    future_verbs = (
        "Add",
        "Choose",
        "Define",
        "Document",
        "Extend",
        "Implement",
        "Keep",
        "Replace",
        "Select",
        "Store",
        "Wire",
    )

    assert len(implemented_scopes) == 5
    for block in implemented_scopes:
        for line in block.splitlines():
            assert not line.startswith(tuple(f"- {verb} " for verb in future_verbs))


def test_ucan_zk_wallet_plan_has_no_stale_mvp_or_open_gap_phrasing() -> None:
    text = PLAN.read_text(encoding="utf-8")

    stale_phrases = [
        "MVP",
        "needs real wallet storage adapters",
        "must be made production-safe",
        "should be wrapped by wallet-aware privacy controls",
        "Production deployments must replace this",
        "Implementation contract:",
        "Add a proof backend interface",
        "Add request flags",
        "Add unit tests",
        "production database wiring remains",
    ]

    for phrase in stale_phrases:
        assert phrase not in text


def test_wallet_docs_do_not_reintroduce_mvp_status_language() -> None:
    wallet_docs = [PLAN, *sorted(Path("docs").glob("WALLET_*.md"))]

    for path in wallet_docs:
        assert "MVP" not in path.read_text(encoding="utf-8")


def test_ucan_zk_wallet_has_target_signoff_and_retention_artifacts() -> None:
    retention_text = RETENTION_POLICY.read_text(encoding="utf-8")
    signoff_text = TARGET_SIGNOFF.read_text(encoding="utf-8")
    packet_text = TARGET_SIGNOFF_PACKET.read_text(encoding="utf-8")

    assert "WALLET_REPOSITORY_ROOT" in retention_text
    assert "WALLET_STORAGE_CONFIG" in retention_text
    assert "python -m wallet_interface.ops --validate-production-readiness" in retention_text
    assert "Do not paste secret values" in signoff_text
    assert "docs/WALLET_RETENTION_POLICY.md" in signoff_text
    assert "docs/WALLET_TARGET_PRODUCTION_SIGNOFF_PACKET.template.json" in signoff_text
    assert "status=ok" in signoff_text
    assert "secret_manager_refs" in packet_text
    assert "retention_mapping" in packet_text
    assert "analytics_privacy_review" in packet_text


def test_location_distance_proof_ui_stays_behind_staging_verifier_gate() -> None:
    plan_text = PLAN.read_text(encoding="utf-8")
    app_text = UI_APP.read_text(encoding="utf-8")
    api_text = UI_API.read_text(encoding="utf-8")

    assert "target verifier staging validation before live UI exposure" in plan_text
    assert "regression guard keeps `location_distance` out of the visible Proof Center" in plan_text
    assert "createLocationDistanceProof" in api_text
    assert "/distance-proofs" in api_text
    assert "createLocationDistanceProof" not in app_text
    assert "/distance-proofs" not in app_text
    assert "location/prove_distance" not in app_text
