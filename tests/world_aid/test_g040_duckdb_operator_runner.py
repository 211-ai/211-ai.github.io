"""Adversarial tests for the sealed, operator-only G040 DuckDB runner."""

from __future__ import annotations

import ast
import base64
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import threading
import time
import zipfile
from dataclasses import replace
from pathlib import Path

import pytest

import scripts.run_world_aid_duckdb_bootstrap as duckdb_runner
from scripts.run_world_aid_duckdb_bootstrap import (
    CHILD_RESULT_SCHEMA,
    G033_EXCLUDED_CONTROLS,
    PLAN_SCHEMA,
    RECEIPT_NAME,
    RECEIPT_SCHEMA,
    REQUIRED_G040_CHECKS,
    DuckDBBootstrapPlan,
    DuckDBBoundArtifact,
    DuckDBResourceBounds,
    G040DuckDBBootstrapError,
    execution_plan_sha256,
    run_approved_duckdb_bootstrap,
)

_DUCKDB_VERSION = "1.4.3"
_SECOND_WRITER_SCHEMA = "world-human-aid-g040-second-writer/v1"


def _sha256_bytes(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _record_hash(raw: bytes) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(raw).digest()).rstrip(b"=").decode()


@pytest.fixture(scope="module")
def pinned_python(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, str]:
    candidates = (Path("/usr/bin/python3.12"), Path(sys.executable).resolve())
    source = next(path for path in candidates if path.is_file() and not path.is_symlink())
    destination = tmp_path_factory.mktemp("g040-python") / "python"
    shutil.copyfile(source, destination)
    destination.chmod(0o555)
    version = subprocess.check_output(
        [
            os.fspath(destination),
            "-I",
            "-S",
            "-B",
            "-c",
            "import sys; print('.'.join(map(str, sys.version_info[:3])))",
        ],
        text=True,
    ).strip()
    return destination.absolute(), version


def _wheel_identity(python_version: str) -> tuple[str, str, str]:
    major, minor, _patch = python_version.split(".")
    python_tag = f"cp{major}{minor}"
    machine = os.uname().machine.lower()
    platform_tag = f"manylinux_2_26_{machine}.manylinux_2_28_{machine}"
    filename = f"duckdb-{_DUCKDB_VERSION}-{python_tag}-{python_tag}-{platform_tag}.whl"
    return python_tag, platform_tag, filename


def _write_wheel(
    path: Path,
    *,
    python_tag: str,
    platform_tag: str,
    kind: str = "valid",
) -> None:
    dist_info = f"duckdb-{_DUCKDB_VERSION}.dist-info"
    files: dict[str, bytes] = {
        "duckdb/__init__.py": (f"__version__ = {_DUCKDB_VERSION!r}\n").encode(),
        f"{dist_info}/METADATA": (f"Metadata-Version: 2.1\nName: duckdb\nVersion: {_DUCKDB_VERSION}\n\n").encode(),
        f"{dist_info}/WHEEL": (
            "Wheel-Version: 1.0\n"
            "Generator: world-aid-test\n"
            "Root-Is-Purelib: false\n"
            + "".join(f"Tag: {python_tag}-{python_tag}-{platform}\n" for platform in platform_tag.split("."))
        ).encode(),
    }
    special_name: str | None = None
    if kind == "traversal":
        special_name = "../outside.py"
        files[special_name] = b"escape\n"
    elif kind == "symlink":
        special_name = "duckdb/unsafe-link"
        files[special_name] = b"/etc/passwd"
    elif kind == "wrong_tag":
        files[f"{dist_info}/WHEEL"] = (
            "Wheel-Version: 1.0\n"
            "Generator: world-aid-test\n"
            "Root-Is-Purelib: false\n"
            f"Tag: {python_tag}-{python_tag}-win_amd64\n"
        ).encode()

    record_path = f"{dist_info}/RECORD"
    rows = []
    for name, raw in files.items():
        digest = _record_hash(raw)
        if kind == "record_mismatch" and name == "duckdb/__init__.py":
            digest = _record_hash(b"different")
        rows.append(f"{name},sha256={digest},{len(raw)}\n")
    rows.append(f"{record_path},,\n")
    files[record_path] = "".join(rows).encode()

    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, raw in files.items():
            if kind == "symlink" and name == special_name:
                info = zipfile.ZipInfo(name)
                info.create_system = 3
                info.external_attr = (stat.S_IFLNK | 0o777) << 16
                archive.writestr(info, raw)
            else:
                archive.writestr(name, raw)
    path.chmod(0o444)


