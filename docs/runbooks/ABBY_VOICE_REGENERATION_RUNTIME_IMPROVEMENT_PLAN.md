# Abby voice queue-regeneration and runtime improvement plan

Date: 2026-07-28

## Current state

- Canonical staged dataset: `tmp_assets/hf-abby-tts-canonical-dataset`.
- Regeneration queue: `tmp_assets/hf-abby-tts-canonical-dataset/metadata/abby_tts_regeneration_queue.jsonl`.
- Queue size: 3,908 rows.
- Alternate replacement queue: 0 rows.
- Manual-review queue: 0 rows.
- Latest upstream state was fetched and reconciled for:
  - `ipfs_accelerate_py`
  - `ipfs_datasets_py`
- `ipfs_datasets_py.voice.regeneration` deterministically projects the queue into
  3,908 TTS jobs, 3,908 ASR jobs, and 3,908 validation jobs while retaining
  superseded audio/response lineage. The normalized spoken text contains no raw
  digits, dash punctuation, parentheses, or literal `negative` artifacts.
- The complete local plan, workset, and endpoint response manifest are
  materialized as `metadata/regeneration-full-plan.json`,
  `metadata/regeneration-full-workset.json`, and
  `metadata/regeneration-full-responses.json`. The stable plan ID is
  `abby-voice-regeneration-plan:sha256:a7d3994a5d2edeaf792fa491da888f869410d839ff4ddb22ec375ab60d39353a`.
- The live synthesis endpoint is
  `https://indexteam-indextts-2-demo.hf.space`. Its registered synthesis
  contract is `/gen_single` (function index 6, 24 inputs). The Space does not
  currently register `/gen_batch`, `/gen_batch_with_upload`, or result-upload
  APIs, so the detected safe mode is `parallel-gen-single`.
- A stable 12-item canary was generated through that live endpoint: 12 generated,
  0 failed. The resulting MP3 files are under
  `tmp_assets/hf-abby-tts-canonical-dataset/regeneration-canary-audio`.
- The final Whisper review passed 12/12 with minimum normalized similarity
  89.42%, minimum content-word coverage 80%, maximum WER 20%, and no forbidden
  `negative` detections. The receipt is
  `tmp_assets/hf-abby-tts-canonical-dataset/metadata/regeneration-canary-whisper-review.json`.
- The offline two-surface, 12-turn test produced 8 retrieval/cache hits and 4
  misses: 66.67% hit and 33.33% miss. All 12 returned-audio reviews matched;
  the four validated misses staged four idempotent local response-DAG
  candidates. Telephone output was verified as 8 kHz, mono, PCM mu-law.
- No Hugging Face dataset, bucket, or response-DAG write was performed. All DAG
  candidates remain local and publication authority remains disabled.
- The recovered outer worktree registration has been repaired. Package-owned
  behavior must still land in the two packages; this repository retains thin
  integration wrappers and deployment wiring.
- The closure test matrix passed 139 tests: 74 focused package/wrapper
  regressions, 59 broader pipeline/distributed/safety/release tests, and 6
  Whisper-backed multi-turn scenarios.

## AUTO-033 final local integration receipt

Status: **passed on 2026-07-29**.

The integration subject was root commit
`495b73b3b8d48132254ef2b3d957a676aef80f9f`, Git tree
`1825f6a13bc2565172917d45ddd316daad6b5b7e`, with package gitlinks
`ipfs_accelerate_py@b18442ae36aa98fdfcb68e380954cc6894bd1751` and
`ipfs_datasets_py@98aafd10844988bb51c7a5fd81e2c722df4c43b4`.
The implementation commits for AUTO-034 through AUTO-038 are all ancestors of
that exact root commit. The authoritative aggregate mapping is
`data/abby_voice/agent_supervisor/discovery/ABBY-VOICE-G030-completion.md`.

The declared local gate passed with **69 passed, 3 skipped** in 4.32 seconds:

```text
python -m pytest -q tests/voice/test_abby_voice_multiturn_e2e.py tests/voice/test_abby_voice_pipeline.py tests/voice/test_abby_voice_distributed_pipeline.py tests/voice/test_abby_voice_safety.py ipfs_accelerate_py/test/test_voice_router_precomputed_audio.py tests/test_upload_hf_abby_tts_dataset.py
```

