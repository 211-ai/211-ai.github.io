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
import scripts.portal_implementation_supervisor as supervisor_module
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
- Validation: python -c "print('control-ok')"
- Acceptance: control plane exists

## PORTAL-010 Builder
- Status: todo
- Priority: P0
- Track: data
- Depends on: PORTAL-000
- Outputs: data/output.parquet
- Validation: python -c "print('build-ok')"
- Acceptance: builder exists

## PORTAL-020 UI
- Status: todo
- Priority: P1
- Track: ui
- Depends on: PORTAL-010
- Outputs: ui/detail.tsx
- Validation: python -c "print('ui-ok')"
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
- Validation: python -c "print('agent-control-ok')"
- Acceptance: agent control plane exists

## AGENT-010 Chat Shell
- Status: todo
- Priority: P1
- Track: ui
- Depends on: AGENT-000
- Outputs: ui/chat.tsx
- Validation: python -c "print('agent-chat-ok')"
- Acceptance: chat exists
""".strip()
        + "\n",
        encoding="utf-8",
    )


def write_parallel_agent_todo(path: Path) -> None:
    path.write_text(
        """
# Agent Todo

## AGENT-000 Primary Task
- Status: todo
- Priority: P0
- Track: ui
- Depends on: none
- Outputs: ui/primary.tsx
- Validation: python -c "print('primary-ok')"
- Acceptance: primary exists

## AGENT-010 Secondary Task
- Status: todo
- Priority: P1
- Track: data
- Depends on: none
- Outputs: data/secondary.json
- Validation: python -c "print('secondary-ok')"
- Acceptance: secondary exists
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
    state_dir = tmp_path / "state"
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
    state_dir = tmp_path / "state"
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


def test_daemon_runs_implementation_in_worktree_branch_and_merges_main(tmp_path):
    repo_root = tmp_path / "repo"
    todo_path = repo_root / "agent_todo.md"
    state_dir = tmp_path / "agent_state"
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
    assert implementation["validation_result"]["passed"] is True
    assert implementation["commit_result"]["committed"] is True
    assert implementation["implementation_commit"]
    assert implementation["branch"].startswith("implementation/agent-000-attempt-1-")
    assert implementation["merge_result"]["merged"] is True
    assert implementation["cleanup_result"]["cleaned"] is True
    assert implementation["merge_result"]["merge_commit"]
    assert not Path(implementation["worktree_path"]).exists()
    assert state.last_implementation_task_id == "AGENT-000"
    assert state.last_implementation_branch == implementation["branch"]
    assert state.last_implementation_commit == implementation["implementation_commit"]
    assert state.last_merge_branch == implementation["branch"]
    assert state.last_merge_commit == implementation["merge_result"]["merge_commit"]
    assert output.read_text(encoding="utf-8") == "implemented in worktree"
    branch_check = subprocess.run(
        ["git", "rev-parse", "--verify", implementation["branch"]],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert branch_check.returncode != 0


def test_daemon_validation_failure_blocks_commit_and_merge(tmp_path):
    repo_root = tmp_path / "repo"
    todo_path = repo_root / "agent_todo.md"
    state_dir = tmp_path / "agent_state"
    fake_worker = repo_root / "fake_worker.py"
    validate_fail = repo_root / "validate_fail.py"
    repo_root.mkdir(parents=True)
    todo_path.write_text(
        """
# Agent Todo

## AGENT-000 Control Plane
- Status: todo
- Priority: P0
- Track: platform
- Depends on: none
- Outputs: docs/agent.md
- Validation: python validate_fail.py
- Acceptance: agent control plane exists
""".strip()
        + "\n",
        encoding="utf-8",
    )
    fake_worker.write_text(
        """
from pathlib import Path

Path("docs").mkdir(exist_ok=True)
Path("docs/agent.md").write_text("implemented in worktree", encoding="utf-8")
""".strip()
        + "\n",
        encoding="utf-8",
    )
    validate_fail.write_text("import sys\nsys.exit(7)\n", encoding="utf-8")
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
        worktree_root=tmp_path / "worktrees",
    )

    result = daemon.run_once()
    implementation = result["implementation_result"]

    assert implementation["task_id"] == "AGENT-000"
    assert implementation["returncode"] == 7
    assert implementation["validation_result"]["passed"] is False
    assert implementation["commit_result"]["committed"] is False
    assert implementation["merge_result"]["merged"] is False
    assert implementation["cleanup_result"]["cleaned"] is False
    assert Path(implementation["worktree_path"]).exists()
    assert not (repo_root / "docs" / "agent.md").exists()
    branch_check = subprocess.run(
        ["git", "rev-parse", "--verify", implementation["branch"]],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert branch_check.returncode == 0


def test_daemon_cleans_no_change_ephemeral_worktree(tmp_path):
    repo_root = tmp_path / "repo"
    todo_path = repo_root / "agent_todo.md"
    state_dir = tmp_path / "agent_state"
    fake_worker = repo_root / "fake_worker.py"
    repo_root.mkdir(parents=True)
    todo_path.write_text(
        """
# Agent Todo

## AGENT-000 Control Plane
- Status: todo
- Priority: P0
- Track: platform
- Depends on: none
- Outputs: none
- Validation: python -c "print('agent-control-ok')"
- Acceptance: agent control plane exists
""".strip()
        + "\n",
        encoding="utf-8",
    )
    fake_worker.write_text("print('no changes')\n", encoding="utf-8")
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
        worktree_root=tmp_path / "worktrees",
    )

    result = daemon.run_once()
    implementation = result["implementation_result"]

    assert implementation["commit_result"] == {"committed": False, "reason": "no_changes"}
    assert implementation["cleanup_result"]["cleaned"] is True
    assert not Path(implementation["worktree_path"]).exists()
    assert subprocess.run(
        ["git", "rev-parse", "--verify", implementation["branch"]],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    ).returncode != 0


