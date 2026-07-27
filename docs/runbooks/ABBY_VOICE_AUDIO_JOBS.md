# Abby Voice Audio Jobs Runbook

This runbook operates the distributed dataset-to-voice audio job path owned by
`ABBY-VOICE-G014` through `ABBY-VOICE-G020`. It covers durable DuckDB tasks,
capability and resource admission, worker crash recovery, offline gates, and the
separately **human-approved** **real-provider canary** protocol.

## Control plane vs execution plane

| Plane | Owner | Responsibility |
| --- | --- | --- |
| Voice-data control plane | `ipfs_datasets_py` | Pinned inventory, normalization, GraphRAG indexes, reconciliation, deterministic HF release construction, revision-pinned release loading |
| Audio execution plane | `ipfs_accelerate_py` | `TaskQueue` (DuckDB), worker/mesh claims, capability registry, `ResourceScheduler` admission, provider batching, TTS/ASR/validation execution through `voice_jobs` and `voice_router` |

High-volume audio rows never run through `agent_supervisor` goal queues. They
run through `ipfs_accelerate_py.p2p_tasks.TaskQueue` with content-addressed
`VoiceTTSJob` / `VoiceASRJob` / `VoiceAudioValidationJob` payloads that carry
artifact **descriptors**, never raw audio bytes.

## Offline deterministic fixture

The authoritative offline path is
`tests/voice/test_abby_voice_distributed_pipeline.py`. It is the
**offline deterministic fixture** for G020 and proves:

1. pinned source inventory receipt (synthetic, public-only);
2. canonical response/template rows;
3. DuckDB TTS → audio validation → ASR jobs with complete lineage;
4. reconciliation into reciprocal audio/provenance rows;
5. deterministic local HF release construction via `AbbyVoiceHFReleaseBuilder`;
6. revision-pinned load via `AbbyVoiceReleaseLoader`;
7. grounded `process_voice_turn` with exact factual slots and privacy-safe receipts.

Run from the repository root:

```bash
python -m pytest -q tests/voice/test_abby_voice_distributed_pipeline.py tests/voice/test_abby_voice_safety.py
python benchmarks/bench_abby_voice_router.py --offline --check
```

Conflict policy: offline gates use fakes and tiny public fixtures. They never
contact paid speech services, open mutable remote writes, or embed private
caller audio.

## Job identities and lineage

Every job carries `VoiceJobLineage` with:

- `workset_id`, `manifest_id`, `source_manifest_id`, `work_item_id`
- `subject_id` + `subject_schema_version` (exact workset subject)
- `policy_id` (audio quality / admission policy)
- optional `depends_on_task_ids` (full SHA-256 task ids)
- optional `publication_id` for release-bound work

Task ids are content hashes of the canonical request identity. Re-submitting the
same payload is a replay (`submit_with_outcome` returns `was_replay=True`) and
must not create a second provider call after completion.

## Worker-crash recovery test

The **worker-crash recovery test** (same suite) proves restart safety:

1. Worker A claims a task with a short lease.
2. The process terminates without completing.
3. A new `TaskQueue` handle recovers expired leases (`recover_expired_leases`).
4. Worker B reclaims the same task on attempt N+1.
5. Stale worker A cannot complete the recovered claim.
6. Worker B completes once; re-submitting the identity reuses the completed row
   with **no duplicate provider call** and no conflicting artifact.

Operational recovery checklist:

```text
1. Confirm DuckDB path and that only one writer upgrades schema at a time.
2. Run recover_expired_leases on orchestrator tick (or after worker mesh restart).
3. Inspect attempt, max_attempts, next_attempt_at, lease_until, assigned_worker.
4. Do not delete completed artifacts when a lease expires mid-write; re-run by identity.
5. If maximum attempts are exhausted, leave the row failed with the last error code.
```

## Capability/resource backpressure test

The **capability/resource backpressure test** asserts that admission fails closed:

| Signal | Source | Observed behavior |
| --- | --- | --- |
| Capability mismatch | `PeerCapabilityRegistry.matches_task_requirements` | Unsupported provider/model/voice/codec/locale/device/memory/artifact scheme is not scheduled to that peer |
| Host CPU/RAM/disk/GPU saturation | `ResourceScheduler` | Candidate wave admits zero lanes with `host_*_high_watermark` reasons |
| Provider concurrency/quota/token exhaustion | `ProviderCapacity` + `ResourceScheduler` | Candidate wave admits zero lanes with `provider_*` backpressure counts |

Never override high watermarks to force throughput during production backfill.
Scale workers or reduce wave size instead.

## Failure classes operators must recognize

The offline suite asserts each of the following without network access:

| Class | Expected receipt / queue outcome |
| --- | --- |
| Timeout | Provider raises; job retries per `max_attempts` / backoff |
| Cancellation | Terminal `failed` with `cancelled` / operator error |
| HTTP 429 | Retryable provider error; backoff respects retry-after when present |
| Retryable 5xx | Retryable provider error; circuit may open after consecutive exhaustion |
| Circuit-open | Endpoint skipped until cooldown; text-only or next fallback |
| Corrupt input | Validation fails closed; no linked audio row |
| Quality rejection | Reconciliation quarantines or marks retryable; no silent remap |
| Text-only fallback | Grounded text retained; no false audio hash or base64 |

## Privacy and lineage audit

Ordinary logs, DuckDB task rows, supervisor evidence, and release manifests must
not contain:

- raw caller audio or base64 audio blobs;
- private runtime transcripts;
- API keys, Bearer tokens, or query credentials;
- local filesystem paths to private recordings.

Public dataset ASR validation may retain content-addressed transcript artifacts
under explicit `dataset_asr_validation` purpose only. Runtime STT
(`purpose=runtime_stt`) is ephemeral and never enters a public release.

## Real-provider canary (human-approved only)

A **real-provider canary** is **not** part of the autonomous offline gate. It
requires explicit human approval of:

1. **scope** — exact item count (recommend ≤ 5 public synthetic or already-public rows);
2. **credentials** — short-lived token held only in the operator environment;
3. **cost limit** — hard dollar or request budget;
4. **retention** — write only to a disposable **staging prefix** (never `main`,
   never a production release pointer);
5. **non-sensitive** rows only — no private caller audio, no PII beyond public
   program facts already approved for the corpus.

Suggested canary sequence after offline gates pass:

```text
1. Dry-run job submission with network disabled; confirm identities and receipts.
2. Enable one provider endpoint with the approved cost limit.
3. Run ≤ N non-sensitive rows through TTS → validate → ASR.
4. Capture provider receipts (sanitized), artifact hashes, and reconciliation dispositions.
5. Delete or quarantine the staging prefix per retention policy; do not promote.
```

Any canary that would mutate a production Hugging Face dataset or bucket is
owned by `ABBY-VOICE-G021` publication, not by this audio-jobs path.

## Related evidence

| Artifact | Path |
| --- | --- |
| Distributed offline suite | `tests/voice/test_abby_voice_distributed_pipeline.py` |
| Distributed evaluation report | `docs/reports/ABBY_VOICE_DISTRIBUTED_EVALUATION.md` |
| G020 objective validation repair | `data/abby_voice/agent_supervisor/discovery/2026-07-26-abby-voice-auto-020-objective-validation-repair.md` |
| Objective heap | `docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md` |
| Recovery/admission suite | `ipfs_accelerate_py/test/test_voice_job_recovery.py` |
| Worker/executor suite | `ipfs_accelerate_py/test/test_voice_job_worker.py` |
