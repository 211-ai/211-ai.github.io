# ABBY-VOICE-AUTO-020 Objective Validation Repair

Date: 2026-07-26
Source gap fingerprint: `749af6bcaadfe2644f29e37b95f398c30490c9fc`
Goal id: `ABBY-VOICE-G020`
Task id: `ABBY-VOICE-AUTO-020`
Goal title: Prove the distributed dataset-to-voice pipeline end to end
Objective heap: `docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md`
Priority: P0
Track: `voice-evaluation`
Parents: `ABBY-VOICE-G011`
Dependencies: `ABBY-VOICE-G009`, `ABBY-VOICE-G016`, `ABBY-VOICE-G018`, `ABBY-VOICE-G019`
Graph depth: 4
Bundle: `abby-voice/end-to-end`
Work scope: `goal_subgoal_multi_evidence_batch`
Implementation status: validated offline; authoritative daemon completion pending

## Finding

The objective scan correctly found that G020 named, but did not yet define or
test, **offline deterministic fixture**, **worker-crash recovery test**, and
**capability/resource backpressure test** on an authorized distributed
dataset-to-voice path. Present-evidence matches pointed at unrelated DuckDB
benchmark docs and non-voice canary scripts rather than a restart-safe fixture
spanning inventory → jobs → release → GraphRAG voice output.

Conflict policy from the gap: offline gates use fakes and tiny public fixtures;
real provider and remote read canaries require explicit scope, credentials, cost
limit, and retention approval.

## Scope-safe authorized paths

| Path | Role |
| --- | --- |
| `tests/voice/test_abby_voice_distributed_pipeline.py` | Offline evidence suite: offline deterministic fixture, worker-crash recovery test, capability/resource backpressure test, failure-class matrix, critical-slot fidelity, residual term anchors |
| `docs/runbooks/ABBY_VOICE_AUDIO_JOBS.md` | Operator runbook for audio jobs, recovery, admission, privacy, human-approved real-provider canary |
| `docs/reports/ABBY_VOICE_DISTRIBUTED_EVALUATION.md` | Distributed evaluation receipt and observed offline gate |
| `data/abby_voice/agent_supervisor/discovery/2026-07-26-abby-voice-auto-020-objective-validation-repair.md` | This authoritative evidence map |
| `docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md` | G020 evidence linkage |

Protected `data/abby_voice/agent_supervisor/ABBY_VOICE_ROUTER_TODO.md` was not
modified. No remote Hugging Face write or production pointer promotion is
performed (G021 ownership).

## Repaired evidence map

| Required evidence | Authoritative repository evidence | Validation rule |
| --- | --- | --- |
| offline deterministic fixture | `test_offline_deterministic_fixture_end_to_end` + `_offline_deterministic_fixture` in `tests/voice/test_abby_voice_distributed_pipeline.py` | Fixture runs pinned inventory → normalization → DuckDB TTS/validate/ASR → reconciliation → `AbbyVoiceHFReleaseBuilder` → `AbbyVoiceReleaseLoader` → `process_voice_turn` with complete lineage and no network |
| worker-crash recovery test | `test_worker_crash_recovery_test` in the same suite; `TaskQueue.recover_expired_leases` / claim ownership | Replaying after process termination recovers expired leases; stale workers cannot complete; completed identities reuse with no duplicate provider call or conflicting artifact |
| capability/resource backpressure test | `test_capability_resource_backpressure_test`; `PeerCapabilityRegistry` + `ResourceScheduler` | Capability mismatch refuses peer match; host CPU/RAM/disk/GPU and provider concurrency/quota/token saturation admit zero lanes with explicit backpressure reasons |
| DuckDB TTS-to-validate-to-ASR workflow receipt | offline fixture stages in the suite; job contracts `VoiceTTSJob` / `VoiceAudioValidationJob` / `VoiceASRJob` | Ordered durable tasks complete with descriptor-only payloads and lineage |
| real-provider canary protocol | `docs/runbooks/ABBY_VOICE_AUDIO_JOBS.md`; report canary section | Separately human-approved, bounded by item count and cost, non-sensitive rows, staging prefix only |
| privacy and lineage audit | `_privacy_scan` + critical-slot tests; runbook privacy section | Logs, DuckDB state, receipts, and artifacts pass secret/private-audio/private-transcript scan; factual slots exact in text, ASR, and runtime speech |
| authoritative evidence map: data/abby_voice/agent_supervisor/discovery/2026-07-26-abby-voice-auto-020-objective-validation-repair.md | this receipt + `G020_AUTHORITATIVE_EVIDENCE_MAP` / `test_g020_evidence_phrases_are_discoverable` | Residual scan re-finds the three acceptance phrases on the authorized paths |

## Acceptance assertions

1. The offline deterministic fixture runs pinned inventory to normalization to
   deterministic tasks to TTS to audio validation to ASR to reconciliation to
   release to GraphRAG voice turn with complete lineage and no network.
2. Replaying after process termination recovers expired leases, reuses completed
   identities, and produces no duplicate provider call or conflicting artifact.
3. Capability mismatch, GPU/RAM/disk/provider saturation, timeout, cancellation,
   429, retryable 5xx, circuit-open, corrupt input, quality rejection, and
   text-only fallback are each asserted offline.
4. Critical factual slots are exact in rendered text, admitted audio ASR, and
   the final runtime response; citations remain machine provenance and are
   absent from spoken output.
5. Logs, DuckDB state, receipts, and artifacts pass a secret/private-audio/
   private-transcript scan.
6. Any real-provider canary is separately human-approved, bounded by item count
   and cost, uses non-sensitive rows, and writes only to a staging prefix.

## Validation receipt

Command:

```text
python -m pytest -q tests/voice/test_abby_voice_distributed_pipeline.py tests/voice/test_abby_voice_safety.py && python benchmarks/bench_abby_voice_router.py --offline --check
```

Result on 2026-07-26: **passed — 25 passed** for the pytest gate and
`passed: true` for `benchmarks/bench_abby_voice_router.py --offline --check`.

The gate is offline and uses only local fixtures; it requires no credentials
and performs no network or remote bucket/dataset write.

## Supervisor and child-goal alignment

This evidence remains aligned with merge family `objective/ABBY-VOICE-G020`,
bundle `abby-voice/end-to-end`, and parallel lane `abby-voice-evaluation`. No
supervisor-generated TODO, vector index, objective graph, or task-status
metadata was manually completed or regenerated; the implementation daemon
remains responsible for rebuilding those artifacts after its validation gate.

No smaller child goal is needed. G020 owns verification and canary evidence.
G021 owns the remote release transaction and promotion decision.
