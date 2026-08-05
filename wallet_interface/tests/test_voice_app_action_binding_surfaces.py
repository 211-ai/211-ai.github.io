"""Surface exposure coverage tests (VAS-010)."""

from __future__ import annotations

import json
from pathlib import Path

from ipfs_accelerate_py.action_runtime.contracts import ActionStatus

from wallet_interface.helpers._voice_app_action_binding import (
    OPEN_APP_SURFACE_LOGICAL,
    SURFACE_EXPOSURE_CLASS,
    WalletAppSession,
    get_surface_exposure_class,
    surface_exposure_error,
)
from wallet_interface.tests.test_voice_app_action_binding import (
    _binding,
    build_app_proposal,
    build_permit_decision,
)


def _session(
    *,
    tenant_id: str = "tenant-a",
    confirmed: bool = True,
    authenticated: bool = True,
    channel: str = "voice",
) -> WalletAppSession:
    return WalletAppSession(
        tenant_id=tenant_id,
        authenticated=authenticated,
        confirmed=confirmed,
        client_id="client-abby",
        session_id="sess-surface-test-1",
        channel=channel,
    )

REPO_ROOT = Path(__file__).resolve().parents[2]
EXPOSURE = (
    REPO_ROOT
    / "data"
    / "voice_app_surface_coverage"
    / "baseline"
    / "voice-exposure-matrix.json"
)


def test_exposure_map_covers_matrix_p0_and_never_voice() -> None:
    matrix = json.loads(EXPOSURE.read_text(encoding="utf-8"))
    for row in matrix["surfaces"]:
        sid = row["surface_id"]
        assert sid in SURFACE_EXPOSURE_CLASS, sid
        assert SURFACE_EXPOSURE_CLASS[sid] == row["exposure_class"], sid


def test_never_voice_surfaces_deny_on_client_voice() -> None:
    binding = _binding()
    session = _session(channel="voice")
    for surface_id, klass in SURFACE_EXPOSURE_CLASS.items():
        if klass != "never_voice":
            continue
        proposal = build_app_proposal(
            logical_action=OPEN_APP_SURFACE_LOGICAL,
            arguments={"surface_id": surface_id},
            tenant_id=session.tenant_id,
            proposal_id=f"prop-never-{surface_id}",
        )
        receipt = binding.invoke(
            proposal=proposal,
            decision=build_permit_decision(proposal),
            session=session,
        )
        assert receipt.status is ActionStatus.DENIED, surface_id
        assert receipt.error == "surface_never_voice", surface_id
    assert binding.list_opened(tenant_id=session.tenant_id) == ()


def test_staff_only_surfaces_deny_on_client_voice() -> None:
    binding = _binding()
    session = _session(channel="voice")
    for surface_id, klass in SURFACE_EXPOSURE_CLASS.items():
        if klass != "staff_only":
            continue
        proposal = build_app_proposal(
            logical_action=OPEN_APP_SURFACE_LOGICAL,
            arguments={"surface_id": surface_id},
            tenant_id=session.tenant_id,
            proposal_id=f"prop-staff-{surface_id}",
        )
        receipt = binding.invoke(
            proposal=proposal,
            decision=build_permit_decision(proposal),
            session=session,
        )
        assert receipt.status is ActionStatus.DENIED, surface_id
        assert receipt.error == "surface_staff_only", surface_id


def test_p0_navigable_and_actionable_open_after_permit() -> None:
    binding = _binding()
    session = _session(channel="voice", confirmed=True)
    # Representative P0 set (not provider/never).
    for surface_id in ("home", "calendar", "messages", "uploads", "settings"):
        assert get_surface_exposure_class(surface_id) in {
            "voice_navigable",
            "voice_actionable",
        }
        assert surface_exposure_error(surface_id, channel="voice") is None
        proposal = build_app_proposal(
            logical_action=OPEN_APP_SURFACE_LOGICAL,
            arguments={"surface_id": surface_id},
            tenant_id=session.tenant_id,
            proposal_id=f"prop-p0-{surface_id}",
        )
        receipt = binding.invoke(
            proposal=proposal,
            decision=build_permit_decision(proposal),
            session=session,
        )
        assert receipt.status is ActionStatus.SUCCEEDED, (
            surface_id,
            receipt.error,
            receipt.status,
        )
        assert receipt.public_result["surface_id"] == surface_id


def test_alias_calendar_appointments_resolves_under_exposure() -> None:
    binding = _binding()
    session = _session(channel="voice", confirmed=True)
    proposal = build_app_proposal(
        logical_action=OPEN_APP_SURFACE_LOGICAL,
        arguments={"surface_id": "appointments"},
        tenant_id=session.tenant_id,
        proposal_id="prop-alias-cal",
    )
    receipt = binding.invoke(
        proposal=proposal,
        decision=build_permit_decision(proposal),
        session=session,
    )
    assert receipt.status is ActionStatus.SUCCEEDED
    assert receipt.public_result["surface_id"] == "calendar"
