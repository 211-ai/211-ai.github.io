# ABBY-VOICE-AUTO-008 Objective Validation Repair

Date: 2026-07-23
Fingerprint: `c18c3e2f296cfc1b9d9cf4eaf9adab94c9680b1c`
Goal id: `ABBY-VOICE-G009`
Task id: `ABBY-VOICE-AUTO-008`
Goal title: Establish voice safety quality and performance evaluation
Objective heap: `docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md`
Priority: P0
Track: `voice-evaluation`
Parents: `ABBY-VOICE-G005`, `ABBY-VOICE-G007`, `ABBY-VOICE-G008`
Graph depth: 5
Bundle: `abby-voice/evaluation`
Work scope: `objective_validation_repair`

## Finding

The source objective scan reported the synthetic missing evidence term
`objective validation repair` and attributed G009 terms to unrelated generated
batch, Chainlink, ProveKit, and World ID artifacts through AST token matches.
Those files do not define or validate Abby voice safety or performance. This
receipt replaces those coincidental matches with directly authoritative,
dependency-light fixtures, focused assertions, an offline benchmark, and this
report. No remote state was read or changed.

## Repaired evidence map

| Required G009 evidence | Authoritative evidence | Focused assertion |
| --- | --- | --- |
| Golden voice-turn evaluation set | `data/abby_voice/eval/golden_voice_turns.jsonl` | `test_golden_set_is_schema_valid_and_public_fixture_only` loads eight versioned synthetic records and rejects private/credential content. |
| STT word-error measurements | `_word_error_rate` and the golden-turn loop in `tests/voice/test_abby_voice_safety.py`; benchmark `wer_mean` | `test_golden_metrics_cover_wer_retrieval_slot_fidelity_and_factuality` requires mean WER <= 5%; benchmark repeats it offline. |
| Template retrieval metrics | `GoldenTemplateProvider`, `process_voice_turn`, and benchmark `retrieval_plan_cases` | Every fixture with a response plan must have a successful retrieval trace; safe no-match remains an intentional degraded case. |
| Slot fidelity and grounded factuality | `_response_plan`, `GroundedSlot`, `VoiceGroundingSource`, and source-fact assertions in `tests/voice/test_abby_voice_safety.py` | Every factual slot must retain its exact value and cited source IDs, and match a structured fact from that source. |
| Crisis policy | `crisis_immediate_danger` fixture and `test_crisis_policy_and_accessibility_are_not_latency_optimizations` | Immediate danger retains `911` and urgency and cannot emit delaying language. |
| Accessibility and spoken readability | accessibility/language fixtures plus forbidden-token checks | Spoken text is short, trimmed, citation-free, URL-free, CID-free, and SSML-free. |
| Privacy safety | `test_privacy_safe_receipts_exclude_audio_paths_and_secrets` and `VoiceTurnResult.to_dict()` | Raw caller audio, base64 audio, local paths, and secret-like values do not enter ordinary receipts. |
| Fallback behavior | `test_stt_failure_is_a_failed_safe_handoff_and_tts_failure_is_text_only` and `test_provider_fallback_is_visible_in_stage_receipts` | STT failure, TTS text-only degradation, and failed-then-successful provider fallback are visible in status, traces, and provenance. |
| Latency and cache benchmark | `benchmarks/bench_abby_voice_router.py` | `--offline --check` enforces route/fallback p95 <= 1000 ms and one-provider-call cache reuse without remote work. |
| G009 completion receipt | `docs/reports/ABBY_VOICE_EVALUATION.md` and the G009 gate in the objective heap | The report records the exact commands, thresholds, observed metrics, safety policy, and production measurement caveat. |

## Acceptance assertions

The repaired gate establishes all of the following:

1. the golden set is isolated from private audio and secrets and contains both
   successful and intentionally degraded policy cases;
2. WER, retrieval success, exact slot fidelity, and structured-fact factuality
   are measured from the typed `VoiceTurnResult` receipt;
3. immediate-danger routing and accessibility/readability constraints are
   explicit assertions, not inferred from latency or model output;
4. visual citations are removed from spoken text while source CIDs and slots
   remain in machine provenance;
5. STT, retrieval/grounding, TTS, and provider fallback outcomes are visible
   and deterministic; and
6. the benchmark proves cache behavior and bounded local route/fallback
   overhead without network, credentials, model downloads, or mutable data.

## Validation receipt

Focused command:

```text
python -m pytest -q tests/voice/test_abby_voice_safety.py
```

Result on 2026-07-23: **passed — 11 passed** (one unrelated existing Starlette
deprecation warning during collection).

Required command:

```text
python benchmarks/bench_abby_voice_router.py --offline --check
```

Result on 2026-07-23: **passed — all 10 checks true** over eight cases and
five iterations. Recorded metrics were mean WER 0.0, slot fidelity 1.0,
router p95 0.474 ms, fallback p95 0.492 ms, one synthesis call on a cache
hit, and successful fallback receipts with audio. The local environment may
emit an informational `ipfs_kit_py` availability warning; the benchmark makes
no IPFS call.

## Supervisor and child-goal alignment

This repair preserves the supervisor-fed identity and boundaries:

- task `ABBY-VOICE-AUTO-008`, goal `ABBY-VOICE-G009`, P0, and track
  `voice-evaluation`;
- parents G005/G007/G008, graph depth 5, and bundle `abby-voice/evaluation`;
- conflict policy requiring synthetic or explicitly public fixtures;
- outputs: golden set, focused safety tests, offline benchmark, this receipt,
  the objective heap update, and the evaluation report; and
- validation gate: the exact pytest and `--offline --check` commands above.

No supervisor-generated todo, vector index, graph, or task-status metadata was
manually rewritten. The implementation daemon owns backlog status regeneration
after merge. No smaller child goal is required: G009 is the cohesive safety,
quality, and performance validation boundary, while G010 remains responsible
for downstream wallet adoption.
