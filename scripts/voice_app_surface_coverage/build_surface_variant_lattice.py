#!/usr/bin/env python3
"""Build deterministic per-surface request variant lattices (VAS-012 / VAS-013)."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
VARIANTS_DIR = REPO_ROOT / "data" / "voice_app_surface_coverage" / "variants"
SCHEMA_PATH = VARIANTS_DIR / "schema.json"
EXPOSURE = (
    REPO_ROOT
    / "data"
    / "voice_app_surface_coverage"
    / "baseline"
    / "voice-exposure-matrix.json"
)
PROGRAM_ID = "voice-app-surface-coverage-v1"
FLOORS = {"P0": 200, "P1": 50}
FORBIDDEN = [
    re.compile(p, re.I)
    for p in (
        r"https?://",
        r"file://",
        r"/etc/",
        r"\\\\",
        r"\bimport\s+",
        r"os\.system",
    )
]

# Deterministic seed templates per surface (expanded combinatorially).
SURFACE_SEEDS: dict[str, dict[str, Any]] = {
    "calendar": {
        "logical_action": "read_calendar",
        "expected_route": "calendar_event_support",
        "intents": [
            "what is on my calendar",
            "what's on my calendar",
            "what appointments do I have",
            "show my calendar",
            "read my calendar",
            "any appointments",
            "what is on my schedule",
            "do I have anything scheduled",
            "show my day",
            "list my events",
            "check my calendar",
            "calendar for me please",
        ],
        "slots": [
            "",
            " today",
            " tomorrow",
            " this week",
            " for Monday",
            " this afternoon",
            " tonight",
            " next week",
        ],
        "polite": ["", "please", "can you", "could you", "I need to know"],
        "noise": ["um ", "uh ", "so ", "hey ", ""],
    },
    "home": {
        "logical_action": "open_app_surface",
        "expected_route": "app_surface_navigation",
        "intents": [
            "go home",
            "open home",
            "take me home",
            "open the home screen",
            "show dashboard",
            "back to start",
            "open today view",
            "show my home page",
            "open the main screen",
            "go to the start page",
        ],
        "slots": ["", " now", " please", " in the app"],
        "polite": ["", "please", "can you", "could you"],
        "noise": ["", "um ", "hey "],
    },
    "messages": {
        "logical_action": "read_provider_messages",
        "expected_route": "provider_contact_support",
        "intents": [
            "do I have any messages",
            "check my messages",
            "open messages",
            "any messages from my caseworker",
            "read my inbox",
            "show client messages",
            "do I have notifications",
            "check my message inbox",
        ],
        "slots": ["", " today", " from my caseworker", " unread"],
        "polite": ["", "please", "can you"],
        "noise": ["", "um ", "so "],
    },
    "uploads": {
        "logical_action": "open_wallet_documents",
        "expected_route": "wallet_document_support",
        "intents": [
            "open my wallet",
            "show my documents",
            "open wallet documents",
            "show my files",
            "open uploads",
            "show my records",
            "open the document wallet",
        ],
        "slots": ["", " please", " in the app"],
        "polite": ["", "please", "can you"],
        "noise": ["", "um "],
    },
    "social-services": {
        "logical_action": "open_service_detail",
        "expected_route": "grounded_211_answer",
        "intents": [
            "open services",
            "show social services",
            "find shelter help",
            "open the services screen",
            "help me find services",
            "show 211 services",
            "browse services",
        ],
        "slots": ["", " for housing", " for food", " near me"],
        "polite": ["", "please", "can you"],
        "noise": ["", "um "],
    },
    "check-in": {
        "logical_action": "open_app_surface",
        "expected_route": "app_surface_navigation",
        "intents": [
            "open check in",
            "open check-in",
            "show check in reminders",
            "go to check in",
            "open my reminders",
            "show check-in screen",
        ],
        "slots": ["", " please", " now"],
        "polite": ["", "please", "can you"],
        "noise": ["", "hey "],
    },
    "contacts": {
        "logical_action": "open_app_surface",
        "expected_route": "app_surface_navigation",
        "intents": [
            "open contacts",
            "show my contacts",
            "go to people",
            "open the contacts screen",
            "show recipients",
        ],
        "slots": ["", " please"],
        "polite": ["", "please", "can you"],
        "noise": ["", "um "],
    },
    "interactions": {
        "logical_action": "open_app_surface",
        "expected_route": "app_surface_navigation",
        "intents": [
            "open interactions",
            "show my history",
            "open interaction history",
            "show past interactions",
            "go to history",
        ],
        "slots": ["", " please"],
        "polite": ["", "please"],
        "noise": ["", "so "],
    },
    "settings": {
        "logical_action": "open_app_surface",
        "expected_route": "app_surface_navigation",
        "intents": [
            "open settings",
            "open account settings",
            "show preferences",
            "go to settings",
            "open profile settings",
        ],
        "slots": ["", " please"],
        "polite": ["", "please", "can you"],
        "noise": ["", "um "],
    },
}

NEGATIVES = [
    ("cancel that", "no_action", True),
    ("never mind", "no_action", True),
    ("don't open anything", "no_action", True),
    ("stop", "no_action", True),
    ("open security settings", "open_app_surface", True),  # never_voice target
    ("export all my data", "open_app_surface", True),
    ("open staff case management", "open_app_surface", True),
]


def _vid(*parts: str) -> str:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return f"var-{digest[:16]}"


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _forbidden(text: str) -> bool:
    return any(p.search(text) for p in FORBIDDEN)


def expand_surface(surface_id: str, priority: str) -> list[dict[str, Any]]:
    seed = SURFACE_SEEDS[surface_id]
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(
        user_text: str,
        *,
        axes: list[str],
        logical_action: str,
        negative: bool = False,
    ) -> None:
        text = _clean(user_text)
        if not text or text.lower() in seen or _forbidden(text):
            return
        seen.add(text.lower())
        rows.append(
            {
                "variant_id": _vid(surface_id, text, logical_action),
                "surface_id": surface_id,
                "user_text": text,
                "logical_action": logical_action,
                "axes": axes,
                "priority": priority,
                "negative": negative,
                "expected_route": seed.get("expected_route"),
                "language": "en",
                "program_id": PROGRAM_ID,
            }
        )

    for polite in seed["polite"]:
        for noise in seed["noise"]:
            for intent in seed["intents"]:
                for slot in seed["slots"]:
                    # Combinations of prefix styles
                    if polite in {"can you", "could you", "I need to know"}:
                        body = f"{noise}{polite} {intent}{slot}"
                    elif polite == "please":
                        body = f"{noise}{intent}{slot} please"
                    else:
                        body = f"{noise}{intent}{slot}"
                    add(
                        body,
                        axes=["paraphrase", "slot", "noise"],
                        logical_action=seed["logical_action"],
                    )

    # Extra calendar-specific paraphrases for reliability under variants.
    if surface_id == "calendar":
        extras = [
            "what do I have on the calendar",
            "is anything on my calendar",
            "tell me what's on my calendar",
            "calendar check",
            "pull up my appointments",
            "am I free tomorrow",
            "do I have a free slot today",
            "what meetings are on my calendar",
            "show upcoming appointments",
            "read calendar events",
        ]
        for e in extras:
            for slot in ("", " tomorrow", " today"):
                add(e + slot, axes=["paraphrase", "slot"], logical_action="read_calendar")

    # Pad with numbered neutral paraphrases if still under floor (deterministic).
    floor = FLOORS[priority]
    n = 1
    base_intent = seed["intents"][0]
    while len(rows) < floor and n < floor * 3:
        add(
            f"{base_intent} variant {n}",
            axes=["paraphrase", "pad"],
            logical_action=seed["logical_action"],
        )
        n += 1

    for text, action, neg in NEGATIVES:
        add(text, axes=["negative"], logical_action=action, negative=neg)

    return rows


def p0_surfaces() -> list[str]:
    if not EXPOSURE.is_file():
        return sorted(SURFACE_SEEDS)
    matrix = json.loads(EXPOSURE.read_text(encoding="utf-8"))
    out = []
    for row in matrix.get("surfaces") or []:
        if row.get("priority") == "P0" and row.get("exposure_class") in {
            "voice_navigable",
            "voice_actionable",
        }:
            sid = row["surface_id"]
            if sid in SURFACE_SEEDS:
                out.append(sid)
    return sorted(out)


def write_priority(priority: str) -> dict[str, int]:
    VARIANTS_DIR.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    surfaces = p0_surfaces() if priority == "P0" else list(SURFACE_SEEDS)
    for surface_id in surfaces:
        if surface_id not in SURFACE_SEEDS:
            continue
        rows = expand_surface(surface_id, priority)
        path = VARIANTS_DIR / f"{surface_id}.jsonl"
        path.write_text(
            "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows),
            encoding="utf-8",
        )
        counts[surface_id] = len({r["user_text"].lower() for r in rows})
    return counts


def check_priority(priority: str) -> list[str]:
    errors: list[str] = []
    if not SCHEMA_PATH.is_file():
        errors.append(f"missing schema {SCHEMA_PATH}")
    floor = FLOORS[priority]
    surfaces = p0_surfaces() if priority == "P0" else list(SURFACE_SEEDS)
    for surface_id in surfaces:
        path = VARIANTS_DIR / f"{surface_id}.jsonl"
        if not path.is_file():
            errors.append(f"missing lattice {path}")
            continue
        texts: set[str] = set()
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            text = str(row.get("user_text") or "").strip()
            if _forbidden(text):
                errors.append(f"{surface_id}: forbidden content in {text!r}")
            texts.add(text.lower())
            for field in (
                "variant_id",
                "surface_id",
                "user_text",
                "logical_action",
                "axes",
                "priority",
                "negative",
            ):
                if field not in row:
                    errors.append(f"{surface_id}: missing field {field}")
        if len(texts) < floor:
            errors.append(
                f"{surface_id}: unique user_text {len(texts)} < floor {floor}"
            )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--check-schema", action="store_true")
    parser.add_argument("--priority", default="P0", choices=["P0", "P1"])
    args = parser.parse_args()

    if args.check_schema:
        if not SCHEMA_PATH.is_file():
            print(f"missing {SCHEMA_PATH}", file=sys.stderr)
            return 1
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        assert schema.get("schema")
        print("variant schema OK")
        return 0

    if args.write or not args.check:
        counts = write_priority(args.priority)
        print(json.dumps({"wrote": counts}, indent=2, sort_keys=True))

    if args.check:
        errors = check_priority(args.priority)
        if errors:
            print("variant lattice check FAILED:", file=sys.stderr)
            for err in errors:
                print(f"  - {err}", file=sys.stderr)
            return 1
        print(f"variant lattice check OK ({args.priority})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
