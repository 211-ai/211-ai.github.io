"""Wallet binding: navigationTools/registry surfaces as admitted app backends.

Binds the pilot logical actions ``open_app_surface`` and
``open_wallet_documents`` to the wallet UI navigation allowlist (the same
route set owned by ``navigationTools`` / ``surfaceRegistry``).

Safety rules (fail closed):

* Only allowlisted surfaces from the navigation registry may be opened
* Non-allowlisted routes deny without mutating surface state
* Adapter execution requires a permitting ``ActionDecision`` bound to the
  proposal (server permit)
* Receipts never carry private filesystem paths, shell locators, or raw
  absolute paths
* Offline fake surface API only — no network, shell, or browser side effects
  from this binding

Importing this module starts no processes and loads no credentials.
"""

from __future__ import annotations

import re
import time
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Final, Protocol

from ipfs_accelerate_py.action_runtime.contracts import (
    ActionDecision,
    ActionDecisionKind,
    ActionProposal,
    ActionReceipt,
    ActionStatus,
    RiskClass,
    content_digest,
)

# Stable pilot descriptor ids (must match catalog_211ai python adapters).
OPEN_APP_SURFACE_DESCRIPTOR_ID: Final = "voice.python.open_app_surface.v1"
OPEN_WALLET_DOCUMENTS_DESCRIPTOR_ID: Final = (
    "voice.python.open_wallet_documents.v1"
)

OPEN_APP_SURFACE_LOGICAL: Final = "open_app_surface"
OPEN_WALLET_DOCUMENTS_LOGICAL: Final = "open_wallet_documents"

_ALLOWED_LOGICAL_ACTIONS: Final = frozenset(
    {OPEN_APP_SURFACE_LOGICAL, OPEN_WALLET_DOCUMENTS_LOGICAL}
)

# Wallet documents map to the navigationTools "uploads" surface (Wallet).
WALLET_DOCUMENTS_SURFACE: Final = "uploads"
WALLET_APP_SUPPORT_ROUTE: Final = "app_surface_navigation"
WALLET_DOCS_SUPPORT_ROUTE: Final = "wallet_document_support"

BINDING_VERSION: Final = "1.0"

# Route ids from surfaceRegistry / navigationTools / appRoutes (+ audit).
# Keep in lockstep with wallet_interface/ui navigation allowlist — fail closed
# for anything outside this set.
NAVIGATION_SURFACE_IDS: Final[frozenset[str]] = frozenset(
    {
        "home",
        "register",
        "check-in",
        "calendar",
        "messages",
        "contacts",
        "sharing-rules",
        "uploads",
        "settings",
        "social-services",
        "interactions",
        "shelter",
        "provider-clients",
        "provider-cases",
        "provider-messages",
        "provider-analytics",
        "provider-proofs",
        "provider-operations",
        "recipient-access",
        "benefits-protection",
        "analytics",
        "proof-center",
        "exports",
        "security",
        "audit",
    }
)

NAVIGATION_SURFACE_LABELS: Final[Mapping[str, str]] = {
    "home": "Home",
    "register": "Register",
    "check-in": "Check in",
    "calendar": "Calendar",
    "messages": "Messages",
    "contacts": "Contacts",
    "sharing-rules": "Sharing",
    "uploads": "Wallet",
    "settings": "Settings",
    "social-services": "Services",
    "interactions": "Interactions",
    "shelter": "Provider overview",
    "provider-clients": "Clients served",
    "provider-cases": "Case management",
    "provider-messages": "Client messages",
    "provider-analytics": "Staff analytics",
    "provider-proofs": "ZK certificates",
    "provider-operations": "Staff operations",
    "recipient-access": "Who can see info",
    "benefits-protection": "Benefits",
    "analytics": "Analytics",
    "proof-center": "Proofs",
    "exports": "Exports",
    "security": "Security",
    "audit": "Audit",
}

