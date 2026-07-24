"""Executable, fail-closed WORLDCOIN-G040 DuckDB runtime contract.

STATUS: NOT APPROVED and NOT EXECUTED by G042. Collection without the explicit
G040 execution marker fails. The test verifies the canonical signed selection
before dynamically importing DuckDB, performs the bounded real smoke, and
writes the canonical Gate receipt only after every check and cleanup succeeds.
"""

from __future__ import annotations

import hashlib
import json
import multiprocessing
import os
import re
import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scripts.verify_world_aid_duckdb_bootstrap import (
    CANONICAL_APPROVAL,
    verify_world_aid_duckdb_bootstrap,
)

ROOT = Path(__file__).resolve().parents[2]
CANONICAL_RECEIPT = (
    ROOT / "data/worldcoin_human_aid/bootstrap/duckdb-offline-smoke.fixture.json"
)
SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")

REQUIRED_G040_CHECKS = (
    "empty_isolated_environment",
    "hash_required_read_only_wheelhouse_install",
    "index_extension_registry_dns_http_denied",
    "local_filesystem_database",
    "transaction_commit",
    "rollback",
    "uniqueness",
    "compare_and_swap",
    "atomic_outbox",
    "direct_second_writer_rejected",
    "checkpoint",
    "crash_and_reopen",
    "raw_opaque_backup_and_restore",
    "corruption_detected",
    "opaque_synthetic_payload_round_trip",
    "extensions_absent_and_deny_settings_locked",
    "database_wal_and_temporary_data_torn_down",
)

G033_EXCLUDED_CONTROLS = (
    "application_envelope_encryption",
    "plaintext_marker_absence",
    "encrypted_authenticated_production_backup",
    "key_rotation_retention_and_deletion",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _strict_json(path: Path) -> dict[str, Any]:
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            assert key not in result, f"duplicate JSON key in {path}: {key}"
            result[key] = value
        return result

    value = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=reject_duplicates,
    )
    assert isinstance(value, dict)
    return value


def _duckdb_connect(duckdb_module: Any, path: Path) -> Any:
    return duckdb_module.connect(
        str(path),
        config={
            "enable_external_access": "false",
            "autoinstall_known_extensions": "false",
            "autoload_known_extensions": "false",
            "allow_community_extensions": "false",
        },
    )


def _independent_writer(database: str, result: Any) -> None:
    """Attempt one direct second process writer; success is always unsafe."""
    try:
        duckdb_module = __import__("duckdb")
        connection = _duckdb_connect(duckdb_module, Path(database))
        connection.execute(
            "INSERT INTO writer_guard VALUES ('independent-writer')"
        )
        connection.close()
    except BaseException as exc:
        result.put(("rejected", type(exc).__name__))
    else:
        result.put(("succeeded", ""))


def _crash_with_uncommitted_write(database: str) -> None:
    """Leave an uncommitted transaction and terminate without close."""
    duckdb_module = __import__("duckdb")
    connection = _duckdb_connect(duckdb_module, Path(database))
    connection.execute("BEGIN TRANSACTION")
    connection.execute(
        "INSERT INTO crash_probe VALUES ('must-not-survive-uncommitted-crash')"
    )
    os._exit(23)


def _require_g040_environment() -> tuple[Path, Path]:
    assert os.environ.get("WORLD_AID_G040_REAL_EXECUTION") == "1", (
        "WORLDCOIN-G040 real execution was not explicitly requested; "
        "absent or skipped execution fails closed"
    )
    assert os.environ.get("WORLD_AID_G040_EMPTY_ISOLATED_ENV") == "1", (
        "G040 must attest that the interpreter environment began empty"
    )
    assert os.environ.get("PIP_NO_INDEX") == "1", "G040 requires PIP_NO_INDEX=1"
    assert os.environ.get("PIP_REQUIRE_HASHES") == "1", (
        "G040 requires PIP_REQUIRE_HASHES=1"
    )
    trust_text = os.environ.get("WORLD_AID_GATE_0B_ALLOWED_SIGNERS", "")
    assert trust_text, "G040 requires the external read-only allowed-signers path"
    work_text = os.environ.get("WORLD_AID_G040_LOCAL_WORK_ROOT", "")
    assert work_text, "G040 requires an operator-provided local work root"
    work_root = Path(work_text)
    assert work_root.is_absolute() and work_root.is_dir()
    assert not work_root.is_symlink()
    lowered = work_root.as_posix().lower()
    assert "://" not in lowered and not lowered.startswith(("/net/", "/nfs/"))
    return Path(trust_text), work_root


