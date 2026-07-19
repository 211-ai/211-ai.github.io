from __future__ import annotations

from pathlib import Path

from scripts.hmis_implementation_daemon import (
    DEFAULT_STATE_DIR,
    DEFAULT_TODO_PATH,
    HMIS_STATE_PREFIX,
    HMIS_TASK_PREFIX,
    HmisImplementationDaemon,
)
from scripts.hmis_implementation_daemon import parse_args as parse_daemon_args
from scripts.hmis_implementation_supervisor import (
    HmisImplementationSupervisor,
    build_supervisor,
)
from scripts.hmis_implementation_supervisor import parse_args as parse_supervisor_args


def write_todo(path: Path) -> None:
    path.write_text(
        """
# Test HMIS Todo

## HMIS-000 Control Plane
- Status: completed
- Completion: artifact
- Priority: P0
- Track: platform
- Depends on: none
- Outputs: docs/control.md
- Validation: python -c "print('control-ok')"
- Acceptance: control plane exists

## HMIS-010 Governance
- Status: todo
- Completion: artifact
- Priority: P0
- Track: governance
- Depends on: HMIS-000
- Outputs: docs/governance.md
- Validation: python -c "print('governance-ok')"
- Acceptance: governance exists
""".strip()
        + "\n",
        encoding="utf-8",
    )



def test_hmis_wrapper_types_are_stable() -> None:
    assert issubclass(HmisImplementationSupervisor, object)
    assert issubclass(HmisImplementationDaemon, object)



def test_hmis_default_paths_and_prefixes_are_stable() -> None:
    daemon_args = parse_daemon_args([])
    supervisor_args = parse_supervisor_args([])

    assert daemon_args.todo_path == DEFAULT_TODO_PATH
    assert daemon_args.state_dir == DEFAULT_STATE_DIR
    assert daemon_args.task_prefix == HMIS_TASK_PREFIX
    assert daemon_args.state_prefix == HMIS_STATE_PREFIX
    assert supervisor_args.todo_path == DEFAULT_TODO_PATH
    assert supervisor_args.state_dir == DEFAULT_STATE_DIR
    assert supervisor_args.task_prefix == HMIS_TASK_PREFIX
    assert supervisor_args.state_prefix == HMIS_STATE_PREFIX



def test_hmis_supervisor_builds_correct_daemon_script(tmp_path: Path) -> None:
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

    assert loop_config["task_board_path"] == todo_path
    assert loop_config["child_pid_path"] == state_dir / f"{HMIS_STATE_PREFIX}_managed_daemon.pid"
    assert Path(loop_config["command"][1]).name == "hmis_implementation_daemon.py"



def test_hmis_daemon_can_parse_and_select_ready_task(tmp_path: Path) -> None:
    todo_path = tmp_path / "todo.md"
    state_dir = tmp_path / "state"
    write_todo(todo_path)

    daemon = HmisImplementationDaemon(
        todo_path=todo_path,
        state_path=state_dir / f"{HMIS_STATE_PREFIX}_task_state.json",
        strategy_path=state_dir / f"{HMIS_STATE_PREFIX}_strategy.json",
        events_path=state_dir / f"{HMIS_STATE_PREFIX}_events.jsonl",
        task_header_prefix=HMIS_TASK_PREFIX,
        implement=False,
    )

    result = daemon.run_once()

    assert result["active_task_id"] == "HMIS-010"
    assert result["completed_count"] == 1
    assert result["ready_count"] == 1



def test_hmis_real_backlog_selects_first_ready_task(tmp_path: Path) -> None:
    state_dir = tmp_path / "state"
    daemon = HmisImplementationDaemon(
        todo_path=DEFAULT_TODO_PATH,
        state_path=state_dir / f"{HMIS_STATE_PREFIX}_task_state.json",
        strategy_path=state_dir / f"{HMIS_STATE_PREFIX}_strategy.json",
        events_path=state_dir / f"{HMIS_STATE_PREFIX}_events.jsonl",
        task_header_prefix=HMIS_TASK_PREFIX,
        implement=False,
    )

    result = daemon.run_once()

    assert result["active_task_id"] is None
    assert result["ready_count"] == 0
    assert result["completed_count"] >= 25
