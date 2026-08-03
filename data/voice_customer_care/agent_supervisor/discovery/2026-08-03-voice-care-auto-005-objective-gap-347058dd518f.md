# VOICE-CARE-AUTO-005 Objective Goal Gap

Date: 2026-08-03
Fingerprint: 347058dd518f32354b9e5d44370122d8b2ed55bc
Goal id: VOICE-CARE-G006
Goal title: Define typed action lifecycle contracts
Objective heap: docs/planning/VOICE_CUSTOMER_CARE_OBJECTIVE_HEAP.md
Priority: P0
Track: action-runtime
Status: todo
Schedulable: true
Review only: false
Parent goals: VOICE-CARE-G001
Graph depth: 1
Objective heap index: 4
Bundle: voice-care/action-contracts
Parallel lane: voice-care-runtime
Bundle strategy: explicit
Goal packet: none
Goal packet role: none
Goal packet goals: none
Goal packet task count: 0
Goal packet work item count: 0
Evidence methods: embedding
Embedding query: action descriptor proposal decision invocation receipt lifecycle status schema hash redaction
AST query: ActionDescriptor, ActionProposal, ActionDecision, ActionInvocation, ActionReceipt, ActionStatus
Conflict policy: keep contracts transport-neutral and optional-dependency safe; adapters cannot redefine lifecycle semantics
Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/contracts.py, ipfs_accelerate_py/test/test_action_runtime_contracts.py, docs/schemas/VOICE_CUSTOMER_CARE_ACTIONS.md
AST symbols: ActionDescriptor, ActionProposal, ActionDecision, ActionInvocation, ActionReceipt, ActionStatus
Interfaces: domain graph action_ref, MCP IDL, workflow, human handoff
Submodules: ipfs_accelerate_py
Generated artifacts: none
Allow concurrent with: none
Semantic identity: objective-evidence-obligation/v1/49cb9e69e2c36f126a1d4ba5ddab29d7665df1c8f4680d977d67ec95f7cfc3f4
Acceptance subset: redaction-safe serialization, invalid transition tests
Preconditions: objective goal VOICE-CARE-G006 is schedulable
Effects: satisfy evidence requirement: redaction-safe serialization, satisfy evidence requirement: invalid transition tests
Evidence subset: redaction-safe serialization, invalid transition tests
Dependencies: VOICE-CARE-G003
Resource class: cpu-medium
Token class: medium
Estimated tokens: 0
Resources: cpu-medium
Merge fate: objective/VOICE-CARE-G006
Rejection reasons: none (accepted)

## Goal

Define dependency-light ActionDescriptor, ActionProposal, ActionDecision, ActionInvocation, ActionReceipt, and normalized lifecycle contracts.

## Missing Evidence

- redaction-safe serialization
- invalid transition tests

## Present Evidence

- strict serializable dataclasses or models: ipfs_accelerate_py/ipfs_accelerate_py/agent_supervisor/admissibility_bridge.py (embedding:0.32), ipfs_accelerate_py/ipfs_accelerate_py/agent_supervisor/proof/formal_verification_provider.py (embedding:0.37), ipfs_accelerate_py/ipfs_accelerate_py/agent_supervisor/self_improvement/supervisor_state_model.py (embedding:0.36)
- status transition table: ipfs_accelerate_py/test/api/test_agent_supervisor_proof_obligation_templates.py (embedding:0.39), ipfs_accelerate_py/test/api/test_agent_supervisor_runtime_contract_obligations.py (embedding:0.30), ipfs_accelerate_py/test/api_monitoring_dashboard.py (embedding:0.30)
- schema and hash identity: docs/adr/WORLD_AID_DUCKDB_STORAGE_ADR.md (embedding:0.35), docs/reports/ABBY_VOICE_EVALUATION.md (embedding:0.34), docs/runbooks/ABBY_VOICE_AUDIO_JOBS.md (embedding:0.34)

## Suggested Handling

Land the shared action vocabulary before implementing any executable adapter.
