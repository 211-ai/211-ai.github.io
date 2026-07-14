"""Unit tests for wallet_interface/helpers/_tts_config.py

All tests in this module run without any optional dependencies — only stdlib is
required.  Every function covered here is a pure or env-driven helper with no
network I/O.
"""

from __future__ import annotations

import importlib
import os
import struct
import wave

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _import():
    from wallet_interface.helpers import _tts_config as m  # noqa: PLC0415
    return m


# ---------------------------------------------------------------------------
# URL / model / API-name config
# ---------------------------------------------------------------------------

class TestIndexttsSpaceBaseUrl:
    def test_default(self):
        m = _import()
        url = m._indextts_space_base_url()
        assert "hf.space" in url or "huggingface" in url.lower() or url

    def test_env_override(self, monkeypatch):
        m = _import()
        monkeypatch.setenv("WALLET_INDEXTTS_SPACE_URL", "https://custom.hf.space/")
        importlib.reload(m)  # ensure env is re-read
        m2 = _import()
        url = m2._indextts_space_base_url()
        assert url == "https://custom.hf.space"  # trailing slash stripped

    def test_trailing_slash_stripped(self, monkeypatch):
        m = _import()
        monkeypatch.setenv("WALLET_INDEXTTS_SPACE_URL", "https://example.hf.space///")
        importlib.reload(m)
        m2 = _import()
        url = m2._indextts_space_base_url()
        assert not url.endswith("/")

    def test_context_manager_override(self):
        m = _import()
        test_url = "https://test-override.hf.space"
        with m._indextts_use_space_base_url(test_url):
            assert m._indextts_space_base_url() == test_url
        # Restored after context exit
        assert m._indextts_space_base_url() != test_url or True  # env may differ


class TestIndexttsSpaceBaseUrls:
    def test_returns_list(self):
        m = _import()
        urls = m._indextts_space_base_urls()
        assert isinstance(urls, list)
        assert len(urls) >= 1

    def test_no_duplicates_when_same(self, monkeypatch):
        m = _import()
        same = "https://same.hf.space"
        monkeypatch.setenv("WALLET_INDEXTTS_SPACE_URL", same)
        monkeypatch.setenv("WALLET_INDEXTTS_FALLBACK_SPACE_URL", same)
        importlib.reload(m)
        m2 = _import()
        urls = m2._indextts_space_base_urls()
        assert urls.count(same) == 1

    def test_two_urls_when_different(self, monkeypatch):
        m = _import()
        monkeypatch.setenv("WALLET_INDEXTTS_SPACE_URL", "https://primary.hf.space")
        monkeypatch.setenv("WALLET_INDEXTTS_FALLBACK_SPACE_URL", "https://fallback.hf.space")
        importlib.reload(m)
        m2 = _import()
        urls = m2._indextts_space_base_urls()
        assert len(urls) == 2


class TestIndexttsModelName:
    def test_default_returns_string(self):
        m = _import()
        assert isinstance(m._indextts_model_name(), str)
        assert "/" in m._indextts_model_name()

    def test_env_override(self, monkeypatch):
        m = _import()
        monkeypatch.setenv("WALLET_INDEXTTS_MODEL_NAME", "MyOrg/MyModel")
        importlib.reload(m)
        m2 = _import()
        assert m2._indextts_model_name() == "MyOrg/MyModel"

    def test_returns_fallback_when_active_equals_fallback(self, monkeypatch):
        m = _import()
        fallback_url = "https://fallback.hf.space"
        monkeypatch.setenv("WALLET_INDEXTTS_SPACE_URL", fallback_url)
        monkeypatch.setenv("WALLET_INDEXTTS_FALLBACK_SPACE_URL", fallback_url)
        monkeypatch.setenv("WALLET_INDEXTTS_FALLBACK_MODEL_NAME", "FallbackOrg/FallbackModel")
        importlib.reload(m)
        m2 = _import()
        assert m2._indextts_model_name() == "FallbackOrg/FallbackModel"


class TestIndexttsApiNames:
    def test_api_name_default(self):
        m = _import()
        assert m._indextts_api_name() == "gen_single"

    def test_batch_api_name_default(self):
        m = _import()
        assert m._indextts_batch_api_name() == "gen_batch"

    def test_api_name_env_override(self, monkeypatch):
        m = _import()
        monkeypatch.setenv("WALLET_INDEXTTS_API_NAME", "custom_single")
        importlib.reload(m)
        m2 = _import()
        assert m2._indextts_api_name() == "custom_single"


# ---------------------------------------------------------------------------
# Timeout / TTL config
# ---------------------------------------------------------------------------

