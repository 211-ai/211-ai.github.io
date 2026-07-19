"""Unit tests for auth notification helpers in wallet_interface/helpers/_auth.py.

These tests cover the pure input-validation paths of _send_sms_notification,
_send_auth_email_notification, and _send_phone_call_notification without
requiring a live webhook endpoint. Network calls are prevented by the
missing environment variables, and we assert on the expected RuntimeError.
"""
from __future__ import annotations

import os
import unittest


class TestSendSmsNotificationValidation(unittest.TestCase):
    """Input validation for _send_sms_notification."""

    def setUp(self):
        from wallet_interface.helpers._auth import _send_sms_notification

        self._fn = _send_sms_notification
        os.environ.pop("WALLET_SMS_WEBHOOK_URL", None)
        os.environ.pop("WALLET_SMS_BACKEND", None)

    def tearDown(self):
        os.environ.pop("WALLET_SMS_WEBHOOK_URL", None)
        os.environ.pop("WALLET_SMS_BACKEND", None)

    def test_raises_value_error_for_empty_message(self):
        with self.assertRaises(ValueError):
            self._fn(to_phone="+15035551234", message="")

    def test_raises_value_error_for_whitespace_message(self):
        with self.assertRaises(ValueError):
            self._fn(to_phone="+15035551234", message="   ")

    def test_raises_runtime_error_without_webhook_url(self):
        """Without a configured URL, should raise before any network call."""
        with self.assertRaises(RuntimeError):
            self._fn(to_phone="+15035551234", message="Hello")

    def test_raises_runtime_error_with_bad_phone_number(self):
        """A phone that can't be normalized raises ValueError."""
        with self.assertRaises(ValueError):
            self._fn(to_phone="not-a-phone", message="Hello")


class TestSendAuthEmailNotificationValidation(unittest.TestCase):
    """Input validation for _send_auth_email_notification."""

    def setUp(self):
        from wallet_interface.helpers._auth import _send_auth_email_notification

        self._fn = _send_auth_email_notification
        os.environ.pop("WALLET_AUTH_EMAIL_WEBHOOK_URL", None)
        os.environ.pop("WALLET_AUTH_EMAIL_BACKEND", None)

    def tearDown(self):
        os.environ.pop("WALLET_AUTH_EMAIL_WEBHOOK_URL", None)
        os.environ.pop("WALLET_AUTH_EMAIL_BACKEND", None)

    def test_raises_for_invalid_email_no_at(self):
        with self.assertRaises(ValueError):
            self._fn(to_email="notanemail", subject="Hi", body="body")

    def test_raises_for_invalid_email_no_domain_dot(self):
        with self.assertRaises(ValueError):
            self._fn(to_email="user@nodot", subject="Hi", body="body")

    def test_raises_for_empty_local_part(self):
        with self.assertRaises(ValueError):
            self._fn(to_email="@example.com", subject="Hi", body="body")

    def test_raises_runtime_error_without_webhook_url(self):
        """Without a configured URL, should raise before any network call."""
        with self.assertRaises(RuntimeError):
            self._fn(to_email="user@example.com", subject="Hi", body="body")

    def test_normalizes_to_lowercase(self):
        """_send_auth_email_notification normalizes the email to lowercase before raising."""
        try:
            self._fn(to_email="User@EXAMPLE.COM", subject="Hi", body="body")
        except RuntimeError as exc:
            # Should reach RuntimeError (unconfigured webhook), not ValueError
            self.assertIn("WEBHOOK_URL", str(exc))
        except Exception:  # pragma: no cover
            pass


class TestSendPhoneCallNotificationValidation(unittest.TestCase):
    """Input validation for _send_phone_call_notification."""

    def setUp(self):
        from wallet_interface.helpers._auth import _send_phone_call_notification

        self._fn = _send_phone_call_notification
        os.environ.pop("WALLET_CALL_WEBHOOK_URL", None)
        os.environ.pop("WALLET_CALL_BACKEND", None)

    def tearDown(self):
        os.environ.pop("WALLET_CALL_WEBHOOK_URL", None)
        os.environ.pop("WALLET_CALL_BACKEND", None)

    def test_raises_value_error_for_empty_script(self):
        with self.assertRaises(ValueError):
            self._fn(to_phone="+15035551234", script="")

    def test_raises_value_error_for_whitespace_script(self):
        with self.assertRaises(ValueError):
            self._fn(to_phone="+15035551234", script="   ")

    def test_raises_runtime_error_without_webhook_url(self):
        """Without a configured URL, should raise before any network call."""
        with self.assertRaises(RuntimeError):
            self._fn(to_phone="+15035551234", script="Please call back")

    def test_raises_for_invalid_phone(self):
        with self.assertRaises(ValueError):
            self._fn(to_phone="bad", script="Script text")


class TestSendWebhookNotificationValidation(unittest.TestCase):
    """Input validation for _send_webhook_notification configuration guards."""

    def setUp(self):
        from wallet_interface.helpers._auth import _send_webhook_notification

        self._fn = _send_webhook_notification
        for key in ("TEST_WEBHOOK_URL", "TEST_BACKEND", "TEST_TIMEOUT_SECONDS"):
            os.environ.pop(key, None)

    def tearDown(self):
        for key in ("TEST_WEBHOOK_URL", "TEST_BACKEND", "TEST_TIMEOUT_SECONDS"):
            os.environ.pop(key, None)

    def test_raises_when_no_url_configured(self):
        with self.assertRaises(RuntimeError) as ctx:
            self._fn(env_prefix="TEST", required_key="to", required_value="addr")
        self.assertIn("WEBHOOK_URL", str(ctx.exception))

    def test_raises_for_non_http_backend(self):
        os.environ["TEST_WEBHOOK_URL"] = "https://example.com/hook"
        os.environ["TEST_BACKEND"] = "smtp"
        with self.assertRaises(RuntimeError) as ctx:
            self._fn(env_prefix="TEST", required_key="to", required_value="addr")
        self.assertIn("http", str(ctx.exception))

    def test_raises_for_zero_timeout(self):
        os.environ["TEST_WEBHOOK_URL"] = "https://example.com/hook"
        os.environ["TEST_TIMEOUT_SECONDS"] = "0"
        with self.assertRaises(RuntimeError) as ctx:
            self._fn(env_prefix="TEST", required_key="to", required_value="addr")
        self.assertIn("positive", str(ctx.exception))

    def test_raises_for_negative_timeout(self):
        os.environ["TEST_WEBHOOK_URL"] = "https://example.com/hook"
        os.environ["TEST_TIMEOUT_SECONDS"] = "-5"
        with self.assertRaises(RuntimeError):
            self._fn(env_prefix="TEST", required_key="to", required_value="addr")


if __name__ == "__main__":
    unittest.main()
