# ABBY-VOICE-AUTO-018 Objective Goal Gap

Date: 2026-07-25
Fingerprint: e21ff415cb45552960e5c4329109ecd894cad733
Goal id: ABBY-VOICE-G018
Goal title: Build and validate deterministic Hugging Face releases
Objective heap: docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md
Priority: P0
Track: voice-data
Status: todo
Schedulable: true
Review only: false
Parent goals: ABBY-VOICE-G011
Graph depth: 4
Objective heap index: 8
Bundle: abby-voice/hf-release
Parallel lane: abby-voice-release
Bundle strategy: explicit
Goal packet: none
Goal packet role: none
Goal packet goals: none
Goal packet task count: 0
Goal packet work item count: 0
Evidence methods: embedding
Embedding query: deterministic Abby Hugging Face Parquet release Dataset Viewer ArtifactManifest GraphRAG index
AST query: ArtifactManifest, AbbyVoiceHFReleaseBuilder, validate_abby_voice_hf_release, AbbyVoiceEvaluation
Conflict policy: extract generic atomic Parquet descriptor helpers without copying the SkillCenter builder; manifests and indexes are support artifacts, never mixed into row configs
Predicted files: ipfs_datasets_py/ipfs_datasets_py/huggingface/release.py, ipfs_datasets_py/ipfs_datasets_py/voice/hf_release.py, ipfs_datasets_py/ipfs_datasets_py/voice/evaluation_schema.py, ipfs_datasets_py/tests/unit/voice/test_abby_voice_hf_release.py
AST symbols: ArtifactManifest, AbbyVoiceHFReleaseBuilder, validate_abby_voice_hf_release, AbbyVoiceEvaluation
Interfaces: ArtifactManifest, PyArrow voice schemas, SlottedResponseIndex serialization, Hugging Face dataset YAML
Submodules: ipfs_datasets_py
Generated artifacts: data/abby_voice/releases/release-manifest.json, data/abby_voice/releases/README.md
Allow concurrent with: none
Semantic identity: objective-evidence-obligation/v1/86eca39bfb7aeb8c74771af34ff91bc7f4a67ab885be6c3652a1348d7618b519
Acceptance subset: deterministic release construction, five flat Abby configs including evaluation, sharded ZSTD Parquet descriptors, byte-identical rebuild
Preconditions: objective goal ABBY-VOICE-G018 is schedulable
Effects: satisfy evidence requirement: deterministic release construction, satisfy evidence requirement: five flat Abby configs including evaluation, satisfy evidence requirement: sharded ZSTD Parquet descriptors, satisfy evidence requirement: byte-identical rebuild
Evidence subset: deterministic release construction, five flat Abby configs including evaluation, sharded ZSTD Parquet descriptors, byte-identical rebuild
Dependencies: ABBY-VOICE-G007, ABBY-VOICE-G017
Resource class: cpu-medium
Token class: medium
Estimated tokens: 0
Resources: cpu-medium
Merge fate: objective/ABBY-VOICE-G018
Rejection reasons: none (accepted)

## Goal

Reuse the generic ArtifactManifest and SkillCenter Parquet release patterns to create a deterministic Abby release that Hugging Face Dataset Viewer can load by immutable revision.

## Missing Evidence

- deterministic release construction
- five flat Abby configs including evaluation
- sharded ZSTD Parquet descriptors
- byte-identical rebuild

## Present Evidence

- extracted generic release helpers: ipfs_datasets_py/ipfs_datasets_py/processors/legal_data/docket_dataset.py (embedding:0.33)
- GraphRAG support-index artifact: docs/pregenerated_text_audio_bm25_batches/batch-00176-offset-005632.json (embedding:0.31), docs/pregenerated_text_audio_bm25_batches/batch-00183-offset-005856.json (embedding:0.31), docs/pregenerated_text_audio_bm25_batches/batch-00195-offset-006240.json (embedding:0.31)
- exhaustive local release validator: ipfs_datasets_py/docs/guides/legal_data/HYBRID_LEGAL_REASONING_TODO.md (embedding:0.44), ipfs_datasets_py/ipfs_datasets_py/logic/intent_ir/README.md (embedding:0.32), ipfs_datasets_py/security_ir_artifacts/corpora/xaman-app/native-vault/rekey-state-fuzz-report.json (embedding:0.34)

## Suggested Handling

Resolve the documented four-versus-five config mismatch and build a voice-specific release wrapper over shared hashing sharding and validation helpers.
