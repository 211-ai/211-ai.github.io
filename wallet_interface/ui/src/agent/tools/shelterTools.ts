import type { DisclosureRecipientDraft, ShelterContactRequest } from "../../models/abby";
import type { ShelterStaffAccount, ShelterUserAccount } from "../../app/appState";
import type { AppActionOptions, AppActionResult, AppActionRuntime } from "../../app/appActions";
import type {
  AddShelterAsRecipientCommandInput,
  CreateManagedUserAccountCommandInput,
  CreateShelterStaffAccountCommandInput,
  RequestShelterContactCommandInput,
  SendShelterNudgeCommandInput,
  ShelterContactRequestDecisionCommandInput,
  UserShelterRequestDecisionCommandInput
} from "../commandSchemas";
import type { AgentCommandName } from "../commandSchemas";
import type { AgentConfirmationRisk, AgentPermissionLevel } from "../types";
import { confirmationRiskForGate, getAgentToolPermissionPolicy } from "../permissionPolicy";
import { getToolDefinition } from "../surfaceRegistry";

const minimumDisclosureScopes: DisclosureRecipientDraft["allowedScopes"] = ["identity_minimum"];

export async function createManagedUserAccountAction(
  runtime: AppActionRuntime,
  input: CreateManagedUserAccountCommandInput,
  options: AppActionOptions
): Promise<AppActionResult> {
  const blocked = requiresConfirmation("create_managed_user_account", input, options);
  if (blocked) return blocked;
  const setShelterUserAccounts = requireSetter(
    "create_managed_user_account",
    runtime.setShelterUserAccounts,
    "Shelter user accounts"
  );
  if (typeof setShelterUserAccounts !== "function") return setShelterUserAccounts;

  const state = runtime.getState();
  const staff = findVerifiedStaff(input.shelter, input.staffId, state.shelterStaffAccounts ?? []);
  if (!staff) {
    return failure(
      "create_managed_user_account",
      "shelter_staff_not_verified",
      "A verified staff operator for this shelter is required."
    );
  }

  const botCheck = input.easyBotCheckStatus ?? "pending";
  if (botCheck === "pending" || (botCheck === "passed" && !clean(input.captchaToken))) {
    return failure(
      "create_managed_user_account",
      "shelter_bot_check_incomplete",
      "The shelter account bot check must be failed or passed with a captcha token before account creation."
    );
  }

  const account: ShelterUserAccount = {
    id: `user-${Date.now()}`,
    shelter: staff.shelter,
    legalName: clean(input.legalName),
    preferredName: clean(input.preferredName),
    pronouns: clean(input.pronouns),
    dateOfBirth: clean(input.dateOfBirth),
    photoAssetId: clean(input.photoAssetId),
    phone: clean(input.phone),
    email: clean(input.email),
    currentLocation: clean(input.currentLocation),
    preferredShelter: clean(input.preferredShelter),
    serviceNeeds: uniqueCleanStrings(input.serviceNeeds ?? []),
    easyBotCheckStatus: botCheck,
    captchaToken: clean(input.captchaToken),
    localPrecinctNotified: input.localPrecinctNotified ?? false,
    foundPermanentHousing: input.foundPermanentHousing ?? false,
    createdByStaffId: staff.id,
    createdAt: new Date().toISOString()
  };

  setShelterUserAccounts([...(state.shelterUserAccounts ?? []), account]);
  return success("create_managed_user_account", `Created shelter user account for ${account.legalName}.`, {
    artifactId: account.id,
    confirmation: confirmationFor("create_managed_user_account", input),
    metadata: {
      account,
      operatorStaffId: staff.id,
      stagedWithConfirmation: true
    }
  });
}

