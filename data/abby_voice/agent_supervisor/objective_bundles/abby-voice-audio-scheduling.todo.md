# Objective Bundle: abby-voice/audio-scheduling

Source todo: data/abby_voice/agent_supervisor/ABBY_VOICE_ROUTER_TODO.md
Purpose: bundle objective-generated tasks so parallel daemons can work one lane at a time.
Conflict policy: keep edits inside this bundle when possible; use the LLM merge resolver for semantic conflicts.

## ABBY-VOICE-AUTO-015 Implement Abby voice objective: Add idempotent recovery resource admission and provider batching

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: voice-scheduling
- Depends on: ABBY-VOICE-AUTO-014
- Outputs: data/abby_voice/agent_supervisor/discovery, docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md, ipfs_accelerate_py/ipfs_accelerate_py/p2p_tasks/task_queue.py, ipfs_accelerate_py/ipfs_accelerate_py/p2p_tasks/orchestrator.py, ipfs_accelerate_py/ipfs_accelerate_py/p2p_tasks/capability_registry.py, ipfs_accelerate_py/ipfs_accelerate_py/agent_supervisor/provider_batch_scheduler.py, ipfs_accelerate_py/test/test_voice_job_recovery.py
- Validation: python -m pytest -q ipfs_accelerate_py/test/test_voice_job_recovery.py ipfs_accelerate_py/test/api/test_agent_supervisor_provider_batch_scheduler.py ipfs_accelerate_py/test/api/test_agent_supervisor_resource_scheduler.py
- Bundle: abby-voice/audio-scheduling
- Bundle shard: data/abby_voice/agent_supervisor/objective_bundles/abby-voice-audio-scheduling.todo.md
- Bundle strategy: explicit
- Graph parents: ABBY-VOICE-G011
- Graph depth: 4
- Objective heap index: 5
- Parallel lane: abby-voice-scheduling
- Conflict policy: preserve existing text-task behavior and DuckDB compatibility; provider-local retry remains inside the existing Abby adapter while queue retry handles worker loss and exhausted retryable job failures
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/p2p_tasks/task_queue.py, ipfs_accelerate_py/ipfs_accelerate_py/p2p_tasks/orchestrator.py, ipfs_accelerate_py/ipfs_accelerate_py/p2p_tasks/capability_registry.py, ipfs_accelerate_py/ipfs_accelerate_py/agent_supervisor/provider_batch_scheduler.py, ipfs_accelerate_py/test/test_voice_job_recovery.py
- Changed paths:
- AST symbols: TaskQueue, TaskOrchestrator, PeerCapabilityRegistry, ProviderBatchScheduler, ResourceScheduler
- Interfaces: DuckDB TaskQueue, capability registry, ResourceScheduler, ProviderBatchScheduler
- Submodules: ipfs_accelerate_py
- Generated artifacts:
- Allow concurrent with:
- Goal id: ABBY-VOICE-G016
- Canonical task key: task/v1/6d310e2baf15978bf678eabee47f8aacf214149420b00f9a06279285e7c221a3
- Canonical task CID: baguqeeranuyq4k5pcwlyx5ty5k7oi74kvtzbifeuecya7gqge6jilz6cegrq
- Semantic identity: objective-evidence-obligation/v1/1f9de07afe18fd8804b4789f2956e46c60606148655126a33289fb5d1b664267
- Acceptance subset: priority-aware claims, audio capability constraints, provider batch compatibility tests, resource and provider saturation tests
- Preconditions: objective goal ABBY-VOICE-G016 is schedulable
- Effects: satisfy evidence requirement: priority-aware claims, satisfy evidence requirement: audio capability constraints, satisfy evidence requirement: provider batch compatibility tests, satisfy evidence requirement: resource and provider saturation tests
- Evidence subset: priority-aware claims, audio capability constraints, provider batch compatibility tests, resource and provider saturation tests
- Resource class: cpu-medium
- Token class: medium
- Estimated tokens: 0
- Resources: cpu-medium
- Merge fate: objective/ABBY-VOICE-G016
- Rejection reasons: none (accepted)
- Evidence obligation key: objective-evidence-obligation/v1/1f9de07afe18fd8804b4789f2956e46c60606148655126a33289fb5d1b664267
- Missing evidence: priority-aware claims, audio capability constraints, provider batch compatibility tests, resource and provider saturation tests
- Embedding query: DuckDB voice task lease heartbeat retry idempotent GPU resource provider batch singleflight
- AST query: TaskQueue, TaskOrchestrator, PeerCapabilityRegistry, ProviderBatchScheduler, ResourceScheduler
- Surplus group: objective/ABBY-VOICE-G016
- Merge key: 5eb79dd7fa80778b
- Merge family: objective/ABBY-VOICE-G016
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
- Todo vector key: fe4b2ce57d2dd612
- Acceptance: Objective scan filed this gap for ABBY-VOICE-G016. Use evidence in /home/barberb/211-AI/data/abby_voice/agent_supervisor/discovery/2026-07-25-abby-voice-auto-015-objective-gap-7d9fb03c0236.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (priority-aware claims, audio capability constraints, provider batch compatibility tests, resource and provider saturation tests), and keep the supervisor-fed backlog aligned with the objective heap.  Refine the objective heap if the gap needs smaller child goals.
