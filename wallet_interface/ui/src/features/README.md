# Feature Slices

This directory contains the feature-slice modules for the Abby UI. Each slice owns its screens, domain-specific services, and client-side state without coupling to other slices.

## Planned layout

| Slice | Current source (to migrate) | Responsibility |
| --- | --- | --- |
| `wallet/` | `app/screens/ProofCenterScreen.tsx`, `app/screens/ExportCenterScreen.tsx`, `app/screens/RecipientAccessScreen.tsx`, `services/walletApi.ts`, `services/walletProofReview.ts` | Wallet screens, wallet API client, proof review UI |
| `service-navigation/` | `app/screens/HomeScreen.tsx`, `app/screens/SocialServicesScreen.tsx`, `app/screens/ShelterScreen.tsx`, `app/screens/BenefitsProtectionScreen.tsx`, `app/screens/CheckInScreen.tsx`, `app/screens/ServicePlanScreen.tsx`, `app/screens/ServiceDetailScreen.tsx`, `services/serviceActionService.ts`, `services/serviceInteractionService.ts`, `services/graphRagService.ts` | Service search, service detail, service plan, interactions |
| `agent/` | `agent/`, `services/agentChatService.ts`, `lib/graphrag/`, workers for LLM and audio | Agent/chat flows, LLM workers, audio chat |
| `interactions/` | `app/InteractionsScreen.tsx`, `services/serviceInteractionService.ts` | Interaction history screen and service |
| `calendar/` | `app/CalendarScreen.tsx`, `lib/calendar/` | Calendar screen |

## Migration approach

Files in `../app/`, `../components/`, `../lib/`, `../services/`, `../agent/`, and `../workers/` are being migrated incrementally into this structure. During migration, existing files remain in their current locations and continue to function. New feature development should target the feature-slice structure.

See `ARCHITECTURE.md` at the repository root for the target layout.
