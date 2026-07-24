---
license: CC-BY-4.0
pretty_name: Abby Voice v2
task_categories:
- text-to-speech
- automatic-speech-recognition
language:
- en
configs:
- config_name: abby_voice_response_v2
  data_files:
  - split: train
    path: data/abby_voice_v2/{release_id}/responses/train-*.parquet
  - split: validation
    path: data/abby_voice_v2/{release_id}/responses/validation-*.parquet
  - split: test
    path: data/abby_voice_v2/{release_id}/responses/test-*.parquet
- config_name: abby_voice_template_v2
  data_files:
  - split: train
    path: data/abby_voice_v2/{release_id}/templates/train-*.parquet
  - split: validation
    path: data/abby_voice_v2/{release_id}/templates/validation-*.parquet
  - split: test
    path: data/abby_voice_v2/{release_id}/templates/test-*.parquet
- config_name: abby_voice_audio_v2
  data_files:
  - split: train
    path: data/abby_voice_v2/{release_id}/audio/train-*.parquet
  - split: validation
    path: data/abby_voice_v2/{release_id}/audio/validation-*.parquet
  - split: test
    path: data/abby_voice_v2/{release_id}/audio/test-*.parquet
- config_name: abby_voice_provenance_v2
  data_files:
  - split: train
    path: data/abby_voice_v2/{release_id}/provenance/train-*.parquet
  - split: validation
    path: data/abby_voice_v2/{release_id}/provenance/validation-*.parquet
  - split: test
    path: data/abby_voice_v2/{release_id}/provenance/test-*.parquet
- config_name: abby_voice_evaluation_v2
  data_files:
  - split: validation
    path: data/abby_voice_v2/{release_id}/evaluation/validation-*.parquet
  - split: test
    path: data/abby_voice_v2/{release_id}/evaluation/test-*.parquet
---

# Abby Voice v2

This is the reviewable Dataset Card template for the canonical Abby voice
release. Replace `{release_id}` only after the local normalization, Parquet,
checksum, and Dataset Viewer preflight receipts pass.

## Safety and publication boundary

This template describes a planned release. It does not authorize a Hugging
Face upload, bucket sync, move, rewrite, or delete. The mutable source bucket
(`hf://buckets/Publicus/abby-voice`) and legacy dataset repository
(`Publicus/211-abby-tts`) remain retained and read-only. A human must approve a
signed inventory, release manifest, and dry-run copy/upload receipt before
publication.

Raw run artifacts belong under date- and run-scoped prefixes such as
`raw/runs/{yyyy-mm-dd}/{run_id}/`. Curated Parquet belongs under an immutable
release prefix. Indexes, manifests, batch wrappers, logs, and run summaries
must stay outside config directories.

## Configurations and splits

The five configurations are intentionally separate so Hugging Face Dataset
Viewer sees one stable Arrow schema per config:

| Config | Splits | Contract |
| --- | --- | --- |
| `abby_voice_response_v2` | train, validation, test | `AbbyVoiceResponse` rows |
| `abby_voice_template_v2` | train, validation, test | `AbbyVoiceTemplate` rows |
| `abby_voice_audio_v2` | train, validation, test | `AbbyVoiceAudio` metadata; audio remains external |
| `abby_voice_provenance_v2` | train, validation, test | `AbbyVoiceProvenance` lineage |
| `abby_voice_evaluation_v2` | validation, test | synthetic/public safety and quality cases |

Each `data_files` path points only to Parquet shards for its named config and
split. Do not place JSON manifests, indexes, heterogeneous legacy records, or
batch output beside those shards.

## Reproducibility and grounding

Every release carries a SHA-256 manifest with source inventory revision, byte
lengths, row counts, schema versions, and split counts. Response content hashes
are computed over normalized spoken text; audio hashes cover the complete
external audio bytes. Provenance rows retain source locations and source CIDs.
Factual slots must bind to current cited evidence, and `unknown` consent or
`NOASSERTION` licensing remains non-publishable until reviewed.

## Validation checklist

1. Run the offline builder with `--check --check-idempotence`.
2. Materialize and validate each Parquet config with the v2 schema contract.
3. Confirm counts, checksums, references, consent, license, and split
   isolation in the release receipt.
4. Load every non-empty split locally, then inspect every config in Dataset
   Viewer at the approved immutable revision.
5. Retain the Dataset Viewer response digest and release manifest before
   changing any consumer revision.

Rollback selects the previous approved immutable release or dataset revision.
It never deletes or rewrites source objects or a published release.
