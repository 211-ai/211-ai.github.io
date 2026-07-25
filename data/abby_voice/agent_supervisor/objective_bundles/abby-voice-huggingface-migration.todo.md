# Objective Bundle: abby-voice/huggingface-migration

Source todo: data/abby_voice/agent_supervisor/ABBY_VOICE_ROUTER_TODO.md
Purpose: bundle objective-generated tasks so parallel daemons can work one lane at a time.
Conflict policy: keep edits inside this bundle when possible; use the LLM merge resolver for semantic conflicts.

## ABBY-VOICE-AUTO-009 Implement Abby voice objective: Produce a safe Hugging Face bucket and dataset migration plan

- Status: completed
- Completion: manual
- Priority: P1
- Track: voice-data
- Depends on:
- Outputs: data/abby_voice/agent_supervisor/discovery, docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md, docs/data/ABBY_VOICE_HF_MIGRATION_PLAN.md, data/abby_voice/huggingface/README.template.md, data/abby_voice/huggingface/migration-plan.json
- Validation: python scripts/build_abby_voice_dataset_v2.py --check --output-dir /tmp/abby-voice-v2-check && test -f data/abby_voice/huggingface/migration-plan.json
- Bundle: abby-voice/huggingface-migration
- Bundle shard: data/abby_voice/agent_supervisor/objective_bundles/abby-voice-huggingface-migration.todo.md
- Bundle strategy: explicit
- Graph parents: ABBY-VOICE-G004, ABBY-VOICE-G005
- Graph depth: 3
- Parallel lane: abby-voice-data
- Conflict policy: prohibit remote writes moves and deletes; only emit a local dry-run plan with checksums counts costs and rollback notes for human approval
- Predicted files: docs/data/ABBY_VOICE_HF_MIGRATION_PLAN.md, data/abby_voice/huggingface/README.template.md, data/abby_voice/huggingface/migration-plan.json
- Changed paths:
- AST symbols: upload_hf_abby_tts_dataset, data_files, configs, list_bucket_tree, sync_bucket
- Interfaces: Publicus/abby-voice bucket, Publicus/211-abby-tts dataset
- Submodules: ipfs_datasets_py
- Generated artifacts: data/abby_voice/huggingface/migration-plan.json
- Allow concurrent with:
- Goal id: ABBY-VOICE-G006
- Canonical task key: task/v1/632309306045625241a576bbdbb99c0854c6d1a1959bed84d9b00b5f3d7524ab
- Canonical task CID: baguqeerammrqsmdaivrfeqnfo255xom4bbkmnunbswn63bgzwafv6plvesvq
- Missing evidence: objective validation repair
- Embedding query: Hugging Face bucket curated dataset configs splits Parquet migration dry run no delete
- AST query: upload_hf_abby_tts_dataset, data_files, configs, list_bucket_tree, sync_bucket
- Surplus group: objective/ABBY-VOICE-G006
- Merge key: 1eedbf8f9889fb5b
- Merge family: objective/ABBY-VOICE-G006
- Merge role: validation_gate
- Work item count: 1
- Work scope: objective_validation_repair
- Goal packet:
- Goal packet role:
- Goal packet goals:
- Goal packet task count: 0
- Goal packet work item count: 0
- Candidate kind: validation_gate
- Todo vector key: ea4fa40f0c683548
- Acceptance: Objective scan filed this gap for ABBY-VOICE-G006. Use evidence in /home/barberb/211-AI/data/abby_voice/agent_supervisor/discovery/2026-07-23-abby-voice-auto-009-objective-gap-a78d6dd48ff4.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (objective validation repair), and keep the supervisor-fed backlog aligned with the objective heap.  Refine the objective heap if the gap needs smaller child goals.
