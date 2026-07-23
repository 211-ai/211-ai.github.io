# Abby Voice Dataset Schema v2

Status: canonical

Owner: `ABBY-VOICE-G004`

Python API: `ipfs_datasets_py.voice.schema`

## Purpose

Abby voice data is published as four independent, flat dataset configurations:

| Dataset config | Python row | Purpose |
| --- | --- | --- |
| `abby_voice_response_v2` | `AbbyVoiceResponse` | Caller utterances, response text, grounded slot bindings, and response labels |
| `abby_voice_template_v2` | `AbbyVoiceTemplate` | Reusable response frames and their declared slots |
| `abby_voice_audio_v2` | `AbbyVoiceAudio` | Metadata and integrity values for external audio assets |
| `abby_voice_provenance_v2` | `AbbyVoiceProvenance` | Source and transformation lineage for the other three configs |

These configs must be stored as separate JSONL or Parquet files. Runtime
indexes, aggregate manifests, run summaries, normalization dictionaries, and
batch wrappers are not rows and must not appear in any config. This separation
is what lets Arrow and Hugging Face Dataset Viewer use one fixed set of column
types per config.

The contract uses only:

- non-null scalar `string`, `int64`, and `float64` columns;
- explicitly nullable scalar columns; and
- non-null `list[string]` columns, represented as `[]` when empty.

There are no arbitrary metadata objects, union columns, raw audio byte columns,
or lists whose element type varies from row to row.

## Shared rules

Every row carries an exact `schema_version` discriminator equal to its dataset
config name. It also carries a stable type-specific ID, an explicit
`license_id`, and a controlled `consent_status`.

`consent_status` is one of:

- `granted`
- `not_required`
- `unknown`
- `denied`
- `withdrawn`

`unknown` is structurally valid so legacy data can be normalized without
inventing consent. Only `granted` and `not_required` are publishable.
`NOASSERTION` and `UNKNOWN` licenses are also structurally valid for a
quarantine workflow but fail the publication gate.

Other shared invariants are:

- SHA-256 values are the full 64-character lower-case hexadecimal digest.
  Legacy 20-character `textHash` values are identifiers, not integrity hashes.
- Locales are BCP-47-style tags such as `en` or `en-US`.
- Timestamps are timezone-aware RFC 3339 strings. Dates without an offset are
  rejected.
- IDs and list elements are trimmed, non-empty strings. List values are
  ordered and de-duplicated.
- Source CIDs stay in `source_cids`; ordinary legacy source IDs must not be
  relabeled as CIDs.
- `safety_labels` is an extensible `list[string]`, not a comma-delimited scalar.

Call `validate_publishable()` in addition to structural validation before
materializing a release. Publication remains a reviewed action; this schema
does not authorize a remote upload, move, rewrite, or deletion.

## `abby_voice_response_v2`

| Column | Type | Nullable | Meaning |
| --- | --- | --- | --- |
| `schema_version` | string | no | Exact value `abby_voice_response_v2` |
| `response_id` | string | no | Stable response identifier |
| `text` | string | no | Display response with normal written forms |
| `spoken_text` | string | no | Exact normalized text sent to TTS |
| `locale` | string | no | Language/locale of the utterance and response |
| `content_sha256` | string | no | SHA-256 of UTF-8 `spoken_text` |
| `template_id` | string | yes | Template used to render the response |
| `intent` | string | yes | Selected caller intent |
| `utterance` | string | yes | Caller utterance paired with the response |
| `slot_names` | list[string] | no | Bound template slot names |
| `slot_values` | list[string] | no | Values aligned with `slot_names` |
| `slot_source_cids` | list[string] | no | Evidence CID aligned with each bound slot |
| `audio_ids` | list[string] | no | Audio assets for this response |
| `provenance_ids` | list[string] | no | Provenance records for this response |
| `source_cids` | list[string] | no | All grounded source CIDs used by the response |
| `route_labels` | list[string] | no | Router outcomes such as `grounded_211_answer` |
| `service_tags` | list[string] | no | Normalized service taxonomy labels |
| `location_tags` | list[string] | no | Normalized geographic labels |
| `safety_labels` | list[string] | no | Safety and review classifications |
| `license_id` | string | no | SPDX expression or reviewed license identifier |
| `consent_status` | string | no | Controlled consent value |
| `created_at` | string | yes | RFC 3339 creation time |

