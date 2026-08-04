"""Wallet binding for messaging adapter → provider-message surfaces.

Binds the authority-plane messaging adapter (``read_provider_messages`` /
``leave_provider_message``) to wallet provider-message inbox/outbox surfaces.

Safety rules (fail closed):

* Offline fake inbox/outbox only — no network, SMS, or telephony side effects
* Adapter execution requires a permitting ``ActionDecision`` bound to the proposal
* Reads are strictly tenant-scoped; cross-tenant access denies
* ``provider_id`` must be *grounded* (registry and/or proposal evidence) —
  free-text alone never authorizes a provider target
* Message bodies remain redacted in adapter receipts by default

Importing this module starts no processes and loads no credentials.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Final

from ipfs_accelerate_py.action_runtime.adapters.messaging import (
    InMemoryProviderMessageStore,
    MessagingActionAdapter,
    MessagingActionRegistration,
    MessagingInvocationContext,
    MessagingSandboxPolicy,
    ProviderMessageRecord,
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

# Stable pilot descriptor ids (must match catalog_211ai / messaging adapter).
READ_PROVIDER_MESSAGES_DESCRIPTOR_ID: Final = "voice.python.read_provider_messages.v1"
LEAVE_PROVIDER_MESSAGE_DESCRIPTOR_ID: Final = "voice.python.leave_provider_message.v1"

READ_LOGICAL_ACTION: Final = "read_provider_messages"
LEAVE_LOGICAL_ACTION: Final = "leave_provider_message"

# Wallet UI surface id for client/provider messages (navigation route).
WALLET_PROVIDER_MESSAGES_SURFACE: Final = "provider-messages"
WALLET_CLIENT_MESSAGES_SURFACE: Final = "messages"

# Evidence token prefixes accepted as grounding for a provider id.
# Longer prefixes first so ``provider_id:`` wins over ``provider:``.
_PROVIDER_EVIDENCE_PREFIXES: Final[tuple[str, ...]] = (
    "grounded_provider:",
    "provider_id:",
    "provider:",
    "service:",
    "svc:",
)

BINDING_VERSION: Final = "1.0"


def _text(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def normalize_provider_id(value: object | None) -> str | None:
    """Return a stripped provider id or ``None`` when absent/blank."""

    return _text(value)


def extract_grounded_provider_ids(
    grounded: Iterable[str] | None = None,
    *,
    evidence: Sequence[str] | None = None,
) -> frozenset[str]:
    """Collect grounded provider ids from an explicit registry and evidence tokens.

    Evidence may name a provider as:

    * the bare id (``provider-rose``)
    * a prefixed token (``provider:provider-rose``, ``provider_id:…``, …)
    """

    found: set[str] = set()
    for raw in grounded or ():
        pid = normalize_provider_id(raw)
        if pid:
            found.add(pid)
    for token in evidence or ():
        text = normalize_provider_id(token)
        if not text:
            continue
        matched_prefix = False
        lower = text.lower()
        for prefix in _PROVIDER_EVIDENCE_PREFIXES:
            if lower.startswith(prefix):
                pid = normalize_provider_id(text[len(prefix) :])
                if pid:
                    found.add(pid)
                matched_prefix = True
                break
        if not matched_prefix:
            # Bare evidence token may itself be a provider id.
            found.add(text)
    return frozenset(found)


def is_provider_id_grounded(
    provider_id: object | None,
    *,
    grounded_provider_ids: Iterable[str] | None = None,
    evidence: Sequence[str] | None = None,
) -> bool:
    """Return whether ``provider_id`` is present in the grounded set."""

    pid = normalize_provider_id(provider_id)
    if not pid:
        return False
    allowed = extract_grounded_provider_ids(grounded_provider_ids, evidence=evidence)
    return pid in allowed


def provider_grounding_error(
    provider_id: object | None,
    *,
    grounded_provider_ids: Iterable[str] | None = None,
    evidence: Sequence[str] | None = None,
) -> str | None:
    """Return a fail-closed error code when provider id is missing or ungrounded."""

    pid = normalize_provider_id(provider_id)
    if not pid:
        return "provider_id_required"
    if not is_provider_id_grounded(
        pid,
        grounded_provider_ids=grounded_provider_ids,
        evidence=evidence,
    ):
        return "provider_id_not_grounded"
    return None


@dataclass(frozen=True)
class WalletMessagingSession:
    """Caller session facts re-checked at the wallet binding boundary."""

    tenant_id: str
    authenticated: bool = False
    confirmed: bool = False
    client_id: str | None = None
    session_id: str | None = None
    channel: str = "voice"

    def to_messaging_context(self) -> MessagingInvocationContext:
        return MessagingInvocationContext(
            confirmed=self.confirmed,
            authenticated=self.authenticated,
            session_tenant_id=self.tenant_id,
        )


@dataclass
class WalletMessagingActionBinding:
    """Deployment binding: pilot messaging descriptors ↔ wallet message surfaces.

    Holds an offline fake inbox/outbox (``InMemoryProviderMessageStore``) and
    the admitted ``MessagingActionAdapter``.  The binding layer adds wallet-
    specific grounding of ``provider_id`` before adapter invocation.
    """

    adapter: MessagingActionAdapter
    grounded_provider_ids: frozenset[str] = field(default_factory=frozenset)
    surface_id: str = WALLET_PROVIDER_MESSAGES_SURFACE
    binding_version: str = BINDING_VERSION

    @property
    def store(self) -> InMemoryProviderMessageStore:
        store = self.adapter.store
        if not isinstance(store, InMemoryProviderMessageStore):
            raise TypeError("wallet messaging binding requires InMemoryProviderMessageStore")
        return store

    def with_grounded_providers(
        self,
        *provider_ids: str,
        replace: bool = False,
    ) -> WalletMessagingActionBinding:
        """Return a binding with additional (or replaced) grounded provider ids."""

        extra = {pid for pid in (normalize_provider_id(p) for p in provider_ids) if pid}
        if replace:
            grounded = frozenset(extra)
        else:
            grounded = frozenset(set(self.grounded_provider_ids) | extra)
        return WalletMessagingActionBinding(
            adapter=self.adapter,
            grounded_provider_ids=grounded,
            surface_id=self.surface_id,
            binding_version=self.binding_version,
        )

    def seed_inbox(self, *records: ProviderMessageRecord) -> None:
        """Seed inbound (or arbitrary) messages into the fake inbox."""

        self.store.seed(*records)

    def list_inbox(
        self,
        *,
        tenant_id: str,
        provider_id: str | None = None,
        client_id: str | None = None,
        limit: int = 50,
    ) -> tuple[ProviderMessageRecord, ...]:
        """Direct store list for tests/diagnostics (still tenant-scoped)."""

        if not tenant_id:
            return ()
        return tuple(
            self.store.list_messages(
                tenant_id=tenant_id,
                provider_id=provider_id,
                client_id=client_id,
                limit=limit,
            )
        )

    def list_outbox(
        self,
        *,
        tenant_id: str,
        provider_id: str | None = None,
        client_id: str | None = None,
        limit: int = 50,
    ) -> tuple[ProviderMessageRecord, ...]:
        """Return outbound (client→provider) rows for a tenant."""

        rows = self.list_inbox(
            tenant_id=tenant_id,
            provider_id=provider_id,
            client_id=client_id,
            limit=limit,
        )
        return tuple(r for r in rows if r.direction == "outbound")

    def resolve_grounded_providers(
        self,
        proposal: ActionProposal | None = None,
        *,
        extra_evidence: Sequence[str] | None = None,
    ) -> frozenset[str]:
        evidence: list[str] = []
        if proposal is not None:
            evidence.extend(proposal.evidence)
        if extra_evidence:
            evidence.extend(extra_evidence)
        return extract_grounded_provider_ids(
            self.grounded_provider_ids,
            evidence=evidence,
        )

    def _grounding_gate(
        self,
        proposal: ActionProposal,
        *,
        require_provider_id: bool,
    ) -> str | None:
        """Fail closed when provider_id is required/ungrounded for this call."""

        args = dict(proposal.arguments)
        raw_provider = args.get("provider_id")
        pid = normalize_provider_id(raw_provider)

        if not require_provider_id and pid is None:
            # Whole-tenant inbox read without a provider filter is allowed when
            # the caller is otherwise authorized; no free-text provider target.
            return None

        grounded = self.resolve_grounded_providers(proposal)
        return provider_grounding_error(
            pid,
            grounded_provider_ids=grounded,
            evidence=(),
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
            receipt_id=f"rcpt-wallet-msg-{uuid.uuid4().hex[:12]}",
            status=ActionStatus.FAILED,
            proposal_id=proposal.proposal_id,
            decision_id=decision.decision_id,
            descriptor_id=proposal.descriptor_id,
            adapter="messaging",
            interface_identity=f"wallet-messaging:{self.surface_id}",
            started_epoch_s=started,
            completed_epoch_s=time.time(),
            error=error,
            metadata={
                "binding_version": self.binding_version,
                "surface_id": self.surface_id,
                "layer": "wallet_messaging_binding",
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
            receipt_id=f"rcpt-wallet-msg-{uuid.uuid4().hex[:12]}",
            status=ActionStatus.DENIED,
            proposal_id=proposal.proposal_id,
            decision_id=decision.decision_id,
            descriptor_id=proposal.descriptor_id,
            adapter="messaging",
            interface_identity=f"wallet-messaging:{self.surface_id}",
            started_epoch_s=started,
            completed_epoch_s=time.time(),
            error=error,
            metadata={
                "binding_version": self.binding_version,
                "surface_id": self.surface_id,
                "layer": "wallet_messaging_binding",
            },
        )

    def invoke(
        self,
        *,
        proposal: ActionProposal,
        decision: ActionDecision,
        session: WalletMessagingSession,
    ) -> ActionReceipt:
        """Invoke the messaging adapter after wallet grounding + session gates.

        Returns a failed/denied receipt without store mutation when:

        * decision does not permit execution
        * session tenant mismatches proposal tenant
        * provider_id is required and not grounded
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
        if logical == LEAVE_LOGICAL_ACTION:
            gate = self._grounding_gate(proposal, require_provider_id=True)
            if gate is not None:
                return self._failed_receipt(
                    proposal=proposal,
                    decision=decision,
                    error=gate,
                    started=started,
                )
        elif logical == READ_LOGICAL_ACTION:
            gate = self._grounding_gate(proposal, require_provider_id=False)
            if gate is not None:
                return self._failed_receipt(
                    proposal=proposal,
                    decision=decision,
                    error=gate,
                    started=started,
                )
        else:
            return self._failed_receipt(
                proposal=proposal,
                decision=decision,
                error=f"unsupported_logical_action:{logical}",
                started=started,
            )

        context = session.to_messaging_context()
        receipt = self.adapter.invoke(
            proposal=proposal,
            decision=decision,
            context=context,
        )
        # Annotate successful receipts with wallet surface metadata (copy-on-write).
        meta = dict(receipt.metadata)
        meta.setdefault("binding_version", self.binding_version)
        meta.setdefault("surface_id", self.surface_id)
        meta.setdefault("layer", "wallet_messaging_binding")
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

    def read_provider_messages(
        self,
        *,
        session: WalletMessagingSession,
        decision: ActionDecision,
        proposal: ActionProposal | None = None,
        provider_id: str | None = None,
        client_id: str | None = None,
        limit: int | None = None,
        proposal_id: str | None = None,
        evidence: Sequence[str] | None = None,
    ) -> ActionReceipt:
        """Convenience: build/read proposal for the wallet inbox surface."""

        args: dict[str, str] = {}
        if provider_id is not None:
            args["provider_id"] = str(provider_id)
        if client_id is not None:
            args["client_id"] = str(client_id)
        elif session.client_id:
            args["client_id"] = session.client_id
        if limit is not None:
            args["limit"] = str(int(limit))

        if proposal is None:
            proposal = build_messaging_proposal(
                logical_action=READ_LOGICAL_ACTION,
                arguments=args,
                tenant_id=session.tenant_id,
                session_id=session.session_id,
                channel=session.channel,
                evidence=evidence or (),
                proposal_id=proposal_id or f"prop-read-{uuid.uuid4().hex[:12]}",
            )
        return self.invoke(proposal=proposal, decision=decision, session=session)

    def leave_provider_message(
        self,
        *,
        session: WalletMessagingSession,
        decision: ActionDecision,
        provider_id: str,
        body: str,
        proposal: ActionProposal | None = None,
        client_id: str | None = None,
        channel: str = "in_app",
        subject: str = "",
        proposal_id: str | None = None,
        evidence: Sequence[str] | None = None,
    ) -> ActionReceipt:
        """Convenience: leave an outbound message on the wallet outbox surface."""

        args: dict[str, str] = {
            "provider_id": str(provider_id),
            "body": body,
            "channel": channel,
            "subject": subject,
        }
        cid = client_id or session.client_id
        if cid:
            args["client_id"] = cid

        if proposal is None:
            proposal = build_messaging_proposal(
                logical_action=LEAVE_LOGICAL_ACTION,
                arguments=args,
                tenant_id=session.tenant_id,
                session_id=session.session_id,
                channel=session.channel,
                evidence=evidence or (),
                proposal_id=proposal_id or f"prop-leave-{uuid.uuid4().hex[:12]}",
            )
        return self.invoke(proposal=proposal, decision=decision, session=session)


