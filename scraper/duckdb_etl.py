from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import duckdb


class DuckDBETLWarehouse:
    """Queryable DuckDB warehouse for crawler and WARC ETL outputs."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self):
        return duckdb.connect(str(self.db_path))

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS crawl_pages (
                    source_run TEXT,
                    url TEXT,
                    title TEXT,
                    body_text TEXT,
                    links_json TEXT,
                    depth INTEGER,
                    kind TEXT,
                    quality_score DOUBLE,
                    archive_json TEXT,
                    fetched_at TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS raw_services (
                    source_run TEXT,
                    source TEXT,
                    name TEXT,
                    description TEXT,
                    address TEXT,
                    phone TEXT,
                    email TEXT,
                    website TEXT,
                    hours TEXT,
                    eligibility TEXT,
                    categories TEXT,
                    detail_url TEXT,
                    source_archive TEXT,
                    category TEXT,
                    search_zip TEXT,
                    payload_json TEXT,
                    captured_at TIMESTAMP DEFAULT now()
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS processed_services (
                    source_run TEXT,
                    id TEXT,
                    name TEXT,
                    description TEXT,
                    address TEXT,
                    city TEXT,
                    state TEXT,
                    zip TEXT,
                    phone TEXT,
                    email TEXT,
                    website TEXT,
                    hours TEXT,
                    eligibility TEXT,
                    languages TEXT,
                    categories TEXT,
                    accessibility TEXT,
                    source_url TEXT,
                    search_category TEXT,
                    search_zip TEXT,
                    source TEXT,
                    processed_at TIMESTAMP DEFAULT now()
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS warc_documents (
                    source_run TEXT,
                    url TEXT,
                    status_code INTEGER,
                    content_type TEXT,
                    title TEXT,
                    text TEXT,
                    warc_path TEXT,
                    record_index INTEGER,
                    metadata_json TEXT,
                    captured_at TIMESTAMP DEFAULT now()
                )
                """
            )
            for table, column in (
                ("crawl_pages", "source_run"),
                ("raw_services", "source_run"),
                ("processed_services", "source_run"),
                ("warc_documents", "source_run"),
            ):
                try:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} TEXT")
                except Exception:
                    pass

    def append_crawl_pages(self, records: list[dict[str, Any]], *, source_run: str = "") -> None:
        if not records:
            return
        with self._connect() as conn:
            for record in records:
                conn.execute(
                    """
                    INSERT INTO crawl_pages (
                        source_run, url, title, body_text, links_json, depth, kind,
                        quality_score, archive_json, fetched_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        source_run,
                        str(record.get("url") or ""),
                        str(record.get("title") or ""),
                        str(record.get("body_text") or ""),
                        json.dumps(record.get("links") or [], ensure_ascii=False),
                        int(record.get("depth") or 0),
                        str(record.get("kind") or ""),
                        float(record.get("quality_score") or 0.0),
                        json.dumps(record.get("archive") or {}, ensure_ascii=False),
                        str(record.get("fetched_at") or ""),
                    ],
                )

    def append_raw_services(self, records: list[dict[str, Any]], *, source: str, source_run: str = "") -> None:
        if not records:
            return
        with self._connect() as conn:
            for record in records:
                conn.execute(
                    """
                    INSERT INTO raw_services (
                        source_run, source, name, description, address, phone, email, website,
                        hours, eligibility, categories, detail_url, source_archive,
                        category, search_zip, payload_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        source_run,
                        source,
                        str(record.get("name") or ""),
                        str(record.get("description") or ""),
                        str(record.get("address") or ""),
                        str(record.get("phone") or ""),
                        str(record.get("email") or ""),
                        str(record.get("website") or ""),
                        str(record.get("hours") or ""),
                        str(record.get("eligibility") or ""),
                        str(record.get("categories") or ""),
                        str(record.get("detail_url") or ""),
                        str(record.get("source_archive") or ""),
                        str(record.get("category") or ""),
                        str(record.get("search_zip") or ""),
                        json.dumps(record, ensure_ascii=False),
                    ],
                )

    def append_processed_services(self, records: list[dict[str, Any]], *, source: str, source_run: str = "") -> None:
        if not records:
            return
        with self._connect() as conn:
            for record in records:
                conn.execute(
                    """
                    INSERT INTO processed_services (
                        source_run, id, name, description, address, city, state, zip,
                        phone, email, website, hours, eligibility, languages,
                        categories, accessibility, source_url, search_category,
                        search_zip, source
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        source_run,
                        str(record.get("id") or ""),
                        str(record.get("name") or ""),
                        str(record.get("description") or ""),
                        str(record.get("address") or ""),
                        str(record.get("city") or ""),
                        str(record.get("state") or ""),
                        str(record.get("zip") or ""),
                        str(record.get("phone") or ""),
                        str(record.get("email") or ""),
                        str(record.get("website") or ""),
                        str(record.get("hours") or ""),
                        str(record.get("eligibility") or ""),
                        str(record.get("languages") or ""),
                        str(record.get("categories") or ""),
                        str(record.get("accessibility") or ""),
                        str(record.get("source_url") or ""),
                        str(record.get("search_category") or ""),
                        str(record.get("search_zip") or ""),
                        source,
                    ],
                )

    def append_warc_documents(self, records: list[dict[str, Any]], *, source_run: str = "") -> None:
        if not records:
            return
        with self._connect() as conn:
            for record in records:
                conn.execute(
                    """
                    INSERT INTO warc_documents (
                        source_run, url, status_code, content_type, title, text,
                        warc_path, record_index, metadata_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        source_run,
                        str(record.get("url") or ""),
                        int(record.get("status_code") or 0),
                        str(record.get("content_type") or ""),
                        str(record.get("title") or ""),
                        str(record.get("text") or ""),
                        str(record.get("warc_path") or ""),
                        int(record.get("record_index") or 0),
                        json.dumps(record.get("metadata") or {}, ensure_ascii=False),
                    ],
                )
