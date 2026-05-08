import { LLM_CONFIG, getClientLlmModelInfo } from "./llmConfig";

const WORKER_RESTART_REQUIRED_PREFIX = "ABBY_LLM_WORKER_RESTART_REQUIRED:";

interface PendingRequest<T> {
  resolve: (value: T) => void;
  reject: (reason?: unknown) => void;
}

interface LlmWorkerResponse {
  text?: string;
  modelName?: string;
  capabilities?: {
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
  };
  device?: "wasm" | "webgpu" | "auto";
  isInitialized?: boolean;
}

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
  tryGenerateText: (prompt: string, maxTokens?: number) => Promise<ClientLlmTextGenerationResult>;
  generateStructuredText: (prompt: string, maxTokens?: number) => Promise<ClientLlmStructuredTextResult>;
}

class ClientLLMWorkerService {
  private worker: Worker | null = null;
  private isInitialized = false;
  private isInitializing = false;
  private requestCounter = 0;
  private pendingRequests = new Map<string, PendingRequest<LlmWorkerResponse>>();
  private currentModel = LLM_CONFIG.defaultModel;
  private currentDevice: "wasm" | "webgpu" | "auto" = "wasm";
  private webGPUFallbackReason: string | undefined;
  private capabilities: NonNullable<LlmWorkerResponse["capabilities"]> = {
    webGPU: false,
    webGPUShaderF16: false,
    simd: false,
    wasmThreads: false,
    crossOriginIsolated: Boolean((globalThis as { crossOriginIsolated?: boolean }).crossOriginIsolated),
    sharedArrayBuffer: typeof SharedArrayBuffer !== "undefined",
  };

  constructor() {
    this.initializeWorker();
  }

  async initialize(modelName = this.currentModel): Promise<void> {
    const targetModelName = this.resolveModelNameForSession(modelName);
    if (this.isInitialized && this.currentModel === targetModelName) {
      return;
    }
    if (this.isInitializing) {
      while (this.isInitializing) {
        await new Promise((resolve) => window.setTimeout(resolve, 100));
      }
      const nextTargetModelName = this.resolveModelNameForSession(modelName);
      if (this.isInitialized && this.currentModel === nextTargetModelName) {
        return;
      }
      return this.initialize(nextTargetModelName);
    }

    this.isInitializing = true;
    try {
      let result: LlmWorkerResponse;
      try {
        result = await this.sendWorkerRequest("initialize", { modelName: targetModelName }, LLM_CONFIG.modelDownloadTimeoutMs);
      } catch (error) {
        if (isWorkerRestartRequiredError(error)) {
          await this.restartWorkerWithFallback(formatWorkerRestartReason(error));
          return;
        }
        throw error;
      }
      this.isInitialized = Boolean(result.isInitialized ?? true);
      this.currentModel = result.modelName || targetModelName;
      this.currentDevice = result.device || this.currentDevice;
      if (this.currentDevice === "webgpu") {
        this.webGPUFallbackReason = undefined;
      }
      if (result.capabilities) {
        this.applyCapabilities(result.capabilities);
      }
    } finally {
      this.isInitializing = false;
    }
  }

  async switchModel(modelName: string): Promise<void> {
    const targetModelName = this.resolveModelNameForSession(modelName);
    if (this.isInitialized && this.currentModel === targetModelName) {
      return;
    }
    let result: LlmWorkerResponse;
    try {
      result = await this.sendWorkerRequest("switchModel", { modelName: targetModelName }, LLM_CONFIG.modelDownloadTimeoutMs);
    } catch (error) {
      if (isWorkerRestartRequiredError(error)) {
        await this.restartWorkerWithFallback(formatWorkerRestartReason(error));
        return;
      }
      throw error;
    }
    this.currentModel = result.modelName || targetModelName;
    this.currentDevice = result.device || this.currentDevice;
    if (this.currentDevice === "webgpu") {
      this.webGPUFallbackReason = undefined;
    }
    if (result.capabilities) {
      this.applyCapabilities(result.capabilities);
    }
    this.isInitialized = true;
  }

