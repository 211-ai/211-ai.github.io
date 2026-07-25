# Abby Voice Router Objective Heap

This objective heap turns the current Abby voice-assistant implementation into
bounded work for `ipfs_accelerate_py.agent_supervisor`.

Current implementation evidence:

- `wallet_interface` already provides remote IndexTTS, remote Whisper STT,
  browser speech, local WebGPU audio, retry/fallback handling, precomputed audio,
  and a GraphRAG-aware voice prompt.
- `ipfs_accelerate_py.voice_router` already provides TTS/STT provider selection,
  local Hugging Face inference, remote providers, backend-manager routing, and
  response caching.
- `ipfs_datasets_py` already provides IPLD knowledge graphs, vector stores,
  GraphRAG processing, and the 211 response-frame/slot concepts used by the UI.
- `Publicus/abby-voice` is a mutable Hugging Face bucket containing useful raw
  artifacts and run outputs. `Publicus/211-abby-tts` is the current dataset
  repository, but Dataset Viewer cannot build it because heterogeneous metadata,
  indexes, manifests, provenance, and response rows are interpreted as one
  schema.

Autonomous workers must not delete or rewrite remote Hugging Face bucket or
dataset content. Remote migration is plan-only until a human explicitly
approves a reviewed manifest and dry-run receipt.

## Reuse-first execution design

The implementation boundary is intentionally split between the two existing
submodules:

- `ipfs_datasets_py` is the voice-data control plane. It owns immutable
  Hugging Face inventory receipts, verified downloads and cache entries,
  canonical Abby voice rows, normalization and quarantine, GraphRAG indexes,
  audio-to-row reconciliation, release manifests, deterministic Parquet
  materialization, and post-publication verification.
- `ipfs_accelerate_py` is the audio execution plane. It owns durable DuckDB
  tasks, worker and mesh capability discovery, provider/model/device routing,
  resource admission, provider batching and single-flight execution, retries,
  TTS/ASR execution through `voice_router`, and privacy-safe job receipts.
- `ipfs_accelerate_py.agent_supervisor` implements and verifies the bounded
  goals in this heap. It is not the high-volume audio-row queue. Dataset jobs
  run through `ipfs_accelerate_py.p2p_tasks.TaskQueue`.

The target flow is:

```text
pinned HF dataset commit + checksummed bucket inventory
  -> verified content-addressed cache
  -> canonical Abby normalization / quarantine / GraphRAG index
  -> deterministic missing-or-revalidate workset
  -> DuckDB P2P tasks
  -> capability + resource admission
  -> provider batch scheduler
  -> voice_router TTS or ASR provider
  -> immutable audio artifact descriptor + execution receipt
  -> dataset reconciliation and audio quality gates
  -> deterministic Parquet release candidate
  -> human-approved append-only HF publication
  -> download by returned commit SHA and revalidate
```

ASR and STT share one canonical scheduled operation, `voice.asr`. The job
field `purpose` distinguishes `runtime_stt` from
`dataset_asr_validation`; private runtime caller audio is ephemeral and can
never enter the public Abby release. TTS, ASR, and audio validation remain
separate composable jobs so each one is independently retryable, auditable,
and cacheable.

Remote bucket objects are raw immutable inputs. The Hugging Face dataset
repository is a curated release surface containing schema-stable Parquet,
manifests, GraphRAG support indexes, and immutable references to verified
audio. Large audio bytes and base64 values must not be stored in DuckDB task
rows, supervisor evidence, logs, or ordinary router receipts.

## ABBY-VOICE-G001 Deliver a unified grounded Abby voice pipeline

- Status: complete
- Fib priority: 1000
- Priority: P0
- Track: voice-platform
- Goal: Deliver a reusable voice turn pipeline that transcribes caller audio, retrieves grounded 211 evidence and reusable response frames, renders safe spoken text, synthesizes audio, and returns provenance and fallback metadata.
- Evidence: unified VoiceTurnRequest and VoiceTurnResult contracts in `ipfs_accelerate_py/ipfs_accelerate_py/voice_router.py`; an injected GraphRAG response-template retrieval boundary; one offline test that proves transcription, grounded template rendering, synthesis, provenance, stage trace, and deterministic degradation; architecture and objective-validation receipts that map every claim to a repository path
- Outputs: docs/architecture/ABBY_VOICE_ROUTER_ARCHITECTURE.md, ipfs_accelerate_py/ipfs_accelerate_py/voice_router.py, tests/voice/test_abby_voice_pipeline.py, data/abby_voice/agent_supervisor/discovery/2026-07-23-abby-voice-auto-001-objective-validation-repair.md
- Validation: python -m pytest -q tests/voice/test_abby_voice_pipeline.py
- Bundle: abby-voice/integration
- Parallel lane: abby-voice-integration
- Embedding query: Abby grounded voice turn STT GraphRAG response templates TTS fallback provenance
- AST query: VoiceTurnRequest, VoiceTurnResult, process_voice_turn, GraphRAGVoiceTemplateProvider
- Interfaces: ipfs_accelerate_py.voice_router, ipfs_datasets_py GraphRAG, wallet voice proxy
- Submodules: ipfs_accelerate_py, ipfs_datasets_py
- Predicted files: docs/architecture/ABBY_VOICE_ROUTER_ARCHITECTURE.md, ipfs_accelerate_py/ipfs_accelerate_py/voice_router.py, tests/voice/test_abby_voice_pipeline.py
- Conflict policy: integrate child-goal contracts only after their focused tests pass; preserve backward compatibility for text_to_speech and speech_to_text
- Gap task: Integrate the child deliverables into one backward-compatible process_voice_turn API and record an offline end-to-end acceptance receipt.
- Objective-validation repair: `ABBY-VOICE-AUTO-001` owns the cross-child validation gate. The source discovery scan found the phrase `objective validation repair` missing and attributed the other evidence to unrelated JSON by AST token coincidence. The authoritative replacement is `data/abby_voice/agent_supervisor/discovery/2026-07-23-abby-voice-auto-001-objective-validation-repair.md`; evidence is valid only when it names the defining or asserting source path.
- Acceptance gate:
  1. Importing `ipfs_accelerate_py.voice_router` remains optional-dependency safe, and the existing `text_to_speech` and `speech_to_text` entry points remain compatible.
  2. `process_voice_turn` accepts injected STT, template-retrieval, and TTS collaborators so the complete route is testable without network access, credentials, mutable datasets, or heavyweight model downloads.
  3. The success receipt contains the transcript, grounded rendered response, non-empty audio, selected providers, `transcription` → `retrieval` → `rendering` → `synthesis` traces, retrieved source provenance, and no fallback reason. A grounded slot cites a present source ID; when that source declares the corresponding fact, its value must match.
  4. The degraded receipt is deterministic when no grounded template is returned: it does not invent a factual service claim, records the template-stage degradation and fallback reason, and still synthesizes the safe response when TTS is available.
  5. An STT failure returns status `failed`, skips retrieval/rendering, and synthesizes a deterministic safe handoff when TTS is available. A total TTS failure preserves grounded text and provenance with status `text_only` and no false audio.
  6. `python -m pytest -q tests/voice/test_abby_voice_pipeline.py` passes and the result is recorded in the objective-validation repair receipt.
- Child-goal boundary: no additional child goal is needed for this repair. G002 owns typed contracts, G003 provider fallback, G004/G005/G011 curated data, G007 retrieval, G008 router/template composition, and G009 safety evaluation. G001 owns only their offline integration gate and evidence receipt; it does not mark those independently active goals complete.

## ABBY-VOICE-G002 Define stable voice-turn and provider contracts

- Status: complete
- Fib priority: 2000
- Priority: P0
- Track: voice-router
- Parents: ABBY-VOICE-G001
- Goal: Replace byte-or-string-only routing with typed request result capability and trace contracts while preserving the existing public TTS and STT functions.
- Evidence: versioned and privacy-safe VoiceTurnRequest serialization; validated VoiceTurnResult, VoiceTurnProvenance, and VoiceStageTrace receipts; serializable VoiceProviderCapabilities and ProviderInfo metadata; capability-aware registry routing; complete cache identities; direct compatibility tests for text_to_speech and speech_to_text; ABBY-VOICE-G002 completion receipt
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/voice_router.py, ipfs_accelerate_py/test/test_voice_router_contracts.py, data/abby_voice/agent_supervisor/discovery/2026-07-23-abby-voice-auto-002-objective-validation-repair.md
- Validation: python -m pytest -q ipfs_accelerate_py/test/test_voice_router_contracts.py ipfs_accelerate_py/test/test_voice_router_integration.py
- Bundle: abby-voice/voice-router-contracts
- Parallel lane: abby-voice-router
- Embedding query: typed voice router contracts provider capabilities stage traces backward compatibility
- AST query: VoiceProvider, text_to_speech, speech_to_text, VoiceTurnRequest, VoiceTurnResult
- Interfaces: ipfs_accelerate_py.voice_router public API
- Submodules: ipfs_accelerate_py
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/voice_router.py, ipfs_accelerate_py/test/test_voice_router_contracts.py
- Conflict policy: retain current function signatures and lazy optional dependencies; add new orchestration as an additive API
- Gap task: Introduce serializable typed contracts for audio input transcript retrieval template rendered text audio output provider selection fallback reason cache identity timings and provenance.
- Objective-validation repair: `ABBY-VOICE-AUTO-002` owns this validation gate. The source discovery scan found the phrase `objective validation repair` missing and attributed contract terms to unrelated Chainlink, ProveKit, and IndexTTS artifacts by token coincidence. The authoritative replacement is `data/abby_voice/agent_supervisor/discovery/2026-07-23-abby-voice-auto-002-objective-validation-repair.md`; evidence is accepted only when it names the defining source and focused assertion.
- Acceptance gate:
  1. `VoiceTurnRequest` validates that audio or a transcript is present, normalizes provider/model/locale/options fields, derives deterministic audio identity from bytes or current file contents, serializes every routing-affecting field, and excludes raw audio and local paths unless transport serialization is explicitly requested.
  2. `VoiceTurnResult`, `VoiceTurnProvenance`, and `VoiceStageTrace` reject invalid statuses and malformed values, normalize sequence/mapping fields, expose provider selection, fallback, cache identity, duration, audio metadata, hashes, and provenance, and produce JSON-safe receipts with output audio omitted by default.
  3. `VoiceProviderCapabilities` and `ProviderInfo` preserve explicit STT, TTS, streaming, and format metadata. Registry lookup is canonical, capabilities are discoverable without constructing optional providers, unsupported operations are skipped, and re-registration invalidates the global provider cache.
  4. Voice-turn and legacy response-cache identities cover every output-affecting option, current file content, and injected provider instance. They contain hashes rather than caller audio, transcript, fallback wording, or request IDs.
  5. Importing `ipfs_accelerate_py.voice_router` remains optional-dependency safe. The established keyword-only signatures and bytes/string returns of `text_to_speech` and `speech_to_text`, provider injection, arbitrary provider kwargs, response caching, and `output_path` behavior remain compatible.
  6. `python -m pytest -q ipfs_accelerate_py/test/test_voice_router_contracts.py ipfs_accelerate_py/test/test_voice_router_integration.py` passes and its result is recorded in the objective-validation repair receipt.
- Child-goal boundary: no additional child goal is needed. G002 owns typed contracts, capability metadata, identity isolation, and compatibility only. G003 remains responsible for provider adapters and production fallback policy; G008 remains responsible for GraphRAG template composition and orchestration behavior.

## ABBY-VOICE-G003 Port Abby provider fallback behavior into voice_router

