from __future__ import annotations

import argparse
import json
import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger("scraper.hmis.implementation.daemon")

HMIS_TASK_PREFIX = "## HMIS-"
HMIS_STATE_PREFIX = "hmis"
DEFAULT_TODO_PATH = Path("docs/planning/HMIS_INTEGRATION_TODO.md")
DEFAULT_STATE_DIR = Path("data/hmis_implementation/state")
PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}


@dataclass(slots=True)
class HmisTodoTask:
    task_id: str
    title: str
    status: str
    priority: str
    track: str
    depends_on: tuple[str, ...]
    order: int


def parse_hmis_tasks(path: Path, *, task_prefix: str = HMIS_TASK_PREFIX) -> list[HmisTodoTask]:
    lines = path.read_text(encoding="utf-8").splitlines()
    tasks: list[HmisTodoTask] = []
    index = 0
    order = 0
    while index < len(lines):
        line = lines[index]
        if not line.startswith(task_prefix):
            index += 1
            continue
        heading = line.removeprefix("## ").strip()
        task_id, _, title = heading.partition(" ")
        metadata: dict[str, str] = {}
        index += 1
        while index < len(lines) and lines[index].startswith("- "):
            match = re.match(r"-\s+([^:]+):\s*(.*)", lines[index])
            if match:
                metadata[match.group(1).strip().lower().replace(" ", "_")] = match.group(2).strip()
            index += 1
        depends_raw = metadata.get("depends_on", "none")
        depends_on = tuple(
            item.strip()
            for item in depends_raw.split(",")
            if item.strip() and item.strip().lower() != "none"
        )
        tasks.append(
            HmisTodoTask(
                task_id=task_id,
                title=title.strip(),
                status=metadata.get("status", "todo").lower(),
                priority=metadata.get("priority", "P3"),
                track=metadata.get("track", ""),
                depends_on=depends_on,
                order=order,
            )
        )
        order += 1
    return tasks


class HmisImplementationDaemon:
    def __init__(
        self,
        *,
        todo_path: Path,
        state_path: Path,
        strategy_path: Path,
        events_path: Path,
        task_header_prefix: str = HMIS_TASK_PREFIX,
        implement: bool = False,
        **_: Any,
    ) -> None:
        self.todo_path = todo_path
        self.state_path = state_path
        self.strategy_path = strategy_path
        self.events_path = events_path
        self.task_header_prefix = task_header_prefix
        self.implement = implement

    def _select_ready_task(self, tasks: list[HmisTodoTask]) -> HmisTodoTask | None:
        completed = {task.task_id for task in tasks if task.status == "completed"}
        ready = [
            task
            for task in tasks
            if task.status in {"todo", "pending"}
            and all(dependency in completed for dependency in task.depends_on)
        ]
        ready.sort(key=lambda task: (PRIORITY_ORDER.get(task.priority, 99), task.order))
        return ready[0] if ready else None

    def run_once(self) -> dict[str, Any]:
        tasks = parse_hmis_tasks(self.todo_path, task_prefix=self.task_header_prefix)
        completed_count = sum(1 for task in tasks if task.status == "completed")
        ready_tasks = [
            task
            for task in tasks
            if task.status in {"todo", "pending"}
            and all(dependency in {row.task_id for row in tasks if row.status == "completed"} for dependency in task.depends_on)
        ]
        active_task = self._select_ready_task(tasks)
        state = {
            "active_task_id": active_task.task_id if active_task else None,
            "completed_count": completed_count,
            "ready_count": len(ready_tasks),
            "implement": self.implement,
            "updated_at": time.time(),
        }
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        if not self.strategy_path.exists():
            self.strategy_path.write_text(json.dumps({"selection": "priority_then_backlog_order"}, indent=2) + "\n", encoding="utf-8")
        with self.events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(state, sort_keys=True) + "\n")
        return state


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the HMIS implementation backlog daemon")
    parser.add_argument("--once", action="store_true", help="Run one backlog pass and exit")
    parser.add_argument("--interval", type=float, default=300.0, help="Seconds between backlog passes")
    parser.add_argument("--todo-path", type=Path, default=DEFAULT_TODO_PATH, help="Machine-readable markdown backlog")
    parser.add_argument("--state-dir", type=Path, default=DEFAULT_STATE_DIR, help="HMIS daemon state directory")
    parser.add_argument("--task-prefix", default=HMIS_TASK_PREFIX, help="Markdown heading prefix for HMIS tasks")
    parser.add_argument("--state-prefix", default=HMIS_STATE_PREFIX, help="State file prefix inside --state-dir")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    parser.add_argument("--no-implement", action="store_true", help="Only update backlog state")
    parser.add_argument("--implement", action="store_true", help="Invoke the implementation agent")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    logging.basicConfig(level=getattr(logging, args.log_level))
    implement = bool(args.implement and not args.no_implement)
    daemon = HmisImplementationDaemon(
        todo_path=args.todo_path,
        state_path=args.state_dir / f"{args.state_prefix}_task_state.json",
        strategy_path=args.state_dir / f"{args.state_prefix}_strategy.json",
        events_path=args.state_dir / f"{args.state_prefix}_events.jsonl",
        task_header_prefix=args.task_prefix,
        implement=implement,
    )
    while True:
        result = daemon.run_once()
        logger.info("HMIS implementation daemon pass complete: %s", result)
        if args.once:
            break
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
