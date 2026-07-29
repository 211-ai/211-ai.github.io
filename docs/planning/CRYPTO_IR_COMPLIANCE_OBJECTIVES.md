# Crypto IR, Smart-Contract Assurance, and Transaction Compliance Objective Heap

This reviewed objective heap is the durable, machine-projectable source of
intent for the architecture in
[`CRYPTO_IR_COMPLIANCE_PLAN.md`](CRYPTO_IR_COMPLIANCE_PLAN.md). The executable
projection is
[`CRYPTO_IR_COMPLIANCE_TODO.md`](CRYPTO_IR_COMPLIANCE_TODO.md).

Program invariants:

- Integration target is `codex/crypto-ir-contract-compliance`, pinned to the
  reviewed wallet and software-contract baseline recorded in the plan.
- `processors.wallets` and `processors.smart_contracts` remain read-only:
  they never retain secrets, sign, approve, submit, or broadcast.
- Crypto IR reuses `ir_core`, `security_ir`, `software_contracts`, and the
  admissibility receipt/capability runtime; it does not invent parallel
  authority, proof-result, or generic AST hierarchies.
- Every identity binds chain/network, schema, canonicalization, provenance,
  finality, completeness, policy, toolchain, and time where those facts are
  semantic. Binary floating-point values are forbidden for money.
- A backend earns proof authority only by executing a sound, supported
  lowering. Opaque JSON, GraphRAG, static findings, tests, simulation,
  monitors, and heuristic scores are not theorem proofs.
- Exact applicable sanctions identifiers and established blocked parties are
  distinct from indirect exposure and heuristic association. Missing, stale,
  inconsistent, reorged, or incomplete critical evidence fails closed.
- Automated signing or broadcast requires a current `ALLOW` and atomic
  consumption of an exact-candidate, one-use admissibility capability.
- Network access is bounded and injected; credentials, auto-install,
  publication, reporting, and production fund movement are outside default
  task authority.
- Broad shared directories are not output claims. Package export files have
  one owner, and downstream goals use direct imports until the serialized
  cutover.

## CRYPTOIR-G000 Deliver Crypto IR contract assurance and transaction compliance

- Status: blocked
- Review only: true
- Parent:
- Fib priority: 1
- Priority: P0
- Track: crypto-ir-program
- Bundle: crypto-ir/control
- Parallel lane: control
- Conflict policy: serialize aggregate review only and delegate every implementation edit to child goals
- Submodules: ipfs_datasets_py
- Resource class: cpu-large
- Token class: small
- Goal: Deliver a chain-neutral Crypto IR, bounded smart-contract acquisition and assurance, sanctions and monetary-flow compliance reasoning, and a fail-closed pre-sign/pre-broadcast transaction gate.
- Evidence: CRYPTOIR-G010, CRYPTOIR-G020, CRYPTOIR-G030, CRYPTOIR-G100, CRYPTOIR-G110, CRYPTOIR-G120, CRYPTOIR-G130, CRYPTOIR-G140, CRYPTOIR-G200, CRYPTOIR-G210, CRYPTOIR-G220, CRYPTOIR-G230, CRYPTOIR-G240, CRYPTOIR-G250, CRYPTOIR-G260, CRYPTOIR-G300, CRYPTOIR-G310, CRYPTOIR-G320, CRYPTOIR-G330, CRYPTOIR-G400, CRYPTOIR-G410, CRYPTOIR-G420, CRYPTOIR-G430, CRYPTOIR-G440, CRYPTOIR-G500, CRYPTOIR-G510, CRYPTOIR-G520, CRYPTOIR-G530, CRYPTOIR-G540, CRYPTOIR-G550, CRYPTOIR-G560, CRYPTOIR-G570, CRYPTOIR-G600, CRYPTOIR-G610
- Outputs:
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/logic/crypto_ir ipfs_datasets_py/tests/unit/processors/smart_contracts ipfs_datasets_py/tests/unit/processors/wallets/guard ipfs_datasets_py/tests/contract/logic/crypto_ir ipfs_datasets_py/tests/contract/processors/smart_contracts ipfs_datasets_py/tests/contract/processors/wallets
- Acceptance: Every child has current-tree evidence; all supported chains have explicit semantic coverage; no hard-deny or stale-critical-evidence fixture obtains `ALLOW`; proof and sanctions authority never exceed their evidence; exact-candidate permission is revalidated and consumed atomically; processors remain non-custodial; release, rollback, privacy, security, compliance, and operational evidence is current.
- Gap task: Review child-goal evidence and completion quorum only; do not create an aggregate implementation change or edit the planning control plane.
- Refinement: Preserve the authority boundaries and complete dependency-ready children before integration or release.
- Embedding query: crypto intermediate representation smart contract security theorem prover sanctions flow graph transaction gate
- AST query: CryptoIR TransactionPolicyDecision EnforcementReceipt ContractArtifact ExposurePath

## CRYPTOIR-G010 Define trust, authority, threat, and fail-closed policy

- Status: active
- Review only: false
- Parent: CRYPTOIR-G000
- Fib priority: 2
- Priority: P0
- Track: trust
- Bundle: crypto-ir/trust
- Parallel lane: trust-policy
- Conflict policy: sole owner of Crypto IR threat, authority, and baseline policy documents
- Submodules: ipfs_datasets_py
- Resource class: cpu-small
- Token class: small
- Goal: Freeze the pinned repository baseline and define the trusted computing base, adversaries, legal-policy boundary, result authority lattice, unsupported behavior, freshness, and fail-closed rules before schemas or gates are implemented.
- Evidence: ipfs_datasets_py/docs/crypto_ir/THREAT_MODEL.md, ipfs_datasets_py/docs/crypto_ir/AUTHORITY_AND_POLICY.md
- Outputs: ipfs_datasets_py/docs/crypto_ir/THREAT_MODEL.md, ipfs_datasets_py/docs/crypto_ir/AUTHORITY_AND_POLICY.md, ipfs_datasets_py/tests/unit/logic/crypto_ir/test_policy_baseline.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/logic/crypto_ir/test_policy_baseline.py
- Acceptance: Documents bind the reviewed git revisions; distinguish observation, evidence, proof, monitor, heuristic, designation, policy, and authorization authority; define exact `PROVED`, `DISPROVED`, `UNKNOWN`, `UNSUPPORTED`, `INCONCLUSIVE`, `STALE`, `ERROR`, `ALLOW`, `REVIEW`, and `DENY` semantics; prohibit unbounded guilt by association and universal security claims; unsupported or stale critical inputs fail closed.
- Gap task: Add machine-checked threat and authority policies with positive and rejection fixtures; do not implement chain logic.
- Refinement: Narrow evidence-bound claims are preferable to broad claims that the current models cannot prove.
- Embedding query: crypto trust boundary proof authority sanctions legal policy fail closed threat model
- AST query: AnalysisAuthority PolicyAuthority TransactionVerdict EvidenceFreshness

## CRYPTOIR-G020 Build the canonical Crypto IR model, identity, provenance, and schema core

- Status: active
- Review only: false
- Parent: CRYPTOIR-G000
- Fib priority: 3
- Priority: P0
- Track: crypto-ir-kernel
- Bundle: crypto-ir/kernel
- Depends on: CRYPTOIR-G010
- Parallel lane: kernel-model
- Conflict policy: sole owner of the root crypto_ir package exports, foundational records, canonical identity profile, and schema registry
- Submodules: ipfs_datasets_py
- Resource class: cpu-medium
- Token class: small
- Goal: Define immutable chain-neutral records for wallet identities, assets, exact amounts, unsigned intents, serialized candidates, contract artifacts, observations, claims, evidence, completeness, and time-bounded epochs by adapting `logic.ir_core`.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/logic/crypto_ir/model.py, ipfs_datasets_py/tests/unit/logic/crypto_ir/test_model.py
- Outputs: ipfs_datasets_py/ipfs_datasets_py/logic/crypto_ir/__init__.py, ipfs_datasets_py/ipfs_datasets_py/logic/crypto_ir/model.py, ipfs_datasets_py/ipfs_datasets_py/logic/crypto_ir/identity.py, ipfs_datasets_py/ipfs_datasets_py/logic/crypto_ir/provenance.py, ipfs_datasets_py/ipfs_datasets_py/logic/crypto_ir/schema_versions.py, ipfs_datasets_py/tests/unit/logic/crypto_ir/test_model.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/logic/crypto_ir/test_model.py
- Acceptance: Records are frozen, strict, round-trippable, mutation resistant, and content addressed; identity includes chain/genesis and schema profiles; amounts reject floats; ordering and multiplicity are explicit; observations carry finality, completeness, validity, and retraction; unknown authoritative extensions fail closed; shared ir_core types are reused rather than cloned.
- Gap task: Implement the minimal versioned kernel and golden canonicalization vectors without adding chain-specific parsing.
- Refinement: Separate declarations, observations, assumptions, results, and authorization so conversion cannot elevate authority.
- Embedding query: immutable chain neutral wallet transaction contract ir canonical identity provenance epoch
- AST query: ChainIdentity AccountIdentity UnsignedTransactionIntent SerializedTransactionCandidate ContractArtifact CompletenessReceipt

