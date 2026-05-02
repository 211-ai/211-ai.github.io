"""
Supervisor for the agentic 211info ETL daemon.

The supervisor monitors daemon heartbeat/progress and rewrites the daemon's
strategy file when it detects stagnation. It deliberately avoids mutating Python
source at runtime; strategy rewrites are auditable, reversible, and testable.
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .agentic_daemon import CrawlState, utc_now
from .utils import setup_logging

logger = logging.getLogger("scraper.supervisor")


@dataclass
class SupervisorConfig:
    state_path: Path
    strategy_path: Path
    events_path: Path
    stale_seconds: float = 600.0
    check_interval: float = 30.0
    max_restarts: int = 10
    daemon_max_pages: int = 25
    daemon_interval: float = 300.0
    output_dir: Path = Path("data")
    state_dir: Path = Path("data/state")


class SelfHealingSupervisor:
    """Monitor, restart, and strategy-rewrite loop for the daemon."""

    def __init__(self, config: SupervisorConfig) -> None:
        self.config = config
        self.restart_count = 0

    def is_stuck(self, state: CrawlState, *, now_ts: float | None = None) -> tuple[bool, str]:
        now_ts = now_ts if now_ts is not None else time.time()
        heartbeat_age = self._age_seconds(state.heartbeat_at, now_ts)
        progress_age = self._age_seconds(state.last_progress_at, now_ts)
        stale = self.config.stale_seconds

        if state.active_url and heartbeat_age > stale:
            return True, f"heartbeat stale for active URL {state.active_url}"
        if state.queue and progress_age > stale and state.processed_pages > 0:
            return True, "queued work exists but no recent progress"
        return False, ""

    def rewrite_strategy(self, state: CrawlState, reason: str) -> dict[str, Any]:
        strategy = self._load_strategy()
        generation = int(strategy.get("generation", 0)) + 1
        blocked_urls = list(dict.fromkeys([*strategy.get("blocked_urls", []), state.active_url]))
        blocked_urls = [url for url in blocked_urls if url]
        current_delay = float(strategy.get("request_delay", 1.5))

        strategy.update(
            {
                "generation": generation,
                "request_delay": min(max(current_delay * 1.5, 1.5), 30.0),
                "max_depth": max(1, int(strategy.get("max_depth", 3)) - 1),
                "blocked_urls": blocked_urls,
                "last_rewrite_at": utc_now(),
                "last_rewrite_reason": reason,
            }
        )
        self.config.strategy_path.parent.mkdir(parents=True, exist_ok=True)
        self.config.strategy_path.write_text(
            json.dumps(strategy, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        self._record_event("strategy_rewrite", {"reason": reason, "generation": generation})
        return strategy

    def run_forever(self) -> None:
        process: subprocess.Popen[str] | None = None
        try:
            while self.restart_count <= self.config.max_restarts:
                if process is None or process.poll() is not None:
                    process = self._start_daemon()
                    self.restart_count += 1
                    self._record_event("daemon_start", {"restart_count": self.restart_count})

                state = CrawlState.load(self.config.state_path)
                stuck, reason = self.is_stuck(state)
                if stuck:
                    self.rewrite_strategy(state, reason)
                    self._terminate(process)
                    process = None

                time.sleep(self.config.check_interval)
        finally:
            if process is not None:
                self._terminate(process)

    def _start_daemon(self) -> subprocess.Popen[str]:
        command = [
            sys.executable,
            "-m",
            "scraper.agentic_daemon",
            "--interval",
            str(self.config.daemon_interval),
            "--max-pages",
            str(self.config.daemon_max_pages),
            "--output-dir",
            str(self.config.output_dir),
            "--state-dir",
            str(self.config.state_dir),
        ]
        return subprocess.Popen(command, text=True)

    def _terminate(self, process: subprocess.Popen[str]) -> None:
        if process.poll() is not None:
            return
        process.terminate()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=15)
        self._record_event("daemon_stop", {"returncode": process.returncode})

    def _load_strategy(self) -> dict[str, Any]:
        if not self.config.strategy_path.exists():
            return {}
        return json.loads(self.config.strategy_path.read_text(encoding="utf-8"))

    def _record_event(self, event_type: str, payload: dict[str, Any]) -> None:
        self.config.events_path.parent.mkdir(parents=True, exist_ok=True)
        event = {
            "type": event_type,
            "timestamp": utc_now(),
            **payload,
        }
        with self.config.events_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=False) + "\n")

    @staticmethod
    def _age_seconds(timestamp: str, now_ts: float) -> float:
        if not timestamp:
            return float("inf")
        try:
            parsed = datetime.fromisoformat(timestamp)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return max(0.0, now_ts - parsed.timestamp())
        except ValueError:
            return float("inf")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Supervise and self-heal the 211info agentic daemon")
    parser.add_argument("--output-dir", type=Path, default=Path("data"))
    parser.add_argument("--state-dir", type=Path, default=Path("data/state"))
    parser.add_argument("--stale-seconds", type=float, default=600.0)
    parser.add_argument("--check-interval", type=float, default=30.0)
    parser.add_argument("--max-restarts", type=int, default=10)
    parser.add_argument("--daemon-max-pages", type=int, default=25)
    parser.add_argument("--daemon-interval", type=float, default=300.0)
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    setup_logging(getattr(logging, args.log_level))
    cfg = SupervisorConfig(
        state_path=args.state_dir / "agentic_daemon_state.json",
        strategy_path=args.state_dir / "daemon_strategy.json",
        events_path=args.state_dir / "supervisor_events.jsonl",
        stale_seconds=args.stale_seconds,
        check_interval=args.check_interval,
        max_restarts=args.max_restarts,
        daemon_max_pages=args.daemon_max_pages,
        daemon_interval=args.daemon_interval,
        output_dir=args.output_dir,
        state_dir=args.state_dir,
    )
    SelfHealingSupervisor(cfg).run_forever()


if __name__ == "__main__":
    main()
