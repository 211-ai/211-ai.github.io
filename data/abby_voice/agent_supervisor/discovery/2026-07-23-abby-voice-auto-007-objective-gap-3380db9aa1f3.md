# ABBY-VOICE-AUTO-007 Objective Goal Gap

Date: 2026-07-23
Fingerprint: 3380db9aa1f3dcb10a9c90abfa30ce9f3bc4a654
Goal id: ABBY-VOICE-G008
Goal title: Integrate GraphRAG templating into voice_router
Objective heap: docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md
Priority: P0
Track: voice-graphrag
Parent goals: ABBY-VOICE-G002, ABBY-VOICE-G003, ABBY-VOICE-G007
Graph depth: 4
Bundle: abby-voice/router-graphrag-integration
Parallel lane: abby-voice-graphrag
Bundle strategy: explicit
Goal packet: none
Goal packet role: none
Goal packet goals: none
Goal packet task count: 0
Goal packet work item count: 0
Evidence methods: ast
Embedding query: voice router GraphRAG template provider grounded slot binding spoken normalization provenance
AST query: process_voice_turn, VoiceTemplateProvider, GraphRAGVoiceTemplateProvider, buildVoiceGraphRagPromptParts
Conflict policy: use dependency injection across submodules and avoid mandatory ipfs_datasets_py imports at voice_router import time
Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/voice_router.py, ipfs_accelerate_py/ipfs_accelerate_py/voice_templates.py, ipfs_accelerate_py/test/test_voice_router_graphrag.py
AST symbols: process_voice_turn, VoiceTemplateProvider, GraphRAGVoiceTemplateProvider, buildVoiceGraphRagPromptParts
Interfaces: VoiceTemplateProvider, GraphRAGVoiceTemplateProvider, VoiceTurnResult
Submodules: ipfs_accelerate_py, ipfs_datasets_py
Generated artifacts: none
Allow concurrent with: none

## Goal

Add an optional template provider to process_voice_turn that can retrieve a response plan bind only grounded facts normalize spoken text and synthesize the final response.

## Missing Evidence

- objective validation repair

## Present Evidence

- optional VoiceTemplateProvider protocol: artifacts/chainlink-cre-spike/cre-capability-matrix.json (ast), artifacts/world-id-idkit-signoff/pilot-signoff-evidence-index.json (ast), chainlink/cre/llm_consensus_workflow.example.json (ast)
- grounded slot binding implementation: docs/211_indextts_precompute_batches/batch-00000-offset-000000.json (ast), docs/211_indextts_precompute_batches/batch-00001-offset-000032.json (ast), docs/211_indextts_precompute_batches/batch-00002-offset-000064.json (ast)
- citation stripping with retained machine provenance: artifacts/provekit-spike/provekit-v1-smoke.json (ast), docs/211_indextts_precompute_batches/batch-00000-offset-000000.json (ast), docs/211_indextts_precompute_batches/batch-00001-offset-000032.json (ast)
- deterministic fallback response: docs/211_indextts_precompute_batches/batch-00000-offset-000000.json (ast), docs/211_indextts_precompute_batches/batch-00001-offset-000032.json (ast), docs/211_indextts_precompute_batches/batch-00002-offset-000064.json (ast)
- integration tests with fake GraphRAG provider: artifacts/chainlink-cre-spike/cre-capability-matrix.json (ast), artifacts/provekit-ui-signoff/signoff-matrix.json (ast), artifacts/world-id-idkit-signoff/pilot-signoff-evidence-index.json (ast)
- ABBY-VOICE-G008 completion receipt: docs/211_indextts_precompute_batches/batch-00000-offset-000000.json (ast), docs/211_indextts_precompute_batches/batch-00001-offset-000032.json (ast), docs/211_indextts_precompute_batches/batch-00002-offset-000064.json (ast)

## Suggested Handling

Run and repair the objective validation command until it passes, then record the evidence.
