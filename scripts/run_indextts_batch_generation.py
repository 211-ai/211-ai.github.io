#!/usr/bin/env python3
"""Run resumable IndexTTS precompute jobs in small deduplicated batches."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
DEFAULT_STATE = REPO_ROOT / "docs/211_indextts_batch_generation_state.json"
DEFAULT_BATCH_MANIFEST_DIR = REPO_ROOT / "docs/211_indextts_precompute_batches"
DEFAULT_PROGRESS_DIR = REPO_ROOT / "docs/211_indextts_precompute_progress"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--remote-batch-size", type=int, default=int(os.getenv("WALLET_INDEXTTS_REMOTE_BATCH_SIZE", "32") or "32"))
    parser.add_argument("--parallel-workers", type=int, default=int(os.getenv("WALLET_INDEXTTS_PARALLEL_WORKERS", "1") or "1"))
    parser.add_argument("--max-runtime-seconds", type=float, default=8 * 60 * 60)
    parser.add_argument("--start-offset", type=int, default=0)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--batch-manifest-dir", type=Path, default=DEFAULT_BATCH_MANIFEST_DIR)
    parser.add_argument("--progress-dir", type=Path, default=DEFAULT_PROGRESS_DIR)
    parser.add_argument("--output-dir", type=Path, default=REPO_ROOT / "wallet_interface/ui/public/assets/audio/precomputed/211-dag-indextts")
    parser.add_argument("--public-manifest", type=Path, default=REPO_ROOT / "wallet_interface/ui/public/assets/audio/precomputed/211-dag-indextts/manifest.json")
    parser.add_argument("--response-manifest", type=Path, default=None)
    parser.add_argument("--dag", type=Path, default=REPO_ROOT / "docs/211_conversation_dag.json")
    parser.add_argument("--results", type=Path, default=REPO_ROOT / "docs/211_chatbot_simulation_results.json")
    parser.add_argument("--stop-on-error", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--validate-transcripts", action="store_true")
    parser.add_argument("--transcript-validation-limit", type=int, default=1)
    parser.add_argument("--transcript-validation-model", default="tiny.en")
    parser.add_argument("--transcript-validation-language", default="en")
    parser.add_argument("--transcript-validation-device", default="auto")
    parser.add_argument("--transcript-validation-threshold", type=float, default=0.72)
    parser.add_argument("--transcript-validation-soft-fail", action="store_true")
    return parser.parse_args()


def total_response_count(response_manifest: Path | None, dag: Path, results: Path) -> int:
    from scripts.precompute_indextts_responses import load_audio_responses, load_audio_responses_from_manifest

    if response_manifest is not None:
        return len(load_audio_responses_from_manifest(response_manifest))
    return len(load_audio_responses(dag, results))


def write_state(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> None:
    args = parse_args()
    args.batch_manifest_dir.mkdir(parents=True, exist_ok=True)
    args.progress_dir.mkdir(parents=True, exist_ok=True)
    started_at = time.time()
    deadline = started_at + max(0.0, args.max_runtime_seconds)
    total = total_response_count(args.response_manifest, args.dag, args.results)
    offset = max(0, args.start_offset)
    batches_completed = 0
    failures = 0

    while offset < total and time.time() < deadline:
        batch_index = offset // max(1, args.batch_size)
        manifest = args.batch_manifest_dir / f"batch-{batch_index:05d}-offset-{offset:06d}.json"
        progress = args.progress_dir / f"batch-{batch_index:05d}-offset-{offset:06d}.progress.json"
        remaining_seconds = max(1, int(deadline - time.time()))
        cmd = [
            "python3",
            str(REPO_ROOT / "scripts/precompute_indextts_responses.py"),
            "--offset",
            str(offset),
            "--limit",
            str(args.batch_size),
            "--max-runtime-seconds",
            str(remaining_seconds),
            "--output-dir",
            str(args.output_dir),
            "--manifest",
            str(manifest),
            "--public-manifest",
            str(args.public_manifest),
            "--progress-json",
            str(progress),
            "--remote-batch-size",
            str(args.remote_batch_size),
            "--parallel-workers",
            str(args.parallel_workers),
        ]
        if args.response_manifest is not None:
            cmd.extend(["--response-manifest", str(args.response_manifest)])
        else:
            cmd.extend(["--dag", str(args.dag), "--results", str(args.results)])
        if args.force:
            cmd.append("--force")
        if args.stop_on_error:
            cmd.append("--stop-on-error")
        if args.validate_transcripts:
            cmd.extend(
                [
                    "--validate-transcripts",
                    "--transcript-validation-limit",
                    str(args.transcript_validation_limit),
                    "--transcript-validation-model",
                    args.transcript_validation_model,
                    "--transcript-validation-language",
                    args.transcript_validation_language,
                    "--transcript-validation-device",
                    args.transcript_validation_device,
                    "--transcript-validation-threshold",
                    str(args.transcript_validation_threshold),
                ]
            )
        if args.transcript_validation_soft_fail:
            cmd.append("--transcript-validation-soft-fail")

        print(f"[batch {batch_index}] offset={offset} size={args.batch_size} remaining={remaining_seconds}s")
        completed = subprocess.run(cmd, cwd=REPO_ROOT)
        if completed.returncode != 0:
            failures += 1
            if args.stop_on_error:
                break
        batches_completed += 1
        offset += args.batch_size
        write_state(
            args.state,
            {
                "schemaVersion": 1,
                "updatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "elapsedSeconds": round(time.time() - started_at, 3),
                "totalResponses": total,
                "nextOffset": offset,
                "batchSize": args.batch_size,
                "batchesCompleted": batches_completed,
                "failures": failures,
                "lastManifest": str(manifest),
                "lastProgress": str(progress),
            },
        )

    print(f"Finished batch loop at offset {offset}/{total}; batches={batches_completed}; failures={failures}")


if __name__ == "__main__":
    main()
