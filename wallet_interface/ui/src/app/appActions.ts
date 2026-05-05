import type {
  AuditEvent,
  CheckInPolicyDraft,
  DisclosureDataScope,
  DisclosureRecipientDraft,
  ExportBundleView,
  ProofReceiptView,
  RegistrationProfileDraft,
  RouteId,
  UploadItem,
  WalletAccessRequest,
  WalletGrantReceipt
} from "../models/abby";
import { auditEvents } from "../services/mockAbbyService";
import {
  approveAccessRequest as approveWalletAccessRequest,
  createLocationRegionProof,
  createVerifiedExportBundleView,
  listWalletAuditEvents,
  rejectAccessRequest as rejectWalletAccessRequest,
  type WalletApiConfig
} from "../services/walletApi";
import {
  answerServiceNavigationQuestion,
  searchServiceNavigation,
} from "../agent/serviceNavigationAgent";
import { getRouteFromHash, setLocationRouteHash } from "./appState";
import type {
  AccessRequestDecisionCommandInput,
  AgentCommandName,
  Answer211QuestionCommandInput,
  CreateLocationRegionProofCommandInput,
  CreateServicePlanCommandInput,
  CreateVerifiedExportBundleCommandInput,
  NavigateCommandInput,
  OpenServiceDetailCommandInput,
  ReadSurfaceContextCommandInput,
  RefreshWalletAuditCommandInput,
  SaveServiceCommandInput,
  Search211ServicesCommandInput,
  SetDisclosureScopesCommandInput,
  UpdateCheckInPolicyCommandInput,
  UpdateRegistrationDraftCommandInput
} from "../agent/commandSchemas";
import { commandSchemas } from "../agent/commandSchemas";
import type { AgentConfirmationRisk, AgentPermissionLevel, EvidenceBundle, SurfaceContext } from "../agent/types";
import { getRouteLabel, getToolDefinition } from "../agent/surfaceRegistry";

export interface AppActionState {
  activeRoute: RouteId;
  profile: RegistrationProfileDraft;
  policy: CheckInPolicyDraft;
  recipients: DisclosureRecipientDraft[];
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
  return {
    required: tool.requiresConfirmation,
    title: tool.title,
    summary: summarizeConfirmation(action, input),
    risk: confirmationRiskFor(tool.permissionLevel),
    permissionLevel: tool.permissionLevel,
    auditEventType: tool.auditEventType,
    details: input && typeof input === "object" ? { input } : undefined
  };
}

function confirmationRiskFor(permissionLevel: AgentPermissionLevel): AgentConfirmationRisk {
  if (permissionLevel === "admin") return "restricted";
  if (permissionLevel === "wallet_write") return "high";
  if (permissionLevel === "wallet_private") return "moderate";
  return "low";
}

