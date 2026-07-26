# ABBY-VOICE-AUTO-026 Objective Goal Gap

Date: 2026-07-26
Fingerprint: b40f59f925a488f03575180069483ee4d405075c
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
Objective heap index: 1
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
Semantic identity: objective-evidence-obligation/v1/f538ae8b1a597dbb828fde0315eee93a433592c181bdbac2ce3ee7674e29aa0c
Acceptance subset: persisted attempt/backoff/lease state, owner heartbeats, IndexTTS/Whisper batch-size-one policy, existing sibling isolation and single-flight receipts, existing `ResourceScheduler` CPU/RAM/disk/GPU/provider backpressure assertions, authoritative evidence map: data/abby_voice/agent_supervisor/discovery/2026-07-26-abby-voice-auto-015-objective-validation-repair.md
Preconditions: objective goal ABBY-VOICE-G016 is schedulable
Effects: satisfy evidence requirement: persisted attempt/backoff/lease state, satisfy evidence requirement: owner heartbeats, satisfy evidence requirement: IndexTTS/Whisper batch-size-one policy, satisfy evidence requirement: existing sibling isolation and single-flight receipts, satisfy evidence requirement: existing `ResourceScheduler` CPU/RAM/disk/GPU/provider backpressure assertions, satisfy evidence requirement: authoritative evidence map: data/abby_voice/agent_supervisor/discovery/2026-07-26-abby-voice-auto-015-objective-validation-repair.md
Evidence subset: persisted attempt/backoff/lease state, owner heartbeats, IndexTTS/Whisper batch-size-one policy, existing sibling isolation and single-flight receipts, existing `ResourceScheduler` CPU/RAM/disk/GPU/provider backpressure assertions, authoritative evidence map: data/abby_voice/agent_supervisor/discovery/2026-07-26-abby-voice-auto-015-objective-validation-repair.md
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

- persisted attempt/backoff/lease state
- owner heartbeats
- IndexTTS/Whisper batch-size-one policy
- existing sibling isolation and single-flight receipts
- existing `ResourceScheduler` CPU/RAM/disk/GPU/provider backpressure assertions
- authoritative evidence map: data/abby_voice/agent_supervisor/discovery/2026-07-26-abby-voice-auto-015-objective-validation-repair.md

## Present Evidence

- `TaskQueue` submit-once identity: ipfs_accelerate_py/ipfs_accelerate_py/p2p_tasks/task_queue.py (embedding:0.32), ipfs_accelerate_py/test/api/test_task_worker_backend_manager_required.py (embedding:0.43), ipfs_accelerate_py/test/api/test_task_worker_backend_manager_routing.py (embedding:0.36)
- expired-lease recovery: ipfs_datasets_py/tests/unit/optimizers/logic_theorem_optimizer/test_global_resource_scheduler.py (embedding:0.32)
- priority-aware atomic claims: ipfs_accelerate_py/ipfs_accelerate_py/agent_supervisor/merge_train.py (embedding:0.32), ipfs_accelerate_py/test/test_voice_job_recovery.py (embedding:0.33), ipfs_datasets_py/security_ir_artifacts/corpora/xaman-app/public-source-assessment-new.json (embedding:0.30)
- and legacy DuckDB migration: artifacts/chainlink-cre-spike/cre-capability-matrix.json (embedding:0.43), docs/adr/WORLD_AID_DUCKDB_STORAGE_ADR.md (embedding:0.54), docs/architecture/REPOSITORY_STRUCTURE.md (embedding:0.39)
- `PeerCapabilityRegistry` plus `TaskOrchestrator` audio capability rejection and safe remote-lease release: ipfs_accelerate_py/test/api/test_agent_supervisor_lease_coordination.py (embedding:0.63), ipfs_accelerate_py/test/api/test_agent_supervisor_task_identity.py (embedding:0.65), ipfs_datasets_py/ipfs_datasets_py/mcp_server/tools/web_archive_tools/__init__.py (embedding:0.65)
- complete audio `ProviderBatchKey` compatibility: ipfs_accelerate_py/test/docs/WEBGPU_BROWSER_COMPATIBILITY.md (embedding:0.31), ipfs_accelerate_py/test/improvements/improved_skillset_generator.py (embedding:0.30), ipfs_datasets_py/docs/guides/processors/PROCESSORS_QUICK_REFERENCE.md (embedding:0.31)

## Suggested Handling

Add the minimum generic reliability fields and semantics missing from TaskQueue, then configure existing resource and provider schedulers for audio.
