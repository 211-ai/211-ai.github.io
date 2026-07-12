/**
 * service-navigation feature slice
 *
 * Owns service search, service detail, service plan, and interaction list screens.
 * Migrate from:
 *   app/screens/HomeScreen.tsx
 *   app/screens/SocialServicesScreen.tsx
 *   app/screens/ShelterScreen.tsx
 *   app/screens/BenefitsProtectionScreen.tsx
 *   app/screens/CheckInScreen.tsx
 *   app/screens/ServicePlanScreen.tsx
 *   app/screens/ServiceDetailScreen.tsx
 *   services/serviceActionService.ts
 *   services/serviceInteractionService.ts
 *   services/graphRagService.ts
 */

// Types — re-exported from lib once migration is complete
export type { ServiceDirectoryEntry, ServiceSearchParams } from "./lib/types";

// Components — uncomment as screens are migrated
// export { SocialServicesScreen } from './components/SocialServicesScreen';
// export { ServiceDetailScreen } from './components/ServiceDetailScreen';
// export { ServicePlanScreen } from './components/ServicePlanScreen';

// Hooks — uncomment as hooks are migrated
// export { useServiceSearch } from './hooks/useServiceSearch';
// export { useServicePlan } from './hooks/useServicePlan';
