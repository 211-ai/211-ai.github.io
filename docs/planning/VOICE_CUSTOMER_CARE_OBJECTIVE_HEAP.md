# Reusable Voice Customer-Care Objective Heap

This heap is the durable implementation program for the reusable platform
defined in
`docs/architecture/VOICE_CUSTOMER_CARE_PLATFORM_ARCHITECTURE.md`. It is
intended for `ipfs_accelerate_py.agent_supervisor` objective scanning,
goal/subgoal refinement, content-addressed todo generation, parallel bundle
lanes, deterministic validation, and bounded backlog refill.

The engine is application-neutral. `211-ai` is one reference domain pack, not
a package-level dependency. Autonomous workers must use fake or local
transports, must not place calls or mutate remote systems, and must not process
private caller data.

## VOICE-CARE-G001 Deliver the reusable voice customer-care platform boundary

- Status: active
- Fib priority: 1000
- Priority: P0
- Track: platform
- Goal: Define and integrate a provider-neutral, domain-pack-driven conversation and action platform that supports voice, web, chat, operator, tool, workflow, supervisor, and human-handoff paths without 211-specific engine logic.
- Evidence: stable public interaction and orchestration contracts; architecture ownership map; additive compatibility with existing voice_router APIs; offline integration fixture proving retrieval, clarification, confirmation, execution, handoff, response, and receipts
- Outputs: docs/architecture/VOICE_CUSTOMER_CARE_PLATFORM_ARCHITECTURE.md, ipfs_accelerate_py/ipfs_accelerate_py/conversation_runtime/__init__.py, tests/customer_care/test_platform_contract.py
- Validation: python -m pytest -q tests/customer_care/test_platform_contract.py
- Bundle: voice-care/platform-contract
- Parallel lane: voice-care-platform
- Embedding query: reusable voice customer care intake conversation action orchestration domain pack platform
- AST query: InteractionRequest, InteractionResult, ConversationOrchestrator, DomainPackRuntime
- Interfaces: voice_router, conversation GraphRAG, action runtime, portal gateway
- Submodules: ipfs_accelerate_py, ipfs_datasets_py
- Predicted files: docs/architecture/VOICE_CUSTOMER_CARE_PLATFORM_ARCHITECTURE.md, ipfs_accelerate_py/ipfs_accelerate_py/conversation_runtime/contracts.py, tests/customer_care/test_platform_contract.py
- Conflict policy: establish additive protocols and shared ownership first; preserve existing speech_to_text, text_to_speech, process_voice_turn, and process_telephone_turn behavior
- Gap task: Create the dependency-light top-level contracts and one fake-provider integration harness that child bundles can extend.
- Acceptance gate:
  1. Importing the platform starts no process, network client, model, prover, IPFS node, or optional provider.
  2. The same request/result contracts support telephone, web, chat, and operator channels.
  3. Application data is selected by pinned domain-pack identity rather than hard-coded 211 names.
  4. GraphRAG returns grounded response/action proposals and cannot directly invoke an adapter.
  5. Existing voice-router public APIs remain compatible and their focused tests pass.

## VOICE-CARE-G002 Define an immutable swappable domain-pack contract

- Status: active
- Fib priority: 2000
- Priority: P0
- Track: domain-data
- Parents: VOICE-CARE-G001
- Goal: Define canonical manifest and artifact schemas that package knowledge, ontology, intents, response frames, forms, action references, policies, localization, branding, and evaluations under one root CID.
- Evidence: DomainPackManifestV1 and referenced artifact schemas; canonical JSON and CID vectors; schema migration rules; malicious and incomplete pack rejection tests
- Outputs: ipfs_datasets_py/ipfs_datasets_py/conversation/domain_pack.py, ipfs_datasets_py/tests/unit/conversation/test_domain_pack.py, docs/schemas/VOICE_CUSTOMER_CARE_DOMAIN_PACK.md
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/conversation/test_domain_pack.py
- Bundle: voice-care/domain-pack
- Parallel lane: voice-care-data
- Embedding query: immutable domain pack manifest CID knowledge ontology forms actions policies localization branding evaluations
- AST query: DomainPackManifestV1, DomainPackArtifact, validate_domain_pack, domain_pack_cid
- Interfaces: CID multiformats, GraphRAG inputs, action descriptor references
- Submodules: ipfs_datasets_py
- Predicted files: ipfs_datasets_py/ipfs_datasets_py/conversation/domain_pack.py, ipfs_datasets_py/tests/unit/conversation/test_domain_pack.py, docs/schemas/VOICE_CUSTOMER_CARE_DOMAIN_PACK.md
- Conflict policy: schemas contain data and references only; reject executable code, raw commands, import paths, endpoints, secrets, and policy widening
- Gap task: Build the versioned pack contract and deterministic canonicalization before any application-specific migration.
- Acceptance gate:
  1. Byte-identical normalized input yields the same root CID.
  2. Every artifact is content-addressed and reachable from the manifest.
  3. Unknown schemas, dangling references, duplicate IDs, secrets, executable definitions, and mutable source references fail closed.
  4. A deployment can load two packs without sharing IDs, caches, policies, or private state.

## VOICE-CARE-G003 Generalize the conversation and action DAG schema

- Status: active
- Fib priority: 3000
- Priority: P0
- Track: domain-data
- Parents: VOICE-CARE-G001
- Depends on: VOICE-CARE-G002
- Goal: Replace response-only Abby node assumptions with generic intent, evidence-query, response-frame, form, decision, action-reference, confirmation, handoff, and terminal nodes plus typed deterministic guards.
- Evidence: versioned node and edge schemas; guard AST; graph integrity validation; bounded-loop expansion; migration fixtures for the current slotted response DAG
- Outputs: ipfs_datasets_py/ipfs_datasets_py/conversation/graph.py, ipfs_datasets_py/tests/unit/conversation/test_graph_schema.py, docs/schemas/VOICE_CUSTOMER_CARE_GRAPH.md
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/conversation/test_graph_schema.py
- Bundle: voice-care/graph-schema
- Parallel lane: voice-care-data
- Embedding query: generic conversation DAG intent evidence response form decision action confirmation handoff terminal guard
- AST query: ConversationGraph, ConversationNode, ConversationEdge, GuardExpression, compile_bounded_loop
- Interfaces: response_dag, slotted response graph, domain pack
- Submodules: ipfs_datasets_py
- Predicted files: ipfs_datasets_py/ipfs_datasets_py/conversation/graph.py, ipfs_datasets_py/tests/unit/conversation/test_graph_schema.py, docs/schemas/VOICE_CUSTOMER_CARE_GRAPH.md
- Conflict policy: retain append-only response-DAG compatibility; guards are data-only and side-effect-free
- Gap task: Define a generic graph model and lossless compatibility adapter for current voice response artifacts.
- Acceptance gate:
  1. The persisted graph is acyclic and every nonterminal path has a bounded terminal, clarification, or handoff outcome.
  2. Required slots are defined before use on every admitted path.
  3. Action nodes contain only catalog action ID and descriptor CID references.
  4. Arbitrary expressions, imports, templates with side effects, and unbounded cycles are rejected.

