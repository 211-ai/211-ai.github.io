# Reusable Voice Workflow DAG Client Care Objective Heap

This is the durable intent heap for turning the existing voice response DAG and
GraphRAG implementation into a reusable, multi-tenant client-intake and
customer-care framework. The companion task board is an executable projection;
task completion alone never completes an objective. Objective completion
requires fresh, content-bound evidence for the exact profile, workflow,
adapters, policy, runtime, and acceptance criterion under review.

The response DAG remains a grounded-content plane. Executable authority belongs
to a separate, operator-controlled workflow plane. Retrieval, callers, models,
and public profile data may propose logical capabilities, but they cannot
invent executable locators, increase authority, or bypass policy, confirmation,
lease, isolation, and audit gates.

## VOICE-CARE-G000 Deliver a reusable voice workflow DAG for client intake and customer care

- Status: active
- Parent:
- Fib priority: 1
- Track: voice-care-program
- Priority: P0
- Bundle: voice-care/root
- Goal: Deliver a profile-driven framework that can ground conversations in GraphRAG evidence, collect and validate intake data, propose and execute governed workflows through typed adapters, transfer safely to people, and operate across portal and telephone channels without coupling the core to 211-AI.
- Evidence: voice-care/program-release-root@1, voice-care/two-profile-conformance@1, voice-care/production-readiness@1
- Outputs: docs/planning/REUSABLE_VOICE_WORKFLOW_DAG_CLIENT_CARE_PLAN.md, docs/planning/reusable_voice_workflow_dag_client_care.objectives.md, docs/planning/reusable_voice_workflow_dag_client_care.todo.md, docs/planning/reusable_voice_workflow_dag_client_care.supervisor.json, scripts/validate_voice_workflow_dag_client_care_plan.py
- Validation: python scripts/validate_voice_workflow_dag_client_care_plan.py
- Acceptance: Every direct child has criterion-level evidence bound to an immutable release manifest; the 211-AI and unrelated reference profiles run without core forks; no retrieved or generated content can grant executable authority; mutating actions and human transfers are policy governed, recoverable, observable, and independently auditable.
- Gap task: Refill the highest-priority uncovered child criterion with one bounded task and an explicit evidence contract.
- Refinement: Preserve independent lanes for contracts, content identity, retrieval, admission, orchestration, adapters, conversations, channels, assurance, profiles, verification, and rollout.
- Embedding query: reusable voice workflow DAG GraphRAG client intake customer care profile adapters human handoff telephony
- AST query: GraphRAGVoiceTemplateProvider VoiceTurnRequest VoiceResponsePlan process_voice_turn process_telephone_turn

## VOICE-CARE-G010 Establish the framework doctrine and canonical contracts

- Status: active
- Parent: VOICE-CARE-G000
- Fib priority: 2
- Track: architecture-contracts
- Priority: P0
- Bundle: voice-care/foundation
- Goal: Define the trust boundaries, package ownership, compatibility policy, typed records, lifecycle states, node vocabulary, edge vocabulary, error taxonomy, conformance rules, and deterministic compiler for content, workflow, action, handoff, tenant, and session behavior.
- Evidence: voice-care/architecture-decision-record@1, voice-care/canonical-contract-catalog@1, voice-care/trust-boundary-review@1, voice-care/workflow-compiler-receipt@1
- Outputs: docs/voice_workflows/REFERENCE_ARCHITECTURE.md, docs/voice_workflows/TRUST_PRIVACY_AND_PROOF_MODEL.md, ipfs_datasets_py/ipfs_datasets_py/voice_workflows/records.py, ipfs_datasets_py/ipfs_datasets_py/voice_workflows/compiler.py, ipfs_datasets_py/ipfs_datasets_py/voice_workflows/predicates.py
- Validation: python -m pytest -q tests/voice_workflows/test_architecture_boundaries.py ipfs_datasets_py/tests/unit/voice_workflows/test_records.py ipfs_datasets_py/tests/unit/voice_workflows/test_compiler.py
- Acceptance: Contracts distinguish public content, operator-signed authority, and private session state; the supported node and edge vocabularies are closed and versioned; proposed, authorized, leased, executing, terminal, outcome-unknown, compensation, and escalation states have deterministic transition rules; compilation is deterministic; unknown references, unreachable nodes, unbounded cycles, missing terminal paths, unsafe retries, and incompatible migrations fail closed; backward compatibility with current Abby voice records is explicit.
- Gap task: Add the smallest missing contract, invariant, compiler check, migration, compatibility mapping, or typed error.
- Refinement: Keep semantic records independent from runtime adapters and provider-specific locators and emit source-bound diagnostics suitable for small repair contexts.
- Embedding query: voice workflow architecture trust boundary canonical contract state machine node edge taxonomy
- AST query: GraphNode GraphEdge TemplateGraphSnapshot VoiceResponsePlan VoiceTurnResult