## CRYPTOIR-G030 Add capabilities, adapters, registries, and non-interchangeable verdicts

- Status: active
- Review only: false
- Parent: CRYPTOIR-G000
- Fib priority: 5
- Priority: P0
- Track: crypto-ir-kernel
- Bundle: crypto-ir/kernel
- Depends on: CRYPTOIR-G020
- Parallel lane: kernel-adapters
- Conflict policy: sole owner of crypto_ir adapter exports, capability registry, and verdict compatibility layer
- Submodules: ipfs_datasets_py
- Resource class: cpu-medium
- Token class: small
- Goal: Define side-effect-free adapter and capability protocols for wallet records, Security IR, software-contract IR, knowledge graphs, and prover backends while preserving distinct result authority.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/logic/crypto_ir/capabilities.py, ipfs_datasets_py/tests/unit/logic/crypto_ir/test_registry.py
- Outputs: ipfs_datasets_py/ipfs_datasets_py/logic/crypto_ir/capabilities.py, ipfs_datasets_py/ipfs_datasets_py/logic/crypto_ir/registry.py, ipfs_datasets_py/ipfs_datasets_py/logic/crypto_ir/verdicts.py, ipfs_datasets_py/ipfs_datasets_py/logic/crypto_ir/adapters/__init__.py, ipfs_datasets_py/tests/unit/logic/crypto_ir/test_registry.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/logic/crypto_ir/test_registry.py
- Acceptance: Discovery has no import-time network or installation; adapters preserve provenance and unsupported fields; proof, satisfiability, monitor, readiness, heuristic, sanctions, and policy results cannot be silently coerced; capability identities bind implementation and semantic versions; unavailable capabilities return typed fail-closed results.
- Gap task: Implement strict protocols and a deterministic registry, then prove authority-confusion and import-side-effect rejection cases.
- Refinement: Adapt mature primitives behind narrow interfaces rather than copying their data models.
- Embedding query: crypto ir adapter registry wallet security ir proof capability typed verdict
- AST query: CryptoIRAdapter CapabilityDescriptor AnalysisVerdict PolicyVerdict AdapterRegistry

## CRYPTOIR-G100 Implement the EVM wallet-to-Crypto-IR adapter

- Status: active
- Review only: false
- Parent: CRYPTOIR-G000
- Fib priority: 8
- Priority: P0
- Track: chain-adapter
- Bundle: crypto-ir/adapter-evm
- Depends on: CRYPTOIR-G030
- Parallel lane: adapter-evm
- Conflict policy: owns only the EVM adapter and its unit tests
- Submodules: ipfs_datasets_py
- Resource class: cpu-small
- Token class: small
- Goal: Convert Ethereum and EVM wallet observations and unsigned transaction candidates into chain-qualified Crypto IR without inventing missing receipt, trace, token, or finality facts.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/logic/crypto_ir/adapters/evm.py
- Outputs: ipfs_datasets_py/ipfs_datasets_py/logic/crypto_ir/adapters/evm.py, ipfs_datasets_py/tests/unit/logic/crypto_ir/adapters/test_evm.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/logic/crypto_ir/adapters/test_evm.py
- Acceptance: Chain ID and genesis identity, checksummed/original addresses, native and token assets, exact amounts, calldata, receipts, logs, traces, finality, and missing coverage survive conversion; World Chain remains a distinct network; round trips do not promote observations to proof.
- Gap task: Add deterministic fixture-driven conversion and rejection tests; do not fetch code or call networks.
- Refinement: Preserve raw evidence and explicit absence alongside normalized fields.
- Embedding query: evm ethereum wallet transaction calldata receipt trace crypto ir adapter
- AST query: EVMWalletAdapter EVMTransactionObservation EVMCallIntent

## CRYPTOIR-G110 Implement the Solana wallet-to-Crypto-IR adapter

- Status: active
- Review only: false
- Parent: CRYPTOIR-G000
- Fib priority: 8
- Priority: P0
- Track: chain-adapter
- Bundle: crypto-ir/adapter-solana
- Depends on: CRYPTOIR-G030
- Parallel lane: adapter-solana
- Conflict policy: owns only the Solana adapter and its unit tests
- Submodules: ipfs_datasets_py
- Resource class: cpu-small
- Token class: small
- Goal: Convert Solana wallet records into Crypto IR with exact program, instruction, account, signer, writable, token, inner-instruction, log, slot, and commitment semantics.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/logic/crypto_ir/adapters/solana.py
- Outputs: ipfs_datasets_py/ipfs_datasets_py/logic/crypto_ir/adapters/solana.py, ipfs_datasets_py/tests/unit/logic/crypto_ir/adapters/test_solana.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/logic/crypto_ir/adapters/test_solana.py
- Acceptance: Base58 identities and clusters do not collide; signer/writable/account-order semantics are preserved; lamports and token base units are exact; slot commitment and incomplete inner-instruction coverage remain explicit; unsupported versioned messages fail closed.
- Gap task: Add offline conversion fixtures for legacy and supported versioned messages plus malformed and partial cases.
- Refinement: Account order and privilege bits are semantic, not presentation details.
- Embedding query: solana wallet program instruction signer writable token crypto ir adapter
- AST query: SolanaWalletAdapter SolanaInstruction AccountPrivilege

## CRYPTOIR-G120 Implement the XRPL and Xaman wallet-to-Crypto-IR adapter

- Status: active
- Review only: false
- Parent: CRYPTOIR-G000
- Fib priority: 8
- Priority: P0
- Track: chain-adapter
- Bundle: crypto-ir/adapter-xrpl
- Depends on: CRYPTOIR-G030
- Parallel lane: adapter-xrpl
- Conflict policy: owns only the XRPL and Xaman adapter and tests
- Submodules: ipfs_datasets_py
- Resource class: cpu-small
- Token class: small
- Goal: Convert XRPL and Xaman records into native-ledger Crypto IR while preserving classic/X-address, tag, issued-currency, trust-line, partial-payment, sequence/ticket, signer, and finality semantics.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/logic/crypto_ir/adapters/xrpl.py
- Outputs: ipfs_datasets_py/ipfs_datasets_py/logic/crypto_ir/adapters/xrpl.py, ipfs_datasets_py/tests/unit/logic/crypto_ir/adapters/test_xrpl.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/logic/crypto_ir/adapters/test_xrpl.py
- Acceptance: Address/tag identity is lossless; XRP and issued assets cannot collide; issuer, flags, delivered amount, partial-payment, sequence/ticket, signer, and validated-ledger facts remain typed; Hooks and EVM behavior are never inferred without network capability evidence.
- Gap task: Implement shared XRPL/Xaman conversion over offline ledger fixtures and explicit unsupported cases.
- Refinement: Model XRPL as native ledger state transitions, not as Ethereum-shaped contracts.
- Embedding query: xrpl ripple xaman wallet destination tag trust line issued currency crypto ir
- AST query: XRPLWalletAdapter XRPLAccountIdentity IssuedAsset LedgerTransition

## CRYPTOIR-G130 Implement the Bitcoin wallet-to-Crypto-IR adapter

- Status: active
- Review only: false
- Parent: CRYPTOIR-G000
- Fib priority: 8
- Priority: P0
- Track: chain-adapter
- Bundle: crypto-ir/adapter-bitcoin
- Depends on: CRYPTOIR-G030
- Parallel lane: adapter-bitcoin
- Conflict policy: owns only the Bitcoin adapter and its unit tests
- Submodules: ipfs_datasets_py
- Resource class: cpu-small
- Token class: small
- Goal: Convert Bitcoin wallet, transaction, UTXO, script classification, and finality records into network-bound Crypto IR with exact input/output and spending-context identity.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/logic/crypto_ir/adapters/bitcoin.py
- Outputs: ipfs_datasets_py/ipfs_datasets_py/logic/crypto_ir/adapters/bitcoin.py, ipfs_datasets_py/tests/unit/logic/crypto_ir/adapters/test_bitcoin.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/logic/crypto_ir/adapters/test_bitcoin.py
- Acceptance: Network/genesis, txid byte order, outpoints, satoshis, script bytes, witness context, confirmations, replacement, coinbase, and reorg state are preserved; address strings are never treated as the canonical spending identity; missing previous outputs remain incomplete.
- Gap task: Add deterministic UTXO conversion and identity vectors without implementing Script execution.
- Refinement: Outpoints and script commitments are authoritative where display addresses are not.
- Embedding query: bitcoin wallet utxo outpoint script witness crypto ir adapter
- AST query: BitcoinWalletAdapter UtxoInput SpendingCondition Outpoint

## CRYPTOIR-G140 Implement Worldcoin, World ID, and World Chain composition

