"""Unit tests for auth helper functions not covered by test_wallet_auth_helpers.py
or test_wallet_auth_crypto.py — specifically _capability_resource_matches,
_magic_contact_subject_did, _magic_ucan_capabilities, _magic_login_base_url,
and _build_magic_login_link."""

from __future__ import annotations

import importlib
import os
import unittest


class TestCapabilityResourceMatches(unittest.TestCase):
    """Tests for _capability_resource_matches."""

    def setUp(self):
        from wallet_interface.helpers._auth import _capability_resource_matches

        self.match = _capability_resource_matches

    def test_exact_match(self):
        assert self.match("wallet/123", "wallet/123") is True

    def test_glob_wildcard_matches(self):
        assert self.match("wallet/*", "wallet/123") is True

    def test_glob_wildcard_no_match_different_prefix(self):
        assert self.match("wallet/*", "other/123") is False

    def test_universal_wildcard(self):
        assert self.match("*", "anything/goes") is True

    def test_exact_no_match(self):
        assert self.match("wallet/abc", "wallet/xyz") is False

    def test_empty_resource_not_matched_by_prefix(self):
        assert self.match("wallet/*", "") is False


class TestMagicContactSubjectDid(unittest.TestCase):
    """Tests for _magic_contact_subject_did."""

    def setUp(self):
        from wallet_interface.helpers._auth import _magic_contact_subject_did

        self.subject = _magic_contact_subject_did

    def test_returns_did_string(self):
        result = self.subject("user@example.org")
        assert result.startswith("did:abby:contact:")

    def test_deterministic(self):
        a = self.subject("user@example.org")
        b = self.subject("user@example.org")
        assert a == b

    def test_different_contacts_produce_different_dids(self):
        a = self.subject("alice@example.org")
        b = self.subject("bob@example.org")
        assert a != b


class TestMagicUcanCapabilities(unittest.TestCase):
    """Tests for _magic_ucan_capabilities."""

    def setUp(self):
        from wallet_interface.helpers._auth import _magic_ucan_capabilities

        self.caps = _magic_ucan_capabilities

    def test_returns_list(self):
        result = self.caps("wallet-abc")
        assert isinstance(result, list)

    def test_contains_login_capability(self):
        result = self.caps("wallet-abc")
        cans = [c["can"] for c in result]
        assert "wallet/login" in cans

    def test_capabilities_reference_wallet_id(self):
        result = self.caps("wallet-xyz")
        resources = [c["with"] for c in result]
        # at least one resource should reference the wallet id
        assert any("wallet-xyz" in r for r in resources)

    def test_all_items_have_with_and_can(self):
        result = self.caps("wallet-123")
        for cap in result:
            assert "with" in cap
            assert "can" in cap


class TestMagicLoginBaseUrl(unittest.TestCase):
    """Tests for _magic_login_base_url."""

    def _reload_auth(self):
        import wallet_interface.helpers._auth as m

        importlib.reload(m)
        return m._magic_login_base_url

    def test_allowed_host_returns_url(self):
        os.environ["WALLET_MAGIC_LOGIN_ALLOWED_HOSTS"] = "example.com"
        fn = self._reload_auth()
        result = fn("https://example.com/login/path")
        assert result == "https://example.com/login/path"

    def test_disallowed_host_raises(self):
        os.environ["WALLET_MAGIC_LOGIN_ALLOWED_HOSTS"] = "allowed.com"
        fn = self._reload_auth()
        with self.assertRaises(ValueError):
            fn("https://evil.com/login")

    def tearDown(self):
        os.environ.pop("WALLET_MAGIC_LOGIN_ALLOWED_HOSTS", None)


class TestBuildMagicLoginLink(unittest.TestCase):
    """Tests for _build_magic_login_link."""

    def setUp(self):
        from wallet_interface.helpers._auth import _build_magic_login_link

        self.build = _build_magic_login_link

    def test_token_appended_as_query(self):
        link = self.build(token="mytoken", base_url="https://example.com")
        assert "mytoken" in link
        assert "abbyLogin" in link

    def test_link_starts_with_base_url(self):
        link = self.build(token="tok", base_url="https://example.com/path")
        assert link.startswith("https://example.com/path")

    def test_hash_fragment_present(self):
        link = self.build(token="tok", base_url="https://example.com")
        assert "#" in link


if __name__ == "__main__":
    unittest.main()
