import type { CheckInChannel, RegistrationProfileDraft } from "../../models/abby";
import type {
  AppActionConfirmationMetadata,
  AppActionFailure,
  AppActionOptions,
  AppActionResult,
  AppActionRuntime,
  AppActionSuccess
} from "../../app/appActions";
import type { AgentCommandName, UpdateRegistrationDraftCommandInput } from "../commandSchemas";
import type { AgentConfirmationRisk, AgentPermissionLevel } from "../types";
import { confirmationRiskForGate, getAgentToolPermissionPolicy } from "../permissionPolicy";
import { getToolDefinition } from "../surfaceRegistry";

type RegistrationDraftField = keyof UpdateRegistrationDraftCommandInput;

const registrationDraftFields = [
  "preferredName",
  "pronouns",
  "phone",
  "email",
  "currentLocation",
  "shelterAffiliation",
  "serviceNeeds",
  "preferredCheckInChannels"
] as const satisfies readonly RegistrationDraftField[];

export async function updateRegistrationDraftAction(
  runtime: AppActionRuntime,
  input: UpdateRegistrationDraftCommandInput,
  options: AppActionOptions
): Promise<AppActionResult> {
  const blocked = requiresConfirmation("update_registration_draft", input, options);
  if (blocked) return blocked;
  const setProfile = requireSetter("update_registration_draft", runtime.setProfile, "Registration profile");
  if (typeof setProfile !== "function") return setProfile;

  const state = runtime.getState();
  const patch = buildRegistrationPatch(input);
  const changedFields = changedRegistrationFields(state.profile, patch);
  if (!changedFields.length) {
    return failure("update_registration_draft", "no_registration_changes", "No registration draft changes were provided.", {
      confirmation: confirmationFor("update_registration_draft", input)
    });
  }

  setProfile({ ...state.profile, ...patch });
  return success("update_registration_draft", summarizeRegistrationUpdate(changedFields), {
    confirmation: confirmationFor("update_registration_draft", input),
    metadata: {
      changedFields,
      privateValuesExposed: false,
      restrictedFieldsIgnored: ["legalName", "dateOfBirth", "photoAssetId", "easyBotCheckStatus", "captchaToken"]
    }
  });
}

function buildRegistrationPatch(input: UpdateRegistrationDraftCommandInput): Partial<RegistrationProfileDraft> {
  const patch: Partial<RegistrationProfileDraft> = {};
  if (input.preferredName !== undefined) patch.preferredName = clean(input.preferredName);
  if (input.pronouns !== undefined) patch.pronouns = clean(input.pronouns);
  if (input.phone !== undefined) patch.phone = clean(input.phone);
  if (input.email !== undefined) patch.email = clean(input.email);
  if (input.currentLocation !== undefined) patch.currentLocation = clean(input.currentLocation);
  if (input.shelterAffiliation !== undefined) patch.shelterAffiliation = clean(input.shelterAffiliation);
  if (input.serviceNeeds !== undefined) patch.serviceNeeds = uniqueCleanStrings(input.serviceNeeds);
  if (input.preferredCheckInChannels !== undefined) {
    patch.preferredCheckInChannels = uniqueChannels(input.preferredCheckInChannels);
  }
  return patch;
}

function changedRegistrationFields(
  profile: RegistrationProfileDraft,
  patch: Partial<RegistrationProfileDraft>
): RegistrationDraftField[] {
  return registrationDraftFields.filter((field) => {
    if (!(field in patch)) return false;
    return !sameValue(profile[field], patch[field]);
  });
}

function summarizeRegistrationUpdate(changedFields: RegistrationDraftField[]): string {
  return `Updated registration draft field${plural(changedFields.length)}: ${changedFields.join(", ")}.`;
}

function uniqueChannels(channels: CheckInChannel[]): CheckInChannel[] {
  return Array.from(new Set(channels));
}

function uniqueCleanStrings(values: string[]): string[] {
  return Array.from(new Set(values.map(clean).filter(Boolean)));
}

function sameValue(left: unknown, right: unknown): boolean {
  if (Array.isArray(left) && Array.isArray(right)) {
    return left.length === right.length && left.every((item, index) => item === right[index]);
  }
  return left === right;
}

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

function requiresConfirmation(
  action: AgentCommandName,
  input: unknown,
  options: AppActionOptions
): AppActionFailure | undefined {
  const confirmation = confirmationFor(action, input);
  if (!confirmation.required || options.confirmed) return undefined;
  return failure(action, "confirmation_required", confirmation.summary, { confirmation });
}

function confirmationFor(action: AgentCommandName, input: unknown): AppActionConfirmationMetadata {
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
  if (action === "update_registration_draft" && isRecord(input)) {
    const fields = registrationDraftFields.filter((field) => field in input);
    return fields.length
      ? `Update registration draft fields: ${fields.join(", ")}.`
      : "Update private registration profile fields.";
  }
  return getToolDefinition(action).title;
}

function requireSetter<T>(
  action: AgentCommandName,
  setter: ((value: T) => void) | undefined,
  label: string
): ((value: T) => void) | AppActionFailure {
  if (setter) return setter;
  return failure(action, "missing_app_setter", `${label} is not writable in this app action runtime.`);
}

function clean(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

function plural(count: number): string {
  return count === 1 ? "" : "s";
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}
