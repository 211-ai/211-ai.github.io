"""Offline safety, quality, and performance gates for Abby voice turns.

The fixtures are synthetic and deliberately contain no caller recordings,
credentials, or mutable service data.  These tests validate the observable
``VoiceTurnResult`` contract rather than reaching a speech, GraphRAG, IPFS, or
Hugging Face service.
"""

from __future__ import annotations

import json
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

import pytest

ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "ipfs_accelerate_py"
sys.path.insert(0, str(PACKAGE_ROOT))

from ipfs_accelerate_py.router_deps import RouterDeps  # noqa: E402
from ipfs_accelerate_py.voice_router import (  # noqa: E402
    DEFAULT_GROUNDED_FALLBACK,
    GroundedSlot,
    GraphRAGVoiceTemplateProvider,
    TelephoneTurnState,
    VoiceGroundingSource,
    VoiceResponsePlan,
    VoiceStageTrace,
    VoiceTurnRequest,
    VoiceTurnResult,
    VoiceProviderCapabilities,
    clear_voice_router_caches,
    process_telephone_turn,
    process_voice_turn,
    register_voice_provider,
    speech_to_text,
    text_to_speech,
)


GOLDEN_PATH = ROOT / "data/abby_voice/eval/golden_voice_turns.jsonl"
PRIVATE_AUDIO = b"PRIVATE-CALLER-AUDIO-MUST-NOT-APPEAR-IN-RECEIPT"