# Aliases mirrored from navigationTools.extraRouteAliases (normalized keys).
# Used only to resolve *to* an allowlisted surface id — never to widen the set.
_SURFACE_ALIASES: Final[Mapping[str, tuple[str, ...]]] = {
    "home": ("dashboard", "start", "today", "safety plan"),
    "register": ("registration", "profile", "intake"),
    "check-in": ("reminder", "reminders", "checkins"),
    "calendar": (
        "appointments",
        "appointment",
        "schedule",
        "scheduled services",
        "service schedule",
    ),
    "messages": (
        "inbox",
        "client messages",
        "service staff messages",
        "notifications",
    ),
    "contacts": ("people", "recipients"),
    "sharing-rules": ("sharing rules", "disclosure", "permissions"),
    "uploads": (
        "wallet",
        "documents",
        "files",
        "records",
        "export",
        "import",
        "bundle",
        "bundles",
        "share proofs",
        "wallet documents",
    ),
    "settings": (
        "account settings",
        "profile settings",
        "preferences",
        "personal information",
    ),
    "social-services": (
        "service",
        "services",
        "service navigator",
        "211",
        "211 services",
    ),
    "interactions": (
        "interaction history",
        "service history",
        "service interactions",
        "timeline",
    ),
    "shelter": (
        "provider overview",
        "provider portal",
        "shelter staff",
        "shelters",
        "shelter services",
        "beds",
    ),
    "provider-clients": (
        "served clients",
        "clients served",
        "provider clients",
        "case list",
    ),
    "provider-cases": (
        "case management",
        "cases",
        "caseload",
        "service cases",
        "eligibility cases",
    ),
    "provider-messages": (
        "provider messages",
        "send client messages",
        "client notifications",
    ),
    "provider-analytics": (
        "staff analytics",
        "provider analytics",
        "staff reports",
    ),
    "provider-proofs": (
        "zk certificates",
        "zero knowledge certificates",
        "provider proofs",
        "proof certificates",
    ),
    "provider-operations": (
        "staff operations",
        "provider operations",
        "create user account",
        "contact requests",
    ),
    "recipient-access": (
        "recipient access",
        "access requests",
        "who can see",
        "requests",
    ),
    "benefits-protection": (
        "benefits",
        "benefits protection",
        "public benefits",
    ),
    "analytics": ("reports", "group facts"),
    "proof-center": (
        "proof center",
        "proofs",
        "proof",
        "verification",
        "verifications",
    ),
    "exports": ("export", "sharing bundle", "bundle", "download"),
    "security": ("wallet security", "privacy", "security settings"),
    "audit": ("history", "wallet audit", "activity log", "audit log"),
}

# Argument slots admitted for each logical action (fail closed on extras).
OPEN_APP_ARGUMENT_SLOTS: Final = frozenset(
    {"surface_id", "route", "surface", "target", "label"}
)
OPEN_DOCS_ARGUMENT_SLOTS: Final = frozenset(
    {"document_id", "record_id", "surface_id", "route", "surface", "target"}
)

# Keys that must never appear (shell / filesystem / locator smuggling).
_FORBIDDEN_ARGUMENT_KEYS: Final = frozenset(
    {
        "command",
        "argv",
        "executable",
        "cwd",
        "env",
        "shell",
        "import_path",
        "url",
        "path",
        "filepath",
        "file_path",
        "filesystem_path",
        "absolute_path",
        "home",
        "binary",
        "module",
        "entrypoint",
        "webhook",
        "host",
        "port",
    }
)

_SAFE_ID_RE: Final = re.compile(r"^[A-Za-z0-9_.:@+/-]{1,128}$")
# Private path markers that must never appear in public receipts.
_PRIVATE_PATH_MARKERS: Final = (
    "/home/",
    "/Users/",
    "C:\\",
    "c:\\",
    "/var/",
    "/tmp/",
    "file://",
    "~/",
)


