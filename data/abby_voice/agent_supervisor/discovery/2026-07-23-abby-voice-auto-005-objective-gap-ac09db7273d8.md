# ABBY-VOICE-AUTO-005 Objective Goal Gap

Date: 2026-07-23
Fingerprint: ac09db7273d86236dab5e381c4170fb93a5c69d5
Goal id: ABBY-VOICE-G005
Goal title: Build deterministic dataset normalization and quality gates
Objective heap: docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md
Priority: P0
Track: voice-data
Parent goals: ABBY-VOICE-G004
Graph depth: 2
Bundle: abby-voice/dataset-normalization
Parallel lane: abby-voice-data
Bundle strategy: explicit
Goal packet: none
Goal packet role: none
Goal packet goals: none
Goal packet task count: 0
Goal packet work item count: 0
Evidence methods: ast
Embedding query: Abby dataset normalize deduplicate quarantine short fragments malformed speech slot fidelity audio availability
AST query: normalize_indextts_spoken_text, deduplicate_voice_response_chunks, build_slotted_response_dag
Conflict policy: normalization must be deterministic and non-destructive; every rejected row receives machine-readable reason codes and source references
Predicted files: ipfs_datasets_py/ipfs_datasets_py/voice/normalize.py, scripts/build_abby_voice_dataset_v2.py, ipfs_datasets_py/tests/unit/voice/test_abby_voice_normalize.py
AST symbols: normalize_indextts_spoken_text, deduplicate_voice_response_chunks, build_slotted_response_dag
Interfaces: Abby voice v2 schemas, existing pregenerated response manifests
Submodules: ipfs_datasets_py
Generated artifacts: none
Allow concurrent with: none

## Goal

Convert the existing manifests and response corpus into canonical rows while detecting low-value vocabulary fragments malformed spoken text duplicates ungrounded claims missing audio and inconsistent slots.

## Missing Evidence

- objective validation repair

## Present Evidence

- deterministic manifest normalizer: docs/211_indextts_precompute_batches/batch-00000-offset-000000.json (ast), docs/211_indextts_precompute_batches/batch-00001-offset-000032.json (ast), docs/211_indextts_precompute_batches/batch-00002-offset-000064.json (ast)
- text and audio deduplication report: artifacts/provekit-release-checks/results.json (ast), docs/2026-36- CHA- Pre-Proposal meeting Q and A.transcript.segments.json (ast), docs/211_indextts_precompute_batches/batch-00000-offset-000000.json (ast)
- spoken-text corruption checks: artifacts/chainlink-zkml-ui-review/review-matrix.json (ast), artifacts/provekit-release-checks/results.json (ast), artifacts/provekit-ui-review/review-matrix.json (ast)
- slot fidelity checks: artifacts/chainlink-cre-spike/cre-capability-matrix.json (ast), artifacts/chainlink-zkml-ui-review/review-matrix.json (ast), artifacts/provekit-release-checks/results.json (ast)
- dataset quality summary with quarantine reasons: artifacts/chainlink-zkml-p2p-design/README.md (ast), artifacts/provekit-ui-signoff/signoff-matrix.json (ast), docs/211_indextts_precompute_batches/batch-00000-offset-000000.json (ast)
- ABBY-VOICE-G005 completion receipt: docs/211_indextts_precompute_batches/batch-00000-offset-000000.json (ast), docs/211_indextts_precompute_batches/batch-00001-offset-000032.json (ast), docs/211_indextts_precompute_batches/batch-00002-offset-000064.json (ast)

## Suggested Handling

Run and repair the objective validation command until it passes, then record the evidence.
