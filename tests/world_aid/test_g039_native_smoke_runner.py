"""Focused tests for the sealed WORLDCOIN-G039 native execution primitive."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import threading
import time
from dataclasses import replace
from pathlib import Path

import pytest

import scripts.run_world_aid_zkp_bootstrap as native_runner
from scripts.run_world_aid_zkp_bootstrap import (
    PLAN_SCHEMA,
    RECEIPT_NAME,
    RECEIPT_SCHEMA,
    G039NativeSmokeError,
    NativeSmokeExecutionPlan,
    NativeSmokeInput,
    NativeSmokeResourceBounds,
    execution_plan_sha256,
    run_approved_native_smoke,
)

_FAKE_TOOL = """#!/usr/bin/python3
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import time

arguments = sys.argv[1:]
if os.environ.get("AMBIENT_SECRET") is not None:
    raise SystemExit(70)
if os.environ.get("EXPECTED_VALUE") != "fixed":
    raise SystemExit(71)
if os.environ.get("PIP_NO_INDEX") != "1" or os.environ.get("CARGO_NET_OFFLINE") != "true":
    raise SystemExit(72)

def option(name):
    index = arguments.index(name)
    return arguments[index + 1]

command = arguments[0]
input_root = Path(option("--input-root"))
if (input_root / "locked/smoke-input.txt").read_bytes() != b"approval-bound-input":
    raise SystemExit(73)
if command == "build":
    if "--mutate-input" in arguments:
        locked = input_root / "locked/smoke-input.txt"
        locked.chmod(0o644)
        locked.write_bytes(b"mutated")
    if "--spam" in arguments:
        sys.stdout.write("x" * 1000000)
        sys.stdout.flush()
    if "--sleep" in arguments:
        child_token = option("--child-token")
        subprocess.Popen([
            "/usr/bin/python3",
            "-c",
            "import time; time.sleep(20)",
            child_token,
        ])
        time.sleep(20)
    if "--pause" in arguments:
        time.sleep(0.5)
    output = Path(option("--output"))
    payload = b"deterministic-artifact"
    if "--variant" in arguments:
        payload += option("--variant").encode("utf-8")
    output.write_bytes(payload)
elif command == "prove":
    if "--fail" in arguments:
        raise SystemExit(19)
    artifact = Path(option("--artifact")).read_bytes()
    Path(option("--proof")).write_bytes(b"proof:" + hashlib.sha256(artifact).digest())
elif command == "verify":
    if "--fail" in arguments:
        raise SystemExit(23)
    artifact = Path(option("--artifact")).read_bytes()
    expected = b"proof:" + hashlib.sha256(artifact).digest()
    if Path(option("--proof")).read_bytes() != expected:
        raise SystemExit(24)
else:
    raise SystemExit(64)
