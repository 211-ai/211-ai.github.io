"""End-to-end mult_turn chat acceptance test for the canonical Abby audio set.

This test intentionally exercises the local product staged by
``scripts/upload_hf_abby_tts_dataset.py``:

ASR -> GraphRAG -> precomputed audio resolver
ASR -> GraphRAG miss -> fallback slotted plan -> TTS
ASR -> GraphRAG repeat/restatement -> precomputed audio resolver

The final audio review is deterministic and offline.  Canonical MP3 output is
checked for exact content address, dataset path linkage, byte length, and MPEG
container framing.  Generated fallback WAV output is checked with the versioned
decode/acoustic quality gate.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = REPO_ROOT / "ipfs_accelerate_py"
DATASETS_ROOT = REPO_ROOT / "ipfs_datasets_py"
sys.path.insert(0, str(PACKAGE_ROOT))
sys.path.insert(0, str(DATASETS_ROOT))

from ipfs_accelerate_py.voice_audio_resolver import (  # noqa: E402
    PrecomputedVoiceAudioResolver,
)
from ipfs_accelerate_py.voice_router import (  # noqa: E402
    GraphRAGVoiceTemplateProvider,
    GroundedSlot,
    GroundingEvidence,
    TelephoneTurnState,
    VoiceProviderCapabilities,
    VoiceResponsePlan,
    VoiceTurnRequest,
    VoiceTurnResult,
    process_telephone_turn,
    process_voice_turn,
    register_voice_provider,
)
from ipfs_datasets_py.voice.audio_quality import (  # noqa: E402
    AudioQualityPolicy,
    build_minimal_wav,
    character_error_rate_bp,
    validate_decode_and_acoustic,
    word_error_rate_bp,
)


CANONICAL_STAGE = REPO_ROOT / "tmp_assets" / "hf-abby-tts-canonical-dataset"
RESOLVER_ROWS = CANONICAL_STAGE / "metadata" / "abby_tts_precomputed_audio_resolver.jsonl"
ROUTE_REVIEW_CASES = (
    ("app_surface_navigation", "Open the calendar screen and help me set a pickup reminder."),
    ("calendar_event_support", "Can you help me schedule a time tomorrow?"),
    ("clarifying_prompt", "I am not sure what kind of help I need yet."),
    ("grounded_211_answer", "I need food help near me."),
    ("live_agent", "Please get me a live person right now."),
    ("provider_contact_support", "I need the phone number so I can call them."),
    ("repeat_or_restate", "Repeat that number more slowly."),
    ("safety_guardrail_support", "I do not feel safe right now."),
    ("service_interaction_support", "I finished intake and still have not received a callback."),
    ("speech_unclear_clarification", "My audio cut out. Can you clarify what you heard?"),
    ("template_guided_fallback", "You do not have enough detail for that exact program."),
    ("wallet_document_support", "Help me upload my ID card in the wallet app."),
)
_DIGIT_WORDS = {
    "zero": "0",
    "oh": "0",
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "nine": "9",
}


def _load_canonical_row_for_route(route: str) -> dict[str, Any]:
    if not RESOLVER_ROWS.exists():
        pytest.skip(f"canonical Abby TTS stage is not available: {RESOLVER_ROWS}")
    with RESOLVER_ROWS.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            routes = row.get("metadata", {}).get("routes") or ()
            if route in routes:
                audio_path = CANONICAL_STAGE / row["metadata"]["dataset_audio_path"]
                if audio_path.is_file():
                    return row
    pytest.skip(f"no canonical resolver row found for route {route!r}")


def _load_short_canonical_rows_for_routes(routes: tuple[str, ...]) -> dict[str, dict[str, Any]]:
    if not RESOLVER_ROWS.exists():
        pytest.skip(f"canonical Abby TTS stage is not available: {RESOLVER_ROWS}")
    selected: dict[str, dict[str, Any]] = {}
    with RESOLVER_ROWS.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            text = str(row.get("spoken_text") or "")
            if not 80 <= len(text) <= 260:
                continue
            content_words = {
                word
                for word in _normalize_for_asr_match(text).split()
                if len(word) >= 4 and not word.isdigit()
            }
            if len(content_words) < 6:
                continue
            if sum(char.isdigit() for char in text) / max(1, len(text)) > 0:
                continue
            if re.search(r"\d\s*[-–—]\s*\d", text):
                continue
            audio_path = CANONICAL_STAGE / row.get("metadata", {}).get("dataset_audio_path", "")
            if not audio_path.is_file():
                continue
            for route in row.get("metadata", {}).get("routes") or ():
                if route not in routes:
                    continue
                score = (abs(len(text) - 150), len(text))
                selected_score = (
                    (abs(len(selected[route]["spoken_text"]) - 150), len(selected[route]["spoken_text"]))
                    if route in selected
                    else None
                )
                if selected_score is None or score < selected_score:
                    selected[route] = row
    missing = sorted(set(routes) - set(selected))
    if missing:
        pytest.skip(f"canonical resolver rows are missing routes: {', '.join(missing)}")
    return selected


def _fetch_staged_audio(artifact: Any) -> bytes:
    rel_path = artifact.metadata.get("dataset_audio_path")
    if not isinstance(rel_path, str) or not rel_path:
        raise FileNotFoundError("resolver artifact does not include dataset_audio_path")
    return (CANONICAL_STAGE / rel_path).read_bytes()


def _has_mp3_frame(payload: bytes) -> bool:
    """Return true when an MP3 payload contains a plausible MPEG audio frame."""

    if payload.startswith(b"ID3") and len(payload) >= 10:
        size = (
            ((payload[6] & 0x7F) << 21)
            | ((payload[7] & 0x7F) << 14)
            | ((payload[8] & 0x7F) << 7)
            | (payload[9] & 0x7F)
        )
        start = 10 + size
    else:
        start = 0
    scan_window = payload[start : start + 4096]
    for index in range(max(0, len(scan_window) - 1)):
        first = scan_window[index]
        second = scan_window[index + 1]
        if first == 0xFF and (second & 0xE0) == 0xE0:
            return True
    return False


def _normalize_for_asr_match(text: str) -> str:
    text = str(text or "").casefold().replace("’", "'")
    tokens = re.findall(r"[a-z0-9']+", text)
    normalized: list[str] = []
    for token in tokens:
        normalized.append(_DIGIT_WORDS.get(token, token))
    return " ".join(normalized)


def _content_word_coverage(reference: str, hypothesis: str) -> int:
    ref_words = {
        word
        for word in _normalize_for_asr_match(reference).split()
        if len(word) >= 4 and not word.isdigit()
    }
    if not ref_words:
        return 10_000
    hyp_words = set(_normalize_for_asr_match(hypothesis).split())
    return int((len(ref_words & hyp_words) * 10_000) / len(ref_words))


def _asr_match_review(reference: str, hypothesis: str) -> dict[str, Any]:
    normalized_reference = _normalize_for_asr_match(reference)
    normalized_hypothesis = _normalize_for_asr_match(hypothesis)
    similarity_bp = int(
        SequenceMatcher(None, normalized_reference, normalized_hypothesis).ratio() * 10_000
    )
    coverage_bp = _content_word_coverage(reference, hypothesis)
    return {
        "character_error_rate_bp": character_error_rate_bp(reference, hypothesis),
        "content_word_coverage_bp": coverage_bp,
        "normalized_similarity_bp": similarity_bp,
        "word_error_rate_bp": word_error_rate_bp(reference, hypothesis),
        "whisper_text": hypothesis,
    }


def _ffprobe_audio_metrics(path: Path) -> dict[str, Any] | None:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return None
    completed = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=codec_name,sample_rate,channels,duration",
            "-of",
            "json",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    streams = payload.get("streams") or []
    if not streams:
        return None
    stream = dict(streams[0])
    return {
        "codec_name": str(stream.get("codec_name") or ""),
        "sample_rate_hz": int(stream.get("sample_rate") or 0),
        "channels": int(stream.get("channels") or 0),
        "duration_ms": int(float(stream.get("duration") or 0.0) * 1000),
    }


def _review_precomputed_mp3(result: VoiceTurnResult, row: Mapping[str, Any]) -> dict[str, Any]:
    assert result.status == "completed"
    assert result.provenance.tts_provider == "precomputed"
    assert result.audio is not None
    assert result.response_text == row["spoken_text"]

    payload = result.audio
    expected_path = CANONICAL_STAGE / row["metadata"]["dataset_audio_path"]
    assert payload == expected_path.read_bytes()
    assert sha256(payload).hexdigest() == row["content_sha256"]
    assert len(payload) == row["byte_length"]
    assert payload.startswith(b"ID3") or payload[:2] in {b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"}
    assert _has_mp3_frame(payload)
    decoded_metrics = _ffprobe_audio_metrics(expected_path)
    if decoded_metrics is not None:
        assert decoded_metrics["codec_name"] == "mp3"
        assert decoded_metrics["sample_rate_hz"] == row["sample_rate_hz"]
        assert decoded_metrics["channels"] == row["channels"]
        assert decoded_metrics["duration_ms"] >= 80

    return {
        "audio_id": row["audio_id"],
        "audio_size_bytes": len(payload),
        "content_sha256": row["content_sha256"],
        "decoded_metrics": decoded_metrics,
        "media_type": row["mime_type"],
        "review": "passed_exact_hash_mp3_container_and_stream_metadata",
        "tts_provider": result.provenance.tts_provider,
    }


def _review_generated_wav(result: VoiceTurnResult) -> dict[str, Any]:
    assert result.status == "degraded"
    assert result.provenance.tts_provider in {"fallback-tts", "injected"}
    assert result.audio is not None

    gate = validate_decode_and_acoustic(
        payload=result.audio,
        declared_media_type="audio/wav",
        declared_sample_rate_hz=24_000,
        declared_channels=1,
        policy=AudioQualityPolicy.default(),
    )
    assert gate.passed, gate.to_dict()
    metrics = dict(gate.metrics)
    assert metrics["duration_ms"] >= 80
    assert metrics["silence_ratio_bp"] < 6_000
    assert metrics["clipping_ratio_bp"] <= 200

    return {
        "audio_size_bytes": len(result.audio),
        "content_sha256": sha256(result.audio).hexdigest(),
        "quality_gate": gate.reason,
        "quality_metrics": metrics,
        "review": "passed_decode_and_acoustic_gate",
        "tts_provider": result.provenance.tts_provider,
    }


@dataclass
class SequentialSpeechProvider:
    transcripts: list[str]
    generated_audio: bytes = field(
        default_factory=lambda: build_minimal_wav(frames=3_600, amplitude=9_000)
    )
    calls: list[tuple[str, Any]] = field(default_factory=list)

    def transcribe(self, audio: object, **kwargs: object) -> str:
        self.calls.append(("transcribe", {"audio": audio, **kwargs}))
        if not self.transcripts:
            raise AssertionError("unexpected extra ASR request")
        return self.transcripts.pop(0)

    def synthesize(self, text: str, **kwargs: object) -> bytes:
        self.calls.append(("synthesize", {"text": text, **kwargs}))
        return self.generated_audio


class MultiturnGraphRAGBackend:
    def __init__(self, first_row: Mapping[str, Any], repeat_row: Mapping[str, Any]) -> None:
        self.first_row = dict(first_row)
        self.repeat_row = dict(repeat_row)
        self.calls: list[dict[str, Any]] = []

    def retrieve(
        self,
        query: str,
        *,
        context: Mapping[str, Any] | None = None,
        prompt_parts: Mapping[str, Any] | None = None,
        **kwargs: object,
    ) -> Mapping[str, Any] | None:
        context = dict(context or {})
        self.calls.append(
            {"query": query, "context": context, "prompt_parts": dict(prompt_parts or {})}
        )
        turn_index = int(context.get("turn_index") or 0)
        if turn_index == 0:
            return {
                "template_id": self.first_row.get("template_id") or "canonical-grounded-answer",
                "template": self.first_row["spoken_text"],
                "slots": [],
                "sources": [],
                "confidence": 1.0,
                "intent": "grounded_211_answer",
            }
        if turn_index == 2:
            assert context.get("previous_assistant_audio_sha256")
            return {
                "template_id": self.repeat_row.get("template_id") or "canonical-repeat-answer",
                "template": self.repeat_row["spoken_text"],
                "slots": [],
                "sources": [],
                "confidence": 1.0,
                "intent": "repeat_or_restate",
            }
        return None


class RouteReviewGraphRAGBackend:
    """Small deterministic retrieval backend for ASR-injected route review."""

    provider_name = "route-review-graphrag"

    def __init__(self, rows_by_route: Mapping[str, Mapping[str, Any]]) -> None:
        self.rows_by_route = {route: dict(row) for route, row in rows_by_route.items()}
        self.calls: list[dict[str, Any]] = []

    def retrieve(
        self,
        query: str,
        *,
        context: Mapping[str, Any] | None = None,
        prompt_parts: Mapping[str, Any] | None = None,
        **kwargs: object,
    ) -> Mapping[str, Any]:
        context = dict(context or {})
        route = self._route_for_query(query)
        row = self.rows_by_route[route]
        self.calls.append(
            {
                "query": query,
                "selected_route": route,
                "expected_route": context.get("expected_route"),
                "prompt_parts": dict(prompt_parts or {}),
            }
        )
        return {
            "template_id": row.get("template_id") or f"canonical-{route}",
            "template": row["spoken_text"],
            "slots": [],
            "sources": [],
            "confidence": 1.0,
            "intent": route,
            "metadata": {"selected_route": route, "audio_id": row["audio_id"]},
        }

    @staticmethod
    def _route_for_query(query: str) -> str:
        text = str(query or "").casefold()
        if "audio cut" in text or "clarify what you heard" in text:
            return "speech_unclear_clarification"
        if "repeat" in text or "slowly" in text:
            return "repeat_or_restate"
        if "wallet" in text or "upload" in text or "id card" in text:
            return "wallet_document_support"
        if "calendar screen" in text or "pickup reminder" in text:
            return "app_surface_navigation"
        if "schedule" in text or "tomorrow" in text:
            return "calendar_event_support"
        if "intake" in text or "callback" in text:
            return "service_interaction_support"
        if "not feel safe" in text or "danger" in text:
            return "safety_guardrail_support"
        if "live person" in text or "live specialist" in text:
            return "live_agent"
        if "phone number" in text or "call them" in text:
            return "provider_contact_support"
        if "not enough detail" in text or "exact program" in text:
            return "template_guided_fallback"
        if "not sure" in text or "what kind of help" in text:
            return "clarifying_prompt"
        if "food" in text:
            return "grounded_211_answer"
        raise LookupError(f"no route matched ASR transcript: {query!r}")


class FallbackLLMSlottedProvider:
    provider_name = "fallback-llm-slotted-template"

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def retrieve(
        self,
        transcript: str,
        *,
        context: Mapping[str, Any] | None = None,
        **kwargs: object,
    ) -> VoiceResponsePlan:
        context = dict(context or {})
        self.calls.append({"transcript": transcript, "context": context})
        assert int(context.get("turn_index") or 0) == 1
        evidence = GroundingEvidence(
            source_id="fallback-current-food-record",
            cid="bafy-fallback-food",
            uri="ipfs://bafy-fallback-food",
            text="Community Food Network can help. Call 503-555-0111.",
            facts={
                "program": "Community Food Network",
                "phone": "503-555-0111",
            },
        )
        return VoiceResponsePlan(
            template_id="fallback-food-frame",
            template="{program} can help. Call {phone}.",
            slots=(
                GroundedSlot("program", "Community Food Network", (evidence.source_id,)),
                GroundedSlot("phone", "503-555-0111", (evidence.source_id,)),
            ),
            evidence=(evidence,),
            confidence=0.93,
            intent="food_assistance",
            metadata={"fallback_llm": True, "slotted_template": True},
        )


def test_multiturn_chat_uses_canonical_audio_fallback_tts_and_reviews_final_audio() -> None:
    grounded_row = _load_canonical_row_for_route("grounded_211_answer")
    repeat_row = _load_canonical_row_for_route("repeat_or_restate")
    resolver = PrecomputedVoiceAudioResolver.from_audio_rows(
        [grounded_row, repeat_row],
        byte_fetcher=_fetch_staged_audio,
    )
    graphrag_backend = MultiturnGraphRAGBackend(grounded_row, repeat_row)
    fallback_llm = FallbackLLMSlottedProvider()
    speech = SequentialSpeechProvider(
        transcripts=[
            "I need food help near me.",
            "That did not match the graph; make me a safe food answer.",
            "Repeat the phone number more slowly.",
        ]
    )

    history: list[dict[str, Any]] = []
    reviews: list[dict[str, Any]] = []
    turn_specs = [
        {"format": "mp3", "expected": grounded_row},
        {"format": "wav", "expected": None},
        {"format": "mp3", "expected": repeat_row},
    ]

    for turn_index, spec in enumerate(turn_specs):
        last_audio_sha = (
            sha256(history[-1]["audio"]).hexdigest()
            if history and history[-1].get("audio") is not None
            else None
        )
        output_format = str(spec["format"])
        request = VoiceTurnRequest(
            audio=f"caller-audio-turn-{turn_index}".encode("utf-8"),
            request_id=f"multiturn-e2e-{turn_index}",
            context={
                "turn_index": turn_index,
                "history": [
                    {
                        "transcript": item["transcript"],
                        "response_text_sha256": sha256(
                            item["response_text"].encode("utf-8")
                        ).hexdigest(),
                    }
                    for item in history
                ],
                "previous_assistant_audio_sha256": last_audio_sha,
            },
            language="en-US",
            locale="en-US",
            voice="abby",
            tts_provider="abby_indextts" if output_format == "mp3" else "fallback-tts",
            tts_model="index-tts-v1" if output_format == "mp3" else "fixture-wav",
            output_format=output_format,
            tts_options=(
                {
                    "provider_version": "1.0.0",
                    "sample_rate_hz": 22_050,
                    "channels": 1,
                    "generation_settings": {"temperature": 0.0},
                    "codec": "mp3",
                }
                if output_format == "mp3"
                else {
                    "provider_version": "fixture-1",
                    "sample_rate_hz": 24_000,
                    "channels": 1,
                    "generation_settings": {"temperature": 0.0},
                    "codec": "wav",
                }
            ),
        )
        result = process_voice_turn(
            request,
            stt_provider=speech,
            template_provider=GraphRAGVoiceTemplateProvider(graphrag_backend),
            fallback_template_provider=fallback_llm,
            tts_provider=speech,
            audio_resolver=resolver,
        )

        expected_row = spec["expected"]
        if expected_row is None:
            review = _review_generated_wav(result)
            assert result.response_text == "Community Food Network can help. Call 503-555-0111."
            assert result.provenance.template_id == "fallback-food-frame"
            assert "fallback_template_provider_used" in result.fallback_reasons
        else:
            review = _review_precomputed_mp3(result, expected_row)
            assert "fallback_template_provider_used" not in result.fallback_reasons
        reviews.append({"turn_index": turn_index, **review})
        history.append(
            {
                "transcript": result.transcript,
                "response_text": result.response_text,
                "audio": result.audio,
                "review": review,
            }
        )

    assert [item["tts_provider"] for item in reviews] == [
        "precomputed",
        "injected",
        "precomputed",
    ]
    assert len([call for call in speech.calls if call[0] == "transcribe"]) == 3
    assert len([call for call in speech.calls if call[0] == "synthesize"]) == 1
    assert len(fallback_llm.calls) == 1
    assert graphrag_backend.calls[2]["context"]["previous_assistant_audio_sha256"]
    assert all(item["review"].startswith("passed_") for item in reviews)


@pytest.fixture(scope="module")
def whisper_base():
    try:
        import numpy as np
        import torch
        from transformers import WhisperForConditionalGeneration, WhisperProcessor
    except Exception as exc:  # pragma: no cover - environment-dependent skip
        pytest.skip(f"Whisper dependencies are unavailable: {exc}")
    try:
        processor = WhisperProcessor.from_pretrained(
            "openai/whisper-base",
            local_files_only=True,
        )
        model = WhisperForConditionalGeneration.from_pretrained(
            "openai/whisper-base",
            local_files_only=True,
        )
    except Exception as exc:  # pragma: no cover - environment-dependent skip
        pytest.skip(f"cached openai/whisper-base is unavailable: {exc}")
    model.eval()
    return {"np": np, "torch": torch, "processor": processor, "model": model}


def _transcribe_with_whisper(audio: bytes, tmp_path: Path, whisper_base: Mapping[str, Any]) -> str:
    audio_path = tmp_path / f"returned-{sha256(audio).hexdigest()[:12]}.mp3"
    audio_path.write_bytes(audio)
    raw = subprocess.check_output(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            str(audio_path),
            "-f",
            "f32le",
            "-acodec",
            "pcm_f32le",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-",
        ]
    )
    np = whisper_base["np"]
    torch = whisper_base["torch"]
    processor = whisper_base["processor"]
    model = whisper_base["model"]
    pcm = np.frombuffer(raw, dtype=np.float32)
    inputs = processor(pcm, sampling_rate=16_000, return_tensors="pt", return_attention_mask=True)
    with torch.no_grad():
        predicted_ids = model.generate(
            inputs.input_features,
            attention_mask=inputs.get("attention_mask"),
            language="en",
            task="transcribe",
        )
    return str(processor.batch_decode(predicted_ids, skip_special_tokens=True)[0]).strip()


def test_dozen_asr_injected_examples_retrieve_expected_routes_and_whisper_match_audio(
    tmp_path: Path,
    whisper_base: Mapping[str, Any],
) -> None:
    routes = tuple(route for route, _query in ROUTE_REVIEW_CASES)
    rows_by_route = _load_short_canonical_rows_for_routes(routes)
    resolver = PrecomputedVoiceAudioResolver.from_audio_rows(
        [rows_by_route[route] for route in routes],
        byte_fetcher=_fetch_staged_audio,
    )
    backend = RouteReviewGraphRAGBackend(rows_by_route)
    provider = GraphRAGVoiceTemplateProvider(backend)

    reviews: list[dict[str, Any]] = []
    for index, (expected_route, asr_text) in enumerate(ROUTE_REVIEW_CASES):
        speech = SequentialSpeechProvider(transcripts=[asr_text])
        row = rows_by_route[expected_route]
        result = process_voice_turn(
            VoiceTurnRequest(
                audio=f"caller-audio-route-review-{index}".encode("utf-8"),
                request_id=f"route-review-{index}-{expected_route}",
                context={"expected_route": expected_route, "review_index": index},
                language="en-US",
                locale="en-US",
                voice="abby",
                tts_provider="abby_indextts",
                tts_model="index-tts-v1",
                output_format="mp3",
                tts_options={
                    "provider_version": "1.0.0",
                    "sample_rate_hz": 22_050,
                    "channels": 1,
                    "generation_settings": {"temperature": 0.0},
                    "codec": "mp3",
                },
            ),
            stt_provider=speech,
            template_provider=provider,
            tts_provider=speech,
            audio_resolver=resolver,
        )
        retrieval_call = backend.calls[-1]
        assert result.transcript == asr_text
        assert retrieval_call["query"] == asr_text
        assert retrieval_call["prompt_parts"]["query"] == asr_text
        assert retrieval_call["selected_route"] == expected_route
        assert result.intent == expected_route
        assert result.provenance.template_id == (row.get("template_id") or f"canonical-{expected_route}")
        mp3_review = _review_precomputed_mp3(result, row)

        whisper_text = _transcribe_with_whisper(result.audio or b"", tmp_path, whisper_base)
        asr_review = _asr_match_review(row["spoken_text"], whisper_text)
        assert asr_review["normalized_similarity_bp"] >= 7_800, asr_review
        assert asr_review["content_word_coverage_bp"] >= 6_500, asr_review
        reviews.append(
            {
                "route": expected_route,
                "injected_asr_text": asr_text,
                "selected_audio_id": row["audio_id"],
                "retrieval": "passed",
                **mp3_review,
                **asr_review,
            }
        )

    assert len(reviews) == 12
    assert {review["route"] for review in reviews} == set(routes)
    assert not [call for call in speech.calls if call[0] == "synthesize"]


# The product-facing surface review deliberately reuses the same twelve
# canonical examples above.  Each surface is one six-turn conversation.  Four
# cases are deterministic GraphRAG/audio-cache misses so the suite can prove the
# fallback and append-only response-DAG candidate path without contacting HF.
MULTISURFACE_MISS_ROUTES = frozenset(
    {
        "calendar_event_support",
        "provider_contact_support",
        "speech_unclear_clarification",
        "template_guided_fallback",
    }
)


class MultisurfaceGraphRAGBackend:
    """Deterministic primary GraphRAG with explicit hit/miss receipts."""

    provider_name = "multisurface-primary-graphrag"

    def __init__(self, rows_by_route: Mapping[str, Mapping[str, Any]]) -> None:
        self.rows_by_route = {route: dict(row) for route, row in rows_by_route.items()}
        self.calls: list[dict[str, Any]] = []

    def retrieve(
        self,
        query: str,
        *,
        context: Mapping[str, Any] | None = None,
        prompt_parts: Mapping[str, Any] | None = None,
        **kwargs: object,
    ) -> Mapping[str, Any] | None:
        context = dict(context or {})
        route = RouteReviewGraphRAGBackend._route_for_query(query)
        retrieval = "miss" if route in MULTISURFACE_MISS_ROUTES else "hit"
        self.calls.append(
            {
                "query": query,
                "selected_route": route,
                "expected_route": context.get("expected_route"),
                "surface": context.get("surface"),
                "turn_index": context.get("turn_index"),
                "history_size": len(context.get("history") or ()),
                "previous_assistant_audio_sha256": context.get(
                    "previous_assistant_audio_sha256"
                ),
                "prompt_parts": dict(prompt_parts or {}),
                "retrieval": retrieval,
            }
        )
        if retrieval == "miss":
            return None
        row = self.rows_by_route[route]
        return {
            "template_id": row.get("template_id") or f"canonical-{route}",
            "template": row["spoken_text"],
            "slots": [],
            "sources": [],
            "confidence": 1.0,
            "intent": route,
            "metadata": {
                "selected_route": route,
                "audio_id": row["audio_id"],
                "retrieval": "primary-graphrag-hit",
            },
        }


class SlottedMissFallbackProvider:
    """Offline stand-in for fallback LLM output constrained to one grounded slot."""

    provider_name = "multisurface-fallback-slotted-llm"

    def __init__(self, rows_by_route: Mapping[str, Mapping[str, Any]]) -> None:
        self.rows_by_route = {route: dict(row) for route, row in rows_by_route.items()}
        self.calls: list[dict[str, Any]] = []

    def retrieve(
        self,
        transcript: str,
        *,
        context: Mapping[str, Any] | None = None,
        **kwargs: object,
    ) -> VoiceResponsePlan:
        context = dict(context or {})
        route = str(context.get("expected_route") or "")
        assert route in MULTISURFACE_MISS_ROUTES
        row = self.rows_by_route[route]
        source_id = f"fallback-response:{row['response_id']}"
        response = str(row["spoken_text"])
        self.calls.append(
            {
                "route": route,
                "surface": context.get("surface"),
                "turn_index": context.get("turn_index"),
                "slotted_template": True,
            }
        )
        evidence = GroundingEvidence(
            source_id=source_id,
            cid=f"local-only:{row['audio_id']}",
            text=response,
            facts={"response": response},
            metadata={"publication": "disabled-in-offline-test"},
        )
        return VoiceResponsePlan(
            template_id=row.get("template_id") or f"fallback-slotted-{route}",
            template="{response}",
            slots=(GroundedSlot("response", response, (source_id,)),),
            evidence=(evidence,),
            confidence=1.0,
            intent=route,
            metadata={
                "fallback_llm": True,
                "slotted_template": True,
                "candidate_for_response_dag": True,
            },
        )


@dataclass
class LocalCanonicalEndpointSpeech:
    """Read-only endpoint seam returning already staged canonical audio bytes."""

    audio_by_text: Mapping[str, bytes]
    synthesize_calls: list[dict[str, Any]] = field(default_factory=list)

    def transcribe(self, audio: object, **kwargs: object) -> str:
        raise AssertionError("text-injected ASR must skip speech transcription")

    def synthesize(self, text: str, **kwargs: object) -> bytes:
        self.synthesize_calls.append({"text": text, **kwargs})
        try:
            return self.audio_by_text[text]
        except KeyError as exc:
            raise AssertionError(f"unexpected local endpoint text: {text!r}") from exc


class LocalResponseDagCandidateSink:
    """Append-only, idempotent JSONL staging sink; never publishes remotely."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._candidate_ids: set[str] = set()
        if path.is_file():
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    self._candidate_ids.add(str(json.loads(line)["candidate_id"]))

    def append(self, candidate: Mapping[str, Any]) -> bool:
        candidate_id = str(candidate.get("candidate_id") or "")
        if not candidate_id:
            raise ValueError("response-DAG candidate must have a candidate_id")
        if candidate_id in self._candidate_ids:
            return False
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(dict(candidate), sort_keys=True) + "\n")
        self._candidate_ids.add(candidate_id)
        return True


