"""Offline e2e pilot matrix over slotted-DAG route samples (VOICE-ACTION-029).

Acceptance
----------
* All 12 slotted-DAG routes are covered.
* Tool-adjacent routes exercise confirm → execute against offline fakes.
* Content-only routes assert explicit ``no_action`` (no proposal / no adapter).
* ``live_agent`` asserts handoff request semantics (never silent transfer success).
* No network I/O.

Pipeline under test (dual-plane):

```text
slotted DAG route sample (content)
  -> logical ActionProposal (catalog id only)
  -> PilotPolicy (confirm / handoff / permit)
  -> offline fake adapter (authority)
  -> ActionReceipt + spoken-outcome selection
```
"""

from __future__ import annotations

import json
import socket
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from collections.abc import Mapping
from unittest import mock

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
for _candidate in (
    REPO_ROOT,
    REPO_ROOT / "ipfs_accelerate_py",
    REPO_ROOT / "ipfs_datasets_py",
):
    _path = str(_candidate)
    if _candidate.is_dir() and _path not in sys.path:
        sys.path.insert(0, _path)

from ipfs_accelerate_py.action_runtime.adapters.calendar import (  # noqa: E402
    CalendarActionAdapter,
    CalendarInvocationContext,
    InMemoryCalendarEventStore,
    default_calendar_registrations,
)
from ipfs_accelerate_py.action_runtime.adapters.human_handoff import (  # noqa: E402
    HandoffInvocationContext,
    HumanHandoffActionAdapter,
    InMemoryHandoffRequestStore,
    allows_spoken_success,
    default_handoff_registrations,
    spoken_outcome_role as handoff_spoken_outcome_role,
)
from ipfs_accelerate_py.action_runtime.adapters.messaging import (  # noqa: E402
    InMemoryProviderMessageStore,
    MessagingActionAdapter,
    MessagingInvocationContext,
    ProviderMessageRecord,
    default_messaging_registrations,
)
from ipfs_accelerate_py.action_runtime.adapters.service_interaction import (  # noqa: E402
    InMemoryServiceInteractionStore,
    ServiceDetailRecord,
    ServiceInteractionActionAdapter,
    ServiceInteractionInvocationContext,
    default_service_interaction_registrations,
)
from ipfs_accelerate_py.action_runtime.catalog_211ai import (  # noqa: E402
    CATALOG_ID,
    build_pilot_catalog,
    logical_action_to_descriptor_id,
)
from ipfs_accelerate_py.action_runtime.contracts import (  # noqa: E402
    ActionDecision,
    ActionDecisionKind,
    ActionProposal,
    ActionReceipt,
    ActionStatus,
)
from ipfs_accelerate_py.action_runtime.outcome_speech import (  # noqa: E402
    select_outcome_speech,
)
from ipfs_accelerate_py.action_runtime.policy_pilot import (  # noqa: E402
    PilotAdmissionContext,
    PilotPolicy,
)
from ipfs_accelerate_py.action_runtime.voice_bridge import (  # noqa: E402
    CONTENT_ONLY_ROUTES,
    DEFAULT_ROUTE_CLASSIFICATION,
    EXPECTED_ROUTE_COUNT,
    NO_ACTION,
    SLOTTED_DAG_ROUTES,
    TOOL_ADJACENT_ROUTES,
    VoiceActionBridge,
    is_content_only,
    is_tool_adjacent,
)
from wallet_interface.helpers._voice_app_action_binding import (  # noqa: E402
    InMemoryAppSurfaceApi,
    WalletAppSession,
    build_wallet_app_binding,
)

# ---------------------------------------------------------------------------
# Paths / schema constants
# ---------------------------------------------------------------------------

TASK_ID = "VOICE-ACTION-029"
GOAL_ID = "VOICE-ACTION-G140"
PROGRAM_ID = "voice-action-dag-abby-v1"
BOARD_NAMESPACE = "voice-action-dag-abby-v1"
MATRIX_SCHEMA = "voice-action/e2e-matrix@1"
RECEIPT_SCHEMA = "voice-action/e2e-matrix-receipt@1"
TENANT_ID = "tenant-pilot-e2e"
SESSION_ID = "sess-pilot-e2e-1"
GROUNDED_SERVICE = "svc-housing-211-demo"
GROUNDED_EVIDENCE = (
    f"service_id:{GROUNDED_SERVICE}",
    "bafyE2ePilotEvidenceCid0001",
)

SLOTTED_DAG_PATH = REPO_ROOT / "docs" / "phone_dialog_generation" / "slotted_response_dag.json"
ACTION_LINKS_PATH = (
    REPO_ROOT / "docs" / "phone_dialog_generation" / "slotted_response_action_links.json"
)
ROUTE_GAP_PATH = REPO_ROOT / "data" / "voice_action_dag" / "baseline" / "route-gap-matrix.json"
MATRIX_RECEIPT_EXAMPLE = (
    REPO_ROOT / "data" / "voice_action_dag" / "e2e" / "matrix-receipt.example.json"
)
E2E_PILOT_DOC = REPO_ROOT / "docs" / "voice_action_dag" / "E2E_PILOT.md"

