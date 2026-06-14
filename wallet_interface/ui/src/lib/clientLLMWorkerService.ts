import { LLM_CONFIG, getClientLlmModelInfo } from "./llmConfig";

interface PendingRequest<T> {
  resolve: (value: T) => void;
  reject: (reason?: unknown) => void;
}

export type ClientLlmDevice = "wasm" | "webgpu" | "auto";

export interface ClientLlmRuntimeCapabilities {
  webGPU: boolean;
  webGPUError?: string;
  webGPUShaderF16?: boolean;
  webGPUAdapter?: {
    vendor?: string;
    architecture?: string;
    device?: string;
    description?: string;
  };
  simd: boolean;
  wasmThreads: boolean;
  crossOriginIsolated: boolean;
  sharedArrayBuffer: boolean;
}

export interface LlmWorkerResponse {
  text?: string;
  modelName?: string;
  device?: ClientLlmDevice;
  capabilities?: ClientLlmRuntimeCapabilities;
  isInitialized?: boolean;
}

export interface ClientLlmPromptObject {
  prompt: string;
  systemPrompt?: string;
  userPrompt?: string;
}

export type ClientLlmPromptInput = string | ClientLlmPromptObject;

export interface ClientLlmTextGenerationResult {
  ok: boolean;
  text: string;
  modelName?: string;
  error?: string;
}

export interface ClientLlmStructuredTextResult extends ClientLlmTextGenerationResult {
  json?: unknown;
  parseError?: string;
}

export interface ClientLlmRuntimeService {
  generateText(prompt: ClientLlmPromptInput, maxTokens?: number): Promise<string>;
  tryGenerateText(prompt: ClientLlmPromptInput, maxTokens?: number): Promise<ClientLlmTextGenerationResult>;
  generateStructuredText(prompt: ClientLlmPromptInput, maxTokens?: number): Promise<ClientLlmStructuredTextResult>;
}

export class ClientLLMWorkerService implements ClientLlmRuntimeService {
  private worker: Worker | null = null;
  private isInitialized = false;
  private isInitializing = false;
  private requestCounter = 0;
  private pendingRequests = new Map<string, PendingRequest<LlmWorkerResponse>>();
  private currentModel = LLM_CONFIG.defaultModel;
  private currentDevice: ClientLlmDevice = resolveModelDevice(LLM_CONFIG.defaultModel);
  private capabilities: ClientLlmRuntimeCapabilities = {
    webGPU: false,
    simd: false,
    wasmThreads: false,
    crossOriginIsolated: Boolean((globalThis as { crossOriginIsolated?: boolean }).crossOriginIsolated),
    sharedArrayBuffer: typeof SharedArrayBuffer !== "undefined",
  };

  constructor() {
    this.initializeWorker();
  }

  async initialize(modelName = this.currentModel): Promise<void> {
    if (this.isInitialized && this.currentModel === modelName) {
      return;
    }
    if (this.isInitializing) {
      while (this.isInitializing) {
        await new Promise((resolve) => window.setTimeout(resolve, 100));
      }
      return;
    }

    this.isInitializing = true;
    try {
      const result = await this.sendWorkerRequest("initialize", { modelName }, LLM_CONFIG.modelDownloadTimeoutMs);
      this.isInitialized = Boolean(result.isInitialized ?? true);
      this.currentModel = result.modelName || modelName;
      this.currentDevice = result.device || resolveModelDevice(this.currentModel);
      this.capabilities = mergeCapabilities(this.capabilities, result.capabilities);
    } finally {
      this.isInitializing = false;
    }
  }

  async switchModel(modelName: string): Promise<void> {
    const result = await this.sendWorkerRequest("switchModel", { modelName }, LLM_CONFIG.modelDownloadTimeoutMs);
    this.currentModel = result.modelName || modelName;
    this.currentDevice = result.device || resolveModelDevice(this.currentModel);
    this.capabilities = mergeCapabilities(this.capabilities, result.capabilities);
    this.isInitialized = true;
  }

