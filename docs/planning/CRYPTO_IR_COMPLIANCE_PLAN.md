# Crypto IR, Smart-Contract Assurance, and Transaction Compliance Plan

Status: approved for bounded supervised implementation on the dedicated
integration branch `codex/crypto-ir-contract-compliance`.

This is an engineering and assurance plan, not a legal opinion, an OFAC
license, or a declaration that any person or transaction is lawful. Legal and
compliance owners must approve the jurisdiction, sanctions programs,
ownership rules, licenses, escalation thresholds, retention, reporting, and
release policy before enforcement is enabled.

Companion artifacts:

- Objective heap:
  [`CRYPTO_IR_COMPLIANCE_OBJECTIVES.md`](CRYPTO_IR_COMPLIANCE_OBJECTIVES.md)
- Executable task board:
  [`CRYPTO_IR_COMPLIANCE_TODO.md`](CRYPTO_IR_COMPLIANCE_TODO.md)
- Supervisor runtime:
  `data/crypto_ir_compliance/agent_supervisor/`
- Supervisor launcher:
  `scripts/crypto_ir_compliance_supervisor.sh`

Pinned implementation baseline:

- 211-AI tree: `34b536b59bfb7fcb4c7772b7078fe04709e92fc8`
- `ipfs_datasets_py`: `75ae1de0fd5d8bc3625d26de3ccdd65f3a070dc9`
- `ipfs_accelerate_py`: `c3988ec5e4c55edf8ce541825d82c10e11318745`
- `ipfs_kit_py`: `276d766b8076b725a5a9e53bcf0c057f067acd10`

The baseline descends from the wallet-processor migration and includes the
new read-only multi-chain wallet processors plus the current software-contract
analysis work. Later upstream changes are reconciled through an explicit,
reviewed compatibility gate rather than by following a moving branch.

## 1. Outcome

Build two new package families and connect them to the existing logic,
knowledge-graph, wallet-processor, and theorem-prover layers:

```text
ipfs_datasets_py/ipfs_datasets_py/
├── logic/
│   └── crypto_ir/
│       ├── __init__.py
│       ├── model.py
│       ├── identity.py
│       ├── transactions.py
│       ├── contracts.py
│       ├── observations.py
│       ├── evidence.py
│       ├── results.py
│       ├── policy.py
│       ├── schemas.py
│       ├── adapters/
│       │   ├── wallets.py
│       │   ├── security_ir.py
│       │   ├── software_contracts.py
│       │   └── knowledge_graphs.py
│       ├── formalization/
│       │   ├── compiler.py
│       │   ├── obligations.py
│       │   └── portfolio.py
│       └── compliance/
│           ├── sanctions.py
│           ├── flow_graph.py
│           ├── exposure.py
│           ├── rules.py
│           └── gate.py
└── processors/
    └── smart_contracts/
        ├── __init__.py
        ├── protocols.py
        ├── models.py
        ├── pipeline.py
        ├── registry.py
        ├── storage.py
        ├── provenance.py
        ├── providers/
        ├── evm/
        ├── solana/
        ├── bitcoin/
        ├── xrpl/
        └── worldcoin/
```

`crypto_ir` is a chain-neutral, immutable intermediate representation for:

- public wallet/account identities and capabilities;
- unsigned transaction intentions and exact serialized transaction candidates;
- assets, exact-value transfers, calls, approvals, signers, fees, and UTXOs;
- deployed contracts, programs, scripts, native ledger state machines, code
  epochs, proxies, upgrade authorities, and build/source artifacts;
- observed chain facts with finality, provenance, completeness, and retraction;
- security and compliance claims, assumptions, obligations, findings, and
  counterexamples;
- sanctions-list revisions, designation identifiers, entity/ownership
  evidence, flow-graph snapshots, and exposure paths; and
- analysis results and transaction-policy decisions whose authority is
  explicit and non-interchangeable.

`processors.smart_contracts` is the read-only acquisition and normalization
layer. It downloads or reads bounded artifacts, verifies their provenance,
normalizes chain-specific semantics, and emits Crypto IR. It never stores
private keys, signs, approves, submits, or broadcasts a transaction.

The enforcement output is a fail-closed preflight receipt consumed by a
separate custody wallet or transaction executor immediately before signing and
again immediately before broadcast. The existing wallet processors remain
observation-only.

## 2. Current state and reuse

### 2.1 Wallet processors

The baseline already contains
`ipfs_datasets_py.processors.wallets` implementations for Bitcoin, Ethereum,
Solana, XRPL/Ripple, Xaman, Worldcoin, and World Chain. They provide:

- normalized chain/network/genesis-bound records;
- exact base-unit amounts and typed assets;
- transaction, transfer, UTXO, token-account, contract-event, finality, and
  reorg data;
- bounded RPC/provider reads, checkpoints, storage, registry, pipeline,
  metrics, CLI/MCP adapters, and offline fixtures; and
- explicit no-key, no-signing, and no-broadcast boundaries.

Crypto IR adapts these records rather than replacing the processor schema.
Wallet observations remain evidence; they do not become proof or transaction
authority merely by conversion.

### 2.2 Existing logic and assurance

The implementation must reuse:

- `logic.ir_core` for immutable canonical data, identities, provenance,
  diagnostics, claims, evidence, artifacts, backend protocols, and result
  authority;
- `logic.admissibility.receipt`, `logic.admissibility.enforcement`, and
  `logic.admissibility.runtime` for request-bound decision receipts, one-use
  capabilities, live revalidation, and atomic capability consumption;
- `logic.security_ir` for security declarations, transition/deontic/verification
  views, typed results, and policy separation;
