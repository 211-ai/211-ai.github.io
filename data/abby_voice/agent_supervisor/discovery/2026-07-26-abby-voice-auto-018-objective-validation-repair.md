# ABBY-VOICE-AUTO-018 Objective Validation Repair

Date: 2026-07-26
Source gap fingerprint: `e21ff415cb45552960e5c4329109ecd894cad733`
Goal id: `ABBY-VOICE-G018`
Task id: `ABBY-VOICE-AUTO-018`
Goal title: Build and validate deterministic Hugging Face releases
Objective heap: `docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md`
Priority: P0
Track: `voice-data`
Parents: `ABBY-VOICE-G011`
Dependencies: `ABBY-VOICE-G007`, `ABBY-VOICE-G017`
Graph depth: 4
Bundle: `abby-voice/hf-release`
Work scope: `goal_subgoal_multi_evidence_batch`
Implementation status: validated offline on attempt 2 (scope-safe recovery); authoritative daemon completion pending

## Finding

The objective scan correctly found that G018 named, but did not yet define or
test, **deterministic release construction**, **five flat Abby configs including
evaluation**, **sharded ZSTD Parquet descriptors**, and **byte-identical
rebuild**. Present-evidence matches pointed at unrelated legal/SkillCenter docs
rather than a voice-specific release wrapper over shared hashing, sharding, and
validation helpers.

Attempt 1 implemented the four-versus-five config resolution offline, then
failed proposal admission with `path_outside_scope` after mutating package-root
export surfaces outside the frozen task-owned paths:

- `ipfs_datasets_py/ipfs_datasets_py/huggingface/__init__.py` (out of scope)
- `ipfs_datasets_py/ipfs_datasets_py/voice/__init__.py` (out of scope)

Attempt 2 recovers the defining implementation on the authorized modules only.
Callers and tests import defining symbols from the task-owned modules directly;
package-root `__init__.py` re-exports are not required and are not modified.

## Scope-safe authorized paths

| Path | Role |
| --- | --- |
| `ipfs_datasets_py/ipfs_datasets_py/huggingface/release.py` | Generic atomic helpers: `FileDescriptor`, `write_zstd_parquet`, `describe_file`, `shard_sequence`, `validate_zstd_parquet`, `reject_identity_contamination`; re-exports `ArtifactManifest` for AST discoverability |
| `ipfs_datasets_py/ipfs_datasets_py/voice/evaluation_schema.py` | Flat `AbbyVoiceEvaluation` / `abby_voice_evaluation_v2`; `migrate_evaluation_v1` |
| `ipfs_datasets_py/ipfs_datasets_py/voice/hf_release.py` | `AbbyVoiceHFReleaseBuilder`, `validate_abby_voice_hf_release`, `FIVE_FLAT_ABBY_CONFIGS`, GraphRAG support index + sealed release manifest |
| `ipfs_datasets_py/tests/unit/voice/test_abby_voice_hf_release.py` | Offline evidence suite; imports defining modules without package-root export dependency |
| `data/abby_voice/agent_supervisor/discovery/2026-07-26-abby-voice-auto-018-objective-validation-repair.md` | This authoritative evidence map |
| `docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md` | G018 evidence linkage |

Protected `data/abby_voice/agent_supervisor/ABBY_VOICE_ROUTER_TODO.md` was not
modified.

## Repaired evidence map