- Status: active
- Review only: false
- Parent: CRYPTOIR-G000
- Fib priority: 13
- Priority: P1
- Track: chain-adapter
- Bundle: crypto-ir/adapter-worldcoin
- Depends on: CRYPTOIR-G030, CRYPTOIR-G100
- Parallel lane: adapter-worldcoin
- Conflict policy: owns only Worldcoin and World ID adapter semantics and tests
- Submodules: ipfs_datasets_py
- Resource class: cpu-small
- Token class: small
- Goal: Compose the EVM adapter for World Chain while representing WLD assets, World ID proof-domain facts, nullifiers, actions, verifier instances, bridges, and Mini App evidence without conflating them.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/logic/crypto_ir/adapters/worldcoin.py
- Outputs: ipfs_datasets_py/ipfs_datasets_py/logic/crypto_ir/adapters/worldcoin.py, ipfs_datasets_py/tests/unit/logic/crypto_ir/adapters/test_worldcoin.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/logic/crypto_ir/adapters/test_worldcoin.py
- Acceptance: World ID, World Chain, WLD, verifier, bridge, nullifier, action, RP/app, and proof observations remain distinct; chain/domain binding is mandatory; proof observations confer neither identity nor transaction authorization by themselves.
- Gap task: Add composition records and cross-domain confusion fixtures over existing Worldcoin wallet models.
- Refinement: Reuse EVM transaction semantics, but never collapse proof, identity, asset, and chain authorities.
- Embedding query: worldcoin world id world chain wld nullifier verifier crypto ir
- AST query: WorldcoinAdapter WorldIDObservation NullifierBinding WorldChainIdentity

## CRYPTOIR-G200 Create the bounded smart-contract processor core

- Status: active
- Review only: false
- Parent: CRYPTOIR-G000
- Fib priority: 8
- Priority: P0
- Track: smart-contract-core
- Bundle: smart-contracts/core
- Depends on: CRYPTOIR-G020, CRYPTOIR-G030
- Parallel lane: contract-core
- Conflict policy: sole owner of the smart_contracts root package exports and shared processor contracts
- Submodules: ipfs_datasets_py
- Resource class: cpu-medium
- Token class: small
- Goal: Create `processors.smart_contracts` with immutable requests/results, dependency-injected capability protocols, strict errors, canonical records, and no-key/no-sign/no-broadcast boundaries.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/processors/smart_contracts/models.py, ipfs_datasets_py/tests/unit/processors/smart_contracts/test_models.py
- Outputs: ipfs_datasets_py/ipfs_datasets_py/processors/smart_contracts/__init__.py, ipfs_datasets_py/ipfs_datasets_py/processors/smart_contracts/models.py, ipfs_datasets_py/ipfs_datasets_py/processors/smart_contracts/protocols.py, ipfs_datasets_py/ipfs_datasets_py/processors/smart_contracts/errors.py, ipfs_datasets_py/ipfs_datasets_py/processors/smart_contracts/canonical.py, ipfs_datasets_py/tests/unit/processors/smart_contracts/test_models.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/processors/smart_contracts/test_models.py
- Acceptance: Requests carry chain, network, artifact kind, bounds, cancellation, deadlines, and provider policy; results distinguish unavailable, partial, unsupported, inconsistent, poisoned, stale, and error; imports perform no network or installation; public records contain no private-key or signing surface.
- Gap task: Scaffold the shared read-only processor contracts and strict offline tests; do not add live providers.
- Refinement: Acquisition capability is explicit and separately injected from parsing and analysis.
- Embedding query: smart contract processor bounded acquisition protocol canonical provenance no signing
- AST query: ContractAcquisitionRequest ContractAcquisitionResult ArtifactProvider SmartContractProcessor

## CRYPTOIR-G210 Add bounded artifact acquisition, storage, caching, and provenance

- Status: active
- Review only: false
- Parent: CRYPTOIR-G000
- Fib priority: 13
- Priority: P0
- Track: smart-contract-core
- Bundle: smart-contracts/acquisition
- Depends on: CRYPTOIR-G010, CRYPTOIR-G200
- Parallel lane: contract-acquisition
- Conflict policy: owns shared artifact transport, source manifests, immutable cache, and acquisition tests only
- Submodules: ipfs_datasets_py
- Resource class: io-large
- Token class: small
- Goal: Acquire raw code, state, source, interface, compiler, and build artifacts through bounded allowlisted transports; store untouched bytes and deterministic manifests; and cache only content-bound results.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/processors/smart_contracts/artifacts.py, ipfs_datasets_py/tests/unit/processors/smart_contracts/test_acquisition.py
- Outputs: ipfs_datasets_py/ipfs_datasets_py/processors/smart_contracts/artifacts.py, ipfs_datasets_py/ipfs_datasets_py/processors/smart_contracts/transport.py, ipfs_datasets_py/ipfs_datasets_py/processors/smart_contracts/cache.py, ipfs_datasets_py/ipfs_datasets_py/processors/smart_contracts/source.py, ipfs_datasets_py/tests/unit/processors/smart_contracts/test_acquisition.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/processors/smart_contracts/test_acquisition.py
- Acceptance: URL schemes, hosts, DNS, redirects, response counts, bytes, archives, recursion, time, retries, and credentials are bounded; raw bytes and request/response metadata are content addressed; poisoning, truncation, schema drift, provider disagreement, cache corruption, and artifact/toolchain mismatch fail closed; offline fixtures are default.
- Gap task: Implement injected transports, immutable manifests, strict CAS validation, and hostile endpoint/archive fixtures.
- Refinement: Preserve disagreement and partial coverage rather than choosing a permissive provider response.
- Embedding query: contract artifact source acquisition ssrf bounds cache provenance reproducible build
- AST query: ArtifactManifest SourceManifest AcquisitionTransport ContractArtifactCache

## CRYPTOIR-G220 Implement the EVM contract frontend and deployment semantics

- Status: active
- Review only: false
- Parent: CRYPTOIR-G000
- Fib priority: 21
- Priority: P0
- Track: smart-contract-chain
- Bundle: smart-contracts/evm
- Depends on: CRYPTOIR-G100, CRYPTOIR-G210
- Parallel lane: contract-evm
- Conflict policy: owns only the smart_contracts.evm package and EVM frontend tests
- Submodules: ipfs_datasets_py
- Resource class: cpu-large
- Token class: medium
- Goal: Acquire and normalize EVM creation/runtime bytecode, source, ABI, compiler/build metadata, storage, traces, proxies, implementations, upgrades, opcodes, CFG, call graph, and effects into Crypto IR.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/processors/smart_contracts/evm/frontend.py, ipfs_datasets_py/tests/unit/processors/smart_contracts/evm/test_frontend.py
- Outputs: ipfs_datasets_py/ipfs_datasets_py/processors/smart_contracts/evm/__init__.py, ipfs_datasets_py/ipfs_datasets_py/processors/smart_contracts/evm/provider.py, ipfs_datasets_py/ipfs_datasets_py/processors/smart_contracts/evm/frontend.py, ipfs_datasets_py/ipfs_datasets_py/processors/smart_contracts/evm/semantics.py, ipfs_datasets_py/ipfs_datasets_py/processors/smart_contracts/evm/proxies.py, ipfs_datasets_py/tests/unit/processors/smart_contracts/evm/test_frontend.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/processors/smart_contracts/evm/test_frontend.py
- Acceptance: Artifacts bind chain, address, block, code epoch, compiler, flags, libraries, constructor, and metadata policy; source/deployed equivalence is reproduced rather than trusted; EIP-1967, beacon, diamond, minimal-proxy, delegatecall, selfdestruct/redeployment, and unknown proxy cases are explicit; unsupported opcodes or incomplete traces never pass.
- Gap task: Implement bounded offline EVM provider/frontends and golden bytecode, source-match, proxy, upgrade, and malformed fixtures.
- Refinement: Analyze deployed runtime independently when verified source cannot be reproduced.
- Embedding query: evm bytecode solidity vyper abi proxy upgrade opcode cfg smart contract frontend
- AST query: EVMContractFrontend EVMCodeEpoch ProxyBinding ControlFlowGraph StorageEffect

## CRYPTOIR-G230 Implement the Solana program frontend and deployment semantics

- Status: active
- Review only: false
- Parent: CRYPTOIR-G000
- Fib priority: 21
- Priority: P0
- Track: smart-contract-chain
- Bundle: smart-contracts/solana
- Depends on: CRYPTOIR-G110, CRYPTOIR-G210
- Parallel lane: contract-solana
- Conflict policy: owns only the smart_contracts.solana package and Solana frontend tests
- Submodules: ipfs_datasets_py
- Resource class: cpu-large
- Token class: medium
- Goal: Acquire executable/program/program-data accounts, SBF ELF, loader state, upgrade authority, IDL/source/build artifacts, instructions, CPI, logs, and account data-flow semantics.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/processors/smart_contracts/solana/frontend.py, ipfs_datasets_py/tests/unit/processors/smart_contracts/solana/test_frontend.py
- Outputs: ipfs_datasets_py/ipfs_datasets_py/processors/smart_contracts/solana/__init__.py, ipfs_datasets_py/ipfs_datasets_py/processors/smart_contracts/solana/provider.py, ipfs_datasets_py/ipfs_datasets_py/processors/smart_contracts/solana/frontend.py, ipfs_datasets_py/ipfs_datasets_py/processors/smart_contracts/solana/semantics.py, ipfs_datasets_py/ipfs_datasets_py/processors/smart_contracts/solana/loader.py, ipfs_datasets_py/tests/unit/processors/smart_contracts/solana/test_frontend.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/processors/smart_contracts/solana/test_frontend.py
- Acceptance: Loader version, executable/program-data relation, binary hash, deployment slot, upgrade authority, IDL/build correspondence, signer/writable privileges, PDA seeds, owners, CPI graph, inner instructions, and coverage are explicit; source claims without reproducible SBF equality remain evidence only.
- Gap task: Implement offline program acquisition and normalized SBF/Anchor semantics with loader, CPI, upgrade, and account-substitution fixtures.
- Refinement: Privilege and owner checks are first-class semantics, not generic call metadata.
- Embedding query: solana program sbf elf anchor idl loader upgrade authority cpi frontend
- AST query: SolanaProgramFrontend ProgramDataEpoch UpgradeAuthority CPIEdge PDAConstraint

