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
