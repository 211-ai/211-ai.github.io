from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import duckdb

if TYPE_CHECKING:
    from .agentic_daemon import CrawlItem, CrawlState


class DuckDBCrawlStore:
    """DuckDB-backed durable queue and dedupe store for the agentic crawler."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self, *, read_only: bool = False):
        return duckdb.connect(str(self.db_path), read_only=read_only)

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS queue (
                    seq BIGINT PRIMARY KEY,
                    url TEXT UNIQUE NOT NULL,
                    depth INTEGER NOT NULL,
                    kind TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    priority INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'queued',
                    enqueued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    claimed_at TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS seen_urls (
                    url TEXT PRIMARY KEY,
                    seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS failed_urls (
                    url TEXT PRIMARY KEY,
                    failures INTEGER NOT NULL DEFAULT 0,
                    last_error TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS pattern_yield_stats (
                    pattern TEXT PRIMARY KEY,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    successes INTEGER NOT NULL DEFAULT 0,
                    fetch_failures INTEGER NOT NULL DEFAULT 0,
                    last_url TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute("DROP VIEW IF EXISTS queue_summary")
            conn.execute("DROP VIEW IF EXISTS queue_priority_frontier")
            conn.execute("DROP VIEW IF EXISTS failure_summary")
            conn.execute("DROP VIEW IF EXISTS queue_pattern_frontier")
            queue_columns = {
                str(row[1])
                for row in conn.execute("PRAGMA table_info('queue')").fetchall()
            }
            if "priority" not in queue_columns:
                conn.execute("ALTER TABLE queue ADD COLUMN priority INTEGER")
                conn.execute("UPDATE queue SET priority = 0 WHERE priority IS NULL")
            rows = conn.execute("SELECT seq, url, depth, kind FROM queue").fetchall()
            for seq, url, depth, kind in rows:
                conn.execute(
                    "UPDATE queue SET priority = ? WHERE seq = ?",
                    [score_queue_item(str(url), depth=int(depth), kind=str(kind)), int(seq)],
                )
            conn.execute("UPDATE queue SET status = 'queued', claimed_at = NULL WHERE status = 'active'")
        with self._connect() as conn:
            conn.execute(
                """
                CREATE OR REPLACE VIEW queue_summary AS
                SELECT
                    status,
                    COUNT(*) AS url_count,
                    MIN(priority) AS min_priority,
                    MAX(priority) AS max_priority
                FROM queue
                GROUP BY status
                """
            )
            conn.execute(
                """
                CREATE OR REPLACE VIEW queue_priority_frontier AS
                SELECT
                    url,
                    depth,
                    kind,
                    priority,
                    status,
                    enqueued_at
                FROM queue
                WHERE status = 'queued'
                ORDER BY priority DESC, seq ASC
                """
            )
            conn.execute(
                """
                CREATE OR REPLACE VIEW failure_summary AS
                SELECT
                    url,
                    failures,
                    last_error,
                    updated_at
                FROM failed_urls
                ORDER BY failures DESC, updated_at DESC
                """
            )
            conn.execute(
                """
                CREATE OR REPLACE VIEW queue_pattern_frontier AS
                WITH queued AS (
                    SELECT
                        regexp_extract(lower(url), '(/get-help/[^/]+/)', 1) AS pattern,
                        priority
                    FROM queue
                    WHERE status = 'queued'
                )
                SELECT
                    queued.pattern,
                    COUNT(*) AS queued_urls,
                    MAX(queued.priority) AS max_priority,
                    AVG(queued.priority) AS avg_priority,
                    COALESCE(stats.attempts, 0) AS attempts,
                    COALESCE(stats.successes, 0) AS successes,
                    COALESCE(stats.fetch_failures, 0) AS fetch_failures,
                    CASE
                        WHEN COALESCE(stats.attempts, 0) > 0
                            THEN CAST(stats.successes AS DOUBLE) / CAST(stats.attempts AS DOUBLE)
                        ELSE NULL
                    END AS success_rate
                FROM queued
                LEFT JOIN pattern_yield_stats AS stats
                    ON queued.pattern = stats.pattern
                WHERE queued.pattern IS NOT NULL AND queued.pattern <> ''
                GROUP BY
                    queued.pattern,
                    stats.attempts,
                    stats.successes,
                    stats.fetch_failures
                ORDER BY max_priority DESC, queued_urls DESC, queued.pattern ASC
                """
            )

    def migrate_from_state(self, state: "CrawlState") -> None:
        if not state.queue and not state.seen_urls and not state.failed_urls:
            return
        if self.queue_count(include_active=True) > 0 or self.seen_count() > 0 or self.failed_count() > 0:
            return
        self.enqueue_items(state.queue)
        if state.seen_urls:
            with self._connect() as conn:
                for url in sorted(state.seen_urls):
                    conn.execute(
                        "INSERT INTO seen_urls(url) VALUES (?) ON CONFLICT(url) DO NOTHING",
                        [url],
                    )
        if state.failed_urls:
            with self._connect() as conn:
                for url, failures in state.failed_urls.items():
                    conn.execute(
                        """
                        INSERT INTO failed_urls(url, failures, last_error)
                        VALUES (?, ?, '')
                        ON CONFLICT(url) DO UPDATE
                        SET failures = excluded.failures,
                            updated_at = now()
                        """,
                        [url, int(failures)],
                    )

    def enqueue_items(self, items: list["CrawlItem"]) -> int:
        if not items:
            return 0
        inserted = 0
        with self._connect() as conn:
            next_seq = int(conn.execute("SELECT COALESCE(MAX(seq), 0) + 1 FROM queue").fetchone()[0])
            for item in items:
                url = str(item.url or "").strip()
                if not url:
                    continue
                exists = conn.execute(
                    """
                    SELECT 1
                    FROM queue
                    WHERE url = ?
                    UNION ALL
                    SELECT 1
                    FROM seen_urls
                    WHERE url = ?
                    LIMIT 1
                    """,
                    [url, url],
                ).fetchone()
                if exists:
                    continue
                conn.execute(
                    """
                    INSERT INTO queue(seq, url, depth, kind, metadata_json, priority, status)
                    VALUES (?, ?, ?, ?, ?, ?, 'queued')
                    """,
                    [
                        next_seq,
                        url,
                        int(item.depth),
                        str(item.kind),
                        json.dumps(dict(item.metadata or {}), ensure_ascii=False),
                        score_queue_item(url, depth=int(item.depth), kind=str(item.kind)),
                    ],
                )
                next_seq += 1
                inserted += 1
        return inserted

    def apply_strategy_priorities(self, strategy: dict[str, object]) -> None:
        stats_map = {str(row["pattern"]): row for row in self.pattern_yield_stats()}
        with self._connect() as conn:
            rows = conn.execute("SELECT seq, url, depth, kind FROM queue").fetchall()
            for seq, url, depth, kind in rows:
                pattern = pattern_prefix_for_url(str(url))
                conn.execute(
                    "UPDATE queue SET priority = ? WHERE seq = ?",
                    [
                        score_queue_item(
                            str(url),
                            depth=int(depth),
                            kind=str(kind),
                            strategy=strategy,
                            pattern_stats=stats_map.get(pattern),
                        ),
                        int(seq),
                    ],
                )

    def claim_batch(self, *, limit: int, blocked_urls: set[str]) -> list["CrawlItem"]:
        from .agentic_daemon import CrawlItem

        blocked_urls = {str(url) for url in blocked_urls if str(url).strip()}
        claimed: list["CrawlItem"] = []
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT seq, url, depth, kind, metadata_json
                FROM queue
                WHERE status = 'queued'
                ORDER BY priority DESC, seq ASC
                """
            ).fetchall()
            for seq, url, depth, kind, metadata_json in rows:
                if len(claimed) >= int(limit):
                    break
                if url in blocked_urls:
                    conn.execute("DELETE FROM queue WHERE seq = ?", [seq])
                    continue
                conn.execute(
                    "UPDATE queue SET status = 'active', claimed_at = CURRENT_TIMESTAMP WHERE seq = ?",
                    [seq],
                )
                claimed.append(
                    CrawlItem(
                        url=str(url),
                        depth=int(depth),
                        kind=str(kind),
                        metadata=json.loads(str(metadata_json) or "{}"),
                    )
                )
        return claimed

    def mark_seen(self, url: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM queue WHERE url = ?", [url])
            conn.execute("DELETE FROM failed_urls WHERE url = ?", [url])
            conn.execute(
                "INSERT INTO seen_urls(url) VALUES (?) ON CONFLICT(url) DO NOTHING",
                [url],
            )

    def mark_failed(self, url: str, *, error: str = "") -> int:
        with self._connect() as conn:
            conn.execute("DELETE FROM queue WHERE url = ?", [url])
            conn.execute(
                """
                INSERT INTO failed_urls(url, failures, last_error)
                VALUES (?, 1, ?)
                ON CONFLICT(url) DO UPDATE
                SET failures = failed_urls.failures + 1,
                    last_error = excluded.last_error,
                    updated_at = now()
                """,
                [url, error],
            )
            row = conn.execute("SELECT failures FROM failed_urls WHERE url = ?", [url]).fetchone()
        return int(row[0]) if row else 1

    def record_pattern_outcome(self, url: str, *, extracted: bool, fetch_success: bool) -> None:
        pattern = pattern_prefix_for_url(url)
        if not pattern:
            return
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO pattern_yield_stats(pattern, attempts, successes, fetch_failures, last_url)
                VALUES (?, 1, ?, ?, ?)
                ON CONFLICT(pattern) DO UPDATE
                SET attempts = pattern_yield_stats.attempts + 1,
                    successes = pattern_yield_stats.successes + excluded.successes,
                    fetch_failures = pattern_yield_stats.fetch_failures + excluded.fetch_failures,
                    last_url = excluded.last_url,
                    updated_at = now()
                """,
                [
                    pattern,
                    1 if extracted else 0,
                    0 if fetch_success else 1,
                    str(url),
                ],
            )

    def queue_count(self, *, include_active: bool = False) -> int:
        status_sql = "IN ('queued', 'active')" if include_active else "= 'queued'"
        with self._connect(read_only=True) as conn:
            row = conn.execute(f"SELECT COUNT(*) FROM queue WHERE status {status_sql}").fetchone()
        return int(row[0]) if row else 0

    def seen_count(self) -> int:
        with self._connect(read_only=True) as conn:
            row = conn.execute("SELECT COUNT(*) FROM seen_urls").fetchone()
        return int(row[0]) if row else 0

    def failed_count(self) -> int:
        with self._connect(read_only=True) as conn:
            row = conn.execute("SELECT COUNT(*) FROM failed_urls").fetchone()
        return int(row[0]) if row else 0

    def queue_preview(self, *, limit: int = 50) -> list["CrawlItem"]:
        from .agentic_daemon import CrawlItem

        with self._connect(read_only=True) as conn:
            rows = conn.execute(
                """
                SELECT url, depth, kind, metadata_json
                FROM queue
                WHERE status = 'queued'
                ORDER BY priority DESC, seq ASC
                LIMIT ?
                """,
                [int(limit)],
            ).fetchall()
        return [
            CrawlItem(
                url=str(url),
                depth=int(depth),
                kind=str(kind),
                metadata=json.loads(str(metadata_json) or "{}"),
            )
            for url, depth, kind, metadata_json in rows
        ]

    def failed_map(self) -> dict[str, int]:
        with self._connect(read_only=True) as conn:
            rows = conn.execute("SELECT url, failures FROM failed_urls ORDER BY url").fetchall()
        return {str(url): int(failures) for url, failures in rows}

    def failed_entries(self) -> list[dict[str, str | int]]:
        with self._connect(read_only=True) as conn:
            rows = conn.execute(
                """
                SELECT url, failures, COALESCE(last_error, '')
                FROM failed_urls
                ORDER BY failures DESC, url ASC
                """
            ).fetchall()
        return [
            {"url": str(url), "failures": int(failures), "last_error": str(last_error)}
            for url, failures, last_error in rows
        ]

    def pattern_yield_stats(self) -> list[dict[str, int | str | float]]:
        with self._connect(read_only=True) as conn:
            rows = conn.execute(
                """
                SELECT
                    pattern,
                    attempts,
                    successes,
                    fetch_failures,
                    CASE
                        WHEN attempts > 0 THEN CAST(successes AS DOUBLE) / CAST(attempts AS DOUBLE)
                        ELSE 0.0
                    END AS success_rate
                FROM pattern_yield_stats
                ORDER BY attempts DESC, pattern ASC
                """
            ).fetchall()
        return [
            {
                "pattern": str(pattern),
                "attempts": int(attempts),
                "successes": int(successes),
                "fetch_failures": int(fetch_failures),
                "success_rate": float(success_rate),
            }
            for pattern, attempts, successes, fetch_failures, success_rate in rows
        ]

    def upsert_pattern_yield_stats(self, rows: list[dict[str, int | str]]) -> int:
        if not rows:
            return 0
        merged = 0
        with self._connect() as conn:
            for row in rows:
                pattern = str(row.get("pattern") or "").strip()
                if not pattern:
                    continue
                conn.execute(
                    """
                    INSERT INTO pattern_yield_stats(pattern, attempts, successes, fetch_failures, last_url)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(pattern) DO UPDATE
                    SET attempts = GREATEST(pattern_yield_stats.attempts, excluded.attempts),
                        successes = GREATEST(pattern_yield_stats.successes, excluded.successes),
                        fetch_failures = GREATEST(pattern_yield_stats.fetch_failures, excluded.fetch_failures),
                        last_url = CASE
                            WHEN excluded.last_url <> '' THEN excluded.last_url
                            ELSE pattern_yield_stats.last_url
                        END,
                        updated_at = now()
                    """,
                    [
                        pattern,
                        int(row.get("attempts") or 0),
                        int(row.get("successes") or 0),
                        int(row.get("fetch_failures") or 0),
                        str(row.get("last_url") or ""),
                    ],
                )
                merged += 1
        return merged


def score_queue_item(
    url: str,
    *,
    depth: int,
    kind: str,
    strategy: dict[str, object] | None = None,
    pattern_stats: dict[str, int | str | float] | None = None,
) -> int:
    """Prefer deep service-detail URLs over roots and category pages."""
    lowered = str(url or "").strip().lower()
    parsed = urlparse(lowered)
    path = parsed.path.rstrip("/")
    segments = [segment for segment in path.split("/") if segment]

    score = 0
    if kind == "seed":
        score += 10
    if kind == "discovered":
        score += 20
    if "/get-help/" in lowered:
        score += 120
    if len(segments) >= 3:
        score += min(50, len(segments) * 8)
    if len(segments) >= 4 and "/get-help/" in lowered:
        score += 80
    if any(term in lowered for term in ("community-", "general-", "shelter", "housing", "food", "mental", "youth", "utility")):
        score += 25
    if path in {"", "/"}:
        score -= 120
    if lowered.endswith("/get-help") or lowered.endswith("/get-help/"):
        score -= 80
    if any(
        lowered.endswith(suffix)
        for suffix in (
            "/food/",
            "/basic-needs/",
            "/housing-shelter/",
            "/mental-behavioral-health/",
            "/diverse-populations/",
        )
    ):
        score -= 35
    deprioritized_patterns = [
        str(item).strip().lower()
        for item in ((strategy or {}).get("deprioritized_url_patterns", []) if strategy else [])
        if str(item).strip()
    ]
    if any(pattern in lowered for pattern in deprioritized_patterns):
        score -= 90
    attempts = int((pattern_stats or {}).get("attempts") or 0)
    successes = int((pattern_stats or {}).get("successes") or 0)
    success_rate = float((pattern_stats or {}).get("success_rate") or 0.0)
    if attempts >= 20:
        if success_rate >= 0.9:
            score += 18
        elif success_rate >= 0.75:
            score += 10
        elif success_rate < 0.5:
            score -= 20
        elif success_rate < 0.65 and successes < attempts:
            score -= 10
    score -= min(30, max(0, depth) * 3)
    return int(score)


def pattern_prefix_for_url(url: str) -> str:
    parsed = urlparse(str(url or "").strip().lower())
    path = parsed.path.rstrip("/")
    if not path or "/get-help/" not in path:
        return ""
    segments = [segment for segment in path.split("/") if segment]
    if len(segments) >= 2 and segments[0] == "get-help":
        return "/" + "/".join(segments[:2]) + "/"
    return ""
