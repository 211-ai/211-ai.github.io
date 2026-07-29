# ipfs_datasets_py Symbolic Contract and Dataset Manipulator Objective Heap

This reviewed objective heap is the durable source of intent for repairing the
`ipfs_datasets_py` dataset manipulation surface and building deterministic,
content-addressed contract analysis across Swissknife, `ipfs_accelerate_py`,
`ipfs_kit_py`, and `ipfs_datasets_py`.

The human architecture is
[`DATASETS_CONTRACT_ANALYSIS_PLAN.md`](DATASETS_CONTRACT_ANALYSIS_PLAN.md).
The executable projection is
[`DATASETS_CONTRACT_ANALYSIS_TODO.md`](DATASETS_CONTRACT_ANALYSIS_TODO.md).

Program invariants:

- Integration target is `codex/datasets-contract-analysis`.
- The configured Swissknife source defaults to `/home/barberb/swissknife` and
  is read-only analysis input; its exact commit/tree must be recorded.
- Static discovery, identities, graph construction, proof, findings,
  deduplication, and task admission are deterministic and content addressed.
- No Python `hash()`, `id()`, randomness, timestamps, absolute worktree paths,
  or `repr` fallback enters a durable semantic identity.
- Every tracked object receives a CID and disposition. Unsupported semantics,
  incomplete shards, dynamic calls, timeout, stale evidence, and analyzer
  errors fail closed.
- GraphRAG retrieves and slices evidence; it is not proof authority.
- ZK evidence may attest a pinned deterministic trace or verified receipt. It
  does not prove arbitrary Python or TypeScript correctness.
- LLM providers receive only admitted, bounded repair packets. They do not
  decide whether a contract mismatch exists or whether it is repaired.
- Production network access, credentials, auto-install, publication, and
  destructive changes are outside the default task authority.
- Shared schemas and control-plane files have one serialized owner.

## DSCON-G000 Deliver deterministic contract-drift discovery and repair

- Status: blocked
- Review only: true
- Parent:
- Fib priority: 1
- Priority: P0
- Track: contract-analysis-program
- Bundle: datasets-contract/control
- Parallel lane: control
- Conflict policy: serialize root evidence and delegate implementation to child goals
- Submodules: ipfs_accelerate_py, ipfs_datasets_py, ipfs_kit_py
- Resource class: cpu-large
- Token class: small
- Goal: Repair the dataset manipulator and deliver a deterministic, content-addressed, proof-scoped analysis and supervisor refill system whose primary proof subject is the exact pinned `ipfs_datasets_py` tree.
- Evidence: DSCON-G010, DSCON-G020, DSCON-G030, DSCON-G040, DSCON-G050, DSCON-G055, DSCON-G100, DSCON-G105, DSCON-G110, DSCON-G115, DSCON-G120, DSCON-G130, DSCON-G140, DSCON-G150, DSCON-G200, DSCON-G210, DSCON-G220, DSCON-G230, DSCON-G240, DSCON-G250, DSCON-G300, DSCON-G310, DSCON-G320, DSCON-G330, DSCON-G340, DSCON-G400, DSCON-G410, DSCON-G420, DSCON-G500, DSCON-G510, DSCON-G520, DSCON-G600, DSCON-G610, DSCON-G620, DSCON-G630, DSCON-G700, DSCON-G705, DSCON-G720, DSCON-G730
- Outputs:
- Validation: python scripts/validate_datasets_contract_analysis.py --check-all
- Acceptance: Every mandatory child goal has current-tree evidence or an explicit external blocker; the dataset manipulator has real deterministic semantics and thin adapters; the exact pinned `ipfs_datasets_py` tree has complete replayable disposition and supported-semantic coverage; proof verdicts are scoped and fail closed; stable findings produce deduplicated bounded tasks; Codex and Grok execute isolated repair lanes; rollback and release evidence are current. Boundary repositories are separately identified and cannot silently widen this completion statement.
- Gap task: Review child-goal evidence and completion quorum only; do not create an aggregate implementation edit or modify planning/control files.
- Refinement: Complete trust, identity, and baseline gates first; build AST, contracts, dataset repair, formal proof, and task projection in dependency-safe parallel lanes; run the package-only proof scan before any deferred boundary-composition expansion.
- Embedding query: deterministic symbolic contract analysis dataset manipulator swissknife content addressed cache proof vulnerability supervisor refill
- AST query: DatasetManipulator ContractIR ContractObligation ContractFinding RepairPacket ContractRefillProvider

## DSCON-G010 Freeze repository authorities, revisions, and drift inventory

- Status: active
- Parent: DSCON-G000
- Fib priority: 2
- Priority: P0
- Track: bootstrap
- Bundle: datasets-contract/bootstrap
- Parallel lane: bootstrap-inventory
- Conflict policy: owns only scope and drift audit artifacts
- Submodules: ipfs_accelerate_py, ipfs_datasets_py, ipfs_kit_py
- Resource class: cpu-medium
- Token class: small
- Goal: Record the authoritative 211-AI composition, recursive gitlinks, `/home/barberb/swissknife`, Hallucinate runtime package copies, current dataset manipulator surfaces, duplicate/shadowed definitions, mock-success paths, imports, tests, and revision drift before implementation changes.
- Evidence: data/datasets_contract_analysis/audit/source-roots.json, data/datasets_contract_analysis/audit/datasets-manipulator-drift.json, data/datasets_contract_analysis/audit/ownership-map.md
- Outputs: scripts/contract_analysis/audit_scope.py, data/datasets_contract_analysis/audit/source-roots.json, data/datasets_contract_analysis/audit/datasets-manipulator-drift.json, data/datasets_contract_analysis/audit/ownership-map.md
- Validation: python scripts/contract_analysis/audit_scope.py --check
- Acceptance: The report binds clean commit/tree IDs for every selected root and direct gitlink; records recursive mirror cycles without rescanning them; records Swissknife commit `df11f08f` or an explicit changed/absent status; records the Hallucinate datasets checkout at `8dc4f93e` and current package authority or their reviewed successors; reproduces known mock-success, nondeterministic identity, duplicate definition, missing import, and weak-test findings; unresolved authority fails closed.
- Gap task: Add a read-only deterministic audit and checked-in machine/human evidence; do not refactor production code.
- Refinement: A repository reference in documentation is not an authority until its path and Git identity are verified.
- Embedding query: repository root gitlink swissknife hallucinate datasets revision drift mock success duplicate definition ownership
- AST query: process_dataset DataProcessor DatasetManager load_dataset save_dataset convert_dataset_format generate_clusters

## DSCON-G020 Build recursive tracked-object and coverage manifests

- Status: active
- Parent: DSCON-G000
- Fib priority: 3
- Priority: P0
- Track: bootstrap
- Bundle: datasets-contract/bootstrap
- Depends on: DSCON-G010
- Parallel lane: bootstrap-coverage
- Conflict policy: owns repository manifest schemas and coverage receipts
- Submodules: ipfs_accelerate_py, ipfs_datasets_py, ipfs_kit_py
- Resource class: io-large
- Token class: small
- Goal: Traverse selected Git trees and recursive gitlinks by object identity, deduplicate mirrors and blobs, shard deterministically, and give every tracked object a CID, mode, language, parser disposition, exclusion reason, and coverage status.
- Evidence: data/datasets_contract_analysis/manifests/repository-root.json, data/datasets_contract_analysis/manifests/coverage.json
- Outputs: ipfs_datasets_py/ipfs_datasets_py/logic/software_contracts/repository.py, ipfs_datasets_py/ipfs_datasets_py/logic/software_contracts/coverage.py, ipfs_datasets_py/tests/unit/logic/software_contracts/test_repository_manifest.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/logic/software_contracts/test_repository_manifest.py
- Acceptance: Every tracked object in every selected clean tree is counted exactly once per logical root; recursive mirrors are cycle-safe; unsupported, generated, vendored, binary, archived, oversized, missing, and parseable paths remain explicit; shard counts sum to the root count; dirty or missing inputs yield `INCOMPLETE_SCAN`; two runs produce identical roots.
- Gap task: Implement a Git-object reader, repository identity model, deterministic shard plan, and coverage validator.
- Refinement: Hash unsupported blobs without pretending to parse or prove them.
- Embedding query: git tree blob gitlink recursive manifest coverage shard deduplicate repository identity
- AST query: RepositorySnapshot TrackedBlob GitlinkRecord CoverageDisposition CoverageReceipt

## DSCON-G030 Define the soundness, threat, and verdict policy

- Status: active
- Parent: DSCON-G000
- Fib priority: 2
- Priority: P0
- Track: trust
- Bundle: datasets-contract/trust
- Parallel lane: trust-policy
- Conflict policy: owns proof claim and threat-model documents
- Resource class: cpu-small
- Token class: small
- Goal: Define the supported semantic models, trusted computing base, contract authority order, analyzer adversaries, scan completeness rules, and exact proof/failure verdict vocabulary.
- Evidence: ipfs_datasets_py/docs/software_contracts/SOUNDNESS_AND_THREAT_MODEL.md, ipfs_datasets_py/docs/software_contracts/verdict-policy-v1.json
- Outputs: ipfs_datasets_py/docs/software_contracts/SOUNDNESS_AND_THREAT_MODEL.md, ipfs_datasets_py/docs/software_contracts/verdict-policy-v1.json, ipfs_datasets_py/tests/unit/logic/software_contracts/test_verdict_policy.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/logic/software_contracts/test_verdict_policy.py
- Acceptance: Policy distinguishes `PROVED_WITHIN_MODEL`, `VIOLATED_WITH_COUNTEREXAMPLE`, `UNKNOWN`, `UNSUPPORTED`, `INCOMPLETE_SCAN`, `STALE`, and `ERROR`; defines which evidence can satisfy completion; treats dynamic behavior and absent findings conservatively; states that GraphRAG, tests, types, simulated proofs, and ZK attestations have bounded authority.
- Gap task: Write machine-readable and human policy with positive and rejection fixtures.
- Refinement: Narrow provable claims are preferable to broad unsound claims.
- Embedding query: soundness threat model proof verdict unknown unsupported incomplete scan trusted computing base
- AST query: VerificationVerdict AssuranceLevel CompletionEvidence ProofAttestation

## DSCON-G040 Standardize canonical encoding, multihash, and CID profiles

