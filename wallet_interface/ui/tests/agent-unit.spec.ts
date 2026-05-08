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
import { AUDIO_CHAT_CONFIG, getClientAudioModelInfo } from "../src/lib/audioChatConfig";
import { ClientAudioReplyService, type ClientAudioProgress } from "../src/lib/clientAudioReplyService";
import { LLM_CONFIG, SUPPORTED_CLIENT_LLM_MODELS, type ClientLlmModel } from "../src/lib/llmConfig";
import { OPENROUTER_API_KEY_STORAGE_KEY } from "../src/lib/openRouterClient";

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
  text?: string;
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
  capabilitiesKnown: boolean;
  webGPUFallbackReason?: string;
  openRouterFallbackDelayMs: number;
  openRouterLastError?: string;
  openRouterLastUsedAt?: string;
  lastGenerationModel: string;
  lastGenerationProvider: "local" | "openrouter";
  generationCounter: number;
  generationWinnerId: number;
  capabilities: TestLlmCapabilities;
  pendingRequests: Map<string, { reject: (reason?: unknown) => void }>;
  requestCounter: number;
  initialize: (modelName?: string) => Promise<void>;
  switchModel: (modelName: string) => Promise<void>;
  generateText: (prompt: string, maxTokens?: number) => Promise<string>;
  getCapabilities: () => Promise<TestLlmWorkerResponse>;
  getStatus: () => {
    currentDevice: ClientLlmDevice;
    currentModel: string;
    capabilities: TestLlmCapabilities;
    isInitialized: boolean;
  };
  initializeWorker: () => void;
  sendWorkerRequest: (
    type: string,
    data: { modelName?: string; prompt?: string; maxTokens?: number },
    timeoutMs: number,
  ) => Promise<TestLlmWorkerResponse>;
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

function installMemoryLocalStorage() {
  const original = Object.getOwnPropertyDescriptor(globalThis, "localStorage");
  const values = new Map<string, string>();
  const storage = {
    clear: () => values.clear(),
    getItem: (key: string) => values.get(key) ?? null,
    key: (index: number) => Array.from(values.keys())[index] ?? null,
    removeItem: (key: string) => values.delete(key),
    setItem: (key: string, value: string) => values.set(key, value),
    get length() {
      return values.size;
    },
  } as Storage;
  Object.defineProperty(globalThis, "localStorage", {
    configurable: true,
    value: storage,
  });
  return () => {
    if (original) {
      Object.defineProperty(globalThis, "localStorage", original);
    } else {
      delete (globalThis as { localStorage?: Storage }).localStorage;
    }
  };
}

interface TestAudioWorkerRequest {
  id: string;
  type: "generateAudio" | "warmUp";
  data: {
    modelName?: string;
    text?: string;
  };
}

interface TestAudioWorkerStub {
  onmessage: ((event: MessageEvent) => void) | null;
  onerror: ((event: ErrorEvent) => void) | null;
  postMessage: (message: TestAudioWorkerRequest) => void;
  terminate: () => void;
}

function createAudioWorkerStub(
  handler: (message: TestAudioWorkerRequest, worker: TestAudioWorkerStub) => void,
): TestAudioWorkerStub {
  const worker: TestAudioWorkerStub = {
    onmessage: null,
    onerror: null,
    postMessage: (message) => handler(message, worker),
    terminate: () => undefined,
  };
  return worker;
}

function emitAudioWorkerMessage(worker: TestAudioWorkerStub, data: unknown) {
  worker.onmessage?.({ data } as MessageEvent);
}

