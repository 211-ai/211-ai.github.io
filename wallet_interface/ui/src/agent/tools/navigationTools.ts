import type { RouteId } from "../../models/abby";
import { appRoutes, getRouteFromHash, setLocationRouteHash } from "../../app/appState";
import type { AppActionResult, AppActionRuntime, AppActionState } from "../../app/appActions";
import type { NavigateCommandInput, ReadSurfaceContextCommandInput } from "../commandSchemas";
import { getRouteLabel } from "../surfaceRegistry";
import type { SurfaceContext } from "../types";

type RouteSummaryBuilder = (state: AppActionState) => string;

export interface NavigationSurface {
  route: RouteId;
  label: string;
}

export const navigationSurfaces: NavigationSurface[] = appRoutes.map((route) => ({
  route: route.id,
  label: getRouteLabel(route.id)
}));

export const navigationRouteIds: RouteId[] = navigationSurfaces.map((surface) => surface.route);

const routeSummaries = {
  home: (state) =>
    `Home is active with ${state.uploads.length} uploads, ${state.recipients.length} recipients, and ${pendingAccessRequestCount(
      state
    )} pending access requests.`,
  register: (state) => `Registration draft is active with ${state.profile.serviceNeeds.length} service needs selected.`,
  "check-in": (state) =>
    `Check-in is configured every ${state.policy.intervalDays} days through ${state.policy.reminderChannels.length} channels.`,
  contacts: (state) => `${state.recipients.length} recipients are visible.`,
  "sharing-rules": (state) => `${state.recipients.length} recipients have sharing controls available.`,
  uploads: (state) => `${state.uploads.length} uploads are visible.`,
  "social-services": () => "Services search and public 211 guidance are active.",
  shelter: () => "Shelter resources and public 211 guidance are active.",
  "recipient-access": (state) => `${pendingAccessRequestCount(state)} pending access requests are visible.`,
  "benefits-protection": () => "Benefits protection resources and public 211 guidance are active.",
  analytics: () => "Group facts and aggregate reporting are active.",
  "proof-center": (state) => `${state.walletProofReceipts.length} proof receipts are visible.`,
  exports: (state) => `${state.exportBundleViews.length} export bundles are visible.`,
  security: () => "Security settings and wallet safety information are active.",
  audit: (state) => `${state.walletAuditEvents.length} audit events are visible.`
} satisfies Record<RouteId, RouteSummaryBuilder>;

export async function navigateAction(
  runtime: AppActionRuntime,
  input: NavigateCommandInput
): Promise<AppActionResult> {
  setLocationRouteHash(input.route);
  runtime.setActiveRoute?.(input.route);
  runtime.setMobileNavOpen?.(false);
  return {
    ok: true,
    action: "navigate",
    summary: `Opened ${getRouteLabel(input.route)}.`,
    route: input.route
  };
}

export async function readSurfaceContextAction(
  runtime: AppActionRuntime,
  input: ReadSurfaceContextCommandInput
): Promise<AppActionResult> {
  const surfaceContext = buildSafeSurfaceContext(runtime.getState(), input);
  return {
    ok: true,
    action: "read_surface_context",
    summary: surfaceContext.summary || `Read ${surfaceContext.routeLabel}.`,
    route: surfaceContext.route,
    surfaceContext
  };
}

export function buildSafeSurfaceContext(
  state: AppActionState,
  input: ReadSurfaceContextCommandInput = {}
): SurfaceContext {
  const route = input.route ?? state.activeRoute ?? getRouteFromHash();
  const includePrivateContext = Boolean(input.includePrivateContext && state.privateContextAllowed);
  const visibleRecordIds = getVisibleRecordIds(route, state);
  const visibleServiceDocIds = isServiceRoute(route) ? [] : undefined;

  return {
    route,
    routeLabel: getRouteLabel(route),
    capturedAt: new Date().toISOString(),
    visibleRecordIds,
    visibleServiceDocIds,
    walletUnlocked: state.walletUnlocked ?? true,
    privateContextAllowed: includePrivateContext,
    permissionLevel: includePrivateContext ? "wallet_private" : "app_context",
    summary: summarizeRouteState(route, state),
    metadata: includePrivateContext ? privateSurfaceMetadata(route, state) : publicSurfaceMetadata(route, state)
  };
}

