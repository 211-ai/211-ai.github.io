# ABBY-VOICE-AUTO-003 Objective Validation Repair

Date: 2026-07-23

Goal id: ABBY-VOICE-G004

Task id: ABBY-VOICE-AUTO-003

Goal title: Define the canonical Abby voice dataset schema

Objective heap: `docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md`

Priority: P0

Track: voice-data

Bundle: abby-voice/dataset-schema

Work scope: objective_validation_repair

Source gap fingerprint: `0091726874537b72e42481636ea697183ccdfc2b`

## Finding

The source objective scan reported the synthetic missing evidence term
`objective validation repair`. It also listed ProveKit smoke output, a ProveKit
UI review matrix, a Chainlink capability matrix, and IndexTTS precompute batch
JSON as present evidence for the four v2 schemas, migration fixtures, and a G004
completion receipt.

Those matches came from unrelated AST tokens and are not accepted as G004
evidence. In particular, an IndexTTS batch wrapper containing `responses`,
normalization dictionaries, run metadata, and aggregate counts is precisely the
heterogeneous shape this objective must keep out of canonical response rows.
The authoritative evidence below points only to defining source, focused tests,
the contract document, and this validation receipt.

## Repaired evidence map

| Required evidence | Authoritative repository evidence | Validation rule |
| --- | --- | --- |
| `abby_voice_response_v2` schema | `AbbyVoiceResponse`, `ABBY_VOICE_RESPONSE_V2`, and the response `SchemaDefinition` in `ipfs_datasets_py/ipfs_datasets_py/voice/schema.py`; response fixtures in `ipfs_datasets_py/tests/unit/voice/test_abby_voice_schema.py` | The exact discriminator is required. Caller utterance, written/spoken response, grounded aligned slots, response/audio/provenance references, full spoken-text hash, locale, license, consent, safety labels, and source CIDs serialize as fixed flat columns. |
| `abby_voice_template_v2` schema | `AbbyVoiceTemplate`, `ABBY_VOICE_TEMPLATE_V2`, and the template definition in `ipfs_datasets_py/ipfs_datasets_py/voice/schema.py`; placeholder/subset tests in the focused test | Display and spoken frames declare the same simple placeholders. Required/factual slots are declared subsets; attribute/index/conversion/format expressions and undeclared slots fail validation. |
| `abby_voice_audio_v2` schema | `AbbyVoiceAudio`, `ABBY_VOICE_AUDIO_V2`, and the audio definition in `ipfs_datasets_py/ipfs_datasets_py/voice/schema.py`; audio integrity, locator, media, numeric, and Parquet tests | Rows contain external location and integrity metadata, never raw audio or a batch wrapper. Full audio/text hashes, a logical subject, controlled segment kind, `audio/*` media type, license, speaker consent, locale, safety, and provenance are enforced. |
| `abby_voice_provenance_v2` schema | `AbbyVoiceProvenance`, `ABBY_VOICE_PROVENANCE_V2`, and the provenance definition in `ipfs_datasets_py/ipfs_datasets_py/voice/schema.py`; provenance and bundle-reference tests | A lineage row identifies a response/template/audio subject, source URI or CIDs, optional full source hash, transformation/version, parents, locale, license, consent receipt/state, and safety labels without arbitrary nested metadata. |
| Flat Hugging Face/Arrow/Parquet contract | `ColumnSpec`, `SchemaDefinition`, `HUGGINGFACE_FEATURE_SPECS`, `get_huggingface_features`, `get_pyarrow_schema`, and `get_arrow_schema` in the schema module; `docs/data/ABBY_VOICE_DATASET_SCHEMA.md`; Arrow/Parquet parameterized tests | Each config has a distinct fixed schema using only strings, nullable scalars, numeric scalars, and non-null `list[string]`. Optional packages load lazily. JSON and Parquet round trips preserve exact discriminators, nulls, and typed empty lists. |
| Schema validation and migration fixtures | Strict row parsing, `validate_records`, `validate_bundle`, `validate_publishable`, deterministic stable-ID helpers, and explicit `migrate_v1_record`/type-specific migrations in the schema module; focused invalid/canonical/legacy fixtures | Cross-schema rows and unknown columns fail. Duplicate IDs and dangling local references fail. Aggregate manifests/indexes and truncated integrity hashes fail. Migration is deterministic and non-mutating; publication refuses unknown/denied/withdrawn consent and unreviewed licensing. |
| ABBY-VOICE-G004 completion receipt | This file plus the G004 acceptance gate in `docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md` | Every claim resolves to defining code, an asserting test, or the canonical contract document. No unrelated artifact or remote bucket state is treated as completion evidence. |

## Acceptance assertions

1. The package exports four immutable typed row classes and four exact schema
   identifiers. The registry never combines them into a heterogeneous union.
2. `to_dict()` emits JSON-safe lists for every list column and `None` only for
   explicitly nullable scalars. Strict parsing refuses schema mismatches,
   unknown columns, null/string list impostors, malformed hashes/locales/times,
   unsafe templates, invalid audio metadata, and incomplete provenance.
3. Full SHA-256 values, stable IDs, licensing, consent, locale, safety labels,
   source CIDs, utterance/response data, response frames, bound slots, external
   audio assets, and lineage all have canonical columns and focused assertions.
4. Bundle validation proves response-to-template/audio/provenance links and
   provenance subjects/parents. Structural validation and publishability are
   separate so uncertain legacy rows can be quarantined without being released.
5. Migration fixtures recompute canonical semantic hashes and IDs without
   mutating legacy input. Aggregate batch wrappers are refused; batch
   normalization remains G005's responsibility.
6. Arrow and Parquet round trips pass offline for all four configs. The Hugging
   Face adapter is lazy; its environment-specific object test skips when the
   optional Hugging Face `datasets` distribution is unavailable.
7. Tests use only synthetic/public values, make no network calls, use no
   credentials, and perform no remote Hugging Face mutation.

## Validation receipt

Command:

```text
python -m pytest -q ipfs_datasets_py/tests/unit/voice/test_abby_voice_schema.py
```

Result recorded on 2026-07-23:

```text
44 passed, 1 skipped in 1.07s
```

The single skip is the optional Hugging Face `Features` object assertion because
the Hugging Face `datasets` distribution is not installed in this environment.
The dependency-free feature specification and all four installed PyArrow and
Parquet round trips passed. There were no failures.

## Supervisor and child-goal alignment

This receipt preserves the supervisor mapping:

- goal `ABBY-VOICE-G004`;
- task `ABBY-VOICE-AUTO-003`;
- bundle `abby-voice/dataset-schema`;
- track `voice-data`;
- priority `P0`;
- validation command
  `python -m pytest -q ipfs_datasets_py/tests/unit/voice/test_abby_voice_schema.py`;
- code output `ipfs_datasets_py/ipfs_datasets_py/voice/schema.py`;
- test output
  `ipfs_datasets_py/tests/unit/voice/test_abby_voice_schema.py`;
- contract output `docs/data/ABBY_VOICE_DATASET_SCHEMA.md`;
- heap output `docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md`; and
- discovery output under `data/abby_voice/agent_supervisor/discovery`.

No child goal is needed for this repair. G004 is the cohesive schema and
validation gate. G005 already owns deterministic batch normalization and
quarantine, G011 owns curated dataset materialization and Dataset Viewer
evidence, and G006 owns the review-only Hugging Face migration plan. Generated
todo/vector metadata is not manually completed or rewritten by this receipt.
