#!/usr/bin/env python3
"""Whisper-adjudicate production audio for VAS2-028 residual.

Uses transformers openai/whisper-tiny.en offline on staged production WAVs.
Compares transcripts to expected spoken_text via normalized similarity (bp).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.review_abby_regeneration_audio import (  # noqa: E402
    content_word_coverage_bp,
    normalized_review_text,
    normalized_similarity_bp,
)

RESOLVER = (
    REPO
    / "data/voice_app_surface_full_coverage/audio/stage/production/metadata"
    / "abby_action_precomputed_audio_resolver.jsonl"
)
REPORT = (
    REPO
    / "data/voice_app_surface_full_coverage/reports/whisper-adjudication.json"
)
LEDGER = (
    REPO
    / "data/voice_app_surface_full_coverage/reports/whisper-adjudication-ledger.jsonl"
)
PROGRAM = "voice-app-surface-full-coverage-v2"
DEFAULT_PASS_BP = 7000  # 70%
DEFAULT_MODEL = "openai/whisper-tiny.en"


def load_resolver(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--pass-bp", type=int, default=DEFAULT_PASS_BP)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    if args.check and not args.write:
        if not REPORT.is_file():
            print("missing whisper report", file=sys.stderr)
            return 1
        d = json.loads(REPORT.read_text())
        if d.get("status") not in {"completed", "partial"}:
            print(f"status={d.get('status')}", file=sys.stderr)
            return 1
        if not d.get("meets_pass_rate"):
            print("whisper pass rate below threshold", d.get("summary"), file=sys.stderr)
            return 1
        print(
            "whisper adjudication OK",
            d.get("summary"),
        )
        return 0

    if not RESOLVER.is_file():
        print(f"missing resolver {RESOLVER}", file=sys.stderr)
        return 1
    rows = load_resolver(RESOLVER)
    if args.limit:
        rows = rows[: args.limit]

    from transformers import pipeline

    t0 = time.time()
    pipe = pipeline(
        "automatic-speech-recognition",
        model=args.model,
        device=-1,
    )
    load_s = time.time() - t0

    results: list[dict[str, Any]] = []
    passed = 0
    failed = 0
    errors = 0

    for i, row in enumerate(rows, 1):
        audio_rel = str(row.get("audio_path") or "")
        audio_path = REPO / audio_rel
        expected = str(row.get("spoken_text") or "")
        item: dict[str, Any] = {
            "frame_id": row.get("frame_id"),
            "audio_path": audio_rel,
            "expected_text": expected,
            "index": i,
        }
        if not audio_path.is_file():
            item["status"] = "missing_audio"
            errors += 1
            results.append(item)
            continue
        try:
            t1 = time.time()
            # Long clips need timestamps for transformers Whisper long-form path.
            try:
                out = pipe(str(audio_path), return_timestamps=True)
            except TypeError:
                out = pipe(str(audio_path))
            if isinstance(out, dict):
                hyp = str(out.get("text") or "").strip()
            else:
                hyp = str(out or "").strip()
            sim = normalized_similarity_bp(expected, hyp)
            cov = content_word_coverage_bp(expected, hyp)
            ok = sim >= args.pass_bp
            item.update(
                {
                    "status": "pass" if ok else "fail",
                    "hypothesis_text": hyp,
                    "similarity_bp": sim,
                    "content_word_coverage_bp": cov,
                    "normalized_expected": normalized_review_text(expected),
                    "normalized_hypothesis": normalized_review_text(hyp),
                    "latency_ms": int((time.time() - t1) * 1000),
                }
            )
            if ok:
                passed += 1
            else:
                failed += 1
        except Exception as exc:  # noqa: BLE001
            item["status"] = "error"
            item["error"] = f"{type(exc).__name__}: {exc}"
            errors += 1
        results.append(item)
        if i % 10 == 0 or i == len(rows):
            print(f"[{i}/{len(rows)}] pass={passed} fail={failed} err={errors}", flush=True)

    n = max(1, len(results))
    pass_rate = passed / n
    # Require ≥90% pass among adjudicated rows with audio
    adjudicated = [r for r in results if r.get("status") in {"pass", "fail"}]
    adj_n = max(1, len(adjudicated))
    adj_pass = sum(1 for r in adjudicated if r["status"] == "pass") / adj_n
    # Allow tiny error budget for long-form edge cases if adjudicated quality is solid.
    error_rate = errors / n
    meets = adj_pass >= 0.90 and error_rate <= 0.02

    report = {
        "schema": "voice-app-surface-full-coverage/whisper-adjudication@1",
        "program_id": PROGRAM,
        "task_id": "VAS2-028",
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "completed" if meets else "partial",
        "model": args.model,
        "pass_bp_threshold": args.pass_bp,
        "resolver_path": str(RESOLVER.relative_to(REPO)),
        "ledger_path": str(LEDGER.relative_to(REPO)),
        "summary": {
            "total": len(results),
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "pass_rate": round(pass_rate, 4),
            "adjudicated_pass_rate": round(adj_pass, 4),
            "model_load_seconds": round(load_s, 3),
            "elapsed_seconds": round(time.time() - t0, 3),
        },
        "meets_pass_rate": meets,
        "failures": [
            {
                "frame_id": r.get("frame_id"),
                "similarity_bp": r.get("similarity_bp"),
                "expected": (r.get("expected_text") or "")[:120],
                "hypothesis": (r.get("hypothesis_text") or "")[:120],
            }
            for r in results
            if r.get("status") == "fail"
        ][:30],
        "note": "transformers openai/whisper-tiny.en CPU adjudication against production IndexTTS WAVs.",
    }

    if args.write or True:
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        LEDGER.write_text(
            "".join(json.dumps(r, sort_keys=True) + "\n" for r in results),
            encoding="utf-8",
        )
        print(json.dumps(report["summary"] | {"status": report["status"], "meets": meets}, indent=2))

    if args.check:
        if not meets:
            print("whisper adjudication FAILED", report["summary"], file=sys.stderr)
            return 1
        print("whisper adjudication OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
