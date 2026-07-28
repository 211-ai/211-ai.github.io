# Objective Bundle: abby-voice/regeneration-runtime

Source todo: data/abby_voice/agent_supervisor/ABBY_VOICE_ROUTER_TODO.md
Purpose: regenerate queued Abby phone/address audio repairs and wire cache-miss response DAG appends through the refactored package-owned voice stack.
Conflict policy: land reusable voice behavior in `ipfs_accelerate_py` and `ipfs_datasets_py`; keep repository scripts and wallet/telephone adapters thin; remote Hugging Face writes remain dry-run until exact operator approval.

## ABBY-VOICE-AUTO-033 Verify regenerated Abby audio and multi-surface runtime integration

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: voice-integration
- Depends on: ABBY-VOICE-AUTO-034, ABBY-VOICE-AUTO-035, ABBY-VOICE-AUTO-036, ABBY-VOICE-AUTO-037, ABBY-VOICE-AUTO-038
- Outputs: docs/runbooks/ABBY_VOICE_REGENERATION_RUNTIME_IMPROVEMENT_PLAN.md, docs/reports/ABBY_VOICE_DISTRIBUTED_EVALUATION.md, data/abby_voice/agent_supervisor/discovery/ABBY-VOICE-G030-completion.md
- Validation: python -m pytest -q tests/voice/test_abby_voice_multiturn_e2e.py tests/voice/test_abby_voice_pipeline.py tests/voice/test_abby_voice_distributed_pipeline.py tests/voice/test_abby_voice_safety.py ipfs_accelerate_py/test/test_voice_router_precomputed_audio.py tests/test_upload_hf_abby_tts_dataset.py
- Bundle: abby-voice/regeneration-runtime
- Bundle shard: data/abby_voice/agent_supervisor/objective_bundles/abby-voice-regeneration-runtime.todo.md
- Bundle strategy: explicit
- Graph parents: ABBY-VOICE-G001
- Graph depth: 1
- Parallel lane: abby-voice-regeneration
- Conflict policy: integrate only receipt-backed child outputs; remote Hugging Face mutation remains outside this local completion task.
- Predicted files: docs/runbooks/ABBY_VOICE_REGENERATION_RUNTIME_IMPROVEMENT_PLAN.md, docs/reports/ABBY_VOICE_DISTRIBUTED_EVALUATION.md, data/abby_voice/agent_supervisor/discovery/ABBY-VOICE-G030-completion.md
- Changed paths:
- AST symbols: process_voice_turn, VoiceTurnResult, VoiceStageTrace
- Interfaces: regeneration receipt, response DAG candidate receipt, website multi-turn report, telephone multi-turn report, Whisper quality report
- Submodules: ipfs_accelerate_py, ipfs_datasets_py
- Generated artifacts: data/abby_voice/agent_supervisor/discovery/ABBY-VOICE-G030-completion.md
- Allow concurrent with:
- Goal id: ABBY-VOICE-G036
- Completion authority: local
- External authority blockers:
- Canonical task key: task/v1/aea887ef73c040dc9531757a0fe9036802761d75f38f45575870ba660c82acfc
- Canonical task CID: baguqeerav2uip33tybanzfjrov5a72idnabhmhlv6ohukv2yoc5gmdecvt6a
- Semantic identity: objective-evidence-obligation/v1/4956c0c4c73c913ab8e8b00a1a27534455eb12b8beb11ec3262450f7b6a42e22
- Acceptance subset: child completion receipts, end-to-end local validation, no-remote-write audit
- Preconditions: ABBY-VOICE-AUTO-034 through ABBY-VOICE-AUTO-038 are completed with current-tree-bound receipts.
- Effects: satisfy evidence requirement: G030 local integration completion, satisfy evidence requirement: remote publication remains fenced to G021
- Evidence subset: child completion receipts, local integration report, no-remote-write audit
- Resource class: cpu-medium
- Token class: high
- Estimated tokens: 0
- Resources: cpu-medium
- Merge fate: objective/ABBY-VOICE-G036
- Rejection reasons: none (accepted)
- Missing evidence: child completion receipts, local integration report, no-remote-write audit
- Embedding query: Abby voice regeneration integration completion child receipts website telephone evaluation no remote write
- AST query: process_voice_turn, VoiceTurnResult, VoiceStageTrace
- Surplus group: objective/ABBY-VOICE-G036
- Merge key: regeneration-runtime-integration-20260728
- Merge family: objective/ABBY-VOICE-G036
- Merge role: aggregate
- Work item count: 1
- Work scope: regeneration_runtime_integration_gate
- Candidate kind: aggregate
- Acceptance: Verify current-tree-bound completion receipts for ABBY-VOICE-AUTO-034 through ABBY-VOICE-AUTO-038, run the declared local end-to-end validation, record hit and miss plus Whisper quality results, and prove that no remote Hugging Face mutation occurred.
