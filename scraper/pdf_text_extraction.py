from __future__ import annotations

import importlib.util
import hashlib
import json
import logging
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

logger = logging.getLogger("scraper.pdf_text_extraction")


DEFAULT_PDF_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/pdf,application/octet-stream;q=0.9,*/*;q=0.8",
}


@dataclass
class PdfTextExtractionResult:
    text: str = ""
    success: bool = False
    method: str = ""
    error: str = ""
    byte_length: int = 0
    binary_sha256: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_metadata(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "method": self.method,
            "error": self.error,
            "byte_length": self.byte_length,
            "binary_sha256": self.binary_sha256,
            "text_length": len(self.text),
            "metadata": json_safe(self.metadata),
        }


def is_pdf_document(url: str = "", *, content_type: str = "", text: str = "", content: bytes = b"") -> bool:
    path = urlparse(str(url or "")).path.lower()
    lowered_type = str(content_type or "").lower()
    stripped_text = str(text or "").lstrip()
    return (
        path.endswith(".pdf")
        or "application/pdf" in lowered_type
        or stripped_text.startswith("%PDF-")
        or bytes(content or b"").startswith(b"%PDF-")
    )


def extract_pdf_text_from_url(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout_seconds: int = 60,
) -> PdfTextExtractionResult:
    try:
        response = requests.get(
            url,
            headers={**DEFAULT_PDF_HEADERS, **(headers or {})},
            timeout=(10, max(int(timeout_seconds), 10)),
        )
        response.raise_for_status()
    except Exception as exc:
        return PdfTextExtractionResult(success=False, method="http", error=str(exc))
    return extract_pdf_text_from_bytes(response.content, source_name=url)


def extract_pdf_text_from_bytes(pdf_bytes: bytes, *, source_name: str = "") -> PdfTextExtractionResult:
    byte_length = len(pdf_bytes or b"")
    if not pdf_bytes:
        return PdfTextExtractionResult(success=False, method="ipfs_datasets_py.file_converter", byte_length=0)

    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as handle:
            handle.write(pdf_bytes)
            temp_path = Path(handle.name)
        result = extract_pdf_text_from_path(temp_path, source_name=source_name, byte_length=byte_length)
        result.binary_sha256 = hashlib.sha256(pdf_bytes).hexdigest()
        return result
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except Exception:
                pass


def extract_pdf_text_from_path(
    pdf_path: Path,
    *,
    source_name: str = "",
    byte_length: int | None = None,
) -> PdfTextExtractionResult:
    byte_length = int(byte_length if byte_length is not None else pdf_path.stat().st_size)
    try:
        extractor_cls = load_ipfs_pdf_extractor_class()
        extractor = extractor_cls()
        result = extractor.extract(pdf_path)
        text = str(getattr(result, "text", "") or "").strip()
        success = bool(getattr(result, "success", False) and text)
        metadata = dict(getattr(result, "metadata", {}) or {})
        metadata["source_name"] = source_name
        return PdfTextExtractionResult(
            text=text,
            success=success,
            method=f"ipfs_datasets_py.file_converter.{metadata.get('method') or 'pdf'}",
            error="" if success else str(getattr(result, "error", "") or "PDF extraction returned no text"),
            byte_length=byte_length,
            metadata=metadata,
        )
    except Exception as exc:
        logger.warning("PDF extraction failed for %s: %s", source_name or pdf_path, exc)
        return PdfTextExtractionResult(
            success=False,
            method="ipfs_datasets_py.file_converter",
            error=str(exc),
            byte_length=byte_length,
            metadata={"source_name": source_name},
        )


def load_ipfs_pdf_extractor_class() -> type:
    local_module = (
        Path(__file__).resolve().parent.parent
        / "ipfs_datasets_py"
        / "ipfs_datasets_py"
        / "processors"
        / "file_converter"
        / "text_extractors.py"
    )
    if local_module.exists():
        module_name = "_vendor_ipfs_datasets_py_file_converter_text_extractors"
        module = sys.modules.get(module_name)
        if module is None:
            spec = importlib.util.spec_from_file_location(module_name, local_module)
            if spec is None or spec.loader is None:
                raise ImportError(f"Could not load ipfs_datasets_py PDF extractor from {local_module}")
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
        return getattr(module, "PDFExtractor")

    from ipfs_datasets_py.processors.file_converter.text_extractors import PDFExtractor

    return PDFExtractor


def pdf_title_from_metadata(metadata: dict[str, Any]) -> str:
    pdf_info = metadata.get("pdf_info") if isinstance(metadata, dict) else None
    if isinstance(pdf_info, dict):
        for key in ["Title", "title"]:
            value = str(pdf_info.get(key) or "").strip()
            if value:
                return value
    return ""


def json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, default=str, ensure_ascii=False))
