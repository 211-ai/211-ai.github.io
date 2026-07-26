# ABBY-VOICE-AUTO-026 Objective Validation Repair

Date: 2026-07-26
Source gap fingerprint: `b40f59f925a488f03575180069483ee4d405075c`
Goal id: `ABBY-VOICE-G016`
Task id: `ABBY-VOICE-AUTO-026`
Goal title: Add idempotent recovery resource admission and provider batching
Objective heap: `docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md`
Priority: P0
Track: `voice-scheduling`
Parents: `ABBY-VOICE-G011`
Dependencies: `ABBY-VOICE-G015`
Graph depth: 4
Bundle: `abby-voice/audio-scheduling`
Work scope: residual objective-evidence closure for an already implemented boundary

## Finding

Objective scan `2026-07-26-abby-voice-auto-026-objective-gap-b40f59f925a4.md`
reported six missing evidence terms for G016 even though AUTO-015 already
implemented queue recovery, audio capability admission, provider batch
compatibility, and resource saturation on the frozen output paths. The scan's
"present evidence" matches pointed at unrelated embedding hits rather than the
authorized TaskQueue, capability, provider-batch, and recovery-test surfaces.

This repair does **not** invent a second scheduler. It anchors the residual
terms as exact, discoverable evidence on the same frozen paths AUTO-015 owns,
and reaffirms that the authoritative evidence map remains:

`authoritative evidence map: data/abby_voice/agent_supervisor/discovery/2026-07-26-abby-voice-auto-015-objective-validation-repair.md`

## Repaired residual evidence map

| Required evidence | Authoritative repository evidence | Validation rule |
| --- | --- | --- |
| persisted attempt/backoff/lease state | `TaskQueue` schema and APIs in `ipfs_accelerate_py/ipfs_accelerate_py/p2p_tasks/task_queue.py` (`attempt`, `max_attempts`, `next_attempt_at`, `lease_until`, `heartbeat_at`, `retry`, `recover_expired_leases`); `test_backoff_blocks_claim_and_expired_final_attempt_fails`, `test_owned_heartbeat_extends_lease_and_expired_claim_recovers`, and `test_existing_duckdb_schema_is_migrated_in_place` in `ipfs_accelerate_py/test/test_voice_job_recovery.py` | Retry writes a persisted `next_attempt_at` that blocks claims; expired final attempts fail terminally; migrated legacy rows receive attempt/backoff/lease defaults. |
| owner heartbeats | `TaskQueue.heartbeat` in `task_queue.py`; `test_owned_heartbeat_extends_lease_and_expired_claim_recovers` and stale-owner completion rejection in `test_stale_worker_cannot_finish_recovered_claim` | Only the assigned worker can renew `lease_until` / `heartbeat_at`. Non-owners cannot heartbeat or complete a recovered claim. |
| IndexTTS/Whisper batch-size-one policy | `_SINGLE_MEMBER_AUDIO_PROVIDERS` and `_requires_single_member_batch` in `provider_batch_scheduler.py`; `test_audio_adapters_are_physical_batch_size_one` | IndexTTS and Whisper adapter aliases launch at most one physical member even when the scheduler window and max batch size would otherwise allow multi-member batches. |
| existing sibling isolation and single-flight receipts | Module contract and single-flight/receipt paths in `provider_batch_scheduler.py`; preserved API tests `test_cancelled_batch_member_does_not_cancel_sibling_and_emits_evidence`, `test_singleflight_collapses_identical_work_but_preserves_member_identity`, `test_member_failure_isolated_and_provider_capacity_checked_before_dispatch`, and `test_member_timeout_is_independent_from_running_batch_sibling` in `test/api/test_agent_supervisor_provider_batch_scheduler.py` | Cancellation, timeout, or failure of one member never cancels or corrupts siblings; identical work collapses to one physical call with content-addressed receipts. |
| existing `ResourceScheduler` CPU/RAM/disk/GPU/provider backpressure assertions | `test_resource_saturation_backpressures_the_candidate_wave` in `test_voice_job_recovery.py`; host CPU/RAM/disk/GPU and provider admission suite in `test/api/test_agent_supervisor_resource_scheduler.py` | Saturation returns empty admissions with explicit backpressure reasons rather than overclaiming host or provider capacity. |
| authoritative evidence map: data/abby_voice/agent_supervisor/discovery/2026-07-26-abby-voice-auto-015-objective-validation-repair.md | This residual repair plus `G016_AUTHORITATIVE_EVIDENCE_MAP` / `test_g016_residual_evidence_terms_and_authoritative_map_are_recorded` in `test_voice_job_recovery.py`; AUTO-015 map content above | The AUTO-015 map remains the implementation authority; AUTO-026 only closes residual scan discoverability without changing the execution-control boundary. |

## Acceptance assertions

1. Atomic submit-once, attempt, max attempts, next-attempt, lease, and owner
   heartbeats make a worker crash recoverable without duplicate provider
   execution.
2. IndexTTS and Whisper remain physical batch size one until adapters prove
   real multi-member batching.
3. Existing sibling isolation and single-flight receipts remain the provider
   batch contract; resource saturation backpressures rather than overclaims.
4. No smaller child goal is required: residual terms describe the same
   execution-control boundary AUTO-015 already implemented.
5. The protected source TODO was not modified; backlog status remains owned by
   the implementation daemon after its validation gate.

## Validation receipt

Executed gate:

```text
python -m pytest -q ipfs_accelerate_py/test/test_voice_job_recovery.py ipfs_accelerate_py/test/api/test_agent_supervisor_provider_batch_scheduler.py ipfs_accelerate_py/test/api/test_agent_supervisor_resource_scheduler.py
```

Result: **PASS — 93 tests on 2026-07-26** (includes the residual-term anchor
added by this repair; pre-repair baseline for the same three paths was 92).

## Supervisor and child-goal alignment

This residual repair preserves the supervisor-fed identity: task
`ABBY-VOICE-AUTO-026`, goal `ABBY-VOICE-G016`, P0, track `voice-scheduling`,
parent G011, dependency G015, graph depth 4, bundle
`abby-voice/audio-scheduling`, and merge family `objective/ABBY-VOICE-G016`.

No supervisor-generated todo, vector-index, graph, or task-status metadata was
manually completed or rewritten. No objective-heap child goal split is needed;
G017 continues to own content and speech-quality decisions.
