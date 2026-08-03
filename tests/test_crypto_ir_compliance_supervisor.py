from __future__ import annotations

import json
import os
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "crypto_ir_compliance_supervisor.sh"
SUPERVISOR_MODULE = (
    "ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_supervisor"
)


def _run_library(
    body: str,
    *,
    environment: dict[str, str] | None = None,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["CRYPTO_IR_COMPLIANCE_LIB_ONLY"] = "1"
    env.update(environment or {})
    return subprocess.run(
        [
            "bash",
            "-c",
            'source "$1"\nset +e\n' + body,
            "bash",
            str(SCRIPT),
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
        cwd=cwd,
    )


def _fake_systemctl(tmp_path: Path) -> Path:
    path = tmp_path / "systemctl"
    path.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
if [[ "${FAKE_SYSTEMD_STATE:-active}" == "error" ]]; then
  exit 1
fi
if [[ " $* " == *" show "* ]]; then
  case "${FAKE_SYSTEMD_STATE:-active}" in
    active)
      printf 'LoadState=loaded\\nActiveState=active\\nSubState=running\\nMainPID=%s\\n' "${FAKE_SERVICE_PID}"
      ;;
    activating|reloading|deactivating)
      printf 'LoadState=loaded\\nActiveState=%s\\nSubState=running\\nMainPID=%s\\n' "${FAKE_SYSTEMD_STATE}" "${FAKE_SERVICE_PID}"
      ;;
    inactive)
      printf 'LoadState=loaded\\nActiveState=inactive\\nSubState=dead\\nMainPID=0\\n'
      ;;
    missing)
      printf 'LoadState=not-found\\nActiveState=inactive\\nSubState=dead\\nMainPID=0\\n'
      ;;
  esac
  exit 0
fi
if [[ " $* " == *" stop "* ]]; then
  if [[ "${FAKE_STOP_FAIL:-0}" == "1" ]]; then
    exit 7
  fi
  printf '%s\\n' "$*" >>"${FAKE_SYSTEMCTL_LOG}"
  exit 0
