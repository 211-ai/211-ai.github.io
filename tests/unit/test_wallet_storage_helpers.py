"""Unit tests for wallet_interface/helpers/_storage.py pure helpers.

Tests cover functions that do not require ipfs_datasets_py or network access.
The IPFS-backend-dependent functions are tested with the mock backend mode.
"""
from __future__ import annotations

import hashlib
import os
import unittest


class TestMockIpfsCidForBytes(unittest.TestCase):
    def setUp(self):
        from wallet_interface.helpers._storage import _mock_ipfs_cid_for_bytes

        self._fn = _mock_ipfs_cid_for_bytes

    def test_returns_string(self):
        result = self._fn(b"hello")
        self.assertIsInstance(result, str)

    def test_starts_with_bafybeimock(self):
        result = self._fn(b"hello")
        self.assertTrue(result.startswith("bafybeimock"))

    def test_deterministic(self):
        self.assertEqual(self._fn(b"data"), self._fn(b"data"))

    def test_different_inputs_produce_different_cids(self):
        self.assertNotEqual(self._fn(b"aaa"), self._fn(b"bbb"))

    def test_cid_includes_sha256_hex(self):
        data = b"test-bytes"
        expected_hex = hashlib.sha256(data).hexdigest()[:24]
        self.assertIn(expected_hex, self._fn(data))


class TestKeyFromOptionalHex(unittest.TestCase):
    def setUp(self):
        from wallet_interface.helpers._storage import _key_from_optional_hex

        self._fn = _key_from_optional_hex

    def test_returns_none_for_none(self):
        self.assertIsNone(self._fn(None))

    def test_decodes_32_byte_key(self):
        hex_key = "a" * 64  # 32 bytes
        result = self._fn(hex_key)
        self.assertIsInstance(result, bytes)
        self.assertEqual(len(result), 32)

    def test_raises_for_wrong_length(self):
        with self.assertRaises(ValueError):
            self._fn("deadbeef")  # only 4 bytes


class TestResponseMessageFromRawJson(unittest.TestCase):
    def setUp(self):
        from wallet_interface.helpers._storage import _response_message_from_raw_json

        self._fn = _response_message_from_raw_json

    def test_extracts_error_field(self):
        raw = '{"error": "not found"}'
        self.assertEqual(self._fn(raw), "not found")

    def test_extracts_message_field(self):
        raw = '{"message": "rate limited"}'
        self.assertEqual(self._fn(raw), "rate limited")

    def test_returns_raw_for_non_json(self):
        raw = "plain text error"
        self.assertEqual(self._fn(raw), "plain text error")

    def test_returns_empty_for_empty_input(self):
        self.assertEqual(self._fn(""), "")

    def test_returns_raw_for_non_object(self):
        raw = '["an", "array"]'
        self.assertEqual(self._fn(raw), raw.strip())


class TestFilecoinPinServiceUrl(unittest.TestCase):
    def setUp(self):
        from wallet_interface.helpers._storage import _filecoin_pin_service_url

        self._fn = _filecoin_pin_service_url

    def test_returns_empty_when_not_configured(self):
        os.environ.pop("WALLET_FILECOIN_PIN_SERVICE_URL", None)
        self.assertEqual(self._fn(), "")

    def test_returns_configured_url(self):
        os.environ["WALLET_FILECOIN_PIN_SERVICE_URL"] = "https://pin.example.com/"
        try:
            self.assertEqual(self._fn(), "https://pin.example.com")
        finally:
            del os.environ["WALLET_FILECOIN_PIN_SERVICE_URL"]


class TestFilecoinPinMockStatus(unittest.TestCase):
    def setUp(self):
        from wallet_interface.helpers._storage import _filecoin_pin_mock_status

        self._fn = _filecoin_pin_mock_status

    def test_defaults_to_pinned(self):
        os.environ.pop("WALLET_FILECOIN_PIN_MOCK_STATUS", None)
        self.assertEqual(self._fn(), "pinned")

    def test_returns_configured_status(self):
        os.environ["WALLET_FILECOIN_PIN_MOCK_STATUS"] = "queued"
        try:
            self.assertEqual(self._fn(), "queued")
        finally:
            del os.environ["WALLET_FILECOIN_PIN_MOCK_STATUS"]