- Status: active
- Parent: DSCON-G000
- Fib priority: 5
- Priority: P0
- Track: content-identity
- Bundle: datasets-contract/content
- Depends on: DSCON-G010, DSCON-G030
- Parallel lane: content-profile
- Conflict policy: sole owner of the software-contract CID profile
- Submodules: ipfs_accelerate_py, ipfs_datasets_py
- Resource class: cpu-small
- Token class: small
- Goal: Select one strict, versioned CIDv1 profile for source bytes and structured analysis artifacts and reconcile incompatible canonicalization behavior across datasets and accelerator code.
- Evidence: ipfs_datasets_py/docs/software_contracts/CID_PROFILE_V1.md, ipfs_datasets_py/tests/fixtures/software_contracts/cid_vectors.json
- Outputs: ipfs_datasets_py/ipfs_datasets_py/logic/software_contracts/content.py, ipfs_datasets_py/docs/software_contracts/CID_PROFILE_V1.md, ipfs_datasets_py/tests/unit/logic/software_contracts/test_content_identity.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/logic/software_contracts/test_content_identity.py
- Acceptance: Structured identity accepts only reviewed canonical types and rejects floats, bytes, sets, paths, NaN, host objects, and repr fallback; source uses raw/sha2-256 and structured artifacts use dag-json/sha2-256/base32 unless the ADR proves another profile; decode-and-recompute verifies every read; Python and JavaScript golden vectors match.
- Gap task: Implement strict domain-separated canonical encoders and cross-runtime golden vectors by adapting `utils.cid_utils`, not copying permissive fallbacks.
- Refinement: Existing task IDs remain versioned compatibility identities and are not silently reinterpreted.
- Embedding query: canonical dag json multiformats multihash cidv1 sha2 content identity golden vectors
- AST query: canonical_dag_json_bytes cid_for_bytes cid_for_obj CID multihash

## DSCON-G050 Pin hermetic toolchains, budgets, and no-network execution

- Status: active
- Parent: DSCON-G000
- Fib priority: 5
- Priority: P0
- Track: trust
- Bundle: datasets-contract/trust
- Depends on: DSCON-G030
- Parallel lane: trust-runtime
- Conflict policy: owns analyzer execution profile and resource policy
- Submodules: ipfs_accelerate_py, ipfs_datasets_py
- Resource class: cpu-medium
- Token class: small
- Goal: Define hermetic parser, TypeScript, solver, proof, Python, Node, dependency-lock, resource, and sandbox identities with hard bounds and no ambient network or credentials.
- Evidence: data/datasets_contract_analysis/policy/analyzer-profile-v1.json, data/datasets_contract_analysis/policy/resource-bounds-v1.json
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/agent_supervisor/contract_analysis/execution_profile.py, data/datasets_contract_analysis/policy/analyzer-profile-v1.json, ipfs_accelerate_py/test/api/test_agent_supervisor_contract_execution_profile.py
- Validation: python -m pytest -q ipfs_accelerate_py/test/api/test_agent_supervisor_contract_execution_profile.py
- Acceptance: Profiles bind tool and lock identities; enforce blob, file, AST-node, edge, SCC, recursion, timeout, memory, proof, receipt, finding, task, and prompt limits; reject network, auto-install, home-cache, credential, and write-root escape; resource exhaustion yields incomplete or unknown rather than pass.
- Gap task: Implement validated execution and budget profiles with hermetic environment tests.
- Refinement: Tool availability is a capability fact, never a reason to auto-install during analysis.
- Embedding query: hermetic analyzer parser solver toolchain resource budgets no network credentials sandbox
- AST query: AnalysisExecutionProfile ResourceBudget HermeticValidation CapabilitySnapshot

## DSCON-G055 Add lossless typed objective admission

- Status: active
- Parent: DSCON-G000
- Fib priority: 5
- Priority: P0
- Track: supervisor-governance
- Bundle: datasets-contract/supervisor-governance
- Depends on: DSCON-G030, DSCON-G050
- Parallel lane: objective-schema
- Conflict policy: sole owner of the typed objective compatibility projection, sidecar schema, and admission report
- Submodules: ipfs_accelerate_py
- Resource class: cpu-medium
- Token class: small
- Goal: Extend the objective Markdown projector or add a canonical typed sidecar so evidence producer kind/output schema/authority, criterion completion signals and bindings, completion authorization, assumptions, non-goals, freshness, resource envelopes, uncertainties, unsupported-semantic fallbacks, and refinement budgets survive projection and can be admitted without invented authority.
- Evidence: data/datasets_contract_analysis/agent_supervisor/goal-quality.json, ipfs_accelerate_py/test/api/test_agent_supervisor_datasets_contract_goal_quality.py
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/agent_supervisor/goal_quality.py, ipfs_accelerate_py/ipfs_accelerate_py/agent_supervisor/objective_tracker.py, ipfs_accelerate_py/test/api/test_agent_supervisor_datasets_contract_goal_quality.py
- Validation: python -m pytest -q ipfs_accelerate_py/test/api/test_agent_supervisor_goal_quality.py ipfs_accelerate_py/test/api/test_agent_supervisor_datasets_contract_goal_quality.py
- Acceptance: The current heap round trips through one versioned typed representation; every criterion has a nonempty completion signal plus declared producer and validation bindings; every producer has a reviewed kind, output schema, and authority; finite freshness/resource/refinement bounds are preserved; uncertainty and unsupported behavior retain disposition/fallback; strict lint has no error-severity debt; compatibility behavior remains covered; launcher reports remain bound to the exact heap CID.
- Gap task: Implement a backwards-compatible typed projection/sidecar and golden fixture, migrate this heap, persist its exact quality report, and add a gated-launch test without weakening the linter.
- Refinement: Until this goal is complete, the launcher may use only the documented structural legacy path and must report typed quality debt rather than claim typed admission.
- Embedding query: typed objective goal quality evidence producer output schema completion signal freshness resource refinement admission
- AST query: TypedGoal EvidenceProducer AcceptanceCriterion ValidationRule GoalQualityReport project_objective_markdown

## DSCON-G100 Implement immutable content-addressed analysis caching

- Status: active
- Parent: DSCON-G000
- Fib priority: 8
- Priority: P0
- Track: content-identity
- Bundle: datasets-contract/content
- Depends on: DSCON-G020, DSCON-G040, DSCON-G050
- Parallel lane: content-cache
- Conflict policy: owns software-contract cache implementation only
- Submodules: ipfs_datasets_py, ipfs_accelerate_py
- Resource class: io-large
- Token class: small
- Goal: Build an immutable local CAS and replaceable indexes whose reusable shard keys bind source/dependency closure, analyzer, configuration, semantics, policy, solver, and toolchain, while snapshot manifests separately bind those shard CIDs to the repository-tree CID.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/logic/software_contracts/cache.py, ipfs_datasets_py/tests/unit/logic/software_contracts/test_cache.py
- Outputs: ipfs_datasets_py/ipfs_datasets_py/logic/software_contracts/cache.py, ipfs_accelerate_py/ipfs_accelerate_py/agent_supervisor/contract_analysis/cache_adapter.py, ipfs_datasets_py/tests/unit/logic/software_contracts/test_cache.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/logic/software_contracts/test_cache.py ipfs_accelerate_py/test/api/test_agent_supervisor_contract_cache_adapter.py
- Acceptance: Cache writes are atomic and immutable; reads recompute identity and schema; poisoning, truncation, wrong snapshot membership, wrong toolchain, wrong policy, and dependency-change fixtures miss or reject; the global repository-tree CID is absent from reusable blob/symbol/slice keys and present in aggregate snapshot receipts; unknown/negative results have bounded leases and never satisfy completion; one-blob mutation invalidates only the expected reverse dependency closure.
- Gap task: Adapt existing proof/cache primitives behind a strict contract-analysis namespace and add corruption/invalidation tests.
- Refinement: Mutable indexes are conveniences and can be rebuilt from immutable records; whole-snapshot identities must not be confused with reusable shard identities.
- Embedding query: immutable content addressed cache source closure toolchain policy poisoning invalidation
- AST query: AnalysisCacheKey ImmutableCAS CacheReceipt ProofCache FormalVerificationCache

## DSCON-G105 Define the shared package scaffold and normalized AST/symbol IR

- Status: active
- Parent: DSCON-G000
- Fib priority: 8
- Priority: P0
- Track: source-analysis
- Bundle: datasets-contract/ast
- Depends on: DSCON-G020, DSCON-G040, DSCON-G050
- Parallel lane: ast-schema
- Conflict policy: sole owner of software_contracts package exports, schema-version registry, and language-neutral AST/symbol IR
- Submodules: ipfs_datasets_py
- Resource class: cpu-medium
- Token class: small
- Goal: Create the shared `logic/software_contracts` package scaffold and immutable language-neutral records for modules, definitions, scopes, symbols, signatures, source spans, imports, references, calls, effects, diagnostics, unsupported constructs, and frontend capability/version identities.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/logic/software_contracts/ast_ir.py, ipfs_datasets_py/tests/unit/logic/software_contracts/test_ast_ir.py
- Outputs: ipfs_datasets_py/ipfs_datasets_py/logic/software_contracts/__init__.py, ipfs_datasets_py/ipfs_datasets_py/logic/software_contracts/ast_ir.py, ipfs_datasets_py/ipfs_datasets_py/logic/software_contracts/schema_versions.py, ipfs_datasets_py/tests/unit/logic/software_contracts/test_ast_ir.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/logic/software_contracts/test_ast_ir.py
- Acceptance: Shared records reject ambiguous canonical values, separate parsing from resolution, carry source/provenance and frontend version identity, round trip through the canonical CID profile, and have deterministic golden roots; Python, TypeScript, and contract goals may import the records but may not independently edit shared exports or schema-version files.
- Gap task: Implement the minimal package scaffold, shared immutable IR, version registry, golden vectors, and ownership tests before either language frontend starts.
- Refinement: Keep language-specific syntax in frontend-owned records and change shared schemas only through this serialized owner.
- Embedding query: shared normalized ast symbol ir package scaffold schema version source span call effect diagnostic
- AST query: ASTRecord SymbolDefinition SourceSpan FrontendCapability SchemaVersion

## DSCON-G110 Implement a versioned Python AST and symbol frontend

