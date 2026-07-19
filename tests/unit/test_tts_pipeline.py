"""Unit tests for _tts_pipeline.py — queue-fallback execution and per-space
TTS pipeline functions. Uses mocking so no optional deps are needed."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch


class TestIndexttsExecuteWithQueueFallback(unittest.TestCase):
    """Tests for _indextts_execute_with_queue_fallback."""

    def _call(self, timings=None, **patches):
        from wallet_interface.helpers._tts_pipeline import (
            _indextts_execute_with_queue_fallback,
        )

        with patch.multiple("wallet_interface.helpers._tts_pipeline", **patches):
            t = timings if timings is not None else {}
            return _indextts_execute_with_queue_fallback(
                fn_index=0, data=["text"], timings=t, api_name="/predict"
            ), t

    def test_queue_success_returns_result(self):
        result, timings = self._call(
            _indextts_queue_join=MagicMock(return_value="hash123"),
            _indextts_wait_for_result=MagicMock(return_value={"data": ["ref"]}),
        )
        self.assertEqual(result, {"data": ["ref"]})
        self.assertEqual(timings["result_path"], "queue")

    def test_timings_populated_on_success(self):
        _, timings = self._call(
            _indextts_queue_join=MagicMock(return_value="hash"),
            _indextts_wait_for_result=MagicMock(return_value={"data": []}),
        )
        self.assertIn("queue_join_ms", timings)
        self.assertIn("queue_wait_ms", timings)

    def test_fast_fail_mode_reraises_queue_error(self):
        from wallet_interface.helpers._tts_pipeline import (
            _indextts_execute_with_queue_fallback,
        )

        with patch("wallet_interface.helpers._tts_pipeline._indextts_queue_join", return_value="h"), \
             patch("wallet_interface.helpers._tts_pipeline._indextts_wait_for_result", side_effect=RuntimeError("queue fail")), \
             patch("wallet_interface.helpers._tts_pipeline._indextts_is_fast_fail_mode", return_value=True):
            with self.assertRaises(RuntimeError):
                _indextts_execute_with_queue_fallback(
                    fn_index=0, data=["t"], timings={}, api_name="/predict"
                )

    def test_direct_predict_fallback_succeeds(self):
        from wallet_interface.helpers._tts_pipeline import (
            _indextts_execute_with_queue_fallback,
        )

        mock_client = MagicMock()
        mock_client.call_api_name.side_effect = RuntimeError("api_name fail")
        mock_client.call_endpoint.return_value = ["ref"]

        with patch("wallet_interface.helpers._tts_pipeline._indextts_queue_join", return_value="h"), \
             patch("wallet_interface.helpers._tts_pipeline._indextts_wait_for_result", side_effect=RuntimeError("queue fail")), \
             patch("wallet_interface.helpers._tts_pipeline._indextts_is_fast_fail_mode", return_value=False), \
             patch("wallet_interface.helpers._tts_pipeline._indextts_degraded_fast_fail_enabled", return_value=False), \
             patch("wallet_interface.helpers._tts_pipeline._indextts_allow_direct_predict_fallback", return_value=True), \
             patch("wallet_interface.helpers._tts_pipeline._is_opaque_indextts_queue_failure", return_value=False), \
             patch("wallet_interface.helpers._tts_pipeline._indextts_space_client", return_value=mock_client), \
             patch("wallet_interface.helpers._tts_pipeline._indextts_timeout_seconds", return_value=30.0):
            t = {}
            result = _indextts_execute_with_queue_fallback(
                fn_index=0, data=["t"], timings=t, api_name="/predict"
            )
        self.assertEqual(result, {"data": ["ref"]})
        self.assertEqual(t["result_path"], "direct-predict-fallback")

    def test_queue_retry_on_opaque_failure(self):
        from wallet_interface.helpers._tts_pipeline import (
            _indextts_execute_with_queue_fallback,
        )

        call_count = {"n": 0}
        retry_results = [{"data": ["ref"]}]

        def wait_result(session_hash):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise RuntimeError("opaque queue failure")
            return retry_results[0]

        with patch("wallet_interface.helpers._tts_pipeline._indextts_queue_join", return_value="h"), \
             patch("wallet_interface.helpers._tts_pipeline._indextts_wait_for_result", side_effect=wait_result), \
             patch("wallet_interface.helpers._tts_pipeline._indextts_is_fast_fail_mode", return_value=False), \
             patch("wallet_interface.helpers._tts_pipeline._indextts_degraded_fast_fail_enabled", return_value=False), \
             patch("wallet_interface.helpers._tts_pipeline._indextts_allow_direct_predict_fallback", return_value=True), \
             patch("wallet_interface.helpers._tts_pipeline._is_opaque_indextts_queue_failure", return_value=True):
            t = {}
            result = _indextts_execute_with_queue_fallback(
                fn_index=0, data=["t"], timings=t, api_name="/predict"
            )
        self.assertEqual(result, {"data": ["ref"]})
        self.assertEqual(t["result_path"], "queue-retry")


class TestRunIndexttsGradioTtsForSpace(unittest.TestCase):
    """Tests for _run_indextts_gradio_tts_for_space."""

    def test_empty_text_raises_value_error(self):
        from wallet_interface.helpers._tts_pipeline import (
            _run_indextts_gradio_tts_for_space,
        )

        with self.assertRaises(ValueError, msg="text is required"):
            _run_indextts_gradio_tts_for_space(text="")

    def test_whitespace_only_text_raises(self):
        from wallet_interface.helpers._tts_pipeline import (
            _run_indextts_gradio_tts_for_space,
        )

        with self.assertRaises(ValueError):
            _run_indextts_gradio_tts_for_space(text="   ")


class TestRunIndexttsGradioTtsForSpaceHappyPath(unittest.TestCase):
    """Happy-path test for _run_indextts_gradio_tts_for_space using full mock chain."""

    def test_returns_audio_dict(self):
        from wallet_interface.helpers._tts_pipeline import (
            _run_indextts_gradio_tts_for_space,
        )

        # Minimal silent WAV bytes
        wav_bytes = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x00\x7d\x00\x00\x00\xfa\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00"

        mock_result = {"data": [{"orig_name": "out.wav", "path": "/tmp/out.wav"}]}
        mock_audio_ref = {"orig_name": "out.wav", "path": "/tmp/out.wav"}

        with patch("wallet_interface.helpers._tts_pipeline._indextts_config", return_value={"fn_index": 0}), \
             patch("wallet_interface.helpers._tts_pipeline._indextts_upload_reference_audio", return_value={}), \
             patch("wallet_interface.helpers._tts_pipeline._indextts_fn_index", return_value=0), \
             patch("wallet_interface.helpers._tts_pipeline._indextts_request_data", return_value=["text"]), \
             patch("wallet_interface.helpers._tts_pipeline._indextts_execute_with_queue_fallback", return_value=mock_result), \
             patch("wallet_interface.helpers._tts_pipeline._find_gradio_audio_reference", return_value=mock_audio_ref), \
             patch("wallet_interface.helpers._tts_pipeline._fetch_gradio_file", return_value=(wav_bytes, "audio/wav")), \
             patch("wallet_interface.helpers._tts_pipeline._indextts_model_name", return_value="indextts-v1"), \
             patch("wallet_interface.helpers._tts_pipeline._indextts_space_base_url", return_value="https://space.example"), \
             patch("wallet_interface.helpers._tts_pipeline._indextts_api_name", return_value="/predict"):
            result = _run_indextts_gradio_tts_for_space(text="Hello world")

        self.assertIn("audioBase64", result)
        self.assertEqual(result["mimeType"], "audio/wav")
        self.assertEqual(result["model"], "indextts-v1")
        self.assertIn("latency", result)


class TestRunIndexttsGradioTtsForSpaceNoAudioRef(unittest.TestCase):
    """Tests error path when no audio reference found."""

    def test_no_audio_ref_raises_value_error(self):
        from wallet_interface.helpers._tts_pipeline import (
            _run_indextts_gradio_tts_for_space,
        )

        with patch("wallet_interface.helpers._tts_pipeline._indextts_config", return_value={}), \
             patch("wallet_interface.helpers._tts_pipeline._indextts_upload_reference_audio", return_value={}), \
             patch("wallet_interface.helpers._tts_pipeline._indextts_fn_index", return_value=0), \
             patch("wallet_interface.helpers._tts_pipeline._indextts_request_data", return_value=[]), \
             patch("wallet_interface.helpers._tts_pipeline._indextts_execute_with_queue_fallback", return_value={"data": []}), \
             patch("wallet_interface.helpers._tts_pipeline._find_gradio_audio_reference", return_value=None), \
             patch("wallet_interface.helpers._tts_pipeline._indextts_batch_audio_references", return_value=[]), \
             patch("wallet_interface.helpers._tts_pipeline._indextts_api_name", return_value="/predict"):
            with self.assertRaises(ValueError):
                _run_indextts_gradio_tts_for_space(text="Hello world")


class TestRunIndexttsGradioTtsForSpaceBatchFallback(unittest.TestCase):
    """Tests that batch function falls back to sequential when batch fails and
    require_batch_mode is False."""

    def test_empty_texts_raises(self):
        from wallet_interface.helpers._tts_pipeline import (
            _run_indextts_gradio_batch_tts_for_space,
        )

        with self.assertRaises(ValueError):
            _run_indextts_gradio_batch_tts_for_space(texts=[])

    def test_whitespace_only_texts_raises(self):
        from wallet_interface.helpers._tts_pipeline import (
            _run_indextts_gradio_batch_tts_for_space,
        )

        with self.assertRaises(ValueError):
            _run_indextts_gradio_batch_tts_for_space(texts=["  ", ""])


if __name__ == "__main__":
    unittest.main()