export async function createShelterStaffAccountAction(
  runtime: AppActionRuntime,
  input: CreateShelterStaffAccountCommandInput,
  options: AppActionOptions
): Promise<AppActionResult> {
  const blocked = requiresConfirmation("create_shelter_staff_account", input, options);
  if (blocked) return blocked;
  const setShelterStaffAccounts = requireSetter(
    "create_shelter_staff_account",
    runtime.setShelterStaffAccounts,
    "Shelter staff accounts"
  );
  if (typeof setShelterStaffAccounts !== "function") return setShelterStaffAccounts;

  const state = runtime.getState();
  const operator = findVerifiedStaff(input.shelter, input.operatorStaffId, state.shelterStaffAccounts ?? []);
  if (!operator) {
    return failure(
      "create_shelter_staff_account",
      "shelter_staff_not_verified",
      "A verified staff operator for this shelter is required."
    );
  }

  const account: ShelterStaffAccount = {
    id: `staff-${Date.now()}`,
    shelter: operator.shelter,
    displayName: clean(input.displayName),
    email: clean(input.email),
    verified: false,
    updatedAt: new Date().toISOString()
  };

  setShelterStaffAccounts([...(state.shelterStaffAccounts ?? []), account]);
  return success("create_shelter_staff_account", `Created unverified staff account for ${account.displayName}.`, {
    artifactId: account.id,
    confirmation: confirmationFor("create_shelter_staff_account", input),
    metadata: {
      account,
      operatorStaffId: operator.id,
      stagedWithConfirmation: true
    }
  });
}

export async function sendShelterNudgeAction(
  runtime: AppActionRuntime,
  input: SendShelterNudgeCommandInput,
  options: AppActionOptions
): Promise<AppActionResult> {
  const blocked = requiresConfirmation("send_shelter_nudge", input, options);
  if (blocked) return blocked;
  const setContactRequests = requireSetter(
    "send_shelter_nudge",
    runtime.setShelterContactRequests,
    "Shelter contact requests"
  );
  if (typeof setContactRequests !== "function") return setContactRequests;

  const state = runtime.getState();
  const staff = findVerifiedStaff(input.shelter, input.staffId, state.shelterStaffAccounts ?? []);
  if (!staff) {
    return failure(
      "send_shelter_nudge",
      "shelter_staff_not_verified",
      "A verified staff operator for this shelter is required."
    );
  }

  const contactRequests = state.shelterContactRequests ?? [];
  if (hasPendingShelterNudge(contactRequests, staff.shelter, input.userName, input.userContact)) {
    return failure(
      "send_shelter_nudge",
      "shelter_contact_request_exists",
      "A pending contact request already exists for this shelter and person."
    );
  }

  const request: ShelterContactRequest = {
    id: `shelter-request-${Date.now()}`,
    direction: "shelter_to_user",
    status: "pending",
    shelterName: staff.shelter,
    userName: clean(input.userName),
    userContact: clean(input.userContact),
    staffId: staff.id,
    staffName: staff.displayName,
    createdAt: new Date().toISOString()
  };

  setContactRequests([...contactRequests, request]);
  return success("send_shelter_nudge", `Sent contact request to ${request.userName}.`, {
    artifactId: request.id,
    confirmation: confirmationFor("send_shelter_nudge", input),
    metadata: {
      request,
      stagedWithConfirmation: true
    }
  });
}

export async function requestShelterContactAction(
  runtime: AppActionRuntime,
  input: RequestShelterContactCommandInput,
  options: AppActionOptions
): Promise<AppActionResult> {
  const blocked = requiresConfirmation("request_shelter_contact", input, options);
  if (blocked) return blocked;
  const setContactRequests = requireSetter(
    "request_shelter_contact",
    runtime.setShelterContactRequests,
    "Shelter contact requests"
  );
  if (typeof setContactRequests !== "function") return setContactRequests;

  const state = runtime.getState();
  const shelterName = clean(input.shelterName);
  const userName = clean(input.userName) || state.profile.preferredName || state.profile.legalName || "Abby Example";
  const userContact = clean(input.userContact) || state.profile.email || state.profile.phone || "abby@example.org";
  const contactRequests = state.shelterContactRequests ?? [];
  const existingPending = contactRequests.some(
    (request) =>
      request.status === "pending" &&
      normalized(request.shelterName) === normalized(shelterName) &&
      normalized(request.userContact) === normalized(userContact)
  );
  if (existingPending) {
    return failure(
      "request_shelter_contact",
      "shelter_contact_request_exists",
      "A pending contact request already exists for this shelter."
    );
  }

  const request: ShelterContactRequest = {
    id: `shelter-request-${Date.now()}`,
    direction: "user_to_shelter",
    status: "pending",
    shelterName,
    userName,
    userContact,
    createdAt: new Date().toISOString()
  };
  setContactRequests([...contactRequests, request]);
  return success("request_shelter_contact", `Requested contact with ${request.shelterName}.`, {
    artifactId: request.id,
    confirmation: confirmationFor("request_shelter_contact", input),
    metadata: {
      request,
      stagedWithConfirmation: true
    }
  });
}

