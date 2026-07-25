# World Human-Aid WLD Objective Heap

This is the canonical objective heap for completing the repository's World ID,
document-wallet eligibility, and WLD disbursement integration. The filename
retains “Worldcoin” for project continuity; current implementation names should
use World ID, World Chain, MiniKit, and WLD.

The architecture deliberately separates five facts that must never be collapsed
into one boolean:

1. wallet ownership, authenticated with a server-verified SIWE challenge;
2. optional proof of human, verified with World ID v4;
3. document-claim authenticity, established by an authorized issuer;
4. program eligibility, proven against a versioned policy with a real ZK proof;
5. provider authorization and final WLD transfer settlement on World Chain.

World ID is optional anti-abuse evidence. It is neither login nor proof of
homelessness, residency, income, or benefit eligibility. A person who cannot or
does not use World ID, World App, an Orb, a smartphone, or a crypto wallet must
retain a documented human-review and non-digital service path. The system may
verify a proof, but it must not autonomously deny essential services or make an
unappealable adverse eligibility decision.

Privacy and safety invariants:

- Never put raw documents, biometric data, World ID nullifiers/session IDs,
  homelessness status, eligibility reasons, case notes, or wallet-to-person
  mappings on-chain.
- Treat the existing simulated `document_privacy_profile` receipt as development
  metadata only. It must be rejected as payment-authorizing eligibility proof.
- Put only the WLD ERC-20 transfer and, if required, an opaque randomized claim
  commitment on-chain. Keep the commitment-to-case mapping encrypted off-chain
  under retention and access-control policy.
- Bind every approval to provider, program/policy version, benefit period,
  recipient address, chain, token, exact base-unit amount or expiring fiat quote,
  nonce, and expiry. Idempotency must survive retries and process restarts.
- Keep RP signing keys and treasury authority in approved secret-management,
  HSM/MPC, or multisig systems. No autonomous worker may create or expose a
  production key, change a remote Developer Portal setting, deploy a contract,
  or submit a production transfer.
- Autonomous validation is offline, fixture-backed, or dry-run-only. A World
  Chain Sepolia pilot requires explicit human authorization and supplies a
  read-only receipt for local verification.

Fail-closed runtime ownership is part of this heap. `WORLD_ID_ENABLED=0` is an
existing default in `wallet_interface/world_id.py`. The following two guards are
proposals and **do not exist in implementation yet**; their appearance in this
planning document is not completion evidence:

- WORLDCOIN-G004 owns the shared runtime-guard implementation and focused tests
  for `WORLD_AID_EXTERNAL_CALLS_ENABLED=0`. Every World API, RPC, indexer,
  custody, signer, or other remote adapter must refuse I/O unless this guard is
  explicitly enabled in an approved environment.
- WORLDCOIN-G021 owns implementation and focused tests for
  `WORLD_AID_WLD_TRANSFERS_ENABLED=0`. Signing and broadcasting must remain
  disabled even when external read calls are enabled.
- WORLDCOIN-G028 owns cross-adapter tests proving both new guards default to
  false, invalid values fail closed, and no alternate adapter bypasses them.
  WORLDCOIN-G031 owns the release-gate rule that any enablement is explicit,
  environment-scoped, approval-bound, observable, and reversible.

## Supervisor workflow

Use
`docs/planning/WORLDCOIN_HUMAN_AID_AGENT_SUPERVISOR_RUNBOOK.md` as the only
command source. It pins the no-core/offline-library environment, explicitly
forces every schedulable G001-G034 objective so broad evidence matches cannot
produce a zero-task board, verifies exact TODO/bundle/DAG identity, and excludes
terminal human gates G035-G036. This heap deliberately does not duplicate a
shorter launch command that could drift from those controls.

Generating and reviewing the board or planning lanes without `--start` starts
no workers. Adding `--start --implement` is a separate Gate 0 action and still
does not authorize production credentials, remote configuration, contract
deployment, or asset transfer.

## WORLDCOIN-G001 Integrate the privacy-preserving human-aid WLD implementation

- Status: active
- Fib priority: 610001
- Priority: P0
- Track: world-aid-platform
- Parents: WORLDCOIN-G029
- Goal: Deliver a deterministic local end-to-end implementation in which an authenticated synthetic recipient can optionally prove personhood, prove program eligibility from document-wallet claims without disclosing them, exercise a provider-approved WLD transfer through fake custody/chain adapters, and follow an accessible appeal or manual path; live pilot and production outcomes remain blocked human goals.
- Evidence: typed trust-domain contracts; SIWE authentication; optional World ID v4 verification; issuer and policy registries; production eligibility proof verification; human review; idempotent payout intent; controlled treasury adapter; World Chain reconciliation; private and public audit receipts; offline end-to-end tests; local integration acceptance receipt
- Outputs: docs/architecture/WORLD_HUMAN_AID_ARCHITECTURE.md, wallet_interface/world_aid/__init__.py, wallet_interface/world_aid/service.py, tests/world_aid/test_world_aid_end_to_end.py, data/worldcoin_human_aid/acceptance/end-to-end-receipt.fixture.json
- Validation: python -m pytest -q tests/world_aid/test_world_aid_end_to_end.py
- Bundle: worldcoin-human-aid/integration
- Parallel lane: world-aid-integration
- Embedding query: optional proof of human document wallet eligibility zero knowledge proof provider WLD disbursement World Chain privacy appeal
- AST query: WorldAidService, EligibilityProof, PayoutIntent, WorldChainReceipt, process_world_aid_claim
- Interfaces: wallet_interface World ID and document wallet, ipfs_datasets_py ZKP, World Chain JSON-RPC, WLD ERC-20
- Submodules:
- Generated artifacts: data/worldcoin_human_aid/acceptance/end-to-end-receipt.fixture.json
- Predicted files: docs/architecture/WORLD_HUMAN_AID_ARCHITECTURE.md, wallet_interface/world_aid/__init__.py, wallet_interface/world_aid/service.py, tests/world_aid/test_world_aid_end_to_end.py, data/worldcoin_human_aid/acceptance/end-to-end-receipt.fixture.json
- Conflict policy: integrate child contracts only after their focused gates pass; preserve existing wallet, World ID, document, and proof APIs through additive adapters
- Gap task: Integrate the bounded child goals into one fail-closed service and record success, replay, denial-to-manual-review, and chain-failure receipts without network access or real assets.
- Acceptance criteria: The receipt represents wallet ownership, optional human verification, document-claim authenticity, eligibility proof, provider approval, and settlement as separate typed states; a valid synthetic claim reaches confirmed settlement through injected verifiers and a fake chain, while replay, recipient substitution, amount substitution, expired proof, revoked issuer, and simulated-proof cases fail closed before signing; no test, log, receipt, public API response, or chain payload contains raw documents, biometric data, homelessness status, eligibility reason, private nullifier, secret, or real person data; skipping or failing optional World ID routes to the configured non-World-ID review path and never becomes an automatic essential-service denial; the end-to-end suite is offline and cannot submit a transaction or mutate World, Hugging Face, IPFS, or other remote state.
- Refinement: Generated TODO acceptance must satisfy these exact WORLDCOIN-G001 criteria: the receipt represents wallet ownership, optional human verification, document-claim authenticity, eligibility proof, provider approval, and settlement as separate typed states; a valid synthetic claim reaches confirmed settlement through injected verifiers and a fake chain, while replay, recipient substitution, amount substitution, expired proof, revoked issuer, and simulated-proof cases fail closed before signing; no test, log, receipt, public API response, or chain payload contains raw documents, biometric data, homelessness status, eligibility reason, private nullifier, secret, or real person data; skipping or failing optional World ID routes to the configured non-World-ID review path and never becomes an automatic essential-service denial; the end-to-end suite is offline and cannot submit a transaction or mutate World, Hugging Face, IPFS, or other remote state.
- Acceptance gate:
  1. The receipt represents wallet ownership, optional human verification, document-claim authenticity, eligibility proof, provider approval, and settlement as separate typed states.
  2. A valid synthetic claim reaches confirmed settlement through injected verifiers and a fake chain; replay, recipient substitution, amount substitution, expired proof, revoked issuer, and simulated-proof cases fail closed before signing.
  3. No test, log, receipt, public API response, or chain payload contains raw documents, biometric data, homelessness status, eligibility reason, private nullifier, secret, or real person data.
  4. Skipping or failing optional World ID routes to the configured non-World-ID review path and never becomes an automatic essential-service denial.
  5. The end-to-end suite is offline and cannot submit a transaction or mutate World, Hugging Face, IPFS, or other remote state.

## WORLDCOIN-G002 Audit the unfinished World integration and freeze compatibility boundaries

- Status: active
- Fib priority: 1000
- Priority: P0
- Track: world-aid-discovery
- Parents:
- Goal: Map the current World ID, document-wallet, ZKP, provider, payment, and UI implementations to the target trust domains and record concrete reuse, drift, and deletion-prohibited boundaries.
- Evidence: path-and-symbol inventory; IDKit v4 and legacy-label gap matrix; simulated-proof finding; signal-binding and nullifier durability findings; plaintext LocalWalletRepository snapshot and unauthenticated overbroad status findings; absent EIP-1271 wallet-auth, issuer lifecycle, production store, payout, and reconciliation findings; API and UI compatibility inventory; installed/missing npm, Python/DuckDB, and ZKP toolchain inventory; non-authoritative offline-bootstrap proposal with exact review questions and no downloads; dependency and ownership map
- Outputs: docs/reports/WORLD_HUMAN_AID_INTEGRATION_AUDIT.md, data/worldcoin_human_aid/audit/component-map.json, data/worldcoin_human_aid/audit/offline-bootstrap-proposal.json, tests/world_aid/test_integration_audit_contract.py
- Validation: PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q -s -p no:cacheprovider -c /dev/null --confcutdir=tests/world_aid tests/world_aid/test_integration_audit_contract.py
- Bundle: worldcoin-human-aid/integration-audit
- Parallel lane: world-aid-discovery
- Embedding query: current World ID IDKit wallet document proof backend provider payment integration gap audit compatibility
- AST query: verify_world_id_proof, create_world_id_rp_signature, register_world_id_verification, create_document_profile_proof, HttpLocationRegionProofBackend
- Interfaces: wallet_interface/world_id.py, wallet_interface/routes/world_id.py, wallet_interface/app_service.py, ipfs_datasets_py wallet and logic zkp
- Submodules:
- Generated artifacts: data/worldcoin_human_aid/audit/component-map.json, data/worldcoin_human_aid/audit/offline-bootstrap-proposal.json
- Predicted files: docs/reports/WORLD_HUMAN_AID_INTEGRATION_AUDIT.md, data/worldcoin_human_aid/audit/component-map.json, data/worldcoin_human_aid/audit/offline-bootstrap-proposal.json, tests/world_aid/test_integration_audit_contract.py
- Conflict policy: read and classify existing behavior before proposing rewrites; preserve unrelated dirty work and identify owners for every shared file
- Gap task: Produce a reproducible source audit that distinguishes implemented, partially implemented, simulated, missing, deprecated, and unsafe-to-reuse capabilities.
- Acceptance criteria: Every claim cites a repository path/symbol or official contract version and labels speculation; the audit states that the simulated profile receipt is not eligibility and provider signal context is unenforced; it records that LocalWalletRepository snapshots plaintext principal secrets/raw World bindings, unauthenticated status returns full bindings, legacy acceptance defaults on, and receipts can mislabel accepted v3 evidence as v4; it identifies missing EIP-1271 SIWE, issuer credential lifecycle, encrypted transactional storage, payout, and reconciliation boundaries; the machine map has stable owners/interfaces/risks/goals/conflict surfaces; the offline-bootstrap proposal inventories installed and missing npm, Python/DuckDB, and ZKP inputs and asks humans to select versions, checksums, licenses, provenance, SBOM, cache locations, single-writer topology, and smoke tests without presenting agent choices as approval; the audit performs no mutation, download, network call, secret lookup, package install, container pull/start, toolchain execution, or package-core initialization.
- Refinement: Generated TODO acceptance must satisfy these exact WORLDCOIN-G002 criteria: Every claim cites a repository path/symbol or official contract version and labels speculation; the audit states that the simulated profile receipt is not eligibility and provider signal context is unenforced; it records that LocalWalletRepository snapshots plaintext principal secrets/raw World bindings, unauthenticated status returns full bindings, legacy acceptance defaults on, and receipts can mislabel accepted v3 evidence as v4; it identifies missing EIP-1271 SIWE, issuer credential lifecycle, encrypted transactional storage, payout, and reconciliation boundaries; the machine map has stable owners/interfaces/risks/goals/conflict surfaces; the offline-bootstrap proposal inventories installed and missing npm, Python/DuckDB, and ZKP inputs and asks humans to select versions, checksums, licenses, provenance, SBOM, cache locations, single-writer topology, and smoke tests without presenting agent choices as approval; the audit performs no mutation, download, network call, secret lookup, package install, container pull/start, toolchain execution, or package-core initialization.
- Acceptance gate:
  1. Every claim cites a repository path and symbol or an official API contract version; speculative findings are labeled.
  2. The audit states that the simulated profile receipt is not eligibility and provider signal context is unenforced; it records that LocalWalletRepository snapshots plaintext principal secrets/raw World bindings, unauthenticated status returns full bindings, legacy acceptance defaults on, and receipts can mislabel accepted v3 evidence as v4.
  3. It identifies missing EIP-1271 SIWE, issuer credential lifecycle, encrypted transactional storage, payout, and reconciliation boundaries; the machine map has stable owners, interfaces, risks, goals, and conflict surfaces.
  4. The offline-bootstrap proposal inventories installed and missing npm, Python/DuckDB, and ZKP inputs and asks humans to select versions, checksums, licenses, provenance, SBOM, cache locations, single-writer topology, and smoke tests without presenting agent choices as approval.
  5. Running the audit contract performs no mutation, download, network call, secret lookup, package install, container pull/start, toolchain execution, or package-core initialization.
- Objective-validation evidence (WORLDCOIN-AUTO-001):
  - Discovery repair: `data/worldcoin_human_aid/agent_supervisor/discovery/2026-07-24-worldcoin-auto-001-integration-audit.md`
  - Cited audit: `docs/reports/WORLD_HUMAN_AID_INTEGRATION_AUDIT.md`
  - Stable machine map: `data/worldcoin_human_aid/audit/component-map.json`
  - Human-selection-only bootstrap proposal: `data/worldcoin_human_aid/audit/offline-bootstrap-proposal.json`
  - Static contract: `tests/world_aid/test_integration_audit_contract.py`
  - Historical backlog identity only (superseded by the next immutable regeneration): todo vector `3acfa404134f3aa1`, merge family `objective/WORLDCOIN-G002`, work scope `objective_validation_repair`

## WORLDCOIN-G003 Establish policy, DPIA, legal, accessibility, and manual-path gates

- Status: active
- Fib priority: 3000
- Priority: P0
- Track: world-aid-governance
- Parents: WORLDCOIN-G002
- Goal: Define enforceable human-rights, privacy, financial, accessibility, appeal, retention, and non-digital fallback requirements before eligibility or payment code can be enabled.
- Evidence: data-flow and threat diagrams; DPIA template; jurisdiction and money-transmission question register; sanctions, tax, benefits-interaction, and WLD-volatility review gates; consent and retention matrix; accessibility standard; no-autonomous-denial policy; appeal and manual fallback runbook
- Outputs: docs/governance/WORLD_HUMAN_AID_POLICY_AND_RISK.md, docs/governance/WORLD_HUMAN_AID_DPIA.md, docs/runbooks/WORLD_HUMAN_AID_APPEALS.md, tests/world_aid/test_governance_gates.py
- Validation: python -m pytest -q tests/world_aid/test_governance_gates.py
- Bundle: worldcoin-human-aid/governance
- Parallel lane: world-aid-governance
- Embedding query: DPIA privacy benefit eligibility human review appeal accessibility non-digital fallback WLD volatility financial compliance
- AST query: EligibilityDecision, AppealRecord, ManualReviewReason, ReleaseGate
- Interfaces: program administrators, service providers, privacy and security reviewers, recipient support
- Submodules:
- Predicted files: docs/governance/WORLD_HUMAN_AID_POLICY_AND_RISK.md, docs/governance/WORLD_HUMAN_AID_DPIA.md, docs/runbooks/WORLD_HUMAN_AID_APPEALS.md, tests/world_aid/test_governance_gates.py
- Conflict policy: encode gates and reviewer roles without pretending the software or autonomous agent can provide legal advice or approval
- Gap task: Turn safety assumptions into machine-testable release invariants and explicit human decisions for each deployment jurisdiction and benefit program.
- Acceptance criteria: The policy prohibits conditioning essential service access on World ID, World App, an Orb, smartphone ownership, or crypto familiarity; eligibility uncertainty, proof failure, accessibility barriers, and identity mismatch route to trained human review with notice, reason category, evidence correction, and appeal; retention, deletion, role access, incident response, and encrypted mapping requirements cover documents, identifiers, proofs, quotes, and payout records separately; production enablement remains false until named legal, program, privacy, security, treasury, and accessibility reviewers supply signed gate records.
- Refinement: Generated TODO acceptance must satisfy these exact WORLDCOIN-G003 criteria: the policy prohibits conditioning essential service access on World ID, World App, an Orb, smartphone ownership, or crypto familiarity; eligibility uncertainty, proof failure, accessibility barriers, and identity mismatch route to trained human review with notice, reason category, evidence correction, and appeal; retention, deletion, role access, incident response, and encrypted mapping requirements cover documents, identifiers, proofs, quotes, and payout records separately; production enablement remains false until named legal, program, privacy, security, treasury, and accessibility reviewers supply signed gate records.
- Acceptance gate:
  1. The policy prohibits conditioning essential service access on World ID, World App, an Orb, smartphone ownership, or crypto familiarity.
  2. Eligibility uncertainty, proof failure, accessibility barriers, and identity mismatch route to trained human review with notice, reason category, evidence correction, and appeal.
  3. Retention, deletion, role access, incident response, and encrypted mapping requirements cover documents, identifiers, proofs, quotes, and payout records separately.
  4. Production enablement remains false until named legal, program, privacy, security, treasury, and accessibility reviewers supply signed gate records.

## WORLDCOIN-G004 Harden Developer Portal and World ID v4 configuration boundaries

- Status: active
- Fib priority: 3001
- Priority: P0
- Track: world-id-platform
- Parents: WORLDCOIN-G002
- Goal: Represent World Developer Portal applications, relying parties, actions, allowed origins, RP signing, verification endpoints, and migration deadlines as validated server-side configuration with explicit human-managed remote setup.
- Evidence: `app_id`, `rp_id`, action, proof mode, origin, environment, verification URL, and signing-key-reference schema; backend RP signature boundary; v4 verify request fixture; aid-flow legacy default-off and protocol-accurate receipt labels; v3 rejection/sunset guard; configuration drift report; Identity Check feasibility note; proposed fail-closed external-call runtime guard
- Outputs: wallet_interface/world_aid/world_config.py, wallet_interface/world_aid/runtime_guards.py, docs/runbooks/WORLD_DEVELOPER_PORTAL_CONFIGURATION.md, tests/world_aid/test_world_config.py, tests/world_aid/test_runtime_guards.py
- Validation: python -m pytest -q tests/world_aid/test_world_config.py tests/world_aid/test_runtime_guards.py
- Bundle: worldcoin-human-aid/world-config
- Parallel lane: world-id-platform
- Embedding query: World Developer Portal IDKit v4 relying party RP signature app action origin verification migration
- AST query: WorldEnvironmentConfig, RelyingPartyConfig, WorldActionPolicy, WorldIdV4Verifier, WorldAidRuntimeGuards, require_external_calls_enabled
- Interfaces: World Developer Portal v4 verify API, IDKit 4.x, backend secret provider
- Submodules:
- Predicted files: wallet_interface/world_aid/world_config.py, wallet_interface/world_aid/runtime_guards.py, docs/runbooks/WORLD_DEVELOPER_PORTAL_CONFIGURATION.md, tests/world_aid/test_world_config.py, tests/world_aid/test_runtime_guards.py
- Conflict policy: configuration code emits a reviewed manifest only; autonomous workers never create signing keys or mutate Developer Portal applications, actions, origins, or allowlists
- Gap task: Replace ambient World settings with an environment-scoped, fail-closed configuration contract and offline API fixtures.
- Acceptance criteria: Production requires an `app_id`, `rp_id`, allowlisted proof-mode/action, exact origin, backend signing-key reference, and v4 endpoint, with no serialized secrets; only the backend forwards unchanged IDKit results and calls v4 verification; the aid flow defaults legacy acceptance off, never labels v3 evidence as v4, and rejects mixed environment, unknown action, insecure origin, post-cutoff legacy, and client-selected endpoint; Identity Check remains optional rather than arbitrary wallet eligibility; `WORLD_AID_EXTERNAL_CALLS_ENABLED` defaults/fails closed and every external adapter checks it before I/O.
- Refinement: Generated TODO acceptance must satisfy these exact WORLDCOIN-G004 criteria: Production requires an `app_id`, `rp_id`, allowlisted proof-mode/action, exact origin, backend signing-key reference, and v4 endpoint, with no serialized secrets; only the backend forwards unchanged IDKit results and calls v4 verification; the aid flow defaults legacy acceptance off, never labels v3 evidence as v4, and rejects mixed environment, unknown action, insecure origin, post-cutoff legacy, and client-selected endpoint; Identity Check remains optional rather than arbitrary wallet eligibility; `WORLD_AID_EXTERNAL_CALLS_ENABLED` defaults/fails closed and every external adapter checks it before I/O.
- Acceptance gate:
  1. Production requires an `app_id`, `rp_id`, allowlisted action, exact origin, backend signing-key reference, and v4 verification endpoint; secrets are never serialized.
  2. IDKit results are forwarded unchanged to the backend verifier, and only the backend calls the v4 verification API using an RP signature.
  3. The aid flow defaults legacy acceptance off, keeps protocol/circuit labels accurate for any explicitly accepted migration evidence, and rejects mixed staging/production IDs, unknown actions, insecure origins outside explicit local development, legacy formats after cutoff, and client-supplied verification URLs.
  4. Identity Check or passport facts are documented as optional World capabilities, not a general verifier for arbitrary document-wallet eligibility.
  5. The newly implemented `WORLD_AID_EXTERNAL_CALLS_ENABLED` guard defaults to false, invalid or absent values fail closed, and all external adapters call one audited guard before I/O; this criterion acknowledges that the guard did not exist when the heap was authored.

## WORLDCOIN-G005 Define canonical trust-domain and state contracts

- Status: active
- Fib priority: 3002
- Priority: P0
- Track: world-aid-domain
- Parents: WORLDCOIN-G002
- Goal: Define versioned, serializable trust-domain models plus the early canonical ClaimContext, EligibilityScope, and PayoutPayload contracts that every World, ZKP, and payout task consumes without a dependency loop.
- Evidence: enums with explicit unknown and expired states; schema-versioned models; immutable provider, program, benefit-period, and disbursement-scope identifiers; canonical encoding and domain tags; deterministic identifiers and golden vectors; transition matrix; JSON round-trip tests; separate private and public projections; backward-compatible adapters for current wallet records
- Outputs: wallet_interface/world_aid/models.py, wallet_interface/world_aid/claim_schema.py, docs/specs/WORLD_HUMAN_AID_DOMAIN_MODEL.md, tests/world_aid/test_domain_models.py, tests/world_aid/test_claim_schema.py
- Validation: python -m pytest -q tests/world_aid/test_domain_models.py tests/world_aid/test_claim_schema.py
- Bundle: worldcoin-human-aid/domain-contracts
- Parallel lane: world-aid-domain
- Embedding query: trust domains SIWE optional humanity issuer claims eligibility decision payout settlement appeal state models
- AST query: AuthenticatedPrincipal, HumanVerification, EligibilityClaim, EligibilityScope, WorldAidClaimContext, PayoutPayload, EligibilityDecision, PayoutIntent, SettlementReceipt
- Interfaces: wallet_interface APIs, ipfs_datasets_py proof receipts, provider workflow, World Chain adapters
- Submodules:
- Predicted files: wallet_interface/world_aid/models.py, wallet_interface/world_aid/claim_schema.py, docs/specs/WORLD_HUMAN_AID_DOMAIN_MODEL.md, tests/world_aid/test_domain_models.py, tests/world_aid/test_claim_schema.py
- Conflict policy: add a new versioned namespace and narrow adapters; do not overload WorldIdBinding or ProofReceipt with payment semantics
- Gap task: Make invalid cross-domain shortcuts unrepresentable and define the one-way transitions allowed in each lifecycle.
- Acceptance criteria: Wallet authentication, human verification, claim authenticity, eligibility, provider authorization, and settlement cannot be inferred from one another; every persisted model carries schema version, stable opaque ID, created/expiry timestamps, actor or producer reference, and privacy classification; public serialization omits raw claims, nullifiers, session IDs, document hashes, case labels, notes, encrypted mapping keys, and secrets; invalid, skipped, failed, expired, revoked, review-required, and unknown states remain distinguishable without encoding a benefits denial; immutable ClaimContext, EligibilityScope, and PayoutPayload schemas use versioned canonical encoding and golden vectors before G007, G012, or G016 consumes them, while display-alias changes cannot change cryptographic identities.
- Refinement: Generated TODO acceptance must satisfy these exact WORLDCOIN-G005 criteria: Wallet authentication, human verification, claim authenticity, eligibility, provider authorization, and settlement cannot be inferred from one another; every persisted model carries schema version, stable opaque ID, created/expiry timestamps, actor or producer reference, and privacy classification; public serialization omits raw claims, nullifiers, session IDs, document hashes, case labels, notes, encrypted mapping keys, and secrets; invalid, skipped, failed, expired, revoked, review-required, and unknown states remain distinguishable without encoding a benefits denial; immutable ClaimContext, EligibilityScope, and PayoutPayload schemas use versioned canonical encoding and golden vectors before G007, G012, or G016 consumes them, while display-alias changes cannot change cryptographic identities.
- Acceptance gate:
  1. Wallet authentication, human verification, claim authenticity, eligibility, provider authorization, and settlement cannot be inferred from one another.
  2. Every persisted model carries schema version, stable opaque ID, created/expiry timestamps, actor or producer reference, and privacy classification.
  3. Public serialization omits raw claims, nullifiers, session IDs, document hashes, case labels, notes, encrypted mapping keys, and secrets.
  4. Invalid, skipped, failed, expired, revoked, review-required, and unknown states remain distinguishable without encoding a benefits denial.
  5. Immutable ClaimContext, EligibilityScope, and PayoutPayload schemas use versioned canonical encoding and golden vectors before G007, G012, or G016 consumes them; display-alias changes cannot change cryptographic identities.

