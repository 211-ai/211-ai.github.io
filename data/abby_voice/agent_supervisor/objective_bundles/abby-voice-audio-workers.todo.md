# Objective Bundle: abby-voice/audio-workers

Source todo: data/abby_voice/agent_supervisor/ABBY_VOICE_ROUTER_TODO.md
Purpose: bundle objective-generated tasks so parallel daemons can work one lane at a time.
Conflict policy: keep edits inside this bundle when possible; use the LLM merge resolver for semantic conflicts.

## ABBY-VOICE-AUTO-014 Implement Abby voice objective: Add durable voice workers and repair backend routing

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: voice-scheduling
- Depends on: ABBY-VOICE-AUTO-004, ABBY-VOICE-AUTO-013
- Outputs: data/abby_voice/agent_supervisor/discovery, data/abby_voice/agent_supervisor/discovery/2026-07-26-abby-voice-auto-014-objective-validation-repair.md, docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md, ipfs_accelerate_py/ipfs_accelerate_py/voice_jobs/__init__.py, ipfs_accelerate_py/ipfs_accelerate_py/voice_jobs/executor.py, ipfs_accelerate_py/ipfs_accelerate_py/p2p_tasks/task_types.py, ipfs_accelerate_py/ipfs_accelerate_py/p2p_tasks/worker.py, ipfs_accelerate_py/ipfs_accelerate_py/p2p_tasks/service.py, ipfs_accelerate_py/ipfs_accelerate_py/voice_router.py, ipfs_accelerate_py/test/test_voice_job_worker.py
- Validation: python -m pytest -q ipfs_accelerate_py/test/test_voice_job_worker.py ipfs_accelerate_py/test/test_voice_router_contracts.py ipfs_accelerate_py/test/test_abby_voice_providers.py ipfs_accelerate_py/test/test_voice_job_contracts.py
- Bundle: abby-voice/audio-workers
- Bundle shard: data/abby_voice/agent_supervisor/objective_bundles/abby-voice-audio-workers.todo.md
- Bundle strategy: explicit
- Graph parents: ABBY-VOICE-G011
- Graph depth: 4
- Objective heap index: 4
- Parallel lane: abby-voice-scheduling
- Conflict policy: handlers call `voice_router.text_to_speech` and `speech_to_text` or injected equivalents; do not reimplement Abby HTTP retry/circuit-breaker behavior; preserve legacy router APIs
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/voice_jobs/__init__.py, ipfs_accelerate_py/ipfs_accelerate_py/voice_jobs/executor.py, ipfs_accelerate_py/ipfs_accelerate_py/p2p_tasks/task_types.py, ipfs_accelerate_py/ipfs_accelerate_py/p2p_tasks/worker.py, ipfs_accelerate_py/ipfs_accelerate_py/p2p_tasks/service.py, ipfs_accelerate_py/ipfs_accelerate_py/voice_router.py, ipfs_accelerate_py/test/test_voice_job_worker.py
- Changed paths:
- AST symbols: execute_voice_tts_job, execute_voice_asr_job, execute_voice_audio_validation_job, execute_task, text_to_speech, speech_to_text
- Interfaces: P2P worker handlers, VoiceJobResult, voice_router, voice_providers.abby, InferenceBackendManager
- Submodules: ipfs_accelerate_py
- Generated artifacts:
- Allow concurrent with:
- Goal id: ABBY-VOICE-G015
- Canonical task key: task/v1/b565da18cd2115f0935079bff87d3d12564d308fbc5d95d1375afd889902ba71
- Canonical task CID: baguqeerawvs5uggneek7be2qpg77q7j5cjle2mepxrozlujxll6yrgicxjyq
- Semantic identity: objective-evidence-obligation/v1/94100771979b57c00f0db7693aa04f9e4a3e8d6587f7e3f8e6adc1f57a7ef486
- Acceptance subset: TTS/ASR execution, voice handlers, independent TTS/STT device controls, offline worker and mesh tests
- Preconditions: objective goal ABBY-VOICE-G015 is schedulable
- Effects: satisfy evidence requirement: TTS/ASR execution, satisfy evidence requirement: voice handlers, satisfy evidence requirement: independent TTS/STT device controls, satisfy evidence requirement: offline worker and mesh tests
- Evidence subset: TTS/ASR execution, voice handlers, independent TTS/STT device controls, offline worker and mesh tests
- Resource class: cpu-medium
- Token class: medium
- Estimated tokens: 0
- Resources: cpu-medium
- Merge fate: objective/ABBY-VOICE-G015
- Rejection reasons: none (accepted)
- Evidence obligation key: objective-evidence-obligation/v1/94100771979b57c00f0db7693aa04f9e4a3e8d6587f7e3f8e6adc1f57a7ef486
- Missing evidence: TTS/ASR execution, voice handlers, independent TTS/STT device controls, offline worker and mesh tests
- Embedding query: P2P worker voice TTS ASR STT capability voice_router backend manager artifact
- AST query: execute_voice_tts_job, execute_voice_asr_job, execute_voice_audio_validation_job, execute_task, text_to_speech, speech_to_text
- Surplus group: objective/ABBY-VOICE-G015
- Merge key: 438932bfd049ffda
- Merge family: objective/ABBY-VOICE-G015
- Merge role: aggregate
- Work item count: 4
- Work scope: goal_subgoal_multi_evidence_batch
- Goal packet:
- Goal packet role:
- Goal packet goals:
- Goal packet task count: 0
- Goal packet work item count: 0
- Completion goal bindings: {}
- Completion task bindings:
- Candidate kind: aggregate
- Todo vector key: 41d64c2b520bfacc
- Acceptance: Objective scan filed this gap for ABBY-VOICE-G015. Use evidence in /home/barberb/211-AI/data/abby_voice/agent_supervisor/discovery/2026-07-25-abby-voice-auto-014-objective-gap-d308fe5a1e3c.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (TTS/ASR execution, voice handlers, independent TTS/STT device controls, offline worker and mesh tests), and keep the supervisor-fed backlog aligned with the objective heap.  Refine the objective heap if the gap needs smaller child goals.
