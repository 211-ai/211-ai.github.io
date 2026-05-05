import type { RouteId } from "../models/abby";
import type { AgentPermissionLevel, AgentToolDefinition } from "./types";
import {
  hasPermissionLevel,
  isAgentPermissionLevel,
  isAgentToolDefinition,
  isOneOf,
  isRecord,
  isRouteId,
  isString
} from "./types";
import type { AgentCommandName } from "./commandSchemas";
import { commandSchemas, isAgentCommandName } from "./commandSchemas";

export const SURFACE_CONTEXT_SCOPES = ["public", "app_state", "wallet_metadata", "wallet_private"] as const;
export type SurfaceContextScope = (typeof SURFACE_CONTEXT_SCOPES)[number];

export interface SurfaceContextProviderDefinition {
  id: string;
  label: string;
  scope: SurfaceContextScope;
  permissionLevel: AgentPermissionLevel;
}

export interface AgentSurfaceDefinition {
  route: RouteId;
  label: string;
  contextProviders: SurfaceContextProviderDefinition[];
  tools: AgentCommandName[];
}

export function isSurfaceContextScope(value: unknown): value is SurfaceContextScope {
  return isOneOf(SURFACE_CONTEXT_SCOPES, value);
}

export function isSurfaceContextProviderDefinition(value: unknown): value is SurfaceContextProviderDefinition {
  return (
    isRecord(value) &&
    isString(value.id) &&
    isString(value.label) &&
    isSurfaceContextScope(value.scope) &&
    isAgentPermissionLevel(value.permissionLevel)
  );
}

export function isAgentSurfaceDefinition(value: unknown): value is AgentSurfaceDefinition {
  return (
    isRecord(value) &&
    isRouteId(value.route) &&
    isString(value.label) &&
    Array.isArray(value.contextProviders) &&
    value.contextProviders.every(isSurfaceContextProviderDefinition) &&
    Array.isArray(value.tools) &&
    value.tools.every(isAgentCommandName)
  );
}

export function isRegisteredAgentToolDefinition(value: unknown): value is AgentToolDefinition {
  if (!isAgentToolDefinition(value) || !isAgentCommandName(value.name)) {
    return false;
  }
  const schema = commandSchemas[value.name];
  return value.inputSchema === schema.inputSchema && value.outputSchema === schema.outputSchema;
}

type ToolPolicy = Pick<
  AgentToolDefinition,
  | "title"
  | "permissionLevel"
  | "surfaces"
  | "requiresConfirmation"
  | "requiresWalletUnlock"
  | "requiresUserPresence"
  | "requiresPrivateContextOptIn"
  | "auditEventType"
>;

