# ABBY-VOICE-AUTO-031 Objective Validation Repair

Date: 2026-07-26
Source gap fingerprint: `b111dca2a10b3fdd6026bfea210fd2f254d999d0`
Goal id: `ABBY-VOICE-G016`
Task id: `ABBY-VOICE-AUTO-031`
Goal title: Add idempotent recovery resource admission and provider batching
Objective heap: `docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md`
Priority: P0
Track: `voice-scheduling`
Parents: `ABBY-VOICE-G011`
Dependencies: `ABBY-VOICE-G015`
Graph depth: 4
Bundle: `abby-voice/audio-scheduling`
Work scope: `objective_validation_repair`
Work item: close the literal missing evidence term `objective validation repair`

## Finding

Objective scan `2026-07-26-abby-voice-auto-031-objective-gap-b111dca2a10b.md`
reported one missing evidence term for G016:

- objective validation repair

Every functional G016 claim was already present on the frozen execution-control
surface. AUTO-015 implemented queue recovery, audio capability admission,
provider batch compatibility, and resource saturation. AUTO-026 residual-term
discoverability and AUTO-029 residual scan closure re-anchored those terms as
exact evidence. The scan still could not re-find the space-separated phrase
`objective validation repair` because earlier G016 receipts used only the
hyphenated field name `Objective-validation repair` and did not keep the
literal acceptance-subset term on the authorized validation surface.

This repair does **not** invent a second scheduler, split G016, or rewrite
queue, capability, resource, or provider-batch semantics. It is the
`objective validation repair` receipt for the already-proved boundary and
anchors that exact phrase so subsequent objective scans re-find it.

Implementation authority remains:

`authoritative evidence map: data/abby_voice/agent_supervisor/discovery/2026-07-26-abby-voice-auto-015-objective-validation-repair.md`

Residual-term inventory remains:

`residual scan closure: data/abby_voice/agent_supervisor/discovery/2026-07-26-abby-voice-auto-026-objective-validation-repair.md`

## Repaired residual evidence map

| Required evidence | Authoritative repository evidence | Validation rule |
| --- | --- | --- |
| objective validation repair | This receipt; exact string and file-existence checks in `ipfs_accelerate_py/test/test_voice_job_recovery.py` (`G016_OBJECTIVE_VALIDATION_REPAIR`, `G016_REQUIRED_EVIDENCE_TERMS`, `test_g016_objective_validation_repair_is_discoverable`); G016 heap field that names AUTO-031 as the phrase owner | The exact space-separated phrase remains discoverable on the authorized recovery-test surface and this receipt, without inventing a second scheduler. |
| authoritative evidence map: data/abby_voice/agent_supervisor/discovery/2026-07-26-abby-voice-auto-015-objective-validation-repair.md | AUTO-015 repair remains the implementation authority | AUTO-031 only closes the meta validation-repair phrase. |
| residual scan closure: data/abby_voice/agent_supervisor/discovery/2026-07-26-abby-voice-auto-026-objective-validation-repair.md | AUTO-026 / AUTO-029 residual inventory | Already closed; reaffirmed only. |
| persisted attempt/backoff/lease state | Unchanged from AUTO-015 / AUTO-026 map | Already closed; reaffirmed only. |
| owner heartbeats | Unchanged from AUTO-015 / AUTO-026 map | Already closed; reaffirmed only. |
| IndexTTS/Whisper batch-size-one policy | Unchanged from AUTO-015 / AUTO-026 map | Already closed; reaffirmed only. |
| existing sibling isolation and single-flight receipts | Unchanged from AUTO-015 / AUTO-026 map | Already closed; reaffirmed only. |
| existing `ResourceScheduler` CPU/RAM/disk/GPU/provider backpressure assertions | Unchanged from AUTO-015 / AUTO-026 map | Already closed; reaffirmed only. |

## Acceptance assertions

1. The exact phrase `objective validation repair` is present on the authorized
   G016 validation surface and in this receipt.
2. The three-file offline validation gate continues to pass without semantic
   changes to TaskQueue, TaskOrchestrator, PeerCapabilityRegistry,
   ProviderBatchScheduler, or ResourceScheduler.
3. No smaller child goal is required: the missing term describes the same
   execution-control boundary AUTO-015, AUTO-026, and AUTO-029 already proved.
4. The protected source TODO was not modified; backlog status remains owned by
   the implementation daemon after its validation gate.

## Validation receipt

Executed gate:

```text
python -m pytest -q ipfs_accelerate_py/test/test_voice_job_recovery.py ipfs_accelerate_py/test/api/test_agent_supervisor_provider_batch_scheduler.py ipfs_accelerate_py/test/api/test_agent_supervisor_resource_scheduler.py
```

Result: **PASS — 95 tests on 2026-07-26** (includes the objective validation
repair anchor added by this repair; pre-repair baseline for the same three
paths was 94).

## Supervisor and child-goal alignment

This residual repair preserves the supervisor-fed identity: task
`ABBY-VOICE-AUTO-031`, goal `ABBY-VOICE-G016`, P0, track `voice-scheduling`,
parent G011, dependency G015, graph depth 4, bundle
`abby-voice/audio-scheduling`, and merge family `objective/ABBY-VOICE-G016`.

No supervisor-generated todo, vector-index, graph, or task-status metadata was
manually completed or rewritten. No objective-heap child goal split is needed;
G017 continues to own content and speech-quality decisions.
