"""World human-aid test safety fixtures."""

from __future__ import annotations

import pytest

from .network_guard import NetworkAttempt, install_network_guard


@pytest.fixture(autouse=True)
def world_aid_network_deny(monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest):
    """Deny and report every non-loopback Python network attempt."""

    attempts: list[NetworkAttempt] = []
    install_network_guard(monkeypatch, attempts)
    yield attempts
    if attempts and request.node.get_closest_marker("world_aid_egress_canary") is None:
        rendered = ", ".join(f"{attempt.surface}={attempt.target}" for attempt in attempts)
        pytest.fail(f"unexpected World human-aid network attempts: {rendered}")