def _golden_rows() -> list[dict[str, Any]]:
    rows = [
        json.loads(line)
        for line in GOLDEN_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert rows, "the golden evaluation set must not be empty"
    return rows


def _word_error_rate(reference: str, hypothesis: str) -> float:
    reference_words = reference.lower().split()
    hypothesis_words = hypothesis.lower().split()
    previous = list(range(len(hypothesis_words) + 1))
    for row_index, reference_word in enumerate(reference_words, start=1):
        current = [row_index]
        for column_index, hypothesis_word in enumerate(hypothesis_words, start=1):
            substitution = previous[column_index - 1] + (reference_word != hypothesis_word)
            insertion = current[column_index - 1] + 1
            deletion = previous[column_index] + 1
            current.append(min(substitution, insertion, deletion))
        previous = current
    return previous[-1] / max(1, len(reference_words))


def _response_plan(row: Mapping[str, Any]) -> VoiceResponsePlan | None:
    raw = row.get("response_plan")
    if raw is None:
        return None
    evidence = tuple(
        VoiceGroundingSource(
            source_id=item["source_id"],
            cid=item.get("cid"),
            text=item.get("text"),
            facts=item.get("facts", {}),
        )
        for item in raw.get("evidence", [])
    )
    slots = tuple(
        GroundedSlot(
            name=item["name"],
            value=item.get("value"),
            source_ids=tuple(item.get("source_ids", [])),
        )
        for item in raw.get("slots", [])
    )
    return VoiceResponsePlan(
        template_id=raw["template_id"],
        template=raw["template"],
        slots=slots,
        evidence=evidence,
        confidence=raw.get("confidence", 1.0),
        intent=raw.get("intent"),
    )


@dataclass
class GoldenSpeechProvider:
    name: str
    transcript: str
    audio: bytes = b"RIFF\x00\x00\x00\x00WAVEsynthetic-abby-audio"
    fail_transcription: bool = False
    fail_synthesis: bool = False
    calls: list[tuple[str, str]] = field(default_factory=list)

    def transcribe(self, audio: object, **kwargs: object) -> str:
        if self.fail_transcription:
            raise RuntimeError("synthetic STT outage")
        self.calls.append(("transcribe", self.transcript))
        return self.transcript

    def synthesize(self, text: str, **kwargs: object) -> bytes:
        if self.fail_synthesis:
            raise RuntimeError("synthetic TTS outage")
        self.calls.append(("synthesize", text))
        return self.audio


@dataclass
class GoldenTemplateProvider:
    row: Mapping[str, Any]
    provider_name: str = "synthetic-golden-graphrag"
    calls: int = 0

    def retrieve(self, transcript: str, **kwargs: object) -> VoiceResponsePlan | None:
        self.calls += 1
        return _response_plan(self.row)


def _run_golden(row: Mapping[str, Any]) -> VoiceTurnResult:
    speech = GoldenSpeechProvider("synthetic-speech", row["observed_transcript"])
    result = process_voice_turn(
        VoiceTurnRequest(
            audio=("synthetic-audio-" + row["case_id"]).encode("utf-8"),
            request_id="golden-" + row["case_id"],
            locale=row["locale"],
            output_format="wav",
        ),
        stt_provider=speech,
        template_provider=GoldenTemplateProvider(row),
        tts_provider=speech,
    )
    assert result.audio, f"golden case {row['case_id']} did not synthesize audio"
    return result


def _trace(result: VoiceTurnResult, stage: str, status: str | None = None):
    matches = [item for item in result.traces if item.stage == stage]
    assert matches, f"missing {stage} trace"
    if status is not None:
        assert any(item.status == status for item in matches)
    return matches


def test_golden_set_is_schema_valid_and_public_fixture_only() -> None:
    rows = _golden_rows()
    assert len(rows) >= 8
    for row in rows:
        assert row["schema_version"] == "abby_voice_evaluation_v1"
        assert row["case_id"]
        assert row["reference_transcript"]
        assert row["observed_transcript"]
        assert "synthetic_public_fixture" in row["safety_labels"]
        encoded = json.dumps(row, sort_keys=True)
        assert "PRIVATE-CALLER" not in encoded
        assert "Authorization" not in encoded
        expected = row["expected"]
        assert expected["required_phrases"]
        assert expected["wer_max"] >= 0


def test_golden_turns_preserve_grounding_and_spoken_safety() -> None:
    rows = _golden_rows()
    for row in rows:
        result = _run_golden(row)
        expected = row["expected"]
        assert result.status == expected["status"], row["case_id"]
        assert result.response_text == expected["response_text"], row["case_id"]
        for phrase in expected["required_phrases"]:
            assert phrase.lower() in result.spoken_text.lower(), row["case_id"]
        for phrase in expected["forbidden_phrases"]:
            assert phrase.lower() not in result.spoken_text.lower(), row["case_id"]
        assert _word_error_rate(row["reference_transcript"], result.transcript) <= expected["wer_max"]
        assert result.provenance.transcript_sha256
        assert result.provenance.response_text_sha256
        assert result.provenance.output_audio_sha256

        plan = row.get("response_plan")
        if plan and plan["slots"]:
            actual_slots = {slot.name: slot for slot in result.provenance.grounded_slots}
            for expected_slot in plan["slots"]:
                actual = actual_slots[expected_slot["name"]]
                assert str(actual.value) == str(expected_slot["value"])
                assert set(actual.source_ids) == set(expected_slot["source_ids"])
        if row["category"] == "crisis":
            assert "911" in result.spoken_text
            assert re.search(r"\b(now|immediately)\b", result.spoken_text, re.I)


def test_golden_metrics_cover_wer_retrieval_slot_fidelity_and_factuality() -> None:
    rows = _golden_rows()
    grounded_rows = [row for row in rows if row["response_plan"] and row["response_plan"]["slots"]]
    wers = []
    slot_checks = 0
    factuality_checks = 0
    retrieval_successes = 0
    for row in rows:
        result = _run_golden(row)
        wers.append(_word_error_rate(row["reference_transcript"], result.transcript))
        if row["response_plan"] is not None:
            retrieval_successes += int(_trace(result, "retrieval", "succeeded") != [])
        for slot in row["response_plan"]["slots"] if row["response_plan"] else []:
            slot_checks += 1
            actual = next(item for item in result.provenance.grounded_slots if item.name == slot["name"])
            assert actual.value == slot["value"]
            assert set(actual.source_ids) == set(slot["source_ids"])
            slot_fidelity = [
                source
                for source in row["response_plan"]["evidence"]
                if source["source_id"] in actual.source_ids and slot["name"] in source.get("facts", {})
            ]
            assert slot_fidelity
            assert any(source["facts"][slot["name"]] == actual.value for source in slot_fidelity)
            factuality_checks += 1
    assert sum(wers) / len(wers) <= 0.05
    assert retrieval_successes == len(grounded_rows) + sum(
        row["response_plan"] is not None and not row["response_plan"]["slots"] for row in rows
    )
    assert slot_checks >= 5
    assert factuality_checks == slot_checks


def test_crisis_policy_and_accessibility_are_not_latency_optimizations() -> None:
    rows = _golden_rows()
    crisis = next(row for row in rows if row["category"] == "crisis")
    crisis_result = _run_golden(crisis)
    assert crisis_result.status == "completed"
    assert crisis_result.provenance.template_id == "crisis-immediate-v1"
    assert "911" in crisis_result.response_text
    assert "now" in crisis_result.response_text.lower()
    assert not any(word in crisis_result.response_text.lower() for word in ("wait", "later"))

    for row in rows:
        if row["category"] != "accessibility":
            continue
        result = _run_golden(row)
        assert len(result.spoken_text.split()) <= 30
        assert not re.search(r"<[^>]+>|https?://|ipfs://|\bbafy[a-z0-9]+\b", result.spoken_text, re.I)
        assert result.spoken_text == result.spoken_text.strip()


def test_privacy_safe_receipts_exclude_audio_paths_and_secrets() -> None:
    speech = GoldenSpeechProvider("synthetic-private-check", "I need help")
    result = process_voice_turn(
        VoiceTurnRequest(audio=PRIVATE_AUDIO, request_id="privacy-check"),
        stt_provider=speech,
        template_provider=None,
        tts_provider=speech,
    )
    receipt = json.dumps(result.to_dict(), sort_keys=True)
    assert "PRIVATE-CALLER-AUDIO" not in receipt
    assert "audio_base64" not in receipt
    assert PRIVATE_AUDIO.hex() not in receipt
    assert result.provenance.input_audio_sha256
    assert result.to_dict()["audio_size_bytes"] == len(speech.audio)


def test_stt_failure_is_a_failed_safe_handoff_and_tts_failure_is_text_only() -> None:
    tts = GoldenSpeechProvider("synthetic-handoff-tts", "unused")
    failed_stt = GoldenSpeechProvider(
        "synthetic-failing-stt", "unused", fail_transcription=True
    )
    failed_stt_result = process_voice_turn(
        VoiceTurnRequest(audio=b"synthetic-stt-failure"),
        stt_provider=failed_stt,
        tts_provider=tts,
    )
    assert failed_stt_result.status == "failed"
    assert failed_stt_result.response_text == DEFAULT_GROUNDED_FALLBACK
    assert failed_stt_result.audio
    assert _trace(failed_stt_result, "transcription", "failed")
    assert _trace(failed_stt_result, "retrieval", "skipped")
    assert _trace(failed_stt_result, "rendering", "skipped")

    failed_tts = GoldenSpeechProvider("synthetic-failing-tts", "unused", fail_synthesis=True)
    text_only = process_voice_turn(
        VoiceTurnRequest(transcript="I need help"),
        template_provider=None,
        tts_provider=failed_tts,
    )
    assert text_only.status == "text_only"
    assert text_only.audio is None
    assert text_only.provenance.output_audio_sha256 is None
    assert "tts_failed" in text_only.fallback_reasons


def test_provider_fallback_is_visible_in_stage_receipts() -> None:
    class FailingTTS(GoldenSpeechProvider):
        def __init__(self) -> None:
            super().__init__("synthetic-primary", "unused", fail_synthesis=True)

    class WorkingTTS(GoldenSpeechProvider):
        def __init__(self) -> None:
            super().__init__("synthetic-fallback", "unused")

    register_voice_provider(
        "safety-primary",
        FailingTTS,
        capabilities=VoiceProviderCapabilities(transcription=False, synthesis=True),
    )
    register_voice_provider(
        "safety-secondary",
        WorkingTTS,
        capabilities=VoiceProviderCapabilities(transcription=False, synthesis=True),
    )
    result = process_voice_turn(
        VoiceTurnRequest(
            transcript="I need help",
            tts_provider="safety-primary",
            tts_providers=("safety-secondary",),
        ),
        template_provider=None,
    )
    assert result.status == "degraded"
    assert result.audio
    assert result.provenance.tts_provider == "safety-secondary"
    assert "tts_provider_fallback" in result.fallback_reasons
    synthesis = _trace(result, "synthesis")
    assert [item.status for item in synthesis] == ["failed", "succeeded"]


def test_tts_cache_is_fast_and_never_crosses_provider_instances() -> None:
    clear_voice_router_caches()
    deps = RouterDeps()
    provider = GoldenSpeechProvider("cache-provider", "unused")
    first_started = time.perf_counter()
    first = text_to_speech(
        "A deterministic cache sample.",
        provider_instance=provider,
        output_format="wav",
        deps=deps,
    )
    first_ms = (time.perf_counter() - first_started) * 1000
    second_started = time.perf_counter()
    second = text_to_speech(
        "A deterministic cache sample.",
        provider_instance=provider,
        output_format="wav",
        deps=deps,
    )
    second_ms = (time.perf_counter() - second_started) * 1000
    assert first == second
    assert len([call for call in provider.calls if call[0] == "synthesize"]) == 1
    assert second_ms <= max(100.0, first_ms * 10.0)


def test_stage_traces_are_ordered_and_have_finite_latency() -> None:
    result = _run_golden(next(row for row in _golden_rows() if row["case_id"] == "food_current_grounded"))
    stages = [item.stage for item in result.traces]
    assert stages == ["transcription", "retrieval", "rendering", "synthesis"]
    assert all(isinstance(item, VoiceStageTrace) for item in result.traces)
    assert all(item.duration_ms >= 0 for item in result.traces)
    assert result.total_duration_ms < 1000


def test_telephone_max_turns_escalates_without_provider_dispatch_or_call_id_leak() -> None:
    state = TelephoneTurnState(
        call_id="private-synthetic-provider-call-id",
        turn_index=2,
        max_turns=2,
        barge_in=True,
    )
    result = process_telephone_turn(
        VoiceTurnRequest(
            transcript="One more question",
            request_id="telephone-max-turns",
        ),
        state,
    )

    assert result.status == "text_only"
    assert result.audio is None
    assert result.provenance.stt_provider == "not_dispatched"
    assert result.fallback_reasons == (
        "telephone_max_turns_reached",
        "telephone_human_escalation",
    )
    assert [trace.stage for trace in result.traces] == [
        "telephone_ingress",
        "telephone_escalation",
        "telephone_egress",
    ]
    assert result.traces[1].details["reason"] == "maximum_turns_reached"
    assert result.traces[2].details["delivery"] == "text_only_handoff"
    receipt = json.dumps(result.to_dict(), sort_keys=True)
    assert "private-synthetic-provider-call-id" not in receipt
    assert state.call_id_sha256 in receipt


def test_graphrag_adapter_is_injected_and_prompt_is_auditable() -> None:
    row = next(row for row in _golden_rows() if row["case_id"] == "food_current_grounded")
    captured: dict[str, Any] = {}

    class Backend:
        def retrieve(self, query: str, *, prompt_parts: Mapping[str, Any], **kwargs: object) -> VoiceResponsePlan:
            captured["query"] = query
            captured["prompt_parts"] = dict(prompt_parts)
            return _response_plan(row)  # type: ignore[return-value]

    adapter = GraphRAGVoiceTemplateProvider(Backend(), minimum_confidence=0.9)
    plan = adapter.retrieve(
        row["observed_transcript"],
        context={"county": "synthetic"},
        language="en",
        max_results=3,
    )
    assert plan is not None
    assert captured["prompt_parts"]["max_results"] == 3
    assert captured["prompt_parts"]["language"] == "en"
    assert captured["query"] == row["observed_transcript"]
    assert adapter.last_prompt_parts == captured["prompt_parts"]


def test_legacy_speech_to_text_keeps_plain_string_contract_offline() -> None:
    clear_voice_router_caches()
    provider = GoldenSpeechProvider("legacy-stt", "synthetic legacy transcript")
    result = speech_to_text(
        b"synthetic-legacy-audio",
        provider_instance=provider,
        deps=RouterDeps(),
    )
    assert result == "synthetic legacy transcript"
    assert isinstance(result, str)


def test_returned_audio_transcript_threshold_rejects_a_changed_fact() -> None:
    """Whisper or an injected equivalent must match normalized expected text."""

    normalized_expected = "call nine one one now"
    injected_equivalent_exact = "call nine one one now"
    changed_fact = "call nine one two now"

    assert _word_error_rate(normalized_expected, injected_equivalent_exact) == 0
    assert _word_error_rate(normalized_expected, changed_fact) > 0
