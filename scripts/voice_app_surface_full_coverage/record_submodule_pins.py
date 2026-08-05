#!/usr/bin/env python3
"""Record monorepo submodule pins for voice-app-surface-coverage (VAS2-002).

Fast-forward to origin/main is preferred when safe. When histories have
diverged (or origin/main lacks monorepo-required modules), this tool records
both the **working pin** (required for product continuity) and the fetched
**origin/main tip**, without discarding local safety branches.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = (
    REPO_ROOT
    / "data"
    / "voice_app_surface_full_coverage"
    / "baseline"
    / "submodule-pins.json"
)
SCHEMA = "voice-app-surface-full-coverage/submodule-pins@1"
PROGRAM_ID = "voice-app-surface-full-coverage-v2"
SUBMODULES = (
    "ipfs_accelerate_py",
    "ipfs_datasets_py",
    "ipfs_kit_py",
)
# Modules that must remain importable for VAS continuity after any pin move.
REQUIRED_PATHS = {
    "ipfs_accelerate_py": (
        "ipfs_accelerate_py/action_runtime/voice_bridge.py",
        "ipfs_accelerate_py/action_runtime/catalog_211ai.py",
    ),
    "ipfs_datasets_py": (
        "ipfs_datasets_py/voice/action_links.py",
        "ipfs_datasets_py/voice/action_retrieval.py",
    ),
    "ipfs_kit_py": (),
}


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ("git", "-C", str(cwd), *args),
        check=False,
        capture_output=True,
        text=True,
    )


def _text(result: subprocess.CompletedProcess[str]) -> str:
    return (result.stdout or "").strip()


def _inspect_submodule(name: str) -> dict[str, Any]:
    path = REPO_ROOT / name
    row: dict[str, Any] = {
        "name": name,
        "path": name,
        "exists": path.is_dir(),
        "is_git": (path / ".git").exists() or (path / ".git").is_file(),
    }
    if not row["is_git"]:
        row["error"] = "not a git checkout"
        return row

    head = _text(_git(path, "rev-parse", "HEAD"))
    origin_main = _text(_git(path, "rev-parse", "origin/main^{commit}"))
    remote = _text(_git(path, "config", "--get", "remote.origin.url"))
    branch = _text(_git(path, "rev-parse", "--abbrev-ref", "HEAD"))
    status = _text(_git(path, "status", "-sb"))
    ahead = behind = None
    if origin_main:
        ahead_s = _text(_git(path, "rev-list", "--count", f"origin/main..{head}"))
        behind_s = _text(_git(path, "rev-list", "--count", f"{head}..origin/main"))
        try:
            ahead = int(ahead_s)
            behind = int(behind_s)
        except ValueError:
            ahead = behind = None
    merge_base = _text(_git(path, "merge-base", head, "origin/main")) if origin_main else ""
    can_ff_to_origin = bool(
        origin_main and merge_base == head and head != origin_main
    )
    already_at_origin = bool(origin_main and head == origin_main)
    diverged = bool(
        origin_main
        and head
        and origin_main != head
        and merge_base not in {head, origin_main, ""}
        and (ahead or 0) > 0
        and (behind or 0) > 0
    )

    missing_required: list[str] = []
    for rel in REQUIRED_PATHS.get(name, ()):
        if not (path / rel).is_file():
            missing_required.append(rel)

    origin_missing_required: list[str] = []
    if origin_main and origin_main != head:
        for rel in REQUIRED_PATHS.get(name, ()):
            probe = _git(path, "cat-file", "-e", f"origin/main:{rel}")
            if probe.returncode != 0:
                origin_missing_required.append(rel)

    row.update(
        {
            "remote_origin_url": remote,
            "working_sha": head,
            "working_branch": branch,
            "origin_main_sha": origin_main or None,
            "merge_base_with_origin_main": merge_base or None,
            "ahead_of_origin_main": ahead,
            "behind_origin_main": behind,
            "already_at_origin_main": already_at_origin,
            "can_fast_forward_to_origin_main": can_ff_to_origin,
            "diverged_from_origin_main": diverged,
            "status_sb": status.splitlines()[0] if status else "",
            "required_paths_missing_at_working": missing_required,
            "required_paths_missing_at_origin_main": origin_missing_required,
            "safe_to_ff_to_origin_main": bool(
                can_ff_to_origin and not origin_missing_required
            ),
            "pin_policy": (
                "use_working_sha"
                if diverged or origin_missing_required
                else ("origin_main" if already_at_origin or can_ff_to_origin else "use_working_sha")
            ),
        }
    )
    if diverged:
        row["operator_note"] = (
            "History diverged from origin/main; FF-only pull refused. "
            "Keep working_sha for product continuity; integrate separately."
        )
    elif origin_missing_required:
        row["operator_note"] = (
            "origin/main is missing monorepo-required modules; "
            "do not switch pin until modules are merged upstream."
        )
    elif can_ff_to_origin:
        row["operator_note"] = "Safe to fast-forward working pin to origin/main."
    elif already_at_origin:
        row["operator_note"] = "Working pin already matches origin/main."
    else:
        row["operator_note"] = "Recorded working pin; review relationship to origin/main."
    return row


def build_receipt(*, operator_note: str = "") -> dict[str, Any]:
    monorepo_head = _text(_git(REPO_ROOT, "rev-parse", "HEAD"))
    monorepo_origin = _text(_git(REPO_ROOT, "rev-parse", "origin/main^{commit}"))
    rows = [_inspect_submodule(name) for name in SUBMODULES]
    blocked = [
        row["name"]
        for row in rows
        if row.get("diverged_from_origin_main")
        or row.get("required_paths_missing_at_origin_main")
    ]
    return {
        "schema": SCHEMA,
        "program_id": PROGRAM_ID,
        "task_id": "VAS2-002",
        "generated_at": datetime.now(UTC).isoformat(),
        "monorepo": {
            "path": ".",
            "working_sha": monorepo_head,
            "origin_main_sha": monorepo_origin or None,
        },
        "submodules": rows,
        "safety_branches": {
            "ipfs_accelerate_py": "safety/pre-vas2-002-accelerate",
            "ipfs_datasets_py": "safety/pre-vas2-002-datasets",
        },
        "ff_to_origin_main_blocked_for": blocked,
        "decision": (
            "retain_working_pins_document_divergence"
            if blocked
            else "working_pins_track_or_match_origin_main"
        ),
        "operator_note": operator_note
        or (
            "Fetched origin/main for accelerate and datasets. "
            "datasets was temporarily FF'd then restored because origin/main "
            "lacks voice action_links/action_retrieval. accelerate remains on "
            "working pin (diverged: local voice-action commits vs origin/main). "
            "Safety branches preserve pre-VAS2-002 SHAs."
        ),
    }


def write_receipt(path: Path, receipt: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def check_receipt(path: Path) -> list[str]:
    errors: list[str] = []
    if not path.is_file():
        return [f"pin receipt missing: {path}"]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return [f"cannot read pin receipt: {exc}"]
    if payload.get("schema") != SCHEMA:
        errors.append(f"unexpected schema {payload.get('schema')!r}")
    if payload.get("program_id") != PROGRAM_ID:
        errors.append("program_id mismatch")
    subs = payload.get("submodules")
    if not isinstance(subs, list) or len(subs) < 2:
        errors.append("submodules list incomplete")
    else:
        by_name = {row.get("name"): row for row in subs if isinstance(row, dict)}
        for name in ("ipfs_accelerate_py", "ipfs_datasets_py"):
            row = by_name.get(name)
            if not row:
                errors.append(f"missing submodule row {name}")
                continue
            if not row.get("working_sha"):
                errors.append(f"{name} missing working_sha")
            if not row.get("origin_main_sha"):
                errors.append(f"{name} missing origin_main_sha (fetch origin first)")
            # Working tree must still satisfy required modules.
            for rel in REQUIRED_PATHS.get(name, ()):
                if not (REPO_ROOT / name / rel).is_file():
                    errors.append(f"working tree missing required {name}/{rel}")
    return errors



def write_voice_module_probe(pins: dict[str, Any]) -> dict[str, Any]:
    """Probe required voice modules at working pins; write receipt next to pins."""
    probe_path = DEFAULT_OUT.parent / "voice-module-probe.json"
    modules = []
    ok = True
    for name, rels in REQUIRED_PATHS.items():
        sub = REPO_ROOT / name
        for rel in rels:
            path = sub / rel
            present = path.is_file()
            modules.append({
                "submodule": name,
                "path": f"{name}/{rel}",
                "present": present,
            })
            if not present:
                ok = False
    payload = {
        "schema": "voice-app-surface-full-coverage/voice-module-probe@1",
        "program_id": PROGRAM_ID,
        "generated_at": datetime.now(UTC).isoformat(),
        "ok": ok,
        "modules": modules,
        "pins_path": str(DEFAULT_OUT.relative_to(REPO_ROOT)),
        "working_shas": {
            row.get("name"): row.get("working_sha")
            for row in (pins.get("submodules") or [])
            if isinstance(row, dict)
        },
    }
    probe_path.parent.mkdir(parents=True, exist_ok=True)
    probe_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Write pin receipt JSON")
    parser.add_argument("--check", action="store_true", help="Validate existing receipt")
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help=f"Receipt path (default {DEFAULT_OUT})",
    )
    parser.add_argument("--operator-note", default="", help="Extra note embedded in receipt")
    args = parser.parse_args()

    if args.check and not args.write:
        errors = check_receipt(args.out)
        if errors:
            print("submodule pin check FAILED:", file=sys.stderr)
            for err in errors:
                print(f"  - {err}", file=sys.stderr)
            return 1
        print(f"submodule pin check OK: {args.out}")
        return 0

    receipt = build_receipt(operator_note=args.operator_note)
    if args.write:
        write_receipt(args.out, receipt)
        print(f"wrote {args.out}")
        probe = write_voice_module_probe(receipt)
        print(
            f"wrote {DEFAULT_OUT.parent / 'voice-module-probe.json'} "
            f"ok={probe.get('ok')}"
        )
        if not probe.get("ok"):
            print("voice module probe FAILED", file=sys.stderr)
            return 1
    else:
        print(json.dumps(receipt, indent=2, sort_keys=True))

    if args.check:
        errors = check_receipt(args.out)
        if errors:
            print("submodule pin check FAILED:", file=sys.stderr)
            for err in errors:
                print(f"  - {err}", file=sys.stderr)
            return 1
        print("submodule pin check OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
