# ipfs_datasets_py Symbolic Contract and Dataset Manipulator Analysis Plan

Status: approved for supervised implementation on the dedicated integration
branch `codex/datasets-contract-analysis`.

Companion artifacts:

- Objective heap:
  [`DATASETS_CONTRACT_ANALYSIS_OBJECTIVES.md`](DATASETS_CONTRACT_ANALYSIS_OBJECTIVES.md)
- Executable task board:
  [`DATASETS_CONTRACT_ANALYSIS_TODO.md`](DATASETS_CONTRACT_ANALYSIS_TODO.md)
- Supervisor lifecycle wrapper:
  [`datasets_contract_analysis_supervisor.sh`](../../scripts/datasets_contract_analysis_supervisor.sh)
- Runtime and content-addressed analysis state:
  `data/datasets_contract_analysis/agent_supervisor/`

Operator sequence:

```bash
./scripts/datasets_contract_analysis_supervisor.sh seed
./scripts/datasets_contract_analysis_supervisor.sh doctor
./scripts/datasets_contract_analysis_supervisor.sh start
./scripts/datasets_contract_analysis_supervisor.sh status
# reviewed shutdown only:
./scripts/datasets_contract_analysis_supervisor.sh stop
```

`seed` is deterministic but its generated control-plane artifacts must be
reviewed and committed before launch. `start` fails closed when they are
absent, runs strict reconciliation for each shard, launches both supervisors,
and waits until each supervisor and managed implementation daemon is live.
`status` rewrites the atomic health snapshot and fails if a lane, daemon,
protected-path fence, or maintenance state is unhealthy.

## 1. Outcome

Build a deterministic, incremental software-contract analysis system that:

1. removes the known drift in the `ipfs_datasets_py` dataset manipulation
   surface;
2. inventories and analyzes every Git-tracked object in the exact pinned
   `ipfs_datasets_py` tree, which is the primary proof subject;
3. constructs content-addressed AST, symbol, import, call, contract, proof,
   finding, and repair-packet datasets;
4. proves supported contract obligations, emits replayable counterexamples for
   refuted obligations, and reports unsupported or uncertain behavior without
   claiming it is safe;
5. optionally produces a zero-knowledge attestation that a reviewed,
   deterministic analyzer ran over committed public inputs and produced a
   committed result root;
6. converts stable contract mismatches and security findings into small,
   dependency-aware supervisor tasks; and
7. lets Codex and Grok repair those tasks from bounded context packets while
   deterministic validators, not model assertions, control completion.

The system is designed to minimize language-model context and invocation
count. Static discovery, identity, caching, graph construction, proof,
deduplication, prioritization, and task admission are symbolic and
deterministic. An LLM is used only after a precise repair task has been
admitted, and receives only the relevant contract, call slice, source excerpts,
counterexample, and validation command.

`ipfs_accelerate_py` is the orchestration and task-projection runtime.
`ipfs_kit_py`, Swissknife, and other consumers supply boundary-call and
revision evidence only. They are not part of the primary completeness domain
for the first `ipfs_datasets_py` proof scan, and their partial coverage cannot
block or silently widen that package-scoped milestone.

## 2. Current-state findings

### 2.1 Dataset manipulator drift

The current dataset tool documentation says that MCP dataset tools are thin
wrappers around core operations and marks `process_dataset` production ready.
The implementation does not satisfy that contract:

- `mcp_server/tools/dataset_tools/process_dataset.py` explicitly contains a
  mock processing loop;
- operations such as `transform`, `normalize`, and `clean` construct a
  `DataProcessor` but do not call it;
- a filter fabricates a ten-percent record reduction instead of evaluating a
  predicate;
- unknown dataset sources default to 100 records;
- output IDs use Python's process-randomized `hash()`, so identical inputs are
  not content-addressed or reproducible across processes;
- the MCP operation names do not match the core `DataProcessor`
  transformation vocabulary;
- broad optional-import fallbacks can turn missing behavior into an apparently
  successful mock result; and
- much of the existing test surface checks response shape or mocks the backend
  rather than checking semantic equivalence between direct Python, MCP tool,
  MCP client, and HTTP entrypoints.

This is the first contract-analysis pilot. It must be fixed by a real,
bounded-operation core implementation and thin adapters, not by updating the
documentation to bless mock behavior.