## WORLDCOIN-G006 Bind recipients and providers to wallets with server-verified SIWE

- Status: active
- Fib priority: 5000
- Priority: P0
- Track: world-aid-auth
- Parents: WORLDCOIN-G004, WORLDCOIN-G005, WORLDCOIN-G033, WORLDCOIN-G038
- Goal: Add MiniKit wallet-auth and SIWE verification so every recipient address and interactive provider address is bound to an authenticated principal independently of World ID.
- Evidence: at least 128 bits of server nonce entropy encoded as an alphanumeric-compatible value; domain, URI, chain, issued-at, expiry, request-ID, and statement checks; transactional one-time nonce store; official `verifySiweMessage` Node boundary; injected World Chain EIP-1271 client; EOA and smart-account fixtures; human-reviewed npm package/version/integrity/license/provenance/transitive-SBOM manifest; approved offline cache or internal mirror; pinned dependency lockfiles; `npm ci --offline` proof; address normalization; role-session binding; replay and cross-origin tests
- Outputs: wallet_interface/world_aid/auth.py, wallet_interface/routes/world_aid_auth.py, wallet_interface/ui/src/services/worldAidAuth.ts, wallet_interface/ui/package.json, wallet_interface/ui/package-lock.json, wallet_interface/services/world_siwe_verifier/index.mjs, docs/security/WORLD_SIWE_VERIFIER_SBOM.md, data/worldcoin_human_aid/supply-chain/world-siwe-npm-manifest.fixture.json, tests/world_aid/test_siwe_auth.py, tests/world_aid/fixtures/siwe_eip1271.json
- Validation: python -m pytest -q tests/world_aid/test_siwe_auth.py && npm --prefix wallet_interface/services/world_siwe_verifier ci --offline --ignore-scripts && npm --prefix wallet_interface/services/world_siwe_verifier test
- Bundle: worldcoin-human-aid/siwe-auth
- Parallel lane: world-aid-auth
- Embedding query: MiniKit walletAuth SIWE nonce address ownership recipient provider authentication replay
- AST query: SiweChallenge, SiwePrincipal, create_siwe_nonce, verify_siwe_message, bind_wallet_address
- Interfaces: MiniKit.walletAuth, official Node verifySiweMessage helper, injected World Chain EIP-1271 client, wallet session store
- Submodules:
- Generated artifacts: data/worldcoin_human_aid/supply-chain/world-siwe-npm-manifest.fixture.json
- Predicted files: wallet_interface/world_aid/auth.py, wallet_interface/routes/world_aid_auth.py, wallet_interface/ui/src/services/worldAidAuth.ts, wallet_interface/ui/package.json, wallet_interface/ui/package-lock.json, wallet_interface/services/world_siwe_verifier/index.mjs, docs/security/WORLD_SIWE_VERIFIER_SBOM.md, data/worldcoin_human_aid/supply-chain/world-siwe-npm-manifest.fixture.json, tests/world_aid/test_siwe_auth.py, tests/world_aid/fixtures/siwe_eip1271.json
- Conflict policy: use additive auth scopes and the existing wallet auth abstraction; never treat a World ID proof or client-reported address as a login
- Gap task: Implement an injected, offline-testable SIWE challenge and verification boundary with durable one-time nonce consumption.
- Acceptance criteria: Nonces carry at least 128 bits of cryptographic entropy, remain alphanumeric-compatible, are short-lived/single-use, and are scoped to domain/origin/chain/purpose; the pinned official verifier validates EOA and EIP-1271 fixtures through an injected client and atomically rejects altered/replayed messages; UI/verifier manifests, lockfiles, integrity checks, licenses, provenance, and transitive SBOM are human-reviewed and the exact tarballs are preloaded in an approved cache/mirror so `npm ci --offline` passes without registry egress; an agent cannot relax egress or substitute a package to unblock this goal; provider roles remain server-derived and deterministic tests make no wallet prompt or network call.
- Refinement: Generated TODO acceptance must satisfy these exact WORLDCOIN-G006 criteria: Nonces carry at least 128 bits of cryptographic entropy, remain alphanumeric-compatible, are short-lived/single-use, and are scoped to domain/origin/chain/purpose; the pinned official verifier validates EOA and EIP-1271 fixtures through an injected client and atomically rejects altered/replayed messages; UI/verifier manifests, lockfiles, integrity checks, licenses, provenance, and transitive SBOM are human-reviewed and the exact tarballs are preloaded in an approved cache/mirror so `npm ci --offline` passes without registry egress; an agent cannot relax egress or substitute a package to unblock this goal; provider roles remain server-derived and deterministic tests make no wallet prompt or network call.
- Acceptance gate:
  1. Nonces carry at least 128 bits of cryptographic entropy, remain alphanumeric-compatible, are short-lived and single-use, and are scoped to expected domain, origin, chain, and purpose.
  2. The pinned official verifier boundary validates both EOA and EIP-1271 World smart-account fixtures through an injected chain client and rejects changed address, chain, domain, URI, statement, request ID, expiry, or signature while consuming the nonce atomically.
  3. UI and verifier manifests, lockfiles, integrity checks, licenses, provenance, and transitive SBOM are human-reviewed; exact tarballs are preloaded in an approved cache or mirror and `npm ci --offline` passes without registry egress.
  4. An agent cannot relax egress or substitute a package to unblock this goal.
  5. Provider roles come from server-side authorization after SIWE, never from a signed client field.
  6. Focused tests use deterministic fixtures and injected verification; no wallet prompt or network call occurs.

## WORLDCOIN-G007 Make proof of human optional, context-bound, and replay-safe

- Status: active
- Fib priority: 5001
- Priority: P0
- Track: world-id-verification
- Parents: WORLDCOIN-G004, WORLDCOIN-G006
- Goal: Harden the existing IDKit flow so every action explicitly chooses one-time uniqueness or session continuity, the server enforces the corresponding stable humanity-binding or claim-bound signal, authorization derives from the authenticated principal instead of caller-supplied `actor_did`, and an explicit skip path remains available.
- Evidence: server challenge model consuming the early G005 canonical contracts; proof-mode and action policy; stable authenticated-principal humanity-binding signal for uniqueness; optional claim-bound session signal; authenticated-principal route dependency replacing caller-supplied actor identity; unchanged v4 response forwarding; response-field validation; proofOfHuman policy; optional user-presence policy; skip, failure, expiry, revocation, duplicate-binding, correction, and replay tests
- Outputs: wallet_interface/world_aid/humanity.py, wallet_interface/world_id.py, wallet_interface/routes/world_id.py, tests/world_aid/test_optional_humanity.py
- Validation: python -m pytest -q tests/world_aid/test_optional_humanity.py tests/test_world_id_wallet.py tests/test_world_id_wallet_api.py
- Bundle: worldcoin-human-aid/optional-humanity
- Parallel lane: world-id-verification
- Embedding query: optional World ID v4 proofOfHuman action signal nonce RP context liveness replay
- AST query: WorldIdChallenge, OptionalHumanVerification, AuthenticatedPrincipal, create_world_id_rp_signature, verify_world_id_proof
- Interfaces: IDKit 4.x, World v4 verify API, SIWE principal, WorldIdBinding
- Submodules:
- Predicted files: wallet_interface/world_aid/humanity.py, wallet_interface/world_id.py, wallet_interface/routes/world_id.py, tests/world_aid/test_optional_humanity.py
- Conflict policy: preserve current public World ID routes while adding strict expected-context parameters and a feature-flagged compatibility migration
- Gap task: Close the current gaps between returning signal context and enforcing it, and between trusting request/query `actor_did` values and deriving the actor from a verified SIWE-backed principal.
- Acceptance criteria: The server, not the browser, chooses proof mode, action, expected signal, nonce, RP, acceptable credential, and whether fresh user presence is requested; a uniqueness action uses a stable authenticated-principal humanity-binding signal and reuses only the existing valid binding across corrected claims, while a session action checks expected private continuity and a fresh session nullifier; verification rejects successful upstream responses whose proof mode, action, signal, nonce, RP, credential, environment, or lifetime differs from expected; no signal contains homelessness, eligibility, document facts, or case labels; `not_requested` and `skipped` route to manual or alternate review, not denial; all World routes derive authorization from the server-authenticated principal and expose minimum-necessary projections, never caller-supplied `actor_did` or raw bindings.
- Refinement: Generated TODO acceptance must satisfy these exact WORLDCOIN-G007 criteria: The server, not the browser, chooses proof mode, action, expected signal, nonce, RP, acceptable credential, and whether fresh user presence is requested; a uniqueness action uses a stable authenticated-principal humanity-binding signal and reuses only the existing valid binding across corrected claims, while a session action checks expected private continuity and a fresh session nullifier; verification rejects successful upstream responses whose proof mode, action, signal, nonce, RP, credential, environment, or lifetime differs from expected; no signal contains homelessness, eligibility, document facts, or case labels; `not_requested` and `skipped` route to manual or alternate review, not denial; all World routes derive authorization from the server-authenticated principal and expose minimum-necessary projections, never caller-supplied `actor_did` or raw bindings.
- Acceptance gate:
  1. The server, not the browser, chooses proof mode, action, expected signal, nonce, RP, acceptable credential, and whether fresh user presence is requested.
  2. A uniqueness action uses a stable authenticated-principal humanity-binding signal and reuses only the existing valid binding across corrected claims; a session action checks expected private continuity and a fresh session nullifier.
  3. Verification rejects successful upstream responses whose proof mode, action, signal, nonce, RP, credential, environment, or lifetime differs from expected.
  4. No signal contains homelessness, eligibility, document facts, or case labels; `not_requested` and `skipped` route to manual or alternate review, not denial.
  5. World ID status, signature, registration, and revocation routes derive authorization from the server-authenticated principal and return minimum-necessary projections; caller-supplied `actor_did`, raw bindings, and compatibility fields are never authoritative.

## WORLDCOIN-G008 Persist World ID uniqueness and session replay controls

- Status: active
- Fib priority: 8000
- Priority: P0
- Track: world-id-verification
- Parents: WORLDCOIN-G007, WORLDCOIN-G033
- Goal: Implement atomic, durable, cross-worker, action-scoped replay protection that distinguishes one-time nullifier uniqueness from stable session continuity and session-nullifier replay, with versioned HMAC pseudonyms and binding expiry/revocation invalidation.
- Evidence: strict unsigned-256-bit nullifier parser and canonical 32-byte encoding; secret-provider-backed HMAC key and version; keyed pseudonymous nullifier index; atomic compare-and-consume; proof-mode, action, RP, and environment scope; session continuity store with retention controls; session-nullifier ledger; concurrent cross-worker replay tests; restart persistence; dual-read or atomic-rekey HMAC rotation; binding expiry and revoke invalidation; erasure and audit semantics
- Outputs: wallet_interface/world_aid/nullifiers.py, wallet_interface/world_aid/storage.py, tests/world_aid/test_world_id_replay_store.py
- Validation: python -m pytest -q tests/world_aid/test_world_id_replay_store.py
- Bundle: worldcoin-human-aid/nullifier-ledger
- Parallel lane: world-id-storage
- Embedding query: World ID v4 nullifier session_id session_nullifier uniqueness replay durable atomic privacy
- AST query: WorldNullifierLedger, WorldNullifierHmacKey, SessionContinuityRecord, consume_nullifier, consume_session_nullifier, invalidate_world_id_binding
- Interfaces: World v4 verification result, encrypted wallet storage, audit receipt
- Submodules:
- Predicted files: wallet_interface/world_aid/nullifiers.py, wallet_interface/world_aid/storage.py, tests/world_aid/test_world_id_replay_store.py
- Conflict policy: persist only versioned HMAC pseudonyms and minimum continuity metadata; HMAC key material comes from the secret provider and never storage rows, logs, public receipts, or chain payloads
- Gap task: Replace process-local or advisory replay checks with a transactional cross-worker storage interface, durable HMAC key/version semantics, and expiry/revocation invalidation.
- Acceptance criteria: Malformed, signed, overflow, alternate-case, and leading-zero nullifier encodings are rejected or canonicalized to the same unsigned 256-bit, 32-byte HMAC input before lookup; two workers consuming the same proof-mode/RP/action/environment-scoped nullifier yield exactly one success across restart; uniqueness nullifiers, stable session IDs, and session nullifiers have distinct types, purposes, retention, and access rules; logs and errors omit all private identifiers; every replay row carries a non-secret HMAC key ID, rotation dual-reads all retained keys or atomically rekeys live rows, and duplicate, missing-key, partial-migration, expired, or revoked states fail closed without resetting replay history.
- Refinement: Generated TODO acceptance must satisfy these exact WORLDCOIN-G008 criteria: Malformed, signed, overflow, alternate-case, and leading-zero nullifier encodings are rejected or canonicalized to the same unsigned 256-bit, 32-byte HMAC input before lookup; two workers consuming the same proof-mode/RP/action/environment-scoped nullifier yield exactly one success across restart; uniqueness nullifiers, stable session IDs, and session nullifiers have distinct types, purposes, retention, and access rules; logs and errors omit all private identifiers; every replay row carries a non-secret HMAC key ID, rotation dual-reads all retained keys or atomically rekeys live rows, and duplicate, missing-key, partial-migration, expired, or revoked states fail closed without resetting replay history.
- Acceptance gate:
  1. Malformed, signed, overflow, alternate-case, and leading-zero nullifier encodings are rejected or canonicalized to the same unsigned 256-bit, 32-byte HMAC input before lookup.
  2. Two workers consuming the same proof-mode/RP/action/environment-scoped nullifier yield exactly one success, including across service restart.
  3. Uniqueness nullifiers, stable session IDs, and session nullifiers have distinct types, purposes, retention, and access rules.
  4. Logs and API errors omit the nullifier, session ID, signal, address, raw proof, and HMAC.
  5. Every replay row carries a non-secret HMAC key ID; rotation dual-reads all retained keys or atomically rekeys live rows, and duplicate, missing-key, partial-migration, expired, or revoked states fail closed without resetting replay history.

## WORLDCOIN-G009 Build issuer trust, claim freshness, and revocation registries

- Status: active
- Fib priority: 5002
- Priority: P0
- Track: eligibility-trust
- Parents: WORLDCOIN-G003, WORLDCOIN-G005, WORLDCOIN-G033
- Goal: Let authorized agencies and service providers attest document-derived claims under versioned schemas while supporting issuer keys, scopes, expiry, suspension, revocation roots, and key rotation.
- Evidence: issuer registry; claim schema registry; signature verification; issuance and expiry timestamps; allowed program and attribute scopes; revocation snapshot; rotation overlap; fixture issuers; World Identity Check feasibility adapter boundary
- Outputs: ipfs_datasets_py/ipfs_datasets_py/wallet/eligibility_issuers.py, docs/specs/WORLD_AID_ISSUER_TRUST.md, ipfs_datasets_py/tests/unit/wallet/test_eligibility_issuers.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/wallet/test_eligibility_issuers.py
- Bundle: worldcoin-human-aid/issuer-trust
- Parallel lane: eligibility-trust
- Embedding query: document wallet issuer signed claim schema trust scope freshness expiry revocation key rotation
- AST query: EligibilityIssuer, IssuerKey, ClaimSchema, RevocationSnapshot, verify_issued_claim
- Interfaces: ipfs_datasets_py document wallet, authorized issuer services, optional World Identity Check facts
- Submodules: ipfs_datasets_py
- Predicted files: ipfs_datasets_py/ipfs_datasets_py/wallet/eligibility_issuers.py, docs/specs/WORLD_AID_ISSUER_TRUST.md, ipfs_datasets_py/tests/unit/wallet/test_eligibility_issuers.py
- Conflict policy: add signed derived claims without copying source documents; issuer trust is program-scoped and cannot be inferred from World ID verification
- Gap task: Define how a document-wallet claim becomes cryptographically authentic and revocable before it can enter an eligibility witness.
- Acceptance criteria: Claims expose only typed derived attributes to the prover and retain encrypted provenance to the source document and issuer review; verification rejects untrusted, suspended, wrong-scope, stale, post-revocation, malformed, or ambiguously versioned claims; key rotation supports bounded overlap and deterministic historical verification without silently trusting a new key for old claims; World passport or Identity Check facts, if approved and available, implement one issuer adapter only and do not replace program-specific eligibility policy.
- Refinement: Generated TODO acceptance must satisfy these exact WORLDCOIN-G009 criteria: claims expose only typed derived attributes to the prover and retain encrypted provenance to the source document and issuer review; verification rejects untrusted, suspended, wrong-scope, stale, post-revocation, malformed, or ambiguously versioned claims; key rotation supports bounded overlap and deterministic historical verification without silently trusting a new key for old claims; World passport or Identity Check facts, if approved and available, implement one issuer adapter only and do not replace program-specific eligibility policy.
- Acceptance gate:
  1. Claims expose only typed derived attributes to the prover and retain encrypted provenance to the source document and issuer review.
  2. Verification rejects untrusted, suspended, wrong-scope, stale, post-revocation, malformed, or ambiguously versioned claims.
  3. Key rotation supports bounded overlap and deterministic historical verification without silently trusting a new key for old claims.
  4. World passport or Identity Check facts, if approved and available, implement one issuer adapter only and do not replace program-specific eligibility policy.

## WORLDCOIN-G010 Define a deterministic, versioned eligibility policy language

- Status: active
- Fib priority: 8001
- Priority: P0
- Track: eligibility-policy
- Parents: WORLDCOIN-G003, WORLDCOIN-G009
- Goal: Encode each provider program's allowable claim types, predicates, issuer scopes, benefit period, freshness, revocation, amount rule, and manual-review outcomes in a canonical policy that can compile to a ZK statement.
- Evidence: policy schema; canonical byte encoding and hash; type checker; deterministic compiler input; effective and expiry dates; policy supersession; test vectors; unsupported-predicate rejection; reviewer signature block
- Outputs: ipfs_datasets_py/ipfs_datasets_py/wallet/eligibility_policy.py, docs/specs/WORLD_AID_ELIGIBILITY_POLICY.md, ipfs_datasets_py/tests/unit/wallet/test_eligibility_policy.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/wallet/test_eligibility_policy.py
- Bundle: worldcoin-human-aid/eligibility-policy
- Parallel lane: eligibility-policy
- Embedding query: benefit eligibility policy language canonicalization issuer scope predicate period amount rule zero knowledge
- AST query: EligibilityPolicy, PolicyPredicate, PolicyOutcome, canonicalize_policy, compile_policy
- Interfaces: issuer claim schemas, eligibility prover, provider program administration
- Submodules: ipfs_datasets_py
- Predicted files: ipfs_datasets_py/ipfs_datasets_py/wallet/eligibility_policy.py, docs/specs/WORLD_AID_ELIGIBILITY_POLICY.md, ipfs_datasets_py/tests/unit/wallet/test_eligibility_policy.py
- Conflict policy: policies are immutable and content-addressed; changing any predicate, issuer, period, or amount rule creates a new version and review
- Gap task: Replace ad hoc application checks with a small, auditable policy grammar whose exact semantics can be proven and reproduced.
- Acceptance criteria: Equivalent policies canonicalize to identical bytes and hash, while any semantic change changes the hash; the grammar has an allowlist of bounded predicates and cannot execute code, make network calls, query an LLM, or inspect undeclared wallet data; `eligible`, `not_proven`, `review_required`, and `policy_error` remain distinct, and the compiler does not emit an autonomous denial; a policy identifies its authorized issuers, revocation root, claim freshness, benefit period, token/quote rule, and human approvers.
- Refinement: Generated TODO acceptance must satisfy these exact WORLDCOIN-G010 criteria: equivalent policies canonicalize to identical bytes and hash, while any semantic change changes the hash; the grammar has an allowlist of bounded predicates and cannot execute code, make network calls, query an LLM, or inspect undeclared wallet data; `eligible`, `not_proven`, `review_required`, and `policy_error` remain distinct, and the compiler does not emit an autonomous denial; a policy identifies its authorized issuers, revocation root, claim freshness, benefit period, token/quote rule, and human approvers.
- Acceptance gate:
  1. Equivalent policies canonicalize to identical bytes and hash, while any semantic change changes the hash.
  2. The grammar has an allowlist of bounded predicates and cannot execute code, make network calls, query an LLM, or inspect undeclared wallet data.
  3. `eligible`, `not_proven`, `review_required`, and `policy_error` remain distinct; the compiler does not emit an autonomous denial.
  4. A policy identifies its authorized issuers, revocation root, claim freshness, benefit period, token/quote rule, and human approvers.

## WORLDCOIN-G011 Require consent and least-privilege UCAN witness access

- Status: active
- Fib priority: 8002
- Priority: P0
- Track: eligibility-consent
- Parents: WORLDCOIN-G005, WORLDCOIN-G009, WORLDCOIN-G010
- Goal: Grant the eligibility prover temporary, purpose-bound access to only the document-wallet claim fields required by one program policy, with explicit recipient consent and revocation.
- Evidence: UCAN capability schema; claim-field allowlist; audience and purpose binding; expiry and nonce; consent receipt; revocation; witness access audit; explicit server-side prover trust boundary; isolated-worker and memory/temp-file/core-dump/swap policy; success, failure, timeout, and revocation cleanup; overbroad grant rejection; no-plaintext logging tests; client-side or confidential-compute feasibility note
- Outputs: ipfs_datasets_py/ipfs_datasets_py/wallet/eligibility_consent.py, docs/specs/WORLD_AID_ELIGIBILITY_CONSENT.md, ipfs_datasets_py/tests/unit/wallet/test_eligibility_consent.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/wallet/test_eligibility_consent.py
- Bundle: worldcoin-human-aid/witness-consent
- Parallel lane: eligibility-consent
- Embedding query: UCAN consent document wallet claim fields eligibility witness least privilege revocation
- AST query: EligibilityWitnessGrant, ConsentReceipt, authorize_witness_access, revoke_witness_grant
- Interfaces: ipfs_datasets_py UCAN wallet grants, eligibility policy, ZKP witness manager
- Submodules: ipfs_datasets_py
- Predicted files: ipfs_datasets_py/ipfs_datasets_py/wallet/eligibility_consent.py, docs/specs/WORLD_AID_ELIGIBILITY_CONSENT.md, ipfs_datasets_py/tests/unit/wallet/test_eligibility_consent.py
- Conflict policy: reuse existing UCAN primitives through a new narrow capability; do not grant prover access to whole documents or unrelated wallet records
- Gap task: Make witness derivation an explicit, revocable data-access operation rather than an implicit side effect of requesting a proof.
- Acceptance criteria: The grant names one policy version, audience, purpose, claim-field set, nonce, expiry, and recipient-controlled consent reference; the witness manager rejects missing, expired, revoked, wrong-audience, reused, or overbroad grants before reading claims; the server-side witness builder is explicitly classified as seeing decrypted selected claims and runs in an isolated no-telemetry worker with bounded memory, disabled core dumps and swap, no plaintext temp files, and verified cleanup on success, failure, timeout, and consent revocation; receipts record schema IDs and blinded commitments but never plaintext values, document bytes, local paths, private keys, or globally linkable subject IDs; consent withdrawal prevents new proofs under the reviewed settled-payout policy, and client-side or confidential-compute alternatives are assessed without overclaiming.
- Refinement: Generated TODO acceptance must satisfy these exact WORLDCOIN-G011 criteria: The grant names one policy version, audience, purpose, claim-field set, nonce, expiry, and recipient-controlled consent reference; the witness manager rejects missing, expired, revoked, wrong-audience, reused, or overbroad grants before reading claims; the server-side witness builder is explicitly classified as seeing decrypted selected claims and runs in an isolated no-telemetry worker with bounded memory, disabled core dumps and swap, no plaintext temp files, and verified cleanup on success, failure, timeout, and consent revocation; receipts record schema IDs and blinded commitments but never plaintext values, document bytes, local paths, private keys, or globally linkable subject IDs; consent withdrawal prevents new proofs under the reviewed settled-payout policy, and client-side or confidential-compute alternatives are assessed without overclaiming.
- Acceptance gate:
  1. The grant names one policy version, audience, purpose, claim-field set, nonce, expiry, and recipient-controlled consent reference.
  2. The witness manager rejects missing, expired, revoked, wrong-audience, reused, or overbroad grants before reading claims.
  3. The server-side witness builder is explicitly classified as seeing decrypted selected claims and runs in an isolated no-telemetry worker with bounded memory, disabled core dumps and swap, no plaintext temp files, and verified cleanup on success, failure, timeout, and consent revocation.
  4. Receipts record schema IDs and issuer/domain-blinded commitments but never plaintext values, document bytes, local paths, private keys, or globally linkable subject IDs.
  5. Consent withdrawal prevents new proofs under the reviewed settled-payout policy; client-side or confidential-compute alternatives are assessed without overclaiming.