- Status: complete
- Fib priority: 3000
- Priority: P0
- Track: voice-router
- Parents: ABBY-VOICE-G002
- Goal: Make the Python voice router capable of the same ordered remote local and degraded behaviors used by the wallet voice assistant without importing UI-specific code.
- Evidence: dependency-light `IndexTTSHTTPProvider` and `HuggingFaceWhisperHTTPProvider` adapters with injected stdlib transports; lazy `abby_indextts` and `abby_whisper` router capabilities and aliases; ordered capability-aware remote/local fallback; bounded transient retry, timeout, backoff, and per-endpoint circuit breakers; privacy-safe `AbbyProviderReceipt` attempt history embedded in structured degraded `VoiceTurnResult` traces; 28 focused offline assertions; ABBY-VOICE-G003 completion receipt
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/voice_providers/abby.py, ipfs_accelerate_py/ipfs_accelerate_py/voice_router.py, ipfs_accelerate_py/test/test_abby_voice_providers.py, data/abby_voice/agent_supervisor/discovery/2026-07-23-abby-voice-auto-004-objective-validation-repair.md
- Validation: python -m pytest -q ipfs_accelerate_py/test/test_abby_voice_providers.py
- Bundle: abby-voice/provider-routing
- Parallel lane: abby-voice-router
- Embedding query: IndexTTS Whisper remote local fallback retry timeout circuit breaker voice proxy
- AST query: _run_indextts_gradio_tts, _run_hf_whisper_stt, get_voice_provider, ProviderInfo
- Interfaces: VoiceProviderCapabilities, Abby IndexTTS HTTP, Abby Whisper HTTP
- Submodules: ipfs_accelerate_py
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/voice_providers/abby.py, ipfs_accelerate_py/ipfs_accelerate_py/voice_router.py, ipfs_accelerate_py/test/test_abby_voice_providers.py
- Conflict policy: adapters must be optional and secret-free; tests use injected transports and never call paid or mutable remote services
- Gap task: Extract provider-neutral behavior from wallet_interface helpers into injectable adapters and prove provider selection fallback and error normalization.
- Objective-validation repair: `ABBY-VOICE-AUTO-004` owns this validation gate. The source discovery scan attributed adapter, fallback, resilience, receipt, and completion terms to unrelated Chainlink, ProveKit, and IndexTTS batch artifacts through AST-token coincidence. Those files are not G003 evidence. The defining implementation, focused offline assertions, and exact validation result are mapped in `data/abby_voice/agent_supervisor/discovery/2026-07-23-abby-voice-auto-004-objective-validation-repair.md`.
- Acceptance gate:
  1. Importing `voice_providers.abby` has no optional model, UI, credential, or network side effect. The router lazily resolves canonical `abby_indextts`/`abby_whisper` names and aliases, exposes their synthesis-only/transcription-only capabilities without construction, and leaves automatic legacy provider selection unchanged.
  2. IndexTTS sends normalized JSON synthesis requests through an injected transport, applies optional authorization and billing headers only when configured, accepts direct or base64 audio and same-origin audio references, rejects malformed/empty/unsafe responses, and retains the migration symbol `_run_indextts_gradio_tts`.
  3. Whisper reads byte or current local-file audio, sends raw audio with normalized model URL, content type, language, authorization, billing, and finite timeout, extracts supported nested transcription forms, rejects empty/malformed results, and retains the migration symbol `_run_hf_whisper_stt`.
  4. Explicit preferred/fallback chains are authoritative, de-duplicated, capability-filtered before provider construction, attempted in exact order, and stop on first success. A failed remote followed by local success records the selected local provider, failed and successful traces, content hashes, and `stt_provider_fallback` or `tts_provider_fallback`; all TTS failures return text-only and all STT failures return a failed safe-handoff receipt.
  5. Timeout, connection, HTTP 408/425/429, and 5xx failures retry no more than the configured bound with capped injected backoff and the same finite per-attempt timeout. Terminal validation and HTTP 400/401/403/404/422 failures do not retry or open circuits.
  6. Each provider endpoint has an isolated, lock-protected circuit. Consecutive exhausted transient calls open it; open calls fail without transport I/O; one half-open probe is admitted after cooldown; probe success closes and resets it while failure reopens it.
  7. `AbbyProviderReceipt` records sanitized endpoint, attempt number, status, duration, HTTP status, retryability, selected endpoint, and error code. Router traces retain that receipt while excluding credentials, prompts, caller audio, local paths, and synthesized bytes; Bearer/query/assignment credential forms and reflected caller input are redacted.
  8. Unexpected coroutine results are closed and rejected at the synchronous `VoiceProvider` boundary, allowing the next fallback without an unawaited-coroutine leak. Existing `text_to_speech` and `speech_to_text` signatures and bytes/string returns remain unchanged.
  9. `python -m pytest -q ipfs_accelerate_py/test/test_abby_voice_providers.py` passes offline and the result is recorded in the objective-validation repair receipt.
- Child-goal boundary: no smaller child goal is needed. G003 owns dependency-light remote adapters, resilience, capability-aware provider order, and adapter/degraded receipt evidence. G008 owns GraphRAG template retrieval and grounded turn composition; G010 owns wallet/UI adoption.

## ABBY-VOICE-G004 Define the canonical Abby voice dataset schema

- Status: complete
- Fib priority: 3001
- Priority: P0
- Track: voice-data
- Parents: ABBY-VOICE-G001
- Goal: Define a flat versioned dataset contract that ipfs_datasets_py and Hugging Face Dataset Viewer can load without interpreting indexes or manifests as response rows.
- Evidence: `abby_voice_response_v2`, `abby_voice_template_v2`, `abby_voice_audio_v2`, and `abby_voice_provenance_v2` definitions and typed rows in `ipfs_datasets_py/ipfs_datasets_py/voice/schema.py`; strict schema, migration, bundle-reference, publication-policy, and Arrow/Parquet round-trip fixtures in `ipfs_datasets_py/tests/unit/voice/test_abby_voice_schema.py`; column and release-layout contract in `docs/data/ABBY_VOICE_DATASET_SCHEMA.md`; ABBY-VOICE-G004 objective-validation repair receipt
- Outputs: ipfs_datasets_py/ipfs_datasets_py/voice/schema.py, ipfs_datasets_py/tests/unit/voice/test_abby_voice_schema.py, docs/data/ABBY_VOICE_DATASET_SCHEMA.md, data/abby_voice/agent_supervisor/discovery/2026-07-23-abby-voice-auto-003-objective-validation-repair.md
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/voice/test_abby_voice_schema.py
- Bundle: abby-voice/dataset-schema
- Parallel lane: abby-voice-data
- Embedding query: flat versioned Abby voice dataset schema responses templates audio provenance Hugging Face
- AST query: AbbyVoiceResponse, AbbyVoiceTemplate, AbbyVoiceAudio, AbbyVoiceProvenance
- Interfaces: ipfs_datasets_py.voice schema, Hugging Face datasets Arrow and Parquet
- Submodules: ipfs_datasets_py
- Predicted files: ipfs_datasets_py/ipfs_datasets_py/voice/schema.py, ipfs_datasets_py/tests/unit/voice/test_abby_voice_schema.py, docs/data/ABBY_VOICE_DATASET_SCHEMA.md
- Conflict policy: keep runtime indexes and aggregate manifests out of row files; use stable IDs and nullable scalar or consistently typed list columns
- Gap task: Specify normalized rows for utterances response frames slot values audio assets and provenance with content hashes licensing consent locale safety labels and source CIDs.
- Objective-validation repair: `ABBY-VOICE-AUTO-003` owns the G004 validation gate. The source discovery scan attributed the four schema names and migration evidence to unrelated ProveKit, Chainlink, review-matrix, and IndexTTS batch JSON through AST-token coincidence. Those artifacts are not G004 evidence. The authoritative evidence map and focused validation result are recorded in `data/abby_voice/agent_supervisor/discovery/2026-07-23-abby-voice-auto-003-objective-validation-repair.md`.
- Acceptance gate:
  1. The exact, separate `abby_voice_response_v2`, `abby_voice_template_v2`, `abby_voice_audio_v2`, and `abby_voice_provenance_v2` contracts are importable through dependency-light typed rows; no config accepts a row from another config.
  2. Serialized rows contain only fixed scalar, nullable scalar, and non-null `list[string]` columns. Runtime indexes, aggregate manifests, raw audio bytes, and arbitrary metadata objects are rejected as rows.
  3. Stable IDs, full SHA-256 integrity values, explicit licensing and consent state, BCP-47-style locale, safety labels, provenance references, and source CIDs are represented and validated. Grounded response slot name/value/source-CID lists stay aligned.
  4. Template placeholders use simple declared slot names only; required and factual slots are declared subsets. Audio remains externally addressed and provenance identifies a present response, template, or audio subject when validated as a bundle.
  5. Legacy migration is deterministic and non-mutating, recomputes canonical hashes/IDs, refuses truncated hashes as integrity evidence, and rejects manifest/index wrappers. Structural migration permits quarantine metadata, while a separate publication gate refuses unknown consent or licensing.
  6. Lazy Hugging Face and PyArrow schema adapters expose fixed feature types without making either optional dependency an import-time requirement. Focused Arrow/Parquet fixtures preserve nullable scalars and empty typed lists.
  7. `python -m pytest -q ipfs_datasets_py/tests/unit/voice/test_abby_voice_schema.py` passes and the result is recorded in the objective-validation repair receipt.
- Child-goal boundary: no smaller child goal is needed. G004 owns the cohesive row-contract and focused validation gate. G005 owns batch normalization, de-duplication, and quarantine; G011 owns curated materialization and Dataset Viewer/Parquet output; G006 owns the review-only remote migration plan.

## ABBY-VOICE-G005 Build deterministic dataset normalization and quality gates

- Status: complete
- Fib priority: 5000
- Priority: P0
- Track: voice-data
- Parents: ABBY-VOICE-G004
- Goal: Convert the existing manifests and response corpus into canonical rows while detecting low-value vocabulary fragments malformed spoken text duplicates ungrounded claims missing audio and inconsistent slots.
- Evidence: dependency-light `AbbyVoiceDatasetNormalizer`, stable source references/content IDs/splits, canonical response/template/audio/provenance output, text/audio duplicate winner ledger, `normalize_indextts_spoken_text` corruption checks, grounded slot-fidelity and factual-claim gates, lossless quarantine records, deterministic quality/build manifests in `ipfs_datasets_py/ipfs_datasets_py/voice/normalize.py` and `scripts/build_abby_voice_dataset_v2.py`; 16 focused offline assertions in `ipfs_datasets_py/tests/unit/voice/test_abby_voice_normalize.py`; objective-validation receipt in `data/abby_voice/agent_supervisor/discovery/2026-07-23-abby-voice-auto-005-objective-validation-repair.md`
- Outputs: ipfs_datasets_py/ipfs_datasets_py/voice/normalize.py, scripts/build_abby_voice_dataset_v2.py, ipfs_datasets_py/tests/unit/voice/test_abby_voice_normalize.py, data/abby_voice/agent_supervisor/discovery/2026-07-23-abby-voice-auto-005-objective-validation-repair.md
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/voice/test_abby_voice_normalize.py
- Bundle: abby-voice/dataset-normalization
- Parallel lane: abby-voice-data
- Embedding query: Abby dataset normalize deduplicate quarantine short fragments malformed speech slot fidelity audio availability
- AST query: normalize_indextts_spoken_text, deduplicate_voice_response_chunks, build_slotted_response_dag
- Interfaces: Abby voice v2 schemas, existing pregenerated response manifests
- Submodules: ipfs_datasets_py
- Predicted files: ipfs_datasets_py/ipfs_datasets_py/voice/normalize.py, scripts/build_abby_voice_dataset_v2.py, ipfs_datasets_py/tests/unit/voice/test_abby_voice_normalize.py
- Conflict policy: normalization must be deterministic and non-destructive; every rejected row receives machine-readable reason codes and source references
- Gap task: Reuse the strongest current dedupe and slotted-response logic behind an ipfs_datasets_py normalization API and produce reproducible quality statistics.
- Objective-validation repair: `ABBY-VOICE-AUTO-005` owns the G005 validation gate. The source discovery scan attributed normalization, de-duplication, corruption, slot-fidelity, quality-summary, and completion evidence to unrelated ProveKit, Chainlink, transcript, and IndexTTS batch artifacts through AST-token coincidence. Those artifacts are not G005 evidence. The defining implementation, focused assertions, checked-in corpus dry run, and exact validation result are mapped in `data/abby_voice/agent_supervisor/discovery/2026-07-23-abby-voice-auto-005-objective-validation-repair.md`.
- Acceptance gate:
  1. Aggregate legacy response manifests, top-level record lists, canonical rows, and JSONL inputs normalize without mutating their source objects or files. Source references use a stable legacy ID or complete source-row SHA-256 and never an array position.
  2. Normalized output is independent of input order and wall-clock time. Response/template IDs, real audio-byte hashes/IDs, provenance IDs, split assignments, ordering, JSONL bytes, quality statistics, checksums, and the build manifest are deterministic on rerun.
  3. Accepted response, template, audio, and provenance values use the separate canonical Abby voice v2 row contracts. Audio integrity comes from a full declared or locally verified SHA-256, never a path or truncated legacy text hash.
  4. Canonical spoken-text identity drives text de-duplication; full audio-byte SHA-256 drives audio de-duplication. Each group records one deterministic survivor, every duplicate source reference, merge outcome, reason code, and count.
  5. Empty text, source-aware low-value vocabulary, empty-quote/control/replacement/residual-markup/placeholder corruption, ungrounded factual claims, missing or unverifiable audio under the configured policy, audio hash mismatch, and inconsistent slot/placeholder/source binding are covered by focused quarantine assertions.
  6. Every rejected source row remains recoverable in `QuarantineRecord` with the original JSON-safe value, full source-row SHA-256, stable source reference, sorted reason codes, field diagnostics, and optional candidate ID. Planned missing audio can be retained as a visible warning or promoted to quarantine by policy.
  7. The quality report deterministically reconciles input, accepted canonical configs, quarantine/warning reason counts, text/audio duplicate counts, and split counts. The builder writes separate schema-stable JSONL configs plus quarantine, warnings, duplicate ledger, split map, quality report, and checksummed manifest through atomic local replacements.
  8. The CLI is offline and non-destructive, accepts manifests/directories/JSONL, supports strict audio/grounding/quarantine gates, validates bundle references and checksums with `--check`, and proves byte-identical reruns with `--check-idempotence`; it performs no remote bucket or Hugging Face mutation.
  9. `python -m pytest -q ipfs_datasets_py/tests/unit/voice/test_abby_voice_normalize.py` passes and the result is recorded in the objective-validation repair receipt.