The three skips are optional acoustic tests requiring the canonical staged MP3
corpus and a locally cached `openai/whisper-base`; they are not failures or
silent substitutions. The always-run blocking corpus recorded 8/12 exact audio
hits and 4/12 misses (66.67% / 33.33%), 12/12 returned-audio transcript
matches, zero terminal misses, zero WER/CER, and 10,000 basis points for both
normalized similarity and content-word coverage.

The existing real-Whisper canary receipt was re-read without mutation from the
parent staging area. Its SHA-256 is
`b317e75bd272a8e77e33084d734ba2af34e2148257464e8c19659b5eda42cb25`;
it records 12/12 passed with minimum normalized similarity 8,942 basis points,
minimum content-word coverage 8,000, maximum WER 2,000, no forbidden
`negative` detection, and `remote_writes=false`.

The validation was run with Hugging Face credentials removed, Hub/datasets/
transformers offline modes enabled, and all outbound proxies pointed at closed
loopback port 9. A second identical test selection under
`strace -f -e trace=connect` passed 69/69 runnable tests and emitted **zero
`connect(2)` calls**. Therefore the gate made zero remote Hugging Face reads,
writes, commits, uploads, or pointer changes. Remote publication remains a
separate G021 operator action.

## Supervisor start result

The canonical bundle index now includes `ABBY-VOICE-G030` through
`ABBY-VOICE-G036` and `ABBY-VOICE-AUTO-033` through
`ABBY-VOICE-AUTO-038`. A restricted local launch profile is materialized as a
paired JSON/DuckDB artifact:

- `data/abby_voice/agent_supervisor/launch_profiles/regeneration-runtime.index.json`
- `data/abby_voice/agent_supervisor/launch_profiles/regeneration-runtime.index.duckdb`

That profile allows only the six regeneration/runtime bundles and sets
`remote_mutation_authority` to `false`. A fresh plan under
`recovery_v13/regeneration_runtime` found four immediately claimable lanes:
website, telephone, cache-miss DAG, and endpoint regeneration. Evaluation is
dependency-blocked on the two surface lanes, and the final integration task is
dependency-blocked on all five child tasks.

A bounded scheduler reconciliation was also run under
`recovery_v13/regeneration_runtime_safe_start` with `--start --once
--no-implement` and deliberately impossible CPU/memory admission thresholds.
It exercised scheduler startup but admitted no children: `started_count=0`,
`active_worker_count=0`, and `active_worker_pids=[]`.

After repairing the worktree registration, a second one-cycle start under
`recovery_v14/regeneration_runtime_safe_start` admitted four parallel
**no-implementation** lane supervisors: website, telephone, cache-miss DAG, and
endpoint regeneration. Evaluation and final integration remained
dependency-blocked. All four wrappers exited after the observation pass, with
`started_count=4`, `active_worker_count=0`, `active_worker_pids=[]`, and no
implementation, Hugging Face job, upload, commit, or remote-write event. The
JSON manifest SHA-256 is
`23793a31847c6fa2a117b8d282d4409055d7de6e00e5b6e10f2527bd0edb5fd6`.

Task ownership in the restricted graph is:

- `ABBY-VOICE-AUTO-034`: endpoint contract and regeneration runner;
- `ABBY-VOICE-AUTO-035`: validated cache-miss response-DAG candidate;
- `ABBY-VOICE-AUTO-036`: website multi-turn validation;
- `ABBY-VOICE-AUTO-037`: telephone multi-turn validation;
- `ABBY-VOICE-AUTO-038`: combined evaluation, dependent on the two surface
  lanes;
- `ABBY-VOICE-AUTO-033`: final local integration gate, dependent on all five
  child tasks.

The outer worktree metadata is now registered correctly and is no longer the
launch blocker. The v14 receipt proves scheduler configuration, parallel-lane
admission, and dependency resolution only: implementation workers were
**not** started. The current fence is the dirty recovered checkout plus missing
dependency-completion receipts. Before enabling implementation, review and
land the recovered package diffs, retain the restricted profile, and continue
to leave remote mutation authority disabled.

Maintenance caveat: the current lane preflight runs `git worktree prune` and
Git GC even in `--no-implement` mode. The v14 pass removed no worktree
directories, files, or branch refs, but it did discard seven already-prunable
administrative registrations whose target directories did not exist. Do not
repeat a nominally zero-mutation start until the supervisor gains a
maintenance-disable option, or resource-fence the parent so no child lane
preflight is admitted.