## WORLDCOIN-G012 Implement a real eligibility ZK prover and verifier

- Status: active
- Fib priority: 13000
- Priority: P0
- Track: eligibility-zkp
- Parents: WORLDCOIN-G005, WORLDCOIN-G010, WORLDCOIN-G011, WORLDCOIN-G034, WORLDCOIN-G039
- Goal: Compile authorized claims and a versioned policy into a production-grade eligibility proof using the repository's ProveKit or Groth16 infrastructure, emit a stable one-benefit-scope nullifier, and preserve a fail-closed distinction between cryptographic proof and simulated profile receipt.
- Evidence: eligibility statement using the early G005 canonical contracts; private witness schema; issuer/domain-blinded subject commitments with equal hidden-secret proof; exact public inputs; immutable coordinated disbursement scope; holder-secret PRF nullifier; cross-provider stability, retry, key-rotation, reissuance, and new-case vectors; fresh proof-presentation binding; deterministic fixtures; prover and verifier adapters; proving and verification artifact identities; negative vectors; explicit simulated-proof rejection; backend capability and production-mode gates; human-reviewed backend/toolchain/version/checksum/license/provenance manifest; pre-staged offline binary or container; reproducible no-egress build evidence
- Outputs: ipfs_datasets_py/ipfs_datasets_py/logic/zkp/eligibility.py, ipfs_datasets_py/ipfs_datasets_py/wallet/eligibility_proof.py, ipfs_datasets_py/ipfs_datasets_py/logic/zkp/provekit/circuits/eligibility_v1/Nargo.toml, ipfs_datasets_py/ipfs_datasets_py/logic/zkp/provekit/circuits/eligibility_v1/Nargo.lock, ipfs_datasets_py/ipfs_datasets_py/logic/zkp/provekit/circuits/eligibility_v1/src/main.nr, ipfs_datasets_py/ipfs_datasets_py/logic/zkp/provekit/circuits/eligibility_v1/public-inputs.schema.json, ipfs_datasets_py/ipfs_datasets_py/logic/zkp/provekit/circuits/eligibility_v1/toolchain.lock, scripts/build_world_aid_eligibility_circuit.py, data/worldcoin_human_aid/zkp/toolchain-manifest.fixture.json, data/worldcoin_human_aid/zkp/eligibility-golden-vectors.fixture.json, ipfs_datasets_py/tests/unit/logic/zkp/test_eligibility_proof.py
- Validation: python scripts/build_world_aid_eligibility_circuit.py --check --offline && python -m pytest -q ipfs_datasets_py/tests/unit/logic/zkp/test_eligibility_proof.py
- Bundle: worldcoin-human-aid/eligibility-zkp
- Parallel lane: eligibility-zkp
- Embedding query: ProveKit Groth16 document wallet eligibility witness policy public inputs proof verification simulated rejection
- AST query: EligibilityStatement, EligibilityWitness, EligibilityScope, EligibilityScopeNullifier, EligibilityProofBackend, prove_eligibility, verify_eligibility
- Interfaces: ipfs_datasets_py logic.zkp backend registry, witness manager, issuer claims, eligibility policy
- Submodules: ipfs_datasets_py
- Generated artifacts: data/worldcoin_human_aid/zkp/toolchain-manifest.fixture.json, data/worldcoin_human_aid/zkp/eligibility-golden-vectors.fixture.json
- Predicted files: ipfs_datasets_py/ipfs_datasets_py/logic/zkp/eligibility.py, ipfs_datasets_py/ipfs_datasets_py/wallet/eligibility_proof.py, ipfs_datasets_py/ipfs_datasets_py/logic/zkp/provekit/circuits/eligibility_v1/Nargo.toml, ipfs_datasets_py/ipfs_datasets_py/logic/zkp/provekit/circuits/eligibility_v1/Nargo.lock, ipfs_datasets_py/ipfs_datasets_py/logic/zkp/provekit/circuits/eligibility_v1/src/main.nr, ipfs_datasets_py/ipfs_datasets_py/logic/zkp/provekit/circuits/eligibility_v1/public-inputs.schema.json, ipfs_datasets_py/ipfs_datasets_py/logic/zkp/provekit/circuits/eligibility_v1/toolchain.lock, scripts/build_world_aid_eligibility_circuit.py, data/worldcoin_human_aid/zkp/toolchain-manifest.fixture.json, data/worldcoin_human_aid/zkp/eligibility-golden-vectors.fixture.json, ipfs_datasets_py/tests/unit/logic/zkp/test_eligibility_proof.py
- Conflict policy: extend the existing ZKP registry and witness boundaries; do not rename or reinterpret document privacy-profile or location proof receipts
- Gap task: Define and prove the exact eligibility relation and stable one-benefit-scope nullifier, then require a recognized circuit, verifier key, policy hash, and exact proof-presentation binding in production mode.
- Acceptance criteria: Private inputs contain only consented claims, issuer signatures, issuer/domain-blinded commitments, required paths, and the stable hidden holder secret, while public inputs expose only the narrow result, immutable disbursement-scope/period/rule IDs, stable scope nullifier, policy/issuer/revocation references, and fresh claim bindings; the circuit proves that scoped credential commitments open to the same hidden secret and derives `eligibility_scope_nullifier` exactly from that secret plus `disbursement_scope_id_immutable`, `benefit_period_id`, and `eligibility_uniqueness_scope_id`, excluding provider and aliases so it remains stable across administering providers, retries, replacement proofs, address/key recovery, credential reissuance, new cases, and new claim/server nonces; claim commitment, provider, server nonce, case, recipient, amount, token, chain, and ordinary policy edits cannot change the scope nullifier, while a different reviewed disbursement scope, period, or uniqueness rule does; the fresh proof binds the exact G005 ClaimContext and PayoutPayload, and any changed expected input fails without changing scope semantics; the bounded circuit source constrains issuer signatures, hidden-subject equality, claim predicates, validity/revocation, canonical public inputs, and scope-nullifier derivation, while a human-reviewed checksum-pinned offline toolchain/build emits reproducible artifact hashes and golden vectors within reviewed proof-size/time/memory limits and any Groth16 choice requires an approved ceremony record; simulated, profile-only, test-only, unknown-backend/circuit, missing-artifact, stale/revoked, malformed, or unsupported-policy results fail closed, and the server-side prover hygiene gates from G011 are exercised.
- Refinement: Generated TODO acceptance must satisfy these exact WORLDCOIN-G012 criteria: Private inputs contain only consented claims, issuer signatures, issuer/domain-blinded commitments, required paths, and the stable hidden holder secret, while public inputs expose only the narrow result, immutable disbursement-scope/period/rule IDs, stable scope nullifier, policy/issuer/revocation references, and fresh claim bindings; the circuit proves that scoped credential commitments open to the same hidden secret and derives `eligibility_scope_nullifier` exactly from that secret plus `disbursement_scope_id_immutable`, `benefit_period_id`, and `eligibility_uniqueness_scope_id`, excluding provider and aliases so it remains stable across administering providers, retries, replacement proofs, address/key recovery, credential reissuance, new cases, and new claim/server nonces; claim commitment, provider, server nonce, case, recipient, amount, token, chain, and ordinary policy edits cannot change the scope nullifier, while a different reviewed disbursement scope, period, or uniqueness rule does; the fresh proof binds the exact G005 ClaimContext and PayoutPayload, and any changed expected input fails without changing scope semantics; the bounded circuit source constrains issuer signatures, hidden-subject equality, claim predicates, validity/revocation, canonical public inputs, and scope-nullifier derivation, while a human-reviewed checksum-pinned offline toolchain/build emits reproducible artifact hashes and golden vectors within reviewed proof-size/time/memory limits and any Groth16 choice requires an approved ceremony record; simulated, profile-only, test-only, unknown-backend/circuit, missing-artifact, stale/revoked, malformed, or unsupported-policy results fail closed, and the server-side prover hygiene gates from G011 are exercised.
- Acceptance gate:
  1. Private inputs contain only consented claims, issuer signatures, issuer/domain-blinded commitments, required paths, and the stable hidden holder secret; public inputs expose only the narrow result, immutable disbursement-scope/period/rule IDs, stable scope nullifier, policy/issuer/revocation references, and fresh claim bindings.
  2. The circuit proves that scoped credential commitments open to the same hidden secret and derives `eligibility_scope_nullifier` exactly from that secret plus `disbursement_scope_id_immutable`, `benefit_period_id`, and `eligibility_uniqueness_scope_id`, excluding provider and aliases. It remains stable across administering providers, retries, replacement proofs, address/key recovery, credential reissuance, new cases, and new claim/server nonces.
  3. Claim commitment, provider, server nonce, case, recipient, amount, token, chain, and ordinary policy edits cannot change the scope nullifier; a different reviewed disbursement scope, period, or uniqueness rule does, and no receipt calls it global proof of one human.
  4. The fresh proof binds the exact G005 ClaimContext and PayoutPayload; changing any expected input fails verification without changing scope semantics.
  5. The bounded circuit source constrains issuer signatures, hidden-subject equality, claim predicates, validity/revocation, canonical public inputs, and scope-nullifier derivation; its human-reviewed backend/toolchain/version/checksum/license/provenance manifest resolves only a pre-staged binary or container, and the no-egress build emits reproducible artifact hashes and golden vectors within reviewed proof-size/time/memory limits. Any Groth16 choice requires an approved ceremony record rather than developer-generated production parameters.
  6. Simulated, profile-only, test-only, unknown-backend/circuit, missing-artifact, stale/revoked, malformed, or unsupported-policy results fail closed; tests exercise G011 server-side prover hygiene.

## WORLDCOIN-G013 Register, pin, rotate, and revoke eligibility verifier artifacts

- Status: active
- Fib priority: 21000
- Priority: P0
- Track: eligibility-zkp
- Parents: WORLDCOIN-G012
- Goal: Make eligibility verification reproducible by pinning circuit, proving-system, verifier-key, policy-compiler, and public-input schema identities under an environment-scoped registry.
- Evidence: verifier manifest; content hashes and optional CIDs; environment and activation window; compiler version; policy compatibility range; rotation and rollback; revoked artifact list; signature verification; unknown-artifact rejection
- Outputs: ipfs_datasets_py/ipfs_datasets_py/logic/zkp/eligibility_registry.py, data/worldcoin_human_aid/zkp/verifier-manifest.fixture.json, ipfs_datasets_py/tests/unit/logic/zkp/test_eligibility_registry.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/logic/zkp/test_eligibility_registry.py
- Bundle: worldcoin-human-aid/verifier-registry
- Parallel lane: eligibility-zkp
- Embedding query: ZKP verifier registry circuit key artifact CID hash rotation revocation reproducible eligibility
- AST query: EligibilityVerifierManifest, EligibilityVerifierRegistry, resolve_verifier, revoke_verifier
- Interfaces: ipfs_datasets_py ZKP verifier registry, policy compiler, artifact storage
- Submodules: ipfs_datasets_py
- Generated artifacts: data/worldcoin_human_aid/zkp/verifier-manifest.fixture.json
- Predicted files: ipfs_datasets_py/ipfs_datasets_py/logic/zkp/eligibility_registry.py, data/worldcoin_human_aid/zkp/verifier-manifest.fixture.json, ipfs_datasets_py/tests/unit/logic/zkp/test_eligibility_registry.py
- Conflict policy: immutable manifests and append-only activation records; local fixtures may not become trusted production manifests by default
- Gap task: Prevent verifier-key or circuit drift from turning a syntactically valid proof into ambiguous authorization evidence.
- Acceptance criteria: Verification requires exact content hashes for circuit, verifier key, compiler, policy schema, and public-input schema; environment, activation time, expiry, suspension, and revocation are evaluated against a trusted clock and registry snapshot; rotation supports a bounded overlap for already issued proofs and a deterministic cutoff for new proofs; missing, locally generated, tampered, wrong-environment, expired, or revoked artifacts fail closed with privacy-safe reason codes.
- Refinement: Generated TODO acceptance must satisfy these exact WORLDCOIN-G013 criteria: verification requires exact content hashes for circuit, verifier key, compiler, policy schema, and public-input schema; environment, activation time, expiry, suspension, and revocation are evaluated against a trusted clock and registry snapshot; rotation supports a bounded overlap for already issued proofs and a deterministic cutoff for new proofs; missing, locally generated, tampered, wrong-environment, expired, or revoked artifacts fail closed with privacy-safe reason codes.
- Acceptance gate:
  1. Verification requires exact content hashes for circuit, verifier key, compiler, policy schema, and public-input schema.
  2. Environment, activation time, expiry, suspension, and revocation are evaluated against a trusted clock and registry snapshot.
  3. Rotation supports a bounded overlap for already issued proofs and a deterministic cutoff for new proofs.
  4. Missing, locally generated, tampered, wrong-environment, expired, or revoked artifacts fail closed with privacy-safe reason codes.

## WORLDCOIN-G014 Compose human, eligibility, and payout context without linking identities

- Status: active
- Fib priority: 34000
- Priority: P0
- Track: world-aid-claims
- Parents: WORLDCOIN-G007, WORLDCOIN-G008, WORLDCOIN-G013, WORLDCOIN-G016
- Goal: Implement the early G005 canonical ClaimContext, EligibilityScope, and PayoutPayload contracts as a fresh domain-separated commitment across SIWE, an optional existing World binding, eligibility-proof presentation, and exact payout context without redefining those upstream schemas or confusing the commitment with the stable scope nullifier/idempotency key.
- Evidence: canonical claim preimage; randomized commitment; domain and version tags; optional-humanity branch; payout-context binding; explicit stable-nullifier and fresh-commitment separation; payout payload hash reference; encrypted lookup record; test vectors; unlinkability note; substitution and cross-program replay tests
- Outputs: wallet_interface/world_aid/claims.py, docs/specs/WORLD_AID_CLAIM_COMPOSITION.md, tests/world_aid/test_claim_composition.py
- Validation: python -m pytest -q tests/world_aid/test_claim_composition.py
- Bundle: worldcoin-human-aid/claim-composition
- Parallel lane: world-aid-claims
- Embedding query: claim commitment optional World ID eligibility proof recipient provider program period token amount chain nonce privacy
- AST query: WorldAidClaimContext, ClaimCommitment, EligibilityScopeNullifier, PayoutPayloadHash, compose_claim_commitment, verify_claim_binding
- Interfaces: SIWE principal, World ID challenge, eligibility proof, payout intent
- Submodules:
- Predicted files: wallet_interface/world_aid/claims.py, docs/specs/WORLD_AID_CLAIM_COMPOSITION.md, tests/world_aid/test_claim_composition.py
- Conflict policy: compose opaque references through typed adapters across submodules; never copy private witness or raw World identifiers into the payout model
- Gap task: Make proof swapping, recipient substitution, amount changes, and cross-program replay cryptographically detectable while retaining an optional-humanity path and a stable, payload-independent one-per-scope idempotency identity.
- Acceptance criteria: The implementation consumes the G005 versioned canonical schemas and golden vectors for protocol/environment, immutable provider/program/disbursement-scope/period/rule IDs, policy hash, wallet binding, optional human-binding hash, recipient, chain, token, integer amount or quote, nonce, and expiry; optional World ID references an existing stable uniqueness binding or an expected session proof, while absence is explicit and a corrected claim never assumes a fresh uniqueness proof is available; changing an authorization field invalidates the fresh commitment/proof but cannot change the stable scope nullifier or idempotency key; a new claim nonce may create a replacement eligibility proof resolving to the same reservation, while a different payout payload hash hard-fails; public commitment/chain data reveal no sensitive status, claims, World identifiers, owner identity, or globally reusable subject commitment.
- Refinement: Generated TODO acceptance must satisfy these exact WORLDCOIN-G014 criteria: The implementation consumes the G005 versioned canonical schemas and golden vectors for protocol/environment, immutable provider/program/disbursement-scope/period/rule IDs, policy hash, wallet binding, optional human-binding hash, recipient, chain, token, integer amount or quote, nonce, and expiry; optional World ID references an existing stable uniqueness binding or an expected session proof, while absence is explicit and a corrected claim never assumes a fresh uniqueness proof is available; changing an authorization field invalidates the fresh commitment/proof but cannot change the stable scope nullifier or idempotency key; a new claim nonce may create a replacement eligibility proof resolving to the same reservation, while a different payout payload hash hard-fails; public commitment/chain data reveal no sensitive status, claims, World identifiers, owner identity, or globally reusable subject commitment.
- Acceptance gate:
  1. The implementation consumes the G005 versioned canonical schemas and golden vectors for protocol/environment, immutable provider/program/disbursement-scope/period/rule IDs, policy hash, wallet binding, optional human-binding hash, recipient, chain, token, integer amount or quote, nonce, and expiry.
  2. Optional World ID references an existing stable uniqueness binding or an expected session proof; absence is explicit, and a corrected claim never assumes a fresh uniqueness proof is available.
  3. Changing any authorization field invalidates the fresh commitment and associated proof, including after serialization round trips, but cannot create another eligibility-scope nullifier or payout idempotency key.
  4. A new claim or server nonce may create a new commitment and replacement proof, yet it resolves to the same eligibility-scope nullifier and existing idempotency record; any different payout payload hash produces `payout_payload_conflict`.
  5. The public commitment and chain payload cannot reveal homelessness, program reason, document types, claim values, World nullifier, session ID, wallet owner identity, or a globally reusable subject commitment.

## WORLDCOIN-G015 Implement accountable manual review, notice, correction, and appeal

- Status: active
- Fib priority: 13001
- Priority: P0
- Track: eligibility-decisions
- Parents: WORLDCOIN-G003, WORLDCOIN-G010, WORLDCOIN-G033
- Goal: Give authorized provider reviewers a structured workflow for proof uncertainty, document correction, eligibility decisions, recipient notice, appeal, override, and alternative service access without autonomous adverse decisions.
- Evidence: decision and reason-category model; reviewer role and conflict checks; evidence-correction request; notice templates; appeal deadlines and states; second-review option; immutable decision history; safe manual fallback
- Outputs: wallet_interface/world_aid/decisions.py, docs/runbooks/WORLD_AID_REVIEW_AND_APPEAL.md, tests/world_aid/test_eligibility_decisions.py
- Validation: python -m pytest -q tests/world_aid/test_eligibility_decisions.py
- Bundle: worldcoin-human-aid/review-appeal
- Parallel lane: eligibility-decisions
- Embedding query: benefit eligibility human review notice correction appeal override manual fallback adverse decision
- AST query: EligibilityReview, EligibilityDecision, AppealRecord, request_evidence_correction, decide_appeal
- Interfaces: provider staff authorization, eligibility policy, recipient notifications, audit service
- Submodules:
- Predicted files: wallet_interface/world_aid/decisions.py, docs/runbooks/WORLD_AID_REVIEW_AND_APPEAL.md, tests/world_aid/test_eligibility_decisions.py
- Conflict policy: automation may recommend a route or verify cryptography but only an authorized accountable role can record an adverse program decision
- Gap task: Implement explicit decision ownership and an accessible recovery path for every proof, identity, document, and technology failure.
- Acceptance criteria: `not_proven`, `technical_failure`, `missing_information`, `policy_mismatch`, and a human-recorded `ineligible` decision are distinct; an adverse decision records responsible reviewer, policy version, privacy-safe reason category, notice, correction path, appeal deadline, and immutable history; proof or World ID failure never silently closes a case and instead creates a review or alternate-access task according to program policy; review screens and public receipts expose the minimum information for the actor's role and never reveal unnecessary document contents.
- Refinement: Generated TODO acceptance must satisfy these exact WORLDCOIN-G015 criteria: `not_proven`, `technical_failure`, `missing_information`, `policy_mismatch`, and a human-recorded `ineligible` decision are distinct; an adverse decision records responsible reviewer, policy version, privacy-safe reason category, notice, correction path, appeal deadline, and immutable history; proof or World ID failure never silently closes a case and instead creates a review or alternate-access task according to program policy; review screens and public receipts expose the minimum information for the actor's role and never reveal unnecessary document contents.
- Acceptance gate:
  1. `not_proven`, `technical_failure`, `missing_information`, `policy_mismatch`, and a human-recorded `ineligible` decision are distinct.
  2. An adverse decision records responsible reviewer, policy version, privacy-safe reason category, notice, correction path, appeal deadline, and immutable history.
  3. Proof or World ID failure never silently closes a case; it creates a review or alternate-access task according to program policy.
  4. Review screens and public receipts expose the minimum information for the actor's role and never reveal unnecessary document contents.

## WORLDCOIN-G016 Define idempotent payout intents and a durable state machine

- Status: active
- Fib priority: 13002
- Priority: P0
- Track: world-aid-payouts
- Parents: WORLDCOIN-G005, WORLDCOIN-G010, WORLDCOIN-G012, WORLDCOIN-G033
- Goal: Model one authorized disbursement from draft through finality using a stable eligibility-scope idempotency identity and a separately pinned immutable payout payload hash, so retries or new cases cannot change payment fields or create a second one-per-period payout.
- Evidence: transition table; reviewed eligibility scope; stable scope nullifier; stable payout idempotency key; immutable recipient/address/amount/token/chain payload hash; atomic key-and-hash reservation; exact token base units; fiat-quote identity and expiry policy; compare-and-transition storage; retry and replacement semantics; payload-conflict reason; terminal and recoverable states; concurrency tests
- Outputs: wallet_interface/world_aid/payouts.py, docs/specs/WORLD_AID_PAYOUT_STATE_MACHINE.md, tests/world_aid/test_payout_state_machine.py
- Validation: python -m pytest -q tests/world_aid/test_payout_state_machine.py
- Bundle: worldcoin-human-aid/payout-state
- Parallel lane: world-aid-payouts
- Embedding query: WLD payout intent idempotency state machine draft proof approved submitted mined confirmed reorg
- AST query: PayoutIntent, PayoutState, EligibilityScopeNullifier, PayoutIdempotencyKey, PayoutPayloadHash, reserve_payout_scope, transition_payout
- Interfaces: eligibility decision, provider authorization, treasury adapter, chain reconciler
- Submodules:
- Predicted files: wallet_interface/world_aid/payouts.py, docs/specs/WORLD_AID_PAYOUT_STATE_MACHINE.md, tests/world_aid/test_payout_state_machine.py
- Conflict policy: atomically pin one payload hash to one stable scope idempotency key; retries and resumed/new cases reuse that identity, and payload correction requires a separate audited workflow rather than a new key
- Gap task: Prevent duplicate or changed payouts under retries, replacement proofs, new cases, crashes, concurrent workers, quote expiry, and chain uncertainty.
- Acceptance criteria: `payout_idempotency_key` derives only from the stable eligibility-scope nullifier and immutable coordinated `disbursement_scope_id_immutable`, `benefit_period_id`, and `eligibility_uniqueness_scope_id`, excluding provider/display aliases so an administering-provider change cannot create another entitlement; the identity excludes claim, nonce, case, recipient, amount, token, and chain; a separate payload hash binds a scope-blinded recipient-subject commitment, SIWE-bound address, integer amount, token, chain, and any fiat quote evidence; first authorization atomically pins the unique key to exactly one payload hash and every retry/proof/case/signer request must match or hard-fail `payout_payload_conflict`; illegal transitions, stale versions, duplicate submissions, and changed fields fail closed, while all ambiguous, pending, dropped, failed, replaced, or reorged attempts remain tied to the original authorization and reconciliation history.
- Refinement: Generated TODO acceptance must satisfy these exact WORLDCOIN-G016 criteria: `payout_idempotency_key` derives only from the stable eligibility-scope nullifier and immutable coordinated `disbursement_scope_id_immutable`, `benefit_period_id`, and `eligibility_uniqueness_scope_id`, excluding provider/display aliases so an administering-provider change cannot create another entitlement; the identity excludes claim, nonce, case, recipient, amount, token, and chain; a separate payload hash binds a scope-blinded recipient-subject commitment, SIWE-bound address, integer amount, token, chain, and any fiat quote evidence; first authorization atomically pins the unique key to exactly one payload hash and every retry/proof/case/signer request must match or hard-fail `payout_payload_conflict`; illegal transitions, stale versions, duplicate submissions, and changed fields fail closed, while all ambiguous, pending, dropped, failed, replaced, or reorged attempts remain tied to the original authorization and reconciliation history.
- Acceptance gate:
  1. `payout_idempotency_key` derives only from the stable eligibility-scope nullifier and immutable coordinated `disbursement_scope_id_immutable`, `benefit_period_id`, and `eligibility_uniqueness_scope_id`; provider/display aliases are excluded so an administering-provider change cannot create another entitlement.
  2. The stable idempotency identity deliberately excludes claim commitment, server nonce, case ID, recipient binding/address, amount, token, and chain, so changing a request field cannot create a second key.
  3. A separate domain-separated `payout_payload_hash` binds a scope-blinded recipient-subject commitment, SIWE-bound World Chain address, integer amount in base units, token contract, and chain ID. Fiat programs additionally pin price source, observation, quote expiry, and rounding evidence.
  4. First authorization atomically stores the unique idempotency key with exactly one payload hash. Every retry, replacement proof, resumed/new case, and signer request must match it; a mismatch hard-fails as `payout_payload_conflict`, never a new key or automatic correction.
  5. Illegal transitions, stale compare-and-swap versions, duplicate submissions, and changed approved fields fail closed; ambiguous, pending, dropped, failed, replaced, or reorged attempts remain tied to the original authorization and reconciliation history.