  async generateText(prompt: string, maxTokens = 180, didRestart = false): Promise<string> {
    if (!this.isInitialized) {
      await this.initialize();
    }
    let result: LlmWorkerResponse;
    try {
      result = await this.sendWorkerRequest("generate", { prompt, maxTokens }, LLM_CONFIG.requestTimeoutMs);
    } catch (error) {
      if (!didRestart && isWorkerRestartRequiredError(error)) {
        await this.restartWorkerWithFallback(formatWorkerRestartReason(error));
        return this.generateText(prompt, maxTokens, true);
      }
      throw error;
    }
    if (!result.text) {
      throw new Error("LLM worker returned an empty response");
    }
    return result.text;
  }

  async tryGenerateText(prompt: string, maxTokens = 180): Promise<ClientLlmTextGenerationResult> {
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

  async generateStructuredText(prompt: string, maxTokens = 180): Promise<ClientLlmStructuredTextResult> {
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
      const result = await this.sendWorkerRequest("getCapabilities", {}, 5000);
      return {
        ...result,
        capabilities: result.capabilities ? this.mergeCapabilities(result.capabilities) : this.capabilities,
      };
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
    };
  }

  destroy(reason = "LLM worker was stopped"): void {
    this.worker?.terminate();
    this.worker = null;
    this.isInitialized = false;
    this.isInitializing = false;
    for (const [id, pending] of this.pendingRequests.entries()) {
      pending.reject(new Error(reason));
      this.pendingRequests.delete(id);
    }
    this.pendingRequests.clear();
  }

  private async restartWorkerWithFallback(reason: string): Promise<void> {
    console.warn(`Restarting 211 LLM worker after WebGPU runtime failure. ${reason}`);
    this.webGPUFallbackReason = reason;
    this.destroy("LLM worker restarted after WebGPU runtime failure");
    this.currentModel = LLM_CONFIG.fallbackModel;
    this.currentDevice = "wasm";
    this.capabilities = {
      ...this.capabilities,
      webGPUError: reason,
    };
    this.initializeWorker();
    await this.initialize(LLM_CONFIG.fallbackModel);
    this.capabilities = {
      ...this.capabilities,
      webGPUError: reason,
    };
  }

  private resolveModelNameForSession(modelName: string): string {
    if (!this.webGPUFallbackReason) {
      return modelName;
    }
    const modelInfo = getClientLlmModelInfo(modelName);
    if (modelInfo?.requiresWebGPU || modelInfo?.preferWebGPU || (modelInfo?.device as string | undefined) === "webgpu") {
      return LLM_CONFIG.fallbackModel;
    }
    return modelName;
  }

  private applyCapabilities(capabilities: NonNullable<LlmWorkerResponse["capabilities"]>): void {
    this.capabilities = this.mergeCapabilities(capabilities);
  }

  private mergeCapabilities(capabilities: NonNullable<LlmWorkerResponse["capabilities"]>): NonNullable<LlmWorkerResponse["capabilities"]> {
    return {
      ...capabilities,
      webGPUError: capabilities.webGPUError || this.webGPUFallbackReason,
    };
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
      }
      if (data?.device) {
        this.currentDevice = data.device;
      }
      if (this.currentDevice === "webgpu") {
        this.webGPUFallbackReason = undefined;
      }
      if (data?.capabilities) {
        this.applyCapabilities(data.capabilities);
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
}

function isWorkerRestartRequiredError(error: unknown): boolean {
  return error instanceof Error && error.message.startsWith(WORKER_RESTART_REQUIRED_PREFIX);
}

function formatWorkerRestartReason(error: unknown): string {
  if (error instanceof Error) {
    return error.message.replace(WORKER_RESTART_REQUIRED_PREFIX, "").trim();
  }
  return "WebGPU runtime failed; using WASM fallback.";
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
