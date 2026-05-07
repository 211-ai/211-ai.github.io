"""
Storage helpers: save/load JSON, JSONL, and CSV files.
"""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from typing import Any, Iterable

logger = logging.getLogger("scraper.storage")


class Storage:
    """Handles reading and writing scraped data to disk."""

    def __init__(self, raw_dir: Path, processed_dir: Path) -> None:
        self.raw_dir = raw_dir
        self.processed_dir = processed_dir
        raw_dir.mkdir(parents=True, exist_ok=True)
        processed_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # JSON (single document)
    # ------------------------------------------------------------------

    def save_json(self, data: Any, filename: str, *, processed: bool = False) -> Path:
        """Serialise *data* to a JSON file and return its path."""
        directory = self.processed_dir if processed else self.raw_dir
        path = directory / filename
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info("Saved JSON → %s", path)
        return path

    def load_json(self, filename: str, *, processed: bool = False) -> Any:
        """Load and return data from a JSON file."""
        directory = self.processed_dir if processed else self.raw_dir
        path = directory / filename
        return json.loads(path.read_text(encoding="utf-8"))

    # ------------------------------------------------------------------
    # JSONL (newline-delimited JSON, ideal for large record sets)
    # ------------------------------------------------------------------

    def append_jsonl(self, records: Iterable[dict], filename: str, *, processed: bool = False) -> Path:
        """Append records to a JSONL file (one JSON object per line)."""
        directory = self.processed_dir if processed else self.raw_dir
        path = directory / filename
        with path.open("a", encoding="utf-8") as fh:
            for record in records:
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        logger.debug("Appended records to JSONL → %s", path)
        return path

    def load_jsonl(self, filename: str, *, processed: bool = False) -> list[dict]:
        """Load all records from a JSONL file."""
        directory = self.processed_dir if processed else self.raw_dir
        path = directory / filename
        if not path.exists():
            return []
        records = []
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records

    # ------------------------------------------------------------------
    # CSV
    # ------------------------------------------------------------------

    def save_csv(
        self,
        records: list[dict],
        filename: str,
        fieldnames: list[str] | None = None,
        *,
        processed: bool = True,
    ) -> Path:
        """Write *records* to a CSV file and return its path."""
        if not records:
            logger.warning("No records to write; skipping %s", filename)
            return self.processed_dir / filename
        directory = self.processed_dir if processed else self.raw_dir
        path = directory / filename
        if fieldnames is None:
            # Use the union of all keys, preserving insertion order
            seen: dict[str, None] = {}
            for r in records:
                seen.update({k: None for k in r})
            fieldnames = list(seen)
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(records)
        logger.info("Saved CSV → %s (%d rows)", path, len(records))
        return path

    # ------------------------------------------------------------------
    # Raw HTML
    # ------------------------------------------------------------------

    def save_html(self, html: str, filename: str) -> Path:
        """Save raw HTML to the raw directory."""
        path = self.raw_dir / filename
        path.write_text(html, encoding="utf-8")
        logger.debug("Saved HTML → %s", path)
        return path

    # ------------------------------------------------------------------
    # Deduplication helpers
    # ------------------------------------------------------------------

    def load_seen_ids(self, filename: str = "seen_ids.json") -> set[str]:
        """Load the set of already-scraped resource IDs."""
        path = self.raw_dir / filename
        if not path.exists():
            return set()
        return set(json.loads(path.read_text(encoding="utf-8")))

    def save_seen_ids(self, ids: set[str], filename: str = "seen_ids.json") -> None:
        """Persist the set of scraped resource IDs."""
        path = self.raw_dir / filename
        path.write_text(json.dumps(sorted(ids), indent=2), encoding="utf-8")
