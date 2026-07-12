# Shared UI Primitives and Utilities

This directory contains domain-agnostic UI primitives and utility modules that can be used across any feature slice without creating coupling between slices.

## `components/`

UI primitives with no domain coupling: buttons, inputs, modals, layout components, error boundaries. These components must not import from any feature slice in `../features/`.

## `lib/`

Cross-cutting utilities, storage adapters, and infrastructure helpers:

- Storage adapters (Filecoin, Walrus) — `../services/filecoinStorage.ts`, `../services/walrusStorage.ts`
- Locale and localization helpers — `../lib/localization.ts`
- Runtime config — `../lib/runtimeConfig.ts`
- Backend detection — `../lib/backendDetection.ts`
- Worker service wrappers — `../lib/clientAudioReplyService.ts`, `../lib/clientLLMWorkerService.ts`, etc.

## Migration approach

Shared utilities are being migrated incrementally from `../lib/`, `../services/`, and `../components/`. During migration, existing files remain in their current locations. New shared utilities should be added here.
