# ABBY-VOICE-AUTO-014 Objective Goal Gap

Date: 2026-07-25
Fingerprint: d308fe5a1e3cba11a034b7a4b380cfacd5a3c62f
Goal id: ABBY-VOICE-G015
Goal title: Add durable voice workers and repair backend routing
Objective heap: docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md
Priority: P0
Track: voice-scheduling
Status: todo
Schedulable: true
Review only: false
Parent goals: ABBY-VOICE-G011
Graph depth: 4
Objective heap index: 4
Bundle: abby-voice/audio-workers
Parallel lane: abby-voice-scheduling
Bundle strategy: explicit
Goal packet: none
Goal packet role: none
Goal packet goals: none
Goal packet task count: 0
Goal packet work item count: 0
Evidence methods: embedding
Embedding query: P2P worker voice TTS ASR STT capability voice_router backend manager artifact
AST query: execute_voice_tts_job, execute_voice_asr_job, execute_voice_audio_validation_job, execute_task, text_to_speech, speech_to_text
Conflict policy: handlers call `voice_router.text_to_speech` and `speech_to_text` or injected equivalents; do not reimplement Abby HTTP retry/circuit-breaker behavior; preserve legacy router APIs
Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/voice_jobs/executor.py, ipfs_accelerate_py/ipfs_accelerate_py/p2p_tasks/worker.py, ipfs_accelerate_py/ipfs_accelerate_py/p2p_tasks/service.py, ipfs_accelerate_py/ipfs_accelerate_py/voice_router.py, ipfs_accelerate_py/test/test_voice_job_worker.py
AST symbols: execute_voice_tts_job, execute_voice_asr_job, execute_voice_audio_validation_job, execute_task, text_to_speech, speech_to_text
Interfaces: P2P worker handlers, voice_router, voice_providers.abby, InferenceBackendManager
Submodules: ipfs_accelerate_py
Generated artifacts: none
Allow concurrent with: none
Semantic identity: objective-evidence-obligation/v1/94100771979b57c00f0db7693aa04f9e4a3e8d6587f7e3f8e6adc1f57a7ef486
Acceptance subset: TTS/ASR execution, voice handlers, independent TTS/STT device controls, offline worker and mesh tests
Preconditions: objective goal ABBY-VOICE-G015 is schedulable
Effects: satisfy evidence requirement: TTS/ASR execution, satisfy evidence requirement: voice handlers, satisfy evidence requirement: independent TTS/STT device controls, satisfy evidence requirement: offline worker and mesh tests
Evidence subset: TTS/ASR execution, voice handlers, independent TTS/STT device controls, offline worker and mesh tests
Dependencies: ABBY-VOICE-G003, ABBY-VOICE-G014
Resource class: cpu-medium
Token class: medium
Estimated tokens: 0
Resources: cpu-medium
Merge fate: objective/ABBY-VOICE-G015
Rejection reasons: none (accepted)

## Goal

Add advertised TTS ASR and audio-validation handlers to the existing P2P worker and execute model work through the established voice_router providers.

## Missing Evidence

- TTS/ASR execution
- voice handlers
- independent TTS/STT device controls
- offline worker and mesh tests

## Present Evidence

- shared task alias registry: ipfs_accelerate_py/docs/api/overview.md (embedding:0.34), ipfs_accelerate_py/ipfs_accelerate_py/agent_supervisor/task_identity.py (embedding:0.35), ipfs_accelerate_py/ipfs_accelerate_py/agent_supervisor/todo_daemon/__init__.py (embedding:0.34)
- worker and service capability parity: docs/runbooks/CHAINLINK_ZKML_LLM_ROUTER_RUNBOOK.md (embedding:0.34), docs/specs/AI_AGENT_CHAT_THREAT_MODEL.md (embedding:0.34), ipfs_accelerate_py/README.md (embedding:0.41)
- backend-manager API regression fix: ipfs_accelerate_py/docs/archive/implementations/CICD_MCP_VALIDATION_REPORT.md (embedding:0.30), ipfs_accelerate_py/docs/project/reviews/CODE_REVIEW_FIXES_SUMMARY.md (embedding:0.31), ipfs_datasets_py/docs/PHASE3C_COMPLETION_FULL.md (embedding:0.31)
- allowed-artifact resolver: ipfs_datasets_py/ipfs_datasets_py/logic/profile_g.py (embedding:0.40), ipfs_datasets_py/scripts/ops/security_verification/xaman_firebase_disabled_testnet.py (embedding:0.34), ipfs_kit_py/ipfs_kit_py/mcp_server/agent_supervisor_receipts.py (embedding:0.37)

## Suggested Handling

Register and advertise real audio handlers, repair the drifted backend-manager adapter to the current async API, and fix STT device configuration before distributed routing.
