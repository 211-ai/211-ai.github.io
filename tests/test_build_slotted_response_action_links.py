"""Tests for deterministic slotted DAG action-link projection (VOICE-ACTION-005)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from ipfs_datasets_py.voice.action_links import (
    ACTION_LINK_SCHEMA,
    ACTION_LINK_SCHEMA_VERSION,
    NO_ACTION,
    FORBIDDEN_CONTENT_FIELDS,
    parse_action_link_document,
)
from scripts.build_slotted_response_action_links import (
    CONTENT_ONLY_ROUTES,
    EXPECTED_ROUTE_COUNT,
    ROUTE_ACTION_PROJECTION,
    SOURCE_LABEL,
    TOOL_ADJACENT_ROUTES,
    build_action_link_document,
    build_projection_text,
    check_projection,
    document_payload,
    serialize_document,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = REPO_ROOT / "scripts" / "build_slotted_response_action_links.py"
OUTPUT_PATH = (
    REPO_ROOT / "docs" / "phone_dialog_generation" / "slotted_response_action_links.json"
)
SLOTTED_DAG = REPO_ROOT / "docs" / "phone_dialog_generation" / "slotted_response_dag.json"


def test_projection_table_covers_exactly_twelve_routes() -> None:
    assert len(ROUTE_ACTION_PROJECTION) == EXPECTED_ROUTE_COUNT
    assert EXPECTED_ROUTE_COUNT == 12
    assert sorted(ROUTE_ACTION_PROJECTION) == sorted(ROUTE_ACTION_PROJECTION.keys())


def test_build_document_has_all_routes_sorted() -> None:
    document = build_action_link_document()
    routes = [link.route for link in document.links]
    assert len(routes) == EXPECTED_ROUTE_COUNT
    assert routes == sorted(routes)
    assert set(routes) == set(ROUTE_ACTION_PROJECTION)
    assert document.schema == ACTION_LINK_SCHEMA
    assert document.schema_version == ACTION_LINK_SCHEMA_VERSION
    assert document.source == SOURCE_LABEL


def test_tool_adjacent_routes_map_to_pilot_logical_actions() -> None:
    document = build_action_link_document()
    by_route = document.by_route()
    for route in TOOL_ADJACENT_ROUTES:
        link = by_route[route]
        expected = ROUTE_ACTION_PROJECTION[route]["logical_action"]
        assert link.logical_action == expected
        assert link.logical_action != NO_ACTION
        assert link.classification == "proposal-eligible"
        assert link.may_propose is True
        assert link.confirmation_frame_id is not None
        assert link.confirmation_frame_id.startswith("frame.action.confirm.")
        assert set(link.outcome_frame_ids) == {
            "success",
            "denied",
            "failed",
            "cancelled",
            "unknown",
        }


def test_content_only_routes_map_to_no_action() -> None:
    document = build_action_link_document()
    by_route = document.by_route()
    assert CONTENT_ONLY_ROUTES == frozenset(
        {
            "clarifying_prompt",
            "repeat_or_restate",
            "speech_unclear_clarification",
            "template_guided_fallback",
        }
    )
    for route in CONTENT_ONLY_ROUTES:
        link = by_route[route]
        assert link.logical_action == NO_ACTION
        assert link.classification == "content-only"
        assert link.is_no_action is True
        assert link.may_propose is False
        assert link.confirmation_frame_id is None
        assert dict(link.outcome_frame_ids) == {}


def test_non_content_only_routes_use_pilot_catalog_ids() -> None:
    document = build_action_link_document()
    pilot_actions = {
        "open_app_surface",
        "open_calendar_support",
        "open_service_detail",
        "handoff_live_agent",
        "provide_provider_contact",
        "escalate_safety",
        "review_service_interaction",
        "open_wallet_documents",
    }
    for link in document.links:
        if link.classification == "content-only":
            continue
        assert link.logical_action in pilot_actions
        assert link.logical_action != NO_ACTION


def test_rebuild_is_byte_stable() -> None:
    first = build_projection_text(dag_path=SLOTTED_DAG)
    second = build_projection_text(dag_path=SLOTTED_DAG)
    assert first == second
    assert first.endswith("\n")
    # Independent serialization path must match.
    document = build_action_link_document()
    assert serialize_document(document) == first


def test_on_disk_artifact_matches_rebuild_and_parses() -> None:
    assert OUTPUT_PATH.is_file(), f"missing generated artifact: {OUTPUT_PATH}"
    rebuilt = build_projection_text(dag_path=SLOTTED_DAG)
    check_projection(OUTPUT_PATH, rebuilt)
    on_disk = OUTPUT_PATH.read_text(encoding="utf-8")
    assert on_disk == rebuilt
    payload = json.loads(on_disk)
    document = parse_action_link_document(payload)
    assert len(document.links) == EXPECTED_ROUTE_COUNT
    assert payload["schema"] == ACTION_LINK_SCHEMA
    assert payload["schema_version"] == ACTION_LINK_SCHEMA_VERSION
    assert payload["source"] == SOURCE_LABEL
    # Export omits derived digests; parse recomputes stable link/document ids.
    assert "content_digest" not in payload
    assert "document_id" not in payload
    for raw_link, link in zip(payload["links"], document.links, strict=True):
        assert "link_id" not in raw_link
        assert link.link_id.startswith("action-link-")
    assert document.document_id.startswith("action-link-doc-")


def test_payload_rejects_forbidden_content_fields() -> None:
    payload = document_payload(build_action_link_document())
    blob = json.dumps(payload).casefold()
    for name in FORBIDDEN_CONTENT_FIELDS:
        assert f'"{name}"' not in blob
        assert f"'{name}'" not in blob
    # Path-suffix smuggling must not appear as keys.
    assert "_path" not in json.dumps(list(_walk_keys(payload)))


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


def test_logical_action_for_missing_route_fails_closed() -> None:
    document = build_action_link_document()
    assert document.logical_action_for("not_a_real_route") == NO_ACTION


def test_cli_check_exits_zero() -> None:
    if not SLOTTED_DAG.is_file():
        pytest.skip("slotted response DAG not present")
    result = subprocess.run(
        [sys.executable, str(BUILD_SCRIPT), "--check"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    assert "OK" in result.stdout


def test_cli_check_detects_drift(tmp_path: Path) -> None:
    if not SLOTTED_DAG.is_file():
        pytest.skip("slotted response DAG not present")
    stale = tmp_path / "slotted_response_action_links.json"
    stale.write_text('{"schema":"stale"}\n', encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            str(BUILD_SCRIPT),
            "--check",
            "--output",
            str(stale),
            "--slotted-dag",
            str(SLOTTED_DAG),
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "FAILED" in result.stderr or "drift" in result.stderr.casefold()


def test_cli_write_is_idempotent(tmp_path: Path) -> None:
    if not SLOTTED_DAG.is_file():
        pytest.skip("slotted response DAG not present")
    out = tmp_path / "out.json"
    cmd = [
        sys.executable,
        str(BUILD_SCRIPT),
        "--write",
        "--output",
        str(out),
        "--slotted-dag",
        str(SLOTTED_DAG),
    ]
    first = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True)
    assert first.returncode == 0, first.stderr
    body = out.read_text(encoding="utf-8")
    second = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True)
    assert second.returncode == 0, second.stderr
    assert out.read_text(encoding="utf-8") == body
    check = subprocess.run(
        [
            sys.executable,
            str(BUILD_SCRIPT),
            "--check",
            "--output",
            str(out),
            "--slotted-dag",
            str(SLOTTED_DAG),
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert check.returncode == 0, check.stderr
