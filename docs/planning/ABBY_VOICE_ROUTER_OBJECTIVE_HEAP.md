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

- Status: active
- Fib priority: 3000
- Priority: P0
- Track: voice-router
- Parents: ABBY-VOICE-G002
- Goal: Make the Python voice router capable of the same ordered remote local and degraded behaviors used by the wallet voice assistant without importing UI-specific code.
- Evidence: IndexTTS provider adapter, Hugging Face Whisper HTTP adapter, ordered capability-aware fallback policy, bounded retry timeout and circuit-breaker tests, structured degraded-result receipts, ABBY-VOICE-G003 completion receipt
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/voice_providers/abby.py, ipfs_accelerate_py/ipfs_accelerate_py/voice_router.py, ipfs_accelerate_py/test/test_abby_voice_providers.py
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

## ABBY-VOICE-G004 Define the canonical Abby voice dataset schema

- Status: active
- Fib priority: 3001
- Priority: P0
- Track: voice-data
- Parents: ABBY-VOICE-G001
- Goal: Define a flat versioned dataset contract that ipfs_datasets_py and Hugging Face Dataset Viewer can load without interpreting indexes or manifests as response rows.
- Evidence: abby_voice_response_v2 schema, abby_voice_template_v2 schema, abby_voice_audio_v2 schema, abby_voice_provenance_v2 schema, schema validation and migration fixtures, ABBY-VOICE-G004 completion receipt
- Outputs: ipfs_datasets_py/ipfs_datasets_py/voice/schema.py, ipfs_datasets_py/tests/unit/voice/test_abby_voice_schema.py, docs/data/ABBY_VOICE_DATASET_SCHEMA.md
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

## ABBY-VOICE-G005 Build deterministic dataset normalization and quality gates

- Status: active
- Fib priority: 5000
- Priority: P0
- Track: voice-data
- Parents: ABBY-VOICE-G004
- Goal: Convert the existing manifests and response corpus into canonical rows while detecting low-value vocabulary fragments malformed spoken text duplicates ungrounded claims missing audio and inconsistent slots.
- Evidence: deterministic manifest normalizer, text and audio deduplication report, spoken-text corruption checks, slot fidelity checks, dataset quality summary with quarantine reasons, ABBY-VOICE-G005 completion receipt
- Outputs: ipfs_datasets_py/ipfs_datasets_py/voice/normalize.py, scripts/build_abby_voice_dataset_v2.py, ipfs_datasets_py/tests/unit/voice/test_abby_voice_normalize.py
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

## ABBY-VOICE-G006 Produce a safe Hugging Face bucket and dataset migration plan

- Status: active
- Fib priority: 5001
- Priority: P1
- Track: voice-data
- Parents: ABBY-VOICE-G004, ABBY-VOICE-G005, ABBY-VOICE-G011
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

## ABBY-VOICE-G007 Add GraphRAG response-template ingestion and retrieval

- Status: active
- Fib priority: 5002
- Priority: P0
- Track: voice-graphrag
- Parents: ABBY-VOICE-G004, ABBY-VOICE-G005, ABBY-VOICE-G011
- Goal: Ingest canonical response frames evidence links and slot relationships into ipfs_datasets_py and retrieve them as response plans rather than uncited final answers.
- Evidence: GraphRAGVoiceTemplateProvider implementation, IPLD template intent evidence graph, hybrid template retriever, slot binding safety policy, retrieval provenance tests, ABBY-VOICE-G007 completion receipt
- Outputs: ipfs_datasets_py/ipfs_datasets_py/voice/graphrag.py, ipfs_datasets_py/tests/unit/voice/test_abby_voice_graphrag.py, docs/data/ABBY_VOICE_GRAPHRAG.md
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

## ABBY-VOICE-G008 Integrate GraphRAG templating into voice_router

- Status: active
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

## ABBY-VOICE-G009 Establish voice safety quality and performance evaluation

