import type { SavedService, ServiceInteractionEvent, ServicePlan } from "../../models/abby";
import {
  createWalletServiceInteraction,
  createWalletServicePlan,
  listWalletServicePlans,
  saveWalletService,
  updateWalletServicePlan
} from "../../services/walletApi";
import { searchServiceNavigation } from "../serviceNavigationAgent";
import type { AppActionOptions, AppActionResult, AppActionRuntime, AppActionSuccess } from "../../app/appActions";
import type {
  AddServicePlanChecklistItemCommandInput,
  AgentCommandName,
  CreateServicePlanCommandInput,
  RecordServiceInteractionCommandInput,
  SaveServiceCommandInput,
  SetServicePlanReminderCommandInput
} from "../commandSchemas";
import type { AgentConfirmationRisk, AgentPermissionLevel } from "../types";
import { confirmationRiskForGate, getAgentToolPermissionPolicy } from "../permissionPolicy";
import { getToolDefinition } from "../surfaceRegistry";

type ServiceActionName =
  | "save_service"
  | "create_service_plan"
  | "add_service_plan_checklist_item"
  | "set_service_plan_reminder"
  | "record_service_interaction";

interface ServiceReference {
  serviceDocId: string;
  sourceContentCid: string;
  sourcePageCid: string;
  title: string;
  providerName: string;
  programName: string;
  sourceUrl: string;
}

export async function saveServiceAction(
  runtime: AppActionRuntime,
  input: SaveServiceCommandInput,
  options: AppActionOptions
): Promise<AppActionResult> {
  const blocked = requiresConfirmation("save_service", input, options);
  if (blocked) return blocked;
  const reference = await resolveServiceReference(input.serviceId, input);

  try {
    const saved =
      runtime.walletApiConfig?.actorDid
        ? await saveWalletService(runtime.walletApiConfig, {
            serviceDocId: reference.serviceDocId,
            sourceContentCid: reference.sourceContentCid,
            sourcePageCid: reference.sourcePageCid,
            title: reference.title,
            providerName: reference.providerName,
            programName: reference.programName,
            sourceUrl: reference.sourceUrl,
            label: input.label || reference.title,
            reason: input.reason || input.note || "",
            priority: input.priority || "normal",
            metadata: input.note ? { agent_note_present: true } : {}
          })
        : createStagedSavedService(runtime, input, reference);

    upsertSavedService(runtime, saved);
    await runtime.refreshWalletAuditEvents?.().catch(() => undefined);
    return success("save_service", `Saved service ${reference.serviceDocId}.`, {
      artifactId: saved.saved_service_id,
      confirmation: confirmationFor("save_service", input),
      metadata: {
        savedService: saved,
        stagedOnly: !runtime.walletApiConfig?.actorDid,
        privateNoteStoredByRecordId: Boolean(saved.private_notes_record_id),
        rawPrivateNoteExposed: false
      }
    });
  } catch {
    return failure("save_service", "service_save_failed", "Service save failed.", {
      retryable: true,
      confirmation: confirmationFor("save_service", input)
    });
  }
}

export async function createServicePlanAction(
  runtime: AppActionRuntime,
  input: CreateServicePlanCommandInput,
  options: AppActionOptions
): Promise<AppActionResult> {
  const blocked = requiresConfirmation("create_service_plan", input, options);
  if (blocked) return blocked;
  const reference = await resolveServiceReference(input.serviceId, input);

  try {
    const plan =
      runtime.walletApiConfig?.actorDid
        ? await createWalletServicePlan(runtime.walletApiConfig, {
            serviceDocId: reference.serviceDocId,
            sourceContentCid: reference.sourceContentCid,
            sourcePageCid: reference.sourcePageCid,
            serviceTitle: reference.title,
            providerName: reference.providerName,
            goal: input.goal,
            steps: cleanList(input.steps),
            documentsNeeded: cleanList(input.documentsNeeded),
            questionsToAsk: cleanList(input.questionsToAsk),
            appointmentAt: clean(input.appointmentAt),
            reminderAt: clean(input.reminderAt),
            travelTarget: clean(input.travelTarget),
            assignedWorkerRecipientId: clean(input.assignedWorkerRecipientId)
          })
        : createStagedServicePlan(runtime, input, reference);

    upsertServicePlan(runtime, plan);
    await runtime.refreshWalletAuditEvents?.().catch(() => undefined);
    return success("create_service_plan", `Created a service plan for ${reference.serviceDocId}.`, {
      artifactId: plan.plan_id,
      confirmation: confirmationFor("create_service_plan", input),
      metadata: {
        plan,
        checklistItemCount: plan.steps.length + plan.documents_needed.length + plan.questions_to_ask.length,
        reminderSet: Boolean(plan.reminder_at),
        stagedOnly: !runtime.walletApiConfig?.actorDid,
        rawPrivateNoteExposed: false
      }
    });
  } catch {
    return failure("create_service_plan", "service_plan_create_failed", "Service plan creation failed.", {
      retryable: true,
      confirmation: confirmationFor("create_service_plan", input)
    });
  }
}