- Child-goal boundary: no smaller child goal is needed. G005 owns the reusable normalization API, deterministic de-duplication/quality evidence, quarantine policy, local JSONL builder, and focused unit gate. G011 owns immutable remote-source inventory, full curated materialization, Parquet/Dataset Viewer compatibility, and byte-identical release artifacts. G006 owns the human-reviewed remote migration plan, and G007 owns searchable GraphRAG ingestion/retrieval.

## ABBY-VOICE-G006 Produce a safe Hugging Face bucket and dataset migration plan

- Status: complete
- Fib priority: 5001
- Priority: P1
- Track: voice-data
- Parents: ABBY-VOICE-G004, ABBY-VOICE-G005
- Goal: Separate mutable run artifacts from curated Dataset Viewer data and prepare a reviewable migration without changing remote state.
- Evidence: bucket inventory summary, proposed canonical prefix layout, Hugging Face dataset YAML with separate configs and splits, dry-run copy upload and delete plan, Dataset Viewer validation procedure, ABBY-VOICE-G006 completion receipt
- Outputs: docs/data/ABBY_VOICE_HF_MIGRATION_PLAN.md, data/abby_voice/huggingface/README.template.md, data/abby_voice/huggingface/migration-plan.json
- Validation: python scripts/build_abby_voice_dataset_v2.py --check --output-dir /tmp/abby-voice-v2-check && test -f data/abby_voice/huggingface/migration-plan.json
- Bundle: abby-voice/huggingface-migration
- Parallel lane: abby-voice-data
- Embedding query: Hugging Face bucket curated dataset configs splits Parquet migration dry run no delete
- AST query: upload_hf_abby_tts_dataset, data_files, configs, list_bucket_tree, sync_bucket
- Interfaces: Publicus/abby-voice bucket, Publicus/211-abby-tts dataset
- Submodules: ipfs_datasets_py
- Generated artifacts: data/abby_voice/huggingface/migration-plan.json
- Predicted files: docs/data/ABBY_VOICE_HF_MIGRATION_PLAN.md, data/abby_voice/huggingface/README.template.md, data/abby_voice/huggingface/migration-plan.json
- Conflict policy: prohibit remote writes moves and deletes; only emit a local dry-run plan with checksums counts costs and rollback notes for human approval
- Gap task: Plan separate responses templates audio provenance and evaluation configs in Parquet while retaining raw bucket inputs under date and run scoped prefixes.
- Objective-validation repair: `ABBY-VOICE-AUTO-009` owns this validation gate. The source discovery scan found the phrase `objective validation repair` missing and attributed inventory, prefix, Dataset Viewer, and migration terms to unrelated artifacts through AST-token coincidence. The authoritative replacement is `data/abby_voice/agent_supervisor/discovery/2026-07-23-abby-voice-auto-009-objective-validation-repair.md`; the machine-readable plan, dataset-card template, focused safety assertions, and this acceptance gate are the only G006 evidence.
- Acceptance gate:
  1. `data/abby_voice/huggingface/migration-plan.json` records the two source interfaces, the read-only inventory boundary, known mutable/raw prefixes, a canonical date/run-scoped bucket layout, five isolated Parquet configs (`responses`, `templates`, `audio`, `provenance`, and `evaluation`), and explicit split-to-`data_files` mappings.
  2. The plan contains reproducible local counts and SHA-256 evidence from `build_abby_voice_dataset_v2.py --check`, while remote object counts, byte totals, and monetary costs remain null until a human-approved read-only snapshot. It provides formulas and a receipt schema instead of inventing remote state.
  3. The dry-run copy/upload/delete plan can inventory with `list_bucket_tree`, stage through `upload_hf_abby_tts_dataset`, and describe `sync_bucket`/copy operations, but has no upload, move, rewrite, or delete action enabled. The delete plan is an empty prohibited operation set.
  4. `data/abby_voice/huggingface/README.template.md` is a valid Dataset Card template whose YAML declares the same five configs and split paths; no config directory contains manifests, indexes, batch wrappers, or run output.
  5. The Dataset Viewer procedure validates schema columns, Parquet readability, split isolation, row counts, checksums, and a smoke load before any human-approved remote publication. Rollback is by selecting the previous immutable release/revision; it never deletes or rewrites the legacy source.
  6. `python -m pytest -q tests/voice/test_abby_voice_hf_migration.py` passes offline and records the required evidence mapping in the repair receipt. No focused assertion calls Hugging Face, requires credentials, or mutates a remote source.
- Child-goal boundary: no smaller child goal is needed. G006 owns the human-reviewed migration plan and safety gate; G011 owns immutable inventory plus complete curated Parquet materialization, and G009 owns evaluation fixture content. G006 does not claim that remote inventory or publication has occurred.

## ABBY-VOICE-G007 Add GraphRAG response-template ingestion and retrieval

- Status: complete
- Fib priority: 5002
- Priority: P0
- Track: voice-graphrag
- Parents: ABBY-VOICE-G004, ABBY-VOICE-G005, ABBY-VOICE-G011
- Goal: Ingest canonical response frames evidence links and slot relationships into ipfs_datasets_py and retrieve them as response plans rather than uncited final answers.
- Evidence: dependency-light `GraphRAGVoiceTemplateProvider` and `SlottedResponseIndex`; deterministic CID-addressed intent/template/slot/evidence/response/audio/provenance graph with injected `IPLDKnowledgeGraph` publication; lexical, sparse-vector, injected `IPLDVectorStore`, and graph hybrid ranking; fail-closed current-evidence slot binding that never uses historical response values as facts; 19 focused offline ingestion, safety, ranking, provenance, serialization, and optional-collaborator assertions; ABBY-VOICE-G007 objective-validation completion receipt
- Outputs: ipfs_datasets_py/ipfs_datasets_py/voice/graphrag.py, ipfs_datasets_py/tests/unit/voice/test_abby_voice_graphrag.py, docs/data/ABBY_VOICE_GRAPHRAG.md, data/abby_voice/agent_supervisor/discovery/2026-07-23-abby-voice-auto-006-objective-validation-repair.md
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/voice/test_abby_voice_graphrag.py
- Bundle: abby-voice/graphrag-templates
- Parallel lane: abby-voice-graphrag
- Embedding query: GraphRAG response frame intent slot evidence provenance hybrid retrieval Abby 211
- AST query: IPLDKnowledgeGraph, IPLDVectorStore, GraphRAGLLMProcessor, SlottedResponseIndex
- Interfaces: GraphRAGVoiceTemplateProvider, ipfs_datasets_py vector store, IPLD knowledge graph
- Submodules: ipfs_datasets_py
- Predicted files: ipfs_datasets_py/ipfs_datasets_py/voice/graphrag.py, ipfs_datasets_py/tests/unit/voice/test_abby_voice_graphrag.py, docs/data/ABBY_VOICE_GRAPHRAG.md
- Conflict policy: retrieved templates are response plans only; factual slots must bind from current cited evidence and never from stale example wording
- Gap task: Model caller intents response frames slots evidence documents and audio assets as a queryable graph with confidence thresholds and source CIDs.
- Objective-validation repair: `ABBY-VOICE-AUTO-006` owns this validation gate. The source discovery scan found the phrase `objective validation repair` missing and attributed the provider, graph, hybrid retrieval, slot policy, provenance tests, and completion evidence to unrelated Chainlink, ProveKit, conversation, and IndexTTS artifacts through AST/token coincidence. Those files are not G007 evidence. The defining implementation, focused offline assertions, exact validation result, and evidence-term mapping are recorded in `data/abby_voice/agent_supervisor/discovery/2026-07-23-abby-voice-auto-006-objective-validation-repair.md`.
- Acceptance gate:
  1. Canonical Abby voice v2 template, response, audio, and provenance configs are strictly validated and atomically merged into deterministic intent/template/slot/evidence/response/audio/provenance nodes and typed relationships. Exact duplicates are idempotent; conflicting IDs, broken references, and slotted templates without source-CID allowlists reject.
  2. Canonical graph and index serialization is independent of input order, clocks, UUIDs, Python hashes, local paths, and mutable remote state. Valid CIDv1 identities cover sorted graph content and canonical indexed rows, checked export/restore preserves identity, and tampering fails validation.
  3. `SlottedResponseIndex` combines exact/lexical, deterministic sparse-vector or injected vector-store, and graph/source-coverage signals; enforces locale, explicit intent, confidence, and result limits; and breaks equal-score ties by stable template ID.
  4. `GraphRAGVoiceTemplateProvider` exposes the synchronous backend methods recognized by the router and returns an unrendered plan with declared template, grounded slot structures, current evidence, confidence, intent, and machine provenance—not generated final-answer prose.
  5. Every placeholder binds only from an exact structured fact on current evidence whose CID is declared by the template. Missing, malformed, disallowed, or contradictory evidence fails closed, and canonical response example values are absent from evidence nodes and never read as current facts.
  6. Retrieval receipts preserve source IDs/CIDs, graph/index CIDs, score components, template checksum/source/provenance identities, historical match IDs, and audio IDs in stable JSON-safe order. Slot source IDs resolve to emitted evidence and exact fact values.
  7. `IPLDKnowledgeGraph`, `IPLDVectorStore`, and `GraphRAGLLMProcessor` integrations remain injected and optional. Importing the module loads no model/vector/IPLD extras or network client; query expansion can affect retrieval text only and cannot provide a slot or final answer.
  8. `python -m pytest -q ipfs_datasets_py/tests/unit/voice/test_abby_voice_graphrag.py` passes offline and the exact result is recorded in the objective-validation repair receipt.
- Child-goal boundary: no smaller child goal is needed. G007 owns canonical response-frame graph ingestion, deterministic hybrid template retrieval, and current-evidence binding. G008 owns router rendering and voice-turn orchestration, G009 owns cross-pipeline safety/performance evaluation, and G011 owns immutable inventory plus complete curated dataset materialization. G007 depends on the G004 schema and G005 normalization policy but does not wait for G011 to ingest already canonical rows.

## ABBY-VOICE-G008 Integrate GraphRAG templating into voice_router

