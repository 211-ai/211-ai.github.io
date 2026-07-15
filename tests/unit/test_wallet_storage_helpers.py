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


class TestJsonSafeMetadata(unittest.TestCase):
    """Tests _json_safe_metadata pure sanitization."""

    def setUp(self):
        from wallet_interface.helpers._storage import _json_safe_metadata

        self._fn = _json_safe_metadata

    def test_passthrough_string(self):
        self.assertEqual(self._fn("hello"), "hello")

    def test_passthrough_int(self):
        self.assertEqual(self._fn(42), 42)

    def test_passthrough_float(self):
        self.assertAlmostEqual(self._fn(3.14), 3.14)

    def test_passthrough_bool(self):
        self.assertIs(self._fn(True), True)

    def test_passthrough_none(self):
        self.assertIsNone(self._fn(None))

    def test_dict_removes_none_values(self):
        result = self._fn({"a": "x", "b": None, "c": 1})
        self.assertEqual(result, {"a": "x", "c": 1})

    def test_list_removes_none_items(self):
        result = self._fn(["a", None, "b"])
        self.assertEqual(result, ["a", "b"])

    def test_nested_dict(self):
        result = self._fn({"outer": {"inner": None, "keep": "v"}})
        self.assertEqual(result, {"outer": {"keep": "v"}})

    def test_non_primitive_coerced_to_str(self):
        class Obj:
            def __str__(self):
                return "obj-str"

        result = self._fn(Obj())
        self.assertEqual(result, "obj-str")

    def test_empty_dict(self):
        self.assertEqual(self._fn({}), {})

    def test_empty_list(self):
        self.assertEqual(self._fn([]), [])


class TestGeneratedWalletMetadata(unittest.TestCase):
    """Tests _generated_wallet_metadata key allowlist and sanitization."""

    def setUp(self):
        from wallet_interface.helpers._storage import _generated_wallet_metadata

        self._fn = _generated_wallet_metadata

    def test_allowed_key_passes_through(self):
        result = self._fn({"privacyProfileStatus": "approved", "unwanted": "nope"})
        self.assertIn("privacyProfileStatus", result)
        self.assertNotIn("unwanted", result)

    def test_all_allowed_keys(self):
        allowed = {
            "decryptedClassification",
            "decryptedLabels",
            "decryptedMimeType",
            "fileName",
            "privacyProfileArtifactIds",
            "privacyProfileClassification",
            "privacyProfileLabels",
            "privacyProfileMimeType",
            "privacyProfileProofId",
            "privacyProfilePublicInputs",
            "privacyProfileSearchText",
            "privacyProfileStatus",
            "privacyProfileSummary",
            "privacyProfileVectorTerms",
        }
        data = {key: f"v-{key}" for key in allowed}
        data["shouldBeStripped"] = "yes"
        result = self._fn(data)
        self.assertEqual(set(result.keys()), allowed)

    def test_empty_metadata(self):
        self.assertEqual(self._fn({}), {})

    def test_none_values_stripped(self):
        result = self._fn({"privacyProfileStatus": None, "fileName": "f.pdf"})
        self.assertNotIn("privacyProfileStatus", result)
        self.assertIn("fileName", result)

    def test_output_is_sorted(self):
        result = self._fn({"privacyProfileSummary": "s", "fileName": "f"})
        self.assertEqual(list(result.keys()), sorted(result.keys()))


class TestRecordMetadataCid(unittest.TestCase):
    """Tests _record_metadata_cid CID extraction paths."""

    def setUp(self):
        from wallet_interface.helpers._storage import _record_metadata_cid

        self._fn = _record_metadata_cid

    def test_returns_metadataCid_from_top_level(self):
        record = {"metadata": {"metadataCid": "bafy123"}}
        self.assertEqual(self._fn(record), "bafy123")

    def test_returns_metadataIpldCid_when_metadataCid_absent(self):
        record = {"metadata": {"metadataIpldCid": "bafy456"}}
        self.assertEqual(self._fn(record), "bafy456")

    def test_prefers_metadataCid_over_ipldCid(self):
        record = {"metadata": {"metadataCid": "bafy123", "metadataIpldCid": "bafy456"}}
        self.assertEqual(self._fn(record), "bafy123")

    def test_falls_through_to_nested_record(self):
        record = {"record": {"metadata": {"metadataCid": "bafy789"}}}
        self.assertEqual(self._fn(record), "bafy789")

    def test_returns_empty_when_no_cid(self):
        self.assertEqual(self._fn({}), "")
        self.assertEqual(self._fn({"metadata": {}}), "")

    def test_ignores_empty_cid_string(self):
        record = {"metadata": {"metadataCid": "  "}}
        self.assertEqual(self._fn(record), "")