export async function addServicePlanChecklistItemAction(
  runtime: AppActionRuntime,
  input: AddServicePlanChecklistItemCommandInput,
  options: AppActionOptions
): Promise<AppActionResult> {
  const blocked = requiresConfirmation("add_service_plan_checklist_item", input, options);
  if (blocked) return blocked;
  const plan = await findServicePlan(runtime, input.planId);
  if (!plan) return failure("add_service_plan_checklist_item", "service_plan_not_found", `Plan ${input.planId} was not found.`);

  const nextPlan = withChecklistItem(plan, input);
  return persistPlanUpdate(runtime, "add_service_plan_checklist_item", input, nextPlan, `Added checklist item to ${plan.plan_id}.`);
}

export async function setServicePlanReminderAction(
  runtime: AppActionRuntime,
  input: SetServicePlanReminderCommandInput,
  options: AppActionOptions
): Promise<AppActionResult> {
  const blocked = requiresConfirmation("set_service_plan_reminder", input, options);
  if (blocked) return blocked;
  const plan = await findServicePlan(runtime, input.planId);
  if (!plan) return failure("set_service_plan_reminder", "service_plan_not_found", `Plan ${input.planId} was not found.`);

  const nextPlan: ServicePlan = {
    ...plan,
    reminder_at: input.reminderAt.trim(),
    appointment_at: input.appointmentAt === undefined ? plan.appointment_at : clean(input.appointmentAt),
    updated_at: new Date().toISOString()
  };
  return persistPlanUpdate(runtime, "set_service_plan_reminder", input, nextPlan, `Set reminder for ${plan.plan_id}.`);
}

export async function recordServiceInteractionAction(
  runtime: AppActionRuntime,
  input: RecordServiceInteractionCommandInput,
  options: AppActionOptions
): Promise<AppActionResult> {
  const blocked = requiresConfirmation("record_service_interaction", input, options);
  if (blocked) return blocked;
  const reference = await resolveServiceReference(input.serviceId, input);

  try {
    const interaction =
      runtime.walletApiConfig?.actorDid
        ? await createWalletServiceInteraction(runtime.walletApiConfig, {
            serviceDocId: reference.serviceDocId,
            sourceContentCid: reference.sourceContentCid,
            sourcePageCid: reference.sourcePageCid,
            providerName: input.providerName || reference.providerName,
            programName: input.programName || reference.programName,
            interactionType: input.interactionType,
            channel: input.channel,
            counterpartyName: input.counterpartyName,
            counterpartyContact: input.counterpartyContact,
            timestamp: input.timestamp,
            status: input.status,
            outcome: input.outcome,
            notesRecordId: input.notesRecordId,
            nextAction: input.nextAction,
            nextFollowUpAt: input.nextFollowUpAt,
            sourceActionUrl: input.sourceActionUrl || reference.sourceUrl,
            relatedGrantIds: input.relatedGrantIds,
            relatedRecordIds: input.relatedRecordIds,
            privacyLevel: input.privacyLevel || "private",
            metadata: { recorded_by: "agent" }
          })
        : createStagedServiceInteraction(runtime, input, reference);

    upsertServiceInteraction(runtime, interaction);
    await runtime.refreshWalletAuditEvents?.().catch(() => undefined);
    return success("record_service_interaction", `Recorded service interaction for ${reference.serviceDocId}.`, {
      artifactId: interaction.interaction_id,
      confirmation: confirmationFor("record_service_interaction", input),
      metadata: {
        interaction,
        stagedOnly: !runtime.walletApiConfig?.actorDid,
        rawPrivateNoteExposed: false
      }
    });
  } catch {
    return failure("record_service_interaction", "service_interaction_create_failed", "Service interaction recording failed.", {
      retryable: true,
      confirmation: confirmationFor("record_service_interaction", input)
    });
  }
}

