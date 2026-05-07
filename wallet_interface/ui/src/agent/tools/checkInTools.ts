import type { CheckInChannel, CheckInPolicyDraft } from "../../models/abby";
import type {
  AppActionConfirmationMetadata,
  AppActionFailure,
  AppActionOptions,
  AppActionResult,
  AppActionRuntime,
  AppActionSuccess
} from "../../app/appActions";
import type { AgentCommandName, UpdateCheckInPolicyCommandInput } from "../commandSchemas";
import type { AgentConfirmationRisk, AgentPermissionLevel } from "../types";
import { confirmationRiskForGate, getAgentToolPermissionPolicy } from "../permissionPolicy";
import { getToolDefinition } from "../surfaceRegistry";

type CheckInPolicyField = keyof UpdateCheckInPolicyCommandInput;

const checkInPolicyFields = [
  "intervalDays",
  "reminderChannels",
  "gracePeriodHours",
  "escalationEnabled"
] as const satisfies readonly CheckInPolicyField[];

export async function updateCheckInPolicyAction(
  runtime: AppActionRuntime,
  input: UpdateCheckInPolicyCommandInput,
  options: AppActionOptions
): Promise<AppActionResult> {
  const blocked = requiresConfirmation("update_check_in_policy", input, options);
  if (blocked) return blocked;
  const setPolicy = requireSetter("update_check_in_policy", runtime.setPolicy, "Check-in policy");
  if (typeof setPolicy !== "function") return setPolicy;

  const state = runtime.getState();
  const patch = buildCheckInPolicyPatch(input);
  const changedFields = changedPolicyFields(state.policy, patch);
  if (!changedFields.length) {
    return failure("update_check_in_policy", "no_check_in_policy_changes", "No check-in policy changes were provided.", {
      confirmation: confirmationFor("update_check_in_policy", input)
    });
  }

  setPolicy({ ...state.policy, ...patch });
  return success("update_check_in_policy", summarizeCheckInPolicyUpdate(changedFields), {
    confirmation: confirmationFor("update_check_in_policy", input),
    metadata: {
      changedFields,
      highImpactChanges: buildHighImpactChangeSummary(state.policy, patch),
      privateValuesExposed: false
    }
  });
}

function buildCheckInPolicyPatch(input: UpdateCheckInPolicyCommandInput): Partial<CheckInPolicyDraft> {
  const patch: Partial<CheckInPolicyDraft> = {};
  if (input.intervalDays !== undefined) patch.intervalDays = clampWholeNumber(input.intervalDays, 1, 30);
  if (input.reminderChannels !== undefined) patch.reminderChannels = uniqueChannels(input.reminderChannels);
  if (input.gracePeriodHours !== undefined) patch.gracePeriodHours = clampWholeNumber(input.gracePeriodHours, 0, 168);
  if (input.escalationEnabled !== undefined) patch.escalationEnabled = input.escalationEnabled;
  return patch;
}

function changedPolicyFields(policy: CheckInPolicyDraft, patch: Partial<CheckInPolicyDraft>): CheckInPolicyField[] {
  return checkInPolicyFields.filter((field) => {
    if (!(field in patch)) return false;
    return !sameValue(policy[field], patch[field]);
  });
}

function buildHighImpactChangeSummary(
  policy: CheckInPolicyDraft,
  patch: Partial<CheckInPolicyDraft>
): Record<string, unknown> {
  const nextReminderChannels = patch.reminderChannels ?? policy.reminderChannels;
  const removedReminderChannels = policy.reminderChannels.filter((channel) => !nextReminderChannels.includes(channel));
  const nextEscalationEnabled = patch.escalationEnabled ?? policy.escalationEnabled;
  const escalationChanged = nextEscalationEnabled !== policy.escalationEnabled;
  const intervalIncreased =
    patch.intervalDays !== undefined && patch.intervalDays > policy.intervalDays
      ? { from: policy.intervalDays, to: patch.intervalDays }
      : undefined;
  const gracePeriodIncreased =
    patch.gracePeriodHours !== undefined && patch.gracePeriodHours > policy.gracePeriodHours
      ? { from: policy.gracePeriodHours, to: patch.gracePeriodHours }
      : undefined;

  return {
    reminderChannelsRemoved: removedReminderChannels,
    allReminderChannelsRemoved: policy.reminderChannels.length > 0 && nextReminderChannels.length === 0,
    escalationChanged,
    escalationDisabled: policy.escalationEnabled && !nextEscalationEnabled,
    intervalIncreased,
    gracePeriodIncreased,
    confirmationRequired: true
  };
}

function summarizeCheckInPolicyUpdate(changedFields: CheckInPolicyField[]): string {
  return `Updated check-in policy field${plural(changedFields.length)}: ${changedFields.join(", ")}.`;
}

function uniqueChannels(channels: CheckInChannel[]): CheckInChannel[] {
  return Array.from(new Set(channels));
}

function clampWholeNumber(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, Math.round(value)));
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
  if (action === "update_check_in_policy" && isRecord(input)) {
    const fields = checkInPolicyFields.filter((field) => field in input);
    return fields.length
      ? `Update check-in settings: ${fields.join(", ")}.`
      : "Update check-in reminder and escalation settings.";
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

function plural(count: number): string {
  return count === 1 ? "" : "s";
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}