## VOICE-CARE-G004 Build the deterministic domain-pack compiler and validator

- Status: active
- Fib priority: 3001
- Priority: P0
- Track: domain-data
- Parents: VOICE-CARE-G001
- Depends on: VOICE-CARE-G002, VOICE-CARE-G003
- Goal: Compile normalized pack sources into immutable graph, retrieval, form, policy-overlay, localization, and evaluation artifacts with deterministic diagnostics and no network writes.
- Evidence: compiler API and CLI; stable artifact ordering; reproducibility receipt; actionable validation diagnostics; incremental content-addressed cache
- Outputs: ipfs_datasets_py/ipfs_datasets_py/conversation/compiler.py, ipfs_datasets_py/ipfs_datasets_py/conversation/cli.py, ipfs_datasets_py/tests/unit/conversation/test_compiler.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/conversation/test_compiler.py
- Bundle: voice-care/domain-pack-compiler
- Parallel lane: voice-care-data
- Embedding query: deterministic domain pack compiler graph retrieval form localization evaluation CID cache diagnostics
- AST query: DomainPackCompiler, CompilationReceipt, compile_domain_pack, validate_compiled_pack
- Interfaces: domain pack schemas, multiformats CID, GraphRAG index
- Submodules: ipfs_datasets_py
- Predicted files: ipfs_datasets_py/ipfs_datasets_py/conversation/compiler.py, ipfs_datasets_py/ipfs_datasets_py/conversation/cli.py, ipfs_datasets_py/tests/unit/conversation/test_compiler.py
- Conflict policy: compilation is local and read-only with respect to source data; no implicit upload, pin, or mutable remote fetch
- Gap task: Add a reproducible compiler whose complete output identity can be reviewed before runtime selection.
- Acceptance gate:
  1. Repeated builds from the same pinned inputs are byte-identical.
  2. Changed input affects only dependent artifacts and produces a new root CID.
  3. Diagnostics identify exact source artifact, node, edge, field, and invariant.
  4. Cache hits verify bytes and compiler identity before reuse.

## VOICE-CARE-G005 Generalize GraphRAG retrieval into grounded response and action proposals

- Status: active
- Fib priority: 4000
- Priority: P0
- Track: retrieval
- Parents: VOICE-CARE-G001
- Depends on: VOICE-CARE-G003, VOICE-CARE-G004
- Goal: Retrieve grounded response plans and ranked action references from a selected domain pack while preserving evidence, argument provenance, confidence, missing slots, and a strict non-execution boundary.
- Evidence: generic retrieval protocol; deterministic local index; optional injected GraphRAG adapters; action proposal candidates; prompt-injection fixtures; Abby adapter compatibility
- Outputs: ipfs_datasets_py/ipfs_datasets_py/conversation/retrieval.py, ipfs_datasets_py/tests/unit/conversation/test_retrieval.py, ipfs_accelerate_py/test/test_conversation_retrieval_adapter.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/conversation/test_retrieval.py ipfs_accelerate_py/test/test_conversation_retrieval_adapter.py
- Bundle: voice-care/retrieval
- Parallel lane: voice-care-retrieval
- Embedding query: GraphRAG grounded response action proposal evidence argument provenance confidence non execution
- AST query: ConversationPlanProvider, GroundedResponseCandidate, ActionProposalCandidate, retrieve_conversation_plan
- Interfaces: SlottedResponseIndex, GraphRAGVoiceTemplateProvider, domain pack, action proposal
- Submodules: ipfs_datasets_py, ipfs_accelerate_py
- Predicted files: ipfs_datasets_py/ipfs_datasets_py/conversation/retrieval.py, ipfs_datasets_py/tests/unit/conversation/test_retrieval.py, ipfs_accelerate_py/test/test_conversation_retrieval_adapter.py
- Conflict policy: retrieved content can rank registered action references but cannot create descriptors, authority, commands, imports, endpoints, or credentials
- Gap task: Extract the reusable retrieval kernel from Abby naming and add typed action-candidate output.
- Acceptance gate:
  1. Every factual response slot and action argument cites present current evidence or typed session input.
  2. Example responses and retrieved instructions are never treated as authority.
  3. Unknown action references and ungrounded required arguments are withheld.
  4. The existing voice GraphRAG provider remains usable through an adapter.

## VOICE-CARE-G006 Define typed action lifecycle contracts

- Status: active
- Fib priority: 3002
- Priority: P0
- Track: action-runtime
- Parents: VOICE-CARE-G001
- Depends on: VOICE-CARE-G003
- Goal: Define dependency-light ActionDescriptor, ActionProposal, ActionDecision, ActionInvocation, ActionReceipt, and normalized lifecycle contracts.
- Evidence: strict serializable dataclasses or models; status transition table; schema and hash identity; redaction-safe serialization; invalid transition tests
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/contracts.py, ipfs_accelerate_py/test/test_action_runtime_contracts.py, docs/schemas/VOICE_CUSTOMER_CARE_ACTIONS.md
- Validation: python -m pytest -q ipfs_accelerate_py/test/test_action_runtime_contracts.py
- Bundle: voice-care/action-contracts
- Parallel lane: voice-care-runtime
- Embedding query: action descriptor proposal decision invocation receipt lifecycle status schema hash redaction
- AST query: ActionDescriptor, ActionProposal, ActionDecision, ActionInvocation, ActionReceipt, ActionStatus
- Interfaces: domain graph action_ref, MCP IDL, workflow, human handoff
- Submodules: ipfs_accelerate_py
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/contracts.py, ipfs_accelerate_py/test/test_action_runtime_contracts.py, docs/schemas/VOICE_CUSTOMER_CARE_ACTIONS.md
- Conflict policy: keep contracts transport-neutral and optional-dependency safe; adapters cannot redefine lifecycle semantics
- Gap task: Land the shared action vocabulary before implementing any executable adapter.
- Acceptance gate:
  1. Proposal is explicitly non-authoritative and contains no secrets.
  2. Decision binds descriptor CID, normalized arguments hash, policy revision, capability, consent, and expiry.
  3. Receipt status distinguishes acceptance, start, success, failure, timeout, cancellation, unknown, and compensation.
  4. Invalid state transitions and malformed hashes, schemas, statuses, or secret-bearing fields fail closed.

## VOICE-CARE-G007 Build the deployment-owned action catalog and resolver

