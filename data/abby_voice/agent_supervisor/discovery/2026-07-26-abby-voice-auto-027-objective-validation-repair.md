# ABBY-VOICE-AUTO-027 Objective Validation Repair

Date: 2026-07-26
Source gap fingerprint: `6052767b43b2c92e50d60dbc947594c91bce3473`
Goal id: `ABBY-VOICE-G011`
Task id: `ABBY-VOICE-AUTO-027`
Retry-budget repair: `ABBY-VOICE-AUTO-032`
Goal title: Normalize and materialize the Abby voice dataset
Objective heap: `docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md`
Priority: P0
Track: `voice-data`
Parents: `ABBY-VOICE-G004`, `ABBY-VOICE-G005`
Graph depth: 3
Bundle: `abby-voice/dataset-materialization`
Work scope: residual objective-evidence closure for already-implemented child boundaries
Acceptance subset: deterministic audio worksets, TTS/ASR execution

## Finding

Objective scan `2026-07-26-abby-voice-auto-027-objective-gap-6052767b43b2.md`
reported two missing evidence terms for parent goal G011:

- deterministic audio worksets
- TTS/ASR execution

The scan's "present evidence" matches pointed at unrelated embedding hits
(`xaman/config.py`, legal-IR audit scripts, identity unit tests) rather than the
authorized workset planner and voice-worker surfaces.

Child ownership is already complete:

| Term | Owning goal | Authoritative map |
| --- | --- | --- |
| deterministic audio worksets | G013 | `data/abby_voice/agent_supervisor/discovery/2026-07-25-abby-voice-auto-012-objective-validation-repair.md` (residual parent re-anchor: AUTO-024) |
| TTS/ASR execution | G015 | `data/abby_voice/agent_supervisor/discovery/2026-07-26-abby-voice-auto-014-objective-validation-repair.md` |

G022 and G023 remain blocked duplicate refinements of G013 and G015.

Four AUTO-027 implementation attempts then latched the validation retry budget
with `proposal_gate_failed` (`path_outside_scope` / `command_forbidden`) by
mutating package sources, package `__init__.py`, scripts, or out-of-scope tests
outside the frozen residual surface. AUTO-032 recovers the residual obligation
without re-entering those paths.

This repair stays on the frozen AUTO-027 / AUTO-032 outputs only:

- `data/abby_voice/agent_supervisor/discovery`
- `docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md`
- `data/abby_voice/normalized/manifest.json`
- `data/abby_voice/normalized/quality-report.json`
- `data/abby_voice/normalized/quarantine.jsonl`
- `data/abby_voice/releases/release-manifest.json`
- `data/abby_voice/agent_supervisor/discovery/ABBY-VOICE-G011-completion.md`
- `data/abby_voice/agent_supervisor/recovery_v10/objective_control/discovery`

It does **not** invent a second workset planner or voice worker and does **not**
edit package sources or tests. It anchors the residual G011 acceptance-subset
terms as exact, discoverable evidence and reaffirms the child authoritative maps.

## Repaired residual evidence map