| Required evidence | Authoritative repository evidence | Validation rule |
| --- | --- | --- |
| deterministic release construction | `AbbyVoiceHFReleaseBuilder` and `validate_abby_voice_hf_release` in `voice/hf_release.py`; generic atomic helpers in `huggingface/release.py`; `DETERMINISTIC_RELEASE_CONSTRUCTION_EVIDENCE_TERM`; focused construction test | Builds from pinned rows and policy write schema-stable ZSTD Parquet, content-addressed descriptors, GraphRAG support index, and a sealed release manifest. Construction re-runs the exhaustive local validator. Identity files reject timestamps, local paths, and mutable `/resolve/main/` URLs. |
| five flat Abby configs including evaluation | `FIVE_FLAT_ABBY_CONFIGS` and dataset YAML emission in `hf_release.py`; flat `AbbyVoiceEvaluation` / `abby_voice_evaluation_v2` in `evaluation_schema.py`; migration-plan YAML already declaring five configs; focused evaluation and release tests | Response, template, audio, provenance, and evaluation each have isolated schema-stable Parquet paths and split mappings. Evaluation is a real Dataset Viewer config, not pending support JSONL. Nested v1 golden fixtures flatten through `migrate_evaluation_v1`. |
| sharded ZSTD Parquet descriptors | `write_zstd_parquet`, `FileDescriptor`, `describe_file`, `shard_sequence`, `validate_zstd_parquet` in `huggingface/release.py`; release builder shard paths `{config}/{split}/{split}-{shard:05d}-of-{total:05d}.parquet`; focused shard tests | Every shard is atomically written with fixed ZSTD settings, verified for magic/schema/row count/compression, and described with relative path, byte length, full SHA-256, content CID, media/schema type, producer/config digest, parents, license/consent, and review/trust metadata where applicable. |
| byte-identical rebuild | Builder sort-and-seal path plus `test_byte_identical_rebuild_is_order_independent` | Two builds from the same pinned source and policy (including reversed input order) produce identical file trees, Parquet bytes, manifest SHA-256, release CID, and GraphRAG graph/index CIDs. |
| authoritative evidence map: data/abby_voice/agent_supervisor/discovery/2026-07-26-abby-voice-auto-018-objective-validation-repair.md | this receipt + `G018_AUTHORITATIVE_EVIDENCE_MAP` / `test_evidence_phrases_are_discoverable_in_implementation_modules` | Residual scan must re-find the four evidence phrases on the authorized paths rather than SkillCenter or legal-data coincidence hits. |

## Acceptance assertions

1. `abby_voice_response_v2`, `abby_voice_template_v2`, `abby_voice_audio_v2`,
   `abby_voice_provenance_v2`, and flat `abby_voice_evaluation_v2` each have
   isolated schema-stable Parquet paths and split mappings.
2. Every file descriptor carries relative path, byte length, SHA-256, content
   CID, media/schema type, producer/config digest, and review/trust metadata
   where applicable.
3. Release validation verifies every descriptor, Parquet
   magic/schema/readability/row count/shard coverage, no duplicate IDs, exact
   bundle references, and GraphRAG graph/index identities.
4. Two builds from the same pinned source and policy are byte-identical and
   contain no timestamps, local paths, mutable `/resolve/main/` URLs,
   truncated hashes, or unordered runtime observations in identity-bearing
   files.
5. Runtime observations remain non-identity; support artifacts (manifests,
   GraphRAG index, README, dataset config JSON) never mix into row-config
   directories.
6. Defining symbols are importable from the task-owned modules without mutating
   package-root `__init__.py` (scope-safe recovery for attempt-1
   `path_outside_scope`).

## Validation receipt

Command:

```text
python -m pytest -q ipfs_datasets_py/tests/unit/voice/test_abby_voice_hf_release.py tests/voice/test_abby_voice_hf_migration.py
```

Result on 2026-07-26 (attempt 2, scope-safe recovery): **passed — 10 passed**.

The gate is offline and uses only local fixtures; it requires no credentials
and performs no network or remote bucket/dataset write.

## Supervisor and child-goal alignment

This evidence remains aligned with merge family `objective/ABBY-VOICE-G018`,
bundle `abby-voice/hf-release`, and parallel lane `abby-voice-release`. No
supervisor-generated TODO, vector index, objective graph, or task-status
metadata was manually completed or regenerated; the implementation daemon
remains responsible for rebuilding those artifacts after its validation gate.

No smaller child goal is needed. Generic descriptor helpers, the evaluation
schema, the voice release builder/validator, and focused proofs form one G018
release-packaging boundary. G019 owns pinned runtime loading; G021 alone owns
publication and promotion.