- Status: active
- Fib priority: 4001
- Priority: P0
- Track: action-runtime
- Parents: VOICE-CARE-G001
- Depends on: VOICE-CARE-G006
- Goal: Resolve domain-pack action references against an allowlisted deployment catalog with exact descriptor, schema, interface, owner, version, and capability identities.
- Evidence: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/catalog.py; ipfs_accelerate_py/test/test_action_catalog.py; immutable catalog snapshot; descriptor registration and discovery; CID and schema verification; duplicate/drift rejection; lazy adapter factories
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/catalog.py, ipfs_accelerate_py/test/test_action_catalog.py
- Validation: python -m pytest -q ipfs_accelerate_py/test/test_action_catalog.py
- Bundle: voice-care/action-catalog
- Parallel lane: voice-care-runtime
- Embedding query: deployment action catalog resolver allowlist descriptor CID schema interface capability lazy adapter
- AST query: ActionCatalog, ActionRegistration, ActionResolver, CatalogSnapshot
- Interfaces: MCP IDL registry, CLI registry, callable registry, workflow registry, supervisor control
- Submodules: ipfs_accelerate_py
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/catalog.py, ipfs_accelerate_py/test/test_action_catalog.py
- Conflict policy: domain packs may reference catalog entries but never register, replace, or widen them
- Gap task: Create a fail-closed resolver and capability-discovery snapshot shared by every adapter.
- Acceptance gate:
  1. Catalog identity changes when any executable or schema identity changes.
  2. Unknown, duplicated, stale, disabled, or capability-incompatible actions cannot resolve.
  3. Discovery constructs no optional provider and reveals no secret.
  4. Tenant and channel restrictions are preserved in the resolved descriptor.

## VOICE-CARE-G008 Enforce policy capability consent and confirmation before execution

- Status: active
- Fib priority: 5000
- Priority: P0
- Track: security
- Parents: VOICE-CARE-G001
- Depends on: VOICE-CARE-G006, VOICE-CARE-G007
- Goal: Produce deterministic deny, clarify, confirm, handoff, permit-read, or permit-execute decisions from deployment policy, descriptor risk, actor capability, consent, channel, tenant, and grounded arguments.
- Evidence: policy engine; adapter into the existing ipfs_datasets_py Intent IR pre-dispatch envelope; risk and side-effect taxonomy; consent/confirmation receipts; temporal expiry; policy-narrowing tests; emergency and code-change gates
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/policy.py, ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/intent_ir.py, ipfs_accelerate_py/test/test_action_policy.py, docs/specs/VOICE_CUSTOMER_CARE_ACTION_POLICY.md
- Validation: python -m pytest -q ipfs_accelerate_py/test/test_action_policy.py
- Bundle: voice-care/action-policy
- Parallel lane: voice-care-security
- Embedding query: action policy capability consent confirmation risk side effect tenant channel temporal decision
- AST query: ActionPolicy, ActionRisk, SideEffectClass, ConsentReceipt, ConfirmationReceipt, ActionIntentIRAdapter, evaluate_action
- Interfaces: ipfs_datasets_py logic Intent IR, MCP++ UCAN, temporal policy, wallet grants, domain policy overlay
- Submodules: ipfs_accelerate_py
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/policy.py, ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/intent_ir.py, ipfs_accelerate_py/test/test_action_policy.py, docs/specs/VOICE_CUSTOMER_CARE_ACTION_POLICY.md
- Conflict policy: reuse and preserve the existing Intent IR pre-dispatch envelope; domain and request policy can only narrow deployment authority; retrieval confidence never substitutes for consent or capability
- Gap task: Implement the single policy gate used by all transports.
- Acceptance gate:
  1. No adapter can be invoked without a current permit bound to exact arguments and descriptor.
  2. High-risk, irreversible, financial, identity, code-changing, and emergency actions have explicit policies.
  3. A changed argument, descriptor, tenant, actor, consent, or policy revision invalidates the decision.
  4. Intent IR binds tenant, actor, audience, tool/schema identity, argument commitment, scope, nonce, deadline, rollback, and verification before dispatch.
  5. Denial and confirmation behavior is truthful and channel-appropriate.

## VOICE-CARE-G009 Add content-addressed idempotent execution receipts and replay

- Status: active
- Fib priority: 5001
- Priority: P0
- Track: action-runtime
- Parents: VOICE-CARE-G001
- Depends on: VOICE-CARE-G006, VOICE-CARE-G008
- Goal: Execute admitted actions through a durable state machine with content-derived idempotency, bounded retry, cancellation, compensation, event-DAG lineage, and privacy-safe receipts.
- Evidence: execution coordinator; receipt CAS; idempotency store; crash/retry/replay tests; compensation and unknown-outcome behavior
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/executor.py, ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/receipts.py, ipfs_accelerate_py/test/test_action_execution.py
- Validation: python -m pytest -q ipfs_accelerate_py/test/test_action_execution.py
- Bundle: voice-care/action-execution
- Parallel lane: voice-care-runtime
- Embedding query: content addressed action execution idempotency receipt replay retry compensation event DAG crash recovery
- AST query: ActionExecutor, ActionReceiptStore, IdempotencyRecord, execute_action, replay_action
- Interfaces: MCP++ CID artifacts, event DAG, ipfs_kit storage adapter
- Submodules: ipfs_accelerate_py, ipfs_kit_py
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/executor.py, ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/receipts.py, ipfs_accelerate_py/test/test_action_execution.py
- Conflict policy: never retry an unknown or non-idempotent external side effect automatically; storage adapters remain optional
- Gap task: Build durable invocation semantics once so adapters cannot invent inconsistent retry or completion behavior.
- Acceptance gate:
  1. Equivalent admitted invocations share an idempotency identity scoped by tenant, pack, action, and policy.
  2. Replays return the prior receipt without repeating a completed side effect.
  3. Unknown outcomes remain unknown until reconciled and are never reported as success.
  4. Receipts exclude secrets and private payloads while preserving hashes and approved projections.

## VOICE-CARE-G010 Establish tenant session privacy and case-store boundaries

- Status: active
- Fib priority: 5002
- Priority: P0
- Track: privacy
- Parents: VOICE-CARE-G001
- Depends on: VOICE-CARE-G002, VOICE-CARE-G006, VOICE-CARE-G008
- Goal: Isolate domain packs, tenants, sessions, cases, caches, receipts, and private intake data behind typed storage and retention protocols.
- Evidence: SessionState and CaseStore protocols; field classification; retention and redaction policies; wallet adapter; cross-tenant non-interference and cache-poisoning tests
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/conversation_runtime/session.py, wallet_interface/helpers/customer_care_case_store.py, tests/customer_care/test_privacy_boundaries.py
- Validation: python -m pytest -q tests/customer_care/test_privacy_boundaries.py
- Bundle: voice-care/privacy-tenancy
- Parallel lane: voice-care-security
- Embedding query: tenant session case store privacy retention redaction wallet isolation cache non interference
- AST query: SessionState, CaseStore, DataClassification, RetentionPolicy, WalletCaseStore
- Interfaces: wallet records, HMIS consent, action receipts, domain pack cache
- Submodules: ipfs_accelerate_py
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/conversation_runtime/session.py, wallet_interface/helpers/customer_care_case_store.py, tests/customer_care/test_privacy_boundaries.py
- Conflict policy: public pack and GraphRAG artifacts never contain private intake, transcript, precise location, case, credential, or action-result data
- Gap task: Define storage interfaces and prove tenant/session identity participates in every private cache and receipt boundary.
- Acceptance gate:
  1. Raw caller audio is ephemeral by default and transcripts require explicit retention policy.
  2. Sensitive form fields declare purpose, necessity, retention, and disclosure.
  3. Cross-tenant and cross-pack reads, cache hits, action replays, and handoffs fail closed.
  4. Logs and ordinary receipts contain safe metadata and hashes only.