def _text(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def normalize_surface_text(value: object | None) -> str | None:
    """Normalize free-text surface/route input the way navigationTools does."""

    text = _text(value)
    if text is None:
        return None
    cleaned = text.lower().replace("_", " ").replace("-", " ")
    cleaned = " ".join(cleaned.split())
    return cleaned or None


def is_allowlisted_surface(surface_id: object | None) -> bool:
    """Return whether ``surface_id`` is in the navigationTools registry set."""

    sid = _text(surface_id)
    if sid is None:
        return False
    return sid in NAVIGATION_SURFACE_IDS


def get_surface_label(surface_id: str) -> str:
    """Return the registry label for an allowlisted surface."""

    return NAVIGATION_SURFACE_LABELS.get(surface_id, surface_id)


def resolve_navigation_surface(value: object | None) -> str | None:
    """Resolve a surface id or navigationTools alias to an allowlisted route.

    Returns ``None`` when the input does not map to the registry (fail closed).
    """

    raw = _text(value)
    if raw is None:
        return None
    # Exact route id match (including hyphenated ids).
    if raw in NAVIGATION_SURFACE_IDS:
        return raw

    normalized = normalize_surface_text(raw)
    if normalized is None:
        return None

    # Exact normalized match against route id / label / aliases.
    for surface_id in sorted(NAVIGATION_SURFACE_IDS):
        candidates = {
            normalize_surface_text(surface_id),
            normalize_surface_text(get_surface_label(surface_id)),
        }
        for alias in _SURFACE_ALIASES.get(surface_id, ()):
            candidates.add(normalize_surface_text(alias))
        if normalized in candidates:
            return surface_id
    return None


def surface_allowlist_error(surface_id: object | None) -> str | None:
    """Return a fail-closed error code when surface is missing or not allowlisted."""

    raw = _text(surface_id)
    if not raw:
        return "surface_id_required"
    resolved = resolve_navigation_surface(raw)
    if resolved is None:
        return "surface_not_allowlisted"
    return None


@dataclass(frozen=True)
class OpenedSurfaceRecord:
    """Record of a surface open performed by the fake surface API."""

    open_id: str
    surface_id: str
    label: str
    logical_action: str
    tenant_id: str
    session_id: str | None
    opened_at_epoch_s: float
    document_id: str | None = None
    # Public-only metadata; never absolute filesystem paths.
    metadata: Mapping[str, str] = field(default_factory=dict)


class AppSurfaceApi(Protocol):
    """Backend protocol for opening UI surfaces (fake or product)."""

    def open_surface(
        self,
        *,
        surface_id: str,
        logical_action: str,
        tenant_id: str,
        session_id: str | None = None,
        document_id: str | None = None,
        metadata: Mapping[str, str] | None = None,
    ) -> OpenedSurfaceRecord: ...

    def list_opened(
        self,
        *,
        tenant_id: str | None = None,
        limit: int = 50,
    ) -> Sequence[OpenedSurfaceRecord]: ...

    @property
    def active_surface_id(self) -> str | None: ...


@dataclass
class InMemoryAppSurfaceApi:
    """Offline fake surface API used as the admitted app-adapter backend.

    Tracks opened surfaces without touching the browser, filesystem, or shell.
    """

    _opened: list[OpenedSurfaceRecord] = field(default_factory=list)
    _active_surface_id: str | None = None
    _clock: Any = time.time

    @property
    def active_surface_id(self) -> str | None:
        return self._active_surface_id

    def open_surface(
        self,
        *,
        surface_id: str,
        logical_action: str,
        tenant_id: str,
        session_id: str | None = None,
        document_id: str | None = None,
        metadata: Mapping[str, str] | None = None,
    ) -> OpenedSurfaceRecord:
        if not is_allowlisted_surface(surface_id):
            raise ValueError("surface_not_allowlisted")
        if not tenant_id:
            raise ValueError("tenant_required")
        record = OpenedSurfaceRecord(
            open_id=f"open-{uuid.uuid4().hex[:16]}",
            surface_id=surface_id,
            label=get_surface_label(surface_id),
            logical_action=logical_action,
            tenant_id=tenant_id,
            session_id=session_id,
            opened_at_epoch_s=float(self._clock()),
            document_id=document_id,
            metadata=dict(metadata or {}),
        )
        self._opened.append(record)
        self._active_surface_id = surface_id
        return record

    def list_opened(
        self,
        *,
        tenant_id: str | None = None,
        limit: int = 50,
    ) -> Sequence[OpenedSurfaceRecord]:
        rows = self._opened
        if tenant_id is not None:
            rows = [r for r in rows if r.tenant_id == tenant_id]
        return tuple(rows[-max(0, limit) :]) if limit else ()

    def clear(self) -> None:
        self._opened.clear()
        self._active_surface_id = None


@dataclass(frozen=True)
class WalletAppSession:
    """Caller session facts re-checked at the wallet binding boundary."""

    tenant_id: str
    authenticated: bool = False
    confirmed: bool = False
    client_id: str | None = None
    session_id: str | None = None
    channel: str = "voice"


@dataclass
class WalletAppActionBinding:
    """Deployment binding: pilot app descriptors ↔ navigationTools surfaces.

    Holds an offline fake surface API (``InMemoryAppSurfaceApi``) that only
    admits surfaces from the navigation registry.  The binding layer enforces
    server permit + allowlist before any open.
    """

    surface_api: InMemoryAppSurfaceApi
    allowlist: frozenset[str] = field(default_factory=lambda: NAVIGATION_SURFACE_IDS)
    binding_version: str = BINDING_VERSION
    # Adapter-boundary re-check: pilot reads require explicit confirm.
    require_confirm: bool = True

    def is_allowlisted(self, surface_id: object | None) -> bool:
        resolved = resolve_navigation_surface(surface_id)
        if resolved is None:
            return False
        return resolved in self.allowlist

    def list_opened(
        self,
        *,
        tenant_id: str | None = None,
        limit: int = 50,
    ) -> tuple[OpenedSurfaceRecord, ...]:
        return tuple(self.surface_api.list_opened(tenant_id=tenant_id, limit=limit))

    @property
    def active_surface_id(self) -> str | None:
        return self.surface_api.active_surface_id

    def _failed_receipt(
        self,
        *,
        proposal: ActionProposal,
        decision: ActionDecision,
        error: str,
        started: float,
        public_result: Mapping[str, str] | None = None,
    ) -> ActionReceipt:
        return ActionReceipt(
            receipt_id=f"rcpt-wallet-app-{uuid.uuid4().hex[:12]}",
            status=ActionStatus.FAILED,
            proposal_id=proposal.proposal_id,
            decision_id=decision.decision_id,
            descriptor_id=proposal.descriptor_id,
            adapter="app_tool",
            interface_identity="wallet-app:navigation",
            started_epoch_s=started,
            completed_epoch_s=time.time(),
            error=error,
            public_result=dict(public_result or {}),
            metadata={
                "binding_version": self.binding_version,
                "layer": "wallet_app_binding",
            },
        )

    def _denied_receipt(
        self,
        *,
        proposal: ActionProposal,
        decision: ActionDecision,
        error: str,
        started: float,
        public_result: Mapping[str, str] | None = None,
    ) -> ActionReceipt:
        return ActionReceipt(
            receipt_id=f"rcpt-wallet-app-{uuid.uuid4().hex[:12]}",
            status=ActionStatus.DENIED,
            proposal_id=proposal.proposal_id,
            decision_id=decision.decision_id,
            descriptor_id=proposal.descriptor_id,
            adapter="app_tool",
            interface_identity="wallet-app:navigation",
            started_epoch_s=started,
            completed_epoch_s=time.time(),
            error=error,
            public_result=dict(public_result or {}),
            metadata={
                "binding_version": self.binding_version,
                "layer": "wallet_app_binding",
            },
        )

    def _succeeded_receipt(
        self,
        *,
        proposal: ActionProposal,
        decision: ActionDecision,
        started: float,
        record: OpenedSurfaceRecord,
    ) -> ActionReceipt:
        public_result: dict[str, str] = {
            "ok": "true",
            "surface_id": record.surface_id,
            "label": record.label,
            "logical_action": record.logical_action,
            "open_id": record.open_id,
            "tenant_id": record.tenant_id,
        }
        if record.document_id:
            public_result["document_id"] = record.document_id
        # Defense: never leak private path markers into receipts.
        for key, value in list(public_result.items()):
            if _contains_private_path(value):
                public_result[key] = "[redacted_path]"
        return ActionReceipt(
            receipt_id=f"rcpt-wallet-app-{uuid.uuid4().hex[:12]}",
            status=ActionStatus.SUCCEEDED,
            proposal_id=proposal.proposal_id,
            decision_id=decision.decision_id,
            descriptor_id=proposal.descriptor_id,
            adapter="app_tool",
            interface_identity=f"wallet-app:{record.surface_id}",
            started_epoch_s=started,
            completed_epoch_s=time.time(),
            exit_code=0,
            public_result=public_result,
            metadata={
                "binding_version": self.binding_version,
                "surface_id": record.surface_id,
                "layer": "wallet_app_binding",
            },
        )

    def _reject_forbidden_arguments(
        self, proposal: ActionProposal
    ) -> str | None:
        args = dict(proposal.arguments)
        forbidden = sorted(
            k
            for k in args
            if k.lower() in _FORBIDDEN_ARGUMENT_KEYS
            or k.lower().endswith("_path")
            or k.lower().endswith("_file")
        )
        if forbidden:
            return f"forbidden_argument_slots:{','.join(forbidden)}"
        for key, value in args.items():
            if _contains_private_path(value):
                return f"private_path_rejected:{key}"
            if _looks_like_shell(value):
                return f"shell_locator_rejected:{key}"
        return None

    def _resolve_target_surface(
        self,
        proposal: ActionProposal,
    ) -> tuple[str | None, str | None, str | None]:
        """Return (surface_id, document_id, error)."""

        args = dict(proposal.arguments)
        logical = proposal.logical_action

        if logical == OPEN_WALLET_DOCUMENTS_LOGICAL:
            # Wallet documents always open the uploads surface.
            # Optional explicit surface must still resolve to uploads.
            raw_surface = (
                args.get("surface_id")
                or args.get("route")
                or args.get("surface")
                or args.get("target")
            )
            if raw_surface:
                resolved = resolve_navigation_surface(raw_surface)
                if resolved is None:
                    return None, None, "surface_not_allowlisted"
                if resolved != WALLET_DOCUMENTS_SURFACE:
                    return None, None, "wallet_documents_requires_uploads_surface"
            document_id = _text(args.get("document_id") or args.get("record_id"))
            if document_id is not None:
                if not _SAFE_ID_RE.match(document_id) or ".." in document_id:
                    return None, None, "document_id_invalid"
                if _contains_private_path(document_id):
                    return None, None, "private_path_rejected:document_id"
            return WALLET_DOCUMENTS_SURFACE, document_id, None

        if logical == OPEN_APP_SURFACE_LOGICAL:
            raw_surface = (
                args.get("surface_id")
                or args.get("route")
                or args.get("surface")
                or args.get("target")
            )
            if not raw_surface:
                return None, None, "surface_id_required"
            resolved = resolve_navigation_surface(raw_surface)
            if resolved is None or resolved not in self.allowlist:
                return None, None, "surface_not_allowlisted"
            return resolved, None, None

        return None, None, f"unsupported_logical_action:{logical}"

    def invoke(
        self,
        *,
        proposal: ActionProposal,
        decision: ActionDecision,
        session: WalletAppSession,
    ) -> ActionReceipt:
        """Invoke open_app_surface / open_wallet_documents after wallet gates.

        Returns a failed/denied receipt without surface mutation when:

        * decision does not permit execution
        * session tenant is missing or mismatches proposal tenant
        * surface is not on the navigationTools allowlist
        * arguments smuggle shell/filesystem locators
        * confirmation is required and session is unconfirmed
        """

        started = time.time()

        if not decision.permits_execution:
            return self._denied_receipt(
                proposal=proposal,
                decision=decision,
                error=f"decision_does_not_permit_execution:{decision.kind.value}",
                started=started,
            )

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
        if logical not in _ALLOWED_LOGICAL_ACTIONS:
            return self._failed_receipt(
                proposal=proposal,
                decision=decision,
                error=f"unsupported_logical_action:{logical}",
                started=started,
            )

        # Descriptor binding must match the logical action.
        expected_descriptor = (
            OPEN_APP_SURFACE_DESCRIPTOR_ID
            if logical == OPEN_APP_SURFACE_LOGICAL
            else OPEN_WALLET_DOCUMENTS_DESCRIPTOR_ID
        )
        if proposal.descriptor_id != expected_descriptor:
            return self._failed_receipt(
                proposal=proposal,
                decision=decision,
                error="descriptor_logical_action_mismatch",
                started=started,
            )

        # Pilot read actions use PERMIT_READ (PERMIT_EXECUTE also accepted).
        if decision.kind not in {
            ActionDecisionKind.PERMIT_READ,
            ActionDecisionKind.PERMIT_EXECUTE,
        }:
            return self._denied_receipt(
                proposal=proposal,
                decision=decision,
                error=f"decision_does_not_permit_execution:{decision.kind.value}",
                started=started,
            )

        if self.require_confirm and not session.confirmed:
            return self._failed_receipt(
                proposal=proposal,
                decision=decision,
                error="confirmation_required",
                started=started,
            )

        forbidden = self._reject_forbidden_arguments(proposal)
        if forbidden is not None:
            return self._failed_receipt(
                proposal=proposal,
                decision=decision,
                error=forbidden,
                started=started,
            )

        # Fail closed on unknown argument slots.
        allowed_slots = (
            OPEN_APP_ARGUMENT_SLOTS
            if logical == OPEN_APP_SURFACE_LOGICAL
            else OPEN_DOCS_ARGUMENT_SLOTS
        )
        extras = sorted(k for k in proposal.arguments if k not in allowed_slots)
        if extras:
            return self._failed_receipt(
                proposal=proposal,
                decision=decision,
                error=f"unknown_argument_slots:{','.join(extras)}",
                started=started,
            )

        surface_id, document_id, resolve_error = self._resolve_target_surface(proposal)
        if resolve_error is not None:
            # Non-allowlisted routes fail closed as DENIED (policy-shaped).
            if resolve_error == "surface_not_allowlisted":
                return self._denied_receipt(
                    proposal=proposal,
                    decision=decision,
                    error=resolve_error,
                    started=started,
                    public_result={"ok": "false", "error": resolve_error},
                )
            return self._failed_receipt(
                proposal=proposal,
                decision=decision,
                error=resolve_error,
                started=started,
            )
        assert surface_id is not None

        try:
            record = self.surface_api.open_surface(
                surface_id=surface_id,
                logical_action=logical,
                tenant_id=session_tenant,
                session_id=session.session_id or proposal.session_id,
                document_id=document_id,
                metadata={
                    "source": "wallet_app_binding",
                    "channel": session.channel or proposal.channel or "voice",
                },
            )
        except ValueError as exc:
            code = str(exc) or "surface_open_rejected"
            if code == "surface_not_allowlisted":
                return self._denied_receipt(
                    proposal=proposal,
                    decision=decision,
                    error=code,
                    started=started,
                )
            return self._failed_receipt(
                proposal=proposal,
                decision=decision,
                error=code,
                started=started,
            )

        return self._succeeded_receipt(
            proposal=proposal,
            decision=decision,
            started=started,
            record=record,
        )

    def open_app_surface(
        self,
        *,
        session: WalletAppSession,
        decision: ActionDecision,
        surface_id: str,
        proposal: ActionProposal | None = None,
        proposal_id: str | None = None,
        evidence: Sequence[str] | None = None,
    ) -> ActionReceipt:
        """Convenience: open an allowlisted navigation surface under permit."""

        if proposal is None:
            proposal = build_app_proposal(
                logical_action=OPEN_APP_SURFACE_LOGICAL,
                arguments={"surface_id": surface_id},
                tenant_id=session.tenant_id,
                session_id=session.session_id,
                channel=session.channel,
                evidence=evidence or (),
                proposal_id=proposal_id
                or f"prop-app-open-{uuid.uuid4().hex[:12]}",
            )
        return self.invoke(proposal=proposal, decision=decision, session=session)

    def open_wallet_documents(
        self,
        *,
        session: WalletAppSession,
        decision: ActionDecision,
        proposal: ActionProposal | None = None,
        document_id: str | None = None,
        proposal_id: str | None = None,
        evidence: Sequence[str] | None = None,
    ) -> ActionReceipt:
        """Convenience: open the wallet documents (uploads) surface under permit."""

        args: dict[str, str] = {"surface_id": WALLET_DOCUMENTS_SURFACE}
        if document_id is not None:
            args["document_id"] = document_id
        if proposal is None:
            proposal = build_app_proposal(
                logical_action=OPEN_WALLET_DOCUMENTS_LOGICAL,
                arguments=args,
                tenant_id=session.tenant_id,
                session_id=session.session_id,
                channel=session.channel,
                evidence=evidence or (),
                proposal_id=proposal_id
                or f"prop-docs-open-{uuid.uuid4().hex[:12]}",
            )
        return self.invoke(proposal=proposal, decision=decision, session=session)


def _contains_private_path(value: str) -> bool:
    if not value:
        return False
    if any(marker in value for marker in _PRIVATE_PATH_MARKERS):
        return True
    # Absolute POSIX path that is not a relative surface id.
    if value.startswith("/") and not value.startswith("//"):
        # Allow pure surface-like ids that begin with / only if short? No —
        # absolute paths are rejected.
        return True
    return False


def _looks_like_shell(value: str) -> bool:
    if not value:
        return False
    lowered = value.lower()
    if lowered in {"/bin/sh", "/bin/bash", "cmd.exe", "powershell"}:
        return True
    if any(token in value for token in (";", "&&", "|", "`", "$(")):
        return True
    return False


def build_app_proposal(
    *,
    logical_action: str,
    arguments: Mapping[str, str] | None = None,
    tenant_id: str | None = None,
    session_id: str | None = None,
    channel: str | None = "voice",
    evidence: Sequence[str] = (),
    proposal_id: str | None = None,
    confidence: float = 0.99,
    source: str = "wallet_app_binding",
    route: str | None = None,
) -> ActionProposal:
    """Build a catalog-bound app-surface proposal (no executables / paths)."""

    if logical_action == OPEN_APP_SURFACE_LOGICAL:
        descriptor_id = OPEN_APP_SURFACE_DESCRIPTOR_ID
        default_route = WALLET_APP_SUPPORT_ROUTE
    elif logical_action == OPEN_WALLET_DOCUMENTS_LOGICAL:
        descriptor_id = OPEN_WALLET_DOCUMENTS_DESCRIPTOR_ID
        default_route = WALLET_DOCS_SUPPORT_ROUTE
    else:
        raise ValueError(f"unsupported_logical_action:{logical_action}")

    return ActionProposal(
        proposal_id=proposal_id or f"prop-app-{uuid.uuid4().hex[:12]}",
        descriptor_id=descriptor_id,
        logical_action=logical_action,
        arguments=dict(arguments or {}),
        route=route or default_route,
        source=source,
        confidence=confidence,
        tenant_id=tenant_id,
        session_id=session_id,
        channel=channel,
        evidence=tuple(evidence),
        metadata={
            "family": "app_surface"
            if logical_action == OPEN_APP_SURFACE_LOGICAL
            else "wallet_documents",
            "surface_registry": "navigationTools",
        },
    )


def build_permit_decision(
    proposal: ActionProposal,
    *,
    kind: ActionDecisionKind | None = None,
    risk_class: RiskClass | None = None,
    decision_id: str | None = None,
    reason: str = "wallet_app_permit",
) -> ActionDecision:
    """Build a permitting decision bound to ``proposal`` digests."""

    if kind is None:
        kind = ActionDecisionKind.PERMIT_READ
    if risk_class is None:
        risk_class = RiskClass.READ
    return ActionDecision(
        decision_id=decision_id or f"dec-app-{uuid.uuid4().hex[:12]}",
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


def build_wallet_app_binding(
    *,
    surface_api: InMemoryAppSurfaceApi | None = None,
    allowlist: Sequence[str] | frozenset[str] | None = None,
    require_confirm: bool = True,
) -> WalletAppActionBinding:
    """Construct the wallet app binding with the navigationTools allowlist."""

    if allowlist is None:
        surfaces = NAVIGATION_SURFACE_IDS
    else:
        # Never admit surfaces outside the registry, even if caller widens.
        surfaces = frozenset(s for s in allowlist if s in NAVIGATION_SURFACE_IDS)
        if not surfaces:
            surfaces = NAVIGATION_SURFACE_IDS
    return WalletAppActionBinding(
        surface_api=surface_api or InMemoryAppSurfaceApi(),
        allowlist=frozenset(surfaces),
        require_confirm=require_confirm,
    )


def list_navigation_surfaces() -> tuple[dict[str, str], ...]:
    """Return sorted registry entries ``{surface_id, label}`` for diagnostics."""

    return tuple(
        {"surface_id": sid, "label": get_surface_label(sid)}
        for sid in sorted(NAVIGATION_SURFACE_IDS)
    )


def binding_public_summary(receipt: ActionReceipt) -> dict[str, Any]:
    """Compact wire-safe summary of an app-surface receipt for wallet clients."""

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
        "surface_id": (receipt.metadata or {}).get("surface_id")
        or (receipt.public_result or {}).get("surface_id"),
        "binding_version": (receipt.metadata or {}).get("binding_version"),
    }


__all__ = [
    "BINDING_VERSION",
    "NAVIGATION_SURFACE_IDS",
    "NAVIGATION_SURFACE_LABELS",
    "OPEN_APP_ARGUMENT_SLOTS",
    "OPEN_APP_SURFACE_DESCRIPTOR_ID",
    "OPEN_APP_SURFACE_LOGICAL",
    "OPEN_DOCS_ARGUMENT_SLOTS",
    "OPEN_WALLET_DOCUMENTS_DESCRIPTOR_ID",
    "OPEN_WALLET_DOCUMENTS_LOGICAL",
    "WALLET_APP_SUPPORT_ROUTE",
    "WALLET_DOCUMENTS_SURFACE",
    "WALLET_DOCS_SUPPORT_ROUTE",
    "InMemoryAppSurfaceApi",
    "OpenedSurfaceRecord",
    "WalletAppActionBinding",
    "WalletAppSession",
    "binding_public_summary",
    "build_app_proposal",
    "build_permit_decision",
    "build_wallet_app_binding",
    "get_surface_label",
    "is_allowlisted_surface",
    "list_navigation_surfaces",
    "normalize_surface_text",
    "resolve_navigation_surface",
    "surface_allowlist_error",
]
