# ABBY-VOICE-AUTO-010 Objective Goal Gap

Date: 2026-07-23
Fingerprint: 7d1d7d72091af2f3d2590e9bf33dcc17d20cdaba
Goal id: ABBY-VOICE-G010
Goal title: Adopt the unified router in wallet_interface
Objective heap: docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md
Priority: P1
Track: voice-integration
Parent goals: ABBY-VOICE-G008, ABBY-VOICE-G009
Graph depth: 6
Bundle: abby-voice/wallet-adoption
Parallel lane: abby-voice-integration
Bundle strategy: explicit
Goal packet: none
Goal packet role: none
Goal packet goals: none
Goal packet task count: 0
Goal packet work item count: 0
Evidence methods: ast, embedding
Embedding query: wallet Abby voice proxy shared router browser SpeechRecognition WebGPU browser speech rollout
AST query: ClientAudioReplyService, RemoteSpeechToTextResult, AgentAudioChatSurface, VoiceTurnResult
Conflict policy: use a feature flag and preserve all existing fallback paths until end-to-end receipts pass in deployed-like tests
Predicted files: wallet_interface/helpers/_voice_router_adapter.py, wallet_interface/ui/src/features/agent/lib/voiceTurnResult.ts, wallet_interface/ui/tests/agent-voice-router.spec.ts, docs/runbooks/ABBY_VOICE_ROUTER_ROLLOUT.md
AST symbols: ClientAudioReplyService, RemoteSpeechToTextResult, AgentAudioChatSurface, VoiceTurnResult
Interfaces: wallet voice proxy HTTP, VoiceTurnResult JSON, browser audio fallbacks
Submodules: ipfs_accelerate_py
Generated artifacts: none
Allow concurrent with: none

## Goal

Let the current Abby UI and service proxy use the shared contracts without removing its browser local-audio and browser-speech fallbacks.

## Missing Evidence

- objective validation repair

## Present Evidence

- wallet voice proxy adapter for VoiceTurnResult: artifacts/provekit-release-checks/results.json (ast), artifacts/provekit-spike/provekit-v1-smoke.json (ast), artifacts/provekit-ui-signoff/signoff-matrix.json (ast)
- preserved browser SpeechRecognition fallback: docs/211_indextts_precompute_batches/batch-00000-offset-000000.json (ast), docs/211_indextts_precompute_batches/batch-00001-offset-000032.json (ast), docs/211_indextts_precompute_batches/batch-00002-offset-000064.json (ast)
- preserved local WebGPU and browser speech fallback: docs/211_indextts_precompute_batches/batch-00000-offset-000000.json (ast), docs/211_indextts_precompute_batches/batch-00001-offset-000032.json (ast), docs/211_indextts_precompute_batches/batch-00002-offset-000064.json (ast)
- end-to-end UI voice tests: ARCHITECTURE.md (embedding:0.36), artifacts/provekit-ui-signoff/signoff-matrix.json (ast), docs/2026-36- CHA- Pre-Proposal meeting Q and A.transcript.segments.json (ast)
- operator rollout and rollback documentation: docs/211_conversation_dag_shards/location__clackamas.json (ast), docs/211_conversation_dag_shards/location__eugene.json (ast), docs/211_conversation_dag_shards/location__hillsboro.json (ast)
- ABBY-VOICE-G010 completion receipt: docs/211_indextts_precompute_batches/batch-00000-offset-000000.json (ast), docs/211_indextts_precompute_batches/batch-00001-offset-000032.json (ast), docs/211_indextts_precompute_batches/batch-00002-offset-000064.json (ast)

## Suggested Handling

Run and repair the objective validation command until it passes, then record the evidence.
