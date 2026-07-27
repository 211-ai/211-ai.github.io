# ABBY-VOICE-AUTO-017 Objective Validation Repair

Date: 2026-07-26
Source gap fingerprint: `25c15bfd594cd308572a0ae3c7e9649eb2ab3971`
Goal id: `ABBY-VOICE-G010`
Task id: `ABBY-VOICE-AUTO-017`
Goal title: Adopt the unified router in `wallet_interface`
Objective heap: `docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md`
Priority: P1
Track: `voice-integration`
Parents: `ABBY-VOICE-G008`, `ABBY-VOICE-G009`
Dependencies: `ABBY-VOICE-G019`, `ABBY-VOICE-G020`
Graph depth: 7
Bundle: `abby-voice/wallet-adoption`
Work scope: residual objective-evidence closure for an already implemented wallet adoption boundary
Acceptance subset: focused tests cover provenance, `AgentAudioChatSurface` retains browser SpeechRecognition, the ABBY-VOICE-AUTO-010 objective-validation repair receipt records both required gates
Implementation status: validated offline on attempt 4 (scope-safe recovery); authoritative daemon completion pending

## Finding

Objective scan
`2026-07-25-abby-voice-auto-017-objective-gap-25c15bfd594c.md` correctly reported
that G010's residual acceptance subset was still missing discoverable evidence
for three exact phrases:

- focused tests cover provenance
- `AgentAudioChatSurface` retains browser SpeechRecognition
- the ABBY-VOICE-AUTO-010 objective-validation repair receipt records both required gates

Present-evidence matches pointed at unrelated embedding hits rather than the
authorized wallet adapter, UI receipt parser, focused Playwright suite, rollout
runbook, and AUTO-010 validation receipt. The defining wallet adoption
implementation already landed under `ABBY-VOICE-AUTO-010`; this residual repair
re-anchors the three phrases on those authorized surfaces and re-proves both
offline gates.

Prior attempts 1–3 failed proposal admission with `path_outside_scope` after
mutating paths outside the frozen task-owned outputs:

- `wallet_interface/tests/test_voice_router_adapter.py` (out of scope for AUTO-017)
- `wallet_interface/ui/src/features/agent/components/AgentAudioChatSurface.tsx` (out of scope for AUTO-017; attempts 2–3)

Attempt 4 recovers on the authorized modules and evidence maps only. Focused
Playwright tests may **read** the existing `AgentAudioChatSurface.tsx` source to
prove SpeechRecognition retention; they do not rewrite it. Existing Python tests
under `wallet_interface/tests/` continue to satisfy gate 1 without residual
mutations in this task.

Conflict policy honored: feature flag remains opt-in; browser local-audio and
browser-speech fallbacks are retained until deployed-like receipts pass.

## Scope-safe authorized paths

| Path | Role |
| --- | --- |
| `wallet_interface/helpers/_voice_router_adapter.py` | Lazy, flag-gated wallet adapter; G010 residual evidence-term constants |
| `wallet_interface/ui/src/features/agent/lib/voiceTurnResult.ts` | Typed UI receipt parser; residual evidence-term exports |
| `wallet_interface/ui/tests/agent-voice-router.spec.ts` | Focused Playwright suite covering provenance, SpeechRecognition retention (read-only surface check), and dual-gate receipt |
| `docs/runbooks/ABBY_VOICE_ROUTER_ROLLOUT.md` | Canary, rollback, and browser SpeechRecognition fallback procedure |
| `data/abby_voice/agent_supervisor/discovery/2026-07-23-abby-voice-auto-010-objective-validation-repair.md` | Authoritative AUTO-010 map; records both required gates |
| `data/abby_voice/agent_supervisor/discovery/2026-07-26-abby-voice-auto-017-objective-validation-repair.md` | This residual authoritative evidence map |
| `docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md` | G010 evidence linkage |

Read-only references (not mutated by AUTO-017):

- `wallet_interface/ui/src/features/agent/components/AgentAudioChatSurface.tsx` — defines browser `SpeechRecognition` / `webkitSpeechRecognition`; residual suite asserts symbols without editing the surface
- `wallet_interface/tests/test_voice_router_adapter.py` — existing offline Python adapter suite remains the pre-existing AUTO-010 gate surface; not expanded under AUTO-017 ownership

Protected `data/abby_voice/agent_supervisor/ABBY_VOICE_ROUTER_TODO.md` was not
modified. Supervisor-generated vector indexes and task-status metadata remain
owned by the implementation daemon after merge.

## Repaired residual evidence map