- Status: active
- Parent: DSCON-G000
- Fib priority: 8
- Priority: P0
- Track: source-analysis
- Bundle: datasets-contract/ast
- Depends on: DSCON-G105
- Parallel lane: ast-python
- Conflict policy: owns Python frontend and fixtures; may not edit shared package exports, ast_ir.py, or schema_versions.py
- Submodules: ipfs_datasets_py
- Resource class: cpu-large
- Token class: small
- Goal: Parse Python without imports or execution and emit normalized modules, definitions, scopes, signatures, annotations, decorators, imports, calls, awaits, raises, state access, source spans, and explicit unsupported constructs.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/logic/software_contracts/python_frontend.py, ipfs_datasets_py/tests/fixtures/software_contracts/python
- Outputs: ipfs_datasets_py/ipfs_datasets_py/logic/software_contracts/python_frontend.py, ipfs_datasets_py/tests/unit/logic/software_contracts/test_python_frontend.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/logic/software_contracts/test_python_frontend.py
- Acceptance: Frontend reproduces duplicate/shadowed definitions and undefined-reference candidates in the dataset monolith; preserves async/generator/default/annotation facts; never imports analyzed code; malformed and unsupported syntax is explicit; normalized records and roots are deterministic across processes.
- Gap task: Extend the existing Python extractor and accelerator AST records into a versioned semantic frontend rather than treating lexical calls as resolved.
- Refinement: Parsing facts and resolution facts remain separate records.
- Embedding query: python ast symbol scope definition signature decorator call await raise state source span
- AST query: PythonASTExtractor build_python_ast_blob_record ASTBlobRecord SymbolDefinition

## DSCON-G115 Prove package-wide Python frontend totality

- Status: completed
- Parent: DSCON-G000
- Fib priority: 9
- Priority: P0
- Track: source-analysis
- Bundle: datasets-contract/ast
- Depends on: DSCON-G020, DSCON-G110
- Parallel lane: ast-python-exhaustion
- Conflict policy: owns the package-corpus AST runner, frontend totality repairs, and exhaustion fixtures; serializes edits to python_frontend.py with G110
- Submodules: ipfs_datasets_py
- Resource class: cpu-large
- Token class: small
- Goal: Run the non-executing Python frontend over every parseable Python blob in the exact clean pinned `ipfs_datasets_py` Git tree and make every blob produce a deterministic AST record or an explicit bounded unsupported/error record without an uncaught exception.
- Evidence: data/datasets_contract_analysis/scans/ipfs_datasets_py/baseline/ast-baseline.json, ipfs_datasets_py/tests/integration/logic/software_contracts/test_python_frontend_repository_corpus.py
- Outputs: scripts/contract_analysis/run_ipfs_datasets_ast_baseline.py, ipfs_datasets_py/ipfs_datasets_py/logic/software_contracts/python_frontend.py, ipfs_datasets_py/tests/integration/logic/software_contracts/test_python_frontend_repository_corpus.py
- Validation: python scripts/contract_analysis/run_ipfs_datasets_ast_baseline.py --check --output-dir data/datasets_contract_analysis/scans/ipfs_datasets_py/baseline
- Acceptance: The receipt binds the current datasets commit, tree, package-only repository-root CID, frontend/toolchain CID, and ordered AST-record root; eligible count equals AST plus explicit unsupported/error counts; no analyzed blob escapes as an exception; two runs are byte-identical apart from excluded operational timing; whitespace/control-character, malformed syntax, deep-tree, encoding, and resource-limit corpus cases fail closed; any nonzero unhandled failure count yields `INCOMPLETE_SCAN` and blocks G130 and all proof claims.
- Gap task: Reproduce the current full-corpus ASTIR validation failures, repair normalization at the frontend/IR boundary without weakening canonical validation, and publish a compact deterministic exhaustion receipt.
- Refinement: Unit fixtures are necessary but not sufficient; the tracked package corpus is the exhaustion authority and archived/generated dispositions remain explicit.
- Embedding query: ipfs_datasets_py package corpus python ast totality exhaustion unhandled ASTIRValidationError whitespace control character
- AST query: PythonASTExtractor ASTRecord ASTIRValidationError UnsupportedConstruct RepositorySnapshot

## DSCON-G120 Implement real TypeScript and JavaScript AST frontends

- Status: active
- Parent: DSCON-G000
- Fib priority: 8
- Priority: P0
- Track: source-analysis
- Bundle: datasets-contract/ast
- Depends on: DSCON-G105
- Parallel lane: ast-typescript
- Conflict policy: owns TypeScript Compiler API adapter and JS-family fixtures; may not edit shared package exports, ast_ir.py, or schema_versions.py
- Submodules: ipfs_datasets_py
- Resource class: cpu-large
- Token class: small
- Goal: Use a pinned TypeScript Compiler API worker to parse `.ts`, `.tsx`, `.js`, `.jsx`, `.mts`, `.mjs`, and `.cjs` source and emit the same versioned AST/symbol facts without regex claims.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/logic/software_contracts/typescript_frontend.py, ipfs_datasets_py/scripts/software_contracts/typescript_ast_worker.mjs
- Outputs: ipfs_datasets_py/ipfs_datasets_py/logic/software_contracts/typescript_frontend.py, ipfs_datasets_py/scripts/software_contracts/typescript_ast_worker.mjs, ipfs_datasets_py/tests/unit/logic/software_contracts/test_typescript_frontend.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/logic/software_contracts/test_typescript_frontend.py
- Acceptance: Frontend parses representative Swissknife imports/exports/reexports/classes/interfaces/functions/async/calls/throws and JSX/TSX; Node protocol is bounded JSONL with no code execution; missing compiler capability yields unsupported; golden AST roots are deterministic.
- Gap task: Add the real compiler-backed worker, Python adapter, fixtures, and capability probe.
- Refinement: Existing regex indexes may seed retrieval but cannot satisfy this goal.
- Embedding query: typescript compiler api javascript tsx jsx ast imports exports interfaces calls throws
- AST query: TypeScriptFrontend TypeScriptASTWorker SourceFile TypeChecker Symbol

## DSCON-G130 Resolve cross-repository modules, imports, exports, and protocols

- Status: active
- Parent: DSCON-G000
- Fib priority: 13
- Priority: P0
- Track: source-analysis
- Bundle: datasets-contract/graph
- Depends on: DSCON-G115, DSCON-G120
- Parallel lane: graph-resolution
- Conflict policy: owns resolver and resolution fixtures
- Submodules: ipfs_accelerate_py, ipfs_datasets_py, ipfs_kit_py
- Resource class: cpu-large
- Token class: small
- Goal: Resolve Python and JS-family module paths, aliases, reexports, inheritance, Protocol/ABC implementations, package exports, optional imports, and cross-repository boundaries against the pinned composition.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/logic/software_contracts/resolver.py, ipfs_datasets_py/tests/fixtures/software_contracts/resolution
- Outputs: ipfs_datasets_py/ipfs_datasets_py/logic/software_contracts/resolver.py, ipfs_datasets_py/tests/unit/logic/software_contracts/test_resolver.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/logic/software_contracts/test_resolver.py
- Acceptance: Definite, finite-may, unresolved, optional, missing, and revision-mismatch results are distinct; package mirrors do not create false owners; Swissknife/Hallucinate/package imports bind to recorded revisions; resolution never imports or executes target code.
- Gap task: Implement language-aware resolution with repository composition and optional-dependency models.
- Refinement: Ambiguous targets remain finite may-sets or unknown; they are not guessed.
- Embedding query: module import alias reexport protocol abc inheritance optional dependency cross repository resolution
- AST query: SymbolResolver ImportEdge ExportEdge ProtocolImplementation RepositoryComposition

## DSCON-G140 Build conservative call, effect, exception, and dataflow graphs

- Status: active
- Parent: DSCON-G000
- Fib priority: 21
- Priority: P0
- Track: source-analysis
- Bundle: datasets-contract/graph
- Depends on: DSCON-G130
- Parallel lane: graph-calls
- Conflict policy: owns call/effect graph schemas and builders
- Submodules: ipfs_accelerate_py, ipfs_datasets_py, ipfs_kit_py
- Resource class: cpu-large
- Token class: small
- Goal: Construct must-call, may-call, unresolved, await, raise/catch/swallow, return-use, state, capability, source/sink, and resource-lifecycle edges with explicit path and confidence limits.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/logic/software_contracts/call_graph.py, ipfs_datasets_py/ipfs_datasets_py/logic/software_contracts/effects.py
- Outputs: ipfs_datasets_py/ipfs_datasets_py/logic/software_contracts/call_graph.py, ipfs_datasets_py/ipfs_datasets_py/logic/software_contracts/effects.py, ipfs_datasets_py/tests/unit/logic/software_contracts/test_call_graph.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/logic/software_contracts/test_call_graph.py
- Acceptance: Direct, protocol, method, higher-order, reflection, monkey-patch, dynamic import, and unresolved fixtures have correct certainty; exception swallowing and async misuse are represented; unknown edges prevent universal absence claims; graph roots and SCC shards are deterministic.
- Gap task: Add conservative interprocedural summaries and explicitly bounded dataflow.
- Refinement: False may-edges are preferable to unsoundly missing reachable behavior, but precision metrics must be published.
- Embedding query: conservative call graph effects exceptions dataflow async resource lifecycle must may unknown
- AST query: CallEdge EffectSummary ExceptionFlow DataflowEdge StronglyConnectedComponent

## DSCON-G150 Publish an IPLD evidence graph and deterministic GraphRAG index

- Status: active
- Parent: DSCON-G000
- Fib priority: 21
- Priority: P1
- Track: evidence-graph
- Bundle: datasets-contract/graph
- Depends on: DSCON-G100, DSCON-G140
- Parallel lane: graph-storage
- Conflict policy: owns evidence graph storage and retrieval
- Submodules: ipfs_datasets_py
- Resource class: io-large
- Token class: small
- Goal: Store repository, AST, symbol, call, contract, proof, finding, test, and provenance records as CID-linked graph shards with deterministic lexical/structural retrieval and optional non-authoritative embeddings.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/logic/software_contracts/evidence_graph.py, ipfs_datasets_py/ipfs_datasets_py/logic/software_contracts/retrieval.py
- Outputs: ipfs_datasets_py/ipfs_datasets_py/logic/software_contracts/evidence_graph.py, ipfs_datasets_py/ipfs_datasets_py/logic/software_contracts/retrieval.py, ipfs_datasets_py/tests/unit/logic/software_contracts/test_evidence_graph.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/logic/software_contracts/test_evidence_graph.py
- Acceptance: Every edge resolves to existing CID records; graph manifests verify and round trip; structural queries return reproducible slices; embedding absence or ranking changes cannot create/suppress facts, verdicts, or findings; retrieval budgets are enforced.
- Gap task: Adapt IPLD knowledge graph, graph-query, and GraphRAG components behind a proof-neutral evidence API.
- Refinement: Store evidence once by CID and keep query indexes replaceable.
- Embedding query: ipld knowledge graph graphrag deterministic retrieval evidence provenance cid
- AST query: IPLDKnowledgeGraph GraphRAGProcessor EvidenceGraph StructuralQuery RetrievalSlice

