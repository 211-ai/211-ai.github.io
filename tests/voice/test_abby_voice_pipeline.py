"""Offline acceptance tests for the unified, grounded Abby voice pipeline.

Every collaborator is an in-memory fake.  This suite must never contact a
speech service, a GraphRAG deployment, IPFS, or Hugging Face.
"""

from __future__ import annotations

import base64
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

# The checkout keeps the upstream package one directory below the monorepo
# package name.  Prefer that checkout over any separately installed copy.
REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = REPO_ROOT / "ipfs_accelerate_py"
DATASETS_PACKAGE_ROOT = REPO_ROOT / "ipfs_datasets_py"
sys.path.insert(0, str(PACKAGE_ROOT))
sys.path.insert(0, str(DATASETS_PACKAGE_ROOT))

from ipfs_accelerate_py.voice_router import (  # noqa: E402
    DEFAULT_GROUNDED_FALLBACK,
    GraphRAGVoiceTemplateProvider,
    GroundedSlot,
    PrecomputedAudioResolution,
    VoiceGroundingSource,
    VoiceResponsePlan,
    VoiceStageTrace,
    VoiceTurnRequest,
    VoiceTurnResult,
    clear_voice_router_caches,
    process_voice_turn,
    register_voice_provider,
    speech_to_text,
    text_to_speech,
)
from ipfs_datasets_py.voice.hf_release import (  # noqa: E402
    materialize_response_dag_dry_run,
)
from ipfs_datasets_py.voice.response_dag import (  # noqa: E402
    append_response_dag_candidate,
)


@dataclass
class RecordingSpeechProvider:
    """Deterministic provider implementing both halves of the legacy protocol."""

    name: str
    transcript: str = "I need food assistance near me"
    audio: bytes = b"RIFF-grounded-abby-audio"
    stt_error: Exception | None = None
    tts_error: Exception | None = None
    calls: list[tuple[str, dict[str, Any]]] = field(default_factory=list)

    def transcribe(self, audio: object, **kwargs: object) -> str:
        self.calls.append(("transcribe", {"audio": audio, **kwargs}))
        if self.stt_error is not None:
            raise self.stt_error
        return self.transcript

    def synthesize(self, text: str, **kwargs: object) -> bytes:
        self.calls.append(("synthesize", {"text": text, **kwargs}))
        if self.tts_error is not None:
            raise self.tts_error
        return self.audio


def _source(
    source_id: str = "food-record",
    *,
    cid: str = "bafy-food-2026",
) -> VoiceGroundingSource:
    return VoiceGroundingSource(
        source_id=source_id,
        cid=cid,
        uri=f"ipfs://{cid}",
        text="Community Food Network phone 503-555-0111.",
        facts={
            "program": "Community Food Network",
            "phone": "503-555-0111",
        },
        metadata={"title": "Current public food-service record"},
    )


def _grounded_plan() -> VoiceResponsePlan:
    return VoiceResponsePlan(
        template_id="food-frame-v2",
        template=(
            "{program} can help. Call {phone}. "
            "[source](https://example.test/current-food-record) [1] "
            f"ipfs://{_source().cid}"
        ),
        slots=(
            GroundedSlot("program", "Community Food Network", ("food-record",)),
            GroundedSlot("phone", "503-555-0111", ("food-record",)),
        ),
        evidence=(_source(),),
        intent="food_assistance",
        confidence=0.94,
        metadata={"retrieval": "hybrid"},
    )


@dataclass
class RecordingTemplateProvider:
    plan: VoiceResponsePlan | None = field(default_factory=_grounded_plan)
    error: Exception | None = None
    calls: list[dict[str, Any]] = field(default_factory=list)
    provider_name: str = "fake-ipld-graphrag"

    def retrieve(
        self,
        transcript: str,
        *,
        context: dict[str, Any] | None = None,
        language: str | None = None,
        grounding: dict[str, Any] | None = None,
        max_results: int = 5,
        locale: str | None = None,
    ) -> VoiceResponsePlan | None:
        self.calls.append(
            {
                "transcript": transcript,
                "locale": locale,
                "language": language,
                "context": context or {},
                "grounding": grounding or {},
                "max_results": max_results,
            }
        )
        if self.error is not None:
            raise self.error
        return self.plan


def _trace_status(result: VoiceTurnResult, stage: str) -> str:
    return next(trace.status for trace in result.traces if trace.stage == stage)


