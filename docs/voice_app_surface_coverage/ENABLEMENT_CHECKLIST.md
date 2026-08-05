# Enablement Checklist

Program: `voice-app-surface-coverage-v1`  
Generated: `2026-08-05T18:31:00.321152+00:00`

| # | Gate | Evidence |
| --- | --- | --- |
| 1 | Plan preflight | `python scripts/validate_voice_app_surface_coverage_plan.py` |
| 2 | Submodule pins | `data/voice_app_surface_coverage/baseline/submodule-pins.json` |
| 3 | Exposure matrix 100% | `voice-exposure-matrix.json` |
| 4 | P0 density floors | `reports/dag-density-full.json` |
| 5 | Retrieval thresholds | `reports/retrieval-reliability.json` |
| 6 | Speech frames (text) | `action_speech_frames.jsonl` + `surface_navigation_speech_frames.jsonl` |
| 7 | Audio regen | operator gate VAS-023 (`audio-regen-batch-p0.json`) |
| 8 | Offline e2e | `pytest tests/e2e/voice_app_surface_coverage/` |
| 9 | Product flags | `WALLET_VOICE_UNIFIED_ROUTER_ENABLED`, `WALLET_VOICE_ACTION_EXECUTE_ENABLED` (human only) |
| 10 | Supervisors | pause VOICE-ACTION thrash when editing monorepo tracked files |
