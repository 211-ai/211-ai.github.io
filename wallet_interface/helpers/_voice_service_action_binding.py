"""Wallet binding for service interaction adapter → serviceActionService surfaces.

Binds the authority-plane service interaction adapter
(``open_service_detail`` / ``schedule_service_callback``) to wallet service-
navigation interaction models (``serviceActionService`` /
``serviceInteractionService``).

Safety rules (fail closed):

* Offline fake service catalog + interaction log only — no network, telephony,
  SMS, or browser handoff side effects from this binding
* Adapter execution requires a permitting ``ActionDecision`` bound to the
  proposal
* Callbacks are recorded in the interaction log under permit only
* ``service_id`` must be *grounded* (registry and/or proposal evidence) —
  free-text alone never authorizes a service target
* Reads and writes are tenant-scoped; cross-tenant access denies
* Notes / summaries remain redacted in adapter receipts by default
* ``schedule_service_callback`` re-checks authentication at the wallet boundary
  (defense in depth with adapter sandbox)

Importing this module starts no processes and loads no credentials.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Final

from ipfs_accelerate_py.action_runtime.adapters.service_interaction import (
    OPEN_LOGICAL_ACTION,
    SCHEDULE_LOGICAL_ACTION,
    InMemoryServiceInteractionStore,
    ServiceCallbackRecord,
    ServiceDetailRecord,
    ServiceInteractionActionAdapter,
    ServiceInteractionActionRegistration,
    ServiceInteractionInvocationContext,
    ServiceInteractionSandboxPolicy,
    default_service_interaction_registrations,
    grounded_service_tokens,
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

# Stable pilot descriptor ids (must match catalog_211ai / service interaction).
OPEN_SERVICE_DETAIL_DESCRIPTOR_ID: Final = "voice.python.open_service_detail.v1"
SCHEDULE_SERVICE_CALLBACK_DESCRIPTOR_ID: Final = (
    "voice.workflow.schedule_service_callback.v1"
)

# Re-export logical action names for wallet callers / tests.
OPEN_LOGICAL: Final = OPEN_LOGICAL_ACTION
SCHEDULE_LOGICAL: Final = SCHEDULE_LOGICAL_ACTION

# Wallet UI surfaces for service navigation / interaction log.
WALLET_SOCIAL_SERVICES_SURFACE: Final = "social-services"
WALLET_INTERACTIONS_SURFACE: Final = "interactions"
WALLET_SERVICE_INTERACTION_SUPPORT_ROUTE: Final = "service_interaction_support"

# Product interaction type mirrored from serviceInteractionService.
INTERACTION_TYPE_CALLBACK_REQUESTED: Final = "callback_requested"
INTERACTION_TYPE_VIEWED_SERVICE: Final = "viewed_service"

# Evidence token prefixes accepted as grounding for a service id.
# Longer prefixes first so ``service_id:`` / ``service_doc_id:`` win over shorter.
_SERVICE_EVIDENCE_PREFIXES: Final[tuple[str, ...]] = (
    "service_doc_id:",
    "service_id:",
    "grounded_service:",
    "service:",
    "svc:",
)

BINDING_VERSION: Final = "1.0"


def _text(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def normalize_service_id(value: object | None) -> str | None:
    """Return a stripped service id or ``None`` when absent/blank."""

    return _text(value)


def extract_grounded_service_ids(
    grounded: Iterable[str] | None = None,
    *,
    evidence: Sequence[str] | None = None,
) -> frozenset[str]:
    """Collect grounded service ids from an explicit registry and evidence tokens.

    Evidence may name a service as:

    * the bare id (``svc-housing-211-demo``)
    * a prefixed token (``service_id:…``, ``service:…``, ``service_doc_id:…``, …)
    """

    found: set[str] = set()
    for raw in grounded or ():
        sid = normalize_service_id(raw)
        if sid:
            found.add(sid)
    for token in evidence or ():
        text = normalize_service_id(token)
        if not text:
            continue
        matched_prefix = False
        lower = text.lower()
        for prefix in _SERVICE_EVIDENCE_PREFIXES:
            if lower.startswith(prefix):
                sid = normalize_service_id(text[len(prefix) :])
                if sid:
                    found.add(sid)
                matched_prefix = True
                break
        if not matched_prefix:
            # Bare evidence token may itself be a service id.
            found.add(text)
    # Also admit tokens via the adapter helper for parity with authority plane.
    if evidence:
        found.update(grounded_service_tokens(tuple(evidence)))
    return frozenset(found)


def is_service_id_grounded(
    service_id: object | None,
    *,
    grounded_service_ids: Iterable[str] | None = None,
    evidence: Sequence[str] | None = None,
) -> bool:
    """Return whether ``service_id`` is present in the grounded set."""

    sid = normalize_service_id(service_id)
    if not sid:
        return False
    allowed = extract_grounded_service_ids(grounded_service_ids, evidence=evidence)
    return sid in allowed


def service_grounding_error(
    service_id: object | None,
    *,
    grounded_service_ids: Iterable[str] | None = None,
    evidence: Sequence[str] | None = None,
) -> str | None:
    """Return a fail-closed error code when service id is missing or ungrounded."""

    sid = normalize_service_id(service_id)
    if not sid:
        return "service_id_required"
    if not is_service_id_grounded(
        sid,
        grounded_service_ids=grounded_service_ids,
        evidence=evidence,
    ):
        return "service_id_not_grounded"
    return None


@dataclass(frozen=True)
class WalletServiceSession:
    """Caller session facts re-checked at the wallet binding boundary."""

    tenant_id: str
    authenticated: bool = False
    confirmed: bool = False
    client_id: str | None = None
    session_id: str | None = None
    channel: str = "voice"

    def to_service_context(self) -> ServiceInteractionInvocationContext:
        return ServiceInteractionInvocationContext(
            confirmed=self.confirmed,
            authenticated=self.authenticated,
            session_tenant_id=self.tenant_id,
        )


@dataclass
class WalletServiceActionBinding:
    """Deployment binding: pilot service descriptors ↔ wallet interaction log.

    Holds an offline fake catalog + callback interaction log
    (``InMemoryServiceInteractionStore``) and the admitted
    ``ServiceInteractionActionAdapter``.  The binding layer adds wallet-
    specific grounding of ``service_id`` and session gates before adapter
    invocation.
    """

    adapter: ServiceInteractionActionAdapter
    grounded_service_ids: frozenset[str] = field(default_factory=frozenset)
    surface_id: str = WALLET_SOCIAL_SERVICES_SURFACE
    interaction_surface_id: str = WALLET_INTERACTIONS_SURFACE
    binding_version: str = BINDING_VERSION
    # Wallet-boundary re-check: schedule always requires authenticated session.
    require_auth_for_schedule: bool = True

    @property
    def store(self) -> InMemoryServiceInteractionStore:
        store = self.adapter.store
        if not isinstance(store, InMemoryServiceInteractionStore):
            raise TypeError(
                "wallet service binding requires InMemoryServiceInteractionStore"
            )
        return store

    def with_grounded_services(
        self,
        *service_ids: str,
        replace: bool = False,
    ) -> WalletServiceActionBinding:
        """Return a binding with additional (or replaced) grounded service ids."""

        extra = {sid for sid in (normalize_service_id(s) for s in service_ids) if sid}
        if replace:
            grounded = frozenset(extra)
        else:
            grounded = frozenset(set(self.grounded_service_ids) | extra)
        return WalletServiceActionBinding(
            adapter=self.adapter,
            grounded_service_ids=grounded,
            surface_id=self.surface_id,
            interaction_surface_id=self.interaction_surface_id,
            binding_version=self.binding_version,
            require_auth_for_schedule=self.require_auth_for_schedule,
        )

    def seed_services(self, *records: ServiceDetailRecord) -> None:
        """Seed service catalog rows into the offline fake store."""

        self.store.seed_services(*records)

    def seed_callbacks(self, *records: ServiceCallbackRecord) -> None:
        """Seed callback rows into the offline interaction log."""

        self.store.seed_callbacks(*records)

    def list_services(
        self,
        *,
        tenant_id: str | None = None,
        service_id: str | None = None,
        limit: int = 50,
    ) -> tuple[ServiceDetailRecord, ...]:
        """Direct catalog list for tests/diagnostics (tenant-filtered)."""

        return tuple(
            self.store.list_services(
                tenant_id=tenant_id,
                service_id=service_id,
                limit=limit,
            )
        )

    def list_callbacks(
        self,
        *,
        tenant_id: str,
        service_id: str | None = None,
        limit: int = 50,
    ) -> tuple[ServiceCallbackRecord, ...]:
        """Return interaction-log callback rows for a tenant (offline fake)."""

        if not tenant_id:
            return ()
        return tuple(
            self.store.list_callbacks(
                tenant_id=tenant_id,
                service_id=service_id,
                limit=limit,
            )
        )

    def interaction_log(
        self,
        *,
        tenant_id: str,
        service_id: str | None = None,
        limit: int = 50,
    ) -> tuple[dict[str, Any], ...]:
        """Wallet-shaped interaction log entries from the offline callback store.

        Maps ``ServiceCallbackRecord`` fields onto the product interaction
        model used by ``serviceInteractionService`` (type, channel, status,
        serviceDocId, notes presence) without leaking raw notes.
        """

        rows = self.list_callbacks(
            tenant_id=tenant_id,
            service_id=service_id,
            limit=limit,
        )
        entries: list[dict[str, Any]] = []
        for row in rows:
            entries.append(
                {
                    "interaction_type": row.interaction_type
                    or INTERACTION_TYPE_CALLBACK_REQUESTED,
                    "service_doc_id": row.service_id,
                    "service_id": row.service_id,
                    "tenant_id": row.tenant_id,
                    "channel": row.channel,
                    "status": row.status,
                    "callback_id": row.callback_id,
                    "callback_at": row.callback_at,
                    "client_id": row.client_id,
                    "provider_id": row.provider_id or None,
                    "contact_preference": row.contact_preference or None,
                    "notes_digest": row.notes_digest,
                    "notes_present": bool(row.notes.strip()),
                    "proposal_digest": row.proposal_digest,
                    "created_at_epoch_s": row.created_at_epoch_s,
                    "surface_id": self.interaction_surface_id,
                    "privacy_level": "redacted",
                }
            )
        return tuple(entries)

    def resolve_grounded_services(
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
        return extract_grounded_service_ids(
            self.grounded_service_ids,
            evidence=evidence,
        )

    def _grounding_gate(self, proposal: ActionProposal) -> str | None:
        """Fail closed when service_id is missing or ungrounded for this call.

        The authority-plane adapter re-checks evidence tokens; this wallet
        gate admits either an explicit grounded registry entry or evidence
        tokens (including bare ids and prefixed forms).
        """

        args = dict(proposal.arguments)
        sid = normalize_service_id(args.get("service_id"))
        grounded = self.resolve_grounded_services(proposal)
        return service_grounding_error(
            sid,
            grounded_service_ids=grounded,
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
            receipt_id=f"rcpt-wallet-svc-{uuid.uuid4().hex[:12]}",
            status=ActionStatus.FAILED,
            proposal_id=proposal.proposal_id,
            decision_id=decision.decision_id,
            descriptor_id=proposal.descriptor_id,
            adapter="service_interaction",
            interface_identity=f"wallet-service:{self.surface_id}",
            started_epoch_s=started,
            completed_epoch_s=time.time(),
            error=error,
            metadata={
                "binding_version": self.binding_version,
                "surface_id": self.surface_id,
                "interaction_surface_id": self.interaction_surface_id,
                "layer": "wallet_service_action_binding",
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
            receipt_id=f"rcpt-wallet-svc-{uuid.uuid4().hex[:12]}",
            status=ActionStatus.DENIED,
            proposal_id=proposal.proposal_id,
            decision_id=decision.decision_id,
            descriptor_id=proposal.descriptor_id,
            adapter="service_interaction",
            interface_identity=f"wallet-service:{self.surface_id}",
            started_epoch_s=started,
            completed_epoch_s=time.time(),
            error=error,
            metadata={
                "binding_version": self.binding_version,
                "surface_id": self.surface_id,
                "interaction_surface_id": self.interaction_surface_id,
                "layer": "wallet_service_action_binding",
            },
        )

    def invoke(
        self,
        *,
        proposal: ActionProposal,
        decision: ActionDecision,
        session: WalletServiceSession,
    ) -> ActionReceipt:
        """Invoke the service interaction adapter after wallet gates.

        Returns a failed/denied receipt without store mutation when:

        * decision does not permit execution
        * session tenant mismatches proposal tenant
        * service_id is required and not grounded
        * schedule is attempted without an authenticated session
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
        if logical not in {OPEN_LOGICAL_ACTION, SCHEDULE_LOGICAL_ACTION}:
            return self._failed_receipt(
                proposal=proposal,
                decision=decision,
                error=f"unsupported_logical_action:{logical}",
                started=started,
            )

        # Wallet-boundary auth gate for callback writes (fail closed before I/O).
        if logical == SCHEDULE_LOGICAL_ACTION and self.require_auth_for_schedule:
            if not session.authenticated:
                return self._failed_receipt(
                    proposal=proposal,
                    decision=decision,
                    error="auth_required",
                    started=started,
                )

        gate = self._grounding_gate(proposal)
        if gate is not None:
            return self._failed_receipt(
                proposal=proposal,
                decision=decision,
                error=gate,
                started=started,
            )

        context = session.to_service_context()
        receipt = self.adapter.invoke(
            proposal=proposal,
            decision=decision,
            context=context,
        )
        # Annotate receipts with wallet surface metadata (copy-on-write).
        meta = dict(receipt.metadata)
        meta.setdefault("binding_version", self.binding_version)
        meta.setdefault("surface_id", self.surface_id)
        meta.setdefault("interaction_surface_id", self.interaction_surface_id)
        meta.setdefault("layer", "wallet_service_action_binding")
        if logical == SCHEDULE_LOGICAL_ACTION:
            meta.setdefault(
                "interaction_type", INTERACTION_TYPE_CALLBACK_REQUESTED
            )
        elif logical == OPEN_LOGICAL_ACTION:
            meta.setdefault("interaction_type", INTERACTION_TYPE_VIEWED_SERVICE)
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

    def open_service_detail(
        self,
        *,
        session: WalletServiceSession,
        decision: ActionDecision,
        service_id: str,
        proposal: ActionProposal | None = None,
        provider_id: str | None = None,
        proposal_id: str | None = None,
        evidence: Sequence[str] | None = None,
    ) -> ActionReceipt:
        """Convenience: open a grounded service detail on the wallet surface."""

        args: dict[str, str] = {"service_id": str(service_id)}
        if provider_id is not None:
            args["provider_id"] = str(provider_id)

        if proposal is None:
            proposal = build_service_proposal(
                logical_action=OPEN_LOGICAL_ACTION,
                arguments=args,
                tenant_id=session.tenant_id,
                session_id=session.session_id,
                channel=session.channel,
                evidence=evidence or (f"service_id:{service_id}",),
                proposal_id=proposal_id or f"prop-svc-open-{uuid.uuid4().hex[:12]}",
            )
        return self.invoke(proposal=proposal, decision=decision, session=session)

    def schedule_service_callback(
        self,
        *,
        session: WalletServiceSession,
        decision: ActionDecision,
        service_id: str,
        proposal: ActionProposal | None = None,
        callback_at: str | None = None,
        channel: str = "phone",
        client_id: str | None = None,
        notes: str = "",
        contact_preference: str = "",
        provider_id: str | None = None,
        proposal_id: str | None = None,
        evidence: Sequence[str] | None = None,
    ) -> ActionReceipt:
        """Convenience: schedule a callback into the offline interaction log."""

        args: dict[str, str] = {
            "service_id": str(service_id),
            "channel": channel,
        }
        if callback_at is not None:
            args["callback_at"] = callback_at
        cid = client_id or session.client_id
        if cid:
            args["client_id"] = cid
        if notes:
            args["notes"] = notes
        if contact_preference:
            args["contact_preference"] = contact_preference
        if provider_id is not None:
            args["provider_id"] = str(provider_id)

        if proposal is None:
            proposal = build_service_proposal(
                logical_action=SCHEDULE_LOGICAL_ACTION,
                arguments=args,
                tenant_id=session.tenant_id,
                session_id=session.session_id,
                channel=session.channel,
                evidence=evidence or (f"service_id:{service_id}",),
                proposal_id=proposal_id
                or f"prop-svc-cb-{uuid.uuid4().hex[:12]}",
            )
        return self.invoke(proposal=proposal, decision=decision, session=session)


