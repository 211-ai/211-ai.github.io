"""
Browser-based scraper for the dynamic service-search pages on 211info.org.

Uses Microsoft Playwright (async API) to drive a headless Chromium browser,
perform guided-category searches across many ZIP codes, and extract full
service-record details.

Architecture
------------
  BrowserScraper.run_full_scrape()
      └─ for each category × zip
             └─ search_category_zip()         → list of stub records
                  └─ get_service_detail()      → enriched record
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from typing import Any
from urllib.parse import urljoin

from .config import Config
from .utils import clean_text, rate_limit

logger = logging.getLogger("scraper.browser")

# ---------------------------------------------------------------------------
# CSS / XPath selectors (tweak if the site is re-skinned)
# ---------------------------------------------------------------------------

# gethelp.211info.org search widget selectors
SEARCH_INPUT = 'input[placeholder*="search" i], input[type="search"], input[name="q"]'
LOCATION_INPUT = (
    'input[placeholder*="location" i], input[placeholder*="zip" i], '
    'input[name="location"], input[name="zip"]'
)
SEARCH_BUTTON = 'button[type="submit"], input[type="submit"], button:has-text("Search")'
RESULT_CARD = (
    '.result-card, .resource-card, .service-card, '
    'li.result, div.result, article.resource, '
    '[class*="result"], [class*="resource"]'
)
NEXT_PAGE = (
    'a[aria-label="Next page"], button[aria-label="Next"], '
    'a:has-text("Next"), .pagination .next'
)

# Detail page fields
DETAIL_SELECTORS = {
    "name": "h1, .resource-name, .agency-name",
    "description": ".description, .resource-description, [class*='description']",
    "address": ".address, [class*='address'], [itemprop='address']",
    "phone": ".phone, [class*='phone'], [itemprop='telephone']",
    "website": "a[class*='website'], a[href^='http']:not([href*='211info'])",
    "hours": ".hours, [class*='hours'], [class*='schedule']",
    "eligibility": ".eligibility, [class*='eligibility'], [class*='who-can']",
    "languages": ".languages, [class*='language']",
    "email": "a[href^='mailto:']",
    "categories": ".categories, [class*='categor'], .taxonomy",
    "accessibility": ".accessibility, [class*='accessib']",
}


class BrowserScraper:
    """
    Async Playwright-based scraper for 211info's JavaScript-rendered search pages.

    Usage (async context)::

        async with BrowserScraper() as scraper:
            records = await scraper.run_full_scrape()

    Or via the sync helper::

        records = BrowserScraper.run_sync()
    """

    def __init__(self, config: Config | None = None) -> None:
        self.cfg = config or Config()
        self._browser = None
        self._playwright = None

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    async def __aenter__(self) -> "BrowserScraper":
        from playwright.async_api import async_playwright

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.cfg.headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        logger.info("Playwright browser launched (headless=%s)", self.cfg.headless)
        return self

    async def __aexit__(self, *_) -> None:
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info("Playwright browser closed")

    # ------------------------------------------------------------------
    # New page helper
    # ------------------------------------------------------------------

    async def _new_page(self):
        """Return a new browser page with stealth headers."""
        page = await self._browser.new_page()
        await page.set_extra_http_headers(self.cfg.headers)
        await page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        return page

    # ------------------------------------------------------------------
    # Navigation helpers
    # ------------------------------------------------------------------

    async def _goto(self, page, url: str, wait: str = "networkidle") -> bool:
        """Navigate to *url*, returning False on failure."""
        try:
            await page.goto(url, wait_until=wait, timeout=self.cfg.timeout * 1000)
            return True
        except Exception as exc:
            logger.warning("Navigation failed for %s: %s", url, exc)
            return False

    # ------------------------------------------------------------------
    # Home page discovery
    # ------------------------------------------------------------------

    async def scrape_homepage(self) -> dict[str, Any]:
        """
        Capture the main homepage markup and discover the guided-search
        category links and any embedded widget iframe sources.
        """
        page = await self._new_page()
        try:
            await self._goto(page, self.cfg.base_url)
            html = await page.content()
            title = await page.title()

            # Discover category links / buttons visible on the home page
            categories: list[dict] = []
            for el in await page.query_selector_all("a, button"):
                text = clean_text(await el.text_content() or "")
                href = await el.get_attribute("href") or ""
                if text and len(text) > 2:
                    categories.append({"text": text, "href": href})

            # Discover iframes (the gethelp widget may be embedded)
            iframes = []
            for frame in await page.query_selector_all("iframe"):
                src = await frame.get_attribute("src") or ""
                iframes.append(src)

            return {
                "url": self.cfg.base_url,
                "title": title,
                "categories_found": categories,
                "iframes": iframes,
                "raw_html": html,
            }
        finally:
            await page.close()

    # ------------------------------------------------------------------
    # gethelp.211info.org search
    # ------------------------------------------------------------------

    async def _accept_cookies(self, page) -> None:
        """Dismiss cookie consent dialogs if present."""
        for selector in ["button:has-text('Accept')", "button:has-text('OK')", "#cookie-accept"]:
            try:
                btn = await page.query_selector(selector)
                if btn:
                    await btn.click()
                    await page.wait_for_timeout(500)
            except Exception:
                pass

    async def search_category_zip(
        self,
        category: str,
        zip_code: str,
        max_results: int = 0,
    ) -> list[dict[str, Any]]:
        """
        Navigate the gethelp search widget for *category* + *zip_code*,
        paginate through results, and return a list of stub records.
        """
        page = await self._new_page()
        records: list[dict[str, Any]] = []
        try:
            # Build candidate URLs to try
            candidate_urls = [
                f"{self.cfg.gethelp_url}/?q={category}&location={zip_code}",
                f"{self.cfg.gethelp_url}/search?query={category}&location={zip_code}",
                f"{self.cfg.base_url}/?s={category}&location={zip_code}",
                self.cfg.gethelp_url,
            ]

            loaded = False
            for url in candidate_urls:
                if await self._goto(page, url):
                    await self._accept_cookies(page)
                    loaded = True
                    break

            if not loaded:
                logger.warning("Could not load search page for %s / %s", category, zip_code)
                return records

            # If we landed on a bare search page, fill in the form fields
            await self._fill_search_form(page, category, zip_code)

            # Paginate and collect results
            page_num = 0
            while True:
                page_num += 1
                logger.debug(
                    "Collecting page %d results for [%s / %s]", page_num, category, zip_code
                )
                page_records = await self._extract_result_cards(page, category, zip_code)
                records.extend(page_records)

                if max_results and len(records) >= max_results:
                    records = records[:max_results]
                    break

                # Try to advance to next page
                next_btn = await page.query_selector(NEXT_PAGE)
                if not next_btn:
                    break
                try:
                    await next_btn.click()
                    await page.wait_for_timeout(int(self.cfg.request_delay * 1000))
                except Exception:
                    break

        except Exception as exc:
            logger.error("Error scraping [%s / %s]: %s", category, zip_code, exc)
        finally:
            await page.close()

        return records

    async def _fill_search_form(self, page, category: str, zip_code: str) -> None:
        """Attempt to fill in the search form fields if they exist."""
        try:
            loc_el = await page.query_selector(LOCATION_INPUT)
            if loc_el:
                await loc_el.fill(zip_code)
                await page.wait_for_timeout(300)

            search_el = await page.query_selector(SEARCH_INPUT)
            if search_el:
                await search_el.fill(category.replace("-", " "))

            btn = await page.query_selector(SEARCH_BUTTON)
            if btn:
                await btn.click()
                await page.wait_for_load_state("networkidle", timeout=20000)
        except Exception as exc:
            logger.debug("Form fill partial failure: %s", exc)

    async def _extract_result_cards(
        self, page, category: str, zip_code: str
    ) -> list[dict[str, Any]]:
        """Extract service stub records from the current results page."""
        records: list[dict[str, Any]] = []
        cards = await page.query_selector_all(RESULT_CARD)

        for card in cards:
            try:
                name = clean_text(await card.text_content() or "")
                href = ""
                link_el = await card.query_selector("a")
                if link_el:
                    href = await link_el.get_attribute("href") or ""
                    name = clean_text(await link_el.text_content() or name)

                if not name:
                    continue

                record: dict[str, Any] = {
                    "name": name,
                    "detail_url": urljoin(self.cfg.gethelp_url, href) if href else "",
                    "category": category,
                    "search_zip": zip_code,
                }
                records.append(record)
            except Exception:
                pass

        # Fallback: if no cards found, try to extract any links that look like resources
        if not records:
            records = await self._extract_links_fallback(page, category, zip_code)

        return records

    async def _extract_links_fallback(
        self, page, category: str, zip_code: str
    ) -> list[dict[str, Any]]:
        """Fallback: harvest any anchors from the page that look like resource links."""
        records = []
        html = await page.content()
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            text = clean_text(a.get_text())
            if text and len(text) > 5 and (
                "resource" in href.lower()
                or "service" in href.lower()
                or "program" in href.lower()
            ):
                records.append(
                    {
                        "name": text,
                        "detail_url": urljoin(self.cfg.gethelp_url, href),
                        "category": category,
                        "search_zip": zip_code,
                    }
                )
        return records

    # ------------------------------------------------------------------
    # Detail page extraction
    # ------------------------------------------------------------------

    async def get_service_detail(self, stub: dict[str, Any]) -> dict[str, Any]:
        """
        Visit the detail URL in *stub* and return an enriched record.
        Falls back gracefully if the detail page is not available.
        """
        url = stub.get("detail_url", "")
        if not url:
            return stub

        page = await self._new_page()
        try:
            if not await self._goto(page, url):
                return stub

            await self._accept_cookies(page)
            html = await page.content()
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html, "lxml")

            enriched = dict(stub)
            enriched["raw_html_detail"] = html

            for field, selector in DETAIL_SELECTORS.items():
                try:
                    el = soup.select_one(selector)
                    enriched[field] = clean_text(el.get_text()) if el else stub.get(field, "")
                except Exception:
                    enriched[field] = stub.get(field, "")

            # Extract structured data (JSON-LD / microdata)
            for script in soup.find_all("script", type="application/ld+json"):
                try:
                    ld = json.loads(script.string or "")
                    enriched["json_ld"] = ld
                    break
                except Exception:
                    pass

            return enriched
        finally:
            await page.close()

    # ------------------------------------------------------------------
    # Full scrape orchestration
    # ------------------------------------------------------------------

    async def run_full_scrape(
        self,
        categories: list[str] | None = None,
        zips: list[str] | None = None,
        enrich_details: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Run the complete scrape across all configured categories × ZIP codes.

        Parameters
        ----------
        categories : list[str] | None
            Override the categories to search. Defaults to Config.service_categories.
        zips : list[str] | None
            Override the ZIP codes to use. Defaults to Config.coverage_zips.
        enrich_details : bool
            If True, visit each detail page for richer data.

        Returns a deduplicated list of service records.
        """
        cats = categories or self.cfg.service_categories
        zipcodes = zips or self.cfg.coverage_zips

        all_stubs: list[dict[str, Any]] = []
        seen_urls: set[str] = set()

        # Phase 1: collect stubs
        for cat in cats:
            for zip_code in zipcodes:
                logger.info("Searching [%s] in %s", cat, zip_code)
                stubs = await self.search_category_zip(
                    cat,
                    zip_code,
                    max_results=self.cfg.max_results_per_query,
                )
                for stub in stubs:
                    url = stub.get("detail_url", "")
                    key = url or stub.get("name", "")
                    if key and key not in seen_urls:
                        seen_urls.add(key)
                        all_stubs.append(stub)

                await asyncio.sleep(self.cfg.request_delay)

        logger.info("Phase 1 complete. Unique stubs: %d", len(all_stubs))

        if not enrich_details:
            return all_stubs

        # Phase 2: enrich with detail pages (bounded concurrency)
        sem = asyncio.Semaphore(self.cfg.concurrent_pages)
        results: list[dict[str, Any]] = []

        async def _enrich(stub: dict[str, Any]) -> dict[str, Any]:
            async with sem:
                await asyncio.sleep(self.cfg.request_delay)
                return await self.get_service_detail(stub)

        tasks = [asyncio.create_task(_enrich(s)) for s in all_stubs]
        for idx, coro in enumerate(asyncio.as_completed(tasks)):
            record = await coro
            results.append(record)
            if (idx + 1) % 50 == 0:
                logger.info("Enriched %d / %d records", idx + 1, len(all_stubs))

        logger.info("Phase 2 complete. Enriched records: %d", len(results))
        return results

    # ------------------------------------------------------------------
    # Sync convenience wrapper
    # ------------------------------------------------------------------

    @classmethod
    def run_sync(
        cls,
        config: Config | None = None,
        categories: list[str] | None = None,
        zips: list[str] | None = None,
        enrich_details: bool = True,
    ) -> list[dict[str, Any]]:
        """Synchronous entry point; runs the async scrape in a new event loop."""

        async def _run():
            async with cls(config) as scraper:
                return await scraper.run_full_scrape(
                    categories=categories,
                    zips=zips,
                    enrich_details=enrich_details,
                )

        return asyncio.run(_run())
