# ABBY-VOICE-AUTO-013 Objective Goal Gap

Date: 2026-07-25
Fingerprint: 2141fa5151409156444f362f61025b559d1037b1
Goal id: ABBY-VOICE-G014
Goal title: Define audio job contracts and the datasets-to-accelerate bridge
Objective heap: docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md
Priority: P0
Track: voice-scheduling
Status: todo
Schedulable: true
Review only: false
Parent goals: ABBY-VOICE-G011
Graph depth: 4
Objective heap index: 3
Bundle: abby-voice/audio-job-contracts
Parallel lane: abby-voice-scheduling
Bundle strategy: explicit
Goal packet: none
Goal packet role: none
Goal packet goals: none
Goal packet task count: 0
Goal packet work item count: 0
Evidence methods: embedding
Embedding query: deterministic TTS ASR STT audio validation task contract DuckDB lineage artifact descriptor
AST query: VoiceTTSJob, VoiceASRJob, VoiceAudioValidationJob, VoiceJobResult, submit_voice_workset
Conflict policy: the contract carries immutable URI CID SHA-256 and size descriptors, never audio bytes; use the existing canonical P2P client rather than adding a second queue
Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/voice_jobs/contracts.py, ipfs_datasets_py/ipfs_datasets_py/ml/accelerate_integration/voice_jobs.py, ipfs_accelerate_py/test/test_voice_job_contracts.py, ipfs_datasets_py/tests/unit/ml/test_voice_job_bridge.py
AST symbols: VoiceTTSJob, VoiceASRJob, VoiceAudioValidationJob, VoiceJobResult, submit_voice_workset
Interfaces: ipfs_accelerate_py.p2p_tasks.TaskQueue, ipfs_datasets_py.ml.accelerate_integration, Artifact
Submodules: ipfs_accelerate_py, ipfs_datasets_py
Generated artifacts: none
Allow concurrent with: none
Semantic identity: objective-evidence-obligation/v1/e3265f03d61eb784a8e5d1c682a0446d0b47684116a9e8f0fd505415275b7499
Acceptance subset: lineage propagation, datasets bridge integration tests
Preconditions: objective goal ABBY-VOICE-G014 is schedulable
Effects: satisfy evidence requirement: lineage propagation, satisfy evidence requirement: datasets bridge integration tests
Evidence subset: lineage propagation, datasets bridge integration tests
Dependencies: ABBY-VOICE-G002, ABBY-VOICE-G013
Resource class: cpu-medium
Token class: medium
Estimated tokens: 0
Resources: cpu-medium
Merge fate: objective/ABBY-VOICE-G014
Rejection reasons: none (accepted)

## Goal

Define versioned TTS ASR and audio-validation job contracts and submit them through the existing ipfs_datasets_py accelerate integration into the canonical DuckDB P2P TaskQueue.

## Missing Evidence

- lineage propagation
- datasets bridge integration tests

## Present Evidence

- dependency-light request and result schemas: ipfs_accelerate_py/docs/guides/AGENT_SUPERVISOR_GUIDE.md (embedding:0.35), ipfs_accelerate_py/ipfs_accelerate_py/static/js/mcpp-client.js (embedding:0.54), ipfs_datasets_py/ipfs_datasets_py/static/js/mcpp-client.js (embedding:0.54)
- full-hash deterministic task IDs: docs/specs/CHAINLINK_ZKML_LLM_ROUTER_PROOF_POLICY.md (embedding:0.34), ipfs_accelerate_py/docs/archive/sessions/IMPLEMENTATION_SUMMARY.md (embedding:0.34), ipfs_accelerate_py/docs/guides/p2p/P2P_WORKFLOW_SCHEDULER.md (embedding:0.34)
- submit-once behavior: artifacts/chainlink-zkml-p2p-design/README.md (embedding:0.36), docs/specs/AI_AGENT_CHAT_ACCESSIBILITY_REVIEW.md (embedding:0.40)
- no-audio-in-DuckDB assertions: ipfs_accelerate_py/data/benchmarks/BENCHMARK_TIMING_REPORT_GUIDE.md (embedding:0.30), ipfs_accelerate_py/data/benchmarks/benchmark_with_db_integration.py (embedding:0.36), ipfs_accelerate_py/data/duckdb/core/benchmark_with_db_integration.py (embedding:0.34)

## Suggested Handling

Add a small shared JSON contract and a datasets-side adapter for submit status wait cancel and receipt ingestion.
