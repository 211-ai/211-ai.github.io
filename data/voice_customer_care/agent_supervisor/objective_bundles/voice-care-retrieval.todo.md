# Objective Bundle: voice-care/retrieval

Source todo: data/voice_customer_care/agent_supervisor/VOICE_CUSTOMER_CARE_TODO.md
Purpose: bundle objective-generated tasks so parallel daemons can work one lane at a time.
Conflict policy: keep edits inside this bundle when possible; use the LLM merge resolver for semantic conflicts.

## VOICE-CARE-AUTO-006 Implement reusable voice customer-care objective: Generalize GraphRAG retrieval into grounded response and action proposals

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: retrieval
- Depends on: VOICE-CARE-AUTO-003, VOICE-CARE-AUTO-004
- Outputs: ipfs_datasets_py/ipfs_datasets_py/conversation/retrieval.py, ipfs_datasets_py/tests/unit/conversation/test_retrieval.py, ipfs_accelerate_py/test/test_conversation_retrieval_adapter.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/conversation/test_retrieval.py ipfs_accelerate_py/test/test_conversation_retrieval_adapter.py
- Board namespace: VOICE_CUSTOMER_CARE_TODO.md
- Evidence inputs: data/voice_customer_care/agent_supervisor/discovery
- Discovery evidence: /home/barberb/211-AI/211-AI/data/voice_customer_care/agent_supervisor/discovery/2026-08-03-voice-care-auto-006-objective-gap-077c239e1e93.md
- Bundle: voice-care/retrieval
- Bundle shard: data/voice_customer_care/agent_supervisor/objective_bundles/voice-care-retrieval.todo.md
- Bundle strategy: explicit
- Graph parents: VOICE-CARE-G001
- Graph depth: 1
- Objective heap index: 5
- Parallel lane: voice-care-retrieval
- Conflict policy: retrieved content can rank registered action references but cannot create descriptors, authority, commands, imports, endpoints, or credentials
- Predicted files: ipfs_datasets_py/ipfs_datasets_py/conversation/retrieval.py, ipfs_datasets_py/tests/unit/conversation/test_retrieval.py, ipfs_accelerate_py/test/test_conversation_retrieval_adapter.py
- Changed paths:
- Context paths: ipfs_datasets_py/ipfs_datasets_py/conversation/retrieval.py, ipfs_datasets_py/tests/unit/conversation/test_retrieval.py, ipfs_accelerate_py/test/test_conversation_retrieval_adapter.py
- AST symbols: ConversationPlanProvider, GroundedResponseCandidate, ActionProposalCandidate, retrieve_conversation_plan
- Interfaces: SlottedResponseIndex, GraphRAGVoiceTemplateProvider, domain pack, action proposal
- Submodules: ipfs_datasets_py, ipfs_accelerate_py
- Generated artifacts:
- Allow concurrent with:
- Goal id: VOICE-CARE-G005
- Completion authority: local
- External authority blockers:
- Canonical task key: task/v1/6bc0e07579368f6749cfa639beff8bfd26f62252c670d3c57a6aa1bbdabdfeef
- Canonical task CID: baguqeeranpaoa5lzg2hwosopuy43574l7utpmissyzynhrl2nkq3xwv573xq
- Semantic identity: objective-evidence-obligation/v1/f3939f24d943d7ec627c29546dd4e273a7c3f57cddda3406a4a28c8699641c13
- Acceptance subset: generic retrieval protocol, action proposal candidates, Abby adapter compatibility
- Preconditions: objective goal VOICE-CARE-G005 is schedulable
- Effects: satisfy evidence requirement: generic retrieval protocol, satisfy evidence requirement: action proposal candidates, satisfy evidence requirement: Abby adapter compatibility
- Evidence subset: generic retrieval protocol, action proposal candidates, Abby adapter compatibility
- Resource class: cpu-medium
- Token class: medium
- Estimated tokens: 0
- Context budget tokens: 4096
- Provider role: grok, codex-review
- Resources: cpu-medium
- Merge fate: objective/VOICE-CARE-G005
- Rejection reasons: none (accepted)
- Evidence obligation key: objective-evidence-obligation/v1/f3939f24d943d7ec627c29546dd4e273a7c3f57cddda3406a4a28c8699641c13
- Missing evidence: generic retrieval protocol, action proposal candidates, Abby adapter compatibility
- Embedding query: GraphRAG grounded response action proposal evidence argument provenance confidence non execution
- AST query: ConversationPlanProvider, GroundedResponseCandidate, ActionProposalCandidate, retrieve_conversation_plan
- Surplus group: objective/VOICE-CARE-G005
- Merge key: 87d2932fdc342d95
- Merge family: objective/VOICE-CARE-G005
- Merge role: aggregate
- Work item count: 3
- Work scope: goal_subgoal_multi_evidence_batch
- Goal packet:
- Goal packet role:
- Goal packet goals:
- Goal packet task count: 0
- Goal packet work item count: 0
- Completion goal bindings: {}
- Completion task bindings:
- Candidate kind: aggregate
- Todo vector key: 7ebe40792bd11681
- Acceptance: Objective scan filed this gap for VOICE-CARE-G005. Use evidence in /home/barberb/211-AI/211-AI/data/voice_customer_care/agent_supervisor/discovery/2026-08-03-voice-care-auto-006-objective-gap-077c239e1e93.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (generic retrieval protocol, action proposal candidates, Abby adapter compatibility), and keep the supervisor-fed backlog aligned with the objective heap.  Refine the objective heap if the gap needs smaller child goals.
