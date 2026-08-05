# v1 baseline import (VAS2-004)

Program: `voice-app-surface-full-coverage-v2`  
Imported: `2026-08-05T20:58:02.310605+00:00`  
Prerequisite: `voice-app-surface-coverage-v1` (completed)

## Reused artifacts

See `data/voice_app_surface_full_coverage/baseline/v1-import-receipt.json` for digests.

Key inputs:

- App surface inventory + exposure matrix (25 surfaces classified)
- DAG fold receipt (2288 surface expansion edges)
- Production IndexTTS for 76 pilot speech frames
- Program release evidence on monorepo main

## Gaps this program closes

| Area | v1 | v2 target |
| --- | --- | --- |
| Paraphrase floors | P0 200 / P1 50 | P0 **500** / P1 **150** / P2 **80** |
| Audio | Pilot 76 frames | Full speech corpus + DAG high-traffic + Whisper |
| DAG | One fold wave | Re-project lattices + re-fold + retrieval repair |
| E2E | P0 matrix | P0+P1 matrix + full never_voice adversarial |

## Policy

Do **not** delete `data/voice_app_surface_coverage/` or `docs/voice_app_surface_coverage/`.
v2 writes under `*_full_coverage*` paths.
