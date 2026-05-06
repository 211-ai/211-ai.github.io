# UCAN ZK Data Wallet Todo

This backlog is the executable implementation queue for
`docs/UCAN_ZK_DATA_WALLET_IMPLEMENTATION_PLAN.md`.

The wallet implementation daemon parses tasks with the heading format
`## WALLET-...` and the metadata bullets directly below each heading. The
daemon and supervisor are thin `211-AI` wrappers around
`ipfs_datasets_py.optimizers.todo_daemon`, so task execution, state files,
strategy rewrites, restart policy, and implementation validation use the shared
optimizer todo-daemon stack.

Priority guide:

- `P0`: foundation, safety, or target-production blocker work
- `P1`: user-visible wallet, sharing, storage, or service-matching work
- `P2`: adjacent hardening, interop, or future compatibility work
- `P3`: polish or optional production refinement

Track guide:

- `core`: canonical `ipfs_datasets_py.wallet` models, service API, manifests
- `crypto`: encryption, key wrapping, recovery, threshold approvals
- `storage`: local, IPFS, Filecoin, S3, replica health, lifecycle controls
- `ucan`: capability vocabulary, caveats, delegation, invocation, revocation
- `proofs`: proof registry, verifier contracts, ZK/public-input boundaries
- `analytics`: consent, nullifiers, DP, k-thresholds, query budgets
- `analysis`: document extraction, redaction, GraphRAG, vector profiles
- `ui`: `wallet_interface` API/UI integration and workflow coverage
- `ops`: readiness, release checks, runbooks, signoff, daemon operation
- `interop`: external UCAN/storage/verifier adapters

## WALLET-000 Wallet Control Plane
- Status: completed
- Completion: artifact
- Priority: P0
- Track: ops
- Depends on: none
- Outputs: docs/UCAN_ZK_DATA_WALLET_IMPLEMENTATION_PLAN.md, docs/UCAN_ZK_DATA_WALLET_TODO.md, scripts/wallet_implementation_daemon.py, scripts/wallet_implementation_supervisor.py, scripts/manage_implementation_services.py, tests/test_wallet_implementation_todo_daemon.py, tests/test_implementation_service_manager.py
- Validation: python scripts/wallet_implementation_daemon.py --once --no-implement; python scripts/wallet_implementation_supervisor.py --once --no-implement; pytest tests/test_wallet_implementation_todo_daemon.py tests/test_implementation_service_manager.py -q
- Acceptance: The wallet backlog can be parsed, durable state is written under `data/wallet_implementation/state`, the next WALLET task is selected, and the supervisor can run through the shared optimizer todo daemon without mutating wallet source code in monitor-only mode.

## WALLET-010 Canonical Data Wallet Boundary
- Status: completed
- Completion: artifact
- Priority: P0
- Track: core
- Depends on: WALLET-000
- Outputs: ipfs_datasets_py/ipfs_datasets_py/wallet, docs/DOCUMENT_WALLET_IMPLEMENTATION_PLAN.md, docs/UCAN_ZK_DATA_WALLET_IMPLEMENTATION_PLAN.md
- Validation: pytest ipfs_datasets_py/tests/unit/test_data_wallet.py -q; pytest tests/test_wallet_implementation_plan_docs.py -q
- Acceptance: Documents, locations, profile data, service needs, derived artifacts, grants, invocations, approvals, analytics contributions, and audit events all route through `ipfs_datasets_py.wallet`; the older `data_wallet`, `document_wallet`, and `ipfs_datasets_py.wallet.document` package names remain removed.

## WALLET-020 Envelope Encryption And Key Wrapping
- Status: completed
- Completion: artifact
- Priority: P0
- Track: crypto
- Depends on: WALLET-010
- Outputs: ipfs_datasets_py/ipfs_datasets_py/wallet/crypto.py, ipfs_datasets_py/ipfs_datasets_py/wallet/service.py, ipfs_datasets_py/tests/unit/test_data_wallet.py
- Validation: pytest ipfs_datasets_py/tests/unit/test_data_wallet.py -q
- Acceptance: Each wallet record version has client-side AEAD encryption, per-version data keys, authorized key wraps, unauthorized decrypt rejection, key rotation, re-wrapping, and audit coverage.

## WALLET-030 Replicated Encrypted Storage
- Status: completed
- Completion: artifact
- Priority: P0
- Track: storage
- Depends on: WALLET-020
- Outputs: ipfs_datasets_py/ipfs_datasets_py/wallet/storage.py, docs/WALLET_RETENTION_POLICY.md, docs/WALLET_OPERATIONS_RUNBOOK.md
- Validation: pytest ipfs_datasets_py/tests/unit/test_data_wallet.py tests/test_wallet_interface_ops.py -q
- Acceptance: Local, IPFS, S3, Filecoin-style, and replicated blob stores persist only encrypted payloads, verify ciphertext hashes and AEAD availability, report replica health, and support repair without decrypting stored blobs.