const allRoutes = [
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

const routeLabels: Record<RouteId, string> = {
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

const publicContext: SurfaceContextProviderDefinition = {
  id: "route_summary",
  label: "Route summary",
  scope: "public",
  permissionLevel: "public"
};

const appStateContext: SurfaceContextProviderDefinition = {
  id: "visible_app_state",
  label: "Visible app state",
  scope: "app_state",
  permissionLevel: "app_context"
};

const walletMetadataContext: SurfaceContextProviderDefinition = {
  id: "wallet_metadata",
  label: "Wallet record metadata",
  scope: "wallet_metadata",
  permissionLevel: "wallet_metadata"
};

const walletPrivateContext: SurfaceContextProviderDefinition = {
  id: "wallet_private_context",
  label: "Private wallet context",
  scope: "wallet_private",
  permissionLevel: "wallet_private"
};

const commonReadTools: AgentCommandName[] = ["navigate", "read_surface_context"];

const surfaceTools: Record<RouteId, AgentCommandName[]> = {
  home: commonReadTools,
  register: [...commonReadTools, "update_registration_draft"],
  "check-in": [...commonReadTools, "update_check_in_policy"],
  contacts: [...commonReadTools],
  "sharing-rules": [...commonReadTools, "set_disclosure_scopes"],
  uploads: [...commonReadTools],
  "social-services": [
    ...commonReadTools,
    "search_211_services",
    "answer_211_question",
    "open_service_detail",
    "save_service",
    "create_service_plan"
  ],
  shelter: [...commonReadTools, "search_211_services", "answer_211_question"],
  "recipient-access": [...commonReadTools, "approve_access_request", "reject_access_request"],
  "benefits-protection": [...commonReadTools, "search_211_services", "answer_211_question"],
  analytics: commonReadTools,
  "proof-center": [...commonReadTools, "create_location_region_proof"],
  exports: [...commonReadTools, "create_verified_export_bundle"],
  security: commonReadTools,
  audit: [...commonReadTools, "refresh_wallet_audit"]
};

const contextProvidersByRoute: Record<RouteId, SurfaceContextProviderDefinition[]> = {
  home: [publicContext, appStateContext],
  register: [publicContext, appStateContext, walletPrivateContext],
  "check-in": [publicContext, appStateContext, walletPrivateContext],
  contacts: [publicContext, appStateContext, walletMetadataContext],
  "sharing-rules": [publicContext, appStateContext, walletMetadataContext],
  uploads: [publicContext, appStateContext, walletMetadataContext],
  "social-services": [publicContext, appStateContext],
  shelter: [publicContext, appStateContext],
  "recipient-access": [publicContext, appStateContext, walletMetadataContext],
  "benefits-protection": [publicContext, appStateContext, walletMetadataContext],
  analytics: [publicContext, appStateContext, walletMetadataContext],
  "proof-center": [publicContext, appStateContext, walletMetadataContext, walletPrivateContext],
  exports: [publicContext, appStateContext, walletMetadataContext],
  security: [publicContext, appStateContext, walletMetadataContext],
  audit: [publicContext, appStateContext, walletMetadataContext]
};

const toolPolicies: Record<AgentCommandName, ToolPolicy> = {
  navigate: {
    title: "Navigate",
    permissionLevel: "public",
    surfaces: [...allRoutes],
    requiresConfirmation: false,
    requiresWalletUnlock: false,
    requiresUserPresence: false,
    requiresPrivateContextOptIn: false
  },
  read_surface_context: {
    title: "Read surface context",
    permissionLevel: "app_context",
    surfaces: [...allRoutes],
    requiresConfirmation: false,
    requiresWalletUnlock: false,
    requiresUserPresence: false,
    requiresPrivateContextOptIn: false
  },
  search_211_services: {
    title: "Search 211 services",
    permissionLevel: "public",
    surfaces: ["social-services", "shelter", "benefits-protection"],
    requiresConfirmation: false,
    requiresWalletUnlock: false,
    requiresUserPresence: false,
    requiresPrivateContextOptIn: false
  },
  answer_211_question: {
    title: "Answer 211 question",
    permissionLevel: "public",
    surfaces: ["social-services", "shelter", "benefits-protection"],
    requiresConfirmation: false,
    requiresWalletUnlock: false,
    requiresUserPresence: false,
    requiresPrivateContextOptIn: false
  },
  open_service_detail: {
    title: "Open service detail",
    permissionLevel: "public",
    surfaces: ["social-services"],
    requiresConfirmation: false,
    requiresWalletUnlock: false,
    requiresUserPresence: false,
    requiresPrivateContextOptIn: false
  },
  save_service: {
    title: "Save service",
    permissionLevel: "wallet_write",
    surfaces: ["social-services"],
    requiresConfirmation: true,
    requiresWalletUnlock: true,
    requiresUserPresence: true,
    requiresPrivateContextOptIn: false,
    auditEventType: "agent.service.save"
  },
  create_service_plan: {
    title: "Create service plan",
    permissionLevel: "wallet_write",
    surfaces: ["social-services"],
    requiresConfirmation: true,
    requiresWalletUnlock: true,
    requiresUserPresence: true,
    requiresPrivateContextOptIn: true,
    auditEventType: "agent.service_plan.create"
  },
  update_registration_draft: {
    title: "Update registration draft",
    permissionLevel: "wallet_private",
    surfaces: ["register"],
    requiresConfirmation: true,
    requiresWalletUnlock: true,
    requiresUserPresence: true,
    requiresPrivateContextOptIn: true,
    auditEventType: "agent.registration.update"
  },
  update_check_in_policy: {
    title: "Update check-in policy",
    permissionLevel: "wallet_write",
    surfaces: ["check-in"],
    requiresConfirmation: true,
    requiresWalletUnlock: true,
    requiresUserPresence: true,
    requiresPrivateContextOptIn: false,
    auditEventType: "agent.check_in_policy.update"
  },
  set_disclosure_scopes: {
    title: "Set disclosure scopes",
    permissionLevel: "wallet_write",
    surfaces: ["sharing-rules"],
    requiresConfirmation: true,
    requiresWalletUnlock: true,
    requiresUserPresence: true,
    requiresPrivateContextOptIn: false,
    auditEventType: "agent.disclosure_scopes.set"
  },
  approve_access_request: {
    title: "Approve access request",
    permissionLevel: "wallet_write",
    surfaces: ["recipient-access"],
    requiresConfirmation: true,
    requiresWalletUnlock: true,
    requiresUserPresence: true,
    requiresPrivateContextOptIn: false,
    auditEventType: "agent.access_request.approve"
  },
  reject_access_request: {
    title: "Reject access request",
    permissionLevel: "wallet_write",
    surfaces: ["recipient-access"],
    requiresConfirmation: true,
    requiresWalletUnlock: true,
    requiresUserPresence: true,
    requiresPrivateContextOptIn: false,
    auditEventType: "agent.access_request.reject"
  },
  create_location_region_proof: {
    title: "Create location proof",
    permissionLevel: "wallet_write",
    surfaces: ["proof-center"],
    requiresConfirmation: true,
    requiresWalletUnlock: true,
    requiresUserPresence: true,
    requiresPrivateContextOptIn: true,
    auditEventType: "agent.proof.location_region.create"
  },
  create_verified_export_bundle: {
    title: "Create verified export bundle",
    permissionLevel: "wallet_write",
    surfaces: ["exports"],
    requiresConfirmation: true,
    requiresWalletUnlock: true,
    requiresUserPresence: true,
    requiresPrivateContextOptIn: false,
    auditEventType: "agent.export_bundle.create"
  },
  refresh_wallet_audit: {
    title: "Refresh wallet audit",
    permissionLevel: "wallet_metadata",
    surfaces: ["audit"],
    requiresConfirmation: false,
    requiresWalletUnlock: true,
    requiresUserPresence: false,
    requiresPrivateContextOptIn: false
  }
};

export const agentSurfaces: AgentSurfaceDefinition[] = allRoutes.map((route) => ({
  route,
  label: routeLabels[route],
  contextProviders: contextProvidersByRoute[route],
  tools: surfaceTools[route]
}));

export const agentToolDefinitions: AgentToolDefinition[] = Object.entries(toolPolicies).map(([name, policy]) => {
  const commandName = name as AgentCommandName;
  const schema = commandSchemas[commandName];
  return {
    name: commandName,
    title: policy.title,
    description: schema.description,
    inputSchema: schema.inputSchema,
    outputSchema: schema.outputSchema,
    permissionLevel: policy.permissionLevel,
    surfaces: policy.surfaces,
    requiresConfirmation: policy.requiresConfirmation,
    requiresWalletUnlock: policy.requiresWalletUnlock,
    requiresUserPresence: policy.requiresUserPresence,
    requiresPrivateContextOptIn: policy.requiresPrivateContextOptIn,
    auditEventType: policy.auditEventType
  };
});

export function isAgentSurfaceRegistry(value: unknown): value is AgentSurfaceDefinition[] {
  return Array.isArray(value) && value.every(isAgentSurfaceDefinition);
}

export function isAgentToolDefinitionRegistry(value: unknown): value is AgentToolDefinition[] {
  return Array.isArray(value) && value.every(isRegisteredAgentToolDefinition);
}

export function getSurfaceDefinition(route: RouteId): AgentSurfaceDefinition {
  return agentSurfaces.find((surface) => surface.route === route) || agentSurfaces[0];
}

export function getRouteLabel(route: RouteId): string {
  return routeLabels[route];
}

export function getToolDefinition(name: AgentCommandName): AgentToolDefinition {
  const definition = agentToolDefinitions.find((tool) => tool.name === name);
  if (!definition) {
    throw new Error(`Unknown agent tool: ${name}`);
  }
  return definition;
}

export function listToolsForSurface(route: RouteId, permissionLevel: AgentPermissionLevel = "public"): AgentToolDefinition[] {
  const surface = getSurfaceDefinition(route);
  return surface.tools
    .map(getToolDefinition)
    .filter((tool) => hasPermissionLevel(permissionLevel, tool.permissionLevel));
}

export function canUseToolOnSurface(name: AgentCommandName, route: RouteId, permissionLevel: AgentPermissionLevel): boolean {
  const tool = getToolDefinition(name);
  return tool.surfaces.includes(route) && hasPermissionLevel(permissionLevel, tool.permissionLevel);
}

export function listContextProvidersForSurface(
  route: RouteId,
  permissionLevel: AgentPermissionLevel = "public"
): SurfaceContextProviderDefinition[] {
  return getSurfaceDefinition(route).contextProviders.filter((provider) =>
    hasPermissionLevel(permissionLevel, provider.permissionLevel)
  );
}
