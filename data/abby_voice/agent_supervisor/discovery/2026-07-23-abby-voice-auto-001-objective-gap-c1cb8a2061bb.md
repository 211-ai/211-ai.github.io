# ABBY-VOICE-AUTO-001 Objective Goal Gap

Date: 2026-07-23
Fingerprint: c1cb8a2061bbb65830b5c820ee7884dd584d4eb3
Goal id: ABBY-VOICE-G001
Goal title: Deliver a unified grounded Abby voice pipeline
Objective heap: docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md
Priority: P0
Track: voice-platform
Parent goals: none
Graph depth: 0
Bundle: abby-voice/integration
Parallel lane: abby-voice-integration
Bundle strategy: explicit
Goal packet: none
Goal packet role: none
Goal packet goals: none
Goal packet task count: 0
Goal packet work item count: 0
Evidence methods: ast
Embedding query: Abby grounded voice turn STT GraphRAG response templates TTS fallback provenance
AST query: VoiceTurnRequest, VoiceTurnResult, process_voice_turn, GraphRAGVoiceTemplateProvider
Conflict policy: integrate child-goal contracts only after their focused tests pass; preserve backward compatibility for text_to_speech and speech_to_text
Predicted files: docs/architecture/ABBY_VOICE_ROUTER_ARCHITECTURE.md, ipfs_accelerate_py/ipfs_accelerate_py/voice_router.py, tests/voice/test_abby_voice_pipeline.py
AST symbols: VoiceTurnRequest, VoiceTurnResult, process_voice_turn, GraphRAGVoiceTemplateProvider
Interfaces: ipfs_accelerate_py.voice_router, ipfs_datasets_py GraphRAG, wallet voice proxy
Submodules: ipfs_accelerate_py, ipfs_datasets_py
Generated artifacts: none
Allow concurrent with: none

## Goal

Deliver a reusable voice turn pipeline that transcribes caller audio, retrieves grounded 211 evidence and reusable response frames, renders safe spoken text, synthesizes audio, and returns provenance and fallback metadata.

## Missing Evidence

- objective validation repair

## Present Evidence

- unified VoiceTurnRequest and VoiceTurnResult contracts: artifacts/provekit-release-checks/results.json (ast), artifacts/provekit-spike/provekit-v1-smoke.json (ast), artifacts/provekit-ui-signoff/signoff-matrix.json (ast)
- GraphRAG response-template retrieval adapter: docs/211_indextts_precompute_batches/batch-00000-offset-000000.json (ast), docs/211_indextts_precompute_batches/batch-00001-offset-000032.json (ast), docs/211_indextts_precompute_batches/batch-00002-offset-000064.json (ast)
- curated Abby voice dataset configurations: docs/211_indextts_precompute_batches/batch-00000-offset-000000.json (ast), docs/211_indextts_precompute_batches/batch-00001-offset-000032.json (ast), docs/211_indextts_precompute_batches/batch-00002-offset-000064.json (ast)
- end-to-end voice pipeline acceptance receipts: docs/2026-36- CHA- Pre-Proposal meeting Q and A.transcript.segments.json (ast), docs/211_conversation_dag_shards/location__clackamas.json (ast), docs/211_conversation_dag_shards/location__eugene.json (ast)
- ABBY-VOICE-G001 completion receipt: docs/211_indextts_precompute_batches/batch-00000-offset-000000.json (ast), docs/211_indextts_precompute_batches/batch-00001-offset-000032.json (ast), docs/211_indextts_precompute_batches/batch-00002-offset-000064.json (ast)

## Suggested Handling

Run and repair the objective validation command until it passes, then record the evidence.
