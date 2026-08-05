# Program Signoff

Program: `voice-app-surface-coverage-v1`  
Updated: `2026-08-05T19:59:43.142356+00:00`  
Landed: PR #45 → `main` (`060b63e4`); residuals PR #46 → `main` (`3d41f0dd`)

## Ready (on main / this branch)

- Full app-surface inventory + exposure classification
- P0/P1 variant lattices and DAG expansion packs
- **Sidecar projected edges folded into** `slotted_response_dag.json` (2288 edges; see `dag-fold-receipt.json`)
- Symbolic retrieval reliability thresholds met
- Client exposure denies for never_voice / staff_only
- Offline e2e harness (surface matrix + adversarial + DAG samples)
- Speech text frames for pilot actions + P0 surface navigation
- Offline smoke audio fixtures (pilot 40 + surface 36) with exact-match resolver
- **Submodule pins match origin/main** after accelerate #128 + datasets #1246

## Residual / operator-owned

1. **Production IndexTTS** + Whisper — `INDEXTTS_OPERATOR_RUNBOOK.md` (still gated; no live TTS secrets in autonomous workers)
2. Delete temporary `ci/monorepo-pin-*` branches after CI green on new pins

Evidence: `data/voice_app_surface_coverage/reports/program-release-evidence.json`
