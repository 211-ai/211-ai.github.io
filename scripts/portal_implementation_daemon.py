from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
IPFS_DATASETS_ROOT = REPO_ROOT / "ipfs_datasets_py"
for import_root in (IPFS_DATASETS_ROOT, REPO_ROOT):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))
os.environ.setdefault("IPFS_DATASETS_AUTO_INSTALL", "false")
os.environ.setdefault("IPFS_AUTO_INSTALL", "false")
os.environ.setdefault("IPFS_DATASETS_PY_MINIMAL_IMPORTS", "1")

from ipfs_datasets_py.optimizers.todo_daemon.implementation_daemon import (
    DEFAULT_IMPLEMENTATION_TIMEOUT_SECONDS,
    DEFAULT_TRACKS,
    EPHEMERAL_WORKTREE_PATHS,
    NO_CHANGE_SELECTION_PENALTY,
    PRIORITY_ORDER,
    RECENT_NO_CHANGE_COOLDOWN_SECONDS,
    SHARED_WORKTREE_PATHS,
    TASK_HEADER_PREFIX,
    TodoImplementationDaemon,
    TodoTask as PortalTask,
    TodoTaskState as PortalTaskState,
    UNRESOLVED_MERGE_SELECTION_PENALTY,
    load_json_dict,
    normalize_task_header_prefix,
    normalize_status,
    parse_timestamp,
    parse_task_file,
    process_command_line,
    process_is_running,
    split_csv,
    utc_now,
    write_json_atomic,
    write_text_atomic,
)
from scraper.utils import setup_logging

logger = logging.getLogger("scraper.portal.implementation.daemon")


class PortalImplementationDaemon(TodoImplementationDaemon):
    """211-AI compatibility wrapper around the shared todo implementation daemon."""

    def _lock_owner_is_active(self, metadata: dict[str, object], *, expected_kind: str) -> bool:
        kind = str(metadata.get("kind") or "")
        if kind and kind != expected_kind:
            return False
        try:
            pid = int(metadata.get("pid") or 0)
        except (TypeError, ValueError):
            return False
        if not process_is_running(pid):
            return False
        owner_script = str(metadata.get("owner_script") or "")
        command_line = process_command_line(pid)
        if owner_script and owner_script not in command_line:
            return False
        return True


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the portal implementation backlog daemon")
    parser.add_argument("--once", action="store_true", help="Run one backlog pass and exit")
    parser.add_argument("--interval", type=float, default=300.0, help="Seconds between backlog passes")
    parser.add_argument(
        "--todo-path",
        type=Path,
        default=Path("docs/211_SERVICE_NAVIGATION_PORTAL_TODO.md"),
        help="Machine-readable markdown backlog",
    )
    parser.add_argument(
        "--state-dir",
        type=Path,
        default=Path("data/portal_implementation/state"),
        help="Portal daemon state directory",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity",
    )
    parser.add_argument(
        "--task-prefix",
        default=TASK_HEADER_PREFIX,
        help="Markdown heading prefix for tasks, for example '## PORTAL-' or '## AGENT-'",
    )
    parser.add_argument(
        "--state-prefix",
        default="portal",
        help="State file prefix inside --state-dir",
    )
    parser.add_argument(
        "--no-implement",
        action="store_true",
        help="Only update backlog state; do not invoke the implementation agent",
    )
    parser.add_argument(
        "--implement",
        action="store_true",
        help="Invoke the configured implementation agent for the selected ready task",
    )
    parser.add_argument(
        "--implementation-command",
        default="",
        help="Command used for implementation. Defaults to codex exec --full-auto.",
    )
    parser.add_argument("--implementation-timeout", type=float, default=DEFAULT_IMPLEMENTATION_TIMEOUT_SECONDS)
    parser.add_argument(
        "--no-ephemeral-worktree",
        action="store_true",
        help="Run the implementation agent in the main checkout instead of an isolated temporary git worktree",
    )
    parser.add_argument(
        "--worktree-root",
        type=Path,
        default=None,
        help="Directory for temporary implementation worktrees",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    setup_logging(getattr(logging, args.log_level))
    implement = bool(args.implement and not args.no_implement)
    daemon = PortalImplementationDaemon(
        todo_path=args.todo_path,
        state_path=args.state_dir / f"{args.state_prefix}_task_state.json",
        strategy_path=args.state_dir / f"{args.state_prefix}_strategy.json",
        events_path=args.state_dir / f"{args.state_prefix}_events.jsonl",
        repo_root=REPO_ROOT,
        task_header_prefix=args.task_prefix,
        implement=implement,
        implementation_command=args.implementation_command or None,
        implementation_timeout=args.implementation_timeout,
        use_ephemeral_worktree=implement and not args.no_ephemeral_worktree,
        worktree_root=args.worktree_root,
    )
    while True:
        result = daemon.run_once()
        logger.info("Portal implementation daemon pass complete: %s", result)
        if args.once:
            break
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
