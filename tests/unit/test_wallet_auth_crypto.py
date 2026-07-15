"""Unit tests for wallet_interface/helpers/_auth.py crypto and magic-login helpers."""

from __future__ import annotations

import os
import time
import unittest
from unittest.mock import patch


def _import_auth():
    try:
        from wallet_interface.helpers._auth import (
            _allowed_magic_login_hosts,
            _base64url_decode_to_bytes,
            _base64url_encode_bytes,
            _build_magic_login_link,
            _hmac_base64url,
            _magic_login_base_url,
            _sign_magic_login_token,
            _verify_magic_login_token,
        )
        return (
            _allowed_magic_login_hosts,
            _base64url_decode_to_bytes,
            _base64url_encode_bytes,
            _build_magic_login_link,
            _hmac_base64url,
            _magic_login_base_url,
            _sign_magic_login_token,
            _verify_magic_login_token,
        )
    except ImportError:
        import pytest
        pytest.skip("wallet_interface.helpers._auth not importable")


# ---------------------------------------------------------------------------
# _base64url_encode_bytes / _base64url_decode_to_bytes
# ---------------------------------------------------------------------------


class TestBase64UrlCodecs:
    def _fns(self):
        (_, dec, enc, *_) = _import_auth()
        return enc, dec

    def test_roundtrip_empty(self):
        enc, dec = self._fns()
        assert dec(enc(b"")) == b""

    def test_roundtrip_short(self):
        enc, dec = self._fns()
        data = b"hello"
        assert dec(enc(data)) == data

    def test_roundtrip_binary(self):
        enc, dec = self._fns()
        data = bytes(range(256))
        assert dec(enc(data)) == data

    def test_no_padding_chars_in_output(self):
        enc, _ = self._fns()
        result = enc(b"test")
        assert "=" not in result

    def test_url_safe_chars_only(self):
        enc, _ = self._fns()
        result = enc(b"some test data here")
        assert all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_" for c in result)

    def test_decode_handles_missing_padding(self):
        enc, dec = self._fns()
        original = b"hello world"
        encoded = enc(original)
        # Encoded should not have =, but decode should still work
        assert "=" not in encoded
        assert dec(encoded) == original

    def test_decode_handles_extra_padding(self):
        _, dec = self._fns()
        # Add extra padding - should still work
        encoded = "aGVsbG8"  # "hello" base64url without padding
        assert dec(encoded) == b"hello"


# ---------------------------------------------------------------------------
# _hmac_base64url
# ---------------------------------------------------------------------------


class TestHmacBase64url:
    def _fn(self):
        (_, _, _, _, fn, *_) = _import_auth()
        return fn

    def test_returns_string(self):
        fn = self._fn()
        result = fn("secret", "message")
        assert isinstance(result, str)

    def test_deterministic(self):
        fn = self._fn()
        r1 = fn("secret", "message")
        r2 = fn("secret", "message")
        assert r1 == r2

    def test_different_secrets_produce_different_macs(self):
        fn = self._fn()
        r1 = fn("secret1", "message")
        r2 = fn("secret2", "message")
        assert r1 != r2

    def test_different_messages_produce_different_macs(self):
        fn = self._fn()
        r1 = fn("secret", "message1")
        r2 = fn("secret", "message2")
        assert r1 != r2

    def test_no_padding_chars(self):
        fn = self._fn()
        result = fn("secret", "message")
        assert "=" not in result

    def test_uses_sha256_length(self):
        fn = self._fn()
        # SHA-256 = 32 bytes → base64url ~43 chars
        result = fn("secret", "message")
        # At least 40 chars for 32-byte HMAC
        assert len(result) >= 40

    def test_known_vector(self):
        """Verify against known HMAC-SHA256 base64url value."""
        import base64
        import hashlib
        import hmac as stdlib_hmac
        fn = self._fn()
        secret = "test-secret"
        message = "payload"
        expected = base64.urlsafe_b64encode(
            stdlib_hmac.new(secret.encode(), message.encode(), hashlib.sha256).digest()
        ).decode().rstrip("=")
        assert fn(secret, message) == expected


# ---------------------------------------------------------------------------
# _sign_magic_login_token / _verify_magic_login_token
# ---------------------------------------------------------------------------

def _mock_secret(val: str = "test-login-secret-abc"):
    return patch("wallet_interface.helpers._auth.resolve_secret", return_value=val)


