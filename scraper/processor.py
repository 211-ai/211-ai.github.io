"""
Post-processing pipeline: deduplicate, normalise, and export scraped records.

Run after BrowserScraper / StaticScraper have saved raw data.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Any

from .config import Config
from .storage import Storage
from .utils import clean_text, extract_phone, extract_zip

logger = logging.getLogger("scraper.processor")

# Fields retained in the final, normalised output
CANONICAL_FIELDS = [
    "id",
    "name",
    "provider_name",
    "program_name",
    "description",
    "address",
    "city",
    "state",
    "zip",
    "phone",
    "email",
    "website",
    "hours",
    "eligibility",
    "languages",
    "categories",
    "accessibility",
    "source_url",
    "search_category",
    "search_zip",
]


class DataProcessor:
    """
    Clean, deduplicate, and export raw scraped records.

    Usage::

        processor = DataProcessor()
        clean = processor.process(raw_records)
        processor.export(clean, "services")
    """

    def __init__(self, config: Config | None = None) -> None:
        self.cfg = config or Config()
        self.storage = Storage(self.cfg.raw_dir, self.cfg.processed_dir)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Normalise and deduplicate *records*.

        Returns a list of clean, canonical service records.
        """
        normalised = [self._normalise(r) for r in records]
        deduped = self._deduplicate(normalised)
        logger.info(
            "Processed %d raw → %d normalised → %d unique records",
            len(records),
            len(normalised),
            len(deduped),
        )
        return deduped

    def process_from_files(
        self,
        raw_filename: str = "services_raw.jsonl",
    ) -> list[dict[str, Any]]:
        """Load raw JSONL, process, and return clean records."""
        raw = self.storage.load_jsonl(raw_filename)
        return self.process(raw)

    def export(self, records: list[dict[str, Any]], basename: str = "services") -> None:
        """Save processed records as both JSONL and CSV."""
        self.storage.append_jsonl(records, f"{basename}.jsonl", processed=True)
        self.storage.save_csv(records, f"{basename}.csv", fieldnames=CANONICAL_FIELDS)
        logger.info("Exported %d records to %s.[jsonl|csv]", len(records), basename)

    # ------------------------------------------------------------------
    # Normalisation
    # ------------------------------------------------------------------

    def _normalise(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Map a raw scraper record to the canonical schema."""
        name = clean_text(raw.get("name", ""))
        description = clean_text(raw.get("description", ""))
        address_raw = clean_text(raw.get("address", ""))

        # Try to split city/state/zip from address
        city, state, zipcode = self._parse_address(address_raw)

        # Phone – prefer scraped value, fall back to text-extraction
        phone = clean_text(raw.get("phone", ""))
        if not phone:
            phone = extract_phone(address_raw) or extract_phone(description) or ""

        # Email – handle mailto: links
        email = clean_text(raw.get("email", ""))
        if email.startswith("mailto:"):
            email = email[7:]

        # Website
        website = clean_text(raw.get("website", ""))

        # Categories (may be a list or a comma-separated string)
        categories = raw.get("categories", "")
        if isinstance(categories, list):
            categories = ", ".join(clean_text(c) for c in categories)
        else:
            categories = clean_text(str(categories))

        source_url = raw.get("detail_url", "") or raw.get("url", "")
        record_id = self._stable_id(name, address_raw, source_url)

        return {
            "id": record_id,
            "name": name,
            "provider_name": clean_text(raw.get("provider_name", "")) or name,
            "program_name": clean_text(raw.get("program_name", "")),
            "description": description,
            "address": address_raw,
            "city": city,
            "state": state,
            "zip": zipcode or extract_zip(address_raw) or "",
            "phone": phone,
            "email": email,
            "website": website,
            "hours": clean_text(raw.get("hours", "")),
            "eligibility": clean_text(raw.get("eligibility", "")),
            "languages": clean_text(raw.get("languages", "")),
            "categories": categories or clean_text(raw.get("category", "")),
            "accessibility": clean_text(raw.get("accessibility", "")),
            "source_url": source_url,
            "search_category": raw.get("category", "") or raw.get("search_category", ""),
            "search_zip": raw.get("search_zip", ""),
        }

    # ------------------------------------------------------------------
    # Address parsing
    # ------------------------------------------------------------------

    _ADDR_RE = re.compile(
        r"^(?P<street>.+?),?\s+"
        r"(?P<city>[A-Za-z\s]+),\s*"
        r"(?P<state>[A-Z]{2})\s+"
        r"(?P<zip>\d{5}(?:-\d{4})?)\s*$"
    )

    @staticmethod
    def _parse_address(address: str) -> tuple[str, str, str]:
        """Return (city, state, zip) parsed from *address*, or empty strings."""
        m = DataProcessor._ADDR_RE.search(address)
        if m:
            return m.group("city").strip(), m.group("state"), m.group("zip")
        # Fallback: try ZIP extraction only
        zipcode = extract_zip(address) or ""
        return "", "", zipcode

    # ------------------------------------------------------------------
    # Deduplication
    # ------------------------------------------------------------------

    def _deduplicate(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Remove duplicate records, merging categories when name+address match."""
        by_id: dict[str, dict[str, Any]] = {}
        for rec in records:
            rid = rec["id"]
            if rid not in by_id:
                by_id[rid] = rec
            else:
                # Merge categories
                existing = by_id[rid]
                cats = {
                    c.strip()
                    for c in [existing.get("categories", ""), rec.get("categories", "")]
                    if c and c.strip()
                }
                existing["categories"] = ", ".join(sorted(cats))
                # Fill in missing fields from the duplicate
                for key, val in rec.items():
                    if not existing.get(key) and val:
                        existing[key] = val
        return list(by_id.values())

    # ------------------------------------------------------------------
    # Stable ID generation
    # ------------------------------------------------------------------

    @staticmethod
    def _stable_id(*parts: str) -> str:
        """Generate a short, stable SHA-256-based ID from the given parts."""
        combined = "|".join(p.lower().strip() for p in parts if p)
        return hashlib.sha256(combined.encode()).hexdigest()[:16]

    # ------------------------------------------------------------------
    # Processing static page content
    # ------------------------------------------------------------------

    def process_static_pages(
        self, pages: list[dict[str, Any]], basename: str = "static_pages"
    ) -> None:
        """Save scraped static pages (stripping large raw_html field)."""
        stripped = []
        for page in pages:
            clean = {k: v for k, v in page.items() if k != "raw_html"}
            stripped.append(clean)
        self.storage.save_json(stripped, f"{basename}.json", processed=True)
        logger.info("Saved %d static pages to %s.json", len(stripped), basename)