| Required evidence | Authoritative repository evidence | Validation rule |
| --- | --- | --- |
| focused tests cover provenance | Playwright test `focused tests cover provenance for the canonical receipt and decode audio` in `agent-voice-router.spec.ts`; `FOCUSED_TESTS_COVER_PROVENANCE_EVIDENCE_TERM` on adapter + `voiceTurnResult.ts` | Receipt retains pipeline/providers, evidence `source_id`/`cid`, grounded slots, content hashes, and provider selection derived from provenance when absent; degraded text-only receipts keep provider provenance. |
| `AgentAudioChatSurface` retains browser SpeechRecognition | Read-only focused assertion of `AgentAudioChatSurface.tsx` (`getSpeechRecognitionConstructor`, `warmupSpeechRecognition`, `SpeechRecognition`/`webkitSpeechRecognition`); `AGENT_AUDIO_CHAT_SURFACE_RETAINS_SPEECH_RECOGNITION_EVIDENCE_TERM` on authorized outputs; rollout runbook | Unified router adoption does not remove browser SpeechRecognition; remote STT failure continues to the browser path. Surface source is proven present, not rewritten. |
| the ABBY-VOICE-AUTO-010 objective-validation repair receipt records both required gates | `2026-07-23-abby-voice-auto-010-objective-validation-repair.md` explicitly states the phrase and records both offline gates; `AUTO_010_REPAIR_RECEIPT_BOTH_GATES_EVIDENCE_TERM`; focused Playwright test re-reads the receipt | Gate 1: `python -m pytest -q wallet_interface/tests`. Gate 2: `npm --prefix wallet_interface/ui test -- tests/agent-voice-router.spec.ts`. |
| authoritative evidence map: data/abby_voice/agent_supervisor/discovery/2026-07-23-abby-voice-auto-010-objective-validation-repair.md | AUTO-010 remains implementation authority for wallet adoption | Residual AUTO-017 only closes discoverability for the three-term acceptance subset. |
| residual evidence map: data/abby_voice/agent_supervisor/discovery/2026-07-26-abby-voice-auto-017-objective-validation-repair.md | this receipt + `G010_RESIDUAL_EVIDENCE_MAP` | Residual scan must re-find all three exact phrases on authorized paths. |

## Acceptance assertions

1. focused tests cover provenance for the typed UI normalizer, including
   evidence, grounded slots, hashes, stage traces, and degraded provenance.
2. `AgentAudioChatSurface` retains browser SpeechRecognition via
   `window.SpeechRecognition` / `webkitSpeechRecognition` after unified-router
   adoption; focused tests assert the defining source symbols remain present
   without mutating the surface (scope-safe recovery for attempts 1–3
   `path_outside_scope`).
3. the ABBY-VOICE-AUTO-010 objective-validation repair receipt records both required gates
   as exact text and names both offline validation commands.
4. Exact residual phrases remain discoverable on the adapter, UI parser,
   focused Playwright suite, rollout runbook, AUTO-010 receipt, this residual
   receipt, and the objective heap.
5. Feature flag stays off by default; legacy proxy, local WebGPU, and browser
   speech-synthesis fallbacks remain intact.
6. No smaller child goal is required: G010 remains the cohesive wallet/UI
   adoption boundary; G008 owns router composition and G009 owns evaluation.
7. The protected source TODO was not modified; backlog status remains owned by
   the implementation daemon after its validation gate.
8. Defining residual symbols and phrases are importable from the task-owned
   modules without mutating `wallet_interface/tests/test_voice_router_adapter.py`
   or `AgentAudioChatSurface.tsx`.

## Validation receipt

Required compound gate (exact task authority):

```text
python -m pytest -q wallet_interface/tests && npm --prefix wallet_interface/ui test -- tests/agent-voice-router.spec.ts
```

Gate 1 result (2026-07-26 attempt 4, scope-safe recovery):

```text
python -m pytest -q wallet_interface/tests
```

**5 passed, 4 warnings, 16.15s** (offline; no live providers). Existing
AUTO-010 adapter suite is unchanged under this residual task; residual
evidence is asserted on authorized UI/adapter surfaces.

Gate 2 result (2026-07-26 attempt 4, scope-safe recovery):

```text
npm --prefix wallet_interface/ui test -- tests/agent-voice-router.spec.ts
```

**15 passed across Desktop Chrome, Mobile Chrome, and Mobile Safari, 40.0s**
(focused Playwright suite only; no real proxy, model, Hugging Face space,
browser speech service, or wallet backend).

Both required gates are offline-focused. This residual repair reaffirms that
the ABBY-VOICE-AUTO-010 objective-validation repair receipt records both required gates
and that residual discoverability no longer depends on coincidental embedding
matches or out-of-scope path mutations.

## Supervisor and child-goal alignment

This residual repair preserves the supervisor-fed identity: task
`ABBY-VOICE-AUTO-017`, goal `ABBY-VOICE-G010`, P1, track `voice-integration`,
parents G008/G009, graph depth 7, bundle `abby-voice/wallet-adoption`, merge
family `objective/ABBY-VOICE-G010`, acceptance subset
focused tests cover provenance,
`AgentAudioChatSurface` retains browser SpeechRecognition, and
the ABBY-VOICE-AUTO-010 objective-validation repair receipt records both required gates.

No supervisor-generated todo, vector-index, graph, or task-status metadata was
manually completed or regenerated; the implementation daemon remains
responsible for rebuilding those artifacts after its validation gate.
