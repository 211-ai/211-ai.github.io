# Program Signoff

Program: `voice-app-surface-coverage-v1`  
Updated: `2026-08-05T19:48:08.314814+00:00`  
Landed: PR #45 → `main` (`060b63e4`)

## Ready (on main)

- Full app-surface inventory + exposure classification
- P0/P1 variant lattices and DAG expansion packs
- **Sidecar projected edges** (`surface_expansion_edges.jsonl`) with P0 floors met
- Symbolic retrieval reliability thresholds met
- Client exposure denies for never_voice / staff_only
- Offline e2e harness (surface matrix + adversarial + DAG samples)
- Speech text frames for pilot actions + P0 surface navigation
- Offline smoke audio fixtures (pilot 40 + surface 36) with exact-match resolver
- Submodule pin SHAs published for CI fetch

## Residual / operator-owned

1. **Production IndexTTS** + Whisper — `INDEXTTS_OPERATOR_RUNBOOK.md`
2. **Fold sidecar edges into** `slotted_response_dag.json` during offline rebuild window
3. **Merge voice modules into submodule `main`**, then retarget monorepo gitlinks — `SUBMODULE_PIN_POLICY.md`

Evidence: `data/voice_app_surface_coverage/reports/program-release-evidence.json`