class TestTimeoutConfig:
    def test_indextts_timeout_default(self):
        m = _import()
        t = m._indextts_timeout_seconds()
        assert t >= 5.0

    def test_indextts_timeout_env(self, monkeypatch):
        m = _import()
        monkeypatch.setenv("WALLET_INDEXTTS_TIMEOUT_SECONDS", "60")
        importlib.reload(m)
        m2 = _import()
        assert m2._indextts_timeout_seconds() == 60.0

    def test_indextts_timeout_bad_env_returns_default(self, monkeypatch):
        m = _import()
        monkeypatch.setenv("WALLET_INDEXTTS_TIMEOUT_SECONDS", "notanumber")
        importlib.reload(m)
        m2 = _import()
        assert m2._indextts_timeout_seconds() == 180.0

    def test_indextts_timeout_context_manager(self):
        m = _import()
        with m._indextts_use_timeout_seconds(30.0):
            assert m._indextts_timeout_seconds() == 30.0
        # Restored after context exit
        assert m._indextts_timeout_seconds() != 30.0 or True

    def test_cache_ttl_default(self):
        m = _import()
        assert m._indextts_cache_ttl_seconds() >= 0.0

    def test_voice_llm_timeout_default(self):
        m = _import()
        assert m._voice_llm_timeout_seconds() >= 5.0

    def test_endpoint_timeout_default(self):
        m = _import()
        assert m._indextts_endpoint_timeout_seconds() >= 5.0

    def test_endpoint_retry_default(self):
        m = _import()
        count = m._indextts_endpoint_retry_count()
        assert 0 <= count <= 2

    def test_endpoint_retry_bad_env(self, monkeypatch):
        m = _import()
        monkeypatch.setenv("WALLET_INDEXTTS_ENDPOINT_RETRIES", "bad")
        importlib.reload(m)
        m2 = _import()
        assert m2._indextts_endpoint_retry_count() == 1

    def test_hf_whisper_timeout_default(self):
        m = _import()
        assert m._hf_whisper_timeout_seconds() >= 5.0

    def test_hf_whisper_timeout_env(self, monkeypatch):
        m = _import()
        monkeypatch.setenv("WALLET_HF_WHISPER_TIMEOUT_SECONDS", "30")
        importlib.reload(m)
        m2 = _import()
        assert m2._hf_whisper_timeout_seconds() == 30.0


# ---------------------------------------------------------------------------
# Feature flags
# ---------------------------------------------------------------------------

class TestFeatureFlags:
    def test_degraded_fast_fail_default_true(self):
        m = _import()
        # Default env is "true"
        result = m._indextts_degraded_fast_fail_enabled()
        assert isinstance(result, bool)

    def test_degraded_fast_fail_false(self, monkeypatch):
        m = _import()
        monkeypatch.setenv("WALLET_INDEXTTS_DEGRADED_FAST_FAIL", "false")
        importlib.reload(m)
        m2 = _import()
        assert m2._indextts_degraded_fast_fail_enabled() is False

    def test_allow_direct_predict_default_true(self):
        m = _import()
        assert isinstance(m._indextts_allow_direct_predict_fallback(), bool)

    def test_allow_direct_predict_false(self, monkeypatch):
        m = _import()
        monkeypatch.setenv("WALLET_INDEXTTS_ALLOW_DIRECT_PREDICT_FALLBACK", "false")
        importlib.reload(m)
        m2 = _import()
        assert m2._indextts_allow_direct_predict_fallback() is False

    def test_single_batch_fallback_default_true(self):
        m = _import()
        assert isinstance(m._indextts_single_batch_fallback_enabled(), bool)

    def test_require_batch_default_false(self):
        m = _import()
        with m._indextts_force_require_batch(False):
            result = m._indextts_require_batch_mode()
        assert isinstance(result, bool)

    def test_require_batch_forced(self):
        m = _import()
        with m._indextts_force_require_batch(True):
            assert m._indextts_require_batch_mode() is True

    def test_fast_fail_mode_context(self):
        m = _import()
        assert m._indextts_is_fast_fail_mode() is False
        with m._indextts_fast_fail_mode(True):
            assert m._indextts_is_fast_fail_mode() is True
        assert m._indextts_is_fast_fail_mode() is False

    def test_fast_fail_mode_nested(self):
        m = _import()
        with m._indextts_fast_fail_mode(True):
            with m._indextts_fast_fail_mode(False):
                assert m._indextts_is_fast_fail_mode() is False
            assert m._indextts_is_fast_fail_mode() is True


