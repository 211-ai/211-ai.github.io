from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from scripts import wait_for_hf_space_hardware as gate


def runtime(
    *,
    stage: str = "RUNNING",
    hardware: str = "l40sx1",
    requested_hardware: str = "l40sx1",
    domain_stage: str = "READY",
    revision: str = "9ecca0d440939e08fea1292bccf31d6724616312",
) -> SimpleNamespace:
    return SimpleNamespace(
        stage=stage,
        hardware=hardware,
        requested_hardware=requested_hardware,
        raw={"domains": [{"stage": domain_stage}], "sha": revision},
    )


def test_runtime_ready_requires_running_expected_hardware_and_domain() -> None:
    expected = gate.runtime_snapshot(runtime())
    assert gate.runtime_ready(expected, "l40sx1") is True

    building = gate.runtime_snapshot(runtime(stage="RUNNING_BUILDING"))
    wrong_current = gate.runtime_snapshot(runtime(hardware="zero-a10g"))
    wrong_requested = gate.runtime_snapshot(
        runtime(requested_hardware="zero-a10g")
    )
    pending_domain = gate.runtime_snapshot(runtime(domain_stage="BUILDING"))

    assert gate.runtime_ready(building, "l40sx1") is False
    assert gate.runtime_ready(wrong_current, "l40sx1") is False
    assert gate.runtime_ready(wrong_requested, "l40sx1") is False
    assert gate.runtime_ready(pending_domain, "l40sx1") is False


def test_runtime_ready_can_require_deployed_revision() -> None:
    expected = gate.runtime_snapshot(runtime())
    assert gate.runtime_ready(expected, "l40sx1", "9ecca0d") is True
    assert gate.runtime_ready(expected, "l40sx1", "c238158") is False


def test_wait_fails_closed_on_running_revision_drift() -> None:
    api = SimpleNamespace(
        get_space_runtime=lambda _repo: runtime(revision="c238158")
    )
    assert (
        gate.wait_for_hardware(
            api,
            space_repo_id="Publicus/IndexTTS-2-Demo",
            expected_hardware="l40sx1",
            expected_revision="9ecca0d",
            timeout_seconds=30,
            poll_interval_seconds=1,
            clock=lambda: 0,
            sleeper=lambda _seconds: None,
        )
        == gate.EXIT_HARDWARE_DRIFT
    )


def test_wait_fails_closed_on_requested_hardware_drift() -> None:
    api = SimpleNamespace(
        get_space_runtime=lambda _repo: runtime(
            hardware="zero-a10g",
            requested_hardware="zero-a10g",
        )
    )
    assert (
        gate.wait_for_hardware(
            api,
            space_repo_id="Publicus/IndexTTS-2-Demo",
            expected_hardware="l40sx1",
            timeout_seconds=30,
            poll_interval_seconds=1,
            clock=lambda: 0,
            sleeper=lambda _seconds: None,
        )
        == gate.EXIT_HARDWARE_DRIFT
    )


def test_wait_allows_transition_to_expected_hardware() -> None:
    runtimes = iter(
        [
            runtime(
                stage="RUNNING_BUILDING",
                hardware="zero-a10g",
                requested_hardware="l40sx1",
            ),
            runtime(),
        ]
    )
    api = SimpleNamespace(get_space_runtime=lambda _repo: next(runtimes))

    assert (
        gate.wait_for_hardware(
            api,
            space_repo_id="Publicus/IndexTTS-2-Demo",
            expected_hardware="l40sx1",
            timeout_seconds=30,
            poll_interval_seconds=1,
            clock=lambda: 0,
            sleeper=lambda _seconds: None,
        )
        == 0
    )


def test_complete_checkpoint_skips_runtime_and_wake(tmp_path: Path) -> None:
    checkpoint = tmp_path / "state.json"
    checkpoint.write_text(
        json.dumps({"nextOffset": 3906, "totalResponses": 3906}),
        encoding="utf-8",
    )

    class UnexpectedApi:
        def get_space_runtime(self, _repo: str) -> None:
            raise AssertionError("completed queue must not query or wake the Space")

    assert (
        gate.wait_for_hardware(
            UnexpectedApi(),
            space_repo_id="Publicus/IndexTTS-2-Demo",
            expected_hardware="l40sx1",
            timeout_seconds=30,
            poll_interval_seconds=1,
            checkpoint=checkpoint,
            wake_sleeping=True,
        )
        == 0
    )


def test_sleeping_expected_hardware_is_restarted_once() -> None:
    runtimes = iter(
        [
            runtime(stage="SLEEPING", domain_stage="SLEEPING"),
            runtime(stage="RUNNING_BUILDING", domain_stage="BUILDING"),
            runtime(),
        ]
    )
    restarts: list[str] = []
    api = SimpleNamespace(
        get_space_runtime=lambda _repo: next(runtimes),
        restart_space=lambda repo: restarts.append(repo),
    )

    assert (
        gate.wait_for_hardware(
            api,
            space_repo_id="Publicus/IndexTTS-2-Demo",
            expected_hardware="l40sx1",
            timeout_seconds=30,
            poll_interval_seconds=1,
            wake_sleeping=True,
            clock=lambda: 0,
            sleeper=lambda _seconds: None,
        )
        == 0
    )
    assert restarts == ["Publicus/IndexTTS-2-Demo"]
