#!/usr/bin/env python3
"""Generate an agent-ready UI refinement backlog from multimodal review output."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


UI_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REVIEW_RESULTS = "artifacts/ui-review/latest/review-results.json"
DEFAULT_OUTPUT_DIR = "artifacts/ui-review/latest"

SECTION_ALIASES = {
    "critical issues": ("critical", "P0", "ui-agent"),
    "critical issue": ("critical", "P0", "ui-agent"),
    "ui/ux improvements": ("ui_ux", "P2", "ui-agent"),
    "ux improvements": ("ui_ux", "P2", "ui-agent"),
    "ui improvements": ("ui_ux", "P2", "ui-agent"),
    "accessibility concerns": ("accessibility", "P1", "accessibility-agent"),
    "accessibility concern": ("accessibility", "P1", "accessibility-agent"),
    "suggested implementation changes": ("implementation", "P2", "implementation-agent"),
    "implementation changes": ("implementation", "P2", "implementation-agent"),
}


@dataclass(frozen=True)
class BacklogTask:
    task_id: str
    priority: str
    category: str
    suggested_agent: str
    title: str
    route_id: str
    route_path: str
    viewport: str
    state: str
    screenshot_path: str
    source_feedback: str
    acceptance_criteria: list[str]
    status: str = "ready"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--review-results",
        default=DEFAULT_REVIEW_RESULTS,
        help=f"Review results JSON relative to wallet_interface/ui. Default: {DEFAULT_REVIEW_RESULTS}",
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory relative to wallet_interface/ui. Default: {DEFAULT_OUTPUT_DIR}",
    )
    return parser.parse_args()


def resolve_ui_path(path_value: str | Path) -> Path:
    path = Path(path_value)
    return path if path.is_absolute() else UI_ROOT / path


def normalize_heading(line: str) -> str:
    line = re.sub(r"^[#*\-\s]+", "", line.strip())
    line = re.sub(r"[:*#\s]+$", "", line)
    return line.lower()


def clean_bullet(line: str) -> str:
    return re.sub(r"^\s*(?:[-*]|\d+[.)])\s*", "", line).strip()


def extract_section_tasks(feedback: str) -> list[tuple[str, str, str, str]]:
    """Return tuples of category, priority, suggested_agent, finding."""

    current: tuple[str, str, str] | None = None
    extracted: list[tuple[str, str, str, str]] = []

    for raw_line in feedback.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        heading = normalize_heading(line)
        if heading in SECTION_ALIASES:
            current = SECTION_ALIASES[heading]
            continue

        is_bullet = bool(re.match(r"^\s*(?:[-*]|\d+[.)])\s+", raw_line))
        if current and is_bullet:
            finding = clean_bullet(raw_line)
            if finding and not finding.lower().startswith("none"):
                extracted.append((*current, finding))

    return extracted


def fallback_tasks_for_entry(entry: dict[str, Any], dry_run: bool) -> list[tuple[str, str, str, str, str]]:
    if dry_run:
        return [
            (
                "review_needed",
                "P3",
                "review-agent",
                f"Run multimodal review for {entry['viewport']} {entry.get('state', 'default')} {entry['title']}",
                "blocked",
            )
        ]
    return [
        (
            "triage",
            "P2",
            "review-agent",
            f"Triage unstructured feedback for {entry['viewport']} {entry.get('state', 'default')} {entry['title']}",
            "ready",
        )
    ]


def make_task_id(viewport: str, route_id: str, index: int) -> str:
    viewport_slug = re.sub(r"[^a-z0-9]+", "-", viewport.lower()).strip("-")
    route_slug = re.sub(r"[^a-z0-9]+", "-", route_id.lower()).strip("-")
    return f"ABBY-UI-{viewport_slug}-{route_slug}-{index:03d}".upper()


def build_acceptance_criteria(entry: dict[str, Any], category: str) -> list[str]:
    criteria = [
        f"Updated `{entry['routePath']}` remains usable in `{entry['viewport']}`.",
        f"The `{entry.get('state', 'default')}` UI state is preserved or improved.",
        f"Changes are checked against `{entry['screenshotPath']}` and a regenerated screenshot.",
        "No sensitive data is implied to be shared without explicit user action.",
    ]
    if category == "accessibility":
        criteria.append("Keyboard focus, visible labels, touch targets, and color contrast are preserved or improved.")
    if category == "critical":
        criteria.append("The issue no longer blocks the primary user action on the affected screen.")
    return criteria


def build_tasks(payload: dict[str, Any]) -> list[BacklogTask]:
    tasks: list[BacklogTask] = []
    dry_run = bool(payload.get("dryRun"))

    for entry in payload.get("entries", []):
        feedback = str(entry.get("feedback", "")).strip()
        parsed = [
            (*item, "ready")
            for item in extract_section_tasks(feedback)
        ]
        if not parsed:
            parsed = fallback_tasks_for_entry(entry, dry_run=dry_run)

        for index, item in enumerate(parsed, start=1):
            category, priority, suggested_agent, finding, status = item
            tasks.append(
                BacklogTask(
                    task_id=make_task_id(str(entry["viewport"]), str(entry["routeId"]), index),
                    priority=priority,
                    category=category,
                    suggested_agent=suggested_agent,
                    title=f"{entry['title']}: {finding}",
                    route_id=str(entry["routeId"]),
                    route_path=str(entry["routePath"]),
                    viewport=str(entry["viewport"]),
                    state=str(entry.get("state", "default")),
                    screenshot_path=str(entry["screenshotPath"]),
                    source_feedback=finding,
                    acceptance_criteria=build_acceptance_criteria(entry, category),
                    status=status,
                )
            )

    return tasks


def count_tasks(tasks: list[BacklogTask], field_name: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for task in tasks:
        value = str(getattr(task, field_name))
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def write_outputs(output_dir: Path, tasks: list[BacklogTask], source_path: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(timezone.utc).isoformat()
    payload = {
        "generatedAt": generated_at,
        "sourceReviewResults": str(source_path.relative_to(UI_ROOT)),
        "taskCount": len(tasks),
        "tasks": [task.__dict__ for task in tasks],
    }
    (output_dir / "refinement-backlog.json").write_text(json.dumps(payload, indent=2) + "\n")

    lines = [
        "# Abby UI Refinement Backlog",
        "",
        f"Generated: {generated_at}",
        f"Source: `{source_path.relative_to(UI_ROOT)}`",
        f"Tasks: {len(tasks)}",
        "",
        "## Summary",
        "",
        "By status:",
        *[f"- `{status}`: {count}" for status, count in count_tasks(tasks, "status").items()],
        "",
        "By priority:",
        *[f"- `{priority}`: {count}" for priority, count in count_tasks(tasks, "priority").items()],
        "",
        "By viewport:",
        *[f"- `{viewport}`: {count}" for viewport, count in count_tasks(tasks, "viewport").items()],
        "",
        "## Tasks",
        "",
    ]
    for task in tasks:
        lines.extend(
            [
                f"## {task.task_id}: {task.title}",
                "",
                f"- Priority: `{task.priority}`",
                f"- Status: `{task.status}`",
                f"- Category: `{task.category}`",
                f"- Suggested agent: `{task.suggested_agent}`",
                f"- Route: `{task.route_path}`",
                f"- Viewport: `{task.viewport}`",
                f"- State: `{task.state}`",
                f"- Screenshot: `{task.screenshot_path}`",
                "",
                "### Acceptance Criteria",
                "",
                *[f"- {criterion}" for criterion in task.acceptance_criteria],
                "",
            ]
        )
    (output_dir / "refinement-backlog.md").write_text("\n".join(lines).rstrip() + "\n")


def main() -> int:
    args = parse_args()
    source_path = resolve_ui_path(args.review_results)
    output_dir = resolve_ui_path(args.output_dir)
    payload = json.loads(source_path.read_text())
    tasks = build_tasks(payload)
    write_outputs(output_dir, tasks, source_path)
    print(f"Wrote {output_dir / 'refinement-backlog.json'}")
    print(f"Wrote {output_dir / 'refinement-backlog.md'}")
    print(f"Generated {len(tasks)} tasks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
