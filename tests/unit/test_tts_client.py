"""Unit tests for wallet_interface/helpers/_tts_client.py.

Tests cover client caching, fn-index resolution, config cache TTL,
upload reference audio (bytes, local path, remote path, default),
wait for result, batch audio reference parsing, and gradio file fetch.
All tests use mocking so ipfs_accelerate_py is not exercised over the network.
"""

from __future__ import annotations

import os
import threading
import unittest
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _reset_client_globals():
    """Reset module-level client singletons and caches between tests."""
    import wallet_interface.helpers._tts_client as mod

    mod._INDEXTTS_SPACE_CLIENT = None
    mod._INDEXTTS_SPACE_CLIENT_KEY = ""
    mod._INDEXTTS_CONFIG_CACHE.clear()
    mod._INDEXTTS_FN_INDEX_CACHE.clear()
    mod._INDEXTTS_REFERENCE_CACHE.clear()


# ---------------------------------------------------------------------------
# _indextts_space_client — singleton / cache-key refresh
# ---------------------------------------------------------------------------


class TestIndexttsSpaceClient(unittest.TestCase):
    def tearDown(self):
        _reset_client_globals()

    def _make_mock_client(self):
        mock = MagicMock()
        return mock

    def test_returns_client_instance(self):
        mock_cls = MagicMock(return_value=self._make_mock_client())
        with patch("wallet_interface.helpers._tts_client.HFSpaceClient", mock_cls):
            from wallet_interface.helpers._tts_client import _indextts_space_client
            client = _indextts_space_client()
        self.assertIsNotNone(client)
        mock_cls.assert_called_once()

    def test_returns_cached_client_on_second_call(self):
        mock_cls = MagicMock(return_value=self._make_mock_client())
        with patch("wallet_interface.helpers._tts_client.HFSpaceClient", mock_cls):
            from wallet_interface.helpers._tts_client import _indextts_space_client
            c1 = _indextts_space_client()
            c2 = _indextts_space_client()
        self.assertIs(c1, c2)
        self.assertEqual(mock_cls.call_count, 1)

    def test_creates_new_client_when_cache_key_changes(self):
        mock_cls = MagicMock(side_effect=[self._make_mock_client(), self._make_mock_client()])
        with patch("wallet_interface.helpers._tts_client.HFSpaceClient", mock_cls):
            with patch.dict(os.environ, {"WALLET_INDEXTTS_SPACE_BASE_URL": "http://space1"}):
                from wallet_interface.helpers._tts_client import _indextts_space_client
                _reset_client_globals()
                c1 = _indextts_space_client()
            _reset_client_globals()
            with patch.dict(os.environ, {"WALLET_INDEXTTS_SPACE_BASE_URL": "http://space2"}):
                c2 = _indextts_space_client()
        self.assertIsNot(c1, c2)

    def test_cached_hf_token_change_refreshes_client_without_storing_secret(self):
        mock_cls = MagicMock(side_effect=[self._make_mock_client(), self._make_mock_client()])
        with patch("wallet_interface.helpers._tts_client.HFSpaceClient", mock_cls), \
             patch(
                 "wallet_interface.helpers._tts_client._configured_hf_token",
                 side_effect=["cached-token-one", "cached-token-two"],
             ):
            from wallet_interface.helpers import _tts_client as module

            first = module._indextts_space_client()
            second = module._indextts_space_client()

        self.assertIsNot(first, second)
        self.assertEqual(mock_cls.call_count, 2)
        self.assertNotIn("cached-token-one", module._INDEXTTS_SPACE_CLIENT_KEY)
        self.assertNotIn("cached-token-two", module._INDEXTTS_SPACE_CLIENT_KEY)


# ---------------------------------------------------------------------------
# _indextts_config — TTL caching
# ---------------------------------------------------------------------------