- Status: complete
- Fib priority: 8000
- Priority: P0
- Track: voice-graphrag
- Parents: ABBY-VOICE-G002, ABBY-VOICE-G003, ABBY-VOICE-G007
- Goal: Add an optional template provider to process_voice_turn that can retrieve a response plan bind only grounded facts normalize spoken text and synthesize the final response.
- Evidence: optional VoiceTemplateProvider protocol, grounded slot binding implementation, citation stripping with retained machine provenance, deterministic fallback response, integration tests with fake GraphRAG provider, ABBY-VOICE-G008 completion receipt
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/voice_router.py, ipfs_accelerate_py/ipfs_accelerate_py/voice_templates.py, ipfs_accelerate_py/test/test_voice_router_graphrag.py
- Validation: python -m pytest -q ipfs_accelerate_py/test/test_voice_router_graphrag.py
- Bundle: abby-voice/router-graphrag-integration
- Parallel lane: abby-voice-graphrag
- Embedding query: voice router GraphRAG template provider grounded slot binding spoken normalization provenance
- AST query: process_voice_turn, VoiceTemplateProvider, GraphRAGVoiceTemplateProvider, buildVoiceGraphRagPromptParts
- Interfaces: VoiceTemplateProvider, GraphRAGVoiceTemplateProvider, VoiceTurnResult
- Submodules: ipfs_accelerate_py, ipfs_datasets_py
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/voice_router.py, ipfs_accelerate_py/ipfs_accelerate_py/voice_templates.py, ipfs_accelerate_py/test/test_voice_router_graphrag.py
- Conflict policy: use dependency injection across submodules and avoid mandatory ipfs_datasets_py imports at voice_router import time
- Gap task: Implement STT to retrieval to safe response rendering to TTS orchestration with explicit fallback stages and provenance.
- Objective-validation repair: `ABBY-VOICE-AUTO-007` owns this validation gate. The source discovery scan incorrectly attributed the router's GraphRAG evidence to unrelated generated artifacts. The authoritative replacement is `data/abby_voice/agent_supervisor/discovery/2026-07-23-abby-voice-auto-007-objective-validation-repair.md`; the dependency-light template helper, router integration, focused offline suite, and this acceptance gate are the only G008 completion evidence.
- Acceptance gate:
  1. `voice_templates.py` exposes `buildVoiceGraphRagPromptParts` and its Pythonic alias as a deterministic, JSON-safe query envelope. It normalizes the transcript, preserves language/context/current grounding, validates result limits, and never produces a final answer or invents a slot value.
  2. `GraphRAGVoiceTemplateProvider` remains lazy and dependency-injected. It uses the canonical prompt envelope for opt-in backends, accepts legacy narrow backend signatures, normalizes candidate mappings into response plans, and applies confidence filtering without importing `ipfs_datasets_py` at router import time.
  3. `process_voice_turn` executes STT → retrieval → grounded rendering → TTS. Every factual placeholder requires a cited evidence source and agrees with any structured current fact; unsupported fields, missing sources, conflicting facts, malformed templates, and empty citation-stripped output fail closed.
  4. Spoken output removes visual URLs, CIDs, and citations while `VoiceTurnProvenance` retains template identity, evidence/CIDs, grounded slots, hashes, provider selection, stage traces, and fallback reasons. The deterministic safe fallback is synthesized when retrieval or grounding fails.
  5. `ipfs_accelerate_py/test/test_voice_router_graphrag.py` covers canonical prompt construction/non-mutation, citation normalization, STT-to-TTS ordering, opt-in GraphRAG prompt delivery, safe slot rejection, deterministic retrieval fallback, TTS text-only degradation, and template-expression rejection using only in-memory fakes.
  6. `python -m pytest -q ipfs_accelerate_py/test/test_voice_router_graphrag.py` passes offline. No focused assertion calls a remote speech service, GraphRAG deployment, IPFS node, or Hugging Face API.
- Child-goal boundary: no smaller child goal is needed. G008 owns the router-side prompt envelope, response-plan rendering, citation stripping, fallback orchestration, and focused gate. G007 owns canonical GraphRAG ingestion/retrieval, G009 owns evaluation, and G010 owns downstream wallet adoption.

## ABBY-VOICE-G009 Establish voice safety quality and performance evaluation

- Status: complete
- Fib priority: 8001
- Priority: P0
- Track: voice-evaluation
- Parents: ABBY-VOICE-G005, ABBY-VOICE-G007, ABBY-VOICE-G008
- Goal: Prevent autonomous optimization from trading away grounding privacy accessibility or emergency behavior for latency or response reuse.
- Evidence: `data/abby_voice/eval/golden_voice_turns.jsonl` provides eight synthetic, schema-versioned voice turns; `tests/voice/test_abby_voice_safety.py` provides eleven offline assertions for WER, retrieval, slot fidelity, grounded factuality, crisis routing, accessibility/readability, privacy-safe receipts, fallback, GraphRAG prompt handling, legacy STT, stage traces, and cache reuse; `benchmarks/bench_abby_voice_router.py` provides the offline latency/cache/fallback gate; `docs/reports/ABBY_VOICE_EVALUATION.md` is the completion receipt; objective-validation repair is recorded in `data/abby_voice/agent_supervisor/discovery/2026-07-23-abby-voice-auto-008-objective-validation-repair.md`
- Outputs: data/abby_voice/eval/golden_voice_turns.jsonl, tests/voice/test_abby_voice_safety.py, benchmarks/bench_abby_voice_router.py, docs/reports/ABBY_VOICE_EVALUATION.md
- Validation: python -m pytest -q tests/voice/test_abby_voice_safety.py && python benchmarks/bench_abby_voice_router.py --offline --check
- Bundle: abby-voice/evaluation
- Parallel lane: abby-voice-evaluation
- Embedding query: voice safety grounding privacy emergency accessibility WER slot fidelity latency fallback benchmark
- AST query: VoiceStageTrace, GraphRAGVoiceTemplateProvider, speech_to_text, text_to_speech
- Interfaces: Abby voice evaluation schema, VoiceTurnResult receipts
- Submodules: ipfs_accelerate_py, ipfs_datasets_py
- Generated artifacts: docs/reports/ABBY_VOICE_EVALUATION.md
- Predicted files: data/abby_voice/eval/golden_voice_turns.jsonl, tests/voice/test_abby_voice_safety.py, benchmarks/bench_abby_voice_router.py, docs/reports/ABBY_VOICE_EVALUATION.md
- Conflict policy: evaluation fixtures must contain synthetic or explicitly public data and no private caller audio or secrets
- Gap task: **completed** — build offline deterministic gates for emergency routing, source grounding, slot fidelity, spoken readability, privacy-safe receipts, fallback behavior, and latency budgets.
- Objective-validation repair: `ABBY-VOICE-AUTO-008` replaces the source scan's unrelated AST matches with the directly defining evaluation fixtures, focused assertions, offline benchmark, report, and receipt listed above. The repair is local-only and makes no remote provider or dataset call.
- Acceptance gate:
  1. The golden set contains only synthetic/publicly safe data and includes grounded, crisis, accessibility, no-match, unsafe-slot, privacy, and language-access cases.
  2. Focused tests measure mean STT WER <= 5%, successful retrieval for every response plan, 100% exact grounded slot/source fidelity, structured-fact factuality, crisis urgency/911 policy, readable citation-free speech, and privacy-safe receipts.
  3. Retrieval/grounding failures fail closed to the deterministic safe handoff; STT failure returns `failed`; total TTS failure returns `text_only`; provider fallback records failed and selected attempts.
  4. The offline benchmark enforces cache reuse, visible fallback receipts, route/fallback p95 <= 1000 ms, and all safety checks without network, credentials, model downloads, or mutable data.
  5. `python -m pytest -q tests/voice/test_abby_voice_safety.py && python benchmarks/bench_abby_voice_router.py --offline --check` passes, with the exact result recorded in the objective-validation repair receipt and evaluation report.
- Child-goal boundary: no smaller child goal is needed. G009 owns the cohesive evaluation gate; G010 remains responsible for wallet adoption and production/provider-specific latency measurement.

## ABBY-VOICE-G010 Adopt the unified router in wallet_interface

- Status: active
- Fib priority: 13000
- Priority: P1
- Track: voice-integration
- Parents: ABBY-VOICE-G008, ABBY-VOICE-G009
- Depends on: ABBY-VOICE-G019, ABBY-VOICE-G020
- Goal: Let the current Abby UI and service proxy use the shared contracts without removing its browser local-audio and browser-speech fallbacks.
- Evidence: the lazy, opt-in wallet adapter delegates to `process_voice_turn` and serializes the canonical `VoiceTurnResult`; the UI normalizer consumes that receipt while preserving legacy payloads; focused tests cover provenance, stage ordering, audio decoding, text-only degradation, and legacy rejection; `AgentAudioChatSurface` retains browser SpeechRecognition, local WebGPU, and browser speech fallback branches; the rollout runbook defines canary receipts and flag-off rollback; the ABBY-VOICE-AUTO-010 objective-validation repair receipt records both required gates
- Outputs: wallet_interface/helpers/_voice_router_adapter.py, wallet_interface/ui/src/features/agent/lib/voiceTurnResult.ts, wallet_interface/ui/tests/agent-voice-router.spec.ts, docs/runbooks/ABBY_VOICE_ROUTER_ROLLOUT.md
- Validation: python -m pytest -q wallet_interface/tests && npm --prefix wallet_interface/ui test -- tests/agent-voice-router.spec.ts
- Bundle: abby-voice/wallet-adoption
- Parallel lane: abby-voice-integration
- Embedding query: wallet Abby voice proxy shared router browser SpeechRecognition WebGPU browser speech rollout
- AST query: ClientAudioReplyService, RemoteSpeechToTextResult, AgentAudioChatSurface, VoiceTurnResult
- Interfaces: wallet voice proxy HTTP, VoiceTurnResult JSON, browser audio fallbacks
- Submodules: ipfs_accelerate_py
- Predicted files: wallet_interface/helpers/_voice_router_adapter.py, wallet_interface/ui/src/features/agent/lib/voiceTurnResult.ts, wallet_interface/ui/tests/agent-voice-router.spec.ts, docs/runbooks/ABBY_VOICE_ROUTER_ROLLOUT.md
- Conflict policy: use a feature flag and preserve all existing fallback paths until end-to-end receipts pass in deployed-like tests
- Gap task: Add an adapter and staged rollout that consumes the unified router result while retaining the proven client fallback chain.
- Objective-validation repair: `ABBY-VOICE-AUTO-010` owns the wallet adoption validation gate. The source scan incorrectly treated generated manifests and unrelated review artifacts as wallet-router evidence; the authoritative replacement is `data/abby_voice/agent_supervisor/discovery/2026-07-23-abby-voice-auto-010-objective-validation-repair.md`. Evidence is accepted only when the defining adapter, UI parser, focused test, fallback implementation, and runbook are named directly.
- Acceptance gate:
  1. `wallet_interface/helpers/_voice_router_adapter.py` imports the shared router lazily, is disabled by default with `WALLET_VOICE_UNIFIED_ROUTER_ENABLED`, accepts injected STT/template/TTS collaborators, and serializes the typed receipt without putting raw audio in ordinary router fields.
  2. The enabled adapter produces a canonical result with `status`, transcript, response text, provenance, ordered transcription/retrieval/rendering/synthesis traces, explicit fallback reasons, and an opt-in base64 audio wire field.
  3. `voiceTurnResult.ts` accepts snake_case and camelCase receipt fields, retains provenance and fallback metadata, decodes audio only when present, and does not reinterpret an unrelated legacy payload as a unified result.
  4. `ClientAudioReplyService`, `RemoteSpeechToTextResult`, and `AgentAudioChatSurface` continue to retain remote endpoint fallback, browser SpeechRecognition, local WebGPU, and browser speech-synthesis paths when the unified receipt is unavailable, degraded, or text-only.
  5. `python -m pytest -q wallet_interface/tests` and `npm --prefix wallet_interface/ui test -- tests/agent-voice-router.spec.ts` pass offline, and `docs/runbooks/ABBY_VOICE_ROUTER_ROLLOUT.md` defines a reversible canary/rollback procedure.
- Child-goal boundary: no smaller child goal is needed. G010 is the cohesive wallet/UI adoption and rollout-validation boundary; G008 owns router/template composition and G009 owns safety/performance evaluation.

## ABBY-VOICE-G011 Normalize and materialize the Abby voice dataset

