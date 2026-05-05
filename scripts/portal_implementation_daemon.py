from __future__ import annotations

import argparse
import json
import logging
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scraper.utils import setup_logging

logger = logging.getLogger("scraper.portal.implementation.daemon")

TASK_HEADER_PREFIX = "## PORTAL-"
DEFAULT_TRACKS = ["platform", "data", "ui", "mobile", "wallet", "collab", "pwa", "ops"]
PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
DEFAULT_IMPLEMENTATION_TIMEOUT_SECONDS = 1800.0


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def split_csv(value: str) -> list[str]:
    raw = [item.strip() for item in value.split(",")]
    return [item for item in raw if item and item.lower() not in {"none", "n/a"}]


def normalize_status(value: str) -> str:
    lowered = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    if lowered in {"done", "complete", "completed"}:
        return "completed"
    if lowered in {"blocked", "on_hold"}:
        return "blocked"
    if lowered in {"active", "in_progress"}:
        return "in_progress"
    if lowered in {"ready", "todo", "queued", ""}:
        return "todo"
    return lowered


def normalize_task_header_prefix(value: str) -> str:
    stripped = value.strip()
    if stripped.startswith("## "):
        return stripped
    return f"## {stripped}"


@dataclass(frozen=True)
class PortalTask:
    task_id: str
    title: str
    status: str
    completion: str
    priority: str
    track: str
    depends_on: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    validation: list[str] = field(default_factory=list)
    acceptance: str = ""
    source_line: int = 0


@dataclass
class PortalTaskState:
    heartbeat_at: str = ""
    last_progress_at: str = ""
    active_task_id: str = ""
    active_task_title: str = ""
    active_task_track: str = ""
    active_task_started_at: str = ""
    recommended_task_id: str = ""
    recommended_actions: list[str] = field(default_factory=list)
    completed_task_ids: list[str] = field(default_factory=list)
    ready_task_ids: list[str] = field(default_factory=list)
    waiting_task_ids: list[str] = field(default_factory=list)
    blocked_task_ids: list[str] = field(default_factory=list)
    task_statuses: dict[str, str] = field(default_factory=dict)
    task_artifacts: dict[str, list[str]] = field(default_factory=dict)
    task_validation: dict[str, list[str]] = field(default_factory=dict)
    implementation_attempts: dict[str, int] = field(default_factory=dict)
    last_implementation_task_id: str = ""
    last_implementation_started_at: str = ""
    last_implementation_finished_at: str = ""
    last_implementation_returncode: int | None = None
    last_implementation_log_path: str = ""
    completed_count: int = 0
    ready_count: int = 0
    waiting_count: int = 0
    blocked_count: int = 0
    task_count: int = 0
    strategy_generation: int = 0

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2, sort_keys=True), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "PortalTaskState":
        if not path.exists():
            return cls()
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            return cls()
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return cls()
        if not isinstance(payload, dict):
            return cls()
        return cls(
            heartbeat_at=str(payload.get("heartbeat_at") or ""),
            last_progress_at=str(payload.get("last_progress_at") or ""),
            active_task_id=str(payload.get("active_task_id") or ""),
            active_task_title=str(payload.get("active_task_title") or ""),
            active_task_track=str(payload.get("active_task_track") or ""),
            active_task_started_at=str(payload.get("active_task_started_at") or ""),
            recommended_task_id=str(payload.get("recommended_task_id") or ""),
            recommended_actions=[str(item) for item in payload.get("recommended_actions", []) or []],
            completed_task_ids=[str(item) for item in payload.get("completed_task_ids", []) or []],
            ready_task_ids=[str(item) for item in payload.get("ready_task_ids", []) or []],
            waiting_task_ids=[str(item) for item in payload.get("waiting_task_ids", []) or []],
            blocked_task_ids=[str(item) for item in payload.get("blocked_task_ids", []) or []],
            task_statuses={str(key): str(value) for key, value in (payload.get("task_statuses") or {}).items()},
            task_artifacts={
                str(key): [str(item) for item in value]
                for key, value in (payload.get("task_artifacts") or {}).items()
                if isinstance(value, list)
            },
            task_validation={
                str(key): [str(item) for item in value]
                for key, value in (payload.get("task_validation") or {}).items()
                if isinstance(value, list)
            },
            implementation_attempts={
                str(key): int(value)
                for key, value in (payload.get("implementation_attempts") or {}).items()
                if str(value).isdigit()
            },
            last_implementation_task_id=str(payload.get("last_implementation_task_id") or ""),
            last_implementation_started_at=str(payload.get("last_implementation_started_at") or ""),
            last_implementation_finished_at=str(payload.get("last_implementation_finished_at") or ""),
            last_implementation_returncode=(
                int(payload["last_implementation_returncode"])
                if payload.get("last_implementation_returncode") is not None
                else None
            ),
            last_implementation_log_path=str(payload.get("last_implementation_log_path") or ""),
            completed_count=int(payload.get("completed_count") or 0),
            ready_count=int(payload.get("ready_count") or 0),
            waiting_count=int(payload.get("waiting_count") or 0),
            blocked_count=int(payload.get("blocked_count") or 0),
            task_count=int(payload.get("task_count") or 0),
            strategy_generation=int(payload.get("strategy_generation") or 0),
        )


