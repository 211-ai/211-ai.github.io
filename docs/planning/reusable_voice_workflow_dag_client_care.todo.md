# Reusable Voice Workflow DAG Client Intake and Customer Care Task Board

This is the executable projection of
`reusable_voice_workflow_dag_client_care.objectives.md`. The
`ipfs_accelerate_py.agent_supervisor` owns status transitions, dependency
admission, bounded refinement, and objective refill for this board.

Program invariants:

- Board namespace is `voice-care-workflow-dag-v1`; task identities are stable.
- Profile content can name only logical capabilities. It cannot contain a raw
  command, executable path, Python import target, arbitrary URL, credential, or
  unapproved MCP server identity.
- Retrieval, transcripts, templates, and models may propose an allowlisted
  logical action but cannot increase execution authority.
- Mutations fail closed unless the active signed profile, policy, tenant,
  consent or confirmation, authentication, resource limits, and a fenced lease
  all authorize the exact canonical proposal.
- Durable outbox, idempotency, fencing, reconciliation, and an explicit
  `outcome_unknown` state replace any false exactly-once claim.
- Public packs, signed control packs, and encrypted private session state have
  distinct stores, indexes, cache namespaces, and retention rules.
- Symbolic checks run before a bounded LLM repair packet is admitted.
- Optional zero-knowledge artifacts attest only the explicitly modeled,
  deterministic public statement and never prove arbitrary external behavior.
- Completion requires current-tree validation evidence; documentation-only
  assertions do not satisfy executable contracts.

## VOICE-CARE-001 Bootstrap the supervisor control plane and protected plan namespace

- Status: todo
- Completion: manual
- Priority: P0
- Track: operations
- Depends on:
- Goal id: VOICE-CARE-G130
- Outputs: scripts/voice_workflows/supervisor_control.py, data/voice_workflows/agent_supervisor/runtime-policy.json, data/voice_workflows/agent_supervisor/README.md, tests/voice_workflows/test_supervisor_control.py
- Validation: python scripts/voice_workflows/supervisor_control.py validate-config && python -m pytest -q tests/voice_workflows/test_supervisor_control.py
- Board namespace: voice-care-workflow-dag-v1
- Bundle: voice-care/operations
- Parallel lane: wave-00-control
- Resource class: cpu-small
- Predicted files: scripts/voice_workflows/supervisor_control.py, data/voice_workflows/agent_supervisor/runtime-policy.json, data/voice_workflows/agent_supervisor/README.md, tests/voice_workflows/test_supervisor_control.py
- Conflict policy: This task exclusively owns supervisor launch policy and protected-path configuration.
- Symbolic first: true
- LLM context budget bytes: 12288
- Acceptance: A parent-repository control command validates the objective heap and this board, creates the absent `agent/voice-care-workflow-dag` merge target only from the reviewed pinned base, translates the bespoke launch profile into supported supervisor arguments, starts four deterministic task shards with exactly one refill owner, protects plan and board files from implementation agents, constrains worktree and merge targets, disables publication and credential use by default, and passes independent idempotent preflight, start, status, and stop tests; every configuration or base mismatch fails before workers start.

## VOICE-CARE-002 Inventory current voice, GraphRAG, action, portal, and supervisor contracts

- Status: todo
- Completion: manual
- Priority: P0
- Track: architecture
- Depends on: VOICE-CARE-001
- Goal id: VOICE-CARE-G010
- Outputs: scripts/voice_workflows/audit_baseline.py, data/voice_workflows/baseline/component-inventory.json, data/voice_workflows/baseline/contract-drift.json, docs/voice_workflows/CURRENT_SYSTEM_BOUNDARIES.md
- Validation: python scripts/voice_workflows/audit_baseline.py --check
- Board namespace: voice-care-workflow-dag-v1
- Bundle: voice-care/doctrine
- Parallel lane: wave-01-inventory
- Resource class: io-medium
- Predicted files: scripts/voice_workflows/audit_baseline.py, data/voice_workflows/baseline/component-inventory.json, data/voice_workflows/baseline/contract-drift.json, docs/voice_workflows/CURRENT_SYSTEM_BOUNDARIES.md
- Conflict policy: Owns baseline reports only and must not modify implementation modules.
- Symbolic first: true
- LLM context budget bytes: 16384
- Acceptance: The deterministic inventory binds repository revisions and AST symbols for the current response DAG, GraphRAG provider, voice router, DAG sink, UI action system, service action layer, MCP surfaces, and supervisor entry points; records missing, ambiguous, or incompatible contracts explicitly; and distinguishes shipped behavior from proposed behavior.

## VOICE-CARE-003 Freeze the trust, privacy, authority, and proof doctrine

- Status: todo
- Completion: manual
- Priority: P0
- Track: trust
- Depends on: VOICE-CARE-002
- Goal id: VOICE-CARE-G010
- Outputs: docs/voice_workflows/TRUST_PRIVACY_AND_PROOF_MODEL.md, docs/voice_workflows/schemas/assurance-verdict-v1.schema.json, tests/voice_workflows/test_assurance_verdict_policy.py
- Validation: python -m pytest -q tests/voice_workflows/test_assurance_verdict_policy.py
- Board namespace: voice-care-workflow-dag-v1
- Bundle: voice-care/doctrine
- Parallel lane: wave-01-trust
- Resource class: cpu-small
- Predicted files: docs/voice_workflows/TRUST_PRIVACY_AND_PROOF_MODEL.md, docs/voice_workflows/schemas/assurance-verdict-v1.schema.json, tests/voice_workflows/test_assurance_verdict_policy.py
- Conflict policy: Owns normative trust and verdict vocabulary; downstream tasks consume but do not redefine it.
- Symbolic first: true
- LLM context budget bytes: 16384
- Acceptance: The doctrine defines public, signed-control, and private planes; authority monotonicity; tenant isolation; consent and authentication obligations; conservative verdicts including unknown and unsupported; the trusted computing base; limits of GraphRAG, static analysis, tests, receipts, and zero-knowledge attestations; and fail-closed treatment of stale, partial, or errored evidence.

## VOICE-CARE-004 Publish package boundaries and architecture conformance checks

- Status: todo
- Completion: manual
- Priority: P0
- Track: architecture
- Depends on: VOICE-CARE-002, VOICE-CARE-003
- Goal id: VOICE-CARE-G010
- Outputs: docs/voice_workflows/REFERENCE_ARCHITECTURE.md, scripts/voice_workflows/check_architecture_boundaries.py, tests/voice_workflows/test_architecture_boundaries.py
- Validation: python -m pytest -q tests/voice_workflows/test_architecture_boundaries.py
- Board namespace: voice-care-workflow-dag-v1
- Bundle: voice-care/doctrine
- Parallel lane: wave-01-boundaries
- Resource class: cpu-small
- Predicted files: docs/voice_workflows/REFERENCE_ARCHITECTURE.md, scripts/voice_workflows/check_architecture_boundaries.py, tests/voice_workflows/test_architecture_boundaries.py
- Conflict policy: Owns dependency-boundary rules and imports no domain profile data.
- Symbolic first: true
- LLM context budget bytes: 12288
- Acceptance: Checks enforce domain-neutral data contracts in `ipfs_datasets_py`, execution and adapters in `ipfs_accelerate_py`, optional storage transport in `ipfs_kit_py`, and product profiles and UI in the parent repository; the response-content DAG and executable workflow DAG remain separate; and generic packages do not depend on 211, Abby, wallet, or service-taxonomy symbols.

## VOICE-CARE-005 Define canonical domain-profile, workflow, action, policy, and session records

- Status: todo
- Completion: manual
- Priority: P0
- Track: contracts
- Depends on: VOICE-CARE-004
- Goal id: VOICE-CARE-G010
- Outputs: ipfs_datasets_py/ipfs_datasets_py/voice_workflows/records.py, ipfs_datasets_py/ipfs_datasets_py/voice_workflows/schemas.py, ipfs_datasets_py/tests/unit/voice_workflows/test_records.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/voice_workflows/test_records.py
- Board namespace: voice-care-workflow-dag-v1
- Bundle: voice-care/contracts
- Parallel lane: wave-02-records
- Resource class: cpu-medium
- Predicted files: ipfs_datasets_py/ipfs_datasets_py/voice_workflows/records.py, ipfs_datasets_py/ipfs_datasets_py/voice_workflows/schemas.py, ipfs_datasets_py/tests/unit/voice_workflows/test_records.py
- Conflict policy: Owns versioned wire records; consumers extend through declared schema versions rather than editing these files concurrently.
- Symbolic first: true
- LLM context budget bytes: 24576
- Acceptance: Immutable validated records cover manifests, logical actions, workflows, typed predicates, action proposals, grants, workflow instances, handoffs, and normalized outcomes; closed node and edge vocabularies reject arbitrary evaluation; private fields are classified; unknown fields and unsupported schema versions fail closed; and no record field permits executable locators.

## VOICE-CARE-006 Implement canonical encoding, multiformats, multihash, and CID identity

- Status: todo
- Completion: manual
- Priority: P0
- Track: contracts
- Depends on: VOICE-CARE-005
- Goal id: VOICE-CARE-G020
- Outputs: ipfs_datasets_py/ipfs_datasets_py/voice_workflows/content_addressing.py, ipfs_datasets_py/tests/unit/voice_workflows/test_content_addressing.py, docs/voice_workflows/schemas/canonical-identity-v1.md
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/voice_workflows/test_content_addressing.py
- Board namespace: voice-care-workflow-dag-v1
- Bundle: voice-care/contracts
- Parallel lane: wave-02-cids
- Resource class: cpu-medium
- Predicted files: ipfs_datasets_py/ipfs_datasets_py/voice_workflows/content_addressing.py, ipfs_datasets_py/tests/unit/voice_workflows/test_content_addressing.py, docs/voice_workflows/schemas/canonical-identity-v1.md
- Conflict policy: Owns canonical byte and CID derivation only; it must reuse audited multiformats and multihash primitives.
- Symbolic first: true
- LLM context budget bytes: 16384
- Acceptance: Canonical identities are stable across process, ordering, locale, and supported runtime versions; an artifact-type registry pins codec, multibase, multihash, and schema version; golden vectors distinguish the existing voice GraphRAG `CIDv1/raw/sha2-256` profile from any new `dag-json/sha2-256` profile; compatibility links and migrations preserve both identities instead of silently reinterpreting bytes; parsing rejects noncanonical aliases and unsupported profiles; every signature binds canonical bytes and schema version; and private plaintext is never published merely to derive a public CID.

