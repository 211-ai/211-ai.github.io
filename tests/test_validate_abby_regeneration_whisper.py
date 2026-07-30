from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.validate_abby_regeneration_whisper import (
    ITEM_SCHEMA,
    _transcribe_resiliently,
    load_receipt_events,
    run_validation,
    validation_artifact_paths,
)


def _write_manifest(root: Path, texts: list[str]) -> Path:
    audio_root = root / "audio"
    audio_root.mkdir()
    rows = []
    for index, text in enumerate(texts):
        audio_path = audio_root / f"item-{index}.mp3"
        audio_path.write_bytes(f"audio-{index}".encode())
        rows.append(
            {
                "id": f"item-{index}",
                "preferredAudioPath": str(audio_path),
                "sourceIds": [f"response-{index}", f"source-audio-{index}"],
                "text": text,
            }
        )
    manifest = root / "manifest.json"
    manifest.write_text(json.dumps({"responses": rows}), encoding="utf-8")
    return manifest


def _run(
    manifest: Path,
    prefix: Path,
    transcribe_many,
    **kwargs,
):
    return run_validation(
        manifest,
        prefix,
        model_name="test/whisper",
        model_revision="a" * 40,
        device="cpu",
        dtype="float32",
        language="en",
        batch_size=2,
        minimum_similarity_bp=7_800,
        minimum_content_coverage_bp=6_500,
        maximum_wer_bp=3_500,
        transcribe_many=transcribe_many,
        **kwargs,
    )


def test_run_validation_is_durable_and_resumes_without_retranscription(
    tmp_path: Path,
) -> None:
    texts = [
        "Call five zero three, five five five, zero one zero zero.",
        "The shelter is open tonight.",
        "Bring photo identification if you have it.",
    ]
    manifest = _write_manifest(tmp_path, texts)
    prefix = tmp_path / "full-validation"
    calls: list[list[str]] = []

    def transcribe(paths):
        calls.append([path.name for path in paths])
        return [
            texts[int(path.stem.rsplit("-", 1)[-1])]
            for path in paths
        ]

    first = _run(
        manifest,
        prefix,
        transcribe,
        max_items=2,
    )
    assert first["completed_count"] == 2
    assert first["pending_count"] == 1
    assert calls == [["item-0.mp3", "item-1.mp3"]]

    second = _run(manifest, prefix, transcribe)
    assert second["status"] == "complete"
    assert second["completed_count"] == 3
    assert second["passed_count"] == 3
    assert calls[-1] == ["item-2.mp3"]

    artifacts = validation_artifact_paths(
        prefix, shard_count=1, shard_index=0
    )
    events = [
        json.loads(line)
        for line in artifacts["ledger"].read_text(encoding="utf-8").splitlines()
    ]
    assert [event["audio_id"] for event in events] == [
        "item-0",
        "item-1",
        "item-2",
    ]
    assert all(event["schema_version"] == ITEM_SCHEMA for event in events)
    assert all(event["model_revision"] == "a" * 40 for event in events)
    final = json.loads(artifacts["receipt"].read_text(encoding="utf-8"))
    assert final["all_passed"] is True
    assert final["completed_count"] == 3
    assert final["model_revision"] == "a" * 40
    assert len(final["ledger_sha256"]) == 64
    failure_manifest = json.loads(
        artifacts["failures"].read_text(encoding="utf-8")
    )
    assert failure_manifest["model_revision"] == "a" * 40
    assert failure_manifest["failed_count"] == 0
    assert failure_manifest["failures"] == []


def test_run_validation_revalidates_audio_changed_after_checkpoint(
    tmp_path: Path,
) -> None:
    manifest = _write_manifest(tmp_path, ["The shelter is open tonight."])
    prefix = tmp_path / "full-validation"
    call_count = 0

    def transcribe(paths):
        nonlocal call_count
        call_count += len(paths)
        return ["The shelter is open tonight." for _ in paths]

    assert _run(manifest, prefix, transcribe)["completed_count"] == 1
    (tmp_path / "audio" / "item-0.mp3").write_bytes(b"changed-audio")
    assert _run(manifest, prefix, transcribe)["completed_count"] == 1
    assert call_count == 2

    artifacts = validation_artifact_paths(
        prefix, shard_count=1, shard_index=0
    )
    assert (
        len(artifacts["ledger"].read_text(encoding="utf-8").splitlines()) == 2
    )


