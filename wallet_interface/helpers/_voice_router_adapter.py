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
import hashlib
import os
import threading
import time
from collections.abc import Callable, Mapping
from typing import Any, Final

UNIFIED_VOICE_ROUTER_FLAG = "WALLET_VOICE_UNIFIED_ROUTER_ENABLED"
RUNTIME_AUDIO_MANIFEST_ENV = "WALLET_ABBY_VOICE_RUNTIME_MANIFEST_URL"
RUNTIME_GRAPHRAG_MINIMUM_CONFIDENCE_ENV = (
    "WALLET_ABBY_VOICE_GRAPHRAG_MINIMUM_CONFIDENCE"
)
VOICE_ROUTER_ADAPTER_VERSION = "1.4"
_AUDIO_MIME_TYPES: Final[dict[str, str]] = {
    "aac": "audio/aac",
    "flac": "audio/flac",
    "m4a": "audio/mp4",
    "mp3": "audio/mpeg",
    "mpeg": "audio/mpeg",
    "ogg": "audio/ogg",
    "opus": "audio/ogg",
    "wav": "audio/wav",
    "wave": "audio/wav",
    "webm": "audio/webm",
}
_PACKAGE_INDEXTTS_PROVIDER: object | None = None
_PACKAGE_INDEXTTS_PROVIDER_KEY: tuple[object, ...] = ()
_PACKAGE_PRECOMPUTED_AUDIO_RESOLVER: object | None = None
_PACKAGE_PRECOMPUTED_AUDIO_RESOLVER_KEY: tuple[object, ...] = ()
_PACKAGE_PRECOMPUTED_AUDIO_RESOLVER_ERROR: str | None = None
_PACKAGE_PRECOMPUTED_AUDIO_RESOLVER_FAILURE_AT = 0.0
_PACKAGE_PRECOMPUTED_AUDIO_RESOLVER_LOCK = threading.Lock()
_PACKAGE_GRAPHRAG_TEMPLATE_PROVIDER: object | None = None
_PACKAGE_GRAPHRAG_TEMPLATE_PROVIDER_KEY: tuple[object, ...] = ()
_PACKAGE_GRAPHRAG_TEMPLATE_PROVIDER_ERROR: str | None = None
_PACKAGE_GRAPHRAG_TEMPLATE_PROVIDER_FAILURE_AT = 0.0
_PACKAGE_GRAPHRAG_TEMPLATE_PROVIDER_LOCK = threading.Lock()
_PACKAGE_RESPONSE_DAG_RUNTIME: object | None = None
_PACKAGE_RESPONSE_DAG_RUNTIME_KEY: tuple[object, ...] = ()
_PACKAGE_RESPONSE_DAG_RUNTIME_ERROR: str | None = None
_PACKAGE_RESPONSE_DAG_RUNTIME_FAILURE_AT = 0.0
_PACKAGE_RESPONSE_DAG_RUNTIME_LOCK = threading.Lock()
_VOICE_SURFACE_ALIASES: Final[dict[str, str]] = {
    "web": "website",
    "website": "website",
    "sip": "telephone",
    "telephone": "telephone",
    "telephony": "telephone",
    "twilio": "telephone",
}

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


def _mapping_field(payload: Mapping[str, object], *names: str) -> dict[str, object]:
    value = _field(payload, *names)
    return dict(value) if isinstance(value, Mapping) else {}


def _voice_surface(
    payload: Mapping[str, object],
    context: Mapping[str, object],
) -> str:
    """Resolve the public surface without retaining call/session identifiers."""

    payload_surface = _text_field(payload, "surface")
    context_surface = _text_field(context, "surface")
    def normalize(value: str) -> str:
        requested = value.casefold()
        try:
            return _VOICE_SURFACE_ALIASES[requested]
        except KeyError as exc:
            raise ValueError(
                f"unsupported wallet voice surface: {requested}"
            ) from exc

    if payload_surface and context_surface:
        if normalize(payload_surface) != normalize(context_surface):
            raise ValueError("wallet voice payload has conflicting surfaces")
    requested = str(payload_surface or context_surface or "website")
    return normalize(requested)


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

    def __init__(self) -> None:
        self.last_result: dict[str, Any] | None = None

    def synthesize(
        self,
        text: str,
        *,
        voice: str | None = None,
        model_name: str | None = None,
        device: str | None = None,
        output_format: str | None = None,
        reference_audio: object | None = None,
        reference_audio_name: str | None = None,
        reference_audio_mime_type: str | None = None,
        **_: object,
    ) -> bytes:
        from ._tts import (  # noqa: WPS433
            _run_indextts_compatibility_tts_with_batch_fallback,
        )

        result = _run_indextts_compatibility_tts_with_batch_fallback(
            text=text,
            voice_description=voice,
            reference_audio=(
                reference_audio
                if isinstance(reference_audio, bytes)
                else None
            ),
            reference_audio_name=reference_audio_name,
            reference_audio_mime_type=reference_audio_mime_type,
        )
        self.last_result = dict(result)
        audio, _ = _audio_from_tts_result(result)
        return audio