def _synthetic_bootstrap(mode: str) -> str:
    checks = repr(REQUIRED_G040_CHECKS)
    excluded = repr(list(G033_EXCLUDED_CONTROLS))
    return f"""#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path

MODE = {mode!r}
CHECKS = {checks}
EXCLUDED = {excluded}

def require(value, code):
    if not value:
        raise SystemExit(code)

require(sys.argv[1] == "run" and len(sys.argv) == 11, 60)
site_root = Path(sys.argv[2])
workspace = Path(sys.argv[3])
result_path = Path(sys.argv[4])
expected_python = sys.argv[5]
expected_duckdb = sys.argv[6]
require(sys.flags.isolated == 1, 61)
require(sys.flags.no_site == 1, 62)
require(sys.flags.dont_write_bytecode == 1, 63)
require(".".join(map(str, sys.version_info[:3])) == expected_python, 64)
require("AMBIENT_SECRET" not in os.environ, 65)
require(os.environ.get("PIP_NO_INDEX") == "1", 66)
require(os.environ.get("PATH") == "/nonexistent", 67)
require(os.environ.get("HOME", "").startswith(str(workspace)), 68)
require(os.environ.get("TMPDIR", "").startswith(str(workspace)), 69)
sys.path.insert(0, str(site_root))
import duckdb
require(str(duckdb.__version__) == expected_duckdb, 70)
Path(duckdb.__file__).resolve(strict=True).relative_to(site_root.resolve(strict=True))

if MODE == "timeout":
    time.sleep(20)
if MODE == "spam":
    sys.stdout.write("x" * 1000000)
    sys.stdout.flush()
if MODE == "fail":
    raise SystemExit(19)
if MODE == "pause_swap":
    (workspace / "swap-ready").write_text("ready", encoding="utf-8")
    time.sleep(0.75)

writer = {{
    "schema_version": {_SECOND_WRITER_SCHEMA!r},
    "import_succeeded": True,
    "connect_attempted": True,
    "connect_succeeded": False,
    "write_attempted": False,
    "rejected": True,
    "rejection_stage": "connect",
    "exception_module": "_duckdb",
    "exception_type": "IOException",
    "lock_marker": "could not set lock",
    "message_sha256": hashlib.sha256(b"could not set lock").hexdigest(),
    "message_bytes": len(b"could not set lock"),
    "message_truncated": False,
}}
if MODE == "bad_writer":
    writer["exception_module"] = "builtins"
    writer["exception_type"] = "ValueError"

payload = {{
    "schema_version": {CHILD_RESULT_SCHEMA!r},
    "duckdb_version": expected_duckdb,
    "checks": {{name: True for name in CHECKS}},
    "cleanup": {{
        "database_exists": False,
        "temporary_data_exists": False,
        "wal_exists": False,
    }},
    "settings": {{
        "allow_community_extensions": "false",
        "autoinstall_known_extensions": "false",
        "autoload_known_extensions": "false",
        "enable_external_access": "false",
        "lock_configuration": "true",
    }},
    "loaded_dynamic_extensions": [],
    "network_attempts": 0,
    "single_writer_enforced": True,
    "second_writer_evidence": writer,
    "g033_excluded_controls": EXCLUDED,
}}
if MODE == "leak_database":
    (workspace / "left-behind.duckdb").write_bytes(b"not-a-real-db")
raw = (
    json.dumps(
        payload,
        ensure_ascii=True,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    + "\\n"
).encode()
descriptor = os.open(
    result_path,
    os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
    0o600,
)
try:
    offset = 0
    while offset < len(raw):
        offset += os.write(descriptor, raw[offset:])
    os.fsync(descriptor)
finally:
    os.close(descriptor)
"""


def _bound_file(tmp_path: Path, role: str) -> DuckDBBoundArtifact:
    path = tmp_path / f"{role}.json"
    path.write_text(f'{{"role":{json.dumps(role)}}}\n', encoding="utf-8")
    path.chmod(0o444)
    return DuckDBBoundArtifact(
        source_path=path.absolute(),
        sha256=_sha256(path),
        size=path.stat().st_size,
    )


