"""Offline acceptance tests for the wallet unified voice-router boundary."""

from __future__ import annotations

import base64

from ipfs_accelerate_py.voice_router import VoiceResponsePlan
from wallet_interface.helpers._voice_router_adapter import (
    WalletVoiceRouterAdapter,
    build_voice_turn_request,
    process_wallet_voice_turn,
)


class _TTS:
    def __init__(self) -> None:
        self.texts: list[str] = []

    def synthesize(self, text: str, **_: object) -> bytes:
        self.texts.append(text)
        return b"RIFF-unified-wallet-audio"


class _Templates:
    def retrieve(self, transcript: str, **_: object) -> VoiceResponsePlan:
        return VoiceResponsePlan(
            template_id="wallet-test-response",
            template="A safe response for the caller.",
            metadata={"transcript": transcript},
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
    assert payload["audio_base64"] == base64.b64encode(b"RIFF-unified-wallet-audio").decode("ascii")
    assert payload["audioBase64"] == payload["audio_base64"]
    assert payload["provenance"]["template_id"] == "wallet-test-response"  # type: ignore[index]
    assert [trace["stage"] for trace in payload["traces"]] == [  # type: ignore[index]
        "transcription",
        "retrieval",
        "rendering",
        "synthesis",
    ]
    assert tts.texts == ["A safe response for the caller."]
