from __future__ import annotations

from pathlib import Path

import pytest

from scraper.pdf_text_extraction import extract_pdf_text_from_bytes, is_pdf_document


def test_extract_pdf_text_from_bytes_uses_ipfs_file_converter(tmp_path: Path):
    fitz = pytest.importorskip("fitz")
    pdf_path = tmp_path / "sample.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "211info PDF extraction for GraphRAG")
    document.save(pdf_path)
    document.close()

    result = extract_pdf_text_from_bytes(pdf_path.read_bytes(), source_name="sample.pdf")

    assert result.success
    assert result.method.startswith("ipfs_datasets_py.file_converter")
    assert "211info PDF extraction" in result.text
    assert result.byte_length == pdf_path.stat().st_size
    assert result.binary_sha256


def test_is_pdf_document_detects_url_content_type_text_and_bytes():
    assert is_pdf_document("https://example.org/file.pdf")
    assert is_pdf_document("https://example.org/file", content_type="application/pdf")
    assert is_pdf_document(text="%PDF-1.7")
    assert is_pdf_document(content=b"%PDF-1.7")
