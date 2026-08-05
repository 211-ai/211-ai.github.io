"""Adversarial e2e: never_voice and staff_only deny without mutation (VAS2-031)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
for _c in (REPO_ROOT, REPO_ROOT / "ipfs_accelerate_py"):
    p = str(_c)
    if _c.is_dir() and p not in sys.path:
        sys.path.insert(0, p)

from ipfs_accelerate_py.action_runtime.catalog_211ai import (  # noqa: E402
    build_pilot_catalog,
    logical_action_to_descriptor_id,
)
from ipfs_accelerate_py.action_runtime.contracts import (  # noqa: E402
    ActionDecisionKind,
    ActionProposal,
    ActionStatus,
)
from ipfs_accelerate_py.action_runtime.policy_pilot import (  # noqa: E402
    PilotAdmissionContext,
    PilotPolicy,
)

from wallet_interface.helpers._voice_app_action_binding import (  # noqa: E402
    InMemoryAppSurfaceApi,
    WalletAppSession,
    build_wallet_app_binding,
)
from wallet_interface.helpers._voice_surface_exposure import (  # noqa: E402
    SURFACE_EXPOSURE_CLASS,
    surface_exposure_error,
)

TENANT = "tenant-vas2-adv"
REPORTS = REPO_ROOT / "data" / "voice_app_surface_full_coverage" / "reports"


@pytest.fixture()
def binding():
    return build_wallet_app_binding(
        surface_api=InMemoryAppSurfaceApi(), require_confirm=True
    )


@pytest.fixture()
def policy():
    return PilotPolicy(catalog=build_pilot_catalog())


def _session():
    return WalletAppSession(
        tenant_id=TENANT,
        authenticated=True,
        confirmed=True,
        client_id="client-abby",
        session_id="sess-adv",
        channel="voice",
    )


def _prop(desc, surface_id: str):
    return ActionProposal(
        proposal_id=f"prop-adv-{surface_id}",
        descriptor_id=desc["open_app_surface"],
        logical_action="open_app_surface",
        arguments={"surface_id": surface_id},
        route="app_surface_navigation",
        source="vas2_e2e_adv",
        confidence=0.99,
        tenant_id=TENANT,
        session_id="sess-adv",
        channel="voice",
    )


def test_exposure_gate_denies_never_voice_and_staff_only(binding):
    session = _session()
    denied = []
    for surface_id, klass in SURFACE_EXPOSURE_CLASS.items():
        if klass not in {"never_voice", "staff_only", "voice_read_only"}:
            continue
        err = surface_exposure_error(surface_id, channel="voice")
        assert err is not None, surface_id
        desc = logical_action_to_descriptor_id()
        proposal = _prop(desc, surface_id)
        # binding deny path: build permit decision still denied by exposure in invoke
        from wallet_interface.tests.test_voice_app_action_binding import (
            build_permit_decision,
        )

        receipt = binding.invoke(
            proposal=proposal,
            decision=build_permit_decision(proposal),
            session=session,
        )
        assert receipt.status is ActionStatus.DENIED, (surface_id, receipt.error)
        denied.append({"surface_id": surface_id, "class": klass, "error": receipt.error})
    assert denied
    assert binding.list_opened(tenant_id=TENANT) == ()
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "e2e-adversarial.json").write_text(
        json.dumps(
            {
                "schema": "voice-app-surface-full-coverage/e2e-adversarial@1",
                "program_id": "voice-app-surface-full-coverage-v2",
                "denied_count": len(denied),
                "denied": denied,
                "status": "green",
            },
            indent=2,
        )
        + "\n"
    )


def test_policy_denies_never_voice_before_confirm(policy):
    desc = logical_action_to_descriptor_id()
    for surface_id, klass in SURFACE_EXPOSURE_CLASS.items():
        if klass != "never_voice":
            continue
        proposal = _prop(desc, surface_id)
        decision = policy.decide(
            proposal, PilotAdmissionContext(confirmed=True, authenticated=True)
        )
        assert decision.kind is ActionDecisionKind.DENY
        assert decision.reason == "surface_never_voice"
