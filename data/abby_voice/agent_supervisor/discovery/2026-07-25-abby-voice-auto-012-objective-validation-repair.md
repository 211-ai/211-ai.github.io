# ABBY-VOICE-AUTO-012 Objective Validation Repair

Date: 2026-07-25
Source gap fingerprint: df61ec9b0c07738ff33d4e894d04722a2b2a12f6
Goal id: ABBY-VOICE-G013
Task id: ABBY-VOICE-AUTO-012
Goal title: Build the Abby dataset manager and deterministic audio workset
Objective heap: docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md
Priority: P0
Track: voice-data
Parent goal: ABBY-VOICE-G011
Dependency: ABBY-VOICE-G012
Graph depth: 4
Bundle: abby-voice/dataset-manager
Work scope: goal_subgoal_multi_evidence_batch

## Finding

The objective scan correctly found that G013 named, but did not yet define or
test, `deterministic audio worksets`, `deterministic TTS ASR and validation
work manifests`, and `fuzzy-review quarantine`. The repair is one cohesive
offline data-plane planner. It composes the existing normalizer, strict
four-config schema validator, GraphRAG index, immutable Hugging Face snapshot
and bucket inventory, and shared `ArtifactManifest`; it does not submit or
execute jobs and performs no network or remote writes.

## Repaired evidence map

| Required evidence | Defining evidence | Focused proof |
| --- | --- | --- |
| deterministic audio worksets | `VoiceAudioWorkset` selects only missing, corrupt, stale-policy, and explicit-revalidation subjects and commits the pinned source set, inventory, policy, exact subject, spoken-text hash, audio descriptor, reason, operation, and dependencies to full-hash identities and canonical bytes. | `test_deterministic_tts_asr_and_validation_work_manifests_cover_selection_matrix` reverses subject/audio order and asserts byte-identical worksets, exact selection, reasons, and operations. `test_manager_rebuild_is_byte_identical_and_input_order_independent` proves full-manager rerun stability. |
| deterministic TTS ASR and validation work manifests | `AudioWorkManifest` and `VoiceAudioWorkset` expose separately identified `tts_manifest`, `asr_manifest`, and `validation_manifest` values. Each manifest sorts and deduplicates deterministic work IDs; ASR and validation dependencies bind generated or existing audio without embedding audio bytes. | `test_deterministic_tts_asr_and_validation_work_manifests_cover_selection_matrix` asserts exact per-kind membership, deterministic identities, dependency-safe canonical bytes, and explicit `audio_validation` serialization. |
| fuzzy-review quarantine | `reconcile_legacy_audio_candidates` auto-links only exact canonical subject and normalized spoken-text identity after full SHA-256, byte length, pinned media/magic, and injected decode validation. Fuzzy text, unknown subjects, plural paths, and claimed/inventory hash disagreement receive stable review-only dispositions and never create canonical audio. | `test_fuzzy_and_ambiguous_legacy_candidates_are_review_only_quarantine` covers fuzzy text, plural paths, and subject mismatch. `test_integrity_failures_never_auto_link` covers claimed hash, downloaded hash, media bytes, and decode failures. |
| complete inventory-to-disposition reconciliation | `LegacyAudioReconciliation` enforces unique stable source references. `AbbyVoiceDatasetManagerResult` merges accepted/quarantined normalized rows with every candidate and bucket object into a sorted, unique disposition ledger. | `test_manager_composes_strict_four_config_bundle_and_artifact_evidence` asserts exactly one disposition for the source row, candidate, audio object, and non-audio inventory object. |
| canonical four-config composition and evaluation-support decision | `AbbyVoiceDatasetManager` calls `AbbyVoiceDatasetNormalizer.normalize_sources`, `validate_bundle`, and `SlottedResponseIndex.from_rows`, then describes every canonical payload and plan with `ArtifactManifest`. Evaluation remains a checksummed `support_pending_g018` artifact, not a fifth dataset config. | `test_manager_composes_strict_four_config_bundle_and_artifact_evidence` asserts strict reciprocal validation, GraphRAG bundle identity, the exact response/template/audio/provenance config set, and the pending-G018 evaluation decision. |

## Acceptance assertions

1. Pinned JSON source bytes are rehashed and size-checked before normalization.
2. The existing normalizer and GraphRAG index remain authoritative; the manager
   only composes their results.
3. Exact legacy linking requires canonical subject identity, exact normalized
   spoken text, full inventory and downloaded-byte SHA-256, byte length,
   declared/detected audio media, and successful injected decode validation.
4. Basename/path plurality, truncated or disagreeing hashes, fuzzy text, and
   inferred or mismatched subjects never auto-promote. They remain in the
   stable review/quarantine disposition evidence.
5. The workset is deterministic planning only. Its TTS, ASR, and
   audio-validation manifests contain descriptors, hashes, and dependencies,
   never raw/base64 audio, credentials, timestamps, or arbitrary local paths.
6. Reversing pinned sources, candidates, and inventory objects preserves
   workset bytes, dispositions, GraphRAG CIDs, output payloads, and the
   deterministic `ArtifactManifest`.
7. Canonical responses, templates, audio, and provenance remain the only four
   dataset configs. Evaluation is explicitly checksummed support evidence
   pending G018's `abby_voice_evaluation_v2` schema.

## Validation receipt

Command:

```text
python -m pytest -q ipfs_datasets_py/tests/unit/voice/test_abby_voice_schema.py ipfs_datasets_py/tests/unit/voice/test_abby_voice_normalize.py ipfs_datasets_py/tests/unit/voice/test_abby_voice_graphrag.py ipfs_datasets_py/tests/unit/voice/test_abby_voice_dataset_manager.py
```

Result: PASS — 93 passed, 1 skipped in 3.66 seconds on 2026-07-25.

The skip is the pre-existing optional PyArrow schema test; all 14 focused
dataset-manager tests passed.

## Supervisor and child-goal alignment

This evidence remains aligned with todo vector `95ebae29da44ec43`, merge key
`e9e330f254c6edc8`, merge family `objective/ABBY-VOICE-G013`, and merge role
`aggregate`. No supervisor-generated TODO, vector index, objective graph, or
task-status metadata was manually completed or regenerated; the implementation
daemon remains responsible for rebuilding those artifacts after its validation
gate.

No smaller child goal is needed. Exact legacy linking, fuzzy-review quarantine,
and deterministic TTS/ASR/audio-validation planning manifests form one G013
data-plane planning boundary. G022 remains a duplicate refinement superseded
by G013; G014 owns cross-package job contracts, G015 owns execution, G017 owns
result reconciliation, and G018 owns the eventual evaluation schema and release
construction.
