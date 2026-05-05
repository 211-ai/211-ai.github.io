import type { RouteId } from "../models/abby";
import type { AgentCommandName } from "./commandSchemas";
import { getRouteLabel, getToolDefinition } from "./surfaceRegistry";
import { resolveNavigationRoute } from "./tools/navigationTools";
import type { AgentConfirmationRequest, AgentIntentKind, SurfaceContext } from "./types";

export interface AgentPlannedTool {
  name: AgentCommandName;
  input: unknown;
  title: string;
}

export interface AgentConfirmationDecision {
  confirmationId: string;
  approved: boolean;
}

export interface AgentPlannedTurn {
  intentKind: AgentIntentKind;
  summary: string;
  tools: AgentPlannedTool[];
  response?: string;
  confirmationDecision?: AgentConfirmationDecision;
}

export interface AgentPlannerInput {
  content: string;
  context: SurfaceContext;
  pendingConfirmations?: AgentConfirmationRequest[];
}

const serviceQuestionPattern =
  /\b(211|service|services|shelter|housing|rent|eviction|food|pantry|meal|benefits|snap|medicaid|legal|clinic|health|transport|bus|crisis|mental health|domestic violence|utility|utilities|near me|nearby)\b/i;

const serviceSearchPattern =
  /\b(search|find|look for|lookup|nearby|near me|closest|open now|available|resources?|programs?)\b/i;

const navigationPattern =
  /\b(go|open|navigate|show|take me|switch|view|visit|jump|move)\b/i;

const confirmationApprovePattern =
  /\b(yes|yep|yeah|approve|approved|confirm|confirmed|ok|okay|sure|do it|go ahead|proceed|continue|sounds good)\b/i;

