# ABBY-VOICE-AUTO-005 Objective Validation Repair

Date: 2026-07-23

Goal id: ABBY-VOICE-G005

Task id: ABBY-VOICE-AUTO-005

Goal title: Build deterministic dataset normalization and quality gates

Objective heap: `docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md`

Priority: P0

Track: voice-data

Parent goal: ABBY-VOICE-G004

Graph depth: 2

Bundle: abby-voice/dataset-normalization

Work scope: objective_validation_repair

Source gap fingerprint: `ac09db7273d86236dab5e381c4170fb93a5c69d5`

## Finding

The source objective scan reported the synthetic missing evidence term
`objective validation repair`. Its present-evidence section attributed the
normalizer, de-duplication report, corruption checks, slot checks, quality
summary, and G005 completion receipt to IndexTTS batch JSON and unrelated
ProveKit, Chainlink, transcript, and review-matrix artifacts.

Those are AST/token-coincidence matches, not G005 evidence. Batch JSON is input
to normalization, and the unrelated release/review artifacts neither define nor
assert the Abby dataset policy. This receipt supersedes that mapping without
altering the source gap report.

## Repaired evidence map

| Required evidence | Authoritative repository evidence | Validation rule |
| --- | --- | --- |
| Deterministic manifest normalizer | `AbbyVoiceDatasetNormalizer`, `normalize_manifest`, `deterministic_split`, canonical JSON/source hashing, and stable provenance construction in `ipfs_datasets_py/ipfs_datasets_py/voice/normalize.py`; offline builder in `scripts/build_abby_voice_dataset_v2.py`; order/non-mutation, split, builder, and rerun assertions in `ipfs_datasets_py/tests/unit/voice/test_abby_voice_normalize.py` | Legacy wrappers/lists and canonical rows produce sorted v2 configs. Stable IDs, source references, provenance, splits, reports, checksums, and output bytes do not depend on input order, array positions, clocks, randomness, Python hashes, or output directory. Input mappings/files remain byte-for-byte unchanged. |
| Text and audio de-duplication report | `normalized_text_identity`, response-group survivor/merge logic, audio SHA-256 grouping, `DuplicateLedgerEntry`, and `deduplicate_voice_response_chunks` in the normalizer; text/audio duplicate tests in the focused suite | Unicode/whitespace/case-normalized spoken identity chooses one deterministic response survivor and merges set metadata in sorted order. Actual audio-byte SHA-256 chooses one audio survivor. Every removed source receives a duplicate reason and ledger edge; counts reconcile in the quality report. |
| Spoken-text corruption checks | dependency-light `normalize_indextts_spoken_text` plus `_spoken_quality_issues`; deterministic/idempotence, empty, empty-smart-quote, residual corruption, and source-aware low-value vocabulary fixtures | TTS normalization repairs Unicode, whitespace, markup/link, phone, 211, and 911 forms. Empty/punctuation-only text, control/replacement characters, empty quoted values, residual markup/placeholders, repeated corruption, oversized speech, and useless BM25-only fragments receive stable reason codes without rejecting meaningful short safety or slot vocabulary. |
| Slot fidelity checks | `_extract_slots`, template construction through the strict G004 schema, factual-claim grounding gate, and focused aligned/misaligned slot, placeholder, and grounding assertions | Slot name/value/source-CID columns preserve order and must align; names are unique/non-empty, values are present in source text, source bindings are non-empty, template placeholders equal declarations, and factual claims require explicit source/evidence references. Opaque legacy source IDs can prove source presence but are never relabeled as IPFS CIDs. |
| Dataset quality summary with quarantine reasons | `QualityIssue`, `QuarantineReason`, `QuarantineRecord`, `NormalizationResult.quality_summary`, local artifact rendering/checksums, and quality/reconciliation/builder tests | Every rejected JSON-safe source value is retained with its complete digest, stable source reference, sorted reason codes, field diagnostics, and optional candidate. Configurable missing audio is a warning or strict quarantine. Summary maps, rows, ledgers, and files are stably sorted; local writes are atomic and remote state is untouched. |
| ABBY-VOICE-G005 completion receipt | this file and the G005 acceptance gate in `docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md` | Each G005 claim resolves to defining code and an offline focused assertion. No generated batch, unrelated project artifact, or remote bucket state is accepted as completion evidence. |