## VOICE-CARE-G011 Implement the MCP and MCP++ action adapter

- Status: active
- Fib priority: 6000
- Priority: P0
- Track: adapters
- Parents: VOICE-CARE-G001
- Depends on: VOICE-CARE-G007, VOICE-CARE-G008, VOICE-CARE-G009
- Goal: Invoke reviewed MCP tools through canonical discovery and dispatch and MCP++ tools through IDL, UCAN, temporal-policy, artifact, and event-DAG bindings.
- Evidence: capability and IDL discovery; input/output parity; descriptor drift and downgrade rejection; fake server tests; MCP and MCP++ receipts
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/adapters/mcp.py, ipfs_accelerate_py/test/test_action_mcp_adapter.py
- Validation: python -m pytest -q ipfs_accelerate_py/test/test_action_mcp_adapter.py ipfs_accelerate_py/mcp/tests/test_mcp_server_mcplusplus_idl.py
- Bundle: voice-care/adapter-mcp
- Parallel lane: voice-care-adapters
- Embedding query: MCP MCP++ action adapter dispatch IDL UCAN temporal policy CID artifact event DAG
- AST query: MCPActionAdapter, MCPPlusPlusActionAdapter, MCPInterfaceBinding
- Interfaces: unified MCP tools_dispatch, IDL registry, UCAN delegation, temporal policy
- Submodules: ipfs_accelerate_py
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/adapters/mcp.py, ipfs_accelerate_py/test/test_action_mcp_adapter.py
- Conflict policy: use canonical mcp_server surfaces; do not add a second dispatcher or bypass IDL and policy checks
- Gap task: Adapt existing MCP/MCP++ capabilities to the shared action lifecycle.
- Acceptance gate:
  1. The adapter verifies exact server, profile, tool, IDL, and schemas before dispatch.
  2. MCP++ capability and temporal policy cannot be widened by pack or request data.
  3. Contradictory or malformed delegate results normalize to failure.
  4. Tests perform no external mutation and cover stale descriptor, downgrade, timeout, denial, and success.

## VOICE-CARE-G012 Implement the sandboxed CLI action adapter

- Status: active
- Fib priority: 6001
- Priority: P0
- Track: adapters
- Parents: VOICE-CARE-G001
- Depends on: VOICE-CARE-G007, VOICE-CARE-G008, VOICE-CARE-G009
- Goal: Invoke allowlisted CLI operations as validated argv in a bounded environment with absolute executable identity, resource limits, timeout, cancellation, and redaction.
- Evidence: CLI registration schema; argv builder; sandbox/resource policy; output bounds; injection and environment-leak tests
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/adapters/cli.py, ipfs_accelerate_py/test/test_action_cli_adapter.py
- Validation: python -m pytest -q ipfs_accelerate_py/test/test_action_cli_adapter.py
- Bundle: voice-care/adapter-cli
- Parallel lane: voice-care-adapters
- Embedding query: sandbox CLI action adapter argv allowlist executable identity timeout resource output redaction injection
- AST query: CLIActionAdapter, CLIActionRegistration, build_argv, CLISandboxPolicy
- Interfaces: native CLI MCP tools, subprocess execution policy
- Submodules: ipfs_accelerate_py
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/adapters/cli.py, ipfs_accelerate_py/test/test_action_cli_adapter.py
- Conflict policy: never use shell expansion, shell=True, caller-controlled cwd, arbitrary environment inheritance, or pack-defined executable paths
- Gap task: Add the minimum safe CLI adapter behind the shared catalog and policy gate.
- Acceptance gate:
  1. Arguments are schema-derived argv elements and cannot inject flags outside descriptor policy.
  2. Executable, cwd, environment, resource, network, and output policies are deployment-owned.
  3. Timeout kills the bounded process tree and reports a truthful terminal state.
  4. Secrets and private values are absent from command displays, logs, errors, and receipts.

## VOICE-CARE-G013 Implement the registered Python callable adapter

- Status: active
- Fib priority: 6002
- Priority: P0
- Track: adapters
- Parents: VOICE-CARE-G001
- Depends on: VOICE-CARE-G007, VOICE-CARE-G008, VOICE-CARE-G009
- Goal: Invoke reviewed Python functions and class methods by catalog registration key with validated dependencies, arguments, results, timeout, cancellation, and explicit side-effect metadata.
- Evidence: callable registry; dependency injection; sync/async support; result validation; arbitrary-import and attribute-traversal rejection tests
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/adapters/python.py, ipfs_accelerate_py/test/test_action_python_adapter.py
- Validation: python -m pytest -q ipfs_accelerate_py/test/test_action_python_adapter.py
- Bundle: voice-care/adapter-python
- Parallel lane: voice-care-adapters
- Embedding query: Python callable class method action adapter registration dependency injection async schema timeout
- AST query: PythonActionAdapter, CallableRegistration, RegisteredCallableResolver
- Interfaces: action catalog, application service methods
- Submodules: ipfs_accelerate_py
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/adapters/python.py, ipfs_accelerate_py/test/test_action_python_adapter.py
- Conflict policy: no caller-supplied imports, eval, exec, arbitrary getattr chains, or implicit global singleton resolution
- Gap task: Provide an in-process adapter for reviewed application methods without weakening catalog controls.
- Acceptance gate:
  1. Only pre-registered callables resolve and their identity participates in catalog CID.
  2. Input and output schemas are checked at the adapter boundary.
  3. Sync and async failures, cancellation, timeout, and unsupported awaitables are normalized.
  4. Hidden side-effect callables are rejected until wrapped with declared policy.

## VOICE-CARE-G014 Implement durable workflow and task adapters

- Status: active
- Fib priority: 6003
- Priority: P0
- Track: adapters
- Parents: VOICE-CARE-G001
- Depends on: VOICE-CARE-G007, VOICE-CARE-G008, VOICE-CARE-G009
- Goal: Submit and observe versioned local or P2P workflows and tasks while preserving durable identity, dependencies, retries, progress, cancellation, and final result receipts.
- Evidence: workflow adapter; task adapter; submit-once behavior; event correlation; fake scheduler and crash-recovery tests
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/adapters/workflow.py, ipfs_accelerate_py/test/test_action_workflow_adapter.py
- Validation: python -m pytest -q ipfs_accelerate_py/test/test_action_workflow_adapter.py ipfs_accelerate_py/test/test_p2p_workflow_scheduler.py
- Bundle: voice-care/adapter-workflow
- Parallel lane: voice-care-adapters
- Embedding query: durable workflow P2P task action adapter submit status progress cancel result idempotency
- AST query: WorkflowActionAdapter, TaskActionAdapter, WorkflowActionHandle
- Interfaces: mcplusplus workflow tools, p2p workflow scheduler, task queue
- Submodules: ipfs_accelerate_py
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/adapters/workflow.py, ipfs_accelerate_py/test/test_action_workflow_adapter.py
- Conflict policy: adapt canonical workflow/task APIs and preserve original idempotency identity across retries
- Gap task: Project durable scheduler state into the shared action lifecycle.
- Acceptance gate:
  1. Submission returns an accepted receipt and never claims workflow completion.
  2. Progress and terminal events correlate to exact workflow, action, session, tenant, and descriptor identities.
  3. Cancellation and retry semantics are explicit and idempotent.
  4. Large/private payloads remain in approved artifact stores, not task rows or logs.

