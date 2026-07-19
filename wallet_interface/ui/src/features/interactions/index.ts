/**
 * interactions feature slice
 *
 * Owns the interaction history screen and the service interaction service.
 * Migrated from:
 *   app/InteractionsScreen.tsx
 *   app/screens/ClientMessagesScreen.tsx
 */

// Types
export type { ServiceInteraction, InteractionNote } from "./lib/types";

// Components
export { InteractionsScreen } from "./components/InteractionsScreen";
export { ClientMessagesScreen } from "./components/ClientMessagesScreen";