"""


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _make_tool(tmp_path: Path) -> Path:
    tool = tmp_path / "fake-zkp-tool"
    tool.write_text(_FAKE_TOOL, encoding="utf-8")
    tool.chmod(0o555)
    return tool


def _make_run_directory(tmp_path: Path, name: str = "run") -> Path:
    run_directory = tmp_path / name
    run_directory.mkdir(mode=0o700)
    run_directory.chmod(0o700)
    return run_directory


def _make_plan(tool: Path, **updates: object) -> NativeSmokeExecutionPlan:
    locked_input = tool.parent / "locked-smoke-input.txt"
    if not locked_input.exists():
        locked_input.write_bytes(b"approval-bound-input")
    values: dict[str, object] = {
        "schema_version": PLAN_SCHEMA,
        "goal_id": "WORLDCOIN-G039",
        "authorization_sha256": "sha256:" + "a" * 64,
        "network_boundary_sha256": "sha256:" + "b" * 64,
        "network_policy": "external-deny-all",
        "tool_path": tool.absolute(),
        "tool_sha256": _sha256(tool),
        "tool_max_bytes": tool.stat().st_size,
        "build_a_argv": (
            "{tool}",
            "build",
            "--input-root",
            "{input_root}",
            "--output",
            "{artifact}",
        ),
        "build_b_argv": (
            "{tool}",
            "build",
            "--input-root",
            "{input_root}",
            "--output",
            "{artifact}",
        ),
        "prove_argv": (
            "{tool}",
            "prove",
            "--input-root",
            "{input_root}",
            "--artifact",
            "{artifact}",
            "--proof",
            "{proof}",
        ),
        "verify_argv": (
            "{tool}",
            "verify",
            "--input-root",
            "{input_root}",
            "--artifact",
            "{artifact}",
            "--proof",
            "{proof}",
        ),
        "fixed_env": (("EXPECTED_VALUE", "fixed"),),
        "inputs": (
            NativeSmokeInput(
                source_path=locked_input.absolute(),
                sha256=_sha256(locked_input),
                max_bytes=1024,
                workspace_relative_path="locked/smoke-input.txt",
            ),
        ),
        "resource_bounds": NativeSmokeResourceBounds(
            max_seconds=5,
            max_memory_mb=256,
            max_output_bytes=64 * 1024,
        ),
        "artifact_relative_path": "out/artifact.bin",
        "proof_relative_path": "out/proof.bin",
        "expires_at": "2099-01-01T00:00:00Z",
    }
    values.update(updates)
    return NativeSmokeExecutionPlan(**values)


def _assert_clean_failure(run_directory: Path) -> None:
    assert not (run_directory / RECEIPT_NAME).exists()
    assert not list(run_directory.glob(".g039-native-smoke.*"))
    assert not list(run_directory.glob(f".{RECEIPT_NAME}.*.tmp"))


def _process_with_token_exists(token: str) -> bool:
    encoded = token.encode("utf-8")
    for command_line in Path("/proc").glob("[0-9]*/cmdline"):
        try:
            if encoded in command_line.read_bytes().split(b"\x00"):
                return True
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
    return False


def test_native_smoke_runs_pinned_tool_and_publishes_atomic_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tool = _make_tool(tmp_path)
    run_directory = _make_run_directory(tmp_path)
    plan = _make_plan(
        tool,
        build_a_argv=(
            "{tool}",
            "build",
            "--input-root",
            "{input_root}",
            "--output",
            "{artifact}",
            ";",
            "exit",
            "99",
        ),
    )
    monkeypatch.setenv("AMBIENT_SECRET", "must-not-cross-the-boundary")

    evidence = run_approved_native_smoke(plan, run_directory=run_directory)

    receipt = run_directory / RECEIPT_NAME
    assert receipt.is_file()
    assert stat.S_IMODE(receipt.stat().st_mode) == 0o600
    assert json.loads(receipt.read_text(encoding="utf-8")) == evidence
    assert evidence["schema_version"] == RECEIPT_SCHEMA
    assert evidence["execution_plan_sha256"] == execution_plan_sha256(plan)
    assert evidence["repeat_build_hashes"][0] == evidence["repeat_build_hashes"][1]
    assert evidence["proof_result"] is True
    assert evidence["verify_result"] is True
    assert evidence["network_registry_denied"] is True
    assert evidence["network_boundary"]["attestation_sha256"] == plan.network_boundary_sha256
    assert evidence["production_trust"] is False
    assert set(evidence["commands"]) == {"build_a", "build_b", "prove", "verify"}
    assert not list(run_directory.glob(".g039-native-smoke.*"))


def test_repeat_build_mismatch_fails_without_receipt(tmp_path: Path) -> None:
    tool = _make_tool(tmp_path)
    run_directory = _make_run_directory(tmp_path)
    plan = _make_plan(
        tool,
        build_b_argv=(
            "{tool}",
            "build",
            "--input-root",
            "{input_root}",
            "--output",
            "{artifact}",
            "--variant",
            "different",
        ),
    )

    with pytest.raises(G039NativeSmokeError, match="repeat-build artifact hashes differ"):
        run_approved_native_smoke(plan, run_directory=run_directory)

    _assert_clean_failure(run_directory)


def test_tool_size_bound_is_independent_from_process_output_bound(tmp_path: Path) -> None:
    tool = _make_tool(tmp_path)
    assert tool.stat().st_size > 64

    successful_run = _make_run_directory(tmp_path, "small-process-output")
    plan = _make_plan(
        tool,
        resource_bounds=NativeSmokeResourceBounds(
            max_seconds=5,
            max_memory_mb=256,
            max_output_bytes=64,
        ),
    )
    evidence = run_approved_native_smoke(plan, run_directory=successful_run)
    assert evidence["tool"]["max_bytes"] == tool.stat().st_size
    assert evidence["resource_bounds"]["max_output_bytes"] == 64

    undersized_run = _make_run_directory(tmp_path, "undersized-tool-bound")
    undersized = replace(plan, tool_max_bytes=tool.stat().st_size - 1)
    with pytest.raises(G039NativeSmokeError, match="evidence file exceeds the approved byte bound"):
        run_approved_native_smoke(undersized, run_directory=undersized_run)
    _assert_clean_failure(undersized_run)


@pytest.mark.parametrize(
    ("field", "argv", "message"),
    (
        (
            "prove_argv",
            (
                "{tool}",
                "prove",
                "--input-root",
                "{input_root}",
                "--artifact",
                "{artifact}",
                "--proof",
                "{proof}",
                "--fail",
            ),
            "prove failed with exit code 19",
        ),
        (
            "verify_argv",
            (
                "{tool}",
                "verify",
                "--input-root",
                "{input_root}",
                "--artifact",
                "{artifact}",
                "--proof",
                "{proof}",
                "--fail",
            ),
            "verify failed with exit code 23",
        ),
    ),
)
def test_proof_or_verify_failure_cleans_workspace(
    tmp_path: Path,
    field: str,
    argv: tuple[str, ...],
    message: str,
) -> None:
    tool = _make_tool(tmp_path)
    run_directory = _make_run_directory(tmp_path)
    plan = replace(_make_plan(tool), **{field: argv})

    with pytest.raises(G039NativeSmokeError, match=message):
        run_approved_native_smoke(plan, run_directory=run_directory)

    _assert_clean_failure(run_directory)


def test_tool_digest_mode_and_symlink_are_rejected_before_execution(tmp_path: Path) -> None:
    tool = _make_tool(tmp_path)

    mismatched_run = _make_run_directory(tmp_path, "mismatched")
    mismatched = _make_plan(tool, tool_sha256="sha256:" + "0" * 64)
    with pytest.raises(G039NativeSmokeError, match="tool_path digest mismatch"):
        run_approved_native_smoke(mismatched, run_directory=mismatched_run)
    _assert_clean_failure(mismatched_run)

    tool.chmod(0o755)
    writable_run = _make_run_directory(tmp_path, "writable")
    with pytest.raises(G039NativeSmokeError, match="mode-immutable"):
        run_approved_native_smoke(_make_plan(tool), run_directory=writable_run)
    _assert_clean_failure(writable_run)
    tool.chmod(0o555)

    symlink = tmp_path / "tool-link"
    symlink.symlink_to(tool)
    symlink_run = _make_run_directory(tmp_path, "symlink")
    with pytest.raises(G039NativeSmokeError, match="without following symlinks"):
        run_approved_native_smoke(
            _make_plan(symlink, tool_sha256=_sha256(tool)),
            run_directory=symlink_run,
        )
    _assert_clean_failure(symlink_run)


def test_timeout_kills_the_entire_process_group(tmp_path: Path) -> None:
    tool = _make_tool(tmp_path)
    run_directory = _make_run_directory(tmp_path)
    child_token = f"g039-child-{os.getpid()}-{time.time_ns()}"
    plan = _make_plan(
        tool,
        build_a_argv=(
            "{tool}",
            "build",
            "--input-root",
            "{input_root}",
            "--output",
            "{artifact}",
            "--sleep",
            "--child-token",
            child_token,
        ),
        resource_bounds=NativeSmokeResourceBounds(
            max_seconds=1,
            max_memory_mb=256,
            max_output_bytes=64 * 1024,
        ),
    )

    with pytest.raises(G039NativeSmokeError, match="wall-clock bound"):
        run_approved_native_smoke(plan, run_directory=run_directory)

    time.sleep(0.2)
    assert not _process_with_token_exists(child_token)
    _assert_clean_failure(run_directory)


def test_bounded_output_and_existing_receipt_fail_closed(tmp_path: Path) -> None:
    tool = _make_tool(tmp_path)
    output_run = _make_run_directory(tmp_path, "output")
    output_plan = _make_plan(
        tool,
        build_a_argv=(
            "{tool}",
            "build",
            "--input-root",
            "{input_root}",
            "--output",
            "{artifact}",
            "--spam",
        ),
        resource_bounds=NativeSmokeResourceBounds(
            max_seconds=5,
            max_memory_mb=256,
            max_output_bytes=4096,
        ),
    )
    with pytest.raises(G039NativeSmokeError, match="output bound"):
        run_approved_native_smoke(output_plan, run_directory=output_run)
    _assert_clean_failure(output_run)

    receipt_run = _make_run_directory(tmp_path, "receipt")
    outside = tmp_path / "outside"
    outside.write_text("do not replace", encoding="utf-8")
    (receipt_run / RECEIPT_NAME).symlink_to(outside)
    with pytest.raises(G039NativeSmokeError, match="receipt destination already exists"):
        run_approved_native_smoke(_make_plan(tool), run_directory=receipt_run)
    assert outside.read_text(encoding="utf-8") == "do not replace"
    assert (receipt_run / RECEIPT_NAME).is_symlink()
    assert not list(receipt_run.glob(".g039-native-smoke.*"))


def test_approval_bound_input_digest_and_materialized_copy_fail_closed(tmp_path: Path) -> None:
    tool = _make_tool(tmp_path)
    plan = _make_plan(tool)

    digest_run = _make_run_directory(tmp_path, "digest-input")
    bad_binding = replace(plan.inputs[0], sha256="sha256:" + "0" * 64)
    with pytest.raises(G039NativeSmokeError, match="input .* digest mismatch"):
        run_approved_native_smoke(
            replace(plan, inputs=(bad_binding,)),
            run_directory=digest_run,
        )
    _assert_clean_failure(digest_run)

    copy_run = _make_run_directory(tmp_path, "copy-input")
    mutating_plan = replace(
        plan,
        build_a_argv=(
            "{tool}",
            "build",
            "--input-root",
            "{input_root}",
            "--output",
            "{artifact}",
            "--mutate-input",
        ),
    )
    with pytest.raises(G039NativeSmokeError, match="materialized input .* (writable|drifted)"):
        run_approved_native_smoke(mutating_plan, run_directory=copy_run)
    _assert_clean_failure(copy_run)

    symlink_run = _make_run_directory(tmp_path, "symlink-input")
    input_symlink = tmp_path / "input-symlink"
    input_symlink.symlink_to(plan.inputs[0].source_path)
    symlink_binding = replace(plan.inputs[0], source_path=input_symlink)
    with pytest.raises(G039NativeSmokeError, match="without following symlinks"):
        run_approved_native_smoke(
            replace(plan, inputs=(symlink_binding,)),
            run_directory=symlink_run,
        )
    _assert_clean_failure(symlink_run)


@pytest.mark.parametrize("mutation", ("replace", "write"))
def test_sealed_input_swap_or_digest_drift_is_detected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    tool = _make_tool(tmp_path)
    plan = _make_plan(
        tool,
        build_a_argv=(
            "{tool}",
            "build",
            "--input-root",
            "{input_root}",
            "--output",
            "{artifact}",
            "--pause",
        ),
    )
    run_directory = _make_run_directory(tmp_path)
    source = plan.inputs[0].source_path
    command_started = threading.Event()
    original_run_command = native_runner._run_command

    def notifying_run_command(**kwargs: object):
        command_started.set()
        return original_run_command(**kwargs)

    monkeypatch.setattr(native_runner, "_run_command", notifying_run_command)

    def mutate_source() -> None:
        assert command_started.wait(timeout=2)
        if mutation == "replace":
            replacement = source.with_name("replacement-input")
            replacement.write_bytes(b"replacement")
            os.replace(replacement, source)
        else:
            source.write_bytes(b"digest-drift")

    mutation_thread = threading.Thread(target=mutate_source)
    mutation_thread.start()
    try:
        with pytest.raises(G039NativeSmokeError, match="input .* (changed|drifted|no longer identifies)"):
            run_approved_native_smoke(plan, run_directory=run_directory)
    finally:
        mutation_thread.join(timeout=2)

    assert not mutation_thread.is_alive()
    _assert_clean_failure(run_directory)


def test_receipt_fsync_failure_rolls_back_published_name(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tool = _make_tool(tmp_path)
    run_directory = _make_run_directory(tmp_path)
    run_identity = (run_directory.stat().st_dev, run_directory.stat().st_ino)
    original_fsync = native_runner.os.fsync
    injected = False

    def fail_first_directory_sync(descriptor: int) -> None:
        nonlocal injected
        metadata = os.fstat(descriptor)
        if (
            not injected
            and (metadata.st_dev, metadata.st_ino) == run_identity
            and (run_directory / RECEIPT_NAME).exists()
        ):
            injected = True
            raise OSError("injected directory fsync failure")
        original_fsync(descriptor)

    monkeypatch.setattr(native_runner.os, "fsync", fail_first_directory_sync)

    with pytest.raises(G039NativeSmokeError, match="atomic no-follow receipt"):
        run_approved_native_smoke(_make_plan(tool), run_directory=run_directory)

    assert injected is True
    _assert_clean_failure(run_directory)


@pytest.mark.parametrize(
    "updates",
    (
        {"network_policy": "best-effort-offline"},
        {"build_a_argv": ("{tool}", "download", "https://example.invalid/tool")},
        {"build_a_argv": ("/bin/sh", "-c", "true")},
        {"artifact_relative_path": "../artifact"},
        {"fixed_env": (("LD_PRELOAD", "/tmp/injected.so"),)},
        {
            "build_a_argv": (
                "{tool}",
                "build",
                "--input-root",
                "{input_root}",
                "--output",
                "{artifact}",
                "--config=/tmp/host-config",
            )
        },
    ),
)
def test_plan_validation_rejects_network_shell_traversal_and_loader_injection(
    tmp_path: Path,
    updates: dict[str, object],
) -> None:
    tool = _make_tool(tmp_path)

    with pytest.raises(G039NativeSmokeError):
        _make_plan(tool, **updates)