class TestIndexttsConfig(unittest.TestCase):
    def tearDown(self):
        _reset_client_globals()

    def test_returns_dict_from_client(self):
        mock_client = MagicMock()
        mock_client.get_config.return_value = {"components": [], "version": "3.0"}
        with patch("wallet_interface.helpers._tts_client._indextts_space_client", return_value=mock_client):
            from wallet_interface.helpers._tts_client import _indextts_config
            config = _indextts_config()
        self.assertIn("components", config)

    def test_second_call_within_ttl_uses_cache(self):
        mock_client = MagicMock()
        mock_client.get_config.return_value = {"version": "1"}
        with patch("wallet_interface.helpers._tts_client._indextts_space_client", return_value=mock_client):
            from wallet_interface.helpers._tts_client import _indextts_config
            _indextts_config()
            _indextts_config()
        self.assertEqual(mock_client.get_config.call_count, 1)

    def test_expired_cache_triggers_fresh_fetch(self):
        mock_client = MagicMock()
        mock_client.get_config.return_value = {"version": "2"}
        with patch("wallet_interface.helpers._tts_client._indextts_space_client", return_value=mock_client), \
             patch("wallet_interface.helpers._tts_client._indextts_cache_ttl_seconds", return_value=0.0), \
             patch("wallet_interface.helpers._tts_client.time") as mock_time:
            mock_time.time.side_effect = [0.0, 100.0, 100.0, 200.0]
            from wallet_interface.helpers._tts_client import _indextts_config
            _reset_client_globals()
            _indextts_config()
            _indextts_config()
        self.assertGreaterEqual(mock_client.get_config.call_count, 1)


# ---------------------------------------------------------------------------
# _indextts_fn_index — env override, cache, resolution
# ---------------------------------------------------------------------------


class TestIndexttssFnIndex(unittest.TestCase):
    def tearDown(self):
        _reset_client_globals()
        os.environ.pop("WALLET_INDEXTTS_FN_INDEX", None)

    def test_env_override_returns_integer(self):
        with patch.dict(os.environ, {"WALLET_INDEXTTS_FN_INDEX": "7"}):
            from wallet_interface.helpers._tts_client import _indextts_fn_index
            result = _indextts_fn_index({})
        self.assertEqual(result, 7)

    def test_resolves_from_client(self):
        mock_client = MagicMock()
        mock_client.resolve_fn_index.return_value = 2
        os.environ.pop("WALLET_INDEXTTS_FN_INDEX", None)
        with patch("wallet_interface.helpers._tts_client._indextts_space_client", return_value=mock_client):
            from wallet_interface.helpers._tts_client import _indextts_fn_index
            result = _indextts_fn_index({"components": []})
        self.assertEqual(result, 2)

    def test_cache_hit_skips_resolution(self):
        mock_client = MagicMock()
        mock_client.resolve_fn_index.return_value = 3
        os.environ.pop("WALLET_INDEXTTS_FN_INDEX", None)
        with patch("wallet_interface.helpers._tts_client._indextts_space_client", return_value=mock_client):
            from wallet_interface.helpers._tts_client import _indextts_fn_index
            _indextts_fn_index({})
            _indextts_fn_index({})
        self.assertEqual(mock_client.resolve_fn_index.call_count, 1)

    def test_raises_value_error_on_resolution_failure(self):
        mock_client = MagicMock()
        mock_client.resolve_fn_index.side_effect = RuntimeError("not found")
        os.environ.pop("WALLET_INDEXTTS_FN_INDEX", None)
        with patch("wallet_interface.helpers._tts_client._indextts_space_client", return_value=mock_client):
            from wallet_interface.helpers._tts_client import _indextts_fn_index
            with self.assertRaises(ValueError):
                _indextts_fn_index({})


# ---------------------------------------------------------------------------
# _indextts_batch_fn_index
# ---------------------------------------------------------------------------