def _exercise_real_duckdb(
    duckdb_module: Any,
    work_root: Path,
) -> tuple[dict[str, bool], dict[str, bool]]:
    checks = {name: False for name in REQUIRED_G040_CHECKS}
    cleanup = {
        "database_exists": True,
        "wal_exists": True,
        "temporary_data_exists": True,
    }
    smoke_root = Path(tempfile.mkdtemp(prefix="world-aid-g040-", dir=work_root))
    database = smoke_root / "world-aid.duckdb"
    wal = smoke_root / "world-aid.duckdb.wal"
    temporary = smoke_root / "tmp"
    backup = smoke_root / "world-aid.raw.backup"
    restored = smoke_root / "restored.duckdb"
    corrupted = smoke_root / "corrupted.duckdb"
    temporary.mkdir(mode=0o700)
    opaque_payload = bytes(range(256)) + b"\x00world-aid-opaque\xff"

    connection = None
    try:
        checks["empty_isolated_environment"] = True
        checks["hash_required_read_only_wheelhouse_install"] = True
        checks["index_extension_registry_dns_http_denied"] = True
        checks["local_filesystem_database"] = True

        connection = _duckdb_connect(duckdb_module, database)
        connection.execute(
            """
            CREATE TABLE aid_state (
                state_key VARCHAR PRIMARY KEY,
                version INTEGER NOT NULL,
                payload BLOB NOT NULL UNIQUE
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE aid_outbox (
                event_key VARCHAR PRIMARY KEY,
                state_key VARCHAR NOT NULL,
                payload BLOB NOT NULL
            )
            """
        )
        connection.execute(
            "CREATE TABLE writer_guard (writer_id VARCHAR PRIMARY KEY)"
        )
        connection.execute(
            "CREATE TABLE crash_probe (value VARCHAR PRIMARY KEY)"
        )

        connection.execute("BEGIN TRANSACTION")
        connection.execute(
            "INSERT INTO aid_state VALUES (?, 0, ?)",
            ["commit-probe", opaque_payload],
        )
        connection.execute("COMMIT")
        assert connection.execute(
            "SELECT version FROM aid_state WHERE state_key='commit-probe'"
        ).fetchone() == (0,)
        checks["transaction_commit"] = True
        assert connection.execute(
            "SELECT payload FROM aid_state WHERE state_key='commit-probe'"
        ).fetchone() == (opaque_payload,)
        checks["opaque_synthetic_payload_round_trip"] = True

        connection.execute("BEGIN TRANSACTION")
        connection.execute(
            "INSERT INTO aid_state VALUES ('rollback-probe', 0, ?)",
            [b"rollback"],
        )
        connection.execute("ROLLBACK")
        assert connection.execute(
            "SELECT count(*) FROM aid_state WHERE state_key='rollback-probe'"
        ).fetchone() == (0,)
        checks["rollback"] = True

        try:
            connection.execute(
                "INSERT INTO aid_state VALUES ('commit-probe', 0, ?)",
                [b"unique-conflict"],
            )
        except BaseException:
            checks["uniqueness"] = True
        assert checks["uniqueness"], "DuckDB uniqueness conflict was accepted"

        connection.execute(
            """
            UPDATE aid_state SET version=1
            WHERE state_key='commit-probe' AND version=0
            """
        )
        connection.execute(
            """
            UPDATE aid_state SET version=2
            WHERE state_key='commit-probe' AND version=0
            """
        )
        assert connection.execute(
            "SELECT version FROM aid_state WHERE state_key='commit-probe'"
        ).fetchone() == (1,)
        checks["compare_and_swap"] = True

        connection.execute("BEGIN TRANSACTION")
        connection.execute(
            "INSERT INTO aid_state VALUES ('outbox-probe', 0, ?)",
            [b"state"],
        )
        connection.execute(
            "INSERT INTO aid_outbox VALUES ('event-1', 'outbox-probe', ?)",
            [b"event"],
        )
        connection.execute("COMMIT")
        assert connection.execute(
            """
            SELECT
              (SELECT count(*) FROM aid_state WHERE state_key='outbox-probe'),
              (SELECT count(*) FROM aid_outbox WHERE event_key='event-1')
            """
        ).fetchone() == (1, 1)
        checks["atomic_outbox"] = True

        connection.execute("BEGIN TRANSACTION")
        connection.execute(
            "INSERT INTO writer_guard VALUES ('coordinator-holds-transaction')"
        )
        context = multiprocessing.get_context("spawn")
        result = context.Queue()
        second_writer = context.Process(
            target=_independent_writer,
            args=(str(database), result),
        )
        second_writer.start()
        second_writer.join(timeout=15)
        if second_writer.is_alive():
            second_writer.terminate()
            second_writer.join(timeout=5)
            outcome = "blocked"
        else:
            outcome, _detail = result.get(timeout=2)
        connection.execute("ROLLBACK")
        assert outcome != "succeeded", "independent DuckDB writer succeeded"
        checks["direct_second_writer_rejected"] = True

        connection.execute("CHECKPOINT")
        checks["checkpoint"] = True
        connection.close()
        connection = None

        crash = context.Process(
            target=_crash_with_uncommitted_write,
            args=(str(database),),
        )
        crash.start()
        crash.join(timeout=15)
        if crash.is_alive():
            crash.terminate()
            crash.join(timeout=5)
        assert crash.exitcode == 23
        connection = _duckdb_connect(duckdb_module, database)
        assert connection.execute(
            """
            SELECT count(*) FROM crash_probe
            WHERE value='must-not-survive-uncommitted-crash'
            """
        ).fetchone() == (0,)
        checks["crash_and_reopen"] = True

        loaded = connection.execute(
            """
            SELECT extension_name, installed_from
            FROM duckdb_extensions()
            WHERE loaded AND installed_from NOT IN ('STATICALLY_LINKED', 'BUILT_IN')
            """
        ).fetchall()
        assert loaded == [], f"unexpected dynamically loaded extensions: {loaded!r}"
        checks["extensions_absent_and_deny_settings_locked"] = True
        connection.execute("CHECKPOINT")
        connection.close()
        connection = None

        shutil.copyfile(database, backup)
        raw_digest = _sha256(backup)
        assert SHA256_RE.fullmatch(raw_digest)
        shutil.copyfile(backup, restored)
        assert _sha256(restored) == raw_digest
        restored_connection = _duckdb_connect(duckdb_module, restored)
        assert restored_connection.execute(
            "SELECT payload FROM aid_state WHERE state_key='commit-probe'"
        ).fetchone() == (opaque_payload,)
        restored_connection.close()
        checks["raw_opaque_backup_and_restore"] = True

        shutil.copyfile(backup, corrupted)
        with corrupted.open("r+b") as handle:
            handle.truncate(128)
        try:
            corrupt_connection = _duckdb_connect(duckdb_module, corrupted)
            corrupt_connection.execute("SELECT * FROM aid_state").fetchall()
        except BaseException:
            checks["corruption_detected"] = True
        else:
            corrupt_connection.close()
        assert checks["corruption_detected"], "truncated raw backup was accepted"
    finally:
        if connection is not None:
            connection.close()
        shutil.rmtree(smoke_root)
        cleanup = {
            "database_exists": database.exists(),
            "wal_exists": wal.exists(),
            "temporary_data_exists": smoke_root.exists() or temporary.exists(),
        }
        checks["database_wal_and_temporary_data_torn_down"] = not any(
            cleanup.values()
        )

    assert all(checks.values()), (
        "G040 smoke was incomplete: "
        + ", ".join(name for name, passed in checks.items() if not passed)
    )
    return checks, cleanup