## WORLDCOIN-G017 Enforce provider organization and staff authorization

- Status: active
- Fib priority: 21001
- Priority: P0
- Track: provider-authorization
- Parents: WORLDCOIN-G006, WORLDCOIN-G015, WORLDCOIN-G016
- Goal: Authenticate provider organizations and staff, enforce program-scoped roles and separation of duties, and record who reviewed, approved, and initiated each payout.
- Evidence: provider registry; staff principal binding; role and program scopes; UCAN or policy grants; dual-control rule; suspension and revocation; authorization decision receipt; role-escalation and confused-deputy tests
- Outputs: wallet_interface/world_aid/provider_auth.py, wallet_interface/routes/world_aid_providers.py, tests/world_aid/test_provider_authorization.py
- Validation: python -m pytest -q tests/world_aid/test_provider_authorization.py
- Bundle: worldcoin-human-aid/provider-auth
- Parallel lane: provider-authorization
- Embedding query: service provider organization staff authorization role program scope dual approval payout
- AST query: ProviderOrganization, ProviderStaffPrincipal, ProviderGrant, authorize_provider_action
- Interfaces: SIWE or existing staff auth, UCAN grants, eligibility decisions, payout state machine
- Submodules:
- Predicted files: wallet_interface/world_aid/provider_auth.py, wallet_interface/routes/world_aid_providers.py, tests/world_aid/test_provider_authorization.py
- Conflict policy: reuse existing staff identity where available but derive all payout authority from server-side, revocable, program-scoped grants
- Gap task: Replace advisory provider context with enforceable organization, role, amount, and action authorization.
- Acceptance criteria: A provider proof-of-human or wallet signature alone grants no staff role, program access, eligibility-decision authority, or treasury authority; review, approval, and treasury submission roles are independently assignable, revocable, time-bound, and subject to configured separation of duties; suspended organizations or staff, wrong programs, excess amounts, self-approval, stale sessions, and delegated-role escalation are rejected; authorization receipts identify opaque actors, policy version, action, scope, and decision without publishing recipient case facts.
- Refinement: Generated TODO acceptance must satisfy these exact WORLDCOIN-G017 criteria: a provider proof-of-human or wallet signature alone grants no staff role, program access, eligibility-decision authority, or treasury authority; review, approval, and treasury submission roles are independently assignable, revocable, time-bound, and subject to configured separation of duties; suspended organizations or staff, wrong programs, excess amounts, self-approval, stale sessions, and delegated-role escalation are rejected; authorization receipts identify opaque actors, policy version, action, scope, and decision without publishing recipient case facts.
- Acceptance gate:
  1. A provider proof-of-human or wallet signature alone grants no staff role, program access, eligibility-decision authority, or treasury authority.
  2. Review, approval, and treasury submission roles are independently assignable, revocable, time-bound, and subject to configured separation of duties.
  3. Suspended organizations or staff, wrong programs, excess amounts, self-approval, stale sessions, and delegated-role escalation are rejected.
  4. Authorization receipts identify opaque actors, policy version, action, scope, and decision without publishing recipient case facts.

## WORLDCOIN-G018 Integrate controlled treasury custody, budgets, and signing

- Status: active
- Fib priority: 34001
- Priority: P0
- Track: world-aid-treasury
- Parents: WORLDCOIN-G003, WORLDCOIN-G017
- Goal: Define a signer-neutral treasury boundary supporting a Safe multisig, HSM/MPC, or reviewed custody service with per-program balances, limits, reservations, dual approval, and emergency pause.
- Evidence: TreasurySigner protocol; unsigned transaction request; Safe or custody adapter contract; WLD and native-gas budget ledgers; amount, gas, fee, and nonce reservations; daily and per-payout limits; signer policy; pause and recovery; fake signer tests; recipient gas/off-ramp support policy; key-management runbook
- Outputs: wallet_interface/world_aid/treasury.py, docs/runbooks/WORLD_AID_TREASURY_OPERATIONS.md, tests/world_aid/test_treasury_controls.py
- Validation: python -m pytest -q tests/world_aid/test_treasury_controls.py
- Bundle: worldcoin-human-aid/treasury-controls
- Parallel lane: world-aid-treasury
- Embedding query: WLD treasury Safe multisig HSM MPC custody budget limits dual approval emergency pause
- AST query: TreasurySigner, TreasuryPolicy, BudgetReservation, build_unsigned_transfer, authorize_signing
- Interfaces: Safe 1.4.1 or approved custody provider, provider authorization, payout intents
- Submodules:
- Predicted files: wallet_interface/world_aid/treasury.py, docs/runbooks/WORLD_AID_TREASURY_OPERATIONS.md, tests/world_aid/test_treasury_controls.py
- Conflict policy: production signing is an injected external capability; repository code and fixtures contain no private key, seed, mnemonic, API token, or default hot-wallet signer
- Gap task: Put auditable organizational controls between an approved payout intent and any request to sign WLD transfer calldata.
- Acceptance criteria: Code builds and inspects an unsigned request offline and only an explicitly configured external signer authorizes it; atomic reservation binds program, period, payout, WLD amount, native-gas balance, fee ceiling, custody account, and nonce with safe release/replacement rules; per-payout/daily/program/signer/destination/gas/fee/pause policies are rechecked immediately before signing, and insufficient native gas blocks submission without releasing the entitlement to a second payout; each program documents how recipients can safely use or off-ramp WLD, including gas, volatility, accessibility, and an alternative path; tests use a production-ineligible fake signer and production rejects raw keys in files/environment.
- Refinement: Generated TODO acceptance must satisfy these exact WORLDCOIN-G018 criteria: Code builds and inspects an unsigned request offline and only an explicitly configured external signer authorizes it; atomic reservation binds program, period, payout, WLD amount, native-gas balance, fee ceiling, custody account, and nonce with safe release/replacement rules; per-payout/daily/program/signer/destination/gas/fee/pause policies are rechecked immediately before signing, and insufficient native gas blocks submission without releasing the entitlement to a second payout; each program documents how recipients can safely use or off-ramp WLD, including gas, volatility, accessibility, and an alternative path; tests use a production-ineligible fake signer and production rejects raw keys in files/environment.
- Acceptance gate:
  1. Code can build and inspect an unsigned request offline; only an explicitly configured external signer can authorize it.
  2. Atomic reservation binds program, period, payout, WLD amount, native-gas balance, fee ceiling, custody account, and nonce; failure, cancellation, and replacement have safe release rules.
  3. Per-payout, daily, program, signer, destination, gas, fee, and pause policies are rechecked immediately before signing; insufficient native gas blocks submission without releasing the entitlement to a second payout.
  4. Each program documents recipient gas, safe-use/off-ramp, volatility, accessibility, and alternative-disbursement support.
  5. Autonomous tests use a fake signer that production cannot accept, and production rejects filesystem/environment raw keys.

## WORLDCOIN-G019 Add a validated World Chain and WLD client

- Status: active
- Fib priority: 8003
- Priority: P0
- Track: world-chain
- Parents: WORLDCOIN-G004, WORLDCOIN-G005
- Goal: Provide an injected World Chain JSON-RPC client with explicit network, WLD token, fee, nonce, receipt, event, and RPC-failover contracts.
- Evidence: chain registry for mainnet 480 and Sepolia 4801; OP Stack L2 plus Ethereum settlement model; checksummed token manifest; WLD mainnet contract validation; RPC allowlist and health; ERC-20 and Safe/EntryPoint envelope codecs; nonce strategy; native gas and fee bounds; included/safe/finalized block tags; receipt and log decoder; offline fixtures
- Outputs: wallet_interface/world_aid/world_chain.py, wallet_interface/world_aid/world_contracts.py, data/worldcoin_human_aid/world-chain/contracts.fixture.json, tests/world_aid/test_world_chain_client.py
- Validation: python -m pytest -q tests/world_aid/test_world_chain_client.py
- Bundle: worldcoin-human-aid/world-chain-client
- Parallel lane: world-chain
- Embedding query: World Chain JSON RPC chain 480 Sepolia 4801 WLD ERC20 transfer receipt log failover
- AST query: WorldChainClient, WorldChainNetwork, WldContract, encode_erc20_transfer, decode_transfer_log
- Interfaces: World Chain RPC providers, WLD ERC-20, treasury signer, transaction reconciler
- Submodules:
- Generated artifacts: data/worldcoin_human_aid/world-chain/contracts.fixture.json
- Predicted files: wallet_interface/world_aid/world_chain.py, wallet_interface/world_aid/world_contracts.py, data/worldcoin_human_aid/world-chain/contracts.fixture.json, tests/world_aid/test_world_chain_client.py
- Conflict policy: all providers and contract manifests are injected and environment-scoped; no implicit chain, token, RPC, explorer, or gas defaults in production
- Gap task: Implement a dependency-light chain boundary that can deterministically construct and verify WLD transfers without conflating user operations and treasury transactions.
- Acceptance criteria: Mainnet 480 and Sepolia 4801 are distinct OP Stack environments with explicit Ethereum/Ethereum-Sepolia settlement policy, and the approved checksummed token manifest is never browser-selected; schema-validated/cross-checked RPC responses distinguish included, safe, finalized, and configured L1 settlement states, while chain/token/code, malformed quantity, native-gas/fee, and nonce mismatches fail closed; direct ERC-20 plus Safe/EntryPoint custody-envelope encoding/decoding and Transfer logs match fixtures in integer base units; imports/tests perform no RPC, with transport, clock, fee, settlement, and chain responses injected.
- Refinement: Generated TODO acceptance must satisfy these exact WORLDCOIN-G019 criteria: Mainnet 480 and Sepolia 4801 are distinct OP Stack environments with explicit Ethereum/Ethereum-Sepolia settlement policy, and the approved checksummed token manifest is never browser-selected; schema-validated/cross-checked RPC responses distinguish included, safe, finalized, and configured L1 settlement states, while chain/token/code, malformed quantity, native-gas/fee, and nonce mismatches fail closed; direct ERC-20 plus Safe/EntryPoint custody-envelope encoding/decoding and Transfer logs match fixtures in integer base units; imports/tests perform no RPC, with transport, clock, fee, settlement, and chain responses injected.
- Acceptance gate:
  1. Mainnet chain ID 480 and Sepolia chain ID 4801 are distinct typed environments; the mainnet WLD address is checksummed from an approved manifest, never accepted from a browser.
  2. RPC responses are schema-validated and cross-checked and distinguish L2 included, safe, finalized, and configured L1 settlement states; chain/token/code, malformed quantity, native-gas/fee, and unsafe nonce state fail closed.
  3. Direct ERC-20 plus Safe/EntryPoint custody-envelope encoding/decoding and Transfer-event decoding match fixtures and preserve integer base units.
  4. Import and focused tests perform no RPC call; transport, clock, fee estimator, settlement, and chain responses are injected.

## WORLDCOIN-G020 Support optional provider-interactive MiniKit transactions

- Status: active
- Fib priority: 34002
- Priority: P1
- Track: world-chain
- Parents: WORLDCOIN-G006, WORLDCOIN-G017, WORLDCOIN-G019
- Goal: Build and test an optional, fixture-only MiniKit `sendTransaction` adapter for an authorized provider, recognizing that current World docs support transaction execution on mainnet rather than Sepolia; no live canary is authorized here and `MiniKit.pay` is never an outbound aid API.
- Evidence: mainnet-only support note and gate-time revalidation; allowlisted contract/function manifest; typed transaction request; write-ahead user-operation intent; userOpHash result; user-operation and custody-envelope resolver; cancellation/rejection/ambiguity states; Developer Portal allowlist checklist; injected MiniKit fixtures
- Outputs: wallet_interface/ui/src/services/worldAidMiniKit.ts, wallet_interface/world_aid/minikit.py, tests/world_aid/test_minikit_transaction_adapter.py, wallet_interface/ui/tests/world-aid-minikit.spec.ts
- Validation: python -m pytest -q tests/world_aid/test_minikit_transaction_adapter.py && npm --prefix wallet_interface/ui test -- tests/world-aid-minikit.spec.ts
- Bundle: worldcoin-human-aid/minikit-provider-transaction
- Parallel lane: world-chain
- Embedding query: MiniKit sendTransaction provider interactive WLD userOpHash user operation allowlist World Chain
- AST query: WorldAidMiniKitTransaction, submitProviderTransaction, resolve_user_operation, MiniKit.sendTransaction
- Interfaces: MiniKit.sendTransaction, Developer Portal user-operation API, provider SIWE session
- Submodules:
- Predicted files: wallet_interface/ui/src/services/worldAidMiniKit.ts, wallet_interface/world_aid/minikit.py, tests/world_aid/test_minikit_transaction_adapter.py, wallet_interface/ui/tests/world-aid-minikit.spec.ts
- Conflict policy: this is an optional adapter behind a capability flag; never fall back from provider authorization to a beneficiary-originated `MiniKit.pay` request
- Gap task: Implement and document the interactive smart-account path while preserving treasury payout as a separate adapter.
- Acceptance criteria: The adapter is fixture-only, is not a Sepolia/MVP dependency, and documents current mainnet-only Mini App transaction support plus a separate human-gated tiny-canary requirement; the client requests only server-produced allowlisted chain/target/function/token/recipient/amount data for an approved intent; a write-ahead intent precedes the prompt, `userOpHash` is not settlement, and backend resolution validates the EntryPoint/account envelope and final WLD transfer; rejection, expiry, changed calldata, wrong chain/contract/function, lost response, or ambiguity do not consume or duplicate authorization; fake MiniKit/API fixtures cannot prompt or submit.
- Refinement: Generated TODO acceptance must satisfy these exact WORLDCOIN-G020 criteria: The adapter is fixture-only, is not a Sepolia/MVP dependency, and documents current mainnet-only Mini App transaction support plus a separate human-gated tiny-canary requirement; the client requests only server-produced allowlisted chain/target/function/token/recipient/amount data for an approved intent; a write-ahead intent precedes the prompt, `userOpHash` is not settlement, and backend resolution validates the EntryPoint/account envelope and final WLD transfer; rejection, expiry, changed calldata, wrong chain/contract/function, lost response, or ambiguity do not consume or duplicate authorization; fake MiniKit/API fixtures cannot prompt or submit.
- Acceptance gate:
  1. The adapter remains fixture-only and outside Sepolia and MVP dependencies; it documents current mainnet-only Mini App transaction support and requires a separate human-gated, minimum-value canary before any live use.
  2. The client can request only server-produced, allowlisted chain, target, function, token, recipient, and amount data for an already approved intent.
  3. A durable write-ahead intent precedes the prompt. Client success returns a `userOpHash`, not settlement; backend resolution validates the expected EntryPoint/account custody envelope and final WLD transfer.
  4. User rejection, expiry, changed calldata, wrong chain/contract/function, lost response, and ambiguity do not consume or duplicate payout authorization.
  5. Tests use fake MiniKit and Developer Portal responses and cannot prompt a wallet or submit a user operation.

## WORLDCOIN-G021 Implement controlled direct WLD treasury payouts

- Status: active
- Fib priority: 55000
- Priority: P0
- Track: world-aid-payouts
- Parents: WORLDCOIN-G014, WORLDCOIN-G017, WORLDCOIN-G018, WORLDCOIN-G019
- Goal: Build the default service-provider disbursement adapter that converts one fully approved payout intent into one signer-reviewed WLD ERC-20 transfer request.
- Evidence: final preflight verifier; recipient and amount binding; WLD/native-gas/fee budget checks; typed write-ahead SubmissionAttempt; reserved custody account and nonce; unsigned and signed envelope hashes; stable Safe/custody/user-operation request IDs; transactional outbox; broadcast ambiguity state and resolver; duplicate-submission lock; linked replacement policy; proposed fail-closed WLD-transfer runtime guard; fake-chain success, lost-response, crash, and failure receipts
- Outputs: wallet_interface/world_aid/wld_payout.py, wallet_interface/world_aid/runtime_guards.py, tests/world_aid/test_wld_payout_adapter.py, tests/world_aid/test_runtime_guards.py
- Validation: python -m pytest -q tests/world_aid/test_wld_payout_adapter.py tests/world_aid/test_runtime_guards.py
- Bundle: worldcoin-human-aid/wld-payout
- Parallel lane: world-aid-payouts
- Embedding query: provider treasury WLD ERC20 disbursement eligibility approval recipient amount idempotent signing
- AST query: WldPayoutAdapter, PayoutPreflight, SubmissionAttempt, prepare_wld_transfer, persist_signed_envelope, resolve_ambiguous_submission, submit_wld_transfer, require_wld_transfers_enabled
- Interfaces: claim commitment, provider authorization, treasury signer, World Chain client, payout state machine
- Submodules:
- Predicted files: wallet_interface/world_aid/wld_payout.py, wallet_interface/world_aid/runtime_guards.py, tests/world_aid/test_wld_payout_adapter.py, tests/world_aid/test_runtime_guards.py
- Conflict policy: make signing and broadcasting separate injected capabilities; this goal implements no production signer and authorizes no live transfer
- Gap task: Connect proof and organizational approvals to an exact transfer request while revalidating every invariant immediately before submission.
- Acceptance criteria: Preflight requires current SIWE/proof/artifacts/claim/approvals/intent/quote, exact idempotency-payload pair, WLD/native-gas/fee reservations, and chain/token/custody match; before external signing or broadcast, one database transaction persists SubmissionAttempt with custody account, reserved nonce, unsigned envelope hash, signer idempotency/request ID, and outbox record, then a raw signed envelope/hash or stable Safe/userOp/custody handle is durably recorded before submission; lost responses/timeouts enter `submission_ambiguous` and must query known hashes, custody handle, account nonce, chain, and outbox before retry, never allocating an uncoordinated nonce/envelope; returned hash means submitted only, replacements link to the same authorization, and duplicate/crash/refusal/insufficient funds/changed calldata cannot create another authorization; `WORLD_AID_WLD_TRANSFERS_ENABLED` defaults/fails closed and independently blocks signing/broadcast even when reads are enabled.
- Refinement: Generated TODO acceptance must satisfy these exact WORLDCOIN-G021 criteria: Preflight requires current SIWE/proof/artifacts/claim/approvals/intent/quote, exact idempotency-payload pair, WLD/native-gas/fee reservations, and chain/token/custody match; before external signing or broadcast, one database transaction persists SubmissionAttempt with custody account, reserved nonce, unsigned envelope hash, signer idempotency/request ID, and outbox record, then a raw signed envelope/hash or stable Safe/userOp/custody handle is durably recorded before submission; lost responses/timeouts enter `submission_ambiguous` and must query known hashes, custody handle, account nonce, chain, and outbox before retry, never allocating an uncoordinated nonce/envelope; returned hash means submitted only, replacements link to the same authorization, and duplicate/crash/refusal/insufficient funds/changed calldata cannot create another authorization; `WORLD_AID_WLD_TRANSFERS_ENABLED` defaults/fails closed and independently blocks signing/broadcast even when reads are enabled.
- Acceptance gate:
  1. Preflight requires current SIWE, proof/artifacts, claim, approvals, intent/quote, exact idempotency-payload pair, WLD/native-gas/fee reservations, and chain/token/custody match.
  2. Before external signing or broadcast, one database transaction persists SubmissionAttempt with custody account, reserved nonce, unsigned envelope hash, signer idempotency/request ID, and outbox; the raw signed envelope/hash or stable Safe/userOp/custody handle is durably recorded before submission.
  3. Lost responses and timeouts enter `submission_ambiguous` and query known hashes, custody handle, account nonce, chain, and outbox before retry; no uncoordinated nonce or envelope is allocated.
  4. A returned hash means submitted only; replacements link to the same authorization, and duplicate, crash, refusal, insufficient funds, or changed calldata cannot create another authorization.
  5. `WORLD_AID_WLD_TRANSFERS_ENABLED` defaults and fails closed and independently blocks signing and broadcast even when external reads are enabled.

## WORLDCOIN-G022 Reconcile transaction receipts, Transfer logs, confirmations, and reorgs

- Status: active
- Fib priority: 89000
- Priority: P0
- Track: world-chain
- Parents: WORLDCOIN-G019, WORLDCOIN-G021, WORLDCOIN-G033
- Goal: Resolve every direct, Safe/custody, or MiniKit submission attempt to canonical World Chain settlement by decoding the custody envelope, verifying the exact inner WLD transfer, and distinguishing L2 included/operational confirmation from safe, finalized, and configured L1 settlement states.
- Evidence: watcher and SubmissionAttempt state; direct/Safe/EntryPoint envelope decoder; receipt verifier; event-index identity; OP Stack included/safe/finalized/L1 policy; RPC disagreement handling; Safe/userOp/custody-handle-to-txHash resolution; ambiguity and nonce resolution; safe/finalized regression and reorg rollback; dropped/replaced detection; periodic reconciliation report
- Outputs: wallet_interface/world_aid/reconciliation.py, scripts/reconcile_world_aid_payouts.py, tests/world_aid/test_payout_reconciliation.py
- Validation: python -m pytest -q tests/world_aid/test_payout_reconciliation.py
- Bundle: worldcoin-human-aid/chain-reconciliation
- Parallel lane: world-chain
- Embedding query: World Chain transaction receipt WLD Transfer log confirmations reorg replacement reconciliation userOpHash
- AST query: PayoutReconciler, SettlementEvidence, CustodyEnvelope, decode_safe_execution, decode_user_operation, verify_transfer_receipt, resolve_submission_attempt, reconcile_payouts
- Interfaces: World Chain RPC, MiniKit user-operation API, payout state storage
- Submodules:
- Generated artifacts: data/worldcoin_human_aid/reconciliation/reconciliation-report.fixture.json
- Predicted files: wallet_interface/world_aid/reconciliation.py, scripts/reconcile_world_aid_payouts.py, tests/world_aid/test_payout_reconciliation.py
- Conflict policy: chain state is observational evidence, not a mutable source of eligibility; rollback only settlement state and never recreate authorization
- Gap task: Make “sent” and “confirmed” evidence-based states and recover safely from pending, failed, ambiguous, replaced, and reorged transactions.
- Acceptance criteria: Reconciliation starts from a persisted SubmissionAttempt and resolves raw transaction, Safe transaction, custody request, or userOp handles without trusting a client hash; direct transactions target WLD, while Safe/module/EntryPoint outer calls are decoded to exactly one authorized inner WLD transfer and expected treasury account; settlement requires expected chain/token/code, successful receipt, exact treasury sender/recipient/integer amount, unique Transfer log/index, canonical block, and the policy's distinct OP Stack included, operational-confirmed, safe, finalized, and optional L1-settled states, never calling block depth alone finality; missing/duplicate/mismatched events, envelope mismatch, RPC disagreement, nonce ambiguity, canonical/safe/finalized regression, replacement, or reorg prevents or reverses settlement and reuses the original authorization; reconciliation is idempotent/restart-safe/rate-limited/privacy-safe and never creates an automatic replacement payout.
- Refinement: Generated TODO acceptance must satisfy these exact WORLDCOIN-G022 criteria: Reconciliation starts from a persisted SubmissionAttempt and resolves raw transaction, Safe transaction, custody request, or userOp handles without trusting a client hash; direct transactions target WLD, while Safe/module/EntryPoint outer calls are decoded to exactly one authorized inner WLD transfer and expected treasury account; settlement requires expected chain/token/code, successful receipt, exact treasury sender/recipient/integer amount, unique Transfer log/index, canonical block, and the policy's distinct OP Stack included, operational-confirmed, safe, finalized, and optional L1-settled states, never calling block depth alone finality; missing/duplicate/mismatched events, envelope mismatch, RPC disagreement, nonce ambiguity, canonical/safe/finalized regression, replacement, or reorg prevents or reverses settlement and reuses the original authorization; reconciliation is idempotent/restart-safe/rate-limited/privacy-safe and never creates an automatic replacement payout.
- Acceptance gate:
  1. Reconciliation starts from a persisted SubmissionAttempt and resolves raw transaction, Safe transaction, custody request, or userOp handles without trusting a client hash.
  2. Direct transactions target WLD; Safe, module, or EntryPoint outer calls decode to exactly one authorized inner WLD transfer and expected treasury account.
  3. Settlement requires expected chain/token/code, successful receipt, exact treasury sender/recipient/integer amount, unique Transfer log/index, canonical block, and distinct OP Stack included, operational-confirmed, safe, finalized, and optional L1-settled policy states; block depth alone is never called finality.
  4. Missing/duplicate/mismatched events, envelope mismatch, RPC disagreement, nonce ambiguity, canonical/safe/finalized regression, replacement, or reorg prevents or reverses settlement and reuses the original authorization.
  5. Reconciliation is idempotent, restart-safe, rate-limited, and privacy-safe and never creates an automatic replacement payout.

