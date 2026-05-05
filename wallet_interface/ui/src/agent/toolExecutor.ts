import type { AgentCommandName } from "./commandSchemas";
import { commandSchemas, isAgentCommandName, isCommandOutputFor } from "./commandSchemas";
import type { AgentSurfaceApi, SurfaceApiInvokeOptions } from "./surfaceApi";
import { getToolDefinition } from "./surfaceRegistry";
import {
  confirmationRiskForGate,
  evaluateAgentToolPermissionPolicy,
  getAgentToolPermissionPolicy
} from "./permissionPolicy";
import type {
  AgentConfirmationRequest,
  AgentPermissionLevel,
  AgentToolCall,
  AgentToolResult,
  SurfaceContext
} from "./types";
import { isAgentToolResult, isRecord } from "./types";

export type AgentToolExecutorEvent =
  | {
      type: "tool_call_validated";
      toolCallId: string;
      toolName: string;
      createdAt: string;
    }
  | {
      type: "confirmation_requested";
      toolCallId: string;
      confirmationId: string;
      createdAt: string;
    }
  | {
      type: "tool_call_started";
      toolCallId: string;
      toolName: string;
      createdAt: string;
    }
  | {
      type: "tool_result";
      toolCallId: string;
      toolName: string;
      resultId: string;
      success: boolean;
      auditEventId?: string;
      createdAt: string;
    };

export interface AgentToolExecutionSucceeded {
  status: "succeeded";
  toolCall: AgentToolCall;
  result: AgentToolResult;
  events: AgentToolExecutorEvent[];
}

export interface AgentToolExecutionFailed {
  status: "failed";
  toolCall: AgentToolCall;
  result: AgentToolResult;
  events: AgentToolExecutorEvent[];
}

export interface AgentToolExecutionWaitingForConfirmation {
  status: "waiting_for_confirmation";
  toolCall: AgentToolCall;
  confirmation: AgentConfirmationRequest;
  events: AgentToolExecutorEvent[];
}

export type AgentToolExecutionOutcome =
  | AgentToolExecutionSucceeded
  | AgentToolExecutionFailed
  | AgentToolExecutionWaitingForConfirmation;

export interface AgentToolExecutorOptions {
  surfaceApi: AgentSurfaceApi;
  sessionId?: string;
  permissionLevel?: AgentPermissionLevel;
  privateContextAllowed?: boolean;
  walletUnlocked?: boolean;
  userPresent?: boolean;
  confirmationExpiresInMs?: number;
  now?: () => string;
  createId?: (prefix: string) => string;
  onEvent?: (event: AgentToolExecutorEvent) => void;
  onConfirmationRequested?: (confirmation: AgentConfirmationRequest) => void;
  onResult?: (result: AgentToolResult) => void;
}

export interface AgentToolExecutionOptions extends SurfaceApiInvokeOptions {
  sessionId?: string;
  confirmed?: boolean;
  confirmationId?: string;
  permissionLevel?: AgentPermissionLevel;
  privateContextAllowed?: boolean;
  walletUnlocked?: boolean;
  userPresent?: boolean;
  includePrivateContext?: boolean;
}

export interface AgentToolExecutorValidation {
  ok: true;
  commandName: AgentCommandName;
  context: SurfaceContext;
}

export interface AgentToolExecutorValidationFailure {
  ok: false;
  result: AgentToolResult;
}

export type AgentToolExecutorValidationResult =
  | AgentToolExecutorValidation
  | AgentToolExecutorValidationFailure;

export interface AgentToolExecutor {
  execute: (
    name: AgentCommandName,
    input: unknown,
    options?: AgentToolExecutionOptions
  ) => Promise<AgentToolExecutionOutcome>;
  executeToolCall: (
    toolCall: AgentToolCall,
    options?: AgentToolExecutionOptions
  ) => Promise<AgentToolExecutionOutcome>;
  validateToolCall: (
    toolCall: AgentToolCall,
    options?: AgentToolExecutionOptions
  ) => AgentToolExecutorValidationResult;
  createConfirmationRequest: (
    toolCall: AgentToolCall,
    commandName: AgentCommandName,
    options?: AgentToolExecutionOptions
  ) => AgentConfirmationRequest;
}

