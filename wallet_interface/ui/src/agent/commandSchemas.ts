import type { RouteId } from "../models/abby";
import type { AgentCommandSchema, AgentSchemaProperty, EvidenceBundle } from "./types";
import {
  isBoolean,
  isEvidenceBundle,
  isNumber,
  isOptional,
  isRecord,
  isRouteId,
  isString,
  isStringArray
} from "./types";

export const AGENT_COMMAND_NAMES = [
  "navigate",
  "read_surface_context",
  "search_211_services",
  "answer_211_question",
  "open_service_detail",
  "save_service",
  "create_service_plan",
  "update_registration_draft",
  "update_check_in_policy",
  "set_disclosure_scopes",
  "approve_access_request",
  "reject_access_request",
  "create_location_region_proof",
  "create_verified_export_bundle",
  "refresh_wallet_audit"
] as const;

export type AgentCommandName = (typeof AGENT_COMMAND_NAMES)[number];

export interface CommandSuccessOutput {
  ok: true;
  summary: string;
  route?: RouteId;
  evidenceBundle?: EvidenceBundle;
  recordIds?: string[];
  artifactId?: string;
}

export interface CommandFailureOutput {
  ok: false;
  errorCode: string;
  message: string;
  retryable?: boolean;
}

export type CommandOutput = CommandSuccessOutput | CommandFailureOutput;

const routeIds = [
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
] as const;

const checkInChannels = ["email", "sms", "web"] as const;

const disclosureScopes = [
  "identity_minimum",
  "profile",
  "photo",
  "current_location",
  "uploaded_documents",
  "missed_check_in",
  "found_permanent_housing",
  "medical_notes",
  "shelter_history",
  "benefits_information",
  "custom"
] as const;

export interface NavigateCommandInput {
  route: RouteId;
}

export interface ReadSurfaceContextCommandInput {
  route?: RouteId;
  includePrivateContext?: boolean;
}

export interface Search211ServicesCommandInput {
  query: string;
  limit?: number;
  city?: string;
  category?: string;
}

export interface Answer211QuestionCommandInput {
  question: string;
  useLocalModel?: boolean;
}

export interface OpenServiceDetailCommandInput {
  docId: string;
}

export interface SaveServiceCommandInput {
  serviceId: string;
  note?: string;
}

export interface CreateServicePlanCommandInput {
  serviceId: string;
  goal: string;
  steps?: string[];
}

export interface UpdateRegistrationDraftCommandInput {
  preferredName?: string;
  pronouns?: string;
  phone?: string;
  email?: string;
  currentLocation?: string;
  shelterAffiliation?: string;
  serviceNeeds?: string[];
  preferredCheckInChannels?: Array<"email" | "sms" | "web">;
}

export interface UpdateCheckInPolicyCommandInput {
  intervalDays?: number;
  reminderChannels?: Array<"email" | "sms" | "web">;
  gracePeriodHours?: number;
  escalationEnabled?: boolean;
}

export interface SetDisclosureScopesCommandInput {
  recipientId: string;
  allowedScopes: string[];
}

export interface AccessRequestDecisionCommandInput {
  requestId: string;
  reason?: string;
}

export interface CreateLocationRegionProofCommandInput {
  verifier: string;
  regionLabel: string;
  recordId?: string;
}

export interface CreateVerifiedExportBundleCommandInput {
  audienceName: string;
  recordIds: string[];
  proofIds?: string[];
}

export interface RefreshWalletAuditCommandInput {
  limit?: number;
}

const stringProperty: AgentSchemaProperty = { type: "string" };
const booleanProperty: AgentSchemaProperty = { type: "boolean" };
const numberProperty: AgentSchemaProperty = { type: "number" };
const stringArrayProperty: AgentSchemaProperty = { type: "array", items: stringProperty };

const commandOutputSchema: AgentSchemaProperty = {
  type: "object",
  required: ["ok"],
  additionalProperties: true,
  properties: {
    ok: booleanProperty,
    summary: stringProperty,
    route: { type: "string", enum: routeIds },
    errorCode: stringProperty,
    message: stringProperty,
    retryable: booleanProperty,
    recordIds: stringArrayProperty,
    artifactId: stringProperty
  }
};