## WORLDCOIN-G023 Publish privacy-preserving audit receipts and controlled exports

- Status: active
- Fib priority: 144000
- Priority: P0
- Track: world-aid-audit
- Parents: WORLDCOIN-G014, WORLDCOIN-G015, WORLDCOIN-G022, WORLDCOIN-G033
- Goal: Produce separate recipient, provider, auditor, and public projections that prove process integrity and settlement without exposing protected documents, identity links, nullifiers, or eligibility facts.
- Evidence: append-only event schema; role projection matrix; salted opaque references; receipt integrity chain; encrypted case mapping; export authorization; redaction tests; deletion and retention markers; residual public transfer-graph risk and consent; address-reuse warning; explorer-link default-off policy; alternative disbursement path
- Outputs: wallet_interface/world_aid/audit.py, docs/specs/WORLD_AID_AUDIT_RECEIPTS.md, tests/world_aid/test_audit_receipts.py
- Validation: python -m pytest -q tests/world_aid/test_audit_receipts.py
- Bundle: worldcoin-human-aid/audit-receipts
- Parallel lane: world-aid-audit
- Embedding query: privacy preserving audit receipt payout settlement eligibility proof redaction encrypted mapping public projection
- AST query: WorldAidAuditEvent, AuditProjection, PublicPayoutReceipt, export_audit_bundle
- Interfaces: decision history, claim commitment, payout state, chain receipt, encrypted storage
- Submodules:
- Predicted files: wallet_interface/world_aid/audit.py, docs/specs/WORLD_AID_AUDIT_RECEIPTS.md, tests/world_aid/test_audit_receipts.py
- Conflict policy: derive projections from one append-only event stream; additions to public schema require privacy review and negative disclosure tests
- Gap task: Provide verifiability and reconciliation evidence without turning a public ledger into a registry of vulnerable people.
- Acceptance criteria: Public receipts expose only unavoidable transaction/integrity data and never label homelessness or identify a benefit, document, claim, World record, or global subject; consent explicitly states that treasury, recipient, amount, and timing remain publicly graph-linkable, warns against address reuse, defaults explorer links off, never calls the transfer anonymous, and offers an alternative when risk is unacceptable; provider/auditor projections follow least privilege/purpose/jurisdiction/retention/export policy; integrity checks detect deletion/reordering/mutation/cross-case projection; planted secrets/identifiers/nullifiers/claims/case labels are absent from public JSON/logs/metrics/URLs.
- Refinement: Generated TODO acceptance must satisfy these exact WORLDCOIN-G023 criteria: Public receipts expose only unavoidable transaction/integrity data and never label homelessness or identify a benefit, document, claim, World record, or global subject; consent explicitly states that treasury, recipient, amount, and timing remain publicly graph-linkable, warns against address reuse, defaults explorer links off, never calls the transfer anonymous, and offers an alternative when risk is unacceptable; provider/auditor projections follow least privilege/purpose/jurisdiction/retention/export policy; integrity checks detect deletion/reordering/mutation/cross-case projection; planted secrets/identifiers/nullifiers/claims/case labels are absent from public JSON/logs/metrics/URLs.
- Acceptance gate:
  1. Public receipts expose only unavoidable transaction and integrity data and never label homelessness or identify a benefit, document, claim, World record, or globally linkable subject.
  2. Consent states that treasury, recipient, amount, and timing remain publicly graph-linkable, warns against address reuse, defaults explorer links off, never calls the transfer anonymous, and offers an alternative when risk is unacceptable.
  3. Provider and auditor projections follow least privilege, purpose, jurisdiction, retention, and export-approval policy.
  4. Integrity checks detect event deletion, reordering, mutation, or projection from a different case while supporting authorized redaction markers.
  5. A fixture corpus with planted secrets, identifiers, nullifiers, claims, and case labels proves they do not appear in public JSON, logs, metrics, or URLs.

## WORLDCOIN-G024 Expose cohesive World-aid service APIs

- Status: active
- Fib priority: 89001
- Priority: P0
- Track: world-aid-api
- Parents: WORLDCOIN-G007, WORLDCOIN-G008, WORLDCOIN-G013, WORLDCOIN-G014, WORLDCOIN-G015, WORLDCOIN-G016, WORLDCOIN-G017, WORLDCOIN-G021, WORLDCOIN-G022, WORLDCOIN-G033, WORLDCOIN-G034
- Goal: Add authenticated APIs for case create/get/cancel/timeline, optional human proof, issuer credential issuance/import/correction, consent, eligibility proving/verification, review, payout approval/submission/status/settlement, appeal, and safe receipts.
- Evidence: versioned case and credential lifecycle schemas; authenticated routes with server-derived principal/tenant; idempotency headers; role scopes; state transition enforcement; problem-detail reason codes; rate limits; minimum-necessary projections; privacy-safe OpenAPI; offline API contract tests
- Outputs: wallet_interface/routes/world_aid.py, wallet_interface/world_aid/service.py, wallet_interface/api.py, docs/api/WORLD_HUMAN_AID_API.md, tests/world_aid/test_world_aid_api.py
- Validation: python -m pytest -q tests/world_aid/test_world_aid_api.py
- Bundle: worldcoin-human-aid/service-api
- Parallel lane: world-aid-api
- Embedding query: World aid API optional human proof eligibility review payout approval status settlement appeal receipt
- AST query: WorldAidService, create_world_aid_router, create_case, cancel_case, import_eligibility_credential, create_claim_challenge, approve_payout, get_settlement
- Interfaces: FastAPI wallet service, SIWE sessions, proof service, provider service, payout service
- Submodules:
- Predicted files: wallet_interface/routes/world_aid.py, wallet_interface/world_aid/service.py, wallet_interface/api.py, docs/api/WORLD_HUMAN_AID_API.md, tests/world_aid/test_world_aid_api.py
- Conflict policy: register additive versioned routes and delegate domain logic to services; do not duplicate cryptographic or transition checks in route handlers
- Gap task: Turn the isolated trust-domain modules into a least-privilege API with stable, retry-safe contracts.
- Acceptance criteria: APIs cover case create/get/cancel/timeline and the G034 credential lifecycle before proof/payout flows; every mutation derives principal and tenant from server middleware, checks CSRF/origin/state/version/rate/idempotency, and atomically audits, never accepting `actor_did`, issuer/provider role, or wallet ownership from caller authority; clients cannot choose trust root, policy/scope, World proof mode/action/signal, verifier, treasury, chain/token/amount, or settlement state; status uses authenticated minimum projections rather than durable-model dictionaries, errors prevent enumeration, and OpenAPI/fixtures contain no secrets, raw proofs/bindings/documents, or private-key endpoints.
- Refinement: Generated TODO acceptance must satisfy these exact WORLDCOIN-G024 criteria: APIs cover case create/get/cancel/timeline and the G034 credential lifecycle before proof/payout flows; every mutation derives principal and tenant from server middleware, checks CSRF/origin/state/version/rate/idempotency, and atomically audits, never accepting `actor_did`, issuer/provider role, or wallet ownership from caller authority; clients cannot choose trust root, policy/scope, World proof mode/action/signal, verifier, treasury, chain/token/amount, or settlement state; status uses authenticated minimum projections rather than durable-model dictionaries, errors prevent enumeration, and OpenAPI/fixtures contain no secrets, raw proofs/bindings/documents, or private-key endpoints.
- Acceptance gate:
  1. APIs cover case create/get/cancel/timeline and the G034 issuer credential lifecycle before proof and payout flows.
  2. Every mutation derives principal and tenant from server middleware, checks CSRF/origin/state/version/rate/idempotency, and atomically audits; caller `actor_did`, role, or wallet-ownership assertions are never authoritative.
  3. Clients cannot choose trust root, policy/scope, World proof mode/action/signal, verifier, treasury, chain/token/amount, or settlement state.
  4. Status uses authenticated minimum projections rather than durable-model dictionaries, errors prevent enumeration, and OpenAPI/fixtures contain no secrets, raw proofs/bindings/documents, or private-key endpoints.

## WORLDCOIN-G025 Build a consent-forward recipient claim and payout experience

- Status: active
- Fib priority: 144001
- Priority: P1
- Track: world-aid-ui
- Parents: WORLDCOIN-G006, WORLDCOIN-G007, WORLDCOIN-G011, WORLDCOIN-G014, WORLDCOIN-G015, WORLDCOIN-G024
- Goal: Let a recipient understand the program, connect or use an alternate address path, optionally use World ID, choose document claims with informed consent, request review, see an exact WLD amount or quote, and track settlement or appeal.
- Evidence: stepwise claim flow; explicit optional World ID choice; prover trust disclosure and consent details; claim-selection summary; accessible proof progress; WLD volatility, public transfer-graph, address-reuse, gas/off-ramp, and fee disclosure; alternative disbursement path; status timeline; correction and appeal controls; localization and screen-reader tests
- Outputs: wallet_interface/ui/src/features/world-aid/index.ts, wallet_interface/ui/src/features/world-aid/WorldAidRecipientFlow.tsx, wallet_interface/ui/tests/world-aid-recipient.spec.ts, docs/ux/WORLD_AID_RECIPIENT_FLOW.md
- Validation: npm --prefix wallet_interface/ui test -- tests/world-aid-recipient.spec.ts
- Bundle: worldcoin-human-aid/recipient-ui
- Parallel lane: world-aid-ui-recipient
- Embedding query: recipient World ID optional consent document wallet eligibility WLD quote payout status appeal accessible
- AST query: WorldAidRecipientFlow, OptionalWorldIdStep, EligibilityConsentStep, PayoutStatusTimeline
- Interfaces: World-aid API, MiniKit walletAuth and IDKit, document wallet, accessibility and localization
- Submodules:
- Predicted files: wallet_interface/ui/src/features/world-aid/index.ts, wallet_interface/ui/src/features/world-aid/WorldAidRecipientFlow.tsx, wallet_interface/ui/tests/world-aid-recipient.spec.ts, docs/ux/WORLD_AID_RECIPIENT_FLOW.md
- Conflict policy: add an isolated feature surface and reuse shared wallet components; preserve current World ID panel and document-wallet flows until migration tests pass
- Gap task: Implement a trauma-informed, privacy-minimizing recipient path that makes optional choices and consequences clear.
- Acceptance criteria: World ID is optional with an equivalent continue-with-review path and no dark pattern; consent names program, selected claim fields, that the witness builder sees decrypted selected claims, prover purpose/retention/expiry/revocation, and what ZK does not hide; before acceptance the user sees exact WLD/quote/rounding/fees/destination/volatility plus public treasury-to-recipient graph linkability, address-reuse warning, gas/off-ramp usability, correction, and a reviewed alternative path; keyboard/screen-reader/zoom/reduced-motion/low-bandwidth/localization/session-expiry/interruption tests pass without private values or anonymity overclaims.
- Refinement: Generated TODO acceptance must satisfy these exact WORLDCOIN-G025 criteria: World ID is optional with an equivalent continue-with-review path and no dark pattern; consent names program, selected claim fields, that the witness builder sees decrypted selected claims, prover purpose/retention/expiry/revocation, and what ZK does not hide; before acceptance the user sees exact WLD/quote/rounding/fees/destination/volatility plus public treasury-to-recipient graph linkability, address-reuse warning, gas/off-ramp usability, correction, and a reviewed alternative path; keyboard/screen-reader/zoom/reduced-motion/low-bandwidth/localization/session-expiry/interruption tests pass without private values or anonymity overclaims.
- Acceptance gate:
  1. World ID is presented as optional anti-abuse verification with a clearly equivalent continue-with-review path and no dark pattern.
  2. Consent names the program, selected claim fields, that the witness builder sees decrypted selected claims, prover purpose/retention/expiry/revocation, and what ZK does not hide.
  3. Before acceptance, the user sees exact WLD/quote/rounding/fees/destination/volatility plus public treasury-to-recipient graph linkability, address-reuse warning, gas/off-ramp usability, correction, and a reviewed alternative path.
  4. Keyboard, screen-reader, zoom, reduced-motion, low-bandwidth, localization, session-expiry, and interrupted-proof fixtures pass without private values or anonymity overclaims.

## WORLDCOIN-G026 Build a least-privilege provider review and payout dashboard

- Status: active
- Fib priority: 144002
- Priority: P1
- Track: world-aid-ui
- Parents: WORLDCOIN-G017, WORLDCOIN-G018, WORLDCOIN-G022, WORLDCOIN-G024
- Goal: Give authorized provider staff bounded queues for eligibility review, dual payout approval, treasury policy checks, settlement exceptions, reconciliation, and appeal handling.
- Evidence: role-filtered queues; minimum-necessary case projection; approval comparison view; budget and limit display; dual approval; transaction evidence; exception and reorg queue; audit export request; accessibility tests
- Outputs: wallet_interface/ui/src/features/world-aid-provider/index.ts, wallet_interface/ui/src/features/world-aid-provider/WorldAidProviderDashboard.tsx, wallet_interface/ui/tests/world-aid-provider.spec.ts, docs/ux/WORLD_AID_PROVIDER_FLOW.md
- Validation: npm --prefix wallet_interface/ui test -- tests/world-aid-provider.spec.ts
- Bundle: worldcoin-human-aid/provider-ui
- Parallel lane: world-aid-ui-provider
- Embedding query: provider dashboard eligibility review dual approval treasury WLD settlement reconciliation appeal least privilege
- AST query: WorldAidProviderDashboard, EligibilityReviewQueue, PayoutApprovalPanel, ReconciliationQueue
- Interfaces: provider and world-aid APIs, audit projections, treasury and reconciliation services
- Submodules:
- Predicted files: wallet_interface/ui/src/features/world-aid-provider/index.ts, wallet_interface/ui/src/features/world-aid-provider/WorldAidProviderDashboard.tsx, wallet_interface/ui/tests/world-aid-provider.spec.ts, docs/ux/WORLD_AID_PROVIDER_FLOW.md
- Conflict policy: role-filter server responses before rendering; UI hiding is never an authorization control
- Gap task: Implement an accountable operations surface that highlights changed fields, limits, conflicts, proof status, and chain uncertainty before staff act.
- Acceptance criteria: The normal ZK review displays only proof result, policy/version, accepted issuer-set status, credential freshness/revocation status, wallet binding, and manual-path availability, never derived claim values/provenance/raw documents; claim/provenance access exists only in a separately consented, purpose-scoped manual-review projection with access audit; approval shows immutable provider/program/disbursement-scope/period/recipient/chain/token/amount/quote/proof/policy/prior-approver/treasury facts; ambiguous, pending, failed, mismatched, replaced, reorged, and settlement-regressed attempts remain exceptions and cannot be UI-confirmed; role/concurrency/stale/revoked/self-approval/export/accessibility tests pass.
- Refinement: Generated TODO acceptance must satisfy these exact WORLDCOIN-G026 criteria: The normal ZK review displays only proof result, policy/version, accepted issuer-set status, credential freshness/revocation status, wallet binding, and manual-path availability, never derived claim values/provenance/raw documents; claim/provenance access exists only in a separately consented, purpose-scoped manual-review projection with access audit; approval shows immutable provider/program/disbursement-scope/period/recipient/chain/token/amount/quote/proof/policy/prior-approver/treasury facts; ambiguous, pending, failed, mismatched, replaced, reorged, and settlement-regressed attempts remain exceptions and cannot be UI-confirmed; role/concurrency/stale/revoked/self-approval/export/accessibility tests pass.
- Acceptance gate:
  1. Normal ZK review displays only proof result, policy/version, accepted issuer-set status, credential freshness/revocation status, wallet binding, and manual-path availability; it never shows derived claim values, provenance, or raw documents.
  2. Claim or provenance access exists only in a separately consented, purpose-scoped manual-review projection with an access audit.
  3. Approval displays immutable provider, program, disbursement scope, period, recipient, chain, token, amount/quote, proof/policy, prior approver, and treasury checks.
  4. Ambiguous, pending, failed, mismatched, replaced, reorged, or settlement-regressed attempts remain exceptions and cannot be UI-confirmed; role, concurrency, stale/revoked, self-approval, export, and accessibility tests pass.

## WORLDCOIN-G027 Implement no-smartphone, no-World-App, offline, and assisted paths

- Status: active
- Fib priority: 233000
- Priority: P0
- Track: world-aid-accessibility
- Parents: WORLDCOIN-G003, WORLDCOIN-G015, WORLDCOIN-G025, WORLDCOIN-G026
- Goal: Ensure people can request service, provide consent, correct evidence, receive notice, appeal, and receive an authorized benefit without World ID, World App, an Orb, a personal smartphone, reliable connectivity, or crypto expertise.
- Evidence: assisted-service protocol; paper and verbal notice templates; proxy and shared-device safeguards; offline resume token; alternate address custody policy; manual eligibility path; alternative disbursement escalation; accessibility acceptance fixtures
- Outputs: wallet_interface/world_aid/assisted_access.py, docs/runbooks/WORLD_AID_ASSISTED_ACCESS.md, tests/world_aid/test_assisted_access.py, wallet_interface/ui/tests/world-aid-accessibility.spec.ts
- Validation: python -m pytest -q tests/world_aid/test_assisted_access.py && npm --prefix wallet_interface/ui test -- tests/world-aid-accessibility.spec.ts
- Bundle: worldcoin-human-aid/assisted-access
- Parallel lane: world-aid-accessibility
- Embedding query: homeless service no smartphone no World App no Orb offline assisted access manual eligibility alternative payout
- AST query: AssistedAccessCase, OfflineResumeToken, AlternateAddressPlan, create_assisted_access_case
- Interfaces: provider staff workflow, document wallet consent, eligibility review, payout and appeal services
- Submodules:
- Predicted files: wallet_interface/world_aid/assisted_access.py, docs/runbooks/WORLD_AID_ASSISTED_ACCESS.md, tests/world_aid/test_assisted_access.py, wallet_interface/ui/tests/world-aid-accessibility.spec.ts
- Conflict policy: assisted paths require explicit safeguards and recipient notice but cannot be a lower-rights or silently lower-priority queue
- Gap task: Implement equivalent process states and protections for assisted, shared-device, interrupted-connectivity, and non-crypto cases.
- Acceptance criteria: The path supports informed consent and withdrawal without requiring a private device, persistent browser storage, email, phone number, World ID, or wallet signature from staff; shared-device sessions clear sensitive state, prevent staff from impersonating recipients, and issue privacy-safe resumable references; alternate custody or disbursement requires an approved program policy, plain-language disclosure, responsible human, and auditable recipient acknowledgment; service access, review timing, correction, appeal, and privacy protections are equivalent to the digital path.
- Refinement: Generated TODO acceptance must satisfy these exact WORLDCOIN-G027 criteria: the path supports informed consent and withdrawal without requiring a private device, persistent browser storage, email, phone number, World ID, or wallet signature from staff; shared-device sessions clear sensitive state, prevent staff from impersonating recipients, and issue privacy-safe resumable references; alternate custody or disbursement requires an approved program policy, plain-language disclosure, responsible human, and auditable recipient acknowledgment; service access, review timing, correction, appeal, and privacy protections are equivalent to the digital path.
- Acceptance gate:
  1. The path supports informed consent and withdrawal without requiring a private device, persistent browser storage, email, phone number, World ID, or wallet signature from staff.
  2. Shared-device sessions clear sensitive state, prevent staff from impersonating recipients, and issue privacy-safe resumable references.
  3. Alternate custody or disbursement requires an approved program policy, plain-language disclosure, responsible human, and auditable recipient acknowledgment.
  4. Service access, review timing, correction, appeal, and privacy protections are equivalent to the digital path.

## WORLDCOIN-G028 Add adversarial, property, API, UI, and end-to-end gates

- Status: active
- Fib priority: 377000
- Priority: P0
- Track: world-aid-quality
- Parents: WORLDCOIN-G008, WORLDCOIN-G013, WORLDCOIN-G014, WORLDCOIN-G016, WORLDCOIN-G022, WORLDCOIN-G024, WORLDCOIN-G025, WORLDCOIN-G026, WORLDCOIN-G027, WORLDCOIN-G033, WORLDCOIN-G034
- Goal: Establish deterministic release gates for cryptography, privacy, authorization, state transitions, chain ambiguity, accessibility, and backward compatibility across the complete flow.
- Evidence: unit and property tests; proof mutation corpus; API contracts; browser flows; concurrency and restart tests; log and receipt secret scans; RPC fault and reorg fixtures; threat-model mapping; existing World ID regression suite; cross-adapter external-call and WLD-transfer guard tests
- Outputs: tests/world_aid/test_world_aid_end_to_end.py, tests/world_aid/test_world_aid_security.py, ipfs_datasets_py/tests/unit/logic/zkp/test_eligibility_adversarial.py, wallet_interface/ui/tests/world-aid-security.spec.ts, docs/reports/WORLD_AID_TEST_MATRIX.md
- Validation: python -m pytest -q tests/world_aid/test_world_aid_end_to_end.py tests/world_aid/test_world_aid_security.py ipfs_datasets_py/tests/unit/logic/zkp/test_eligibility_adversarial.py && npm --prefix wallet_interface/ui test -- tests/world-aid-security.spec.ts
- Bundle: worldcoin-human-aid/quality-gates
- Parallel lane: world-aid-quality
- Embedding query: adversarial World ID SIWE ZKP payout replay authorization privacy reorg accessibility end to end tests
- AST query: EligibilityProof, ClaimCommitment, PayoutState, PayoutReconciler, WorldAidService, require_external_calls_enabled, require_wld_transfers_enabled
- Interfaces: all World-aid domain modules, wallet API, UI, ZKP and chain adapters
- Submodules: ipfs_datasets_py
- Generated artifacts: data/worldcoin_human_aid/quality/release-gate.fixture.json
- Predicted files: tests/world_aid/test_world_aid_end_to_end.py, tests/world_aid/test_world_aid_security.py, ipfs_datasets_py/tests/unit/logic/zkp/test_eligibility_adversarial.py, wallet_interface/ui/tests/world-aid-security.spec.ts, docs/reports/WORLD_AID_TEST_MATRIX.md
- Conflict policy: tests use synthetic persons, documents, issuers, keys, wallets, proofs, and chain data only; network access and real assets are prohibited
- Gap task: Prove that each trust boundary fails closed under substitution, replay, concurrency, restart, dependency failure, malicious payload, and privacy probing.
- Acceptance criteria: The matrix covers SIWE replay, World signal/action substitution, nullifier races, issuer and verifier revocation, proof/public-input mutation, cross-policy replay, recipient/amount substitution, role escalation, duplicate payout, RPC lies, and reorg; property tests cover canonicalization and state-machine invariants, while concurrency fixtures prove atomic nonce, nullifier, approval, budget, idempotency, and submission behavior; secret and privacy scans fail on raw document text, planted PII, World identifiers, claim values, private keys, bearer tokens, case labels, or unredacted errors in public artifacts; existing wallet and World ID suites remain passing, and all external integrations use injected fakes or recorded schema-only fixtures; with existing `WORLD_ID_ENABLED=0` and proposed `WORLD_AID_EXTERNAL_CALLS_ENABLED=0` and `WORLD_AID_WLD_TRANSFERS_ENABLED=0`, all network, signer, and broadcaster spies observe zero calls, missing, malformed, and false-like values fail closed, and each adapter has a bypass-regression test.
- Refinement: Generated TODO acceptance must satisfy these exact WORLDCOIN-G028 criteria: the matrix covers SIWE replay, World signal/action substitution, nullifier races, issuer and verifier revocation, proof/public-input mutation, cross-policy replay, recipient/amount substitution, role escalation, duplicate payout, RPC lies, and reorg; property tests cover canonicalization and state-machine invariants, while concurrency fixtures prove atomic nonce, nullifier, approval, budget, idempotency, and submission behavior; secret and privacy scans fail on raw document text, planted PII, World identifiers, claim values, private keys, bearer tokens, case labels, or unredacted errors in public artifacts; existing wallet and World ID suites remain passing, and all external integrations use injected fakes or recorded schema-only fixtures; with existing `WORLD_ID_ENABLED=0` and proposed `WORLD_AID_EXTERNAL_CALLS_ENABLED=0` and `WORLD_AID_WLD_TRANSFERS_ENABLED=0`, all network, signer, and broadcaster spies observe zero calls, missing, malformed, and false-like values fail closed, and each adapter has a bypass-regression test.
- Acceptance gate:
  1. The matrix covers SIWE replay, World signal/action substitution, nullifier races, issuer and verifier revocation, proof/public-input mutation, cross-policy replay, recipient/amount substitution, role escalation, duplicate payout, RPC lies, and reorg.
  2. Property tests cover canonicalization and state-machine invariants, while concurrency fixtures prove atomic nonce, nullifier, approval, budget, idempotency, and submission behavior.
  3. Secret and privacy scans fail on raw document text, planted PII, World identifiers, claim values, private keys, bearer tokens, case labels, or unredacted errors in public artifacts.
  4. Existing wallet and World ID suites remain passing, and all external integrations use injected fakes or recorded schema-only fixtures.
  5. With existing `WORLD_ID_ENABLED=0` and proposed `WORLD_AID_EXTERNAL_CALLS_ENABLED=0` and `WORLD_AID_WLD_TRANSFERS_ENABLED=0`, all network, signer, and broadcaster spies observe zero calls; missing, malformed, and false-like values fail closed, and each adapter has a bypass-regression test.

