"""Unit tests for scraper/config.py — no network access required."""

from __future__ import annotations

import os
from pathlib import Path

import pytest


def test_config_importable():
    from scraper.config import Config  # noqa: PLC0415

    assert Config is not None


def test_config_data_dir_is_path():
    from scraper import config  # noqa: PLC0415

    assert isinstance(config.DATA_DIR, Path)


def test_config_base_url_is_non_empty_string():
    from scraper import config  # noqa: PLC0415

    assert isinstance(config.BASE_URL, str)
    assert config.BASE_URL.startswith("http")


def test_config_static_pages_is_list():
    from scraper import config  # noqa: PLC0415

    assert isinstance(config.STATIC_PAGES, list)
    assert len(config.STATIC_PAGES) > 0


def test_config_concurrent_pages_positive(monkeypatch):
    monkeypatch.delenv("SCRAPER_CONCURRENT_PAGES", raising=False)
    from scraper import config  # noqa: PLC0415

    assert config.CONCURRENT_PAGES >= 1
