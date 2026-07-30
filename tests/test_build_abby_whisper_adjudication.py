from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

import pytest

from scripts.build_abby_whisper_adjudication import (
    ADJUDICATION_SCHEMA,
    SUBSET_SCHEMA,
    build_adjudication_receipt,
    build_all_failure_subset,
    build_numeric_failure_subset,
)
from scripts.validate_abby_regeneration_whisper import (
    FAILURE_MANIFEST_SCHEMA,
    RECEIPT_SCHEMA,
    atomic_write_json,
)


def _digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _base_evidence(tmp_path: Path, count: int = 5) -> tuple[Path, Path, Path]:
    rows = []
    failures = []
    for index in range(count):
        text = f"Call five zero three zero zero zero zero zero zero {index}."
        row = {
            "id": f"audio-{index}",
            "preferredAudioPath": str(tmp_path / f"audio-{index}.mp3"),
            "sourceIds": [f"response-{index}"],
            "text": text,
        }
        Path(row["preferredAudioPath"]).write_bytes(f"audio-{index}".encode())
        rows.append(row)
        failures.append(
            {
                "audio_id": row["id"],
                "audio_sha256": _digest(Path(row["preferredAudioPath"])),
                "content_word_coverage_bp": 10_000,
                "expected_text_sha256": sha256(text.encode()).hexdigest(),
                "failure_reasons": ["numeric_sequences_match"],
                "forbidden_negative_detected": False,
                "manifest_index": index,
                "normalized_similarity_bp": 9_500,
                "numeric_sequences_match": False,
                "source_ids": row["sourceIds"],
                "validation_receipt_id": f"base-receipt-{index}",
                "wer_bp": 500,
            }
        )
    manifest_path = tmp_path / "canonical.json"
    atomic_write_json(manifest_path, {"responses": rows})
    manifest_digest = _digest(manifest_path)
    failure_path = tmp_path / "failures.json"
    atomic_write_json(
        failure_path,
        {
            "failed_count": len(failures),
            "failures": failures,
            "manifest_sha256": manifest_digest,
            "model_name": "openai/whisper-base",
            "model_revision": "a" * 40,
            "run_fingerprint": "base-fingerprint",
            "schema_version": FAILURE_MANIFEST_SCHEMA,
            "validator_version": "abby_voice_full_whisper_validator_v3",
        },
    )
    receipt_path = tmp_path / "base-receipt.json"
    atomic_write_json(
        receipt_path,
        {
            "error_count": 0,
            "failed_item_manifest_sha256": _digest(failure_path),
            "gates": {
                "maximum_wer_bp": 3_500,
                "minimum_content_word_coverage_bp": 6_500,
                "minimum_similarity_bp": 7_800,
                "require_numeric_sequences_match": True,
            },
            "manifest_sha256": manifest_digest,
            "model_name": "openai/whisper-base",
            "model_revision": "a" * 40,
            "pending_count": 0,
            "run_fingerprint": "base-fingerprint",
            "schema_version": RECEIPT_SCHEMA,
        },
    )
    return manifest_path, receipt_path, failure_path


def test_build_numeric_subset_is_deterministic_and_corpus_spanning(
    tmp_path: Path,
) -> None:
    manifest, receipt, failures = _base_evidence(tmp_path)
    first = tmp_path / "subset-first.json"
    second = tmp_path / "subset-second.json"

    payload = build_numeric_failure_subset(
        manifest, receipt, failures, first, limit=3
    )
    build_numeric_failure_subset(manifest, receipt, failures, second, limit=3)

    assert payload["schemaVersion"] == SUBSET_SCHEMA
    assert [row["id"] for row in payload["responses"]] == [
        "audio-0",
        "audio-2",
        "audio-4",
    ]
    assert first.read_bytes() == second.read_bytes()