## WORLDCOIN-G029 Add privacy-safe observability and incident/reconciliation operations

- Status: active
- Fib priority: 610000
- Priority: P0
- Track: world-aid-operations
- Parents: WORLDCOIN-G022, WORLDCOIN-G023, WORLDCOIN-G024, WORLDCOIN-G028
- Goal: Operate the flow with actionable service, proof, authorization, treasury, chain, reconciliation, and accessibility signals while preventing identifiers and eligibility data from entering telemetry.
- Evidence: metrics allowlist; structured redacted logs; trace correlation IDs; SLOs; payout and reconciliation alerts; privacy canary tests; incident severity matrix; pause and recovery procedures; daily reconciliation and unresolved-liability report
- Outputs: wallet_interface/world_aid/observability.py, docs/runbooks/WORLD_AID_INCIDENT_RESPONSE.md, docs/runbooks/WORLD_AID_RECONCILIATION.md, tests/world_aid/test_observability_privacy.py
- Validation: python -m pytest -q tests/world_aid/test_observability_privacy.py
- Bundle: worldcoin-human-aid/operations
- Parallel lane: world-aid-operations
- Embedding query: privacy safe observability WLD payout reconciliation alert SLO incident pause recovery
- AST query: WorldAidTelemetry, redact_world_aid_event, ReconciliationAlert, pause_world_aid_payouts
- Interfaces: logging and metrics, audit events, payout state, treasury pause, RPC health
- Submodules:
- Predicted files: wallet_interface/world_aid/observability.py, docs/runbooks/WORLD_AID_INCIDENT_RESPONSE.md, docs/runbooks/WORLD_AID_RECONCILIATION.md, tests/world_aid/test_observability_privacy.py
- Conflict policy: allowlist low-cardinality telemetry fields; never rely on denylist-only redaction or use addresses, nullifiers, claim commitments, payout IDs, or case IDs as metric labels
- Gap task: Make stalled or unsafe transfers visible and recoverable without creating a shadow database of vulnerable recipients.
- Acceptance criteria: Metrics cover counts, latency, error categories, queue age, proof backend health, budget utilization, RPC health, and reconciliation age using bounded dimensions; structured logs and traces use ephemeral correlation references and exclude addresses, nullifiers, sessions, signals, documents, claims, eligibility decisions, secrets, and raw transaction calldata; alerts distinguish delayed, failed, mismatched, duplicate-risk, signer, budget, RPC, and reorg incidents and link to reviewed response procedures; emergency pause blocks new signing while preserving review, appeal, read-only status, reconciliation, and safe recovery.
- Refinement: Generated TODO acceptance must satisfy these exact WORLDCOIN-G029 criteria: metrics cover counts, latency, error categories, queue age, proof backend health, budget utilization, RPC health, and reconciliation age using bounded dimensions; structured logs and traces use ephemeral correlation references and exclude addresses, nullifiers, sessions, signals, documents, claims, eligibility decisions, secrets, and raw transaction calldata; alerts distinguish delayed, failed, mismatched, duplicate-risk, signer, budget, RPC, and reorg incidents and link to reviewed response procedures; emergency pause blocks new signing while preserving review, appeal, read-only status, reconciliation, and safe recovery.
- Acceptance gate:
  1. Metrics cover counts, latency, error categories, queue age, proof backend health, budget utilization, RPC health, and reconciliation age using bounded dimensions.
  2. Structured logs and traces use ephemeral correlation references and exclude addresses, nullifiers, sessions, signals, documents, claims, eligibility decisions, secrets, and raw transaction calldata.
  3. Alerts distinguish delayed, failed, mismatched, duplicate-risk, signer, budget, RPC, and reorg incidents and link to reviewed response procedures.
  4. Emergency pause blocks new signing while preserving review, appeal, read-only status, reconciliation, and safe recovery.

## WORLDCOIN-G030 Prepare an offline World Chain Sepolia pilot packet and verifier

- Status: active
- Fib priority: 987000
- Priority: P0
- Track: world-aid-pilot
- Parents: WORLDCOIN-G001, WORLDCOIN-G018, WORLDCOIN-G021, WORLDCOIN-G022, WORLDCOIN-G027, WORLDCOIN-G028, WORLDCOIN-G029
- Goal: Prepare a synthetic, low-value Sepolia pilot template, deterministic receipt fixture, human authorization checklist, and offline evidence verifier; actual remote configuration and transaction evidence belong only to blocked G035.
- Evidence: synthetic participant and issuer set; test policy and proof; reviewed Developer Portal manifest template; direct-treasury signer, native-gas, token, amount, and fee limits; preflight dry run; manual authorization checklist; deterministic custody/receipt/Transfer fixture; reconciliation, privacy, transfer-graph consent, recipient usability, accessibility, pause, and rollback report; explicit MiniKit fixture-only note
- Outputs: docs/runbooks/WORLD_AID_SEPOLIA_PILOT.md, data/worldcoin_human_aid/pilot/sepolia-pilot-template.json, scripts/verify_world_aid_sepolia_pilot.py, tests/world_aid/test_sepolia_pilot_verifier.py
- Validation: python -m pytest -q tests/world_aid/test_sepolia_pilot_verifier.py
- Bundle: worldcoin-human-aid/sepolia-pilot
- Parallel lane: world-aid-pilot
- Embedding query: World Chain Sepolia pilot synthetic eligibility proof WLD testnet receipt reconciliation privacy rollback
- AST query: SepoliaPilotManifest, SepoliaPilotReceipt, verify_sepolia_pilot
- Interfaces: World Chain Sepolia fixture schema, reviewed Developer Portal manifest template, external human signer contract, local receipt verifier
- Submodules:
- Generated artifacts: data/worldcoin_human_aid/pilot/sepolia-pilot-template.json
- Predicted files: docs/runbooks/WORLD_AID_SEPOLIA_PILOT.md, data/worldcoin_human_aid/pilot/sepolia-pilot-template.json, scripts/verify_world_aid_sepolia_pilot.py, tests/world_aid/test_sepolia_pilot_verifier.py
- Conflict policy: the supervisor prepares and verifies artifacts only; it may not acquire test funds, change remote settings, prompt a wallet, sign, broadcast, or deploy
- Gap task: Create a reproducible testnet acceptance packet with hard human authorization boundaries and no real-person or production data.
- Acceptance criteria: All identities, documents, claims, issuer keys, wallets, policies, receipts, and amounts are synthetic and visibly test-only; the local fixture proves direct-treasury custody envelope, chain 4801, reviewed test token, native-gas/fee/amount limits, approvals, and public/private projections without network access, while MiniKit remains fixture-only and is not a Sepolia dependency; remote configuration and actual transaction/evidence fields remain blank and cannot be completed by the supervisor; the offline verifier checks custody envelope, Transfer log, included/safe/finalized policy, ambiguity/idempotency, privacy and transfer-graph consent, recipient gas/off-ramp usability, accessibility, pause, and rollback against deterministic fixtures, preparing G035 without satisfying it.
- Refinement: Generated TODO acceptance must satisfy these exact WORLDCOIN-G030 criteria: All identities, documents, claims, issuer keys, wallets, policies, receipts, and amounts are synthetic and visibly test-only; the local fixture proves direct-treasury custody envelope, chain 4801, reviewed test token, native-gas/fee/amount limits, approvals, and public/private projections without network access, while MiniKit remains fixture-only and is not a Sepolia dependency; remote configuration and actual transaction/evidence fields remain blank and cannot be completed by the supervisor; the offline verifier checks custody envelope, Transfer log, included/safe/finalized policy, ambiguity/idempotency, privacy and transfer-graph consent, recipient gas/off-ramp usability, accessibility, pause, and rollback against deterministic fixtures, preparing G035 without satisfying it.
- Acceptance gate:
  1. All identities, documents, claims, issuer keys, wallets, policies, receipts, and amounts are synthetic and visibly test-only.
  2. The local fixture proves the direct-treasury custody envelope, chain 4801, reviewed test token, native-gas/fee/amount limits, approvals, and public/private projections without network access; MiniKit remains fixture-only and is not a Sepolia dependency.
  3. Remote configuration and actual transaction/evidence fields remain blank and cannot be completed by the supervisor.
  4. The offline verifier checks custody envelope, Transfer log, included/safe/finalized policy, ambiguity/idempotency, privacy and transfer-graph consent, recipient gas/off-ramp usability, accessibility, pause, and rollback against deterministic fixtures, preparing G035 without satisfying it.

## WORLDCOIN-G031 Prepare enforceable release gates and a canary evidence verifier

- Status: active
- Fib priority: 1597000
- Priority: P0
- Track: world-aid-release
- Parents: WORLDCOIN-G003, WORLDCOIN-G023, WORLDCOIN-G029, WORLDCOIN-G030
- Goal: Implement fail-closed templates and offline verification for the independent human approvals, operational evidence, and reversible bounded canary required before blocked G036 can be manually opened; this goal does not grant any approval.
- Evidence: threat-model approval schema; cryptography and ZKP ceremony schema; privacy/DPIA, program, legal, treasury, accessibility, operations, and support approval schemas; artifact/commit/environment binding; canary limits; runtime-guard enablement record schema; rollback rehearsal fixture; final go/no-go verifier; missing/stale/conflicting approval tests
- Outputs: docs/runbooks/WORLD_HUMAN_AID_RELEASE.md, docs/reports/WORLD_AID_SECURITY_REVIEW.md, data/worldcoin_human_aid/release/release-gate-template.json, scripts/verify_world_aid_release_evidence.py, tests/world_aid/test_release_gates.py
- Validation: python -m pytest -q tests/world_aid/test_release_gates.py
- Bundle: worldcoin-human-aid/release
- Parallel lane: world-aid-release
- Embedding query: security privacy compliance ZKP audit treasury accessibility release gate canary rollback production
- AST query: WorldAidReleaseGate, ReleaseApproval, CanaryPolicy, evaluate_release_readiness
- Interfaces: governance records, test gate, pilot receipt, treasury operations, deployment configuration
- Submodules:
- Generated artifacts: data/worldcoin_human_aid/release/release-gate-template.json
- Predicted files: docs/runbooks/WORLD_HUMAN_AID_RELEASE.md, docs/reports/WORLD_AID_SECURITY_REVIEW.md, data/worldcoin_human_aid/release/release-gate-template.json, scripts/verify_world_aid_release_evidence.py, tests/world_aid/test_release_gates.py
- Conflict policy: software validates approval records but cannot create reviewer attestations; absent, stale, scoped-wrong, or conflicting approvals keep production disabled
- Gap task: Turn readiness into a signed, expiring, environment-specific gate with least-privilege rollout and tested rollback.
- Acceptance criteria: The verifier requires but cannot create independent human records for security, cryptography, privacy/DPIA, program, legal/compliance, treasury, accessibility, operations, and support; each record binds repository tree, artifacts, environment, policies, caps, geography, expiry, reviewer, and exceptions, and missing/stale/conflicting records keep G036 blocked; the canary template limits providers, programs, recipients, amounts, duration, custody, native gas/fees, RPCs, support, reconciliation, and kill switch; production keys/settings/deployment/transfers remain outside supervisor authority; tooling independently verifies World ID and both World-aid guards, separate approval-bound enablement, rollback to false, and never interprets fixture/template data as a signed approval.
- Refinement: Generated TODO acceptance must satisfy these exact WORLDCOIN-G031 criteria: The verifier requires but cannot create independent human records for security, cryptography, privacy/DPIA, program, legal/compliance, treasury, accessibility, operations, and support; each record binds repository tree, artifacts, environment, policies, caps, geography, expiry, reviewer, and exceptions, and missing/stale/conflicting records keep G036 blocked; the canary template limits providers, programs, recipients, amounts, duration, custody, native gas/fees, RPCs, support, reconciliation, and kill switch; production keys/settings/deployment/transfers remain outside supervisor authority; tooling independently verifies World ID and both World-aid guards, separate approval-bound enablement, rollback to false, and never interprets fixture/template data as a signed approval.
- Acceptance gate:
  1. Production requires independent approval records for security, cryptography, privacy/DPIA, program policy, legal/compliance, treasury, accessibility, operations, and support; the verifier can validate but cannot create them.
  2. Each approval binds repository tree, artifacts, environment, policy set, amount and geography limits, expiry, reviewer identity, and unresolved exceptions; missing, stale, or conflicting records keep G036 blocked.
  3. Canary policy limits providers, programs, recipients, aggregate and per-payout amount, duration, custody, native gas and fees, RPCs, support, reconciliation, and kill switch.
  4. Production keys, remote settings, contract deployment, and live WLD transfers remain outside supervisor authority and require a separate human-controlled procedure.
  5. Release tooling verifies the existing World ID guard plus both newly implemented World-aid guards; external calls and WLD transfers require separate explicit, approval-bound enablement, rollback restores both World-aid guards to false, and no template or fixture is interpreted as a signed approval.

## WORLDCOIN-G032 Evaluate an optional atomic on-chain payout contract

- Status: active
- Fib priority: 144003
- Priority: P2
- Track: world-aid-research
- Parents: WORLDCOIN-G014, WORLDCOIN-G018, WORLDCOIN-G019, WORLDCOIN-G022
- Goal: Determine whether a minimal audited contract can atomically consume an opaque payout authorization and transfer WLD with stronger replay guarantees than the controlled treasury adapter, without making it an MVP dependency.
- Evidence: threat and cost comparison; calldata and storage privacy analysis; upgradeability decision; nullifier and commitment design; verifier integration options; gas fixtures; emergency pause and recovery; formal properties; independent audit requirement; explicit adopt-or-reject decision
- Outputs: docs/research/WORLD_AID_ATOMIC_PAYOUT_CONTRACT.md, contracts/world_aid/spec/WorldAidPayout.spec.md, tests/world_aid/test_atomic_contract_decision.py
- Validation: python -m pytest -q tests/world_aid/test_atomic_contract_decision.py
- Bundle: worldcoin-human-aid/atomic-contract-research
- Parallel lane: world-aid-research
- Embedding query: optional atomic World Chain WLD payout contract eligibility commitment replay nullifier privacy audit
- AST query: WorldAidPayout, consumeAuthorization, payoutNullifier, AtomicContractDecision
- Interfaces: WLD ERC-20, optional WorldIDVerifier v4, eligibility verifier, Safe treasury
- Submodules:
- Predicted files: docs/research/WORLD_AID_ATOMIC_PAYOUT_CONTRACT.md, contracts/world_aid/spec/WorldAidPayout.spec.md, tests/world_aid/test_atomic_contract_decision.py
- Conflict policy: research and local specification only; no autonomous contract code deployment, mainnet address, upgrade key, or claim that on-chain verification is required
- Gap task: Compare off-chain verification plus controlled treasury transfer against atomic contract designs and document the smallest defensible option.
- Acceptance criteria: The analysis treats backend World v4 verification as the default and justifies any on-chain WorldIDVerifier use with a contract-enforcement requirement; any design stores only opaque one-time authorization/nullifier state and transfer facts, never documents, World session IDs, homelessness, eligibility reason, or wallet-to-person mapping; replay, front-running, recipient and amount substitution, reentrancy, token behavior, pause abuse, upgrade control, key compromise, verifier rotation, reorg, and recovery have explicit properties and tests; adoption requires a separate implementation goal, reproducible build, formal review, independent audit, testnet trial, governance approval, and human deployment, and G032 does not block the MVP treasury path.
- Refinement: Generated TODO acceptance must satisfy these exact WORLDCOIN-G032 criteria: the analysis treats backend World v4 verification as the default and justifies any on-chain WorldIDVerifier use with a contract-enforcement requirement; any design stores only opaque one-time authorization/nullifier state and transfer facts, never documents, World session IDs, homelessness, eligibility reason, or wallet-to-person mapping; replay, front-running, recipient and amount substitution, reentrancy, token behavior, pause abuse, upgrade control, key compromise, verifier rotation, reorg, and recovery have explicit properties and tests; adoption requires a separate implementation goal, reproducible build, formal review, independent audit, testnet trial, governance approval, and human deployment, and G032 does not block the MVP treasury path.
- Acceptance gate:
  1. The analysis treats backend World v4 verification as the default and justifies any on-chain WorldIDVerifier use with a contract-enforcement requirement.
  2. Any design stores only opaque one-time authorization/nullifier state and transfer facts, never documents, World session IDs, homelessness, eligibility reason, or wallet-to-person mapping.
  3. Replay, front-running, recipient and amount substitution, reentrancy, token behavior, pause abuse, upgrade control, key compromise, verifier rotation, reorg, and recovery have explicit properties and tests.
  4. Adoption requires a separate implementation goal, reproducible build, formal review, independent audit, testnet trial, governance approval, and human deployment; G032 does not block the MVP treasury path.

## WORLDCOIN-G033 Replace plaintext snapshots with encrypted transactional production state

- Status: active
- Fib priority: 5003
- Priority: P0
- Track: world-aid-storage
- Parents: WORLDCOIN-G003, WORLDCOIN-G005, WORLDCOIN-G040
- Goal: Implement DuckDB as an encrypted, transactional, single-host production repository behind one authenticated writer service with versioned migrations, so plaintext local snapshots, raw durable models, process-local indexes, SQLite, in-memory substitutes, direct worker file access, and independent multi-process writers cannot back staging identity or payout state.
- Evidence: LocalWalletRepository development-only guard; DuckDB production schema and versioned migration chain; checksum-pinned pre-staged DuckDB wheel; dedicated single-writer service and fenced migration lease; typed authenticated local client boundary with no raw SQL; KMS/HSM envelope-key interface; encrypted-volume and per-domain authenticated-encryption controls; unique replay/idempotency/event constraints; compare-and-swap transitions; atomic outbox; authenticated projections; migration inventory and separately authorized secure-retirement receipt; encrypted authenticated backup/restore; key rotation; retention/deletion; mandatory real DuckDB transaction, writer-contention, crash, checkpoint, restore, and multiprocess-client tests
- Outputs: pyproject.toml, ipfs_datasets_py/ipfs_datasets_py/wallet/secure_repository.py, wallet_interface/world_aid/storage.py, wallet_interface/world_aid/duckdb_writer.py, wallet_interface/world_aid/storage_migrations.py, wallet_interface/world_aid/migrations/0001_world_aid_core.sql, docs/specs/WORLD_AID_SECURE_STORAGE.md, ipfs_datasets_py/tests/unit/wallet/test_secure_repository.py, tests/world_aid/test_secure_storage.py, tests/world_aid/test_secure_storage_duckdb.py, tests/world_aid/test_secure_storage_multiprocess.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/wallet/test_secure_repository.py tests/world_aid/test_secure_storage.py tests/world_aid/test_secure_storage_duckdb.py tests/world_aid/test_secure_storage_multiprocess.py
- Bundle: worldcoin-human-aid/secure-storage
- Parallel lane: world-aid-storage
- Embedding query: encrypted transactional DuckDB single writer wallet storage KMS migration principal secrets World bindings unique constraints outbox backup restore
- AST query: SecureWalletRepository, WorldAidDuckDBWriter, WorldAidUnitOfWork, EnvelopeKeyProvider, WorldAidOutbox, migrate_local_wallet_snapshot, reject_local_repository
- Interfaces: ipfs_datasets_py wallet repository, wallet_interface services, authenticated local writer IPC, approved KMS/HSM secret provider, local DuckDB transaction store
- Submodules: ipfs_datasets_py
- Predicted files: pyproject.toml, ipfs_datasets_py/ipfs_datasets_py/wallet/secure_repository.py, wallet_interface/world_aid/storage.py, wallet_interface/world_aid/duckdb_writer.py, wallet_interface/world_aid/storage_migrations.py, wallet_interface/world_aid/migrations/0001_world_aid_core.sql, docs/specs/WORLD_AID_SECURE_STORAGE.md, ipfs_datasets_py/tests/unit/wallet/test_secure_repository.py, tests/world_aid/test_secure_storage.py, tests/world_aid/test_secure_storage_duckdb.py, tests/world_aid/test_secure_storage_multiprocess.py
- Conflict policy: serialize edits to the shared root dependency manifest/lock and storage configuration; consume only the human-approved offline bootstrap versions/digests, add a versioned DuckDB repository boundary and migrations without rewriting or exposing existing user snapshots, and keep development compatibility explicit; production refuses LocalWalletRepository, fallback stores, direct worker file access, network/shared-filesystem database paths, and independent multi-process writers; agents migrate only synthetic copies, and retirement of real plaintext state is a separately authorized recoverable human operation after backup/restore verification
- Gap task: Make secret-bearing wallet, identity, eligibility, decision, payout, and reconciliation state durable across workers without plaintext snapshots or non-atomic side effects.
- Acceptance criteria: Staging/production require the single-host DuckDB writer service and reject LocalWalletRepository, SQLite, in-memory stores, raw exported snapshots, network/shared-filesystem database paths, direct worker file access, and independent or multi-host writers; every secret-bearing domain uses authenticated envelope encryption with non-serialized KMS/HSM key references, the database/WAL/temp/backup paths use an approved encrypted volume and minimum filesystem roles, and DuckDB file format is never treated as the encryption boundary; versioned migrations and database constraints atomically enforce SIWE nonces, scoped World replay keys, eligibility nullifiers, payout idempotency/payload pairs, transaction attempts, and event identity across worker clients and restart; state changes and signer/reconciliation/revocation/audit work share fenced compare-and-swap DuckDB transactions plus an atomic outbox, with mandatory non-skipped tests against the checksum-pinned pre-staged wheel for transaction/rollback, second-writer rejection, crash boundaries, checkpoint, backup, restore, corruption, and plaintext-marker absence; APIs expose authenticated minimum-necessary projections rather than `to_dict()`, raw SQL, writable paths, or snapshots; agents may inventory and migrate only synthetic/development copies, while retiring any real plaintext source requires a separate human-approved recoverable operation after encrypted authenticated backup/restore verification, key-rotation/retention/deletion checks, and a signed receipt that logs no principal secrets, World identifiers, proofs, documents, or treasury material.
- Refinement: Generated TODO acceptance must satisfy these exact WORLDCOIN-G033 criteria: Staging/production require the single-host DuckDB writer service and reject LocalWalletRepository, SQLite, in-memory stores, raw exported snapshots, network/shared-filesystem database paths, direct worker file access, and independent or multi-host writers; every secret-bearing domain uses authenticated envelope encryption with non-serialized KMS/HSM key references, the database/WAL/temp/backup paths use an approved encrypted volume and minimum filesystem roles, and DuckDB file format is never treated as the encryption boundary; versioned migrations and database constraints atomically enforce SIWE nonces, scoped World replay keys, eligibility nullifiers, payout idempotency/payload pairs, transaction attempts, and event identity across worker clients and restart; state changes and signer/reconciliation/revocation/audit work share fenced compare-and-swap DuckDB transactions plus an atomic outbox, with mandatory non-skipped tests against the checksum-pinned pre-staged wheel for transaction/rollback, second-writer rejection, crash boundaries, checkpoint, backup, restore, corruption, and plaintext-marker absence; APIs expose authenticated minimum-necessary projections rather than `to_dict()`, raw SQL, writable paths, or snapshots; agents may inventory and migrate only synthetic/development copies, while retiring any real plaintext source requires a separate human-approved recoverable operation after encrypted authenticated backup/restore verification, key-rotation/retention/deletion checks, and a signed receipt that logs no principal secrets, World identifiers, proofs, documents, or treasury material.
- Acceptance gate:
  1. Staging and production require the single-host DuckDB writer service and reject LocalWalletRepository, SQLite, in-memory stores, raw exported snapshots, network/shared-filesystem database paths, direct worker file access, and independent or multi-host writers.
  2. Every secret-bearing domain uses authenticated envelope encryption with non-serialized KMS/HSM key references; database, WAL, temporary, and backup paths use an approved encrypted volume and minimum filesystem roles, while DuckDB file format is never treated as encryption.
  3. Versioned migrations and DuckDB constraints atomically enforce SIWE nonces, scoped World replay keys, eligibility nullifiers, payout idempotency/payload pairs, transaction attempts, and event identity across worker clients and restart.
  4. State changes and signer, reconciliation, revocation, and audit work share fenced compare-and-swap DuckDB transactions plus an atomic outbox, with mandatory non-skipped transaction, second-writer rejection, crash, checkpoint, backup, restore, corruption, and plaintext-marker tests against the checksum-pinned pre-staged wheel.
  5. APIs expose authenticated minimum-necessary projections rather than raw `to_dict()` models, raw SQL, writable database paths, or snapshots.
  6. Agents may inventory and migrate only synthetic/development copies. Retiring any real plaintext source is a separate human-approved recoverable operation after encrypted authenticated backup/restore verification, key-rotation/retention/deletion checks, and a signed receipt without principal secrets, World identifiers, proofs, documents, or treasury material.

