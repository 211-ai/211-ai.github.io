# Multi-Chain Wallet Processor Migration and Improvement Plan

Status: approved for supervised implementation on the dedicated integration
branch `codex/wallet-processors-migration`.

Companion artifacts:

- Objective heap:
  [`WALLET_PROCESSORS_OBJECTIVES.md`](WALLET_PROCESSORS_OBJECTIVES.md)
- Executable task board:
  [`WALLET_PROCESSORS_TODO.md`](WALLET_PROCESSORS_TODO.md)
- Runtime state:
  `data/wallet_processor_migration/agent_supervisor/`

## 1. Outcome

Move reusable Worldcoin / World ID behavior out of `211-AI` and into
`ipfs_datasets_py.ipfs_datasets_py.processors.wallets.worldcoin`. Replace the
current `211-AI.wallet_interface.world_id` implementation with a deliberately
small compatibility and application-wiring wrapper.

Create a coherent public-ledger processor family in `ipfs_datasets_py`:

```text
ipfs_datasets_py/processors/wallets/
├── README.md
├── __init__.py
├── protocols.py
├── models.py
├── canonical.py
├── pipeline.py
├── checkpoints.py
├── finality.py
├── registry.py
├── storage.py
├── errors.py
├── providers/
│   ├── __init__.py
│   ├── http.py
│   ├── retry.py
│   └── rate_limit.py
├── adapters/
│   ├── __init__.py
│   ├── processor_protocol.py
│   └── data_wallet.py
├── worldcoin/
│   ├── __init__.py
│   ├── config.py
│   ├── idkit.py
│   ├── rp_signing.py
│   ├── verification.py
│   ├── bindings.py
│   ├── redaction.py
│   └── processor.py
├── xaman/
│   ├── __init__.py
│   ├── models.py
│   ├── payloads.py
│   ├── xrpl_client.py
│   └── processor.py
├── ethereum/
│   ├── __init__.py
│   ├── models.py
│   ├── rpc.py
│   ├── logs.py
│   ├── tokens.py
│   └── processor.py
├── bitcoin/
│   ├── __init__.py
│   ├── models.py
│   ├── rpc.py
│   ├── scripts.py
│   ├── utxo.py
│   └── processor.py
└── solana/
    ├── __init__.py
    ├── models.py
    ├── rpc.py
    ├── instructions.py
    ├── tokens.py
    └── processor.py
```

The first release is non-custodial and data-oriented. It ingests, normalizes,
checkpoints, and exports wallet and public-ledger data. It does not store
private keys, sign transactions, approve Xaman payloads, move funds, or claim
that an address belongs to a person merely because public-ledger activity was
observed.

## 2. Current-state findings

### 2.1 Worldcoin / World ID

Reusable protocol code currently lives in
`wallet_interface/world_id.py`. It includes:

- environment and secret-reference configuration;
- World ID relying-party request signing;
- Keccak/hash-to-field utilities;
- IDKit v3/v4 response validation and normalization;
- Developer Portal verification HTTP behavior;
- verification-response normalization; and
- recursive proof-payload redaction.

Application orchestration lives in `wallet_interface/app_service.py`, route
models and HTTP translation live in `wallet_interface/routes/world_id.py`, and
production checks live in `wallet_interface/ops.py`.

`ipfs_datasets_py.wallet` already contains `WorldIdBinding`, binding indexes,
proof-receipt generation, and snapshot behavior. That package is a
UCAN/encrypted human-data wallet domain, not a public-chain processor domain.
It remains supported. A narrow adapter will connect it to the new Worldcoin
processor; the new public-ledger hierarchy will not be placed under
`ipfs_datasets_py.wallet`.

### 2.2 Xaman

`ipfs_datasets_py` already contains substantial Xaman source/runtime trace
extraction, security IR adapters, assurance reports, proof models, fixtures,
and testnet verification workflows under
`logic/security_models/crypto_exchange` and `logic/security_ir/xaman`.
Those are analysis and assurance assets, not a production XRPL wallet data
processor.

The migration must preserve that distinction:

- reusable XRPL/Xaman payload and ledger normalization moves or is implemented
  under `processors/wallets/xaman`;
- formal-analysis and assurance reports stay under `logic`;
- the two layers share small typed projections, never import report-generation
  internals into the runtime processor; and
- legacy imports remain supported only where a documented deprecation window
  is required.