## VOICE-CARE-G015 Implement the agent-supervisor action adapter

- Status: active
- Fib priority: 7000
- Priority: P0
- Track: adapters
- Parents: VOICE-CARE-G001
- Depends on: VOICE-CARE-G007, VOICE-CARE-G008, VOICE-CARE-G009
- Goal: Expose a narrow action adapter over SupervisorControlService for discovery, status, objective refinement, refill, lifecycle control, retry, and validation replay.
- Evidence: explicit operation allowlist; control request/result mapping; repository and objective scope binding; capacity admission; fake-control-service tests; high-risk confirmation gate
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/adapters/agent_supervisor.py, ipfs_accelerate_py/test/test_action_supervisor_adapter.py
- Validation: python -m pytest -q ipfs_accelerate_py/test/test_action_supervisor_adapter.py ipfs_accelerate_py/test/api/test_agent_supervisor_control_plane.py
- Bundle: voice-care/adapter-supervisor
- Parallel lane: voice-care-supervisor-adapter
- Embedding query: agent supervisor action adapter control service objective refine backlog refill start pause resume drain retry validation replay
- AST query: AgentSupervisorActionAdapter, SupervisorActionRegistration, SupervisorControlService
- Interfaces: agent supervisor control contracts, CLI parity, MCP supervisor tools
- Submodules: ipfs_accelerate_py
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/adapters/agent_supervisor.py, ipfs_accelerate_py/test/test_action_supervisor_adapter.py
- Conflict policy: use the transport-neutral control service; voice or GraphRAG input alone cannot authorize repository mutation or implementation start
- Gap task: Add reviewed supervisor operations as ordinary catalog actions with stricter default risk.
- Acceptance gate:
  1. Discovery and status are read-only and capability-probed.
  2. Mutations bind exact repository, objective/task, provider, capacity, and policy identities.
  3. Start, retry, refill, and validation replay require explicit reviewed authority and idempotency.
  4. Python, CLI, and MCP paths return equivalent normalized results.

## VOICE-CARE-G016 Build human-handoff queue and transfer contracts

- Status: active
- Fib priority: 6004
- Priority: P0
- Track: human-care
- Parents: VOICE-CARE-G001
- Depends on: VOICE-CARE-G006, VOICE-CARE-G008, VOICE-CARE-G009, VOICE-CARE-G010
- Goal: Create privacy-safe HandoffRequest, queue, assignment, acceptance, transfer, connection, disposition, expiry, and fallback contracts for real-human care.
- Evidence: handoff schema; queue protocol; priority/skill routing; safe-summary and consent enforcement; lifecycle receipts; fake queue tests
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/conversation_runtime/handoff.py, ipfs_accelerate_py/test/test_human_handoff.py
- Validation: python -m pytest -q ipfs_accelerate_py/test/test_human_handoff.py
- Bundle: voice-care/human-handoff
- Parallel lane: voice-care-human
- Embedding query: human handoff queue assignment transfer connected disposition privacy consent skills priority
- AST query: HandoffRequest, HandoffQueue, HandoffReceipt, HandoffStatus
- Interfaces: telephone transfer, operator console, case store
- Submodules: ipfs_accelerate_py
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/conversation_runtime/handoff.py, ipfs_accelerate_py/test/test_human_handoff.py
- Conflict policy: distinguish requested, queued, assigned, accepted, transferring, connected, failed, expired, and unknown; share only consented minimum context
- Gap task: Replace the current human-escalation metadata flag with a durable, truthful handoff lifecycle.
- Acceptance gate:
  1. A request can be queued without claiming a human accepted or connected.
  2. Safe summary, field scopes, retention, and consent are explicit.
  3. Queue and transfer failures preserve a caller-visible fallback and retry path.
  4. Operator disposition updates the case through the case-store boundary.

## VOICE-CARE-G017 Build provider-neutral telephony ingress egress and transfer adapters

- Status: active
- Fib priority: 7001
- Priority: P0
- Track: telephony
- Parents: VOICE-CARE-G001
- Depends on: VOICE-CARE-G005, VOICE-CARE-G016
- Goal: Adapt webhook, SIP, media-stream, DTMF, barge-in, playback, queue, and transfer operations to process_telephone_turn without making a telephony vendor part of the core.
- Evidence: telephony port contracts; signed webhook validation; replay protection; media limits; fake provider; transfer-confirmation matrix; multi-turn tests
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/conversation_runtime/telephony.py, ipfs_accelerate_py/test/test_customer_care_telephony.py
- Validation: python -m pytest -q ipfs_accelerate_py/test/test_customer_care_telephony.py ipfs_accelerate_py/test/test_voice_router_graphrag.py
- Bundle: voice-care/telephony
- Parallel lane: voice-care-telephony
- Embedding query: telephone webhook SIP media stream DTMF barge in transfer human handoff provider neutral
- AST query: TelephonyPort, TelephonySession, TelephonyTransferAdapter, process_telephone_interaction
- Interfaces: TelephoneTurnState, process_telephone_turn, HandoffQueue
- Submodules: ipfs_accelerate_py
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/conversation_runtime/telephony.py, ipfs_accelerate_py/test/test_customer_care_telephony.py
- Conflict policy: keep vendor SDKs optional behind adapters; tests use signed synthetic requests and no real calls
- Gap task: Turn the current thin telephone receipt boundary into a tested provider-neutral call-control port.
- Acceptance gate:
  1. Ingress authentication, replay, payload, duration, and media limits fail closed.
  2. Call/session correlation uses privacy-safe identities and does not persist audio by default.
  3. Transfer success requires provider-native confirmation; unknown remains unknown.
  4. Provider outage degrades to queued handoff, safe callback instructions, or text-only response without false success.

## VOICE-CARE-G018 Compose the deterministic conversation and action orchestrator

