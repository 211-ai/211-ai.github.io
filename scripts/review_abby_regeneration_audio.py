#!/usr/bin/env python3
"""Whisper-review a generated Abby regeneration manifest and emit receipts."""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from collections import Counter
from hashlib import sha256
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
for package_root in (
    REPO_ROOT / "ipfs_accelerate_py",
    REPO_ROOT / "ipfs_datasets_py",
):
    if str(package_root) not in sys.path:
        sys.path.insert(0, str(package_root))

from ipfs_accelerate_py.voice_jobs.local_whisper_batch import (  # noqa: E402
    LocalWhisperBatchSession,
)
from ipfs_datasets_py.voice.audio_quality import word_error_rate_bp  # noqa: E402
from ipfs_datasets_py.voice.normalize import (  # noqa: E402
    normalize_indextts_spoken_text,
)
from transformers.models.whisper.english_normalizer import (  # noqa: E402
    EnglishTextNormalizer,
)

DEFAULT_MANIFEST = (
    REPO_ROOT
    / "tmp_assets"
    / "hf-abby-tts-canonical-dataset"
    / "metadata"
    / "regeneration-canary-generation-manifest.json"
)
DEFAULT_REPORT = (
    REPO_ROOT
    / "tmp_assets"
    / "hf-abby-tts-canonical-dataset"
    / "metadata"
    / "regeneration-canary-whisper-review.json"
)

_CONTENT_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "at",
        "be",
        "for",
        "from",
        "if",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "the",
        "this",
        "to",
        "with",
        "you",
        "your",
    }
)
_WHISPER_TEXT_NORMALIZER = EnglishTextNormalizer({})


def normalized_review_text(text: str) -> str:
    normalized = normalize_indextts_spoken_text(str(text or "")).casefold()
    # Whisper commonly emits compact numerals while the safe TTS input spells
    # every digit.  Use Whisper's own English number normalizer so ``five zero
    # three`` and ``503`` compare as the same acoustic content.
    normalized = _WHISPER_TEXT_NORMALIZER(normalized)
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return " ".join(normalized.split())


def normalized_similarity_bp(expected: str, observed: str) -> int:
    expected_norm = normalized_review_text(expected)
    observed_norm = normalized_review_text(observed)
    return int(
        round(
            difflib.SequenceMatcher(None, expected_norm, observed_norm).ratio()
            * 10_000
        )
    )


def content_word_coverage_bp(expected: str, observed: str) -> int:
    expected_words = [
        word
        for word in normalized_review_text(expected).split()
        if word not in _CONTENT_STOPWORDS
    ]
    observed_counts = Counter(normalized_review_text(observed).split())
    expected_counts = Counter(expected_words)
    if not expected_counts:
        return 10_000
    matched = sum(
        min(count, observed_counts.get(word, 0))
        for word, count in expected_counts.items()
    )
    return int(round(matched * 10_000 / sum(expected_counts.values())))


def _resolve_audio_path(manifest_path: Path, value: str) -> Path:
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate.resolve()
    repo_candidate = (REPO_ROOT / candidate).resolve()
    if repo_candidate.is_file():
        return repo_candidate
    return (manifest_path.parent / candidate).resolve()


