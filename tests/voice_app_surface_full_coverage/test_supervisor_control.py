"""VAS2-001 supervisor control unit checks."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "voice_app_surface_full_coverage" / "supervisor_control.py"


def _load():
    spec = importlib.util.spec_from_file_location("vas2_supervisor_control", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_validate_config_ok():
    mod = _load()
    result = mod.validate_config()
    assert result["valid"] is True, result.get("errors")
    assert result["program_id"] == "voice-app-surface-full-coverage-v2"
    assert result["refill_owner_lane_id"] == "vas2-grok-0"


def test_lane_plan_has_four_shards():
    mod = _load()
    plan = mod.print_lane_plan()
    assert plan["task_shard_count"] == 4
    assert len(plan["lanes"]) == 4