async function persistPlanUpdate(
  runtime: AppActionRuntime,
  action: Extract<ServiceActionName, "add_service_plan_checklist_item" | "set_service_plan_reminder">,
  input: AddServicePlanChecklistItemCommandInput | SetServicePlanReminderCommandInput,
  nextPlan: ServicePlan,
  summary: string
): Promise<AppActionResult> {
  try {
    const plan =
      runtime.walletApiConfig?.actorDid
        ? await updateWalletServicePlan(runtime.walletApiConfig, nextPlan.plan_id, {
            steps: nextPlan.steps,
            documentsNeeded: nextPlan.documents_needed,
            questionsToAsk: nextPlan.questions_to_ask,
            appointmentAt: nextPlan.appointment_at,
            reminderAt: nextPlan.reminder_at
          })
        : nextPlan;
    upsertServicePlan(runtime, plan);
    await runtime.refreshWalletAuditEvents?.().catch(() => undefined);
    return success(action, summary, {
      artifactId: plan.plan_id,
      confirmation: confirmationFor(action, input),
      metadata: {
        plan,
        reminderSet: Boolean(plan.reminder_at),
        stagedOnly: !runtime.walletApiConfig?.actorDid,
        rawPrivateNoteExposed: false
      }
    });
  } catch {
    return failure(action, "service_plan_update_failed", "Service plan update failed.", {
      retryable: true,
      confirmation: confirmationFor(action, input)
    });
  }
}

async function findServicePlan(runtime: AppActionRuntime, planId: string): Promise<ServicePlan | undefined> {
  const id = planId.trim();
  const statePlan = runtime.getState().servicePlans?.find((plan) => plan.plan_id === id);
  if (statePlan) return statePlan;
  if (!runtime.walletApiConfig) return undefined;
  try {
    return (await listWalletServicePlans(runtime.walletApiConfig)).find((plan) => plan.plan_id === id);
  } catch {
    return undefined;
  }
}

function withChecklistItem(plan: ServicePlan, input: AddServicePlanChecklistItemCommandInput): ServicePlan {
  const item = input.item.trim();
  const current = plan[input.checklist];
  return {
    ...plan,
    [input.checklist]: current.includes(item) ? current : [...current, item],
    updated_at: new Date().toISOString()
  };
}

async function resolveServiceReference(
  serviceId: string,
  input: Partial<SaveServiceCommandInput & CreateServicePlanCommandInput & RecordServiceInteractionCommandInput>
): Promise<ServiceReference> {
  const serviceDocId = serviceId.trim();
  const explicit: ServiceReference = {
    serviceDocId,
    sourceContentCid: clean(input.sourceContentCid),
    sourcePageCid: clean(input.sourcePageCid),
    title: clean(input.title) || serviceDocId,
    providerName: clean(input.providerName),
    programName: clean(input.programName),
    sourceUrl: clean(input.sourceUrl)
  };
  if (explicit.sourceContentCid) return explicit;

  try {
    const response = await searchServiceNavigation({ query: serviceDocId, limit: 8 });
    const match = response.results.find((result) => result.docId === serviceDocId) ?? response.results[0];
    if (match) {
      return {
        serviceDocId,
        sourceContentCid: match.contentCid || match.document.source_content_cid || fallbackCid(serviceDocId),
        sourcePageCid: match.pageCid || match.document.source_page_cid || "",
        title: clean(input.title) || match.document.title || serviceDocId,
        providerName: clean(input.providerName) || match.document.provider_name || "",
        programName: clean(input.programName) || match.document.program_name || "",
        sourceUrl: clean(input.sourceUrl) || match.document.source_url || ""
      };
    }
  } catch {
    // A missing public corpus should not block staging or wallet audit of user-confirmed intent.
  }

  return { ...explicit, sourceContentCid: fallbackCid(serviceDocId) };
}

function createStagedSavedService(
  runtime: AppActionRuntime,
  input: SaveServiceCommandInput,
  reference: ServiceReference
): SavedService {
  const now = new Date().toISOString();
  return {
    saved_service_id: `saved-${stableSuffix(reference.serviceDocId)}`,
    wallet_id: runtime.walletApiConfig?.walletId ?? "local-wallet",
    service_doc_id: reference.serviceDocId,
    source_content_cid: reference.sourceContentCid,
    source_page_cid: reference.sourcePageCid,
    title: reference.title,
    provider_name: reference.providerName,
    program_name: reference.programName,
    source_url: reference.sourceUrl,
    label: input.label || reference.title,
    reason: input.reason || input.note || "",
    priority: input.priority || "normal",
    status: "saved",
    created_at: now,
    updated_at: now,
    private_notes_record_id: "",
    metadata: input.note ? { agent_note_present: true } : {}
  };
}

