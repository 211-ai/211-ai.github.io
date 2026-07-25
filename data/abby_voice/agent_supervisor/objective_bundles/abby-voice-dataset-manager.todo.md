# Objective Bundle: abby-voice/dataset-manager

Source todo: data/abby_voice/agent_supervisor/ABBY_VOICE_ROUTER_TODO.md
Purpose: bundle objective-generated tasks so parallel daemons can work one lane at a time.
Conflict policy: keep edits inside this bundle when possible; use the LLM merge resolver for semantic conflicts.

## ABBY-VOICE-AUTO-012 Implement Abby voice objective: Build the Abby dataset manager and deterministic audio workset

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: voice-data
- Depends on: ABBY-VOICE-AUTO-011
- Outputs: data/abby_voice/agent_supervisor/discovery, docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md, ipfs_datasets_py/ipfs_datasets_py/voice/dataset_manager.py, ipfs_datasets_py/ipfs_datasets_py/voice/legacy_sources.py, ipfs_datasets_py/ipfs_datasets_py/voice/workset.py, ipfs_datasets_py/tests/unit/voice/test_abby_voice_dataset_manager.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/voice/test_abby_voice_schema.py ipfs_datasets_py/tests/unit/voice/test_abby_voice_normalize.py ipfs_datasets_py/tests/unit/voice/test_abby_voice_graphrag.py ipfs_datasets_py/tests/unit/voice/test_abby_voice_dataset_manager.py
- Bundle: abby-voice/dataset-manager
- Bundle shard: data/abby_voice/agent_supervisor/objective_bundles/abby-voice-dataset-manager.todo.md
- Bundle strategy: explicit
- Graph parents: ABBY-VOICE-G011
- Graph depth: 4
- Objective heap index: 2
- Parallel lane: abby-voice-data
- Conflict policy: call the existing normalizer and GraphRAG index rather than duplicating their policy; plural legacy audio paths are candidates, not proof; fuzzy matches are review-only
- Predicted files: ipfs_datasets_py/ipfs_datasets_py/voice/dataset_manager.py, ipfs_datasets_py/ipfs_datasets_py/voice/legacy_sources.py, ipfs_datasets_py/ipfs_datasets_py/voice/workset.py, ipfs_datasets_py/tests/unit/voice/test_abby_voice_dataset_manager.py
- Changed paths:
- AST symbols: AbbyVoiceDatasetManager, AbbyVoiceDatasetNormalizer, SlottedResponseIndex, ArtifactManifest, VoiceAudioWorkset
- Interfaces: Abby voice v2 schema, HuggingFaceSnapshot, ArtifactManifest
- Submodules: ipfs_datasets_py
- Generated artifacts: data/abby_voice/normalized/disposition.jsonl, data/abby_voice/normalized/audio-workset.jsonl
- Allow concurrent with:
- Goal id: ABBY-VOICE-G013
- Canonical task key: task/v1/895e3c059d0d9e903e50a04d5b6ed8414e06ca6d44eac5f9e342ab463e66caf6
- Canonical task CID: baguqeerarfpdybm5bwpjapsqubgvw3wyifhanstnitvml6pdikvumptgzl3a
- Semantic identity: objective-evidence-obligation/v1/900713683347da7b56c8a386b6da8ac8a19f377ae1e5a2b83c37bb71f0fb8751
- Acceptance subset: deterministic audio worksets, deterministic TTS ASR and validation work manifests, fuzzy-review quarantine
- Preconditions: objective goal ABBY-VOICE-G013 is schedulable
- Effects: satisfy evidence requirement: deterministic audio worksets, satisfy evidence requirement: deterministic TTS ASR and validation work manifests, satisfy evidence requirement: fuzzy-review quarantine
- Evidence subset: deterministic audio worksets, deterministic TTS ASR and validation work manifests, fuzzy-review quarantine
- Resource class: cpu-medium
- Token class: medium
- Estimated tokens: 0
- Resources: cpu-medium
- Merge fate: objective/ABBY-VOICE-G013
- Rejection reasons: none (accepted)
- Evidence obligation key: objective-evidence-obligation/v1/900713683347da7b56c8a386b6da8ac8a19f377ae1e5a2b83c37bb71f0fb8751
- Missing evidence: deterministic audio worksets, deterministic TTS ASR and validation work manifests, fuzzy-review quarantine
- Embedding query: Abby voice dataset manager normalize reconcile missing audio exact identity workset
- AST query: AbbyVoiceDatasetManager, AbbyVoiceDatasetNormalizer, SlottedResponseIndex, ArtifactManifest, VoiceAudioWorkset
- Surplus group: objective/ABBY-VOICE-G013
- Merge key: e9e330f254c6edc8
- Merge family: objective/ABBY-VOICE-G013
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
- Todo vector key: 95ebae29da44ec43
- Acceptance: Objective scan filed this gap for ABBY-VOICE-G013. Use evidence in /home/barberb/211-AI/data/abby_voice/agent_supervisor/discovery/2026-07-25-abby-voice-auto-012-objective-gap-df61ec9b0c07.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (deterministic audio worksets, deterministic TTS ASR and validation work manifests, fuzzy-review quarantine), and keep the supervisor-fed backlog aligned with the objective heap.  Refine the objective heap if the gap needs smaller child goals.
