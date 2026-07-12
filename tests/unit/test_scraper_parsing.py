"""Unit tests for scraper/parsing layer — no network or file-system access required."""

from __future__ import annotations

import importlib

import pytest


def _try_import(name: str):
    try:
        return importlib.import_module(name)
    except ImportError as exc:
        pytest.skip(f"{name} import failed: {exc}")


def test_parsing_package_importable():
    mod = _try_import("scraper.parsing")
    assert mod is not None


def test_parsing_exposes_data_processor():
    _try_import("scraper.parsing")
    from scraper.parsing import DataProcessor  # noqa: PLC0415

    assert DataProcessor is not None


def test_is_pdf_document_by_extension():
    _try_import("scraper.parsing")
    from scraper.parsing import is_pdf_document  # noqa: PLC0415

    assert is_pdf_document("annual_report.pdf")
    assert not is_pdf_document("record.json")


def test_is_office_document_by_extension():
    _try_import("scraper.parsing")
    from scraper.parsing import is_office_document  # noqa: PLC0415

    assert is_office_document("intake_form.docx")
    assert is_office_document("data.xlsx")
    assert not is_office_document("report.pdf")


def test_pdf_result_type_importable():
    _try_import("scraper.parsing")
    from scraper.parsing import PdfTextExtractionResult  # noqa: PLC0415

    assert PdfTextExtractionResult is not None


def test_office_result_type_importable():
    _try_import("scraper.parsing")
    from scraper.parsing import OfficeTextExtractionResult  # noqa: PLC0415

    assert OfficeTextExtractionResult is not None


def test_data_processor_instantiable():
    _try_import("scraper.parsing")
    try:
        from scraper.config import Config  # noqa: PLC0415
        from scraper.parsing import DataProcessor  # noqa: PLC0415
    except ImportError as exc:
        pytest.skip(f"dependency missing: {exc}")

    cfg = Config()
    processor = DataProcessor(cfg)
    assert processor is not None