fi
exit 2
""",
        encoding="utf-8",
    )
    path.chmod(0o755)
    return path


@contextmanager
def _lane_process(
    module: str,
    state_dir: Path,
    state_prefix: str,
) -> Iterator[subprocess.Popen[bytes]]:
    process = subprocess.Popen(
        [
            sys.executable,
            "-c",
            "import time; time.sleep(60)",
            "-m",
            module,
            "--state-dir",
            str(state_dir),
            "--state-prefix",
            state_prefix,
        ]
    )
    try:
        yield process
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=5)


def _service_environment(
    fake_systemctl: Path,
    log_path: Path,
    process: subprocess.Popen[bytes],
    state: str,
) -> dict[str, str]:
    return {
        "CRYPTO_IR_COMPLIANCE_SYSTEMCTL_BIN": str(fake_systemctl),
        "FAKE_SYSTEMCTL_LOG": str(log_path),
        "FAKE_SERVICE_PID": str(process.pid),
        "FAKE_SYSTEMD_STATE": state,
    }


def _write_receipt(
    lifecycle_dir: Path,
    unit_name: str,
    pid: int,
) -> Path:
    lifecycle_dir.mkdir(parents=True, exist_ok=True)
    path = lifecycle_dir / f"{unit_name}.launch.json"
    path.write_text(
        json.dumps(
            {
                "active_state": "active",
                "backend": "systemd-user",
                "pid": pid,
                "unit_name": f"{unit_name}.service",
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def test_merge_target_defaults_to_main_and_accepts_explicit_override() -> None:
    default = _run_library("printf '%s\\n' \"${MERGE_TARGET_BRANCH}\"")
    overridden = _run_library(
        "printf '%s\\n' \"${MERGE_TARGET_BRANCH}\"",
        environment={
            "CRYPTO_IR_COMPLIANCE_MERGE_TARGET_BRANCH": "reviewed/integration"
        },
    )

    assert default.returncode == 0, default.stderr
    assert default.stdout.strip() == "main"
    assert overridden.returncode == 0, overridden.stderr
    assert overridden.stdout.strip() == "reviewed/integration"


def test_systemd_identity_overrides_a_stale_pid_file(tmp_path: Path) -> None:
    fake_systemctl = _fake_systemctl(tmp_path)
    systemctl_log = tmp_path / "systemctl.log"
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    state_prefix = "lane"
    (state_dir / f"{state_prefix}_supervisor.pid").write_text(
        str(os.getpid()), encoding="utf-8"
    )
    with _lane_process(SUPERVISOR_MODULE, state_dir, state_prefix) as process:
        result = _run_library(
            'read_live_supervisor_pid "$TEST_STATE_DIR" "$TEST_STATE_PREFIX" test-unit',
            environment={
                **_service_environment(
                    fake_systemctl, systemctl_log, process, "active"
                ),
                "TEST_STATE_DIR": str(state_dir),
                "TEST_STATE_PREFIX": state_prefix,
            },
        )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == str(process.pid)


def test_stop_uses_the_exact_verified_systemd_unit(tmp_path: Path) -> None:
    fake_systemctl = _fake_systemctl(tmp_path)
    systemctl_log = tmp_path / "systemctl.log"
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    state_prefix = "lane"
    with _lane_process(SUPERVISOR_MODULE, state_dir, state_prefix) as process:
        result = _run_library(
            'request_lane_stop Test "$TEST_STATE_DIR" "$TEST_STATE_PREFIX" test-unit\n'
            'printf "rc=%s\\n" "$?"',
            environment={
                **_service_environment(
                    fake_systemctl, systemctl_log, process, "active"
                ),
                "TEST_STATE_DIR": str(state_dir),
                "TEST_STATE_PREFIX": state_prefix,
            },
        )

    assert "rc=0" in result.stdout
    assert systemctl_log.read_text(encoding="utf-8").strip() == (
        "--user stop test-unit.service"
    )


def test_systemd_bus_error_refuses_pid_fallback(tmp_path: Path) -> None:
    fake_systemctl = _fake_systemctl(tmp_path)
    systemctl_log = tmp_path / "systemctl.log"
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    state_prefix = "lane"
    with _lane_process(SUPERVISOR_MODULE, state_dir, state_prefix) as process:
        (state_dir / f"{state_prefix}_supervisor.pid").write_text(
            str(process.pid), encoding="utf-8"
        )
        result = _run_library(
            'request_lane_stop Test "$TEST_STATE_DIR" "$TEST_STATE_PREFIX" test-unit\n'
            'printf "rc=%s\\n" "$?"',
            environment={
                **_service_environment(
                    fake_systemctl, systemctl_log, process, "error"
                ),
                "TEST_STATE_DIR": str(state_dir),
                "TEST_STATE_PREFIX": state_prefix,
            },
        )
        assert process.poll() is None

    assert "rc=1" in result.stdout
    assert "refusing PID fallback" in result.stderr


def test_failed_systemd_stop_is_reported(tmp_path: Path) -> None:
    fake_systemctl = _fake_systemctl(tmp_path)
    systemctl_log = tmp_path / "systemctl.log"
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    state_prefix = "lane"
    with _lane_process(SUPERVISOR_MODULE, state_dir, state_prefix) as process:
        result = _run_library(
            'request_lane_stop Test "$TEST_STATE_DIR" "$TEST_STATE_PREFIX" test-unit\n'
            'printf "rc=%s\\n" "$?"',
            environment={
                **_service_environment(
                    fake_systemctl, systemctl_log, process, "active"
                ),
                "FAKE_STOP_FAIL": "1",
                "TEST_STATE_DIR": str(state_dir),
                "TEST_STATE_PREFIX": state_prefix,
            },
        )
        assert process.poll() is None

    assert "rc=1" in result.stdout
    assert "failed to stop" in result.stderr


def test_deactivating_durable_unit_is_treated_as_already_stopping(
    tmp_path: Path,
) -> None:
    fake_systemctl = _fake_systemctl(tmp_path)
    systemctl_log = tmp_path / "systemctl.log"
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    state_prefix = "lane"
    lifecycle_dir = tmp_path / "lifecycle"
    _write_receipt(lifecycle_dir, "test-unit", 4242)
    result = _run_library(
        'LIFECYCLE_DIR="$TEST_LIFECYCLE_DIR"\n'
        'request_lane_stop Test "$TEST_STATE_DIR" "$TEST_STATE_PREFIX" test-unit\n'
        'printf "rc=%s\\n" "$?"',
        environment={
            "CRYPTO_IR_COMPLIANCE_SYSTEMCTL_BIN": str(fake_systemctl),
            "FAKE_SYSTEMCTL_LOG": str(systemctl_log),
            "FAKE_SERVICE_PID": "0",
            "FAKE_SYSTEMD_STATE": "deactivating",
            "TEST_LIFECYCLE_DIR": str(lifecycle_dir),
            "TEST_STATE_DIR": str(state_dir),
            "TEST_STATE_PREFIX": state_prefix,
        },
    )

    assert "rc=0" in result.stdout
    assert "already stopping" in result.stdout
    assert not systemctl_log.exists()


def test_unavailable_systemctl_with_durable_receipt_fails_closed(
    tmp_path: Path,
) -> None:
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    state_prefix = "lane"
    lifecycle_dir = tmp_path / "lifecycle"
    with _lane_process(SUPERVISOR_MODULE, state_dir, state_prefix) as process:
        _write_receipt(lifecycle_dir, "test-unit", process.pid)
        (state_dir / f"{state_prefix}_supervisor.pid").write_text(
            str(process.pid), encoding="utf-8"
        )
        result = _run_library(
            'LIFECYCLE_DIR="$TEST_LIFECYCLE_DIR"\n'
            'request_lane_stop Test "$TEST_STATE_DIR" "$TEST_STATE_PREFIX" test-unit\n'
            'printf "rc=%s\\n" "$?"',
            environment={
                "CRYPTO_IR_COMPLIANCE_SYSTEMCTL_BIN": str(
                    tmp_path / "missing-systemctl"
                ),
                "TEST_LIFECYCLE_DIR": str(lifecycle_dir),
                "TEST_STATE_DIR": str(state_dir),
                "TEST_STATE_PREFIX": state_prefix,
            },
        )
        assert process.poll() is None

    assert "rc=1" in result.stdout
    assert "refusing PID fallback" in result.stderr


def test_mismatched_durable_receipt_is_rejected(tmp_path: Path) -> None:
    receipt = _write_receipt(tmp_path, "test-unit", 4242)
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    payload["unit_name"] = "different-unit.service"
    receipt.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    result = _run_library(
        'LIFECYCLE_DIR="$TEST_LIFECYCLE_DIR"\n'
        'request_lane_stop Test "$TEST_STATE_DIR" lane test-unit\n'
        'printf "rc=%s\\n" "$?"',
        environment={
            "CRYPTO_IR_COMPLIANCE_SYSTEMCTL_BIN": str(
                tmp_path / "missing-systemctl"
            ),
            "TEST_LIFECYCLE_DIR": str(tmp_path),
            "TEST_STATE_DIR": str(state_dir),
        },
    )

    assert "rc=1" in result.stdout
    assert "refusing PID fallback" in result.stderr


def test_verified_legacy_pid_fallback_stops_only_the_lane(tmp_path: Path) -> None:
    fake_systemctl = _fake_systemctl(tmp_path)
    systemctl_log = tmp_path / "systemctl.log"
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    state_prefix = "lane"
    with _lane_process(SUPERVISOR_MODULE, state_dir, state_prefix) as process:
        (state_dir / f"{state_prefix}_supervisor.pid").write_text(
            str(process.pid), encoding="utf-8"
        )
        result = _run_library(
            'request_lane_stop Test "$TEST_STATE_DIR" "$TEST_STATE_PREFIX" test-unit\n'
            'printf "rc=%s\\n" "$?"',
            environment={
                **_service_environment(
                    fake_systemctl, systemctl_log, process, "missing"
                ),
                "TEST_STATE_DIR": str(state_dir),
                "TEST_STATE_PREFIX": state_prefix,
            },
        )
        process.wait(timeout=5)

    assert "rc=0" in result.stdout
    assert not systemctl_log.exists()


def test_mismatched_legacy_pid_is_not_signalled(tmp_path: Path) -> None:
    fake_systemctl = _fake_systemctl(tmp_path)
    systemctl_log = tmp_path / "systemctl.log"
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    state_prefix = "lane"
    (state_dir / f"{state_prefix}_supervisor.pid").write_text(
        str(os.getpid()), encoding="utf-8"
    )
    result = _run_library(
        'request_lane_stop Test "$TEST_STATE_DIR" "$TEST_STATE_PREFIX" test-unit\n'
        'printf "rc=%s\\n" "$?"',
        environment={
            "CRYPTO_IR_COMPLIANCE_SYSTEMCTL_BIN": str(fake_systemctl),
            "FAKE_SYSTEMCTL_LOG": str(systemctl_log),
            "FAKE_SERVICE_PID": "0",
            "FAKE_SYSTEMD_STATE": "missing",
            "TEST_STATE_DIR": str(state_dir),
            "TEST_STATE_PREFIX": state_prefix,
        },
    )

    assert "rc=1" in result.stdout
    assert "process identity does not match" in result.stderr


def test_partial_start_rolls_back_the_first_lane(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "bundles"
    bundle_dir.mkdir()
    (bundle_dir / "index.json").write_text("{}\n", encoding="utf-8")
    graph_path = tmp_path / "graph.json"
    graph_path.write_text("{}\n", encoding="utf-8")
    rollback_path = tmp_path / "rollback"
    result = _run_library(
        """
