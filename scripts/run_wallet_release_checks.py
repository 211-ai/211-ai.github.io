#!/usr/bin/env python3
"""Run the local wallet release-check suite.

This script is intentionally a thin command orchestrator. It keeps the backend,
compile, UI build, and live full-stack browser checks in one repeatable entry
point without hiding the exact commands being run.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Mapping, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
UI_ROOT = REPO_ROOT / "wallet_interface" / "ui"

BACKEND_PYTEST_TARGETS = (
    "ipfs_datasets_py/tests/unit/test_data_wallet.py",
    "ipfs_datasets_py/tests/mcp/test_wallet_tools.py",
    "ipfs_datasets_py/tests/mcp/unit/test_hierarchical_tool_manager.py",
    "tests/test_wallet_interface_api.py",
    "tests/test_wallet_interface_ops.py",
    "tests/test_wallet_interface_deploy.py",
    "tests/test_wallet_implementation_plan_docs.py",
    "tests/test_wallet_release_check_runner.py",
    "tests/test_wallet_production_handoff_blackbox.py",
)

NETWORK_BACKEND_PYTEST_TARGETS = frozenset(
    {
        "tests/test_wallet_production_handoff_blackbox.py",
    }
)


def release_pythonpath(repo_root: Path) -> str:
    """Return the PYTHONPATH needed for root tests plus the submodule package."""

    return os.pathsep.join([str(repo_root), str(repo_root / "ipfs_datasets_py")])


def local_tcp_bind_available() -> bool:
    """Return whether this process may bind a local TCP listener."""

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
    except OSError:
        return False
    return True


def ui_toolchain_available(ui_root: Path = UI_ROOT) -> bool:
    """Return whether the checked-out UI has the local build/test toolchain."""

    bin_dir = ui_root / "node_modules" / ".bin"
    return (bin_dir / "tsc").exists() and (bin_dir / "vite").exists()


@dataclass(frozen=True)
class ReleaseCheckStep:
    """A single command in the wallet release-check suite."""

    name: str
    command: tuple[str, ...]
    cwd: Path = REPO_ROOT
    env: Mapping[str, str] = field(default_factory=dict)
    timeout_seconds: int = 900

    def manifest(self) -> dict[str, object]:
        return {
            "name": self.name,
            "cwd": str(self.cwd),
            "command": list(self.command),
            "env": dict(self.env),
            "timeout_seconds": self.timeout_seconds,
        }


@dataclass(frozen=True)
class ReleaseCheckResult:
    """Aggregated result from a release-check run."""

    exit_code: int
    completed: tuple[str, ...]
    failed: str | None = None
    evidence_path: Path | None = None


Runner = Callable[..., subprocess.CompletedProcess[str]]


def build_release_check_steps(
    *,
    repo_root: Path = REPO_ROOT,
    playwright_port: str = "5185",
    skip_backend: bool = False,
    skip_compile: bool = False,
    skip_ui_build: bool = False,
    skip_fullstack: bool = False,
    skip_network_blackbox: bool = False,
    include_smoke: bool = False,
) -> list[ReleaseCheckStep]:
    """Build the ordered local wallet release-check commands."""

    ui_root = repo_root / "wallet_interface" / "ui"
    steps: list[ReleaseCheckStep] = []
    minimal_import_env = {
        "PYTHONPATH": release_pythonpath(repo_root),
        "IPFS_DATASETS_AUTO_INSTALL": "false",
        "IPFS_AUTO_INSTALL": "false",
        "IPFS_DATASETS_PY_MINIMAL_IMPORTS": "1",
        "PYTEST_PLUGINS": "tests.wallet_testclient_compat",
    }

    if not skip_backend:
        backend_targets = tuple(
            target
            for target in BACKEND_PYTEST_TARGETS
            if not skip_network_blackbox or target not in NETWORK_BACKEND_PYTEST_TARGETS
        )
        steps.append(
            ReleaseCheckStep(
                name="backend-wallet-pytest",
                command=(
                    sys.executable,
                    "-m",
                    "pytest",
                    *backend_targets,
                    "-q",
                ),
                cwd=repo_root,
                env=minimal_import_env,
                timeout_seconds=900,
            )
        )

    if not skip_compile:
        steps.append(
            ReleaseCheckStep(
                name="wallet-compileall",
                command=(
                    sys.executable,
                    "-m",
                    "compileall",
                    "-q",
                    "wallet_interface",
                    "ipfs_datasets_py/ipfs_datasets_py/wallet",
                ),
                cwd=repo_root,
                timeout_seconds=120,
            )
        )

    if not skip_ui_build:
        steps.append(
            ReleaseCheckStep(
                name="wallet-ui-build",
                command=("npm", "run", "build"),
                cwd=ui_root,
                timeout_seconds=300,
            )
        )

    if include_smoke:
        steps.append(
            ReleaseCheckStep(
                name="wallet-ui-smoke",
                command=("npm", "run", "test:smoke"),
                cwd=ui_root,
                env={"PLAYWRIGHT_PORT": playwright_port},
                timeout_seconds=300,
            )
        )

    if not skip_fullstack:
        steps.append(
            ReleaseCheckStep(
                name="wallet-ui-fullstack",
                command=("npm", "run", "test:fullstack"),
                cwd=ui_root,
                env={"PLAYWRIGHT_PORT": playwright_port},
                timeout_seconds=600,
            )
        )

    return steps


def run_release_check_steps(
    steps: Sequence[ReleaseCheckStep],
    *,
    keep_going: bool = False,
    evidence_dir: Path | None = None,
    metadata: Mapping[str, object] | None = None,
    runner: Runner = subprocess.run,
) -> ReleaseCheckResult:
    """Run release-check commands sequentially and stop on first failure by default."""

    completed: list[str] = []
    exit_code = 0
    failed: str | None = None
    evidence_path: Path | None = None
    evidence_steps: list[dict[str, object]] = []

    if evidence_dir is not None:
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        evidence_path = evidence_dir / run_id
        evidence_path.mkdir(parents=True, exist_ok=True)
        (evidence_path / "manifest.json").write_text(
            json.dumps([step.manifest() for step in steps], indent=2, sort_keys=True),
            encoding="utf-8",
        )

    for step in steps:
        print(f"==> {step.name}", flush=True)
        env = os.environ.copy()
        env.update(step.env)
        started_at = datetime.now(timezone.utc)
        stdout = ""
        stderr = ""
        timed_out = False
        try:
            result = runner(
                list(step.command),
                cwd=str(step.cwd),
                env=env,
                text=True,
                capture_output=True,
                timeout=step.timeout_seconds,
            )
            stdout = result.stdout or ""
            stderr = result.stderr or ""
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            stdout = str(exc.stdout or "")
            stderr = str(exc.stderr or "")
            result = subprocess.CompletedProcess(
                list(step.command),
                returncode=124,
                stdout=stdout,
                stderr=stderr,
            )
        finished_at = datetime.now(timezone.utc)
        if stdout:
            print(stdout, end="" if stdout.endswith("\n") else "\n", flush=True)
        if stderr:
            print(stderr, end="" if stderr.endswith("\n") else "\n", file=sys.stderr, flush=True)
        step_evidence: dict[str, object] = {
            "name": step.name,
            "command": list(step.command),
            "cwd": str(step.cwd),
            "started_at": started_at.isoformat(),
            "finished_at": finished_at.isoformat(),
            "duration_seconds": (finished_at - started_at).total_seconds(),
            "returncode": result.returncode,
            "timeout_seconds": step.timeout_seconds,
            "timed_out": timed_out,
        }
        if evidence_path is not None:
            step_slug = "".join(char if char.isalnum() or char in {"-", "_"} else "-" for char in step.name)
            stdout_path = evidence_path / f"{step_slug}.stdout.log"
            stderr_path = evidence_path / f"{step_slug}.stderr.log"
            stdout_path.write_text(stdout, encoding="utf-8")
            stderr_path.write_text(stderr, encoding="utf-8")
            step_evidence["stdout_log"] = stdout_path.name
            step_evidence["stderr_log"] = stderr_path.name
        evidence_steps.append(
            step_evidence
        )
        if result.returncode != 0:
            exit_code = result.returncode
            failed = step.name
            if not keep_going:
                break
        else:
            completed.append(step.name)

    if evidence_path is not None:
        (evidence_path / "results.json").write_text(
            json.dumps(
                {
                    "source": "scripts/run_wallet_release_checks.py",
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "status": "ok" if exit_code == 0 else "error",
                    "exit_code": exit_code,
                    "completed": completed,
                    "failed": failed,
                    "metadata": dict(metadata or {}),
                    "steps": evidence_steps,
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        print(f"release-check evidence: {evidence_path}", flush=True)

    return ReleaseCheckResult(
        exit_code=exit_code,
        completed=tuple(completed),
        failed=failed,
        evidence_path=evidence_path,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run local 211-AI wallet release checks.")
    parser.add_argument(
        "--playwright-port",
        default="5185",
        help="Port passed to wallet UI Playwright tests. Default: 5185.",
    )
    parser.add_argument("--skip-backend", action="store_true", help="Skip backend pytest checks.")
    parser.add_argument("--skip-compile", action="store_true", help="Skip compileall check.")
    parser.add_argument("--skip-ui-build", action="store_true", help="Skip wallet UI build.")
    parser.add_argument("--skip-fullstack", action="store_true", help="Skip live full-stack Playwright checks.")
    parser.add_argument(
        "--skip-network-blackbox",
        action="store_true",
        help="Skip backend blackbox tests that require binding local TCP sockets.",
    )
    parser.add_argument(
        "--require-local-sockets",
        action="store_true",
        help="Fail instead of skipping network-backed checks when local TCP binding is unavailable.",
    )
    parser.add_argument(
        "--require-ui-toolchain",
        action="store_true",
        help="Fail instead of skipping UI build/browser checks when npm dependencies are unavailable.",
    )
    parser.add_argument(
        "--include-smoke",
        action="store_true",
        help="Also run the UI smoke suite before the full-stack browser checks.",
    )
    parser.add_argument(
        "--keep-going",
        action="store_true",
        help="Continue running later checks after a failure.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the command manifest without running checks.",
    )
    parser.add_argument(
        "--evidence-dir",
        default=str(REPO_ROOT / "artifacts" / "wallet-release-checks"),
        help="Directory for release-check evidence bundles. Default: artifacts/wallet-release-checks.",
    )
    parser.add_argument(
        "--no-evidence",
        action="store_true",
        help="Do not write manifest/results evidence for this run.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    tcp_bind_available = local_tcp_bind_available()
    socket_limited = not tcp_bind_available and not args.require_local_sockets
    if not tcp_bind_available and args.require_local_sockets:
        print(
            "local TCP bind is unavailable; cannot run network-backed wallet release checks",
            file=sys.stderr,
            flush=True,
        )
        return 2
    if socket_limited:
        print(
            "local TCP bind is unavailable; skipping backend blackbox and Playwright checks "
            "that require local listeners",
            file=sys.stderr,
            flush=True,
        )
    ui_toolchain_ready = ui_toolchain_available()
    ui_toolchain_limited = not args.dry_run and not ui_toolchain_ready and not args.require_ui_toolchain
    if not ui_toolchain_ready and args.require_ui_toolchain:
        print(
            "wallet UI npm toolchain is unavailable; cannot run UI build or browser checks",
            file=sys.stderr,
            flush=True,
        )
        return 2
    if ui_toolchain_limited:
        print(
            "wallet UI npm toolchain is unavailable; skipping UI build and browser checks",
            file=sys.stderr,
            flush=True,
        )
    steps = build_release_check_steps(
        playwright_port=args.playwright_port,
        skip_backend=args.skip_backend,
        skip_compile=args.skip_compile,
        skip_ui_build=args.skip_ui_build or ui_toolchain_limited,
        skip_fullstack=args.skip_fullstack or socket_limited or ui_toolchain_limited,
        skip_network_blackbox=args.skip_network_blackbox or socket_limited,
        include_smoke=args.include_smoke and not socket_limited and not ui_toolchain_limited,
    )
    if args.dry_run:
        print(json.dumps([step.manifest() for step in steps], indent=2, sort_keys=True))
        return 0
    evidence_dir = None if args.no_evidence else Path(args.evidence_dir)
    metadata = {
        "local_tcp_bind_available": tcp_bind_available,
        "socket_limited": socket_limited,
        "ui_toolchain_available": ui_toolchain_ready,
        "ui_toolchain_limited": ui_toolchain_limited,
    }
    return run_release_check_steps(
        steps,
        keep_going=args.keep_going,
        evidence_dir=evidence_dir,
        metadata=metadata,
    ).exit_code


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
