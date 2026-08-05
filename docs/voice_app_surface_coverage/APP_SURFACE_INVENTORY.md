# 211-AI App Surface Inventory

Program: `voice-app-surface-coverage-v1`  
Tasks: `VAS-004`, `VAS-005`  
Generated: `2026-08-05T17:33:55.895801+00:00`

## Counts

- Surfaces: **25** (primary 18, secondary 6, provider 7)
- Navigation allowlist: **25**
- Agent tool modules: **15**
- Action adapters: **5**
- Pilot logical actions: **10**

## Surfaces

| id | label | family | provider | allowlist | removed standalone |
| --- | --- | --- | --- | --- | --- |
| `analytics` | Analytics | secondary | no | yes | no |
| `audit` | Audit | extra | no | yes | no |
| `benefits-protection` | Benefits | secondary | no | yes | yes |
| `calendar` | Calendar | primary | no | yes | no |
| `check-in` | Check in | primary | no | yes | no |
| `contacts` | Contacts | primary | no | yes | no |
| `exports` | Exports | secondary | no | yes | yes |
| `home` | Home | primary | no | yes | no |
| `interactions` | Interactions | primary | no | yes | no |
| `messages` | Messages | primary | no | yes | no |
| `proof-center` | Proofs | secondary | no | yes | no |
| `provider-analytics` | Staff analytics | primary | yes | yes | no |
| `provider-cases` | Case management | primary | yes | yes | no |
| `provider-clients` | Clients served | primary | yes | yes | no |
| `provider-messages` | Client messages | primary | yes | yes | no |
| `provider-operations` | Staff operations | primary | yes | yes | no |
| `provider-proofs` | ZK certificates | primary | yes | yes | no |
| `recipient-access` | Who can see info | secondary | no | yes | yes |
| `register` | Register | primary | no | yes | no |
| `security` | Security | secondary | no | yes | yes |
| `settings` | Settings | primary | no | yes | no |
| `sharing-rules` | Sharing | primary | no | yes | yes |
| `shelter` | Overview | primary | yes | yes | no |
| `social-services` | Services | primary | no | yes | no |
| `uploads` | Wallet | primary | no | yes | no |

## Allowlist vs UI mismatches

```json
{
  "in_allowlist_not_ui": [],
  "in_route_type_not_ui_tables": [],
  "in_ui_not_allowlist": [],
  "in_ui_tables_not_route_type": []
}
```

## Pilot logical actions

- `create_calendar_reminder`
- `escalate_safety`
- `handoff_live_agent`
- `leave_provider_message`
- `open_app_surface`
- `open_service_detail`
- `open_wallet_documents`
- `read_calendar`
- `read_provider_messages`
- `schedule_service_callback`

## Agent tool modules

- `analyticsTools.ts` (4 exports) — `wallet_interface/ui/src/features/agent/lib/tools/analyticsTools.ts`
- `auditTools.ts` (3 exports) — `wallet_interface/ui/src/features/agent/lib/tools/auditTools.ts`
- `checkInTools.ts` (1 exports) — `wallet_interface/ui/src/features/agent/lib/tools/checkInTools.ts`
- `contactTools.ts` (6 exports) — `wallet_interface/ui/src/features/agent/lib/tools/contactTools.ts`
- `exportTools.ts` (2 exports) — `wallet_interface/ui/src/features/agent/lib/tools/exportTools.ts`
- `navigationTools.ts` (9 exports) — `wallet_interface/ui/src/features/agent/lib/tools/navigationTools.ts`
- `proofTools.ts` (7 exports) — `wallet_interface/ui/src/features/agent/lib/tools/proofTools.ts`
- `recipientAccessTools.ts` (6 exports) — `wallet_interface/ui/src/features/agent/lib/tools/recipientAccessTools.ts`
- `registrationTools.ts` (1 exports) — `wallet_interface/ui/src/features/agent/lib/tools/registrationTools.ts`
- `securityTools.ts` (3 exports) — `wallet_interface/ui/src/features/agent/lib/tools/securityTools.ts`
- `serviceDetailTools.ts` (5 exports) — `wallet_interface/ui/src/features/agent/lib/tools/serviceDetailTools.ts`
- `servicePlanTools.ts` (5 exports) — `wallet_interface/ui/src/features/agent/lib/tools/servicePlanTools.ts`
- `sharingRuleTools.ts` (4 exports) — `wallet_interface/ui/src/features/agent/lib/tools/sharingRuleTools.ts`
- `shelterTools.ts` (9 exports) — `wallet_interface/ui/src/features/agent/lib/tools/shelterTools.ts`
- `uploadTools.ts` (5 exports) — `wallet_interface/ui/src/features/agent/lib/tools/uploadTools.ts`
