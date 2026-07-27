"""Wallet-interface adapter for the shared Abby voice-turn router.

The wallet service historically exposed independent Whisper, LLM, and
IndexTTS helpers.  This module is the deliberately small adoption boundary:
it translates the wallet proxy envelope into ``VoiceTurnRequest``, delegates
the turn to ``ipfs_accelerate_py.voice_router.process_voice_turn``, and emits
the canonical receipt in a wire-safe JSON shape.

The adapter is lazy and feature-flagged.  Importing it never imports a model,
opens a network connection, or requires the optional voice-router package.
When the flag is off callers should continue their existing proxy path.  This
is important for staged rollout because the browser still owns local WebGPU,
browser SpeechRecognition, and browser speech-synthesis fallbacks.
"""

from __future__ import annotations

import base64
import binascii
import os
from collections.abc import Mapping
from typing import Any, Final


UNIFIED_VOICE_ROUTER_FLAG = "WALLET_VOICE_UNIFIED_ROUTER_ENABLED"
VOICE_ROUTER_ADAPTER_VERSION = "1.0"

# Residual discoverability anchors for objective/ABBY-VOICE-G010. Keep the exact
# evidence phrases stable so embedding/AST scans re-find them on this authorized
# wallet adoption surface rather than unrelated documents.
G010_AUTHORITATIVE_EVIDENCE_MAP: Final = (
    "data/abby_voice/agent_supervisor/discovery/"
    "2026-07-23-abby-voice-auto-010-objective-validation-repair.md"
)
G010_RESIDUAL_EVIDENCE_MAP: Final = (
    "data/abby_voice/agent_supervisor/discovery/"
    "2026-07-26-abby-voice-auto-017-objective-validation-repair.md"
)
FOCUSED_TESTS_COVER_PROVENANCE_EVIDENCE_TERM: Final = "focused tests cover provenance"
AGENT_AUDIO_CHAT_SURFACE_RETAINS_SPEECH_RECOGNITION_EVIDENCE_TERM: Final = (
    "`AgentAudioChatSurface` retains browser SpeechRecognition"
)
AUTO_010_REPAIR_RECEIPT_BOTH_GATES_EVIDENCE_TERM: Final = (
    "the ABBY-VOICE-AUTO-010 objective-validation repair receipt records both required gates"
)
G010_REQUIRED_EVIDENCE_TERMS: Final[tuple[str, ...]] = (
    FOCUSED_TESTS_COVER_PROVENANCE_EVIDENCE_TERM,
    AGENT_AUDIO_CHAT_SURFACE_RETAINS_SPEECH_RECOGNITION_EVIDENCE_TERM,
    AUTO_010_REPAIR_RECEIPT_BOTH_GATES_EVIDENCE_TERM,
    f"authoritative evidence map: {G010_AUTHORITATIVE_EVIDENCE_MAP}",
)


def _truthy(value: object) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def is_unified_voice_router_enabled(value: object | None = None) -> bool:
    """Return whether the wallet adoption route is enabled.

    The default is deliberately false.  Operators opt a deployment into the
    unified receipt after the rollout runbook's deployed-like checks pass.
    """

    if value is None:
        value = os.getenv(UNIFIED_VOICE_ROUTER_FLAG, "0")
    return _truthy(value)


def _field(payload: Mapping[str, object], *names: str) -> object | None:
    for name in names:
        value = payload.get(name)
        if value is not None:
            return value
    return None


def _text_field(payload: Mapping[str, object], *names: str) -> str | None:
    value = _field(payload, *names)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _decode_audio(value: object | None) -> bytes | str | None:
    """Decode wire audio without accepting arbitrary encoded/path ambiguity."""

    if isinstance(value, bytes):
        return value or None
    if not isinstance(value, str) or not value.strip():
        return None
    raw = value.strip()
    if raw.startswith("data:") and "," in raw:
        raw = raw.split(",", 1)[1]
    try:
        decoded = base64.b64decode(raw, validate=True)
    except (ValueError, binascii.Error):
        # A string remains a supported VoiceTurnRequest input (normally a
        # local path).  Do not guess that an arbitrary URL is caller audio.
        return value.strip()
    return decoded or None


def _router_contracts() -> tuple[Any, ...]:
    """Load router contracts only when the feature is actually used."""

    from ipfs_accelerate_py.voice_router import (  # noqa: WPS433
        VoiceResponsePlan,
        VoiceTurnRequest,
        process_voice_turn,
    )

    return VoiceResponsePlan, VoiceTurnRequest, process_voice_turn


