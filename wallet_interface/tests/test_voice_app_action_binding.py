"""Acceptance tests for wallet app action binding (VOICE-ACTION-014).

Criteria:

* Allowlisted surfaces from navigationTools/registry can be opened after
  server permit
* Non-allowlisted routes fail closed
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LOCAL_IPFS_ACCELERATE = REPO_ROOT / "ipfs_accelerate_py"
for path in (str(REPO_ROOT), str(LOCAL_IPFS_ACCELERATE)):
    if path not in sys.path:
        sys.path.insert(0, path)

from ipfs_accelerate_py.action_runtime.contracts import (  # noqa: E402
    ActionDecision,
    ActionDecisionKind,
    ActionStatus,
    RiskClass,
)
from wallet_interface.helpers._voice_app_action_binding import (  # noqa: E402
    NAVIGATION_SURFACE_IDS,
    OPEN_APP_SURFACE_DESCRIPTOR_ID,
    OPEN_APP_SURFACE_LOGICAL,
    OPEN_WALLET_DOCUMENTS_DESCRIPTOR_ID,
    OPEN_WALLET_DOCUMENTS_LOGICAL,
    WALLET_APP_SUPPORT_ROUTE,
    WALLET_DOCUMENTS_SURFACE,
    WALLET_DOCS_SUPPORT_ROUTE,
    InMemoryAppSurfaceApi,
    WalletAppSession,
    build_app_proposal,
    build_permit_decision,
    build_wallet_app_binding,
    is_allowlisted_surface,
    list_navigation_surfaces,
    resolve_navigation_surface,
    surface_allowlist_error,
)


def _session(
    *,
    tenant_id: str = "tenant-a",
    confirmed: bool = True,
    authenticated: bool = True,
    client_id: str = "client-abby",
) -> WalletAppSession:
    return WalletAppSession(
        tenant_id=tenant_id,
        authenticated=authenticated,
        confirmed=confirmed,
        client_id=client_id,
        session_id="sess-app-test-1",
        channel="voice",
    )


def _binding(*, require_confirm: bool = True) -> object:
    return build_wallet_app_binding(require_confirm=require_confirm)


# ── registry / allowlist helpers ─────────────────────────────────────────────


def test_navigation_registry_covers_navigation_tools_routes() -> None:
    """Allowlist matches surfaceRegistry / navigationTools route set."""

    expected = {
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
    assert set(NAVIGATION_SURFACE_IDS) == expected
    assert WALLET_DOCUMENTS_SURFACE == "uploads"
    assert is_allowlisted_surface("calendar")
    assert is_allowlisted_surface("uploads")
    assert not is_allowlisted_surface("admin-shell")
    assert not is_allowlisted_surface("../etc/passwd")
    assert surface_allowlist_error(None) == "surface_id_required"
    assert surface_allowlist_error("not-a-real-route") == "surface_not_allowlisted"
    assert surface_allowlist_error("home") is None


def test_resolve_navigation_surface_aliases() -> None:
    assert resolve_navigation_surface("calendar") == "calendar"
    assert resolve_navigation_surface("appointments") == "calendar"
    assert resolve_navigation_surface("wallet") == "uploads"
    assert resolve_navigation_surface("documents") == "uploads"
    assert resolve_navigation_surface("Dashboard") == "home"
    assert resolve_navigation_surface("totally-unknown-route") is None
    assert resolve_navigation_surface("/etc/passwd") is None
    assert resolve_navigation_surface("javascript:alert(1)") is None


def test_descriptor_ids_match_pilot_catalog() -> None:
    assert OPEN_APP_SURFACE_DESCRIPTOR_ID == "voice.python.open_app_surface.v1"
    assert (
        OPEN_WALLET_DOCUMENTS_DESCRIPTOR_ID
        == "voice.python.open_wallet_documents.v1"
    )
    proposal = build_app_proposal(
        logical_action=OPEN_APP_SURFACE_LOGICAL,
        arguments={"surface_id": "home"},
        tenant_id="tenant-a",
    )
    assert proposal.descriptor_id == OPEN_APP_SURFACE_DESCRIPTOR_ID
    assert proposal.route == WALLET_APP_SUPPORT_ROUTE
    docs = build_app_proposal(
        logical_action=OPEN_WALLET_DOCUMENTS_LOGICAL,
        arguments={},
        tenant_id="tenant-a",
    )
    assert docs.descriptor_id == OPEN_WALLET_DOCUMENTS_DESCRIPTOR_ID
    assert docs.route == WALLET_DOCS_SUPPORT_ROUTE


def test_list_navigation_surfaces_sorted() -> None:
    rows = list_navigation_surfaces()
    assert len(rows) == len(NAVIGATION_SURFACE_IDS)
    ids = [r["surface_id"] for r in rows]
    assert ids == sorted(ids)
    assert all("label" in r for r in rows)


# ── allowlisted surfaces open after server permit ────────────────────────────


def test_allowlisted_surface_opens_after_permit() -> None:
    binding = _binding()
    session = _session()
    proposal = build_app_proposal(
        logical_action=OPEN_APP_SURFACE_LOGICAL,
        arguments={"surface_id": "calendar"},
        tenant_id=session.tenant_id,
    )
    decision = build_permit_decision(proposal)
    assert decision.kind is ActionDecisionKind.PERMIT_READ
    assert decision.permits_execution

    receipt = binding.invoke(proposal=proposal, decision=decision, session=session)
    assert receipt.status is ActionStatus.SUCCEEDED, receipt.to_dict()
    assert receipt.public_result["ok"] == "true"
    assert receipt.public_result["surface_id"] == "calendar"
    assert receipt.public_result["label"] == "Calendar"
    assert receipt.adapter == "app_tool"
    assert receipt.metadata.get("surface_id") == "calendar"
    assert binding.active_surface_id == "calendar"
    opened = binding.list_opened(tenant_id="tenant-a")
    assert len(opened) == 1
    assert opened[0].surface_id == "calendar"


def test_multiple_allowlisted_surfaces_open_under_permit() -> None:
    binding = _binding()
    session = _session()
    # proof-center is voice_read_only and must not open on client voice.
    for surface in ("home", "messages", "social-services", "settings"):
        proposal = build_app_proposal(
            logical_action=OPEN_APP_SURFACE_LOGICAL,
            arguments={"surface_id": surface},
            tenant_id=session.tenant_id,
            proposal_id=f"prop-{surface}",
        )
        receipt = binding.invoke(
            proposal=proposal,
            decision=build_permit_decision(proposal),
            session=session,
        )
        assert receipt.status is ActionStatus.SUCCEEDED, receipt.to_dict()
        assert receipt.public_result["surface_id"] == surface
    assert binding.active_surface_id == "settings"
    assert len(binding.list_opened(tenant_id="tenant-a")) == 4


def test_alias_resolves_to_allowlisted_surface_under_permit() -> None:
    binding = _binding()
    session = _session()
    proposal = build_app_proposal(
        logical_action=OPEN_APP_SURFACE_LOGICAL,
        arguments={"route": "appointments"},
        tenant_id=session.tenant_id,
    )
    receipt = binding.invoke(
        proposal=proposal,
        decision=build_permit_decision(proposal),
        session=session,
    )
    assert receipt.status is ActionStatus.SUCCEEDED
    assert receipt.public_result["surface_id"] == "calendar"


def test_open_wallet_documents_opens_uploads_after_permit() -> None:
    binding = _binding()
    session = _session()
    proposal = build_app_proposal(
        logical_action=OPEN_WALLET_DOCUMENTS_LOGICAL,
        arguments={},
        tenant_id=session.tenant_id,
    )
    decision = build_permit_decision(proposal)
    receipt = binding.invoke(proposal=proposal, decision=decision, session=session)
    assert receipt.status is ActionStatus.SUCCEEDED, receipt.to_dict()
    assert receipt.public_result["surface_id"] == WALLET_DOCUMENTS_SURFACE
    assert receipt.public_result["label"] == "Wallet"
    assert receipt.public_result["logical_action"] == OPEN_WALLET_DOCUMENTS_LOGICAL
    assert binding.active_surface_id == "uploads"


def test_open_wallet_documents_with_document_id() -> None:
    binding = _binding()
    session = _session()
    proposal = build_app_proposal(
        logical_action=OPEN_WALLET_DOCUMENTS_LOGICAL,
        arguments={"document_id": "rec-abc123"},
        tenant_id=session.tenant_id,
    )
    receipt = binding.invoke(
        proposal=proposal,
        decision=build_permit_decision(proposal),
        session=session,
    )
    assert receipt.status is ActionStatus.SUCCEEDED
    assert receipt.public_result["document_id"] == "rec-abc123"
    assert receipt.public_result["surface_id"] == "uploads"


def test_convenience_open_apis_under_permit() -> None:
    binding = _binding()
    session = _session()

    app_proposal = build_app_proposal(
        logical_action=OPEN_APP_SURFACE_LOGICAL,
        arguments={"surface_id": "settings"},
        tenant_id=session.tenant_id,
    )
    app_receipt = binding.open_app_surface(
        session=session,
        decision=build_permit_decision(app_proposal),
        surface_id="settings",
        proposal=app_proposal,
    )
    assert app_receipt.status is ActionStatus.SUCCEEDED
    assert app_receipt.public_result["surface_id"] == "settings"

    docs_proposal = build_app_proposal(
        logical_action=OPEN_WALLET_DOCUMENTS_LOGICAL,
        arguments={},
        tenant_id=session.tenant_id,
        proposal_id="prop-docs-conv",
    )
    docs_receipt = binding.open_wallet_documents(
        session=session,
        decision=build_permit_decision(docs_proposal),
        proposal=docs_proposal,
    )
    assert docs_receipt.status is ActionStatus.SUCCEEDED
    assert docs_receipt.public_result["surface_id"] == "uploads"


# ── non-allowlisted routes fail closed ───────────────────────────────────────


def test_non_allowlisted_route_fails_closed() -> None:
    binding = _binding()
    session = _session()
    proposal = build_app_proposal(
        logical_action=OPEN_APP_SURFACE_LOGICAL,
        arguments={"surface_id": "admin-debug-console"},
        tenant_id=session.tenant_id,
    )
    decision = build_permit_decision(proposal)
    assert decision.permits_execution

    receipt = binding.invoke(proposal=proposal, decision=decision, session=session)
    assert receipt.status is ActionStatus.DENIED
    assert receipt.error == "surface_not_allowlisted"
    assert binding.list_opened(tenant_id="tenant-a") == ()
    assert binding.active_surface_id is None


def test_path_traversal_surface_fails_closed() -> None:
    binding = _binding()
    session = _session()
    for bad in (
        "../etc/passwd",
        "/home/secret/wallet.db",
        "C:\\Windows\\System32",
        "file:///etc/shadow",
        "../../uploads",
    ):
        proposal = build_app_proposal(
            logical_action=OPEN_APP_SURFACE_LOGICAL,
            arguments={"surface_id": bad},
            tenant_id=session.tenant_id,
            proposal_id=f"prop-bad-{abs(hash(bad)) % 10_000}",
        )
        # Some path-like values are rejected at proposal construction time
        # (banned *_path keys) or at argument validation / allowlist.
        try:
            receipt = binding.invoke(
                proposal=proposal,
                decision=build_permit_decision(proposal),
                session=session,
            )
        except ValueError:
            # ActionProposal rejects some locator-shaped keys; also acceptable.
            continue
        assert receipt.status in {ActionStatus.DENIED, ActionStatus.FAILED}
        assert binding.list_opened(tenant_id="tenant-a") == ()


def test_missing_surface_id_fails_closed() -> None:
    binding = _binding()
    session = _session()
    proposal = build_app_proposal(
        logical_action=OPEN_APP_SURFACE_LOGICAL,
        arguments={},
        tenant_id=session.tenant_id,
    )
    receipt = binding.invoke(
        proposal=proposal,
        decision=build_permit_decision(proposal),
        session=session,
    )
    assert receipt.status is ActionStatus.FAILED
    assert receipt.error == "surface_id_required"
    assert binding.list_opened(tenant_id="tenant-a") == ()


def test_wallet_documents_rejects_non_uploads_surface() -> None:
    binding = _binding()
    session = _session()
    proposal = build_app_proposal(
        logical_action=OPEN_WALLET_DOCUMENTS_LOGICAL,
        arguments={"surface_id": "calendar"},
        tenant_id=session.tenant_id,
    )
    receipt = binding.invoke(
        proposal=proposal,
        decision=build_permit_decision(proposal),
        session=session,
    )
    assert receipt.status is ActionStatus.FAILED
    assert receipt.error == "wallet_documents_requires_uploads_surface"
    assert binding.list_opened(tenant_id="tenant-a") == ()


def test_allowlist_cannot_be_widened_beyond_registry() -> None:
    """Caller-supplied allowlist entries outside the registry are dropped."""

    binding = build_wallet_app_binding(
        allowlist=["home", "evil-backdoor", "calendar"],
    )
    assert "evil-backdoor" not in binding.allowlist
    assert "home" in binding.allowlist
    assert "calendar" in binding.allowlist

    session = _session()
    proposal = build_app_proposal(
        logical_action=OPEN_APP_SURFACE_LOGICAL,
        arguments={"surface_id": "evil-backdoor"},
        tenant_id=session.tenant_id,
    )
    receipt = binding.invoke(
        proposal=proposal,
        decision=build_permit_decision(proposal),
        session=session,
    )
    assert receipt.status is ActionStatus.DENIED
    assert receipt.error == "surface_not_allowlisted"


# ── server permit / confirmation gates ───────────────────────────────────────


def test_unpermitted_decision_does_not_open_surface() -> None:
    binding = _binding()
    session = _session()
    proposal = build_app_proposal(
        logical_action=OPEN_APP_SURFACE_LOGICAL,
        arguments={"surface_id": "home"},
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
        risk_class=RiskClass.READ,
    )
    receipt = binding.invoke(proposal=proposal, decision=decision, session=session)
    assert receipt.status is ActionStatus.DENIED
    assert "does_not_permit" in (receipt.error or "")
    assert binding.list_opened(tenant_id="tenant-a") == ()


def test_unconfirmed_session_fails_before_open() -> None:
    binding = _binding()
    session = _session(confirmed=False)
    proposal = build_app_proposal(
        logical_action=OPEN_APP_SURFACE_LOGICAL,
        arguments={"surface_id": "home"},
        tenant_id=session.tenant_id,
    )
    receipt = binding.invoke(
        proposal=proposal,
        decision=build_permit_decision(proposal),
        session=session,
    )
    assert receipt.status is ActionStatus.FAILED
    assert receipt.error == "confirmation_required"
    assert binding.list_opened(tenant_id="tenant-a") == ()


def test_cross_tenant_denied() -> None:
    binding = _binding()
    proposal = build_app_proposal(
        logical_action=OPEN_APP_SURFACE_LOGICAL,
        arguments={"surface_id": "home"},
        tenant_id="tenant-a",
    )
    session = _session(tenant_id="tenant-b")
    receipt = binding.invoke(
        proposal=proposal,
        decision=build_permit_decision(proposal),
        session=session,
    )
    assert receipt.status is ActionStatus.DENIED
    assert receipt.error == "cross_tenant_denied"
    assert binding.list_opened(tenant_id="tenant-a") == ()
    assert binding.list_opened(tenant_id="tenant-b") == ()


# ── receipts omit private paths / no shell ───────────────────────────────────


def test_receipts_omit_private_filesystem_paths() -> None:
    binding = _binding()
    session = _session()
    proposal = build_app_proposal(
        logical_action=OPEN_APP_SURFACE_LOGICAL,
        arguments={"surface_id": "uploads"},
        tenant_id=session.tenant_id,
    )
    receipt = binding.invoke(
        proposal=proposal,
        decision=build_permit_decision(proposal),
        session=session,
    )
    assert receipt.status is ActionStatus.SUCCEEDED
    blob = str(receipt.to_dict())
    assert "/home/" not in blob
    assert "/Users/" not in blob
    assert "file://" not in blob
    assert "C:\\" not in blob
    assert "~/." not in blob
    # No shell / executable locators in public result.
    assert "argv" not in receipt.public_result
    assert "command" not in receipt.public_result
    assert "executable" not in receipt.public_result


def test_shell_and_path_argument_slots_rejected() -> None:
    binding = _binding()
    session = _session()

    # Forbidden keys rejected at proposal construction (contracts) or binding.
    for key, value in (
        ("command", "/bin/true"),
        ("shell", "bash"),
        ("file_path", "/home/secret/doc.pdf"),
    ):
        try:
            proposal = build_app_proposal(
                logical_action=OPEN_APP_SURFACE_LOGICAL,
                arguments={"surface_id": "home", key: value},
                tenant_id=session.tenant_id,
                proposal_id=f"prop-forbid-{key}",
            )
        except ValueError as exc:
            assert key in str(exc) or "not allowed" in str(exc).lower()
            continue
        receipt = binding.invoke(
            proposal=proposal,
            decision=build_permit_decision(proposal),
            session=session,
        )
        assert receipt.status is ActionStatus.FAILED
        assert binding.list_opened(tenant_id="tenant-a") == ()


def test_private_path_in_surface_value_rejected() -> None:
    binding = _binding()
    session = _session()
    proposal = build_app_proposal(
        logical_action=OPEN_APP_SURFACE_LOGICAL,
        arguments={"surface_id": "/home/barberb/secret-db"},
        tenant_id=session.tenant_id,
    )
    receipt = binding.invoke(
        proposal=proposal,
        decision=build_permit_decision(proposal),
        session=session,
    )
    assert receipt.status in {ActionStatus.DENIED, ActionStatus.FAILED}
    assert binding.list_opened(tenant_id="tenant-a") == ()


def test_fake_surface_api_has_no_filesystem_side_effects() -> None:
    api = InMemoryAppSurfaceApi()
    record = api.open_surface(
        surface_id="home",
        logical_action=OPEN_APP_SURFACE_LOGICAL,
        tenant_id="tenant-a",
    )
    assert record.surface_id == "home"
    assert api.active_surface_id == "home"
    # Opening a non-allowlisted surface raises; no silent open.
    try:
        api.open_surface(
            surface_id="not-registered",
            logical_action=OPEN_APP_SURFACE_LOGICAL,
            tenant_id="tenant-a",
        )
        raised = False
    except ValueError as exc:
        raised = True
        assert "surface_not_allowlisted" in str(exc)
    assert raised
    assert len(api.list_opened(tenant_id="tenant-a")) == 1


def test_default_binding_surface_constants() -> None:
    binding = build_wallet_app_binding()
    assert binding.allowlist == NAVIGATION_SURFACE_IDS
    assert binding.binding_version == "1.0"
    assert binding.active_surface_id is None