class TestShouldPublishRecordMetadataIpld(unittest.TestCase):
    """Tests _should_publish_record_metadata_ipld key-presence check."""

    def setUp(self):
        from wallet_interface.helpers._storage import _should_publish_record_metadata_ipld

        self._fn = _should_publish_record_metadata_ipld

    def test_true_when_privacy_key_present(self):
        self.assertTrue(self._fn({"privacyProfileStatus": "approved"}))

    def test_true_when_decrypted_key_present(self):
        self.assertTrue(self._fn({"decryptedClassification": "public"}))

    def test_false_when_no_generated_keys(self):
        self.assertFalse(self._fn({"fileName": "doc.pdf", "size": 1234}))

    def test_false_for_empty_metadata(self):
        self.assertFalse(self._fn({}))

    def test_all_generated_keys_trigger_true(self):
        generated_keys = [
            "decryptedClassification",
            "decryptedLabels",
            "decryptedMimeType",
            "privacyProfileArtifactIds",
            "privacyProfileClassification",
            "privacyProfileLabels",
            "privacyProfileMimeType",
            "privacyProfileProofId",
            "privacyProfilePublicInputs",
            "privacyProfileSearchText",
            "privacyProfileStatus",
            "privacyProfileSummary",
            "privacyProfileVectorTerms",
        ]
        for key in generated_keys:
            self.assertTrue(self._fn({key: "val"}), f"Expected True for key {key!r}")


class TestFilecoinPinRequestHeaders(unittest.TestCase):
    """Tests _filecoin_pin_request_headers env-driven header construction."""

    def setUp(self):
        from wallet_interface.helpers._storage_filecoin import _filecoin_pin_request_headers

        self._fn = _filecoin_pin_request_headers
        # Clear relevant env vars before each test
        for key in (
            "WALLET_FILECOIN_PIN_BEARER_TOKEN",
            "WALLET_FILECOIN_PIN_HTTP_HEADER_NAME",
            "WALLET_FILECOIN_PIN_HTTP_HEADER_VALUE",
        ):
            os.environ.pop(key, None)

    def tearDown(self):
        for key in (
            "WALLET_FILECOIN_PIN_BEARER_TOKEN",
            "WALLET_FILECOIN_PIN_HTTP_HEADER_NAME",
            "WALLET_FILECOIN_PIN_HTTP_HEADER_VALUE",
        ):
            os.environ.pop(key, None)

    def test_no_headers_when_no_env(self):
        result = self._fn(include_json_content_type=False)
        self.assertEqual(result, {})

    def test_content_type_when_flag_true(self):
        result = self._fn(include_json_content_type=True)
        self.assertEqual(result["content-type"], "application/json")

    def test_bearer_token_added(self):
        os.environ["WALLET_FILECOIN_PIN_BEARER_TOKEN"] = "mytoken"
        result = self._fn(include_json_content_type=False)
        self.assertIn("authorization", result)
        self.assertIn("mytoken", result["authorization"])

    def test_custom_header_added(self):
        os.environ["WALLET_FILECOIN_PIN_HTTP_HEADER_NAME"] = "x-api-key"
        os.environ["WALLET_FILECOIN_PIN_HTTP_HEADER_VALUE"] = "secret"
        result = self._fn(include_json_content_type=False)
        self.assertEqual(result["x-api-key"], "secret")

    def test_raises_when_header_name_set_but_value_missing(self):
        from wallet_interface.helpers._app import FilecoinPinHandoffError

        os.environ["WALLET_FILECOIN_PIN_HTTP_HEADER_NAME"] = "x-api-key"
        with self.assertRaises(FilecoinPinHandoffError):
            self._fn(include_json_content_type=False)


class TestFilecoinPinStatusUrl(unittest.TestCase):
    """Tests _filecoin_pin_status_url URL construction."""

    def setUp(self):
        from wallet_interface.helpers._storage_filecoin import _filecoin_pin_status_url

        self._fn = _filecoin_pin_status_url

    def tearDown(self):
        os.environ.pop("WALLET_FILECOIN_PIN_SERVICE_URL", None)

    def test_returns_empty_when_no_service_url(self):
        os.environ.pop("WALLET_FILECOIN_PIN_SERVICE_URL", None)
        self.assertEqual(self._fn("req-1"), "")

    def test_returns_full_url_when_configured(self):
        os.environ["WALLET_FILECOIN_PIN_SERVICE_URL"] = "https://pin.example.com"
        self.assertEqual(self._fn("req-abc"), "https://pin.example.com/pins/req-abc")


if __name__ == "__main__":
    unittest.main()