class TestIndexttsBatchFnIndex(unittest.TestCase):
    def tearDown(self):
        _reset_client_globals()
        os.environ.pop("WALLET_INDEXTTS_BATCH_FN_INDEX", None)
        os.environ.pop("WALLET_INDEXTTS_BATCH_API_NAME", None)

    def test_env_override_returns_integer(self):
        with patch.dict(os.environ, {"WALLET_INDEXTTS_BATCH_FN_INDEX": "5", "WALLET_INDEXTTS_BATCH_API_NAME": "/batch"}):
            from wallet_interface.helpers._tts_client import _indextts_batch_fn_index
            result = _indextts_batch_fn_index({})
        self.assertEqual(result, 5)

    def test_raises_when_api_name_empty(self):
        with patch.dict(os.environ, {"WALLET_INDEXTTS_BATCH_API_NAME": ""}):
            os.environ.pop("WALLET_INDEXTTS_BATCH_FN_INDEX", None)
            from wallet_interface.helpers._tts_client import _indextts_batch_fn_index
            with self.assertRaises(ValueError):
                _indextts_batch_fn_index({})

    def test_resolves_from_client(self):
        mock_client = MagicMock()
        mock_client.resolve_fn_index.return_value = 4
        os.environ.pop("WALLET_INDEXTTS_BATCH_FN_INDEX", None)
        with patch.dict(os.environ, {"WALLET_INDEXTTS_BATCH_API_NAME": "/batch_tts"}), \
             patch("wallet_interface.helpers._tts_client._indextts_space_client", return_value=mock_client):
            from wallet_interface.helpers._tts_client import _indextts_batch_fn_index
            result = _indextts_batch_fn_index({})
        self.assertEqual(result, 4)


# ---------------------------------------------------------------------------
# _indextts_queue_join
# ---------------------------------------------------------------------------


class TestIndexttsQueueJoin(unittest.TestCase):
    def tearDown(self):
        _reset_client_globals()

    def test_delegates_to_client(self):
        mock_client = MagicMock()
        mock_client.queue_join.return_value = "hash-abc"
        with patch("wallet_interface.helpers._tts_client._indextts_space_client", return_value=mock_client):
            from wallet_interface.helpers._tts_client import _indextts_queue_join
            result = _indextts_queue_join(fn_index=0, data=["text", "ref"])
        self.assertEqual(result, "hash-abc")
        mock_client.queue_join.assert_called_once_with(0, ["text", "ref"])


# ---------------------------------------------------------------------------
# _indextts_upload_reference_audio
# ---------------------------------------------------------------------------