## Acceptance assertions

The focused suite proves all of the following:

1. speech normalization is deterministic, idempotent, and strips or verbalizes
   corpus constructs that are unsafe for IndexTTS;
2. input order changes neither canonical rows nor quarantine, provenance,
   de-duplication, split, or report evidence;
3. source objects and source files are never modified;
4. source references are based on a stable escaped legacy ID or complete row
   digest rather than an array offset;
5. duplicate spoken text has one deterministic survivor, sorted metadata merge,
   duplicate ledger, quarantine source, and reason code;
6. duplicate audio is keyed by locally verified full byte SHA-256, while a
   declared hash mismatch is quarantined;
7. empty, malformed, low-value, ungrounded, missing-audio, hash-mismatch, and
   inconsistent-slot/template cases are covered by distinct stable codes;
8. low-value detection is source-aware and retains a compositional single-word
   slot such as a city name;
9. grounded slots preserve name/value/source order and pass the canonical G004
   bundle validator;
10. missing audio is observable in permissive builds and rejects the response
    when the strict policy is enabled;
11. response/audio/provenance members of a content family receive the same
    deterministic split;
12. chunk de-duplication and the normalization-time slotted relationship DAG
    have deterministic IDs, counts, nodes, and edges;
13. unknown wrappers and non-mapping rows are quarantined without crashing;
14. quality counts and reason maps are stable and reconciled; and
15. two independent offline CLI builds are byte-identical, validate their
    checksums/relationships, and preserve the input file.

All fixtures are synthetic or explicitly public metadata. Tests make no network
call, use no credentials, load no model, and mutate no remote dataset.

## Validation receipt

Exact command:

```text
python -m pytest -q ipfs_datasets_py/tests/unit/voice/test_abby_voice_normalize.py
```

Result recorded on 2026-07-23:

```text
16 passed in 0.61s
```

Canonical-schema regression command:

```text
python -m pytest -q ipfs_datasets_py/tests/unit/voice/test_abby_voice_schema.py ipfs_datasets_py/tests/unit/voice/test_abby_voice_normalize.py
```

Result:

```text
60 passed, 1 skipped in 1.39s
```

The skip is the existing optional Hugging Face `datasets.Features` assertion;
the dependency-free schema and normalization tests all passed. `ruff check`,
`python -m py_compile`, and `git diff --check` also passed for the changed
Python sources.

The offline real-corpus check also completed successfully:

```text
python scripts/build_abby_voice_dataset_v2.py \
  --output-dir <temporary-directory> --check --check-idempotence
```

It deterministically accepted 13,779 response rows and emitted 13,779
provenance rows, quarantined 30 malformed/low-quality sources, and recorded
13,779 missing-audio warnings because the checked-in aggregate is a text
manifest whose referenced generated audio is not present in this worktree.
No remote location was read or modified.

## Supervisor and child-goal alignment

This repair preserves the supervisor-fed identity:

- task `ABBY-VOICE-AUTO-005` and goal `ABBY-VOICE-G005`;
- parent `ABBY-VOICE-G004`, graph depth 2, bundle
  `abby-voice/dataset-normalization`, track `voice-data`, and P0 priority;
- merge family `objective/ABBY-VOICE-G005`, merge role `validation_gate`, and
  work scope `objective_validation_repair`;
- todo vector key `60d36afe101f92e5` and merge key `f51cfe8af230fb32`;
- exact focused validation command shown above;
- implementation outputs
  `ipfs_datasets_py/ipfs_datasets_py/voice/normalize.py`,
  `scripts/build_abby_voice_dataset_v2.py`, and
  `ipfs_datasets_py/tests/unit/voice/test_abby_voice_normalize.py`;
- planning output `docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md`; and
- this discovery receipt.

No supervisor-generated todo/vector metadata was manually completed or
rewritten. The implementation daemon owns status regeneration after merge.
No smaller child goal is required: G005 owns normalization, de-duplication,
quality/quarantine evidence, and the focused gate; G011 owns immutable source
inventory, full Parquet/Dataset Viewer materialization, and release
idempotence; G006 owns the review-only remote migration plan; and G007 owns
GraphRAG ingestion and retrieval.
