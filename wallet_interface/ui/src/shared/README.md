# Shared UI Primitives and Utilities

This directory contains domain-agnostic UI primitives and utility modules that can be used across any feature slice without creating coupling between slices.

## `components/`

UI primitives and cross-feature panels with no domain coupling. Components here must not import from any feature slice in `../features/`.

**Contents:** `ui.tsx` (design-system primitives), `InteractionTimeline`, `SavedServicesPanel`, `ServicePlanSharingPanel`, `ServiceProvenancePanel`, `ServiceQuickActions`, `WorkerServicePlanView`, `WorldIdVerificationPanel`.

Old paths under `../components/agent/`, `../components/services/`, and `../components/ui.tsx` are backward-compatibility re-export stubs.

## `lib/`

Cross-cutting utilities and infrastructure helpers shared across feature slices.

**Contents:**
- `runtimeConfig.ts` — runtime API endpoint and feature-flag config
- `localization.ts` — locale detection and i18n helpers
- `backendDetection.ts` — backend availability detection
- `publicEndpointPolicy.ts` — public vs. authenticated endpoint policy
- `warningSuppressionUtils.ts` — dev-mode console warning suppression

Old paths under `../lib/runtimeConfig.ts`, `../lib/localization.ts`, `../lib/backendDetection.ts`, `../lib/publicEndpointPolicy.ts`, and `../lib/warningSuppressionUtils.ts` are backward-compatibility re-export stubs.

## Migration status

Shared utilities and components have been migrated from `../lib/`, `../services/`, and `../components/`. All original paths are backward-compatibility re-export stubs. New shared utilities should be added here.
