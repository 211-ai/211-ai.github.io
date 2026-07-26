# Objective Bundle: abby-voice/router-graphrag-integration

Source todo: data/abby_voice/agent_supervisor/ABBY_VOICE_ROUTER_TODO.md
Purpose: bundle objective-generated tasks so parallel daemons can work one lane at a time.
Conflict policy: keep edits inside this bundle when possible; use the LLM merge resolver for semantic conflicts.

## ABBY-VOICE-AUTO-007 Implement Abby voice objective: Integrate GraphRAG templating into voice_router

- Status: completed
- Completion: manual
- Priority: P0
- Track: voice-graphrag
- Depends on:
- Outputs: data/abby_voice/agent_supervisor/discovery, docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md, ipfs_accelerate_py/ipfs_accelerate_py/voice_router.py, ipfs_accelerate_py/ipfs_accelerate_py/voice_templates.py, ipfs_accelerate_py/test/test_voice_router_graphrag.py
- Validation: python -m pytest -q ipfs_accelerate_py/test/test_voice_router_graphrag.py
- Bundle: abby-voice/router-graphrag-integration
- Bundle shard: data/abby_voice/agent_supervisor/objective_bundles/abby-voice-router-graphrag-integration.todo.md
- Bundle strategy: explicit
- Graph parents: ABBY-VOICE-G002, ABBY-VOICE-G003, ABBY-VOICE-G007
- Graph depth: 4
- Parallel lane: abby-voice-graphrag
- Conflict policy: use dependency injection across submodules and avoid mandatory ipfs_datasets_py imports at voice_router import time
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/voice_router.py, ipfs_accelerate_py/ipfs_accelerate_py/voice_templates.py, ipfs_accelerate_py/test/test_voice_router_graphrag.py
- Changed paths:
- AST symbols: process_voice_turn, VoiceTemplateProvider, GraphRAGVoiceTemplateProvider, buildVoiceGraphRagPromptParts
- Interfaces: VoiceTemplateProvider, GraphRAGVoiceTemplateProvider, VoiceTurnResult
- Submodules: ipfs_accelerate_py, ipfs_datasets_py
- Generated artifacts:
- Allow concurrent with:
- Goal id: ABBY-VOICE-G008
- Canonical task key: task/v1/17399cd936ebf51296e9d75bc87fe57577ce392ebf8b19a6b3b5c58649ef1867
- Canonical task CID: baguqeerac44zzwjw5p2rffxj25n4q77fov344ojox6frtjvtwxcymsppdbtq
- Missing evidence: objective validation repair
- Embedding query: voice router GraphRAG template provider grounded slot binding spoken normalization provenance
- AST query: process_voice_turn, VoiceTemplateProvider, GraphRAGVoiceTemplateProvider, buildVoiceGraphRagPromptParts
- Surplus group: objective/ABBY-VOICE-G008
- Merge key: 56f4741286457bf7
- Merge family: objective/ABBY-VOICE-G008
- Merge role: validation_gate
- Work item count: 1
- Work scope: objective_validation_repair
- Goal packet:
- Goal packet role:
- Goal packet goals:
- Goal packet task count: 0
- Goal packet work item count: 0
- Candidate kind: validation_gate
- Todo vector key: 4e3a47ff3fc853a2
- Acceptance: Objective scan filed this gap for ABBY-VOICE-G008. Use evidence in /home/barberb/211-AI/data/abby_voice/agent_supervisor/discovery/2026-07-23-abby-voice-auto-007-objective-gap-3380db9aa1f3.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (objective validation repair), and keep the supervisor-fed backlog aligned with the objective heap.  Refine the objective heap if the gap needs smaller child goals.

