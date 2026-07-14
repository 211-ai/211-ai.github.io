# ruff: noqa: E501
"""IndexTTS / Whisper / voice-proxy stdlib-only configuration helpers.

All functions in this module are importable without any optional dependencies
(no ipfs_datasets_py, no ipfs_accelerate_py, no torch).  They cover:

  * env-based knobs (URLs, timeouts, feature flags)
  * threading.local override state (used by test context managers)
  * pure text helpers (_clean_voice_reply_text)
  * WAV byte generation (_silent_wav_bytes)
  * opaque error classification (_is_opaque_indextts_queue_failure)
"""

from __future__ import annotations

import io
import os
import re
import threading
import wave
from contextlib import contextmanager

# ---------------------------------------------------------------------------
# Thread-local override state
# ---------------------------------------------------------------------------

#: Per-thread active IndexTTS space URL override (used by context managers in tests).
_INDEXTTS_ACTIVE_SPACE_URL: threading.local = threading.local()

#: Per-thread active IndexTTS timeout override.
_INDEXTTS_ACTIVE_TIMEOUT_SECONDS: threading.local = threading.local()

#: Per-thread fast-fail mode flag.
_INDEXTTS_FAST_FAIL_MODE: threading.local = threading.local()

#: Per-thread force-require-batch mode flag.
_INDEXTTS_FORCE_REQUIRE_BATCH: threading.local = threading.local()


# ---------------------------------------------------------------------------
# URL / model / API-name config
# ---------------------------------------------------------------------------

def _indextts_space_base_url() -> str:
    override = str(getattr(_INDEXTTS_ACTIVE_SPACE_URL, "value", "") or "").strip().rstrip("/")
    if override:
        return override
    return os.getenv("WALLET_INDEXTTS_SPACE_URL", "https://publicus-indextts-2-demo.hf.space").strip().rstrip("/")


def _indextts_fallback_space_base_url() -> str:
    return os.getenv("WALLET_INDEXTTS_FALLBACK_SPACE_URL", "https://indexteam-indextts-2-demo.hf.space").strip().rstrip("/")


def _indextts_space_base_urls() -> list[str]:
    urls: list[str] = []
    for candidate in (_indextts_space_base_url(), _indextts_fallback_space_base_url()):
        normalized = str(candidate or "").strip().rstrip("/")
        if normalized and normalized not in urls:
            urls.append(normalized)
    return urls


def _indextts_model_name() -> str:
    primary_model = os.getenv("WALLET_INDEXTTS_MODEL_NAME", "Publicus/IndexTTS-2-Demo").strip()
    fallback_model = os.getenv("WALLET_INDEXTTS_FALLBACK_MODEL_NAME", "IndexTeam/IndexTTS-2-Demo").strip()
    active_space = _indextts_space_base_url().strip().rstrip("/")
    if active_space and active_space == _indextts_fallback_space_base_url():
        return fallback_model or primary_model
    return primary_model


def _indextts_api_name() -> str:
    return os.getenv("WALLET_INDEXTTS_API_NAME", "gen_single").strip()


def _indextts_batch_api_name() -> str:
    return os.getenv("WALLET_INDEXTTS_BATCH_API_NAME", "gen_batch").strip()


# ---------------------------------------------------------------------------
# Timeout / TTL config
# ---------------------------------------------------------------------------

def _indextts_timeout_seconds() -> float:
    override = getattr(_INDEXTTS_ACTIVE_TIMEOUT_SECONDS, "value", None)
    if override is not None:
        try:
            return max(5.0, float(override))
        except Exception:
            pass
    try:
        return max(5.0, float(os.getenv("WALLET_INDEXTTS_TIMEOUT_SECONDS", "180")))
    except Exception:
        return 180.0


def _indextts_cache_ttl_seconds() -> float:
    try:
        return max(0.0, float(os.getenv("WALLET_INDEXTTS_CACHE_TTL_SECONDS", "3600")))
    except Exception:
        return 3600.0


def _voice_llm_timeout_seconds() -> float:
    try:
        return max(5.0, float(os.getenv("WALLET_VOICE_LLM_TIMEOUT_SECONDS", "20")))
    except Exception:
        return 20.0


def _indextts_endpoint_timeout_seconds() -> float:
    try:
        return max(5.0, float(os.getenv("WALLET_INDEXTTS_ENDPOINT_TIMEOUT_SECONDS", "95")))
    except Exception:
        return 95.0


def _indextts_endpoint_retry_count() -> int:
    try:
        return max(0, min(2, int(os.getenv("WALLET_INDEXTTS_ENDPOINT_RETRIES", "1"))))
    except Exception:
        return 1


def _hf_whisper_timeout_seconds() -> float:
    try:
        return max(5.0, float(os.getenv("WALLET_HF_WHISPER_TIMEOUT_SECONDS", "45")))
    except Exception:
        return 45.0


# ---------------------------------------------------------------------------
# Feature-flag config
# ---------------------------------------------------------------------------

def _indextts_degraded_fast_fail_enabled() -> bool:
    value = str(os.getenv("WALLET_INDEXTTS_DEGRADED_FAST_FAIL", "true")).strip().lower()
    return value in {"1", "true", "yes", "on"}


