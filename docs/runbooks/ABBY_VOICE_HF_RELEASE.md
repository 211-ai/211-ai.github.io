# Abby Voice Hugging Face release runbook

This runbook operates the **publish and promote an immutable Hugging Face
release** path owned by `ABBY-VOICE-G021`. It replaces legacy basename-skipping
upload scripts with a digest-aware append-only publisher and a fail-closed
promotion workflow.

Local release construction remains `ABBY-VOICE-G018`
(`AbbyVoiceHFReleaseBuilder` / `validate_abby_voice_hf_release`). This runbook
covers only remote write, verification, canary, and rollback.

## Safety boundary (non-negotiable)

| Rule | Behavior |
| --- | --- |
| Autonomous default | **Dry-run only**. Produce a **dry-run diff and cost receipt**; do not contact a write endpoint. |
| Append-only | Upload under a **new** release id prefix. Never delete, move, or rewrite a legacy object. |
| Path identity | Key uploads by **full relative remote path + SHA-256**. Never skip by basename alone. |
| Mutable refs | Never promote a consumer to `/resolve/main/`, `master`, or `latest`. Pin a commit SHA. |
| Tokens | Never persist tokens in task rows, manifests, logs, receipts, or source control. |
| Promotion | Separate reviewed step after **post-publication verification** and **pinned redownload validation**. |
| Rollback | Restore the previous pinned pointer. **Retain** the failed release (no delete). |

Conflict policy: autonomous work stops after a dry run; no delete, move,
overwrite, mutable-main URL, or pointer promotion occurs without explicit human
approval of the exact manifest, commit operations, credentials scope, and cost
bound.

## Components

| Component | Path | Role |
| --- | --- | --- |
| Publisher | `ipfs_datasets_py/ipfs_datasets_py/huggingface/publisher.py` | `HuggingFaceReleasePublisher`, plan, `HfApi create_commit`, verification, redownload, pointer canary/rollback |
| CLI | `scripts/publish_abby_voice_release.py` | Operator entrypoint; default `--dry-run` |
| Local validator | `ipfs_datasets_py/ipfs_datasets_py/voice/hf_release.py` | `validate_abby_voice_hf_release` (G018) |
| Receipt | `data/abby_voice/releases/publication-receipt.json` | Durable dry-run / publish receipt |
| Manifest input | `data/abby_voice/releases/release-manifest.json` | Signed/reviewed local release identity |

## Dry-run (default autonomous path)

From the repository root:

```bash
python scripts/publish_abby_voice_release.py \
  --manifest data/abby_voice/releases/release-manifest.json \
  --dry-run \
  --print-plan
```

This writes `data/abby_voice/releases/publication-receipt.json` with:

1. deterministic operation list (`add` only) under
   `data/abby_voice_v2/{release_id}/…`;
2. byte totals and estimated cost
   (`upload_bytes * transfer_rate + retained_release_bytes * storage_rate`);
3. plan digest (full SHA-256 of the canonical plan);
4. prohibited operations (`delete`, `move`, `overwrite_legacy`, …);
5. `remote_write_performed: false` and `tokens_persisted: false`.

Focused offline suite:

```bash
python -m pytest -q ipfs_datasets_py/tests/unit/voice/test_abby_voice_hf_publish.py
```

## Human approval record

Before any remote write, a human must approve the **exact** dry-run plan:

```json
{
  "approval_id": "approval-YYYYMMDD-001",
  "approver": "release-operator@example.com",
  "plan_digest": "<64-hex from dry-run receipt>",
  "max_cost_usd": 5.0,
  "max_upload_bytes": 500000000,
  "credentials_scope": "dataset:write:Publicus/211-abby-tts",
  "notes": "Reviewed release-manifest.json and cost receipt"
}
```

Store the approval outside source control if it is operationally sensitive. The
approval JSON must not embed tokens.

## Append-only publish (human-gated)

