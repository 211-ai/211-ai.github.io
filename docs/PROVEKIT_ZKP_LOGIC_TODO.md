# ProveKit ZKP Logic Todo

This backlog is the executable implementation queue for
`docs/PROVEKIT_ZKP_LOGIC_IMPLEMENTATION_PLAN.md`.

The ProveKit implementation daemon can consume this file with:

```bash
python scripts/provekit_implementation_daemon.py --once --no-implement
```

For a foreground autonomous run that invokes implementation agents and exits
when all parsed tasks are complete, use:

```bash
python scripts/provekit_implementation_supervisor.py --implement --until-complete
```

For a long-running background service managed by the shared implementation
service manager, use:

```bash
python scripts/manage_implementation_services.py start provekit --implement
```

In a shared dirty checkout where follow-up tasks must build on uncommitted
agent work, run the same persistent background loop in-place:

```bash
python scripts/manage_implementation_services.py start provekit --implement --no-ephemeral-worktree
```

Priority guide:

- `P0`: foundation, safety, or production blocker work
- `P1`: required integration, bridge, cache, or test coverage work
- `P2`: performance, FFI, recursive/on-chain, or hardening follow-up
- `P3`: polish or optional refinement

Track guide:

- `platform`: logic, circuits, bridge contracts, and theorem-prover integration
- `runtime`: backend execution, subprocess/FFI, proof envelopes, and APIs
- `privacy`: witness boundaries, no-leak tests, public-input discipline
- `quality`: unit, integration, golden-vector, and regression coverage
- `ops`: build, packaging, availability, readiness, and signoff
- `wallet`: downstream wallet/verifier interoperability

## PROVEKIT-000 Control Plane And Backlog
- Status: completed
- Completion: artifact
- Priority: P0
- Track: ops
- Depends on: none
- Outputs: docs/PROVEKIT_ZKP_LOGIC_IMPLEMENTATION_PLAN.md, docs/PROVEKIT_ZKP_LOGIC_TODO.md
- Validation: test -f docs/PROVEKIT_ZKP_LOGIC_IMPLEMENTATION_PLAN.md; test -f docs/PROVEKIT_ZKP_LOGIC_TODO.md
- Acceptance: The ProveKit implementation plan and daemon-consumable backlog exist, use the `PROVEKIT-` task prefix, and can be parsed by the shared implementation daemon with a custom todo path and task prefix.

## PROVEKIT-010 Upstream ProveKit Spike And Pin
- Status: completed
- Completion: artifact
- Priority: P0
- Track: ops
- Depends on: PROVEKIT-000
- Outputs: artifacts/provekit-spike/README.md, artifacts/provekit-spike/provekit-v1-smoke.json
- Validation: test -f artifacts/provekit-spike/README.md; test -f artifacts/provekit-spike/provekit-v1-smoke.json
- Acceptance: A local ProveKit `v1` checkout or binary is identified, the upstream basic example has documented `prepare`, `prove`, and `verify` results, and the chosen ProveKit commit, binary path, proof size, key size, command syntax, and runtime measurements are recorded.

## PROVEKIT-020 Public Input And Canonicalization Contract Audit
- Status: completed
- Completion: artifact
- Priority: P0
- Track: quality
- Depends on: PROVEKIT-000
- Outputs: ipfs_datasets_py/ipfs_datasets_py/logic/zkp/provekit/public_inputs.py, ipfs_datasets_py/tests/unit_tests/logic/zkp/test_provekit_public_inputs.py
- Validation: pytest ipfs_datasets_py/tests/unit_tests/logic/zkp/test_provekit_public_inputs.py -q
- Acceptance: Existing theorem hash, axiom commitment, circuit ref, ruleset, compiler guidance, and attestation fields are mapped into ProveKit-compatible public input records without changing existing simulated or Groth16 public-input semantics.