def parse_task_file(path: Path, task_header_prefix: str = TASK_HEADER_PREFIX) -> list[PortalTask]:
    task_header_prefix = normalize_task_header_prefix(task_header_prefix)
    lines = path.read_text(encoding="utf-8").splitlines()
    tasks: list[PortalTask] = []
    current_id = ""
    current_title = ""
    current_line = 0
    block: list[str] = []

    def flush() -> None:
        nonlocal block, current_id, current_title, current_line
        if not current_id:
            return
        metadata: dict[str, str] = {}
        for line in block:
            stripped = line.strip()
            if not stripped.startswith("- ") or ":" not in stripped:
                continue
            key, value = stripped[2:].split(":", 1)
            metadata[key.strip().lower()] = value.strip()
        tasks.append(
            PortalTask(
                task_id=current_id,
                title=current_title,
                status=normalize_status(metadata.get("status", "todo")),
                completion=str(metadata.get("completion", "manual")).strip().lower(),
                priority=str(metadata.get("priority", "P2")).strip().upper(),
                track=str(metadata.get("track", "ops")).strip().lower(),
                depends_on=split_csv(metadata.get("depends on", "")),
                outputs=split_csv(metadata.get("outputs", "")),
                validation=[item.strip() for item in metadata.get("validation", "").split(";") if item.strip()],
                acceptance=str(metadata.get("acceptance", "")).strip(),
                source_line=current_line,
            )
        )
        current_id = ""
        current_title = ""
        current_line = 0
        block = []

    for index, line in enumerate(lines, start=1):
        if line.startswith(task_header_prefix):
            flush()
            header = line[3:].strip()
            parts = header.split(" ", 1)
            if len(parts) == 1:
                current_id = parts[0]
                current_title = ""
            else:
                current_id, current_title = parts[0], parts[1].strip()
            current_line = index
            block = []
            continue
        if current_id:
            block.append(line)

    flush()
    return tasks


