"""Acceptance tests for VOICE-ACTION-012: AI infer route/action surface.

Criteria:
- Unified router path returns action surface when a slotted-DAG route is
  supplied (form field or GraphRAG/template metadata).
- Legacy IndexTTS infer path is unchanged when the unified flag is off
  (route/confirm form fields are ignored; no action surface).
- confirm_action dual-gate is preserved (confirm without execute flag never
  runs adapters).
"""

from __future__ import annotations

import base64
import io
import json
import struct
import sys
import wave
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]
for candidate in (
    REPO_ROOT,
    REPO_ROOT / "ipfs_datasets_py",
    REPO_ROOT / "ipfs_accelerate_py",
):
    candidate_str = str(candidate)
    if candidate.exists() and candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from ipfs_accelerate_py.voice_router import VoiceResponsePlan  # noqa: E402
from wallet_interface.helpers._voice_router_adapter import (  # noqa: E402
    process_wallet_voice_turn,
)
from wallet_interface.routes import ai_router as ai_router_module  # noqa: E402
from wallet_interface.routes.ai_router import (  # noqa: E402
    _resolve_infer_route,
    _route_from_template_metadata,
    create_router,
)


def _minimal_wav(*, frames: int = 160, sample_rate: int = 16_000) -> bytes:
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
    def __init__(self, *, route: str | None = None) -> None:
        self.route = route

    def retrieve(self, transcript: str, **_: object) -> VoiceResponsePlan:
        metadata: dict[str, object] = {"transcript": transcript, "adapter": "test"}
        if self.route:
            metadata["route"] = self.route
        return VoiceResponsePlan(
            template_id="wallet-ai-router-test-response",
            template="A safe response for the caller.",
            metadata=metadata,
        )


def _infer_client() -> TestClient:
    app = FastAPI()
    # Infer path does not use the wallet service; a stub keeps create_router happy.
    app.include_router(create_router(service=MagicMock()))
    return TestClient(app)


def _post_infer(client: TestClient, data: dict[str, str], *, audio: bytes | None = None):
    files = None
    if audio is not None:
        files = {"audio": ("input.wav", audio, "audio/wav")}
    return client.post("/voice/indextts/infer", data=data, files=files)


def test_resolve_infer_route_prefers_form_then_template_metadata() -> None:
    assert _resolve_infer_route(route="app_surface_navigation") == "app_surface_navigation"
    assert (
        _resolve_infer_route(response_route="wallet_document_support")
        == "wallet_document_support"
    )
    assert (
        _resolve_infer_route(
            template_metadata={"route": "calendar_event_support", "source": "graphrag"}
        )
        == "calendar_event_support"
    )
    assert (
        _resolve_infer_route(
            route="app_surface_navigation",
            template_metadata={"route": "calendar_event_support"},
        )
        == "app_surface_navigation"
    )
    assert _route_from_template_metadata({"response_route": "provider_contact_support"}) == (
        "provider_contact_support"
    )
    assert _resolve_infer_route(route="  ", template_metadata=None) is None


