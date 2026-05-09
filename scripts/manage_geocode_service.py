from __future__ import annotations

import argparse
import json
import os
import shlex
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
IPFS_DATASETS_ROOT = REPO_ROOT / "ipfs_datasets_py"
for import_root in (IPFS_DATASETS_ROOT, REPO_ROOT):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))
os.environ.setdefault("IPFS_DATASETS_AUTO_INSTALL", "false")
os.environ.setdefault("IPFS_AUTO_INSTALL", "false")
os.environ.setdefault("IPFS_DATASETS_PY_MINIMAL_IMPORTS", "1")

from ipfs_datasets_py.optimizers.todo_daemon.core import iter_processes, pid_alive, process_args, read_json, read_pid_file, terminate_pid_tree
from ipfs_datasets_py.optimizers.todo_daemon.wrapper import launch_restarting_wrapper

from scripts.geocode_address_daemon import DEFAULT_BROWSER_OUTPUT_DIR, DEFAULT_CACHE_PATH, DEFAULT_PORTAL_DIR, DEFAULT_STATE_DIR, DEFAULT_STATE_PREFIX


@dataclass(frozen=True)
class GeocodeServiceSpec:
    daemon_script: Path
    state_dir: Path
    state_prefix: str
    daemon_args: tuple[str, ...]

    @property
    def wrapper_pid_path(self) -> Path:
        return self.state_dir / f"{self.state_prefix}_service_wrapper.pid"

    @property
    def wrapper_out_path(self) -> Path:
        return self.state_dir / f"{self.state_prefix}_service_wrapper.out"

    @property
    def daemon_pid_path(self) -> Path:
        return self.state_dir / f"{self.state_prefix}_daemon.pid"

    @property
    def state_path(self) -> Path:
        return self.state_dir / f"{self.state_prefix}_state.json"

    @property
    def state_dir_arg(self) -> str:
        for index, value in enumerate(self.daemon_args):
            if value == "--state-dir" and index + 1 < len(self.daemon_args):
                return self.daemon_args[index + 1]
        return str(self.state_dir)

    def command(
        self,
        *,
        log_level: str,
        batch_size_new: int,
        batch_size_retry: int,
        min_delay_seconds: float,
        timeout_seconds: float,
        max_retries: int,
        sleep_seconds: float,
        idle_sleep_seconds: float,
        refresh_browser_corpus: bool,
    ) -> tuple[str, ...]:
        command = [
            sys.executable,
            str(self.daemon_script),
            *self.daemon_args,
            "--log-level",
            log_level,
            "--batch-size-new",
            str(batch_size_new),
            "--batch-size-retry",
            str(batch_size_retry),
            "--min-delay-seconds",
            str(min_delay_seconds),
            "--timeout-seconds",
            str(timeout_seconds),
            "--max-retries",
            str(max_retries),
            "--sleep-seconds",
            str(sleep_seconds),
            "--idle-sleep-seconds",
            str(idle_sleep_seconds),
        ]
        command.append("--refresh-browser-corpus" if refresh_browser_corpus else "--no-refresh-browser-corpus")
        return tuple(command)