def _make_plan(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pinned_python: tuple[Path, str],
    *,
    mode: str = "ok",
    wheel_kind: str = "valid",
    max_seconds: int = 4,
    max_output_bytes: int = 32 * 1024,
) -> DuckDBBootstrapPlan:
    python_path, python_version = pinned_python
    python_tag, platform_tag, filename = _wheel_identity(python_version)
    wheel = tmp_path / filename
    _write_wheel(
        wheel,
        python_tag=python_tag,
        platform_tag=platform_tag,
        kind=wheel_kind,
    )
    run_directory = tmp_path / "run"
    run_directory.mkdir(mode=0o700)
    run_directory.chmod(0o700)
    monkeypatch.setattr(
        duckdb_runner,
        "_FIXED_SMOKE_BOOTSTRAP",
        _synthetic_bootstrap(mode),
    )
    return DuckDBBootstrapPlan(
        schema_version=PLAN_SCHEMA,
        goal_id="WORLDCOIN-G040",
        authorization=_bound_file(tmp_path, "authorization"),
        network_boundary_attestation=_bound_file(tmp_path, "network-attestation"),
        network_policy="external-deny-all",
        python_path=python_path,
        python_sha256=_sha256(python_path),
        python_size=python_path.stat().st_size,
        python_version=python_version,
        wheel_path=wheel.absolute(),
        wheel_sha256=_sha256(wheel),
        wheel_size=wheel.stat().st_size,
        wheel_filename=filename,
        duckdb_version=_DUCKDB_VERSION,
        python_tag=python_tag,
        abi_tag=python_tag,
        platform_tag=platform_tag,
        requirements_lock=_bound_file(tmp_path, "requirements-lock"),
        runtime_policy=_bound_file(tmp_path, "runtime-policy"),
        backup_policy=_bound_file(tmp_path, "backup-policy"),
        storage_adr=_bound_file(tmp_path, "storage-adr"),
        smoke_bootstrap_sha256=duckdb_runner.fixed_smoke_bootstrap_sha256(),
        resource_bounds=DuckDBResourceBounds(
            max_seconds=max_seconds,
            max_memory_mb=256,
            max_output_bytes=max_output_bytes,
            max_file_bytes=16 * 1024 * 1024,
            max_workspace_bytes=16 * 1024 * 1024,
            max_wheel_entries=32,
            max_entry_bytes=1024 * 1024,
            max_uncompressed_bytes=4 * 1024 * 1024,
        ),
        run_directory=run_directory.absolute(),
        expires_at="2099-01-01T00:00:00Z",
    )


def _assert_clean_failure(run_directory: Path) -> None:
    assert not (run_directory / RECEIPT_NAME).exists()
    assert not list(run_directory.glob(".g040-duckdb-bootstrap.*"))
    assert not list(run_directory.glob(f".{RECEIPT_NAME}.*.tmp"))


def test_runner_uses_pinned_python_and_wheel_and_publishes_after_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pinned_python: tuple[Path, str],
) -> None:
    plan = _make_plan(tmp_path, monkeypatch, pinned_python)
    monkeypatch.setenv("AMBIENT_SECRET", "must-not-cross")

    evidence = run_approved_duckdb_bootstrap(plan)

    receipt = plan.run_directory / RECEIPT_NAME
    assert receipt.is_file()
    assert stat.S_IMODE(receipt.stat().st_mode) == 0o600
    assert receipt.read_bytes() == duckdb_runner._canonical_json_bytes(evidence)
    assert evidence["schema_version"] == RECEIPT_SCHEMA
    assert evidence["execution_plan_sha256"] == execution_plan_sha256(plan)
    assert evidence["network_boundary"]["policy"] == "external-deny-all"
    assert evidence["python"]["flags"] == ["-I", "-S", "-B"]
    assert evidence["wheel"]["validation"]["record_count"] == 4
    assert set(evidence["checks"]) == set(REQUIRED_G040_CHECKS)
    assert all(evidence["checks"].values())
    assert evidence["second_writer_evidence"]["exception_type"] == "IOException"
    assert evidence["second_writer_evidence"]["lock_marker"] == "could not set lock"
    assert evidence["cleanup"]["workspace_removed_before_publication"] is True
    assert evidence["production_trust"] is False
    assert not list(plan.run_directory.glob(".g040-duckdb-bootstrap.*"))


