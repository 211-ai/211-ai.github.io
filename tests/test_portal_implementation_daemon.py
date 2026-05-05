from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.portal_implementation_daemon import PortalImplementationDaemon, PortalTaskState, parse_task_file
from scripts.portal_implementation_supervisor import PortalImplementationSupervisor, PortalSupervisorConfig


def write_todo(path: Path) -> None:
    path.write_text(
        """
# Test Todo

## PORTAL-000 Control Plane
- Status: todo
- Completion: artifact
- Priority: P0
- Track: platform
- Depends on: none
- Outputs: docs/control.md, scripts/control.py
- Validation: python scripts/control.py --once
- Acceptance: control plane exists

## PORTAL-010 Builder
- Status: todo
- Priority: P0
- Track: data
- Depends on: PORTAL-000
- Outputs: data/output.parquet
- Validation: python scripts/build.py
- Acceptance: builder exists

## PORTAL-020 UI
- Status: todo
- Priority: P1
- Track: ui
- Depends on: PORTAL-010
- Outputs: ui/detail.tsx
- Validation: npm test
- Acceptance: ui exists
""".strip()
        + "\n",
        encoding="utf-8",
    )


def write_agent_todo(path: Path) -> None:
    path.write_text(
        """
# Agent Todo

## AGENT-000 Control Plane
- Status: todo
- Completion: artifact
- Priority: P0
- Track: platform
- Depends on: none
- Outputs: docs/agent.md
- Validation: python scripts/agent.py --once
- Acceptance: agent control plane exists

## AGENT-010 Chat Shell
- Status: todo
- Priority: P1
- Track: ui
- Depends on: AGENT-000
- Outputs: ui/chat.tsx
- Validation: npm test
- Acceptance: chat exists
""".strip()
        + "\n",
        encoding="utf-8",
    )


