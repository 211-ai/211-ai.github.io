# Abby Voice Router Architecture

## Scope

The Abby voice router is a reusable orchestration boundary for one grounded 211
voice turn. It accepts caller audio, obtains a transcript, asks a
GraphRAG-compatible template provider for a response plan grounded in current
evidence, renders text suitable for speech, synthesizes audio, and returns one
typed result containing both user-facing output and an auditable machine
receipt.

The router lives in `ipfs_accelerate_py.voice_router` (at
`ipfs_accelerate_py/ipfs_accelerate_py/voice_router.py`). It is
provider-neutral and has no import-time dependency on `ipfs_datasets_py`,
Transformers, a remote Abby service, or UI code. Existing callers of
`speech_to_text` and `text_to_speech` continue to work; `process_voice_turn` is
an additive integration API.

This document defines the ABBY-VOICE-G001 integration contract. Child goals own
the deeper implementation of provider adapters, canonical dataset rows,
GraphRAG indexing, safety evaluation, and wallet rollout.

## Component boundaries

| Component | Owns | Must not own |
| --- | --- | --- |
| `process_voice_turn` | stage ordering, dependency selection, normalization, trace collection, fallback classification, result assembly | facts about 211 services, network-specific retry policy, UI state |
| STT provider | conversion of request audio to text | response selection or rendering |
| voice template provider | retrieval of a response plan and its evidence/provenance | audio synthesis or hidden replacement of unbound factual slots |
| renderer | binding only values supported by retrieved evidence and producing spoken text | treating example template text as current factual evidence |
| TTS provider | conversion of final spoken text to audio bytes | changing the response meaning |
| caller/UI adapter | capture/playback, consent UX, feature flags | reconstructing provenance from display text |

The template provider is dependency-injected. A production adapter may use
`GraphRAGVoiceTemplateProvider`, `IPLDKnowledgeGraph`, `IPLDVectorStore`, and
`SlottedResponseIndex` from `ipfs_datasets_py`; the router depends only on the
small provider protocol and serializable returned values. This keeps package
imports acyclic and makes the route deterministic in offline tests.

## Turn flow

```text
VoiceTurnRequest
      |
      v
input validation and provider selection
      |
      v
STT: audio ---------------------------> transcript
      |                                    |
      |                                    v
      |                         template retrieval
      |                                    |
      |                          response plan + evidence
      |                                    |
      |                                    v
      |                         grounded spoken rendering
      |                                    |
      |                                    v
      +------------------------------> TTS synthesis
                                           |
                                           v
 VoiceTurnResult: transcript + response text + audio
                  + provenance + stage traces + fallback metadata
```

Request validation occurs while constructing `VoiceTurnRequest`. Turn
orchestration uses these stable `VoiceStageTrace.stage` names, in order:
`transcription`, `retrieval`, `rendering`, and `synthesis`. A stage trace status
is `succeeded`, `skipped`, or `failed`; provider fallback attempts may produce
a failed and then a succeeded trace for the same stage.

1. Validate turn input and resolve explicitly injected or configured providers
   before operational traces begin.
2. `transcription`: use a supplied transcript (recorded as `skipped`) or
   transcribe audio. Empty or
   whitespace-only transcripts are failures, not valid retrieval queries.
3. `retrieval`: retrieve a `VoiceResponsePlan` for the transcript. The provider
   returns structured provenance alongside the plan; citations are never
   reverse-engineered from rendered prose.
4. `rendering`: render spoken text. Only evidence-backed slots may carry
   factual names, phone numbers, addresses, hours, eligibility rules, or
   availability claims.
5. `synthesis`: synthesize the exact rendered text.
6. Assemble the `VoiceTurnResult` with every succeeded, skipped, or failed
   stage trace.

Each attempted or intentionally skipped stage contributes a `VoiceStageTrace`.
A trace names the stage and provider and records status, elapsed time, and a
normalized failure or fallback explanation without secrets or raw private
audio.

## Public turn contracts

`VoiceTurnRequest` is the input envelope. It carries at least one usable source
of input—audio or a pre-supplied transcript—and optional request ID,
language/voice preferences, STT/TTS provider choices, model/device/output
format options, retrieval context, minimum template confidence, and
deterministic fallback text. Request metadata must be serializable and must not
silently become evidence.

The response-plan boundary is also typed:

- `VoiceProviderCapabilities` declares whether a registered provider supports
  transcription, synthesis, or both, allowing operation-specific fallback
  without invoking an unsupported method.
- `VoiceGroundingSource` identifies a source and its citation/provenance
  metadata.
- `GroundedSlot` couples a template variable and value to source IDs. A
  factual slot without a cited source ID is ungrounded and cannot be rendered.
- `VoiceResponsePlan` carries the template ID, template, grounded slots,
  evidence, intent, confidence, and provider metadata.
- `VoiceTemplateProvider.retrieve` requires the transcript and supports
  language and request/retrieval context. The orchestrator also supplies
  grounding constraints and result limit when the concrete provider declares
  those optional keywords; locale participates through the request's effective
  language.
- `GraphRAGVoiceTemplateProvider` is the lazy injected adapter that translates
  the production GraphRAG backend into this contract.

`VoiceTurnResult` is the acceptance receipt. `status` is one of `completed`,
`degraded`, `text_only`, or `failed`. Its observable contract comprises:

