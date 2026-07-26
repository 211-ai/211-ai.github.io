# ABBY-VOICE-AUTO-029 Objective Goal Gap

Date: 2026-07-26
Fingerprint: 0bd1bac1fa8cd58eddcd855c69d5dcc6c8984924
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
Evidence methods: embedding, exact
Embedding query: DuckDB voice task lease heartbeat retry idempotent GPU resource provider batch singleflight
AST query: TaskQueue, TaskOrchestrator, PeerCapabilityRegistry, ProviderBatchScheduler, ResourceScheduler
Conflict policy: preserve existing text-task behavior and DuckDB compatibility; provider-local retry remains inside the existing Abby adapter while queue retry handles worker loss and exhausted retryable job failures
Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/p2p_tasks/task_queue.py, ipfs_accelerate_py/ipfs_accelerate_py/p2p_tasks/orchestrator.py, ipfs_accelerate_py/ipfs_accelerate_py/p2p_tasks/capability_registry.py, ipfs_accelerate_py/ipfs_accelerate_py/agent_supervisor/provider_batch_scheduler.py, ipfs_accelerate_py/test/test_voice_job_recovery.py, data/abby_voice/agent_supervisor/discovery/2026-07-26-abby-voice-auto-015-objective-validation-repair.md, data/abby_voice/agent_supervisor/discovery/2026-07-26-abby-voice-auto-026-objective-validation-repair.md
AST symbols: TaskQueue, TaskOrchestrator, PeerCapabilityRegistry, ProviderBatchScheduler, ResourceScheduler
Interfaces: DuckDB TaskQueue, capability registry, ResourceScheduler, ProviderBatchScheduler
Submodules: ipfs_accelerate_py
Generated artifacts: none
Allow concurrent with: none
Semantic identity: objective-evidence-obligation/v1/23186a4c5af53fb788cae791195c6cdaa85cc393e52aad8b511574cd8e34c135
Acceptance subset: residual scan closure: data/abby_voice/agent_supervisor/discovery/2026-07-26-abby-voice-auto-026-objective-validation-repair.md
Preconditions: objective goal ABBY-VOICE-G016 is schedulable
Effects: satisfy evidence requirement: residual scan closure: data/abby_voice/agent_supervisor/discovery/2026-07-26-abby-voice-auto-026-objective-validation-repair.md
Evidence subset: residual scan closure: data/abby_voice/agent_supervisor/discovery/2026-07-26-abby-voice-auto-026-objective-validation-repair.md
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

- residual scan closure: data/abby_voice/agent_supervisor/discovery/2026-07-26-abby-voice-auto-026-objective-validation-repair.md

## Present Evidence

- `TaskQueue` submit-once identity: ipfs_accelerate_py/ipfs_accelerate_py/p2p_tasks/task_queue.py (embedding:0.34), ipfs_accelerate_py/test/api/test_task_worker_backend_manager_required.py (embedding:0.43), ipfs_accelerate_py/test/api/test_task_worker_backend_manager_routing.py (embedding:0.36)
- persisted attempt/backoff/lease state: ipfs_accelerate_py/ipfs_accelerate_py/p2p_tasks/capability_registry.py (exact), ipfs_accelerate_py/ipfs_accelerate_py/p2p_tasks/orchestrator.py (exact), ipfs_accelerate_py/ipfs_accelerate_py/p2p_tasks/task_queue.py (exact)
- owner heartbeats: ipfs_accelerate_py/ipfs_accelerate_py/p2p_tasks/capability_registry.py (exact), ipfs_accelerate_py/ipfs_accelerate_py/p2p_tasks/orchestrator.py (exact), ipfs_accelerate_py/ipfs_accelerate_py/p2p_tasks/task_queue.py (exact)
- expired-lease recovery: ipfs_accelerate_py/ipfs_accelerate_py/p2p_tasks/task_queue.py (exact), ipfs_accelerate_py/test/test_voice_job_recovery.py (embedding:0.33), ipfs_datasets_py/tests/unit/optimizers/logic_theorem_optimizer/test_global_resource_scheduler.py (embedding:0.32)
- priority-aware atomic claims: ipfs_accelerate_py/ipfs_accelerate_py/agent_supervisor/merge_train.py (embedding:0.32), ipfs_accelerate_py/test/test_voice_job_recovery.py (embedding:0.30)
- and legacy DuckDB migration: docs/adr/WORLD_AID_DUCKDB_STORAGE_ADR.md (embedding:0.54), docs/architecture/REPOSITORY_STRUCTURE.md (embedding:0.39), docs/reports/WORLD_HUMAN_AID_INTEGRATION_AUDIT.md (embedding:0.36)
- `PeerCapabilityRegistry` plus `TaskOrchestrator` audio capability rejection and safe remote-lease release: ipfs_accelerate_py/test/api/test_agent_supervisor_lease_coordination.py (embedding:0.63), ipfs_accelerate_py/test/api/test_agent_supervisor_task_identity.py (embedding:0.65), ipfs_accelerate_py/test/test_voice_job_recovery.py (embedding:0.48)
- complete audio `ProviderBatchKey` compatibility: ipfs_accelerate_py/test/docs/WEBGPU_BROWSER_COMPATIBILITY.md (embedding:0.31), ipfs_accelerate_py/test/improvements/improved_skillset_generator.py (embedding:0.30), ipfs_datasets_py/docs/guides/processors/PROCESSORS_QUICK_REFERENCE.md (embedding:0.31)
- IndexTTS/Whisper batch-size-one policy: ipfs_accelerate_py/ipfs_accelerate_py/agent_supervisor/provider_batch_scheduler.py (exact), ipfs_accelerate_py/test/test_voice_job_recovery.py (exact)
- existing sibling isolation and single-flight receipts: ipfs_accelerate_py/ipfs_accelerate_py/agent_supervisor/provider_batch_scheduler.py (exact), ipfs_accelerate_py/test/test_voice_job_recovery.py (exact)
- existing `ResourceScheduler` CPU/RAM/disk/GPU/provider backpressure assertions: ipfs_accelerate_py/test/test_voice_job_recovery.py (exact)
- authoritative evidence map: data/abby_voice/agent_supervisor/discovery/2026-07-26-abby-voice-auto-015-objective-validation-repair.md: ipfs_accelerate_py/test/test_voice_job_recovery.py (exact)

## Suggested Handling

Add the minimum generic reliability fields and semantics missing from TaskQueue, then configure existing resource and provider schedulers for audio.
