# ABBY-VOICE-AUTO-015 Objective Goal Gap

Date: 2026-07-25
Fingerprint: 7d9fb03c02362bf52eec0871fe4cd9075a1aded2
Goal id: ABBY-VOICE-G016
Goal title: Add idempotent recovery resource admission and provider batching
Objective heap: docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md
Priority: P0
Track: voice-scheduling
Status: todo
Schedulable: true
Review only: false
Parent goals: ABBY-VOICE-G011
Graph depth: 4
Objective heap index: 5
Bundle: abby-voice/audio-scheduling
Parallel lane: abby-voice-scheduling
Bundle strategy: explicit
Goal packet: none
Goal packet role: none
Goal packet goals: none
Goal packet task count: 0
Goal packet work item count: 0
Evidence methods: embedding
Embedding query: DuckDB voice task lease heartbeat retry idempotent GPU resource provider batch singleflight
AST query: TaskQueue, TaskOrchestrator, PeerCapabilityRegistry, ProviderBatchScheduler, ResourceScheduler
Conflict policy: preserve existing text-task behavior and DuckDB compatibility; provider-local retry remains inside the existing Abby adapter while queue retry handles worker loss and exhausted retryable job failures
Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/p2p_tasks/task_queue.py, ipfs_accelerate_py/ipfs_accelerate_py/p2p_tasks/orchestrator.py, ipfs_accelerate_py/ipfs_accelerate_py/p2p_tasks/capability_registry.py, ipfs_accelerate_py/ipfs_accelerate_py/agent_supervisor/provider_batch_scheduler.py, ipfs_accelerate_py/test/test_voice_job_recovery.py
AST symbols: TaskQueue, TaskOrchestrator, PeerCapabilityRegistry, ProviderBatchScheduler, ResourceScheduler
Interfaces: DuckDB TaskQueue, capability registry, ResourceScheduler, ProviderBatchScheduler
Submodules: ipfs_accelerate_py
Generated artifacts: none
Allow concurrent with: none
Semantic identity: objective-evidence-obligation/v1/1f9de07afe18fd8804b4789f2956e46c60606148655126a33289fb5d1b664267
Acceptance subset: priority-aware claims, audio capability constraints, provider batch compatibility tests, resource and provider saturation tests
Preconditions: objective goal ABBY-VOICE-G016 is schedulable
Effects: satisfy evidence requirement: priority-aware claims, satisfy evidence requirement: audio capability constraints, satisfy evidence requirement: provider batch compatibility tests, satisfy evidence requirement: resource and provider saturation tests
Evidence subset: priority-aware claims, audio capability constraints, provider batch compatibility tests, resource and provider saturation tests
Dependencies: ABBY-VOICE-G015
Resource class: cpu-medium
Token class: medium
Estimated tokens: 0
Resources: cpu-medium
Merge fate: objective/ABBY-VOICE-G016
Rejection reasons: none (accepted)

## Goal

Make distributed voice jobs restart-safe and resource-aware by extending the existing TaskQueue ResourceScheduler and ProviderBatchScheduler rather than creating a new scheduler.

## Missing Evidence

- priority-aware claims
- audio capability constraints
- provider batch compatibility tests
- resource and provider saturation tests

## Present Evidence

- submit-once queue semantics: artifacts/chainlink-zkml-p2p-design/README.md (embedding:0.36), docs/specs/AI_AGENT_CHAT_ACCESSIBILITY_REVIEW.md (embedding:0.39), docs/specs/HMIS_INTEGRATION_THREAT_MODEL.md (embedding:0.32)
- attempt and backoff state: ipfs_accelerate_py/docs/architecture/AGENT_SUPERVISOR_LEANSTRAL_GOAL_DEVELOPMENT.md (embedding:0.32), ipfs_accelerate_py/docs/summaries/PHASES_3_5_COMPLETE.md (embedding:0.35), ipfs_accelerate_py/ipfs_accelerate_py/agent_supervisor/merge_checkpoint.py (embedding:0.30)
- claim lease and heartbeat recovery: docs/adr/WORLD_AID_DUCKDB_STORAGE_ADR.md (embedding:0.47), ipfs_accelerate_py/docs/architecture/AGENT_SUPERVISOR_ARCHITECTURE.md (embedding:0.42), ipfs_accelerate_py/docs/architecture/overview.md (embedding:0.39)

## Suggested Handling

Add the minimum generic reliability fields and semantics missing from TaskQueue, then configure existing resource and provider schedulers for audio.
