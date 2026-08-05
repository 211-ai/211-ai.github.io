"""Acceptance tests for wallet service action binding (VOICE-ACTION-020).

Criteria:

* Offline fake service interaction log records callbacks under permit only
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LOCAL_IPFS_ACCELERATE = REPO_ROOT / "ipfs_accelerate_py"
for path in (str(REPO_ROOT), str(LOCAL_IPFS_ACCELERATE)):
    if path not in sys.path:
        sys.path.insert(0, path)

from ipfs_accelerate_py.action_runtime.adapters.service_interaction import (  # noqa: E402
    InMemoryServiceInteractionStore,
    ServiceCallbackRecord,
    ServiceDetailRecord,
)
from ipfs_accelerate_py.action_runtime.contracts import (  # noqa: E402
    ActionDecision,
    ActionDecisionKind,
    ActionStatus,
    RiskClass,
)
from wallet_interface.helpers._voice_service_action_binding import (  # noqa: E402
    INTERACTION_TYPE_CALLBACK_REQUESTED,
    INTERACTION_TYPE_VIEWED_SERVICE,
    OPEN_LOGICAL_ACTION,
    OPEN_SERVICE_DETAIL_DESCRIPTOR_ID,
    SCHEDULE_LOGICAL_ACTION,
    SCHEDULE_SERVICE_CALLBACK_DESCRIPTOR_ID,
    WALLET_INTERACTIONS_SURFACE,
    WALLET_SERVICE_INTERACTION_SUPPORT_ROUTE,
    WALLET_SOCIAL_SERVICES_SURFACE,
    WalletServiceSession,
    build_permit_decision,
    build_service_proposal,
    build_wallet_service_binding,
    extract_grounded_service_ids,
    is_service_id_grounded,
    seed_demo_service_catalog,
    service_grounding_error,
)


GROUNDED_SERVICE = "svc-housing-211-demo"
UNGROUNDED_SERVICE = "svc-free-text-guess"
GROUNDED_EVIDENCE = (f"service_id:{GROUNDED_SERVICE}", "bafyEvidenceCidExample0001")


def _auth_session(
    *,
    tenant_id: str = "tenant-a",
    confirmed: bool = True,
    authenticated: bool = True,
    client_id: str = "client-abby",
) -> WalletServiceSession:
    return WalletServiceSession(
        tenant_id=tenant_id,
        authenticated=authenticated,
        confirmed=confirmed,
        client_id=client_id,
        session_id="sess-svc-test-1",
        channel="voice",
    )


def _binding(
    *,
    grounded: tuple[str, ...] = (GROUNDED_SERVICE,),
    seed: bool = True,
):
    store = InMemoryServiceInteractionStore()
    if seed:
        seed_demo_service_catalog(store, service_id=GROUNDED_SERVICE)
    return build_wallet_service_binding(
        grounded_service_ids=grounded,
        store=store,
    )


# ── grounding helpers ────────────────────────────────────────────────────────


def test_service_id_grounding_helpers() -> None:
    assert is_service_id_grounded(
        GROUNDED_SERVICE,
        grounded_service_ids={GROUNDED_SERVICE},
    )
    assert not is_service_id_grounded(
        UNGROUNDED_SERVICE,
        grounded_service_ids={GROUNDED_SERVICE},
    )
    assert service_grounding_error(None) == "service_id_required"
    assert (
        service_grounding_error(
            UNGROUNDED_SERVICE,
            grounded_service_ids={GROUNDED_SERVICE},
        )
        == "service_id_not_grounded"
    )

    from_evidence = extract_grounded_service_ids(
        (),
        evidence=(f"service:{GROUNDED_SERVICE}", "unrelated-token"),
    )
    assert GROUNDED_SERVICE in from_evidence
    assert is_service_id_grounded(
        GROUNDED_SERVICE,
        grounded_service_ids=(),
        evidence=(f"service_doc_id:{GROUNDED_SERVICE}",),
    )


def test_descriptor_ids_match_pilot_catalog() -> None:
    assert OPEN_SERVICE_DETAIL_DESCRIPTOR_ID == "voice.python.open_service_detail.v1"
    assert (
        SCHEDULE_SERVICE_CALLBACK_DESCRIPTOR_ID
        == "voice.workflow.schedule_service_callback.v1"
    )
    proposal = build_service_proposal(
        logical_action=OPEN_LOGICAL_ACTION,
        arguments={"service_id": GROUNDED_SERVICE},
        tenant_id="tenant-a",
        evidence=GROUNDED_EVIDENCE,
    )
    assert proposal.descriptor_id == OPEN_SERVICE_DETAIL_DESCRIPTOR_ID
    assert proposal.route == WALLET_SERVICE_INTERACTION_SUPPORT_ROUTE
    schedule = build_service_proposal(
        logical_action=SCHEDULE_LOGICAL_ACTION,
        arguments={"service_id": GROUNDED_SERVICE, "channel": "phone"},
        tenant_id="tenant-a",
        evidence=GROUNDED_EVIDENCE,
    )
    assert schedule.descriptor_id == SCHEDULE_SERVICE_CALLBACK_DESCRIPTOR_ID


# ── offline fake interaction log: callbacks under permit only ────────────────


def test_fake_interaction_log_records_callback_under_permit() -> None:
    """Acceptance: offline fake service interaction log records callbacks under permit only."""

    binding = _binding()
    session = _auth_session()
    notes = "Please call about emergency housing intake — PRIVATE."
    proposal = build_service_proposal(
        logical_action=SCHEDULE_LOGICAL_ACTION,
        arguments={
            "service_id": GROUNDED_SERVICE,
            "channel": "phone",
            "callback_at": "2026-08-12T15:00:00Z",
            "client_id": session.client_id or "client-abby",
            "notes": notes,
            "contact_preference": "afternoon",
        },
        tenant_id=session.tenant_id,
        evidence=GROUNDED_EVIDENCE,
    )
    decision = build_permit_decision(proposal)
    assert decision.kind is ActionDecisionKind.PERMIT_EXECUTE
    assert decision.permits_execution

    # Precondition: interaction log empty for this tenant.
    assert binding.list_callbacks(tenant_id="tenant-a") == ()
    assert binding.interaction_log(tenant_id="tenant-a") == ()

    receipt = binding.invoke(proposal=proposal, decision=decision, session=session)
    assert receipt.status is ActionStatus.SUCCEEDED, receipt.to_dict()
    assert receipt.public_result["ok"] == "true"
    assert receipt.public_result["service_id"] == GROUNDED_SERVICE
    assert receipt.public_result["tenant_id"] == "tenant-a"
    assert receipt.public_result["channel"] == "phone"
    assert receipt.public_result["idempotent_replay"] == "false"
    assert receipt.public_result["notes_redacted"] == "true"
    assert "notes" not in receipt.public_result
    assert notes not in str(receipt.to_dict())
    assert "PRIVATE" not in str(receipt.to_dict())
    assert receipt.public_result["interaction_type"] == INTERACTION_TYPE_CALLBACK_REQUESTED
    assert receipt.metadata.get("surface_id") == WALLET_SOCIAL_SERVICES_SURFACE
    assert receipt.metadata.get("interaction_surface_id") == WALLET_INTERACTIONS_SURFACE
    assert receipt.metadata.get("interaction_type") == INTERACTION_TYPE_CALLBACK_REQUESTED

    # Interaction log records the callback under permit.
    callbacks = binding.list_callbacks(tenant_id="tenant-a")
    assert len(callbacks) == 1
    assert callbacks[0].service_id == GROUNDED_SERVICE
    assert callbacks[0].tenant_id == "tenant-a"
    assert callbacks[0].channel == "phone"
    assert callbacks[0].notes == notes
    assert callbacks[0].interaction_type == INTERACTION_TYPE_CALLBACK_REQUESTED
    assert callbacks[0].callback_id == receipt.public_result["callback_id"]

    log = binding.interaction_log(tenant_id="tenant-a")
    assert len(log) == 1
    entry = log[0]
    assert entry["interaction_type"] == INTERACTION_TYPE_CALLBACK_REQUESTED
    assert entry["service_doc_id"] == GROUNDED_SERVICE
    assert entry["service_id"] == GROUNDED_SERVICE
    assert entry["tenant_id"] == "tenant-a"
    assert entry["channel"] == "phone"
    assert entry["callback_id"] == receipt.public_result["callback_id"]
    assert entry["notes_present"] is True
    assert entry["surface_id"] == WALLET_INTERACTIONS_SURFACE
    assert entry["privacy_level"] == "redacted"
    # Wallet-shaped log never embeds raw notes.
    assert "notes" not in entry or entry.get("notes") != notes
    assert notes not in str(entry)


def test_unpermitted_decision_does_not_record_callback() -> None:
    binding = _binding(seed=True)
    session = _auth_session()
    proposal = build_service_proposal(
        logical_action=SCHEDULE_LOGICAL_ACTION,
        arguments={
            "service_id": GROUNDED_SERVICE,
            "channel": "phone",
            "notes": "should not store",
        },
        tenant_id=session.tenant_id,
        evidence=GROUNDED_EVIDENCE,
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
    assert binding.list_callbacks(tenant_id="tenant-a") == ()
    assert binding.interaction_log(tenant_id="tenant-a") == ()


def test_deny_decision_does_not_record_callback() -> None:
    binding = _binding(seed=True)
    session = _auth_session()
    proposal = build_service_proposal(
        logical_action=SCHEDULE_LOGICAL_ACTION,
        arguments={"service_id": GROUNDED_SERVICE, "channel": "sms"},
        tenant_id=session.tenant_id,
        evidence=GROUNDED_EVIDENCE,
    )
    decision = ActionDecision(
        decision_id="dec-deny",
        kind=ActionDecisionKind.DENY,
        proposal_id=proposal.proposal_id,
        descriptor_id=proposal.descriptor_id,
        descriptor_digest="d",
        arguments_digest=proposal.arguments_digest,
        reason="policy_deny",
        risk_class=RiskClass.WRITE,
    )
    receipt = binding.invoke(proposal=proposal, decision=decision, session=session)
    assert receipt.status is ActionStatus.DENIED
    assert binding.list_callbacks(tenant_id="tenant-a") == ()
    assert binding.interaction_log(tenant_id="tenant-a") == ()


def test_open_service_detail_under_permit_does_not_write_callback_log() -> None:
    binding = _binding()
    session = _auth_session(authenticated=False)  # open path: auth optional
    proposal = build_service_proposal(
        logical_action=OPEN_LOGICAL_ACTION,
        arguments={"service_id": GROUNDED_SERVICE},
        tenant_id=session.tenant_id,
        evidence=GROUNDED_EVIDENCE,
    )
    decision = build_permit_decision(proposal)
    assert decision.kind is ActionDecisionKind.PERMIT_READ

    receipt = binding.invoke(proposal=proposal, decision=decision, session=session)
    assert receipt.status is ActionStatus.SUCCEEDED, receipt.to_dict()
    assert receipt.public_result["ok"] == "true"
    assert receipt.public_result["found"] == "true"
    assert receipt.public_result["service_id"] == GROUNDED_SERVICE
    assert receipt.public_result["summary_redacted"] == "true"
    assert "SECRET" not in str(receipt.to_dict())
    assert receipt.metadata.get("interaction_type") == INTERACTION_TYPE_VIEWED_SERVICE
    # Opening detail is a read; it must not append a callback to the log.
    assert binding.list_callbacks(tenant_id="tenant-a") == ()
    assert binding.interaction_log(tenant_id="tenant-a") == ()


def test_convenience_schedule_and_open_under_permit() -> None:
    binding = _binding()
    session = _auth_session()

    open_proposal = build_service_proposal(
        logical_action=OPEN_LOGICAL_ACTION,
        arguments={"service_id": GROUNDED_SERVICE},
        tenant_id=session.tenant_id,
        evidence=GROUNDED_EVIDENCE,
        proposal_id="prop-open-conv",
    )
    open_receipt = binding.open_service_detail(
        session=session,
        decision=build_permit_decision(open_proposal),
        service_id=GROUNDED_SERVICE,
        proposal=open_proposal,
    )
    assert open_receipt.status is ActionStatus.SUCCEEDED

    schedule_proposal = build_service_proposal(
        logical_action=SCHEDULE_LOGICAL_ACTION,
        arguments={
            "service_id": GROUNDED_SERVICE,
            "channel": "in_app",
            "notes": "Wallet surface callback request.",
        },
        tenant_id=session.tenant_id,
        evidence=GROUNDED_EVIDENCE,
        proposal_id="prop-sched-conv",
    )
    schedule_receipt = binding.schedule_service_callback(
        session=session,
        decision=build_permit_decision(schedule_proposal),
        service_id=GROUNDED_SERVICE,
        channel="in_app",
        notes="Wallet surface callback request.",
        proposal=schedule_proposal,
    )
    assert schedule_receipt.status is ActionStatus.SUCCEEDED
    assert len(binding.list_callbacks(tenant_id="tenant-a")) == 1
    assert len(binding.interaction_log(tenant_id="tenant-a")) == 1


def test_schedule_idempotent_replay_does_not_duplicate_log() -> None:
    binding = _binding()
    session = _auth_session()
    proposal = build_service_proposal(
        logical_action=SCHEDULE_LOGICAL_ACTION,
        arguments={
            "service_id": GROUNDED_SERVICE,
            "channel": "phone",
            "callback_at": "2026-08-15T10:00:00Z",
        },
        tenant_id=session.tenant_id,
        evidence=GROUNDED_EVIDENCE,
        proposal_id="prop-idem-1",
    )
    decision = build_permit_decision(proposal)

    first = binding.invoke(proposal=proposal, decision=decision, session=session)
    assert first.status is ActionStatus.SUCCEEDED
    assert first.public_result["idempotent_replay"] == "false"
    cb_id = first.public_result["callback_id"]

    second = binding.invoke(proposal=proposal, decision=decision, session=session)
    assert second.status is ActionStatus.SUCCEEDED
    assert second.public_result["idempotent_replay"] == "true"
    assert second.public_result["callback_id"] == cb_id
    assert len(binding.list_callbacks(tenant_id="tenant-a")) == 1
    assert len(binding.interaction_log(tenant_id="tenant-a")) == 1


# ── cross-tenant isolation ───────────────────────────────────────────────────


def test_cross_tenant_schedule_denies_and_does_not_record() -> None:
    binding = _binding()
    proposal = build_service_proposal(
        logical_action=SCHEDULE_LOGICAL_ACTION,
        arguments={"service_id": GROUNDED_SERVICE, "channel": "phone"},
        tenant_id="tenant-a",
        evidence=GROUNDED_EVIDENCE,
    )
    session = _auth_session(tenant_id="tenant-b")
    receipt = binding.invoke(
        proposal=proposal,
        decision=build_permit_decision(proposal),
        session=session,
    )
    assert receipt.status is ActionStatus.DENIED
    assert receipt.error == "cross_tenant_denied"
    assert binding.list_callbacks(tenant_id="tenant-a") == ()
    assert binding.list_callbacks(tenant_id="tenant-b") == ()
    assert "LEAK-ME" not in str(receipt.to_dict())


def test_cross_tenant_open_does_not_leak_other_tenant_catalog() -> None:
    binding = _binding()
    session = _auth_session(tenant_id="tenant-a", authenticated=False)
    # Attempt to open a tenant-b-only catalog row while authenticated as tenant-a.
    other_id = "svc-other-tenant-only"
    proposal = build_service_proposal(
        logical_action=OPEN_LOGICAL_ACTION,
        arguments={"service_id": other_id},
        tenant_id="tenant-a",
        evidence=(f"service_id:{other_id}",),
    )
    # Registry must ground the id so the failure is visibility, not grounding.
    binding = binding.with_grounded_services(other_id)
    receipt = binding.invoke(
        proposal=proposal,
        decision=build_permit_decision(proposal),
        session=session,
    )
    assert receipt.status is ActionStatus.SUCCEEDED
    assert receipt.public_result["found"] == "false"
    assert "LEAK-ME" not in str(receipt.to_dict())
    assert "Hidden Provider" not in str(receipt.to_dict())


def test_interaction_log_is_tenant_scoped() -> None:
    binding = _binding(seed=False)
    store = binding.store
    store.seed_callbacks(
        ServiceCallbackRecord(
            callback_id="cb-a-1",
            tenant_id="tenant-a",
            service_id=GROUNDED_SERVICE,
            proposal_digest="digest-a",
            channel="phone",
            callback_at="2026-08-10T12:00:00Z",
            client_id="client-abby",
            notes="tenant-a private notes",
            status="scheduled",
            created_at_epoch_s=1_700_000_100.0,
        ),
        ServiceCallbackRecord(
            callback_id="cb-b-1",
            tenant_id="tenant-b",
            service_id=GROUNDED_SERVICE,
            proposal_digest="digest-b",
            channel="sms",
            callback_at="",
            client_id="client-casey",
            notes="LEAK-ME tenant-b notes",
            status="scheduled",
            created_at_epoch_s=1_700_000_200.0,
        ),
    )
    log_a = binding.interaction_log(tenant_id="tenant-a")
    assert len(log_a) == 1
    assert log_a[0]["callback_id"] == "cb-a-1"
    assert "LEAK-ME" not in str(log_a)

    log_b = binding.interaction_log(tenant_id="tenant-b")
    assert len(log_b) == 1
    assert log_b[0]["callback_id"] == "cb-b-1"
    assert log_b[0]["notes_present"] is True
    # Raw notes still not exposed via interaction_log view.
    assert "LEAK-ME" not in str(log_b)


# ── service_id must be grounded ──────────────────────────────────────────────


def test_schedule_rejects_ungrounded_service_id() -> None:
    binding = _binding(grounded=(GROUNDED_SERVICE,), seed=True)
    session = _auth_session()
    proposal = build_service_proposal(
        logical_action=SCHEDULE_LOGICAL_ACTION,
        arguments={
            "service_id": UNGROUNDED_SERVICE,
            "channel": "phone",
            "notes": "Please call the free-text service I invented.",
        },
        tenant_id=session.tenant_id,
        # Evidence does not ground the free-text service.
        evidence=(f"service_id:{GROUNDED_SERVICE}",),
    )
    receipt = binding.invoke(
        proposal=proposal,
        decision=build_permit_decision(proposal),
        session=session,
    )
    assert receipt.status is ActionStatus.FAILED
    assert receipt.error == "service_id_not_grounded"
    assert binding.list_callbacks(tenant_id="tenant-a") == ()
    assert binding.interaction_log(tenant_id="tenant-a") == ()


def test_schedule_rejects_missing_service_id_at_binding() -> None:
    binding = _binding(seed=True)
    session = _auth_session()
    proposal = build_service_proposal(
        logical_action=SCHEDULE_LOGICAL_ACTION,
        arguments={"channel": "phone", "notes": "no service target"},
        tenant_id=session.tenant_id,
        evidence=GROUNDED_EVIDENCE,
    )
    receipt = binding.invoke(
        proposal=proposal,
        decision=build_permit_decision(proposal),
        session=session,
    )
    assert receipt.status is ActionStatus.FAILED
    assert receipt.error == "service_id_required"
    assert binding.list_callbacks(tenant_id="tenant-a") == ()


def test_open_rejects_ungrounded_service_id() -> None:
    binding = _binding(grounded=(GROUNDED_SERVICE,))
    session = _auth_session(authenticated=False)
    proposal = build_service_proposal(
        logical_action=OPEN_LOGICAL_ACTION,
        arguments={"service_id": UNGROUNDED_SERVICE},
        tenant_id=session.tenant_id,
        evidence=(f"service_id:{GROUNDED_SERVICE}",),
    )
    receipt = binding.invoke(
        proposal=proposal,
        decision=build_permit_decision(proposal),
        session=session,
    )
    assert receipt.status is ActionStatus.FAILED
    assert receipt.error == "service_id_not_grounded"


def test_schedule_accepts_service_grounded_via_proposal_evidence_only() -> None:
    # Registry empty; evidence alone grounds the service (authority-plane prefixes).
    binding = build_wallet_service_binding(grounded_service_ids=())
    seed_demo_service_catalog(binding.store)
    session = _auth_session()
    proposal = build_service_proposal(
        logical_action=SCHEDULE_LOGICAL_ACTION,
        arguments={
            "service_id": GROUNDED_SERVICE,
            "channel": "voice",
            "notes": "Evidence-grounded callback.",
        },
        tenant_id=session.tenant_id,
        evidence=(f"service:{GROUNDED_SERVICE}",),
    )
    receipt = binding.invoke(
        proposal=proposal,
        decision=build_permit_decision(proposal),
        session=session,
    )
    assert receipt.status is ActionStatus.SUCCEEDED, receipt.to_dict()
    assert receipt.public_result["service_id"] == GROUNDED_SERVICE
    assert len(binding.interaction_log(tenant_id="tenant-a")) == 1


def test_schedule_requires_confirm_and_auth() -> None:
    binding = _binding()
    proposal = build_service_proposal(
        logical_action=SCHEDULE_LOGICAL_ACTION,
        arguments={"service_id": GROUNDED_SERVICE, "channel": "phone"},
        tenant_id="tenant-a",
        evidence=GROUNDED_EVIDENCE,
    )
    decision = build_permit_decision(proposal)

    # Wallet-boundary auth gate fires before adapter when unauthenticated.
    unauth = binding.invoke(
        proposal=proposal,
        decision=decision,
        session=_auth_session(confirmed=True, authenticated=False),
    )
    assert unauth.status is ActionStatus.FAILED
    assert "auth_required" in (unauth.error or "")
    assert binding.list_callbacks(tenant_id="tenant-a") == ()

    # Confirmed+auth still required at adapter for schedule.
    unconfirmed = binding.invoke(
        proposal=proposal,
        decision=decision,
        session=_auth_session(confirmed=False, authenticated=True),
    )
    assert unconfirmed.status is ActionStatus.FAILED
    assert "confirmation_required" in (unconfirmed.error or "")
    assert binding.list_callbacks(tenant_id="tenant-a") == ()


def test_with_grounded_services_extends_registry() -> None:
    binding = _binding(grounded=(GROUNDED_SERVICE,), seed=True)
    other = "svc-food-pantry-demo"
    extended = binding.with_grounded_services(other)
    assert GROUNDED_SERVICE in extended.grounded_service_ids
    assert other in extended.grounded_service_ids

    session = _auth_session()
    proposal = build_service_proposal(
        logical_action=SCHEDULE_LOGICAL_ACTION,
        arguments={"service_id": other, "channel": "sms"},
        tenant_id=session.tenant_id,
        evidence=(f"service_id:{other}",),
    )
    receipt = extended.invoke(
        proposal=proposal,
        decision=build_permit_decision(proposal),
        session=session,
    )
    assert receipt.status is ActionStatus.SUCCEEDED
    assert receipt.public_result["service_id"] == other


def test_default_registrations_surface_constants() -> None:
    binding = build_wallet_service_binding()
    assert binding.surface_id == WALLET_SOCIAL_SERVICES_SURFACE
    assert binding.interaction_surface_id == WALLET_INTERACTIONS_SURFACE
    assert (
        binding.adapter.get_registration(OPEN_SERVICE_DETAIL_DESCRIPTOR_ID)
        is not None
    )
    assert (
        binding.adapter.get_registration(SCHEDULE_SERVICE_CALLBACK_DESCRIPTOR_ID)
        is not None
    )


def test_seed_catalog_shapes_match_wallet_service_models() -> None:
    """Demo seed uses service navigation–adjacent ids used by serviceActionService."""

    store = InMemoryServiceInteractionStore()
    seed_demo_service_catalog(store)
    rows = store.list_services()
    assert len(rows) >= 2
    assert isinstance(rows[0], ServiceDetailRecord)
    by_id = {r.service_id: r for r in rows}
    assert GROUNDED_SERVICE in by_id
    assert by_id[GROUNDED_SERVICE].title
    assert by_id[GROUNDED_SERVICE].provider_name