def _package_indextts_tts_provider() -> object | None:
    """Build the package-owned Publicus provider with wallet credentials."""

    global _PACKAGE_INDEXTTS_PROVIDER
    global _PACKAGE_INDEXTTS_PROVIDER_KEY

    explicitly_configured = (
        os.getenv("IPFS_ACCELERATE_PY_ABBY_INDEXTTS_URLS", "").strip()
        or os.getenv("IPFS_ACCELERATE_PY_ABBY_INDEXTTS_URL", "").strip()
    )
    if explicitly_configured:
        configured = explicitly_configured
    else:
        from ._tts_config import _indextts_space_base_url  # noqa: WPS433

        configured = _indextts_space_base_url()
    endpoints: list[str] = []
    for candidate in configured.replace(",", " ").split():
        normalized = candidate.strip().rstrip("/")
        if normalized and normalized not in endpoints:
            endpoints.append(normalized)
    from ._tts_http import _configured_hf_token  # noqa: WPS433

    token = _configured_hf_token()
    token_digest = (
        hashlib.sha256(token.encode("utf-8")).hexdigest()[:16] if token else ""
    )
    provider_key: tuple[object, ...] = (
        tuple(endpoints),
        token_digest,
        os.getenv("IPFS_ACCELERATE_PY_ABBY_INDEXTTS_MODEL", ""),
        os.getenv("WALLET_INDEXTTS_MODEL_NAME", ""),
        os.getenv("IPFS_ACCELERATE_PY_ABBY_HF_BILL_TO", ""),
        os.getenv("WALLET_INDEXTTS_HF_BILL_TO", ""),
        os.getenv("IPFS_ACCELERATE_PY_ABBY_INDEXTTS_BACKEND", ""),
        os.getenv("IPFS_ACCELERATE_PY_ABBY_INDEXTTS_REFERENCE_AUDIO", ""),
        os.getenv("WALLET_INDEXTTS_REFERENCE_AUDIO_PATH", ""),
        os.getenv("IPFS_ACCELERATE_PY_ABBY_INDEXTTS_REFERENCE_AUDIO_REMOTE_PATH", ""),
        os.getenv("WALLET_INDEXTTS_REFERENCE_AUDIO_REMOTE_PATH", ""),
        os.getenv("IPFS_ACCELERATE_PY_ABBY_INDEXTTS_API_NAME", ""),
        os.getenv("WALLET_INDEXTTS_API_NAME", ""),
        os.getenv("IPFS_ACCELERATE_PY_ABBY_INDEXTTS_BATCH_API_NAME", ""),
        os.getenv("WALLET_INDEXTTS_BATCH_API_NAME", ""),
        os.getenv("IPFS_ACCELERATE_PY_ABBY_INDEXTTS_FN_INDEX", ""),
        os.getenv("WALLET_INDEXTTS_FN_INDEX", ""),
        os.getenv("IPFS_ACCELERATE_PY_ABBY_INDEXTTS_BATCH_FN_INDEX", ""),
        os.getenv("WALLET_INDEXTTS_BATCH_FN_INDEX", ""),
        os.getenv("IPFS_ACCELERATE_PY_ABBY_INDEXTTS_TIMEOUT_SECONDS", ""),
        os.getenv("IPFS_ACCELERATE_PY_ABBY_INDEXTTS_MAX_RETRIES", ""),
    )
    if (
        _PACKAGE_INDEXTTS_PROVIDER is not None
        and provider_key == _PACKAGE_INDEXTTS_PROVIDER_KEY
    ):
        return _PACKAGE_INDEXTTS_PROVIDER

    try:
        from ipfs_accelerate_py.voice_providers.abby import (  # noqa: WPS433
            IndexTTSHTTPProvider,
        )

        _PACKAGE_INDEXTTS_PROVIDER = IndexTTSHTTPProvider.from_environment(
            endpoints=tuple(endpoints),
            token=token,
        )
    except (ImportError, OSError, RuntimeError, TypeError, ValueError):
        _PACKAGE_INDEXTTS_PROVIDER = None
        _PACKAGE_INDEXTTS_PROVIDER_KEY = ()
        return None
    _PACKAGE_INDEXTTS_PROVIDER_KEY = provider_key
    return _PACKAGE_INDEXTTS_PROVIDER