## WORLDCOIN-G034 Implement issuer enrollment and credential lifecycle

- Status: active
- Fib priority: 13003
- Priority: P0
- Track: eligibility-credentials
- Parents: WORLDCOIN-G006, WORLDCOIN-G009, WORLDCOIN-G011, WORLDCOIN-G033
- Goal: Implement the missing issuer-to-wallet lifecycle for human-approved issuer enrollment, separate source-document consent, stable hidden-subject binding, scoped credential issuance/import, revocation witness refresh, correction, and reissuance.
- Evidence: issuer enrollment request and approval reference; key/schema/program scopes; source-document and claim-issuance consent separation; holder-secret ceremony; issuer/domain-blinded subject commitment; signed credential envelope; import validation; duplicate and supersession rules; revocation witness refresh; correction/reissue preserving hidden-subject relation; synthetic issuer fixtures; privacy and tenant-isolation tests
- Outputs: ipfs_datasets_py/ipfs_datasets_py/wallet/eligibility_credentials.py, wallet_interface/world_aid/issuer_credentials.py, wallet_interface/routes/world_aid_credentials.py, docs/specs/WORLD_AID_CREDENTIAL_LIFECYCLE.md, ipfs_datasets_py/tests/unit/wallet/test_eligibility_credentials.py, tests/world_aid/test_issuer_credential_api.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/wallet/test_eligibility_credentials.py tests/world_aid/test_issuer_credential_api.py
- Bundle: worldcoin-human-aid/credential-lifecycle
- Parallel lane: eligibility-credentials
- Embedding query: issuer enrollment credential issuance import document consent holder secret blinded subject commitment revocation correction reissuance
- AST query: IssuerEnrollment, CredentialIssuanceConsent, HolderSubjectBinding, EligibilityCredentialEnvelope, import_eligibility_credential, refresh_revocation_witness, correct_credential
- Interfaces: issuer registry, SIWE principal, encrypted document wallet, UCAN consent, eligibility witness builder
- Submodules: ipfs_datasets_py
- Predicted files: ipfs_datasets_py/ipfs_datasets_py/wallet/eligibility_credentials.py, wallet_interface/world_aid/issuer_credentials.py, wallet_interface/routes/world_aid_credentials.py, docs/specs/WORLD_AID_CREDENTIAL_LIFECYCLE.md, ipfs_datasets_py/tests/unit/wallet/test_eligibility_credentials.py, tests/world_aid/test_issuer_credential_api.py
- Conflict policy: self-uploaded evidence cannot self-issue a credential; issuer administration and recipient consent are separate roles, and no route exports source documents to a provider by default
- Gap task: Close the end-to-end gap between a reviewed source document and a trusted, current, privacy-scoped credential usable by the eligibility circuit.
- Acceptance criteria: Issuer enrollment is human-approved and limits organization, keys, schemas, programs, environments, validity, suspension, and revocation authority; source-document access and selected-claim issuance use separate explicit, expiring consent and never grant unrestricted OCR/document export; the holder generates a stable secret and the issuer signs an issuer/domain-blinded commitment, while imports verify registry/key/schema/subject/scope/time/signature/duplicate state before encrypted storage; witness refresh fails closed on stale/unknown roots, and correction/reissuance preserves the hidden-subject relation, links/supersedes the predecessor, and routes an unpreservable subject to duplicate-risk review; APIs are authenticated/tenant-scoped and receipts omit raw claims, documents, globally linkable subject IDs, wallet-person mappings, and private keys.
- Refinement: Generated TODO acceptance must satisfy these exact WORLDCOIN-G034 criteria: Issuer enrollment is human-approved and limits organization, keys, schemas, programs, environments, validity, suspension, and revocation authority; source-document access and selected-claim issuance use separate explicit, expiring consent and never grant unrestricted OCR/document export; the holder generates a stable secret and the issuer signs an issuer/domain-blinded commitment, while imports verify registry/key/schema/subject/scope/time/signature/duplicate state before encrypted storage; witness refresh fails closed on stale/unknown roots, and correction/reissuance preserves the hidden-subject relation, links/supersedes the predecessor, and routes an unpreservable subject to duplicate-risk review; APIs are authenticated/tenant-scoped and receipts omit raw claims, documents, globally linkable subject IDs, wallet-person mappings, and private keys.
- Acceptance gate:
  1. Issuer enrollment is human-approved and limits organization, keys, schemas, programs, environments, validity, suspension, and revocation authority.
  2. Source-document access and selected-claim issuance use separate explicit, expiring consent and never grant unrestricted OCR or document export.
  3. The holder generates a stable secret and the issuer signs an issuer/domain-blinded commitment; import verifies registry, key, schema, subject, scope, time, signature, and duplicate state before encrypted storage.
  4. Revocation-witness refresh fails closed on stale or unknown roots; correction/reissuance preserves the hidden-subject relation, links and supersedes the predecessor, and routes an unpreservable subject to duplicate-risk review.
  5. APIs are authenticated and tenant-scoped; receipts omit raw claims, documents, globally linkable subject IDs, wallet-person mappings, and private keys.

## WORLDCOIN-G035 Record the human-authorized Sepolia pilot

- Status: blocked
- Fib priority: 2584000
- Priority: P0
- Track: world-aid-human-gate
- Parents: WORLDCOIN-G030
- Goal: After named humans approve and perform the bounded Sepolia action outside the supervisor, import and verify their signed approval and redacted pilot evidence without giving an agent remote or signing authority.
- Evidence: signed Gate 2 approval; reviewed commit and artifact digests; synthetic-data attestation; exact chain/token/sender/recipient/amount/gas bounds; human-submitted transaction; canonical redacted receipt and Transfer log; reconciliation and accessibility report
- Outputs: data/worldcoin_human_aid/pilot/sepolia-pilot-evidence.json, data/worldcoin_human_aid/approvals/gate-2-sepolia.json
- Validation: python scripts/verify_world_aid_sepolia_pilot.py --evidence data/worldcoin_human_aid/pilot/sepolia-pilot-evidence.json --offline
- Bundle: worldcoin-human-aid/human-gates
- Parallel lane: world-aid-human-gate
- Embedding query: blocked human approval Sepolia pilot redacted receipt test token reconciliation
- AST query: SepoliaPilotEvidence, Gate2Approval, verify_sepolia_pilot
- Interfaces: named security and treasury approvers, external human signer, read-only local verifier
- Submodules:
- Generated artifacts: data/worldcoin_human_aid/pilot/sepolia-pilot-evidence.json, data/worldcoin_human_aid/approvals/gate-2-sepolia.json
- Predicted files: data/worldcoin_human_aid/pilot/sepolia-pilot-evidence.json, data/worldcoin_human_aid/approvals/gate-2-sepolia.json
- Conflict policy: terminal human gate; the supervisor cannot unblock, self-approve, synthesize evidence, call a remote API, fund an account, sign, or broadcast
- Gap task: Wait for explicit named human authorization and externally produced evidence; do not autonomously implement or fabricate this goal.
- Acceptance criteria: The goal remains supervisor-terminal `blocked` until named Gate 2 approvers sign a commit/artifact/environment/amount-bounded record and a named human performs the transaction; imported evidence is read-only, redacted, synthetic-only, and independently verifies chain 4801, reviewed test token, custody envelope, Transfer log, operational and safe/finalized settlement states, idempotency, privacy, accessibility, and reconciliation; no supervisor credential, RPC call, wallet prompt, signature, funding, deployment, allowance, or transfer can satisfy or unblock it.
- Refinement: Generated TODO acceptance must satisfy these exact WORLDCOIN-G035 criteria: The goal remains supervisor-terminal `blocked` until named Gate 2 approvers sign a commit/artifact/environment/amount-bounded record and a named human performs the transaction; imported evidence is read-only, redacted, synthetic-only, and independently verifies chain 4801, reviewed test token, custody envelope, Transfer log, operational and safe/finalized settlement states, idempotency, privacy, accessibility, and reconciliation; no supervisor credential, RPC call, wallet prompt, signature, funding, deployment, allowance, or transfer can satisfy or unblock it.
- Acceptance gate:
  1. The goal remains supervisor-terminal `blocked` until named Gate 2 approvers sign a commit, artifact, environment, and amount-bounded record and a named human performs the transaction.
  2. Imported evidence is read-only, redacted, synthetic-only, and independently verifies chain 4801, reviewed test token, custody envelope, Transfer log, operational and safe/finalized settlement states, idempotency, privacy, accessibility, and reconciliation.
  3. No supervisor credential, RPC call, wallet prompt, signature, funding, deployment, allowance, or transfer can satisfy or unblock this goal.

## WORLDCOIN-G036 Approve and execute a capped production canary

- Status: blocked
- Fib priority: 4181000
- Priority: P0
- Track: world-aid-human-gate
- Parents: WORLDCOIN-G031, WORLDCOIN-G035
- Goal: Keep production disabled until every named human review is current and authorized humans execute a reversible, capped canary under approved custody, monitoring, support, and reconciliation.
- Evidence: signed security, cryptography, privacy/DPIA, program, legal/compliance, treasury, accessibility, operations, and support approvals; exact repository/artifact/environment/policy digests; canary scope and expiry; human guard-enablement record; custody approvals; daily reconciliation; rollback and participant-support evidence; go/no-go decision
- Outputs: data/worldcoin_human_aid/release/production-canary-evidence.json, data/worldcoin_human_aid/approvals/gate-4-production.json
- Validation: python scripts/verify_world_aid_release_evidence.py --evidence data/worldcoin_human_aid/release/production-canary-evidence.json --offline
- Bundle: worldcoin-human-aid/human-gates
- Parallel lane: world-aid-human-gate
- Embedding query: blocked human production approval capped WLD canary privacy legal treasury accessibility reconciliation rollback
- AST query: ProductionCanaryEvidence, Gate4Approval, verify_world_aid_release_evidence
- Interfaces: named governance reviewers, treasury owners, human change operator, recipient support, read-only release verifier
- Submodules:
- Generated artifacts: data/worldcoin_human_aid/release/production-canary-evidence.json, data/worldcoin_human_aid/approvals/gate-4-production.json
- Predicted files: data/worldcoin_human_aid/release/production-canary-evidence.json, data/worldcoin_human_aid/approvals/gate-4-production.json
- Conflict policy: terminal human gate; agents cannot sign approvals, enable production guards, access custody, submit WLD, decide eligibility/appeal, or claim production readiness
- Gap task: Wait for explicit named human approvals and externally executed canary evidence; do not autonomously implement, unblock, or fabricate this goal.
- Acceptance criteria: The goal remains supervisor-terminal `blocked` until every required named approval binds the reviewed tree/artifacts/environment/policies/caps/geography/expiry and authorized humans enable guards and custody under the release runbook; the canary remains bounded, reversible, fully reconciled, supportable, and independently reviewed, with no unresolved privacy, accessibility, legal, treasury, proof, or accounting exception; agents never sign, enable, fund, deploy, transfer, adjudicate, or manufacture evidence, and rollback returns both World-aid guards to false.
- Refinement: Generated TODO acceptance must satisfy these exact WORLDCOIN-G036 criteria: The goal remains supervisor-terminal `blocked` until every required named approval binds the reviewed tree/artifacts/environment/policies/caps/geography/expiry and authorized humans enable guards and custody under the release runbook; the canary remains bounded, reversible, fully reconciled, supportable, and independently reviewed, with no unresolved privacy, accessibility, legal, treasury, proof, or accounting exception; agents never sign, enable, fund, deploy, transfer, adjudicate, or manufacture evidence, and rollback returns both World-aid guards to false.
- Acceptance gate:
  1. The goal remains supervisor-terminal `blocked` until every required named approval binds the reviewed tree, artifacts, environment, policies, caps, geography, and expiry, and authorized humans enable guards and custody under the release runbook.
  2. The canary remains bounded, reversible, fully reconciled, supportable, and independently reviewed, with no unresolved privacy, accessibility, legal, treasury, proof, or accounting exception.
  3. Agents never sign, enable, fund, deploy, transfer, adjudicate, or manufacture evidence; rollback returns both World-aid guards to false.

## WORLDCOIN-G037 Prepare a non-executing SIWE verifier and dependency lock

- Status: active
- Fib priority: 2001
- Priority: P0
- Track: world-aid-bootstrap-preparation
- Parents: WORLDCOIN-G002
- Goal: Render the isolated Node SIWE verifier, its static and runtime test contracts, package manifest, and deterministic lock proposal without installing or executing packages, so humans can review and bind all executable verifier inputs before any npm lane runs.
- Evidence: official verifier API requirement; isolated service boundary; fail-closed offline verifier; exact direct and transitive dependency graph; lockfile integrity fields; lifecycle-script inventory; engine/platform constraints; license/provenance/SBOM questions; current-cache presence inventory; explicit non-approval label; no-download receipt
- Outputs: wallet_interface/services/world_siwe_verifier/package.json, wallet_interface/services/world_siwe_verifier/package-lock.json, wallet_interface/services/world_siwe_verifier/index.mjs, scripts/verify_world_siwe_offline_bootstrap.py, data/worldcoin_human_aid/bootstrap/world-siwe-dependency-proposal.json, tests/world_aid/test_siwe_dependency_lock.py, tests/world_aid/test_siwe_offline_bootstrap.py
- Validation: test -f tests/world_aid/test_siwe_offline_bootstrap.py && python -m pytest -q tests/world_aid/test_siwe_dependency_lock.py
- Bundle: worldcoin-human-aid/siwe-dependency-lock
- Parallel lane: world-aid-bootstrap-preparation
- Embedding query: SIWE verifySiweMessage Node package lock integrity license SBOM offline cache proposal
- AST query: world_siwe_verifier package.json package-lock.json verifySiweMessage
- Interfaces: official World wallet-auth verifier contract, npm lockfile v3, Gate 0B dependency review
- Submodules:
- Generated artifacts: data/worldcoin_human_aid/bootstrap/world-siwe-dependency-proposal.json
- Predicted files: wallet_interface/services/world_siwe_verifier/package.json, wallet_interface/services/world_siwe_verifier/package-lock.json, wallet_interface/services/world_siwe_verifier/index.mjs, scripts/verify_world_siwe_offline_bootstrap.py, data/worldcoin_human_aid/bootstrap/world-siwe-dependency-proposal.json, tests/world_aid/test_siwe_dependency_lock.py, tests/world_aid/test_siwe_offline_bootstrap.py
- Conflict policy: this goal owns the isolated verifier, manifests, and tests; it may inspect but never modify the user npm cache or existing UI dependency tree, and G038/G006 consume rather than silently rewrite the reviewed verifier or lock
- Gap task: Make the complete verifier dependency proposal reviewable without allowing an agent to install, execute, approve, or substitute a package.
- Acceptance criteria: The isolated manifest contains only the minimum verifier runtime/test dependencies and the lock resolves every transitive package with version/integrity/engine data; the proposal inventories lifecycle scripts, licenses, provenance, SBOM and vulnerability-review questions, and cache presence without claiming that cache presence is trust; the offline verifier and its runtime test contract exist before selection and fail closed on missing approval or dependency drift; all files are prominently non-approved until a signed Gate 0B-selection record binds their digests; static validation performs no npm install/ci/test/audit, package execution, download, registry call, cache mutation, or lock regeneration; an agent cannot edit verifier code, add a dependency, relax integrity, or manufacture approval to make G038 pass.
- Refinement: Generated TODO acceptance must satisfy these exact WORLDCOIN-G037 criteria: The isolated manifest contains only the minimum verifier runtime/test dependencies and the lock resolves every transitive package with version/integrity/engine data; the proposal inventories lifecycle scripts, licenses, provenance, SBOM and vulnerability-review questions, and cache presence without claiming that cache presence is trust; the offline verifier and its runtime test contract exist before selection and fail closed on missing approval or dependency drift; all files are prominently non-approved until a signed Gate 0B-selection record binds their digests; static validation performs no npm install/ci/test/audit, package execution, download, registry call, cache mutation, or lock regeneration; an agent cannot edit verifier code, add a dependency, relax integrity, or manufacture approval to make G038 pass.
- Acceptance gate:
  1. The isolated manifest contains only the minimum verifier runtime and test dependencies; the lock resolves every transitive package with exact version, integrity, and engine data.
  2. The proposal inventories lifecycle scripts, licenses, provenance, transitive SBOM and vulnerability-review questions, and cache presence without treating cache presence as trust.
  3. The fail-closed offline verifier and runtime test contract exist before selection and are bound by it.
  4. Every artifact is prominently non-approved until a signed Gate 0B-selection record binds its digest.
  5. Static validation performs no npm install, CI, test, audit, package execution, download, registry call, cache mutation, or lock regeneration.
  6. An agent cannot edit the verifier, add a dependency, relax integrity, or manufacture approval to make G038 pass.

- Objective-validation evidence (WORLDCOIN-AUTO-005): official registry metadata was read on 2026-07-24 solely to generate an unapproved npm-v3 lock proposal with npm 10.9.8 and Node 22.23.1 in isolated ephemeral caches; no package tarball, `node_modules`, lifecycle script, or package code was downloaded or executed, and no package execution occurred. A rejected earlier draft ran read-only `npm cache ls`, found no MiniKit basis, and was fenced before validation, commit, or enqueue. The exact MiniKit, viem, React peer, transitive closure, hermetic Node archive, and Node/npm member digests remain human Gate 0B decisions and are prominently NOT APPROVED. The canonical verifier is `scripts/verify_world_siwe_offline_bootstrap.py`; the adapter, lock, proposal, static contract, and future runtime contract are digest-bound and protected from G038 writes. Approved verification requires an external canonical-Gate-verifier SHA-256 trust anchor and binds the caller-captured approval bytes, but that in-process pin is defense in depth rather than authentication of the already-running SIWE entrypoint. G038 remains fenced until an operator-controlled Gate-first supervisor launcher authenticates the Gate verifier, SIWE verifier, and runtime entrypoint before any repository Python runs. Static validation performs no npm or Node invocation, registry or cache access, install, package execution, download, or lock regeneration.

## WORLDCOIN-G038 Verify the human-approved SIWE dependency set offline

- Status: blocked
- Fib priority: 3001
- Priority: P0
- Track: world-aid-bootstrap
- Parents: WORLDCOIN-G037
- Goal: Verify that the human-approved SIWE lock and exact pre-staged tarballs install and run in an isolated, registry-denied lane before G006 can implement wallet authentication.
- Evidence: operator-controlled Gate-first launcher receipt; signed Gate 0B-selection dependency record; exact G037 manifest/lock/verifier/runtime digests; package tarball integrity; license/provenance/SBOM approval references; empty isolated install root; signed network-boundary evidence; `npm ci --offline --ignore-scripts`; verifier smoke test; reviewed-cache immutability and local-cache before/after digests; redacted receipt
- Outputs: docs/reports/WORLD_SIWE_OFFLINE_BOOTSTRAP.md, data/worldcoin_human_aid/bootstrap/world-siwe-offline-smoke.fixture.json
- Validation: test -f tests/world_aid/test_siwe_offline_bootstrap.py
- Bundle: worldcoin-human-aid/siwe-offline-bootstrap
- Parallel lane: world-aid-bootstrap
- Embedding query: signed dependency approval npm ci offline ignore scripts registry deny SIWE verifier smoke
- AST query: verify_world_siwe_offline_bootstrap, OfflineNpmApproval, WorldSiweSmokeReceipt
- Interfaces: operator-controlled supervisor launcher, G037 package lock and future runtime contract, human Gate 0B-selection record, read-only approved npm cache or mirror, G006
- Submodules:
- Generated artifacts: data/worldcoin_human_aid/bootstrap/world-siwe-offline-smoke.fixture.json
- Predicted files: docs/reports/WORLD_SIWE_OFFLINE_BOOTSTRAP.md, data/worldcoin_human_aid/bootstrap/world-siwe-offline-smoke.fixture.json
- Conflict policy: remain blocked until an operator-controlled Gate-first launcher exists; that launcher must authenticate the exact Gate verifier under reviewed isolated Python and then authenticate the signed SIWE verifier/runtime entrypoints before repository code runs; execution may never edit the selection-bound G037 verifier, tests, lock, reviewed cache, approval record, or egress policy
- Gap task: Implement and independently review the operator-controlled Gate-first supervisor launcher, then convert the signed dependency review and pre-staged cache into deterministic offline evidence that can safely unblock G006. Raw repository Python or pytest is not an authorization boundary.
- Pre-execution hardening: Before removing the literal runtime fence, replace path-based cache copying with one bounded descriptor-relative snapshot/copy, add adversarial archive and cache race tests, bound subprocess groups/resources/output, write the receipt atomically without following links, and cover wrong nonce/domain/address/chain/time/signature/client SIWE cases.
- Acceptance criteria: G038 remains blocked until a cryptographically bound Gate-first launcher protocol and signed receipt verifier are implemented and independently reviewed; after that launcher is approved, verification requires a current signed Gate 0B-selection record whose commit/manifest/lock/verifier/runtime/tarball digests, licenses, provenance, SBOM, exceptions, reviewers, and expiry match exactly; an empty isolated root completes `npm ci --offline --ignore-scripts` and positive and negative SIWE smoke tests behind the signed default-deny namespace/AppArmor boundary; the reviewed cache remains immutable while before/after digests record any mutation to the owned local cache copy; the receipt truthfully records that network-attempt count is unobserved while proving no successful external egress and no signed-boundary drift; missing inputs, unexpected lifecycle scripts, integrity mismatch, stale/conflicting approval, reviewed-cache mutation, successful external egress, boundary drift, or dependency drift fails closed; the fixture is synthetic and cannot be interpreted as human approval; G006 remains dependency-blocked until this goal has a successful canonical merge receipt.
- Refinement: Generated TODO acceptance must satisfy these exact WORLDCOIN-G038 criteria: G038 remains blocked until a cryptographically bound Gate-first launcher protocol and signed receipt verifier are implemented and independently reviewed; after that launcher is approved, verification requires a current signed Gate 0B-selection record whose commit/manifest/lock/verifier/runtime/tarball digests, licenses, provenance, SBOM, exceptions, reviewers, and expiry match exactly; an empty isolated root completes `npm ci --offline --ignore-scripts` and positive and negative SIWE smoke tests behind the signed default-deny namespace/AppArmor boundary; the reviewed cache remains immutable while before/after digests record any mutation to the owned local cache copy; the receipt truthfully records that network-attempt count is unobserved while proving no successful external egress and no signed-boundary drift; missing inputs, unexpected lifecycle scripts, integrity mismatch, stale/conflicting approval, reviewed-cache mutation, successful external egress, boundary drift, or dependency drift fails closed; the fixture is synthetic and cannot be interpreted as human approval; G006 remains dependency-blocked until this goal has a successful canonical merge receipt.
- Acceptance gate:
  1. G038 remains blocked until an independently reviewed, operator-controlled Gate-first supervisor launcher authenticates the exact Gate verifier under isolated Python and authenticates the signed SIWE verifier/runtime entrypoints before repository code runs.
  2. A current signed Gate 0B-selection record exactly binds the commit, manifest, lock, verifier, runtime, tarball digests, licenses, provenance, SBOM, exceptions, reviewers, and expiry.
  3. An empty isolated root completes `npm ci --offline --ignore-scripts` plus positive and negative SIWE smoke tests while the signed default-deny network boundary remains unchanged and no external egress succeeds; the receipt states that attempt count is unobserved.
  4. The reviewed lock and reviewed cache remain unchanged; mutation of the owned local cache copy is allowed only when its before/after digests are recorded.
  5. Cache snapshot/copy and archive extraction are descriptor-anchored, symlink-free, race-tested, and bounded; child processes have group, time, resource, and output bounds; the receipt is written atomically without following links.
  6. Missing inputs, unexpected lifecycle scripts, integrity mismatch, stale/conflicting approval, reviewed-cache mutation, successful external egress, boundary drift, or dependency drift fails closed.
  7. The fixture is synthetic and is not approval; G006 remains dependency-blocked until G038 has a successful canonical merge receipt.

## WORLDCOIN-G039 Verify a human-approved native ZKP toolchain offline