## CRYPTOIR-G240 Implement XRPL native-ledger, Hooks, and sidechain semantics

- Status: active
- Review only: false
- Parent: CRYPTOIR-G000
- Fib priority: 21
- Priority: P1
- Track: smart-contract-chain
- Bundle: smart-contracts/xrpl
- Depends on: CRYPTOIR-G120, CRYPTOIR-G210
- Parallel lane: contract-xrpl
- Conflict policy: owns only the smart_contracts.xrpl package and XRPL semantic tests
- Submodules: ipfs_datasets_py
- Resource class: cpu-medium
- Token class: medium
- Goal: Normalize XRPL account flags, trust lines, escrows, checks, payment channels, offers, AMMs, NFTs, signer lists, Hooks where capability-proven, and Ripple EVM sidechain delegation as native state machines.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/processors/smart_contracts/xrpl/frontend.py, ipfs_datasets_py/tests/unit/processors/smart_contracts/xrpl/test_frontend.py
- Outputs: ipfs_datasets_py/ipfs_datasets_py/processors/smart_contracts/xrpl/__init__.py, ipfs_datasets_py/ipfs_datasets_py/processors/smart_contracts/xrpl/provider.py, ipfs_datasets_py/ipfs_datasets_py/processors/smart_contracts/xrpl/frontend.py, ipfs_datasets_py/ipfs_datasets_py/processors/smart_contracts/xrpl/semantics.py, ipfs_datasets_py/tests/unit/processors/smart_contracts/xrpl/test_frontend.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/processors/smart_contracts/xrpl/test_frontend.py
- Acceptance: Native ledger objects, amendment/capability state, issuer/freeze/clawback, partial payment, reserve, sequence/ticket, signer quorum, tags, and validated-ledger epochs are modeled; Hooks return `UNSUPPORTED` where absent; an EVM sidechain delegates to the EVM frontend and is never silently treated as XRPL mainnet.
- Gap task: Build fixture-driven native transition semantics with explicit Hooks and sidechain capability routing.
- Refinement: Emit `UNSUPPORTED` or `UNKNOWN` instead of inventing Ethereum-style contract behavior.
- Embedding query: xrpl ripple ledger hooks escrow trustline amm signer state machine smart contract
- AST query: XRPLLedgerFrontend LedgerObjectTransition HookCapability IssuerPolicy

## CRYPTOIR-G250 Implement Bitcoin Script, Tapscript, Miniscript, and PSBT semantics

- Status: active
- Review only: false
- Parent: CRYPTOIR-G000
- Fib priority: 21
- Priority: P0
- Track: smart-contract-chain
- Bundle: smart-contracts/bitcoin
- Depends on: CRYPTOIR-G130, CRYPTOIR-G210
- Parallel lane: contract-bitcoin
- Conflict policy: owns only the smart_contracts.bitcoin package and Bitcoin semantic tests
- Submodules: ipfs_datasets_py
- Resource class: cpu-large
- Token class: medium
- Goal: Normalize legacy Script, SegWit, Tapscript leaves/control blocks, descriptors, Miniscript, witnesses, PSBTs, prevouts, sighash, timelock, hashlock, and threshold spending paths into Crypto IR.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/processors/smart_contracts/bitcoin/frontend.py, ipfs_datasets_py/tests/unit/processors/smart_contracts/bitcoin/test_frontend.py
- Outputs: ipfs_datasets_py/ipfs_datasets_py/processors/smart_contracts/bitcoin/__init__.py, ipfs_datasets_py/ipfs_datasets_py/processors/smart_contracts/bitcoin/frontend.py, ipfs_datasets_py/ipfs_datasets_py/processors/smart_contracts/bitcoin/script.py, ipfs_datasets_py/ipfs_datasets_py/processors/smart_contracts/bitcoin/tapscript.py, ipfs_datasets_py/ipfs_datasets_py/processors/smart_contracts/bitcoin/miniscript.py, ipfs_datasets_py/tests/unit/processors/smart_contracts/bitcoin/test_frontend.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/processors/smart_contracts/bitcoin/test_frontend.py
- Acceptance: Stack and spending-path semantics bind exact prevouts, amounts, script versions, witness/control commitments, sighash flags, locktime/sequence, policy keys, and resource bounds; hidden or unavailable branches remain incomplete; descriptor/miniscript policy equality is proven or explicitly unknown.
- Gap task: Implement bounded offline decoders and semantic records with alternative-spend, weak-sighash, timelock, control-block, and descriptor-mismatch fixtures.
- Refinement: Model spend conditions rather than pretending Bitcoin has account contracts.
- Embedding query: bitcoin script tapscript miniscript descriptor psbt sighash timelock semantics
- AST query: BitcoinScriptFrontend ScriptProgram TapscriptLeaf MiniscriptPolicy SighashCommitment

## CRYPTOIR-G260 Implement World Chain contract and World ID verifier semantics

- Status: active
- Review only: false
- Parent: CRYPTOIR-G000
- Fib priority: 34
- Priority: P1
- Track: smart-contract-chain
- Bundle: smart-contracts/worldcoin
- Depends on: CRYPTOIR-G140, CRYPTOIR-G220
- Parallel lane: contract-worldcoin
- Conflict policy: owns only the smart_contracts.worldcoin package and Worldcoin semantic tests
- Submodules: ipfs_datasets_py
- Resource class: cpu-medium
- Token class: medium
- Goal: Compose EVM semantics for World Chain and add explicit World ID verifier, external-nullifier, action/domain, bridge, proxy, and upgrade semantics.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/processors/smart_contracts/worldcoin/frontend.py, ipfs_datasets_py/tests/unit/processors/smart_contracts/worldcoin/test_frontend.py
- Outputs: ipfs_datasets_py/ipfs_datasets_py/processors/smart_contracts/worldcoin/__init__.py, ipfs_datasets_py/ipfs_datasets_py/processors/smart_contracts/worldcoin/frontend.py, ipfs_datasets_py/ipfs_datasets_py/processors/smart_contracts/worldcoin/semantics.py, ipfs_datasets_py/tests/unit/processors/smart_contracts/worldcoin/test_frontend.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/processors/smart_contracts/worldcoin/test_frontend.py
- Acceptance: Verifier and implementation code epochs, chain/domain/action/external-nullifier bindings, proof-consumer behavior, bridge assumptions, proxy upgrades, and replay boundaries are explicit; a valid identity proof never implies payment authorization, legal identity, or contract safety.
- Gap task: Add World Chain composition and adversarial World ID domain/nullifier/verifier-upgrade fixtures.
- Refinement: State every external verifier and bridge trust assumption.
- Embedding query: world chain world id verifier external nullifier action bridge proxy contract
- AST query: WorldcoinContractFrontend WorldIDVerifierBinding ExternalNullifier ReplayDomain

## CRYPTOIR-G300 Define chain-neutral contract state, control, and effect semantics

- Status: active
- Review only: false
- Parent: CRYPTOIR-G000
- Fib priority: 13
- Priority: P0
- Track: assurance-core
- Bundle: crypto-ir/semantics
- Depends on: CRYPTOIR-G020, CRYPTOIR-G200
- Parallel lane: assurance-semantics
- Conflict policy: owns only common contract semantic records and tests
- Submodules: ipfs_datasets_py
- Resource class: cpu-medium
- Token class: medium
- Goal: Define chain-neutral state epochs, control-flow, call/instruction/spend edges, principals, privileges, asset effects, invariants, assumptions, coverage, and unsupported semantics without erasing chain-specific behavior.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/logic/crypto_ir/contract_semantics.py, ipfs_datasets_py/tests/unit/logic/crypto_ir/test_contract_semantics.py
- Outputs: ipfs_datasets_py/ipfs_datasets_py/logic/crypto_ir/contract_semantics.py, ipfs_datasets_py/ipfs_datasets_py/logic/crypto_ir/state.py, ipfs_datasets_py/ipfs_datasets_py/logic/crypto_ir/effects.py, ipfs_datasets_py/tests/unit/logic/crypto_ir/test_contract_semantics.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/logic/crypto_ir/test_contract_semantics.py
- Acceptance: Common records preserve order, privileges, reentrancy/CPI/spend-path distinctions, exact assets, state/code epochs, assumptions, coverage frontiers, and source provenance; a chain adapter can declare unsupported semantics; lossy projection cannot satisfy a proof obligation that depends on discarded facts.
- Gap task: Implement minimal shared semantic primitives and projection-loss rejection tests.
- Refinement: Share concepts, not false equivalences between VMs and ledger models.
- Embedding query: chain neutral contract state transition control flow asset effect invariant semantics
- AST query: ContractStateEpoch ControlEdge AssetEffect SemanticCoverage UnsupportedSemantic