```bash
export HF_TOKEN=...   # environment only; never pass on argv that is logged
python scripts/publish_abby_voice_release.py \
  --manifest data/abby_voice/releases/release-manifest.json \
  --local-root /path/to/materialized/release \
  --execute \
  --approval-json /secure/path/approval.json
```

The publisher:

1. re-validates local file digests against the plan;
2. builds `CommitOperationAdd` entries for every full remote path;
3. calls injected `HfApi.create_commit`;
4. records the returned **commit SHA** on the receipt.

## Post-publication verification

After the commit returns:

1. inventory each planned remote path at the **returned commit SHA**;
2. compare full SHA-256 and byte length to the plan;
3. fail closed on any mismatch (do not promote).

This is the **post-publication verification** gate. Implementation:
`HuggingFaceReleasePublisher.verify_post_publication`.

## Pinned redownload validation

1. create an **empty** verified cache directory;
2. redownload every planned path by the **pinned commit SHA** (never `main`);
3. rehash and revalidate sizes/digests;
4. optionally re-run `validate_abby_voice_hf_release` on a reconstructed local
   tree when Parquet configs are present.

This is the **pinned redownload validation** gate. Implementation:
`HuggingFaceReleasePublisher.redownload_and_validate_pinned`.

## Canary promotion and rollback

Promotion is a **separate** reviewed step after both verification gates pass:

1. write the runtime release pointer with `canary_percent` in `1..100`;
2. monitor consumer health for the canary window;
3. on success, raise canary to 100% under a second approval if required;
4. on failure, **rollback** to `previous_commit_sha` / `previous_release_id`.

Rollback **retains** the failed release prefix for forensics. It never deletes
the candidate or legacy objects.

Runtime pointer fields (conceptual):

```json
{
  "runtime_release_pointer": true,
  "repository_id": "Publicus/211-abby-tts",
  "release_id": "<release>",
  "commit_sha": "<40-64 hex>",
  "release_prefix": "data/abby_voice_v2/<release>",
  "pointer_path": "runtime/abby_voice_release_pointer.json",
  "previous_commit_sha": "<prior pin>",
  "previous_release_id": "<prior release>",
  "canary_percent": 5
}
```

## Relationship to migration plan (G006)

`docs/data/ABBY_VOICE_HF_MIGRATION_PLAN.md` remains the inventory, layout, and
Dataset Viewer procedure authority. G021 executes the approved transaction
against that layout. The delete plan stays empty.

## Evidence map

Authoritative residual evidence map (full G021 boundary):

`data/abby_voice/agent_supervisor/discovery/2026-07-26-abby-voice-auto-021-objective-validation-repair.md`

Residual scan closure for **post-publication verification** and **pinned
redownload validation** (AUTO-030 subset):

`data/abby_voice/agent_supervisor/discovery/2026-07-26-abby-voice-auto-030-objective-validation-repair.md`

| Evidence term | Where proven |
| --- | --- |
| dry-run diff and cost receipt | `plan_dry_run` / CLI `--dry-run` / publication receipt |
| post-publication verification | `verify_post_publication` + integrated `publish_abby_voice_release` post-commit path + unit tests |
| pinned redownload validation | `redownload_and_validate_pinned` + integrated `publish_abby_voice_release` post-commit path + unit tests |
| append-only commit receipt | `publish_append_only` + `PublicationCommitReceipt` |
| canary and rollback receipt | `canary_promote_pointer` / `rollback_pointer` |
| approval record | `PublicationApproval` required for `--execute` |

After an approved `--execute`, the publisher fail-closes through
post-publication verification (returned commit SHA + digests) and pinned
redownload validation (empty verified cache, pinned SHA only) before the
receipt may claim those evidence flags. Promotion remains a separate reviewed
step.

## Supervisor alignment

Merge family: `objective/ABBY-VOICE-G021`. Bundle: `abby-voice/hf-publication`.
Parallel lane: `abby-voice-release`. No smaller child goal is required for these
three evidence terms; G021 alone owns remote writes and pointer promotion.
Supervisor-generated TODO status remains the daemon’s responsibility.