def _build_local_response_dag_candidate(
    *,
    result: VoiceTurnResult,
    row: Mapping[str, Any],
    surface: str,
    session_id: str,
    turn_index: int,
    resolver_reason: str,
    whisper_review: Mapping[str, Any],
) -> dict[str, Any]:
    stable_identity = {
        "audio_id": row["audio_id"],
        "response_id": row["response_id"],
        "session_id": session_id,
        "spoken_text_sha256": row["text_sha256"],
        "surface": surface,
        "turn_index": turn_index,
    }
    digest = sha256(
        json.dumps(stable_identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "schema_version": "abby_voice_response_dag_candidate_v1",
        "candidate_id": f"response-dag-candidate:sha256:{digest}",
        "append_target": "huggingface-response-dag",
        "publication_status": "local_validated_not_published",
        "surface": surface,
        "session_id": session_id,
        "turn_index": turn_index,
        "intent": result.intent,
        "template_id": result.template_id,
        "spoken_text": result.response_text,
        "spoken_text_sha256": row["text_sha256"],
        "audio_content_sha256": sha256(result.audio or b"").hexdigest(),
        "source_audio_id": row["audio_id"],
        "source_response_id": row["response_id"],
        "cache_outcome": "miss",
        "resolver_reason": resolver_reason,
        "retrieval_outcome": "fallback-slotted-hit",
        "validation": {
            "whisper_match": True,
            "normalized_similarity_bp": whisper_review["normalized_similarity_bp"],
            "content_word_coverage_bp": whisper_review["content_word_coverage_bp"],
        },
        "privacy": {
            "caller_audio_stored": False,
            "caller_transcript_stored": False,
            "caller_transcript_sha256": sha256(
                result.transcript.encode("utf-8")
            ).hexdigest(),
        },
    }


def _telephone_mulaw_surface_audio(audio: bytes, tmp_path: Path, stem: str) -> tuple[bytes, Path]:
    source = tmp_path / f"{stem}-source.mp3"
    output = tmp_path / f"{stem}-telephone-mulaw.wav"
    source.write_bytes(audio)
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-i",
            str(source),
            "-ac",
            "1",
            "-ar",
            "8000",
            "-c:a",
            "pcm_mulaw",
            str(output),
        ],
        check=True,
    )
    return output.read_bytes(), output