const confirmationDenyPattern =
  /\b(no|nope|deny|denied|reject|rejected|cancel|stop|do not|don't|dont|never mind|nevermind|abort)\b/i;

export function planAgentTurn(input: AgentPlannerInput): AgentPlannedTurn {
  const content = input.content.trim();
  const lower = content.toLowerCase();
  const pendingConfirmations = input.pendingConfirmations ?? [];

  const confirmationDecision = planConfirmationDecision(lower, pendingConfirmations);
  if (confirmationDecision) {
    return {
      intentKind: "wallet_action",
      summary: confirmationDecision.approved ? "Approve pending confirmation." : "Deny pending confirmation.",
      tools: [],
      confirmationDecision
    };
  }

  if (isConfirmationReply(lower) && pendingConfirmations.length > 1) {
    return {
      intentKind: "wallet_action",
      summary: "Clarify pending confirmation.",
      tools: [],
      response: "I need to know which pending action you mean before I approve or cancel it."
    };
  }

  const saveServiceId = parseServiceId(lower, content, input.context, "save");
  if (saveServiceId) {
    return {
      intentKind: "wallet_action",
      summary: `Save service ${saveServiceId}.`,
      tools: withToolSurface(input.context, [
        { name: "save_service", input: { serviceId: saveServiceId }, title: getToolDefinition("save_service").title }
      ])
    };
  }

  const servicePlanId = parseServiceId(lower, content, input.context, "plan");
  if (servicePlanId) {
    return {
      intentKind: "wallet_action",
      summary: `Create a service plan for ${servicePlanId}.`,
      tools: withToolSurface(input.context, [
        {
          name: "create_service_plan",
          input: { serviceId: servicePlanId, goal: content },
          title: getToolDefinition("create_service_plan").title
        }
      ])
    };
  }

  if (isSaveOrPlanRequest(lower) && !saveServiceId && !servicePlanId) {
    return {
      intentKind: "wallet_action",
      summary: "Clarify service selection.",
      tools: [],
      response: "Which service should I use? Send the service ID, or open a service record first."
    };
  }

  const serviceDetailId = parseServiceId(lower, content, input.context, "open");
  if (serviceDetailId) {
    return {
      intentKind: "service_navigation",
      summary: `Open service ${serviceDetailId}.`,
      tools: withToolSurface(input.context, [
        { name: "open_service_detail", input: { docId: serviceDetailId }, title: getToolDefinition("open_service_detail").title }
      ])
    };
  }

  if (isCurrentSurfaceQuestion(lower)) {
    return {
      intentKind: "app_navigation",
      summary: "Read current surface context.",
      tools: [{ name: "read_surface_context", input: {}, title: getToolDefinition("read_surface_context").title }]
    };
  }

  const routeTarget = parseRouteTarget(lower);
  if (routeTarget && shouldNavigate(lower, routeTarget)) {
    const tools: AgentPlannedTool[] = [
      { name: "navigate", input: { route: routeTarget }, title: getToolDefinition("navigate").title }
    ];
    if (routeTarget === "audit" && /\b(refresh|reload|update|latest|audit|history|activity)\b/.test(lower)) {
      tools.push({
        name: "refresh_wallet_audit",
        input: { limit: 25 },
        title: getToolDefinition("refresh_wallet_audit").title
      });
    }
    return {
      intentKind: routeTarget === "proof-center" ? "proof_request" : routeTarget === "exports" ? "export_request" : "app_navigation",
      summary: `Navigate to ${getRouteLabel(routeTarget)}.`,
      tools
    };
  }

  if (serviceQuestionPattern.test(content)) {
    const toolName: AgentCommandName = serviceSearchPattern.test(lower) ? "search_211_services" : "answer_211_question";
    return {
      intentKind: "service_navigation",
      summary: toolName === "search_211_services" ? "Search 211 service records." : "Answer 211 service question.",
      tools: withToolSurface(input.context, [
        {
          name: toolName,
          input: toolName === "search_211_services" ? { query: content, limit: 8 } : { question: content, useLocalModel: false },
          title: getToolDefinition(toolName).title
        }
      ])
    };
  }

  if (/\b(audit|history|activity log)\b/.test(lower)) {
    return navigationTurn("audit");
  }

  if (/\b(proof|proofs|verify|verification)\b/.test(lower)) {
    return navigationTurn("proof-center", "proof_request");
  }

  if (/\b(export|exports|download|bundle|share bundle)\b/.test(lower)) {
    return navigationTurn("exports", "export_request");
  }

  return {
    intentKind: "general_question",
    summary: "Respond from current app context.",
    tools: [],
    response: fallbackResponse(input.context)
  };
}

function planConfirmationDecision(
  lower: string,
  pendingConfirmations: AgentConfirmationRequest[]
): AgentConfirmationDecision | undefined {
  if (!pendingConfirmations.length || !isConfirmationReply(lower)) return undefined;
  const matchingConfirmation = parseConfirmationTarget(lower, pendingConfirmations);
  if (!matchingConfirmation) return undefined;

  const approved = confirmationApprovePattern.test(lower) && !confirmationDenyPattern.test(lower);
  const denied = confirmationDenyPattern.test(lower);
  if (!approved && !denied) return undefined;

  return {
    confirmationId: matchingConfirmation.id,
    approved: approved && !denied
  };
}

function parseConfirmationTarget(
  lower: string,
  pendingConfirmations: AgentConfirmationRequest[]
): AgentConfirmationRequest | undefined {
  if (pendingConfirmations.length === 1) return pendingConfirmations[0];
  return pendingConfirmations.find(
    (confirmation) =>
      lower.includes(confirmation.id.toLowerCase()) ||
      lower.includes(confirmation.toolCallId.toLowerCase()) ||
      lower.includes(confirmation.title.toLowerCase())
  );
}

function isConfirmationReply(lower: string): boolean {
  return confirmationApprovePattern.test(lower) || confirmationDenyPattern.test(lower);
}

function isSaveOrPlanRequest(lower: string): boolean {
  return /\b(save|bookmark|keep|remember)\b/.test(lower) || /\b(plan|follow-up|follow up|next steps?)\b/.test(lower);
}

function isCurrentSurfaceQuestion(lower: string): boolean {
  return /\b(where am i|what screen|what page|this screen|this page|what can i do here|what can i do on this|help here|explain this screen)\b/.test(
    lower
  );
}

function shouldNavigate(lower: string, route: RouteId): boolean {
  if (navigationPattern.test(lower)) return true;
  if (route === "audit" || route === "proof-center" || route === "exports") {
    return /\b(audit|history|proof|proofs|verify|verification|export|exports|bundle|download)\b/.test(lower);
  }
  return false;
}

function navigationTurn(route: RouteId, intentKind: AgentIntentKind = "app_navigation"): AgentPlannedTurn {
  return {
    intentKind,
    summary: `Navigate to ${getRouteLabel(route)}.`,
    tools: [{ name: "navigate", input: { route }, title: getToolDefinition("navigate").title }]
  };
}

function withToolSurface(context: SurfaceContext, tools: AgentPlannedTool[]): AgentPlannedTool[] {
  const firstTool = tools[0];
  if (!firstTool || getToolDefinition(firstTool.name).surfaces.includes(context.route)) {
    return tools;
  }
  const route = firstTool.name === "refresh_wallet_audit" ? "audit" : getToolDefinition(firstTool.name).surfaces[0];
  return [{ name: "navigate", input: { route }, title: getToolDefinition("navigate").title }, ...tools];
}

function parseRouteTarget(lower: string): RouteId | undefined {
  return resolveNavigationRoute(lower);
}

function parseServiceId(
  lower: string,
  original: string,
  context: SurfaceContext,
  mode: "save" | "plan" | "open"
): string | undefined {
  const verbPattern =
    mode === "save"
      ? /\b(save|bookmark|keep|remember)\b/
      : mode === "plan"
        ? /\b(plan|follow-up|follow up|next steps?)\b/
        : /\b(open|show|view|details?|detail)\b/;
  if (!verbPattern.test(lower) || !/\b(service|211|program|record|this)\b/.test(lower)) return undefined;

  const explicitWithMarker = original.match(
    /\b(?:service|211|program|record|doc(?:ument)?)(?:\s+(?:id|#))?\s*[:#-]\s*([a-zA-Z0-9][a-zA-Z0-9._:-]{2,})\b/i
  );
  if (isServiceIdCandidate(explicitWithMarker?.[1])) return explicitWithMarker[1];

  const servicePlanFor = original.match(/\bservice\s+plan\s+(?:for|on|with)\s+([a-zA-Z0-9][a-zA-Z0-9._:-]{2,})\b/i);
  if (mode === "plan" && isServiceIdCandidate(servicePlanFor?.[1])) return servicePlanFor[1];

  const afterFor = original.match(
    /\b(?:for|on|with)\s+(?:service|211|program|record|doc(?:ument)?)\s+([a-zA-Z0-9][a-zA-Z0-9._:-]{2,})\b/i
  );
  if (isServiceIdCandidate(afterFor?.[1])) return afterFor[1];

  const afterVerbObject = original.match(
    /\b(?:save|bookmark|keep|remember|plan|open|show|view)\s+(?:service|211|program|record|doc(?:ument)?)\s+([a-zA-Z0-9][a-zA-Z0-9._:-]{2,})\b/i
  );
  if (isServiceIdCandidate(afterVerbObject?.[1])) return afterVerbObject[1];

  const afterVerb = original.match(/\b(?:save|bookmark|keep|remember|plan|open|show|view)\s+([a-zA-Z0-9][a-zA-Z0-9._:-]{2,})\b/i);
  if (isServiceIdCandidate(afterVerb?.[1])) {
    return afterVerb[1];
  }

  if (/\b(this|selected|current)\b/.test(lower)) {
    return context.selectedServiceDocId || singleVisibleServiceId(context);
  }

  return undefined;
}

function isServiceIdCandidate(value: string | undefined): value is string {
  if (!value) return false;
  return ![
    "service",
    "services",
    "program",
    "record",
    "records",
    "this",
    "that",
    "plan",
    "plans",
    "detail",
    "details",
    "question",
    "questions"
  ].includes(value.toLowerCase());
}

function singleVisibleServiceId(context: SurfaceContext): string | undefined {
  return context.visibleServiceDocIds?.length === 1 ? context.visibleServiceDocIds[0] : undefined;
}

function fallbackResponse(context: SurfaceContext): string {
  return `You are on ${context.routeLabel}. I can explain this screen, navigate the app, answer public 211 service questions, and ask for confirmation before changing wallet data.`;
}