### 2.2 Reusable symbolic and content-addressed components

`ipfs_datasets_py` already contains useful components that should be adapted
rather than duplicated:

- Python source extraction:
  `logic/security_models/crypto_exchange/extractors/python_ast_extractor.py`;
- security constraint IR, cache, and query support:
  `logic/security_ir/constraint_cache.py`,
  `logic/security_ir/constraint_query.py`, and
  `logic/security_ir/formalization_adapter.py`;
- canonical IR identity, provenance, claims, diagnostics, and artifacts:
  `logic/ir_core/`;
- FOL/TDFOL, CEC, Z3, and cvc5 proof backends:
  `logic/fol/`, `logic/TDFOL/`, `logic/CEC/`, and `logic/backends/`;
- content-addressed proof corpora, caches, reconstruction, and receipts:
  `logic/hammers/`, `logic/common/proof_cache.py`, and
  `logic/flogic/flogic_proof_cache.py`;
- CIDv1 DAG-JSON helpers:
  `logic/ipld_cid.py` and `utils/cid_utils.py`;
- ProveKit and Groth16 abstractions:
  `logic/zkp/` and `logic/zkp/provekit/`;
- IPLD knowledge-graph and graph-query infrastructure:
  `knowledge_graphs/` and `search/graph_query/`; and
- GraphRAG integration:
  `search/graphrag_integration/` and `processors/graphrag_processor.py`.

These assets have different maturity and dependency profiles. The bootstrap
inventory must test and classify them before treating any of them as completion
evidence.

### 2.3 Existing supervisor capabilities

`ipfs_accelerate_py.agent_supervisor` already provides:

- objective heaps, generated subgoals, bundle shards, task CIDs, and AST/vector
  task indexes;
- deterministic task sharding across independent implementation providers;
- ephemeral parent and submodule-aware worktrees;
- protected control-plane paths, validation gates, merge queues, retry-budget
  repair tasks, and reconciliation;
- objective and codebase refill scans when a backlog becomes low or drains;
  and
- exhaustive drained-backlog scans across discovered worktrees and submodules.

The initial codebase scanner finds annotations, swallowed exceptions, and
placeholder runtime paths. This program extends that admission pipeline with
content-addressed contract and vulnerability findings.

The legacy objective AST dataset exporter is disabled for this program's
bootstrap seed/refill. On the current composition it serialized source-heavy
rows into a roughly 2.6 GB JSONL file before task generation completed, which
is neither a bounded control-plane index nor the content-addressed shard model
specified here. Bootstrap uses structural objective evidence and the bounded
task/vector projection only. Goals G020, G100-G150, and G700 replace that dump
with disposition-complete, incremental CID shards and explicit resource
receipts before any whole-repository analysis claim is allowed.

### 2.4 Primary package and boundary-repository scope

The first complete scan targets the clean, pinned `ipfs_datasets_py` Git tree.
Its commit, tree, tracked-object manifest, analyzer profile, frontend versions,
policy roots, and proof/finding roots form the authoritative scan statement.
Every supported semantic shard must receive an AST or explicit fail-closed
receipt before package-level absence or exhaustion claims are allowed.

The requested Swissknife source is a separate clean Git repository at
`/home/barberb/swissknife`, currently on commit
`df11f08f` (`main`). It has 6,395 tracked paths and is predominantly
TypeScript/JavaScript: 2,278 `.ts`, 106 `.tsx`, 675 `.js`, 300 `.cjs`, 64
`.mjs`, and 6 `.jsx` paths, compared with 100 `.py` paths. A Python-only or
regex-only scanner therefore cannot claim whole-repository semantic coverage.

Swissknife also has a runtime composition through `hallucinate_app`. The
`/home/barberb/hallucinate_app/ipfs_datasets_py` checkout is currently at
`8dc4f93e`, while `/home/barberb/ipfs_datasets_py` is at `6672d6924`; the
former is 1,832 commits behind the latter. The scope manifest must record both
identities and select one reviewed runtime authority before contract findings
are interpreted. It must never compare an expected contract from one revision
to an invocation from another revision without labeling that revision mismatch
as part of the finding.