## VOICE-CARE-007 Compile finite workflow DAGs and typed predicates deterministically

- Status: todo
- Completion: manual
- Priority: P0
- Track: compiler
- Depends on: VOICE-CARE-005
- Goal id: VOICE-CARE-G010
- Outputs: ipfs_datasets_py/ipfs_datasets_py/voice_workflows/compiler.py, ipfs_datasets_py/ipfs_datasets_py/voice_workflows/predicates.py, ipfs_datasets_py/tests/unit/voice_workflows/test_compiler.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/voice_workflows/test_compiler.py
- Board namespace: voice-care-workflow-dag-v1
- Bundle: voice-care/contracts
- Parallel lane: wave-02-compiler
- Resource class: cpu-medium
- Predicted files: ipfs_datasets_py/ipfs_datasets_py/voice_workflows/compiler.py, ipfs_datasets_py/ipfs_datasets_py/voice_workflows/predicates.py, ipfs_datasets_py/tests/unit/voice_workflows/test_compiler.py
- Conflict policy: Owns compiler and predicate semantics; runtime tasks consume the compiled form.
- Symbolic first: true
- LLM context budget bytes: 24576
- Acceptance: Compilation rejects duplicate or missing nodes, illegal edges, unreachable required nodes, unbounded cycles, undeclared state fields, type errors, arbitrary expressions, missing timeout or unknown branches, invalid compensation links, and nonterminating graphs; two equivalent inputs yield the same compiled graph CID and ordered diagnostics.

## VOICE-CARE-008 Build signed profile loading, migration, activation, rollback, and revocation

- Status: todo
- Completion: manual
- Priority: P0
- Track: profiles
- Depends on: VOICE-CARE-006, VOICE-CARE-007
- Goal id: VOICE-CARE-G020
- Outputs: ipfs_datasets_py/ipfs_datasets_py/voice_workflows/profile.py, ipfs_datasets_py/ipfs_datasets_py/voice_workflows/release.py, ipfs_datasets_py/tests/unit/voice_workflows/test_profile_lifecycle.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/voice_workflows/test_profile_lifecycle.py
- Board namespace: voice-care-workflow-dag-v1
- Bundle: voice-care/contracts
- Parallel lane: wave-03-profile-lifecycle
- Resource class: io-medium
- Predicted files: ipfs_datasets_py/ipfs_datasets_py/voice_workflows/profile.py, ipfs_datasets_py/ipfs_datasets_py/voice_workflows/release.py, ipfs_datasets_py/tests/unit/voice_workflows/test_profile_lifecycle.py
- Conflict policy: Owns profile lifecycle and activation receipt contracts; deployment bindings remain outside profile data.
- Symbolic first: true
- LLM context budget bytes: 24576
- Acceptance: Activation verifies every CID, schema, signature, signer scope, migration, required capability, and index before atomically changing a tenant pointer; emits a receipt; retains bounded rollback; prevents downgrade and revoked-pack activation; and never executes an adapter during a capability probe.

## VOICE-CARE-009 Enforce tenant, profile, policy, and privacy separation in indexes and caches

- Status: todo
- Completion: manual
- Priority: P0
- Track: profiles
- Depends on: VOICE-CARE-006, VOICE-CARE-008
- Goal id: VOICE-CARE-G020
- Outputs: ipfs_datasets_py/ipfs_datasets_py/voice_workflows/namespaces.py, ipfs_datasets_py/tests/unit/voice_workflows/test_namespace_isolation.py, docs/voice_workflows/CACHE_AND_INDEX_ISOLATION.md
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/voice_workflows/test_namespace_isolation.py
- Board namespace: voice-care-workflow-dag-v1
- Bundle: voice-care/contracts
- Parallel lane: wave-03-isolation
- Resource class: cpu-medium
- Predicted files: ipfs_datasets_py/ipfs_datasets_py/voice_workflows/namespaces.py, ipfs_datasets_py/tests/unit/voice_workflows/test_namespace_isolation.py, docs/voice_workflows/CACHE_AND_INDEX_ISOLATION.md
- Conflict policy: Owns namespace-key construction and public/private index rules.
- Symbolic first: true
- LLM context budget bytes: 16384
- Acceptance: Every retrieval and pure decision cache key binds tenant namespace, active profile root CID, policy CID, schema versions, locale, and capability snapshot; mutation outcomes are excluded from generic result caches; private embeddings are encrypted, separately indexed, deletable, and never admitted to public IPFS; cross-tenant and stale-profile cache probes produce deterministic misses.

## VOICE-CARE-010 Extend GraphRAG with logical actions, workflows, slots, and citations

- Status: todo
- Completion: manual
- Priority: P0
- Track: graphrag
- Depends on: VOICE-CARE-005, VOICE-CARE-007
- Goal id: VOICE-CARE-G030
- Outputs: ipfs_datasets_py/ipfs_datasets_py/voice_workflows/graphrag.py, ipfs_datasets_py/tests/unit/voice_workflows/test_action_graph.py, docs/voice_workflows/schemas/action-graph-v1.md
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/voice_workflows/test_action_graph.py
- Board namespace: voice-care-workflow-dag-v1
- Bundle: voice-care/graphrag
- Parallel lane: wave-03-action-graph
- Resource class: cpu-medium
- Predicted files: ipfs_datasets_py/ipfs_datasets_py/voice_workflows/graphrag.py, ipfs_datasets_py/tests/unit/voice_workflows/test_action_graph.py, docs/voice_workflows/schemas/action-graph-v1.md
- Conflict policy: Owns the domain-neutral action graph schema and does not alter existing Abby graph records in place.
- Symbolic first: true
- LLM context budget bytes: 24576
- Acceptance: The graph indexes public intents, evidence, templates, logical actions, workflows, declared slots, consent requirements, capability requirements, escalation routes, and citations using closed node and edge types; excludes deployment bindings and private caller data; and preserves compatibility through an explicit adapter rather than schema reinterpretation.

## VOICE-CARE-011 Implement deterministic hybrid retrieval and bounded action ranking

- Status: todo
- Completion: manual
- Priority: P0
- Track: graphrag
- Depends on: VOICE-CARE-009, VOICE-CARE-010
- Goal id: VOICE-CARE-G030
- Outputs: ipfs_datasets_py/ipfs_datasets_py/voice_workflows/retrieval.py, ipfs_datasets_py/tests/unit/voice_workflows/test_action_retrieval.py, data/voice_workflows/evaluation/retrieval-golden.json
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/voice_workflows/test_action_retrieval.py
- Board namespace: voice-care-workflow-dag-v1
- Bundle: voice-care/graphrag
- Parallel lane: wave-04-retrieval
- Resource class: cpu-large
- Predicted files: ipfs_datasets_py/ipfs_datasets_py/voice_workflows/retrieval.py, ipfs_datasets_py/tests/unit/voice_workflows/test_action_retrieval.py, data/voice_workflows/evaluation/retrieval-golden.json
- Conflict policy: Owns retrieval scoring and golden vectors; it cannot write authority or execution modules.
- Symbolic first: true
- LLM context budget bytes: 24576
- Acceptance: Lexical, vector, graph, locale, slot, and policy-visibility signals combine deterministically with stable tie-breaking and explicit score provenance; low confidence yields clarify, handoff, or no-action rather than authority; filtered candidates remain explainable; and identical snapshots and queries yield identical ordered results.

## VOICE-CARE-012 Bind grounded responses and action proposals to current evidence

- Status: todo
- Completion: manual
- Priority: P0
- Track: graphrag
- Depends on: VOICE-CARE-011
- Goal id: VOICE-CARE-G030
- Outputs: ipfs_datasets_py/ipfs_datasets_py/voice_workflows/grounding.py, ipfs_datasets_py/tests/unit/voice_workflows/test_grounding.py, docs/voice_workflows/GROUNDING_CONTRACT.md
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/voice_workflows/test_grounding.py
- Board namespace: voice-care-workflow-dag-v1
- Bundle: voice-care/graphrag
- Parallel lane: wave-04-grounding
- Resource class: cpu-medium
- Predicted files: ipfs_datasets_py/ipfs_datasets_py/voice_workflows/grounding.py, ipfs_datasets_py/tests/unit/voice_workflows/test_grounding.py, docs/voice_workflows/GROUNDING_CONTRACT.md
- Conflict policy: Owns evidence-binding rules and spoken-claim validation.
- Symbolic first: true
- LLM context budget bytes: 16384
- Acceptance: Every factual response claim and proposed logical action binds current profile, graph, evidence, and template CIDs plus score and policy-visible facts; stale or absent evidence cannot yield a grounded verdict; citations are display-safe; and provenance survives voice, portal, and handoff serialization.

## VOICE-CARE-013 Reject prompt injection, schema smuggling, and authority escalation in retrieved data

