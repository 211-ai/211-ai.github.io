import type { AppActionRuntime, AppActionResult, AppActionOptions } from "../app/appActions";
import { runAppAction } from "../app/appActions";
import type { AgentCommandName } from "./commandSchemas";
import { commandSchemas, isAgentCommandName } from "./commandSchemas";
import type { AgentToolCall, AgentToolResult, SurfaceContext } from "./types";
import { hasPermissionLevel } from "./types";
import { canUseToolOnSurface, getRouteLabel, getToolDefinition } from "./surfaceRegistry";
import { buildSafeSurfaceContext } from "./tools/navigationTools";

export interface SurfaceApiInvokeOptions extends AppActionOptions {
  sessionId?: string;
  toolCallId?: string;
}

export interface SurfaceApiInvokeRequest {
  name: AgentCommandName;
  input: unknown;
  options?: SurfaceApiInvokeOptions;
}

export interface AgentSurfaceApi {
  getContext: (includePrivateContext?: boolean) => SurfaceContext;
  invoke: (name: AgentCommandName, input: unknown, options?: SurfaceApiInvokeOptions) => Promise<AppActionResult>;
  invokeRequest: (request: SurfaceApiInvokeRequest) => Promise<AppActionResult>;
  invokeToolCall: (toolCall: AgentToolCall, options?: SurfaceApiInvokeOptions) => Promise<AgentToolResult>;
}

export function createAgentSurfaceApi(runtime: AppActionRuntime): AgentSurfaceApi {
  return {
    getContext: (includePrivateContext = false) => buildSurfaceContext(runtime, includePrivateContext),
    invoke: (name, input, options = {}) => invokeSurfaceAction(runtime, name, input, options),
    invokeRequest: (request) => invokeSurfaceAction(runtime, request.name, request.input, request.options ?? {}),
    invokeToolCall: (toolCall, options = {}) => invokeToolCall(runtime, toolCall, options)
  };
}

export async function invokeSurfaceAction(
  runtime: AppActionRuntime,
  name: AgentCommandName,
  input: unknown,
  options: SurfaceApiInvokeOptions = {}
): Promise<AppActionResult> {
  const validationFailure = validateSurfaceInvocation(runtime, name, input);
  if (validationFailure) return validationFailure;
  return runAppAction(runtime, name, input, options);
}

export async function invokeToolCall(
  runtime: AppActionRuntime,
  toolCall: AgentToolCall,
  options: SurfaceApiInvokeOptions = {}
): Promise<AgentToolResult> {
  if (!isAgentCommandName(toolCall.name)) {
    return toAgentToolResult(toolCall, {
      ok: false,
      action: "read_surface_context",
      errorCode: "unknown_tool",
      message: `Unknown tool ${toolCall.name}.`
    });
  }
  const result = await invokeSurfaceAction(runtime, toolCall.name, toolCall.input, {
    ...options,
    toolCallId: toolCall.id
  });
  return toAgentToolResult(toolCall, result);
}

export function buildSurfaceContext(runtime: AppActionRuntime, includePrivateContext = false): SurfaceContext {
  return buildSafeSurfaceContext(runtime.getState(), { includePrivateContext });
}

function validateSurfaceInvocation(
  runtime: AppActionRuntime,
  name: AgentCommandName,
  input: unknown
): AppActionResult | undefined {
  const schema = commandSchemas[name];
  if (!schema.isInput(input)) {
    return {
      ok: false,
      action: name,
      errorCode: "invalid_input",
      message: `Invalid input for ${name}.`
    };
  }

  const state = runtime.getState();
  const tool = getToolDefinition(name);
  const walletUnlocked = state.walletUnlocked ?? true;
  const privateContextAllowed = state.privateContextAllowed ?? false;

  if (!canUseToolOnSurface(name, state.activeRoute, state.permissionLevel ?? "wallet_write") && name !== "navigate") {
    return {
      ok: false,
      action: name,
      errorCode: "surface_not_allowed",
      message: `${tool.title} cannot run from ${getRouteLabel(state.activeRoute)}.`
    };
  }

  if (!hasPermissionLevel(state.permissionLevel ?? "wallet_write", tool.permissionLevel)) {
    return {
      ok: false,
      action: name,
      errorCode: "permission_denied",
      message: `${tool.title} requires ${tool.permissionLevel} permission.`
    };
  }

  if (tool.requiresWalletUnlock && !walletUnlocked) {
    return {
      ok: false,
      action: name,
      errorCode: "wallet_locked",
      message: `${tool.title} requires an unlocked wallet.`
    };
  }

  if (tool.requiresPrivateContextOptIn && !privateContextAllowed) {
    return {
      ok: false,
      action: name,
      errorCode: "private_context_required",
      message: `${tool.title} requires private context permission.`
    };
  }

  return undefined;
}

function toAgentToolResult(toolCall: AgentToolCall, result: AppActionResult): AgentToolResult {
  const completedAt = new Date().toISOString();
  return result.ok
    ? {
        id: `tool-result-${toolCall.id}`,
        toolCallId: toolCall.id,
        name: toolCall.name,
        success: true,
        completedAt,
        output: result,
        evidenceBundleIds: result.evidenceBundle ? [result.evidenceBundle.id] : undefined,
        auditEventId: result.auditEventId
      }
    : {
        id: `tool-result-${toolCall.id}`,
        toolCallId: toolCall.id,
        name: toolCall.name,
        success: false,
        completedAt,
        error: {
          code: result.errorCode,
          message: result.message,
          retryable: result.retryable
        },
        output: result
      };
}
