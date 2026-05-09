from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
IPFS_DATASETS_ROOT = REPO_ROOT / "ipfs_datasets_py"
for import_root in (IPFS_DATASETS_ROOT, REPO_ROOT):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))
os.environ.setdefault("IPFS_DATASETS_AUTO_INSTALL", "false")
os.environ.setdefault("IPFS_AUTO_INSTALL", "false")
os.environ.setdefault("IPFS_DATASETS_PY_MINIMAL_IMPORTS", "1")

from scraper.enrich_service_addresses import (  # noqa: E402
    DEFAULT_CACHE_PATH,
    DEFAULT_PORTAL_DIR,
    build_query_from_location_row,
    enrich_service_addresses,
    load_cache,
    parse_json_value,
    write_json_atomic,
)
from scraper.utils import setup_logging  # noqa: E402


logger = setup_logging()

DEFAULT_STATE_DIR = REPO_ROOT / "data" / "portal_geocoding" / "state"
DEFAULT_STATE_PREFIX = "portal_geocode"
DEFAULT_BROWSER_OUTPUT_DIR = REPO_ROOT / "wallet_interface" / "ui" / "public" / "corpus" / "211-info" / "current"
DEFAULT_BATCH_SIZE_NEW = 180
DEFAULT_BATCH_SIZE_RETRY = 60
DEFAULT_LOOP_SLEEP_SECONDS = 30.0
DEFAULT_IDLE_SLEEP_SECONDS = 600.0


def daemon_pid_path(state_dir: Path, state_prefix: str) -> Path:
    return state_dir / f"{state_prefix}_daemon.pid"


def daemon_state_path(state_dir: Path, state_prefix: str) -> Path:
    return state_dir / f"{state_prefix}_state.json"


def write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(text, encoding="utf-8")
    temp_path.replace(path)


def safe_read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def summarize_geocode_progress(
    *,
    source_dir: Path,
    cache_path: Path,
) -> dict[str, Any]:
    cache = load_cache(cache_path)
    locations_path = source_dir / "service_locations.parquet"
    locations_frame = pd.read_parquet(locations_path).fillna("")
    total_unique_queries: dict[str, str] = {}
    unresolved_query_keys: set[str] = set()

    for row in locations_frame.to_dict(orient="records"):
        query = build_query_from_location_row(row)
        if not query:
            continue
        total_unique_queries.setdefault(query.key, query.display)
        existing_geo = parse_json_value(row.get("geo_json"), {"lat": None, "lon": None})
        if isinstance(existing_geo, dict) and existing_geo.get("lat") is not None and existing_geo.get("lon") is not None:
            continue
        unresolved_query_keys.add(query.key)

    cache_status_counts: dict[str, int] = {}
    for record in cache.values():
        status = str(record.get("status") or "unknown")
        cache_status_counts[status] = cache_status_counts.get(status, 0) + 1

    uncached_remaining = 0
    cached_non_ok_remaining = 0
    cached_ok_remaining = 0
    for key in unresolved_query_keys:
        record = cache.get(key)
        if record is None:
            uncached_remaining += 1
            continue
        if record.get("status") == "ok":
            cached_ok_remaining += 1
        else:
            cached_non_ok_remaining += 1

    manifest = safe_read_json(source_dir / "service_portal_manifest.json")
    coverage = manifest.get("coverage") if isinstance(manifest.get("coverage"), dict) else {}
    service_geo = coverage.get("geo") if isinstance(coverage.get("geo"), dict) else {}
    location_geo = coverage.get("location_geo") if isinstance(coverage.get("location_geo"), dict) else {}

    return {
        "cache_entries": len(cache),
        "cache_status_counts": cache_status_counts,
        "total_unique_queries": len(total_unique_queries),
        "unresolved_query_count": len(unresolved_query_keys),
        "uncached_remaining": uncached_remaining,
        "cached_non_ok_remaining": cached_non_ok_remaining,
        "cached_ok_remaining": cached_ok_remaining,
        "remaining_query_count": uncached_remaining + cached_non_ok_remaining + cached_ok_remaining,
        "service_geo_count": int(service_geo.get("count") or 0),
        "service_geo_pct": float(service_geo.get("pct") or 0.0),
        "location_geo_count": int(location_geo.get("count") or 0),
        "location_geo_pct": float(location_geo.get("pct") or 0.0),
    }


