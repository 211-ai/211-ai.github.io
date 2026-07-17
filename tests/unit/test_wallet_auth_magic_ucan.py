"""Unit tests for magic UCAN signing/verification and magic-login payload helpers.

Covers:
  _sign_magic_ucan          — HMAC-based UCAN token serialization
  _verify_magic_ucan        — deserialization, signature check, expiry
  _issue_magic_ucan         — full issued-UCAN structure
  _magic_login_payload_from_request — request → payload dict
  _wallet_config_from_magic_payload — payload → wallet config dict
  _require_magic_ucan       — FastAPI-style authorization helper
"""

from __future__ import annotations

import os
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch


def _mod():
    from wallet_interface.helpers import _auth as m
    return m


def _mock_secret(val: str = "test-magic-ucan-secret"):
    """Patch resolve_secret so UCAN signing works without optional deps."""
    return patch("wallet_interface.helpers._auth.resolve_secret", return_value=val)


# ---------------------------------------------------------------------------
# _sign_magic_ucan / _verify_magic_ucan
# ---------------------------------------------------------------------------
class TestSignVerifyMagicUcan(unittest.TestCase):
    """Round-trip signing and verification of magic UCAN tokens."""

    def _future_payload(self, **extras) -> dict:
        m = _mod()
        issued = int(time.time() * 1000)
        payload = {
            "profile": m._MAGIC_UCAN_CONTEXT,  # type: ignore[attr-defined]
            "iss": "did:abby:issuer",
            "aud": "did:abby:contact:abc123",
            "walletId": "wallet-test",
            "expiresAt": issued + 600_000,
            "nonce": "abc123",
        }
        payload.update(extras)
        return payload

    def test_sign_returns_three_part_token(self):
        m = _mod()
        with _mock_secret():
            token = m._sign_magic_ucan(self._future_payload())
        parts = token.split(".")
        self.assertEqual(len(parts), 3)

    def test_sign_context_prefix_matches(self):
        m = _mod()
        with _mock_secret():
            token = m._sign_magic_ucan(self._future_payload())
        self.assertTrue(token.startswith(m._MAGIC_UCAN_CONTEXT + "."))  # type: ignore[attr-defined]

    def test_verify_roundtrip_returns_payload(self):
        m = _mod()
        payload = self._future_payload(walletId="wlt-abc")
        with _mock_secret():
            token = m._sign_magic_ucan(payload)
            result = m._verify_magic_ucan(token)
        self.assertEqual(result["walletId"], "wlt-abc")

    def test_verify_rejects_tampered_payload(self):
        m = _mod()
        with _mock_secret():
            token = m._sign_magic_ucan(self._future_payload())
            ctx, payload_encoded, sig = token.split(".")
            tampered = ctx + "." + payload_encoded + "A" + "." + sig
            with self.assertRaises(ValueError):
                m._verify_magic_ucan(tampered)

    def test_verify_rejects_tampered_signature(self):
        m = _mod()
        with _mock_secret():
            token = m._sign_magic_ucan(self._future_payload())
            parts = token.split(".")
            parts[-1] = parts[-1][:-4] + "XXXX"
            with self.assertRaises(ValueError):
                m._verify_magic_ucan(".".join(parts))

    def test_verify_rejects_expired_token(self):
        m = _mod()
        payload = self._future_payload(expiresAt=int(time.time() * 1000) - 1)
        with _mock_secret():
            token = m._sign_magic_ucan(payload)
            with self.assertRaises(ValueError):
                m._verify_magic_ucan(token)

    def test_verify_rejects_malformed_token_two_parts(self):
        m = _mod()
        with _mock_secret():
            with self.assertRaises(ValueError):
                m._verify_magic_ucan("part1.part2")

    def test_verify_rejects_wrong_context_prefix(self):
        m = _mod()
        with _mock_secret():
            token = m._sign_magic_ucan(self._future_payload())
            parts = token.split(".")
            wrong = "wrong-context." + parts[1] + "." + parts[2]
            with self.assertRaises(ValueError):
                m._verify_magic_ucan(wrong)

    def test_sign_raises_without_secret(self):
        m = _mod()
        with _mock_secret(""):
            with self.assertRaises(RuntimeError):
                m._sign_magic_ucan(self._future_payload())

    def test_verify_raises_without_secret(self):
        m = _mod()
        with _mock_secret():
            token = m._sign_magic_ucan(self._future_payload())
        with _mock_secret(""):
            with self.assertRaises(RuntimeError):
                m._verify_magic_ucan(token)

    def test_token_not_reproducible_due_to_nonce(self):
        m = _mod()
        payload = self._future_payload()
        with _mock_secret():
            t1 = m._sign_magic_ucan({**payload, "nonce": "n1"})
            t2 = m._sign_magic_ucan({**payload, "nonce": "n2"})
        self.assertNotEqual(t1, t2)


