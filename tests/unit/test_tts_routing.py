"""Unit tests for wallet_interface/helpers/_tts.py — multi-space routing.

Tests cover single-TTS routing, batch-TTS routing, and the single-with-batch-
fallback helper.  All external dependencies are mocked so no network access
or optional deps are required.
"""

from __future__ import annotations

import os
import unittest
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# _run_indextts_gradio_tts — multi-space routing
# ---------------------------------------------------------------------------


class TestRunIndexttsGradioTts(unittest.TestCase):
    """Tests for the multi-space single-TTS routing function."""

    _GOOD_RESULT = {
        "audioBase64": "AAEC",
        "mimeType": "audio/wav",
        "model": "indextts",
        "spaceUrl": "http://space1",
        "provider": "huggingface-zero-gpu-gradio",
        "billTo": "publicus",
        "referenceAudio": "",
        "text": "hello",
        "originalText": "hello",
        "latency": {},
    }

    def _call(self, space_urls, side_effects, **kwargs):
        from wallet_interface.helpers._tts import _run_indextts_gradio_tts

        with patch("wallet_interface.helpers._tts._indextts_space_base_urls", return_value=space_urls), \
             patch("wallet_interface.helpers._tts._run_indextts_gradio_tts_for_space", side_effect=side_effects), \
             patch("wallet_interface.helpers._tts._indextts_attempt_timeout_seconds", return_value=30.0), \
             patch("wallet_interface.helpers._tts._indextts_use_space_base_url") as mock_url_cm, \
             patch("wallet_interface.helpers._tts._indextts_use_timeout_seconds") as mock_timeout_cm, \
             patch("wallet_interface.helpers._tts._indextts_fast_fail_mode") as mock_ff_cm:
            # Make context managers work
            for cm in [mock_url_cm, mock_timeout_cm, mock_ff_cm]:
                cm.return_value.__enter__ = MagicMock(return_value=None)
                cm.return_value.__exit__ = MagicMock(return_value=False)
            return _run_indextts_gradio_tts(text="hello", **kwargs)

    def test_succeeds_on_first_space(self):
        result = self._call(
            ["http://space1"],
            [self._GOOD_RESULT],
        )
        self.assertEqual(result["audioBase64"], "AAEC")

    def test_falls_through_to_second_space_on_first_failure(self):
        result = self._call(
            ["http://space1", "http://space2"],
            [ValueError("space1 failed"), self._GOOD_RESULT],
        )
        self.assertEqual(result["audioBase64"], "AAEC")

    def test_raises_value_error_when_all_spaces_fail(self):
        from wallet_interface.helpers._tts import _run_indextts_gradio_tts

        with patch("wallet_interface.helpers._tts._indextts_space_base_urls", return_value=["http://s1", "http://s2"]), \
             patch("wallet_interface.helpers._tts._run_indextts_gradio_tts_for_space", side_effect=[ValueError("s1"), ValueError("s2")]), \
             patch("wallet_interface.helpers._tts._indextts_attempt_timeout_seconds", return_value=30.0), \
             patch("wallet_interface.helpers._tts._indextts_use_space_base_url") as mock_url_cm, \
             patch("wallet_interface.helpers._tts._indextts_use_timeout_seconds") as mock_timeout_cm, \
             patch("wallet_interface.helpers._tts._indextts_fast_fail_mode") as mock_ff_cm:
            for cm in [mock_url_cm, mock_timeout_cm, mock_ff_cm]:
                cm.return_value.__enter__ = MagicMock(return_value=None)
                cm.return_value.__exit__ = MagicMock(return_value=False)
            with self.assertRaises(ValueError) as ctx:
                _run_indextts_gradio_tts(text="hello")
        self.assertIn("IndexTTS failed across", str(ctx.exception))

    def test_raises_value_error_when_no_spaces_configured(self):
        from wallet_interface.helpers._tts import _run_indextts_gradio_tts

        with patch("wallet_interface.helpers._tts._indextts_space_base_urls", return_value=[]):
            with self.assertRaises(ValueError) as ctx:
                _run_indextts_gradio_tts(text="hello")
        self.assertIn("no configured spaces", str(ctx.exception))

    def test_error_message_contains_space_urls(self):
        from wallet_interface.helpers._tts import _run_indextts_gradio_tts

        with patch("wallet_interface.helpers._tts._indextts_space_base_urls", return_value=["http://myspace"]), \
             patch("wallet_interface.helpers._tts._run_indextts_gradio_tts_for_space", side_effect=ValueError("timeout")), \
             patch("wallet_interface.helpers._tts._indextts_attempt_timeout_seconds", return_value=30.0), \
             patch("wallet_interface.helpers._tts._indextts_use_space_base_url") as mock_url_cm, \
             patch("wallet_interface.helpers._tts._indextts_use_timeout_seconds") as mock_timeout_cm, \
             patch("wallet_interface.helpers._tts._indextts_fast_fail_mode") as mock_ff_cm:
            for cm in [mock_url_cm, mock_timeout_cm, mock_ff_cm]:
                cm.return_value.__enter__ = MagicMock(return_value=None)
                cm.return_value.__exit__ = MagicMock(return_value=False)
            with self.assertRaises(ValueError) as ctx:
                _run_indextts_gradio_tts(text="hello")
        self.assertIn("http://myspace", str(ctx.exception))


