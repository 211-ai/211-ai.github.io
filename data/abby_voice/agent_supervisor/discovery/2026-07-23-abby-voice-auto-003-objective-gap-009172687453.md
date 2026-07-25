# ABBY-VOICE-AUTO-003 Objective Goal Gap

Date: 2026-07-23
Fingerprint: 0091726874537b72e42481636ea697183ccdfc2b
Goal id: ABBY-VOICE-G004
Goal title: Define the canonical Abby voice dataset schema
Objective heap: docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md
Priority: P0
Track: voice-data
Parent goals: ABBY-VOICE-G001
Graph depth: 1
Bundle: abby-voice/dataset-schema
Parallel lane: abby-voice-data
Bundle strategy: explicit
Goal packet: none
Goal packet role: none
Goal packet goals: none
Goal packet task count: 0
Goal packet work item count: 0
Evidence methods: ast
Embedding query: flat versioned Abby voice dataset schema responses templates audio provenance Hugging Face
AST query: AbbyVoiceResponse, AbbyVoiceTemplate, AbbyVoiceAudio, AbbyVoiceProvenance
Conflict policy: keep runtime indexes and aggregate manifests out of row files; use stable IDs and nullable scalar or consistently typed list columns
Predicted files: ipfs_datasets_py/ipfs_datasets_py/voice/schema.py, ipfs_datasets_py/tests/unit/voice/test_abby_voice_schema.py, docs/data/ABBY_VOICE_DATASET_SCHEMA.md
AST symbols: AbbyVoiceResponse, AbbyVoiceTemplate, AbbyVoiceAudio, AbbyVoiceProvenance
Interfaces: ipfs_datasets_py.voice schema, Hugging Face datasets Arrow and Parquet
Submodules: ipfs_datasets_py
Generated artifacts: none
Allow concurrent with: none

## Goal

Define a flat versioned dataset contract that ipfs_datasets_py and Hugging Face Dataset Viewer can load without interpreting indexes or manifests as response rows.

## Missing Evidence

- objective validation repair

## Present Evidence

- abby_voice_response_v2 schema: artifacts/provekit-spike/provekit-v1-smoke.json (ast), artifacts/provekit-ui-review/review-matrix.json (ast), docs/211_indextts_precompute_batches/batch-00000-offset-000000.json (ast)
- abby_voice_template_v2 schema: artifacts/provekit-spike/provekit-v1-smoke.json (ast), artifacts/provekit-ui-review/review-matrix.json (ast), docs/211_indextts_precompute_batches/batch-00000-offset-000000.json (ast)
- abby_voice_audio_v2 schema: artifacts/provekit-spike/provekit-v1-smoke.json (ast), artifacts/provekit-ui-review/review-matrix.json (ast), docs/211_indextts_precompute_batches/batch-00000-offset-000000.json (ast)
- abby_voice_provenance_v2 schema: artifacts/provekit-spike/provekit-v1-smoke.json (ast), artifacts/provekit-ui-review/review-matrix.json (ast), docs/211_indextts_precompute_batches/batch-00000-offset-000000.json (ast)
- schema validation and migration fixtures: artifacts/chainlink-cre-spike/cre-capability-matrix.json (ast), artifacts/provekit-spike/provekit-v1-smoke.json (ast), artifacts/provekit-ui-review/review-matrix.json (ast)
- ABBY-VOICE-G004 completion receipt: docs/211_indextts_precompute_batches/batch-00000-offset-000000.json (ast), docs/211_indextts_precompute_batches/batch-00001-offset-000032.json (ast), docs/211_indextts_precompute_batches/batch-00002-offset-000064.json (ast)

## Suggested Handling

Run and repair the objective validation command until it passes, then record the evidence.
