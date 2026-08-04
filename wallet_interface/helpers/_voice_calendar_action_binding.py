"""Wallet binding for calendar adapter → wallet calendar service surfaces.

Binds the authority-plane calendar adapter (``read_calendar`` /
``create_calendar_reminder``) to an offline fake wallet calendar store
(``InMemoryCalendarEventStore``). Product backends may later replace the
injected store; this binding never opens network calendar APIs.

Safety rules (fail closed):

* Offline fake calendar store only — no network, ICS download, or filesystem
  side effects from this binding
* Adapter execution requires a permitting ``ActionDecision`` bound to the
  proposal
* Reads are strictly tenant-scoped; cross-tenant access denies
* ``create_calendar_reminder`` re-checks authentication at the wallet boundary
  (defense in depth with adapter sandbox)
* Event notes remain redacted in adapter receipts by default
* Structured slots only — no raw ICS injection from free text

Importing this module starts no processes and loads no credentials.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Final

from ipfs_accelerate_py.action_runtime.adapters.calendar import (
    CREATE_LOGICAL_ACTION,
    READ_LOGICAL_ACTION,
    CalendarActionAdapter,
    CalendarActionRegistration,
    CalendarEventRecord,
    CalendarInvocationContext,
    CalendarSandboxPolicy,
    InMemoryCalendarEventStore,
    default_calendar_registrations,
)
from ipfs_accelerate_py.action_runtime.contracts import (
    ActionDecision,
    ActionDecisionKind,
    ActionProposal,
    ActionReceipt,
    ActionStatus,
    RiskClass,
    content_digest,
)

# Stable pilot descriptor ids (must match catalog_211ai / calendar adapter).
READ_CALENDAR_DESCRIPTOR_ID: Final = "voice.python.read_calendar.v1"
CREATE_CALENDAR_REMINDER_DESCRIPTOR_ID: Final = (
    "voice.python.create_calendar_reminder.v1"
)

# Re-export logical action names for wallet callers / tests.
READ_LOGICAL = READ_LOGICAL_ACTION
CREATE_LOGICAL = CREATE_LOGICAL_ACTION

# Wallet UI surface id for client calendar (navigation route).
WALLET_CALENDAR_SURFACE: Final = "calendar"
WALLET_CALENDAR_SUPPORT_ROUTE: Final = "calendar_event_support"

BINDING_VERSION: Final = "1.0"


def _text(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


@dataclass(frozen=True)
class WalletCalendarSession:
    """Caller session facts re-checked at the wallet binding boundary."""

    tenant_id: str
    authenticated: bool = False
    confirmed: bool = False
    client_id: str | None = None
    session_id: str | None = None
    channel: str = "voice"

    def to_calendar_context(self) -> CalendarInvocationContext:
        return CalendarInvocationContext(
            confirmed=self.confirmed,
            authenticated=self.authenticated,
            session_tenant_id=self.tenant_id,
        )


@dataclass
class WalletCalendarActionBinding:
    """Deployment binding: pilot calendar descriptors ↔ wallet calendar surface.

    Holds an offline fake calendar store (``InMemoryCalendarEventStore``) and
    the admitted ``CalendarActionAdapter``.  The binding layer adds wallet-
    specific session gates (auth for writes, cross-tenant deny) before adapter
    invocation.
    """

    adapter: CalendarActionAdapter
    surface_id: str = WALLET_CALENDAR_SURFACE
    binding_version: str = BINDING_VERSION
    # Wallet-boundary re-check: create always requires authenticated session.
    require_auth_for_create: bool = True

    @property
    def store(self) -> InMemoryCalendarEventStore:
        store = self.adapter.store
        if not isinstance(store, InMemoryCalendarEventStore):
            raise TypeError(
                "wallet calendar binding requires InMemoryCalendarEventStore"
            )
        return store

    def seed_events(self, *records: CalendarEventRecord) -> None:
        """Seed events into the offline fake calendar store."""

        self.store.seed(*records)

    def list_events(
        self,
        *,
        tenant_id: str,
        starts_after: str | None = None,
        ends_before: str | None = None,
        event_id: str | None = None,
        limit: int = 50,
    ) -> tuple[CalendarEventRecord, ...]:
        """Direct store list for tests/diagnostics (still tenant-scoped)."""

        if not tenant_id:
            return ()
        return tuple(
            self.store.list_events(
                tenant_id=tenant_id,
                starts_after=starts_after,
                ends_before=ends_before,
                event_id=event_id,
                limit=limit,
            )
        )

    def _failed_receipt(
        self,
        *,
        proposal: ActionProposal,
        decision: ActionDecision,
        error: str,
        started: float,
    ) -> ActionReceipt:
        return ActionReceipt(
            receipt_id=f"rcpt-wallet-cal-{uuid.uuid4().hex[:12]}",
            status=ActionStatus.FAILED,
            proposal_id=proposal.proposal_id,
            decision_id=decision.decision_id,
            descriptor_id=proposal.descriptor_id,
            adapter="calendar",
            interface_identity=f"wallet-calendar:{self.surface_id}",
            started_epoch_s=started,
            completed_epoch_s=time.time(),
            error=error,
            metadata={
                "binding_version": self.binding_version,
                "surface_id": self.surface_id,
                "layer": "wallet_calendar_binding",
            },
        )

    def _denied_receipt(
        self,
        *,
        proposal: ActionProposal,
        decision: ActionDecision,
        error: str,
        started: float,
    ) -> ActionReceipt:
        return ActionReceipt(
            receipt_id=f"rcpt-wallet-cal-{uuid.uuid4().hex[:12]}",
            status=ActionStatus.DENIED,
            proposal_id=proposal.proposal_id,
            decision_id=decision.decision_id,
            descriptor_id=proposal.descriptor_id,
            adapter="calendar",
            interface_identity=f"wallet-calendar:{self.surface_id}",
            started_epoch_s=started,
            completed_epoch_s=time.time(),
            error=error,
            metadata={
                "binding_version": self.binding_version,
                "surface_id": self.surface_id,
                "layer": "wallet_calendar_binding",
            },
        )

    def invoke(
        self,
        *,
        proposal: ActionProposal,
        decision: ActionDecision,
        session: WalletCalendarSession,
    ) -> ActionReceipt:
        """Invoke the calendar adapter after wallet session gates.

        Returns a failed/denied receipt without store mutation when:

        * decision does not permit execution
        * session tenant mismatches proposal tenant
        * create is attempted without an authenticated session
        * logical action is not a calendar pilot action
        """

        started = time.time()

        if not decision.permits_execution:
            return self._denied_receipt(
                proposal=proposal,
                decision=decision,
                error=f"decision_does_not_permit_execution:{decision.kind.value}",
                started=started,
            )

        # Cross-tenant: proposal and session tenants must agree when both set.
        proposal_tenant = _text(proposal.tenant_id)
        session_tenant = _text(session.tenant_id)
        if not session_tenant:
            return self._failed_receipt(
                proposal=proposal,
                decision=decision,
                error="tenant_required",
                started=started,
            )
        if proposal_tenant and proposal_tenant != session_tenant:
            return self._denied_receipt(
                proposal=proposal,
                decision=decision,
                error="cross_tenant_denied",
                started=started,
            )

        logical = proposal.logical_action
        if logical not in {READ_LOGICAL_ACTION, CREATE_LOGICAL_ACTION}:
            return self._failed_receipt(
                proposal=proposal,
                decision=decision,
                error=f"unsupported_logical_action:{logical}",
                started=started,
            )

        # Wallet-boundary auth gate for writes (fail closed before store I/O).
        if logical == CREATE_LOGICAL_ACTION and self.require_auth_for_create:
            if not session.authenticated:
                return self._failed_receipt(
                    proposal=proposal,
                    decision=decision,
                    error="auth_required",
                    started=started,
                )

        context = session.to_calendar_context()
        receipt = self.adapter.invoke(
            proposal=proposal,
            decision=decision,
            context=context,
        )
        # Annotate receipts with wallet surface metadata (copy-on-write).
        meta = dict(receipt.metadata)
        meta.setdefault("binding_version", self.binding_version)
        meta.setdefault("surface_id", self.surface_id)
        meta.setdefault("layer", "wallet_calendar_binding")
        return ActionReceipt(
            receipt_id=receipt.receipt_id,
            status=receipt.status,
            proposal_id=receipt.proposal_id,
            decision_id=receipt.decision_id,
            descriptor_id=receipt.descriptor_id,
            adapter=receipt.adapter,
            interface_identity=receipt.interface_identity,
            started_epoch_s=receipt.started_epoch_s,
            completed_epoch_s=receipt.completed_epoch_s,
            exit_code=receipt.exit_code,
            stdout_digest=receipt.stdout_digest,
            stderr_digest=receipt.stderr_digest,
            public_result=dict(receipt.public_result),
            error=receipt.error,
            metadata=meta,
        )

    def read_calendar(
        self,
        *,
        session: WalletCalendarSession,
        decision: ActionDecision,
        proposal: ActionProposal | None = None,
        limit: int | None = None,
        starts_after: str | None = None,
        ends_before: str | None = None,
        event_id: str | None = None,
        proposal_id: str | None = None,
        evidence: Sequence[str] | None = None,
    ) -> ActionReceipt:
        """Convenience: build/read proposal for the wallet calendar surface."""

        args: dict[str, str] = {}
        if limit is not None:
            args["limit"] = str(int(limit))
        if starts_after is not None:
            args["starts_after"] = str(starts_after)
        if ends_before is not None:
            args["ends_before"] = str(ends_before)
        if event_id is not None:
            args["event_id"] = str(event_id)

        if proposal is None:
            proposal = build_calendar_proposal(
                logical_action=READ_LOGICAL_ACTION,
                arguments=args,
                tenant_id=session.tenant_id,
                session_id=session.session_id,
                channel=session.channel,
                evidence=evidence or (),
                proposal_id=proposal_id or f"prop-cal-read-{uuid.uuid4().hex[:12]}",
            )
        return self.invoke(proposal=proposal, decision=decision, session=session)

    def create_calendar_reminder(
        self,
        *,
        session: WalletCalendarSession,
        decision: ActionDecision,
        title: str,
        starts_at: str,
        proposal: ActionProposal | None = None,
        ends_at: str | None = None,
        duration_minutes: int | None = None,
        notes: str = "",
        location: str = "",
        all_day: bool = False,
        reminder_minutes_before: int = 0,
        proposal_id: str | None = None,
        evidence: Sequence[str] | None = None,
    ) -> ActionReceipt:
        """Convenience: create a reminder on the wallet calendar surface."""

        args: dict[str, str] = {
            "title": title,
            "starts_at": starts_at,
            "all_day": "true" if all_day else "false",
            "reminder_minutes_before": str(int(reminder_minutes_before)),
        }
        if ends_at is not None:
            args["ends_at"] = ends_at
        if duration_minutes is not None:
            args["duration_minutes"] = str(int(duration_minutes))
        if notes:
            args["notes"] = notes
        if location:
            args["location"] = location

        if proposal is None:
            proposal = build_calendar_proposal(
                logical_action=CREATE_LOGICAL_ACTION,
                arguments=args,
                tenant_id=session.tenant_id,
                session_id=session.session_id,
                channel=session.channel,
                evidence=evidence or (),
                proposal_id=proposal_id
                or f"prop-cal-create-{uuid.uuid4().hex[:12]}",
            )
        return self.invoke(proposal=proposal, decision=decision, session=session)


def build_calendar_proposal(
    *,
    logical_action: str,
    arguments: Mapping[str, str] | None = None,
    tenant_id: str | None = None,
    session_id: str | None = None,
    channel: str | None = "voice",
    evidence: Sequence[str] = (),
    proposal_id: str | None = None,
    confidence: float = 0.99,
    source: str = "wallet_calendar_binding",
    route: str = WALLET_CALENDAR_SUPPORT_ROUTE,
) -> ActionProposal:
    """Build a catalog-bound calendar proposal (no executables / raw ICS)."""

    if logical_action == READ_LOGICAL_ACTION:
        descriptor_id = READ_CALENDAR_DESCRIPTOR_ID
    elif logical_action == CREATE_LOGICAL_ACTION:
        descriptor_id = CREATE_CALENDAR_REMINDER_DESCRIPTOR_ID
    else:
        raise ValueError(f"unsupported_logical_action:{logical_action}")

    return ActionProposal(
        proposal_id=proposal_id or f"prop-cal-{uuid.uuid4().hex[:12]}",
        descriptor_id=descriptor_id,
        logical_action=logical_action,
        arguments=dict(arguments or {}),
        route=route,
        source=source,
        confidence=confidence,
        tenant_id=tenant_id,
        session_id=session_id,
        channel=channel,
        evidence=tuple(evidence),
        metadata={
            "surface_id": WALLET_CALENDAR_SURFACE,
            "family": "calendar",
        },
    )


def build_permit_decision(
    proposal: ActionProposal,
    *,
    kind: ActionDecisionKind | None = None,
    risk_class: RiskClass | None = None,
    decision_id: str | None = None,
    reason: str = "wallet_calendar_permit",
) -> ActionDecision:
    """Build a permitting decision bound to ``proposal`` digests."""

    if kind is None:
        if proposal.logical_action == READ_LOGICAL_ACTION:
            kind = ActionDecisionKind.PERMIT_READ
        else:
            kind = ActionDecisionKind.PERMIT_EXECUTE
    if risk_class is None:
        risk_class = (
            RiskClass.READ
            if proposal.logical_action == READ_LOGICAL_ACTION
            else RiskClass.WRITE
        )
    return ActionDecision(
        decision_id=decision_id or f"dec-cal-{uuid.uuid4().hex[:12]}",
        kind=kind,
        proposal_id=proposal.proposal_id,
        descriptor_id=proposal.descriptor_id,
        descriptor_digest=content_digest(
            {
                "descriptor_id": proposal.descriptor_id,
                "logical_action": proposal.logical_action,
            }
        ),
        arguments_digest=proposal.arguments_digest,
        reason=reason,
        risk_class=risk_class,
    )


def build_wallet_calendar_binding(
    *,
    store: InMemoryCalendarEventStore | None = None,
    sandbox: CalendarSandboxPolicy | None = None,
    registrations: Sequence[CalendarActionRegistration] | None = None,
    surface_id: str = WALLET_CALENDAR_SURFACE,
    seed: Sequence[CalendarEventRecord] | None = None,
    require_auth_for_create: bool = True,
) -> WalletCalendarActionBinding:
    """Construct the wallet calendar binding with optional fake seed data."""

    event_store = store or InMemoryCalendarEventStore()
    if seed:
        event_store.seed(*seed)

    if registrations is None:
        if sandbox is None:
            regs = default_calendar_registrations()
        else:
            regs = (
                CalendarActionRegistration(
                    descriptor_id=READ_CALENDAR_DESCRIPTOR_ID,
                    logical_action=READ_LOGICAL_ACTION,
                    sandbox=sandbox,
                ),
                CalendarActionRegistration(
                    descriptor_id=CREATE_CALENDAR_REMINDER_DESCRIPTOR_ID,
                    logical_action=CREATE_LOGICAL_ACTION,
                    sandbox=sandbox,
                ),
            )
    else:
        regs = tuple(registrations)

    adapter = CalendarActionAdapter(regs, store=event_store)
    return WalletCalendarActionBinding(
        adapter=adapter,
        surface_id=surface_id,
        require_auth_for_create=require_auth_for_create,
    )


def seed_demo_calendar(
    store: InMemoryCalendarEventStore,
    *,
    tenant_id: str = "tenant-a",
    other_tenant_id: str = "tenant-b",
) -> None:
    """Seed a small multi-tenant fake calendar for offline acceptance tests."""

    store.seed(
        CalendarEventRecord(
            event_id="evt-a-1",
            tenant_id=tenant_id,
            title="Intake appointment",
            starts_at="2026-08-05T10:00:00Z",
            ends_at="2026-08-05T10:30:00Z",
            notes="Bring photo ID. SECRET-TENANT-A notes.",
            location="Rose City Shelter front desk",
            all_day=False,
            reminder_minutes_before=30,
            status="scheduled",
            created_at_epoch_s=1_700_000_100.0,
        ),
        CalendarEventRecord(
            event_id="evt-b-1",
            tenant_id=other_tenant_id,
            title="Other tenant secret event",
            starts_at="2026-08-06T09:00:00Z",
            ends_at="2026-08-06T09:45:00Z",
            notes="LEAK-ME cross-tenant calendar notes",
            location="Hidden location",
            all_day=False,
            reminder_minutes_before=15,
            status="scheduled",
            created_at_epoch_s=1_700_000_200.0,
        ),
    )


def binding_public_summary(receipt: ActionReceipt) -> dict[str, Any]:
    """Compact wire-safe summary of a calendar receipt for wallet clients."""

    return {
        "status": (
            receipt.status.value
            if hasattr(receipt.status, "value")
            else str(receipt.status)
        ),
        "error": receipt.error,
        "public_result": dict(receipt.public_result),
        "descriptor_id": receipt.descriptor_id,
        "adapter": receipt.adapter,
        "surface_id": (receipt.metadata or {}).get("surface_id"),
        "binding_version": (receipt.metadata or {}).get("binding_version"),
    }


# Re-export adapter primitives commonly needed by tests without deep imports.
__all__ = [
    "BINDING_VERSION",
    "CREATE_CALENDAR_REMINDER_DESCRIPTOR_ID",
    "CREATE_LOGICAL",
    "CREATE_LOGICAL_ACTION",
    "READ_CALENDAR_DESCRIPTOR_ID",
    "READ_LOGICAL",
    "READ_LOGICAL_ACTION",
    "WALLET_CALENDAR_SUPPORT_ROUTE",
    "WALLET_CALENDAR_SURFACE",
    "WalletCalendarActionBinding",
    "WalletCalendarSession",
    "binding_public_summary",
    "build_calendar_proposal",
    "build_permit_decision",
    "build_wallet_calendar_binding",
    "seed_demo_calendar",
]
