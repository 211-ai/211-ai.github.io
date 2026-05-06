from __future__ import annotations

from pathlib import Path

from ipfs_datasets_py.optimizers.todo_daemon.implementation_daemon import TodoImplementationDaemon
from ipfs_datasets_py.optimizers.todo_daemon.implementation_supervisor import TodoImplementationSupervisor
from scripts.portal_implementation_daemon import PortalImplementationDaemon
from scripts.portal_implementation_supervisor import PortalImplementationSupervisor
from scripts.wallet_implementation_daemon import (
    DEFAULT_STATE_DIR,
    DEFAULT_TODO_PATH,
    WALLET_STATE_PREFIX,
    WALLET_TASK_PREFIX,
    WalletImplementationDaemon,
    parse_args as parse_daemon_args,
)
from scripts.wallet_implementation_supervisor import (
    WalletImplementationSupervisor,
    build_supervisor,
    parse_args as parse_supervisor_args,
)


def write_todo(path: Path) -> None:
    path.write_text(
        """
# Test Wallet Todo

## WALLET-000 Control Plane
- Status: completed
- Completion: artifact
- Priority: P0
- Track: ops
- Depends on: none
- Outputs: docs/control.md
- Validation: python -c "print('control-ok')"
- Acceptance: control plane exists

## WALLET-110 Release Gate
- Status: todo
- Completion: evidence
- Priority: P0
- Track: ops
- Depends on: WALLET-000
- Outputs: docs/signoff.md
- Validation: python -c "print('release-ok')"
- Acceptance: release evidence exists
""".strip()
        + "\n",
        encoding="utf-8",
    )


def test_wallet_wrappers_use_shared_todo_stack() -> None:
    assert issubclass(WalletImplementationDaemon, PortalImplementationDaemon)
    assert issubclass(WalletImplementationDaemon, TodoImplementationDaemon)
    assert issubclass(WalletImplementationSupervisor, PortalImplementationSupervisor)
    assert issubclass(WalletImplementationSupervisor, TodoImplementationSupervisor)


def test_wallet_default_paths_and_prefixes_are_stable() -> None:
    daemon_args = parse_daemon_args([])
    supervisor_args = parse_supervisor_args([])

    assert daemon_args.todo_path == DEFAULT_TODO_PATH
    assert daemon_args.state_dir == DEFAULT_STATE_DIR
    assert daemon_args.task_prefix == WALLET_TASK_PREFIX
    assert daemon_args.state_prefix == WALLET_STATE_PREFIX
    assert supervisor_args.todo_path == DEFAULT_TODO_PATH
    assert supervisor_args.state_dir == DEFAULT_STATE_DIR
    assert supervisor_args.task_prefix == WALLET_TASK_PREFIX
    assert supervisor_args.state_prefix == WALLET_STATE_PREFIX


def test_wallet_supervisor_builds_correct_daemon_script(tmp_path: Path) -> None:
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
                "--no-implement",
            ]
        )
    )
    loop_config = supervisor.build_supervisor_loop_config()

    assert loop_config.spec.task_board_path == todo_path
    assert loop_config.spec.child_pid_path == state_dir / f"{WALLET_STATE_PREFIX}_managed_daemon.pid"
    assert Path(loop_config.command[1]).name == "wallet_implementation_daemon.py"
    assert "--implement" not in loop_config.command


def test_wallet_daemon_can_parse_and_select_ready_task(tmp_path: Path) -> None:
    todo_path = tmp_path / "todo.md"
    state_dir = tmp_path / "state"
    write_todo(todo_path)

    daemon = WalletImplementationDaemon(
        todo_path=todo_path,
        state_path=state_dir / f"{WALLET_STATE_PREFIX}_task_state.json",
        strategy_path=state_dir / f"{WALLET_STATE_PREFIX}_strategy.json",
        events_path=state_dir / f"{WALLET_STATE_PREFIX}_events.jsonl",
        repo_root=tmp_path,
        task_header_prefix=WALLET_TASK_PREFIX,
        implement=False,
        use_ephemeral_worktree=False,
    )

    result = daemon.run_once()

    assert result["active_task_id"] == "WALLET-110"
    assert result["completed_count"] == 1
    assert result["ready_count"] == 1


def test_wallet_real_backlog_selects_target_release_gate(tmp_path: Path) -> None:
    state_dir = tmp_path / "state"
    daemon = WalletImplementationDaemon(
        todo_path=DEFAULT_TODO_PATH,
        state_path=state_dir / f"{WALLET_STATE_PREFIX}_task_state.json",
        strategy_path=state_dir / f"{WALLET_STATE_PREFIX}_strategy.json",
        events_path=state_dir / f"{WALLET_STATE_PREFIX}_events.jsonl",
        repo_root=Path.cwd(),
        task_header_prefix=WALLET_TASK_PREFIX,
        implement=False,
        use_ephemeral_worktree=False,
    )

    result = daemon.run_once()

    assert result["active_task_id"] == "WALLET-110"
    assert result["completed_count"] >= 10
    assert "WALLET-110" in (state_dir / f"{WALLET_STATE_PREFIX}_task_state.json").read_text(encoding="utf-8")
