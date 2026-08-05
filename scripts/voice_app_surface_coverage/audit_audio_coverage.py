#!/usr/bin/env python3
"""Audit audio coverage receipts for voice-app-surface-coverage (VAS-022..024)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
REPORTS = REPO / "data/voice_app_surface_coverage/reports"

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--check", action="store_true")
    p.add_argument("--check-stage", action="store_true")
    p.add_argument("--check-regen-receipt", action="store_true")
    args = p.parse_args()
    errors = []
    stage = REPORTS / "audio-stage-receipt.json"
    regen = REPORTS / "audio-regen-batch-p0.json"
    cov = REPORTS / "audio-coverage.json"
    if args.check_stage or args.check:
        if not stage.is_file():
            errors.append("missing audio-stage-receipt.json")
        else:
            d = json.loads(stage.read_text())
            pilot = (d.get("pilot_action_smoke") or {}).get("row_count") or d.get("action_frame_count") or 0
            if int(pilot) < 40 and d.get("status") not in {"smoke_staged", "ready_for_smoke_stage"}:
                errors.append("action_frame_count too low")
            if d.get("status") == "smoke_staged":
                pilot_n = int((d.get("pilot_action_smoke") or {}).get("row_count") or 0)
                surf_n = int((d.get("surface_nav_smoke") or {}).get("row_count") or 0)
                if pilot_n < 40:
                    errors.append(f"pilot smoke rows {pilot_n} < 40")
                if surf_n < 36:
                    errors.append(f"surface smoke rows {surf_n} < 36")
    if args.check_regen_receipt or args.check:
        if not regen.is_file():
            errors.append("missing audio-regen-batch-p0.json")
        else:
            d = json.loads(regen.read_text())
            if d.get("status") not in {"deferred_operator_gate", "completed", "partial"}:
                errors.append(f"unexpected regen status {d.get('status')}")
    if args.check:
        if not cov.is_file():
            errors.append("missing audio-coverage.json")
        else:
            d = json.loads(cov.read_text())
            if not d.get("p0_complete_for_text_plane"):
                errors.append("text plane incomplete")
            if d.get("counts", {}).get("total_frames", 0) < 40:
                errors.append("coverage frame count too low")
    if errors:
        print("audio coverage FAILED:", file=sys.stderr)
        for e in errors:
            print(" -", e, file=sys.stderr)
        return 1
    print("audio coverage OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
