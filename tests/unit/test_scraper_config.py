"""Unit tests for scraper/config.py — no network access required."""

from __future__ import annotations

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


def test_config_service_categories_non_empty():
    from scraper import config  # noqa: PLC0415

    assert isinstance(config.SERVICE_CATEGORIES, list)
    assert len(config.SERVICE_CATEGORIES) > 0


def test_config_coverage_zips_non_empty():
    from scraper import config  # noqa: PLC0415

    assert isinstance(config.COVERAGE_ZIPS, list)
    assert len(config.COVERAGE_ZIPS) > 0
    # Each entry should be a 5-digit ZIP string
    assert all(z.isdigit() and len(z) == 5 for z in config.COVERAGE_ZIPS[:5])


def test_config_default_headers_contain_accept():
    from scraper import config  # noqa: PLC0415

    assert "Accept" in config.DEFAULT_HEADERS


def test_config_raw_dir_under_data_dir():
    from scraper import config  # noqa: PLC0415

    assert config.RAW_DIR.is_relative_to(config.DATA_DIR)


def test_config_processed_dir_under_data_dir():
    from scraper import config  # noqa: PLC0415

    assert config.PROCESSED_DIR.is_relative_to(config.DATA_DIR)


def test_config_gethelp_url_is_https():
    from scraper import config  # noqa: PLC0415

    assert config.GETHELP_URL.startswith("https://")


def test_config_instance_overrides_base_url():
    from scraper.config import Config  # noqa: PLC0415

    cfg = Config(base_url="https://example.com")
    assert cfg.base_url == "https://example.com"


def test_config_instance_rejects_unknown_key():
    from scraper.config import Config  # noqa: PLC0415

    with pytest.raises(ValueError, match="Unknown config key"):
        Config(nonexistent_setting=True)


def test_config_env_override_delay(monkeypatch):
    import importlib  # noqa: PLC0415

    import scraper.config as cfg_mod  # noqa: PLC0415

    monkeypatch.setenv("SCRAPER_DELAY", "3.7")
    importlib.reload(cfg_mod)
    try:
        assert cfg_mod.REQUEST_DELAY_SECONDS == pytest.approx(3.7)
    finally:
        monkeypatch.delenv("SCRAPER_DELAY", raising=False)
        importlib.reload(cfg_mod)


def test_config_env_override_max_retries(monkeypatch):
    import importlib  # noqa: PLC0415

    import scraper.config as cfg_mod  # noqa: PLC0415

    monkeypatch.setenv("SCRAPER_MAX_RETRIES", "7")
    importlib.reload(cfg_mod)
    try:
        assert cfg_mod.MAX_RETRIES == 7
    finally:
        monkeypatch.delenv("SCRAPER_MAX_RETRIES", raising=False)
        importlib.reload(cfg_mod)
