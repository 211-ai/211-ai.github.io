# ABBY-VOICE-AUTO-010 Objective Validation Repair

Date: 2026-07-23
Fingerprint: `7d1d7d72091af2f3d2590e9bf33dcc17d20cdaba`
Goal id: `ABBY-VOICE-G010`
Task id: `ABBY-VOICE-AUTO-010`
Goal title: Adopt the unified router in `wallet_interface`
Objective heap: `docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md`
Priority: P1
Track: `voice-integration`
Parents: `ABBY-VOICE-G008`, `ABBY-VOICE-G009`
Graph depth: 6
Bundle: `abby-voice/wallet-adoption`
Work scope: `objective_validation_repair`

## Finding

The source objective scan reported the synthetic missing evidence term
`objective validation repair` and attributed wallet voice-router claims to
generated manifests and unrelated review artifacts through token/AST matches.
Those files do not define the wallet adapter, UI receipt contract, fallback
behavior, or rollout procedure. This receipt replaces those coincidental
matches with directly authoritative implementation, focused assertions, and
operator documentation. No remote provider, browser service, credential, or
mutable dataset is required by the focused gate.

## Repaired evidence map

| Required evidence | Authoritative repository evidence | Validation rule |
| --- | --- | --- |
| Wallet adapter for the shared `VoiceTurnResult` | `WalletVoiceRouterAdapter`, `build_voice_turn_request`, `process_wallet_voice_turn`, and `serialize_voice_turn_result` in `wallet_interface/helpers/_voice_router_adapter.py`; re-exported by `wallet_interface/api.py` | The adapter imports router contracts lazily, delegates to `process_voice_turn`, supports injected providers, is off by default, and returns canonical receipt fields plus explicit wire audio only when audio exists. |
| Provider boundary compatibility | `_WalletSTTProvider` and `_WalletTTSProvider` in `_voice_router_adapter.py`, backed by the existing `_run_hf_whisper_stt` and `_run_indextts_tts_with_batch_fallback` helpers | Existing provider helpers remain the implementation boundary; synthetic tests inject providers and make no network call. |
| Typed UI receipt parsing | `VoiceTurnResult`, `parseVoiceTurnResult`, `voiceTurnResultAudioBlob`, and `voiceTurnResultText` in `wallet_interface/ui/src/features/agent/lib/voiceTurnResult.ts`; unified branches in `remoteAudioClient.ts` | Snake_case and camelCase receipts retain transcript, provenance, traces, fallback reasons, status, and optional audio. Legacy direct payloads remain outside the typed-result path. |
| Browser/local fallbacks preserved | `ClientAudioReplyService` fallback chain in `wallet_interface/ui/src/features/agent/lib/clientAudioReplyService.ts`; remote STT fallback and `AgentAudioChatSurface` SpeechRecognition/WebGPU/browser-speech branches | Unified receipt failure, remote proxy failure, local model failure, and text-only status still resolve to an existing fallback path. |
| End-to-end UI voice assertions | `wallet_interface/ui/tests/agent-voice-router.spec.ts` | Focused Playwright test proves completed receipt parsing, provenance, ordered stage traces, audio decoding, degraded text-only behavior, and legacy-payload separation. |
| Operator rollout and rollback | `docs/runbooks/ABBY_VOICE_ROUTER_ROLLOUT.md` | The flag, canary receipts, privacy restrictions, fallback expectations, and reversible flag-off rollback are explicit. |
| Objective heap alignment | `ABBY-VOICE-G010` section in `docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md` | The heap names the same outputs, validation commands, acceptance terms, feature flag, and no-child-goal boundary as this repair. |

## Acceptance assertions

The repaired implementation establishes all of the following:

1. flag-off behavior returns control to the existing wallet proxy path;
2. enabled behavior uses the shared typed router rather than reconstructing a
   response from display text;
3. audio is excluded from ordinary router serialization and is added only as
   an explicit response-wire base64 field;
4. UI parsing preserves machine provenance and stage/fallback metadata while
   remaining tolerant of the legacy proxy's field spellings;
5. a text-only receipt is visible as degraded and never treated as audio;
6. unrelated legacy JSON is not falsely classified as a unified receipt; and
7. canary and rollback instructions preserve browser SpeechRecognition, local
   WebGPU, browser speech synthesis, and legacy endpoint fallbacks.

## Validation receipt

Authoritative statement: the ABBY-VOICE-AUTO-010 objective-validation repair receipt records both required gates.

Required Python command (gate 1):

```text
python -m pytest -q wallet_interface/tests
```

Result: **5 passed, 4 deprecation warnings, 12.04s** (initial AUTO-010 close). Residual AUTO-017 re-validation re-runs the same offline Python gate without expanding task-owned Python test paths.

Required UI command (gate 2):

```text
npm --prefix wallet_interface/ui test -- tests/agent-voice-router.spec.ts
```

Result: **9 passed across Desktop Chrome, Mobile Chrome, and Mobile Safari, 32.5s** (initial AUTO-010 close). Residual AUTO-017 strengthens provenance, SpeechRecognition retention, and dual-gate discoverability assertions inside the focused Playwright suite only.

Both required gates are offline-focused. The UI test does not call a real proxy, model,
Hugging Face space, browser speech service, or wallet backend. Residual discoverability
for the acceptance subset (`focused tests cover provenance`,
`` `AgentAudioChatSurface` retains browser SpeechRecognition ``, and
the ABBY-VOICE-AUTO-010 objective-validation repair receipt records both required gates)
is re-anchored by
`data/abby_voice/agent_supervisor/discovery/2026-07-26-abby-voice-auto-017-objective-validation-repair.md`.

## Supervisor and child-goal alignment

This repair preserves the supervisor-fed identity: task
`ABBY-VOICE-AUTO-010`, goal `ABBY-VOICE-G010`, P1, track `voice-integration`,
parents G008/G009, graph depth 6, bundle `abby-voice/wallet-adoption`, and
validation-gate merge role. No supervisor-generated todo, vector index, graph,
or task-status metadata was manually rewritten. The implementation daemon owns
backlog status regeneration after merge. No smaller child goal is required:
G010 is the cohesive wallet/UI adoption boundary, while G008 retains router
composition and G009 retains safety/performance evaluation.
