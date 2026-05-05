import type { AppActionResult } from "../app/appActions";
import type { RouteId } from "../models/abby";
import type { AgentCommandName } from "./commandSchemas";
import { isAgentCommandName } from "./commandSchemas";
import { planAgentTurn, type AgentPlannedTool, type AgentPlannedTurn } from "./agentPlanner";
import type { AgentSurfaceApi } from "./surfaceApi";
import { getToolDefinition } from "./surfaceRegistry";
import { confirmationRiskForGate, getAgentToolPermissionPolicy } from "./permissionPolicy";
import type {
  AgentConfirmationRequest,
  AgentIntent,
  AgentMessage,
  AgentPermissionLevel,
  AgentPlan,
  AgentPlanStep,
  AgentSession,
  AgentToolCall,
  AgentToolResult,
  EvidenceBundle,
  SurfaceContext
} from "./types";
import { isEvidenceBundle, isRecord } from "./types";

export type AgentChatProgressStage =
  | "idle"
  | "queued"
  | "reading_context"
  | "planning"
  | "waiting_for_confirmation"
  | "running_tool"
  | "responding"
  | "complete"
  | "failed";

export interface AgentChatProgressUpdate {
  id: string;
  sessionId: string;
  stage: AgentChatProgressStage;
  message: string;
  createdAt: string;
  toolCallId?: string;
  confirmationId?: string;
  error?: AgentChatError;
}

export interface AgentChatError {
  code: string;
  message: string;
  retryable: boolean;
}

export interface AgentChatSnapshot {
  session: AgentSession;
  messages: AgentMessage[];
  progress: AgentChatProgressUpdate[];
  pendingConfirmations: AgentConfirmationRequest[];
  responding: boolean;
  lastError?: AgentChatError;
  canRetry: boolean;
}

export interface AgentChatControllerOptions {
  surfaceApi: AgentSurfaceApi;
  sessionId?: string;
  title?: string;
  permissionLevel?: AgentPermissionLevel;
  privateContextAllowed?: boolean;
  initialMessages?: AgentMessage[];
  now?: () => string;
  createId?: (prefix: string) => string;
}

export interface AgentChatSendOptions {
  retryOfMessageId?: string;
}

export interface AgentChatController {
  getSnapshot: () => AgentChatSnapshot;
  subscribe: (listener: () => void) => () => void;
  sendMessage: (content: string, options?: AgentChatSendOptions) => Promise<void>;
  requestTool: (name: AgentCommandName, input: unknown) => Promise<void>;
  approveConfirmation: (confirmationId: string) => Promise<void>;
  denyConfirmation: (confirmationId: string) => void;
  retry: () => Promise<void>;
  resetError: () => void;
  setActiveRoute: (route: RouteId) => void;
}

interface RetryRequest {
  content?: string;
  tool?: AgentPlannedTool;
}