def build_service_proposal(
    *,
    logical_action: str,
    arguments: Mapping[str, str] | None = None,
    tenant_id: str | None = None,
    session_id: str | None = None,
    channel: str | None = "voice",
    evidence: Sequence[str] = (),
    proposal_id: str | None = None,
    confidence: float = 0.99,
    source: str = "wallet_service_action_binding",
    route: str = WALLET_SERVICE_INTERACTION_SUPPORT_ROUTE,
) -> ActionProposal:
    """Build a catalog-bound service interaction proposal (no executables)."""

    if logical_action == OPEN_LOGICAL_ACTION:
        descriptor_id = OPEN_SERVICE_DETAIL_DESCRIPTOR_ID
    elif logical_action == SCHEDULE_LOGICAL_ACTION:
        descriptor_id = SCHEDULE_SERVICE_CALLBACK_DESCRIPTOR_ID
    else:
        raise ValueError(f"unsupported_logical_action:{logical_action}")

    return ActionProposal(
        proposal_id=proposal_id or f"prop-svc-{uuid.uuid4().hex[:12]}",
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
            "surface_id": WALLET_SOCIAL_SERVICES_SURFACE,
            "interaction_surface_id": WALLET_INTERACTIONS_SURFACE,
            "family": "service_interaction",
        },
    )