### 2.3 Processor protocol ambiguity

The repository currently has two generic processor shapes:

- `processors/protocol.py` uses `can_process(input_source)`; and
- `processors/core/protocol.py` plus `processors/core/registry.py` use
  `can_handle(ProcessingContext)`.

`processors/core/universal_processor.py` also references a separate registry
surface. The wallet implementation must not select one accidentally. It will
define domain protocols in `processors/wallets/protocols.py`, keep imports
lightweight, and expose exactly one reviewed adapter to the canonical generic
processor protocol after a protocol decision record is accepted.

## 3. Scope

### Included

- World ID configuration, signing, parsing, verification, redaction, binding
  projection, and World Chain wallet-ledger ingestion.
- Xaman payload/account data and XRPL public-ledger ingestion/export.
- Ethereum EOA and contract-account public activity, native transfers,
  receipts/logs, ERC-20, ERC-721, and ERC-1155 projections.
- Bitcoin address/script/transaction/UTXO public activity with explicit
  attribution limits.
- Solana account/signature/transaction/instruction, lamport, SPL token, and NFT
  projections.
- Wallet-centric and bounded ledger-range ingestion modes.
- Deterministic, resumable exports to JSONL and Parquet/Arrow-compatible
  datasets with provenance and schema versions.
- Offline fixtures by default, optional network integration tests, CLI/MCP
  adapters, documentation, metrics, and release migration.
- A thin `211-AI` wrapper and compatibility tests proving ownership has moved.

### Excluded from the first release

- Seed phrases, private keys, key derivation, custodial signing, remote signing,
  transaction approval, or fund movement.
- Mempool trading, MEV, tax determination, sanctions decisions, identity
  inference, eligibility decisions, or risk scoring.
- Full archival indexing of every supported ledger without bounded range,
  rate, storage, and retention controls.
- Treating provider responses as final without chain-specific finality rules.
- Treating Xaman security-assurance artifacts as proof of runtime correctness.
- Silent network access, ambient credentials, or automatic dependency
  installation.

## 4. Architecture principles

1. **One normalized envelope, chain-native payloads retained separately.**
   Cross-chain queries use stable common fields; lossless chain-specific fields
   live in versioned extension objects or content-addressed raw records.
2. **Integers at boundaries.** Native and token quantities are stored in base
   units as decimal strings or integers, never binary floats. Display decimals
   are derived.
3. **Provenance is mandatory.** Every record carries chain/network identity,
   provider kind, request/range identity, observed time, block/slot/ledger
   reference, schema version, and raw-payload digest when available.
4. **Idempotent ingestion.** Stable record IDs derive from chain identity and
   canonical on-chain coordinates, not provider pagination.
5. **Finality is a state, not a boolean.** Records distinguish observed,
   pending, safe/confirmed, finalized, orphaned/reverted, failed, and unknown
   states as the chain permits.
6. **Reorg-aware checkpoints.** Checkpoints include a block/slot/ledger anchor
   and hash. Resume validates the anchor and rewinds within a configured safety
   window on mismatch.
7. **Dependency injection at every I/O boundary.** Tests use fixtures and fake
   clocks/transports. Importing a package performs no network call.
8. **No secret material in datasets or logs.** Secret references may be
   configured; resolved values are never serialized, displayed in `repr`, or
   placed in exception text.
9. **Thin wrappers are measurable.** The final 211-AI World ID wrapper contains
   aliases, deprecation notices, application defaults, and adapters only. It
   contains no cryptographic, HTTP, parsing, redaction, or normalization
   implementation.
10. **Safe parallel ownership.** Shared contracts land before chain modules.
    After that gate, Worldcoin, Xaman, Ethereum, Bitcoin, and Solana own
    disjoint package paths and can execute in parallel.

## 5. Canonical domain contract

The exact names may be refined in the contract task, but the semantics are
fixed.

### 5.1 Protocols

```python
class WalletProcessor(Protocol):
    chain: ChainDescriptor

    def validate_address(self, address: str) -> NormalizedAddress: ...

    async def ingest_wallet(
        self,
        request: WalletIngestRequest,
    ) -> AsyncIterator[WalletRecordBatch]: ...

    async def ingest_ledger(
        self,
        request: LedgerIngestRequest,
    ) -> AsyncIterator[WalletRecordBatch]: ...

    async def export_wallet(
        self,
        request: WalletExportRequest,
        sink: WalletDatasetSink,
    ) -> ExportReceipt: ...
```