# ---------------------------------------------------------------------------
# _run_indextts_gradio_batch_tts — multi-space batch routing
# ---------------------------------------------------------------------------


class TestRunIndexttsGradioBatchTts(unittest.TestCase):
    """Tests for the multi-space batch-TTS routing function."""

    _GOOD_BATCH_RESULT = {
        "items": [
            {"audioBase64": "BATCH1", "mimeType": "audio/wav", "text": "line1"},
            {"audioBase64": "BATCH2", "mimeType": "audio/wav", "text": "line2"},
        ],
        "model": "indextts",
        "spaceUrl": "http://space1",
        "provider": "huggingface-zero-gpu-gradio",
        "billTo": "publicus",
        "latency": {},
    }

    def _call(self, space_urls, side_effects, **kwargs):
        from wallet_interface.helpers._tts import _run_indextts_gradio_batch_tts

        with patch("wallet_interface.helpers._tts._indextts_space_base_urls", return_value=space_urls), \
             patch("wallet_interface.helpers._tts._run_indextts_gradio_batch_tts_for_space", side_effect=side_effects), \
             patch("wallet_interface.helpers._tts._indextts_attempt_timeout_seconds", return_value=30.0), \
             patch("wallet_interface.helpers._tts._indextts_use_space_base_url") as mock_url_cm, \
             patch("wallet_interface.helpers._tts._indextts_use_timeout_seconds") as mock_timeout_cm, \
             patch("wallet_interface.helpers._tts._indextts_fast_fail_mode") as mock_ff_cm:
            for cm in [mock_url_cm, mock_timeout_cm, mock_ff_cm]:
                cm.return_value.__enter__ = MagicMock(return_value=None)
                cm.return_value.__exit__ = MagicMock(return_value=False)
            return _run_indextts_gradio_batch_tts(texts=["line1", "line2"], **kwargs)

    def test_succeeds_on_first_space(self):
        result = self._call(["http://space1"], [self._GOOD_BATCH_RESULT])
        self.assertEqual(len(result["items"]), 2)

    def test_falls_through_to_second_space_on_first_failure(self):
        result = self._call(
            ["http://space1", "http://space2"],
            [ValueError("s1 failed"), self._GOOD_BATCH_RESULT],
        )
        self.assertEqual(result["items"][0]["audioBase64"], "BATCH1")

    def test_raises_when_all_spaces_fail(self):
        from wallet_interface.helpers._tts import _run_indextts_gradio_batch_tts

        with patch("wallet_interface.helpers._tts._indextts_space_base_urls", return_value=["http://s1"]), \
             patch("wallet_interface.helpers._tts._run_indextts_gradio_batch_tts_for_space", side_effect=ValueError("fail")), \
             patch("wallet_interface.helpers._tts._indextts_attempt_timeout_seconds", return_value=30.0), \
             patch("wallet_interface.helpers._tts._indextts_use_space_base_url") as mock_url_cm, \
             patch("wallet_interface.helpers._tts._indextts_use_timeout_seconds") as mock_timeout_cm, \
             patch("wallet_interface.helpers._tts._indextts_fast_fail_mode") as mock_ff_cm:
            for cm in [mock_url_cm, mock_timeout_cm, mock_ff_cm]:
                cm.return_value.__enter__ = MagicMock(return_value=None)
                cm.return_value.__exit__ = MagicMock(return_value=False)
            with self.assertRaises(ValueError) as ctx:
                _run_indextts_gradio_batch_tts(texts=["t"])
        self.assertIn("batch failed across", str(ctx.exception))

    def test_raises_when_no_spaces(self):
        from wallet_interface.helpers._tts import _run_indextts_gradio_batch_tts

        with patch("wallet_interface.helpers._tts._indextts_space_base_urls", return_value=[]):
            with self.assertRaises(ValueError) as ctx:
                _run_indextts_gradio_batch_tts(texts=["t"])
        self.assertIn("no configured spaces", str(ctx.exception))


