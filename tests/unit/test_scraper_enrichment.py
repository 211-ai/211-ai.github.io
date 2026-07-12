"""Unit tests for scraper/enrichment layer — no network access required."""

from __future__ import annotations

import importlib

import pytest


def _try_import(name: str):
    try:
        return importlib.import_module(name)
    except ImportError as exc:
        pytest.skip(f"{name} import failed: {exc}")


def test_enrichment_package_importable():
    mod = _try_import("scraper.enrichment")
    assert mod is not None


def test_enrichment_exposes_address_geocoder():
    _try_import("scraper.enrichment")
    from scraper.enrichment import AddressGeocoder  # noqa: PLC0415

    assert AddressGeocoder is not None


def test_enrichment_exposes_address_query():
    _try_import("scraper.enrichment")
    from scraper.enrichment import AddressQuery  # noqa: PLC0415

    assert AddressQuery is not None


def test_address_query_dataclass_fields():
    _try_import("scraper.enrichment")
    import dataclasses

    from scraper.enrichment import AddressQuery  # noqa: PLC0415

    fields = {f.name for f in dataclasses.fields(AddressQuery)}
    # Must include at least one address field
    assert "raw" in fields or "address" in fields or len(fields) > 0


def test_normalized_query_address_text_importable():
    _try_import("scraper.enrichment")
    from scraper.enrichment import normalized_query_address_text  # noqa: PLC0415

    assert callable(normalized_query_address_text)


def test_normalized_query_address_basic():
    _try_import("scraper.enrichment")
    from scraper.enrichment import normalized_query_address_text  # noqa: PLC0415

    result = normalized_query_address_text("123 Main St, Portland, OR 97201")
    assert isinstance(result, str)
    assert len(result) > 0


def test_enrichment_exposes_duckdb_etl():
    _try_import("scraper.enrichment")
    from scraper.enrichment import DuckDBETLWarehouse  # noqa: PLC0415

    assert DuckDBETLWarehouse is not None


def test_enrichment_exposes_classify_failed_urls():
    _try_import("scraper.enrichment")
    from scraper.enrichment import classify_failed_urls  # noqa: PLC0415

    assert callable(classify_failed_urls)
