# ABBY-VOICE-AUTO-017 Objective Goal Gap

Date: 2026-07-25
Fingerprint: 25c15bfd594cd308572a0ae3c7e9649eb2ab3971
Goal id: ABBY-VOICE-G010
Goal title: Adopt the unified router in wallet_interface
Objective heap: docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md
Priority: P1
Track: voice-integration
Status: todo
Schedulable: true
Review only: false
Parent goals: ABBY-VOICE-G008, ABBY-VOICE-G009
Graph depth: 7
Objective heap index: 7
Bundle: abby-voice/wallet-adoption
Parallel lane: abby-voice-integration
Bundle strategy: explicit
Goal packet: none
Goal packet role: none
Goal packet goals: none
Goal packet task count: 0
Goal packet work item count: 0
Evidence methods: embedding, exact
Embedding query: wallet Abby voice proxy shared router browser SpeechRecognition WebGPU browser speech rollout
AST query: ClientAudioReplyService, RemoteSpeechToTextResult, AgentAudioChatSurface, VoiceTurnResult
Conflict policy: use a feature flag and preserve all existing fallback paths until end-to-end receipts pass in deployed-like tests
Predicted files: wallet_interface/helpers/_voice_router_adapter.py, wallet_interface/ui/src/features/agent/lib/voiceTurnResult.ts, wallet_interface/ui/tests/agent-voice-router.spec.ts, docs/runbooks/ABBY_VOICE_ROUTER_ROLLOUT.md
AST symbols: ClientAudioReplyService, RemoteSpeechToTextResult, AgentAudioChatSurface, VoiceTurnResult
Interfaces: wallet voice proxy HTTP, VoiceTurnResult JSON, browser audio fallbacks
Submodules: ipfs_accelerate_py
Generated artifacts: none
Allow concurrent with: none
Semantic identity: objective-evidence-obligation/v1/930680fbaa1db6c01aaec79a39014f229361d6e787eff7b98bce851fe42fb0d6
Acceptance subset: focused tests cover provenance, `AgentAudioChatSurface` retains browser SpeechRecognition, the ABBY-VOICE-AUTO-010 objective-validation repair receipt records both required gates
Preconditions: objective goal ABBY-VOICE-G010 is schedulable
Effects: satisfy evidence requirement: focused tests cover provenance, satisfy evidence requirement: `AgentAudioChatSurface` retains browser SpeechRecognition, satisfy evidence requirement: the ABBY-VOICE-AUTO-010 objective-validation repair receipt records both required gates
Evidence subset: focused tests cover provenance, `AgentAudioChatSurface` retains browser SpeechRecognition, the ABBY-VOICE-AUTO-010 objective-validation repair receipt records both required gates
Dependencies: ABBY-VOICE-G019, ABBY-VOICE-G020
Resource class: cpu-medium
Token class: medium
Estimated tokens: 0
Resources: cpu-medium
Merge fate: objective/ABBY-VOICE-G010
Rejection reasons: none (accepted)

## Goal

Let the current Abby UI and service proxy use the shared contracts without removing its browser local-audio and browser-speech fallbacks.

## Missing Evidence

- focused tests cover provenance
- `AgentAudioChatSurface` retains browser SpeechRecognition
- the ABBY-VOICE-AUTO-010 objective-validation repair receipt records both required gates

## Present Evidence

- the lazy: docs/architecture/ABBY_VOICE_ROUTER_ARCHITECTURE.md (exact), docs/specs/WORLD_AID_GATE_FIRST_EXECUTION_PLAN_V2.md (exact), ipfs_accelerate_py/CONTRIBUTING.md (embedding:0.32)
- opt-in wallet adapter delegates to `process_voice_turn` and serializes the canonical `VoiceTurnResult`: docs/adr/WALLET_PRODUCTION_DECISIONS_ADR.md (embedding:0.68), docs/architecture/ABBY_VOICE_ROUTER_ARCHITECTURE.md (embedding:0.59), docs/runbooks/ABBY_VOICE_ROUTER_ROLLOUT.md (embedding:0.64)
- the UI normalizer consumes that receipt while preserving legacy payloads: ipfs_accelerate_py/ipfs_accelerate_js/test/performance/webgpu_optimizer/dashboard/README.md (embedding:0.63), ipfs_accelerate_py/test/scripts/README.md (embedding:0.62), ipfs_accelerate_py/test/temp_docs/en/model_doc/univnet.md (embedding:0.63)
- stage ordering: docs/architecture/ABBY_VOICE_ROUTER_ARCHITECTURE.md (exact), ipfs_accelerate_py/ipfs_accelerate_py/agent_supervisor/proof_scheduler.py (embedding:0.44), ipfs_accelerate_py/ipfs_accelerate_py/agent_supervisor/validation_commands.py (embedding:0.40)
- audio decoding: ipfs_accelerate_py/scripts/generators/skill_generator/pipeline_test_output/audio_pipeline.md (embedding:0.35), ipfs_accelerate_py/test/docs/model_specific_optimizations/audio_models.md (embedding:0.34), ipfs_accelerate_py/test/refactored_generator_suite/pipeline_test_output/audio_pipeline.md (embedding:0.34)
- text-only degradation: ipfs_datasets_py/.github/workflows/COPILOT-CLI-INTEGRATION.md (embedding:0.40), ipfs_datasets_py/docs/architecture/submodule_migration_verification.md (embedding:0.36), ipfs_datasets_py/docs/logic/CEC/ARCHIVE/NATIVE_INTEGRATION.md (embedding:0.33)
- and legacy rejection: docs/reports/ABBY_VOICE_EVALUATION.md (embedding:0.54), ipfs_accelerate_py/ipfs_accelerate_py/agent_supervisor/scan_receipts.py (embedding:0.30), ipfs_accelerate_py/test/api/test_agent_supervisor_task_quality.py (embedding:0.33)
- local WebGPU: docs/runbooks/ABBY_VOICE_ROUTER_ROLLOUT.md (exact), docs/runbooks/AI_AGENT_CHAT_RUNBOOK.md (embedding:0.35), ipfs_accelerate_py/ipfs_accelerate_js/src/hardware/webgpu/ultra_low_precision.ts (embedding:0.41)
- and browser speech fallback branches: docs/runbooks/ABBY_VOICE_ROUTER_ROLLOUT.md (embedding:0.42), ipfs_accelerate_py/docs/development_history/TRUE_100_PERCENT_COVERAGE.md (embedding:0.31), ipfs_accelerate_py/ipfs_accelerate_js/docs/IMPLEMENTATION_STATUS.md (embedding:0.34)
- the rollout runbook defines canary receipts and flag-off rollback: docs/runbooks/ABBY_VOICE_ROUTER_ROLLOUT.md (embedding:0.58), ipfs_datasets_py/docs/guides/IR_FAMILY_OPERATIONS.md (embedding:0.42), ipfs_kit_py/docs/guides/auto_update_install.md (embedding:0.65)

## Suggested Handling

Add an adapter and staged rollout that consumes the unified router result while retaining the proven client fallback chain.
