import { LLM_CONFIG } from "./llmConfig";

interface PendingRequest<T> {
  resolve: (value: T) => void;
  reject: (reason?: unknown) => void;
}

interface EmbeddingWorkerResponse {
  embedding?: number[];
  modelName?: string;
  isInitialized?: boolean;
}

class ClientEmbeddingWorkerService {
  private worker: Worker | null = null;
  private requestCounter = 0;
  private pendingRequests = new Map<string, PendingRequest<EmbeddingWorkerResponse>>();
  private currentModel = LLM_CONFIG.defaultEmbeddingModel;

  constructor() {
    this.initializeWorker();
  }

  async generateEmbedding(text: string, modelName = this.currentModel): Promise<Float32Array> {
    const response = await this.sendWorkerRequest("embed", { text, modelName });
    if (!Array.isArray(response.embedding)) {
      throw new Error("Embedding worker returned an invalid embedding");
    }
    return new Float32Array(response.embedding);
  }

  async getStatus(): Promise<{ modelName: string; isInitialized: boolean; hasWorker: boolean }> {
    if (!this.worker) {
      return { modelName: this.currentModel, isInitialized: false, hasWorker: false };
    }
    try {
      const response = await this.sendWorkerRequest("status", {}, 5000);
      return {
        modelName: response.modelName || this.currentModel,
        isInitialized: Boolean(response.isInitialized),
        hasWorker: true,
      };
    } catch {
      return { modelName: this.currentModel, isInitialized: false, hasWorker: true };
    }
  }

  destroy(): void {
    this.worker?.terminate();
    this.worker = null;
    this.pendingRequests.clear();
  }

  private initializeWorker(): void {
    if (typeof Worker === "undefined") {
      return;
    }
    try {
      this.worker = new Worker(new URL("../workers/embeddingWorker.ts", import.meta.url), { type: "module" });
      this.worker.onmessage = this.handleWorkerMessage.bind(this);
      this.worker.onerror = this.handleWorkerError.bind(this);
    } catch (error) {
      console.error("Failed to create 211 embedding worker:", error);
      this.worker = null;
    }
  }

  private handleWorkerMessage(event: MessageEvent): void {
    const { id, success, data, error } = event.data as {
      id: string;
      success: boolean;
      data?: EmbeddingWorkerResponse;
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
      pending.resolve(data || {});
    } else {
      pending.reject(new Error(error || "Embedding worker request failed"));
    }
  }

  private handleWorkerError(error: ErrorEvent): void {
    console.error("211 embedding worker error:", error);
    for (const [id, pending] of this.pendingRequests.entries()) {
      pending.reject(new Error("Embedding worker error"));
      this.pendingRequests.delete(id);
    }
  }

  private sendWorkerRequest(
    type: string,
    data: unknown,
    timeoutMs = LLM_CONFIG.modelDownloadTimeoutMs,
  ): Promise<EmbeddingWorkerResponse> {
    if (!this.worker) {
      throw new Error("Embedding worker is not available");
    }
    const worker = this.worker;

    return new Promise((resolve, reject) => {
      const id = `embedding_${++this.requestCounter}`;
      const timeout = window.setTimeout(() => {
        if (this.pendingRequests.has(id)) {
          this.pendingRequests.delete(id);
          reject(new Error("Embedding worker request timed out"));
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

export const clientEmbeddingWorkerService = new ClientEmbeddingWorkerService();
