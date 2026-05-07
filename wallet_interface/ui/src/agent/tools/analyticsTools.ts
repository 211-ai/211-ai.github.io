import type { AnalyticsStudy } from "../../models/abby";
import { analyticsStudies } from "../../services/mockAbbyService";
import {
  createWalletAnalyticsConsent,
  listAnalyticsTemplates,
  listWalletAnalyticsConsents
} from "../../services/walletApi";
import type {
  AppActionConfirmationMetadata,
  AppActionFailure,
  AppActionOptions,
  AppActionResult,
  AppActionRuntime,
  AppActionSuccess
} from "../../app/appActions";
import type {
  AgentCommandName,
  AnalyticsStudyReferenceCommandInput,
  SubmitAnalyticsConsentCommandInput
} from "../commandSchemas";
import type { AgentConfirmationRisk, AgentPermissionLevel } from "../types";
import { confirmationRiskForGate, getAgentToolPermissionPolicy } from "../permissionPolicy";
import { getToolDefinition } from "../surfaceRegistry";

export async function selectAnalyticsStudyAction(
  runtime: AppActionRuntime,
  input: AnalyticsStudyReferenceCommandInput
): Promise<AppActionResult> {
  return setAnalyticsStudySelection(runtime, input, true);
}

export async function unselectAnalyticsStudyAction(
  runtime: AppActionRuntime,
  input: AnalyticsStudyReferenceCommandInput
): Promise<AppActionResult> {
  return setAnalyticsStudySelection(runtime, input, false);
}

export async function explainAnalyticsPrivacyBudgetAction(
  runtime: AppActionRuntime,
  input: AnalyticsStudyReferenceCommandInput
): Promise<AppActionResult> {
  const studies = await loadAnalyticsStudies(runtime);
  const studyId = input.studyId?.trim();
  const selectedStudy = studyId ? findStudy(studies, studyId) : undefined;
  const selectedStudies = studyId ? (selectedStudy ? [selectedStudy] : []) : studies;
  if (studyId && selectedStudies.length === 0) {
    return failure("explain_analytics_privacy_budget", "analytics_study_not_found", `Study ${studyId} was not found.`);
  }

  const summaries = selectedStudies.map(formatPrivacyBudgetSummary);
  return success(
    "explain_analytics_privacy_budget",
    summaries.length
      ? summaries.join(" ")
      : "No analytics studies are available. Privacy budgets limit aggregate releases and do not expose names, contact details, exact locations, files, or private notes.",
    {
      metadata: {
        studies: selectedStudies.map(summarizeStudy),
        rawDocumentsExposed: false,
        privateNotesExposed: false
      }
    }
  );
}

export async function submitAnalyticsConsentAction(
  runtime: AppActionRuntime,
  input: SubmitAnalyticsConsentCommandInput,
  options: AppActionOptions
): Promise<AppActionResult> {
  const blocked = requiresConfirmation("submit_analytics_consent", input, options);
  if (blocked) return blocked;

  const studies = await loadAnalyticsStudies(runtime);
  const study = findStudy(studies, input.studyId);
  if (!study) {
    return failure("submit_analytics_consent", "analytics_study_not_found", `Study ${input.studyId} was not found.`, {
      confirmation: confirmationFor("submit_analytics_consent", input)
    });
  }

  try {
    const consent =
      runtime.walletApiConfig?.actorDid && !input.stageOnly
        ? await createWalletAnalyticsConsent(runtime.walletApiConfig, study.id, input.expiresAt)
        : createStagedConsent(study, input.expiresAt);

    runtime.setAnalyticsOptIn?.({ ...(runtime.getState().analyticsOptIn ?? {}), [study.id]: true });
    await runtime.refreshWalletAuditEvents?.().catch(() => undefined);
    return success("submit_analytics_consent", `Staged analytics consent for ${study.title}.`, {
      artifactId: consent.id,
      confirmation: confirmationFor("submit_analytics_consent", input),
      metadata: {
        consent,
        study: summarizeStudy(study),
        rawDocumentsExposed: false,
        privateNotesExposed: false,
        stagedOnly: input.stageOnly === true || !runtime.walletApiConfig?.actorDid
      }
    });
  } catch {
    return failure("submit_analytics_consent", "analytics_consent_failed", "Analytics consent submission failed.", {
      retryable: true,
      confirmation: confirmationFor("submit_analytics_consent", input)
    });
  }
}