prepare_runtime() { :; }
require_target_checkout() { :; }
require_executable() { :; }
lane_fully_running() { return 1; }
any_lane_process_running() { return 1; }
run_reconciliation_preflight() { :; }
start_codex_lane() { printf 'codex-started\\n'; }
start_grok_lane() { printf 'grok-failed\\n'; return 1; }
stop_supervisors() { printf 'rolled-back\\n' | tee "${TEST_ROLLBACK_PATH}"; }
GRAPH_PATH="${TEST_GRAPH_PATH}"
BUNDLE_DIR="${TEST_BUNDLE_DIR}"
start_supervisors
printf 'rc=%s\\n' "$?"
""",
        environment={
            "TEST_BUNDLE_DIR": str(bundle_dir),
            "TEST_GRAPH_PATH": str(graph_path),
            "TEST_ROLLBACK_PATH": str(rollback_path),
        },
    )

    assert "codex-started" in result.stdout
    assert "grok-failed" in result.stdout
    assert "rolled-back" in result.stdout
    assert "rc=1" in result.stdout
    assert rollback_path.read_text(encoding="utf-8").strip() == "rolled-back"


def test_preflight_failure_prevents_any_lane_launch(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "bundles"
    bundle_dir.mkdir()
    (bundle_dir / "index.json").write_text("{}\n", encoding="utf-8")
    graph_path = tmp_path / "graph.json"
    graph_path.write_text("{}\n", encoding="utf-8")
    attempted_path = tmp_path / "launch-attempted"
    result = _run_library(
        """
