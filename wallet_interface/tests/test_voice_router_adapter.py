"""Offline acceptance tests for the wallet unified voice-router boundary."""

from __future__ import annotations

import base64
import io
import json
import math
import struct
import wave
from hashlib import sha256

import pytest
from ipfs_accelerate_py.voice_audio_resolver import PrecomputedAudioArtifact
from ipfs_accelerate_py.voice_response_dag_sink import (
    IndependentVoiceValidationReceipt,
    LocalResponseDAGQueue,
    LocalValidatedVoiceCacheMissArtifacts,
)
from ipfs_accelerate_py.voice_router import (
    GroundedSlot,
    GroundingEvidence,
    PrecomputedAudioResolution,
    SynthesisIdentity,
    VoiceResponsePlan,
)

from wallet_interface.helpers._voice_router_adapter import (
    WalletVoiceRouterAdapter,
    _package_indextts_tts_provider,
    _PackageFirstTTSProvider,
    build_voice_turn_request,
    process_wallet_voice_turn,
)


def _fixture_wav() -> bytes:
    sample_rate = 16_000
    sample_count = sample_rate // 5
    frames = bytearray()
    for index in range(sample_count):
        value = int(
            7_000 * math.sin(2.0 * math.pi * 220.0 * index / sample_rate)
        )
        frames.extend(struct.pack("<h", value))
    output = io.BytesIO()
    with wave.open(output, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(bytes(frames))
    return output.getvalue()


VALID_WAV = _fixture_wav()


class _TTS:
    def __init__(self) -> None:
        self.texts: list[str] = []

    def synthesize(self, text: str, **_: object) -> bytes:
        self.texts.append(text)
        return VALID_WAV


class _Templates:
    def retrieve(self, transcript: str, **_: object) -> VoiceResponsePlan:
        return VoiceResponsePlan(
            template_id="wallet-test-response",
            template="A safe response for the caller.",
            metadata={"transcript": transcript},
        )


class _SlottedTemplates:
    def retrieve(self, transcript: str, **_: object) -> VoiceResponsePlan:
        evidence = GroundingEvidence(
            source_id="service-phone",
            cid="bafy-service-phone",
            facts={"phone": "five zero three, five five five, zero one zero zero"},
        )
        return VoiceResponsePlan(
            template_id="wallet-phone-response",
            template="Call {phone}.",
            slots=(
                GroundedSlot(
                    "phone",
                    "five zero three, five five five, zero one zero zero",
                    ("service-phone",),
                ),
            ),
            evidence=(evidence,),
            intent="resource_phone",
        )


class _ExactMiss:
    def resolve(self, *_args: object, **_kwargs: object) -> PrecomputedAudioResolution:
        return PrecomputedAudioResolution(
            status="miss",
            reason="exact_text_not_found",
        )


SLOTTED_RESPONSE = (
    "Call five zero three, five five five, zero one zero zero."
)


def _validation_receipt(result: object) -> IndependentVoiceValidationReceipt:
    response_text = str(getattr(result, "response_text", "") or "")
    audio = getattr(result, "audio", None)
    assert isinstance(audio, bytes)
    return IndependentVoiceValidationReceipt(
        validation_receipt_id="wallet-whisper-round-trip-pass",
        rendered_text_sha256=sha256(response_text.encode("utf-8")).hexdigest(),
        output_audio_sha256=sha256(audio).hexdigest(),
        validator_identity="openai-whisper-base-pinned-revision",
        validation_method="asr_round_trip",
    )


class _LocalWhisperPostprocessor:
    remote_writes = False

    def __init__(
        self,
        root,
        *,
        asr_transcript: str = SLOTTED_RESPONSE,
    ) -> None:
        self.root = root
        self.asr_transcript = asr_transcript
        self.calls: list[object] = []
        self.artifact_path = None

    def validate_and_store_local(
        self,
        result: object,
    ) -> LocalValidatedVoiceCacheMissArtifacts | None:
        self.calls.append(result)
        response_text = str(getattr(result, "response_text", "") or "")
        audio = getattr(result, "audio", None)
        if self.asr_transcript != response_text or not isinstance(audio, bytes):
            return None
        digest = sha256(audio).hexdigest()
        self.root.mkdir(parents=True, exist_ok=True)
        self.artifact_path = self.root / f"{digest}.wav"
        self.artifact_path.write_bytes(audio)
        self.artifact_path.chmod(0o600)
        return LocalValidatedVoiceCacheMissArtifacts(
            validation_receipt=_validation_receipt(result),
            audio_descriptor={
                "byte_length": len(audio),
                "content_sha256": digest,
                "media_type": "audio/wav",
                "uri": self.artifact_path.resolve().as_uri(),
            },
            response_id="wallet-phone-rendered-response",
        )


class _ExactHit:
    def resolve(self, *_args: object, **_kwargs: object) -> PrecomputedAudioResolution:
        synthesis = SynthesisIdentity(
            provider="fixture",
            model="fixture",
            voice="abby",
            provider_version="pinned-fixture",
            locale="en-US",
            codec="wav",
            sample_rate_hz=16_000,
            channels=1,
        )
        artifact = PrecomputedAudioArtifact(
            audio_id="audio-wallet-phone-response",
            spoken_text=SLOTTED_RESPONSE,
            spoken_text_sha256=sha256(
                SLOTTED_RESPONSE.encode("utf-8")
            ).hexdigest(),
            content_sha256=sha256(VALID_WAV).hexdigest(),
            synthesis_identity=synthesis,
            match_key="0" * 64,
            uri="ipfs://bafy-precomputed-wallet-audio",
            mime_type="audio/wav",
            byte_length=len(VALID_WAV),
            template_id="wallet-phone-response",
            response_id="wallet-phone-response",
        )
        return PrecomputedAudioResolution(
            status="hit",
            reason="exact_match",
            audio=VALID_WAV,
            artifact=artifact,
        )


def test_flag_off_leaves_legacy_proxy_path_available() -> None:
    assert process_wallet_voice_turn({"mode": "tts", "text": "hello"}, enabled=False) is None
    assert WalletVoiceRouterAdapter(enabled=False).process({"mode": "tts", "text": "hello"}) is None


def test_adapter_builds_typed_request_without_exposing_audio_in_normal_serialization() -> None:
    audio = b"synthetic-wav"
    request = build_voice_turn_request(
        {
            "mode": "voice-reply",
            "audio_base64": base64.b64encode(audio).decode("ascii"),
            "user_prompt": "Where can I find help?",
            "fallback_text": "I can help you find a local service.",
            "requestId": "wallet-test-1",
        }
    )

    assert request.request_id == "wallet-test-1"
    assert request.transcript == "Where can I find help?"
    assert request.audio == audio
    assert "audio_base64" not in request.to_dict()


def test_enabled_adapter_returns_canonical_receipt_and_audio_wire_field() -> None:
    tts = _TTS()
    payload = process_wallet_voice_turn(
        {
            "mode": "voice-reply",
            "text": "I can help you find a local service.",
            "user_prompt": "food help",
            "request_id": "wallet-turn-1",
        },
        enabled=True,
        template_provider=_Templates(),
        tts_provider=tts,
    )

    assert payload is not None
    assert payload["voice_router"] is True
    assert payload["status"] == "completed"
    assert payload["response_text"] == "A safe response for the caller."
    assert payload["audio_base64"] == base64.b64encode(VALID_WAV).decode("ascii")
    assert payload["audioBase64"] == payload["audio_base64"]
    assert payload["provenance"]["template_id"] == "wallet-test-response"  # type: ignore[index]
    assert [trace["stage"] for trace in payload["traces"]] == [  # type: ignore[index]
        "transcription",
        "retrieval",
        "rendering",
        "synthesis",
    ]
    assert tts.texts == ["A safe response for the caller."]


def test_publicus_gradio_space_activates_native_package_provider(monkeypatch) -> None:
    from wallet_interface.helpers import _voice_router_adapter as adapter

    monkeypatch.delenv("IPFS_ACCELERATE_PY_ABBY_INDEXTTS_URLS", raising=False)
    monkeypatch.delenv("IPFS_ACCELERATE_PY_ABBY_INDEXTTS_URL", raising=False)
    monkeypatch.setenv(
        "WALLET_INDEXTTS_SPACE_URL",
        "https://publicus-indextts-2-demo.hf.space",
    )
    adapter._PACKAGE_INDEXTTS_PROVIDER = None
    adapter._PACKAGE_INDEXTTS_PROVIDER_KEY = ()

    provider = _package_indextts_tts_provider()

    assert provider is not None
    assert provider.endpoints == (  # type: ignore[attr-defined]
        "https://publicus-indextts-2-demo.hf.space",
    )


def test_explicit_json_endpoint_uses_cached_package_provider(monkeypatch) -> None:
    from wallet_interface.helpers import _voice_router_adapter as adapter

    monkeypatch.setenv(
        "IPFS_ACCELERATE_PY_ABBY_INDEXTTS_URLS",
        "https://voice.example.test/v1/tts, https://voice-fallback.example.test/v1/tts/",
    )
    monkeypatch.setenv(
        "IPFS_ACCELERATE_PY_ABBY_INDEXTTS_MODEL",
        "Publicus/IndexTTS-2-Demo",
    )
    monkeypatch.setattr(
        "wallet_interface.helpers._tts_http._configured_hf_token",
        lambda: "cached-hf-token",
    )
    adapter._PACKAGE_INDEXTTS_PROVIDER = None
    adapter._PACKAGE_INDEXTTS_PROVIDER_KEY = ()

    first = _package_indextts_tts_provider()
    second = _package_indextts_tts_provider()

    assert first is second
    assert first is not None
    assert first.endpoints == (  # type: ignore[attr-defined]
        "https://voice.example.test/v1/tts",
        "https://voice-fallback.example.test/v1/tts",
    )
    assert first.default_model == "Publicus/IndexTTS-2-Demo"  # type: ignore[attr-defined]
    assert "cached-hf-token" not in repr(adapter._PACKAGE_INDEXTTS_PROVIDER_KEY)


def test_adapter_prefers_compatible_package_provider(monkeypatch) -> None:
    class _PackageTTS:
        def __init__(self) -> None:
            self.batches: list[list[str]] = []

        def synthesize_batch(self, texts: list[str], **_: object) -> tuple[bytes, ...]:
            self.batches.append(list(texts))
            return (VALID_WAV,)

    package_tts = _PackageTTS()
    monkeypatch.setattr(
        "wallet_interface.helpers._voice_router_adapter._package_indextts_tts_provider",
        lambda: package_tts,
    )

    payload = process_wallet_voice_turn(
        {
            "mode": "voice-reply",
            "text": "fallback",
            "user_prompt": "food help",
        },
        enabled=True,
        template_provider=_Templates(),
    )

    assert payload is not None
    assert payload["status"] == "completed"
    assert package_tts.batches == [["A safe response for the caller."]]


def test_package_failure_uses_wallet_gradio_compatibility_provider(monkeypatch) -> None:
    class _FailedPackage:
        last_receipt = None

        def synthesize_batch(self, texts: list[str], **_: object) -> tuple[bytes, ...]:
            raise RuntimeError(f"package unavailable for {len(texts)} item")

    monkeypatch.setattr(
        "wallet_interface.helpers._voice_router_adapter._WalletTTSProvider.synthesize",
        lambda self, text, **options: b"RIFF-wallet-compatibility",
    )
    provider = _PackageFirstTTSProvider(_FailedPackage())

    audio = provider.synthesize("hello")

    assert audio == b"RIFF-wallet-compatibility"
    assert provider.last_receipt is not None
    assert provider.last_receipt.degraded is True  # type: ignore[attr-defined]
    assert (
        provider.last_receipt.to_dict()["selected_backend"]  # type: ignore[attr-defined]
        == "wallet_gradio_compatibility"
    )


@pytest.mark.parametrize(
    ("surface", "expected_surface"),
    [
        (None, "website"),
        ("telephone", "telephone"),
    ],
)
def test_validated_live_tts_miss_stages_private_local_response_dag_candidate(
    tmp_path,
    surface,
    expected_surface,
) -> None:
    queue = LocalResponseDAGQueue(tmp_path / f"{expected_surface}-queue")
    postprocessor = _LocalWhisperPostprocessor(
        tmp_path / f"{expected_surface}-validated-audio"
    )
    tts = _TTS()
    private_audio = b"private caller audio"
    context = {
        "authorization": "Bearer private-wallet-credential",
        "call_id": "private-call-id",
        "session_id": "private-session-id",
    }
    if surface is not None:
        context["surface"] = surface

    payload = process_wallet_voice_turn(
        {
            "mode": "voice-reply",
            "audio_base64": base64.b64encode(private_audio).decode("ascii"),
            "user_prompt": "private caller transcript",
            "context": context,
        },
        enabled=True,
        template_provider=_SlottedTemplates(),
        tts_provider=tts,
        audio_resolver=_ExactMiss(),
        response_dag_sink=queue,
        response_dag_postprocessor=postprocessor,
    )

    assert payload is not None
    assert payload["response_text"] == SLOTTED_RESPONSE
    queue_payload = payload["response_dag_queue"]
    assert isinstance(queue_payload, dict)
    assert queue_payload["candidate_id"]
    assert queue_payload["queue"]["remote_writes"] is False
    assert len(queue) == 1
    assert len(postprocessor.calls) == 1
    assert postprocessor.artifact_path is not None
    assert postprocessor.artifact_path.read_bytes() == VALID_WAV

    candidate = queue.load(str(queue_payload["candidate_id"]))
    assert candidate.metadata["surface"] == expected_surface
    assert len(candidate.template_rows) == 1
    assert candidate.template_rows[0]["template_text"] == "Call {phone}."
    assert len(candidate.vocabulary_rows) == 1
    assert candidate.vocabulary_rows[0]["source_cids"] == [
        "bafy-service-phone"
    ]

    queue_file = queue.root / queue_payload["queue"]["relative_path"]
    staged = queue_file.read_text(encoding="utf-8")
    assert "private caller transcript" not in staged
    assert private_audio.hex() not in staged
    assert base64.b64encode(private_audio).decode("ascii") not in staged
    assert "private-wallet-credential" not in staged
    assert "private-call-id" not in staged
    assert "private-session-id" not in staged
    assert json.loads(staged)["remote_writes"] is False


def test_precomputed_cache_hit_never_stages_response_dag_candidate(
    tmp_path,
) -> None:
    queue = LocalResponseDAGQueue(tmp_path / "cache-hit-queue")
    postprocessor = _LocalWhisperPostprocessor(
        tmp_path / "cache-hit-validated-audio"
    )
    tts = _TTS()

    payload = process_wallet_voice_turn(
        {
            "mode": "voice-reply",
            "user_prompt": "Where should I call?",
        },
        enabled=True,
        template_provider=_SlottedTemplates(),
        tts_provider=tts,
        audio_resolver=_ExactHit(),
        response_dag_sink=queue,
        response_dag_postprocessor=postprocessor,
    )

    assert payload is not None
    assert payload["response_dag_queue"] == {
        "candidate_id": None,
        "publication_status": "not_applicable",
        "reason": "not_live_tts_cache_miss",
        "remote_writes": False,
        "status": "not_queued",
    }
    assert len(queue) == 0
    assert postprocessor.calls == []
    assert postprocessor.artifact_path is None
    assert tts.texts == []


def test_partial_response_dag_staging_configuration_fails_before_tts(
    tmp_path,
) -> None:
    tts = _TTS()

    with pytest.raises(ValueError, match="requires response_dag_sink"):
        process_wallet_voice_turn(
            {
                "mode": "voice-reply",
                "user_prompt": "Where should I call?",
            },
            enabled=True,
            template_provider=_SlottedTemplates(),
            tts_provider=tts,
            audio_resolver=_ExactMiss(),
            response_dag_sink=LocalResponseDAGQueue(tmp_path / "partial"),
        )

    assert tts.texts == []


def test_failed_independent_validation_returns_audio_without_queueing(
    tmp_path,
) -> None:
    queue = LocalResponseDAGQueue(tmp_path / "failed-validation-queue")
    postprocessor = _LocalWhisperPostprocessor(
        tmp_path / "failed-validation-audio",
        asr_transcript="The audio did not match.",
    )

    payload = process_wallet_voice_turn(
        {
            "mode": "voice-reply",
            "user_prompt": "Where should I call?",
        },
        enabled=True,
        template_provider=_SlottedTemplates(),
        tts_provider=_TTS(),
        audio_resolver=_ExactMiss(),
        response_dag_sink=queue,
        response_dag_postprocessor=postprocessor,
    )

    assert payload is not None
    assert payload["audio_base64"] == base64.b64encode(VALID_WAV).decode("ascii")
    assert payload["response_dag_queue"] == {
        "candidate_id": None,
        "publication_status": "not_applicable",
        "reason": "independent_validation_not_passed",
        "remote_writes": False,
        "status": "not_queued",
    }
    assert len(postprocessor.calls) == 1
    assert len(queue) == 0


def test_remote_write_capable_postprocessor_is_rejected_before_tts(
    tmp_path,
) -> None:
    class _RemotePublisher:
        remote_writes = True

        def validate_and_store_local(self, result: object) -> None:
            raise AssertionError("must not run")

    tts = _TTS()
    with pytest.raises(ValueError, match="remote_writes = False"):
        process_wallet_voice_turn(
            {
                "mode": "voice-reply",
                "user_prompt": "Where should I call?",
            },
            enabled=True,
            template_provider=_SlottedTemplates(),
            tts_provider=tts,
            audio_resolver=_ExactMiss(),
            response_dag_sink=LocalResponseDAGQueue(tmp_path / "no-remote"),
            response_dag_postprocessor=_RemotePublisher(),
        )

    assert tts.texts == []
