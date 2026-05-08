import { expect, test } from "@playwright/test";

import {
  commandSchemas,
  isCommandOutputFor,
  validateCommandSchemas,
  type AgentCommandName,
} from "../src/agent/commandSchemas";
import { planAgentTurn } from "../src/agent/agentPlanner";
import {
  buildPromptSafeSurfaceContext,
  compactPromptConversationHistory,
  guardAgentToolDefinitions,
  guardEvidenceBundles,
  guardPromptText,
} from "../src/agent/promptGuards";
import {
  confirmationRiskForGate,
  evaluateAgentToolPermissionPolicy,
  getAgentToolPermissionPolicy,
} from "../src/agent/permissionPolicy";
import {
  agentToolDefinitions,
  getToolDefinition,
  validateSurfaceRegistry,
} from "../src/agent/surfaceRegistry";
import { createAgentToolExecutor } from "../src/agent/toolExecutor";
import {
  buildServiceNavigationNextSteps,
  evidenceBundleFromResults,
} from "../src/agent/serviceNavigationAgent";
import { createAgentChatController } from "../src/agent/chatController";
import type { AgentSurfaceApi } from "../src/agent/surfaceApi";
import type {
  AgentMessage,
  AgentPermissionLevel,
  AgentToolCall,
  AgentToolResult,
  EvidenceBundle,
  SurfaceContext,
} from "../src/agent/types";
import type { AppActionResult } from "../src/app/appActions";
import type { RouteId } from "../src/models/abby";
import { build211GraphRagPrompt, DEFAULT_GRAPH_RAG_MODEL_MAX_TOKENS } from "../src/lib/graphrag";
import type { GraphRagEvidence, SearchResult } from "../src/lib/graphrag";
import { clientLLMWorkerService } from "../src/lib/clientLLMWorkerService";
import { LLM_CONFIG } from "../src/lib/llmConfig";

const NOW = "2026-05-05T12:00:00.000Z";
const WORKER_RESTART_REQUIRED_PREFIX = "ABBY_LLM_WORKER_RESTART_REQUIRED:";

type ClientLlmDevice = "wasm" | "webgpu" | "auto";

interface TestLlmCapabilities {
  webGPU: boolean;
  webGPUError?: string;
  webGPUShaderF16?: boolean;
  simd: boolean;
  wasmThreads: boolean;
  crossOriginIsolated: boolean;
  sharedArrayBuffer: boolean;
}

interface TestLlmWorkerResponse {
  modelName?: string;
  capabilities?: TestLlmCapabilities;
  device?: ClientLlmDevice;
  isInitialized?: boolean;
}

interface TestableClientLLMWorkerService {
  worker: { terminate: () => void } | null;
  isInitialized: boolean;
  isInitializing: boolean;
  currentModel: string;
  currentDevice: ClientLlmDevice;
  webGPUFallbackReason?: string;
  capabilities: TestLlmCapabilities;
  pendingRequests: Map<string, { reject: (reason?: unknown) => void }>;
  requestCounter: number;
  initialize: (modelName?: string) => Promise<void>;
  getCapabilities: () => Promise<TestLlmWorkerResponse>;
  getStatus: () => {
    currentDevice: ClientLlmDevice;
    currentModel: string;
    capabilities: TestLlmCapabilities;
    isInitialized: boolean;
  };
  initializeWorker: () => void;
  sendWorkerRequest: (type: string, data: { modelName?: string }, timeoutMs: number) => Promise<TestLlmWorkerResponse>;
}

function createSurfaceContext(
  route: RouteId,
  overrides: Partial<SurfaceContext> = {},
): SurfaceContext {
  return {
    route,
    routeLabel: route,
    capturedAt: NOW,
    walletUnlocked: true,
    privateContextAllowed: false,
    permissionLevel: "public",
    ...overrides,
  };
}

function createToolCall(name: string, input: unknown): AgentToolCall {
  return {
    id: `tool-${name}`,
    sessionId: "agent-session-unit",
    name,
    input,
    status: "pending",
    requestedAt: NOW,
  };
}

