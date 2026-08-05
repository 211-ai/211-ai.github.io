# Surface bindings (VAS2-012)

Program: `voice-app-surface-full-coverage-v2`  
Updated: `2026-08-05T21:06:40.142044+00:00`

## Modules

| Module | Role |
| --- | --- |
| `wallet_interface/helpers/_voice_surface_exposure.py` | Client deny gate; re-exports accelerate map |
| `wallet_interface/helpers/_voice_app_action_binding.py` | open_app_surface / open_wallet_documents invoke |
| `ipfs_accelerate_py/.../surface_exposure.py` | Normative exposure map + policy helper |

## Rules

1. UI `NAVIGATION_SURFACE_IDS` remains the full RouteId registry for tools.
2. **Voice/phone opens** additionally require exposure class in
   `voice_navigable` / `voice_actionable` via `surface_exposure_error`.
3. Binding invoke denies never_voice/staff_only without mutation.
4. Policy plane denies the same classes before execute (belt + suspenders).

## P0 openable surfaces

- `calendar`
- `check-in`
- `contacts`
- `home`
- `interactions`
- `messages`
- `register`
- `settings`
- `social-services`
- `uploads`
