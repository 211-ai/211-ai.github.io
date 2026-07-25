# Objective Bundle: abby-voice/voice-router-contracts

Source todo: data/abby_voice/agent_supervisor/ABBY_VOICE_ROUTER_TODO.md
Purpose: bundle objective-generated tasks so parallel daemons can work one lane at a time.
Conflict policy: keep edits inside this bundle when possible; use the LLM merge resolver for semantic conflicts.

## ABBY-VOICE-AUTO-002 Implement Abby voice objective: Define stable voice-turn and provider contracts

- Status: completed
- Completion: manual
- Priority: P0
- Track: voice-router
- Depends on:
- Outputs: data/abby_voice/agent_supervisor/discovery, docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md, ipfs_accelerate_py/ipfs_accelerate_py/voice_router.py, ipfs_accelerate_py/test/test_voice_router_contracts.py
- Validation: python -m pytest -q ipfs_accelerate_py/test/test_voice_router_contracts.py ipfs_accelerate_py/test/test_voice_router_integration.py
- Bundle: abby-voice/voice-router-contracts
- Bundle shard: data/abby_voice/agent_supervisor/objective_bundles/abby-voice-voice-router-contracts.todo.md
- Bundle strategy: explicit
- Graph parents: ABBY-VOICE-G001
- Graph depth: 1
- Parallel lane: abby-voice-router
- Conflict policy: retain current function signatures and lazy optional dependencies; add new orchestration as an additive API
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/voice_router.py, ipfs_accelerate_py/test/test_voice_router_contracts.py
- Changed paths:
- AST symbols: VoiceProvider, text_to_speech, speech_to_text, VoiceTurnRequest, VoiceTurnResult
- Interfaces: ipfs_accelerate_py.voice_router public API
- Submodules: ipfs_accelerate_py
- Generated artifacts:
- Allow concurrent with:
- Goal id: ABBY-VOICE-G002
- Canonical task key: task/v1/90880cb1cb867636a3c1ff14af98ae4ecaf99a72cbbb675e26038fbdb42b0b0e
- Canonical task CID: baguqeerasceazmolqz3dni6b74kk7gfoj3fptgtszo5woxrgaoh33nblbmha
- Missing evidence: objective validation repair
- Embedding query: typed voice router contracts provider capabilities stage traces backward compatibility
- AST query: VoiceProvider, text_to_speech, speech_to_text, VoiceTurnRequest, VoiceTurnResult
- Surplus group: objective/ABBY-VOICE-G002
- Merge key: 407fe86571e7b1a7
- Merge family: objective/ABBY-VOICE-G002
- Merge role: validation_gate
- Work item count: 1
- Work scope: objective_validation_repair
- Goal packet:
- Goal packet role:
- Goal packet goals:
- Goal packet task count: 0
- Goal packet work item count: 0
- Candidate kind: validation_gate
- Todo vector key: f63efd593e502c7c
- Acceptance: Objective scan filed this gap for ABBY-VOICE-G002. Use evidence in /home/barberb/211-AI/data/abby_voice/agent_supervisor/discovery/2026-07-23-abby-voice-auto-002-objective-gap-c4349323df82.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (objective validation repair), and keep the supervisor-fed backlog aligned with the objective heap.  Refine the objective heap if the gap needs smaller child goals.
