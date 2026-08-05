# Catalog × Surface Delta (VAS-008)

Program: `voice-app-surface-coverage-v1`  
Catalog: `211ai-pilot-v1`

## Summary

P0 exposed surfaces are covered by the **existing** pilot logical actions.
No new descriptor IDs were required for wave-02 catalog coverage; open routes
use `open_app_surface` with an allowlisted `surface_id`, and refined tools map
as below.

## P0 surface → logical action map

| Surface | Exposure | Logical action(s) | Descriptor family |
| --- | --- | --- | --- |
| `calendar` | voice_actionable | `open_app_surface`, `read_calendar`, `create_calendar_reminder` | app + calendar |
| `messages` | voice_actionable | `open_app_surface`, `read_provider_messages`, `leave_provider_message` | app + messaging |
| `uploads` | voice_actionable | `open_wallet_documents`, `open_app_surface` | wallet + app |
| `social-services` | voice_actionable | `open_app_surface`, `open_service_detail`, `schedule_service_callback` | app + service |
| `home` | voice_navigable | `open_app_surface` | app |
| `check-in` | voice_navigable | `open_app_surface` | app |
| `contacts` | voice_navigable | `open_app_surface` | app |
| `interactions` | voice_navigable | `open_app_surface` | app |
| `settings` | voice_navigable | `open_app_surface` | app |

## Staff / never_voice

| Surface class | Policy |
| --- | --- |
| `staff_only` | Deny open on client voice/phone/chat (`surface_staff_only`) |
| `never_voice` | Deny open always on client channels (`surface_never_voice`) |
| `voice_read_only` | Deny UI open from phone/voice (`surface_voice_read_only`) |

Enforcement lives in `wallet_interface/helpers/_voice_app_action_binding.py`
(`surface_exposure_error`) in addition to catalog channel lists.

## Validation

```bash
PYTHONPATH=ipfs_accelerate_py:ipfs_datasets_py:ipfs_kit_py \
  python -m pytest -q ipfs_accelerate_py/test/test_action_catalog_211ai.py
python scripts/voice_app_surface_coverage/audit_catalog_surface_coverage.py --check
```

## Future additive deltas (not this task)

- Per-surface refined tools (check-in submit, contacts add) would need new
  descriptors with write+auth.
- Staff channel-specific descriptors for provider portal (explicit staff role).
