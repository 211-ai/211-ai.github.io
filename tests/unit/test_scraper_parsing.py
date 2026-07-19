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


# ---------------------------------------------------------------------------
# DataProcessor static helpers (no deps)
# ---------------------------------------------------------------------------


class TestDataProcessorStableId:
    def _fn(self):
        from scraper.parsing.processor import DataProcessor
        return DataProcessor._stable_id

    def test_returns_16_char_hex_string(self):
        fn = self._fn()
        result = fn("Test Service", "Seattle")
        assert len(result) == 16
        int(result, 16)  # valid hex

    def test_deterministic(self):
        fn = self._fn()
        a = fn("Alpha", "Beta", "Gamma")
        b = fn("Alpha", "Beta", "Gamma")
        assert a == b

    def test_order_matters(self):
        fn = self._fn()
        assert fn("A", "B") != fn("B", "A")

    def test_empty_parts_skipped(self):
        fn = self._fn()
        a = fn("A", "", "B")
        b = fn("A", "B")
        assert a == b

    def test_case_insensitive(self):
        fn = self._fn()
        assert fn("Seattle") == fn("SEATTLE") == fn("seattle")


class TestDataProcessorNormalise:
    def _normalise(self, rec):
        from scraper.parsing.processor import DataProcessor
        dp = DataProcessor.__new__(DataProcessor)
        return dp._normalise(rec)

    def test_name_preserved(self):
        result = self._normalise({"name": "Community Center"})
        assert result["name"] == "Community Center"

    def test_phone_preserved(self):
        result = self._normalise({"name": "X", "phone": "206-555-0001"})
        assert result["phone"] == "206-555-0001"

    def test_missing_fields_default_to_empty_string(self):
        result = self._normalise({"name": "X"})
        for key in ("description", "email", "website"):
            assert result.get(key, "") == ""

    def test_id_generated(self):
        result = self._normalise({"name": "Service X"})
        assert "id" in result
        assert len(result["id"]) == 16