- `logic.security_models.crypto_exchange` for existing wallet/exchange claims,
  Z3/CVC5 runners, counterexamples, proof receipts, evidence gates, monitors,
  and release-gate patterns;
- `logic.software_contracts` for bounded CID-addressed AST, callable-contract,
  effect, provenance, registry, and cache records where their semantics fit;
- the existing logic backend registry, CVC5/Z3 compilers, CEC/TDFOL tools, and
  formalization contracts; and
- existing knowledge-graph storage and bounded query infrastructure.

Crypto IR must not create a third proof-result hierarchy, a second CAS, or a
parallel generic software-contract AST. Chain adapters add deployment,
asset-flow, VM, and transaction semantics that those generic layers do not
currently model.

### 2.3 Gaps

The current code does not provide:

- a chain-neutral wallet/transaction/deployed-code IR;
- contract source, ABI/IDL, deployed bytecode/program, compiler, build, proxy,
  upgrade, or code-epoch acquisition;
- EVM bytecode, Solana SBF/Anchor, Bitcoin Script/Tapscript/Miniscript, or XRPL
  native-ledger semantic frontends;
- chain-aware proof obligations and security release decisions;
- official OFAC SDN snapshot ingestion and digital-currency identifier parsing;
- sanctions-list revision/freshness semantics;
- a provenance-preserving blockchain flow knowledge graph;
- sound distinction between an exact designation, entity/ownership evidence,
  indirect flow exposure, and heuristic association; or
- a transaction pre-sign/pre-broadcast decision gate.

The existing `logic/zkp/eth_integration.py` signing/broadcast helper is an
identified enforcement hotspot: its transaction path must be disabled by
default or routed through the new exact-candidate gate before any production
cutover. Crypto IR does not make that module a custody service.

## 3. Scope and non-goals

### Included

- Ethereum and other approved EVM networks, including World Chain.
- Solana programs and program-owned state.
- Bitcoin Script, Tapscript, Miniscript/descriptors, PSBT policy, and UTXO
  spending conditions.
- XRPL/Ripple native transaction and ledger-object state machines; Hooks only
  on networks where capability evidence proves they exist; Ripple EVM
  sidechains reuse the EVM adapter.
- World ID/Worldcoin verifier, nullifier, bridge, upgrade, and domain-binding
  checks, while keeping World ID, World Chain, and WLD distinct.
- Exact SDN digital-currency-address screening, evidence-backed entity and
  ownership policy, risk-based indirect-flow analysis, ongoing re-screening,
  historical lookback, explainable holds/review, and immutable audit receipts.
- Static analysis, deterministic compilation, theorem proving, bounded
  simulation/monitoring, counterexample generation, and differential checks.
- Offline fixtures by default and explicitly approved network integration
  tests.

### Excluded unless a later reviewed objective adds authority

- Private-key, seed-phrase, HSM, MPC, or custodial key management.
- Signing, user approval, transaction submission, or broadcast inside
  `ipfs_datasets_py` processors.
- Automatic filing with OFAC, law enforcement, or another external party.
- A legal conclusion based solely on graph distance, taint, fuzzy matching,
  model output, or a theorem about incomplete facts.
- Treating every address that once received funds from a listed address as a
  blocked person.
- Treating an explorer's “verified source” badge as source/bytecode equality.
- Treating a static analyzer, GraphRAG answer, runtime monitor, ZK commitment,
  or satisfiability result as a theorem proof.
- A universal claim that a contract is “secure.” The strongest permissible
  claim is that named obligations were proved under named assumptions for an
  exact code epoch and toolchain.
- Silent dependency installation, ambient credentials, unbounded RPC scans,
  unrestricted explorer access, or import-time network activity.

## 4. Architecture and authority boundaries

### 4.1 Five distinct layers

1. **Declaration** — wallet/account, unsigned intent, deployed artifact,
   policy, and proof-obligation declarations.
2. **Observation** — chain, source, list, graph, simulation, and runtime facts
   bound to position, finality, time, and completeness.
3. **Evidence and assumptions** — source references, artifact digests,
   coverage, capability probes, trust decisions, and explicit unknowns.
4. **Analysis results** — static findings, monitor results, satisfiability,
   theorem proof/disproof, counterexamples, and inconclusive states.
5. **Authorization decision** — a separate policy result bound to the exact
   transaction candidate and every input above.

No layer can manufacture authority belonging to a later layer. In particular,
an observation or high risk score cannot be relabeled a designation, and a
proof result cannot itself authorize a transaction.

### 4.2 Identity and provenance

Every authoritative record must bind:

- schema and canonicalization version;
- repository and implementation revision where locally produced;
- chain namespace, network, chain/genesis identity, and block/slot/ledger
  reference;
- finality and reorg/retraction status;
- normalized account/address plus the original representation;
- raw artifact digest/CID and acquisition request/response metadata;
- parser/analyzer/compiler/backend/toolchain identities;
- policy, jurisdiction, list, graph, and model revisions;
- assumptions, unsupported semantics, coverage frontier, and resource bounds;
- observed/effective/expiry times; and
- a deterministic content identity.

Mutable facts such as proxy implementations, Solana upgrade authorities, list
membership, graph edges, and chain finality are modeled as time-bounded epochs.
Changing an epoch invalidates dependent decisions.

### 4.3 Core Crypto IR records

The reviewed schema must cover:

- `ChainIdentity`, `AccountIdentity`, `WalletDescriptor`, `AssetIdentity`,
  `ExactAmount`, and `LedgerCoordinate`;
