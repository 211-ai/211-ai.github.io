"""Acceptance tests for wallet messaging action binding (VOICE-ACTION-018).

Criteria:

* Fake inbox/outbox works under permit
* Cross-tenant read denies
* Provider id must be grounded
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LOCAL_IPFS_ACCELERATE = REPO_ROOT / "ipfs_accelerate_py"
for path in (str(REPO_ROOT), str(LOCAL_IPFS_ACCELERATE)):
    if path not in sys.path:
        sys.path.insert(0, path)

from ipfs_accelerate_py.action_runtime.adapters.messaging import (  # noqa: E402
    InMemoryProviderMessageStore,
    ProviderMessageRecord,
)
from ipfs_accelerate_py.action_runtime.contracts import (  # noqa: E402
    ActionDecision,
    ActionDecisionKind,
    ActionStatus,
    RiskClass,
)
from wallet_interface.helpers._voice_messaging_action_binding import (  # noqa: E402
    LEAVE_LOGICAL_ACTION,
    LEAVE_PROVIDER_MESSAGE_DESCRIPTOR_ID,
    READ_LOGICAL_ACTION,
    READ_PROVIDER_MESSAGES_DESCRIPTOR_ID,
    WALLET_PROVIDER_MESSAGES_SURFACE,
    WalletMessagingSession,
    build_messaging_proposal,
    build_permit_decision,
    build_wallet_messaging_binding,
    extract_grounded_provider_ids,
    is_provider_id_grounded,
    provider_grounding_error,
    seed_demo_inbox,
)


GROUNDED_PROVIDER = "provider-rose"
UNGROUNDED_PROVIDER = "provider-free-text-guess"


def _auth_session(
    *,
    tenant_id: str = "tenant-a",
    confirmed: bool = True,
    authenticated: bool = True,
    client_id: str = "client-abby",
) -> WalletMessagingSession:
    return WalletMessagingSession(
        tenant_id=tenant_id,
        authenticated=authenticated,
        confirmed=confirmed,
        client_id=client_id,
        session_id="sess-test-1",
        channel="voice",
    )


def _binding(*, grounded: tuple[str, ...] = (GROUNDED_PROVIDER,), seed: bool = True):
    store = InMemoryProviderMessageStore()
    if seed:
        seed_demo_inbox(store, provider_id=GROUNDED_PROVIDER)
    return build_wallet_messaging_binding(
        grounded_provider_ids=grounded,
        store=store,
    )


# ── grounding helpers ────────────────────────────────────────────────────────


def test_provider_id_grounding_helpers() -> None:
    assert is_provider_id_grounded(
        GROUNDED_PROVIDER,
        grounded_provider_ids={GROUNDED_PROVIDER},
    )
    assert not is_provider_id_grounded(
        UNGROUNDED_PROVIDER,
        grounded_provider_ids={GROUNDED_PROVIDER},
    )
    assert provider_grounding_error(None) == "provider_id_required"
    assert (
        provider_grounding_error(
            UNGROUNDED_PROVIDER,
            grounded_provider_ids={GROUNDED_PROVIDER},
        )
        == "provider_id_not_grounded"
    )

    from_evidence = extract_grounded_provider_ids(
        (),
        evidence=(f"provider:{GROUNDED_PROVIDER}", "unrelated-token"),
    )
    assert GROUNDED_PROVIDER in from_evidence
    assert is_provider_id_grounded(
        GROUNDED_PROVIDER,
        grounded_provider_ids=(),
        evidence=(f"provider_id:{GROUNDED_PROVIDER}",),
    )


def test_descriptor_ids_match_pilot_catalog() -> None:
    assert READ_PROVIDER_MESSAGES_DESCRIPTOR_ID == "voice.python.read_provider_messages.v1"
    assert LEAVE_PROVIDER_MESSAGE_DESCRIPTOR_ID == "voice.python.leave_provider_message.v1"
    proposal = build_messaging_proposal(
        logical_action=READ_LOGICAL_ACTION,
        tenant_id="tenant-a",
    )
    assert proposal.descriptor_id == READ_PROVIDER_MESSAGES_DESCRIPTOR_ID
    assert proposal.route == "provider_contact_support"
    leave = build_messaging_proposal(
        logical_action=LEAVE_LOGICAL_ACTION,
        arguments={"provider_id": GROUNDED_PROVIDER, "body": "hi"},
        tenant_id="tenant-a",
    )
    assert leave.descriptor_id == LEAVE_PROVIDER_MESSAGE_DESCRIPTOR_ID


# ── fake inbox / outbox under permit ─────────────────────────────────────────


def test_fake_inbox_read_works_under_permit() -> None:
    binding = _binding()
    session = _auth_session()
    proposal = build_messaging_proposal(
        logical_action=READ_LOGICAL_ACTION,
        arguments={"provider_id": GROUNDED_PROVIDER},
        tenant_id=session.tenant_id,
        evidence=(f"provider:{GROUNDED_PROVIDER}",),
    )
    decision = build_permit_decision(proposal)
    assert decision.kind is ActionDecisionKind.PERMIT_READ
    assert decision.permits_execution

    receipt = binding.invoke(proposal=proposal, decision=decision, session=session)
    assert receipt.status is ActionStatus.SUCCEEDED, receipt.to_dict()
    assert receipt.public_result["ok"] == "true"
    assert receipt.public_result["message_count"] == "1"
    assert "msg-inbox-a-1" in receipt.public_result["message_ids"]
    assert receipt.public_result["bodies_redacted"] == "true"
    assert "LEAK-ME" not in str(receipt.to_dict())
    assert receipt.metadata.get("surface_id") == WALLET_PROVIDER_MESSAGES_SURFACE


def test_fake_outbox_leave_works_under_permit() -> None:
    binding = _binding(seed=True)
    session = _auth_session()
    body = "Please leave a note that I need a transportation voucher."
    proposal = build_messaging_proposal(
        logical_action=LEAVE_LOGICAL_ACTION,
        arguments={
            "provider_id": GROUNDED_PROVIDER,
            "client_id": session.client_id or "client-abby",
            "channel": "in_app",
            "subject": "Voucher follow-up",
            "body": body,
        },
        tenant_id=session.tenant_id,
        evidence=(GROUNDED_PROVIDER,),
    )
    decision = build_permit_decision(proposal)
    assert decision.kind is ActionDecisionKind.PERMIT_EXECUTE

    receipt = binding.invoke(proposal=proposal, decision=decision, session=session)
    assert receipt.status is ActionStatus.SUCCEEDED, receipt.to_dict()
    assert receipt.public_result["ok"] == "true"
    assert receipt.public_result["provider_id"] == GROUNDED_PROVIDER
    assert receipt.public_result["tenant_id"] == "tenant-a"
    assert receipt.public_result["bodies_redacted"] == "true"
    assert "body" not in receipt.public_result
    assert body not in str(receipt.to_dict())

    outbox = binding.list_outbox(tenant_id="tenant-a", provider_id=GROUNDED_PROVIDER)
    assert len(outbox) == 1
    assert outbox[0].body == body
    assert outbox[0].direction == "outbound"
    assert outbox[0].tenant_id == "tenant-a"


def test_convenience_read_and_leave_under_permit() -> None:
    binding = _binding()
    session = _auth_session()

    read_proposal = build_messaging_proposal(
        logical_action=READ_LOGICAL_ACTION,
        arguments={"provider_id": GROUNDED_PROVIDER},
        tenant_id=session.tenant_id,
    )
    read_receipt = binding.read_provider_messages(
        session=session,
        decision=build_permit_decision(read_proposal),
        proposal=read_proposal,
    )
    assert read_receipt.status is ActionStatus.SUCCEEDED

    leave_proposal = build_messaging_proposal(
        logical_action=LEAVE_LOGICAL_ACTION,
        arguments={
            "provider_id": GROUNDED_PROVIDER,
            "body": "Callback request from wallet surface.",
            "channel": "in_app",
        },
        tenant_id=session.tenant_id,
    )
    leave_receipt = binding.leave_provider_message(
        session=session,
        decision=build_permit_decision(leave_proposal),
        provider_id=GROUNDED_PROVIDER,
        body="Callback request from wallet surface.",
        proposal=leave_proposal,
    )
    assert leave_receipt.status is ActionStatus.SUCCEEDED
    assert len(binding.list_outbox(tenant_id="tenant-a")) == 1


def test_unpermitted_decision_does_not_mutate_outbox() -> None:
    binding = _binding(seed=False)
    session = _auth_session()
    proposal = build_messaging_proposal(
        logical_action=LEAVE_LOGICAL_ACTION,
        arguments={"provider_id": GROUNDED_PROVIDER, "body": "should not store"},
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
    assert binding.list_outbox(tenant_id="tenant-a") == ()
    assert binding.list_inbox(tenant_id="tenant-a") == ()


# ── cross-tenant isolation ───────────────────────────────────────────────────


def test_cross_tenant_read_denies_on_session_mismatch() -> None:
    binding = _binding()
    # Proposal claims tenant-a; session is tenant-b.
    proposal = build_messaging_proposal(
        logical_action=READ_LOGICAL_ACTION,
        arguments={"provider_id": GROUNDED_PROVIDER},
        tenant_id="tenant-a",
    )
    decision = build_permit_decision(proposal)
    session = _auth_session(tenant_id="tenant-b")

    receipt = binding.invoke(proposal=proposal, decision=decision, session=session)
    assert receipt.status is ActionStatus.DENIED
    assert receipt.error == "cross_tenant_denied"
    # No leakage of either tenant's bodies in the denial receipt.
    assert "LEAK-ME" not in str(receipt.to_dict())
    assert "intake appointment" not in str(receipt.to_dict()).lower()


def test_cross_tenant_read_does_not_return_other_tenant_rows() -> None:
    binding = _binding()
    session = _auth_session(tenant_id="tenant-a")
    proposal = build_messaging_proposal(
        logical_action=READ_LOGICAL_ACTION,
        arguments={"provider_id": GROUNDED_PROVIDER},
        tenant_id="tenant-a",
    )
    receipt = binding.invoke(
        proposal=proposal,
        decision=build_permit_decision(proposal),
        session=session,
    )
    assert receipt.status is ActionStatus.SUCCEEDED
    assert "msg-inbox-a-1" in receipt.public_result["message_ids"]
    assert "msg-inbox-b-1" not in receipt.public_result["message_ids"]
    assert "LEAK-ME" not in str(receipt.to_dict())

    # tenant-b may only see its own seeded row.
    session_b = _auth_session(tenant_id="tenant-b", client_id="client-casey")
    proposal_b = build_messaging_proposal(
        logical_action=READ_LOGICAL_ACTION,
        arguments={"provider_id": GROUNDED_PROVIDER},
        tenant_id="tenant-b",
        proposal_id="prop-read-b",
    )
    receipt_b = binding.invoke(
        proposal=proposal_b,
        decision=build_permit_decision(proposal_b),
        session=session_b,
    )
    assert receipt_b.status is ActionStatus.SUCCEEDED
    assert receipt_b.public_result["message_ids"] == "msg-inbox-b-1"
    assert "msg-inbox-a-1" not in receipt_b.public_result["message_ids"]


def test_leave_cannot_write_into_other_tenant_via_session_mismatch() -> None:
    binding = _binding(seed=False)
    proposal = build_messaging_proposal(
        logical_action=LEAVE_LOGICAL_ACTION,
        arguments={"provider_id": GROUNDED_PROVIDER, "body": "cross-tenant write"},
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
    assert binding.list_outbox(tenant_id="tenant-a") == ()
    assert binding.list_outbox(tenant_id="tenant-b") == ()


# ── provider id must be grounded ─────────────────────────────────────────────


def test_leave_rejects_ungrounded_provider_id() -> None:
    binding = _binding(grounded=(GROUNDED_PROVIDER,), seed=False)
    session = _auth_session()
    proposal = build_messaging_proposal(
        logical_action=LEAVE_LOGICAL_ACTION,
        arguments={
            "provider_id": UNGROUNDED_PROVIDER,
            "body": "Please call the free-text provider I invented.",
        },
        tenant_id=session.tenant_id,
        # Evidence does not ground the free-text provider.
        evidence=(f"provider:{GROUNDED_PROVIDER}",),
    )
    receipt = binding.invoke(
        proposal=proposal,
        decision=build_permit_decision(proposal),
        session=session,
    )
    assert receipt.status is ActionStatus.FAILED
    assert receipt.error == "provider_id_not_grounded"
    assert binding.list_outbox(tenant_id="tenant-a") == ()


def test_leave_rejects_missing_provider_id_at_binding() -> None:
    binding = _binding(seed=False)
    session = _auth_session()
    # Build a leave proposal without provider_id (adapter would also reject).
    proposal = build_messaging_proposal(
        logical_action=LEAVE_LOGICAL_ACTION,
        arguments={"body": "no provider target"},
        tenant_id=session.tenant_id,
    )
    receipt = binding.invoke(
        proposal=proposal,
        decision=build_permit_decision(proposal),
        session=session,
    )
    assert receipt.status is ActionStatus.FAILED
    assert receipt.error == "provider_id_required"
    assert binding.list_outbox(tenant_id="tenant-a") == ()


def test_read_rejects_ungrounded_provider_filter() -> None:
    binding = _binding(grounded=(GROUNDED_PROVIDER,))
    session = _auth_session()
    proposal = build_messaging_proposal(
        logical_action=READ_LOGICAL_ACTION,
        arguments={"provider_id": UNGROUNDED_PROVIDER},
        tenant_id=session.tenant_id,
    )
    receipt = binding.invoke(
        proposal=proposal,
        decision=build_permit_decision(proposal),
        session=session,
    )
    assert receipt.status is ActionStatus.FAILED
    assert receipt.error == "provider_id_not_grounded"


def test_leave_accepts_provider_grounded_via_proposal_evidence_only() -> None:
    # Registry empty; evidence alone grounds the provider.
    binding = build_wallet_messaging_binding(grounded_provider_ids=())
    session = _auth_session()
    proposal = build_messaging_proposal(
        logical_action=LEAVE_LOGICAL_ACTION,
        arguments={
            "provider_id": GROUNDED_PROVIDER,
            "body": "Evidence-grounded leave.",
            "channel": "in_app",
        },
        tenant_id=session.tenant_id,
        evidence=(f"grounded_provider:{GROUNDED_PROVIDER}",),
    )
    receipt = binding.invoke(
        proposal=proposal,
        decision=build_permit_decision(proposal),
        session=session,
    )
    assert receipt.status is ActionStatus.SUCCEEDED, receipt.to_dict()
    assert receipt.public_result["provider_id"] == GROUNDED_PROVIDER


def test_read_without_provider_filter_still_tenant_scoped() -> None:
    """Whole-tenant inbox read is allowed without provider_id (no free-text target)."""

    binding = _binding()
    session = _auth_session(tenant_id="tenant-a")
    proposal = build_messaging_proposal(
        logical_action=READ_LOGICAL_ACTION,
        arguments={},
        tenant_id=session.tenant_id,
    )
    receipt = binding.invoke(
        proposal=proposal,
        decision=build_permit_decision(proposal),
        session=session,
    )
    assert receipt.status is ActionStatus.SUCCEEDED
    assert receipt.public_result["message_count"] == "1"
    assert "msg-inbox-b-1" not in receipt.public_result["message_ids"]


def test_read_and_leave_require_confirm_and_auth_at_adapter() -> None:
    binding = _binding()
    proposal = build_messaging_proposal(
        logical_action=LEAVE_LOGICAL_ACTION,
        arguments={"provider_id": GROUNDED_PROVIDER, "body": "needs auth"},
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

    unauth = binding.invoke(
        proposal=proposal,
        decision=decision,
        session=_auth_session(confirmed=True, authenticated=False),
    )
    assert unauth.status is ActionStatus.FAILED
    assert "auth_required" in (unauth.error or "")


def test_with_grounded_providers_extends_registry() -> None:
    binding = _binding(grounded=(GROUNDED_PROVIDER,), seed=False)
    extended = binding.with_grounded_providers("provider-other")
    assert GROUNDED_PROVIDER in extended.grounded_provider_ids
    assert "provider-other" in extended.grounded_provider_ids

    session = _auth_session()
    proposal = build_messaging_proposal(
        logical_action=LEAVE_LOGICAL_ACTION,
        arguments={"provider_id": "provider-other", "body": "to other provider"},
        tenant_id=session.tenant_id,
    )
    receipt = extended.invoke(
        proposal=proposal,
        decision=build_permit_decision(proposal),
        session=session,
    )
    assert receipt.status is ActionStatus.SUCCEEDED


def test_default_registrations_surface_constant() -> None:
    binding = build_wallet_messaging_binding()
    assert binding.surface_id == WALLET_PROVIDER_MESSAGES_SURFACE
    assert binding.adapter.get_registration(READ_PROVIDER_MESSAGES_DESCRIPTOR_ID) is not None
    assert binding.adapter.get_registration(LEAVE_PROVIDER_MESSAGE_DESCRIPTOR_ID) is not None


def test_seed_record_shapes_match_wallet_demo_providers() -> None:
    """Demo seed uses wallet-adjacent provider ids used by provider-message UI."""

    store = InMemoryProviderMessageStore()
    seed_demo_inbox(store)
    rows = store.list_messages(tenant_id="tenant-a")
    assert len(rows) == 1
    assert isinstance(rows[0], ProviderMessageRecord)
    assert rows[0].provider_id == GROUNDED_PROVIDER
    assert rows[0].channel in {"in_app", "sms", "email"}
