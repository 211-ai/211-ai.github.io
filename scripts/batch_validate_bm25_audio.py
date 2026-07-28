#!/usr/bin/env python3
"""Fetch BM25/vocabulary Abby bucket audio and validate with local Whisper.

The Publicus/abby-voice phase1-bm25 tree was generated from the BM25/vocabulary
manifests.  After deterministic textHash remapping, preferred clips total only
~150 MB.  This script:

1. Loads a rescued/normalized bundle.
2. Selects one preferred path per vocabulary/BM25 legacy text hash.
3. Fetches those objects into a local cache (Xet-bound).
4. Runs a warm local HuggingFace Whisper session (CUDA when available).
5. Scores transcripts against expected source_text (exact normalized or WER).
6. Writes a validation report and optional updated normalized bundle with
   ASR confirmation metadata for failures / residual unmapped rows.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from collections import defaultdict
from hashlib import sha256
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPO_ROOT / "ipfs_datasets_py"
ACCEL_ROOT = REPO_ROOT / "ipfs_accelerate_py"
for path in (PACKAGE_ROOT, ACCEL_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from ipfs_datasets_py.huggingface.bucket import (  # noqa: E402
    HuggingFaceBucketHttpClient,
    HuggingFaceBucketListingObject,
    HuggingFaceBucketStore,
)
from ipfs_datasets_py.voice.bucket_audio_normalize import (  # noqa: E402
    AbbyVoiceBucketAudioNormalizedBundle,
    BucketAudioMappingStatus,
)
from ipfs_datasets_py.voice.bucket_audio_rescue import (  # noqa: E402
    AsrRescueCandidate,
    preferred_unmapped_for_asr,
    rescue_unmapped_by_asr,
)
from ipfs_accelerate_py.voice_jobs.local_whisper_batch import (  # noqa: E402
    LocalWhisperBatchSession,
)


def _json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        + "\n"
    ).encode("utf-8")


def _atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    os.close(fd)
    tmp_path = Path(tmp)
    try:
        tmp_path.write_bytes(content)
        tmp_path.replace(path)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink()
        raise


def _load_bundle(path: Path) -> AbbyVoiceBucketAudioNormalizedBundle:
    raw = path.expanduser().resolve()
    if raw.is_dir():
        raw = raw / "bucket-audio-normalized.json"
    payload = json.loads(raw.read_text(encoding="utf-8"))
    return AbbyVoiceBucketAudioNormalizedBundle.from_dict(payload)


def _rank(entry: Any) -> tuple[int, int, str]:
    phase = 0 if (entry.phase or "").startswith("phase4") else 1
    media = 0 if (entry.media_extension or "") == "mp3" else 1
    return phase, media, entry.path


def preferred_vocabulary_entries(
    bundle: AbbyVoiceBucketAudioNormalizedBundle,
    *,
    limit: int | None = None,
) -> list[Any]:
    """One preferred path per vocabulary/BM25 legacy text hash."""

    groups: dict[str, list[Any]] = defaultdict(list)
    for entry in bundle.entries:
        if entry.mapping_status not in {
            BucketAudioMappingStatus.MAPPED_TO_VOCABULARY,
            BucketAudioMappingStatus.ASR_RESCUED_VOCABULARY,
        }:
            continue
        if not entry.legacy_text_hash or not entry.source_text:
            continue
        groups[entry.legacy_text_hash].append(entry)
    preferred = [sorted(items, key=_rank)[0] for items in groups.values()]
    preferred.sort(key=lambda item: item.path)
    if limit is not None:
        preferred = preferred[:limit]
    return preferred


def fetch_entry(
    store: HuggingFaceBucketStore,
    entry: Any,
    cache_root: Path,
) -> Path:
    dest = cache_root / "bm25" / f"{entry.legacy_text_hash}.{(entry.media_extension or 'mp3')}"
    if dest.is_file() and not dest.is_symlink() and dest.stat().st_size == entry.size_bytes:
        return dest
    if dest.exists() or dest.is_symlink():
        dest.unlink()
    dest.parent.mkdir(parents=True, exist_ok=True)
    listing = HuggingFaceBucketListingObject(
        path=entry.path,
        size_bytes=entry.size_bytes,
        xet_hash=entry.xet_hash,
        media_type=(
            "audio/mpeg" if (entry.media_extension or "mp3") == "mp3" else "audio/wav"
        ),
    )
    store.fetch_discovered(listing, dest)
    return dest


def _append_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(
                json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                + "\n"
            )
            handle.flush()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--normalized-dir", type=Path, required=True)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "data" / "abby_voice" / "bm25-batch-validate",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=REPO_ROOT / "tmp_assets" / "abby-voice-audio-recovery" / "objects",
    )
    parser.add_argument("--limit", type=int, default=0, help="0 = all preferred BM25 clips")
    parser.add_argument(
        "--resume",
        action="store_true",
        help=(
            "Resume a prior interrupted batch from its JSONL checkpoints. "
            "Only rows whose bucket_path remains in the current normalized "
            "bundle are reused."
        ),
    )
    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help="With --resume, discard only prior failed rows and retry them.",
    )
    parser.add_argument("--asr-open-limit", type=int, default=20, help="Also ASR residual unmapped")
    parser.add_argument("--model", default=os.getenv("IPFS_ACCELERATE_PY_STT_MODEL", "openai/whisper-base"))
    parser.add_argument("--device", default=None)
    parser.add_argument("--max-wer-bp", type=int, default=2500)
    parser.add_argument("--endpoint", default="https://huggingface.co")
    parser.add_argument("--token-env", default="HF_TOKEN")
    parser.add_argument("--timeout-seconds", type=float, default=120.0)
    parser.add_argument("--bucket-id", default="Publicus/abby-voice")
    args = parser.parse_args(argv)

    bundle = _load_bundle(args.normalized_dir)
    limit = None if not args.limit else args.limit
    preferred = preferred_vocabulary_entries(bundle, limit=limit)
    print(
        json.dumps(
            {
                "preferred_count": len(preferred),
                "preferred_bytes": sum(item.size_bytes for item in preferred),
                "model": args.model,
                "device": args.device or "auto",
            },
            indent=2,
        ),
        flush=True,
    )

    token = os.environ.get(args.token_env) if args.token_env else None
    client = HuggingFaceBucketHttpClient(
        endpoint=args.endpoint,
        token=token,
        timeout_seconds=args.timeout_seconds,
    )
    store = HuggingFaceBucketStore(args.bucket_id, client=client)
    cache_root = args.cache_dir.expanduser().resolve()
    cache_root.mkdir(parents=True, exist_ok=True)

    out_root = args.output_dir.expanduser().resolve()
    out_root.mkdir(parents=True, exist_ok=True)
    results_path = out_root / "bm25-batch-validation-results.jsonl"
    preferred_by_path = {entry.path: entry for entry in preferred}
    completed_paths: set[str] = set()
    results: list[dict[str, Any]] = []
    matched = 0
    mismatched = 0
    failed = 0
    retried_failure_count = 0
    if args.resume and results_path.is_file():
        for line_number, line in enumerate(
            results_path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except ValueError as exc:
                raise ValueError(
                    f"invalid resume checkpoint row {line_number}: {exc}"
                ) from exc
            bucket_path = row.get("bucket_path")
            if not isinstance(bucket_path, str) or bucket_path not in preferred_by_path:
                raise ValueError(
                    "resume checkpoint row does not bind a current preferred "
                    f"bucket path at line {line_number}"
                )
            if bucket_path in completed_paths:
                raise ValueError(
                    f"duplicate resume checkpoint for {bucket_path!r}"
                )
            if args.retry_failed and not row.get("ok"):
                retried_failure_count += 1
                continue
            completed_paths.add(bucket_path)
            results.append(row)
            if not row.get("ok"):
                failed += 1
            elif row.get("matched"):
                matched += 1
            else:
                mismatched += 1
        if retried_failure_count:
            _atomic_write(
                results_path,
                b"".join(
                    json.dumps(
                        row,
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ).encode("utf-8")
                    + b"\n"
                    for row in results
                ),
            )
    elif results_path.exists():
        # Fresh results file for a new run (cache still resumes fetches).
        results_path.unlink()

    remaining_preferred = [
        entry for entry in preferred if entry.path not in completed_paths
    ]
    if args.resume:
        print(
            json.dumps(
                {
                    "resume_checkpoint_count": len(completed_paths),
                    "retried_failure_count": retried_failure_count,
                    "remaining_count": len(remaining_preferred),
                },
                indent=2,
            ),
            flush=True,
        )

    local_paths: list[str] = []
    expected: dict[str, str] = {}
    fetch_errors: list[dict[str, str]] = []
    path_to_entry: dict[str, Any] = {}
    cached_hits = 0
    for index, entry in enumerate(remaining_preferred, start=1):
        try:
            dest = (
                cache_root
                / "bm25"
                / f"{entry.legacy_text_hash}.{(entry.media_extension or 'mp3')}"
            )
            if (
                dest.is_file()
                and not dest.is_symlink()
                and dest.stat().st_size == entry.size_bytes
            ):
                cached_hits += 1
            else:
                dest = fetch_entry(store, entry, cache_root)
            local_paths.append(str(dest))
            expected[str(dest)] = entry.source_text or ""
            path_to_entry[str(dest)] = entry
            if index % 100 == 0 or index == len(remaining_preferred):
                print(
                    f"fetched {index}/{len(remaining_preferred)} cached_hits={cached_hits} errors={len(fetch_errors)}",
                    flush=True,
                )
        except Exception as exc:
            fetch_errors.append({"path": entry.path, "error": str(exc)[:300]})
            if index % 100 == 0 or index == len(remaining_preferred):
                print(
                    f"fetched {index}/{len(remaining_preferred)} cached_hits={cached_hits} errors={len(fetch_errors)}",
                    flush=True,
                )

    print(
        json.dumps(
            {
                "fetch_complete": True,
                "local_paths": len(local_paths),
                "resumed_rows": len(completed_paths),
                "cached_hits": cached_hits,
                "fetch_errors": len(fetch_errors),
            },
            indent=2,
        ),
        flush=True,
    )

    session = LocalWhisperBatchSession(
        model_name=args.model,
        device=args.device,
        language="en",
        provider_name="huggingface",
    )
    pending_rows: list[dict[str, Any]] = []
    for index, item in enumerate(
        session.transcribe_paths(
            local_paths,
            expected_by_path=expected,
            max_wer_bp=args.max_wer_bp,
        ),
        start=len(completed_paths) + 1,
    ):
        row = {
            "path": item.path,
            "bucket_path": getattr(path_to_entry.get(item.path), "path", None),
            "legacy_text_hash": getattr(
                path_to_entry.get(item.path), "legacy_text_hash", None
            ),
            "expected_text": item.expected_text,
            "transcript": item.transcript,
            "ok": item.ok,
            "matched": item.matched,
            "wer_bp": item.wer_bp,
            "error": item.error,
        }
        results.append(row)
        pending_rows.append(row)
        if not item.ok:
            failed += 1
        elif item.matched:
            matched += 1
        else:
            mismatched += 1
        if index % 50 == 0 or index == len(preferred):
            _append_jsonl(results_path, pending_rows)
            pending_rows.clear()
            print(
                f"transcribed {index}/{len(preferred)} matched={matched} mismatched={mismatched} failed={failed}",
                flush=True,
            )
    if pending_rows:
        _append_jsonl(results_path, pending_rows)

    # Residual unmapped / asr_unmatched rescue via same warm session.
    open_entries = [
        item
        for item in bundle.entries
        if item.mapping_status
        in {
            BucketAudioMappingStatus.UNMAPPED_LINKABLE,
            BucketAudioMappingStatus.ASR_UNMATCHED,
        }
    ]
    residual_stats = {"attempted": 0, "matched": 0, "unmatched": 0, "errors": 0}
    asr_candidates: list[AsrRescueCandidate] = []
    residual_targets = preferred_unmapped_for_asr(
        bundle, limit=args.asr_open_limit if args.asr_open_limit > 0 else None
    )
    # preferred_unmapped only sees UNMAPPED_LINKABLE; include asr_unmatched manually
    residual_by_hash: dict[str, Any] = {}
    for entry in open_entries:
        if not entry.legacy_text_hash:
            continue
        residual_by_hash.setdefault(entry.legacy_text_hash, []).append(entry)
    residual_preferred = [
        sorted(group, key=_rank)[0] for group in residual_by_hash.values()
    ]
    residual_preferred.sort(key=lambda item: item.path)
    if args.asr_open_limit > 0:
        residual_preferred = residual_preferred[: args.asr_open_limit]

    for entry in residual_preferred:
        residual_stats["attempted"] += 1
        try:
            dest = fetch_entry(store, entry, cache_root)
            transcript = session.transcribe_path(dest)
            if not transcript.strip():
                residual_stats["errors"] += 1
                continue
            asr_candidates.append(
                AsrRescueCandidate(path=entry.path, transcript=transcript)
            )
        except Exception:
            residual_stats["errors"] += 1

    response_texts: dict[str, tuple[str, str]] = {}
    vocabulary_texts: dict[str, tuple[str, str]] = {}
    for entry in bundle.entries:
        if entry.source_text and entry.subject_id:
            if entry.subject_kind.value == "response" or entry.response_id:
                rid = entry.response_id or entry.subject_id
                response_texts[rid] = (entry.source_text, entry.source_text)
            else:
                vocabulary_texts[entry.subject_id] = (
                    entry.source_text,
                    entry.source_text,
                )
    # Also index BM25 expected texts from preferred list.
    for entry in preferred:
        if entry.subject_id and entry.source_text:
            vocabulary_texts[entry.subject_id] = (entry.source_text, entry.source_text)

    updated_bundle = bundle
    if asr_candidates:
        updated_bundle, apply_stats = rescue_unmapped_by_asr(
            bundle,
            asr_candidates,
            response_texts=response_texts,
            vocabulary_texts=vocabulary_texts,
            max_wer_bp=args.max_wer_bp,
        )
        residual_stats["matched"] = apply_stats.get("matched", 0)
        residual_stats["unmatched"] = apply_stats.get("unmatched", 0)
        residual_stats["propagated"] = apply_stats.get("propagated", 0)

    report = {
        "preferred_count": len(preferred),
        "fetched": len(completed_paths) + len(local_paths),
        "resumed_rows": len(completed_paths),
        "retried_failure_count": retried_failure_count,
        "cached_hits": cached_hits,
        "fetch_errors": fetch_errors[:50],
        "fetch_error_count": len(fetch_errors),
        "batch_asr": {
            "matched": matched,
            "mismatched": mismatched,
            "failed": failed,
            "max_wer_bp": args.max_wer_bp,
            "model": args.model,
            "device": args.device or "auto",
        },
        "residual_asr": residual_stats,
        "final_mapping_status_counts": updated_bundle.summary().get(
            "mapping_status_counts"
        ),
        "final_unmapped_linkable_count": updated_bundle.summary().get(
            "unmapped_linkable_count"
        ),
    }
    report_path = out_root / "bm25-batch-validation-report.json"
    _atomic_write(report_path, _json_bytes(report))
    # Write updated normalized bundle JSON next to the report.
    bundle_dir = out_root / "normalized-bundle"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    bundle_json = bundle_dir / "bucket-audio-normalized.json"
    bundle_jsonl = bundle_dir / "bucket-audio-normalized.jsonl"
    _atomic_write(bundle_json, updated_bundle.canonical_bytes() + b"\n")
    _atomic_write(bundle_jsonl, updated_bundle.to_jsonl_bytes())
    _atomic_write(
        bundle_dir / "normalized-summary.json",
        _json_bytes(
            {
                **updated_bundle.summary(),
                "stage": "bm25_batch_validated",
            }
        ),
    )
    summary = {
        **report,
        "report_path": str(report_path),
        "results_path": str(results_path),
        "normalized_bundle_dir": str(bundle_dir),
        "normalized_id": updated_bundle.normalized_id,
    }
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2), flush=True)
    # Non-zero only when batch validation itself fails hard.
    return 0 if failed < max(1, len(local_paths) // 2) else 3


if __name__ == "__main__":
    raise SystemExit(main())