## WALLET-040 UCAN Capability And Caveat Engine
- Status: completed
- Completion: artifact
- Priority: P0
- Track: ucan
- Depends on: WALLET-020
- Outputs: ipfs_datasets_py/ipfs_datasets_py/wallet/ucan.py, docs/WALLET_UCAN_PROFILE.md, docs/WALLET_PRODUCTION_DECISIONS_ADR.md
- Validation: pytest ipfs_datasets_py/tests/unit/test_data_wallet.py tests/test_wallet_interface_api.py -q
- Acceptance: Wallet grants and invocations enforce resources, abilities, expiration, not-before, record IDs, data types, output caveats, purpose, user presence, revocation, and delegated attenuation before any decrypt, analysis, proof, export, or service-match operation.

## WALLET-050 Threshold Governance And Recovery
- Status: completed
- Completion: artifact
- Priority: P0
- Track: crypto
- Depends on: WALLET-040
- Outputs: ipfs_datasets_py/ipfs_datasets_py/wallet/service.py, wallet_interface/api.py, wallet_interface/ui/src/app/App.tsx
- Validation: pytest ipfs_datasets_py/tests/unit/test_data_wallet.py tests/test_wallet_interface_api.py -q; npm --prefix wallet_interface/ui test -- tests/smoke.spec.ts
- Acceptance: Sensitive decrypt, export, root authority, controller, device, emergency revoke, and recovery operations can require multi-controller threshold approval and preserve an auditable decision trail.

## WALLET-060 Document-Derived Analysis Boundary
- Status: completed
- Completion: artifact
- Priority: P0
- Track: analysis
- Depends on: WALLET-040
- Outputs: ipfs_datasets_py/ipfs_datasets_py/wallet/service.py, ipfs_datasets_py/ipfs_datasets_py/mcp_server/tools/wallet_tools, wallet_interface/api.py
- Validation: pytest ipfs_datasets_py/tests/unit/test_data_wallet.py ipfs_datasets_py/tests/mcp/test_wallet_tools.py tests/test_wallet_interface_api.py -q
- Acceptance: PDF/OCR/text extraction, form analysis, redacted document analysis, cross-record analysis, vector-profile generation, and redacted GraphRAG decrypt inside the wallet boundary, return only allowed output types, store encrypted derived artifacts, and audit delegated use.

## WALLET-070 Location Claims And 211 Service Matching
- Status: completed
- Completion: artifact
- Priority: P0
- Track: proofs
- Depends on: WALLET-040
- Outputs: ipfs_datasets_py/ipfs_datasets_py/wallet/location.py, wallet_interface/service_matching.py, wallet_interface/api.py
- Validation: pytest ipfs_datasets_py/tests/unit/test_data_wallet.py tests/test_wallet_interface_api.py -q
- Acceptance: Precise location remains encrypted, coarse location and proof receipts are preferred for service matching, precise location requires explicit grants, and public proof inputs do not leak coordinates or witness material.

## WALLET-080 Proof Registry And Verifier Contracts
- Status: completed
- Completion: artifact
- Priority: P0
- Track: proofs
- Depends on: WALLET-070
- Outputs: ipfs_datasets_py/ipfs_datasets_py/wallet/proofs.py, docs/WALLET_PROOF_VERIFIER_CONTRACT.md, wallet_interface/ops.py
- Validation: pytest ipfs_datasets_py/tests/unit/test_data_wallet.py tests/test_wallet_interface_ops.py tests/test_wallet_production_handoff_blackbox.py -q
- Acceptance: Development proofs are labeled as simulated, production-style services fail closed without configured non-simulated backends, HTTP verifier contracts validate `location_region` and `location_distance`, and receipt public inputs remain safe for UI display.

## WALLET-090 Privacy-Preserving Analytics
- Status: completed
- Completion: artifact
- Priority: P0
- Track: analytics
- Depends on: WALLET-040, WALLET-080
- Outputs: ipfs_datasets_py/ipfs_datasets_py/wallet/analytics.py, ipfs_datasets_py/ipfs_datasets_py/wallet/privacy.py, wallet_interface/api.py
- Validation: pytest ipfs_datasets_py/tests/unit/test_data_wallet.py tests/test_wallet_interface_api.py tests/test_wallet_production_handoff_blackbox.py -q
- Acceptance: Approved templates, consent, nullifiers, duplicate rejection, k-threshold suppression, differential privacy metadata, query budgets, durable analytics ledger entries, and aggregate audit events are enforced without releasing raw contribution fields.

