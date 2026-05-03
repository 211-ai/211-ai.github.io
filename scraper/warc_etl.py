"""
WARC unpacking and ETL for archived 211 pages.

Supports Common Crawl ranged WARC records and full WARC/WARC.GZ files. Parsed
HTML pages are converted into the same raw page/service outputs used by the
agentic daemon.
"""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from bs4 import BeautifulSoup

from .agentic_daemon import (
    AgenticCrawlerDaemon,
    CrawlItem,
    FetchResult,
    extract_links,
    utc_now,
)
from .config import Config
from .duckdb_etl import DuckDBETLWarehouse
from .processor import DataProcessor
from .storage import Storage
from .utils import clean_text, setup_logging

logger = logging.getLogger("scraper.warc_etl")


@dataclass
class WarcDocument:
    url: str
    status_code: int = 0
    content_type: str = ""
    title: str = ""
    text: str = ""
    html: str = ""
    warc_path: str = ""
    record_index: int = 0
    metadata: dict[str, Any] | None = None


def iter_warc_documents(paths: Iterable[Path]) -> Iterable[WarcDocument]:
    """Yield parsed HTML documents from WARC/WARC.GZ files."""
    try:
        from warcio.archiveiterator import ArchiveIterator
    except ImportError as exc:
        raise RuntimeError("warcio is required to unpack WARC files") from exc

    for path in paths:
        with path.open("rb") as fh:
            for idx, record in enumerate(ArchiveIterator(fh)):
                if getattr(record, "rec_type", "") != "response":
                    continue

                url = record.rec_headers.get_header("WARC-Target-URI") or ""
                http_headers = record.http_headers
                status_code = int(http_headers.get_statuscode() or 0) if http_headers else 0
                content_type = http_headers.get_header("Content-Type") if http_headers else ""
                if not is_html_content_type(content_type):
                    continue

                body = record.content_stream().read()
                html = decode_body(body)
                title, text = html_title_text(html)
                yield WarcDocument(
                    url=url,
                    status_code=status_code,
                    content_type=content_type,
                    title=title,
                    text=text,
                    html=html,
                    warc_path=str(path),
                    record_index=idx,
                    metadata={
                        "warc_record_id": record.rec_headers.get_header("WARC-Record-ID") or "",
                        "warc_date": record.rec_headers.get_header("WARC-Date") or "",
                    },
                )


def is_html_content_type(content_type: str) -> bool:
    lowered = (content_type or "").lower()
    return "text/html" in lowered or "application/xhtml" in lowered


def decode_body(body: bytes) -> str:
    for encoding in ("utf-8", "latin-1"):
        try:
            return body.decode(encoding)
        except UnicodeDecodeError:
            continue
    return body.decode("utf-8", errors="replace")


def html_title_text(html: str) -> tuple[str, str]:
    soup = BeautifulSoup(html or "", "lxml")
    title = clean_text(soup.title.string) if soup.title else ""
    for remove in soup.find_all(["script", "style", "nav", "footer", "header"]):
        remove.decompose()
    text = clean_text((soup.find("main") or soup.body or soup).get_text(separator=" "))
    return title, text


def is_blocked_or_thin(doc: WarcDocument) -> bool:
    haystack = f"{doc.title} {doc.text[:500]}".lower()
    blocked_signals = [
        "just a moment",
        "checking your browser",
        "attention required",
        "enable javascript and cookies",
        "cloudflare",
    ]
    return doc.status_code in {403, 429, 503} and any(sig in haystack for sig in blocked_signals)


def document_to_fetch_result(doc: WarcDocument) -> FetchResult:
    return FetchResult(
        url=doc.url,
        title=doc.title,
        text=doc.text,
        html=doc.html,
        links=extract_links(doc.html, doc.url),
        metadata={
            **(doc.metadata or {}),
            "provider": "warc",
            "warc_path": doc.warc_path,
            "warc_record_index": doc.record_index,
            "http_status": doc.status_code,
            "content_type": doc.content_type,
        },
        success=True,
        quality_score=1.0 if doc.text and not is_blocked_or_thin(doc) else 0.1,
    )


