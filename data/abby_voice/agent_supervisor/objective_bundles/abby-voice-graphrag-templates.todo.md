# Objective Bundle: abby-voice/graphrag-templates

Source todo: data/abby_voice/agent_supervisor/ABBY_VOICE_ROUTER_TODO.md
Purpose: bundle objective-generated tasks so parallel daemons can work one lane at a time.
Conflict policy: keep edits inside this bundle when possible; use the LLM merge resolver for semantic conflicts.

## ABBY-VOICE-AUTO-006 Implement Abby voice objective: Add GraphRAG response-template ingestion and retrieval

- Status: completed
- Completion: manual
- Priority: P0
- Track: voice-graphrag
- Depends on:
- Outputs: data/abby_voice/agent_supervisor/discovery, docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md, ipfs_datasets_py/ipfs_datasets_py/voice/graphrag.py, ipfs_datasets_py/tests/unit/voice/test_abby_voice_graphrag.py, docs/data/ABBY_VOICE_GRAPHRAG.md
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/voice/test_abby_voice_graphrag.py
- Bundle: abby-voice/graphrag-templates
- Bundle shard: data/abby_voice/agent_supervisor/objective_bundles/abby-voice-graphrag-templates.todo.md
- Bundle strategy: explicit
- Graph parents: ABBY-VOICE-G004, ABBY-VOICE-G005
- Graph depth: 3
- Parallel lane: abby-voice-graphrag
- Conflict policy: retrieved templates are response plans only; factual slots must bind from current cited evidence and never from stale example wording
- Predicted files: ipfs_datasets_py/ipfs_datasets_py/voice/graphrag.py, ipfs_datasets_py/tests/unit/voice/test_abby_voice_graphrag.py, docs/data/ABBY_VOICE_GRAPHRAG.md
- Changed paths:
- AST symbols: IPLDKnowledgeGraph, IPLDVectorStore, GraphRAGLLMProcessor, SlottedResponseIndex
- Interfaces: GraphRAGVoiceTemplateProvider, ipfs_datasets_py vector store, IPLD knowledge graph
- Submodules: ipfs_datasets_py
- Generated artifacts:
- Allow concurrent with:
- Goal id: ABBY-VOICE-G007
- Canonical task key: task/v1/5c4cb26a6051c3fb8ab9522113b4d362c9d79d94df6c27fd877b47bbd45afc75
- Canonical task CID: baguqeeralrgle2takhb7xcvzkiqrhngtmle5phmu35wcp7mhpnd3xvc27r2q
- Missing evidence: objective validation repair
- Embedding query: GraphRAG response frame intent slot evidence provenance hybrid retrieval Abby 211
- AST query: IPLDKnowledgeGraph, IPLDVectorStore, GraphRAGLLMProcessor, SlottedResponseIndex
- Surplus group: objective/ABBY-VOICE-G007
- Merge key: 48fb2e0da7bdd0b3
- Merge family: objective/ABBY-VOICE-G007
- Merge role: validation_gate
- Work item count: 1
- Work scope: objective_validation_repair
- Goal packet:
- Goal packet role:
- Goal packet goals:
- Goal packet task count: 0
- Goal packet work item count: 0
- Candidate kind: validation_gate
- Todo vector key: a5461a4fe555f956
- Acceptance: Objective scan filed this gap for ABBY-VOICE-G007. Use evidence in /home/barberb/211-AI/data/abby_voice/agent_supervisor/discovery/2026-07-23-abby-voice-auto-006-objective-gap-961cb0c87404.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (objective validation repair), and keep the supervisor-fed backlog aligned with the objective heap.  Refine the objective heap if the gap needs smaller child goals.