The three slot lists have identical lengths. A slot without a current evidence
CID is not a grounded factual binding and must not be put into a canonical
response row. Content integrity is calculated over `spoken_text` because that
is the actual semantic input to synthesis.

## `abby_voice_template_v2`

| Column | Type | Nullable | Meaning |
| --- | --- | --- | --- |
| `schema_version` | string | no | Exact value `abby_voice_template_v2` |
| `template_id` | string | no | Stable response-frame identifier |
| `template_text` | string | no | Display template |
| `intent` | string | no | Intent retrieved by GraphRAG/template search |
| `spoken_template` | string | no | TTS-oriented form of the same template |
| `locale` | string | no | Template language/locale |
| `content_sha256` | string | no | SHA-256 of UTF-8 `spoken_template` |
| `slot_names` | list[string] | no | Every declared simple placeholder |
| `required_slot_names` | list[string] | no | Required subset of `slot_names` |
| `factual_slot_names` | list[string] | no | Slots that require current evidence |
| `provenance_ids` | list[string] | no | Template lineage |
| `source_cids` | list[string] | no | Sources that justify the frame/policy |
| `safety_labels` | list[string] | no | Template safety classifications |
| `license_id` | string | no | SPDX expression or reviewed license identifier |
| `consent_status` | string | no | Controlled consent value |
| `created_at` | string | yes | RFC 3339 creation time |

The placeholders in both template strings must exactly equal `slot_names`.
Only simple `{slot_name}` syntax is accepted. Attribute access, item access,
conversions, and format specifications are rejected. A template is a response
plan, not a cached factual answer: example factual slot values do not belong in
this table.

## `abby_voice_audio_v2`

| Column | Type | Nullable | Meaning |
| --- | --- | --- | --- |
| `schema_version` | string | no | Exact value `abby_voice_audio_v2` |
| `audio_id` | string | no | Stable audio asset identifier |
| `spoken_text` | string | no | Text represented by the asset |
| `content_sha256` | string | no | SHA-256 of the external audio bytes |
| `text_sha256` | string | no | SHA-256 of UTF-8 `spoken_text` |
| `locale` | string | no | Spoken locale |
| `uri` | string | yes | Dataset-relative, HTTPS, or `ipfs://` location |
| `ipfs_cid` | string | yes | Direct content CID |
| `response_id` | string | yes | Owning response |
| `template_id` | string | yes | Owning template |
| `segment_kind` | string | no | `response`, `template_shell`, `slot_value`, or `vocabulary` |
| `slot_name` | string | yes | Slot represented by a slot-value asset |
| `slot_value` | string | yes | Value spoken by a slot-value asset |
| `mime_type` | string | no | An `audio/*` media type |
| `codec` | string | yes | Codec name |
| `byte_length` | int64 | yes | Non-negative encoded byte count |
| `duration_ms` | float64 | yes | Finite non-negative duration |
| `sample_rate_hz` | int64 | yes | Positive sample rate |
| `channels` | int64 | yes | Positive channel count |
| `provider` | string | yes | Synthesis provider |
| `model` | string | yes | Synthesis model/version |
| `voice` | string | yes | Voice identifier |
| `provenance_ids` | list[string] | no | Asset lineage |
| `source_cids` | list[string] | no | Grounding/source CIDs |
| `safety_labels` | list[string] | no | Asset safety classifications |
| `license_id` | string | no | SPDX expression or reviewed license identifier |
| `consent_status` | string | no | Speaker/data consent value |
| `created_at` | string | yes | RFC 3339 creation time |

An audio row has at least one location (`uri` or `ipfs_cid`) and at least one
logical subject (`response_id`, `template_id`, or `slot_name`). Raw audio bytes
remain external. A `slot_value` segment requires both `slot_name` and
`slot_value`.

