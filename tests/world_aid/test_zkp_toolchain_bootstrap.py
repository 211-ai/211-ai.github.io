"""NOT APPROVED: future, explicitly guarded WORLDCOIN-G039 native ZKP runtime contract.

This file is deliberately present before selection so the signed Gate 0B-selection
record can bind its exact bytes. G041 never executes it. Human approval and
repository-controlled environment markers are necessary but are not a trusted
execution boundary. G039 remains blocked until an operator-controlled,
Gate-first supervisor launcher authenticates the exact entrypoint and verifier
before any repository Python runs. That launcher must enforce descriptor-backed
immutable inputs, process-group time/resource/output bounds, network and
registry denial, and an atomic no-follow receipt. The implementation below
contains only the contract checks; a later G039 owner supplies the injected
native tool runner after that launcher exists. The smoke result is not
production trust.
"""

from __future__ import annotations

import os
from pathlib import Path

from scripts.verify_world_aid_zkp_toolchain import verify_world_aid_zkp_toolchain

ROOT = Path(__file__).resolve().parents[2]
TRUSTED_GATE_FIRST_LAUNCHER_IMPLEMENTED = False


def _require_g039_environment() -> None:
    assert os.environ.get("WORLD_AID_G039_REAL_EXECUTION") == "1", (
        "WORLDCOIN-G039 real execution was not explicitly requested; absent or skipped execution fails closed"
    )
    assert os.environ.get("WORLD_AID_G039_GATE_FIRST_ATTESTED") == "1", "G039 requires a Gate-first launcher attestation"
    assert os.environ.get("WORLD_AID_G039_NETWORK_DENIED") == "1", "G039 requires network and registry denial"
    assert os.environ.get("WORLD_AID_G039_RESOURCE_BOUNDS") == "1", "G039 requires signed resource bounds"
    assert os.environ.get("WORLD_AID_GATE_0B_ALLOWED_SIGNERS"), "G039 requires external Gate 0B signer trust"


def _run_approved_native_smoke() -> dict[str, object]:
    """Reserved G039 handoff; G041 must never call this function."""
    raise AssertionError(
        "G039 native runner is an operator-owned execution handoff; no backend is selected in G041"
    )


def test_zkp_toolchain_runtime_contract_fails_closed_without_g039_authority() -> None:
    if TRUSTED_GATE_FIRST_LAUNCHER_IMPLEMENTED is not True:
        raise AssertionError(
            "G039 remains blocked: an operator-controlled Gate-first supervisor launcher has not been implemented"
        )
    _require_g039_environment()
    selected = verify_world_aid_zkp_toolchain(
        ROOT,
        approval=Path("data/worldcoin_human_aid/approvals/gate-0b-selection/approval.json"),
        allowed_signers=Path(os.environ["WORLD_AID_GATE_0B_ALLOWED_SIGNERS"]),
        require_approval=True,
    )
    assert selected.execution_owner == "G039"
    assert selected.architecture in {"x86_64", "aarch64"}
    assert selected.tool_digest is not None
    assert selected.proposal_digest is not None
    assert selected.static_test_digest is not None
    assert selected.verifier_digest is not None
    assert selected.runtime_test_digest is not None
    assert selected.smoke_spec_digest is not None
    assert selected.smoke_toml_digest is not None
    assert selected.smoke_source_digest is not None
    assert selected.smoke_lock_digest is not None
    evidence = _run_approved_native_smoke()
    required = {"repeat_build_hashes", "proof_result", "verify_result", "network_registry_denied", "resource_bounds", "expiry"}
    assert required <= set(evidence)
    assert evidence["repeat_build_hashes"][0] == evidence["repeat_build_hashes"][1]
    assert evidence["proof_result"] is True and evidence["verify_result"] is True
    assert evidence["network_registry_denied"] is True
    assert evidence["production_trust"] is False