class TestFilecoinUploadStatusUrl(unittest.TestCase):
    def setUp(self):
        from wallet_interface.helpers._storage import _filecoin_upload_status_url

        self._fn = _filecoin_upload_status_url

    def test_returns_path_with_request_id(self):
        result = self._fn("req-abc-123")
        self.assertIn("req-abc-123", result)
        self.assertTrue(result.startswith("/"))


class TestMockFilecoinPinRequest(unittest.TestCase):
    def setUp(self):
        from wallet_interface.helpers._storage import _mock_filecoin_pin_request

        self._fn = _mock_filecoin_pin_request

    def test_post_pins_returns_requestid(self):
        result = self._fn("POST", "/pins", payload={"cid": "bafybeitest"})
        self.assertIn("requestid", result)
        self.assertIn("bafybeitest", str(result))

    def test_post_pins_status_is_queued(self):
        result = self._fn("POST", "/pins", payload={"cid": "bafybeitest"})
        self.assertEqual(result["status"], "queued")

    def test_get_pins_returns_status(self):
        result = self._fn("GET", "/pins/mock-req-id")
        self.assertIn("status", result)
        self.assertIn("requestid", result)

    def test_raises_for_post_without_cid(self):
        from wallet_interface.helpers._app import FilecoinPinHandoffError

        with self.assertRaises(FilecoinPinHandoffError):
            self._fn("POST", "/pins", payload={})

    def test_raises_for_unknown_method_path(self):
        from wallet_interface.helpers._app import FilecoinPinHandoffError

        with self.assertRaises(FilecoinPinHandoffError):
            self._fn("DELETE", "/pins/something")

    def test_requestid_is_deterministic(self):
        r1 = self._fn("POST", "/pins", payload={"cid": "bafybeiabc"})
        r2 = self._fn("POST", "/pins", payload={"cid": "bafybeiabc"})
        self.assertEqual(r1["requestid"], r2["requestid"])


class TestParseUploadMetadata(unittest.TestCase):
    def setUp(self):
        from wallet_interface.helpers._storage import _parse_upload_metadata

        self._fn = _parse_upload_metadata

    def test_returns_empty_for_none(self):
        self.assertEqual(self._fn(None), {})

    def test_returns_empty_for_empty_string(self):
        self.assertEqual(self._fn(""), {})

    def test_parses_valid_json(self):
        result = self._fn('{"key": "value"}')
        self.assertEqual(result, {"key": "value"})

    def test_raises_for_non_object_json(self):
        with self.assertRaises(Exception):
            self._fn("[1, 2, 3]")


class TestFilecoinPinTimeoutSeconds(unittest.TestCase):
    def setUp(self):
        from wallet_interface.helpers._storage import _filecoin_pin_timeout_seconds

        self._fn = _filecoin_pin_timeout_seconds

    def test_defaults_to_30(self):
        os.environ.pop("WALLET_FILECOIN_PIN_TIMEOUT_SECONDS", None)
        self.assertAlmostEqual(self._fn(), 30.0)

    def test_raises_for_zero(self):
        from wallet_interface.helpers._app import FilecoinPinHandoffError

        os.environ["WALLET_FILECOIN_PIN_TIMEOUT_SECONDS"] = "0"
        try:
            with self.assertRaises(FilecoinPinHandoffError):
                self._fn()
        finally:
            del os.environ["WALLET_FILECOIN_PIN_TIMEOUT_SECONDS"]


class TestPublishBytesViaIpfsBackendMock(unittest.TestCase):
    """Tests _publish_bytes_via_ipfs_backend in mock mode (no IPFS needed)."""

    def setUp(self):
        from wallet_interface.helpers._storage import _publish_bytes_via_ipfs_backend

        self._fn = _publish_bytes_via_ipfs_backend

    def test_mock_mode_returns_cid(self):
        os.environ["WALLET_IPFS_UPLOAD_BACKEND"] = "mock"
        try:
            result = self._fn(b"some data")
            self.assertTrue(result.startswith("bafybeimock"))
        finally:
            del os.environ["WALLET_IPFS_UPLOAD_BACKEND"]

    def test_non_mock_mode_raises_without_backend(self):
        os.environ.pop("WALLET_IPFS_UPLOAD_BACKEND", None)
        # Without ipfs_datasets_py installed, this should raise
        from wallet_interface.helpers._storage import _IPFS_BACKEND_AVAILABLE

        if not _IPFS_BACKEND_AVAILABLE:
            with self.assertRaises(RuntimeError):
                self._fn(b"data")


if __name__ == "__main__":
    unittest.main()
