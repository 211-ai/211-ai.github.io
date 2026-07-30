from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import pytest

from scripts.build_abby_voice_canonical_release import (
    BASE_WHISPER_MODEL_NAME,
    BASE_WHISPER_MODEL_REVISION,
    CanonicalReleaseInputs,
    _full_whisper_receipt_id,
    load_full_whisper_validation_evidence,
    reconcile_canonical_release,
)


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
            for row in rows
        ),
        encoding="utf-8",
    )


def test_full_whisper_receipt_identity_binds_semantic_manifest() -> None:
    assert _full_whisper_receipt_id(
        manifest_sha256=(
            "edf8afe3d3c322393f28bc55bde85ce85266c26085bd07ee246339ff7f8891e8"
        ),
        ledger_sha256=(
            "444c6c0e88480999c2e51ad538921cb7be6b30d788dd516729502f3c55a8239a"
        ),
        run_fingerprint=(
            "84c7c269e561e28064aebf878e5481a682a8c9b1f8fe64e1665a10207cf3e0bf"
        ),
        semantic_manifest_sha256=(
            "e190ec5dad516fbed56e207b62781c207b412752d0ee2a541d7d73125ea74652"
        ),
    ) == (
        "abby-voice-full-asr-corpus:sha256:"
        "86ce4b4faefc5e40796f25657fa08c151dae3300a9f3ce6fd60db833434d83d0"
    )


def test_reconciliation_runtime_manifest_contains_only_active_safe_audio(
    tmp_path: Path,
) -> None:
    stage_root = tmp_path / "stage"
    metadata = stage_root / "metadata"
    audio_root = stage_root / "audio"
    audio_root.mkdir(parents=True)
    safe_audio = b"safe-mp3-fixture"
    unsafe_audio = b"unsafe-mp3-fixture"
    (audio_root / "safe.mp3").write_bytes(safe_audio)
    (audio_root / "unsafe.mp3").write_bytes(unsafe_audio)

    retained_responses = metadata / "responses.jsonl"
    _write_jsonl(
        retained_responses,
        [
            {
                "audioAvailable": True,
                "audioBytes": len(safe_audio),
                "audioSha256": sha256(safe_audio).hexdigest(),
                "datasetAudioPath": "audio/safe.mp3",
                "id": "abby-tts-safe",
                "originalTexts": ["A safe cached response."],
                "preferredMimeType": "audio/mpeg",
                "routes": ["grounded_211_answer"],
                "serviceTags": ["food"],
                "slottedIntentIds": ["intent-food"],
                "sourceIds": ["source-safe"],
                "text": "A safe cached response.",
            },
            {
                "audioAvailable": True,
                "audioBytes": len(unsafe_audio),
                "audioSha256": sha256(unsafe_audio).hexdigest(),
                "datasetAudioPath": "audio/unsafe.mp3",
                "id": "abby-tts-unsafe",
                "originalTexts": ["Call five-zero-three for help."],
                "preferredMimeType": "audio/mpeg",
                "routes": ["grounded_211_answer"],
                "sourceIds": ["source-unsafe"],
                "text": "Call five-zero-three for help.",
            },
        ],
    )
    vocabulary = metadata / "vocabulary.jsonl"
    frames = metadata / "frames.jsonl"
    intents = metadata / "intents.jsonl"
    bucket_objects = metadata / "bucket.jsonl"
    for path in (vocabulary, frames, bucket_objects):
        _write_jsonl(path, [])
    _write_jsonl(
        intents,
        [{"id": "intent-food"}],
    )
    regeneration_plan = metadata / "regeneration-plan.json"
    regeneration_audio = metadata / "regeneration-audio.json"
    slotted_dag = metadata / "slotted-dag.json"
    _write_json(regeneration_plan, {"supersession_map": []})
    _write_json(
        regeneration_audio,
        {"aggregation": {"complete": True}, "responses": []},
    )
    _write_json(slotted_dag, {})

    result = reconcile_canonical_release(
        CanonicalReleaseInputs(
            stage_root=stage_root,
            retained_responses=retained_responses,
            vocabulary=vocabulary,
            frames=frames,
            intents=intents,
            bucket_objects=bucket_objects,
            regeneration_plan=regeneration_plan,
            regeneration_audio=regeneration_audio,
            slotted_dag=slotted_dag,
        )
    )

    assert result.audit["active_audio_count"] == 1
    assert result.audit["runtime_precomputed_audio_count"] == 1
    assert result.audit["unsafe_spoken_regeneration_queue_count"] == 1
    assert len(result.runtime_precomputed_audio_rows) == 1
    runtime_row = result.runtime_precomputed_audio_rows[0]
    assert runtime_row["id"] == "abby-tts-safe"
    assert runtime_row["status"] == "active_immutable_release"
    assert runtime_row["preferredAudioUrl"].startswith("../assets/audio/")
    assert "/resolve/main/" not in runtime_row["preferredAudioUrl"]
    assert runtime_row["slottedIntentIds"] == ["intent-food"]
    assert result.unsafe_spoken_regeneration_rows[0]["excluded_audio_id"] == (
        "abby-tts-unsafe"
    )
    assert result.unsafe_spoken_regeneration_rows[0]["risk_reasons"] == [
        "number_word_dash"
    ]