prepare_runtime() { :; }
require_target_checkout() { :; }
require_executable() { :; }
lane_fully_running() { return 1; }
any_lane_process_running() { return 1; }
run_reconciliation_preflight() { return 9; }
start_codex_lane() { touch "${TEST_ATTEMPTED_PATH}"; }
GRAPH_PATH="${TEST_GRAPH_PATH}"
BUNDLE_DIR="${TEST_BUNDLE_DIR}"
start_supervisors
printf 'rc=%s\\n' "$?"
""",
        environment={
            "TEST_ATTEMPTED_PATH": str(attempted_path),
            "TEST_BUNDLE_DIR": str(bundle_dir),
            "TEST_GRAPH_PATH": str(graph_path),
        },
    )

    assert "rc=1" in result.stdout
    assert "preflight failed" in result.stderr
    assert not attempted_path.exists()


def test_launch_normalizes_interpreter_and_persists_receipt(
    tmp_path: Path,
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake_python = bin_dir / "fake-python"
    argument_log = tmp_path / "arguments.txt"
    lifecycle_dir = tmp_path / "lifecycle"
    lifecycle_dir.mkdir()
    fake_python.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == "-c" && "${2:-}" == *"sys.executable"* ]]; then
  readlink -f "$0"
  exit 0
fi
if [[ "${1:-}" == "-m" ]]; then
  printf '%s\\n' "$@" >"${FAKE_PYTHON_ARGUMENT_LOG}"
  printf '{"active_state":"active","backend":"systemd-user","pid":4242,"unit_name":"test-unit.service"}\\n'
  exit 0
fi
exec "${REAL_PYTHON}" "$@"
""",
        encoding="utf-8",
    )
    fake_python.chmod(0o755)

    result = _run_library(
        """
LIFECYCLE_DIR="${TEST_LIFECYCLE_DIR}"
launch_durable_lane test-unit "${TEST_LOG_PATH}" \
  -m example.supervisor --state-dir /tmp/state --state-prefix lane
""",
        environment={
            "CRYPTO_IR_COMPLIANCE_PYTHON": "bin/fake-python",
            "FAKE_PYTHON_ARGUMENT_LOG": str(argument_log),
            "REAL_PYTHON": sys.executable,
            "TEST_LIFECYCLE_DIR": str(lifecycle_dir),
            "TEST_LOG_PATH": str(tmp_path / "lane.log"),
        },
        cwd=tmp_path,
    )

    assert result.returncode == 0, result.stderr
    receipt_path = lifecycle_dir / "test-unit.launch.json"
    assert json.loads(receipt_path.read_text(encoding="utf-8"))["pid"] == 4242
    assert not list(lifecycle_dir.glob("*.tmp.*"))
    arguments = argument_log.read_text(encoding="utf-8").splitlines()
    separator = arguments.index("--")
    assert Path(arguments[separator + 1]).is_absolute()
    assert Path(arguments[separator + 1]) == fake_python.resolve()
    assert arguments[separator + 2 :] == [
        "-m",
        "example.supervisor",
        "--state-dir",
        "/tmp/state",
        "--state-prefix",
        "lane",
    ]