## VOICE-CARE-G020 Make profiles and runtime artifacts content addressed and safely swappable

- Status: active
- Parent: VOICE-CARE-G000
- Fib priority: 3
- Track: content-identity
- Priority: P0
- Bundle: voice-care/content-identity
- Goal: Define canonical multiformats identities and signed manifests for public content packs, operator-controlled workflow and policy packs, private state references, adapter registries, and complete deployments.
- Evidence: voice-care/domain-profile-manifest@1, voice-care/profile-signature-verification@1, voice-care/profile-activation-receipt@1
- Outputs: ipfs_datasets_py/ipfs_datasets_py/voice_workflows/content_addressing.py, ipfs_datasets_py/ipfs_datasets_py/voice_workflows/profile.py, ipfs_datasets_py/ipfs_datasets_py/voice_workflows/release.py, ipfs_datasets_py/ipfs_datasets_py/voice_workflows/namespaces.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/voice_workflows/test_content_addressing.py ipfs_datasets_py/tests/unit/voice_workflows/test_profile_lifecycle.py ipfs_datasets_py/tests/unit/voice_workflows/test_namespace_isolation.py
- Acceptance: All authority-relevant dimensions affect the deployment CID; public packs contain no credentials or executable locators; private records are never placed in public indexes; signatures, compatibility, tenant binding, activation, rollback, cache invalidation, and missing-pack behavior fail closed with typed evidence.
- Gap task: Repair one canonicalization, signature, isolation, activation, rollback, or invalidation invariant.
- Refinement: Keep immutable pack identity separate from mutable tenant aliases and deployment status.
- Embedding query: domain profile CID multiformats multihash signed manifest activation rollback tenant cache
- AST query: cid_for_dag_json validate_cid ResponseDAGAppendCandidate SlottedResponseIndex

## VOICE-CARE-G030 Extend GraphRAG from grounded responses to bounded action proposals

- Status: active
- Parent: VOICE-CARE-G000
- Fib priority: 5
- Track: graphrag-routing
- Priority: P0
- Bundle: voice-care/retrieval
- Goal: Project profile content, workflow nodes, slots, capabilities, citations, and handoff options into a deterministic evidence graph that retrieves compact response and action candidates without acquiring execution authority.
- Evidence: voice-care/action-graphrag-snapshot@1, voice-care/retrieval-provenance@1, voice-care/authority-noninterference@1
- Outputs: ipfs_datasets_py/ipfs_datasets_py/voice_workflows/graphrag.py, ipfs_datasets_py/ipfs_datasets_py/voice_workflows/retrieval.py, ipfs_datasets_py/ipfs_datasets_py/voice_workflows/grounding.py, ipfs_datasets_py/ipfs_datasets_py/voice_workflows/guards.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/voice_workflows/test_action_graph.py ipfs_datasets_py/tests/unit/voice_workflows/test_action_retrieval.py ipfs_datasets_py/tests/unit/voice_workflows/test_grounding.py ipfs_datasets_py/tests/security/voice_workflows/test_retrieval_injection.py
- Acceptance: Retrieval returns only profile-declared logical capabilities, required slots, citations, ranking reasons, and bounded continuation handles; profile, locale, channel, tenant, and policy scopes are enforced; truncation and ambiguity are explicit; prompt or indexed-data injection cannot introduce adapter names, commands, endpoints, imports, or broader privileges.
- Gap task: Add one missing graph relation, bounded query, provenance field, or authority-noninterference test.
- Refinement: Preserve deterministic symbolic routing as the default and make embedding or model ranking optional and non-authoritative.
- Embedding query: GraphRAG voice action proposal capability retrieval evidence provenance bounded symbolic routing
- AST query: GraphRAGVoiceTemplateProvider TemplateMatch query_terms rerank_candidates