function summarizeConfirmation(action: AgentCommandName, input: unknown): string {
  if (action === "set_disclosure_scopes" && isRecord(input)) {
    return `Update sharing scopes for recipient ${String(input.recipientId ?? "")}.`;
  }
  if ((action === "approve_access_request" || action === "reject_access_request") && isRecord(input)) {
    return `${action === "approve_access_request" ? "Approve" : "Reject"} access request ${String(input.requestId ?? "")}.`;
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

function uniqueStrings(values: string[]): string[] {
  return Array.from(new Set(values.map((value) => value.trim()).filter(Boolean)));
}

function surfaceContextFromState(state: AppActionState, input: ReadSurfaceContextCommandInput = {}): SurfaceContext {
  const route = input.route ?? state.activeRoute ?? getRouteFromHash();
  const includePrivateContext = Boolean(input.includePrivateContext && state.privateContextAllowed);
  const visibleServiceDocIds = route === "social-services" ? [] : undefined;
  const visibleRecordIds =
    route === "uploads" || route === "proof-center" || route === "exports"
      ? state.uploads.map((upload) => upload.recordId || upload.id)
      : undefined;

  return {
    route,
    routeLabel: getRouteLabel(route),
    capturedAt: new Date().toISOString(),
    visibleRecordIds,
    visibleServiceDocIds,
    walletUnlocked: state.walletUnlocked ?? true,
    privateContextAllowed: state.privateContextAllowed ?? false,
    permissionLevel: includePrivateContext ? "wallet_private" : "app_context",
    summary: summarizeRouteState(route, state),
    metadata: includePrivateContext
      ? {
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
        }
      : {
          uploadCount: state.uploads.length,
          recipientCount: state.recipients.length,
          pendingAccessRequestCount: state.accessRequests.filter((request) => request.status === "pending").length
        }
  };
}

function summarizeRouteState(route: RouteId, state: AppActionState): string {
  if (route === "register") {
    const name = state.profile.preferredName || state.profile.legalName || "No name yet";
    return `Registration draft for ${name}; ${state.profile.serviceNeeds.length} service needs selected.`;
  }
  if (route === "check-in") {
    return `Check-in every ${state.policy.intervalDays} days through ${state.policy.reminderChannels.join(", ") || "no channels"}.`;
  }
  if (route === "sharing-rules" || route === "contacts") {
    return `${state.recipients.length} recipients saved.`;
  }
  if (route === "recipient-access") {
    return `${state.accessRequests.filter((request) => request.status === "pending").length} pending access requests.`;
  }
  if (route === "proof-center") {
    return `${state.walletProofReceipts.length} proof receipts available.`;
  }
  if (route === "exports") {
    return `${state.exportBundleViews.length} export bundles available.`;
  }
  if (route === "audit") {
    return `${state.walletAuditEvents.length} audit events visible.`;
  }
  return `${getRouteLabel(route)} surface is active.`;
}

async function navigateAction(
  runtime: AppActionRuntime,
  input: NavigateCommandInput
): Promise<AppActionResult> {
  setLocationRouteHash(input.route);
  runtime.setActiveRoute?.(input.route);
  runtime.setMobileNavOpen?.(false);
  return success("navigate", `Opened ${getRouteLabel(input.route)}.`, { route: input.route });
}

async function readSurfaceContextAction(
  runtime: AppActionRuntime,
  input: ReadSurfaceContextCommandInput
): Promise<AppActionResult> {
  const surfaceContext = surfaceContextFromState(runtime.getState(), input);
  return success("read_surface_context", surfaceContext.summary || `Read ${surfaceContext.routeLabel}.`, {
    route: surfaceContext.route,
    surfaceContext
  });
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

async function setDisclosureScopesAction(
  runtime: AppActionRuntime,
  input: SetDisclosureScopesCommandInput,
  options: AppActionOptions
): Promise<AppActionResult> {
  const blocked = requiresConfirmation("set_disclosure_scopes", input, options);
  if (blocked) return blocked;
  const setRecipients = requireSetter("set_disclosure_scopes", runtime.setRecipients, "Recipients");
  if (typeof setRecipients !== "function") return setRecipients;
  const state = runtime.getState();
  const recipient = state.recipients.find((item) => item.id === input.recipientId);
  if (!recipient) {
    return failure("set_disclosure_scopes", "recipient_not_found", `Recipient ${input.recipientId} was not found.`);
  }
  setRecipients(
    state.recipients.map((item) =>
      item.id === input.recipientId
        ? { ...item, allowedScopes: uniqueStrings(input.allowedScopes) as DisclosureDataScope[] }
        : item
    )
  );
  return success("set_disclosure_scopes", `Updated sharing scopes for ${recipient.displayName}.`, {
    artifactId: input.recipientId,
    confirmation: confirmationFor("set_disclosure_scopes", input)
  });
}

async function decideAccessRequestAction(
  runtime: AppActionRuntime,
  input: AccessRequestDecisionCommandInput,
  status: "approved" | "rejected",
  action: "approve_access_request" | "reject_access_request",
  options: AppActionOptions
): Promise<AppActionResult> {
  const blocked = requiresConfirmation(action, input, options);
  if (blocked) return blocked;
  const setAccessRequests = requireSetter(action, runtime.setAccessRequests, "Access requests");
  if (typeof setAccessRequests !== "function") return setAccessRequests;
  const state = runtime.getState();
  const request = state.accessRequests.find((item) => item.id === input.requestId);
  if (!request) return failure(action, "access_request_not_found", `Access request ${input.requestId} was not found.`);

  if (runtime.walletApiConfig?.actorDid) {
    try {
      if (status === "approved") {
        await approveWalletAccessRequest(runtime.walletApiConfig, input.requestId);
      } else {
        await rejectWalletAccessRequest(runtime.walletApiConfig, input.requestId, input.reason || "Rejected by app action");
      }
      await runtime.refreshWalletAccessState?.();
      await runtime.refreshWalletAuditEvents?.();
      return success(action, `${status === "approved" ? "Approved" : "Rejected"} ${request.requesterName}.`, {
        artifactId: input.requestId,
        confirmation: confirmationFor(action, input)
      });
    } catch {
      // Keep the local demo state path available if a configured API is unavailable.
    }
  }

  setAccessRequests(
    state.accessRequests.map((item) =>
      item.id === input.requestId
        ? { ...item, status, grantStatus: status === "approved" ? "active" : item.grantStatus }
        : item
    )
  );

  if (
    status === "approved" &&
    runtime.setGrantReceipts &&
    !state.grantReceipts.some((receipt) => receipt.id === `receipt-${request.id}`)
  ) {
    runtime.setGrantReceipts([
      ...state.grantReceipts,
      {
        id: `receipt-${request.id}`,
        grantId: `grant-${request.id}`,
        audienceName: request.requesterName,
        audienceDid: request.audienceDid,
        resources: [`wallet://demo-wallet/records/${request.resourceLabel}`],
        recordId: undefined,
        resourceLabel: request.resourceLabel,
        abilities: request.abilities,
        purpose: request.purpose,
        receiptHash: `local-${request.id}-receipt`,
        status: "active",
        createdAt: "Just now",
        expiresAt: "30 days"
      }
    ]);
  }

  return success(action, `${status === "approved" ? "Approved" : "Rejected"} ${request.requesterName}.`, {
    artifactId: input.requestId,
    confirmation: confirmationFor(action, input)
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
  set_disclosure_scopes: setDisclosureScopesAction,
  approve_access_request: (runtime, input, options) =>
    decideAccessRequestAction(runtime, input, "approved", "approve_access_request", options),
  reject_access_request: (runtime, input, options) =>
    decideAccessRequestAction(runtime, input, "rejected", "reject_access_request", options),
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
