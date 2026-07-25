# ABBY-VOICE-AUTO-004 Objective Goal Gap

Date: 2026-07-23
Fingerprint: 31b52886b4899c799a7addda29d1151f592141f9
Goal id: ABBY-VOICE-G003
Goal title: Port Abby provider fallback behavior into voice_router
Objective heap: docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md
Priority: P0
Track: voice-router
Parent goals: ABBY-VOICE-G002
Graph depth: 2
Bundle: abby-voice/provider-routing
Parallel lane: abby-voice-router
Bundle strategy: explicit
Goal packet: none
Goal packet role: none
Goal packet goals: none
Goal packet task count: 0
Goal packet work item count: 0
Evidence methods: ast
Embedding query: IndexTTS Whisper remote local fallback retry timeout circuit breaker voice proxy
AST query: _run_indextts_gradio_tts, _run_hf_whisper_stt, get_voice_provider, ProviderInfo
Conflict policy: adapters must be optional and secret-free; tests use injected transports and never call paid or mutable remote services
Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/voice_providers/abby.py, ipfs_accelerate_py/ipfs_accelerate_py/voice_router.py, ipfs_accelerate_py/test/test_abby_voice_providers.py
AST symbols: _run_indextts_gradio_tts, _run_hf_whisper_stt, get_voice_provider, ProviderInfo
Interfaces: VoiceProviderCapabilities, Abby IndexTTS HTTP, Abby Whisper HTTP
Submodules: ipfs_accelerate_py
Generated artifacts: none
Allow concurrent with: none

## Goal

Make the Python voice router capable of the same ordered remote local and degraded behaviors used by the wallet voice assistant without importing UI-specific code.

## Missing Evidence

- objective validation repair

## Present Evidence

- IndexTTS provider adapter: artifacts/chainlink-cre-spike/cre-capability-matrix.json (ast), artifacts/world-id-idkit-signoff/pilot-signoff-evidence-index.json (ast), chainlink/cre/llm_consensus_workflow.example.json (ast)
- Hugging Face Whisper HTTP adapter: chainlink/cre/llm_consensus_workflow.example.json (ast), docs/211_indextts_precompute_batches/batch-00000-offset-000000.json (ast), docs/211_indextts_precompute_batches/batch-00001-offset-000032.json (ast)
- ordered capability-aware fallback policy: artifacts/chainlink-cre-spike/cre-capability-matrix.json (ast), chainlink/cre/llm_consensus_workflow.example.json (ast), docs/211_indextts_precompute_batches/batch-00000-offset-000000.json (ast)
- bounded retry timeout and circuit-breaker tests: /home/barberb/211-AI/ipfs_accelerate_py/ipfs_accelerate_js/test/performance/webgpu_optimizer/run_benchmarks.py (ast), artifacts/provekit-ui-signoff/signoff-matrix.json (ast), docs/211_indextts_precompute_batches/batch-00000-offset-000000.json (ast)
- structured degraded-result receipts: artifacts/provekit-release-checks/results.json (ast), artifacts/provekit-spike/provekit-v1-smoke.json (ast), artifacts/provekit-ui-signoff/signoff-matrix.json (ast)
- ABBY-VOICE-G003 completion receipt: docs/211_indextts_precompute_batches/batch-00000-offset-000000.json (ast), docs/211_indextts_precompute_batches/batch-00001-offset-000032.json (ast), docs/211_indextts_precompute_batches/batch-00002-offset-000064.json (ast)

## Suggested Handling

Run and repair the objective validation command until it passes, then record the evidence.
