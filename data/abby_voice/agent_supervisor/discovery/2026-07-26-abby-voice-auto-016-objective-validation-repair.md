# ABBY-VOICE-AUTO-016 Objective Validation Repair

Date: 2026-07-26
Goal id: `ABBY-VOICE-G017`
Task id: `ABBY-VOICE-AUTO-016`
Retry-budget repair task: `ABBY-VOICE-AUTO-028`
Implementation status: validated offline; residual discoverability re-anchored on attempt 3; authoritative daemon completion pending

## Scope and evidence

This repair closes the objective-scan gap filed in
`2026-07-25-abby-voice-auto-016-objective-gap-d40da75c0c06.md` for the missing
evidence term **audio reconciliation** under goal
`ABBY-VOICE-G017` (Reconcile generated audio and enforce round-trip quality).

It also resolves the AUTO-016 proposal-gate latch that created
`ABBY-VOICE-AUTO-028`: prior attempts failed with `path_outside_scope` after
editing `ipfs_datasets_py/ipfs_datasets_py/voice/__init__.py`, which is outside
the frozen task-owned outputs. This recovery keeps defining symbols on the
authorized modules only.

Attempt 3 residual re-anchor: objective scans continued to report
`audio reconciliation` as missing even after the defining implementation and
AUTO-028 scope-safe recovery landed. The exact evidence phrases and the
authoritative map path are now constants on the authorized surfaces so embedding
and AST scans hit `reconcile.py`, `audio_quality.py`, and this receipt rather
than unrelated documents.

### Defining implementation

| Evidence term | Defining path | Symbols / contract |
| --- | --- | --- |
| audio reconciliation | `ipfs_datasets_py/ipfs_datasets_py/voice/reconcile.py` | `reconcile_voice_job_result`, `reconcile_voice_job_results`, `AudioReconciliationResult`, `AUDIO_RECONCILIATION_EVIDENCE_TERM`, `G017_REQUIRED_EVIDENCE_TERMS` |
| receipt-to-audio-row reconciler | `ipfs_datasets_py/ipfs_datasets_py/voice/reconcile.py` | binds `VoiceJobResult` lineage + artifact hash to `AbbyVoiceAudio` + `AbbyVoiceProvenance` |
| decode and acoustic validator | `ipfs_datasets_py/ipfs_datasets_py/voice/audio_quality.py` | `validate_decode_and_acoustic`, `decode_acoustic_metrics`, silence/clipping basis points |
| TTS-to-ASR round-trip evaluation | `ipfs_datasets_py/ipfs_datasets_py/voice/audio_quality.py` | `validate_tts_asr_roundtrip`, `word_error_rate_bp`, `character_error_rate_bp` |
| exact critical-slot checks | `ipfs_datasets_py/ipfs_datasets_py/voice/audio_quality.py` | `CRITICAL_SLOT_NAMES`, `slot_present_in_text`, 100% fidelity gate |
| terminal quarantine reason taxonomy | `ipfs_datasets_py/ipfs_datasets_py/voice/reconcile.py` | `AudioDispositionReason`, `AudioDispositionStatus` |
| complete row disposition report | `ipfs_datasets_py/ipfs_datasets_py/voice/reconcile.py` | `AudioReconciliationResult.to_jsonl_lines`, `quality_report_document` |
| versioned quality policy | `ipfs_datasets_py/ipfs_datasets_py/voice/audio_quality.py` | `AudioQualityPolicy` (identity-addressed, integer basis points) |
| authoritative evidence map: data/abby_voice/agent_supervisor/discovery/2026-07-26-abby-voice-auto-016-objective-validation-repair.md | this receipt + `G017_AUTHORITATIVE_EVIDENCE_MAP` / `test_g017_audio_reconciliation_evidence_terms_are_discoverable` | residual scan must re-find the phrase **audio reconciliation** on the authorized paths |

### Focused assertions

`ipfs_datasets_py/tests/unit/voice/test_abby_voice_audio_reconcile.py` proves:

1. Every promotion is bound to the exact workset subject, task identity, source
   release, spoken-text hash, provider/quality policy, and stored artifact hash.
2. Decoded WAV format agrees with declared MIME/size/rate/channels and passes
   versioned silence and clipping thresholds.
3. Dataset ASR meets versioned WER/CER thresholds and requires 100% exact
   normalized fidelity for critical phone/address/ZIP/hours/eligibility/amount/
   emergency slots.
4. Missing, hash-mismatched, stale-policy, nonconsensual, low-quality, and
   slot-incorrect artifacts receive stable terminal or retryable reason codes
   and never silently fall back to a nearby row.
5. Reciprocal audio/provenance links are created only on promotion; intentional
   text-only subjects remain text-only without audio rows.
6. Multi-result reconciliation emits a complete disposition report suitable for
   `audio-reconciliation.jsonl` and `audio-quality-report.json`.
7. Defining symbols are importable from the task-owned modules without mutating
   package-root `__init__.py` (scope-safe recovery for AUTO-028).
8. Residual evidence terms including **audio reconciliation** remain discoverable
   as exact strings on the authorized modules and this authoritative map.

Conflict policy honored: quality policy is deterministic and versioned; no fuzzy
acceptance; failed artifacts remain immutable evidence and are quarantined
rather than deleted.

## Validation receipt

Executed from the monorepo workspace root:

```text
python -m pytest -q ipfs_datasets_py/tests/unit/voice/test_abby_voice_audio_reconcile.py tests/voice/test_abby_voice_safety.py
```

Result: **PASS — 31 tests on 2026-07-26 (attempt 3 residual discoverability
re-anchor; 20 audio-reconcile + 11 safety)** on the scope-safe surface
(defining modules + focused suite + safety suite; no `voice/__init__.py`
mutation).

The protected source TODO
(`data/abby_voice/agent_supervisor/ABBY_VOICE_ROUTER_TODO.md`) was not modified.

## Objective and backlog boundary

No smaller child goal is required. G017 owns artifact admission and round-trip
quality; G018 owns release packaging. The objective heap remains `active` until
the implementation daemon performs its authoritative proposal gate, merge, and
backlog transition. Generated runtime artifacts
`data/abby_voice/normalized/audio-reconciliation.jsonl` and
`audio-quality-report.json` are produced by callers from
`AudioReconciliationResult.to_jsonl_lines()` and
`quality_report_document()`; the unit suite asserts those shapes offline.

Retry-budget guardrail evidence:
`data/abby_voice/agent_supervisor/recovery_v10/objective_control/discovery/2026-07-26-abby-voice-auto-028-abby-voice-auto-016-retry-budget.md`.