def etl_warc_paths(
    paths: Iterable[Path],
    *,
    output_dir: Path,
    state_dir: Path | None = None,
    basename: str = "services_warc",
    include_blocked: bool = False,
) -> dict[str, Any]:
    cfg = Config(raw_dir=output_dir / "raw", processed_dir=output_dir / "processed", request_delay=0)
    storage = Storage(cfg.raw_dir, cfg.processed_dir)
    processor = DataProcessor(cfg)
    warehouse = DuckDBETLWarehouse((state_dir or (output_dir / "state")) / "etl_warehouse.duckdb")
    extractor = AgenticCrawlerDaemon(
        cfg,
        state_path=(state_dir or (output_dir / "state")) / "warc_etl_state.json",
        strategy_path=(state_dir or (output_dir / "state")) / "warc_etl_strategy.json",
    )

    page_records: list[dict[str, Any]] = []
    raw_services: list[dict[str, Any]] = []
    warc_records: list[dict[str, Any]] = []
    parsed = 0
    skipped_blocked = 0

    for doc in iter_warc_documents(paths):
        parsed += 1
        warc_records.append(
            {
                "url": doc.url,
                "status_code": doc.status_code,
                "content_type": doc.content_type,
                "title": doc.title,
                "text": doc.text,
                "warc_path": doc.warc_path,
                "record_index": doc.record_index,
                "metadata": doc.metadata or {},
            }
        )
        if is_blocked_or_thin(doc) and not include_blocked:
            skipped_blocked += 1
            continue

        result = document_to_fetch_result(doc)
        item = CrawlItem(url=doc.url, depth=0, kind="warc", metadata={"source": "warc"})
        page_records.append(
            {
                "url": result.url,
                "title": result.title,
                "body_text": result.text,
                "links": result.links,
                "quality_score": result.quality_score,
                "metadata": result.metadata,
                "fetched_at": utc_now(),
            }
        )
        service = extractor._extract_service_record(result, item)
        if service:
            service["source_archive"] = doc.warc_path
            raw_services.append(service)

    if page_records:
        storage.append_jsonl(page_records, "warc_pages_raw.jsonl")
        warehouse.append_crawl_pages(page_records)
    if warc_records:
        warehouse.append_warc_documents(warc_records)
    if raw_services:
        storage.append_jsonl(raw_services, f"{basename}_raw.jsonl")
        warehouse.append_raw_services(raw_services, source="warc_etl")
        clean = processor.process(raw_services)
        processor.export(clean, basename)
        warehouse.append_processed_services(clean, source="warc_etl")
    else:
        clean = []

    return {
        "status": "success",
        "warc_documents": parsed,
        "skipped_blocked_or_thin": skipped_blocked,
        "raw_pages": len(page_records),
        "raw_services": len(raw_services),
        "processed_services": len(clean),
        "basename": basename,
    }


def collect_warc_paths(inputs: list[Path]) -> list[Path]:
    paths: list[Path] = []
    for item in inputs:
        if item.is_dir():
            paths.extend(sorted(item.glob("*.warc")))
            paths.extend(sorted(item.glob("*.warc.gz")))
        elif item.exists():
            paths.append(item)
    return paths


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Unpack WARC files and ETL archived 211 pages")
    parser.add_argument("paths", nargs="+", type=Path, help="WARC files or directories")
    parser.add_argument("--output-dir", type=Path, default=Path("data/live"))
    parser.add_argument("--state-dir", type=Path, default=Path("data/live/state"))
    parser.add_argument("--basename", default="services_warc")
    parser.add_argument("--include-blocked", action="store_true")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    setup_logging(getattr(logging, args.log_level))
    paths = collect_warc_paths(args.paths)
    result = etl_warc_paths(
        paths,
        output_dir=args.output_dir,
        state_dir=args.state_dir,
        basename=args.basename,
        include_blocked=args.include_blocked,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
