import type {
  DisclosureDataScope,
  DisclosureRecipientDraft,
  ShelterContactRequest
} from "../../models/abby";
import type { AppActionOptions, AppActionResult, AppActionRuntime } from "../../app/appActions";
import type {
  AddRecipientCommandInput,
  EditRecipientCommandInput,
  RemoveRecipientCommandInput,
  RequestShelterContactCommandInput,
  ShelterContactRequestDecisionCommandInput
} from "../commandSchemas";
import type { AgentCommandName } from "../commandSchemas";
import type { AgentConfirmationRisk, AgentPermissionLevel } from "../types";
import { confirmationRiskForGate, getAgentToolPermissionPolicy } from "../permissionPolicy";
import { getToolDefinition } from "../surfaceRegistry";

const minimumDisclosureScopes: DisclosureDataScope[] = ["identity_minimum"];

export async function addRecipientAction(
  runtime: AppActionRuntime,
  input: AddRecipientCommandInput,
  options: AppActionOptions
): Promise<AppActionResult> {
  const blocked = requiresConfirmation("add_recipient", input, options);
  if (blocked) return blocked;
  const setRecipients = requireSetter("add_recipient", runtime.setRecipients, "Recipients");
  if (typeof setRecipients !== "function") return setRecipients;

  const state = runtime.getState();
  const recipient = buildRecipient(input);
  setRecipients([...state.recipients, recipient]);
  return success("add_recipient", `Added ${recipient.displayName} to contacts.`, {
    artifactId: recipient.id,
    confirmation: confirmationFor("add_recipient", input),
    metadata: {
      recipient,
      disclosure: buildDisclosureMetadata([], recipient.allowedScopes)
    }
  });
}

export async function editRecipientAction(
  runtime: AppActionRuntime,
  input: EditRecipientCommandInput,
  options: AppActionOptions
): Promise<AppActionResult> {
  const blocked = requiresConfirmation("edit_recipient", input, options);
  if (blocked) return blocked;
  const setRecipients = requireSetter("edit_recipient", runtime.setRecipients, "Recipients");
  if (typeof setRecipients !== "function") return setRecipients;

  const state = runtime.getState();
  const recipient = state.recipients.find((item) => item.id === input.recipientId);
  if (!recipient) return failure("edit_recipient", "recipient_not_found", `Recipient ${input.recipientId} was not found.`);

  const nextRecipient = mergeRecipient(recipient, input);
  setRecipients(state.recipients.map((item) => (item.id === input.recipientId ? nextRecipient : item)));
  return success("edit_recipient", `Updated ${nextRecipient.displayName}.`, {
    artifactId: input.recipientId,
    confirmation: confirmationFor("edit_recipient", input),
    metadata: {
      recipient: nextRecipient,
      disclosure: buildDisclosureMetadata(recipient.allowedScopes, nextRecipient.allowedScopes)
    }
  });
}

export async function removeRecipientAction(
  runtime: AppActionRuntime,
  input: RemoveRecipientCommandInput,
  options: AppActionOptions
): Promise<AppActionResult> {
  const blocked = requiresConfirmation("remove_recipient", input, options);
  if (blocked) return blocked;
  const setRecipients = requireSetter("remove_recipient", runtime.setRecipients, "Recipients");
  if (typeof setRecipients !== "function") return setRecipients;

  const state = runtime.getState();
  const recipient = state.recipients.find((item) => item.id === input.recipientId);
  if (!recipient) return failure("remove_recipient", "recipient_not_found", `Recipient ${input.recipientId} was not found.`);

  setRecipients(state.recipients.filter((item) => item.id !== input.recipientId));
  return success("remove_recipient", `Removed ${recipient.displayName} from contacts.`, {
    artifactId: input.recipientId,
    confirmation: confirmationFor("remove_recipient", input),
    metadata: {
      recipientId: input.recipientId,
      recipientName: recipient.displayName,
      reason: input.reason
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
  const userName = clean(input.userName) || state.profile.preferredName || state.profile.legalName || "Abby Example";
  const userContact = clean(input.userContact) || state.profile.email || state.profile.phone || "abby@example.org";
  const contactRequests = state.shelterContactRequests ?? [];
  const existingPending = contactRequests.some(
    (request) =>
      request.status === "pending" &&
      request.shelterName === input.shelterName &&
      request.userContact.trim().toLowerCase() === userContact.trim().toLowerCase()
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
    shelterName: input.shelterName.trim(),
    userName,
    userContact,
    createdAt: new Date().toISOString()
  };
  setContactRequests([...contactRequests, request]);
  return success("request_shelter_contact", `Requested contact with ${request.shelterName}.`, {
    artifactId: request.id,
    confirmation: confirmationFor("request_shelter_contact", input),
    metadata: { request }
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
        reason: input.reason
      }
    }
  );
}

function buildRecipient(input: AddRecipientCommandInput): DisclosureRecipientDraft {
  return {
    id: `rec-${Date.now()}`,
    type: input.type ?? "emergency_contact",
    displayName: input.displayName.trim(),
    relationship: clean(input.relationship),
    email: clean(input.email),
    phone: clean(input.phone),
    agencyName: clean(input.agencyName),
    precinctName: clean(input.precinctName),
    verified: input.verified ?? false,
    allowedScopes: uniqueScopes(input.allowedScopes ?? minimumDisclosureScopes)
  };
}

function mergeRecipient(
  recipient: DisclosureRecipientDraft,
  input: EditRecipientCommandInput
): DisclosureRecipientDraft {
  return {
    ...recipient,
    type: input.type ?? recipient.type,
    displayName: clean(input.displayName) || recipient.displayName,
    relationship: input.relationship === undefined ? recipient.relationship : clean(input.relationship),
    email: input.email === undefined ? recipient.email : clean(input.email),
    phone: input.phone === undefined ? recipient.phone : clean(input.phone),
    agencyName: input.agencyName === undefined ? recipient.agencyName : clean(input.agencyName),
    precinctName: input.precinctName === undefined ? recipient.precinctName : clean(input.precinctName),
    verified: input.verified ?? recipient.verified,
    allowedScopes: input.allowedScopes === undefined ? recipient.allowedScopes : uniqueScopes(input.allowedScopes)
  };
}

function shelterRecipientForRequest(
  request: ShelterContactRequest,
  recipients: DisclosureRecipientDraft[]
): DisclosureRecipientDraft {
  const existing = recipients.find(
    (recipient) => recipient.type === "shelter_staff" && recipient.agencyName === request.shelterName
  );
  if (existing) return existing;
  return {
    id: `rec-${Date.now()}`,
    type: "shelter_staff",
    displayName: request.staffName || request.shelterName,
    relationship: "Shelter",
    email: "",
    phone: "",
    agencyName: request.shelterName,
    precinctName: "",
    verified: true,
    allowedScopes: minimumDisclosureScopes
  };
}

function buildDisclosureMetadata(currentScopes: DisclosureDataScope[], nextScopes: DisclosureDataScope[]) {
  const current = new Set(currentScopes);
  const next = new Set(nextScopes);
  const added = nextScopes.filter((scope) => !current.has(scope));
  const removed = currentScopes.filter((scope) => !next.has(scope));
  return {
    added,
    removed,
    expanded: added.length > 0,
    reduced: removed.length > 0
  };
}

function uniqueScopes(scopes: string[]): DisclosureDataScope[] {
  return Array.from(new Set(scopes)) as DisclosureDataScope[];
}

function clean(value: string | undefined): string {
  return value?.trim() ?? "";
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
