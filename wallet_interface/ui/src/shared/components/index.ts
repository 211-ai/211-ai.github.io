/**
 * shared/components — domain-agnostic UI primitives
 *
 * These components must not import from any feature slice in ../features/.
 * Canonical home for ui.tsx primitives and cross-feature service panels.
 */

// Core UI primitives
export * from "./ui";

// Cross-feature service panels
export { InteractionTimeline } from "./InteractionTimeline";
export { SavedServicesPanel } from "./SavedServicesPanel";
export { ServicePlanSharingPanel } from "./ServicePlanSharingPanel";
export { ServiceProvenancePanel } from "./ServiceProvenancePanel";
export { ServiceQuickActions } from "./ServiceQuickActions";
export { WorkerServicePlanView } from "./WorkerServicePlanView";
export { WorldIdVerificationPanel } from "./WorldIdVerificationPanel";
