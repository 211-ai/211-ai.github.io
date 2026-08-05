#!/usr/bin/env python3
"""Classify voice/phone amenability for every app surface (VAS-006 / VAS-007)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
BASELINE = REPO_ROOT / "data" / "voice_app_surface_coverage" / "baseline"
SURFACE_INV = BASELINE / "app-surface-inventory.json"
BINDING_INV = BASELINE / "binding-inventory.json"
EXPOSURE = BASELINE / "voice-exposure-matrix.json"
GAPS = BASELINE / "coverage-gap-matrix.json"
DOCTRINE = REPO_ROOT / "docs" / "voice_app_surface_coverage" / "VOICE_EXPOSURE_DOCTRINE.md"
GAPS_DOC = REPO_ROOT / "docs" / "voice_app_surface_coverage" / "COVERAGE_GAPS.md"
ACTION_LINKS = (
    REPO_ROOT / "docs" / "phone_dialog_generation" / "slotted_response_action_links.json"
)
ROUTE_GAP = REPO_ROOT / "data" / "voice_action_dag" / "baseline" / "route-gap-matrix.json"
SPEECH_FRAMES = (
    REPO_ROOT / "docs" / "phone_dialog_generation" / "action_speech_frames.jsonl"
)
PROGRAM_ID = "voice-app-surface-coverage-v1"
SCHEMA_EXPOSURE = "voice-app-surface-coverage/voice-exposure-matrix@1"
SCHEMA_GAPS = "voice-app-surface-coverage/coverage-gap-matrix@1"
EXPOSURE_CLASSES = frozenset(
    {
        "voice_navigable",
        "voice_actionable",
        "voice_read_only",
        "phone_handoff",
        "staff_only",
        "never_voice",
    }
)

# Conservative initial classification for the full allowlist.
# Human review may override via matrix edits + rationale.
DEFAULT_CLASS: dict[str, dict[str, Any]] = {
    "home": {
        "class": "voice_navigable",
        "priority": "P0",
        "risk_class": "read",
        "allowed_channels": ["voice", "chat"],
        "logical_actions": ["open_app_surface"],
        "rationale": "Client home is a safe navigation target after confirm.",
    },
    "check-in": {
        "class": "voice_navigable",
        "priority": "P0",
        "risk_class": "read",
        "allowed_channels": ["voice", "chat"],
        "logical_actions": ["open_app_surface"],
        "rationale": "Check-in surface is client-facing; mutations stay behind later tools.",
    },
    "calendar": {
        "class": "voice_actionable",
        "priority": "P0",
        "risk_class": "read",
        "allowed_channels": ["voice", "chat"],
        "logical_actions": [
            "open_app_surface",
            "read_calendar",
            "create_calendar_reminder",
        ],
        "rationale": "Core pilot calendar reads/writes with confirm (+auth for write).",
    },
    "messages": {
        "class": "voice_actionable",
        "priority": "P0",
        "risk_class": "read",
        "allowed_channels": ["voice", "chat"],
        "logical_actions": [
            "open_app_surface",
            "read_provider_messages",
            "leave_provider_message",
        ],
        "rationale": "Messaging pilot actions with confirm+auth.",
    },
    "contacts": {
        "class": "voice_navigable",
        "priority": "P0",
        "risk_class": "read",
        "allowed_channels": ["voice", "chat"],
        "logical_actions": ["open_app_surface"],
        "rationale": "Navigate contacts; sensitive grants stay never_voice.",
    },
    "social-services": {
        "class": "voice_actionable",
        "priority": "P0",
        "risk_class": "read",
        "allowed_channels": ["voice", "chat"],
        "logical_actions": [
            "open_app_surface",
            "open_service_detail",
            "schedule_service_callback",
        ],
        "rationale": "Service navigation + grounded detail/callback pilot.",
    },
    "interactions": {
        "class": "voice_navigable",
        "priority": "P0",
        "risk_class": "read",
        "allowed_channels": ["voice", "chat"],
        "logical_actions": ["open_app_surface"],
        "rationale": "History surface open after confirm.",
    },
    "uploads": {
        "class": "voice_actionable",
        "priority": "P0",
        "risk_class": "read",
        "allowed_channels": ["voice", "chat"],
        "logical_actions": ["open_wallet_documents", "open_app_surface"],
        "rationale": "Wallet documents pilot open; no bulk export via voice.",
    },
    "settings": {
        "class": "voice_navigable",
        "priority": "P0",
        "risk_class": "read",
        "allowed_channels": ["voice", "chat"],
        "logical_actions": ["open_app_surface"],
        "rationale": "Open settings UI only; credential changes never_voice.",
    },
    "register": {
        "class": "voice_navigable",
        "priority": "P1",
        "risk_class": "read",
        "allowed_channels": ["voice", "chat"],
        "logical_actions": ["open_app_surface"],
        "rationale": "Registration guidance/navigation; submission stays out of auto-execute.",
    },
    "analytics": {
        "class": "voice_read_only",
        "priority": "P1",
        "risk_class": "read",
        "allowed_channels": ["chat"],
        "logical_actions": [],
        "rationale": "Prefer spoken summaries later; no client phone navigation by default.",
    },
    "proof-center": {
        "class": "voice_read_only",
        "priority": "P1",
        "risk_class": "read",
        "allowed_channels": ["chat"],
        "logical_actions": [],
        "rationale": "Proofs are sensitive; voice open deferred.",
    },
    "audit": {
        "class": "never_voice",
        "priority": "P2",
        "risk_class": "admin",
        "allowed_channels": [],
        "logical_actions": [],
        "rationale": "Audit trail is staff/ops sensitive.",
    },
    "security": {
        "class": "never_voice",
        "priority": "P0",
        "risk_class": "admin",
        "allowed_channels": [],
        "logical_actions": [],
        "rationale": "Security controls must not be voice-driven.",
    },
    "exports": {
        "class": "never_voice",
        "priority": "P0",
        "risk_class": "write",
        "allowed_channels": [],
        "logical_actions": [],
        "rationale": "Bulk export is high risk for voice/phone.",
    },
    "recipient-access": {
        "class": "never_voice",
        "priority": "P0",
        "risk_class": "write",
        "allowed_channels": [],
        "logical_actions": [],
        "rationale": "Disclosure grants are not voice-amenable by default.",
    },
    "sharing-rules": {
        "class": "never_voice",
        "priority": "P0",
        "risk_class": "write",
        "allowed_channels": [],
        "logical_actions": [],
        "rationale": "Sharing policy changes require deliberate UI.",
    },
    "benefits-protection": {
        "class": "never_voice",
        "priority": "P1",
        "risk_class": "read",
        "allowed_channels": [],
        "logical_actions": [],
        "rationale": "Benefits protection flows are high-stakes; keep off phone auto-nav.",
    },
    "shelter": {
        "class": "staff_only",
        "priority": "P1",
        "risk_class": "read",
        "allowed_channels": ["chat"],
        "logical_actions": [],
        "rationale": "Provider portal overview; deny on client voice channel.",
    },
    "provider-clients": {
        "class": "staff_only",
        "priority": "P1",
        "risk_class": "read",
        "allowed_channels": ["chat"],
        "logical_actions": [],
        "rationale": "Staff clients list.",
    },
    "provider-cases": {
        "class": "staff_only",
        "priority": "P1",
        "risk_class": "read",
        "allowed_channels": ["chat"],
        "logical_actions": [],
        "rationale": "Case management is staff-only.",
    },
    "provider-messages": {
        "class": "staff_only",
        "priority": "P1",
        "risk_class": "read",
        "allowed_channels": ["chat"],
        "logical_actions": [],
        "rationale": "Staff message console; client uses messages surface.",
    },
    "provider-analytics": {
        "class": "staff_only",
        "priority": "P2",
        "risk_class": "read",
        "allowed_channels": [],
        "logical_actions": [],
        "rationale": "Staff analytics.",
    },
    "provider-proofs": {
        "class": "staff_only",
        "priority": "P2",
        "risk_class": "read",
        "allowed_channels": [],
        "logical_actions": [],
        "rationale": "Staff ZK certificates.",
    },
    "provider-operations": {
        "class": "staff_only",
        "priority": "P2",
        "risk_class": "admin",
        "allowed_channels": [],
        "logical_actions": [],
        "rationale": "Staff operations console.",
    },
}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _route_density() -> dict[str, int]:
    if ROUTE_GAP.is_file():
        payload = _load(ROUTE_GAP)
        census = payload.get("route_census") or {}
        if isinstance(census, dict):
            return {str(k): int(v) for k, v in census.items()}
    return {}


def _speech_actions() -> set[str]:
    actions: set[str] = set()
    if not SPEECH_FRAMES.is_file():
        return actions
    for line in SPEECH_FRAMES.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        la = row.get("logical_action")
        if la:
            actions.add(str(la))
    return actions


def build_exposure(surface_inv: dict[str, Any]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for surface in surface_inv.get("surfaces") or []:
        sid = str(surface["id"])
        preset = DEFAULT_CLASS.get(sid)
        if preset is None:
            # Fail closed for unknown surfaces.
            preset = {
                "class": "never_voice",
                "priority": "P2",
                "risk_class": "admin",
                "allowed_channels": [],
                "logical_actions": [],
                "rationale": "Unknown surface defaults to never_voice until reviewed.",
            }
        klass = preset["class"]
        if klass not in EXPOSURE_CLASSES:
            raise ValueError(f"invalid class for {sid}: {klass}")
        rows.append(
            {
                "surface_id": sid,
                "label": surface.get("label"),
                "family": surface.get("family"),
                "is_provider": surface.get("is_provider"),
                "exposure_class": klass,
                "priority": preset["priority"],
                "risk_class": preset["risk_class"],
                "allowed_channels": list(preset["allowed_channels"]),
                "logical_actions": list(preset["logical_actions"]),
                "rationale": preset["rationale"],
                "in_navigation_allowlist": surface.get("in_navigation_allowlist"),
            }
        )
    by_class: dict[str, int] = {c: 0 for c in sorted(EXPOSURE_CLASSES)}
    for row in rows:
        by_class[row["exposure_class"]] += 1
    return {
        "schema": SCHEMA_EXPOSURE,
        "program_id": PROGRAM_ID,
        "task_ids": ["VAS-006"],
        "generated_at": datetime.now(UTC).isoformat(),
        "doctrine": "docs/voice_app_surface_coverage/VOICE_EXPOSURE_DOCTRINE.md",
        "counts_by_class": by_class,
        "surfaces": sorted(rows, key=lambda r: r["surface_id"]),
        "notes": [
            "Initial classification is conservative; human overrides require rationale.",
            "staff_only and never_voice must deny on client voice/phone channel.",
        ],
    }


def build_gaps(
    exposure: dict[str, Any],
    binding: dict[str, Any],
) -> dict[str, Any]:
    density = _route_density()
    speech = _speech_actions()
    catalog = set(binding.get("catalog_logical_actions") or [])
    # Map surfaces to primary DAG routes for density (best-effort).
    surface_routes = {
        "calendar": ["calendar_event_support", "app_surface_navigation"],
        "messages": ["provider_contact_support"],
        "uploads": ["wallet_document_support"],
        "social-services": ["grounded_211_answer", "service_interaction_support"],
        "home": ["app_surface_navigation"],
        "check-in": ["app_surface_navigation"],
        "contacts": ["app_surface_navigation"],
        "interactions": ["app_surface_navigation"],
        "settings": ["app_surface_navigation"],
    }
    rows = []
    for surface in exposure.get("surfaces") or []:
        sid = surface["surface_id"]
        klass = surface["exposure_class"]
        actions = list(surface.get("logical_actions") or [])
        routes = surface_routes.get(sid, [])
        dag_edges = sum(density.get(r, 0) for r in routes)
        missing_catalog = [a for a in actions if a not in catalog]
        missing_speech = [a for a in actions if a not in speech]
        needs_work = klass in {"voice_navigable", "voice_actionable"}
        holes = []
        if needs_work and dag_edges < 200:
            holes.append("dag_density_below_p0_floor")
        if missing_catalog:
            holes.append("catalog_gap")
        if missing_speech:
            holes.append("speech_frame_gap")
        if needs_work and not routes:
            holes.append("no_dag_route_mapping")
        rows.append(
            {
                "surface_id": sid,
                "exposure_class": klass,
                "priority": surface.get("priority"),
                "logical_actions": actions,
                "dag_routes": routes,
                "dag_edge_count_approx": dag_edges,
                "catalog_actions_present": [a for a in actions if a in catalog],
                "catalog_actions_missing": missing_catalog,
                "speech_actions_missing": missing_speech,
                "holes": holes,
                "p0_attention": needs_work and surface.get("priority") == "P0",
            }
        )
    p0_holes = [r for r in rows if r.get("p0_attention") and r.get("holes")]
    return {
        "schema": SCHEMA_GAPS,
        "program_id": PROGRAM_ID,
        "task_ids": ["VAS-007"],
        "generated_at": datetime.now(UTC).isoformat(),
        "route_density_source": str(ROUTE_GAP.relative_to(REPO_ROOT))
        if ROUTE_GAP.is_file()
        else None,
        "surfaces": sorted(rows, key=lambda r: r["surface_id"]),
        "p0_surfaces_with_holes": [r["surface_id"] for r in p0_holes],
        "counts": {
            "surfaces": len(rows),
            "p0_with_holes": len(p0_holes),
        },
    }


def write_doctrine() -> None:
    text = """# Voice Exposure Doctrine