def _assert_safe_phone_and_address_rendering(text: str) -> None:
    lowered = text.casefold()
    assert "negative" not in lowered
    assert "(" not in text and ")" not in text
    # Numeric separators in addresses/phone numbers are the punctuation that
    # caused IndexTTS to say "negative". Prose em dashes remain allowed.
    digitish = r"(?:\d+|zero|one|two|three|four|five|six|seven|eight|nine)"
    assert not re.search(
        rf"\b{digitish}(?:\s+{digitish})*\s*[-–—]\s*{digitish}\b",
        text,
        re.IGNORECASE,
    )


def _ratio_bp(numerator: int, denominator: int) -> int:
    return int(round((numerator * 10_000) / denominator)) if denominator else 0


def test_dozen_text_injected_multiturn_cases_score_surfaces_and_stage_cache_misses(
    tmp_path: Path,
    whisper_base: Mapping[str, Any],
) -> None:
    routes = tuple(route for route, _query in ROUTE_REVIEW_CASES)
    rows_by_route = _load_short_canonical_rows_for_routes(routes)
    cache_hit_routes = tuple(route for route in routes if route not in MULTISURFACE_MISS_ROUTES)
    resolver = PrecomputedVoiceAudioResolver.from_audio_rows(
        [rows_by_route[route] for route in cache_hit_routes],
        byte_fetcher=_fetch_staged_audio,
    )
    endpoint = LocalCanonicalEndpointSpeech(
        {
            str(row["spoken_text"]): (
                CANONICAL_STAGE / row["metadata"]["dataset_audio_path"]
            ).read_bytes()
            for row in rows_by_route.values()
        }
    )
    primary_backend = MultisurfaceGraphRAGBackend(rows_by_route)
    primary_provider = GraphRAGVoiceTemplateProvider(primary_backend)
    fallback_provider = SlottedMissFallbackProvider(rows_by_route)
    candidate_sink = LocalResponseDagCandidateSink(tmp_path / "response-dag-candidates.jsonl")
    histories: dict[str, list[dict[str, Any]]] = {"web": [], "telephone": []}
    reviews: list[dict[str, Any]] = []
    staged_candidates: list[dict[str, Any]] = []

    for case_index, (expected_route, asr_text) in enumerate(ROUTE_REVIEW_CASES):
        surface = "web" if case_index < 6 else "telephone"
        session_id = f"offline-{surface}-multiturn"
        history = histories[surface]
        turn_index = len(history)
        previous_audio_sha = (
            str(history[-1]["surface_audio_sha256"]) if history else None
        )
        row = rows_by_route[expected_route]
        result = process_voice_turn(
            VoiceTurnRequest(
                transcript=asr_text,
                request_id=f"multisurface-{surface}-{turn_index}-{expected_route}",
                context={
                    "expected_route": expected_route,
                    "surface": surface,
                    "session_id": session_id,
                    "turn_index": turn_index,
                    "history": [
                        {
                            "route": item["route"],
                            "response_text_sha256": item["response_text_sha256"],
                        }
                        for item in history
                    ],
                    "previous_assistant_audio_sha256": previous_audio_sha,
                },
                language="en-US",
                locale="en-US",
                voice="abby",
                tts_provider="abby_indextts",
                tts_model="index-tts-v1",
                output_format="mp3",
                tts_options={
                    "provider_version": "1.0.0",
                    "sample_rate_hz": 22_050,
                    "channels": 1,
                    "generation_settings": {"temperature": 0.0},
                    "codec": "mp3",
                },
            ),
            template_provider=primary_provider,
            fallback_template_provider=fallback_provider,
            tts_provider=endpoint,
            audio_resolver=resolver,
        )

        assert result.transcript == asr_text
        assert next(trace for trace in result.traces if trace.stage == "transcription").status == "skipped"
        assert result.intent == expected_route
        assert result.response_text == row["spoken_text"]
        assert result.audio == (
            CANONICAL_STAGE / row["metadata"]["dataset_audio_path"]
        ).read_bytes()
        _assert_safe_phone_and_address_rendering(result.response_text)

        primary_call = primary_backend.calls[-1]
        assert primary_call["query"] == asr_text
        assert primary_call["prompt_parts"]["query"] == asr_text
        assert primary_call["selected_route"] == expected_route
        assert primary_call["surface"] == surface
        assert primary_call["turn_index"] == turn_index
        assert primary_call["history_size"] == turn_index
        assert primary_call["previous_assistant_audio_sha256"] == previous_audio_sha

        precomputed = dict(result.provenance.metadata["precomputed_audio"] or {})
        expected_cache = (
            "miss" if expected_route in MULTISURFACE_MISS_ROUTES else "hit"
        )
        assert precomputed["status"] == expected_cache
        expected_retrieval = (
            "miss" if expected_route in MULTISURFACE_MISS_ROUTES else "hit"
        )
        assert primary_call["retrieval"] == expected_retrieval
        if expected_cache == "hit":
            assert result.status == "completed"
            assert result.provenance.tts_provider == "precomputed"
            assert "fallback_template_provider_used" not in result.fallback_reasons
        else:
            assert result.status == "degraded"
            assert result.provenance.tts_provider == "injected"
            assert "fallback_template_provider_used" in result.fallback_reasons

        surface_audio = result.audio or b""
        media_review: dict[str, Any]
        if surface == "telephone":
            surface_audio, telephone_path = _telephone_mulaw_surface_audio(
                surface_audio,
                tmp_path,
                f"{turn_index}-{expected_route}",
            )
            metrics = _ffprobe_audio_metrics(telephone_path)
            assert metrics is not None
            assert metrics["codec_name"] == "pcm_mulaw"
            assert metrics["sample_rate_hz"] == 8_000
            assert metrics["channels"] == 1
            media_review = {"transport": "telephone-pcm-mulaw-8khz", **metrics}
        else:
            assert _has_mp3_frame(surface_audio)
            media_review = {"transport": "web-mp3-22050hz"}

        whisper_text = _transcribe_with_whisper(surface_audio, tmp_path, whisper_base)
        whisper_review = _asr_match_review(row["spoken_text"], whisper_text)
        assert whisper_review["normalized_similarity_bp"] >= 7_800, whisper_review
        assert whisper_review["content_word_coverage_bp"] >= 6_500, whisper_review
        assert "negative" not in whisper_text.casefold()

        if expected_cache == "miss":
            candidate = _build_local_response_dag_candidate(
                result=result,
                row=row,
                surface=surface,
                session_id=session_id,
                turn_index=turn_index,
                resolver_reason=str(precomputed["reason"]),
                whisper_review=whisper_review,
            )
            assert candidate_sink.append(candidate)
            staged_candidates.append(candidate)

        history_item = {
            "route": expected_route,
            "response_text_sha256": sha256(
                result.response_text.encode("utf-8")
            ).hexdigest(),
            "surface_audio_sha256": sha256(surface_audio).hexdigest(),
        }
        history.append(history_item)
        reviews.append(
            {
                "route": expected_route,
                "surface": surface,
                "turn_index": turn_index,
                "retrieval": expected_retrieval,
                "audio_cache": expected_cache,
                "whisper_match": True,
                **media_review,
                **whisper_review,
            }
        )

    assert len(reviews) == 12
    assert [item["turn_index"] for item in reviews if item["surface"] == "web"] == list(
        range(6)
    )
    assert [
        item["turn_index"] for item in reviews if item["surface"] == "telephone"
    ] == list(range(6))

    retrieval_hits = sum(item["retrieval"] == "hit" for item in reviews)
    retrieval_misses = len(reviews) - retrieval_hits
    audio_cache_hits = sum(item["audio_cache"] == "hit" for item in reviews)
    audio_cache_misses = len(reviews) - audio_cache_hits
    scorecard = {
        "turn_count": len(reviews),
        "retrieval_hits": retrieval_hits,
        "retrieval_misses": retrieval_misses,
        "retrieval_hit_ratio_bp": _ratio_bp(retrieval_hits, len(reviews)),
        "retrieval_miss_ratio_bp": _ratio_bp(retrieval_misses, len(reviews)),
        "audio_cache_hits": audio_cache_hits,
        "audio_cache_misses": audio_cache_misses,
        "audio_cache_hit_ratio_bp": _ratio_bp(audio_cache_hits, len(reviews)),
        "audio_cache_miss_ratio_bp": _ratio_bp(audio_cache_misses, len(reviews)),
        "whisper_matches": sum(item["whisper_match"] for item in reviews),
    }
    assert scorecard == {
        "turn_count": 12,
        "retrieval_hits": 8,
        "retrieval_misses": 4,
        "retrieval_hit_ratio_bp": 6_667,
        "retrieval_miss_ratio_bp": 3_333,
        "audio_cache_hits": 8,
        "audio_cache_misses": 4,
        "audio_cache_hit_ratio_bp": 6_667,
        "audio_cache_miss_ratio_bp": 3_333,
        "whisper_matches": 12,
    }
    assert len(endpoint.synthesize_calls) == 4
    assert len(fallback_provider.calls) == 4

    staged_rows = [
        json.loads(line)
        for line in candidate_sink.path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(staged_rows) == 4
    assert {row["surface"] for row in staged_rows} == {"web", "telephone"}
    assert all(row["publication_status"] == "local_validated_not_published" for row in staged_rows)
    assert all(row["privacy"]["caller_audio_stored"] is False for row in staged_rows)
    assert all(row["privacy"]["caller_transcript_stored"] is False for row in staged_rows)
    assert not candidate_sink.append(staged_candidates[0])
    assert len(candidate_sink.path.read_text(encoding="utf-8").splitlines()) == 4

    report = {
        "schema_version": "abby_voice_multisurface_review_v1",
        "mode": "offline-no-huggingface-reads-or-writes",
        "scorecard": scorecard,
        "surface_turns": {
            surface: sum(item["surface"] == surface for item in reviews)
            for surface in ("web", "telephone")
        },
        "telephone_transport": {
            "codec": "pcm_mulaw",
            "sample_rate_hz": 8_000,
            "channels": 1,
        },
        "staged_response_dag_candidate_count": len(staged_rows),
        "minimum_whisper_normalized_similarity_bp": min(
            item["normalized_similarity_bp"] for item in reviews
        ),
        "minimum_whisper_content_word_coverage_bp": min(
            item["content_word_coverage_bp"] for item in reviews
        ),
        "reviews": reviews,
    }
    (tmp_path / "abby-voice-multisurface-review.json").write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def test_phone_and_address_slot_normalization_blocks_negative_pronunciation_traps() -> None:
    from scripts.precompute_indextts_responses import normalize_slot_value_text

    phone = normalize_slot_value_text("phone", "+1 (503) 555-0100")
    address = normalize_slot_value_text(
        "address",
        "11-32 Southwest thirteenth Avenue, Portland, OR 97205",
    )

    assert phone == "five zero three, five five five, zero one zero zero"
    assert address == (
        "one one three two Southwest thirteenth Avenue, Portland, Oregon. "
        "ZIP code nine seven two zero five"
    )
    for rendered in (phone, address):
        _assert_safe_phone_and_address_rendering(rendered)


@pytest.mark.parametrize(
    "raw_address",
    (
        "11-32 Southwest 13th Avenue, Portland, OR 97205",
        "11-32 SW 13th Ave, Portland, OR 97205",
    ),
)
def test_address_slot_normalization_regression_for_abbreviated_street_tokens(
    raw_address: str,
) -> None:
    from scripts.precompute_indextts_responses import normalize_slot_value_text

    rendered = normalize_slot_value_text("address", raw_address)
    _assert_safe_phone_and_address_rendering(rendered)


@dataclass
class SyntheticTelephoneTTS:
    name: str
    fail_with_timeout: bool = False
    spoken: list[str] = field(default_factory=list)

    def synthesize(self, text: str, **kwargs: object) -> bytes:
        self.spoken.append(text)
        if self.fail_with_timeout:
            raise TimeoutError("synthetic telephone provider timeout")
        # The fully synthetic fixture makes the provider input recoverable
        # from its output so the asserted audio transcript is deterministic.
        return b"RIFF\x00\x00\x00\x00WAVE" + text.encode("utf-8")

    def transcribe(self, audio: object, **kwargs: object) -> str:
        raise AssertionError("telephone fixture injects text at the ASR boundary")


class SyntheticTelephonePlans:
    provider_name = "synthetic-telephone-graphrag"

    def retrieve(
        self,
        transcript: str,
        *,
        context: Mapping[str, object] | None = None,
        **kwargs: object,
    ) -> VoiceResponsePlan:
        turn_index = int((context or {})["turn_index"])
        if turn_index == 0:
            facts = {"phone": "+1 (503) 555-0100"}
            return VoiceResponsePlan(
                template_id="telephone-phone-v1",
                template="Call {phone}.",
                slots=(GroundedSlot("phone", facts["phone"], ("phone-source",)),),
                evidence=(GroundingEvidence("phone-source", facts=facts),),
                intent="provider_contact_support",
            )
        if turn_index == 1:
            facts = {
                "address": (
                    "11-32 SW 13th Ave (main office), Portland, OR 97205"
                )
            }
            return VoiceResponsePlan(
                template_id="telephone-address-v1",
                template="The address is {address}.",
                slots=(
                    GroundedSlot(
                        "address",
                        facts["address"],
                        ("address-source",),
                    ),
                ),
                evidence=(GroundingEvidence("address-source", facts=facts),),
                intent="service_location",
            )
        return VoiceResponsePlan(
            template_id="telephone-handoff-v1",
            template="I will connect you with a person now.",
            intent="service_followup",
        )


def _synthetic_telephone_audio_text(audio: bytes) -> str:
    assert audio.startswith(b"RIFF\x00\x00\x00\x00WAVE")
    return audio[12:].decode("utf-8")


def _assert_no_telephone_audio_markers(text: str) -> None:
    lowered = text.casefold()
    assert "negative" not in lowered
    assert "parenthesis" not in lowered
    assert "parentheses" not in lowered
    assert "hyphen" not in lowered
    assert " dash " not in f" {lowered} "
    assert "(" not in text and ")" not in text
    assert not re.search(r"\d\s*[-–—]\s*\d", text)


def test_synthetic_telephone_multiturn_retry_barge_in_and_escalation() -> None:
    """The telephone adapter stays thin and every turn uses the shared router."""

    primary = SyntheticTelephoneTTS(
        "synthetic-telephone-primary",
        fail_with_timeout=True,
    )
    retry = SyntheticTelephoneTTS("synthetic-telephone-retry")
    register_voice_provider(
        "synthetic-telephone-retry",
        lambda: retry,
        capabilities=VoiceProviderCapabilities(
            transcription=False,
            synthesis=True,
            audio_formats=("wav",),
        ),
    )
    plans = SyntheticTelephonePlans()
    state = TelephoneTurnState(
        call_id="synthetic-call-do-not-persist",
        max_turns=4,
    )

    first = process_telephone_turn(
        VoiceTurnRequest(
            transcript="What phone number should I call?",
            request_id="synthetic-telephone-0",
            tts_providers=("synthetic-telephone-retry",),
            output_format="wav",
        ),
        state,
        template_provider=plans,
        tts_provider=primary,
    )
    assert first.status == "degraded"
    assert first.audio is not None
    first_audio_text = _synthetic_telephone_audio_text(first.audio)
    assert (
        "five zero three, five five five, zero one zero zero"
        in first_audio_text
    )
    _assert_no_telephone_audio_markers(first_audio_text)
    synthesis = [trace for trace in first.traces if trace.stage == "synthesis"]
    assert [trace.status for trace in synthesis] == ["failed", "succeeded"]
    assert synthesis[0].details == {
        "attempt": 1,
        "retry": False,
        "will_retry": True,
    }
    assert synthesis[1].details["attempt"] == 2
    assert synthesis[1].details["retry"] is True
    assert (
        next(
            trace
            for trace in first.traces
            if trace.stage == "telephone_escalation"
        ).status
        == "skipped"
    )

    state = state.advance(first, barge_in=True)
    second = process_telephone_turn(
        VoiceTurnRequest(
            transcript="Stop and give me the address instead.",
            request_id="synthetic-telephone-1",
            tts_providers=("synthetic-telephone-retry",),
            output_format="wav",
        ),
        state,
        template_provider=plans,
        tts_provider=primary,
    )
    assert second.audio is not None
    second_audio_text = _synthetic_telephone_audio_text(second.audio)
    assert "one one three two SW 13th Ave" in second_audio_text
    assert "ZIP code nine seven two zero five" in second_audio_text
    assert "main office" in second_audio_text
    _assert_no_telephone_audio_markers(second_audio_text)
    telephone_metadata = second.provenance.metadata["telephone"]
    assert telephone_metadata["turn_index"] == 1
    assert telephone_metadata["barge_in"] is True
    assert (
        telephone_metadata["previous_response_sha256"]
        == first.provenance.response_text_sha256
    )

    state = state.advance(second)
    exhausted = process_telephone_turn(
        VoiceTurnRequest(
            transcript="I still need help.",
            request_id="synthetic-telephone-2",
            output_format="wav",
        ),
        state,
        template_provider=plans,
        tts_provider=primary,
    )
    assert exhausted.status == "text_only"
    assert exhausted.audio is None
    assert "tts_failed" in exhausted.fallback_reasons
    assert "telephone_human_escalation" in exhausted.fallback_reasons
    escalation = next(
        trace
        for trace in exhausted.traces
        if trace.stage == "telephone_escalation"
    )
    assert escalation.status == "succeeded"
    assert escalation.provider == "human_handoff"
    assert escalation.details["reason"] == "provider_exhausted"
    assert (
        exhausted.provenance.metadata["telephone"]["escalation_required"]
        is True
    )

    receipt = json.dumps(exhausted.to_dict(), sort_keys=True)
    assert "synthetic-call-do-not-persist" not in receipt
    assert state.call_id_sha256 in receipt
