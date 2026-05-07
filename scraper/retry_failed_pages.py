from __future__ import annotations

import argparse
import json
from pathlib import Path

from .agentic_daemon import CrawlItem, is_junk_failed_url, is_probably_retryable_error
from .duckdb_state import DuckDBCrawlStore


def classify_failed_urls(entries: list[dict[str, str | int]]) -> dict[str, list[dict[str, str | int]]]:
    retryable: list[dict[str, str | int]] = []
    permanent: list[dict[str, str | int]] = []
    for entry in entries:
        url = str(entry.get("url") or "")
        error = str(entry.get("last_error") or "")
        if is_junk_failed_url(url):
            permanent.append(entry)
            continue
        if is_probably_retryable_error(error):
            retryable.append(entry)
            continue
        permanent.append(entry)
    return {"retryable": retryable, "permanent": permanent}


def enqueue_retryable_failed_urls(
    *,
    state_db_path: Path,
    limit: int = 50,
    max_failures: int = 3,
) -> dict[str, int]:
    store = DuckDBCrawlStore(state_db_path)
    classified = classify_failed_urls(store.failed_entries())
    retryable = [
        entry
        for entry in classified["retryable"]
        if int(entry.get("failures") or 0) <= int(max_failures)
    ][:limit]
    enqueued = store.enqueue_items(
        [
            CrawlItem(
                url=str(entry["url"]),
                depth=1,
                kind="retry_failed",
                metadata={"retry_failed": True, "prior_failures": int(entry.get("failures") or 0)},
            )
            for entry in retryable
        ]
    )
    return {
        "failed_total": len(store.failed_entries()),
        "retryable_total": len(classified["retryable"]),
        "permanent_total": len(classified["permanent"]),
        "selected_for_retry": len(retryable),
        "enqueued": enqueued,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Requeue retryable failed 211info pages")
    parser.add_argument("--state-dir", type=Path, default=Path("data/state"), help="Daemon state directory")
    parser.add_argument("--limit", type=int, default=50, help="Maximum failed URLs to requeue")
    parser.add_argument(
        "--max-failures",
        type=int,
        default=3,
        help="Only retry failed URLs with failures at or below this threshold",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    result = enqueue_retryable_failed_urls(
        state_db_path=args.state_dir / "agentic_daemon_state.duckdb",
        limit=args.limit,
        max_failures=args.max_failures,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