# ---------------------------------------------------------------------------
# _issue_magic_ucan
# ---------------------------------------------------------------------------
class TestIssueMagicUcan(unittest.TestCase):
    """Tests for the issued-UCAN envelope wrapper."""

    def _payload(self, **kw):
        issued = int(time.time() * 1000)
        base = {
            "contact": "user@example.com",
            "walletId": "wallet-xyz",
            "expiresAt": issued + 900_000,
        }
        base.update(kw)
        return base

    def test_issued_ucan_has_token(self):
        m = _mod()
        with _mock_secret():
            result = m._issue_magic_ucan(self._payload())
        self.assertIn("token", result)
        self.assertIsInstance(result["token"], str)

    def test_issued_ucan_has_capabilities(self):
        m = _mod()
        with _mock_secret():
            result = m._issue_magic_ucan(self._payload(walletId="wallet-xyz"))
        self.assertIsInstance(result["capabilities"], list)
        self.assertTrue(len(result["capabilities"]) > 0)

    def test_issued_ucan_has_caveats(self):
        m = _mod()
        with _mock_secret():
            result = m._issue_magic_ucan(self._payload())
        caveats = result["caveats"]
        self.assertTrue(caveats["no_plaintext_key_access"])
        self.assertFalse(caveats["server_can_decrypt"])

    def test_issued_ucan_expires_within_ttl(self):
        m = _mod()
        before = int(time.time() * 1000)
        with _mock_secret():
            result = m._issue_magic_ucan(self._payload())
        after = int(time.time() * 1000)
        self.assertGreaterEqual(result["expires_at"], before)
        self.assertLessEqual(result["expires_at"], after + 15 * 60 * 1000 + 1000)

    def test_issued_ucan_caps_expiry_at_15_minutes(self):
        m = _mod()
        far_future = int(time.time() * 1000) + 10 * 3600 * 1000  # 10 hours
        with _mock_secret():
            result = m._issue_magic_ucan(self._payload(expiresAt=far_future))
        max_exp = int(time.time() * 1000) + 15 * 60 * 1000 + 5000  # 5s buffer
        self.assertLessEqual(result["expires_at"], max_exp)

    def test_issued_ucan_token_is_verifiable(self):
        m = _mod()
        with _mock_secret():
            result = m._issue_magic_ucan(self._payload())
            verified = m._verify_magic_ucan(result["token"])
        self.assertIsNotNone(verified)

    def test_issued_ucan_audience_derived_from_contact(self):
        m = _mod()
        with _mock_secret():
            result = m._issue_magic_ucan(self._payload(contact="test@example.com"))
        aud = result["audience"]
        self.assertTrue(aud.startswith("did:abby:contact:"))

    def test_issued_ucan_empty_wallet_id_allowed(self):
        m = _mod()
        with _mock_secret():
            result = m._issue_magic_ucan(self._payload(walletId=""))
        self.assertIn("token", result)


