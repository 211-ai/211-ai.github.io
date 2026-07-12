"""Unit tests for wallet_interface/helpers.py pure utility functions.

These tests exercise stateless pure helpers that require no network access
or optional dependencies such as FastAPI or ipfs_datasets_py.
"""

from __future__ import annotations

import base64

import pytest

# ---------------------------------------------------------------------------
# _normalize_ipfs_cid / _valid_ipfs_cid
# ---------------------------------------------------------------------------

class TestIpfsCidHelpers:
    def _import(self):
        try:
            from wallet_interface.helpers import _normalize_ipfs_cid, _valid_ipfs_cid
            return _normalize_ipfs_cid, _valid_ipfs_cid
        except ImportError:
            pytest.skip("wallet_interface.helpers not importable (missing optional deps)")

    def test_valid_bafy_cid(self):
        normalize, valid = self._import()
        cid = "bafybeigdyrzt5sfp7udm7hu76uh7y26nf3efuylqabf3oclgtqy55fbzdi"
        assert valid(normalize(cid))

    def test_valid_qm_cid(self):
        normalize, valid = self._import()
        cid = "QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG"
        assert valid(normalize(cid))

    def test_invalid_cid_returns_false(self):
        normalize, valid = self._import()
        assert not valid("not-a-cid")
        assert not valid("")

    def test_normalize_strips_whitespace(self):
        normalize, valid = self._import()
        cid = "  bafybeigdyrzt5sfp7udm7hu76uh7y26nf3efuylqabf3oclgtqy55fbzdi  "
        assert normalize(cid) == cid.strip()


# ---------------------------------------------------------------------------
# _is_email_contact / _normalize_phone_number
# ---------------------------------------------------------------------------

class TestContactHelpers:
    def _import(self):
        try:
            from wallet_interface.helpers import _is_email_contact, _normalize_phone_number
            return _is_email_contact, _normalize_phone_number
        except ImportError:
            pytest.skip("wallet_interface.helpers not importable")

    def test_email_recognized(self):
        is_email, _ = self._import()
        assert is_email("user@example.com")
        assert is_email("USER@EXAMPLE.COM")

    def test_phone_not_email(self):
        is_email, _ = self._import()
        assert not is_email("+15035551234")
        assert not is_email("5035551234")

    def test_normalize_phone_digits_only(self):
        _, normalize = self._import()
        result = normalize("(503) 555-1234")
        assert result.isdigit() or result.startswith("+")


# ---------------------------------------------------------------------------
# _base64url_encode_bytes / _base64url_decode_to_bytes
# ---------------------------------------------------------------------------

class TestBase64UrlHelpers:
    def _import(self):
        try:
            from wallet_interface.helpers import _base64url_decode_to_bytes, _base64url_encode_bytes
            return _base64url_encode_bytes, _base64url_decode_to_bytes
        except ImportError:
            pytest.skip("wallet_interface.helpers not importable")

    def test_roundtrip(self):
        encode, decode = self._import()
        data = b"hello world \x00\xff"
        assert decode(encode(data)) == data

    def test_no_padding_chars(self):
        encode, _ = self._import()
        result = encode(b"test data")
        assert "=" not in result

    def test_url_safe_chars_only(self):
        encode, _ = self._import()
        result = encode(b"binary \x00\xfe\xff data")
        assert "+" not in result
        assert "/" not in result


# ---------------------------------------------------------------------------
# _number_to_words
# ---------------------------------------------------------------------------

class TestNumberToWords:
    def _import(self):
        try:
            from wallet_interface.helpers import _number_to_words
            return _number_to_words
        except ImportError:
            pytest.skip("wallet_interface.helpers not importable")

    def test_zero(self):
        fn = self._import()
        assert fn(0) == "zero"

    def test_small_numbers(self):
        fn = self._import()
        assert fn(1) == "one"
        assert fn(11) == "eleven"
        assert fn(20) == "twenty"

    def test_compound(self):
        fn = self._import()
        assert "twenty" in fn(21)
        assert "one" in fn(21)

    def test_hundred(self):
        fn = self._import()
        result = fn(100)
        assert "hundred" in result
