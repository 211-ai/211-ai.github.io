# Multi-Chain Wallet Processor Objective Heap

This reviewed heap is the durable source of intent for migrating reusable
Worldcoin code from 211-AI into `ipfs_datasets_py`, retaining a thin 211-AI
wrapper, refactoring Xaman/XRPL processing, and implementing Ethereum, Bitcoin,
and Solana wallet/public-ledger ingestion and data export.

The human architecture is
[`WALLET_PROCESSORS_MIGRATION_PLAN.md`](WALLET_PROCESSORS_MIGRATION_PLAN.md).
The executable projection is
[`WALLET_PROCESSORS_TODO.md`](WALLET_PROCESSORS_TODO.md).

Program invariants:

- Integration target is branch `codex/wallet-processors-migration`.
- Reusable behavior belongs under
  `ipfs_datasets_py/ipfs_datasets_py/processors/wallets`.
- The existing `ipfs_datasets_py.wallet` UCAN/human-data package remains a
  compatibility surface; World-specific internals move behind delegators.
- World ID, World Chain, and the WLD token are separate types and capabilities.
- Xaman composes XRPL; World Chain composes Ethereum/EVM.
- The initial processor surface is read-only and non-custodial: no key storage,
  signing, approval, submission, or broadcast.
- Imports and normal tests perform no network calls or dependency installation.
- Exact amounts use integer base units; floats are forbidden.
- Checkpoints are chain/network/genesis/provider/scope/schema bound,
  compare-and-set, hash anchored, and reorg aware.
- Public-ledger observations never assert ownership, identity, personhood,
  eligibility, or authorization.
- Shared contract files have one serialized owner. Chain lanes own only their
  package and focused tests.
- Objective/task completion requires current-tree validation evidence, not
  model output or a changed Markdown status.

## WALPROC-G000 Deliver reusable, safe multi-chain wallet processors

