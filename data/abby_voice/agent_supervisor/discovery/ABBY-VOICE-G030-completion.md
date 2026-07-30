# ABBY-VOICE-G030 / G036 Completion Receipt

Date: 2026-07-29
Goal ids: `ABBY-VOICE-G030`, `ABBY-VOICE-G036`
Task id: `ABBY-VOICE-AUTO-033`
Dependencies: `ABBY-VOICE-AUTO-034` through `ABBY-VOICE-AUTO-038`
Track: `voice-integration`
Status: **complete — local integration passed; remote mutation remained disabled**

## Validation subject

This receipt is bound to the exact implementation tree tested before this
evidence-only document update:

| Coordinate | Value |
| --- | --- |
| Root commit | `495b73b3b8d48132254ef2b3d957a676aef80f9f` |
| Root Git tree | `1825f6a13bc2565172917d45ddd316daad6b5b7e` |
| Branch | `implementation/abby-voice-auto-033-aea887ef73c0-attempt-1-1785288124` |
| `ipfs_accelerate_py` gitlink | `b18442ae36aa98fdfcb68e380954cc6894bd1751` |
| `ipfs_datasets_py` gitlink | `98aafd10844988bb51c7a5fd81e2c722df4c43b4` |

The checkpoint directory was inspected before validation and contained no
files, so no prior result was reused.

## Child completion receipts

Every child implementation commit below is an ancestor of the validation
subject. The current gitlinks above include the merged package-owned behavior.

| Task | Root implementation commit | Current-tree evidence | Receipt status |
| --- | --- | --- | --- |
| `ABBY-VOICE-AUTO-034` | `36e54828060d91742bc4928308fcc9d3f4229e5a` | `tests/test_precompute_indextts_batch.py`: read-only endpoint probe; deterministic bounded canary manifest; canonical plan round trip; retry, quarantine, resume, tamper, and endpoint-drift tests | verified |
| `ABBY-VOICE-AUTO-035` | `82e4f33cda2dd79e4aaa1caed916c0c004dc4efa` | `test_validated_live_tts_miss_stops_at_local_response_dag_dry_run`: privacy-safe event, deterministic candidate, template/vocabulary rows, duplicate idempotency, local-only publication receipt | verified |
| `ABBY-VOICE-AUTO-036` | `ca906cafbd74bee909e0b9403ad05a0661fde22c` | `test_website_adapter_multiturn_asr_exact_hit_fallback_miss_and_text_only`: adapter contract, ordered browser fixture, exact hit/miss trace, safe degradation | verified |
| `ABBY-VOICE-AUTO-037` | `cf6337f9985690ac872a6b43b5e1f3b0426e7171` | telephone factual-slot safety, retry/barge-in/escalation fixture, and max-turn privacy-safe escalation assertions | verified |
| `ABBY-VOICE-AUTO-038` | `3818634da6cafd3b12d2047ebeed8d13b3257410` | deterministic 12-turn multi-surface corpus, exact ratio schema, returned-audio comparison, changed-fact rejection, and documented Whisper thresholds | verified |

Focused endpoint/regeneration receipt command:

```text
python -m pytest -q tests/test_precompute_indextts_batch.py
```

Result: **47 passed in 0.52 seconds**.

## Declared local integration gate

```text
python -m pytest -q tests/voice/test_abby_voice_multiturn_e2e.py tests/voice/test_abby_voice_pipeline.py tests/voice/test_abby_voice_distributed_pipeline.py tests/voice/test_abby_voice_safety.py ipfs_accelerate_py/test/test_voice_router_precomputed_audio.py tests/test_upload_hf_abby_tts_dataset.py
```

Result: **PASS — 69 passed, 3 skipped, 2 warnings in 4.32 seconds**.

The skips are the three optional tests that require the canonical staged MP3
corpus and locally cached `openai/whisper-base`. The always-run deterministic
audio-quality gate executed and passed. The two warnings are unrelated Python
deprecations (`audioop` and package/spec metadata).

## Hit, miss, and transcript results

| Surface | Turns | Cache hit | Cache miss | GraphRAG hit | Fallback/live TTS | Terminal miss | Audio transcript match |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Website | 6 | 4/6 | 2/6 | 4/6 | 2/6 | 0/6 | 6/6 |
| Telephone | 6 | 4/6 | 2/6 | 4/6 | 2/6 | 0/6 | 6/6 |
| **Combined** | **12** | **8/12 (66.67%)** | **4/12 (33.33%)** | **8/12** | **4/12** | **0/12** | **12/12** |

The blocking injected-ASR equivalent verified the exact returned WAV bytes:
12/12 transcript matches, normalized similarity 10,000 basis points,
content-word coverage 10,000 basis points, and zero WER/CER.

The real `openai/whisper-base` canary receipt was re-read from the parent
staging area without changing it:

- receipt SHA-256:
  `b317e75bd272a8e77e33084d734ba2af34e2148257464e8c19659b5eda42cb25`;
- 12 receipts, 12 passed, 0 failed;
- minimum normalized similarity: 8,942 bp (gate: 7,800);
- minimum content-word coverage: 8,000 bp (gate: 6,500);
- maximum WER: 2,000 bp (gate: 3,500);
- forbidden `negative` detections: 0;
- receipt field: `remote_writes=false`.

These are real-Whisper acoustic results from the retained canary, not results
from the three skipped optional tests in this checkout.

## No-remote-write audit

The declared gate ran with:

- all recognized Hugging Face token variables removed;
- `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`,
  `DATASETS_OFFLINE=1`, and `HF_DATASETS_OFFLINE=1`;
- `HTTP_PROXY`, `HTTPS_PROXY`, and `ALL_PROXY` set to closed loopback port 9;
- `NO_PROXY` limited to localhost.

The identical test selection was then repeated under:

```text
strace -f -e trace=connect python -m pytest -q tests/voice/test_abby_voice_multiturn_e2e.py tests/voice/test_abby_voice_pipeline.py tests/voice/test_abby_voice_distributed_pipeline.py tests/voice/test_abby_voice_safety.py ipfs_accelerate_py/test/test_voice_router_precomputed_audio.py tests/test_upload_hf_abby_tts_dataset.py
```

Result: **69 passed, 3 skipped in 6.18 seconds; zero `connect(2)` calls**.

The selected cache-miss publication test independently asserts
`remote_write_contacted=false` and `remote_writes=false`. The upload-named test
imports the staging script but calls only `stage_abby_tts_dataset` against a
temporary local directory; it never calls `HfApi.upload_folder`.

Therefore the integration gate performed:

- remote Hugging Face reads: **0**;
- remote Hugging Face writes/uploads/commits: **0**;
- remote dataset pointer promotions: **0**.

Remote publication remains owned by G021 and requires a separate explicit
operator action. AUTO-033 grants no remote mutation authority.

## Closure

Required evidence is satisfied:

- child completion receipts: **verified for AUTO-034 through AUTO-038**;
- local integration report: **69 passed, 3 optional skips**;
- hit and miss metrics: **8/12 hits, 4/12 misses, zero terminal misses**;
- Whisper quality: **12/12 retained real canary receipts passed**;
- no-remote-write audit: **zero network connects and zero remote writes**.
