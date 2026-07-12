"""Unit tests for scraper/utils.py — pure-function helpers with no I/O."""

from __future__ import annotations

import pytest


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
