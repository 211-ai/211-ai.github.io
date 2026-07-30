from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from scripts import retry_after_policy
from scripts import run_quota_aware_command as launcher


def test_launcher_honors_checkpoint_retry_after_before_retrying(monkeypatch, tmp_path: Path) -> None:
    anchor = retry_after_policy.parse_timestamp("2026-07-29T00:00:00Z")
    assert anchor is not None
    state = tmp_path / "state.json"
    status = tmp_path / "launcher-status.json"
    state.write_text("{}", encoding="utf-8")
    returncodes = iter((75, 0))
    calls: list[list[str]] = []
    sleeps: list[float] = []

    def fake_run(command: list[str], check: bool) -> SimpleNamespace:
        calls.append(list(command))
        returncode = next(returncodes)
        if returncode == 75:
            state.write_text(
                json.dumps({"updatedAt": "2026-07-29T00:00:00Z", "retryAfter": "01:00:00"}),
                encoding="utf-8",
            )
        return SimpleNamespace(returncode=returncode)

    monkeypatch.setattr(launcher.subprocess, "run", fake_run)
    monkeypatch.setattr(launcher.time, "time", lambda: anchor + 600.0)
    monkeypatch.setattr(launcher.time, "sleep", lambda seconds: sleeps.append(seconds))

    exit_code = launcher.main(
        [
            "--state",
            str(state),
            "--status",
            str(status),
            "--",
            "python3",
            "worker.py",
        ]
    )

    payload = json.loads(status.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert calls == [["python3", "worker.py"], ["python3", "worker.py"]]
    assert sleeps == [3015.0]
    assert payload["phase"] == "complete"
    assert payload["quotaExitCount"] == 1


def test_launcher_resumes_existing_quota_wait_before_starting_child(monkeypatch, tmp_path: Path) -> None:
    anchor = retry_after_policy.parse_timestamp("2026-07-29T00:00:00Z")
    assert anchor is not None
    state = tmp_path / "state.json"
    status = tmp_path / "launcher-status.json"
    state.write_text(
        json.dumps({"updatedAt": "2026-07-29T00:00:00Z", "retryAfter": "01:00:00"}),
        encoding="utf-8",
    )
    events: list[str] = []
    monkeypatch.setattr(launcher.time, "time", lambda: anchor + 600.0)
    monkeypatch.setattr(launcher.time, "sleep", lambda seconds: events.append(f"sleep:{seconds}"))
    monkeypatch.setattr(
        launcher.subprocess,
        "run",
        lambda command, check: events.append("run") or SimpleNamespace(returncode=0),
    )

    exit_code = launcher.main(
        [
            "--state",
            str(state),
            "--status",
            str(status),
            "--",
            "python3",
            "worker.py",
        ]
    )

    assert exit_code == 0
    assert events == ["sleep:3015.0", "run"]


def test_launcher_returns_non_quota_failure_without_internal_loop(monkeypatch, tmp_path: Path) -> None:
    state = tmp_path / "state.json"
    status = tmp_path / "launcher-status.json"
    sleeps: list[float] = []
    monkeypatch.setattr(
        launcher.subprocess,
        "run",
        lambda command, check: SimpleNamespace(returncode=2),
    )
    monkeypatch.setattr(launcher.time, "sleep", lambda seconds: sleeps.append(seconds))

    exit_code = launcher.main(
        [
            "--state",
            str(state),
            "--status",
            str(status),
            "--",
            "python3",
            "worker.py",
        ]
    )

    payload = json.loads(status.read_text(encoding="utf-8"))
    assert exit_code == 2
    assert sleeps == []
    assert payload["phase"] == "failed"
    assert payload["childExitCode"] == 2


def test_launcher_quota_retry_limit_is_observable(monkeypatch, tmp_path: Path) -> None:
    state = tmp_path / "state.json"
    status = tmp_path / "launcher-status.json"
    state.write_text("{}", encoding="utf-8")
    sleeps: list[float] = []
    monkeypatch.setattr(
        launcher.subprocess,
        "run",
        lambda command, check: SimpleNamespace(returncode=75),
    )
    monkeypatch.setattr(launcher.time, "sleep", lambda seconds: sleeps.append(seconds))

    exit_code = launcher.main(
        [
            "--state",
            str(state),
            "--status",
            str(status),
            "--quota-minimum-delay-seconds",
            "1",
            "--quota-fallback-delay-seconds",
            "1",
            "--quota-grace-seconds",
            "0",
            "--max-quota-retries",
            "1",
            "--",
            "python3",
            "worker.py",
        ]
    )

    payload = json.loads(status.read_text(encoding="utf-8"))
    assert exit_code == 75
    assert sleeps == [1.0]
    assert payload["phase"] == "quota_retry_exhausted"
    assert payload["quotaExitCount"] == 2
