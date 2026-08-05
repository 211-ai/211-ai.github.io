"""Offline e2e: P0 surface paraphrases -> proposal -> confirm -> fake adapter (VAS-025)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
for _c in (REPO_ROOT, REPO_ROOT / "ipfs_accelerate_py", REPO_ROOT / "ipfs_datasets_py"):
    p = str(_c)
    if _c.is_dir() and p not in sys.path:
        sys.path.insert(0, p)

from ipfs_accelerate_py.action_runtime.adapters.calendar import (  # noqa: E402
    CalendarActionAdapter,
    CalendarInvocationContext,
    InMemoryCalendarEventStore,
    default_calendar_registrations,
)
from ipfs_accelerate_py.action_runtime.catalog_211ai import (  # noqa: E402
    build_pilot_catalog,
    logical_action_to_descriptor_id,
)
from ipfs_accelerate_py.action_runtime.contracts import (  # noqa: E402
    ActionDecisionKind,
    ActionProposal,
    ActionStatus,
)
from ipfs_accelerate_py.action_runtime.outcome_speech import select_outcome_speech  # noqa: E402
from ipfs_accelerate_py.action_runtime.policy_pilot import (  # noqa: E402
    PilotAdmissionContext,
    PilotPolicy,
)
from wallet_interface.helpers._voice_app_action_binding import (  # noqa: E402
    InMemoryAppSurfaceApi,
    WalletAppSession,
    build_wallet_app_binding,
)
from wallet_interface.helpers._voice_surface_exposure import surface_exposure_error  # noqa: E402

VARIANTS = REPO_ROOT / "data" / "voice_app_surface_coverage" / "variants"
TENANT = "tenant-vas-e2e"
SESSION = "sess-vas-e2e"
P0 = [
    "home",
    "check-in",
    "calendar",
    "messages",
    "contacts",
    "social-services",
    "interactions",
    "uploads",
    "settings",
]
PARAPHRASES_PER = 5


def _load_paraphrases(surface_id: str, n: int = PARAPHRASES_PER) -> list[str]:
    path = VARIANTS / f"{surface_id}.jsonl"
    assert path.is_file(), path
    out: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("negative"):
            continue
        out.append(row["user_text"])
        if len(out) >= n:
            break
    assert len(out) >= n, (surface_id, len(out))
    return out


@pytest.fixture()
def stack():
    catalog = build_pilot_catalog()
    policy = PilotPolicy(catalog=catalog)
    desc = logical_action_to_descriptor_id()
    app = build_wallet_app_binding(
        surface_api=InMemoryAppSurfaceApi(), require_confirm=True
    )
    cal_store = InMemoryCalendarEventStore()
    calendar = CalendarActionAdapter(default_calendar_registrations(), store=cal_store)
    return {
        "catalog": catalog,
        "policy": policy,
        "desc": desc,
        "app": app,
        "calendar": calendar,
    }


def _decide(policy, proposal, *, confirmed: bool, authenticated: bool = True):
    return policy.decide(
        proposal,
        PilotAdmissionContext(
            confirmed=confirmed,
            authenticated=authenticated,
            session_tenant_id=TENANT if authenticated or confirmed else None,
        ),
    )


def _proposal(desc_map, surface_id: str, user: str, logical: str, arguments: dict):
    return ActionProposal(
        proposal_id=f"prop-vas-{surface_id}-{abs(hash(user)) % 10**6:06d}",
        descriptor_id=desc_map[logical],
        logical_action=logical,
        arguments={k: str(v) for k, v in arguments.items()},
        route="app_surface_navigation" if logical == "open_app_surface" else "calendar_event_support",
        source="vas_e2e_surface_matrix",
        confidence=0.99,
        tenant_id=TENANT,
        session_id=SESSION,
        channel="voice",
        evidence=(),
        metadata={"transcript_sha_prefix": user[:32], "surface_id": surface_id},
    )


@pytest.mark.parametrize("surface_id", P0)
def test_p0_surface_paraphrases_open_or_read(stack, surface_id: str):
    assert surface_exposure_error(surface_id, channel="voice") is None
    texts = _load_paraphrases(surface_id)
    session = WalletAppSession(
        tenant_id=TENANT,
        authenticated=True,
        confirmed=True,
        client_id="client-abby",
        session_id=SESSION,
        channel="voice",
    )
    for user in texts:
        if surface_id == "calendar" and "calendar" in user.lower():
            # exercise read_calendar for calendar-ish paraphrases
            logical = "read_calendar"
            args = {"limit": "5"}
            prop = _proposal(stack["desc"], surface_id, user, logical, args)
            d0 = _decide(stack["policy"], prop, confirmed=False)
            assert d0.kind is ActionDecisionKind.CONFIRM
            d1 = _decide(stack["policy"], prop, confirmed=True, authenticated=True)
            assert d1.permits_execution
            receipt = stack["calendar"].invoke(
                proposal=prop,
                decision=d1,
                context=CalendarInvocationContext(
                    confirmed=True,
                    authenticated=True,
                    session_tenant_id=TENANT,
                ),
            )
        else:
            logical = "open_wallet_documents" if surface_id == "uploads" else "open_app_surface"
            args = {} if logical == "open_wallet_documents" else {"surface_id": surface_id}
            prop = _proposal(stack["desc"], surface_id, user, logical, args)
            d0 = _decide(stack["policy"], prop, confirmed=False)
            assert d0.kind is ActionDecisionKind.CONFIRM
            d1 = _decide(stack["policy"], prop, confirmed=True, authenticated=True)
            assert d1.permits_execution
            receipt = stack["app"].invoke(
                proposal=prop, decision=d1, session=session
            )
        assert receipt.status is ActionStatus.SUCCEEDED, (surface_id, user, receipt.to_dict())
        spoken = select_outcome_speech(
            logical_action=prop.logical_action, receipt=receipt, library=None
        )
        assert spoken.outcome_role == "success"
        assert spoken.spoken_text


def test_what_is_on_my_calendar_path(stack):
    user = "What is on my calendar?"
    prop = _proposal(
        stack["desc"], "calendar", user, "read_calendar", {"limit": "5"}
    )
    d1 = _decide(stack["policy"], prop, confirmed=True, authenticated=True)
    receipt = stack["calendar"].invoke(
        proposal=prop,
        decision=d1,
        context=CalendarInvocationContext(
            confirmed=True, authenticated=True, session_tenant_id=TENANT
        ),
    )
    assert receipt.status is ActionStatus.SUCCEEDED