def test_plan_rejects_malformed_resource_bounds_with_domain_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pinned_python: tuple[Path, str],
) -> None:
    plan = _make_plan(tmp_path, monkeypatch, pinned_python)

    with pytest.raises(
        G040DuckDBBootstrapError,
        match="resource_bounds must be DuckDBResourceBounds",
    ):
        replace(plan, resource_bounds=object())


@pytest.mark.parametrize(
    ("kind", "message"),
    [
        ("traversal", "unsafe member path|not normalized"),
        ("symlink", "symlink or special file"),
        ("record_mismatch", "digest differs from RECORD"),
        ("wrong_tag", "tags differ"),
    ],
)
def test_wheel_validation_rejects_unsafe_or_unbound_content(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pinned_python: tuple[Path, str],
    kind: str,
    message: str,
) -> None:
    plan = _make_plan(
        tmp_path,
        monkeypatch,
        pinned_python,
        wheel_kind=kind,
    )

    with pytest.raises(G040DuckDBBootstrapError, match=message):
        run_approved_duckdb_bootstrap(plan)

    _assert_clean_failure(plan.run_directory)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("wheel_sha256", "sha256:" + "0" * 64, "wheel digest"),
        ("python_sha256", "sha256:" + "0" * 64, "Python executable digest"),
    ],
)
def test_pinned_digest_mismatch_fails_before_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pinned_python: tuple[Path, str],
    field: str,
    value: str,
    message: str,
) -> None:
    plan = _make_plan(tmp_path, monkeypatch, pinned_python)
    plan = replace(plan, **{field: value})

    with pytest.raises(G040DuckDBBootstrapError, match=message):
        run_approved_duckdb_bootstrap(plan)

    _assert_clean_failure(plan.run_directory)


def test_exact_python_version_is_checked_by_isolated_child(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pinned_python: tuple[Path, str],
) -> None:
    plan = _make_plan(tmp_path, monkeypatch, pinned_python)
    major, minor, patch = plan.python_version.split(".")
    wrong_version = f"{major}.{minor}.{int(patch) + 1}"
    plan = replace(plan, python_version=wrong_version)

    with pytest.raises(G040DuckDBBootstrapError, match="failed with exit code 64"):
        run_approved_duckdb_bootstrap(plan)

    _assert_clean_failure(plan.run_directory)


@pytest.mark.parametrize(
    ("mode", "max_seconds", "max_output", "message"),
    [
        ("timeout", 1, 32 * 1024, "exceeded the 1-second bound"),
        ("spam", 4, 1024, "exceeded the aggregate output bound"),
    ],
)
def test_child_time_and_output_are_bounded(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pinned_python: tuple[Path, str],
    mode: str,
    max_seconds: int,
    max_output: int,
    message: str,
) -> None:
    plan = _make_plan(
        tmp_path,
        monkeypatch,
        pinned_python,
        mode=mode,
        max_seconds=max_seconds,
        max_output_bytes=max_output,
    )

    with pytest.raises(G040DuckDBBootstrapError, match=message):
        run_approved_duckdb_bootstrap(plan)

    _assert_clean_failure(plan.run_directory)


@pytest.mark.parametrize(
    ("mode", "message"),
    [
        ("fail", "failed with exit code 19"),
        ("bad_writer", "non-lock exception class"),
        ("leak_database", "left database or WAL"),
    ],
)
def test_failed_or_forged_smoke_evidence_never_publishes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pinned_python: tuple[Path, str],
    mode: str,
    message: str,
) -> None:
    plan = _make_plan(tmp_path, monkeypatch, pinned_python, mode=mode)

    with pytest.raises(G040DuckDBBootstrapError, match=message):
        run_approved_duckdb_bootstrap(plan)

    _assert_clean_failure(plan.run_directory)


def test_wheel_path_swap_is_detected_after_child_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pinned_python: tuple[Path, str],
) -> None:
    plan = _make_plan(tmp_path, monkeypatch, pinned_python, mode="pause_swap")
    swapped = threading.Event()
    failures: list[BaseException] = []

    def replace_wheel_path() -> None:
        try:
            deadline = time.monotonic() + 4
            while time.monotonic() < deadline:
                if list(plan.run_directory.glob(".g040-duckdb-bootstrap.*/swap-ready")):
                    held = plan.wheel_path.with_name(plan.wheel_path.name + ".held")
                    plan.wheel_path.rename(held)
                    plan.wheel_path.write_bytes(b"replacement")
                    plan.wheel_path.chmod(0o444)
                    swapped.set()
                    return
                time.sleep(0.01)
            raise AssertionError("synthetic child never reached swap point")
        except BaseException as exc:
            failures.append(exc)

    thread = threading.Thread(target=replace_wheel_path)
    thread.start()
    try:
        with pytest.raises(
            G040DuckDBBootstrapError,
            match=("descriptor metadata drifted|path no longer identifies its pinned descriptor"),
        ):
            run_approved_duckdb_bootstrap(plan)
    finally:
        thread.join(timeout=5)

    assert not failures
    assert swapped.is_set()
    _assert_clean_failure(plan.run_directory)


