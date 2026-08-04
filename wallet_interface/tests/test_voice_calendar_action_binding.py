"""Acceptance tests for wallet calendar action binding (VOICE-ACTION-016).

Criteria:

* Offline fake calendar store supports read/create under permit
* Unauthenticated write denies
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LOCAL_IPFS_ACCELERATE = REPO_ROOT / "ipfs_accelerate_py"
for path in (str(REPO_ROOT), str(LOCAL_IPFS_ACCELERATE)):
    if path not in sys.path:
        sys.path.insert(0, path)

from ipfs_accelerate_py.action_runtime.adapters.calendar import (  # noqa: E402
    CalendarEventRecord,
    InMemoryCalendarEventStore,
)
from ipfs_accelerate_py.action_runtime.contracts import (  # noqa: E402
    ActionDecision,
    ActionDecisionKind,
    ActionStatus,
    RiskClass,
)
from wallet_interface.helpers._voice_calendar_action_binding import (  # noqa: E402
    CREATE_CALENDAR_REMINDER_DESCRIPTOR_ID,
    CREATE_LOGICAL_ACTION,
    READ_CALENDAR_DESCRIPTOR_ID,
    READ_LOGICAL_ACTION,
    WALLET_CALENDAR_SUPPORT_ROUTE,
    WALLET_CALENDAR_SURFACE,
    WalletCalendarSession,
    build_calendar_proposal,
    build_permit_decision,
    build_wallet_calendar_binding,
    seed_demo_calendar,
)


def _auth_session(
    *,
    tenant_id: str = "tenant-a",
    confirmed: bool = True,
    authenticated: bool = True,
    client_id: str = "client-abby",
) -> WalletCalendarSession:
    return WalletCalendarSession(
        tenant_id=tenant_id,
        authenticated=authenticated,
        confirmed=confirmed,
        client_id=client_id,
        session_id="sess-cal-test-1",
        channel="voice",
    )


def _binding(*, seed: bool = True):
    store = InMemoryCalendarEventStore()
    if seed:
        seed_demo_calendar(store)
    return build_wallet_calendar_binding(store=store)


# ── descriptor / proposal helpers ────────────────────────────────────────────


def test_descriptor_ids_match_pilot_catalog() -> None:
    assert READ_CALENDAR_DESCRIPTOR_ID == "voice.python.read_calendar.v1"
    assert (
        CREATE_CALENDAR_REMINDER_DESCRIPTOR_ID
        == "voice.python.create_calendar_reminder.v1"
    )
    proposal = build_calendar_proposal(
        logical_action=READ_LOGICAL_ACTION,
        tenant_id="tenant-a",
    )
    assert proposal.descriptor_id == READ_CALENDAR_DESCRIPTOR_ID
    assert proposal.route == WALLET_CALENDAR_SUPPORT_ROUTE
    create = build_calendar_proposal(
        logical_action=CREATE_LOGICAL_ACTION,
        arguments={
            "title": "Follow-up",
            "starts_at": "2026-08-10T14:00:00Z",
        },
        tenant_id="tenant-a",
    )
    assert create.descriptor_id == CREATE_CALENDAR_REMINDER_DESCRIPTOR_ID


# ── offline fake store: read/create under permit ─────────────────────────────


def test_fake_calendar_read_works_under_permit() -> None:
    binding = _binding()
    session = _auth_session()
    proposal = build_calendar_proposal(
        logical_action=READ_LOGICAL_ACTION,
        arguments={},
        tenant_id=session.tenant_id,
    )
    decision = build_permit_decision(proposal)
    assert decision.kind is ActionDecisionKind.PERMIT_READ
    assert decision.permits_execution

    receipt = binding.invoke(proposal=proposal, decision=decision, session=session)
    assert receipt.status is ActionStatus.SUCCEEDED, receipt.to_dict()
    assert receipt.public_result["ok"] == "true"
    assert receipt.public_result["event_count"] == "1"
    assert "evt-a-1" in receipt.public_result["event_ids"]
    assert receipt.public_result["summaries_redacted"] == "true"
    assert receipt.public_result["notes_redacted"] == "true"
    assert "SECRET-TENANT-A" not in str(receipt.to_dict())
    assert "LEAK-ME" not in str(receipt.to_dict())
    assert receipt.metadata.get("surface_id") == WALLET_CALENDAR_SURFACE


def test_fake_calendar_create_works_under_permit() -> None:
    binding = _binding(seed=True)
    session = _auth_session(authenticated=True, confirmed=True)
    notes = "Private reminder notes for voucher pickup — do not leak."
    proposal = build_calendar_proposal(
        logical_action=CREATE_LOGICAL_ACTION,
        arguments={
            "title": "Voucher pickup reminder",
            "starts_at": "2026-08-12T15:00:00Z",
            "duration_minutes": "30",
            "notes": notes,
            "location": "Front desk",
            "reminder_minutes_before": "60",
        },
        tenant_id=session.tenant_id,
    )
    decision = build_permit_decision(proposal)
    assert decision.kind is ActionDecisionKind.PERMIT_EXECUTE

    receipt = binding.invoke(proposal=proposal, decision=decision, session=session)
    assert receipt.status is ActionStatus.SUCCEEDED, receipt.to_dict()
    assert receipt.public_result["ok"] == "true"
    assert receipt.public_result["tenant_id"] == "tenant-a"
    assert receipt.public_result["title"] == "Voucher pickup reminder"
    assert receipt.public_result["starts_at"] == "2026-08-12T15:00:00Z"
    assert receipt.public_result["notes_redacted"] == "true"
    assert "notes" not in receipt.public_result
    assert notes not in str(receipt.to_dict())
    assert "do not leak" not in str(receipt.to_dict())

    created_id = receipt.public_result["event_id"]
    rows = binding.list_events(tenant_id="tenant-a")
    assert any(r.event_id == created_id for r in rows)
    created = next(r for r in rows if r.event_id == created_id)
    assert created.notes == notes
    assert created.tenant_id == "tenant-a"
    assert created.title == "Voucher pickup reminder"


def test_convenience_read_and_create_under_permit() -> None:
    binding = _binding()
    session = _auth_session()

    read_proposal = build_calendar_proposal(
        logical_action=READ_LOGICAL_ACTION,
        arguments={},
        tenant_id=session.tenant_id,
    )
    read_receipt = binding.read_calendar(
        session=session,
        decision=build_permit_decision(read_proposal),
        proposal=read_proposal,
    )
    assert read_receipt.status is ActionStatus.SUCCEEDED
    assert read_receipt.public_result["event_count"] == "1"

    create_proposal = build_calendar_proposal(
        logical_action=CREATE_LOGICAL_ACTION,
        arguments={
            "title": "Callback reminder",
            "starts_at": "2026-08-15T11:00:00Z",
            "notes": "Call provider about housing waitlist.",
        },
        tenant_id=session.tenant_id,
    )
    create_receipt = binding.create_calendar_reminder(
        session=session,
        decision=build_permit_decision(create_proposal),
        title="Callback reminder",
        starts_at="2026-08-15T11:00:00Z",
        notes="Call provider about housing waitlist.",
        proposal=create_proposal,
    )
    assert create_receipt.status is ActionStatus.SUCCEEDED
    # Seeded + newly created
    assert len(binding.list_events(tenant_id="tenant-a")) == 2


def test_unpermitted_decision_does_not_mutate_store() -> None:
    binding = _binding(seed=False)
    session = _auth_session()
    proposal = build_calendar_proposal(
        logical_action=CREATE_LOGICAL_ACTION,
        arguments={
            "title": "should not store",
            "starts_at": "2026-08-20T09:00:00Z",
        },
        tenant_id=session.tenant_id,
    )
    decision = ActionDecision(
        decision_id="dec-confirm-only",
        kind=ActionDecisionKind.CONFIRM,
        proposal_id=proposal.proposal_id,
        descriptor_id=proposal.descriptor_id,
        descriptor_digest="d",
        arguments_digest=proposal.arguments_digest,
        reason="confirmation_required",
        risk_class=RiskClass.WRITE,
    )
    receipt = binding.invoke(proposal=proposal, decision=decision, session=session)
    assert receipt.status is ActionStatus.DENIED
    assert "does_not_permit" in (receipt.error or "")
    assert binding.list_events(tenant_id="tenant-a") == ()


# ── unauthenticated write denies ─────────────────────────────────────────────


def test_unauthenticated_write_denies_at_binding() -> None:
    binding = _binding(seed=False)
    session = _auth_session(authenticated=False, confirmed=True)
    proposal = build_calendar_proposal(
        logical_action=CREATE_LOGICAL_ACTION,
        arguments={
            "title": "Unauth create attempt",
            "starts_at": "2026-08-18T10:00:00Z",
            "notes": "should never persist",
        },
        tenant_id=session.tenant_id,
    )
    decision = build_permit_decision(proposal)
    assert decision.permits_execution

    receipt = binding.invoke(proposal=proposal, decision=decision, session=session)
    assert receipt.status is ActionStatus.FAILED
    assert receipt.error == "auth_required"
    assert binding.list_events(tenant_id="tenant-a") == ()


def test_unauthenticated_write_denies_via_convenience_api() -> None:
    binding = _binding(seed=False)
    session = _auth_session(authenticated=False, confirmed=True)
    proposal = build_calendar_proposal(
        logical_action=CREATE_LOGICAL_ACTION,
        arguments={
            "title": "Convenience unauth",
            "starts_at": "2026-08-19T12:00:00Z",
        },
        tenant_id=session.tenant_id,
    )
    receipt = binding.create_calendar_reminder(
        session=session,
        decision=build_permit_decision(proposal),
        title="Convenience unauth",
        starts_at="2026-08-19T12:00:00Z",
        proposal=proposal,
    )
    assert receipt.status is ActionStatus.FAILED
    assert receipt.error == "auth_required"
    assert binding.list_events(tenant_id="tenant-a") == ()


def test_authenticated_create_still_requires_confirm_at_adapter() -> None:
    binding = _binding(seed=False)
    # Auth present at wallet boundary, but adapter still requires confirm.
    session = _auth_session(authenticated=True, confirmed=False)
    proposal = build_calendar_proposal(
        logical_action=CREATE_LOGICAL_ACTION,
        arguments={
            "title": "Needs confirm",
            "starts_at": "2026-08-21T08:00:00Z",
        },
        tenant_id=session.tenant_id,
    )
    receipt = binding.invoke(
        proposal=proposal,
        decision=build_permit_decision(proposal),
        session=session,
    )
    assert receipt.status is ActionStatus.FAILED
    assert "confirmation_required" in (receipt.error or "")
    assert binding.list_events(tenant_id="tenant-a") == ()


# ── cross-tenant isolation ───────────────────────────────────────────────────


def test_cross_tenant_read_denies_on_session_mismatch() -> None:
    binding = _binding()
    proposal = build_calendar_proposal(
        logical_action=READ_LOGICAL_ACTION,
        arguments={},
        tenant_id="tenant-a",
    )
    decision = build_permit_decision(proposal)
    session = _auth_session(tenant_id="tenant-b")

    receipt = binding.invoke(proposal=proposal, decision=decision, session=session)
    assert receipt.status is ActionStatus.DENIED
    assert receipt.error == "cross_tenant_denied"
    assert "LEAK-ME" not in str(receipt.to_dict())
    assert "SECRET-TENANT-A" not in str(receipt.to_dict())


def test_cross_tenant_read_does_not_return_other_tenant_rows() -> None:
    binding = _binding()
    session = _auth_session(tenant_id="tenant-a")
    proposal = build_calendar_proposal(
        logical_action=READ_LOGICAL_ACTION,
        arguments={},
        tenant_id="tenant-a",
    )
    receipt = binding.invoke(
        proposal=proposal,
        decision=build_permit_decision(proposal),
        session=session,
    )
    assert receipt.status is ActionStatus.SUCCEEDED
    assert "evt-a-1" in receipt.public_result["event_ids"]
    assert "evt-b-1" not in receipt.public_result["event_ids"]
    assert "LEAK-ME" not in str(receipt.to_dict())

    session_b = _auth_session(tenant_id="tenant-b", client_id="client-casey")
    proposal_b = build_calendar_proposal(
        logical_action=READ_LOGICAL_ACTION,
        arguments={},
        tenant_id="tenant-b",
        proposal_id="prop-read-b",
    )
    receipt_b = binding.invoke(
        proposal=proposal_b,
        decision=build_permit_decision(proposal_b),
        session=session_b,
    )
    assert receipt_b.status is ActionStatus.SUCCEEDED
    assert receipt_b.public_result["event_ids"] == "evt-b-1"
    assert "evt-a-1" not in receipt_b.public_result["event_ids"]


def test_create_cannot_write_into_other_tenant_via_session_mismatch() -> None:
    binding = _binding(seed=False)
    proposal = build_calendar_proposal(
        logical_action=CREATE_LOGICAL_ACTION,
        arguments={
            "title": "cross-tenant write",
            "starts_at": "2026-08-22T10:00:00Z",
        },
        tenant_id="tenant-a",
    )
    session = _auth_session(tenant_id="tenant-b")
    receipt = binding.invoke(
        proposal=proposal,
        decision=build_permit_decision(proposal),
        session=session,
    )
    assert receipt.status is ActionStatus.DENIED
    assert receipt.error == "cross_tenant_denied"
    assert binding.list_events(tenant_id="tenant-a") == ()
    assert binding.list_events(tenant_id="tenant-b") == ()


# ── registration / seed shape ────────────────────────────────────────────────


def test_default_registrations_surface_constant() -> None:
    binding = build_wallet_calendar_binding()
    assert binding.surface_id == WALLET_CALENDAR_SURFACE
    assert binding.adapter.get_registration(READ_CALENDAR_DESCRIPTOR_ID) is not None
    assert (
        binding.adapter.get_registration(CREATE_CALENDAR_REMINDER_DESCRIPTOR_ID)
        is not None
    )


def test_seed_record_shapes_match_wallet_calendar() -> None:
    """Demo seed uses wallet-adjacent event ids used by calendar UI tests."""

    store = InMemoryCalendarEventStore()
    seed_demo_calendar(store)
    rows = store.list_events(tenant_id="tenant-a")
    assert len(rows) == 1
    assert isinstance(rows[0], CalendarEventRecord)
    assert rows[0].event_id == "evt-a-1"
    assert rows[0].status == "scheduled"
    assert rows[0].starts_at.startswith("2026-")


def test_read_without_confirm_fails_at_adapter() -> None:
    binding = _binding()
    proposal = build_calendar_proposal(
        logical_action=READ_LOGICAL_ACTION,
        arguments={},
        tenant_id="tenant-a",
    )
    decision = build_permit_decision(proposal)
    unconfirmed = binding.invoke(
        proposal=proposal,
        decision=decision,
        session=_auth_session(confirmed=False, authenticated=True),
    )
    assert unconfirmed.status is ActionStatus.FAILED
    assert "confirmation_required" in (unconfirmed.error or "")


def test_permit_read_cannot_create() -> None:
    binding = _binding(seed=False)
    session = _auth_session()
    proposal = build_calendar_proposal(
        logical_action=CREATE_LOGICAL_ACTION,
        arguments={
            "title": "wrong decision kind",
            "starts_at": "2026-08-23T09:00:00Z",
        },
        tenant_id=session.tenant_id,
    )
    decision = build_permit_decision(
        proposal,
        kind=ActionDecisionKind.PERMIT_READ,
        risk_class=RiskClass.READ,
    )
    receipt = binding.invoke(proposal=proposal, decision=decision, session=session)
    assert receipt.status is ActionStatus.FAILED
    assert "create_requires_permit_execute" in (receipt.error or "")
    assert binding.list_events(tenant_id="tenant-a") == ()