## Ownership rule

All reusable voice behavior lands in the refactored packages:

- `ipfs_accelerate_py`
  - voice runtime router
  - exact precomputed audio resolver
  - ASR/TTS provider adapters
  - endpoint admission, retries, circuit breakers
  - durable voice job contracts and execution
  - agent-supervisor goal/subgoal/task integration
- `ipfs_datasets_py`
  - Abby voice dataset schemas
  - response DAG and slotted template storage
  - GraphRAG template/retrieval indexes
  - Hugging Face release builder/publisher
  - deterministic workset generation and bridge into `ipfs_accelerate_py` voice jobs

This repository should retain only:

- thin CLI wrappers;
- environment wiring;
- migration runbooks;
- website/telephone adapters that call the package APIs.

## Workstream 0: package compatibility after refactor

Status: implemented and contract-tested.

The canonical `ipfs_accelerate_py.hf_space_inference` surface now provides:

- Gradio config probing and API-name/function-index resolution;
- queue/SSE invocation for the registered `/gen_single` endpoint;
- upload/download helpers for deployments that expose them;
- resumable response-manifest execution;
- current `hf buckets list/cp` integration;
- redacted endpoint-contract receipts.

Compatibility imports are retained:

1. `ipfs_accelerate_py.hf_space_inference.HFSpaceClient`
2. `ipfs_accelerate_py.hf_space_inference.HFBucketBackend`

The focused contract proves:

- no credential is serialized into a receipt;
- probing is read-only;
- upload-capable batch detection fails closed;
- deployment drift selects `parallel-gen-single` because the live Space exposes
  only `/gen_single`.

Acceptance achieved:

- `scripts/precompute_indextts_responses.py --print-indextts-contract` works
  against `https://indexteam-indextts-2-demo.hf.space`;
- the live receipt records `/gen_single`, function index 6, 24 inputs, and
  `recommendedMode=parallel-gen-single`.

Ongoing compatibility gate:

- probe once before every canary or resumed batch;
- stop if the registered input count or function index changes;
- never infer upload capability from a configured API name that is absent from
  the live dependencies.

## Workstream 1: regenerate the 3,908 queue rows

Input:

- `abby_tts_regeneration_queue.jsonl`

Each row contains:

- `audioId`;
- `responseId`;
- `selectedDatasetAudioPath`;
- `selectedText`;
- `normalizedRepairText`;
- risk reasons.

Implemented planning and canary:

1. `ipfs_datasets_py.voice.regeneration` converts the queue into a deterministic
   `VoiceAudioWorkset`.
2. For each queue row:
   - use `normalizedRepairText` as the exact TTS input;
   - compute canonical spoken-text SHA-256;
   - preserve the original `audioId` as superseded lineage;
   - mint a new content-addressed audio ID unless exact identity is intentionally reused after byte validation.
3. Submit work through `ipfs_datasets_py.ml.accelerate_integration.voice_jobs.VoiceJobBridge`.
4. Execute jobs through `ipfs_accelerate_py.voice_jobs.executor`, using `voice_router.text_to_speech`.
5. Use the probed endpoint mode. For the current deployment this is resumable,
   bounded `/gen_single`; batch/upload modes remain unavailable and must not be
   fabricated by the wrapper.
6. Validate generated audio:
   - run Whisper ASR;
   - normalize expected and observed transcripts;
   - compute exact required phrase coverage and WER/similarity;
   - reject audio containing “negative”, raw punctuation phone artifacts, parentheses artifacts, or missing required phone/address digits.
7. Write output as append-only artifacts:
   - audio descriptors;
   - TTS provider receipts;
   - ASR validation receipts;
   - supersession map from old audio IDs to new audio IDs.

Canary evidence:

- deterministic canary plan:
  `metadata/regeneration-canary-plan.json`;
- projected TTS/ASR/validation workset:
  `metadata/regeneration-canary-workset.json`;
- live generation manifest:
  `metadata/regeneration-canary-generation-manifest.json`;
- final ASR review:
  `metadata/regeneration-canary-whisper-review.json`;
- generated 12/12, Whisper passed 12/12, minimum similarity 89.42%, minimum
  coverage 80%, maximum WER 20%.