export function createAgentChatController(options: AgentChatControllerOptions): AgentChatController {
  const now = options.now ?? (() => new Date().toISOString());
  const createId =
    options.createId ??
    ((prefix: string) => `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`);
  const listeners = new Set<() => void>();
  const initialContext = options.surfaceApi.getContext(false);
  const sessionId = options.sessionId ?? createId("agent-session");
  let responding = false;
  let lastError: AgentChatError | undefined;
  let retryRequest: RetryRequest | undefined;
  let progress: AgentChatProgressUpdate[] = [];
  let session: AgentSession = {
    id: sessionId,
    title: options.title ?? "Abby assistant",
    status: "active",
    createdAt: now(),
    updatedAt: now(),
    activeRoute: initialContext.route,
    messages:
      options.initialMessages ??
      [
        createMessage(
          sessionId,
          "assistant",
          "I can help with this screen, public 211 service questions, and app actions. I will ask before changing wallet data.",
          "complete"
        )
      ],
    intents: [],
    plans: [],
    toolCalls: [],
    toolResults: [],
    confirmations: [],
    evidenceBundles: [],
    permissionLevel: options.permissionLevel ?? initialContext.permissionLevel,
    privateContextAllowed: options.privateContextAllowed ?? initialContext.privateContextAllowed
  };

  function createMessage(
    targetSessionId: string,
    role: AgentMessage["role"],
    content: string,
    status: AgentMessage["status"],
    extra: Partial<AgentMessage> = {}
  ): AgentMessage {
    return {
      id: createId("agent-message"),
      sessionId: targetSessionId,
      role,
      content,
      createdAt: now(),
      status,
      ...extra
    };
  }

  function emit() {
    for (const listener of listeners) {
      listener();
    }
  }

  function replaceSession(update: Partial<AgentSession>) {
    session = {
      ...session,
      ...update,
      updatedAt: now()
    };
    emit();
  }

  function pushProgress(stage: AgentChatProgressStage, message: string, extra: Partial<AgentChatProgressUpdate> = {}) {
    progress = [
      ...progress.slice(-20),
      {
        id: createId("agent-progress"),
        sessionId,
        stage,
        message,
        createdAt: now(),
        ...extra
      }
    ];
    emit();
  }

  function setError(error: AgentChatError, request?: RetryRequest) {
    lastError = error;
    retryRequest = error.retryable ? request : undefined;
    session = { ...session, status: "failed", updatedAt: now() };
    pushProgress("failed", error.message, { error });
  }

  function clearError() {
    lastError = undefined;
    session = { ...session, status: "active", updatedAt: now() };
  }

  function appendMessage(message: AgentMessage) {
    replaceSession({ messages: [...session.messages, message] });
  }

  async function sendMessage(content: string, sendOptions: AgentChatSendOptions = {}) {
    const trimmed = content.trim();
    if (!trimmed || responding) return;

    clearError();
    responding = true;
    retryRequest = undefined;
    progress = [];
    pushProgress(sendOptions.retryOfMessageId ? "queued" : "queued", "Queued message.");

    if (!sendOptions.retryOfMessageId) {
      appendMessage(createMessage(sessionId, "user", trimmed, "complete"));
    }

    try {
      await runTurn(trimmed);
      pushProgress("complete", "Response complete.");
    } catch (error) {
      const chatError = toChatError(error);
      appendMessage(createMessage(sessionId, "assistant", chatError.message, "failed"));
      setError(chatError, { content: trimmed });
    } finally {
      responding = false;
      emit();
    }
  }

  async function requestTool(name: AgentCommandName, input: unknown) {
    if (responding) return;
    clearError();
    responding = true;
    progress = [];
    const tool = getToolDefinition(name);
    const plannedTool = { name, input, title: tool.title };
    pushProgress("queued", `Queued ${tool.title}.`);

    try {
      await executeToolPlan(
        {
          intentKind: "app_navigation",
          summary: tool.title,
          tools: [plannedTool]
        },
        options.surfaceApi.getContext(false)
      );
      pushProgress("complete", "Tool request complete.");
    } catch (error) {
      const chatError = toChatError(error);
      appendMessage(createMessage(sessionId, "assistant", chatError.message, "failed"));
      setError(chatError, { tool: plannedTool });
    } finally {
      responding = false;
      emit();
    }
  }

  async function runTurn(content: string) {
    pushProgress("reading_context", "Reading current app context.");
    const context = options.surfaceApi.getContext(false);
    replaceSession({
      activeRoute: context.route,
      permissionLevel: context.permissionLevel,
      privateContextAllowed: context.privateContextAllowed
    });

    pushProgress("planning", "Planning next assistant action.");
    const turn = planAgentTurn({
      content,
      context,
      pendingConfirmations: session.confirmations.filter((confirmation) => confirmation.status === "pending")
    });
    if (turn.confirmationDecision) {
      await resolveConfirmationFromMessage(turn.confirmationDecision.confirmationId, turn.confirmationDecision.approved);
      return;
    }
    await executeToolPlan(turn, context);
  }

  async function executeToolPlan(turn: AgentPlannedTurn, context: SurfaceContext) {
    const intent = createIntent(turn, context);
    const plan = createPlan(intent, turn);
    replaceSession({
      intents: [...session.intents, intent],
      plans: [...session.plans, plan]
    });

    if (!turn.tools.length) {
      appendMessage(createMessage(sessionId, "assistant", turn.response ?? fallbackResponse(context), "complete", {
        intentId: intent.id,
        planId: plan.id
      }));
      markPlanComplete(plan.id);
      return;
    }

    const successfulResults: AgentToolResult[] = [];
    for (let index = 0; index < turn.tools.length; index += 1) {
      const plannedTool = turn.tools[index];
      const step = plan.steps[index];
      const toolCall = createToolCall(plannedTool);
      replaceSession({
        toolCalls: [...session.toolCalls, toolCall],
        plans: updatePlanStep(session.plans, plan.id, step.id, { status: "running" })
      });

      const tool = getToolDefinition(plannedTool.name);
      if (tool.requiresConfirmation) {
        const confirmation = createConfirmation(toolCall, plannedTool);
        replaceSession({
          confirmations: [...session.confirmations, confirmation],
          toolCalls: updateToolCall(session.toolCalls, toolCall.id, {
            status: "waiting_for_confirmation",
            confirmationId: confirmation.id
          }),
          plans: updatePlanStep(
            updatePlanStatus(session.plans, plan.id, "waiting_for_confirmation"),
            plan.id,
            step.id,
            {
              status: "pending",
              confirmationId: confirmation.id
            }
          )
        });
        pushProgress("waiting_for_confirmation", confirmation.summary, {
          toolCallId: toolCall.id,
          confirmationId: confirmation.id
        });
        appendMessage(createMessage(sessionId, "assistant", `Please review this action: ${confirmation.summary}`, "complete", {
          intentId: intent.id,
          planId: plan.id,
          toolCallIds: [toolCall.id],
          metadata: { confirmationId: confirmation.id }
        }));
        return;
      }

      const result = await executeToolCall(toolCall);
      successfulResults.push(result);
      replaceSession({
        plans: updatePlanStep(session.plans, plan.id, step.id, {
          status: result.success ? "complete" : "failed"
        })
      });
    }

    const failedResult = successfulResults.find((result) => !result.success);
    if (failedResult?.error) {
      throw new ChatControllerError(failedResult.error.code, failedResult.error.message, Boolean(failedResult.error.retryable));
    }

    appendMessage(createMessage(sessionId, "assistant", summarizeResults(successfulResults, turn.response), "complete", {
      intentId: intent.id,
      planId: plan.id,
      toolResultIds: successfulResults.map((result) => result.id),
      evidenceBundleIds: successfulResults.flatMap((result) => result.evidenceBundleIds ?? [])
    }));
    markPlanComplete(plan.id);
  }

  async function resolveConfirmationFromMessage(confirmationId: string, approved: boolean) {
    const confirmation = session.confirmations.find((candidate) => candidate.id === confirmationId);
    if (!confirmation || confirmation.status !== "pending") return;
    if (!approved) {
      denyConfirmation(confirmationId);
      return;
    }

    const toolCall = session.toolCalls.find((candidate) => candidate.id === confirmation.toolCallId);
    if (!toolCall) return;

    replaceSession({
      confirmations: updateConfirmation(session.confirmations, confirmationId, {
        status: "approved",
        resolvedAt: now()
      }),
      plans: session.plans.map((plan) =>
        plan.steps.some((step) => step.confirmationId === confirmationId) ? { ...plan, status: "running", updatedAt: now() } : plan
      )
    });
    pushProgress("running_tool", `Confirmed ${confirmation.title}.`, {
      toolCallId: toolCall.id,
      confirmationId
    });

    try {
      const result = await executeToolCall(toolCall, true);
      markConfirmationPlanStep(confirmationId, result.success ? "complete" : "failed");
      appendMessage(createMessage(sessionId, "assistant", summarizeResults([result]), "complete", {
        toolCallIds: [toolCall.id],
        toolResultIds: [result.id],
        evidenceBundleIds: result.evidenceBundleIds
      }));
      markPlanContainingConfirmation(confirmationId, result.success ? "complete" : "failed");
    } catch (error) {
      markConfirmationPlanStep(confirmationId, "failed");
      markPlanContainingConfirmation(confirmationId, "failed");
      throw error;
    }
  }

  async function executeToolCall(toolCall: AgentToolCall, confirmed = false): Promise<AgentToolResult> {
    replaceSession({
      toolCalls: updateToolCall(session.toolCalls, toolCall.id, {
        status: "running",
        startedAt: now()
      })
    });
    pushProgress("running_tool", `Running ${readableToolName(toolCall.name)}.`, { toolCallId: toolCall.id });

    const result = await options.surfaceApi.invokeToolCall(toolCall, { confirmed });
    const evidenceBundle = getEvidenceBundleFromResult(result);
    replaceSession({
      evidenceBundles: evidenceBundle ? upsertEvidenceBundle(session.evidenceBundles, evidenceBundle) : session.evidenceBundles,
      toolResults: upsertToolResult(session.toolResults, result),
      toolCalls: updateToolCall(session.toolCalls, toolCall.id, {
        status: result.success ? "succeeded" : "failed",
        completedAt: result.completedAt
      })
    });

    if (!result.success && result.error) {
      throw new ChatControllerError(result.error.code, result.error.message, Boolean(result.error.retryable));
    }

    return result;
  }

  async function approveConfirmation(confirmationId: string) {
    if (responding) return;
    const confirmation = session.confirmations.find((candidate) => candidate.id === confirmationId);
    if (!confirmation || confirmation.status !== "pending") return;
    const toolCall = session.toolCalls.find((candidate) => candidate.id === confirmation.toolCallId);
    if (!toolCall) return;

    clearError();
    responding = true;
    progress = [];
    replaceSession({
      confirmations: updateConfirmation(session.confirmations, confirmationId, {
        status: "approved",
        resolvedAt: now()
      }),
      plans: session.plans.map((plan) =>
        plan.steps.some((step) => step.confirmationId === confirmationId) ? { ...plan, status: "running", updatedAt: now() } : plan
      )
    });
    pushProgress("running_tool", `Confirmed ${confirmation.title}.`, {
      toolCallId: toolCall.id,
      confirmationId
    });

    try {
      const result = await executeToolCall(toolCall, true);
      markConfirmationPlanStep(confirmationId, result.success ? "complete" : "failed");
      appendMessage(createMessage(sessionId, "assistant", summarizeResults([result]), "complete", {
        toolCallIds: [toolCall.id],
        toolResultIds: [result.id],
        evidenceBundleIds: result.evidenceBundleIds
      }));
      markPlanContainingConfirmation(confirmationId, result.success ? "complete" : "failed");
      pushProgress("complete", "Confirmed action complete.");
    } catch (error) {
      const chatError = toChatError(error);
      markConfirmationPlanStep(confirmationId, "failed");
      markPlanContainingConfirmation(confirmationId, "failed");
      appendMessage(createMessage(sessionId, "assistant", chatError.message, "failed", {
        toolCallIds: [toolCall.id]
      }));
      setError(chatError, { tool: { name: toolCall.name as AgentCommandName, input: toolCall.input, title: confirmation.title } });
    } finally {
      responding = false;
      emit();
    }
  }

  function denyConfirmation(confirmationId: string) {
    const confirmation = session.confirmations.find((candidate) => candidate.id === confirmationId);
    if (!confirmation || confirmation.status !== "pending") return;
    replaceSession({
      confirmations: updateConfirmation(session.confirmations, confirmationId, {
        status: "denied",
        resolvedAt: now()
      }),
      toolCalls: updateToolCall(session.toolCalls, confirmation.toolCallId, {
        status: "canceled",
        completedAt: now()
      })
    });
    markConfirmationPlanStep(confirmationId, "skipped");
    markPlanContainingConfirmation(confirmationId, "complete");
    appendMessage(createMessage(sessionId, "assistant", `Canceled: ${confirmation.summary}`, "canceled", {
      toolCallIds: [confirmation.toolCallId],
      metadata: { confirmationId }
    }));
    pushProgress("complete", "Confirmation canceled.", { confirmationId });
  }

  async function retry() {
    if (!retryRequest || responding) return;
    clearError();
    if (retryRequest.tool) {
      await requestTool(retryRequest.tool.name, retryRequest.tool.input);
      return;
    }
    if (retryRequest.content) {
      const userMessage = [...session.messages].reverse().find((message) => message.role === "user");
      await sendMessage(retryRequest.content, { retryOfMessageId: userMessage?.id });
    }
  }

  function getSnapshot(): AgentChatSnapshot {
    return {
      session,
      messages: session.messages,
      progress,
      pendingConfirmations: session.confirmations.filter((confirmation) => confirmation.status === "pending"),
      responding,
      lastError,
      canRetry: Boolean(retryRequest)
    };
  }

  return {
    getSnapshot,
    subscribe: (listener) => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    sendMessage,
    requestTool,
    approveConfirmation,
    denyConfirmation,
    retry,
    resetError: () => {
      clearError();
      emit();
    },
    setActiveRoute: (route) => {
      if (session.activeRoute !== route) {
        replaceSession({ activeRoute: route });
      }
    }
  };

  function createIntent(turn: AgentPlannedTurn, context: SurfaceContext): AgentIntent {
    return {
      id: createId("agent-intent"),
      kind: turn.intentKind,
      summary: turn.summary,
      confidence: turn.tools.length ? 0.82 : 0.64,
      createdAt: now(),
      route: context.route,
      requiresPrivateContext: turn.tools.some((tool) => getToolDefinition(tool.name).requiresPrivateContextOptIn)
    };
  }

  function createPlan(intent: AgentIntent, turn: AgentPlannedTurn): AgentPlan {
    const createdAt = now();
    return {
      id: createId("agent-plan"),
      sessionId,
      intentId: intent.id,
      status: turn.tools.length ? "ready" : "complete",
      steps: turn.tools.length
        ? turn.tools.map((tool) => ({
            id: createId("agent-plan-step"),
            title: tool.title,
            status: "pending",
            toolName: tool.name
          }))
        : [
            {
              id: createId("agent-plan-step"),
              title: "Respond",
              status: "complete"
            }
          ],
      createdAt,
      updatedAt: createdAt,
      summary: turn.summary
    };
  }

  function createToolCall(tool: AgentPlannedTool): AgentToolCall {
    return {
      id: createId("agent-tool-call"),
      sessionId,
      name: tool.name,
      input: tool.input,
      status: "pending",
      requestedAt: now()
    };
  }

  function createConfirmation(toolCall: AgentToolCall, tool: AgentPlannedTool): AgentConfirmationRequest {
    const definition = getToolDefinition(tool.name);
    const policy = getAgentToolPermissionPolicy(tool.name);
    return {
      id: createId("agent-confirmation"),
      sessionId,
      toolCallId: toolCall.id,
      title: definition.title,
      summary: summarizeConfirmation(tool.name, tool.input),
      risk: confirmationRiskForGate(policy.gate),
      permissionLevel: definition.permissionLevel,
      status: "pending",
      requestedAt: now(),
      details: isRecord(tool.input)
        ? {
            input: tool.input,
            permissionGate: policy.gate,
            requiresAudit: policy.requiresAudit,
            auditEventType: policy.auditEventType
          }
        : {
            permissionGate: policy.gate,
            requiresAudit: policy.requiresAudit,
            auditEventType: policy.auditEventType
          }
    };
  }

  function markPlanComplete(planId: string) {
    replaceSession({ plans: updatePlanStatus(session.plans, planId, "complete") });
  }

  function markConfirmationPlanStep(confirmationId: string, status: AgentPlanStep["status"]) {
    replaceSession({
      plans: session.plans.map((plan) => ({
        ...plan,
        steps: plan.steps.map((step) => (step.confirmationId === confirmationId ? { ...step, status } : step)),
        updatedAt: plan.steps.some((step) => step.confirmationId === confirmationId) ? now() : plan.updatedAt
      }))
    });
  }

  function markPlanContainingConfirmation(confirmationId: string, status: AgentPlan["status"]) {
    replaceSession({
      plans: session.plans.map((plan) =>
        plan.steps.some((step) => step.confirmationId === confirmationId) ? { ...plan, status, updatedAt: now() } : plan
      )
    });
  }
}

