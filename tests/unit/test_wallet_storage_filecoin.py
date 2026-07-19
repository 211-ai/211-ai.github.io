"""Unit tests for wallet_interface/helpers/_storage_filecoin.py.

Covers the functions not already exercised in test_wallet_storage_helpers.py:
_filecoin_pin_request (mock-backend and error paths),
_fetch_filecoin_pin_status, and _submit_ipfs_cid_to_filecoin_pin.
All tests are stdlib-only and require no network access.
"""
from __future__ import annotations

import os
import unittest
import unittest.mock


class TestFilecoinPinRequestMockBackend(unittest.TestCase):
    """_filecoin_pin_request delegates to mock backend when service url is 'mock'."""

    def setUp(self):
        from wallet_interface.helpers._storage_filecoin import _filecoin_pin_request

        self._fn = _filecoin_pin_request

    def _with_mock_url(self, env: dict[str, str] | None = None):
        base = {"WALLET_FILECOIN_PIN_SERVICE_URL": "mock"}
        base.update(env or {})
        return base

    def test_post_pins_returns_queued_status(self):
        with unittest.mock.patch.dict(os.environ, self._with_mock_url(), clear=False):
            result = self._fn("POST", "/pins", payload={"cid": "bafytest123"})
        self.assertEqual(result["status"], "queued")
        self.assertEqual(result["info"]["cid"], "bafytest123")

    def test_post_pins_returns_deterministic_request_id(self):
        with unittest.mock.patch.dict(os.environ, self._with_mock_url(), clear=False):
            r1 = self._fn("POST", "/pins", payload={"cid": "bafyabc"})
            r2 = self._fn("POST", "/pins", payload={"cid": "bafyabc"})
        self.assertEqual(r1["requestid"], r2["requestid"])

    def test_post_pins_different_cids_produce_different_ids(self):
        with unittest.mock.patch.dict(os.environ, self._with_mock_url(), clear=False):
            r1 = self._fn("POST", "/pins", payload={"cid": "bafyabc"})
            r2 = self._fn("POST", "/pins", payload={"cid": "bafyxyz"})
        self.assertNotEqual(r1["requestid"], r2["requestid"])

    def test_get_pin_status_returns_requestid(self):
        with unittest.mock.patch.dict(os.environ, self._with_mock_url(), clear=False):
            r = self._fn("POST", "/pins", payload={"cid": "bafystatus"})
            req_id = r["requestid"]
            status_r = self._fn("GET", f"/pins/{req_id}")
        self.assertEqual(status_r["requestid"], req_id)

    def test_get_pin_status_default_mock_status_is_pinned(self):
        with unittest.mock.patch.dict(
            os.environ,
            {**self._with_mock_url(), "WALLET_FILECOIN_PIN_MOCK_STATUS": "pinned"},
            clear=False,
        ):
            r = self._fn("POST", "/pins", payload={"cid": "bafycheck"})
            req_id = r["requestid"]
            status_r = self._fn("GET", f"/pins/{req_id}")
        self.assertEqual(status_r["status"], "pinned")

    def test_unsupported_method_raises(self):
        from wallet_interface.helpers._app import FilecoinPinHandoffError

        with unittest.mock.patch.dict(os.environ, self._with_mock_url(), clear=False):
            with self.assertRaises(FilecoinPinHandoffError):
                self._fn("DELETE", "/pins/foo")

    def test_post_pins_missing_cid_raises(self):
        from wallet_interface.helpers._app import FilecoinPinHandoffError

        with unittest.mock.patch.dict(os.environ, self._with_mock_url(), clear=False):
            with self.assertRaises(FilecoinPinHandoffError):
                self._fn("POST", "/pins", payload={"cid": ""})

    def test_get_pin_status_empty_id_raises(self):
        from wallet_interface.helpers._app import FilecoinPinHandoffError

        with unittest.mock.patch.dict(os.environ, self._with_mock_url(), clear=False):
            with self.assertRaises(FilecoinPinHandoffError):
                self._fn("GET", "/pins/")


class TestFilecoinPinRequestNoServiceUrl(unittest.TestCase):
    """_filecoin_pin_request raises when no service url is configured."""

    def test_raises_when_url_not_set(self):
        from wallet_interface.helpers._app import FilecoinPinHandoffError
        from wallet_interface.helpers._storage_filecoin import _filecoin_pin_request

        env = {k: v for k, v in os.environ.items() if k != "WALLET_FILECOIN_PIN_SERVICE_URL"}
        with unittest.mock.patch.dict(os.environ, env, clear=True):
            with self.assertRaises(FilecoinPinHandoffError):
                _filecoin_pin_request("POST", "/pins", payload={"cid": "bafy"})

    def test_raises_with_empty_url(self):
        from wallet_interface.helpers._app import FilecoinPinHandoffError
        from wallet_interface.helpers._storage_filecoin import _filecoin_pin_request

        with unittest.mock.patch.dict(
            os.environ,
            {"WALLET_FILECOIN_PIN_SERVICE_URL": ""},
            clear=False,
        ):
            with self.assertRaises(FilecoinPinHandoffError):
                _filecoin_pin_request("POST", "/pins", payload={"cid": "bafy"})