The launch wrapper supplies the Swissknife path as an optional, read-only
boundary root. If it is absent, dirty, or not a Git repository, boundary
composition evidence records that limitation, but this does not make a clean
`ipfs_datasets_py` package inventory incomplete. No whole-Swissknife exhaustion
or safety claim is part of the first package-scoped release.

### 2.5 Current package AST checkpoint

The first package-only immutable snapshot and AST exhaustion pass is recorded
under `data/datasets_contract_analysis/scans/ipfs_datasets_py/baseline/`.
It binds datasets commit `0689cff0b58c5c57fae67f51d20fa76b3a8d2061`,
tree `9d5389eaca12826353263a755d486547fed6ddba`, and repository-root CID
`baguqeerawnqcvy5yfuappuhkdmuiqrtlp66on4idvup76x3qx2stuwq6x5la`.
All 12,109 tracked blobs have dispositions. All 7,019 eligible Python blobs
terminate in a content-addressed AST result: 6,416 without unsupported
constructs and 603 with explicit unsupported records; no frontend exception,
resource exhaustion, unavailable source, or unattempted blob remains. The
aggregate AST baseline receipt is
`baguqeeravqeus4d5klxxypnc3vm6l2qvwhsfylt7zhonmkkm5yc5igox6zbq`.

This checkpoint has `STATIC_AST_BASELINE_ONLY` authority. It is not a function
contract proof or a package safety claim. The bounded resolver is implemented
and covered by nine focused tests. Call/effect graph, contract extraction,
obligation, solver/reconstruction, evidence-graph, receipt, security-rule,
finding, and supervisor contract-refill stages remain mandatory before G705
can emit proof and finding roots.

## 3. Proof boundary and claim vocabulary

Python is dynamic. Reflection, monkey-patching, native extensions, network
services, runtime code generation, optional imports, and unconstrained external
state prevent a whole-repository analyzer from proving arbitrary functional
correctness. The system must never collapse that limitation into a pass.

Every obligation has exactly one verdict:

- `proved`: the encoded obligation is valid within a named semantics,
  assumptions, analyzer version, and bounded model;
- `refuted`: a checked counterexample or deterministic witness violates it;
- `unknown`: the solver timed out or could not decide it within the budget;
- `unsupported`: the source uses behavior outside the reviewed semantics;
- `inconsistent_contract`: the declared assumptions are themselves
  contradictory;
- `stale`: the evidence does not bind the current repository tree, gitlinks,
  policy, or analyzer; or
- `error`: the analyzer did not complete safely.

Only `proved` evidence may satisfy a proof-required completion criterion.
`unknown`, `unsupported`, `stale`, and `error` fail closed. A test pass is
runtime evidence, not a formal proof. A type-check pass is type evidence, not a
behavior proof.

Zero-knowledge proofs have a narrower claim:

> Given the public repository-tree CID, analyzer/policy/toolchain CIDs, trace
> commitment, and result Merkle root, the prover opened the committed canonical
> trace and the reviewed circuit checked exactly the named transition,
> commitment, and completeness constraints encoded by that circuit.

The baseline statement is a trace-commitment opening, not a general attestation
that the analyzer executed correctly. It may claim analyzer execution only
after the circuit covers every relevant trace transition, input opening, result
derivation, and completeness check. It does not make an unsound analyzer sound,
prove an unmodeled Python behavior, hide public source code, or turn an
`unknown` verdict into `proved`.

## 4. Repository identity and scan scope

### 4.1 Canonical snapshot

The analyzer reads Git objects, not an ambient recursive filesystem walk.
Snapshot identity contains:

- superproject commit and tree;
- each recursive gitlink path and pinned commit/tree;
- `.gitmodules` content;
- analyzer source commit;
- canonical analyzer configuration;
- parser, solver, proof-backend, and schema versions; and
- an explicit dirty-tree decision.

Production analysis fails closed on tracked modifications, unmerged entries,
missing gitlink objects, symlink escapes, or an unrecorded analyzer
configuration. A developer mode may analyze a dirty tree only after building a
separate immutable overlay manifest whose blobs and path decisions are all
content addressed.

### 4.2 Complete `ipfs_datasets_py` coverage

Every tracked blob receives a CID and disposition record. "Indexed" does not
mean "semantically proved":