async function setAnalyticsStudySelection(
  runtime: AppActionRuntime,
  input: AnalyticsStudyReferenceCommandInput,
  selected: boolean
): Promise<AppActionResult> {
  const action = selected ? "select_analytics_study" : "unselect_analytics_study";
  const setAnalyticsOptIn = requireSetter(action, runtime.setAnalyticsOptIn, "Analytics consent staging");
  if (typeof setAnalyticsOptIn !== "function") return setAnalyticsOptIn;

  const studies = await loadAnalyticsStudies(runtime);
  const studyId = input.studyId?.trim();
  if (!studyId) return failure(action, "analytics_study_required", "An analytics study ID is required.");
  const study = findStudy(studies, studyId);
  if (!study) {
    return failure(action, "analytics_study_not_found", `Study ${studyId} was not found.`);
  }

  setAnalyticsOptIn({ ...(runtime.getState().analyticsOptIn ?? {}), [study.id]: selected });
  return success(action, `${selected ? "Selected" : "Unselected"} ${study.title} for staged analytics consent.`, {
    artifactId: study.id,
    metadata: {
      study: summarizeStudy(study),
      selected,
      rawDocumentsExposed: false,
      privateNotesExposed: false
    }
  });
}

async function loadAnalyticsStudies(runtime: AppActionRuntime): Promise<AnalyticsStudy[]> {
  const stateStudies = runtime.getState().analyticsStudies;
  if (stateStudies?.length) return stateStudies;
  if (!runtime.walletApiConfig) return analyticsStudies;
  try {
    const templates = await listAnalyticsTemplates({ apiBaseUrl: runtime.walletApiConfig.apiBaseUrl });
    const consents = await listWalletAnalyticsConsents(runtime.walletApiConfig).catch(() => []);
    const consentedTemplateIds = new Set(
      consents.filter((consent) => consent.status === "active").map((consent) => consent.templateId)
    );
    return templates.map((study) => ({
      ...study,
      status: consentedTemplateIds.has(study.id) ? "consented" : study.status
    }));
  } catch {
    return analyticsStudies;
  }
}

function findStudy(studies: AnalyticsStudy[], studyId: string): AnalyticsStudy | undefined {
  const normalized = studyId.trim().toLowerCase();
  return studies.find((study) => study.id.toLowerCase() === normalized || study.title.toLowerCase() === normalized);
}

function formatPrivacyBudgetSummary(study: AnalyticsStudy): string {
  const remaining = Math.max(0, study.epsilonBudget - study.spentBudget);
  const fieldSummary = study.fields.length ? study.fields.map(formatField).join(", ") : "no derived fields";
  return `${study.title} has ${remaining.toFixed(2)} of ${study.epsilonBudget.toFixed(
    2
  )} epsilon remaining, with ${study.spentBudget.toFixed(2)} already spent. It only contributes ${fieldSummary} after the group reaches at least ${study.minCohortSize} people, and it does not reveal names, contact details, exact locations, files, or private notes.`;
}

function summarizeStudy(study: AnalyticsStudy): Record<string, unknown> {
  return {
    id: study.id,
    title: study.title,
    purpose: study.purpose,
    fields: study.fields.map(formatField),
    minCohortSize: study.minCohortSize,
    epsilonBudget: study.epsilonBudget,
    spentBudget: study.spentBudget,
    remainingBudget: Math.max(0, study.epsilonBudget - study.spentBudget),
    status: study.status
  };
}

function createStagedConsent(study: AnalyticsStudy, expiresAt: string | undefined) {
  return {
    id: `analytics-consent-staged-${study.id}-${Date.now()}`,
    templateId: study.id,
    fields: [...study.fields],
    status: "staged",
    createdAt: "Just now",
    expiresAt
  };
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
  if (action === "submit_analytics_consent" && isRecord(input)) {
    return `Submit analytics consent for ${String(input.studyId ?? "")}.`;
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

function formatField(field: string): string {
  return field
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}
