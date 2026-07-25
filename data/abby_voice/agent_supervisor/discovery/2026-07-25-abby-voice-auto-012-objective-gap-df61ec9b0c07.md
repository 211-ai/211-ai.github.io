# ABBY-VOICE-AUTO-012 Objective Goal Gap

Date: 2026-07-25
Fingerprint: df61ec9b0c07738ff33d4e894d04722a2b2a12f6
Goal id: ABBY-VOICE-G013
Goal title: Build the Abby dataset manager and deterministic audio workset
Objective heap: docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md
Priority: P0
Track: voice-data
Status: todo
Schedulable: true
Review only: false
Parent goals: ABBY-VOICE-G011
Graph depth: 4
Objective heap index: 2
Bundle: abby-voice/dataset-manager
Parallel lane: abby-voice-data
Bundle strategy: explicit
Goal packet: none
Goal packet role: none
Goal packet goals: none
Goal packet task count: 0
Goal packet work item count: 0
Evidence methods: embedding
Embedding query: Abby voice dataset manager normalize reconcile missing audio exact identity workset
AST query: AbbyVoiceDatasetManager, AbbyVoiceDatasetNormalizer, SlottedResponseIndex, ArtifactManifest, VoiceAudioWorkset
Conflict policy: call the existing normalizer and GraphRAG index rather than duplicating their policy; plural legacy audio paths are candidates, not proof; fuzzy matches are review-only
Predicted files: ipfs_datasets_py/ipfs_datasets_py/voice/dataset_manager.py, ipfs_datasets_py/ipfs_datasets_py/voice/legacy_sources.py, ipfs_datasets_py/ipfs_datasets_py/voice/workset.py, ipfs_datasets_py/tests/unit/voice/test_abby_voice_dataset_manager.py
AST symbols: AbbyVoiceDatasetManager, AbbyVoiceDatasetNormalizer, SlottedResponseIndex, ArtifactManifest, VoiceAudioWorkset
Interfaces: Abby voice v2 schema, HuggingFaceSnapshot, ArtifactManifest
Submodules: ipfs_datasets_py
Generated artifacts: data/abby_voice/normalized/disposition.jsonl, data/abby_voice/normalized/audio-workset.jsonl
Allow concurrent with: none
Semantic identity: objective-evidence-obligation/v1/900713683347da7b56c8a386b6da8ac8a19f377ae1e5a2b83c37bb71f0fb8751
Acceptance subset: deterministic audio worksets, deterministic TTS ASR and validation work manifests, fuzzy-review quarantine
Preconditions: objective goal ABBY-VOICE-G013 is schedulable
Effects: satisfy evidence requirement: deterministic audio worksets, satisfy evidence requirement: deterministic TTS ASR and validation work manifests, satisfy evidence requirement: fuzzy-review quarantine
Evidence subset: deterministic audio worksets, deterministic TTS ASR and validation work manifests, fuzzy-review quarantine
Dependencies: ABBY-VOICE-G012
Resource class: cpu-medium
Token class: medium
Estimated tokens: 0
Resources: cpu-medium
Merge fate: objective/ABBY-VOICE-G013
Rejection reasons: none (accepted)

## Goal

Compose the existing Abby schema normalizer GraphRAG and ArtifactManifest APIs into one dataset manager that reconciles legacy candidates and emits deterministic missing-or-revalidate audio work.

## Missing Evidence

- deterministic audio worksets
- deterministic TTS ASR and validation work manifests
- fuzzy-review quarantine

## Present Evidence

- canonical normalization: ipfs_datasets_py/tests/unit/logic/ir_core/test_identity.py (embedding:0.41)
- exact legacy adapter: docs/architecture/ABBY_VOICE_ROUTER_ARCHITECTURE.md (embedding:0.43), docs/data/ABBY_VOICE_DATASET_SCHEMA.md (embedding:0.31), docs/reports/WORLD_HUMAN_AID_INTEGRATION_AUDIT.md (embedding:0.31)
- complete inventory-to-disposition ledger: ipfs_datasets_py/docs/implementation/reports/LEGAL_IR_LEGACY_FEATURE_INVENTORY.md (embedding:0.43), ipfs_datasets_py/docs/logic/MASTER_REFACTORING_PLAN_2026.md (embedding:0.34), ipfs_datasets_py/docs/optimizers/TODO_DAEMON_MODULE.md (embedding:0.33)
- canonical four-config bundle: ipfs_accelerate_py/ipfs_accelerate_py/mcp_server/server.py (embedding:0.74), ipfs_datasets_py/ipfs_datasets_py/mcp_server/docs/tools/README.md (embedding:0.62), ipfs_datasets_py/ipfs_datasets_py/processors/__init__.py (embedding:0.33)
- explicit evaluation-support artifact decision: ipfs_accelerate_py/docs/guides/AGENT_SUPERVISOR_GUIDE.md (embedding:0.30), ipfs_accelerate_py/ipfs_accelerate_py/agent_supervisor/formal_plan_conformance.py (embedding:0.31), ipfs_accelerate_py/test/api/test_agent_supervisor_adaptive_resources.py (embedding:0.34)

## Suggested Handling

Replace script-level source handling with a reusable manager that converts pinned sources into canonical rows, quarantine records, ArtifactManifests, and deterministic work specifications.