export async function approveShelterContactRequestAction(
  runtime: AppActionRuntime,
  input: ShelterContactRequestDecisionCommandInput,
  options: AppActionOptions
): Promise<AppActionResult> {
  return decideShelterContactRequestAction(runtime, input, "approved", "approve_shelter_contact_request", options);
}

export async function denyShelterContactRequestAction(
  runtime: AppActionRuntime,
  input: ShelterContactRequestDecisionCommandInput,
  options: AppActionOptions
): Promise<AppActionResult> {
  return decideShelterContactRequestAction(runtime, input, "denied", "deny_shelter_contact_request", options);
}

export async function approveUserShelterRequestAction(
  runtime: AppActionRuntime,
  input: UserShelterRequestDecisionCommandInput,
  options: AppActionOptions
): Promise<AppActionResult> {
  return decideUserShelterRequestAction(runtime, input, "approved", "approve_user_shelter_request", options);
}

export async function denyUserShelterRequestAction(
  runtime: AppActionRuntime,
  input: UserShelterRequestDecisionCommandInput,
  options: AppActionOptions
): Promise<AppActionResult> {
  return decideUserShelterRequestAction(runtime, input, "denied", "deny_user_shelter_request", options);
}

export async function addShelterAsRecipientAction(
  runtime: AppActionRuntime,
  input: AddShelterAsRecipientCommandInput,
  options: AppActionOptions
): Promise<AppActionResult> {
  const blocked = requiresConfirmation("add_shelter_as_recipient", input, options);
  if (blocked) return blocked;
  const setRecipients = requireSetter("add_shelter_as_recipient", runtime.setRecipients, "Recipients");
  if (typeof setRecipients !== "function") return setRecipients;

  const state = runtime.getState();
  const recipient = shelterRecipientForName(input.shelterName, input.staffName, state.recipients);
  const existing = state.recipients.some((item) => item.id === recipient.id);
  if (!existing) {
    setRecipients([...state.recipients, recipient]);
  }

  return success(
    "add_shelter_as_recipient",
    existing ? `${recipient.displayName} is already a shelter recipient.` : `Added ${recipient.displayName} as a shelter recipient.`,
    {
      artifactId: recipient.id,
      confirmation: confirmationFor("add_shelter_as_recipient", input),
      metadata: {
        recipient,
        alreadyExists: existing,
        stagedWithConfirmation: true
      }
    }
  );
}