function updateToolCall(
  calls: AgentToolCall[],
  id: string,
  update: Partial<AgentToolCall>
): AgentToolCall[] {
  return calls.map((call) => (call.id === id ? { ...call, ...update } : call));
}

function updateConfirmation(
  confirmations: AgentConfirmationRequest[],
  id: string,
  update: Partial<AgentConfirmationRequest>
): AgentConfirmationRequest[] {
  return confirmations.map((confirmation) => (confirmation.id === id ? { ...confirmation, ...update } : confirmation));
}

function updatePlanStatus(plans: AgentPlan[], id: string, status: AgentPlan["status"]): AgentPlan[] {
  const updatedAt = new Date().toISOString();
  return plans.map((plan) => (plan.id === id ? { ...plan, status, updatedAt } : plan));
}

function updatePlanStep(
  plans: AgentPlan[],
  planId: string,
  stepId: string,
  update: Partial<AgentPlanStep>
): AgentPlan[] {
  const updatedAt = new Date().toISOString();
  return plans.map((plan) =>
    plan.id === planId
      ? {
          ...plan,
          updatedAt,
          steps: plan.steps.map((step) => (step.id === stepId ? { ...step, ...update } : step))
        }
      : plan
  );
}

function upsertToolResult(results: AgentToolResult[], result: AgentToolResult): AgentToolResult[] {
  return results.some((item) => item.id === result.id)
    ? results.map((item) => (item.id === result.id ? result : item))
    : [...results, result];
}

