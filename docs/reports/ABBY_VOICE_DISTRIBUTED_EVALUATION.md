# Abby Voice Distributed Pipeline Evaluation

Date: 2026-07-28

Goals: `ABBY-VOICE-G020`, `ABBY-VOICE-G035`, `ABBY-VOICE-G036`

Tasks: `ABBY-VOICE-AUTO-020`, `ABBY-VOICE-AUTO-033`, `ABBY-VOICE-AUTO-038`

Status: **passed — offline distributed and multi-surface evaluation gates complete**

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

The G035 extension runs one deterministic conversation corpus containing six
ordered website turns and six ordered telephone turns. It measures the exact
precomputed-audio cache, grounded-template, primary GraphRAG, slotted-fallback,
live-TTS, cache-miss, and terminal-miss outcomes. The returned audio from every
turn is transcribed by an injected ASR equivalent and compared with normalized
expected text. Cached Whisper remains an optional acoustic canary and is not a
dependency of the blocking offline gate.

The G036 closure binds the five child implementation receipts to one root tree,
runs the declared cross-surface gate, and audits the process boundary for
remote Hugging Face access. This receipt does not grant publication authority.

## Authoritative evidence

| Evidence | Repository path | Gate |
| --- | --- | --- |
| offline deterministic fixture | `tests/voice/test_abby_voice_distributed_pipeline.py` (`test_offline_deterministic_fixture_end_to_end`) | Inventory → normalize → DuckDB TTS/validate/ASR → reconcile → `AbbyVoiceHFReleaseBuilder` → `AbbyVoiceReleaseLoader` → `process_voice_turn` with complete lineage and no network |
| worker-crash recovery test | same suite (`test_worker_crash_recovery_test`) | Expired leases recover; stale workers cannot complete; completed identities reuse without duplicate provider calls |
| capability/resource backpressure test | same suite (`test_capability_resource_backpressure_test`) | Capability mismatch plus host CPU/RAM/disk/GPU and provider concurrency/quota/token saturation admit zero work |
| Failure-class matrix | `test_failure_modes_are_asserted_offline` | Timeout, cancellation, 429, retryable 5xx, circuit-open, corrupt input, quality rejection, text-only fallback |
| Critical slot fidelity | `test_critical_slots_exact_across_text_asr_and_runtime` | Program/phone exact in rendered text, admitted ASR, release rows, and runtime spoken output; citations absent from speech |
| deterministic conversation corpus | `tests/voice/test_abby_voice_multiturn_e2e.py` (`test_deterministic_multisurface_corpus_reports_exact_ratios_and_audio_match`) | Six website plus six telephone turns through the real adapters/shared router, with ordered history and exact per-stage outcomes |
| Hit and miss metric schema | same test plus `test_multisurface_evaluation_report_records_exact_ratios_and_audio_gate` | Exact numerator/denominator strings and basis points for cache hit, template hit, GraphRAG hit, fallback, live TTS, cache miss, terminal miss, and audio transcript match |
| Returned-audio transcript comparison | same corpus | Checksummed injected ASR equivalent reads each exact returned WAV; normalized expected/hypothesis WER and CER are zero on 12/12 turns |
| Optional Whisper comparison | `test_dozen_asr_injected_examples_retrieve_expected_routes_and_whisper_match_audio` and `test_dozen_text_injected_multiturn_cases_score_surfaces_and_stage_cache_misses` | Runs only when the canonical staged MP3 corpus, ffmpeg, and cached `openai/whisper-base` are locally available |
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
| Safety + distributed suite | pass | See the G035 required gate below |
| Offline benchmark | `--check` passed | `passed: true` (route p95 0.537 ms in recorded run) |

## AUTO-033 aggregate gate

Validation subject:

- root commit: `495b73b3b8d48132254ef2b3d957a676aef80f9f`
- root Git tree: `1825f6a13bc2565172917d45ddd316daad6b5b7e`
- `ipfs_accelerate_py`: `b18442ae36aa98fdfcb68e380954cc6894bd1751`
- `ipfs_datasets_py`: `98aafd10844988bb51c7a5fd81e2c722df4c43b4`

Declared command:

```text
python -m pytest -q tests/voice/test_abby_voice_multiturn_e2e.py tests/voice/test_abby_voice_pipeline.py tests/voice/test_abby_voice_distributed_pipeline.py tests/voice/test_abby_voice_safety.py ipfs_accelerate_py/test/test_voice_router_precomputed_audio.py tests/test_upload_hf_abby_tts_dataset.py
```

Observed on 2026-07-29: **69 passed, 3 skipped** in 4.32 seconds. A separate
endpoint/regeneration child-receipt check,
`python -m pytest -q tests/test_precompute_indextts_batch.py`, passed **47/47**
in 0.52 seconds.