## WALLET-100 211-AI Wallet UI And API Integration
- Status: completed
- Completion: artifact
- Priority: P1
- Track: ui
- Depends on: WALLET-060, WALLET-070, WALLET-090
- Outputs: wallet_interface/api.py, wallet_interface/ui/src/app/App.tsx, wallet_interface/ui/src/services/walletApi.ts, wallet_interface/ui/tests/fullstack-wallet.spec.ts
- Validation: pytest tests/test_wallet_interface_api.py -q; npm --prefix wallet_interface/ui run build; npm --prefix wallet_interface/ui test -- tests/smoke.spec.ts; npm --prefix wallet_interface/ui test -- tests/fullstack-wallet.spec.ts
- Acceptance: Users can create a wallet, add documents and location, share scoped analysis-only access, review grant receipts, run service matching, manage proofs, consent to analytics, create encrypted exports, revoke access, inspect storage health, and view audit events through the app layer without duplicating wallet core logic outside `ipfs_datasets_py`.

## WALLET-110 End-To-End Release Gate
- Status: todo
- Completion: evidence
- Priority: P0
- Track: ops
- Depends on: WALLET-100
- Outputs: scripts/run_wallet_release_checks.py, docs/WALLET_TARGET_PRODUCTION_SIGNOFF.md, docs/WALLET_TARGET_PRODUCTION_SIGNOFF_PACKET.template.json
- Validation: python scripts/run_wallet_release_checks.py --dry-run; python scripts/run_wallet_release_checks.py --playwright-port 5185; python -m wallet_interface.ops --validate-production-readiness; python -m wallet_interface.ops --validate-target-signoff-packet
- Acceptance: A target staging environment produces a passing production-readiness report, a completed signoff packet, archived release-check evidence, and a human-approved decision covering security, privacy, legal, accessibility, ops, and product ownership.

## WALLET-120 External UCAN Adapter Track
- Status: todo
- Completion: evidence
- Priority: P1
- Track: interop
- Depends on: WALLET-040, WALLET-110
- Outputs: docs/WALLET_UCAN_PROFILE.md, ipfs_datasets_py/ipfs_datasets_py/wallet/ucan.py, ipfs_datasets_py/tests/unit/test_data_wallet.py
- Validation: python -m ipfs_datasets_py.wallet.cli ucan-validate-fixture; pytest ipfs_datasets_py/tests/unit/test_data_wallet.py -q
- Acceptance: The internal `wallet-ucan-v1` profile remains the first-production encoding while a target-specific adapter proves byte-level compatibility with the selected external UCAN stack without broadening wallet capabilities or bypassing caveat enforcement.

## WALLET-130 Target IPFS, Filecoin, And S3 Storage Operations
- Status: todo
- Completion: evidence
- Priority: P1
- Track: storage
- Depends on: WALLET-030, WALLET-110
- Outputs: docs/WALLET_RETENTION_POLICY.md, docs/WALLET_OPERATIONS_RUNBOOK.md, wallet_interface/deploy
- Validation: python -m wallet_interface.ops --validate-production-readiness; python scripts/run_wallet_release_checks.py --dry-run
- Acceptance: Target storage credentials are provisioned by secret-manager reference, encrypted replica retention is mapped to IPFS pinning, Filecoin deal expiration, S3 lifecycle, backup purge, and alert retention controls, and storage repair checks pass without exposing plaintext.

## WALLET-140 Target Verifier Credential Handoff
- Status: todo
- Completion: evidence
- Priority: P1
- Track: proofs
- Depends on: WALLET-080, WALLET-110
- Outputs: docs/WALLET_PROOF_VERIFIER_CONTRACT.md, docs/WALLET_TARGET_PRODUCTION_SIGNOFF.md
- Validation: python -m wallet_interface.ops --validate-proof-contract --fail-on-error; python -m wallet_interface.ops --validate-distance-proof-contract --fail-on-error; python -m wallet_interface.ops --validate-production-readiness
- Acceptance: Real verifier credentials are present only as secret-manager references, the external verifier health/prove/verify/no-leak contracts pass in target staging, and `location_distance` remains hidden from live Proof Center exposure until that validation is archived.

## WALLET-150 Live Auth And Passkey Binding
- Status: todo
- Completion: artifact
- Priority: P1
- Track: crypto
- Depends on: WALLET-050, WALLET-110
- Outputs: wallet_interface/api.py, wallet_interface/ui/src/app/App.tsx, docs/WALLET_SECURITY_ARCHITECTURE_ADR.md
- Validation: pytest tests/test_wallet_interface_api.py -q; npm --prefix wallet_interface/ui run build; npm --prefix wallet_interface/ui test -- tests/smoke.spec.ts
- Acceptance: The selected live authentication layer binds passkey or device-auth sessions to wallet controller/device DIDs, gates sensitive UI operations with user presence, and preserves the existing wallet threshold and recovery semantics.