## PROVEKIT-030 ProveKit CLI Wrapper Skeleton
- Status: completed
- Completion: artifact
- Priority: P0
- Track: runtime
- Depends on: PROVEKIT-010
- Outputs: ipfs_datasets_py/ipfs_datasets_py/logic/zkp/provekit/cli.py, ipfs_datasets_py/tests/unit_tests/logic/zkp/test_provekit_cli_wrapper.py
- Validation: pytest ipfs_datasets_py/tests/unit_tests/logic/zkp/test_provekit_cli_wrapper.py -q
- Acceptance: The CLI wrapper discovers ProveKit from explicit environment variables or package paths, builds `prepare`, `prove`, and `verify` subprocess commands, enforces timeouts, captures structured failures, and never logs witness content.

## PROVEKIT-040 Backend Registry And Fail-Closed Backend
- Status: completed
- Completion: artifact
- Priority: P0
- Track: runtime
- Depends on: PROVEKIT-030
- Outputs: ipfs_datasets_py/ipfs_datasets_py/logic/zkp/backends/provekit.py, ipfs_datasets_py/tests/unit_tests/logic/zkp/test_provekit_backend.py
- Validation: pytest ipfs_datasets_py/tests/unit_tests/logic/zkp/test_backend_selection.py ipfs_datasets_py/tests/unit_tests/logic/zkp/test_provekit_backend.py -q
- Acceptance: `get_backend("provekit")` and aliases instantiate a lazy fail-closed backend, unavailable binaries or missing artifacts raise `ZKPError`, and normal `ipfs_datasets_py.logic.api` imports remain quiet and deterministic.

## PROVEKIT-050 Artifact Manifest And Key Discovery
- Status: completed
- Completion: artifact
- Priority: P0
- Track: ops
- Depends on: PROVEKIT-030
- Outputs: ipfs_datasets_py/ipfs_datasets_py/logic/zkp/provekit/artifacts.py, ipfs_datasets_py/tests/unit_tests/logic/zkp/test_provekit_artifacts.py, ipfs_datasets_py/ipfs_datasets_py/processors/provekit_backend/README.md
- Validation: pytest ipfs_datasets_py/tests/unit_tests/logic/zkp/test_provekit_artifacts.py -q
- Acceptance: ProveKit `.pkp`, `.pkv`, Noir package, hash backend, branch, commit, and digest metadata are represented by a deterministic artifact manifest, and missing or mismatched key hashes fail closed.

## PROVEKIT-060 Knowledge-Of-Axioms Noir Circuit Package
- Status: completed
- Completion: artifact
- Priority: P0
- Track: platform
- Depends on: PROVEKIT-020, PROVEKIT-050
- Outputs: ipfs_datasets_py/ipfs_datasets_py/logic/zkp/provekit/circuits/knowledge_of_axioms/Nargo.toml, ipfs_datasets_py/ipfs_datasets_py/logic/zkp/provekit/circuits/knowledge_of_axioms/src/main.nr, ipfs_datasets_py/tests/unit_tests/logic/zkp/test_provekit_knowledge_of_axioms_circuit.py
- Validation: pytest ipfs_datasets_py/tests/unit_tests/logic/zkp/test_provekit_knowledge_of_axioms_circuit.py -q
- Acceptance: A first Noir circuit binds theorem hash, axiom commitment, circuit ref, circuit version, and ruleset ID for the knowledge-of-axioms proof family without asserting unbounded theorem derivability.

## PROVEKIT-070 Prover Witness Serializer And No-Leak Temp Handling
- Status: completed
- Completion: artifact
- Priority: P0
- Track: privacy
- Depends on: PROVEKIT-020, PROVEKIT-030, PROVEKIT-060
- Outputs: ipfs_datasets_py/ipfs_datasets_py/logic/zkp/provekit/witness.py, ipfs_datasets_py/tests/unit_tests/logic/zkp/test_provekit_witness_no_leak.py
- Validation: pytest ipfs_datasets_py/tests/unit_tests/logic/zkp/test_provekit_witness_no_leak.py -q
- Acceptance: Private axioms and derivation witnesses are rendered into ProveKit input files only inside private temporary directories, all temp files are cleaned up, and serialized proof, cache, logs, and exceptions contain no private axiom text.

