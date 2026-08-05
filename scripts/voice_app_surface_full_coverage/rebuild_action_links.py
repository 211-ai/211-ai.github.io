#!/usr/bin/env python3
"""Rebuild slotted_response_action_links and write VAS2 receipt (VAS2-020)."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BUILDER = REPO / "scripts" / "build_slotted_response_action_links.py"
LINKS = REPO / "docs" / "phone_dialog_generation" / "slotted_response_action_links.json"
RECEIPT = (
    REPO
    / "data"
    / "voice_app_surface_full_coverage"
    / "reports"
    / "action-link-rebuild-receipt.json"
)
PROGRAM_ID = "voice-app-surface-full-coverage-v2"


def _digest(path: Path) -> str:
    h = hashlib.sha256(path.read_bytes()).hexdigest()
    return f"sha256:{h}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    if args.write or not args.check:
        cmd = [sys.executable, str(BUILDER), "--write"]
        proc = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
        if proc.returncode != 0:
            print(proc.stdout)
            print(proc.stderr, file=sys.stderr)
            return proc.returncode
        print(proc.stdout.strip())

    if not LINKS.is_file():
        print(f"missing {LINKS}", file=sys.stderr)
        return 1
    doc = json.loads(LINKS.read_text(encoding="utf-8"))
    links = doc.get("links") or doc.get("action_links") or []
    receipt = {
        "schema": "voice-app-surface-full-coverage/action-link-rebuild@1",
        "program_id": PROGRAM_ID,
        "task_id": "VAS2-020",
        "generated_at": datetime.now(UTC).isoformat(),
        "links_path": str(LINKS.relative_to(REPO)),
        "links_digest": _digest(LINKS),
        "link_count": len(links) if isinstance(links, list) else None,
        "builder": str(BUILDER.relative_to(REPO)),
        "status": "ok",
    }
    if args.write or not RECEIPT.is_file():
        RECEIPT.parent.mkdir(parents=True, exist_ok=True)
        RECEIPT.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
        print(f"wrote {RECEIPT}")

    if args.check:
        if not RECEIPT.is_file():
            print("missing action-link rebuild receipt", file=sys.stderr)
            return 1
        r = json.loads(RECEIPT.read_text())
        if r.get("status") != "ok":
            print("receipt status not ok", file=sys.stderr)
            return 1
        # re-run builder check
        proc = subprocess.run(
            [sys.executable, str(BUILDER), "--check"],
            cwd=REPO,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            print(proc.stderr, file=sys.stderr)
            return proc.returncode
        print("action link rebuild OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