- supported source files receive AST and contract analysis;
- supported declarative files receive schema/config/dependency analysis;
- generated, vendored, archived, binary, fixture, and oversized files remain in
  the inventory but receive an explicit non-semantic disposition;
- nested duplicate submodules are deduplicated by tree/blob CID; and
- every excluded semantic path records its reason, governing policy, size, and
  count so coverage cannot silently shrink.

The first sound semantic frontend is Python. TypeScript/JavaScript, shell,
Docker, TOML/YAML/JSON, Solidity/Noir, and Rust frontends are separate,
versioned capabilities. Until a frontend is accepted, its files are
`unsupported`, not passed.

The primary coverage root contains only the exact pinned `ipfs_datasets_py`
tree. Cross-package and Swissknife snapshots are separate boundary evidence
roots, so a missing boundary checkout cannot alter the package object count or
be confused with package semantic coverage.

The current supervisor objective scanner is also bounded: it recognizes a
fixed suffix set, ignores oversized files, and its codebase refill rules
primarily target annotations, swallowed exceptions, and placeholders. Its
normal scan is not the package proof requested here. The recursive
tracked-object manifest, real TypeScript Compiler API frontend, and typed
contract-finding admission layer are mandatory bootstrap work before stronger
coverage language is permitted.

## 5. Content-addressed evidence model

Use canonical DAG-JSON or DAG-CBOR and CIDv1 with an explicitly pinned
multicodec and multihash profile. No process-local `hash()`, timestamps,
absolute paths, dictionary insertion accidents, or host-specific values enter
semantic identities.

Per-blob, per-symbol, and dependency-slice cache keys are domain separated and
bind only the immutable closure needed to reuse that result:

```text
analysis-shard-key/v1(
  source-blob-cid or dependency-slice-root,
  analyzer-binary/source-cid,
  analyzer-config-cid,
  language-semantics-cid,
  contract-policy-cid,
  solver-and-toolchain-cid,
  dependency-summary-cids
)
```

The global repository-tree CID is deliberately absent from a reusable shard
key: including it would invalidate every shard after any one-blob change.
Snapshot, coverage, proof-quorum, and final result manifests separately bind
the repository-tree CID to the complete ordered set of reused and newly
computed shard CIDs. Cache entries are immutable. Mutable lookup indexes point
to immutable CIDs and are replaceable. A cache hit is accepted only after
digest, schema, provenance, dependency-closure, and snapshot-membership
verification. Negative and `unknown` results have bounded leases; they are
never permanent proof.

Merkle roots are emitted for:

- repository inventory;
- AST shard dataset;
- symbol and call graph;
- contract declarations;
- generated obligations;
- proof/counterexample receipts;
- findings and suppressions; and
- generated repair packets and supervisor tasks.

## 6. Deterministic analysis pipeline

```text
Git tree + recursive gitlinks
  -> tracked-object/CID manifest
  -> language/disposition shards
  -> normalized AST and symbol definitions
  -> imports, references, overrides, and conservative call edges
  -> explicit and inferred contract summaries
  -> caller/callee and architecture-policy obligations
  -> SMT/TDFOL/security-rule verification
  -> proof, counterexample, unknown, or unsupported receipts
  -> stable findings
  -> bounded repair packets
  -> supervisor goal/subgoal/task admission
```

Every stage is a pure or explicitly effect-bounded transform with an input root
and output root. Shards are deterministic by repository/tree/path/blob/symbol
identity. Strongly connected call components are analyzed as bounded units.
Only transitive dependants of a changed summary are invalidated.

## 7. AST, symbol graph, and deterministic GraphRAG

A single shared-schema stage owns the
`logic/software_contracts` package scaffold, exports, schema-version registry,
and language-neutral AST/symbol IR. Python and TypeScript/JavaScript frontends
depend on that stage and may then run in parallel without independently
creating or changing shared package files.

The normalized graph represents repositories, trees, blobs, modules, symbols,
parameters, types, imports, exports, inheritance, protocol implementation,
decorators, reads/writes, raises, awaits, context-manager use, call sites,
tests, configuration, and contract evidence.

Call edges have confidence classes:

- exact lexical/static resolution;
- finite target set from type/protocol dispatch;
- conservative wildcard target set;
- dynamic/reflection boundary; or
- unresolved.