- Status: active
- Fib priority: 8001
- Priority: P0
- Track: voice-evaluation
- Parents: ABBY-VOICE-G005, ABBY-VOICE-G007, ABBY-VOICE-G008
- Goal: Prevent autonomous optimization from trading away grounding privacy accessibility or emergency behavior for latency or response reuse.
- Evidence: golden voice-turn evaluation set, STT word error measurements, template retrieval and slot fidelity metrics, grounded factuality and crisis policy tests, latency cache and fallback benchmarks, ABBY-VOICE-G009 completion receipt
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
- Gap task: Build offline deterministic gates for emergency routing source grounding slot fidelity spoken readability fallback behavior and latency budgets.

## ABBY-VOICE-G010 Adopt the unified router in wallet_interface

- Status: active
- Fib priority: 13000
- Priority: P1
- Track: voice-integration
- Parents: ABBY-VOICE-G008, ABBY-VOICE-G009
- Goal: Let the current Abby UI and service proxy use the shared contracts without removing its browser local-audio and browser-speech fallbacks.
- Evidence: wallet voice proxy adapter for VoiceTurnResult, preserved browser SpeechRecognition fallback, preserved local WebGPU and browser speech fallback, end-to-end UI voice tests, operator rollout and rollback documentation, ABBY-VOICE-G010 completion receipt
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

## ABBY-VOICE-G011 Normalize and materialize the Abby voice dataset

- Status: active
- Fib priority: 5001
- Priority: P0
- Track: voice-data
- Parents: ABBY-VOICE-G004, ABBY-VOICE-G005
- Goal: Run the canonical normalizer over an immutable inventory of the Abby bucket and 211 Abby TTS dataset, then materialize schema-stable responses templates audio provenance and evaluation configurations that ipfs_datasets_py and Hugging Face Dataset Viewer can load independently.
- Evidence: normalized dataset manifest, schema-stable Parquet shards for five named configurations, deterministic ID and content-hash map, duplicate merge ledger, quarantined-row ledger with reason codes, before-and-after quality report, byte-identical rerun receipt, local Dataset Viewer compatibility receipt, ABBY-VOICE-G011 completion receipt
- Outputs: scripts/build_abby_voice_dataset_v2.py, data/abby_voice/normalized/manifest.json, data/abby_voice/normalized/quality-report.json, data/abby_voice/normalized/quarantine.jsonl, data/abby_voice/normalized/README.md, ipfs_datasets_py/tests/unit/voice/test_abby_voice_dataset_build.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/voice/test_abby_voice_dataset_build.py && python scripts/build_abby_voice_dataset_v2.py --fixture ipfs_datasets_py/tests/fixtures/voice/abby_mixed_records --output-dir /tmp/abby-voice-normalized-check --check-idempotence
- Bundle: abby-voice/dataset-materialization
- Parallel lane: abby-voice-data
- Embedding query: normalize materialize Abby voice bucket responses templates audio provenance evaluation Parquet quarantine deduplicate idempotent Dataset Viewer
- AST query: build_abby_voice_dataset_v2, AbbyVoiceDatasetNormalizer, write_dataset_config, quarantine_record, normalization_receipt
- Interfaces: ipfs_datasets_py.voice normalization API, Hugging Face datasets Arrow and Parquet, Publicus Abby source inventory
- Submodules: ipfs_datasets_py
- Generated artifacts: data/abby_voice/normalized/manifest.json, data/abby_voice/normalized/quality-report.json, data/abby_voice/normalized/quarantine.jsonl
- Predicted files: scripts/build_abby_voice_dataset_v2.py, ipfs_datasets_py/ipfs_datasets_py/voice/normalize.py, ipfs_datasets_py/tests/unit/voice/test_abby_voice_dataset_build.py, ipfs_datasets_py/tests/fixtures/voice/abby_mixed_records
- Conflict policy: treat all source bucket and dataset objects as immutable; perform no remote writes moves or deletes; make every transformation deterministic and preserve source URI revision checksum and rejection reason for audit and rollback
- Gap task: Build a reproducible local normalization run that separates row data from indexes and manifests, removes or quarantines low-value fragments, merges duplicates by stable content identity, preserves usable audio links and GraphRAG slots, and emits five independently loadable dataset configurations.
