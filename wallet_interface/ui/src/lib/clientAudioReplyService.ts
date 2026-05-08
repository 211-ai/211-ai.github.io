import { AUDIO_CHAT_CONFIG, getClientAudioModelInfo } from "./audioChatConfig";

type ClientAudioProvider = "local-liquidai" | "browser-speech";

interface PendingRequest<T> {
  resolve: (value: T) => void;
  reject: (reason?: unknown) => void;
  onProgress?: (progress: ClientAudioProgress) => void;
}

interface AudioWorkerResponse {
  audioBlob?: Blob;
  mimeType?: string;
  modelName?: string;
  provider?: ClientAudioProvider;
}

interface AudioWorkerMessage {
  id: string;
  type?: "progress";
  success?: boolean;
  data?: AudioWorkerResponse;
  error?: string;
  progress?: ClientAudioProgress;
}

export type ClientAudioProgressPhase =
  | "queued"
  | "loading-runtime"
  | "downloading-model"
  | "warming-up"
  | "ready"
  | "generating"
  | "decoding"
  | "fallback";

export interface ClientAudioProgress {
  phase: ClientAudioProgressPhase;
  progress: number;
  status: string;
  file?: string;
  modelName?: string;
}

export type ClientAudioReplyResult =
  | {
      kind: "audio";
      audioBlob: Blob;
      mimeType: string;
      modelName: string;
      provider: "local-liquidai";
    }
  | {
      kind: "browser-speech";
      text: string;
      modelName: string;
      provider: "browser-speech";
      fallbackForModel: string;
      fallbackReason: string;
    };

export type ClientAudioWarmupResult =
  | {
      kind: "local-ready";
      modelName: string;
      provider: "local-liquidai";
    }
  | {
      kind: "fallback";
      modelName: string;
      provider: "browser-speech";
      fallbackReason: string;
    };

interface ClientAudioProgressOptions {
  onProgress?: (progress: ClientAudioProgress) => void;
}

interface ClientAudioReplyServiceOptions {
  createWorker?: () => Worker;
  hasWebGPU?: () => boolean;
  hasSpeechSynthesis?: () => boolean;
}

export class ClientAudioReplyService {
  private worker: Worker | null = null;
  private requestCounter = 0;
  private pendingRequests = new Map<string, PendingRequest<AudioWorkerResponse>>();
  private localAudioUnavailableReason: string | undefined;
  private readonly createWorker: () => Worker;
  private readonly hasWebGPU: () => boolean;
  private readonly hasSpeechSynthesis: () => boolean;

  constructor(options: ClientAudioReplyServiceOptions = {}) {
    this.createWorker = options.createWorker ?? defaultCreateWorker;
    this.hasWebGPU = options.hasWebGPU ?? defaultHasWebGPU;
    this.hasSpeechSynthesis = options.hasSpeechSynthesis ?? defaultHasSpeechSynthesis;
  }

  async warmUp(options: ClientAudioProgressOptions = {}): Promise<ClientAudioWarmupResult> {
    const modelName = AUDIO_CHAT_CONFIG.defaultModel;
    if (this.canAttemptLocalAudio()) {
      try {
        options.onProgress?.({
          phase: "queued",
          progress: 0,
          status: "Preparing local audio model.",
          modelName,
        });
        await this.sendWorkerRequest(
          "warmUp",
          { modelName },
          AUDIO_CHAT_CONFIG.requestTimeoutMs,
          options.onProgress,
        );
        return {
          kind: "local-ready",
          modelName,
          provider: "local-liquidai",
        };
      } catch (error) {
        this.localAudioUnavailableReason = formatError(error);
        this.restartWorker();
      }
    }

    const fallbackReason = this.getLocalAudioFallbackReason(modelName);
    if (!this.hasSpeechSynthesis()) {
      throw new Error(fallbackReason);
    }
    options.onProgress?.({
      phase: "fallback",
      progress: 100,
      status: "Using browser speech output.",
      modelName,
    });
    return {
      kind: "fallback",
      modelName: AUDIO_CHAT_CONFIG.fallbackVoiceModel,
      provider: "browser-speech",
      fallbackReason,
    };
  }

