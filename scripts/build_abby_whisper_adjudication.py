#!/usr/bin/env python3
"""Build and reconcile a pinned stronger-Whisper adjudication sample."""

from __future__ import annotations

import argparse
import json
import re
import sys
from hashlib import sha256
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.validate_abby_regeneration_whisper import (  # noqa: E402
    FAILURE_MANIFEST_SCHEMA,
    RECEIPT_SCHEMA,
    atomic_write_json,
)

SUBSET_SCHEMA = "abby_voice_whisper_adjudication_subset_v1"
ADJUDICATION_SCHEMA = "abby_voice_whisper_adjudication_receipt_v1"
DECISION_POLICY = (
    "base_failure_recoverable_only_when_stronger_item_passed_and_hashes_identical"
)


def _sha256_path(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(REPO_ROOT))
    except ValueError:
        return str(resolved)


def _load_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _resolve_evidence_path(value: str, owner_path: Path) -> Path:
    candidate = Path(str(value or ""))
    if candidate.is_absolute():
        return candidate.resolve()
    repo_candidate = (REPO_ROOT / candidate).resolve()
    if repo_candidate.is_file():
        return repo_candidate
    return (owner_path.parent / candidate).resolve()


def _evenly_spaced(items: list[Any], limit: int) -> list[Any]:
    if limit < 1:
        raise ValueError("limit must be positive")
    if len(items) <= limit:
        return list(items)
    if limit == 1:
        return [items[0]]
    positions = [
        (sample_index * (len(items) - 1)) // (limit - 1)
        for sample_index in range(limit)
    ]
    if len(set(positions)) != limit:
        raise AssertionError("deterministic sample positions are not unique")
    return [items[position] for position in positions]