class TestIndexttsUploadReferenceAudio(unittest.TestCase):
    def tearDown(self):
        _reset_client_globals()
        for key in [
            "WALLET_INDEXTTS_REFERENCE_AUDIO_PATH",
            "WALLET_INDEXTTS_REFERENCE_AUDIO_REMOTE_PATH",
        ]:
            os.environ.pop(key, None)

    def test_uploads_provided_bytes(self):
        mock_client = MagicMock()
        mock_client.upload_file.return_value = [{"path": "/tmp/uploaded.wav"}]
        with patch("wallet_interface.helpers._tts_client._indextts_space_client", return_value=mock_client), \
             patch("wallet_interface.helpers._tts_client._first_upload_path", return_value="/tmp/uploaded.wav"):
            from wallet_interface.helpers._tts_client import _indextts_upload_reference_audio
            result = _indextts_upload_reference_audio(b"\x00\x01", "voice.wav", "audio/wav")
        self.assertIsNotNone(result)
        self.assertEqual(result["path"], "/tmp/uploaded.wav")

    def test_upload_with_bytes_raises_on_missing_path(self):
        mock_client = MagicMock()
        mock_client.upload_file.return_value = []
        with patch("wallet_interface.helpers._tts_client._indextts_space_client", return_value=mock_client), \
             patch("wallet_interface.helpers._tts_client._first_upload_path", return_value=None):
            from wallet_interface.helpers._tts_client import _indextts_upload_reference_audio
            with self.assertRaises(RuntimeError):
                _indextts_upload_reference_audio(b"\x00", "voice.wav")

    def test_uses_remote_path_env(self):
        with patch.dict(os.environ, {
            "WALLET_INDEXTTS_REFERENCE_AUDIO_REMOTE_PATH": "/gradio/remote/ref.wav",
            "WALLET_INDEXTTS_REFERENCE_AUDIO_PATH": "",
        }):
            from wallet_interface.helpers._tts_client import _indextts_upload_reference_audio
            result = _indextts_upload_reference_audio(None, None)
        self.assertIsNotNone(result)
        self.assertEqual(result["path"], "/gradio/remote/ref.wav")

    def test_uploads_default_reference_when_no_audio_or_path(self):
        mock_client = MagicMock()
        mock_client.upload_file.return_value = [{"path": "/tmp/abby.wav"}]
        with patch.dict(os.environ, {
            "WALLET_INDEXTTS_REFERENCE_AUDIO_PATH": "",
            "WALLET_INDEXTTS_REFERENCE_AUDIO_REMOTE_PATH": "",
        }), \
             patch("wallet_interface.helpers._tts_client._indextts_space_client", return_value=mock_client), \
             patch("wallet_interface.helpers._tts_client._first_upload_path", return_value="/tmp/abby.wav"), \
             patch("wallet_interface.helpers._tts_client._default_indextts_reference_wav", return_value=b"\xff\xfe"):
            from wallet_interface.helpers._tts_client import _indextts_upload_reference_audio
            result = _indextts_upload_reference_audio(None, None)
        self.assertIsNotNone(result)
        self.assertIn("path", result)

    def test_default_reference_is_cached(self):
        mock_client = MagicMock()
        mock_client.upload_file.return_value = [{"path": "/tmp/abby.wav"}]
        with patch.dict(os.environ, {
            "WALLET_INDEXTTS_REFERENCE_AUDIO_PATH": "",
            "WALLET_INDEXTTS_REFERENCE_AUDIO_REMOTE_PATH": "",
        }), \
             patch("wallet_interface.helpers._tts_client._indextts_space_client", return_value=mock_client), \
             patch("wallet_interface.helpers._tts_client._first_upload_path", return_value="/tmp/abby.wav"), \
             patch("wallet_interface.helpers._tts_client._default_indextts_reference_wav", return_value=b"\xff\xfe"):
            from wallet_interface.helpers._tts_client import _indextts_upload_reference_audio
            _indextts_upload_reference_audio(None, None)
            _indextts_upload_reference_audio(None, None)
        self.assertEqual(mock_client.upload_file.call_count, 1)


# ---------------------------------------------------------------------------
# _indextts_wait_for_result
# ---------------------------------------------------------------------------


class TestIndexttsWaitForResult(unittest.TestCase):
    def tearDown(self):
        _reset_client_globals()

    def test_returns_result_on_success(self):
        mock_client = MagicMock()
        mock_client.wait_for_queue_result.return_value = {"data": ["audio"]}
        with patch("wallet_interface.helpers._tts_client._indextts_space_client", return_value=mock_client):
            from wallet_interface.helpers._tts_client import _indextts_wait_for_result
            result = _indextts_wait_for_result("hash-123")
        self.assertEqual(result["data"], ["audio"])

    def test_raises_value_error_on_queue_failure(self):
        mock_client = MagicMock()
        mock_client.wait_for_queue_result.side_effect = RuntimeError("timeout")
        with patch("wallet_interface.helpers._tts_client._indextts_space_client", return_value=mock_client), \
             patch("wallet_interface.helpers._tts_client._normalize_indextts_queue_failure", return_value="timeout detail"):
            from wallet_interface.helpers._tts_client import _indextts_wait_for_result
            with self.assertRaises(ValueError):
                _indextts_wait_for_result("hash-bad")