## WALLET-160 Production Analytics Review Packets
- Status: todo
- Completion: evidence
- Priority: P1
- Track: analytics
- Depends on: WALLET-090, WALLET-110
- Outputs: docs/WALLET_TARGET_PRODUCTION_SIGNOFF.md, docs/WALLET_RETENTION_POLICY.md
- Validation: python -m wallet_interface.ops --validate-target-signoff-packet
- Acceptance: Each approved production analytics template has a documented purpose, data fields, consent language, retention mapping, cohort threshold, privacy budget, sparse-cell risk review, reviewer decision, and withdrawal/audit handling plan.

## WALLET-170 Third-Party Sharing Blackbox Harness
- Status: todo
- Completion: artifact
- Priority: P1
- Track: ucan
- Depends on: WALLET-110, WALLET-120, WALLET-150
- Outputs: tests/test_wallet_third_party_blackbox.py, docs/WALLET_OPERATOR_INTEGRATOR_REFERENCE.md, wallet_interface/api.py
- Validation: pytest tests/test_wallet_interface_api.py tests/test_wallet_production_handoff_blackbox.py -q; pytest tests/test_wallet_third_party_blackbox.py -q
- Acceptance: A blackbox test creates wallet data, issues scoped UCAN grants to simulated third parties, invokes document-derived analysis, coarse-location service matching, proof-only claims, encrypted export, and revocation flows through public API boundaries without importing wallet internals.

## WALLET-180 Non-Simulated Verifier Cutover Packet
- Status: todo
- Completion: evidence
- Priority: P1
- Track: proofs
- Depends on: WALLET-140
- Outputs: docs/WALLET_PROOF_VERIFIER_CONTRACT.md, docs/WALLET_TARGET_PRODUCTION_SIGNOFF.md, docs/WALLET_OPERATOR_INTEGRATOR_REFERENCE.md
- Validation: python -m wallet_interface.ops --validate-proof-contract --fail-on-error; python -m wallet_interface.ops --validate-distance-proof-contract --fail-on-error; python -m wallet_interface.ops --validate-production-readiness
- Acceptance: The selected verifier backend has archived staging health, prove, verify, no-leak, credential-reference, failure-mode, and rollback evidence for `location_region` and `location_distance` before any non-simulated proof path is exposed to users.

## WALLET-190 Storage Retention And Deletion Dry Run
- Status: todo
- Completion: evidence
- Priority: P1
- Track: storage
- Depends on: WALLET-130
- Outputs: docs/WALLET_RETENTION_POLICY.md, docs/WALLET_OPERATIONS_RUNBOOK.md, docs/WALLET_TARGET_PRODUCTION_SIGNOFF.md
- Validation: python -m wallet_interface.ops --validate-production-readiness; python scripts/run_wallet_release_checks.py --dry-run
- Acceptance: Target staging demonstrates encrypted replica creation, replica health checks, repair, grant revocation, key rotation, record deletion, analytics-consent withdrawal, export-bundle retention, and purge/audit evidence without revealing plaintext or secret values.

## WALLET-200 Analytics Governance Release Workflow
- Status: todo
- Completion: evidence
- Priority: P1
- Track: analytics
- Depends on: WALLET-160
- Outputs: docs/WALLET_TARGET_PRODUCTION_SIGNOFF.md, docs/WALLET_RETENTION_POLICY.md, docs/WALLET_OPERATOR_INTEGRATOR_REFERENCE.md
- Validation: python -m wallet_interface.ops --validate-target-signoff-packet; python scripts/run_wallet_release_checks.py --dry-run
- Acceptance: Production analytics cannot run from arbitrary raw queries; every approved template has consent copy, allowed fields, proof statements, nullifier policy, k-threshold, privacy budget, retention mapping, reviewer names or roles, and withdrawal handling recorded in the signoff packet.

## WALLET-210 211 Service Partner Pilot Readiness
- Status: todo
- Completion: evidence
- Priority: P1
- Track: ui
- Depends on: WALLET-170, WALLET-180, WALLET-190, WALLET-200
- Outputs: docs/WALLET_OPERATOR_INTEGRATOR_REFERENCE.md, docs/WALLET_OPERATIONS_RUNBOOK.md, wallet_interface/ui/tests/fullstack-wallet.spec.ts
- Validation: pytest tests/test_wallet_interface_api.py tests/test_wallet_third_party_blackbox.py -q; npm --prefix wallet_interface/ui run build; npm --prefix wallet_interface/ui test -- tests/fullstack-wallet.spec.ts
- Acceptance: A staging pilot can show a user adding documents and location, sharing purpose-bound access with a partner, proving location eligibility without precise-coordinate disclosure, contributing to approved aggregate analytics, revoking access, and auditing the full workflow through 211-AI UI/API surfaces backed by `ipfs_datasets_py.wallet`.
