import type { RouteId } from "../models/abby";
import type { AgentCommandSchema, AgentSchemaProperty, EvidenceBundle } from "./types";
import {
  isAgentCommandSchema,
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
  "add_recipient",
  "edit_recipient",
  "remove_recipient",
  "update_recipient_scopes",
  "preview_sharing_capabilities",
  "request_shelter_contact",
  "approve_shelter_contact_request",
  "deny_shelter_contact_request",
  "summarize_upload_requirements",
  "classify_uploaded_document",
  "repair_upload_storage",
  "toggle_upload_shared",
  "set_disclosure_scopes",
  "record_controller_approval",
  "approve_access_request",
  "reject_access_request",
  "revoke_access_request",
  "analyze_granted_record",
  "view_granted_record",
  "delegate_grant",
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

const disclosureRecipientTypes = [
  "emergency_contact",
  "police_precinct",
  "social_worker",
  "shelter_staff",
  "government_liaison",
  "benefits_agency"
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

export interface AddRecipientCommandInput {
  displayName: string;
  type?: (typeof disclosureRecipientTypes)[number];
  relationship?: string;
  email?: string;
  phone?: string;
  agencyName?: string;
  precinctName?: string;
  verified?: boolean;
  allowedScopes?: string[];
}

export interface EditRecipientCommandInput {
  recipientId: string;
  displayName?: string;
  type?: (typeof disclosureRecipientTypes)[number];
  relationship?: string;
  email?: string;
  phone?: string;
  agencyName?: string;
  precinctName?: string;
  verified?: boolean;
  allowedScopes?: string[];
}

export interface RemoveRecipientCommandInput {
  recipientId: string;
  reason?: string;
}

export interface UpdateRecipientScopesCommandInput {
  recipientId: string;
  allowedScopes: string[];
  stageOnly?: boolean;
}

export interface PreviewSharingCapabilitiesCommandInput {
  recipientId?: string;
  allowedScopes?: string[];
}

export interface RequestShelterContactCommandInput {
  shelterName: string;
  userName?: string;
  userContact?: string;
}

export interface ShelterContactRequestDecisionCommandInput {
  requestId: string;
  reason?: string;
}

export const UPLOAD_DOCUMENT_CATEGORIES = [
  "Identity",
  "Benefits",
  "Housing",
  "Medical",
  "Legal",
  "Income",
  "Contact",
  "Other"
] as const;
export type UploadDocumentCategory = (typeof UPLOAD_DOCUMENT_CATEGORIES)[number];

export const UPLOAD_DOCUMENT_SENSITIVITIES = ["low", "moderate", "high", "restricted"] as const;
export type UploadDocumentSensitivity = (typeof UPLOAD_DOCUMENT_SENSITIVITIES)[number];

export interface SummarizeUploadRequirementsCommandInput {
  goal?: string;
  documentType?: string;
}

export interface ClassifyUploadedDocumentCommandInput {
  uploadId?: string;
  recordId?: string;
  fileName?: string;
  mimeType?: string;
  machineSummary?: string;
  userSelected: boolean;
  categoryHint?: UploadDocumentCategory;
}

export interface RepairUploadStorageCommandInput {
  uploadId?: string;
  recordId?: string;
}

export interface ToggleUploadSharedCommandInput {
  uploadId: string;
  shared: boolean;
  reason?: string;
}

export interface AccessRequestDecisionCommandInput {
  requestId: string;
  reason?: string;
}

export interface RecordControllerApprovalCommandInput {
  requestId: string;
}

export interface RevokeAccessRequestCommandInput {
  requestId: string;
  reason?: string;
}

export const RECIPIENT_ANALYSIS_MODES = ["summary", "redacted", "vector", "extract-text", "form"] as const;
export type RecipientAnalysisMode = (typeof RECIPIENT_ANALYSIS_MODES)[number];

export interface AnalyzeGrantedRecordCommandInput {
  grantId?: string;
  receiptId?: string;
  recordId?: string;
  mode?: RecipientAnalysisMode;
  maxChars?: number;
  maxBytes?: number;
  chunkSizeWords?: number;
  maxFields?: number;
  useOcr?: boolean;
  userPresent?: boolean;
}

export interface ViewGrantedRecordCommandInput {
  grantId?: string;
  receiptId?: string;
  recordId?: string;
  userPresent?: boolean;
}

export interface DelegateGrantCommandInput {
  grantId?: string;
  receiptId?: string;
  audienceDid: string;
  audienceKeyHex?: string;
  ability?: string;
  purpose?: string;
  expiresAt?: string;
  resources?: string[];
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

function isDisclosureRecipientType(value: unknown): value is (typeof disclosureRecipientTypes)[number] {
  return isStringOneOf(disclosureRecipientTypes, value);
}

function isUploadDocumentCategory(value: unknown): value is UploadDocumentCategory {
  return isStringOneOf(UPLOAD_DOCUMENT_CATEGORIES, value);
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

export function isAddRecipientCommandInput(value: unknown): value is AddRecipientCommandInput {
  return (
    isRecord(value) &&
    isString(value.displayName) &&
    value.displayName.trim().length > 0 &&
    isOptional(value.type, isDisclosureRecipientType) &&
    isOptional(value.relationship, isString) &&
    isOptional(value.email, isString) &&
    isOptional(value.phone, isString) &&
    isOptional(value.agencyName, isString) &&
    isOptional(value.precinctName, isString) &&
    isOptional(value.verified, isBoolean) &&
    isOptional(value.allowedScopes, isDisclosureScopeArray)
  );
}

export function isEditRecipientCommandInput(value: unknown): value is EditRecipientCommandInput {
  return (
    isRecord(value) &&
    isString(value.recipientId) &&
    value.recipientId.trim().length > 0 &&
    isOptional(value.displayName, isString) &&
    isOptional(value.type, isDisclosureRecipientType) &&
    isOptional(value.relationship, isString) &&
    isOptional(value.email, isString) &&
    isOptional(value.phone, isString) &&
    isOptional(value.agencyName, isString) &&
    isOptional(value.precinctName, isString) &&
    isOptional(value.verified, isBoolean) &&
    isOptional(value.allowedScopes, isDisclosureScopeArray)
  );
}

export function isRemoveRecipientCommandInput(value: unknown): value is RemoveRecipientCommandInput {
  return (
    isRecord(value) &&
    isString(value.recipientId) &&
    value.recipientId.trim().length > 0 &&
    isOptional(value.reason, isString)
  );
}

export function isUpdateRecipientScopesCommandInput(value: unknown): value is UpdateRecipientScopesCommandInput {
  return (
    isRecord(value) &&
    isString(value.recipientId) &&
    value.recipientId.trim().length > 0 &&
    isDisclosureScopeArray(value.allowedScopes) &&
    isOptional(value.stageOnly, isBoolean)
  );
}

export function isPreviewSharingCapabilitiesCommandInput(value: unknown): value is PreviewSharingCapabilitiesCommandInput {
  return (
    isRecord(value) &&
    (value.recipientId === undefined || (isString(value.recipientId) && value.recipientId.trim().length > 0)) &&
    isOptional(value.allowedScopes, isDisclosureScopeArray) &&
    (value.recipientId !== undefined || value.allowedScopes !== undefined)
  );
}

export function isRequestShelterContactCommandInput(value: unknown): value is RequestShelterContactCommandInput {
  return (
    isRecord(value) &&
    isString(value.shelterName) &&
    value.shelterName.trim().length > 0 &&
    isOptional(value.userName, isString) &&
    isOptional(value.userContact, isString)
  );
}

export function isShelterContactRequestDecisionCommandInput(
  value: unknown
): value is ShelterContactRequestDecisionCommandInput {
  return (
    isRecord(value) &&
    isString(value.requestId) &&
    value.requestId.trim().length > 0 &&
    isOptional(value.reason, isString)
  );
}

export function isSummarizeUploadRequirementsCommandInput(
  value: unknown
): value is SummarizeUploadRequirementsCommandInput {
  return isRecord(value) && isOptional(value.goal, isString) && isOptional(value.documentType, isString);
}

export function isClassifyUploadedDocumentCommandInput(
  value: unknown
): value is ClassifyUploadedDocumentCommandInput {
  return (
    isRecord(value) &&
    value.userSelected === true &&
    (value.uploadId === undefined || (isString(value.uploadId) && value.uploadId.trim().length > 0)) &&
    (value.recordId === undefined || (isString(value.recordId) && value.recordId.trim().length > 0)) &&
    (value.fileName === undefined || (isString(value.fileName) && value.fileName.trim().length > 0)) &&
    isOptional(value.mimeType, isString) &&
    isOptional(value.machineSummary, isString) &&
    isOptional(value.categoryHint, isUploadDocumentCategory) &&
    (value.uploadId !== undefined || value.recordId !== undefined || value.fileName !== undefined)
  );
}

export function isRepairUploadStorageCommandInput(value: unknown): value is RepairUploadStorageCommandInput {
  return (
    isRecord(value) &&
    (value.uploadId === undefined || (isString(value.uploadId) && value.uploadId.trim().length > 0)) &&
    (value.recordId === undefined || (isString(value.recordId) && value.recordId.trim().length > 0)) &&
    (value.uploadId !== undefined || value.recordId !== undefined)
  );
}

export function isToggleUploadSharedCommandInput(value: unknown): value is ToggleUploadSharedCommandInput {
  return (
    isRecord(value) &&
    isString(value.uploadId) &&
    value.uploadId.trim().length > 0 &&
    isBoolean(value.shared) &&
    isOptional(value.reason, isString)
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

export function isRecordControllerApprovalCommandInput(value: unknown): value is RecordControllerApprovalCommandInput {
  return isRecord(value) && isString(value.requestId) && value.requestId.trim().length > 0;
}

export function isRevokeAccessRequestCommandInput(value: unknown): value is RevokeAccessRequestCommandInput {
  return (
    isRecord(value) &&
    isString(value.requestId) &&
    value.requestId.trim().length > 0 &&
    isOptional(value.reason, isString)
  );
}

function hasGrantReference(value: Record<string, unknown>): boolean {
  return (
    (isString(value.grantId) && value.grantId.trim().length > 0) ||
    (isString(value.receiptId) && value.receiptId.trim().length > 0)
  );
}

function isRecipientAnalysisMode(value: unknown): value is RecipientAnalysisMode {
  return value === undefined || isStringOneOf(RECIPIENT_ANALYSIS_MODES, value);
}

export function isAnalyzeGrantedRecordCommandInput(value: unknown): value is AnalyzeGrantedRecordCommandInput {
  return (
    isRecord(value) &&
    hasGrantReference(value) &&
    isOptional(value.recordId, isString) &&
    isRecipientAnalysisMode(value.mode) &&
    isOptionalLimitedNumber(value.maxChars, 1, 100_000) &&
    isOptionalLimitedNumber(value.maxBytes, 1, 10_000_000) &&
    isOptionalLimitedNumber(value.chunkSizeWords, 10, 2_000) &&
    isOptionalLimitedNumber(value.maxFields, 1, 1_000) &&
    isOptional(value.useOcr, isBoolean) &&
    isOptional(value.userPresent, isBoolean)
  );
}

export function isViewGrantedRecordCommandInput(value: unknown): value is ViewGrantedRecordCommandInput {
  return (
    isRecord(value) &&
    hasGrantReference(value) &&
    isOptional(value.recordId, isString) &&
    isOptional(value.userPresent, isBoolean)
  );
}

export function isDelegateGrantCommandInput(value: unknown): value is DelegateGrantCommandInput {
  return (
    isRecord(value) &&
    hasGrantReference(value) &&
    isString(value.audienceDid) &&
    value.audienceDid.trim().length > 0 &&
    isOptional(value.audienceKeyHex, isString) &&
    isOptional(value.ability, isString) &&
    isOptional(value.purpose, isString) &&
    isOptional(value.expiresAt, isString) &&
    isOptional(value.resources, isStringArray)
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
  add_recipient: {
    name: "add_recipient",
    description: "Add a contact or sharing recipient to the wallet draft.",
    inputSchema: objectSchema({
      displayName: stringProperty,
      type: { type: "string", enum: disclosureRecipientTypes },
      relationship: stringProperty,
      email: stringProperty,
      phone: stringProperty,
      agencyName: stringProperty,
      precinctName: stringProperty,
      verified: booleanProperty,
      allowedScopes: { type: "array", items: { type: "string", enum: disclosureScopes } }
    }, ["displayName"]),
    outputSchema: commandOutputSchema,
    isInput: isAddRecipientCommandInput,
    isOutput: isCommandOutput
  },
  edit_recipient: {
    name: "edit_recipient",
    description: "Edit saved contact recipient fields or sharing scopes.",
    inputSchema: objectSchema({
      recipientId: stringProperty,
      displayName: stringProperty,
      type: { type: "string", enum: disclosureRecipientTypes },
      relationship: stringProperty,
      email: stringProperty,
      phone: stringProperty,
      agencyName: stringProperty,
      precinctName: stringProperty,
      verified: booleanProperty,
      allowedScopes: { type: "array", items: { type: "string", enum: disclosureScopes } }
    }, ["recipientId"]),
    outputSchema: commandOutputSchema,
    isInput: isEditRecipientCommandInput,
    isOutput: isCommandOutput
  },
  remove_recipient: {
    name: "remove_recipient",
    description: "Remove a saved contact recipient after confirmation.",
    inputSchema: objectSchema({ recipientId: stringProperty, reason: stringProperty }, ["recipientId"]),
    outputSchema: commandOutputSchema,
    isInput: isRemoveRecipientCommandInput,
    isOutput: isCommandOutput
  },
  update_recipient_scopes: {
    name: "update_recipient_scopes",
    description: "Stage and apply updated sharing scopes for a recipient after confirmation.",
    inputSchema: objectSchema({
      recipientId: stringProperty,
      allowedScopes: { type: "array", items: { type: "string", enum: disclosureScopes } },
      stageOnly: booleanProperty
    }, ["recipientId", "allowedScopes"]),
    outputSchema: commandOutputSchema,
    isInput: isUpdateRecipientScopesCommandInput,
    isOutput: isCommandOutput
  },
  preview_sharing_capabilities: {
    name: "preview_sharing_capabilities",
    description: "Preview capabilities implied by disclosure scopes without changing wallet state.",
    inputSchema: objectSchema({
      recipientId: stringProperty,
      allowedScopes: { type: "array", items: { type: "string", enum: disclosureScopes } }
    }),
    outputSchema: commandOutputSchema,
    isInput: isPreviewSharingCapabilitiesCommandInput,
    isOutput: isCommandOutput
  },
  request_shelter_contact: {
    name: "request_shelter_contact",
    description: "Stage a contact request from the user to a shelter.",
    inputSchema: objectSchema({
      shelterName: stringProperty,
      userName: stringProperty,
      userContact: stringProperty
    }, ["shelterName"]),
    outputSchema: commandOutputSchema,
    isInput: isRequestShelterContactCommandInput,
    isOutput: isCommandOutput
  },
  approve_shelter_contact_request: {
    name: "approve_shelter_contact_request",
    description: "Approve a pending shelter contact request and add the shelter contact.",
    inputSchema: objectSchema({ requestId: stringProperty, reason: stringProperty }, ["requestId"]),
    outputSchema: commandOutputSchema,
    isInput: isShelterContactRequestDecisionCommandInput,
    isOutput: isCommandOutput
  },
  deny_shelter_contact_request: {
    name: "deny_shelter_contact_request",
    description: "Deny a pending shelter contact request.",
    inputSchema: objectSchema({ requestId: stringProperty, reason: stringProperty }, ["requestId"]),
    outputSchema: commandOutputSchema,
    isInput: isShelterContactRequestDecisionCommandInput,
    isOutput: isCommandOutput
  },
  summarize_upload_requirements: {
    name: "summarize_upload_requirements",
    description: "Guide a user through selecting documents to upload without reading local files.",
    inputSchema: objectSchema({
      goal: stringProperty,
      documentType: stringProperty
    }),
    outputSchema: commandOutputSchema,
    isInput: isSummarizeUploadRequirementsCommandInput,
    isOutput: isCommandOutput
  },
  classify_uploaded_document: {
    name: "classify_uploaded_document",
    description: "Classify metadata for a document after the user selected it through an upload event.",
    inputSchema: objectSchema({
      uploadId: stringProperty,
      recordId: stringProperty,
      fileName: stringProperty,
      mimeType: stringProperty,
      machineSummary: stringProperty,
      userSelected: booleanProperty,
      categoryHint: { type: "string", enum: UPLOAD_DOCUMENT_CATEGORIES }
    }, ["userSelected"]),
    outputSchema: commandOutputSchema,
    isInput: isClassifyUploadedDocumentCommandInput,
    isOutput: isCommandOutput
  },
  repair_upload_storage: {
    name: "repair_upload_storage",
    description: "Repair wallet storage for an already uploaded record.",
    inputSchema: objectSchema({
      uploadId: stringProperty,
      recordId: stringProperty
    }),
    outputSchema: commandOutputSchema,
    isInput: isRepairUploadStorageCommandInput,
    isOutput: isCommandOutput
  },
  toggle_upload_shared: {
    name: "toggle_upload_shared",
    description: "Change whether an uploaded document is marked as shareable after confirmation.",
    inputSchema: objectSchema({
      uploadId: stringProperty,
      shared: booleanProperty,
      reason: stringProperty
    }, ["uploadId", "shared"]),
    outputSchema: commandOutputSchema,
    isInput: isToggleUploadSharedCommandInput,
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
  record_controller_approval: {
    name: "record_controller_approval",
    description: "Record one required controller approval toward an access request threshold.",
    inputSchema: objectSchema({ requestId: stringProperty }, ["requestId"]),
    outputSchema: commandOutputSchema,
    isInput: isRecordControllerApprovalCommandInput,
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
  revoke_access_request: {
    name: "revoke_access_request",
    description: "Revoke an active wallet access grant created from an access request.",
    inputSchema: objectSchema({ requestId: stringProperty, reason: stringProperty }, ["requestId"]),
    outputSchema: commandOutputSchema,
    isInput: isRevokeAccessRequestCommandInput,
    isOutput: isCommandOutput
  },
  analyze_granted_record: {
    name: "analyze_granted_record",
    description: "Create an allowed derived analysis artifact from a record covered by an active grant.",
    inputSchema: objectSchema({
      grantId: stringProperty,
      receiptId: stringProperty,
      recordId: stringProperty,
      mode: { type: "string", enum: RECIPIENT_ANALYSIS_MODES },
      maxChars: numberProperty,
      maxBytes: numberProperty,
      chunkSizeWords: numberProperty,
      maxFields: numberProperty,
      useOcr: booleanProperty,
      userPresent: booleanProperty
    }),
    outputSchema: commandOutputSchema,
    isInput: isAnalyzeGrantedRecordCommandInput,
    isOutput: isCommandOutput
  },
  view_granted_record: {
    name: "view_granted_record",
    description: "View plaintext for a record covered by an active grant with decrypt ability.",
    inputSchema: objectSchema({
      grantId: stringProperty,
      receiptId: stringProperty,
      recordId: stringProperty,
      userPresent: booleanProperty
    }),
    outputSchema: commandOutputSchema,
    isInput: isViewGrantedRecordCommandInput,
    isOutput: isCommandOutput
  },
  delegate_grant: {
    name: "delegate_grant",
    description: "Delegate one allowed ability from an active grant to another recipient DID.",
    inputSchema: objectSchema({
      grantId: stringProperty,
      receiptId: stringProperty,
      audienceDid: stringProperty,
      audienceKeyHex: stringProperty,
      ability: stringProperty,
      purpose: stringProperty,
      expiresAt: stringProperty,
      resources: stringArrayProperty
    }, ["audienceDid"]),
    outputSchema: commandOutputSchema,
    isInput: isDelegateGrantCommandInput,
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

export function validateCommandSchemas(): string[] {
  const errors: string[] = [];

  for (const name of AGENT_COMMAND_NAMES) {
    const schema = commandSchemas[name];
    if (!isAgentCommandSchema(schema)) {
      errors.push(`Invalid agent command schema: ${name}`);
      continue;
    }
    if (schema.name !== name) {
      errors.push(`Command schema key ${name} has mismatched name ${schema.name}.`);
    }
  }

  for (const name of Object.keys(commandSchemas)) {
    if (!isAgentCommandName(name)) {
      errors.push(`Unexpected agent command schema: ${name}`);
    }
  }

  return errors;
}

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