# ---------------------------------------------------------------------------
# _indextts_batch_audio_references
# ---------------------------------------------------------------------------


class TestIndexttsBatchAudioReferences(unittest.TestCase):
    def test_extracts_from_second_output_slot(self):
        result = {
            "data": [
                "ignored",
                [{"path": "/a.wav"}, {"path": "/b.wav"}],
            ]
        }
        with patch("wallet_interface.helpers._tts_client._gradio_output_values", return_value=result["data"]), \
             patch("wallet_interface.helpers._tts_client._find_gradio_audio_references", return_value=[{"path": "/a.wav"}, {"path": "/b.wav"}]), \
             patch("wallet_interface.helpers._tts_client._dedupe_gradio_references", side_effect=lambda x: x):
            from wallet_interface.helpers._tts_client import _indextts_batch_audio_references
            refs = _indextts_batch_audio_references(result)
        self.assertEqual(len(refs), 2)

    def test_returns_empty_list_on_empty_result(self):
        with patch("wallet_interface.helpers._tts_client._gradio_output_values", return_value=[]), \
             patch("wallet_interface.helpers._tts_client._find_gradio_audio_references", return_value=[]), \
             patch("wallet_interface.helpers._tts_client._dedupe_gradio_references", return_value=[]):
            from wallet_interface.helpers._tts_client import _indextts_batch_audio_references
            refs = _indextts_batch_audio_references({})
        self.assertEqual(refs, [])


# ---------------------------------------------------------------------------
# _fetch_gradio_file
# ---------------------------------------------------------------------------


class TestFetchGradioFile(unittest.TestCase):
    def tearDown(self):
        _reset_client_globals()

    def test_inline_bytes_returned_directly(self):
        reference = {"_inline_bytes": b"\xff\xfe\x00", "name": "audio.wav"}
        from wallet_interface.helpers._tts_client import _fetch_gradio_file
        data, mime = _fetch_gradio_file(reference)
        self.assertEqual(data, b"\xff\xfe\x00")
        # mimetypes.guess_type may return "audio/wav" or "audio/x-wav" depending on platform
        self.assertIn("wav", mime)

    def test_fetches_from_client_when_no_inline_bytes(self):
        mock_client = MagicMock()
        mock_client.fetch_file.return_value = (b"\x01\x02", "audio/wav")
        reference = {"path": "/tmp/file.wav"}
        with patch("wallet_interface.helpers._tts_client._indextts_space_client", return_value=mock_client):
            from wallet_interface.helpers._tts_client import _fetch_gradio_file
            data, mime = _fetch_gradio_file(reference)
        self.assertEqual(data, b"\x01\x02")
        self.assertIn("wav", mime)

    def test_mime_type_from_reference_overrides_detected(self):
        mock_client = MagicMock()
        mock_client.fetch_file.return_value = (b"\x00", "application/octet-stream")
        reference = {"path": "/tmp/file.wav", "mime_type": "audio/ogg"}
        with patch("wallet_interface.helpers._tts_client._indextts_space_client", return_value=mock_client):
            from wallet_interface.helpers._tts_client import _fetch_gradio_file
            _, mime = _fetch_gradio_file(reference)
        self.assertEqual(mime, "audio/ogg")


# ---------------------------------------------------------------------------
# Thread-safety: concurrent cache access
# ---------------------------------------------------------------------------


class TestConcurrentCacheAccess(unittest.TestCase):
    def tearDown(self):
        _reset_client_globals()

    def test_concurrent_config_cache_reads_stable(self):
        mock_client = MagicMock()
        mock_client.get_config.return_value = {"version": "1"}
        errors = []

        def read_config():
            try:
                with patch("wallet_interface.helpers._tts_client._indextts_space_client", return_value=mock_client):
                    from wallet_interface.helpers._tts_client import _indextts_config
                    _indextts_config()
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=read_config) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
