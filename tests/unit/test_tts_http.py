"""Unit tests for wallet_interface/helpers/_tts_http.py.

Tests cover the credential helpers, runtime-warning aggregation,
voice-reply text generation (non-LLM path), and HTTP response validation
logic — all without network access or optional dependencies.
"""

from __future__ import annotations

import os
import unittest
from unittest.mock import MagicMock, patch


def _import_tts_http():
    try:
        from wallet_interface.helpers._tts_http import (
            _configured_hf_token,
            _generate_indextts_voice_reply_text,
            _indextts_headers,
            _publicus_indextts_credential_warning,
            _voice_proxy_runtime_warnings,
        )
        return (
            _configured_hf_token,
            _generate_indextts_voice_reply_text,
            _indextts_headers,
            _publicus_indextts_credential_warning,
            _voice_proxy_runtime_warnings,
        )
    except ImportError:  # pragma: no cover
        import pytest
        pytest.skip("wallet_interface.helpers._tts_http not importable")


# ---------------------------------------------------------------------------
# _configured_hf_token
# ---------------------------------------------------------------------------


class TestConfiguredHfToken:
    def test_returns_empty_when_no_env(self):
        (fn, *_) = _import_tts_http()
        env_keys = [
            "WALLET_INDEXTTS_HF_TOKEN", "HF_TOKEN", "HUGGINGFACEHUB_API_TOKEN",
            "IPFS_DATASETS_PY_HF_API_TOKEN", "HUGGINGFACE_API_TOKEN", "HUGGINGFACE_HUB_TOKEN",
        ]
        with patch.dict(os.environ, {k: "" for k in env_keys}):
            with patch("wallet_interface.helpers._tts_http.resolve_secret", return_value=None):
                result = fn()
        assert result == ""

    def test_returns_token_from_env(self):
        (fn, *_) = _import_tts_http()
        with patch("wallet_interface.helpers._tts_http.resolve_secret", return_value="test-token-abc"):
            result = fn()
        assert result == "test-token-abc"

    def test_strips_whitespace(self):
        (fn, *_) = _import_tts_http()
        with patch("wallet_interface.helpers._tts_http.resolve_secret", return_value="  tok  "):
            result = fn()
        assert result == "tok"

    def test_returns_empty_string_for_none(self):
        (fn, *_) = _import_tts_http()
        with patch("wallet_interface.helpers._tts_http.resolve_secret", return_value=None):
            result = fn()
        assert result == ""

    def test_falls_back_to_hf_token_env_when_no_secrets(self):
        (fn, *_) = _import_tts_http()
        # When resolve_secret is None (dep unavailable), falls back to os.getenv
        with patch("wallet_interface.helpers._tts_http.resolve_secret", None):
            with patch.dict(os.environ, {"HF_TOKEN": "fallback-token"}):
                result = fn()
        assert result == "fallback-token"


# ---------------------------------------------------------------------------
# _indextts_headers
# ---------------------------------------------------------------------------


class TestIndexttsHeaders:
    def test_default_accept_header(self):
        (_, _, fn, *_) = _import_tts_http()
        with patch("wallet_interface.helpers._tts_http._configured_hf_token", return_value=""):
            with patch.dict(os.environ, {"WALLET_INDEXTTS_HF_BILL_TO": "", "IPFS_DATASETS_PY_HF_BILL_TO": ""}):
                headers = fn()
        assert headers.get("Accept") == "application/json"

    def test_custom_accept_header(self):
        (_, _, fn, *_) = _import_tts_http()
        with patch("wallet_interface.helpers._tts_http._configured_hf_token", return_value=""):
            with patch.dict(os.environ, {"WALLET_INDEXTTS_HF_BILL_TO": "", "IPFS_DATASETS_PY_HF_BILL_TO": ""}):
                headers = fn(accept="audio/wav")
        assert headers.get("Accept") == "audio/wav"

    def test_no_auth_header_when_no_token(self):
        (_, _, fn, *_) = _import_tts_http()
        with patch("wallet_interface.helpers._tts_http._configured_hf_token", return_value=""):
            headers = fn()
        assert "Authorization" not in headers

    def test_auth_header_present_when_token_set(self):
        (_, _, fn, *_) = _import_tts_http()
        with patch("wallet_interface.helpers._tts_http._configured_hf_token", return_value="my-token"):
            headers = fn()
        assert "Authorization" in headers
        assert "my-token" in headers["Authorization"]

    def test_bill_to_header_from_env(self):
        (_, _, fn, *_) = _import_tts_http()
        with patch("wallet_interface.helpers._tts_http._configured_hf_token", return_value=""):
            with patch.dict(os.environ, {"WALLET_INDEXTTS_HF_BILL_TO": "myorg"}):
                headers = fn()
        assert headers.get("X-HF-Bill-To") == "myorg"

    def test_bill_to_defaults_to_publicus(self):
        (_, _, fn, *_) = _import_tts_http()
        with patch("wallet_interface.helpers._tts_http._configured_hf_token", return_value=""):
            with patch.dict(os.environ, {"WALLET_INDEXTTS_HF_BILL_TO": "", "IPFS_DATASETS_PY_HF_BILL_TO": ""}):
                headers = fn()
        assert headers.get("X-HF-Bill-To") == "publicus"

    def test_bill_to_fallback_env(self):
        (_, _, fn, *_) = _import_tts_http()
        with patch("wallet_interface.helpers._tts_http._configured_hf_token", return_value=""):
            with patch.dict(os.environ, {
                "WALLET_INDEXTTS_HF_BILL_TO": "",
                "IPFS_DATASETS_PY_HF_BILL_TO": "fallback-org",
            }):
                headers = fn()
        assert headers.get("X-HF-Bill-To") == "fallback-org"