function objectSchema(
  properties: Record<string, AgentSchemaProperty>,
  required: readonly string[] = [],
  additionalProperties = false
): AgentSchemaProperty {
  return {
    type: "object",
    required,
    properties,
    additionalProperties
  };
}

function isCommandOutput(value: unknown): value is CommandOutput {
  if (!isRecord(value) || !isBoolean(value.ok)) {
    return false;
  }
  if (value.ok) {
    return (
      isString(value.summary) &&
      isOptional(value.route, isRouteId) &&
      isOptional(value.evidenceBundle, isEvidenceBundle) &&
      isOptional(value.recordIds, isStringArray) &&
      isOptional(value.artifactId, isString)
    );
  }
  return (
    isString(value.errorCode) &&
    isString(value.message) &&
    isOptional(value.retryable, isBoolean)
  );
}

function isStringOneOf<T extends readonly string[]>(values: T, value: unknown): value is T[number] {
  return isString(value) && values.includes(value);
}

function isOptionalLimitedNumber(value: unknown, min: number, max: number): value is number | undefined {
  return value === undefined || (isNumber(value) && value >= min && value <= max);
}

function isCheckInChannelArray(value: unknown): value is Array<"email" | "sms" | "web"> {
  return Array.isArray(value) && value.every((item) => isStringOneOf(checkInChannels, item));
}

function isDisclosureScopeArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => isStringOneOf(disclosureScopes, item));
}

export function isNavigateCommandInput(value: unknown): value is NavigateCommandInput {
  return isRecord(value) && isRouteId(value.route);
}

export function isReadSurfaceContextCommandInput(value: unknown): value is ReadSurfaceContextCommandInput {
  return (
    isRecord(value) &&
    isOptional(value.route, isRouteId) &&
    isOptional(value.includePrivateContext, isBoolean)
  );
}

export function isSearch211ServicesCommandInput(value: unknown): value is Search211ServicesCommandInput {
  return (
    isRecord(value) &&
    isString(value.query) &&
    value.query.trim().length > 0 &&
    isOptionalLimitedNumber(value.limit, 1, 20) &&
    isOptional(value.city, isString) &&
    isOptional(value.category, isString)
  );
}

export function isAnswer211QuestionCommandInput(value: unknown): value is Answer211QuestionCommandInput {
  return (
    isRecord(value) &&
    isString(value.question) &&
    value.question.trim().length > 0 &&
    isOptional(value.useLocalModel, isBoolean)
  );
}

export function isOpenServiceDetailCommandInput(value: unknown): value is OpenServiceDetailCommandInput {
  return isRecord(value) && isString(value.docId) && value.docId.trim().length > 0;
}

export function isSaveServiceCommandInput(value: unknown): value is SaveServiceCommandInput {
  return (
    isRecord(value) &&
    isString(value.serviceId) &&
    value.serviceId.trim().length > 0 &&
    isOptional(value.note, isString)
  );
}

export function isCreateServicePlanCommandInput(value: unknown): value is CreateServicePlanCommandInput {
  return (
    isRecord(value) &&
    isString(value.serviceId) &&
    value.serviceId.trim().length > 0 &&
    isString(value.goal) &&
    value.goal.trim().length > 0 &&
    isOptional(value.steps, isStringArray)
  );
}

export function isUpdateRegistrationDraftCommandInput(value: unknown): value is UpdateRegistrationDraftCommandInput {
  return (
    isRecord(value) &&
    isOptional(value.preferredName, isString) &&
    isOptional(value.pronouns, isString) &&
    isOptional(value.phone, isString) &&
    isOptional(value.email, isString) &&
    isOptional(value.currentLocation, isString) &&
    isOptional(value.shelterAffiliation, isString) &&
    isOptional(value.serviceNeeds, isStringArray) &&
    isOptional(value.preferredCheckInChannels, isCheckInChannelArray)
  );
}

export function isUpdateCheckInPolicyCommandInput(value: unknown): value is UpdateCheckInPolicyCommandInput {
  return (
    isRecord(value) &&
    isOptionalLimitedNumber(value.intervalDays, 1, 365) &&
    isOptional(value.reminderChannels, isCheckInChannelArray) &&
    isOptionalLimitedNumber(value.gracePeriodHours, 0, 168) &&
    isOptional(value.escalationEnabled, isBoolean)
  );
}