## CRYPTOIR-G310 Define common and chain-specific security rules

- Status: active
- Review only: false
- Parent: CRYPTOIR-G000
- Fib priority: 21
- Priority: P0
- Track: assurance-core
- Bundle: crypto-ir/security-rules
- Depends on: CRYPTOIR-G300
- Parallel lane: assurance-rules
- Conflict policy: owns security claim and obligation rule packs only
- Submodules: ipfs_datasets_py
- Resource class: cpu-medium
- Token class: medium
- Goal: Encode named obligations for authorization, value conservation, mint/burn/transfer/allowance, replay, callback/reentrancy/CPI, arithmetic, upgrades, oracle freshness, intent/effect equality, timelocks, and resource bounds with chain applicability.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/logic/crypto_ir/security_rules.py, ipfs_datasets_py/tests/unit/logic/crypto_ir/test_security_rules.py
- Outputs: ipfs_datasets_py/ipfs_datasets_py/logic/crypto_ir/security_rules.py, ipfs_datasets_py/ipfs_datasets_py/logic/crypto_ir/chain_rules.py, ipfs_datasets_py/tests/unit/logic/crypto_ir/test_security_rules.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/logic/crypto_ir/test_security_rules.py
- Acceptance: Every rule declares chain/semantic preconditions, trusted assumptions, required evidence, formal target, violation witness, and unsupported fallback; inappropriate rules do not silently apply; security conclusions name exact obligations and never collapse into universal “secure”.
- Gap task: Add versioned rule descriptors and positive, violated, missing-semantic, and wrong-chain fixtures.
- Refinement: A rule is admissible only when the frontend proves it supplies every semantic dependency.
- Embedding query: smart contract security obligation authorization conservation replay reentrancy upgrade oracle
- AST query: SecurityRule ProofObligation RuleApplicability ViolationWitness

## CRYPTOIR-G320 Build sound formal lowering, prover routing, and analysis receipts

- Status: active
- Review only: false
- Parent: CRYPTOIR-G000
- Fib priority: 21
- Priority: P0
- Track: assurance-formal
- Bundle: crypto-ir/formalization
- Depends on: CRYPTOIR-G030, CRYPTOIR-G300
- Parallel lane: assurance-formalization
- Conflict policy: sole owner of crypto_ir formalization exports, supported lowerings, portfolio routing, and proof receipts
- Submodules: ipfs_datasets_py
- Resource class: cpu-large
- Token class: medium
- Goal: Lower supported obligations soundly into existing executable SMT-LIB, propositional/FOL, Datalog, temporal, CVC5, or Z3 backends; route a bounded portfolio; and emit evidence-bound attempts, counterexamples, and typed receipts.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/logic/crypto_ir/formalization/compiler.py, ipfs_datasets_py/tests/unit/logic/crypto_ir/formalization/test_compiler.py
- Outputs: ipfs_datasets_py/ipfs_datasets_py/logic/crypto_ir/formalization/__init__.py, ipfs_datasets_py/ipfs_datasets_py/logic/crypto_ir/formalization/obligations.py, ipfs_datasets_py/ipfs_datasets_py/logic/crypto_ir/formalization/compiler.py, ipfs_datasets_py/ipfs_datasets_py/logic/crypto_ir/formalization/portfolio.py, ipfs_datasets_py/ipfs_datasets_py/logic/crypto_ir/formalization/receipts.py, ipfs_datasets_py/tests/unit/logic/crypto_ir/formalization/test_compiler.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/logic/crypto_ir/formalization/test_compiler.py
- Acceptance: Each lowering declares soundness scope and supported theory; selected backends actually execute; receipts bind obligation/model/tool/policy/capability/timeout; opaque `security_verification_condition` JSON, prose, unsupported theory, unavailable solver, timeout, disagreement, or incomplete model yields explicit non-proof authority; SAT is not silently a security proof.
- Gap task: Implement reviewed lowering contracts and differential proof/disproof/unknown/unavailable/timeout fixtures over existing prover registries.
- Refinement: Never submit an opaque serialization to a backend that does not compile its logic family.
- Embedding query: formal verification lowering smtlib z3 cvc5 datalog temporal proof receipt
- AST query: ObligationCompiler ProverPortfolio AnalysisReceipt ProofAuthority LoweringContract

## CRYPTOIR-G330 Add sandboxed simulation, differential analysis, and counterexamples

- Status: active
- Review only: false
- Parent: CRYPTOIR-G000
- Fib priority: 34
- Priority: P1
- Track: assurance-dynamic
- Bundle: crypto-ir/simulation
- Depends on: CRYPTOIR-G210, CRYPTOIR-G220, CRYPTOIR-G230, CRYPTOIR-G300
- Parallel lane: assurance-simulation
- Conflict policy: owns simulation and differential-analysis adapters only
- Submodules: ipfs_datasets_py
- Resource class: cpu-large
- Token class: medium
- Goal: Run bounded sandboxed simulations and differential checks over exact chain state snapshots, preserve traces and counterexamples, and label their monitor/evidence authority.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/logic/crypto_ir/simulation.py, ipfs_datasets_py/tests/unit/logic/crypto_ir/test_simulation.py
- Outputs: ipfs_datasets_py/ipfs_datasets_py/logic/crypto_ir/simulation.py, ipfs_datasets_py/ipfs_datasets_py/logic/crypto_ir/differential.py, ipfs_datasets_py/ipfs_datasets_py/logic/crypto_ir/counterexamples.py, ipfs_datasets_py/tests/unit/logic/crypto_ir/test_simulation.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/logic/crypto_ir/test_simulation.py
- Acceptance: State, block/slot, VM, tool, input, time, memory, trace, and network bounds are receipt-bound; state mutation is isolated; counterexamples replay; provider/backend disagreement remains explicit; simulation and monitor satisfaction cannot be promoted to theorem proof.
- Gap task: Add injected offline sandbox protocols and deterministic replay/differential fixtures; production forks remain opt-in.
- Refinement: A useful counterexample can disprove an obligation even when successful traces cannot prove it.
- Embedding query: smart contract sandbox simulation symbolic differential counterexample trace state snapshot
- AST query: SimulationRequest SimulationReceipt DifferentialResult CounterexampleTrace

## CRYPTOIR-G400 Define sanctions authority, snapshots, ownership, and risk policy

- Status: active
- Review only: false
- Parent: CRYPTOIR-G000
- Fib priority: 8
- Priority: P0
- Track: compliance
- Bundle: compliance/policy
- Depends on: CRYPTOIR-G010, CRYPTOIR-G020, CRYPTOIR-G030
- Parallel lane: compliance-policy
- Conflict policy: sole owner of crypto_ir compliance package exports, policy models, and sanctions policy document
- Submodules: ipfs_datasets_py
- Resource class: cpu-medium
- Token class: small
- Goal: Define typed sanctions authorities, list revisions, designations, digital-currency identifiers, entity and aggregate ownership evidence, licenses, jurisdictions, direct matches, indirect exposure, heuristic evidence, and risk-policy outcomes.
- Evidence: ipfs_datasets_py/docs/crypto_ir/SANCTIONS_POLICY.md, ipfs_datasets_py/tests/unit/logic/crypto_ir/compliance/test_policy.py
- Outputs: ipfs_datasets_py/ipfs_datasets_py/logic/crypto_ir/compliance/__init__.py, ipfs_datasets_py/ipfs_datasets_py/logic/crypto_ir/compliance/models.py, ipfs_datasets_py/ipfs_datasets_py/logic/crypto_ir/compliance/policy.py, ipfs_datasets_py/docs/crypto_ir/SANCTIONS_POLICY.md, ipfs_datasets_py/tests/unit/logic/crypto_ir/compliance/test_policy.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/logic/crypto_ir/compliance/test_policy.py
- Acceptance: Exact listed identifier, named party, evidence-backed ownership, direct association, bounded indirect exposure, and heuristic association are non-interchangeable; lists/programs/jurisdictions/effective times/licenses remain typed; `ALLOW` means screened under a named policy and snapshot, not a legal certification; missing legal-policy authority prevents production enforcement.
- Gap task: Add strict policy records, a human review document, and authority-confusion fixtures; do not fetch live lists.
- Refinement: Encode legal-owner-approved rules as versioned inputs instead of hard-coding a universal legal conclusion.
- Embedding query: ofac sdn sanctions digital currency address ownership fifty percent risk policy
- AST query: SanctionsPolicy SanctionsSnapshot DesignationRecord OwnershipEvidence LicenseRecord

## CRYPTOIR-G410 Ingest and validate primary-source OFAC SDN snapshots