## DSCON-G200 Define the software contract IR and reviewed registry

- Status: active
- Parent: DSCON-G000
- Fib priority: 8
- Priority: P0
- Track: formal-contracts
- Bundle: datasets-contract/contracts
- Depends on: DSCON-G030, DSCON-G040, DSCON-G105
- Parallel lane: contracts-schema
- Conflict policy: sole owner of contract IR and registry schemas
- Submodules: ipfs_datasets_py
- Resource class: cpu-medium
- Token class: small
- Goal: Define versioned callable, data, effect, exception, capability, resource, temporal, determinism, schema, trust-boundary, provenance, and authority records for a deliberately bounded proof model.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/logic/software_contracts/contracts.py, ipfs_datasets_py/docs/schemas/software-contract-v1.schema.json
- Outputs: ipfs_datasets_py/ipfs_datasets_py/logic/software_contracts/contracts.py, ipfs_datasets_py/ipfs_datasets_py/logic/software_contracts/registry.py, ipfs_datasets_py/docs/schemas/software-contract-v1.schema.json, ipfs_datasets_py/tests/unit/logic/software_contracts/test_contract_ir.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/logic/software_contracts/test_contract_ir.py
- Acceptance: IR encodes explicit assumptions and source authority; rejects unbounded executable predicates and ambiguous canonical values; distinguishes declared, mechanically extracted, witnessed, and inferred facts; contradictory contracts are findings; schema round trips and CIDs are stable.
- Gap task: Implement immutable contract records, registry, JSON Schema, and golden vectors.
- Refinement: The IR supports only constructs that can be validated and lowered soundly.
- Embedding query: software contract ir precondition postcondition invariant effects exceptions capability resources provenance authority
- AST query: CallableContract EffectContract ResourceContract ContractRegistry ContractAuthority

## DSCON-G210 Extract contracts deterministically from source and schemas

- Status: active
- Parent: DSCON-G000
- Fib priority: 13
- Priority: P0
- Track: formal-contracts
- Bundle: datasets-contract/contracts
- Depends on: DSCON-G115, DSCON-G120, DSCON-G200
- Parallel lane: contracts-extraction
- Conflict policy: owns source-to-contract extractors
- Submodules: ipfs_datasets_py
- Resource class: cpu-large
- Token class: small
- Goal: Extract structural contracts from reviewed manifests, Protocol/ABC/stub/signature/annotation/decorator declarations, schemas, tests, and mechanically parsed documentation using fixed precedence and provenance.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/logic/software_contracts/extract.py, ipfs_datasets_py/tests/fixtures/software_contracts/contracts
- Outputs: ipfs_datasets_py/ipfs_datasets_py/logic/software_contracts/extract.py, ipfs_datasets_py/tests/unit/logic/software_contracts/test_contract_extraction.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/logic/software_contracts/test_contract_extraction.py
- Acceptance: Higher-authority sources cannot be silently overridden; docs are nominations rather than proof; tests are witnesses rather than universal claims; conflicting and missing evidence stays explicit; extraction runs without imports, code execution, network, or LLM.
- Gap task: Implement deterministic extractors and precedence/conflict fixtures.
- Refinement: Conservative inference cannot promote itself to reviewed contract authority.
- Embedding query: contract extraction protocol abc stub annotation decorator schema tests documentation precedence
- AST query: ContractExtractor Protocol Callable Signature JSONSchema PropertyTest

## DSCON-G220 Declare cross-package architecture, effect, and security policies

- Status: active
- Parent: DSCON-G000
- Fib priority: 13
- Priority: P0
- Track: formal-contracts
- Bundle: datasets-contract/contracts
- Depends on: DSCON-G010, DSCON-G200
- Parallel lane: contracts-policy
- Conflict policy: owns reviewed policy manifests, not package implementation
- Submodules: ipfs_accelerate_py, ipfs_datasets_py, ipfs_kit_py
- Resource class: cpu-medium
- Token class: small
- Goal: Declare ownership, dependency direction, wrapper delegation, optional dependency, no-mock-success, CID, persistence, network, secret, async, resource, and error-semantics policies for the three packages and Swissknife entrypoints.
- Evidence: data/datasets_contract_analysis/policy/cross-package-contracts-v1.json
- Outputs: data/datasets_contract_analysis/policy/cross-package-contracts-v1.json, ipfs_datasets_py/tests/contract/software_contracts/test_policy_registry.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/contract/software_contracts/test_policy_registry.py
- Acceptance: Policies name exact owners/interfaces/revisions and distinguish expected behavior from observations; no broad marketing statement becomes authoritative; exceptions are scoped and expiring; package/runtime revision mismatch is explicit; policy identity is content addressed.
- Gap task: Convert reviewed architecture and security invariants into a machine-readable registry with validation fixtures.
- Refinement: Start with high-value boundaries and extend through reviewed child policies.
- Embedding query: cross package architecture policy ownership wrapper delegation persistence no mock cid async security
- AST query: ArchitecturePolicy EffectPolicy PackageBoundary WrapperContract

## DSCON-G230 Generate caller/callee and policy proof obligations

- Status: active
- Parent: DSCON-G000
- Fib priority: 21
- Priority: P0
- Track: formal-verification
- Bundle: datasets-contract/formal
- Depends on: DSCON-G140, DSCON-G210, DSCON-G220
- Parallel lane: formal-obligations
- Conflict policy: owns obligation generation only
- Submodules: ipfs_datasets_py
- Resource class: cpu-large
- Token class: small
- Goal: Generate typed obligations for arguments/preconditions, postconditions/use, return/error shapes, exceptions, effects, resources, async/cancellation, schemas, identities, capabilities, security labels, and package policies.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/logic/software_contracts/obligations.py
- Outputs: ipfs_datasets_py/ipfs_datasets_py/logic/software_contracts/obligations.py, ipfs_datasets_py/tests/unit/logic/software_contracts/test_obligations.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/logic/software_contracts/test_obligations.py
- Acceptance: Obligations bind exact source closure, contracts, assumptions, semantics, and policy CIDs; must/may/unknown edges generate different claims; unsupported constructs cannot produce a proved obligation; golden valid, violated, and unknown examples are stable.
- Gap task: Implement small domain-separated obligation templates and fixtures.
- Refinement: Prefer many independently checkable obligations to one opaque whole-program formula.
- Embedding query: caller callee proof obligation precondition postcondition effects exceptions resources async schema
- AST query: ContractObligation CallContractObligation EffectCompatibility AssumptionSet

## DSCON-G240 Implement SMT, temporal-policy, and proof reconstruction

- Status: active
- Parent: DSCON-G000
- Fib priority: 21
- Priority: P0
- Track: formal-verification
- Bundle: datasets-contract/formal
- Depends on: DSCON-G100, DSCON-G230
- Parallel lane: formal-solvers
- Conflict policy: owns contract solver adapters and reconstruction
- Submodules: ipfs_datasets_py
- Resource class: cpu-large
- Token class: small
- Goal: Lower the reviewed finite contract subset to Z3/cvc5 and TDFOL/security constraints, validate translations, capture countermodels, and reconstruct high-value templates with an independent checker.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/logic/software_contracts/solver.py, ipfs_datasets_py/ipfs_datasets_py/logic/software_contracts/reconstruct.py
- Outputs: ipfs_datasets_py/ipfs_datasets_py/logic/software_contracts/solver.py, ipfs_datasets_py/ipfs_datasets_py/logic/software_contracts/reconstruct.py, ipfs_datasets_py/tests/unit/logic/software_contracts/test_solver.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/logic/software_contracts/test_solver.py
- Acceptance: Positive, negative, contradictory, timeout, unsupported, malformed, and mutation fixtures classify exactly; solver inputs and versions are retained; counterexamples replay concretely where possible; translation tests prevent polarity or implication reversal; simulation is non-authoritative.
- Gap task: Implement bounded translators, adapters, budgets, and independent template checks.
- Refinement: A solver `sat`/`unsat` string without replayable normalized input is not evidence.
- Embedding query: z3 cvc5 tdfol smt contract solver countermodel proof reconstruction mutation
- AST query: ContractSolver SolverReceipt Counterexample ProofReconstructor TDFOL

## DSCON-G250 Emit replayable proof and coverage receipts

- Status: active
- Parent: DSCON-G000
- Fib priority: 34
- Priority: P0
- Track: formal-verification
- Bundle: datasets-contract/formal
- Depends on: DSCON-G150, DSCON-G240
- Parallel lane: formal-receipts
- Conflict policy: owns receipt schemas and replay verifier
- Submodules: ipfs_accelerate_py, ipfs_datasets_py
- Resource class: cpu-large
- Token class: small
- Goal: Emit immutable receipts for proof, counterexample, unknown, unsupported, incomplete, stale, and error results and verify them against current tree, coverage, analyzer, policy, toolchain, and evidence roots.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/logic/software_contracts/receipts.py, ipfs_accelerate_py/ipfs_accelerate_py/agent_supervisor/contract_analysis/receipt_verifier.py
- Outputs: ipfs_datasets_py/ipfs_datasets_py/logic/software_contracts/receipts.py, ipfs_accelerate_py/ipfs_accelerate_py/agent_supervisor/contract_analysis/receipt_verifier.py, ipfs_accelerate_py/test/api/test_agent_supervisor_contract_receipts.py
- Validation: python -m pytest -q ipfs_accelerate_py/test/api/test_agent_supervisor_contract_receipts.py ipfs_datasets_py/tests/unit/logic/software_contracts/test_receipts.py
- Acceptance: Clean-process replay verifies all links and roots; tampered, stale, partial, wrong-policy, wrong-toolchain, missing-shard, and forged-status receipts fail; only allowed verdict/assurance combinations satisfy completion; receipts remain bounded.
- Gap task: Adapt IR-core, hammer receipt, accelerator assurance, and formal cache patterns into a strict cross-package receipt verifier.
- Refinement: Coverage and proof are separate linked receipts; neither substitutes for the other.
- Embedding query: proof receipt coverage receipt replay verifier stale tampered assurance current tree
- AST query: ContractAnalysisReceipt CoverageReceipt CompletionEvidence ReceiptVerifier AssuranceLevel

## DSCON-G300 Freeze dataset manipulation compatibility and failure baselines

