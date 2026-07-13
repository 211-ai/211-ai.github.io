/**
 * service-navigation feature slice
 *
 * Owns service search, service detail, service plan, and interaction list screens.
 * Migrated from:
 *   app/screens/HomeScreen.tsx
 *   app/screens/SocialServicesScreen.tsx
 *   app/screens/ShelterScreen.tsx
 *   app/screens/BenefitsProtectionScreen.tsx
 *   app/screens/CheckInScreen.tsx
 *   app/ServicePlanScreen.tsx
 *   app/ServiceDetailScreen.tsx
 *   services/serviceActionService.ts
 *   services/serviceInteractionService.ts
 *   services/graphRagService.ts
 */

// Types
export type { ServiceDirectoryEntry, ServiceSearchParams } from "./lib/types";

// Services (canonical locations)
export * from "./lib/serviceActionService";
export * from "./lib/serviceInteractionService";
export * from "./lib/graphRagService";

// Components
export { HomeScreen } from "./components/HomeScreen";
export { SocialServicesScreen } from "./components/SocialServicesScreen";
export { ShelterScreen } from "./components/ShelterScreen";
export { CheckInScreen } from "./components/CheckInScreen";
export { ServiceDetailScreen } from "./components/ServiceDetailScreen";
export { ServicePlanScreen } from "./components/ServicePlanScreen";
export {
  getServicePlanDocIdFromHash,
  servicePlanRouteHash,
  setLocationServicePlanHash,
} from "./components/ServicePlanScreen";