## PROVEKIT-080 ProveKit Proof Envelope And Attestation Compatibility
- Status: completed
- Completion: artifact
- Priority: P0
- Track: runtime
- Depends on: PROVEKIT-040, PROVEKIT-070
- Outputs: ipfs_datasets_py/tests/unit_tests/logic/zkp/test_provekit_attestation_envelope.py
- Validation: pytest ipfs_datasets_py/tests/unit_tests/logic/zkp/test_provekit_attestation_envelope.py -q
- Acceptance: The ProveKit backend returns existing `ZKPProof` envelopes with `.np` proof bytes, public inputs, ProveKit metadata, size, timestamp, and a fresh attestation view that passes the existing attestation consistency checks.

## PROVEKIT-090 Real CLI Prepare-Prove-Verify Integration Gate
- Status: completed
- Completion: artifact
- Priority: P0
- Track: quality
- Depends on: PROVEKIT-040, PROVEKIT-050, PROVEKIT-060, PROVEKIT-070, PROVEKIT-080
- Outputs: ipfs_datasets_py/tests/integration/test_provekit_zkp.py, artifacts/provekit-integration/README.md
- Validation: pytest ipfs_datasets_py/tests/integration/test_provekit_zkp.py -q
- Acceptance: When `IPFS_DATASETS_RUN_PROVEKIT_TESTS=1` and a ProveKit binary is configured, the integration test prepares keys, generates a real proof, verifies it through ProveKit, serializes it through `ZKPProof`, and verifies that disabled or unavailable environments skip or fail closed as intended.

## PROVEKIT-100 TDFOL Trace Schema And Python Prevalidation
- Status: completed
- Completion: artifact
- Priority: P1
- Track: platform
- Depends on: PROVEKIT-020, PROVEKIT-090
- Outputs: ipfs_datasets_py/ipfs_datasets_py/logic/zkp/provekit/trace.py, ipfs_datasets_py/tests/unit_tests/logic/zkp/test_provekit_tdfol_trace_schema.py
- Validation: pytest ipfs_datasets_py/tests/unit_tests/logic/zkp/test_provekit_tdfol_trace_schema.py -q
- Acceptance: A bounded TDFOL trace witness schema is defined, Python-side validation rejects non-derivable traces before proving, and the schema reuses existing canonicalization and `TDFOL_v1` semantics.

## PROVEKIT-110 TDFOL V1 Trace Noir Circuit
- Status: completed
- Completion: artifact
- Priority: P1
- Track: platform
- Depends on: PROVEKIT-100
- Outputs: ipfs_datasets_py/ipfs_datasets_py/logic/zkp/provekit/circuits/tdfol_v1_trace/Nargo.toml, ipfs_datasets_py/ipfs_datasets_py/logic/zkp/provekit/circuits/tdfol_v1_trace/src/main.nr, ipfs_datasets_py/tests/unit_tests/logic/zkp/test_provekit_tdfol_trace_circuit.py
- Validation: pytest ipfs_datasets_py/tests/unit_tests/logic/zkp/test_provekit_tdfol_trace_circuit.py -q
- Acceptance: The Noir trace circuit proves bounded fact and implication/modus-ponens derivation traces against public theorem and axiom commitments, and invalid traces fail before proof generation or fail verification.

## PROVEKIT-120 ZKP Attestation Bridge ProveKit Wiring
- Status: completed
- Completion: artifact
- Priority: P1
- Track: platform
- Depends on: PROVEKIT-080, PROVEKIT-110
- Outputs: ipfs_datasets_py/tests/unit_tests/logic/zkp/test_provekit_zkp_attestation_bridge.py
- Validation: pytest ipfs_datasets_py/tests/unit_tests/logic/zkp/test_provekit_zkp_attestation_bridge.py -q
- Acceptance: `ZkpAttestationBridgeAdapter(prover_kwargs={"backend": "provekit"})` emits verified LegalIR ZKP attestation records, public inputs, proof-gate details, and graph triples while preserving the existing bridge output shape.