def build_messaging_proposal(
    *,
    logical_action: str,
    arguments: Mapping[str, str] | None = None,
    tenant_id: str | None = None,
    session_id: str | None = None,
    channel: str | None = "voice",
    evidence: Sequence[str] = (),
    proposal_id: str | None = None,
    confidence: float = 0.99,
    source: str = "wallet_messaging_binding",
    route: str = "provider_contact_support",
) -> ActionProposal:
    """Build a catalog-bound messaging proposal (no executables)."""

    if logical_action == READ_LOGICAL_ACTION:
        descriptor_id = READ_PROVIDER_MESSAGES_DESCRIPTOR_ID
    elif logical_action == LEAVE_LOGICAL_ACTION:
        descriptor_id = LEAVE_PROVIDER_MESSAGE_DESCRIPTOR_ID
    else:
        raise ValueError(f"unsupported_logical_action:{logical_action}")

    return ActionProposal(
        proposal_id=proposal_id or f"prop-msg-{uuid.uuid4().hex[:12]}",
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
            "surface_id": WALLET_PROVIDER_MESSAGES_SURFACE,
            "family": "messaging",
        },
    )


def build_permit_decision(
    proposal: ActionProposal,
    *,
    kind: ActionDecisionKind | None = None,
    risk_class: RiskClass | None = None,
    decision_id: str | None = None,
    reason: str = "wallet_messaging_permit",
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
        decision_id=decision_id or f"dec-msg-{uuid.uuid4().hex[:12]}",
        kind=kind,
        proposal_id=proposal.proposal_id,
        descriptor_id=proposal.descriptor_id,
        descriptor_digest=content_digest(
            {"descriptor_id": proposal.descriptor_id, "logical_action": proposal.logical_action}
        ),
        arguments_digest=proposal.arguments_digest,
        reason=reason,
        risk_class=risk_class,
    )


