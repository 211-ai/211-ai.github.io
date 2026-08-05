# Surface Bindings (VAS-010)

Program: `voice-app-surface-coverage-v1`  
Module: `wallet_interface/helpers/_voice_app_action_binding.py`

## Allowlist

`NAVIGATION_SURFACE_IDS` must stay in lockstep with UI `RouteId` set (25
surfaces). Audit: `scripts/voice_app_surface_coverage/audit_app_surface.py`.

## Aliases (navigationTools parity)

Natural phrases resolve via `resolve_navigation_surface` / `_SURFACE_ALIASES`:

| Surface | Example aliases |
| --- | --- |
| `calendar` | appointments, schedule |
| `uploads` | wallet, documents, files |
| `messages` | inbox, notifications |
| `home` | dashboard, today |
| `social-services` | (label: Services) |
| `check-in` | reminder, checkins |

## Exposure gate

`surface_exposure_error(surface_id, channel=..., role=...)` denies:

- `never_voice` surfaces on client channels
- `staff_only` surfaces on client channels
- `voice_read_only` surface **opens** from voice/phone

## Logical actions

| Logical action | Surface resolution |
| --- | --- |
| `open_app_surface` | `surface_id` / route / alias → allowlist + exposure |
| `open_wallet_documents` | always `uploads` |

## Validation

```bash
python -m pytest -q wallet_interface/tests/test_voice_app_action_binding.py \
  wallet_interface/tests/test_voice_app_action_binding_surfaces.py
```