# ---------------------------------------------------------------------------
# _magic_login_payload_from_request
# ---------------------------------------------------------------------------
class TestMagicLoginPayloadFromRequest(unittest.TestCase):
    """Tests for the magic login request → payload dict conversion."""

    def _req(self, **kw):
        defaults = {
            "portal": "client",
            "contact": "user@example.com",
            "wallet_id": "wallet-abc",
            "wallet_api_base_url": "https://wallet.example.com",
            "actor_did": "did:abby:actor:123",
        }
        defaults.update(kw)
        return SimpleNamespace(**defaults)

    def test_returns_dict_with_version(self):
        m = _mod()
        result = m._magic_login_payload_from_request(self._req())
        self.assertEqual(result["v"], 1)

    def test_portal_client_accepted(self):
        m = _mod()
        result = m._magic_login_payload_from_request(self._req(portal="client"))
        self.assertEqual(result["portal"], "client")

    def test_portal_provider_accepted(self):
        m = _mod()
        result = m._magic_login_payload_from_request(self._req(portal="provider"))
        self.assertEqual(result["portal"], "provider")

    def test_invalid_portal_raises(self):
        m = _mod()
        with self.assertRaises(ValueError):
            m._magic_login_payload_from_request(self._req(portal="admin"))

    def test_contact_is_normalized_email(self):
        m = _mod()
        result = m._magic_login_payload_from_request(self._req(contact="User@Example.COM"))
        self.assertEqual(result["contact"], "user@example.com")

    def test_wallet_id_preserved(self):
        m = _mod()
        result = m._magic_login_payload_from_request(self._req(wallet_id="wlt-xyz"))
        self.assertEqual(result["walletId"], "wlt-xyz")

    def test_expires_at_after_issued_at(self):
        m = _mod()
        result = m._magic_login_payload_from_request(self._req())
        self.assertGreater(result["expiresAt"], result["issuedAt"])

    def test_nonce_is_nonempty_string(self):
        m = _mod()
        result = m._magic_login_payload_from_request(self._req())
        self.assertIsInstance(result["nonce"], str)
        self.assertTrue(len(result["nonce"]) > 0)

    def test_nonce_different_each_call(self):
        m = _mod()
        r1 = m._magic_login_payload_from_request(self._req())
        r2 = m._magic_login_payload_from_request(self._req())
        self.assertNotEqual(r1["nonce"], r2["nonce"])

    def test_custom_ttl_respected(self):
        m = _mod()
        with patch.dict(os.environ, {"WALLET_MAGIC_LOGIN_TTL_SECONDS": "120"}):
            result = m._magic_login_payload_from_request(self._req())
        delta_ms = result["expiresAt"] - result["issuedAt"]
        self.assertAlmostEqual(delta_ms, 120_000, delta=2000)

    def test_ttl_clamped_to_minimum(self):
        m = _mod()
        with patch.dict(os.environ, {"WALLET_MAGIC_LOGIN_TTL_SECONDS": "5"}):
            result = m._magic_login_payload_from_request(self._req())
        delta_ms = result["expiresAt"] - result["issuedAt"]
        self.assertGreaterEqual(delta_ms, 60_000)

    def test_ttl_clamped_to_maximum(self):
        m = _mod()
        with patch.dict(os.environ, {"WALLET_MAGIC_LOGIN_TTL_SECONDS": "9999"}):
            result = m._magic_login_payload_from_request(self._req())
        delta_ms = result["expiresAt"] - result["issuedAt"]
        self.assertLessEqual(delta_ms, 3_600_000 + 2000)


# ---------------------------------------------------------------------------
# _wallet_config_from_magic_payload
# ---------------------------------------------------------------------------
class TestWalletConfigFromMagicPayload(unittest.TestCase):
    """Tests for extracting optional wallet config keys from a payload dict."""

    def test_full_payload_returns_all_keys(self):
        m = _mod()
        payload = {
            "walletId": "wlt-123",
            "walletApiBaseUrl": "https://wallet.example.com",
            "actorDid": "did:abby:actor:xyz",
        }
        result = m._wallet_config_from_magic_payload(payload)
        self.assertEqual(result["walletId"], "wlt-123")
        self.assertEqual(result["apiBaseUrl"], "https://wallet.example.com")
        self.assertEqual(result["actorDid"], "did:abby:actor:xyz")

    def test_empty_wallet_id_omitted(self):
        m = _mod()
        result = m._wallet_config_from_magic_payload({"walletId": ""})
        self.assertNotIn("walletId", result)

    def test_empty_api_base_url_omitted(self):
        m = _mod()
        result = m._wallet_config_from_magic_payload({"walletApiBaseUrl": ""})
        self.assertNotIn("apiBaseUrl", result)

    def test_empty_actor_did_omitted(self):
        m = _mod()
        result = m._wallet_config_from_magic_payload({"actorDid": ""})
        self.assertNotIn("actorDid", result)

    def test_none_values_omitted(self):
        m = _mod()
        result = m._wallet_config_from_magic_payload({"walletId": None, "actorDid": None})
        self.assertNotIn("walletId", result)
        self.assertNotIn("actorDid", result)

    def test_empty_payload_returns_empty_dict(self):
        m = _mod()
        result = m._wallet_config_from_magic_payload({})
        self.assertEqual(result, {})

    def test_whitespace_only_values_omitted(self):
        m = _mod()
        result = m._wallet_config_from_magic_payload({"walletId": "   "})
        self.assertNotIn("walletId", result)