- Status: todo
- Completion: manual
- Priority: P0
- Track: graphrag-security
- Depends on: VOICE-CARE-010, VOICE-CARE-011, VOICE-CARE-012
- Goal id: VOICE-CARE-G030
- Outputs: ipfs_datasets_py/ipfs_datasets_py/voice_workflows/guards.py, ipfs_datasets_py/tests/security/voice_workflows/test_retrieval_injection.py, data/voice_workflows/evaluation/hostile-content-corpus.json
- Validation: python -m pytest -q ipfs_datasets_py/tests/security/voice_workflows/test_retrieval_injection.py
- Board namespace: voice-care-workflow-dag-v1
- Bundle: voice-care/graphrag
- Parallel lane: wave-04-content-guards
- Resource class: security-medium
- Predicted files: ipfs_datasets_py/ipfs_datasets_py/voice_workflows/guards.py, ipfs_datasets_py/tests/security/voice_workflows/test_retrieval_injection.py, data/voice_workflows/evaluation/hostile-content-corpus.json
- Conflict policy: Owns hostile-content fixtures and data-plane validation, not runtime authorization.
- Symbolic first: true
- LLM context budget bytes: 16384
- Acceptance: Adversarial documents, transcripts, Unicode aliases, hidden fields, oversized records, forged CIDs, nested locator fields, and instruction-shaped content cannot create capabilities, change policy, select an adapter, expose secrets, or bypass confirmation; all rejections have bounded machine-readable reasons.

## VOICE-CARE-014 Implement the durable workflow and action state machines

- Status: todo
- Completion: manual
- Priority: P0
- Track: runtime
- Depends on: VOICE-CARE-005, VOICE-CARE-007
- Goal id: VOICE-CARE-G050
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/contracts.py, ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/engine.py, ipfs_accelerate_py/test/api/voice_workflows/test_voice_workflow_engine.py
- Validation: python -m pytest -q ipfs_accelerate_py/test/api/voice_workflows/test_voice_workflow_engine.py
- Board namespace: voice-care-workflow-dag-v1
- Bundle: voice-care/runtime
- Parallel lane: wave-03-state-machine
- Resource class: cpu-large
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/contracts.py, ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/engine.py, ipfs_accelerate_py/test/api/voice_workflows/test_voice_workflow_engine.py
- Conflict policy: Owns runtime transition semantics; adapter and storage implementations use its public interfaces.
- Symbolic first: true
- LLM context budget bytes: 32768
- Acceptance: The engine separates immutable dispatch-attempt observations from workflow action state; each attempt closes as confirmed success, confirmed failure, or unresolved unknown; `outcome_unknown` is a durable non-conclusive reconciliation hold that can be resolved only by appending a provider-bound reconciliation receipt; conclusive workflow outcomes are monotonic and are never rewritten; invalid or duplicate transitions are rejected; and waits and subworkflows are bounded.

## VOICE-CARE-015 Build the fail-closed admission, consent, confirmation, authentication, and policy gateway

- Status: todo
- Completion: manual
- Priority: P0
- Track: runtime-security
- Depends on: VOICE-CARE-003, VOICE-CARE-014
- Goal id: VOICE-CARE-G040
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/policy.py, ipfs_accelerate_py/test/api/voice_workflows/test_voice_workflow_policy.py, docs/voice_workflows/POLICY_GATEWAY.md
- Validation: python -m pytest -q ipfs_accelerate_py/test/api/voice_workflows/test_voice_workflow_policy.py
- Board namespace: voice-care-workflow-dag-v1
- Bundle: voice-care/runtime
- Parallel lane: wave-04-policy
- Resource class: security-large
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/policy.py, ipfs_accelerate_py/test/api/voice_workflows/test_voice_workflow_policy.py, docs/voice_workflows/POLICY_GATEWAY.md
- Conflict policy: Owns the single runtime admission boundary; adapters may narrow but never override its denial.
- Symbolic first: true
- LLM context budget bytes: 24576
- Acceptance: Admission binds canonical proposal, active signed profile and policy, tenant, session, risk, schemas, slots, capability, consent, confirmation, authentication freshness, delegation, rate and cost limits, and revocation state; mutations are denied when any fact is missing, stale, unknown, or mismatched; and authorization is rechecked immediately before execution.

## VOICE-CARE-016 Add durable events, outbox, leases, fencing, idempotency, and replay

- Status: todo
- Completion: manual
- Priority: P0
- Track: runtime
- Depends on: VOICE-CARE-014, VOICE-CARE-015
- Goal id: VOICE-CARE-G050
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/state.py, ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/outbox.py, ipfs_accelerate_py/test/api/voice_workflows/test_voice_workflow_durability.py
- Validation: python -m pytest -q ipfs_accelerate_py/test/api/voice_workflows/test_voice_workflow_durability.py
- Board namespace: voice-care-workflow-dag-v1
- Bundle: voice-care/runtime
- Parallel lane: wave-05-durability
- Resource class: io-large
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/state.py, ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/outbox.py, ipfs_accelerate_py/test/api/voice_workflows/test_voice_workflow_durability.py
- Conflict policy: Owns persistence protocols and reference local store; optional IPFS Kit storage implements the same interface separately.
- Symbolic first: true
- LLM context budget bytes: 32768
- Acceptance: State and outbox writes commit atomically; workers use expiring fenced leases; repeated identical idempotency keys and payloads return prior outcomes while a changed payload conflicts; crashes before and after dispatch are recoverable; tenant and profile identities survive replay; and no implementation claims exactly-once external effects.

## VOICE-CARE-017 Implement retries, cancellation, compensation, reconciliation, and outcome unknown

- Status: todo
- Completion: manual
- Priority: P0
- Track: runtime
- Depends on: VOICE-CARE-016
- Goal id: VOICE-CARE-G050
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/recovery.py, ipfs_accelerate_py/test/api/voice_workflows/test_voice_workflow_recovery.py, docs/voice_workflows/FAILURE_SEMANTICS.md
- Validation: python -m pytest -q ipfs_accelerate_py/test/api/voice_workflows/test_voice_workflow_recovery.py
- Board namespace: voice-care-workflow-dag-v1
- Bundle: voice-care/runtime
- Parallel lane: wave-06-recovery
- Resource class: cpu-large
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/recovery.py, ipfs_accelerate_py/test/api/voice_workflows/test_voice_workflow_recovery.py, docs/voice_workflows/FAILURE_SEMANTICS.md
- Conflict policy: Owns post-dispatch failure semantics and provider reconciliation hooks.
- Symbolic first: true
- LLM context budget bytes: 24576
- Acceptance: Retry policy is capability and error-class aware; cancellation cannot erase a possible external effect; compensation is an explicit separately authorized action; reconciliation appends evidence that may move an unresolved `outcome_unknown` hold to one conclusive workflow outcome without rewriting the original attempt; a cancellation request is separately receipted and cannot disguise an unknown external effect; and the engine never fabricates success, failure, or rollback.

## VOICE-CARE-018 Enforce revocation, quotas, circuit breakers, and the runtime kill switch

- Status: todo
- Completion: manual
- Priority: P0
- Track: runtime-security
- Depends on: VOICE-CARE-015, VOICE-CARE-016, VOICE-CARE-017
- Goal id: VOICE-CARE-G040
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/controls.py, ipfs_accelerate_py/test/api/voice_workflows/test_voice_workflow_controls.py, docs/voice_workflows/EMERGENCY_CONTROLS.md
- Validation: python -m pytest -q ipfs_accelerate_py/test/api/voice_workflows/test_voice_workflow_controls.py
- Board namespace: voice-care-workflow-dag-v1
- Bundle: voice-care/runtime
- Parallel lane: wave-06-runtime-controls
- Resource class: security-medium
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/controls.py, ipfs_accelerate_py/test/api/voice_workflows/test_voice_workflow_controls.py, docs/voice_workflows/EMERGENCY_CONTROLS.md
- Conflict policy: Owns global and tenant-scoped execution controls, not adapter-specific health probes.
- Symbolic first: true
- LLM context budget bytes: 16384
- Acceptance: Policy, signer, binding, tenant, capability, and global revocations invalidate new admission and leased work before dispatch; per-tenant time, cost, concurrency, and call quotas are atomic; circuit breakers degrade to safe response or human handoff; and an audited kill switch stops mutations without losing queued evidence.

## VOICE-CARE-019 Define the adapter SPI, trusted deployment registry, and normalized outcomes

- Status: todo
- Completion: manual
- Priority: P0
- Track: adapters
- Depends on: VOICE-CARE-014, VOICE-CARE-015
- Goal id: VOICE-CARE-G060
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/adapters/base.py, ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/adapters/registry.py, ipfs_accelerate_py/test/api/voice_workflows/test_voice_adapter_registry.py
- Validation: python -m pytest -q ipfs_accelerate_py/test/api/voice_workflows/test_voice_adapter_registry.py
- Board namespace: voice-care-workflow-dag-v1
- Bundle: voice-care/adapters
- Parallel lane: wave-05-adapter-spi
- Resource class: cpu-medium
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/adapters/base.py, ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/adapters/registry.py, ipfs_accelerate_py/test/api/voice_workflows/test_voice_adapter_registry.py
- Conflict policy: Owns adapter protocols and registry; concrete adapters receive separate modules.
- Symbolic first: true
- LLM context budget bytes: 24576
- Acceptance: A logical capability resolves only through operator-installed, signed deployment bindings to a registered adapter factory; registration is code or trusted deployment configuration rather than profile data; input and output schemas, risk, health, timeout, idempotency, compensation, and reconciliation metadata are explicit; and all adapters return the same bounded outcome vocabulary.

## VOICE-CARE-020 Build adapter conformance, health, fault-injection, and contract tests

