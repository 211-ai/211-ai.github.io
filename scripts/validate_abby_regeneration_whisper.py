#!/usr/bin/env python3
"""Resumably Whisper-validate the complete Abby regeneration audio manifest.

The per-item JSONL ledger is authoritative and is fsynced before the atomic
checkpoint is advanced.  A process interrupted after the ledger append but
before the checkpoint update therefore resumes without retranscribing the
validated item.  A final compact receipt binds the manifest, run
configuration, and completed ledger by SHA-256.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import sys
import time
from collections.abc import Callable, Iterable, Sequence
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.review_abby_regeneration_audio import (  # noqa: E402
    _resolve_audio_path,
    content_word_coverage_bp,
    normalized_review_text,
    normalized_similarity_bp,
    numeric_sequences_match,
)

for package_root in (
    REPO_ROOT / "ipfs_accelerate_py",
    REPO_ROOT / "ipfs_datasets_py",
):
    if str(package_root) not in sys.path:
        sys.path.insert(0, str(package_root))

from ipfs_datasets_py.voice.audio_quality import word_error_rate_bp  # noqa: E402

DEFAULT_MANIFEST = (
    REPO_ROOT
    / "tmp_assets"
    / "hf-abby-tts-canonical-dataset"
    / "metadata"
    / "regeneration-audio-manifest.json"
)
DEFAULT_OUTPUT_PREFIX = (
    DEFAULT_MANIFEST.parent / "regeneration-full-whisper-validation-v3"
)
VALIDATOR_VERSION = "abby_voice_full_whisper_validator_v3"
ITEM_SCHEMA = "abby_voice_full_whisper_validation_item_v3"
CHECKPOINT_SCHEMA = "abby_voice_full_whisper_validation_checkpoint_v3"
RECEIPT_SCHEMA = "abby_voice_full_whisper_validation_receipt_v3"
FAILURE_MANIFEST_SCHEMA = "abby_voice_full_whisper_failures_v2"
SEMANTIC_CORRUPTION_SCHEMA = "abby_voice_semantic_corruptions_v2"
_APOSTROPHE_DIRECTION_EXPANSION = re.compile(
    r"\b(?:Lane County|Salem)[’'](?:North|South|East|West)\b"
)
_CONFIRMED_ST_ABBREVIATION_EXPANSION = re.compile(
    r"\bStreet\.\s+(?:Vincent|Mary[’']s|Charles)\b"
)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(REPO_ROOT))
    except ValueError:
        return str(resolved)


def _sha256_path(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _fsync_parent(path: Path) -> None:
    descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    """Durably replace *path* with canonical, human-readable JSON."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    encoded = (
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    try:
        with temporary.open("wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        _fsync_parent(path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def append_receipt_events(path: Path, events: Sequence[dict[str, Any]]) -> None:
    """Append complete JSONL events and fsync them as one bounded transaction."""

    if not events:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("ab") as handle:
        for event in events:
            handle.write(
                (
                    json.dumps(
                        event,
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                    + "\n"
                ).encode("utf-8")
            )
        handle.flush()
        os.fsync(handle.fileno())
    _fsync_parent(path)


def validation_artifact_paths(
    output_prefix: Path,
    *,
    shard_count: int,
    shard_index: int,
) -> dict[str, Path]:
    if shard_count < 1:
        raise ValueError("shard_count must be positive")
    if shard_index < 0 or shard_index >= shard_count:
        raise ValueError("shard_index must be in [0, shard_count)")
    suffix = (
        ""
        if shard_count == 1
        else f"-shard-{shard_index:03d}-of-{shard_count:03d}"
    )
    stem = output_prefix.with_name(output_prefix.name + suffix)
    return {
        "checkpoint": stem.with_suffix(".checkpoint.json"),
        "ledger": stem.with_suffix(".receipts.jsonl"),
        "lock": stem.with_suffix(".lock"),
        "failures": stem.with_suffix(".failures.json"),
        "receipt": stem.with_suffix(".receipt.json"),
        "semantic_corruptions": stem.with_suffix(
            ".semantic-corruptions.json"
        ),
    }


def _trim_partial_jsonl_tail(path: Path) -> bool:
    """Discard only a final non-newline-terminated record after a hard stop."""

    if not path.is_file() or path.stat().st_size == 0:
        return False
    with path.open("r+b") as handle:
        handle.seek(-1, os.SEEK_END)
        if handle.read(1) == b"\n":
            return False
        handle.seek(0)
        data = handle.read()
        boundary = data.rfind(b"\n")
        handle.truncate(boundary + 1 if boundary >= 0 else 0)
        handle.flush()
        os.fsync(handle.fileno())
    _fsync_parent(path)
    return True


def load_receipt_events(
    path: Path,
    *,
    run_fingerprint: str,
    selected_ids: set[str],
) -> tuple[list[dict[str, Any]], bool]:
    """Load and validate a ledger, repairing only an interrupted final record."""

    repaired_tail = _trim_partial_jsonl_tail(path)
    if not path.is_file():
        return [], repaired_tail
    events: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"invalid receipt JSONL at line {line_number}: {exc}"
                ) from exc
            if not isinstance(event, dict):
                raise ValueError(
                    f"receipt JSONL line {line_number} is not an object"
                )
            if event.get("schema_version") != ITEM_SCHEMA:
                raise ValueError(
                    f"receipt JSONL line {line_number} has an unknown schema"
                )
            if event.get("run_fingerprint") != run_fingerprint:
                raise ValueError(
                    "existing receipt ledger belongs to another manifest or run "
                    "configuration"
                )
            audio_id = str(event.get("audio_id") or "")
            if audio_id not in selected_ids:
                raise ValueError(
                    f"receipt JSONL line {line_number} has unexpected audio_id "
                    f"{audio_id!r}"
                )
            if event.get("status") not in {"validated", "error"}:
                raise ValueError(
                    f"receipt JSONL line {line_number} has invalid status"
                )
            events.append(event)
    return events, repaired_tail


def _manifest_rows(
    manifest_path: Path,
    *,
    shard_count: int,
    shard_index: int,
) -> list[tuple[int, dict[str, Any]]]:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    rows = payload.get("responses") if isinstance(payload, dict) else None
    if not isinstance(rows, list) or not rows:
        raise ValueError("generation manifest has no response rows")
    selected: list[tuple[int, dict[str, Any]]] = []
    seen_ids: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"manifest response {index} is not an object")
        audio_id = str(row.get("id") or "").strip()
        expected = str(row.get("text") or "").strip()
        if not audio_id:
            raise ValueError(f"manifest response {index} has no id")
        if audio_id in seen_ids:
            raise ValueError(f"manifest contains duplicate id {audio_id!r}")
        seen_ids.add(audio_id)
        if not expected:
            raise ValueError(f"manifest response {audio_id!r} has no text")
        if index % shard_count == shard_index:
            selected.append((index, row))
    if not selected:
        raise ValueError("selected shard has no response rows")
    return selected