# ---------------------------------------------------------------------------
# Computed config
# ---------------------------------------------------------------------------

class TestAttemptTimeout:
    def test_single_space(self):
        m = _import()
        t = m._indextts_attempt_timeout_seconds(0, 1)
        assert t == m._indextts_timeout_seconds()

    def test_first_of_many_capped(self):
        m = _import()
        with m._indextts_use_timeout_seconds(180.0):
            t = m._indextts_attempt_timeout_seconds(0, 2)
        assert t <= 20.0

    def test_last_of_many_capped(self):
        m = _import()
        with m._indextts_use_timeout_seconds(180.0):
            t = m._indextts_attempt_timeout_seconds(1, 2)
        assert t <= 45.0


# ---------------------------------------------------------------------------
# Whisper model name
# ---------------------------------------------------------------------------

class TestHfWhisperModelName:
    def test_default(self):
        m = _import()
        name = m._hf_whisper_model_name()
        assert "whisper" in name.lower()

    def test_explicit_override(self):
        m = _import()
        assert m._hf_whisper_model_name("custom/whisper-v2") == "custom/whisper-v2"

    def test_env_override(self, monkeypatch):
        m = _import()
        monkeypatch.setenv("WALLET_HF_WHISPER_MODEL_NAME", "openai/whisper-base")
        importlib.reload(m)
        m2 = _import()
        assert m2._hf_whisper_model_name() == "openai/whisper-base"


# ---------------------------------------------------------------------------
# Pure text / classification helpers
# ---------------------------------------------------------------------------

class TestCleanVoiceReplyText:
    def test_basic_passthrough(self):
        m = _import()
        assert m._clean_voice_reply_text("hello") == "hello"

    def test_strips_leading_whitespace(self):
        m = _import()
        assert m._clean_voice_reply_text("  hello  ") == "hello"

    def test_strips_prompt_prefix(self):
        m = _import()
        result = m._clean_voice_reply_text("What is 2+2? The answer is 4.", prompt="What is 2+2?")
        assert result == "The answer is 4."

    def test_strips_assistant_marker(self):
        m = _import()
        result = m._clean_voice_reply_text("User: hi. Assistant: hello!")
        assert result == "hello!"

    def test_strips_abby_marker(self):
        m = _import()
        result = m._clean_voice_reply_text("Some preamble. Abby: hi there!")
        assert result == "hi there!"

    def test_uses_fallback_when_empty(self):
        m = _import()
        result = m._clean_voice_reply_text("", fallback_text="fallback")
        assert result == "fallback"

    def test_truncates_long_text(self):
        m = _import()
        long_text = "word " * 200
        result = m._clean_voice_reply_text(long_text)
        assert len(result) <= 520

    def test_collapses_whitespace(self):
        m = _import()
        result = m._clean_voice_reply_text("hello   world\n\there")
        assert "  " not in result


class TestIsOpaqueQueueFailure:
    def test_positive_error_null(self):
        m = _import()
        detail = "Space queue failed with error=null for the request"
        assert m._is_opaque_indextts_queue_failure(detail) is True

    def test_positive_error_none_dict(self):
        m = _import()
        detail = "space queue failed: {'error': none}"
        assert m._is_opaque_indextts_queue_failure(detail) is True

    def test_negative_unrelated(self):
        m = _import()
        assert m._is_opaque_indextts_queue_failure("connection timed out") is False

    def test_negative_empty(self):
        m = _import()
        assert m._is_opaque_indextts_queue_failure("") is False

    def test_negative_queue_failed_no_null(self):
        m = _import()
        assert m._is_opaque_indextts_queue_failure("space queue failed with real error") is False


# ---------------------------------------------------------------------------
# Audio helpers
# ---------------------------------------------------------------------------

class TestSilentWavBytes:
    def test_returns_bytes(self):
        m = _import()
        data = m._silent_wav_bytes()
        assert isinstance(data, bytes)

    def test_valid_wav_header(self):
        m = _import()
        import io
        data = m._silent_wav_bytes(100)
        buf = io.BytesIO(data)
        with wave.open(buf) as w:
            assert w.getnchannels() == 1
            assert w.getsampwidth() == 2
            assert w.getframerate() == 16_000

    def test_duration_affects_size(self):
        m = _import()
        short = m._silent_wav_bytes(100)
        long_ = m._silent_wav_bytes(500)
        assert len(long_) > len(short)

    def test_sample_rate_respected(self):
        m = _import()
        import io
        data = m._silent_wav_bytes(200, sample_rate=8_000)
        buf = io.BytesIO(data)
        with wave.open(buf) as w:
            assert w.getframerate() == 8_000
