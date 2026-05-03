from __future__ import annotations

import argparse
import json
from pathlib import Path

from .duckdb_etl import DuckDBETLWarehouse


def export_canonical_services(
    *,
    warehouse_path: Path,
    output_dir: Path,
    basename: str = "services_canonical",
) -> dict[str, object]:
    warehouse = DuckDBETLWarehouse(warehouse_path)
    jsonl_path = output_dir / f"{basename}.jsonl"
    csv_path = output_dir / f"{basename}.csv"
    return warehouse.export_canonical_processed_services(jsonl_path=jsonl_path, csv_path=csv_path)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export canonical processed services from DuckDB to JSONL and CSV")
    parser.add_argument("--warehouse-path", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--basename", default="services_canonical")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    result = export_canonical_services(
        warehouse_path=args.warehouse_path,
        output_dir=args.output_dir,
        basename=args.basename,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