- Status: active
- Fib priority: 5001
- Priority: P0
- Track: voice-data
- Parents: ABBY-VOICE-G004, ABBY-VOICE-G005
- Goal: Coordinate the reuse-first dataset and audio-job goals that turn immutable Abby source snapshots into a verified, schema-stable, GraphRAG-ready Hugging Face release.
- Evidence: immutable inventory; canonical normalization; deterministic audio worksets; TTS/ASR execution; audio reconciliation; deterministic release construction; runtime resolution; post-publication verification
- Outputs: data/abby_voice/normalized/manifest.json, data/abby_voice/normalized/quality-report.json, data/abby_voice/normalized/quarantine.jsonl, data/abby_voice/releases/release-manifest.json, data/abby_voice/agent_supervisor/discovery/ABBY-VOICE-G011-completion.md
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/voice tests/voice && python benchmarks/bench_abby_voice_router.py --offline --check
- Bundle: abby-voice/dataset-materialization
- Parallel lane: abby-voice-data
- Embedding query: immutable Hugging Face Abby voice normalization audio workset TTS ASR GraphRAG deterministic release
- AST query: AbbyVoiceDatasetNormalizer, ArtifactManifest, VoiceAudioJobSpec, AbbyVoiceHFReleaseBuilder
- Interfaces: ipfs_datasets_py.voice, ipfs_datasets_py ArtifactManifest, ipfs_accelerate_py p2p tasks, Hugging Face datasets and buckets
- Submodules: ipfs_datasets_py, ipfs_accelerate_py
- Generated artifacts: data/abby_voice/normalized/manifest.json, data/abby_voice/normalized/quality-report.json, data/abby_voice/normalized/quarantine.jsonl, data/abby_voice/releases/release-manifest.json
- Predicted files: ipfs_datasets_py/ipfs_datasets_py/voice, ipfs_accelerate_py/ipfs_accelerate_py/p2p_tasks, data/abby_voice/normalized, data/abby_voice/releases
- Conflict policy: treat all source bucket and dataset objects as immutable; perform no remote writes moves or deletes; make every transformation deterministic and preserve source URI revision checksum and rejection reason for audit and rollback
- Gap task: Integrate and verify G012 through G021 without replacing the existing schema normalizer GraphRAG router providers TaskQueue resource scheduler or provider batch scheduler.
- Acceptance gate:
  1. G012 through G020 are verified complete and G021 has either a human-approved publication receipt or remains explicitly blocked at its remote-write gate.
  2. Every discovered source row is classified as linked, synthesized, quarantined, or intentionally text-only; no unresolved row is silently omitted.
  3. Every admitted audio link is backed by downloaded-byte SHA-256, byte length, immutable subject identity, source revision, and provenance. Basename, truncated-hash, fuzzy-text, and mutable-`main` matches never auto-promote.
  4. Rebuilding the same pinned inputs produces byte-identical canonical rows, GraphRAG index identity, Parquet shards, and release manifest.
  5. DuckDB tasks and receipts contain descriptors and hashes rather than raw or base64 audio, credentials, private caller transcripts, or arbitrary local paths.
  6. The focused dataset, queue, provider, GraphRAG, safety, and release validation suites pass with an evidence receipt tied to the exact repository trees.
- Child-goal boundary: G012-G013 own immutable source management and normalization; G014-G016 own job contracts and execution; G017 owns reconciliation and audio quality; G018 owns release construction; G019 owns runtime resolution; G020 owns end-to-end verification; G021 alone owns human-gated remote publication.

## ABBY-VOICE-G012 Generalize immutable Hugging Face source snapshots

- Status: active
- Fib priority: 5002
- Priority: P0
- Track: voice-data
- Parents: ABBY-VOICE-G011
- Depends on: ABBY-VOICE-G004, ABBY-VOICE-G005, ABBY-VOICE-G006
- Goal: Reuse the existing SkillCenter immutable snapshot and verified-cache machinery as generic Hugging Face dataset and bucket source adapters for Abby.
- Evidence: `HuggingFaceSnapshot` and `HuggingFaceSnapshotCache` provide the reusable immutable snapshot/cache contract while the existing `SkillCenterSnapshot`, `SkillCenterSnapshotCache`, and `HuggingFaceSkillCenterFetcher` imports remain compatible; `HuggingFaceRepository` records a pinned dataset commit; `HuggingFaceBucketStore` produces a canonical inventory digest over path, size, full SHA-256, ETag, and media type; focused tests reject tampered bytes and mutable refs and prove a verified cache hit performs no fetch or network access; the authoritative evidence map is `data/abby_voice/agent_supervisor/discovery/2026-07-25-abby-voice-auto-011-objective-validation-repair.md`
- Outputs: ipfs_datasets_py/ipfs_datasets_py/huggingface/snapshot.py, ipfs_datasets_py/ipfs_datasets_py/huggingface/repository.py, ipfs_datasets_py/ipfs_datasets_py/huggingface/bucket.py, ipfs_datasets_py/ipfs_datasets_py/logic/intent_ir/source_adapters/snapshot.py, ipfs_datasets_py/tests/unit/huggingface/test_voice_source_snapshot.py, ipfs_datasets_py/tests/unit/logic/intent_ir/test_skillcenter_snapshot.py, data/abby_voice/agent_supervisor/discovery/2026-07-25-abby-voice-auto-011-objective-validation-repair.md
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/logic/intent_ir/test_skillcenter_snapshot.py ipfs_datasets_py/tests/unit/huggingface/test_voice_source_snapshot.py
- Bundle: abby-voice/hf-sources
- Parallel lane: abby-voice-data
- Embedding query: Hugging Face immutable revision bucket inventory content addressed cache Abby voice
- AST query: SkillCenterSnapshot, SkillCenterSnapshotCache, HuggingFaceSkillCenterFetcher, HuggingFaceSnapshot, HuggingFaceBucketStore
- Interfaces: huggingface_hub injected client, hf bucket CLI adapter, Artifact
- Submodules: ipfs_datasets_py
- Predicted files: ipfs_datasets_py/ipfs_datasets_py/huggingface/snapshot.py, ipfs_datasets_py/ipfs_datasets_py/huggingface/repository.py, ipfs_datasets_py/ipfs_datasets_py/huggingface/bucket.py, ipfs_datasets_py/tests/unit/huggingface/test_voice_source_snapshot.py
- Conflict policy: extract or wrap generic behavior while keeping the SkillCenter symbols import-compatible; inventory and downloads are read-only; reject branch names such as main and master from canonical receipts
- Gap task: Promote the existing pinned snapshot/cache pattern to a reusable API and add only the missing bucket inventory/fetch adapter.
- Objective-validation repair: `ABBY-VOICE-AUTO-011` owns this validation gate. The source discovery scan found the three terms `backward-compatible generic snapshot/cache API`, `tamper and mutable-ref rejection tests`, and `no-network cache-hit test` missing because it matched only unrelated inventory artifacts and the pre-generalization SkillCenter implementation. The authoritative replacement is `data/abby_voice/agent_supervisor/discovery/2026-07-25-abby-voice-auto-011-objective-validation-repair.md`; evidence is accepted only when it identifies the defining generic and compatibility symbols plus the focused offline assertion.
- Acceptance gate:
  1. The generic dataset snapshot/cache API carries Hugging Face dataset ID, immutable revision, relative repository path, expected full SHA-256, byte length, content CID, producer, and content-addressed cache path. Existing SkillCenter symbols remain import-compatible and retain their schema, serialization, artifact projection, read-only bundle reader, and injected Hugging Face fetcher behavior.
  2. Dataset sources resolve to an immutable Hugging Face commit SHA and each bucket inventory has a deterministic digest over normalized path, size, full SHA-256, ETag, and media type. Mutable refs such as `main`, `master`, `latest`, and `refs/heads/*`, path traversal, partial targets, and incomplete inventory metadata fail closed.
  3. Cache promotion is atomic and locked; aliases and every cache hit are revalidated against the requested manifest, size, and SHA-256. Focused tests prove fetched-byte tampering, cached-byte tampering, stale or unsafe aliases, and mutable refs are rejected.
  4. Network and CLI clients are injected and imports have no network or credential side effects. A focused cache-hit test first populates with an injected fetcher, then reopens with a fetcher and network function that both fail if invoked, proving verified bytes are returned without either path; a true offline miss raises the typed cache-miss error.
  5. Remote write, delete, move, overwrite, and release-pointer operations are absent. The exact command `python -m pytest -q ipfs_datasets_py/tests/unit/logic/intent_ir/test_skillcenter_snapshot.py ipfs_datasets_py/tests/unit/huggingface/test_voice_source_snapshot.py` passes and its result is recorded in the objective-validation repair receipt.
- Child-goal boundary: no smaller child goal is needed. The generic API, legacy compatibility, tamper/mutable-ref rejection, and no-network cache hit exercise one cohesive source-identity and verified-cache boundary. G013 owns Abby row interpretation and workset construction; G021 owns publication.

## ABBY-VOICE-G013 Build the Abby dataset manager and deterministic audio workset

- Status: active
- Fib priority: 5003
- Priority: P0
- Track: voice-data
- Parents: ABBY-VOICE-G011
- Depends on: ABBY-VOICE-G012
- Goal: Compose the existing Abby schema normalizer GraphRAG and ArtifactManifest APIs into one dataset manager that reconciles legacy candidates and emits deterministic missing-or-revalidate audio work.
- Evidence: canonical normalization; deterministic audio worksets; exact legacy adapter; complete inventory-to-disposition ledger; canonical four-config bundle; explicit evaluation-support artifact decision; deterministic TTS ASR and validation work manifests; fuzzy-review quarantine; authoritative evidence map: data/abby_voice/agent_supervisor/discovery/2026-07-25-abby-voice-auto-012-objective-validation-repair.md
- Outputs: ipfs_datasets_py/ipfs_datasets_py/voice/dataset_manager.py, ipfs_datasets_py/ipfs_datasets_py/voice/legacy_sources.py, ipfs_datasets_py/ipfs_datasets_py/voice/workset.py, ipfs_datasets_py/tests/unit/voice/test_abby_voice_dataset_manager.py, data/abby_voice/agent_supervisor/discovery/2026-07-25-abby-voice-auto-012-objective-validation-repair.md
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/voice/test_abby_voice_schema.py ipfs_datasets_py/tests/unit/voice/test_abby_voice_normalize.py ipfs_datasets_py/tests/unit/voice/test_abby_voice_graphrag.py ipfs_datasets_py/tests/unit/voice/test_abby_voice_dataset_manager.py
- Bundle: abby-voice/dataset-manager
- Parallel lane: abby-voice-data
- Embedding query: Abby voice dataset manager normalize reconcile missing audio exact identity workset
- AST query: AbbyVoiceDatasetManager, AbbyVoiceDatasetNormalizer, SlottedResponseIndex, ArtifactManifest, VoiceAudioWorkset
- Interfaces: Abby voice v2 schema, HuggingFaceSnapshot, ArtifactManifest
- Submodules: ipfs_datasets_py
- Generated artifacts: data/abby_voice/normalized/disposition.jsonl, data/abby_voice/normalized/audio-workset.jsonl
- Predicted files: ipfs_datasets_py/ipfs_datasets_py/voice/dataset_manager.py, ipfs_datasets_py/ipfs_datasets_py/voice/legacy_sources.py, ipfs_datasets_py/ipfs_datasets_py/voice/workset.py, ipfs_datasets_py/tests/unit/voice/test_abby_voice_dataset_manager.py
- Conflict policy: call the existing normalizer and GraphRAG index rather than duplicating their policy; plural legacy audio paths are candidates, not proof; fuzzy matches are review-only
- Gap task: Replace script-level source handling with a reusable manager that converts pinned sources into canonical rows, quarantine records, ArtifactManifests, and deterministic work specifications.
- Objective-validation repair: `ABBY-VOICE-AUTO-012` owns this validation gate. The source scan reported `deterministic audio worksets`, `deterministic TTS ASR and validation work manifests`, and `fuzzy-review quarantine` missing because no defining G013 implementation or focused assertion was present. The authoritative replacement is `data/abby_voice/agent_supervisor/discovery/2026-07-25-abby-voice-auto-012-objective-validation-repair.md`; evidence is accepted only when it names the defining manager, exact legacy adapter, deterministic workset manifests, quarantine behavior, and focused offline assertions.
- Acceptance gate:
  1. Every inventory object and input row receives exactly one disposition with a stable reason code and source identity.
  2. An audio candidate auto-links only when subject and exact normalized spoken-text identity agree and downloaded bytes pass full SHA-256, size, media, and decode checks. A fuzzy, ambiguous, truncated-hash, basename-only, or identity-mismatched candidate receives a stable review-only quarantine/disposition and never auto-links.
  3. Canonical response, template, audio, and provenance rows pass existing strict bundle and publication validation; GraphRAG serialization remains content-addressed and input-order independent.
  4. The workset contains only missing, corrupt, stale-policy, or explicitly requested revalidation work; its TTS, ASR, and audio-validation manifests have deterministic full-hash identities, canonical ordering, and byte-identical serialization for the same pinned source manifest and policy.
  5. Evaluation remains a checksummed support artifact until G018 implements the promised `abby_voice_evaluation_v2` flat schema.
- Child-goal boundary: No smaller child goal is needed. Exact legacy linking, fuzzy-review quarantine, and deterministic TTS/ASR/audio-validation planning manifests are one cohesive data-plane planning boundary. G022 remains a duplicate refinement superseded by G013; G014 owns cross-package job contracts, G015 owns execution, and G017 owns result reconciliation. G013 does not submit, execute, upload, or delete anything.