function createFakeSurfaceApi(
  context: SurfaceContext,
  invoked: AgentToolCall[] = [],
): AgentSurfaceApi {
  const successOutput = (name: string): AppActionResult => ({
    ok: true,
    action: name,
    summary: `Ran ${name}`,
  } as AppActionResult);

  return {
    getContext: () => context,
    invoke: async (name) => successOutput(name),
    invokeRequest: async (request) => successOutput(request.name),
    invokeToolCall: async (toolCall): Promise<AgentToolResult> => {
      invoked.push(toolCall);
      return {
        id: `tool-result-${toolCall.id}`,
        toolCallId: toolCall.id,
        name: toolCall.name,
        success: true,
        completedAt: NOW,
        output: successOutput(toolCall.name),
        auditEventId: `audit-${toolCall.id}`,
      };
    },
  };
}

function createSearchResult(docId: string, providerName: string): SearchResult {
  return {
    docId,
    contentCid: `cid-${docId}`,
    pageCid: `page-${docId}`,
    score: 9.5,
    scoreParts: { keyword: 9.5, vector: 0, metadata: 0 },
    snippet: `${providerName} offers pantry appointments and referral support.`,
    document: {
      doc_id: docId,
      doc_type: "service",
      title: `${providerName} program`,
      text: `${providerName} offers pantry appointments and referral support in Portland.`,
      text_truncated: false,
      source_url: `https://211.example.test/services/${docId}`,
      source_content_cid: `cid-${docId}`,
      source_page_cid: `page-${docId}`,
      provider_name: providerName,
      program_name: "Pantry appointments",
      categories: "Food",
      host: "211.example.test",
      city: "Portland",
      state: "OR",
    },
  };
}

