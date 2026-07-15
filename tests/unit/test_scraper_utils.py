"""Unit tests for scraper/utils.py — pure-function helpers with no I/O."""

from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# clean_text
# ---------------------------------------------------------------------------

def test_clean_text_none_returns_empty():
    from scraper.utils import clean_text  # noqa: PLC0415

    assert clean_text(None) == ""


def test_clean_text_collapses_whitespace():
    from scraper.utils import clean_text  # noqa: PLC0415

    assert clean_text("  hello   world  ") == "hello world"


def test_clean_text_normalizes_unicode():
    from scraper.utils import clean_text  # noqa: PLC0415

    # NFKC normalisation: fullwidth space → ASCII space
    result = clean_text("hello\u3000world")
    assert result == "hello world"


def test_extract_phone_basic():
    from scraper.utils import extract_phone  # noqa: PLC0415

    assert extract_phone("Call us at (503) 555-1234 today") == "(503) 555-1234"


def test_extract_phone_no_match_returns_none():
    from scraper.utils import extract_phone  # noqa: PLC0415

    assert extract_phone("no phone here") is None


def test_extract_zip_basic():
    from scraper.utils import extract_zip  # noqa: PLC0415

    assert extract_zip("Portland, OR 97201") == "97201"


def test_extract_zip_plus_four():
    from scraper.utils import extract_zip  # noqa: PLC0415

    assert extract_zip("97201-4567 is the ZIP") == "97201"


def test_extract_zip_no_match_returns_none():
    from scraper.utils import extract_zip  # noqa: PLC0415

    assert extract_zip("no ZIP code here") is None


# ---------------------------------------------------------------------------
# normalise_url
# ---------------------------------------------------------------------------

def test_normalise_url_absolute_passthrough():
    from scraper.utils import normalise_url  # noqa: PLC0415

    url = "https://www.211info.org/about/"
    assert normalise_url(url, "https://www.211info.org") == url


def test_normalise_url_relative_resolved():
    from scraper.utils import normalise_url  # noqa: PLC0415

    result = normalise_url("/programs/", "https://www.211info.org")
    assert result == "https://www.211info.org/programs/"


def test_normalise_url_strips_fragment():
    from scraper.utils import normalise_url  # noqa: PLC0415

    result = normalise_url("https://www.211info.org/about/#section", "https://www.211info.org")
    assert "#" not in result
    assert result == "https://www.211info.org/about/"


def test_normalise_url_empty_returns_empty():
    from scraper.utils import normalise_url  # noqa: PLC0415

    assert normalise_url("", "https://www.211info.org") == ""


def test_normalise_url_hash_anchor_returns_empty():
    from scraper.utils import normalise_url  # noqa: PLC0415

    assert normalise_url("#top", "https://www.211info.org") == ""


def test_normalise_url_javascript_returns_empty():
    from scraper.utils import normalise_url  # noqa: PLC0415

    assert normalise_url("javascript:void(0)", "https://www.211info.org") == ""


def test_normalise_url_mailto_returns_empty():
    from scraper.utils import normalise_url  # noqa: PLC0415

    assert normalise_url("mailto:info@211info.org", "https://www.211info.org") == ""


# ---------------------------------------------------------------------------
# same_domain
# ---------------------------------------------------------------------------

def test_same_domain_identical_origins():
    from scraper.utils import same_domain  # noqa: PLC0415

    assert same_domain("https://www.211info.org/about/", "https://www.211info.org") is True


def test_same_domain_www_stripped():
    from scraper.utils import same_domain  # noqa: PLC0415

    assert same_domain("https://211info.org/contact/", "https://www.211info.org") is True


def test_same_domain_subdomain_allowed():
    from scraper.utils import same_domain  # noqa: PLC0415

    assert same_domain("https://gethelp.211info.org/search", "https://www.211info.org") is True


def test_same_domain_different_domain_rejected():
    from scraper.utils import same_domain  # noqa: PLC0415

    assert same_domain("https://example.com/page", "https://www.211info.org") is False


# ---------------------------------------------------------------------------
# setup_logging
# ---------------------------------------------------------------------------


class TestSetupLogging:
    def test_returns_logger(self):
        from scraper.utils import setup_logging
        import logging
        logger = setup_logging()
        assert isinstance(logger, logging.Logger)

    def test_logger_name_is_scraper(self):
        from scraper.utils import setup_logging
        logger = setup_logging()
        assert logger.name == "scraper"

    def test_idempotent_second_call(self):
        from scraper.utils import setup_logging
        logger1 = setup_logging()
        logger2 = setup_logging()
        assert logger1 is logger2


# ---------------------------------------------------------------------------
# with_retry decorator
# ---------------------------------------------------------------------------


class TestWithRetry:
    def test_returns_callable(self):
        from scraper.utils import with_retry
        decorator = with_retry(max_attempts=2, base_wait=0.0)
        assert callable(decorator)

    def test_wraps_function(self):
        from scraper.utils import with_retry

        @with_retry(max_attempts=1, base_wait=0.0)
        def my_func():
            return 42

        assert my_func() == 42

    def test_retries_on_exception(self):
        from scraper.utils import with_retry

        attempts = []

        @with_retry(max_attempts=3, base_wait=0.0)
        def sometimes_fails():
            attempts.append(1)
            if len(attempts) < 3:
                raise ValueError("not ready yet")
            return "done"

        result = sometimes_fails()
        assert result == "done"
        assert len(attempts) == 3

    def test_raises_after_max_attempts(self):
        import pytest
        from scraper.utils import with_retry

        @with_retry(max_attempts=2, base_wait=0.0)
        def always_fails():
            raise RuntimeError("always fails")

        with pytest.raises(RuntimeError, match="always fails"):
            always_fails()