## ABBY-VOICE-G014 Define audio job contracts and the datasets-to-accelerate bridge

- Status: active
- Fib priority: 8002
- Priority: P0
- Track: voice-scheduling
- Parents: ABBY-VOICE-G011
- Depends on: ABBY-VOICE-G002, ABBY-VOICE-G013
- Goal: Define versioned TTS ASR and audio-validation job contracts and submit them through the existing ipfs_datasets_py accelerate integration into the canonical DuckDB P2P TaskQueue.
- Evidence: dependency-light request and result schemas; full-hash deterministic task IDs; submit-once behavior; lineage propagation; no-audio-in-DuckDB assertions; datasets bridge integration tests
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/voice_jobs/contracts.py, ipfs_datasets_py/ipfs_datasets_py/ml/accelerate_integration/voice_jobs.py, ipfs_accelerate_py/test/test_voice_job_contracts.py, ipfs_datasets_py/tests/unit/ml/test_voice_job_bridge.py
- Validation: python -m pytest -q ipfs_accelerate_py/test/test_voice_job_contracts.py ipfs_datasets_py/tests/unit/ml/test_voice_job_bridge.py
- Bundle: abby-voice/audio-job-contracts
- Parallel lane: abby-voice-scheduling
- Embedding query: deterministic TTS ASR STT audio validation task contract DuckDB lineage artifact descriptor
- AST query: VoiceTTSJob, VoiceASRJob, VoiceAudioValidationJob, VoiceJobResult, submit_voice_workset
- Interfaces: ipfs_accelerate_py.p2p_tasks.TaskQueue, ipfs_datasets_py.ml.accelerate_integration, Artifact
- Submodules: ipfs_accelerate_py, ipfs_datasets_py
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/voice_jobs/contracts.py, ipfs_datasets_py/ipfs_datasets_py/ml/accelerate_integration/voice_jobs.py, ipfs_accelerate_py/test/test_voice_job_contracts.py, ipfs_datasets_py/tests/unit/ml/test_voice_job_bridge.py
- Conflict policy: the contract carries immutable URI CID SHA-256 and size descriptors, never audio bytes; use the existing canonical P2P client rather than adding a second queue
- Gap task: Add a small shared JSON contract and a datasets-side adapter for submit status wait cancel and receipt ingestion.
- Acceptance gate:
  1. Canonical task types are `voice.tts`, `voice.asr`, and `voice.audio-validate`; `speech-to-text`, `stt`, and `automatic-speech-recognition` normalize to `voice.asr`.
  2. `purpose` separates `runtime_stt` and `dataset_asr_validation`; the runtime form rejects publication lineage and retention by default.
  3. TTS identity covers exact normalized spoken-text bytes, provider/model/voice/version, locale, reference-audio hash, codec, sample rate, channels, and all generation settings. ASR and validation identities cover source audio full SHA-256 and every output-affecting policy.
  4. Replaying one request returns the same task or terminal receipt and causes at most one physical artifact/provider execution.
  5. Results contain immutable artifact descriptors, integer quality metrics, privacy-safe provider receipts, lineage, and typed retryable or terminal errors; no task row contains raw/base64 audio, secrets, private transcript text, or arbitrary paths.
- Child-goal boundary: G014 owns contracts, deterministic identity, and bridge behavior only. G015 executes the jobs; G017 interprets their quality receipts.

## ABBY-VOICE-G015 Add durable voice workers and repair backend routing

- Status: active
- Fib priority: 8003
- Priority: P0
- Track: voice-scheduling
- Parents: ABBY-VOICE-G011
- Depends on: ABBY-VOICE-G003, ABBY-VOICE-G014
- Goal: Add advertised TTS ASR and audio-validation handlers to the existing P2P worker and execute model work through the established voice_router providers.
- Evidence: TTS/ASR execution; shared task alias registry; worker and service capability parity; voice handlers; backend-manager API regression fix; independent TTS/STT device controls; allowed-artifact resolver; offline worker and mesh tests
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/voice_jobs/executor.py, ipfs_accelerate_py/ipfs_accelerate_py/p2p_tasks/worker.py, ipfs_accelerate_py/ipfs_accelerate_py/p2p_tasks/service.py, ipfs_accelerate_py/ipfs_accelerate_py/voice_router.py, ipfs_accelerate_py/test/test_voice_job_worker.py
- Validation: python -m pytest -q ipfs_accelerate_py/test/test_voice_job_worker.py ipfs_accelerate_py/test/test_voice_router_contracts.py ipfs_accelerate_py/test/test_abby_voice_providers.py
- Bundle: abby-voice/audio-workers
- Parallel lane: abby-voice-scheduling
- Embedding query: P2P worker voice TTS ASR STT capability voice_router backend manager artifact
- AST query: execute_voice_tts_job, execute_voice_asr_job, execute_voice_audio_validation_job, execute_task, text_to_speech, speech_to_text
- Interfaces: P2P worker handlers, voice_router, voice_providers.abby, InferenceBackendManager
- Submodules: ipfs_accelerate_py
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/voice_jobs/executor.py, ipfs_accelerate_py/ipfs_accelerate_py/p2p_tasks/worker.py, ipfs_accelerate_py/ipfs_accelerate_py/p2p_tasks/service.py, ipfs_accelerate_py/ipfs_accelerate_py/voice_router.py, ipfs_accelerate_py/test/test_voice_job_worker.py
- Conflict policy: handlers call `voice_router.text_to_speech` and `speech_to_text` or injected equivalents; do not reimplement Abby HTTP retry/circuit-breaker behavior; preserve legacy router APIs
- Gap task: Register and advertise real audio handlers, repair the drifted backend-manager adapter to the current async API, and fix STT device configuration before distributed routing.
- Acceptance gate:
  1. Worker, service, orchestrator, and capability registry use one task-name normalization function and advertise the same supported audio operations.
  2. Claims reject workers that lack the requested provider, model, voice, codec, locale, device, memory, or artifact-access capability.
  3. TTS and ASR handlers call existing router/provider APIs, verify input descriptors before decoding, persist output outside DuckDB, rehash the stored bytes, and return only a descriptor and receipt.
  4. The backend-manager adapter uses current `BackendInfo` and async `execute_task` contracts; focused tests fail on the previously drifted `protocol`, mapping, and `execute_inference` calls.
  5. STT reads its own device setting rather than the TTS device setting.
  6. URI scheme/root allowlists, checksum/size/duration limits, decompression protection, and SSRF/path-traversal rejection are tested offline.
- Child-goal boundary: G015 owns executable handlers and routing correctness. G016 owns queue recovery, resource admission, and provider batching.

## ABBY-VOICE-G016 Add idempotent recovery resource admission and provider batching

- Status: active
- Fib priority: 8004
- Priority: P0
- Track: voice-scheduling
- Parents: ABBY-VOICE-G011
- Depends on: ABBY-VOICE-G015
- Goal: Make distributed voice jobs restart-safe and resource-aware by extending the existing TaskQueue ResourceScheduler and ProviderBatchScheduler rather than creating a new scheduler.
- Evidence: submit-once queue semantics; attempt and backoff state; claim lease and heartbeat recovery; priority-aware claims; audio capability constraints; provider batch compatibility tests; resource and provider saturation tests
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/p2p_tasks/task_queue.py, ipfs_accelerate_py/ipfs_accelerate_py/p2p_tasks/orchestrator.py, ipfs_accelerate_py/ipfs_accelerate_py/p2p_tasks/capability_registry.py, ipfs_accelerate_py/ipfs_accelerate_py/agent_supervisor/provider_batch_scheduler.py, ipfs_accelerate_py/test/test_voice_job_recovery.py
- Validation: python -m pytest -q ipfs_accelerate_py/test/test_voice_job_recovery.py ipfs_accelerate_py/test/api/test_agent_supervisor_provider_batch_scheduler.py ipfs_accelerate_py/test/api/test_agent_supervisor_resource_scheduler.py
- Bundle: abby-voice/audio-scheduling
- Parallel lane: abby-voice-scheduling
- Embedding query: DuckDB voice task lease heartbeat retry idempotent GPU resource provider batch singleflight
- AST query: TaskQueue, TaskOrchestrator, PeerCapabilityRegistry, ProviderBatchScheduler, ResourceScheduler
- Interfaces: DuckDB TaskQueue, capability registry, ResourceScheduler, ProviderBatchScheduler
- Submodules: ipfs_accelerate_py
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/p2p_tasks/task_queue.py, ipfs_accelerate_py/ipfs_accelerate_py/p2p_tasks/orchestrator.py, ipfs_accelerate_py/ipfs_accelerate_py/p2p_tasks/capability_registry.py, ipfs_accelerate_py/ipfs_accelerate_py/agent_supervisor/provider_batch_scheduler.py, ipfs_accelerate_py/test/test_voice_job_recovery.py
- Conflict policy: preserve existing text-task behavior and DuckDB compatibility; provider-local retry remains inside the existing Abby adapter while queue retry handles worker loss and exhausted retryable job failures
- Gap task: Add the minimum generic reliability fields and semantics missing from TaskQueue, then configure existing resource and provider schedulers for audio.
- Acceptance gate:
  1. Atomic submit-once, `attempt`, `max_attempts`, `next_attempt_at`, `lease_until`, and heartbeat ownership make a worker crash recoverable without duplicate provider execution.
  2. Claim order honors priority and eligibility while retaining atomic microbatch claims and safe DuckDB single-writer behavior.
  3. Provider batch keys include provider, route, model, operation, policy digest, voice, locale, reference hash, codec, sample rate, channels, tenant policy, and generation digest; incompatible work never shares a batch.
  4. IndexTTS and Whisper remain batch size one until their adapters prove real batching. Cancellation, timeout, or fallback of one member does not cancel or corrupt siblings.
  5. Resource admission limits CPU, RAM, disk, GPU memory, provider concurrency/rate, and retry-after state; saturation backpressures rather than overclaims.
  6. Single-flight identical work produces one physical provider call and a content-addressed batch receipt whose integrity can be verified.
- Child-goal boundary: G016 owns generic queue reliability and resource/provider admission. G017 owns content and speech-quality decisions.

## ABBY-VOICE-G017 Reconcile generated audio and enforce round-trip quality

- Status: active
- Fib priority: 8005
- Priority: P0
- Track: voice-quality
- Parents: ABBY-VOICE-G011
- Depends on: ABBY-VOICE-G013, ABBY-VOICE-G016
- Goal: Ingest completed audio-job receipts into the canonical dataset and promote only artifacts that pass integrity decode acoustic ASR and slot-fidelity gates.
- Evidence: audio reconciliation; receipt-to-audio-row reconciler; decode and acoustic validator; TTS-to-ASR round-trip evaluation; exact critical-slot checks; terminal quarantine reason taxonomy; complete row disposition report
- Outputs: ipfs_datasets_py/ipfs_datasets_py/voice/reconcile.py, ipfs_datasets_py/ipfs_datasets_py/voice/audio_quality.py, ipfs_datasets_py/tests/unit/voice/test_abby_voice_audio_reconcile.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/voice/test_abby_voice_audio_reconcile.py tests/voice/test_abby_voice_safety.py
- Bundle: abby-voice/audio-reconciliation
- Parallel lane: abby-voice-quality
- Embedding query: Abby audio reconcile TTS ASR WER CER slot fidelity silence clipping quarantine
- AST query: reconcile_voice_job_result, AudioQualityPolicy, validate_tts_asr_roundtrip, AbbyVoiceAudio
- Interfaces: VoiceJobResult, AbbyVoiceAudio, ArtifactManifest, GraphRAG response plan
- Submodules: ipfs_datasets_py, ipfs_accelerate_py
- Generated artifacts: data/abby_voice/normalized/audio-reconciliation.jsonl, data/abby_voice/normalized/audio-quality-report.json
- Predicted files: ipfs_datasets_py/ipfs_datasets_py/voice/reconcile.py, ipfs_datasets_py/ipfs_datasets_py/voice/audio_quality.py, ipfs_datasets_py/tests/unit/voice/test_abby_voice_audio_reconcile.py
- Conflict policy: quality policy is deterministic and versioned; no fuzzy acceptance; failed artifacts remain immutable evidence and are quarantined rather than deleted
- Gap task: Turn immutable job results into reciprocal canonical row/audio links and require both byte integrity and speech-content fidelity.
- Acceptance gate:
  1. Every result is bound to the exact workset subject, task identity, source release, spoken-text hash, provider policy, and stored artifact hash before it can create an audio row.
  2. The actual decoded format agrees with declared MIME/codec, size, duration, sample rate, and channels and passes versioned silence and clipping thresholds.
  3. Dataset validation ASR meets the versioned WER/CER threshold and has 100 percent exact normalized fidelity for critical phone, address, ZIP, hours, eligibility, amount, and emergency slots.
  4. Missing, corrupt, hash-mismatched, stale-policy, low-quality, nonconsensual, or slot-incorrect artifacts receive stable terminal or retryable reason codes and never silently fall back to a nearby row.
  5. All response/template/audio/provenance references remain reciprocal and every source subject ends linked, synthesized, quarantined, or intentionally text-only.
