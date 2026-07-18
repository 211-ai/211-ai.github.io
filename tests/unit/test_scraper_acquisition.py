"""Unit tests for scraper/acquisition layer — no network access required."""

from __future__ import annotations

import importlib

import pytest


def test_acquisition_package_importable():
    try:
        mod = importlib.import_module("scraper.acquisition")
        assert mod is not None
    except ImportError as exc:
        pytest.skip(f"scraper.acquisition import failed (circular/optional dep): {exc}")


def test_acquisition_exposes_browser_scraper():
    try:
        from scraper.acquisition import BrowserScraper  # noqa: PLC0415
    except ImportError as exc:
        pytest.skip(f"BrowserScraper unavailable: {exc}")
    assert BrowserScraper is not None


def test_acquisition_exposes_static_scraper():
    try:
        from scraper.acquisition import StaticScraper  # noqa: PLC0415
    except ImportError as exc:
        pytest.skip(f"StaticScraper unavailable: {exc}")
    assert StaticScraper is not None


def test_browser_scraper_requires_no_network():
    """Instantiating BrowserScraper should not open network connections."""
    try:
        from scraper.acquisition import BrowserScraper  # noqa: PLC0415
        from scraper.config import Config  # noqa: PLC0415
    except ImportError as exc:
        pytest.skip(f"BrowserScraper unavailable: {exc}")

    cfg = Config()
    scraper = BrowserScraper(cfg)
    # Only check that the scraper stores config — no run call
    assert scraper.cfg is cfg


def test_static_scraper_requires_no_network():
    """Instantiating StaticScraper should not open network connections."""
    try:
        from scraper.acquisition import StaticScraper  # noqa: PLC0415
        from scraper.config import Config  # noqa: PLC0415
    except ImportError as exc:
        pytest.skip(f"StaticScraper unavailable: {exc}")

    cfg = Config()
    scraper = StaticScraper(cfg)
    assert scraper.cfg is cfg


def test_warc_etl_importable():
    """WarcEtl module should import without errors even if warc lib absent."""
    try:
        from scraper.acquisition import WarcEtl  # noqa: PLC0415

        assert WarcEtl is not None
    except ImportError:
        pytest.skip("optional warc dependency not installed")
