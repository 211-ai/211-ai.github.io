from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.hmis_implementation_daemon import (
    DEFAULT_STATE_DIR,
    DEFAULT_TODO_PATH,
    HMIS_STATE_PREFIX,
    HMIS_TASK_PREFIX,
    HmisImplementationDaemon,
)

logger = logging.getLogger("scraper.hmis.implementation.supervisor")


@dataclass(slots=True)
class HmisSupervisorConfig:
    todo_path: Path
    state_dir: Path
    task_prefix: str = HMIS_TASK_PREFIX
    state_prefix: str = HMIS_STATE_PREFIX
    implement: bool = True


class HmisImplementationSupervisor:
    def __init__(self, config: HmisSupervisorConfig) -> None:
        self.config = config

    def build_supervisor_loop_config(self) -> dict[str, Any]:
        return {
            "task_board_path": self.config.todo_path,
            "child_pid_path": self.config.state_dir / f"{self.config.state_prefix}_managed_daemon.pid",
            "command": [
                "python",
                str(Path(__file__).resolve().parent / "hmis_implementation_daemon.py"),
            ],
        }

    def run_once(self) -> dict[str, Any]:
        daemon = HmisImplementationDaemon(
            todo_path=self.config.todo_path,
            state_path=self.config.state_dir / f"{self.config.state_prefix}_task_state.json",
            strategy_path=self.config.state_dir / f"{self.config.state_prefix}_strategy.json",
            events_path=self.config.state_dir / f"{self.config.state_prefix}_supervisor_events.jsonl",
            task_header_prefix=self.config.task_prefix,
            implement=self.config.implement,
        )
        result = daemon.run_once()
        status_path = self.config.state_dir / f"{self.config.state_prefix}_supervisor_status.json"
        status_path.parent.mkdir(parents=True, exist_ok=True)
        status_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Supervise the HMIS implementation backlog daemon")
    parser.add_argument("--once", action="store_true", help="Run one supervisor check and exit")
    parser.add_argument("--todo-path", type=Path, default=DEFAULT_TODO_PATH, help="Machine-readable markdown backlog")
    parser.add_argument("--state-dir", type=Path, default=DEFAULT_STATE_DIR, help="HMIS daemon state directory")
    parser.add_argument("--task-prefix", default=HMIS_TASK_PREFIX, help="Markdown heading prefix for HMIS tasks")
    parser.add_argument("--state-prefix", default=HMIS_STATE_PREFIX, help="State file prefix inside --state-dir")
    parser.add_argument("--implement", dest="implement", action="store_true", help="Allow implementation")
    parser.add_argument("--no-implement", dest="implement", action="store_false", help="Disable implementation")
    parser.set_defaults(implement=True)
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    return parser.parse_args(argv)


def build_supervisor(args: argparse.Namespace) -> HmisImplementationSupervisor:
    return HmisImplementationSupervisor(
        HmisSupervisorConfig(
            todo_path=args.todo_path,
            state_dir=args.state_dir,
            task_prefix=args.task_prefix,
            state_prefix=args.state_prefix,
            implement=args.implement,
        )
    )


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    logging.basicConfig(level=getattr(logging, args.log_level))
    supervisor = build_supervisor(args)
    result = supervisor.run_once()
    logger.info("HMIS implementation supervisor check complete: %s", result)


if __name__ == "__main__":
    main()