Supporting boundaries:

- `LedgerClient`: bounded, paginated reads and health/capability reporting.
- `WalletDatasetSource`: optional import of wallet-owned export files.
- `WalletDatasetSink`: streaming batches, checkpoint commits, and final
  manifests.
- `CheckpointStore`: compare-and-set checkpoint writes.
- `Clock`, `RetryPolicy`, and `RateLimiter`: injectable operational controls.
- `RawPayloadStore`: optional, explicit, content-addressed lossless storage.

Every method accepts a cancellation/deadline budget through its request or
context. Implementations do not hide unbounded retries.

### 5.2 Normalized records

Core records:

- `ChainDescriptor`: namespace, network, genesis/chain identifier, native
  asset.
- `NormalizedAddress`: original value, canonical value, address/script/account
  kind, validation status.
- `LedgerPosition`: height/slot/ledger index, hash, transaction index, event or
  instruction index.
- `TransactionRecord`: transaction identity, participants when knowable, fee,
  status, finality, time, position, provenance.
- `TransferRecord`: asset identity, source, destination, base-unit quantity,
  transfer kind, transaction/event coordinates.
- `BalanceSnapshot`: address, asset, base-unit amount, position, finality.
- `AssetRecord`: native/token/NFT identity plus chain-native metadata.
- `WalletSnapshot`: requested account set, balances, checkpoint, export
  manifest reference.
- `Checkpoint`: request scope, cursor, anchor hash, safety depth, source
  identity, compare-and-set revision.
- `ExportManifest` and `ExportReceipt`: schema versions, partitions, counts,
  min/max positions, digests, checkpoints, warnings, and partial/final status.

Required common fields:

```text
schema_version
record_id
record_type
chain_namespace
network
chain_id
observed_at
ledger_position
finality
source
raw_payload_digest?
extensions
```

### 5.3 Chain namespaces

Use CAIP-compatible identities where practical:

- Ethereum and World Chain: `eip155:<chain-id>`.
- Bitcoin: a reviewed Bitcoin namespace plus network/genesis binding; never
  infer network only from a user-supplied address.
- Solana: cluster/genesis binding.
- XRPL: network identifier plus validated-ledger identity.
- World ID proof records use a protocol namespace distinct from World Chain
  ledger records.

The same human-readable address on two networks is never the same internal
wallet identity.

## 6. Chain-specific behavior

| Processor | Wallet ingestion | Public-ledger ingestion | Finality / reorg rule | Important limits |
| --- | --- | --- | --- | --- |
| Worldcoin | IDKit proof metadata, RP verification result, redacted binding projection | World Chain address activity through the Ethereum/EVM base | EVM safe/finalized tags or configured confirmations | Proof verification is not wallet ownership, eligibility, or payment authorization |
| Xaman / XRPL | Xaman payload metadata and account transactions | Validated ledger/account transaction pages | `validated=true`, ledger hash/index continuity | Never approve/sign payloads; issued currencies require issuer + currency identity |
| Ethereum | Account history, balances, receipts/logs, token transfers | Block/range, log, trace only when provider declares capability | pending/latest/safe/finalized plus hash-anchored rewind | Contract-internal value transfers need trace capability and must be labeled incomplete otherwise |
| Bitcoin | Address/script transactions, UTXOs, balances | Block/range and transaction inputs/outputs | confirmation depth and chain-tip hash rewind | Inputs consume UTXOs, not account balances; change/ownership clustering is not asserted |
| Solana | Signatures, transactions, account/token balances | Slot/range where RPC capability permits | processed/confirmed/finalized plus blockhash/slot rewind | Address lookup tables, versioned messages, inner instructions, and failed txs must remain distinguishable |

## 7. Ingest and export flows

### 7.1 Wallet-centric ingestion

1. Validate and normalize the requested address/account and network.
2. Resolve a declared provider capability; fail before I/O when unavailable.
3. Load the checkpoint for the exact chain, network, address set, record kinds,
   provider family, and schema major version.
4. Validate its anchor against the current ledger.
5. Page forward under item, byte, time, and request limits.
6. Normalize records and compute deterministic IDs.
7. Stream a batch to the sink.
8. Commit data and checkpoint atomically or record a partial receipt without
   advancing the durable checkpoint.
