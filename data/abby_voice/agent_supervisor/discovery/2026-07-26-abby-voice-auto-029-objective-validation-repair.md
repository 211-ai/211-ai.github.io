# ABBY-VOICE-AUTO-029 Objective Validation Repair

Date: 2026-07-26
Source gap fingerprint: `0bd1bac1fa8cd58eddcd855c69d5dcc6c8984924`
Goal id: `ABBY-VOICE-G016`
Task id: `ABBY-VOICE-AUTO-029`
Goal title: Add idempotent recovery resource admission and provider batching
Objective heap: `docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md`
Priority: P0
Track: `voice-scheduling`
Parents: `ABBY-VOICE-G011`
Dependencies: `ABBY-VOICE-G015`
Graph depth: 4
Bundle: `abby-voice/audio-scheduling`
Work scope: residual scan-closure discoverability for an already implemented boundary

## Finding

Objective scan `2026-07-26-abby-voice-auto-029-objective-gap-0bd1bac1fa8c.md`
reported one missing evidence term for G016 even though AUTO-015 implemented
the execution-control boundary and AUTO-026 already repaired residual-term
discoverability on the frozen paths:

- residual scan closure: data/abby_voice/agent_supervisor/discovery/2026-07-26-abby-voice-auto-026-objective-validation-repair.md

The scan already found the authoritative AUTO-015 map and the individual
residual terms on `test_voice_job_recovery.py`, but it did not re-find the
AUTO-026 residual-scan-closure receipt as an exact, authorized evidence term.

This repair does **not** invent a second scheduler, split G016, or rewrite
queue/provider semantics. It anchors residual scan closure of the AUTO-026
receipt as exact discoverable evidence on the same frozen validation surface,
and reaffirms that implementation authority remains:

`authoritative evidence map: data/abby_voice/agent_supervisor/discovery/2026-07-26-abby-voice-auto-015-objective-validation-repair.md`

with residual-term inventory remaining:

`residual scan closure: data/abby_voice/agent_supervisor/discovery/2026-07-26-abby-voice-auto-026-objective-validation-repair.md`

## Repaired residual evidence map

| Required evidence | Authoritative repository evidence | Validation rule |
| --- | --- | --- |
| residual scan closure: data/abby_voice/agent_supervisor/discovery/2026-07-26-abby-voice-auto-026-objective-validation-repair.md | Exact string and file-existence checks in `ipfs_accelerate_py/test/test_voice_job_recovery.py` (`G016_RESIDUAL_SCAN_CLOSURE`, `G016_REQUIRED_EVIDENCE_TERMS`, `test_g016_residual_evidence_terms_and_authoritative_map_are_recorded`, `test_g016_residual_scan_closure_receipt_is_discoverable`); AUTO-026 repair content at that path | The residual-scan-closure path remains an exact discoverable term on the authorized recovery test surface, and the AUTO-026 receipt file is present and still lists the residual terms plus the AUTO-015 authoritative map. |
| persisted attempt/backoff/lease state | Unchanged from AUTO-015 / AUTO-026 map (`task_queue.py` + recovery tests) | Already closed; reaffirmed only. |
| owner heartbeats | Unchanged from AUTO-015 / AUTO-026 map | Already closed; reaffirmed only. |
| IndexTTS/Whisper batch-size-one policy | Unchanged from AUTO-015 / AUTO-026 map | Already closed; reaffirmed only. |
| existing sibling isolation and single-flight receipts | Unchanged from AUTO-015 / AUTO-026 map | Already closed; reaffirmed only. |
| existing `ResourceScheduler` CPU/RAM/disk/GPU/provider backpressure assertions | Unchanged from AUTO-015 / AUTO-026 map | Already closed; reaffirmed only. |
| authoritative evidence map: data/abby_voice/agent_supervisor/discovery/2026-07-26-abby-voice-auto-015-objective-validation-repair.md | AUTO-015 repair remains the implementation authority | AUTO-029 only closes residual-scan-closure discoverability. |

## Acceptance assertions

1. The exact residual scan-closure term for the AUTO-026 repair receipt is
   present on the authorized G016 validation surface and the receipt file
   exists.
2. The AUTO-026 residual inventory still lists the six residual terms and the
   AUTO-015 authoritative evidence map.
3. No smaller child goal is required: residual scan closure describes the same
   execution-control boundary AUTO-015 and AUTO-026 already proved.
4. The protected source TODO was not modified; backlog status remains owned by
   the implementation daemon after its validation gate.

## Validation receipt

Executed gate:

```text
python -m pytest -q ipfs_accelerate_py/test/test_voice_job_recovery.py ipfs_accelerate_py/test/api/test_agent_supervisor_provider_batch_scheduler.py ipfs_accelerate_py/test/api/test_agent_supervisor_resource_scheduler.py
```

Result: **PASS — 94 tests on 2026-07-26** (includes the residual-scan-closure
anchor added by this repair; pre-repair baseline for the same three paths was
93).

## Supervisor and child-goal alignment

This residual repair preserves the supervisor-fed identity: task
`ABBY-VOICE-AUTO-029`, goal `ABBY-VOICE-G016`, P0, track `voice-scheduling`,
parent G011, dependency G015, graph depth 4, bundle
`abby-voice/audio-scheduling`, and merge family `objective/ABBY-VOICE-G016`.

No supervisor-generated todo, vector-index, graph, or task-status metadata was
manually completed or rewritten. No objective-heap child goal split is needed;
G017 continues to own content and speech-quality decisions.