  async generateText(prompt: ClientLlmPromptInput, maxTokens = 180): Promise<string> {
    if (!this.isInitialized) {
      await this.initialize();
    }
    const result = await this.sendWorkerRequest(
      "generate",
      { prompt: normalizePromptInput(prompt), maxTokens },
      LLM_CONFIG.requestTimeoutMs,
    );
    if (!result.text) {
      throw new Error("LLM worker returned an empty response");
    }
    return result.text;
  }

  async tryGenerateText(prompt: ClientLlmPromptInput, maxTokens = 180): Promise<ClientLlmTextGenerationResult> {
    try {
      const text = await this.generateText(prompt, maxTokens);
      return {
        ok: true,
        text,
        modelName: this.currentModel
      };
    } catch (error) {
      return {
        ok: false,
        text: "",
        modelName: this.currentModel,
        error: error instanceof Error ? error.message : "LLM worker text generation failed"
      };
    }
  }

  async generateStructuredText(prompt: ClientLlmPromptInput, maxTokens = 180): Promise<ClientLlmStructuredTextResult> {
    const result = await this.tryGenerateText(prompt, maxTokens);
    if (!result.ok) return result;

    const parsed = extractFirstJsonValue(result.text);
    if (!parsed.ok) {
      return {
        ...result,
        parseError: parsed.error
      };
    }

    return {
      ...result,
      json: parsed.value
    };
  }

  async getCapabilities(): Promise<LlmWorkerResponse> {
    try {
      return await this.sendWorkerRequest("getCapabilities", {}, 5000);
    } catch {
      return {
        modelName: this.currentModel,
        device: this.currentDevice,
        capabilities: this.capabilities,
        isInitialized: this.isInitialized,
      };
    }
  }

  getStatus() {
    return {
      isInitialized: this.isInitialized,
      isInitializing: this.isInitializing,
      hasWorker: this.worker !== null,
      currentModel: this.currentModel,
      currentDevice: this.currentDevice,
      capabilities: this.capabilities,
      openRouter: this.getOpenRouterStatus(),
    };
  }

  saveOpenRouterApiKey(apiKey: string) {
    if (typeof localStorage !== "undefined") {
      localStorage.setItem("abby.openrouter.apiKey", apiKey);
    }
    return this.getOpenRouterStatus();
  }

  clearOpenRouterApiKey() {
    if (typeof localStorage !== "undefined") {
      localStorage.removeItem("abby.openrouter.apiKey");
    }
    return this.getOpenRouterStatus();
  }

  destroy(): void {
    this.worker?.terminate();
    this.worker = null;
    this.isInitialized = false;
    this.isInitializing = false;
    this.pendingRequests.clear();
  }

  private initializeWorker(): void {
    if (typeof Worker === "undefined") {
      return;
    }
    try {
      this.worker = new Worker(new URL("../workers/clientLLMWorker.ts", import.meta.url), { type: "module" });
      this.worker.onmessage = this.handleWorkerMessage.bind(this);
      this.worker.onerror = this.handleWorkerError.bind(this);
    } catch (error) {
      console.error("Failed to create 211 LLM worker:", error);
      this.worker = null;
    }
  }

  private handleWorkerMessage(event: MessageEvent): void {
    const { id, success, data, error } = event.data as {
      id: string;
      success: boolean;
      data?: LlmWorkerResponse;
      error?: string;
    };
    const pending = this.pendingRequests.get(id);
    if (!pending) {
      return;
    }

    this.pendingRequests.delete(id);
      if (success) {
        if (data?.modelName) {
          this.currentModel = data.modelName;
          this.currentDevice = data.device || resolveModelDevice(data.modelName);
        }
        if (data?.capabilities) {
          this.capabilities = mergeCapabilities(this.capabilities, data.capabilities);
        }
      pending.resolve(data || {});
    } else {
      pending.reject(new Error(error || "LLM worker request failed"));
    }
  }

  private handleWorkerError(error: ErrorEvent): void {
    console.error("211 LLM worker error:", error);
    for (const [id, pending] of this.pendingRequests.entries()) {
      pending.reject(new Error("LLM worker error"));
      this.pendingRequests.delete(id);
    }
  }