## VOICE-CARE-G040 Admit actions only through a fail-closed authority gateway

- Status: active
- Parent: VOICE-CARE-G000
- Fib priority: 5
- Track: action-admission
- Priority: P0
- Bundle: voice-care/authority
- Goal: Convert proposals into authorized invocation intents only after schema, tenant, capability, policy, consent, confirmation, authentication, quota, delegation, and freshness checks.
- Evidence: voice-care/action-admission-decision@1, voice-care/consent-receipt@1, voice-care/confused-deputy-test@1
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/policy.py, ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/controls.py, docs/voice_workflows/POLICY_GATEWAY.md, docs/voice_workflows/EMERGENCY_CONTROLS.md
- Validation: python -m pytest -q ipfs_accelerate_py/test/api/voice_workflows/test_voice_workflow_policy.py ipfs_accelerate_py/test/api/voice_workflows/test_voice_workflow_controls.py
- Acceptance: Missing or stale policy, consent, delegation, tenant binding, schema, confirmation, step-up authentication, or quota denies mutation; authorization is rechecked after lease acquisition; retrieval and model output cannot broaden scopes; decision receipts explain allow or deny without exposing secrets.
- Gap task: Add the highest-risk missing admission predicate or adversarial denial test.
- Refinement: Separate standing consent, per-action confirmation, operator delegation, and emergency escalation policy.
- Embedding query: action admission policy consent confirmation authorization tenant quota delegation confused deputy
- AST query: AgentToolPermissionPolicy AgentConfirmationRequest AgentToolExecutorValidationResult SupervisorControlService

## VOICE-CARE-G050 Execute workflows with durable, idempotent, recoverable orchestration

- Status: active
- Parent: VOICE-CARE-G000
- Fib priority: 8
- Track: orchestration-runtime
- Priority: P0
- Bundle: voice-care/runtime
- Goal: Implement the workflow interpreter and action state machine with durable state, outbox delivery, leases, fencing, idempotency, retries, cancellation, deadlines, compensation, reconciliation, and explicit unknown outcomes.
- Evidence: voice-care/workflow-execution-trace@1, voice-care/idempotency-conformance@1, voice-care/recovery-replay@1
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/contracts.py, ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/engine.py, ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/state.py, ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/outbox.py, ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/recovery.py
- Validation: python -m pytest -q ipfs_accelerate_py/test/api/voice_workflows/test_voice_workflow_engine.py ipfs_accelerate_py/test/api/voice_workflows/test_voice_workflow_durability.py ipfs_accelerate_py/test/api/voice_workflows/test_voice_workflow_recovery.py
- Acceptance: The runtime never claims exactly-once delivery for arbitrary providers; an idempotency key is bound to canonical intent and rejects payload substitution; leases are fenced; crashes replay safely; dispatch-attempt observations are immutable; at most one conclusive workflow result is admitted; timeout or ambiguous provider state becomes a durable non-conclusive `outcome_unknown` hold until a provider-bound reconciliation receipt resolves or escalates it; cancellation and compensation are separately authorized and cannot erase the unknown external effect.
- Gap task: Add one missing transition, crash boundary, replay, fencing, compensation, or reconciliation case.
- Refinement: Keep pure graph evaluation separate from durable effects and provider delivery.
- Embedding query: durable workflow orchestration outbox lease fencing idempotency retry compensation outcome unknown
- AST query: AgentToolExecutor process_voice_turn process_telephone_turn append_response_dag_candidate

## VOICE-CARE-G060 Define a capability adapter SDK with uniform conformance