def _indextts_allow_direct_predict_fallback() -> bool:
    value = str(os.getenv("WALLET_INDEXTTS_ALLOW_DIRECT_PREDICT_FALLBACK", "true")).strip().lower()
    return value in {"1", "true", "yes", "on"}


def _indextts_single_batch_fallback_enabled() -> bool:
    value = str(os.getenv("WALLET_INDEXTTS_SINGLE_BATCH_FALLBACK", "true")).strip().lower()
    return value in {"1", "true", "yes", "on"}


def _indextts_require_batch_mode() -> bool:
    if bool(getattr(_INDEXTTS_FORCE_REQUIRE_BATCH, "value", False)):
        return True
    return str(os.getenv("WALLET_INDEXTTS_REQUIRE_BATCH", "")).strip().lower() in {"1", "true", "yes"}


def _indextts_is_fast_fail_mode() -> bool:
    return bool(getattr(_INDEXTTS_FAST_FAIL_MODE, "value", False))


def _hf_whisper_model_name(model_name: str | None = None) -> str:
    return (model_name or os.getenv("WALLET_HF_WHISPER_MODEL_NAME") or "openai/whisper-large-v3-turbo").strip()


# ---------------------------------------------------------------------------
# Computed config
# ---------------------------------------------------------------------------

def _indextts_attempt_timeout_seconds(space_index: int, total_spaces: int) -> float:
    default_timeout = _indextts_timeout_seconds()
    if total_spaces > 1 and space_index == 0:
        return min(default_timeout, 20.0)
    if total_spaces > 1 and space_index == total_spaces - 1:
        return min(default_timeout, 45.0)
    return default_timeout


# ---------------------------------------------------------------------------
# Context managers (testing / overrides)
# ---------------------------------------------------------------------------

@contextmanager
def _indextts_use_space_base_url(base_url: str):
    previous = getattr(_INDEXTTS_ACTIVE_SPACE_URL, "value", None)
    _INDEXTTS_ACTIVE_SPACE_URL.value = str(base_url or "").strip().rstrip("/")
    try:
        yield
    finally:
        if previous is None:
            try:
                delattr(_INDEXTTS_ACTIVE_SPACE_URL, "value")
            except AttributeError:
                pass
        else:
            _INDEXTTS_ACTIVE_SPACE_URL.value = previous


@contextmanager
def _indextts_use_timeout_seconds(seconds: float | None):
    previous = getattr(_INDEXTTS_ACTIVE_TIMEOUT_SECONDS, "value", None)
    _INDEXTTS_ACTIVE_TIMEOUT_SECONDS.value = None if seconds is None else float(seconds)
    try:
        yield
    finally:
        if previous is None:
            try:
                delattr(_INDEXTTS_ACTIVE_TIMEOUT_SECONDS, "value")
            except AttributeError:
                pass
        else:
            _INDEXTTS_ACTIVE_TIMEOUT_SECONDS.value = previous


@contextmanager
def _indextts_fast_fail_mode(enabled: bool):
    previous = getattr(_INDEXTTS_FAST_FAIL_MODE, "value", False)
    _INDEXTTS_FAST_FAIL_MODE.value = bool(enabled)
    try:
        yield
    finally:
        _INDEXTTS_FAST_FAIL_MODE.value = previous


@contextmanager
def _indextts_force_require_batch(enabled: bool):
    previous = getattr(_INDEXTTS_FORCE_REQUIRE_BATCH, "value", False)
    _INDEXTTS_FORCE_REQUIRE_BATCH.value = bool(enabled)
    try:
        yield
    finally:
        _INDEXTTS_FORCE_REQUIRE_BATCH.value = previous


# ---------------------------------------------------------------------------
# Pure text / classification helpers
# ---------------------------------------------------------------------------

def _clean_voice_reply_text(text: str, *, prompt: str = "", fallback_text: str = "") -> str:
    cleaned = str(text or "").strip()
    prompt = str(prompt or "").strip()
    if prompt and cleaned.startswith(prompt):
        cleaned = cleaned[len(prompt):].strip()
    for marker in ("Assistant:", "Abby:", "Response:", "Answer:"):
        index = cleaned.rfind(marker)
        if index >= 0:
            cleaned = cleaned[index + len(marker):].strip()
            break
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        cleaned = str(fallback_text or "").strip()
    max_chars = 520
    if len(cleaned) > max_chars:
        trimmed = cleaned[:max_chars].rsplit(" ", 1)[0].strip()
        cleaned = trimmed or cleaned[:max_chars].strip()
    return cleaned


def _is_opaque_indextts_queue_failure(detail: str) -> bool:
    normalized = str(detail or "").lower()
    return "space queue failed" in normalized and (
        "error=null" in normalized or "{'error': none}" in normalized
    )


# ---------------------------------------------------------------------------
# Audio helpers
# ---------------------------------------------------------------------------

def _silent_wav_bytes(duration_ms: int = 240, sample_rate: int = 16_000) -> bytes:
    sample_count = max(1, int(sample_rate * duration_ms / 1000))
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(b"\x00\x00" * sample_count)
    return buffer.getvalue()
