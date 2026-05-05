import type {
  AuditEvent,
  CheckInPolicyDraft,
  DisclosureRecipientDraft,
  ExportBundleView,
  ProofReceiptView,
  RegistrationProfileDraft,
  RouteId,
  ShelterContactRequest,
  UploadItem,
  WalletAccessRequest,
  WalletGrantReceipt
} from "../models/abby";
import { auditEvents } from "../services/mockAbbyService";
import {
  createLocationRegionProof,
  createVerifiedExportBundleView,
  listWalletAuditEvents,
  type WalletApiConfig
} from "../services/walletApi";
import {
  answerServiceNavigationQuestion,
  searchServiceNavigation,
} from "../agent/serviceNavigationAgent";
import { navigateAction, readSurfaceContextAction } from "../agent/tools/navigationTools";
import {
  addRecipientAction,
  approveShelterContactRequestAction,
  denyShelterContactRequestAction,
  editRecipientAction,
  removeRecipientAction,
  requestShelterContactAction
} from "../agent/tools/contactTools";
import {
  previewSharingCapabilitiesAction,
  setDisclosureScopesAction,
  updateRecipientScopesAction
} from "../agent/tools/sharingRuleTools";
import {
  analyzeGrantedRecordAction,
  decideAccessRequestAction,
  delegateGrantAction,
  recordControllerApprovalAction,
  revokeAccessRequestAction,
  viewGrantedRecordAction
} from "../agent/tools/recipientAccessTools";
import type {
  AccessRequestDecisionCommandInput,
  AddRecipientCommandInput,
  AgentCommandName,
  AnalyzeGrantedRecordCommandInput,
  Answer211QuestionCommandInput,
  CreateLocationRegionProofCommandInput,
  CreateServicePlanCommandInput,
  CreateVerifiedExportBundleCommandInput,
  DelegateGrantCommandInput,
  EditRecipientCommandInput,
  OpenServiceDetailCommandInput,
  RemoveRecipientCommandInput,
  RequestShelterContactCommandInput,
  RefreshWalletAuditCommandInput,
  RecordControllerApprovalCommandInput,
  RevokeAccessRequestCommandInput,
  SaveServiceCommandInput,
  Search211ServicesCommandInput,
  ShelterContactRequestDecisionCommandInput,
  UpdateCheckInPolicyCommandInput,
  UpdateRecipientScopesCommandInput,
  UpdateRegistrationDraftCommandInput,
  ViewGrantedRecordCommandInput
} from "../agent/commandSchemas";
import { commandSchemas } from "../agent/commandSchemas";
import type { AgentConfirmationRisk, AgentPermissionLevel, EvidenceBundle, SurfaceContext } from "../agent/types";
import { getRouteLabel, getToolDefinition } from "../agent/surfaceRegistry";
import { confirmationRiskForGate, getAgentToolPermissionPolicy } from "../agent/permissionPolicy";

export interface AppActionState {
  activeRoute: RouteId;
  profile: RegistrationProfileDraft;
  policy: CheckInPolicyDraft;
  recipients: DisclosureRecipientDraft[];
  shelterContactRequests?: ShelterContactRequest[];
  uploads: UploadItem[];
  accessRequests: WalletAccessRequest[];
  grantReceipts: WalletGrantReceipt[];
  walletAuditEvents: AuditEvent[];
  walletProofReceipts: ProofReceiptView[];
  exportBundleViews: ExportBundleView[];
  walletUnlocked?: boolean;
  privateContextAllowed?: boolean;
  permissionLevel?: AgentPermissionLevel;
}

export interface AppActionRuntime {
  getState: () => AppActionState;
  setActiveRoute?: (route: RouteId) => void;
  setMobileNavOpen?: (open: boolean) => void;
  setProfile?: (profile: RegistrationProfileDraft) => void;
  setPolicy?: (policy: CheckInPolicyDraft) => void;
  setRecipients?: (recipients: DisclosureRecipientDraft[]) => void;
  setShelterContactRequests?: (requests: ShelterContactRequest[]) => void;
  setAccessRequests?: (requests: WalletAccessRequest[]) => void;
  setGrantReceipts?: (receipts: WalletGrantReceipt[]) => void;
  setWalletAuditEvents?: (events: AuditEvent[]) => void;
  setWalletProofReceipts?: (proofs: ProofReceiptView[]) => void;
  setExportBundleViews?: (bundles: ExportBundleView[]) => void;
  walletApiConfig?: WalletApiConfig;
  refreshWalletAccessState?: () => Promise<void>;
  refreshWalletAuditEvents?: () => Promise<void>;
}