- Child-goal boundary: G017 owns artifact admission and quality. G018 owns release packaging, not speech generation.

## ABBY-VOICE-G018 Build and validate deterministic Hugging Face releases

- Status: active
- Fib priority: 13001
- Priority: P0
- Track: voice-data
- Parents: ABBY-VOICE-G011
- Depends on: ABBY-VOICE-G007, ABBY-VOICE-G017
- Goal: Reuse the generic ArtifactManifest and SkillCenter Parquet release patterns to create a deterministic Abby release that Hugging Face Dataset Viewer can load by immutable revision.
- Evidence: deterministic release construction; extracted generic release helpers; five flat Abby configs including evaluation; sharded ZSTD Parquet descriptors; GraphRAG support-index artifact; byte-identical rebuild; exhaustive local release validator
- Outputs: ipfs_datasets_py/ipfs_datasets_py/huggingface/release.py, ipfs_datasets_py/ipfs_datasets_py/voice/hf_release.py, ipfs_datasets_py/ipfs_datasets_py/voice/evaluation_schema.py, ipfs_datasets_py/tests/unit/voice/test_abby_voice_hf_release.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/voice/test_abby_voice_hf_release.py tests/voice/test_abby_voice_hf_migration.py
- Bundle: abby-voice/hf-release
- Parallel lane: abby-voice-release
- Embedding query: deterministic Abby Hugging Face Parquet release Dataset Viewer ArtifactManifest GraphRAG index
- AST query: ArtifactManifest, AbbyVoiceHFReleaseBuilder, validate_abby_voice_hf_release, AbbyVoiceEvaluation
- Interfaces: ArtifactManifest, PyArrow voice schemas, SlottedResponseIndex serialization, Hugging Face dataset YAML
- Submodules: ipfs_datasets_py
- Generated artifacts: data/abby_voice/releases/release-manifest.json, data/abby_voice/releases/README.md
- Predicted files: ipfs_datasets_py/ipfs_datasets_py/huggingface/release.py, ipfs_datasets_py/ipfs_datasets_py/voice/hf_release.py, ipfs_datasets_py/ipfs_datasets_py/voice/evaluation_schema.py, ipfs_datasets_py/tests/unit/voice/test_abby_voice_hf_release.py
- Conflict policy: extract generic atomic Parquet descriptor helpers without copying the SkillCenter builder; manifests and indexes are support artifacts, never mixed into row configs
- Gap task: Resolve the documented four-versus-five config mismatch and build a voice-specific release wrapper over shared hashing sharding and validation helpers.
- Acceptance gate:
  1. `abby_voice_response_v2`, `abby_voice_template_v2`, `abby_voice_audio_v2`, `abby_voice_provenance_v2`, and a newly defined flat `abby_voice_evaluation_v2` each have isolated schema-stable Parquet paths and split mappings.
  2. Every file descriptor carries relative path, byte length, SHA-256, content CID, media/schema type, producer/config digest, parents, license/consent, and review/trust metadata where applicable.
  3. Release validation verifies every descriptor, Parquet magic/schema/readability/row count/shard coverage, no duplicate IDs, exact bundle references, and GraphRAG graph/index identities.
  4. Two builds from the same pinned source and policy are byte-identical and contain no timestamps, local paths, mutable `/resolve/main/` URLs, truncated hashes, or unordered runtime observations in identity-bearing files.
  5. Runtime observations, job timing, and provider utilization remain non-identity evidence artifacts.
- Child-goal boundary: G018 builds and validates locally. Only G021 can publish or promote a release.

## ABBY-VOICE-G019 Load pinned releases and resolve precomputed audio safely

- Status: active
- Fib priority: 13002
- Priority: P0
- Track: voice-integration
- Parents: ABBY-VOICE-G011
- Depends on: ABBY-VOICE-G008, ABBY-VOICE-G018
- Goal: Load an immutable Abby release into the GraphRAG template provider and resolve precomputed audio only when the rendered spoken text and complete synthesis identity match.
- Evidence: runtime resolution; revision-pinned streaming/release loader; content-addressed GraphRAG restore; exact audio resolver; stale-slot regression test; text-only or live-TTS fallback receipt
- Outputs: ipfs_datasets_py/ipfs_datasets_py/voice/release_loader.py, ipfs_accelerate_py/ipfs_accelerate_py/voice_audio_resolver.py, ipfs_accelerate_py/ipfs_accelerate_py/voice_router.py, ipfs_accelerate_py/test/test_voice_router_precomputed_audio.py
- Validation: python -m pytest -q ipfs_accelerate_py/test/test_voice_router_precomputed_audio.py ipfs_accelerate_py/test/test_voice_router_graphrag.py
- Bundle: abby-voice/runtime-release
- Parallel lane: abby-voice-integration
- Embedding query: pinned Abby release GraphRAG runtime precomputed audio exact rendered text slot hash
- AST query: AbbyVoiceReleaseLoader, PrecomputedVoiceAudioResolver, process_voice_turn
- Interfaces: HuggingFaceStreamingLoader, SlottedResponseIndex, VoiceTemplateProvider, voice_router
- Submodules: ipfs_datasets_py, ipfs_accelerate_py
- Predicted files: ipfs_datasets_py/ipfs_datasets_py/voice/release_loader.py, ipfs_accelerate_py/ipfs_accelerate_py/voice_audio_resolver.py, ipfs_accelerate_py/ipfs_accelerate_py/voice_router.py, ipfs_accelerate_py/test/test_voice_router_precomputed_audio.py
- Conflict policy: add revision support to the existing streaming loader; resolver failure falls through to live TTS or text-only output and never serves a near or stale match
- Gap task: Connect curated rows to runtime retrieval and remove identifier-only precomputed-audio matching.
- Acceptance gate:
  1. The loader requires a release manifest plus immutable dataset commit SHA, downloads only the manifest, relevant indexes, and selected Parquet shards, and validates descriptors before use.
  2. A precomputed artifact matches only the exact rendered spoken-text SHA-256 and the full provider/model/voice/version/locale/reference/codec/rate/channel/generation identity.
  3. Changing a grounded phone, address, ZIP, hours, eligibility, amount, or emergency slot invalidates stale audio even if the template or slotted-response identifier is unchanged.
  4. Missing or invalid audio records a deterministic resolver reason and falls through to live TTS or text-only behavior without weakening GraphRAG provenance.
  5. Runtime caller audio and transcripts are neither cached into the public release nor written into ordinary receipts.
- Child-goal boundary: G019 owns pinned runtime loading and exact audio reuse. G010 owns wallet rollout; G020 owns deployed-like end-to-end gates.

## ABBY-VOICE-G020 Prove the distributed dataset-to-voice pipeline end to end

- Status: active
- Fib priority: 21000
- Priority: P0
- Track: voice-evaluation
- Parents: ABBY-VOICE-G011
- Depends on: ABBY-VOICE-G009, ABBY-VOICE-G016, ABBY-VOICE-G018, ABBY-VOICE-G019
- Goal: Demonstrate a restart-safe fixture and approved canary flow from pinned source inventory through TTS validation ASR release loading GraphRAG slotting and final voice output.
- Evidence: offline deterministic fixture; DuckDB TTS-to-validate-to-ASR workflow receipt; worker-crash recovery test; capability/resource backpressure test; real-provider canary protocol; privacy and lineage audit
- Outputs: tests/voice/test_abby_voice_distributed_pipeline.py, docs/runbooks/ABBY_VOICE_AUDIO_JOBS.md, docs/reports/ABBY_VOICE_DISTRIBUTED_EVALUATION.md
- Validation: python -m pytest -q tests/voice/test_abby_voice_distributed_pipeline.py tests/voice/test_abby_voice_safety.py && python benchmarks/bench_abby_voice_router.py --offline --check
- Bundle: abby-voice/end-to-end
- Parallel lane: abby-voice-evaluation
- Embedding query: Abby distributed TTS ASR STT DuckDB GraphRAG release end to end restart recovery
- AST query: TaskQueue, VoiceJobResult, AbbyVoiceHFReleaseBuilder, AbbyVoiceReleaseLoader, process_voice_turn
- Interfaces: all Abby voice dataset scheduler router and runtime boundaries
- Submodules: ipfs_accelerate_py, ipfs_datasets_py
- Generated artifacts: docs/reports/ABBY_VOICE_DISTRIBUTED_EVALUATION.md
- Predicted files: tests/voice/test_abby_voice_distributed_pipeline.py, docs/runbooks/ABBY_VOICE_AUDIO_JOBS.md, docs/reports/ABBY_VOICE_DISTRIBUTED_EVALUATION.md
- Conflict policy: offline gates use fakes and tiny public fixtures; real provider and remote read canaries require explicit scope credentials cost limit and retention approval
- Gap task: Verify the complete control-plane and execution-plane contract including failure recovery and exact factual slot audio.
- Acceptance gate:
  1. The fixture runs pinned inventory to normalization to deterministic tasks to TTS to audio validation to ASR to reconciliation to release to GraphRAG voice turn with complete lineage and no network.
  2. Replaying after process termination recovers expired leases, reuses completed identities, and produces no duplicate provider call or conflicting artifact.
  3. Capability mismatch, GPU/RAM/disk/provider saturation, timeout, cancellation, 429, retryable 5xx, circuit-open, corrupt input, quality rejection, and text-only fallback are each asserted.
  4. Critical factual slots are exact in rendered text, admitted audio ASR, and the final runtime response; citations remain machine provenance and are absent from spoken output.
  5. Logs, DuckDB state, receipts, and artifacts pass a secret/private-audio/private-transcript scan.
  6. Any real-provider canary is separately human-approved, bounded by item count and cost, uses non-sensitive rows, and writes only to a staging prefix.
- Child-goal boundary: G020 owns verification and canary evidence. G021 owns the remote release transaction and promotion decision.

## ABBY-VOICE-G021 Publish and promote an immutable Hugging Face release

- Status: active
- Fib priority: 21001
- Priority: P1
- Track: voice-release
- Parents: ABBY-VOICE-G011
- Depends on: ABBY-VOICE-G006, ABBY-VOICE-G018, ABBY-VOICE-G020
- Goal: Perform an explicitly approved append-only release transaction, capture the resulting Hugging Face commit SHA, redownload by that SHA, revalidate, and canary the consumer pointer with rollback.
- Evidence: post-publication verification; signed reviewed release manifest; dry-run diff and cost receipt; approval record; append-only commit receipt; pinned redownload validation; canary and rollback receipt
- Outputs: ipfs_datasets_py/ipfs_datasets_py/huggingface/publisher.py, scripts/publish_abby_voice_release.py, docs/runbooks/ABBY_VOICE_HF_RELEASE.md, data/abby_voice/releases/publication-receipt.json
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/voice/test_abby_voice_hf_publish.py && python scripts/publish_abby_voice_release.py --manifest data/abby_voice/releases/release-manifest.json --dry-run
- Bundle: abby-voice/hf-publication
- Parallel lane: abby-voice-release
- Embedding query: Hugging Face append only publish commit SHA verify canary rollback Abby voice
- AST query: HuggingFaceReleasePublisher, publish_abby_voice_release, validate_abby_voice_hf_release
- Interfaces: HfApi create_commit, Abby release manifest, runtime release pointer
- Submodules: ipfs_datasets_py
- Generated artifacts: data/abby_voice/releases/publication-receipt.json
- Predicted files: ipfs_datasets_py/ipfs_datasets_py/huggingface/publisher.py, scripts/publish_abby_voice_release.py, docs/runbooks/ABBY_VOICE_HF_RELEASE.md, ipfs_datasets_py/tests/unit/voice/test_abby_voice_hf_publish.py
- Conflict policy: autonomous work stops after a dry run; no delete move overwrite mutable-main URL or pointer promotion occurs without explicit human approval of the exact manifest commit operations credentials scope and cost bound
- Gap task: Replace legacy script upload behavior with a digest-aware append-only publisher and a fail-closed promotion workflow.
- Acceptance gate:
  1. Before approval, the publisher can only produce a deterministic dry-run operation list, byte totals, estimated cost, target immutable release prefix, and hashes; it cannot contact a write endpoint.
  2. The approved transaction uploads by full relative path and digest under a new release ID, never skips by basename, never deletes or rewrites a legacy object, and records the returned commit SHA.
  3. The release is downloaded by returned commit SHA into an empty verified cache and every manifest, descriptor, Parquet shard, GraphRAG index, and audio reference revalidates.
  4. Consumer promotion is a separate reviewed step with a bounded canary. Rollback restores the previous pinned manifest/commit and never deletes the failed release.
  5. Tokens are never persisted in task rows, manifests, logs, receipts, or source control.