## `abby_voice_provenance_v2`

| Column | Type | Nullable | Meaning |
| --- | --- | --- | --- |
| `schema_version` | string | no | Exact value `abby_voice_provenance_v2` |
| `provenance_id` | string | no | Stable lineage-event identifier |
| `subject_id` | string | no | ID of the response, template, or audio subject |
| `subject_schema_version` | string | no | Subject's exact v2 schema |
| `transformation_name` | string | no | Deterministic transformation name |
| `source_uri` | string | yes | Human-auditable source location |
| `source_revision` | string | yes | Source revision/version |
| `source_sha256` | string | yes | SHA-256 of the source artifact |
| `source_cids` | list[string] | no | Content-addressed source blocks |
| `parent_provenance_ids` | list[string] | no | Earlier lineage events |
| `transformation_version` | string | yes | Transformer implementation version |
| `generated_at` | string | yes | RFC 3339 event time |
| `locale` | string | yes | Source locale when applicable |
| `license_id` | string | no | SPDX expression or reviewed license identifier |
| `consent_status` | string | no | Controlled consent value |
| `consent_id` | string | yes | Reference to an approved consent receipt |
| `safety_labels` | list[string] | no | Lineage/source review labels |

A provenance row has a source location or one or more source CIDs. Its subject
must exist in the corresponding response, template, or audio config when a
bundle is validated.

## Python usage

```python
from ipfs_datasets_py.voice.schema import (
    AbbyVoiceResponse,
    validate_publishable,
)

row = AbbyVoiceResponse(
    response_id="response-safe-handoff",
    utterance="I need help tonight.",
    text="I can help you look for current options.",
    spoken_text="I can help you look for current options.",
    locale="en-US",
    safety_labels=("safe_handoff",),
    license_id="CC-BY-4.0",
    consent_status="not_required",
)

payload = row.to_dict()  # JSON-, Arrow-, and Parquet-safe
validate_publishable(row)
```

`parse_abby_voice_record()` dispatches canonical mappings using the exact
`schema_version`. `validate_records()` adds duplicate-ID detection.
`validate_bundle()` validates cross-config template, audio, provenance, subject,
and parent-provenance references.

Optional integrations are lazy:

```python
from ipfs_datasets_py.voice.schema import (
    ABBY_VOICE_RESPONSE_V2,
    get_huggingface_features,
    get_pyarrow_schema,
)

arrow_schema = get_pyarrow_schema(ABBY_VOICE_RESPONSE_V2)
hf_features = get_huggingface_features(ABBY_VOICE_RESPONSE_V2)
```

Importing `ipfs_datasets_py.voice.schema` does not require `pyarrow` or
`datasets`. The optional package is imported only when its adapter is called.

## Legacy migration boundary

`migrate_v1_record(record, target_schema_version, ...)` migrates exactly one
row and requires the caller to select its target config. It:

- maps known snake_case and camelCase legacy fields;
- computes full semantic hashes and deterministic IDs;
- never mutates the input mapping;
- does not reinterpret truncated `textHash` values as content hashes; and
- rejects aggregate manifests and indexes instead of silently iterating them.

Batch expansion, quarantine reasons, de-duplication, and source inventory are
owned by `ABBY-VOICE-G005`. Parquet materialization is owned by the downstream
curated-dataset goal. Remote Hugging Face migration is plan-only until reviewed
and explicitly approved.

## File layout

A release should use separate config/split paths, for example:

```text
data/
  responses/train-*.parquet
  templates/train-*.parquet
  audio/train-*.parquet
  provenance/train-*.parquet
```

Do not point a response config at a directory that also contains batch JSON,
indexes, manifests, run output, or another canonical config. That layout is the
core Dataset Viewer compatibility guarantee of v2.

## Validation

The authoritative offline validation command is:

```bash
python -m pytest -q ipfs_datasets_py/tests/unit/voice/test_abby_voice_schema.py
```

The focused fixtures are synthetic/public, perform no network access, and make
no remote dataset changes.
