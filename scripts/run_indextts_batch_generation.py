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
from typing import Any, Mapping, Sequence

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
DEFAULT_FULL_REPAIR_OVERLAY = (
    CANONICAL_DATASET_ROOT
    / "metadata/regeneration-padding-repair-generation-manifest.json"
)
EXIT_SUCCESS = 0
EXIT_BATCH_FAILED = 1
EXIT_RATE_LIMITED = 75
EXIT_RUNTIME_LIMIT = 124
BATCH_RECEIPT_KEY = "batchReceipt"
BATCH_RECEIPT_SCHEMA_VERSION = 1
PUBLIC_MANIFEST_AGGREGATION_SCHEMA_VERSION = 1
_PUBLIC_MANIFEST_INVARIANT_FIELDS = (
    "schemaVersion",
    "provider",
    "spaceUrl",
    "referenceAudio",
    "voiceDescription",
    "sources",
    "normalization",
    "mp3",
    "batchInference",
    "bucketUpload",
)
_RESPONSE_EXECUTION_FIELDS = {
    "status",
    "latencyMs",
    "batchLatencyMs",
    "batchMode",
    "batchFallbackReason",
    "batchRequestedSize",
    "batchExecutedSize",
    "batchSplitDepth",
}
_REPAIR_ARTIFACT_FIELDS = {
    "status",
    "audioPath",
    "mimeType",
    "audioBytes",
    "mp3Path",
    "mp3MimeType",
    "mp3Bytes",
    "preferredAudioPath",
    "preferredMimeType",
    "wavDeprecated",
    "latencyMs",
    "batchLatencyMs",
    "batchMode",
}


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
    parser.add_argument(
        "--repair-overlay",
        type=Path,
        default=None,
        help=(
            "Optional audited regeneration manifest whose artifact metadata "
            "overlays older immutable batch receipts."
        ),
    )
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
    if args.repair_overlay is None:
        args.repair_overlay = DEFAULT_FULL_REPAIR_OVERLAY
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