def _build_failure_subset(
    canonical_manifest_path: Path,
    base_receipt_path: Path,
    failure_manifest_path: Path,
    output_path: Path,
    *,
    mode: str,
    limit: int | None,
) -> dict[str, Any]:
    """Build a hash-bound stronger-model workset from base failures."""

    canonical_manifest_path = canonical_manifest_path.resolve()
    base_receipt_path = base_receipt_path.resolve()
    failure_manifest_path = failure_manifest_path.resolve()
    output_path = output_path.resolve()
    base = _load_object(base_receipt_path)
    failures = _load_object(failure_manifest_path)
    manifest = _load_object(canonical_manifest_path)
    if base.get("schema_version") != RECEIPT_SCHEMA:
        raise ValueError("base validation receipt does not use the v3 schema")
    if failures.get("schema_version") != FAILURE_MANIFEST_SCHEMA:
        raise ValueError("base failure manifest has an unexpected schema")
    if int(base.get("pending_count") or 0) != 0:
        raise ValueError("base validation receipt is incomplete")
    if int(base.get("error_count") or 0) != 0:
        raise ValueError("base validation receipt has unresolved runtime errors")
    manifest_digest = _sha256_path(canonical_manifest_path)
    failure_digest = _sha256_path(failure_manifest_path)
    if base.get("manifest_sha256") != manifest_digest:
        raise ValueError("canonical manifest hash does not match base receipt")
    if base.get("failed_item_manifest_sha256") != failure_digest:
        raise ValueError("failure manifest hash does not match base receipt")
    if failures.get("manifest_sha256") != manifest_digest:
        raise ValueError("failure manifest binds another canonical manifest")
    if failures.get("run_fingerprint") != base.get("run_fingerprint"):
        raise ValueError("failure manifest and base receipt run fingerprints differ")
    if failures.get("model_name") != base.get("model_name"):
        raise ValueError("failure manifest and base receipt models differ")
    if failures.get("model_revision") != base.get("model_revision"):
        raise ValueError("failure manifest and base receipt revisions differ")

    rows = manifest.get("responses")
    if not isinstance(rows, list):
        raise ValueError("canonical manifest has no response list")
    failures_list = failures.get("failures")
    if not isinstance(failures_list, list):
        raise ValueError("failure manifest has no failure list")
    if len(failures_list) != int(failures.get("failed_count") or -1):
        raise ValueError("failure manifest count is inconsistent")
    if not all(isinstance(failure, dict) for failure in failures_list):
        raise ValueError("failure manifest contains a non-object item")
    failure_ids = [str(failure.get("audio_id") or "") for failure in failures_list]
    if any(not audio_id for audio_id in failure_ids):
        raise ValueError("failure manifest contains an empty audio ID")
    if len(failure_ids) != len(set(failure_ids)):
        raise ValueError("failure manifest contains duplicate audio IDs")

    if mode == "all_failures":
        eligible = list(failures_list)
    elif mode == "numeric_sample":
        eligible = [
            failure
            for failure in failures_list
            if isinstance(failure, dict)
            and failure.get("failure_reasons") == ["numeric_sequences_match"]
        ]
    else:
        raise ValueError(f"unsupported failure-subset mode: {mode}")
    eligible.sort(key=lambda item: (int(item["manifest_index"]), item["audio_id"]))
    selected = (
        list(eligible)
        if mode == "all_failures"
        else _evenly_spaced(eligible, int(limit or 0))
    )
    responses: list[dict[str, Any]] = []
    for failure in selected:
        manifest_index = int(failure["manifest_index"])
        if manifest_index < 0 or manifest_index >= len(rows):
            raise ValueError("failure manifest index is outside canonical manifest")
        row = rows[manifest_index]
        if not isinstance(row, dict) or row.get("id") != failure.get("audio_id"):
            raise ValueError("failure ID does not match canonical manifest index")
        expected_digest = sha256(str(row.get("text") or "").encode()).hexdigest()
        if expected_digest != failure.get("expected_text_sha256"):
            raise ValueError("failure expected-text hash does not match manifest")
        responses.append(
            {
                "baseValidation": {
                    "audioSha256": failure["audio_sha256"],
                    "expectedTextSha256": failure["expected_text_sha256"],
                    "failureReasons": failure["failure_reasons"],
                    "validationReceiptId": failure["validation_receipt_id"],
                },
                "id": row["id"],
                "preferredAudioPath": (
                    row.get("preferredAudioPath")
                    or row.get("mp3Path")
                    or row.get("audioPath")
                ),
                "sourceIds": [
                    str(value)
                    for value in row.get("sourceIds") or []
                    if str(value)
                ],
                "text": row["text"],
            }
        )
    payload = {
        "responseCount": len(responses),
        "responses": responses,
        "schemaVersion": SUBSET_SCHEMA,
        "selection": (
            {
                "baseFailureCount": len(failures_list),
                "policy": "all_base_failures_in_manifest_order_v1",
                "selectedCount": len(responses),
            }
            if mode == "all_failures"
            else {
                "eligibleNumericOnlyFailureCount": len(eligible),
                "limit": limit,
                "policy": "manifest_order_evenly_spaced_including_endpoints_v1",
                "selectedCount": len(responses),
            }
        ),
        "source": {
            "baseFailureManifest": _display_path(failure_manifest_path),
            "baseFailureManifestSha256": failure_digest,
            "baseValidationReceipt": _display_path(base_receipt_path),
            "baseValidationReceiptSha256": _sha256_path(base_receipt_path),
            "canonicalManifest": _display_path(canonical_manifest_path),
            "canonicalManifestSha256": manifest_digest,
        },
    }
    atomic_write_json(output_path, payload)
    return payload


