"""Document parsing and text extraction helpers."""

from .office_text_extraction import OfficeTextExtractionResult, extract_office_text_from_bytes, extract_office_text_from_url, is_office_document
from .pdf_text_extraction import PdfTextExtractionResult, extract_pdf_text_from_bytes, extract_pdf_text_from_url, is_pdf_document
from .processor import DataProcessor

__all__ = [
    "DataProcessor",
    "OfficeTextExtractionResult",
    "PdfTextExtractionResult",
    "extract_office_text_from_bytes",
    "extract_office_text_from_url",
    "extract_pdf_text_from_bytes",
    "extract_pdf_text_from_url",
    "is_office_document",
    "is_pdf_document",
]