- Status: active
- Parent:
- Fib priority: 1
- Priority: P0
- Track: wallet-processors-program
- Bundle: wallet-processors/control
- Goal: Deliver a production-quality, dependency-light `processors.wallets` package with Worldcoin, Xaman/XRPL, Ethereum/World Chain, Bitcoin, and Solana wallet/public-ledger ingestion and dataset export; migrate Worldcoin ownership out of 211-AI; and leave a tested thin compatibility wrapper.
- Evidence: WALPROC-G010, WALPROC-G020, WALPROC-G030, WALPROC-G040, WALPROC-G050, WALPROC-G060, WALPROC-G070, WALPROC-G080, WALPROC-G090, WALPROC-G100, WALPROC-G110, WALPROC-G120, WALPROC-G130, WALPROC-G200, WALPROC-G210, WALPROC-G220, WALPROC-G300, WALPROC-G400, WALPROC-G500, WALPROC-G600, WALPROC-G610, WALPROC-G620, WALPROC-G630, WALPROC-G640, WALPROC-G700, WALPROC-G710, WALPROC-G800
- Outputs: ipfs_datasets_py/ipfs_datasets_py/processors/wallets, wallet_interface/world_id.py, docs/planning/WALLET_PROCESSORS_MIGRATION_PLAN.md
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/processors/wallets ipfs_datasets_py/tests/contract/processors/wallets tests/test_world_id_wallet.py tests/test_world_id_wallet_api.py
- Acceptance: Every child objective has current-tree evidence or a recorded external blocker; all five chain families pass shared conformance; Worldcoin reusable code has one owner in ipfs_datasets_py; the 211-AI wrapper passes its static thinness gate; Xaman runtime processing is separated from formal assurance; release, rollback, privacy, security, and bounded-operation documentation is current.
- Gap task: Implement the highest-priority ready child objective without widening custody, signing, broadcast, network, or production authority.
- Refinement: Complete inventory and shared contracts first; then run chain packages in parallel; serialize integration and cutover.
- Embedding query: multi chain wallet processor worldcoin xaman xrpl ethereum bitcoin solana public ledger ingestion dataset export thin wrapper
- AST query: WalletProcessor LedgerProvider WalletLedgerProcessor WorldcoinWalletProcessor
- Goal completion schema version: 1
- Completion confidence: 0.083333
- Uncovered criteria: ["Every child objective has current-tree evidence or a recorded external blocker","all five chain families pass shared conformance","Worldcoin reusable code has one owner in ipfs_datasets_py","the 211-AI wrapper passes its static thinness gate","Xaman runtime processing is separated from formal assurance","release, rollback, privacy, security, and bounded-operation documentation is current."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []

## WALPROC-G010 Freeze the source inventory and ownership map

- Status: provisionally_complete
- Parent: WALPROC-G000
- Fib priority: 2
- Priority: P0
- Track: bootstrap
- Bundle: wallet-processors/bootstrap
- Goal: Produce a deterministic inventory of Worldcoin, World ID, World Chain, Xaman, XRPL, existing wallet-domain, processor-protocol, caller, test, dependency, network, secret, snapshot, and UI boundaries before production code moves.
- Evidence: data/wallet_processor_migration/audit/source-inventory.json, data/wallet_processor_migration/audit/import-map.json, data/wallet_processor_migration/audit/ownership-map.md
- Outputs: data/wallet_processor_migration/audit/source-inventory.json, data/wallet_processor_migration/audit/import-map.json, data/wallet_processor_migration/audit/ownership-map.md
- Validation: python scripts/audit_wallet_processor_migration.py --check
- Acceptance: The inventory includes every symbol in the 955-line wallet_interface/world_id.py, World ID code in app_service.py and ops.py, WorldIdBinding and all service/snapshot/proof/nullifier paths in ipfs_datasets_py.wallet, all direct Python and TypeScript callers, current Xaman security/formal assets, both incompatible generic processor protocols and registries, optional dependency declarations, network endpoints, config keys, secret references, and a move/retain/deprecate decision with one owner per symbol.
- Gap task: Add a deterministic read-only audit script and checked-in machine/human reports; do not move code.
- Refinement: Record unresolved ownership as a blocker rather than guessing.
- Embedding query: source inventory world id binding app service xaman xrpl processor protocols dependencies imports ownership
- AST query: WorldIdBinding DataWalletService WorldIdConfig normalize_world_id_idkit_response _world_id_production_readiness_checks
- Goal completion schema version: 1
- Completion confidence: 0.166667
- Uncovered criteria: ["The inventory includes every symbol in the 955-line wallet_interface/world_id.py, World ID code in app_service.py and ops.py, WorldIdBinding and all service/snapshot/proof/nullifier paths in ipfs_datasets_py.wallet, all direct Python and TypeScript callers, current Xaman security/formal assets, both incompatible generic processor protocols and registries, optional dependency declarations, network endpoints, config keys, secret references, and a move/retain/deprecate decision with one owner per symbol."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []
- State transitioned at: 2026-07-28T22:49:13.476228+00:00
- State transition reason: Produce completion evidence for: The inventory includes every symbol in the 955-line wallet_interface/world_id.py, World ID code in app_service.py and ops.py, WorldIdBinding and all service/snapshot/proof/nullifier paths in ipfs_datasets_py.wallet, all direct Python and TypeScript callers, current Xaman security/formal assets, both incompatible generic processor protocols and registries, optional dependency declarations, network endpoints, config keys, secret references, and a move/retain/deprecate decision with one owner per symbol.; Map every mandatory acceptance criterion to fresh, verified implementation and validation proof bound to the current tree.; Every submitted validation proof must be fresh and passing, and every mandatory criterion must have one.; Require an explicitly healthy analyzer that is safe for completion reasoning.; Require the configured number of independent, fresh, healthy exhaustive receipts bound to the current repository tree.; Task completion is provisional until every criterion has valid evidence.
- Provisional at: 2026-07-28T22:49:13.476228+00:00

## WALPROC-G020 Freeze compatibility, security, and fixture baselines

- Status: provisionally_complete
- Parent: WALPROC-G000
- Fib priority: 3
- Priority: P0
- Track: bootstrap
- Bundle: wallet-processors/bootstrap
- Depends on: WALPROC-G010
- Goal: Freeze current import names, route DTOs, snapshot shapes, World ID signing/hash/parser vectors, public projections, Xaman assurance links, and known security failures so moves cannot silently change behavior or bless unsafe behavior.
- Evidence: ipfs_datasets_py/tests/fixtures/wallets/worldcoin, ipfs_datasets_py/tests/fixtures/wallets/xaman, ipfs_datasets_py/tests/contract/processors/wallets/test_migration_baseline.py, data/wallet_processor_migration/audit/security-baseline.json
- Outputs: ipfs_datasets_py/tests/fixtures/wallets/worldcoin, ipfs_datasets_py/tests/fixtures/wallets/xaman, ipfs_datasets_py/tests/contract/processors/wallets/test_migration_baseline.py, data/wallet_processor_migration/audit/security-baseline.json
- Validation: python -m pytest -q ipfs_datasets_py/tests/contract/processors/wallets/test_migration_baseline.py
- Acceptance: Golden vectors cover existing World ID signing, hash-to-field, IDKit v3/v4 uniqueness/session, verify success/failure, redaction, old snapshot import, route shapes, and old import identities; the baseline explicitly marks legacy-default-on, unenforced user presence/signal/provider context, unissued challenge acceptance, optional status authentication, raw/process-local nullifier state, v3-as-v4 receipt labeling, stale proof receipts after revoke/expiry, unsafe configurable endpoints, and plaintext snapshots as failures to fix rather than compatibility guarantees.
- Gap task: Copy and classify fixtures before implementation movement; add expected-failure security tests for each known gap.
- Refinement: Compatibility freezes API shape and safe vectors, not vulnerabilities.
- Embedding query: golden fixtures migration compatibility world id security baseline xaman assurance snapshot route
- AST query: sign_world_id_request hash_to_field normalize_idkit_response get_world_id_status
- Goal completion schema version: 1
- Completion confidence: 0.166667
- Uncovered criteria: ["Golden vectors cover existing World ID signing, hash-to-field, IDKit v3/v4 uniqueness/session, verify success/failure, redaction, old snapshot import, route shapes, and old import identities","the baseline explicitly marks legacy-default-on, unenforced user presence/signal/provider context, unissued challenge acceptance, optional status authentication, raw/process-local nullifier state, v3-as-v4 receipt labeling, stale proof receipts after revoke/expiry, unsafe configurable endpoints, and plaintext snapshots as failures to fix rather than compatibility guarantees."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []
- State transitioned at: 2026-07-28T22:49:13.476228+00:00
- State transition reason: Produce completion evidence for: Golden vectors cover existing World ID signing, hash-to-field, IDKit v3/v4 uniqueness/session, verify success/failure, redaction, old snapshot import, route shapes, and old import identities; Map every mandatory acceptance criterion to fresh, verified implementation and validation proof bound to the current tree.; Every submitted validation proof must be fresh and passing, and every mandatory criterion must have one.; Require an explicitly healthy analyzer that is safe for completion reasoning.; Require the configured number of independent, fresh, healthy exhaustive receipts bound to the current repository tree.; Task completion is provisional until every criterion has valid evidence.
- Provisional at: 2026-07-28T22:49:13.476228+00:00

## WALPROC-G030 Approve the wallet-domain protocol and processor adapter decision

- Status: provisionally_complete
- Parent: WALPROC-G000
- Fib priority: 5
- Priority: P0
- Track: shared-contracts
- Bundle: wallet-processors/contracts
- Depends on: WALPROC-G010
- Goal: Define dependency-light async wallet/ledger/source/sink/checkpoint/finality protocols and resolve or explicitly defer the incompatible generic `can_process` versus `can_handle` processor/registry surfaces.
- Evidence: ipfs_datasets_py/docs/architecture/WALLET_PROCESSOR_PROTOCOL_ADR.md, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/protocols.py, ipfs_datasets_py/tests/unit/processors/wallets/test_protocols.py
- Outputs: ipfs_datasets_py/docs/architecture/WALLET_PROCESSOR_PROTOCOL_ADR.md, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/protocols.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/errors.py, ipfs_datasets_py/tests/unit/processors/wallets/test_protocols.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/processors/wallets/test_protocols.py
- Acceptance: Protocols cover WalletProvider, LedgerProvider, ChainNormalizer, CheckpointStore, DatasetSink, Exporter, HttpTransport, SecretResolver, FinalityPolicy, capabilities, cancellation, deadlines, and bounded requests; signing/broadcast are absent; imports have no optional/network side effects; ADR documents both current generic APIs and permits exactly one later compatibility adapter.
- Gap task: Write the ADR and structural protocols with fake implementations and import-smoke tests.
- Refinement: Do not edit either generic registry in this goal.
- Embedding query: wallet domain protocol ledger provider dataset sink checkpoint finality generic processor ambiguity
- AST query: ProcessorProtocol ProcessingContext ProcessorRegistry UniversalProcessor
- Goal completion schema version: 1
- Completion confidence: 0.166667
- Uncovered criteria: ["Protocols cover WalletProvider, LedgerProvider, ChainNormalizer, CheckpointStore, DatasetSink, Exporter, HttpTransport, SecretResolver, FinalityPolicy, capabilities, cancellation, deadlines, and bounded requests","signing/broadcast are absent","imports have no optional/network side effects","ADR documents both current generic APIs and permits exactly one later compatibility adapter."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []
- State transitioned at: 2026-07-28T22:49:13.476228+00:00
- State transition reason: Produce completion evidence for: Protocols cover WalletProvider, LedgerProvider, ChainNormalizer, CheckpointStore, DatasetSink, Exporter, HttpTransport, SecretResolver, FinalityPolicy, capabilities, cancellation, deadlines, and bounded requests; Map every mandatory acceptance criterion to fresh, verified implementation and validation proof bound to the current tree.; Every submitted validation proof must be fresh and passing, and every mandatory criterion must have one.; Require an explicitly healthy analyzer that is safe for completion reasoning.; Require the configured number of independent, fresh, healthy exhaustive receipts bound to the current repository tree.; Task completion is provisional until every criterion has valid evidence.
- Provisional at: 2026-07-28T22:49:13.476228+00:00

## WALPROC-G040 Define normalized schemas and canonical identity

- Status: provisionally_complete
- Parent: WALPROC-G000
- Fib priority: 5
- Priority: P0
- Track: shared-contracts
- Bundle: wallet-processors/contracts
- Depends on: WALPROC-G030
- Goal: Implement versioned chain, account, asset, position, block, transaction, transfer, balance, UTXO, token-account, contract-event, provenance, checkpoint, and export-manifest models with deterministic canonical encoding.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/models.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/canonical.py, ipfs_datasets_py/docs/schemas/wallet-ledger-record-v1.schema.json, ipfs_datasets_py/tests/unit/processors/wallets/test_models.py
- Outputs: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/models.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/canonical.py, ipfs_datasets_py/docs/schemas/wallet-ledger-record-v1.schema.json, ipfs_datasets_py/docs/schemas/wallet-export-manifest-v1.schema.json, ipfs_datasets_py/tests/unit/processors/wallets/test_models.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/processors/wallets/test_models.py
- Acceptance: All records carry schema/version, deterministic ID, chain/network/genesis identity, source provenance, observed time, finality, and extensions; amounts are exact base units with explicit decimals; raw payloads are digest/CID references; cross-network identities cannot collide; unknown/failed/orphaned states remain distinguishable; serialization is deterministic and JSON Schema validated.
- Gap task: Implement immutable models, schemas, canonical ID rules, and golden round trips.
- Refinement: Chain-specific fields remain in versioned extensions unless shared semantics are proven.
- Embedding query: chain account asset transaction transfer balance utxo canonical record id schema provenance exact amount
- AST query: ChainRef AccountRef AssetRef TransactionRecord TransferRecord LedgerCursor ExportManifest
- Goal completion schema version: 1
- Completion confidence: 0.166667
- Uncovered criteria: ["All records carry schema/version, deterministic ID, chain/network/genesis identity, source provenance, observed time, finality, and extensions","amounts are exact base units with explicit decimals","raw payloads are digest/CID references","cross-network identities cannot collide","unknown/failed/orphaned states remain distinguishable","serialization is deterministic and JSON Schema validated."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []
- State transitioned at: 2026-07-28T22:49:13.476228+00:00
- State transition reason: Produce completion evidence for: All records carry schema/version, deterministic ID, chain/network/genesis identity, source provenance, observed time, finality, and extensions; Map every mandatory acceptance criterion to fresh, verified implementation and validation proof bound to the current tree.; Every submitted validation proof must be fresh and passing, and every mandatory criterion must have one.; Require an explicitly healthy analyzer that is safe for completion reasoning.; Require the configured number of independent, fresh, healthy exhaustive receipts bound to the current repository tree.; Task completion is provisional until every criterion has valid evidence.
- Provisional at: 2026-07-28T22:49:13.476228+00:00

## WALPROC-G050 Review and declare optional dependency extras

- Status: provisionally_complete
- Parent: WALPROC-G000
- Fib priority: 8
- Priority: P1
- Track: dependencies
- Bundle: wallet-processors/dependencies
- Depends on: WALPROC-G010, WALPROC-G020
- Goal: Select minimal reviewed dependencies and extras for shared wallet, Worldcoin, Ethereum, XRPL/Xaman, Bitcoin, Solana, and all-wallet installs while aligning the Python version contract between 211-AI and ipfs_datasets_py.
- Evidence: ipfs_datasets_py/docs/dependencies/WALLET_PROCESSOR_DEPENDENCIES.md, ipfs_datasets_py/pyproject.toml, ipfs_datasets_py/setup.py, ipfs_datasets_py/tests/contract/processors/wallets/test_optional_dependencies.py
- Outputs: ipfs_datasets_py/docs/dependencies/WALLET_PROCESSOR_DEPENDENCIES.md, ipfs_datasets_py/pyproject.toml, ipfs_datasets_py/setup.py, ipfs_datasets_py/tests/contract/processors/wallets/test_optional_dependencies.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/contract/processors/wallets/test_optional_dependencies.py
- Acceptance: Extras `wallets`, `wallets-worldcoin`, `wallets-ethereum`, `wallets-xrpl`, `wallets-xaman`, `wallets-bitcoin`, `wallets-solana`, and `wallets-all` have compatible bounds, hashes/provenance/license/SBOM rationale; coincurve/pycryptodome versus existing eth-hash/eth-keys is decided by vectors; raw REST/JSON-RPC remains sufficient unless an SDK earns inclusion; minimal imports succeed with every chain extra absent; Python support mismatch has a documented resolution.
- Gap task: Produce a dependency selection report and synchronized metadata changes; do not auto-install anything.
- Refinement: SDK convenience is not sufficient justification for a mandatory dependency.
- Embedding query: wallet optional extras dependency license sbom worldcoin coincurve pycryptodome web3 solana xrpl bitcoin
- AST query: optional-dependencies extras_require
- Goal completion schema version: 1
- Completion confidence: 0.166667
- Uncovered criteria: ["Extras `wallets`, `wallets-worldcoin`, `wallets-ethereum`, `wallets-xrpl`, `wallets-xaman`, `wallets-bitcoin`, `wallets-solana`, and `wallets-all` have compatible bounds, hashes/provenance/license/SBOM rationale","coincurve/pycryptodome versus existing eth-hash/eth-keys is decided by vectors","raw REST/JSON-RPC remains sufficient unless an SDK earns inclusion","minimal imports succeed with every chain extra absent","Python support mismatch has a documented resolution."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []
- State transitioned at: 2026-07-28T22:49:13.476228+00:00
- State transition reason: Produce completion evidence for: Extras `wallets`, `wallets-worldcoin`, `wallets-ethereum`, `wallets-xrpl`, `wallets-xaman`, `wallets-bitcoin`, `wallets-solana`, and `wallets-all` have compatible bounds, hashes/provenance/license/SBOM rationale; Map every mandatory acceptance criterion to fresh, verified implementation and validation proof bound to the current tree.; Every submitted validation proof must be fresh and passing, and every mandatory criterion must have one.; Require an explicitly healthy analyzer that is safe for completion reasoning.; Require the configured number of independent, fresh, healthy exhaustive receipts bound to the current repository tree.; Task completion is provisional until every criterion has valid evidence.
- Provisional at: 2026-07-28T22:49:13.476228+00:00

## WALPROC-G060 Implement bounded provider transport and security controls

- Status: active
- Parent: WALPROC-G000
- Fib priority: 8
- Priority: P0
- Track: shared-runtime
- Bundle: wallet-processors/pipeline
- Depends on: WALPROC-G030, WALPROC-G040
- Goal: Provide injected HTTP/JSON-RPC transport, endpoint policy, capabilities, retry taxonomy, Retry-After handling, jitter, rate limits, circuit breaking, body/page/range/deadline bounds, cancellation, SSRF defense, and safe error/redaction behavior.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/providers/http.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/providers/retry.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/providers/rate_limit.py, ipfs_datasets_py/tests/unit/processors/wallets/test_transport.py
- Outputs: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/providers, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/security.py, ipfs_datasets_py/tests/unit/processors/wallets/test_transport.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/processors/wallets/test_transport.py
- Acceptance: Import performs no I/O; fake transport covers success, malformed response, timeout, cancellation, throttling, transient/permanent errors, oversized response, pagination loop, unsafe endpoint, and circuit breaker; secrets and full endpoints never enter repr/log/errors/checkpoints/manifests; every request has finite byte/page/time/retry budgets.
- Gap task: Implement dependency-injected transport and deterministic fake-clock tests.
- Refinement: Provider authentication uses secret references, never secret fields in serializable config.
- Embedding query: http json rpc retry rate limit circuit breaker ssrf deadline cancellation redaction wallet provider
- AST query: HttpTransport RetryPolicy RateLimiter ProviderCapability SecretResolver
- Goal completion schema version: 1
- Completion confidence: 0.166667
- Uncovered criteria: ["Import performs no I/O","fake transport covers success, malformed response, timeout, cancellation, throttling, transient/permanent errors, oversized response, pagination loop, unsafe endpoint, and circuit breaker","secrets and full endpoints never enter repr/log/errors/checkpoints/manifests","every request has finite byte/page/time/retry budgets."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []

## WALPROC-G070 Implement checkpoint, finality, and reorganization contracts

- Status: active
- Parent: WALPROC-G000
- Fib priority: 13
- Priority: P0
- Track: shared-runtime
- Bundle: wallet-processors/pipeline
- Depends on: WALPROC-G040, WALPROC-G060
- Goal: Implement hash-anchored compare-and-set checkpoints, bounded canonical history, chain-specific finality policy hooks, resume validation, common-ancestor rewind, orphan/tombstone projection, and deep-reorg fail-closed behavior.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/checkpoints.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/finality.py, ipfs_datasets_py/tests/unit/processors/wallets/test_checkpoints.py, ipfs_datasets_py/tests/unit/processors/wallets/test_reorgs.py
- Outputs: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/checkpoints.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/finality.py, ipfs_datasets_py/tests/unit/processors/wallets/test_checkpoints.py, ipfs_datasets_py/tests/unit/processors/wallets/test_reorgs.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/processors/wallets/test_checkpoints.py ipfs_datasets_py/tests/unit/processors/wallets/test_reorgs.py
- Acceptance: Checkpoint identity binds chain/network/genesis/provider/scan scope/schema/normalizer; sink commit precedes checkpoint CAS; crash replay is idempotent; shallow reorg finds an ancestor and emits orphan corrections; deep reorg stops for review; finality is an enum/state transition rather than a boolean; provisional export requires explicit opt-in.
- Gap task: Add in-memory reference implementations and crash/CAS/reorg state-machine tests.
- Refinement: Provider continuation tokens never replace canonical hash anchors.
- Embedding query: checkpoint compare and set finality reorg rewind orphan tombstone canonical hash crash replay
- AST query: CheckpointStore FinalityPolicy rewind common_ancestor
- Goal completion schema version: 1
- Completion confidence: 0.166667
- Uncovered criteria: ["Checkpoint identity binds chain/network/genesis/provider/scan scope/schema/normalizer","sink commit precedes checkpoint CAS","crash replay is idempotent","shallow reorg finds an ancestor and emits orphan corrections","deep reorg stops for review","finality is an enum/state transition rather than a boolean","provisional export requires explicit opt-in."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []

## WALPROC-G080 Implement streaming ingestion and dataset export

- Status: active
- Parent: WALPROC-G000
- Fib priority: 13
- Priority: P0
- Track: shared-runtime
- Bundle: wallet-processors/pipeline
- Depends on: WALPROC-G060, WALPROC-G070
- Goal: Implement bounded wallet-centric and ledger-range pipelines, transactional streaming batches, deterministic JSONL and Parquet/Arrow exports, optional IPLD/CAR export, raw-payload digest storage, partial receipts, resume, and manifest verification.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/pipeline.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/storage.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/export.py, ipfs_datasets_py/tests/unit/processors/wallets/test_pipeline.py
- Outputs: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/pipeline.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/storage.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/export.py, ipfs_datasets_py/tests/unit/processors/wallets/test_pipeline.py, ipfs_datasets_py/tests/unit/processors/wallets/test_export.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/processors/wallets/test_pipeline.py ipfs_datasets_py/tests/unit/processors/wallets/test_export.py
- Acceptance: Scans require finite scopes; normalization streams without whole-history accumulation; duplicate/out-of-order pages do not duplicate records; partial/cancelled runs do not skip checkpoints; manifests include scope, versions, provider capability, digests/CIDs, counts, positions, finality, warnings, raw-data policy, and before/after checkpoints; round trips preserve exact types and IDs.
- Gap task: Build reference sinks/exporters and deterministic pipeline fixture tests.
- Refinement: IPLD/CAR may remain an optional child if JSONL and Parquet contracts land first.
- Embedding query: streaming wallet ingestion ledger range jsonl parquet arrow ipld car export manifest resume
- AST query: WalletLedgerProcessor DatasetSink Exporter ExportReceipt
- Goal completion schema version: 1
- Completion confidence: 0.166667
- Uncovered criteria: ["Scans require finite scopes","normalization streams without whole-history accumulation","duplicate/out-of-order pages do not duplicate records","partial/cancelled runs do not skip checkpoints","manifests include scope, versions, provider capability, digests/CIDs, counts, positions, finality, warnings, raw-data policy, and before/after checkpoints","round trips preserve exact types and IDs."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []

## WALPROC-G090 Build shared chain conformance and fixture harness

- Status: active
- Parent: WALPROC-G000
- Fib priority: 13
- Priority: P0
- Track: testing
- Bundle: wallet-processors/conformance
- Depends on: WALPROC-G040, WALPROC-G070, WALPROC-G080
- Goal: Create reusable provider/normalizer/processor conformance suites and offline fixture loaders that every chain must pass.
- Evidence: ipfs_datasets_py/tests/contract/processors/wallets/conformance.py, ipfs_datasets_py/tests/fixtures/wallets, ipfs_datasets_py/tests/contract/processors/wallets/test_fixture_integrity.py
- Outputs: ipfs_datasets_py/tests/contract/processors/wallets/conformance.py, ipfs_datasets_py/tests/fixtures/wallets, ipfs_datasets_py/tests/contract/processors/wallets/test_fixture_integrity.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/contract/processors/wallets/test_fixture_integrity.py
- Acceptance: Harness tests address/network identity, exact amounts, deterministic IDs, malformed/empty/partial data, pagination, retries, cancellation, idempotency, CAS conflicts, shallow/deep reorg, export round trip, secret leaks, optional dependency absence, and no-network imports; fixtures are immutable/digested and include source/license/provenance.
- Gap task: Implement abstract conformance mixins/factories and integrity-checked offline fixtures.
- Refinement: Chain-specific assertions extend rather than weaken shared checks.
- Embedding query: wallet chain conformance fixtures provider normalizer checkpoint reorg export offline
- AST query: WalletProcessorConformance ProviderContract FixtureTransport
- Goal completion schema version: 1
- Completion confidence: 0.166667
- Uncovered criteria: ["Harness tests address/network identity, exact amounts, deterministic IDs, malformed/empty/partial data, pagination, retries, cancellation, idempotency, CAS conflicts, shallow/deep reorg, export round trip, secret leaks, optional dependency absence, and no-network imports","fixtures are immutable/digested and include source/license/provenance."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []

## WALPROC-G100 Migrate World ID pure protocol code

- Status: active
- Parent: WALPROC-G000
- Fib priority: 21
- Priority: P0
- Track: worldcoin
- Bundle: wallet-processors/worldcoin
- Depends on: WALPROC-G020, WALPROC-G030, WALPROC-G040, WALPROC-G050, WALPROC-G060
- Goal: Move World ID exceptions, DTOs, config, secret descriptors, Keccak/hash-to-field, EIP-191 RP signing, IDKit v3/v4 parsing, Developer Portal verification, safe errors, and proof redaction from wallet_interface/world_id.py into the new reusable Worldcoin package.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin/config.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin/signing.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin/idkit.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin/developer_portal.py, ipfs_datasets_py/tests/unit/processors/wallets/worldcoin
- Outputs: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin, ipfs_datasets_py/tests/unit/processors/wallets/worldcoin
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/processors/wallets/worldcoin
- Acceptance: Existing official vectors are byte-identical; safe defaults reject legacy evidence unless explicitly permitted; v3/v4/session labels remain accurate; injected transport and endpoint policy are bounded; config serializes secret references only; raw proof/nullifier/upstream payload cannot enter logs/errors/public dicts; package import has no I/O.
- Gap task: Port pure code by module with copied golden tests before deleting any source implementation.
- Refinement: Config/models, signing, and IDKit/verifier can be separate tasks with disjoint files after API scaffold.
- Embedding query: world id idkit developer portal rp signing hash to field redaction migration
- AST query: WorldIdConfig WorldIdRpSignature sign_world_id_request normalize_idkit_response verify_world_id_proof
- Goal completion schema version: 1
- Completion confidence: 0.166667
- Uncovered criteria: ["Existing official vectors are byte-identical","safe defaults reject legacy evidence unless explicitly permitted","v3/v4/session labels remain accurate","injected transport and endpoint policy are bounded","config serializes secret references only","raw proof/nullifier/upstream payload cannot enter logs/errors/public dicts","package import has no I/O."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []

## WALPROC-G110 Extract World ID binding, challenge, replay, proof, and snapshot ownership

- Status: active
- Parent: WALPROC-G000
- Fib priority: 21
- Priority: P0
- Track: worldcoin
- Bundle: wallet-processors/worldcoin-state
- Depends on: WALPROC-G040, WALPROC-G070, WALPROC-G100
- Goal: Extract WorldIdBinding, nullifier indexes, issued challenges, verification orchestration, proof receipts, revocation/expiry, snapshot hooks, and export sanitation from app_service.py and ipfs_datasets_py.wallet behind durable privacy-safe Worldcoin services and compatibility delegators.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin/bindings.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin/challenges.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin/proofs.py, ipfs_datasets_py/tests/unit/processors/wallets/worldcoin/test_bindings.py
- Outputs: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin/bindings.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin/challenges.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin/proofs.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin/snapshots.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin/processor.py, ipfs_datasets_py/ipfs_datasets_py/wallet/models.py, ipfs_datasets_py/ipfs_datasets_py/wallet/service.py, ipfs_datasets_py/tests/unit/processors/wallets/worldcoin/test_bindings.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/processors/wallets/worldcoin/test_bindings.py ipfs_datasets_py/tests/unit/test_data_wallet.py
- Acceptance: Old snapshots load and new snapshots round-trip through delegators; challenge verification binds nonce, signal/context, action, environment, credential policy, presence, expiry, protocol, actor/provider context; configured HMAC protects durable replay commitments; raw nullifiers never persist/export; replay survives restart and uniqueness is atomic; revoked/expired bindings cannot yield active verified receipts; v3 is never labeled v4; minimum-necessary projections require caller authorization.
- Gap task: Extract one World-specific service slice at a time while keeping existing DataWalletService tests green.
- Refinement: `wallet/service.py` has one owner for this bundle; other lanes must not edit it.
- Embedding query: world id binding durable challenge replay hmac proof receipt snapshot revoke expiry data wallet
- AST query: WorldIdBinding add_world_id_binding _create_world_id_proof_receipt world_id_private_nullifiers
- Goal completion schema version: 1
- Completion confidence: 0.166667
- Uncovered criteria: ["Old snapshots load and new snapshots round-trip through delegators","challenge verification binds nonce, signal/context, action, environment, credential policy, presence, expiry, protocol, actor/provider context","configured HMAC protects durable replay commitments","raw nullifiers never persist/export","replay survives restart and uniqueness is atomic","revoked/expired bindings cannot yield active verified receipts","v3 is never labeled v4","minimum-necessary projections require caller authorization."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []

## WALPROC-G120 Compose World Chain and WLD through Ethereum

- Status: active
- Parent: WALPROC-G000
- Fib priority: 34
- Priority: P1
- Track: worldcoin
- Bundle: wallet-processors/worldcoin
- Depends on: WALPROC-G100, WALPROC-G300
- Goal: Add World Chain configuration and WLD asset manifests as a strict composition layer over the Ethereum processor, not a duplicate EVM implementation.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin/world_chain.py, ipfs_datasets_py/tests/unit/processors/wallets/worldcoin/test_world_chain.py
- Outputs: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin/world_chain.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin/assets.py, ipfs_datasets_py/tests/unit/processors/wallets/worldcoin/test_world_chain.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/processors/wallets/worldcoin/test_world_chain.py
- Acceptance: Chain IDs 480 and 4801 and genesis/network identity are validated; WLD asset identity is network/contract bound; Ethereum parsing is reused; included, operationally confirmed, safe, finalized, and optional L1-settled states are distinct; block depth alone is not called finality; no SIWE bootstrap placeholder is promoted.
- Gap task: Implement World Chain descriptors, WLD manifests, and EVM composition fixtures.
- Refinement: Future SIWE is a separate reviewed child objective.
- Embedding query: world chain 480 4801 wld ethereum composition finality l1 settlement
- AST query: WorldChainProcessor EthereumWalletProcessor AssetRef Finality
- Goal completion schema version: 1
- Completion confidence: 0.166667
- Uncovered criteria: ["Chain IDs 480 and 4801 and genesis/network identity are validated","WLD asset identity is network/contract bound","Ethereum parsing is reused","included, operationally confirmed, safe, finalized, and optional L1-settled states are distinct","block depth alone is not called finality","no SIWE bootstrap placeholder is promoted."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []

## WALPROC-G130 Cut 211-AI over to a thin Worldcoin wrapper

- Status: active
- Parent: WALPROC-G000
- Fib priority: 55
- Priority: P0
- Track: worldcoin-cutover
- Bundle: wallet-processors/wrapper
- Depends on: WALPROC-G100, WALPROC-G110, WALPROC-G120
- Goal: Replace wallet_interface/world_id.py with compatibility exports and reduce WalletInterfaceService World ID methods to application authorization, policy, persistence, and response adapters delegating to ipfs_datasets_py.
- Evidence: tests/test_world_id_wrapper_ownership.py, tests/test_world_id_wallet.py, tests/test_world_id_wallet_api.py, wallet_interface/world_id.py
- Outputs: wallet_interface/world_id.py, wallet_interface/app_service.py, wallet_interface/ops.py, tests/test_world_id_wrapper_ownership.py, tests/test_world_id_wallet.py, tests/test_world_id_wallet_api.py
- Validation: python -m pytest -q tests/test_world_id_wrapper_ownership.py tests/test_world_id_wallet.py tests/test_world_id_wallet_api.py
- Acceptance: Old documented imports and exception identities remain for the deprecation window; route paths/DTOs remain stable; wrapper has explicit __all__ and no crypto, hashing, HTTP, endpoint literal, secret resolution, proof parsing, normalization, redaction, binding, replay, or proof implementation; status is authenticated/minimum necessary; readiness probes delegate; provider/actor application policy remains in 211-AI.
- Gap task: Add ownership static test, switch imports/delegation, then delete duplicate implementation.
- Refinement: `wallet_interface/app_service.py` has one cutover owner; UI migration is a later child if needed.
- Embedding query: 211 ai world id thin wrapper compatibility reexport app service delegation ownership static test
- AST query: WalletInterfaceService create_world_id_rp_signature register_world_id_verification
- Goal completion schema version: 1
- Completion confidence: 0.166667
- Uncovered criteria: ["Old documented imports and exception identities remain for the deprecation window","route paths/DTOs remain stable","wrapper has explicit __all__ and no crypto, hashing, HTTP, endpoint literal, secret resolution, proof parsing, normalization, redaction, binding, replay, or proof implementation","status is authenticated/minimum necessary","readiness probes delegate","provider/actor application policy remains in 211-AI."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []

## WALPROC-G200 Implement the reusable XRPL ledger processor

- Status: active
- Parent: WALPROC-G000
- Fib priority: 21
- Priority: P0
- Track: xrpl
- Bundle: wallet-processors/xaman
- Depends on: WALPROC-G040, WALPROC-G060, WALPROC-G070, WALPROC-G080, WALPROC-G090
- Goal: Implement XRPL address/account, `account_tx` pagination, transactions plus metadata, delivered amount, XRP and issued-currency/trustline assets, destination tags, memos, sequence, validated-ledger checkpoints, normalization, and export.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/xrpl, ipfs_datasets_py/tests/unit/processors/wallets/xrpl, ipfs_datasets_py/tests/fixtures/wallets/xrpl
- Outputs: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/xrpl, ipfs_datasets_py/tests/unit/processors/wallets/xrpl, ipfs_datasets_py/tests/fixtures/wallets/xrpl
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/processors/wallets/xrpl ipfs_datasets_py/tests/contract/processors/wallets/test_xrpl_conformance.py
- Acceptance: Marker pagination has no gaps/duplicates; only validated results are final; ledger hash/index continuity anchors checkpoints; partial-payment delivered_amount is correct; issued asset identity includes currency and issuer; tags/memos are preserved under privacy policy; failed/unvalidated/unknown outcomes remain distinct; no signing/submission capability exists.
- Gap task: Build fixtures first, then provider, normalizer, finality, and conformance adapter.
- Refinement: Keep Xaman wallet payload concerns out of the XRPL ledger provider.
- Embedding query: xrpl account tx marker validated ledger delivered amount issued currency trustline destination tag memo
- AST query: XRPLLedgerProvider XRPLNormalizer delivered_amount
- Goal completion schema version: 1
- Completion confidence: 0.166667
- Uncovered criteria: ["Marker pagination has no gaps/duplicates","only validated results are final","ledger hash/index continuity anchors checkpoints","partial-payment delivered_amount is correct","issued asset identity includes currency and issuer","tags/memos are preserved under privacy policy","failed/unvalidated/unknown outcomes remain distinct","no signing/submission capability exists."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []

## WALPROC-G210 Implement Xaman wallet and payload processing over XRPL

- Status: active
- Parent: WALPROC-G000
- Fib priority: 34
- Priority: P0
- Track: xaman
- Bundle: wallet-processors/xaman
- Depends on: WALPROC-G020, WALPROC-G200
- Goal: Implement Xaman wallet/payload metadata ingestion, payload lifecycle normalization, account activity correlation, redacted export, and ledger settlement verification by composing the XRPL processor.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/xaman, ipfs_datasets_py/tests/unit/processors/wallets/xaman, ipfs_datasets_py/tests/fixtures/wallets/xaman
- Outputs: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/xaman, ipfs_datasets_py/tests/unit/processors/wallets/xaman, ipfs_datasets_py/tests/fixtures/wallets/xaman
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/processors/wallets/xaman ipfs_datasets_py/tests/contract/processors/wallets/test_xaman_conformance.py
- Acceptance: Created/opened/signed/rejected/expired/cancelled/submitted/validated/failed/unknown states remain distinct; Xaman API success is never settlement; transaction facts are verified through XRPL; network/account/payload identity is bound; memos and payload content follow redaction/size policy; processor cannot approve, sign, or submit.
- Gap task: Implement typed lifecycle/payload fixtures and a read-only provider adapter over the XRPL processor.
- Refinement: Xaman and XRPL may share a bundle but keep separate public modules.
- Embedding query: xaman payload lifecycle xrpl wallet account activity settlement validation redacted export
- AST query: XamanWalletProcessor XamanPayload PayloadStatus
- Goal completion schema version: 1
- Completion confidence: 0.166667
- Uncovered criteria: ["Created/opened/signed/rejected/expired/cancelled/submitted/validated/failed/unknown states remain distinct","Xaman API success is never settlement","transaction facts are verified through XRPL","network/account/payload identity is bound","memos and payload content follow redaction/size policy","processor cannot approve, sign, or submit."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []

## WALPROC-G220 Link Xaman runtime records to formal assurance without coupling

- Status: active
- Parent: WALPROC-G000
- Fib priority: 55
- Priority: P1
- Track: xaman-assurance
- Bundle: wallet-processors/xaman-assurance
- Depends on: WALPROC-G210
- Goal: Preserve Xaman formal/security models under logic, remove any duplicated runtime normalization only after a compatibility audit, and add a narrow projection/conformance bridge from runtime records to assurance inputs.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/xaman/assurance.py, ipfs_datasets_py/tests/contract/processors/wallets/test_xaman_assurance_bridge.py, ipfs_datasets_py/docs/security_verification/xaman_wallet_processor_mapping.md
- Outputs: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/xaman/assurance.py, ipfs_datasets_py/tests/contract/processors/wallets/test_xaman_assurance_bridge.py, ipfs_datasets_py/docs/security_verification/xaman_wallet_processor_mapping.md
- Validation: python -m pytest -q ipfs_datasets_py/tests/contract/processors/wallets/test_xaman_assurance_bridge.py
- Acceptance: Runtime imports no proof tool, report generator, archive corpus, Firebase, native vault, or device harness; formal modules stay at existing paths unless separately mapped; projection covers network binding, payload lifecycle, signing decision, submission, and finality assumptions; assurance status is not runtime authorization or release proof.
- Gap task: Document mapping and add one-way projection tests without moving formal reports.
- Refinement: Treat formal artifact relocation as a separate task only if the inventory proves true runtime duplication.
- Embedding query: xaman runtime formal assurance bridge security model no coupling
- AST query: xaman_source_extractor XamanWalletProcessor SecurityModelIR
- Goal completion schema version: 1
- Completion confidence: 0.166667
- Uncovered criteria: ["Runtime imports no proof tool, report generator, archive corpus, Firebase, native vault, or device harness","formal modules stay at existing paths unless separately mapped","projection covers network binding, payload lifecycle, signing decision, submission, and finality assumptions","assurance status is not runtime authorization or release proof."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []

## WALPROC-G300 Implement Ethereum/EVM wallet and ledger processing

- Status: active
- Parent: WALPROC-G000
- Fib priority: 21
- Priority: P0
- Track: ethereum
- Bundle: wallet-processors/ethereum
- Depends on: WALPROC-G040, WALPROC-G060, WALPROC-G070, WALPROC-G080, WALPROC-G090
- Goal: Implement chain/genesis validation, account/balance/history, blocks, legacy and EIP-1559 transactions, receipts, native transfers, contract creation, logs, ERC-20/721/1155 transfers, optional trace capability, removed logs, finality, reorgs, and exports.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/ethereum, ipfs_datasets_py/tests/unit/processors/wallets/ethereum, ipfs_datasets_py/tests/fixtures/wallets/ethereum
- Outputs: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/ethereum, ipfs_datasets_py/tests/unit/processors/wallets/ethereum, ipfs_datasets_py/tests/fixtures/wallets/ethereum
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/processors/wallets/ethereum ipfs_datasets_py/tests/contract/processors/wallets/test_ethereum_conformance.py
- Acceptance: eth_chainId and genesis bind provider identity; amounts/fees are exact; reverted receipts and removed logs are preserved; event IDs are stable; ERC standards decode from logs; traces/internal value are labeled optional/incomplete when unavailable; safe/finalized tags are preferred with explicit confirmation fallback; reorg replay emits corrections; read-only interface has no signer/broadcaster.
- Gap task: Land fixture-driven RPC client, normalizer/log decoder, token projection, finality policy, and conformance adapter within the Ethereum package.
- Refinement: Token metadata lookup is optional and cannot block transfer ingestion.
- Embedding query: ethereum evm eip1559 receipts logs erc20 erc721 erc1155 safe finalized reorg
- AST query: EthereumLedgerProvider EthereumNormalizer decode_transfer_log
- Goal completion schema version: 1
- Completion confidence: 0.166667
- Uncovered criteria: ["eth_chainId and genesis bind provider identity","amounts/fees are exact","reverted receipts and removed logs are preserved","event IDs are stable","ERC standards decode from logs","traces/internal value are labeled optional/incomplete when unavailable","safe/finalized tags are preferred with explicit confirmation fallback","reorg replay emits corrections","read-only interface has no signer/broadcaster."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []

## WALPROC-G400 Implement Bitcoin wallet and ledger processing

- Status: active
- Parent: WALPROC-G000
- Fib priority: 21
- Priority: P0
- Track: bitcoin
- Bundle: wallet-processors/bitcoin
- Depends on: WALPROC-G040, WALPROC-G060, WALPROC-G070, WALPROC-G080, WALPROC-G090
- Goal: Implement network/genesis-bound Bitcoin transaction, input/output, script/address descriptor, fee, UTXO create/spend, mempool/confirmed state, configurable confirmation finality, reorg rollback, balance, and export processing.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/bitcoin, ipfs_datasets_py/tests/unit/processors/wallets/bitcoin, ipfs_datasets_py/tests/fixtures/wallets/bitcoin
- Outputs: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/bitcoin, ipfs_datasets_py/tests/unit/processors/wallets/bitcoin, ipfs_datasets_py/tests/fixtures/wallets/bitcoin
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/processors/wallets/bitcoin ipfs_datasets_py/tests/contract/processors/wallets/test_bitcoin_conformance.py
- Acceptance: Legacy/SegWit/Taproot, coinbase, multi-input/output, spent/unspent, replacement, network mismatch, and reorg fixtures pass; UTXOs—not account debits—drive state; satoshi amounts are exact; ownership/change clustering is not asserted; confirmation threshold is policy not universal truth; reorg reverses UTXO effects; no PSBT/sign/broadcast capability exists.
- Gap task: Build descriptor/UTXO models, bounded RPC or Esplora-style provider, normalizer, finality/reorg, and conformance adapter.
- Refinement: Support one reviewed provider family first behind the common protocol.
- Embedding query: bitcoin utxo scripts segwit taproot coinbase mempool confirmation reorg wallet export
- AST query: BitcoinLedgerProvider UtxoRecord ScriptDescriptor
- Goal completion schema version: 1
- Completion confidence: 0.166667
- Uncovered criteria: ["Legacy/SegWit/Taproot, coinbase, multi-input/output, spent/unspent, replacement, network mismatch, and reorg fixtures pass","UTXOs\u2014not account debits\u2014drive state","satoshi amounts are exact","ownership/change clustering is not asserted","confirmation threshold is policy not universal truth","reorg reverses UTXO effects","no PSBT/sign/broadcast capability exists."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []

## WALPROC-G500 Implement Solana wallet and ledger processing

- Status: active
- Parent: WALPROC-G000
- Fib priority: 21
- Priority: P0
- Track: solana
- Bundle: wallet-processors/solana
- Depends on: WALPROC-G040, WALPROC-G060, WALPROC-G070, WALPROC-G080, WALPROC-G090
- Goal: Implement cluster/genesis-bound account/signature pagination, legacy/versioned transactions, address lookup tables, outer/inner instructions, program logs, lamport/SPL transfers, token accounts/balances, failed transactions, commitment/finality, skipped slots, checkpoints, and exports.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/solana, ipfs_datasets_py/tests/unit/processors/wallets/solana, ipfs_datasets_py/tests/fixtures/wallets/solana
- Outputs: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/solana, ipfs_datasets_py/tests/unit/processors/wallets/solana, ipfs_datasets_py/tests/fixtures/wallets/solana
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/processors/wallets/solana ipfs_datasets_py/tests/contract/processors/wallets/test_solana_conformance.py
- Acceptance: Signature pagination has no gaps/duplicates; versioned messages and lookup tables resolve deterministically; failed txs remain visible; inner instructions are indexed distinctly; lamport/SPL amounts are exact; processed/confirmed/finalized remain distinct; skipped/missing slots do not silently advance; finalized slot/blockhash anchors checkpoints; no transaction signing/submission exists.
- Gap task: Build offline fixtures, bounded JSON-RPC provider, instruction/token normalizers, finality, and conformance adapter.
- Refinement: NFT enrichment is an optional projection over token records, not a core ingestion dependency.
- Embedding query: solana signatures versioned transaction address lookup inner instruction spl token commitment skipped slot
- AST query: SolanaLedgerProvider SolanaNormalizer TokenAccountRecord
- Goal completion schema version: 1
- Completion confidence: 0.166667
- Uncovered criteria: ["Signature pagination has no gaps/duplicates","versioned messages and lookup tables resolve deterministically","failed txs remain visible","inner instructions are indexed distinctly","lamport/SPL amounts are exact","processed/confirmed/finalized remain distinct","skipped/missing slots do not silently advance","finalized slot/blockhash anchors checkpoints","no transaction signing/submission exists."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []

## WALPROC-G600 Publish lazy registry and one generic processor adapter

- Status: active
- Parent: WALPROC-G000
- Fib priority: 55
- Priority: P1
- Track: integration
- Bundle: wallet-processors/integration
- Depends on: WALPROC-G030, WALPROC-G100, WALPROC-G200, WALPROC-G300, WALPROC-G400, WALPROC-G500
- Goal: Publish a lazy wallet processor registry/factory and exactly one compatibility adapter to the canonical generic processor contract selected by the ADR.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/registry.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/adapters/processor_protocol.py, ipfs_datasets_py/tests/unit/processors/wallets/test_registry.py
- Outputs: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/registry.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/adapters, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/__init__.py, ipfs_datasets_py/tests/unit/processors/wallets/test_registry.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/processors/wallets/test_registry.py
- Acceptance: Chain providers load lazily; capabilities are explicit; unknown/ambiguous networks fail; optional dependency errors identify the extra without auto-installing; one generic adapter exists and the rejected registry surface is not also wired; root processor imports remain lightweight; Xaman composes XRPL and World Chain composes Ethereum.
- Gap task: Add registry/factory, lazy exports, and the ADR-selected compatibility adapter.
- Refinement: Integration owner alone edits shared package __init__ and registry files.
- Embedding query: lazy wallet processor registry factory generic adapter optional dependencies capabilities
- AST query: WalletProcessorRegistry get_wallet_processor
- Goal completion schema version: 1
- Completion confidence: 0.166667
- Uncovered criteria: ["Chain providers load lazily","capabilities are explicit","unknown/ambiguous networks fail","optional dependency errors identify the extra without auto-installing","one generic adapter exists and the rejected registry surface is not also wired","root processor imports remain lightweight","Xaman composes XRPL and World Chain composes Ethereum."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []

## WALPROC-G610 Add bounded Python, CLI, and MCP ingest/export surfaces

- Status: active
- Parent: WALPROC-G000
- Fib priority: 89
- Priority: P1
- Track: integration
- Bundle: wallet-processors/integration
- Depends on: WALPROC-G080, WALPROC-G600
- Goal: Expose consistent Python facade, CLI commands, and MCP tools for wallet and finite ledger-range ingest/export, resume, status, capabilities, and manifest verification.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/api.py, ipfs_datasets_py/ipfs_datasets_py/mcp_server/tools/wallet_processor_tools, ipfs_datasets_py/tests/mcp/test_wallet_processor_tools.py
- Outputs: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/api.py, ipfs_datasets_py/ipfs_datasets_py/cli/wallets.py, ipfs_datasets_py/ipfs_datasets_py/mcp_server/tools/wallet_processor_tools, ipfs_datasets_py/tests/mcp/test_wallet_processor_tools.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/mcp/test_wallet_processor_tools.py ipfs_datasets_py/tests/unit/processors/wallets/test_api.py
- Acceptance: Surfaces share typed requests/results; every scan has finite range/item/byte/time/retry bounds; provider URLs and secret values cannot be supplied by untrusted MCP requests outside allowlists; default export is finalized; provisional/raw modes are explicit; no signing/broadcast verb exists; status/receipts exclude wallet payload and secrets.
- Gap task: Implement Python API first, then thin CLI/MCP adapters and parity tests.
- Refinement: Reuse existing MCP registration conventions without importing all chain extras.
- Embedding query: wallet processor python cli mcp ingest export resume status capabilities bounded
- AST query: WalletProcessorAPI wallet_ingest wallet_export
- Goal completion schema version: 1
- Completion confidence: 0.166667
- Uncovered criteria: ["Surfaces share typed requests/results","every scan has finite range/item/byte/time/retry bounds","provider URLs and secret values cannot be supplied by untrusted MCP requests outside allowlists","default export is finalized","provisional/raw modes are explicit","no signing/broadcast verb exists","status/receipts exclude wallet payload and secrets."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []

## WALPROC-G620 Prove cross-chain conformance and differential compatibility

- Status: active
- Parent: WALPROC-G000
- Fib priority: 89
- Priority: P0
- Track: validation
- Bundle: wallet-processors/conformance
- Depends on: WALPROC-G110, WALPROC-G120, WALPROC-G210, WALPROC-G300, WALPROC-G400, WALPROC-G500, WALPROC-G600
- Goal: Run shared conformance across all processors, old/new World ID differential vectors and snapshots, cross-chain schema queries, and two clean full validation passes.
- Evidence: ipfs_datasets_py/tests/contract/processors/wallets/test_all_processors.py, ipfs_datasets_py/tests/contract/processors/wallets/test_worldcoin_differential.py, data/wallet_processor_migration/validation/conformance-report.json
- Outputs: ipfs_datasets_py/tests/contract/processors/wallets/test_all_processors.py, ipfs_datasets_py/tests/contract/processors/wallets/test_worldcoin_differential.py, data/wallet_processor_migration/validation/conformance-report.json
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/processors/wallets ipfs_datasets_py/tests/contract/processors/wallets
- Acceptance: Five families pass the same contract without exemptions hiding required behavior; old/new safe World ID results and snapshots match; known unsafe baseline cases now fail closed; normalized queries preserve chain identity and exact quantities; no import/network/secret regressions; report records two consecutive clean current-tree runs and dependency versions.
- Gap task: Parameterize every processor through conformance and generate a deterministic report.
- Refinement: A failing chain creates a scoped repair task in that chain bundle.
- Embedding query: all wallet processors conformance world id differential snapshot cross chain schema
- AST query: WalletProcessorConformance
- Goal completion schema version: 1
- Completion confidence: 0.166667
- Uncovered criteria: ["Five families pass the same contract without exemptions hiding required behavior","old/new safe World ID results and snapshots match","known unsafe baseline cases now fail closed","normalized queries preserve chain identity and exact quantities","no import/network/secret regressions","report records two consecutive clean current-tree runs and dependency versions."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []

## WALPROC-G630 Complete privacy, threat-model, and secret-leak review

- Status: active
- Parent: WALPROC-G000
- Fib priority: 89
- Priority: P0
- Track: security
- Bundle: wallet-processors/security
- Depends on: WALPROC-G060, WALPROC-G080, WALPROC-G110, WALPROC-G210, WALPROC-G300, WALPROC-G400, WALPROC-G500
- Goal: Threat-model public-ledger profiling, World ID/nullifier handling, Xaman payloads, raw data, endpoints, provider keys, exports, checkpoints, logs, denial-of-service, SSRF, and future custody boundary; add enforceable negative tests.
- Evidence: ipfs_datasets_py/docs/security/WALLET_PROCESSOR_THREAT_MODEL.md, ipfs_datasets_py/tests/security/test_wallet_processor_secrets.py, ipfs_datasets_py/tests/security/test_wallet_processor_bounds.py
- Outputs: ipfs_datasets_py/docs/security/WALLET_PROCESSOR_THREAT_MODEL.md, ipfs_datasets_py/tests/security/test_wallet_processor_secrets.py, ipfs_datasets_py/tests/security/test_wallet_processor_bounds.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/security/test_wallet_processor_secrets.py ipfs_datasets_py/tests/security/test_wallet_processor_bounds.py
- Acceptance: No seed/private/signing material is accepted by canonical models; public data is treated as potentially personal; identity clustering is absent; raw/memo/calldata/instruction storage is opt-in/bounded/redacted; SSRF and decompression/body/page/range abuse fail; secrets/full endpoints are absent from every serialization/log/error/receipt; signing/broadcast remain explicitly denied future capabilities.
- Gap task: Write threat model, scan serializers/logging, and add adversarial bounds/no-leak tests.
- Refinement: Critical findings block release and generate scoped repair goals.
- Embedding query: wallet public ledger privacy threat model nullifier payload secrets ssrf dos raw data custody
- AST query: redact SecretResolver RawPayloadStore
- Goal completion schema version: 1
- Completion confidence: 0.166667
- Uncovered criteria: ["No seed/private/signing material is accepted by canonical models","public data is treated as potentially personal","identity clustering is absent","raw/memo/calldata/instruction storage is opt-in/bounded/redacted","SSRF and decompression/body/page/range abuse fail","secrets/full endpoints are absent from every serialization/log/error/receipt","signing/broadcast remain explicitly denied future capabilities."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []

## WALPROC-G640 Add metrics, benchmarks, and operational runbooks

- Status: active
- Parent: WALPROC-G000
- Fib priority: 144
- Priority: P2
- Track: operations
- Bundle: wallet-processors/operations
- Depends on: WALPROC-G080, WALPROC-G620
- Goal: Add payload-free structured metrics/run receipts, deterministic fixture benchmarks, resource budgets, checkpoint/head-lag and reorg observability, optional live-smoke controls, and recovery runbooks.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/metrics.py, ipfs_datasets_py/benchmarks/wallet_processors, ipfs_datasets_py/docs/operations/WALLET_PROCESSOR_RUNBOOK.md
- Outputs: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/metrics.py, ipfs_datasets_py/benchmarks/wallet_processors, ipfs_datasets_py/docs/operations/WALLET_PROCESSOR_RUNBOOK.md
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/processors/wallets/test_metrics.py && python ipfs_datasets_py/benchmarks/wallet_processors/run.py --fixture-only
- Acceptance: Metrics cover calls/retries/throttles/bytes/records/errors/checkpoint age/head lag/rewinds/finality/throughput without addresses/payloads/secrets; benchmark reports records/sec and peak memory on fixed fixtures; operational bounds and recovery from crash/CAS/reorg/provider mismatch are documented; live smoke is disabled unless explicit endpoint and network approval are supplied.
- Gap task: Instrument shared pipeline and add a deterministic small benchmark plus recovery runbook.
- Refinement: Do not set performance budgets from live provider latency alone.
- Embedding query: wallet processor metrics benchmark checkpoint lag reorg throughput operations runbook
- AST query: WalletProcessorMetrics IngestRunReceipt
- Goal completion schema version: 1
- Completion confidence: 0.166667
- Uncovered criteria: ["Metrics cover calls/retries/throttles/bytes/records/errors/checkpoint age/head lag/rewinds/finality/throughput without addresses/payloads/secrets","benchmark reports records/sec and peak memory on fixed fixtures","operational bounds and recovery from crash/CAS/reorg/provider mismatch are documented","live smoke is disabled unless explicit endpoint and network approval are supplied."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []

## WALPROC-G700 Finish packaging, schemas, examples, and migration documentation

- Status: active
- Parent: WALPROC-G000
- Fib priority: 144
- Priority: P1
- Track: release
- Bundle: wallet-processors/release
- Depends on: WALPROC-G050, WALPROC-G610, WALPROC-G620, WALPROC-G630
- Goal: Publish API/schema/reference docs, per-chain examples, dependency extras, compatibility/import map, data migration, privacy guidance, version matrix, changelog, and rollback procedure.
- Evidence: ipfs_datasets_py/docs/wallet_processors/README.md, ipfs_datasets_py/examples/wallet_processors, docs/planning/WALLET_PROCESSORS_MIGRATION_PLAN.md
- Outputs: ipfs_datasets_py/docs/wallet_processors, ipfs_datasets_py/examples/wallet_processors, ipfs_datasets_py/README.md, ipfs_datasets_py/CHANGELOG.md, docs/planning/WALLET_PROCESSORS_MIGRATION_PLAN.md
- Validation: python -m pytest -q ipfs_datasets_py/tests/contract/processors/wallets/test_documented_examples.py
- Acceptance: Docs distinguish World ID/World Chain/WLD and Xaman/XRPL; examples are offline or require explicit network opt-in; import and schema migration windows are stated; extras and capability gaps are documented; no example signs/broadcasts or embeds a real address/key; rollback covers target package version and outer gitlink/wrapper.
- Gap task: Build docs from verified public APIs and execute every documented example against fixtures.
- Refinement: Shared docs have one release owner after chain docs land.
- Embedding query: wallet processors documentation examples schema migration compatibility rollback worldcoin xaman
- AST query: __all__
- Goal completion schema version: 1
- Completion confidence: 0.166667
- Uncovered criteria: ["Docs distinguish World ID/World Chain/WLD and Xaman/XRPL","examples are offline or require explicit network opt-in","import and schema migration windows are stated","extras and capability gaps are documented","no example signs/broadcasts or embeds a real address/key","rollback covers target package version and outer gitlink/wrapper."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []

## WALPROC-G710 Perform staged 211-AI cutover and release validation

- Status: active
- Parent: WALPROC-G000
- Fib priority: 233
- Priority: P0
- Track: release
- Bundle: wallet-processors/release
- Depends on: WALPROC-G130, WALPROC-G620, WALPROC-G630, WALPROC-G640, WALPROC-G700
- Goal: Release and pin ipfs_datasets_py first, update the 211-AI submodule pointer and wrapper, run backend/UI/Playwright/snapshot/import checks, prove rollback, and retain aliases for one documented compatibility release.
- Evidence: data/wallet_processor_migration/release/cutover-receipt.json, docs/runbooks/WALLET_PROCESSOR_CUTOVER.md, tests/test_world_id_wrapper_ownership.py
- Outputs: data/wallet_processor_migration/release/cutover-receipt.json, docs/runbooks/WALLET_PROCESSOR_CUTOVER.md, ipfs_datasets_py, wallet_interface/world_id.py
- Validation: python -m pytest -q tests/test_world_id_wrapper_ownership.py tests/test_world_id_wallet.py tests/test_world_id_wallet_api.py && npm --prefix wallet_interface/ui test -- --runInBand
- Acceptance: Target package commit and outer gitlink are recorded; two clean target validation runs and application tests pass; UI uses the typed client and exposes no raw-nullifier DTO where migrated; production defaults are fail closed; old implementation is absent; wrapper aliases have an expiry version; rollback to the prior gitlink/wrapper is rehearsed without dataset loss.
- Gap task: Execute staged release checklist and write a tree-bound receipt; do not enable production endpoints automatically.
- Refinement: Playwright/live signoff may be recorded as an external blocker when required infrastructure is unavailable.
- Embedding query: staged cutover release ipfs datasets submodule pin 211 ai wrapper ui playwright rollback
- AST query: create_world_id_router WorldIdVerificationPanel
- Goal completion schema version: 1
- Completion confidence: 0.166667
- Uncovered criteria: ["Target package commit and outer gitlink are recorded","two clean target validation runs and application tests pass","UI uses the typed client and exposes no raw-nullifier DTO where migrated","production defaults are fail closed","old implementation is absent","wrapper aliases have an expiry version","rollback to the prior gitlink/wrapper is rehearsed without dataset loss."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []

## WALPROC-G800 Operate dual-provider agent supervision with bounded refill

- Status: active
- Parent: WALPROC-G000
- Fib priority: 4
- Priority: P0
- Track: autonomous-execution
- Bundle: wallet-processors/control
- Depends on: WALPROC-G010
- Goal: Generate canonical goals/subgoals/tasks/bundles from this heap, drain deterministic shards concurrently with ChatGPT Codex and Grok Build in isolated worktrees, refill from unsatisfied evidence, and preserve bounded retry/dependency/reconciliation controls.
- Evidence: data/wallet_processor_migration/agent_supervisor/objective_graph.json, data/wallet_processor_migration/agent_supervisor/bundles/index.json, data/wallet_processor_migration/agent_supervisor/runtime/supervisor-health.json
- Outputs: data/wallet_processor_migration/agent_supervisor, docs/planning/WALLET_PROCESSORS_TODO.md, scripts/wallet_processor_migration_supervisor.sh
- Validation: scripts/wallet_processor_migration_supervisor.sh status
- Acceptance: Objective graph and task board contain stable goal/task identities and dependencies; Codex and Grok supervisors use shard 0/2 and 1/2, separate state/worktrees/logs, the shared integration branch and merge queue, and `--worktree-submodule-path ipfs_datasets_py`; only the control lane refills; protected plan/heap files are read-only to agents; PID, command line, heartbeat, events, and child daemon health are verified; retries stop at the budget and generate repair/blocker work.
- Gap task: Add a small start/stop/status wrapper around packaged agent-supervisor modules, seed artifacts, start both provider lanes, and record health.
- Refinement: Supervisor automation may manage generated todo/state artifacts but cannot authorize network, credentials, dependency installation, signing, broadcasting, production config, or release approval.
- Embedding query: ipfs accelerate agent supervisor codex grok parallel shards objective refill wallet processors
- AST query: PortalImplementationSupervisor objective_daemon task_shard_count
- Goal completion schema version: 1
- Completion confidence: 0.166667
- Uncovered criteria: ["Objective graph and task board contain stable goal/task identities and dependencies","Codex and Grok supervisors use shard 0/2 and 1/2, separate state/worktrees/logs, the shared integration branch and merge queue, and `--worktree-submodule-path ipfs_datasets_py`","only the control lane refills","protected plan/heap files are read-only to agents","PID, command line, heartbeat, events, and child daemon health are verified","retries stop at the budget and generate repair/blocker work."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []

## WALPROC-G801 Prove WALPROC-G060 for Deliver reusable, safe multi-chain wallet processors

- Status: active
- Parent: WALPROC-G000
- Fib priority: 3000
- Track: wallet-processors-program
- Priority: P0
- Bundle: wallet-processors/control
- Goal: Create concrete implementation, tests, docs, or interface descriptors proving `WALPROC-G060`.
- Evidence: WALPROC-G060
- Outputs: ipfs_datasets_py/ipfs_datasets_py/processors/wallets, wallet_interface/world_id.py, docs/planning/WALLET_PROCESSORS_MIGRATION_PLAN.md
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/processors/wallets ipfs_datasets_py/tests/contract/processors/wallets tests/test_world_id_wallet.py tests/test_world_id_wallet_api.py
- Refinement depth: 1
- Embedding query: WALPROC-G060
- AST query: WALPROC-G060
- Parallel lane: wallet-processors/control
- Conflict policy: prefer bundle-local changes; invoke the LLM merge resolver for semantic conflicts
- Gap task: Close the missing objective evidence `WALPROC-G060` with a narrow, verifiable change.

## WALPROC-G802 Prove WALPROC-G070 for Deliver reusable, safe multi-chain wallet processors

- Status: active
- Parent: WALPROC-G000
- Fib priority: 3001
- Track: wallet-processors-program
- Priority: P0
- Bundle: wallet-processors/control
- Goal: Create concrete implementation, tests, docs, or interface descriptors proving `WALPROC-G070`.
- Evidence: WALPROC-G070
- Outputs: ipfs_datasets_py/ipfs_datasets_py/processors/wallets, wallet_interface/world_id.py, docs/planning/WALLET_PROCESSORS_MIGRATION_PLAN.md
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/processors/wallets ipfs_datasets_py/tests/contract/processors/wallets tests/test_world_id_wallet.py tests/test_world_id_wallet_api.py
- Refinement depth: 1
- Embedding query: WALPROC-G070
- AST query: WALPROC-G070
- Parallel lane: wallet-processors/control
- Conflict policy: prefer bundle-local changes; invoke the LLM merge resolver for semantic conflicts
- Gap task: Close the missing objective evidence `WALPROC-G070` with a narrow, verifiable change.

## WALPROC-G803 Prove WALPROC-G080 for Deliver reusable, safe multi-chain wallet processors

- Status: active
- Parent: WALPROC-G000
- Fib priority: 3002
- Track: wallet-processors-program
- Priority: P0
- Bundle: wallet-processors/control
- Goal: Create concrete implementation, tests, docs, or interface descriptors proving `WALPROC-G080`.
- Evidence: WALPROC-G080
- Outputs: ipfs_datasets_py/ipfs_datasets_py/processors/wallets, wallet_interface/world_id.py, docs/planning/WALLET_PROCESSORS_MIGRATION_PLAN.md
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/processors/wallets ipfs_datasets_py/tests/contract/processors/wallets tests/test_world_id_wallet.py tests/test_world_id_wallet_api.py
- Refinement depth: 1
- Embedding query: WALPROC-G080
- AST query: WALPROC-G080
- Parallel lane: wallet-processors/control
- Conflict policy: prefer bundle-local changes; invoke the LLM merge resolver for semantic conflicts
- Gap task: Close the missing objective evidence `WALPROC-G080` with a narrow, verifiable change.

## WALPROC-G804 Prove WALPROC-G090 for Deliver reusable, safe multi-chain wallet processors

- Status: active
- Parent: WALPROC-G000
- Fib priority: 3000
- Track: wallet-processors-program
- Priority: P0
- Bundle: wallet-processors/control
- Goal: Create concrete implementation, tests, docs, or interface descriptors proving `WALPROC-G090`.
- Evidence: WALPROC-G090
- Outputs: ipfs_datasets_py/ipfs_datasets_py/processors/wallets, wallet_interface/world_id.py, docs/planning/WALLET_PROCESSORS_MIGRATION_PLAN.md
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/processors/wallets ipfs_datasets_py/tests/contract/processors/wallets tests/test_world_id_wallet.py tests/test_world_id_wallet_api.py
- Refinement depth: 1
- Embedding query: WALPROC-G090
- AST query: WALPROC-G090
- Parallel lane: wallet-processors/control
- Conflict policy: prefer bundle-local changes; invoke the LLM merge resolver for semantic conflicts
- Gap task: Close the missing objective evidence `WALPROC-G090` with a narrow, verifiable change.

## WALPROC-G805 Prove WALPROC-G100 for Deliver reusable, safe multi-chain wallet processors

- Status: active
- Parent: WALPROC-G000
- Fib priority: 3001
- Track: wallet-processors-program
- Priority: P0
- Bundle: wallet-processors/control
- Goal: Create concrete implementation, tests, docs, or interface descriptors proving `WALPROC-G100`.
- Evidence: WALPROC-G100
- Outputs: ipfs_datasets_py/ipfs_datasets_py/processors/wallets, wallet_interface/world_id.py, docs/planning/WALLET_PROCESSORS_MIGRATION_PLAN.md
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/processors/wallets ipfs_datasets_py/tests/contract/processors/wallets tests/test_world_id_wallet.py tests/test_world_id_wallet_api.py
- Refinement depth: 1
- Embedding query: WALPROC-G100
- AST query: WALPROC-G100
- Parallel lane: wallet-processors/control
- Conflict policy: prefer bundle-local changes; invoke the LLM merge resolver for semantic conflicts
- Gap task: Close the missing objective evidence `WALPROC-G100` with a narrow, verifiable change.

## WALPROC-G806 Prove WALPROC-G110 for Deliver reusable, safe multi-chain wallet processors

- Status: active
- Parent: WALPROC-G000
- Fib priority: 3002
- Track: wallet-processors-program
- Priority: P0
- Bundle: wallet-processors/control
- Goal: Create concrete implementation, tests, docs, or interface descriptors proving `WALPROC-G110`.
- Evidence: WALPROC-G110
- Outputs: ipfs_datasets_py/ipfs_datasets_py/processors/wallets, wallet_interface/world_id.py, docs/planning/WALLET_PROCESSORS_MIGRATION_PLAN.md
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/processors/wallets ipfs_datasets_py/tests/contract/processors/wallets tests/test_world_id_wallet.py tests/test_world_id_wallet_api.py
- Refinement depth: 1
- Embedding query: WALPROC-G110
- AST query: WALPROC-G110
- Parallel lane: wallet-processors/control
- Conflict policy: prefer bundle-local changes; invoke the LLM merge resolver for semantic conflicts
- Gap task: Close the missing objective evidence `WALPROC-G110` with a narrow, verifiable change.

## WALPROC-G807 Prove WALPROC-G300 for Deliver reusable, safe multi-chain wallet processors

- Status: active
- Parent: WALPROC-G000
- Fib priority: 3000
- Track: wallet-processors-program
- Priority: P0
- Bundle: wallet-processors/control
- Goal: Create concrete implementation, tests, docs, or interface descriptors proving `WALPROC-G300`.
- Evidence: WALPROC-G300
- Outputs: ipfs_datasets_py/ipfs_datasets_py/processors/wallets, wallet_interface/world_id.py, docs/planning/WALLET_PROCESSORS_MIGRATION_PLAN.md
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/processors/wallets ipfs_datasets_py/tests/contract/processors/wallets tests/test_world_id_wallet.py tests/test_world_id_wallet_api.py
- Refinement depth: 1
- Embedding query: WALPROC-G300
- AST query: WALPROC-G300
- Parallel lane: wallet-processors/control
- Conflict policy: prefer bundle-local changes; invoke the LLM merge resolver for semantic conflicts
- Gap task: Close the missing objective evidence `WALPROC-G300` with a narrow, verifiable change.

## WALPROC-G808 Prove WALPROC-G400 for Deliver reusable, safe multi-chain wallet processors

- Status: active
- Parent: WALPROC-G000
- Fib priority: 3001
- Track: wallet-processors-program
- Priority: P0
- Bundle: wallet-processors/control
- Goal: Create concrete implementation, tests, docs, or interface descriptors proving `WALPROC-G400`.
- Evidence: WALPROC-G400
- Outputs: ipfs_datasets_py/ipfs_datasets_py/processors/wallets, wallet_interface/world_id.py, docs/planning/WALLET_PROCESSORS_MIGRATION_PLAN.md
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/processors/wallets ipfs_datasets_py/tests/contract/processors/wallets tests/test_world_id_wallet.py tests/test_world_id_wallet_api.py
- Refinement depth: 1
- Embedding query: WALPROC-G400
- AST query: WALPROC-G400
- Parallel lane: wallet-processors/control
- Conflict policy: prefer bundle-local changes; invoke the LLM merge resolver for semantic conflicts
- Gap task: Close the missing objective evidence `WALPROC-G400` with a narrow, verifiable change.

## WALPROC-G809 Prove WALPROC-G500 for Deliver reusable, safe multi-chain wallet processors

- Status: active
- Parent: WALPROC-G000
- Fib priority: 3002
- Track: wallet-processors-program
- Priority: P0
- Bundle: wallet-processors/control
- Goal: Create concrete implementation, tests, docs, or interface descriptors proving `WALPROC-G500`.
- Evidence: WALPROC-G500
- Outputs: ipfs_datasets_py/ipfs_datasets_py/processors/wallets, wallet_interface/world_id.py, docs/planning/WALLET_PROCESSORS_MIGRATION_PLAN.md
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/processors/wallets ipfs_datasets_py/tests/contract/processors/wallets tests/test_world_id_wallet.py tests/test_world_id_wallet_api.py
- Refinement depth: 1
- Embedding query: WALPROC-G500
- AST query: WALPROC-G500
- Parallel lane: wallet-processors/control
- Conflict policy: prefer bundle-local changes; invoke the LLM merge resolver for semantic conflicts
- Gap task: Close the missing objective evidence `WALPROC-G500` with a narrow, verifiable change.

## WALPROC-G810 Prove data/wallet_processor_migration/agent_supervisor/objective_graph.json for Operate dual-provider agent supervision with bounded refill

- Status: active
- Parent: WALPROC-G800
- Fib priority: 5000
- Track: autonomous-execution
- Priority: P0
- Bundle: wallet-processors/control
- Goal: Create concrete implementation, tests, docs, or interface descriptors proving `data/wallet_processor_migration/agent_supervisor/objective_graph.json`.
- Evidence: data/wallet_processor_migration/agent_supervisor/objective_graph.json
- Outputs: data/wallet_processor_migration/agent_supervisor, docs/planning/WALLET_PROCESSORS_TODO.md, scripts/wallet_processor_migration_supervisor.sh
- Validation: scripts/wallet_processor_migration_supervisor.sh status
- Refinement depth: 2
- Embedding query: data/wallet_processor_migration/agent_supervisor/objective_graph.json
- AST query: data/wallet_processor_migration/agent_supervisor/objective_graph.json
- Parallel lane: wallet-processors/control
- Conflict policy: prefer bundle-local changes; invoke the LLM merge resolver for semantic conflicts
- Gap task: Close the missing objective evidence `data/wallet_processor_migration/agent_supervisor/objective_graph.json` with a narrow, verifiable change.

## WALPROC-G811 Prove ipfs_datasets_py/ipfs_datasets_py/processors/wallets/checkpoints.py for Goal packet aggregate for WALPROC-G070, WALPROC-G080

- Status: active
- Parent: WALPROC-G070
- Fib priority: 5000
- Track: shared-runtime
- Priority: P0
- Bundle: wallet-processors/pipeline
- Goal: Create concrete implementation, tests, docs, or interface descriptors proving `ipfs_datasets_py/ipfs_datasets_py/processors/wallets/checkpoints.py`.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/checkpoints.py
- Outputs: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/checkpoints.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/finality.py, ipfs_datasets_py/tests/unit/processors/wallets/test_checkpoints.py, ipfs_datasets_py/tests/unit/processors/wallets/test_reorgs.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/pipeline.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/storage.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/export.py, ipfs_datasets_py/tests/unit/processors/wallets/test_pipeline.py, ipfs_datasets_py/tests/unit/processors/wallets/test_export.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/processors/wallets/test_checkpoints.py ipfs_datasets_py/tests/unit/processors/wallets/test_reorgs.py
- Refinement depth: 2
- Embedding query: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/checkpoints.py
- AST query: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/checkpoints.py
- Parallel lane: wallet-processors/pipeline
- Conflict policy: prefer bundle-local changes; invoke the LLM merge resolver for semantic conflicts
- Gap task: Close the missing objective evidence `ipfs_datasets_py/ipfs_datasets_py/processors/wallets/checkpoints.py` with a narrow, verifiable change.

## WALPROC-G812 Prove ipfs_datasets_py/ipfs_datasets_py/processors/wallets/finality.py for Goal packet aggregate for WALPROC-G070, WALPROC-G080

- Status: active
- Parent: WALPROC-G070
- Fib priority: 5001
- Track: shared-runtime
- Priority: P0
- Bundle: wallet-processors/pipeline
- Goal: Create concrete implementation, tests, docs, or interface descriptors proving `ipfs_datasets_py/ipfs_datasets_py/processors/wallets/finality.py`.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/finality.py
- Outputs: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/checkpoints.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/finality.py, ipfs_datasets_py/tests/unit/processors/wallets/test_checkpoints.py, ipfs_datasets_py/tests/unit/processors/wallets/test_reorgs.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/pipeline.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/storage.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/export.py, ipfs_datasets_py/tests/unit/processors/wallets/test_pipeline.py, ipfs_datasets_py/tests/unit/processors/wallets/test_export.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/processors/wallets/test_checkpoints.py ipfs_datasets_py/tests/unit/processors/wallets/test_reorgs.py
- Refinement depth: 2
- Embedding query: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/finality.py
- AST query: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/finality.py
- Parallel lane: wallet-processors/pipeline
- Conflict policy: prefer bundle-local changes; invoke the LLM merge resolver for semantic conflicts
- Gap task: Close the missing objective evidence `ipfs_datasets_py/ipfs_datasets_py/processors/wallets/finality.py` with a narrow, verifiable change.

## WALPROC-G813 Prove ipfs_datasets_py/tests/unit/processors/wallets/test_checkpoints.py for Goal packet aggregate for WALPROC-G070, WALPROC-G080

- Status: active
- Parent: WALPROC-G070
- Fib priority: 5002
- Track: shared-runtime
- Priority: P0
- Bundle: wallet-processors/pipeline
- Goal: Create concrete implementation, tests, docs, or interface descriptors proving `ipfs_datasets_py/tests/unit/processors/wallets/test_checkpoints.py`.
- Evidence: ipfs_datasets_py/tests/unit/processors/wallets/test_checkpoints.py
- Outputs: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/checkpoints.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/finality.py, ipfs_datasets_py/tests/unit/processors/wallets/test_checkpoints.py, ipfs_datasets_py/tests/unit/processors/wallets/test_reorgs.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/pipeline.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/storage.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/export.py, ipfs_datasets_py/tests/unit/processors/wallets/test_pipeline.py, ipfs_datasets_py/tests/unit/processors/wallets/test_export.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/processors/wallets/test_checkpoints.py ipfs_datasets_py/tests/unit/processors/wallets/test_reorgs.py
- Refinement depth: 2
- Embedding query: ipfs_datasets_py/tests/unit/processors/wallets/test_checkpoints.py
- AST query: ipfs_datasets_py/tests/unit/processors/wallets/test_checkpoints.py
- Parallel lane: wallet-processors/pipeline
- Conflict policy: prefer bundle-local changes; invoke the LLM merge resolver for semantic conflicts
- Gap task: Close the missing objective evidence `ipfs_datasets_py/tests/unit/processors/wallets/test_checkpoints.py` with a narrow, verifiable change.

## WALPROC-G814 Prove ipfs_datasets_py/ipfs_datasets_py/processors/wallets/pipeline.py for Implement streaming ingestion and dataset export

- Status: active
- Parent: WALPROC-G080
- Fib priority: 5000
- Track: shared-runtime
- Priority: P0
- Bundle: wallet-processors/pipeline
- Goal: Create concrete implementation, tests, docs, or interface descriptors proving `ipfs_datasets_py/ipfs_datasets_py/processors/wallets/pipeline.py`.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/pipeline.py
- Outputs: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/pipeline.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/storage.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/export.py, ipfs_datasets_py/tests/unit/processors/wallets/test_pipeline.py, ipfs_datasets_py/tests/unit/processors/wallets/test_export.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/processors/wallets/test_pipeline.py ipfs_datasets_py/tests/unit/processors/wallets/test_export.py
- Refinement depth: 2
- Embedding query: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/pipeline.py
- AST query: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/pipeline.py
- Parallel lane: wallet-processors/pipeline
- Conflict policy: prefer bundle-local changes; invoke the LLM merge resolver for semantic conflicts
- Gap task: Close the missing objective evidence `ipfs_datasets_py/ipfs_datasets_py/processors/wallets/pipeline.py` with a narrow, verifiable change.

## WALPROC-G815 Prove ipfs_datasets_py/ipfs_datasets_py/processors/wallets/storage.py for Implement streaming ingestion and dataset export

- Status: active
- Parent: WALPROC-G080
- Fib priority: 5001
- Track: shared-runtime
- Priority: P0
- Bundle: wallet-processors/pipeline
- Goal: Create concrete implementation, tests, docs, or interface descriptors proving `ipfs_datasets_py/ipfs_datasets_py/processors/wallets/storage.py`.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/storage.py
- Outputs: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/pipeline.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/storage.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/export.py, ipfs_datasets_py/tests/unit/processors/wallets/test_pipeline.py, ipfs_datasets_py/tests/unit/processors/wallets/test_export.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/processors/wallets/test_pipeline.py ipfs_datasets_py/tests/unit/processors/wallets/test_export.py
- Refinement depth: 2
- Embedding query: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/storage.py
- AST query: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/storage.py
- Parallel lane: wallet-processors/pipeline
- Conflict policy: prefer bundle-local changes; invoke the LLM merge resolver for semantic conflicts
- Gap task: Close the missing objective evidence `ipfs_datasets_py/ipfs_datasets_py/processors/wallets/storage.py` with a narrow, verifiable change.

## WALPROC-G816 Prove ipfs_datasets_py/ipfs_datasets_py/processors/wallets/export.py for Implement streaming ingestion and dataset export

- Status: active
- Parent: WALPROC-G080
- Fib priority: 5002
- Track: shared-runtime
- Priority: P0
- Bundle: wallet-processors/pipeline
- Goal: Create concrete implementation, tests, docs, or interface descriptors proving `ipfs_datasets_py/ipfs_datasets_py/processors/wallets/export.py`.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/export.py
- Outputs: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/pipeline.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/storage.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/export.py, ipfs_datasets_py/tests/unit/processors/wallets/test_pipeline.py, ipfs_datasets_py/tests/unit/processors/wallets/test_export.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/processors/wallets/test_pipeline.py ipfs_datasets_py/tests/unit/processors/wallets/test_export.py
- Refinement depth: 2
- Embedding query: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/export.py
- AST query: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/export.py
- Parallel lane: wallet-processors/pipeline
- Conflict policy: prefer bundle-local changes; invoke the LLM merge resolver for semantic conflicts
- Gap task: Close the missing objective evidence `ipfs_datasets_py/ipfs_datasets_py/processors/wallets/export.py` with a narrow, verifiable change.

## WALPROC-G817 Prove ipfs_datasets_py/tests/unit/processors/wallets/test_pipeline.py for Implement streaming ingestion and dataset export

- Status: active
- Parent: WALPROC-G080
- Fib priority: 5000
- Track: shared-runtime
- Priority: P0
- Bundle: wallet-processors/pipeline
- Goal: Create concrete implementation, tests, docs, or interface descriptors proving `ipfs_datasets_py/tests/unit/processors/wallets/test_pipeline.py`.
- Evidence: ipfs_datasets_py/tests/unit/processors/wallets/test_pipeline.py
- Outputs: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/pipeline.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/storage.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/export.py, ipfs_datasets_py/tests/unit/processors/wallets/test_pipeline.py, ipfs_datasets_py/tests/unit/processors/wallets/test_export.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/processors/wallets/test_pipeline.py ipfs_datasets_py/tests/unit/processors/wallets/test_export.py
- Refinement depth: 2
- Embedding query: ipfs_datasets_py/tests/unit/processors/wallets/test_pipeline.py
- AST query: ipfs_datasets_py/tests/unit/processors/wallets/test_pipeline.py
- Parallel lane: wallet-processors/pipeline
- Conflict policy: prefer bundle-local changes; invoke the LLM merge resolver for semantic conflicts
- Gap task: Close the missing objective evidence `ipfs_datasets_py/tests/unit/processors/wallets/test_pipeline.py` with a narrow, verifiable change.

## WALPROC-G818 Prove ipfs_datasets_py/tests/unit/processors/wallets/test_reorgs.py for Implement checkpoint, finality, and reorganization contracts

- Status: active
- Parent: WALPROC-G070
- Fib priority: 5000
- Track: shared-runtime
- Priority: P0
- Bundle: wallet-processors/pipeline
- Goal: Create concrete implementation, tests, docs, or interface descriptors proving `ipfs_datasets_py/tests/unit/processors/wallets/test_reorgs.py`.
- Evidence: ipfs_datasets_py/tests/unit/processors/wallets/test_reorgs.py
- Outputs: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/checkpoints.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/finality.py, ipfs_datasets_py/tests/unit/processors/wallets/test_checkpoints.py, ipfs_datasets_py/tests/unit/processors/wallets/test_reorgs.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/processors/wallets/test_checkpoints.py ipfs_datasets_py/tests/unit/processors/wallets/test_reorgs.py
- Refinement depth: 2
- Embedding query: ipfs_datasets_py/tests/unit/processors/wallets/test_reorgs.py
- AST query: ipfs_datasets_py/tests/unit/processors/wallets/test_reorgs.py
- Parallel lane: wallet-processors/pipeline
- Conflict policy: prefer bundle-local changes; invoke the LLM merge resolver for semantic conflicts
- Gap task: Close the missing objective evidence `ipfs_datasets_py/tests/unit/processors/wallets/test_reorgs.py` with a narrow, verifiable change.

## WALPROC-G819 Prove ipfs_datasets_py/tests/contract/processors/wallets/conformance.py for Build shared chain conformance and fixture harness

- Status: active
- Parent: WALPROC-G090
- Fib priority: 5000
- Track: testing
- Priority: P0
- Bundle: wallet-processors/conformance
- Goal: Create concrete implementation, tests, docs, or interface descriptors proving `ipfs_datasets_py/tests/contract/processors/wallets/conformance.py`.
- Evidence: ipfs_datasets_py/tests/contract/processors/wallets/conformance.py
- Outputs: ipfs_datasets_py/tests/contract/processors/wallets/conformance.py, ipfs_datasets_py/tests/fixtures/wallets, ipfs_datasets_py/tests/contract/processors/wallets/test_fixture_integrity.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/contract/processors/wallets/test_fixture_integrity.py
- Refinement depth: 2
- Embedding query: ipfs_datasets_py/tests/contract/processors/wallets/conformance.py
- AST query: ipfs_datasets_py/tests/contract/processors/wallets/conformance.py
- Parallel lane: wallet-processors/conformance
- Conflict policy: prefer bundle-local changes; invoke the LLM merge resolver for semantic conflicts
- Gap task: Close the missing objective evidence `ipfs_datasets_py/tests/contract/processors/wallets/conformance.py` with a narrow, verifiable change.

## WALPROC-G820 Prove ipfs_datasets_py/tests/contract/processors/wallets/test_fixture_integ... for Build shared chain conformance and fixture harness

- Status: active
- Parent: WALPROC-G090
- Fib priority: 5001
- Track: testing
- Priority: P0
- Bundle: wallet-processors/conformance
- Goal: Create concrete implementation, tests, docs, or interface descriptors proving `ipfs_datasets_py/tests/contract/processors/wallets/test_fixture_integrity.py`.
- Evidence: ipfs_datasets_py/tests/contract/processors/wallets/test_fixture_integrity.py
- Outputs: ipfs_datasets_py/tests/contract/processors/wallets/conformance.py, ipfs_datasets_py/tests/fixtures/wallets, ipfs_datasets_py/tests/contract/processors/wallets/test_fixture_integrity.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/contract/processors/wallets/test_fixture_integrity.py
- Refinement depth: 2
- Embedding query: ipfs_datasets_py/tests/contract/processors/wallets/test_fixture_integrity.py
- AST query: ipfs_datasets_py/tests/contract/processors/wallets/test_fixture_integrity.py
- Parallel lane: wallet-processors/conformance
- Conflict policy: prefer bundle-local changes; invoke the LLM merge resolver for semantic conflicts
- Gap task: Close the missing objective evidence `ipfs_datasets_py/tests/contract/processors/wallets/test_fixture_integrity.py` with a narrow, verifiable change.

## WALPROC-G821 Prove ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin/challe... for Extract World ID binding, challenge, replay, proof, and snapshot ownership

- Status: active
- Parent: WALPROC-G110
- Fib priority: 5000
- Track: worldcoin
- Priority: P0
- Bundle: wallet-processors/worldcoin-state
- Goal: Create concrete implementation, tests, docs, or interface descriptors proving `ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin/challenges.py`.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin/challenges.py
- Outputs: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin/bindings.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin/challenges.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin/proofs.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin/snapshots.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin/processor.py, ipfs_datasets_py/ipfs_datasets_py/wallet/models.py, ipfs_datasets_py/ipfs_datasets_py/wallet/service.py, ipfs_datasets_py/tests/unit/processors/wallets/worldcoin/test_bindings.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/processors/wallets/worldcoin/test_bindings.py ipfs_datasets_py/tests/unit/test_data_wallet.py
- Refinement depth: 2
- Embedding query: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin/challenges.py
- AST query: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin/challenges.py
- Parallel lane: wallet-processors/worldcoin-state
- Conflict policy: prefer bundle-local changes; invoke the LLM merge resolver for semantic conflicts
- Gap task: Close the missing objective evidence `ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin/challenges.py` with a narrow, verifiable change.

## WALPROC-G822 Prove ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin/proofs.py for Extract World ID binding, challenge, replay, proof, and snapshot ownership

- Status: active
- Parent: WALPROC-G110
- Fib priority: 5001
- Track: worldcoin
- Priority: P0
- Bundle: wallet-processors/worldcoin-state
- Goal: Create concrete implementation, tests, docs, or interface descriptors proving `ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin/proofs.py`.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin/proofs.py
- Outputs: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin/bindings.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin/challenges.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin/proofs.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin/snapshots.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin/processor.py, ipfs_datasets_py/ipfs_datasets_py/wallet/models.py, ipfs_datasets_py/ipfs_datasets_py/wallet/service.py, ipfs_datasets_py/tests/unit/processors/wallets/worldcoin/test_bindings.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/processors/wallets/worldcoin/test_bindings.py ipfs_datasets_py/tests/unit/test_data_wallet.py
- Refinement depth: 2
- Embedding query: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin/proofs.py
- AST query: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin/proofs.py
- Parallel lane: wallet-processors/worldcoin-state
- Conflict policy: prefer bundle-local changes; invoke the LLM merge resolver for semantic conflicts
- Gap task: Close the missing objective evidence `ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin/proofs.py` with a narrow, verifiable change.

## WALPROC-G823 Prove ipfs_datasets_py/tests/unit/processors/wallets/worldcoin/test_binding... for Extract World ID binding, challenge, replay, proof, and snapshot ownership

- Status: active
- Parent: WALPROC-G110
- Fib priority: 5002
- Track: worldcoin
- Priority: P0
- Bundle: wallet-processors/worldcoin-state
- Goal: Create concrete implementation, tests, docs, or interface descriptors proving `ipfs_datasets_py/tests/unit/processors/wallets/worldcoin/test_bindings.py`.
- Evidence: ipfs_datasets_py/tests/unit/processors/wallets/worldcoin/test_bindings.py
- Outputs: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin/bindings.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin/challenges.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin/proofs.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin/snapshots.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin/processor.py, ipfs_datasets_py/ipfs_datasets_py/wallet/models.py, ipfs_datasets_py/ipfs_datasets_py/wallet/service.py, ipfs_datasets_py/tests/unit/processors/wallets/worldcoin/test_bindings.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/processors/wallets/worldcoin/test_bindings.py ipfs_datasets_py/tests/unit/test_data_wallet.py
- Refinement depth: 2
- Embedding query: ipfs_datasets_py/tests/unit/processors/wallets/worldcoin/test_bindings.py
- AST query: ipfs_datasets_py/tests/unit/processors/wallets/worldcoin/test_bindings.py
- Parallel lane: wallet-processors/worldcoin-state
- Conflict policy: prefer bundle-local changes; invoke the LLM merge resolver for semantic conflicts
- Gap task: Close the missing objective evidence `ipfs_datasets_py/tests/unit/processors/wallets/worldcoin/test_bindings.py` with a narrow, verifiable change.

## WALPROC-G824 Prove ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin/bindin... for Extract World ID binding, challenge, replay, proof, and snapshot ownership

- Status: active
- Parent: WALPROC-G110
- Fib priority: 5000
- Track: worldcoin
- Priority: P0
- Bundle: wallet-processors/worldcoin-state
- Goal: Create concrete implementation, tests, docs, or interface descriptors proving `ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin/bindings.py`.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin/bindings.py
- Outputs: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin/bindings.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin/challenges.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin/proofs.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin/snapshots.py, ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin/processor.py, ipfs_datasets_py/ipfs_datasets_py/wallet/models.py, ipfs_datasets_py/ipfs_datasets_py/wallet/service.py, ipfs_datasets_py/tests/unit/processors/wallets/worldcoin/test_bindings.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/processors/wallets/worldcoin/test_bindings.py ipfs_datasets_py/tests/unit/test_data_wallet.py
- Refinement depth: 2
- Embedding query: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin/bindings.py
- AST query: ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin/bindings.py
- Parallel lane: wallet-processors/worldcoin-state
- Conflict policy: prefer bundle-local changes; invoke the LLM merge resolver for semantic conflicts
- Gap task: Close the missing objective evidence `ipfs_datasets_py/ipfs_datasets_py/processors/wallets/worldcoin/bindings.py` with a narrow, verifiable change.
