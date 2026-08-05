# Offline audio stage (VAS-022)

Program: `voice-app-surface-coverage-v1`

Use the existing action-audio smoke stager:

```bash
python scripts/stage_abby_action_audio.py --smoke \
  --stage-root data/voice_app_surface_coverage/audio/stage/smoke
```

Surface navigation frames in `docs/phone_dialog_generation/surface_navigation_speech_frames.jsonl`
are marked `generate_required` until IndexTTS batch (VAS-023) or smoke stage extension.

Generated: `2026-08-05T18:31:00.321152+00:00`
