#!/usr/bin/env python3
"""Run resumable IndexTTS precompute jobs in small deduplicated batches."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from json import JSONDecodeError
from pathlib import Path
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
DEFAULT_STATE = REPO_ROOT / "docs/211_indextts_batch_generation_state.json"
DEFAULT_BATCH_MANIFEST_DIR = REPO_ROOT / "docs/211_indextts_precompute_batches"
DEFAULT_PROGRESS_DIR = REPO_ROOT / "docs/211_indextts_precompute_progress"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "wallet_interface/ui/public/assets/audio/precomputed/211-dag-indextts"
DEFAULT_PUBLIC_MANIFEST = DEFAULT_OUTPUT_DIR / "manifest.json"
DEFAULT_INDEXTTS_SPACE_URL = "https://publicus-indextts-2-demo.hf.space"
DEFAULT_INDEXTTS_MODEL_NAME = "Publicus/IndexTTS-2-Demo"
DEFAULT_INDEXTTS_REMOTE_BATCH_SIZE = 4
CANONICAL_DATASET_ROOT = REPO_ROOT / "tmp_assets/hf-abby-tts-canonical-dataset"
DEFAULT_FULL_RESPONSE_MANIFEST = CANONICAL_DATASET_ROOT / "metadata/regeneration-full-responses.json"
DEFAULT_FULL_STATE = CANONICAL_DATASET_ROOT / "metadata/regeneration-batch-state.json"
DEFAULT_FULL_BATCH_MANIFEST_DIR = CANONICAL_DATASET_ROOT / "metadata/regeneration-batches"
DEFAULT_FULL_PROGRESS_DIR = CANONICAL_DATASET_ROOT / "metadata/regeneration-progress"
DEFAULT_FULL_OUTPUT_DIR = CANONICAL_DATASET_ROOT / "audio"
DEFAULT_FULL_PUBLIC_MANIFEST = CANONICAL_DATASET_ROOT / "metadata/regeneration-audio-manifest.json"
EXIT_SUCCESS = 0
EXIT_BATCH_FAILED = 1
EXIT_RATE_LIMITED = 75
EXIT_RUNTIME_LIMIT = 124


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument(
        "--remote-batch-size",
        type=int,
        default=int(
            os.getenv(
                "WALLET_INDEXTTS_REMOTE_BATCH_SIZE",
                str(DEFAULT_INDEXTTS_REMOTE_BATCH_SIZE),
            )
            or str(DEFAULT_INDEXTTS_REMOTE_BATCH_SIZE)
        ),
    )
    parser.add_argument("--parallel-workers", type=int, default=int(os.getenv("WALLET_INDEXTTS_PARALLEL_WORKERS", "1") or "1"))
    parser.add_argument(
        "--space-url",
        default=os.getenv("WALLET_INDEXTTS_SPACE_URL", DEFAULT_INDEXTTS_SPACE_URL).strip() or DEFAULT_INDEXTTS_SPACE_URL,
    )
    parser.add_argument(
        "--model-name",
        default=os.getenv("WALLET_INDEXTTS_MODEL_NAME", DEFAULT_INDEXTTS_MODEL_NAME).strip() or DEFAULT_INDEXTTS_MODEL_NAME,
    )
    parser.add_argument("--bucket-uri", default=os.getenv("WALLET_INDEXTTS_BUCKET_URI", "").strip())
    parser.add_argument("--require-upload-capable-batch", action="store_true")
    batch_requirement = parser.add_mutually_exclusive_group()
    batch_requirement.add_argument(
        "--require-batch",
        dest="require_batch",
        action="store_true",
        default=True,
        help="Fail closed instead of silently falling back to gen_single.",
    )
    batch_requirement.add_argument(
        "--allow-single-fallback",
        dest="require_batch",
        action="store_false",
        help="Explicitly permit gen_single fallback for a legacy or alternate endpoint.",
    )
    parser.add_argument(
        "--batch-retry-attempts",
        type=int,
        default=int(os.getenv("WALLET_INDEXTTS_BATCH_RETRY_ATTEMPTS", "2") or "2"),
    )
    parser.add_argument(
        "--batch-retry-backoff-seconds",
        type=float,
        default=float(os.getenv("WALLET_INDEXTTS_BATCH_RETRY_BACKOFF_SECONDS", "15") or "15"),
    )
    parser.add_argument(
        "--batch-retry-backoff-multiplier",
        type=float,
        default=float(os.getenv("WALLET_INDEXTTS_BATCH_RETRY_BACKOFF_MULTIPLIER", "2") or "2"),
    )
    parser.add_argument(
        "--batch-retry-max-backoff-seconds",
        type=float,
        default=float(os.getenv("WALLET_INDEXTTS_BATCH_RETRY_MAX_BACKOFF_SECONDS", "120") or "120"),
    )
    parser.add_argument(
        "--max-runtime-seconds",
        type=float,
        default=0.0,
        help="Maximum per-phase runtime in seconds. Use 0 to disable the deadline and run until the backlog is complete.",
    )
    parser.add_argument("--start-offset", type=int, default=0)
    resume_group = parser.add_mutually_exclusive_group()
    resume_group.add_argument(
        "--resume",
        dest="resume",
        action="store_true",
        default=True,
        help="Resume a compatible existing state checkpoint (default).",
    )
    resume_group.add_argument(
        "--no-resume",
        dest="resume",
        action="store_false",
        help="Ignore an existing checkpoint and start from --start-offset.",
    )
    parser.add_argument(
        "--reset-state",
        action="store_true",
        help="Ignore any existing checkpoint and replace it as this run progresses.",
    )
    parser.add_argument(
        "--regeneration-full",
        action="store_true",
        help="Use the canonical 3,908-row regeneration response manifest and dataset-local output/checkpoint paths.",
    )
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--batch-manifest-dir", type=Path, default=DEFAULT_BATCH_MANIFEST_DIR)
    parser.add_argument("--progress-dir", type=Path, default=DEFAULT_PROGRESS_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--public-manifest", type=Path, default=DEFAULT_PUBLIC_MANIFEST)
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
    parser.add_argument("--prune-local-audio-after-sync", action="store_true",
        help="Pass --prune-local-audio-after-sync to precompute; deletes local audio after each bucket sync.")
    args = parser.parse_args(argv)
    return configure_regeneration_full(args)


def configure_regeneration_full(args: argparse.Namespace) -> argparse.Namespace:
    if not bool(getattr(args, "regeneration_full", False)):
        return args
    if args.response_manifest is None:
        args.response_manifest = DEFAULT_FULL_RESPONSE_MANIFEST
    if args.state == DEFAULT_STATE:
        args.state = DEFAULT_FULL_STATE
    if args.batch_manifest_dir == DEFAULT_BATCH_MANIFEST_DIR:
        args.batch_manifest_dir = DEFAULT_FULL_BATCH_MANIFEST_DIR
    if args.progress_dir == DEFAULT_PROGRESS_DIR:
        args.progress_dir = DEFAULT_FULL_PROGRESS_DIR
    if args.output_dir == DEFAULT_OUTPUT_DIR:
        args.output_dir = DEFAULT_FULL_OUTPUT_DIR
    if args.public_manifest == DEFAULT_PUBLIC_MANIFEST:
        args.public_manifest = DEFAULT_FULL_PUBLIC_MANIFEST
    return args


def total_response_count(response_manifest: Path | None, dag: Path, results: Path) -> int:
    from scripts.precompute_indextts_responses import load_audio_responses, load_audio_responses_from_manifest

    if response_manifest is not None:
        return len(load_audio_responses_from_manifest(response_manifest))
    return len(load_audio_responses(dag, results))


def source_response_count(response_manifest: Path | None, fallback_total: int) -> int:
    """Return the source queue size before text-level audio deduplication."""
    if response_manifest is None or not response_manifest.exists():
        return fallback_total
    payload = load_json_file(response_manifest)
    if isinstance(payload, list):
        return len(payload)
    if isinstance(payload, dict):
        declared = payload.get("responseCount")
        if isinstance(declared, int) and not isinstance(declared, bool) and declared >= 0:
            return declared
        responses = payload.get("responses")
        if isinstance(responses, list):
            return len(responses)
    return fallback_total


def file_run_identity(path: Path) -> dict[str, str]:
    resolved = path.resolve()
    if not path.exists():
        return {"path": str(resolved), "sha256": ""}
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return {"path": str(resolved), "sha256": digest.hexdigest()}


def build_run_identity(
    args: argparse.Namespace,
    *,
    total: int,
    source_total: int,
) -> dict[str, Any]:
    if args.response_manifest is not None:
        source = {
            "kind": "response-manifest",
            "responseManifest": file_run_identity(args.response_manifest),
        }
    else:
        source = {
            "kind": "dag-results",
            "dag": file_run_identity(args.dag),
            "results": file_run_identity(args.results),
        }
    return {
        "schemaVersion": 1,
        "source": source,
        "sourceResponseCount": source_total,
        "totalResponses": total,
        "spaceUrl": str(args.space_url or "").strip().rstrip("/"),
        "modelName": str(getattr(args, "model_name", DEFAULT_INDEXTTS_MODEL_NAME) or "").strip(),
        "batchSize": int(args.batch_size),
        "remoteBatchSize": int(args.remote_batch_size),
        "requireBatch": bool(getattr(args, "require_batch", True)),
    }


def load_resume_checkpoint(
    args: argparse.Namespace,
    *,
    total: int,
    run_identity: dict[str, Any],
) -> tuple[int, int, int]:
    requested_offset = max(0, int(args.start_offset))
    if bool(getattr(args, "reset_state", False)) or not bool(getattr(args, "resume", True)):
        return requested_offset, 0, 0
    if not args.state.exists():
        return requested_offset, 0, 0

    state = load_json_file(args.state)
    if not isinstance(state, dict):
        raise RuntimeError(f"Cannot resume: checkpoint {args.state} is not a JSON object")
    state_total = state.get("totalResponses")
    if isinstance(state_total, bool) or not isinstance(state_total, int) or state_total != total:
        raise RuntimeError(
            f"Cannot resume: checkpoint totalResponses={state_total!r} does not match current total {total}. "
            "Use --reset-state or --no-resume to start a new run."
        )
    next_offset = state.get("nextOffset")
    if (
        isinstance(next_offset, bool)
        or not isinstance(next_offset, int)
        or next_offset < 0
        or next_offset > total
    ):
        raise RuntimeError(
            f"Cannot resume: checkpoint nextOffset={next_offset!r} is outside 0..{total}. "
            "Use --reset-state or --no-resume to start a new run."
        )
    prior_identity = state.get("runIdentity")
    if prior_identity is not None and prior_identity != run_identity:
        raise RuntimeError(
            "Cannot resume: checkpoint run identity does not match the selected source or endpoint. "
            "Use --reset-state or --no-resume to start a new run."
        )
    batches_completed = state.get("batchesCompleted", 0)
    failures = state.get("failures", 0)
    if isinstance(batches_completed, bool) or not isinstance(batches_completed, int) or batches_completed < 0:
        batches_completed = 0
    if isinstance(failures, bool) or not isinstance(failures, int) or failures < 0:
        failures = 0
    return max(requested_offset, next_offset), batches_completed, failures


def write_state(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def load_json_file(path: Path, *, retry_attempts: int = 5, retry_delay_seconds: float = 0.2) -> Any:
    last_error: Exception | None = None
    for attempt in range(max(1, retry_attempts)):
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, JSONDecodeError) as error:
            last_error = error
            if attempt + 1 >= max(1, retry_attempts):
                raise
            time.sleep(retry_delay_seconds)
    if last_error is not None:
        raise last_error
    raise RuntimeError(f"Failed to load JSON from {path}")


def read_manifest_rate_limit(path: Path) -> dict[str, str] | None:
    if not path.exists():
        return None
    payload = load_json_file(path)
    rate_limit = (((payload.get("batchInference") or {}).get("rateLimitDetected")) or {})
    if not rate_limit:
        return None
    return {
        "type": str(rate_limit.get("type") or ""),
        "message": str(rate_limit.get("message") or ""),
        "retryAfter": str(rate_limit.get("retryAfter") or ""),
    }


_TRANSIENT_FAILURE_MARKERS = (
    "zerogpu worker error",
    "queue full",
    "temporarily unavailable",
    "service unavailable",
    "bad gateway",
    "gateway timeout",
    "space queue failed",
    "queue failed",
    "timed out",
    "connection reset",
    "remote disconnected",
)


def is_retryable_failure_message(message: str) -> bool:
    normalized = str(message or "").strip().casefold()
    return any(marker in normalized for marker in _TRANSIENT_FAILURE_MARKERS)


def read_manifest_failures(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"failedCount": 0, "retryableCount": 0, "allRetryable": False, "messages": []}
    payload = load_json_file(path)
    responses = payload.get("responses") or []
    failures = [
        entry
        for entry in responses
        if isinstance(entry, dict) and str(entry.get("status") or "").strip().lower() == "failed"
    ]
    messages = [str(entry.get("error") or "Unknown error").strip() or "Unknown error" for entry in failures]
    retryable_count = sum(
        1
        for entry, message in zip(failures, messages)
        if bool(entry.get("retriable")) or is_retryable_failure_message(message)
    )
    return {
        "failedCount": len(failures),
        "retryableCount": retryable_count,
        "allRetryable": bool(failures) and retryable_count == len(failures),
        "messages": messages,
    }


def retry_backoff_seconds(attempt_index: int, *, base_seconds: float, multiplier: float, max_seconds: float) -> float:
    base = max(0.0, float(base_seconds))
    capped_max = max(base, float(max_seconds))
    factor = max(1.0, float(multiplier))
    return min(capped_max, base * (factor ** max(0, int(attempt_index))))


def runtime_deadline(started_at: float, max_runtime_seconds: float | None) -> float | None:
    if max_runtime_seconds is None:
        return None
    limit = float(max_runtime_seconds)
    if limit <= 0.0:
        return None
    return started_at + limit


def write_loop_state(
    *,
    path: Path,
    started_at: float,
    total: int,
    offset: int,
    batch_size: int,
    batches_completed: int,
    failures: int,
    manifest: Path | None,
    progress: Path | None,
    source_total: int | None = None,
    run_identity: dict[str, Any] | None = None,
    stop_reason: str = "",
    retry_after: str = "",
) -> None:
    payload = {
        "schemaVersion": 2,
        "updatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "elapsedSeconds": round(time.time() - started_at, 3),
        "totalResponses": total,
        "sourceResponseCount": total if source_total is None else source_total,
        "nextOffset": offset,
        "batchSize": batch_size,
        "batchesCompleted": batches_completed,
        "failures": failures,
        "lastManifest": str(manifest) if manifest is not None else "",
        "lastProgress": str(progress) if progress is not None else "",
        **({"runIdentity": run_identity} if run_identity is not None else {}),
        **({"stopReason": stop_reason} if stop_reason else {}),
        **({"retryAfter": retry_after} if retry_after else {}),
    }
    write_state(path, payload)


def build_precompute_command(
    args: argparse.Namespace,
    *,
    manifest: Path,
    progress: Path,
    offset: int,
    remaining_seconds: int | None,
) -> list[str]:
    cmd = [
        "python3",
        str(REPO_ROOT / "scripts/precompute_indextts_responses.py"),
        "--offset",
        str(offset),
        "--limit",
        str(args.batch_size),
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
        "--model-name",
        str(getattr(args, "model_name", DEFAULT_INDEXTTS_MODEL_NAME)),
    ]
    if remaining_seconds is not None:
        cmd.extend(["--max-runtime-seconds", str(remaining_seconds)])
    if args.space_url:
        cmd.extend(["--space-url", args.space_url])
    if args.bucket_uri:
        cmd.extend(["--bucket-uri", args.bucket_uri])
    if args.require_upload_capable_batch:
        cmd.append("--require-upload-capable-batch")
    if bool(getattr(args, "require_batch", True)):
        cmd.append("--require-batch")
    else:
        cmd.append("--allow-single-fallback")
    if getattr(args, "prune_local_audio_after_sync", False):
        cmd.append("--prune-local-audio-after-sync")
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
    return cmd


def main() -> int:
    args = parse_args()
    if args.batch_size < 1:
        raise ValueError("--batch-size must be at least 1")
    if args.remote_batch_size < 1:
        raise ValueError("--remote-batch-size must be at least 1")
    if args.parallel_workers < 1:
        raise ValueError("--parallel-workers must be at least 1")
    args.batch_manifest_dir.mkdir(parents=True, exist_ok=True)
    args.progress_dir.mkdir(parents=True, exist_ok=True)
    started_at = time.time()
    deadline = runtime_deadline(started_at, args.max_runtime_seconds)
    total = total_response_count(args.response_manifest, args.dag, args.results)
    source_total = source_response_count(args.response_manifest, total)
    run_identity = build_run_identity(args, total=total, source_total=source_total)
    offset, batches_completed, failures = load_resume_checkpoint(
        args,
        total=total,
        run_identity=run_identity,
    )
    if offset:
        print(f"Resuming batch loop at offset {offset}/{total} from {args.state}")
    stop_reason = ""
    retry_after = ""
    exit_code = EXIT_SUCCESS
    last_manifest: Path | None = None
    last_progress: Path | None = None

    while offset < total and (deadline is None or time.time() < deadline):
        batch_index = offset // max(1, args.batch_size)
        manifest = args.batch_manifest_dir / f"batch-{batch_index:05d}-offset-{offset:06d}.json"
        progress = args.progress_dir / f"batch-{batch_index:05d}-offset-{offset:06d}.progress.json"
        last_manifest = manifest
        last_progress = progress
        batch_succeeded = False
        retry_attempt = 0
        last_returncode: int | None = None

        while deadline is None or time.time() < deadline:
            remaining_seconds = None if deadline is None else max(1, int(deadline - time.time()))
            cmd = build_precompute_command(
                args,
                manifest=manifest,
                progress=progress,
                offset=offset,
                remaining_seconds=remaining_seconds,
            )
            remaining_label = "unbounded" if remaining_seconds is None else f"{remaining_seconds}s"
            print(
                f"[batch {batch_index}] offset={offset} size={args.batch_size} remaining={remaining_label} attempt={retry_attempt + 1}"
            )
            completed = subprocess.run(cmd, cwd=REPO_ROOT)
            last_returncode = completed.returncode
            rate_limit = read_manifest_rate_limit(manifest)
            manifest_failures = read_manifest_failures(manifest)
            if completed.returncode == 0 and manifest_failures["failedCount"] == 0:
                batch_succeeded = True
                stop_reason = ""
                retry_after = ""
                break

            failures += 1
            if completed.returncode == 75 or rate_limit:
                stop_reason = (rate_limit or {}).get("message") or "IndexTTS quota exhausted"
                retry_after = (rate_limit or {}).get("retryAfter") or ""
                break

            if manifest_failures["failedCount"]:
                first_message = manifest_failures["messages"][0] if manifest_failures["messages"] else "Unknown error"
                stop_reason = f"{manifest_failures['failedCount']} response(s) failed in batch {batch_index}: {first_message}"
                if manifest_failures["allRetryable"] and retry_attempt < max(0, args.batch_retry_attempts):
                    backoff_seconds = retry_backoff_seconds(
                        retry_attempt,
                        base_seconds=args.batch_retry_backoff_seconds,
                        multiplier=args.batch_retry_backoff_multiplier,
                        max_seconds=args.batch_retry_max_backoff_seconds,
                    )
                    if deadline is not None and time.time() + backoff_seconds >= deadline:
                        break
                    print(
                        f"[batch {batch_index}] transient failure; retrying in {backoff_seconds:.1f}s: {first_message}"
                    )
                    time.sleep(backoff_seconds)
                    retry_attempt += 1
                    continue
                break

            stop_reason = f"Batch command failed with exit code {completed.returncode}"
            break

        if not batch_succeeded:
            exit_code = (
                EXIT_RATE_LIMITED
                if retry_after or last_returncode == EXIT_RATE_LIMITED
                else EXIT_BATCH_FAILED
            )
            write_loop_state(
                path=args.state,
                started_at=started_at,
                total=total,
                offset=offset,
                batch_size=args.batch_size,
                batches_completed=batches_completed,
                failures=failures,
                manifest=manifest,
                progress=progress,
                source_total=source_total,
                run_identity=run_identity,
                stop_reason=stop_reason or "Batch failed",
                retry_after=retry_after,
            )
            break

        batches_completed += 1
        offset = min(total, offset + args.batch_size)
        write_loop_state(
            path=args.state,
            started_at=started_at,
            total=total,
            offset=offset,
            batch_size=args.batch_size,
            batches_completed=batches_completed,
            failures=failures,
            manifest=manifest,
            progress=progress,
            source_total=source_total,
            run_identity=run_identity,
            stop_reason=stop_reason,
            retry_after=retry_after,
        )

    if exit_code == EXIT_SUCCESS and offset < total:
        stop_reason = stop_reason or f"Reached runtime deadline after {max(0.0, float(args.max_runtime_seconds)):.1f}s"
        write_loop_state(
            path=args.state,
            started_at=started_at,
            total=total,
            offset=offset,
            batch_size=args.batch_size,
            batches_completed=batches_completed,
            failures=failures,
            manifest=last_manifest,
            progress=last_progress,
            source_total=source_total,
            run_identity=run_identity,
            stop_reason=stop_reason,
            retry_after=retry_after,
        )
        exit_code = EXIT_RUNTIME_LIMIT

    summary = f"Finished batch loop at offset {offset}/{total}; batches={batches_completed}; failures={failures}"
    if stop_reason:
        summary = f"{summary}; stopReason={stop_reason}"
        if retry_after:
            summary = f"{summary}; retryAfter={retry_after}"
    print(summary)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
