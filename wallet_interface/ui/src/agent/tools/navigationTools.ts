import type { AppActionResult } from "../../app/appActions";
import type { RouteId } from "../../models/abby";
import type { NavigateCommandInput, ReadSurfaceContextCommandInput } from "../commandSchemas";
import type { AgentSurfaceApi } from "../surfaceApi";
import type { SurfaceContext } from "../types";

export const NAVIGABLE_ROUTE_IDS = [
  "home",
  "register",
  "check-in",
  "contacts",
  "sharing-rules",
  "uploads",
  "social-services",
  "shelter",
  "recipient-access",
  "benefits-protection",
  "analytics",
  "proof-center",
  "exports",
  "security",
  "audit"
] as const satisfies readonly RouteId[];

export const NAVIGATION_TOOL_NAMES = ["navigate", "read_surface_context", "summarize_current_screen"] as const;
export type NavigationToolName = (typeof NAVIGATION_TOOL_NAMES)[number];

export const NAVIGATION_ROUTE_LABELS: Record<RouteId, string> = {
  home: "Home",
  register: "Register",
  "check-in": "Check in",
  contacts: "Contacts",
  "sharing-rules": "Sharing",
  uploads: "Uploads",
  "social-services": "Services",
  shelter: "Shelter",
  "recipient-access": "Who can see info",
  "benefits-protection": "Benefits",
  analytics: "Group facts",
  "proof-center": "Proofs",
  exports: "Exports",
  security: "Security",
  audit: "Audit"
};

type NavigationSurfaceApi = Pick<AgentSurfaceApi, "getContext" | "invoke">;

export interface RouteNavigationTools {
  navigate: (input: RouteId | NavigateCommandInput) => Promise<AppActionResult>;
  read_surface_context: (input?: ReadSurfaceContextCommandInput) => Promise<AppActionResult>;
  summarize_current_screen: (input?: Pick<ReadSurfaceContextCommandInput, "route">) => Promise<AppActionResult>;
  getSafeCurrentScreenSummary: () => string;
}

export function isNavigableRouteId(value: unknown): value is RouteId {
  return typeof value === "string" && NAVIGABLE_ROUTE_IDS.includes(value as RouteId);
}

export function getNavigationRouteLabel(route: RouteId): string {
  return NAVIGATION_ROUTE_LABELS[route];
}

export async function navigateToRoute(
  surfaceApi: NavigationSurfaceApi,
  input: RouteId | NavigateCommandInput
): Promise<AppActionResult> {
  const commandInput = typeof input === "string" ? { route: input } : input;
  return surfaceApi.invoke("navigate", commandInput);
}

export async function readSafeSurfaceContext(
  surfaceApi: NavigationSurfaceApi,
  input: ReadSurfaceContextCommandInput = {}
): Promise<AppActionResult> {
  return surfaceApi.invoke("read_surface_context", {
    ...input,
    includePrivateContext: false
  });
}

export async function summarizeCurrentScreen(
  surfaceApi: NavigationSurfaceApi,
  input: Pick<ReadSurfaceContextCommandInput, "route"> = {}
): Promise<AppActionResult> {
  return readSafeSurfaceContext(surfaceApi, input);
}

export function summarizeSafeSurfaceContext(context: SurfaceContext): string {
  const details = [
    context.summary,
    context.visibleRecordIds?.length ? `${context.visibleRecordIds.length} visible records` : undefined,
    context.visibleServiceDocIds?.length ? `${context.visibleServiceDocIds.length} visible services` : undefined
  ].filter((detail): detail is string => Boolean(detail));

  return details.length
    ? `${context.routeLabel}: ${details.join("; ")}.`
    : `${context.routeLabel} is active.`;
}

export function createRouteNavigationTools(surfaceApi: NavigationSurfaceApi): RouteNavigationTools {
  return {
    navigate: (input) => navigateToRoute(surfaceApi, input),
    read_surface_context: (input = {}) => readSafeSurfaceContext(surfaceApi, input),
    summarize_current_screen: (input = {}) => summarizeCurrentScreen(surfaceApi, input),
    getSafeCurrentScreenSummary: () => summarizeSafeSurfaceContext(surfaceApi.getContext(false))
  };
}
