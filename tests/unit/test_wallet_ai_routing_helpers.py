"""Unit tests for wallet_interface/helpers/_ai_routing.py pure helpers.

All tests run without optional dependencies.
"""
from __future__ import annotations

import os
import time
import unittest


class TestWalletRouterSubject(unittest.TestCase):
    def setUp(self):
        from wallet_interface.helpers._ai_routing import _wallet_router_subject

        self._fn = _wallet_router_subject

    def test_returns_wallet_id_slug_when_no_cid(self):
        result = self._fn("wallet-123", None)
        self.assertIn("wallet-123", result)

    def test_uses_valid_ipfs_cid_when_provided(self):
        cid = "bafybeihdwdcefgh4dqkjv67uzcmw7ojee6xedzdetojuzjevtenxquvyku"
        result = self._fn("wallet-123", cid)
        self.assertEqual(result, cid)

    def test_sanitizes_non_cid_wallet_cid(self):
        result = self._fn("wallet-123", "some/special chars!")
        self.assertNotIn("/", result)
        self.assertNotIn("!", result)

    def test_result_max_length(self):
        long_id = "x" * 200
        result = self._fn(long_id, None)
        self.assertLessEqual(len(result), 160)

    def test_empty_wallet_id_uses_unknown(self):
        result = self._fn("", None)
        self.assertIn("unknown-wallet", result)

    def test_returns_string(self):
        result = self._fn("abc", "xyz")
        self.assertIsInstance(result, str)


class TestWalletRouterRateLimits(unittest.TestCase):
    def setUp(self):
        from wallet_interface.helpers._ai_routing import (
            _wallet_router_rate_limit_per_day,
            _wallet_router_rate_limit_per_minute,
        )

        self._per_minute = _wallet_router_rate_limit_per_minute
        self._per_day = _wallet_router_rate_limit_per_day

    def test_per_minute_default(self):
        os.environ.pop("WALLET_AI_ROUTER_RATE_LIMIT_PER_MINUTE", None)
        self.assertEqual(self._per_minute(), 30)

    def test_per_day_default(self):
        os.environ.pop("WALLET_AI_ROUTER_RATE_LIMIT_PER_DAY", None)
        self.assertEqual(self._per_day(), 500)

    def test_per_minute_env_override(self):
        os.environ["WALLET_AI_ROUTER_RATE_LIMIT_PER_MINUTE"] = "10"
        try:
            self.assertEqual(self._per_minute(), 10)
        finally:
            del os.environ["WALLET_AI_ROUTER_RATE_LIMIT_PER_MINUTE"]

    def test_per_day_env_override(self):
        os.environ["WALLET_AI_ROUTER_RATE_LIMIT_PER_DAY"] = "100"
        try:
            self.assertEqual(self._per_day(), 100)
        finally:
            del os.environ["WALLET_AI_ROUTER_RATE_LIMIT_PER_DAY"]

    def test_per_minute_minimum_is_one(self):
        os.environ["WALLET_AI_ROUTER_RATE_LIMIT_PER_MINUTE"] = "0"
        try:
            self.assertEqual(self._per_minute(), 1)
        finally:
            del os.environ["WALLET_AI_ROUTER_RATE_LIMIT_PER_MINUTE"]

    def test_per_minute_invalid_falls_back(self):
        os.environ["WALLET_AI_ROUTER_RATE_LIMIT_PER_MINUTE"] = "not-a-number"
        try:
            self.assertEqual(self._per_minute(), 30)
        finally:
            del os.environ["WALLET_AI_ROUTER_RATE_LIMIT_PER_MINUTE"]


class TestCheckWalletRouterRateLimit(unittest.TestCase):
    def setUp(self):
        from wallet_interface.helpers._ai_routing import (
            _AI_ROUTER_RATE_LIMITS,
            _check_wallet_router_rate_limit,
        )

        self._fn = _check_wallet_router_rate_limit
        self._limits = _AI_ROUTER_RATE_LIMITS
        # Clean up any stale state from other tests
        self._limits.clear()

    def test_returns_rate_limit_info(self):
        result = self._fn("test-subject-1")
        self.assertIn("subject", result)
        self.assertIn("minuteLimit", result)
        self.assertIn("dayLimit", result)
        self.assertIn("minuteRemaining", result)
        self.assertIn("dayRemaining", result)

    def test_decrements_remaining_on_each_call(self):
        os.environ["WALLET_AI_ROUTER_RATE_LIMIT_PER_MINUTE"] = "10"
        os.environ["WALLET_AI_ROUTER_RATE_LIMIT_PER_DAY"] = "100"
        self._limits.clear()
        try:
            r1 = self._fn("test-subject-2")
            r2 = self._fn("test-subject-2")
            self.assertEqual(r2["minuteRemaining"], r1["minuteRemaining"] - 1)
        finally:
            del os.environ["WALLET_AI_ROUTER_RATE_LIMIT_PER_MINUTE"]
            del os.environ["WALLET_AI_ROUTER_RATE_LIMIT_PER_DAY"]

    def test_raises_when_per_minute_exceeded(self):
        os.environ["WALLET_AI_ROUTER_RATE_LIMIT_PER_MINUTE"] = "2"
        os.environ["WALLET_AI_ROUTER_RATE_LIMIT_PER_DAY"] = "1000"
        self._limits.clear()
        try:
            self._fn("test-subject-3")
            self._fn("test-subject-3")
            with self.assertRaises(ValueError):
                self._fn("test-subject-3")
        finally:
            del os.environ["WALLET_AI_ROUTER_RATE_LIMIT_PER_MINUTE"]
            del os.environ["WALLET_AI_ROUTER_RATE_LIMIT_PER_DAY"]

    def test_cost_counted_correctly(self):
        os.environ["WALLET_AI_ROUTER_RATE_LIMIT_PER_MINUTE"] = "10"
        os.environ["WALLET_AI_ROUTER_RATE_LIMIT_PER_DAY"] = "100"
        self._limits.clear()
        try:
            r = self._fn("test-subject-4", cost=3)
            self.assertEqual(r["minuteRemaining"], 7)
        finally:
            del os.environ["WALLET_AI_ROUTER_RATE_LIMIT_PER_MINUTE"]
            del os.environ["WALLET_AI_ROUTER_RATE_LIMIT_PER_DAY"]

    def test_uses_unknown_wallet_for_empty_subject(self):
        self._limits.clear()
        result = self._fn("")
        self.assertEqual(result["subject"], "unknown-wallet")

    def tearDown(self):
        os.environ.pop("WALLET_AI_ROUTER_RATE_LIMIT_PER_MINUTE", None)
        os.environ.pop("WALLET_AI_ROUTER_RATE_LIMIT_PER_DAY", None)
        self._limits.clear()


class TestAnalysisResultToDict(unittest.TestCase):
    def setUp(self):
        from wallet_interface.helpers._ai_routing import _analysis_result_to_dict

        self._fn = _analysis_result_to_dict

    def test_converts_artifact_with_to_dict(self):
        class MockArtifact:
            def to_dict(self):
                return {"id": "abc"}

        result = self._fn({"artifact": MockArtifact(), "output": {"key": "val"}})
        self.assertEqual(result["artifact"]["id"], "abc")
        self.assertEqual(result["output"]["key"], "val")

    def test_converts_artifact_without_to_dict(self):
        result = self._fn({"artifact": {"id": "xyz"}, "output": {"x": 1}})
        self.assertEqual(result["artifact"]["id"], "xyz")


if __name__ == "__main__":
    unittest.main()