An unresolved edge is evidence of uncertainty, not the absence of a call.

GraphRAG is used here as deterministic graph retrieval and evidence slicing.
Embedding similarity may rank already-admitted nodes, but cannot create,
delete, prove, or suppress an edge or finding. The authoritative repair packet
is reproducible from graph IDs and CIDs without an embedding service or LLM.

## 8. Contract IR and obligation generation

The software contract IR covers:

- callable name, owner, visibility, sync/async/generator shape, parameters,
  defaults, and return type;
- preconditions, postconditions, invariants, state transitions, and temporal
  ordering;
- raised and swallowed exceptions;
- side effects: filesystem, subprocess, network, environment, imports,
  database, cache, logging, secrets, and global mutation;
- resource bounds: bytes, rows, pages, recursion, retries, timeout, processes,
  and concurrency;
- determinism and idempotency;
- data classification and trust boundaries;
- capability requirements and optional-dependency behavior; and
- provenance for every declared or inferred fact.

Contract source precedence is deterministic:

1. reviewed machine-readable contract manifests and schemas;
2. Python `Protocol`, ABC, stub, signature, annotation, and validated decorator
   declarations;
3. executable property/contract tests;
4. explicit package policy manifests;
5. mechanically parsed documentation statements; and
6. conservative inference from source.

Lower-precedence evidence cannot silently override higher-precedence evidence.
Contradictions become findings.

For a call `caller -> callee`, the initial proof obligations include:

- caller argument facts imply callee preconditions;
- callee return and exception facts are compatible with caller use;
- caller handles or intentionally propagates declared failures;
- required capabilities and optional dependencies are available;
- callee effects are permitted by caller and package policy;
- async/sync, cancellation, context-manager, transaction, and resource
  lifecycles are respected;
- security labels do not flow to an unauthorized sink; and
- wrapper documentation and behavior match the owning core implementation.

## 9. Formal solvers and proof receipts

Use small, reviewable translations:

- Z3/cvc5 for types, predicates, ranges, state transitions, and bounded
  dataflow;
- FOL/TDFOL for implication and temporal/ordering policies;
- security IR constraints for capability, effect, and trust-boundary policies;
- optional CEC/Lean/hammer reconstruction for high-value obligations; and
- concrete property tests for extracted counterexamples.

Each `proved` receipt stores the normalized proposition, assumptions, solver
input, solver version, result, reconstruction/check status, budgets, and CIDs.
Proof caches must not accept solver text or booleans without replayable inputs.
At least one independent checker or proof reconstruction is required before a
high-severity finding can be marked repaired.

## 10. Security analysis

Initial deterministic rule families cover:

- unsafe deserialization, dynamic execution, shell/subprocess injection;
- path traversal, symlink escape, archive extraction, and unsafe temporary
  files;
- SSRF, unbounded redirects/retries/pages/bodies, and ambient network access;
- secret/token/private-data flows to logs, exceptions, caches, task prompts, or
  public artifacts;
- authentication/authorization default allow, capability confusion, and
  validation bypass;
- SQL/Cypher/template injection and unsafe query construction;
- insecure hashes, process-randomized identity, nonce/key misuse, and
  unverifiable fallback digests;
- swallowed exceptions, mock/placeholder success paths, and fail-open optional
  dependencies;
- async blocking, cancellation loss, resource leaks, race windows, and
  non-atomic state updates; and
- cross-package signature, return, exception, schema, and version drift.

Findings use stable rule and semantic IDs, CWE mappings where applicable,
confidence, severity, reachability, counterexample/proof status, owners, and
precise affected symbols. Suppressions are scoped, expiring, reviewable
contracts bound to finding and tree identity.

## 11. Dataset manipulator target contract

The pilot defines one canonical `DatasetOperationPlan` and one
`DatasetManipulator` owner in `core_operations`. Supported operations have
typed parameters, finite row/byte/time limits, deterministic ordering rules,
input/output schema behavior, and explicit error semantics.

Required initial behavior:

- no silent or mock success;
- deterministic content-derived operation/result IDs;
- real filter, select/drop/rename, map through a safe registered transform,
  normalize/clean, shuffle with explicit seed, and bounded slice operations;