- Status: active
- Review only: false
- Parent: CRYPTOIR-G000
- Fib priority: 13
- Priority: P0
- Track: compliance
- Bundle: compliance/sdn-ingest
- Depends on: CRYPTOIR-G400
- Parallel lane: sdn-ingest
- Conflict policy: sole owner of processors.compliance package exports, sanctions exports, OFAC parser, and snapshot validator
- Submodules: ipfs_datasets_py
- Resource class: io-medium
- Token class: medium
- Goal: Fetch or import bounded official OFAC Sanctions List Service artifacts, preserve raw bytes and source metadata, parse SDN digital-currency identifiers, validate snapshots, and enforce freshness and rollback policy.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/processors/compliance/sanctions/ofac_sdn.py, ipfs_datasets_py/tests/unit/processors/compliance/sanctions/test_ofac_sdn.py
- Outputs: ipfs_datasets_py/ipfs_datasets_py/processors/compliance/__init__.py, ipfs_datasets_py/ipfs_datasets_py/processors/compliance/sanctions/__init__.py, ipfs_datasets_py/ipfs_datasets_py/processors/compliance/sanctions/ofac_sdn.py, ipfs_datasets_py/ipfs_datasets_py/processors/compliance/sanctions/snapshot.py, ipfs_datasets_py/tests/unit/processors/compliance/sanctions/test_ofac_sdn.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/processors/compliance/sanctions/test_ofac_sdn.py
- Acceptance: Imports bind official URL, untouched bytes, retrieval/publication/effective time, hashes/signature evidence when available, parser/schema identity, counts, diagnostics, and CID; chain/currency-qualified identifiers from OFAC fields are validated without cross-network coercion; malformed schema, suspicious count drop, truncation, rollback, delisting/effective-time error, or expiry yields `UNKNOWN` or `STALE` and no `ALLOW`; offline historical fixtures are default.
- Gap task: Implement injected primary-source ingestion, append-only snapshot records, chain-specific address parsers, and delta/replay/corruption fixtures.
- Refinement: Search and entity-resolution conveniences never replace the authoritative downloaded snapshot.
- Embedding query: ofac sanctions list service sdn digital currency address snapshot parser freshness
- AST query: OFACSDNParser SanctionsSnapshotValidator DigitalCurrencyIdentifier SnapshotDelta

## CRYPTOIR-G420 Build the multi-chain monetary-flow knowledge graph

- Status: active
- Review only: false
- Parent: CRYPTOIR-G000
- Fib priority: 21
- Priority: P0
- Track: compliance
- Bundle: compliance/flow-graph
- Depends on: CRYPTOIR-G100, CRYPTOIR-G110, CRYPTOIR-G120, CRYPTOIR-G130, CRYPTOIR-G140, CRYPTOIR-G400
- Parallel lane: flow-graph
- Conflict policy: owns only knowledge_graphs.crypto_flows exports, records, builder, store, and tests; never edits the knowledge_graphs root exports
- Submodules: ipfs_datasets_py
- Resource class: io-large
- Token class: medium
- Goal: Build a provenance-preserving, reorg-aware graph of multi-chain transactions, UTXOs, transfers, calls, assets, services, bridges, list facts, entities, ownership evidence, and retractions.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/knowledge_graphs/crypto_flows/model.py, ipfs_datasets_py/tests/unit/knowledge_graphs/crypto_flows/test_builder.py
- Outputs: ipfs_datasets_py/ipfs_datasets_py/knowledge_graphs/crypto_flows/__init__.py, ipfs_datasets_py/ipfs_datasets_py/knowledge_graphs/crypto_flows/model.py, ipfs_datasets_py/ipfs_datasets_py/knowledge_graphs/crypto_flows/builder.py, ipfs_datasets_py/ipfs_datasets_py/knowledge_graphs/crypto_flows/store.py, ipfs_datasets_py/tests/unit/knowledge_graphs/crypto_flows/test_builder.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/knowledge_graphs/crypto_flows/test_builder.py
- Acceptance: Nodes and edges bind chain, ledger coordinate, asset, exact amount, direction, finality, source, confidence, validity, derivation, and retraction; observed-address and asserted-entity graphs remain separate; UTXO and account ledgers are chain-correct; pool, mixer, exchange, bridge, CoinJoin, peel/change, and shared-infrastructure ambiguity is preserved; deterministic snapshots report provider/range/asset completeness.
- Gap task: Implement strict graph records, deterministic ingestion, immutable snapshot/store interfaces, and multi-chain/reorg/ambiguity fixtures.
- Refinement: GraphRAG may retrieve candidate evidence but exact bounded traversal decides exposure.
- Embedding query: blockchain monetary flow knowledge graph utxo account bridge mixer provenance reorg
- AST query: CryptoFlowGraph FlowNode FlowEdge GraphSnapshot CompletenessReceipt

## CRYPTOIR-G430 Formalize bounded exposure and compliance policy

- Status: active
- Review only: false
- Parent: CRYPTOIR-G000
- Fib priority: 34
- Priority: P0
- Track: compliance
- Bundle: compliance/exposure-proof
- Depends on: CRYPTOIR-G320, CRYPTOIR-G400, CRYPTOIR-G410, CRYPTOIR-G420
- Parallel lane: exposure-proof
- Conflict policy: owns bounded exposure traversal, compliance rules, and formal lowering only
- Submodules: ipfs_datasets_py
- Resource class: cpu-large
- Token class: medium
- Goal: Compute exact bounded exposure paths and compile explicit sanctions, ownership, direct-counterparty, freshness, and risk-policy rules into executable supported logic with completeness-qualified negative conclusions.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/logic/crypto_ir/compliance/exposure.py, ipfs_datasets_py/tests/unit/logic/crypto_ir/compliance/test_exposure_proof.py
- Outputs: ipfs_datasets_py/ipfs_datasets_py/logic/crypto_ir/compliance/exposure.py, ipfs_datasets_py/ipfs_datasets_py/logic/crypto_ir/compliance/formalize.py, ipfs_datasets_py/ipfs_datasets_py/logic/crypto_ir/compliance/rules.py, ipfs_datasets_py/tests/unit/logic/crypto_ir/compliance/test_exposure_proof.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/logic/crypto_ir/compliance/test_exposure_proof.py
- Acceptance: Traversal is bounded by depth, nodes, edges, paths, time, asset, amount/ratio, finality, providers, and runtime; every path is explainable and replays against one graph/list/policy snapshot; direct exact hits hard-deny under applicable policy; indirect exposure returns configured `REVIEW` or `DENY` without declaring designation; absence is scoped to a completeness frontier; unsupported lowering or truncation fails closed.
- Gap task: Implement deterministic bounded traversal, supported formalization, proof/disproof/truncation fixtures, and policy property tests.
- Refinement: Never infer unlimited transitive guilt or claim that incomplete graph search proves no connection exists.
- Embedding query: bounded sanctions exposure path theorem prover flow graph completeness direct indirect
- AST query: BoundedExposure ExposurePolicy ComplianceRule ComplianceFormalizer ExposurePath

## CRYPTOIR-G440 Emit explainable compliance decisions and immutable receipts

- Status: active
- Review only: false
- Parent: CRYPTOIR-G000
- Fib priority: 55
- Priority: P0
- Track: compliance
- Bundle: compliance/decisions
- Depends on: CRYPTOIR-G030, CRYPTOIR-G430
- Parallel lane: compliance-decisions
- Conflict policy: owns compliance decision composition, explanations, and immutable evidence receipts only
- Submodules: ipfs_datasets_py
- Resource class: cpu-medium
- Token class: small
- Goal: Combine direct-list, party/ownership, bounded-flow, freshness, license, and uncertainty results deterministically into explainable `ALLOW`, `DENY`, `REVIEW`, `INCONCLUSIVE`, `STALE`, or `ERROR` compliance decisions.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/logic/crypto_ir/compliance/decisions.py, ipfs_datasets_py/tests/unit/logic/crypto_ir/compliance/test_decisions.py
- Outputs: ipfs_datasets_py/ipfs_datasets_py/logic/crypto_ir/compliance/decisions.py, ipfs_datasets_py/ipfs_datasets_py/logic/crypto_ir/compliance/receipts.py, ipfs_datasets_py/ipfs_datasets_py/logic/crypto_ir/compliance/explain.py, ipfs_datasets_py/tests/unit/logic/crypto_ir/compliance/test_decisions.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/logic/crypto_ir/compliance/test_decisions.py
- Acceptance: Decisions bind exact transaction counterparties, list/graph/entity/ownership/license/policy revisions, path evidence, bounds, freshness, uncertainty, reasons, and expiry; deterministic precedence prevents permissive downgrade; heuristic evidence can request review but cannot create designation or allow authority; receipts reproduce byte-for-byte.
- Gap task: Add deterministic policy combination, human/machine explanations, immutable receipts, and precedence/substitution/staleness fixtures.
- Refinement: Explain both the decision and the evidentiary boundary of the decision.
- Embedding query: explainable sanctions compliance decision receipt allow deny review stale evidence
- AST query: ComplianceDecision ComplianceReceipt DecisionReason PolicyCombiner

## CRYPTOIR-G500 Define exact transaction intent and fail-closed preflight guard contracts

