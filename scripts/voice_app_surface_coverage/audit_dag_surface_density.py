#!/usr/bin/env python3
"""Audit DAG + expansion density for voice app surfaces (VAS-015+)."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[2]
REPORTS = REPO / "data/voice_app_surface_coverage/reports"

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--check", action="store_true")
    p.add_argument("--routes", default="")
    p.add_argument("--priority", default="")
    args = p.parse_args()
    full = REPORTS / "dag-density-full.json"
    if not full.is_file():
        print("missing density report; run project expansion first", file=sys.stderr)
        return 1
    data = json.loads(full.read_text())
    errors = []
    if not data.get("all_p0_holes_meet_floor"):
        bad = [r for r in data.get("surfaces", []) if r.get("holes")]
        errors.append(f"density floors not met: {bad}")
    if args.check and errors:
        print("dag density FAILED:", file=sys.stderr)
        for e in errors:
            print(" -", e, file=sys.stderr)
        return 1
    print("dag density OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
