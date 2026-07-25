# ABBY-VOICE-AUTO-002 Objective Goal Gap

Date: 2026-07-23
Fingerprint: c4349323df82d9bacadbae735e3e09b50300ccf6
Goal id: ABBY-VOICE-G002
Goal title: Define stable voice-turn and provider contracts
Objective heap: docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md
Priority: P0
Track: voice-router
Parent goals: ABBY-VOICE-G001
Graph depth: 1
Bundle: abby-voice/voice-router-contracts
Parallel lane: abby-voice-router
Bundle strategy: explicit
Goal packet: none
Goal packet role: none
Goal packet goals: none
Goal packet task count: 0
Goal packet work item count: 0
Evidence methods: ast, embedding
Embedding query: typed voice router contracts provider capabilities stage traces backward compatibility
AST query: VoiceProvider, text_to_speech, speech_to_text, VoiceTurnRequest, VoiceTurnResult
Conflict policy: retain current function signatures and lazy optional dependencies; add new orchestration as an additive API
Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/voice_router.py, ipfs_accelerate_py/test/test_voice_router_contracts.py
AST symbols: VoiceProvider, text_to_speech, speech_to_text, VoiceTurnRequest, VoiceTurnResult
Interfaces: ipfs_accelerate_py.voice_router public API
Submodules: ipfs_accelerate_py
Generated artifacts: none
Allow concurrent with: none

## Goal

Replace byte-or-string-only routing with typed request result capability and trace contracts while preserving the existing public TTS and STT functions.

## Missing Evidence

- objective validation repair

## Present Evidence

- VoiceTurnRequest dataclass: chainlink/cre/llm_consensus_workflow.example.json (ast), docs/211_indextts_precompute_batches/batch-00000-offset-000000.json (ast), docs/211_indextts_precompute_batches/batch-00001-offset-000032.json (ast)
- VoiceTurnResult dataclass: artifacts/provekit-release-checks/results.json (ast), artifacts/provekit-spike/provekit-v1-smoke.json (ast), artifacts/provekit-ui-signoff/signoff-matrix.json (ast)
- VoiceProviderCapabilities contract: artifacts/chainlink-cre-spike/cre-capability-matrix.json (ast), artifacts/world-id-idkit-signoff/pilot-signoff-evidence-index.json (ast), chainlink/cre/llm_consensus_workflow.example.json (ast)
- VoiceStageTrace contract: docs/211_indextts_precompute_batches/batch-00000-offset-000000.json (ast), docs/211_indextts_precompute_batches/batch-00001-offset-000032.json (ast), docs/211_indextts_precompute_batches/batch-00002-offset-000064.json (ast)
- compatibility tests for text_to_speech and speech_to_text: artifacts/chainlink-zkml-p2p-design/README.md (embedding:0.38), artifacts/chainlink-zkml-router-audit/README.md (embedding:0.36), artifacts/provekit-ui-signoff/signoff-matrix.json (ast)
- ABBY-VOICE-G002 completion receipt: docs/211_indextts_precompute_batches/batch-00000-offset-000000.json (ast), docs/211_indextts_precompute_batches/batch-00001-offset-000032.json (ast), docs/211_indextts_precompute_batches/batch-00002-offset-000064.json (ast)

## Suggested Handling

Run and repair the objective validation command until it passes, then record the evidence.