export function summarizeRouteState(route: RouteId, state: AppActionState): string {
  return routeSummaries[route](state);
}

export function canNavigateToRoute(route: RouteId): boolean {
  return navigationRouteIds.includes(route);
}

function getVisibleRecordIds(route: RouteId, state: AppActionState): string[] | undefined {
  if (!routeHasVisibleWalletRecords(route)) {
    return undefined;
  }
  return state.uploads.map((upload) => upload.recordId || upload.id);
}

function publicSurfaceMetadata(route: RouteId, state: AppActionState): Record<string, unknown> {
  return {
    route,
    routeLabel: getRouteLabel(route),
    uploadCount: state.uploads.length,
    recipientCount: state.recipients.length,
    pendingAccessRequestCount: pendingAccessRequestCount(state),
    proofCount: state.walletProofReceipts.length,
    exportBundleCount: state.exportBundleViews.length,
    auditEventCount: state.walletAuditEvents.length,
    ...routePublicMetadata(route, state)
  };
}

function privateSurfaceMetadata(route: RouteId, state: AppActionState): Record<string, unknown> {
  return {
    ...publicSurfaceMetadata(route, state),
    profile: {
      preferredName: state.profile.preferredName,
      currentLocation: state.profile.currentLocation,
      serviceNeeds: state.profile.serviceNeeds,
      preferredCheckInChannels: state.profile.preferredCheckInChannels
    },
    policy: state.policy,
    recipients: state.recipients.map((recipient) => ({
      id: recipient.id,
      displayName: recipient.displayName,
      type: recipient.type,
      allowedScopes: recipient.allowedScopes
    }))
  };
}

function routePublicMetadata(route: RouteId, state: AppActionState): Record<string, unknown> {
  switch (route) {
    case "register":
      return {
        selectedServiceNeedCount: state.profile.serviceNeeds.length,
        preferredCheckInChannelCount: state.profile.preferredCheckInChannels.length
      };
    case "check-in":
      return {
        intervalDays: state.policy.intervalDays,
        reminderChannelCount: state.policy.reminderChannels.length,
        escalationEnabled: state.policy.escalationEnabled
      };
    case "contacts":
    case "sharing-rules":
      return {
        verifiedRecipientCount: state.recipients.filter((recipient) => recipient.verified).length
      };
    case "uploads":
      return {
        storedUploadCount: state.uploads.filter((upload) => upload.status === "stored").length,
        sharedUploadCount: state.uploads.filter((upload) => upload.shared).length
      };
    case "recipient-access":
      return {
        approvedAccessRequestCount: state.accessRequests.filter((request) => request.status === "approved").length,
        visibleAccessRequestIds: state.accessRequests.map((request) => request.id)
      };
    case "proof-center":
      return {
        verifiedProofCount: state.walletProofReceipts.filter((proof) => proof.verificationStatus === "verified").length,
        visibleProofReceiptIds: state.walletProofReceipts.map((proof) => proof.id)
      };
    case "exports":
      return {
        verifiedExportBundleCount: state.exportBundleViews.filter((bundle) => bundle.verificationOk).length,
        visibleExportBundleIds: state.exportBundleViews.map((bundle) => bundle.bundleId || bundle.id)
      };
    default:
      return {};
  }
}

function isServiceRoute(route: RouteId): boolean {
  return route === "social-services" || route === "shelter" || route === "benefits-protection";
}

function routeHasVisibleWalletRecords(route: RouteId): boolean {
  return route === "uploads";
}

function pendingAccessRequestCount(state: AppActionState): number {
  return state.accessRequests.filter((request) => request.status === "pending").length;
}