- Status: todo
- Completion: manual
- Priority: P0
- Track: adapters
- Depends on: VOICE-CARE-016, VOICE-CARE-019
- Goal id: VOICE-CARE-G060
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/adapters/conformance.py, ipfs_accelerate_py/test/api/voice_workflows/adapter_contract/, docs/voice_workflows/ADAPTER_CONFORMANCE.md
- Validation: python -m pytest -q ipfs_accelerate_py/test/api/voice_workflows/adapter_contract
- Board namespace: voice-care-workflow-dag-v1
- Bundle: voice-care/adapters
- Parallel lane: wave-06-adapter-conformance
- Resource class: cpu-large
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/adapters/conformance.py, ipfs_accelerate_py/test/api/voice_workflows/adapter_contract/, docs/voice_workflows/ADAPTER_CONFORMANCE.md
- Conflict policy: Owns the reusable adapter harness and fixtures; concrete adapters add cases without weakening common assertions.
- Symbolic first: true
- LLM context budget bytes: 24576
- Acceptance: The harness verifies schema rejection, tenant propagation, policy recheck, timeouts, cancellation, lease fencing, replay, payload conflicts, secret redaction, normalized errors, health probes without mutation, reconciliation, compensation declarations, and crash boundaries; an adapter cannot register unless its capability class passes every mandatory case.

## VOICE-CARE-021 Implement the MCP++ capability adapter

- Status: todo
- Completion: manual
- Priority: P0
- Track: mcp
- Depends on: VOICE-CARE-019, VOICE-CARE-020
- Goal id: VOICE-CARE-G061
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/adapters/mcplusplus.py, ipfs_accelerate_py/test/api/voice_workflows/adapter_contract/test_mcplusplus_adapter.py, docs/voice_workflows/MCPPLUSPLUS_BINDINGS.md
- Validation: python -m pytest -q ipfs_accelerate_py/test/api/voice_workflows/adapter_contract/test_mcplusplus_adapter.py
- Board namespace: voice-care-workflow-dag-v1
- Bundle: voice-care/mcp
- Parallel lane: wave-07-mcplusplus
- Resource class: integration-medium
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/adapters/mcplusplus.py, ipfs_accelerate_py/test/api/voice_workflows/adapter_contract/test_mcplusplus_adapter.py, docs/voice_workflows/MCPPLUSPLUS_BINDINGS.md
- Conflict policy: Owns only the MCP++ adapter and binding tests.
- Symbolic first: true
- LLM context budget bytes: 24576
- Acceptance: Logical capabilities bind to an operator-approved MCP++ server, tool, schema digest, delegation scope, and transport policy outside profile content; tests exercise the shipped `TrioMCPClient` discovery, `tools/list`, `tools/call`, and `mcp++/execute` paths; every invocation carries tenant, proposal, lease, policy, and idempotency identities; `retry=False` is forced for mutations unless the provider contract explicitly declares idempotency and propagates the canonical key; absent or mismatched delegation fails closed; tool discovery cannot create authority; and receipts are normalized and redacted.

## VOICE-CARE-022 Implement the conventional MCP capability adapter

- Status: todo
- Completion: manual
- Priority: P0
- Track: mcp
- Depends on: VOICE-CARE-019, VOICE-CARE-020
- Goal id: VOICE-CARE-G061
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/adapters/mcp.py, ipfs_accelerate_py/test/api/voice_workflows/adapter_contract/test_mcp_adapter.py, docs/voice_workflows/MCP_BINDINGS.md
- Validation: python -m pytest -q ipfs_accelerate_py/test/api/voice_workflows/adapter_contract/test_mcp_adapter.py
- Board namespace: voice-care-workflow-dag-v1
- Bundle: voice-care/mcp
- Parallel lane: wave-07-mcp
- Resource class: integration-medium
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/adapters/mcp.py, ipfs_accelerate_py/test/api/voice_workflows/adapter_contract/test_mcp_adapter.py, docs/voice_workflows/MCP_BINDINGS.md
- Conflict policy: Owns only the conventional MCP adapter and binding tests.
- Symbolic first: true
- LLM context budget bytes: 24576
- Acceptance: The adapter pins approved server identity, tool name, protocol version, and input and output schema digests in trusted deployment configuration; validates capabilities on connect and before dispatch; rejects tool substitution, schema drift, untrusted notifications, and oversized output; and provides timeout, cancellation, reconciliation, and redacted receipt behavior consistent with the SPI.

## VOICE-CARE-023 Implement a fixed-argv CLI capability adapter without a shell

- Status: todo
- Completion: manual
- Priority: P0
- Track: native-adapters
- Depends on: VOICE-CARE-019, VOICE-CARE-020
- Goal id: VOICE-CARE-G061
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/adapters/cli.py, ipfs_accelerate_py/test/api/voice_workflows/adapter_contract/test_cli_adapter.py, docs/voice_workflows/CLI_BINDINGS.md
- Validation: python -m pytest -q ipfs_accelerate_py/test/api/voice_workflows/adapter_contract/test_cli_adapter.py
- Board namespace: voice-care-workflow-dag-v1
- Bundle: voice-care/native-adapters
- Parallel lane: wave-07-cli
- Resource class: security-medium
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/adapters/cli.py, ipfs_accelerate_py/test/api/voice_workflows/adapter_contract/test_cli_adapter.py, docs/voice_workflows/CLI_BINDINGS.md
- Conflict policy: Owns only the CLI adapter and its process-isolation policy.
- Symbolic first: true
- LLM context budget bytes: 16384
- Acceptance: Only operator-registered executables and fixed argument templates are callable; no shell, interpolation, PATH search, working-directory escape, environment inheritance, profile-supplied executable, or caller-supplied option name is permitted; resource limits and output bounds apply; and injection fixtures cannot alter the launched argv.

## VOICE-CARE-024 Implement an injected Python callable capability adapter

- Status: todo
- Completion: manual
- Priority: P0
- Track: native-adapters
- Depends on: VOICE-CARE-019, VOICE-CARE-020
- Goal id: VOICE-CARE-G061
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/adapters/python_callable.py, ipfs_accelerate_py/test/api/voice_workflows/adapter_contract/test_python_callable_adapter.py, docs/voice_workflows/PYTHON_BINDINGS.md
- Validation: python -m pytest -q ipfs_accelerate_py/test/api/voice_workflows/adapter_contract/test_python_callable_adapter.py
- Board namespace: voice-care-workflow-dag-v1
- Bundle: voice-care/native-adapters
- Parallel lane: wave-07-python
- Resource class: cpu-medium
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/adapters/python_callable.py, ipfs_accelerate_py/test/api/voice_workflows/adapter_contract/test_python_callable_adapter.py, docs/voice_workflows/PYTHON_BINDINGS.md
- Conflict policy: Owns only dependency-injected callable bindings and forbids dynamic import resolution.
- Symbolic first: true
- LLM context budget bytes: 16384
- Acceptance: Trusted application code injects a callable under a logical capability during startup; profile, GraphRAG, transcript, and request data cannot name modules, classes, methods, or dotted paths; request and result schemas are enforced; blocking work is bounded; exceptions are normalized and redacted; and registry replacement requires an audited operator deployment.

## VOICE-CARE-025 Implement a registered HTTP and webhook capability adapter

- Status: todo
- Completion: manual
- Priority: P0
- Track: native-adapters
- Depends on: VOICE-CARE-019, VOICE-CARE-020
- Goal id: VOICE-CARE-G061
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/adapters/http.py, ipfs_accelerate_py/test/api/voice_workflows/adapter_contract/test_http_adapter.py, docs/voice_workflows/HTTP_BINDINGS.md
- Validation: python -m pytest -q ipfs_accelerate_py/test/api/voice_workflows/adapter_contract/test_http_adapter.py
- Board namespace: voice-care-workflow-dag-v1
- Bundle: voice-care/native-adapters
- Parallel lane: wave-07-http
- Resource class: security-large
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/adapters/http.py, ipfs_accelerate_py/test/api/voice_workflows/adapter_contract/test_http_adapter.py, docs/voice_workflows/HTTP_BINDINGS.md
- Conflict policy: Owns only the HTTP adapter and egress policy.
- Symbolic first: true
- LLM context budget bytes: 24576
- Acceptance: Endpoints, methods, redirect policy, DNS and address constraints, certificates, credentials, schemas, and retry semantics come only from trusted deployment registration; profile and caller data cannot select a URL; SSRF, DNS rebinding, redirect escape, request smuggling, credential forwarding, oversized bodies, and unsafe retries are denied and tested.

## VOICE-CARE-026 Implement read-only agent-supervisor inspection capabilities

- Status: todo
- Completion: manual
- Priority: P0
- Track: supervisor-adapter
- Depends on: VOICE-CARE-019, VOICE-CARE-020
- Goal id: VOICE-CARE-G062
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/adapters/supervisor.py, ipfs_accelerate_py/test/api/voice_workflows/adapter_contract/test_supervisor_inspection.py, docs/voice_workflows/SUPERVISOR_VOICE_CAPABILITIES.md
- Validation: python -m pytest -q ipfs_accelerate_py/test/api/voice_workflows/adapter_contract/test_supervisor_inspection.py
- Board namespace: voice-care-workflow-dag-v1
- Bundle: voice-care/supervisor-adapter
- Parallel lane: wave-07-supervisor-read
- Resource class: cpu-medium
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/adapters/supervisor.py, ipfs_accelerate_py/test/api/voice_workflows/adapter_contract/test_supervisor_inspection.py, docs/voice_workflows/SUPERVISOR_VOICE_CAPABILITIES.md
- Conflict policy: Owns the supervisor adapter module; mutation support is added only by the dependent task.
- Symbolic first: true
- LLM context budget bytes: 24576
- Acceptance: A narrow allowlist exposes status, goal, task, worker, evidence, and bounded log summaries with tenant-safe redaction and pagination; raw filesystem reads, commands, prompts, credentials, patches, and arbitrary task selection are unavailable; stale or unavailable supervisor state is reported as unknown rather than inferred.

## VOICE-CARE-027 Gate delegated agent-supervisor mutations behind formal plans and quotas

