# VOICE-CARE-AUTO-006 Objective Goal Gap

Date: 2026-08-03
Fingerprint: 077c239e1e93b70e806b3fe77c158c748eb5dc03
Goal id: VOICE-CARE-G005
Goal title: Generalize GraphRAG retrieval into grounded response and action proposals
Objective heap: docs/planning/VOICE_CUSTOMER_CARE_OBJECTIVE_HEAP.md
Priority: P0
Track: retrieval
Status: todo
Schedulable: true
Review only: false
Parent goals: VOICE-CARE-G001
Graph depth: 1
Objective heap index: 5
Bundle: voice-care/retrieval
Parallel lane: voice-care-retrieval
Bundle strategy: explicit
Goal packet: none
Goal packet role: none
Goal packet goals: none
Goal packet task count: 0
Goal packet work item count: 0
Evidence methods: embedding
Embedding query: GraphRAG grounded response action proposal evidence argument provenance confidence non execution
AST query: ConversationPlanProvider, GroundedResponseCandidate, ActionProposalCandidate, retrieve_conversation_plan
Conflict policy: retrieved content can rank registered action references but cannot create descriptors, authority, commands, imports, endpoints, or credentials
Predicted files: ipfs_datasets_py/ipfs_datasets_py/conversation/retrieval.py, ipfs_datasets_py/tests/unit/conversation/test_retrieval.py, ipfs_accelerate_py/test/test_conversation_retrieval_adapter.py
AST symbols: ConversationPlanProvider, GroundedResponseCandidate, ActionProposalCandidate, retrieve_conversation_plan
Interfaces: SlottedResponseIndex, GraphRAGVoiceTemplateProvider, domain pack, action proposal
Submodules: ipfs_datasets_py, ipfs_accelerate_py
Generated artifacts: none
Allow concurrent with: none
Semantic identity: objective-evidence-obligation/v1/f3939f24d943d7ec627c29546dd4e273a7c3f57cddda3406a4a28c8699641c13
Acceptance subset: generic retrieval protocol, action proposal candidates, Abby adapter compatibility
Preconditions: objective goal VOICE-CARE-G005 is schedulable
Effects: satisfy evidence requirement: generic retrieval protocol, satisfy evidence requirement: action proposal candidates, satisfy evidence requirement: Abby adapter compatibility
Evidence subset: generic retrieval protocol, action proposal candidates, Abby adapter compatibility
Dependencies: VOICE-CARE-G003, VOICE-CARE-G004
Resource class: cpu-medium
Token class: medium
Estimated tokens: 0
Resources: cpu-medium
Merge fate: objective/VOICE-CARE-G005
Rejection reasons: none (accepted)

## Goal

Retrieve grounded response plans and ranked action references from a selected domain pack while preserving evidence, argument provenance, confidence, missing slots, and a strict non-execution boundary.

## Missing Evidence

- generic retrieval protocol
- action proposal candidates
- Abby adapter compatibility

## Present Evidence

- deterministic local index: ipfs_datasets_py/benchmarks/semantic_roundtrip/plateau_leanstral_proposals.py (embedding:0.35), ipfs_datasets_py/ipfs_datasets_py/logic/intent_ir/README.md (embedding:0.31), ipfs_datasets_py/ipfs_datasets_py/logic/intent_ir/graphrag/skillcenter_graphrag.py (embedding:0.39)
- optional injected GraphRAG adapters: ARCHITECTURE.md (embedding:0.31), ipfs_accelerate_py/ipfs_accelerate_py/agent_supervisor/control/symbolic_assurance_rollout.py (embedding:0.38), ipfs_accelerate_py/ipfs_accelerate_py/agent_supervisor/program_graph.py (embedding:0.34)
- prompt-injection fixtures: ipfs_accelerate_py/test/api/test_agent_supervisor_prompt_workflow_adversarial.py (embedding:0.36), ipfs_datasets_py/tests/unit/logic/intent_ir/source_adapters/test_prompt_mcp.py (embedding:0.41)

## Suggested Handling

Extract the reusable retrieval kernel from Abby naming and add typed action-candidate output.