def test_unified_path_returns_action_surface_from_route_form(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unified flag on + route form field → action proposal surface on the receipt."""

    monkeypatch.setattr(ai_router_module, "is_unified_voice_router_enabled", lambda: True)

    def _process(envelope: dict[str, Any], *, enabled: bool = True, **_: object):
        assert enabled is True
        assert envelope["route"] == "app_surface_navigation"
        assert envelope.get("confirm_action") is None
        return process_wallet_voice_turn(
            envelope,
            enabled=True,
            template_provider=_Templates(route="app_surface_navigation"),
            tts_provider=_TTS(),
            action_execute_enabled=False,
        )

    monkeypatch.setattr(ai_router_module, "process_wallet_voice_turn", _process)

    client = _infer_client()
    response = _post_infer(
        client,
        {
            "mode": "voice-reply",
            "text": "A safe response for the caller.",
            "user_prompt": "Open my wallet documents surface",
            "route": "app_surface_navigation",
            "request_id": "infer-action-1",
        },
        audio=_VALID_TTS_AUDIO,
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["voice_router"] is True
    assert payload["status"] == "completed"
    assert payload["text"] == "A safe response for the caller."
    action = payload["action"]
    assert action["route"] == "app_surface_navigation"
    assert action["proposal"]["logical_action"] == "open_app_surface"
    assert action["proposal"]["descriptor_id"] == "voice.cli.open_app_surface.v1"
    assert "executable" not in action["proposal"]["arguments"]
    assert action["decision"]["kind"] == "confirm"
    assert action["receipt"] is None
    assert action["status"] == "confirm"
    assert action["execution_enabled"] is False
    assert payload["actionSurface"]["status"] == "confirm"


def test_unified_path_resolves_route_from_template_metadata_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GraphRAG/template metadata JSON form field supplies the slotted-DAG route."""

    monkeypatch.setattr(ai_router_module, "is_unified_voice_router_enabled", lambda: True)
    captured: dict[str, Any] = {}

    def _process(envelope: dict[str, Any], *, enabled: bool = True, **_: object):
        captured["envelope"] = dict(envelope)
        return process_wallet_voice_turn(
            envelope,
            enabled=True,
            template_provider=_Templates(route="wallet_document_support"),
            tts_provider=_TTS(),
            action_execute_enabled=False,
        )

    monkeypatch.setattr(ai_router_module, "process_wallet_voice_turn", _process)

    client = _infer_client()
    metadata = {
        "route": "wallet_document_support",
        "template_id": "wallet-docs-v1",
        "source": "wallet-graphrag",
    }
    response = _post_infer(
        client,
        {
            "mode": "voice-reply",
            "text": "A safe response for the caller.",
            "userPrompt": "Open wallet documents",
            "template_metadata": json.dumps(metadata),
            "requestId": "infer-meta-1",
        },
    )

    assert response.status_code == 200, response.text
    assert captured["envelope"]["route"] == "wallet_document_support"
    assert captured["envelope"]["template_metadata"]["source"] == "wallet-graphrag"
    action = response.json()["action"]
    assert action["route"] == "wallet_document_support"
    assert action["proposal"]["logical_action"] == "open_wallet_documents"
    assert action["status"] == "confirm"
    assert action["receipt"] is None


def test_legacy_path_unchanged_when_unified_flag_off(monkeypatch: pytest.MonkeyPatch) -> None:
    """Flag off: route/confirm are ignored; legacy TTS payload has no action surface."""

    monkeypatch.setattr(ai_router_module, "is_unified_voice_router_enabled", lambda: False)

    def _fail_unified(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("unified path must not run when flag is off")

    monkeypatch.setattr(ai_router_module, "process_wallet_voice_turn", _fail_unified)

    def _fake_generate(**_kwargs: object) -> tuple[str, dict[str, float]]:
        return "legacy reply text", {"generation_ms": 1.0}

    def _fake_tts(**_kwargs: object) -> dict[str, Any]:
        return {
            "audio_base64": base64.b64encode(_VALID_TTS_AUDIO).decode("ascii"),
            "audio_format": "wav",
            "latency": {"tts_ms": 2.0},
        }

    def _fake_retry(_label: str, operation: Any) -> Any:
        return operation()

    monkeypatch.setattr(ai_router_module, "_generate_indextts_voice_reply_text", _fake_generate)
    monkeypatch.setattr(ai_router_module, "_run_indextts_tts_with_batch_fallback", _fake_tts)
    monkeypatch.setattr(ai_router_module, "_run_indextts_with_endpoint_retry", _fake_retry)

    client = _infer_client()
    response = _post_infer(
        client,
        {
            "mode": "voice-reply",
            "text": "hello",
            "route": "app_surface_navigation",
            "confirm_action": "true",
            "request_id": "legacy-1",
        },
        audio=_VALID_TTS_AUDIO,
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["text"] == "legacy reply text"
    assert "audio_base64" in payload
    assert "action" not in payload
    assert "actionSurface" not in payload
    assert "voice_router" not in payload


def test_confirm_action_dual_gate_preserved(monkeypatch: pytest.MonkeyPatch) -> None:
    """confirm_action alone never executes; operator execute flag is required too."""

    monkeypatch.setattr(ai_router_module, "is_unified_voice_router_enabled", lambda: True)
    # Default execute flag off (clear any ambient grant).
    monkeypatch.delenv("WALLET_VOICE_ACTION_EXECUTE_ENABLED", raising=False)

    def _process(envelope: dict[str, Any], *, enabled: bool = True, **_: object):
        assert str(envelope.get("confirm_action")).lower() in {"1", "true", "yes", "on"}
        return process_wallet_voice_turn(
            envelope,
            enabled=True,
            template_provider=_Templates(route="app_surface_navigation"),
            tts_provider=_TTS(),
            action_execute_enabled=False,
        )

    monkeypatch.setattr(ai_router_module, "process_wallet_voice_turn", _process)

    client = _infer_client()
    response = _post_infer(
        client,
        {
            "mode": "voice-reply",
            "text": "A safe response for the caller.",
            "user_prompt": "Open calendar",
            "route": "app_surface_navigation",
            "confirm_action": "true",
            "request_id": "infer-confirm-blocked-1",
        },
    )

    assert response.status_code == 200, response.text
    action = response.json()["action"]
    assert action["status"] == "execution_disabled"
    assert action["receipt"] is None
    assert action["proposal"]["logical_action"] == "open_app_surface"
    assert action["execution_enabled"] is False


def test_confirm_action_and_execute_flag_permit_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Both gates present: explicit confirm + operator execute flag → receipt."""

    monkeypatch.setattr(ai_router_module, "is_unified_voice_router_enabled", lambda: True)
    monkeypatch.setenv("WALLET_VOICE_ACTION_EXECUTE_ENABLED", "1")

    def _process(envelope: dict[str, Any], *, enabled: bool = True, **_: object):
        return process_wallet_voice_turn(
            envelope,
            enabled=True,
            template_provider=_Templates(route="app_surface_navigation"),
            tts_provider=_TTS(),
            action_execute_enabled=True,
        )

    monkeypatch.setattr(ai_router_module, "process_wallet_voice_turn", _process)

    client = _infer_client()
    response = _post_infer(
        client,
        {
            "mode": "voice-reply",
            "text": "A safe response for the caller.",
            "user_prompt": "Open calendar",
            "response_route": "app_surface_navigation",
            "action_confirm": "true",
            "request_id": "infer-confirm-exec-1",
        },
    )

    assert response.status_code == 200, response.text
    action = response.json()["action"]
    assert action["status"] == "executed"
    assert action["receipt"] is not None
    assert action["receipt"]["status"] == "succeeded"
    assert action["decision"]["kind"] == "permit_execute"


def test_non_tool_route_is_not_actionable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ai_router_module, "is_unified_voice_router_enabled", lambda: True)

    def _process(envelope: dict[str, Any], *, enabled: bool = True, **_: object):
        return process_wallet_voice_turn(
            envelope,
            enabled=True,
            template_provider=_Templates(route="grounded_211_answer"),
            tts_provider=_TTS(),
        )

    monkeypatch.setattr(ai_router_module, "process_wallet_voice_turn", _process)

    client = _infer_client()
    response = _post_infer(
        client,
        {
            "mode": "voice-reply",
            "text": "A safe response for the caller.",
            "user_prompt": "I need food help",
            "route": "grounded_211_answer",
            "request_id": "infer-none-1",
        },
    )

    assert response.status_code == 200, response.text
    action = response.json()["action"]
    assert action["status"] == "route_not_actionable"
    assert action["proposal"] is None
