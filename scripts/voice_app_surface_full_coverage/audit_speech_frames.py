#!/usr/bin/env python3
"""Audit speech frames for VAS2-023/024/025."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ACTION = REPO / "docs/phone_dialog_generation/action_speech_frames.jsonl"
SURFACE = REPO / "docs/phone_dialog_generation/surface_navigation_speech_frames.jsonl"
DAG = REPO / "docs/phone_dialog_generation/dag_high_traffic_speech_frames.jsonl"
BUDGET = REPO / "data/voice_app_surface_full_coverage/reports/dag-speech-budget.json"

PILOT_ACTIONS = {
    "handoff_live_agent",
    "open_app_surface",
    "open_wallet_documents",
    "read_calendar",
    "create_calendar_reminder",
    "read_provider_messages",
    "leave_provider_message",
    "open_service_detail",
    "schedule_service_callback",
    "escalate_safety",
}
OPENABLE = {
    "home",
    "register",
    "check-in",
    "calendar",
    "messages",
    "contacts",
    "social-services",
    "interactions",
    "uploads",
    "settings",
}
ROLES = {"confirm", "success", "deny", "fail"}
FORBIDDEN = re.compile(r"https?://|file://|/etc/|os\.system|import\s+", re.I)


def load(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def check_actions() -> list[str]:
    errors = []
    rows = load(ACTION)
    if not rows:
        return ["missing action speech frames"]
    by = defaultdict(set)
    for r in rows:
        if FORBIDDEN.search(str(r.get("spoken_text") or "")):
            errors.append(f"forbidden content in {r.get('frame_id')}")
        by[r.get("logical_action")].add(r.get("role"))
    for a in PILOT_ACTIONS:
        missing = ROLES - by.get(a, set())
        if missing:
            errors.append(f"{a}: missing roles {sorted(missing)}")
    return errors


def check_surfaces() -> list[str]:
    errors = []
    rows = load(SURFACE)
    if not rows:
        return ["missing surface speech frames"]
    by = defaultdict(set)
    for r in rows:
        if FORBIDDEN.search(str(r.get("spoken_text") or "")):
            errors.append(f"forbidden content in {r.get('frame_id')}")
        by[r.get("surface_id")].add(r.get("role"))
    for s in OPENABLE:
        missing = ROLES - by.get(s, set())
        if missing:
            errors.append(f"{s}: missing roles {sorted(missing)}")
    return errors


def check_dag_budget() -> list[str]:
    errors = []
    if not DAG.is_file():
        return ["missing dag high traffic frames"]
    if not BUDGET.is_file():
        return ["missing dag speech budget receipt"]
    rows = load(DAG)
    b = json.loads(BUDGET.read_text())
    if len(rows) < 20:
        errors.append(f"too few dag frames: {len(rows)}")
    if b.get("budgeted_frames") != len(rows):
        errors.append("budget receipt count mismatch")
    for r in rows:
        if FORBIDDEN.search(str(r.get("spoken_text") or "")):
            errors.append(f"forbidden in {r.get('frame_id')}")
    return errors


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--check", action="store_true")
    p.add_argument("--check-actions", action="store_true")
    p.add_argument("--check-surfaces", action="store_true")
    p.add_argument("--check-dag-budget", action="store_true")
    args = p.parse_args()
    if not any([args.check, args.check_actions, args.check_surfaces, args.check_dag_budget]):
        args.check = True
    errors: list[str] = []
    if args.check or args.check_actions:
        errors.extend(check_actions())
    if args.check or args.check_surfaces:
        errors.extend(check_surfaces())
    if args.check or args.check_dag_budget:
        errors.extend(check_dag_budget())
    if errors:
        print("speech frames FAILED:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1
    print("speech frames OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