- Status: active
- Parent: VOICE-CARE-G000
- Fib priority: 8
- Track: action-adapters
- Priority: P0
- Bundle: voice-care/adapters
- Goal: Define a typed adapter protocol and registry for capability discovery, input and output validation, health, authorization context, deadlines, cancellation, idempotency, receipts, redaction, reconciliation, and conformance testing.
- Evidence: voice-care/adapter-contract@1, voice-care/adapter-conformance-suite@1, voice-care/capability-registry-snapshot@1
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/adapters/base.py, ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/adapters/registry.py, ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/adapters/conformance.py
- Validation: python -m pytest -q ipfs_accelerate_py/test/api/voice_workflows/test_voice_adapter_registry.py ipfs_accelerate_py/test/api/voice_workflows/adapter_contract
- Acceptance: Profiles reference logical capabilities rather than executable locators; adapters cannot self-register beyond operator policy; every invocation and result is schema checked and tenant bound; secret fields are opaque and redacted; unsupported cancellation, idempotency, compensation, or reconciliation is declared rather than inferred.
- Gap task: Add one missing adapter contract field, registry invariant, or shared conformance case.
- Refinement: Make adapter implementations replaceable without changing graph semantics or profile content.
- Embedding query: capability adapter SDK registry typed schema deadline cancellation idempotency receipt redaction
- AST query: AgentToolDefinition ToolRegistry AgentToolResult ServiceActionDescriptor

## VOICE-CARE-G061 Integrate MCP++, MCP, CLI, Python, and HTTP capabilities safely

- Status: active
- Parent: VOICE-CARE-G060
- Fib priority: 13
- Track: action-adapters
- Priority: P0
- Bundle: voice-care/adapters
- Goal: Implement provider adapters for MCP++, conventional MCP, fixed-argument CLI programs, injected Python callables, and registered HTTP or webhook operations under the common capability contract.
- Evidence: voice-care/mcplusplus-adapter-witness@1, voice-care/mcp-adapter-witness@1, voice-care/local-adapter-witness@1, voice-care/http-adapter-witness@1
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/adapters/mcplusplus.py, ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/adapters/mcp.py, ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/adapters/cli.py, ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/adapters/python_callable.py, ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/adapters/http.py
- Validation: python -m pytest -q ipfs_accelerate_py/test/api/voice_workflows/adapter_contract/test_mcplusplus_adapter.py ipfs_accelerate_py/test/api/voice_workflows/adapter_contract/test_mcp_adapter.py ipfs_accelerate_py/test/api/voice_workflows/adapter_contract/test_cli_adapter.py ipfs_accelerate_py/test/api/voice_workflows/adapter_contract/test_python_callable_adapter.py ipfs_accelerate_py/test/api/voice_workflows/adapter_contract/test_http_adapter.py
- Acceptance: MCP handshakes and tool schemas are verified; CLI invocation uses a fixed executable and argv without a shell; Python callables are injected from an allowlisted registry rather than imported from profile strings; HTTP targets are registered and protected from SSRF and redirect escapes; every adapter passes shared timeout, cancellation, redaction, replay, and error-mapping fixtures.
- Gap task: Implement or harden one adapter behind the shared conformance suite.
- Refinement: Split provider implementations by files and tests while preserving one registry and receipt schema.
- Embedding query: MCP++ MCP CLI Python callable HTTP webhook secure adapter SSRF command injection
- AST query: TrioMCPClient call_tool list_tools ToolRegistry create_subprocess_exec

## VOICE-CARE-G062 Expose a narrow agent-supervisor capability without granting repository control

- Status: active
- Parent: VOICE-CARE-G060
- Fib priority: 13
- Track: supervisor-integration
- Priority: P0
- Bundle: voice-care/adapters
- Goal: Permit approved intake or operator workflows to query, propose, enqueue, and monitor bounded ipfs_accelerate_py agent-supervisor operations without voice-triggered arbitrary code execution, repository expansion, merge, push, or completion authority.
- Evidence: voice-care/supervisor-delegation@1, voice-care/supervisor-adapter-receipt@1, voice-care/supervisor-authority-negative-suite@1
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/adapters/supervisor.py, ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/adapters/supervisor_mutations.py, docs/voice_workflows/SUPERVISOR_DELEGATION_POLICY.md
- Validation: python -m pytest -q ipfs_accelerate_py/test/api/voice_workflows/adapter_contract/test_supervisor_inspection.py ipfs_accelerate_py/test/api/voice_workflows/adapter_contract/test_supervisor_mutations.py
- Acceptance: Mutating operations require an operator-signed delegation, validated goal and task plan, explicit repository and path bounds, quotas, isolated worktrees, and confirmation; raw commands, prompt-supplied paths, write-root expansion, direct merge, direct push, false completion, or resource escalation are denied; read-only status remains separately scoped.
- Gap task: Add one missing supervisor operation contract or privilege-escalation denial fixture.
- Refinement: Start with status and bounded task proposal, then admit mutation operations only after independent authorization review.
- Embedding query: agent supervisor voice capability delegation goals tasks isolated worktree deny merge push
- AST query: implementation_supervisor_entry SupervisorControlService parse_goal_heap parse_task_file

