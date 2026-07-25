# Objective Bundle: abby-voice/dataset-normalization

Source todo: data/abby_voice/agent_supervisor/ABBY_VOICE_ROUTER_TODO.md
Purpose: bundle objective-generated tasks so parallel daemons can work one lane at a time.
Conflict policy: keep edits inside this bundle when possible; use the LLM merge resolver for semantic conflicts.

## ABBY-VOICE-AUTO-005 Implement Abby voice objective: Build deterministic dataset normalization and quality gates

- Status: completed
- Completion: manual
- Priority: P0
- Track: voice-data
- Depends on:
- Outputs: data/abby_voice/agent_supervisor/discovery, docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md, ipfs_datasets_py/ipfs_datasets_py/voice/normalize.py, scripts/build_abby_voice_dataset_v2.py, ipfs_datasets_py/tests/unit/voice/test_abby_voice_normalize.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/voice/test_abby_voice_normalize.py
- Bundle: abby-voice/dataset-normalization
- Bundle shard: data/abby_voice/agent_supervisor/objective_bundles/abby-voice-dataset-normalization.todo.md
- Bundle strategy: explicit
- Graph parents: ABBY-VOICE-G004
- Graph depth: 2
- Parallel lane: abby-voice-data
- Conflict policy: normalization must be deterministic and non-destructive; every rejected row receives machine-readable reason codes and source references
- Predicted files: ipfs_datasets_py/ipfs_datasets_py/voice/normalize.py, scripts/build_abby_voice_dataset_v2.py, ipfs_datasets_py/tests/unit/voice/test_abby_voice_normalize.py
- Changed paths:
- AST symbols: normalize_indextts_spoken_text, deduplicate_voice_response_chunks, build_slotted_response_dag
- Interfaces: Abby voice v2 schemas, existing pregenerated response manifests
- Submodules: ipfs_datasets_py
- Generated artifacts:
- Allow concurrent with:
- Goal id: ABBY-VOICE-G005
- Canonical task key: task/v1/731830fcef31996a47e9f5ff21539f3b023c24c069ae3e96bbc8202141726792
- Canonical task CID: baguqeeraommdb7hpggmwur7j6x7scu47hmbdyjgangxd5fv3zaqccqlsm6ja
- Missing evidence: objective validation repair
- Embedding query: Abby dataset normalize deduplicate quarantine short fragments malformed speech slot fidelity audio availability
- AST query: normalize_indextts_spoken_text, deduplicate_voice_response_chunks, build_slotted_response_dag
- Surplus group: objective/ABBY-VOICE-G005
- Merge key: f51cfe8af230fb32
- Merge family: objective/ABBY-VOICE-G005
- Merge role: validation_gate
- Work item count: 1
- Work scope: objective_validation_repair
- Goal packet:
- Goal packet role:
- Goal packet goals:
- Goal packet task count: 0
- Goal packet work item count: 0
- Candidate kind: validation_gate
- Todo vector key: 60d36afe101f92e5
- Acceptance: Objective scan filed this gap for ABBY-VOICE-G005. Use evidence in /home/barberb/211-AI/data/abby_voice/agent_supervisor/discovery/2026-07-23-abby-voice-auto-005-objective-gap-ac09db7273d8.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (objective validation repair), and keep the supervisor-fed backlog aligned with the objective heap.  Refine the objective heap if the gap needs smaller child goals.
