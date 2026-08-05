#!/usr/bin/env python3
"""Audit audio coverage for VAS2-026..029."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
REPO=Path(__file__).resolve().parents[2]
REPORTS=REPO/"data/voice_app_surface_full_coverage/reports"

def main()->int:
    p=argparse.ArgumentParser(); p.add_argument("--check", action="store_true")
    p.add_argument("--check-stage", action="store_true"); p.add_argument("--check-regen", action="store_true")
    p.add_argument("--check-whisper", action="store_true"); args=p.parse_args()
    errors=[]
    stage=REPORTS/"audio-stage-receipt.json"
    regen=REPORTS/"audio-regen-batch.json"
    cov=REPORTS/"audio-coverage.json"
    wh=REPORTS/"whisper-adjudication.json"
    if args.check or args.check_stage:
        if not stage.is_file(): errors.append("missing stage receipt")
        else:
            d=json.loads(stage.read_text())
            if d.get("status") not in {"offline_smoke_staged","production_staged","partial_production_staged"}:
                errors.append(f"bad stage status {d.get('status')}")
    if args.check or args.check_regen:
        if not regen.is_file(): errors.append("missing regen receipt")
        else:
            d=json.loads(regen.read_text())
            if d.get("status") not in {"completed","partial"}:
                errors.append(f"bad regen status {d.get('status')}")
    if args.check:
        if not cov.is_file(): errors.append("missing coverage")
        else:
            d=json.loads(cov.read_text())
            if not d.get("p0_complete_for_text_plane"): errors.append("text plane incomplete")
            if d.get("counts",{}).get("total_frames",0) < 40: errors.append("too few frames")
    if args.check or args.check_whisper:
        if not wh.is_file(): errors.append("missing whisper receipt")
    if errors:
        print("audio coverage FAILED:", file=sys.stderr)
        for e in errors: print(" -", e, file=sys.stderr)
        return 1
    print("audio coverage OK")
    return 0
if __name__=="__main__":
    raise SystemExit(main())