## VOICE-CARE-G070 Support resumable, privacy-aware multi-turn intake

- Status: active
- Parent: VOICE-CARE-G000
- Fib priority: 13
- Track: conversation-intake
- Priority: P0
- Bundle: voice-care/conversation
- Goal: Generalize the voice router into a channel-neutral dialogue runtime for slot collection, validation, clarification, consent, confirmation, branching, citations, action proposals, and resumable sessions.
- Evidence: voice-care/intake-session-trace@1, voice-care/cross-channel-resume@1, voice-care/dialogue-safety-report@1
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/router_collaborator.py, ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/dialogue.py, ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/sessions.py, ipfs_accelerate_py/ipfs_accelerate_py/voice_router.py, ipfs_kit_py/ipfs_kit_py/voice_workflow_store.py
- Validation: python -m pytest -q ipfs_accelerate_py/test/api/voice_workflows/test_voice_router_workflow_compatibility.py ipfs_accelerate_py/test/api/voice_workflows/test_voice_workflow_dialogue.py ipfs_accelerate_py/test/api/voice_workflows/test_voice_workflow_sessions.py ipfs_accelerate_py/test/api/voice_workflows/test_package_adoption.py ipfs_kit_py/tests/test_voice_workflow_store.py
- Acceptance: Required slots are collected minimally and validated before use; ambiguity causes clarification rather than guessed facts or actions; consent and confirmation are bound to the action and material parameters; sensitive session state is encrypted, tenant isolated, expirable, exportable, and deletable; web and telephone sessions can resume under verified identity and policy.
- Gap task: Add one missing dialogue transition, slot rule, privacy control, or cross-channel replay case.
- Refinement: Keep transport input and output normalization separate from the deterministic dialogue state machine.
- Embedding query: multi turn client intake slots validation clarification consent confirmation resumable session privacy
- AST query: TelephoneTurnState VoiceTurnRequest VoiceTurnProvenance process_telephone_turn

## VOICE-CARE-G071 Escalate and hand off to people with least-data continuity

- Status: active
- Parent: VOICE-CARE-G070
- Fib priority: 21
- Track: human-handoff
- Priority: P0
- Bundle: voice-care/conversation
- Goal: Model warm transfer, queue routing, callback, case creation, operator context, consent, availability, timeout, and degraded fallback as first-class workflow operations.
- Evidence: voice-care/handoff-envelope@1, voice-care/warm-transfer-trace@1, voice-care/handoff-minimization-proof@1
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/handoff.py, ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/escalation.py, docs/voice_workflows/HUMAN_HANDOFF.md, docs/voice_workflows/SAFE_DEGRADED_MODE.md
- Validation: python -m pytest -q ipfs_accelerate_py/test/api/voice_workflows/test_voice_handoff_contracts.py ipfs_accelerate_py/test/api/voice_workflows/test_voice_escalation_policy.py
- Acceptance: The handoff envelope is limited to the caller grant and destination queue schema; the person receives cited context, completed slots, pending decisions, consent, and safety flags without hidden chain-of-thought or unrelated data; unavailable, rejected, timed-out, and abandoned transfers have explicit callback or safe-return paths.
- Gap task: Add one missing queue, transfer, callback, minimization, or failure-mode contract.
- Refinement: Separate abstract handoff semantics from contact-center and telephony providers.
- Embedding query: human handoff warm transfer queue callback least data context consent customer care
- AST query: ServiceActionDescriptor ServiceInteractionIntent buildServiceInteractionIntent VoiceTurnResult

## VOICE-CARE-G072 Operate reliably across telephone and portal channels

