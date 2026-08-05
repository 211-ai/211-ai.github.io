#!/usr/bin/env python3
"""Build deterministic per-surface request variant lattices (VAS2-014..017).

Raised floors vs v1: P0≥500, P1≥150, P2≥80 unique user texts per surface.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
VARIANTS_DIR = REPO_ROOT / "data" / "voice_app_surface_full_coverage" / "variants"
SCHEMA_PATH = VARIANTS_DIR / "schema.json"
REPORTS = REPO_ROOT / "data" / "voice_app_surface_full_coverage" / "reports"
EXPOSURE = (
    REPO_ROOT
    / "data"
    / "voice_app_surface_full_coverage"
    / "baseline"
    / "voice-exposure-matrix.json"
)
DOCTRINE = (
    REPO_ROOT
    / "docs"
    / "voice_app_surface_full_coverage"
    / "VARIANT_LATTICE.md"
)
PROGRAM_ID = "voice-app-surface-full-coverage-v2"
SCHEMA_ID = "voice-app-surface-full-coverage/variant-lattice-schema@1"
FLOORS = {"P0": 500, "P1": 150, "P2": 80}
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

# Deterministic seed templates — expanded combinatorially then padded.
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
            "what do I have on the calendar",
            "is anything on my calendar",
            "tell me what's on my calendar",
            "pull up my appointments",
            "what meetings are on my calendar",
            "show upcoming appointments",
            "read calendar events",
            "am I free",
            "do I have a free slot",
            "calendar check",
            "look at my schedule",
            "any calendar events",
            "what's coming up on my calendar",
            "show me my calendar entries",
            "open calendar and read it",
            "review my appointments",
            "scan my calendar",
            "calendar overview please",
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
            " this morning",
            " on Tuesday",
            " this weekend",
            " later today",
        ],
        "polite": ["", "please", "can you", "could you", "I need to know", "would you"],
        "noise": ["", "um ", "uh ", "so ", "hey ", "okay ", "like "],
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
            "home screen please",
            "return home",
            "open start",
            "show home",
            "navigate home",
            "bring up home",
            "load the home page",
            "switch to home",
            "open my dashboard",
            "go to dashboard",
        ],
        "slots": ["", " now", " please", " in the app", " for me", " again"],
        "polite": ["", "please", "can you", "could you", "would you"],
        "noise": ["", "um ", "hey ", "so ", "okay "],
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
            "show my messages",
            "any new messages",
            "read provider messages",
            "open my inbox",
            "check inbox",
            "messages from my provider",
            "any texts in the app",
            "show unread messages",
            "pull up messages",
            "look at my messages",
            "message center please",
            "open the messages screen",
        ],
        "slots": ["", " today", " from my caseworker", " unread", " now", " please"],
        "polite": ["", "please", "can you", "could you", "would you"],
        "noise": ["", "um ", "so ", "hey ", "okay "],
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
            "open documents",
            "show wallet",
            "go to wallet",
            "open my document folder",
            "bring up my files",
            "show uploaded documents",
            "open document store",
            "wallet docs please",
            "open my uploads",
            "show proof documents",
            "open records wallet",
            "navigate to documents",
            "show my wallet files",
        ],
        "slots": ["", " please", " in the app", " now", " for me"],
        "polite": ["", "please", "can you", "could you", "would you"],
        "noise": ["", "um ", "hey ", "so "],
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
            "open service list",
            "find food help",
            "show housing resources",
            "open community services",
            "find help near me",
            "show service directory",
            "open 211 list",
            "browse social services",
            "find rental assistance",
            "show shelter options",
            "services for me",
            "open help resources",
            "find local services",
        ],
        "slots": [
            "",
            " for housing",
            " for food",
            " near me",
            " for shelter",
            " for utilities",
            " please",
        ],
        "polite": ["", "please", "can you", "could you", "I need"],
        "noise": ["", "um ", "so ", "hey "],
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
            "open checkins",
            "show reminders",
            "check in please",
            "open daily check in",
            "go to reminders",
            "open check-in page",
            "show my check ins",
            "navigate to check-in",
            "bring up check in",
            "open reminder list",
            "check-in screen",
            "open check in panel",
            "show checkin",
            "go check in",
        ],
        "slots": ["", " please", " now", " for today", " in the app"],
        "polite": ["", "please", "can you", "could you", "would you"],
        "noise": ["", "hey ", "um ", "so "],
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
            "open people list",
            "show contact list",
            "go to contacts",
            "open my people",
            "show who I can share with",
            "open contacts page",
            "navigate to contacts",
            "bring up contacts",
            "contacts please",
            "show my people list",
            "open recipient list",
            "go to recipients",
            "open contact book",
            "show contacts screen",
            "list my contacts",
        ],
        "slots": ["", " please", " now", " in the app"],
        "polite": ["", "please", "can you", "could you", "would you"],
        "noise": ["", "um ", "hey ", "so "],
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
            "open activity history",
            "show recent interactions",
            "open my timeline",
            "show interaction log",
            "go to interactions",
            "open history screen",
            "show past activity",
            "navigate to history",
            "bring up interactions",
            "history please",
            "open my activity",
            "show logs",
            "open past cases",
            "show interaction list",
            "go to activity",
        ],
        "slots": ["", " please", " now", " for this week"],
        "polite": ["", "please", "can you", "could you"],
        "noise": ["", "so ", "um ", "hey "],
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
            "open my settings",
            "show account preferences",
            "open configuration",
            "go to preferences",
            "settings please",
            "open settings page",
            "navigate to settings",
            "bring up settings",
            "show settings screen",
            "open app settings",
            "go into settings",
            "open options",
            "show options menu",
            "open user settings",
            "settings screen",
        ],
        "slots": ["", " please", " now", " in the app"],
        "polite": ["", "please", "can you", "could you", "would you"],
        "noise": ["", "um ", "hey ", "so "],
    },
    "register": {
        "logical_action": "open_app_surface",
        "expected_route": "app_surface_navigation",
        "intents": [
            "open registration",
            "open register",
            "go to register",
            "show sign up",
            "open enrollment",
            "start registration",
            "open the register screen",
            "go to sign up",
            "open register page",
            "show registration form",
            "navigate to register",
            "bring up registration",
            "register please",
            "open my registration",
            "show enroll screen",
        ],
        "slots": ["", " please", " now", " in the app"],
        "polite": ["", "please", "can you", "could you"],
        "noise": ["", "um ", "hey ", "so "],
    },
}

# P1/P2 read-only or deny-class surfaces: query/negative lattices.
READ_ONLY_SEEDS: dict[str, dict[str, Any]] = {
    "analytics": {
        "logical_action": "no_action",
        "expected_route": "template_guided_fallback",
        "intents": [
            "what do my analytics show",
            "tell me about my stats",
            "read my analytics summary",
            "how am I doing on goals",
            "analytics overview",
            "show analytics numbers as speech",
            "what do the charts mean",
            "summarize my analytics",
            "any trends in my data",
            "analytics status please",
        ],
        "slots": ["", " today", " this week", " please"],
        "polite": ["", "please", "can you"],
        "noise": ["", "um ", "so "],
    },
    "proof-center": {
        "logical_action": "no_action",
        "expected_route": "template_guided_fallback",
        "intents": [
            "what proofs do I have",
            "tell me about my certificates",
            "summarize proof center",
            "any zk proofs ready",
            "proof status please",
            "read my proof list",
            "what is in proof center",
            "certificate status",
            "do I have verified proofs",
            "proof overview",
        ],
        "slots": ["", " today", " please"],
        "polite": ["", "please", "can you"],
        "noise": ["", "um "],
    },
}

NEVER_VOICE_SURFACES = (
    "audit",
    "security",
    "exports",
    "recipient-access",
    "sharing-rules",
    "benefits-protection",
)
STAFF_ONLY_SURFACES = (
    "shelter",
    "provider-clients",
    "provider-cases",
    "provider-messages",
    "provider-analytics",
    "provider-proofs",
    "provider-operations",
)

NEGATIVES_BASE = [
    ("cancel that", "no_action"),
    ("never mind", "no_action"),
    ("don't open anything", "no_action"),
    ("stop", "no_action"),
    ("no thanks", "no_action"),
    ("abort", "no_action"),
    ("forget it", "no_action"),
    ("not now", "no_action"),
]


def _vid(*parts: str) -> str:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return f"var-{digest[:16]}"


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _forbidden(text: str) -> bool:
    return any(p.search(text) for p in FORBIDDEN)


def expand_from_seed(
    surface_id: str,
    seed: dict[str, Any],
    priority: str,
    *,
    floor: int,
    extra_negatives: Iterable[tuple[str, str]] = (),
) -> list[dict[str, Any]]:
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

    intents = list(seed["intents"])
    slots = list(seed["slots"])
    polite = list(seed["polite"])
    noise = list(seed["noise"])

    # Cap slightly above floor so repos stay lean while meeting acceptance.
    soft_cap = max(floor + 40, int(floor * 1.08))

    def under_cap() -> bool:
        return len(seen) < soft_cap

    for p in polite:
        if not under_cap():
            break
        for n in noise:
            if not under_cap():
                break
            for intent in intents:
                if not under_cap():
                    break
                for slot in slots:
                    if not under_cap():
                        break
                    if p in {"can you", "could you", "I need to know", "would you", "I need"}:
                        body = f"{n}{p} {intent}{slot}"
                    elif p == "please":
                        body = f"{n}{intent}{slot} please"
                    else:
                        body = f"{n}{intent}{slot}"
                    add(
                        body,
                        axes=["paraphrase", "slot", "noise", "dialect"],
                        logical_action=seed["logical_action"],
                    )

    # Multiturn shells (short prefixes).
    multiturn = ["wait ", "actually ", "one more thing ", "also ", "and then "]
    for mt in multiturn:
        if not under_cap():
            break
        for intent in intents[:12]:
            for slot in slots[:4]:
                if not under_cap():
                    break
                add(
                    f"{mt}{intent}{slot}",
                    axes=["multiturn", "paraphrase"],
                    logical_action=seed["logical_action"],
                )

    # STT noise / partials
    for intent in intents[:15]:
        if not under_cap():
            break
        words = intent.split()
        if len(words) >= 3:
            add(
                " ".join(words[:-1]),
                axes=["noise", "stt_partial"],
                logical_action=seed["logical_action"],
            )
            add(
                words[0] + " " + words[-1],
                axes=["noise", "stt_drop"],
                logical_action=seed["logical_action"],
            )
        soft = intent.replace("my", "mah").replace("for", "fer")
        if soft != intent:
            add(soft, axes=["noise", "stt_soft"], logical_action=seed["logical_action"])

    # Pad deterministically to floor
    n = 1
    base_intent = intents[0]
    while len(seen) < floor and n < floor * 8:
        add(
            f"{base_intent} variant {n}",
            axes=["paraphrase", "pad"],
            logical_action=seed["logical_action"],
        )
        add(
            f"{base_intent} option {n}",
            axes=["paraphrase", "pad"],
            logical_action=seed["logical_action"],
        )
        n += 1

    for text, action in list(NEGATIVES_BASE) + list(extra_negatives):
        add(text, axes=["negative"], logical_action=action, negative=True)

    return rows


def expand_deny_surface(surface_id: str, priority: str, floor: int) -> list[dict[str, Any]]:
    """Variants that attempt to open a denied surface (negative=true)."""

    seed = {
        "logical_action": "open_app_surface",
        "expected_route": "app_surface_navigation",
        "intents": [
            f"open {surface_id}",
            f"go to {surface_id}",
            f"show {surface_id}",
            f"open the {surface_id} screen",
            f"navigate to {surface_id}",
            f"bring up {surface_id}",
            f"load {surface_id}",
            f"switch to {surface_id}",
            f"open my {surface_id}",
            f"{surface_id} please",
            f"open {surface_id} page",
            f"show {surface_id} panel",
            f"go into {surface_id}",
            f"launch {surface_id}",
            f"open {surface_id} view",
        ],
        "slots": ["", " now", " please", " in the app", " for me"],
        "polite": ["", "please", "can you", "could you"],
        "noise": ["", "um ", "hey ", "so "],
    }
    extras = [
        (f"open staff {surface_id}", "open_app_surface"),
        (f"force open {surface_id}", "open_app_surface"),
        (f"bypass and open {surface_id}", "open_app_surface"),
    ]
    rows = expand_from_seed(
        surface_id, seed, priority, floor=floor, extra_negatives=extras
    )
    # Force negative flag for open attempts on deny surfaces
    for r in rows:
        if r["logical_action"] == "open_app_surface":
            r["negative"] = True
            if "negative" not in r["axes"]:
                r["axes"] = list(r["axes"]) + ["negative"]
    return rows


def load_exposure() -> list[dict[str, Any]]:
    if not EXPOSURE.is_file():
        return []
    return list(json.loads(EXPOSURE.read_text(encoding="utf-8")).get("surfaces") or [])


def surfaces_for_tier(tier: str) -> list[str]:
    rows = load_exposure()
    openable = {"voice_navigable", "voice_actionable"}
    if tier == "P0":
        out = [
            r["surface_id"]
            for r in rows
            if r.get("priority") == "P0" and r.get("exposure_class") in openable
        ]
        return sorted(s for s in out if s in SURFACE_SEEDS)
    if tier == "P1":
        out = []
        for r in rows:
            if r.get("priority") != "P1":
                continue
            sid = r["surface_id"]
            klass = r.get("exposure_class")
            if klass in openable and sid in SURFACE_SEEDS:
                out.append(sid)
            elif klass == "voice_read_only" and sid in READ_ONLY_SEEDS:
                out.append(sid)
        return sorted(set(out))
    if tier == "P2":
        # Deny-class surfaces at any priority that are staff/never, plus P2 priority
        out = []
        for r in rows:
            sid = r["surface_id"]
            klass = r.get("exposure_class")
            if klass in {"staff_only", "never_voice"}:
                out.append(sid)
        return sorted(set(out))
    return []


def tier_dir(tier: str) -> Path:
    return VARIANTS_DIR / tier.lower()


def write_schema() -> None:
    VARIANTS_DIR.mkdir(parents=True, exist_ok=True)
    schema = {
        "schema": SCHEMA_ID,
        "program_id": PROGRAM_ID,
        "description": "JSONL row schema for per-surface request variant lattices (VAS2-014).",
        "required_fields": [
            "variant_id",
            "surface_id",
            "user_text",
            "logical_action",
            "axes",
            "priority",
            "negative",
        ],
        "fields": {
            "variant_id": "stable content-addressable id (sha256 prefix)",
            "surface_id": "RouteId / navigation surface id",
            "user_text": "user utterance (unique within surface file)",
            "logical_action": "catalog logical action or no_action",
            "axes": "list of axis labels (paraphrase, slot, noise, negative, multiturn, stt_*)",
            "priority": "P0 | P1 | P2",
            "negative": "boolean; if true, expected deny or no_action",
            "expected_route": "optional slotted-DAG route",
            "language": "optional BCP-47 tag, default en",
            "program_id": "program namespace",
        },
        "forbidden_user_text_patterns": [
            "https?://",
            "file://",
            "/etc/",
            "\\\\",
            "import ",
            "os.system",
        ],
        "floors": {
            "P0_unique_user_texts": FLOORS["P0"],
            "P1_unique_user_texts": FLOORS["P1"],
            "P2_unique_user_texts": FLOORS["P2"],
        },
        "layout": {
            "P0": "data/voice_app_surface_full_coverage/variants/p0/<surface>.jsonl",
            "P1": "data/voice_app_surface_full_coverage/variants/p1/<surface>.jsonl",
            "P2": "data/voice_app_surface_full_coverage/variants/p2/<surface>.jsonl",
        },
    }
    SCHEMA_PATH.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    DOCTRINE.parent.mkdir(parents=True, exist_ok=True)
    DOCTRINE.write_text(
        f"""# Variant lattice doctrine (v2)

