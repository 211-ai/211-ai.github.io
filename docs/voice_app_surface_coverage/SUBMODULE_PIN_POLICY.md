# Submodule pin policy (voice-app-surface-coverage residual)

Program: `voice-app-surface-coverage-v1`  
Updated: `2026-08-05T19:59:43.142356+00:00`

## Current monorepo pins

| Submodule | Working pin | Policy |
| --- | --- | --- |
| `ipfs_accelerate_py` | `2fdba70ed` | matches `origin/main` (PR #128 merged) |
| `ipfs_datasets_py` | `e6049b644` | matches `origin/main` (PR #1246 merged) |
| `ipfs_kit_py` | `80afdad2` | matches `origin/main` |

These SHAs include **voice-action** modules required by the monorepo
(`action_runtime`, `voice/action_links`, `voice/action_retrieval`).

## Integration path (completed 2026-08-05)

1. Merged voice-action commits into each submodule's `main` (datasets #1246, accelerate #128).
2. Fast-forwarded monorepo gitlinks to those tips.
3. Re-ran `scripts/voice_app_surface_coverage/record_submodule_pins.py --write --check`.
4. Temporary `ci/monorepo-pin-*` branches may be deleted once CI is green on main pins.

## Receipt

`data/voice_app_surface_coverage/baseline/submodule-pins.json`