- Status: active
- Parent: DSCON-G000
- Fib priority: 3
- Priority: P0
- Track: datasets-pilot
- Bundle: datasets-contract/datasets
- Depends on: DSCON-G010
- Parallel lane: datasets-baseline
- Conflict policy: owns dataset characterization fixtures and reports only
- Submodules: ipfs_datasets_py, ipfs_kit_py
- Resource class: cpu-medium
- Token class: small
- Goal: Characterize direct Python, MCP tool, MCP client, HTTP service, Swissknife descriptor, and ipfs_kit dataset load/save/convert/process contracts and freeze safe behavior, observed drift, mock-success failures, persistence effects, return/errors, IDs, and schema shapes.
- Evidence: data/datasets_contract_analysis/audit/dataset-contract-baseline.json, ipfs_datasets_py/tests/contract/core_operations/test_dataset_manipulator_baseline.py
- Outputs: data/datasets_contract_analysis/audit/dataset-contract-baseline.json, ipfs_datasets_py/tests/fixtures/dataset_manipulator, ipfs_datasets_py/tests/contract/core_operations/test_dataset_manipulator_baseline.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/contract/core_operations/test_dataset_manipulator_baseline.py
- Acceptance: Fixtures reproduce pass/no-op transformations, fabricated counts, random hash/id identities, no-write saves, no-conversion converts, fallback sample datasets, duplicate/shadowed monolith methods, missing calls/imports, kit integration failures, and weak wrappers; safe existing vectors are preserved; vulnerabilities are expected failures, not compatibility promises.
- Gap task: Add immutable fixtures and expected-failure characterization without fixing production code.
- Refinement: Observe actual artifacts and side effects, not dictionary shape alone.
- Embedding query: dataset manipulator baseline load save convert process mcp client http kit swissknife mock persistence
- AST query: DataProcessor DatasetManager DatasetLoader DatasetSaver DatasetConverter process_dataset

## DSCON-G310 Define canonical dataset operations, artifacts, and receipts

- Status: active
- Parent: DSCON-G000
- Fib priority: 13
- Priority: P0
- Track: datasets-pilot
- Bundle: datasets-contract/datasets
- Depends on: DSCON-G200, DSCON-G300
- Parallel lane: datasets-contract
- Conflict policy: sole owner of dataset operation schemas
- Submodules: ipfs_datasets_py
- Resource class: cpu-medium
- Token class: small
- Goal: Define typed `DatasetRef`, `ArtifactRef`, `DatasetOperationPlan`, operation registry, provenance, limits, partial/error semantics, and `DatasetOperationReceipt` with deterministic CIDs.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/core_operations/dataset_contracts.py, ipfs_datasets_py/docs/schemas/dataset-operation-v1.schema.json
- Outputs: ipfs_datasets_py/ipfs_datasets_py/core_operations/dataset_contracts.py, ipfs_datasets_py/docs/schemas/dataset-operation-v1.schema.json, ipfs_datasets_py/tests/unit/core_operations/test_dataset_contracts.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/core_operations/test_dataset_contracts.py
- Acceptance: Supported operations and parameters are finite and schema validated; IDs derive from canonical input/plan/output facts; ordering, seed, materialization, row/byte/time budgets, schema transitions, unsupported behavior, and errors are explicit; arbitrary code/callable deserialization is impossible.
- Gap task: Implement immutable schemas, registry, canonical identity, and golden round trips.
- Refinement: Extend operations only with semantic fixtures and reviewed resource behavior.
- Embedding query: dataset ref artifact operation plan receipt provenance deterministic cid filter map normalize shuffle
- AST query: DatasetRef ArtifactRef DatasetOperationPlan DatasetOperationReceipt OperationRegistry

## DSCON-G320 Implement the real bounded DatasetManipulator core

- Status: active
- Parent: DSCON-G000
- Fib priority: 21
- Priority: P0
- Track: datasets-pilot
- Bundle: datasets-contract/datasets
- Depends on: DSCON-G310
- Parallel lane: datasets-core
- Conflict policy: owns core dataset manipulation implementation and focused tests
- Submodules: ipfs_datasets_py
- Resource class: cpu-large
- Token class: medium
- Goal: Implement actual atomic load, save, convert, and bounded process behavior for the canonical operation plan and remove fabricated success from core paths.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/core_operations/dataset_manipulator.py, ipfs_datasets_py/tests/unit/core_operations/test_dataset_manipulator.py
- Outputs: ipfs_datasets_py/ipfs_datasets_py/core_operations/dataset_manipulator.py, ipfs_datasets_py/ipfs_datasets_py/core_operations/dataset_loader.py, ipfs_datasets_py/ipfs_datasets_py/core_operations/dataset_saver.py, ipfs_datasets_py/ipfs_datasets_py/core_operations/dataset_converter.py, ipfs_datasets_py/tests/unit/core_operations/test_dataset_manipulator.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/core_operations/test_dataset_contracts.py ipfs_datasets_py/tests/unit/core_operations/test_dataset_manipulator.py
- Acceptance: Successful save creates and verifies an artifact atomically; conversion round trips content/schema; supported operations transform actual rows; unsupported backends fail explicitly; identifiers are cross-process deterministic; no sample/mock fallback, eval/import, unbounded materialization, ambient network, or silent partial success remains.
- Gap task: Build the core around injected source/sink/format adapters and deterministic offline fixtures.
- Refinement: Deprecate legacy monolith ownership behind adapters rather than fixing unrelated monolith behavior opportunistically.
- Embedding query: real dataset manipulator atomic load save convert process deterministic bounded offline
- AST query: DatasetManipulator DatasetLoader DatasetSaver DatasetConverter apply_operation

## DSCON-G330 Make MCP, client/HTTP, Swissknife, and ipfs_kit dataset adapters thin

- Status: active
- Parent: DSCON-G000
- Fib priority: 34
- Priority: P0
- Track: datasets-pilot
- Bundle: datasets-contract/datasets-integration
- Depends on: DSCON-G320
- Parallel lane: datasets-adapters
- Conflict policy: owns entrypoint adapters and integration tests; core schemas stay unchanged
- Submodules: ipfs_accelerate_py, ipfs_datasets_py, ipfs_kit_py
- Resource class: cpu-large
- Token class: medium
- Goal: Delegate the existing direct Python, MCP tool, MCP client, and HTTP dataset entrypoints to the canonical core, repair live registration plus VFS/GraphRAG dataset integration, and retain only request/response translation and compatibility notices in wrappers; inspect Swissknife descriptors as read-only contract consumers and do not invent a dataset CLI.
- Evidence: ipfs_datasets_py/tests/contract/core_operations/test_dataset_entrypoint_equivalence.py, ipfs_kit_py/tests/test_ipfs_datasets_integration_contract.py
- Outputs: ipfs_datasets_py/ipfs_datasets_py/mcp_server/tools/dataset_tools/load_dataset.py, ipfs_datasets_py/ipfs_datasets_py/mcp_server/tools/dataset_tools/process_dataset.py, ipfs_datasets_py/ipfs_datasets_py/mcp_server/tools/dataset_tools/save_dataset.py, ipfs_datasets_py/ipfs_datasets_py/mcp_server/tools/dataset_tools/convert_dataset_format.py, ipfs_datasets_py/ipfs_datasets_py/mcp_server/tools/dataset_tools/__init__.py, ipfs_datasets_py/ipfs_datasets_py/mcp_server/client.py, ipfs_datasets_py/ipfs_datasets_py/mcp_server/fastapi_service.py, ipfs_datasets_py/ipfs_datasets_py/mcp_server/simple_server.py, ipfs_datasets_py/ipfs_datasets_py/mcp_server/hierarchical_tool_manager.py, ipfs_kit_py/ipfs_kit_py/ipfs_datasets_integration.py, ipfs_kit_py/ipfs_kit_py/vfs_bucket_graphrag_integration.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/contract/core_operations/test_dataset_entrypoint_equivalence.py ipfs_kit_py/tests/test_ipfs_datasets_integration_contract.py
- Acceptance: Direct Python/MCP-tool/client/HTTP adapters return equivalent receipts and errors; `dataset_tools/__init__.py`, `simple_server.py`, and `hierarchical_tool_manager.py` expose and dispatch the same four load/process/save/convert contracts; wrappers contain no manipulation, identity, fabricated counts, mock persistence, or success fallback; kit validates CIDs through the canonical API and observes real artifacts; GraphRAG integration uses actual current method signatures; Swissknife descriptor expectations are checked without mutating its repository; optional dependency absence fails or degrades exactly as declared; no CLI equivalence is claimed until a separately reviewed CLI exists.
- Gap task: Replace mock/fallback adapter paths with thin delegation and cross-package fixtures.
- Refinement: External Swissknife source remains read-only; repair package adapters first and create separately authorized Swissknife tasks for source edits. `mcp_server/server.py` also names the `dataset_tools` directory and is contract evidence, but it is not an edit target unless a focused registration mismatch proves a change is required.
- Embedding query: thin dataset adapter mcp client http swissknife ipfs kit vfs graphrag live binding
- AST query: load_dataset process_dataset save_dataset convert_dataset_format IPFSDatasetsClient IPFSDatasetsIntegration VFSBucketGraphRAGIntegration

## DSCON-G340 Prove the dataset manipulator pilot contracts

- Status: active
- Parent: DSCON-G000
- Fib priority: 55
- Priority: P0
- Track: datasets-pilot
- Bundle: datasets-contract/datasets-integration
- Depends on: DSCON-G230, DSCON-G250, DSCON-G330
- Parallel lane: datasets-proof
- Conflict policy: owns pilot proof registry and receipts
- Submodules: ipfs_accelerate_py, ipfs_datasets_py, ipfs_kit_py
- Resource class: cpu-large
- Token class: small
- Goal: Run the contract pipeline over direct Python, MCP-tool/client/HTTP, and ipfs_kit dataset entrypoints and prove or refute delegation, identity, persistence, return/error, optional dependency, effect, and resource obligations within the reviewed model.
- Evidence: data/datasets_contract_analysis/pilot/dataset-manipulator-proof-root.json
- Outputs: data/datasets_contract_analysis/pilot/dataset-manipulator-contracts.json, data/datasets_contract_analysis/pilot/dataset-manipulator-proof-root.json, ipfs_datasets_py/tests/contract/software_contracts/test_dataset_manipulator_proofs.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/contract/software_contracts/test_dataset_manipulator_proofs.py
- Acceptance: Every pilot entrypoint has a current receipt; known baseline violations become refuted before repair and proved-repaired or explicitly unsupported after repair; direct/MCP-tool/client/HTTP/kit witnesses agree; Swissknife descriptor expectations are checked as read-only evidence; no unknown or incomplete result is presented as repaired and no CLI equivalence is claimed.
- Gap task: Register pilot contracts, generate obligations, replay proofs/counterexamples, and publish the bounded result root.
- Refinement: This pilot validates the pipeline but does not imply whole-repository soundness.
- Embedding query: dataset manipulator formal contract proof delegation persistence identity entrypoint
- AST query: DatasetManipulator ContractObligation ContractAnalysisReceipt

