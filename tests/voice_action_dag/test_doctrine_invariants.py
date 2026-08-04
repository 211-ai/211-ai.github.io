"""Non-negotiable dual-plane doctrine invariants for VOICE-ACTION-003.

These tests freeze content vs authority planes, package ownership, forbidden
content executables, confirmation rules, and handoff truthfulness as
assertions over the normative doctrine document and assurance-verdict schema.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCTRINE = REPO_ROOT / "docs" / "voice_action_dag" / "INTEGRATION_DOCTRINE.md"
SCHEMA = (
    REPO_ROOT
    / "docs"
    / "voice_action_dag"
    / "schemas"
    / "assurance-verdict-v1.schema.json"
)

PROGRAM_ID = "voice-action-dag-abby-v1"
BOARD_NAMESPACE = "voice-action-dag-abby-v1"
DOCTRINE_ID = "voice-action/integration-doctrine@1"
VERDICT_SCHEMA_ID = "voice-action/assurance-verdict@1"

REQUIRED_OWNERS = (
    "ipfs_datasets_py",
    "ipfs_accelerate_py",
    "wallet_interface",
    "docs/phone_dialog_generation",
)

FORBIDDEN_CONTENT_FIELDS = (
    "command",
    "argv",
    "executable",
    "shell",
    "cwd",
    "env",
    "import_path",
    "url",
)

REQUIRED_INVARIANT_IDS = (
    "INV-PLANE-001",
    "INV-OWN-001",
    "INV-CONTENT-001",
    "INV-PROP-001",
    "INV-CONF-001",
    "INV-AUTH-001",
    "INV-HAND-001",
    "INV-RCPT-001",
)

BANNED_PROPOSAL_ARGUMENT_KEYS = frozenset(
    {
        "command",
        "argv",
        "executable",
        "cwd",
        "env",
        "shell",
        "import_path",
        "url",
    }
)


@pytest.fixture(scope="module")
def doctrine_text() -> str:
    assert DOCTRINE.is_file(), f"missing doctrine: {DOCTRINE}"
    return DOCTRINE.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def verdict_schema() -> dict[str, Any]:
    assert SCHEMA.is_file(), f"missing schema: {SCHEMA}"
    data = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def test_declared_outputs_exist() -> None:
    assert DOCTRINE.is_file()
    assert SCHEMA.is_file()


def test_doctrine_states_content_and_authority_planes(doctrine_text: str) -> None:
    lower = doctrine_text.lower()
    assert "content plane" in lower
    assert "authority plane" in lower
    assert "dual-plane" in lower or "dual plane" in lower
    # Planes must remain distinct: content emits proposals; authority executes.
    assert "logical actionproposal" in lower or "logical action proposal" in lower
    assert "actionreceipt" in lower or "action receipt" in lower
    # Frozen dual-plane rule block (content -> proposal; authority -> receipt).
    assert re.search(
        r"content plane[^\n]*\n\s*->\s*logical\s+ActionProposal",
        doctrine_text,
        re.IGNORECASE,
    )
    assert re.search(
        r"authority plane[^\n]*\n\s*->\s*ActionReceipt",
        doctrine_text,
        re.IGNORECASE,
    )
    assert re.search(
        r"authority plane[\s\S]{0,200}(catalog|policy|confirmation|adapter)",
        doctrine_text,
        re.IGNORECASE,
    )


def test_doctrine_lists_package_ownership(doctrine_text: str) -> None:
    assert "package ownership" in doctrine_text.lower()
    for owner in REQUIRED_OWNERS:
        assert owner in doctrine_text, f"missing owner {owner!r}"
    # Ownership map must assign content vs authority responsibilities.
    assert "Abby content" in doctrine_text or "content→action" in doctrine_text
    assert "action_runtime" in doctrine_text
    assert "UI confirm" in doctrine_text or "confirm/execute" in doctrine_text


def test_doctrine_forbids_content_executables(doctrine_text: str) -> None:
    lower = doctrine_text.lower()
    assert "forbidden content executables" in lower or "forbid" in lower
    for field in FORBIDDEN_CONTENT_FIELDS:
        assert field in doctrine_text, f"doctrine must forbid content field {field!r}"
    assert "never embeds executables" in lower or "never" in lower and "executable" in lower
    assert "credentials" in lower
    # Content may name logical actions only.
    assert "logical_action" in doctrine_text or "logical action" in lower


def test_doctrine_defines_confirmation_rules(doctrine_text: str) -> None:
    lower = doctrine_text.lower()
    assert "confirmation" in lower
    assert "retrieval alone never executes" in lower or (
        "retrieval" in lower and "never execute" in lower
    )
    assert "deny without confirm" in lower or "denied when confirmation is absent" in lower
    assert "write" in lower and ("auth" in lower or "authenticated" in lower)
    assert "requires_confirmation" in doctrine_text or "require confirmation" in lower


def test_doctrine_defines_handoff_truthfulness_rules(doctrine_text: str) -> None:
    lower = doctrine_text.lower()
    assert "handoff truthfulness" in lower
    assert "never claim unverified transfer success" in lower or (
        "never" in lower and "unverified" in lower and "transfer" in lower
    )
    assert "live_agent" in doctrine_text
    assert "handoff_live_agent" in doctrine_text
    assert "provider confirmation" in lower or "provider confirmation receipt" in lower
    assert "metadata-only" in lower or "metadata only" in lower


def test_doctrine_encodes_named_invariants(doctrine_text: str) -> None:
    for inv_id in REQUIRED_INVARIANT_IDS:
        assert inv_id in doctrine_text, f"missing invariant id {inv_id}"
    assert "authority monotonicity" in doctrine_text.lower() or "INV-AUTH-001" in doctrine_text


def test_assurance_schema_identity_and_required_keys(verdict_schema: dict[str, Any]) -> None:
    assert verdict_schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert verdict_schema["type"] == "object"
    assert verdict_schema.get("additionalProperties") is False
    required = set(verdict_schema["required"])
    for key in (
        "schema",
        "program_id",
        "board_namespace",
        "doctrine_id",
        "planes",
        "package_ownership",
        "forbidden_content_fields",
        "confirmation_rules",
        "handoff_truthfulness",
        "invariants",
        "verdict",
        "evidence",
    ):
        assert key in required, f"schema missing required key {key!r}"
    props = verdict_schema["properties"]
    assert props["schema"]["const"] == VERDICT_SCHEMA_ID
    assert props["program_id"]["const"] == PROGRAM_ID
    assert props["board_namespace"]["const"] == BOARD_NAMESPACE
    assert props["doctrine_id"]["const"] == DOCTRINE_ID


def test_assurance_schema_encodes_dual_plane_separation(
    verdict_schema: dict[str, Any],
) -> None:
    planes = verdict_schema["properties"]["planes"]
    assert planes["type"] == "object"
    assert set(planes["required"]) >= {"content", "authority", "separation_enforced"}
    content = planes["properties"]["content"]
    authority = planes["properties"]["authority"]
    assert content["properties"]["may_execute"]["const"] is False
    assert content["properties"]["may_emit_logical_proposals"]["const"] is True
    for flag in (
        "owns_catalog",
        "owns_policy",
        "owns_confirmation",
        "owns_adapters",
        "owns_receipts",
    ):
        assert authority["properties"][flag]["const"] is True
    assert planes["properties"]["separation_enforced"]["const"] is True


def test_assurance_schema_lists_package_owners(verdict_schema: dict[str, Any]) -> None:
    owner_def = verdict_schema["$defs"]["packageOwner"]
    owners = set(owner_def["properties"]["owner"]["enum"])
    assert owners == set(REQUIRED_OWNERS)
    ownership = verdict_schema["properties"]["package_ownership"]
    assert ownership["minItems"] == 4


def test_assurance_schema_forbids_content_executables(
    verdict_schema: dict[str, Any],
) -> None:
    forbidden = verdict_schema["properties"]["forbidden_content_fields"]
    enum_vals = set(forbidden["items"]["enum"])
    for field in FORBIDDEN_CONTENT_FIELDS:
        assert field in enum_vals
    assert forbidden["minItems"] >= 8
    assert verdict_schema["properties"]["forbidden_content_path_suffix"]["const"] == "_path"


def test_assurance_schema_confirmation_and_handoff_rules(
    verdict_schema: dict[str, Any],
) -> None:
    conf = verdict_schema["properties"]["confirmation_rules"]
    for key in (
        "retrieval_alone_never_executes",
        "read_requires_confirmation",
        "write_requires_confirmation_and_auth",
        "deny_without_confirm",
        "safety_auto_path_documented",
    ):
        assert conf["properties"][key]["const"] is True
        assert key in conf["required"]

    handoff = verdict_schema["properties"]["handoff_truthfulness"]
    for key in (
        "never_claim_unverified_transfer_success",
        "metadata_only_is_not_success",
        "request_distinct_from_completed_transfer",
        "outcome_speech_requires_receipt",
    ):
        assert handoff["properties"][key]["const"] is True
        assert key in handoff["required"]
    assert handoff["properties"]["live_agent_route"]["const"] == "live_agent"
    assert handoff["properties"]["logical_action"]["const"] == "handoff_live_agent"


def test_assurance_schema_verdict_is_fail_closed(verdict_schema: dict[str, Any]) -> None:
    verdict = verdict_schema["properties"]["verdict"]
    assert set(verdict["enum"]) == {"pass", "fail", "unknown"}
    # Verdicts never grant execute authority.
    assert verdict_schema["properties"]["verdict_grants_execute"]["const"] is False
    assert verdict_schema["properties"]["fail_closed"]["const"] is True


def test_canonical_passing_verdict_fixture_matches_schema_constants(
    verdict_schema: dict[str, Any],
) -> None:
    """Build a minimal passing verdict and assert structural invariants."""

    fixture = _canonical_passing_verdict()
    _assert_verdict_structure(fixture, verdict_schema)


def test_proposal_argument_ban_matches_doctrine_and_runtime_contract(
    doctrine_text: str,
) -> None:
    """Content/proposal ban list is a non-negotiable assertion set."""

    for key in BANNED_PROPOSAL_ARGUMENT_KEYS:
        assert key in doctrine_text
    # Keys ending in _path are also banned as executable smuggling.
    assert "_path" in doctrine_text
    # Runtime contract documents the same ban (read-only cross-check when present).
    contracts = (
        REPO_ROOT
        / "ipfs_accelerate_py"
        / "ipfs_accelerate_py"
        / "action_runtime"
        / "contracts.py"
    )
    if contracts.is_file():
        source = contracts.read_text(encoding="utf-8")
        assert "Proposals never carry executable locators" in source
        for key in BANNED_PROPOSAL_ARGUMENT_KEYS:
            assert f'"{key}"' in source or f"'{key}'" in source


def test_weakened_content_may_execute_is_rejected_by_schema(
    verdict_schema: dict[str, Any],
) -> None:
    """Schema constants must refuse content-plane execution."""

    content_may_execute = verdict_schema["properties"]["planes"]["properties"]["content"][
        "properties"
    ]["may_execute"]["const"]
    assert content_may_execute is False
    # A forged verdict claiming content may execute is invalid against frozen const.
    forged = _canonical_passing_verdict()
    forged["planes"]["content"]["may_execute"] = True
    with pytest.raises(AssertionError):
        _assert_verdict_structure(forged, verdict_schema)


def test_weakened_handoff_truthfulness_is_rejected(
    verdict_schema: dict[str, Any],
) -> None:
    forged = _canonical_passing_verdict()
    forged["handoff_truthfulness"]["never_claim_unverified_transfer_success"] = False
    with pytest.raises(AssertionError):
        _assert_verdict_structure(forged, verdict_schema)


def test_missing_owner_is_rejected(verdict_schema: dict[str, Any]) -> None:
    forged = _canonical_passing_verdict()
    forged["package_ownership"] = [
        row for row in forged["package_ownership"] if row["owner"] != "ipfs_datasets_py"
    ]
    with pytest.raises(AssertionError):
        _assert_verdict_structure(forged, verdict_schema)


# ---------------------------------------------------------------------------
# Structural validators (stdlib-only; no jsonschema dependency required)
# ---------------------------------------------------------------------------


def _canonical_passing_verdict() -> dict[str, Any]:
    return {
        "schema": VERDICT_SCHEMA_ID,
        "program_id": PROGRAM_ID,
        "board_namespace": BOARD_NAMESPACE,
        "doctrine_id": DOCTRINE_ID,
        "doctrine_path": "docs/voice_action_dag/INTEGRATION_DOCTRINE.md",
        "issued_at": "2026-08-04T00:00:00Z",
        "subject": {
            "task_id": "VOICE-ACTION-003",
            "goal_id": "VOICE-ACTION-G010",
        },
        "planes": {
            "content": {
                "name": "content",
                "description": "Abby DAG / GraphRAG / audio",
                "may_emit_logical_proposals": True,
                "may_execute": False,
                "assets": ["slotted_response_dag", "graphrag", "audio_library"],
            },
            "authority": {
                "name": "authority",
                "description": "catalog / policy / confirmation / adapter",
                "owns_catalog": True,
                "owns_policy": True,
                "owns_confirmation": True,
                "owns_adapters": True,
                "owns_receipts": True,
            },
            "separation_enforced": True,
            "authority_monotonicity": "retrieval_never_increases_authority",
        },
        "package_ownership": [
            {
                "owner": "ipfs_datasets_py",
                "plane_focus": "content",
                "owns": ["action links", "GraphRAG candidates", "audio frame indexes"],
            },
            {
                "owner": "ipfs_accelerate_py",
                "plane_focus": "authority+orchestration",
                "owns": ["action_runtime", "adapters", "policy", "voice_router hooks"],
            },
            {
                "owner": "wallet_interface",
                "plane_focus": "product/UI",
                "owns": ["UI confirm/execute", "app tool bindings"],
            },
            {
                "owner": "docs/phone_dialog_generation",
                "plane_focus": "content-generation",
                "owns": ["slotted DAG rebuild outputs"],
            },
        ],
        "forbidden_content_fields": list(FORBIDDEN_CONTENT_FIELDS),
        "forbidden_content_path_suffix": "_path",
        "confirmation_rules": {
            "retrieval_alone_never_executes": True,
            "read_requires_confirmation": True,
            "write_requires_confirmation_and_auth": True,
            "deny_without_confirm": True,
            "safety_auto_path_documented": True,
            "descriptor_requires_confirmation_honored": True,
        },
        "handoff_truthfulness": {
            "never_claim_unverified_transfer_success": True,
            "metadata_only_is_not_success": True,
            "request_distinct_from_completed_transfer": True,
            "outcome_speech_requires_receipt": True,
            "live_agent_route": "live_agent",
            "logical_action": "handoff_live_agent",
        },
        "invariants": [
            {
                "id": inv_id,
                "statement": f"Doctrine invariant {inv_id}",
                "satisfied": True,
            }
            for inv_id in REQUIRED_INVARIANT_IDS
        ],
        "verdict": "pass",
        "verdict_grants_execute": False,
        "fail_closed": True,
        "reasons": ["doctrine frozen and invariants satisfied"],
        "evidence": [
            {
                "kind": "doctrine",
                "ref": "docs/voice_action_dag/INTEGRATION_DOCTRINE.md",
            },
            {
                "kind": "schema",
                "ref": "docs/voice_action_dag/schemas/assurance-verdict-v1.schema.json",
            },
            {
                "kind": "test",
                "ref": "tests/voice_action_dag/test_doctrine_invariants.py",
            },
        ],
    }


def _assert_verdict_structure(
    verdict: dict[str, Any],
    schema: dict[str, Any],
) -> None:
    """Fail-closed structural check aligned with frozen schema constants."""

    props = schema["properties"]
    assert verdict.get("schema") == props["schema"]["const"]
    assert verdict.get("program_id") == props["program_id"]["const"]
    assert verdict.get("board_namespace") == props["board_namespace"]["const"]
    assert verdict.get("doctrine_id") == props["doctrine_id"]["const"]
    assert re.match(
        r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$",
        str(verdict.get("issued_at", "")),
    )

    planes = verdict["planes"]
    assert planes["separation_enforced"] is True
    assert planes["content"]["may_execute"] is False
    assert planes["content"]["may_emit_logical_proposals"] is True
    assert planes["content"]["name"] == "content"
    for flag in (
        "owns_catalog",
        "owns_policy",
        "owns_confirmation",
        "owns_adapters",
        "owns_receipts",
    ):
        assert planes["authority"][flag] is True

    owners = {row["owner"] for row in verdict["package_ownership"]}
    assert owners == set(REQUIRED_OWNERS)
    assert len(verdict["package_ownership"]) >= 4

    forbidden = set(verdict["forbidden_content_fields"])
    for field in FORBIDDEN_CONTENT_FIELDS:
        assert field in forbidden

    conf = verdict["confirmation_rules"]
    for key in (
        "retrieval_alone_never_executes",
        "read_requires_confirmation",
        "write_requires_confirmation_and_auth",
        "deny_without_confirm",
        "safety_auto_path_documented",
    ):
        assert conf[key] is True

    handoff = verdict["handoff_truthfulness"]
    for key in (
        "never_claim_unverified_transfer_success",
        "metadata_only_is_not_success",
        "request_distinct_from_completed_transfer",
        "outcome_speech_requires_receipt",
    ):
        assert handoff[key] is True

    inv_ids = {row["id"] for row in verdict["invariants"]}
    for inv_id in REQUIRED_INVARIANT_IDS:
        assert inv_id in inv_ids

    assert verdict["verdict"] in {"pass", "fail", "unknown"}
    assert verdict.get("verdict_grants_execute", False) is False
    assert verdict.get("fail_closed", True) is True
    assert isinstance(verdict["evidence"], list) and len(verdict["evidence"]) >= 1