test.describe("agent unit contracts", () => {
  test("validates command schemas and rejects malformed command payloads", () => {
    expect(validateCommandSchemas()).toEqual([]);
    expect(validateSurfaceRegistry()).toEqual([]);

    expect(commandSchemas.navigate.isInput({ route: "social-services" })).toBe(true);
    expect(commandSchemas.navigate.isInput({ route: "service-detail" })).toBe(false);

    expect(commandSchemas.search_211_services.isInput({ query: "food pantry", limit: 8 })).toBe(true);
    expect(commandSchemas.search_211_services.isInput({ query: "food pantry", limit: 0 })).toBe(false);
    expect(commandSchemas.search_211_services.isInput({ query: "   ", limit: 8 })).toBe(false);

    expect(commandSchemas.create_verified_export_bundle.isInput({
      audienceName: "Benefits clinic",
      recordIds: ["rec-1"],
      proofIds: ["proof-1"],
    })).toBe(true);
    expect(commandSchemas.create_verified_export_bundle.isInput({
      audienceName: "Benefits clinic",
      recordIds: [],
    })).toBe(false);

    expect(isCommandOutputFor("search_211_services", {
      ok: true,
      summary: "Found pantry records.",
      evidenceBundle: {
        id: "evidence-1",
        query: "pantry",
        generatedAt: NOW,
        items: [{
          id: "svc-food-1",
          title: "Neighborhood Pantry",
          source: "211 corpus",
          snippet: "Food pantry referrals.",
          citation: { label: "Neighborhood Pantry", docId: "svc-food-1" },
        }],
      } satisfies EvidenceBundle,
      recordIds: ["svc-food-1"],
    })).toBe(true);
    expect(isCommandOutputFor("search_211_services", {
      ok: true,
      summary: "Broken evidence.",
      evidenceBundle: { id: "missing-items" },
    })).toBe(false);
  });

  test("routes deterministic planner turns to app, service, wallet, and confirmation actions", () => {
    const homeContext = createSurfaceContext("home");
    const serviceSearch = planAgentTurn({
      content: "Find food pantry services near me",
      context: homeContext,
    });

    expect(serviceSearch.intentKind).toBe("service_navigation");
    expect(serviceSearch.tools.map((tool) => tool.name)).toEqual(["navigate", "search_211_services"]);
    expect(serviceSearch.tools[0].input).toEqual({ route: "social-services" });
    expect(serviceSearch.tools[1].input).toEqual({
      query: "Find food pantry services near me",
      limit: 8,
    });

    const auditTurn = planAgentTurn({
      content: "Open the latest audit history",
      context: createSurfaceContext("home"),
    });
    expect(auditTurn.tools.map((tool) => tool.name)).toEqual(["navigate", "summarize_audit_events"]);
    expect(auditTurn.tools[0].input).toEqual({ route: "audit" });
    expect(auditTurn.tools[1].input).toEqual({ limit: 25 });

    const auditRefreshTurn = planAgentTurn({
      content: "Refresh audit activity",
      context: createSurfaceContext("home"),
    });
    expect(auditRefreshTurn.tools.map((tool) => tool.name)).toEqual(["navigate", "refresh_wallet_audit"]);
    expect(auditRefreshTurn.tools[0].input).toEqual({ route: "audit" });
    expect(auditRefreshTurn.tools[1].input).toEqual({ limit: 25 });

    const saveTurn = planAgentTurn({
      content: "Save this service",
      context: createSurfaceContext("social-services", {
        selectedServiceDocId: "svc-food-1",
        visibleServiceDocIds: ["svc-food-1"],
      }),
    });
    expect(saveTurn.intentKind).toBe("wallet_action");
    expect(saveTurn.tools).toEqual([{
      name: "save_service",
      input: { serviceId: "svc-food-1" },
      title: getToolDefinition("save_service").title,
    }]);

    const confirmationTurn = planAgentTurn({
      content: "yes, go ahead",
      context: createSurfaceContext("social-services"),
      pendingConfirmations: [{
        id: "confirmation-save",
        sessionId: "agent-session-unit",
        toolCallId: "tool-save",
        title: "Save service",
        summary: "Save service svc-food-1.",
        risk: "high",
        permissionLevel: "write_wallet",
        status: "pending",
        requestedAt: NOW,
      }],
    });
    expect(confirmationTurn.confirmationDecision).toEqual({
      confirmationId: "confirmation-save",
      approved: true,
    });

    const serviceAnswerTurn = planAgentTurn({
      content: "Do you know about eviction help?",
      context: createSurfaceContext("social-services"),
    });
    expect(serviceAnswerTurn.tools.map((tool) => tool.name)).toEqual(["answer_211_question"]);
    expect(serviceAnswerTurn.tools[0].input).toEqual({
      question: "Do you know about eviction help?",
      useLocalModel: true,
    });
  });

  test("enforces permission gates before tools can run", () => {
    const savePolicy = getAgentToolPermissionPolicy("save_service");
    expect(savePolicy.gate).toBe("write_wallet");
    expect(confirmationRiskForGate(savePolicy.gate)).toBe("high");

    expect(evaluateAgentToolPermissionPolicy("save_service", {
      route: "home",
      allowedSurfaces: ["social-services"],
      grantedPermissionLevel: "write_wallet",
      walletUnlocked: true,
      privateContextAllowed: false,
      userPresent: true,
      toolTitle: "Save service",
    })).toMatchObject({ ok: false, code: "surface_not_allowed" });

    expect(evaluateAgentToolPermissionPolicy("save_service", {
      route: "social-services",
      allowedSurfaces: ["social-services"],
      grantedPermissionLevel: "public",
      walletUnlocked: true,
      privateContextAllowed: false,
      userPresent: true,
      toolTitle: "Save service",
    })).toMatchObject({ ok: false, code: "permission_denied" });

    expect(evaluateAgentToolPermissionPolicy("save_service", {
      route: "social-services",
      allowedSurfaces: ["social-services"],
      grantedPermissionLevel: "write_wallet",
      walletUnlocked: false,
      privateContextAllowed: false,
      userPresent: true,
      toolTitle: "Save service",
    })).toMatchObject({ ok: false, code: "wallet_locked" });

    expect(evaluateAgentToolPermissionPolicy("create_service_plan", {
      route: "social-services",
      allowedSurfaces: ["social-services"],
      grantedPermissionLevel: "write_wallet",
      walletUnlocked: true,
      privateContextAllowed: false,
      userPresent: true,
      toolTitle: "Create service plan",
    })).toMatchObject({ ok: false, code: "private_context_required" });
  });

  test("requires confirmation for wallet writes and executes public reads directly", async () => {
    const invoked: AgentToolCall[] = [];
    let idCounter = 0;
    const executor = createAgentToolExecutor({
      surfaceApi: createFakeSurfaceApi(createSurfaceContext("social-services", {
        permissionLevel: "write_wallet",
        walletUnlocked: true,
      }), invoked),
      sessionId: "agent-session-unit",
      now: () => NOW,
      createId: (prefix) => `${prefix}-${++idCounter}`,
    });

    const publicRead = await executor.execute("search_211_services", { query: "pantry", limit: 3 });
    expect(publicRead.status).toBe("succeeded");
    expect(invoked.map((toolCall) => toolCall.name)).toEqual(["search_211_services"]);

    const save = await executor.execute("save_service", { serviceId: "svc-food-1" });
    expect(save.status).toBe("waiting_for_confirmation");
    expect(save.toolCall.status).toBe("waiting_for_confirmation");
    if (save.status !== "waiting_for_confirmation") {
      throw new Error("save_service should wait for confirmation");
    }
    expect(save.confirmation).toMatchObject({
      id: "agent-confirmation-3",
      sessionId: "agent-session-unit",
      toolCallId: save.toolCall.id,
      title: "Save service",
      risk: "high",
      permissionLevel: "write_wallet",
      status: "pending",
      details: {
        permissionGate: "write_wallet",
        requiresAudit: true,
        auditEventType: "agent.service.save",
      },
    });
    expect(save.confirmation.summary).toContain("Save service svc-food-1");
    expect(invoked.map((toolCall) => toolCall.name)).toEqual(["search_211_services"]);

    const confirmed = await executor.executeToolCall(save.toolCall, {
      confirmed: true,
      confirmationId: save.confirmation.id,
    });
    expect(confirmed.status).toBe("succeeded");
    expect(invoked.map((toolCall) => toolCall.name)).toEqual(["search_211_services", "save_service"]);
  });

  test("redacts private prompt context, raw history, and raw evidence queries by default", () => {
    const privateContext = createSurfaceContext("register", {
      routeLabel: "Register",
      permissionLevel: "wallet_private",
      walletUnlocked: true,
      privateContextAllowed: true,
      selectedRecordId: "rec-state-id",
      visibleRecordIds: ["rec-state-id", "rec-medical-note"],
      summary: "Jordan is at 123 Main Street and uses jordan@example.test.",
      metadata: {
        visibleCount: 2,
        phone: "503-555-0199",
        privateNotes: "notes: disclose only at intake",
        documentContents: "document: full benefits letter text",
        currentLocation: "45.5201, -122.6802",
      },
    });

    const safe = buildPromptSafeSurfaceContext(privateContext);
    expect(safe.permissionLevel).toBe("app_context");
    expect(safe.privateContextAllowed).toBe(false);
    expect(safe.summary).toBe("Register surface is active.");
    expect(safe.selectedRecordId).toBeUndefined();
    expect(safe.visibleRecordIds).toBeUndefined();
    expect(safe.metadata).toEqual({ visibleCount: 2 });
    expect(safe.redactions.join("\n")).toContain("Private route summaries are replaced");
    expect(JSON.stringify(safe)).not.toContain("jordan@example.test");
    expect(JSON.stringify(safe)).not.toContain("503-555-0199");
    expect(JSON.stringify(safe)).not.toContain("rec-state-id");

    expect(guardPromptText(
      "Email jordan@example.test, call 503-555-0199, private notes: urgent intake.",
      "user.message",
    )).toBe("Email [redacted private contact], call [redacted private contact], [redacted private notes].");

    const history: AgentMessage[] = [{
      id: "message-user",
      sessionId: "agent-session-unit",
      role: "user",
      content: "My phone is 503-555-0199. Find shelter.",
      createdAt: NOW,
      status: "complete",
    }];
    expect(compactPromptConversationHistory(history)).toEqual([{
      role: "user",
      content: "[redacted prior user query]",
      createdAt: NOW,
      status: "complete",
    }]);

    const evidence = evidenceBundleFromResults("pantry near 123 Main Street", [
      createSearchResult("svc-food-1", "Neighborhood Pantry"),
    ]);
    expect(guardEvidenceBundles([evidence])[0].query).toBe("[redacted raw query]");

    const visibleTools = guardAgentToolDefinitions(agentToolDefinitions, privateContext);
    expect(visibleTools.map((tool) => tool.name)).not.toContain("update_registration_draft");
  });

  test("allows explicitly approved private prompt context without exposing unrelated categories", () => {
    const privateContext = createSurfaceContext("register", {
      routeLabel: "Register",
      permissionLevel: "wallet_private",
      walletUnlocked: true,
      privateContextAllowed: true,
      selectedRecordId: "rec-state-id",
      visibleRecordIds: ["rec-state-id"],
      summary: "Profile email is jordan@example.test.",
      metadata: {
        phone: "503-555-0199",
        currentLocation: "45.5201, -122.6802",
        documentContents: "document: full benefits letter text",
      },
    });

    const safe = buildPromptSafeSurfaceContext(privateContext, {
      includePrivateWalletContext: true,
    });

    expect(safe.permissionLevel).toBe("wallet_private");
    expect(safe.privateContextAllowed).toBe(true);
    expect(safe.selectedRecordId).toBe("rec-state-id");
    expect(safe.summary).toBe("Profile email is jordan@example.test.");
    expect(safe.metadata).toEqual({ phone: "503-555-0199" });
    expect(JSON.stringify(safe)).not.toContain("45.5201");
    expect(JSON.stringify(safe)).not.toContain("full benefits letter text");
    expect(safe.redactions.join("\n")).toContain("metadata.currentLocation");
    expect(safe.redactions.join("\n")).toContain("metadata.documentContents");
  });

  test("maps GraphRAG evidence into citations, record IDs, and actionable next steps", () => {
    const first = createSearchResult("svc-food-1", "Neighborhood Pantry");
    const second = createSearchResult("svc-food-2", "Community Kitchen");

    const evidence = evidenceBundleFromResults("food pantry", [first, second]);
    expect(evidence.id).toMatch(/^evidence-/);
    expect(evidence.items.map((item) => item.id)).toEqual(["svc-food-1", "svc-food-2"]);
    expect(evidence.items[0]).toMatchObject({
      title: "Neighborhood Pantry program",
      source: "https://211.example.test/services/svc-food-1",
      citation: {
        label: "Neighborhood Pantry program",
        url: "https://211.example.test/services/svc-food-1",
        contentCid: "cid-svc-food-1",
        pageCid: "page-svc-food-1",
        docId: "svc-food-1",
      },
    });

    expect(buildServiceNavigationNextSteps([first, second])).toEqual([
      "Open service detail svc-food-1 to review Neighborhood Pantry.",
      "After you review a record, you can ask Abby to save it or create a follow-up plan; wallet writes require confirmation.",
    ]);
    expect(buildServiceNavigationNextSteps([])).toEqual([
      "Try a more specific service type, neighborhood, or eligibility term.",
      "For urgent service navigation, contact 211 directly.",
    ]);
  });

  test("keeps GraphRAG prompts compact and citation-oriented for browser inference", () => {
    const longSnippet = "Food pantry intake and grocery pickup details. ".repeat(40);
    const results = Array.from({ length: 6 }, (_, index) => {
      const result = createSearchResult(`svc-food-${index + 1}`, `Provider ${index + 1}`);
      result.snippet = longSnippet;
      return result;
    });
    const evidence: GraphRagEvidence = {
      query: "food pantry near Portland",
      results,
      nodes: Array.from({ length: 12 }, (_, index) => ({
        node_id: `node-${index + 1}`,
        node_type: "category",
        label: `Graph node ${index + 1}`,
      })),
      edges: Array.from({ length: 12 }, (_, index) => ({
        source: `node-${index + 1}`,
        target: `node-${Math.min(index + 2, 12)}`,
        relation: "RELATED_TO",
        edge_cid: `edge-${index + 1}`,
      })),
    };

    const prompt = build211GraphRagPrompt("Which food pantry should I try?", evidence);

    expect(DEFAULT_GRAPH_RAG_MODEL_MAX_TOKENS).toBeLessThanOrEqual(160);
    expect(prompt).toContain("Keep it under 120 words");
    expect(prompt).toContain("Cite every bullet");
    expect(prompt).toContain("[4] Provider 4");
    expect(prompt).not.toContain("[5] Provider 5");
    expect(prompt).toContain("Graph node 8");
    expect(prompt).not.toContain("Graph node 9");
    expect(prompt.length).toBeLessThan(5200);
  });

  test("keeps every registered tool tied to a concrete permission policy", () => {
    for (const tool of agentToolDefinitions) {
      const commandName = tool.name as AgentCommandName;
      const policy = getAgentToolPermissionPolicy(commandName);
      expect(tool.requiresConfirmation).toBe(policy.requiresConfirmation);
      expect(tool.requiresAudit).toBe(policy.requiresAudit);
      expect(tool.requiresWalletUnlock).toBe(policy.requiresWalletUnlock);
      expect(tool.requiresUserPresence).toBe(policy.requiresUserPresence);
      expect(tool.requiresPrivateContextOptIn).toBe(policy.requiresPrivateContextOptIn);
      expect(tool.permissionLevel as AgentPermissionLevel).toBeTruthy();
    }
  });

  test("caches chat snapshots until controller state changes", () => {
    const controller = createAgentChatController({
      surfaceApi: createFakeSurfaceApi(createSurfaceContext("home")),
      now: () => NOW,
      createId: (prefix) => `${prefix}-unit`,
    });

    const initial = controller.getSnapshot();
    expect(controller.getSnapshot()).toBe(initial);

    controller.setActiveRoute("exports");
    const updated = controller.getSnapshot();

    expect(updated).not.toBe(initial);
    expect(updated.session.activeRoute).toBe("exports");
    expect(controller.getSnapshot()).toBe(updated);
  });

  test("uses the local LLM service for general assistant chat responses", async () => {
    const invoked: AgentToolCall[] = [];
    const prompts: string[] = [];
    const controller = createAgentChatController({
      surfaceApi: createFakeSurfaceApi(createSurfaceContext("home"), invoked),
      enableLocalLlmToolSelection: false,
      enableLocalLlmResponses: true,
      localLlmService: {
        tryGenerateText: async (prompt) => {
          prompts.push(prompt);
          return {
            ok: true,
            text: "Abby: I can explain this screen and help you move to the right app surface.",
            modelName: "test-local-model",
          };
        },
        generateStructuredText: async () => ({
          ok: false,
          text: "",
          error: "not used",
        }),
      },
      now: () => NOW,
      createId: (prefix) => `${prefix}-unit`,
    });

    await controller.sendMessage("hello there");

    expect(invoked).toEqual([]);
    expect(prompts[0]).toContain("Safe app context");
    expect(controller.getSnapshot().messages.at(-1)?.content).toBe(
      "I can explain this screen and help you move to the right app surface.",
    );
  });

  test("falls back when local LLM capability answers are too generic", async () => {
    const invoked: AgentToolCall[] = [];
    const controller = createAgentChatController({
      surfaceApi: createFakeSurfaceApi(createSurfaceContext("home"), invoked),
      enableLocalLlmToolSelection: false,
      enableLocalLlmResponses: true,
      localLlmService: {
        tryGenerateText: async () => ({
          ok: true,
          text: "Sure! What can I assist you with today?",
          modelName: "test-local-model",
        }),
        generateStructuredText: async () => ({
          ok: false,
          text: "",
          error: "not used",
        }),
      },
      now: () => NOW,
      createId: (prefix) => `${prefix}-unit`,
    });

    await controller.sendMessage("What can you help me with?");

    expect(invoked).toEqual([]);
    expect(controller.getSnapshot().messages.at(-1)?.content).toMatch(
      /I can explain this screen, navigate the app, answer public 211 service questions, and ask for confirmation before changing wallet data\./,
    );
  });

  test("uses local LLM tool selection by default before falling back to deterministic responses", async () => {
    const invoked: AgentToolCall[] = [];
    const controller = createAgentChatController({
      surfaceApi: createFakeSurfaceApi(createSurfaceContext("home"), invoked),
      localLlmService: {
        tryGenerateText: async () => ({
          ok: true,
          text: "not used",
        }),
        generateStructuredText: async () => ({
          ok: true,
          text: "{\"action\":\"call_tool\",\"tool\":\"navigate\",\"input\":{\"route\":\"exports\"},\"message\":\"Open Exports.\"}",
          json: {
            action: "call_tool",
            tool: "navigate",
            input: { route: "exports" },
            message: "Open Exports.",
          },
          modelName: "test-local-model",
        }),
      },
      now: () => NOW,
      createId: (prefix) => `${prefix}-unit`,
    });

    await controller.sendMessage("organize my verified packet");

    expect(invoked.map((toolCall) => toolCall.name)).toEqual(["navigate"]);
    expect(invoked[0].input).toEqual({ route: "exports" });
  });

  test("restarts the LLM worker before using WASM fallback after WebGPU runtime failure", async () => {
    const service = clientLLMWorkerService as unknown as TestableClientLLMWorkerService;
    const originalState = {
      worker: service.worker,
      isInitialized: service.isInitialized,
      isInitializing: service.isInitializing,
      currentModel: service.currentModel,
      currentDevice: service.currentDevice,
      webGPUFallbackReason: service.webGPUFallbackReason,
      capabilities: service.capabilities,
      pendingRequests: service.pendingRequests,
      requestCounter: service.requestCounter,
      initializeWorker: service.initializeWorker,
      sendWorkerRequest: service.sendWorkerRequest,
      consoleWarn: console.warn,
    };
    const calls: string[] = [];
    const baseCapabilities: TestLlmCapabilities = {
      webGPU: true,
      webGPUShaderF16: false,
      simd: true,
      wasmThreads: true,
      crossOriginIsolated: true,
      sharedArrayBuffer: true,
    };

    try {
      console.warn = () => undefined;
      service.worker = { terminate: () => calls.push("terminate") };
      service.isInitialized = false;
      service.isInitializing = false;
      service.currentModel = LLM_CONFIG.defaultModel;
      service.currentDevice = "webgpu";
      service.webGPUFallbackReason = undefined;
      service.capabilities = baseCapabilities;
      service.pendingRequests = new Map();
      service.requestCounter = 0;
      service.initializeWorker = () => {
        calls.push("initializeWorker");
        service.worker = { terminate: () => calls.push("terminate-fallback") };
      };
      service.sendWorkerRequest = async (type, data) => {
        calls.push(`${type}:${data.modelName || ""}`);
        if (type === "initialize" && data.modelName === LLM_CONFIG.defaultModel) {
          throw new Error(`${WORKER_RESTART_REQUIRED_PREFIX}WebGPU execution failed for test model.`);
        }
        if (type === "initialize" && data.modelName === LLM_CONFIG.fallbackModel) {
          return {
            isInitialized: true,
            modelName: LLM_CONFIG.fallbackModel,
            device: "wasm",
            capabilities: baseCapabilities,
          };
        }
        if (type === "getCapabilities") {
          return {
            isInitialized: true,
            modelName: LLM_CONFIG.fallbackModel,
            device: "wasm",
            capabilities: baseCapabilities,
          };
        }
        throw new Error(`Unexpected worker request ${type}`);
      };

      await service.initialize(LLM_CONFIG.defaultModel);
      const status = service.getStatus();
      const capabilities = await service.getCapabilities();

      expect(calls).toEqual([
        `initialize:${LLM_CONFIG.defaultModel}`,
        "terminate",
        "initializeWorker",
        `initialize:${LLM_CONFIG.fallbackModel}`,
        "getCapabilities:",
      ]);
      expect(status).toMatchObject({
        currentModel: LLM_CONFIG.fallbackModel,
        currentDevice: "wasm",
        isInitialized: true,
      });
      expect(status.capabilities.webGPUError).toContain("WebGPU execution failed");
      expect(capabilities.capabilities?.webGPUError).toContain("WebGPU execution failed");
    } finally {
      service.worker = originalState.worker;
      service.isInitialized = originalState.isInitialized;
      service.isInitializing = originalState.isInitializing;
      service.currentModel = originalState.currentModel;
      service.currentDevice = originalState.currentDevice;
      service.webGPUFallbackReason = originalState.webGPUFallbackReason;
      service.capabilities = originalState.capabilities;
      service.pendingRequests = originalState.pendingRequests;
      service.requestCounter = originalState.requestCounter;
      service.initializeWorker = originalState.initializeWorker;
      service.sendWorkerRequest = originalState.sendWorkerRequest;
      console.warn = originalState.consoleWarn;
    }
  });
});
