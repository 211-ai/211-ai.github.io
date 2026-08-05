#!/usr/bin/env python3
"""Verify pilot catalog covers P0 exposure-matrix logical actions (VAS-008)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "ipfs_accelerate_py"))
sys.path.insert(0, str(REPO_ROOT))

from ipfs_accelerate_py.action_runtime.catalog_211ai import (  # noqa: E402
    PILOT_LOGICAL_ACTIONS,
    logical_action_to_descriptor_id,
)

EXPOSURE = (
    REPO_ROOT
    / "data"
    / "voice_app_surface_coverage"
    / "baseline"
    / "voice-exposure-matrix.json"
)


def check() -> list[str]:
    errors: list[str] = []
    if not EXPOSURE.is_file():
        return [f"missing exposure matrix {EXPOSURE}"]
    matrix = json.loads(EXPOSURE.read_text(encoding="utf-8"))
    catalog = set(PILOT_LOGICAL_ACTIONS)
    mapping = logical_action_to_descriptor_id()
    required: set[str] = set()
    for row in matrix.get("surfaces") or []:
        if row.get("priority") != "P0":
            continue
        if row.get("exposure_class") not in {"voice_navigable", "voice_actionable"}:
            continue
        for action in row.get("logical_actions") or []:
            required.add(str(action))
    missing = sorted(required - catalog)
    if missing:
        errors.append(f"P0 logical actions missing from catalog: {missing}")
    for action in sorted(required):
        if action not in mapping:
            errors.append(f"no descriptor mapping for {action}")
    if "open_app_surface" not in catalog:
        errors.append("open_app_surface required for navigable surfaces")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    errors = check()
    if errors:
        print("catalog surface coverage FAILED:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1
    print("catalog surface coverage OK")
    return 0 if args.check or True else 0


if __name__ == "__main__":
    raise SystemExit(main())