def test_daemon_merge_failure_keeps_artifact_task_ready(tmp_path):
    repo_root = tmp_path / "repo"
    todo_path = repo_root / "agent_todo.md"
    state_dir = tmp_path / "agent_state"
    fake_worker = repo_root / "fake_worker.py"
    repo_root.mkdir(parents=True)
    write_agent_todo(todo_path)
    fake_worker.write_text(
        f"""
from pathlib import Path

main_repo = Path({str(repo_root)!r})
Path("docs").mkdir(exist_ok=True)
Path("docs/agent.md").write_text("implemented in worktree", encoding="utf-8")
(main_repo / "docs").mkdir(exist_ok=True)
(main_repo / "docs" / "agent.md").write_text("dirty main copy", encoding="utf-8")
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
        worktree_root=tmp_path / "worktrees",
    )

    result = daemon.run_once()
    implementation = result["implementation_result"]
    state = PortalTaskState.load(state_dir / "agent_chat_task_state.json")

    assert implementation["validation_result"]["passed"] is True
    assert implementation["commit_result"]["committed"] is True
    assert implementation["merge_result"]["attempted"] is True
    assert implementation["merge_result"]["merged"] is False
    assert implementation["merge_result"]["reason"] == "main_checkout_dirty_conflict"
    assert implementation["merge_result"]["dirty_paths"] == ["docs/agent.md"]
    assert implementation["returncode"] != 0
    assert state.last_merge_returncode != 0

    daemon.implement = False
    result = daemon.run_once()
    state = PortalTaskState.load(state_dir / "agent_chat_task_state.json")

    assert result["completed_count"] == 0
    assert "AGENT-000" not in state.completed_task_ids
    assert state.active_task_id == "AGENT-000"


def test_daemon_skips_new_attempt_when_unresolved_merge_failure_exists(tmp_path):
    repo_root = tmp_path / "repo"
    todo_path = repo_root / "agent_todo.md"
    state_dir = tmp_path / "agent_state"
    events_path = state_dir / "agent_chat_events.jsonl"
    repo_root.mkdir(parents=True)
    write_agent_todo(todo_path)
    init_git_repo(repo_root)
    default_branch = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    branch_name = "implementation/agent-000-attempt-1-test"
    subprocess.run(["git", "checkout", "-b", branch_name], cwd=repo_root, check=True, capture_output=True, text=True)
    (repo_root / "docs").mkdir(exist_ok=True)
    (repo_root / "docs" / "agent.md").write_text("implemented in branch", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=repo_root, check=True)
    subprocess.run(["git", "commit", "-m", "AGENT-000: failed merge candidate"], cwd=repo_root, check=True)
    implementation_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    subprocess.run(["git", "checkout", default_branch], cwd=repo_root, check=True, capture_output=True, text=True)
    (repo_root / "docs").mkdir(exist_ok=True)
    (repo_root / "docs" / "agent.md").write_text("dirty main copy", encoding="utf-8")
    events_path.parent.mkdir(parents=True, exist_ok=True)
    events_path.write_text(
        json.dumps(
            {
                "type": "implementation_finished",
                "task_id": "AGENT-000",
                "attempt": 1,
                "returncode": 2,
                "worktree_path": str(tmp_path / "missing-worktree"),
                "branch": branch_name,
                "implementation_commit": implementation_commit,
                "merge_result": {"attempted": True, "merged": False, "returncode": 2},
                "validation_result": {"attempted": True, "passed": True, "returncode": 0},
                "cleanup_result": {"cleaned": False, "reason": "not_attempted"},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    daemon = PortalImplementationDaemon(
        todo_path=todo_path,
        state_path=state_dir / "agent_chat_task_state.json",
        strategy_path=state_dir / "agent_chat_strategy.json",
        events_path=events_path,
        repo_root=repo_root,
        task_header_prefix="AGENT-",
        implement=True,
        implementation_command=f"python {repo_root / 'missing.py'}",
        implementation_timeout=10,
        use_ephemeral_worktree=True,
        worktree_root=tmp_path / "worktrees",
    )

    result = daemon.run_once()

    assert result["merge_reconciliation"][0]["resolved"] is False
    assert result["implementation_result"]["skipped"] is True
    assert result["implementation_result"]["reason"] == "unresolved_merge_failure"
    assert result["implementation_result"]["branch"] == branch_name
    assert not list((tmp_path / "worktrees").glob("*"))


def test_daemon_prefers_other_ready_task_when_unresolved_merge_failure_exists(tmp_path):
    repo_root = tmp_path / "repo"
    todo_path = repo_root / "parallel_agent_todo.md"
    state_dir = tmp_path / "agent_state"
    events_path = state_dir / "agent_chat_events.jsonl"
    repo_root.mkdir(parents=True)
    write_parallel_agent_todo(todo_path)
    init_git_repo(repo_root)
    default_branch = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    branch_name = "implementation/agent-000-attempt-1-test"
    subprocess.run(["git", "checkout", "-b", branch_name], cwd=repo_root, check=True, capture_output=True, text=True)
    (repo_root / "ui").mkdir(exist_ok=True)
    (repo_root / "ui" / "primary.tsx").write_text("implemented in branch", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=repo_root, check=True)
    subprocess.run(["git", "commit", "-m", "AGENT-000: failed merge candidate"], cwd=repo_root, check=True)
    implementation_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    subprocess.run(["git", "checkout", default_branch], cwd=repo_root, check=True, capture_output=True, text=True)
    (repo_root / "ui").mkdir(exist_ok=True)
    (repo_root / "ui" / "primary.tsx").write_text("dirty main copy", encoding="utf-8")
    events_path.parent.mkdir(parents=True, exist_ok=True)
    events_path.write_text(
        json.dumps(
            {
                "type": "implementation_finished",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "task_id": "AGENT-000",
                "attempt": 1,
                "returncode": 2,
                "worktree_path": str(tmp_path / "missing-worktree"),
                "branch": branch_name,
                "implementation_commit": implementation_commit,
                "merge_result": {"attempted": True, "merged": False, "returncode": 2},
                "validation_result": {"attempted": True, "passed": True, "returncode": 0},
                "cleanup_result": {"cleaned": False, "reason": "not_attempted"},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    daemon = PortalImplementationDaemon(
        todo_path=todo_path,
        state_path=state_dir / "agent_chat_task_state.json",
        strategy_path=state_dir / "agent_chat_strategy.json",
        events_path=events_path,
        repo_root=repo_root,
        task_header_prefix="AGENT-",
    )

    result = daemon.run_once()

    assert result["active_task_id"] == "AGENT-010"


def test_daemon_skips_recent_no_change_retry(tmp_path):
    repo_root = tmp_path / "repo"
    todo_path = repo_root / "agent_todo.md"
    state_dir = tmp_path / "agent_state"
    events_path = state_dir / "agent_chat_events.jsonl"
    repo_root.mkdir(parents=True)
    write_agent_todo(todo_path)
    events_path.parent.mkdir(parents=True, exist_ok=True)
    events_path.write_text(
        json.dumps(
            {
                "type": "implementation_finished",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "task_id": "AGENT-000",
                "attempt": 1,
                "returncode": 0,
                "commit_result": {"committed": False, "reason": "no_changes"},
                "merge_result": {"merged": False, "reason": "not_attempted"},
                "validation_result": {"attempted": True, "passed": True, "returncode": 0},
                "cleanup_result": {"cleaned": True},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    daemon = PortalImplementationDaemon(
        todo_path=todo_path,
        state_path=state_dir / "agent_chat_task_state.json",
        strategy_path=state_dir / "agent_chat_strategy.json",
        events_path=events_path,
        repo_root=repo_root,
        task_header_prefix="AGENT-",
        implement=True,
        implementation_command=f"python {repo_root / 'missing.py'}",
    )

    result = daemon.run_once()

    assert result["implementation_result"]["skipped"] is True
    assert result["implementation_result"]["reason"] == "recent_no_change"


def test_daemon_prefers_other_ready_task_when_recent_no_change_exists(tmp_path):
    repo_root = tmp_path / "repo"
    todo_path = repo_root / "parallel_agent_todo.md"
    state_dir = tmp_path / "agent_state"
    events_path = state_dir / "agent_chat_events.jsonl"
    repo_root.mkdir(parents=True)
    write_parallel_agent_todo(todo_path)
    events_path.parent.mkdir(parents=True, exist_ok=True)
    events_path.write_text(
        json.dumps(
            {
                "type": "implementation_finished",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "task_id": "AGENT-000",
                "attempt": 3,
                "returncode": 0,
                "commit_result": {"committed": False, "reason": "no_changes"},
                "merge_result": {"merged": False, "reason": "not_attempted"},
                "validation_result": {"attempted": True, "passed": True, "returncode": 0},
                "cleanup_result": {"cleaned": True},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    daemon = PortalImplementationDaemon(
        todo_path=todo_path,
        state_path=state_dir / "agent_chat_task_state.json",
        strategy_path=state_dir / "agent_chat_strategy.json",
        events_path=events_path,
        repo_root=repo_root,
        task_header_prefix="AGENT-",
    )

    result = daemon.run_once()

    assert result["active_task_id"] == "AGENT-010"


def test_daemon_retries_failed_worktree_merge_when_main_is_clean(tmp_path):
    repo_root = tmp_path / "repo"
    todo_path = repo_root / "agent_todo.md"
    state_dir = tmp_path / "agent_state"
    fake_worker = repo_root / "fake_worker.py"
    repo_root.mkdir(parents=True)
    write_agent_todo(todo_path)
    fake_worker.write_text(
        f"""
from pathlib import Path

main_repo = Path({str(repo_root)!r})
Path("docs").mkdir(exist_ok=True)
Path("docs/agent.md").write_text("implemented in worktree", encoding="utf-8")
(main_repo / "docs").mkdir(exist_ok=True)
(main_repo / "docs" / "agent.md").write_text("dirty main copy", encoding="utf-8")
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
        worktree_root=tmp_path / "worktrees",
    )

    first_result = daemon.run_once()
    first_implementation = first_result["implementation_result"]

    assert first_implementation["merge_result"]["merged"] is False
    assert first_implementation["merge_result"]["reason"] == "main_checkout_dirty_conflict"
    assert Path(first_implementation["worktree_path"]).exists()
    assert subprocess.run(
        ["git", "rev-parse", "--verify", first_implementation["branch"]],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    ).returncode == 0

    (repo_root / "docs" / "agent.md").unlink()
    daemon.implement = False
    second_result = daemon.run_once()
    reconciliation = second_result["merge_reconciliation"]

    assert reconciliation
    assert reconciliation[0]["resolved"] is True
    assert reconciliation[0]["merge_result"]["merged"] is True
    assert reconciliation[0]["cleanup_result"]["cleaned"] is True
    assert second_result["completed_count"] == 1
    assert (repo_root / "docs" / "agent.md").read_text(encoding="utf-8") == "implemented in worktree"
    assert not Path(first_implementation["worktree_path"]).exists()
    assert subprocess.run(
        ["git", "rev-parse", "--verify", first_implementation["branch"]],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    ).returncode != 0