function upsertEvidenceBundle(bundles: EvidenceBundle[], bundle: EvidenceBundle): EvidenceBundle[] {
  return bundles.some((item) => item.id === bundle.id)
    ? bundles.map((item) => (item.id === bundle.id ? bundle : item))
    : [...bundles, bundle];
}

function getEvidenceBundleFromResult(result: AgentToolResult): EvidenceBundle | undefined {
  const output = result.output;
  if (isAppActionResult(output) && output.ok && isEvidenceBundle(output.evidenceBundle)) {
    return output.evidenceBundle;
  }
  return undefined;
}

function isAppActionResult(value: unknown): value is AppActionResult {
  return isRecord(value) && typeof value.ok === "boolean" && isAgentCommandName(value.action);
}

function summarizeResults(results: AgentToolResult[], fallback = "Done."): string {
  const summaries = results
    .map((result) => {
      const output = result.output;
      if (isAppActionResult(output)) {
        return output.ok ? output.summary : output.message;
      }
      return result.success ? undefined : result.error?.message;
    })
    .filter((summary): summary is string => Boolean(summary));
  return summaries.length ? summaries.join("\n\n") : fallback;
}

function summarizeConfirmation(name: AgentCommandName, input: unknown): string {
  if (name === "save_service" && isRecord(input)) {
    return `Save service ${String(input.serviceId ?? "")} to your wallet-backed service list.`;
  }
  if (name === "create_service_plan" && isRecord(input)) {
    return `Create a private service follow-up plan for ${String(input.serviceId ?? "")}.`;
  }
  if (name === "update_registration_draft") return "Update private registration profile fields.";
  if (name === "update_check_in_policy") return "Update check-in reminder and escalation settings.";
  if (name === "set_disclosure_scopes" && isRecord(input)) {
    return `Update sharing scopes for recipient ${String(input.recipientId ?? "")}.`;
  }
  if (name === "update_recipient_scopes" && isRecord(input)) {
    return `Update sharing scopes for recipient ${String(input.recipientId ?? "")}.`;
  }
  if ((name === "add_recipient" || name === "edit_recipient") && isRecord(input)) {
    return `${name === "add_recipient" ? "Add" : "Edit"} recipient ${String(
      input.displayName ?? input.recipientId ?? ""
    )}.`;
  }
  if (name === "remove_recipient" && isRecord(input)) {
    return `Remove recipient ${String(input.recipientId ?? "")}.`;
  }
  if (name === "request_shelter_contact" && isRecord(input)) {
    return `Request shelter contact with ${String(input.shelterName ?? "")}.`;
  }
  if (
    (name === "approve_shelter_contact_request" || name === "deny_shelter_contact_request") &&
    isRecord(input)
  ) {
    return `${name === "approve_shelter_contact_request" ? "Approve" : "Deny"} shelter contact request ${String(
      input.requestId ?? ""
    )}.`;
  }
  if (
    (name === "record_controller_approval" ||
      name === "approve_access_request" ||
      name === "reject_access_request" ||
      name === "revoke_access_request") &&
    isRecord(input)
  ) {
    const verbs: Partial<Record<AgentCommandName, string>> = {
      record_controller_approval: "Record controller approval for",
      approve_access_request: "Approve",
      reject_access_request: "Reject",
      revoke_access_request: "Revoke"
    };
    return `${verbs[name] ?? "Update"} access request ${String(input.requestId ?? "")}.`;
  }
  if (
    (name === "analyze_granted_record" || name === "view_granted_record" || name === "delegate_grant") &&
    isRecord(input)
  ) {
    const verbs: Partial<Record<AgentCommandName, string>> = {
      analyze_granted_record: "Analyze",
      view_granted_record: "View",
      delegate_grant: "Delegate"
    };
    return `${verbs[name] ?? "Use"} grant ${String(input.grantId ?? input.receiptId ?? "")}.`;
  }
  if (name === "create_location_region_proof" && isRecord(input)) {
    return `Create a location-region proof for ${String(input.regionLabel ?? "the selected region")}.`;
  }
  if (name === "create_proof" && isRecord(input)) {
    return `Stage proof "${String(input.claim ?? "")}" for verifier ${String(input.verifier ?? "")} using witness label ${String(
      input.witnessLabel ?? ""
    )}.`;
  }
  if (name === "create_verified_export_bundle" && isRecord(input)) {
    return `Create an export bundle for ${String(input.audienceName ?? "the selected recipient")}.`;
  }
  return getToolDefinition(name).title;
}

function readableToolName(name: string): string {
  return isAgentCommandName(name) ? getToolDefinition(name).title : name;
}

function fallbackResponse(context: SurfaceContext): string {
  return `You are on ${context.routeLabel}. I can explain this screen, navigate the app, answer public 211 service questions, and ask for confirmation before changing wallet data.`;
}

function toChatError(error: unknown): AgentChatError {
  if (error instanceof ChatControllerError) {
    return {
      code: error.code,
      message: error.message,
      retryable: error.retryable
    };
  }
  return {
    code: "agent_chat_error",
    message: "I could not complete that request. Try again or ask for a smaller action.",
    retryable: true
  };
}

class ChatControllerError extends Error {
  constructor(
    readonly code: string,
    message: string,
    readonly retryable: boolean
  ) {
    super(message);
  }
}