9. Reconcile finality in later passes and emit orphan/revert corrections rather
   than silently deleting history.

### 7.2 Ledger-range ingestion

Ledger scans require explicit start/end positions or a finite count. They
partition by non-overlapping ranges, persist range receipts, and may run in
parallel only when their sink partitions do not overlap. Tip-following is a
separate bounded mode with polling and cancellation controls.

### 7.3 Wallet export

Exports are data exports, not asset transfers. A manifest records:

- requested scope and filters;
- normalized schema and processor versions;
- source/provider capability;
- partition paths/CIDs and hashes;
- record and warning counts;
- start/end positions and finality distribution;
- checkpoint before/after;
- whether raw payloads were omitted, redacted, or separately encrypted; and
- whether the export is complete, partial, or cancelled.

JSONL is the debugging/interchange baseline. Parquet/Arrow is the analytical
baseline. Dataset writers use deterministic column types and partition keys.

## 8. Worldcoin migration boundary

### Move to `ipfs_datasets_py`

- `WorldIdConfig`, `WorldIdSecretConfig`, config loading/validation.
- RP signature model and signing/hash primitives.
- IDKit credential/result models and v3/v4 normalization.
- Developer Portal request protocol and injectable HTTP verifier.
- Verification response model/normalizer.
- Redaction and safe error helpers.
- Binding projection into `ipfs_datasets_py.wallet.WorldIdBinding`.
- World Chain ledger ingestion through the EVM processor.
- Focused unit and fixture tests now owned by the reusable package.

### Remain in `211-AI`

- FastAPI route schemas and HTTP status mapping.
- Application-specific authorization, actor/provider-staff checks, audit event
  naming, and UI.
- Environment-to-application wiring.
- A compatibility module re-exporting the documented public World ID API during
  the deprecation window.
- End-to-end application tests proving the wrapper uses the reusable package.

### Thin-wrapper gate

An AST/static test must prove that `wallet_interface/world_id.py`:

- imports only the reusable package and declared compatibility utilities;
- contains no `urllib`, `requests`, `httpx`, `Crypto`, `coincurve`, hash,
  signing, JSON normalization, or recursive-redaction implementation;
- has no network endpoint literal;
- stays below a reviewed line/symbol budget; and
- keeps old imports and exception identities compatible for one documented
  release window.

## 9. Xaman refactor boundary

1. Inventory current Xaman/XRPL logic and freeze import paths and assurance
   artifacts before moving anything.
2. Implement runtime Xaman/XRPL models, payload parsing, account transaction
   pagination, issued-currency identity, memo redaction, and normalized exports
   under `processors/wallets/xaman`.
3. Keep source extractors, formal security IR, theorem/protocol artifacts, and
   assurance reports under `logic`.
4. Add a small projection adapter from runtime records to security-analysis
   input where useful.
5. Do not make runtime ingestion depend on proof tooling, archived corpora,
   Firebase, mobile vault code, or a testnet device.
6. Preserve Xaman payload lifecycle states—created, opened, signed, rejected,
   expired, cancelled, submitted, validated, failed, unknown—without
   synthesizing signing or ledger-finality claims.

## 10. Delivery phases and gates

### Phase 0 — Baseline and ownership freeze

- Reproducible inventory of Worldcoin and Xaman symbols, callers, tests,
  optional dependencies, network boundaries, and target paths.
- Architecture decision for the wallet domain protocol and generic processor
  adapter.
- Golden behavior tests copied before moving code.

Gate: no production move begins until the inventory identifies every current
import and the protocol decision is accepted.

### Phase 1 — Shared wallet processor kernel

- Domain protocols and normalized models.
- Canonical serialization and deterministic IDs.
- Provider capability, retry, rate-limit, cancellation, and error taxonomy.
- Checkpoint, finality, reorg, streaming pipeline, storage, and manifests.
- No eager optional imports.

Gate: offline conformance tests prove idempotency, checkpoint CAS behavior,
reorg rewind, numeric precision, cancellation, and round-trip export.

### Phase 2 — Parallel chain implementations

After Phase 1, five disjoint lanes can run:

- Worldcoin migration plus World Chain adapter;
- Xaman/XRPL runtime processor;
- Ethereum;
- Bitcoin; and
- Solana.