def test_load_receipts_repairs_only_a_partial_final_line(tmp_path: Path) -> None:
    ledger = tmp_path / "receipts.jsonl"
    event = {
        "audio_id": "one",
        "run_fingerprint": "fingerprint",
        "schema_version": ITEM_SCHEMA,
        "status": "validated",
    }
    ledger.write_bytes(
        (json.dumps(event) + "\n" + '{"audio_id":"partial').encode()
    )

    events, repaired = load_receipt_events(
        ledger,
        run_fingerprint="fingerprint",
        selected_ids={"one"},
    )

    assert repaired is True
    assert events == [event]
    assert ledger.read_bytes().endswith(b"\n")


def test_load_receipts_fails_closed_on_complete_corrupt_record(
    tmp_path: Path,
) -> None:
    ledger = tmp_path / "receipts.jsonl"
    ledger.write_text("{broken}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="invalid receipt JSONL"):
        load_receipt_events(
            ledger,
            run_fingerprint="fingerprint",
            selected_ids={"one"},
        )


def test_transcribe_resiliently_isolates_one_bad_file(tmp_path: Path) -> None:
    paths = [tmp_path / name for name in ("good-a", "bad", "good-b")]

    def transcribe(batch):
        if any(path.name == "bad" for path in batch):
            raise RuntimeError("decode failed")
        return [path.name for path in batch]

    results = _transcribe_resiliently(transcribe, paths)

    assert results[0] == "good-a"
    assert isinstance(results[1], RuntimeError)
    assert results[2] == "good-b"


def test_deterministic_shards_write_independent_ledgers(tmp_path: Path) -> None:
    texts = [f"Expected response number {index}." for index in range(5)]
    manifest = _write_manifest(tmp_path, texts)
    prefix = tmp_path / "full-validation"

    def transcribe(paths):
        return [
            texts[int(path.stem.rsplit("-", 1)[-1])]
            for path in paths
        ]

    shard = _run(
        manifest,
        prefix,
        transcribe,
        shard_count=2,
        shard_index=1,
    )

    assert shard["total_count"] == 2
    assert shard["completed_count"] == 2
    artifacts = validation_artifact_paths(
        prefix, shard_count=2, shard_index=1
    )
    events = [
        json.loads(line)
        for line in artifacts["ledger"].read_text(encoding="utf-8").splitlines()
    ]
    assert [event["manifest_index"] for event in events] == [1, 3]


def test_failure_manifest_is_redacted_and_regeneration_actionable(
    tmp_path: Path,
) -> None:
    manifest = _write_manifest(
        tmp_path,
        ["Call five zero three, five five five, zero one zero zero."],
    )
    prefix = tmp_path / "full-validation"

    checkpoint = _run(
        manifest,
        prefix,
        lambda paths: ["Call 503-555-0101." for _ in paths],
    )

    assert checkpoint["failed_count"] == 1
    artifacts = validation_artifact_paths(
        prefix, shard_count=1, shard_index=0
    )
    payload = json.loads(artifacts["failures"].read_text(encoding="utf-8"))
    failure = payload["failures"][0]
    assert failure["audio_id"] == "item-0"
    assert failure["source_ids"] == ["response-0", "source-audio-0"]
    assert "numeric_sequences_match" in failure["failure_reasons"]
    serialized = json.dumps(payload)
    assert "Call five" not in serialized
    assert "transcript" not in serialized


def test_run_validation_requires_an_exact_model_revision(tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path, ["The shelter is open tonight."])

    with pytest.raises(ValueError, match="exact 40-hex"):
        run_validation(
            manifest,
            tmp_path / "validation",
            model_name="test/whisper",
            model_revision="main",
            device="cpu",
            dtype="float32",
            language="en",
            batch_size=1,
            minimum_similarity_bp=7_800,
            minimum_content_coverage_bp=6_500,
            maximum_wer_bp=3_500,
            transcribe_many=lambda paths: ["The shelter is open tonight."],
        )
