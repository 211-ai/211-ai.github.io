#!/usr/bin/env python3
"""Evaluate symbolic retrieval reliability on variant lattices (VAS-019)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
REPORT = REPO / "data/voice_app_surface_coverage/reports/retrieval-reliability.json"

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--check", action="store_true")
    args = p.parse_args()
    if not REPORT.is_file():
        print("missing retrieval report", file=sys.stderr)
        return 1
    data = json.loads(REPORT.read_text())
    if args.check and not data.get("meets_thresholds"):
        print("retrieval reliability FAILED:", data.get("failures"), file=sys.stderr)
        return 1
    print(
        "retrieval reliability OK:",
        "meets=", data.get("meets_thresholds"),
        "neg_deny=", data.get("negative_deny_rate"),
    )
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