export interface AppActionOptions {
  confirmed?: boolean;
  userPresent?: boolean;
}

export interface AppActionConfirmationMetadata {
  required: boolean;
  title: string;
  summary: string;
  risk: AgentConfirmationRisk;
  permissionLevel: AgentPermissionLevel;
  auditEventType?: string;
  details?: Record<string, unknown>;
}

export interface AppActionSuccess {
  ok: true;
  action: AgentCommandName;
  summary: string;
  route?: RouteId;
  evidenceBundle?: EvidenceBundle;
  surfaceContext?: SurfaceContext;
  recordIds?: string[];
  artifactId?: string;
  auditEventId?: string;
  confirmation?: AppActionConfirmationMetadata;
  metadata?: Record<string, unknown>;
}

export interface AppActionFailure {
  ok: false;
  action: AgentCommandName;
  errorCode: string;
  message: string;
  retryable?: boolean;
  confirmation?: AppActionConfirmationMetadata;
}

export type AppActionResult = AppActionSuccess | AppActionFailure;

type AppActionHandler<TInput> = (
  runtime: AppActionRuntime,
  input: TInput,
  options: AppActionOptions
) => Promise<AppActionResult>;

function success(
  action: AgentCommandName,
  summary: string,
  extra: Omit<AppActionSuccess, "ok" | "action" | "summary"> = {}
): AppActionSuccess {
  return {
    ok: true,
    action,
    summary,
    ...extra
  };
}

function failure(
  action: AgentCommandName,
  errorCode: string,
  message: string,
  extra: Omit<AppActionFailure, "ok" | "action" | "errorCode" | "message"> = {}
): AppActionFailure {
  return {
    ok: false,
    action,
    errorCode,
    message,
    ...extra
  };
}

function confirmationFor(action: AgentCommandName, input: unknown): AppActionConfirmationMetadata {
  const tool = getToolDefinition(action);
  const policy = getAgentToolPermissionPolicy(action);
  return {
    required: tool.requiresConfirmation,
    title: tool.title,
    summary: summarizeConfirmation(action, input),
    risk: confirmationRiskForGate(policy.gate),
    permissionLevel: tool.permissionLevel,
    auditEventType: tool.auditEventType,
    details: input && typeof input === "object" ? { input, permissionGate: policy.gate, requiresAudit: policy.requiresAudit } : undefined
  };
}

function summarizeConfirmation(action: AgentCommandName, input: unknown): string {
  if (action === "set_disclosure_scopes" && isRecord(input)) {
    return `Update sharing scopes for recipient ${String(input.recipientId ?? "")}.`;
  }
  if (action === "update_recipient_scopes" && isRecord(input)) {
    return `Update sharing scopes for recipient ${String(input.recipientId ?? "")}.`;
  }
  if ((action === "add_recipient" || action === "edit_recipient") && isRecord(input)) {
    return `${action === "add_recipient" ? "Add" : "Edit"} recipient ${String(
      input.displayName ?? input.recipientId ?? ""
    )}.`;
  }
  if (action === "remove_recipient" && isRecord(input)) {
    return `Remove recipient ${String(input.recipientId ?? "")}.`;
  }
  if (action === "request_shelter_contact" && isRecord(input)) {
    return `Request shelter contact with ${String(input.shelterName ?? "")}.`;
  }
  if (
    (action === "approve_shelter_contact_request" || action === "deny_shelter_contact_request") &&
    isRecord(input)
  ) {
    return `${action === "approve_shelter_contact_request" ? "Approve" : "Deny"} shelter contact request ${String(
      input.requestId ?? ""
    )}.`;
  }
  if (
    (action === "record_controller_approval" ||
      action === "approve_access_request" ||
      action === "reject_access_request" ||
      action === "revoke_access_request") &&
    isRecord(input)
  ) {
    const verbs: Partial<Record<AgentCommandName, string>> = {
      record_controller_approval: "Record controller approval for",
      approve_access_request: "Approve",
      reject_access_request: "Reject",
      revoke_access_request: "Revoke"
    };
    return `${verbs[action] ?? "Update"} access request ${String(input.requestId ?? "")}.`;
  }
  if (
    (action === "analyze_granted_record" || action === "view_granted_record" || action === "delegate_grant") &&
    isRecord(input)
  ) {
    const verbs: Partial<Record<AgentCommandName, string>> = {
      analyze_granted_record: "Analyze",
      view_granted_record: "View",
      delegate_grant: "Delegate"
    };
    return `${verbs[action] ?? "Use"} grant ${String(input.grantId ?? input.receiptId ?? "")}.`;
  }
  if (action === "create_location_region_proof" && isRecord(input)) {
    return `Create a location-region proof for ${String(input.regionLabel ?? "the selected region")}.`;
  }
  if (action === "create_verified_export_bundle" && isRecord(input)) {
    return `Create an export bundle for ${String(input.audienceName ?? "the selected recipient")}.`;
  }
  if (action === "update_registration_draft") return "Update private registration profile fields.";
  if (action === "update_check_in_policy") return "Update check-in reminder and escalation settings.";
  if (action === "save_service") return "Save this service to the wallet-backed service list.";
  if (action === "create_service_plan") return "Create a private service follow-up plan.";
  return getToolDefinition(action).title;
}

