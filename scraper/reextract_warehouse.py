from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb

from .agentic_daemon import AgenticCrawlerDaemon, CrawlItem, FetchResult
from .config import Config
from .duckdb_etl import DuckDBETLWarehouse
from .processor import DataProcessor


def reextract_warehouse(
    *,
    warehouse_path: Path,
    source: str = "agentic_reextract_v2",
    source_run_filter: str = "",
    limit: int = 0,
) -> dict[str, object]:
    cfg = Config(raw_dir=Path("data/reextract/raw"), processed_dir=Path("data/reextract/processed"), request_delay=0)
    extractor = AgenticCrawlerDaemon(
        cfg,
        state_path=warehouse_path.parent / "reextract_state.json",
        strategy_path=warehouse_path.parent / "reextract_strategy.json",
    )
    processor = DataProcessor(cfg)
    warehouse = DuckDBETLWarehouse(warehouse_path)
    warehouse.delete_service_source(source=source)

    con = duckdb.connect(str(warehouse_path), read_only=True)
    sql = """
        SELECT source_run, url, title, body_text
        FROM crawl_pages
        WHERE lower(url) LIKE '%/get-help/%'
    """
    params: list[object] = []
    if source_run_filter:
        sql += " AND source_run = ?"
        params.append(source_run_filter)
    sql += " ORDER BY fetched_at ASC, url ASC"
    if limit > 0:
        sql += " LIMIT ?"
        params.append(int(limit))
    rows = con.execute(sql, params).fetchall()
    con.close()

    raw_records: list[dict[str, object]] = []
    raw_records_by_run: dict[str, list[dict[str, object]]] = {}
    page_count_with_records = 0
    for source_run, url, title, body_text in rows:
        result = FetchResult(url=str(url or ""), title=str(title or ""), text=str(body_text or ""), html="")
        run_name = str(source_run or "")
        item = CrawlItem(url=str(url or ""), depth=0, kind="reextract", metadata={})
        records = extractor._extract_service_records(result, item)
        if records:
            page_count_with_records += 1
        for record in records:
            payload = dict(record)
            raw_records.append(payload)
            raw_records_by_run.setdefault(run_name, []).append(payload)

    for run_name, run_records in raw_records_by_run.items():
        warehouse.append_raw_services(run_records, source=source, source_run=run_name)
        clean = processor.process(run_records)
        warehouse.append_processed_services(clean, source=source, source_run=run_name)

    clean_count = 0
    for run_records in raw_records_by_run.values():
        clean_count += len(processor.process(run_records))

    return {
        "status": "success",
        "warehouse_path": str(warehouse_path),
        "source": source,
        "source_run_filter": source_run_filter,
        "pages_scanned": len(rows),
        "pages_with_records": page_count_with_records,
        "raw_records": len(raw_records),
        "processed_records": clean_count,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Replay crawl_pages through the current extractor into the warehouse")
    parser.add_argument("--warehouse-path", type=Path, required=True)
    parser.add_argument("--source", default="agentic_reextract_v2")
    parser.add_argument("--source-run", default="")
    parser.add_argument("--limit", type=int, default=0)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    result = reextract_warehouse(
        warehouse_path=args.warehouse_path,
        source=args.source,
        source_run_filter=args.source_run,
        limit=args.limit,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
