# Abby unified voice-router rollout

This runbook enables the shared `VoiceTurnRequest`/`VoiceTurnResult` contract
in `wallet_interface` without removing the existing browser or proxy fallback
paths. It covers the staged adoption owned by `ABBY-VOICE-G010`.

Residual G010 discoverability anchors (exact evidence phrases):

- focused tests cover provenance
- `AgentAudioChatSurface` retains browser SpeechRecognition
- the ABBY-VOICE-AUTO-010 objective-validation repair receipt records both required gates

Authoritative maps:

- `data/abby_voice/agent_supervisor/discovery/2026-07-23-abby-voice-auto-010-objective-validation-repair.md`
- residual: `data/abby_voice/agent_supervisor/discovery/2026-07-26-abby-voice-auto-017-objective-validation-repair.md`

## Components and guardrails

The wallet boundary is `wallet_interface/helpers/_voice_router_adapter.py`.
It lazily delegates to `ipfs_accelerate_py.voice_router.process_voice_turn`,
uses the existing wallet Whisper and IndexTTS helpers as provider shims, and
serializes a receipt with transcript, spoken text, provenance, stage traces,
fallback reasons, and optional base64 audio. Focused tests cover provenance on
that receipt (providers, evidence, grounded slots, and stage traces).

The browser boundary is
`wallet_interface/ui/src/features/agent/lib/voiceTurnResult.ts`. The remote
audio client accepts the unified receipt as well as the older direct text and
base64-audio payloads. `AgentAudioChatSurface` retains browser SpeechRecognition
(`window.SpeechRecognition` / `webkitSpeechRecognition`) when remote STT is
unavailable. The following fallbacks remain enabled throughout the rollout:

| Failure or policy condition | Client behavior |
| --- | --- |
| Unified router flag is off | Existing proxy handler remains authoritative |
| Unified proxy unavailable or returns an invalid receipt | Existing fallback endpoint, then local WebGPU audio |
| Local WebGPU is unavailable, warming, or fails | Browser speech synthesis |
| Remote STT unavailable or empty | Browser `SpeechRecognition` transcript (`AgentAudioChatSurface` retains browser SpeechRecognition) |
| Unified receipt is `text_only` | Speak `spoken_text` with browser speech when available |

The adapter flag defaults to off:

```text
WALLET_VOICE_UNIFIED_ROUTER_ENABLED=0
```

Do not enable it globally until the deployed-like checks below pass for the
target environment. The UI may still have `VITE_VOICE_PROXY_ENABLED=true`;
that controls whether the client attempts the proxy and is independent of the
server-side adoption flag.

## Preflight

Run from the repository root. These are the same dual offline gates that the
ABBY-VOICE-AUTO-010 objective-validation repair receipt records both required gates for:

```bash
python -m pytest -q wallet_interface/tests
npm --prefix wallet_interface/ui test -- tests/agent-voice-router.spec.ts
```

Confirm that the proxy response is a JSON `VoiceTurnResult`-compatible object
with:

- `contract_version`, `request_id`, `status`, `transcript`,
  `response_text`, and `spoken_text`;
- `provenance` with selected providers and any evidence/grounded slots
  (focused tests cover provenance for these fields);
- ordered `traces` for transcription, retrieval, rendering, and synthesis;
- `fallback_reasons` when the status is degraded, failed, or text-only; and
- `audio_base64` plus `audio_mime_type` only when audio was actually produced.

Ordinary logs and persisted receipts must not contain raw input audio. The
adapter's normal router serialization excludes raw audio; the explicit wire
field is base64 audio for the caller response only and must not be copied into
metrics or logs.

## Staged rollout

1. Deploy the adapter and UI code with the flag set to `0`. Check that legacy
   TTS/STT requests still succeed and that browser speech/local WebGPU tests
   remain green.
2. Enable the flag for one internal or synthetic-canary proxy instance:

   ```bash
   export WALLET_VOICE_UNIFIED_ROUTER_ENABLED=1
   ```

3. Exercise a text-to-speech request, a voice-reply request with a synthetic
   WAV input, a remote STT failure, a TTS failure, and a fallback-endpoint
   success. Record the receipt rather than only the HTTP status.
4. Verify that a successful receipt has a non-empty `response_text`, a
   matching `spoken_text`, audio bytes, the four ordered stage names, and a
   selected TTS provider. Verify that fallback receipts visibly carry their
   reason and do not claim audio when `status` is `text_only`.
5. Increase exposure by deployment slice. Watch router status, stage failure
   counts, browser fallback rate, receipt parse failures, p95 request latency,
   and audio playback errors. A canary is healthy only when these stay within
   the existing voice SLOs and no new privacy or provenance violations appear.

## Rollback

Rollback is reversible and does not require deleting data or changing the
shared router:

```bash
export WALLET_VOICE_UNIFIED_ROUTER_ENABLED=0
```

Restart or reload the proxy deployment so the process reads the flag again.
The UI will continue to use the configured legacy proxy, local WebGPU, and
browser speech paths. If the UI receipt parser itself must be reverted, deploy
the previous UI bundle; do not remove or rewrite receipt evidence. Preserve
the failed receipt IDs, stage errors, endpoint role, and deployment revision
for incident review while redacting audio, credentials, prompts, local paths,
and source documents.

## Exit criteria

The rollout can become the default only after the operator has retained:

1. passing Python and focused Playwright validation receipts;
2. a deployed-like successful unified receipt;
3. a degraded retrieval or provider-fallback receipt with an explicit reason;
4. a text-only TTS-failure receipt with no output-audio hash or audio field;
5. evidence that remote STT failure reaches browser SpeechRecognition and that
   local WebGPU failure reaches browser speech synthesis; and
6. a tested flag-off rollback in the same deployment shape.

Until all six receipts exist, leave the feature flag opt-in and retain the
legacy endpoint configuration.