## DSCON-G400 Implement deterministic vulnerability and defect rule packs

- Status: active
- Parent: DSCON-G000
- Fib priority: 21
- Priority: P0
- Track: security-analysis
- Bundle: datasets-contract/security
- Depends on: DSCON-G140, DSCON-G200
- Parallel lane: security-rules
- Conflict policy: owns rule definitions and fixtures
- Submodules: ipfs_accelerate_py, ipfs_datasets_py, ipfs_kit_py
- Resource class: cpu-large
- Token class: small
- Goal: Detect duplicate/shadowed definitions, missing symbols, mock success, swallowed exceptions, nondeterministic identity, injection, path/SSRF/secret flows, auth fail-open, insecure hash/nonce use, unbounded operations, async/cancellation/resource misuse, and unsafe persistence.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/logic/software_contracts/security_rules.py, ipfs_datasets_py/tests/fixtures/software_contracts/security
- Outputs: ipfs_datasets_py/ipfs_datasets_py/logic/software_contracts/security_rules.py, ipfs_datasets_py/tests/unit/logic/software_contracts/test_security_rules.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/logic/software_contracts/test_security_rules.py
- Acceptance: Every rule has positive, negative, unknown, suppression, reachability, and mutation fixtures; CWE mapping and severity are versioned; heuristic-only findings cannot become proved; conventional pinned SCA/SAST evidence can be linked with explicit coverage but does not claim completeness.
- Gap task: Implement high-confidence symbolic rules first and publish a coverage/limitation matrix.
- Refinement: A contract checker cannot find all vulnerabilities; layer independent tools and disclose gaps.
- Embedding query: static security vulnerability duplicate definition mock success swallowed exception injection ssrf secret async
- AST query: SecurityRule TaintFlow VulnerabilityFinding CWE DuplicateDefinition

## DSCON-G410 Detect cross-package contract and revision mismatches

- Status: active
- Parent: DSCON-G000
- Fib priority: 34
- Priority: P0
- Track: security-analysis
- Bundle: datasets-contract/security
- Depends on: DSCON-G220, DSCON-G230, DSCON-G400
- Parallel lane: security-cross-package
- Conflict policy: owns mismatch classifiers and fixtures
- Submodules: ipfs_accelerate_py, ipfs_datasets_py, ipfs_kit_py
- Resource class: cpu-large
- Token class: small
- Goal: Classify missing modules/symbols, signature/default, async/await, return/error, schema/version, CID/canonicalization, effect/policy, optional-fallback, wrapper/delegation, import-cycle, ownership, and runtime revision mismatches.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/logic/software_contracts/mismatches.py
- Outputs: ipfs_datasets_py/ipfs_datasets_py/logic/software_contracts/mismatches.py, ipfs_datasets_py/tests/contract/software_contracts/test_cross_package_mismatches.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/contract/software_contracts/test_cross_package_mismatches.py
- Acceptance: Synthetic and real dataset/kit/accelerator fixtures classify exact mismatch types with affected callers and counterexamples; revision drift is not misreported as a same-tree behavioral defect; may/unknown edges stay review-only.
- Gap task: Implement typed mismatch projection over obligations, graph edges, package manifests, and revision records.
- Refinement: Report one semantic root cause with affected callers instead of a task storm of duplicate symptoms.
- Embedding query: cross package contract mismatch revision signature async return schema cid optional wrapper ownership
- AST query: ContractMismatch RevisionMismatch InterfaceMismatch WrapperViolation

## DSCON-G420 Define stable findings, severity, deduplication, and suppressions

- Status: active
- Parent: DSCON-G000
- Fib priority: 34
- Priority: P0
- Track: security-analysis
- Bundle: datasets-contract/security
- Depends on: DSCON-G250, DSCON-G400
- Parallel lane: security-findings
- Conflict policy: sole owner of finding and suppression schemas
- Submodules: ipfs_accelerate_py, ipfs_datasets_py
- Resource class: cpu-medium
- Token class: small
- Goal: Define content-addressed findings with semantic identity, evidence roots, verdict, confidence, severity, reachability, affected symbols, owner, status, and scoped expiring suppressions.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/logic/software_contracts/findings.py, ipfs_datasets_py/docs/schemas/contract-finding-v1.schema.json
- Outputs: ipfs_datasets_py/ipfs_datasets_py/logic/software_contracts/findings.py, ipfs_datasets_py/docs/schemas/contract-finding-v1.schema.json, ipfs_datasets_py/tests/unit/logic/software_contracts/test_findings.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/logic/software_contracts/test_findings.py
- Acceptance: Unchanged mismatch identity is stable across scans; evidence revisions update observations without duplicating semantic findings; suppressions bind rule/finding/scope/reviewer/reason/expiry; unknown/stale/incomplete findings cannot be closed as safe; severity changes are auditable.
- Gap task: Implement schemas, semantic identity, lifecycle, dedupe, and suppression verification.
- Refinement: Finding identity excludes transient timestamps and absolute worktree paths.
- Embedding query: contract finding severity reachability deduplication suppression expiry semantic identity
- AST query: ContractFinding FindingIdentity FindingObservation FindingSuppression

## DSCON-G500 Define the exact zero-knowledge attestation statement

- Status: active
- Parent: DSCON-G000
- Fib priority: 34
- Priority: P1
- Track: zk-attestation
- Bundle: datasets-contract/zk
- Depends on: DSCON-G250
- Parallel lane: zk-policy
- Conflict policy: owns ZK statement, public inputs, threat model, and disclosure policy
- Submodules: ipfs_datasets_py
- Resource class: cpu-medium
- Token class: small
- Goal: Specify bounded public inputs, witness, circuit semantics, setup/verifier-key provenance, disclosure, trust, backend, and failure policy for opening a canonical analysis-trace commitment and attesting only the transition and completeness constraints actually encoded by the circuit.
- Evidence: ipfs_datasets_py/docs/software_contracts/ZK_ATTESTATION_V1.md, ipfs_datasets_py/docs/schemas/contract-zk-statement-v1.schema.json
- Outputs: ipfs_datasets_py/docs/software_contracts/ZK_ATTESTATION_V1.md, ipfs_datasets_py/docs/schemas/contract-zk-statement-v1.schema.json, ipfs_datasets_py/tests/unit/logic/software_contracts/test_zk_statement.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/logic/software_contracts/test_zk_statement.py
- Acceptance: Statement binds source-manifest, analyzer, config, contract, policy, toolchain, trace commitment, receipt, result-root, completeness counters, verifier key, and setup identities; labels commitment-only, partially constrained, and fully constrained trace statements distinctly; analyzer-execution language is forbidden unless every relevant transition, input opening, result derivation, and completeness check is circuit-verified; simulated/hash-only backends cannot satisfy production evidence.
- Gap task: Write reviewed schema, threat model, positive fixtures, and misleading-claim rejection tests.
- Refinement: ZK work cannot start by choosing a prover before defining the statement.
- Embedding query: zero knowledge attestation public inputs witness analyzer execution receipt verifier key setup
- AST query: ProofStatement PublicInputs VerificationKey ProofAttestation

## DSCON-G510 Implement a deterministic native trace and verifier

- Status: active
- Parent: DSCON-G000
- Fib priority: 55
- Priority: P1
- Track: zk-attestation
- Bundle: datasets-contract/zk
- Depends on: DSCON-G500
- Parallel lane: zk-trace
- Conflict policy: owns trace schema and native verifier
- Submodules: ipfs_datasets_py
- Resource class: cpu-large
- Token class: small
- Goal: Generate and independently verify a canonical bounded trace for hash/preimage, receipt-link, finite contract-state, verdict, and completeness checks before any ZK wrapper is trusted.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/logic/software_contracts/zk_trace.py
- Outputs: ipfs_datasets_py/ipfs_datasets_py/logic/software_contracts/zk_trace.py, ipfs_datasets_py/tests/unit/logic/software_contracts/test_zk_trace.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/logic/software_contracts/test_zk_trace.py
- Acceptance: Native verifier rejects tampered source, policy, analyzer, receipt, result, count, order, stale tree, malformed witness, and wrong-key fixtures; trace is deterministic and bounded; witness serialization has an explicit non-leak policy.
- Gap task: Implement the smallest useful trace and negative-test matrix.
- Refinement: Only natively verified trace semantics may be encoded in a circuit.
- Embedding query: deterministic analysis trace native verifier receipt links completeness tamper stale witness
- AST query: ContractAnalysisTrace NativeTraceVerifier TraceStep

## DSCON-G520 Add optional cryptographic proof-envelope integration

- Status: active
- Parent: DSCON-G000
- Fib priority: 89
- Priority: P1
- Track: zk-attestation
- Bundle: datasets-contract/zk
- Depends on: DSCON-G510
- Parallel lane: zk-backend
- Conflict policy: owns optional ProveKit/Groth16 adapter and proof fixtures
- Submodules: ipfs_datasets_py
- Resource class: cpu-large
- Token class: small
- Goal: Bind the native trace commitment to a reviewed ProveKit, Groth16, or equivalent production-capable proof envelope with verifier-key/setup provenance and fail-closed capability behavior, without claiming more trace semantics than the circuit checks.
- Evidence: ipfs_datasets_py/ipfs_datasets_py/logic/software_contracts/zk_attestation.py
- Outputs: ipfs_datasets_py/ipfs_datasets_py/logic/software_contracts/zk_attestation.py, ipfs_datasets_py/tests/integration/logic/software_contracts/test_zk_attestation.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/integration/logic/software_contracts/test_zk_attestation.py
- Acceptance: Valid commitment-opening fixture verifies; tampered trace commitment/public inputs/proof/key/setup fail; the receipt enumerates every transition and completeness constraint actually checked; analyzer execution is claimed only if all relevant steps are covered; simulated backends are labeled and rejected for production proof evidence; missing production backend records `not_enabled`, skips optional generation, and cannot manufacture proof; performance and disclosure measurements are recorded.
- Gap task: Reuse existing ZKP backend protocols and proof-attestation gates for the bounded trace.
- Refinement: A zkVM feasibility spike remains non-production until its image/toolchain identity and circuit semantics are reviewed.
- Embedding query: provekit groth16 cryptographic proof envelope verifier setup attestation fail closed
- AST query: ProveKitBackend Groth16Backend ProofAttestation ZKBackend

