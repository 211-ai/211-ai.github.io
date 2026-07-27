#!/usr/bin/env python3
"""Recover Abby response audio from a Hugging Face bucket without fuzzy joins.

The command is intentionally staged:

``plan``
    Normalize the pinned aggregate response manifest, discover the mutable
    bucket read-only, build the exact legacy-hash-to-canonical-response alias,
    and write content-addressed listing and recovery-plan evidence.

``fetch``
    Consume an immutable plan, download a bounded canary (three rows by
    default), verify Xet binding, raw SHA-256, size, media magic and ffprobe
    decode evidence, and emit staging artifacts plus retry dispositions.

``schedule``
    Verify a recovery bundle, import its cache bytes into the accelerator's
    content-addressed artifact store, and produce ASR/audio-validation jobs.
    Queue submission is explicit; scheduling still does not promote or publish
    any dataset row.

``admit``
    Strictly ingest completed queue receipts, bind retained ASR evidence to the
    exact recovered bytes, and emit promoted audio rows or quarantine
    dispositions. Admission performs no dataset merge or remote publication.

``merge-release``
    Verify pinned normalized and admission bundles, reciprocally merge admitted
    audio into the normalized responses, rebuild GraphRAG, and construct and
    validate a deterministic release in a new local directory. This stage never
    calls a remote publisher.

No stage changes the source bucket or publishes a dataset release remotely.
Recovered rows remain staged until ASR, acoustic, and exact critical-slot
validation pass; admitted rows are promoted only through the pinned local merge
and release-validation boundary.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Mapping
from hashlib import sha256
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPO_ROOT / "ipfs_datasets_py"
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from ipfs_datasets_py.huggingface.bucket import (  # noqa: E402
    HuggingFaceBucketHttpClient,
    HuggingFaceBucketListing,
    HuggingFaceBucketStore,
)
from ipfs_datasets_py.voice.bucket_audio_inventory import (  # noqa: E402
    AbbyVoiceBucketAudioInventory,
    build_bucket_audio_inventory,
    discover_production_run_ids,
)
from ipfs_datasets_py.voice.bucket_audio_normalize import (  # noqa: E402
    AbbyVoiceBucketAudioNormalizedBundle,
    normalize_bucket_audio_entries,
)
from ipfs_datasets_py.voice.bucket_audio_plan import (  # noqa: E402
    AbbyVoiceBucketAudioPlan,
    plan_abby_voice_bucket_audio,
)
from ipfs_datasets_py.voice.bucket_audio_recovery import (  # noqa: E402
    AbbyVoiceBucketAudioRecovery,
    DecodeProbeEvidence,
    bucket_audio_cache_path,
    recover_abby_voice_bucket_audio,
)
from ipfs_datasets_py.voice.normalize import (  # noqa: E402
    NormalizationConfig,
    NormalizationResult,
    normalize_manifest,
)
from ipfs_datasets_py.voice.reconcile import (  # noqa: E402
    AudioReconciliationResult,
)

DEFAULT_BUCKET_ID = "Publicus/abby-voice"
DEFAULT_SOURCE = REPO_ROOT / "docs" / "pregenerated_text_response_manifest.json"
DEFAULT_SOURCE_SHA256 = (
    "91103f89fcc12137f1a1603e5fa8cbb9e5922aa978e5c0b8f055b5d7fc1442fe"
)
DEFAULT_OUTPUT_DIR = REPO_ROOT / "data" / "abby_voice" / "recovery"
DEFAULT_CACHE_DIR = REPO_ROOT / "tmp_assets" / "abby-voice-audio-recovery"
DEFAULT_ALLOWED_RUN_IDS = (
    "abby-full-preprocess-20260605T063738Z",
    "abby-full-preprocess-20260614T004544Z",
    "abby-full-preprocess-20260621T141953Z",
    "abby-full-preprocess-20260622T152102Z",
)
DEFAULT_STABLE_DISCOVERY_PASSES = 2
PINNED_ACCEPTED_RESPONSE_COUNT = 13_779
PINNED_MIN_SELECTED_AUDIO_COUNT = 13_771
PINNED_MAX_MISSING_AUDIO_COUNT = 8
PLAN_ARTIFACT_MANIFEST_NAME = "artifact-manifest.json"
PLAN_ARTIFACT_MANIFEST_SCHEMA_VERSION = (
    "abby_voice_bucket_audio_plan_artifacts_v1"
)
LATEST_PLAN_POINTER_NAME = "latest.json"
LATEST_PLAN_POINTER_SCHEMA_VERSION = "abby_voice_bucket_audio_latest_plan_v1"
RECOVERY_ARTIFACT_MANIFEST_SCHEMA_VERSION = (
    "abby_voice_bucket_audio_recovery_artifacts_v1"
)
REVALIDATION_ARTIFACT_MANIFEST_SCHEMA_VERSION = (
    "abby_voice_bucket_audio_revalidation_artifacts_v1"
)
ADMISSION_ARTIFACT_MANIFEST_SCHEMA_VERSION = (
    "abby_voice_bucket_audio_admission_artifacts_v1"
)
NORMALIZED_ARTIFACT_MANIFEST_SCHEMA_VERSION = (
    "abby_voice_bucket_audio_normalized_artifacts_v1"
)
DEFAULT_ACCELERATOR_ARTIFACT_DIR = (
    DEFAULT_CACHE_DIR / "accelerator-artifacts"
)
DEFAULT_NORMALIZED_OUTPUT_DIR = (
    DEFAULT_CACHE_DIR / "normalized-bucket-audio"
)
DEFAULT_REVALIDATION_OUTPUT_DIR = (
    DEFAULT_CACHE_DIR / "revalidation-plans"
)
DEFAULT_ADMISSION_OUTPUT_DIR = DEFAULT_CACHE_DIR / "admission-runs"
DEFAULT_VOICE_QUEUE_PATH = DEFAULT_CACHE_DIR / "voice-jobs.duckdb"


def _json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".partial",
        dir=path.parent,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.chmod(0o644)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _write_new_file(path: Path, content: bytes) -> None:
    """Write and sync one new staging file without replacement semantics."""

    with path.open("xb") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
    path.chmod(0o644)


def _sync_directory(path: Path) -> None:
    """Best-effort fsync for a directory containing newly published entries."""

    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    descriptor = os.open(path, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _artifact_manifest_bytes(
    *,
    plan_id: str,
    artifacts: Mapping[str, bytes],
) -> bytes:
    return _json_bytes(
        {
            "schema_version": PLAN_ARTIFACT_MANIFEST_SCHEMA_VERSION,
            "plan_id": plan_id,
            "files": {
                name: {
                    "byte_length": len(content),
                    "sha256": sha256(content).hexdigest(),
                }
                for name, content in sorted(artifacts.items())
            },
        }
    )


def _assert_immutable_bundle_matches(
    *,
    plan_dir: Path,
    artifacts: Mapping[str, bytes],
    manifest_bytes: bytes,
) -> None:
    """Accept an existing publication only when every byte is identical."""

    expected = {
        **artifacts,
        PLAN_ARTIFACT_MANIFEST_NAME: manifest_bytes,
    }
    if not plan_dir.is_dir() or plan_dir.is_symlink():
        raise ValueError(
            f"immutable plan destination is not a directory: {plan_dir}"
        )
    actual_names = {item.name for item in plan_dir.iterdir()}
    expected_names = set(expected)
    if actual_names != expected_names:
        raise ValueError(
            "immutable plan artifact set mismatch for "
            f"{plan_dir.name}: expected {sorted(expected_names)!r}, "
            f"received {sorted(actual_names)!r}"
        )
    for name, expected_bytes in sorted(expected.items()):
        path = plan_dir / name
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"immutable plan artifact is not a regular file: {path}")
        if path.read_bytes() != expected_bytes:
            raise ValueError(f"immutable plan artifact mismatch: {path}")


def _publish_immutable_bundle(
    *,
    root: Path,
    plan_id: str,
    artifacts: Mapping[str, bytes],
    manifest_bytes: bytes,
) -> tuple[Path, bool]:
    """Publish a complete plan directory by one rename, never replacing it."""

    if Path(plan_id).name != plan_id or plan_id in {".", ".."}:
        raise ValueError("plan_id is not safe for use as an artifact directory")
    root.mkdir(parents=True, exist_ok=True)
    plan_dir = root / plan_id
    if plan_dir.exists() or plan_dir.is_symlink():
        _assert_immutable_bundle_matches(
            plan_dir=plan_dir,
            artifacts=artifacts,
            manifest_bytes=manifest_bytes,
        )
        return plan_dir, False

    staging = Path(
        tempfile.mkdtemp(
            prefix=f".{sha256(plan_id.encode()).hexdigest()[:16]}.",
            suffix=".partial",
            dir=root,
        )
    )
    try:
        for name, content in sorted(artifacts.items()):
            _write_new_file(staging / name, content)
        # The checksum manifest is deliberately durable only after every file it
        # authenticates.  Readers never see staging, and the final rename exposes
        # the complete bundle as one directory entry.
        _write_new_file(staging / PLAN_ARTIFACT_MANIFEST_NAME, manifest_bytes)
        _sync_directory(staging)
        try:
            staging.rename(plan_dir)
        except OSError:
            # A concurrent identical publisher may have won the rename.  It is
            # idempotent only if its complete immutable bundle is byte-identical.
            if not plan_dir.exists() and not plan_dir.is_symlink():
                raise
            _assert_immutable_bundle_matches(
                plan_dir=plan_dir,
                artifacts=artifacts,
                manifest_bytes=manifest_bytes,
            )
            return plan_dir, False
        _sync_directory(root)
        return plan_dir, True
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def _load_source(
    path: Path,
    *,
    expected_sha256: str,
) -> tuple[Mapping[str, Any], bytes, str]:
    source_path = path.expanduser().resolve()
    payload_bytes = source_path.read_bytes()
    digest = sha256(payload_bytes).hexdigest()
    if digest != expected_sha256:
        raise ValueError(
            "source manifest SHA-256 mismatch: "
            f"expected {expected_sha256}, received {digest}"
        )
    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"source manifest must be UTF-8 JSON: {exc}") from exc
    if not isinstance(payload, Mapping):
        raise ValueError("source manifest root must be an object")
    return payload, payload_bytes, digest


def discover_stable_listing(
    *,
    store: HuggingFaceBucketStore,
    prefix: str,
    passes: int = DEFAULT_STABLE_DISCOVERY_PASSES,
) -> HuggingFaceBucketListing:
    """Require repeated identical views before treating absences as missing."""

    if isinstance(passes, bool) or not isinstance(passes, int) or passes < 2:
        raise ValueError("stable discovery requires at least two passes")
    first = store.discover(prefix=prefix)
    expected = first.canonical_bytes()
    for attempt in range(2, passes + 1):
        current = store.discover(prefix=prefix)
        if current.canonical_bytes() != expected:
            raise ValueError(
                "bucket discovery was not stable across passes "
                f"1 and {attempt}; retry planning against a quiescent view"
            )
    return first


def build_recovery_plan(
    *,
    source_manifest: Mapping[str, Any],
    source_sha256: str,
    listing: HuggingFaceBucketListing,
    source_uri: str,
    locale: str = "en-US",
    license_id: str = "MIT",
    consent_status: str = "not_required",
    allowed_run_ids: tuple[str, ...] = (),
) -> tuple[NormalizationResult, AbbyVoiceBucketAudioPlan]:
    """Build the exact recovery plan from already-read, injected inputs."""

    normalization = normalize_manifest(
        source_manifest,
        source_uri=source_uri,
        source_sha256=source_sha256,
        config=NormalizationConfig(
            locale=locale,
            license_id=license_id,
            consent_status=consent_status,
            require_audio=False,
            require_grounding_for_claims=True,
        ),
    )
    plan = plan_abby_voice_bucket_audio(
        source_manifest=source_manifest,
        accepted_responses=normalization.responses,
        discovered_objects=listing.objects,
        quarantined_sources=normalization.quarantine,
        source_uri=source_uri,
        default_locale=locale,
        bucket_id=listing.bucket_id,
        listing_sha256=listing.listing_sha256,
        allowed_run_ids=allowed_run_ids,
    )
    return normalization, plan


def enforce_pinned_production_coverage(
    *,
    source_sha256: str,
    plan: AbbyVoiceBucketAudioPlan,
    allowed_run_ids: tuple[str, ...],
) -> None:
    """Fail closed when the known production corpus unexpectedly loses audio."""

    if (
        source_sha256 != DEFAULT_SOURCE_SHA256
        or plan.bucket_id != DEFAULT_BUCKET_ID
        or tuple(plan.allowed_run_ids)
        != tuple(sorted(DEFAULT_ALLOWED_RUN_IDS))
    ):
        return
    if plan.accepted_response_count != PINNED_ACCEPTED_RESPONSE_COUNT:
        raise ValueError(
            "pinned source accepted-response coverage changed: "
            f"expected {PINNED_ACCEPTED_RESPONSE_COUNT}, "
            f"received {plan.accepted_response_count}"
        )
    if len(plan.selections) < PINNED_MIN_SELECTED_AUDIO_COUNT:
        raise ValueError(
            "approved production audio coverage regressed: "
            f"expected at least {PINNED_MIN_SELECTED_AUDIO_COUNT} selected rows, "
            f"received {len(plan.selections)}"
        )
    if len(plan.missing_response_ids) > PINNED_MAX_MISSING_AUDIO_COUNT:
        raise ValueError(
            "approved production missing-audio coverage regressed: "
            f"expected at most {PINNED_MAX_MISSING_AUDIO_COUNT} missing rows, "
            f"received {len(plan.missing_response_ids)}"
        )
    if plan.unmapped_response_ids:
        raise ValueError(
            "pinned production source has unmapped accepted responses: "
            f"{len(plan.unmapped_response_ids)}"
        )


def write_plan_artifacts(
    *,
    output_dir: Path,
    source_sha256: str,
    listing: HuggingFaceBucketListing,
    normalization: NormalizationResult,
    plan: AbbyVoiceBucketAudioPlan,
    inventory: AbbyVoiceBucketAudioInventory | None = None,
    update_latest: bool = True,
) -> dict[str, Any]:
    """Transactionally publish one immutable, content-addressed plan bundle."""

    if plan.bucket_id != listing.bucket_id:
        raise ValueError("plan bucket_id does not match the discovered listing")
    if plan.listing_sha256 != listing.listing_sha256:
        raise ValueError("plan listing SHA-256 does not match the discovered listing")
    if inventory is None:
        inventory = build_bucket_audio_inventory(
            listing.objects,
            bucket_id=listing.bucket_id,
            listing_sha256=listing.listing_sha256,
        )
    if (
        inventory.bucket_id != listing.bucket_id
        or inventory.listing_sha256 != listing.listing_sha256
    ):
        raise ValueError("inventory does not bind the discovered listing")
    selected_bytes = sum(item.selected.size_bytes for item in plan.selections)
    normalized = normalize_bucket_audio_entries(
        inventory=inventory,
        plan=plan,
        plan_id=plan.plan_id,
    )
    summary = {
        **plan.summary(),
        "estimated_selected_bytes": selected_bytes,
        "inventory": inventory.summary(),
        "normalized_bucket_audio": normalized.summary(),
        "normalization": normalization.quality_summary(),
        "plan_id": plan.plan_id,
        "source_sha256": source_sha256,
        "stage": "planned_unverified",
    }
    artifacts = {
        "bucket-audio-inventory.json": inventory.canonical_bytes() + b"\n",
        "bucket-audio-inventory.jsonl": inventory.to_jsonl_bytes(),
        "bucket-audio-normalized.json": normalized.canonical_bytes() + b"\n",
        "bucket-audio-normalized.jsonl": normalized.to_jsonl_bytes(),
        "bucket-listing.json": listing.canonical_bytes() + b"\n",
        "recovery-plan.json": plan.canonical_bytes() + b"\n",
        "recovery-plan-summary.json": _json_bytes(summary),
    }
    root = output_dir.expanduser().resolve()
    manifest_bytes = _artifact_manifest_bytes(
        plan_id=plan.plan_id,
        artifacts=artifacts,
    )
    plan_dir, published = _publish_immutable_bundle(
        root=root,
        plan_id=plan.plan_id,
        artifacts=artifacts,
        manifest_bytes=manifest_bytes,
    )
    manifest_sha256 = sha256(manifest_bytes).hexdigest()
    latest_pointer: Path | None = None
    if update_latest:
        latest_pointer = root / LATEST_PLAN_POINTER_NAME
        _atomic_write(
            latest_pointer,
            _json_bytes(
                {
                    "schema_version": LATEST_PLAN_POINTER_SCHEMA_VERSION,
                    "plan_id": plan.plan_id,
                    "artifact_dir": plan.plan_id,
                    "manifest": (
                        f"{plan.plan_id}/{PLAN_ARTIFACT_MANIFEST_NAME}"
                    ),
                    "manifest_sha256": manifest_sha256,
                }
            ),
        )
    return {
        **summary,
        "artifact_root": str(root),
        "output_dir": str(plan_dir),
        "published": published,
        "idempotent": not published,
        "checksum_manifest": {
            "path": str(plan_dir / PLAN_ARTIFACT_MANIFEST_NAME),
            "sha256": manifest_sha256,
        },
        "files": json.loads(manifest_bytes)["files"],
        "latest_pointer": str(latest_pointer) if latest_pointer else None,
    }


def load_plan_artifacts(
    plan_dir: Path,
) -> tuple[HuggingFaceBucketListing, AbbyVoiceBucketAudioPlan]:
    """Verify and load one immutable plan bundle without trusting its pointer."""

    raw_dir = plan_dir.expanduser()
    if raw_dir.is_symlink():
        raise ValueError("plan artifact directory must not be a symlink")
    resolved = raw_dir.resolve()
    if not resolved.is_dir():
        raise ValueError(f"plan artifact directory does not exist: {resolved}")
    manifest_path = resolved / PLAN_ARTIFACT_MANIFEST_NAME
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise ValueError("plan artifact checksum manifest is missing or unsafe")
    manifest_bytes = manifest_path.read_bytes()
    try:
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"plan artifact checksum manifest is invalid: {exc}") from exc
    if (
        not isinstance(manifest, Mapping)
        or set(manifest) != {"files", "plan_id", "schema_version"}
        or manifest.get("schema_version")
        != PLAN_ARTIFACT_MANIFEST_SCHEMA_VERSION
        or _json_bytes(manifest) != manifest_bytes
    ):
        raise ValueError("plan artifact checksum manifest is not canonical")
    raw_files = manifest["files"]
    # Accept plan bundles with progressive artifact sets.
    allowed_file_sets = {
        frozenset(
            {
                "bucket-audio-inventory.json",
                "bucket-audio-inventory.jsonl",
                "bucket-audio-normalized.json",
                "bucket-audio-normalized.jsonl",
                "bucket-listing.json",
                "recovery-plan.json",
                "recovery-plan-summary.json",
            }
        ),
        frozenset(
            {
                "bucket-audio-inventory.json",
                "bucket-audio-inventory.jsonl",
                "bucket-listing.json",
                "recovery-plan.json",
                "recovery-plan-summary.json",
            }
        ),
        frozenset(
            {
                "bucket-listing.json",
                "recovery-plan.json",
                "recovery-plan-summary.json",
            }
        ),
    }
    if not isinstance(raw_files, Mapping) or frozenset(raw_files) not in allowed_file_sets:
        raise ValueError("plan artifact checksum manifest has an invalid file set")
    expected_names = set(raw_files)
    if {item.name for item in resolved.iterdir()} != {
        *expected_names,
        PLAN_ARTIFACT_MANIFEST_NAME,
    }:
        raise ValueError("plan artifact directory has an unexpected file set")
    payloads: dict[str, bytes] = {}
    for name in sorted(expected_names):
        metadata = raw_files[name]
        path = resolved / name
        if (
            not isinstance(metadata, Mapping)
            or set(metadata) != {"byte_length", "sha256"}
            or not isinstance(metadata["byte_length"], int)
            or isinstance(metadata["byte_length"], bool)
            or metadata["byte_length"] < 0
            or not isinstance(metadata["sha256"], str)
            or not path.is_file()
            or path.is_symlink()
        ):
            raise ValueError(f"plan artifact metadata is invalid: {name}")
        content = path.read_bytes()
        if (
            len(content) != metadata["byte_length"]
            or sha256(content).hexdigest() != metadata["sha256"]
        ):
            raise ValueError(f"plan artifact checksum mismatch: {name}")
        payloads[name] = content

    listing = HuggingFaceBucketListing.from_json(payloads["bucket-listing.json"])
    plan = AbbyVoiceBucketAudioPlan.from_json(payloads["recovery-plan.json"])
    if (
        plan.plan_id != manifest["plan_id"]
        or resolved.name != plan.plan_id
        or plan.bucket_id != listing.bucket_id
        or plan.listing_sha256 != listing.listing_sha256
    ):
        raise ValueError("plan artifact bundle bindings do not match")
    return listing, plan


def build_ffprobe_decode_probe(
    *,
    executable: str = "ffprobe",
    decoder_executable: str = "ffmpeg",
    runner: Any = subprocess.run,
    temp_dir: Path | None = None,
):
    """Return a probe that records metadata and forces a full frame decode."""

    resolved_executable = shutil.which(executable)
    if resolved_executable is None:
        raise ValueError(f"ffprobe executable was not found: {executable}")
    version_result = runner(
        [resolved_executable, "-version"],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    version_lines = str(version_result.stdout or "").splitlines()
    if version_result.returncode != 0 or not version_lines:
        raise ValueError("ffprobe version check failed")
    version = version_lines[0].strip()
    if not version:
        raise ValueError("ffprobe version output was empty")
    resolved_decoder = shutil.which(decoder_executable)
    if resolved_decoder is None:
        raise ValueError(f"ffmpeg executable was not found: {decoder_executable}")
    decoder_version_result = runner(
        [resolved_decoder, "-version"],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    decoder_version_lines = str(
        decoder_version_result.stdout or ""
    ).splitlines()
    if decoder_version_result.returncode != 0 or not decoder_version_lines:
        raise ValueError("ffmpeg version check failed")
    decoder_version = decoder_version_lines[0].strip()
    if not decoder_version:
        raise ValueError("ffmpeg version output was empty")

    def probe(payload: bytes, media_type: str) -> DecodeProbeEvidence:
        if not isinstance(payload, bytes) or not payload:
            raise ValueError("ffprobe payload must be non-empty bytes")
        directory = temp_dir.expanduser().resolve() if temp_dir else None
        if directory is not None:
            directory.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".abby-voice-ffprobe.",
            suffix=".audio",
            dir=directory,
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            completed = runner(
                [
                    resolved_executable,
                    "-v",
                    "error",
                    "-show_entries",
                    (
                        "stream=codec_type,codec_name,sample_rate,channels,duration:"
                        "format=duration"
                    ),
                    "-of",
                    "json",
                    str(temporary),
                ],
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
            if completed.returncode != 0:
                detail = " ".join(str(completed.stderr or "").split())[:256]
                raise ValueError(f"ffprobe rejected audio: {detail or 'unknown error'}")
            try:
                decoded = json.loads(completed.stdout)
            except (TypeError, json.JSONDecodeError) as exc:
                raise ValueError("ffprobe returned invalid JSON") from exc
            if not isinstance(decoded, Mapping):
                raise ValueError("ffprobe result must be a JSON object")
            streams = decoded.get("streams")
            if not isinstance(streams, list):
                raise ValueError("ffprobe did not return stream evidence")
            audio_streams = [
                item
                for item in streams
                if isinstance(item, Mapping) and item.get("codec_type") == "audio"
            ]
            if not audio_streams:
                raise ValueError("ffprobe found no audio stream")
            try:
                sample_rates = sorted(
                    {
                        int(item["sample_rate"])
                        for item in audio_streams
                        if item.get("sample_rate") not in (None, "", "N/A")
                    }
                )
                channels = sorted(
                    {
                        int(item["channels"])
                        for item in audio_streams
                        if item.get("channels") not in (None, "", "N/A")
                    }
                )
                durations = [
                    float(item["duration"])
                    for item in audio_streams
                    if item.get("duration") not in (None, "", "N/A")
                ]
                format_row = decoded.get("format")
                if isinstance(format_row, Mapping) and format_row.get(
                    "duration"
                ) not in (None, "", "N/A"):
                    durations.append(float(format_row["duration"]))
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError("ffprobe returned invalid audio properties") from exc
            if (
                not sample_rates
                or min(sample_rates) <= 0
                or not channels
                or min(channels) <= 0
                or not durations
                or max(durations) <= 0
            ):
                raise ValueError("ffprobe audio properties are incomplete")
            codecs = sorted(
                {
                    str(item["codec_name"])
                    for item in audio_streams
                    if item.get("codec_name") not in (None, "")
                }
            )
            decoded_result = runner(
                [
                    resolved_decoder,
                    "-nostdin",
                    "-hide_banner",
                    "-v",
                    "error",
                    "-xerror",
                    "-i",
                    str(temporary),
                    "-map",
                    "0:a:0",
                    "-vn",
                    "-sn",
                    "-dn",
                    "-f",
                    "null",
                    "-",
                ],
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
            if decoded_result.returncode != 0:
                detail = " ".join(
                    str(decoded_result.stderr or "").split()
                )[:256]
                raise ValueError(
                    "ffmpeg full decode rejected audio: "
                    f"{detail or 'unknown error'}"
                )
            return DecodeProbeEvidence(
                probe_name="ffprobe+ffmpeg",
                probe_version=f"{version} | {decoder_version}",
                passed=True,
                details={
                    "audio_stream_count": len(audio_streams),
                    "channels": channels,
                    "codecs": codecs,
                    "full_frame_decode": True,
                    "decoder_version": decoder_version,
                    "duration_seconds": max(durations),
                    "media_type": media_type,
                    "sample_rates_hz": sample_rates,
                },
            )
        finally:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass

    return probe


def _recovery_artifact_manifest_bytes(
    *,
    recovery: AbbyVoiceBucketAudioRecovery,
    artifacts: Mapping[str, bytes],
) -> bytes:
    return _json_bytes(
        {
            "schema_version": RECOVERY_ARTIFACT_MANIFEST_SCHEMA_VERSION,
            "plan_id": recovery.plan_id,
            "recovery_id": recovery.recovery_id,
            "files": {
                name: {
                    "byte_length": len(content),
                    "sha256": sha256(content).hexdigest(),
                }
                for name, content in sorted(artifacts.items())
            },
        }
    )


def write_recovery_artifacts(
    *,
    output_dir: Path,
    recovery: AbbyVoiceBucketAudioRecovery,
) -> dict[str, Any]:
    """Publish one immutable staging bundle; never authorize a final link."""

    candidate_bytes = b"".join(
        json.dumps(
            item.to_dict(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        + b"\n"
        for item in recovery.candidates
    )
    failure_bytes = b"".join(
        item.canonical_bytes() + b"\n" for item in recovery.failures
    )
    summary = {
        **recovery.summary(),
        "recovery_id": recovery.recovery_id,
        "stage": "staged_pending_asr_and_critical_slot_validation",
    }
    artifacts = {
        "failure-dispositions.jsonl": failure_bytes,
        "recovery.json": recovery.canonical_bytes() + b"\n",
        "recovery-summary.json": _json_bytes(summary),
        "staging-candidates.pending-asr.jsonl": candidate_bytes,
        "verified-inventory.json": recovery.inventory.canonical_bytes() + b"\n",
    }
    root = output_dir.expanduser().resolve()
    manifest_bytes = _recovery_artifact_manifest_bytes(
        recovery=recovery,
        artifacts=artifacts,
    )
    recovery_dir, published = _publish_immutable_bundle(
        root=root,
        plan_id=recovery.recovery_id,
        artifacts=artifacts,
        manifest_bytes=manifest_bytes,
    )
    return {
        **summary,
        "artifact_root": str(root),
        "output_dir": str(recovery_dir),
        "published": published,
        "idempotent": not published,
        "checksum_manifest": {
            "path": str(recovery_dir / PLAN_ARTIFACT_MANIFEST_NAME),
            "sha256": sha256(manifest_bytes).hexdigest(),
        },
    }


def load_recovery_artifacts(
    recovery_dir: Path,
) -> AbbyVoiceBucketAudioRecovery:
    """Verify and re-derive one immutable pending-recovery bundle."""

    raw_dir = recovery_dir.expanduser()
    if raw_dir.is_symlink():
        raise ValueError("recovery artifact directory must not be a symlink")
    resolved = raw_dir.resolve()
    if not resolved.is_dir():
        raise ValueError(f"recovery artifact directory does not exist: {resolved}")
    manifest_path = resolved / PLAN_ARTIFACT_MANIFEST_NAME
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise ValueError("recovery artifact checksum manifest is missing or unsafe")
    manifest_bytes = manifest_path.read_bytes()
    try:
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(
            f"recovery artifact checksum manifest is invalid: {exc}"
        ) from exc
    expected_names = {
        "failure-dispositions.jsonl",
        "recovery.json",
        "recovery-summary.json",
        "staging-candidates.pending-asr.jsonl",
        "verified-inventory.json",
    }
    if (
        not isinstance(manifest, Mapping)
        or set(manifest)
        != {"files", "plan_id", "recovery_id", "schema_version"}
        or manifest.get("schema_version")
        != RECOVERY_ARTIFACT_MANIFEST_SCHEMA_VERSION
        or _json_bytes(manifest) != manifest_bytes
        or not isinstance(manifest.get("files"), Mapping)
        or set(manifest["files"]) != expected_names
    ):
        raise ValueError("recovery artifact checksum manifest is not canonical")
    if {item.name for item in resolved.iterdir()} != {
        *expected_names,
        PLAN_ARTIFACT_MANIFEST_NAME,
    }:
        raise ValueError("recovery artifact directory has an unexpected file set")

    payloads: dict[str, bytes] = {}
    for name in sorted(expected_names):
        metadata = manifest["files"][name]
        path = resolved / name
        if (
            not isinstance(metadata, Mapping)
            or set(metadata) != {"byte_length", "sha256"}
            or isinstance(metadata.get("byte_length"), bool)
            or not isinstance(metadata.get("byte_length"), int)
            or metadata["byte_length"] < 0
            or not isinstance(metadata.get("sha256"), str)
            or not path.is_file()
            or path.is_symlink()
        ):
            raise ValueError(f"recovery artifact metadata is invalid: {name}")
        content = path.read_bytes()
        if (
            len(content) != metadata["byte_length"]
            or sha256(content).hexdigest() != metadata["sha256"]
        ):
            raise ValueError(f"recovery artifact checksum mismatch: {name}")
        payloads[name] = content

    recovery = AbbyVoiceBucketAudioRecovery.from_json(payloads["recovery.json"])
    expected_candidate_bytes = b"".join(
        json.dumps(
            item.to_dict(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        + b"\n"
        for item in recovery.candidates
    )
    expected_failure_bytes = b"".join(
        item.canonical_bytes() + b"\n" for item in recovery.failures
    )
    expected_summary_bytes = _json_bytes(
        {
            **recovery.summary(),
            "recovery_id": recovery.recovery_id,
            "stage": "staged_pending_asr_and_critical_slot_validation",
        }
    )
    expected_inventory_bytes = recovery.inventory.canonical_bytes() + b"\n"
    if (
        manifest["plan_id"] != recovery.plan_id
        or manifest["recovery_id"] != recovery.recovery_id
        or resolved.name != recovery.recovery_id
        or payloads["staging-candidates.pending-asr.jsonl"]
        != expected_candidate_bytes
        or payloads["failure-dispositions.jsonl"] != expected_failure_bytes
        or payloads["recovery-summary.json"] != expected_summary_bytes
        or payloads["verified-inventory.json"] != expected_inventory_bytes
    ):
        raise ValueError("recovery artifact bundle bindings do not match")
    return recovery


def _revalidation_artifact_manifest_bytes(
    *,
    execution_plan_id: str,
    revalidation_plan_id: str,
    recovery_id: str,
    workset_id: str,
    artifacts: Mapping[str, bytes],
) -> bytes:
    return _json_bytes(
        {
            "schema_version": REVALIDATION_ARTIFACT_MANIFEST_SCHEMA_VERSION,
            "execution_plan_id": execution_plan_id,
            "revalidation_plan_id": revalidation_plan_id,
            "recovery_id": recovery_id,
            "workset_id": workset_id,
            "files": {
                name: {
                    "byte_length": len(content),
                    "sha256": sha256(content).hexdigest(),
                }
                for name, content in sorted(artifacts.items())
            },
        }
    )


def write_revalidation_artifacts(
    *,
    output_dir: Path,
    revalidation_plan: Any,
    jobs: tuple[Any, ...],
) -> dict[str, Any]:
    """Publish an immutable ASR/validation plan without queue side effects."""

    bindings = tuple(revalidation_plan.bindings)
    execution_identity = {
        "jobs": [job.to_payload() for job in jobs],
        "revalidation_plan_id": revalidation_plan.revalidation_plan_id,
        "workset_id": revalidation_plan.workset.workset_id,
    }
    execution_plan_id = (
        "abby-voice-bucket-audio-execution:sha256:"
        + sha256(
            json.dumps(
                execution_identity,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        ).hexdigest()
    )
    job_bytes = b"".join(
        json.dumps(
            job.to_payload(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        + b"\n"
        for job in jobs
    )
    binding_bytes = b"".join(
        json.dumps(
            item.to_dict(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        + b"\n"
        for item in bindings
    )
    bound_count = sum(
        item.critical_fact_classification.value == "critical_facts_bound"
        for item in bindings
    )
    summary = {
        "asr_job_count": sum(job.task_type == "voice.asr" for job in jobs),
        "audio_validation_job_count": sum(
            job.task_type == "voice.audio-validate" for job in jobs
        ),
        "critical_facts_bound_count": bound_count,
        "execution_plan_id": execution_plan_id,
        "no_critical_facts_detected_count": len(bindings) - bound_count,
        "policy_id": revalidation_plan.policy.identity,
        "publishable": False,
        "recovery_id": revalidation_plan.recovery_id,
        "revalidation_plan_id": revalidation_plan.revalidation_plan_id,
        "stage": "planned_pending_asr_and_audio_validation_execution",
        "submitted": False,
        "tts_job_count": sum(job.task_type == "voice.tts" for job in jobs),
        "verified_record_count": len(bindings),
        "workset_id": revalidation_plan.workset.workset_id,
    }
    artifacts = {
        "audio-workset.json": revalidation_plan.workset.canonical_bytes() + b"\n",
        "critical-slot-bindings.jsonl": binding_bytes,
        "quality-policy.json": _json_bytes(revalidation_plan.policy.to_dict()),
        "revalidation-plan.json": revalidation_plan.canonical_bytes() + b"\n",
        "revalidation-summary.json": _json_bytes(summary),
        "voice-jobs.jsonl": job_bytes,
    }
    manifest_bytes = _revalidation_artifact_manifest_bytes(
        execution_plan_id=execution_plan_id,
        revalidation_plan_id=revalidation_plan.revalidation_plan_id,
        recovery_id=revalidation_plan.recovery_id,
        workset_id=revalidation_plan.workset.workset_id,
        artifacts=artifacts,
    )
    root = output_dir.expanduser().resolve()
    plan_dir, published = _publish_immutable_bundle(
        root=root,
        plan_id=execution_plan_id,
        artifacts=artifacts,
        manifest_bytes=manifest_bytes,
    )
    return {
        **summary,
        "artifact_root": str(root),
        "output_dir": str(plan_dir),
        "published": published,
        "idempotent": not published,
        "checksum_manifest": {
            "path": str(plan_dir / PLAN_ARTIFACT_MANIFEST_NAME),
            "sha256": sha256(manifest_bytes).hexdigest(),
        },
    }


def write_admission_artifacts(
    *,
    output_dir: Path,
    recovery_id: str,
    revalidation_plan_id: str,
    admission: Any,
) -> dict[str, Any]:
    """Publish immutable link/quarantine evidence; perform no remote write."""

    def jsonl_bytes(values: Any) -> bytes:
        return b"".join(
            json.dumps(
                item.to_dict(),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
            + b"\n"
            for item in values
        )

    linked_bytes = jsonl_bytes(admission.linked_audio)
    provenance_bytes = jsonl_bytes(admission.provenance)
    disposition_bytes = jsonl_bytes(admission.dispositions)
    quality_document = admission.quality_report_document()
    summary = {
        "linked_audio_count": admission.promoted_count,
        "policy_id": admission.policy_identity,
        "publishable": False,
        "quarantined_audio_count": admission.quarantined_count,
        "reconciliation_id": admission.reconciliation_id,
        "recovery_id": recovery_id,
        "revalidation_plan_id": revalidation_plan_id,
        "stage": "admitted_pending_dataset_merge_and_release_validation",
    }
    artifacts = {
        "admission-summary.json": _json_bytes(summary),
        "audio-reconciliation.json": admission.canonical_bytes() + b"\n",
        "dispositions.jsonl": disposition_bytes,
        "linked-audio.jsonl": linked_bytes,
        "provenance.jsonl": provenance_bytes,
        "quality-report.json": _json_bytes(quality_document),
    }
    manifest_bytes = _json_bytes(
        {
            "schema_version": ADMISSION_ARTIFACT_MANIFEST_SCHEMA_VERSION,
            "reconciliation_id": admission.reconciliation_id,
            "recovery_id": recovery_id,
            "revalidation_plan_id": revalidation_plan_id,
            "files": {
                name: {
                    "byte_length": len(content),
                    "sha256": sha256(content).hexdigest(),
                }
                for name, content in sorted(artifacts.items())
            },
        }
    )
    root = output_dir.expanduser().resolve()
    admission_dir, published = _publish_immutable_bundle(
        root=root,
        plan_id=admission.reconciliation_id,
        artifacts=artifacts,
        manifest_bytes=manifest_bytes,
    )
    return {
        **summary,
        "artifact_root": str(root),
        "output_dir": str(admission_dir),
        "published": published,
        "idempotent": not published,
        "checksum_manifest": {
            "path": str(admission_dir / PLAN_ARTIFACT_MANIFEST_NAME),
            "sha256": sha256(manifest_bytes).hexdigest(),
        },
    }


def load_admission_artifacts(
    admission_dir: Path,
) -> tuple[AudioReconciliationResult, dict[str, Any], str]:
    """Verify and re-derive one immutable admitted-audio bundle."""

    raw_dir = admission_dir.expanduser()
    if raw_dir.is_symlink():
        raise ValueError("admission artifact directory must not be a symlink")
    resolved = raw_dir.resolve()
    if not resolved.is_dir():
        raise ValueError(
            f"admission artifact directory does not exist: {resolved}"
        )
    manifest_path = resolved / PLAN_ARTIFACT_MANIFEST_NAME
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise ValueError("admission artifact checksum manifest is missing or unsafe")
    manifest_bytes = manifest_path.read_bytes()
    manifest_sha256 = sha256(manifest_bytes).hexdigest()
    try:
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(
            f"admission artifact checksum manifest is invalid: {exc}"
        ) from exc
    expected_names = {
        "admission-summary.json",
        "audio-reconciliation.json",
        "dispositions.jsonl",
        "linked-audio.jsonl",
        "provenance.jsonl",
        "quality-report.json",
    }
    if (
        not isinstance(manifest, Mapping)
        or set(manifest)
        != {
            "files",
            "reconciliation_id",
            "recovery_id",
            "revalidation_plan_id",
            "schema_version",
        }
        or manifest.get("schema_version")
        != ADMISSION_ARTIFACT_MANIFEST_SCHEMA_VERSION
        or _json_bytes(manifest) != manifest_bytes
        or not isinstance(manifest.get("files"), Mapping)
        or set(manifest["files"]) != expected_names
        or not all(
            isinstance(manifest.get(name), str)
            and bool(manifest[name])
            and manifest[name].strip() == manifest[name]
            for name in (
                "reconciliation_id",
                "recovery_id",
                "revalidation_plan_id",
            )
        )
    ):
        raise ValueError("admission artifact checksum manifest is not canonical")
    if {item.name for item in resolved.iterdir()} != {
        *expected_names,
        PLAN_ARTIFACT_MANIFEST_NAME,
    }:
        raise ValueError("admission artifact directory has an unexpected file set")

    payloads: dict[str, bytes] = {}
    for name in sorted(expected_names):
        metadata = manifest["files"][name]
        path = resolved / name
        digest = metadata.get("sha256") if isinstance(metadata, Mapping) else None
        if (
            not isinstance(metadata, Mapping)
            or set(metadata) != {"byte_length", "sha256"}
            or isinstance(metadata.get("byte_length"), bool)
            or not isinstance(metadata.get("byte_length"), int)
            or metadata["byte_length"] < 0
            or not isinstance(digest, str)
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
            or not path.is_file()
            or path.is_symlink()
        ):
            raise ValueError(f"admission artifact metadata is invalid: {name}")
        content = path.read_bytes()
        if (
            len(content) != metadata["byte_length"]
            or sha256(content).hexdigest() != digest
        ):
            raise ValueError(f"admission artifact checksum mismatch: {name}")
        payloads[name] = content

    admission = AudioReconciliationResult.from_json(
        payloads["audio-reconciliation.json"]
    )

    def jsonl_bytes(values: Any) -> bytes:
        return b"".join(
            json.dumps(
                item.to_dict(),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
            + b"\n"
            for item in values
        )

    expected_summary = {
        "linked_audio_count": admission.promoted_count,
        "policy_id": admission.policy_identity,
        "publishable": False,
        "quarantined_audio_count": admission.quarantined_count,
        "reconciliation_id": admission.reconciliation_id,
        "recovery_id": manifest["recovery_id"],
        "revalidation_plan_id": manifest["revalidation_plan_id"],
        "stage": "admitted_pending_dataset_merge_and_release_validation",
    }
    expected_payloads = {
        "admission-summary.json": _json_bytes(expected_summary),
        "audio-reconciliation.json": admission.canonical_bytes() + b"\n",
        "dispositions.jsonl": jsonl_bytes(admission.dispositions),
        "linked-audio.jsonl": jsonl_bytes(admission.linked_audio),
        "provenance.jsonl": jsonl_bytes(admission.provenance),
        "quality-report.json": _json_bytes(admission.quality_report_document()),
    }
    if (
        manifest["reconciliation_id"] != admission.reconciliation_id
        or resolved.name != admission.reconciliation_id
        or payloads != expected_payloads
    ):
        raise ValueError("admission artifact derived artifacts do not match")
    return admission, dict(manifest), manifest_sha256


def _source_uri(path: Path, digest: str) -> str:
    resolved = path.expanduser().resolve()
    try:
        relative = resolved.relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        relative = resolved.name
    return f"repo://211-AI/{relative}@sha256:{digest}"


def write_normalized_artifacts(
    *,
    output_dir: Path,
    normalized: AbbyVoiceBucketAudioNormalizedBundle,
) -> dict[str, Any]:
    """Publish an immutable full-bucket normalized entry bundle."""

    summary = {
        **normalized.summary(),
        "stage": "normalized_all_bucket_entries",
    }
    artifacts = {
        "bucket-audio-normalized.json": normalized.canonical_bytes() + b"\n",
        "bucket-audio-normalized.jsonl": normalized.to_jsonl_bytes(),
        "normalized-summary.json": _json_bytes(summary),
    }
    manifest_bytes = _json_bytes(
        {
            "schema_version": NORMALIZED_ARTIFACT_MANIFEST_SCHEMA_VERSION,
            "normalized_id": normalized.normalized_id,
            "bucket_id": normalized.bucket_id,
            "listing_sha256": normalized.listing_sha256,
            "plan_id": normalized.plan_id,
            "files": {
                name: {
                    "byte_length": len(content),
                    "sha256": sha256(content).hexdigest(),
                }
                for name, content in sorted(artifacts.items())
            },
        }
    )
    root = output_dir.expanduser().resolve()
    bundle_dir, published = _publish_immutable_bundle(
        root=root,
        plan_id=normalized.normalized_id,
        artifacts=artifacts,
        manifest_bytes=manifest_bytes,
    )
    return {
        **summary,
        "artifact_root": str(root),
        "output_dir": str(bundle_dir),
        "published": published,
        "idempotent": not published,
        "checksum_manifest": {
            "path": str(bundle_dir / PLAN_ARTIFACT_MANIFEST_NAME),
            "sha256": sha256(manifest_bytes).hexdigest(),
        },
    }


def _normalize_command(args: argparse.Namespace) -> int:
    """Normalize every object from a sealed plan listing under entry schema v1."""

    listing, plan = load_plan_artifacts(args.plan_dir)
    plan_dir = args.plan_dir.expanduser().resolve()
    inventory_path = plan_dir / "bucket-audio-inventory.json"
    if inventory_path.is_file() and not inventory_path.is_symlink():
        inventory = AbbyVoiceBucketAudioInventory.from_dict(
            json.loads(inventory_path.read_text(encoding="utf-8"))
        )
        if (
            inventory.bucket_id != listing.bucket_id
            or inventory.listing_sha256 != listing.listing_sha256
        ):
            raise ValueError("plan inventory does not bind the sealed listing")
    else:
        inventory = build_bucket_audio_inventory(
            listing.objects,
            bucket_id=listing.bucket_id,
            listing_sha256=listing.listing_sha256,
        )
    normalized = normalize_bucket_audio_entries(
        inventory=inventory,
        plan=plan,
        plan_id=plan.plan_id,
    )
    result = write_normalized_artifacts(
        output_dir=args.output_dir,
        normalized=normalized,
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


def _plan_command(args: argparse.Namespace) -> int:
    payload, _source_bytes, source_digest = _load_source(
        args.source,
        expected_sha256=args.expected_source_sha256,
    )
    token = os.environ.get(args.token_env) if args.token_env else None
    client = HuggingFaceBucketHttpClient(
        endpoint=args.endpoint,
        token=token,
        timeout_seconds=args.timeout_seconds,
    )
    store = HuggingFaceBucketStore(args.bucket_id, client=client)
    listing = discover_stable_listing(
        store=store,
        prefix=args.prefix,
        passes=args.discovery_passes,
    )
    inventory = build_bucket_audio_inventory(
        listing.objects,
        bucket_id=listing.bucket_id,
        listing_sha256=listing.listing_sha256,
    )
    if args.allow_unlisted_runs:
        allowed_run_ids: tuple[str, ...] = ()
    elif args.allowed_run_id:
        raw_allowed_run_ids = tuple(args.allowed_run_id)
        if len(raw_allowed_run_ids) != len(set(raw_allowed_run_ids)):
            raise ValueError("approved production run IDs must not contain duplicates")
        allowed_run_ids = raw_allowed_run_ids
    else:
        # Default: every production run present in the listing, so residual
        # phase1/phase4 folders under all abby-full-preprocess-* trees map.
        # Fall back to the historical pin only when discovery returned none.
        discovered_runs = inventory.production_run_ids or discover_production_run_ids(
            listing.objects
        )
        allowed_run_ids = discovered_runs or DEFAULT_ALLOWED_RUN_IDS
        if len(allowed_run_ids) != len(set(allowed_run_ids)):
            raise ValueError("approved production run IDs must not contain duplicates")
    normalization, plan = build_recovery_plan(
        source_manifest=payload,
        source_sha256=source_digest,
        listing=listing,
        source_uri=_source_uri(args.source, source_digest),
        locale=args.locale,
        license_id=args.license_id,
        consent_status=args.consent_status,
        allowed_run_ids=allowed_run_ids,
    )
    if not args.skip_production_coverage_gate:
        enforce_pinned_production_coverage(
            source_sha256=source_digest,
            plan=plan,
            allowed_run_ids=allowed_run_ids,
        )
    result = write_plan_artifacts(
        output_dir=args.output_dir,
        source_sha256=source_digest,
        listing=listing,
        normalization=normalization,
        plan=plan,
        inventory=inventory,
        update_latest=not args.no_update_latest,
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


def _fetch_command(args: argparse.Namespace) -> int:
    _listing, plan = load_plan_artifacts(args.plan_dir)
    limit = None if args.all else args.limit
    if limit is not None and (
        isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0
    ):
        raise ValueError("fetch limit must be a positive integer")
    cache_dir = args.cache_dir.expanduser().resolve()
    plan_key = sha256(plan.plan_id.encode("utf-8")).hexdigest()
    ledger_path = (
        args.ledger_path.expanduser().resolve()
        if args.ledger_path is not None
        else cache_dir / "ledgers" / f"{plan_key}.verified.jsonl"
    )
    token = os.environ.get(args.token_env) if args.token_env else None
    client = HuggingFaceBucketHttpClient(
        endpoint=args.endpoint,
        token=token,
        timeout_seconds=args.timeout_seconds,
    )
    store = HuggingFaceBucketStore(plan.bucket_id, client=client)
    decode_probe = (
        None
        if args.skip_decode_probe
        else build_ffprobe_decode_probe(
            executable=args.ffprobe,
            decoder_executable=args.ffmpeg,
            temp_dir=cache_dir / "probe-tmp",
        )
    )
    recovery = recover_abby_voice_bucket_audio(
        plan=plan,
        store=store,
        cache_dir=cache_dir / "objects",
        ledger_path=ledger_path,
        decode_probe=decode_probe,
        limit=limit,
        checkpoint_interval=args.checkpoint_interval,
        fail_fast=args.fail_fast,
    )
    result = write_recovery_artifacts(
        output_dir=args.output_dir,
        recovery=recovery,
    )
    result["ledger_path"] = str(ledger_path)
    result["decode_probe_required"] = not args.skip_decode_probe
    result["command_status"] = (
        "partial_success" if recovery.failures else "success"
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 3 if recovery.failures and args.fail_on_row_failure else 0


def _schedule_command(args: argparse.Namespace) -> int:
    recovery = load_recovery_artifacts(args.recovery_dir)
    if not recovery.records:
        raise ValueError("recovery bundle has no verified records to schedule")

    accelerate_root = REPO_ROOT / "ipfs_accelerate_py"
    if str(accelerate_root) not in sys.path:
        sys.path.insert(0, str(accelerate_root))
    from ipfs_datasets_py.ml.accelerate_integration.bucket_audio import (
        build_bucket_audio_revalidation_plan,
    )
    from ipfs_datasets_py.ml.accelerate_integration.voice_jobs import (
        VoiceJobBridge,
        VoiceWorksetBridgeConfig,
        jobs_from_voice_workset,
    )

    revalidation_plan = build_bucket_audio_revalidation_plan(
        recovery,
        cache_dir=args.cache_dir,
        artifact_root=args.artifact_root,
        max_artifact_bytes=args.max_artifact_bytes,
    )
    bridge_config = VoiceWorksetBridgeConfig(
        asr_provider=args.asr_provider,
        asr_model_name=args.asr_model,
        asr_provider_version=args.asr_provider_version,
        asr_decoding_settings={},
        asr_retention_policy="result",
        validation_provider="local",
        validation_model_name="abby-audio-validator",
        validation_policy_version=revalidation_plan.policy.policy_version,
        validation_policy=revalidation_plan.policy.to_dict(),
    )
    jobs = jobs_from_voice_workset(
        revalidation_plan.workset,
        config=bridge_config,
    )
    result = write_revalidation_artifacts(
        output_dir=args.output_dir,
        revalidation_plan=revalidation_plan,
        jobs=jobs,
    )
    result["recovery_failure_count"] = len(recovery.failures)
    result["queue_submission"] = {
        "requested": bool(args.submit),
        "submitted_job_count": 0,
    }
    if args.submit:
        bridge = VoiceJobBridge(queue_path=str(args.queue_path.expanduser().resolve()))
        submission = bridge.submit_workset(
            revalidation_plan.workset,
            config=bridge_config,
        )
        result["queue_submission"] = {
            "requested": True,
            "queue_path": str(args.queue_path.expanduser().resolve()),
            "replayed_job_count": sum(item.replayed for item in submission.jobs),
            "submitted_job_count": len(submission.jobs),
            "tasks": [
                {
                    "replayed": item.replayed,
                    "status": item.status,
                    "task_id": item.task_id,
                    "task_type": item.task_type,
                    "work_item_id": item.work_item_id,
                }
                for item in submission.jobs
            ],
        }
        result["submitted"] = True
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


def load_revalidation_artifacts(
    schedule_dir: Path,
) -> tuple[Any, tuple[Any, ...], dict[str, Any], str]:
    """Verify and load one immutable schedule bundle (pinned plan + jobs)."""

    accelerate_root = REPO_ROOT / "ipfs_accelerate_py"
    if str(accelerate_root) not in sys.path:
        sys.path.insert(0, str(accelerate_root))
    from ipfs_accelerate_py.voice_jobs.contracts import voice_job_from_payload
    from ipfs_datasets_py.ml.accelerate_integration.bucket_audio import (
        BucketAudioRevalidationPlan,
    )

    raw_dir = schedule_dir.expanduser()
    if raw_dir.is_symlink():
        raise ValueError("schedule artifact directory must not be a symlink")
    resolved = raw_dir.resolve()
    if not resolved.is_dir():
        raise ValueError(
            f"schedule artifact directory does not exist: {resolved}"
        )
    manifest_path = resolved / PLAN_ARTIFACT_MANIFEST_NAME
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise ValueError("schedule artifact checksum manifest is missing or unsafe")
    manifest_bytes = manifest_path.read_bytes()
    manifest_sha256 = sha256(manifest_bytes).hexdigest()
    try:
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(
            f"schedule artifact checksum manifest is invalid: {exc}"
        ) from exc
    expected_names = {
        "audio-workset.json",
        "critical-slot-bindings.jsonl",
        "quality-policy.json",
        "revalidation-plan.json",
        "revalidation-summary.json",
        "voice-jobs.jsonl",
    }
    if (
        not isinstance(manifest, Mapping)
        or set(manifest)
        != {
            "execution_plan_id",
            "files",
            "recovery_id",
            "revalidation_plan_id",
            "schema_version",
            "workset_id",
        }
        or manifest.get("schema_version")
        != REVALIDATION_ARTIFACT_MANIFEST_SCHEMA_VERSION
        or _json_bytes(manifest) != manifest_bytes
        or not isinstance(manifest.get("files"), Mapping)
        or set(manifest["files"]) != expected_names
    ):
        raise ValueError("schedule artifact checksum manifest is not canonical")
    if {item.name for item in resolved.iterdir()} != {
        *expected_names,
        PLAN_ARTIFACT_MANIFEST_NAME,
    }:
        raise ValueError("schedule artifact directory has an unexpected file set")

    payloads: dict[str, bytes] = {}
    for name in sorted(expected_names):
        metadata = manifest["files"][name]
        path = resolved / name
        if (
            not isinstance(metadata, Mapping)
            or set(metadata) != {"byte_length", "sha256"}
            or not path.is_file()
            or path.is_symlink()
        ):
            raise ValueError(f"schedule artifact {name!r} is missing or unsafe")
        content = path.read_bytes()
        if (
            len(content) != int(metadata["byte_length"])
            or sha256(content).hexdigest() != metadata["sha256"]
        ):
            raise ValueError(f"schedule artifact {name!r} failed checksum verification")
        payloads[name] = content

    revalidation_plan = BucketAudioRevalidationPlan.from_json(
        payloads["revalidation-plan.json"]
    )
    if (
        revalidation_plan.revalidation_plan_id != manifest["revalidation_plan_id"]
        or revalidation_plan.recovery_id != manifest["recovery_id"]
        or revalidation_plan.workset.workset_id != manifest["workset_id"]
        or resolved.name != manifest["execution_plan_id"]
    ):
        raise ValueError("schedule artifact bundle bindings do not match")

    jobs: list[Any] = []
    for line in payloads["voice-jobs.jsonl"].splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"voice-jobs.jsonl is invalid: {exc}") from exc
        if not isinstance(payload, Mapping):
            raise ValueError("voice-jobs.jsonl rows must be mappings")
        jobs.append(voice_job_from_payload(payload))
    jobs_tuple = tuple(jobs)
    if not jobs_tuple:
        raise ValueError("schedule bundle has no pinned voice jobs")
    # Fail closed if the sealed plan and sealed job payloads disagree.
    expected_work_ids = {
        item.work_id for item in revalidation_plan.workset.items
    }
    job_work_ids = {job.lineage.work_item_id for job in jobs_tuple}
    if expected_work_ids != job_work_ids:
        raise ValueError(
            "pinned voice jobs do not match the sealed revalidation workset"
        )
    return revalidation_plan, jobs_tuple, dict(manifest), manifest_sha256


def _admit_command(args: argparse.Namespace) -> int:
    recovery = load_recovery_artifacts(args.recovery_dir)
    if not recovery.records:
        raise ValueError("recovery bundle has no verified records to admit")

    accelerate_root = REPO_ROOT / "ipfs_accelerate_py"
    if str(accelerate_root) not in sys.path:
        sys.path.insert(0, str(accelerate_root))
    from ipfs_accelerate_py.voice_jobs.executor import (
        ArtifactPolicy,
        ArtifactResolver,
    )
    from ipfs_datasets_py.ml.accelerate_integration.bucket_audio_admission import (
        admit_bucket_audio_revalidation,
    )
    from ipfs_datasets_py.ml.accelerate_integration.voice_jobs import (
        VoiceJobBridge,
    )

    # Admission authority is the sealed schedule bundle, not a rebuilt plan.
    revalidation_plan, jobs, _manifest, _manifest_sha256 = (
        load_revalidation_artifacts(args.schedule_dir)
    )
    if revalidation_plan.recovery_id != recovery.recovery_id:
        raise ValueError(
            "schedule revalidation plan does not bind the recovery bundle"
        )

    bridge = VoiceJobBridge(queue_path=str(args.queue_path.expanduser().resolve()))
    results_by_task_id: dict[str, Any] = {}
    for job in jobs:
        try:
            results_by_task_id[job.task_id] = bridge.ingest_receipt(job.task_id)
        except Exception:
            # Missing/incomplete receipts become per-row dispositions inside
            # admit_bucket_audio_revalidation rather than aborting the batch.
            continue
    resolver = ArtifactResolver(
        ArtifactPolicy(
            output_root=args.artifact_root.expanduser().resolve(),
            max_input_bytes=args.max_artifact_bytes,
            max_decoded_bytes=max(args.max_artifact_bytes, 256 * 1024 * 1024),
            max_duration_ms=revalidation_plan.policy.max_duration_ms,
            decoder_timeout_seconds=120,
        )
    )
    transcript_bytes: dict[str, bytes] = {}
    for job in jobs:
        if job.task_type != "voice.asr":
            continue
        receipt = results_by_task_id.get(job.task_id)
        if receipt is None or not getattr(receipt, "artifacts", None):
            continue
        if len(receipt.artifacts) != 1:
            continue
        try:
            transcript_bytes[job.task_id] = resolver.resolve(
                receipt.artifacts[0].to_dict()
            )
        except Exception:
            continue
    audio_bytes: dict[str, bytes] = {}
    for record in recovery.records:
        cache_path = bucket_audio_cache_path(
            args.cache_dir.expanduser().resolve(), record.xet_hash
        )
        if cache_path.is_file() and not cache_path.is_symlink():
            audio_bytes[record.raw_sha256] = cache_path.read_bytes()
    admission = admit_bucket_audio_revalidation(
        recovery,
        revalidation_plan,
        jobs=jobs,
        results_by_task_id=results_by_task_id,
        transcript_bytes_by_asr_task_id=transcript_bytes,
        audio_bytes_by_sha256=audio_bytes,
        license_id=args.license_id,
        consent_status=args.consent_status,
    )
    result = write_admission_artifacts(
        output_dir=args.output_dir,
        recovery_id=recovery.recovery_id,
        revalidation_plan_id=revalidation_plan.revalidation_plan_id,
        admission=admission,
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


def _merge_release_command(args: argparse.Namespace) -> int:
    raw_output = args.output_dir.expanduser()
    if raw_output.exists() or raw_output.is_symlink():
        raise ValueError(
            "merge-release output directory must not already exist"
        )
    output_dir = raw_output.resolve()
    if output_dir.exists() or output_dir.is_symlink():
        raise ValueError(
            "merge-release output directory must not already exist"
        )

    from ipfs_datasets_py.voice.dataset_merge import (
        load_normalized_dataset_bundle,
        merge_admitted_audio,
    )
    from ipfs_datasets_py.voice.hf_release import (
        build_abby_voice_hf_release,
        validate_abby_voice_hf_release,
    )

    normalized = load_normalized_dataset_bundle(
        args.normalized_dir,
        expected_manifest_sha256=args.expected_normalized_manifest_sha256,
    )
    admission, admission_manifest, admission_manifest_sha256 = (
        load_admission_artifacts(args.admission_dir)
    )
    merged = merge_admitted_audio(normalized.bundle, admission)
    parent_source_ids = tuple(
        sorted(
            {
                normalized.manifest_id,
                admission.reconciliation_id,
                str(admission_manifest["recovery_id"]),
                str(admission_manifest["revalidation_plan_id"]),
            }
        )
    )
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    staging_dir = Path(
        tempfile.mkdtemp(
            prefix=f".{sha256(args.release_id.encode()).hexdigest()[:16]}.",
            suffix=".partial",
            dir=output_dir.parent,
        )
    )
    published_final = False
    try:
        release = build_abby_voice_hf_release(
            output_dir=staging_dir,
            release_id=args.release_id,
            responses=merged.bundle.responses,
            templates=merged.bundle.templates,
            audio=merged.bundle.audio,
            provenance=merged.bundle.provenance,
            graphrag_index=merged.graphrag_index,
            parent_source_ids=parent_source_ids,
            repository_commit=args.repository_commit,
        )
        validate_abby_voice_hf_release(staging_dir)
        if output_dir.exists() or output_dir.is_symlink():
            raise ValueError(
                "merge-release output directory must not already exist"
            )
        staging_dir.rename(output_dir)
        published_final = True
        validation = validate_abby_voice_hf_release(output_dir)
    except Exception:
        if published_final and output_dir.is_dir() and not output_dir.is_symlink():
            shutil.rmtree(output_dir)
        raise
    finally:
        if staging_dir.exists() and not staging_dir.is_symlink():
            shutil.rmtree(staging_dir)
    release_receipt = release.to_dict()
    release_receipt["manifest_path"] = str(output_dir / "release-manifest.json")
    release_receipt["output_dir"] = str(output_dir)
    result = {
        "admission_manifest_sha256": admission_manifest_sha256,
        "audio_count": len(merged.bundle.audio),
        "graph_cid": merged.graphrag_index.graph_cid,
        "index_cid": merged.graphrag_index.index_cid,
        "local_only": True,
        "merge_id": merged.merge_id,
        "normalized_manifest_sha256": normalized.manifest_sha256,
        "output_dir": str(output_dir),
        "parent_source_ids": list(parent_source_ids),
        "publication_status": "not_requested",
        "published": False,
        "reconciliation_id": admission.reconciliation_id,
        "release": release_receipt,
        "release_validation": validation,
        "remote_write_attempted": False,
        "response_count": len(merged.bundle.responses),
        "stage": "local_release_validated_pending_publication_approval",
    }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    plan = subparsers.add_parser(
        "plan",
        help="Discover the bucket read-only and build a pinned recovery plan.",
    )
    plan.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    plan.add_argument(
        "--expected-source-sha256",
        default=DEFAULT_SOURCE_SHA256,
        help="Required SHA-256 pin for the aggregate source manifest.",
    )
    plan.add_argument("--bucket-id", default=DEFAULT_BUCKET_ID)
    plan.add_argument("--prefix", default="")
    plan.add_argument("--endpoint", default="https://huggingface.co")
    plan.add_argument(
        "--token-env",
        default="HF_TOKEN",
        help="Environment variable containing an optional read token; never serialized.",
    )
    plan.add_argument("--timeout-seconds", type=float, default=60.0)
    plan.add_argument(
        "--discovery-passes",
        type=int,
        default=DEFAULT_STABLE_DISCOVERY_PASSES,
        help="Identical full listings required before absences are accepted (minimum 2).",
    )
    run_policy = plan.add_mutually_exclusive_group()
    run_policy.add_argument(
        "--allowed-run-id",
        action="append",
        help=(
            "Approved abby-full-preprocess run ID; repeat to replace the "
            "auto-discovered production allowlist from the listing."
        ),
    )
    run_policy.add_argument(
        "--allow-unlisted-runs",
        action="store_true",
        help=(
            "Allow response-linkable objects outside production run paths "
            "(development-only)."
        ),
    )
    plan.add_argument(
        "--skip-production-coverage-gate",
        action="store_true",
        help="Development-only: skip pinned 13,771-selected/8-missing coverage floors.",
    )
    plan.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    plan.add_argument(
        "--no-update-latest",
        action="store_true",
        help="Do not atomically update output-dir/latest.json after publication.",
    )
    plan.add_argument("--locale", default="en-US")
    plan.add_argument("--license-id", default="MIT")
    plan.add_argument(
        "--consent-status",
        choices=("granted", "not_required", "unknown", "denied", "withdrawn"),
        default="not_required",
    )
    plan.set_defaults(handler=_plan_command)

    normalize = subparsers.add_parser(
        "normalize",
        help=(
            "Normalize every sealed-plan bucket object (all ~30k+ paths) into "
            "abby_voice_bucket_audio_entry_v1 rows, including unmapped "
            "response-linkable audio and non-response orphans."
        ),
    )
    normalize.add_argument(
        "--plan-dir",
        type=Path,
        required=True,
        help="Immutable plan bundle produced by the plan command.",
    )
    normalize.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_NORMALIZED_OUTPUT_DIR,
        help="Root for immutable full-bucket normalized entry bundles.",
    )
    normalize.set_defaults(handler=_normalize_command)

    fetch = subparsers.add_parser(
        "fetch",
        help=(
            "Download a bounded plan prefix into byte/decode-verified staging; "
            "default limit is 3."
        ),
    )
    fetch.add_argument(
        "--plan-dir",
        type=Path,
        required=True,
        help="Immutable output/<plan_id> directory produced by the plan command.",
    )
    fetch_target = fetch.add_mutually_exclusive_group()
    fetch_target.add_argument(
        "--limit",
        type=int,
        default=3,
        help="Total deterministic response-sorted canary target (default: 3).",
    )
    fetch_target.add_argument(
        "--all",
        action="store_true",
        help="Explicitly fetch every selected response in the plan.",
    )
    fetch.add_argument(
        "--cache-dir",
        type=Path,
        default=DEFAULT_CACHE_DIR,
        help="Ignored local cache root for Xet-keyed objects and the resume ledger.",
    )
    fetch.add_argument(
        "--ledger-path",
        type=Path,
        help="Optional explicit verified-record ledger path.",
    )
    fetch.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_CACHE_DIR / "recovery-runs",
        help="Root for immutable recovery result bundles.",
    )
    fetch.add_argument("--endpoint", default="https://huggingface.co")
    fetch.add_argument(
        "--token-env",
        default="HF_TOKEN",
        help="Environment variable containing an optional read token; never serialized.",
    )
    fetch.add_argument("--timeout-seconds", type=float, default=60.0)
    fetch.add_argument("--ffprobe", default="ffprobe")
    fetch.add_argument("--ffmpeg", default="ffmpeg")
    fetch.add_argument(
        "--skip-decode-probe",
        action="store_true",
        help="Development-only: stage without ffprobe evidence; never publishable.",
    )
    fetch.add_argument("--checkpoint-interval", type=int, default=100)
    fetch.add_argument(
        "--fail-fast",
        action="store_true",
        help="Diagnostic mode: stop instead of recording row-level retry dispositions.",
    )
    fetch.add_argument(
        "--fail-on-row-failure",
        action="store_true",
        help=(
            "Return exit code 3 when retry dispositions were recorded. By "
            "default handled row failures are reported as partial success."
        ),
    )
    fetch.set_defaults(handler=_fetch_command)

    schedule = subparsers.add_parser(
        "schedule",
        help=(
            "Verify pending recovery, import artifacts, and plan ASR/audio "
            "validation jobs."
        ),
    )
    schedule.add_argument(
        "--recovery-dir",
        type=Path,
        required=True,
        help="Immutable recovery/<recovery_id> bundle produced by fetch.",
    )
    schedule.add_argument(
        "--cache-dir",
        type=Path,
        default=DEFAULT_CACHE_DIR / "objects",
        help="Exact Xet-keyed object-cache directory used by fetch.",
    )
    schedule.add_argument(
        "--artifact-root",
        type=Path,
        default=DEFAULT_ACCELERATOR_ARTIFACT_DIR,
        help=(
            "Content-addressed accelerator artifact root shared with voice workers."
        ),
    )
    schedule.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_REVALIDATION_OUTPUT_DIR,
        help="Root for immutable ASR/audio-validation plan bundles.",
    )
    schedule.add_argument(
        "--max-artifact-bytes",
        type=int,
        default=32 * 1024 * 1024,
    )
    schedule.add_argument("--asr-provider", default="huggingface")
    schedule.add_argument("--asr-model", default="openai/whisper-base.en")
    schedule.add_argument("--asr-provider-version", default="transformers")
    schedule.add_argument(
        "--submit",
        action="store_true",
        help="Explicitly submit the deterministic jobs to the DuckDB queue.",
    )
    schedule.add_argument(
        "--queue-path",
        type=Path,
        default=DEFAULT_VOICE_QUEUE_PATH,
    )
    schedule.set_defaults(handler=_schedule_command)

    admit = subparsers.add_parser(
        "admit",
        help=(
            "Load the sealed schedule bundle, verify completed "
            "ASR/audio-validation receipts, and emit only linkable rows plus "
            "per-row quarantine dispositions."
        ),
    )
    admit.add_argument("--recovery-dir", type=Path, required=True)
    admit.add_argument(
        "--schedule-dir",
        type=Path,
        required=True,
        help=(
            "Immutable revalidation/schedule artifact directory produced by "
            "the schedule command (contains revalidation-plan.json and "
            "voice-jobs.jsonl). Admission never rebuilds the plan."
        ),
    )
    admit.add_argument(
        "--cache-dir",
        type=Path,
        default=DEFAULT_CACHE_DIR / "objects",
    )
    admit.add_argument(
        "--artifact-root",
        type=Path,
        default=DEFAULT_ACCELERATOR_ARTIFACT_DIR,
    )
    admit.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_ADMISSION_OUTPUT_DIR,
    )
    admit.add_argument(
        "--queue-path",
        type=Path,
        default=DEFAULT_VOICE_QUEUE_PATH,
    )
    admit.add_argument(
        "--max-artifact-bytes",
        type=int,
        default=32 * 1024 * 1024,
    )
    admit.add_argument("--license-id", default="MIT")
    admit.add_argument(
        "--consent-status",
        choices=("granted", "not_required"),
        default="not_required",
    )
    admit.set_defaults(handler=_admit_command)

    merge_release = subparsers.add_parser(
        "merge-release",
        help=(
            "Verify pinned normalized/admission bundles, merge reciprocal "
            "audio links, and validate a new local release without publishing."
        ),
    )
    merge_release.add_argument("--normalized-dir", type=Path, required=True)
    merge_release.add_argument(
        "--expected-normalized-manifest-sha256",
        required=True,
        help="Exact SHA-256 of normalized-dir/manifest.json bytes.",
    )
    merge_release.add_argument("--admission-dir", type=Path, required=True)
    merge_release.add_argument("--output-dir", type=Path, required=True)
    merge_release.add_argument("--release-id", required=True)
    merge_release.add_argument("--repository-commit", required=True)
    merge_release.set_defaults(handler=_merge_release_command)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except (OSError, TypeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
