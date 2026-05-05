from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scraper.utils import setup_logging
from scripts.agent_chat_implementation_daemon import AGENT_STATE_PREFIX, AGENT_TASK_PREFIX, DEFAULT_STATE_DIR, DEFAULT_TODO_PATH
from scripts.portal_implementation_supervisor import PortalImplementationSupervisor, PortalSupervisorConfig

logger = logging.getLogger("scraper.agent_chat.implementation.supervisor")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Supervise the AI agent chat implementation backlog daemon")
    parser.add_argument("--once", action="store_true", help="Run one supervisor check and exit")
    parser.add_argument(
        "--todo-path",
        type=Path,
        default=DEFAULT_TODO_PATH,
        help="Machine-readable markdown backlog",
    )
    parser.add_argument(
        "--state-dir",
        type=Path,
        default=DEFAULT_STATE_DIR,
        help="Agent chat daemon state directory",
    )
    parser.add_argument("--stale-seconds", type=float, default=1800.0)
    parser.add_argument("--check-interval", type=float, default=60.0)
    parser.add_argument("--max-restarts", type=int, default=10)
    parser.add_argument("--daemon-interval", type=float, default=300.0)
    parser.add_argument(
        "--no-implement",
        action="store_true",
        help="Only supervise backlog state; do not invoke the implementation agent",
    )
    parser.add_argument(
        "--implementation-command",
        default="",
        help="Command used for implementation. Defaults to codex exec --full-auto.",
    )
    parser.add_argument("--implementation-timeout", type=float, default=1800.0)
    parser.add_argument(
        "--no-ephemeral-worktree",
        action="store_true",
        help="Run implementation commands in the main checkout instead of isolated temporary git worktrees",
    )
    parser.add_argument(
        "--worktree-root",
        type=Path,
        default=None,
        help="Directory for temporary implementation worktrees",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity",
    )
    return parser.parse_args(argv)


def build_supervisor(args: argparse.Namespace) -> PortalImplementationSupervisor:
    return PortalImplementationSupervisor(
        PortalSupervisorConfig(
            todo_path=args.todo_path,
            state_path=args.state_dir / f"{AGENT_STATE_PREFIX}_task_state.json",
            strategy_path=args.state_dir / f"{AGENT_STATE_PREFIX}_strategy.json",
            events_path=args.state_dir / f"{AGENT_STATE_PREFIX}_supervisor_events.jsonl",
            state_dir=args.state_dir,
            stale_seconds=args.stale_seconds,
            check_interval=args.check_interval,
            max_restarts=args.max_restarts,
            daemon_interval=args.daemon_interval,
            task_prefix=AGENT_TASK_PREFIX,
            state_prefix=AGENT_STATE_PREFIX,
            implement=not args.no_implement,
            implementation_command=args.implementation_command,
            implementation_timeout=args.implementation_timeout,
            use_ephemeral_worktree=not args.no_ephemeral_worktree,
            worktree_root=args.worktree_root,
        )
    )


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    setup_logging(getattr(logging, args.log_level))
    supervisor = build_supervisor(args)
    if args.once:
        result = supervisor.run_once()
        logger.info("Agent chat implementation supervisor check complete: %s", result)
        return
    supervisor.run_forever()


if __name__ == "__main__":
    main()