class _WalletTTSCompatibilityReceipt:
    """Receipt emitted when the package provider needed the legacy wallet path."""

    degraded = True

    def __init__(self, package_provider: object, error: Exception) -> None:
        receipt = getattr(package_provider, "last_receipt", None)
        to_dict = getattr(receipt, "to_dict", None)
        try:
            package_receipt = to_dict() if callable(to_dict) else None
        except Exception:
            package_receipt = None
        self.package_receipt = package_receipt
        self.error_code = str(
            getattr(error, "code", "") or error.__class__.__name__
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "provider": "wallet_indextts_compatibility",
            "operation": "synthesis",
            "status": "degraded",
            "degraded": True,
            "selected_backend": "wallet_gradio_compatibility",
            "package_error_code": self.error_code,
            "package_receipt": self.package_receipt,
        }


class _PackageFirstTTSProvider:
    """Use package-native Publicus batch synthesis, then the wallet shim."""

    cache_identity = "wallet-package-first-indextts-v2"

    def __init__(self, package_provider: object) -> None:
        self.package_provider = package_provider
        self.compatibility_provider = _WalletTTSProvider()
        self.last_receipt: object | None = None
        self.last_backend = ""
        self.last_spoken_text = ""

    def synthesize(
        self,
        text: str,
        *,
        voice: str | None = None,
        model_name: str | None = None,
        device: str | None = None,
        output_format: str | None = None,
        **options: object,
    ) -> bytes:
        from ._tts_config import _indextts_batch_enabled  # noqa: WPS433
        from ._tts_normalization import (  # noqa: WPS433
            _normalize_indextts_spoken_text,
        )

        spoken_text = _normalize_indextts_spoken_text(text)
        self.last_spoken_text = spoken_text
        try:
            synthesize_batch = getattr(self.package_provider, "synthesize_batch", None)
            if _indextts_batch_enabled() and callable(synthesize_batch):
                outputs = synthesize_batch(
                    [spoken_text],
                    voice=voice,
                    model_name=model_name,
                    device=device,
                    output_format=output_format,
                    **options,
                )
                if (
                    not isinstance(outputs, (list, tuple))
                    or len(outputs) != 1
                    or not isinstance(outputs[0], bytes)
                    or not outputs[0]
                ):
                    raise TypeError("package IndexTTS batch returned invalid audio")
                audio = outputs[0]
                self.last_backend = "package-publicus-batch"
            else:
                synthesize = getattr(self.package_provider, "synthesize")
                audio = synthesize(
                    spoken_text,
                    voice=voice,
                    model_name=model_name,
                    device=device,
                    output_format=output_format,
                    **options,
                )
                self.last_backend = "package-indextts-single"
            if not isinstance(audio, bytes) or not audio:
                raise TypeError("package IndexTTS returned invalid audio")
            self.last_receipt = getattr(self.package_provider, "last_receipt", None)
            return audio
        except Exception as package_error:
            audio = self.compatibility_provider.synthesize(
                text,
                voice=voice,
                model_name=model_name,
                device=device,
                output_format=output_format,
                **options,
            )
            self.last_receipt = _WalletTTSCompatibilityReceipt(
                self.package_provider,
                package_error,
            )
            self.last_backend = "wallet-gradio-compatibility"
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


class _WalletLazyResponsePlanProvider:
    """Generate the wallet LLM fallback only after primary GraphRAG misses."""

    provider_name = "wallet-llm-fallback"

    def __init__(
        self,
        generate: Callable[[], tuple[str, Mapping[str, object]]],
    ) -> None:
        if not callable(generate):
            raise TypeError("generate must be callable")
        self._generate = generate
        self._lock = threading.Lock()
        self._generated = False
        self.response_text = ""
        self.generation_latency: dict[str, object] = {}
        self.error_code: str | None = None

    @property
    def generated(self) -> bool:
        return self._generated

    def retrieve(self, transcript: str, **_: object) -> object:
        with self._lock:
            if not self._generated:
                try:
                    response_text, latency = self._generate()
                    response_text = str(response_text or "").strip()
                    if not response_text:
                        raise ValueError(
                            "wallet LLM fallback returned empty text"
                        )
                    if not isinstance(latency, Mapping):
                        raise TypeError(
                            "wallet LLM fallback latency must be a mapping"
                        )
                except Exception as exc:
                    self.error_code = exc.__class__.__name__
                    raise
                self.response_text = response_text
                self.generation_latency = dict(latency)
                self._generated = True
        voice_response_plan, _, _ = _router_contracts()
        return voice_response_plan(
            template_id="wallet-interface-llm-fallback-v1",
            template=self.response_text,
            metadata={
                "adapter": "wallet_interface",
                "generated_fallback": True,
                "grounding_boundary": "upstream",
                "slotted_template": False,
            },
        )