def init_git_repo(path: Path) -> None:
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=path, check=True)
    subprocess.run(["git", "add", "-A"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=path, check=True, capture_output=True, text=True)


def test_parse_task_file_reads_machine_friendly_markdown(tmp_path):
    todo_path = tmp_path / "todo.md"
    write_todo(todo_path)

    tasks = parse_task_file(todo_path)

    assert [task.task_id for task in tasks] == ["PORTAL-000", "PORTAL-010", "PORTAL-020"]
    assert tasks[0].outputs == ["docs/control.md", "scripts/control.py"]
    assert tasks[1].depends_on == ["PORTAL-000"]
    assert tasks[2].track == "ui"


def test_parse_task_file_supports_agent_task_prefix(tmp_path):
    todo_path = tmp_path / "agent_todo.md"
    write_agent_todo(todo_path)

    tasks = parse_task_file(todo_path, "## AGENT-")

    assert [task.task_id for task in tasks] == ["AGENT-000", "AGENT-010"]
    assert tasks[0].outputs == ["docs/agent.md"]
    assert tasks[1].depends_on == ["AGENT-000"]


def test_daemon_selects_agent_tasks_with_custom_prefix(tmp_path):
    repo_root = tmp_path / "repo"
    todo_path = repo_root / "agent_todo.md"
    state_dir = repo_root / "state"
    (repo_root / "docs").mkdir(parents=True)
    (repo_root / "docs" / "agent.md").write_text("ok", encoding="utf-8")
    write_agent_todo(todo_path)

    daemon = PortalImplementationDaemon(
        todo_path=todo_path,
        state_path=state_dir / "agent_chat_task_state.json",
        strategy_path=state_dir / "agent_chat_strategy.json",
        events_path=state_dir / "agent_chat_events.jsonl",
        repo_root=repo_root,
        task_header_prefix="AGENT-",
    )

    result = daemon.run_once()
    state = PortalTaskState.load(state_dir / "agent_chat_task_state.json")

    assert result["completed_count"] == 1
    assert "AGENT-000" in state.completed_task_ids
    assert state.active_task_id == "AGENT-010"


def test_daemon_can_invoke_autonomous_implementation_command(tmp_path):
    repo_root = tmp_path / "repo"
    todo_path = repo_root / "agent_todo.md"
    state_dir = repo_root / "state"
    fake_worker = repo_root / "fake_worker.py"
    output = repo_root / "docs" / "agent.md"
    repo_root.mkdir(parents=True)
    write_agent_todo(todo_path)
    fake_worker.write_text(
        """
from pathlib import Path
import sys

prompt = sys.stdin.read()
assert "AGENT-000" in prompt
Path("docs").mkdir(exist_ok=True)
Path("docs/agent.md").write_text("implemented", encoding="utf-8")
""".strip()
        + "\n",
        encoding="utf-8",
    )

    daemon = PortalImplementationDaemon(
        todo_path=todo_path,
        state_path=state_dir / "agent_chat_task_state.json",
        strategy_path=state_dir / "agent_chat_strategy.json",
        events_path=state_dir / "agent_chat_events.jsonl",
        repo_root=repo_root,
        task_header_prefix="AGENT-",
        implement=True,
        implementation_command=f"python {fake_worker}",
        implementation_timeout=10,
    )

    result = daemon.run_once()
    state = PortalTaskState.load(state_dir / "agent_chat_task_state.json")

    assert result["implementation_result"]["task_id"] == "AGENT-000"
    assert result["implementation_result"]["returncode"] == 0
    assert state.implementation_attempts["AGENT-000"] == 1
    assert state.last_implementation_task_id == "AGENT-000"
    assert output.read_text(encoding="utf-8") == "implemented"


def test_daemon_runs_implementation_in_ephemeral_worktree_and_applies_patch(tmp_path):
    repo_root = tmp_path / "repo"
    todo_path = repo_root / "agent_todo.md"
    state_dir = repo_root / "state"
    fake_worker = repo_root / "fake_worker.py"
    output = repo_root / "docs" / "agent.md"
    worktree_root = tmp_path / "worktrees"
    repo_root.mkdir(parents=True)
    write_agent_todo(todo_path)
    fake_worker.write_text(
        """
from pathlib import Path
import os
import sys

prompt = sys.stdin.read()
assert "AGENT-000" in prompt
assert "agent-000-attempt-1" in os.getcwd()
Path("docs").mkdir(exist_ok=True)
Path("docs/agent.md").write_text("implemented in worktree", encoding="utf-8")
""".strip()
        + "\n",
        encoding="utf-8",
    )
    init_git_repo(repo_root)

    daemon = PortalImplementationDaemon(
        todo_path=todo_path,
        state_path=state_dir / "agent_chat_task_state.json",
        strategy_path=state_dir / "agent_chat_strategy.json",
        events_path=state_dir / "agent_chat_events.jsonl",
        repo_root=repo_root,
        task_header_prefix="AGENT-",
        implement=True,
        implementation_command=f"python {fake_worker}",
        implementation_timeout=10,
        use_ephemeral_worktree=True,
        worktree_root=worktree_root,
    )

    result = daemon.run_once()
    implementation = result["implementation_result"]
    state = PortalTaskState.load(state_dir / "agent_chat_task_state.json")

    assert implementation["task_id"] == "AGENT-000"
    assert implementation["returncode"] == 0
    assert implementation["commit_result"]["committed"] is True
    assert implementation["implementation_commit"]
    assert implementation["branch"].startswith("implementation/agent-000-attempt-1-")
    assert Path(implementation["worktree_path"]).exists()
    assert state.last_implementation_task_id == "AGENT-000"
    assert state.last_implementation_branch == implementation["branch"]
    assert state.last_implementation_commit == implementation["implementation_commit"]
    assert not output.exists()
    assert (Path(implementation["worktree_path"]) / "docs" / "agent.md").read_text(
        encoding="utf-8"
    ) == "implemented in worktree"
    assert (
        subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=implementation["worktree_path"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        == ""
    )


def test_daemon_marks_output_backed_tasks_completed_and_selects_next(tmp_path):
    repo_root = tmp_path / "repo"
    todo_path = repo_root / "todo.md"
    state_dir = repo_root / "state"
    (repo_root / "docs").mkdir(parents=True)
    (repo_root / "scripts").mkdir(parents=True)
    (repo_root / "docs" / "control.md").write_text("ok", encoding="utf-8")
    (repo_root / "scripts" / "control.py").write_text("print('ok')", encoding="utf-8")
    write_todo(todo_path)

    daemon = PortalImplementationDaemon(
        todo_path=todo_path,
        state_path=state_dir / "portal_task_state.json",
        strategy_path=state_dir / "portal_strategy.json",
        events_path=state_dir / "portal_events.jsonl",
        repo_root=repo_root,
    )

    result = daemon.run_once()
    state = PortalTaskState.load(state_dir / "portal_task_state.json")

    assert result["completed_count"] == 1
    assert "PORTAL-000" in state.completed_task_ids
    assert state.active_task_id == "PORTAL-010"
    assert state.ready_task_ids == ["PORTAL-010"]
    assert state.waiting_task_ids == ["PORTAL-020"]


def test_supervisor_rewrites_strategy_for_stale_task(tmp_path):
    repo_root = tmp_path / "repo"
    todo_path = repo_root / "todo.md"
    state_dir = repo_root / "state"
    repo_root.mkdir(parents=True)
    write_todo(todo_path)
    state_dir.mkdir(parents=True)

    stale_time = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    state = PortalTaskState(
        heartbeat_at=stale_time,
        last_progress_at=stale_time,
        active_task_id="PORTAL-010",
        active_task_title="Builder",
        active_task_track="data",
        active_task_started_at=stale_time,
        completed_task_ids=["PORTAL-000"],
        ready_task_ids=["PORTAL-010"],
        task_statuses={"PORTAL-000": "completed", "PORTAL-010": "ready"},
        completed_count=1,
        ready_count=1,
        task_count=3,
    )
    state.save(state_dir / "portal_task_state.json")

    supervisor = PortalImplementationSupervisor(
        PortalSupervisorConfig(
            todo_path=todo_path,
            state_path=state_dir / "portal_task_state.json",
            strategy_path=state_dir / "portal_strategy.json",
            events_path=state_dir / "portal_supervisor_events.jsonl",
            state_dir=state_dir,
            stale_seconds=60.0,
            check_interval=1.0,
            max_restarts=1,
            daemon_interval=60.0,
        )
    )

    result = supervisor.run_once()
    strategy = json.loads((state_dir / "portal_strategy.json").read_text(encoding="utf-8"))

    assert result["stuck"] is True
    assert strategy["generation"] == 1
    assert "PORTAL-010" in strategy["deprioritized_tasks"]
    assert strategy["focus_tracks"][-1] == "data"
