"""Unit tests for scraper/export layer — no network access required."""

from __future__ import annotations

import importlib

import pytest


def _try_import(name: str):
    try:
        return importlib.import_module(name)
    except ImportError as exc:
        pytest.skip(f"{name} import failed: {exc}")


def test_export_package_importable():
    mod = _try_import("scraper.export")
    assert mod is not None


def test_export_exposes_build_browser_graphrag_corpus():
    _try_import("scraper.export")
    from scraper.export import build_browser_graphrag_corpus  # noqa: PLC0415

    assert callable(build_browser_graphrag_corpus)


def test_export_exposes_export_canonical_services():
    _try_import("scraper.export")
    from scraper.export import export_canonical_services  # noqa: PLC0415

    assert callable(export_canonical_services)


def test_export_canonical_services_module_importable():
    mod = _try_import("scraper.export.export_canonical_services")
    assert mod is not None


def test_build_retrieval_package_importable():
    try:
        mod = importlib.import_module("scraper.export.build_retrieval_package")
        assert mod is not None
    except ImportError:
        pytest.skip("optional dependency for retrieval package not installed")


def test_build_service_portal_package_importable():
    mod = _try_import("scraper.export.build_service_portal_package")
    assert mod is not None