def test_daemon_reconciles_historical_failed_merge_that_already_landed(tmp_path):
    repo_root = tmp_path / "repo"
    todo_path = repo_root / "agent_todo.md"
    state_dir = tmp_path / "agent_state"
    events_path = state_dir / "agent_chat_events.jsonl"
    repo_root.mkdir(parents=True)
    write_agent_todo(todo_path)
    (repo_root / "docs").mkdir()
    (repo_root / "docs" / "agent.md").write_text("landed\n", encoding="utf-8")
    init_git_repo(repo_root)
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    events_path.parent.mkdir(parents=True, exist_ok=True)
    events_path.write_text(
        json.dumps(
            {
                "type": "implementation_finished",
                "task_id": "AGENT-000",
                "attempt": 1,
                "returncode": 1,
                "worktree_path": str(tmp_path / "missing-worktree"),
                "branch": "implementation/missing",
                "implementation_commit": head,
                "merge_result": {"attempted": True, "merged": False, "returncode": 2},
                "validation_result": {"attempted": True, "passed": True, "returncode": 0},
                "cleanup_result": {"cleaned": False, "reason": "not_attempted"},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    daemon = PortalImplementationDaemon(
        todo_path=todo_path,
        state_path=state_dir / "agent_chat_task_state.json",
        strategy_path=state_dir / "agent_chat_strategy.json",
        events_path=events_path,
        repo_root=repo_root,
        task_header_prefix="AGENT-",
    )

    result = daemon.run_once()
    second_result = daemon.run_once()

    assert result["merge_reconciliation"][0]["resolved"] is True
    assert result["completed_count"] == 1
    assert "AGENT-000" in PortalTaskState.load(state_dir / "agent_chat_task_state.json").completed_task_ids
    assert second_result["merge_reconciliation"] == []


def test_daemon_links_shared_node_modules_into_ephemeral_worktree(tmp_path):
    repo_root = tmp_path / "repo"
    todo_path = repo_root / "agent_todo.md"
    state_dir = tmp_path / "agent_state"
    fake_worker = repo_root / "fake_worker.py"
    validate_worker = repo_root / "validate_node_modules.py"
    repo_root.mkdir(parents=True)
    (repo_root / "wallet_interface" / "ui" / "node_modules" / "@xenova" / "transformers").mkdir(parents=True)
    todo_path.write_text(
        """
# Agent Todo

## AGENT-000 Control Plane
- Status: todo
- Priority: P0
- Track: platform
- Depends on: none
- Outputs: docs/agent.md
- Validation: python validate_node_modules.py
- Acceptance: agent control plane exists
""".strip()
        + "\n",
        encoding="utf-8",
    )
    fake_worker.write_text(
        """
from pathlib import Path

Path("docs").mkdir(exist_ok=True)
Path("docs/agent.md").write_text("implemented in worktree", encoding="utf-8")
""".strip()
        + "\n",
        encoding="utf-8",
    )
    validate_worker.write_text(
        """
from pathlib import Path

path = Path("wallet_interface/ui/node_modules/@xenova/transformers")
assert path.exists()
assert path.is_dir()
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
        worktree_root=tmp_path / "worktrees",
    )

    result = daemon.run_once()
    implementation = result["implementation_result"]

    assert implementation["returncode"] == 0
    assert implementation["validation_result"]["passed"] is True
    assert implementation["merge_result"]["merged"] is True
    assert implementation["cleanup_result"]["cleaned"] is True
    assert (repo_root / "docs" / "agent.md").read_text(encoding="utf-8") == "implemented in worktree"


def test_daemon_relinks_shared_node_modules_before_validation(tmp_path):
    repo_root = tmp_path / "repo"
    todo_path = repo_root / "agent_todo.md"
    state_dir = tmp_path / "agent_state"
    fake_worker = repo_root / "fake_worker.py"
    validate_worker = repo_root / "validate_node_modules.py"
    shared_module = repo_root / "wallet_interface" / "ui" / "node_modules" / "@xenova" / "transformers"
    repo_root.mkdir(parents=True)
    shared_module.mkdir(parents=True)
    (shared_module / "package.json").write_text('{"name":"@xenova/transformers"}\n', encoding="utf-8")
    todo_path.write_text(
        """
# Agent Todo

## AGENT-000 Control Plane
- Status: todo
- Priority: P0
- Track: platform
- Depends on: none
- Outputs: docs/agent.md
- Validation: python validate_node_modules.py
- Acceptance: agent control plane exists
""".strip()
        + "\n",
        encoding="utf-8",
    )
    fake_worker.write_text(
        """
from pathlib import Path
import shutil

node_modules = Path("wallet_interface/ui/node_modules")
if node_modules.is_symlink():
    node_modules.unlink()
elif node_modules.exists():
    shutil.rmtree(node_modules)
node_modules.mkdir(parents=True)
Path("docs").mkdir(exist_ok=True)
Path("docs/agent.md").write_text("implemented in worktree", encoding="utf-8")
""".strip()
        + "\n",
        encoding="utf-8",
    )
    validate_worker.write_text(
        """
from pathlib import Path

path = Path("wallet_interface/ui/node_modules/@xenova/transformers/package.json")
assert path.exists()
assert path.read_text(encoding="utf-8").strip() == '{"name":"@xenova/transformers"}'
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
        worktree_root=tmp_path / "worktrees",
    )

    result = daemon.run_once()
    implementation = result["implementation_result"]

    assert implementation["returncode"] == 0
    assert implementation["validation_result"]["passed"] is True
    assert implementation["commit_result"]["committed"] is True
    assert implementation["merge_result"]["merged"] is True


def test_daemon_replaces_preexisting_shared_node_modules_directory_with_symlink(tmp_path):
    repo_root = tmp_path / "repo"
    todo_path = repo_root / "agent_todo.md"
    state_dir = tmp_path / "agent_state"
    repo_root.mkdir(parents=True)
    write_agent_todo(todo_path)
    source = repo_root / "wallet_interface" / "ui" / "node_modules" / "@xenova" / "transformers"
    source.mkdir(parents=True)
    worktree = tmp_path / "worktree"
    target = worktree / "wallet_interface" / "ui" / "node_modules"
    target.mkdir(parents=True)
    (target / "stale.txt").write_text("stale", encoding="utf-8")

    daemon = PortalImplementationDaemon(
        todo_path=todo_path,
        state_path=state_dir / "agent_chat_task_state.json",
        strategy_path=state_dir / "agent_chat_strategy.json",
        events_path=state_dir / "agent_chat_events.jsonl",
        repo_root=repo_root,
        task_header_prefix="AGENT-",
    )

    daemon._link_shared_worktree_paths(worktree)

    assert target.is_symlink()
    assert target.resolve() == (repo_root / "wallet_interface" / "ui" / "node_modules").resolve()
    assert (target / "@xenova" / "transformers").is_dir()


def test_daemon_shared_node_modules_link_does_not_create_baseline_commit(tmp_path):
    repo_root = tmp_path / "repo"
    todo_path = repo_root / "agent_todo.md"
    state_dir = tmp_path / "agent_state"
    repo_root.mkdir(parents=True)
    write_agent_todo(todo_path)
    tracked_file = repo_root / "wallet_interface" / "ui" / "node_modules" / "@xenova" / "transformers" / "package.json"
    tracked_file.parent.mkdir(parents=True, exist_ok=True)
    tracked_file.write_text('{"name":"@xenova/transformers"}\n', encoding="utf-8")
    init_git_repo(repo_root)
    head_before = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    daemon = PortalImplementationDaemon(
        todo_path=todo_path,
        state_path=state_dir / "agent_chat_task_state.json",
        strategy_path=state_dir / "agent_chat_strategy.json",
        events_path=state_dir / "agent_chat_events.jsonl",
        repo_root=repo_root,
        task_header_prefix="AGENT-",
        worktree_root=tmp_path / "worktrees",
    )

    baseline_ref = daemon._create_seeded_worktree(tmp_path / "worktree", "implementation/test-baseline")

    assert baseline_ref == head_before


def test_daemon_worktree_starts_from_committed_head_without_dirty_workspace_seed(tmp_path):
    repo_root = tmp_path / "repo"
    todo_path = repo_root / "agent_todo.md"
    state_dir = tmp_path / "agent_state"
    repo_root.mkdir(parents=True)
    write_agent_todo(todo_path)
    (repo_root / "docs").mkdir()
    dirty_doc = repo_root / "docs" / "dirty.md"
    dirty_doc.write_text("committed\n", encoding="utf-8")
    init_git_repo(repo_root)
    dirty_doc.write_text("uncommitted\n", encoding="utf-8")

    daemon = PortalImplementationDaemon(
        todo_path=todo_path,
        state_path=state_dir / "agent_chat_task_state.json",
        strategy_path=state_dir / "agent_chat_strategy.json",
        events_path=state_dir / "agent_chat_events.jsonl",
        repo_root=repo_root,
        task_header_prefix="AGENT-",
        worktree_root=tmp_path / "worktrees",
    )

    worktree = tmp_path / "worktree"
    baseline_ref = daemon._create_seeded_worktree(worktree, "implementation/test-clean-baseline")
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=worktree,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    assert baseline_ref == subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert (worktree / "docs" / "dirty.md").read_text(encoding="utf-8") == "committed\n"
    assert status == ""


def test_daemon_commit_restores_ephemeral_paths_before_staging(tmp_path):
    repo_root = tmp_path / "repo"
    todo_path = repo_root / "agent_todo.md"
    state_dir = tmp_path / "agent_state"
    repo_root.mkdir(parents=True)
    write_agent_todo(todo_path)
    tracked_module = repo_root / "wallet_interface" / "ui" / "node_modules" / "@xenova" / "transformers" / "package.json"
    tracked_module.parent.mkdir(parents=True, exist_ok=True)
    tracked_module.write_text('{"name":"@xenova/transformers"}\n', encoding="utf-8")
    tracked_dist = repo_root / "wallet_interface" / "ui" / "dist" / "index.html"
    tracked_dist.parent.mkdir(parents=True, exist_ok=True)
    tracked_dist.write_text("<html>stable</html>\n", encoding="utf-8")
    tracked_artifact = (
        repo_root
        / "wallet_interface"
        / "ui"
        / "artifacts"
        / "ui-screenshots"
        / "latest"
        / "desktop"
        / "home.png"
    )
    tracked_artifact.parent.mkdir(parents=True, exist_ok=True)
    tracked_artifact.write_bytes(b"png")
    init_git_repo(repo_root)

    daemon = PortalImplementationDaemon(
        todo_path=todo_path,
        state_path=state_dir / "agent_chat_task_state.json",
        strategy_path=state_dir / "agent_chat_strategy.json",
        events_path=state_dir / "agent_chat_events.jsonl",
        repo_root=repo_root,
        task_header_prefix="AGENT-",
        worktree_root=tmp_path / "worktrees",
    )

    worktree = tmp_path / "worktree"
    daemon._create_seeded_worktree(worktree, "implementation/test-commit-restore")
    (worktree / "docs").mkdir(exist_ok=True)
    (worktree / "docs" / "agent.md").write_text("implemented", encoding="utf-8")
    (worktree / "wallet_interface" / "ui" / "dist" / "index.html").write_text("<html>generated</html>\n", encoding="utf-8")
    (worktree / "wallet_interface" / "ui" / "artifacts" / "ui-screenshots" / "latest" / "desktop" / "home.png").unlink()

    task = parse_task_file(todo_path, "## AGENT-")[0]
    commit_result = daemon._commit_worktree_changes(worktree, task, 1)
    changed_paths = subprocess.run(
        ["git", "show", "--name-only", "--format=", commit_result["commit"]],
        cwd=worktree,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()

    assert commit_result["committed"] is True
    assert changed_paths == ["docs/agent.md"]


def test_daemon_skips_duplicate_implementation_when_prior_worktree_process_is_live(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    todo_path = repo_root / "agent_todo.md"
    state_dir = tmp_path / "agent_state"
    repo_root.mkdir(parents=True)
    write_agent_todo(todo_path)
    events_path = state_dir / "agent_chat_events.jsonl"
    events_path.parent.mkdir(parents=True, exist_ok=True)
    events_path.write_text(
        json.dumps(
            {
                "type": "implementation_started",
                "timestamp": "2026-05-05T02:39:54.229904+00:00",
                "task_id": "AGENT-000",
                "attempt": 1,
                "worktree_path": "/tmp/existing-worktree",
                "command": ["/usr/local/bin/codex", "exec", "--full-auto", "-C", "/tmp/existing-worktree", "-"],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    daemon = PortalImplementationDaemon(
        todo_path=todo_path,
        state_path=state_dir / "agent_chat_task_state.json",
        strategy_path=state_dir / "agent_chat_strategy.json",
        events_path=events_path,
        repo_root=repo_root,
        task_header_prefix="AGENT-",
        implement=True,
        implementation_command=f"python {repo_root / 'missing.py'}",
    )
    monkeypatch.setattr(
        daemon,
        "_list_process_commands",
        lambda: ["node /usr/local/bin/codex exec --full-auto -C /tmp/existing-worktree -"],
    )

    task = parse_task_file(todo_path, "## AGENT-")[0]
    result = daemon._run_implementation(task, PortalTaskState())

    assert result["skipped"] is True
    assert result["reason"] == "inflight_process"
    assert result["worktree_path"] == "/tmp/existing-worktree"
    assert not (state_dir / "implementation.lock").exists()


def test_daemon_clears_stale_lock_before_starting_new_implementation(tmp_path):
    repo_root = tmp_path / "repo"
    todo_path = repo_root / "agent_todo.md"
    state_dir = tmp_path / "agent_state"
    fake_worker = repo_root / "fake_worker.py"
    output = repo_root / "docs" / "agent.md"
    repo_root.mkdir(parents=True)
    write_agent_todo(todo_path)
    fake_worker.write_text(
        """
from pathlib import Path

Path("docs").mkdir(exist_ok=True)
Path("docs/agent.md").write_text("implemented", encoding="utf-8")
""".strip()
        + "\n",
        encoding="utf-8",
    )
    stale_lock = state_dir / "implementation.lock"
    stale_lock.parent.mkdir(parents=True, exist_ok=True)
    stale_lock.write_text("stale\n", encoding="utf-8")

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

    task = parse_task_file(todo_path, "## AGENT-")[0]
    result = daemon._run_implementation(task, PortalTaskState())

    assert result["returncode"] == 0
    assert output.read_text(encoding="utf-8") == "implemented"
    assert not stale_lock.exists()


def test_daemon_preserves_live_lock_and_skips_duplicate_implementation(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    todo_path = repo_root / "agent_todo.md"
    state_dir = tmp_path / "agent_state"
    repo_root.mkdir(parents=True)
    write_agent_todo(todo_path)
    live_lock = state_dir / "implementation.lock"
    live_lock.parent.mkdir(parents=True, exist_ok=True)
    live_lock.write_text(
        json.dumps(
            {
                "kind": "implementation",
                "pid": 43210,
                "owner_script": "portal_implementation_daemon.py",
                "state_dir": str(state_dir.resolve()),
                "task_id": "AGENT-000",
                "attempt": 2,
                "started_at": "2026-05-05T00:00:00+00:00",
            }
        ),
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
        implementation_command=f"python {repo_root / 'missing.py'}",
    )
    monkeypatch.setattr("scripts.portal_implementation_daemon.process_is_running", lambda pid: pid == 43210)
    monkeypatch.setattr(
        "scripts.portal_implementation_daemon.process_command_line",
        lambda pid: f"python portal_implementation_daemon.py --state-dir {state_dir}",
    )

    task = parse_task_file(todo_path, "## AGENT-")[0]
    result = daemon._run_implementation(task, PortalTaskState())

    assert result["skipped"] is True
    assert result["reason"] == "lock_exists"
    assert result["lock_owner_pid"] == 43210
    assert json.loads(live_lock.read_text(encoding="utf-8"))["pid"] == 43210


def test_daemon_validation_timeout_returns_failure(tmp_path):
    repo_root = tmp_path / "repo"
    todo_path = repo_root / "agent_todo.md"
    state_dir = tmp_path / "agent_state"
    repo_root.mkdir(parents=True)
    todo_path.write_text(
        """
# Agent Todo

## AGENT-000 Control Plane
- Status: todo
- Priority: P0
- Track: platform
- Depends on: none
- Outputs: docs/agent.md
- Validation: sleep 5
- Acceptance: agent control plane exists
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
        implementation_timeout=0.1,
    )

    task = parse_task_file(todo_path, "## AGENT-")[0]
    log_path = state_dir / "validation.log"
    result = daemon._run_validation_commands(repo_root, task, log_path)

    assert result["attempted"] is True
    assert result["passed"] is False
    assert result["returncode"] == 124
    assert result["error"] == "timeout"
    assert result["results"][0]["timed_out"] is True
    assert "validation timed out" in log_path.read_text(encoding="utf-8")


def test_daemon_load_strategy_falls_back_from_corrupt_json(tmp_path):
    repo_root = tmp_path / "repo"
    todo_path = repo_root / "agent_todo.md"
    state_dir = tmp_path / "agent_state"
    repo_root.mkdir(parents=True)
    write_agent_todo(todo_path)
    strategy_path = state_dir / "agent_chat_strategy.json"
    strategy_path.parent.mkdir(parents=True, exist_ok=True)
    strategy_path.write_text("{broken", encoding="utf-8")

    daemon = PortalImplementationDaemon(
        todo_path=todo_path,
        state_path=state_dir / "agent_chat_task_state.json",
        strategy_path=strategy_path,
        events_path=state_dir / "agent_chat_events.jsonl",
        repo_root=repo_root,
        task_header_prefix="AGENT-",
    )

    strategy = daemon.load_strategy()

    assert strategy["generation"] == 0
    assert strategy["focus_tracks"]


def test_daemon_clears_stale_merge_lock_before_merging(tmp_path):
    repo_root = tmp_path / "repo"
    todo_path = repo_root / "agent_todo.md"
    state_dir = tmp_path / "agent_state"
    repo_root.mkdir(parents=True)
    write_agent_todo(todo_path)
    init_git_repo(repo_root)

    daemon = PortalImplementationDaemon(
        todo_path=todo_path,
        state_path=state_dir / "agent_chat_task_state.json",
        strategy_path=state_dir / "agent_chat_strategy.json",
        events_path=state_dir / "agent_chat_events.jsonl",
        repo_root=repo_root,
        task_header_prefix="AGENT-",
        worktree_root=tmp_path / "worktrees",
    )

    worktree = tmp_path / "worktree"
    branch_name = "implementation/test-stale-merge-lock"
    daemon._create_seeded_worktree(worktree, branch_name)
    (worktree / "docs").mkdir(exist_ok=True)
    (worktree / "docs" / "agent.md").write_text("implemented", encoding="utf-8")
    task = parse_task_file(todo_path, "## AGENT-")[0]
    commit_result = daemon._commit_worktree_changes(worktree, task, 1)
    merge_lock = daemon._repo_merge_lock_path()
    merge_lock.parent.mkdir(parents=True, exist_ok=True)
    merge_lock.write_text("stale\n", encoding="utf-8")

    result = daemon._merge_branch_to_main(branch_name, task, 1)

    assert commit_result["committed"] is True
    assert result["attempted"] is True
    assert result["merged"] is True
    assert not merge_lock.exists()
    daemon._cleanup_merged_worktree(worktree, branch_name)


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


def test_supervisor_starts_managed_daemon_from_repo_root(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    todo_path = repo_root / "todo.md"
    state_dir = repo_root / "state"
    repo_root.mkdir(parents=True)
    write_todo(todo_path)
    captured: dict[str, object] = {}

    class FakeProcess:
        pid = 12345

        def poll(self) -> int | None:
            return None

    def fake_popen(command: list[str], **kwargs: object) -> FakeProcess:
        captured["command"] = command
        captured["kwargs"] = kwargs
        return FakeProcess()

    monkeypatch.setattr(supervisor_module.subprocess, "Popen", fake_popen)
    supervisor = PortalImplementationSupervisor(
        PortalSupervisorConfig(
            todo_path=todo_path,
            state_path=state_dir / "portal_task_state.json",
            strategy_path=state_dir / "portal_strategy.json",
            events_path=state_dir / "portal_supervisor_events.jsonl",
            state_dir=state_dir,
            implement=True,
            daemon_interval=60.0,
        )
    )

    process = supervisor._start_daemon()

    assert process.pid == 12345
    assert captured["kwargs"]["cwd"] == supervisor_module.REPO_ROOT
    assert (state_dir / "portal_managed_daemon.pid").read_text(encoding="utf-8") == "12345\n"


def test_supervisor_load_strategy_falls_back_from_corrupt_json(tmp_path):
    repo_root = tmp_path / "repo"
    todo_path = repo_root / "todo.md"
    state_dir = repo_root / "state"
    repo_root.mkdir(parents=True)
    write_todo(todo_path)
    strategy_path = state_dir / "portal_strategy.json"
    strategy_path.parent.mkdir(parents=True, exist_ok=True)
    strategy_path.write_text("{broken", encoding="utf-8")

    supervisor = PortalImplementationSupervisor(
        PortalSupervisorConfig(
            todo_path=todo_path,
            state_path=state_dir / "portal_task_state.json",
            strategy_path=strategy_path,
            events_path=state_dir / "portal_supervisor_events.jsonl",
            state_dir=state_dir,
        )
    )

    strategy = supervisor._load_strategy()

    assert strategy["generation"] == 0
    assert strategy["focus_tracks"]


def test_supervisor_adopts_existing_managed_daemon_pid(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    todo_path = repo_root / "todo.md"
    state_dir = repo_root / "state"
    repo_root.mkdir(parents=True)
    write_todo(todo_path)
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "portal_managed_daemon.pid").write_text("43210\n", encoding="utf-8")

    monkeypatch.setattr(supervisor_module, "process_is_running", lambda pid: pid == 43210)
    monkeypatch.setattr(
        supervisor_module,
        "process_command_line",
        lambda pid: (
            f"python portal_implementation_daemon.py --todo-path {todo_path} "
            f"--state-dir {state_dir} --state-prefix portal --implement"
        ),
    )

    supervisor = PortalImplementationSupervisor(
        PortalSupervisorConfig(
            todo_path=todo_path,
            state_path=state_dir / "portal_task_state.json",
            strategy_path=state_dir / "portal_strategy.json",
            events_path=state_dir / "portal_supervisor_events.jsonl",
            state_dir=state_dir,
            state_prefix="portal",
        )
    )

    adopted = supervisor._adopt_existing_daemon()

    assert adopted is not None
    assert adopted.pid == 43210


def test_supervisor_rejects_managed_daemon_with_wrong_implement_mode(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    todo_path = repo_root / "todo.md"
    state_dir = repo_root / "state"
    repo_root.mkdir(parents=True)
    write_todo(todo_path)
    state_dir.mkdir(parents=True, exist_ok=True)
    pid_path = state_dir / "portal_managed_daemon.pid"
    pid_path.write_text("43210\n", encoding="utf-8")

    monkeypatch.setattr(supervisor_module, "process_is_running", lambda pid: pid == 43210)
    monkeypatch.setattr(
        supervisor_module,
        "process_command_line",
        lambda pid: (
            f"python portal_implementation_daemon.py --todo-path {todo_path} "
            f"--state-dir {state_dir} --state-prefix portal"
        ),
    )

    supervisor = PortalImplementationSupervisor(
        PortalSupervisorConfig(
            todo_path=todo_path,
            state_path=state_dir / "portal_task_state.json",
            strategy_path=state_dir / "portal_strategy.json",
            events_path=state_dir / "portal_supervisor_events.jsonl",
            state_dir=state_dir,
            state_prefix="portal",
            implement=True,
        )
    )

    adopted = supervisor._adopt_existing_daemon()

    assert adopted is None
    assert not pid_path.exists()
