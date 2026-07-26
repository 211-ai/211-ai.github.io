# ABBY-VOICE-AUTO-028 Objective Validation Repair

Date: 2026-07-26
Source task: `ABBY-VOICE-AUTO-016`
Repair task: `ABBY-VOICE-AUTO-028`
Goal id: `ABBY-VOICE-G017`
Track: `ops` (retry-budget recovery for voice-quality implementation)

## Finding

Retry-budget guardrail filed AUTO-028 after two consecutive AUTO-016 proposal
gate failures (`proposal_gate_failed` / `path_outside_scope`). Both attempts
implemented audio reconciliation successfully offline, then failed admission
because they mutated `ipfs_datasets_py/ipfs_datasets_py/voice/__init__.py`,
which is outside the frozen AUTO-016 task-owned outputs:

- `ipfs_datasets_py/ipfs_datasets_py/voice/reconcile.py`
- `ipfs_datasets_py/ipfs_datasets_py/voice/audio_quality.py`
- `ipfs_datasets_py/tests/unit/voice/test_abby_voice_audio_reconcile.py`
- `data/abby_voice/agent_supervisor/discovery`
- `docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md`

## Repair

Recover the defining implementation on the frozen paths only:

| Path | Role |
| --- | --- |
| `ipfs_datasets_py/ipfs_datasets_py/voice/audio_quality.py` | `AudioQualityPolicy`, decode/acoustic, WER/CER, critical-slot fidelity, `validate_tts_asr_roundtrip` |
| `ipfs_datasets_py/ipfs_datasets_py/voice/reconcile.py` | `reconcile_voice_job_result`, disposition taxonomy, reciprocal promotion |
| `ipfs_datasets_py/tests/unit/voice/test_abby_voice_audio_reconcile.py` | offline evidence suite; imports defining modules (no package-root export dependency) |
| `data/abby_voice/agent_supervisor/discovery/2026-07-26-abby-voice-auto-016-objective-validation-repair.md` | authoritative G017 evidence map |
| `data/abby_voice/agent_supervisor/recovery_v10/objective_control/discovery/2026-07-26-abby-voice-auto-028-abby-voice-auto-016-retry-budget.md` | retry-budget finding + resolution |
| `docs/planning/ABBY_VOICE_ROUTER_OBJECTIVE_HEAP.md` | G017 evidence and repair linkage |

## Acceptance assertions

1. The retry-budget evidence file exists at the exact path required by AUTO-028
   validation.
2. The G017 offline validation command passes without editing out-of-scope
   package `__init__.py`.
3. The defining evidence terms for audio reconciliation remain discoverable on
   the authorized reconcile and audio-quality modules plus the AUTO-016 repair
   receipt.
4. Completing AUTO-028 is sufficient for the supervisor to release AUTO-016
   from strategy `blocked_tasks`.

## Validation receipt

AUTO-028 gate:

```text
test -f data/abby_voice/agent_supervisor/recovery_v10/objective_control/discovery/2026-07-26-abby-voice-auto-028-abby-voice-auto-016-retry-budget.md
```

Source-task gate re-verified by this repair:

```text
python -m pytest -q ipfs_datasets_py/tests/unit/voice/test_abby_voice_audio_reconcile.py tests/voice/test_abby_voice_safety.py
```

Result: **PASS — 30 tests on 2026-07-26** (19 audio-reconcile + 11 safety).

Protected `ABBY_VOICE_ROUTER_TODO.md` was not modified.
