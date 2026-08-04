"""Fail-closed action proposal surface for wallet voice turns.

Retrieval and the slotted response library may identify a logical action via a
route string.  This module:

* proposes a catalog-bound action from the multi-descriptor 211-AI pilot catalog
  (never an executable path);
* evaluates a pilot policy decision (usually CONFIRM / HANDOFF);
* executes a reviewed adapter only when both the operator enable flag and an
  explicit per-request confirmation are present.

Importing this module starts no processes and loads no credentials.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from types import MappingProxyType
from typing import Any, Final

VOICE_ACTION_EXECUTE_FLAG: Final = "WALLET_VOICE_ACTION_EXECUTE_ENABLED"

# Stable pilot descriptor ids (must match catalog_211ai / 211ai-pilot-v1).
APP_SURFACE_DESCRIPTOR_ID: Final = "voice.python.open_app_surface.v1"
WALLET_DOCS_DESCRIPTOR_ID: Final = "voice.python.open_wallet_documents.v1"
READ_CALENDAR_DESCRIPTOR_ID: Final = "voice.python.read_calendar.v1"
CREATE_CALENDAR_REMINDER_DESCRIPTOR_ID: Final = (
    "voice.python.create_calendar_reminder.v1"
)
READ_PROVIDER_MESSAGES_DESCRIPTOR_ID: Final = (
    "voice.python.read_provider_messages.v1"
)
LEAVE_PROVIDER_MESSAGE_DESCRIPTOR_ID: Final = (
    "voice.python.leave_provider_message.v1"
)
OPEN_SERVICE_DETAIL_DESCRIPTOR_ID: Final = "voice.python.open_service_detail.v1"
SCHEDULE_SERVICE_CALLBACK_DESCRIPTOR_ID: Final = (
    "voice.workflow.schedule_service_callback.v1"
)
HANDOFF_LIVE_AGENT_DESCRIPTOR_ID: Final = "voice.human.handoff_live_agent.v1"
ESCALATE_SAFETY_DESCRIPTOR_ID: Final = "voice.human.escalate_safety.v1"

# Deployment-owned route → pilot logical_action map for the 12 slotted-DAG routes.
# Content-only routes are intentionally absent (bridge returns None → no_action).
PILOT_ROUTE_TO_LOGICAL_ACTION: Final[Mapping[str, str]] = MappingProxyType(
    {
        "app_surface_navigation": "open_app_surface",
        "wallet_document_support": "open_wallet_documents",
        "calendar_event_support": "read_calendar",
        "provider_contact_support": "read_provider_messages",
        "service_interaction_support": "schedule_service_callback",
        "grounded_211_answer": "open_service_detail",
        "live_agent": "handoff_live_agent",
        "safety_guardrail_support": "escalate_safety",
    }
)

# All 12 slotted-DAG routes (proposal-eligible + content-only + safety).
PILOT_SLOTTED_ROUTES: Final[tuple[str, ...]] = (
    "app_surface_navigation",
    "calendar_event_support",
    "clarifying_prompt",
    "grounded_211_answer",
    "live_agent",
    "provider_contact_support",
    "repeat_or_restate",
    "safety_guardrail_support",
    "service_interaction_support",
    "speech_unclear_clarification",
    "template_guided_fallback",
    "wallet_document_support",
)

CONTENT_ONLY_ROUTES: Final[frozenset[str]] = frozenset(
    {
        "clarifying_prompt",
        "repeat_or_restate",
        "speech_unclear_clarification",
        "template_guided_fallback",
    }
)


def _truthy(value: object) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def is_voice_action_execute_enabled(value: object | None = None) -> bool:
    """Return whether adapter execution may run after an explicit confirm.

    Default is off.  Proposals and confirmation decisions are always available
    when a route maps; only the execute path is gated.
    """

    if value is None:
        value = os.getenv(VOICE_ACTION_EXECUTE_FLAG, "0")
    return _truthy(value)


def _text(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def extract_voice_route(
    payload: Mapping[str, object],
    *,
    result: object | None = None,
) -> str | None:
    """Resolve a response-DAG route from the request envelope or turn result."""

    direct = _text(payload.get("route")) or _text(payload.get("response_route"))
    if direct:
        return direct

    context = payload.get("context")
    if isinstance(context, Mapping):
        nested = _text(context.get("route")) or _text(context.get("response_route"))
        if nested:
            return nested

    grounding = payload.get("grounding")
    if isinstance(grounding, Mapping):
        nested = _text(grounding.get("route"))
        if nested:
            return nested

    if result is not None:
        provenance = getattr(result, "provenance", None)
        metadata = getattr(provenance, "metadata", None)
        if isinstance(metadata, Mapping):
            nested = _text(metadata.get("route")) or _text(metadata.get("response_route"))
            if nested:
                return nested
        # Some providers stash route on template metadata mirrored into result.
        template_meta = None
        if isinstance(metadata, Mapping):
            template_meta = metadata.get("template_metadata") or metadata.get(
                "response_template"
            )
        if isinstance(template_meta, Mapping):
            nested = _text(template_meta.get("route"))
            if nested:
                return nested

    return None


def pilot_descriptor_map() -> Mapping[str, str]:
    """Return logical_action → descriptor_id for the 211-AI pilot catalog."""

    from ipfs_accelerate_py.action_runtime.catalog_211ai import (
        logical_action_to_descriptor_id,
    )

    return dict(logical_action_to_descriptor_id())


def build_default_action_stack() -> tuple[Any, Any, Any]:
    """Return (catalog, policy, executor) bound to the multi-descriptor pilot catalog.

    Catalog and pilot policy come from the deployment-owned 211-AI pilot set.
    Execution uses a separate fail-closed grant policy so the dual gate
    (operator flag + explicit confirm) never relies on ambient authority.
    Domain packs never supply executable locators.
    """

    from ipfs_accelerate_py.action_runtime import ActionExecutor, FailClosedPolicy
    from ipfs_accelerate_py.action_runtime.catalog_211ai import build_pilot_catalog
    from ipfs_accelerate_py.action_runtime.policy_pilot import build_pilot_policy

    catalog = build_pilot_catalog()
    policy = build_pilot_policy(catalog=catalog)
    # Execute path: grant-only FailClosedPolicy. No CLI registrations — pilot
    # descriptors use python/human/workflow adapters that the executor must not
    # invent. Attempted executes without an admitted adapter fail closed.
    execute_policy = FailClosedPolicy(catalog=catalog)
    executor = ActionExecutor(catalog=catalog, policy=execute_policy, cli_adapter=None)
    return catalog, policy, executor


def _admission_context_from_payload(
    request_payload: Mapping[str, object],
    *,
    confirmed: bool,
):
    """Build pilot admission facts from the wallet request envelope."""

    from ipfs_accelerate_py.action_runtime.policy_pilot import PilotAdmissionContext

    authenticated = _truthy(
        request_payload.get("authenticated")
        if "authenticated" in request_payload
        else (
            request_payload.get("action_authenticated")
            if "action_authenticated" in request_payload
            else request_payload.get("session_authenticated")
        )
    )
    safety_overlay = _truthy(
        request_payload.get("safety_overlay")
        if "safety_overlay" in request_payload
        else request_payload.get("safetyOverlay")
    )
    elevated = _truthy(
        request_payload.get("elevated_admin_grant")
        if "elevated_admin_grant" in request_payload
        else request_payload.get("elevatedAdminGrant")
    )
    session_tenant = _text(request_payload.get("session_tenant_id")) or _text(
        request_payload.get("sessionTenantId")
    )
    return PilotAdmissionContext(
        confirmed=confirmed,
        authenticated=authenticated,
        session_tenant_id=session_tenant,
        safety_overlay=safety_overlay,
        elevated_admin_grant=elevated,
    )


def _decide(policy: object, proposal: object, context: object | None = None):
    """Call policy.decide with optional pilot admission context."""

    decide = getattr(policy, "decide", None)
    if decide is None:
        raise TypeError("policy must provide decide()")
    if context is None:
        return decide(proposal)
    try:
        return decide(proposal, context)
    except TypeError:
        # FailClosedPolicy and other single-arg engines.
        return decide(proposal)


def attach_action_surface(
    serialized: dict[str, object],
    *,
    request_payload: Mapping[str, object],
    result: object | None = None,
    catalog: object | None = None,
    policy: object | None = None,
    executor: object | None = None,
    execute_enabled: bool | None = None,
) -> dict[str, object]:
    """Attach proposal/decision/(optional) receipt to a wallet voice receipt.

    Never mutates authority: proposals alone cannot execute.  Execution requires
    ``is_voice_action_execute_enabled`` and an explicit request confirmation
    (``confirm_action`` / ``action_confirm``).  Confirm without the execute flag
    never runs an adapter.
    """

    route = extract_voice_route(request_payload, result=result)
    surface: dict[str, object] = {
        "route": route,
        "proposal": None,
        "decision": None,
        "receipt": None,
        "execution_enabled": is_voice_action_execute_enabled(execute_enabled),
        "status": "no_route",
    }
    if not route:
        serialized["action"] = surface
        serialized["actionSurface"] = surface
        return serialized

    try:
        from ipfs_accelerate_py.action_runtime import VoiceActionBridge
        from ipfs_accelerate_py.action_runtime.contracts import ActionDecisionKind
    except Exception as exc:  # pragma: no cover - optional package surface
        surface["status"] = "action_runtime_unavailable"
        surface["error"] = type(exc).__name__
        serialized["action"] = surface
        serialized["actionSurface"] = surface
        return serialized

    if catalog is None or policy is None or executor is None:
        catalog, policy, executor = build_default_action_stack()

    try:
        descriptor_map = pilot_descriptor_map()
    except Exception:  # pragma: no cover - catalog import edge
        descriptor_map = {
            "open_app_surface": APP_SURFACE_DESCRIPTOR_ID,
            "open_wallet_documents": WALLET_DOCS_DESCRIPTOR_ID,
            "read_calendar": READ_CALENDAR_DESCRIPTOR_ID,
            "create_calendar_reminder": CREATE_CALENDAR_REMINDER_DESCRIPTOR_ID,
            "read_provider_messages": READ_PROVIDER_MESSAGES_DESCRIPTOR_ID,
            "leave_provider_message": LEAVE_PROVIDER_MESSAGE_DESCRIPTOR_ID,
            "open_service_detail": OPEN_SERVICE_DETAIL_DESCRIPTOR_ID,
            "schedule_service_callback": SCHEDULE_SERVICE_CALLBACK_DESCRIPTOR_ID,
            "handoff_live_agent": HANDOFF_LIVE_AGENT_DESCRIPTOR_ID,
            "escalate_safety": ESCALATE_SAFETY_DESCRIPTOR_ID,
        }

    bridge = VoiceActionBridge(
        catalog=catalog,  # type: ignore[arg-type]
        route_map=dict(PILOT_ROUTE_TO_LOGICAL_ACTION),
        descriptor_map=dict(descriptor_map),
    )
    transcript = ""
    if result is not None:
        transcript = str(getattr(result, "transcript", "") or "")
    if not transcript:
        transcript = str(
            request_payload.get("user_prompt")
            or request_payload.get("userPrompt")
            or request_payload.get("transcript")
            or ""
        )
    template_id = None
    if result is not None:
        provenance = getattr(result, "provenance", None)
        template_id = getattr(provenance, "template_id", None)

    tenant_id = _text(request_payload.get("tenant_id")) or _text(
        request_payload.get("tenantId")
    )
    session_id = _text(request_payload.get("session_id")) or _text(
        request_payload.get("sessionId")
    )
    channel = _text(request_payload.get("channel")) or "voice"

    proposal = bridge.propose(
        route=route,
        transcript=transcript,
        template_id=str(template_id) if template_id else None,
        tenant_id=tenant_id,
        session_id=session_id,
        channel=channel,
        confidence=0.0,
    )
    if proposal is None:
        surface["status"] = "route_not_actionable"
        serialized["action"] = surface
        serialized["actionSurface"] = surface
        return serialized

    surface["proposal"] = proposal.to_dict()

    confirm = _truthy(
        request_payload.get("confirm_action")
        if "confirm_action" in request_payload
        else request_payload.get("action_confirm")
    )
    execute_ok = is_voice_action_execute_enabled(execute_enabled)

    # Default product path: evaluate without treating confirm as execute authority.
    # Confirm alone never grants adapter invocation.
    unconfirmed_ctx = _admission_context_from_payload(
        request_payload, confirmed=False
    )
    decision = _decide(policy, proposal, unconfirmed_ctx)
    surface["decision"] = decision.to_dict()
    surface["status"] = decision.kind.value

    if confirm and execute_ok:
        # Re-evaluate with confirmed admission facts for pilot matrix (auth, etc.).
        confirmed_ctx = _admission_context_from_payload(
            request_payload, confirmed=True
        )
        confirmed_decision = _decide(policy, proposal, confirmed_ctx)
        surface["decision"] = confirmed_decision.to_dict()
        surface["status"] = confirmed_decision.kind.value

        if confirmed_decision.permits_execution:
            # Explicit grant for this proposal only on the executor's grant policy.
            exec_policy = getattr(executor, "policy", None)
            grant = getattr(exec_policy, "grant", None)
            if callable(grant):
                grant(
                    proposal_id=proposal.proposal_id,
                    kind=ActionDecisionKind.PERMIT_EXECUTE
                    if confirmed_decision.kind == ActionDecisionKind.PERMIT_EXECUTE
                    else ActionDecisionKind.PERMIT_READ,
                )
            decision, receipt = executor.execute(proposal)  # type: ignore[union-attr]
            surface["decision"] = decision.to_dict()
            surface["receipt"] = receipt.to_dict()
            receipt_status = str(
                receipt.status.value if hasattr(receipt.status, "value") else receipt.status
            )
            surface["status"] = (
                "executed" if receipt_status == "succeeded" else "execution_failed"
            )
        # else: handoff/deny/confirm — never force adapter run
    elif confirm and not execute_ok:
        surface["status"] = "execution_disabled"
        surface["error"] = (
            f"set {VOICE_ACTION_EXECUTE_FLAG}=1 to allow confirmed adapter execution"
        )
    # else: leave pilot decision status (confirm / handoff / deny)

    serialized["action"] = surface
    # camelCase alias for browser clients
    serialized["actionSurface"] = surface
    return serialized
