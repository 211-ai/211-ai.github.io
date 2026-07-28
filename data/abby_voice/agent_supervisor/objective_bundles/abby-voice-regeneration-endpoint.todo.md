# Objective Bundle: abby-voice/regeneration-endpoint

Source todo: data/abby_voice/agent_supervisor/ABBY_VOICE_ROUTER_TODO.md
Purpose: build the deterministic, resumable Abby repair-queue runner and its bounded endpoint canary manifest.
Conflict policy: no live generation or paid endpoint dispatch occurs without an item and cost bound; retries are idempotent and never overwrite a validated artifact.

## ABBY-VOICE-AUTO-034 Build the endpoint-safe regeneration runner and canary manifest

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: voice-regeneration
- Depends on: ABBY-VOICE-AUTO-014, ABBY-VOICE-AUTO-031
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/voice_jobs, ipfs_datasets_py/ipfs_datasets_py/voice/regeneration.py, ipfs_datasets_py/ipfs_datasets_py/ml/accelerate_integration/voice_jobs.py, scripts/precompute_indextts_responses.py, tests/test_precompute_indextts_batch.py
- Validation: python -m pytest -q ipfs_accelerate_py/test/test_voice_job_worker.py ipfs_datasets_py/tests/unit/ml/test_voice_job_bridge.py ipfs_datasets_py/tests/unit/voice/test_abby_voice_regeneration.py tests/test_precompute_indextts_batch.py
- Bundle: abby-voice/regeneration-endpoint
- Bundle shard: data/abby_voice/agent_supervisor/objective_bundles/abby-voice-regeneration-endpoint.todo.md
- Bundle strategy: explicit
- Graph parents: ABBY-VOICE-G030
- Graph depth: 2
- Parallel lane: abby-voice-regeneration
- Conflict policy: no live generation or paid endpoint dispatch occurs without an item and cost bound; retries are idempotent and never overwrite a validated artifact.
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/voice_jobs/contracts.py, ipfs_accelerate_py/ipfs_accelerate_py/voice_jobs/executor.py, ipfs_datasets_py/ipfs_datasets_py/voice/regeneration.py, ipfs_datasets_py/ipfs_datasets_py/ml/accelerate_integration/voice_jobs.py, scripts/precompute_indextts_responses.py, ipfs_datasets_py/tests/unit/voice/test_abby_voice_regeneration.py, tests/test_precompute_indextts_batch.py
- Changed paths:
- AST symbols: VoiceTTSJob, VoiceJobBridge, execute_voice_tts_job, HFSpaceClient
- Interfaces: IndexTTS endpoint contract, VoiceTTSJob, VoiceJobBridge, provider receipt
- Submodules: ipfs_accelerate_py, ipfs_datasets_py
- Generated artifacts: tmp_assets/hf-abby-tts-canonical-dataset/metadata/abby_tts_regeneration_queue.jsonl, data/abby_voice/agent_supervisor/discovery
- Allow concurrent with: ABBY-VOICE-AUTO-035, ABBY-VOICE-AUTO-036, ABBY-VOICE-AUTO-037
- Goal id: ABBY-VOICE-G031
- Completion authority: local
- External authority blockers:
- Canonical task key: task/v1/4ce2ac39d2cfa42b2616e9cfad203cd88188fdcb64fa4d5ee51f342232d36214
- Canonical task CID: baguqeerajtrkyoosz6scwjqw5hh22ib43cayr7olmt5e2xxfd42cemwtmika
- Semantic identity: objective-evidence-obligation/v1/a929c4cb0580cc9d04e769771e134069e9cf948735c0ce09c7cc32d2efaa36be
- Acceptance subset: endpoint contract probe, deterministic regeneration workset, retry and resume receipt, quarantine receipt, canary dry-run manifest
- Preconditions: the latest package-owned voice job contracts and queue bridge are importable; live endpoint dispatch remains disabled.
- Effects: satisfy evidence requirement: endpoint-safe regeneration runner, satisfy evidence requirement: deterministic resumable queue
- Evidence subset: endpoint contract probe, deterministic regeneration workset, retry and resume receipt, canary dry-run manifest
- Resource class: cpu-medium
- Token class: high
- Estimated tokens: 0
- Resources: cpu-medium
- Merge fate: objective/ABBY-VOICE-G031
- Rejection reasons: none (accepted)
- Missing evidence: endpoint contract probe, deterministic regeneration workset, retry and resume receipt, quarantine receipt, canary dry-run manifest
- Embedding query: Abby IndexTTS endpoint regeneration workset retry resume quarantine dry run
- AST query: VoiceTTSJob, VoiceJobBridge, execute_voice_tts_job, HFSpaceClient
- Surplus group: objective/ABBY-VOICE-G031
- Merge key: regeneration-endpoint-20260728
- Merge family: objective/ABBY-VOICE-G031
- Merge role: aggregate
- Work item count: 3
- Work scope: endpoint_regeneration_runner
- Candidate kind: aggregate
- Acceptance: Implement the package-owned deterministic regeneration workset and resumable runner, prove it with fake-provider integration tests and a read-only endpoint contract probe, and emit a bounded canary dispatch manifest without sending live generation requests.