Every lane begins with fixtures and contract tests, then implements clients and
normalizers. Live integration tests remain opt-in.

Gate: each chain passes the shared conformance suite and its chain-native golden
fixtures, including failure, pagination, retry, and finality cases.

### Phase 3 — Integration surfaces

- Registry compatibility adapter after resolving generic protocol ambiguity.
- Dataset/CLI/MCP surfaces with bounded parameters.
- `ipfs_datasets_py.wallet` World ID binding adapter.
- Cross-chain query/export examples and schema documentation.

Gate: package import remains side-effect free; MCP/CLI cannot disclose secrets,
perform unbounded scans, or sign/broadcast.

### Phase 4 — 211-AI cutover

- Replace World ID implementation with thin wrapper.
- Delegate application service operations to the reusable processor/service.
- Retain routes/UI and application authorization.
- Run old/new differential fixtures and end-to-end tests.
- Publish deprecation and rollback instructions.

Gate: no duplicate World ID protocol implementation remains in `211-AI`; all
application tests pass with the submodule package installed from the pinned
commit.

### Phase 5 — Release and hardening

- Dependency extras by chain; SBOM/license review.
- Performance budgets and representative fixture benchmarks.
- Optional live smoke tests against explicitly selected non-production
  endpoints.
- Versioned release notes, compatibility matrix, and staged rollout.

Gate: two consecutive clean full validation runs, current-tree manifests, no
critical security findings, and a tested submodule rollback.

## 11. Parallel execution graph

```text
inventory ──> contracts ──> pipeline/storage ─┬─> worldcoin ─> thin wrapper
                                             ├─> xaman
                                             ├─> ethereum ─> world chain
                                             ├─> bitcoin
                                             └─> solana

contracts + all chain lanes ─> registry/CLI/MCP ─> conformance/security
                             └───────────────────> release/cutover
```

Conflict ownership:

| Bundle | Owned paths |
| --- | --- |
| `wallet-processors/contracts` | `processors/wallets/{protocols,models,canonical,errors}.py` |
| `wallet-processors/pipeline` | shared pipeline/checkpoint/finality/provider/storage modules |
| `wallet-processors/worldcoin` | `processors/wallets/worldcoin/**` and focused target tests |
| `wallet-processors/xaman` | `processors/wallets/xaman/**`; formal Xaman code only through an explicit child task |
| `wallet-processors/ethereum` | `processors/wallets/ethereum/**` |
| `wallet-processors/bitcoin` | `processors/wallets/bitcoin/**` |
| `wallet-processors/solana` | `processors/wallets/solana/**` |
| `wallet-processors/integration` | registry, CLI/MCP, shared docs, shared conformance |
| `wallet-processors/wrapper` | `wallet_interface/**` and outer-repository tests |

Chain lanes do not edit shared models. Missing shared fields produce a contract
refinement task instead of opportunistic edits.

## 12. Test strategy

### Required offline tests

- Address validation and network separation.
- Canonical ID and serialization golden vectors.
- Base-unit amount precision and large values.
- Empty, malformed, partial, duplicate, and out-of-order provider responses.
- Pagination boundaries and repeated cursors.
- Retry classification, rate limiting, deadlines, and cancellation.
- Checkpoint compare-and-set conflicts.
- Reorg/rollback and finality transitions.
- Export manifest hashes, partition schema, and partial-run recovery.
- No secrets in repr, logs, exceptions, JSON, Parquet, or raw-payload metadata.
- Import smoke tests with every optional chain dependency absent.
- Shared processor conformance for all five implementations.

### Chain fixtures

- World ID v3/v4 uniqueness/session responses, signing vectors, success/failure
  verification responses, and redaction cases.
- XRPL native XRP, issued currency, partial payment, destination tag, memo,
  failed transaction, pagination marker, and validated/unvalidated fixtures.
- EVM legacy/EIP-1559 txs, reverted receipt, removed log, contract creation,
  ERC-20/721/1155, safe/finalized, and reorg fixtures.
- Bitcoin legacy/SegWit/Taproot scripts, coinbase, multi-input/output, spent and
  unspent outputs, replacement/reorg, and network mismatch fixtures.
- Solana legacy/versioned messages, address lookup tables, failed tx,
  inner instructions, lamport/SPL transfers, token balances, and commitment
  transitions.

### Optional integration tests

