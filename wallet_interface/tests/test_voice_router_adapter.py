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


def test_default_action_stack_loads_pilot_catalog() -> None:
    """Default stack must bind the multi-descriptor 211-AI pilot catalog."""

    from ipfs_accelerate_py.action_runtime.catalog_211ai import (
        CATALOG_ID,
        PILOT_LOGICAL_ACTIONS,
        build_pilot_catalog,
        logical_action_to_descriptor_id,
    )
    from wallet_interface.helpers._voice_action_surface import (
        PILOT_ROUTE_TO_LOGICAL_ACTION,
        build_default_action_stack,
        pilot_descriptor_map,
    )

    catalog, policy, executor = build_default_action_stack()
    pilot = build_pilot_catalog()
    mapping = logical_action_to_descriptor_id()

    assert set(catalog.list_ids()) == set(pilot.list_ids())
    assert set(PILOT_LOGICAL_ACTIONS) <= {
        catalog.require(descriptor_id).logical_action for descriptor_id in catalog.list_ids()
    }
    assert pilot_descriptor_map() == dict(mapping)
    assert getattr(policy, "catalog", None) is catalog or set(
        getattr(policy, "catalog", catalog).list_ids()
    ) == set(pilot.list_ids())
    assert executor.catalog is catalog
    # No ambient execute authority: grant policy starts empty.
    assert getattr(executor.policy, "grants", {}) == {}
    # Every pilot route maps to a catalog-present logical action.
    for route, logical in PILOT_ROUTE_TO_LOGICAL_ACTION.items():
        assert logical in mapping, f"{route} → {logical} missing from pilot catalog"
        assert catalog.get(mapping[logical]) is not None
    assert CATALOG_ID == "211ai-pilot-v1"


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
    assert action["proposal"]["descriptor_id"] == "voice.python.open_app_surface.v1"
    assert "executable" not in action["proposal"]["arguments"]
    assert action["decision"]["kind"] == "confirm"
    assert action["receipt"] is None
    assert action["status"] == "confirm"
    assert action["execution_enabled"] is False
    assert payload["actionSurface"]["receipt"] is None


def test_action_surface_executes_only_with_flag_and_confirm(monkeypatch) -> None:
    """Confirm + execute flag may enter the executor; pilot adapters fail closed."""

    monkeypatch.setenv("WALLET_VOICE_ACTION_EXECUTE_ENABLED", "1")

    payload = process_wallet_voice_turn(
        {
            "mode": "voice-reply",
            "text": "A safe response for the caller.",
            "user_prompt": "Open app surface",
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
    # Pilot python adapters are not CLI-bound; dual-gate still reaches executor.
    assert action["status"] == "execution_failed"
    assert action["receipt"] is not None
    assert action["receipt"]["status"] == "failed"
    assert action["receipt"]["error"] == "adapter_not_implemented"
    assert action["decision"]["permits_execution"] is True
    assert action["proposal"]["descriptor_id"] == "voice.python.open_app_surface.v1"


def test_action_surface_confirm_without_flag_is_blocked() -> None:
    """Confirm without the operator execute flag must never produce a receipt."""

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
    assert action["proposal"]["descriptor_id"] == "voice.python.open_wallet_documents.v1"
    assert action["execution_enabled"] is False


def test_action_surface_confirm_without_flag_never_runs_for_all_pilot_routes() -> None:
    """Every pilot-mapped route: confirm alone never yields a receipt."""

    from wallet_interface.helpers._voice_action_surface import (
        PILOT_ROUTE_TO_LOGICAL_ACTION,
    )

    for route, logical in PILOT_ROUTE_TO_LOGICAL_ACTION.items():
        payload = process_wallet_voice_turn(
            {
                "mode": "voice-reply",
                "text": "A safe response for the caller.",
                "user_prompt": f"confirm {route}",
                "route": route,
                "confirm_action": True,
                "request_id": f"blocked-{route}",
            },
            enabled=True,
            template_provider=_Templates(),
            tts_provider=_TTS(),
            action_execute_enabled=False,
        )
        assert payload is not None, route
        action = payload["action"]
        assert action["proposal"] is not None, route
        assert action["proposal"]["logical_action"] == logical, route
        assert action["receipt"] is None, route
        assert action["status"] == "execution_disabled", route


def test_action_surface_all_pilot_routes_covered() -> None:
    """All 12 slotted-DAG routes classify to pilot proposal or content-only."""

    from wallet_interface.helpers._voice_action_surface import (
        CONTENT_ONLY_ROUTES,
        PILOT_ROUTE_TO_LOGICAL_ACTION,
        PILOT_SLOTTED_ROUTES,
        pilot_descriptor_map,
    )

    descriptor_map = pilot_descriptor_map()
    assert len(PILOT_SLOTTED_ROUTES) == 12
    assert set(CONTENT_ONLY_ROUTES).isdisjoint(PILOT_ROUTE_TO_LOGICAL_ACTION)
    assert set(PILOT_SLOTTED_ROUTES) == set(CONTENT_ONLY_ROUTES) | set(
        PILOT_ROUTE_TO_LOGICAL_ACTION
    )

    expected_status = {
        "app_surface_navigation": "confirm",
        "wallet_document_support": "confirm",
        "calendar_event_support": "confirm",
        "provider_contact_support": "confirm",
        "service_interaction_support": "confirm",
        "grounded_211_answer": "confirm",
        "live_agent": "handoff",
        "safety_guardrail_support": "handoff",
    }

    for route in PILOT_SLOTTED_ROUTES:
        payload = process_wallet_voice_turn(
            {
                "mode": "voice-reply",
                "text": "A safe response for the caller.",
                "user_prompt": f"route {route}",
                "route": route,
                "request_id": f"pilot-route-{route}",
            },
            enabled=True,
            template_provider=_Templates(),
            tts_provider=_TTS(),
            action_execute_enabled=False,
        )
        assert payload is not None, route
        action = payload["action"]
        assert action["route"] == route
        assert action["receipt"] is None, route
        assert action["execution_enabled"] is False, route

        if route in CONTENT_ONLY_ROUTES:
            assert action["status"] == "route_not_actionable", route
            assert action["proposal"] is None, route
            continue

        logical = PILOT_ROUTE_TO_LOGICAL_ACTION[route]
        assert action["proposal"]["logical_action"] == logical, route
        assert action["proposal"]["descriptor_id"] == descriptor_map[logical], route
        assert "executable" not in action["proposal"].get("arguments", {}), route
        assert action["status"] == expected_status[route], (
            route,
            action["status"],
            action.get("decision"),
        )
        assert action["decision"] is not None, route


def test_action_surface_non_tool_route_is_not_actionable() -> None:
    payload = process_wallet_voice_turn(
        {
            "mode": "voice-reply",
            "text": "A safe response for the caller.",
            "user_prompt": "Please clarify",
            "route": "clarifying_prompt",
            "request_id": "action-none-1",
        },
        enabled=True,
        template_provider=_Templates(),
        tts_provider=_TTS(),
    )

    assert payload is not None
    assert payload["action"]["status"] == "route_not_actionable"
    assert payload["action"]["proposal"] is None
