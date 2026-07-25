# ABBY-VOICE-AUTO-009 Objective Goal Gap

Date: 2026-07-23
Fingerprint: a78d6dd48ff4daf6276d57dcc1c2372b5fe30c2d
Goal id: ABBY-VOICE-G006
Goal title: Produce a safe Hugging Face bucket and dataset migration plan
Objective heap: docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md
Priority: P1
Track: voice-data
Parent goals: ABBY-VOICE-G004, ABBY-VOICE-G005
Graph depth: 3
Bundle: abby-voice/huggingface-migration
Parallel lane: abby-voice-data
Bundle strategy: explicit
Goal packet: none
Goal packet role: none
Goal packet goals: none
Goal packet task count: 0
Goal packet work item count: 0
Evidence methods: ast
Embedding query: Hugging Face bucket curated dataset configs splits Parquet migration dry run no delete
AST query: upload_hf_abby_tts_dataset, data_files, configs, list_bucket_tree, sync_bucket
Conflict policy: prohibit remote writes moves and deletes; only emit a local dry-run plan with checksums counts costs and rollback notes for human approval
Predicted files: docs/data/ABBY_VOICE_HF_MIGRATION_PLAN.md, data/abby_voice/huggingface/README.template.md, data/abby_voice/huggingface/migration-plan.json
AST symbols: upload_hf_abby_tts_dataset, data_files, configs, list_bucket_tree, sync_bucket
Interfaces: Publicus/abby-voice bucket, Publicus/211-abby-tts dataset
Submodules: ipfs_datasets_py
Generated artifacts: data/abby_voice/huggingface/migration-plan.json
Allow concurrent with: none

## Goal

Separate mutable run artifacts from curated Dataset Viewer data and prepare a reviewable migration without changing remote state.

## Missing Evidence

- objective validation repair

## Present Evidence

- bucket inventory summary: artifacts/chainlink-zkml-p2p-design/README.md (ast), docs/211_conversation_dag_shards/location__clackamas.json (ast), docs/211_conversation_dag_shards/location__eugene.json (ast)
- proposed canonical prefix layout: /home/barberb/211-AI/ipfs_accelerate_py/ipfs_accelerate_js/test/performance/webgpu_optimizer/run_benchmarks.py (ast), /home/barberb/211-AI/ipfs_accelerate_py/test/run_dashboard_tests.py (ast), docs/211_indextts_precompute_batches/batch-00000-offset-000000.json (ast)
- Hugging Face dataset YAML with separate configs and splits: docs/211_indextts_precompute_batches/batch-00000-offset-000000.json (ast), docs/211_indextts_precompute_batches/batch-00001-offset-000032.json (ast), docs/211_indextts_precompute_batches/batch-00002-offset-000064.json (ast)
- dry-run copy upload and delete plan: docs/211_indextts_precompute_batches/batch-00000-offset-000000.json (ast), docs/211_indextts_precompute_batches/batch-00001-offset-000032.json (ast), docs/211_indextts_precompute_batches/batch-00002-offset-000064.json (ast)
- Dataset Viewer validation procedure: artifacts/chainlink-cre-spike/cre-capability-matrix.json (ast), artifacts/provekit-ui-signoff/signoff-matrix.json (ast), artifacts/world-id-idkit-signoff/pilot-signoff-evidence-index.json (ast)
- ABBY-VOICE-G006 completion receipt: docs/211_indextts_precompute_batches/batch-00000-offset-000000.json (ast), docs/211_indextts_precompute_batches/batch-00001-offset-000032.json (ast), docs/211_indextts_precompute_batches/batch-00002-offset-000064.json (ast)

## Suggested Handling

Run and repair the objective validation command until it passes, then record the evidence.