SERVICE = GeocodeServiceSpec(
    daemon_script=REPO_ROOT / "scripts" / "geocode_address_daemon.py",
    state_dir=DEFAULT_STATE_DIR,
    state_prefix=DEFAULT_STATE_PREFIX,
    daemon_args=(
        "--state-dir",
        "data/portal_geocoding/state",
        "--state-prefix",
        DEFAULT_STATE_PREFIX,
        "--source-dir",
        str(DEFAULT_PORTAL_DIR),
        "--cache-path",
        str(DEFAULT_CACHE_PATH),
        "--browser-output-dir",
        str(DEFAULT_BROWSER_OUTPUT_DIR),
    ),
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Manage the long-running portal geocode daemon service")
    parser.add_argument("action", choices=("status", "start", "stop", "restart"))
    parser.add_argument("--log-level", default="INFO", choices=("DEBUG", "INFO", "WARNING", "ERROR"))
    parser.add_argument("--batch-size-new", type=int, default=180)
    parser.add_argument("--batch-size-retry", type=int, default=60)
    parser.add_argument("--min-delay-seconds", type=float, default=1.1)
    parser.add_argument("--timeout-seconds", type=float, default=12.0)
    parser.add_argument("--max-retries", type=int, default=2)
    parser.add_argument("--sleep-seconds", type=float, default=30.0)
    parser.add_argument("--idle-sleep-seconds", type=float, default=600.0)
    parser.add_argument("--restart-delay", type=int, default=5)
    parser.add_argument("--startup-wait", type=float, default=2.0)
    parser.add_argument("--refresh-browser-corpus", dest="refresh_browser_corpus", action="store_true")
    parser.add_argument("--no-refresh-browser-corpus", dest="refresh_browser_corpus", action="store_false")
    parser.set_defaults(refresh_browser_corpus=True)
    return parser.parse_args(argv)


def _command_has_flag(command: str, flag: str) -> bool:
    try:
        tokens = shlex.split(command)
    except ValueError:
        tokens = command.split()
    return flag in tokens


def _process_matches(args: str, fragments: tuple[str, ...]) -> bool:
    return all(fragment and fragment in args for fragment in fragments)


def _matching_wrapper_pids(spec: GeocodeServiceSpec) -> list[int]:
    required_fragments = ("bash -lc while true; do", str(spec.daemon_script), "--state-dir", spec.state_dir_arg)
    return [candidate_pid for candidate_pid, args in iter_processes() if _process_matches(args, required_fragments)]


def _matching_daemon_pids(spec: GeocodeServiceSpec) -> list[int]:
    required_fragments = (str(spec.daemon_script), "--state-dir", spec.state_dir_arg)
    return [
        candidate_pid
        for candidate_pid, args in iter_processes()
        if "while true; do" not in args and _process_matches(args, required_fragments)
    ]


def _unique_pids(items: list[int]) -> list[int]:
    return list(dict.fromkeys(pid for pid in items if pid > 0))


def _wrapper_pid(spec: GeocodeServiceSpec) -> int | None:
    pid = read_pid_file(spec.wrapper_pid_path)
    if pid and pid_alive(pid):
        return pid
    spec.wrapper_pid_path.unlink(missing_ok=True)
    matches = _matching_wrapper_pids(spec)
    if matches:
        spec.wrapper_pid_path.write_text(f"{matches[0]}\n", encoding="utf-8")
        return matches[0]
    return None


def _daemon_pid(spec: GeocodeServiceSpec) -> int | None:
    pid = read_pid_file(spec.daemon_pid_path)
    if pid and pid_alive(pid):
        return pid
    matches = _matching_daemon_pids(spec)
    if matches:
        spec.daemon_pid_path.write_text(f"{matches[0]}\n", encoding="utf-8")
        return matches[0]
    spec.daemon_pid_path.unlink(missing_ok=True)
    return None


def service_status(spec: GeocodeServiceSpec) -> dict[str, Any]:
    wrapper_pid = _wrapper_pid(spec)
    daemon_pid = _daemon_pid(spec)
    wrapper_command = process_args(wrapper_pid) if wrapper_pid else ""
    daemon_command = process_args(daemon_pid) if daemon_pid else ""
    state = read_json(spec.state_path)
    return {
        "service": spec.state_prefix,
        "wrapper_pid": wrapper_pid,
        "wrapper_pid_alive": bool(wrapper_pid),
        "wrapper_command": wrapper_command,
        "daemon_pid": daemon_pid,
        "daemon_pid_alive": bool(daemon_pid),
        "daemon_command": daemon_command,
        "wrapper_pid_count": len(_matching_wrapper_pids(spec)),
        "daemon_pid_count": len(_matching_daemon_pids(spec)),
        "refresh_browser_corpus": _command_has_flag(wrapper_command, "--refresh-browser-corpus")
        or _command_has_flag(daemon_command, "--refresh-browser-corpus"),
        "state": state,
    }


def _status_matches_requested_mode(status: dict[str, Any], *, refresh_browser_corpus: bool) -> bool:
    wrapper_command = str(status.get("wrapper_command") or "")
    daemon_command = str(status.get("daemon_command") or "")
    if refresh_browser_corpus:
        return _command_has_flag(wrapper_command, "--refresh-browser-corpus") and _command_has_flag(daemon_command, "--refresh-browser-corpus")
    return _command_has_flag(wrapper_command, "--no-refresh-browser-corpus") and _command_has_flag(daemon_command, "--no-refresh-browser-corpus")


def _stop_pid(kind: str, pid: int) -> dict[str, Any]:
    was_alive = pid_alive(pid)
    terminated = terminate_pid_tree(pid, grace_seconds=10.0) if was_alive else False
    return {
        "kind": kind,
        "pid": pid,
        "was_alive": was_alive,
        "terminated": terminated,
        "stopped": not pid_alive(pid),
    }


def stop_service(spec: GeocodeServiceSpec, *, restart_wait_seconds: float = 0.0, poll_seconds: float = 0.5) -> dict[str, Any]:
    stopped: list[dict[str, Any]] = []
    deadline = time.monotonic() + max(0.0, float(restart_wait_seconds))
    while True:
        found = False
        for kind, pids in (
            ("wrapper", [pid for pid in [read_pid_file(spec.wrapper_pid_path)] if pid] + _matching_wrapper_pids(spec)),
            ("daemon", [pid for pid in [read_pid_file(spec.daemon_pid_path)] if pid] + _matching_daemon_pids(spec)),
        ):
            unique = _unique_pids(pids)
            found = found or bool(unique)
            for pid in unique:
                stopped.append(_stop_pid(kind, pid))
        spec.wrapper_pid_path.unlink(missing_ok=True)
        spec.daemon_pid_path.unlink(missing_ok=True)
        if time.monotonic() >= deadline or not found:
            break
        sleep_for = min(max(0.05, float(poll_seconds)), max(0.0, deadline - time.monotonic()))
        if sleep_for <= 0:
            break
        time.sleep(sleep_for)
    return {"service": spec.state_prefix, "action": "stop", "stopped": stopped, "status": service_status(spec)}


def start_service(
    spec: GeocodeServiceSpec,
    *,
    log_level: str,
    batch_size_new: int,
    batch_size_retry: int,
    min_delay_seconds: float,
    timeout_seconds: float,
    max_retries: int,
    sleep_seconds: float,
    idle_sleep_seconds: float,
    restart_delay: int,
    startup_wait: float,
    refresh_browser_corpus: bool,
) -> dict[str, Any]:
    spec.state_dir.mkdir(parents=True, exist_ok=True)
    status = service_status(spec)
    if status["wrapper_pid_alive"] and _status_matches_requested_mode(status, refresh_browser_corpus=refresh_browser_corpus):
        return {"service": spec.state_prefix, "action": "start", "result": "already_running", "status": status}
    if status["wrapper_pid_alive"] or status["daemon_pid_alive"]:
        stop_service(spec, restart_wait_seconds=max(0.0, float(restart_delay) + 1.0))
    for stale_path in (spec.wrapper_pid_path, spec.daemon_pid_path):
        stale_path.unlink(missing_ok=True)
    launch = launch_restarting_wrapper(
        repo_root=REPO_ROOT,
        command=spec.command(
            log_level=log_level,
            batch_size_new=batch_size_new,
            batch_size_retry=batch_size_retry,
            min_delay_seconds=min_delay_seconds,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            sleep_seconds=sleep_seconds,
            idle_sleep_seconds=idle_sleep_seconds,
            refresh_browser_corpus=refresh_browser_corpus,
        ),
        out_path=spec.wrapper_out_path,
        pid_path=spec.wrapper_pid_path,
        launch_mode="nohup_loop",
        restart_delay_seconds=restart_delay,
        restart_message="portal geocode daemon exited with code",
    )
    deadline = time.monotonic() + max(0.0, startup_wait)
    while time.monotonic() < deadline:
        current = service_status(spec)
        if current["wrapper_pid_alive"] or current["daemon_pid_alive"]:
            break
        time.sleep(0.2)
    return {
        "service": spec.state_prefix,
        "action": "start",
        "result": "started",
        "launcher_mode": launch.mode,
        "launcher_pid": launch.pid,
        "status": service_status(spec),
    }


def restart_service(spec: GeocodeServiceSpec, **kwargs: Any) -> dict[str, Any]:
    restart_delay = int(kwargs["restart_delay"])
    return {
        "service": spec.state_prefix,
        "action": "restart",
        "stop": stop_service(spec, restart_wait_seconds=max(0.0, float(restart_delay) + 1.0)),
        "start": start_service(spec, **kwargs),
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.action == "status":
        payload = service_status(SERVICE)
    elif args.action == "start":
        payload = start_service(
            SERVICE,
            log_level=args.log_level,
            batch_size_new=args.batch_size_new,
            batch_size_retry=args.batch_size_retry,
            min_delay_seconds=args.min_delay_seconds,
            timeout_seconds=args.timeout_seconds,
            max_retries=args.max_retries,
            sleep_seconds=args.sleep_seconds,
            idle_sleep_seconds=args.idle_sleep_seconds,
            restart_delay=args.restart_delay,
            startup_wait=args.startup_wait,
            refresh_browser_corpus=args.refresh_browser_corpus,
        )
    elif args.action == "stop":
        payload = stop_service(SERVICE)
    else:
        payload = restart_service(
            SERVICE,
            log_level=args.log_level,
            batch_size_new=args.batch_size_new,
            batch_size_retry=args.batch_size_retry,
            min_delay_seconds=args.min_delay_seconds,
            timeout_seconds=args.timeout_seconds,
            max_retries=args.max_retries,
            sleep_seconds=args.sleep_seconds,
            idle_sleep_seconds=args.idle_sleep_seconds,
            restart_delay=args.restart_delay,
            startup_wait=args.startup_wait,
            refresh_browser_corpus=args.refresh_browser_corpus,
        )
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