- Child-goal boundary: G021 is the sole owner of remote writes and consumer-pointer changes; failure to obtain approval is a valid blocked state, not permission for an autonomous workaround.

## ABBY-VOICE-G022 Prove deterministic audio worksets for Normalize and materialize the Abby voice dataset

- Status: blocked
- Blocked reason: duplicate refinement; ABBY-VOICE-G013 already owns the exact deterministic audio worksets evidence requirement
- Superseded by: ABBY-VOICE-G013
- Parent: ABBY-VOICE-G011
- Fib priority: 13000
- Track: voice-data
- Priority: P0
- Bundle: abby-voice/dataset-materialization
- Goal: Create concrete implementation, tests, docs, or interface descriptors proving `deterministic audio worksets`.
- Evidence: deterministic audio worksets
- Outputs: data/abby_voice/normalized/manifest.json, data/abby_voice/normalized/quality-report.json, data/abby_voice/normalized/quarantine.jsonl, data/abby_voice/releases/release-manifest.json, data/abby_voice/agent_supervisor/discovery/ABBY-VOICE-G011-completion.md
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/voice tests/voice && python benchmarks/bench_abby_voice_router.py --offline --check
- Refinement depth: 4
- Embedding query: deterministic audio worksets
- AST query: deterministic audio worksets
- Parallel lane: abby-voice-data
- Conflict policy: treat all source bucket and dataset objects as immutable; perform no remote writes moves or deletes; make every transformation deterministic and preserve source URI revision checksum and rejection reason for audit and rollback
- Gap task: Close the missing objective evidence `deterministic audio worksets` with a narrow, verifiable change.

## ABBY-VOICE-G023 Prove TTS/ASR execution for Normalize and materialize the Abby voice dataset

- Status: blocked
- Blocked reason: duplicate refinement; ABBY-VOICE-G015 already owns the exact TTS/ASR execution evidence requirement
- Superseded by: ABBY-VOICE-G015
- Parent: ABBY-VOICE-G011
- Fib priority: 13001
- Track: voice-data
- Priority: P0
- Bundle: abby-voice/dataset-materialization
- Goal: Create concrete implementation, tests, docs, or interface descriptors proving `TTS/ASR execution`.
- Evidence: TTS/ASR execution
- Outputs: data/abby_voice/normalized/manifest.json, data/abby_voice/normalized/quality-report.json, data/abby_voice/normalized/quarantine.jsonl, data/abby_voice/releases/release-manifest.json, data/abby_voice/agent_supervisor/discovery/ABBY-VOICE-G011-completion.md
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/voice tests/voice && python benchmarks/bench_abby_voice_router.py --offline --check
- Refinement depth: 4
- Embedding query: TTS/ASR execution
- AST query: TTS/ASR execution
- Parallel lane: abby-voice-data
- Conflict policy: treat all source bucket and dataset objects as immutable; perform no remote writes moves or deletes; make every transformation deterministic and preserve source URI revision checksum and rejection reason for audit and rollback
- Gap task: Close the missing objective evidence `TTS/ASR execution` with a narrow, verifiable change.

## ABBY-VOICE-G024 Prove audio reconciliation for Normalize and materialize the Abby voice dataset

- Status: blocked
- Blocked reason: duplicate refinement; ABBY-VOICE-G017 already owns the exact audio reconciliation evidence requirement
- Superseded by: ABBY-VOICE-G017
- Parent: ABBY-VOICE-G011
- Fib priority: 13002
- Track: voice-data
- Priority: P0
- Bundle: abby-voice/dataset-materialization
- Goal: Create concrete implementation, tests, docs, or interface descriptors proving `audio reconciliation`.
- Evidence: audio reconciliation
- Outputs: data/abby_voice/normalized/manifest.json, data/abby_voice/normalized/quality-report.json, data/abby_voice/normalized/quarantine.jsonl, data/abby_voice/releases/release-manifest.json, data/abby_voice/agent_supervisor/discovery/ABBY-VOICE-G011-completion.md
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/voice tests/voice && python benchmarks/bench_abby_voice_router.py --offline --check
- Refinement depth: 4
- Embedding query: audio reconciliation
- AST query: audio reconciliation
- Parallel lane: abby-voice-data
- Conflict policy: treat all source bucket and dataset objects as immutable; perform no remote writes moves or deletes; make every transformation deterministic and preserve source URI revision checksum and rejection reason for audit and rollback
- Gap task: Close the missing objective evidence `audio reconciliation` with a narrow, verifiable change.

## ABBY-VOICE-G025 Prove deterministic release construction for Normalize and materialize the Abby voice dataset

- Status: blocked
- Blocked reason: duplicate refinement; ABBY-VOICE-G018 already owns the exact deterministic release construction evidence requirement
- Superseded by: ABBY-VOICE-G018
- Parent: ABBY-VOICE-G011
- Fib priority: 13000
- Track: voice-data
- Priority: P0
- Bundle: abby-voice/dataset-materialization
- Goal: Create concrete implementation, tests, docs, or interface descriptors proving `deterministic release construction`.
- Evidence: deterministic release construction
- Outputs: data/abby_voice/normalized/manifest.json, data/abby_voice/normalized/quality-report.json, data/abby_voice/normalized/quarantine.jsonl, data/abby_voice/releases/release-manifest.json, data/abby_voice/agent_supervisor/discovery/ABBY-VOICE-G011-completion.md
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/voice tests/voice && python benchmarks/bench_abby_voice_router.py --offline --check
- Refinement depth: 4
- Embedding query: deterministic release construction
- AST query: deterministic release construction
- Parallel lane: abby-voice-data
- Conflict policy: treat all source bucket and dataset objects as immutable; perform no remote writes moves or deletes; make every transformation deterministic and preserve source URI revision checksum and rejection reason for audit and rollback
- Gap task: Close the missing objective evidence `deterministic release construction` with a narrow, verifiable change.

## ABBY-VOICE-G026 Prove bucket inventory summary for Produce a safe Hugging Face bucket and dataset migration plan

- Status: blocked
- Blocked reason: duplicate refinement; verified ABBY-VOICE-G006 migration artifacts already contain the bucket inventory summary
- Superseded by: ABBY-VOICE-G006
- Parent: ABBY-VOICE-G006
- Fib priority: 13000
- Track: voice-data
- Priority: P1
- Bundle: abby-voice/huggingface-migration
- Goal: Create concrete implementation, tests, docs, or interface descriptors proving `bucket inventory summary`.
- Evidence: bucket inventory summary
- Outputs: docs/data/ABBY_VOICE_HF_MIGRATION_PLAN.md, data/abby_voice/huggingface/README.template.md, data/abby_voice/huggingface/migration-plan.json
- Validation: python scripts/build_abby_voice_dataset_v2.py --check --output-dir /tmp/abby-voice-v2-check && test -f data/abby_voice/huggingface/migration-plan.json
- Refinement depth: 4
- Embedding query: bucket inventory summary
- AST query: bucket inventory summary
- Parallel lane: abby-voice-data
- Conflict policy: prohibit remote writes moves and deletes; only emit a local dry-run plan with checksums counts costs and rollback notes for human approval
- Gap task: Close the missing objective evidence `bucket inventory summary` with a narrow, verifiable change.

## ABBY-VOICE-G027 Prove proposed canonical prefix layout for Produce a safe Hugging Face bucket and dataset migration plan

- Status: blocked
- Blocked reason: duplicate refinement; verified ABBY-VOICE-G006 migration artifacts already contain the proposed canonical prefix layout
- Superseded by: ABBY-VOICE-G006
- Parent: ABBY-VOICE-G006
- Fib priority: 13001
- Track: voice-data
- Priority: P1
- Bundle: abby-voice/huggingface-migration
- Goal: Create concrete implementation, tests, docs, or interface descriptors proving `proposed canonical prefix layout`.
- Evidence: proposed canonical prefix layout
- Outputs: docs/data/ABBY_VOICE_HF_MIGRATION_PLAN.md, data/abby_voice/huggingface/README.template.md, data/abby_voice/huggingface/migration-plan.json
- Validation: python scripts/build_abby_voice_dataset_v2.py --check --output-dir /tmp/abby-voice-v2-check && test -f data/abby_voice/huggingface/migration-plan.json
- Refinement depth: 4
- Embedding query: proposed canonical prefix layout
- AST query: proposed canonical prefix layout
- Parallel lane: abby-voice-data
- Conflict policy: prohibit remote writes moves and deletes; only emit a local dry-run plan with checksums counts costs and rollback notes for human approval
- Gap task: Close the missing objective evidence `proposed canonical prefix layout` with a narrow, verifiable change.

## ABBY-VOICE-G028 Prove Dataset Viewer validation procedure for Produce a safe Hugging Face bucket and dataset migration plan

- Status: blocked
- Blocked reason: duplicate refinement; verified ABBY-VOICE-G006 migration artifacts already contain the Dataset Viewer validation procedure
- Superseded by: ABBY-VOICE-G006
- Parent: ABBY-VOICE-G006
- Fib priority: 13002
- Track: voice-data
- Priority: P1
- Bundle: abby-voice/huggingface-migration
- Goal: Create concrete implementation, tests, docs, or interface descriptors proving `Dataset Viewer validation procedure`.
- Evidence: Dataset Viewer validation procedure
- Outputs: docs/data/ABBY_VOICE_HF_MIGRATION_PLAN.md, data/abby_voice/huggingface/README.template.md, data/abby_voice/huggingface/migration-plan.json
- Validation: python scripts/build_abby_voice_dataset_v2.py --check --output-dir /tmp/abby-voice-v2-check && test -f data/abby_voice/huggingface/migration-plan.json
- Refinement depth: 4
- Embedding query: Dataset Viewer validation procedure
- AST query: Dataset Viewer validation procedure
- Parallel lane: abby-voice-data
- Conflict policy: prohibit remote writes moves and deletes; only emit a local dry-run plan with checksums counts costs and rollback notes for human approval
- Gap task: Close the missing objective evidence `Dataset Viewer validation procedure` with a narrow, verifiable change.

## ABBY-VOICE-G029 Prove ABBY-VOICE-G006 completion receipt for Produce a safe Hugging Face bucket and dataset migration plan

- Status: blocked
- Blocked reason: duplicate refinement; ABBY-VOICE-G006 already has its focused validation receipt and completed canonical task
- Superseded by: ABBY-VOICE-G006
- Parent: ABBY-VOICE-G006
- Fib priority: 13000
- Track: voice-data
- Priority: P1
- Bundle: abby-voice/huggingface-migration
- Goal: Create concrete implementation, tests, docs, or interface descriptors proving `ABBY-VOICE-G006 completion receipt`.
- Evidence: ABBY-VOICE-G006 completion receipt
- Outputs: docs/data/ABBY_VOICE_HF_MIGRATION_PLAN.md, data/abby_voice/huggingface/README.template.md, data/abby_voice/huggingface/migration-plan.json
- Validation: python scripts/build_abby_voice_dataset_v2.py --check --output-dir /tmp/abby-voice-v2-check && test -f data/abby_voice/huggingface/migration-plan.json
- Refinement depth: 4
- Embedding query: ABBY-VOICE-G006 completion receipt
- AST query: ABBY-VOICE-G006 completion receipt
- Parallel lane: abby-voice-data
- Conflict policy: prohibit remote writes moves and deletes; only emit a local dry-run plan with checksums counts costs and rollback notes for human approval
- Gap task: Close the missing objective evidence `ABBY-VOICE-G006 completion receipt` with a narrow, verifiable change.
