import { LLM_CONFIG } from "./llmConfig";

interface PendingRequest<T> {
  resolve: (value: T) => void;
  reject: (reason?: unknown) => void;
}

interface LlmWorkerResponse {
  text?: string;
  modelName?: string;
  capabilities?: {
    webGPU: boolean;
    simd: boolean;
  };
  isInitialized?: boolean;
}

class ClientLLMWorkerService {
  private worker: Worker | null = null;
  private isInitialized = false;
  private isInitializing = false;
  private requestCounter = 0;
  private pendingRequests = new Map<string, PendingRequest<LlmWorkerResponse>>();
  private currentModel = LLM_CONFIG.defaultModel;
  private capabilities = { webGPU: false, simd: false };

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
      this.capabilities = result.capabilities || this.capabilities;
    } finally {
      this.isInitializing = false;
    }
  }

  async switchModel(modelName: string): Promise<void> {
    const result = await this.sendWorkerRequest("switchModel", { modelName }, LLM_CONFIG.modelDownloadTimeoutMs);
    this.currentModel = result.modelName || modelName;
    this.capabilities = result.capabilities || this.capabilities;
    this.isInitialized = true;
  }

  async generateText(prompt: string, maxTokens = 180): Promise<string> {
    if (!this.isInitialized) {
      await this.initialize();
    }
    const result = await this.sendWorkerRequest("generate", { prompt, maxTokens }, LLM_CONFIG.requestTimeoutMs);
    if (!result.text) {
      throw new Error("LLM worker returned an empty response");
    }
    return result.text;
  }

  async getCapabilities(): Promise<LlmWorkerResponse> {
    try {
      return await this.sendWorkerRequest("getCapabilities", {}, 5000);
    } catch {
      return {
        modelName: this.currentModel,
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
      capabilities: this.capabilities,
    };
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
      }
      if (data?.capabilities) {
        this.capabilities = data.capabilities;
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

export const clientLLMWorkerService = new ClientLLMWorkerService();