- Status: active
- Fib priority: 8000
- Priority: P0
- Track: orchestration
- Parents: VOICE-CARE-G001
- Depends on: VOICE-CARE-G005, VOICE-CARE-G008, VOICE-CARE-G009, VOICE-CARE-G011, VOICE-CARE-G012, VOICE-CARE-G013, VOICE-CARE-G014, VOICE-CARE-G015, VOICE-CARE-G016
- Goal: Advance immutable session state through retrieval, forms, clarification, confirmation, action execution, result grounding, response rendering, and handoff using injected adapters.
- Evidence: orchestrator; deterministic node transition receipt; adapter registry; interruption/resume; multi-action sequencing; failure and compensation tests
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/conversation_runtime/orchestrator.py, ipfs_accelerate_py/test/test_conversation_orchestrator.py
- Validation: python -m pytest -q ipfs_accelerate_py/test/test_conversation_orchestrator.py
- Bundle: voice-care/orchestrator
- Parallel lane: voice-care-integration
- Embedding query: conversation action orchestrator session retrieval form clarify confirm execute result response handoff resume
- AST query: ConversationOrchestrator, InteractionRequest, InteractionResult, advance_conversation
- Interfaces: voice router, retrieval provider, action executor, handoff queue, case store
- Submodules: ipfs_accelerate_py, ipfs_datasets_py
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/conversation_runtime/orchestrator.py, ipfs_accelerate_py/test/test_conversation_orchestrator.py
- Conflict policy: orchestrator composes established contracts; it cannot bypass policy, catalog, case-store, receipt, or adapter boundaries
- Gap task: Implement the reusable state machine after focused contracts and adapters are independently green.
- Acceptance gate:
  1. Every transition records prior state CID, node, reason, evidence, decision, action/handoff receipts, and next state CID.
  2. Clarification and confirmation resume without repeating completed actions.
  3. Action outputs become evidence only through descriptor-approved projections.
  4. Failures, cancellation, timeout, compensation, and human interruption have deterministic next states.

## VOICE-CARE-G019 Define reusable intake forms and case lifecycle

- Status: active
- Fib priority: 6005
- Priority: P1
- Track: intake
- Parents: VOICE-CARE-G001
- Depends on: VOICE-CARE-G002, VOICE-CARE-G010
- Goal: Render and validate domain-pack forms for intake, disclosures, consent, eligibility hints, contact preference, case creation, follow-up, and disposition across voice and web channels.
- Evidence: form schema and validator; voice prompt projection; web form projection; progressive disclosure; case lifecycle; synthetic accessibility and privacy tests
- Outputs: ipfs_datasets_py/ipfs_datasets_py/conversation/forms.py, ipfs_accelerate_py/ipfs_accelerate_py/conversation_runtime/intake.py, tests/customer_care/test_intake_forms.py
- Validation: python -m pytest -q tests/customer_care/test_intake_forms.py
- Bundle: voice-care/intake
- Parallel lane: voice-care-portal
- Embedding query: reusable client intake dynamic forms voice web consent disclosure case lifecycle follow up disposition
- AST query: IntakeForm, IntakeField, IntakeSession, CaseLifecycle
- Interfaces: domain pack forms, SessionState, CaseStore, wallet/HMIS consent
- Submodules: ipfs_datasets_py, ipfs_accelerate_py
- Predicted files: ipfs_datasets_py/ipfs_datasets_py/conversation/forms.py, ipfs_accelerate_py/ipfs_accelerate_py/conversation_runtime/intake.py, tests/customer_care/test_intake_forms.py
- Conflict policy: collect the minimum required data progressively; application packs define labels but cannot weaken data classification or consent
- Gap task: Create one canonical form contract with channel-specific projections.
- Acceptance gate:
  1. The same form validates equivalent voice and web input.
  2. Sensitive fields include purpose, optionality, retention, and disclosure.
  3. Partial intake is resumable and does not falsely complete a case or action.
  4. Accessibility, localization, correction, and user withdrawal are tested.

## VOICE-CARE-G020 Expose a transport-neutral customer-care gateway

- Status: active
- Fib priority: 9000
- Priority: P1
- Track: api
- Parents: VOICE-CARE-G001
- Depends on: VOICE-CARE-G017, VOICE-CARE-G018, VOICE-CARE-G019
- Goal: Expose session, turn, form, confirmation, action, handoff, status, resume, and cancellation operations through one service with HTTP/WebSocket adapters and stable error semantics.
- Evidence: service protocol; request/result schemas; idempotent endpoints; streaming events; authentication and rate limits; HTTP/WebSocket contract tests
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/conversation_runtime/service.py, wallet_interface/routes/customer_care.py, tests/customer_care/test_gateway.py
- Validation: python -m pytest -q tests/customer_care/test_gateway.py
- Bundle: voice-care/gateway
- Parallel lane: voice-care-api
- Embedding query: customer care gateway API session turn form confirm action handoff status resume cancel stream
- AST query: CustomerCareService, CustomerCareGateway, InteractionEventStream
- Interfaces: orchestrator, telephony adapter, portal API, operator console
- Submodules: ipfs_accelerate_py
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/conversation_runtime/service.py, wallet_interface/routes/customer_care.py, tests/customer_care/test_gateway.py
- Conflict policy: transport adapters delegate to one service and cannot reconstruct policy or execution state
- Gap task: Provide the stable application boundary used by phone, portal, chat, and operators.
- Acceptance gate:
  1. Python and HTTP projections return equivalent normalized results.
  2. Every mutation is authenticated, authorized, rate-limited, and idempotent.
  3. Streaming reconnect resumes from event identity without replaying actions.
  4. Errors reveal safe reason codes rather than secrets, private values, or provider internals.

## VOICE-CARE-G021 Build the reusable portal shell and operator console

- Status: active
- Fib priority: 10000
- Priority: P1
- Track: portal
- Parents: VOICE-CARE-G001
- Depends on: VOICE-CARE-G019, VOICE-CARE-G020
- Goal: Build a configuration-driven customer portal and human-agent console for intake, grounded answers, action confirmation/status, plans, follow-up, handoff queue, redacted context, and disposition.
- Evidence: reusable route/component package; domain-pack presentation adapter; action timeline; operator queue; redaction and grant enforcement; accessibility/mobile/offline tests
- Outputs: wallet_interface/ui/src/customer_care, wallet_interface/ui/src/app/CustomerCareScreen.tsx, wallet_interface/ui/src/app/CustomerCareOperatorScreen.tsx, wallet_interface/ui/tests/customer-care.spec.ts
- Validation: npm --prefix wallet_interface/ui test -- --runInBand
- Bundle: voice-care/portal
- Parallel lane: voice-care-portal
- Embedding query: reusable customer portal operator console intake grounded answer action confirmation workflow handoff disposition
- AST query: CustomerCareScreen, CustomerCareOperatorScreen, ActionTimeline, HandoffQueuePanel
- Interfaces: customer-care gateway, wallet grants, domain-pack presentation
- Submodules: ipfs_accelerate_py
- Predicted files: wallet_interface/ui/src/customer_care, wallet_interface/ui/src/app/CustomerCareScreen.tsx, wallet_interface/ui/src/app/CustomerCareOperatorScreen.tsx
- Conflict policy: UI receives public presentation data and authorized private projections only; it never executes tools directly or stores secrets/private case plaintext in public caches
- Gap task: Factor a reusable shell from the existing 211 portal and add explicit action/handoff lifecycle UI.
- Acceptance gate:
  1. Branding, copy, forms, visible actions, and navigation are driven by selected pack/configuration.
  2. Users review exact action and arguments before required confirmation.
  3. Operators see only assigned and granted context and every disposition is audited.
  4. Mobile, keyboard, screen-reader, large-text, reduced-motion, and offline public-shell paths pass.

