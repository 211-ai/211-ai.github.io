from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .duckdb_etl import DuckDBETLWarehouse


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            text = line.strip()
            if not text:
                continue
            payload = json.loads(text)
            if isinstance(payload, dict):
                rows.append(payload)
    return rows


def discover_runs(data_dir: Path) -> list[Path]:
    runs: list[Path] = []
    for child in sorted(data_dir.iterdir()):
        if not child.is_dir():
            continue
        if (child / "raw").exists() or (child / "processed").exists():
            runs.append(child)
    return runs


def backfill_run(run_dir: Path, warehouse: DuckDBETLWarehouse) -> dict[str, int]:
    source_run = run_dir.name
    counts = {
        "crawl_pages": 0,
        "raw_services": 0,
        "processed_services": 0,
        "warc_documents": 0,
    }

    raw_dir = run_dir / "raw"
    processed_dir = run_dir / "processed"

    page_files = sorted(raw_dir.glob("*pages_raw.jsonl"))
    raw_service_files = sorted(raw_dir.glob("*services_raw*.jsonl"))
    processed_service_files = sorted(processed_dir.glob("*.jsonl"))

    for path in page_files:
        rows = load_jsonl(path)
        warehouse.append_crawl_pages(rows, source_run=source_run)
        counts["crawl_pages"] += len(rows)

    for path in raw_service_files:
        rows = load_jsonl(path)
        source = "warc_etl" if "warc" in path.name else "agentic_daemon"
        warehouse.append_raw_services(rows, source=source, source_run=source_run)
        counts["raw_services"] += len(rows)

    for path in processed_service_files:
        rows = load_jsonl(path)
        source = "warc_etl" if "warc" in path.name else "agentic_daemon"
        warehouse.append_processed_services(rows, source=source, source_run=source_run)
        counts["processed_services"] += len(rows)

    return counts


def backfill_data_dir(data_dir: Path, warehouse_path: Path) -> dict[str, Any]:
    if warehouse_path.exists():
        warehouse_path.unlink()
    warehouse = DuckDBETLWarehouse(warehouse_path)

    totals = {
        "runs": 0,
        "crawl_pages": 0,
        "raw_services": 0,
        "processed_services": 0,
        "warc_documents": 0,
    }
    per_run: dict[str, dict[str, int]] = {}

    for run_dir in discover_runs(data_dir):
        counts = backfill_run(run_dir, warehouse)
        per_run[run_dir.name] = counts
        totals["runs"] += 1
        for key, value in counts.items():
            totals[key] += value

    return {"status": "success", "warehouse_path": str(warehouse_path), "totals": totals, "runs": per_run}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill DuckDB ETL warehouse from historical JSONL artifacts")
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--warehouse-path", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    result = backfill_data_dir(args.data_dir, args.warehouse_path)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
