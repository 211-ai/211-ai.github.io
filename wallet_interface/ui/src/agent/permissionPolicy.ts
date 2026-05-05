import type { RouteId } from "../models/abby";
import type { AgentCommandName } from "./commandSchemas";
import type { AgentConfirmationRisk, AgentPermissionLevel } from "./types";
import { hasPermissionLevel } from "./types";

export const AGENT_PERMISSION_GATES = [
  "read_public",
  "read_wallet_summary",
  "write_wallet",
  "share_or_disclose"
] as const;

export type AgentPermissionGate = (typeof AGENT_PERMISSION_GATES)[number];

export type AgentPermissionPolicyFailureCode =
  | "surface_not_allowed"
  | "permission_denied"
  | "wallet_locked"
  | "user_presence_required"
  | "private_context_required";

export interface AgentToolPermissionPolicy {
  gate: AgentPermissionGate;
  requiresConfirmation: boolean;
  requiresWalletUnlock: boolean;
  requiresUserPresence: boolean;
  requiresPrivateContextOptIn: boolean;
  requiresAudit: boolean;
  auditEventType?: string;
}

export interface AgentPermissionPolicyEnvironment {
  route: RouteId;
  allowedSurfaces: readonly RouteId[];
  grantedPermissionLevel: AgentPermissionLevel;
  walletUnlocked: boolean;
  privateContextAllowed: boolean;
  userPresent: boolean;
  toolTitle?: string;
}

export interface AgentPermissionPolicyAllowed {
  ok: true;
  policy: AgentToolPermissionPolicy;
}

export interface AgentPermissionPolicyDenied {
  ok: false;
  policy: AgentToolPermissionPolicy;
  code: AgentPermissionPolicyFailureCode;
  message: string;
}

export type AgentPermissionPolicyDecision = AgentPermissionPolicyAllowed | AgentPermissionPolicyDenied;

export const agentToolPermissionPolicies: Record<AgentCommandName, AgentToolPermissionPolicy> = {
  navigate: readPublicPolicy(),
  read_surface_context: readPublicPolicy(),
  search_211_services: readPublicPolicy(),
  answer_211_question: readPublicPolicy(),
  open_service_detail: readPublicPolicy(),
  save_service: writeWalletPolicy("agent.service.save"),
  create_service_plan: writeWalletPolicy("agent.service_plan.create", { requiresPrivateContextOptIn: true }),
  update_registration_draft: writeWalletPolicy("agent.registration.update", { requiresPrivateContextOptIn: true }),
  update_check_in_policy: writeWalletPolicy("agent.check_in_policy.update"),
  set_disclosure_scopes: shareOrDisclosePolicy("agent.disclosure_scopes.set"),
  approve_access_request: shareOrDisclosePolicy("agent.access_request.approve"),
  reject_access_request: shareOrDisclosePolicy("agent.access_request.reject"),
  create_location_region_proof: shareOrDisclosePolicy("agent.proof.location_region.create", {
    requiresPrivateContextOptIn: true
  }),
  create_verified_export_bundle: shareOrDisclosePolicy("agent.export_bundle.create"),
  refresh_wallet_audit: {
    gate: "read_wallet_summary",
    requiresConfirmation: false,
    requiresWalletUnlock: true,
    requiresUserPresence: false,
    requiresPrivateContextOptIn: false,
    requiresAudit: false
  }
};

export function getAgentToolPermissionPolicy(name: AgentCommandName): AgentToolPermissionPolicy {
  return agentToolPermissionPolicies[name];
}

export function evaluateAgentToolPermissionPolicy(
  name: AgentCommandName,
  environment: AgentPermissionPolicyEnvironment
): AgentPermissionPolicyDecision {
  const policy = getAgentToolPermissionPolicy(name);
  const title = environment.toolTitle ?? name;

  if (!environment.allowedSurfaces.includes(environment.route)) {
    return denied(policy, "surface_not_allowed", `${title} cannot run from this surface.`);
  }

  if (!hasAgentPermissionGate(environment.grantedPermissionLevel, policy.gate)) {
    return denied(policy, "permission_denied", `${title} requires ${policy.gate} permission.`);
  }

  if (policy.requiresWalletUnlock && !environment.walletUnlocked) {
    return denied(policy, "wallet_locked", `${title} requires an unlocked wallet.`);
  }

  if (policy.requiresUserPresence && !environment.userPresent) {
    return denied(policy, "user_presence_required", `${title} requires user presence.`);
  }

  if (policy.requiresPrivateContextOptIn && !environment.privateContextAllowed) {
    return denied(policy, "private_context_required", `${title} requires private context permission.`);
  }

  return {
    ok: true,
    policy
  };
}

export function hasAgentPermissionGate(granted: AgentPermissionLevel, required: AgentPermissionGate): boolean {
  return hasPermissionLevel(granted, required);
}

export function permissionLevelForGate(gate: AgentPermissionGate): AgentPermissionLevel {
  return gate;
}

export function confirmationRiskForGate(gate: AgentPermissionGate): AgentConfirmationRisk {
  if (gate === "share_or_disclose") return "restricted";
  if (gate === "write_wallet") return "high";
  if (gate === "read_wallet_summary") return "moderate";
  return "low";
}

export function isAgentPermissionGate(value: unknown): value is AgentPermissionGate {
  return typeof value === "string" && AGENT_PERMISSION_GATES.includes(value as AgentPermissionGate);
}

function readPublicPolicy(): AgentToolPermissionPolicy {
  return {
    gate: "read_public",
    requiresConfirmation: false,
    requiresWalletUnlock: false,
    requiresUserPresence: false,
    requiresPrivateContextOptIn: false,
    requiresAudit: false
  };
}

function writeWalletPolicy(
  auditEventType: string,
  options: Partial<Pick<AgentToolPermissionPolicy, "requiresPrivateContextOptIn">> = {}
): AgentToolPermissionPolicy {
  return {
    gate: "write_wallet",
    requiresConfirmation: true,
    requiresWalletUnlock: true,
    requiresUserPresence: true,
    requiresPrivateContextOptIn: options.requiresPrivateContextOptIn ?? false,
    requiresAudit: true,
    auditEventType
  };
}

function shareOrDisclosePolicy(
  auditEventType: string,
  options: Partial<Pick<AgentToolPermissionPolicy, "requiresPrivateContextOptIn">> = {}
): AgentToolPermissionPolicy {
  return {
    gate: "share_or_disclose",
    requiresConfirmation: true,
    requiresWalletUnlock: true,
    requiresUserPresence: true,
    requiresPrivateContextOptIn: options.requiresPrivateContextOptIn ?? false,
    requiresAudit: true,
    auditEventType
  };
}

function denied(
  policy: AgentToolPermissionPolicy,
  code: AgentPermissionPolicyFailureCode,
  message: string
): AgentPermissionPolicyDenied {
  return {
    ok: false,
    policy,
    code,
    message
  };
}