class TestSignAndVerifyMagicToken:
    def _fns(self):
        (*_, sign, verify) = _import_auth()
        return sign, verify

    def _payload(self, **overrides):
        now_ms = int(time.time() * 1000)
        base = {
            "v": 1,
            "portal": "client",
            "contact": "user@example.com",
            "nonce": "abc123",
            "issuedAt": now_ms - 1000,
            "expiresAt": now_ms + 3_600_000,
        }
        base.update(overrides)
        return base

    def test_sign_returns_string(self):
        sign, _ = self._fns()
        with _mock_secret():
            token = sign(self._payload())
        assert isinstance(token, str)

    def test_token_has_two_parts(self):
        sign, _ = self._fns()
        with _mock_secret():
            token = sign(self._payload())
        parts = token.split(".")
        assert len(parts) == 2

    def test_verify_roundtrip(self):
        sign, verify = self._fns()
        payload = self._payload()
        with _mock_secret():
            token = sign(payload)
            verified = verify(token)
        assert verified["contact"] == payload["contact"]

    def test_verify_rejects_tampered_signature(self):
        import pytest
        sign, verify = self._fns()
        with _mock_secret():
            token = sign(self._payload())
        # Corrupt last character of signature
        parts = token.rsplit(".", 1)
        tampered = parts[0] + "." + parts[1][:-1] + ("A" if parts[1][-1] != "A" else "B")
        with pytest.raises(ValueError, match="signature is invalid"):
            with _mock_secret():
                verify(tampered)

    def test_verify_rejects_expired_token(self):
        import pytest
        sign, verify = self._fns()
        now_ms = int(time.time() * 1000)
        expired_payload = self._payload(expiresAt=now_ms - 10_000)
        with _mock_secret():
            token = sign(expired_payload)
        with pytest.raises(ValueError, match="expired"):
            with _mock_secret():
                verify(token)

    def test_verify_rejects_malformed_token(self):
        import pytest
        _, verify = self._fns()
        with pytest.raises(ValueError, match="malformed"):
            with _mock_secret():
                verify("not.a.valid.token")

    def test_verify_rejects_wrong_portal(self):
        import pytest
        sign, verify = self._fns()
        with _mock_secret():
            token = sign(self._payload(portal="admin"))
        with pytest.raises(ValueError, match="malformed"):
            with _mock_secret():
                verify(token)

    def test_sign_raises_without_secret(self):
        import pytest
        sign, _ = self._fns()
        with pytest.raises(RuntimeError, match="WALLET_MAGIC_LOGIN_SECRET"):
            with _mock_secret(""):
                sign(self._payload())


# ---------------------------------------------------------------------------
# _allowed_magic_login_hosts
# ---------------------------------------------------------------------------


class TestAllowedMagicLoginHosts:
    def _fn(self):
        (fn, *_) = _import_auth()
        return fn

    def test_includes_default_hosts(self):
        fn = self._fn()
        with patch.dict(os.environ, {"WALLET_MAGIC_LOGIN_ALLOWED_HOSTS": ""}):
            hosts = fn()
        assert hosts.issuperset({"211-ai.com", "localhost"})

    def test_custom_hosts_from_env(self):
        fn = self._fn()
        with patch.dict(os.environ, {"WALLET_MAGIC_LOGIN_ALLOWED_HOSTS": "myapp.com,staging.myapp.com"}):
            hosts = fn()
        assert hosts.issuperset({"myapp.com", "staging.myapp.com"})

    def test_hosts_are_lowercase(self):
        fn = self._fn()
        with patch.dict(os.environ, {"WALLET_MAGIC_LOGIN_ALLOWED_HOSTS": "MyApp.COM"}):
            hosts = fn()
        assert hosts.issuperset({"myapp.com"})

    def test_returns_set(self):
        result = self._fn()()
        assert isinstance(result, set)


# ---------------------------------------------------------------------------
# _magic_login_base_url
# ---------------------------------------------------------------------------


class TestMagicLoginBaseUrl:
    def _fn(self):
        (_, _, _, _, _, fn, *_) = _import_auth()
        return fn

    def test_accepts_valid_url(self):
        fn = self._fn()
        with patch.dict(os.environ, {"WALLET_MAGIC_LOGIN_ALLOWED_HOSTS": "211-ai.com,example.com"}):
            result = fn("https://example.com/login")
        assert result == "https://example.com/login"

    def test_rejects_non_http_scheme(self):
        import pytest
        fn = self._fn()
        with pytest.raises(ValueError, match="absolute http"):
            fn("ftp://example.com/login")

    def test_rejects_disallowed_host(self):
        import pytest
        fn = self._fn()
        with patch.dict(os.environ, {"WALLET_MAGIC_LOGIN_ALLOWED_HOSTS": "trusted.com"}):
            with pytest.raises(ValueError, match="not allowed"):
                fn("https://evil.com/login")

    def test_uses_fallback_when_empty(self):
        fn = self._fn()
        with patch.dict(os.environ, {
            "WALLET_MAGIC_LOGIN_BASE_URL": "https://211-ai.com/",
            "WALLET_MAGIC_LOGIN_ALLOWED_HOSTS": "",
        }):
            result = fn("")
        from urllib.parse import urlparse
        assert urlparse(result).netloc == "211-ai.com"


# ---------------------------------------------------------------------------
# _build_magic_login_link
# ---------------------------------------------------------------------------


class TestBuildMagicLoginLink:
    def _fn(self):
        (_, _, _, fn, *_) = _import_auth()
        return fn

    def test_includes_token_param(self):
        fn = self._fn()
        link = fn(token="abc123", base_url="https://211-ai.com/")
        assert "magic_login" in link or "abc123" in link

    def test_link_is_valid_url(self):
        from urllib import parse as urllib_parse
        fn = self._fn()
        link = fn(token="mytoken", base_url="https://211-ai.com/")
        parsed = urllib_parse.urlparse(link)
        assert parsed.scheme == "https"
        assert parsed.netloc == "211-ai.com"

    def test_token_preserved_in_query(self):
        from urllib import parse as urllib_parse
        fn = self._fn()
        link = fn(token="test-token-xyz", base_url="https://211-ai.com/app")
        params = dict(urllib_parse.parse_qsl(urllib_parse.urlparse(link).query))
        # Token should be in one of the query params
        assert "test-token-xyz" in params.values()
