from __future__ import annotations

from pathlib import Path

from ipfs_datasets_py.optimizers.todo_daemon.implementation_daemon import TodoImplementationDaemon
from ipfs_datasets_py.optimizers.todo_daemon.implementation_supervisor import TodoImplementationSupervisor
from scripts.portal_implementation_daemon import PortalImplementationDaemon
from scripts.portal_implementation_supervisor import PortalImplementationSupervisor
from scripts.portland_graphrag_implementation_daemon import (
    DEFAULT_STATE_DIR,
    DEFAULT_TODO_PATH,
    GRAPHRAG_STATE_PREFIX,
    GRAPHRAG_TASK_PREFIX,
    PortlandGraphRagImplementationDaemon,
    parse_args as parse_daemon_args,
)
from scripts.portland_graphrag_implementation_supervisor import (
    PortlandGraphRagImplementationSupervisor,
    build_supervisor,
    parse_args as parse_supervisor_args,
)


def write_todo(path: Path) -> None:
    path.write_text(
        """
# Test GraphRAG Todo

## GRAPHRAG-000 Control Plane
- Status: completed
- Completion: artifact
- Priority: P0
- Track: platform
- Depends on: none
- Outputs: docs/control.md
- Validation: python -c "print('control-ok')"
- Acceptance: control plane exists

## GRAPHRAG-020 Runtime Parity
- Status: todo
- Completion: artifact
- Priority: P0
- Track: runtime
- Depends on: GRAPHRAG-000
- Outputs: src/runtime.ts
- Validation: python -c "print('runtime-ok')"
- Acceptance: runtime parity exists
""".strip()
        + "\n",
        encoding="utf-8",
    )


def test_portland_graphrag_wrappers_use_shared_todo_stack() -> None:
    assert issubclass(PortlandGraphRagImplementationDaemon, PortalImplementationDaemon)
    assert issubclass(PortlandGraphRagImplementationDaemon, TodoImplementationDaemon)
    assert issubclass(PortlandGraphRagImplementationSupervisor, PortalImplementationSupervisor)
    assert issubclass(PortlandGraphRagImplementationSupervisor, TodoImplementationSupervisor)


def test_portland_graphrag_default_paths_and_prefixes_are_stable() -> None:
    daemon_args = parse_daemon_args([])
    supervisor_args = parse_supervisor_args([])

    assert daemon_args.todo_path == DEFAULT_TODO_PATH
    assert daemon_args.state_dir == DEFAULT_STATE_DIR
    assert daemon_args.task_prefix == GRAPHRAG_TASK_PREFIX
    assert daemon_args.state_prefix == GRAPHRAG_STATE_PREFIX
    assert supervisor_args.todo_path == DEFAULT_TODO_PATH
    assert supervisor_args.state_dir == DEFAULT_STATE_DIR
    assert supervisor_args.task_prefix == GRAPHRAG_TASK_PREFIX
    assert supervisor_args.state_prefix == GRAPHRAG_STATE_PREFIX


def test_portland_graphrag_supervisor_builds_correct_daemon_script(tmp_path: Path) -> None:
    todo_path = tmp_path / "todo.md"
    state_dir = tmp_path / "state"
    write_todo(todo_path)

    supervisor = build_supervisor(
        parse_supervisor_args(
            [
                "--todo-path",
                str(todo_path),
                "--state-dir",
                str(state_dir),
            ]
        )
    )
    loop_config = supervisor.build_supervisor_loop_config()

    assert loop_config.spec.task_board_path == todo_path
    assert loop_config.spec.child_pid_path == state_dir / f"{GRAPHRAG_STATE_PREFIX}_managed_daemon.pid"
    assert Path(loop_config.command[1]).name == "portland_graphrag_implementation_daemon.py"


def test_portland_graphrag_daemon_can_parse_and_select_ready_task(tmp_path: Path) -> None:
    todo_path = tmp_path / "todo.md"
    state_dir = tmp_path / "state"
    write_todo(todo_path)

    daemon = PortlandGraphRagImplementationDaemon(
        todo_path=todo_path,
        state_path=state_dir / f"{GRAPHRAG_STATE_PREFIX}_task_state.json",
        strategy_path=state_dir / f"{GRAPHRAG_STATE_PREFIX}_strategy.json",
        events_path=state_dir / f"{GRAPHRAG_STATE_PREFIX}_events.jsonl",
        repo_root=tmp_path,
        task_header_prefix=GRAPHRAG_TASK_PREFIX,
        implement=False,
        use_ephemeral_worktree=False,
    )

    result = daemon.run_once()

    assert result["active_task_id"] == "GRAPHRAG-020"
    assert result["completed_count"] == 1
    assert result["ready_count"] == 1