  async generateAudio(text: string, options: ClientAudioProgressOptions = {}): Promise<ClientAudioReplyResult> {
    const normalizedText = text.trim().slice(0, AUDIO_CHAT_CONFIG.maxPromptCharacters);
    if (!normalizedText) {
      throw new Error("Audio reply text is empty.");
    }

    const modelName = AUDIO_CHAT_CONFIG.defaultModel;
    if (this.canAttemptLocalAudio()) {
      try {
        const result = await this.sendWorkerRequest(
          "generateAudio",
          { text: normalizedText, modelName },
          AUDIO_CHAT_CONFIG.requestTimeoutMs,
          options.onProgress,
        );
        if (result.audioBlob) {
          return {
            kind: "audio",
            audioBlob: result.audioBlob,
            mimeType: result.mimeType || result.audioBlob.type || "audio/wav",
            modelName: result.modelName || modelName,
            provider: "local-liquidai",
          };
        }
        throw new Error("Audio worker completed without an audio blob.");
      } catch (error) {
        this.localAudioUnavailableReason = formatError(error);
        this.restartWorker();
      }
    }

    if (this.hasSpeechSynthesis()) {
      return {
        kind: "browser-speech",
        text: normalizedText,
        modelName: AUDIO_CHAT_CONFIG.fallbackVoiceModel,
        provider: "browser-speech",
        fallbackForModel: modelName,
        fallbackReason: this.getLocalAudioFallbackReason(modelName),
      };
    }

    throw new Error(this.getLocalAudioFallbackReason(modelName));
  }

  getStatus() {
    return {
      defaultModel: AUDIO_CHAT_CONFIG.defaultModel,
      defaultModelInfo: getClientAudioModelInfo(AUDIO_CHAT_CONFIG.defaultModel),
      localAudioEnabled: AUDIO_CHAT_CONFIG.enableLocalAudio,
      localAudioAvailable: this.canAttemptLocalAudio(),
      localAudioUnavailableReason: this.localAudioUnavailableReason,
      fallbackVoiceAvailable: this.hasSpeechSynthesis(),
    };
  }

  private canAttemptLocalAudio(): boolean {
    return AUDIO_CHAT_CONFIG.enableLocalAudio && !this.localAudioUnavailableReason && this.hasWebGPU();
  }

  private getLocalAudioFallbackReason(modelName: string): string {
    if (!AUDIO_CHAT_CONFIG.enableLocalAudio) {
      return "Local audio generation is disabled by configuration.";
    }
    if (!this.hasWebGPU()) {
      return `${modelName} requires local WebGPU; using browser speech output instead.`;
    }
    return (
      this.localAudioUnavailableReason ||
      `${modelName} could not be started in the browser audio worker; using browser speech output instead.`
    );
  }

  private sendWorkerRequest(
    type: "generateAudio" | "warmUp",
    data: { text?: string; modelName: string },
    timeoutMs: number,
    onProgress?: (progress: ClientAudioProgress) => void,
  ): Promise<AudioWorkerResponse> {
    this.ensureWorker();
    const requestId = `audio-${++this.requestCounter}`;
    return new Promise((resolve, reject) => {
      const timeout = globalThis.setTimeout(() => {
        this.pendingRequests.delete(requestId);
        reject(new Error("Audio generation timed out."));
      }, timeoutMs);
      this.pendingRequests.set(requestId, {
        onProgress,
        resolve: (value) => {
          globalThis.clearTimeout(timeout);
          resolve(value);
        },
        reject: (reason) => {
          globalThis.clearTimeout(timeout);
          reject(reason);
        },
      });
      this.worker?.postMessage({ id: requestId, type, data });
    });
  }

  private ensureWorker(): void {
    if (this.worker) return;
    this.worker = this.createWorker();
    this.worker.onmessage = (event: MessageEvent<AudioWorkerMessage>) => {
      const pending = this.pendingRequests.get(event.data.id);
      if (!pending) return;
      if (event.data.type === "progress") {
        if (event.data.progress) pending.onProgress?.(event.data.progress);
        return;
      }
      if (typeof event.data.success !== "boolean") return;
      this.pendingRequests.delete(event.data.id);
      if (event.data.success) {
        pending.resolve(event.data.data || {});
      } else {
        pending.reject(new Error(event.data.error || "Audio worker failed."));
      }
    };
    this.worker.onerror = (event) => {
      const error = new Error(event.message || "Audio worker failed.");
      this.pendingRequests.forEach((pending) => pending.reject(error));
      this.pendingRequests.clear();
      this.localAudioUnavailableReason = error.message;
      this.restartWorker();
    };
  }

  private restartWorker(): void {
    if (this.worker) {
      this.worker.terminate();
      this.worker = null;
    }
    this.pendingRequests.forEach((pending) => pending.reject(new Error("Audio worker restarted.")));
    this.pendingRequests.clear();
  }
}

function defaultCreateWorker(): Worker {
  return new Worker(new URL("../workers/clientAudioWorker.ts", import.meta.url), { type: "module" });
}

function defaultHasWebGPU(): boolean {
  return AUDIO_CHAT_CONFIG.enableWebGPU && typeof navigator !== "undefined" && Boolean((navigator as { gpu?: unknown }).gpu);
}

function defaultHasSpeechSynthesis(): boolean {
  return typeof window !== "undefined" && "speechSynthesis" in window && typeof SpeechSynthesisUtterance !== "undefined";
}

function formatError(error: unknown): string {
  return error instanceof Error ? error.message : String(error || "Unknown audio error");
}

export const clientAudioReplyService = new ClientAudioReplyService();
