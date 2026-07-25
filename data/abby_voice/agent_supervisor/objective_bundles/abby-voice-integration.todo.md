# Objective Bundle: abby-voice/integration

Source todo: data/abby_voice/agent_supervisor/ABBY_VOICE_ROUTER_TODO.md
Purpose: bundle objective-generated tasks so parallel daemons can work one lane at a time.
Conflict policy: keep edits inside this bundle when possible; use the LLM merge resolver for semantic conflicts.

## ABBY-VOICE-AUTO-001 Implement Abby voice objective: Deliver a unified grounded Abby voice pipeline

- Status: done
- Completion: validated by commits `0c68eddd` (submodule) and `ed987516` (superproject); 18 focused and 9 legacy router tests pass
- Priority: P0
- Track: voice-platform
- Depends on:
- Outputs: data/abby_voice/agent_supervisor/discovery, docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md, docs/architecture/ABBY_VOICE_ROUTER_ARCHITECTURE.md, ipfs_accelerate_py/ipfs_accelerate_py/voice_router.py, tests/voice/test_abby_voice_pipeline.py
- Validation: python -m pytest -q tests/voice/test_abby_voice_pipeline.py
- Bundle: abby-voice/integration
- Bundle shard: data/abby_voice/agent_supervisor/objective_bundles/abby-voice-integration.todo.md
- Bundle strategy: explicit
- Graph parents: none
- Graph depth: 0
- Parallel lane: abby-voice-integration
- Conflict policy: integrate child-goal contracts only after their focused tests pass; preserve backward compatibility for text_to_speech and speech_to_text
- Predicted files: docs/architecture/ABBY_VOICE_ROUTER_ARCHITECTURE.md, ipfs_accelerate_py/ipfs_accelerate_py/voice_router.py, tests/voice/test_abby_voice_pipeline.py
- Changed paths:
- AST symbols: VoiceTurnRequest, VoiceTurnResult, process_voice_turn, GraphRAGVoiceTemplateProvider
- Interfaces: ipfs_accelerate_py.voice_router, ipfs_datasets_py GraphRAG, wallet voice proxy
- Submodules: ipfs_accelerate_py, ipfs_datasets_py
- Generated artifacts:
- Allow concurrent with:
- Goal id: ABBY-VOICE-G001
- Canonical task key: task/v1/e56607d2a1d11f8cd70bf580acb0fb42e32f2c654089e896db9c5dd6235e5adb
- Canonical task CID: baguqeera4vtapuvb2epyzvyl6wakzmh3ilrs6ldfice6rfw3tro5mi26llnq
- Missing evidence: objective validation repair
- Embedding query: Abby grounded voice turn STT GraphRAG response templates TTS fallback provenance
- AST query: VoiceTurnRequest, VoiceTurnResult, process_voice_turn, GraphRAGVoiceTemplateProvider
- Surplus group: objective/ABBY-VOICE-G001
- Merge key: 2a02bbdaf075da81
- Merge family: objective/ABBY-VOICE-G001
- Merge role: validation_gate
- Work item count: 1
- Work scope: objective_validation_repair
- Goal packet:
- Goal packet role:
- Goal packet goals:
- Goal packet task count: 0
- Goal packet work item count: 0
- Candidate kind: validation_gate
- Todo vector key: 176a49df84265f54
- Acceptance: Objective scan filed this gap for ABBY-VOICE-G001. Use evidence in /home/barberb/211-AI/data/abby_voice/agent_supervisor/discovery/2026-07-23-abby-voice-auto-001-objective-gap-c1cb8a2061bb.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (objective validation repair), and keep the supervisor-fed backlog aligned with the objective heap.  Refine the objective heap if the gap needs smaller child goals.