- Status: active
- Parent: VOICE-CARE-G070
- Fib priority: 21
- Track: channel-telephony
- Priority: P0
- Bundle: voice-care/channels
- Goal: Provide channel adapters for telephone media and events plus browser text and voice while preserving one workflow, policy, session, provenance, and action contract.
- Evidence: voice-care/telephony-call-trace@1, voice-care/channel-parity@1, voice-care/degraded-channel-test@1
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/channels/telephony.py, ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/channels/transfer.py, ipfs_accelerate_py/test/api/voice_workflows/test_voice_telephony_handoff.py
- Validation: python -m pytest -q ipfs_accelerate_py/test/api/voice_workflows/test_voice_telephony_handoff.py
- Acceptance: Call identity, consent cues, DTMF or speech input, barge-in, interruption, silence, transfer, hangup, callback, and media failure map to typed events; provider callbacks are authenticated and replay protected; channel limitations never weaken action authorization; accessibility and degraded text or callback paths remain available.
- Gap task: Add one missing channel event, provider boundary, parity check, or degraded-path test.
- Refinement: Keep provider codecs and webhooks outside the channel-neutral session runtime.
- Embedding query: telephony voice portal channel adapter DTMF barge in callback webhook parity
- AST query: process_telephone_turn TelephoneTurnState VoiceStageTrace

## VOICE-CARE-G080 Provide reusable APIs and schema-driven client and operator interfaces

- Status: active
- Parent: VOICE-CARE-G000
- Fib priority: 21
- Track: portal-api-ui
- Priority: P0
- Bundle: voice-care/portal
- Goal: Expose stable APIs and schema-driven UI surfaces for intake, evidence, consent, actions, status, receipts, handoff, case history, profile authoring, activation, and operational control.
- Evidence: voice-care/api-conformance@1, voice-care/client-journey@1, voice-care/operator-journey@1, voice-care/accessibility-audit@1
- Outputs: wallet_interface/routes/voice_workflows.py, wallet_interface/schemas/voice_workflows.py, wallet_interface/api.py, wallet_interface/ui/src/features/voice-workflows, wallet_interface/ui/src/app/components/AppRouter.tsx, wallet_interface/ui/tests/voice-workflows-client.spec.ts, wallet_interface/ui/tests/voice-workflows-operator.spec.ts, wallet_interface/ui/tests/voice-workflows-adoption.spec.ts
- Validation: python -m pytest -q tests/api/test_voice_workflow_api.py wallet_interface/tests/test_voice_workflow_api_adoption.py && npm --prefix wallet_interface/ui test -- tests/voice-workflows-client.spec.ts tests/voice-workflows-operator.spec.ts tests/voice-workflows-adoption.spec.ts
- Acceptance: API schemas match canonical records; the UI shows sources, requested data, action consequences, confirmation, progress, unknown outcomes, retries, cancellation, and human-handoff state; operator controls cannot bypass server authorization; rendering is profile driven, accessible, localizable, responsive, and usable without voice.
- Gap task: Implement one missing API contract, schema-driven surface, accessibility case, or operator authorization guard.
- Refinement: Reuse the existing agent tool, planner, permission, confirmation, and service-action foundations behind server-enforced policy.
- Embedding query: client intake portal customer care API schema driven UI action receipt operator accessibility
- AST query: AgentToolExecutor AgentToolPermissionPolicy ServiceActionDescriptor ServiceInteractionIntent

## VOICE-CARE-G090 Prove critical invariants and continuously test security and privacy