def test_receipt_publication_is_atomic_and_never_replaces_a_racer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pinned_python: tuple[Path, str],
) -> None:
    plan = _make_plan(tmp_path, monkeypatch, pinned_python)
    original_publish = duckdb_runner._publish_receipt

    def publish_after_collision(
        run_descriptor: int,
        run_metadata: tuple[int, ...],
        payload: dict[str, object],
    ) -> None:
        descriptor = os.open(
            RECEIPT_NAME,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
            dir_fd=run_descriptor,
        )
        try:
            os.write(descriptor, b"racer-owned\\n")
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        original_publish(run_descriptor, run_metadata, payload)

    monkeypatch.setattr(duckdb_runner, "_publish_receipt", publish_after_collision)

    with pytest.raises(G040DuckDBBootstrapError, match="already exists"):
        run_approved_duckdb_bootstrap(plan)

    assert (plan.run_directory / RECEIPT_NAME).read_bytes() == b"racer-owned\\n"
    assert not list(plan.run_directory.glob(".g040-duckdb-bootstrap.*"))
    assert not list(plan.run_directory.glob(f".{RECEIPT_NAME}.*.tmp"))


@pytest.mark.parametrize(
    ("expected_lock", "return_code"),
    [(True, 42), (False, 43)],
)
def test_fixed_second_writer_only_accepts_duckdb_lock_conflicts(
    tmp_path: Path,
    pinned_python: tuple[Path, str],
    expected_lock: bool,
    return_code: int,
) -> None:
    python_path, _version = pinned_python
    bootstrap = tmp_path / "bootstrap.py"
    bootstrap.write_text(duckdb_runner._FIXED_SMOKE_BOOTSTRAP, encoding="utf-8")
    bootstrap.chmod(0o444)
    site_root = tmp_path / "site"
    package = site_root / "duckdb"
    package.mkdir(parents=True)
    (site_root / "_duckdb.py").write_text(
        "class IOException(Exception):\n    pass\n",
        encoding="utf-8",
    )
    if expected_lock:
        exception = (
            "from _duckdb import IOException\n"
            "def connect(*args, **kwargs):\n"
            "    raise IOException('IO Error: Could not set lock on file')\n"
        )
    else:
        exception = "def connect(*args, **kwargs):\n    raise ValueError('unrelated configuration failure')\n"
    (package / "__init__.py").write_text(
        f"__version__ = {_DUCKDB_VERSION!r}\n{exception}",
        encoding="utf-8",
    )
    evidence_path = tmp_path / "writer-evidence.json"
    environment = {key: value for key, value in os.environ.items() if key not in {"PYTHONPATH", "PYTHONHOME"}}

    completed = subprocess.run(
        [
            os.fspath(python_path),
            "-I",
            "-S",
            "-B",
            os.fspath(bootstrap),
            "second-writer",
            os.fspath(site_root),
            _DUCKDB_VERSION,
            os.fspath(tmp_path / "database.duckdb"),
            os.fspath(evidence_path),
        ],
        check=False,
        env=environment,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == return_code, completed.stderr
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert evidence["rejected"] is expected_lock
    if expected_lock:
        assert evidence["exception_module"] == "_duckdb"
        assert evidence["exception_type"] == "IOException"
        assert evidence["lock_marker"] == "could not set lock"
    else:
        assert evidence["exception_type"] == "ValueError"
        assert evidence["lock_marker"] is None


def test_outer_module_has_no_cli_or_ambient_authority_entrypoint() -> None:
    source = Path(duckdb_runner.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    top_level_main_guards = [
        node
        for node in tree.body
        if isinstance(node, ast.If)
        and isinstance(node.test, ast.Compare)
        and ast.unparse(node.test).startswith("__name__")
    ]

    assert top_level_main_guards == []
    assert "argparse" not in source