- Status: todo
- Completion: manual
- Priority: P0
- Track: supervisor-adapter
- Depends on: VOICE-CARE-015, VOICE-CARE-016, VOICE-CARE-026
- Goal id: VOICE-CARE-G062
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/adapters/supervisor_mutations.py, ipfs_accelerate_py/test/api/voice_workflows/adapter_contract/test_supervisor_mutations.py, docs/voice_workflows/SUPERVISOR_DELEGATION_POLICY.md
- Validation: python -m pytest -q ipfs_accelerate_py/test/api/voice_workflows/adapter_contract/test_supervisor_mutations.py
- Board namespace: voice-care-workflow-dag-v1
- Bundle: voice-care/supervisor-adapter
- Parallel lane: wave-08-supervisor-write
- Resource class: security-large
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/adapters/supervisor_mutations.py, ipfs_accelerate_py/test/api/voice_workflows/adapter_contract/test_supervisor_mutations.py, docs/voice_workflows/SUPERVISOR_DELEGATION_POLICY.md
- Conflict policy: Owns mutation admission and cannot weaken the general policy gateway.
- Symbolic first: true
- LLM context budget bytes: 24576
- Acceptance: Voice can request only predeclared operations against a validated objective and task plan with explicit operator delegation, confirmation, task and resource quotas, path scope, isolated worktree, protected branches, and expiry; it cannot expand write roots, submit raw implementation commands, merge, push, publish, mark completion, alter refill policy, or increase resources; every accepted or denied attempt emits an auditable receipt.

## VOICE-CARE-028 Add an optional workflow collaborator to the existing voice router

- Status: todo
- Completion: manual
- Priority: P0
- Track: orchestration
- Depends on: VOICE-CARE-012, VOICE-CARE-014, VOICE-CARE-015
- Goal id: VOICE-CARE-G070
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/router_collaborator.py, ipfs_accelerate_py/test/api/voice_workflows/test_voice_router_workflow_compatibility.py, docs/voice_workflows/VOICE_ROUTER_COMPATIBILITY.md
- Validation: python -m pytest -q ipfs_accelerate_py/test/api/voice_workflows/test_voice_router_workflow_compatibility.py
- Board namespace: voice-care-workflow-dag-v1
- Bundle: voice-care/orchestration
- Parallel lane: wave-05-router
- Resource class: integration-large
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/router_collaborator.py, ipfs_accelerate_py/test/api/voice_workflows/test_voice_router_workflow_compatibility.py, docs/voice_workflows/VOICE_ROUTER_COMPATIBILITY.md
- Conflict policy: Adds a collaborator boundary without rewriting existing voice-router result contracts.
- Symbolic first: true
- LLM context budget bytes: 32768
- Acceptance: Existing one-turn and telephone APIs remain compatible when the collaborator is absent; when enabled, the router passes a canonical grounded proposal to the engine and receives only safe dialogue, action-state, or handoff directives; response-DAG cache misses remain content candidates, never executable nodes; and timeouts degrade to current safe response behavior.

## VOICE-CARE-029 Implement typed slot collection, validation, clarification, consent, and confirmation dialogue

- Status: todo
- Completion: manual
- Priority: P0
- Track: orchestration
- Depends on: VOICE-CARE-015, VOICE-CARE-028
- Goal id: VOICE-CARE-G070
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/dialogue.py, ipfs_accelerate_py/test/api/voice_workflows/test_voice_workflow_dialogue.py, docs/voice_workflows/DIALOGUE_STATE.md
- Validation: python -m pytest -q ipfs_accelerate_py/test/api/voice_workflows/test_voice_workflow_dialogue.py
- Board namespace: voice-care-workflow-dag-v1
- Bundle: voice-care/orchestration
- Parallel lane: wave-06-dialogue
- Resource class: cpu-large
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/dialogue.py, ipfs_accelerate_py/test/api/voice_workflows/test_voice_workflow_dialogue.py, docs/voice_workflows/DIALOGUE_STATE.md
- Conflict policy: Owns domain-neutral dialogue transitions; profile text and field definitions remain data.
- Symbolic first: true
- LLM context budget bytes: 24576
- Acceptance: Dialogue collects only declared fields, validates typed values before persistence, explains purpose and retention, distinguishes clarification from confirmation, reads back material effects, supports correction and withdrawal, never treats silence or uncertain ASR as consent, and routes repeated uncertainty to a configured safe fallback or human.

## VOICE-CARE-030 Persist encrypted resumable sessions across voice, phone, and portal channels

- Status: todo
- Completion: manual
- Priority: P0
- Track: orchestration
- Depends on: VOICE-CARE-009, VOICE-CARE-016, VOICE-CARE-029
- Goal id: VOICE-CARE-G070
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/sessions.py, ipfs_accelerate_py/test/api/voice_workflows/test_voice_workflow_sessions.py, ipfs_kit_py/ipfs_kit_py/voice_workflow_store.py, ipfs_kit_py/tests/test_voice_workflow_store.py
- Validation: python -m pytest -q ipfs_accelerate_py/test/api/voice_workflows/test_voice_workflow_sessions.py ipfs_kit_py/tests/test_voice_workflow_store.py
- Board namespace: voice-care-workflow-dag-v1
- Bundle: voice-care/orchestration
- Parallel lane: wave-07-sessions
- Resource class: io-large
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/sessions.py, ipfs_accelerate_py/test/api/voice_workflows/test_voice_workflow_sessions.py, ipfs_kit_py/ipfs_kit_py/voice_workflow_store.py, ipfs_kit_py/tests/test_voice_workflow_store.py
- Conflict policy: Owns session interface and optional IPFS Kit implementation; the dependency-light local store remains in the runtime state task.
- Symbolic first: true
- LLM context budget bytes: 32768
- Acceptance: Session state is tenant-bound, encrypted, retention-limited, versioned, and optimistic-concurrency safe; a scoped resume token can transfer a declared workflow between phone, browser voice, chat, and operator surfaces without copying public indexes or secrets; profile changes invoke an explicit migration or safe restart; and deletion removes private records and embeddings while retaining only permitted audit commitments.

## VOICE-CARE-031 Define privacy-minimized human handoff, queue, grant, and outcome contracts

- Status: todo
- Completion: manual
- Priority: P0
- Track: human-care
- Depends on: VOICE-CARE-005, VOICE-CARE-015, VOICE-CARE-029
- Goal id: VOICE-CARE-G071
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/handoff.py, ipfs_accelerate_py/test/api/voice_workflows/test_voice_handoff_contracts.py, docs/voice_workflows/HUMAN_HANDOFF.md
- Validation: python -m pytest -q ipfs_accelerate_py/test/api/voice_workflows/test_voice_handoff_contracts.py
- Board namespace: voice-care-workflow-dag-v1
- Bundle: voice-care/human-care
- Parallel lane: wave-07-handoff-contract
- Resource class: security-medium
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/handoff.py, ipfs_accelerate_py/test/api/voice_workflows/test_voice_handoff_contracts.py, docs/voice_workflows/HUMAN_HANDOFF.md
- Conflict policy: Owns generic handoff records and field-release enforcement.
- Symbolic first: true
- LLM context budget bytes: 24576
- Acceptance: Handoff context is the intersection of an explicit caller grant and destination queue schema; purpose, fields, expiry, urgency, locale, accessibility, channel, consent receipt, and provenance are explicit; transcript sharing is off by default; revocation and redaction are enforceable; and unknown destination policy blocks transfer rather than over-sharing.

## VOICE-CARE-032 Implement callback, warm-transfer, SIP or telephony, and operator-presence orchestration

- Status: todo
- Completion: manual
- Priority: P0
- Track: human-care
- Depends on: VOICE-CARE-016, VOICE-CARE-030, VOICE-CARE-031
- Goal id: VOICE-CARE-G072
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/channels/telephony.py, ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/channels/transfer.py, ipfs_accelerate_py/test/api/voice_workflows/test_voice_telephony_handoff.py
- Validation: python -m pytest -q ipfs_accelerate_py/test/api/voice_workflows/test_voice_telephony_handoff.py
- Board namespace: voice-care-workflow-dag-v1
- Bundle: voice-care/human-care
- Parallel lane: wave-08-telephony
- Resource class: integration-large
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/channels/telephony.py, ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/channels/transfer.py, ipfs_accelerate_py/test/api/voice_workflows/test_voice_telephony_handoff.py
- Conflict policy: Owns provider-neutral channel and transfer interfaces; provider bindings live in deployment configuration.
- Symbolic first: true
- LLM context budget bytes: 32768
- Acceptance: The orchestrator supports queue placement, availability checks, consented context release, warm transfer, callback scheduling, decline, no-answer, busy, timeout, disconnect, and resume; provider callbacks are authenticated and replay-safe; caller-visible status never fabricates operator presence; and failed transfer returns to a defined workflow branch.

## VOICE-CARE-033 Add crisis, abuse, accessibility, and degraded-mode escalation policy

- Status: todo
- Completion: manual
- Priority: P0
- Track: human-care
- Depends on: VOICE-CARE-003, VOICE-CARE-018, VOICE-CARE-031, VOICE-CARE-032
- Goal id: VOICE-CARE-G071
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/escalation.py, ipfs_accelerate_py/test/api/voice_workflows/test_voice_escalation_policy.py, docs/voice_workflows/SAFE_DEGRADED_MODE.md
- Validation: python -m pytest -q ipfs_accelerate_py/test/api/voice_workflows/test_voice_escalation_policy.py
- Board namespace: voice-care-workflow-dag-v1
- Bundle: voice-care/human-care
- Parallel lane: wave-09-escalation
- Resource class: safety-review
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/escalation.py, ipfs_accelerate_py/test/api/voice_workflows/test_voice_escalation_policy.py, docs/voice_workflows/SAFE_DEGRADED_MODE.md
- Conflict policy: Owns generic escalation primitives; domain emergency destinations remain signed profile data.
- Symbolic first: true
- LLM context budget bytes: 24576
- Acceptance: Deterministic policy can prioritize human help, accessibility support, alternate channel, or safe information when confidence, adapter health, caller risk, abuse, or connectivity requires it; it does not make unmodeled clinical or legal claims; emergency destinations are current and cited; and no failure mode strands a caller in a mutating or falsely transferred state.