# ---------------------------------------------------------------------------
# _require_magic_ucan
# ---------------------------------------------------------------------------
class TestRequireMagicUcan(unittest.TestCase):
    """Tests for the FastAPI-style UCAN authorization middleware."""

    def setUp(self):
        self._m = _mod()

    def _issue_token(self, wallet_id: str = "wallet-req") -> str:
        issued = int(time.time() * 1000)
        with _mock_secret():
            result = self._m._issue_magic_ucan({
                "contact": "user@example.com",
                "walletId": wallet_id,
                "expiresAt": issued + 600_000,
            })
        return result["token"]

    def _http_exc_status(self, exc) -> int:
        return getattr(exc, "status_code", None)

    def test_valid_ucan_returns_payload(self):
        m = self._m
        token = self._issue_token("wallet-req")
        with _mock_secret():
            result = m._require_magic_ucan(
                authorization="Bearer " + token,
                wallet_id="wallet-req",
                ability="wallet/login",
                resource="wallet://*",
            )
        self.assertIsNotNone(result)

    def test_missing_authorization_raises_401(self):
        m = self._m
        with _mock_secret():
            try:
                m._require_magic_ucan(
                    authorization=None,
                    wallet_id="wallet-req",
                    ability="wallet/login",
                    resource="wallet://*",
                )
                self.fail("Expected HTTPException")
            except Exception as exc:
                self.assertEqual(self._http_exc_status(exc), 401)

    def test_wrong_wallet_id_raises_403(self):
        m = self._m
        token = self._issue_token("wallet-right")
        with _mock_secret():
            try:
                m._require_magic_ucan(
                    authorization="Bearer " + token,
                    wallet_id="wallet-wrong",
                    ability="wallet/login",
                    resource="wallet://*",
                )
                self.fail("Expected HTTPException")
            except Exception as exc:
                self.assertEqual(self._http_exc_status(exc), 403)

    def test_capability_mismatch_raises_403(self):
        m = self._m
        token = self._issue_token("wallet-req")
        with _mock_secret():
            try:
                m._require_magic_ucan(
                    authorization="Bearer " + token,
                    wallet_id="wallet-req",
                    ability="wallet/admin",  # not in issued capabilities
                    resource="wallet://*",
                )
                self.fail("Expected HTTPException")
            except Exception as exc:
                self.assertEqual(self._http_exc_status(exc), 403)

    def test_expired_token_raises_401(self):
        m = self._m
        issued = int(time.time() * 1000)
        payload = {
            "profile": m._MAGIC_UCAN_CONTEXT,  # type: ignore[attr-defined]
            "iss": "did:abby:issuer",
            "aud": "did:abby:contact:abc",
            "walletId": "wallet-req",
            "expiresAt": issued - 1000,  # already expired
            "capabilities": [{"with": "wallet://*", "can": "wallet/login"}],
            "nonce": "n",
        }
        with _mock_secret():
            expired_token = m._sign_magic_ucan(payload)
            try:
                m._require_magic_ucan(
                    authorization="Bearer " + expired_token,
                    wallet_id="wallet-req",
                    ability="wallet/login",
                    resource="wallet://*",
                )
                self.fail("Expected HTTPException")
            except Exception as exc:
                self.assertEqual(self._http_exc_status(exc), 401)

    def test_wildcard_resource_matches(self):
        m = self._m
        token = self._issue_token("wallet-req")
        with _mock_secret():
            # "wallet/login" capability has resource "wallet://*" — should match specific wallet
            result = m._require_magic_ucan(
                authorization="Bearer " + token,
                wallet_id="wallet-req",
                ability="wallet/login",
                resource="wallet://wallet-req",
            )
        self.assertIsNotNone(result)


if __name__ == "__main__":
    unittest.main()
