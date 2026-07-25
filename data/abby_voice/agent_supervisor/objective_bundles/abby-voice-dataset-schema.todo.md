# Objective Bundle: abby-voice/dataset-schema

Source todo: data/abby_voice/agent_supervisor/ABBY_VOICE_ROUTER_TODO.md
Purpose: bundle objective-generated tasks so parallel daemons can work one lane at a time.
Conflict policy: keep edits inside this bundle when possible; use the LLM merge resolver for semantic conflicts.

## ABBY-VOICE-AUTO-003 Implement Abby voice objective: Define the canonical Abby voice dataset schema

- Status: completed
- Completion: manual
- Priority: P0
- Track: voice-data
- Depends on:
- Outputs: data/abby_voice/agent_supervisor/discovery, docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md, ipfs_datasets_py/ipfs_datasets_py/voice/schema.py, ipfs_datasets_py/tests/unit/voice/test_abby_voice_schema.py, docs/data/ABBY_VOICE_DATASET_SCHEMA.md
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/voice/test_abby_voice_schema.py
- Bundle: abby-voice/dataset-schema
- Bundle shard: data/abby_voice/agent_supervisor/objective_bundles/abby-voice-dataset-schema.todo.md
- Bundle strategy: explicit
- Graph parents: ABBY-VOICE-G001
- Graph depth: 1
- Parallel lane: abby-voice-data
- Conflict policy: keep runtime indexes and aggregate manifests out of row files; use stable IDs and nullable scalar or consistently typed list columns
- Predicted files: ipfs_datasets_py/ipfs_datasets_py/voice/schema.py, ipfs_datasets_py/tests/unit/voice/test_abby_voice_schema.py, docs/data/ABBY_VOICE_DATASET_SCHEMA.md
- Changed paths:
- AST symbols: AbbyVoiceResponse, AbbyVoiceTemplate, AbbyVoiceAudio, AbbyVoiceProvenance
- Interfaces: ipfs_datasets_py.voice schema, Hugging Face datasets Arrow and Parquet
- Submodules: ipfs_datasets_py
- Generated artifacts:
- Allow concurrent with:
- Goal id: ABBY-VOICE-G004
- Canonical task key: task/v1/7872dc1dfc73d064545730db55555f0d513a204f2346ff466b52795821288e4f
- Canonical task CID: baguqeerapbznyhp4opigivcxgdnvkvk7bvituicpendp6rtlkj4vqijirzhq
- Missing evidence: objective validation repair
- Embedding query: flat versioned Abby voice dataset schema responses templates audio provenance Hugging Face
- AST query: AbbyVoiceResponse, AbbyVoiceTemplate, AbbyVoiceAudio, AbbyVoiceProvenance
- Surplus group: objective/ABBY-VOICE-G004
- Merge key: 1e4be5cfde01cb32
- Merge family: objective/ABBY-VOICE-G004
- Merge role: validation_gate
- Work item count: 1
- Work scope: objective_validation_repair
- Goal packet:
- Goal packet role:
- Goal packet goals:
- Goal packet task count: 0
- Goal packet work item count: 0
- Candidate kind: validation_gate
- Todo vector key: 1ecf8fc51c97c90e
- Acceptance: Objective scan filed this gap for ABBY-VOICE-G004. Use evidence in /home/barberb/211-AI/data/abby_voice/agent_supervisor/discovery/2026-07-23-abby-voice-auto-003-objective-gap-009172687453.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (objective validation repair), and keep the supervisor-fed backlog aligned with the objective heap.  Refine the objective heap if the gap needs smaller child goals.