Marked tests require explicit endpoint variables and an allow-network flag.
They use bounded historical ranges or known public addresses, redact provider
keys, write only temporary artifacts, and never sign or broadcast.

## 13. Security, privacy, and abuse controls

- Public data can still be personal data; exports retain purpose, scope,
  retention, and access-control metadata.
- No cross-address identity clustering in the canonical processor.
- Memos, calldata, instruction data, and raw payloads are opt-in fields with
  size and redaction limits.
- Provider URLs and API-key references are configuration; client requests do
  not choose arbitrary endpoints by default.
- SSRF checks apply to configurable HTTP endpoints.
- Decompression, response bytes, page counts, records, range, wall time, and
  retries are bounded.
- Log fields use allowlists. Payload dumps are prohibited.
- Dependencies are optional extras (`wallets-worldcoin`, `wallets-xaman`,
  `wallets-ethereum`, `wallets-bitcoin`, `wallets-solana`, `wallets-all`) and
  reviewed for license and supply-chain risk.
- Signing and broadcasting remain separate denied capabilities. Any future
  enablement requires a new objective, threat model, authorization contract,
  and release gate.

## 14. Performance and operability

Initial measurable budgets:

- Streaming normalization; no unbounded whole-history list in memory.
- Configurable page and batch sizes with conservative defaults.
- Checkpoint after each committed batch.
- Bounded concurrent provider requests per endpoint.
- Metrics for calls, retries, throttles, bytes, records, normalization errors,
  checkpoint age, head lag, reorg rewinds, finality distribution, and export
  throughput.
- Structured run receipts without wallet payloads or provider secrets.
- A deterministic fixture benchmark for records/second and peak memory; live
  provider latency is reported separately.

## 15. Compatibility and rollout

1. Introduce new target package as experimental and keep old 211-AI code.
2. Run copied golden tests against both implementations.
3. Switch 211-AI imports to the target while the compatibility wrapper
   preserves old symbols.
4. Pin the `ipfs_datasets_py` submodule commit and run end-to-end tests.
5. Remove duplicate implementation from the wrapper.
6. Hold one release with deprecation warnings and documented import mapping.
7. Remove deprecated aliases only in a separately approved breaking release.

Rollback is a gitlink reversal plus the prior wrapper release. Dataset schemas
remain readable across rollback through explicit schema-version adapters.

## 16. Definition of done

- `ipfs_datasets_py.processors.wallets` contains the shared kernel and five
  processors with documented public APIs.
- Worldcoin protocol logic has one implementation, in `ipfs_datasets_py`.
- `211-AI.wallet_interface.world_id` passes the thin-wrapper static gate.
- Xaman runtime processing is separate from, but compatible with, its security
  analysis assets.
- Wallet and bounded public-ledger ingestion/export work from offline fixtures
  for Worldcoin/World Chain, XRPL, Ethereum, Bitcoin, and Solana.
- Every chain passes shared conformance, finality/reorg, checkpoint,
  serialization, security, and import tests.
- CLI/MCP operations are bounded and non-custodial.
- Dependency extras, schemas, examples, migration guide, observability, and
  rollback are documented.
- The agent supervisor objective heap has no active child goal without either a
  ready task, verified evidence, or a recorded blocker.

## 17. Supervisor operating model

The `ipfs_accelerate_py.agent_supervisor` objective daemon owns projection from
the reviewed objective heap to tasks, bundles, graph, AST dataset, discovery
evidence, and todo-vector index.

Two implementation supervisors drain deterministic task shards:

- shard 0: ChatGPT Codex;
- shard 1: Grok Build.

Both use isolated outer-repository worktrees, explicit
`--worktree-submodule-path ipfs_datasets_py`, a shared merge target
`codex/wallet-processors-migration`, separate state directories, bounded retry
budgets, and protected plan/objective files. The Codex control lane performs
objective refill when healthy open work drops below the threshold. The Grok
lane consumes its shard without independently rewriting the objective heap.

Refill policy:

- scan only active/reopened goals;
- generate at most the configured bounded findings per pass;
- deduplicate by canonical task identity;
- prioritize retry/dependency/reconciliation repairs before new feature work;
- never mark a goal complete from todo text alone;
- require current-tree validation evidence;
- stop automatic implementation after the retry budget and generate a repair
  task or blocker instead; and
- never auto-enable network, credentials, signing, broadcasting, package
  installation, or production configuration.