- `UnsignedTransactionIntent`, `SerializedTransactionCandidate`,
  `SignerRequirement`, `CallIntent`, `TransferIntent`, `ApprovalIntent`,
  `FeeIntent`, `UtxoInput`, and `ExpectedEffect`;
- `ContractArtifact`, `DeployedInstance`, `CodeEpoch`, `BuildManifest`,
  `SourceManifest`, `InterfaceManifest`, `ProxyBinding`,
  `UpgradeAuthority`, `ProgramInstruction`, and `SpendingCondition`;
- `ObservedTransaction`, `ObservedFlow`, `ContractCallObservation`,
  `StateObservation`, and `CompletenessReceipt`;
- `SanctionsSnapshot`, `DesignationRecord`, `DigitalCurrencyIdentifier`,
  `OwnershipEvidence`, `GraphSnapshot`, and `ExposurePath`;
- `SecurityClaim`, `ComplianceClaim`, `ProofObligation`,
  `AnalysisAttempt`, `Finding`, `Counterexample`, and `AnalysisReceipt`; and
- `TransactionPolicyRequest`, `TransactionPolicyDecision`, and
  `EnforcementReceipt`.

Collections declare whether order, multiplicity, and duplicates are semantic.
Amounts never use binary floats. Unknown extensions fail closed until a schema
policy explicitly accepts them.

## 5. Smart-contract acquisition and normalization

### 5.1 Shared processor contract

`processors.smart_contracts` provides bounded, dependency-injected protocols:

- artifact/provider capability discovery;
- exact-chain code and state acquisition;
- source, ABI/IDL, metadata, build, and verification-document acquisition;
- archive/CAS storage and deterministic manifests;
- parsing and normalization into Crypto IR;
- checkpoint, finality, code-epoch, and reorg handling;
- cancellation, deadlines, item/request/byte/depth limits; and
- structured unavailable, partial, unsupported, inconsistent, and poisoned
  results.

Endpoints are allowlisted, HTTPS-first, SSRF resistant, redirect/DNS checked,
rate limited, and credential values remain injected secrets. Provider
disagreement is preserved; it is not resolved by choosing the most permissive
response.

### 5.2 Source-to-deployment equivalence

A source artifact qualifies only when a reproducible manifest binds:

- exact source bytes and file paths;
- compiler and linker versions;
- target VM/architecture and optimization settings;
- libraries, metadata hash policy, feature flags, and dependencies;
- creation/runtime bytecode or program binary;
- constructor/initialization parameters where required;
- deployment transaction and code epoch; and
- deterministic comparison rules including explicitly ignored metadata.

When reproduction is unavailable, source remains useful evidence but deployed
code is analyzed independently and the result stays `NOT_MODELED` or
`INCONCLUSIVE` where source correspondence matters.

### 5.3 Chain semantics

| Lane | Acquired artifacts | Required semantics | Critical hazards |
| --- | --- | --- | --- |
| EVM / Ethereum / World Chain | runtime and creation bytecode, verified/unverified source, ABI, compiler metadata, storage slots, call/trace/log evidence | Solidity/Vyper AST where present, opcodes, CFG/call graph, storage and calldata effects, EIP-1967/beacon/diamond/minimal proxies, code epochs | access control, reentrancy/callbacks, delegatecall, unchecked calls, upgrade capture, oracle/price, approval drain, arithmetic/precision, replay/domain, DoS |
| Solana | executable/program/program-data accounts, SBF ELF, loader state, Anchor IDL/source/build data, instructions/logs/accounts | loader and upgrade authority, signer/writable privileges, PDA/seed constraints, owner checks, CPI graph, inner instructions and account data flow | missing signer/owner checks, writable escalation, arbitrary CPI, account substitution, reinitialization, upgrade capture, lamport/token conservation |
| Bitcoin | scripts, redeem/witness scripts, descriptors/Miniscript, Tapscript leaves/control blocks, PSBT and UTXO context | stack/spending semantics, sighash commitments, timelocks, hashlocks, multisig/threshold paths, taproot commitment and policy equivalence | unintended spend path, weak sighash, timelock bypass, malleability/replay assumptions, hidden tapleaf, policy/descriptor mismatch |
| XRPL / Ripple | transactions, account flags, trust lines, escrows, checks, payment channels, offers, AMMs, NFT objects, Hooks only where supported | native state-machine transitions, tags/memos, sequence/ticket, signer list, reserve/issuer/freeze/clawback, ledger finality; EVM sidechain delegates to EVM lane | destination/tag confusion, issuer/trust-line ambiguity, freeze/clawback, partial payment, replay/sequence, signer quorum, unsupported Hooks claims |
| Worldcoin / World ID | World Chain verifier/proxy/bridge code, World ID configuration and proof-domain bindings | reuse EVM semantics; verify external nullifier/action/domain binding, proof consumer, bridge and upgrade assumptions | cross-action replay, nullifier misuse, wrong chain/domain, verifier/proxy upgrade, bridge trust, proof accepted as payment or identity authority |

## 6. Contract assurance and theorem proving

### 6.1 Obligation model

Common obligations include:

- authorization and least privilege;
- signer, account-owner, and writable-account constraints;
- conservation of native/token/UTXO value;
- no unauthorized mint, burn, transfer, allowance, freeze, clawback, or upgrade;
- replay resistance and domain/network/nonce/sequence binding;
- callback/reentrancy and external-call safety;
- arithmetic, precision, overflow, rounding, and slippage bounds;
- proxy/implementation/upgrade invariants;
- oracle freshness and manipulation assumptions;
- workflow/finality/expiry/timelock safety;
- resource-exhaustion and denial-of-service bounds; and
- transaction effects matching the displayed user intent.