def _fallback_codes(result: VoiceTurnResult) -> tuple[str, ...]:
    return tuple(
        item if isinstance(item, str) else item.code
        for item in result.fallbacks
    )


def test_public_contracts_are_typed_serializable_and_dependency_light() -> None:
    request = VoiceTurnRequest(
        transcript="hello",
        request_id="contract-1",
        context={"county": "Multnomah"},
    )
    trace = VoiceStageTrace(stage="input", status="succeeded", duration_ms=0)

    assert request.request_id == "contract-1"
    assert request.to_dict()["transcript"] == "hello"
    assert trace.to_dict()["stage"] == "input"
    assert json.loads(json.dumps(request.to_dict()))["context"] == {
        "county": "Multnomah"
    }
    assert isinstance(_grounded_plan(), VoiceResponsePlan)
    assert callable(process_voice_turn)


def test_full_audio_turn_runs_in_order_and_returns_grounded_receipt() -> None:
    call_order: list[str] = []

    class OrderedSpeechProvider(RecordingSpeechProvider):
        def transcribe(self, audio: object, **kwargs: object) -> str:
            call_order.append("transcription")
            return super().transcribe(audio, **kwargs)

        def synthesize(self, text: str, **kwargs: object) -> bytes:
            call_order.append("synthesis")
            return super().synthesize(text, **kwargs)

    class OrderedTemplateProvider(RecordingTemplateProvider):
        def retrieve(self, transcript: str, **kwargs: object) -> VoiceResponsePlan:
            call_order.append("retrieval")
            plan = super().retrieve(transcript, **kwargs)
            assert plan is not None
            return plan

    speech = OrderedSpeechProvider("abby-local")
    templates = OrderedTemplateProvider()
    request = VoiceTurnRequest(
        audio=b"synthetic-wav-input",
        request_id="turn-happy-1",
        locale="en-US",
        language="en",
        voice="abby",
        output_format="wav",
        context={"county": "Multnomah"},
        grounding={"corpus_cid": "bafy-corpus"},
        max_template_results=3,
    )

    result = process_voice_turn(
        request,
        stt_provider=speech,
        template_provider=templates,
        tts_provider=speech,
    )

    assert call_order == ["transcription", "retrieval", "synthesis"]
    assert result.status == "completed"
    assert result.transcript == "I need food assistance near me"
    assert result.response_text == (
        "Community Food Network can help. Call 503-555-0111."
    )
    assert result.audio == b"RIFF-grounded-abby-audio"
    assert result.audio_format == "wav"
    assert result.template_id == "food-frame-v2"
    assert result.intent == "food_assistance"
    assert result.sources == (_source(),)
    assert _fallback_codes(result) == ()
    assert [trace.stage for trace in result.traces] == [
        "transcription",
        "retrieval",
        "rendering",
        "synthesis",
    ]
    assert all(trace.duration_ms >= 0 for trace in result.traces)
    assert templates.calls == [
        {
            "transcript": "I need food assistance near me",
            "locale": None,
            "language": "en",
            "context": {"county": "Multnomah"},
            "grounding": {"corpus_cid": "bafy-corpus"},
            "max_results": 3,
        }
    ]

    synth_call = next(payload for name, payload in speech.calls if name == "synthesize")
    assert synth_call["text"] == result.response_text
    assert synth_call["voice"] == "abby"
    assert synth_call["output_format"] == "wav"

    # Display citations are removed from speech while machine provenance stays.
    assert "http" not in result.response_text
    assert "ipfs://" not in result.response_text
    assert "[1]" not in result.response_text
    assert result.sources[0].cid == "bafy-food-2026"
    assert result.provenance.template_id == "food-frame-v2"


def test_supplied_transcript_skips_stt_and_uses_identical_grounded_path() -> None:
    speech = RecordingSpeechProvider("abby-tts")
    result = process_voice_turn(
        VoiceTurnRequest(transcript="food help", request_id="turn-text-1"),
        template_provider=RecordingTemplateProvider(),
        stt_provider=speech,
        tts_provider=speech,
    )

    assert result.status == "completed"
    assert not any(name == "transcribe" for name, _ in speech.calls)
    assert _trace_status(result, "transcription") == "skipped"
    assert _trace_status(result, "retrieval") == "succeeded"
    assert result.transcript == "food help"