Full-run acceptance:

- 100% of 3,908 rows have terminal status: regenerated, quarantined, or provider-exhausted.
- No regenerated row contains phone/address hyphenation traps in expected text.
- Every successful synthesis has an audio SHA-256 and passing ASR-validation
  receipt before it can supersede the old object.
- Full-batch publication is blocked unless canary hit/miss and ASR-quality gates pass.

## Workstream 2: response DAG append on cache miss

Cache miss definition:

- precomputed resolver status is `miss`;
- rendered spoken text is safe and normalized;
- GraphRAG retrieval either produced a grounded response or fallback LLM produced an approved slotted template response;
- live TTS succeeded and ASR validation passed.

Implemented local contract:

1. `ipfs_accelerate_py.voice_cache_miss` exposes a structured cache-miss event:
   - rendered text hash;
   - synthesis identity;
   - resolver miss reason;
   - template ID / response ID if present;
   - stage traces;
   - no private audio bytes or credentials.
2. `ipfs_datasets_py.voice.response_dag` performs append-only local
   materialization:
   - deterministic response node ID;
   - slotted template node when fallback generated a reusable pattern;
   - vocabulary entries for slot values;
   - audio descriptor node after validation.
3. The candidate is rejected unless the ASR-validation receipt and expected
   response/audio hashes agree. Replaying the same event produces the same
   candidate ID and no duplicate append.
4. The candidate release manifest is consumable by the existing
   `ipfs_datasets_py` Hugging Face publisher dry-run:
   - branch or immutable prefix only;
   - compare-and-swap base revision;
   - no deletes, moves, force pushes, or mutable-main promotion;
   - local dry-run diff required before remote write.
5. Website and telephone adapters call the same package API:
   - `record_voice_cache_miss(...)`;
   - `append_response_dag_candidate(...)`;
   - `publish_append_only_cache_miss_batch(...)`.

Verified acceptance:

- The 12-turn offline multi-surface test staged four validated local candidates,
  one for each live-TTS miss.
- Duplicate cache miss with the same rendered text and synthesis identity is
  idempotent.
- Remote append dry-run shows exact files to add and no file replacements.
- Caller audio and caller transcript are absent from the event and candidate.
- No remote write occurred. A future append requires explicit operator approval
  of repository ID, target branch/base revision, and credential scope.

## Workstream 3: website voice chat validation

Target:

- `wallet_interface` keeps thin wrappers and calls `ipfs_accelerate_py.voice_router.process_voice_turn`.

Implemented offline integration test:

1. Browser/unit coverage remains responsible for:
   - microphone permission blocked;
   - local browser speech fallback retained;
   - remote voice proxy STT/TTS path;
   - exact precomputed audio hit path;
   - miss→live TTS path;
   - miss event is emitted without private audio.
2. API:
   - `/voice/stt`, `/voice/turn`, `/voice/tts` or current equivalent routes return the package `VoiceTurnResult` contract.
3. The package-level E2E test currently injects text at the ASR boundary and
   runs six ordered web turns through GraphRAG retrieval, slotted fallback,
   exact-audio resolution/live TTS, and Whisper review.

Current evidence and remaining scale gate:

- the combined web/telephone fixture has 12/12 successful returned-audio
  reviews, 8 retrieval/audio-cache hits, and 4 validated misses;
- cache-miss candidates are generated for 100% of validated live-TTS misses;
- no caller audio or transcript is present in telemetry/DAG payloads;
- expand to at least 20 synthetic web conversations and require >=95% turn
  success before website production enablement.

## Workstream 4: telephone support-line validation

Target:

- telephone runtime calls the same package voice API as the website.

Implemented offline integration test:

1. Telephony ingress retains required fixture coverage:
   - Twilio/SIP webhook fixture;
   - audio media fetch/stream mocked;
   - ASR call through `voice_router.speech_to_text`.
2. Dialog manager:
   - maximum-turn enforcement;
   - crisis routing;
   - barge-in / repeat / slow-speech handling;
   - phone-number readback without hyphenation or “negative”.
3. Telephony egress:
   - returned audio URL or TwiML-compatible media reference;
   - text-only fallback when TTS unavailable;
   - status callbacks captured.
4. Six ordered telephone turns now traverse the same package path as the web
   turns. Returned media is transcoded and inspected as PCM mu-law, 8,000 Hz,
   mono before Whisper review.

