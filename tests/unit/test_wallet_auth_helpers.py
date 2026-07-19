"""Unit tests for wallet_interface/helpers/_auth.py pure utility functions.

These tests exercise stateless pure helpers that require no network access
or optional dependencies such as FastAPI or ipfs_datasets_py.
"""

from __future__ import annotations

import pytest


def _import_auth_helpers():
    try:
        from wallet_interface.helpers._auth import (
            _extract_bearer_token,
            _is_email_contact,
            _normalize_login_contact,
            _normalize_phone_number,
        )
        return (
            _extract_bearer_token,
            _is_email_contact,
            _normalize_login_contact,
            _normalize_phone_number,
        )
    except ImportError:
        pytest.skip("wallet_interface.helpers._auth not importable (missing optional deps)")


# ---------------------------------------------------------------------------
# _extract_bearer_token
# ---------------------------------------------------------------------------

class TestExtractBearerToken:
    def _header(self, token: str) -> str:
        return "Bearer " + token

    def test_valid_bearer_token(self):
        fn, *_ = _import_auth_helpers()
        assert fn(self._header("abc123")) == "abc123"

    def test_case_insensitive_scheme(self):
        fn, *_ = _import_auth_helpers()
        assert fn("BEARER mytoken") == "mytoken"
        assert fn("bearer MYTOKEN") == "MYTOKEN"

    def test_non_bearer_scheme_returns_empty(self):
        fn, *_ = _import_auth_helpers()
        assert fn("Basic dXNlcjpwYXNz") == ""
        assert fn("Token abc") == ""

    def test_empty_header_returns_empty(self):
        fn, *_ = _import_auth_helpers()
        assert fn("") == ""
        assert fn(None) == ""

    def test_strips_whitespace_from_token(self):
        fn, *_ = _import_auth_helpers()
        assert fn(self._header("spacy") + "   ") == "spacy"

    def test_just_scheme_no_token(self):
        fn, *_ = _import_auth_helpers()
        assert fn("Bearer") == ""
        assert fn("Bearer ") == ""


# ---------------------------------------------------------------------------
# _is_email_contact
# ---------------------------------------------------------------------------

class TestIsEmailContact:
    def test_standard_email(self):
        _, is_email, *_ = _import_auth_helpers()
        assert is_email("user@example.com")

    def test_email_uppercase(self):
        _, is_email, *_ = _import_auth_helpers()
        assert is_email("USER@EXAMPLE.COM")

    def test_phone_not_email(self):
        _, is_email, *_ = _import_auth_helpers()
        assert not is_email("+15035551234")
        assert not is_email("5035551234")

    def test_empty_not_email(self):
        _, is_email, *_ = _import_auth_helpers()
        assert not is_email("")

    def test_at_sign_only_is_email_like(self):
        _, is_email, *_ = _import_auth_helpers()
        # _is_email_contact only checks for "@" presence
        assert is_email("@")


# ---------------------------------------------------------------------------
# _normalize_phone_number
# ---------------------------------------------------------------------------

class TestNormalizePhoneNumber:
    def test_us_number_with_formatting(self):
        *_, normalize = _import_auth_helpers()
        result = normalize("(503) 555-1234")
        assert result.replace("+", "").isdigit()
        assert "503" in result
        assert "5551234" in result

    def test_e164_format_preserved(self):
        *_, normalize = _import_auth_helpers()
        result = normalize("+15035551234")
        assert result.startswith("+")
        assert "15035551234" in result

    def test_plain_digits(self):
        *_, normalize = _import_auth_helpers()
        result = normalize("5035551234")
        assert result == "5035551234"

    def test_too_short_raises(self):
        *_, normalize = _import_auth_helpers()
        with pytest.raises(ValueError, match="10 digits"):
            normalize("123")

    def test_empty_raises(self):
        *_, normalize = _import_auth_helpers()
        with pytest.raises(ValueError):
            normalize("")


# ---------------------------------------------------------------------------
# _normalize_login_contact
# ---------------------------------------------------------------------------

class TestNormalizeLoginContact:
    def test_email_lowercased(self):
        _, _, normalize_contact, _ = _import_auth_helpers()
        result = normalize_contact("User@Example.COM")
        assert result == "user@example.com"

    def test_valid_phone_digits(self):
        _, _, normalize_contact, _ = _import_auth_helpers()
        result = normalize_contact("(503) 555-1234")
        assert result.replace("+", "").isdigit()

    def test_invalid_email_raises(self):
        _, _, normalize_contact, _ = _import_auth_helpers()
        with pytest.raises(ValueError, match="valid email"):
            normalize_contact("not-an-email@")

    def test_malformed_email_no_domain_raises(self):
        _, _, normalize_contact, _ = _import_auth_helpers()
        with pytest.raises(ValueError, match="valid email"):
            normalize_contact("user@nodot")