## PROVEKIT-130 Hybrid TDFOL CEC And F-Logic Compatibility
- Status: todo
- Completion: artifact
- Priority: P1
- Track: platform
- Depends on: PROVEKIT-120
- Outputs: ipfs_datasets_py/tests/unit_tests/logic/zkp/test_provekit_hybrid_provers.py
- Validation: pytest ipfs_datasets_py/tests/unit_tests/logic/zkp/test_provekit_hybrid_provers.py -q
- Acceptance: `ZKPTDFOLProver`, `ZKPCECProver`, and `ZKPFLogicProver` can select `zkp_backend="provekit"` through their existing constructors, verify generated proof envelopes, and retain standard proving fallback behavior where allowed.

## PROVEKIT-140 Deontic LegalNormIR Guidance Commitments
- Status: todo
- Completion: artifact
- Priority: P1
- Track: privacy
- Depends on: PROVEKIT-120
- Outputs: ipfs_datasets_py/tests/unit_tests/logic/deontic/test_deontic_provekit_bridge.py
- Validation: pytest ipfs_datasets_py/tests/unit_tests/logic/deontic/test_deontic_provekit_bridge.py -q
- Acceptance: Deontic `LegalNormIR`, parser capability records, prover syntax readiness, and repair/compiler guidance metadata flow into stable public commitments and `compiler_guidance_ref` fields without exposing private legal text or parser witness data.

## PROVEKIT-150 Proof Cache And IPFS Public Payload Hardening
- Status: todo
- Completion: artifact
- Priority: P1
- Track: privacy
- Depends on: PROVEKIT-080, PROVEKIT-120
- Outputs: ipfs_datasets_py/tests/unit_tests/logic/zkp/test_provekit_cache_ipfs_payloads.py
- Validation: pytest ipfs_datasets_py/tests/unit_tests/logic/zkp/test_provekit_cache_ipfs_payloads.py -q
- Acceptance: Proof cache keys include ProveKit backend ID, circuit ref, hash backend, verifier-key digest, ProveKit commit, and ruleset; IPFS/cache payloads contain only public proof envelopes and artifact references.

## PROVEKIT-160 Optional Dependency Packaging And Build Script
- Status: todo
- Completion: artifact
- Priority: P1
- Track: ops
- Depends on: PROVEKIT-050, PROVEKIT-090
- Outputs: ipfs_datasets_py/ipfs_datasets_py/processors/provekit_backend/build.sh, ipfs_datasets_py/tests/unit_tests/logic/zkp/test_provekit_optional_dependencies.py
- Validation: pytest ipfs_datasets_py/tests/unit_tests/logic/zkp/test_provekit_optional_dependencies.py -q
- Acceptance: A `provekit` optional dependency/build path is documented and test-covered, package data rules cover approved backend assets, and no Rust build, network clone, or artifact preparation runs at import time.

## PROVEKIT-170 Ops Readiness And Backend Health Checks
- Status: todo
- Completion: artifact
- Priority: P1
- Track: ops
- Depends on: PROVEKIT-150, PROVEKIT-160
- Outputs: docs/PROVEKIT_ZKP_OPERATIONS.md, ipfs_datasets_py/tests/unit_tests/logic/zkp/test_provekit_backend_health.py
- Validation: pytest ipfs_datasets_py/tests/unit_tests/logic/zkp/test_provekit_backend_health.py -q; test -f docs/PROVEKIT_ZKP_OPERATIONS.md
- Acceptance: Operators can check ProveKit binary availability, artifact integrity, circuit manifests, backend enablement, and fail-closed readiness from documented commands without exposing witness material.