export function createAgentToolExecutor(options: AgentToolExecutorOptions): AgentToolExecutor {
  const now = options.now ?? (() => new Date().toISOString());
  const createId =
    options.createId ??
    ((prefix: string) => `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`);

  function emit(event: AgentToolExecutorEvent, events: AgentToolExecutorEvent[]) {
    events.push(event);
    options.onEvent?.(event);
  }

  function createToolCall(name: AgentCommandName, input: unknown, executionOptions: AgentToolExecutionOptions): AgentToolCall {
    const requestedAt = now();
    return {
      id: createId("agent-tool-call"),
      sessionId: executionOptions.sessionId ?? options.sessionId ?? createId("agent-session"),
      name,
      input,
      status: "pending",
      requestedAt
    };
  }

  async function execute(
    name: AgentCommandName,
    input: unknown,
    executionOptions: AgentToolExecutionOptions = {}
  ): Promise<AgentToolExecutionOutcome> {
    return executeToolCall(createToolCall(name, input, executionOptions), executionOptions);
  }

  async function executeToolCall(
    toolCall: AgentToolCall,
    executionOptions: AgentToolExecutionOptions = {}
  ): Promise<AgentToolExecutionOutcome> {
    const events: AgentToolExecutorEvent[] = [];
    const validation = validateToolCall(toolCall, executionOptions);
    if (!validation.ok) {
      emit(resultEvent(toolCall, validation.result, now()), events);
      options.onResult?.(validation.result);
      return {
        status: "failed",
        toolCall: completeToolCall(toolCall, "failed", validation.result.completedAt),
        result: validation.result,
        events
      };
    }

    const validatedAt = now();
    emit(
      {
        type: "tool_call_validated",
        toolCallId: toolCall.id,
        toolName: validation.commandName,
        createdAt: validatedAt
      },
      events
    );

    const definition = getToolDefinition(validation.commandName);
    if (definition.requiresConfirmation && !executionOptions.confirmed) {
      const confirmation = createConfirmationRequest(toolCall, validation.commandName, executionOptions);
      emit(
        {
          type: "confirmation_requested",
          toolCallId: toolCall.id,
          confirmationId: confirmation.id,
          createdAt: confirmation.requestedAt
        },
        events
      );
      options.onConfirmationRequested?.(confirmation);
      return {
        status: "waiting_for_confirmation",
        toolCall: {
          ...toolCall,
          status: "waiting_for_confirmation",
          confirmationId: confirmation.id
        },
        confirmation,
        events
      };
    }

    const startedAt = now();
    emit(
      {
        type: "tool_call_started",
        toolCallId: toolCall.id,
        toolName: validation.commandName,
        createdAt: startedAt
      },
      events
    );

    const result = enforceAuditRequirement(
      toolCall,
      validation.commandName,
      normalizeSurfaceResult(
        toolCall,
        await options.surfaceApi.invokeToolCall(
          {
            ...toolCall,
            status: "running",
            startedAt,
            confirmationId: executionOptions.confirmationId ?? toolCall.confirmationId
          },
          {
            ...executionOptions,
            confirmed: executionOptions.confirmed,
            sessionId: executionOptions.sessionId ?? options.sessionId,
            toolCallId: toolCall.id
          }
        )
      )
    );
    emit(resultEvent(toolCall, result, now()), events);
    options.onResult?.(result);

    return {
      status: result.success ? "succeeded" : "failed",
      toolCall: completeToolCall(toolCall, result.success ? "succeeded" : "failed", result.completedAt, {
        startedAt,
        confirmationId: executionOptions.confirmationId ?? toolCall.confirmationId
      }),
      result,
      events
    };
  }

  function validateToolCall(
    toolCall: AgentToolCall,
    executionOptions: AgentToolExecutionOptions = {}
  ): AgentToolExecutorValidationResult {
    if (!isAgentCommandName(toolCall.name)) {
      return {
        ok: false,
        result: failureResult(toolCall, "unknown_tool", `Unknown tool ${toolCall.name}.`, false, now())
      };
    }

    const schema = commandSchemas[toolCall.name];
    if (!schema.isInput(toolCall.input)) {
      return {
        ok: false,
        result: failureResult(toolCall, "invalid_input", `Invalid input for ${toolCall.name}.`, false, now())
      };
    }

    const includePrivateContext =
      executionOptions.includePrivateContext ??
      executionOptions.privateContextAllowed ??
      options.privateContextAllowed ??
      false;
    const context = options.surfaceApi.getContext(includePrivateContext);
    const definition = getToolDefinition(toolCall.name);
    const permissionLevel = executionOptions.permissionLevel ?? options.permissionLevel ?? context.permissionLevel;
    const walletUnlocked = executionOptions.walletUnlocked ?? options.walletUnlocked ?? context.walletUnlocked;
    const privateContextAllowed =
      executionOptions.privateContextAllowed ?? options.privateContextAllowed ?? context.privateContextAllowed;
    const userPresent = executionOptions.userPresent ?? options.userPresent ?? true;

    const decision = evaluateAgentToolPermissionPolicy(toolCall.name, {
      route: context.route,
      allowedSurfaces: definition.surfaces,
      grantedPermissionLevel: permissionLevel,
      walletUnlocked,
      privateContextAllowed,
      userPresent,
      toolTitle: definition.title
    });
    if (!decision.ok) {
      return {
        ok: false,
        result: failureResult(toolCall, decision.code, decision.message, false, now())
      };
    }

    return {
      ok: true,
      commandName: toolCall.name,
      context
    };
  }

  function createConfirmationRequest(
    toolCall: AgentToolCall,
    commandName: AgentCommandName,
    executionOptions: AgentToolExecutionOptions = {}
  ): AgentConfirmationRequest {
    const definition = getToolDefinition(commandName);
    const requestedAt = now();
    const expiresAt =
      options.confirmationExpiresInMs === undefined
        ? undefined
        : new Date(Date.parse(requestedAt) + options.confirmationExpiresInMs).toISOString();
    return {
      id: executionOptions.confirmationId ?? createId("agent-confirmation"),
      sessionId: executionOptions.sessionId ?? options.sessionId ?? toolCall.sessionId,
      toolCallId: toolCall.id,
      title: definition.title,
      summary: summarizeConfirmation(commandName, toolCall.input),
      risk: confirmationRiskForGate(getAgentToolPermissionPolicy(commandName).gate),
      permissionLevel: definition.permissionLevel,
      status: "pending",
      requestedAt,
      expiresAt,
      details: confirmationDetails(toolCall.input, commandName)
    };
  }

  return {
    execute,
    executeToolCall,
    validateToolCall,
    createConfirmationRequest
  };
}

