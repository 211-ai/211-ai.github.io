"""Tests for Abby pilot action speech frames (VOICE-ACTION-024)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.build_abby_action_speech_frames import (
    ALLOWED_SLOT_NAMES,
    FORBIDDEN_CONTENT_FIELDS,
    REQUIRED_ROLES,
    SCHEMA,
    SCHEMA_VERSION,
    SOURCE_LABEL,
    TASK_ID,
    BuildError,
    assert_slot_safe,
    build_corpus_text,
    build_frame_records,
    check_corpus,
    coverage_report_text,
    extract_slot_names,
    frame_id_for,
    load_pilot_logical_actions,
    parse_corpus_text,
    serialize_frames,
    validate_corpus_records,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
BUILD_SCRIPT = REPO_ROOT / "scripts" / "build_abby_action_speech_frames.py"
OUTPUT_PATH = (
    REPO_ROOT / "docs" / "phone_dialog_generation" / "action_speech_frames.jsonl"
)


def _walk_keys(value: object) -> list[str]:
    keys: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            keys.append(str(key))
            keys.extend(_walk_keys(item))
    elif isinstance(value, list):
        for item in value:
            keys.extend(_walk_keys(item))
    return keys


def test_pilot_actions_cover_required_catalog_set() -> None:
    actions = load_pilot_logical_actions()
    expected = {
        "handoff_live_agent",
        "open_app_surface",
        "open_wallet_documents",
        "read_calendar",
        "create_calendar_reminder",
        "read_provider_messages",
        "leave_provider_message",
        "open_service_detail",
        "schedule_service_callback",
        "escalate_safety",
    }
    assert set(actions) == expected
    assert len(actions) == 10


def test_each_pilot_action_has_confirm_success_deny_fail() -> None:
    records = build_frame_records()
    by_action: dict[str, set[str]] = {}
    for row in records:
        by_action.setdefault(row["logical_action"], set()).add(row["role"])
    actions = load_pilot_logical_actions()
    assert len(records) == len(actions) * len(REQUIRED_ROLES)
    for action in actions:
        assert by_action[action] == set(REQUIRED_ROLES)


def test_frame_ids_align_with_action_link_conventions() -> None:
    assert (
        frame_id_for("open_app_surface", "confirm")
        == "frame.action.confirm.open_app_surface.v1"
    )
    assert (
        frame_id_for("open_app_surface", "success")
        == "frame.action.outcome.open_app_surface.success.v1"
    )
    assert (
        frame_id_for("open_app_surface", "deny")
        == "frame.action.outcome.open_app_surface.denied.v1"
    )
    assert (
        frame_id_for("open_app_surface", "fail")
        == "frame.action.outcome.open_app_surface.failed.v1"
    )
    for row in build_frame_records():
        assert row["frame_id"] == frame_id_for(row["logical_action"], row["role"])


def test_texts_are_slot_safe_and_prefer_slot_free() -> None:
    records = build_frame_records()
    for row in records:
        slots = assert_slot_safe(row["spoken_text"], frame_id=row["frame_id"])
        assert list(row["slot_names"]) == list(slots)
        for name in slots:
            assert name in ALLOWED_SLOT_NAMES
        # Pilot corpus is authored slot-free for exact-match audio staging.
        assert slots == ()
        assert "{" not in row["spoken_text"]
        assert "}" not in row["spoken_text"]


def test_unsafe_placeholders_are_rejected() -> None:
    with pytest.raises(BuildError, match="unsafe placeholder"):
        extract_slot_names("Hello {name!r}")
    with pytest.raises(BuildError, match="unsafe placeholder"):
        extract_slot_names("Hello {name:>10}")
    with pytest.raises(BuildError, match="unsafe placeholder"):
        extract_slot_names("Hello {obj.attr}")
    with pytest.raises(BuildError, match="disallowed slot"):
        assert_slot_safe("Call {phone} now", frame_id="frame.action.confirm.x.v1")


def test_no_executable_content_in_records() -> None:
    records = build_frame_records()
    blob = json.dumps(records).casefold()
    for name in FORBIDDEN_CONTENT_FIELDS:
        assert f'"{name}"' not in blob
        assert f"'{name}'" not in blob
    assert "_path" not in json.dumps(list(_walk_keys(records)))
    for row in records:
        assert row["schema"] == SCHEMA
        assert row["schema_version"] == SCHEMA_VERSION
        assert row["source"] == SOURCE_LABEL
        assert row["task_id"] == TASK_ID
        assert row["audio_status"] == "generate_required"


def test_handoff_success_does_not_claim_completed_transfer() -> None:
    records = {
        (row["logical_action"], row["role"]): row["spoken_text"].casefold()
        for row in build_frame_records()
    }
    success = records[("handoff_live_agent", "success")]
    for forbidden in (
        "you are connected",
        "transfer is complete",
        "i transferred you",
        "you are now speaking with",
    ):
        assert forbidden not in success
    assert "provider confirms" in success or "submitted" in success


def test_rebuild_is_byte_stable() -> None:
    first = build_corpus_text()
    second = build_corpus_text()
    assert first == second
    assert first.endswith("\n")
    records = build_frame_records()
    assert serialize_frames(records) == first


def test_coverage_report_marks_complete() -> None:
    records = build_frame_records()
    report = validate_corpus_records(records)
    assert report["complete"] is True
    assert report["pilot_action_count"] == 10
    assert report["frame_count"] == 40
    assert report["generate_required_count"] == 40
    text = coverage_report_text(report)
    assert TASK_ID in text
    assert "10/10" in text
    assert "40 frames" in text


def test_on_disk_artifact_matches_rebuild() -> None:
    assert OUTPUT_PATH.is_file(), f"missing generated artifact: {OUTPUT_PATH}"
    rebuilt = build_corpus_text()
    check_corpus(OUTPUT_PATH, rebuilt)
    on_disk = OUTPUT_PATH.read_text(encoding="utf-8")
    assert on_disk == rebuilt
    rows = parse_corpus_text(on_disk)
    report = validate_corpus_records(rows)
    assert report["complete"] is True
    assert len(rows) == 40
    # JSONL: one object per non-empty line.
    assert on_disk.count("\n") == len(rows)


def test_cli_check_exits_zero_and_emits_coverage() -> None:
    result = subprocess.run(
        [sys.executable, str(BUILD_SCRIPT), "--check"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    assert "coverage:" in result.stdout
    assert "10/10" in result.stdout
    assert "OK" in result.stdout


def test_cli_check_detects_drift(tmp_path: Path) -> None:
    stale = tmp_path / "action_speech_frames.jsonl"
    stale.write_text('{"schema":"stale"}\n', encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            str(BUILD_SCRIPT),
            "--check",
            "--output",
            str(stale),
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "FAILED" in (result.stderr or result.stdout)
