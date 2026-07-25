# Objective Bundle: abby-voice/hf-release

Source todo: data/abby_voice/agent_supervisor/ABBY_VOICE_ROUTER_TODO.md
Purpose: bundle objective-generated tasks so parallel daemons can work one lane at a time.
Conflict policy: keep edits inside this bundle when possible; use the LLM merge resolver for semantic conflicts.

## ABBY-VOICE-AUTO-018 Implement Abby voice objective: Build and validate deterministic Hugging Face releases

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: voice-data
- Depends on: ABBY-VOICE-AUTO-006, ABBY-VOICE-AUTO-016
- Outputs: data/abby_voice/agent_supervisor/discovery, docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md, ipfs_datasets_py/ipfs_datasets_py/huggingface/release.py, ipfs_datasets_py/ipfs_datasets_py/voice/hf_release.py, ipfs_datasets_py/ipfs_datasets_py/voice/evaluation_schema.py, ipfs_datasets_py/tests/unit/voice/test_abby_voice_hf_release.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/voice/test_abby_voice_hf_release.py tests/voice/test_abby_voice_hf_migration.py
- Bundle: abby-voice/hf-release
- Bundle shard: data/abby_voice/agent_supervisor/objective_bundles/abby-voice-hf-release.todo.md
- Bundle strategy: explicit
- Graph parents: ABBY-VOICE-G011
- Graph depth: 4
- Objective heap index: 8
- Parallel lane: abby-voice-release
- Conflict policy: extract generic atomic Parquet descriptor helpers without copying the SkillCenter builder; manifests and indexes are support artifacts, never mixed into row configs
- Predicted files: ipfs_datasets_py/ipfs_datasets_py/huggingface/release.py, ipfs_datasets_py/ipfs_datasets_py/voice/hf_release.py, ipfs_datasets_py/ipfs_datasets_py/voice/evaluation_schema.py, ipfs_datasets_py/tests/unit/voice/test_abby_voice_hf_release.py
- Changed paths:
- AST symbols: ArtifactManifest, AbbyVoiceHFReleaseBuilder, validate_abby_voice_hf_release, AbbyVoiceEvaluation
- Interfaces: ArtifactManifest, PyArrow voice schemas, SlottedResponseIndex serialization, Hugging Face dataset YAML
- Submodules: ipfs_datasets_py
- Generated artifacts: data/abby_voice/releases/release-manifest.json, data/abby_voice/releases/README.md
- Allow concurrent with:
- Goal id: ABBY-VOICE-G018
- Canonical task key: task/v1/6cc88e1ee6e34ada05cbdbaf6214950c222353f70e4343ac52c47a02edbf330c
- Canonical task CID: baguqeerantei4hxg4nfnubol3oxwefevbqrcgu7xbzbuhlcsyr5af3n7gmga
- Semantic identity: objective-evidence-obligation/v1/86eca39bfb7aeb8c74771af34ff91bc7f4a67ab885be6c3652a1348d7618b519
- Acceptance subset: deterministic release construction, five flat Abby configs including evaluation, sharded ZSTD Parquet descriptors, byte-identical rebuild
- Preconditions: objective goal ABBY-VOICE-G018 is schedulable
- Effects: satisfy evidence requirement: deterministic release construction, satisfy evidence requirement: five flat Abby configs including evaluation, satisfy evidence requirement: sharded ZSTD Parquet descriptors, satisfy evidence requirement: byte-identical rebuild
- Evidence subset: deterministic release construction, five flat Abby configs including evaluation, sharded ZSTD Parquet descriptors, byte-identical rebuild
- Resource class: cpu-medium
- Token class: medium
- Estimated tokens: 0
- Resources: cpu-medium
- Merge fate: objective/ABBY-VOICE-G018
- Rejection reasons: none (accepted)
- Evidence obligation key: objective-evidence-obligation/v1/86eca39bfb7aeb8c74771af34ff91bc7f4a67ab885be6c3652a1348d7618b519
- Missing evidence: deterministic release construction, five flat Abby configs including evaluation, sharded ZSTD Parquet descriptors, byte-identical rebuild
- Embedding query: deterministic Abby Hugging Face Parquet release Dataset Viewer ArtifactManifest GraphRAG index
- AST query: ArtifactManifest, AbbyVoiceHFReleaseBuilder, validate_abby_voice_hf_release, AbbyVoiceEvaluation
- Surplus group: objective/ABBY-VOICE-G018
- Merge key: e2842b7cf318f174
- Merge family: objective/ABBY-VOICE-G018
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
- Todo vector key: 3094616398567711
- Acceptance: Objective scan filed this gap for ABBY-VOICE-G018. Use evidence in /home/barberb/211-AI/data/abby_voice/agent_supervisor/discovery/2026-07-25-abby-voice-auto-018-objective-gap-e21ff415cb45.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (deterministic release construction, five flat Abby configs including evaluation, sharded ZSTD Parquet descriptors, byte-identical rebuild), and keep the supervisor-fed backlog aligned with the objective heap.  Refine the objective heap if the gap needs smaller child goals.
