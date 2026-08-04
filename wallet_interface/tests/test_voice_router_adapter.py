"""Offline acceptance tests for the wallet unified voice-router boundary."""

from __future__ import annotations

import base64
import io
import struct
import wave

from ipfs_accelerate_py.voice_router import VoiceResponsePlan
from wallet_interface.helpers._voice_router_adapter import (
    WalletVoiceRouterAdapter,
    _PackageFirstTTSProvider,
    _package_indextts_tts_provider,
    build_voice_turn_request,
    process_wallet_voice_turn,
)


def _minimal_wav(*, frames: int = 160, sample_rate: int = 16_000) -> bytes:
    """Return a tiny PCM WAV the voice-router decode gate accepts."""
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        samples = b"".join(
            struct.pack("<h", 1_000 if index % 2 else -1_000) for index in range(frames)
        )
        handle.writeframes(samples)
    return buffer.getvalue()


_VALID_TTS_AUDIO = _minimal_wav()


class _TTS:
    def __init__(self) -> None:
        self.texts: list[str] = []

    def synthesize(self, text: str, **_: object) -> bytes:
        self.texts.append(text)
        return _VALID_TTS_AUDIO


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
    assert payload["audio_base64"] == base64.b64encode(_VALID_TTS_AUDIO).decode("ascii")
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
            return (_VALID_TTS_AUDIO,)

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
        lambda self, text, **options: _VALID_TTS_AUDIO,
    )
    provider = _PackageFirstTTSProvider(_FailedPackage())

    audio = provider.synthesize("hello")

    assert audio == _VALID_TTS_AUDIO
    assert provider.last_receipt is not None
    assert provider.last_receipt.degraded is True  # type: ignore[attr-defined]
    assert (
        provider.last_receipt.to_dict()["selected_backend"]  # type: ignore[attr-defined]
        == "wallet_gradio_compatibility"
    )


def test_action_surface_proposes_confirm_without_executing() -> None:
    """Library routes propose actions but never execute without grant + flag."""

    payload = process_wallet_voice_turn(
        {
            "mode": "voice-reply",
            "text": "A safe response for the caller.",
            "user_prompt": "Open my wallet documents surface",
            "route": "app_surface_navigation",
            "request_id": "action-propose-1",
        },
        enabled=True,
        template_provider=_Templates(),
        tts_provider=_TTS(),
        action_execute_enabled=False,
    )

    assert payload is not None
    assert payload["status"] == "completed"
    action = payload["action"]
    assert action["route"] == "app_surface_navigation"
    assert action["proposal"]["logical_action"] == "open_app_surface"
    assert action["proposal"]["descriptor_id"] == "voice.cli.open_app_surface.v1"
    assert "executable" not in action["proposal"]["arguments"]
    assert action["decision"]["kind"] == "confirm"
    assert action["receipt"] is None
    assert action["status"] == "confirm"
    assert action["execution_enabled"] is False


def test_action_surface_executes_only_with_flag_and_confirm(monkeypatch) -> None:
    monkeypatch.setenv("WALLET_VOICE_ACTION_EXECUTE_ENABLED", "1")

    payload = process_wallet_voice_turn(
        {
            "mode": "voice-reply",
            "text": "A safe response for the caller.",
            "user_prompt": "Open calendar",
            "route": "app_surface_navigation",
            "confirm_action": True,
            "request_id": "action-exec-1",
        },
        enabled=True,
        template_provider=_Templates(),
        tts_provider=_TTS(),
        action_execute_enabled=True,
    )

    assert payload is not None
    action = payload["action"]
    assert action["status"] == "executed"
    assert action["receipt"] is not None
    assert action["receipt"]["status"] == "succeeded"
    assert action["receipt"]["exit_code"] == 0
    assert action["decision"]["kind"] == "permit_execute"


def test_action_surface_confirm_without_flag_is_blocked() -> None:
    payload = process_wallet_voice_turn(
        {
            "mode": "voice-reply",
            "text": "A safe response for the caller.",
            "user_prompt": "Open wallet docs",
            "route": "wallet_document_support",
            "confirm_action": True,
            "request_id": "action-blocked-1",
        },
        enabled=True,
        template_provider=_Templates(),
        tts_provider=_TTS(),
        action_execute_enabled=False,
    )

    assert payload is not None
    action = payload["action"]
    assert action["status"] == "execution_disabled"
    assert action["receipt"] is None
    assert action["proposal"]["logical_action"] == "open_wallet_documents"


def test_action_surface_non_tool_route_is_not_actionable() -> None:
    payload = process_wallet_voice_turn(
        {
            "mode": "voice-reply",
            "text": "A safe response for the caller.",
            "user_prompt": "I need food help",
            "route": "grounded_211_answer",
            "request_id": "action-none-1",
        },
        enabled=True,
        template_provider=_Templates(),
        tts_provider=_TTS(),
    )

    assert payload is not None
    assert payload["action"]["status"] == "route_not_actionable"
    assert payload["action"]["proposal"] is None