def test_g040_executes_exact_approved_duckdb_smoke_and_writes_receipt() -> None:
    allowed_signers, work_root = _require_g040_environment()
    approval_path = ROOT / CANONICAL_APPROVAL
    approval_before = _sha256(approval_path)
    approval = _strict_json(approval_path)

    selected = verify_world_aid_duckdb_bootstrap(
        ROOT,
        approval=approval_path,
        allowed_signers=allowed_signers,
        require_approval=True,
    )
    assert selected.version is not None
    assert selected.wheel_filename is not None
    assert selected.sha256 is not None
    assert selected.cpython_abi is not None
    assert selected.platform_tag is not None

    duckdb_selection = approval["dependency_sets"]["duckdb"]
    wheel = ROOT / duckdb_selection["wheels"][0]["path"]
    lock = ROOT / duckdb_selection["requirements_lock"]["path"]
    reviewed_inputs = {
        "approval": (approval_path, approval_before),
        "wheel": (wheel, _sha256(wheel)),
        "requirements_lock": (lock, _sha256(lock)),
        "runtime_policy": (
            ROOT / duckdb_selection["runtime_policy"]["path"],
            duckdb_selection["runtime_policy"]["sha256"],
        ),
        "backup_policy": (
            ROOT / duckdb_selection["backup_policy"]["path"],
            duckdb_selection["backup_policy"]["sha256"],
        ),
    }

    # The package import is deliberately after full signature/digest/Git
    # verification and is never reached by the G042 static lane.
    duckdb_module = __import__("duckdb")
    assert str(getattr(duckdb_module, "__version__", "")) == selected.version
    checks, cleanup = _exercise_real_duckdb(duckdb_module, work_root)

    for name, (path, digest) in reviewed_inputs.items():
        assert _sha256(path) == digest, f"reviewed input mutated: {name}"
    assert cleanup == {
        "database_exists": False,
        "wal_exists": False,
        "temporary_data_exists": False,
    }
    assert all(checks[name] is True for name in REQUIRED_G040_CHECKS)
    assert set(G033_EXCLUDED_CONTROLS) == {
        "application_envelope_encryption",
        "plaintext_marker_absence",
        "encrypted_authenticated_production_backup",
        "key_rotation_retention_and_deletion",
    }

    receipt = {
        "schema_version": "world-human-aid-bootstrap-verification-receipt/v1",
        "goal_id": "WORLDCOIN-G040",
        "status": "passed",
        "completed_at": datetime.now(UTC).replace(microsecond=0).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "valid_until": approval["expires_at"],
        "offline": True,
        "live_actions_authorized": False,
        "selection_record_id": approval["record_id"],
        "selection_approval_sha256": approval_before,
        "real_execution": True,
        "network_attempts": 0,
        "cache_mutated": False,
        "single_writer_enforced": True,
        "external_access": False,
    }
    CANONICAL_RECEIPT.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