- status;
- a derived `degraded` flag;
- transcript;
- response text and the citation-free spoken text;
- optional synthesized audio and audio format;
- ordered stage traces;
- provenance containing the selected STT/template/TTS providers, template ID,
  evidence, grounded slots, and SHA-256 identities for input audio, response
  text, and output audio;
- ordered fallback/degradation reasons;
- a stable cache key.

Audio bytes are valid in the in-process result. An HTTP adapter is responsible
for base64 encoding or object storage and must not discard the rest of the
receipt. `VoiceTurnResult.to_dict()` produces a receipt that excludes raw audio
by default, so logging or persisting the ordinary serialized result does not
copy caller output audio accidentally.

Provider and template objects are collaborators, not global prerequisites.
`process_voice_turn` accepts injected collaborators for tests and embedded
deployments, while normal configured-provider resolution remains available for
production. Provider-specific keyword arguments are kept stage-scoped so, for
example, a TTS option cannot leak into STT or retrieval.

## Grounding and provenance

GraphRAG output is a response plan, not an uncited final answer. The provider
boundary carries:

- a stable template or response-frame identifier;
- source identifiers or CIDs for the evidence used;
- grounded slot values, when any;
- retrieval confidence or equivalent selection metadata when available.

The router preserves this information in `VoiceTurnResult`. Human-readable
citations may be omitted from spoken text, but machine provenance must remain.
Request context, cached sample wording, model memory, and template examples are
not factual evidence.

A `GroundedSlot` must cite an evidence source ID that is present in the plan.
When a source supplies structured facts, the slot value must match the fact
declared for that slot. An explicit current source ID is sufficient when the
source has no structured facts; the router must not fabricate an expected fact
that the retrieval backend did not supply.

If retrieval yields no usable grounded plan, the router uses a short,
deterministic response that asks the caller to clarify or routes them to a safe
next step. It must not manufacture a service, phone number, address, hours, or
eligibility claim. This is a successful degraded turn only if the degradation
is visible in both the trace and result fallback metadata.

## Failure and fallback semantics

Failures are classified at their originating stage.

| Condition | Result |
| --- | --- |
| Neither usable audio nor transcript supplied | reject `VoiceTurnRequest` construction with `ValueError` |
| STT provider unavailable or transcription fails | skip retrieval/rendering, synthesize the deterministic safe handoff when TTS is available, and return status `failed` with the failed transcription and skipped-stage traces |
| Empty transcript | fail at STT; never issue a blank GraphRAG query |
| Retrieval error or no grounded plan | use deterministic safe response, retain the retrieval failure in trace and fallback reason |
| Rendering rejects unbound factual slots | use deterministic safe response and retain any safe retrieval provenance |
| TTS provider fallback succeeds | return audio and identify both degradation and selected provider |
| All TTS providers fail | return `text_only` with audio empty, preserving completed-stage traces and synthesis failure; never report a fully successful voice turn |

Fallback metadata is data, not logging. Logs are operational hints and cannot
be the only place a caller learns that its response degraded.

## Caching and privacy

The existing STT and TTS caches remain implementation details of their public
functions. Cache identity must include the operation, provider/model options,
and a digest of audio or text plus relevant stage options. Raw caller audio,
transcripts, credentials, and source documents must not appear in cache keys or
stage logs.

A cached retrieval plan is safe only while its source identity and freshness
policy remain valid. The G001 integration API must not cache a rendered factual
answer independently of its provenance. Private caller audio is not written to
the Abby dataset by this pipeline.

## Trust and safety boundaries

- Remote providers receive data only when selected by deployment policy.
- Secrets are read by provider adapters and are excluded from requests,
  results, traces, cache identities, and errors returned to users.
- Retrieved phone numbers, addresses, hours, availability, and eligibility
  values require current source provenance.
- Emergency or crisis behavior is a policy gate, not an optimization fallback;
  ABBY-VOICE-G009 owns its evaluation fixtures.
- Tests use synthetic audio and fake collaborators. The G001 acceptance test
  performs no network calls and contains no private caller data.
- Remote Hugging Face buckets and datasets are immutable from this route.

## Objective validation and ownership

The executable integration gate is:

```bash
python -m pytest -q tests/voice/test_abby_voice_pipeline.py
```

That test must exercise a successful grounded turn, deterministic degraded
retrieval/rendering, a structured failed STT turn with synthesized safe
handoff, and a text-only TTS failure using
injected fake STT, template, and TTS collaborators. It proves stage order,
exact text passed to synthesis, citation removal from spoken text with
provenance retention, raw-audio-safe serialization, and fallback visibility.
It also checks the legacy `speech_to_text` and `text_to_speech` entry points as
needed to protect backward compatibility.

Evidence for ABBY-VOICE-AUTO-001 is indexed in
`data/abby_voice/agent_supervisor/discovery/2026-07-23-abby-voice-auto-001-objective-validation-repair.md`.
Only repository paths that define behavior or assert it count as evidence.
Large batch manifests and unrelated JSON containing matching symbol strings do
not.

Passing this integration gate repairs the G001 objective validation gap; it
does not by itself complete the independently tracked dataset, production
provider, evaluation, or wallet-adoption child goals.