## PROVEKIT-180 Golden Vector And Property Test Suite
- Status: todo
- Completion: artifact
- Priority: P1
- Track: quality
- Depends on: PROVEKIT-060, PROVEKIT-110, PROVEKIT-140
- Outputs: ipfs_datasets_py/tests/unit_tests/logic/zkp/provekit_golden_vectors.json, ipfs_datasets_py/tests/unit_tests/logic/zkp/test_provekit_golden_vectors.py, ipfs_datasets_py/tests/unit_tests/logic/zkp/test_provekit_properties.py
- Validation: pytest ipfs_datasets_py/tests/unit_tests/logic/zkp/test_provekit_golden_vectors.py ipfs_datasets_py/tests/unit_tests/logic/zkp/test_provekit_properties.py -q
- Acceptance: Golden vectors cover theorem canonicalization, axiom commitments, Prover.toml rendering, public inputs, attestation refs, and verifier-key digests; property tests cover determinism and failure cases.

## PROVEKIT-190 ProveKit FFI Feasibility And Wrapper Prototype
- Status: todo
- Completion: artifact
- Priority: P2
- Track: runtime
- Depends on: PROVEKIT-090, PROVEKIT-160
- Outputs: ipfs_datasets_py/ipfs_datasets_py/logic/zkp/backends/provekit_ffi.py, ipfs_datasets_py/tests/unit_tests/logic/zkp/test_provekit_ffi_wrapper.py
- Validation: pytest ipfs_datasets_py/tests/unit_tests/logic/zkp/test_provekit_ffi_wrapper.py -q
- Acceptance: A ctypes wrapper prototypes `pk_init`, memory configuration, prover/verifier loading, proving, verification, error retrieval, and buffer cleanup behind a process-local lock, while CLI remains the default production path.

## PROVEKIT-200 Recursive Gnark And On-Chain Evaluation
- Status: todo
- Completion: artifact
- Priority: P2
- Track: wallet
- Depends on: PROVEKIT-090
- Outputs: docs/PROVEKIT_RECURSIVE_ONCHAIN_EVALUATION.md, ipfs_datasets_py/tests/unit_tests/logic/zkp/test_provekit_recursive_export_contract.py
- Validation: test -f docs/PROVEKIT_RECURSIVE_ONCHAIN_EVALUATION.md; pytest ipfs_datasets_py/tests/unit_tests/logic/zkp/test_provekit_recursive_export_contract.py -q
- Acceptance: The team has a documented decision on ProveKit recursive verifier/Gnark export, whether it should integrate with the existing Groth16/EVM verifier path, and which tests are required before any on-chain ProveKit route is production-exposed.

## PROVEKIT-210 Security Review And Threat Model
- Status: todo
- Completion: artifact
- Priority: P1
- Track: privacy
- Depends on: PROVEKIT-150, PROVEKIT-170
- Outputs: docs/PROVEKIT_ZKP_SECURITY_NOTES.md
- Validation: test -f docs/PROVEKIT_ZKP_SECURITY_NOTES.md
- Acceptance: The security notes distinguish simulated, Groth16, ProveKit WHIR, and future recursive wrapper claims; document no-leak boundaries, artifact trust, cache/IPFS risks, verifier-key rotation, failure modes, and production cutover requirements.

## PROVEKIT-220 End-To-End ProveKit ZKP Signoff
- Status: todo
- Completion: evidence
- Priority: P0
- Track: ops
- Depends on: PROVEKIT-130, PROVEKIT-140, PROVEKIT-150, PROVEKIT-170, PROVEKIT-180, PROVEKIT-210
- Outputs: docs/PROVEKIT_ZKP_TARGET_SIGNOFF.md, artifacts/provekit-release-checks/results.json
- Validation: pytest ipfs_datasets_py/tests/unit_tests/logic/zkp -q; pytest ipfs_datasets_py/tests/unit_tests/logic/deontic/test_deontic_provekit_bridge.py -q; test -f docs/PROVEKIT_ZKP_TARGET_SIGNOFF.md
- Acceptance: A target environment demonstrates real ProveKit proof generation and verification for supported circuits, bridge integration, hybrid prover selection, deontic guidance commitments, cache/IPFS public payload safety, and documented rollback/readiness evidence.
