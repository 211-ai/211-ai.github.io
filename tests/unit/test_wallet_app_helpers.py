"""Unit tests for wallet_interface/helpers/_app.py pure helpers."""

from __future__ import annotations

import json
import os
from unittest.mock import patch


def _import():
    from wallet_interface.helpers import _app as m
    return m


class TestIpfsProxyAllowsCid:
    def _fn(self):
        return _import()._ipfs_proxy_allows_cid

    def test_allows_all_when_no_restriction(self):
        fn = self._fn()
        with patch.dict(os.environ, {"WALLET_IPFS_PROXY_ALLOWED_CIDS": ""}):
            assert fn("bafybeiabc123") is True

    def test_allows_configured_cid(self):
        fn = self._fn()
        cid = "bafybeiabc123def"
        with patch.dict(os.environ, {"WALLET_IPFS_PROXY_ALLOWED_CIDS": cid}):
            assert fn(cid) is True

    def test_blocks_unconfigured_cid(self):
        fn = self._fn()
        with patch.dict(os.environ, {"WALLET_IPFS_PROXY_ALLOWED_CIDS": "bafybeiabc123"}):
            assert fn("bafybeiXYZ999") is False

    def test_normalizes_cid_for_comparison(self):
        fn = self._fn()
        cid = "bafybeiabc123"
        with patch.dict(os.environ, {"WALLET_IPFS_PROXY_ALLOWED_CIDS": cid}):
            # With ipfs:// prefix should still work
            assert fn(f"ipfs://{cid}") is True

    def test_comma_separated_allowed_cids(self):
        fn = self._fn()
        with patch.dict(os.environ, {"WALLET_IPFS_PROXY_ALLOWED_CIDS": "bafybeiabc,bafybeidef"}):
            assert fn("bafybeiabc") is True
            assert fn("bafybeidef") is True
            assert fn("bafybeighi") is False


class TestIpfsProxyMediaType:
    def _fn(self):
        return _import()._ipfs_proxy_media_type

    def test_json_bytes_returns_application_json(self):
        fn = self._fn()
        data = json.dumps({"key": "value"}).encode("utf-8")
        assert fn(data) == "application/json"

    def test_binary_bytes_returns_octet_stream(self):
        fn = self._fn()
        assert fn(b"\x00\x01\x02\x03") == "application/octet-stream"

    def test_json_array_returns_application_json(self):
        fn = self._fn()
        data = json.dumps([1, 2, 3]).encode("utf-8")
        assert fn(data) == "application/json"

    def test_invalid_json_returns_octet_stream(self):
        fn = self._fn()
        assert fn(b"not json at all") == "application/octet-stream"

    def test_empty_bytes_returns_octet_stream(self):
        fn = self._fn()
        assert fn(b"") == "application/octet-stream"


class TestIpfsProxyFallbackGateways:
    def _fn(self):
        return _import()._ipfs_proxy_fallback_gateways

    def test_default_gateways(self):
        fn = self._fn()
        with patch.dict(os.environ, {"WALLET_IPFS_PROXY_FALLBACK_GATEWAYS": ""}):
            gateways = fn()
        assert any("w3s.link" in g for g in gateways)
        assert any("ipfs.io" in g for g in gateways)

    def test_custom_gateways(self):
        fn = self._fn()
        with patch.dict(os.environ, {"WALLET_IPFS_PROXY_FALLBACK_GATEWAYS": "https://my-gateway.com/ipfs,https://other.com/ipfs"}):
            gateways = fn()
        assert "https://my-gateway.com/ipfs" in gateways
        assert "https://other.com/ipfs" in gateways

    def test_returns_list(self):
        fn = self._fn()
        assert isinstance(fn(), list)

    def test_gateways_have_no_trailing_slash(self):
        fn = self._fn()
        with patch.dict(os.environ, {"WALLET_IPFS_PROXY_FALLBACK_GATEWAYS": ""}):
            for gateway in fn():
                assert not gateway.endswith("/")


class TestOpsHealthSharedSecret:
    def _fn(self):
        return _import()._ops_health_shared_secret

    def test_returns_empty_when_not_set(self):
        fn = self._fn()
        with patch.dict(os.environ, {"WALLET_OPS_HEALTH_SHARED_SECRET": ""}):
            assert fn() == ""

    def test_returns_configured_secret(self):
        fn = self._fn()
        with patch.dict(os.environ, {"WALLET_OPS_HEALTH_SHARED_SECRET": "my-secret"}):
            assert fn() == "my-secret"

    def test_strips_whitespace(self):
        fn = self._fn()
        with patch.dict(os.environ, {"WALLET_OPS_HEALTH_SHARED_SECRET": "  secret  "}):
            assert fn() == "secret"
