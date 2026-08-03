# VOICE-CARE-AUTO-008 Objective Goal Gap

Date: 2026-08-03
Fingerprint: d420f333e08cadb345170b0f481ec65aa3dfef70
Goal id: VOICE-CARE-G009
Goal title: Add content-addressed idempotent execution receipts and replay
Objective heap: docs/planning/VOICE_CUSTOMER_CARE_OBJECTIVE_HEAP.md
Priority: P0
Track: action-runtime
Status: todo
Schedulable: true
Review only: false
Parent goals: VOICE-CARE-G001
Graph depth: 1
Objective heap index: 8
Bundle: voice-care/action-execution
Parallel lane: voice-care-runtime
Bundle strategy: explicit
Goal packet: none
Goal packet role: none
Goal packet goals: none
Goal packet task count: 0
Goal packet work item count: 0
Evidence methods: embedding, exact
Embedding query: content addressed action execution idempotency receipt replay retry compensation event DAG crash recovery
AST query: ActionExecutor, ActionReceiptStore, IdempotencyRecord, execute_action, replay_action
Conflict policy: never retry an unknown or non-idempotent external side effect automatically; storage adapters remain optional
Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/executor.py, ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/receipts.py, ipfs_accelerate_py/test/test_action_execution.py
AST symbols: ActionExecutor, ActionReceiptStore, IdempotencyRecord, execute_action, replay_action
Interfaces: MCP++ CID artifacts, event DAG, ipfs_kit storage adapter
Submodules: ipfs_accelerate_py, ipfs_kit_py
Generated artifacts: none
Allow concurrent with: none
Semantic identity: objective-evidence-obligation/v1/872e05e09ae2d17b712ef45b3922e4b4118f9fe08cb2ef17ae842e3b35285199
Acceptance subset: crash/retry/replay tests
Preconditions: objective goal VOICE-CARE-G009 is schedulable
Effects: satisfy evidence requirement: crash/retry/replay tests
Evidence subset: crash/retry/replay tests
Dependencies: VOICE-CARE-G006, VOICE-CARE-G008
Resource class: cpu-medium
Token class: medium
Estimated tokens: 0
Resources: cpu-medium
Merge fate: objective/VOICE-CARE-G009
Rejection reasons: none (accepted)

## Goal

Execute admitted actions through a durable state machine with content-derived idempotency, bounded retry, cancellation, compensation, event-DAG lineage, and privacy-safe receipts.

## Missing Evidence

- crash/retry/replay tests

## Present Evidence

- execution coordinator: ipfs_accelerate_py/docs/architecture/AGENT_SUPERVISOR_ARCHITECTURE.md (exact), ipfs_accelerate_py/test/api/test_agent_supervisor_distributed_lanes.py (embedding:0.30), ipfs_accelerate_py/test/api/test_agent_supervisor_provider_execution.py (embedding:0.32)
- receipt CAS: ipfs_datasets_py/benchmarks/semantic_roundtrip/holdout_candidate_freeze.py (exact), ipfs_datasets_py/benchmarks/semantic_roundtrip/selective_repair.py (exact), ipfs_datasets_py/ipfs_datasets_py/logic/software_contracts/cache.py (exact)
- idempotency store: ipfs_accelerate_py/ipfs_accelerate_py/endpoint_usage/coordinator.py (embedding:0.45), ipfs_datasets_py/benchmarks/knowledge_graphs/surfaces.py (embedding:0.30), ipfs_datasets_py/docs/archive/reorganization/MASTER_IMPROVEMENT_PLAN_2026_v15.md (embedding:0.40)
- compensation and unknown-outcome behavior: ipfs_accelerate_py/docs/architecture/AGENT_SUPERVISOR_PROOF_DIRECTED_RUNTIME_REVIEW.md (embedding:0.47), ipfs_accelerate_py/docs/architecture/agent_supervisor_code_claim_evidence_contract.md (embedding:0.33), ipfs_accelerate_py/docs/benchmarks/agent_supervisor_codebase_proof_evaluation.md (embedding:0.38)

## Suggested Handling

Build durable invocation semantics once so adapters cannot invent inconsistent retry or completion behavior.