## VOICE-CARE-034 Build content-addressed action, transition, interaction, handoff, and activation receipts

- Status: todo
- Completion: manual
- Priority: P0
- Track: assurance
- Depends on: VOICE-CARE-006, VOICE-CARE-016, VOICE-CARE-017, VOICE-CARE-031
- Goal id: VOICE-CARE-G090
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/receipts.py, ipfs_accelerate_py/test/api/voice_workflows/test_voice_workflow_receipts.py, docs/voice_workflows/schemas/receipt-dag-v1.md
- Validation: python -m pytest -q ipfs_accelerate_py/test/api/voice_workflows/test_voice_workflow_receipts.py
- Board namespace: voice-care-workflow-dag-v1
- Bundle: voice-care/assurance
- Parallel lane: wave-08-receipts
- Resource class: cpu-large
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/receipts.py, ipfs_accelerate_py/test/api/voice_workflows/test_voice_workflow_receipts.py, docs/voice_workflows/schemas/receipt-dag-v1.md
- Conflict policy: Owns receipt schemas and append validation; it does not publish private payloads.
- Symbolic first: true
- LLM context budget bytes: 24576
- Acceptance: Append-only receipts bind prior receipt, tenant-private commitment, profile, policy, workflow, proposal, authorization, lease, adapter capability, request and response schema, redacted outcome, and timestamps; broken links, forks, replay conflicts, invalid terminal rewrites, and cross-tenant references are rejected; and private values are encrypted or committed rather than placed in public receipts.

## VOICE-CARE-035 Add CID-keyed pure caches and an idempotency receipt ledger with invalidation proofs

- Status: todo
- Completion: manual
- Priority: P0
- Track: assurance
- Depends on: VOICE-CARE-009, VOICE-CARE-015, VOICE-CARE-034
- Goal id: VOICE-CARE-G090
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/cache.py, ipfs_accelerate_py/test/api/voice_workflows/test_voice_workflow_cache.py, docs/voice_workflows/CACHE_VALIDITY.md
- Validation: python -m pytest -q ipfs_accelerate_py/test/api/voice_workflows/test_voice_workflow_cache.py
- Board namespace: voice-care-workflow-dag-v1
- Bundle: voice-care/assurance
- Parallel lane: wave-09-cache
- Resource class: cpu-medium
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/cache.py, ipfs_accelerate_py/test/api/voice_workflows/test_voice_workflow_cache.py, docs/voice_workflows/CACHE_VALIDITY.md
- Conflict policy: Owns runtime cache validity and delegates canonical identity to the datasets package.
- Symbolic first: true
- LLM context budget bytes: 16384
- Acceptance: Pure-cache identity binds all semantic inputs including tenant, profile, policy, schemas, runtime version, and capability snapshot; mutation effects are never served from the generic result cache; the idempotency ledger returns a prior receipt only for the same tenant, admitted proposal, key, and payload commitment and conflicts otherwise; every dispatch re-evaluates revocation epoch, consent and authentication freshness, quota, lease and fence, clock, tenant, and principal even after a cache hit; invalidation is defense in depth rather than the sole safety mechanism; and every hit emits a machine-checkable validity explanation.

## VOICE-CARE-036 Encode invariants as logic constraints and emit bounded counterexamples

- Status: todo
- Completion: manual
- Priority: P0
- Track: formal-assurance
- Depends on: VOICE-CARE-003, VOICE-CARE-007, VOICE-CARE-014, VOICE-CARE-015, VOICE-CARE-016, VOICE-CARE-034
- Goal id: VOICE-CARE-G090
- Outputs: ipfs_datasets_py/ipfs_datasets_py/logic/voice_workflows/model.py, ipfs_datasets_py/ipfs_datasets_py/logic/voice_workflows/constraints.py, ipfs_datasets_py/tests/unit/logic/voice_workflows/test_constraints.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/logic/voice_workflows/test_constraints.py
- Board namespace: voice-care-workflow-dag-v1
- Bundle: voice-care/assurance
- Parallel lane: wave-09-symbolic
- Resource class: solver-large
- Predicted files: ipfs_datasets_py/ipfs_datasets_py/logic/voice_workflows/model.py, ipfs_datasets_py/ipfs_datasets_py/logic/voice_workflows/constraints.py, ipfs_datasets_py/tests/unit/logic/voice_workflows/test_constraints.py
- Conflict policy: Owns formal models and clearly separates modeled facts from runtime observations.
- Symbolic first: true
- LLM context budget bytes: 32768
- Acceptance: Constraints cover authorization before execution, confirmation or standing consent for mutation, tenant equality, replay identity, conclusive terminal monotonicity, explicit unresolved unknown outcomes, current evidence for system-authored domain and action claims, caller-assertion attribution, private-to-public and private-to-unapproved-inference noninterference, handoff field subset, authority monotonicity, and supervisor delegation; satisfiable violations emit minimal replayable counterexamples; unsupported dynamic behavior remains unknown.

## VOICE-CARE-037 Add optional zero-knowledge receipt attestations in shadow mode

- Status: todo
- Completion: manual
- Priority: P2
- Track: formal-assurance
- Depends on: VOICE-CARE-006, VOICE-CARE-034, VOICE-CARE-036
- Goal id: VOICE-CARE-G090
- Outputs: ipfs_datasets_py/ipfs_datasets_py/logic/voice_workflows/zk_attestations.py, ipfs_datasets_py/tests/unit/logic/voice_workflows/test_zk_attestations.py, docs/voice_workflows/ZK_ATTESTATION_PROFILE.md
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/logic/voice_workflows/test_zk_attestations.py
- Board namespace: voice-care-workflow-dag-v1
- Bundle: voice-care/assurance
- Parallel lane: wave-10-zk-shadow
- Resource class: solver-large
- Predicted files: ipfs_datasets_py/ipfs_datasets_py/logic/voice_workflows/zk_attestations.py, ipfs_datasets_py/tests/unit/logic/voice_workflows/test_zk_attestations.py, docs/voice_workflows/ZK_ATTESTATION_PROFILE.md
- Conflict policy: Owns optional attestation interfaces and cannot become an execution dependency in the first release.
- Symbolic first: true
- LLM context budget bytes: 32768
- Acceptance: Shadow-mode proofs can attest a versioned public statement such as valid signatures, bound CIDs, admitted policy facts, and allowed transition without revealing selected private inputs; verifier keys, circuit versions, public inputs, and trusted setup assumptions are explicit; unsupported adapters or statements yield unsupported; and no artifact claims to prove external side effects or arbitrary Python behavior.

## VOICE-CARE-038 Publish tenant, profile, session, workflow, action, consent, and handoff APIs

- Status: todo
- Completion: manual
- Priority: P0
- Track: portal
- Depends on: VOICE-CARE-008, VOICE-CARE-014, VOICE-CARE-015, VOICE-CARE-030, VOICE-CARE-031, VOICE-CARE-034
- Goal id: VOICE-CARE-G080
- Outputs: wallet_interface/routes/voice_workflows.py, wallet_interface/schemas/voice_workflows.py, tests/api/test_voice_workflow_api.py
- Validation: python -m pytest -q tests/api/test_voice_workflow_api.py
- Board namespace: voice-care-workflow-dag-v1
- Bundle: voice-care/portal
- Parallel lane: wave-09-api
- Resource class: integration-large
- Predicted files: wallet_interface/routes/voice_workflows.py, wallet_interface/schemas/voice_workflows.py, tests/api/test_voice_workflow_api.py
- Conflict policy: Owns the parent-product API boundary and calls generic runtime interfaces only.
- Symbolic first: true
- LLM context budget bytes: 32768
- Acceptance: Authenticated APIs expose schema-driven profile metadata, safe conversation turns, resumable session state, workflow timeline, proposed action, confirmation, cancellation, consent, callback, handoff, and redacted receipts; tenant scope and optimistic concurrency are mandatory; arbitrary capability, adapter, command, locator, policy, or receipt mutation inputs are absent.

## VOICE-CARE-039 Build accessible schema-driven client intake and customer-care surfaces

- Status: todo
- Completion: manual
- Priority: P1
- Track: portal
- Depends on: VOICE-CARE-029, VOICE-CARE-030, VOICE-CARE-038
- Goal id: VOICE-CARE-G080
- Outputs: wallet_interface/ui/src/features/voice-workflows/client/, wallet_interface/ui/tests/voice-workflows-client.spec.ts, docs/voice_workflows/CLIENT_UX.md
- Validation: npm --prefix wallet_interface/ui test -- tests/voice-workflows-client.spec.ts
- Board namespace: voice-care-workflow-dag-v1
- Bundle: voice-care/portal
- Parallel lane: wave-10-client-ui
- Resource class: browser-large
- Predicted files: wallet_interface/ui/src/features/voice-workflows/client/, wallet_interface/ui/tests/voice-workflows-client.spec.ts, docs/voice_workflows/CLIENT_UX.md
- Conflict policy: Owns new client workflow UI paths and reuses existing design and action primitives without editing their contracts.
- Symbolic first: true
- LLM context budget bytes: 32768
- Acceptance: Users can review citations, collect and correct fields, understand purpose and retention, grant or withdraw consent, confirm material effects, see pending or unknown outcomes, cancel where valid, request a human or callback, and resume across channels; keyboard, screen-reader, reduced-motion, localization, low-bandwidth, and no-microphone paths pass automated checks.

## VOICE-CARE-040 Build the operator queue, transfer, audit, and workflow diagnostics surfaces

