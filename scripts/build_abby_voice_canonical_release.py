#!/usr/bin/env python3
"""Build the immutable canonical Abby voice v2 release locally.

The builder replaces every superseded phone/address clip with the completed
deduplicated regeneration output, retains the vocabulary and slotted-template
corpus as checksum-pinned support artifacts, embeds only active audio assets,
and delegates final Parquet/release sealing to ``ipfs_datasets_py``.

This command is offline. It has no Hugging Face client and performs no remote
write or consumer-pointer mutation.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from string import Formatter
import sys
import tempfile
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPO_ROOT / "ipfs_datasets_py"
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from ipfs_datasets_py.huggingface.release import canonical_json_bytes  # noqa: E402
from ipfs_datasets_py.voice.hf_release import (  # noqa: E402
    AbbyVoiceHFReleaseBuilder,
    AbbyVoiceHFReleasePolicy,
    AbbyVoiceReleaseSupportSource,
    validate_abby_voice_hf_release,
)
from ipfs_datasets_py.voice.normalize import (  # noqa: E402
    AbbyVoiceDatasetNormalizer,
    NormalizationConfig,
    normalize_indextts_spoken_text,
    normalized_text_identity,
)
from ipfs_datasets_py.voice.regeneration import (  # noqa: E402
    normalize_regeneration_spoken_text,
    unsafe_spoken_numeric_punctuation_reasons,
    unsafe_spoken_transformation_reasons,
)
from ipfs_datasets_py.voice.schema import (  # noqa: E402
    AbbyVoiceDatasetBundle,
    stable_template_id,
    validate_publishable,
)

DEFAULT_STAGE_ROOT = REPO_ROOT / "tmp_assets" / "hf-abby-tts-canonical-dataset"
DEFAULT_METADATA_ROOT = DEFAULT_STAGE_ROOT / "metadata"
DEFAULT_RETAINED_RESPONSES = DEFAULT_METADATA_ROOT / "abby_tts_responses.jsonl"
DEFAULT_VOCABULARY = DEFAULT_METADATA_ROOT / "abby_tts_vocabulary.jsonl"
DEFAULT_FRAMES = DEFAULT_METADATA_ROOT / "abby_tts_slotted_response_frames.jsonl"
DEFAULT_INTENTS = DEFAULT_METADATA_ROOT / "abby_tts_slotted_intents.jsonl"
DEFAULT_BUCKET_OBJECTS = DEFAULT_METADATA_ROOT / "abby_tts_bucket_audio_objects.jsonl"
DEFAULT_REGENERATION_PLAN = DEFAULT_METADATA_ROOT / "regeneration-full-plan.json"
DEFAULT_REGENERATION_AUDIO = DEFAULT_METADATA_ROOT / "regeneration-audio-manifest.json"
DEFAULT_WHISPER_RECEIPT = (
    DEFAULT_METADATA_ROOT / "regeneration-full-whisper-validation-v3.receipt.json"
)
DEFAULT_SLOTTED_DAG = REPO_ROOT / "docs" / "phone_dialog_generation" / "slotted_response_dag.json"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "tmp_assets" / "abby-voice-v2-releases"

FULL_WHISPER_ITEM_SCHEMA = "abby_voice_full_whisper_validation_item_v3"
FULL_WHISPER_RECEIPT_SCHEMA = "abby_voice_full_whisper_validation_receipt_v3"
FULL_WHISPER_FAILURE_SCHEMA = "abby_voice_full_whisper_failures_v2"
FULL_WHISPER_VALIDATOR_VERSION = "abby_voice_full_whisper_validator_v3"
SEMANTIC_CORRUPTION_SCHEMA = "abby_voice_semantic_corruptions_v2"
SEMANTIC_CORRUPTION_SCAN_RULE = (
    "confirmed_abbreviation_and_apostrophe_direction_rules_v2"
)
EXPECTED_SEMANTIC_CORRUPTION_REASON_COUNTS = {
    "apostrophe_direction_expansion": 9,
    "st_abbreviation_expanded_to_street": 33,
}
BASE_WHISPER_MODEL_NAME = "openai/whisper-base"
BASE_WHISPER_MODEL_REVISION = "e37978b90ca9030d5170a5c07aadb050351a65bb"
ADJUDICATION_MODEL_NAME = "openai/whisper-large-v3-turbo"
ADJUDICATION_MODEL_REVISION = "41f01f3fe87f28c78e2fbf8b568835947dd65ed9"
ADJUDICATION_SUBSET_SCHEMA = "abby_voice_whisper_adjudication_subset_v1"
ADJUDICATION_RECEIPT_SCHEMA = "abby_voice_whisper_adjudication_receipt_v1"
ADJUDICATION_DECISION_POLICY = (
    "base_failure_recoverable_only_when_stronger_item_passed_and_hashes_identical"
)
APPROVED_WHISPER_GATES = {
    "maximum_wer_bp": 3_500,
    "minimum_content_word_coverage_bp": 6_500,
    "minimum_similarity_bp": 7_800,
    "require_numeric_sequences_match": True,
}

_MUTABLE_HF_MARKERS = (
    "/resolve/main/",
    "/resolve/master/",
    "/resolve/latest/",
    "/tree/main/",
    "/blob/main/",
    "refs/heads/",
)
_INHERITED_LIST_FIELDS = (
    "locationTags",
    "originalTexts",
    "routes",
    "serviceTags",
    "slottedCanonicalQueryTemplates",
    "slottedEdgeIds",
    "slottedIntentIds",
    "slottedResponseFrameIds",
    "slottedResponseSignatures",
    "sourceIds",
    "sourceTypes",
)


class CanonicalReleaseReconciliationError(ValueError):
    """Raised when source evidence cannot form one canonical release."""


@dataclass(frozen=True, slots=True)
class CanonicalReleaseInputs:
    stage_root: Path
    retained_responses: Path
    vocabulary: Path
    frames: Path
    intents: Path
    bucket_objects: Path
    regeneration_plan: Path
    regeneration_audio: Path
    slotted_dag: Path


@dataclass(frozen=True, slots=True)
class FullWhisperValidationEvidence:
    """Complete, content-bound v3 Whisper evidence used by release sealing."""

    receipt_path: Path
    manifest_path: Path
    ledger_path: Path
    failure_manifest_path: Path
    receipt: Mapping[str, Any]
    latest_events: Mapping[str, Mapping[str, Any]]
    failed_audio_ids: frozenset[str]
    semantic_corruption_manifest_path: Path | None
    semantic_corruption_ids: frozenset[str]

    @property
    def validation_receipt_id(self) -> str:
        return str(self.receipt["validation_receipt_id"])

    @property
    def receipt_sha256(self) -> str:
        return _sha256_file(self.receipt_path)

    @property
    def ledger_sha256(self) -> str:
        return _sha256_file(self.ledger_path)

    @property
    def failure_manifest_sha256(self) -> str:
        return _sha256_file(self.failure_manifest_path)

    @property
    def semantic_corruption_manifest_sha256(self) -> str | None:
        if self.semantic_corruption_manifest_path is None:
            return None
        return _sha256_file(self.semantic_corruption_manifest_path)


@dataclass(frozen=True, slots=True)
class WhisperAdjudicationEvidence:
    """Pinned stronger-model decision layer over every base-v3 failure."""

    summary_path: Path
    summary: Mapping[str, Any]
    validation: FullWhisperValidationEvidence

    @property
    def summary_sha256(self) -> str:
        return _sha256_file(self.summary_path)

    @property
    def validation_receipt_id(self) -> str:
        return self.validation.validation_receipt_id

    @property
    def latest_events(self) -> Mapping[str, Mapping[str, Any]]:
        return self.validation.latest_events

    @property
    def receipt_sha256(self) -> str:
        return self.validation.receipt_sha256

    @property
    def ledger_sha256(self) -> str:
        return self.validation.ledger_sha256

    @property
    def failure_manifest_sha256(self) -> str:
        return self.validation.failure_manifest_sha256


@dataclass(frozen=True, slots=True)
class CanonicalReleaseReconciliation:
    bundle: AbbyVoiceDatasetBundle
    audio_sources: Mapping[str, Path]
    active_links: tuple[Mapping[str, Any], ...]
    supersession_rows: tuple[Mapping[str, Any], ...]
    excluded_audio_rows: tuple[Mapping[str, Any], ...]
    quality_exclusion_rows: tuple[Mapping[str, Any], ...]
    unsafe_spoken_regeneration_rows: tuple[Mapping[str, Any], ...]
    regeneration_inventory_rows: tuple[Mapping[str, Any], ...]
    runtime_precomputed_audio_rows: tuple[Mapping[str, Any], ...]
    frame_template_rows: tuple[Mapping[str, Any], ...]
    audit: Mapping[str, Any]


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _full_whisper_receipt_id(
    *,
    manifest_sha256: str,
    ledger_sha256: str,
    run_fingerprint: str,
    semantic_manifest_sha256: str,
) -> str:
    digest = sha256(
        (
            manifest_sha256
            + "\0"
            + ledger_sha256
            + "\0"
            + run_fingerprint
            + "\0"
            + semantic_manifest_sha256
        ).encode("utf-8")
    ).hexdigest()
    return f"abby-voice-full-asr-corpus:sha256:{digest}"


def _relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CanonicalReleaseReconciliationError(
            f"cannot read JSON {path}: {exc}"
        ) from exc


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise CanonicalReleaseReconciliationError(
            f"cannot read JSONL {path}: {exc}"
        ) from exc
    for line_number, raw in enumerate(lines, start=1):
        if not raw.strip():
            continue
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise CanonicalReleaseReconciliationError(
                f"malformed JSONL at {path}:{line_number}: {exc}"
            ) from exc
        if not isinstance(value, Mapping):
            raise CanonicalReleaseReconciliationError(
                f"JSONL row must be an object at {path}:{line_number}"
            )
        rows.append(dict(value))
    return rows


def _required_count(value: Any, *, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise CanonicalReleaseReconciliationError(
            f"full Whisper receipt field {field} must be a non-negative integer"
        )
    return value


def _event_passes_approved_gates(event: Mapping[str, Any]) -> bool:
    try:
        return (
            int(event["normalized_similarity_bp"])
            >= APPROVED_WHISPER_GATES["minimum_similarity_bp"]
            and int(event["content_word_coverage_bp"])
            >= APPROVED_WHISPER_GATES["minimum_content_word_coverage_bp"]
            and int(event["wer_bp"])
            <= APPROVED_WHISPER_GATES["maximum_wer_bp"]
            and event.get("forbidden_negative_detected") is False
            and event.get("numeric_sequences_match") is True
        )
    except (KeyError, TypeError, ValueError):
        return False


def _resolve_bound_artifact(receipt_path: Path, declared: Any, *, field: str) -> Path:
    raw = str(declared or "").strip()
    if not raw:
        raise CanonicalReleaseReconciliationError(
            f"full Whisper receipt is missing {field}"
        )
    requested = Path(raw).expanduser()
    candidates = (
        (requested,)
        if requested.is_absolute()
        else (
            REPO_ROOT / requested,
            receipt_path.parent / requested.name,
        )
    )
    existing = {
        candidate.resolve()
        for candidate in candidates
        if candidate.is_file() and not candidate.is_symlink()
    }
    if len(existing) != 1:
        raise CanonicalReleaseReconciliationError(
            f"full Whisper receipt {field} does not resolve to exactly one "
            f"regular non-symlink file: {raw!r}"
        )
    return existing.pop()


def _generated_audio_path(row: Mapping[str, Any]) -> Path:
    raw_path = str(
        row.get("preferredAudioPath")
        or row.get("mp3Path")
        or row.get("audioPath")
        or ""
    ).strip()
    path = Path(raw_path)
    if raw_path and not path.is_absolute():
        path = REPO_ROOT / path
    if not raw_path or not path.is_file() or path.is_symlink():
        raise CanonicalReleaseReconciliationError(
            f"generated audio is missing or unsafe: {row.get('id')!r}"
        )
    return path.resolve()


def _stage_audio_path(stage_root: Path, relative: Any, *, audio_id: str) -> Path:
    raw = str(relative or "").strip()
    if not raw:
        raise CanonicalReleaseReconciliationError(
            f"retained audio has no datasetAudioPath: {audio_id}"
        )
    stage = stage_root.expanduser().resolve()
    candidate = stage.joinpath(*Path(raw).parts)
    if candidate.is_symlink():
        raise CanonicalReleaseReconciliationError(
            f"retained audio must not be a symlink: {audio_id}"
        )
    resolved = candidate.resolve()
    try:
        resolved.relative_to(stage)
    except ValueError as exc:
        raise CanonicalReleaseReconciliationError(
            f"retained audio escapes the stage root: {audio_id}"
        ) from exc
    if not resolved.is_file():
        raise CanonicalReleaseReconciliationError(
            f"retained audio is missing: {audio_id}"
        )
    return resolved


def _without_audio_locator(row: Mapping[str, Any]) -> dict[str, Any]:
    result = _without_remote_urls(row)
    for field in (
        "audioPath",
        "audioSha256",
        "datasetAudioPath",
        "mp3Path",
        "preferredAudioPath",
    ):
        result.pop(field, None)
    result["audioAvailable"] = False
    return result


def load_full_whisper_validation_evidence(
    *,
    validation_manifest: Path,
    receipt_path: Path,
    required_model_name: str | None = None,
    required_model_revision: str | None = None,
    require_semantic_manifest: bool = False,
) -> FullWhisperValidationEvidence:
    """Load and exhaustively bind a final single-shard v3 Whisper receipt."""

    receipt_path = receipt_path.expanduser().resolve()
    if not receipt_path.is_file() or receipt_path.is_symlink():
        raise CanonicalReleaseReconciliationError(
            f"full Whisper receipt is missing or unsafe: {receipt_path}"
        )
    receipt = _load_json(receipt_path)
    validation_manifest = validation_manifest.expanduser().resolve()
    generation = _load_json(validation_manifest)
    if not isinstance(receipt, Mapping):
        raise CanonicalReleaseReconciliationError(
            "full Whisper receipt must be an object"
        )
    if not isinstance(generation, Mapping):
        raise CanonicalReleaseReconciliationError(
            "regeneration audio manifest must be an object"
        )
    raw_rows = generation.get("responses")
    if not isinstance(raw_rows, list):
        raise CanonicalReleaseReconciliationError(
            "regeneration audio manifest is missing responses"
        )
    generated_rows = [
        dict(row) for row in raw_rows if isinstance(row, Mapping)
    ]
    if len(generated_rows) != len(raw_rows):
        raise CanonicalReleaseReconciliationError(
            "regeneration audio response rows must be objects"
        )
    generated_by_id = _index_unique(
        generated_rows,
        "id",
        label="generated responses",
    )
    manifest_sha256 = _sha256_file(validation_manifest)
    if (
        receipt.get("schema_version") != FULL_WHISPER_RECEIPT_SCHEMA
        or receipt.get("validator_version") != FULL_WHISPER_VALIDATOR_VERSION
    ):
        raise CanonicalReleaseReconciliationError(
            "full Whisper receipt has an unsupported schema or validator"
        )
    if receipt.get("manifest_sha256") != manifest_sha256:
        raise CanonicalReleaseReconciliationError(
            "full Whisper receipt does not bind the regeneration manifest"
        )
    if receipt.get("gates") != APPROVED_WHISPER_GATES:
        raise CanonicalReleaseReconciliationError(
            "full Whisper receipt was not produced with the approved v3 gates"
        )
    if (
        required_model_name is not None
        and receipt.get("model_name") != required_model_name
    ):
        raise CanonicalReleaseReconciliationError(
            "full Whisper receipt model does not match the required pinned model"
        )
    if (
        required_model_revision is not None
        and receipt.get("model_revision") != required_model_revision
    ):
        raise CanonicalReleaseReconciliationError(
            "full Whisper receipt revision does not match the required pin"
        )
    if (
        receipt.get("shard_count") != 1
        or receipt.get("shard_index") != 0
        or receipt.get("remote_writes") is not False
    ):
        raise CanonicalReleaseReconciliationError(
            "release requires one complete offline full-corpus Whisper receipt"
        )

    counts = {
        name: _required_count(receipt.get(name), field=name)
        for name in (
            "completed_count",
            "error_count",
            "failed_count",
            "passed_count",
            "pending_count",
            "total_count",
        )
    }
    semantic_corruption_count = _required_count(
        receipt.get("semantic_corruption_count"),
        field="semantic_corruption_count",
    )
    expected_total = len(generated_by_id)
    if (
        counts["total_count"] != expected_total
        or counts["completed_count"] != expected_total
        or counts["pending_count"] != 0
        or counts["error_count"] != 0
        or counts["passed_count"] + counts["failed_count"] != expected_total
        or receipt.get("all_passed")
        is not (
            counts["failed_count"] == 0
            and semantic_corruption_count == 0
        )
    ):
        raise CanonicalReleaseReconciliationError(
            "full Whisper receipt is incomplete or internally inconsistent"
        )

    run_fingerprint = str(receipt.get("run_fingerprint") or "")
    if len(run_fingerprint) != 64:
        raise CanonicalReleaseReconciliationError(
            "full Whisper receipt has an invalid run_fingerprint"
        )
    declared_manifest_path = _resolve_bound_artifact(
        receipt_path,
        receipt.get("manifest"),
        field="manifest",
    )
    if declared_manifest_path != validation_manifest:
        raise CanonicalReleaseReconciliationError(
            "full Whisper receipt manifest path does not identify the "
            "validated input"
        )
    ledger_path = _resolve_bound_artifact(
        receipt_path,
        receipt.get("ledger"),
        field="ledger",
    )
    failure_manifest_path = _resolve_bound_artifact(
        receipt_path,
        receipt.get("failed_item_manifest"),
        field="failed_item_manifest",
    )
    semantic_manifest_path = _resolve_bound_artifact(
        receipt_path,
        receipt.get("semantic_corruption_manifest"),
        field="semantic_corruption_manifest",
    )
    ledger_sha256 = _sha256_file(ledger_path)
    failure_manifest_sha256 = _sha256_file(failure_manifest_path)
    semantic_manifest_sha256 = _sha256_file(semantic_manifest_path)
    if (
        receipt.get("ledger_sha256") != ledger_sha256
        or receipt.get("failed_item_manifest_sha256")
        != failure_manifest_sha256
        or receipt.get("semantic_corruption_manifest_sha256")
        != semantic_manifest_sha256
    ):
        raise CanonicalReleaseReconciliationError(
            "full Whisper receipt artifact digest mismatch"
        )
    expected_receipt_id = _full_whisper_receipt_id(
        manifest_sha256=manifest_sha256,
        ledger_sha256=ledger_sha256,
        run_fingerprint=run_fingerprint,
        semantic_manifest_sha256=semantic_manifest_sha256,
    )
    if receipt.get("validation_receipt_id") != expected_receipt_id:
        raise CanonicalReleaseReconciliationError(
            "full Whisper validation_receipt_id does not match its bound inputs"
        )

    manifest_indices = {
        str(row["id"]): index for index, row in enumerate(generated_rows)
    }
    latest_events: dict[str, dict[str, Any]] = {}
    for event in _load_jsonl(ledger_path):
        audio_id = str(event.get("audio_id") or "")
        if (
            event.get("schema_version") != FULL_WHISPER_ITEM_SCHEMA
            or event.get("validator_version") != FULL_WHISPER_VALIDATOR_VERSION
            or event.get("run_fingerprint") != run_fingerprint
            or event.get("asr_model") != receipt.get("model_name")
            or event.get("model_revision") != receipt.get("model_revision")
            or audio_id not in generated_by_id
        ):
            raise CanonicalReleaseReconciliationError(
                f"invalid full Whisper ledger event for {audio_id!r}"
            )
        latest_events[audio_id] = event
    if set(latest_events) != set(generated_by_id):
        raise CanonicalReleaseReconciliationError(
            "full Whisper ledger does not cover every generated audio ID"
        )

    failed_audio_ids: set[str] = set()
    for audio_id, row in generated_by_id.items():
        event = latest_events[audio_id]
        audio_path = _generated_audio_path(row)
        expected_audio_sha256 = _sha256_file(audio_path)
        expected_text_sha256 = sha256(
            str(row.get("text") or "").encode("utf-8")
        ).hexdigest()
        if (
            event.get("status") != "validated"
            or event.get("manifest_index") != manifest_indices[audio_id]
            or event.get("audio_sha256") != expected_audio_sha256
            or event.get("expected_text_sha256") != expected_text_sha256
            or not isinstance(event.get("passed"), bool)
            or event["passed"] is not _event_passes_approved_gates(event)
        ):
            raise CanonicalReleaseReconciliationError(
                f"full Whisper event is stale or incomplete for {audio_id}"
            )
        if event["passed"] is False:
            failed_audio_ids.add(audio_id)
    if (
        len(failed_audio_ids) != counts["failed_count"]
        or expected_total - len(failed_audio_ids) != counts["passed_count"]
    ):
        raise CanonicalReleaseReconciliationError(
            "full Whisper event outcomes do not match receipt counts"
        )

    failure_manifest = _load_json(failure_manifest_path)
    if (
        not isinstance(failure_manifest, Mapping)
        or failure_manifest.get("schema_version") != FULL_WHISPER_FAILURE_SCHEMA
        or failure_manifest.get("validator_version")
        != FULL_WHISPER_VALIDATOR_VERSION
        or failure_manifest.get("manifest_sha256") != manifest_sha256
        or failure_manifest.get("model_name") != receipt.get("model_name")
        or failure_manifest.get("model_revision")
        != receipt.get("model_revision")
        or failure_manifest.get("run_fingerprint") != run_fingerprint
        or failure_manifest.get("failed_count") != len(failed_audio_ids)
        or not isinstance(failure_manifest.get("failures"), list)
    ):
        raise CanonicalReleaseReconciliationError(
            "full Whisper failure manifest is invalid"
        )
    failures_by_id = _index_unique(
        [
            dict(row)
            for row in failure_manifest["failures"]
            if isinstance(row, Mapping)
        ],
        "audio_id",
        label="full Whisper failures",
    )
    if len(failures_by_id) != len(failure_manifest["failures"]):
        raise CanonicalReleaseReconciliationError(
            "full Whisper failure rows must be objects"
        )
    if set(failures_by_id) != failed_audio_ids:
        raise CanonicalReleaseReconciliationError(
            "full Whisper failure manifest does not match failed events"
        )
    for audio_id, failure in failures_by_id.items():
        event = latest_events[audio_id]
        if (
            failure.get("audio_sha256") != event.get("audio_sha256")
            or failure.get("expected_text_sha256")
            != event.get("expected_text_sha256")
            or failure.get("manifest_index") != event.get("manifest_index")
            or failure.get("validation_receipt_id")
            != event.get("validation_receipt_id")
            or not isinstance(failure.get("failure_reasons"), list)
            or not failure["failure_reasons"]
        ):
            raise CanonicalReleaseReconciliationError(
                f"full Whisper failure evidence is incomplete for {audio_id}"
            )

    semantic_corruption_ids: set[str] = set()
    if require_semantic_manifest:
        semantic_manifest = _load_json(semantic_manifest_path)
        if (
            receipt.get("semantic_corruption_manifest_sha256")
            != semantic_manifest_sha256
            or receipt.get("semantic_corruption_count") != 42
            or receipt.get("semantic_override_exclusion_count") != 42
            or receipt.get("semantic_corruption_reason_counts")
            != EXPECTED_SEMANTIC_CORRUPTION_REASON_COUNTS
            or not isinstance(semantic_manifest, Mapping)
            or semantic_manifest.get("schema_version")
            != SEMANTIC_CORRUPTION_SCHEMA
            or semantic_manifest.get("scan_rule")
            != SEMANTIC_CORRUPTION_SCAN_RULE
            or semantic_manifest.get("manifest_sha256") != manifest_sha256
            or semantic_manifest.get("corruption_count") != 42
            or semantic_manifest.get("release_eligible_count")
            != expected_total - 42
            or semantic_manifest.get("reason_counts")
            != EXPECTED_SEMANTIC_CORRUPTION_REASON_COUNTS
            or not isinstance(semantic_manifest.get("items"), list)
        ):
            raise CanonicalReleaseReconciliationError(
                "base Whisper semantic-corruption evidence is invalid"
            )
        semantic_items = _index_unique(
            [
                dict(row)
                for row in semantic_manifest["items"]
                if isinstance(row, Mapping)
            ],
            "audio_id",
            label="semantic corruption items",
        )
        if len(semantic_items) != len(semantic_manifest["items"]):
            raise CanonicalReleaseReconciliationError(
                "semantic corruption items must be objects"
            )
        semantic_reason_counts: dict[str, int] = defaultdict(int)
        for audio_id, item in semantic_items.items():
            if audio_id not in generated_by_id:
                raise CanonicalReleaseReconciliationError(
                    f"unknown semantic corruption audio ID: {audio_id}"
                )
            reasons = item.get("reasons")
            if (
                item.get("active_eligible") is not False
                or item.get("manifest_index") != manifest_indices[audio_id]
                or item.get("expected_text_sha256")
                != latest_events[audio_id].get("expected_text_sha256")
                or not isinstance(reasons, list)
                or not reasons
                or not set(reasons)
                <= set(EXPECTED_SEMANTIC_CORRUPTION_REASON_COUNTS)
            ):
                raise CanonicalReleaseReconciliationError(
                    f"invalid semantic corruption item for {audio_id}"
                )
            for reason in set(reasons):
                semantic_reason_counts[str(reason)] += 1
        semantic_corruption_ids = set(semantic_items)
        semantic_ids_payload = (
            "".join(
                f"{audio_id}\n"
                for audio_id in sorted(semantic_corruption_ids)
            ).encode("utf-8")
            if semantic_corruption_ids
            else b""
        )
        semantic_ids_sha256 = sha256(semantic_ids_payload).hexdigest()
        if (
            len(semantic_corruption_ids) != 42
            or dict(sorted(semantic_reason_counts.items()))
            != EXPECTED_SEMANTIC_CORRUPTION_REASON_COUNTS
            or semantic_manifest.get("unique_audio_ids_sha256")
            != semantic_ids_sha256
            or receipt.get(
                "semantic_corruption_unique_audio_ids_sha256"
            )
            != semantic_ids_sha256
        ):
            raise CanonicalReleaseReconciliationError(
                "semantic corruption IDs/reasons do not match their bindings"
            )

    return FullWhisperValidationEvidence(
        receipt_path=receipt_path,
        manifest_path=validation_manifest,
        ledger_path=ledger_path,
        failure_manifest_path=failure_manifest_path,
        receipt=dict(receipt),
        latest_events=dict(sorted(latest_events.items())),
        failed_audio_ids=frozenset(failed_audio_ids),
        semantic_corruption_manifest_path=semantic_manifest_path,
        semantic_corruption_ids=frozenset(semantic_corruption_ids),
    )


def load_whisper_adjudication_evidence(
    *,
    base_validation: FullWhisperValidationEvidence,
    summary_path: Path,
) -> WhisperAdjudicationEvidence:
    """Validate the non-mutating stronger-model layer over all base failures."""

    summary_path = summary_path.expanduser().resolve()
    if not summary_path.is_file() or summary_path.is_symlink():
        raise CanonicalReleaseReconciliationError(
            f"Whisper adjudication summary is missing or unsafe: {summary_path}"
        )
    summary = _load_json(summary_path)
    if not isinstance(summary, Mapping):
        raise CanonicalReleaseReconciliationError(
            "Whisper adjudication summary must be an object"
        )
    if (
        summary.get("schema_version") != ADJUDICATION_RECEIPT_SCHEMA
        or summary.get("decision_policy") != ADJUDICATION_DECISION_POLICY
        or summary.get("evidence_only") is not True
        or summary.get("base_receipt_mutated") is not False
        or summary.get("stronger_model_name") != ADJUDICATION_MODEL_NAME
        or summary.get("stronger_model_revision")
        != ADJUDICATION_MODEL_REVISION
    ):
        raise CanonicalReleaseReconciliationError(
            "Whisper adjudication summary policy/model is invalid"
        )

    base_receipt_path = _resolve_bound_artifact(
        summary_path,
        summary.get("base_validation_receipt"),
        field="base_validation_receipt",
    )
    base_failure_path = _resolve_bound_artifact(
        summary_path,
        summary.get("base_failure_manifest"),
        field="base_failure_manifest",
    )
    subset_path = _resolve_bound_artifact(
        summary_path,
        summary.get("subset_manifest"),
        field="subset_manifest",
    )
    stronger_receipt_path = _resolve_bound_artifact(
        summary_path,
        summary.get("stronger_validation_receipt"),
        field="stronger_validation_receipt",
    )
    semantic_manifest_path = _resolve_bound_artifact(
        summary_path,
        summary.get("semantic_corruption_manifest"),
        field="semantic_corruption_manifest",
    )
    summary_semantic_ids = summary.get("semantic_corruption_ids")
    if (
        base_receipt_path != base_validation.receipt_path
        or base_failure_path != base_validation.failure_manifest_path
        or summary.get("base_validation_receipt_sha256")
        != base_validation.receipt_sha256
        or summary.get("base_failure_manifest_sha256")
        != base_validation.failure_manifest_sha256
        or summary.get("subset_manifest_sha256") != _sha256_file(subset_path)
        or summary.get("stronger_validation_receipt_sha256")
        != _sha256_file(stronger_receipt_path)
        or semantic_manifest_path
        != base_validation.semantic_corruption_manifest_path
        or summary.get("semantic_corruption_manifest_sha256")
        != base_validation.semantic_corruption_manifest_sha256
        or summary.get("semantic_corruption_count")
        != len(base_validation.semantic_corruption_ids)
        or summary.get("semantic_override_exclusion_count")
        != len(base_validation.semantic_corruption_ids)
        or not isinstance(summary_semantic_ids, list)
        or summary_semantic_ids
        != sorted(base_validation.semantic_corruption_ids)
        or summary.get("semantic_corruption_unique_audio_ids_sha256")
        != base_validation.receipt.get(
            "semantic_corruption_unique_audio_ids_sha256"
        )
    ):
        raise CanonicalReleaseReconciliationError(
            "Whisper adjudication summary has a stale evidence binding"
        )

    subset = _load_json(subset_path)
    if (
        not isinstance(subset, Mapping)
        or subset.get("schemaVersion") != ADJUDICATION_SUBSET_SCHEMA
        or not isinstance(subset.get("responses"), list)
        or subset.get("responseCount") != len(subset["responses"])
    ):
        raise CanonicalReleaseReconciliationError(
            "Whisper adjudication subset manifest is invalid"
        )
    validation = load_full_whisper_validation_evidence(
        validation_manifest=subset_path,
        receipt_path=stronger_receipt_path,
        required_model_name=ADJUDICATION_MODEL_NAME,
        required_model_revision=ADJUDICATION_MODEL_REVISION,
    )
    base_failure_manifest = _load_json(base_validation.failure_manifest_path)
    assert isinstance(base_failure_manifest, Mapping)
    ordered_base_failure_ids = [
        str(row["audio_id"])
        for row in base_failure_manifest["failures"]
    ]
    ordered_subset_ids = [
        str(row["id"])
        for row in subset["responses"]
        if isinstance(row, Mapping)
    ]
    selected_ids = set(validation.latest_events)
    if selected_ids != set(base_validation.failed_audio_ids):
        raise CanonicalReleaseReconciliationError(
            "stronger-model adjudication must exactly cover every base failure"
        )
    if (
        ordered_subset_ids != ordered_base_failure_ids
        or len(ordered_subset_ids) != len(subset["responses"])
    ):
        raise CanonicalReleaseReconciliationError(
            "stronger-model adjudication subset is not in base failure "
            "manifest order"
        )

    raw_decisions = summary.get("decisions")
    if not isinstance(raw_decisions, list):
        raise CanonicalReleaseReconciliationError(
            "Whisper adjudication decisions are required"
        )
    decisions = _index_unique(
        [dict(row) for row in raw_decisions if isinstance(row, Mapping)],
        "audio_id",
        label="Whisper adjudication decisions",
    )
    if len(decisions) != len(raw_decisions) or set(decisions) != selected_ids:
        raise CanonicalReleaseReconciliationError(
            "Whisper adjudication decisions do not exactly cover the subset"
        )
    if [
        str(row["audio_id"])
        for row in raw_decisions
        if isinstance(row, Mapping)
    ] != ordered_base_failure_ids:
        raise CanonicalReleaseReconciliationError(
            "Whisper adjudication decisions are not in base failure "
            "manifest order"
        )
    acoustic_pass_ids = {
        audio_id
        for audio_id, event in validation.latest_events.items()
        if event.get("passed") is True
    }
    passed_ids = acoustic_pass_ids - set(
        base_validation.semantic_corruption_ids
    )
    still_failed_ids = selected_ids - passed_ids
    summary_passed_ids = summary.get("adjudicated_pass_ids")
    summary_failed_ids = summary.get("still_failed_ids")
    for audio_id, decision in decisions.items():
        if (
            decision.get("adjudicated_passed") is not (
                audio_id in passed_ids
            )
            or decision.get("stronger_acoustic_passed") is not (
                audio_id in acoustic_pass_ids
            )
            or decision.get("semantic_corruption_excluded") is not (
                audio_id in base_validation.semantic_corruption_ids
            )
            or decision.get("base_validation_receipt_id")
            != base_validation.latest_events[audio_id].get(
                "validation_receipt_id"
            )
            or decision.get("stronger_validation_receipt_id")
            != validation.latest_events[audio_id].get(
                "validation_receipt_id"
            )
        ):
            raise CanonicalReleaseReconciliationError(
                f"Whisper adjudication decision mismatch for {audio_id}"
            )
    if (
        summary.get("selected_count") != len(selected_ids)
        or summary.get("adjudicated_pass_count") != len(passed_ids)
        or summary.get("still_failed_count") != len(still_failed_ids)
        or not isinstance(summary_passed_ids, list)
        or len(summary_passed_ids) != len(passed_ids)
        or summary_passed_ids
        != [
            audio_id
            for audio_id in ordered_base_failure_ids
            if audio_id in passed_ids
        ]
        or not isinstance(summary_failed_ids, list)
        or len(summary_failed_ids) != len(still_failed_ids)
        or summary_failed_ids
        != [
            audio_id
            for audio_id in ordered_base_failure_ids
            if audio_id in still_failed_ids
        ]
    ):
        raise CanonicalReleaseReconciliationError(
            "Whisper adjudication summary counts or ordered IDs are invalid"
        )
    expected_identity = (
        "abby-voice-whisper-adjudication:sha256:"
        + sha256(
            (
                base_validation.receipt_sha256
                + "\0"
                + _sha256_file(subset_path)
                + "\0"
                + validation.receipt_sha256
                + "\0"
                + ADJUDICATION_DECISION_POLICY
            ).encode()
        ).hexdigest()
    )
    if summary.get("validation_receipt_id") != expected_identity:
        raise CanonicalReleaseReconciliationError(
            "Whisper adjudication validation_receipt_id is invalid"
        )
    return WhisperAdjudicationEvidence(
        summary_path=summary_path,
        summary=dict(summary),
        validation=validation,
    )


def _ordered_strings(values: Iterable[Any]) -> list[str]:
    return sorted(
        {
            " ".join(str(value or "").split()).strip()
            for value in values
            if " ".join(str(value or "").split()).strip()
        }
    )


def _index_unique(rows: Sequence[Mapping[str, Any]], field: str, *, label: str) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        identity = str(row.get(field) or "").strip()
        if not identity:
            raise CanonicalReleaseReconciliationError(
                f"{label} row is missing {field}"
            )
        if identity in indexed:
            raise CanonicalReleaseReconciliationError(
                f"{label} contains duplicate {field} {identity!r}"
            )
        indexed[identity] = dict(row)
    return indexed


def _without_remote_urls(row: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(row)
    for field in (
        "audioUrl",
        "datasetAudioUrl",
        "mp3Url",
        "preferredAudioUrl",
    ):
        result.pop(field, None)
    return result


def _assert_no_mutable_hf_refs(value: Any, *, label: str) -> None:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True).casefold()
    if any(marker in encoded for marker in _MUTABLE_HF_MARKERS):
        raise CanonicalReleaseReconciliationError(
            f"{label} contains a mutable Hugging Face reference"
        )


def _template_record(frame: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    frame_id = str(frame.get("id") or "").strip()
    signature = " ".join(str(frame.get("responseSignature") or "").split()).strip()
    if not frame_id or not signature:
        raise CanonicalReleaseReconciliationError(
            "slotted response frame requires id and responseSignature"
        )
    segments = [" ".join(part.split()).strip() for part in signature.split("|")]
    template_text = " ".join(part for part in segments if part)
    slot_names: list[str] = []
    try:
        for _, name, format_spec, conversion in Formatter().parse(template_text):
            if name is None:
                continue
            if not name or format_spec or conversion or "." in name or "[" in name:
                raise CanonicalReleaseReconciliationError(
                    f"unsafe placeholder {name!r} in frame {frame_id}"
                )
            slot_names.append(name)
    except ValueError as exc:
        raise CanonicalReleaseReconciliationError(
            f"invalid braces in frame {frame_id}: {exc}"
        ) from exc
    unique_slots = tuple(sorted(set(slot_names)))
    routes = frame.get("routes")
    route_counts = (
        {
            str(key): int(value)
            for key, value in routes.items()
            if str(key).strip() and isinstance(value, int) and not isinstance(value, bool)
        }
        if isinstance(routes, Mapping)
        else {}
    )
    intent = (
        sorted(route_counts, key=lambda item: (-route_counts[item], item))[0]
        if route_counts
        else "template_guided_fallback"
    )
    spoken_template = normalize_indextts_spoken_text(template_text)
    canonical_template_id = stable_template_id(
        template_text,
        spoken_template,
        "en-US",
        intent,
    )
    record = {
        "consent_status": "not_required",
        "factual_slot_names": list(unique_slots),
        "intent": intent,
        "license_id": "MIT",
        "required_slot_names": list(unique_slots),
        "slot_names": list(unique_slots),
        "source_cids": _ordered_strings(frame.get("evidenceDocIds") or ()),
        "spoken_template": spoken_template,
        "template_text": template_text,
        "type": "template",
    }
    mapping = {
        "canonical_template_id": canonical_template_id,
        "frame_id": frame_id,
        "intent": intent,
        "reuse_count": int(frame.get("reuseCount") or 0),
        "slot_names": list(unique_slots),
    }
    return record, mapping


def reconcile_canonical_release(
    inputs: CanonicalReleaseInputs,
    *,
    whisper_validation: FullWhisperValidationEvidence | None = None,
    whisper_adjudication: FullWhisperValidationEvidence | None = None,
) -> CanonicalReleaseReconciliation:
    retained_rows = _load_jsonl(inputs.retained_responses)
    vocabulary_rows = _load_jsonl(inputs.vocabulary)
    frame_rows = _load_jsonl(inputs.frames)
    intent_rows = _load_jsonl(inputs.intents)
    plan = _load_json(inputs.regeneration_plan)
    generation = _load_json(inputs.regeneration_audio)
    if not isinstance(plan, Mapping) or not isinstance(generation, Mapping):
        raise CanonicalReleaseReconciliationError(
            "regeneration plan and audio manifest must be objects"
        )
    raw_supersessions = plan.get("supersession_map")
    generated_rows = generation.get("responses")
    if not isinstance(raw_supersessions, list) or not isinstance(generated_rows, list):
        raise CanonicalReleaseReconciliationError(
            "regeneration evidence is missing supersession_map or responses"
        )
    if generation.get("aggregation", {}).get("complete") is not True:
        raise CanonicalReleaseReconciliationError(
            "regeneration audio manifest is not complete"
        )

    retained_by_id = _index_unique(retained_rows, "id", label="retained responses")
    _index_unique(vocabulary_rows, "id", label="vocabulary")
    frames_by_id = _index_unique(frame_rows, "id", label="slotted frames")
    intents_by_id = _index_unique(intent_rows, "id", label="slotted intents")

    supersession_by_old: dict[str, dict[str, Any]] = {}
    for item in raw_supersessions:
        if not isinstance(item, Mapping):
            raise CanonicalReleaseReconciliationError(
                "supersession_map rows must be objects"
            )
        old_id = str(item.get("superseded_audio_id") or "").strip()
        if not old_id or old_id in supersession_by_old:
            raise CanonicalReleaseReconciliationError(
                f"invalid or duplicate superseded_audio_id {old_id!r}"
            )
        retained = retained_by_id.get(old_id)
        if retained is None or retained.get("audioAvailable") is not True:
            raise CanonicalReleaseReconciliationError(
                f"superseded audio is not an active retained row: {old_id}"
            )
        supersession_by_old[old_id] = dict(item)

    generated_by_id = _index_unique(
        [dict(row) for row in generated_rows if isinstance(row, Mapping)],
        "id",
        label="generated responses",
    )
    generation_source_sha = _sha256_file(inputs.regeneration_audio)
    if whisper_adjudication is not None and whisper_validation is None:
        raise CanonicalReleaseReconciliationError(
            "stronger-model adjudication requires base Whisper evidence"
        )
    if whisper_validation is not None:
        if (
            whisper_validation.receipt.get("manifest_sha256")
            != generation_source_sha
            or whisper_validation.receipt.get("model_name")
            != BASE_WHISPER_MODEL_NAME
            or whisper_validation.receipt.get("model_revision")
            != BASE_WHISPER_MODEL_REVISION
        ):
            raise CanonicalReleaseReconciliationError(
                "base Whisper evidence does not bind the pinned corpus/model"
            )
        if set(whisper_validation.latest_events) != set(generated_by_id):
            raise CanonicalReleaseReconciliationError(
                "base Whisper evidence does not cover the generated corpus"
            )
    if whisper_adjudication is not None:
        adjudication_ids = set(whisper_adjudication.latest_events)
        assert whisper_validation is not None
        if (
            whisper_adjudication.receipt.get("model_name")
            != ADJUDICATION_MODEL_NAME
            or whisper_adjudication.receipt.get("model_revision")
            != ADJUDICATION_MODEL_REVISION
            or adjudication_ids != whisper_validation.failed_audio_ids
        ):
            raise CanonicalReleaseReconciliationError(
                "adjudication must be the exact pinned set of all base failures"
            )
        for audio_id in adjudication_ids:
            base_event = whisper_validation.latest_events[audio_id]
            event = whisper_adjudication.latest_events[audio_id]
            if (
                event.get("audio_sha256") != base_event.get("audio_sha256")
                or event.get("expected_text_sha256")
                != base_event.get("expected_text_sha256")
            ):
                raise CanonicalReleaseReconciliationError(
                    f"adjudication evidence is content-discordant for {audio_id}"
                )

    quality_decisions: dict[str, str] = {}
    unresolved_quality_ids: set[str] = set()
    for generated_id in generated_by_id:
        if whisper_validation is None:
            quality_decisions[generated_id] = "unvalidated_candidate"
            continue
        if generated_id not in whisper_validation.failed_audio_ids:
            quality_decisions[generated_id] = "base_whisper_v3_pass"
            continue
        adjudication_event = (
            whisper_adjudication.latest_events.get(generated_id)
            if whisper_adjudication is not None
            else None
        )
        if (
            adjudication_event is not None
            and adjudication_event.get("passed") is True
        ):
            base_event = whisper_validation.latest_events[generated_id]
            if (
                adjudication_event.get("audio_sha256")
                != base_event.get("audio_sha256")
                or adjudication_event.get("expected_text_sha256")
                != base_event.get("expected_text_sha256")
            ):
                raise CanonicalReleaseReconciliationError(
                    f"adjudication evidence is content-discordant for {generated_id}"
                )
            quality_decisions[generated_id] = (
                "recovered_by_whisper_large_v3_turbo"
            )
            continue
        quality_decisions[generated_id] = (
            "excluded_unresolved_whisper_v3_failure"
        )
        unresolved_quality_ids.add(generated_id)

    old_to_generated: dict[str, str] = {}
    generated_to_old: dict[str, list[str]] = defaultdict(list)
    for generated_id, row in generated_by_id.items():
        old_ids = sorted(
            {
                str(value)
                for value in row.get("sourceIds") or ()
                if str(value) in supersession_by_old
            }
        )
        if not old_ids:
            raise CanonicalReleaseReconciliationError(
                f"generated response has no supersession binding: {generated_id}"
            )
        for old_id in old_ids:
            if old_id in old_to_generated:
                raise CanonicalReleaseReconciliationError(
                    f"superseded row has multiple replacements: {old_id}"
                )
            old_to_generated[old_id] = generated_id
            generated_to_old[generated_id].append(old_id)
    if set(old_to_generated) != set(supersession_by_old):
        raise CanonicalReleaseReconciliationError(
            "generated responses do not exactly cover the supersession map"
        )

    generated_assets: dict[str, tuple[Path, str]] = {}
    for generated_id, row in generated_by_id.items():
        path = _generated_audio_path(row)
        generated_assets[generated_id] = (path, _sha256_file(path))

    legacy_assets: dict[str, tuple[Path, str]] = {}
    for old_id, retained in supersession_by_old.items():
        retained_row = retained_by_id[old_id]
        path = _stage_audio_path(
            inputs.stage_root,
            retained_row.get("datasetAudioPath"),
            audio_id=old_id,
        )
        actual_sha256 = _sha256_file(path)
        declared_sha256 = str(
            retained_row.get("audioSha256") or ""
        ).strip().casefold()
        if actual_sha256 != declared_sha256:
            raise CanonicalReleaseReconciliationError(
                f"superseded legacy audio hash mismatch: {old_id}"
            )
        legacy_assets[old_id] = (path, actual_sha256)

    audio_paths_by_digest: dict[str, list[Path]] = defaultdict(list)
    retained_active_records: list[dict[str, Any]] = []
    generated_active_records: list[dict[str, Any]] = []
    unsafe_spoken_regeneration_rows: list[dict[str, Any]] = []
    retained_unsafe_exclusion_ids: set[str] = set()
    retained_numeric_exclusion_ids: set[str] = set()
    generated_unsafe_exclusion_ids: set[str] = set()
    active_raw_audio_ids: set[str] = set()
    active_status: dict[str, str] = {}
    for retained_id, raw in sorted(retained_by_id.items()):
        if retained_id in supersession_by_old:
            continue
        row = _without_remote_urls(raw)
        if row.get("audioAvailable") is True:
            relative = str(row.get("datasetAudioPath") or "").strip()
            expected_sha = str(row.get("audioSha256") or "").strip().lower()
            path = _stage_audio_path(
                inputs.stage_root,
                relative,
                audio_id=retained_id,
            )
            if _sha256_file(path) != expected_sha:
                raise CanonicalReleaseReconciliationError(
                    f"retained active audio failed path/hash validation: {retained_id}"
                )
            row["preferredAudioPath"] = relative
            numeric_risk_reasons = unsafe_spoken_numeric_punctuation_reasons(
                str(row.get("text") or "")
            )
            risk_reasons = unsafe_spoken_transformation_reasons(
                str(row.get("text") or "")
            )
            if risk_reasons:
                repaired_spoken_text = normalize_regeneration_spoken_text(
                    str(row.get("text") or "")
                )
                unsafe_spoken_regeneration_rows.append(
                    {
                        "excluded_audio_bytes": path.stat().st_size,
                        "excluded_audio_id": retained_id,
                        "excluded_audio_path": (
                            f"retained/audio/{retained_id}"
                            f"{path.suffix.casefold()}"
                        ),
                        "excluded_audio_sha256": expected_sha,
                        "recommendation": (
                            "regenerate_from_normalized_spoken_text"
                        ),
                        "risk_reasons": list(risk_reasons),
                        "schema_version": (
                            "abby_voice_unsafe_spoken_regeneration_queue_v1"
                        ),
                        "source_kind": "retained_audio",
                        "source_ids": _ordered_strings(
                            row.get("sourceIds") or ()
                        ),
                        "source_text_sha256": sha256(
                            str(row.get("text") or "").encode("utf-8")
                        ).hexdigest(),
                        "target_spoken_text": repaired_spoken_text,
                        "target_spoken_text_sha256": sha256(
                            repaired_spoken_text.encode("utf-8")
                        ).hexdigest(),
                    }
                )
                retained_unsafe_exclusion_ids.add(retained_id)
                if numeric_risk_reasons:
                    retained_numeric_exclusion_ids.add(retained_id)
                active_status[retained_id] = (
                    "excluded_unsafe_spoken_transformation"
                )
                row = _without_audio_locator(row)
            else:
                audio_paths_by_digest[expected_sha].append(path)
                active_raw_audio_ids.add(retained_id)
                active_status[retained_id] = "retained"
        retained_active_records.append(row)

    for generated_id, raw in sorted(generated_by_id.items()):
        row = _without_remote_urls(raw)
        inherited_rows = [
            retained_by_id[old_id]
            for old_id in generated_to_old[generated_id]
        ]
        for field in _INHERITED_LIST_FIELDS:
            row[field] = _ordered_strings(
                [
                    *(row.get(field) or ()),
                    *(
                        value
                        for inherited in inherited_rows
                        for value in (inherited.get(field) or ())
                    ),
                ]
            )
        path, digest = generated_assets[generated_id]
        row["preferredAudioPath"] = _relative(path)
        row["audioSha256"] = digest
        row["audioBytes"] = path.stat().st_size
        row["audioAvailable"] = True
        row["datasetAudioPath"] = f"audio/{generated_id}{path.suffix.casefold()}"
        generated_risk_reasons = unsafe_spoken_transformation_reasons(
            str(row.get("text") or "")
        )
        if generated_risk_reasons:
            repaired_spoken_text = normalize_regeneration_spoken_text(
                str(row.get("text") or "")
            )
            unsafe_spoken_regeneration_rows.append(
                {
                    "excluded_audio_bytes": path.stat().st_size,
                    "excluded_audio_id": generated_id,
                    "excluded_audio_path": (
                        f"regenerated/audio/{generated_id}"
                        f"{path.suffix.casefold()}"
                    ),
                    "excluded_audio_sha256": digest,
                    "recommendation": (
                        "regenerate_from_normalized_spoken_text"
                    ),
                    "risk_reasons": list(generated_risk_reasons),
                    "schema_version": (
                        "abby_voice_unsafe_spoken_regeneration_queue_v1"
                    ),
                    "source_ids": _ordered_strings(
                        row.get("sourceIds") or ()
                    ),
                    "source_kind": "generated_replacement_audio",
                    "source_text_sha256": sha256(
                        str(row.get("text") or "").encode("utf-8")
                    ).hexdigest(),
                    "target_spoken_text": repaired_spoken_text,
                    "target_spoken_text_sha256": sha256(
                        repaired_spoken_text.encode("utf-8")
                    ).hexdigest(),
                }
            )
            generated_unsafe_exclusion_ids.add(generated_id)
        if (
            generated_id in unresolved_quality_ids
            or generated_id in generated_unsafe_exclusion_ids
        ):
            row = _without_audio_locator(row)
            active_status[generated_id] = (
                "excluded_unsafe_spoken_transformation"
                if generated_id in generated_unsafe_exclusion_ids
                else quality_decisions[generated_id]
            )
        else:
            audio_paths_by_digest[digest].append(path)
            active_raw_audio_ids.add(generated_id)
            active_status[generated_id] = quality_decisions[generated_id]
        generated_active_records.append(row)

    active_records = [*retained_active_records, *generated_active_records]
    if (
        whisper_validation is not None
        and generated_unsafe_exclusion_ids
        != set(whisper_validation.semantic_corruption_ids)
    ):
        raise CanonicalReleaseReconciliationError(
            "package semantic scan does not match the bound base-v3 "
            "semantic-corruption manifest"
        )

    if set(active_raw_audio_ids) & set(supersession_by_old):
        raise CanonicalReleaseReconciliationError(
            "superseded audio IDs remain in the active set"
        )
    expected_active_audio = (
        sum(row.get("audioAvailable") is True for row in retained_rows)
        - len(supersession_by_old)
        + len(generated_by_id)
        - len(unresolved_quality_ids | generated_unsafe_exclusion_ids)
        - len(retained_unsafe_exclusion_ids)
    )
    if len(active_raw_audio_ids) != expected_active_audio:
        raise CanonicalReleaseReconciliationError(
            "active audio count does not reconcile after supersession"
        )

    template_records: list[dict[str, Any]] = []
    frame_template_rows: list[dict[str, Any]] = []
    for frame in frame_rows:
        record, mapping = _template_record(frame)
        template_records.append(record)
        frame_template_rows.append(mapping)

    retained_source_sha = _sha256_file(inputs.retained_responses)
    frames_source_sha = _sha256_file(inputs.frames)
    normalizer = AbbyVoiceDatasetNormalizer(
        NormalizationConfig(
            consent_status="not_required",
            license_id="MIT",
            locale="en-US",
            require_audio=False,
            require_grounding_for_claims=True,
        )
    )
    normalized = normalizer.normalize_sources(
        (
            (
                retained_active_records,
                "source://retained/abby_tts_responses.jsonl",
                retained_source_sha,
                inputs.stage_root,
            ),
            (
                generated_active_records,
                "source://regeneration/regeneration-audio-manifest.json",
                generation_source_sha,
                REPO_ROOT,
            ),
            (
                {"templates": template_records},
                "source://templates/abby_tts_slotted_response_frames.jsonl",
                frames_source_sha,
                None,
            ),
        )
    )
    bundle = AbbyVoiceDatasetBundle(
        responses=normalized.responses,
        templates=normalized.templates,
        audio=normalized.audio,
        provenance=normalized.provenance,
    )
    validate_publishable(bundle)
    if len(bundle.audio) != expected_active_audio:
        raise CanonicalReleaseReconciliationError(
            f"canonical audio count mismatch: expected {expected_active_audio}, "
            f"got {len(bundle.audio)}"
        )
    unsafe_canonical_audio = [
        row.audio_id
        for row in bundle.audio
        if unsafe_spoken_transformation_reasons(row.spoken_text)
    ]
    if unsafe_canonical_audio:
        raise CanonicalReleaseReconciliationError(
            "canonical audio retained unsafe spoken transformation text: "
            + ", ".join(sorted(unsafe_canonical_audio)[:10])
        )
    canonical_template_by_identity = {
        normalized_text_identity(row.spoken_template or ""): row
        for row in bundle.templates
    }
    expected_template_identities = {
        normalized_text_identity(
            normalize_indextts_spoken_text(str(record["spoken_template"]))
        )
        for record in template_records
    }
    if (
        len(canonical_template_by_identity) != len(bundle.templates)
        or len(bundle.templates) != len(expected_template_identities)
    ):
        raise CanonicalReleaseReconciliationError(
            "canonical templates do not exactly cover the unique retained "
            "slotted response-frame identities"
        )
    for record, mapping in zip(
        template_records,
        frame_template_rows,
        strict=True,
    ):
        identity = normalized_text_identity(
            normalize_indextts_spoken_text(str(record["spoken_template"]))
        )
        canonical = canonical_template_by_identity[identity]
        proposed_id = str(mapping["canonical_template_id"])
        mapping["canonical_template_id"] = canonical.template_id
        mapping["deduplicated_into_survivor"] = (
            proposed_id != canonical.template_id
        )
        mapping["normalized_template_identity_sha256"] = sha256(
            identity.encode("utf-8")
        ).hexdigest()

    audio_sources: dict[str, Path] = {}
    for audio in bundle.audio:
        candidates = sorted(set(audio_paths_by_digest.get(audio.content_sha256, ())))
        if not candidates:
            raise CanonicalReleaseReconciliationError(
                f"canonical audio has no pinned local source: {audio.audio_id}"
            )
        audio_sources[audio.audio_id] = candidates[0]
    if len(audio_sources) != expected_active_audio:
        raise CanonicalReleaseReconciliationError(
            "canonical audio source map is incomplete"
        )
    canonical_audio_by_digest = {
        row.content_sha256: row for row in bundle.audio
    }
    canonical_response_by_id = {
        row.response_id: row for row in bundle.responses
    }
    runtime_precomputed_audio_rows_list: list[dict[str, Any]] = []
    for row in sorted(
        active_records,
        key=lambda item: str(item.get("id") or ""),
    ):
        if row.get("audioAvailable") is not True:
            continue
        raw_response_id = str(row.get("id") or "").strip()
        audio_sha256 = str(row.get("audioSha256") or "").strip().casefold()
        canonical_audio = canonical_audio_by_digest.get(audio_sha256)
        if canonical_audio is None or canonical_audio.response_id is None:
            raise CanonicalReleaseReconciliationError(
                "active runtime row has no canonical audio/response binding: "
                f"{raw_response_id}"
            )
        canonical_response = canonical_response_by_id.get(
            canonical_audio.response_id
        )
        if canonical_response is None:
            raise CanonicalReleaseReconciliationError(
                "active runtime row references an unknown canonical response: "
                f"{raw_response_id}"
            )
        source_path = audio_sources[canonical_audio.audio_id]
        extension = source_path.suffix.casefold()
        if extension not in {".mp3", ".wav", ".flac", ".ogg", ".m4a"}:
            raise CanonicalReleaseReconciliationError(
                f"unsupported runtime audio extension: {extension}"
            )
        runtime_precomputed_audio_rows_list.append(
            {
                "audioBytes": canonical_audio.byte_length,
                "audioSha256": canonical_audio.content_sha256,
                "canonicalAudioId": canonical_audio.audio_id,
                "canonicalResponseId": canonical_response.response_id,
                "id": raw_response_id,
                "locationTags": _ordered_strings(
                    (
                        *(row.get("locationTags") or ()),
                        *canonical_response.location_tags,
                    )
                ),
                "originalTexts": _ordered_strings(
                    (
                        *(row.get("originalTexts") or ()),
                        canonical_response.text,
                    )
                ),
                "preferredAudioUrl": (
                    f"../assets/audio/{canonical_audio.audio_id}{extension}"
                ),
                "preferredMimeType": canonical_audio.mime_type,
                "rawResponseId": raw_response_id,
                "routes": _ordered_strings(
                    (
                        *(row.get("routes") or ()),
                        *canonical_response.route_labels,
                    )
                ),
                "serviceTags": _ordered_strings(
                    (
                        *(row.get("serviceTags") or ()),
                        *canonical_response.service_tags,
                    )
                ),
                "slottedCanonicalQueryTemplates": _ordered_strings(
                    row.get("slottedCanonicalQueryTemplates") or ()
                ),
                "slottedEdgeIds": _ordered_strings(
                    row.get("slottedEdgeIds") or ()
                ),
                "slottedIntentIds": _ordered_strings(
                    row.get("slottedIntentIds") or ()
                ),
                "slottedResponseFrameIds": _ordered_strings(
                    row.get("slottedResponseFrameIds") or ()
                ),
                "slottedResponseSignatures": _ordered_strings(
                    row.get("slottedResponseSignatures") or ()
                ),
                "sourceIds": _ordered_strings(row.get("sourceIds") or ()),
                "status": "active_immutable_release",
                "text": canonical_audio.spoken_text,
                "textSha256": canonical_audio.text_sha256,
            }
        )
    runtime_precomputed_audio_rows = tuple(
        runtime_precomputed_audio_rows_list
    )
    if len(runtime_precomputed_audio_rows) != expected_active_audio:
        raise CanonicalReleaseReconciliationError(
            "runtime precomputed-audio manifest does not exactly cover active "
            "safe audio"
        )
    _assert_publication_support_safe(
        runtime_precomputed_audio_rows,
        label="runtime precomputed-audio rows",
    )

    active_links = tuple(
        {
            "active_audio": bool(row.get("audioAvailable")),
            "active_status": active_status.get(str(row.get("id") or ""), "planned_only"),
            "canonical_query_templates": _ordered_strings(
                row.get("slottedCanonicalQueryTemplates") or ()
            ),
            "intent_ids": _ordered_strings(row.get("slottedIntentIds") or ()),
            "raw_response_id": str(row.get("id") or ""),
            "response_frame_ids": _ordered_strings(
                row.get("slottedResponseFrameIds") or ()
            ),
            "text_sha256": sha256(
                str(row.get("text") or "").encode("utf-8")
            ).hexdigest(),
        }
        for row in sorted(active_records, key=lambda item: str(item.get("id") or ""))
    )
    referenced_frames = {
        frame_id
        for row in active_links
        for frame_id in row["response_frame_ids"]
    }
    referenced_intents = {
        intent_id for row in active_links for intent_id in row["intent_ids"]
    }
    if referenced_frames - set(frames_by_id):
        raise CanonicalReleaseReconciliationError(
            "active responses reference unknown slotted response frames"
        )
    if referenced_intents - set(intents_by_id):
        raise CanonicalReleaseReconciliationError(
            "active responses reference unknown slotted intents"
        )

    supersession_rows_list: list[dict[str, Any]] = []
    for old_id in sorted(supersession_by_old):
        replacement_id = old_to_generated[old_id]
        old_path, old_sha256 = legacy_assets[old_id]
        replacement_path, replacement_sha256 = generated_assets[replacement_id]
        replacement_row = generated_by_id[replacement_id]
        canonical_audio = canonical_audio_by_digest.get(replacement_sha256)
        base_event = (
            whisper_validation.latest_events.get(replacement_id)
            if whisper_validation is not None
            else None
        )
        adjudication_event = (
            whisper_adjudication.latest_events.get(replacement_id)
            if whisper_adjudication is not None
            else None
        )
        supersession_rows_list.append(
            {
                **supersession_by_old[old_id],
                "base_validation_item_id": (
                    base_event.get("validation_receipt_id")
                    if base_event is not None
                    else None
                ),
                "legacy_audio_bytes": old_path.stat().st_size,
                "legacy_audio_path": (
                    f"retained/audio/{old_id}{old_path.suffix.casefold()}"
                ),
                "legacy_audio_sha256": old_sha256,
                "legacy_normalized_text_sha256": sha256(
                    normalize_indextts_spoken_text(
                        str(retained_by_id[old_id].get("text") or "")
                    ).encode("utf-8")
                ).hexdigest(),
                "quality_decision": (
                    "excluded_unsafe_spoken_transformation"
                    if replacement_id in generated_unsafe_exclusion_ids
                    else quality_decisions[replacement_id]
                ),
                "replacement_active": replacement_id not in (
                    unresolved_quality_ids | generated_unsafe_exclusion_ids
                ),
                "replacement_adjudication_item_id": (
                    adjudication_event.get("validation_receipt_id")
                    if adjudication_event is not None
                    else None
                ),
                "replacement_audio_bytes": replacement_path.stat().st_size,
                "replacement_audio_id": replacement_id,
                "replacement_audio_path": (
                    f"regenerated/audio/{replacement_id}"
                    f"{replacement_path.suffix.casefold()}"
                ),
                "replacement_audio_sha256": replacement_sha256,
                "replacement_normalized_text_sha256": sha256(
                    normalize_indextts_spoken_text(
                        str(replacement_row.get("text") or "")
                    ).encode("utf-8")
                ).hexdigest(),
                "replacement_release_audio_id": (
                    canonical_audio.audio_id
                    if canonical_audio is not None
                    else None
                ),
                "replacement_release_audio_path": (
                    f"assets/audio/{canonical_audio.audio_id}"
                    f"{replacement_path.suffix.casefold()}"
                    if canonical_audio is not None
                    else None
                ),
                "replacement_text_sha256": sha256(
                    str(replacement_row.get("text") or "").encode("utf-8")
                ).hexdigest(),
                "schema_version": "abby_voice_supersession_evidence_v2",
            }
        )
    supersession_rows = tuple(supersession_rows_list)
    excluded_audio_rows = tuple(
        {
            "legacy_audio_id": old_id,
            "legacy_audio_path": (
                f"retained/audio/{old_id}"
                f"{legacy_assets[old_id][0].suffix.casefold()}"
            ),
            "legacy_audio_sha256": legacy_assets[old_id][1],
            "replacement_audio_id": old_to_generated[old_id],
            "schema_version": "abby_voice_excluded_legacy_audio_v2",
            "status": "excluded_superseded_quality_repair",
        }
        for old_id in sorted(supersession_by_old)
    )
    quality_exclusion_rows = tuple(
        {
            "audio_bytes": generated_assets[audio_id][0].stat().st_size,
            "audio_id": audio_id,
            "audio_path": (
                f"regenerated/audio/{audio_id}"
                f"{generated_assets[audio_id][0].suffix.casefold()}"
            ),
            "audio_sha256": generated_assets[audio_id][1],
            "base_validation_item_id": (
                whisper_validation.latest_events[audio_id].get(
                    "validation_receipt_id"
                )
                if whisper_validation is not None
                else None
            ),
            "expected_text_sha256": sha256(
                str(generated_by_id[audio_id].get("text") or "").encode("utf-8")
            ).hexdigest(),
            "schema_version": "abby_voice_quality_audio_exclusion_v2",
            "status": quality_decisions[audio_id],
        }
        for audio_id in sorted(unresolved_quality_ids)
    )
    regeneration_inventory_rows = tuple(
        {
            "audio_bytes": generated_assets[audio_id][0].stat().st_size,
            "audio_id": audio_id,
            "audio_path": (
                f"regenerated/audio/{audio_id}"
                f"{generated_assets[audio_id][0].suffix.casefold()}"
            ),
            "audio_sha256": generated_assets[audio_id][1],
            "base_validation_item_id": (
                whisper_validation.latest_events[audio_id].get(
                    "validation_receipt_id"
                )
                if whisper_validation is not None
                else None
            ),
            "expected_text_sha256": sha256(
                str(generated_by_id[audio_id].get("text") or "").encode("utf-8")
            ).hexdigest(),
            "quality_decision": (
                "excluded_unsafe_spoken_transformation"
                if audio_id in generated_unsafe_exclusion_ids
                else quality_decisions[audio_id]
            ),
            "schema_version": "abby_voice_regeneration_audio_inventory_v2",
            "source_ids": _ordered_strings(
                generated_by_id[audio_id].get("sourceIds") or ()
            ),
            "stronger_validation_item_id": (
                whisper_adjudication.latest_events[audio_id].get(
                    "validation_receipt_id"
                )
                if (
                    whisper_adjudication is not None
                    and audio_id in whisper_adjudication.latest_events
                )
                else None
            ),
        }
        for audio_id in sorted(generated_by_id)
    )
    unsafe_spoken_regeneration_queue = tuple(
        sorted(
            unsafe_spoken_regeneration_rows,
            key=lambda item: (
                str(item["excluded_audio_id"]),
                str(item["source_kind"]),
            ),
        )
    )
    if any(
        unsafe_spoken_transformation_reasons(
            str(item["target_spoken_text"])
        )
        for item in unsafe_spoken_regeneration_queue
    ):
        raise CanonicalReleaseReconciliationError(
            "unsafe-spoken regeneration queue contains an unsafe repair target"
        )
    retained_numeric_ids_sha256 = sha256(
        "".join(
            f"{audio_id}\n"
            for audio_id in sorted(retained_numeric_exclusion_ids)
        ).encode("utf-8")
    ).hexdigest()
    retained_unsafe_ids_sha256 = sha256(
        "".join(
            f"{audio_id}\n"
            for audio_id in sorted(retained_unsafe_exclusion_ids)
        ).encode("utf-8")
    ).hexdigest()
    retained_apostrophe_direction_ids = {
        str(item["excluded_audio_id"])
        for item in unsafe_spoken_regeneration_queue
        if (
            item["source_kind"] == "retained_audio"
            and "apostrophe_direction_corruption" in item["risk_reasons"]
        )
    }
    retained_apostrophe_direction_ids_sha256 = sha256(
        "".join(
            f"{audio_id}\n"
            for audio_id in sorted(retained_apostrophe_direction_ids)
        ).encode("utf-8")
    ).hexdigest()
    generated_unsafe_ids_sha256 = sha256(
        "".join(
            f"{audio_id}\n"
            for audio_id in sorted(generated_unsafe_exclusion_ids)
        ).encode("utf-8")
    ).hexdigest()
    unsafe_spoken_reason_counts: dict[str, int] = defaultdict(int)
    for item in unsafe_spoken_regeneration_queue:
        for reason in item["risk_reasons"]:
            unsafe_spoken_reason_counts[str(reason)] += 1
    source_paths = {
        "bucket_audio_objects": inputs.bucket_objects,
        "regeneration_audio_manifest": inputs.regeneration_audio,
        "regeneration_plan": inputs.regeneration_plan,
        "retained_responses": inputs.retained_responses,
        "slotted_intents": inputs.intents,
        "slotted_response_dag": inputs.slotted_dag,
        "slotted_response_frames": inputs.frames,
        "vocabulary": inputs.vocabulary,
    }
    source_digests = {
        label: _sha256_file(path) for label, path in source_paths.items()
    }
    if whisper_validation is not None:
        source_digests.update(
            {
                "whisper_base_failure_manifest": (
                    whisper_validation.failure_manifest_sha256
                ),
                "whisper_base_ledger": whisper_validation.ledger_sha256,
                "whisper_base_receipt": whisper_validation.receipt_sha256,
            }
        )
        if (
            whisper_validation.semantic_corruption_manifest_sha256
            is not None
        ):
            source_digests[
                "whisper_base_semantic_corruption_manifest"
            ] = whisper_validation.semantic_corruption_manifest_sha256
    if whisper_adjudication is not None:
        source_digests.update(
            {
                "whisper_adjudication_failure_manifest": (
                    whisper_adjudication.failure_manifest_sha256
                ),
                "whisper_adjudication_ledger": (
                    whisper_adjudication.ledger_sha256
                ),
                "whisper_adjudication_receipt": (
                    whisper_adjudication.receipt_sha256
                ),
            }
        )
    audit = {
        "active_audio_count": len(bundle.audio),
        "active_raw_audio_count": len(active_raw_audio_ids),
        "base_whisper_all_passed": (
            whisper_validation.receipt.get("all_passed")
            if whisper_validation is not None
            else None
        ),
        "base_whisper_failed_count": (
            len(whisper_validation.failed_audio_ids)
            if whisper_validation is not None
            else None
        ),
        "base_whisper_validation_receipt_id": (
            whisper_validation.validation_receipt_id
            if whisper_validation is not None
            else None
        ),
        "canonical_provenance_count": len(bundle.provenance),
        "canonical_response_count": len(bundle.responses),
        "canonical_template_count": len(bundle.templates),
        "deduplicated_response_frame_template_count": (
            len(frame_rows) - len(bundle.templates)
        ),
        "excluded_superseded_audio_count": len(excluded_audio_rows),
        "excluded_whisper_quality_audio_count": len(quality_exclusion_rows),
        "generated_replacement_count": len(generated_by_id),
        "intent_count": len(intent_rows),
        "normalization_input_count": normalized.input_record_count,
        "normalization_quarantine_count": len(normalized.quarantine),
        "normalization_warning_count": len(normalized.warnings),
        "publication_ready": (
            whisper_validation is not None
            and (
                not whisper_validation.failed_audio_ids
                or whisper_adjudication is not None
            )
        ),
        "referenced_intent_count": len(referenced_intents),
        "referenced_response_frame_count": len(referenced_frames),
        "recovered_by_adjudication_count": sum(
            decision == "recovered_by_whisper_large_v3_turbo"
            for decision in quality_decisions.values()
        ),
        "response_frame_count": len(frame_rows),
        "runtime_precomputed_audio_count": len(
            runtime_precomputed_audio_rows
        ),
        "generated_unsafe_spoken_exclusion_count": len(
            generated_unsafe_exclusion_ids
        ),
        "generated_unsafe_spoken_exclusion_ids_sha256": (
            generated_unsafe_ids_sha256
        ),
        "retained_apostrophe_direction_exclusion_count": len(
            retained_apostrophe_direction_ids
        ),
        "retained_apostrophe_direction_exclusion_ids_sha256": (
            retained_apostrophe_direction_ids_sha256
        ),
        "retained_apostrophe_direction_exclusion_population_rule": (
            "retained row text where audioAvailable is true, audio ID is "
            "absent from regeneration-full-plan supersession_map, and "
            "unsafe_spoken_transformation_reasons(text) contains "
            "apostrophe_direction_corruption; bind sorted full audio IDs "
            "as UTF-8 with one trailing LF per ID"
        ),
        "retained_numeric_punctuation_exclusion_count": len(
            retained_numeric_exclusion_ids
        ),
        "retained_numeric_punctuation_exclusion_ids_sha256": (
            retained_numeric_ids_sha256
        ),
        "retained_unsafe_spoken_exclusion_count": len(
            retained_unsafe_exclusion_ids
        ),
        "retained_unsafe_spoken_exclusion_ids_sha256": (
            retained_unsafe_ids_sha256
        ),
        "unsafe_spoken_regeneration_queue_count": len(
            unsafe_spoken_regeneration_queue
        ),
        "unsafe_spoken_transformation_reason_counts": dict(
            sorted(unsafe_spoken_reason_counts.items())
        ),
        "schema_version": "abby_voice_canonical_reconciliation_v2",
        "source_digests": dict(sorted(source_digests.items())),
        "stronger_whisper_validation_receipt_id": (
            whisper_adjudication.validation_receipt_id
            if whisper_adjudication is not None
            else None
        ),
        "supersession_count": len(supersession_rows),
        "superseded_audio_active_count": 0,
        "unvalidated_generated_audio_count": sum(
            decision == "unvalidated_candidate"
            for decision in quality_decisions.values()
        ),
        "vocabulary_count": len(vocabulary_rows),
    }
    _assert_no_mutable_hf_refs(audit, label="canonical reconciliation audit")
    return CanonicalReleaseReconciliation(
        bundle=bundle,
        audio_sources=audio_sources,
        active_links=active_links,
        supersession_rows=supersession_rows,
        excluded_audio_rows=excluded_audio_rows,
        quality_exclusion_rows=quality_exclusion_rows,
        unsafe_spoken_regeneration_rows=unsafe_spoken_regeneration_queue,
        regeneration_inventory_rows=regeneration_inventory_rows,
        runtime_precomputed_audio_rows=runtime_precomputed_audio_rows,
        frame_template_rows=tuple(
            sorted(frame_template_rows, key=lambda item: str(item["frame_id"]))
        ),
        audit=audit,
    )


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        ).encode("utf-8")
        + b"\n"
    )


def _write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> int:
    ordered = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = b"".join(canonical_json_bytes(dict(row)) + b"\n" for row in ordered)
    path.write_bytes(payload)
    return len(ordered)


def _assert_publication_support_safe(value: Any, *, label: str) -> None:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True).casefold()
    markers = (
        *_MUTABLE_HF_MARKERS,
        "/home/",
        "/tmp/",
        "file://",
        "tmp_assets",
        ".worktrees/",
    )
    if any(marker in encoded for marker in markers):
        raise CanonicalReleaseReconciliationError(
            f"{label} contains a mutable or local execution path"
        )


def _sanitized_bucket_rows(
    rows: Iterable[Mapping[str, Any]],
) -> tuple[Mapping[str, Any], ...]:
    sanitized: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        raw_source_ref = str(item.pop("sourceRef", "") or "")
        if raw_source_ref:
            path_part, separator, fragment = raw_source_ref.partition("#")
            source_name = Path(path_part).name or "source-manifest"
            item["sourceRef"] = (
                f"source-manifests/{source_name}"
                + (f"#{fragment}" if separator else "")
            )
            item["sourceRefSha256"] = sha256(
                raw_source_ref.encode("utf-8")
            ).hexdigest()
        sanitized.append(item)
    result = tuple(
        sorted(
            sanitized,
            key=lambda item: (
                str(item.get("bucketPath") or ""),
                str(item.get("subjectId") or ""),
                str(item.get("sourceRefSha256") or ""),
            ),
        )
    )
    _assert_publication_support_safe(result, label="sanitized bucket inventory")
    return result


def _validation_publication_binding(
    evidence: FullWhisperValidationEvidence,
    *,
    role: str,
) -> dict[str, Any]:
    excluded_paths = {
        "failed_item_manifest",
        "ledger",
        "manifest",
        "semantic_corruption_manifest",
    }
    payload = {
        key: value
        for key, value in evidence.receipt.items()
        if key not in excluded_paths and key != "schema_version"
    }
    payload.update(
        {
            "evidence_role": role,
            "failure_manifest_sha256": evidence.failure_manifest_sha256,
            "ledger_sha256": evidence.ledger_sha256,
            "manifest_sha256": evidence.receipt["manifest_sha256"],
            "schema_version": "abby_voice_whisper_publication_binding_v1",
            "source_receipt_schema_version": evidence.receipt["schema_version"],
            "source_receipt_sha256": evidence.receipt_sha256,
        }
    )
    _assert_publication_support_safe(payload, label=f"{role} publication binding")
    return payload


def _validation_decision_rows(
    evidence: FullWhisperValidationEvidence,
    *,
    role: str,
) -> tuple[Mapping[str, Any], ...]:
    fields = (
        "asr_model",
        "audio_id",
        "audio_sha256",
        "content_word_coverage_bp",
        "device",
        "dtype",
        "expected_text_sha256",
        "forbidden_negative_detected",
        "manifest_index",
        "model_revision",
        "normalized_similarity_bp",
        "numeric_sequences_match",
        "passed",
        "run_fingerprint",
        "shard_count",
        "shard_index",
        "status",
        "transcript_sha256",
        "validation_receipt_id",
        "validator_version",
        "wer_bp",
    )
    rows = tuple(
        {
            **{
                field: event[field]
                for field in fields
                if field in event
            },
            "decision": (
                "accepted_by_gate"
                if event.get("passed") is True
                else "failed_gate"
            ),
            "evidence_role": role,
            "schema_version": "abby_voice_whisper_publication_item_v1",
        }
        for _, event in sorted(evidence.latest_events.items())
    )
    _assert_publication_support_safe(rows, label=f"{role} decision ledger")
    return rows


def _sanitized_adjudication_summary(
    evidence: WhisperAdjudicationEvidence,
) -> dict[str, Any]:
    excluded_paths = {
        "base_failure_manifest",
        "base_validation_receipt",
        "semantic_corruption_manifest",
        "stronger_validation_receipt",
        "subset_manifest",
    }
    payload = {
        key: value
        for key, value in evidence.summary.items()
        if key not in excluded_paths and key != "schema_version"
    }
    payload.update(
        {
            "schema_version": "abby_voice_whisper_adjudication_binding_v1",
            "source_schema_version": evidence.summary["schema_version"],
            "source_summary_sha256": evidence.summary_sha256,
        }
    )
    _assert_publication_support_safe(payload, label="adjudication summary")
    return payload


def _sanitized_adjudication_subset(
    evidence: WhisperAdjudicationEvidence,
) -> tuple[Mapping[str, Any], ...]:
    subset = _load_json(evidence.validation.manifest_path)
    assert isinstance(subset, Mapping)
    rows = []
    for raw in subset["responses"]:
        assert isinstance(raw, Mapping)
        audio_id = str(raw.get("id") or "")
        event = evidence.validation.latest_events[audio_id]
        rows.append(
            {
                "audio_id": audio_id,
                "audio_path": f"regenerated/audio/{audio_id}.mp3",
                "audio_sha256": event["audio_sha256"],
                "base_validation": dict(raw.get("baseValidation") or {}),
                "expected_text_sha256": event["expected_text_sha256"],
                "schema_version": (
                    "abby_voice_whisper_adjudication_subset_item_v1"
                ),
                "source_ids": _ordered_strings(raw.get("sourceIds") or ()),
            }
        )
    result = tuple(rows)
    _assert_publication_support_safe(result, label="adjudication subset")
    return result


def _support_source(
    *,
    source: Path,
    relative_path: str,
    schema_type: str,
    row_count: int | None = None,
    kind: str,
) -> AbbyVoiceReleaseSupportSource:
    return AbbyVoiceReleaseSupportSource(
        relative_path=relative_path,
        source_path=source,
        expected_sha256=_sha256_file(source),
        media_type=(
            "application/x-ndjson"
            if source.suffix.casefold() == ".jsonl"
            else "application/json"
        ),
        schema_type=schema_type,
        row_count=row_count,
        metadata={"kind": kind},
    )


def build_canonical_release(
    *,
    inputs: CanonicalReleaseInputs,
    output_root: Path,
    whisper_receipt: Path,
    whisper_adjudication_summary: Path | None = None,
    release_id: str | None = None,
    repository_commit: str = "commit:local-abby-voice-canonical-v2",
    shard_rows: int = 4096,
) -> dict[str, Any]:
    base_validation = load_full_whisper_validation_evidence(
        validation_manifest=inputs.regeneration_audio,
        receipt_path=whisper_receipt,
        required_model_name=BASE_WHISPER_MODEL_NAME,
        required_model_revision=BASE_WHISPER_MODEL_REVISION,
        require_semantic_manifest=True,
    )
    adjudication: WhisperAdjudicationEvidence | None = None
    if base_validation.failed_audio_ids:
        if whisper_adjudication_summary is None:
            raise CanonicalReleaseReconciliationError(
                "every base-v3 failure requires complete pinned stronger-model "
                "adjudication before release sealing"
            )
        adjudication = load_whisper_adjudication_evidence(
            base_validation=base_validation,
            summary_path=whisper_adjudication_summary,
        )
    elif whisper_adjudication_summary is not None:
        raise CanonicalReleaseReconciliationError(
            "adjudication evidence is not accepted when the base corpus passed"
        )
    reconciliation = reconcile_canonical_release(
        inputs,
        whisper_validation=base_validation,
        whisper_adjudication=(
            adjudication.validation if adjudication is not None else None
        ),
    )
    if reconciliation.audit.get("publication_ready") is not True:
        raise CanonicalReleaseReconciliationError(
            "canonical reconciliation is not publication-ready"
        )
    identity = {
        "audit": reconciliation.audit,
        "audio": [
            {
                "audio_id": row.audio_id,
                "content_sha256": row.content_sha256,
                "text_sha256": row.text_sha256,
            }
            for row in reconciliation.bundle.audio
        ],
        "policy": {
            "consent_status": "not_required",
            "license_id": "MIT",
            "shard_rows": shard_rows,
        },
        "schema_version": "abby_voice_canonical_release_identity_v2",
        "validation_evidence": {
            "base_receipt_sha256": base_validation.receipt_sha256,
            "base_validation_receipt_id": (
                base_validation.validation_receipt_id
            ),
            "stronger_adjudication_summary_sha256": (
                adjudication.summary_sha256
                if adjudication is not None
                else None
            ),
            "stronger_validation_receipt_id": (
                adjudication.validation.validation_receipt_id
                if adjudication is not None
                else None
            ),
        },
    }
    identity_sha256 = sha256(canonical_json_bytes(identity)).hexdigest()
    selected_release_id = (
        str(release_id).strip()
        if release_id is not None
        else f"abby-voice-v2-{identity_sha256[:20]}"
    )
    release_dir = output_root.expanduser().resolve() / selected_release_id

    with tempfile.TemporaryDirectory(
        prefix="abby-voice-release-support-"
    ) as temporary_name:
        temporary = Path(temporary_name)
        active_links_path = temporary / "active-response-links.jsonl"
        supersession_path = temporary / "supersession-map.jsonl"
        excluded_path = temporary / "excluded-legacy-audio.jsonl"
        quality_exclusion_path = temporary / "excluded-whisper-audio.jsonl"
        unsafe_spoken_queue_path = temporary / "unsafe-spoken-regeneration.jsonl"
        regeneration_inventory_path = temporary / "regeneration-inventory.jsonl"
        bucket_inventory_path = temporary / "bucket-audio-inventory.jsonl"
        regeneration_plan_path = temporary / "regeneration-plan.json"
        frame_map_path = temporary / "frame-template-map.jsonl"
        runtime_precomputed_audio_path = (
            temporary / "runtime-precomputed-audio-manifest.json"
        )
        audit_path = temporary / "reconciliation-audit.json"
        base_binding_path = temporary / "whisper-base-binding.json"
        base_decisions_path = temporary / "whisper-base-decisions.jsonl"
        base_failures_path = temporary / "whisper-base-failures.json"
        base_semantic_corruptions_path = (
            temporary / "whisper-base-semantic-corruptions.json"
        )
        _write_jsonl(active_links_path, reconciliation.active_links)
        _write_jsonl(supersession_path, reconciliation.supersession_rows)
        _write_jsonl(excluded_path, reconciliation.excluded_audio_rows)
        _write_jsonl(
            quality_exclusion_path,
            reconciliation.quality_exclusion_rows,
        )
        _write_jsonl(
            unsafe_spoken_queue_path,
            reconciliation.unsafe_spoken_regeneration_rows,
        )
        _write_jsonl(
            regeneration_inventory_path,
            reconciliation.regeneration_inventory_rows,
        )
        bucket_rows = _sanitized_bucket_rows(
            _load_jsonl(inputs.bucket_objects)
        )
        _write_jsonl(bucket_inventory_path, bucket_rows)
        regeneration_plan = _load_json(inputs.regeneration_plan)
        _assert_publication_support_safe(
            regeneration_plan,
            label="regeneration plan",
        )
        _write_json(regeneration_plan_path, regeneration_plan)
        _write_jsonl(frame_map_path, reconciliation.frame_template_rows)
        runtime_precomputed_audio_manifest = {
            "audioBase": "../assets/audio/",
            "immutableReleaseOnly": True,
            "responseCount": len(
                reconciliation.runtime_precomputed_audio_rows
            ),
            "responses": list(
                reconciliation.runtime_precomputed_audio_rows
            ),
            "schemaVersion": (
                "abby_voice_runtime_precomputed_audio_manifest_v2"
            ),
        }
        _assert_publication_support_safe(
            runtime_precomputed_audio_manifest,
            label="runtime precomputed-audio manifest",
        )
        _write_json(
            runtime_precomputed_audio_path,
            runtime_precomputed_audio_manifest,
        )
        _write_json(audit_path, reconciliation.audit)
        _write_json(
            base_binding_path,
            _validation_publication_binding(
                base_validation,
                role="base_whisper_v3",
            ),
        )
        base_decision_rows = _validation_decision_rows(
            base_validation,
            role="base_whisper_v3",
        )
        _write_jsonl(base_decisions_path, base_decision_rows)
        base_failure_manifest = _load_json(
            base_validation.failure_manifest_path
        )
        _assert_publication_support_safe(
            base_failure_manifest,
            label="base Whisper failure manifest",
        )
        _write_json(base_failures_path, base_failure_manifest)
        if base_validation.semantic_corruption_manifest_path is None:
            raise CanonicalReleaseReconciliationError(
                "base semantic-corruption evidence is required"
            )
        base_semantic_corruptions = _load_json(
            base_validation.semantic_corruption_manifest_path
        )
        _assert_publication_support_safe(
            base_semantic_corruptions,
            label="base Whisper semantic-corruption manifest",
        )
        _write_json(
            base_semantic_corruptions_path,
            base_semantic_corruptions,
        )

        support_sources = [
            _support_source(
                source=inputs.vocabulary,
                relative_path="metadata/retained-vocabulary.jsonl",
                schema_type="abby_tts_vocabulary_v1",
                row_count=int(reconciliation.audit["vocabulary_count"]),
                kind="retained_vocabulary",
            ),
            _support_source(
                source=inputs.frames,
                relative_path="metadata/retained-slotted-response-frames.jsonl",
                schema_type="abby_tts_slotted_response_frames_v1",
                row_count=int(reconciliation.audit["response_frame_count"]),
                kind="retained_slotted_response_frames",
            ),
            _support_source(
                source=inputs.intents,
                relative_path="metadata/retained-slotted-intents.jsonl",
                schema_type="abby_tts_slotted_intents_v1",
                row_count=int(reconciliation.audit["intent_count"]),
                kind="retained_slotted_intents",
            ),
            _support_source(
                source=bucket_inventory_path,
                relative_path="metadata/retained-bucket-audio-objects.jsonl",
                schema_type="abby_tts_bucket_audio_objects_publication_v2",
                row_count=len(bucket_rows),
                kind="retained_bucket_audio_inventory",
            ),
            _support_source(
                source=inputs.slotted_dag,
                relative_path="manifests/retained/slotted-response-dag.json",
                schema_type="abby_tts_slotted_response_dag_v1",
                kind="retained_slotted_response_dag",
            ),
            _support_source(
                source=regeneration_plan_path,
                relative_path="manifests/retained/regeneration-plan.json",
                schema_type="abby_voice_regeneration_plan_v1",
                kind="regeneration_plan",
            ),
            _support_source(
                source=regeneration_inventory_path,
                relative_path="metadata/regeneration-audio-inventory.jsonl",
                schema_type="abby_voice_regeneration_audio_inventory_v2",
                row_count=len(reconciliation.regeneration_inventory_rows),
                kind="regeneration_audio_inventory",
            ),
            _support_source(
                source=active_links_path,
                relative_path="metadata/active-response-links.jsonl",
                schema_type="abby_voice_active_response_links_v2",
                row_count=len(reconciliation.active_links),
                kind="active_response_links",
            ),
            _support_source(
                source=supersession_path,
                relative_path="metadata/supersession-map.jsonl",
                schema_type="abby_voice_supersession_map_v1",
                row_count=len(reconciliation.supersession_rows),
                kind="supersession_map",
            ),
            _support_source(
                source=excluded_path,
                relative_path="metadata/excluded-legacy-audio.jsonl",
                schema_type="abby_voice_excluded_legacy_audio_v2",
                row_count=len(reconciliation.excluded_audio_rows),
                kind="excluded_legacy_audio",
            ),
            _support_source(
                source=quality_exclusion_path,
                relative_path="metadata/excluded-whisper-audio.jsonl",
                schema_type="abby_voice_quality_audio_exclusion_v2",
                row_count=len(reconciliation.quality_exclusion_rows),
                kind="excluded_whisper_audio",
            ),
            _support_source(
                source=unsafe_spoken_queue_path,
                relative_path=(
                    "metadata/unsafe-spoken-regeneration-queue.jsonl"
                ),
                schema_type=(
                    "abby_voice_unsafe_spoken_regeneration_queue_v1"
                ),
                row_count=len(
                    reconciliation.unsafe_spoken_regeneration_rows
                ),
                kind="unsafe_spoken_regeneration_queue",
            ),
            _support_source(
                source=frame_map_path,
                relative_path="metadata/frame-template-map.jsonl",
                schema_type="abby_voice_frame_template_map_v2",
                row_count=len(reconciliation.frame_template_rows),
                kind="frame_template_map",
            ),
            _support_source(
                source=runtime_precomputed_audio_path,
                relative_path=(
                    "metadata/runtime-precomputed-audio-manifest.json"
                ),
                schema_type=(
                    "abby_voice_runtime_precomputed_audio_manifest_v2"
                ),
                kind="runtime_precomputed_audio_manifest",
            ),
            _support_source(
                source=audit_path,
                relative_path="metadata/reconciliation-audit.json",
                schema_type="abby_voice_canonical_reconciliation_v2",
                kind="reconciliation_audit",
            ),
            _support_source(
                source=base_binding_path,
                relative_path="metadata/whisper-base-v3-publication-receipt.json",
                schema_type="abby_voice_whisper_publication_binding_v1",
                kind="base_whisper_validation_receipt",
            ),
            _support_source(
                source=base_decisions_path,
                relative_path="metadata/whisper-base-v3-decisions.jsonl",
                schema_type="abby_voice_whisper_publication_item_v1",
                row_count=len(base_decision_rows),
                kind="base_whisper_validation_decisions",
            ),
            _support_source(
                source=base_failures_path,
                relative_path="metadata/whisper-base-v3-failures.json",
                schema_type=FULL_WHISPER_FAILURE_SCHEMA,
                kind="base_whisper_failure_manifest",
            ),
            _support_source(
                source=base_semantic_corruptions_path,
                relative_path=(
                    "metadata/whisper-base-v3-semantic-corruptions.json"
                ),
                schema_type=SEMANTIC_CORRUPTION_SCHEMA,
                kind="base_whisper_semantic_corruption_manifest",
            ),
        ]
        if adjudication is not None:
            stronger_binding_path = temporary / "whisper-stronger-binding.json"
            stronger_decisions_path = temporary / "whisper-stronger-decisions.jsonl"
            stronger_failures_path = temporary / "whisper-stronger-failures.json"
            adjudication_summary_path = temporary / "whisper-adjudication.json"
            adjudication_subset_path = temporary / "whisper-adjudication-subset.jsonl"
            _write_json(
                stronger_binding_path,
                _validation_publication_binding(
                    adjudication.validation,
                    role="stronger_whisper_adjudication",
                ),
            )
            stronger_decision_rows = _validation_decision_rows(
                adjudication.validation,
                role="stronger_whisper_adjudication",
            )
            _write_jsonl(stronger_decisions_path, stronger_decision_rows)
            stronger_failure_manifest = _load_json(
                adjudication.validation.failure_manifest_path
            )
            _assert_publication_support_safe(
                stronger_failure_manifest,
                label="stronger Whisper failure manifest",
            )
            _write_json(stronger_failures_path, stronger_failure_manifest)
            _write_json(
                adjudication_summary_path,
                _sanitized_adjudication_summary(adjudication),
            )
            adjudication_subset_rows = _sanitized_adjudication_subset(
                adjudication
            )
            _write_jsonl(
                adjudication_subset_path,
                adjudication_subset_rows,
            )
            support_sources.extend(
                (
                    _support_source(
                        source=stronger_binding_path,
                        relative_path=(
                            "metadata/whisper-stronger-publication-receipt.json"
                        ),
                        schema_type=(
                            "abby_voice_whisper_publication_binding_v1"
                        ),
                        kind="stronger_whisper_validation_receipt",
                    ),
                    _support_source(
                        source=stronger_decisions_path,
                        relative_path=(
                            "metadata/whisper-stronger-decisions.jsonl"
                        ),
                        schema_type=(
                            "abby_voice_whisper_publication_item_v1"
                        ),
                        row_count=len(stronger_decision_rows),
                        kind="stronger_whisper_validation_decisions",
                    ),
                    _support_source(
                        source=stronger_failures_path,
                        relative_path=(
                            "metadata/whisper-stronger-failures.json"
                        ),
                        schema_type=FULL_WHISPER_FAILURE_SCHEMA,
                        kind="stronger_whisper_failure_manifest",
                    ),
                    _support_source(
                        source=adjudication_summary_path,
                        relative_path=(
                            "metadata/whisper-adjudication-summary.json"
                        ),
                        schema_type=(
                            "abby_voice_whisper_adjudication_binding_v1"
                        ),
                        kind="whisper_adjudication_summary",
                    ),
                    _support_source(
                        source=adjudication_subset_path,
                        relative_path=(
                            "metadata/whisper-adjudication-subset.jsonl"
                        ),
                        schema_type=(
                            "abby_voice_whisper_adjudication_subset_item_v1"
                        ),
                        row_count=len(adjudication_subset_rows),
                        kind="whisper_adjudication_subset",
                    ),
                )
            )
        policy = AbbyVoiceHFReleasePolicy(
            shard_rows=shard_rows,
            dataset_repo_id="Publicus/211-abby-tts",
            require_publishable=True,
        )
        result = AbbyVoiceHFReleaseBuilder(
            policy=policy,
            repository_commit=repository_commit,
        ).build(
            output_dir=release_dir,
            release_id=selected_release_id,
            responses=reconciliation.bundle.responses,
            templates=reconciliation.bundle.templates,
            audio=reconciliation.bundle.audio,
            provenance=reconciliation.bundle.provenance,
            audio_asset_sources=reconciliation.audio_sources,
            support_sources=support_sources,
            parent_source_ids=tuple(
                sorted(
                    {
                        *reconciliation.audit["source_digests"].values(),
                        *(
                            (adjudication.summary_sha256,)
                            if adjudication is not None
                            else ()
                        ),
                    }
                )
            ),
            license_id="MIT",
            consent_status="not_required",
        )
    validation = validate_abby_voice_hf_release(release_dir)
    return {
        "audit": dict(reconciliation.audit),
        "descriptor_count": len(result.descriptors),
        "identity_sha256": identity_sha256,
        "manifest_path": result.manifest_path,
        "manifest_sha256": result.manifest_sha256,
        "output_dir": result.output_dir,
        "release_cid": result.release_cid,
        "release_id": result.release_id,
        "remote_write_performed": False,
        "row_counts": validation["row_counts"],
        "schema_version": "abby_voice_canonical_release_build_receipt_v2",
        "valid": validation["valid"],
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage-root", type=Path, default=DEFAULT_STAGE_ROOT)
    parser.add_argument("--retained-responses", type=Path, default=DEFAULT_RETAINED_RESPONSES)
    parser.add_argument("--vocabulary", type=Path, default=DEFAULT_VOCABULARY)
    parser.add_argument("--frames", type=Path, default=DEFAULT_FRAMES)
    parser.add_argument("--intents", type=Path, default=DEFAULT_INTENTS)
    parser.add_argument("--bucket-objects", type=Path, default=DEFAULT_BUCKET_OBJECTS)
    parser.add_argument("--regeneration-plan", type=Path, default=DEFAULT_REGENERATION_PLAN)
    parser.add_argument("--regeneration-audio", type=Path, default=DEFAULT_REGENERATION_AUDIO)
    parser.add_argument(
        "--whisper-receipt",
        type=Path,
        default=DEFAULT_WHISPER_RECEIPT,
        help="Authoritative pinned whisper-base v3 corpus receipt.",
    )
    parser.add_argument(
        "--whisper-adjudication-summary",
        type=Path,
        help=(
            "Required when base v3 has failures; must bind the complete "
            "large-v3-turbo adjudication set."
        ),
    )
    parser.add_argument("--slotted-dag", type=Path, default=DEFAULT_SLOTTED_DAG)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--release-id")
    parser.add_argument(
        "--repository-commit",
        default="commit:local-abby-voice-canonical-v2",
    )
    parser.add_argument("--shard-rows", type=int, default=4096)
    parser.add_argument(
        "--audit-only",
        action="store_true",
        help="Reconcile and print counts without copying/building release assets.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    inputs = CanonicalReleaseInputs(
        stage_root=args.stage_root,
        retained_responses=args.retained_responses,
        vocabulary=args.vocabulary,
        frames=args.frames,
        intents=args.intents,
        bucket_objects=args.bucket_objects,
        regeneration_plan=args.regeneration_plan,
        regeneration_audio=args.regeneration_audio,
        slotted_dag=args.slotted_dag,
    )
    if args.audit_only:
        base_validation = (
            load_full_whisper_validation_evidence(
                validation_manifest=inputs.regeneration_audio,
                receipt_path=args.whisper_receipt,
                required_model_name=BASE_WHISPER_MODEL_NAME,
                required_model_revision=BASE_WHISPER_MODEL_REVISION,
                require_semantic_manifest=True,
            )
            if args.whisper_receipt.is_file()
            else None
        )
        adjudication = (
            load_whisper_adjudication_evidence(
                base_validation=base_validation,
                summary_path=args.whisper_adjudication_summary,
            )
            if (
                base_validation is not None
                and args.whisper_adjudication_summary is not None
            )
            else None
        )
        reconciliation = reconcile_canonical_release(
            inputs,
            whisper_validation=base_validation,
            whisper_adjudication=(
                adjudication.validation if adjudication is not None else None
            ),
        )
        receipt = {
            "audit": dict(reconciliation.audit),
            "remote_write_performed": False,
            "schema_version": "abby_voice_canonical_release_audit_v2",
        }
    else:
        receipt = build_canonical_release(
            inputs=inputs,
            output_root=args.output_root,
            whisper_receipt=args.whisper_receipt,
            whisper_adjudication_summary=args.whisper_adjudication_summary,
            release_id=args.release_id,
            repository_commit=args.repository_commit,
            shard_rows=args.shard_rows,
        )
    print(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
