/**
 * shared/lib — cross-cutting utilities and infrastructure helpers
 *
 * These utilities must not import from any feature slice in ../features/.
 * Migrate from ../lib/, ../services/filecoinStorage.ts, etc.
 */

// Migrated canonical utilities
export * from "./runtimeConfig";
export * from "./localization";
export * from "./backendDetection";
export * from "./warningSuppressionUtils";
export * from "./publicEndpointPolicy";