def choose_geocode_mode(summary: dict[str, Any]) -> str:
    if int(summary.get("uncached_remaining") or 0) > 0:
        return "new"
    if int(summary.get("cached_non_ok_remaining") or 0) > 0:
        return "retry"
    return "idle"


def refresh_browser_corpus(browser_output_dir: Path) -> dict[str, Any]:
    command = [
        sys.executable,
        str(REPO_ROOT / "scraper" / "browser_graphrag_corpus.py"),
        "--output-dir",
        str(browser_output_dir),
    ]
    started_at = time.time()
    completed = subprocess.run(
        command,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    payload: dict[str, Any] = {
        "command": command,
        "returncode": int(completed.returncode),
        "duration_seconds": round(time.time() - started_at, 3),
    }
    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()
    if stdout:
        try:
            payload["result"] = json.loads(stdout)
        except Exception:
            payload["stdout_tail"] = stdout[-4000:]
    if stderr:
        payload["stderr_tail"] = stderr[-4000:]
    return payload


def write_daemon_state(path: Path, payload: dict[str, Any]) -> None:
    payload = dict(payload)
    payload["schema"] = "211-ai.portal_geocode_daemon.v1"
    payload["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    write_json_atomic(path, payload)


def run_geocode_pass(args: argparse.Namespace, *, pass_index: int) -> dict[str, Any]:
    before = summarize_geocode_progress(source_dir=args.source_dir, cache_path=args.cache_path)
    mode = choose_geocode_mode(before)
    if mode == "idle":
        return {
            "mode": "idle",
            "pass_index": pass_index,
            "before": before,
            "result": None,
            "after": before,
            "browser_refresh": None,
            "sleep_seconds": args.idle_sleep_seconds,
        }

    batch_size = args.batch_size_new if mode == "new" else args.batch_size_retry
    logger.info(
        "starting geocode pass %d mode=%s batch_size=%d uncached_remaining=%d cached_non_ok_remaining=%d",
        pass_index,
        mode,
        batch_size,
        int(before.get("uncached_remaining") or 0),
        int(before.get("cached_non_ok_remaining") or 0),
    )
    result = enrich_service_addresses(
        source_dir=args.source_dir,
        cache_path=args.cache_path,
        provider=args.provider,
        min_delay_seconds=args.min_delay_seconds,
        timeout_seconds=args.timeout_seconds,
        max_retries=args.max_retries,
        max_queries=batch_size,
        retry_misses=(mode == "retry"),
        refresh_only=False,
        overwrite=False,
    )
    after = summarize_geocode_progress(source_dir=args.source_dir, cache_path=args.cache_path)
    browser_refresh = None
    if args.refresh_browser_corpus and int(result.get("geocode_hits") or 0) > 0:
        browser_refresh = refresh_browser_corpus(args.browser_output_dir)
        logger.info(
            "browser corpus refresh returncode=%s duration_seconds=%s",
            browser_refresh.get("returncode"),
            browser_refresh.get("duration_seconds"),
        )
    return {
        "mode": mode,
        "pass_index": pass_index,
        "before": before,
        "result": result,
        "after": after,
        "browser_refresh": browser_refresh,
        "sleep_seconds": args.sleep_seconds,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Continuously geocode remaining portal service addresses")
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_PORTAL_DIR)
    parser.add_argument("--cache-path", type=Path, default=DEFAULT_CACHE_PATH)
    parser.add_argument("--browser-output-dir", type=Path, default=DEFAULT_BROWSER_OUTPUT_DIR)
    parser.add_argument("--state-dir", type=Path, default=DEFAULT_STATE_DIR)
    parser.add_argument("--state-prefix", default=DEFAULT_STATE_PREFIX)
    parser.add_argument("--provider", default="nominatim")
    parser.add_argument("--batch-size-new", type=int, default=DEFAULT_BATCH_SIZE_NEW)
    parser.add_argument("--batch-size-retry", type=int, default=DEFAULT_BATCH_SIZE_RETRY)
    parser.add_argument("--min-delay-seconds", type=float, default=1.1)
    parser.add_argument("--timeout-seconds", type=float, default=12.0)
    parser.add_argument("--max-retries", type=int, default=2)
    parser.add_argument("--sleep-seconds", type=float, default=DEFAULT_LOOP_SLEEP_SECONDS)
    parser.add_argument("--idle-sleep-seconds", type=float, default=DEFAULT_IDLE_SLEEP_SECONDS)
    parser.add_argument("--log-level", default="INFO", choices=("DEBUG", "INFO", "WARNING", "ERROR"))
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--refresh-browser-corpus", dest="refresh_browser_corpus", action="store_true")
    parser.add_argument("--no-refresh-browser-corpus", dest="refresh_browser_corpus", action="store_false")
    parser.set_defaults(refresh_browser_corpus=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    state_dir = args.state_dir.resolve()
    state_dir.mkdir(parents=True, exist_ok=True)
    pid_path = daemon_pid_path(state_dir, args.state_prefix)
    state_path = daemon_state_path(state_dir, args.state_prefix)
    write_text_atomic(pid_path, f"{os.getpid()}\n")
    logger.setLevel(getattr(logging, args.log_level.upper(), logging.INFO))

    pass_index = int(safe_read_json(state_path).get("pass_count") or 0)
    try:
        while True:
            pass_index += 1
            started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            progress = summarize_geocode_progress(source_dir=args.source_dir, cache_path=args.cache_path)
            write_daemon_state(
                state_path,
                {
                    "status": "running",
                    "heartbeat_at": started_at,
                    "pid": os.getpid(),
                    "pass_count": pass_index - 1,
                    "phase": "scan",
                    "progress": progress,
                    "config": {
                        "source_dir": str(args.source_dir),
                        "cache_path": str(args.cache_path),
                        "browser_output_dir": str(args.browser_output_dir),
                        "batch_size_new": args.batch_size_new,
                        "batch_size_retry": args.batch_size_retry,
                        "min_delay_seconds": args.min_delay_seconds,
                        "timeout_seconds": args.timeout_seconds,
                        "max_retries": args.max_retries,
                        "sleep_seconds": args.sleep_seconds,
                        "idle_sleep_seconds": args.idle_sleep_seconds,
                        "refresh_browser_corpus": args.refresh_browser_corpus,
                    },
                },
            )
            pass_result = run_geocode_pass(args, pass_index=pass_index)
            finished_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            write_daemon_state(
                state_path,
                {
                    "status": "idle" if pass_result["mode"] == "idle" else "running",
                    "heartbeat_at": finished_at,
                    "pid": os.getpid(),
                    "pass_count": pass_index,
                    "phase": "sleep" if not args.once else "done",
                    "last_run_started_at": started_at,
                    "last_run_finished_at": finished_at,
                    "last_run_mode": pass_result["mode"],
                    "last_run_result": pass_result["result"],
                    "last_browser_refresh": pass_result["browser_refresh"],
                    "progress": pass_result["after"],
                    "next_sleep_seconds": pass_result["sleep_seconds"],
                },
            )
            if args.once:
                print(json.dumps(pass_result, indent=2))
                return 0
            time.sleep(float(pass_result["sleep_seconds"]))
    finally:
        pid_path.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