- Status: active
- Parent: VOICE-CARE-G000
- Fib priority: 34
- Track: formal-assurance
- Priority: P0
- Bundle: voice-care/assurance
- Goal: Express supported workflow, authority, tenant, replay, terminal-outcome, evidence, privacy, handoff, and supervisor invariants as machine-checkable constraints with counterexamples, runtime witnesses, and optional qualified zero-knowledge attestations.
- Evidence: voice-care/invariant-proof-root@1, voice-care/security-counterexample-suite@1, voice-care/privacy-erasure-receipt@1, voice-care/zk-shadow-receipt@1
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/receipts.py, ipfs_accelerate_py/ipfs_accelerate_py/voice_workflows/cache.py, ipfs_datasets_py/ipfs_datasets_py/logic/voice_workflows, tests/property/voice_workflows, tests/security/voice_workflows
- Validation: python -m pytest -q ipfs_accelerate_py/test/api/voice_workflows/test_voice_workflow_receipts.py ipfs_accelerate_py/test/api/voice_workflows/test_voice_workflow_cache.py ipfs_datasets_py/tests/unit/logic/voice_workflows tests/property/voice_workflows tests/security/voice_workflows
- Acceptance: Executed actions imply a signed valid profile, authorization, lease, and idempotency binding; mutating actions imply consent or confirmation; tenant equality holds end to end; replay substitution is rejected; terminal-result uniqueness and explicit unknown outcomes hold; system-authored domain, action, eligibility, availability, and status claims cite admitted evidence while caller assertions remain attributed to private session records; private data cannot flow to public artifacts or unapproved shared inference; retrieval cannot increase authority; ZK, if enabled, proves only declared trace commitments and never substitutes for semantic proof or runtime authorization.
- Gap task: Add the highest-risk missing invariant, proof obligation, attack fixture, or privacy lifecycle check.
- Refinement: Prefer symbolic constraints, property tests, and minimal counterexamples before model-assisted diagnosis.
- Embedding query: formal logic voice workflow invariant authorization tenant replay privacy zero knowledge proof
- AST query: ReceiptAttestationStatement ProofReceipt MultiProverRouter ProofScopeIndex VoiceTurnProvenance

## VOICE-CARE-G100 Ship a governed 211-AI client-intake profile

- Status: active
- Parent: VOICE-CARE-G000
- Fib priority: 34
- Track: profile-211
- Priority: P0
- Bundle: voice-care/profiles
- Goal: Encode 211-AI resources, eligibility and safety questions, intake schemas, service-navigation workflows, approved actions, escalation queues, languages, consent text, and operational policy as a signed domain profile rather than core code.
- Evidence: voice-care/211-profile-manifest@1, voice-care/211-scenario-suite@1, voice-care/211-stakeholder-acceptance@1
- Outputs: profiles/voice_workflows/211-ai, scripts/voice_workflows/import_211_abby.py, tests/profiles/test_211_voice_profile.py, tests/e2e/voice_workflows/test_211_client_care.py
- Validation: python -m pytest -q tests/profiles/test_211_voice_profile.py tests/e2e/voice_workflows/test_211_client_care.py
- Acceptance: The profile supports resource navigation, eligibility clarification, contact or referral actions, client intake, callback, warm handoff, safety escalation, multilingual copy, and service provenance; local policy and content can update by signed pack activation without modifying generic runtime modules; stakeholder scenarios pass with least-data collection.
- Gap task: Add one missing 211 content, workflow, policy, locale, handoff, or acceptance scenario.
- Refinement: Keep agency-specific terminology, forms, queues, and actions entirely inside the 211 profile and its registered bindings.
- Embedding query: 211 AI service navigation client intake resource referral eligibility crisis handoff profile
- AST query: GraphRAGVoiceTemplateProvider serviceActionService Resource

## VOICE-CARE-G110 Prove reuse with an unrelated reference profile and authoring kit

- Status: active
- Parent: VOICE-CARE-G000
- Fib priority: 55
- Track: profile-portability
- Priority: P0
- Bundle: voice-care/profiles
- Goal: Provide a profile authoring SDK, CLI, examples, validation reports, migration tools, and a neutral IT-helpdesk reference profile that exercises the framework without 211 concepts or core forks.
- Evidence: voice-care/authoring-sdk-conformance@1, voice-care/it-helpdesk-profile-manifest@1, voice-care/core-unchanged-proof@1
- Outputs: ipfs_datasets_py/ipfs_datasets_py/voice_workflows/authoring.py, scripts/voice_workflows/profile_tool.py, profiles/voice_workflows/it-helpdesk-reference, tests/e2e/voice_workflows/test_profile_swap.py
- Validation: python -m pytest -q tests/voice_workflows/test_profile_authoring.py tests/profiles/test_it_helpdesk_voice_profile.py tests/e2e/voice_workflows/test_profile_swap.py
- Acceptance: An operator can compile, lint, sign, test, activate, roll back, export, and migrate a profile using documented tools; the IT-helpdesk profile supports issue triage, approved diagnostics, ticket creation, status lookup, and human escalation; both reference profiles pass the same conformance suite with no profile-name branches or core source changes.
- Gap task: Remove one hard-coded domain assumption or add one missing authoring and portability fixture.
- Refinement: Treat the second profile as an architectural acceptance gate, not a cosmetic demonstration.
- Embedding query: reusable profile authoring SDK IT helpdesk workflow domain neutral portability no core changes
- AST query: AbbyVoiceResponse GraphRAGVoiceTemplateProvider DomainProfileManifest WorkflowDefinition