Current evidence and remaining scale gate:

- the six-turn offline telephone fixture passes end to end;
- the combined fixture's retrieval/audio hit ratio is 66.67% and miss ratio is
  33.33%;
- all validated live-TTS misses stage an append candidate;
- crisis route false-negative rate = 0 on fixture set;
- “negative” phone artifact rate = 0;
- expand the telephony fixture set and require >=95% synthetic turn success
  before production-line enablement.

## Workstream 5: multi-turn simulation and hit/miss ratios

Dataset:

- seed from `data/abby_voice/eval/golden_voice_turns.jsonl`;
- add 100+ public synthetic dialogs across:
  - food;
  - shelter;
  - crisis;
  - diapers;
  - utilities;
  - medical clinic;
  - accessibility;
  - Spanish language access;
  - no-current-match fallback;
  - unsafe unbound slot rejection.

Harness:

- inject text into ASR for deterministic retrieval tests;
- optionally run TTS and Whisper for audio validation;
- run both `surface=web` and `surface=telephone`;
- collect per-turn and per-dialog metrics.

Verified baseline:

- two six-turn sessions, one web and one telephone;
- 12 total turns;
- retrieval: 8 hits / 4 misses = 66.67% / 33.33%;
- exact-audio cache: 8 hits / 4 misses = 66.67% / 33.33%;
- live synthesis/fallback calls: 4;
- locally staged response-DAG candidates: 4;
- Whisper returned-audio matches: 12/12;
- Hugging Face reads/writes during this offline simulation: 0/0.

Metrics:

- `precomputed_hit_ratio = precomputed_hits / total_tts_turns`
- `validated_live_tts_miss_ratio = validated_live_tts_misses / total_tts_turns`
- `text_only_fallback_ratio = text_only_turns / total_turns`
- `retrieval_hit_ratio = grounded_retrieval_hits / retrieval_attempts`
- `unsafe_rejection_ratio = unsafe_rejections / unsafe_cases`
- `dag_append_candidate_ratio = append_candidates / validated_live_tts_misses`
- ASR WER and normalized phrase coverage per generated audio.

Acceptance:

- metrics are emitted as JSONL and summary JSON;
- failing examples retain trace receipts but no private audio;
- simulation can run offline with fakes and online with approved endpoints.

## Rollout progression and release gates

Progress is monotonic and receipt-driven:

1. **Offline planning**
   - parse exactly 3,908 source rows;
   - build exactly 3,908 TTS, ASR, and validation jobs;
   - reject normalized text containing raw digits, dash punctuation,
     parentheses, or the literal word `negative`;
   - record stable plan, workset, response, and lineage identities.
2. **Read-only endpoint contract**
   - probe the live Space;
   - require the expected `/gen_single` function index/input count;
   - stop on deployment drift;
   - keep bucket/repository mutation disabled.
3. **12-item canary**
   - already complete: 12/12 generated and 12/12 Whisper-validated;
   - retain the observed quality floor of 89.42% similarity, 80% content
     coverage, and 20% maximum WER as the minimum current evidence, not a reason
     to weaken configured gates.
4. **Bounded batch waves**
   - begin with a small resumable wave, review provider-exhausted/quarantined
     outcomes and quality distributions, then increase the wave size;
   - do not start the next wave while any prior successful synthesis lacks an
     ASR-validation receipt;
   - stop if failure rate, forbidden-artifact rate, endpoint contract, quota, or
     cost ceiling crosses its configured limit.
5. **Full remaining queue**
   - resume by content identity rather than regenerating completed items;
   - require every one of the 3,908 rows to end as regenerated, quarantined, or
     provider-exhausted;
   - build a local canonical-dataset release candidate and supersession ledger.
6. **Append-only publication**
   - dry-run the exact additions against an immutable prefix/branch and
     compare-and-swap base revision;
   - require explicit operator approval for repository/bucket identity,
     revision, credential scope, and expected write volume;
   - publish no replacement/deletion and never force-push mutable main.
7. **Surface rollout**
   - deploy the same package versions to website and telephone adapters;
   - run expanded public synthetic multi-turn suites and require >=95% turn
     success, zero crisis false negatives, zero forbidden phone/address
     artifacts, and a DAG candidate for every validated live-TTS miss;
   - release gradually with hit/miss, text-only fallback, ASR-quality, latency,
     and provider-exhaustion monitoring.

