import type { RouteId } from "../../models/abby";
import { appRoutes, getRouteFromHash, setLocationRouteHash } from "../../app/appState";
import type { AppActionResult, AppActionRuntime, AppActionState } from "../../app/appActions";
import type { NavigateCommandInput, ReadSurfaceContextCommandInput } from "../commandSchemas";
import { getRouteLabel, listContextProvidersForSurface } from "../surfaceRegistry";
import type { SurfaceContext } from "../types";
import { hasPermissionLevel } from "../types";

type RouteSummaryBuilder = (state: AppActionState) => string;

export interface NavigationSurface {
  route: RouteId;
  label: string;
  aliases: string[];
}

export const navigationSurfaces: NavigationSurface[] = appRoutes.map((route) => ({
  route: route.id,
  label: getRouteLabel(route.id),
  aliases: buildRouteAliases(route.id, route.label)
}));

export const navigationRouteIds: RouteId[] = navigationSurfaces.map((surface) => surface.route);
const navigationRouteIdSet = new Set<RouteId>(navigationRouteIds);

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
  if (!canNavigateToRoute(input.route)) {
    return {
      ok: false,
      action: "navigate",
      errorCode: "route_not_found",
      message: `Route ${String(input.route)} is not available.`
    };
  }

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
  const route = resolveSurfaceRoute(state, input);
  const walletUnlocked = state.walletUnlocked ?? true;
  const includePrivateContext = canReadPrivateSurfaceContext(route, state, input, walletUnlocked);
  const visibleRecordIds = includePrivateContext ? getVisibleRecordIds(route, state) : undefined;
  const visibleServiceDocIds = getVisibleServiceDocIds(route);

  return {
    route,
    routeLabel: getRouteLabel(route),
    capturedAt: new Date().toISOString(),
    visibleRecordIds,
    visibleServiceDocIds,
    walletUnlocked,
    privateContextAllowed: includePrivateContext,
    permissionLevel: includePrivateContext ? "wallet_private" : "app_context",
    summary: summarizeRouteState(route, state),
    metadata: includePrivateContext ? privateSurfaceMetadata(route, state) : publicSurfaceMetadata(route, state)
  };
}

export function summarizeRouteState(route: RouteId, state: AppActionState): string {
  return routeSummaries[route](state);
}

export function canNavigateToRoute(route: unknown): route is RouteId {
  return navigationRouteIdSet.has(route as RouteId);
}

export function resolveNavigationRoute(input: string): RouteId | undefined {
  const normalized = normalizeRouteText(input);
  if (!normalized) return undefined;
  return navigationSurfaces.find((surface) =>
    surface.aliases.some((alias) => normalizeRouteText(alias) === normalized)
  )?.route;
}

export async function summarizeCurrentScreenAction(runtime: AppActionRuntime): Promise<AppActionResult> {
  return readSurfaceContextAction(runtime, {});
}

function buildRouteAliases(route: RouteId, appLabel: string): string[] {
  const label = getRouteLabel(route);
  return uniqueStrings([
    route,
    route.replace(/-/g, " "),
    label,
    appLabel,
    appLabel.toLowerCase(),
    label.toLowerCase()
  ]);
}

function normalizeRouteText(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ");
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
    activeRoute: state.activeRoute,
    uploadCount: state.uploads.length,
    recipientCount: state.recipients.length,
    pendingAccessRequestCount: pendingAccessRequestCount(state),
    activeGrantCount: state.grantReceipts.filter((receipt) => receipt.status === "active").length,
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
    })),
    uploads: state.uploads.map((upload) => ({
      id: upload.id,
      recordId: upload.recordId,
      category: upload.category,
      sensitivity: upload.sensitivity,
      status: upload.status,
      shared: upload.shared
    })),
    ...privateRouteMetadata(route, state)
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
        verifiedRecipientCount: state.recipients.filter((recipient) => recipient.verified).length,
        recipientTypeCounts: countBy(state.recipients.map((recipient) => recipient.type))
      };
    case "uploads":
      return {
        storedUploadCount: state.uploads.filter((upload) => upload.status === "stored").length,
        sharedUploadCount: state.uploads.filter((upload) => upload.shared).length,
        uploadCategoryCounts: countBy(state.uploads.map((upload) => upload.category)),
        uploadSensitivityCounts: countBy(state.uploads.map((upload) => upload.sensitivity))
      };
    case "recipient-access":
      return {
        approvedAccessRequestCount: state.accessRequests.filter((request) => request.status === "approved").length,
        rejectedAccessRequestCount: state.accessRequests.filter((request) => request.status === "rejected").length
      };
    case "analytics":
      return {
        activeGrantCount: state.grantReceipts.filter((receipt) => receipt.status === "active").length
      };
    case "proof-center":
      return {
        verifiedProofCount: state.walletProofReceipts.filter((proof) => proof.verificationStatus === "verified").length,
        simulatedProofCount: state.walletProofReceipts.filter((proof) => proof.simulated).length
      };
    case "exports":
      return {
        verifiedExportBundleCount: state.exportBundleViews.filter((bundle) => bundle.verificationOk).length
      };
    default:
      return {};
  }
}

function privateRouteMetadata(route: RouteId, state: AppActionState): Record<string, unknown> {
  switch (route) {
    case "recipient-access":
      return {
        visibleAccessRequestIds: state.accessRequests.map((request) => request.id)
      };
    case "proof-center":
      return {
        visibleProofReceiptIds: state.walletProofReceipts.map((proof) => proof.id)
      };
    case "exports":
      return {
        visibleExportBundleIds: state.exportBundleViews.map((bundle) => bundle.bundleId || bundle.id)
      };
    default:
      return {};
  }
}

function resolveSurfaceRoute(state: AppActionState, input: ReadSurfaceContextCommandInput): RouteId {
  if (input.route && canNavigateToRoute(input.route)) {
    return input.route;
  }
  if (canNavigateToRoute(state.activeRoute)) {
    return state.activeRoute;
  }
  const hashRoute = getRouteFromHash();
  return canNavigateToRoute(hashRoute) ? hashRoute : "home";
}

function getVisibleServiceDocIds(route: RouteId): string[] | undefined {
  return isServiceRoute(route) ? [] : undefined;
}

function isServiceRoute(route: RouteId): boolean {
  return route === "social-services" || route === "shelter" || route === "benefits-protection";
}

function routeHasVisibleWalletRecords(route: RouteId): boolean {
  return route === "uploads";
}

function canReadPrivateSurfaceContext(
  route: RouteId,
  state: AppActionState,
  input: ReadSurfaceContextCommandInput,
  walletUnlocked: boolean
): boolean {
  if (!input.includePrivateContext || !state.privateContextAllowed || !walletUnlocked) {
    return false;
  }
  if (!hasPermissionLevel(state.permissionLevel ?? "wallet_write", "wallet_private")) {
    return false;
  }
  return listContextProvidersForSurface(route, "wallet_private").some(
    (provider) => provider.permissionLevel === "wallet_private"
  );
}

function pendingAccessRequestCount(state: AppActionState): number {
  return state.accessRequests.filter((request) => request.status === "pending").length;
}

function countBy(values: string[]): Record<string, number> {
  return values.reduce<Record<string, number>>((counts, value) => {
    counts[value] = (counts[value] ?? 0) + 1;
    return counts;
  }, {});
}

function uniqueStrings(values: string[]): string[] {
  return Array.from(new Set(values.map((value) => value.trim()).filter(Boolean)));
}
