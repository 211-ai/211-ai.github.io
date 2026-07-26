# ABBY-VOICE-AUTO-015 Objective Validation Repair

Date: 2026-07-26
Goal id: `ABBY-VOICE-G016`
Task id: `ABBY-VOICE-AUTO-015`
Implementation status: validated; authoritative daemon completion pending

## Scope and evidence

This repair closes the four evidence gaps in
`2026-07-25-abby-voice-auto-015-objective-gap-7d9fb03c0236.md` within the
task's frozen seven-path authority.

- **Priority-aware claims and recovery:** `p2p_tasks/task_queue.py` migrates
  legacy DuckDB queues in place; persists priority, attempt, maximum-attempt,
  next-attempt, lease, heartbeat, and idempotency fields; performs atomic
  submit-once and priority/FIFO microbatch claims; renews owner leases; recovers
  expired claims; applies retry backoff; and rejects stale-owner completion.
- **Audio capability constraints:** `p2p_tasks/capability_registry.py` matches
  canonical voice jobs against provider, model, voice, codec, locale, device,
  memory, and artifact-access advertisements while retaining permissive legacy
  text behavior. `p2p_tasks/orchestrator.py` releases an already claimed remote
  audio task when the selected peer does not satisfy those requirements.
- **Provider batch compatibility:** `agent_supervisor/provider_batch_scheduler.py`
  adds voice, locale, reference SHA-256, codec, sample rate, channels, and
  tenant policy to the existing provider/route/model/operation/context/policy/
  generation compatibility identity. IndexTTS and Whisper aliases stay at one
  physical member per provider call; existing single-flight, cancellation,
  integrity-receipt, sibling-isolation, and provider-backpressure behavior is
  preserved.
- **Resource and provider saturation:** the authorized
  `test/test_voice_job_recovery.py` now asserts CPU, RAM, disk, and GPU
  saturation against the existing `ResourceScheduler`, as well as every new
  audio compatibility dimension, batch-size-one policy, capability rejection,
  and safe orchestrator release. Existing provider/resource suites continue to
  assert provider concurrency, quota/token reservations, retry-after
  backpressure, single-flight receipts, and sibling-provider progress.

The repair intentionally does not modify `resource_scheduler.py`,
`p2p_tasks/client.py`, `p2p_tasks/service.py`, `p2p_tasks/worker.py`, or the
four API test modules from the rejected attempt because those paths are outside
the frozen task authority. Legacy callers that omit `worker_id` retain their
existing completion behavior; owner-aware callers receive stale-completion
protection directly from `TaskQueue.complete`.

## Validation receipt

Executed from the `ipfs_accelerate_py` submodule:

```text
python -m pytest -q test/test_voice_job_recovery.py test/api/test_agent_supervisor_provider_batch_scheduler.py test/api/test_agent_supervisor_resource_scheduler.py
```

Result: **PASS — 90 tests on 2026-07-26.**

Additional integration validation:

```text
python -m pytest -q test/api/test_peer_capability_registry.py test/api/test_task_orchestrator_capability_routing.py test/api/test_task_worker_generic_heartbeat.py
```

Result: **PASS — 3 tests on 2026-07-26.**

The rejected proposal contained 13 nested file changes and measured 2,049,763
materialized bytes against a 2,000,000-byte limit. This repair retains only the
five authorized nested files plus this discovery receipt and the objective-heap
evidence link. The protected source TODO was not modified.

## Objective and backlog boundary

No smaller child goal is needed for the accepted execution-control boundary:
queue recovery, detailed capability admission, provider compatibility, and
saturation backpressure are now executable and directly asserted. The
objective heap remains `active` until the implementation daemon performs its
authoritative proposal gate, merge, and backlog transition.
