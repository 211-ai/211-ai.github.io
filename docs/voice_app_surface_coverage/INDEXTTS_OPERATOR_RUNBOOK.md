# IndexTTS operator runbook (production audio residual)

Program: `voice-app-surface-coverage-v1`  
Task residual: VAS-023 / VAS-024 Whisper

## Status

Offline **smoke fixtures** are staged and resolve exact-match:

- Pilot actions: `data/voice_app_surface_coverage/audio/stage/smoke/` (40 rows)
- Surface nav: `data/voice_app_surface_coverage/audio/stage/smoke-surface/` (36 rows)

**Production** Abby voice still requires IndexTTS (or the approved HF Space
pipeline), not synthetic fixtures.

## Preconditions

1. Human enables network + TTS Space credentials **out of band** (never argv).
2. Pause monorepo thrashing supervisors if they reset dirty trees.
3. Confirm text frames:

```bash
wc -l docs/phone_dialog_generation/action_speech_frames.jsonl \
  docs/phone_dialog_generation/surface_navigation_speech_frames.jsonl
```

## Suggested commands (operator)

Use existing monorepo tooling (paths may vary by environment):

```bash
# 1) Stage / precompute production audio for action frames
python scripts/run_abby_tts_precompute_pipeline.py   # or site-specific IndexTTS batch

# 2) Validate with Whisper adjudication
python scripts/validate_abby_regeneration_whisper.py

# 3) Refresh coverage receipts
python scripts/voice_app_surface_coverage/audit_audio_coverage.py --check
```

Update:

- `data/voice_app_surface_coverage/reports/audio-regen-batch-p0.json` → `status: completed`
- `whisper-adjudication-p0.json` → real metrics
- `audio-coverage.json` → `validated` counts
- `program-release-evidence.json` → `audio_validated_rows: true`

## Non-goals for autonomous workers

- No live HF publish
- No secrets in argv
- No silent claim of production audio readiness from smoke fixtures alone