- Status: blocked
- Fib priority: 3002
- Priority: P0
- Track: world-aid-bootstrap
- Parents: WORLDCOIN-G041
- Goal: Verify the exact human-selected native ZKP backend/toolchain with a bounded smoke circuit and reproducible hashes before G012 can build the eligibility circuit.
- Evidence: signed Gate 0B-selection ZKP record; native architecture match; binary/container digest; compiler/backend/version; licenses and provenance; offline smoke circuit source and lock; deterministic build flags; artifact hashes; proof/verify result; registry and network deny canary; resource bounds; Groth16 ceremony-not-yet-approved marker
- Outputs: docs/reports/WORLD_AID_ZKP_OFFLINE_BOOTSTRAP.md, data/worldcoin_human_aid/bootstrap/zkp-toolchain-smoke.fixture.json
- Validation: python scripts/verify_world_aid_zkp_toolchain.py --approval data/worldcoin_human_aid/approvals/gate-0b-selection/approval.json --offline && python -m pytest -q tests/world_aid/test_zkp_toolchain_bootstrap.py
- Bundle: worldcoin-human-aid/zkp-toolchain-bootstrap
- Parallel lane: world-aid-bootstrap
- Embedding query: ZKP Nargo ProveKit Groth16 native toolchain checksum offline smoke circuit reproducible
- AST query: verify_world_aid_zkp_toolchain, ZkpToolchainApproval, ZkpSmokeReceipt
- Interfaces: G041 verifier/proposal, human Gate 0B-selection record, pre-staged native binary/container, G012 circuit build
- Submodules:
- Generated artifacts: data/worldcoin_human_aid/bootstrap/zkp-toolchain-smoke.fixture.json
- Predicted files: docs/reports/WORLD_AID_ZKP_OFFLINE_BOOTSTRAP.md, data/worldcoin_human_aid/bootstrap/zkp-toolchain-smoke.fixture.json
- Conflict policy: remain terminally blocked until an operator-controlled Gate-first supervisor launcher authenticates the exact selection-bound entrypoint and verifier before repository Python runs; signed approval and repository-controlled environment flags are necessary but never sufficient launcher authority; after that external launcher exists, execute but never edit the selection-bound G041 verifier, smoke circuit, lock, and tests, using only the human-selected pre-staged native binary/container; enforce descriptor-backed immutable inputs, process-group time/resource/output bounds, network and registry denial, and atomic no-follow receipts; never download, cross-run the bundled ARM64 binary on x86_64, substitute a backend, generate production setup parameters, edit the verifier to fit an artifact, or edit the approval record
- Gap task: Establish reproducible, architecture-correct offline toolchain evidence before any eligibility-circuit lane executes.
- Acceptance criteria: Verification requires a current signed Gate 0B-selection record binding native architecture, backend/toolchain/version, binary or image digest, licenses, provenance, flags, resource bounds, reviewer, exceptions, and expiry; the checksum-pinned pre-staged toolchain compiles the locked smoke circuit twice with identical artifact hashes and completes bounded proof/verification while registries and network are denied; missing/wrong-architecture/tampered tools, unpinned inputs, network attempts, nondeterminism, resource-limit breach, or absent/stale/conflicting approval fails closed; no smoke artifact or developer-generated Groth16 parameter is production trust; G012 remains dependency-blocked until this goal has a successful canonical merge receipt.
- Refinement: Generated TODO acceptance must satisfy these exact WORLDCOIN-G039 criteria: Verification requires a current signed Gate 0B-selection record binding native architecture, backend/toolchain/version, binary or image digest, licenses, provenance, flags, resource bounds, reviewer, exceptions, and expiry; the checksum-pinned pre-staged toolchain compiles the locked smoke circuit twice with identical artifact hashes and completes bounded proof/verification while registries and network are denied; missing/wrong-architecture/tampered tools, unpinned inputs, network attempts, nondeterminism, resource-limit breach, or absent/stale/conflicting approval fails closed; no smoke artifact or developer-generated Groth16 parameter is production trust; G012 remains dependency-blocked until this goal has a successful canonical merge receipt.
- Acceptance gate:
  1. G039 remains blocked behind a literal-false runtime fence until an operator-controlled Gate-first supervisor launcher authenticates the exact entrypoint and verifier before repository Python runs; approval records and environment flags alone cannot open the fence.
  2. A current signed Gate 0B-selection record binds native architecture, backend/toolchain/version, binary or image digest, licenses, provenance, flags, resource bounds, reviewer, exceptions, and expiry.
  3. The checksum-pinned pre-staged toolchain compiles the locked smoke circuit twice with identical artifact hashes and completes bounded proof and verification with registries and network denied.
  4. Missing, wrong-architecture, tampered, or unpinned tools, network attempts, nondeterminism, resource-limit breach, or absent/stale/conflicting approval fails closed.
  5. The launcher uses descriptor-backed immutable inputs, bounded process groups and output, enforced network/registry denial, and an atomic no-follow receipt.
  6. Smoke artifacts and developer-generated Groth16 parameters are never production trust.
  7. G012 remains dependency-blocked until G039 has a successful canonical merge receipt.

## WORLDCOIN-G040 Verify the human-approved DuckDB runtime and wheelhouse offline

- Status: blocked
- Fib priority: 3003
- Priority: P0
- Track: world-aid-bootstrap
- Parents: WORLDCOIN-G042
- Goal: Verify the exact human-approved Python dependency lock, DuckDB wheel, and single-writer runtime policy without registry access before G033 implements production envelope encryption and persistence.
- Evidence: signed Gate 0B-selection DuckDB record; exact Python wheel names/hashes, CPython ABI, platform tag, and DuckDB version; license/provenance/SBOM and vulnerability disposition; extension autoinstall/autoload and external access disabled; local-filesystem single-writer policy; reviewed encrypted-volume, envelope-encryption, and backup design; empty isolated environment; transaction/rollback/unique-constraint/compare-and-swap/outbox smoke with opaque synthetic payloads; direct second-writer rejection; checkpoint/crash/reopen/backup/restore/corruption smoke; dependency-lock and wheelhouse non-mutation; redacted receipt
- Outputs: docs/reports/WORLD_AID_DUCKDB_OFFLINE_BOOTSTRAP.md, data/worldcoin_human_aid/bootstrap/duckdb-offline-smoke.fixture.json
- Validation: python scripts/verify_world_aid_duckdb_bootstrap.py --approval data/worldcoin_human_aid/approvals/gate-0b-selection/approval.json --offline && python -m pytest -q tests/world_aid/test_duckdb_bootstrap.py
- Bundle: worldcoin-human-aid/duckdb-bootstrap
- Parallel lane: world-aid-bootstrap
- Embedding query: DuckDB Python wheelhouse single writer offline no index external access disabled transaction rollback checkpoint backup restore smoke
- AST query: verify_world_aid_duckdb_bootstrap, DuckDBBootstrapApproval, DuckDBRuntimePolicy, DuckDBSmokeReceipt
- Interfaces: G042 verifier/runtime-policy proposal, human Gate 0B-selection record, approved read-only Python wheelhouse, single-writer runtime policy, local encrypted storage paths, G033
- Submodules:
- Generated artifacts: data/worldcoin_human_aid/bootstrap/duckdb-offline-smoke.fixture.json
- Predicted files: docs/reports/WORLD_AID_DUCKDB_OFFLINE_BOOTSTRAP.md, data/worldcoin_human_aid/bootstrap/duckdb-offline-smoke.fixture.json
- Conflict policy: remain terminally blocked until an operator-controlled Gate-first supervisor launcher authenticates the exact selection-bound entrypoint and verifier before repository Python runs; signed approval and repository-controlled environment flags are necessary but never sufficient launcher authority; after that external launcher exists, execute but never edit the selection-bound G042 verifier, runtime/backup policy, lock, and tests, using only human-approved pre-staged artifacts; enforce a descriptor-backed read-only wheelhouse, empty isolated interpreter, process-group time/resource/output bounds, network and registry denial, local-only storage, and atomic no-follow receipts; never contact a package or extension registry, install/load an unapproved extension, enable external filesystem/HTTP access, use a network/shared-filesystem database path, allow an independent writer, use persistent real data, weaken digest/hash checks, mutate the reviewed wheelhouse/cache/lock, edit the verifier to fit an artifact, or edit the approval record
- Gap task: Make the DuckDB wheel/runtime supply chain and real single-writer database smoke evidence explicit before secure-storage implementation begins.
- Acceptance criteria: Verification requires a current signed Gate 0B-selection record binding the root and submodule commits, lock/wheel hashes, CPython ABI, platform, exact DuckDB version, licenses, provenance, SBOM, vulnerability disposition, runtime and storage policies, reviewer, exceptions, and expiry; installation uses only the approved read-only wheelhouse with hashes in an empty isolated environment while indexes, extension registries, DNS, and HTTP are denied, then a local-filesystem database passes transaction, rollback, uniqueness, compare-and-swap, atomic-outbox, direct second-writer rejection, checkpoint, crash/reopen, backup/restore, corruption, opaque-synthetic-payload, and teardown checks with extension autoinstall/autoload and external access disabled; missing or mismatched wheels, dependency-lock drift, unexpected extension, non-local path, independent writer success, network attempt, stale/conflicting approval, skipped real-database execution, wheelhouse mutation, or incomplete cleanup fails closed and leaves no database/WAL/temp data; this goal does not claim DuckDB file encryption or implement the application envelope layer, which remains G033-owned; the synthetic fixture is not approval, and G033 remains dependency-blocked until this goal has a successful canonical merge receipt.
- Refinement: Generated TODO acceptance must satisfy these exact WORLDCOIN-G040 criteria: Verification requires a current signed Gate 0B-selection record binding the root and submodule commits, lock/wheel hashes, CPython ABI, platform, exact DuckDB version, licenses, provenance, SBOM, vulnerability disposition, runtime and storage policies, reviewer, exceptions, and expiry; installation uses only the approved read-only wheelhouse with hashes in an empty isolated environment while indexes, extension registries, DNS, and HTTP are denied, then a local-filesystem database passes transaction, rollback, uniqueness, compare-and-swap, atomic-outbox, direct second-writer rejection, checkpoint, crash/reopen, backup/restore, corruption, opaque-synthetic-payload, and teardown checks with extension autoinstall/autoload and external access disabled; missing or mismatched wheels, dependency-lock drift, unexpected extension, non-local path, independent writer success, network attempt, stale/conflicting approval, skipped real-database execution, wheelhouse mutation, or incomplete cleanup fails closed and leaves no database/WAL/temp data; this goal does not claim DuckDB file encryption or implement the application envelope layer, which remains G033-owned; the synthetic fixture is not approval, and G033 remains dependency-blocked until this goal has a successful canonical merge receipt.
- Acceptance gate:
  1. G040 remains blocked behind a literal-false runtime fence until an operator-controlled Gate-first supervisor launcher authenticates the exact entrypoint and verifier before repository Python runs; approval records and environment flags alone cannot open the fence.
  2. A current signed Gate 0B-selection record binds root and submodule commits, lock and wheel hashes, CPython ABI, platform, exact DuckDB version, licenses, provenance, SBOM, vulnerability disposition, runtime/storage policies, reviewer, exceptions, and expiry.
  3. An empty isolated environment installs only from the approved descriptor-backed read-only wheelhouse with hashes while indexes, extension registries, DNS, and HTTP are denied; extension autoinstall/autoload and external access remain disabled.
  4. The launcher applies process-group time/resource/output bounds, local-only storage enforcement, and an atomic no-follow receipt.
  5. A local-filesystem database passes transaction, rollback, uniqueness, compare-and-swap, atomic-outbox, direct second-writer rejection, checkpoint, crash/reopen, backup/restore, corruption, opaque-synthetic-payload, and teardown checks.
  6. Missing/mismatched wheels, dependency-lock drift, unexpected extensions, non-local paths, independent-writer success, network attempts, stale/conflicting approval, skipped real execution, wheelhouse mutation, or incomplete cleanup fails closed and leaves no database, WAL, or temporary data.
  7. G040 does not claim DuckDB file encryption or implement the application envelope layer; G033 owns those controls.
  8. The synthetic fixture is not approval; G033 remains dependency-blocked until G040 has a successful canonical merge receipt.

## WORLDCOIN-G041 Prepare a non-executing ZKP bootstrap verifier proposal

- Status: active
- Fib priority: 2002
- Priority: P0
- Track: world-aid-bootstrap-preparation
- Parents: WORLDCOIN-G002
- Goal: Prepare the backend-neutral ZKP bootstrap verifier, bounded smoke-circuit specification, and human review proposal without downloading, installing, importing, or executing a ZKP toolchain, so Gate 0B-selection can bind an exact native backend before G039 runs it.
- Evidence: architecture and command inventory from G002; explicit native-architecture requirement; backend/version/binary-or-image digest fields; license/provenance/SBOM/vulnerability questions; deterministic flags and resource bounds; locked-input and repeat-build requirements; network/registry deny contract; Groth16 ceremony-not-yet-approved marker; no-execution receipt
- Outputs: scripts/verify_world_aid_zkp_toolchain.py, tests/world_aid/fixtures/zkp_toolchain_smoke/SMOKE_SPEC.md, tests/world_aid/fixtures/zkp_toolchain_smoke/Nargo.toml, tests/world_aid/fixtures/zkp_toolchain_smoke/Nargo.lock, tests/world_aid/fixtures/zkp_toolchain_smoke/src/main.nr, data/worldcoin_human_aid/bootstrap/zkp-toolchain-dependency-proposal.json, tests/world_aid/test_zkp_toolchain_bootstrap_static.py, tests/world_aid/test_zkp_toolchain_bootstrap.py
- Validation: test -f tests/world_aid/test_zkp_toolchain_bootstrap.py && PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q -s -p no:cacheprovider -c /dev/null --confcutdir=tests/world_aid tests/world_aid/test_zkp_toolchain_bootstrap_static.py
- Bundle: worldcoin-human-aid/zkp-toolchain-preparation
- Parallel lane: world-aid-bootstrap-preparation
- Embedding query: non-executing ZKP bootstrap verifier proposal native architecture checksum license provenance SBOM smoke circuit
- AST query: verify_world_aid_zkp_toolchain, ZkpToolchainSelectionProposal, ZkpSmokeSpecification
- Interfaces: G002 qualified inventory, Gate 0B-selection schema, G039 execution lane
- Submodules:
- Generated artifacts: data/worldcoin_human_aid/bootstrap/zkp-toolchain-dependency-proposal.json
- Predicted files: scripts/verify_world_aid_zkp_toolchain.py, tests/world_aid/fixtures/zkp_toolchain_smoke/SMOKE_SPEC.md, tests/world_aid/fixtures/zkp_toolchain_smoke/Nargo.toml, tests/world_aid/fixtures/zkp_toolchain_smoke/Nargo.lock, tests/world_aid/fixtures/zkp_toolchain_smoke/src/main.nr, data/worldcoin_human_aid/bootstrap/zkp-toolchain-dependency-proposal.json, tests/world_aid/test_zkp_toolchain_bootstrap_static.py, tests/world_aid/test_zkp_toolchain_bootstrap.py
- Conflict policy: this goal owns only a non-executing verifier/proposal/locked-smoke-input boundary; it may inspect text and install metadata but must not import or run Nargo, Noir, ProveKit, `bb`, Cargo, Rust, a proof backend, a container, or a circuit; it must not download, contact a registry, mutate a cache, choose a trusted backend, generate setup parameters, or manufacture approval
- Gap task: Give reviewers a stable fail-closed verifier and complete decision packet before any native ZKP artifact is trusted or executed.
- Acceptance criteria: The proposal leaves backend selection human-owned and enumerates exact architecture, version, binary/image digest, licenses, provenance, SBOM, vulnerability disposition, deterministic flags, resource bounds, offline location, locked smoke inputs, expected repeat-build/proof/verify evidence, and expiry; the verifier, locked bounded smoke circuit, and runtime test contract exist before selection and fail closed on missing or conflicting approval, wrong architecture, digest drift, unpinned inputs, unexpected network/registry configuration, mutable paths, and production-trust claims; static validation reads repository files only and performs no tool import/execution, package or container action, subprocess smoke, download, secret lookup, cache mutation, circuit build, proof, verification, or parameter generation; every artifact is prominently non-approved until signed Gate 0B-selection binds it, and G039 alone owns approved runtime execution.
- Refinement: Generated TODO acceptance must satisfy these exact WORLDCOIN-G041 criteria: The proposal leaves backend selection human-owned and enumerates exact architecture, version, binary/image digest, licenses, provenance, SBOM, vulnerability disposition, deterministic flags, resource bounds, offline location, locked smoke inputs, expected repeat-build/proof/verify evidence, and expiry; the verifier, locked bounded smoke circuit, and runtime test contract exist before selection and fail closed on missing or conflicting approval, wrong architecture, digest drift, unpinned inputs, unexpected network/registry configuration, mutable paths, and production-trust claims; static validation reads repository files only and performs no tool import/execution, package or container action, subprocess smoke, download, secret lookup, cache mutation, circuit build, proof, verification, or parameter generation; every artifact is prominently non-approved until signed Gate 0B-selection binds it, and G039 alone owns approved runtime execution.
- Acceptance gate:
  1. Backend selection remains human-owned; the proposal enumerates exact architecture, version, binary/image digest, licenses, provenance, SBOM, vulnerability disposition, flags, bounds, location, locked inputs, expected evidence, and expiry.
  2. The verifier, locked bounded smoke circuit, and runtime test contract exist before selection and fail closed on absent/conflicting approval, wrong architecture, digest drift, unpinned inputs, unexpected network/registry configuration, mutable paths, or production-trust claims.
  3. Static validation performs no tool import/execution, package/container action, subprocess smoke, download, secret lookup, cache mutation, circuit build, proof, verification, or parameter generation.
  4. Artifacts remain explicitly non-approved until Gate 0B-selection binds them; G039 alone owns approved runtime execution.
- Objective-validation evidence (WORLDCOIN-AUTO-006):
  - Discovery repair: `data/worldcoin_human_aid/agent_supervisor/discovery/2026-07-24-worldcoin-auto-006-zkp-bootstrap.md`
  - The discovery record and canonical command document the repository-only, non-executing validation boundary; the proposal, locked smoke inputs, verifier, static contract, and future G039 runtime contract are all explicitly unapproved until signed Gate 0B-selection.

## WORLDCOIN-G042 Prepare a non-executing DuckDB bootstrap verifier proposal

- Status: active
- Fib priority: 2003
- Priority: P0
- Track: world-aid-bootstrap-preparation
- Parents: WORLDCOIN-G002
- Goal: Prepare the DuckDB runtime-policy contract, offline verifier, and human dependency proposal without installing or importing DuckDB, so reviewers can approve an exact wheel and single-writer topology before G040 executes the runtime smoke.
- Evidence: root DuckDB declaration and qualified installed-metadata inventory; exact CPython ABI/platform/wheel hash fields; license/provenance/SBOM/vulnerability questions; extension autoinstall/autoload/community and external-access deny policy; single-host/single-writer service topology; local encrypted-volume and envelope-encryption design; transaction/recovery/backup/opaque-payload smoke specification; explicit handoff of application plaintext-marker tests to G033; no-execution receipt
- Outputs: docs/adr/WORLD_AID_DUCKDB_STORAGE_ADR.md, requirements-world-aid.lock, wallet_interface/deploy/world-aid-duckdb-runtime.yml, docs/specs/WORLD_AID_DUCKDB_BACKUP.md, scripts/verify_world_aid_duckdb_bootstrap.py, data/worldcoin_human_aid/bootstrap/duckdb-dependency-proposal.json, tests/world_aid/test_duckdb_bootstrap_static.py, tests/world_aid/test_duckdb_bootstrap.py
- Validation: test -f tests/world_aid/test_duckdb_bootstrap.py && PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q -s -p no:cacheprovider -c /dev/null --confcutdir=tests/world_aid tests/world_aid/test_duckdb_bootstrap_static.py
- Bundle: worldcoin-human-aid/duckdb-preparation
- Parallel lane: world-aid-bootstrap-preparation
- Embedding query: non-executing DuckDB wheel verifier single writer runtime policy offline wheelhouse encryption backup restore
- AST query: verify_world_aid_duckdb_bootstrap, DuckDBSelectionProposal, DuckDBRuntimePolicy
- Interfaces: G002 qualified inventory, World human-aid DuckDB ADR, Gate 0B-selection schema, G040 execution lane
- Submodules:
- Generated artifacts: data/worldcoin_human_aid/bootstrap/duckdb-dependency-proposal.json
- Predicted files: docs/adr/WORLD_AID_DUCKDB_STORAGE_ADR.md, requirements-world-aid.lock, wallet_interface/deploy/world-aid-duckdb-runtime.yml, docs/specs/WORLD_AID_DUCKDB_BACKUP.md, scripts/verify_world_aid_duckdb_bootstrap.py, data/worldcoin_human_aid/bootstrap/duckdb-dependency-proposal.json, tests/world_aid/test_duckdb_bootstrap_static.py, tests/world_aid/test_duckdb_bootstrap.py
- Conflict policy: this goal owns only non-executing ADR/lock/policy/verifier/proposal/test files; it may inspect text and distribution metadata but must not import DuckDB, create/open a database, install a wheel, execute pip, contact an index/extension registry, enable external access, inspect or mutate a package cache, select a trusted wheel, or manufacture approval
- Gap task: Give reviewers a stable fail-closed DuckDB verifier and complete single-writer supply-chain packet before any database runtime smoke or secure repository implementation.
- Acceptance criteria: The proposal records declarations and observed metadata only as unapproved inventory and leaves the exact DuckDB version/wheel human-owned; it enumerates wheel filename/hash, CPython ABI/platform, license, provenance, SBOM, vulnerability disposition, read-only wheelhouse, the reviewed ADR, requirements lock, runtime/storage/encryption/backup policies, extension and external-access deny settings, single-host exactly-one-writer topology, local IPC boundary, tests, exceptions, and expiry; the verifier and runtime test contract exist before selection and fail closed on missing/conflicting approval, hash or ABI drift, mutable wheelhouse/lock, extension/network enablement, non-local/shared paths, direct or multiple writers, skipped real execution, or a claim that DuckDB supplies application encryption; static validation reads repository files only and performs no DuckDB import, database creation, wheel install, pip execution, index/extension request, cache access/mutation, secret lookup, or runtime smoke; every artifact is prominently non-approved until signed Gate 0B-selection binds it, G040 alone owns approved runtime execution, and G033 owns envelope-encryption/plaintext-marker implementation.
- Refinement: Generated TODO acceptance must satisfy these exact WORLDCOIN-G042 criteria: The proposal records declarations and observed metadata only as unapproved inventory and leaves the exact DuckDB version/wheel human-owned; it enumerates wheel filename/hash, CPython ABI/platform, license, provenance, SBOM, vulnerability disposition, read-only wheelhouse, the reviewed ADR, requirements lock, runtime/storage/encryption/backup policies, extension and external-access deny settings, single-host exactly-one-writer topology, local IPC boundary, tests, exceptions, and expiry; the verifier and runtime test contract exist before selection and fail closed on missing/conflicting approval, hash or ABI drift, mutable wheelhouse/lock, extension/network enablement, non-local/shared paths, direct or multiple writers, skipped real execution, or a claim that DuckDB supplies application encryption; static validation reads repository files only and performs no DuckDB import, database creation, wheel install, pip execution, index/extension request, cache access/mutation, secret lookup, or runtime smoke; every artifact is prominently non-approved until signed Gate 0B-selection binds it, G040 alone owns approved runtime execution, and G033 owns envelope-encryption/plaintext-marker implementation.
- Acceptance gate:
  1. Exact DuckDB wheel selection remains human-owned; inventory is explicitly unapproved and the proposal covers wheel/ABI/hash, license, provenance, SBOM, vulnerabilities, wheelhouse, policies, topology, tests, exceptions, and expiry.
  2. The reviewed ADR, requirements lock, runtime and backup policies, verifier, and runtime test contract exist before selection; the verifier fails closed on absent/conflicting approval, hash/ABI drift, mutable inputs, extension/network enablement, non-local/shared paths, direct or multiple writers, skipped execution, or a claim that DuckDB supplies application encryption.
  3. Static validation performs no DuckDB import, database creation, wheel install, pip/index/extension action, cache access/mutation, secret lookup, or runtime smoke.
  4. Artifacts remain explicitly non-approved until Gate 0B-selection binds them; G040 owns approved runtime execution and G033 owns envelope-encryption/plaintext-marker implementation.
- Objective-validation evidence (WORLDCOIN-AUTO-007):
  - Discovery repair: `data/worldcoin_human_aid/agent_supervisor/discovery/2026-07-24-worldcoin-auto-007-duckdb-bootstrap.md`
  - Human-selection-only proposal: `data/worldcoin_human_aid/bootstrap/duckdb-dependency-proposal.json`
  - Repository-only verifier: `scripts/verify_world_aid_duckdb_bootstrap.py`
  - Reviewed storage inputs: `docs/adr/WORLD_AID_DUCKDB_STORAGE_ADR.md`, `requirements-world-aid.lock`, `wallet_interface/deploy/world-aid-duckdb-runtime.yml`, `docs/specs/WORLD_AID_DUCKDB_BACKUP.md`
  - Static/runtime contracts: `tests/world_aid/test_duckdb_bootstrap_static.py`, `tests/world_aid/test_duckdb_bootstrap.py`
  - G002 inventory source: `data/worldcoin_human_aid/audit/offline-bootstrap-proposal.json::inventory.python_duckdb`
  - Preparation validation is deliberately unapproved; G040 must supply the signed-selection-bound, non-skipped real runtime receipt.
