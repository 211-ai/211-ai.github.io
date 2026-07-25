# Objective Bundle: abby-voice/hf-sources

Source todo: data/abby_voice/agent_supervisor/ABBY_VOICE_ROUTER_TODO.md
Purpose: bundle objective-generated tasks so parallel daemons can work one lane at a time.
Conflict policy: keep edits inside this bundle when possible; use the LLM merge resolver for semantic conflicts.

## ABBY-VOICE-AUTO-011 Implement Abby voice objective: Generalize immutable Hugging Face source snapshots

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: voice-data
- Depends on: ABBY-VOICE-AUTO-003, ABBY-VOICE-AUTO-005, ABBY-VOICE-AUTO-009
- Outputs: data/abby_voice/agent_supervisor/discovery, docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md, ipfs_datasets_py/ipfs_datasets_py/huggingface/snapshot.py, ipfs_datasets_py/ipfs_datasets_py/huggingface/repository.py, ipfs_datasets_py/ipfs_datasets_py/huggingface/bucket.py, ipfs_datasets_py/tests/unit/huggingface/test_voice_source_snapshot.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/logic/intent_ir/test_skillcenter_snapshot.py ipfs_datasets_py/tests/unit/huggingface/test_voice_source_snapshot.py
- Bundle: abby-voice/hf-sources
- Bundle shard: data/abby_voice/agent_supervisor/objective_bundles/abby-voice-hf-sources.todo.md
- Bundle strategy: explicit
- Graph parents: ABBY-VOICE-G011
- Graph depth: 4
- Objective heap index: 1
- Parallel lane: abby-voice-data
- Conflict policy: extract or wrap generic behavior while keeping the SkillCenter symbols import-compatible; inventory and downloads are read-only; reject branch names such as main and master from canonical receipts
- Predicted files: ipfs_datasets_py/ipfs_datasets_py/huggingface/snapshot.py, ipfs_datasets_py/ipfs_datasets_py/huggingface/repository.py, ipfs_datasets_py/ipfs_datasets_py/huggingface/bucket.py, ipfs_datasets_py/tests/unit/huggingface/test_voice_source_snapshot.py
- Changed paths:
- AST symbols: SkillCenterSnapshot, SkillCenterSnapshotCache, HuggingFaceSkillCenterFetcher, HuggingFaceSnapshot, HuggingFaceBucketStore
- Interfaces: huggingface_hub injected client, hf bucket CLI adapter, Artifact
- Submodules: ipfs_datasets_py
- Generated artifacts:
- Allow concurrent with:
- Goal id: ABBY-VOICE-G012
- Canonical task key: task/v1/003343e110ca2d40ceb5e82f14f1652229169a36b852ff68a5b5eab352cb410e
- Canonical task CID: baguqeeraaazuhyiqziwubtvv5axrj4lfeiurngrwxbjp62ffwxvlguwlieha
- Semantic identity: objective-evidence-obligation/v1/7afac630bc04684f4a6c29d6c32ae593bfacc4734f75748b051522f7e8cbfb22
- Acceptance subset: backward-compatible generic snapshot/cache API, tamper and mutable-ref rejection tests, no-network cache-hit test
- Preconditions: objective goal ABBY-VOICE-G012 is schedulable
- Effects: satisfy evidence requirement: backward-compatible generic snapshot/cache API, satisfy evidence requirement: tamper and mutable-ref rejection tests, satisfy evidence requirement: no-network cache-hit test
- Evidence subset: backward-compatible generic snapshot/cache API, tamper and mutable-ref rejection tests, no-network cache-hit test
- Resource class: cpu-medium
- Token class: medium
- Estimated tokens: 0
- Resources: cpu-medium
- Merge fate: objective/ABBY-VOICE-G012
- Rejection reasons: none (accepted)
- Evidence obligation key: objective-evidence-obligation/v1/7afac630bc04684f4a6c29d6c32ae593bfacc4734f75748b051522f7e8cbfb22
- Missing evidence: backward-compatible generic snapshot/cache API, tamper and mutable-ref rejection tests, no-network cache-hit test
- Embedding query: Hugging Face immutable revision bucket inventory content addressed cache Abby voice
- AST query: SkillCenterSnapshot, SkillCenterSnapshotCache, HuggingFaceSkillCenterFetcher, HuggingFaceSnapshot, HuggingFaceBucketStore
- Surplus group: objective/ABBY-VOICE-G012
- Merge key: dc0532fadbea1e8d
- Merge family: objective/ABBY-VOICE-G012
- Merge role: aggregate
- Work item count: 3
- Work scope: goal_subgoal_multi_evidence_batch
- Goal packet:
- Goal packet role:
- Goal packet goals:
- Goal packet task count: 0
- Goal packet work item count: 0
- Completion goal bindings: {}
- Completion task bindings:
- Candidate kind: aggregate
- Todo vector key: b6b14e94e1870624
- Acceptance: Objective scan filed this gap for ABBY-VOICE-G012. Use evidence in /home/barberb/211-AI/data/abby_voice/agent_supervisor/discovery/2026-07-25-abby-voice-auto-011-objective-gap-d5cfef28e2c8.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (backward-compatible generic snapshot/cache API, tamper and mutable-ref rejection tests, no-network cache-hit test), and keep the supervisor-fed backlog aligned with the objective heap.  Refine the objective heap if the gap needs smaller child goals.
