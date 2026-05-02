"""
Configuration for the 211info.org scraper.
All tuneable constants live here so the rest of the code stays clean.
"""

from __future__ import annotations

import os
from pathlib import Path


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

# ---------------------------------------------------------------------------
# Target site
# ---------------------------------------------------------------------------
BASE_URL = "https://www.211info.org"
GETHELP_URL = "https://gethelp.211info.org"

# Top-level static pages to scrape for informational content
STATIC_PAGES = [
    "/",
    "/about-211info/",
    "/about-211info/find-services/",
    "/about-211info/our-mission/",
    "/about-211info/our-team/",
    "/about-211info/our-partners/",
    "/about-211info/annual-reports/",
    "/programs/",
    "/contact-us/",
    "/privacy-policy/",
    "/how-to-search-for-resources/",
]

# Guided-search category slugs as observed on the 211info homepage.
# These map to the iCarol-powered search widget at gethelp.211info.org.
SERVICE_CATEGORIES = [
    "crisis-hotlines",
    "housing-shelter",
    "utility-assistance",
    "child-care-parenting",
    "food",
    "basic-needs",
    "foster-families",
    "health-care",
    "volunteering-donating",
    "mental-behavioral-health",
    "transportation",
    "legal-public-safety",
    "employment",
    "education",
    "financial-wellness",
    "diverse-populations",
    "youth-services",
    "disaster-services",
]

# Oregon ZIP codes that give broad geographic coverage for search sweeps.
# Spanning from Portland metro to rural areas and SW Washington.
COVERAGE_ZIPS = [
    # Portland metro (OR)
    "97201", "97202", "97203", "97204", "97205", "97206", "97207",
    "97208", "97209", "97210", "97211", "97212", "97213", "97214",
    "97215", "97216", "97217", "97218", "97219", "97220", "97221",
    "97222", "97223", "97224", "97225", "97227", "97229", "97230",
    "97231", "97232", "97233", "97236",
    # Salem
    "97301", "97302", "97303", "97304", "97305", "97306",
    # Eugene/Springfield
    "97401", "97402", "97403", "97404", "97405",
    # Bend
    "97701", "97702", "97703",
    # Medford/Ashland
    "97501", "97520",
    # Corvallis / Albany
    "97330", "97321",
    # Astoria
    "97103",
    # The Dalles
    "97058",
    # Pendleton
    "97801",
    # Klamath Falls
    "97601",
    # Grants Pass
    "97526",
    # SW Washington (Vancouver area)
    "98660", "98661", "98662", "98663", "98664", "98665",
    "98671", "98682", "98683", "98684",
]

# ---------------------------------------------------------------------------
# Crawl behaviour
# ---------------------------------------------------------------------------
REQUEST_DELAY_SECONDS: float = float(os.getenv("SCRAPER_DELAY", "1.5"))
MAX_RETRIES: int = int(os.getenv("SCRAPER_MAX_RETRIES", "3"))
REQUEST_TIMEOUT: int = int(os.getenv("SCRAPER_TIMEOUT", "30"))
HEADLESS: bool = os.getenv("SCRAPER_HEADLESS", "true").lower() != "false"
CONCURRENT_PAGES: int = int(os.getenv("SCRAPER_CONCURRENCY", "2"))

# Maximum service records to fetch per (category, zip) combination.
# Set to 0 / None to fetch all pages.
MAX_RESULTS_PER_QUERY: int = int(os.getenv("SCRAPER_MAX_RESULTS", "0")) or 0

# ---------------------------------------------------------------------------
# HTTP headers shared by both static and browser scrapers
# ---------------------------------------------------------------------------
DEFAULT_HEADERS: dict[str, str] = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


class Config:
    """Central configuration object (can be instantiated for override purposes)."""

    base_url: str = BASE_URL
    gethelp_url: str = GETHELP_URL
    static_pages: list[str] = STATIC_PAGES
    service_categories: list[str] = SERVICE_CATEGORIES
    coverage_zips: list[str] = COVERAGE_ZIPS
    request_delay: float = REQUEST_DELAY_SECONDS
    max_retries: int = MAX_RETRIES
    timeout: int = REQUEST_TIMEOUT
    headless: bool = HEADLESS
    concurrent_pages: int = CONCURRENT_PAGES
    max_results_per_query: int = MAX_RESULTS_PER_QUERY
    raw_dir: Path = RAW_DIR
    processed_dir: Path = PROCESSED_DIR
    headers: dict[str, str] = DEFAULT_HEADERS

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                raise ValueError(f"Unknown config key: {key}")
        # Ensure output directories exist
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