## VOICE-CARE-G022 Migrate 211 and Abby assets into a reference domain pack

- Status: active
- Fib priority: 8001
- Priority: P1
- Track: reference-pack
- Parents: VOICE-CARE-G001
- Depends on: VOICE-CARE-G004, VOICE-CARE-G005, VOICE-CARE-G018, VOICE-CARE-G019
- Goal: Produce a pinned `211-ai` domain pack from current service corpus, Abby templates/audio references, slotted conversation DAG, service actions, portal forms, safety routes, and evaluation fixtures.
- Evidence: deterministic migration; source and output CIDs; route/action mapping; compatibility report; no private data; offline 211 smoke tests
- Outputs: data/domain_packs/211-ai/manifest.json, scripts/build_211_customer_care_pack.py, tests/customer_care/test_211_domain_pack.py
- Validation: python -m pytest -q tests/customer_care/test_211_domain_pack.py
- Bundle: voice-care/pack-211
- Parallel lane: voice-care-reference-packs
- Embedding query: 211 Abby domain pack service corpus voice DAG response template live agent portal action migration
- AST query: build_211_customer_care_pack, AbbyDomainPackAdapter, ServicePortalPackAdapter
- Interfaces: Abby voice schema, slotted response DAG, portal package, GraphRAG
- Submodules: ipfs_datasets_py, ipfs_accelerate_py
- Predicted files: data/domain_packs/211-ai/manifest.json, scripts/build_211_customer_care_pack.py, tests/customer_care/test_211_domain_pack.py
- Conflict policy: migration is deterministic and read-only toward remote corpus/Hugging Face sources; preserve current voice and portal behavior as explicit compatibility gates
- Gap task: Make 211 the first pack using generic contracts rather than the hidden default baked into the engine.
- Acceptance gate:
  1. All public service facts retain source URL, content CID, freshness, and extraction provenance.
  2. Existing clarification, grounded-answer, crisis, and live-agent routes map without semantic loss.
  3. Existing router and portal tests remain green behind the compatibility adapter.
  4. Pack artifacts contain no caller/session/case data and require no mutable remote reference.

## VOICE-CARE-G023 Prove data swapping with a non-211 reference pack

- Status: active
- Fib priority: 8002
- Priority: P1
- Track: reference-pack
- Parents: VOICE-CARE-G001
- Depends on: VOICE-CARE-G004, VOICE-CARE-G005, VOICE-CARE-G018, VOICE-CARE-G019
- Goal: Build a small synthetic non-211 help-desk or appointment domain pack and run it through the exact same engine, API, action adapters, and portal shell.
- Evidence: second pack; distinct ontology/forms/actions/branding; identical engine configuration path; isolation tests; swap and rollback receipt
- Outputs: data/domain_packs/example-helpdesk/manifest.json, tests/customer_care/test_domain_pack_swap.py
- Validation: python -m pytest -q tests/customer_care/test_domain_pack_swap.py
- Bundle: voice-care/pack-example
- Parallel lane: voice-care-reference-packs
- Embedding query: non 211 synthetic helpdesk domain pack swap reusable engine portal action isolation
- AST query: ExampleHelpdeskPack, load_domain_pack, switch_domain_pack
- Interfaces: domain compiler, orchestrator, gateway, portal shell
- Submodules: ipfs_datasets_py, ipfs_accelerate_py
- Predicted files: data/domain_packs/example-helpdesk/manifest.json, tests/customer_care/test_domain_pack_swap.py
- Conflict policy: no conditional engine code keyed to either pack ID; fixture contains synthetic public data and fake actions only
- Gap task: Make reuse falsifiable by demonstrating a second purpose with no engine fork.
- Acceptance gate:
  1. Switching the pinned pack changes knowledge, forms, routes, actions, evaluation, and branding only.
  2. Engine imports, adapter registrations, policy core, gateway routes, and portal components are unchanged.
  3. Pack, tenant, session, cache, receipt, and action identities cannot collide.
  4. Rollback to the prior pinned pack is deterministic.

## VOICE-CARE-G024 Add formal safety contract and adversarial evaluation gates

- Status: active
- Fib priority: 9001
- Priority: P0
- Track: assurance
- Parents: VOICE-CARE-G001
- Depends on: VOICE-CARE-G003, VOICE-CARE-G008, VOICE-CARE-G009, VOICE-CARE-G018
- Goal: Prove and test graph reachability, consent-before-side-effect, confirmation-before-high-risk execution, descriptor/argument binding, tenant non-interference, bounded retries, terminal failures, and truthful handoff status.
- Evidence: executable invariants; property tests; formal obligations and proof receipts; adversarial fixtures; MCP contract parity; counterexample minimization
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/assurance.py, ipfs_accelerate_py/test/test_action_assurance.py, tests/customer_care/fixtures/adversarial_actions.jsonl, docs/reports/VOICE_CUSTOMER_CARE_ASSURANCE.md
- Validation: python -m pytest -q ipfs_accelerate_py/test/test_action_assurance.py tests/customer_care
- Bundle: voice-care/assurance
- Parallel lane: voice-care-assurance
- Embedding query: formal proof conversation graph action safety consent confirmation descriptor binding tenant non interference retry handoff
- AST query: ActionSafetyInvariant, ConversationProofObligation, verify_action_trace, verify_conversation_graph
- Interfaces: ipfs_datasets_py logic providers, agent supervisor proof adapters, MCP contract obligations
- Submodules: ipfs_accelerate_py, ipfs_datasets_py
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/assurance.py, ipfs_accelerate_py/test/test_action_assurance.py, docs/reports/VOICE_CUSTOMER_CARE_ASSURANCE.md
- Conflict policy: distinguish tests, bounded model checks, solver candidates, reconstructed proofs, and kernel-verified proofs; absence of a prover is not a proof
- Gap task: Turn the core safety statements into replayable properties and typed proof evidence.
- Acceptance gate:
  1. No reachable trace executes before catalog resolution and policy permit.
  2. High-risk traces contain current consent and confirmation bound to exact arguments.
  3. Cross-tenant state is non-interfering in generated adversarial traces.
  4. Counterexamples become minimized supervisor tasks with exact symbols, paths, and validation commands.

## VOICE-CARE-G025 Add observability operations deployment and rollback

