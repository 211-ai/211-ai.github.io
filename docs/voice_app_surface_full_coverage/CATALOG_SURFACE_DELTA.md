# Catalog surface delta (VAS2-010)

Program: `voice-app-surface-full-coverage-v2`  
Updated: `2026-08-05T21:06:40.142044+00:00`

## Summary

Pilot catalog `211ai-pilot-v1` version **1.1** adds surface-gate metadata on
navigation descriptors and exports a **surface × logical-action matrix**.
No new executable locators. Logical action set unchanged (10 pilot actions).

## Metadata additions

| Logical action | New metadata |
| --- | --- |
| `open_app_surface` | `surface_gate=voice_navigable_or_voice_actionable`, `surface_arg=surface_id` |
| `open_wallet_documents` | `surface_gate=voice_actionable_uploads`, `default_surface_id=uploads` |

## Client-open surfaces (voice)

- `calendar` → open_app_surface, read_calendar, create_calendar_reminder
- `check-in` → open_app_surface
- `contacts` → open_app_surface
- `home` → open_app_surface
- `interactions` → open_app_surface
- `messages` → open_app_surface, read_provider_messages, leave_provider_message
- `register` → open_app_surface
- `settings` → open_app_surface
- `social-services` → open_app_surface, open_service_detail, schedule_service_callback
- `uploads` → open_app_surface, open_wallet_documents

## Receipt

`data/voice_app_surface_full_coverage/catalog/surface-catalog-delta.json`
