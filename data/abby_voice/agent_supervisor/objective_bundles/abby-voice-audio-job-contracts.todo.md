# Objective Bundle: abby-voice/audio-job-contracts

Source todo: data/abby_voice/agent_supervisor/ABBY_VOICE_ROUTER_TODO.md
Purpose: bundle objective-generated tasks so parallel daemons can work one lane at a time.
Conflict policy: keep edits inside this bundle when possible; use the LLM merge resolver for semantic conflicts.

## ABBY-VOICE-AUTO-013 Implement Abby voice objective: Define audio job contracts and the datasets-to-accelerate bridge

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: voice-scheduling
- Depends on: ABBY-VOICE-AUTO-002, ABBY-VOICE-AUTO-012
- Outputs: data/abby_voice/agent_supervisor/discovery, docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md, ipfs_accelerate_py/ipfs_accelerate_py/voice_jobs/contracts.py, ipfs_datasets_py/ipfs_datasets_py/ml/accelerate_integration/voice_jobs.py, ipfs_accelerate_py/test/test_voice_job_contracts.py, ipfs_datasets_py/tests/unit/ml/test_voice_job_bridge.py
- Validation: python -m pytest -q ipfs_accelerate_py/test/test_voice_job_contracts.py ipfs_datasets_py/tests/unit/ml/test_voice_job_bridge.py
- Bundle: abby-voice/audio-job-contracts
- Bundle shard: data/abby_voice/agent_supervisor/objective_bundles/abby-voice-audio-job-contracts.todo.md
- Bundle strategy: explicit
- Graph parents: ABBY-VOICE-G011
- Graph depth: 4
- Objective heap index: 3
- Parallel lane: abby-voice-scheduling
- Conflict policy: the contract carries immutable URI CID SHA-256 and size descriptors, never audio bytes; use the existing canonical P2P client rather than adding a second queue
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/voice_jobs/contracts.py, ipfs_datasets_py/ipfs_datasets_py/ml/accelerate_integration/voice_jobs.py, ipfs_accelerate_py/test/test_voice_job_contracts.py, ipfs_datasets_py/tests/unit/ml/test_voice_job_bridge.py
- Changed paths:
- AST symbols: VoiceTTSJob, VoiceASRJob, VoiceAudioValidationJob, VoiceJobResult, submit_voice_workset
- Interfaces: ipfs_accelerate_py.p2p_tasks.TaskQueue, ipfs_datasets_py.ml.accelerate_integration, Artifact
- Submodules: ipfs_accelerate_py, ipfs_datasets_py
- Generated artifacts:
- Allow concurrent with:
- Goal id: ABBY-VOICE-G014
- Canonical task key: task/v1/c929c2fe64a9f52d0249ec0f37544694878e9db89ebb08de41e83fe68a7fc927
- Canonical task CID: baguqeerazeu4f7tevh2s2asj5qhtovcgssdy5hnyt25qrxsb5a76nct7zetq
- Semantic identity: objective-evidence-obligation/v1/e3265f03d61eb784a8e5d1c682a0446d0b47684116a9e8f0fd505415275b7499
- Acceptance subset: lineage propagation, datasets bridge integration tests
- Preconditions: objective goal ABBY-VOICE-G014 is schedulable
- Effects: satisfy evidence requirement: lineage propagation, satisfy evidence requirement: datasets bridge integration tests
- Evidence subset: lineage propagation, datasets bridge integration tests
- Resource class: cpu-medium
- Token class: medium
- Estimated tokens: 0
- Resources: cpu-medium
- Merge fate: objective/ABBY-VOICE-G014
- Rejection reasons: none (accepted)
- Evidence obligation key: objective-evidence-obligation/v1/e3265f03d61eb784a8e5d1c682a0446d0b47684116a9e8f0fd505415275b7499
- Missing evidence: lineage propagation, datasets bridge integration tests
- Embedding query: deterministic TTS ASR STT audio validation task contract DuckDB lineage artifact descriptor
- AST query: VoiceTTSJob, VoiceASRJob, VoiceAudioValidationJob, VoiceJobResult, submit_voice_workset
- Surplus group: objective/ABBY-VOICE-G014
- Merge key: 663ed194591a2277
- Merge family: objective/ABBY-VOICE-G014
- Merge role: aggregate
- Work item count: 2
- Work scope: goal_subgoal_multi_evidence_batch
- Goal packet:
- Goal packet role:
- Goal packet goals:
- Goal packet task count: 0
- Goal packet work item count: 0
- Completion goal bindings: {}
- Completion task bindings:
- Candidate kind: aggregate
- Todo vector key: f2f1595d927e863c
- Acceptance: Objective scan filed this gap for ABBY-VOICE-G014. Use evidence in /home/barberb/211-AI/data/abby_voice/agent_supervisor/discovery/2026-07-25-abby-voice-auto-013-objective-gap-2141fa515140.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (lineage propagation, datasets bridge integration tests), and keep the supervisor-fed backlog aligned with the objective heap.  Refine the objective heap if the gap needs smaller child goals.