- Status: active
- Fib priority: 10001
- Priority: P1
- Track: operations
- Parents: VOICE-CARE-G001
- Depends on: VOICE-CARE-G009, VOICE-CARE-G016, VOICE-CARE-G020, VOICE-CARE-G021, VOICE-CARE-G024
- Goal: Operate the platform with privacy-safe metrics, traces, health/capability probes, SLOs, pack/action canaries, incident controls, feature flags, and receipt-driven rollback.
- Evidence: operator runbook; metric schema; health and readiness probes; pack/action canary; privacy review; failure drills; rollback receipt
- Outputs: docs/runbooks/VOICE_CUSTOMER_CARE_OPERATIONS.md, docs/specs/VOICE_CUSTOMER_CARE_THREAT_MODEL.md, tests/customer_care/test_operational_readiness.py
- Validation: python -m pytest -q tests/customer_care/test_operational_readiness.py
- Bundle: voice-care/operations
- Parallel lane: voice-care-operations
- Embedding query: customer care observability operations deployment SLO health canary incident feature flag rollback privacy
- AST query: CustomerCareHealth, ActionMetric, PackCanary, rollback_domain_pack
- Interfaces: gateway, action receipts, telephony, supervisor runtime, portal
- Submodules: ipfs_accelerate_py, ipfs_datasets_py
- Predicted files: docs/runbooks/VOICE_CUSTOMER_CARE_OPERATIONS.md, docs/specs/VOICE_CUSTOMER_CARE_THREAT_MODEL.md, tests/customer_care/test_operational_readiness.py
- Conflict policy: metrics and evidence use bounded labels and redacted identities; no raw transcript, audio, case values, secrets, or action payloads
- Gap task: Define production controls before any real telephony or mutating action canary.
- Acceptance gate:
  1. Readiness fails when pack, catalog, policy, adapter, case store, queue, or receipt store identity is incompatible.
  2. Operators can disable a pack, action, adapter, tenant, or channel independently.
  3. Rollback never replays an action and preserves auditable receipts.
  4. Incident drills cover privacy leak, stale tool IDL, duplicate action, failed transfer, provider outage, and malicious pack.

## VOICE-CARE-G026 Prove the complete platform with two offline end-to-end journeys

- Status: active
- Fib priority: 13000
- Priority: P0
- Track: integration
- Parents: VOICE-CARE-G001
- Depends on: VOICE-CARE-G011, VOICE-CARE-G012, VOICE-CARE-G013, VOICE-CARE-G014, VOICE-CARE-G015, VOICE-CARE-G017, VOICE-CARE-G018, VOICE-CARE-G020, VOICE-CARE-G021, VOICE-CARE-G022, VOICE-CARE-G023, VOICE-CARE-G024, VOICE-CARE-G025
- Goal: Run identical engine code through 211 and non-211 voice/web journeys covering grounded answers, intake, clarification, confirmation, MCP/CLI/callable/workflow/supervisor fakes, human handoff, failure, resume, and rollback.
- Evidence: deterministic end-to-end suite; cross-channel equivalence; domain-swap proof; action and handoff receipt chains; compatibility and release report
- Outputs: tests/customer_care/test_end_to_end.py, docs/reports/VOICE_CUSTOMER_CARE_END_TO_END.md
- Validation: python -m pytest -q tests/customer_care/test_end_to_end.py tests/voice wallet_interface/tests/test_voice_router_adapter.py
- Bundle: voice-care/end-to-end
- Parallel lane: voice-care-integration
- Embedding query: end to end voice web customer care 211 non 211 intake action MCP CLI callable workflow supervisor human handoff
- AST query: test_211_end_to_end, test_helpdesk_end_to_end, verify_receipt_chain
- Interfaces: all customer-care platform boundaries
- Submodules: ipfs_accelerate_py, ipfs_datasets_py, ipfs_kit_py
- Predicted files: tests/customer_care/test_end_to_end.py, docs/reports/VOICE_CUSTOMER_CARE_END_TO_END.md
- Conflict policy: use synthetic input and fake/local adapters only; live telephony, remote mutation, paid providers, and production supervisor start require separate human approval
- Gap task: Create the final evidence gate that proves reuse and truthful action behavior rather than only component coverage.
- Acceptance gate:
  1. Both packs run without engine branches keyed to application identity.
  2. Voice and web forms produce equivalent validated session facts and decisions.
  3. Every action and handoff state is content-addressed, replay-safe, and truthfully presented.
  4. Existing Abby voice and 211 portal compatibility suites remain green.

## VOICE-CARE-G027 Establish bounded autonomous refill and contract-mismatch repair

- Status: active
- Fib priority: 11000
- Priority: P1
- Track: supervisor
- Parents: VOICE-CARE-G001
- Depends on: VOICE-CARE-G002, VOICE-CARE-G006, VOICE-CARE-G024
- Goal: Configure objective scanning, AST/GraphRAG evidence indexing, formal-plan validation, contract-mismatch task generation, bundle-local lanes, Grok-first implementation with pre-dispatch Codex fallback, retry budgets, and drained-backlog refill for this program.
- Evidence: generated todo and bundle indexes; plan evaluation; refill configuration; contract mismatch and vulnerability ingestion; lane conflict map; dry-run manifest
- Outputs: scripts/ops/voice_customer_care_supervisor.py, tests/customer_care/test_supervisor_program.py, docs/planning/VOICE_CUSTOMER_CARE_AGENT_SUPERVISOR_RUNBOOK.md
- Validation: PYTHONPATH=ipfs_accelerate_py python -m ipfs_accelerate_py.agent_supervisor.objectives.bundle_supervisor --repo-root . --bundle-index-path data/voice_customer_care/agent_supervisor/objective_bundles/index.json --state-root data/voice_customer_care/agent_supervisor/lane_state --worktree-root /tmp/voice-care-agent-worktrees --manifest-path data/voice_customer_care/agent_supervisor/lane-manifest.json --task-prefix VOICE-CARE-AUTO- --max-lanes 6 --no-implement
- Bundle: voice-care/supervisor-control
- Parallel lane: voice-care-supervisor-control
- Embedding query: agent supervisor objective scan AST GraphRAG formal plan contract mismatch vulnerability bundle lane refill
- AST query: ObjectiveGoal, ObjectiveFinding, ContractMismatchTask, BundleSupervisor, SelfImprovementEpoch
- Interfaces: objective daemon, analysis/proof providers, task sources, bundle supervisor, self-improvement refill
- Submodules: ipfs_accelerate_py, ipfs_datasets_py
- Predicted files: scripts/ops/voice_customer_care_supervisor.py, tests/customer_care/test_supervisor_program.py, docs/planning/VOICE_CUSTOMER_CARE_AGENT_SUPERVISOR_RUNBOOK.md
- Conflict policy: objective heap, todo board, generated graph/index, and runbook are protected control-plane inputs; generated implementation tasks are bounded by exact predicted paths, symbols, interfaces, and validations; deduplicate by canonical task identity and serialize overlapping contracts
- Gap task: Make this heap continuously projectable into small Grok-first implementation packets with Codex fallback when Grok is not dispatch-ready, without relying on one large prompt.
- Acceptance gate:
  1. Initial scan creates content-addressed tasks and bundle shards for missing evidence without marking new goals complete by token coincidence.
  2. Dry-run lane planning exposes dependencies, resource classes, conflicts, and worktree/submodule ownership.
  3. Refill creates bounded novel tasks only after completion evidence or analyzer findings change.
  4. Static, contract, proof, security, and validation findings can append tasks with exact evidence and no unbounded LLM context.
  5. Generated tasks use the soft `grok, codex-review` role with provider `auto`, select Grok when dispatch-ready, and select Codex only before dispatch when Grok is unavailable.
  6. A started Grok attempt never falls through to Codex in the same mutable worktree; quota, runtime, policy, and validation failures remain fail-closed.
