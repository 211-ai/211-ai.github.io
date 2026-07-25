# ABBY-VOICE-AUTO-023 Objective Goal Gap

Date: 2026-07-25
Fingerprint: 687350d0bedd68596d0b638fff6399378286bba4
Goal id: ABBY-VOICE-G012
Goal title: Generalize immutable Hugging Face source snapshots
Objective heap: docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md
Priority: P0
Track: voice-data
Status: todo
Schedulable: true
Review only: false
Parent goals: ABBY-VOICE-G011
Graph depth: 4
Objective heap index: 1
Bundle: abby-voice/hf-sources
Parallel lane: abby-voice-data
Bundle strategy: explicit
Goal packet: none
Goal packet role: none
Goal packet goals: none
Goal packet task count: 0
Goal packet work item count: 0
Evidence methods: ast, embedding, exact
Embedding query: Hugging Face immutable revision bucket inventory content addressed cache Abby voice
AST query: SkillCenterSnapshot, SkillCenterSnapshotCache, HuggingFaceSkillCenterFetcher, HuggingFaceSnapshot, HuggingFaceBucketStore
Conflict policy: extract or wrap generic behavior while keeping the SkillCenter symbols import-compatible; inventory and downloads are read-only; reject branch names such as main and master from canonical receipts
Predicted files: ipfs_datasets_py/ipfs_datasets_py/huggingface/snapshot.py, ipfs_datasets_py/ipfs_datasets_py/huggingface/repository.py, ipfs_datasets_py/ipfs_datasets_py/huggingface/bucket.py, ipfs_datasets_py/ipfs_datasets_py/logic/intent_ir/source_adapters/snapshot.py, ipfs_datasets_py/tests/unit/huggingface/test_voice_source_snapshot.py, ipfs_datasets_py/tests/unit/logic/intent_ir/test_skillcenter_snapshot.py, data/abby_voice/agent_supervisor/discovery/2026-07-25-abby-voice-auto-011-objective-validation-repair.md
AST symbols: SkillCenterSnapshot, SkillCenterSnapshotCache, HuggingFaceSkillCenterFetcher, HuggingFaceSnapshot, HuggingFaceBucketStore
Interfaces: huggingface_hub injected client, hf bucket CLI adapter, Artifact
Submodules: ipfs_datasets_py
Generated artifacts: none
Allow concurrent with: none
Semantic identity: objective-evidence-obligation/v1/0544a515bbfaeede8b2248bf15c319b4b4d95c2bce20cc1ee2d7ae31c884479e
Acceptance subset: `HuggingFaceSnapshot` and `HuggingFaceSnapshotCache` provide the reusable immutable snapshot/cache contract while the existing `SkillCenterSnapshot`, `HuggingFaceBucketStore` produces a canonical inventory digest over path, focused tests reject tampered bytes and mutable refs and prove a verified cache hit performs no fetch or network access, the authoritative evidence map is `data/abby_voice/agent_supervisor/discovery/2026-07-25-abby-voice-auto-011-objective-validation-repair.md`
Preconditions: objective goal ABBY-VOICE-G012 is schedulable
Effects: satisfy evidence requirement: `HuggingFaceSnapshot` and `HuggingFaceSnapshotCache` provide the reusable immutable snapshot/cache contract while the existing `SkillCenterSnapshot`, satisfy evidence requirement: `HuggingFaceBucketStore` produces a canonical inventory digest over path, satisfy evidence requirement: focused tests reject tampered bytes and mutable refs and prove a verified cache hit performs no fetch or network access, satisfy evidence requirement: the authoritative evidence map is `data/abby_voice/agent_supervisor/discovery/2026-07-25-abby-voice-auto-011-objective-validation-repair.md`
Evidence subset: `HuggingFaceSnapshot` and `HuggingFaceSnapshotCache` provide the reusable immutable snapshot/cache contract while the existing `SkillCenterSnapshot`, `HuggingFaceBucketStore` produces a canonical inventory digest over path, focused tests reject tampered bytes and mutable refs and prove a verified cache hit performs no fetch or network access, the authoritative evidence map is `data/abby_voice/agent_supervisor/discovery/2026-07-25-abby-voice-auto-011-objective-validation-repair.md`
Dependencies: ABBY-VOICE-G004, ABBY-VOICE-G005, ABBY-VOICE-G006
Resource class: cpu-medium
Token class: medium
Estimated tokens: 0
Resources: cpu-medium
Merge fate: objective/ABBY-VOICE-G012
Rejection reasons: none (accepted)

## Goal

Reuse the existing SkillCenter immutable snapshot and verified-cache machinery as generic Hugging Face dataset and bucket source adapters for Abby.

## Missing Evidence

- `HuggingFaceSnapshot` and `HuggingFaceSnapshotCache` provide the reusable immutable snapshot/cache contract while the existing `SkillCenterSnapshot`
- `HuggingFaceBucketStore` produces a canonical inventory digest over path
- focused tests reject tampered bytes and mutable refs and prove a verified cache hit performs no fetch or network access
- the authoritative evidence map is `data/abby_voice/agent_supervisor/discovery/2026-07-25-abby-voice-auto-011-objective-validation-repair.md`

## Present Evidence

- `SkillCenterSnapshotCache`: ipfs_datasets_py/docs/guides/IR_FAMILY_OPERATIONS.md (exact), ipfs_datasets_py/ipfs_datasets_py/logic/intent_ir/source_adapters/snapshot.py (ast)
- and `HuggingFaceSkillCenterFetcher` imports remain compatible: docs/architecture/ABBY_VOICE_ROUTER_ARCHITECTURE.md (embedding:0.35), docs/data/ABBY_VOICE_GRAPHRAG.md (embedding:0.37), docs/specs/WORLD_AID_GATE_FIRST_LAUNCHER.md (embedding:0.35)
- `HuggingFaceRepository` records a pinned dataset commit: ipfs_datasets_py/docs/guides/IR_FAMILY_OPERATIONS.md (embedding:0.38)
- size: artifacts/git-migration-20260507/README.md (exact), artifacts/provekit-spike/README.md (exact), artifacts/provekit-spike/provekit-v1-smoke.json (exact)
- full SHA-256: ipfs_accelerate_py/docs/summaries/PHASES_3_5_COMPLETE.md (embedding:0.31), ipfs_accelerate_py/ipfs_accelerate_py/agent_supervisor/supervisor_efficiency_metrics.py (embedding:0.30), ipfs_accelerate_py/ipfs_accelerate_py/mcp_server/mcplusplus/artifacts.py (embedding:0.62)
- ETag: docs/211_conversation_dag_shards/location__clackamas.json (exact), docs/211_conversation_dag_shards/location__eugene.json (exact), docs/211_conversation_dag_shards/location__hillsboro.json (exact)
- and media type: ipfs_accelerate_py/ipfs_accelerate_js/examples/browser/streaming/WebGPUStreamingDemo.html (embedding:0.36), ipfs_accelerate_py/test/WebGPUStreamingDemo.html (embedding:0.36), ipfs_accelerate_py/test/ipfs_accelerate_js/examples/browser/models/hardware_abstracted_clip_example.html (embedding:0.32)

## Suggested Handling

Promote the existing pinned snapshot/cache pattern to a reusable API and add only the missing bucket inventory/fetch adapter.