def _resolve_device_and_dtype(device: str, dtype: str) -> tuple[str, str]:
    selected_device = str(device or "auto").strip().casefold()
    selected_dtype = str(dtype or "auto").strip().casefold()
    if selected_device == "auto":
        try:
            import torch

            selected_device = "cuda" if torch.cuda.is_available() else "cpu"
        except Exception:
            selected_device = "cpu"
    if selected_device not in {"cpu", "cuda"}:
        raise ValueError("device must be auto, cpu, or cuda")
    if selected_dtype == "auto":
        selected_dtype = "float16" if selected_device == "cuda" else "float32"
    if selected_dtype not in {"float16", "float32", "bfloat16"}:
        raise ValueError("dtype must be auto, float16, float32, or bfloat16")
    if selected_device == "cpu" and selected_dtype == "float16":
        raise ValueError("float16 CPU Whisper inference is unsupported")
    return selected_device, selected_dtype


def _run_fingerprint(
    *,
    manifest_sha256: str,
    model_name: str,
    model_revision: str,
    device: str,
    dtype: str,
    language: str,
    minimum_similarity_bp: int,
    minimum_content_coverage_bp: int,
    maximum_wer_bp: int,
    shard_count: int,
    shard_index: int,
) -> str:
    payload = {
        "device": device,
        "dtype": dtype,
        "language": language,
        "manifest_sha256": manifest_sha256,
        "maximum_wer_bp": maximum_wer_bp,
        "minimum_content_coverage_bp": minimum_content_coverage_bp,
        "minimum_similarity_bp": minimum_similarity_bp,
        "model_name": model_name,
        "model_revision": model_revision,
        "schema_version": RECEIPT_SCHEMA,
        "shard_count": shard_count,
        "shard_index": shard_index,
        "validator_version": VALIDATOR_VERSION,
    }
    return sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _build_validation_event(
    *,
    row: dict[str, Any],
    manifest_index: int,
    audio_path: Path,
    audio_digest: str,
    transcript: str,
    model_name: str,
    model_revision: str,
    device: str,
    dtype: str,
    run_fingerprint: str,
    minimum_similarity_bp: int,
    minimum_content_coverage_bp: int,
    maximum_wer_bp: int,
    shard_count: int,
    shard_index: int,
) -> dict[str, Any]:
    expected = str(row.get("text") or "")
    expected_digest = sha256(expected.encode()).hexdigest()
    similarity = normalized_similarity_bp(expected, transcript)
    coverage = content_word_coverage_bp(expected, transcript)
    wer = word_error_rate_bp(
        normalized_review_text(expected),
        normalized_review_text(transcript),
    )
    forbidden_negative = "negative" in normalized_review_text(transcript).split()
    numbers_match = numeric_sequences_match(expected, transcript)
    passed = (
        bool(transcript.strip())
        and similarity >= minimum_similarity_bp
        and coverage >= minimum_content_coverage_bp
        and wer <= maximum_wer_bp
        and not forbidden_negative
        and numbers_match
    )
    transcript_digest = sha256(transcript.encode()).hexdigest()
    receipt_identity = sha256(
        (
            audio_digest
            + "\0"
            + expected_digest
            + "\0"
            + transcript_digest
            + "\0"
            + model_name
            + "\0"
            + run_fingerprint
        ).encode()
    ).hexdigest()
    return {
        "asr_model": model_name,
        "audio_id": str(row.get("id") or ""),
        "audio_path": _display_path(audio_path),
        "audio_sha256": audio_digest,
        "content_word_coverage_bp": coverage,
        "device": device,
        "dtype": dtype,
        "expected_text_sha256": expected_digest,
        "forbidden_negative_detected": forbidden_negative,
        "manifest_index": manifest_index,
        "model_revision": model_revision,
        "normalized_similarity_bp": similarity,
        "numeric_sequences_match": numbers_match,
        "passed": passed,
        "run_fingerprint": run_fingerprint,
        "schema_version": ITEM_SCHEMA,
        "shard_count": shard_count,
        "shard_index": shard_index,
        "status": "validated",
        "transcript": transcript,
        "transcript_sha256": transcript_digest,
        "validated_at": _utc_now(),
        "validation_receipt_id": (
            "abby-voice-full-asr-validation:sha256:" + receipt_identity
        ),
        "validator_version": VALIDATOR_VERSION,
        "wer_bp": wer,
    }