# ---------------------------------------------------------------------------
# _run_indextts_tts_with_batch_fallback
# ---------------------------------------------------------------------------


class TestRunIndexttsTtsWithBatchFallback(unittest.TestCase):
    """Tests for the single-with-batch-fallback helper."""

    _SINGLE_RESULT = {
        "audioBase64": "SINGLE",
        "mimeType": "audio/wav",
        "model": "indextts",
        "spaceUrl": "http://space1",
        "provider": "huggingface-zero-gpu-gradio",
        "billTo": "publicus",
        "referenceAudio": "",
        "text": "hello",
        "originalText": "hello",
        "latency": {},
    }
    _BATCH_RESULT = {
        "items": [{"audioBase64": "BATCH_FALLBACK", "mimeType": "audio/wav", "text": "hello", "originalText": ""}],
        "model": "indextts",
        "spaceUrl": "http://space1",
        "provider": "huggingface-zero-gpu-gradio",
        "billTo": "publicus",
        "latency": {"result_path": "batch"},
    }

    def test_returns_single_result_when_single_succeeds(self):
        from wallet_interface.helpers._tts import _run_indextts_tts_with_batch_fallback

        with patch("wallet_interface.helpers._tts._run_indextts_gradio_tts", return_value=self._SINGLE_RESULT):
            result = _run_indextts_tts_with_batch_fallback(text="hello")
        self.assertEqual(result["audioBase64"], "SINGLE")

    def test_falls_back_to_batch_when_single_fails(self):
        from wallet_interface.helpers._tts import _run_indextts_tts_with_batch_fallback

        with patch("wallet_interface.helpers._tts._run_indextts_gradio_tts", side_effect=ValueError("single failed")), \
             patch("wallet_interface.helpers._tts._indextts_single_batch_fallback_enabled", return_value=True), \
             patch("wallet_interface.helpers._tts._indextts_force_require_batch") as mock_force, \
             patch("wallet_interface.helpers._tts._run_indextts_gradio_batch_tts", return_value=self._BATCH_RESULT), \
             patch("wallet_interface.helpers._tts._indextts_model_name", return_value="indextts"), \
             patch("wallet_interface.helpers._tts._indextts_space_base_url", return_value="http://space1"):
            mock_force.return_value.__enter__ = MagicMock(return_value=None)
            mock_force.return_value.__exit__ = MagicMock(return_value=False)
            result = _run_indextts_tts_with_batch_fallback(text="hello")
        self.assertEqual(result["audioBase64"], "BATCH_FALLBACK")
        self.assertEqual(result["latency"]["result_path"], "single-batch-fallback")

    def test_raises_when_fallback_disabled(self):
        from wallet_interface.helpers._tts import _run_indextts_tts_with_batch_fallback

        with patch("wallet_interface.helpers._tts._run_indextts_gradio_tts", side_effect=ValueError("single failed")), \
             patch("wallet_interface.helpers._tts._indextts_single_batch_fallback_enabled", return_value=False):
            with self.assertRaises(ValueError):
                _run_indextts_tts_with_batch_fallback(text="hello")

    def test_raises_value_error_when_both_single_and_batch_fail(self):
        from wallet_interface.helpers._tts import _run_indextts_tts_with_batch_fallback

        with patch("wallet_interface.helpers._tts._run_indextts_gradio_tts", side_effect=ValueError("single failed")), \
             patch("wallet_interface.helpers._tts._indextts_single_batch_fallback_enabled", return_value=True), \
             patch("wallet_interface.helpers._tts._indextts_force_require_batch") as mock_force, \
             patch("wallet_interface.helpers._tts._run_indextts_gradio_batch_tts", side_effect=ValueError("batch failed")):
            mock_force.return_value.__enter__ = MagicMock(return_value=None)
            mock_force.return_value.__exit__ = MagicMock(return_value=False)
            with self.assertRaises(ValueError) as ctx:
                _run_indextts_tts_with_batch_fallback(text="hello")
        self.assertIn("batch fallback failed", str(ctx.exception))

    def test_raises_when_batch_returns_empty_items(self):
        from wallet_interface.helpers._tts import _run_indextts_tts_with_batch_fallback

        empty_batch = {"items": [], "model": "indextts", "spaceUrl": "http://s1", "provider": "hf", "billTo": "pub", "latency": {}}
        with patch("wallet_interface.helpers._tts._run_indextts_gradio_tts", side_effect=ValueError("single failed")), \
             patch("wallet_interface.helpers._tts._indextts_single_batch_fallback_enabled", return_value=True), \
             patch("wallet_interface.helpers._tts._indextts_force_require_batch") as mock_force, \
             patch("wallet_interface.helpers._tts._run_indextts_gradio_batch_tts", return_value=empty_batch):
            mock_force.return_value.__enter__ = MagicMock(return_value=None)
            mock_force.return_value.__exit__ = MagicMock(return_value=False)
            with self.assertRaises(ValueError) as ctx:
                _run_indextts_tts_with_batch_fallback(text="hello")
        self.assertIn("no items", str(ctx.exception))

    def test_raises_when_batch_item_has_no_audio(self):
        from wallet_interface.helpers._tts import _run_indextts_tts_with_batch_fallback

        no_audio_batch = {
            "items": [{"audioBase64": "", "mimeType": "audio/wav", "text": "hi", "originalText": ""}],
            "model": "indextts", "spaceUrl": "http://s1", "provider": "hf", "billTo": "pub", "latency": {},
        }
        with patch("wallet_interface.helpers._tts._run_indextts_gradio_tts", side_effect=ValueError("single failed")), \
             patch("wallet_interface.helpers._tts._indextts_single_batch_fallback_enabled", return_value=True), \
             patch("wallet_interface.helpers._tts._indextts_force_require_batch") as mock_force, \
             patch("wallet_interface.helpers._tts._run_indextts_gradio_batch_tts", return_value=no_audio_batch), \
             patch("wallet_interface.helpers._tts._indextts_model_name", return_value="indextts"), \
             patch("wallet_interface.helpers._tts._indextts_space_base_url", return_value="http://s1"):
            mock_force.return_value.__enter__ = MagicMock(return_value=None)
            mock_force.return_value.__exit__ = MagicMock(return_value=False)
            with self.assertRaises(ValueError) as ctx:
                _run_indextts_tts_with_batch_fallback(text="hi")
        self.assertIn("audioBase64", str(ctx.exception))

    def test_batch_fallback_result_includes_single_error_in_latency(self):
        from wallet_interface.helpers._tts import _run_indextts_tts_with_batch_fallback

        with patch("wallet_interface.helpers._tts._run_indextts_gradio_tts", side_effect=ValueError("specific error")), \
             patch("wallet_interface.helpers._tts._indextts_single_batch_fallback_enabled", return_value=True), \
             patch("wallet_interface.helpers._tts._indextts_force_require_batch") as mock_force, \
             patch("wallet_interface.helpers._tts._run_indextts_gradio_batch_tts", return_value=self._BATCH_RESULT), \
             patch("wallet_interface.helpers._tts._indextts_model_name", return_value="indextts"), \
             patch("wallet_interface.helpers._tts._indextts_space_base_url", return_value="http://space1"):
            mock_force.return_value.__enter__ = MagicMock(return_value=None)
            mock_force.return_value.__exit__ = MagicMock(return_value=False)
            result = _run_indextts_tts_with_batch_fallback(text="hello")
        self.assertIn("specific error", result["latency"]["single_error"])


if __name__ == "__main__":
    unittest.main()