- Status: active
- Review only: false
- Parent: CRYPTOIR-G000
- Fib priority: 13
- Priority: P0
- Track: wallet-guard
- Bundle: wallet-guard/core
- Depends on: CRYPTOIR-G030, CRYPTOIR-G200
- Parallel lane: guard-core
- Conflict policy: sole owner of processors.wallets.guard exports, request models, preflight protocol, and guard errors
- Submodules: ipfs_datasets_py
- Resource class: cpu-medium
- Token class: medium
- Goal: Define a custody-neutral guard contract that binds an unsigned intent and exact serialized candidate, composes security and compliance requirements, and specializes existing admissibility receipts and one-use capabilities.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/guard/preflight.py, ipfs_datasets_py/tests/unit/processors/wallets/guard/test_preflight.py
- Outputs: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/guard/__init__.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/guard/models.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/guard/preflight.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/guard/errors.py, ipfs_datasets_py/tests/unit/processors/wallets/guard/test_preflight.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/processors/wallets/guard/test_preflight.py
- Acceptance: Requests bind network, sender, destination, method/instruction/script, assets, amounts, fees, nonce/sequence, UTXOs, signers, serialized bytes, expected effects, and expiry; every non-current `ALLOW` blocks automation; admissibility capabilities are request-bound, one-use, live-revalidated, and atomically consumed; no bare boolean, caller-supplied approval, key, signing, or broadcast API is introduced.
- Gap task: Implement guard protocols over `logic.admissibility` and substitution/replay/expiry/concurrent-consumption tests.
- Refinement: The processor issues evidence-bound permission; an external custody system remains responsible for keys and user approval.
- Embedding query: wallet transaction preflight exact candidate admissibility one use capability fail closed
- AST query: TransactionPreflightRequest TransactionIntent TransactionCandidate AdmissibilityCapability

## CRYPTOIR-G510 Add the smart-contract safety gate

- Status: active
- Review only: false
- Parent: CRYPTOIR-G000
- Fib priority: 55
- Priority: P0
- Track: wallet-guard
- Bundle: wallet-guard/contract
- Depends on: CRYPTOIR-G310, CRYPTOIR-G320, CRYPTOIR-G330, CRYPTOIR-G500
- Parallel lane: guard-contract
- Conflict policy: owns only contract safety gate composition and tests
- Submodules: ipfs_datasets_py
- Resource class: cpu-medium
- Token class: medium
- Goal: Bind a transaction candidate to exact deployed code/state epochs, required named obligations, proof/simulation evidence, assumptions, freshness, and a deterministic contract-safety decision.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/guard/contract_gate.py
- Outputs: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/guard/contract_gate.py, ipfs_datasets_py/tests/unit/processors/wallets/guard/test_contract_gate.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/processors/wallets/guard/test_contract_gate.py
- Acceptance: Exact code/proxy/upgrade/state epochs and required obligation set are receipt-bound; disproved, unsupported-required, unknown, stale, unavailable, errored, mismatched, or unexecuted analyses block automated use; static, simulation, monitor, SAT, and proof authorities remain distinct; an upgraded contract invalidates prior permission.
- Gap task: Implement deterministic security-result composition and adversarial code/proxy/state/obligation substitution tests.
- Refinement: Permit only the transaction whose exact effects and required obligations were evaluated.
- Embedding query: contract safety transaction gate proof obligation code epoch proxy upgrade
- AST query: ContractSafetyGate ContractSafetyDecision RequiredObligationSet CodeEpoch

## CRYPTOIR-G520 Add direct-sanctions and bounded-flow compliance gate

- Status: active
- Review only: false
- Parent: CRYPTOIR-G000
- Fib priority: 55
- Priority: P0
- Track: wallet-guard
- Bundle: wallet-guard/compliance
- Depends on: CRYPTOIR-G410, CRYPTOIR-G440, CRYPTOIR-G500
- Parallel lane: guard-compliance
- Conflict policy: owns only compliance gate composition and tests
- Submodules: ipfs_datasets_py
- Resource class: cpu-medium
- Token class: medium
- Goal: Screen every relevant sender, recipient, spender, beneficiary, contract, token issuer, fee recipient, and derived counterparty against direct sanctions and configured bounded-flow policy before capability issuance and consumption.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/guard/compliance_gate.py
- Outputs: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/guard/compliance_gate.py, ipfs_datasets_py/tests/unit/processors/wallets/guard/test_compliance_gate.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/processors/wallets/guard/test_compliance_gate.py
- Acceptance: Applicable exact listed matches hard-deny; party and ownership decisions require reviewed evidence; indirect exposure obeys named bounds and policy; stale/incomplete list or graph evidence blocks automation; destination indirection, token/router/proxy changes, bridge legs, fee flows, multisend outputs, and UTXO change cannot bypass screening; license exceptions are scoped and expiry-bound.
- Gap task: Implement compliance preflight and direct/indirect/stale/substitution/bypass fixtures.
- Refinement: Screen all economically relevant effects, not only the displayed `to` address.
- Embedding query: wallet sanctions screen direct address indirect flow compliance transaction gate
- AST query: ComplianceGate CounterpartySet SanctionsDecision ExposureDecision

## CRYPTOIR-G530 Integrate the Ethereum transaction guard

- Status: active
- Review only: false
- Parent: CRYPTOIR-G000
- Fib priority: 89
- Priority: P1
- Track: wallet-guard-chain
- Bundle: wallet-guard/ethereum
- Depends on: CRYPTOIR-G220, CRYPTOIR-G510, CRYPTOIR-G520
- Parallel lane: guard-ethereum
- Conflict policy: owns only the Ethereum leaf guard adapter and tests
- Submodules: ipfs_datasets_py
- Resource class: cpu-small
- Token class: medium
- Goal: Normalize Ethereum/EVM transaction candidates and all native/token/contract/proxy effects into the common two-phase guard without adding signing or broadcast.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/ethereum/transaction_guard.py
- Outputs: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/ethereum/transaction_guard.py, ipfs_datasets_py/tests/unit/processors/wallets/ethereum/test_transaction_guard.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/processors/wallets/ethereum/test_transaction_guard.py
- Acceptance: Chain ID, nonce, fee, calldata, value, approvals, internal/token effects, code/proxy epoch, sender recovery, and exact serialized candidate are bound and revalidated; permit substitution, nonce/fee mutation, proxy upgrade, hidden transfer, stale list/graph, and replay fixtures fail closed.
- Gap task: Add the non-custodial EVM guard adapter and offline adversarial fixtures.
- Refinement: An EVM transaction is guarded by actual decoded and simulated effects, not method name alone.
- Embedding query: ethereum wallet transaction guard calldata approval proxy token sanctions
- AST query: EthereumTransactionGuard EVMTransactionCandidate

## CRYPTOIR-G540 Integrate the Solana transaction guard

- Status: active
- Review only: false
- Parent: CRYPTOIR-G000
- Fib priority: 89
- Priority: P1
- Track: wallet-guard-chain
- Bundle: wallet-guard/solana
- Depends on: CRYPTOIR-G230, CRYPTOIR-G510, CRYPTOIR-G520
- Parallel lane: guard-solana
- Conflict policy: owns only the Solana leaf guard adapter and tests
- Submodules: ipfs_datasets_py
- Resource class: cpu-small
- Token class: medium
- Goal: Normalize Solana messages, address tables, programs, accounts, privileges, instructions, CPI effects, lamport/token movements, blockhash, and fees into the two-phase guard.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/solana/transaction_guard.py
- Outputs: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/solana/transaction_guard.py, ipfs_datasets_py/tests/unit/processors/wallets/solana/test_transaction_guard.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/processors/wallets/solana/test_transaction_guard.py
- Acceptance: Message version, account order, address-table epoch, signer/writable bits, recent blockhash, program/program-data epoch, CPI and token effects, and exact bytes are bound; substituted accounts/programs, privilege escalation, hidden CPI transfers, upgrade, stale blockhash, and stale compliance evidence block.
- Gap task: Add the non-custodial Solana guard adapter and adversarial message fixtures.
- Refinement: Re-resolve address tables and executable program epochs at consumption.
- Embedding query: solana wallet transaction guard message account signer cpi token sanctions
- AST query: SolanaTransactionGuard SolanaMessageCandidate

## CRYPTOIR-G550 Integrate XRPL and Xaman transaction guards

- Status: active
- Review only: false
- Parent: CRYPTOIR-G000
- Fib priority: 89
- Priority: P1
- Track: wallet-guard-chain
- Bundle: wallet-guard/xrpl
- Depends on: CRYPTOIR-G240, CRYPTOIR-G510, CRYPTOIR-G520
- Parallel lane: guard-xrpl
- Conflict policy: jointly owns XRPL and Xaman leaf guard adapters because they share normalized XRPL effects
- Submodules: ipfs_datasets_py
- Resource class: cpu-small
- Token class: medium
- Goal: Bind XRPL/Xaman transaction JSON and serialized candidates, accounts/tags, issued assets, flags, delivered amounts, sequence/tickets, signer quorum, native ledger effects, and compliance evidence into the common guard.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/xrpl/transaction_guard.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/xaman/transaction_guard.py
- Outputs: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/xrpl/transaction_guard.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/xaman/transaction_guard.py, ipfs_datasets_py/tests/unit/processors/wallets/xrpl/test_transaction_guard.py, ipfs_datasets_py/tests/unit/processors/wallets/xaman/test_transaction_guard.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/processors/wallets/xrpl/test_transaction_guard.py ipfs_datasets_py/tests/unit/processors/wallets/xaman/test_transaction_guard.py
- Acceptance: Network, destination/tag, issuer/currency/value, partial-payment/delivered amount, sequence/ticket, fee, signer list, ledger epoch, Xaman payload identity, and exact candidate are bound; tag/issuer/amount/signature-list mutation, unsupported Hooks, stale ledger, and compliance changes block.
- Gap task: Add shared XRPL effect normalization and separate non-custodial XRPL/Xaman guard adapters with bypass fixtures.
- Refinement: Xaman approval workflow evidence does not replace transaction policy authorization.
- Embedding query: xrpl xaman transaction guard destination tag issuer partial payment sanctions
- AST query: XRPLTransactionGuard XamanTransactionGuard XRPLTransactionCandidate

