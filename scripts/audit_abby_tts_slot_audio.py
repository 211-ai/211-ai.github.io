#!/usr/bin/env python3
"""Audit canonical Abby TTS rows for phone/slot renderings that need repair.

The scanner focuses on text forms that are risky for TTS/ASR round trips:

* digit-by-digit hyphen runs such as ``5-0-3`` that Whisper can hear as
  "negative three";
* parenthesized phone fragments such as ``(503)``;
* full numeric phone numbers that should be spoken as words;
* ZIP/address/unit digit punctuation that should be normalized before TTS.

For each risky selected response, the script checks alternate bucket rows for
the same response id.  A lower-risk alternate is marked for replacement;
otherwise the selected row is marked for regeneration using the shared
``normalize_indextts_spoken_text`` transformation.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.precompute_indextts_responses import normalize_indextts_spoken_text  # noqa: E402


DEFAULT_STAGE_DIR = REPO_ROOT / "tmp_assets" / "hf-abby-tts-canonical-dataset"
DEFAULT_OUTPUT_JSON = REPO_ROOT / "tmp_assets" / "hf-abby-tts-canonical-dataset" / "metadata" / "abby_tts_slot_audio_audit.json"
DEFAULT_OUTPUT_MD = REPO_ROOT / "tmp_assets" / "hf-abby-tts-canonical-dataset" / "metadata" / "abby_tts_slot_audio_audit.md"
DEFAULT_REGEN_JSONL = REPO_ROOT / "tmp_assets" / "hf-abby-tts-canonical-dataset" / "metadata" / "abby_tts_regeneration_queue.jsonl"
DEFAULT_REPLACEMENT_JSONL = REPO_ROOT / "tmp_assets" / "hf-abby-tts-canonical-dataset" / "metadata" / "abby_tts_alternate_replacement_queue.jsonl"
DEFAULT_MANUAL_JSONL = REPO_ROOT / "tmp_assets" / "hf-abby-tts-canonical-dataset" / "metadata" / "abby_tts_manual_review_queue.jsonl"

RISK_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("negative_prone_hyphen_digit_run", re.compile(r"(?<!\d)(?:\d\s*[-–—]\s*){2,}\d(?!\d)")),
    ("parenthesized_digits", re.compile(r"\(\s*\d{2,5}\s*\)")),
    (
        "raw_phone_number",
        re.compile(r"(?:\+?1[\s,.\-–—]*)?(?:\(\d{3}\)|\d{3})[\s,.\-–—]*\d{3}[\s,.\-–—]*\d{4}\b"),
    ),
    ("long_raw_digit_sequence", re.compile(r"(?<!\d)(?:\d[\s,.;:\-–—]*){7,}\d(?!\d)")),
    ("zip_plus_four_hyphen", re.compile(r"\b\d{5}-\d{4}\b")),
    ("numeric_extension", re.compile(r"\b(?:ext\.?|extension|x)\s*#?\s*\d{1,6}\b", re.I)),
)

ADDRESSISH_WORDS = re.compile(
    r"\b(?:address|street|avenue|road|boulevard|drive|lane|suite|unit|apartment|zip)\b",
    re.I,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage-dir", type=Path, default=DEFAULT_STAGE_DIR)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    parser.add_argument("--regen-jsonl", type=Path, default=DEFAULT_REGEN_JSONL)
    parser.add_argument("--replacement-jsonl", type=Path, default=DEFAULT_REPLACEMENT_JSONL)
    parser.add_argument("--manual-jsonl", type=Path, default=DEFAULT_MANUAL_JSONL)
    parser.add_argument("--top", type=int, default=50, help="Rows to include in the Markdown sample table.")
    return parser.parse_args()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def text_for_row(row: Mapping[str, Any]) -> str:
    return str(row.get("spoken_text") or row.get("text") or row.get("sourceText") or row.get("source_text") or "")


def risk_reasons(text: str) -> list[str]:
    reasons = [name for name, pattern in RISK_PATTERNS if pattern.search(text)]
    if re.search(r"\d\s*[-–—]\s*\d", text) and ADDRESSISH_WORDS.search(text):
        reasons.append("numeric_address_or_zip_context")
    return sorted(set(reasons))


def risk_score(text: str) -> int:
    reasons = risk_reasons(text)
    score = 0
    for reason in reasons:
        if reason == "negative_prone_hyphen_digit_run":
            score += 5
        elif reason == "parenthesized_digits":
            score += 4
        elif reason == "raw_phone_number":
            score += 4
        elif reason == "long_raw_digit_sequence":
            score += 3
        else:
            score += 2
    return score


def normalized_repair(text: str) -> str:
    return normalize_indextts_spoken_text(text)


def row_id(row: Mapping[str, Any]) -> str:
    return str(row.get("audio_id") or row.get("id") or row.get("bucketPath") or row.get("path") or "")


def response_id(row: Mapping[str, Any]) -> str:
    return str(row.get("response_id") or row.get("responseId") or "")


def compact_text(text: str, limit: int = 180) -> str:
    text = " ".join(str(text or "").split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def audit(stage_dir: Path) -> dict[str, Any]:
    metadata = stage_dir / "metadata"
    selected_rows = load_jsonl(metadata / "abby_tts_precomputed_audio_resolver.jsonl")
    bucket_rows = load_jsonl(metadata / "abby_tts_bucket_audio_objects.jsonl")

    text_by_canonical_sha: dict[str, str] = {}
    for row in selected_rows:
        text_sha = str(row.get("text_sha256") or row.get("canonicalTextSha256") or "")
        if text_sha:
            text_by_canonical_sha[text_sha] = text_for_row(row)
    for row in bucket_rows:
        text_sha = str(row.get("canonicalTextSha256") or "")
        source_text = text_for_row(row)
        if text_sha and source_text:
            text_by_canonical_sha.setdefault(text_sha, source_text)

    alternates_by_response: dict[str, list[dict[str, Any]]] = defaultdict(list)
    selected_bucket_by_response: dict[str, list[dict[str, Any]]] = defaultdict(list)
    status_counts = Counter()
    for row in bucket_rows:
        status = str(row.get("mappingStatus") or "")
        status_counts[status] += 1
        rid = response_id(row)
        if not rid:
            continue
        if status == "alternate_for_response":
            alternates_by_response[rid].append(row)
        elif status == "selected_for_response":
            selected_bucket_by_response[rid].append(row)

    findings: list[dict[str, Any]] = []
    summary = Counter()
    risk_reason_counts = Counter()
    for row in selected_rows:
        text = text_for_row(row)
        reasons = risk_reasons(text)
        if not reasons:
            continue
        rid = response_id(row)
        repaired = normalized_repair(text)
        repaired_reasons = risk_reasons(repaired)
        selected_score = risk_score(text)
        repaired_score = risk_score(repaired)
        risk_reason_counts.update(reasons)

        alternate_candidates = []
        for alt in alternates_by_response.get(rid, ()):
            alt_text = text_for_row(alt)
            if not alt_text:
                alt_text = text_by_canonical_sha.get(str(alt.get("canonicalTextSha256") or ""), "")
            has_text_evidence = bool(alt_text)
            alt_score = risk_score(alt_text) if has_text_evidence else 999
            alternate_candidates.append(
                {
                    "bucketPath": alt.get("bucketPath"),
                    "legacyTextHash": alt.get("legacyTextHash"),
                    "canonicalTextSha256": alt.get("canonicalTextSha256"),
                    "sourceText": alt_text,
                    "hasTextEvidence": has_text_evidence,
                    "riskScore": alt_score,
                    "riskReasons": risk_reasons(alt_text),
                    "asrWerBp": alt.get("asrWerBp"),
                    "alternateRank": alt.get("alternateRank"),
                    "sizeBytes": alt.get("sizeBytes"),
                    "xetHash": alt.get("xetHash"),
                }
            )
        alternate_candidates.sort(
            key=lambda item: (
                not bool(item["hasTextEvidence"]),
                int(item["riskScore"]),
                int(item["asrWerBp"]) if item.get("asrWerBp") is not None else 10_000,
                int(item["alternateRank"]) if item.get("alternateRank") is not None else 10_000,
                -int(item.get("sizeBytes") or 0),
            )
        )
        best_alternate = alternate_candidates[0] if alternate_candidates else None

        if best_alternate and best_alternate.get("hasTextEvidence") and int(best_alternate["riskScore"]) < selected_score:
            recommendation = "replace_with_alternate"
        elif repaired_score < selected_score:
            recommendation = "regenerate_from_normalized_text"
        else:
            recommendation = "manual_review"
        summary[recommendation] += 1

        findings.append(
            {
                "audioId": row_id(row),
                "responseId": rid,
                "selectedDatasetAudioPath": (row.get("metadata") or {}).get("dataset_audio_path") if isinstance(row.get("metadata"), Mapping) else None,
                "selectedText": text,
                "selectedRiskScore": selected_score,
                "selectedRiskReasons": reasons,
                "normalizedRepairText": repaired,
                "normalizedRepairRiskScore": repaired_score,
                "normalizedRepairRiskReasons": repaired_reasons,
                "recommendation": recommendation,
                "bestAlternate": best_alternate,
                "alternateCandidateCount": len(alternate_candidates),
                "selectedBucketRows": selected_bucket_by_response.get(rid, ()),
            }
        )

    findings.sort(
        key=lambda item: (
            -int(item["selectedRiskScore"]),
            item["recommendation"],
            item["audioId"],
        )
    )
    return {
        "stageDir": str(stage_dir),
        "selectedRowCount": len(selected_rows),
        "bucketStatusCounts": dict(sorted(status_counts.items())),
        "riskySelectedCount": len(findings),
        "recommendationCounts": dict(sorted(summary.items())),
        "riskReasonCounts": dict(sorted(risk_reason_counts.items())),
        "findings": findings,
    }


def write_markdown(report: Mapping[str, Any], path: Path, *, top: int) -> None:
    lines = [
        "# Abby TTS slot audio audit",
        "",
        f"- Stage: `{report.get('stageDir')}`",
        f"- Selected rows scanned: {report.get('selectedRowCount')}",
        f"- Risky selected rows: {report.get('riskySelectedCount')}",
        f"- Recommendations: `{json.dumps(report.get('recommendationCounts', {}), sort_keys=True)}`",
        f"- Risk reasons: `{json.dumps(report.get('riskReasonCounts', {}), sort_keys=True)}`",
        "",
        "## Top findings",
        "",
        "| Recommendation | Audio | Reasons | Selected text | Repair / alternate |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in list(report.get("findings") or [])[:top]:
        alternate = item.get("bestAlternate") or {}
        repair = (
            f"alt `{alternate.get('bucketPath')}`: {compact_text(alternate.get('sourceText') or '')}"
            if alternate
            else compact_text(item.get("normalizedRepairText") or "")
        )
        lines.append(
            "| "
            + " | ".join(
                [
                    str(item.get("recommendation") or ""),
                    f"`{item.get('audioId')}`",
                    ", ".join(item.get("selectedRiskReasons") or []),
                    compact_text(item.get("selectedText") or "").replace("|", "\\|"),
                    repair.replace("|", "\\|"),
                ]
            )
            + " |"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def queue_item(item: Mapping[str, Any]) -> dict[str, Any]:
    alternate = item.get("bestAlternate") if isinstance(item.get("bestAlternate"), Mapping) else None
    return {
        "audioId": item.get("audioId"),
        "responseId": item.get("responseId"),
        "selectedDatasetAudioPath": item.get("selectedDatasetAudioPath"),
        "recommendation": item.get("recommendation"),
        "riskReasons": item.get("selectedRiskReasons"),
        "selectedText": item.get("selectedText"),
        "normalizedRepairText": item.get("normalizedRepairText"),
        "bestAlternateBucketPath": alternate.get("bucketPath") if alternate else None,
        "bestAlternateText": alternate.get("sourceText") if alternate else None,
        "bestAlternateRiskReasons": alternate.get("riskReasons") if alternate else None,
        "alternateCandidateCount": item.get("alternateCandidateCount"),
    }


def write_recommendation_queue(report: Mapping[str, Any], path: Path, recommendation: str) -> int:
    rows = [
        queue_item(item)
        for item in report.get("findings", [])
        if isinstance(item, Mapping) and item.get("recommendation") == recommendation
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    return len(rows)


def main() -> None:
    args = parse_args()
    report = audit(args.stage_dir)
    queue_counts = {
        "regenerationQueueRows": write_recommendation_queue(report, args.regen_jsonl, "regenerate_from_normalized_text"),
        "replacementQueueRows": write_recommendation_queue(report, args.replacement_jsonl, "replace_with_alternate"),
        "manualReviewQueueRows": write_recommendation_queue(report, args.manual_jsonl, "manual_review"),
    }
    report = {**report, **queue_counts}
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    write_markdown(report, args.output_md, top=args.top)
    print(
        json.dumps(
            {
                key: report[key]
                for key in (
                    "selectedRowCount",
                    "riskySelectedCount",
                    "recommendationCounts",
                    "riskReasonCounts",
                    "regenerationQueueRows",
                    "replacementQueueRows",
                    "manualReviewQueueRows",
                )
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
