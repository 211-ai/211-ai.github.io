from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb

from .duckdb_state import DuckDBCrawlStore


def build_pattern_rows(warehouse_path: Path) -> list[dict[str, int | str]]:
    con = duckdb.connect(str(warehouse_path), read_only=True)
    rows = con.execute(
        """
        WITH crawl_patterns AS (
            SELECT
                regexp_extract(lower(url), '(/get-help/[^/]+/)', 1) AS pattern,
                url
            FROM crawl_pages
            WHERE lower(url) LIKE '%/get-help/%'
        ),
        raw_successes AS (
            SELECT DISTINCT lower(detail_url) AS detail_url
            FROM raw_services
            WHERE lower(detail_url) LIKE '%/get-help/%'
        )
        SELECT
            pattern,
            COUNT(DISTINCT crawl_patterns.url) AS attempts,
            COUNT(DISTINCT raw_successes.detail_url) AS successes,
            0 AS fetch_failures,
            MAX(crawl_patterns.url) AS last_url
        FROM crawl_patterns
        LEFT JOIN raw_successes
            ON lower(crawl_patterns.url) = raw_successes.detail_url
        WHERE pattern IS NOT NULL AND pattern <> ''
        GROUP BY 1
        ORDER BY attempts DESC, pattern ASC
        """
    ).fetchall()
    con.close()
    return [
        {
            "pattern": str(pattern),
            "attempts": int(attempts),
            "successes": int(successes),
            "fetch_failures": int(fetch_failures),
            "last_url": str(last_url or ""),
        }
        for pattern, attempts, successes, fetch_failures, last_url in rows
    ]


def backfill_pattern_stats(*, warehouse_path: Path, state_db_path: Path) -> dict[str, object]:
    rows = build_pattern_rows(warehouse_path)
    store = DuckDBCrawlStore(state_db_path)
    merged = store.upsert_pattern_yield_stats(rows)
    top = store.pattern_yield_stats()[:20]
    return {
        "status": "success",
        "warehouse_path": str(warehouse_path),
        "state_db_path": str(state_db_path),
        "pattern_count": len(rows),
        "merged": merged,
        "top_patterns": top,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill pattern yield stats from warehouse into crawl-state DuckDB")
    parser.add_argument("--warehouse-path", type=Path, required=True)
    parser.add_argument("--state-db-path", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    result = backfill_pattern_stats(warehouse_path=args.warehouse_path, state_db_path=args.state_db_path)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