@pytest.mark.parametrize(
    "plan",
    [
        VoiceResponsePlan(
            template_id="unknown-source",
            template="Call {phone}.",
            slots=(GroundedSlot("phone", "503-555-9999", ("stale-record",)),),
            evidence=(_source("current-record"),),
        ),
        VoiceResponsePlan(
            template_id="missing-slot",
            template="{program} is at {address}.",
            slots=(
                GroundedSlot(
                    "program",
                    "Community Food Network",
                    ("food-record",),
                ),
            ),
            evidence=(_source(),),
        ),
    ],
    ids=["unknown-slot-source", "missing-template-slot"],
)
def test_unbound_factual_slots_fail_closed_to_safe_spoken_text(
    plan: VoiceResponsePlan,
) -> None:
    tts = RecordingSpeechProvider("abby-tts")
    result = process_voice_turn(
        VoiceTurnRequest(transcript="help", request_id="turn-unsafe-1"),
        template_provider=RecordingTemplateProvider(plan=plan),
        tts_provider=tts,
    )

    assert result.status == "degraded"
    assert result.response_text == DEFAULT_GROUNDED_FALLBACK
    assert "503-555-9999" not in result.response_text
    assert "grounding_validation_failed" in _fallback_codes(result)
    assert _trace_status(result, "rendering") == "failed"
    assert tts.calls[-1][1]["text"] == DEFAULT_GROUNDED_FALLBACK


@pytest.mark.parametrize(
    "provider",
    [
        RecordingTemplateProvider(plan=None),
        RecordingTemplateProvider(error=RuntimeError("offline fixture failure")),
    ],
    ids=["no-plan", "provider-error"],
)
def test_retrieval_failure_is_deterministic_visible_and_still_synthesized(
    provider: RecordingTemplateProvider,
) -> None:
    first_tts = RecordingSpeechProvider("abby-tts")
    second_tts = RecordingSpeechProvider("abby-tts")
    first = process_voice_turn(
        VoiceTurnRequest(transcript="housing", request_id="turn-retrieval-1"),
        template_provider=provider,
        tts_provider=first_tts,
    )
    second = process_voice_turn(
        VoiceTurnRequest(transcript="housing", request_id="turn-retrieval-2"),
        template_provider=provider,
        tts_provider=second_tts,
    )

    assert first.status == second.status == "degraded"
    assert first.response_text == second.response_text == DEFAULT_GROUNDED_FALLBACK
    assert "template_retrieval_failed" in _fallback_codes(first)
    assert _trace_status(first, "retrieval") == "failed"
    assert first.sources == ()
    assert first_tts.calls[-1][1]["text"] == DEFAULT_GROUNDED_FALLBACK
    assert second_tts.calls[-1][1]["text"] == DEFAULT_GROUNDED_FALLBACK


def test_graphrag_miss_uses_fallback_llm_slotted_plan_before_tts() -> None:
    """Fallback LLM providers must return the same grounded slotted plan shape."""

    primary = RecordingTemplateProvider(plan=None)
    fallback = RecordingTemplateProvider(
        plan=_grounded_plan(),
        provider_name="fallback-llm-slotted-template",
    )
    tts = RecordingSpeechProvider("abby-tts")

    result = process_voice_turn(
        VoiceTurnRequest(transcript="food", request_id="turn-fallback-llm-1"),
        template_provider=primary,
        fallback_template_provider=fallback,
        tts_provider=tts,
    )

    assert result.status == "degraded"
    assert result.response_text == "Community Food Network can help. Call 503-555-0111."
    assert result.provenance.template_provider == "fallback-llm-slotted-template"
    assert result.provenance.template_id == "food-frame-v2"
    assert result.provenance.grounded_slots
    assert "template_retrieval_failed" in _fallback_codes(result)
    assert "fallback_template_provider_used" in _fallback_codes(result)
    assert _trace_status(result, "fallback_retrieval") == "succeeded"
    assert tts.calls[-1][1]["text"] == result.response_text


def test_tts_failure_returns_text_only_degradation_without_false_audio() -> None:
    tts = RecordingSpeechProvider(
        "tts-down",
        tts_error=TimeoutError("synthetic timeout"),
    )
    result = process_voice_turn(
        VoiceTurnRequest(transcript="food", request_id="turn-text-only-1"),
        template_provider=RecordingTemplateProvider(),
        tts_provider=tts,
    )

    assert result.status == "text_only"
    assert result.degraded is True
    assert result.response_text.startswith("Community Food Network")
    assert result.audio is None
    assert result.audio_format is None
    assert "tts_failed" in _fallback_codes(result)
    assert _trace_status(result, "synthesis") == "failed"
    assert result.provenance.output_audio_sha256 is None