The declared command was also repeated under `strace -f -e trace=connect` with
all recognized Hugging Face token variables removed, offline modes enabled,
and HTTP(S)/all proxies fenced to closed loopback port 9. It passed **69
runnable tests with 3 optional skips** in 6.18 seconds and produced no
`connect(2)` call. The selected tests therefore had no network path capable of
performing a Hugging Face mutation. The cache-miss dry-run assertion also
requires `remote_write_contacted=false` and `remote_writes=false`; the upload
test invokes local `stage_abby_tts_dataset` only, never `HfApi.upload_folder`.

| Quality result | Threshold | Observed |
| --- | ---: | ---: |
| Exact audio cache hit | recorded | 8/12 (66.67%) |
| Exact audio cache miss | recorded | 4/12 (33.33%) |
| Terminal miss | 0 | 0/12 |
| Blocking returned-audio comparison | 12/12 | 12/12 |
| Blocking normalized similarity | 10,000 bp | 10,000 bp |
| Blocking content-word coverage | 10,000 bp | 10,000 bp |
| Blocking WER / CER | 0 / 0 | 0 / 0 |
| Real Whisper canary | 12/12 | 12/12 |
| Real Whisper minimum similarity | ≥7,800 bp | 8,942 bp |
| Real Whisper minimum content coverage | ≥6,500 bp | 8,000 bp |
| Real Whisper maximum WER | ≤3,500 bp | 2,000 bp |
| Forbidden `negative` transcription | 0 | 0 |
| Remote Hugging Face reads / writes during gate | 0 / 0 | 0 / 0 |

The real-Whisper figures come from the existing read-only parent-stage receipt
`tmp_assets/hf-abby-tts-canonical-dataset/metadata/regeneration-canary-whisper-review.json`
(SHA-256
`b317e75bd272a8e77e33084d734ba2af34e2148257464e8c19659b5eda42cb25`).
The receipt records `remote_writes=false`. The three optional Whisper tests in
the declared checkout gate skipped because that checkout does not contain the
staged MP3 corpus/model cache; this is recorded explicitly rather than treating
the injected blocking verifier as a real Whisper run.

## Multi-surface hit, miss, and audio-quality scorecard

Blocking command:

```text
python -m pytest -q tests/voice/test_abby_voice_multiturn_e2e.py tests/voice/test_abby_voice_distributed_pipeline.py tests/voice/test_abby_voice_safety.py
```

Observed on 2026-07-28: **34 passed, 3 skipped** in 4.25 seconds. The
always-run 12-turn injected-ASR corpus passed. The three skips are the optional
canonical-stage/cached-Whisper tests whose local MP3 dataset or model cache is
not present in this checkout.

Outcome definitions are deliberately non-overlapping where they describe a
routing tier:

- A **cache hit** is an exact precomputed-audio resolver hit.
- A **template hit** means a grounded plan rendered successfully, whether it
  came from primary GraphRAG or the slotted fallback.
- A **GraphRAG hit** is a primary GraphRAG plan; a primary miss proceeds to the
  fallback fixture.
- A **fallback** is a successful slotted fallback plan after a GraphRAG miss.
- **live TTS** means returned audio was synthesized after a cache miss.
- A **miss** is an exact precomputed-audio cache miss. A **terminal miss** is a
  turn whose returned audio did not match normalized expected text.

| Surface | Turns | Cache hit | Template hit | GraphRAG hit | Fallback | Live TTS | Miss | Terminal miss | Audio transcript match |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Website | 6 | 4/6 | 6/6 | 4/6 | 2/6 | 2/6 | 2/6 | 0/6 | 6/6 |
| Telephone | 6 | 4/6 | 6/6 | 4/6 | 2/6 | 2/6 | 2/6 | 0/6 | 6/6 |
| **Combined** | **12** | **8/12** | **12/12** | **8/12** | **4/12** | **4/12** | **4/12** | **0/12** | **12/12** |

The machine scorecard also records rounded basis points: cache hit 6,667;
template hit 10,000; GraphRAG hit 6,667; fallback 3,333; live TTS 3,333; miss
3,333; terminal miss 0; and returned-audio transcript match 10,000.

The injected ASR equivalent is the deterministic blocking verifier permitted by
the acceptance contract. Each valid PCM WAV contains a checksummed normalized
transcript receipt in an unknown RIFF chunk. The verifier reads the exact bytes
returned by the website adapter or telephone router, validates the receipt
digest, and requires normalized similarity and content coverage of 10,000 basis
points with zero WER and CER. This proves byte-to-expected-text association and
route selection without claiming model-based acoustic intelligibility. When
local assets are present, the separate Whisper tests decode the staged website
MP3 and telephone μ-law audio and require at least 7,800 similarity and 6,500
content-word coverage basis points.

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
values, synthetic WAV parameters, 8/12 cache and GraphRAG hits, 12/12 template
hits, 4/12 fallback/live-TTS/cache misses, and 0/12 terminal misses).