Chain rule packs instantiate these obligations only where the frontend has
semantic coverage. Missing semantics produce explicit unsupported or
inconclusive results.

### 6.2 Analysis portfolio

The portfolio may combine:

- deterministic lint and pattern checks;
- generic software-contract AST/call/effect evidence;
- chain-native bytecode/program/script semantics;
- transaction simulation and fork/testnet traces;
- symbolic execution and mutation-generated counterexamples;
- CVC5 and Z3 differential SMT checks;
- CEC/TDFOL/deontic reasoning for policy and workflow obligations;
- optional protocol/temporal proof tools when capability probes pass; and
- runtime monitors that validate only the traces they observed.

Backend discovery is side-effect free. A backend must actually execute before
its result receives backend authority. Timeouts, unavailable solvers,
unsupported theories, incomplete models, disagreements, and resource-bound
terminations remain explicit.

The present security formalizer can emit an opaque
`security_verification_condition` JSON family that existing solver compilers
do not execute. Each Crypto IR obligation therefore needs a reviewed,
soundness-documented lowering to a logic family that the selected backend
actually supports, such as bounded SMT-LIB, Datalog, propositional/FOL, or an
explicit temporal fragment. Opaque JSON, prose, retrieval output, and
unsupported theories return `NOT_MODELED` or `UNKNOWN`; they are never
submitted or reported as proof.

### 6.3 Verdicts

Analysis results and policy decisions use different closed vocabularies.

Analysis authority:

- `PROVED` — the named obligation was proved for the exact model and
  assumptions by an executed proof backend;
- `DISPROVED` — a valid counterexample or proof of negation exists;
- `SATISFIABLE` / `UNSATISFIABLE` — solver answers to a model query, not
  automatically a security proof;
- `MONITOR_SATISFIED` / `MONITOR_VIOLATED` — bounded trace result only;
- `NOT_MODELED`, `UNKNOWN`, `TIMEOUT`, `UNAVAILABLE`, or `ERROR`.

Transaction policy:

- `ALLOW` — all policy-required evidence and obligations pass and are fresh;
- `DENY` — a hard prohibition or disqualifying security result applies;
- `REVIEW` — a configured risk or ambiguity requires human authority;
- `INCONCLUSIVE` — required evidence or capability is missing;
- `STALE` — a formerly usable decision has expired or an input epoch changed;
- `ERROR` — the evaluation did not complete safely.

For production signing/broadcast, every result other than a current `ALLOW`
blocks automated execution.

## 7. Sanctions and illicit-flow risk controls

### 7.1 Official-list acquisition

The first authoritative source is the U.S. Treasury OFAC Sanctions List
Service:

- `https://ofac.treasury.gov/sanctions-list-service`
- `https://sanctionslist.ofac.treas.gov/`
- OFAC FAQ 563 for “Digital Currency Address - <symbol>” identifiers:
  `https://ofac.treasury.gov/faqs/563`
- OFAC virtual-currency compliance guidance:
  `https://ofac.treasury.gov/system/files/126/virtual_currency_guidance_brochure.pdf`
- OFAC revised 50 Percent Rule guidance:
  `https://ofac.treasury.gov/media/6186/download?inline=`

Every import stores the untouched source bytes, source URL, transport and
published hash/signature evidence where available, retrieval time, publication
or effective time, parser/schema version, entry counts, diagnostics, and a
snapshot CID. Updates are append-only. Rollback, truncation, malformed data,
unknown schema changes, suspicious count drops, and freshness expiry prevent a
new `ALLOW`.

The design supports additional reviewed sanctions lists later. SDN and
non-SDN lists are not interchangeable, and each program's prohibitions,
licenses, and effective periods remain typed.

### 7.2 Match-authority levels

The system must never collapse these levels:

1. **Exact listed digital-currency identifier** — chain/currency-qualified
   canonical address or identifier from an authoritative list snapshot.
2. **Named designated party** — source-backed list identity or high-quality
   reviewed entity resolution.
3. **Owned entity** — reviewed ownership evidence evaluated under an approved
   ownership rule such as the applicable aggregate 50 Percent Rule.
4. **Direct transaction association** — a transaction directly involving a
   listed identifier or a party established by the earlier levels.
5. **Indirect flow exposure** — a provenance-preserving path through observed
   transactions under configured depth, time, amount, asset, finality, and
   completeness constraints.
6. **Heuristic association** — clustering, shared-wallet, bridge, mixer,
   exchange, behavioral, GraphRAG, or fuzzy evidence that may prioritize
   review but cannot create designation authority.

Exact digital-currency identifiers use chain-specific validation. Ethereum
case/checksum handling, Bitcoin network/script identity, Solana base58/account
type, XRPL classic/X-address and destination tags, and World Chain/EVM chain
identity must not collide or silently coerce.

### 7.3 Flow knowledge graph

The canonical graph contains typed nodes for:

- chain/network and ledger positions;
- address/account/script/wallet claims;
- transactions, UTXOs, inputs, outputs, transfers, calls, programs, contracts,
  bridges, pools, mixers, and exchanges;
- assets and exact amounts;
- list snapshots, designations, entities, aliases, ownership evidence,
  licenses, and policy revisions; and
- analysis, completeness, and retraction receipts.

Edges carry source identity, amount where meaningful, asset, direction,
timestamp, ledger position, finality, validity interval, confidence,
derivation method, and retraction status. Observed-address graphs and
asserted-entity graphs remain separate.

