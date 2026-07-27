# Abby Voice Distributed Pipeline Evaluation

Date: 2026-07-26  
Goal: `ABBY-VOICE-G020`  
Task: `ABBY-VOICE-AUTO-020`  
Status: **passed — offline distributed dataset-to-voice gate complete**

## Scope

This report is the checked-in evaluation receipt for proving the distributed
dataset-to-voice pipeline end to end. It covers the control-plane and
execution-plane contract from pinned source inventory through TTS, audio
validation, ASR, reconciliation, deterministic release construction, revision-
pinned load, GraphRAG-grounded voice turns, worker-crash recovery, and
capability/resource backpressure.

All fixtures are synthetic and public. No private caller audio, credentials,
remote speech service, GraphRAG deployment, IPFS node, or Hugging Face write
API is used by the offline gate.

## Authoritative evidence

| Evidence | Repository path | Gate |
| --- | --- | --- |
| offline deterministic fixture | `tests/voice/test_abby_voice_distributed_pipeline.py` (`test_offline_deterministic_fixture_end_to_end`) | Inventory → normalize → DuckDB TTS/validate/ASR → reconcile → `AbbyVoiceHFReleaseBuilder` → `AbbyVoiceReleaseLoader` → `process_voice_turn` with complete lineage and no network |
| worker-crash recovery test | same suite (`test_worker_crash_recovery_test`) | Expired leases recover; stale workers cannot complete; completed identities reuse without duplicate provider calls |
| capability/resource backpressure test | same suite (`test_capability_resource_backpressure_test`) | Capability mismatch plus host CPU/RAM/disk/GPU and provider concurrency/quota/token saturation admit zero work |
| Failure-class matrix | `test_failure_modes_are_asserted_offline` | Timeout, cancellation, 429, retryable 5xx, circuit-open, corrupt input, quality rejection, text-only fallback |
| Critical slot fidelity | `test_critical_slots_exact_across_text_asr_and_runtime` | Program/phone exact in rendered text, admitted ASR, release rows, and runtime spoken output; citations absent from speech |
| Safety co-gate | `tests/voice/test_abby_voice_safety.py` | Golden safety, privacy, crisis, and readability assertions remain green |
| Offline router benchmark | `benchmarks/bench_abby_voice_router.py --offline --check` | Latency/cache/fallback contract overhead without network |
| Audio jobs runbook | `docs/runbooks/ABBY_VOICE_AUDIO_JOBS.md` | Operator recovery, admission, privacy, and human-approved canary protocol |
| Objective-validation repair | `data/abby_voice/agent_supervisor/discovery/2026-07-26-abby-voice-auto-020-objective-validation-repair.md` | Maps each G020 evidence term to defining assertions |

## Acceptance thresholds and observed result

Command:

```text
python -m pytest -q tests/voice/test_abby_voice_distributed_pipeline.py tests/voice/test_abby_voice_safety.py && python benchmarks/bench_abby_voice_router.py --offline --check
```

| Metric | Threshold | Observed |
| --- | ---: | ---: |
| Offline distributed fixture | pass | inventory→turn lineage complete, no network |
| Worker-crash recovery | recover + no duplicate provider call | expired lease reclaimed; synthesize called once |
| Capability mismatch | refuse peer match | unsupported provider rejected |
| Host resource saturation | admit zero lanes | CPU/RAM/disk/GPU backpressure counts equal wave size |
| Provider saturation | admit zero lanes | concurrency/quota/token backpressure |
| Critical slot fidelity | 100% exact program/phone | exact across text, ASR, release, runtime |
| Privacy scan | no secret/private audio/transcript in receipts | passed on queue rows and turn receipts |
| Safety + distributed suite | pass | **25 passed** (14 distributed + 11 safety) |
| Offline benchmark | `--check` passed | `passed: true` (route p95 0.537 ms in recorded run) |

## Distributed flow under test

```text
pinned HF dataset commit + checksummed inventory receipt
  -> canonical Abby rows (offline fixture)
  -> deterministic TaskQueue work (voice.tts / voice.audio-validate / voice.asr)
  -> capability + resource admission
  -> injected TTS / validation / ASR collaborators
  -> immutable audio artifact descriptor + VoiceJobResult
  -> reconcile_voice_job_result (exact subject + quality gates)
  -> AbbyVoiceHFReleaseBuilder (five flat configs)
  -> AbbyVoiceReleaseLoader (immutable commit SHA)
  -> process_voice_turn grounded response + spoken audio
```

## Real-provider canary protocol

A **real-provider canary** remains outside the autonomous offline gate. It must
be **human-approved**, bounded by item count and **cost**, use only
**non-sensitive** rows, and write only to a disposable **staging prefix**. See
`docs/runbooks/ABBY_VOICE_AUDIO_JOBS.md` for the operator checklist. Promotion
and append-only remote publication remain `ABBY-VOICE-G021`.

## Reproducibility

The offline suite injects every provider, fetcher, capacity snapshot, and
template collaborator. Re-running the validation command on a clean checkout
must remain deterministic given the same fixture constants (spoken text, slot
values, and synthetic WAV parameters).
