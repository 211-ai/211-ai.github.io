# Abby Voice Hugging Face migration plan

Status: review-only plan; no remote operation was performed

Task: `ABBY-VOICE-AUTO-009`
Goal: `ABBY-VOICE-G006`
Date: 2026-07-23

This plan separates mutable preprocessing artifacts from curated Dataset
Viewer data. It is deliberately local and dry-run only. The authoritative
machine-readable form is
[`data/abby_voice/huggingface/migration-plan.json`](../../data/abby_voice/huggingface/migration-plan.json), and the proposed Dataset Card is
[`data/abby_voice/huggingface/README.template.md`](../../data/abby_voice/huggingface/README.template.md).

## Non-negotiable safety boundary

Autonomous workers may not write, move, rewrite, or delete anything in
`hf://buckets/Publicus/abby-voice` or `Publicus/211-abby-tts`. The plan emits a
local inventory/copy manifest and review receipts only. A human approval is
required before a read-only remote inventory, upload, Dataset Viewer
publication, or release-pointer change. The delete plan is intentionally an
empty prohibited operation set.

The legacy `audio/abby-tts/current/` prefix remains available as a rollback
source. New raw work is date- and run-scoped, for example
`raw/runs/{yyyy-mm-dd}/{run_id}/`; a curated release is immutable under
`curated/abby_voice_v2/{release_id}/` in the bucket and
`data/abby_voice_v2/{release_id}/` in the dataset repository.

## Inventory summary and local evidence

The current repository gives us a useful local source manifest, not a remote
bucket inventory:

| Evidence | Value |
| --- | --- |
| Local source | `docs/pregenerated_text_response_manifest.json` |
| Local source SHA-256 | `91103f89fcc12137f1a1603e5fa8cbb9e5922aa978e5c0b8f055b5d7fc1442fe` |
| Local source bytes | 28,602,699 |
| Builder input rows | 13,809 |
| Accepted responses/provenance | 13,779 / 13,779 |
| Quarantined source rows | 30 |
| Missing-audio warnings | 13,779 |
| Checked builder manifest SHA-256 | `6c7fb33fc18515a3ea5ef43d7129c1e4e45c1df6defbd453123219179d9d783c` |

The local command was:

```bash
python scripts/build_abby_voice_dataset_v2.py \
  --check --output-dir /tmp/abby-voice-v2-check
```

Remote object counts, revisions, total bytes, and monetary costs are unknown
until a human-approved `list_bucket_tree` snapshot. The plan records the
receipt fields and cost formula rather than treating local manifest counts as
remote facts. Every source object and emitted Parquet shard will receive a
full SHA-256, byte length, row count, schema version, and release-manifest
entry.

## Canonical layout

The release has five isolated Parquet configurations and explicit splits:

| Config | Dataset Viewer splits | Bucket prefix |
| --- | --- | --- |
| `abby_voice_response_v2` | train, validation, test | `curated/abby_voice_v2/{release_id}/responses/{split}/` |
| `abby_voice_template_v2` | train, validation, test | `curated/abby_voice_v2/{release_id}/templates/{split}/` |
| `abby_voice_audio_v2` | train, validation, test | `curated/abby_voice_v2/{release_id}/audio/{split}/` |
| `abby_voice_provenance_v2` | train, validation, test | `curated/abby_voice_v2/{release_id}/provenance/{split}/` |
| `abby_voice_evaluation_v2` | validation, test | `curated/abby_voice_v2/{release_id}/evaluation/{split}/` |

The corresponding Hugging Face `configs` and `data_files` declarations are
checked into the JSON plan and README template. A config directory may contain
only its schema-stable Parquet shards. Runtime indexes, manifests, batch
wrappers, logs, and run summaries belong under `raw/` or the release
`manifests/` prefix. Audio rows contain metadata and integrity values; raw
audio remains external.

## Dry-run copy, upload, and delete plan

1. Inventory: after approval, call `list_bucket_tree` read-only and write a
   checksum-complete inventory receipt. No remote state changes.
2. Normalize: run the offline v2 builder with `--check-idempotence`; quarantine
   malformed rows and keep missing audio visible under the selected policy.
3. Materialize: write local Parquet shards by config and split, validate the
   fixed schema, cross-config references, consent/license gates, row counts,
   and checksums.
4. Stage: use `upload_hf_abby_tts_dataset` without `--upload` to create a local
   file map and Dataset Card. The map must report copy candidates, existing
   checksum matches, byte totals, and mismatches.
5. Review: describe the `sync_bucket` comparison against a new immutable
   release prefix. It may report additions and mismatches, but it does not
   execute a sync.
6. Delete: zero operations. No legacy object, current prefix, release shard,
   or source manifest may be deleted, moved, overwritten, or force-uploaded.

The exact dry-run commands and approval states are in the JSON plan. Uploading
or changing a dataset pointer requires a signed human receipt containing the
source inventory digest, release digest, row/byte counts, cost estimate, and
rollback target.

## Dataset Viewer validation procedure

Before publication, load every non-empty config/split locally with PyArrow or
`datasets`. Assert the exact `schema_version`, fixed column types, split
isolation, full SHA-256 checksums, row-count reconciliation, provenance
references, and publishable consent/license values from
[`ABBY_VOICE_DATASET_SCHEMA.md`](ABBY_VOICE_DATASET_SCHEMA.md). A local smoke
load must not discover a batch wrapper, index, aggregate manifest, or mixed
legacy row.

After human approval and upload, inspect all five named configs in Dataset
Viewer. Every declared split must load without schema inference errors; Viewer
row counts and config names must match the signed release receipt. Sample
response-to-template, response-to-audio, and response-to-provenance references
and retain the immutable dataset revision, Viewer URL, timestamp, and response
digest. Any failure stops publication and leaves the previous release selected.

## Rollback and cost accounting

Rollback selects the previous approved immutable dataset revision/release
manifest. The failed candidate and all source prefixes remain retained for
forensics; no delete or move is needed. Consumers change revision only after
the operator records both release digests and approval.

Costs are computed only after inventory:

```text
upload_bytes = sum(new_or_mismatched_object.byte_length)
estimated_cost = upload_bytes * transfer_rate
                 + retained_release_bytes * storage_rate
```

Until then, object count, bytes, upload bytes, storage cost, and transfer cost
are `null` in the machine-readable plan. This is an explicit safety property,
not missing work.

## Objective-validation receipt

The objective scan’s missing evidence term was `objective validation repair`.
The authoritative repair receipt is
[`2026-07-23-abby-voice-auto-009-objective-validation-repair.md`](../../data/abby_voice/agent_supervisor/discovery/2026-07-23-abby-voice-auto-009-objective-validation-repair.md).
It maps each required claim—bucket inventory summary, canonical prefix layout,
Dataset Viewer validation, dry-run copy/upload/delete behavior, checksums,
counts, costs, rollback notes, and the G006 completion receipt—to this plan,
the template, and focused offline assertions. The supervisor-fed backlog keeps
G006 in the same `voice-data` lane with parents G004/G005; status regeneration
remains the daemon’s responsibility.
