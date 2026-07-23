# ABBY-VOICE-AUTO-001 Objective Validation Repair

Date: 2026-07-23
Goal id: ABBY-VOICE-G001
Task id: ABBY-VOICE-AUTO-001
Goal title: Deliver a unified grounded Abby voice pipeline
Objective heap: `docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md`
Priority: P0
Track: voice-platform
Bundle: abby-voice/integration
Work scope: objective_validation_repair
Source gap fingerprint: `c1cb8a2061bbb65830b5c820ee7884dd584d4eb3`

## Finding

The source objective scan reported the literal missing evidence term
`objective validation repair`. It also listed unrelated batch manifests,
transcripts, DAG shards, and ProveKit receipts as present evidence because they
contained matching AST tokens. Those files do not define or verify the Abby
voice pipeline and are not accepted as G001 evidence.

This receipt repairs the evidence mapping. Every accepted claim below points to
the source that defines the behavior or the test that asserts it. G001 remains
active while its independent child goals remain active; this task is the
cross-child offline integration gate, not a claim that all production rollout
work is complete.

## Repaired evidence map

| Required evidence | Authoritative repository evidence | Validation rule |
| --- | --- | --- |
| Unified `VoiceTurnRequest` and `VoiceTurnResult` contracts | `ipfs_accelerate_py/ipfs_accelerate_py/voice_router.py`; `tests/voice/test_abby_voice_pipeline.py` | Contracts are importable; a complete result exposes status/degradation, transcript, response/spoken text, optional audio/format, traces, fallbacks, provider/template/evidence provenance, and cache identity; `to_dict()` excludes raw audio by default. |
| Typed grounding plan | `VoiceGroundingSource`, `GroundedSlot`, and `VoiceResponsePlan` in `ipfs_accelerate_py/ipfs_accelerate_py/voice_router.py`; assertions in `tests/voice/test_abby_voice_pipeline.py` | Every rendered factual slot cites a present source ID. An explicit current source is accepted without structured facts; when it declares the matching fact key, its value must agree. Citations are removed only from spoken text and remain in machine provenance. |
| GraphRAG response-template retrieval adapter | `VoiceTemplateProvider.retrieve` and lazy `GraphRAGVoiceTemplateProvider` in `ipfs_accelerate_py/ipfs_accelerate_py/voice_router.py`; injected fake adapter in `tests/voice/test_abby_voice_pipeline.py` | Retrieval receives the STT transcript plus language/context and supported grounding/result-limit options; returned template provenance survives rendering and synthesis. No `ipfs_datasets_py` import is required at router import time. |
| Curated Abby voice dataset configurations | owned by ABBY-VOICE-G004, G005, and G011; consumed through the provider boundary described in `docs/architecture/ABBY_VOICE_ROUTER_ARCHITECTURE.md` | G001 does not treat manifests or example rows as runtime evidence. Dataset completion remains gated by the child goals and their focused tests. |
| End-to-end voice pipeline acceptance receipt | `tests/voice/test_abby_voice_pipeline.py` plus this receipt | Offline success path proves STT → retrieval → grounded render → TTS, ordered traces, exact synthesized text, provenance, and no fallback. Degraded path proves deterministic safe text and visible fallback metadata. |
| ABBY-VOICE-G001 completion receipt | this file and the G001 acceptance gate in `docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md` | This is an objective-validation repair receipt. Final G001 completion additionally requires its independently tracked child evidence; this receipt makes no false completion claim. |
| Architecture and compatibility boundary | `docs/architecture/ABBY_VOICE_ROUTER_ARCHITECTURE.md`; legacy compatibility assertions in `tests/voice/test_abby_voice_pipeline.py` | `process_voice_turn` is additive and does not remove or change the established `speech_to_text` and `text_to_speech` entry points. |

## Acceptance assertions

The focused test is required to establish all of the following in one offline
suite:

1. caller audio is passed to the selected STT collaborator;
2. the resulting transcript is the retrieval query;
3. response text is derived from a returned grounded response plan;
4. the exact rendered text is passed to TTS;
5. returned audio is non-empty;
6. retrieval source/template provenance is retained in the typed result;
7. traces use the ordered `transcription`, `retrieval`, `rendering`, and
   `synthesis` stages; statuses are `succeeded`, `skipped`, or `failed`, and
   selected collaborators are preserved in provenance;
8. the grounded path has no fallback reason;
9. missing or unusable retrieval produces deterministic safe spoken text,
   records template-stage degradation and fallback reason, and does not invent
   a factual service claim;
10. the test makes no network call, loads no heavyweight model, needs no
    credentials, and mutates no remote dataset;
11. STT failure returns a structured failed result, skips retrieval/rendering,
    and synthesizes the deterministic safe handoff when TTS is available;
12. TTS failure returns `text_only` and preserves the earlier grounded
    text and provenance;
13. the default `to_dict()` receipt contains no raw audio bytes.

## Validation

Command:

```bash
python -m pytest -q tests/voice/test_abby_voice_pipeline.py
```

Result: **passed** on 2026-07-23 — `18 passed, 1 warning`. The warning
is an unrelated pre-existing Starlette/httpx deprecation emitted while pytest
loads `tests/wallet_testclient_compat.py`; it does not affect the focused Abby
pipeline assertions.

## Supervisor alignment

The heap and supervisor todo remain aligned on:

- goal `ABBY-VOICE-G001`;
- bundle `abby-voice/integration`;
- track `voice-platform`;
- P0 priority;
- validation command `python -m pytest -q tests/voice/test_abby_voice_pipeline.py`;
- implementation outputs
  `ipfs_accelerate_py/ipfs_accelerate_py/voice_router.py`,
  `tests/voice/test_abby_voice_pipeline.py`, and
  `docs/architecture/ABBY_VOICE_ROUTER_ARCHITECTURE.md`;
- discovery output under `data/abby_voice/agent_supervisor/discovery`.

No additional child goal is introduced. Existing G002, G003, G004/G005/G011,
G007, G008, and G009 already partition contracts, providers, data, retrieval,
composition, and evaluation. G001 supplies the missing integration validation
and evidence-indexing gate.