class PortalImplementationDaemon:
    def __init__(
        self,
        *,
        todo_path: Path,
        state_path: Path,
        strategy_path: Path,
        events_path: Path,
        repo_root: Path | None = None,
        task_header_prefix: str = TASK_HEADER_PREFIX,
        implement: bool = False,
        implementation_command: str | None = None,
        implementation_timeout: float = DEFAULT_IMPLEMENTATION_TIMEOUT_SECONDS,
        implementation_log_dir: Path | None = None,
        use_ephemeral_worktree: bool = False,
        worktree_root: Path | None = None,
    ) -> None:
        self.todo_path = todo_path
        self.state_path = state_path
        self.strategy_path = strategy_path
        self.events_path = events_path
        self.repo_root = repo_root or REPO_ROOT
        self.task_header_prefix = normalize_task_header_prefix(task_header_prefix)
        self.implement = implement
        self.implementation_command = implementation_command
        self.implementation_timeout = implementation_timeout
        self.implementation_log_dir = implementation_log_dir or self.state_path.parent / "implementation_logs"
        self.use_ephemeral_worktree = use_ephemeral_worktree
        self.worktree_root = worktree_root or Path(tempfile.gettempdir()) / "211-ai-implementation-worktrees"

    def load_strategy(self) -> dict[str, Any]:
        defaults = {
            "generation": 0,
            "focus_tracks": DEFAULT_TRACKS,
            "blocked_tasks": [],
            "deprioritized_tasks": [],
            "last_rewrite_at": "",
            "last_rewrite_reason": "",
        }
        if not self.strategy_path.exists():
            self.strategy_path.parent.mkdir(parents=True, exist_ok=True)
            self.strategy_path.write_text(json.dumps(defaults, indent=2, sort_keys=True), encoding="utf-8")
            return defaults
        payload = json.loads(self.strategy_path.read_text(encoding="utf-8"))
        merged = {**defaults, **payload}
        merged["focus_tracks"] = [str(item).lower() for item in merged.get("focus_tracks", DEFAULT_TRACKS)]
        merged["blocked_tasks"] = [str(item) for item in merged.get("blocked_tasks", [])]
        merged["deprioritized_tasks"] = [str(item) for item in merged.get("deprioritized_tasks", [])]
        return merged

    def run_once(self) -> dict[str, Any]:
        tasks = parse_task_file(self.todo_path, self.task_header_prefix)
        if not tasks:
            raise RuntimeError(f"No tasks found in {self.todo_path}")
        previous = PortalTaskState.load(self.state_path)
        strategy = self.load_strategy()
        now = utc_now()

        previous_completed = set(previous.completed_task_ids)
        completed_set: set[str] = set()
        newly_completed: list[str] = []
        resolved_statuses: dict[str, str] = {}
        task_artifacts: dict[str, list[str]] = {}

        for task in tasks:
            existing_outputs = [item for item in task.outputs if (self.repo_root / item).exists()]
            task_artifacts[task.task_id] = existing_outputs
            artifact_complete = (
                task.completion == "artifact"
                and bool(task.outputs)
                and len(existing_outputs) == len(task.outputs)
            )
            if task.status == "completed" or artifact_complete:
                resolved_statuses[task.task_id] = "completed"
                completed_set.add(task.task_id)
                if task.task_id not in previous_completed:
                    newly_completed.append(task.task_id)
                continue
            if task.task_id in strategy.get("blocked_tasks", []) or task.status == "blocked":
                resolved_statuses[task.task_id] = "blocked"
                continue
            unresolved_deps = [dep for dep in task.depends_on if dep not in completed_set]
            if unresolved_deps:
                resolved_statuses[task.task_id] = "waiting"
                continue
            resolved_statuses[task.task_id] = "ready"

        selected = self._select_next_task(tasks, resolved_statuses, strategy)
        state = PortalTaskState.load(self.state_path)
        state.heartbeat_at = now
        if newly_completed or not state.last_progress_at:
            state.last_progress_at = now
        state.completed_task_ids = sorted(completed_set)
        state.completed_count = len(state.completed_task_ids)
        state.ready_task_ids = [task.task_id for task in tasks if resolved_statuses[task.task_id] == "ready"]
        state.waiting_task_ids = [task.task_id for task in tasks if resolved_statuses[task.task_id] == "waiting"]
        state.blocked_task_ids = [task.task_id for task in tasks if resolved_statuses[task.task_id] == "blocked"]
        state.ready_count = len(state.ready_task_ids)
        state.waiting_count = len(state.waiting_task_ids)
        state.blocked_count = len(state.blocked_task_ids)
        state.task_count = len(tasks)
        state.task_statuses = resolved_statuses
        state.task_artifacts = task_artifacts
        state.task_validation = {task.task_id: task.validation for task in tasks if task.validation}
        state.strategy_generation = int(strategy.get("generation", 0))
        state.implementation_attempts = previous.implementation_attempts
        state.last_implementation_task_id = previous.last_implementation_task_id
        state.last_implementation_started_at = previous.last_implementation_started_at
        state.last_implementation_finished_at = previous.last_implementation_finished_at
        state.last_implementation_returncode = previous.last_implementation_returncode
        state.last_implementation_log_path = previous.last_implementation_log_path

        if selected is not None:
            if state.active_task_id != selected.task_id:
                state.active_task_started_at = now
                state.last_progress_at = now
                self._record_event(
                    "task_selected",
                    {
                        "task_id": selected.task_id,
                        "title": selected.title,
                        "track": selected.track,
                    },
                )
            state.active_task_id = selected.task_id
            state.active_task_title = selected.title
            state.active_task_track = selected.track
            state.recommended_task_id = selected.task_id
            state.recommended_actions = self._build_recommended_actions(selected)
        else:
            state.active_task_id = ""
            state.active_task_title = ""
            state.active_task_track = ""
            state.active_task_started_at = ""
            state.recommended_task_id = ""
            state.recommended_actions = []

        state.save(self.state_path)
        for task_id in newly_completed:
            self._record_event("task_completed", {"task_id": task_id})
        implementation_result: dict[str, Any] | None = None
        if self.implement and selected is not None and resolved_statuses.get(selected.task_id) == "ready":
            implementation_result = self._run_implementation(selected, state)
        self._record_event(
            "daemon_pass",
            {
                "completed_count": state.completed_count,
                "ready_count": state.ready_count,
                "waiting_count": state.waiting_count,
                "blocked_count": state.blocked_count,
                "active_task_id": state.active_task_id,
            },
        )
        return {
            "task_count": state.task_count,
            "completed_count": state.completed_count,
            "ready_count": state.ready_count,
            "waiting_count": state.waiting_count,
            "blocked_count": state.blocked_count,
            "active_task_id": state.active_task_id,
            "state_path": str(self.state_path),
            "strategy_path": str(self.strategy_path),
            "events_path": str(self.events_path),
            "implementation_result": implementation_result,
        }

    def _run_implementation(self, task: PortalTask, state: PortalTaskState) -> dict[str, Any]:
        lock_path = self.state_path.parent / "implementation.lock"
        try:
            lock_fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            self._record_event("implementation_skipped", {"task_id": task.task_id, "reason": "lock_exists"})
            return {"skipped": True, "reason": "lock_exists"}

        started_at = utc_now()
        attempt = state.implementation_attempts.get(task.task_id, 0) + 1
        log_path = self.implementation_log_dir / f"{task.task_id.lower()}-attempt-{attempt}.log"
        prompt = self._build_implementation_prompt(task, attempt)
        workspace_path = self.repo_root
        command = self._build_implementation_command(workspace_path)
        result: dict[str, Any]

        try:
            os.write(lock_fd, f"{task.task_id}\n{started_at}\n".encode("utf-8"))
            os.close(lock_fd)
            if self.use_ephemeral_worktree:
                return self._run_implementation_in_ephemeral_worktree(
                    task=task,
                    state=state,
                    attempt=attempt,
                    started_at=started_at,
                    log_path=log_path,
                    prompt=prompt,
                )
            self.implementation_log_dir.mkdir(parents=True, exist_ok=True)
            self._record_event(
                "implementation_started",
                {
                    "task_id": task.task_id,
                    "attempt": attempt,
                    "command": command,
                    "log_path": str(log_path),
                },
            )
            with log_path.open("w", encoding="utf-8") as log_fh:
                log_fh.write(f"Task: {task.task_id} {task.title}\n")
                log_fh.write(f"Started: {started_at}\n")
                log_fh.write(f"Command: {' '.join(shlex.quote(item) for item in command)}\n\n")
                log_fh.flush()
                completed = subprocess.run(
                    command,
                    input=prompt,
                    text=True,
                    stdout=log_fh,
                    stderr=subprocess.STDOUT,
                    cwd=workspace_path,
                    timeout=self.implementation_timeout,
                    check=False,
                )
            finished_at = utc_now()
            state.implementation_attempts[task.task_id] = attempt
            state.last_implementation_task_id = task.task_id
            state.last_implementation_started_at = started_at
            state.last_implementation_finished_at = finished_at
            state.last_implementation_returncode = completed.returncode
            state.last_implementation_log_path = str(log_path)
            state.last_progress_at = finished_at
            state.save(self.state_path)
            result = {
                "task_id": task.task_id,
                "attempt": attempt,
                "returncode": completed.returncode,
                "log_path": str(log_path),
            }
            self._record_event("implementation_finished", result)
            return result
        except subprocess.TimeoutExpired:
            finished_at = utc_now()
            state.implementation_attempts[task.task_id] = attempt
            state.last_implementation_task_id = task.task_id
            state.last_implementation_started_at = started_at
            state.last_implementation_finished_at = finished_at
            state.last_implementation_returncode = 124
            state.last_implementation_log_path = str(log_path)
            state.save(self.state_path)
            result = {
                "task_id": task.task_id,
                "attempt": attempt,
                "returncode": 124,
                "log_path": str(log_path),
                "error": "timeout",
            }
            self._record_event("implementation_finished", result)
            return result
        finally:
            try:
                if lock_path.exists():
                    lock_path.unlink()
            except OSError:
                logger.warning("Failed to remove implementation lock %s", lock_path)

    def _run_implementation_in_ephemeral_worktree(
        self,
        *,
        task: PortalTask,
        state: PortalTaskState,
        attempt: int,
        started_at: str,
        log_path: Path,
        prompt: str,
    ) -> dict[str, Any]:
        self.implementation_log_dir.mkdir(parents=True, exist_ok=True)
        self.worktree_root.mkdir(parents=True, exist_ok=True)
        patch_dir = self.state_path.parent / "implementation_patches"
        patch_dir.mkdir(parents=True, exist_ok=True)
        safe_task_id = task.task_id.lower().replace("/", "-")
        worktree_path = self.worktree_root / f"{safe_task_id}-attempt-{attempt}-{int(time.time())}"
        patch_path = patch_dir / f"{safe_task_id}-attempt-{attempt}.patch"
        baseline_ref = ""
        command: list[str] = []
        returncode = 1
        apply_result: dict[str, Any] = {"applied": False}

        try:
            baseline_ref = self._create_seeded_worktree(worktree_path)
            command = self._build_implementation_command(worktree_path)
            self._record_event(
                "implementation_started",
                {
                    "task_id": task.task_id,
                    "attempt": attempt,
                    "command": command,
                    "log_path": str(log_path),
                    "worktree_path": str(worktree_path),
                    "baseline_ref": baseline_ref,
                },
            )
            with log_path.open("w", encoding="utf-8") as log_fh:
                log_fh.write(f"Task: {task.task_id} {task.title}\n")
                log_fh.write(f"Started: {started_at}\n")
                log_fh.write(f"Workspace: {worktree_path}\n")
                log_fh.write(f"Baseline: {baseline_ref}\n")
                log_fh.write(f"Patch: {patch_path}\n")
                log_fh.write(f"Command: {' '.join(shlex.quote(item) for item in command)}\n\n")
                log_fh.flush()
                completed = subprocess.run(
                    command,
                    input=prompt,
                    text=True,
                    stdout=log_fh,
                    stderr=subprocess.STDOUT,
                    cwd=worktree_path,
                    timeout=self.implementation_timeout,
                    check=False,
                )
            returncode = completed.returncode
            patch_created = self._write_worktree_patch(worktree_path, baseline_ref, patch_path)
            if returncode == 0 and patch_created:
                apply_result = self._apply_patch_to_main_workspace(patch_path)
            elif returncode == 0:
                apply_result = {"applied": False, "reason": "empty_patch", "patch_path": str(patch_path)}
        except subprocess.TimeoutExpired:
            returncode = 124
            self._record_event(
                "implementation_timeout",
                {"task_id": task.task_id, "attempt": attempt, "worktree_path": str(worktree_path)},
            )
        finally:
            self._remove_worktree(worktree_path)

        finished_at = utc_now()
        state.implementation_attempts[task.task_id] = attempt
        state.last_implementation_task_id = task.task_id
        state.last_implementation_started_at = started_at
        state.last_implementation_finished_at = finished_at
        state.last_implementation_returncode = returncode
        state.last_implementation_log_path = str(log_path)
        state.last_progress_at = finished_at
        state.save(self.state_path)
        result = {
            "task_id": task.task_id,
            "attempt": attempt,
            "returncode": returncode,
            "log_path": str(log_path),
            "worktree_path": str(worktree_path),
            "patch_path": str(patch_path),
            "baseline_ref": baseline_ref,
            "apply_result": apply_result,
        }
        self._record_event("implementation_finished", result)
        return result

    def _create_seeded_worktree(self, worktree_path: Path) -> str:
        self._run_git(["worktree", "add", "--detach", str(worktree_path), "HEAD"], cwd=self.repo_root)
        self._seed_worktree_from_workspace(worktree_path)
        baseline_ref = self._run_git(["rev-parse", "HEAD"], cwd=worktree_path).stdout.strip()
        status = self._run_git(["status", "--porcelain"], cwd=worktree_path).stdout.strip()
        if status:
            self._run_git(["add", "-A"], cwd=worktree_path)
            self._run_git(
                [
                    "-c",
                    "user.name=Implementation Daemon",
                    "-c",
                    "user.email=implementation-daemon@example.invalid",
                    "commit",
                    "-m",
                    "implementation daemon baseline",
                ],
                cwd=worktree_path,
            )
            baseline_ref = self._run_git(["rev-parse", "HEAD"], cwd=worktree_path).stdout.strip()
        return baseline_ref

    def _seed_worktree_from_workspace(self, worktree_path: Path) -> None:
        dirty_paths = set(self._git_path_list(["diff", "--name-only", "HEAD", "--"]))
        dirty_paths.update(self._git_path_list(["ls-files", "--others", "--exclude-standard", "-z"]))
        for relative in sorted(path for path in dirty_paths if self._should_seed_path(path)):
            source = self.repo_root / relative
            target = worktree_path / relative
            if source.exists() and source.is_file():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
            elif source.exists() and source.is_dir():
                continue
            elif target.exists():
                target.unlink()

    def _git_path_list(self, args: list[str]) -> list[str]:
        result = self._run_git(args, cwd=self.repo_root)
        if "-z" in args:
            return [item for item in result.stdout.split("\0") if item]
        return [item for item in result.stdout.splitlines() if item]

    @staticmethod
    def _should_seed_path(path: str) -> bool:
        skip_prefixes = (
            ".git/",
            ".pytest_cache/",
            "data/",
            "node_modules/",
            "wallet_interface/ui/node_modules/",
            "wallet_interface/ui/dist/",
        )
        skip_parts = {".git", "__pycache__", ".pytest_cache", "node_modules"}
        normalized = path.replace("\\", "/")
        if normalized == "data" or normalized.startswith(skip_prefixes):
            return False
        return not any(part in skip_parts for part in normalized.split("/"))

    def _write_worktree_patch(self, worktree_path: Path, baseline_ref: str, patch_path: Path) -> bool:
        self._run_git(["add", "-A"], cwd=worktree_path)
        diff = self._run_git(["diff", "--binary", "--cached", baseline_ref, "--"], cwd=worktree_path).stdout
        patch_path.write_text(diff, encoding="utf-8")
        return bool(diff.strip())

    def _apply_patch_to_main_workspace(self, patch_path: Path) -> dict[str, Any]:
        integration_lock = self._repo_integration_lock_path()
        try:
            lock_fd = os.open(integration_lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            return {"applied": False, "reason": "integration_lock_exists", "patch_path": str(patch_path)}

        try:
            os.write(lock_fd, f"{patch_path}\n{utc_now()}\n".encode("utf-8"))
            os.close(lock_fd)
            check = subprocess.run(
                ["git", "apply", "--check", str(patch_path)],
                cwd=self.repo_root,
                text=True,
                capture_output=True,
                check=False,
            )
            command = ["git", "apply", str(patch_path)] if check.returncode == 0 else ["git", "apply", "--3way", str(patch_path)]
            apply = subprocess.run(command, cwd=self.repo_root, text=True, capture_output=True, check=False)
            return {
                "applied": apply.returncode == 0,
                "returncode": apply.returncode,
                "command": command,
                "patch_path": str(patch_path),
                "stdout": apply.stdout[-2000:],
                "stderr": apply.stderr[-2000:],
                "check_returncode": check.returncode,
            }
        finally:
            try:
                if integration_lock.exists():
                    integration_lock.unlink()
            except OSError:
                logger.warning("Failed to remove integration lock %s", integration_lock)

    def _remove_worktree(self, worktree_path: Path) -> None:
        if not worktree_path.exists():
            return
        remove = subprocess.run(
            ["git", "worktree", "remove", "--force", str(worktree_path)],
            cwd=self.repo_root,
            text=True,
            capture_output=True,
            check=False,
        )
        if remove.returncode != 0:
            logger.warning("Failed to remove worktree %s: %s", worktree_path, remove.stderr.strip())

    def _run_git(self, args: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(["git", *args], cwd=cwd, text=True, capture_output=True, check=False)
        if result.returncode != 0:
            raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
        return result

    def _repo_integration_lock_path(self) -> Path:
        git_common_dir = self._run_git(["rev-parse", "--git-common-dir"], cwd=self.repo_root).stdout.strip()
        path = Path(git_common_dir)
        if not path.is_absolute():
            path = self.repo_root / path
        return path / "implementation-integration.lock"

    def _build_implementation_command(self, workspace_path: Path) -> list[str]:
        if self.implementation_command:
            return shlex.split(self.implementation_command)
        env_command = os.environ.get("IMPLEMENTATION_DAEMON_COMMAND", "").strip()
        if env_command:
            return shlex.split(env_command)
        codex = shutil.which("codex")
        if codex:
            return [codex, "exec", "--full-auto", "-C", str(workspace_path), "-"]
        raise RuntimeError(
            "No implementation command configured. Install codex or set IMPLEMENTATION_DAEMON_COMMAND."
        )

    def _build_implementation_prompt(self, task: PortalTask, attempt: int) -> str:
        return f"""You are an autonomous implementation agent working in this repository.

Implement exactly this backlog task and keep changes scoped.

Task:
- ID: {task.task_id}
- Title: {task.title}
- Priority: {task.priority}
- Track: {task.track}
- Attempt: {attempt}
- Todo file: {self.todo_path}
- Source line: {task.source_line}
- Depends on: {", ".join(task.depends_on) or "none"}
- Expected outputs: {", ".join(task.outputs) or "none listed"}
- Validation commands: {"; ".join(task.validation) or "none listed"}
- Acceptance: {task.acceptance or "none listed"}

Primary plan document:
- docs/AI_AGENT_CHAT_IMPLEMENTATION_PLAN.md when the task ID starts with AGENT-
- docs/211_SERVICE_NAVIGATION_PORTAL_PLAN.md when the task ID starts with PORTAL-

Rules:
- Read the relevant plan and nearby code before editing.
- Do not revert unrelated local changes.
- Prefer existing repo patterns and small, reviewable changes.
- Implement the expected outputs for this task.
- Run the listed validation commands when practical.
- If validation cannot be run, record why in your final response.
- Do not mark the backlog task completed manually unless the task explicitly asks for TODO metadata changes.
- Final response should list changed files and validation results.
"""

    def _build_recommended_actions(self, task: PortalTask) -> list[str]:
        actions = [f"Implement outputs for {task.task_id}: {', '.join(task.outputs)}"]
        for command in task.validation:
            actions.append(f"Validate with: {command}")
        if task.acceptance:
            actions.append(f"Acceptance: {task.acceptance}")
        return actions

    def _select_next_task(
        self,
        tasks: list[PortalTask],
        resolved_statuses: dict[str, str],
        strategy: dict[str, Any],
    ) -> PortalTask | None:
        ready = [task for task in tasks if resolved_statuses.get(task.task_id) == "ready"]
        if not ready:
            return None
        focus_order = {
            track: index
            for index, track in enumerate(
                [str(item).lower() for item in strategy.get("focus_tracks", DEFAULT_TRACKS)]
            )
        }
        deprioritized = {str(item) for item in strategy.get("deprioritized_tasks", [])}

        def sort_key(task: PortalTask) -> tuple[int, int, int, int, str]:
            return (
                PRIORITY_ORDER.get(task.priority, 99),
                1 if task.task_id in deprioritized else 0,
                focus_order.get(task.track, len(focus_order)),
                len(task.depends_on),
                task.task_id,
            )

        return sorted(ready, key=sort_key)[0]

    def _record_event(self, event_type: str, payload: dict[str, Any]) -> None:
        self.events_path.parent.mkdir(parents=True, exist_ok=True)
        event = {"type": event_type, "timestamp": utc_now(), **payload}
        with self.events_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=False) + "\n")


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
        "--task-prefix",
        default=TASK_HEADER_PREFIX,
        help="Markdown heading prefix for tasks, for example '## PORTAL-' or '## AGENT-'",
    )
    parser.add_argument(
        "--state-prefix",
        default="portal",
        help="State file prefix inside --state-dir",
    )
    parser.add_argument("--implement", action="store_true", help="Invoke an autonomous implementation agent for the ready task")
    parser.add_argument(
        "--implementation-command",
        default="",
        help="Command used for implementation. Defaults to codex exec --full-auto.",
    )
    parser.add_argument("--implementation-timeout", type=float, default=DEFAULT_IMPLEMENTATION_TIMEOUT_SECONDS)
    parser.add_argument(
        "--no-ephemeral-worktree",
        action="store_true",
        help="Run the implementation command in the main checkout instead of an isolated temporary git worktree",
    )
    parser.add_argument(
        "--worktree-root",
        type=Path,
        default=None,
        help="Directory for temporary implementation worktrees. Defaults to the system temp directory.",
    )
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
    daemon = PortalImplementationDaemon(
        todo_path=args.todo_path,
        state_path=args.state_dir / f"{args.state_prefix}_task_state.json",
        strategy_path=args.state_dir / f"{args.state_prefix}_strategy.json",
        events_path=args.state_dir / f"{args.state_prefix}_events.jsonl",
        task_header_prefix=args.task_prefix,
        implement=args.implement,
        implementation_command=args.implementation_command or None,
        implementation_timeout=args.implementation_timeout,
        use_ephemeral_worktree=args.implement and not args.no_ephemeral_worktree,
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
