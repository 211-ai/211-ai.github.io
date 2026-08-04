"""Fail-closed action proposal surface for wallet voice turns.

Retrieval and the slotted response library may identify a logical action via a
route string.  This module:

* proposes a catalog-bound action (never an executable path);
* evaluates a default-deny policy decision (usually CONFIRM);
* executes a reviewed CLI adapter only when both the operator enable flag and
  an explicit per-request confirmation are present.

Importing this module starts no processes and loads no credentials.
"""

from __future__ import annotations

import os
import shutil
from collections.abc import Mapping
from typing import Any, Final

VOICE_ACTION_EXECUTE_FLAG: Final = "WALLET_VOICE_ACTION_EXECUTE_ENABLED"

# Logical descriptor ids must stay stable for clients and tests.
APP_SURFACE_DESCRIPTOR_ID: Final = "voice.cli.open_app_surface.v1"
WALLET_DOCS_DESCRIPTOR_ID: Final = "voice.cli.open_wallet_documents.v1"
CALENDAR_DESCRIPTOR_ID: Final = "voice.cli.open_calendar_support.v1"
SERVICE_INTERACTION_DESCRIPTOR_ID: Final = "voice.cli.review_service_interaction.v1"
PROVIDER_CONTACT_DESCRIPTOR_ID: Final = "voice.cli.provide_provider_contact.v1"


def _truthy(value: object) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def is_voice_action_execute_enabled(value: object | None = None) -> bool:
    """Return whether CLI execution may run after an explicit confirm.

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
            template_meta = metadata.get("template_metadata") or metadata.get("response_template")
        if isinstance(template_meta, Mapping):
            nested = _text(template_meta.get("route"))
            if nested:
                return nested

    return None


def build_default_action_stack() -> tuple[Any, Any, Any]:
    """Return (catalog, policy, executor) for reviewed read-only CLI probes.

    Executables are pinned to the absolute ``true`` binary.  Domain packs never
    supply these paths; this is operator-owned deployment configuration.
    """

    from ipfs_accelerate_py.action_runtime import (
        ActionCatalog,
        ActionDescriptor,
        ActionExecutor,
        FailClosedPolicy,
        RiskClass,
        SideEffectClass,
    )
    from ipfs_accelerate_py.action_runtime.adapters.cli import (
        CLIActionAdapter,
        CLIActionRegistration,
        CLISandboxPolicy,
    )

    true_bin = shutil.which("true") or "/usr/bin/true"
    descriptors = (
        ActionDescriptor(
            descriptor_id=APP_SURFACE_DESCRIPTOR_ID,
            logical_action="open_app_surface",
            adapter="cli",
            risk_class=RiskClass.READ,
            side_effect_class=SideEffectClass.LOCAL_READ,
            requires_confirmation=True,
            allowed_channels=("voice", "chat", "test"),
        ),
        ActionDescriptor(
            descriptor_id=WALLET_DOCS_DESCRIPTOR_ID,
            logical_action="open_wallet_documents",
            adapter="cli",
            risk_class=RiskClass.READ,
            side_effect_class=SideEffectClass.LOCAL_READ,
            requires_confirmation=True,
            allowed_channels=("voice", "chat", "test"),
        ),
        ActionDescriptor(
            descriptor_id=CALENDAR_DESCRIPTOR_ID,
            logical_action="open_calendar_support",
            adapter="cli",
            risk_class=RiskClass.READ,
            side_effect_class=SideEffectClass.LOCAL_READ,
            requires_confirmation=True,
            allowed_channels=("voice", "chat", "test"),
        ),
        ActionDescriptor(
            descriptor_id=SERVICE_INTERACTION_DESCRIPTOR_ID,
            logical_action="review_service_interaction",
            adapter="cli",
            risk_class=RiskClass.READ,
            side_effect_class=SideEffectClass.LOCAL_READ,
            requires_confirmation=True,
            allowed_channels=("voice", "chat", "test"),
        ),
        ActionDescriptor(
            descriptor_id=PROVIDER_CONTACT_DESCRIPTOR_ID,
            logical_action="provide_provider_contact",
            adapter="cli",
            risk_class=RiskClass.READ,
            side_effect_class=SideEffectClass.LOCAL_READ,
            requires_confirmation=True,
            allowed_channels=("voice", "chat", "test"),
        ),
    )
    catalog = ActionCatalog(list(descriptors))
    policy = FailClosedPolicy(catalog=catalog)
    registrations = [
        CLIActionRegistration(
            descriptor_id=descriptor.descriptor_id,
            executable=true_bin,
            sandbox=CLISandboxPolicy(timeout_seconds=2.0, isolate_environment=True),
        )
        for descriptor in descriptors
    ]
    adapter = CLIActionAdapter(registrations)
    executor = ActionExecutor(catalog=catalog, policy=policy, cli_adapter=adapter)
    return catalog, policy, executor


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
    (``confirm_action`` / ``action_confirm``).
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
        return serialized

    try:
        from ipfs_accelerate_py.action_runtime import VoiceActionBridge
        from ipfs_accelerate_py.action_runtime.contracts import ActionDecisionKind
    except Exception as exc:  # pragma: no cover - optional package surface
        surface["status"] = "action_runtime_unavailable"
        surface["error"] = type(exc).__name__
        serialized["action"] = surface
        return serialized

    if catalog is None or policy is None or executor is None:
        catalog, policy, executor = build_default_action_stack()

    bridge = VoiceActionBridge(catalog=catalog)  # type: ignore[arg-type]
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
        return serialized

    surface["proposal"] = proposal.to_dict()
    decision = policy.decide(proposal)  # type: ignore[union-attr]
    surface["decision"] = decision.to_dict()
    surface["status"] = decision.kind.value

    confirm = _truthy(
        request_payload.get("confirm_action")
        if "confirm_action" in request_payload
        else request_payload.get("action_confirm")
    )
    execute_ok = is_voice_action_execute_enabled(execute_enabled)
    if confirm and execute_ok:
        # Explicit grant for this proposal only — never ambient authority.
        policy.grant(  # type: ignore[union-attr]
            proposal_id=proposal.proposal_id,
            kind=ActionDecisionKind.PERMIT_EXECUTE,
        )
        decision, receipt = executor.execute(proposal)  # type: ignore[union-attr]
        surface["decision"] = decision.to_dict()
        surface["receipt"] = receipt.to_dict()
        surface["status"] = (
            "executed"
            if str(receipt.status.value if hasattr(receipt.status, "value") else receipt.status)
            == "succeeded"
            else "execution_failed"
        )
    elif confirm and not execute_ok:
        surface["status"] = "execution_disabled"
        surface["error"] = (
            f"set {VOICE_ACTION_EXECUTE_FLAG}=1 to allow confirmed CLI execution"
        )
    else:
        # Default product path: speak the library response and ask for confirm.
        surface["status"] = decision.kind.value

    serialized["action"] = surface
    # camelCase alias for browser clients
    serialized["actionSurface"] = surface
    return serialized