def _build_error_event(
    *,
    row: dict[str, Any],
    manifest_index: int,
    audio_path: Path,
    audio_digest: str,
    error: Exception,
    model_name: str,
    model_revision: str,
    device: str,
    dtype: str,
    run_fingerprint: str,
    shard_count: int,
    shard_index: int,
) -> dict[str, Any]:
    expected = str(row.get("text") or "")
    return {
        "asr_model": model_name,
        "audio_id": str(row.get("id") or ""),
        "audio_path": _display_path(audio_path),
        "audio_sha256": audio_digest,
        "device": device,
        "dtype": dtype,
        "error": f"{type(error).__name__}: {error}"[:1000],
        "expected_text_sha256": sha256(expected.encode()).hexdigest(),
        "manifest_index": manifest_index,
        "model_revision": model_revision,
        "passed": False,
        "run_fingerprint": run_fingerprint,
        "schema_version": ITEM_SCHEMA,
        "shard_count": shard_count,
        "shard_index": shard_index,
        "status": "error",
        "validated_at": _utc_now(),
        "validator_version": VALIDATOR_VERSION,
    }


class TransformersWhisperTranscriber:
    """Lazily loaded, bounded-batch Transformers Whisper pipeline."""

    def __init__(
        self,
        *,
        model_name: str,
        model_revision: str,
        device: str,
        dtype: str,
        language: str,
        batch_size: int,
    ) -> None:
        self.model_name = model_name
        self.model_revision = model_revision
        self.device = device
        self.dtype = dtype
        self.language = language
        self.batch_size = batch_size
        self._pipeline: Any | None = None

    def _ensure_pipeline(self) -> Any:
        if self._pipeline is not None:
            return self._pipeline
        import torch
        from transformers import pipeline

        torch_dtype = {
            "float16": torch.float16,
            "float32": torch.float32,
            "bfloat16": torch.bfloat16,
        }[self.dtype]
        self._pipeline = pipeline(
            "automatic-speech-recognition",
            model=self.model_name,
            revision=self.model_revision,
            device=0 if self.device == "cuda" else -1,
            dtype=torch_dtype,
        )
        return self._pipeline

    def transcribe_many(self, paths: Sequence[Path]) -> list[str]:
        if not paths:
            return []
        pipe = self._ensure_pipeline()
        result = pipe(
            [str(path) for path in paths],
            batch_size=min(self.batch_size, len(paths)),
            return_timestamps=True,
            generate_kwargs={"language": self.language},
        )
        results = result if isinstance(result, list) else [result]
        if len(results) != len(paths):
            raise RuntimeError(
                f"Whisper returned {len(results)} results for {len(paths)} inputs"
            )
        transcripts: list[str] = []
        for item in results:
            if not isinstance(item, dict):
                raise RuntimeError("Whisper returned a non-object result")
            text = item.get("text")
            if not isinstance(text, str) or not text.strip():
                raise RuntimeError("Whisper returned an empty transcript")
            transcripts.append(text)
        return transcripts

    def recover_after_error(self) -> None:
        if self.device != "cuda":
            return
        try:
            import torch

            torch.cuda.empty_cache()
        except Exception:
            pass


