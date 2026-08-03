# VOICE-CARE-AUTO-003 Objective Goal Gap

Date: 2026-08-03
Fingerprint: 95b1a1fbffec02f8d02c7b4ba2e84563a843be2e
Goal id: VOICE-CARE-G003
Goal title: Generalize the conversation and action DAG schema
Objective heap: docs/planning/VOICE_CUSTOMER_CARE_OBJECTIVE_HEAP.md
Priority: P0
Track: domain-data
Status: todo
Schedulable: true
Review only: false
Parent goals: VOICE-CARE-G001
Graph depth: 1
Objective heap index: 2
Bundle: voice-care/graph-schema
Parallel lane: voice-care-data
Bundle strategy: explicit
Goal packet: none
Goal packet role: none
Goal packet goals: none
Goal packet task count: 0
Goal packet work item count: 0
Evidence methods: embedding
Embedding query: generic conversation DAG intent evidence response form decision action confirmation handoff terminal guard
AST query: ConversationGraph, ConversationNode, ConversationEdge, GuardExpression, compile_bounded_loop
Conflict policy: retain append-only response-DAG compatibility; guards are data-only and side-effect-free
Predicted files: ipfs_datasets_py/ipfs_datasets_py/conversation/graph.py, ipfs_datasets_py/tests/unit/conversation/test_graph_schema.py, docs/schemas/VOICE_CUSTOMER_CARE_GRAPH.md
AST symbols: ConversationGraph, ConversationNode, ConversationEdge, GuardExpression, compile_bounded_loop
Interfaces: response_dag, slotted response graph, domain pack
Submodules: ipfs_datasets_py
Generated artifacts: none
Allow concurrent with: none
Semantic identity: objective-evidence-obligation/v1/074ff9ad2be12418be9faba0edcb1a4882d9e62cc98fa2ce9b41599fd34c1804
Acceptance subset: guard AST, graph integrity validation
Preconditions: objective goal VOICE-CARE-G003 is schedulable
Effects: satisfy evidence requirement: guard AST, satisfy evidence requirement: graph integrity validation
Evidence subset: guard AST, graph integrity validation
Dependencies: VOICE-CARE-G002
Resource class: cpu-medium
Token class: medium
Estimated tokens: 0
Resources: cpu-medium
Merge fate: objective/VOICE-CARE-G003
Rejection reasons: none (accepted)

## Goal

Replace response-only Abby node assumptions with generic intent, evidence-query, response-frame, form, decision, action-reference, confirmation, handoff, and terminal nodes plus typed deterministic guards.

## Missing Evidence

- guard AST
- graph integrity validation

## Present Evidence

- versioned node and edge schemas: ipfs_datasets_py/docs/crypto_ir/THREAT_MODEL.md (embedding:0.36), ipfs_datasets_py/ipfs_datasets_py/knowledge_graphs/adapters/code_evidence.py (embedding:0.32), ipfs_datasets_py/ipfs_datasets_py/logic/intent_ir/README.md (embedding:0.38)
- bounded-loop expansion: ipfs_accelerate_py/test/api/test_agent_supervisor_contract_repair_packet.py (embedding:0.62)
- migration fixtures for the current slotted response DAG: docs/pregenerated_text_audio_residual_response_batches/batch-00017-offset-000544.json (embedding:0.37), docs/pregenerated_text_audio_residual_response_batches/batch-00095-offset-003040.json (embedding:0.32), docs/pregenerated_text_audio_residual_response_batches/batch-00099-offset-003168.json (embedding:0.33)

## Suggested Handling

Define a generic graph model and lossless compatibility adapter for current voice response artifacts.