def run_identity_sha256(run_identity: Mapping[str, Any]) -> str:
    """Return a stable identity for selecting receipts from one compatible run."""

    encoded = json.dumps(
        run_identity,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_resume_checkpoint(
    args: argparse.Namespace,
    *,
    total: int,
    run_identity: dict[str, Any],
) -> tuple[int, int, int, int]:
    requested_offset = max(0, int(args.start_offset))
    if bool(getattr(args, "reset_state", False)) or not bool(getattr(args, "resume", True)):
        return requested_offset, 0, 0, requested_offset
    if not args.state.exists():
        return requested_offset, 0, 0, requested_offset

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
    run_start_offset = state.get("runStartOffset")
    if (
        isinstance(run_start_offset, bool)
        or not isinstance(run_start_offset, int)
        or run_start_offset < 0
        or run_start_offset > next_offset
    ):
        # Schema-v1/v2 checkpoints did not persist the initial offset. Infer it
        # from completed batches so existing regeneration runs remain resumable.
        run_start_offset = max(0, next_offset - batches_completed * max(1, int(args.batch_size)))
    return max(requested_offset, next_offset), batches_completed, failures, run_start_offset


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
            json.dump(payload, handle, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def batch_manifest_path(batch_manifest_dir: Path, *, batch_size: int, offset: int) -> Path:
    batch_index = offset // max(1, batch_size)
    return batch_manifest_dir / f"batch-{batch_index:05d}-offset-{offset:06d}.json"


def batch_public_manifest_path(manifest: Path) -> Path:
    """Return the immutable public receipt path owned by one child batch."""

    return manifest.with_name(f"{manifest.stem}.public.json")


def canonical_response_ids(
    response_manifest: Path | None,
    dag: Path,
    results: Path,
) -> list[str]:
    from scripts.precompute_indextts_responses import load_audio_responses, load_audio_responses_from_manifest

    if response_manifest is not None:
        responses = load_audio_responses_from_manifest(response_manifest)
    else:
        responses = load_audio_responses(dag, results)
    return [str(response.get("id") or "") for response in responses]


def public_payload_from_batch_manifest(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Derive the browser-facing receipt used by the child precompute script."""

    from scripts.precompute_indextts_responses import audio_url_for

    responses = payload.get("responses")
    if not isinstance(responses, list):
        raise RuntimeError("Cannot build public batch receipt: responses is not a list")
    return {
        **{key: value for key, value in payload.items() if key != BATCH_RECEIPT_KEY},
        "referenceAudio": "abby-reference.wav",
        "responses": [
            {
                **entry,
                "audioUrl": audio_url_for(str(entry.get("audioPath") or "")),
                "mp3Url": audio_url_for(str(entry.get("mp3Path") or "")),
                "preferredAudioUrl": audio_url_for(
                    str(entry.get("preferredAudioPath") or entry.get("audioPath") or "")
                ),
            }
            for entry in responses
            if isinstance(entry, Mapping)
        ],
    }


def _validated_response_entries(
    payload: Mapping[str, Any],
    *,
    path: Path,
    expected_count: int,
    expected_ids: Sequence[str] | None = None,
) -> list[dict[str, Any]]:
    responses = payload.get("responses")
    if not isinstance(responses, list):
        raise RuntimeError(f"Invalid batch receipt {path}: responses is not a list")
    if len(responses) != expected_count:
        raise RuntimeError(
            f"Incomplete batch receipt {path}: found {len(responses)} response(s), expected {expected_count}"
        )
    declared_count = payload.get("responseCount")
    if declared_count is not None and (
        isinstance(declared_count, bool)
        or not isinstance(declared_count, int)
        or declared_count != len(responses)
    ):
        raise RuntimeError(
            f"Invalid batch receipt {path}: responseCount={declared_count!r} "
            f"does not match {len(responses)} response(s)"
        )

    validated: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, value in enumerate(responses):
        if not isinstance(value, dict):
            raise RuntimeError(f"Invalid batch receipt {path}: response {index} is not an object")
        response_id = str(value.get("id") or "").strip()
        text_hash = str(value.get("textHash") or "").strip()
        if not response_id or not text_hash or response_id != f"abby-tts-{text_hash}":
            raise RuntimeError(
                f"Invalid canonical audio ID in {path} response {index}: "
                f"id={response_id!r}, textHash={text_hash!r}"
            )
        if response_id in seen_ids:
            raise RuntimeError(f"Duplicate canonical audio ID {response_id!r} inside {path}")
        seen_ids.add(response_id)
        status = str(value.get("status") or "").strip().lower()
        if status in {"", "failed", "planned"}:
            raise RuntimeError(
                f"Unsuccessful response {response_id!r} in {path}: status={status or '<missing>'}"
            )
        if not any(
            str(value.get(field) or "").strip()
            for field in (
                "preferredAudioPath",
                "mp3Path",
                "audioPath",
                "preferredBucketAudioUri",
                "bucketMp3Uri",
                "bucketAudioUri",
            )
        ):
            raise RuntimeError(f"Response {response_id!r} in {path} has no usable audio reference")
        validated.append(dict(value))

    actual_ids = [str(entry["id"]) for entry in validated]
    if expected_ids is not None and actual_ids != list(expected_ids):
        raise RuntimeError(
            f"Incompatible batch receipt {path}: canonical response IDs do not match "
            "the current source slice"
        )
    return validated


def _validate_legacy_receipt_identity(
    payload: Mapping[str, Any],
    *,
    path: Path,
    run_identity: Mapping[str, Any],
) -> None:
    """Fail closed before adopting a pre-identity receipt from an old runner."""

    expected_provider = str(run_identity.get("modelName") or "").strip()
    actual_provider = str(payload.get("provider") or "").strip()
    if not expected_provider or actual_provider != expected_provider:
        raise RuntimeError(
            f"Cannot adopt legacy batch receipt {path}: provider {actual_provider!r} "
            f"does not match {expected_provider!r}"
        )
    expected_space = str(run_identity.get("spaceUrl") or "").strip().rstrip("/")
    actual_space = str(payload.get("spaceUrl") or "").strip().rstrip("/")
    if not expected_space or actual_space != expected_space:
        raise RuntimeError(
            f"Cannot adopt legacy batch receipt {path}: Space {actual_space!r} "
            f"does not match {expected_space!r}"
        )

    source_identity = run_identity.get("source")
    sources = payload.get("sources")
    if not isinstance(source_identity, Mapping) or not isinstance(sources, Mapping):
        raise RuntimeError(f"Cannot adopt legacy batch receipt {path}: source metadata is missing")
    if source_identity.get("kind") == "response-manifest":
        expected = source_identity.get("responseManifest")
        actual = str(sources.get("responseManifest") or "").strip()
        if not isinstance(expected, Mapping) or not actual:
            raise RuntimeError(f"Cannot adopt legacy batch receipt {path}: response manifest is missing")
        if Path(actual).resolve() != Path(str(expected.get("path") or "")).resolve():
            raise RuntimeError(
                f"Cannot adopt legacy batch receipt {path}: response manifest path does not match"
            )


def stamp_completed_batch_receipts(
    *,
    manifest: Path,
    public_receipt: Path,
    run_identity: Mapping[str, Any],
    offset: int,
    batch_size: int,
    total: int,
    expected_ids: Sequence[str] | None = None,
    allow_legacy_public_derivation: bool = False,
) -> Path:
    """Validate and atomically stamp one successful raw/public receipt pair."""

    if not manifest.exists():
        raise RuntimeError(f"Successful batch did not write its receipt: {manifest}")
    raw_payload = load_json_file(manifest)
    if not isinstance(raw_payload, dict):
        raise RuntimeError(f"Invalid batch receipt {manifest}: top level is not an object")
    existing_raw_receipt = raw_payload.get(BATCH_RECEIPT_KEY)
    identity_digest = run_identity_sha256(run_identity)
    if isinstance(existing_raw_receipt, Mapping):
        prior_digest = str(existing_raw_receipt.get("runIdentitySha256") or "")
        if prior_digest and prior_digest != identity_digest:
            raise RuntimeError(
                f"Incompatible stamped batch receipt {manifest}: run identity does not match"
            )
    elif allow_legacy_public_derivation:
        _validate_legacy_receipt_identity(raw_payload, path=manifest, run_identity=run_identity)

    expected_count = min(max(0, total - offset), max(1, batch_size))
    raw_entries = _validated_response_entries(
        raw_payload,
        path=manifest,
        expected_count=expected_count,
        expected_ids=expected_ids,
    )
    receipt_metadata = {
        "schemaVersion": BATCH_RECEIPT_SCHEMA_VERSION,
        "complete": True,
        "runIdentitySha256": identity_digest,
        "runIdentity": dict(run_identity),
        "batchIndex": offset // max(1, batch_size),
        "offset": offset,
        "requestedLimit": max(1, batch_size),
        "expectedResponseCount": expected_count,
        "responseCount": len(raw_entries),
    }
    stamped_raw = {**raw_payload, "responseCount": len(raw_entries), BATCH_RECEIPT_KEY: receipt_metadata}

    if public_receipt.exists():
        public_payload = load_json_file(public_receipt)
        if not isinstance(public_payload, dict):
            raise RuntimeError(f"Invalid public batch receipt {public_receipt}: top level is not an object")
        existing_public_receipt = public_payload.get(BATCH_RECEIPT_KEY)
        if isinstance(existing_public_receipt, Mapping):
            prior_digest = str(existing_public_receipt.get("runIdentitySha256") or "")
            if prior_digest and prior_digest != identity_digest:
                raise RuntimeError(
                    f"Incompatible stamped public receipt {public_receipt}: run identity does not match"
                )
        elif allow_legacy_public_derivation:
            # A shared or partially migrated public file cannot prove which
            # child produced it. Rebuild it from the validated raw receipt.
            public_payload = public_payload_from_batch_manifest(stamped_raw)
    elif allow_legacy_public_derivation:
        public_payload = public_payload_from_batch_manifest(stamped_raw)
    else:
        raise RuntimeError(f"Successful batch did not write its public receipt: {public_receipt}")

    public_entries = _validated_response_entries(
        public_payload,
        path=public_receipt,
        expected_count=expected_count,
        expected_ids=expected_ids,
    )
    if [entry["id"] for entry in public_entries] != [entry["id"] for entry in raw_entries]:
        raise RuntimeError(f"Raw/public response IDs differ for batch receipt {manifest}")
    for raw_entry, public_entry in zip(raw_entries, public_entries):
        for key, raw_value in raw_entry.items():
            if key in public_entry and public_entry[key] != raw_value:
                raise RuntimeError(
                    f"Raw/public field {key!r} differs for canonical audio ID {raw_entry['id']!r}"
                )
    write_state(manifest, stamped_raw)
    raw_sha256 = sha256_file(manifest)
    public_metadata = {**receipt_metadata, "batchManifestSha256": raw_sha256}
    stamped_public = {
        **public_payload,
        "responseCount": len(public_entries),
        BATCH_RECEIPT_KEY: public_metadata,
    }
    write_state(public_receipt, stamped_public)
    return public_receipt


def bootstrap_completed_batch_receipts(
    *,
    args: argparse.Namespace,
    run_identity: Mapping[str, Any],
    response_ids: Sequence[str],
    run_start_offset: int,
    completed_offset: int,
    total: int,
) -> None:
    """Adopt validated receipts written before identity stamping was introduced."""

    offset = run_start_offset
    while offset < completed_offset:
        manifest = batch_manifest_path(args.batch_manifest_dir, batch_size=args.batch_size, offset=offset)
        public_receipt = batch_public_manifest_path(manifest)
        expected_count = min(max(0, total - offset), max(1, args.batch_size))
        expected_ids = response_ids[offset : offset + expected_count]
        stamp_completed_batch_receipts(
            manifest=manifest,
            public_receipt=public_receipt,
            run_identity=run_identity,
            offset=offset,
            batch_size=args.batch_size,
            total=total,
            expected_ids=expected_ids,
            allow_legacy_public_derivation=True,
        )
        offset = min(total, offset + max(1, args.batch_size))
    if offset != completed_offset:
        raise RuntimeError(
            f"Checkpoint offset {completed_offset} is not aligned with completed batch receipts "
            f"from run start {run_start_offset}"
        )


def _receipt_response_conflict_view(entry: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in entry.items()
        if key not in _RESPONSE_EXECUTION_FIELDS
    }


def apply_repair_overlay(
    response_by_id: dict[str, dict[str, Any]],
    *,
    repair_overlay: Path,
    public_manifest: Path,
) -> dict[str, Any]:
    """Overlay validated replacement-artifact metadata onto receipt entries."""

    payload = load_json_file(repair_overlay)
    if not isinstance(payload, Mapping):
        raise RuntimeError(
            f"Invalid repair overlay {repair_overlay}: top level is not an object"
        )
    raw_entries = payload.get("responses")
    if not isinstance(raw_entries, list):
        raise RuntimeError(
            f"Invalid repair overlay {repair_overlay}: responses is not a list"
        )
    declared_count = payload.get("responseCount")
    if (
        isinstance(declared_count, bool)
        or not isinstance(declared_count, int)
        or declared_count != len(raw_entries)
    ):
        raise RuntimeError(
            f"Invalid repair overlay {repair_overlay}: "
            f"responseCount={declared_count!r} does not match "
            f"{len(raw_entries)} response(s)"
        )

    seen_ids: set[str] = set()
    matched = 0
    for index, raw_entry in enumerate(raw_entries):
        if not isinstance(raw_entry, Mapping):
            raise RuntimeError(
                f"Invalid repair overlay {repair_overlay}: "
                f"response {index} is not an object"
            )
        response_id = str(raw_entry.get("id") or "").strip()
        if not response_id or response_id in seen_ids:
            raise RuntimeError(
                f"Invalid repair overlay {repair_overlay}: "
                f"duplicate or missing response ID {response_id!r}"
            )
        seen_ids.add(response_id)
        existing = response_by_id.get(response_id)
        if existing is None:
            continue
        for identity_field in ("textHash", "text"):
            overlay_value = raw_entry.get(identity_field)
            if (
                overlay_value is not None
                and existing.get(identity_field) != overlay_value
            ):
                raise RuntimeError(
                    f"Repair overlay identity mismatch for {response_id!r}: "
                    f"{identity_field} differs"
                )

        mp3_path_value = str(raw_entry.get("mp3Path") or "").strip()
        mp3_bytes = raw_entry.get("mp3Bytes")
        if not mp3_path_value or isinstance(mp3_bytes, bool) or not isinstance(
            mp3_bytes, int
        ):
            raise RuntimeError(
                f"Repair overlay {repair_overlay} has no authoritative MP3 "
                f"metadata for {response_id!r}"
            )
        mp3_path = Path(mp3_path_value)
        if not mp3_path.is_absolute():
            mp3_path = REPO_ROOT / mp3_path
        if not mp3_path.is_file() or mp3_path.stat().st_size != mp3_bytes:
            raise RuntimeError(
                f"Repair overlay MP3 size mismatch for {response_id!r}: "
                f"{mp3_path}"
            )

        updated = dict(existing)
        for field in _REPAIR_ARTIFACT_FIELDS:
            if field in raw_entry:
                updated[field] = raw_entry[field]
        response_by_id[response_id] = updated
        matched += 1

    return {
        "path": os.path.relpath(repair_overlay, start=public_manifest.parent),
        "sha256": sha256_file(repair_overlay),
        "declaredResponseCount": len(raw_entries),
        "matchedResponseCount": matched,
        "pendingResponseCount": len(raw_entries) - matched,
    }


def aggregate_public_batch_receipts(
    *,
    batch_manifest_dir: Path,
    public_manifest: Path,
    run_identity: Mapping[str, Any],
    run_start_offset: int,
    completed_offset: int,
    total: int,
    source_total: int,
    batch_size: int,
    repair_overlay: Path | None = None,
) -> dict[str, Any]:
    """Atomically rebuild the canonical public manifest from completed receipts."""

    identity_digest = run_identity_sha256(run_identity)
    selected_receipts: list[tuple[int, Path, dict[str, Any], list[dict[str, Any]]]] = []
    offset = run_start_offset
    while offset < completed_offset:
        manifest = batch_manifest_path(batch_manifest_dir, batch_size=batch_size, offset=offset)
        public_receipt = batch_public_manifest_path(manifest)
        if not public_receipt.exists():
            raise RuntimeError(f"Missing completed public batch receipt: {public_receipt}")
        payload = load_json_file(public_receipt)
        if not isinstance(payload, dict):
            raise RuntimeError(f"Invalid public batch receipt {public_receipt}: top level is not an object")
        receipt = payload.get(BATCH_RECEIPT_KEY)
        if not isinstance(receipt, Mapping):
            raise RuntimeError(f"Unstamped public batch receipt cannot be aggregated: {public_receipt}")
        if str(receipt.get("runIdentitySha256") or "") != identity_digest:
            raise RuntimeError(
                f"Incompatible public batch receipt at required offset {offset}: {public_receipt}"
            )
        if receipt.get("runIdentity") != run_identity:
            raise RuntimeError(f"Run identity payload mismatch in {public_receipt}")
        expected_count = min(max(0, total - offset), max(1, batch_size))
        for field, expected in (
            ("complete", True),
            ("offset", offset),
            ("batchIndex", offset // max(1, batch_size)),
            ("expectedResponseCount", expected_count),
            ("responseCount", expected_count),
        ):
            if receipt.get(field) != expected:
                raise RuntimeError(
                    f"Invalid {field} in {public_receipt}: {receipt.get(field)!r} != {expected!r}"
                )
        raw_sha256 = str(receipt.get("batchManifestSha256") or "")
        if not manifest.exists() or not raw_sha256 or sha256_file(manifest) != raw_sha256:
            raise RuntimeError(f"Raw batch receipt checksum mismatch for {public_receipt}")
        entries = _validated_response_entries(
            payload,
            path=public_receipt,
            expected_count=expected_count,
        )
        selected_receipts.append((offset, public_receipt, payload, entries))
        offset = min(total, offset + max(1, batch_size))
    if offset != completed_offset:
        raise RuntimeError(
            f"Completed offset {completed_offset} is not aligned with receipt ranges "
            f"from {run_start_offset}"
        )

    base_payload: dict[str, Any] = {}
    invariant_values: dict[str, Any] = {}
    response_by_id: dict[str, dict[str, Any]] = {}
    response_order: list[str] = []
    receipt_summaries: list[dict[str, Any]] = []
    generated_at_values: list[str] = []
    covered_response_count = 0

    for receipt_offset, receipt_path, payload, entries in selected_receipts:
        if not base_payload:
            base_payload = {
                key: value
                for key, value in payload.items()
                if key not in {"responses", "responseCount", "generatedAt", BATCH_RECEIPT_KEY, "transcriptValidation"}
            }
        for field in _PUBLIC_MANIFEST_INVARIANT_FIELDS:
            if field not in payload:
                continue
            if field not in invariant_values:
                invariant_values[field] = payload[field]
            elif invariant_values[field] != payload[field]:
                raise RuntimeError(
                    f"Conflicting public manifest field {field!r} in {receipt_path}"
                )
        generated_at = str(payload.get("generatedAt") or "").strip()
        if generated_at:
            generated_at_values.append(generated_at)
        covered_response_count += len(entries)
        for entry in entries:
            response_id = str(entry["id"])
            existing = response_by_id.get(response_id)
            if existing is None:
                response_by_id[response_id] = entry
                response_order.append(response_id)
            elif _receipt_response_conflict_view(existing) != _receipt_response_conflict_view(entry):
                raise RuntimeError(
                    f"Conflicting duplicate canonical audio ID {response_id!r} in {receipt_path}"
                )
        receipt_summaries.append(
            {
                "offset": receipt_offset,
                "responseCount": len(entries),
                "path": os.path.relpath(receipt_path, start=public_manifest.parent),
                "sha256": sha256_file(receipt_path),
            }
        )

    repair_overlay_summaries: list[dict[str, Any]] = []
    if repair_overlay is not None and repair_overlay.exists():
        repair_overlay_summaries.append(
            apply_repair_overlay(
                response_by_id,
                repair_overlay=repair_overlay,
                public_manifest=public_manifest,
            )
        )
    responses = [response_by_id[response_id] for response_id in response_order]
    aggregate_payload = {
        **base_payload,
        "schemaVersion": invariant_values.get("schemaVersion", 1),
        "generatedAt": max(generated_at_values, default=""),
        "responseCount": len(responses),
        "aggregation": {
            "schemaVersion": PUBLIC_MANIFEST_AGGREGATION_SCHEMA_VERSION,
            "runIdentitySha256": identity_digest,
            "runIdentity": dict(run_identity),
            "runStartOffset": run_start_offset,
            "completedOffset": completed_offset,
            "totalResponses": total,
            "sourceResponseCount": source_total,
            "coveredResponseCount": covered_response_count,
            "deduplicatedResponseCount": len(responses),
            "duplicateResponseCount": covered_response_count - len(responses),
            "completedBatchCount": len(selected_receipts),
            "complete": run_start_offset == 0 and completed_offset == total,
            "receipts": receipt_summaries,
            **(
                {"repairOverlays": repair_overlay_summaries}
                if repair_overlay_summaries
                else {}
            ),
        },
        "responses": responses,
    }
    write_state(public_manifest, aggregate_payload)
    return aggregate_payload


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
    "audio_trailing_silence_exceeded",
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
    run_start_offset: int = 0,
    public_manifest: Path | None = None,
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
        "runStartOffset": run_start_offset,
        "batchSize": batch_size,
        "batchesCompleted": batches_completed,
        "failures": failures,
        "lastManifest": str(manifest) if manifest is not None else "",
        "lastProgress": str(progress) if progress is not None else "",
        **({"publicManifest": str(public_manifest)} if public_manifest is not None else {}),
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
        str(batch_public_manifest_path(manifest)),
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
    offset, batches_completed, failures, run_start_offset = load_resume_checkpoint(
        args,
        total=total,
        run_identity=run_identity,
    )
    response_ids = canonical_response_ids(args.response_manifest, args.dag, args.results)
    if len(response_ids) != total:
        raise RuntimeError(
            f"Canonical response ID count {len(response_ids)} does not match totalResponses {total}"
        )
    if offset > run_start_offset:
        bootstrap_completed_batch_receipts(
            args=args,
            run_identity=run_identity,
            response_ids=response_ids,
            run_start_offset=run_start_offset,
            completed_offset=offset,
            total=total,
        )
    aggregate_public_batch_receipts(
        batch_manifest_dir=args.batch_manifest_dir,
        public_manifest=args.public_manifest,
        run_identity=run_identity,
        run_start_offset=run_start_offset,
        completed_offset=offset,
        total=total,
        source_total=source_total,
        batch_size=args.batch_size,
        repair_overlay=args.repair_overlay,
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
        manifest = batch_manifest_path(args.batch_manifest_dir, batch_size=args.batch_size, offset=offset)
        public_receipt = batch_public_manifest_path(manifest)
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
                expected_count = min(max(0, total - offset), max(1, args.batch_size))
                try:
                    stamp_completed_batch_receipts(
                        manifest=manifest,
                        public_receipt=public_receipt,
                        run_identity=run_identity,
                        offset=offset,
                        batch_size=args.batch_size,
                        total=total,
                        expected_ids=response_ids[offset : offset + expected_count],
                    )
                except RuntimeError as exc:
                    failures += 1
                    stop_reason = f"Batch receipt validation failed: {exc}"
                    break
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
                run_start_offset=run_start_offset,
                public_manifest=args.public_manifest,
                stop_reason=stop_reason or "Batch failed",
                retry_after=retry_after,
            )
            break

        next_offset = min(total, offset + args.batch_size)
        try:
            aggregate_public_batch_receipts(
                batch_manifest_dir=args.batch_manifest_dir,
                public_manifest=args.public_manifest,
                run_identity=run_identity,
                run_start_offset=run_start_offset,
                completed_offset=next_offset,
                total=total,
                source_total=source_total,
                batch_size=args.batch_size,
                repair_overlay=args.repair_overlay,
            )
        except RuntimeError as exc:
            failures += 1
            stop_reason = f"Canonical public manifest aggregation failed: {exc}"
            exit_code = EXIT_BATCH_FAILED
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
                run_start_offset=run_start_offset,
                public_manifest=args.public_manifest,
                stop_reason=stop_reason,
            )
            break

        batches_completed += 1
        offset = next_offset
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
            run_start_offset=run_start_offset,
            public_manifest=args.public_manifest,
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
            run_start_offset=run_start_offset,
            public_manifest=args.public_manifest,
            stop_reason=stop_reason,
            retry_after=retry_after,
        )
        exit_code = EXIT_RUNTIME_LIMIT

    if exit_code == EXIT_SUCCESS and offset == total:
        aggregate_public_batch_receipts(
            batch_manifest_dir=args.batch_manifest_dir,
            public_manifest=args.public_manifest,
            run_identity=run_identity,
            run_start_offset=run_start_offset,
            completed_offset=offset,
            total=total,
            source_total=source_total,
            batch_size=args.batch_size,
            repair_overlay=args.repair_overlay,
        )

    summary = f"Finished batch loop at offset {offset}/{total}; batches={batches_completed}; failures={failures}"
    if stop_reason:
        summary = f"{summary}; stopReason={stop_reason}"
        if retry_after:
            summary = f"{summary}; retryAfter={retry_after}"
    print(summary)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
