# ABBY-VOICE-AUTO-006 Objective Goal Gap

Date: 2026-07-23
Fingerprint: 961cb0c87404aa2afd2afa62f661db994d5b25f6
Goal id: ABBY-VOICE-G007
Goal title: Add GraphRAG response-template ingestion and retrieval
Objective heap: docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md
Priority: P0
Track: voice-graphrag
Parent goals: ABBY-VOICE-G004, ABBY-VOICE-G005
Graph depth: 3
Bundle: abby-voice/graphrag-templates
Parallel lane: abby-voice-graphrag
Bundle strategy: explicit
Goal packet: none
Goal packet role: none
Goal packet goals: none
Goal packet task count: 0
Goal packet work item count: 0
Evidence methods: ast
Embedding query: GraphRAG response frame intent slot evidence provenance hybrid retrieval Abby 211
AST query: IPLDKnowledgeGraph, IPLDVectorStore, GraphRAGLLMProcessor, SlottedResponseIndex
Conflict policy: retrieved templates are response plans only; factual slots must bind from current cited evidence and never from stale example wording
Predicted files: ipfs_datasets_py/ipfs_datasets_py/voice/graphrag.py, ipfs_datasets_py/tests/unit/voice/test_abby_voice_graphrag.py, docs/data/ABBY_VOICE_GRAPHRAG.md
AST symbols: IPLDKnowledgeGraph, IPLDVectorStore, GraphRAGLLMProcessor, SlottedResponseIndex
Interfaces: GraphRAGVoiceTemplateProvider, ipfs_datasets_py vector store, IPLD knowledge graph
Submodules: ipfs_datasets_py
Generated artifacts: none
Allow concurrent with: none

## Goal

Ingest canonical response frames evidence links and slot relationships into ipfs_datasets_py and retrieve them as response plans rather than uncited final answers.

## Missing Evidence

- objective validation repair

## Present Evidence

- GraphRAGVoiceTemplateProvider implementation: artifacts/chainlink-cre-spike/cre-capability-matrix.json (ast), artifacts/world-id-idkit-signoff/pilot-signoff-evidence-index.json (ast), chainlink/cre/llm_consensus_workflow.example.json (ast)
- IPLD template intent evidence graph: artifacts/chainlink-cre-spike/cre-capability-matrix.json (ast), artifacts/chainlink-zkml-ui-review/review-matrix.json (ast), artifacts/provekit-ui-signoff/signoff-matrix.json (ast)
- hybrid template retriever: artifacts/chainlink-cre-spike/cre-capability-matrix.json (ast), artifacts/world-id-idkit-signoff/pilot-signoff-evidence-index.json (ast), docs/211_conversation_dag_shards/location__clackamas.json (ast)
- slot binding safety policy: chainlink/cre/llm_consensus_workflow.example.json (ast), docs/211_indextts_precompute_batches/batch-00000-offset-000000.json (ast), docs/211_indextts_precompute_batches/batch-00001-offset-000032.json (ast)
- retrieval provenance tests: artifacts/provekit-spike/provekit-v1-smoke.json (ast), artifacts/provekit-ui-signoff/signoff-matrix.json (ast), docs/211_indextts_precompute_batches/batch-00000-offset-000000.json (ast)
- ABBY-VOICE-G007 completion receipt: docs/211_indextts_precompute_batches/batch-00000-offset-000000.json (ast), docs/211_indextts_precompute_batches/batch-00001-offset-000032.json (ast), docs/211_indextts_precompute_batches/batch-00002-offset-000064.json (ast)

## Suggested Handling

Run and repair the objective validation command until it passes, then record the evidence.
