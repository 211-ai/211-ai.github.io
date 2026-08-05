#!/usr/bin/env python3
"""Project coverage control status for supervisor dashboards (VAS-029)."""
from __future__ import annotations
import argparse, json, sys
from datetime import datetime, timezone
from pathlib import Path
REPO = Path(__file__).resolve().parents[2]
BASE = REPO / "data/voice_app_surface_coverage"
OUT = BASE / "projection/control-status.json"

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--check", action="store_true")
    p.add_argument("--check-release", action="store_true")
    p.add_argument("--write", action="store_true")
    args = p.parse_args()
    inv = BASE / "baseline/app-surface-inventory.json"
    exp = BASE / "baseline/voice-exposure-matrix.json"
    dens = BASE / "reports/dag-density-full.json"
    ret = BASE / "reports/retrieval-reliability.json"
    audio = BASE / "reports/audio-coverage.json"
    pins = BASE / "baseline/submodule-pins.json"
    status = {
        "schema": "voice-app-surface-coverage/control-status@1",
        "program_id": "voice-app-surface-coverage-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "inventory_surfaces": 0,
        "exposure_classified": 0,
        "density_p0_holes_ok": False,
        "retrieval_meets": False,
        "audio_text_plane_ok": False,
        "audio_audio_plane_ok": False,
        "submodule_decision": None,
    }
    if inv.is_file():
        status["inventory_surfaces"] = json.loads(inv.read_text())["counts"]["surfaces"]
    if exp.is_file():
        e = json.loads(exp.read_text())
        status["exposure_classified"] = len(e.get("surfaces") or [])
        status["exposure_by_class"] = e.get("counts_by_class")
    if dens.is_file():
        status["density_p0_holes_ok"] = bool(json.loads(dens.read_text()).get("all_p0_holes_meet_floor"))
    if ret.is_file():
        status["retrieval_meets"] = bool(json.loads(ret.read_text()).get("meets_thresholds"))
    if audio.is_file():
        a = json.loads(audio.read_text())
        status["audio_text_plane_ok"] = bool(a.get("p0_complete_for_text_plane"))
        status["audio_audio_plane_ok"] = bool(a.get("p0_complete_for_audio_plane"))
        status["audio_counts"] = a.get("counts")
    if pins.is_file():
        status["submodule_decision"] = json.loads(pins.read_text()).get("decision")
    status["overall_ready_for_audio_operator"] = all([
        status["inventory_surfaces"] >= 20,
        status["exposure_classified"] >= 20,
        status["density_p0_holes_ok"],
        status["retrieval_meets"],
        status["audio_text_plane_ok"],
    ])
    if args.write or not (args.check or args.check_release):
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n")
        print("wrote", OUT)
    if args.check or args.check_release:
        if not status["overall_ready_for_audio_operator"]:
            print("projection incomplete", status, file=sys.stderr)
            return 1
        if args.check_release:
            rel = BASE / "reports/program-release-evidence.json"
            if not rel.is_file():
                print("missing program-release-evidence.json", file=sys.stderr)
                return 1
        print("coverage projection OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