# ---------------------------------------------------------------------------
# _publicus_indextts_credential_warning
# ---------------------------------------------------------------------------


class TestPublicusIndexttsCredentialWarning:
    def _patch_space_url(self, url: str):
        return patch("wallet_interface.helpers._tts_http._indextts_space_base_url", return_value=url)

    def test_returns_none_for_non_publicus_space(self):
        (_, _, _, fn, _) = _import_tts_http()
        with self._patch_space_url("https://someother-space.hf.space"):
            result = fn()
        assert result is None

    def test_returns_none_when_token_present(self):
        (_, _, _, fn, _) = _import_tts_http()
        with self._patch_space_url("https://publicus-indextts.hf.space"):
            with patch("wallet_interface.helpers._tts_http._configured_hf_token", return_value="tok"):
                result = fn()
        assert result is None

    def test_returns_warning_for_publicus_without_token(self):
        (_, _, _, fn, _) = _import_tts_http()
        with self._patch_space_url("https://publicus-indextts.hf.space"):
            with patch("wallet_interface.helpers._tts_http._configured_hf_token", return_value=""):
                with patch.dict(os.environ, {
                    "WALLET_INDEXTTS_HF_BILL_TO": "",
                    "IPFS_DATASETS_PY_HF_BILL_TO": "",
                    "WALLET_INDEXTTS_MODEL_NAME": "",
                }):
                    result = fn()
        assert result is not None
        assert result["code"] == "publicus_indextts_missing_hf_token"
        assert "WALLET_INDEXTTS_HF_TOKEN" in result["envVars"]

    def test_warning_includes_space_url(self):
        (_, _, _, fn, _) = _import_tts_http()
        with self._patch_space_url("https://publicus-indextts.hf.space"):
            with patch("wallet_interface.helpers._tts_http._configured_hf_token", return_value=""):
                with patch.dict(os.environ, {
                    "WALLET_INDEXTTS_HF_BILL_TO": "",
                    "IPFS_DATASETS_PY_HF_BILL_TO": "",
                    "WALLET_INDEXTTS_MODEL_NAME": "",
                }):
                    result = fn()
        assert result is not None
        assert result["spaceUrl"] == "https://publicus-indextts.hf.space"

    def test_matches_by_model_name_env(self):
        (_, _, _, fn, _) = _import_tts_http()
        with self._patch_space_url("https://some-other.hf.space"):
            with patch("wallet_interface.helpers._tts_http._configured_hf_token", return_value=""):
                with patch.dict(os.environ, {
                    "WALLET_INDEXTTS_MODEL_NAME": "Publicus/IndexTTS-2-Demo",
                    "WALLET_INDEXTTS_HF_BILL_TO": "",
                    "IPFS_DATASETS_PY_HF_BILL_TO": "",
                }):
                    result = fn()
        assert result is not None

    def test_bill_to_defaults_to_publicus_in_warning(self):
        (_, _, _, fn, _) = _import_tts_http()
        with self._patch_space_url("https://publicus-indextts.hf.space"):
            with patch("wallet_interface.helpers._tts_http._configured_hf_token", return_value=""):
                with patch.dict(os.environ, {
                    "WALLET_INDEXTTS_HF_BILL_TO": "",
                    "IPFS_DATASETS_PY_HF_BILL_TO": "",
                    "WALLET_INDEXTTS_MODEL_NAME": "",
                }):
                    result = fn()
        assert result is not None
        assert result["billTo"] == "publicus"


# ---------------------------------------------------------------------------
# _voice_proxy_runtime_warnings
# ---------------------------------------------------------------------------