def build_permit_decision(
    proposal: ActionProposal,
    *,
    kind: ActionDecisionKind | None = None,
    risk_class: RiskClass | None = None,
    decision_id: str | None = None,
    reason: str = "wallet_service_permit",
) -> ActionDecision:
    """Build a permitting decision bound to ``proposal`` digests."""

    if kind is None:
        if proposal.logical_action == OPEN_LOGICAL_ACTION:
            kind = ActionDecisionKind.PERMIT_READ
        else:
            kind = ActionDecisionKind.PERMIT_EXECUTE
    if risk_class is None:
        risk_class = (
            RiskClass.READ
            if proposal.logical_action == OPEN_LOGICAL_ACTION
            else RiskClass.WRITE
        )
    return ActionDecision(
        decision_id=decision_id or f"dec-svc-{uuid.uuid4().hex[:12]}",
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


def build_wallet_service_binding(
    *,
    grounded_service_ids: Iterable[str] | None = None,
    store: InMemoryServiceInteractionStore | None = None,
    sandbox: ServiceInteractionSandboxPolicy | None = None,
    registrations: Sequence[ServiceInteractionActionRegistration] | None = None,
    surface_id: str = WALLET_SOCIAL_SERVICES_SURFACE,
    interaction_surface_id: str = WALLET_INTERACTIONS_SURFACE,
    seed_services: Sequence[ServiceDetailRecord] | None = None,
    seed_callbacks: Sequence[ServiceCallbackRecord] | None = None,
    require_auth_for_schedule: bool = True,
) -> WalletServiceActionBinding:
    """Construct the wallet service action binding with optional fake seed data."""

    interaction_store = store or InMemoryServiceInteractionStore()
    if seed_services:
        interaction_store.seed_services(*seed_services)
    if seed_callbacks:
        interaction_store.seed_callbacks(*seed_callbacks)

    if registrations is None:
        if sandbox is None:
            regs = default_service_interaction_registrations()
        else:
            regs = (
                ServiceInteractionActionRegistration(
                    descriptor_id=OPEN_SERVICE_DETAIL_DESCRIPTOR_ID,
                    logical_action=OPEN_LOGICAL_ACTION,
                    sandbox=sandbox,
                ),
                ServiceInteractionActionRegistration(
                    descriptor_id=SCHEDULE_SERVICE_CALLBACK_DESCRIPTOR_ID,
                    logical_action=SCHEDULE_LOGICAL_ACTION,
                    sandbox=sandbox,
                ),
            )
    else:
        regs = tuple(registrations)

    adapter = ServiceInteractionActionAdapter(regs, store=interaction_store)
    grounded = extract_grounded_service_ids(grounded_service_ids)
    return WalletServiceActionBinding(
        adapter=adapter,
        grounded_service_ids=grounded,
        surface_id=surface_id,
        interaction_surface_id=interaction_surface_id,
        require_auth_for_schedule=require_auth_for_schedule,
    )


def seed_demo_service_catalog(
    store: InMemoryServiceInteractionStore,
    *,
    tenant_id: str = "tenant-a",
    other_tenant_id: str = "tenant-b",
    service_id: str = "svc-housing-211-demo",
) -> None:
    """Seed a small multi-tenant fake service catalog for offline acceptance tests."""

    store.seed_services(
        ServiceDetailRecord(
            service_id=service_id,
            title="Emergency Housing Intake",
            provider_name="Community Shelter Network",
            program_name="211 Housing",
            summary="SECRET eligibility notes — do not leak in receipts by default",
            status="available",
        ),
        ServiceDetailRecord(
            service_id="svc-food-pantry-demo",
            title="Neighborhood Food Pantry",
            provider_name="Rose City Food Bank",
            program_name="211 Food",
            summary="Walk-in hours and ID requirements for pantry access.",
            status="available",
            tenant_id=tenant_id,
        ),
        ServiceDetailRecord(
            service_id="svc-other-tenant-only",
            title="Other tenant secret service",
            provider_name="Hidden Provider",
            program_name="Internal",
            summary="LEAK-ME cross-tenant summary",
            tenant_id=other_tenant_id,
            status="available",
        ),
    )


def binding_public_summary(receipt: ActionReceipt) -> dict[str, Any]:
    """Compact wire-safe summary of a service interaction receipt for wallet clients."""

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
        "interaction_surface_id": (receipt.metadata or {}).get(
            "interaction_surface_id"
        ),
        "interaction_type": (receipt.metadata or {}).get("interaction_type"),
        "binding_version": (receipt.metadata or {}).get("binding_version"),
    }


# Re-export adapter primitives commonly needed by tests without deep imports.
__all__ = [
    "BINDING_VERSION",
    "INTERACTION_TYPE_CALLBACK_REQUESTED",
    "INTERACTION_TYPE_VIEWED_SERVICE",
    "OPEN_LOGICAL",
    "OPEN_LOGICAL_ACTION",
    "OPEN_SERVICE_DETAIL_DESCRIPTOR_ID",
    "SCHEDULE_LOGICAL",
    "SCHEDULE_LOGICAL_ACTION",
    "SCHEDULE_SERVICE_CALLBACK_DESCRIPTOR_ID",
    "WALLET_INTERACTIONS_SURFACE",
    "WALLET_SERVICE_INTERACTION_SUPPORT_ROUTE",
    "WALLET_SOCIAL_SERVICES_SURFACE",
    "WalletServiceActionBinding",
    "WalletServiceSession",
    "binding_public_summary",
    "build_permit_decision",
    "build_service_proposal",
    "build_wallet_service_binding",
    "extract_grounded_service_ids",
    "is_service_id_grounded",
    "normalize_service_id",
    "seed_demo_service_catalog",
    "service_grounding_error",
]
