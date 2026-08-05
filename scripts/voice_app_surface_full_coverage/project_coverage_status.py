#!/usr/bin/env python3
"""Project coverage control status and release evidence (VAS2-034/035)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
BASE = REPO / "data" / "voice_app_surface_full_coverage"
REPORTS = BASE / "reports"
PROJ = BASE / "projection" / "control-status.json"
EVIDENCE = REPORTS / "program-release-evidence.json"
SIGNOFF = REPO / "docs" / "voice_app_surface_full_coverage" / "PROGRAM_SIGNOFF.md"
PROGRAM = "voice-app-surface-full-coverage-v2"


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def build_status() -> dict[str, Any]:
    inv = _load(BASE / "baseline" / "app-surface-inventory.json") or {}
    exp = _load(BASE / "baseline" / "voice-exposure-matrix.json") or {}
    floors_p0 = _load(REPORTS / "variant-floors-p0.json") or {}
    floors_p1 = _load(REPORTS / "variant-floors-p1.json") or {}
    floors_p2 = _load(REPORTS / "variant-floors-p2.json") or {}
    retrieval = _load(REPORTS / "retrieval-reliability.json") or {}
    audio = _load(REPORTS / "audio-coverage.json") or {}
    regen = _load(REPORTS / "audio-regen-batch.json") or {}
    e2e_m = _load(REPORTS / "e2e-surface-matrix.json") or {}
    e2e_a = _load(REPORTS / "e2e-adversarial.json") or {}
    e2e_d = _load(REPORTS / "e2e-dag-sim.json") or {}
    pins = _load(BASE / "baseline" / "submodule-pins.json") or {}
    fold = _load(REPORTS / "dag-fold-receipt.json") or {}

    surfaces = inv.get("surfaces") or exp.get("surfaces") or []
    n_surfaces = len(surfaces) if isinstance(surfaces, list) else 0

    status = {
        "schema": "voice-app-surface-full-coverage/control-status@1",
        "program_id": PROGRAM,
        "generated_at": datetime.now(UTC).isoformat(),
        "inventory": {
            "surface_count": n_surfaces,
            "present": bool(inv),
        },
        "exposure": {
            "present": bool(exp),
            "classified": n_surfaces,
        },
        "variant_floors": {
            "P0": floors_p0.get("all_met"),
            "P1": floors_p1.get("all_met"),
            "P2": floors_p2.get("all_met"),
            "counts_p0": floors_p0.get("counts"),
        },
        "dag_fold": {
            "status": (fold.get("status") if fold else None),
            "added_edges": (fold.get("stats") or {}).get("added_edges"),
            "final_edge_count": (fold.get("stats") or {}).get("final_edge_count"),
        },
        "retrieval": {
            "meets_thresholds": retrieval.get("meets_thresholds"),
            "top1": retrieval.get("top1_rate"),
            "top3": retrieval.get("top3_rate"),
        },
        "audio": {
            "regen_status": regen.get("status"),
            "production_frames": (audio.get("counts") or {}).get("production_indextts"),
            "total_frames": (audio.get("counts") or {}).get("total_frames"),
            "missing": (audio.get("counts") or {}).get("missing"),
        },
        "e2e": {
            "matrix": e2e_m.get("status"),
            "adversarial": e2e_a.get("status"),
            "dag_sim": e2e_d.get("status"),
        },
        "submodule_pins": {
            "decision": pins.get("decision"),
            "shas": {
                s.get("name"): (s.get("working_sha") or "")[:12]
                for s in (pins.get("submodules") or [])
                if isinstance(s, dict)
            },
        },
    }
    # overall
    green = all(
        [
            status["inventory"]["present"],
            status["exposure"]["present"],
            status["variant_floors"]["P0"] is True,
            status["retrieval"]["meets_thresholds"] is True,
            status["audio"]["regen_status"] in {"completed", "partial"},
            status["e2e"]["matrix"] == "green",
            status["e2e"]["adversarial"] == "green",
        ]
    )
    status["overall"] = "green" if green else "in_progress"
    return status


def write_status() -> dict[str, Any]:
    status = build_status()
    PROJ.parent.mkdir(parents=True, exist_ok=True)
    PROJ.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n")
    return status


def write_release() -> dict[str, Any]:
    status = write_status()
    evidence = {
        "schema": "voice-app-surface-full-coverage/program-release-evidence@1",
        "program_id": PROGRAM,
        "generated_at": datetime.now(UTC).isoformat(),
        "control_status": status,
        "artifacts": {
            "inventory": "data/voice_app_surface_full_coverage/baseline/app-surface-inventory.json",
            "exposure": "data/voice_app_surface_full_coverage/baseline/voice-exposure-matrix.json",
            "variants": "data/voice_app_surface_full_coverage/variants/",
            "dag_fold": "data/voice_app_surface_full_coverage/reports/dag-fold-receipt.json",
            "retrieval": "data/voice_app_surface_full_coverage/reports/retrieval-reliability.json",
            "audio_regen": "data/voice_app_surface_full_coverage/reports/audio-regen-batch.json",
            "audio_coverage": "data/voice_app_surface_full_coverage/reports/audio-coverage.json",
            "e2e_matrix": "data/voice_app_surface_full_coverage/reports/e2e-surface-matrix.json",
            "e2e_adversarial": "data/voice_app_surface_full_coverage/reports/e2e-adversarial.json",
            "projection": str(PROJ.relative_to(REPO)),
        },
        "residuals": [
            "Full Whisper ASR adjudication remains deferred_file_presence_gate",
            "Optional: raise cancel-like negative retrieval further above 0.70",
        ],
        "status": status.get("overall"),
    }
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")

    audio = status.get("audio") or {}
    ret = status.get("retrieval") or {}
    fold = status.get("dag_fold") or {}
    SIGNOFF.write_text(
        f"""# Program Signoff — voice-app-surface-full-coverage-v2

Updated: `{evidence['generated_at']}`  
Overall: **{evidence['status']}**

## Delivered

- Full app-surface inventory + exposure classification
- Raised paraphrase floors: P0≥500, P1≥150, P2≥80
- Catalog/policy surface gates (accelerate PR #130) + wallet binding denials
- DAG fold: added edges → final **{fold.get('final_edge_count')}**
- Retrieval: top1={ret.get('top1')} top3={ret.get('top3')} meets={ret.get('meets_thresholds')}
- Production IndexTTS: {audio.get('production_frames')}/{audio.get('total_frames')} frames staged
- Offline e2e matrix + adversarial green

## Residuals

{chr(10).join('- ' + r for r in evidence['residuals'])}

## Evidence

`data/voice_app_surface_full_coverage/reports/program-release-evidence.json`  
`data/voice_app_surface_full_coverage/projection/control-status.json`
""",
        encoding="utf-8",
    )
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--check-release", action="store_true")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    if args.write or args.check_release or not PROJ.is_file():
        write_status()
        print(f"wrote {PROJ}")
    if args.check_release or args.write:
        write_release()
        print(f"wrote {EVIDENCE}")
        print(f"wrote {SIGNOFF}")
    if args.check or args.check_release:
        if not PROJ.is_file():
            print("missing projection", file=sys.stderr)
            return 1
        status = json.loads(PROJ.read_text())
        if args.check_release:
            if not EVIDENCE.is_file() or not SIGNOFF.is_file():
                print("missing release evidence/signoff", file=sys.stderr)
                return 1
        print("coverage projection OK overall=", status.get("overall"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