async function decideShelterContactRequestAction(
  runtime: AppActionRuntime,
  input: ShelterContactRequestDecisionCommandInput,
  status: "approved" | "denied",
  action: "approve_shelter_contact_request" | "deny_shelter_contact_request",
  options: AppActionOptions
): Promise<AppActionResult> {
  const blocked = requiresConfirmation(action, input, options);
  if (blocked) return blocked;
  const setContactRequests = requireSetter(action, runtime.setShelterContactRequests, "Shelter contact requests");
  if (typeof setContactRequests !== "function") return setContactRequests;
  const setRecipients = runtime.setRecipients;
  if (status === "approved" && typeof setRecipients !== "function") {
    return failure(action, "missing_app_setter", "Recipients is not writable in this app action runtime.");
  }

  const state = runtime.getState();
  const contactRequests = state.shelterContactRequests ?? [];
  const request = contactRequests.find((item) => item.id === input.requestId);
  if (!request) return failure(action, "shelter_contact_request_not_found", `Request ${input.requestId} was not found.`);
  if (request.status !== "pending") {
    return failure(action, "shelter_contact_request_not_pending", "Only pending shelter contact requests can be decided.");
  }

  const decidedAt = new Date().toISOString();
  setContactRequests(
    contactRequests.map((item) =>
      item.id === input.requestId ? { ...item, status, decidedAt } : item
    )
  );

  let recipient: DisclosureRecipientDraft | undefined;
  if (status === "approved" && typeof setRecipients === "function") {
    recipient = shelterRecipientForRequest(request, state.recipients);
    if (!state.recipients.some((item) => item.id === recipient?.id)) {
      setRecipients([...state.recipients, recipient]);
    }
  }

  return success(
    action,
    `${status === "approved" ? "Approved" : "Denied"} contact request for ${request.shelterName}.`,
    {
      artifactId: input.requestId,
      confirmation: confirmationFor(action, input),
      metadata: {
        requestId: input.requestId,
        status,
        recipient,
        reason: input.reason,
        stagedWithConfirmation: true
      }
    }
  );
}

async function decideUserShelterRequestAction(
  runtime: AppActionRuntime,
  input: UserShelterRequestDecisionCommandInput,
  status: "approved" | "denied",
  action: "approve_user_shelter_request" | "deny_user_shelter_request",
  options: AppActionOptions
): Promise<AppActionResult> {
  const blocked = requiresConfirmation(action, input, options);
  if (blocked) return blocked;
  const setContactRequests = requireSetter(action, runtime.setShelterContactRequests, "Shelter contact requests");
  if (typeof setContactRequests !== "function") return setContactRequests;
  const setRecipients = runtime.setRecipients;
  if (status === "approved" && typeof setRecipients !== "function") {
    return failure(action, "missing_app_setter", "Recipients is not writable in this app action runtime.");
  }

  const state = runtime.getState();
  const contactRequests = state.shelterContactRequests ?? [];
  const request = contactRequests.find((item) => item.id === input.requestId);
  if (!request) return failure(action, "shelter_contact_request_not_found", `Request ${input.requestId} was not found.`);
  if (request.direction !== "user_to_shelter") {
    return failure(action, "shelter_contact_request_wrong_direction", "Only user-to-shelter requests can use this action.");
  }
  if (request.status !== "pending") {
    return failure(action, "shelter_contact_request_not_pending", "Only pending shelter contact requests can be decided.");
  }

  const decidedAt = new Date().toISOString();
  setContactRequests(
    contactRequests.map((item) =>
      item.id === input.requestId ? { ...item, status, decidedAt } : item
    )
  );

  let recipient: DisclosureRecipientDraft | undefined;
  if (status === "approved" && typeof setRecipients === "function") {
    recipient = shelterRecipientForRequest(request, state.recipients);
    if (!state.recipients.some((item) => item.id === recipient?.id)) {
      setRecipients([...state.recipients, recipient]);
    }
  }

  return success(action, `${status === "approved" ? "Approved" : "Denied"} user request for ${request.shelterName}.`, {
    artifactId: input.requestId,
    confirmation: confirmationFor(action, input),
    metadata: {
      requestId: input.requestId,
      status,
      recipient,
      reason: input.reason,
      stagedWithConfirmation: true
    }
  });
}

function findVerifiedStaff(
  shelter: string,
  staffId: string,
  accounts: ShelterStaffAccount[]
): ShelterStaffAccount | undefined {
  return accounts.find(
    (account) => account.id === staffId && normalized(account.shelter) === normalized(shelter) && account.verified
  );
}

function hasPendingShelterNudge(
  requests: ShelterContactRequest[],
  shelterName: string,
  userName: string,
  userContact: string
): boolean {
  const contactKey = normalized(userContact);
  const nameKey = normalized(userName);
  return requests.some(
    (request) =>
      request.status === "pending" &&
      normalized(request.shelterName) === normalized(shelterName) &&
      (normalized(request.userContact) === contactKey || normalized(request.userName) === nameKey)
  );
}