Program: `voice-app-surface-coverage-v1`
Task: `VAS-006`

## Purpose

Classify every 211-AI app surface for voice/phone amenability. The matrix is
**authority** for whether the content plane may propose opening or acting on a
surface under a given channel/role.

## Classes

| Class | Client voice/phone | Meaning |
| --- | --- | --- |
| `voice_navigable` | allow after confirm | Open UI surface only |
| `voice_actionable` | allow after confirm (+auth if write) | Open and/or tool actions |
| `voice_read_only` | speak only (optional later) | No surface mutation |
| `phone_handoff` | handoff path | Live agent / safety |
| `staff_only` | **deny** on client channel | Provider portal |
| `never_voice` | **deny** | Too sensitive/destructive |

## Defaults

- Unknown surface → `never_voice`.
- Security, exports, sharing grants, audit → `never_voice`.
- Provider portal routes → `staff_only`.
- Calendar / messages / wallet / services → `voice_actionable` (pilot).
- Remaining client core → `voice_navigable`.

## Non-negotiables

1. Content never embeds executables or locators.
2. Catalog logical actions only.
3. Confidence never upgrades authority.
4. `staff_only` / `never_voice` fail closed on client voice/phone.
5. Human override of class requires written rationale in the matrix.

## Artifacts

- Matrix: `data/voice_app_surface_coverage/baseline/voice-exposure-matrix.json`
- Gaps: `data/voice_app_surface_coverage/baseline/coverage-gap-matrix.json`
"""
    DOCTRINE.parent.mkdir(parents=True, exist_ok=True)
    DOCTRINE.write_text(text, encoding="utf-8")


def write_gaps_doc(gaps: dict[str, Any]) -> None:
    lines = [
        "# Coverage Gaps",
        "",
        f"Program: `{PROGRAM_ID}`  ",
        "Task: `VAS-007`  ",
        f"Generated: `{gaps.get('generated_at')}`",
        "",
        f"P0 surfaces with holes: **{gaps['counts']['p0_with_holes']}**",
        "",
        "| surface | class | priority | dag edges | holes |",
        "| --- | --- | --- | ---: | --- |",
    ]
    for row in gaps.get("surfaces") or []:
        holes = ", ".join(row.get("holes") or []) or "—"
        lines.append(
            f"| `{row['surface_id']}` | {row['exposure_class']} | "
            f"{row.get('priority')} | {row.get('dag_edge_count_approx')} | {holes} |"
        )
    lines.append("")
    GAPS_DOC.parent.mkdir(parents=True, exist_ok=True)
    GAPS_DOC.write_text("\n".join(lines), encoding="utf-8")


def check_exposure() -> list[str]:
    errors: list[str] = []
    if not EXPOSURE.is_file():
        return [f"missing {EXPOSURE}"]
    payload = json.loads(EXPOSURE.read_text(encoding="utf-8"))
    if payload.get("schema") != SCHEMA_EXPOSURE:
        errors.append("exposure schema mismatch")
    rows = payload.get("surfaces") or []
    if not rows:
        errors.append("exposure matrix empty")
    seen: set[str] = set()
    for row in rows:
        sid = row.get("surface_id")
        klass = row.get("exposure_class")
        if sid in seen:
            errors.append(f"duplicate surface {sid}")
        seen.add(str(sid))
        if klass not in EXPOSURE_CLASSES:
            errors.append(f"{sid} has invalid class {klass!r}")
        if not str(row.get("rationale") or "").strip():
            errors.append(f"{sid} missing rationale")
    if SURFACE_INV.is_file():
        inv = _load(SURFACE_INV)
        inv_ids = {s["id"] for s in inv.get("surfaces") or []}
        if inv_ids - seen:
            errors.append(f"unclassified surfaces: {sorted(inv_ids - seen)}")
        if seen - inv_ids:
            errors.append(f"matrix has unknown surfaces: {sorted(seen - inv_ids)}")
    if not DOCTRINE.is_file():
        errors.append(f"missing doctrine {DOCTRINE}")
    return errors


def check_gaps() -> list[str]:
    errors = check_exposure()
    if not GAPS.is_file():
        errors.append(f"missing {GAPS}")
        return errors
    payload = json.loads(GAPS.read_text(encoding="utf-8"))
    if payload.get("schema") != SCHEMA_GAPS:
        errors.append("gaps schema mismatch")
    if not GAPS_DOC.is_file():
        errors.append(f"missing {GAPS_DOC}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--check-gaps", action="store_true")
    args = parser.parse_args()

    if not SURFACE_INV.is_file():
        print("run audit_app_surface.py --write first", file=sys.stderr)
        return 1

    if args.write or not (args.check or args.check_gaps):
        surface_inv = _load(SURFACE_INV)
        binding = _load(BINDING_INV) if BINDING_INV.is_file() else {}
        exposure = build_exposure(surface_inv)
        gaps = build_gaps(exposure, binding)
        EXPOSURE.parent.mkdir(parents=True, exist_ok=True)
        EXPOSURE.write_text(
            json.dumps(exposure, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        GAPS.write_text(
            json.dumps(gaps, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        write_doctrine()
        write_gaps_doc(gaps)
        print(f"wrote {EXPOSURE}")
        print(f"wrote {GAPS}")
        print(f"wrote {DOCTRINE}")
        print(f"wrote {GAPS_DOC}")

    errors: list[str] = []
    if args.check:
        errors.extend(check_exposure())
    if args.check_gaps:
        errors.extend(check_gaps())
    if errors:
        print("voice exposure audit FAILED:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1
    if args.check or args.check_gaps:
        print("voice exposure audit OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
