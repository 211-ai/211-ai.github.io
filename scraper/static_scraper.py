"""
Static scraper: fetches and parses 211info.org pages that do not require
JavaScript execution (informational pages, blog posts, program pages, etc.).

Uses requests + BeautifulSoup.
"""

from __future__ import annotations

import logging
import time
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from .config import Config
from .utils import clean_text, normalise_url, rate_limit, same_domain, with_retry

logger = logging.getLogger("scraper.static")


class StaticScraper:
    """Crawl the static (non-JS) sections of 211info.org."""

    def __init__(self, config: Config | None = None) -> None:
        self.cfg = config or Config()
        self.session = self._build_session()

    # ------------------------------------------------------------------
    # Session setup
    # ------------------------------------------------------------------

    def _build_session(self) -> requests.Session:
        session = requests.Session()
        session.headers.update(self.cfg.headers)
        # Try to use a realistic user-agent string
        try:
            from fake_useragent import UserAgent
            session.headers["User-Agent"] = UserAgent().chrome
        except Exception:
            session.headers["User-Agent"] = (
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        return session

    # ------------------------------------------------------------------
    # Low-level fetch
    # ------------------------------------------------------------------

    @with_retry(max_attempts=3)
    def _get(self, url: str) -> requests.Response:
        rate_limit(self.cfg.request_delay)
        resp = self.session.get(url, timeout=self.cfg.timeout)
        resp.raise_for_status()
        return resp

    def _soup(self, url: str) -> tuple[BeautifulSoup, str]:
        """Return (BeautifulSoup, final_url) for *url*."""
        resp = self._get(url)
        return BeautifulSoup(resp.text, "lxml"), resp.url

    # ------------------------------------------------------------------
    # Page-level extraction
    # ------------------------------------------------------------------

    def scrape_page(self, path: str) -> dict[str, Any]:
        """
        Scrape a single static page and return a structured record.

        Returns a dict with keys:
          url, title, meta_description, headings, body_text, links, raw_html
        """
        url = urljoin(self.cfg.base_url, path)
        logger.info("Scraping static page: %s", url)
        try:
            soup, final_url = self._soup(url)
        except Exception as exc:
            logger.warning("Failed to fetch %s: %s", url, exc)
            return {"url": url, "error": str(exc)}

        record: dict[str, Any] = {
            "url": final_url,
            "title": clean_text(soup.title.string) if soup.title else "",
            "meta_description": "",
            "headings": [],
            "body_text": "",
            "links": [],
            "raw_html": str(soup),
        }

        # Meta description
        meta = soup.find("meta", attrs={"name": "description"})
        if meta and meta.get("content"):
            record["meta_description"] = clean_text(meta["content"])

        # Headings
        for tag in soup.find_all(["h1", "h2", "h3", "h4"]):
            text = clean_text(tag.get_text())
            if text:
                record["headings"].append({"level": tag.name, "text": text})

        # Body text (remove nav, footer, scripts, styles)
        for remove in soup.find_all(["script", "style", "nav", "footer", "header"]):
            remove.decompose()
        main = soup.find("main") or soup.find("article") or soup.find("div", class_="entry-content")
        body_el = main or soup.body
        if body_el:
            record["body_text"] = clean_text(body_el.get_text(separator=" "))

        # Internal links
        for anchor in soup.find_all("a", href=True):
            norm = normalise_url(anchor["href"], self.cfg.base_url)
            if norm and same_domain(norm, self.cfg.base_url):
                record["links"].append(
                    {
                        "href": norm,
                        "text": clean_text(anchor.get_text()),
                    }
                )

        return record

    # ------------------------------------------------------------------
    # Sitemap discovery
    # ------------------------------------------------------------------

    def fetch_sitemap_urls(self) -> list[str]:
        """
        Attempt to parse /sitemap.xml (and any sitemap-index children).
        Returns a flat list of page URLs.
        """
        sitemap_url = urljoin(self.cfg.base_url, "/sitemap.xml")
        logger.info("Fetching sitemap: %s", sitemap_url)
        urls: list[str] = []
        try:
            resp = self._get(sitemap_url)
            soup = BeautifulSoup(resp.text, "lxml-xml")
            # Sitemap index
            for loc in soup.find_all("sitemap"):
                child_url = clean_text(loc.find("loc").get_text()) if loc.find("loc") else ""
                if child_url:
                    urls.extend(self._parse_sitemap(child_url))
            # Regular urlset
            for loc in soup.find_all("url"):
                href = clean_text(loc.find("loc").get_text()) if loc.find("loc") else ""
                if href:
                    urls.append(href)
        except Exception as exc:
            logger.warning("Could not parse sitemap: %s", exc)
        return urls

    def _parse_sitemap(self, sitemap_url: str) -> list[str]:
        urls: list[str] = []
        try:
            resp = self._get(sitemap_url)
            soup = BeautifulSoup(resp.text, "lxml-xml")
            for loc in soup.find_all("url"):
                href = clean_text(loc.find("loc").get_text()) if loc.find("loc") else ""
                if href:
                    urls.append(href)
        except Exception as exc:
            logger.warning("Could not parse child sitemap %s: %s", sitemap_url, exc)
        return urls

    # ------------------------------------------------------------------
    # robots.txt
    # ------------------------------------------------------------------

    def fetch_robots(self) -> str:
        """Return the raw text of robots.txt (empty string on failure)."""
        url = urljoin(self.cfg.base_url, "/robots.txt")
        try:
            resp = self._get(url)
            return resp.text
        except Exception as exc:
            logger.warning("Could not fetch robots.txt: %s", exc)
            return ""

    # ------------------------------------------------------------------
    # Crawl all configured static pages
    # ------------------------------------------------------------------

    def crawl_static_pages(self) -> list[dict[str, Any]]:
        """
        Scrape every URL in Config.static_pages and return a list of records.
        """
        results = []
        for path in self.cfg.static_pages:
            record = self.scrape_page(path)
            results.append(record)
        logger.info("Static crawl complete. Pages scraped: %d", len(results))
        return results

    # ------------------------------------------------------------------
    # Discover additional pages via BFS link following
    # ------------------------------------------------------------------

    def crawl_site(self, max_pages: int = 200) -> list[dict[str, Any]]:
        """
        Breadth-first crawl starting from the home page.

        Limits crawl to pages within the same domain and stops at *max_pages*.
        Returns a list of scraped page records.
        """
        seen: set[str] = set()
        queue: list[str] = [self.cfg.base_url + "/"]
        results: list[dict[str, Any]] = []

        while queue and len(results) < max_pages:
            url = queue.pop(0)
            if url in seen:
                continue
            seen.add(url)

            record = self.scrape_page(url.replace(self.cfg.base_url, ""))
            results.append(record)

            for link in record.get("links", []):
                href = link.get("href", "")
                if href and href not in seen and same_domain(href, self.cfg.base_url):
                    queue.append(href)

        logger.info("BFS crawl complete. Pages scraped: %d", len(results))
        return results

    # ------------------------------------------------------------------
    # Fetch and parse the search-help PDF guide
    # ------------------------------------------------------------------

    def fetch_search_guide(self) -> dict[str, Any]:
        """Download the 211info search-guide PDF URL for reference."""
        pdf_url = urljoin(
            self.cfg.base_url,
            "/wp-content/uploads/How-to-Use-the-211-Search-Tool-1.pdf",
        )
        return {"url": pdf_url, "type": "pdf_guide"}