@pytest.mark.parametrize("transcript", ["", "   ", "\n\t"])
def test_stt_empty_output_skips_retrieval_and_synthesizes_safe_handoff(
    transcript: str,
) -> None:
    stt = RecordingSpeechProvider("stt-down", transcript=transcript)
    templates = RecordingTemplateProvider()
    tts = RecordingSpeechProvider("unused-tts")
    result = process_voice_turn(
        VoiceTurnRequest(audio=b"synthetic-audio", request_id="turn-stt-fail"),
        stt_provider=stt,
        template_provider=templates,
        tts_provider=tts,
    )

    assert result.status == "failed"
    assert result.transcript == ""
    assert result.audio == tts.audio
    assert result.response_text == DEFAULT_GROUNDED_FALLBACK
    assert "stt_failed" in _fallback_codes(result)
    assert templates.calls == []
    assert tts.calls[-1][1]["text"] == DEFAULT_GROUNDED_FALLBACK
    assert _trace_status(result, "transcription") == "failed"
    assert _trace_status(result, "retrieval") == "skipped"
    assert _trace_status(result, "synthesis") == "succeeded"


def test_graph_rag_adapter_normalizes_mapping_without_optional_imports() -> None:
    class DatasetGraphRAGBackend:
        def retrieve_voice_template(
            self,
            transcript: str,
            *,
            language: str,
            context: dict[str, Any],
            grounding: dict[str, Any],
            max_results: int,
        ) -> dict[str, Any]:
            assert (
                transcript,
                language,
                context,
                grounding,
                max_results,
            ) == ("utility help", "en-US", {}, {}, 5)
            return {
                "template_id": "utility-frame",
                "template": "{program} serves {county}. Source: ipfs://bafy-utility",
                "slots": [
                    {
                        "name": "program",
                        "value": "Energy Assistance",
                        "source_ids": ["utility-record"],
                    },
                    {
                        "name": "county",
                        "value": "Lane County",
                        "source_ids": ["utility-record"],
                    },
                ],
                "sources": [
                    {
                        "source_id": "utility-record",
                        "cid": "bafy-utility",
                        "uri": "ipfs://bafy-utility",
                        "title": "Utility record",
                        "facts": {
                            "program": "Energy Assistance",
                            "county": "Lane County",
                        },
                    }
                ],
                "confidence": 0.91,
                "intent": "utility_help",
            }

    result = process_voice_turn(
        VoiceTurnRequest(
            transcript="utility help",
            request_id="turn-adapter-1",
            locale="en-US",
        ),
        template_provider=GraphRAGVoiceTemplateProvider(DatasetGraphRAGBackend()),
        tts_provider=RecordingSpeechProvider("abby-tts"),
    )

    assert result.status == "completed"
    assert result.response_text == "Energy Assistance serves Lane County."
    assert result.template_id == "utility-frame"
    assert result.intent == "utility_help"
    assert result.sources[0].cid == "bafy-utility"


def test_result_serialization_is_json_safe_and_omits_raw_private_audio() -> None:
    raw_input = b"private-synthetic-input-audio"
    raw_output = b"RIFF-synthetic-output"
    result = process_voice_turn(
        VoiceTurnRequest(audio=raw_input, request_id="turn-json-1"),
        stt_provider=RecordingSpeechProvider("abby-stt"),
        template_provider=RecordingTemplateProvider(),
        tts_provider=RecordingSpeechProvider(
            "abby-tts",
            audio=raw_output,
        ),
    )

    default_payload = result.to_dict()
    payload = result.to_dict(include_audio=True)
    serialized = json.dumps(payload, sort_keys=True)

    assert "private-synthetic-input-audio" not in serialized
    assert base64.b64encode(raw_input).decode("ascii") not in serialized
    assert "audio_base64" not in default_payload
    assert payload["audio_base64"] == base64.b64encode(raw_output).decode("ascii")
    assert payload["provenance"]["input_audio_sha256"]
    assert payload["provenance"]["response_text_sha256"]
    assert result.cache_key
    assert raw_input.hex() not in result.cache_key
    assert result.transcript not in result.cache_key


