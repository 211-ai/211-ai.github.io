/**
 * interactions feature slice
 *
 * Owns the interaction history screen and the service interaction service.
 * Migrate from:
 *   app/InteractionsScreen.tsx
 *   services/serviceInteractionService.ts
 */

// Types — re-exported from lib once migration is complete
export type { ServiceInteraction, InteractionNote } from "./lib/types";

// Components — uncomment as screens are migrated
// export { InteractionsScreen } from './components/InteractionsScreen';
// export { InteractionTimeline } from './components/InteractionTimeline';

// Hooks — uncomment as hooks are migrated
// export { useInteractions } from './hooks/useInteractions';