test.describe("agent unit contracts", () => {
  test("uses LiquidAI ONNX text-chat models for the default WebGPU client LLM path", () => {
    const defaultModelName = LLM_CONFIG.defaultModel as ClientLlmModel;
    const defaultModel = SUPPORTED_CLIENT_LLM_MODELS[defaultModelName];
    const thinkingModel = SUPPORTED_CLIENT_LLM_MODELS["LiquidAI/LFM2.5-1.2B-Thinking-ONNX"];

    expect(defaultModelName).toBe("LiquidAI/LFM2.5-1.2B-Instruct-ONNX");
    expect(defaultModel).toMatchObject({
      task: "text-generation",
      inputMode: "chat",
      device: "webgpu",
      requiresWebGPU: true,
      dtype: "q4f16",
      quantized: true,
    });
    expect(thinkingModel).toMatchObject({
      task: "text-generation",
      inputMode: "chat",
      device: "webgpu",
      requiresWebGPU: true,
      dtype: "q4f16",
      quantized: true,
    });
  });

  test("configures LiquidAI audio chat separately from text chat models", () => {
    const audioModel = getClientAudioModelInfo(AUDIO_CHAT_CONFIG.defaultModel);

    expect(AUDIO_CHAT_CONFIG.defaultModel).toBe("LiquidAI/LFM2.5-Audio-1.5B-ONNX");
    expect(audioModel).toMatchObject({
      task: "text-to-audio",
      device: "webgpu",
      dtype: "q4",
      requiresWebGPU: true,
      quantized: true,
    });
    expect(AUDIO_CHAT_CONFIG.liquidAudioRunnerBaseUrl).toContain("LFM2.5-Audio-1.5B-transformers-js");
    expect(AUDIO_CHAT_CONFIG.maxAudioFrames).toBeGreaterThan(0);
    expect(SUPPORTED_CLIENT_LLM_MODELS).not.toHaveProperty(AUDIO_CHAT_CONFIG.defaultModel);
  });

  test("falls back to browser speech when local LiquidAI audio cannot start", async () => {
    const service = new ClientAudioReplyService({
      createWorker: () => {
        throw new Error("test audio worker unavailable");
      },
      hasWebGPU: () => true,
      hasSpeechSynthesis: () => true,
    });

    const result = await service.generateAudio("Read this assistant reply aloud.");

    expect(result).toMatchObject({
      kind: "browser-speech",
      provider: "browser-speech",
      modelName: AUDIO_CHAT_CONFIG.fallbackVoiceModel,
      fallbackForModel: AUDIO_CHAT_CONFIG.defaultModel,
    });
    expect(result.kind === "browser-speech" ? result.fallbackReason : "").toContain("test audio worker unavailable");
  });

  test("reports LiquidAI audio model warmup progress from the worker", async () => {
    const progressEvents: ClientAudioProgress[] = [];
    const worker = createAudioWorkerStub((message, activeWorker) => {
      emitAudioWorkerMessage(activeWorker, {
        id: message.id,
        type: "progress",
        progress: {
          phase: "loading-runtime",
          progress: 4,
          status: "Loading LiquidAI audio runtime.",
          modelName: message.data.modelName,
        },
      });
      emitAudioWorkerMessage(activeWorker, {
        id: message.id,
        type: "progress",
        progress: {
          phase: "downloading-model",
          progress: 42,
          status: "Downloading audio model.",
          file: "decoder_model_quantized.onnx",
          modelName: message.data.modelName,
        },
      });
      emitAudioWorkerMessage(activeWorker, {
        id: message.id,
        success: true,
        data: {
          modelName: message.data.modelName,
          provider: "local-liquidai",
        },
      });
    });
    const service = new ClientAudioReplyService({
      createWorker: () => worker as unknown as Worker,
      hasWebGPU: () => true,
      hasSpeechSynthesis: () => false,
    });

    const result = await service.warmUp({ onProgress: (progress) => progressEvents.push(progress) });

    expect(result).toMatchObject({
      kind: "local-ready",
      modelName: AUDIO_CHAT_CONFIG.defaultModel,
      provider: "local-liquidai",
    });
    expect(progressEvents).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ phase: "queued", progress: 0 }),
        expect.objectContaining({ phase: "loading-runtime", progress: 4 }),
        expect.objectContaining({
          phase: "downloading-model",
          progress: 42,
          file: "decoder_model_quantized.onnx",
        }),
      ]),
    );
  });

  test("reports LiquidAI audio generation progress before returning a playable blob", async () => {
    const progressEvents: ClientAudioProgress[] = [];
    const audioBlob = new Blob(["RIFF....WAVE"], { type: "audio/wav" });
    const worker = createAudioWorkerStub((message, activeWorker) => {
      emitAudioWorkerMessage(activeWorker, {
        id: message.id,
        type: "progress",
        progress: {
          phase: "generating",
          progress: 90,
          status: "Generating speech audio.",
          modelName: message.data.modelName,
        },
      });
      emitAudioWorkerMessage(activeWorker, {
        id: message.id,
        type: "progress",
        progress: {
          phase: "decoding",
          progress: 97,
          status: "Decoding generated audio.",
          modelName: message.data.modelName,
        },
      });
      emitAudioWorkerMessage(activeWorker, {
        id: message.id,
        success: true,
        data: {
          audioBlob,
          mimeType: "audio/wav",
          modelName: message.data.modelName,
          provider: "local-liquidai",
        },
      });
    });
    const service = new ClientAudioReplyService({
      createWorker: () => worker as unknown as Worker,
      hasWebGPU: () => true,
      hasSpeechSynthesis: () => false,
    });

    const result = await service.generateAudio("Please speak this reply.", {
      onProgress: (progress) => progressEvents.push(progress),
    });

    expect(result).toMatchObject({
      kind: "audio",
      audioBlob,
      mimeType: "audio/wav",
      modelName: AUDIO_CHAT_CONFIG.defaultModel,
      provider: "local-liquidai",
    });
    expect(progressEvents).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ phase: "generating", progress: 90 }),
        expect.objectContaining({ phase: "decoding", progress: 97 }),
      ]),
    );
  });

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

  test("uses OpenRouter when WebGPU is unavailable for the default client LLM", async () => {
    const service = clientLLMWorkerService as unknown as TestableClientLLMWorkerService;
    const restoreStorage = installMemoryLocalStorage();
    const originalState = {
      worker: service.worker,
      isInitialized: service.isInitialized,
      isInitializing: service.isInitializing,
      currentModel: service.currentModel,
      currentDevice: service.currentDevice,
      capabilitiesKnown: service.capabilitiesKnown,
      webGPUFallbackReason: service.webGPUFallbackReason,
      openRouterLastError: service.openRouterLastError,
      openRouterLastUsedAt: service.openRouterLastUsedAt,
      lastGenerationModel: service.lastGenerationModel,
      lastGenerationProvider: service.lastGenerationProvider,
      generationCounter: service.generationCounter,
      generationWinnerId: service.generationWinnerId,
      capabilities: service.capabilities,
      pendingRequests: service.pendingRequests,
      requestCounter: service.requestCounter,
      sendWorkerRequest: service.sendWorkerRequest,
      fetch: globalThis.fetch,
    };
    const calls: string[] = [];
    let requestBody: any;

    try {
      globalThis.localStorage.setItem(OPENROUTER_API_KEY_STORAGE_KEY, "test-openrouter-key");
      service.worker = { terminate: () => undefined };
      service.isInitialized = false;
      service.isInitializing = false;
      service.currentModel = LLM_CONFIG.defaultModel;
      service.currentDevice = "wasm";
      service.capabilitiesKnown = true;
      service.webGPUFallbackReason = undefined;
      service.openRouterLastError = undefined;
      service.openRouterLastUsedAt = undefined;
      service.lastGenerationModel = LLM_CONFIG.defaultModel;
      service.lastGenerationProvider = "local";
      service.generationWinnerId = 0;
      service.capabilities = {
        webGPU: false,
        webGPUError: "navigator.gpu is unavailable",
        webGPUShaderF16: false,
        simd: true,
        wasmThreads: true,
        crossOriginIsolated: true,
        sharedArrayBuffer: true,
      };
      service.pendingRequests = new Map();
      service.requestCounter = 0;
      service.sendWorkerRequest = async (type) => {
        calls.push(type);
        throw new Error("local worker should not be used before OpenRouter");
      };
      globalThis.fetch = async (_input, init) => {
        requestBody = JSON.parse(String(init?.body || "{}"));
        return new Response(
          JSON.stringify({
            model: "liquid/lfm-2.5-1.2b-instruct:free",
            choices: [{ message: { role: "assistant", content: "remote answer" } }],
          }),
          { headers: { "Content-Type": "application/json" }, status: 200 },
        );
      };

      const text = await service.generateText("What can you do?", 64);

      expect(text).toBe("remote answer");
      expect(calls).toEqual([]);
      expect(requestBody.model).toBe("liquid/lfm-2.5-1.2b-instruct:free");
      expect(requestBody.messages[0]).toMatchObject({ role: "system" });
      expect(requestBody.max_tokens).toBe(64);
      expect(requestBody.temperature).toBe(0.1);
      expect(requestBody.top_k).toBe(50);
      expect(service.lastGenerationProvider).toBe("openrouter");
      expect(service.lastGenerationModel).toBe("liquid/lfm-2.5-1.2b-instruct:free");
    } finally {
      service.worker = originalState.worker;
      service.isInitialized = originalState.isInitialized;
      service.isInitializing = originalState.isInitializing;
      service.currentModel = originalState.currentModel;
      service.currentDevice = originalState.currentDevice;
      service.capabilitiesKnown = originalState.capabilitiesKnown;
      service.webGPUFallbackReason = originalState.webGPUFallbackReason;
      service.openRouterLastError = originalState.openRouterLastError;
      service.openRouterLastUsedAt = originalState.openRouterLastUsedAt;
      service.lastGenerationModel = originalState.lastGenerationModel;
      service.lastGenerationProvider = originalState.lastGenerationProvider;
      service.generationCounter = originalState.generationCounter;
      service.generationWinnerId = originalState.generationWinnerId;
      service.capabilities = originalState.capabilities;
      service.pendingRequests = originalState.pendingRequests;
      service.requestCounter = originalState.requestCounter;
      service.sendWorkerRequest = originalState.sendWorkerRequest;
      globalThis.fetch = originalState.fetch;
      restoreStorage();
    }
  });

  test("uses OpenRouter while the local LLM is still warming up", async () => {
    const service = clientLLMWorkerService as unknown as TestableClientLLMWorkerService;
    const restoreStorage = installMemoryLocalStorage();
    const originalState = {
      worker: service.worker,
      isInitialized: service.isInitialized,
      isInitializing: service.isInitializing,
      currentModel: service.currentModel,
      currentDevice: service.currentDevice,
      capabilitiesKnown: service.capabilitiesKnown,
      webGPUFallbackReason: service.webGPUFallbackReason,
      openRouterFallbackDelayMs: service.openRouterFallbackDelayMs,
      openRouterLastError: service.openRouterLastError,
      openRouterLastUsedAt: service.openRouterLastUsedAt,
      lastGenerationModel: service.lastGenerationModel,
      lastGenerationProvider: service.lastGenerationProvider,
      generationCounter: service.generationCounter,
      generationWinnerId: service.generationWinnerId,
      capabilities: service.capabilities,
      pendingRequests: service.pendingRequests,
      requestCounter: service.requestCounter,
      sendWorkerRequest: service.sendWorkerRequest,
      fetch: globalThis.fetch,
    };
    const calls: string[] = [];

    try {
      globalThis.localStorage.setItem(OPENROUTER_API_KEY_STORAGE_KEY, "test-openrouter-key");
      service.worker = { terminate: () => undefined };
      service.isInitialized = false;
      service.isInitializing = false;
      service.currentModel = LLM_CONFIG.defaultModel;
      service.currentDevice = "webgpu";
      service.capabilitiesKnown = true;
      service.webGPUFallbackReason = undefined;
      service.openRouterFallbackDelayMs = 1;
      service.openRouterLastError = undefined;
      service.openRouterLastUsedAt = undefined;
      service.lastGenerationModel = LLM_CONFIG.defaultModel;
      service.lastGenerationProvider = "local";
      service.generationWinnerId = 0;
      service.capabilities = {
        webGPU: true,
        webGPUShaderF16: true,
        simd: true,
        wasmThreads: true,
        crossOriginIsolated: true,
        sharedArrayBuffer: true,
      };
      service.pendingRequests = new Map();
      service.requestCounter = 0;
      service.sendWorkerRequest = async (type, data) => {
        calls.push(`${type}:${data.modelName || ""}`);
        await new Promise((resolve) => setTimeout(resolve, 25));
        if (type === "initialize") {
          service.isInitialized = true;
          return {
            isInitialized: true,
            modelName: data.modelName,
            device: "webgpu",
            capabilities: service.capabilities,
          };
        }
        if (type === "generate") {
          return {
            text: "local answer",
            modelName: LLM_CONFIG.defaultModel,
            device: "webgpu",
            capabilities: service.capabilities,
          };
        }
        throw new Error(`Unexpected worker request ${type}`);
      };
      globalThis.fetch = async () =>
        new Response(
          JSON.stringify({
            model: "liquid/lfm-2.5-1.2b-instruct:free",
            choices: [{ message: { role: "assistant", content: "remote during warmup" } }],
          }),
          { headers: { "Content-Type": "application/json" }, status: 200 },
        );

      const text = await service.generateText("Summarize housing options.", 80);
      await new Promise((resolve) => setTimeout(resolve, 60));

      expect(text).toBe("remote during warmup");
      expect(calls).toContain(`initialize:${LLM_CONFIG.defaultModel}`);
      expect(service.lastGenerationProvider).toBe("openrouter");
      expect(service.lastGenerationModel).toBe("liquid/lfm-2.5-1.2b-instruct:free");
    } finally {
      service.worker = originalState.worker;
      service.isInitialized = originalState.isInitialized;
      service.isInitializing = originalState.isInitializing;
      service.currentModel = originalState.currentModel;
      service.currentDevice = originalState.currentDevice;
      service.capabilitiesKnown = originalState.capabilitiesKnown;
      service.webGPUFallbackReason = originalState.webGPUFallbackReason;
      service.openRouterFallbackDelayMs = originalState.openRouterFallbackDelayMs;
      service.openRouterLastError = originalState.openRouterLastError;
      service.openRouterLastUsedAt = originalState.openRouterLastUsedAt;
      service.lastGenerationModel = originalState.lastGenerationModel;
      service.lastGenerationProvider = originalState.lastGenerationProvider;
      service.generationCounter = originalState.generationCounter;
      service.generationWinnerId = originalState.generationWinnerId;
      service.capabilities = originalState.capabilities;
      service.pendingRequests = originalState.pendingRequests;
      service.requestCounter = originalState.requestCounter;
      service.sendWorkerRequest = originalState.sendWorkerRequest;
      globalThis.fetch = originalState.fetch;
      restoreStorage();
    }
  });

  test("restarts the LLM worker before using WASM fallback after WebGPU runtime failure", async () => {
    const service = clientLLMWorkerService as unknown as TestableClientLLMWorkerService;
    const originalState = {
      worker: service.worker,
      isInitialized: service.isInitialized,
      isInitializing: service.isInitializing,
      currentModel: service.currentModel,
      currentDevice: service.currentDevice,
      capabilitiesKnown: service.capabilitiesKnown,
      webGPUFallbackReason: service.webGPUFallbackReason,
      openRouterLastError: service.openRouterLastError,
      openRouterLastUsedAt: service.openRouterLastUsedAt,
      lastGenerationModel: service.lastGenerationModel,
      lastGenerationProvider: service.lastGenerationProvider,
      generationCounter: service.generationCounter,
      generationWinnerId: service.generationWinnerId,
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
      service.capabilitiesKnown = true;
      service.webGPUFallbackReason = undefined;
      service.openRouterLastError = undefined;
      service.openRouterLastUsedAt = undefined;
      service.lastGenerationModel = LLM_CONFIG.defaultModel;
      service.lastGenerationProvider = "local";
      service.generationWinnerId = 0;
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

      calls.length = 0;
      await service.switchModel("onnx-community/Llama-3.2-1B-Instruct-ONNX");
      expect(calls).toEqual([]);
      expect(service.getStatus()).toMatchObject({
        currentModel: LLM_CONFIG.fallbackModel,
        currentDevice: "wasm",
        isInitialized: true,
      });
    } finally {
      service.worker = originalState.worker;
      service.isInitialized = originalState.isInitialized;
      service.isInitializing = originalState.isInitializing;
      service.currentModel = originalState.currentModel;
      service.currentDevice = originalState.currentDevice;
      service.capabilitiesKnown = originalState.capabilitiesKnown;
      service.webGPUFallbackReason = originalState.webGPUFallbackReason;
      service.openRouterLastError = originalState.openRouterLastError;
      service.openRouterLastUsedAt = originalState.openRouterLastUsedAt;
      service.lastGenerationModel = originalState.lastGenerationModel;
      service.lastGenerationProvider = originalState.lastGenerationProvider;
      service.generationCounter = originalState.generationCounter;
      service.generationWinnerId = originalState.generationWinnerId;
      service.capabilities = originalState.capabilities;
      service.pendingRequests = originalState.pendingRequests;
      service.requestCounter = originalState.requestCounter;
      service.initializeWorker = originalState.initializeWorker;
      service.sendWorkerRequest = originalState.sendWorkerRequest;
      console.warn = originalState.consoleWarn;
    }
  });
});