def test_build_publication_subset_contains_every_failure_in_order(
    tmp_path: Path,
) -> None:
    manifest, receipt, failures = _base_evidence(tmp_path)
    failure_payload = json.loads(failures.read_text())
    failure_payload["failures"][1]["failure_reasons"] = [
        "minimum_similarity_bp"
    ]
    atomic_write_json(failures, failure_payload)
    receipt_payload = json.loads(receipt.read_text())
    receipt_payload["failed_item_manifest_sha256"] = _digest(failures)
    atomic_write_json(receipt, receipt_payload)

    payload = build_all_failure_subset(
        manifest,
        receipt,
        failures,
        tmp_path / "all-failures.json",
    )

    assert [row["id"] for row in payload["responses"]] == [
        f"audio-{index}" for index in range(5)
    ]
    assert payload["selection"] == {
        "baseFailureCount": 5,
        "policy": "all_base_failures_in_manifest_order_v1",
        "selectedCount": 5,
    }


def test_build_adjudication_receipt_requires_hash_identity_and_keeps_base(
    tmp_path: Path,
) -> None:
    manifest, base_receipt, failures = _base_evidence(tmp_path, count=2)
    subset_path = tmp_path / "subset.json"
    subset = build_numeric_failure_subset(
        manifest, base_receipt, failures, subset_path, limit=2
    )
    ledger_path = tmp_path / "stronger.receipts.jsonl"
    events = []
    for index, row in enumerate(subset["responses"]):
        events.append(
            {
                "audio_id": row["id"],
                "asr_model": "openai/whisper-large-v3-turbo",
                "audio_sha256": row["baseValidation"]["audioSha256"],
                "content_word_coverage_bp": 10_000,
                "expected_text_sha256": row["baseValidation"][
                    "expectedTextSha256"
                ],
                "forbidden_negative_detected": False,
                "model_revision": "b" * 40,
                "normalized_similarity_bp": 10_000,
                "numeric_sequences_match": True,
                "passed": index == 0,
                "status": "validated",
                "validation_receipt_id": f"stronger-{index}",
                "wer_bp": 0,
            }
        )
    ledger_path.write_text(
        "".join(json.dumps(event) + "\n" for event in events),
        encoding="utf-8",
    )
    stronger_receipt = tmp_path / "stronger.receipt.json"
    atomic_write_json(
        stronger_receipt,
        {
            "error_count": 0,
            "completed_count": 2,
            "gates": json.loads(base_receipt.read_text())["gates"],
            "ledger": str(ledger_path),
            "ledger_sha256": _digest(ledger_path),
            "manifest_sha256": _digest(subset_path),
            "model_name": "openai/whisper-large-v3-turbo",
            "model_revision": "b" * 40,
            "pending_count": 0,
            "schema_version": RECEIPT_SCHEMA,
            "total_count": 2,
        },
    )
    output = tmp_path / "adjudication.json"

    payload = build_adjudication_receipt(
        base_receipt,
        subset_path,
        stronger_receipt,
        output,
        stronger_model_name="openai/whisper-large-v3-turbo",
        stronger_model_revision="b" * 40,
    )

    assert payload["schema_version"] == ADJUDICATION_SCHEMA
    assert payload["adjudicated_pass_ids"] == ["audio-0"]
    assert payload["still_failed_ids"] == ["audio-1"]
    assert payload["base_receipt_mutated"] is False
    assert payload["evidence_only"] is True

    events[0]["audio_sha256"] = "c" * 64
    ledger_path.write_text(
        "".join(json.dumps(event) + "\n" for event in events),
        encoding="utf-8",
    )
    stronger_payload = json.loads(stronger_receipt.read_text())
    stronger_payload["ledger_sha256"] = _digest(ledger_path)
    atomic_write_json(stronger_receipt, stronger_payload)
    with pytest.raises(ValueError, match="audio hash differs"):
        build_adjudication_receipt(
            base_receipt,
            subset_path,
            stronger_receipt,
            output,
            stronger_model_name="openai/whisper-large-v3-turbo",
            stronger_model_revision="b" * 40,
        )
