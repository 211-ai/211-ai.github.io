from pathlib import Path


SERVICE_TEMPLATE = (
    Path(__file__).resolve().parents[1]
    / "ops"
    / "systemd"
    / "user"
    / "abby-voice-publicus-regeneration.service"
)


def test_service_template_uses_quota_launcher_and_bounded_system_restarts() -> None:
    unit = SERVICE_TEMPLATE.read_text(encoding="utf-8")

    assert "scripts/run_quota_aware_command.py" in unit
    assert unit.count("regeneration-batch-state.json") == 2
    assert "--max-quota-retries 0" in unit
    assert "StartLimitIntervalSec=30min" in unit
    assert "StartLimitBurst=3" in unit
    assert "Restart=on-failure" in unit
    assert "RestartSec=60" in unit
    assert "RestartPreventExitStatus=75" in unit