function createStagedServicePlan(
  runtime: AppActionRuntime,
  input: CreateServicePlanCommandInput,
  reference: ServiceReference
): ServicePlan {
  const now = new Date().toISOString();
  return {
    plan_id: `plan-${stableSuffix(`${reference.serviceDocId}-${now}`)}`,
    wallet_id: runtime.walletApiConfig?.walletId ?? "local-wallet",
    service_doc_id: reference.serviceDocId,
    source_content_cid: reference.sourceContentCid,
    source_page_cid: reference.sourcePageCid,
    service_title: reference.title,
    provider_name: reference.providerName,
    goal: input.goal.trim(),
    steps: cleanList(input.steps),
    documents_needed: cleanList(input.documentsNeeded),
    questions_to_ask: cleanList(input.questionsToAsk),
    appointment_at: clean(input.appointmentAt),
    reminder_at: clean(input.reminderAt),
    travel_target: clean(input.travelTarget),
    assigned_worker_recipient_id: clean(input.assignedWorkerRecipientId),
    status: "active",
    related_interaction_ids: [],
    private_notes_record_id: "",
    created_at: now,
    updated_at: now
  };
}

function createStagedServiceInteraction(
  runtime: AppActionRuntime,
  input: RecordServiceInteractionCommandInput,
  reference: ServiceReference
): ServiceInteractionEvent {
  const now = new Date().toISOString();
  return {
    interaction_id: `interaction-${stableSuffix(`${reference.serviceDocId}-${input.interactionType}-${now}`)}`,
    wallet_id: runtime.walletApiConfig?.walletId ?? "local-wallet",
    service_doc_id: reference.serviceDocId,
    source_content_cid: reference.sourceContentCid,
    source_page_cid: reference.sourcePageCid,
    provider_name: input.providerName || reference.providerName,
    program_name: input.programName || reference.programName,
    interaction_type: input.interactionType.trim(),
    channel: clean(input.channel),
    actor_did: runtime.walletApiConfig?.actorDid ?? "local-agent",
    counterparty_name: clean(input.counterpartyName),
    counterparty_contact: clean(input.counterpartyContact),
    timestamp: clean(input.timestamp) || now,
    status: clean(input.status),
    outcome: clean(input.outcome),
    notes_record_id: clean(input.notesRecordId),
    next_action: clean(input.nextAction),
    next_follow_up_at: clean(input.nextFollowUpAt),
    source_action_url: clean(input.sourceActionUrl) || reference.sourceUrl,
    related_grant_ids: cleanList(input.relatedGrantIds),
    related_record_ids: cleanList(input.relatedRecordIds),
    privacy_level: clean(input.privacyLevel) || "private",
    created_at: now,
    updated_at: now,
    metadata: { recorded_by: "agent" }
  };
}

function upsertSavedService(runtime: AppActionRuntime, saved: SavedService): void {
  runtime.setSavedServices?.([
    saved,
    ...(runtime.getState().savedServices ?? []).filter((item) => item.saved_service_id !== saved.saved_service_id)
  ]);
}

function upsertServicePlan(runtime: AppActionRuntime, plan: ServicePlan): void {
  runtime.setServicePlans?.([
    plan,
    ...(runtime.getState().servicePlans ?? []).filter((item) => item.plan_id !== plan.plan_id)
  ]);
}

function upsertServiceInteraction(runtime: AppActionRuntime, interaction: ServiceInteractionEvent): void {
  runtime.setServiceInteractions?.([
    interaction,
    ...(runtime.getState().serviceInteractions ?? []).filter((item) => item.interaction_id !== interaction.interaction_id)
  ]);
}

function clean(value: string | undefined): string {
  return value?.trim() ?? "";
}

function cleanList(values: string[] | undefined): string[] {
  return Array.from(new Set((values ?? []).map((value) => value.trim()).filter(Boolean)));
}

function fallbackCid(serviceDocId: string): string {
  return `agent-unresolved-${stableSuffix(serviceDocId)}`;
}

function stableSuffix(value: string): string {
  let hash = 5381;
  for (let index = 0; index < value.length; index += 1) {
    hash = (hash * 33) ^ value.charCodeAt(index);
  }
  return (hash >>> 0).toString(36);
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

function requiresConfirmation(action: AgentCommandName, input: unknown, options: AppActionOptions): AppActionResult | undefined {
  const confirmation = confirmationFor(action, input);
  if (!confirmation.required || options.confirmed) return undefined;
  return failure(action, "confirmation_required", confirmation.summary, { confirmation });
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
  if (isRecord(input)) {
    if (action === "save_service") return `Save service ${String(input.serviceId ?? "")} to the wallet-backed service list.`;
    if (action === "create_service_plan") return `Create a private service follow-up plan for ${String(input.serviceId ?? "")}.`;
    if (action === "add_service_plan_checklist_item") return `Add a checklist item to plan ${String(input.planId ?? "")}.`;
    if (action === "set_service_plan_reminder") return `Set a reminder for plan ${String(input.planId ?? "")}.`;
    if (action === "record_service_interaction") return `Record a service interaction for ${String(input.serviceId ?? "")}.`;
  }
  return getToolDefinition(action).title;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
