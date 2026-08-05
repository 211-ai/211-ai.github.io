"""Adversarial e2e: never_voice and staff_only deny without mutation (VAS-026)."""

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

TENANT = "tenant-vas-adv"
NEG = (
    REPO_ROOT
    / "data"
    / "voice_app_surface_coverage"
    / "variants"
    / "negatives-staff-never.jsonl"
)


@pytest.fixture()
def binding():
    return build_wallet_app_binding(
        surface_api=InMemoryAppSurfaceApi(), require_confirm=True
    )


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
        source="vas_e2e_adv",
        confidence=0.99,
        tenant_id=TENANT,
        session_id="sess-adv",
        channel="voice",
    )


def test_matrix_classes_deny_on_client_voice(binding):
    desc = logical_action_to_descriptor_id()
    policy = PilotPolicy(catalog=build_pilot_catalog())
    session = _session()
    for surface_id, klass in SURFACE_EXPOSURE_CLASS.items():
        if klass not in {"never_voice", "staff_only", "voice_read_only"}:
            continue
        err = surface_exposure_error(surface_id, channel="voice")
        assert err is not None, surface_id
        prop = _prop(desc, surface_id)
        decision = policy.decide(
            prop,
            PilotAdmissionContext(
                confirmed=True, authenticated=True, session_tenant_id=TENANT
            ),
        )
        assert decision.permits_execution
        receipt = binding.invoke(proposal=prop, decision=decision, session=session)
        assert receipt.status is ActionStatus.DENIED, surface_id
        assert receipt.error in {
            "surface_never_voice",
            "surface_staff_only",
            "surface_voice_read_only",
        }
    assert binding.list_opened(tenant_id=TENANT) == ()


def test_negative_lattice_targets_are_denied(binding):
    assert NEG.is_file()
    desc = logical_action_to_descriptor_id()
    policy = PilotPolicy(catalog=build_pilot_catalog())
    session = _session()
    checked = 0
    for line in NEG.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if not row.get("expected_deny"):
            continue
        sid = row.get("surface_id")
        if not sid or sid == "none":
            continue
        prop = _prop(desc, sid)
        decision = policy.decide(
            prop,
            PilotAdmissionContext(
                confirmed=True, authenticated=True, session_tenant_id=TENANT
            ),
        )
        receipt = binding.invoke(proposal=prop, decision=decision, session=session)
        assert receipt.status is ActionStatus.DENIED, (sid, row["user_text"])
        checked += 1
    assert checked >= 10
    assert binding.list_opened(tenant_id=TENANT) == ()


def test_injection_cannot_invent_descriptor():
    """Unknown logical actions are not in the pilot map; policy denies unknown descriptors."""
    desc = logical_action_to_descriptor_id()
    assert "rm_rf_home" not in desc
    catalog = build_pilot_catalog()
    policy = PilotPolicy(catalog=catalog)
    prop = ActionProposal(
        proposal_id="prop-inject",
        descriptor_id="voice.python.not_real.v1",
        logical_action="open_app_surface",  # legal name, unknown descriptor id
        arguments={"surface_id": "home"},
        route="app_surface_navigation",
        source="evil",
        confidence=1.0,
        tenant_id=TENANT,
    )
    decision = policy.decide(
        prop,
        PilotAdmissionContext(
            confirmed=True, authenticated=True, session_tenant_id=TENANT
        ),
    )
    assert decision.permits_execution is False
    assert decision.kind.value == "deny"
