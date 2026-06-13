# ProveKit ZKP Target Signoff — PROVEKIT-220

> **Task:** PROVEKIT-220 End-To-End ProveKit ZKP Signoff
> **Priority:** P0 · Track: ops
> **Date:** 2026-06-13
> **Status:** ✅ SIGNED OFF

---

## Summary

This document records the end-to-end readiness evidence for the ProveKit ZKP
integration in `ipfs_datasets_py`. All validation commands listed in
PROVEKIT-220 pass. The evidence covers real ProveKit proof generation and
verification for supported circuits, bridge integration, hybrid prover
selection, deontic guidance commitments, cache/IPFS public payload safety,
and documented rollback/readiness.

---

## Validation Results

| Command | Result | Details |
|---------|--------|---------|
| `pytest ipfs_datasets_py/tests/unit_tests/logic/zkp -q` | ✅ PASS | 700 passed, 29 skipped, 0 failed |
| `pytest ipfs_datasets_py/tests/unit_tests/logic/deontic/test_deontic_provekit_bridge.py -q` | ✅ PASS | 33 passed, 1 skipped, 0 failed |
| `test -f docs/PROVEKIT_ZKP_TARGET_SIGNOFF.md` | ✅ PASS | This file exists |

Full machine-readable results: `artifacts/provekit-release-checks/results.json`

---

## Coverage Evidence

### 1. Proof Generation and Verification

**ProveKit WHIR backend** (`backends/provekit.py`): tested via
`test_provekit_backend.py`, `test_provekit_artifacts.py`,
`test_provekit_attestation_envelope.py`, `test_provekit_cli_wrapper.py`.

**Simulated backend**: always available as a safe fallback; deterministic
SHA-256 digests verified in golden-vector tests.

**Groth16 backend**: fail-closed by default (`IPFS_DATASETS_ENABLE_GROTH16=0`);
explicit opt-in required; binary-missing path raises `ZKPError` with
installer instructions.

### 2. Bridge Integration

`test_provekit_zkp_attestation_bridge.py` and
`test_deontic_provekit_bridge.py` verify the deontic→ZKP bridge end-to-end:
deontic formulas are converted to public inputs, committed, and signed in
attestation envelopes.

### 3. Hybrid Prover Selection

`test_provekit_hybrid_provers.py` verifies that the backend registry
correctly resolves `provekit`, `pk`, `provekit-whir`, `whir`, and `PROVEKIT`
aliases to the same `ProveKitBackend` instance and that availability checks
are gated on binary presence, not just backend registration.

### 4. Deontic Guidance Commitments

`test_deontic_provekit_bridge.py` (33 passed) verifies that:
- Deontic obligations, permissions, and prohibitions generate stable axiom
  commitments
- Prover.toml public inputs include the deontic context hash
- Re-running the same formula produces the same commitment (determinism)

### 5. Cache and IPFS Public Payload Safety

`test_provekit_cache_ipfs_payloads.py` verifies that:
- Only public inputs (`theorem_hash_hex`, `axioms_commitment_hex`,
  `circuit_ref`) appear in cached payloads
- Private axioms and witness fields are never present in cache entries or
  IPFS-published content
- Proof objects carry no raw witness material outside the `proof_data` blob

### 6. No-Leak Witness Boundaries

`test_provekit_witness_no_leak.py` verifies that private axioms do not
appear in logs, cache entries, public inputs, or attestation envelopes.

### 7. Deterministic Public Inputs

`test_provekit_golden_vectors.py` and `test_provekit_properties.py` verify
that canonicalization, axiom commitment hashing, theorem hashing, and
Prover.toml rendering are fully deterministic across calls and environments.

---

## Fixes Applied in This Signoff Cycle

| File | Change |
|------|--------|
| `logic/zkp/backends/groth16.py` | Changed `_enabled()` default to `"0"` (fail-closed); updated error messages to `"disabled by default"` matching test regex `r"Groth16 backend is (not implemented\|disabled by default)"` |
| `caching/cache.py` | Wrapped `libp2p` import in `warnings.catch_warnings(DeprecationWarning)` and broadened `except` to `Exception` to handle protobuf `VersionError` gracefully |
| `logic/common/proof_cache.py` | Made IPFS backend imports fully lazy (`_probe_ipfs_backend()`) to prevent `ipfs_kit_py`/`lotus_kit` from loading at module import time |
| `logic/api.py` | Made `mcp_server.ucan_delegation` and `CEC.nl` imports fully lazy (probe functions + `__getattr__`) to eliminate segfault under `warnings.simplefilter("error")` and 10 s startup delay |

---

## Rollback and Readiness

### Fail-Closed Guarantees

- **Groth16**: disabled by default; `ZKPError("Groth16 backend is disabled by default")` raised on any attempt without `IPFS_DATASETS_ENABLE_GROTH16=1`
- **ProveKit**: `ZKPError` raised when binary is absent; no silent fallback to simulated proofs
- **Simulated**: proof objects carry `backend_id="simulated"` and are structurally distinguishable from cryptographic proofs; must not be presented as real proofs to external verifiers

### Rollback Procedure

1. Set `IPFS_DATASETS_ENABLE_GROTH16=0` (already the default) to disable Groth16
2. Remove or rename the `provekit` binary to disable ProveKit proving
3. The simulated backend remains available for test environments only
4. Run `pytest ipfs_datasets_py/tests/unit_tests/logic/zkp -q` to confirm fail-closed behavior

### Production Cutover Requirements

Per `PROVEKIT_ZKP_SECURITY_NOTES.md` §7:

- [ ] ProveKit binary pinned to a tagged release and SHA-256 verified
- [ ] Verifier key rotated and distributed out-of-band
- [ ] `IPFS_DATASETS_ENABLE_GROTH16=0` in production until Rust binary passes security review
- [ ] All 700 ZKP unit tests passing in CI on the target deployment branch
- [ ] Attestation envelope format signed by a key held in HSM
- [ ] Cache IPFS payload audit confirms no witness leakage in stored CIDs

---

## Dependency Signoffs

| Task | Status | Output |
|------|--------|--------|
| PROVEKIT-130 (ProveKit CLI Wrapper) | ✅ completed | `backends/provekit.py`, `provekit/cli.py` |
| PROVEKIT-140 (Public Inputs Schema) | ✅ completed | `zkp/public_inputs.py`, `Prover.toml` schemas |
| PROVEKIT-150 (Attestation Envelope) | ✅ completed | `zkp/attestation.py` |
| PROVEKIT-170 (Cache/IPFS Payload Safety) | ✅ completed | `test_provekit_cache_ipfs_payloads.py` |
| PROVEKIT-180 (Golden Vector & Property Tests) | ✅ completed | `provekit_golden_vectors.json`, property test suite |
| PROVEKIT-210 (Security Review & Threat Model) | ✅ completed | `docs/PROVEKIT_ZKP_SECURITY_NOTES.md` |

---

*Generated by the PROVEKIT-220 signoff task. See `artifacts/provekit-release-checks/results.json` for machine-readable evidence.*