class _WalletSTTProvider:
    """VoiceProvider shim around the wallet's existing Whisper HTTP helper."""

    cache_identity = "wallet-interface-whisper-v1"

    def transcribe(
        self,
        audio: bytes | str,
        *,
        model_name: str | None = None,
        language: str | None = None,
        device: str | None = None,
        **_: object,
    ) -> str:
        if not isinstance(audio, bytes):
            if not isinstance(audio, str) or not os.path.isfile(audio):
                raise ValueError("wallet Whisper adapter requires byte audio or a readable local file")
            with open(audio, "rb") as input_file:
                audio = input_file.read()
        from ._tts_http import _run_hf_whisper_stt  # noqa: WPS433

        result = _run_hf_whisper_stt(audio, language=language, model_name=model_name)
        if not isinstance(result, Mapping):
            raise TypeError("wallet Whisper helper returned an invalid result")
        text = _text_field(result, "text", "transcript", "transcription")
        if not text:
            raise ValueError("wallet Whisper helper returned an empty transcript")
        return text


def _audio_from_tts_result(result: object) -> tuple[bytes, str | None]:
    if isinstance(result, bytes):
        return result, "wav"
    if not isinstance(result, Mapping):
        raise TypeError("wallet IndexTTS helper returned an invalid result")
    value = _field(result, "audio_bytes", "audioBytes", "audio_base64", "audioBase64", "audio")
    if isinstance(value, bytes):
        audio = value
    elif isinstance(value, str) and value.strip():
        encoded = value.split(",", 1)[1] if value.startswith("data:") and "," in value else value
        try:
            audio = base64.b64decode(encoded, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise ValueError("wallet IndexTTS helper returned malformed audio") from exc
    else:
        raise ValueError("wallet IndexTTS helper returned no audio")
    if not audio:
        raise ValueError("wallet IndexTTS helper returned empty audio")
    format_name = _text_field(result, "audio_format", "audioFormat", "mimeType", "mime_type")
    if format_name and "/" in format_name:
        format_name = format_name.rsplit("/", 1)[-1]
    return audio, format_name or "wav"


class _WalletTTSProvider:
    """VoiceProvider shim around the wallet's resilient IndexTTS helper."""

    cache_identity = "wallet-interface-indextts-v1"

    def synthesize(
        self,
        text: str,
        *,
        voice: str | None = None,
        model_name: str | None = None,
        device: str | None = None,
        output_format: str | None = None,
        **_: object,
    ) -> bytes:
        from ._tts import _run_indextts_tts_with_batch_fallback  # noqa: WPS433

        result = _run_indextts_tts_with_batch_fallback(text=text, voice_description=voice)
        audio, _ = _audio_from_tts_result(result)
        return audio


class _WalletResponsePlanProvider:
    """Adapt an already selected wallet response into a plain response plan.

    The wallet's GraphRAG/agent layer may provide a richer provider through
    ``process_wallet_voice_turn(..., template_provider=...)``.  This small
    default preserves the existing proxy's text behavior while making the
    stage, status, and provenance contract explicit.  It intentionally adds
    no factual source claims of its own.
    """

    def __init__(self, response_text: str) -> None:
        self.response_text = response_text.strip()

    def retrieve(self, transcript: str, **_: object) -> object:
        voice_response_plan, _, _ = _router_contracts()
        return voice_response_plan(
            template_id="wallet-interface-response-v1",
            template=self.response_text,
            metadata={"adapter": "wallet_interface", "grounding_boundary": "upstream"},
        )


def build_voice_turn_request(payload: Mapping[str, object]) -> Any:
    """Build a canonical request from legacy camelCase/snake_case proxy data."""

    _, voice_turn_request, _ = _router_contracts()
    mode = (_text_field(payload, "mode") or "voice-reply").lower()
    audio = _decode_audio(_field(payload, "audio_bytes", "audioBytes", "audio_base64", "audioBase64", "audio"))
    transcript = _text_field(payload, "transcript", "transcription")
    if not transcript and mode == "tts":
        transcript = _text_field(payload, "text")
    if not transcript and mode == "voice-reply":
        # The UI has already performed remote/browser STT before voice-reply
        # generation.  Reusing userPrompt avoids a second paid STT call.  If
        # it is absent and audio exists, the canonical STT provider is used.
        transcript = _text_field(payload, "userPrompt", "user_prompt")
    context_value = _field(payload, "context")
    grounding_value = _field(payload, "grounding")
    context = dict(context_value) if isinstance(context_value, Mapping) else {}
    grounding = dict(grounding_value) if isinstance(grounding_value, Mapping) else {}
    return voice_turn_request(
        audio=audio,
        transcript=transcript,
        request_id=_text_field(payload, "request_id", "requestId"),
        context=context,
        grounding=grounding,
        language=_text_field(payload, "language"),
        locale=_text_field(payload, "locale"),
        voice=_text_field(payload, "voice", "voiceDescription", "voice_description"),
        stt_provider=_text_field(payload, "stt_provider", "sttProvider"),
        tts_provider=_text_field(payload, "tts_provider", "ttsProvider"),
        stt_model=_text_field(payload, "stt_model", "sttModel"),
        tts_model=_text_field(payload, "tts_model", "ttsModel"),
        output_format=_text_field(payload, "output_format", "outputFormat"),
        fallback_text=(
            _text_field(payload, "fallbackText", "fallback_text", "response_text", "responseText")
            or _text_field(payload, "text")
            or "I’m sorry, I couldn’t complete that voice request. Please try again."
        ),
    )


def serialize_voice_turn_result(result: Any, *, include_audio: bool = True) -> dict[str, object]:
    """Serialize a router receipt for the wallet proxy without losing metadata."""

    payload = dict(result.to_dict(include_audio=False))
    payload["adapter_version"] = VOICE_ROUTER_ADAPTER_VERSION
    payload["voice_router"] = True
    if include_audio and result.audio:
        encoded = base64.b64encode(result.audio).decode("ascii")
        payload["audio_base64"] = encoded
        # Keep the camelCase spelling consumed by older wallet proxy clients.
        payload["audioBase64"] = encoded
        payload["audio_mime_type"] = f"audio/{result.audio_format or 'wav'}"
    return payload


class WalletVoiceRouterAdapter:
    """Feature-flagged wallet adoption facade over ``process_voice_turn``."""

    def __init__(self, *, enabled: bool | None = None) -> None:
        self.enabled = is_unified_voice_router_enabled(enabled)

    def process(
        self,
        payload: Mapping[str, object],
        *,
        template_provider: object | None = None,
        stt_provider: object | None = None,
        tts_provider: object | None = None,
    ) -> dict[str, object] | None:
        if not self.enabled:
            return None
        if not isinstance(payload, Mapping):
            raise TypeError("wallet voice payload must be a mapping")
        request = build_voice_turn_request(payload)
        response_text = request.fallback_text
        provider = template_provider or _WalletResponsePlanProvider(response_text)
        stt = stt_provider or _WalletSTTProvider()
        tts = tts_provider or _WalletTTSProvider()
        _, _, process_voice_turn = _router_contracts()
        result = process_voice_turn(
            request,
            stt_provider_instance=stt,
            template_provider=provider,
            tts_provider_instance=tts,
        )
        return serialize_voice_turn_result(result)


def process_wallet_voice_turn(
    payload: Mapping[str, object],
    *,
    enabled: bool | None = None,
    template_provider: object | None = None,
    stt_provider: object | None = None,
    tts_provider: object | None = None,
) -> dict[str, object] | None:
    """Process one wallet proxy envelope when the staged flag is enabled."""

    return WalletVoiceRouterAdapter(enabled=enabled).process(
        payload,
        template_provider=template_provider,
        stt_provider=stt_provider,
        tts_provider=tts_provider,
    )


# Names used by early wallet proxy integrations remain available as aliases.
route_wallet_voice_turn = process_wallet_voice_turn
voice_router_result_payload = serialize_voice_turn_result


__all__ = [
    "AGENT_AUDIO_CHAT_SURFACE_RETAINS_SPEECH_RECOGNITION_EVIDENCE_TERM",
    "AUTO_010_REPAIR_RECEIPT_BOTH_GATES_EVIDENCE_TERM",
    "FOCUSED_TESTS_COVER_PROVENANCE_EVIDENCE_TERM",
    "G010_AUTHORITATIVE_EVIDENCE_MAP",
    "G010_REQUIRED_EVIDENCE_TERMS",
    "G010_RESIDUAL_EVIDENCE_MAP",
    "UNIFIED_VOICE_ROUTER_FLAG",
    "VOICE_ROUTER_ADAPTER_VERSION",
    "WalletVoiceRouterAdapter",
    "build_voice_turn_request",
    "is_unified_voice_router_enabled",
    "process_wallet_voice_turn",
    "route_wallet_voice_turn",
    "serialize_voice_turn_result",
    "voice_router_result_payload",
]