## VOICE-CARE-G120 Verify end-to-end behavior, resilience, and operational observability

- Status: active
- Parent: VOICE-CARE-G000
- Fib priority: 55
- Track: verification-observability
- Priority: P0
- Bundle: voice-care/verification
- Goal: Build hermetic conformance, property, fuzz, adversarial, chaos, load, accessibility, cross-channel, and end-to-end tests plus privacy-safe metrics, traces, alerts, and signed release evidence.
- Evidence: voice-care/e2e-conformance-root@1, voice-care/chaos-recovery-report@1, voice-care/operational-slo-report@1, voice-care/release-evidence-bundle@1
- Outputs: tests/e2e/voice_workflows/test_release_matrix.py, scripts/voice_workflows/run_release_gates.py, data/voice_workflows/evaluation/release-report.json
- Validation: python scripts/voice_workflows/run_release_gates.py --check
- Acceptance: Tests cover prompt and tool injection, schema smuggling, command injection, SSRF, replay, confused deputy, cross-tenant access, lease races, crash recovery, provider ambiguity, handoff failure, deletion, and profile rollback; production signals expose latency, denial, unknown outcomes, retries, queue health, abandonment, and adapter health without recording sensitive utterances or secrets by default.
- Gap task: Add the smallest missing high-risk fixture, fault injection, invariant metric, or alert.
- Refinement: Use deterministic fakes for gating and separately label optional live-provider probes as non-authoritative.
- Embedding query: end to end voice workflow property fuzz chaos security observability SLO privacy
- AST query: VoiceStageTrace AgentToolResult ResponseDAGAppendCandidate InteractionReceipt

## VOICE-CARE-G130 Roll out safely and sustain bounded autonomous improvement

- Status: active
- Parent: VOICE-CARE-G000
- Fib priority: 89
- Track: rollout-supervision
- Priority: P0
- Bundle: voice-care/release
- Goal: Define feature flags, shadow and canary stages, kill switches, incident response, data governance, profile approval, adapter certification, supervisor sharding, bounded evidence-driven refill, rollback, and production promotion criteria.
- Evidence: voice-care/rollout-checklist@1, voice-care/canary-report@1, voice-care/refill-audit@1, voice-care/general-availability-approval@1
- Outputs: docs/voice_workflows/OPERATIONS_RUNBOOK.md, docs/voice_workflows/INCIDENT_AND_ROLLBACK.md, scripts/voice_workflows/supervisor_control.py, docs/planning/reusable_voice_workflow_dag_client_care.supervisor.json
- Validation: python scripts/validate_voice_workflow_dag_client_care_plan.py && python scripts/voice_workflows/supervisor_control.py readiness
- Acceptance: Read-only shadow precedes effects; each adapter and profile is independently gated; high-risk actions require explicit canary approval; a global and tenant kill switch denies new mutations while preserving safe status and handoff paths; rollback is rehearsed; one supervisor lane owns refill; generated tasks are bounded by evidence, path, dependency, resource, context, and attempt budgets; promotion requires security, privacy, accessibility, reliability, and stakeholder sign-off.
- Gap task: Create one bounded task for the highest-priority failed release gate or unresolved production risk.
- Refinement: Advance from simulation to internal pilot, limited tenant canary, and general availability only through evidence-bearing gates.
- Embedding query: voice workflow rollout shadow canary kill switch incident supervisor refill release gate
- AST query: implementation_supervisor_entry materialize_task_dependency_dag parse_goal_heap parse_task_file