def _transcribe_resiliently(
    transcribe_many: Callable[[Sequence[Path]], list[str]],
    paths: Sequence[Path],
    *,
    recover_after_error: Callable[[], None] | None = None,
) -> list[str | Exception]:
    """Split failed batches so one bad file does not discard its neighbors."""

    try:
        transcripts = transcribe_many(paths)
        if len(transcripts) != len(paths):
            raise RuntimeError("transcriber returned the wrong result count")
        return transcripts
    except Exception as exc:
        if recover_after_error is not None:
            recover_after_error()
        if len(paths) <= 1:
            return [exc]
        midpoint = len(paths) // 2
        return _transcribe_resiliently(
            transcribe_many,
            paths[:midpoint],
            recover_after_error=recover_after_error,
        ) + _transcribe_resiliently(
            transcribe_many,
            paths[midpoint:],
            recover_after_error=recover_after_error,
        )


def _latest_events(
    events: Iterable[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    return {str(event["audio_id"]): event for event in events}


def _summarize(
    *,
    rows: Sequence[tuple[int, dict[str, Any]]],
    latest: dict[str, dict[str, Any]],
    valid_audio: dict[str, tuple[str, str]],
) -> dict[str, int]:
    passed = 0
    failed = 0
    errors = 0
    completed = 0
    for _, row in rows:
        audio_id = str(row["id"])
        event = latest.get(audio_id)
        current = valid_audio.get(audio_id)
        if event is None:
            continue
        event_current = current == (
            str(event.get("audio_sha256") or ""),
            str(event.get("expected_text_sha256") or ""),
        )
        if event.get("status") == "validated" and event_current:
            completed += 1
            if event.get("passed") is True:
                passed += 1
            else:
                failed += 1
        elif event.get("status") == "error" and event_current:
            errors += 1
    return {
        "completed_count": completed,
        "error_count": errors,
        "failed_count": failed,
        "passed_count": passed,
        "pending_count": len(rows) - completed,
        "total_count": len(rows),
    }


def _failure_reasons(
    event: dict[str, Any],
    gates: dict[str, Any],
) -> list[str]:
    reasons: list[str] = []
    if not str(event.get("transcript") or "").strip():
        reasons.append("empty_transcript")
    if int(event.get("normalized_similarity_bp") or 0) < int(
        gates["minimum_similarity_bp"]
    ):
        reasons.append("minimum_similarity_bp")
    if int(event.get("content_word_coverage_bp") or 0) < int(
        gates["minimum_content_word_coverage_bp"]
    ):
        reasons.append("minimum_content_word_coverage_bp")
    if int(event.get("wer_bp") or 0) > int(gates["maximum_wer_bp"]):
        reasons.append("maximum_wer_bp")
    if event.get("forbidden_negative_detected") is True:
        reasons.append("forbidden_negative_detected")
    if event.get("numeric_sequences_match") is not True:
        reasons.append("numeric_sequences_match")
    return reasons


def semantic_corruption_items(
    rows: Sequence[tuple[int, dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Return redacted expected-text corruptions that acoustic ASR cannot clear."""

    items: list[dict[str, Any]] = []
    for manifest_index, row in rows:
        expected = str(row.get("text") or "")
        reasons: list[str] = []
        if _APOSTROPHE_DIRECTION_EXPANSION.search(expected):
            reasons.append("apostrophe_direction_expansion")
        if _CONFIRMED_ST_ABBREVIATION_EXPANSION.search(expected):
            reasons.append("st_abbreviation_expanded_to_street")
        if not reasons:
            continue
        items.append(
            {
                "active_eligible": False,
                "audio_id": str(row.get("id") or ""),
                "expected_text_sha256": sha256(expected.encode()).hexdigest(),
                "manifest_index": manifest_index,
                "reasons": reasons,
                "source_ids": [
                    str(value)
                    for value in row.get("sourceIds") or []
                    if str(value)
                ],
            }
        )
    return items


def _checkpoint_payload(
    *,
    manifest_path: Path,
    manifest_sha256: str,
    paths: dict[str, Path],
    run_fingerprint: str,
    model_name: str,
    model_revision: str,
    device: str,
    dtype: str,
    language: str,
    gates: dict[str, Any],
    shard_count: int,
    shard_index: int,
    event_count: int,
    repaired_partial_tail: bool,
    summary: dict[str, int],
    started_at: str,
    active_seconds: float,
    status: str,
) -> dict[str, Any]:
    completed = summary["completed_count"]
    total = summary["total_count"]
    rate = completed / active_seconds if completed and active_seconds > 0 else 0.0
    remaining_seconds = (
        (total - completed) / rate if rate > 0 and completed < total else 0.0
    )
    estimated_completion = (
        (
            datetime.now(UTC) + timedelta(seconds=remaining_seconds)
        ).isoformat().replace("+00:00", "Z")
        if remaining_seconds
        else None
    )
    return {
        "active_seconds": round(active_seconds, 3),
        "attempt_event_count": event_count,
        "completed_bp": int(round(completed * 10_000 / total)),
        "device": device,
        "dtype": dtype,
        "estimated_completion_at": estimated_completion,
        "gates": gates,
        "language": language,
        "ledger": _display_path(paths["ledger"]),
        "manifest": _display_path(manifest_path),
        "manifest_sha256": manifest_sha256,
        "model_name": model_name,
        "model_revision": model_revision,
        "partial_tail_repaired": repaired_partial_tail,
        "receipt": _display_path(paths["receipt"]),
        "run_fingerprint": run_fingerprint,
        "schema_version": CHECKPOINT_SCHEMA,
        "shard_count": shard_count,
        "shard_index": shard_index,
        "started_at": started_at,
        "status": status,
        "throughput_items_per_second": round(rate, 6),
        "updated_at": _utc_now(),
        "validator_version": VALIDATOR_VERSION,
        **summary,
    }


def run_validation(
    manifest_path: Path,
    output_prefix: Path,
    *,
    model_name: str,
    model_revision: str,
    device: str,
    dtype: str,
    language: str,
    batch_size: int,
    minimum_similarity_bp: int,
    minimum_content_coverage_bp: int,
    maximum_wer_bp: int,
    shard_count: int = 1,
    shard_index: int = 0,
    max_items: int | None = None,
    max_consecutive_errors: int = 4,
    transcribe_many: Callable[[Sequence[Path]], list[str]] | None = None,
    recover_after_error: Callable[[], None] | None = None,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Run or resume a bounded shard and return its latest checkpoint."""

    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    if max_items is not None and max_items < 0:
        raise ValueError("max_items must not be negative")
    if max_consecutive_errors < 1:
        raise ValueError("max_consecutive_errors must be positive")
    model_revision = str(model_revision or "").strip().casefold()
    if not re.fullmatch(r"[0-9a-f]{40}", model_revision):
        raise ValueError("model_revision must be an exact 40-hex commit SHA")
    manifest_path = manifest_path.resolve()
    output_prefix = output_prefix.resolve()
    device, dtype = _resolve_device_and_dtype(device, dtype)
    rows = _manifest_rows(
        manifest_path,
        shard_count=shard_count,
        shard_index=shard_index,
    )
    artifacts = validation_artifact_paths(
        output_prefix,
        shard_count=shard_count,
        shard_index=shard_index,
    )
    artifacts["lock"].parent.mkdir(parents=True, exist_ok=True)
    manifest_digest = _sha256_path(manifest_path)
    gates = {
        "maximum_wer_bp": maximum_wer_bp,
        "minimum_content_word_coverage_bp": minimum_content_coverage_bp,
        "minimum_similarity_bp": minimum_similarity_bp,
        "require_numeric_sequences_match": True,
    }
    fingerprint = _run_fingerprint(
        manifest_sha256=manifest_digest,
        model_name=model_name,
        model_revision=model_revision,
        device=device,
        dtype=dtype,
        language=language,
        minimum_similarity_bp=minimum_similarity_bp,
        minimum_content_coverage_bp=minimum_content_coverage_bp,
        maximum_wer_bp=maximum_wer_bp,
        shard_count=shard_count,
        shard_index=shard_index,
    )

    with artifacts["lock"].open("a+b") as lock_handle:
        try:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError(
                f"validation shard is already running: {artifacts['lock']}"
            ) from exc

        selected_ids = {str(row["id"]) for _, row in rows}
        events, repaired_tail = load_receipt_events(
            artifacts["ledger"],
            run_fingerprint=fingerprint,
            selected_ids=selected_ids,
        )
        latest = _latest_events(events)
        previous_checkpoint: dict[str, Any] = {}
        if artifacts["checkpoint"].is_file():
            previous_checkpoint = json.loads(
                artifacts["checkpoint"].read_text(encoding="utf-8")
            )
            if previous_checkpoint.get("run_fingerprint") != fingerprint:
                raise ValueError(
                    "existing checkpoint belongs to another manifest or run "
                    "configuration"
                )
        started_at = str(previous_checkpoint.get("started_at") or _utc_now())
        prior_active_seconds = float(
            previous_checkpoint.get("active_seconds") or 0.0
        )
        process_started = time.monotonic()

        valid_audio: dict[str, tuple[str, str]] = {}
        prepared: list[tuple[int, dict[str, Any], Path, str]] = []
        for manifest_index, row in rows:
            audio_id = str(row["id"])
            audio_value = str(
                row.get("preferredAudioPath")
                or row.get("mp3Path")
                or row.get("audioPath")
                or ""
            )
            audio_path = _resolve_audio_path(manifest_path, audio_value)
            if not audio_path.is_file() or audio_path.is_symlink():
                raise ValueError(
                    f"audio path for {audio_id!r} is missing or unsafe: "
                    f"{audio_path}"
                )
            audio_digest = _sha256_path(audio_path)
            expected_digest = sha256(str(row["text"]).encode()).hexdigest()
            valid_audio[audio_id] = (audio_digest, expected_digest)
            event = latest.get(audio_id)
            if event is not None and event.get("status") == "validated":
                if valid_audio[audio_id] == (
                    str(event.get("audio_sha256") or ""),
                    str(event.get("expected_text_sha256") or ""),
                ):
                    continue
            prepared.append((manifest_index, row, audio_path, audio_digest))

        if max_items is not None:
            prepared = prepared[:max_items]
        summary = _summarize(rows=rows, latest=latest, valid_audio=valid_audio)
        checkpoint = _checkpoint_payload(
            manifest_path=manifest_path,
            manifest_sha256=manifest_digest,
            paths=artifacts,
            run_fingerprint=fingerprint,
            model_name=model_name,
            model_revision=model_revision,
            device=device,
            dtype=dtype,
            language=language,
            gates=gates,
            shard_count=shard_count,
            shard_index=shard_index,
            event_count=len(events),
            repaired_partial_tail=repaired_tail,
            summary=summary,
            started_at=started_at,
            active_seconds=prior_active_seconds,
            status="running" if summary["pending_count"] else "complete",
        )
        atomic_write_json(artifacts["checkpoint"], checkpoint)
        if summary["pending_count"] and artifacts["receipt"].is_file():
            # A completed receipt becomes stale if a bound audio object changes.
            # The append-only ledger remains intact and the changed object is
            # revalidated before a replacement receipt is published.
            artifacts["receipt"].unlink()
            _fsync_parent(artifacts["receipt"])
        if summary["pending_count"] and artifacts["failures"].is_file():
            artifacts["failures"].unlink()
            _fsync_parent(artifacts["failures"])

        transcriber: TransformersWhisperTranscriber | None = None
        if transcribe_many is None and prepared:
            transcriber = TransformersWhisperTranscriber(
                model_name=model_name,
                model_revision=model_revision,
                device=device,
                dtype=dtype,
                language=language,
                batch_size=batch_size,
            )
            transcribe_many = transcriber.transcribe_many
            recover_after_error = transcriber.recover_after_error

        consecutive_errors = 0
        for offset in range(0, len(prepared), batch_size):
            batch = prepared[offset : offset + batch_size]
            assert transcribe_many is not None
            results = _transcribe_resiliently(
                transcribe_many,
                [item[2] for item in batch],
                recover_after_error=recover_after_error,
            )
            new_events: list[dict[str, Any]] = []
            for (manifest_index, row, audio_path, audio_digest), result in zip(
                batch, results, strict=True
            ):
                if isinstance(result, Exception):
                    event = _build_error_event(
                        row=row,
                        manifest_index=manifest_index,
                        audio_path=audio_path,
                        audio_digest=audio_digest,
                        error=result,
                        model_name=model_name,
                        model_revision=model_revision,
                        device=device,
                        dtype=dtype,
                        run_fingerprint=fingerprint,
                        shard_count=shard_count,
                        shard_index=shard_index,
                    )
                    consecutive_errors += 1
                else:
                    event = _build_validation_event(
                        row=row,
                        manifest_index=manifest_index,
                        audio_path=audio_path,
                        audio_digest=audio_digest,
                        transcript=result,
                        model_name=model_name,
                        model_revision=model_revision,
                        device=device,
                        dtype=dtype,
                        run_fingerprint=fingerprint,
                        minimum_similarity_bp=minimum_similarity_bp,
                        minimum_content_coverage_bp=minimum_content_coverage_bp,
                        maximum_wer_bp=maximum_wer_bp,
                        shard_count=shard_count,
                        shard_index=shard_index,
                    )
                    consecutive_errors = 0
                new_events.append(event)
                latest[str(event["audio_id"])] = event
            append_receipt_events(artifacts["ledger"], new_events)
            events.extend(new_events)
            summary = _summarize(
                rows=rows,
                latest=latest,
                valid_audio=valid_audio,
            )
            active_seconds = (
                prior_active_seconds + time.monotonic() - process_started
            )
            checkpoint = _checkpoint_payload(
                manifest_path=manifest_path,
                manifest_sha256=manifest_digest,
                paths=artifacts,
                run_fingerprint=fingerprint,
                model_name=model_name,
                model_revision=model_revision,
                device=device,
                dtype=dtype,
                language=language,
                gates=gates,
                shard_count=shard_count,
                shard_index=shard_index,
                event_count=len(events),
                repaired_partial_tail=repaired_tail,
                summary=summary,
                started_at=started_at,
                active_seconds=active_seconds,
                status="running" if summary["pending_count"] else "complete",
            )
            atomic_write_json(artifacts["checkpoint"], checkpoint)
            if progress_callback is not None:
                progress_callback(checkpoint)
            if consecutive_errors >= max_consecutive_errors:
                break

        summary = _summarize(rows=rows, latest=latest, valid_audio=valid_audio)
        active_seconds = prior_active_seconds + time.monotonic() - process_started
        status = "complete" if summary["pending_count"] == 0 else "running"
        checkpoint = _checkpoint_payload(
            manifest_path=manifest_path,
            manifest_sha256=manifest_digest,
            paths=artifacts,
            run_fingerprint=fingerprint,
            model_name=model_name,
            model_revision=model_revision,
            device=device,
            dtype=dtype,
            language=language,
            gates=gates,
            shard_count=shard_count,
            shard_index=shard_index,
            event_count=len(events),
            repaired_partial_tail=repaired_tail,
            summary=summary,
            started_at=started_at,
            active_seconds=active_seconds,
            status=status,
        )
        atomic_write_json(artifacts["checkpoint"], checkpoint)

        if status == "complete":
            ordered = [latest[str(row["id"])] for _, row in rows]
            rows_by_id = {str(row["id"]): row for _, row in rows}
            semantic_items = semantic_corruption_items(rows)
            semantic_reason_counts = {
                reason: sum(
                    reason in item["reasons"] for item in semantic_items
                )
                for reason in (
                    "apostrophe_direction_expansion",
                    "st_abbreviation_expanded_to_street",
                )
            }
            semantic_manifest = {
                "corruption_count": len(semantic_items),
                "items": semantic_items,
                "manifest_sha256": manifest_digest,
                "reason_counts": semantic_reason_counts,
                "release_eligible_count": len(rows) - len(semantic_items),
                "scan_rule": (
                    "confirmed_abbreviation_and_apostrophe_direction_rules_v2"
                ),
                "schema_version": SEMANTIC_CORRUPTION_SCHEMA,
            }
            atomic_write_json(
                artifacts["semantic_corruptions"], semantic_manifest
            )
            semantic_manifest_digest = _sha256_path(
                artifacts["semantic_corruptions"]
            )
            failed_items = []
            for event in ordered:
                if event.get("passed") is True:
                    continue
                row = rows_by_id[str(event["audio_id"])]
                failed_items.append(
                    {
                        "audio_id": event["audio_id"],
                        "audio_sha256": event["audio_sha256"],
                        "content_word_coverage_bp": event[
                            "content_word_coverage_bp"
                        ],
                        "expected_text_sha256": event["expected_text_sha256"],
                        "failure_reasons": _failure_reasons(event, gates),
                        "forbidden_negative_detected": event[
                            "forbidden_negative_detected"
                        ],
                        "manifest_index": event["manifest_index"],
                        "normalized_similarity_bp": event[
                            "normalized_similarity_bp"
                        ],
                        "numeric_sequences_match": event[
                            "numeric_sequences_match"
                        ],
                        "source_ids": [
                            str(value)
                            for value in row.get("sourceIds") or []
                            if str(value)
                        ],
                        "validation_receipt_id": event[
                            "validation_receipt_id"
                        ],
                        "wer_bp": event["wer_bp"],
                    }
                )
            failure_manifest = {
                "failed_count": len(failed_items),
                "failures": failed_items,
                "manifest_sha256": manifest_digest,
                "model_name": model_name,
                "model_revision": model_revision,
                "run_fingerprint": fingerprint,
                "schema_version": FAILURE_MANIFEST_SCHEMA,
                "validator_version": VALIDATOR_VERSION,
            }
            atomic_write_json(artifacts["failures"], failure_manifest)
            failure_manifest_digest = _sha256_path(artifacts["failures"])
            final_receipt = {
                "all_passed": (
                    summary["failed_count"] == 0 and not semantic_items
                ),
                "completed_at": _utc_now(),
                "device": device,
                "dtype": dtype,
                "gates": gates,
                "language": language,
                "ledger": _display_path(artifacts["ledger"]),
                "ledger_sha256": _sha256_path(artifacts["ledger"]),
                "failed_item_manifest": _display_path(artifacts["failures"]),
                "failed_item_manifest_sha256": failure_manifest_digest,
                "manifest": _display_path(manifest_path),
                "manifest_sha256": manifest_digest,
                "maximum_observed_wer_bp": max(
                    int(event["wer_bp"]) for event in ordered
                ),
                "minimum_content_word_coverage_bp": min(
                    int(event["content_word_coverage_bp"]) for event in ordered
                ),
                "minimum_normalized_similarity_bp": min(
                    int(event["normalized_similarity_bp"]) for event in ordered
                ),
                "model_name": model_name,
                "model_revision": model_revision,
                "remote_writes": False,
                "run_fingerprint": fingerprint,
                "schema_version": RECEIPT_SCHEMA,
                "semantic_corruption_count": len(semantic_items),
                "semantic_corruption_manifest": _display_path(
                    artifacts["semantic_corruptions"]
                ),
                "semantic_corruption_manifest_sha256": (
                    semantic_manifest_digest
                ),
                "semantic_corruption_reason_counts": semantic_reason_counts,
                "shard_count": shard_count,
                "shard_index": shard_index,
                "validation_receipt_id": (
                    "abby-voice-full-asr-corpus:sha256:"
                    + sha256(
                        (
                            manifest_digest
                            + "\0"
                            + _sha256_path(artifacts["ledger"])
                            + "\0"
                            + fingerprint
                            + "\0"
                            + semantic_manifest_digest
                        ).encode()
                    ).hexdigest()
                ),
                "validator_version": VALIDATOR_VERSION,
                **summary,
            }
            atomic_write_json(artifacts["receipt"], final_receipt)
        return checkpoint


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output-prefix", type=Path, default=DEFAULT_OUTPUT_PREFIX)
    parser.add_argument("--model", default="openai/whisper-base")
    parser.add_argument(
        "--model-revision",
        required=True,
        help="Exact 40-hex Hugging Face model commit SHA.",
    )
    parser.add_argument("--device", default="auto")
    parser.add_argument("--dtype", default="auto")
    parser.add_argument("--language", default="en")
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--minimum-similarity-bp", type=int, default=7_800)
    parser.add_argument("--minimum-content-coverage-bp", type=int, default=6_500)
    parser.add_argument("--maximum-wer-bp", type=int, default=3_500)
    parser.add_argument("--shard-count", type=int, default=1)
    parser.add_argument("--shard-index", type=int, default=0)
    parser.add_argument(
        "--max-items",
        type=int,
        default=None,
        help="Process at most this many pending items, primarily for canaries.",
    )
    parser.add_argument("--max-consecutive-errors", type=int, default=4)
    parser.add_argument(
        "--progress-every",
        type=int,
        default=40,
        help="Print progress after this many newly completed items.",
    )
    parser.add_argument(
        "--soft-fail",
        action="store_true",
        help="Return success when transcription coverage is complete but gates fail.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    last_printed = -1

    def report_progress(checkpoint: dict[str, Any]) -> None:
        nonlocal last_printed
        completed = int(checkpoint["completed_count"])
        total = int(checkpoint["total_count"])
        should_print = (
            completed == total
            or completed - last_printed >= max(1, args.progress_every)
        )
        if not should_print:
            return
        last_printed = completed
        print(
            json.dumps(
                {
                    "completed": completed,
                    "completed_bp": checkpoint["completed_bp"],
                    "errors": checkpoint["error_count"],
                    "estimated_completion_at": checkpoint[
                        "estimated_completion_at"
                    ],
                    "failed": checkpoint["failed_count"],
                    "passed": checkpoint["passed_count"],
                    "total": total,
                    "updated_at": checkpoint["updated_at"],
                },
                sort_keys=True,
            ),
            flush=True,
        )

    checkpoint = run_validation(
        args.manifest,
        args.output_prefix,
        model_name=args.model,
        model_revision=args.model_revision,
        device=args.device,
        dtype=args.dtype,
        language=args.language,
        batch_size=args.batch_size,
        minimum_similarity_bp=args.minimum_similarity_bp,
        minimum_content_coverage_bp=args.minimum_content_coverage_bp,
        maximum_wer_bp=args.maximum_wer_bp,
        shard_count=args.shard_count,
        shard_index=args.shard_index,
        max_items=args.max_items,
        max_consecutive_errors=args.max_consecutive_errors,
        progress_callback=report_progress,
    )
    print(json.dumps(checkpoint, indent=2, sort_keys=True), flush=True)
    if checkpoint["pending_count"]:
        raise SystemExit(75)
    if checkpoint["failed_count"] and not args.soft_fail:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