Traversal is bounded by explicit depth, time window, asset, amount/ratio,
provider coverage, finality, and resource budgets. It models UTXO and
account-based ledgers separately, preserves CoinJoin/mixer/pool/exchange/bridge
ambiguity, and never assumes that all inflows to or outflows from a service
belong to the same customer.

### 7.4 Compliance logic

Representative predicates:

```text
ListedIdentifier(snapshot, chain, address, designation)
DesignatedParty(snapshot, party)
OwnedAtLeast(policy, blocked_owners, entity, percentage, time)
DirectCounterparty(intent, party_or_address)
ObservedFlow(graph, source, destination, asset, amount, time, finality)
BoundedExposure(graph, origin, listed_identifier, path_policy, path)
EvidenceFresh(snapshot, graph, code_epoch, policy, now)
ContractObligationsSatisfied(intent, code_epoch, required_obligations)
RequiresReview(intent, reason)
Forbidden(intent, legal_policy, reason)
```

Theorem provers establish consequences of explicit facts and policy rules.
They cannot prove that no undiscovered connection exists beyond a graph's
coverage frontier. A negative conclusion is valid only for the bound snapshot,
providers, range, assets, path policy, and completeness receipt.

Default engineering behavior:

- an applicable exact listed address or established blocked party is a hard
  `DENY`;
- evidence-backed ownership rules are evaluated only under an approved legal
  policy;
- indirect flow exposure is `REVIEW` or `DENY` according to a reviewed,
  versioned risk policy, never automatically called a designation;
- fuzzy names, clustering, shared infrastructure, and other heuristics cannot
  produce `ALLOW` or a blocked-party conclusion;
- missing, stale, inconsistent, reorged, or incomplete critical evidence is
  fail-closed; and
- a license or exception is accepted only as a scoped, effective, signed
  policy artifact with separate human authority.

## 8. Transaction enforcement

### 8.1 Two-phase gate

```text
construct unsigned intent
        │
        ▼
normalize exact candidate + expected effects
        │
        ▼
contract/code-epoch acquisition and assurance
        │
        ├───────────────┐
        ▼               ▼
direct sanctions     bounded flow/KG
and ownership        exposure analysis
        └───────┬───────┘
                ▼
deterministic policy combination
                │
       ALLOW / DENY / REVIEW /
       INCONCLUSIVE / STALE / ERROR
                │
                ▼
pre-sign revalidation
                │
                ▼
external custody signer
                │
                ▼
pre-broadcast revalidation
                │
                ▼
external broadcaster
```

The gate receipt binds:

- canonical unsigned intent and exact serialized candidate digest;
- chain/network, sender, destination, method/instruction/script, asset, amount,
  fee, nonce/sequence, UTXO set, signer requirements, and expected effects;
- deployed code epoch, proxy implementation, upgrade authority, and simulator
  state;
- sanctions snapshot, graph snapshot, ownership evidence, and path policy;
- security/compliance models, assumptions, obligations, results, and
  counterexamples;
- policy/jurisdiction/license revisions;
- capability probes and freshness/expiry;
- decision, reasons, evidence paths, and a deterministic receipt identity.

Any material change requires a new decision. Receipts are single-candidate,
short-lived, replay protected, and cannot be transferred between networks,
accounts, methods, nonces, UTXOs, code epochs, or policies.

The gate specializes the existing admissibility stack: it issues a
request-bound, short-lived one-use capability only after an `ALLOW`, validates
all live facts again at consumption, and consumes authorization atomically.
Signing and broadcast adapters accept that capability rather than a bare
boolean or caller-supplied “approved” flag. The guarded cutover must inventory
and either retrofit or disable every pre-existing sign/broadcast entry point,
including `logic/zkp/eth_integration.py`.

### 8.2 Overrides and operations

There is no universal allowlist bypass. A human action can:

- reject a transaction;
- keep it on hold;
- request more evidence;
- acknowledge a false-positive heuristic;
- attach a scoped license/authorization; or
- authorize a narrowly defined review outcome if policy permits.

Every action requires named authority, reason, scope, expiry, separation of
duties where configured, and an immutable audit receipt. It cannot convert a
failed proof into a proof or make stale evidence fresh.

Holding, rejecting, blocking property, reporting, unblocking, and recordkeeping
are separate workflows. The library produces evidence and workflow states; it
does not silently perform external reporting or move funds.

## 9. Security, privacy, and supply-chain controls

- Treat RPC, explorer, source, ABI/IDL, list, model, and graph data as
  untrusted.
- Require strict schemas, finite numbers, bounded strings/collections,
  deterministic ordering, and decompression/archive limits.
- Sandbox parsers and analyzers where practical; source retrieval never
  executes builds by default.
- Pin approved compilers/analyzers and record hashes, versions, flags, and
  capability probes.
- Redact credentials, KYC data, internal labels, and sensitive evidence from
  logs and model prompts.
- Separate public-chain observations from customer/entity/KYC graphs with
  explicit access control and retention.
- Never send transaction candidates, KYC, sanctions investigations, or
  nonpublic source to an external model without a separately approved data
  policy.
- Record provider split views, reorgs, poisoning, schema drift, and quorum
  disagreement rather than hiding them.
- Cache only content-bound results and invalidate transitively on any source,
  code, graph, list, policy, assumption, capability, or toolchain change.

## 10. Parallel execution plan

The objective heap is the durable dependency graph. Bundles own disjoint
paths so work can run safely in parallel.

### Wave 0 — baseline and policy

- baseline/source/interface inventory;
- architecture, threat, soundness, and decision-authority ADR.

### Wave 1 — four parallel foundations

- Crypto IR kernel and schema;
- smart-contract processor protocols and provenance;
- security-obligation/formalization contracts; and
- sanctions snapshot ingestion and exact identifiers.

