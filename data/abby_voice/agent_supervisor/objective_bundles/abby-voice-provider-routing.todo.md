# Objective Bundle: abby-voice/provider-routing

Source todo: data/abby_voice/agent_supervisor/ABBY_VOICE_ROUTER_TODO.md
Purpose: bundle objective-generated tasks so parallel daemons can work one lane at a time.
Conflict policy: keep edits inside this bundle when possible; use the LLM merge resolver for semantic conflicts.

## ABBY-VOICE-AUTO-004 Implement Abby voice objective: Port Abby provider fallback behavior into voice_router

- Status: completed
- Completion: manual
- Priority: P0
- Track: voice-router
- Depends on:
- Outputs: data/abby_voice/agent_supervisor/discovery, docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md, ipfs_accelerate_py/ipfs_accelerate_py/voice_providers/abby.py, ipfs_accelerate_py/ipfs_accelerate_py/voice_router.py, ipfs_accelerate_py/test/test_abby_voice_providers.py
- Validation: python -m pytest -q ipfs_accelerate_py/test/test_abby_voice_providers.py
- Bundle: abby-voice/provider-routing
- Bundle shard: data/abby_voice/agent_supervisor/objective_bundles/abby-voice-provider-routing.todo.md
- Bundle strategy: explicit
- Graph parents: ABBY-VOICE-G002
- Graph depth: 2
- Parallel lane: abby-voice-router
- Conflict policy: adapters must be optional and secret-free; tests use injected transports and never call paid or mutable remote services
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/voice_providers/abby.py, ipfs_accelerate_py/ipfs_accelerate_py/voice_router.py, ipfs_accelerate_py/test/test_abby_voice_providers.py
- Changed paths:
- AST symbols: _run_indextts_gradio_tts, _run_hf_whisper_stt, get_voice_provider, ProviderInfo
- Interfaces: VoiceProviderCapabilities, Abby IndexTTS HTTP, Abby Whisper HTTP
- Submodules: ipfs_accelerate_py
- Generated artifacts:
- Allow concurrent with:
- Goal id: ABBY-VOICE-G003
- Canonical task key: task/v1/b0e4974e75cc85b5b48da2b5a594355cc00b4432f64f4dd99e152ed60a3e7b56
- Canonical task CID: baguqeerawdsjottvzsc3lnenuk22lfbvltaawrbs6zhu3wm6cuxnmcr6pnla
- Missing evidence: objective validation repair
- Embedding query: IndexTTS Whisper remote local fallback retry timeout circuit breaker voice proxy
- AST query: _run_indextts_gradio_tts, _run_hf_whisper_stt, get_voice_provider, ProviderInfo
- Surplus group: objective/ABBY-VOICE-G003
- Merge key: 8ece9d87394a54b2
- Merge family: objective/ABBY-VOICE-G003
- Merge role: validation_gate
- Work item count: 1
- Work scope: objective_validation_repair
- Goal packet:
- Goal packet role:
- Goal packet goals:
- Goal packet task count: 0
- Goal packet work item count: 0
- Candidate kind: validation_gate
- Todo vector key: 5d930aabc55df3e7
- Acceptance: Objective scan filed this gap for ABBY-VOICE-G003. Use evidence in /home/barberb/211-AI/data/abby_voice/agent_supervisor/discovery/2026-07-23-abby-voice-auto-004-objective-gap-31b52886b489.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (objective validation repair), and keep the supervisor-fed backlog aligned with the objective heap.  Refine the objective heap if the gap needs smaller child goals.