def test_authoritative_base_v3_evidence_reconciles_production_corpus() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    stage_root = repo_root / "tmp_assets" / "hf-abby-tts-canonical-dataset"
    metadata = stage_root / "metadata"
    inputs = CanonicalReleaseInputs(
        stage_root=stage_root,
        retained_responses=metadata / "abby_tts_responses.jsonl",
        vocabulary=metadata / "abby_tts_vocabulary.jsonl",
        frames=metadata / "abby_tts_slotted_response_frames.jsonl",
        intents=metadata / "abby_tts_slotted_intents.jsonl",
        bucket_objects=metadata / "abby_tts_bucket_audio_objects.jsonl",
        regeneration_plan=metadata / "regeneration-full-plan.json",
        regeneration_audio=metadata / "regeneration-audio-manifest.json",
        slotted_dag=(
            repo_root
            / "docs"
            / "phone_dialog_generation"
            / "slotted_response_dag.json"
        ),
    )
    receipt_path = (
        metadata / "regeneration-full-whisper-validation-v3.receipt.json"
    )
    required_paths = (
        inputs.retained_responses,
        inputs.vocabulary,
        inputs.frames,
        inputs.intents,
        inputs.bucket_objects,
        inputs.regeneration_plan,
        inputs.regeneration_audio,
        inputs.slotted_dag,
        receipt_path,
    )
    if not all(path.is_file() for path in required_paths):
        pytest.skip("authoritative local Abby publication corpus is absent")

    evidence = load_full_whisper_validation_evidence(
        validation_manifest=inputs.regeneration_audio,
        receipt_path=receipt_path,
        required_model_name=BASE_WHISPER_MODEL_NAME,
        required_model_revision=BASE_WHISPER_MODEL_REVISION,
        require_semantic_manifest=True,
    )
    assert evidence.validation_receipt_id == (
        "abby-voice-full-asr-corpus:sha256:"
        "86ce4b4faefc5e40796f25657fa08c151dae3300a9f3ce6fd60db833434d83d0"
    )
    assert evidence.ledger_sha256 == (
        "444c6c0e88480999c2e51ad538921cb7be6b30d788dd516729502f3c55a8239a"
    )
    assert evidence.failure_manifest_sha256 == (
        "dcd8e51400dab614044791c31cdb6b792cd395ea7e3b2f22268da5e3491baec5"
    )
    assert evidence.semantic_corruption_manifest_sha256 == (
        "e190ec5dad516fbed56e207b62781c207b412752d0ee2a541d7d73125ea74652"
    )
    assert len(evidence.failed_audio_ids) == 1_690
    assert len(evidence.semantic_corruption_ids) == 42

    result = reconcile_canonical_release(
        inputs,
        whisper_validation=evidence,
    )
    assert result.audit["active_audio_count"] == 11_651
    assert result.audit["runtime_precomputed_audio_count"] == 11_651
    assert result.audit["base_whisper_failed_count"] == 1_690
    assert result.audit["publication_ready"] is False
    assert result.audit[
        "retained_apostrophe_direction_exclusion_ids_sha256"
    ] == "b1484f48ec7ee5a3aea5a29a8f450e63f3405f9e57f6354c795c675c37b6981b"
    assert result.audit[
        "generated_unsafe_spoken_exclusion_ids_sha256"
    ] == "40a4d120603ae3a9e2a5062bd8989c133dfdc1fb0b6af202d2172ee023a2f4b1"
    assert {
        row["status"] for row in result.quality_exclusion_rows
    } == {"excluded_unresolved_whisper_v3_failure"}
    assert all(
        str(row["preferredAudioUrl"]).startswith("../assets/audio/")
        for row in result.runtime_precomputed_audio_rows
    )
