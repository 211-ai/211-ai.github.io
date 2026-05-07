from __future__ import annotations

import csv
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
                    provider_name TEXT,
                    program_name TEXT,
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
                    provider_name TEXT,
                    program_name TEXT,
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
                ("raw_services", "provider_name"),
                ("raw_services", "program_name"),
                ("processed_services", "provider_name"),
                ("processed_services", "program_name"),
            ):
                try:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} TEXT")
                except Exception:
                    pass
            conn.execute("DROP VIEW IF EXISTS canonical_raw_services")
            conn.execute("DROP VIEW IF EXISTS canonical_processed_services")
            conn.execute(
                """
                CREATE OR REPLACE VIEW canonical_raw_services AS
                WITH ranked AS (
                    SELECT
                        raw_services.*,
                        CASE
                            WHEN source = 'agentic_reextract_v2' THEN 300
                            WHEN source = 'warc_etl' THEN 200
                            WHEN source = 'agentic_daemon' THEN 100
                            ELSE 0
                        END AS source_priority,
                        ROW_NUMBER() OVER (
                            PARTITION BY COALESCE(
                                NULLIF(detail_url, ''),
                                NULLIF(website, ''),
                                NULLIF(name || '|' || address || '|' || phone, ''),
                                payload_json
                            )
                            ORDER BY
                                CASE
                                    WHEN source = 'agentic_reextract_v2' THEN 300
                                    WHEN source = 'warc_etl' THEN 200
                                    WHEN source = 'agentic_daemon' THEN 100
                                    ELSE 0
                                END DESC,
                                captured_at DESC,
                                source_run DESC
                        ) AS rn
                    FROM raw_services
                )
                SELECT * EXCLUDE (source_priority, rn)
                FROM ranked
                WHERE rn = 1
                """
            )
            conn.execute(
                """
                CREATE OR REPLACE VIEW canonical_processed_services AS
                WITH ranked AS (
                    SELECT
                        processed_services.*,
                        CASE
                            WHEN source = 'agentic_reextract_v2' THEN 300
                            WHEN source = 'warc_etl' THEN 200
                            WHEN source = 'agentic_daemon' THEN 100
                            ELSE 0
                        END AS source_priority,
                        ROW_NUMBER() OVER (
                            PARTITION BY COALESCE(
                                NULLIF(source_url, ''),
                                NULLIF(id, ''),
                                NULLIF(website, ''),
                                NULLIF(name || '|' || address || '|' || phone, ''),
                                name || '|' || address || '|' || phone || '|' || source
                            )
                            ORDER BY
                                CASE
                                    WHEN source = 'agentic_reextract_v2' THEN 300
                                    WHEN source = 'warc_etl' THEN 200
                                    WHEN source = 'agentic_daemon' THEN 100
                                    ELSE 0
                                END DESC,
                                processed_at DESC,
                                source_run DESC
                        ) AS rn
                    FROM processed_services
                )
                SELECT * EXCLUDE (source_priority, rn)
                FROM ranked
                WHERE rn = 1
                """
            )

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
                        source_run, source, name, provider_name, program_name, description, address, phone, email, website,
                        hours, eligibility, categories, detail_url, source_archive,
                        category, search_zip, payload_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        source_run,
                        source,
                        str(record.get("name") or ""),
                        str(record.get("provider_name") or ""),
                        str(record.get("program_name") or ""),
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
                        source_run, id, name, provider_name, program_name, description, address, city, state, zip,
                        phone, email, website, hours, eligibility, languages,
                        categories, accessibility, source_url, search_category,
                        search_zip, source
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        source_run,
                        str(record.get("id") or ""),
                        str(record.get("name") or ""),
                        str(record.get("provider_name") or ""),
                        str(record.get("program_name") or ""),
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

    def delete_service_source(self, *, source: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM raw_services WHERE source = ?", [str(source)])
            conn.execute("DELETE FROM processed_services WHERE source = ?", [str(source)])

    def export_canonical_processed_services(
        self,
        *,
        jsonl_path: Path,
        csv_path: Path,
    ) -> dict[str, Any]:
        jsonl_path.parent.mkdir(parents=True, exist_ok=True)
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        conn = duckdb.connect(str(self.db_path), read_only=True)
        rows = conn.execute(
            """
            SELECT *
            FROM canonical_processed_services
            ORDER BY source_url ASC, name ASC, provider_name ASC, program_name ASC
            """
        ).fetchall()
        columns = [str(item[0]) for item in conn.description]
        records = [
            {
                key: (value.isoformat() if hasattr(value, "isoformat") else value)
                for key, value in dict(zip(columns, row, strict=False)).items()
            }
            for row in rows
        ]
        with jsonl_path.open("w", encoding="utf-8") as fh:
            for record in records:
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        with csv_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=columns, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(records)
        conn.close()
        return {
            "status": "success",
            "record_count": len(records),
            "jsonl_path": str(jsonl_path),
            "csv_path": str(csv_path),
        }