- streaming or bounded materialization, with explicit unsupported responses
  where a backend cannot honor a contract;
- no arbitrary `eval`, import, callable deserialization, or ambient network;
- identical semantics from direct Python, MCP tool modules, the MCP client, and
  the existing HTTP service entrypoints;
- stable receipts with input/plan/output CIDs, record counts, schema
  fingerprints, warnings, and partial/error status; and
- compatibility tests that distinguish deliberate changes from regressions.

MCP tool, client, and HTTP layers parse/serialize requests and delegate. They
contain no operation execution, fabricated counts, fallback mock results, or
identity logic. This repository currently has no canonical dataset-manipulator
CLI, so this program does not invent one or claim CLI equivalence. A future CLI
requires a separately owned interface contract and task.

The pilot inventory also covers the 1,912-line legacy
`ipfs_datasets_py/ipfs_datasets.py` monolith, including duplicate/shadowed
method definitions, undefined calls, inconsistent sync/async and return/error
contracts, nondeterministic shuffling, and imports of missing multiformat
surfaces. Characterization fixtures land before the monolith is split or
deprecated.

## 12. ZK attestation rollout

ZK work is gated behind a deterministic native verifier.

1. Define public inputs, private witness, circuit semantics, disclosure, setup,
   verifier-key, and trust assumptions.
2. Produce a canonical analysis trace for a deliberately small obligation
   class, initially hash/preimage and finite contract-transition checks.
3. Replay and verify the trace natively.
4. Bind trace and result roots to ProveKit/Groth16 artifacts as a
   trace-commitment opening; encode only explicitly reviewed transitions.
5. Verify positive, tampered-input, tampered-policy, stale-tree, forged-result,
   and wrong-verifier-key cases.
6. Expand only after measured circuit cost and an independent security review.

ZK generation is optional and offline by default. Missing ZK dependencies
cannot block ordinary deterministic analysis unless a task explicitly requires
ZK evidence.

## 13. Supervisor integration and low-context repair

The supervisor consumes stable `ContractFinding` records. Admission requires:

- current repository, gitlink, analyzer, and policy CIDs;
- a non-`unknown`, non-stale finding with a precise owner;
- an exact, repository-relative file/symbol scope;
- a reproducible validation command;
- deduplication against open/completed/suppressed semantic identities;
- dependency mapping to the owning goal/subgoal; and
- a bounded repair packet.

A repair packet contains:

- finding/rule/verdict/severity;
- one-line expected-versus-observed contract;
- source and contract CIDs;
- the smallest caller/callee graph slice;
- exact source excerpts with line/symbol identity;
- proof witness or counterexample;
- permitted and protected paths;
- acceptance criteria and focused tests; and
- a token/byte budget.

No repository dump, full GraphRAG corpus, solver log flood, raw secret, or
unrelated file enters the prompt. Default packet target is at most 8 KiB of
text and 2,048 input tokens; exceptions require an explicit larger resource
class.

The supervisor runs two deterministic task shards:

- Codex: shard 0;
- Grok Build: shard 1.

The checked-in heap currently uses the supervisor's legacy Markdown
compatibility projection. Structural parsing, parent/dependency topology,
bounded objective-gap refinement, and task materialization are supported by
that path. It must not be described as strict typed-goal admission:
`goal_quality.project_objective_markdown()` currently drops evidence output
schemas and acceptance completion signals, so strict lint correctly reports
quality debt even when additional legacy fields are present. The launcher
persists that quality report as diagnostic evidence but gates startup on the
legacy structural/materialization checks that the running daemon actually
uses. A bootstrap objective extends the projector or adds a canonical typed
sidecar for producer schemas, completion signals, authority, freshness,
resource envelopes, unsupported-semantic fallbacks, and refinement budgets.
Strict typed admission may become a startup gate only after that representation
round trips and the current heap has no admission-blocking debt.

All three submodules are initialized in implementation worktrees. Shared
schemas and control-plane files are serialized through dependency gates and
protected paths. Package-local tasks use disjoint ownership where possible.
Merge validation re-runs the focused proof/test and checks that the finding CID
is absent or has an accepted state transition.

When open work falls below the configured threshold:

1. objective refill checks missing evidence and may add bounded child goals;
2. the content-addressed scanner reuses unchanged shards and analyzes changed
   dependency slices;
3. new findings pass deterministic admission and deduplication;
4. admitted findings append bundle-local tasks; and
5. exhausted scans emit a current-tree coverage/quorum receipt instead of
   inventing work.

## 14. Parallel work and ownership

| Lane | Primary ownership | May run with |
| --- | --- | --- |
| bootstrap | inventory, identity, soundness policy | dataset baseline |
| content | CID profile, Merkle inventory, cache | AST frontend |
| schema | package scaffold, shared AST/symbol IR, schema versions | content cache after CID profile |
| graph | language frontends, symbols, imports, calls, IPLD/GraphRAG | contract schema after shared IR |
| formal | contract IR, obligations, solvers, receipts | security rules |
| datasets | dataset operation IR, core manipulator, adapters | graph/formal after schema gates |
| supervisor | finding/task adapters, refill, repair packets | analyzers after finding schema |
| ZK | statement, trace, proof envelope | only after native verifier |
| rollout | package proof scan, canaries, autonomous repair, release | after package proof prerequisites |

The canonical schemas, CID profile, task board, objective heap, launch script,
and merge queue each have one serialized owner. Agents must not modify
protected planning/control files.

### 14.1 Executable package-proof critical path

The first formal analysis target is the exact pinned `ipfs_datasets_py` tree.
The supervisor must follow this dependency graph and may parallelize only the
branches shown:

```text
G115 complete ──> G130 complete ──> G140 ──┬─> G150 ──────────────┐
                                            ├─> G400 ────────┐     │
G115 + G200 complete ──> G210 ──┐           │                │     │
G010 + G200 complete ──> G220 ──┴─> G230 ──┴─> G240 ────────┴─> G250
                                                                  │
G400 + G250 ───────────────────────────────────────────────────> G420
G115 + G250 + G420 ────────────────────────────────────────────> G705
G705 ──> G600 ──> G610 ──> G620 ──> G630
  └────> G700
G630 + G700 ───────────────────────────────────────────────────> G720
```

G210 contract extraction, G220 package policy, and G140 call/effect graph are
the next independent implementation lanes. After G140, evidence-graph,
obligation, and security-rule work may run in parallel. G340, G410, G710, the
TypeScript capability gap, and optional ZK envelopes are explicitly outside
the first package-proof critical path. Aggregate packet cards are tracking
records and never compete with their granular implementation cards.

## 15. Phases and release gates

### Phase 0 — freeze and measure

- inventory current repository/gitlink state and analyzer capabilities;
- capture dataset manipulator semantic drift and security baselines;
- define proof/soundness claims and supported-language dispositions;
- preserve a current structural/materialization and typed-quality-debt report
  for the legacy objective heap; and
- add a lossless typed objective representation before strict goal-quality
  admission is made mandatory.

Gate: repeatable baseline reports, no production-code changes, all unknowns
explicit.

### Phase 1 — content identity and AST graph

- canonical CID profile and Merkle inventory;
- incremental cache;
- shared normalized AST/symbol schemas followed by language-specific
  AST/symbol/import/call datasets;
- deterministic IPLD/GraphRAG index.

Gate: two clean runs have identical roots; a one-blob mutation invalidates only
the expected dependency slice; every tracked blob has a disposition.

### Phase 2 — contracts and proofs

- contract IR and extractors;
- obligation generator and solver backends;
- proof/counterexample/unknown receipts;
- security rules and finding schema.

Gate: golden valid/invalid/unknown fixtures are classified exactly; proof
receipts replay in a clean process; unsupported dynamic behavior fails closed.

### Phase 3 — complete the first `ipfs_datasets_py` proof scan

- inventory and index the full committed `ipfs_datasets_py` tree;
- emit package-scoped AST, contract, obligation, proof, coverage, and finding
  roots;
- replay every receipt against the exact tree, analyzer, policy, schema,
  solver, and tool identities;
- fail closed on missing, unknown, unsupported, stale, or incomplete
  supported-semantic shards.

Gate: G705 has a current scan receipt, proof root, and finding root; every
tracked object has exactly one disposition; no boundary-repository safety or
exhaustion claim is made.

### Phase 4 — supervisor refill and low-context edits

