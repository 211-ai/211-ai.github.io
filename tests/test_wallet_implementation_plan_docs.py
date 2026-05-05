from __future__ import annotations

from pathlib import Path


PLAN = Path("docs/UCAN_ZK_DATA_WALLET_IMPLEMENTATION_PLAN.md")
RETENTION_POLICY = Path("docs/WALLET_RETENTION_POLICY.md")
TARGET_SIGNOFF = Path("docs/WALLET_TARGET_PRODUCTION_SIGNOFF.md")


def test_ucan_zk_wallet_plan_has_no_unresolved_open_decisions() -> None:
    text = PLAN.read_text(encoding="utf-8")

    assert "## Open Decisions" not in text
    assert "## Resolved Decisions" in text
    assert "docs/WALLET_PRODUCTION_DECISIONS_ADR.md" in text
    assert "docs/WALLET_UCAN_PROFILE.md" in text
    assert "docs/WALLET_RETENTION_POLICY.md" in text
    assert "docs/WALLET_TARGET_PRODUCTION_SIGNOFF.md" in text
    assert "python -m wallet_interface.ops --validate-production-readiness" in text


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


def test_ucan_zk_wallet_has_target_signoff_and_retention_artifacts() -> None:
    retention_text = RETENTION_POLICY.read_text(encoding="utf-8")
    signoff_text = TARGET_SIGNOFF.read_text(encoding="utf-8")

    assert "WALLET_REPOSITORY_ROOT" in retention_text
    assert "WALLET_STORAGE_CONFIG" in retention_text
    assert "python -m wallet_interface.ops --validate-production-readiness" in retention_text
    assert "Do not paste secret values" in signoff_text
    assert "docs/WALLET_RETENTION_POLICY.md" in signoff_text
    assert "status=ok" in signoff_text