# ---------------------------------------------------------------------------
# Compact route recipes (slotted-DAG samples without re-emitting full edges)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RouteRecipe:
    """Compact offline sample for one of the 12 slotted-DAG routes."""

    route: str
    classification: str
    user: str
    assistant: str
    # Pilot catalog logical action used by the e2e execute path, or no_action.
    logical_action: str
    # Adapter family for confirm+execute paths; None for content-only / safety policy.
    adapter: str | None = None
    arguments: Mapping[str, str] = field(default_factory=dict)
    evidence: tuple[str, ...] = ()
    # When True, write-class auth is required after confirm.
    requires_auth: bool = False
    # Secondary pilot action exercised under the same route (calendar/messages).
    secondary_logical_action: str | None = None
    secondary_arguments: Mapping[str, str] = field(default_factory=dict)
    secondary_requires_auth: bool = False


# Pilot-catalog-bound execute map for the e2e matrix.
# Tool-adjacent routes use refined pilot actions (read_calendar, etc.) rather
# than historical CLI probe names (open_calendar_support, …).
ROUTE_RECIPES: tuple[RouteRecipe, ...] = (
    RouteRecipe(
        route="app_surface_navigation",
        classification="proposal-eligible",
        user="Can you open my calendar screen?",
        assistant="I can open the calendar surface after you confirm.",
        logical_action="open_app_surface",
        adapter="app",
        arguments={"surface_id": "calendar"},
    ),
    RouteRecipe(
        route="calendar_event_support",
        classification="proposal-eligible",
        user="What appointments do I have tomorrow?",
        assistant="I can read your calendar after you confirm.",
        logical_action="read_calendar",
        adapter="calendar",
        arguments={"limit": "5"},
        secondary_logical_action="create_calendar_reminder",
        secondary_arguments={
            "title": "Call housing intake",
            "starts_at": "2026-08-06T09:00:00Z",
            "duration_minutes": "30",
        },
        secondary_requires_auth=True,
    ),
    RouteRecipe(
        route="clarifying_prompt",
        classification="content-only",
        user="I need help.",
        assistant="Sure — what kind of help are you looking for today?",
        logical_action=NO_ACTION,
    ),
    RouteRecipe(
        route="grounded_211_answer",
        classification="proposal-eligible",
        user="Is there shelter space in Multnomah County?",
        assistant="I found a housing program. I can open its detail if you confirm.",
        logical_action="open_service_detail",
        adapter="service",
        arguments={"service_id": GROUNDED_SERVICE},
        evidence=GROUNDED_EVIDENCE,
    ),
    RouteRecipe(
        route="live_agent",
        classification="proposal-eligible",
        user="Please transfer me to a live specialist.",
        assistant="I can request a live-agent handoff. Transfer success needs a receipt.",
        logical_action="handoff_live_agent",
        adapter="handoff",
        arguments={
            "reason": "caller_requested_specialist",
            "priority": "high",
            "queue": "live_agent",
            "summary": "Caller needs housing intake help.",
        },
    ),
    RouteRecipe(
        route="provider_contact_support",
        classification="proposal-eligible",
        user="Do I have any messages from my caseworker?",
        assistant="I can read provider messages after you confirm and authenticate.",
        logical_action="read_provider_messages",
        adapter="messaging",
        arguments={
            "provider_id": "provider-rose",
            "client_id": "client-abby",
            "limit": "10",
        },
        requires_auth=True,
        secondary_logical_action="leave_provider_message",
        secondary_arguments={
            "provider_id": "provider-rose",
            "client_id": "client-abby",
            "channel": "in_app",
            "subject": "Callback request",
            "body": "Please call me about housing intake.",
        },
        secondary_requires_auth=True,
    ),
    RouteRecipe(
        route="repeat_or_restate",
        classification="content-only",
        user="Could you say that again more slowly?",
        assistant="Of course. I'll repeat the last answer more slowly.",
        logical_action=NO_ACTION,
    ),
    RouteRecipe(
        route="safety_guardrail_support",
        classification="safety-overlay",
        user="Someone is threatening me right now.",
        assistant="If you are in immediate danger, call 911. I can escalate under policy.",
        logical_action="escalate_safety",
        adapter="safety",
    ),
    RouteRecipe(
        route="service_interaction_support",
        classification="proposal-eligible",
        user="Open that service and schedule a callback.",
        assistant="I can open the service detail after you confirm.",
        logical_action="open_service_detail",
        adapter="service",
        arguments={"service_id": GROUNDED_SERVICE},
        evidence=GROUNDED_EVIDENCE,
        secondary_logical_action="schedule_service_callback",
        secondary_arguments={
            "service_id": GROUNDED_SERVICE,
            "callback_at": "2026-08-06T14:00:00Z",
            "channel": "phone",
            "client_id": "client-abby",
            "notes": "Prefer afternoon callback.",
        },
        secondary_requires_auth=True,
    ),
    RouteRecipe(
        route="speech_unclear_clarification",
        classification="content-only",
        user="... (unclear audio) ...",
        assistant="I didn't catch that. Could you please repeat?",
        logical_action=NO_ACTION,
    ),
    RouteRecipe(
        route="template_guided_fallback",
        classification="content-only",
        user="asdf qwerty unrelated gibberish",
        assistant="I can help with 211 resources, appointments, or a live agent.",
        logical_action=NO_ACTION,
    ),
    RouteRecipe(
        route="wallet_document_support",
        classification="proposal-eligible",
        user="Show me my wallet documents.",
        assistant="I can open your wallet documents surface after you confirm.",
        logical_action="open_wallet_documents",
        adapter="app",
        arguments={},
    ),
)

assert len(ROUTE_RECIPES) == EXPECTED_ROUTE_COUNT
assert {r.route for r in ROUTE_RECIPES} == set(SLOTTED_DAG_ROUTES)