  private sendWorkerRequest(type: string, data: unknown, timeoutMs: number): Promise<LlmWorkerResponse> {
    if (!this.worker) {
      throw new Error("LLM worker is not available");
    }
    const worker = this.worker;

    return new Promise((resolve, reject) => {
      const id = `llm_${++this.requestCounter}`;
      const timeout = window.setTimeout(() => {
        if (this.pendingRequests.has(id)) {
          this.pendingRequests.delete(id);
          reject(new Error("LLM worker request timed out"));
        }
      }, timeoutMs);

      this.pendingRequests.set(id, {
        resolve: (value) => {
          window.clearTimeout(timeout);
          resolve(value);
        },
        reject: (reason) => {
          window.clearTimeout(timeout);
          reject(reason);
        },
      });

      worker.postMessage({ id, type, data });
    });
  }

  private getOpenRouterStatus() {
    const browserKeyConfigured =
      typeof localStorage !== "undefined" && Boolean(localStorage.getItem("abby.openrouter.apiKey"));
    const proxyConfigured = Boolean(LLM_CONFIG.openRouterProxyUrl);
    return {
      enabled: LLM_CONFIG.openRouterEnabled || browserKeyConfigured || proxyConfigured,
      configured: browserKeyConfigured || proxyConfigured,
      credentialSource: browserKeyConfigured ? "browser" as const : proxyConfigured ? "proxy" as const : "none" as const,
      endpoint: LLM_CONFIG.openRouterProxyUrl || "https://openrouter.ai/api/v1/chat/completions",
      model: LLM_CONFIG.openRouterInstructModel,
      fallbackDelayMs: LLM_CONFIG.openRouterFallbackDelayMs,
    };
  }
}

function normalizePromptInput(input: ClientLlmPromptInput): string {
  if (typeof input === "string") {
    return input;
  }
  return [input.systemPrompt, input.userPrompt, input.prompt].filter(Boolean).join("\n\n");
}

function resolveModelDevice(modelName: string): ClientLlmDevice {
  return getClientLlmModelInfo(modelName)?.requiresWebGPU ? "webgpu" : "wasm";
}

function mergeCapabilities(
  current: ClientLlmRuntimeCapabilities,
  next: Partial<ClientLlmRuntimeCapabilities> | undefined,
): ClientLlmRuntimeCapabilities {
  return {
    ...current,
    ...(next || {}),
  };
}

function extractFirstJsonValue(text: string): { ok: true; value: unknown } | { ok: false; error: string } {
  const trimmed = stripJsonFence(text.trim());
  try {
    return { ok: true, value: JSON.parse(trimmed) };
  } catch {
    const balanced = firstBalancedJsonValue(trimmed);
    if (!balanced) {
      return { ok: false, error: "No JSON object or array found in LLM response" };
    }
    try {
      return { ok: true, value: JSON.parse(balanced) };
    } catch {
      return { ok: false, error: "LLM response JSON could not be parsed" };
    }
  }
}

function stripJsonFence(text: string): string {
  const fence = /^```(?:json)?\s*([\s\S]*?)\s*```$/i.exec(text);
  return fence?.[1] ?? text;
}

function firstBalancedJsonValue(text: string): string | undefined {
  const start = text.search(/[\[{]/);
  if (start < 0) return undefined;
  const stack: string[] = [];
  let inString = false;
  let escaping = false;

  for (let index = start; index < text.length; index += 1) {
    const char = text[index];
    if (inString) {
      if (escaping) {
        escaping = false;
      } else if (char === "\\") {
        escaping = true;
      } else if (char === "\"") {
        inString = false;
      }
      continue;
    }

    if (char === "\"") {
      inString = true;
    } else if (char === "{" || char === "[") {
      stack.push(char === "{" ? "}" : "]");
    } else if (char === "}" || char === "]") {
      if (stack.pop() !== char) return undefined;
      if (stack.length === 0) return text.slice(start, index + 1);
    }
  }

  return undefined;
}

export const clientLLMWorkerService = new ClientLLMWorkerService();