export function isToolExecutorConfirmationRequired(
  outcome: AgentToolExecutionOutcome
): outcome is AgentToolExecutionWaitingForConfirmation {
  return outcome.status === "waiting_for_confirmation";
}

export function isToolExecutorResult(
  outcome: AgentToolExecutionOutcome
): outcome is AgentToolExecutionSucceeded | AgentToolExecutionFailed {
  return outcome.status === "succeeded" || outcome.status === "failed";
}

function normalizeSurfaceResult(toolCall: AgentToolCall, result: AgentToolResult): AgentToolResult {
  if (!isAgentToolResult(result)) {
    return failureResult(toolCall, "invalid_tool_result", "The tool returned an invalid result.");
  }

  if (!isAgentCommandName(toolCall.name)) {
    return result;
  }

  if (!result.output || !isCommandOutputFor(toolCall.name, result.output)) {
    return result.success
      ? failureResult(toolCall, "invalid_tool_output", `The ${toolCall.name} tool returned invalid output.`)
      : result;
  }

  return result;
}

function enforceAuditRequirement(
  toolCall: AgentToolCall,
  commandName: AgentCommandName,
  result: AgentToolResult
): AgentToolResult {
  const policy = getAgentToolPermissionPolicy(commandName);
  if (!result.success || !policy.requiresAudit || result.auditEventId) {
    return result;
  }
  return failureResult(
    toolCall,
    "audit_required",
    `The ${commandName} tool completed without the required audit event.`,
    false,
    result.completedAt
  );
}

function completeToolCall(
  toolCall: AgentToolCall,
  status: AgentToolCall["status"],
  completedAt: string,
  extra: Partial<AgentToolCall> = {}
): AgentToolCall {
  return {
    ...toolCall,
    ...extra,
    status,
    completedAt
  };
}

function failureResult(
  toolCall: AgentToolCall,
  code: string,
  message: string,
  retryable = false,
  completedAt = new Date().toISOString()
): AgentToolResult {
  const output = isAgentCommandName(toolCall.name)
    ? {
        ok: false,
        errorCode: code,
        message,
        retryable
      }
    : undefined;
  return {
    id: `tool-result-${toolCall.id}`,
    toolCallId: toolCall.id,
    name: toolCall.name,
    success: false,
    completedAt,
    output,
    error: {
      code,
      message,
      retryable
    }
  };
}

function confirmationDetails(input: unknown, commandName: AgentCommandName): Record<string, unknown> | undefined {
  const policy = getAgentToolPermissionPolicy(commandName);
  const policyDetails = {
    permissionGate: policy.gate,
    requiresAudit: policy.requiresAudit,
    auditEventType: policy.auditEventType
  };
  if (isRecord(input)) {
    return { input, ...policyDetails };
  }
  return policyDetails;
}

function resultEvent(toolCall: AgentToolCall, result: AgentToolResult, createdAt: string): AgentToolExecutorEvent {
  return {
    type: "tool_result",
    toolCallId: toolCall.id,
    toolName: toolCall.name,
    resultId: result.id,
    success: result.success,
    auditEventId: result.auditEventId,
    createdAt
  };
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
  if (name === "create_verified_export_bundle" && isRecord(input)) {
    return `Create an export bundle for ${String(input.audienceName ?? "the selected recipient")}.`;
  }
  return getToolDefinition(name).title;
}