### Wave 2 — chain and graph lanes

After the shared contracts freeze, EVM/World Chain, Solana, Bitcoin, XRPL, and
Worldcoin specialize disjoint paths in parallel. Sanctions entity/ownership,
flow-graph, and exposure lanes run alongside them.

### Wave 3 — assurance convergence

Chain semantics feed common and chain-specific obligations, proof backends,
simulation, counterexamples, result policy, and contract release decisions.
Compliance facts feed theorem/policy compilation and explainable decisions.

### Wave 4 — enforcement

The transaction preflight API, custody-wallet SPI, two-phase freshness checks,
audit/override workflow, and API/CLI/MCP surfaces integrate only after result
authority and compliance policy are stable.

### Wave 5 — release

Adversarial corpus, conformance, fuzz/property tests, performance/resource
measurement, upstream reconciliation, privacy/security/legal review, staged
shadow rollout, and the final release gate.

Initial runtime admission is two implementation shards because other
supervisors are active on this host. The plan permits four or more logical
lanes, but concurrency increases only after measured resource and merge
pressure support it.

## 11. Test and evidence strategy

### Offline mandatory suites

- canonical identity, schema migration, mutation resistance, round trip, and
  unknown-extension tests;
- address/network/tag/checksum and exact-amount property tests;
- malicious archive, endpoint, redirect, DNS, decompression, source, ABI/IDL,
  parser, bytecode, and list fixtures;
- source/build/deployed-code match and mismatch vectors;
- EVM proxy upgrades, reentrancy, delegatecall, approval drain, oracle, and
  calldata substitution;
- Solana signer/writable/owner/PDA/CPI/reinitialization/upgrade attacks;
- Bitcoin alternative spend paths, witness/control-block, sighash, timelock,
  and descriptor mismatch;
- XRPL tag, issuer, partial-payment, freeze/clawback, ticket/sequence, signer,
  and ledger-state cases;
- World ID domain/nullifier/replay/verifier-upgrade cases;
- exact SDN address hits, delisting/effective-time, source rollback/truncation,
  parser drift, stale snapshots, and false-network matches;
- direct, one-hop, multi-hop, UTXO, pool, CoinJoin, mixer, exchange, bridge,
  peel-chain, change, dust, reorg, and incomplete-coverage graph cases;
- theorem proof/disproof/unknown/timeout/unavailable/disagreement and result
  authority misuse;
- transaction substitution, nonce/UTXO change, proxy upgrade, list update,
  graph update, reorg, stale receipt, split RPC view, and signer/broadcast
  time-of-check/time-of-use races; and
- no-network/no-install/no-secret/no-sign/no-broadcast import and API tests.

### Opt-in integration suites

- pinned public RPC/explorer/list endpoints with strict egress and byte limits;
- reproducible compiler/analyzer containers;
- local forks, devnets, and testnets with non-custodial dummy transactions;
- historical OFAC delta/replay snapshots; and
- differential providers and proof backends.

### Release evidence

The release gate requires:

- zero false `ALLOW` for every hard-deny fixture;
- zero `ALLOW` with stale or missing critical evidence;
- zero promotion of heuristic, monitor, satisfiability, model, or graph output
  to theorem/designation authority;
- full required-language and chain-semantic coverage or an explicit
  fail-closed unsupported result;
- deterministic identities and reproducible receipts across processes;
- no secret, signing, broadcast, or external-reporting path in processors;
- measured latency, memory, storage, provider, proof, and graph budgets;
- successful rollback and cache invalidation drills; and
- named security, compliance/legal, privacy, operations, and release owners.

## 12. Rollout

1. **Observe** — ingest and normalize only; compare artifacts and list
   snapshots; no transaction decisions consumed.
2. **Shadow** — emit security/compliance decisions beside existing behavior;
   never affect signing.
3. **Review-only** — holds and review queues consume receipts, but automated
   signing remains disabled.
4. **Direct-list enforcement** — enable hard denial for exact authoritative
   identifiers under a reviewed jurisdiction/list policy.
5. **Contract enforcement** — enable only obligation sets with adequate
   coverage, fresh proof evidence, and approved policy.
6. **Indirect-flow enforcement** — promote one bounded, measured risk policy at
   a time after false-positive/negative, mixer/exchange/bridge, and legal review.
7. **Broader automatic use** — only after separate current-tree evaluation,
   production telemetry, recovery drills, and explicit authorization.

Any stale binding, provider/list/capability loss, proof disagreement, current
tree regression, resource violation, or audit failure returns the affected
behavior to shadow or fail-closed review. Rollback never deletes audit
evidence.

## 13. Definition of done

The program is complete only when every child objective has fresh,
current-tree evidence and:

- Crypto IR is stable, immutable, content addressed, provenance complete, and
  compatible with `ir_core`, Security IR, software-contract IR, wallet records,
  and the knowledge graph;
- all five chain families produce bounded, chain-correct artifacts and
  semantics with explicit coverage;
- contract decisions bind exact deployed code epochs and never overstate proof;
- official sanctions snapshots and direct digital-currency identifiers are
  reproducible, fresh, and chain correct;
- indirect flow results are explainable, bounded, reorg aware, uncertainty
  preserving, and distinct from designation authority;
- a transaction cannot obtain an automated `ALLOW` when a required security or
  compliance result is denied, review-only, inconclusive, stale, or erroneous;
- pre-sign and pre-broadcast checks bind the exact transaction candidate and
  invalidate on every material change;