- finding-to-task projection;
- minimal repair packets;
- objective/codebase refill adapters;
- completion evidence and independent validation.

Gate: package findings generate one stable task each, duplicates generate
none, unknown/stale findings are blocked, and scan failure leaves both
supervisor lanes live without claiming exhaustion.

### Phase 5 — staged package repair and dataset-manipulator canary

- canonical operation plan and core implementation;
- thin MCP tool, client, and HTTP adapters;
- direct/MCP-tool/client/HTTP equivalence and security tests;
- pilot call-contract proofs;
- high-confidence, low-blast-radius package finding repairs through Codex and
  Grok Build.

Gate: no mock success or process-randomized IDs; compatibility and semantic
tests pass twice; exact finding and dependant obligations are rechecked; pilot
drift findings are proved repaired or explicitly unsupported.

### Phase 6 — optional ZK attestation

- native trace verifier;
- reviewed public input and witness schema;
- optional proof backend integration and negative tests.

Gate when enabled: tampering and stale inputs fail; verifier keys and setup
provenance are bound; documentation states whether the proof is only a
trace-commitment opening or covers a named set of transitions. A current
`not_enabled` capability receipt is sufficient for the ordinary release path.

### Phase 7 — optional boundary-composition expansion

- analyze the pinned accelerator, kit, and Swissknife boundary trees;
- compose package and external-call contracts without changing the package
  proof root;
- publish separate cross-repository coverage, mismatch, and finding roots.

Gate when reviewed: every boundary root is clean and pinned, partial language
coverage is explicit, and no package-only result is silently widened into a
cross-repository claim.

## 16. Validation strategy

Every analyzer stage has:

- canonical golden fixtures;
- mutation fixtures with one expected invalidation;
- malformed, cyclic, recursive, missing-submodule, dirty-tree, symlink, and
  oversized-input cases;
- deterministic double-run comparison;
- property/fuzz tests for canonicalization and parsers;
- time, memory, file-count, graph-degree, solver, and receipt-size budgets;
- no-network and minimal-optional-dependency tests;
- stale/tampered cache and proof rejection tests; and
- a clean-process replay validator.

Whole-program release validation includes focused unit tests, cross-package
contract fixtures, a clean recursive-tree scan, a second independent verifier,
supervisor task-generation canaries, merge/rollback rehearsal, and a scan
coverage report.

## 17. Safety, privacy, and operational bounds

- Analyze tracked source by default; never ingest `.env`, credentials,
  untracked runtime state, home-directory caches, or arbitrary worktrees.
- Store hashes/CIDs and bounded redacted excerpts in findings; do not copy
  complete sensitive fixtures into prompts or public proof artifacts.
- Parsing and solving run without network, ambient credentials, auto-install,
  shell expansion, or write access outside explicit cache/output roots.
- Set hard limits for blob size, archive depth, AST nodes, graph edges,
  recursion, SCC size, solver time/memory, proof size, findings per rule, tasks
  per refill, and prompt bytes.
- A failed, partial, stale, or resource-exhausted scan is not evidence of
  absence.
- Autonomous repairs begin with low-severity, deterministic, focused changes.
  Authentication, cryptography, deletion, migration, publication, and
  production enablement require explicit higher-authority gates.

## 18. Completion definition

The program is complete when:

- the dataset manipulator has one real core owner and thin adapters;
- every tracked object in the exact pinned `ipfs_datasets_py` tree has a CID
  and disposition;
- supported Python call and contract surfaces are indexed with explicit
  uncertainty;
- proof and counterexample receipts replay from immutable inputs;
- content-addressed caching is deterministic and incrementally invalidated;
- ZK attestations, if enabled, verify only their documented statement;
- stable bugs and vulnerabilities generate deduplicated, bounded supervisor
  tasks;
- Codex and Grok repair tasks through isolated worktrees and deterministic
  completion gates;
- drained-backlog refills consume new analyzer findings without unbounded goal
  or task growth; and
- current-tree coverage, exhaustion quorum, security review, rollback, and
  release receipts are present for the package-scoped proof statement.

A later Swissknife/three-package composition scan is a separate, deferred
milestone. It cannot be used as a substitute for, or prerequisite to, the
first complete `ipfs_datasets_py` proof scan.
