"""
Unit tests for the 211info scraper package.

These tests do NOT make network requests; they test logic, parsing,
storage, processing, and configuration in isolation.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Config tests
# ---------------------------------------------------------------------------

def test_config_defaults():
    from scraper.config import Config, BASE_URL, SERVICE_CATEGORIES, COVERAGE_ZIPS

    cfg = Config()
    assert cfg.base_url == BASE_URL
    assert len(cfg.service_categories) > 0
    assert "food" in cfg.service_categories
    assert "housing-shelter" in cfg.service_categories
    assert len(cfg.coverage_zips) > 0
    assert cfg.request_delay > 0


def test_config_override():
    from scraper.config import Config

    cfg = Config(request_delay=2.0, headless=False)
    assert cfg.request_delay == 2.0
    assert cfg.headless is False


def test_config_unknown_key_raises():
    from scraper.config import Config

    with pytest.raises(ValueError, match="Unknown config key"):
        Config(nonexistent_key="value")


def test_config_creates_dirs(tmp_path):
    from scraper.config import Config

    raw = tmp_path / "raw"
    proc = tmp_path / "processed"
    assert not raw.exists()
    Config(raw_dir=raw, processed_dir=proc)
    assert raw.exists()
    assert proc.exists()


# ---------------------------------------------------------------------------
# Utils tests
# ---------------------------------------------------------------------------

def test_clean_text_basic():
    from scraper.utils import clean_text

    assert clean_text("  hello   world  ") == "hello world"
    assert clean_text(None) == ""
    assert clean_text("") == ""


def test_clean_text_unicode():
    from scraper.utils import clean_text

    assert clean_text("caf\u00e9") == "café"
    # Non-breaking space → space
    assert clean_text("a\u00a0b") == "a b"


def test_normalise_url_absolute():
    from scraper.utils import normalise_url

    url = normalise_url("https://www.211info.org/food", "https://www.211info.org")
    assert url == "https://www.211info.org/food"


def test_normalise_url_relative():
    from scraper.utils import normalise_url

    url = normalise_url("/about/", "https://www.211info.org")
    assert url == "https://www.211info.org/about/"


def test_normalise_url_strips_fragment():
    from scraper.utils import normalise_url

    url = normalise_url("/page#section", "https://www.211info.org")
    assert "#" not in url


def test_normalise_url_ignores_mailto():
    from scraper.utils import normalise_url

    assert normalise_url("mailto:test@example.com", "https://www.211info.org") == ""


def test_same_domain_true():
    from scraper.utils import same_domain

    assert same_domain("https://www.211info.org/about", "https://www.211info.org")
    assert same_domain("https://gethelp.211info.org/search", "https://211info.org")


def test_same_domain_false():
    from scraper.utils import same_domain

    assert not same_domain("https://example.com", "https://www.211info.org")


def test_extract_phone():
    from scraper.utils import extract_phone

    assert extract_phone("Call us at 503-282-0555 today") == "503-282-0555"
    assert extract_phone("(971) 123-4567") == "(971) 123-4567"
    assert extract_phone("no phone here") is None


def test_extract_zip():
    from scraper.utils import extract_zip

    assert extract_zip("Portland, OR 97201") == "97201"
    assert extract_zip("ZIP: 97401-1234") == "97401"
    assert extract_zip("no zip") is None


# ---------------------------------------------------------------------------
# Storage tests
# ---------------------------------------------------------------------------

def test_storage_save_load_json(tmp_path):
    from scraper.storage import Storage

    s = Storage(tmp_path / "raw", tmp_path / "proc")
    data = {"key": "value", "num": 42}
    s.save_json(data, "test.json")
    loaded = s.load_json("test.json")
    assert loaded == data


def test_storage_jsonl_append_and_load(tmp_path):
    from scraper.storage import Storage

    s = Storage(tmp_path / "raw", tmp_path / "proc")
    records = [{"id": "1", "name": "Alpha"}, {"id": "2", "name": "Beta"}]
    s.append_jsonl(records, "test.jsonl")
    # Append again
    s.append_jsonl([{"id": "3", "name": "Gamma"}], "test.jsonl")
    loaded = s.load_jsonl("test.jsonl")
    assert len(loaded) == 3
    assert loaded[0]["name"] == "Alpha"
    assert loaded[2]["name"] == "Gamma"


def test_storage_load_jsonl_missing(tmp_path):
    from scraper.storage import Storage

    s = Storage(tmp_path / "raw", tmp_path / "proc")
    result = s.load_jsonl("nonexistent.jsonl")
    assert result == []


def test_storage_save_csv(tmp_path):
    from scraper.storage import Storage

    s = Storage(tmp_path / "raw", tmp_path / "proc")
    records = [
        {"name": "Food Bank", "phone": "503-111-2222"},
        {"name": "Shelter", "phone": "503-333-4444"},
    ]
    path = s.save_csv(records, "test.csv")
    assert path.exists()
    content = path.read_text()
    assert "Food Bank" in content
    assert "Shelter" in content


def test_storage_seen_ids(tmp_path):
    from scraper.storage import Storage

    s = Storage(tmp_path / "raw", tmp_path / "proc")
    ids = {"abc", "def", "ghi"}
    s.save_seen_ids(ids)
    loaded = s.load_seen_ids()
    assert loaded == ids


def test_storage_save_html(tmp_path):
    from scraper.storage import Storage

    s = Storage(tmp_path / "raw", tmp_path / "proc")
    s.save_html("<html><body>test</body></html>", "page.html")
    path = tmp_path / "raw" / "page.html"
    assert path.exists()
    assert "test" in path.read_text()


# ---------------------------------------------------------------------------
# Processor tests
# ---------------------------------------------------------------------------

def test_processor_normalise_full_record(tmp_path):
    from scraper.config import Config
    from scraper.processor import DataProcessor

    cfg = Config(raw_dir=tmp_path / "raw", processed_dir=tmp_path / "proc")
    proc = DataProcessor(cfg)

    raw = {
        "name": "  Oregon Food Bank  ",
        "description": "Provides food to families.",
        "address": "7900 NE 33rd Dr, Portland, OR 97211",
        "phone": "503-282-0555",
        "website": "https://www.oregonfoodbank.org",
        "hours": "Mon-Fri 9-5",
        "eligibility": "Low income",
        "languages": "English, Spanish",
        "categories": ["Food", "Basic Needs"],
        "detail_url": "https://gethelp.211info.org/resource/123",
        "category": "food",
        "search_zip": "97211",
    }
    result = proc._normalise(raw)

    assert result["name"] == "Oregon Food Bank"
    assert result["city"] == "Portland"
    assert result["state"] == "OR"
    assert result["zip"] == "97211"
    assert result["phone"] == "503-282-0555"
    assert "Food" in result["categories"]
    assert result["id"]  # has a non-empty ID


def test_processor_normalise_email_mailto(tmp_path):
    from scraper.config import Config
    from scraper.processor import DataProcessor

    cfg = Config(raw_dir=tmp_path / "raw", processed_dir=tmp_path / "proc")
    proc = DataProcessor(cfg)

    raw = {"name": "Test Org", "email": "mailto:info@example.com"}
    result = proc._normalise(raw)
    assert result["email"] == "info@example.com"


def test_processor_deduplicate(tmp_path):
    from scraper.config import Config
    from scraper.processor import DataProcessor

    cfg = Config(raw_dir=tmp_path / "raw", processed_dir=tmp_path / "proc")
    proc = DataProcessor(cfg)

    r1 = {
        "name": "Food Bank",
        "description": "",
        "address": "123 Main St, Portland, OR 97201",
        "phone": "",
        "email": "",
        "website": "",
        "hours": "",
        "eligibility": "",
        "languages": "",
        "categories": "Food",
        "accessibility": "",
        "source_url": "https://example.com/1",
        "search_category": "food",
        "search_zip": "97201",
        "city": "Portland",
        "state": "OR",
        "zip": "97201",
        "id": "aabbccdd11223344",
    }
    r2 = dict(r1)  # exact duplicate
    r2["categories"] = "Basic Needs"

    result = proc._deduplicate([r1, r2])
    assert len(result) == 1
    assert "Food" in result[0]["categories"]
    assert "Basic Needs" in result[0]["categories"]


def test_processor_stable_id_deterministic(tmp_path):
    from scraper.processor import DataProcessor

    id1 = DataProcessor._stable_id("Oregon Food Bank", "7900 NE 33rd Dr", "https://example.com")
    id2 = DataProcessor._stable_id("Oregon Food Bank", "7900 NE 33rd Dr", "https://example.com")
    assert id1 == id2
    assert len(id1) == 16


def test_processor_stable_id_differs(tmp_path):
    from scraper.processor import DataProcessor

    id1 = DataProcessor._stable_id("Food Bank A", "123 Main St")
    id2 = DataProcessor._stable_id("Food Bank B", "123 Main St")
    assert id1 != id2


def test_processor_process_and_export(tmp_path):
    from scraper.config import Config
    from scraper.processor import DataProcessor

    cfg = Config(raw_dir=tmp_path / "raw", processed_dir=tmp_path / "proc")
    proc = DataProcessor(cfg)

    raw = [
        {
            "name": "Test Service",
            "address": "100 N Main St, Salem, OR 97301",
            "phone": "503-555-0100",
            "category": "health-care",
            "search_zip": "97301",
            "detail_url": "",
        }
    ]
    clean = proc.process(raw)
    assert len(clean) == 1
    proc.export(clean, "test_services")

    # Check files exist
    assert (tmp_path / "proc" / "test_services.jsonl").exists()
    assert (tmp_path / "proc" / "test_services.csv").exists()


# ---------------------------------------------------------------------------
# Address parsing
# ---------------------------------------------------------------------------

def test_address_parse_full():
    from scraper.processor import DataProcessor

    city, state, zipcode = DataProcessor._parse_address("7900 NE 33rd Dr, Portland, OR 97211")
    assert city == "Portland"
    assert state == "OR"
    assert zipcode == "97211"


def test_address_parse_no_match():
    from scraper.processor import DataProcessor

    city, state, zipcode = DataProcessor._parse_address("unknown address")
    assert city == ""
    assert state == ""
    assert zipcode == ""


# ---------------------------------------------------------------------------
# Static scraper (no-network smoke tests)
# ---------------------------------------------------------------------------

def test_static_scraper_init():
    from scraper.static_scraper import StaticScraper

    s = StaticScraper()
    assert s.cfg is not None
    assert s.session is not None


# ---------------------------------------------------------------------------
# BrowserScraper (init only, no actual browser)
# ---------------------------------------------------------------------------

def test_browser_scraper_init():
    from scraper.browser_scraper import BrowserScraper

    s = BrowserScraper()
    assert s.cfg is not None
    assert s._browser is None


# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------

def test_cli_defaults():
    from scraper.main import parse_args

    args = parse_args([])
    assert args.mode == "all"
    assert args.headless is True
    assert args.delay == 1.5
    assert args.no_enrich is False


def test_cli_browser_mode():
    from scraper.main import parse_args

    args = parse_args(["--mode", "browser", "--categories", "food", "--zips", "97201"])
    assert args.mode == "browser"
    assert args.categories == ["food"]
    assert args.zips == ["97201"]


def test_cli_no_enrich():
    from scraper.main import parse_args

    args = parse_args(["--mode", "browser", "--no-enrich"])
    assert args.no_enrich is True


def test_cli_log_level():
    from scraper.main import parse_args

    args = parse_args(["--log-level", "DEBUG"])
    assert args.log_level == "DEBUG"


def test_cli_max_pages():
    from scraper.main import parse_args

    args = parse_args(["--mode", "crawl", "--max-pages", "50"])
    assert args.max_pages == 50
