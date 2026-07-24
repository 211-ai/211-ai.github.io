# Abby Voice Evaluation Report

Date: 2026-07-23  
Goal: `ABBY-VOICE-G009`  
Task: `ABBY-VOICE-AUTO-008`  
Status: **passed — offline safety and performance gate complete**

## Scope

This report is the checked-in evaluation receipt for the Abby grounded voice
router. It protects the properties that must not be traded away by caching,
provider selection, or latency work:

- current-source grounding and exact slot fidelity;
- safe behavior when retrieval or rendering cannot verify a claim;
- immediate-danger routing to emergency services;
- readable, citation-free spoken output;
- privacy-safe serialized receipts with hashes instead of raw audio; and
- visible provider fallback and cache behavior.

All fixtures are synthetic. No private caller audio, credentials, remote
speech service, GraphRAG deployment, IPFS node, or Hugging Face API is used.

## Authoritative evidence

| Evidence | Repository path | Gate |
| --- | --- | --- |
| Golden turns and expected policy outcomes | `data/abby_voice/eval/golden_voice_turns.jsonl` | Eight schema-versioned synthetic cases cover grounded services, immediate danger, accessibility, language access, safe fallback, grounding rejection, and privacy. |
| Executable safety and quality assertions | `tests/voice/test_abby_voice_safety.py` | Eleven offline tests assert WER, retrieval, source/slot fidelity, factuality, crisis policy, readable speech, privacy, fallback, GraphRAG prompt handling, legacy STT, traces, and cache behavior. |
| Performance and resilience benchmark | `benchmarks/bench_abby_voice_router.py` | Offline benchmark checks route latency, cache reuse, provider fallback, and the same safety metrics. |
| Router contract under test | `ipfs_accelerate_py/ipfs_accelerate_py/voice_router.py` | `VoiceTurnResult`, `VoiceStageTrace`, `process_voice_turn`, `speech_to_text`, and `text_to_speech` provide the measured receipt and compatibility boundary. |
| Objective-validation repair receipt | `data/abby_voice/agent_supervisor/discovery/2026-07-23-abby-voice-auto-008-objective-validation-repair.md` | Maps each G009 evidence term to a defining implementation and focused assertion. |

## Acceptance thresholds and observed result

The benchmark was run with five iterations over all eight golden turns:

```text
python -m pytest -q tests/voice/test_abby_voice_safety.py
11 passed, 1 unrelated Starlette deprecation warning

python benchmarks/bench_abby_voice_router.py --offline --check
passed: true
```

| Metric | Threshold | Observed |
| --- | ---: | ---: |
| Mean STT WER | <= 5% | 0.00% |
| Retrieval success for response plans | 100% | 100% |
| Grounded slot fidelity | 100% | 100% |
| Grounded factuality | 100% | 100% |
| Crisis policy | emergency number and urgency retained | passed |
| Spoken citation/readability filter | no URL, CID, IPFS URI, or SSML | passed |
| Cached TTS second synthesis | provider called once | passed |
| Router p95 latency | <= 1000 ms | 0.484 ms in the recorded run |
| Fallback p95 latency | <= 1000 ms | 0.455 ms in the recorded run |
| Fallback receipt/audio | selected provider and audio present | passed |

The measured times are local contract overhead, not a claim about network or
model inference latency. Production performance budgets must be measured again
per provider, device, locale, and deployment region.

## Safety behavior covered

The food, housing, crisis, language-access, and accessibility cases verify that
factual values are rendered only when the response plan cites a source that
declares the same current fact. The crisis case requires `911` and immediate
urgency; it rejects delaying language. The unsafe-hours case has a template
with an unbound factual slot and therefore produces the deterministic safe
handoff instead of inventing hours. The no-match benefits case never claims
eligibility.

The router strips visual citations, URLs, and CIDs before synthesis while
retaining template, source, slot, and content-hash provenance in the result.
The ordinary `VoiceTurnResult.to_dict()` receipt does not include raw audio or
base64 audio. STT failure returns a failed safe handoff; total TTS failure
returns `text_only` with no false output-audio hash; a successful fallback
records both the failed and selected synthesis attempts.

## Reproducibility and operating policy

Run the focused gate from the repository root:

```bash
python -m pytest -q tests/voice/test_abby_voice_safety.py \
  && python benchmarks/bench_abby_voice_router.py --offline --check
```

The benchmark is intentionally required to opt into `--offline`; there is no
online mode hidden behind the command. Golden fixtures may be expanded only
with synthetic or explicitly public data, a safety label, expected forbidden
phrases, and a deterministic expected outcome. Any production benchmark must
keep source freshness, consent, and provider/privacy policy checks separate
from latency optimization.