export function isSetDisclosureScopesCommandInput(value: unknown): value is SetDisclosureScopesCommandInput {
  return (
    isRecord(value) &&
    isString(value.recipientId) &&
    value.recipientId.trim().length > 0 &&
    isDisclosureScopeArray(value.allowedScopes)
  );
}

export function isAccessRequestDecisionCommandInput(value: unknown): value is AccessRequestDecisionCommandInput {
  return (
    isRecord(value) &&
    isString(value.requestId) &&
    value.requestId.trim().length > 0 &&
    isOptional(value.reason, isString)
  );
}

export function isCreateLocationRegionProofCommandInput(value: unknown): value is CreateLocationRegionProofCommandInput {
  return (
    isRecord(value) &&
    isString(value.verifier) &&
    value.verifier.trim().length > 0 &&
    isString(value.regionLabel) &&
    value.regionLabel.trim().length > 0 &&
    isOptional(value.recordId, isString)
  );
}

export function isCreateVerifiedExportBundleCommandInput(value: unknown): value is CreateVerifiedExportBundleCommandInput {
  return (
    isRecord(value) &&
    isString(value.audienceName) &&
    value.audienceName.trim().length > 0 &&
    isStringArray(value.recordIds) &&
    value.recordIds.length > 0 &&
    isOptional(value.proofIds, isStringArray)
  );
}

export function isRefreshWalletAuditCommandInput(value: unknown): value is RefreshWalletAuditCommandInput {
  return isRecord(value) && isOptionalLimitedNumber(value.limit, 1, 100);
}