## Retry, resume, and idempotency policy

- Plan IDs, spoken-text hashes, synthesis identities, audio SHA-256 values,
  validation receipt IDs, and DAG candidate IDs are deterministic.
- A completed audio object whose bytes and validation receipt match is reused;
  process restart resumes from the progress/manifest receipt instead of issuing
  a second synthesis call.
- Retry only transient timeout, connection, HTTP 408/425/429, and 5xx failures.
  Respect provider `Retry-After`, use bounded exponential backoff/jitter, cap
  attempts and concurrency, and stop on quota/cost admission failure.
- Do not retry terminal authentication, contract, input-validation, or unsafe
  spoken-text failures. Record them as quarantined or provider-exhausted with a
  sanitized reason.
- Cache-miss DAG staging is idempotent. Replaying the same validated event
  materializes the same candidate and cannot duplicate response, template,
  vocabulary, or audio nodes.
- Remote append, when approved, uses a base revision compare-and-swap so a
  concurrent change causes a new dry run rather than an overwrite.

## Privacy and mutation boundary

- Runtime events and receipts contain hashes, IDs, safe stage metadata, and
  sanitized provider status only.
- Never serialize credentials, authorization headers, caller audio bytes, local
  secret paths, or caller transcripts into telemetry or response-DAG
  candidates.
- Generated public response audio is addressed by SHA-256 after validation;
  failing traces retain hashes/reason codes, not private audio.
- Endpoint inference is authorized separately from Hugging Face
  dataset/bucket mutation. The completed canary used inference only.
- The supervisor restricted profile fixes
  `remote_mutation_authority=false`; implementation lanes cannot grant
  themselves publication authority.

## Workstream 6: supervisor goals, subgoals, and parallel task lanes

Add/maintain package-owned goals:

- `ABBY-VOICE-G030`: endpoint contract, regeneration runner, cache-miss DAG
  candidate, and website/telephone multi-turn validation. Remote publication
  remains owned by `ABBY-VOICE-G021`.
- `ABBY-VOICE-G031`: endpoint-safe regeneration runner and bounded canary
  manifest.
- `ABBY-VOICE-G032`: cache-miss event and append-only response-DAG candidate.
- `ABBY-VOICE-G033`: website voice-agent multi-turn validation.
- `ABBY-VOICE-G034`: telephone support-line multi-turn validation.
- `ABBY-VOICE-G035`: multi-turn simulation metrics and Whisper quality gates.
- `ABBY-VOICE-G036`: final receipt-bound local integration and no-remote-write
  audit.

Parallel lanes:

- `abby-voice-regeneration`
  - endpoint contract probe;
  - queue-to-workset conversion;
  - canary regeneration;
  - full regeneration runner.
- `abby-voice-runtime`
  - cache-miss event;
  - exact resolver metrics;
  - live TTS validation receipt.
- `abby-voice-data`
  - response DAG append;
  - template/vocabulary updates;
  - HF release append dry-run.
- `abby-voice-web`
  - website adapter tests;
  - browser E2E.
- `abby-voice-telephone`
  - Twilio/SIP fixtures;
  - phone-line E2E.
- `abby-voice-evaluation`
  - synthetic multi-turn corpus;
  - hit/miss dashboard and gates.

Supervisor policy:

- local code/tests may run autonomously;
- remote Hugging Face writes are dry-run only until operator approval;
- generated audio cost must be bounded by queue length, batch size, retry count, and endpoint billing identity;
- all jobs are idempotent by content hash.

## Immediate next commands

Rebuild the deterministic 3,908-row plan/workset (use `--canary-size 12` only
when rebuilding the stable canary):

```bash
PYTHONPATH="$PWD/ipfs_accelerate_py:$PWD/ipfs_datasets_py" \
  python scripts/plan_abby_tts_regeneration.py \
  --queue tmp_assets/hf-abby-tts-canonical-dataset/metadata/abby_tts_regeneration_queue.jsonl \
  --plan-out tmp_assets/hf-abby-tts-canonical-dataset/metadata/regeneration-full-plan.json \
  --workset-out tmp_assets/hf-abby-tts-canonical-dataset/metadata/regeneration-full-workset.json \
  --response-manifest-out tmp_assets/hf-abby-tts-canonical-dataset/metadata/regeneration-full-responses.json
```