def build_wallet_messaging_binding(
    *,
    grounded_provider_ids: Iterable[str] | None = None,
    store: InMemoryProviderMessageStore | None = None,
    sandbox: MessagingSandboxPolicy | None = None,
    registrations: Sequence[MessagingActionRegistration] | None = None,
    surface_id: str = WALLET_PROVIDER_MESSAGES_SURFACE,
    seed: Sequence[ProviderMessageRecord] | None = None,
) -> WalletMessagingActionBinding:
    """Construct the wallet messaging binding with optional fake seed data."""

    message_store = store or InMemoryProviderMessageStore()
    if seed:
        message_store.seed(*seed)

    policy = sandbox or MessagingSandboxPolicy()
    if registrations is None:
        regs = (
            MessagingActionRegistration(
                descriptor_id=READ_PROVIDER_MESSAGES_DESCRIPTOR_ID,
                logical_action=READ_LOGICAL_ACTION,
                sandbox=policy,
            ),
            MessagingActionRegistration(
                descriptor_id=LEAVE_PROVIDER_MESSAGE_DESCRIPTOR_ID,
                logical_action=LEAVE_LOGICAL_ACTION,
                sandbox=policy,
            ),
        )
    else:
        regs = tuple(registrations)

    adapter = MessagingActionAdapter(regs, store=message_store)
    grounded = extract_grounded_provider_ids(grounded_provider_ids)
    return WalletMessagingActionBinding(
        adapter=adapter,
        grounded_provider_ids=grounded,
        surface_id=surface_id,
    )


