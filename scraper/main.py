#!/usr/bin/env python3
"""
211info.org Comprehensive Scraper — CLI entry point.

Usage examples
--------------
# Scrape all static/informational pages only:
python -m scraper.main --mode static

# Scrape the dynamic search pages (all categories, all ZIPs):
python -m scraper.main --mode browser

# Quick test: one category, two ZIPs, no detail enrichment:
python -m scraper.main --mode browser \\
    --categories food housing-shelter \\
    --zips 97201 97401 \\
    --no-enrich

# Full pipeline (static + browser):
python -m scraper.main --mode all

# BFS site crawl (follows internal links):
python -m scraper.main --mode crawl --max-pages 300

Options
-------
--mode         static | browser | crawl | all   (default: all)
--categories   space-separated list; defaults to all 18 categories
--zips         space-separated list; defaults to all configured ZIPs
--no-enrich    skip detail-page fetches (faster, less data)
--max-pages    limit for BFS crawl (default: 200)
--headless     run browser headless (default: true)
--delay        seconds between requests (default: 1.5)
--output-dir   directory to write data files (default: data/)
--log-level    DEBUG | INFO | WARNING (default: INFO)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

# Ensure the package root is importable when run as `python -m scraper.main`
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scraper.browser_scraper import BrowserScraper
from scraper.config import Config
from scraper.processor import DataProcessor
from scraper.static_scraper import StaticScraper
from scraper.storage import Storage
from scraper.utils import setup_logging


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Comprehensive scraper for 211info.org social-services data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--mode",
        choices=["static", "browser", "crawl", "all"],
        default="all",
        help="Scraping mode (default: all)",
    )
    parser.add_argument(
        "--categories",
        nargs="+",
        metavar="CAT",
        help="Service categories to search (default: all 18)",
    )
    parser.add_argument(
        "--zips",
        nargs="+",
        metavar="ZIP",
        help="ZIP codes to search (default: all configured ZIPs)",
    )
    parser.add_argument(
        "--no-enrich",
        action="store_true",
        help="Skip per-record detail-page fetches",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=200,
        metavar="N",
        help="Max pages for BFS crawl mode (default: 200)",
    )
    parser.add_argument(
        "--headless",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Run browser headless (default: true). Use --no-headless to show the browser.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.5,
        metavar="SECS",
        help="Seconds to wait between requests (default: 1.5)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "data",
        metavar="DIR",
        help="Root directory for output files (default: data/)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity (default: INFO)",
    )
    return parser.parse_args(argv)


# ---------------------------------------------------------------------------
# Mode runners
# ---------------------------------------------------------------------------

def run_static(cfg: Config, args: argparse.Namespace) -> None:
    """Scrape all static informational pages."""
    scraper = StaticScraper(cfg)
    storage = Storage(cfg.raw_dir, cfg.processed_dir)
    processor = DataProcessor(cfg)

    # robots.txt
    robots = scraper.fetch_robots()
    if robots:
        storage.save_html(robots, "robots.txt")
        print("[robots.txt]\n" + robots[:500])

    # Sitemap URLs
    sitemap_urls = scraper.fetch_sitemap_urls()
    storage.save_json(sitemap_urls, "sitemap_urls.json")
    print(f"Sitemap URLs found: {len(sitemap_urls)}")

    # Static pages
    pages = scraper.crawl_static_pages()
    storage.save_json(pages, "static_pages_raw.json")
    processor.process_static_pages(pages, "static_pages")
    print(f"Static pages scraped: {len(pages)}")


def run_crawl(cfg: Config, args: argparse.Namespace) -> None:
    """BFS crawl following internal links."""
    scraper = StaticScraper(cfg)
    storage = Storage(cfg.raw_dir, cfg.processed_dir)
    processor = DataProcessor(cfg)

    pages = scraper.crawl_site(max_pages=args.max_pages)
    storage.save_json(pages, "crawl_raw.json")
    processor.process_static_pages(pages, "crawl_pages")
    print(f"BFS crawl complete. Pages: {len(pages)}")


def run_browser(cfg: Config, args: argparse.Namespace) -> None:
    """Run the Playwright-based search scraper."""
    storage = Storage(cfg.raw_dir, cfg.processed_dir)
    processor = DataProcessor(cfg)

    async def _run():
        async with BrowserScraper(cfg) as scraper:
            # Optionally capture homepage metadata
            homepage = await scraper.scrape_homepage()
            storage.save_json(homepage, "homepage_meta.json")

            records = await scraper.run_full_scrape(
                categories=args.categories,
                zips=args.zips,
                enrich_details=not args.no_enrich,
            )
        return records

    raw_records = asyncio.run(_run())

    # Save raw JSONL immediately
    storage.append_jsonl(raw_records, "services_raw.jsonl")
    print(f"Raw service records collected: {len(raw_records)}")

    # Process + export
    clean = processor.process(raw_records)
    processor.export(clean, "services")
    print(f"Clean, unique service records: {len(clean)}")


def run_all(cfg: Config, args: argparse.Namespace) -> None:
    """Run both static and browser modes."""
    run_static(cfg, args)
    run_browser(cfg, args)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    # Configure logging
    setup_logging(getattr(logging, args.log_level))
    logger = logging.getLogger("scraper")

    # Build config from CLI overrides
    raw_dir = args.output_dir / "raw"
    processed_dir = args.output_dir / "processed"
    cfg = Config(
        headless=args.headless,
        request_delay=args.delay,
        raw_dir=raw_dir,
        processed_dir=processed_dir,
    )

    logger.info("Starting scraper | mode=%s | output=%s", args.mode, args.output_dir)

    runners = {
        "static": run_static,
        "crawl": run_crawl,
        "browser": run_browser,
        "all": run_all,
    }
    runners[args.mode](cfg, args)

    logger.info("Scraper finished.")


if __name__ == "__main__":
    main()