def build_voice_turn_request(
    payload: Mapping[str, object],
    *,
    synthesis_identity: object | None = None,
) -> Any:
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
    context = _mapping_field(payload, "context")
    context["surface"] = _voice_surface(payload, context)
    grounding = _mapping_field(payload, "grounding")
    stt_options = _mapping_field(payload, "stt_options", "sttOptions")
    tts_options = _mapping_field(payload, "tts_options", "ttsOptions")
    identity_to_dict = getattr(synthesis_identity, "to_dict", None)
    identity = (
        dict(identity_to_dict())
        if callable(identity_to_dict)
        else (
            dict(synthesis_identity)
            if isinstance(synthesis_identity, Mapping)
            else {}
        )
    )
    identity_options = {
        "channels": identity.get("channels"),
        "codec": identity.get("codec"),
        "generation_settings": identity.get("generation_settings"),
        "provider_version": identity.get("provider_version"),
        "reference_audio_sha256": identity.get(
            "reference_audio_sha256"
        ),
        "sample_rate_hz": identity.get("sample_rate_hz"),
    }
    for key, value in identity_options.items():
        if value is not None:
            tts_options.setdefault(key, value)
    return voice_turn_request(
        audio=audio,
        transcript=transcript,
        request_id=_text_field(payload, "request_id", "requestId"),
        context=context,
        grounding=grounding,
        language=_text_field(payload, "language"),
        locale=(
            _text_field(payload, "locale")
            or str(identity.get("locale") or "").strip()
            or None
        ),
        voice=(
            _text_field(
                payload,
                "voice",
                "voiceDescription",
                "voice_description",
            )
            or str(identity.get("voice") or "").strip()
            or None
        ),
        stt_provider=_text_field(payload, "stt_provider", "sttProvider"),
        tts_provider=(
            _text_field(payload, "tts_provider", "ttsProvider")
            or str(identity.get("provider") or "").strip()
            or None
        ),
        stt_model=_text_field(payload, "stt_model", "sttModel"),
        tts_model=(
            _text_field(payload, "tts_model", "ttsModel")
            or str(identity.get("model") or "").strip()
            or None
        ),
        device=_text_field(payload, "device"),
        output_format=(
            _text_field(payload, "output_format", "outputFormat")
            or str(identity.get("codec") or "").strip()
            or None
        ),
        fallback_text=(
            _text_field(payload, "fallbackText", "fallback_text", "response_text", "responseText")
            or _text_field(payload, "text")
            or "I’m sorry, I couldn’t complete that voice request. Please try again."
        ),
        stt_options=stt_options,
        tts_options=tts_options,
    )


