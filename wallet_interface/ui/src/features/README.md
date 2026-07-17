# Feature Slices

This directory contains the feature-slice modules for the Abby UI. Each slice owns its screens, domain-specific services, and client-side state without coupling to other slices.

## Completed layout

| Slice | Canonical contents | Responsibility |
| --- | --- | --- |
| `wallet/` | `components/` (10 screens), `lib/` (walletApi, walletProofReview, filecoinStorage, walrusStorage, capabilities, mockAbbyService, types) | Wallet screens, wallet API client, proof review UI, storage adapters |
| `service-navigation/` | `components/` (6 screens), `lib/` (graphRagService, serviceActionService, serviceInteractionService, backendDetectionWorkerService, clientEmbeddingWorkerService, graphrag/), `graphrag.ts` | Service search, service detail, service plan, check-in, graphRAG |
| `agent/` | `components/` (11 components), `lib/` (chatController, agentChatService, LLM/audio clients, tools/, etc.), `workers/` (5 workers) | Agent/chat flows, LLM workers, audio chat |
| `interactions/` | `components/` (InteractionsScreen, ClientMessagesScreen), `lib/types.ts` | Interaction history screen and service |
| `calendar/` | `components/CalendarScreen.tsx`, `lib/ics.ts`, `lib/types.ts` | Calendar screen and ICS export |

## Migration status

Migration from the flat `../app/screens/`, `../services/`, `../agent/`, `../workers/`, and `../lib/` directories into this feature-slice structure is **complete**. All original paths remain as backward-compatibility re-export stubs so that any remaining references continue to compile without modification.

New feature development should target this feature-slice structure directly.

See `ARCHITECTURE.md` at the repository root for the full migration record.