def seed_demo_inbox(
    store: InMemoryProviderMessageStore,
    *,
    tenant_id: str = "tenant-a",
    provider_id: str = "provider-rose",
    other_tenant_id: str = "tenant-b",
) -> None:
    """Seed a small multi-tenant fake inbox for offline acceptance tests."""

    store.seed(
        ProviderMessageRecord(
            message_id="msg-inbox-a-1",
            tenant_id=tenant_id,
            provider_id=provider_id,
            client_id="client-abby",
            channel="in_app",
            subject="Intake appointment reminder",
            body="Your Rose City Shelter intake appointment is on your calendar.",
            direction="inbound",
            status="sent",
            created_at_epoch_s=1_700_000_100.0,
        ),
        ProviderMessageRecord(
            message_id="msg-inbox-b-1",
            tenant_id=other_tenant_id,
            provider_id=provider_id,
            client_id="client-casey",
            channel="sms",
            subject="Other tenant secret",
            body="LEAK-ME cross-tenant body",
            direction="inbound",
            status="sent",
            created_at_epoch_s=1_700_000_200.0,
        ),
    )


def binding_public_summary(receipt: ActionReceipt) -> dict[str, Any]:
    """Compact wire-safe summary of a messaging receipt for wallet clients."""

    return {
        "status": receipt.status.value if hasattr(receipt.status, "value") else str(receipt.status),
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
    "LEAVE_LOGICAL_ACTION",
    "LEAVE_PROVIDER_MESSAGE_DESCRIPTOR_ID",
    "READ_LOGICAL_ACTION",
    "READ_PROVIDER_MESSAGES_DESCRIPTOR_ID",
    "WALLET_CLIENT_MESSAGES_SURFACE",
    "WALLET_PROVIDER_MESSAGES_SURFACE",
    "WalletMessagingActionBinding",
    "WalletMessagingSession",
    "binding_public_summary",
    "build_messaging_proposal",
    "build_permit_decision",
    "build_wallet_messaging_binding",
    "extract_grounded_provider_ids",
    "is_provider_id_grounded",
    "normalize_provider_id",
    "provider_grounding_error",
    "seed_demo_inbox",
]
