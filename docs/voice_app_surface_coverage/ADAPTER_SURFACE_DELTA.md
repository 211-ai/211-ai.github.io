# Adapter × Surface Delta (VAS-011)

Program: `voice-app-surface-coverage-v1`

## Status

P0 exposed surfaces reuse existing offline adapters from the voice-action pilot:

| Family | Module | Surfaces / actions |
| --- | --- | --- |
| App open | `wallet_interface.helpers._voice_app_action_binding` | all `voice_navigable` / open paths |
| Wallet docs | same | `uploads` / `open_wallet_documents` |
| Calendar | `action_runtime.adapters.calendar` | `read_calendar`, `create_calendar_reminder` |
| Messaging | `action_runtime.adapters.messaging` | `read_provider_messages`, `leave_provider_message` |
| Service | `action_runtime.adapters.service_interaction` | `open_service_detail`, `schedule_service_callback` |
| Handoff | `action_runtime.adapters.human_handoff` | live agent / safety |

## New in this program

- Exposure gate before app open (`_voice_surface_exposure.py` + binding wire).
- No new network transports; workers remain fake-adapter only.

## Validation

```bash
PYTHONPATH=ipfs_accelerate_py:ipfs_datasets_py:ipfs_kit_py:. \
  python -m pytest -q wallet_interface/tests/test_voice_app_action_binding.py \
  wallet_interface/tests/test_voice_app_action_binding_surfaces.py
```
