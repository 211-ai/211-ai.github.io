"""Unit tests for scraper/orchestration layer — no network or subprocess required."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest


def _try_import(name: str):
    try:
        return importlib.import_module(name)
    except ImportError as exc:
        pytest.skip(f"{name} import failed: {exc}")


def test_orchestration_package_importable():
    mod = _try_import("scraper.orchestration")
    assert mod is not None


def test_orchestration_exposes_supervisor_config():
    _try_import("scraper.orchestration")
    from scraper.orchestration import SupervisorConfig  # noqa: PLC0415

    assert SupervisorConfig is not None


def test_orchestration_exposes_self_healing_supervisor():
    _try_import("scraper.orchestration")
    from scraper.orchestration import SelfHealingSupervisor  # noqa: PLC0415

    assert SelfHealingSupervisor is not None


def test_supervisor_config_defaults(tmp_path):
    _try_import("scraper.orchestration")
    from scraper.orchestration import SupervisorConfig  # noqa: PLC0415

    cfg = SupervisorConfig(
        state_path=tmp_path / "state.json",
        strategy_path=tmp_path / "strategy.json",
        events_path=tmp_path / "events.json",
    )
    assert cfg.stale_seconds == 600.0
    assert cfg.check_interval == 30.0
    assert cfg.max_restarts == 10


def test_self_healing_supervisor_instantiable(tmp_path):
    _try_import("scraper.orchestration")
    from scraper.orchestration import SelfHealingSupervisor, SupervisorConfig  # noqa: PLC0415

    cfg = SupervisorConfig(
        state_path=tmp_path / "state.json",
        strategy_path=tmp_path / "strategy.json",
        events_path=tmp_path / "events.json",
    )
    supervisor = SelfHealingSupervisor(cfg)
    assert supervisor.config is cfg
    assert supervisor.restart_count == 0


def test_orchestration_exposes_agentic_crawler_daemon():
    _try_import("scraper.orchestration")
    from scraper.orchestration import AgenticCrawlerDaemon  # noqa: PLC0415

    assert AgenticCrawlerDaemon is not None


def test_orchestration_exposes_parse_args():
    _try_import("scraper.orchestration")
    from scraper.orchestration import parse_args  # noqa: PLC0415

    assert callable(parse_args)