function requiresConfirmation(action: AgentCommandName, input: unknown, options: AppActionOptions): AppActionFailure | undefined {
  const confirmation = confirmationFor(action, input);
  if (!confirmation.required || options.confirmed) return undefined;
  return failure(action, "confirmation_required", confirmation.summary, { confirmation });
}

function requireSetter<T>(
  action: AgentCommandName,
  setter: ((value: T) => void) | undefined,
  label: string
): ((value: T) => void) | AppActionFailure {
  if (setter) return setter;
  return failure(action, "missing_app_setter", `${label} is not writable in this app action runtime.`);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

async function search211ServicesAction(
  _runtime: AppActionRuntime,
  input: Search211ServicesCommandInput
): Promise<AppActionResult> {
  const response = await searchServiceNavigation(input);
  return success("search_211_services", response.summary, {
    evidenceBundle: response.evidenceBundle,
    recordIds: response.recordIds
  });
}

async function answer211QuestionAction(
  _runtime: AppActionRuntime,
  input: Answer211QuestionCommandInput
): Promise<AppActionResult> {
  const response = await answerServiceNavigationQuestion(input);
  return success("answer_211_question", response.answer, {
    evidenceBundle: response.evidenceBundle,
    recordIds: response.recordIds
  });
}

async function openServiceDetailAction(
  runtime: AppActionRuntime,
  input: OpenServiceDetailCommandInput
): Promise<AppActionResult> {
  await navigateAction(runtime, { route: "social-services" });
  return success("open_service_detail", `Opened service ${input.docId}.`, {
    route: "social-services",
    artifactId: input.docId
  });
}

async function saveServiceAction(
  _runtime: AppActionRuntime,
  input: SaveServiceCommandInput,
  options: AppActionOptions
): Promise<AppActionResult> {
  const blocked = requiresConfirmation("save_service", input, options);
  if (blocked) return blocked;
  return success("save_service", `Saved service ${input.serviceId}.`, {
    artifactId: `saved-${input.serviceId}`,
    confirmation: confirmationFor("save_service", input)
  });
}

async function createServicePlanAction(
  _runtime: AppActionRuntime,
  input: CreateServicePlanCommandInput,
  options: AppActionOptions
): Promise<AppActionResult> {
  const blocked = requiresConfirmation("create_service_plan", input, options);
  if (blocked) return blocked;
  return success("create_service_plan", `Created a service plan for ${input.serviceId}.`, {
    artifactId: `plan-${input.serviceId}-${Date.now()}`,
    confirmation: confirmationFor("create_service_plan", input)
  });
}

async function updateRegistrationDraftAction(
  runtime: AppActionRuntime,
  input: UpdateRegistrationDraftCommandInput,
  options: AppActionOptions
): Promise<AppActionResult> {
  const blocked = requiresConfirmation("update_registration_draft", input, options);
  if (blocked) return blocked;
  const setProfile = requireSetter("update_registration_draft", runtime.setProfile, "Registration profile");
  if (typeof setProfile !== "function") return setProfile;
  const state = runtime.getState();
  setProfile({ ...state.profile, ...input });
  return success("update_registration_draft", "Updated registration draft fields.", {
    confirmation: confirmationFor("update_registration_draft", input)
  });
}

async function updateCheckInPolicyAction(
  runtime: AppActionRuntime,
  input: UpdateCheckInPolicyCommandInput,
  options: AppActionOptions
): Promise<AppActionResult> {
  const blocked = requiresConfirmation("update_check_in_policy", input, options);
  if (blocked) return blocked;
  const setPolicy = requireSetter("update_check_in_policy", runtime.setPolicy, "Check-in policy");
  if (typeof setPolicy !== "function") return setPolicy;
  const state = runtime.getState();
  setPolicy({
    ...state.policy,
    ...input,
    intervalDays: input.intervalDays === undefined ? state.policy.intervalDays : Math.max(1, Math.min(30, input.intervalDays)),
    gracePeriodHours:
      input.gracePeriodHours === undefined ? state.policy.gracePeriodHours : Math.max(0, input.gracePeriodHours)
  });
  return success("update_check_in_policy", "Updated check-in policy.", {
    confirmation: confirmationFor("update_check_in_policy", input)
  });
}

async function createLocationRegionProofAction(
  runtime: AppActionRuntime,
  input: CreateLocationRegionProofCommandInput,
  options: AppActionOptions
): Promise<AppActionResult> {
  const blocked = requiresConfirmation("create_location_region_proof", input, options);
  if (blocked) return blocked;
  const setProofs = requireSetter("create_location_region_proof", runtime.setWalletProofReceipts, "Proof receipts");
  if (typeof setProofs !== "function") return setProofs;
  if (!runtime.walletApiConfig?.actorDid) {
    return failure("create_location_region_proof", "wallet_api_required", "Connect a wallet API before creating proofs.");
  }
  try {
    const state = runtime.getState();
    const proof = await createLocationRegionProof(runtime.walletApiConfig, {
      locationRecordId: input.recordId?.trim() || "rec-location-current",
      regionId: input.regionLabel.trim()
    });
    setProofs([proof, ...state.walletProofReceipts.filter((item) => item.id !== proof.id)]);
    await runtime.refreshWalletAuditEvents?.().catch(() => undefined);
    return success("create_location_region_proof", `Created proof for ${input.regionLabel}.`, {
      artifactId: proof.id,
      confirmation: confirmationFor("create_location_region_proof", input)
    });
  } catch {
    return failure("create_location_region_proof", "proof_creation_failed", "Proof creation failed.", {
      retryable: true,
      confirmation: confirmationFor("create_location_region_proof", input)
    });
  }
}

async function createVerifiedExportBundleAction(
  runtime: AppActionRuntime,
  input: CreateVerifiedExportBundleCommandInput,
  options: AppActionOptions
): Promise<AppActionResult> {
  const blocked = requiresConfirmation("create_verified_export_bundle", input, options);
  if (blocked) return blocked;
  const setBundles = requireSetter("create_verified_export_bundle", runtime.setExportBundleViews, "Export bundles");
  if (typeof setBundles !== "function") return setBundles;
  if (!runtime.walletApiConfig) {
    return failure("create_verified_export_bundle", "wallet_api_required", "Connect a wallet API before creating exports.");
  }
  const extendedInput = input as CreateVerifiedExportBundleCommandInput & { audienceDid?: string; purpose?: string };
  const audienceDid = extendedInput.audienceDid?.trim() || input.audienceName.trim();
  if (!audienceDid.startsWith("did:")) {
    return failure(
      "create_verified_export_bundle",
      "audience_did_required",
      "Export bundle creation requires a recipient DID."
    );
  }
  try {
    const state = runtime.getState();
    const bundle = await createVerifiedExportBundleView(runtime.walletApiConfig, {
      audienceDid,
      audienceName: input.audienceName,
      purpose: extendedInput.purpose || "user_export",
      recordIds: input.recordIds
    });
    setBundles([bundle, ...state.exportBundleViews.filter((item) => item.bundleId !== bundle.bundleId)]);
    return success("create_verified_export_bundle", `Created export bundle for ${bundle.audienceName}.`, {
      artifactId: bundle.bundleId,
      recordIds: input.recordIds,
      confirmation: confirmationFor("create_verified_export_bundle", input)
    });
  } catch {
    return failure("create_verified_export_bundle", "export_creation_failed", "Export bundle creation failed.", {
      retryable: true,
      confirmation: confirmationFor("create_verified_export_bundle", input)
    });
  }
}

async function refreshWalletAuditAction(
  runtime: AppActionRuntime,
  input: RefreshWalletAuditCommandInput
): Promise<AppActionResult> {
  const setWalletAuditEvents = requireSetter("refresh_wallet_audit", runtime.setWalletAuditEvents, "Wallet audit");
  if (typeof setWalletAuditEvents !== "function") return setWalletAuditEvents;
  if (!runtime.walletApiConfig) {
    const limitedEvents = auditEvents.slice(0, input.limit ?? auditEvents.length);
    setWalletAuditEvents(limitedEvents);
    return success("refresh_wallet_audit", `Loaded ${limitedEvents.length} local audit events.`);
  }
  const events = await listWalletAuditEvents(runtime.walletApiConfig);
  const limitedEvents = events.slice(0, input.limit ?? events.length);
  setWalletAuditEvents(limitedEvents.length ? limitedEvents : auditEvents);
  return success("refresh_wallet_audit", `Loaded ${limitedEvents.length || auditEvents.length} audit events.`);
}

export const appActionHandlers = {
  navigate: navigateAction,
  read_surface_context: readSurfaceContextAction,
  search_211_services: search211ServicesAction,
  answer_211_question: answer211QuestionAction,
  open_service_detail: openServiceDetailAction,
  save_service: saveServiceAction,
  create_service_plan: createServicePlanAction,
  update_registration_draft: updateRegistrationDraftAction,
  update_check_in_policy: updateCheckInPolicyAction,
  add_recipient: (runtime, input: AddRecipientCommandInput, options) => addRecipientAction(runtime, input, options),
  edit_recipient: (runtime, input: EditRecipientCommandInput, options) => editRecipientAction(runtime, input, options),
  remove_recipient: (runtime, input: RemoveRecipientCommandInput, options) =>
    removeRecipientAction(runtime, input, options),
  update_recipient_scopes: (runtime, input: UpdateRecipientScopesCommandInput, options) =>
    updateRecipientScopesAction(runtime, input, options),
  preview_sharing_capabilities: previewSharingCapabilitiesAction,
  request_shelter_contact: (runtime, input: RequestShelterContactCommandInput, options) =>
    requestShelterContactAction(runtime, input, options),
  approve_shelter_contact_request: (runtime, input: ShelterContactRequestDecisionCommandInput, options) =>
    approveShelterContactRequestAction(runtime, input, options),
  deny_shelter_contact_request: (runtime, input: ShelterContactRequestDecisionCommandInput, options) =>
    denyShelterContactRequestAction(runtime, input, options),
  set_disclosure_scopes: setDisclosureScopesAction,
  record_controller_approval: (runtime, input: RecordControllerApprovalCommandInput, options) =>
    recordControllerApprovalAction(runtime, input, options),
  approve_access_request: (runtime, input, options) =>
    decideAccessRequestAction(runtime, input, "approved", "approve_access_request", options),
  reject_access_request: (runtime, input, options) =>
    decideAccessRequestAction(runtime, input, "rejected", "reject_access_request", options),
  revoke_access_request: (runtime, input: RevokeAccessRequestCommandInput, options) =>
    revokeAccessRequestAction(runtime, input, options),
  analyze_granted_record: (runtime, input: AnalyzeGrantedRecordCommandInput, options) =>
    analyzeGrantedRecordAction(runtime, input, options),
  view_granted_record: (runtime, input: ViewGrantedRecordCommandInput, options) =>
    viewGrantedRecordAction(runtime, input, options),
  delegate_grant: (runtime, input: DelegateGrantCommandInput, options) =>
    delegateGrantAction(runtime, input, options),
  create_location_region_proof: createLocationRegionProofAction,
  create_verified_export_bundle: createVerifiedExportBundleAction,
  refresh_wallet_audit: refreshWalletAuditAction
} satisfies Record<AgentCommandName, AppActionHandler<never>>;

export async function runAppAction(
  runtime: AppActionRuntime,
  action: AgentCommandName,
  input: unknown,
  options: AppActionOptions = {}
): Promise<AppActionResult> {
  const schema = commandSchemas[action];
  if (!schema.isInput(input)) {
    return failure(action, "invalid_input", `Invalid input for ${action}.`);
  }
  return appActionHandlers[action](runtime, input as never, options);
}

export function listAppActionConfirmations(): Record<AgentCommandName, AppActionConfirmationMetadata> {
  return Object.fromEntries(
    Object.keys(commandSchemas).map((name) => {
      const action = name as AgentCommandName;
      return [action, confirmationFor(action, {})];
    })
  ) as Record<AgentCommandName, AppActionConfirmationMetadata>;
}
