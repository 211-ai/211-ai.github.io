"""
Archive-backed ingestion helpers for the 211 crawler.

This CLI can discover 211 URLs from Common Crawl/HuggingFace-backed indexes,
download WARC ranged records or full WARC files with explicit limits, and seed
the live daemon through an append-only external seed file.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

import requests

from .agentic_daemon import utc_now
from .utils import setup_logging

logger = logging.getLogger("scraper.archive_ingest")


DEFAULT_DOMAINS = ["www.211info.org", "gethelp.211info.org"]
DEFAULT_SHARED_SECRETS_PATH = Path.home() / ".config" / "ipfs_datasets_py" / "secrets.json"
CLOUDFLARE_KEYRING_SERVICE = "ipfs_datasets_py"
CLOUDFLARE_ACCOUNT_KEYS = (
    "IPFS_DATASETS_CLOUDFLARE_ACCOUNT_ID",
    "LEGAL_SCRAPER_CLOUDFLARE_ACCOUNT_ID",
    "CLOUDFLARE_ACCOUNT_ID",
    "CLOUDFLARE_AGENT_ACCOUNT_ID",
)
CLOUDFLARE_TOKEN_KEYS = (
    "IPFS_DATASETS_CLOUDFLARE_API_TOKEN",
    "LEGAL_SCRAPER_CLOUDFLARE_API_TOKEN",
    "CLOUDFLARE_API_TOKEN",
    "CLOUDFLARE_AGENT_API_KEY",
)


def ensure_ipfs_datasets_path() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    local_ipfs = repo_root / "ipfs_datasets_py"
    if (local_ipfs / "ipfs_datasets_py").exists() and str(local_ipfs) not in sys.path:
        sys.path.insert(0, str(local_ipfs))


def _candidate_shared_secrets_paths() -> list[Path]:
    configured = str(
        os.environ.get("IPFS_DATASETS_SECRETS_FILE")
        or os.environ.get("IPFS_DATASETS_PY_SECRETS_FILE")
        or ""
    ).strip()
    paths: list[Path] = []
    for candidate in (configured, str(DEFAULT_SHARED_SECRETS_PATH)):
        if not candidate:
            continue
        path = Path(candidate).expanduser()
        if path not in paths:
            paths.append(path)
    return paths


def load_shared_secrets() -> dict[str, str]:
    for path in _candidate_shared_secrets_paths():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(payload, dict):
            return {str(key): str(value) for key, value in payload.items() if value is not None}
    return {}


def bootstrap_cloudflare_keyring(*, secrets: dict[str, str] | None = None) -> dict[str, Any]:
    payload = secrets or load_shared_secrets()
    account_value = next((str(payload.get(name) or "").strip() for name in CLOUDFLARE_ACCOUNT_KEYS if str(payload.get(name) or "").strip()), "")
    token_value = next((str(payload.get(name) or "").strip() for name in CLOUDFLARE_TOKEN_KEYS if str(payload.get(name) or "").strip()), "")

    result = {
        "keyring_available": False,
        "account_present": bool(account_value),
        "token_present": bool(token_value),
        "synced": 0,
        "service": CLOUDFLARE_KEYRING_SERVICE,
    }
    if not account_value or not token_value:
        return result

    try:
        import keyring  # type: ignore
    except Exception:
        return result

    result["keyring_available"] = True
    synced = 0
    for name in CLOUDFLARE_ACCOUNT_KEYS:
        if str(keyring.get_password(CLOUDFLARE_KEYRING_SERVICE, name) or "").strip() != account_value:
            keyring.set_password(CLOUDFLARE_KEYRING_SERVICE, name, account_value)
            synced += 1
    for name in CLOUDFLARE_TOKEN_KEYS:
        if str(keyring.get_password(CLOUDFLARE_KEYRING_SERVICE, name) or "").strip() != token_value:
            keyring.set_password(CLOUDFLARE_KEYRING_SERVICE, name, token_value)
            synced += 1
    result["synced"] = synced
    return result


def append_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("a", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1
    return count


def append_external_seed_urls(state_dir: Path, urls: Iterable[str], *, source: str) -> int:
    path = state_dir / "external_seed_urls.jsonl"
    seen: set[str] = set()
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            text = line.strip()
            if not text:
                continue
            try:
                payload = json.loads(text)
                url = str(payload.get("url") or "").strip() if isinstance(payload, dict) else text
            except json.JSONDecodeError:
                url = text
            if url:
                seen.add(url)

    records = []
    for url in urls:
        clean = str(url or "").strip()
        if clean and clean not in seen:
            records.append({"url": clean, "source": source, "added_at": utc_now()})
            seen.add(clean)
    return append_jsonl(path, records)


def is_http_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def record_url(record: dict[str, Any], *, prefer_archive_url: bool = False) -> str:
    keys = ["archive_url", "wayback_url", "url"] if prefer_archive_url else ["url", "target_uri", "archive_url", "wayback_url"]
    for key in keys:
        url = str(record.get(key) or "").strip()
        if is_http_url(url):
            return url
    return ""


def create_common_crawl_engine(args: argparse.Namespace):
    ensure_ipfs_datasets_path()
    from ipfs_datasets_py.processors.web_archiving.common_crawl_integration import (
        CommonCrawlSearchEngine,
    )

    kwargs: dict[str, Any] = {
        "mode": args.mode,
        "state_dir": args.cc_state_dir,
    }
    if args.mcp_endpoint:
        kwargs["mcp_endpoint"] = args.mcp_endpoint
    if args.cli_command:
        kwargs["cli_command"] = args.cli_command
    if args.ssh_host:
        kwargs["ssh_host"] = args.ssh_host
    return CommonCrawlSearchEngine(**kwargs)


def run_common_crawl(args: argparse.Namespace) -> dict[str, Any]:
    engine = None if args.backend == "cdx" else create_common_crawl_engine(args)
    output_dir = args.output_dir
    records_path = output_dir / "raw" / "common_crawl_records.jsonl"
    warc_record_dir = output_dir / "raw" / "common_crawl_warc_records"
    full_warc_dir = output_dir / "raw" / "common_crawl_warcs"

    all_records: list[dict[str, Any]] = []
    for domain in args.domains:
        if args.backend == "cdx":
            records = search_domain_cdx(
                domain,
                max_matches=args.max_matches,
                crawl_id=args.collection,
                include_www_alias=args.include_www_alias,
                scan_limit=args.cdx_scan_limit,
                statuses=set(args.status or []),
                mime_contains=args.mime_contains,
            )
        else:
            records = engine.search_domain(
                domain,
                max_matches=args.max_matches,
                collection=args.collection,
                year=args.year,
                max_parquet_files=args.max_parquet_files,
                per_parquet_limit=args.per_parquet_limit,
                hf_remote_meta=not args.no_hf_remote_meta,
            )
        for record in records:
            item = dict(record)
            item["searched_domain"] = domain
            item["discovered_at"] = utc_now()
            all_records.append(item)
        logger.info("Common Crawl domain=%s records=%d", domain, len(records))

    all_records = filter_and_rank_records(
        all_records,
        url_contains=list(args.url_contains or []),
        url_excludes=list(args.url_excludes or []),
        statuses=set(args.status or []),
        mime_contains=args.mime_contains,
        prefer_service_paths=args.prefer_service_paths,
    )

    append_jsonl(records_path, all_records)
    urls = [url for url in (record_url(item, prefer_archive_url=args.prefer_archive_urls) for item in all_records) if url]
    enqueued = append_external_seed_urls(args.state_dir, urls, source="common_crawl") if args.enqueue else 0

    fetched_records = 0
    fetched_paths: list[Path] = []
    if args.fetch_records > 0:
        warc_record_dir.mkdir(parents=True, exist_ok=True)
        for record in all_records:
            if fetched_records >= args.fetch_records:
                break
            filename = str(record.get("warc_filename") or "").strip()
            offset = record.get("warc_offset")
            length = record.get("warc_length")
            if not filename or offset in {None, ""} or length in {None, ""}:
                continue
            try:
                if engine is not None:
                    raw = engine.fetch_warc_record(
                        filename,
                        int(offset),
                        int(length),
                        max_bytes=args.max_record_bytes,
                        full_warc_cache_dir=str(full_warc_dir) if args.use_full_warc_cache else None,
                    )
                else:
                    raw = fetch_warc_record_cdx(
                        filename,
                        int(offset),
                        int(length),
                        max_bytes=args.max_record_bytes,
                    )
            except Exception as exc:
                logger.warning("WARC record fetch failed for %s @ %s: %s", filename, offset, exc)
                continue
            out = warc_record_dir / f"record_{fetched_records:06d}.warc"
            out.write_bytes(raw)
            fetched_paths.append(out)
            fetched_records += 1

    full_warcs = 0
    full_warc_paths: list[Path] = []
    if args.download_full_warcs > 0:
        full_warc_dir.mkdir(parents=True, exist_ok=True)
        for filename in unique_warc_filenames(all_records):
            if full_warcs >= args.download_full_warcs:
                break
            if download_full_warc(filename, full_warc_dir, max_bytes=args.full_warc_max_bytes):
                full_warc_paths.append(full_warc_dir / Path(filename).name)
                full_warcs += 1

    warc_etl_result: dict[str, Any] | None = None
    if args.etl_warc:
        from .warc_etl import etl_warc_paths

        warc_paths = [*fetched_paths, *full_warc_paths]
        if args.etl_existing_warc_dir:
            warc_paths.extend(sorted(Path(args.etl_existing_warc_dir).glob("*.warc")))
            warc_paths.extend(sorted(Path(args.etl_existing_warc_dir).glob("*.warc.gz")))
        warc_etl_result = etl_warc_paths(
            warc_paths,
            output_dir=args.output_dir,
            state_dir=args.state_dir,
            basename=args.etl_basename,
            include_blocked=args.include_blocked_warc,
        )

    return {
        "status": "success",
        "records": len(all_records),
        "seed_urls": len(urls),
        "enqueued": enqueued,
        "fetched_warc_records": fetched_records,
        "downloaded_full_warcs": full_warcs,
        "warc_etl": warc_etl_result,
        "records_path": str(records_path),
    }


def search_domain_cdx(
    domain: str,
    *,
    max_matches: int,
    crawl_id: str | None = None,
    include_www_alias: bool = False,
    scan_limit: int = 0,
    statuses: set[str] | None = None,
    mime_contains: str = "",
) -> list[dict[str, Any]]:
    try:
        from cdx_toolkit import CDXFetcher
    except ImportError as exc:
        raise RuntimeError("cdx_toolkit is required for --backend cdx") from exc

    clean_domain = domain.strip().removeprefix("https://").removeprefix("http://").strip("/")
    patterns = [f"{clean_domain}/*"]
    if include_www_alias and clean_domain.startswith("www."):
        patterns.append(f"{clean_domain[4:]}/*")
    elif include_www_alias and not clean_domain.startswith("www."):
        patterns.append(f"www.{clean_domain}/*")

    records: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    cdx = CDXFetcher(source=crawl_id or "cc")
    remaining = int(max_matches)
    scanned_budget = int(scan_limit) if int(scan_limit or 0) > 0 else max(int(max_matches) * 20, int(max_matches))
    for pattern in patterns:
        if remaining <= 0:
            break
        for record in cdx.iter(url=pattern, limit=scanned_budget):
            data = dict(record.data)
            if not cdx_record_matches(data, statuses=statuses, mime_contains=mime_contains):
                continue
            url = str(data.get("url") or "").strip()
            timestamp = str(data.get("timestamp") or "").strip()
            key = (url, timestamp)
            if key in seen:
                continue
            seen.add(key)
            normalized = normalize_cdx_record(data)
            records.append(normalized)
            remaining -= 1
            if remaining <= 0:
                break
    return records


def cdx_record_matches(
    data: dict[str, Any],
    *,
    statuses: set[str] | None = None,
    mime_contains: str = "",
) -> bool:
    if statuses:
        status = str(data.get("status") or "").strip()
        if status not in statuses:
            return False
    if mime_contains:
        needle = mime_contains.lower()
        mime = f"{data.get('mime') or ''} {data.get('mime-detected') or ''}".lower()
        if needle not in mime:
            return False
    return True


def record_matches_url_filters(
    record: dict[str, Any],
    *,
    url_contains: list[str],
    url_excludes: list[str],
) -> bool:
    url = str(record.get("url") or "").strip().lower()
    if url_contains:
        needles = [item.lower() for item in url_contains if str(item).strip()]
        if needles and not any(needle in url for needle in needles):
            return False
    if url_excludes:
        blocked = [item.lower() for item in url_excludes if str(item).strip()]
        if any(needle in url for needle in blocked):
            return False
    return True


def record_rank(
    record: dict[str, Any],
    *,
    prefer_service_paths: bool,
) -> tuple[int, int, str]:
    url = str(record.get("url") or "").strip().lower()
    status = str(record.get("status") or "").strip()
    mime = f"{record.get('mime') or ''} {record.get('mime-detected') or ''}".lower()
    score = 0
    if status == "200":
        score += 100
    elif status.startswith("3"):
        score += 20
    elif status == "403":
        score -= 50
    if "html" in mime:
        score += 25
    if prefer_service_paths:
        if "/get-help/" in url:
            score += 80
        if "/get-help/" in url and url.rstrip("/").count("/") >= 5:
            score += 60
        if any(term in url for term in ("community-", "general-", "shelter", "housing", "food", "mental-health")):
            score += 20
        if url.endswith("/get-help/") or url.endswith("/get-help"):
            score -= 40
        if url.endswith("/basic-needs/") or url.endswith("/food/"):
            score -= 20
    timestamp = str(record.get("timestamp") or "")
    return (score, len(url), timestamp)


def filter_and_rank_records(
    records: list[dict[str, Any]],
    *,
    url_contains: list[str],
    url_excludes: list[str],
    statuses: set[str],
    mime_contains: str,
    prefer_service_paths: bool,
) -> list[dict[str, Any]]:
    filtered = [
        record
        for record in records
        if cdx_record_matches(record, statuses=statuses or None, mime_contains=mime_contains)
        and record_matches_url_filters(record, url_contains=url_contains, url_excludes=url_excludes)
    ]
    return sorted(
        filtered,
        key=lambda record: record_rank(record, prefer_service_paths=prefer_service_paths),
        reverse=True,
    )


def normalize_cdx_record(data: dict[str, Any]) -> dict[str, Any]:
    item = dict(data)
    if "filename" in item and "warc_filename" not in item:
        item["warc_filename"] = item.get("filename")
    if "offset" in item and "warc_offset" not in item:
        item["warc_offset"] = item.get("offset")
    if "length" in item and "warc_length" not in item:
        item["warc_length"] = item.get("length")
    timestamp = str(item.get("timestamp") or "").strip()
    url = str(item.get("url") or "").strip()
    if timestamp and url:
        item.setdefault("wayback_url", f"https://web.archive.org/web/{timestamp}/{url}")
        item.setdefault("archive_url", item["wayback_url"])
    item.setdefault("source", "common_crawl_cdx")
    return item


def fetch_warc_record_cdx(
    warc_filename: str,
    warc_offset: int,
    warc_length: int,
    *,
    max_bytes: int,
) -> bytes:
    if max_bytes and int(warc_length) > int(max_bytes):
        raise RuntimeError(f"WARC record length {warc_length} exceeds max_bytes {max_bytes}")
    url = f"https://data.commoncrawl.org/{warc_filename}"
    end = int(warc_offset) + int(warc_length) - 1
    headers = {
        "Range": f"bytes={int(warc_offset)}-{end}",
        "User-Agent": "211-AI-CommonCrawlIngest/1.0",
    }
    response = requests.get(url, headers=headers, timeout=60)
    response.raise_for_status()
    return response.content


def unique_warc_filenames(records: Iterable[dict[str, Any]]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for record in records:
        filename = str(record.get("warc_filename") or "").strip()
        if filename and filename not in seen:
            seen.add(filename)
            out.append(filename)
    return out


def download_full_warc(filename: str, output_dir: Path, *, max_bytes: int = 0) -> bool:
    url = f"https://data.commoncrawl.org/{filename}"
    target = output_dir / Path(filename).name
    tmp = target.with_suffix(target.suffix + ".part")
    headers = {"User-Agent": "211-AI-CommonCrawlIngest/1.0"}
    try:
        with requests.get(url, headers=headers, stream=True, timeout=60) as response:
            response.raise_for_status()
            total = 0
            with tmp.open("wb") as fh:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if not chunk:
                        continue
                    total += len(chunk)
                    if max_bytes and total > max_bytes:
                        raise RuntimeError(
                            f"full WARC exceeds --full-warc-max-bytes ({max_bytes})"
                        )
                    fh.write(chunk)
        tmp.replace(target)
        return True
    except Exception as exc:
        logger.warning("Full WARC download failed for %s: %s", filename, exc)
        try:
            tmp.unlink(missing_ok=True)
        except Exception:
            pass
        return False


async def run_cloudflare(args: argparse.Namespace) -> dict[str, Any]:
    ensure_ipfs_datasets_path()
    from ipfs_datasets_py.processors.web_archiving.cloudflare_browser_rendering_engine import (
        crawl_with_cloudflare_browser_rendering,
    )
    from ipfs_datasets_py.processors.web_archiving.cloudflare_browser_rendering_engine import (
        _resolve_credentials,
    )

    records_path = args.output_dir / "raw" / "cloudflare_crawl_records.jsonl"
    keyring_bootstrap = bootstrap_cloudflare_keyring()
    resolved_account_id, resolved_api_token = _resolve_credentials()
    all_records: list[dict[str, Any]] = []
    job_results: list[dict[str, Any]] = []
    for url in args.seed_urls:
        result = await crawl_with_cloudflare_browser_rendering(
            url,
            account_id=resolved_account_id,
            api_token=resolved_api_token,
            wait_for_completion=True,
            timeout_seconds=args.timeout_seconds,
            poll_interval_seconds=args.poll_interval_seconds,
            limit=args.limit,
            depth=args.depth,
            formats=args.formats,
            render=args.render,
            source=args.source,
            max_age=args.max_age,
            modified_since=args.modified_since,
            user_agent=args.user_agent,
            include_subdomains=args.include_subdomains,
            include_external_links=args.include_external_links,
            include_patterns=args.include_patterns,
            exclude_patterns=args.exclude_patterns,
            extra_body=json.loads(args.extra_body) if args.extra_body else None,
        )
        job_results.append(result)
        for record in result.get("records") or []:
            if isinstance(record, dict):
                item = dict(record)
                item["submitted_url"] = url
                item["discovered_at"] = utc_now()
                all_records.append(item)

    append_jsonl(records_path, all_records)
    urls = [url for url in (record_url(item) for item in all_records) if url]
    enqueued = append_external_seed_urls(args.state_dir, urls, source="cloudflare") if args.enqueue else 0
    return {
        "status": "success",
        "jobs": len(job_results),
        "records": len(all_records),
        "seed_urls": len(urls),
        "enqueued": enqueued,
        "records_path": str(records_path),
        "job_statuses": [item.get("status") for item in job_results],
        "keyring_bootstrap": keyring_bootstrap,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Archive-backed ingestion for 211 crawler")
    parser.add_argument("--output-dir", type=Path, default=Path("data/live"))
    parser.add_argument("--state-dir", type=Path, default=Path("data/live/state"))
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    sub = parser.add_subparsers(dest="command", required=True)

    cc = sub.add_parser("common-crawl", help="Discover and optionally download Common Crawl data")
    cc.add_argument("--backend", choices=["cdx", "ipfs"], default="cdx")
    cc.add_argument("--domain", action="append", dest="domains", default=[])
    cc.add_argument("--max-matches", type=int, default=1000)
    cc.add_argument("--collection")
    cc.add_argument("--year")
    cc.add_argument("--max-parquet-files", type=int, default=20)
    cc.add_argument("--per-parquet-limit", type=int, default=100)
    cc.add_argument("--include-www-alias", action="store_true")
    cc.add_argument("--cdx-scan-limit", type=int, default=0)
    cc.add_argument("--status", action="append", default=[])
    cc.add_argument("--mime-contains", default="")
    cc.add_argument("--url-contains", action="append", default=[])
    cc.add_argument("--url-excludes", action="append", default=[])
    cc.add_argument("--prefer-service-paths", action="store_true")
    cc.add_argument("--mode", choices=["local", "remote", "cli"], default="local")
    cc.add_argument("--mcp-endpoint")
    cc.add_argument("--cli-command", default="ccindex")
    cc.add_argument("--ssh-host")
    cc.add_argument("--cc-state-dir", type=Path, default=Path("data/common_crawl_state"))
    cc.add_argument("--no-hf-remote-meta", action="store_true")
    cc.add_argument("--enqueue", action="store_true")
    cc.add_argument("--prefer-archive-urls", action="store_true")
    cc.add_argument("--fetch-records", type=int, default=0)
    cc.add_argument("--max-record-bytes", type=int, default=2_000_000)
    cc.add_argument("--use-full-warc-cache", action="store_true")
    cc.add_argument("--download-full-warcs", type=int, default=0)
    cc.add_argument("--full-warc-max-bytes", type=int, default=0)
    cc.add_argument("--etl-warc", action="store_true", help="Unpack and ETL fetched/full WARC files")
    cc.add_argument("--etl-existing-warc-dir", type=Path)
    cc.add_argument("--etl-basename", default="services_warc")
    cc.add_argument("--include-blocked-warc", action="store_true")

    cf = sub.add_parser("cloudflare", help="Run Cloudflare Browser Rendering crawl jobs")
    cf.add_argument("--seed-url", action="append", dest="seed_urls", default=[])
    cf.add_argument("--limit", type=int, default=1000)
    cf.add_argument("--depth", type=int, default=2)
    cf.add_argument("--formats", nargs="+", default=["html"])
    cf.add_argument("--render", action=argparse.BooleanOptionalAction, default=True)
    cf.add_argument("--source")
    cf.add_argument("--max-age", type=int)
    cf.add_argument("--modified-since", type=int)
    cf.add_argument("--user-agent")
    cf.add_argument("--include-subdomains", action=argparse.BooleanOptionalAction, default=True)
    cf.add_argument("--include-external-links", action=argparse.BooleanOptionalAction, default=False)
    cf.add_argument("--include-patterns", nargs="*", default=None)
    cf.add_argument("--exclude-patterns", nargs="*", default=None)
    cf.add_argument("--extra-body", help="Raw JSON object merged into Cloudflare crawl payload")
    cf.add_argument("--timeout-seconds", type=int, default=300)
    cf.add_argument("--poll-interval-seconds", type=float, default=3.0)
    cf.add_argument("--enqueue", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    setup_logging(getattr(logging, args.log_level))
    if args.command == "common-crawl":
        if not args.domains:
            args.domains = list(DEFAULT_DOMAINS)
        result = run_common_crawl(args)
    elif args.command == "cloudflare":
        if not args.seed_urls:
            args.seed_urls = ["https://www.211info.org", "https://gethelp.211info.org"]
        result = asyncio.run(run_cloudflare(args))
    else:
        parser.error(f"unknown command: {args.command}")
        return
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
