"""
Persistent agentic crawl and ETL daemon for 211info.org.

This module keeps a durable crawl queue, fetches pages through the optional
ipfs_datasets_py unified web-archiving API when available, extracts service
records, and exports normalized datasets after every run.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import unquote, urlparse

import requests
from bs4 import BeautifulSoup
from requests import exceptions as requests_exceptions

from .config import Config
from .duckdb_etl import DuckDBETLWarehouse
from .duckdb_state import DuckDBCrawlStore
from .processor import DataProcessor
from .storage import Storage
from .utils import clean_text, extract_phone, normalise_url, same_domain, setup_logging

logger = logging.getLogger("scraper.agentic_daemon")


SERVICE_HINTS = {
    "eligibility",
    "hours",
    "intake",
    "service",
    "program",
    "phone",
    "address",
    "resources",
    "food",
    "housing",
    "shelter",
    "utility",
    "mental health",
    "transportation",
}


@dataclass
class FetchResult:
    """Provider-neutral page fetch result used by the daemon."""

    url: str
    title: str = ""
    text: str = ""
    html: str = ""
    links: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    success: bool = True
    errors: list[str] = field(default_factory=list)
    quality_score: float = 0.0


@dataclass
class CrawlItem:
    """Durable crawl queue item."""

    url: str
    depth: int = 0
    kind: str = "page"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CrawlState:
    """JSON-serializable daemon state."""

    queue: list[CrawlItem] = field(default_factory=list)
    seen_urls: set[str] = field(default_factory=set)
    failed_urls: dict[str, int] = field(default_factory=dict)
    active_url: str = ""
    active_urls: list[str] = field(default_factory=list)
    heartbeat_at: str = ""
    last_progress_at: str = ""
    processed_pages: int = 0
    extracted_services: int = 0
    errors: int = 0
    strategy_generation: int = 0

    @classmethod
    def load(cls, path: Path) -> "CrawlState":
        if not path.exists():
            return cls()
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            return cls()
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return cls()
        return cls(
            queue=[CrawlItem(**item) for item in payload.get("queue", [])],
            seen_urls=set(payload.get("seen_urls", [])),
            failed_urls=dict(payload.get("failed_urls", {})),
            active_url=str(payload.get("active_url", "")),
            active_urls=list(payload.get("active_urls", [])),
            heartbeat_at=str(payload.get("heartbeat_at", "")),
            last_progress_at=str(payload.get("last_progress_at", "")),
            processed_pages=int(payload.get("processed_pages", 0)),
            extracted_services=int(payload.get("extracted_services", 0)),
            errors=int(payload.get("errors", 0)),
            strategy_generation=int(payload.get("strategy_generation", 0)),
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = asdict(self)
        payload["seen_urls"] = sorted(self.seen_urls)
        payload["queue"] = [asdict(item) for item in self.queue]
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


class WebArchivingAdapter:
    """Fetch and archive pages through ipfs_datasets_py when available."""

    def __init__(self, cfg: Config, archive_dir: Path | None = None) -> None:
        self.cfg = cfg
        self.archive_dir = archive_dir
        self._api: Any | None = None
        self._web_archive: Any | None = None
        self._session = requests.Session()
        self._session.headers.update(cfg.headers)
        self._session.headers["User-Agent"] = (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        self._headers = dict(self._session.headers)
        self._load_optional_tools()

    def _load_optional_tools(self) -> None:
        if not external_tools_enabled():
            logger.info("External ipfs_datasets tools disabled; using lightweight local fetch/archive")
            return

        repo_root = Path(__file__).resolve().parent.parent
        local_ipfs = repo_root / "ipfs_datasets_py"
        if (local_ipfs / "ipfs_datasets_py").exists() and str(local_ipfs) not in sys.path:
            sys.path.insert(0, str(local_ipfs))

        try:
            from ipfs_datasets_py.processors.web_archiving import UnifiedWebArchivingAPI

            self._api = UnifiedWebArchivingAPI()
        except Exception as exc:
            logger.info("Unified web archiving API unavailable; using requests fallback: %s", exc)

        try:
            from ipfs_datasets_py.processors.web_archiving import WebArchive

            self._web_archive = WebArchive(storage_path=str(self.archive_dir) if self.archive_dir else None)
        except Exception as exc:
            logger.info("WebArchive unavailable; archive metadata will be file-only: %s", exc)

    def fetch(self, url: str) -> FetchResult:
        if self._api is not None:
            try:
                response = self._api.fetch(url, domain="general")
                if response.success and response.document:
                    doc = response.document
                    links = list((doc.metadata or {}).get("links") or [])
                    if not links and doc.html:
                        links = extract_links(doc.html, doc.url)
                    return FetchResult(
                        url=doc.url,
                        title=doc.title,
                        text=doc.text,
                        html=doc.html,
                        links=links,
                        metadata=dict(doc.metadata or {}),
                        success=True,
                        quality_score=float(response.quality_score or 0.0),
                    )
                errors = [err.message for err in response.errors]
                logger.debug("Unified fetch failed for %s: %s", url, errors)
            except Exception as exc:
                logger.debug("Unified fetch exception for %s: %s", url, exc)

        return self._fetch_with_requests(url)

    def archive(self, result: FetchResult, metadata: dict[str, Any]) -> dict[str, Any]:
        if self._web_archive is not None:
            archive_result = self._web_archive.archive_url(result.url, metadata=metadata)
            if archive_result.get("status") == "success":
                return archive_result

        if not self.archive_dir:
            return {"status": "skipped"}
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        archive_id = f"page_{abs(hash(result.url))}"
        payload = {
            "id": archive_id,
            "url": result.url,
            "title": result.title,
            "text": result.text,
            "metadata": metadata,
            "timestamp": utc_now(),
        }
        path = self.archive_dir / f"{archive_id}.json"
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return {"status": "success", "archive_id": archive_id, "path": str(path)}

    def _fetch_with_requests(self, url: str) -> FetchResult:
        try:
            return self._request_with_timeout(url, timeout_seconds=int(self.cfg.timeout))
        except requests_exceptions.Timeout:
            retry_timeout = max(int(self.cfg.timeout) * 3, 90)
            try:
                return self._request_with_timeout(url, timeout_seconds=retry_timeout)
            except Exception as exc:
                return FetchResult(url=url, success=False, errors=[str(exc)], metadata={"provider": "requests"})
        except Exception as exc:
            return FetchResult(url=url, success=False, errors=[str(exc)], metadata={"provider": "requests"})

    def _request_with_timeout(self, url: str, *, timeout_seconds: int) -> FetchResult:
        response = self._session.get(url, timeout=timeout_seconds)
        response.raise_for_status()
        html = response.text
        soup = BeautifulSoup(html, "lxml")
        title = clean_text(soup.title.string) if soup.title else ""
        for remove in soup.find_all(["script", "style", "nav", "footer", "header"]):
            remove.decompose()
        text = clean_text((soup.find("main") or soup.body or soup).get_text(separator=" "))
        links = extract_links(html, response.url)
        return FetchResult(
            url=response.url,
            title=title,
            text=text,
            html=html,
            links=links,
            metadata={"provider": "requests", "timeout_seconds": int(timeout_seconds)},
            success=True,
            quality_score=1.0 if text else 0.4,
        )


class DatasetSink:
    """Persist snapshots through dataset tools when available, else JSON."""

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self._save_dataset: Any | None = None
        self._load_optional_tool()

    def _load_optional_tool(self) -> None:
        if not external_tools_enabled():
            logger.info("External dataset tools disabled; using JSON snapshot fallback")
            return

        repo_root = Path(__file__).resolve().parent.parent
        local_ipfs = repo_root / "ipfs_datasets_py"
        if (local_ipfs / "ipfs_datasets_py").exists() and str(local_ipfs) not in sys.path:
            sys.path.insert(0, str(local_ipfs))
        try:
            from ipfs_datasets_py.mcp_server.tools.dataset_tools.save_dataset import save_dataset

            self._save_dataset = save_dataset
        except Exception as exc:
            logger.info("Dataset save tool unavailable; using JSON snapshot fallback: %s", exc)

    def save_snapshot(self, records: list[dict[str, Any]], destination: Path) -> dict[str, Any]:
        destination.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "name": "211info-agentic-services",
            "created_at": utc_now(),
            "data": records,
        }
        if self._save_dataset is not None:
            try:
                import asyncio

                return asyncio.run(
                    self._save_dataset(payload, destination=str(destination), format="json")
                )
            except Exception as exc:
                logger.debug("Dataset tool save failed; falling back to JSON: %s", exc)

        destination.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return {
            "status": "success",
            "destination": str(destination),
            "format": "json",
            "record_count": len(records),
        }


class AgenticCrawlerDaemon:
    """Stateful crawler that continuously discovers, extracts, and ETLs."""

    def __init__(
        self,
        cfg: Config,
        *,
        state_path: Path,
        strategy_path: Path,
        db_path: Path | None = None,
        fetcher: WebArchivingAdapter | None = None,
        dataset_sink: DatasetSink | None = None,
    ) -> None:
        self.cfg = cfg
        self.state_path = state_path
        self.strategy_path = strategy_path
        self.db_path = db_path or state_path.with_suffix(".duckdb")
        self.etl_db_path = self.state_path.parent / "etl_warehouse.duckdb"
        self.storage = Storage(cfg.raw_dir, cfg.processed_dir)
        self.processor = DataProcessor(cfg)
        self.fetcher = fetcher or WebArchivingAdapter(cfg, archive_dir=cfg.raw_dir / "archive")
        self.dataset_sink = dataset_sink or DatasetSink(cfg.processed_dir)
        self.store = DuckDBCrawlStore(self.db_path)
        self.warehouse = DuckDBETLWarehouse(self.etl_db_path)

    def run_once(
        self,
        *,
        seed_urls: Iterable[str],
        max_pages: int = 25,
        max_workers: int = 1,
    ) -> dict[str, Any]:
        state = CrawlState.load(self.state_path)
        self.store.migrate_from_state(state)
        strategy = self.load_strategy()
        self.store.apply_strategy_priorities(strategy)
        state.strategy_generation = int(strategy.get("generation", state.strategy_generation))
        all_seed_urls = [*seed_urls, *self._load_external_seed_urls()]
        self._seed_queue(all_seed_urls)
        self._refresh_state_snapshot(state)
        processed_this_run = 0
        raw_services: list[dict[str, Any]] = []
        workers = max(1, int(max_workers))

        while self.store.queue_count() and processed_this_run < max_pages:
            batch = self._next_batch(strategy, limit=min(workers, max_pages - processed_this_run))
            if not batch:
                break

            state.active_urls = [item.url for item in batch]
            state.active_url = state.active_urls[0] if len(state.active_urls) == 1 else ""
            state.heartbeat_at = utc_now()
            self._refresh_state_snapshot(state)
            state.save(self.state_path)

            with ThreadPoolExecutor(max_workers=len(batch)) as executor:
                futures = {executor.submit(self.fetcher.fetch, item.url): item for item in batch}
                for future in as_completed(futures):
                    item = futures[future]
                    try:
                        result = future.result()
                    except Exception as exc:
                        result = FetchResult(url=item.url, success=False, errors=[str(exc)])

                    if not result.success:
                        state.errors += 1
                        state.failed_urls[item.url] = self.store.mark_failed(
                            item.url,
                            error="; ".join(result.errors),
                        )
                        self.store.record_pattern_outcome(item.url, extracted=False, fetch_success=False)
                        state.active_urls = [url for url in state.active_urls if url != item.url]
                        state.heartbeat_at = utc_now()
                        self._refresh_state_snapshot(state)
                        state.save(self.state_path)
                        continue

                    self.store.mark_seen(item.url)
                    state.seen_urls.add(item.url)
                    state.processed_pages += 1
                    state.last_progress_at = utc_now()
                    processed_this_run += 1

                    archive_meta = {
                        "depth": item.depth,
                        "kind": item.kind,
                        "quality_score": result.quality_score,
                        "strategy_generation": state.strategy_generation,
                    }
                    archive_info = self.fetcher.archive(result, archive_meta)
                    page_record = self._page_record(result, item, archive_info)
                    self.storage.append_jsonl([page_record], "agentic_pages_raw.jsonl")
                    self.warehouse.append_crawl_pages([page_record])

                    services = self._extract_service_records(result, item)
                    self.store.record_pattern_outcome(
                        item.url,
                        extracted=bool(services),
                        fetch_success=True,
                    )
                    if services:
                        raw_services.extend(services)
                        state.extracted_services += len(services)

                    self._enqueue_links(result, item.depth + 1, strategy)
                    state.active_urls = [url for url in state.active_urls if url != item.url]
                    state.active_url = ""
                    state.heartbeat_at = utc_now()
                    self._refresh_state_snapshot(state)
                    state.save(self.state_path)

            delay = float(strategy.get("request_delay", self.cfg.request_delay))
            if delay > 0 and self.store.queue_count() and processed_this_run < max_pages:
                time.sleep(delay)

        if raw_services:
            self.storage.append_jsonl(raw_services, "services_raw_agentic.jsonl")
            self.warehouse.append_raw_services(raw_services, source="agentic_daemon")
            clean = self.processor.process(raw_services)
            self.processor.export(clean, "services_agentic")
            self.warehouse.append_processed_services(clean, source="agentic_daemon")
            self.dataset_sink.save_snapshot(clean, self.cfg.processed_dir / "services_agentic_dataset.json")

        state.active_url = ""
        state.active_urls = []
        state.heartbeat_at = utc_now()
        self._refresh_state_snapshot(state)
        state.save(self.state_path)
        return {
            "processed_pages": processed_this_run,
            "extracted_services": len(raw_services),
            "queue_remaining": self.store.queue_count(),
            "max_workers": workers,
            "state_path": str(self.state_path),
            "db_path": str(self.db_path),
            "etl_db_path": str(self.etl_db_path),
        }

    def load_strategy(self) -> dict[str, Any]:
        defaults = {
            "generation": 0,
            "max_depth": 3,
            "request_delay": self.cfg.request_delay,
            "allowed_hosts": ["www.211info.org", "211info.org", "gethelp.211info.org"],
            "blocked_urls": [],
            "blocked_url_patterns": [],
            "deprioritized_url_patterns": [],
            "target_terms": sorted(SERVICE_HINTS),
        }
        if not self.strategy_path.exists():
            self.strategy_path.parent.mkdir(parents=True, exist_ok=True)
            self.strategy_path.write_text(json.dumps(defaults, indent=2, sort_keys=True), encoding="utf-8")
            return defaults
        payload = json.loads(self.strategy_path.read_text(encoding="utf-8"))
        return {**defaults, **payload}

    def _seed_queue(self, seed_urls: Iterable[str]) -> None:
        self.store.enqueue_items(
            [CrawlItem(url=url, depth=0, kind="seed") for url in seed_urls if str(url or "").strip()]
        )

    def _load_external_seed_urls(self) -> list[str]:
        path = self.state_path.parent / "external_seed_urls.jsonl"
        if not path.exists():
            return []
        urls: list[str] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            text = line.strip()
            if not text:
                continue
            try:
                payload = json.loads(text)
                url = str(payload.get("url") or "").strip() if isinstance(payload, dict) else ""
            except json.JSONDecodeError:
                url = text
            if url:
                urls.append(url)
        return urls

    def _next_batch(
        self,
        strategy: dict[str, Any],
        *,
        limit: int,
    ) -> list[CrawlItem]:
        return self.store.claim_batch(
            limit=limit,
            blocked_urls={str(item) for item in strategy.get("blocked_urls", [])},
        )

    def _enqueue_links(
        self,
        result: FetchResult,
        next_depth: int,
        strategy: dict[str, Any],
    ) -> None:
        if next_depth > int(strategy.get("max_depth", 3)):
            return
        ranked = rank_links(result.links, strategy.get("target_terms", []))
        items: list[CrawlItem] = []
        for url in ranked:
            if self._is_blocked(url, strategy):
                continue
            if not self._allowed_host(url, strategy):
                continue
            items.append(CrawlItem(url=url, depth=next_depth, kind="discovered"))
        self.store.enqueue_items(items)

    def _refresh_state_snapshot(self, state: CrawlState) -> None:
        state.queue = self.store.queue_preview(limit=50)
        state.failed_urls = self.store.failed_map()

    def _allowed_host(self, url: str, strategy: dict[str, Any]) -> bool:
        host = urlparse(url).netloc.lower()
        allowed_hosts = {str(item).lower() for item in strategy.get("allowed_hosts", [])}
        return not allowed_hosts or host in allowed_hosts

    def _is_blocked(self, url: str, strategy: dict[str, Any]) -> bool:
        if is_junk_failed_url(url):
            return True
        blocked = {str(item) for item in strategy.get("blocked_urls", [])}
        if url in blocked:
            return True
        patterns = [str(item).strip().lower() for item in strategy.get("blocked_url_patterns", []) if str(item).strip()]
        lowered = url.lower()
        return any(pattern in lowered for pattern in patterns)

    def _page_record(
        self,
        result: FetchResult,
        item: CrawlItem,
        archive_info: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "url": result.url,
            "title": result.title,
            "body_text": result.text,
            "links": result.links,
            "depth": item.depth,
            "kind": item.kind,
            "quality_score": result.quality_score,
            "archive": archive_info,
            "fetched_at": utc_now(),
        }

    def _extract_service_records(self, result: FetchResult, item: CrawlItem) -> list[dict[str, Any]]:
        text = clean_text(result.text)
        if not text:
            return []
        if "0 matching service providers" in text.lower():
            return []
        result_page_services = extract_result_page_services(text, result.url)
        if result_page_services:
            records: list[dict[str, Any]] = []
            for service in result_page_services:
                service["detail_url"] = result.url
                service["category"] = item.metadata.get("category", "")
                service["search_zip"] = item.metadata.get("zip", "")
                records.append(service)
            return records

        service = self._extract_single_service_record(result, item)
        return [service] if service else []

    def _extract_single_service_record(self, result: FetchResult, item: CrawlItem) -> dict[str, Any] | None:
        haystack = f"{result.title} {result.text}".lower()
        if not any(hint in haystack for hint in SERVICE_HINTS):
            return None

        phone = extract_phone(result.text) or ""
        email = extract_email(result.text)
        address = extract_address(result.text)
        description = clean_text(result.text[:1200])
        name = normalize_provider_name(result.title or first_heading(result.html) or first_sentence(result.text))
        categories = infer_categories(result.text)

        if not name and not phone and not address:
            return None
        if is_result_page_title_name(result.text, result.title, name) and not phone and not address:
            return None

        return {
            "name": name,
            "provider_name": name,
            "program_name": "",
            "description": description,
            "address": address,
            "phone": phone,
            "email": email,
            "website": result.url,
            "hours": extract_labeled_value(result.text, "hours"),
            "eligibility": extract_labeled_value(result.text, "eligibility"),
            "categories": categories,
            "detail_url": result.url,
            "category": item.metadata.get("category", ""),
            "search_zip": item.metadata.get("zip", ""),
        }


def extract_links(html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html or "", "lxml")
    links: list[str] = []
    seen: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        href = normalise_url(anchor["href"], base_url)
        if href and href not in seen and same_domain(href, base_url):
            links.append(href)
            seen.add(href)
    return links


def rank_links(links: Iterable[str], target_terms: Iterable[str]) -> list[str]:
    terms = [term.lower() for term in target_terms]

    def score(url: str) -> tuple[int, str]:
        lowered = url.lower().replace("-", " ")
        return (sum(1 for term in terms if term in lowered), url)

    return sorted(links, key=score, reverse=True)


def extract_email(text: str) -> str:
    match = re.search(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", text, re.IGNORECASE)
    return match.group(0) if match else ""


def extract_address(text: str) -> str:
    patterns = (
        r"\b\d{1,6}\s+[A-Za-z0-9 .#'/:-]{3,120}?\s+[A-Za-z .'-]+,\s*(?:[A-Z]{2})\s+\d{5}(?:-\d{4})?\b",
        r"\bP\.?O\.?\s+Box\s+\d+[^.]{0,80}?\s+[A-Za-z .'-]+,\s*(?:[A-Z]{2})\s+\d{5}(?:-\d{4})?\b",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return clean_text(match.group(0))
    return ""


def extract_labeled_value(text: str, label: str) -> str:
    pattern = rf"{re.escape(label)}\s*:?\s*(.{0,240})"
    match = re.search(pattern, text, re.IGNORECASE)
    return clean_text(match.group(1)) if match else ""


def infer_categories(text: str) -> str:
    lowered = text.lower()
    categories = sorted(term for term in SERVICE_HINTS if term in lowered and len(term) > 3)
    return ", ".join(categories[:8])


def first_heading(html: str) -> str:
    soup = BeautifulSoup(html or "", "lxml")
    heading = soup.find(["h1", "h2", "h3"])
    return clean_text(heading.get_text()) if heading else ""


def first_sentence(text: str) -> str:
    sentence = clean_text(text).split(".")[0]
    return sentence[:120]


RESULT_PAGE_MARKER = "Print & Share X Print & Share Print PDF"
DESCRIPTION_CUES = (
    "Provides",
    "Arranges",
    "Offers",
    "Coordinates",
    "Helps",
    "Operates",
    "Connects",
    "Supports",
    "Advocates",
    "Walk-in center providing",
    "Locator for",
    "Access to",
)


def extract_result_page_services(text: str, detail_url: str) -> list[dict[str, Any]]:
    if "matching service providers" not in text.lower():
        return []
    normalized = clean_text(text)
    if RESULT_PAGE_MARKER not in normalized:
        return []
    chunks = [chunk.strip() for chunk in re.split(r"\bMore Details\b", normalized) if chunk.strip()]
    records: list[dict[str, Any]] = []
    for chunk in chunks:
        record = extract_service_from_result_chunk(chunk, detail_url)
        if record:
            records.append(record)
    return records


def extract_service_from_result_chunk(chunk: str, detail_url: str) -> dict[str, Any] | None:
    if RESULT_PAGE_MARKER not in chunk:
        return None
    name_blob, body = chunk.rsplit(RESULT_PAGE_MARKER, 1)
    body = clean_text(body)
    if not body:
        return None

    name = extract_result_provider_name(name_blob)
    address = extract_address(body)
    phone = extract_phone(body) or ""
    if not any(cue.lower() in body.lower() for cue in DESCRIPTION_CUES) and not address and not phone:
        return None
    email = extract_email(body)
    hours = extract_labeled_value(body, "hours")
    eligibility = extract_labeled_value(body, "eligibility")
    description = extract_result_description(body, address=address)
    categories = infer_categories(body)

    if not name and not address and not phone:
        return None

    base_name = normalize_provider_name(name or first_sentence(body))
    display_name = choose_result_display_name(
        base_name,
        description=description,
        detail_url=detail_url,
    )
    provider_name, program_name = split_provider_program_names(base_name, display_name)

    return {
        "name": display_name,
        "provider_name": provider_name,
        "program_name": program_name,
        "description": description,
        "address": address,
        "phone": phone,
        "email": email,
        "website": detail_url,
        "hours": hours,
        "eligibility": eligibility,
        "categories": categories,
        "detail_url": detail_url,
        "category": "",
        "search_zip": "",
    }


def extract_result_provider_name(name_blob: str) -> str:
    cleaned = clean_text(name_blob)
    if not cleaned:
        return ""
    tokens = cleaned.split()
    selected: list[str] = []
    for token in reversed(tokens):
        stripped = token.strip(" ,;:-")
        if re.fullmatch(r"[A-Z0-9&'()./#-]+", stripped):
            selected.append(stripped)
            continue
        if selected:
            break
    if not selected:
        return ""
    return normalize_provider_name(" ".join(reversed(selected)))[:160]


def extract_result_description(body: str, *, address: str) -> str:
    description = body
    if address and address in description:
        description = description.split(address, 1)[0]
    for marker in ("Eligibility:", "Hours:", "Email", "Get Directions", "Visit Website"):
        if marker in description:
            description = description.split(marker, 1)[0]
    return clean_text(description[:1200])


def normalize_provider_name(name: str) -> str:
    cleaned = clean_text(name)
    if not cleaned:
        return ""
    cleaned = re.sub(r"^(?:PDF\s+)+", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*-\s*211info\s*$", "", cleaned, flags=re.IGNORECASE)
    cleaned = collapse_repeated_prefix(cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" -,:;")
    return cleaned[:160]


def collapse_repeated_prefix(text: str) -> str:
    tokens = text.split()
    limit = min(len(tokens) // 2, 8)
    for size in range(limit, 0, -1):
        left = tokens[:size]
        right = tokens[size : size * 2]
        if left == right:
            return " ".join(tokens[size:])
    return text


def is_result_page_title_name(text: str, title: str, normalized_name: str) -> bool:
    cleaned_title = normalize_provider_name(title)
    if not cleaned_title or not normalized_name:
        return False
    lowered_text = clean_text(text).lower()
    return (
        "matching service providers" in lowered_text
        and normalized_name == cleaned_title
    )


STRONG_PROGRAM_TAIL_WORDS = {
    "HELPLINE",
    "HOTLINE",
    "LOCATOR",
    "PROGRAM",
    "ADVOCACY",
    "SUPPORT",
    "CENTER",
    "CENTRE",
    "SERVICES",
    "SERVICE",
    "CLINIC",
    "CARE",
    "HOUSING",
    "HEALTH",
    "CONNECTIONS",
    "AC",
}


def choose_result_display_name(name: str, *, description: str, detail_url: str) -> str:
    normalized = normalize_provider_name(name)
    if not normalized:
        return ""
    if len(normalized.split()) < 8 or normalized != normalized.upper():
        return normalized

    slug_tokens = set(tokenize_nameish(url_slug_tail(detail_url)))
    desc_tokens = set(tokenize_nameish(description))
    tokens = normalized.split()
    best = normalized
    best_score = -1
    for size in range(2, min(5, len(tokens)) + 1):
        candidate = " ".join(tokens[-size:])
        candidate_tokens = set(tokenize_nameish(candidate))
        if not candidate_tokens:
            continue
        overlap = len(candidate_tokens & slug_tokens) * 3 + len(candidate_tokens & desc_tokens)
        tail_bonus = 2 if tokens[-1] in STRONG_PROGRAM_TAIL_WORDS else 0
        score = overlap + tail_bonus - size
        if score > best_score:
            best = candidate
            best_score = score
    if best_score >= 2:
        return best
    return normalized


def split_provider_program_names(base_name: str, display_name: str) -> tuple[str, str]:
    normalized_base = normalize_provider_name(base_name)
    normalized_display = normalize_provider_name(display_name)
    if not normalized_base:
        return "", normalized_display
    if not normalized_display or normalized_display == normalized_base:
        return normalized_base, ""

    if normalized_base.endswith(normalized_display):
        provider = normalize_provider_name(normalized_base[: -len(normalized_display)])
        if provider:
            return provider, normalized_display
    return normalized_base, normalized_display


def tokenize_nameish(text: str) -> list[str]:
    normalized = unquote(str(text or "")).replace("-", " ").replace("/", " ").replace("*", " ")
    return [token for token in re.findall(r"[A-Za-z0-9']+", normalized.upper()) if len(token) >= 2]


def path_parts(url: str) -> list[str]:
    return [part for part in urlparse(str(url or "")).path.split("/") if part]


def is_probably_retryable_error(error: str) -> bool:
    lowered = str(error or "").lower()
    if not lowered:
        return False
    hard_fail_markers = ("404", "not found", "410", "gone")
    if any(marker in lowered for marker in hard_fail_markers):
        return False
    retry_markers = (
        "timed out",
        "timeout",
        "temporarily unavailable",
        "too many requests",
        "429",
        "500",
        "502",
        "503",
        "504",
        "connection reset",
        "connection aborted",
        "remote disconnected",
        "ssl",
    )
    return any(marker in lowered for marker in retry_markers)


def is_junk_failed_url(url: str) -> bool:
    lowered = str(url or "").lower()
    if not lowered:
        return True
    if "/cdn-cgi/" in lowered or "resources@" in lowered:
        return True
    if "/blog" in lowered or "/update/" in lowered:
        return True
    parts = path_parts(lowered)
    if len(parts) >= 4 and parts[:1] == ["get-help"]:
        return True
    return False


def url_slug_tail(url: str) -> str:
    path = urlparse(str(url or "")).path.rstrip("/")
    return path.split("/")[-1] if path else ""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def external_tools_enabled() -> bool:
    raw = os.getenv("SCRAPER_ENABLE_IPFS_TOOLS", "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the persistent 211info agentic ETL daemon")
    parser.add_argument("--once", action="store_true", help="Run one crawl/ETL pass and exit")
    parser.add_argument("--interval", type=float, default=300.0, help="Seconds between daemon passes")
    parser.add_argument("--max-pages", type=int, default=25, help="Maximum pages per pass")
    parser.add_argument(
        "--workers",
        type=int,
        default=int(os.getenv("SCRAPER_DAEMON_WORKERS", "1")),
        help="Concurrent fetch workers per daemon pass",
    )
    parser.add_argument("--output-dir", type=Path, default=Path("data"), help="Output data directory")
    parser.add_argument("--state-dir", type=Path, default=Path("data/state"), help="Daemon state directory")
    parser.add_argument(
        "--seed-url",
        action="append",
        dest="seed_urls",
        default=[],
        help="Seed URL. May be passed multiple times.",
    )
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
    cfg = Config(raw_dir=args.output_dir / "raw", processed_dir=args.output_dir / "processed")
    daemon = AgenticCrawlerDaemon(
        cfg,
        state_path=args.state_dir / "agentic_daemon_state.json",
        strategy_path=args.state_dir / "daemon_strategy.json",
    )
    seeds = args.seed_urls or [cfg.base_url, cfg.gethelp_url]

    while True:
        result = daemon.run_once(seed_urls=seeds, max_pages=args.max_pages, max_workers=args.workers)
        logger.info("Agentic daemon pass complete: %s", result)
        if args.once:
            break
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
