"""DAG expansion sample simulation (VAS-027)."""

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

EXPANSION = REPO_ROOT / "data" / "voice_app_surface_coverage" / "dag_expansion"
TENANT = "tenant-dag-sim"


def _samples(route_file: str, n: int = 3) -> list[dict]:
    path = EXPANSION / route_file
    assert path.is_file(), path
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rows.append(json.loads(line))
        if len(rows) >= n:
            break
    return rows


@pytest.mark.parametrize(
    "route_file,logical,args_builder",
    [
        (
            "route-app_surface_navigation.exemplars.jsonl",
            "open_app_surface",
            lambda e: {"surface_id": e.get("surface_id") or "home"},
        ),
        (
            "home.exemplars.jsonl",
            "open_app_surface",
            lambda e: {"surface_id": "home"},
        ),
    ],
)
def test_expansion_samples_confirm_execute(route_file, logical, args_builder):
    catalog = build_pilot_catalog()
    policy = PilotPolicy(catalog=catalog)
    desc = logical_action_to_descriptor_id()
    binding = build_wallet_app_binding(
        surface_api=InMemoryAppSurfaceApi(), require_confirm=True
    )
    session = WalletAppSession(
        tenant_id=TENANT,
        authenticated=True,
        confirmed=True,
        client_id="client-abby",
        session_id="sess-dag-sim",
        channel="voice",
    )
    for ex in _samples(route_file):
        args = args_builder(ex)
        prop = ActionProposal(
            proposal_id=f"prop-sim-{ex['id'][:12]}",
            descriptor_id=desc[logical],
            logical_action=logical,
            arguments={k: str(v) for k, v in args.items()},
            route=ex.get("route") or "app_surface_navigation",
            source="dag_expansion",
            confidence=0.99,
            tenant_id=TENANT,
            session_id="sess-dag-sim",
            channel="voice",
        )
        d0 = policy.decide(
            prop, PilotAdmissionContext(confirmed=False, authenticated=False)
        )
        assert not d0.permits_execution
        d1 = policy.decide(
            prop,
            PilotAdmissionContext(
                confirmed=True, authenticated=True, session_tenant_id=TENANT
            ),
        )
        assert d1.permits_execution
        receipt = binding.invoke(proposal=prop, decision=d1, session=session)
        assert receipt.status is ActionStatus.SUCCEEDED, receipt.to_dict()