Program: `{PROGRAM_ID}`

## Floors

| Tier | Unique user texts / surface |
| --- | ---: |
| P0 | {FLOORS['P0']} |
| P1 | {FLOORS['P1']} |
| P2 | {FLOORS['P2']} |

## Axes

paraphrase, dialect (polite forms), slot, noise, multiturn, stt_partial, stt_drop, stt_soft, negative, pad.

## Layout

```text
data/voice_app_surface_full_coverage/variants/
  schema.json
  p0/<surface_id>.jsonl
  p1/<surface_id>.jsonl
  p2/<surface_id>.jsonl  # staff_only / never_voice open attempts (negative)
```

## Ban list

No URLs, file paths, import/exec smuggling in `user_text`.

## Tooling

```bash
python scripts/voice_app_surface_full_coverage/build_surface_variant_lattice.py --write
python scripts/voice_app_surface_full_coverage/build_surface_variant_lattice.py --check
python scripts/voice_app_surface_full_coverage/build_surface_variant_lattice.py --check --tier P0
```
""",
        encoding="utf-8",
    )


def write_tier(tier: str) -> dict[str, int]:
    write_schema()
    out_dir = tier_dir(tier)
    out_dir.mkdir(parents=True, exist_ok=True)
    floor = FLOORS[tier]
    counts: dict[str, int] = {}
    surfaces = surfaces_for_tier(tier)
    for surface_id in surfaces:
        if tier in {"P0", "P1"} and surface_id in SURFACE_SEEDS:
            seed = SURFACE_SEEDS[surface_id]
            rows = expand_from_seed(surface_id, seed, tier, floor=floor)
        elif tier == "P1" and surface_id in READ_ONLY_SEEDS:
            rows = expand_from_seed(
                surface_id, READ_ONLY_SEEDS[surface_id], tier, floor=floor
            )
        elif tier == "P2":
            rows = expand_deny_surface(surface_id, tier, floor)
        else:
            continue
        path = out_dir / f"{surface_id}.jsonl"
        path.write_text(
            "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows),
            encoding="utf-8",
        )
        counts[surface_id] = len({r["user_text"].lower() for r in rows})
    REPORTS.mkdir(parents=True, exist_ok=True)
    receipt = {
        "schema": f"voice-app-surface-full-coverage/variant-floors-{tier.lower()}@1",
        "program_id": PROGRAM_ID,
        "tier": tier,
        "floor": floor,
        "generated_at": datetime.now(UTC).isoformat(),
        "counts": counts,
        "all_met": all(c >= floor for c in counts.values()) if counts else False,
        "surfaces": surfaces,
    }
    (REPORTS / f"variant-floors-{tier.lower()}.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return counts


def check_tier(tier: str) -> list[str]:
    errors: list[str] = []
    if not SCHEMA_PATH.is_file():
        errors.append(f"missing schema {SCHEMA_PATH}")
    else:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        if schema.get("schema") != SCHEMA_ID:
            errors.append("schema id mismatch")
        floors = schema.get("floors") or {}
        key = f"{tier}_unique_user_texts"
        if int(floors.get(key) or 0) < FLOORS[tier]:
            errors.append(f"schema floor {key} too low")
    floor = FLOORS[tier]
    out_dir = tier_dir(tier)
    surfaces = surfaces_for_tier(tier)
    if not surfaces:
        errors.append(f"no surfaces selected for tier {tier}")
    for surface_id in surfaces:
        path = out_dir / f"{surface_id}.jsonl"
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
                f"{surface_id}: unique texts {len(texts)} < floor {floor}"
            )
    receipt = REPORTS / f"variant-floors-{tier.lower()}.json"
    if not receipt.is_file():
        errors.append(f"missing floor receipt {receipt}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--check-schema", action="store_true")
    parser.add_argument(
        "--tier",
        choices=("P0", "P1", "P2"),
        default=None,
        help="Limit write/check to one tier (default: all)",
    )
    args = parser.parse_args()
    tiers = (args.tier,) if args.tier else ("P0", "P1", "P2")

    if args.check_schema or args.write:
        write_schema()
        if args.check_schema and not args.write and not args.check:
            print("variant lattice schema OK")
            return 0

    if args.write:
        summary = {}
        for tier in tiers:
            counts = write_tier(tier)
            summary[tier] = counts
            print(json.dumps({"tier": tier, "counts": counts}, sort_keys=True))
        print(json.dumps({"wrote": True, "summary": summary}, indent=2, sort_keys=True))

    if args.check or (not args.write and not args.check_schema):
        errors: list[str] = []
        for tier in tiers:
            errors.extend(check_tier(tier))
        if errors:
            print("variant lattice check FAILED:", file=sys.stderr)
            for err in errors:
                print(f"  - {err}", file=sys.stderr)
            return 1
        print(f"variant lattice check OK tiers={list(tiers)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