- Status: todo
- Completion: manual
- Priority: P1
- Track: portal
- Depends on: VOICE-CARE-031, VOICE-CARE-032, VOICE-CARE-034, VOICE-CARE-038
- Goal id: VOICE-CARE-G080
- Outputs: wallet_interface/ui/src/features/voice-workflows/operator/, wallet_interface/ui/tests/voice-workflows-operator.spec.ts, docs/voice_workflows/OPERATOR_UX.md
- Validation: npm --prefix wallet_interface/ui test -- tests/voice-workflows-operator.spec.ts
- Board namespace: voice-care-workflow-dag-v1
- Bundle: voice-care/portal
- Parallel lane: wave-10-operator-ui
- Resource class: browser-large
- Predicted files: wallet_interface/ui/src/features/voice-workflows/operator/, wallet_interface/ui/tests/voice-workflows-operator.spec.ts, docs/voice_workflows/OPERATOR_UX.md
- Conflict policy: Owns new operator workflow UI paths and never exposes unredacted secrets or unrestricted supervisor controls.
- Symbolic first: true
- LLM context budget bytes: 32768
- Acceptance: Authorized operators can view scoped queues, availability, caller-granted context, workflow and action timeline, unknown outcomes, transfer status, redacted receipts, escalation reason, and safe retry or resolution choices; field access is role- and grant-filtered; every operator action is confirmed when material and audited.

## VOICE-CARE-041 Migrate Abby and 211 content into a signed 211-AI domain profile

- Status: todo
- Completion: manual
- Priority: P0
- Track: 211-profile
- Depends on: VOICE-CARE-008, VOICE-CARE-009, VOICE-CARE-010, VOICE-CARE-012
- Goal id: VOICE-CARE-G100
- Outputs: profiles/voice_workflows/211-ai/, scripts/voice_workflows/import_211_abby.py, tests/profiles/test_211_voice_profile.py
- Validation: python -m pytest -q tests/profiles/test_211_voice_profile.py
- Board namespace: voice-care-workflow-dag-v1
- Bundle: voice-care/211
- Parallel lane: wave-08-211-content
- Resource class: data-large
- Predicted files: profiles/voice_workflows/211-ai/, scripts/voice_workflows/import_211_abby.py, tests/profiles/test_211_voice_profile.py
- Conflict policy: Owns the 211-AI profile tree and compatibility importer; generic package files are read-only.
- Symbolic first: true
- LLM context budget bytes: 32768
- Acceptance: A deterministic importer maps current Abby responses, evidence, intents, locales, and audio references into public content records without changing their meaning; 211 workflows and logical actions live in signed control records; validation rejects private data and executable locators; golden queries remain grounded; and the legacy voice provider remains available during migration.

## VOICE-CARE-042 Bind 211 service actions and human-care routes and run a guarded pilot

- Status: todo
- Completion: manual
- Priority: P1
- Track: 211-profile
- Depends on: VOICE-CARE-021, VOICE-CARE-022, VOICE-CARE-025, VOICE-CARE-032, VOICE-CARE-033, VOICE-CARE-041, VOICE-CARE-052
- Goal id: VOICE-CARE-G100
- Outputs: profiles/voice_workflows/211-ai/deployment.example.json, tests/e2e/voice_workflows/test_211_client_care.py, docs/voice_workflows/211_PILOT.md
- Validation: python -m pytest -q tests/e2e/voice_workflows/test_211_client_care.py
- Board namespace: voice-care-workflow-dag-v1
- Bundle: voice-care/211
- Parallel lane: wave-11-211-pilot
- Resource class: integration-large
- Predicted files: profiles/voice_workflows/211-ai/deployment.example.json, tests/e2e/voice_workflows/test_211_client_care.py, docs/voice_workflows/211_PILOT.md
- Conflict policy: Owns 211 deployment examples, pilot fixtures, and evaluation; live credentials and production mutations are forbidden.
- Symbolic first: true
- LLM context budget bytes: 32768
- Acceptance: Synthetic calls cover resource discovery, intake, service action proposal, explicit confirmation, callback, warm human transfer, decline, disconnect, stale data, adapter outage, and safe escalation; bindings reference only operator-approved logical capabilities and opaque secret handles; pilot gates define consent, monitoring, rollback, sample limits, and human override without enabling production by default.

## VOICE-CARE-043 Provide a reusable profile authoring SDK, validator, compiler, and local simulator

- Status: todo
- Completion: manual
- Priority: P1
- Track: reusable-sdk
- Depends on: VOICE-CARE-007, VOICE-CARE-008, VOICE-CARE-010, VOICE-CARE-014, VOICE-CARE-020
- Goal id: VOICE-CARE-G110
- Outputs: ipfs_datasets_py/ipfs_datasets_py/voice_workflows/authoring.py, scripts/voice_workflows/profile_tool.py, tests/voice_workflows/test_profile_authoring.py
- Validation: python -m pytest -q tests/voice_workflows/test_profile_authoring.py
- Board namespace: voice-care-workflow-dag-v1
- Bundle: voice-care/reuse
- Parallel lane: wave-09-authoring-sdk
- Resource class: cpu-large
- Predicted files: ipfs_datasets_py/ipfs_datasets_py/voice_workflows/authoring.py, scripts/voice_workflows/profile_tool.py, tests/voice_workflows/test_profile_authoring.py
- Conflict policy: Owns authoring and simulation tools and does not add domain-specific branches to generic runtime code.
- Symbolic first: true
- LLM context budget bytes: 32768
- Acceptance: A domain author can validate, compile, diff, sign, inspect, simulate, migrate, and package content, action, workflow, policy, locale, and UI records; diagnostics are deterministic and point to schema locations; simulation uses fake admitted adapters and cannot make external effects; templates cannot introduce raw commands, imports, endpoints, credentials, or authority.

## VOICE-CARE-044 Prove pack swapping with an unrelated IT helpdesk reference profile

- Status: todo
- Completion: manual
- Priority: P1
- Track: reusable-sdk
- Depends on: VOICE-CARE-043, VOICE-CARE-052
- Goal id: VOICE-CARE-G110
- Outputs: profiles/voice_workflows/it-helpdesk-reference/, tests/profiles/test_it_helpdesk_voice_profile.py, tests/e2e/voice_workflows/test_profile_swap.py
- Validation: python -m pytest -q tests/profiles/test_it_helpdesk_voice_profile.py tests/e2e/voice_workflows/test_profile_swap.py
- Board namespace: voice-care-workflow-dag-v1
- Bundle: voice-care/reuse
- Parallel lane: wave-11-neutral-profile
- Resource class: integration-large
- Predicted files: profiles/voice_workflows/it-helpdesk-reference/, tests/profiles/test_it_helpdesk_voice_profile.py, tests/e2e/voice_workflows/test_profile_swap.py
- Conflict policy: Owns only the neutral reference profile and swap tests; core and portal source changes are disallowed.
- Symbolic first: true
- LLM context budget bytes: 32768
- Acceptance: An unrelated profile supports issue intake, device and account slots, knowledge retrieval, approved diagnostic action, ticket creation, callback, and technician handoff; activating it changes data and signed bindings only; the same runtime, APIs, client UI, and operator UI execute both profiles; and cross-profile cache, session, wording, action, and receipt leakage tests remain empty.

## VOICE-CARE-045 Add model-based, property, fuzz, and deterministic replay verification

- Status: todo
- Completion: manual
- Priority: P0
- Track: verification
- Depends on: VOICE-CARE-007, VOICE-CARE-014, VOICE-CARE-016, VOICE-CARE-017, VOICE-CARE-020, VOICE-CARE-034, VOICE-CARE-036
- Goal id: VOICE-CARE-G090
- Outputs: tests/property/voice_workflows/, tests/fuzz/voice_workflows/, scripts/voice_workflows/replay_receipts.py
- Validation: python -m pytest -q tests/property/voice_workflows tests/fuzz/voice_workflows
- Board namespace: voice-care-workflow-dag-v1
- Bundle: voice-care/verification
- Parallel lane: wave-10-model-tests
- Resource class: cpu-large
- Predicted files: tests/property/voice_workflows/, tests/fuzz/voice_workflows/, scripts/voice_workflows/replay_receipts.py
- Conflict policy: Owns generative verification and replay tooling; implementation files are read-only.
- Symbolic first: true
- LLM context budget bytes: 24576
- Acceptance: Generated workflows, events, crashes, retries, cancellations, revocations, profile swaps, malformed records, and concurrent workers test compiler and runtime invariants; every failure shrinks to a stable seed and minimal trace; receipt replay reproduces the same modeled state; and incomplete coverage or unsupported behavior cannot be reported as proved.

## VOICE-CARE-046 Complete adversarial security, privacy, and tenant-isolation verification

- Status: todo
- Completion: manual
- Priority: P0
- Track: verification
- Depends on: VOICE-CARE-013, VOICE-CARE-015, VOICE-CARE-018, VOICE-CARE-021, VOICE-CARE-022, VOICE-CARE-023, VOICE-CARE-024, VOICE-CARE-025, VOICE-CARE-027, VOICE-CARE-030, VOICE-CARE-031
- Goal id: VOICE-CARE-G090
- Outputs: tests/security/voice_workflows/, docs/voice_workflows/SECURITY_REVIEW.md, data/voice_workflows/evaluation/security-gates.json
- Validation: python -m pytest -q tests/security/voice_workflows
- Board namespace: voice-care-workflow-dag-v1
- Bundle: voice-care/verification
- Parallel lane: wave-11-security
- Resource class: security-large
- Predicted files: tests/security/voice_workflows/, docs/voice_workflows/SECURITY_REVIEW.md, data/voice_workflows/evaluation/security-gates.json
- Conflict policy: Owns adversarial fixtures and release findings; fixes are emitted as new bounded tasks rather than broad edits.
- Symbolic first: true
- LLM context budget bytes: 32768
- Acceptance: Tests cover prompt and tool injection, schema smuggling, command injection, dynamic import attempts, SSRF and DNS rebinding, replay and confused deputy, forged callbacks, lease theft, signature and CID substitution, downgrade, cross-tenant cache and session access, transcript and embedding leakage, private fields sent outside an admitted tenant-isolated inference boundary, overbroad handoff, secret exposure, quota races, revocation races, and supervisor scope escalation; every P0 or P1 finding blocks release.