Probe the live contract before synthesis:

```bash
PYTHONPATH="$PWD/ipfs_accelerate_py:$PWD/ipfs_datasets_py" \
  python scripts/precompute_indextts_responses.py \
  --print-indextts-contract \
  --space-url https://indexteam-indextts-2-demo.hf.space
```

The completed canary invocation shape is:

```bash
PYTHONPATH="$PWD/ipfs_accelerate_py:$PWD/ipfs_datasets_py" \
  python scripts/precompute_indextts_responses.py \
  --space-url https://indexteam-indextts-2-demo.hf.space \
  --response-manifest tmp_assets/hf-abby-tts-canonical-dataset/metadata/regeneration-canary-responses.json \
  --reference-audio tmp_assets/abby-reference.wav \
  --output-dir tmp_assets/hf-abby-tts-canonical-dataset/regeneration-canary-audio \
  --manifest tmp_assets/hf-abby-tts-canonical-dataset/metadata/regeneration-canary-generation-manifest.json \
  --public-manifest tmp_assets/hf-abby-tts-canonical-dataset/metadata/regeneration-canary-generation-public.json \
  --progress-json tmp_assets/hf-abby-tts-canonical-dataset/metadata/regeneration-canary-generation-progress.json \
  --limit 12 \
  --bucket-uri ""
```

Review generated or safely resumed audio with Whisper:

```bash
PYTHONPATH="$PWD/ipfs_accelerate_py:$PWD/ipfs_datasets_py" \
  python scripts/review_abby_regeneration_audio.py \
  --manifest tmp_assets/hf-abby-tts-canonical-dataset/metadata/regeneration-canary-generation-manifest.json \
  --report-out tmp_assets/hf-abby-tts-canonical-dataset/metadata/regeneration-canary-whisper-review.json \
  --model openai/whisper-base
```

Supervisor plan (no child processes):

```bash
PYTHONPATH="$PWD/ipfs_accelerate_py:$PWD/ipfs_datasets_py" \
  python -m ipfs_accelerate_py.agent_supervisor.objectives.bundle_supervisor \
  --bundle-index-path data/abby_voice/agent_supervisor/launch_profiles/regeneration-runtime.index.json \
  --repo-root "$PWD" \
  --state-root data/abby_voice/agent_supervisor/recovery_v13/regeneration_runtime/state \
  --worktree-root data/abby_voice/agent_supervisor/recovery_v13/regeneration_runtime/worktrees \
  --log-dir data/abby_voice/agent_supervisor/recovery_v13/regeneration_runtime/logs \
  --manifest-path data/abby_voice/agent_supervisor/recovery_v13/regeneration_runtime/plan.json \
  --task-prefix ABBY-VOICE-AUTO- \
  --max-lanes 4 \
  --no-implement
```

Bounded scheduler-start proof (resource-fenced; no child processes):

```bash
PYTHONPATH="$PWD/ipfs_accelerate_py:$PWD/ipfs_datasets_py" \
  python -m ipfs_accelerate_py.agent_supervisor.objectives.bundle_supervisor \
  --bundle-index-path data/abby_voice/agent_supervisor/launch_profiles/regeneration-runtime.index.json \
  --repo-root "$PWD" \
  --state-root data/abby_voice/agent_supervisor/recovery_v13/regeneration_runtime_safe_start/state \
  --worktree-root data/abby_voice/agent_supervisor/recovery_v13/regeneration_runtime_safe_start/worktrees \
  --log-dir data/abby_voice/agent_supervisor/recovery_v13/regeneration_runtime_safe_start/logs \
  --manifest-path data/abby_voice/agent_supervisor/recovery_v13/regeneration_runtime_safe_start/manifest.json \
  --task-prefix ABBY-VOICE-AUTO- \
  --max-lanes 4 \
  --start \
  --no-implement \
  --once \
  --max-cpu-percent 0 \
  --minimum-memory-available-bytes 9223372036854775807
```

The scheduler proof above intentionally starts no implementation workers. Before
using `--implement --start`, run the focused package/root test gates, inspect
all pending diffs, verify that the registered worktree is healthy, and reuse
only the restricted launch profile. Keep `remote_mutation_authority=false`;
remote publication remains a separate, explicit operator action.
