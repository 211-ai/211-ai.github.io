# ABBY-VOICE-AUTO-002 Objective Validation Repair

Date: 2026-07-23
Goal id: ABBY-VOICE-G002
Task id: ABBY-VOICE-AUTO-002
Goal title: Define stable voice-turn and provider contracts
Objective heap: `docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md`
Priority: P0
Track: voice-router
Parent goal: ABBY-VOICE-G001
Graph depth: 1
Bundle: abby-voice/voice-router-contracts
Work scope: objective_validation_repair
Source gap fingerprint: `c4349323df82d9bacadbae735e3e09b50300ccf6`

## Finding

The source objective scan reported the literal missing evidence term
`objective validation repair`. Its present-evidence section pointed to
unrelated Chainlink and ProveKit artifacts, IndexTTS precompute JSON, and other
README/JSON files because they happened to contain matching AST tokens or
embedding phrases. Those files neither define nor assert the
`ipfs_accelerate_py.voice_router` contract and are not accepted as G002
evidence.

This receipt supersedes that token-coincidence mapping without altering the
source gap report. Every accepted claim below identifies both its defining
source and a focused offline assertion.

## Repaired evidence map

| Required evidence | Authoritative repository evidence | Validation rule |
| --- | --- | --- |
| `VoiceTurnRequest` dataclass | Definition in `ipfs_accelerate_py/ipfs_accelerate_py/voice_router.py`; request validation, normalization, file/byte identity, immutability, JSON, privacy, and cache-variation assertions in `ipfs_accelerate_py/test/test_voice_router_contracts.py` | A request contains non-empty audio or transcript; records context, grounding, locale/language, providers, models, device, format, fallback, limits, and adapter options; derives current content identity; serializes all behavior-affecting fields; and emits no raw audio/path unless explicitly requested for transport. |
| `VoiceTurnResult` and provenance contracts | `VoiceTurnResult` and `VoiceTurnProvenance` in `ipfs_accelerate_py/ipfs_accelerate_py/voice_router.py`; result receipt assertions in `ipfs_accelerate_py/test/test_voice_router_contracts.py` | Results use a defined status, non-empty response, typed audio, typed traces/provenance, normalized fallbacks, provider selection, aggregate timing, cache identity, and content hashes. Default JSON omits audio; opt-in audio is base64. |
| `VoiceProviderCapabilities` and provider metadata | `VoiceProviderCapabilities`, `ProviderInfo`, `register_voice_provider`, and `get_voice_provider_capabilities` in `ipfs_accelerate_py/ipfs_accelerate_py/voice_router.py`; capability/registry tests in `ipfs_accelerate_py/test/test_voice_router_contracts.py` | STT, TTS, streaming, and audio formats are normalized and serializable. Names resolve canonically. Built-in and registered capabilities are inspectable without provider construction, unsupported operations are skipped, invalid metadata is rejected, and re-registration takes effect immediately. |
| `VoiceStageTrace` contract | `VoiceStageTrace` in `ipfs_accelerate_py/ipfs_accelerate_py/voice_router.py`; validation/serialization tests in `ipfs_accelerate_py/test/test_voice_router_contracts.py` | Stage is non-empty; status is `succeeded`, `failed`, or `skipped`; duration is finite and non-negative; provider/error/details are normalized; byte-bearing details serialize as hashes and sizes. |
| Stable privacy-safe cache identity | `voice_turn_cache_key`, `_voice_turn_cache_key`, `_tts_response_cache_key`, and `_stt_response_cache_key` in `ipfs_accelerate_py/ipfs_accelerate_py/voice_router.py`; request-field, provider-instance, option, and mutable-file tests in `ipfs_accelerate_py/test/test_voice_router_contracts.py` | Every output-affecting request/provider option changes identity. Request IDs do not. Caller audio, transcripts, paths, and fallback wording are never embedded. Distinct injected providers cannot receive one another's cached output, and changed file bytes invalidate STT cache identity. |
| Compatibility tests for `text_to_speech` and `speech_to_text` | Direct signature, return, provider injection, kwargs, caching, and `output_path` assertions in `ipfs_accelerate_py/test/test_voice_router_contracts.py`; existing smoke coverage in `ipfs_accelerate_py/test/test_voice_router_integration.py` | Existing keyword-only parameter lists and bytes/string return forms are unchanged. Injected providers receive all established arguments, output files contain synthesized bytes, and explicit custom providers remain supported. |
| ABBY-VOICE-G002 completion receipt | This file plus the G002 acceptance gate in `docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md` | The exact objective validation command passes offline and every required evidence term resolves to the defining/asserting repository path rather than an unrelated token match. |

## Acceptance assertions

The focused contract suite establishes all of the following:

1. the contract version and status vocabularies are public from both the module
   and package surface;
2. request, result, provenance, trace, capability, and provider metadata are
   normalized and JSON-safe;
3. constructor errors separate malformed caller/programmer input from runtime
   provider degradation;
4. raw caller input and synthesized audio are excluded from default receipts;
5. explicit transport serialization uses base64 for byte audio;
6. capability lookup never imports a model, checks credentials, or calls a
   remote endpoint;
7. a provider whose capability excludes the requested operation is skipped
   without invoking its factory;
8. cache identities cover device, format, provider/model chains, retrieval
   limits, fallback text hash, adapter options, collaborators, and current
   file content;
9. two injected providers cannot cross-contaminate legacy TTS or STT caches;
10. legacy TTS/STT signatures, return types, `output_path`, provider injection,
    forwarded kwargs, and response caching remain compatible;
11. all tests use synthetic bytes and injected providers, make no network
    call, require no credentials, load no heavyweight model, and mutate no
    remote data.

## Validation

Command:

```bash
python -m pytest -q ipfs_accelerate_py/test/test_voice_router_contracts.py ipfs_accelerate_py/test/test_voice_router_integration.py
```

Result: **passed** on 2026-07-23 — `40 passed, 9 warnings in 1.19s`.
The nine warnings are pre-existing `PytestReturnNotNoneWarning` notices from
the legacy integration file's boolean-returning smoke-test style. The 31 new
focused contract cases use direct assertions, so failures propagate normally.

An additional parent-pipeline regression run also passed:

```bash
python -m pytest -q tests/voice/test_abby_voice_pipeline.py
```

Result: `18 passed, 1 warning in 7.26s`; the warning is an unrelated
Starlette/httpx deprecation emitted during root test discovery.

## Supervisor alignment

The heap and supervisor-fed backlog agree on:

- task `ABBY-VOICE-AUTO-002` and goal `ABBY-VOICE-G002`;
- parent `ABBY-VOICE-G001`, graph depth 1, bundle
  `abby-voice/voice-router-contracts`, track `voice-router`, and P0 priority;
- merge family `objective/ABBY-VOICE-G002`, merge role `validation_gate`, and
  work scope `objective_validation_repair`;
- todo vector key `f63efd593e502c7c` and merge key `407fe86571e7b1a7`;
- the exact two-file validation command above;
- implementation outputs
  `ipfs_accelerate_py/ipfs_accelerate_py/voice_router.py` and
  `ipfs_accelerate_py/test/test_voice_router_contracts.py`;
- planning output `docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md` and this
  discovery receipt.

No supervisor-generated todo/vector/graph state was edited manually. The
implementation daemon owns task completion and post-merge regeneration. No
additional child goal is required: G003 retains provider adapter and production
fallback ownership, while G008 retains GraphRAG template composition and
voice-turn orchestration ownership. G002 is complete at its contract and
backward-compatibility boundary.