- processors remain non-custodial and read-only;
- CLI/MCP cannot bypass policy, freshness, or receipt checks; and
- shadow, recovery, rollback, security, privacy, compliance/legal, and release
  reviews pass with durable evidence.

## 14. Solidity CPT Top-10 GraphRAG and formal-learning expansion

### 14.1 Outcome and source pin

Add a provenance-bound Solidity corpus pipeline for the Hugging Face dataset
[`samscrack/solidity-cpt-top10-quality`](https://huggingface.co/datasets/samscrack/solidity-cpt-top10-quality).
The reviewed source profile is:

- immutable dataset revision
  `23c0b2f279fa29c6b425543fe9c8bf41d574d028`;
- one `train` split containing 23,471 Solidity source rows;
- LFS object `top10.parquet`, 109,124,886 bytes, SHA-256
  `185f1ac548f0df10a8166c8a2a10610bcc3422ce77f51567c3de86ddc8f5e455`;
- ordered row fields `text`, `source`, `address`, `name`, `compiler`,
  `license`, `path`, and `n_chars`; and
- a declared dataset-level CC BY 4.0 license plus per-row source-license
  metadata that may be different, absent, ambiguous, or more restrictive.

The source profile is verified again from observed Hub metadata before any row
is admitted. A moving branch, changed shard, row-count or schema drift,
truncation, unexpected compression expansion, or digest mismatch fails closed.
The name `top10` describes the dataset author's top-decile quality selection;
it is not an OWASP Top 10 label and is not evidence that a contract is secure.

The corpus provides Solidity syntax and source-distribution evidence. It does
not provide authoritative vulnerability labels, deployed-bytecode equality,
complete execution semantics, theorem proofs, or transaction permission.

### 14.2 Reuse and package boundaries

Use the reviewed CVEfixes Security IR implementation at
`ipfs_datasets_py` ref `origin/integration/cvesir-ipfs-accelerate`, commit
`3952dae8925e9f469632ed53eccf1678a924fd4e`, as the primary implementation
pattern. Reconcile or deliberately port its shared contracts before creating
new equivalents. In particular, reuse its immutable source profiles, strict
derived schemas, release policy, typed graph, bounded hybrid retrieval,
Security IR adapter, formalizer, leakage-safe evaluation, and deterministic
release staging. Reuse the current Intent IR rule that retrieved premises are
content-bound `context_only` assumptions with `proof_authority=False`.

Ownership is deliberately split:

```text
ipfs_datasets_py/ipfs_datasets_py/
├── processors/smart_contracts/solidity/
│   ├── __init__.py
│   ├── models.py
│   └── parser.py
├── logic/security_ir/solidity_cpt_top10/
│   ├── __init__.py
│   ├── source_snapshot.py
│   ├── hf_source.py
│   ├── schemas.py
│   ├── release_policy.py
│   ├── vocabulary.py
│   ├── projector.py
│   ├── graph.py
│   ├── retrieval.py
│   ├── partitions.py
│   ├── adapter.py
│   ├── formalize.py
│   ├── training_records.py
│   ├── training.py
│   ├── evaluation.py
│   └── hf_release.py
└── logic/crypto_ir/adapters/
    └── solidity_cpt_top10.py
```

`processors.smart_contracts.solidity` is an inert, bounded implementation of
the existing contract-parser protocol. The Security IR package owns corpus
ingestion, graph projection, retrieval, candidate formalization, learning
records, and evaluation. The narrow Crypto IR bridge may propose reviewed
security rules and proof obligations with explicit semantic prerequisites; it
cannot directly decide contract safety or authorize a wallet transaction.

### 14.3 Bounded acquisition, provenance, and license policy

The default path consumes a previously downloaded, digest-verified local
Parquet file or a bounded injected stream. Imports perform no network access,
credential discovery, dependency installation, source execution, compilation,
prompt interpretation, publication, or upload.

Each admitted row receives:

- the exact dataset, revision, shard, row, and producer-configuration identity;
- a raw-source digest and CID, with source bodies stored separately from graph
  nodes and release manifests;
- normalized but non-authoritative source, repository, address, compiler,
  license, path, and size metadata;
- strict byte, character, token, AST-node, nesting, import, and time bounds;
- explicit quarantine diagnostics for malformed encodings, duplicate fields,
  unsafe paths, oversize values, parser failure, and suspicious content; and
- a license-review result controlling internal use, derived release, raw-source
  redistribution, and model/checkpoint publication independently.

An Etherscan address or “verified source” observation remains source metadata;
it does not establish equality with deployed runtime bytecode. Rows whose
underlying license is absent or ambiguous default to internal research use and
source-free derived release only until a reviewer grants narrower authority.

### 14.4 Solidity projection and contract-security graph

The parser produces deterministic, source-spanned facts for contracts,
libraries, interfaces, inheritance, imports, functions, constructors,
modifiers, state variables, events, errors, calls, state reads/writes,
authorization guards, value effects, control flow, assembly regions, and
unsupported syntax. It never executes Solidity, resolves imports over the
network, trusts the declared compiler, or silently treats source semantics as
deployed EVM semantics.

The versioned graph contains content-addressed nodes for:

- dataset snapshots, shards, rows, source units, repositories, source
  licenses, compiler declarations, and unverified deployment-address hints;
- contracts, libraries, interfaces, functions, modifiers, variables, events,
  errors, call sites, state accesses, and effect summaries;
- typed security concepts, candidate claims, assumptions, mitigations,
  proof obligations, and exact formal views; and
- producer configurations, graph partitions, evaluation cases, and receipts.

Typed edges cover `contains`, `declares`, `inherits`, `imports`, `calls`,
`reads`, `writes`, `emits`, `guards`, `may_effect`, `derived_from`,
`grounded_in`, `has_license`, `has_compiler`, `candidate_for`, and explicit
structural or semantic similarity. Approximate similarity is always labeled
non-authoritative. Unknown node, edge, schema, or authority extensions fail
closed.

### 14.5 Retrieval and accelerator integration

Build a deterministic hybrid retriever over lexical, embedding, and bounded
graph-neighborhood scores. Its embedding dependency is the existing injected
`EmbeddingAcceleratorPort` contract; accelerator/model selection remains
outside the corpus package. Every index root binds:

- source, graph, ontology, partition, shard, and projection CIDs;
- exact embedding model, revision, tokenizer, dimensions, normalization, and
  accelerator configuration;
- lexical/vector/graph weights and all node, byte, hop, result, and time
  limits; and
- the release and authority policy under which the index was built.

Queries name exactly one allowed partition and authority scope. Retrieval
cannot cross a held-out, source-family, adversarial, license, or graph-snapshot
fence. Every hit cites its source and graph path and is returned as context or
a candidate only. Rehash-on-load, stale-index, missing-assignment,
cross-partition, grant-like metadata, and model/config mismatch checks fail
closed.

### 14.6 Formal-learning records and training

Keep four non-interchangeable streams:

1. license-admitted raw continued-pretraining tokens;
2. source-to-Security-IR and source-to-proof-obligation instruction records;
3. formal formulas, counterexamples, and proof-attempt records whose labels
   bind exact executed prover receipts; and
4. evaluation-only, adversarial, mutated, vulnerable/fixed, and held-out cases.

Before any split, group exact and near duplicates by normalized content,
repository/source family, path history, address, fork/import lineage, and
generated-code family. Assign connected groups—not individual rows—to
deterministic train, validation, test, held-out-domain, held-out-revision, and
adversarial partitions. Retrieval for evaluation is fenced to the permitted
partition snapshot.

Formalization may learn to retrieve evidence, construct a typed Security IR
candidate, propose an assumption, rank a rule, or generate a proof obligation.
The dataset's quality score is never converted into a safety label. Missing
labels remain unlabeled rather than negative. A theorem label exists only when
an exact supported lowering was executed by the named backend and its receipt
was validated; solver answers, proof traces, and evaluation labels remain
separate from input features unless the named training objective explicitly
uses them as targets.

The backend-neutral training runner is offline and dry-run safe by default.
An opt-in run binds the base model and revision, tokenizer, optimizer,
hyperparameters, random seed, partitions, source and graph CIDs, license
policy, hardware/capability profile, budgets, checkpoints, logs, and terminal
status. It emits candidate formalization authority only. Model download, a
full GPU run, external tracking, checkpoint upload, and publication require
separate operator authority, credentials, budget, and license approval.

### 14.7 Evaluation and promotion gates

Mandatory offline evaluation measures:

- source-pin, schema, license, CID, parser, ontology, graph, and index
  integrity;
- exact/near-duplicate and source-family leakage, which must be zero;
- retrieval recall/precision/MRR, graph-path validity, partition isolation,
  attribution coverage, latency, and memory;
- Security IR schema validity, source-span grounding, unsupported-semantics
  abstention, obligation coverage, and executable-lowering rate;
- proof, disproof, unknown, timeout, unavailable, and backend-disagreement
  rates against held-out and mutation-generated controls;
- calibration and abstention under unsupported syntax, ambiguous licenses,
  poisoned text, prompt-like content, compiler mismatch, source/deployment
  mismatch, and graph/index corruption; and
- a cross-layer authority test proving that corpus quality, GraphRAG score,
  model confidence, SAT, simulation, or an unexecuted formal candidate cannot
  become theorem authority, a contract-safety `ALLOW`, or wallet permission.

Any CVEfixes, OWASP, CWE, SWC, SCSVS, EthTrust, exploit, or patch corpus used
for labels or controls needs its own pinned provenance, license admission, and
leakage group. Nearest-neighbor similarity never transfers a vulnerability or
safety label.

Release artifacts include deterministic data/model cards, source and
derivation manifests, evaluation receipts, known limitations, rollback
instructions, and license exclusions. Raw sources or learned weights are not
uploaded by the supervisor. The first integration is observation/shadow only:
retrieval may help reviewers choose obligations, but the existing
exact-code-epoch contract gate consumes only independently validated proof and
policy receipts.

### 14.8 Parallel execution waves

- **Wave A — governance:** `CRYPTOIR-G710` pins the source, reusable contracts,
  authority, threat, license, and release policy.
- **Wave B — two parallel foundations:** `CRYPTOIR-G720` builds bounded source
  intake and canonical records while `CRYPTOIR-G730` builds the inert Solidity
  parser against offline fixtures.
- **Wave C — graph and partitioning:** `CRYPTOIR-G740` builds the typed graph;
  then `CRYPTOIR-G750` builds retrieval while `CRYPTOIR-G760` builds
  leakage-safe partitions and fences.
- **Wave D — formal learning:** `CRYPTOIR-G770` builds the Security IR/formal
  adapter and training records; `CRYPTOIR-G780` adds the bounded training
  runner and checkpoint receipts.
- **Wave E — assurance and release:** `CRYPTOIR-G790` runs held-out and
  adversarial evaluation; `CRYPTOIR-G800` adds the narrow Crypto IR bridge,
  deterministic release staging, conformance tests, and rollback docs.

The supervisor may schedule logically independent lanes in parallel, but its
shared `ipfs_datasets_py` resource claim remains the physical merge-safety
fence. That fence is not weakened merely to increase concurrency.
