#!/usr/bin/env python3
"""Generate per-task implementation prompts from the Abby UI refinement backlog."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


UI_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BACKLOG = "artifacts/ui-review/latest/refinement-backlog.json"
DEFAULT_OUTPUT_DIR = "artifacts/ui-review/latest/agent-prompts"

LIKELY_FILES = [
    "src/app/App.tsx",
    "src/styles/global.css",
    "src/components/ui.tsx",
    "src/services/mockAbbyService.ts",
    "tests/smoke.spec.ts",
    "tests/visual-capture.spec.ts",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--backlog",
        default=DEFAULT_BACKLOG,
        help=f"Backlog JSON relative to wallet_interface/ui. Default: {DEFAULT_BACKLOG}",
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory relative to wallet_interface/ui. Default: {DEFAULT_OUTPUT_DIR}",
    )
    parser.add_argument(
        "--include-blocked",
        action="store_true",
        help="Also generate prompts for blocked review-needed tasks.",
    )
    return parser.parse_args()


def resolve_ui_path(path_value: str | Path) -> Path:
    path = Path(path_value)
    return path if path.is_absolute() else UI_ROOT / path


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def task_should_generate(task: dict[str, Any], include_blocked: bool) -> bool:
    if include_blocked:
        return True
    return str(task.get("status")) != "blocked"


def count_by(tasks: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for task in tasks:
        value = str(task.get(key, "unknown"))
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def validate_task(task: dict[str, Any]) -> None:
    required_fields = [
        "task_id",
        "title",
        "priority",
        "category",
        "suggested_agent",
        "status",
        "route_path",
        "viewport",
        "state",
        "screenshot_path",
        "source_feedback",
    ]
    missing_fields = [field for field in required_fields if field not in task]
    if missing_fields:
        raise ValueError(f"{task.get('task_id', '<unknown>')} is missing fields: {', '.join(missing_fields)}")

    screenshot_path = resolve_ui_path(str(task["screenshot_path"]))
    if not screenshot_path.exists():
        raise FileNotFoundError(f"{task['task_id']} screenshot missing: {screenshot_path}")


def build_prompt(task: dict[str, Any]) -> str:
    criteria = "\n".join(f"- {criterion}" for criterion in task.get("acceptance_criteria", []))
    likely_files = "\n".join(f"- `{path}`" for path in LIKELY_FILES)
    return f"""# {task["task_id"]}: {task["title"]}

You are an implementation agent working in `wallet_interface/ui`.

## Task

- Priority: `{task["priority"]}`
- Category: `{task["category"]}`
- Suggested agent: `{task["suggested_agent"]}`
- Status: `{task["status"]}`
- Route: `{task["route_path"]}`
- Viewport: `{task["viewport"]}`
- State: `{task["state"]}`
- Screenshot: `{task["screenshot_path"]}`

## Source Feedback

{task["source_feedback"]}

## Acceptance Criteria

{criteria}

## Likely Files

{likely_files}

## Instructions

1. Inspect the screenshot and the route implementation before changing code.
2. Make the smallest UI/UX change that satisfies the task.
3. Preserve mobile and desktop behavior for the affected route.
4. Do not imply sensitive data is shared without explicit user action.
5. After patching, run:

```bash
npm run build
npm run test:smoke
npm run test:visual
```

6. Regenerate review artifacts when the visual state changes:

```bash
npm run review:visual:dry-run
npm run review:tasks
npm run review:prompts -- --include-blocked
```
"""


def write_outputs(output_dir: Path, backlog: dict[str, Any], tasks: list[dict[str, Any]]) -> None:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(timezone.utc).isoformat()
    index_lines = [
        "# Abby UI Agent Prompts",
        "",
        f"Generated: {generated_at}",
        f"Source: `{backlog.get('sourceReviewResults', DEFAULT_BACKLOG)}`",
        f"Prompts: {len(tasks)}",
        "",
        "## Summary",
        "",
        "By status:",
        *[f"- `{status}`: {count}" for status, count in count_by(tasks, "status").items()],
        "",
        "By priority:",
        *[f"- `{priority}`: {count}" for priority, count in count_by(tasks, "priority").items()],
        "",
        "By viewport:",
        *[f"- `{viewport}`: {count}" for viewport, count in count_by(tasks, "viewport").items()],
        "",
        "## Prompts",
        "",
    ]

    for task in tasks:
        validate_task(task)
        filename = f"{slugify(task['task_id'])}.md"
        prompt_path = output_dir / filename
        prompt_path.write_text(build_prompt(task))
        index_lines.append(f"- [{task['task_id']}]({filename}) `{task['status']}` `{task['priority']}` {task['title']}")

    (output_dir / "index.md").write_text("\n".join(index_lines).rstrip() + "\n")


def main() -> int:
    args = parse_args()
    backlog_path = resolve_ui_path(args.backlog)
    output_dir = resolve_ui_path(args.output_dir)
    backlog = json.loads(backlog_path.read_text())
    tasks = [
        task
        for task in backlog.get("tasks", [])
        if task_should_generate(task, include_blocked=args.include_blocked)
    ]
    write_outputs(output_dir, backlog, tasks)
    print(f"Wrote {output_dir / 'index.md'}")
    print(f"Generated {len(tasks)} prompt files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
