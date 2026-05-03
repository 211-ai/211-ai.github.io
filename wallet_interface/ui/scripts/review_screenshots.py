#!/usr/bin/env python3
"""Review Abby UI screenshots with ipfs_datasets_py.multimodal_router.

This script reads Playwright visual-capture manifests, sends each screenshot to
the multimodal router with the route-specific prompt, and writes both JSON and
Markdown feedback artifacts. Use --dry-run to validate manifests without making
provider calls.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


UI_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = UI_ROOT.parents[1]
DEFAULT_MANIFEST_GLOB = "artifacts/ui-screenshots/latest/*/manifest.json"
DEFAULT_OUTPUT_DIR = "artifacts/ui-review/latest"
SYSTEM_PROMPT = """You are reviewing UI screenshots for Abby, a safety check-in
and social-services liaison product. Be concrete and implementation-oriented.
Prioritize privacy clarity, emergency/safety comprehension, mobile ergonomics,
accessibility, text fit, and visual hierarchy. Do not invent backend behavior."""


@dataclass(frozen=True)
class ReviewTarget:
    manifest_path: Path
    screenshot_path: Path
    route_id: str
    route_path: str
    title: str
    state: str
    viewport: str
    goals: list[str]
    prompt: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest-glob",
        default=DEFAULT_MANIFEST_GLOB,
        help=f"Manifest glob relative to wallet_interface/ui. Default: {DEFAULT_MANIFEST_GLOB}",
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory relative to wallet_interface/ui. Default: {DEFAULT_OUTPUT_DIR}",
    )
    parser.add_argument("--provider", default=None, help="Optional llm_router provider name.")
    parser.add_argument("--model", default=None, help="Optional multimodal model name.")
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit reviewed screenshots. Useful for provider smoke tests. 0 means all.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate manifests and write placeholder feedback without calling the router.",
    )
    return parser.parse_args()


def resolve_ui_path(path_value: str | Path) -> Path:
    path = Path(path_value)
    return path if path.is_absolute() else UI_ROOT / path


def load_targets(manifest_glob: str, limit: int = 0) -> list[ReviewTarget]:
    manifest_paths = sorted(UI_ROOT.glob(manifest_glob))
    if not manifest_paths:
        raise FileNotFoundError(
            f"No manifests matched {manifest_glob!r}. Run `npm run test:visual` from {UI_ROOT} first."
        )

    targets: list[ReviewTarget] = []
    for manifest_path in manifest_paths:
        manifest = json.loads(manifest_path.read_text())
        screenshots = manifest.get("screenshots")
        if not isinstance(screenshots, list):
            raise ValueError(f"{manifest_path} does not contain a screenshots list")

        for item in screenshots:
            screenshot_path = resolve_ui_path(item["screenshotPath"])
            if not screenshot_path.exists():
                raise FileNotFoundError(f"Screenshot missing: {screenshot_path}")
            targets.append(
                ReviewTarget(
                    manifest_path=manifest_path,
                    screenshot_path=screenshot_path,
                    route_id=str(item["id"]),
                    route_path=str(item["path"]),
                    title=str(item["title"]),
                    state=str(item.get("state", "default")),
                    viewport=str(item["viewport"]),
                    goals=[str(goal) for goal in item.get("goals", [])],
                    prompt=str(item["multimodalPrompt"]),
                )
            )

    return targets[:limit] if limit and limit > 0 else targets


def ensure_router_importable() -> Any:
    local_package = REPO_ROOT / "ipfs_datasets_py"
    if local_package.exists():
        sys.path.insert(0, str(local_package))
    from ipfs_datasets_py import multimodal_router

    return multimodal_router


def run_review(target: ReviewTarget, *, provider: str | None, model: str | None, dry_run: bool) -> str:
    if dry_run:
        goals = "\n".join(f"- {goal}" for goal in target.goals)
        return (
            "DRY RUN: router call skipped.\n\n"
            "This target is ready for multimodal review.\n\n"
            f"Screen: {target.title}\n"
            f"Viewport: {target.viewport}\n"
            f"State: {target.state}\n"
            f"Screenshot: {target.screenshot_path.relative_to(UI_ROOT)}\n\n"
            f"Goals:\n{goals}\n"
        )

    multimodal_router = ensure_router_importable()
    return multimodal_router.generate_multimodal_text(
        target.prompt,
        provider=provider,
        model_name=model,
        image_paths=[target.screenshot_path],
        system_prompt=SYSTEM_PROMPT,
    )


def build_result_entry(target: ReviewTarget, feedback: str) -> dict[str, Any]:
    return {
        "routeId": target.route_id,
        "routePath": target.route_path,
        "title": target.title,
        "state": target.state,
        "viewport": target.viewport,
        "manifestPath": str(target.manifest_path.relative_to(UI_ROOT)),
        "screenshotPath": str(target.screenshot_path.relative_to(UI_ROOT)),
        "goals": target.goals,
        "prompt": target.prompt,
        "feedback": feedback,
    }


def write_outputs(output_dir: Path, entries: list[dict[str, Any]], *, dry_run: bool) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(timezone.utc).isoformat()
    payload = {
        "generatedAt": generated_at,
        "dryRun": dry_run,
        "entryCount": len(entries),
        "entries": entries,
    }
    (output_dir / "review-results.json").write_text(json.dumps(payload, indent=2) + "\n")

    lines = [
        "# Abby UI Multimodal Review",
        "",
        f"Generated: {generated_at}",
        f"Dry run: {dry_run}",
        f"Entries: {len(entries)}",
        "",
    ]
    for entry in entries:
        lines.extend(
            [
                f"## {entry['viewport']} · {entry['title']}",
                "",
                f"- Route: `{entry['routePath']}`",
                f"- Screenshot: `{entry['screenshotPath']}`",
                f"- State: `{entry.get('state', 'default')}`",
                "",
                "### Goals",
                "",
                *[f"- {goal}" for goal in entry["goals"]],
                "",
                "### Feedback",
                "",
                str(entry["feedback"]).strip(),
                "",
            ]
        )
    (output_dir / "review-summary.md").write_text("\n".join(lines).rstrip() + "\n")


def main() -> int:
    args = parse_args()
    output_dir = resolve_ui_path(args.output_dir)
    targets = load_targets(args.manifest_glob, limit=args.limit)
    entries: list[dict[str, Any]] = []

    for index, target in enumerate(targets, start=1):
        print(f"[{index}/{len(targets)}] Reviewing {target.viewport} {target.route_id}")
        feedback = run_review(target, provider=args.provider, model=args.model, dry_run=args.dry_run)
        entries.append(build_result_entry(target, feedback))

    write_outputs(output_dir, entries, dry_run=args.dry_run)
    print(f"Wrote {output_dir / 'review-results.json'}")
    print(f"Wrote {output_dir / 'review-summary.md'}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"review_screenshots.py: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