def build_all_failure_subset(
    canonical_manifest_path: Path,
    base_receipt_path: Path,
    failure_manifest_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    """Build the publication-authoritative workset containing every base failure."""

    return _build_failure_subset(
        canonical_manifest_path,
        base_receipt_path,
        failure_manifest_path,
        output_path,
        mode="all_failures",
        limit=None,
    )


def build_numeric_failure_subset(
    canonical_manifest_path: Path,
    base_receipt_path: Path,
    failure_manifest_path: Path,
    output_path: Path,
    *,
    limit: int = 12,
) -> dict[str, Any]:
    """Build a diagnostic corpus-spanning sample of numeric-only failures."""

    return _build_failure_subset(
        canonical_manifest_path,
        base_receipt_path,
        failure_manifest_path,
        output_path,
        mode="numeric_sample",
        limit=limit,
    )


def build_adjudication_receipt(
    base_receipt_path: Path,
    subset_manifest_path: Path,
    stronger_receipt_path: Path,
    output_path: Path,
    *,
    stronger_model_name: str,
    stronger_model_revision: str,
) -> dict[str, Any]:
    """Reconcile stronger evidence without mutating the base validation result."""

    base_receipt_path = base_receipt_path.resolve()
    subset_manifest_path = subset_manifest_path.resolve()
    stronger_receipt_path = stronger_receipt_path.resolve()
    output_path = output_path.resolve()
    if not re.fullmatch(r"[0-9a-f]{40}", stronger_model_revision):
        raise ValueError("stronger_model_revision must be an exact commit SHA")
    base = _load_object(base_receipt_path)
    subset = _load_object(subset_manifest_path)
    stronger = _load_object(stronger_receipt_path)
    base_digest = _sha256_path(base_receipt_path)
    if base.get("schema_version") != RECEIPT_SCHEMA:
        raise ValueError("base validation receipt does not use the v3 schema")
    if subset.get("schemaVersion") != SUBSET_SCHEMA:
        raise ValueError("adjudication subset has an unexpected schema")
    if stronger.get("schema_version") != RECEIPT_SCHEMA:
        raise ValueError("stronger validation receipt does not use the v3 schema")
    subset_digest = _sha256_path(subset_manifest_path)
    if stronger.get("manifest_sha256") != subset_digest:
        raise ValueError("stronger receipt does not bind the adjudication subset")
    if stronger.get("model_name") != stronger_model_name:
        raise ValueError("stronger receipt model name is not pinned as requested")
    if stronger.get("model_revision") != stronger_model_revision:
        raise ValueError("stronger receipt model revision is not pinned as requested")
    if int(stronger.get("pending_count") or 0) != 0:
        raise ValueError("stronger validation receipt is incomplete")
    if int(stronger.get("error_count") or 0) != 0:
        raise ValueError("stronger validation has unresolved runtime errors")
    if stronger.get("gates") != base.get("gates"):
        raise ValueError("stronger and base validation gates differ")
    source = subset.get("source")
    if not isinstance(source, dict):
        raise ValueError("adjudication subset has no source bindings")
    if source.get("baseValidationReceiptSha256") != base_digest:
        raise ValueError("subset does not bind the supplied base receipt")
    if source.get("baseFailureManifestSha256") != base.get(
        "failed_item_manifest_sha256"
    ):
        raise ValueError("subset failure-manifest binding differs from base")
    if source.get("canonicalManifestSha256") != base.get("manifest_sha256"):
        raise ValueError("subset canonical-manifest binding differs from base")

    rows = subset.get("responses")
    if not isinstance(rows, list) or len(rows) != int(
        subset.get("responseCount") or -1
    ):
        raise ValueError("adjudication subset response count is inconsistent")
    if int(stronger.get("total_count") or -1) != len(rows):
        raise ValueError("stronger receipt total does not equal subset size")
    if int(stronger.get("completed_count") or -1) != len(rows):
        raise ValueError("stronger receipt completion does not equal subset size")
    ledger_path = _resolve_evidence_path(
        str(stronger.get("ledger") or ""), stronger_receipt_path
    )
    if not ledger_path.is_file():
        raise ValueError("stronger receipt ledger is missing")
    if _sha256_path(ledger_path) != stronger.get("ledger_sha256"):
        raise ValueError("stronger receipt ledger hash is invalid")
    latest: dict[str, dict[str, Any]] = {}
    for line_number, line in enumerate(
        ledger_path.read_text(encoding="utf-8").splitlines(), 1
    ):
        event = json.loads(line)
        if not isinstance(event, dict):
            raise ValueError(f"stronger ledger line {line_number} is not an object")
        latest[str(event.get("audio_id") or "")] = event
    expected_ids = {str(row.get("id") or "") for row in rows}
    if set(latest) != expected_ids:
        raise ValueError("stronger ledger IDs do not exactly equal subset IDs")

    decisions: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("adjudication response is not an object")
        audio_id = str(row.get("id") or "")
        event = latest.get(audio_id)
        base_validation = row.get("baseValidation")
        if not isinstance(event, dict) or event.get("status") != "validated":
            raise ValueError(f"stronger receipt is missing validated item {audio_id}")
        if not isinstance(base_validation, dict):
            raise ValueError(f"subset item {audio_id} has no base validation binding")
        if event.get("model_revision") != stronger_model_revision:
            raise ValueError(f"stronger item {audio_id} has the wrong model revision")
        if event.get("asr_model") != stronger_model_name:
            raise ValueError(f"stronger item {audio_id} has the wrong model name")
        if event.get("audio_sha256") != base_validation.get("audioSha256"):
            raise ValueError(f"stronger item {audio_id} audio hash differs from base")
        if event.get("expected_text_sha256") != base_validation.get(
            "expectedTextSha256"
        ):
            raise ValueError(
                f"stronger item {audio_id} expected-text hash differs from base"
            )
        passed = event.get("passed") is True
        gates = stronger["gates"]
        if passed and (
            event.get("numeric_sequences_match") is not True
            or event.get("forbidden_negative_detected") is not False
            or int(event.get("normalized_similarity_bp") or 0)
            < int(gates["minimum_similarity_bp"])
            or int(event.get("content_word_coverage_bp") or 0)
            < int(gates["minimum_content_word_coverage_bp"])
            or int(event.get("wer_bp") or 0) > int(gates["maximum_wer_bp"])
        ):
            raise ValueError(
                f"stronger item {audio_id} claims pass without satisfying gates"
            )
        decisions.append(
            {
                "adjudicated_passed": passed,
                "audio_id": audio_id,
                "base_validation_receipt_id": base_validation[
                    "validationReceiptId"
                ],
                "stronger_validation_receipt_id": event[
                    "validation_receipt_id"
                ],
            }
        )
    passed_ids = [
        decision["audio_id"]
        for decision in decisions
        if decision["adjudicated_passed"]
    ]
    failed_ids = [
        decision["audio_id"]
        for decision in decisions
        if not decision["adjudicated_passed"]
    ]
    stronger_digest = _sha256_path(stronger_receipt_path)
    identity = sha256(
        (
            base_digest
            + "\0"
            + subset_digest
            + "\0"
            + stronger_digest
            + "\0"
            + DECISION_POLICY
        ).encode()
    ).hexdigest()
    payload = {
        "adjudicated_pass_count": len(passed_ids),
        "adjudicated_pass_ids": passed_ids,
        "base_receipt_mutated": False,
        "base_validation_receipt": _display_path(base_receipt_path),
        "base_validation_receipt_sha256": base_digest,
        "decision_policy": DECISION_POLICY,
        "decisions": decisions,
        "evidence_only": True,
        "schema_version": ADJUDICATION_SCHEMA,
        "selected_count": len(decisions),
        "still_failed_count": len(failed_ids),
        "still_failed_ids": failed_ids,
        "stronger_model_name": stronger_model_name,
        "stronger_model_revision": stronger_model_revision,
        "stronger_validation_receipt": _display_path(stronger_receipt_path),
        "stronger_validation_receipt_sha256": stronger_digest,
        "subset_manifest": _display_path(subset_manifest_path),
        "subset_manifest_sha256": subset_digest,
        "validation_receipt_id": (
            "abby-voice-whisper-adjudication:sha256:" + identity
        ),
    }
    payload["base_failure_manifest"] = source.get("baseFailureManifest")
    payload["base_failure_manifest_sha256"] = source.get(
        "baseFailureManifestSha256"
    )
    atomic_write_json(output_path, payload)
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subset = subparsers.add_parser("subset")
    subset.add_argument("--canonical-manifest", type=Path, required=True)
    subset.add_argument("--base-receipt", type=Path, required=True)
    subset.add_argument("--failure-manifest", type=Path, required=True)
    subset.add_argument("--output", type=Path, required=True)
    subset.add_argument(
        "--mode",
        choices=("all-failures", "numeric-sample"),
        default="all-failures",
    )
    subset.add_argument("--limit", type=int, default=12)

    receipt = subparsers.add_parser("receipt")
    receipt.add_argument("--base-receipt", type=Path, required=True)
    receipt.add_argument("--subset-manifest", type=Path, required=True)
    receipt.add_argument("--stronger-receipt", type=Path, required=True)
    receipt.add_argument("--output", type=Path, required=True)
    receipt.add_argument(
        "--stronger-model-name",
        default="openai/whisper-large-v3-turbo",
    )
    receipt.add_argument("--stronger-model-revision", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.command == "subset":
        if args.mode == "all-failures":
            payload = build_all_failure_subset(
                args.canonical_manifest,
                args.base_receipt,
                args.failure_manifest,
                args.output,
            )
        else:
            payload = build_numeric_failure_subset(
                args.canonical_manifest,
                args.base_receipt,
                args.failure_manifest,
                args.output,
                limit=args.limit,
            )
    else:
        payload = build_adjudication_receipt(
            args.base_receipt,
            args.subset_manifest,
            args.stronger_receipt,
            args.output,
            stronger_model_name=args.stronger_model_name,
            stronger_model_revision=args.stronger_model_revision,
        )
    print(
        json.dumps(
            {
                "output": str(args.output),
                "output_sha256": _sha256_path(args.output.resolve()),
                "schema": payload.get("schema_version")
                or payload.get("schemaVersion"),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