## DSCON-G600 Build bounded, CID-linked repair packets

- Status: active
- Parent: DSCON-G000
- Fib priority: 55
- Priority: P0
- Track: supervisor-integration
- Bundle: datasets-contract/supervisor
- Depends on: DSCON-G150, DSCON-G420
- Parallel lane: supervisor-context
- Conflict policy: owns repair packet compiler and context budgets
- Submodules: ipfs_accelerate_py, ipfs_datasets_py
- Resource class: cpu-medium
- Token class: small
- Goal: Compile each admissible finding into a minimal packet containing expected/observed contract, exact spans, bounded graph slice, proof/counterexample, permitted/protected paths, focused validation, and CIDs.
- Evidence: ipfs_accelerate_py/ipfs_accelerate_py/agent_supervisor/contract_analysis/repair_packet.py
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/agent_supervisor/contract_analysis/repair_packet.py, ipfs_accelerate_py/test/api/test_agent_supervisor_contract_repair_packet.py
- Validation: python -m pytest -q ipfs_accelerate_py/test/api/test_agent_supervisor_contract_repair_packet.py
- Acceptance: Default packets are at most 8 KiB and 2,048 estimated input tokens; exclude unrelated files, raw secrets, repository dumps, solver floods, and absolute host paths; all references resolve and recompute; truncation is explicit; unknown/ambiguous findings route to review.
- Gap task: Adapt context compiler and evidence graph retrieval for contract repair packets.
- Refinement: Increase a packet budget only through a named resource class and recorded necessity.
- Embedding query: minimal llm context repair packet contract mismatch counterexample graph slice token budget
- AST query: RepairPacket ContextBudget ContextCompiler EvidenceSlice

## DSCON-G610 Project findings into deterministic supervisor tasks

- Status: active
- Parent: DSCON-G000
- Fib priority: 55
- Priority: P0
- Track: supervisor-integration
- Bundle: datasets-contract/supervisor
- Depends on: DSCON-G600
- Parallel lane: supervisor-tasks
- Conflict policy: owns finding admission and task projection
- Submodules: ipfs_accelerate_py
- Resource class: cpu-medium
- Token class: small
- Goal: Admit current precise findings and project stable semantic identities into dependency-aware, owner-bound, resource-bounded tasks while blocking stale, unknown, incomplete, broad, or duplicate work.
- Evidence: ipfs_accelerate_py/ipfs_accelerate_py/agent_supervisor/contract_analysis/task_projection.py
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/agent_supervisor/contract_analysis/task_projection.py, ipfs_accelerate_py/test/api/test_agent_supervisor_contract_task_projection.py
- Validation: python -m pytest -q ipfs_accelerate_py/test/api/test_agent_supervisor_contract_task_projection.py
- Acceptance: One finding CID/semantic family creates one task; unchanged scans create none; changed observations update evidence without spending retries; exact paths/symbols/goals/dependencies/tests are required; unknown and manual-authority findings are non-schedulable; task IDs/CIDs are deterministic.
- Gap task: Integrate finding validation with backlog admission, task identity, quality, and conflict graph APIs.
- Refinement: Group symptoms only when they share a proven root cause and safe edit scope.
- Embedding query: finding to task projection deterministic admission dedupe goal dependency resource scope
- AST query: TaskProposalRouter TaskQuality ContractFinding TaskProjection

## DSCON-G620 Integrate symbolic contract refill with the agent supervisor

- Status: active
- Parent: DSCON-G000
- Fib priority: 89
- Priority: P0
- Track: supervisor-integration
- Bundle: datasets-contract/supervisor
- Depends on: DSCON-G055, DSCON-G610
- Parallel lane: supervisor-refill
- Conflict policy: owns contract refill provider and supervisor wiring
- Submodules: ipfs_accelerate_py
- Resource class: cpu-large
- Token class: medium
- Goal: Add a bounded contract-analysis provider to objective/codebase refill so low or drained backlogs reuse cached shards, scan changed closures, admit new findings, refine goals, and emit exhaustion/coverage receipts without LLM discovery.
- Evidence: ipfs_accelerate_py/ipfs_accelerate_py/agent_supervisor/contract_analysis/refill_provider.py
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/agent_supervisor/contract_analysis/refill_provider.py, ipfs_accelerate_py/ipfs_accelerate_py/agent_supervisor/todo_daemon/implementation_supervisor.py, ipfs_accelerate_py/test/api/test_agent_supervisor_contract_refill.py
- Validation: python -m pytest -q ipfs_accelerate_py/test/api/test_agent_supervisor_contract_refill.py
- Acceptance: Refill is content-addressed, bounded, cooldown/backpressure aware, objective-linked, idempotent, and disabled on incomplete authority; codebase and objective refills serialize; exhausted complete scans emit quorum receipts; scan failure leaves supervisors alive but cannot claim exhaustion.
- Gap task: Implement the provider boundary and focused supervisor integration without replacing existing guardrails.
- Refinement: Codex control lane owns refill writes; Grok remains execution-only.
- Embedding query: agent supervisor symbolic contract refill low backlog drained scan cached shards goals tasks
- AST query: PortalImplementationSupervisor refill_codebase_backlog refill_objective_backlog ContractRefillProvider

## DSCON-G630 Gate repair completion with patch-bound reanalysis and quorum

- Status: active
- Parent: DSCON-G000
- Fib priority: 89
- Priority: P0
- Track: supervisor-integration
- Bundle: datasets-contract/supervisor
- Depends on: DSCON-G620
- Parallel lane: supervisor-validation
- Conflict policy: owns completion artifact refresh and proof quorum
- Submodules: ipfs_accelerate_py, ipfs_datasets_py
- Resource class: cpu-large
- Token class: small
- Goal: Reanalyze changed blobs and dependants after each patch, bind focused tests and proof receipts to the candidate tree, require independent verification for high severity, and prevent task status or model text from satisfying completion.
- Evidence: data/datasets_contract_analysis/policy/completion-gate-v1.json
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/agent_supervisor/contract_analysis/completion_gate.py, scripts/contract_analysis/refresh_completion_evidence.py, ipfs_accelerate_py/test/api/test_agent_supervisor_contract_completion_gate.py
- Validation: python -m pytest -q ipfs_accelerate_py/test/api/test_agent_supervisor_contract_completion_gate.py
- Acceptance: Candidate-tree mismatch, stale receipt, omitted dependant, finding recurrence, weakened contract/test, incomplete scan, and single-checker high-severity evidence fail; valid repair transitions the original finding with provenance; root worktree and gitlinks remain clean.
- Gap task: Implement shell-free artifact refresh, patch-scope calculation, validation receipts, and quorum checks.
- Refinement: Goal completion reconciliation remains disabled until this artifact is healthy.
- Embedding query: repair completion gate patch bound reanalysis dependent proof quorum candidate tree
- AST query: CompletionGate CompletionEvidence CodeProofScope ExhaustionQuorum

## DSCON-G700 Prove incremental/full-scan equivalence and scale bounds

- Status: active
- Parent: DSCON-G000
- Fib priority: 89
- Priority: P0
- Track: rollout
- Bundle: datasets-contract/rollout
- Depends on: DSCON-G250, DSCON-G420
- Parallel lane: rollout-performance
- Conflict policy: owns benchmark fixtures and performance receipts
- Submodules: ipfs_accelerate_py, ipfs_datasets_py
- Resource class: cpu-xlarge
- Token class: small
- Goal: Measure full and incremental scans over representative large shards, prove result-set equivalence on mutation corpora, and set reviewed CPU/RSS/disk/time/cache/finding/context ceilings.
- Evidence: data/datasets_contract_analysis/benchmarks/scale-report.json, data/datasets_contract_analysis/benchmarks/incremental-equivalence.json
- Outputs: ipfs_datasets_py/benchmarks/bench_software_contract_analysis.py, data/datasets_contract_analysis/benchmarks/scale-report.json, ipfs_datasets_py/tests/integration/logic/software_contracts/test_incremental_equivalence.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/integration/logic/software_contracts/test_incremental_equivalence.py
- Acceptance: Changed-blob plus reverse-closure scan equals full-scan findings/receipts on the corpus; all shards are accounted; cache warm/cold results match; bounds stop safely; measured context reduction and false-positive/unknown rates are published; no default 8,192-file bound is mislabeled exhaustive.
- Gap task: Add mutation corpus, full/incremental comparator, benchmark runner, and reviewed initial ceilings.
- Refinement: Performance optimizations cannot weaken identities, coverage, or verdicts.
- Embedding query: incremental static analysis full scan equivalence benchmark cache context reduction scale
- AST query: IncrementalAnalysis AnalysisShard ReverseDependencyGraph ScaleReceipt

## DSCON-G705 Run the first complete ipfs_datasets_py proof scan

- Status: active
- Parent: DSCON-G000
- Fib priority: 100
- Priority: P0
- Track: rollout
- Bundle: datasets-contract/datasets-proof-scan
- Depends on: DSCON-G115, DSCON-G340, DSCON-G410, DSCON-G630, DSCON-G700
- Parallel lane: datasets-proof-scan
- Conflict policy: owns immutable package scan outputs and the generated package finding root
- Submodules: ipfs_datasets_py
- Resource class: cpu-xlarge
- Token class: small
- Goal: Inventory and analyze the exact clean pinned `ipfs_datasets_py` tree; emit disposition-complete AST, symbol, call, contract, obligation, proof, and finding roots; and publish the first package finding root to G620 while treating accelerator, kit, Swissknife, and other callers as boundary summaries only.
- Evidence: data/datasets_contract_analysis/scans/ipfs_datasets_py/scan-receipt.json, data/datasets_contract_analysis/scans/ipfs_datasets_py/proof-root.json, data/datasets_contract_analysis/scans/ipfs_datasets_py/finding-root.json
- Outputs: scripts/contract_analysis/verify_scan.py, data/datasets_contract_analysis/scans/ipfs_datasets_py
- Validation: python scripts/contract_analysis/verify_scan.py data/datasets_contract_analysis/scans/ipfs_datasets_py/scan-receipt.json --expected-logical-root ipfs_datasets_py
- Acceptance: The receipt binds the current datasets commit/tree plus repository, analyzer, policy, schema, frontend, solver, and tool CIDs; every tracked package object has exactly one disposition; every supported Python shard has AST, contract, obligation, and proof/counterexample/unknown/unsupported receipts; unhandled errors, missing shards, unknown, unsupported, stale, and incomplete results fail closed; findings identify exact package symbols and owners and are consumable by G620; no absence, safety, or exhaustion claim is made about boundary repositories.
- Gap task: Execute the hermetic package-only scan, verify every ordered root and count, triage finding authority, and publish immutable deterministic package findings without using an implementation worker to hand-edit the task board.
- Refinement: The dataset-manipulator proof is a pilot subset, not a substitute for package coverage; G710 is an optional later boundary-composition expansion.
- Embedding query: ipfs_datasets_py complete proof scan package ast contract obligation findings coverage cid
- AST query: RepositoryScan ASTRecord ContractObligation ContractFinding CoverageReceipt ProofReceipt