def test_validated_live_tts_miss_stops_at_local_response_dag_dry_run(
    tmp_path: Path,
) -> None:
    """One miss becomes one slotted append receipt without a remote write."""

    class ExactAudioMiss:
        def resolve(
            self, *_args: object, **_kwargs: object
        ) -> PrecomputedAudioResolution:
            return PrecomputedAudioResolution(
                status="miss",
                reason="no_precomputed_candidates",
                details={"candidate_count": 0},
            )

    plan = VoiceResponsePlan(
        template_id="phone-frame-v1",
        template="Call {phone}.",
        slots=(GroundedSlot("phone", "503-555-0111", ("food-record",)),),
        evidence=(_source(),),
        intent="resource_phone",
        confidence=0.99,
    )
    live_tts = RecordingSpeechProvider(
        "abby-live-tts",
        audio=b"RIFF-validated-live-cache-miss-WAVE",
    )
    result = process_voice_turn(
        VoiceTurnRequest(
            transcript="What number should I call?",
            request_id="turn-cache-miss-1",
            tts_provider="abby-live-tts",
            tts_model="IndexTTS-2",
            voice="abby",
            output_format="wav",
        ),
        template_provider=RecordingTemplateProvider(plan=plan),
        tts_provider=live_tts,
        audio_resolver=ExactAudioMiss(),
    )

    event = result.validated_cache_miss_event(
        validation_receipt_id="asr-round-trip-pass-1",
        response_id="phone-response-v1",
    )
    duplicate = result.validated_cache_miss_event(
        validation_receipt_id="asr-round-trip-pass-retry",
        response_id="phone-response-v1",
    )
    assert event is not None and duplicate is not None
    assert event.event_id == duplicate.event_id
    assert event.ready_for_dag_append is True
    assert result.transcript not in json.dumps(event.to_dict(), sort_keys=True)
    assert live_tts.audio.hex() not in json.dumps(event.to_dict(), sort_keys=True)

    candidate = append_response_dag_candidate(
        event,
        response_text=result.response_text,
        audio_descriptor={
            "byte_length": len(live_tts.audio),
            "content_sha256": result.provenance.output_audio_sha256,
            "media_type": "audio/wav",
            "uri": "hf://datasets/Publicus/211-abby-tts/audio/phone-response-v1.wav",
        },
        template_text=plan.template,
        slot_bindings={
            "phone": {
                "source_cids": [result.sources[0].cid],
                "value": result.provenance.grounded_slots[0].value,
            }
        },
    )
    receipt = materialize_response_dag_dry_run(
        candidate,
        output_dir=tmp_path / "response-dag-release",
    )
    receipt_again = materialize_response_dag_dry_run(
        candidate,
        output_dir=tmp_path / "response-dag-release-rebuild",
    )

    assert len(candidate.template_rows) == 1
    assert len(candidate.vocabulary_rows) == 1
    assert any("/rows/templates.jsonl" in path for path in candidate.file_payloads())
    assert any("/rows/vocabulary.jsonl" in path for path in candidate.file_payloads())
    assert receipt.publication_plan["upload_file_count"] == len(
        candidate.file_payloads()
    )
    assert receipt.to_dict()["publication_status"] == "local_only"
    assert receipt.to_dict()["remote_write_contacted"] is False
    assert receipt.to_dict()["remote_writes"] is False
    assert receipt.receipt_sha256 == receipt_again.receipt_sha256
    assert (
        receipt.publication_plan_sha256
        == receipt_again.publication_plan_sha256
    )


@pytest.mark.parametrize(
    "kwargs",
    [
        {},
        {"audio": b""},
        {"transcript": "   "},
        {"audio": ""},
    ],
)
def test_request_rejects_missing_or_empty_input(kwargs: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        VoiceTurnRequest(**kwargs)


def test_legacy_text_to_speech_and_speech_to_text_remain_compatible(
    tmp_path: Path,
) -> None:
    clear_voice_router_caches()
    provider = RecordingSpeechProvider("legacy")
    register_voice_provider("acceptance-legacy-provider", lambda: provider)

    audio = text_to_speech("Hello", provider="acceptance-legacy-provider")
    transcript = speech_to_text(
        b"voice",
        provider="acceptance-legacy-provider",
    )
    output_path = tmp_path / "reply.wav"
    returned_path = text_to_speech(
        "Saved reply",
        provider_instance=provider,
        output_path=str(output_path),
    )

    assert audio == provider.audio
    assert transcript == provider.transcript
    assert returned_path == str(output_path)
    assert output_path.read_bytes() == provider.audio
