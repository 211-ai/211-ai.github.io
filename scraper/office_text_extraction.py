from __future__ import annotations

import hashlib
import importlib.util
import json
import logging
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

logger = logging.getLogger("scraper.office_text_extraction")


DEFAULT_OFFICE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "application/vnd.openxmlformats-officedocument.presentationml.presentation,"
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document,"
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,"
        "application/zip;q=0.9,application/octet-stream;q=0.8,*/*;q=0.7"
    ),
}
OFFICE_EXTENSIONS = {".ppt", ".pptx", ".doc", ".docx", ".xls", ".xlsx", ".rtf", ".odt", ".ods", ".odp"}
OFFICE_CONTENT_TYPE_PARTS = (
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument",
    "application/msword",
    "application/vnd.ms-excel",
    "application/rtf",
    "application/vnd.oasis.opendocument",
)


@dataclass
class OfficeTextExtractionResult:
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


def is_office_document(url: str = "", *, content_type: str = "", text: str = "", content: bytes = b"") -> bool:
    path = urlparse(str(url or "")).path.lower()
    suffix = Path(path).suffix.lower()
    lowered_type = str(content_type or "").lower()
    return (
        suffix in OFFICE_EXTENSIONS
        or any(part in lowered_type for part in OFFICE_CONTENT_TYPE_PARTS)
        or looks_like_office_zip_text(text)
        or bytes(content or b"").startswith(b"PK\x03\x04")
    )


def is_binary_like_text(text: str, *, sample_size: int = 4000) -> bool:
    sample = str(text or "")[:sample_size]
    if not sample:
        return False
    if looks_like_office_zip_text(sample) or sample.lstrip().startswith("%PDF-"):
        return True
    if "\x00" in sample:
        return True
    controls = sum(1 for char in sample if (ord(char) < 32 and char not in "\n\r\t") or ord(char) == 0xFFFD)
    return controls / max(len(sample), 1) > 0.02


def looks_like_office_zip_text(text: str) -> bool:
    sample = str(text or "").lstrip()[:8000]
    return sample.startswith("PK") or any(
        marker in sample
        for marker in (
            "[Content_Types].xml",
            "ppt/slides/",
            "word/document.xml",
            "xl/workbook.xml",
            "application/vnd.openxmlformats",
        )
    )


def extract_office_text_from_url(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout_seconds: int = 60,
) -> OfficeTextExtractionResult:
    try:
        response = requests.get(
            url,
            headers={**DEFAULT_OFFICE_HEADERS, **(headers or {})},
            timeout=(10, max(int(timeout_seconds), 10)),
        )
        response.raise_for_status()
    except Exception as exc:
        return OfficeTextExtractionResult(success=False, method="http", error=str(exc))
    return extract_office_text_from_bytes(response.content, source_name=url)


def extract_office_text_from_bytes(office_bytes: bytes, *, source_name: str = "") -> OfficeTextExtractionResult:
    byte_length = len(office_bytes or b"")
    if not office_bytes:
        return OfficeTextExtractionResult(success=False, method="ipfs_datasets_py.file_converter", byte_length=0)

    suffix = Path(urlparse(source_name).path).suffix or ".bin"
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as handle:
            handle.write(office_bytes)
            temp_path = Path(handle.name)
        result = extract_office_text_from_path(temp_path, source_name=source_name, byte_length=byte_length)
        result.binary_sha256 = hashlib.sha256(office_bytes).hexdigest()
        return result
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except Exception:
                pass


def extract_office_text_from_path(
    office_path: Path,
    *,
    source_name: str = "",
    byte_length: int | None = None,
) -> OfficeTextExtractionResult:
    byte_length = int(byte_length if byte_length is not None else office_path.stat().st_size)
    try:
        extract_office_format = load_ipfs_office_extract_function()
        result = extract_office_format(office_path)
        text = str(getattr(result, "text", "") or "").strip()
        success = bool(getattr(result, "success", False) and text)
        metadata = dict(getattr(result, "metadata", {}) or {})
        metadata["source_name"] = source_name
        return OfficeTextExtractionResult(
            text=text,
            success=success,
            method=f"ipfs_datasets_py.file_converter.{metadata.get('method') or getattr(result, 'method', '') or 'office'}",
            error="" if success else str(getattr(result, "error", "") or "Office extraction returned no text"),
            byte_length=byte_length,
            metadata=metadata,
        )
    except Exception as exc:
        logger.warning("Office extraction failed for %s: %s", source_name or office_path, exc)
        return OfficeTextExtractionResult(
            success=False,
            method="ipfs_datasets_py.file_converter",
            error=str(exc),
            byte_length=byte_length,
            metadata={"source_name": source_name},
        )


def load_ipfs_office_extract_function() -> Any:
    local_module = (
        Path(__file__).resolve().parent.parent
        / "ipfs_datasets_py"
        / "ipfs_datasets_py"
        / "processors"
        / "file_converter"
        / "office_format_extractors.py"
    )
    if local_module.exists():
        module_name = "_vendor_ipfs_datasets_py_file_converter_office_format_extractors"
        module = sys.modules.get(module_name)
        if module is None:
            spec = importlib.util.spec_from_file_location(module_name, local_module)
            if spec is None or spec.loader is None:
                raise ImportError(f"Could not load ipfs_datasets_py office extractor from {local_module}")
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
        return getattr(module, "extract_office_format")

    from ipfs_datasets_py.processors.file_converter.office_format_extractors import extract_office_format

    return extract_office_format


def office_title_from_metadata(metadata: dict[str, Any]) -> str:
    nested = metadata.get("metadata") if isinstance(metadata, dict) else None
    if isinstance(nested, dict):
        value = str(nested.get("title") or "").strip()
        if value:
            return value
    return ""


def json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, default=str, ensure_ascii=False))