function shelterRecipientForRequest(
  request: ShelterContactRequest,
  recipients: DisclosureRecipientDraft[]
): DisclosureRecipientDraft {
  return shelterRecipientForName(request.shelterName, request.staffName, recipients);
}

function shelterRecipientForName(
  shelterName: string,
  staffName: string | undefined,
  recipients: DisclosureRecipientDraft[]
): DisclosureRecipientDraft {
  const shelter = clean(shelterName);
  const existing = recipients.find(
    (recipient) => recipient.type === "shelter_staff" && normalized(recipient.agencyName) === normalized(shelter)
  );
  if (existing) return existing;
  return {
    id: `rec-${Date.now()}`,
    type: "shelter_staff",
    displayName: clean(staffName) || shelter,
    relationship: "Shelter",
    email: "",
    phone: "",
    agencyName: shelter,
    precinctName: "",
    verified: true,
    allowedScopes: minimumDisclosureScopes
  };
}

function uniqueCleanStrings(values: string[]): string[] {
  return Array.from(new Set(values.map(clean).filter(Boolean)));
}

function clean(value: string | undefined): string {
  return value?.trim() ?? "";
}

function normalized(value: string | undefined): string {
  return clean(value).toLowerCase();
}

function success(
  action: AgentCommandName,
  summary: string,
  extra: Omit<Extract<AppActionResult, { ok: true }>, "ok" | "action" | "summary"> = {}
): AppActionResult {
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
  extra: Omit<Extract<AppActionResult, { ok: false }>, "ok" | "action" | "errorCode" | "message"> = {}
): AppActionResult {
  return {
    ok: false,
    action,
    errorCode,
    message,
    ...extra
  };
}

function confirmationFor(action: AgentCommandName, input: unknown) {
  const tool = getToolDefinition(action);
  const policy = getAgentToolPermissionPolicy(action);
  return {
    required: tool.requiresConfirmation,
    title: tool.title,
    summary: summarizeConfirmation(action, input),
    risk: confirmationRiskForGate(policy.gate) as AgentConfirmationRisk,
    permissionLevel: tool.permissionLevel as AgentPermissionLevel,
    auditEventType: tool.auditEventType,
    details: input && typeof input === "object" ? { input, permissionGate: policy.gate, requiresAudit: policy.requiresAudit } : undefined
  };
}

function summarizeConfirmation(action: AgentCommandName, input: unknown): string {
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
  if (action === "create_managed_user_account" && isRecord(input)) {
    return `Create managed shelter user account for ${String(input.legalName ?? "")}.`;
  }
  if (action === "create_shelter_staff_account" && isRecord(input)) {
    return `Create shelter staff account for ${String(input.displayName ?? "")}.`;
  }
  if (action === "send_shelter_nudge" && isRecord(input)) {
    return `Send shelter contact request to ${String(input.userName ?? "the selected person")}.`;
  }
  if (
    (action === "approve_user_shelter_request" || action === "deny_user_shelter_request") &&
    isRecord(input)
  ) {
    return `${action === "approve_user_shelter_request" ? "Approve" : "Deny"} user shelter request ${String(
      input.requestId ?? ""
    )}.`;
  }
  if (action === "add_shelter_as_recipient" && isRecord(input)) {
    return `Add ${String(input.shelterName ?? "the selected shelter")} as a shelter recipient.`;
  }
  return getToolDefinition(action).title;
}

function requiresConfirmation(action: AgentCommandName, input: unknown, options: AppActionOptions): AppActionResult | undefined {
  const confirmation = confirmationFor(action, input);
  if (!confirmation.required || options.confirmed) return undefined;
  return failure(action, "confirmation_required", confirmation.summary, { confirmation });
}

function requireSetter<T>(
  action: AgentCommandName,
  setter: ((value: T) => void) | undefined,
  label: string
): ((value: T) => void) | AppActionResult {
  if (setter) return setter;
  return failure(action, "missing_app_setter", `${label} is not writable in this app action runtime.`);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