export const commandSchemas = {
  navigate: {
    name: "navigate",
    description: "Move the app to a registered route.",
    inputSchema: objectSchema({ route: { type: "string", enum: routeIds } }, ["route"]),
    outputSchema: commandOutputSchema,
    isInput: isNavigateCommandInput,
    isOutput: isCommandOutput
  },
  read_surface_context: {
    name: "read_surface_context",
    description: "Read public or approved contextual state for the current app surface.",
    inputSchema: objectSchema({
      route: { type: "string", enum: routeIds },
      includePrivateContext: booleanProperty
    }),
    outputSchema: commandOutputSchema,
    isInput: isReadSurfaceContextCommandInput,
    isOutput: isCommandOutput
  },
  search_211_services: {
    name: "search_211_services",
    description: "Search the local 211 corpus for service records.",
    inputSchema: objectSchema({
      query: stringProperty,
      limit: numberProperty,
      city: stringProperty,
      category: stringProperty
    }, ["query"]),
    outputSchema: commandOutputSchema,
    isInput: isSearch211ServicesCommandInput,
    isOutput: isCommandOutput
  },
  answer_211_question: {
    name: "answer_211_question",
    description: "Answer a question using grounded local 211 corpus evidence.",
    inputSchema: objectSchema({
      question: stringProperty,
      useLocalModel: booleanProperty
    }, ["question"]),
    outputSchema: commandOutputSchema,
    isInput: isAnswer211QuestionCommandInput,
    isOutput: isCommandOutput
  },
  open_service_detail: {
    name: "open_service_detail",
    description: "Open a specific service record detail surface.",
    inputSchema: objectSchema({ docId: stringProperty }, ["docId"]),
    outputSchema: commandOutputSchema,
    isInput: isOpenServiceDetailCommandInput,
    isOutput: isCommandOutput
  },
  save_service: {
    name: "save_service",
    description: "Save a service to the user's wallet-backed service list.",
    inputSchema: objectSchema({ serviceId: stringProperty, note: stringProperty }, ["serviceId"]),
    outputSchema: commandOutputSchema,
    isInput: isSaveServiceCommandInput,
    isOutput: isCommandOutput
  },
  create_service_plan: {
    name: "create_service_plan",
    description: "Create a follow-up plan for a selected service.",
    inputSchema: objectSchema({
      serviceId: stringProperty,
      goal: stringProperty,
      steps: stringArrayProperty
    }, ["serviceId", "goal"]),
    outputSchema: commandOutputSchema,
    isInput: isCreateServicePlanCommandInput,
    isOutput: isCommandOutput
  },
  update_registration_draft: {
    name: "update_registration_draft",
    description: "Update non-legal-name registration draft fields.",
    inputSchema: objectSchema({
      preferredName: stringProperty,
      pronouns: stringProperty,
      phone: stringProperty,
      email: stringProperty,
      currentLocation: stringProperty,
      shelterAffiliation: stringProperty,
      serviceNeeds: stringArrayProperty,
      preferredCheckInChannels: { type: "array", items: { type: "string", enum: checkInChannels } }
    }),
    outputSchema: commandOutputSchema,
    isInput: isUpdateRegistrationDraftCommandInput,
    isOutput: isCommandOutput
  },
  update_check_in_policy: {
    name: "update_check_in_policy",
    description: "Update check-in reminder cadence and escalation settings.",
    inputSchema: objectSchema({
      intervalDays: numberProperty,
      reminderChannels: { type: "array", items: { type: "string", enum: checkInChannels } },
      gracePeriodHours: numberProperty,
      escalationEnabled: booleanProperty
    }),
    outputSchema: commandOutputSchema,
    isInput: isUpdateCheckInPolicyCommandInput,
    isOutput: isCommandOutput
  },
  set_disclosure_scopes: {
    name: "set_disclosure_scopes",
    description: "Set which disclosure scopes a recipient may access.",
    inputSchema: objectSchema({
      recipientId: stringProperty,
      allowedScopes: { type: "array", items: { type: "string", enum: disclosureScopes } }
    }, ["recipientId", "allowedScopes"]),
    outputSchema: commandOutputSchema,
    isInput: isSetDisclosureScopesCommandInput,
    isOutput: isCommandOutput
  },
  approve_access_request: {
    name: "approve_access_request",
    description: "Approve a pending wallet access request.",
    inputSchema: objectSchema({ requestId: stringProperty, reason: stringProperty }, ["requestId"]),
    outputSchema: commandOutputSchema,
    isInput: isAccessRequestDecisionCommandInput,
    isOutput: isCommandOutput
  },
  reject_access_request: {
    name: "reject_access_request",
    description: "Reject a pending wallet access request.",
    inputSchema: objectSchema({ requestId: stringProperty, reason: stringProperty }, ["requestId"]),
    outputSchema: commandOutputSchema,
    isInput: isAccessRequestDecisionCommandInput,
    isOutput: isCommandOutput
  },
  create_location_region_proof: {
    name: "create_location_region_proof",
    description: "Create a verifier-scoped proof about being within a location region.",
    inputSchema: objectSchema({
      verifier: stringProperty,
      regionLabel: stringProperty,
      recordId: stringProperty
    }, ["verifier", "regionLabel"]),
    outputSchema: commandOutputSchema,
    isInput: isCreateLocationRegionProofCommandInput,
    isOutput: isCommandOutput
  },
  create_verified_export_bundle: {
    name: "create_verified_export_bundle",
    description: "Create a shareable export bundle from selected wallet records and proofs.",
    inputSchema: objectSchema({
      audienceName: stringProperty,
      recordIds: stringArrayProperty,
      proofIds: stringArrayProperty
    }, ["audienceName", "recordIds"]),
    outputSchema: commandOutputSchema,
    isInput: isCreateVerifiedExportBundleCommandInput,
    isOutput: isCommandOutput
  },
  refresh_wallet_audit: {
    name: "refresh_wallet_audit",
    description: "Refresh wallet audit events.",
    inputSchema: objectSchema({ limit: numberProperty }),
    outputSchema: commandOutputSchema,
    isInput: isRefreshWalletAuditCommandInput,
    isOutput: isCommandOutput
  }
} satisfies Record<AgentCommandName, AgentCommandSchema>;

export function isAgentCommandName(value: unknown): value is AgentCommandName {
  return isString(value) && AGENT_COMMAND_NAMES.includes(value as AgentCommandName);
}

export function getCommandSchema(name: AgentCommandName): AgentCommandSchema {
  return commandSchemas[name];
}

export function isCommandInput(name: AgentCommandName, value: unknown): boolean {
  return commandSchemas[name].isInput(value);
}

export function isCommandOutputFor(name: AgentCommandName, value: unknown): value is CommandOutput {
  return commandSchemas[name].isOutput(value);
}

export { isCommandOutput };