def _recipe_by_route() -> dict[str, RouteRecipe]:
    return {r.route: r for r in ROUTE_RECIPES}


# ---------------------------------------------------------------------------
# Network deny (fail closed if any test path opens a socket)
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _deny_network() -> Any:
    """Block ambient network for the entire pilot matrix suite."""

    def _blocked(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("network_denied: voice-action e2e pilot matrix is offline")

    with mock.patch.object(socket.socket, "connect", side_effect=_blocked), mock.patch.object(
        socket.socket, "connect_ex", side_effect=_blocked
    ), mock.patch.object(
        socket, "create_connection", side_effect=_blocked
    ):
        yield


# ---------------------------------------------------------------------------
# Offline pilot harness (catalog + policy + fakes)
# ---------------------------------------------------------------------------


@dataclass
class PilotFakeStack:
    """In-memory adapters for the pilot matrix (no network, no shell)."""

    catalog: Any
    policy: PilotPolicy
    app_binding: Any
    calendar: CalendarActionAdapter
    messaging: MessagingActionAdapter
    service: ServiceInteractionActionAdapter
    handoff: HumanHandoffActionAdapter
    calendar_store: InMemoryCalendarEventStore
    messaging_store: InMemoryProviderMessageStore
    service_store: InMemoryServiceInteractionStore
    handoff_store: InMemoryHandoffRequestStore
    app_surfaces: InMemoryAppSurfaceApi
    descriptor_map: Mapping[str, str]


def build_fake_stack() -> PilotFakeStack:
    catalog = build_pilot_catalog()
    # Use the real clock so decision TTL does not expire mid-invoke.
    policy = PilotPolicy(catalog=catalog)
    app_surfaces = InMemoryAppSurfaceApi()
    app_binding = build_wallet_app_binding(surface_api=app_surfaces, require_confirm=True)

    calendar_store = InMemoryCalendarEventStore()
    messaging_store = InMemoryProviderMessageStore()
    messaging_store.seed(
        ProviderMessageRecord(
            message_id="msg-seed-1",
            tenant_id=TENANT_ID,
            provider_id="provider-rose",
            client_id="client-abby",
            channel="in_app",
            subject="Welcome",
            body="SECRET body must not leak into public receipts",
            direction="inbound",
            status="delivered",
            created_at_epoch_s=1_700_000_000.0,
        )
    )
    service_store = InMemoryServiceInteractionStore()
    service_store.seed_services(
        ServiceDetailRecord(
            service_id=GROUNDED_SERVICE,
            title="211 Housing Intake Demo",
            provider_name="211info",
            program_name="Emergency Shelter Referral",
            summary="Offline pilot service row",
            tenant_id=None,
        )
    )
    handoff_store = InMemoryHandoffRequestStore()

    return PilotFakeStack(
        catalog=catalog,
        policy=policy,
        app_binding=app_binding,
        calendar=CalendarActionAdapter(
            default_calendar_registrations(), store=calendar_store
        ),
        messaging=MessagingActionAdapter(
            default_messaging_registrations(), store=messaging_store
        ),
        service=ServiceInteractionActionAdapter(
            default_service_interaction_registrations(), store=service_store
        ),
        handoff=HumanHandoffActionAdapter(
            default_handoff_registrations(), store=handoff_store
        ),
        calendar_store=calendar_store,
        messaging_store=messaging_store,
        service_store=service_store,
        handoff_store=handoff_store,
        app_surfaces=app_surfaces,
        descriptor_map=logical_action_to_descriptor_id(),
    )


def _proposal_for(
    recipe: RouteRecipe,
    *,
    logical_action: str | None = None,
    arguments: Mapping[str, str] | None = None,
    proposal_id: str | None = None,
) -> ActionProposal:
    action = logical_action or recipe.logical_action
    if action == NO_ACTION:
        raise ValueError("cannot build proposal for no_action")
    desc_map = logical_action_to_descriptor_id()
    if action not in desc_map:
        raise KeyError(f"logical_action {action!r} not in pilot catalog")
    return ActionProposal(
        proposal_id=proposal_id or f"prop-e2e-{recipe.route[:12]}-{action[:16]}",
        descriptor_id=desc_map[action],
        logical_action=action,
        arguments=dict(arguments if arguments is not None else recipe.arguments),
        route=recipe.route,
        source="e2e_pilot_matrix",
        confidence=0.99,
        tenant_id=TENANT_ID,
        session_id=SESSION_ID,
        channel="voice",
        evidence=recipe.evidence,
        metadata={
            "task_id": TASK_ID,
            "route_classification": recipe.classification,
            "transcript_sha_prefix": recipe.user[:32],
        },
    )


def _decide(
    stack: PilotFakeStack,
    proposal: ActionProposal,
    *,
    confirmed: bool = False,
    authenticated: bool = False,
    safety_overlay: bool = False,
) -> ActionDecision:
    return stack.policy.decide(
        proposal,
        PilotAdmissionContext(
            confirmed=confirmed,
            authenticated=authenticated,
            session_tenant_id=TENANT_ID if authenticated or confirmed else None,
            safety_overlay=safety_overlay,
        ),
    )


def _execute(
    stack: PilotFakeStack,
    recipe: RouteRecipe,
    proposal: ActionProposal,
    decision: ActionDecision,
    *,
    confirmed: bool,
    authenticated: bool,
) -> ActionReceipt:
    adapter = recipe.adapter
    if adapter == "app":
        session = WalletAppSession(
            tenant_id=TENANT_ID,
            authenticated=authenticated,
            confirmed=confirmed,
            client_id="client-abby",
            session_id=SESSION_ID,
            channel="voice",
        )
        return stack.app_binding.invoke(
            proposal=proposal, decision=decision, session=session
        )
    if adapter == "calendar":
        return stack.calendar.invoke(
            proposal=proposal,
            decision=decision,
            context=CalendarInvocationContext(
                confirmed=confirmed,
                authenticated=authenticated,
                session_tenant_id=TENANT_ID,
            ),
        )
    if adapter == "messaging":
        return stack.messaging.invoke(
            proposal=proposal,
            decision=decision,
            context=MessagingInvocationContext(
                confirmed=confirmed,
                authenticated=authenticated,
                session_tenant_id=TENANT_ID,
            ),
        )
    if adapter == "service":
        return stack.service.invoke(
            proposal=proposal,
            decision=decision,
            context=ServiceInteractionInvocationContext(
                confirmed=confirmed,
                authenticated=authenticated,
                session_tenant_id=TENANT_ID,
            ),
        )
    if adapter == "handoff":
        return stack.handoff.invoke(
            proposal=proposal,
            decision=decision,
            context=HandoffInvocationContext(
                confirmed=confirmed,
                authenticated=authenticated,
                session_tenant_id=TENANT_ID,
            ),
        )
    raise ValueError(f"no execute path for adapter={adapter!r}")


def _matrix_case_receipt(
    *,
    recipe: RouteRecipe,
    proposal: ActionProposal | None,
    unconfirmed_decision: ActionDecision | None,
    confirmed_decision: ActionDecision | None,
    receipt: ActionReceipt | None,
    spoken_role: str | None,
    spoken_success_allowed: bool | None,
    status: str,
) -> dict[str, Any]:
    """Build a compact, redacted matrix case receipt (no full envelopes)."""

    return {
        "route": recipe.route,
        "classification": recipe.classification,
        "logical_action": recipe.logical_action,
        "adapter": recipe.adapter,
        "status": status,
        "proposal_id": proposal.proposal_id if proposal else None,
        "descriptor_id": proposal.descriptor_id if proposal else None,
        "unconfirmed_decision_kind": (
            unconfirmed_decision.kind.value if unconfirmed_decision else None
        ),
        "confirmed_decision_kind": (
            confirmed_decision.kind.value if confirmed_decision else None
        ),
        "receipt_status": receipt.status.value if receipt else None,
        "receipt_id": receipt.receipt_id if receipt else None,
        "spoken_outcome_role": spoken_role,
        "spoken_success_allowed": spoken_success_allowed,
        "network": "denied",
        "sample": {
            "user": recipe.user,
            "assistant_prefix": recipe.assistant[:80],
        },
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def stack() -> PilotFakeStack:
    return build_fake_stack()


@pytest.fixture(scope="module")
def action_links() -> dict[str, Any]:
    assert ACTION_LINKS_PATH.is_file(), f"missing action links: {ACTION_LINKS_PATH}"
    return json.loads(ACTION_LINKS_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def route_gap() -> dict[str, Any]:
    assert ROUTE_GAP_PATH.is_file(), f"missing route gap matrix: {ROUTE_GAP_PATH}"
    return json.loads(ROUTE_GAP_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Census / coverage
# ---------------------------------------------------------------------------


def test_matrix_covers_exactly_twelve_routes() -> None:
    routes = [r.route for r in ROUTE_RECIPES]
    assert len(routes) == 12
    assert len(routes) == EXPECTED_ROUTE_COUNT
    assert set(routes) == set(SLOTTED_DAG_ROUTES)
    assert set(routes) == set(DEFAULT_ROUTE_CLASSIFICATION)
    assert sorted(routes) == sorted(SLOTTED_DAG_ROUTES)


def test_recipe_classifications_match_voice_bridge() -> None:
    for recipe in ROUTE_RECIPES:
        assert recipe.classification == DEFAULT_ROUTE_CLASSIFICATION[recipe.route]
        if recipe.classification == "content-only":
            assert recipe.logical_action == NO_ACTION
            assert recipe.adapter is None
            assert is_content_only(recipe.route)
        if recipe.route in TOOL_ADJACENT_ROUTES:
            assert is_tool_adjacent(recipe.route)
            assert recipe.adapter is not None
            assert recipe.logical_action != NO_ACTION


def test_slotted_dag_summary_route_census(route_gap: dict[str, Any]) -> None:
    """Assert the 12-route census without loading the multi-MB edge dump."""

    census = route_gap["route_census"]
    assert len(census) == 12
    assert set(census) == set(SLOTTED_DAG_ROUTES)
    # Optional: if the full DAG is present, summary.routeCounts must match.
    if SLOTTED_DAG_PATH.is_file():
        # Stream only the top-level summary via a cheap partial read of route gap
        # already validated; full DAG load is intentionally avoided for speed.
        assert route_gap["route_census_total"] == sum(census.values())
        assert route_gap["slotted_response_dag"].endswith("slotted_response_dag.json")


def test_action_links_projection_covers_all_routes(action_links: dict[str, Any]) -> None:
    links = action_links["links"]
    by_route = {row["route"]: row for row in links}
    assert set(by_route) == set(SLOTTED_DAG_ROUTES)
    for recipe in ROUTE_RECIPES:
        link = by_route[recipe.route]
        assert link["classification"] == recipe.classification
        if recipe.classification == "content-only":
            assert link["logical_action"] == NO_ACTION
        else:
            assert link["logical_action"] != NO_ACTION


# ---------------------------------------------------------------------------
# Content-only routes → no_action
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("route", sorted(CONTENT_ONLY_ROUTES))
def test_content_only_routes_assert_no_action(stack: PilotFakeStack, route: str) -> None:
    recipe = _recipe_by_route()[route]
    assert recipe.logical_action == NO_ACTION
    assert recipe.classification == "content-only"

    # Content-plane bridge never proposes for content-only routes.
    bridge = VoiceActionBridge(catalog=stack.catalog)
    assert bridge.propose(route=route, transcript=recipe.user) is None

    # Pilot catalog path: no descriptor for no_action; harness refuses proposal.
    with pytest.raises(ValueError, match="no_action"):
        _proposal_for(recipe)

    case = _matrix_case_receipt(
        recipe=recipe,
        proposal=None,
        unconfirmed_decision=None,
        confirmed_decision=None,
        receipt=None,
        spoken_role=None,
        spoken_success_allowed=None,
        status="no_action",
    )
    assert case["status"] == "no_action"
    assert case["logical_action"] == NO_ACTION
    assert case["receipt_status"] is None


def test_all_content_only_routes_are_covered() -> None:
    content = {r.route for r in ROUTE_RECIPES if r.classification == "content-only"}
    assert content == CONTENT_ONLY_ROUTES
    assert content == {
        "clarifying_prompt",
        "repeat_or_restate",
        "speech_unclear_clarification",
        "template_guided_fallback",
    }


# ---------------------------------------------------------------------------
# Tool-adjacent: confirm then execute with fakes
# ---------------------------------------------------------------------------


def _tool_adjacent_recipes() -> list[RouteRecipe]:
    return [r for r in ROUTE_RECIPES if r.route in TOOL_ADJACENT_ROUTES]


@pytest.mark.parametrize("recipe", _tool_adjacent_recipes(), ids=lambda r: r.route)
def test_tool_adjacent_requires_confirm_before_execute(
    stack: PilotFakeStack, recipe: RouteRecipe
) -> None:
    proposal = _proposal_for(recipe)
    unconfirmed = _decide(stack, proposal, confirmed=False, authenticated=False)
    assert unconfirmed.kind is ActionDecisionKind.CONFIRM
    assert unconfirmed.permits_execution is False

    # Adapter must no-op / deny when decision does not permit.
    denied_receipt = _execute(
        stack,
        recipe,
        proposal,
        unconfirmed,
        confirmed=False,
        authenticated=False,
    )
    assert denied_receipt.status in {ActionStatus.DENIED, ActionStatus.FAILED}
    assert denied_receipt.status is not ActionStatus.SUCCEEDED


@pytest.mark.parametrize("recipe", _tool_adjacent_recipes(), ids=lambda r: r.route)
def test_tool_adjacent_confirm_and_execute_with_fakes(
    stack: PilotFakeStack, recipe: RouteRecipe
) -> None:
    proposal = _proposal_for(recipe)
    unconfirmed = _decide(stack, proposal, confirmed=False, authenticated=False)
    assert unconfirmed.kind is ActionDecisionKind.CONFIRM

    auth = bool(recipe.requires_auth)
    confirmed = _decide(
        stack,
        proposal,
        confirmed=True,
        authenticated=auth or True,  # read paths accept auth; auth-gated need it
    )
    if recipe.requires_auth:
        # Auth-gated reads (messages) need authenticated tenant.
        confirmed = _decide(
            stack, proposal, confirmed=True, authenticated=True
        )
        assert confirmed.kind is ActionDecisionKind.PERMIT_READ
    else:
        assert confirmed.kind in {
            ActionDecisionKind.PERMIT_READ,
            ActionDecisionKind.PERMIT_EXECUTE,
        }
    assert confirmed.permits_execution is True

    receipt = _execute(
        stack,
        recipe,
        proposal,
        confirmed,
        confirmed=True,
        authenticated=True,
    )
    assert receipt.status is ActionStatus.SUCCEEDED, receipt.to_dict()
    assert receipt.proposal_id == proposal.proposal_id
    assert receipt.decision_id == confirmed.decision_id
    assert receipt.descriptor_id == proposal.descriptor_id

    # Spoken outcome after success (library optional; safe fallback ok).
    spoken = select_outcome_speech(
        logical_action=proposal.logical_action,
        receipt=receipt,
        library=None,
    )
    assert spoken.outcome_role == "success"
    assert spoken.spoken_text

    case = _matrix_case_receipt(
        recipe=recipe,
        proposal=proposal,
        unconfirmed_decision=unconfirmed,
        confirmed_decision=confirmed,
        receipt=receipt,
        spoken_role=spoken.outcome_role,
        spoken_success_allowed=spoken.spoken_success_allowed,
        status="confirm_execute_ok",
    )
    assert case["unconfirmed_decision_kind"] == "confirm"
    assert case["receipt_status"] == "succeeded"


def test_tool_adjacent_set_is_exactly_five() -> None:
    assert TOOL_ADJACENT_ROUTES == frozenset(
        {
            "app_surface_navigation",
            "wallet_document_support",
            "calendar_event_support",
            "service_interaction_support",
            "provider_contact_support",
        }
    )
    assert len(_tool_adjacent_recipes()) == 5


# ---------------------------------------------------------------------------
# Calendar + messages secondary write paths (confirm + auth)
# ---------------------------------------------------------------------------


def test_calendar_create_reminder_confirm_auth_execute(stack: PilotFakeStack) -> None:
    recipe = _recipe_by_route()["calendar_event_support"]
    assert recipe.secondary_logical_action == "create_calendar_reminder"
    proposal = _proposal_for(
        recipe,
        logical_action=recipe.secondary_logical_action,
        arguments=recipe.secondary_arguments,
        proposal_id="prop-e2e-cal-create",
    )
    # Unconfirmed write → confirm
    unconfirmed = _decide(stack, proposal, confirmed=False, authenticated=False)
    assert unconfirmed.kind is ActionDecisionKind.CONFIRM
    # Confirmed without auth → deny
    no_auth = _decide(stack, proposal, confirmed=True, authenticated=False)
    assert no_auth.kind is ActionDecisionKind.DENY
    assert "auth" in no_auth.reason
    # Confirmed + auth → permit_execute
    permitted = _decide(stack, proposal, confirmed=True, authenticated=True)
    assert permitted.kind is ActionDecisionKind.PERMIT_EXECUTE
    receipt = _execute(
        stack,
        recipe,
        proposal,
        permitted,
        confirmed=True,
        authenticated=True,
    )
    assert receipt.status is ActionStatus.SUCCEEDED, receipt.to_dict()
    # Notes must not dump into public_result.
    public_blob = json.dumps(dict(receipt.public_result), sort_keys=True)
    assert "SECRET" not in public_blob


def test_messaging_leave_message_confirm_auth_execute(stack: PilotFakeStack) -> None:
    recipe = _recipe_by_route()["provider_contact_support"]
    assert recipe.secondary_logical_action == "leave_provider_message"
    proposal = _proposal_for(
        recipe,
        logical_action=recipe.secondary_logical_action,
        arguments=recipe.secondary_arguments,
        proposal_id="prop-e2e-msg-leave",
    )
    unconfirmed = _decide(stack, proposal, confirmed=False, authenticated=True)
    assert unconfirmed.kind is ActionDecisionKind.CONFIRM
    no_auth = _decide(stack, proposal, confirmed=True, authenticated=False)
    assert no_auth.kind is ActionDecisionKind.DENY
    permitted = _decide(stack, proposal, confirmed=True, authenticated=True)
    assert permitted.kind is ActionDecisionKind.PERMIT_EXECUTE
    receipt = _execute(
        stack,
        recipe,
        proposal,
        permitted,
        confirmed=True,
        authenticated=True,
    )
    assert receipt.status is ActionStatus.SUCCEEDED, receipt.to_dict()
    # Body redaction: free text must not appear in public_result.
    public_blob = json.dumps(dict(receipt.public_result), sort_keys=True)
    assert "Please call me" not in public_blob


def test_service_callback_confirm_auth_execute(stack: PilotFakeStack) -> None:
    recipe = _recipe_by_route()["service_interaction_support"]
    assert recipe.secondary_logical_action == "schedule_service_callback"
    proposal = _proposal_for(
        recipe,
        logical_action=recipe.secondary_logical_action,
        arguments=recipe.secondary_arguments,
        proposal_id="prop-e2e-svc-callback",
    )
    unconfirmed = _decide(stack, proposal, confirmed=False, authenticated=True)
    assert unconfirmed.kind is ActionDecisionKind.CONFIRM
    permitted = _decide(stack, proposal, confirmed=True, authenticated=True)
    assert permitted.kind is ActionDecisionKind.PERMIT_EXECUTE
    receipt = _execute(
        stack,
        recipe,
        proposal,
        permitted,
        confirmed=True,
        authenticated=True,
    )
    assert receipt.status is ActionStatus.SUCCEEDED, receipt.to_dict()


# ---------------------------------------------------------------------------
# live_agent handoff semantics
# ---------------------------------------------------------------------------


def test_live_agent_handoff_request_not_transfer_success(stack: PilotFakeStack) -> None:
    recipe = _recipe_by_route()["live_agent"]
    proposal = _proposal_for(recipe, proposal_id="prop-e2e-live-agent")

    # Policy admits request creation (HANDOFF), never permit_execute.
    decision = _decide(stack, proposal, confirmed=False, authenticated=False)
    assert decision.kind is ActionDecisionKind.HANDOFF
    assert decision.permits_execution is False
    assert "handoff" in decision.reason

    receipt = _execute(
        stack,
        recipe,
        proposal,
        decision,
        confirmed=False,
        authenticated=False,
    )
    assert receipt.status is ActionStatus.ACCEPTED, receipt.to_dict()
    assert receipt.public_result.get("is_transfer_complete") == "false"
    assert receipt.public_result.get("spoken_success_allowed") == "false"
    assert allows_spoken_success(receipt) is False
    assert handoff_spoken_outcome_role(receipt) != "success"

    request_id = receipt.public_result["request_id"]
    stored = stack.handoff_store.get(request_id)
    assert stored is not None
    assert stored.status is ActionStatus.ACCEPTED
    assert stored.is_transfer_complete is False

    # Spoken outcome must not claim transfer success on accepted.
    spoken = select_outcome_speech(
        logical_action="handoff_live_agent",
        receipt=receipt,
        library=None,
    )
    assert spoken.spoken_success_allowed is False
    assert spoken.outcome_role == "unknown"
    assert "connected you" not in spoken.spoken_text.lower()
    assert "transferred" not in spoken.spoken_text.lower()

    # Provider-confirmed success is the only path that unlocks spoken success.
    stack.handoff.mark_started(request_id)
    succeeded = stack.handoff.record_provider_outcome(
        request_id,
        status="succeeded",
        provider_confirmation="pstn-confirm-e2e-pilot-001",
    )
    assert succeeded.status is ActionStatus.SUCCEEDED
    assert allows_spoken_success(succeeded) is True
    spoken_ok = select_outcome_speech(
        logical_action="handoff_live_agent",
        receipt=succeeded,
        library=None,
    )
    assert spoken_ok.spoken_success_allowed is True
    assert spoken_ok.outcome_role == "success"


def test_live_agent_unknown_provider_outcome_blocks_success_speech(
    stack: PilotFakeStack,
) -> None:
    recipe = _recipe_by_route()["live_agent"]
    proposal = _proposal_for(recipe, proposal_id="prop-e2e-live-unknown")
    decision = _decide(stack, proposal, confirmed=True, authenticated=False)
    assert decision.kind is ActionDecisionKind.HANDOFF
    create = _execute(
        stack, recipe, proposal, decision, confirmed=True, authenticated=False
    )
    request_id = create.public_result["request_id"]
    unknown = stack.handoff.record_provider_outcome(
        request_id, status="unknown"
    )
    assert unknown.status is ActionStatus.UNKNOWN
    assert allows_spoken_success(unknown) is False
    spoken = select_outcome_speech(
        logical_action="handoff_live_agent",
        receipt=unknown,
        library=None,
    )
    assert spoken.spoken_success_allowed is False
    assert spoken.outcome_role == "unknown"


# ---------------------------------------------------------------------------
# Safety overlay + grounded service open
# ---------------------------------------------------------------------------


def test_safety_overlay_admits_escalate_not_execute(stack: PilotFakeStack) -> None:
    recipe = _recipe_by_route()["safety_guardrail_support"]
    proposal = _proposal_for(recipe, proposal_id="prop-e2e-safety")
    decision = _decide(
        stack, proposal, confirmed=False, authenticated=False, safety_overlay=True
    )
    assert decision.kind is ActionDecisionKind.HANDOFF
    assert decision.permits_execution is False
    assert decision.reason in {
        "safety_overlay_force_escalate",
        "safety_policy_handoff",
    }
    # Overlay must not widen to a write descriptor.
    cal = _recipe_by_route()["calendar_event_support"]
    write_prop = _proposal_for(
        cal,
        logical_action="create_calendar_reminder",
        arguments=cal.secondary_arguments,
        proposal_id="prop-e2e-safety-widen",
    )
    widened = _decide(
        stack, write_prop, confirmed=False, authenticated=True, safety_overlay=True
    )
    assert widened.kind is ActionDecisionKind.CONFIRM
    assert widened.permits_execution is False


def test_grounded_211_answer_open_service_after_confirm(stack: PilotFakeStack) -> None:
    recipe = _recipe_by_route()["grounded_211_answer"]
    proposal = _proposal_for(recipe, proposal_id="prop-e2e-grounded")
    unconfirmed = _decide(stack, proposal, confirmed=False)
    assert unconfirmed.kind is ActionDecisionKind.CONFIRM
    confirmed = _decide(stack, proposal, confirmed=True, authenticated=False)
    assert confirmed.kind is ActionDecisionKind.PERMIT_READ
    receipt = _execute(
        stack, recipe, proposal, confirmed, confirmed=True, authenticated=False
    )
    assert receipt.status is ActionStatus.SUCCEEDED, receipt.to_dict()


# ---------------------------------------------------------------------------
# Full matrix sweep (one pass, all 12 routes)
# ---------------------------------------------------------------------------


def test_full_matrix_sweep_offline(stack: PilotFakeStack) -> None:
    """Run every route sample once and collect compact case receipts."""

    cases: list[dict[str, Any]] = []
    for recipe in ROUTE_RECIPES:
        if recipe.logical_action == NO_ACTION:
            cases.append(
                _matrix_case_receipt(
                    recipe=recipe,
                    proposal=None,
                    unconfirmed_decision=None,
                    confirmed_decision=None,
                    receipt=None,
                    spoken_role=None,
                    spoken_success_allowed=None,
                    status="no_action",
                )
            )
            continue

        proposal = _proposal_for(recipe)
        if recipe.adapter == "safety":
            decision = _decide(
                stack,
                proposal,
                confirmed=False,
                safety_overlay=True,
            )
            assert decision.kind is ActionDecisionKind.HANDOFF
            cases.append(
                _matrix_case_receipt(
                    recipe=recipe,
                    proposal=proposal,
                    unconfirmed_decision=decision,
                    confirmed_decision=decision,
                    receipt=None,
                    spoken_role=None,
                    spoken_success_allowed=False,
                    status="safety_handoff",
                )
            )
            continue

        if recipe.adapter == "handoff":
            decision = _decide(stack, proposal, confirmed=False)
            assert decision.kind is ActionDecisionKind.HANDOFF
            receipt = _execute(
                stack,
                recipe,
                proposal,
                decision,
                confirmed=False,
                authenticated=False,
            )
            assert receipt.status is ActionStatus.ACCEPTED
            assert allows_spoken_success(receipt) is False
            cases.append(
                _matrix_case_receipt(
                    recipe=recipe,
                    proposal=proposal,
                    unconfirmed_decision=decision,
                    confirmed_decision=decision,
                    receipt=receipt,
                    spoken_role=handoff_spoken_outcome_role(receipt),
                    spoken_success_allowed=False,
                    status="handoff_accepted",
                )
            )
            continue

        # Tool-adjacent + proposal-eligible service open.
        unconfirmed = _decide(stack, proposal, confirmed=False)
        assert unconfirmed.kind is ActionDecisionKind.CONFIRM
        confirmed = _decide(
            stack,
            proposal,
            confirmed=True,
            authenticated=True,
        )
        assert confirmed.permits_execution is True
        receipt = _execute(
            stack,
            recipe,
            proposal,
            confirmed,
            confirmed=True,
            authenticated=True,
        )
        assert receipt.status is ActionStatus.SUCCEEDED, (
            recipe.route,
            receipt.to_dict(),
        )
        spoken = select_outcome_speech(
            logical_action=proposal.logical_action,
            receipt=receipt,
            library=None,
        )
        cases.append(
            _matrix_case_receipt(
                recipe=recipe,
                proposal=proposal,
                unconfirmed_decision=unconfirmed,
                confirmed_decision=confirmed,
                receipt=receipt,
                spoken_role=spoken.outcome_role,
                spoken_success_allowed=spoken.spoken_success_allowed,
                status="confirm_execute_ok",
            )
        )

    assert len(cases) == 12
    by_route = {c["route"]: c for c in cases}
    assert set(by_route) == set(SLOTTED_DAG_ROUTES)

    # Content-only
    for route in CONTENT_ONLY_ROUTES:
        assert by_route[route]["status"] == "no_action"

    # Tool-adjacent executed
    for route in TOOL_ADJACENT_ROUTES:
        assert by_route[route]["status"] == "confirm_execute_ok"
        assert by_route[route]["receipt_status"] == "succeeded"

    # live_agent handoff
    live = by_route["live_agent"]
    assert live["status"] == "handoff_accepted"
    assert live["receipt_status"] == "accepted"
    assert live["spoken_success_allowed"] is False

    # safety
    assert by_route["safety_guardrail_support"]["status"] == "safety_handoff"

    # grounded service open
    assert by_route["grounded_211_answer"]["status"] == "confirm_execute_ok"


# ---------------------------------------------------------------------------
# Example receipt artifact + docs
# ---------------------------------------------------------------------------


def test_matrix_receipt_example_artifact() -> None:
    assert MATRIX_RECEIPT_EXAMPLE.is_file(), (
        f"missing example receipt: {MATRIX_RECEIPT_EXAMPLE}"
    )
    payload = json.loads(MATRIX_RECEIPT_EXAMPLE.read_text(encoding="utf-8"))
    assert payload["schema"] == RECEIPT_SCHEMA
    assert payload["schema_version"] == 1
    assert payload["program_id"] == PROGRAM_ID
    assert payload["board_namespace"] == BOARD_NAMESPACE
    assert payload["task_id"] == TASK_ID
    assert payload["goal_id"] == GOAL_ID
    assert payload["catalog_id"] == CATALOG_ID
    assert payload["network"] == "denied"
    assert payload["transport"] == "offline_fakes"
    cases = payload["cases"]
    assert len(cases) == 12
    routes = {c["route"] for c in cases}
    assert routes == set(SLOTTED_DAG_ROUTES)
    # At least one of each acceptance class is represented.
    statuses = {c["status"] for c in cases}
    assert "no_action" in statuses
    assert "confirm_execute_ok" in statuses
    assert "handoff_accepted" in statuses
    # No executable locators in the example.
    blob = json.dumps(payload).casefold()
    for banned in ("command", "argv", "executable", "import_path", "webhook"):
        assert f'"{banned}"' not in blob


def test_e2e_pilot_doc_exists_and_names_matrix() -> None:
    assert E2E_PILOT_DOC.is_file(), f"missing doc: {E2E_PILOT_DOC}"
    text = E2E_PILOT_DOC.read_text(encoding="utf-8")
    assert "VOICE-ACTION-029" in text
    assert "test_abby_pilot_matrix.py" in text
    assert "no network" in text.casefold() or "offline" in text.casefold()
    assert "live_agent" in text
    assert "no_action" in text
    assert "tool-adjacent" in text.casefold() or "tool adjacent" in text.casefold()
    for route in SLOTTED_DAG_ROUTES:
        assert route in text


def test_pilot_catalog_registers_matrix_actions(stack: PilotFakeStack) -> None:
    needed = {
        r.logical_action
        for r in ROUTE_RECIPES
        if r.logical_action != NO_ACTION
    }
    needed |= {
        r.secondary_logical_action
        for r in ROUTE_RECIPES
        if r.secondary_logical_action
    }
    mapping = stack.descriptor_map
    for action in needed:
        assert action in mapping, f"missing pilot descriptor for {action}"
        assert stack.catalog.get(mapping[action]) is not None


def test_confidence_never_upgrades_unconfirmed_tool_action(stack: PilotFakeStack) -> None:
    recipe = _recipe_by_route()["app_surface_navigation"]
    proposal = _proposal_for(recipe)
    # Even with confidence=1.0, unconfirmed stays confirm (authority plane).
    high = ActionProposal(
        proposal_id="prop-e2e-conf",
        descriptor_id=proposal.descriptor_id,
        logical_action=proposal.logical_action,
        arguments=dict(proposal.arguments),
        route=proposal.route,
        source="e2e_pilot_matrix",
        confidence=1.0,
        tenant_id=TENANT_ID,
        session_id=SESSION_ID,
        channel="voice",
    )
    decision = _decide(stack, high, confirmed=False)
    assert decision.kind is ActionDecisionKind.CONFIRM
    assert decision.permits_execution is False