def review_manifest(
    manifest_path: Path,
    *,
    model_name: str,
    device: str,
    language: str,
    minimum_similarity_bp: int,
    minimum_content_coverage_bp: int,
    maximum_wer_bp: int,
    prior_transcripts: dict[str, str] | None = None,
) -> dict[str, Any]:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    rows = payload.get("responses") or []
    if not isinstance(rows, list) or not rows:
        raise ValueError("generation manifest has no response rows")
    session: LocalWhisperBatchSession | None = None
    prior_transcripts = dict(prior_transcripts or {})
    receipts: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        audio_value = str(
            row.get("preferredAudioPath")
            or row.get("mp3Path")
            or row.get("audioPath")
            or ""
        )
        audio_path = _resolve_audio_path(manifest_path, audio_value)
        expected = str(row.get("text") or "")
        audio = audio_path.read_bytes()
        audio_digest = sha256(audio).hexdigest()
        transcript = prior_transcripts.get(audio_digest, "")
        if not transcript:
            if session is None:
                session = LocalWhisperBatchSession(
                    model_name=model_name,
                    device=device,
                    language=language,
                )
            transcript = session.transcribe_path(audio_path)
        similarity = normalized_similarity_bp(expected, transcript)
        coverage = content_word_coverage_bp(expected, transcript)
        wer = word_error_rate_bp(
            normalized_review_text(expected),
            normalized_review_text(transcript),
        )
        forbidden_negative = bool(re.search(r"(?i)\bnegative\b", transcript))
        passed = (
            bool(transcript.strip())
            and similarity >= minimum_similarity_bp
            and coverage >= minimum_content_coverage_bp
            and wer <= maximum_wer_bp
            and not forbidden_negative
        )
        receipts.append(
            {
                "asr_model": model_name,
                "audio_id": str(row.get("id") or ""),
                "audio_path": str(audio_path.relative_to(REPO_ROOT)),
                "audio_sha256": audio_digest,
                "content_word_coverage_bp": coverage,
                "expected_text_sha256": sha256(expected.encode()).hexdigest(),
                "forbidden_negative_detected": forbidden_negative,
                "normalized_similarity_bp": similarity,
                "passed": passed,
                "transcript": transcript,
                "transcript_sha256": sha256(transcript.encode()).hexdigest(),
                "validation_receipt_id": (
                    "abby-voice-asr-validation:sha256:"
                    + sha256(
                        (
                            audio_digest
                            + "\0"
                            + sha256(expected.encode()).hexdigest()
                            + "\0"
                            + sha256(transcript.encode()).hexdigest()
                            + "\0"
                            + model_name
                        ).encode()
                    ).hexdigest()
                ),
                "wer_bp": wer,
            }
        )
    passed_count = sum(bool(receipt["passed"]) for receipt in receipts)
    return {
        "all_passed": passed_count == len(receipts),
        "failed_count": len(receipts) - passed_count,
        "gates": {
            "maximum_wer_bp": maximum_wer_bp,
            "minimum_content_word_coverage_bp": minimum_content_coverage_bp,
            "minimum_similarity_bp": minimum_similarity_bp,
        },
        "manifest": str(manifest_path.relative_to(REPO_ROOT)),
        "minimum_content_word_coverage_bp": min(
            receipt["content_word_coverage_bp"] for receipt in receipts
        ),
        "minimum_normalized_similarity_bp": min(
            receipt["normalized_similarity_bp"] for receipt in receipts
        ),
        "maximum_observed_wer_bp": max(
            receipt["wer_bp"] for receipt in receipts
        ),
        "passed_count": passed_count,
        "receipt_count": len(receipts),
        "receipts": receipts,
        "remote_writes": False,
        "schema_version": "abby_voice_regeneration_whisper_review_v1",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--report-out", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--model", default="openai/whisper-base")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--language", default="en")
    parser.add_argument("--minimum-similarity-bp", type=int, default=7_800)
    parser.add_argument("--minimum-content-coverage-bp", type=int, default=6_500)
    parser.add_argument("--maximum-wer-bp", type=int, default=3_500)
    parser.add_argument(
        "--reuse-transcripts-from",
        type=Path,
        default=None,
        help="Reuse prior transcripts keyed by verified audio SHA-256.",
    )
    parser.add_argument("--soft-fail", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    prior_transcripts: dict[str, str] = {}
    if args.reuse_transcripts_from is not None:
        prior_payload = json.loads(
            args.reuse_transcripts_from.read_text(encoding="utf-8")
        )
        for receipt in prior_payload.get("receipts") or []:
            if not isinstance(receipt, dict):
                continue
            audio_sha = str(receipt.get("audio_sha256") or "")
            transcript = str(receipt.get("transcript") or "")
            if re.fullmatch(r"[0-9a-f]{64}", audio_sha) and transcript:
                prior_transcripts[audio_sha] = transcript
    report = review_manifest(
        args.manifest.resolve(),
        model_name=args.model,
        device=args.device,
        language=args.language,
        minimum_similarity_bp=args.minimum_similarity_bp,
        minimum_content_coverage_bp=args.minimum_content_coverage_bp,
        maximum_wer_bp=args.maximum_wer_bp,
        prior_transcripts=prior_transcripts,
    )
    args.report_out.parent.mkdir(parents=True, exist_ok=True)
    args.report_out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "all_passed": report["all_passed"],
                "failed_count": report["failed_count"],
                "maximum_observed_wer_bp": report["maximum_observed_wer_bp"],
                "minimum_content_word_coverage_bp": report[
                    "minimum_content_word_coverage_bp"
                ],
                "minimum_normalized_similarity_bp": report[
                    "minimum_normalized_similarity_bp"
                ],
                "passed_count": report["passed_count"],
                "receipt_count": report["receipt_count"],
                "report": str(args.report_out),
            },
            indent=2,
            sort_keys=True,
        )
    )
    if not report["all_passed"] and not args.soft_fail:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