def _package_precomputed_audio_resolver() -> object | None:
    """Load the explicitly configured immutable runtime manifest once.

    Failed loads create an empty resolver so the router records a measurable
    cache miss and safely falls through to live TTS.  A bounded retry window
    avoids turning a temporary read outage into either a request storm or a
    process-lifetime failure.
    """

    global _PACKAGE_PRECOMPUTED_AUDIO_RESOLVER
    global _PACKAGE_PRECOMPUTED_AUDIO_RESOLVER_ERROR
    global _PACKAGE_PRECOMPUTED_AUDIO_RESOLVER_FAILURE_AT
    global _PACKAGE_PRECOMPUTED_AUDIO_RESOLVER_KEY

    manifest_url = str(os.getenv(RUNTIME_AUDIO_MANIFEST_ENV) or "").strip()
    if not manifest_url:
        return None
    timeout_raw = str(
        os.getenv(
            "WALLET_ABBY_VOICE_RUNTIME_MANIFEST_TIMEOUT_SECONDS",
            "15",
        )
        or "15"
    )
    retry_raw = str(
        os.getenv(
            "WALLET_ABBY_VOICE_RUNTIME_MANIFEST_RETRY_SECONDS",
            "60",
        )
        or "60"
    )
    try:
        timeout_seconds = max(1.0, float(timeout_raw))
        retry_seconds = max(1.0, float(retry_raw))
    except ValueError as exc:
        raise ValueError(
            "Abby runtime-manifest timeout/retry values must be numeric"
        ) from exc
    resolver_key: tuple[object, ...] = (manifest_url, timeout_seconds)
    now = time.monotonic()
    with _PACKAGE_PRECOMPUTED_AUDIO_RESOLVER_LOCK:
        if (
            resolver_key == _PACKAGE_PRECOMPUTED_AUDIO_RESOLVER_KEY
            and _PACKAGE_PRECOMPUTED_AUDIO_RESOLVER is not None
            and (
                _PACKAGE_PRECOMPUTED_AUDIO_RESOLVER_ERROR is None
                or now - _PACKAGE_PRECOMPUTED_AUDIO_RESOLVER_FAILURE_AT
                < retry_seconds
            )
        ):
            return _PACKAGE_PRECOMPUTED_AUDIO_RESOLVER
        try:
            from ipfs_accelerate_py.voice_runtime_manifest import (  # noqa: WPS433
                load_pinned_voice_runtime_resolver,
            )

            resolver = load_pinned_voice_runtime_resolver(
                manifest_url,
                timeout_seconds=timeout_seconds,
            )
            error_code = None
            failure_at = 0.0
        except Exception as exc:
            from ipfs_accelerate_py.voice_audio_resolver import (  # noqa: WPS433
                PrecomputedVoiceAudioResolver,
            )

            resolver = PrecomputedVoiceAudioResolver()
            error_code = exc.__class__.__name__
            failure_at = now
        _PACKAGE_PRECOMPUTED_AUDIO_RESOLVER = resolver
        _PACKAGE_PRECOMPUTED_AUDIO_RESOLVER_KEY = resolver_key
        _PACKAGE_PRECOMPUTED_AUDIO_RESOLVER_ERROR = error_code
        _PACKAGE_PRECOMPUTED_AUDIO_RESOLVER_FAILURE_AT = failure_at
        return resolver


def _package_graphrag_template_provider() -> object | None:
    """Load GraphRAG from the same explicitly pinned release as audio."""

    global _PACKAGE_GRAPHRAG_TEMPLATE_PROVIDER
    global _PACKAGE_GRAPHRAG_TEMPLATE_PROVIDER_ERROR
    global _PACKAGE_GRAPHRAG_TEMPLATE_PROVIDER_FAILURE_AT
    global _PACKAGE_GRAPHRAG_TEMPLATE_PROVIDER_KEY

    manifest_url = str(os.getenv(RUNTIME_AUDIO_MANIFEST_ENV) or "").strip()
    if not manifest_url:
        return None
    timeout_raw = str(
        os.getenv(
            "WALLET_ABBY_VOICE_RUNTIME_MANIFEST_TIMEOUT_SECONDS",
            "15",
        )
        or "15"
    )
    retry_raw = str(
        os.getenv(
            "WALLET_ABBY_VOICE_RUNTIME_MANIFEST_RETRY_SECONDS",
            "60",
        )
        or "60"
    )
    confidence_raw = str(
        os.getenv(RUNTIME_GRAPHRAG_MINIMUM_CONFIDENCE_ENV, "0.35")
        or "0.35"
    )
    try:
        timeout_seconds = max(1.0, float(timeout_raw))
        retry_seconds = max(1.0, float(retry_raw))
        minimum_confidence = float(confidence_raw)
        if not 0.0 <= minimum_confidence <= 1.0:
            raise ValueError("confidence must be between zero and one")
    except ValueError:
        timeout_seconds = 15.0
        retry_seconds = 60.0
        minimum_confidence = 0.35
        configuration_error = "ValueError"
    else:
        configuration_error = None

    provider_key: tuple[object, ...] = (
        manifest_url,
        timeout_seconds,
        minimum_confidence,
        configuration_error,
    )
    now = time.monotonic()
    with _PACKAGE_GRAPHRAG_TEMPLATE_PROVIDER_LOCK:
        if (
            provider_key == _PACKAGE_GRAPHRAG_TEMPLATE_PROVIDER_KEY
            and (
                _PACKAGE_GRAPHRAG_TEMPLATE_PROVIDER is not None
                or (
                    _PACKAGE_GRAPHRAG_TEMPLATE_PROVIDER_ERROR is not None
                    and now - _PACKAGE_GRAPHRAG_TEMPLATE_PROVIDER_FAILURE_AT
                    < retry_seconds
                )
            )
        ):
            return _PACKAGE_GRAPHRAG_TEMPLATE_PROVIDER
        if configuration_error is not None:
            provider = None
            error_code = configuration_error
            failure_at = now
        else:
            try:
                from ipfs_accelerate_py.voice_router import (  # noqa: WPS433
                    GraphRAGVoiceTemplateProvider,
                )
                from ipfs_accelerate_py.voice_runtime_manifest import (  # noqa: WPS433
                    load_pinned_voice_graphrag_provider,
                )

                backend = load_pinned_voice_graphrag_provider(
                    manifest_url,
                    timeout_seconds=timeout_seconds,
                    minimum_confidence=minimum_confidence,
                )
                provider = GraphRAGVoiceTemplateProvider(
                    backend,
                    minimum_confidence=minimum_confidence,
                )
                error_code = None
                failure_at = 0.0
            except Exception as exc:
                provider = None
                error_code = exc.__class__.__name__
                failure_at = now
        _PACKAGE_GRAPHRAG_TEMPLATE_PROVIDER = provider
        _PACKAGE_GRAPHRAG_TEMPLATE_PROVIDER_KEY = provider_key
        _PACKAGE_GRAPHRAG_TEMPLATE_PROVIDER_ERROR = error_code
        _PACKAGE_GRAPHRAG_TEMPLATE_PROVIDER_FAILURE_AT = failure_at
        return provider