class TestFetchFilecoinPinStatus(unittest.TestCase):
    """_fetch_filecoin_pin_status wraps _filecoin_pin_request for GET /pins/{id}."""

    def setUp(self):
        from wallet_interface.helpers._storage_filecoin import _fetch_filecoin_pin_status

        self._fn = _fetch_filecoin_pin_status

    def test_returns_status_dict_for_known_id(self):
        with unittest.mock.patch.dict(
            os.environ,
            {"WALLET_FILECOIN_PIN_SERVICE_URL": "mock"},
            clear=False,
        ):
            from wallet_interface.helpers._storage_filecoin import _filecoin_pin_request

            pin = _filecoin_pin_request("POST", "/pins", payload={"cid": "bafyfetchtest"})
            req_id = pin["requestid"]
            status = self._fn(req_id)
        self.assertEqual(status["requestid"], req_id)
        self.assertIn("status", status)

    def test_raises_for_empty_request_id(self):
        with self.assertRaises(ValueError):
            self._fn("")

    def test_raises_for_whitespace_request_id(self):
        with self.assertRaises(ValueError):
            self._fn("   ")

    def test_raises_when_no_service_configured(self):
        from wallet_interface.helpers._app import FilecoinPinHandoffError

        env = {k: v for k, v in os.environ.items() if k != "WALLET_FILECOIN_PIN_SERVICE_URL"}
        with unittest.mock.patch.dict(os.environ, env, clear=True):
            with self.assertRaises(FilecoinPinHandoffError):
                self._fn("some-request-id")


class TestSubmitIpfsCidToFilecoinPin(unittest.TestCase):
    """_submit_ipfs_cid_to_filecoin_pin returns None when not configured."""

    def setUp(self):
        from wallet_interface.helpers._storage_filecoin import _submit_ipfs_cid_to_filecoin_pin

        self._fn = _submit_ipfs_cid_to_filecoin_pin

    def test_returns_none_when_no_service_url(self):
        env = {k: v for k, v in os.environ.items() if k != "WALLET_FILECOIN_PIN_SERVICE_URL"}
        with unittest.mock.patch.dict(os.environ, env, clear=True):
            result = self._fn("bafytest")
        self.assertIsNone(result)

    def test_returns_none_when_url_is_empty_string(self):
        with unittest.mock.patch.dict(
            os.environ,
            {"WALLET_FILECOIN_PIN_SERVICE_URL": ""},
            clear=False,
        ):
            result = self._fn("bafytest")
        self.assertIsNone(result)

    def test_submits_to_mock_backend_and_returns_dict(self):
        with unittest.mock.patch.dict(
            os.environ,
            {"WALLET_FILECOIN_PIN_SERVICE_URL": "mock"},
            clear=False,
        ):
            result = self._fn("bafymockcid")
        self.assertIsNotNone(result)
        self.assertIsInstance(result, dict)
        self.assertIn("requestid", result)

    def test_returned_status_is_queued(self):
        with unittest.mock.patch.dict(
            os.environ,
            {"WALLET_FILECOIN_PIN_SERVICE_URL": "mock"},
            clear=False,
        ):
            result = self._fn("bafymockcid2")
        self.assertEqual(result["status"], "queued")

    def test_metadata_includes_source(self):
        with unittest.mock.patch.dict(
            os.environ,
            {"WALLET_FILECOIN_PIN_SERVICE_URL": "mock"},
            clear=False,
        ):
            result = self._fn("bafymeta", wallet_id="wid-1", source_record_id="rec-1")
        self.assertEqual(result["info"]["cid"], "bafymeta")

    def test_optional_fields_do_not_affect_return_structure(self):
        with unittest.mock.patch.dict(
            os.environ,
            {"WALLET_FILECOIN_PIN_SERVICE_URL": "mock"},
            clear=False,
        ):
            result = self._fn(
                "bafyoptional",
                file_name="report.pdf",
                mime_type="application/pdf",
                source_record_id="rec-99",
                wallet_id="wid-99",
            )
        self.assertIsInstance(result, dict)
        self.assertIn("requestid", result)

    def test_deterministic_for_same_cid(self):
        with unittest.mock.patch.dict(
            os.environ,
            {"WALLET_FILECOIN_PIN_SERVICE_URL": "mock"},
            clear=False,
        ):
            r1 = self._fn("bafysamecid")
            r2 = self._fn("bafysamecid")
        self.assertEqual(r1["requestid"], r2["requestid"])

    def test_origins_env_var_is_read(self):
        with unittest.mock.patch.dict(
            os.environ,
            {
                "WALLET_FILECOIN_PIN_SERVICE_URL": "mock",
                "WALLET_FILECOIN_PIN_ORIGINS": "/ip4/127.0.0.1/tcp/4001",
            },
            clear=False,
        ):
            result = self._fn("bafyorigins")
        self.assertIsNotNone(result)


if __name__ == "__main__":
    import unittest as _unittest

    _unittest.main()