## VOICE-CARE-047 Run end-to-end, load, crash, channel, and accessibility release gates

- Status: todo
- Completion: manual
- Priority: P0
- Track: verification
- Depends on: VOICE-CARE-035, VOICE-CARE-042, VOICE-CARE-044, VOICE-CARE-045, VOICE-CARE-046, VOICE-CARE-052
- Goal id: VOICE-CARE-G120
- Outputs: tests/e2e/voice_workflows/test_release_matrix.py, scripts/voice_workflows/run_release_gates.py, data/voice_workflows/evaluation/release-report.json
- Validation: python scripts/voice_workflows/run_release_gates.py --check
- Board namespace: voice-care-workflow-dag-v1
- Bundle: voice-care/verification
- Parallel lane: wave-12-release-gates
- Resource class: integration-large
- Predicted files: tests/e2e/voice_workflows/test_release_matrix.py, scripts/voice_workflows/run_release_gates.py, data/voice_workflows/evaluation/release-report.json
- Conflict policy: Owns release orchestration and evidence only; it cannot waive failed component gates.
- Symbolic first: true
- LLM context budget bytes: 32768
- Acceptance: The matrix exercises browser voice, chat, telephone simulation, disconnect and resume, human transfer, each adapter class, profile activation and rollback, both reference profiles, cache invalidation, concurrent workers, crash boundaries, degraded dependencies, deletion, localization, and accessibility; results bind current tree and pack CIDs; optional ZK failure does not block non-ZK mode but cannot be mislabeled; mandatory gates pass without live credentials or production effects.

## VOICE-CARE-048 Publish operations runbooks and enable bounded objective refill

- Status: todo
- Completion: manual
- Priority: P0
- Track: operations
- Depends on: VOICE-CARE-001, VOICE-CARE-047
- Goal id: VOICE-CARE-G130
- Outputs: docs/voice_workflows/OPERATIONS_RUNBOOK.md, docs/voice_workflows/INCIDENT_AND_ROLLBACK.md, scripts/voice_workflows/supervisor_control.py
- Validation: python scripts/voice_workflows/supervisor_control.py readiness
- Board namespace: voice-care-workflow-dag-v1
- Bundle: voice-care/operations
- Parallel lane: wave-13-operations
- Resource class: operations-medium
- Predicted files: docs/voice_workflows/OPERATIONS_RUNBOOK.md, docs/voice_workflows/INCIDENT_AND_ROLLBACK.md, scripts/voice_workflows/supervisor_control.py
- Conflict policy: Serializes after the bootstrap owner for the shared control script and owns final operating procedures.
- Symbolic first: true
- LLM context budget bytes: 24576
- Acceptance: Runbooks cover signed profile promotion, canary limits, monitoring, receipt and queue diagnostics, kill switch, revocation, key rotation, adapter disablement, session and embedding deletion, incident evidence, profile and runtime rollback, human override, and recovery from outcome unknown; the supervisor refills only from deterministic static, symbolic, security, and evaluation findings with deduplication, bounded depth and count, protected paths, one refill owner, small evidence packets, and explicit operator review for scope or authority expansion.

## VOICE-CARE-049 Integrate datasets package exports and the legacy voice compatibility boundary

- Status: todo
- Completion: manual
- Priority: P0
- Track: integration
- Depends on: VOICE-CARE-005, VOICE-CARE-006, VOICE-CARE-007, VOICE-CARE-008, VOICE-CARE-010, VOICE-CARE-012, VOICE-CARE-043
- Goal id: VOICE-CARE-G010
- Outputs: ipfs_datasets_py/ipfs_datasets_py/voice_workflows/__init__.py, ipfs_datasets_py/ipfs_datasets_py/voice/__init__.py, ipfs_datasets_py/tests/unit/voice_workflows/test_package_exports.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/voice_workflows/test_package_exports.py
- Board namespace: voice-care-workflow-dag-v1
- Bundle: voice-care/integration
- Parallel lane: wave-09-datasets-adoption
- Resource class: integration-medium
- Predicted files: ipfs_datasets_py/ipfs_datasets_py/voice_workflows/__init__.py, ipfs_datasets_py/ipfs_datasets_py/voice/__init__.py, ipfs_datasets_py/tests/unit/voice_workflows/test_package_exports.py
- Conflict policy: Serial integration owner for datasets package exports; leaf data, compiler, and GraphRAG tasks may not edit these shared export files.
- Symbolic first: true
- LLM context budget bytes: 16384
- Acceptance: The generic records, compiler, profile, GraphRAG, and authoring entry points import through one documented package surface; the current Abby response-DAG and GraphRAG APIs remain available through an explicit versioned compatibility adapter; import tests prove that domain data is not loaded as an import side effect; and no export aliases legacy and new CID profiles as the same identity.

## VOICE-CARE-050 Integrate accelerator package exports and adopt the workflow collaborator in the voice router

- Status: todo
- Completion: manual
- Priority: P0
- Track: integration
- Depends on: VOICE-CARE-014, VOICE-CARE-015, VOICE-CARE-019, VOICE-CARE-028, VOICE-CARE-030, VOICE-CARE-031, VOICE-CARE-032
- Goal id: VOICE-CARE-G070
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/__init__.py, ipfs_accelerate_py/ipfs_accelerate_py/voice_router.py, ipfs_accelerate_py/test/api/voice_workflows/test_package_adoption.py
- Validation: python -m pytest -q ipfs_accelerate_py/test/api/voice_workflows/test_package_adoption.py
- Board namespace: voice-care-workflow-dag-v1
- Bundle: voice-care/integration
- Parallel lane: wave-10-accelerator-adoption
- Resource class: integration-large
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/__init__.py, ipfs_accelerate_py/ipfs_accelerate_py/voice_router.py, ipfs_accelerate_py/test/api/voice_workflows/test_package_adoption.py
- Conflict policy: Serial integration owner for accelerator exports and the existing voice-router adoption point; leaf runtime, adapter, session, handoff, and channel tasks treat these files as read-only.
- Symbolic first: true
- LLM context budget bytes: 24576
- Acceptance: The generic runtime, policy, adapter, session, handoff, and channel entry points have one stable import surface; `process_voice_turn` and `process_telephone_turn` preserve exact response-only behavior when no collaborator is injected; the optional collaborator receives only canonical grounded proposals and returns typed directives; an advisory handoff flag cannot be mistaken for a provider transfer receipt; and normal package CI collects the adoption test through the existing `test/api` path.

## VOICE-CARE-051 Register the workflow API through the existing wallet backend

- Status: todo
- Completion: manual
- Priority: P0
- Track: integration
- Depends on: VOICE-CARE-038, VOICE-CARE-049, VOICE-CARE-050
- Goal id: VOICE-CARE-G080
- Outputs: wallet_interface/api.py, wallet_interface/routes/__init__.py, wallet_interface/schemas/__init__.py, wallet_interface/tests/test_voice_workflow_api_adoption.py
- Validation: python -m pytest -q wallet_interface/tests/test_voice_workflow_api_adoption.py tests/api/test_voice_workflow_api.py
- Board namespace: voice-care-workflow-dag-v1
- Bundle: voice-care/integration
- Parallel lane: wave-11-backend-adoption
- Resource class: integration-large
- Predicted files: wallet_interface/api.py, wallet_interface/routes/__init__.py, wallet_interface/schemas/__init__.py, wallet_interface/tests/test_voice_workflow_api_adoption.py
- Conflict policy: Serial integration owner for the existing wallet API registry and package exports; task VOICE-CARE-038 owns only the new route and schema leaf modules.
- Symbolic first: true
- LLM context budget bytes: 24576
- Acceptance: The existing `wallet_interface/api.py` application registers the typed voice-workflow routes without converting the file into a directory or duplicating app construction; schema and route exports are explicit; authentication, tenant scope, optimistic concurrency, request limits, and server-side action admission are exercised through the real application; and legacy wallet endpoints remain unchanged.

## VOICE-CARE-052 Register profile-driven client and operator surfaces in the existing portal router

- Status: todo
- Completion: manual
- Priority: P0
- Track: integration
- Depends on: VOICE-CARE-039, VOICE-CARE-040, VOICE-CARE-051
- Goal id: VOICE-CARE-G080
- Outputs: wallet_interface/ui/src/features/voice-workflows/index.ts, wallet_interface/ui/src/models/abby.ts, wallet_interface/ui/src/app/components/AppRouter.tsx, wallet_interface/ui/src/app/config/navigation.ts, wallet_interface/ui/tests/voice-workflows-adoption.spec.ts
- Validation: npm --prefix wallet_interface/ui test -- tests/voice-workflows-adoption.spec.ts
- Board namespace: voice-care-workflow-dag-v1
- Bundle: voice-care/integration
- Parallel lane: wave-12-portal-adoption
- Resource class: browser-large
- Predicted files: wallet_interface/ui/src/features/voice-workflows/index.ts, wallet_interface/ui/src/models/abby.ts, wallet_interface/ui/src/app/components/AppRouter.tsx, wallet_interface/ui/src/app/config/navigation.ts, wallet_interface/ui/tests/voice-workflows-adoption.spec.ts
- Conflict policy: Serial integration owner for feature exports, route typing, navigation, and the application router; client and operator leaf tasks may not edit these shared files.
- Symbolic first: true
- LLM context budget bytes: 32768
- Acceptance: Customer and authorized operator views are reachable through the current typed hash router and navigation model; route authorization and profile-driven labels are preserved on direct load, reload, and back navigation; no 211-specific label or action is added to the generic feature; legacy routes remain compatible; and the adoption test exercises the registered API client, client workflow, operator queue, consent, unknown-outcome, and handoff states.