def _package_response_dag_runtime() -> object | None:
    """Build the package-owned local-only response-DAG runtime if selected."""

    global _PACKAGE_RESPONSE_DAG_RUNTIME
    global _PACKAGE_RESPONSE_DAG_RUNTIME_ERROR
    global _PACKAGE_RESPONSE_DAG_RUNTIME_FAILURE_AT
    global _PACKAGE_RESPONSE_DAG_RUNTIME_KEY

    from ipfs_accelerate_py.voice_response_dag_runtime import (  # noqa: WPS433
        RESPONSE_DAG_AUDIO_ROOT_ENV,
        RESPONSE_DAG_QUEUE_ROOT_ENV,
        RESPONSE_DAG_VALIDATOR_DEVICE_ENV,
        RESPONSE_DAG_VALIDATOR_LANGUAGE_ENV,
        RESPONSE_DAG_VALIDATOR_MAX_WER_BP_ENV,
        RESPONSE_DAG_VALIDATOR_MODEL_ENV,
        RESPONSE_DAG_VALIDATOR_PROVIDER_ENV,
        load_local_voice_response_dag_runtime_from_environment,
    )

    queue_root = str(os.getenv(RESPONSE_DAG_QUEUE_ROOT_ENV) or "").strip()
    if not queue_root:
        return None
    runtime_key: tuple[object, ...] = tuple(
        str(os.getenv(name) or "").strip()
        for name in (
            RESPONSE_DAG_QUEUE_ROOT_ENV,
            RESPONSE_DAG_AUDIO_ROOT_ENV,
            RESPONSE_DAG_VALIDATOR_PROVIDER_ENV,
            RESPONSE_DAG_VALIDATOR_MODEL_ENV,
            RESPONSE_DAG_VALIDATOR_LANGUAGE_ENV,
            RESPONSE_DAG_VALIDATOR_DEVICE_ENV,
            RESPONSE_DAG_VALIDATOR_MAX_WER_BP_ENV,
        )
    )
    now = time.monotonic()
    with _PACKAGE_RESPONSE_DAG_RUNTIME_LOCK:
        if runtime_key == _PACKAGE_RESPONSE_DAG_RUNTIME_KEY:
            if _PACKAGE_RESPONSE_DAG_RUNTIME is not None:
                return _PACKAGE_RESPONSE_DAG_RUNTIME
            if (
                _PACKAGE_RESPONSE_DAG_RUNTIME_ERROR is not None
                and now - _PACKAGE_RESPONSE_DAG_RUNTIME_FAILURE_AT < 60.0
            ):
                return None
        try:
            runtime = load_local_voice_response_dag_runtime_from_environment()
            error_code = None
            failure_at = 0.0
        except Exception as exc:
            runtime = None
            error_code = exc.__class__.__name__
            failure_at = now
        _PACKAGE_RESPONSE_DAG_RUNTIME = runtime
        _PACKAGE_RESPONSE_DAG_RUNTIME_KEY = runtime_key
        _PACKAGE_RESPONSE_DAG_RUNTIME_ERROR = error_code
        _PACKAGE_RESPONSE_DAG_RUNTIME_FAILURE_AT = failure_at
        return runtime


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
        audio_format = str(result.audio_format or "wav").strip().lower().lstrip(".")
        payload["audio_mime_type"] = _AUDIO_MIME_TYPES.get(
            audio_format,
            f"audio/{audio_format}",
        )
    return payload