| Required evidence | Authoritative repository evidence | Validation rule |
| --- | --- | --- |
| deterministic audio worksets | G013 defining planner `VoiceAudioWorkset` / `AudioWorkManifest` in `ipfs_datasets_py/ipfs_datasets_py/voice/workset.py`; manager composition in `ipfs_datasets_py/ipfs_datasets_py/voice/dataset_manager.py`; focused suite `ipfs_datasets_py/tests/unit/voice/test_abby_voice_dataset_manager.py`; residual parent repair `data/abby_voice/agent_supervisor/discovery/2026-07-26-abby-voice-auto-024-objective-validation-repair.md`; offline fixture `data/abby_voice/normalized/manifest.json` with `evidence.deterministic_audio_worksets: true` | Workset selects only missing, corrupt, stale-policy, and explicit-revalidation subjects; full-hash identities and canonical bytes are input-order independent. |
| TTS/ASR execution | G015 voice handlers and executor in `ipfs_accelerate_py/ipfs_accelerate_py/voice_jobs/executor.py` with shared task aliases, capability parity, and offline worker suite `ipfs_accelerate_py/test/test_voice_job_worker.py`; authoritative map `data/abby_voice/agent_supervisor/discovery/2026-07-26-abby-voice-auto-014-objective-validation-repair.md`; offline fixture `data/abby_voice/normalized/manifest.json` with `evidence.tts_asr_execution: true` and `execution_receipt_count` | Jobs execute through existing voice_router providers; DuckDB/task receipts hold descriptors and digests only (no raw audio or private transcripts). |
| authoritative evidence map: data/abby_voice/agent_supervisor/discovery/2026-07-25-abby-voice-auto-012-objective-validation-repair.md | AUTO-012 G013 repair remains the workset implementation authority | AUTO-027 only closes residual parent-goal discoverability for this term. |
| authoritative evidence map: data/abby_voice/agent_supervisor/discovery/2026-07-26-abby-voice-auto-014-objective-validation-repair.md | AUTO-014 G015 repair remains the execution implementation authority | AUTO-027 only closes residual parent-goal discoverability for this term. |
| retry-budget recovery: data/abby_voice/agent_supervisor/recovery_v10/objective_control/discovery/2026-07-27-abby-voice-auto-032-abby-voice-auto-027-retry-budget.md | AUTO-032 latch + resolution | Completing AUTO-032 releases AUTO-027 from strategy `blocked_tasks`. |

## Acceptance assertions

1. Exact phrases `deterministic audio worksets` and `TTS/ASR execution` are
   present on this residual receipt, the G011 partial completion receipt, the
   G011 objective-heap residual repair linkage, and the offline materialize
   fixtures.
2. Offline G011 materialization artifacts under `data/abby_voice/normalized/`
   and `data/abby_voice/releases/` record both
   `evidence.deterministic_audio_worksets: true` and
   `evidence.tts_asr_execution: true` with a content-addressed `workset_id`
   and non-zero `execution_receipt_count` bound to the offline fixture.
3. No smaller child goal is required: G022 stays blocked as a duplicate of
   G013; G023 stays blocked as a duplicate of G015. Residual parent-term
   discoverability is the only G011 obligation closed by AUTO-027/AUTO-032 for
   this acceptance subset.
4. The protected source TODO was not modified; backlog status remains owned by
   the implementation daemon after its validation gate.
5. Remaining G011 evidence terms (audio reconciliation, deterministic release
   construction, runtime resolution, post-publication verification) continue
   to be owned by G017–G021 and are out of this residual acceptance subset.
6. No out-of-scope package, submodule, script, or test path was modified by this
   residual repair.

## Validation receipt

AUTO-032 gate:

```text
test -f data/abby_voice/agent_supervisor/recovery_v10/objective_control/discovery/2026-07-27-abby-voice-auto-032-abby-voice-auto-027-retry-budget.md
```

Source-task offline gate (re-verified by this residual repair):

```text
python -m pytest -q ipfs_datasets_py/tests/unit/voice tests/voice
python benchmarks/bench_abby_voice_router.py --offline --check
```

Result: **PASS on 2026-07-27** — 167 passed, 1 skipped; offline bench
`passed: true`. AUTO-032 file-existence gate also passes.

## Supervisor and child-goal alignment

This residual repair preserves the supervisor-fed identity: task
`ABBY-VOICE-AUTO-027`, goal `ABBY-VOICE-G011`, P0, track `voice-data`, parents
G004/G005, graph depth 3, bundle `abby-voice/dataset-materialization`, merge
family `objective/ABBY-VOICE-G011`, acceptance subset
`deterministic audio worksets, TTS/ASR execution`.

Retry-budget repair task `ABBY-VOICE-AUTO-032` owns the latch evidence at
`data/abby_voice/agent_supervisor/recovery_v10/objective_control/discovery/2026-07-27-abby-voice-auto-032-abby-voice-auto-027-retry-budget.md`
and is sufficient to release AUTO-027 from strategy `blocked_tasks`.

No supervisor-generated todo, vector-index, graph, or task-status metadata was
manually completed or rewritten. No objective-heap child goal split is needed;
G013 remains the sole owner of deterministic audio workset planning, G015 remains
the sole owner of TTS/ASR execution, and G022/G023 remain blocked duplicate
refinements.
