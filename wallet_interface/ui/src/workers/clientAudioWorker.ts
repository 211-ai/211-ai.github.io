import { LogLevel, env, pipeline } from "@huggingface/transformers";
import ortWasmAsyncifyMjsUrl from "../../node_modules/@huggingface/transformers/node_modules/onnxruntime-web/dist/ort-wasm-simd-threaded.asyncify.mjs?url";
import ortWasmAsyncifyWasmUrl from "../../node_modules/@huggingface/transformers/node_modules/onnxruntime-web/dist/ort-wasm-simd-threaded.asyncify.wasm?url";
import { AUDIO_CHAT_CONFIG, getClientAudioModelInfo } from "../lib/audioChatConfig";
import { getSafeOnnxWasmThreadCount, installWarningSuppression } from "../lib/warningSuppressionUtils";

env.allowLocalModels = false;
env.useBrowserCache = true;
env.useWasmCache = true;
env.logLevel = LogLevel.ERROR;
installWarningSuppression();

type AudioWorkerRequest = {
  id: string;
  type: "generateAudio";
  data: {
    text: string;
    modelName?: string;
  };
};

interface AudioWorkerResponse {
  id: string;
  success: boolean;
  data?: {
    audioBlob?: Blob;
    mimeType?: string;
    modelName?: string;
    provider?: "local-liquidai";
  };
  error?: string;
}

let audioGenerator: any = null;
let currentModelName = AUDIO_CHAT_CONFIG.defaultModel;
let initializePromise: Promise<void> | null = null;
let requestChain: Promise<void> = Promise.resolve();

self.onmessage = (event: MessageEvent<AudioWorkerRequest>) => {
  const request = event.data;
  requestChain = requestChain.then(
    () => handleWorkerRequest(request),
    () => handleWorkerRequest(request),
  );
};

async function handleWorkerRequest(request: AudioWorkerRequest): Promise<void> {
  try {
    if (request.type !== "generateAudio") {
      throw new Error(`Unknown audio worker request: ${request.type}`);
    }

    const modelName = request.data.modelName || AUDIO_CHAT_CONFIG.defaultModel;
    await initialize(modelName);
    const output = await audioGenerator(request.data.text);
    const audio = Array.isArray(output) ? output[0] : output;
    if (!audio || typeof audio.toBlob !== "function") {
      throw new Error("Audio model did not return a RawAudio result.");
    }

    const audioBlob = audio.toBlob();
    postResponse({
      id: request.id,
      success: true,
      data: {
        audioBlob,
        mimeType: audioBlob.type || "audio/wav",
        modelName: currentModelName,
        provider: "local-liquidai",
      },
    });
  } catch (error) {
    postResponse({
      id: request.id,
      success: false,
      error: error instanceof Error ? error.message : "Audio worker failed",
    });
  }
}

async function initialize(modelName: string): Promise<void> {
  if (audioGenerator && currentModelName === modelName) {
    return;
  }
  if (initializePromise) {
    await initializePromise;
    if (audioGenerator && currentModelName === modelName) {
      return;
    }
  }
  initializePromise = initializePipeline(modelName);
  try {
    await initializePromise;
  } finally {
    initializePromise = null;
  }
}

async function initializePipeline(modelName: string): Promise<void> {
  configureTransformersRuntime();
  const modelInfo = getClientAudioModelInfo(modelName);
  if (!modelInfo) {
    throw new Error(`Unsupported audio chat model: ${modelName}`);
  }
  if (!hasWebGPU()) {
    throw new Error(`${modelInfo.name} requires browser WebGPU for local audio generation.`);
  }

  try {
    audioGenerator = await pipeline("text-to-audio" as any, modelName, {
      device: "webgpu",
      dtype: modelInfo.dtype,
    } as any);
  } catch (error) {
    throw new Error(
      `${modelInfo.name} requires a dedicated ONNX audio runner; this Transformers.js build cannot load it through the generic text-to-audio pipeline. ${formatError(error)}`,
    );
  }
  currentModelName = modelName;
}

function configureTransformersRuntime(): void {
  const backends = env.backends as unknown as {
    onnx?: {
      setLogLevel?: (logLevel: number) => void;
      logLevel?: string;
      logVerbosityLevel?: number;
      wasm?: {
        numThreads?: number;
        wasmPaths?: {
          mjs: string;
          wasm: string;
        };
      };
      webgpu?: {
        powerPreference?: "low-power" | "high-performance";
        forceFallbackAdapter?: boolean;
        validateInputContent?: boolean;
      };
    };
  };
  const onnx = backends.onnx;
  onnx?.setLogLevel?.(LogLevel.ERROR);
  if (onnx) {
    onnx.logLevel = "error";
    onnx.logVerbosityLevel = 0;
  }
  if (onnx?.webgpu) {
    onnx.webgpu.powerPreference = "high-performance";
    onnx.webgpu.forceFallbackAdapter = false;
    onnx.webgpu.validateInputContent = false;
  }
  if (onnx?.wasm) {
    onnx.wasm.numThreads = getSafeOnnxWasmThreadCount(8);
    onnx.wasm.wasmPaths = {
      mjs: ortWasmAsyncifyMjsUrl,
      wasm: ortWasmAsyncifyWasmUrl,
    };
  }
}

function hasWebGPU(): boolean {
  return AUDIO_CHAT_CONFIG.enableWebGPU && typeof navigator !== "undefined" && Boolean((navigator as { gpu?: unknown }).gpu);
}

function postResponse(response: AudioWorkerResponse): void {
  self.postMessage(response);
}

function formatError(error: unknown): string {
  return error instanceof Error ? error.message : String(error || "Unknown audio worker error");
}