## ABBY-VOICE-AUTO-024 Implement Abby voice objective: Integrate GraphRAG templating into voice_router

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: voice-graphrag
- Depends on:
- Outputs: data/abby_voice/agent_supervisor/discovery, docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md, ipfs_accelerate_py/ipfs_accelerate_py/voice_router.py, ipfs_accelerate_py/ipfs_accelerate_py/voice_templates.py, ipfs_accelerate_py/test/test_voice_router_graphrag.py
- Validation: python -m pytest -q ipfs_accelerate_py/test/test_voice_router_graphrag.py
- Bundle: abby-voice/router-graphrag-integration
- Bundle shard: data/abby_voice/agent_supervisor/objective_bundles/abby-voice-router-graphrag-integration.todo.md
- Bundle strategy: explicit
- Graph parents: ABBY-VOICE-G002, ABBY-VOICE-G003, ABBY-VOICE-G007
- Graph depth: 5
- Objective heap index: 10
- Parallel lane: abby-voice-graphrag
- Conflict policy: use dependency injection across submodules and avoid mandatory ipfs_datasets_py imports at voice_router import time
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/voice_router.py, ipfs_accelerate_py/ipfs_accelerate_py/voice_templates.py, ipfs_accelerate_py/test/test_voice_router_graphrag.py
- Changed paths:
- AST symbols: process_voice_turn, VoiceTemplateProvider, GraphRAGVoiceTemplateProvider, buildVoiceGraphRagPromptParts
- Interfaces: VoiceTemplateProvider, GraphRAGVoiceTemplateProvider, VoiceTurnResult
- Submodules: ipfs_accelerate_py, ipfs_datasets_py
- Generated artifacts:
- Allow concurrent with:
- Goal id: ABBY-VOICE-G008
- Canonical task key: task/v1/c0cb602542a6d844d02be02c3d7cd014a1a2ec324aecce7c99f58ca40f3547d2
- Canonical task CID: baguqeeraydfwajkcu3mejubl4awd27gqcsq2f3bsjlwm47ez6wgkidzvi7ja
- Semantic identity: objective-evidence-obligation/v1/804cf855670b89ec99e85a7a94b09b3e76bc168b7a2c967b6a738b8fb81c4e5a
- Acceptance subset: optional VoiceTemplateProvider protocol, grounded slot binding implementation, citation stripping with retained machine provenance, integration tests with fake GraphRAG provider, ABBY-VOICE-G008 completion receipt
- Preconditions: objective goal ABBY-VOICE-G008 is schedulable
- Effects: satisfy evidence requirement: optional VoiceTemplateProvider protocol, satisfy evidence requirement: grounded slot binding implementation, satisfy evidence requirement: citation stripping with retained machine provenance, satisfy evidence requirement: integration tests with fake GraphRAG provider, satisfy evidence requirement: ABBY-VOICE-G008 completion receipt
- Evidence subset: optional VoiceTemplateProvider protocol, grounded slot binding implementation, citation stripping with retained machine provenance, integration tests with fake GraphRAG provider, ABBY-VOICE-G008 completion receipt
- Resource class: cpu-medium
- Token class: medium
- Estimated tokens: 0
- Resources: cpu-medium
- Merge fate: objective/ABBY-VOICE-G008
- Rejection reasons: none (accepted)
- Evidence obligation key: objective-evidence-obligation/v1/804cf855670b89ec99e85a7a94b09b3e76bc168b7a2c967b6a738b8fb81c4e5a
- Missing evidence: optional VoiceTemplateProvider protocol, grounded slot binding implementation, citation stripping with retained machine provenance, integration tests with fake GraphRAG provider, ABBY-VOICE-G008 completion receipt
- Embedding query: voice router GraphRAG template provider grounded slot binding spoken normalization provenance
- AST query: process_voice_turn, VoiceTemplateProvider, GraphRAGVoiceTemplateProvider, buildVoiceGraphRagPromptParts
- Surplus group: objective/ABBY-VOICE-G008
- Merge key: b3b151b0023c14fc
- Merge family: objective/ABBY-VOICE-G008
- Merge role: aggregate
- Work item count: 5
- Work scope: goal_subgoal_multi_evidence_batch
- Goal packet:
- Goal packet role:
- Goal packet goals:
- Goal packet task count: 0
- Goal packet work item count: 0
- Completion goal bindings: {}
- Completion task bindings:
- Candidate kind: aggregate
- Todo vector key: 92143df12490398b
- Acceptance: Objective scan filed this gap for ABBY-VOICE-G008. Use evidence in /home/barberb/211-AI/.worktrees/abby-voice-objective-control-v10/data/abby_voice/agent_supervisor/discovery/2026-07-26-abby-voice-auto-024-objective-gap-0cb0505c898e.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (optional VoiceTemplateProvider protocol, grounded slot binding implementation, citation stripping with retained machine provenance, integration tests with fake GraphRAG provider, ABBY-VOICE-G008 completion receipt), and keep the supervisor-fed backlog aligned with the objective heap.  Refine the objective heap if the gap needs smaller child goals.