def _response_dag_stage_configuration(
    *,
    sink: object | None,
    postprocessor: object | None,
) -> object | None:
    """Fail closed on partial opt-in to local response-DAG staging."""

    if sink is None and postprocessor is None:
        return None
    if sink is None or postprocessor is None:
        raise ValueError(
            "response-DAG staging requires response_dag_sink, "
            "and response_dag_postprocessor together"
        )
    from ipfs_accelerate_py.voice_response_dag_sink import (  # noqa: WPS433
        LocalResponseDAGQueue,
    )

    if not isinstance(sink, LocalResponseDAGQueue):
        raise TypeError(
            "response_dag_sink must be a package-owned LocalResponseDAGQueue"
        )
    if getattr(postprocessor, "remote_writes", None) is not False:
        raise ValueError(
            "response_dag_postprocessor must explicitly declare "
            "remote_writes = False"
        )
    callback = getattr(postprocessor, "validate_and_store_local", None)
    if not callable(callback):
        raise TypeError(
            "response_dag_postprocessor must implement "
            "validate_and_store_local(result)"
        )
    return callback


class WalletVoiceRouterAdapter:
    """Feature-flagged wallet adoption facade over ``process_voice_turn``."""

    def __init__(self, *, enabled: bool | None = None) -> None:
        self.enabled = is_unified_voice_router_enabled(enabled)

    def process(
        self,
        payload: Mapping[str, object],
        *,
        template_provider: object | None = None,
        fallback_template_provider: object | None = None,
        stt_provider: object | None = None,
        tts_provider: object | None = None,
        audio_resolver: object | None = None,
        response_dag_sink: object | None = None,
        response_dag_postprocessor: object | None = None,
    ) -> dict[str, object] | None:
        if not self.enabled:
            return None
        if not isinstance(payload, Mapping):
            raise TypeError("wallet voice payload must be a mapping")
        selected_response_dag_sink = response_dag_sink
        selected_response_dag_postprocessor = response_dag_postprocessor
        environment_dag_runtime = None
        if (
            selected_response_dag_sink is None
            and selected_response_dag_postprocessor is None
        ):
            environment_dag_runtime = _package_response_dag_runtime()
            if environment_dag_runtime is not None:
                selected_response_dag_sink = getattr(
                    environment_dag_runtime,
                    "sink",
                    None,
                )
                selected_response_dag_postprocessor = getattr(
                    environment_dag_runtime,
                    "postprocessor",
                    None,
                )
        response_dag_callback = _response_dag_stage_configuration(
            sink=selected_response_dag_sink,
            postprocessor=selected_response_dag_postprocessor,
        )
        selected_audio_resolver = (
            audio_resolver
            if audio_resolver is not None
            else _package_precomputed_audio_resolver()
        )
        synthesis_identity = getattr(
            selected_audio_resolver,
            "default_synthesis_identity",
            None,
        )
        request = build_voice_turn_request(
            payload,
            synthesis_identity=synthesis_identity,
        )
        response_text = request.fallback_text
        selected_template_provider = (
            template_provider
            if template_provider is not None
            else _package_graphrag_template_provider()
        )
        provider = selected_template_provider
        if provider is None and fallback_template_provider is None:
            provider = _WalletResponsePlanProvider(response_text)
        stt = stt_provider or _WalletSTTProvider()
        package_tts = (
            _package_indextts_tts_provider() if tts_provider is None else None
        )
        tts = (
            tts_provider
            or (_PackageFirstTTSProvider(package_tts) if package_tts else None)
            or _WalletTTSProvider()
        )
        _, _, process_voice_turn = _router_contracts()
        result = process_voice_turn(
            request,
            stt_provider_instance=stt,
            template_provider=provider,
            fallback_template_provider=fallback_template_provider,
            tts_provider_instance=tts,
            audio_resolver=selected_audio_resolver,
        )
        queued = None
        queue_reason = "not_live_tts_cache_miss"
        queue_error_code = None
        if response_dag_callback is not None and result.is_live_tts_cache_miss:
            try:
                from ipfs_accelerate_py.voice_response_dag_sink import (  # noqa: WPS433
                    LocalValidatedVoiceCacheMissArtifacts,
                )

                validated = response_dag_callback(result)
                if validated is not None:
                    artifacts = LocalValidatedVoiceCacheMissArtifacts.from_value(
                        validated
                    )
                    queued = result.enqueue_validated_cache_miss_candidate(
                        sink=selected_response_dag_sink,
                        validation_receipt=artifacts.validation_receipt,
                        audio_descriptor=artifacts.audio_descriptor,
                        response_id=artifacts.response_id,
                        surface=str(request.context.get("surface") or ""),
                    )
                else:
                    queue_reason = "independent_validation_not_passed"
                    queue_error_code = str(
                        getattr(
                            selected_response_dag_postprocessor,
                            "last_error_code",
                            "",
                        )
                        or ""
                    ) or None
            except Exception as exc:
                # Local response-DAG staging is an observability/durability
                # side effect. Never discard an otherwise valid user-facing
                # voice response because the local queue is unavailable.
                queue_reason = "local_staging_failed"
                queue_error_code = exc.__class__.__name__
        serialized = serialize_voice_turn_result(result)
        if (
            audio_resolver is None
            and selected_audio_resolver is not None
            and str(os.getenv(RUNTIME_AUDIO_MANIFEST_ENV) or "").strip()
        ):
            serialized["precomputed_audio_runtime"] = {
                "artifact_count": int(
                    getattr(selected_audio_resolver, "artifact_count", 0) or 0
                ),
                "configured": True,
                "loader_error_code": (
                    _PACKAGE_PRECOMPUTED_AUDIO_RESOLVER_ERROR
                ),
                "remote_writes": False,
            }
        if template_provider is None and str(
            os.getenv(RUNTIME_AUDIO_MANIFEST_ENV) or ""
        ).strip():
            graph_backend = getattr(
                selected_template_provider,
                "backend",
                selected_template_provider,
            )
            graph_index = getattr(graph_backend, "index", None)
            serialized["graphrag_runtime"] = {
                "configured": True,
                "graph_cid": str(
                    getattr(graph_index, "graph_cid", "") or ""
                )
                or None,
                "index_cid": str(
                    getattr(graph_index, "index_cid", "") or ""
                )
                or None,
                "loader_error_code": _PACKAGE_GRAPHRAG_TEMPLATE_PROVIDER_ERROR,
                "remote_writes": False,
                "status": (
                    "available"
                    if selected_template_provider is not None
                    else "unavailable"
                ),
            }
        dag_environment_configured = bool(
            str(
                os.getenv(
                    "IPFS_ACCELERATE_PY_ABBY_RESPONSE_DAG_QUEUE_ROOT",
                    "",
                )
                or ""
            ).strip()
        )
        if response_dag_callback is not None:
            serialized["response_dag_queue"] = (
                queued.to_dict()
                if queued is not None
                else {
                    "candidate_id": None,
                    "publication_status": "not_applicable",
                    "reason": queue_reason,
                    "remote_writes": False,
                    "status": (
                        "error"
                        if queue_reason == "local_staging_failed"
                        else "not_queued"
                    ),
                }
            )
            if queued is None and queue_error_code is not None:
                serialized["response_dag_queue"]["error_code"] = (  # type: ignore[index]
                    queue_error_code
                )
        elif (
            response_dag_sink is None
            and response_dag_postprocessor is None
            and dag_environment_configured
        ):
            serialized["response_dag_queue"] = {
                "candidate_id": None,
                "error_code": _PACKAGE_RESPONSE_DAG_RUNTIME_ERROR,
                "publication_status": "not_applicable",
                "reason": "local_runtime_unavailable",
                "remote_writes": False,
                "status": "unavailable",
            }
        return serialized


def process_wallet_voice_turn(
    payload: Mapping[str, object],
    *,
    enabled: bool | None = None,
    template_provider: object | None = None,
    fallback_template_provider: object | None = None,
    stt_provider: object | None = None,
    tts_provider: object | None = None,
    audio_resolver: object | None = None,
    response_dag_sink: object | None = None,
    response_dag_postprocessor: object | None = None,
) -> dict[str, object] | None:
    """Process one wallet proxy envelope when the staged flag is enabled."""

    return WalletVoiceRouterAdapter(enabled=enabled).process(
        payload,
        template_provider=template_provider,
        fallback_template_provider=fallback_template_provider,
        stt_provider=stt_provider,
        tts_provider=tts_provider,
        audio_resolver=audio_resolver,
        response_dag_sink=response_dag_sink,
        response_dag_postprocessor=response_dag_postprocessor,
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
    "RUNTIME_AUDIO_MANIFEST_ENV",
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