## CRYPTOIR-G560 Integrate the Bitcoin transaction guard

- Status: active
- Review only: false
- Parent: CRYPTOIR-G000
- Fib priority: 89
- Priority: P1
- Track: wallet-guard-chain
- Bundle: wallet-guard/bitcoin
- Depends on: CRYPTOIR-G250, CRYPTOIR-G510, CRYPTOIR-G520
- Parallel lane: guard-bitcoin
- Conflict policy: owns only the Bitcoin leaf guard adapter and tests
- Submodules: ipfs_datasets_py
- Resource class: cpu-small
- Token class: medium
- Goal: Bind Bitcoin PSBT/transaction candidates, prevouts, scripts, witnesses, sighashes, outputs, change, fees, locktime/sequence, spending policies, and sanctions exposure into the common guard.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/bitcoin/transaction_guard.py
- Outputs: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/bitcoin/transaction_guard.py, ipfs_datasets_py/tests/unit/processors/wallets/bitcoin/test_transaction_guard.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/processors/wallets/bitcoin/test_transaction_guard.py
- Acceptance: Network, every prevout/amount/script, all outputs and change, fee, RBF, locktime/sequence, sighash commitment, descriptor/spend path, UTXO availability, exact unsigned transaction, list/graph revisions, and exposure paths are bound; output/change/prevout/sighash mutation, spent UTXO, reorg, and stale evidence block.
- Gap task: Add the non-custodial Bitcoin guard adapter and PSBT/UTXO/spending-policy bypass fixtures.
- Refinement: Screen every output and trace UTXO ancestry without assuming CoinJoin ownership.
- Embedding query: bitcoin wallet psbt transaction guard utxo output change sighash sanctions
- AST query: BitcoinTransactionGuard BitcoinTransactionCandidate PSBTBinding

## CRYPTOIR-G570 Integrate Worldcoin and World Chain transaction guards

- Status: active
- Review only: false
- Parent: CRYPTOIR-G000
- Fib priority: 89
- Priority: P1
- Track: wallet-guard-chain
- Bundle: wallet-guard/worldcoin
- Depends on: CRYPTOIR-G260, CRYPTOIR-G510, CRYPTOIR-G520
- Parallel lane: guard-worldcoin
- Conflict policy: owns only the Worldcoin and World Chain leaf guard adapter and tests
- Submodules: ipfs_datasets_py
- Resource class: cpu-small
- Token class: medium
- Goal: Compose EVM transaction guarding for World Chain and add World ID action/domain/nullifier/verifier, WLD, bridge, and Mini App transaction bindings.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin/transaction_guard.py
- Outputs: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin/transaction_guard.py, ipfs_datasets_py/tests/unit/processors/wallets/worldcoin/test_transaction_guard.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/processors/wallets/worldcoin/test_transaction_guard.py
- Acceptance: World Chain ID, candidate bytes, WLD/native effects, verifier/proxy epoch, action/external-nullifier/domain, RP/app, bridge legs, proof age, list/graph/policy, and expected effects are bound; replay/domain/nullifier/verifier/bridge/candidate substitution and stale evidence block; proof success cannot bypass contract or sanctions policy.
- Gap task: Add the non-custodial Worldcoin guard adapter and domain/replay/upgrade/bridge fixtures.
- Refinement: Compose EVM enforcement while preserving World ID-specific evidence boundaries.
- Embedding query: worldcoin world chain transaction guard world id nullifier verifier bridge sanctions
- AST query: WorldcoinTransactionGuard WorldChainTransactionCandidate WorldIDBinding

## CRYPTOIR-G600 Cut over public services, registries, and every signing boundary

- Status: active
- Review only: false
- Parent: CRYPTOIR-G000
- Fib priority: 144
- Priority: P0
- Track: integration
- Bundle: crypto-ir/integration
- Depends on: CRYPTOIR-G530, CRYPTOIR-G540, CRYPTOIR-G550, CRYPTOIR-G560, CRYPTOIR-G570
- Parallel lane: integration-cutover
- Conflict policy: serialized sole owner of existing wallet API/registry and Ethereum signing-helper retrofit after every chain guard is stable
- Submodules: ipfs_datasets_py
- Resource class: cpu-large
- Token class: medium
- Goal: Publish read-only smart-contract and guarded-wallet service APIs, register chain implementations, inventory every sign/broadcast path, and require exact-candidate admissibility capability consumption or disable the path by default.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/guard/service.py, ipfs_datasets_py/tests/unit/processors/wallets/guard/test_service_api.py
- Outputs: ipfs_datasets_py/ipfs_datasets_py/processors/smart_contracts/api.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/guard/service.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/api.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/registry.py, ipfs_datasets_py/ipfs_datasets_py/logic/zkp/eth_integration.py, ipfs_datasets_py/tests/unit/processors/wallets/guard/test_service_api.py, ipfs_datasets_py/tests/unit/logic/zkp/test_eth_transaction_guard.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/processors/wallets/guard/test_service_api.py ipfs_datasets_py/tests/unit/logic/zkp/test_eth_transaction_guard.py
- Acceptance: API/CLI/MCP consumers cannot bypass policy, freshness, exact-candidate binding, live revalidation, or atomic consumption; read-only lookup remains usable without custody authority; every located sign/broadcast helper, including `logic/zkp/eth_integration.py`, is disabled by default or requires the consumed guard capability immediately before signing and broadcast; no processor gains key storage; compatibility behavior is explicit.
- Gap task: Perform a repository-wide signing/broadcast inventory, implement the serialized service/registry cutover, retrofit or disable unsafe paths, and add bypass plus compatibility tests.
- Refinement: Do not expose an “approved=true” compatibility escape hatch; legacy callers must migrate or remain disabled.
- Embedding query: wallet api registry transaction guard admissibility signing broadcast cutover zkp ethereum
- AST query: GuardService WalletRegistry sign_transaction send_raw_transaction broadcast

## CRYPTOIR-G610 Prove cross-chain conformance and deliver operations, release, and rollback

- Status: active
- Review only: false
- Parent: CRYPTOIR-G000
- Fib priority: 233
- Priority: P0
- Track: release
- Bundle: crypto-ir/release
- Depends on: CRYPTOIR-G600
- Parallel lane: release-conformance
- Conflict policy: tests and crypto_ir documentation only; production files are owned by earlier goals
- Submodules: ipfs_datasets_py
- Resource class: cpu-large
- Token class: medium
- Goal: Run cross-chain adversarial conformance, property/fuzz/resource/current-tree tests; reconcile the pinned baseline with reviewed upstream changes; and document observe, shadow, review, direct-list, contract, indirect-flow, rollback, recovery, privacy, legal, and operational gates.
- Evidence: ipfs_datasets_py/tests/contract/logic/crypto_ir/test_multichain_conformance.py, ipfs_datasets_py/docs/crypto_ir/RELEASE_AND_ROLLBACK.md
- Outputs: ipfs_datasets_py/tests/contract/logic/crypto_ir/test_multichain_conformance.py, ipfs_datasets_py/tests/contract/processors/smart_contracts/test_security_gate.py, ipfs_datasets_py/tests/contract/processors/wallets/test_transaction_preflight.py, ipfs_datasets_py/docs/crypto_ir/OPERATIONS.md, ipfs_datasets_py/docs/crypto_ir/RELEASE_AND_ROLLBACK.md
- Validation: python -m pytest -q ipfs_datasets_py/tests/contract/logic/crypto_ir/test_multichain_conformance.py ipfs_datasets_py/tests/contract/processors/smart_contracts/test_security_gate.py ipfs_datasets_py/tests/contract/processors/wallets/test_transaction_preflight.py
- Acceptance: All chain families have positive, adversarial, unsupported, stale, reorg, substitution, and incomplete-evidence cases; no hard-deny or stale-critical fixture obtains `ALLOW`; identities and receipts reproduce; resource and egress budgets hold; no secrets/sign/broadcast/reporting path exists in processors; upgrade/list/graph/policy changes invalidate receipts; rollback preserves audit evidence; named security, privacy, compliance/legal, operations, and release owners approve staged enforcement.
- Gap task: Add the conformance corpus, run current-tree release evidence, reconcile upstream conflicts explicitly, and publish operations/release/rollback playbooks.
- Refinement: Roll out observation and shadow modes first; promote one reviewed enforcement class at a time.
- Embedding query: crypto ir cross chain conformance adversarial release rollback operations sanctions contract gate
- AST query: MultichainConformance ReleaseGate RollbackPlan TransactionPreflight