class TestVoiceProxyRuntimeWarnings:
    def test_empty_list_when_no_warnings(self):
        (*_, fn) = _import_tts_http()
        with patch("wallet_interface.helpers._tts_http._publicus_indextts_credential_warning", return_value=None):
            result = fn()
        assert result == []

    def test_includes_publicus_warning_when_present(self):
        (*_, fn) = _import_tts_http()
        warning = {"code": "publicus_indextts_missing_hf_token", "message": "test"}
        with patch("wallet_interface.helpers._tts_http._publicus_indextts_credential_warning", return_value=warning):
            result = fn()
        assert len(result) == 1
        assert result[0]["code"] == "publicus_indextts_missing_hf_token"

    def test_returns_list_type(self):
        (*_, fn) = _import_tts_http()
        with patch("wallet_interface.helpers._tts_http._publicus_indextts_credential_warning", return_value=None):
            result = fn()
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# _generate_indextts_voice_reply_text (non-LLM path)
# ---------------------------------------------------------------------------


class TestGenerateIndexttsVoiceReplyText:
    def _fn(self):
        (_, fn, *_) = _import_tts_http()
        return fn

    def test_passthrough_mode_returns_text(self):
        fn = self._fn()
        text, timings = fn(mode="read-aloud", text="Hello world", system_prompt=None, user_prompt=None, fallback_text=None)
        assert text == "Hello world"
        assert isinstance(timings, dict)

    def test_passthrough_uses_fallback_when_text_empty(self):
        fn = self._fn()
        text, _ = fn(mode="read-aloud", text="", system_prompt=None, user_prompt=None, fallback_text="Fallback text")
        assert text == "Fallback text"

    def test_passthrough_raises_when_both_empty(self):
        fn = self._fn()
        import pytest
        with pytest.raises(ValueError, match="text is required"):
            fn(mode="summary", text="", system_prompt=None, user_prompt=None, fallback_text=None)

    def test_passthrough_mode_case_insensitive(self):
        fn = self._fn()
        text, _ = fn(mode="READ-ALOUD", text="hi", system_prompt=None, user_prompt=None, fallback_text=None)
        assert text == "hi"

    def test_passthrough_strips_text(self):
        fn = self._fn()
        text, _ = fn(mode="tts", text="  padded  ", system_prompt=None, user_prompt=None, fallback_text=None)
        assert text == "padded"

    def test_voice_reply_mode_uses_fallback_on_llm_error(self):
        fn = self._fn()
        with patch("wallet_interface.helpers._tts_http._prepare_hf_router_environment", side_effect=ImportError("no llm")):
            text, timings = fn(
                mode="voice-reply",
                text="Hello",
                system_prompt=None,
                user_prompt=None,
                fallback_text="Sorry, unavailable",
            )
        assert text == "Sorry, unavailable"
        assert "llm_error" in timings

    def test_voice_reply_mode_raises_when_no_fallback_and_llm_fails(self):
        fn = self._fn()
        import pytest
        with patch("wallet_interface.helpers._tts_http._prepare_hf_router_environment", side_effect=RuntimeError("LLM down")):
            with pytest.raises(RuntimeError):
                fn(
                    mode="voice-reply",
                    text="Hello",
                    system_prompt=None,
                    user_prompt=None,
                    fallback_text=None,
                )

    def test_voice_reply_builds_prompt_from_user_prompt(self):
        fn = self._fn()
        # When text is empty but user_prompt is set, it should build a prompt
        # and attempt LLM (which will fail, then use fallback)
        with patch("wallet_interface.helpers._tts_http._prepare_hf_router_environment", side_effect=RuntimeError("fail")):
            text, timings = fn(
                mode="voice-reply",
                text="",
                system_prompt=None,
                user_prompt="What services are available?",
                fallback_text="Check back later",
            )
        assert text == "Check back later"

    def test_voice_reply_raises_when_both_text_and_prompt_empty(self):
        fn = self._fn()
        import pytest
        with pytest.raises(ValueError, match="text or user_prompt is required"):
            fn(mode="voice-reply", text="", system_prompt=None, user_prompt="", fallback_text=None)

    def test_timings_dict_returned(self):
        fn = self._fn()
        _, timings = fn(mode="echo", text="x", system_prompt=None, user_prompt=None, fallback_text=None)
        assert isinstance(timings, dict)

    def test_none_mode_treated_as_non_voice_reply(self):
        fn = self._fn()
        # None/empty mode should NOT be treated as voice-reply
        text, _ = fn(mode=None, text="hello", system_prompt=None, user_prompt=None, fallback_text=None)
        assert text == "hello"

    def test_llm_timings_recorded_on_error(self):
        fn = self._fn()
        with patch("wallet_interface.helpers._tts_http._prepare_hf_router_environment", side_effect=RuntimeError("fail")):
            _, timings = fn(
                mode="voice-reply",
                text="Hello",
                system_prompt=None,
                user_prompt=None,
                fallback_text="fb",
            )
        assert "llm_request_ms" in timings
        assert timings["llm_request_ms"] >= 0