## DSCON-G710 Run the first complete Swissknife and three-package analysis

- Status: blocked
- Review only: true
- Parent: DSCON-G000
- Fib priority: 144
- Priority: P2
- Track: rollout
- Bundle: datasets-contract/rollout
- Depends on: DSCON-G705
- Parallel lane: rollout-full-scan
- Conflict policy: owns immutable scan outputs and generated finding backlog
- Submodules: ipfs_accelerate_py, ipfs_datasets_py, ipfs_kit_py
- Resource class: cpu-xlarge
- Token class: small
- Goal: Inventory and analyze the clean Swissknife tree and pinned package composition, publish complete/unsupported coverage plus proofs/findings, and make the first deterministic bug/vulnerability finding root available to the serialized refill provider for task projection.
- Evidence: data/datasets_contract_analysis/scans/initial/scan-receipt.json, data/datasets_contract_analysis/scans/initial/finding-root.json
- Outputs: data/datasets_contract_analysis/scans/initial
- Validation: python scripts/contract_analysis/verify_scan.py data/datasets_contract_analysis/scans/initial/scan-receipt.json
- Acceptance: All repository and analyzer shards are accounted; source/analyzer/policy/tool roots are current; unsupported languages/features and incomplete areas are explicit; findings dedupe and map to owners; unknown/heuristic issues are review-only; the verified finding root is consumable by G620 so its serialized control lane, not an implementation worker, generates bounded ipfs_accelerate_py tasks; absence claims require complete relevant coverage.
- Gap task: Deferred boundary-composition expansion; do not schedule until the package-only G705 scan and release evidence are reviewed.
- Refinement: External Swissknife edits require their own reviewed execution authority; this goal may analyze and propose tasks without mutating that repository, and it is not part of the first `ipfs_datasets_py` proof-scan completion statement.
- Embedding query: whole swissknife scan ipfs accelerate kit datasets bugs vulnerabilities coverage findings
- AST query: RepositoryScan ContractFinding CoverageReceipt TaskProposal

## DSCON-G720 Execute staged autonomous repair canaries and ratchets

- Status: active
- Parent: DSCON-G000
- Fib priority: 233
- Priority: P0
- Track: rollout
- Bundle: datasets-contract/rollout
- Depends on: DSCON-G705
- Parallel lane: rollout-repairs
- Conflict policy: tasks own exact leased files/symbols; shared contracts serialize
- Submodules: ipfs_accelerate_py, ipfs_datasets_py, ipfs_kit_py
- Resource class: cpu-large
- Token class: medium
- Goal: Let Codex and Grok repair high-confidence, low-blast-radius findings first, measure repair correctness and context use, then ratchet rule/severity/package autonomy only after reviewed gates.
- Evidence: data/datasets_contract_analysis/release/canary-report.json, data/datasets_contract_analysis/release/ratchet-policy.json
- Outputs: data/datasets_contract_analysis/release/canary-report.json, data/datasets_contract_analysis/release/ratchet-policy.json, data/datasets_contract_analysis/release/repair-quality.json
- Validation: python scripts/contract_analysis/verify_repair_canaries.py --check
- Acceptance: Canaries use isolated worktrees and leases; exact finding and dependant obligations are rechecked; tests/contracts are not weakened; no task loops or duplicate storms occur; token/context, false-positive, merge, retry, and rollback metrics meet policy before autonomy expands.
- Gap task: Select deterministic canaries, execute both shards, review receipts, and publish ratchet decisions.
- Refinement: Cryptography, authentication, destructive migration, publication, and production enablement remain higher-authority work.
- Embedding query: autonomous repair canary codex grok ratchet quality context metrics rollback
- AST query: RepairPacket ContractFinding CompletionGate TaskLease

## DSCON-G730 Validate release, rollback, security, and exhaustion

- Status: active
- Parent: DSCON-G000
- Fib priority: 377
- Priority: P0
- Track: release
- Bundle: datasets-contract/release
- Depends on: DSCON-G720
- Parallel lane: release
- Conflict policy: serialize final validation and release evidence
- Submodules: ipfs_accelerate_py, ipfs_datasets_py, ipfs_kit_py
- Resource class: cpu-xlarge
- Token class: small
- Goal: Run clean-tree double validation, independent proof and security review, cache/proof tamper tests, complete scan/exhaustion quorum, supervisor restart/reconciliation, and rollback rehearsal before release.
- Evidence: data/datasets_contract_analysis/release/release-evidence.json, data/datasets_contract_analysis/release/rollback-receipt.json
- Outputs: scripts/validate_datasets_contract_analysis.py, data/datasets_contract_analysis/release/release-evidence.json, data/datasets_contract_analysis/release/rollback-receipt.json, docs/software_contracts/OPERATIONS.md
- Validation: python scripts/validate_datasets_contract_analysis.py --check-all
- Acceptance: All mandatory tests pass twice from clean state; source/gitlink/analyzer/policy/tool roots match; independent checker/quorum is healthy; ZK capability is accurately classified as `not_enabled`, trace-commitment-only, partially constrained, or fully constrained and is not a mandatory ordinary-release dependency; critical/high admitted findings have repair or explicit blocker; supervisors restart and refill safely; rollback restores prior gitlinks/config/cache indexes; documentation states limitations and operations.
- Gap task: Build and execute the final hard gate, independent review, restart, and rollback rehearsal.
- Refinement: Release evidence is not production publication or authority to alter external Swissknife.
- Embedding query: release validation rollback security exhaustion quorum supervisor restart content addressed proof
- AST query: ReleaseEvidence RollbackReceipt ExhaustionQuorum SupervisorHealth

## DSCON-G731 Prove ipfs_datasets_py/tests/fixtures/software_contracts/cid_vectors.json for Standardize canonical encoding, multihash, and CID profiles

- Status: active
- Parent: DSCON-G040
- Fib priority: 5000
- Track: content-identity
- Priority: P0
- Bundle: datasets-contract/content
- Goal: Create concrete implementation, tests, docs, or interface descriptors proving `ipfs_datasets_py/tests/fixtures/software_contracts/cid_vectors.json`.
- Evidence: ipfs_datasets_py/tests/fixtures/software_contracts/cid_vectors.json
- Outputs: ipfs_datasets_py/ipfs_datasets_py/logic/software_contracts/content.py, ipfs_datasets_py/docs/software_contracts/CID_PROFILE_V1.md, ipfs_datasets_py/tests/unit/logic/software_contracts/test_content_identity.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/logic/software_contracts/test_content_identity.py
- Refinement depth: 2
- Embedding query: ipfs_datasets_py/tests/fixtures/software_contracts/cid_vectors.json
- AST query: ipfs_datasets_py/tests/fixtures/software_contracts/cid_vectors.json
- Parallel lane: content-profile
- Conflict policy: sole owner of the software-contract CID profile
- Gap task: Close the missing objective evidence `ipfs_datasets_py/tests/fixtures/software_contracts/cid_vectors.json` with a narrow, verifiable change.

## DSCON-G732 Prove data/datasets_contract_analysis/agent_supervisor/goal-quality.json for Add lossless typed objective admission

- Status: active
- Parent: DSCON-G055
- Fib priority: 5000
- Track: supervisor-governance
- Priority: P0
- Bundle: datasets-contract/supervisor-governance
- Goal: Create concrete implementation, tests, docs, or interface descriptors proving `data/datasets_contract_analysis/agent_supervisor/goal-quality.json`.
- Evidence: data/datasets_contract_analysis/agent_supervisor/goal-quality.json
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/agent_supervisor/goal_quality.py, ipfs_accelerate_py/ipfs_accelerate_py/agent_supervisor/objective_tracker.py, ipfs_accelerate_py/test/api/test_agent_supervisor_datasets_contract_goal_quality.py
- Validation: python -m pytest -q ipfs_accelerate_py/test/api/test_agent_supervisor_goal_quality.py ipfs_accelerate_py/test/api/test_agent_supervisor_datasets_contract_goal_quality.py
- Refinement depth: 2
- Embedding query: data/datasets_contract_analysis/agent_supervisor/goal-quality.json
- AST query: data/datasets_contract_analysis/agent_supervisor/goal-quality.json
- Parallel lane: objective-schema
- Conflict policy: sole owner of the typed objective compatibility projection, sidecar schema, and admission report
- Gap task: Close the missing objective evidence `data/datasets_contract_analysis/agent_supervisor/goal-quality.json` with a narrow, verifiable change.

## DSCON-G733 Prove ipfs_accelerate_py/test/api/test_agent_supervisor_datasets_contract_g... for Add lossless typed objective admission

- Status: active
- Parent: DSCON-G055
- Fib priority: 5000
- Track: supervisor-governance
- Priority: P0
- Bundle: datasets-contract/supervisor-governance
- Goal: Create concrete implementation, tests, docs, or interface descriptors proving `ipfs_accelerate_py/test/api/test_agent_supervisor_datasets_contract_goal_quality.py`.
- Evidence: ipfs_accelerate_py/test/api/test_agent_supervisor_datasets_contract_goal_quality.py
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/agent_supervisor/goal_quality.py, ipfs_accelerate_py/ipfs_accelerate_py/agent_supervisor/objective_tracker.py, ipfs_accelerate_py/test/api/test_agent_supervisor_datasets_contract_goal_quality.py
- Validation: python -m pytest -q ipfs_accelerate_py/test/api/test_agent_supervisor_goal_quality.py ipfs_accelerate_py/test/api/test_agent_supervisor_datasets_contract_goal_quality.py
- Refinement depth: 2
- Embedding query: ipfs_accelerate_py/test/api/test_agent_supervisor_datasets_contract_goal_quality.py
- AST query: ipfs_accelerate_py/test/api/test_agent_supervisor_datasets_contract_goal_quality.py
- Parallel lane: objective-schema
- Conflict policy: sole owner of the typed objective compatibility projection, sidecar schema, and admission report
- Gap task: Close the missing objective evidence `ipfs_accelerate_py/test/api/test_agent_supervisor_datasets_contract_goal_quality.py` with a narrow, verifiable change.
