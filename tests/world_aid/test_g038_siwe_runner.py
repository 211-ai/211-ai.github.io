"""Adversarial unit tests for the sealed G038 SIWE offline runner."""

from __future__ import annotations

import hashlib
import io
import json
import os
import stat
import tarfile
import threading
import time
from dataclasses import replace
from pathlib import Path

import pytest

import scripts.run_world_aid_siwe_bootstrap as siwe_runner
from scripts.run_world_aid_siwe_bootstrap import (
    PLAN_SCHEMA,
    RECEIPT_NAME,
    RECEIPT_SCHEMA,
    G038SIWERunnerError,
    SIWEBoundInput,
    SIWECacheArchive,
    SIWECacheEntry,
    SIWEExecutionPlan,
    SIWENetworkBoundary,
    SIWEResourceBounds,
    SIWEToolBinding,
    cache_tree_sha256,
    execution_plan_sha256,
    run_approved_siwe_bootstrap,
)


def _sha256_bytes(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _fake_node_source(mode: str, child_token: str) -> str:
    return f"""#!/usr/bin/python3
import json
import os
from pathlib import Path
import subprocess
import sys
import time

MODE = {mode!r}
CHILD_TOKEN = {child_token!r}
arguments = sys.argv[1:]

if os.environ.get("AMBIENT_SECRET") is not None:
    raise SystemExit(70)
if os.environ.get("npm_config_offline") != "true":
    raise SystemExit(71)
if os.environ.get("npm_config_ignore_scripts") != "true":
    raise SystemExit(72)
if os.environ.get("npm_config_registry") != "file:///nonexistent-world-aid-registry":
    raise SystemExit(73)
if os.environ.get("PATH") != "/nonexistent":
    raise SystemExit(74)

def maybe_pause():
    if MODE == "pause":
        time.sleep(0.5)

if arguments == ["--version"]:
    maybe_pause()
    print("v22.23.1")
elif len(arguments) == 2 and arguments[0].startswith("/proc/self/fd/") and arguments[1] == "--version":
    if MODE == "timeout":
        subprocess.Popen([
            "/usr/bin/python3",
            "-c",
            "import time; time.sleep(20)",
            CHILD_TOKEN,
        ])
        time.sleep(20)
    if MODE == "spam":
        sys.stdout.write("x" * 1000000)
        sys.stdout.flush()
    maybe_pause()
    print("10.9.8")
elif arguments and arguments[0].startswith("/proc/self/fd/") and len(arguments) == 8:
    cache = arguments[-1]
    expected = [
        "ci",
        "--offline",
        "--ignore-scripts",
        "--audit=false",
        "--fund=false",
        "--cache",
        cache,
    ]
    if arguments[1:] != expected:
        raise SystemExit(75)
    if os.environ.get("npm_config_cache") != cache:
        raise SystemExit(76)
    if MODE == "fail_install":
        raise SystemExit(17)
    if MODE == "mutate_input":
        manifest = Path("package.json")
        manifest.chmod(0o600)
        manifest.write_text("mutated", encoding="utf-8")
    Path("node_modules").mkdir()
    Path("node_modules/installed.txt").write_text("offline", encoding="utf-8")
    Path(cache, "last-used").write_text("local mutation", encoding="utf-8")
elif len(arguments) == 1 and arguments[0].endswith("g038-smoke.mjs"):
    smoke = Path(arguments[0]).read_text(encoding="utf-8")
    if "EOA_SYNTHETIC" not in smoke or "EIP1271_INJECTED" not in smoke:
        raise SystemExit(77)
    if MODE == "fail_smoke":
        raise SystemExit(19)
    if MODE == "bad_smoke":
        print(json.dumps({{"eoa": True, "eip1271": False, "contractReads": 0}}))
    elif MODE == "numeric_smoke":
        print(json.dumps({{"eoa": 1, "eip1271": 1, "contractReads": True}}))
    else:
        print(json.dumps({{"eoa": True, "eip1271": True, "contractReads": 1}}))
else:
    raise SystemExit(64)
"""


def _make_tools(tmp_path: Path, mode: str = "ok") -> tuple[Path, Path, str]:
    child_token = f"g038-child-{os.getpid()}-{time.time_ns()}"
    node = tmp_path / "node"
    node.write_text(_fake_node_source(mode, child_token), encoding="utf-8")
    node.chmod(0o555)
    npm = tmp_path / "npm-cli.js"
    npm.write_text("// pinned fake npm entrypoint\n", encoding="utf-8")
    npm.chmod(0o444)
    return node, npm, child_token


def _normal_cache_entries() -> tuple[SIWECacheEntry, ...]:
    payload = b"offline-package-tarball"
    return (
        SIWECacheEntry(path="content", kind="directory", size=0, sha256=None),
        SIWECacheEntry(
            path="content/package.tgz",
            kind="file",
            size=len(payload),
            sha256=_sha256_bytes(payload),
        ),
    )


def _write_cache_archive(
    path: Path,
    *,
    unsafe_kind: str | None = None,
) -> None:
    with tarfile.open(path, "w") as archive:
        if unsafe_kind is None:
            directory = tarfile.TarInfo("content")
            directory.type = tarfile.DIRTYPE
            directory.mode = 0o755
            archive.addfile(directory)
            payload = b"offline-package-tarball"
            item = tarfile.TarInfo("content/package.tgz")
            item.size = len(payload)
            item.mode = 0o644
            archive.addfile(item, io.BytesIO(payload))
            return

        name = "../escape" if unsafe_kind == "traversal" else "unsafe"
        member = tarfile.TarInfo(name)
        if unsafe_kind == "traversal":
            payload = b"escape"
            member.size = len(payload)
            archive.addfile(member, io.BytesIO(payload))
        elif unsafe_kind == "symlink":
            member.type = tarfile.SYMTYPE
            member.linkname = "/etc/passwd"
            archive.addfile(member)
        elif unsafe_kind == "hardlink":
            member.type = tarfile.LNKTYPE
            member.linkname = "content/package.tgz"
            archive.addfile(member)
        elif unsafe_kind == "fifo":
            member.type = tarfile.FIFOTYPE
            archive.addfile(member)
        elif unsafe_kind == "device":
            member.type = tarfile.CHRTYPE
            member.devmajor = 1
            member.devminor = 3
            archive.addfile(member)
        else:
            raise AssertionError(unsafe_kind)


def _make_input(tmp_path: Path, filename: str, content: str) -> SIWEBoundInput:
    source = tmp_path / f"source-{filename}"
    source.write_text(content, encoding="utf-8")
    return SIWEBoundInput(
        source_path=source.absolute(),
        sha256=_sha256(source),
        max_bytes=4096,
        workspace_relative_path=filename,
    )


def _make_plan(
    tmp_path: Path,
    *,
    mode: str = "ok",
    unsafe_archive: str | None = None,
    **updates: object,
) -> tuple[SIWEExecutionPlan, str]:
    node, npm, child_token = _make_tools(tmp_path, mode)
    archive = tmp_path / "offline-cache.tar"
    _write_cache_archive(archive, unsafe_kind=unsafe_archive)
    entries = _normal_cache_entries()
    values: dict[str, object] = {
        "schema_version": PLAN_SCHEMA,
        "goal_id": "WORLDCOIN-G038",
        "authorization_sha256": "sha256:" + "a" * 64,
        "selection_record_id": "gate-0b-selection-test",
        "network_policy": "external-deny-all",
        "network_boundary": SIWENetworkBoundary(
            attestation_sha256="sha256:" + "b" * 64,
            namespace="net:[4026533000]",
            apparmor_profile="world-aid-gate (enforce)",
            network_deny_canary_sha256="sha256:" + "c" * 64,
            egress_policy_sha256="sha256:" + "d" * 64,
        ),
        "platform": "linux",
        "architecture": "x86_64",
        "toolchain_archive_sha256": "sha256:" + "e" * 64,
        "node": SIWEToolBinding(
            source_path=node.absolute(),
            sha256=_sha256(node),
            max_bytes=node.stat().st_size,
            version="22.23.1",
        ),
        "npm_cli": SIWEToolBinding(
            source_path=npm.absolute(),
            sha256=_sha256(npm),
            max_bytes=npm.stat().st_size,
            version="10.9.8",
        ),
        "manifest": _make_input(tmp_path, "package.json", '{"private":true}\n'),
        "lockfile": _make_input(
            tmp_path,
            "package-lock.json",
            '{"lockfileVersion":3}\n',
        ),
        "adapter": _make_input(
            tmp_path,
            "index.mjs",
            "export async function verifyWorldSiwe() {}\n",
        ),
        "smoke_source": _make_input(
            tmp_path,
            "g038-smoke.mjs",
            "// EOA_SYNTHETIC\n// EIP1271_INJECTED\n",
        ),
        "cache": SIWECacheArchive(
            source_path=archive.absolute(),
            sha256=_sha256(archive),
            max_archive_bytes=archive.stat().st_size,
            archive_format="tar",
            max_entries=16,
            max_extracted_bytes=4096,
            tree_sha256=cache_tree_sha256(entries),
            entries=entries,
        ),
        "resource_bounds": SIWEResourceBounds(
            max_seconds=5,
            max_memory_mb=256,
            max_output_bytes=64 * 1024,
            max_file_bytes=64 * 1024,
            max_workspace_entries=256,
            max_workspace_bytes=1024 * 1024,
        ),
        "expires_at": "2099-01-01T00:00:00Z",
    }
    values.update(updates)
    return SIWEExecutionPlan(**values), child_token


def _make_run_directory(tmp_path: Path, name: str = "run") -> Path:
    path = tmp_path / name
    path.mkdir(mode=0o700)
    path.chmod(0o700)
    return path


def _assert_clean_failure(run_directory: Path) -> None:
    assert not (run_directory / RECEIPT_NAME).exists()
    assert not list(run_directory.glob(".g038-siwe.*"))
    assert not list(run_directory.glob(f".{RECEIPT_NAME}.*.tmp"))


def _process_with_token_exists(token: str) -> bool:
    encoded = token.encode("utf-8")
    for path in Path("/proc").glob("[0-9]*/cmdline"):
        try:
            if encoded in path.read_bytes().split(b"\x00"):
                return True
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
    return False


def test_cache_manifest_digest_uses_gate_depth_first_order() -> None:
    first = _sha256_bytes(b"nested")
    second = _sha256_bytes(b"sibling")
    entries = (
        SIWECacheEntry(path="a", kind="directory", size=0, sha256=None),
        SIWECacheEntry(path="a-foo", kind="file", size=7, sha256=second),
        SIWECacheEntry(path="a/x", kind="file", size=6, sha256=first),
    )
    digest = hashlib.sha256()
    for kind, path, file_digest in (
        (b"D", ".", None),
        (b"D", "a", None),
        (b"F", "a/x", first),
        (b"F", "a-foo", second),
    ):
        encoded = path.encode("utf-8")
        digest.update(kind)
        digest.update(len(encoded).to_bytes(8, "big"))
        digest.update(encoded)
        if file_digest is not None:
            digest.update(bytes.fromhex(file_digest.removeprefix("sha256:")))

    assert cache_tree_sha256(entries) == "sha256:" + digest.hexdigest()


def test_exact_offline_install_and_dual_path_smoke_publish_v2_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan, _ = _make_plan(tmp_path)
    run_directory = _make_run_directory(tmp_path)
    monkeypatch.setenv("AMBIENT_SECRET", "must-not-leak")

    receipt = run_approved_siwe_bootstrap(plan, run_directory=run_directory)

    receipt_path = run_directory / RECEIPT_NAME
    assert receipt_path.is_file()
    assert stat.S_IMODE(receipt_path.stat().st_mode) == 0o600
    assert json.loads(receipt_path.read_text(encoding="utf-8")) == receipt
    assert receipt["schema_version"] == RECEIPT_SCHEMA
    assert receipt["smoke_result"] == {
        "eoa": True,
        "eip1271": True,
        "contractReads": 1,
    }
    assert receipt["toolchain"]["node_version"] == "22.23.1"
    assert receipt["toolchain"]["npm_version"] == "10.9.8"
    assert receipt["cache"]["local_before_sha256"] == plan.cache.tree_sha256
    assert receipt["cache"]["local_after_sha256"] != plan.cache.tree_sha256
    assert receipt["network"]["external_network_succeeded"] is False
    assert receipt["cache_mutated"] is False
    assert execution_plan_sha256(plan).startswith("sha256:")
    assert not list(run_directory.glob(".g038-siwe.*"))


@pytest.mark.parametrize(
    "unsafe_kind",
    ("traversal", "symlink", "hardlink", "fifo", "device"),
)
def test_cache_archive_rejects_escape_links_and_special_entries(
    tmp_path: Path,
    unsafe_kind: str,
) -> None:
    plan, _ = _make_plan(tmp_path, unsafe_archive=unsafe_kind)
    run_directory = _make_run_directory(tmp_path)

    with pytest.raises(G038SIWERunnerError, match="archive member|symlink|hardlink|device|FIFO"):
        run_approved_siwe_bootstrap(plan, run_directory=run_directory)

    assert not (tmp_path / "escape").exists()
    _assert_clean_failure(run_directory)


@pytest.mark.parametrize(
    ("target", "mutation"),
    (
        ("adapter", "write"),
        ("node", "replace"),
        ("cache", "replace"),
    ),
)
def test_descriptor_seals_detect_digest_drift_and_path_swaps(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    target: str,
    mutation: str,
) -> None:
    plan, _ = _make_plan(tmp_path, mode="pause")
    run_directory = _make_run_directory(tmp_path)
    command_started = threading.Event()
    original_run = siwe_runner._run_process

    def notifying_run(**kwargs: object):
        command_started.set()
        return original_run(**kwargs)

    monkeypatch.setattr(siwe_runner, "_run_process", notifying_run)

    source = {
        "adapter": plan.adapter.source_path,
        "node": plan.node.source_path,
        "cache": plan.cache.source_path,
    }[target]

    def mutate_source() -> None:
        assert command_started.wait(timeout=2)
        if mutation == "write":
            source.write_text("digest drift", encoding="utf-8")
        else:
            replacement = source.with_name(f"{source.name}.replacement")
            replacement.write_bytes(b"replacement")
            if target == "node":
                replacement.chmod(0o555)
            os.replace(replacement, source)

    thread = threading.Thread(target=mutate_source)
    thread.start()
    try:
        with pytest.raises(
            G038SIWERunnerError,
            match="changed after sealing|no longer identifies|digest drifted",
        ):
            run_approved_siwe_bootstrap(plan, run_directory=run_directory)
    finally:
        thread.join(timeout=2)
    assert not thread.is_alive()
    _assert_clean_failure(run_directory)


def test_initial_tool_and_input_digest_mismatches_fail_before_execution(tmp_path: Path) -> None:
    plan, _ = _make_plan(tmp_path)

    node_run = _make_run_directory(tmp_path, "node-digest")
    bad_node = replace(plan.node, sha256="sha256:" + "0" * 64)
    with pytest.raises(G038SIWERunnerError, match="Node executable digest mismatch"):
        run_approved_siwe_bootstrap(
            replace(plan, node=bad_node),
            run_directory=node_run,
        )
    _assert_clean_failure(node_run)

    input_run = _make_run_directory(tmp_path, "input-digest")
    bad_adapter = replace(plan.adapter, sha256="sha256:" + "1" * 64)
    with pytest.raises(G038SIWERunnerError, match="adapter digest mismatch"):
        run_approved_siwe_bootstrap(
            replace(plan, adapter=bad_adapter),
            run_directory=input_run,
        )
    _assert_clean_failure(input_run)


def test_incremental_output_bound_fails_closed(tmp_path: Path) -> None:
    initial, _ = _make_plan(tmp_path, mode="spam")
    plan = replace(
        initial,
        resource_bounds=replace(initial.resource_bounds, max_output_bytes=1024),
    )
    run_directory = _make_run_directory(tmp_path)

    with pytest.raises(G038SIWERunnerError, match="output bound"):
        run_approved_siwe_bootstrap(plan, run_directory=run_directory)

    _assert_clean_failure(run_directory)


def test_whole_run_timeout_kills_process_group(tmp_path: Path) -> None:
    initial, child_token = _make_plan(tmp_path, mode="timeout")
    plan = replace(
        initial,
        resource_bounds=replace(initial.resource_bounds, max_seconds=1),
    )
    run_directory = _make_run_directory(tmp_path)

    with pytest.raises(G038SIWERunnerError, match="whole-run timeout"):
        run_approved_siwe_bootstrap(plan, run_directory=run_directory)

    time.sleep(0.2)
    assert not _process_with_token_exists(child_token)
    _assert_clean_failure(run_directory)


@pytest.mark.parametrize(
    ("mode", "message"),
    (
        ("fail_install", "npm_ci failed with exit code 17"),
        ("fail_smoke", "siwe_smoke failed with exit code 19"),
        ("bad_smoke", "exact EOA and injected EIP-1271"),
        ("numeric_smoke", "exact EOA and injected EIP-1271"),
        ("mutate_input", "materialized package.json"),
    ),
)
def test_command_smoke_and_input_mutation_failures_leave_no_receipt(
    tmp_path: Path,
    mode: str,
    message: str,
) -> None:
    plan, _ = _make_plan(tmp_path, mode=mode)
    run_directory = _make_run_directory(tmp_path)

    with pytest.raises(G038SIWERunnerError, match=message):
        run_approved_siwe_bootstrap(plan, run_directory=run_directory)

    _assert_clean_failure(run_directory)


def test_receipt_collision_is_no_replace_and_does_not_execute(tmp_path: Path) -> None:
    plan, _ = _make_plan(tmp_path)
    run_directory = _make_run_directory(tmp_path)
    outside = tmp_path / "outside-receipt"
    outside.write_text("preserve", encoding="utf-8")
    (run_directory / RECEIPT_NAME).symlink_to(outside)

    with pytest.raises(G038SIWERunnerError, match="receipt destination already exists"):
        run_approved_siwe_bootstrap(plan, run_directory=run_directory)

    assert outside.read_text(encoding="utf-8") == "preserve"
    assert (run_directory / RECEIPT_NAME).is_symlink()
    assert not list(run_directory.glob(".g038-siwe.*"))


@pytest.mark.parametrize(
    "updates",
    (
        {"network_policy": "best-effort"},
        {"expires_at": "2000-01-01T00:00:00Z"},
        {"selection_record_id": "../invalid"},
    ),
)
def test_plan_or_expiry_validation_fails_closed(
    tmp_path: Path,
    updates: dict[str, object],
) -> None:
    if updates.get("expires_at") == "2000-01-01T00:00:00Z":
        plan, _ = _make_plan(tmp_path, **updates)
        run_directory = _make_run_directory(tmp_path)
        with pytest.raises(G038SIWERunnerError, match="expired"):
            run_approved_siwe_bootstrap(plan, run_directory=run_directory)
        _assert_clean_failure(run_directory)
    else:
        with pytest.raises(G038SIWERunnerError):
            _make_plan(tmp_path, **updates)
