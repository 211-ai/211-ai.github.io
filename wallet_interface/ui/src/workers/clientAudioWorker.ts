import ortWebGpuModuleUrl from "../../node_modules/onnxruntime-web/dist/ort.webgpu.bundle.min.mjs?url";
import ortWasmAsyncifyWasmUrl from "../../node_modules/onnxruntime-web/dist/ort-wasm-simd-threaded.asyncify.wasm?url";
import transformersWebModuleUrl from "../../node_modules/@huggingface/transformers/dist/transformers.web.js?url";
import { AUDIO_CHAT_CONFIG, getClientAudioModelInfo } from "../lib/audioChatConfig";
import { getSafeOnnxWasmThreadCount, installWarningSuppression } from "../lib/warningSuppressionUtils";

installWarningSuppression();

type AudioWorkerRequest = {
  id: string;
  type: "generateAudio" | "warmUp";
  data: {
    text?: string;
    modelName?: string;
  };
};

type AudioProgressPhase =
  | "queued"
  | "loading-runtime"
  | "downloading-model"
  | "warming-up"
  | "ready"
  | "generating"
  | "decoding";

interface AudioWorkerProgress {
  phase: AudioProgressPhase;
  progress: number;
  status: string;
  file?: string;
  modelName?: string;
}

interface AudioWorkerResponse {
  id: string;
  type?: "progress";
  success: boolean;
  data?: {
    audioBlob?: Blob;
    mimeType?: string;
    modelName?: string;
    provider?: "local-liquidai";
  };
  error?: string;
}

let audioModel: LiquidAudioModel | null = null;
let currentModelName = AUDIO_CHAT_CONFIG.defaultModel;
let initializePromise: Promise<void> | null = null;
let requestChain: Promise<void> = Promise.resolve();
let liquidAudioRuntimePromise: Promise<LiquidAudioRuntime> | null = null;

interface LiquidAudioRuntime {
  AudioModel: new () => LiquidAudioModel;
  revoke: () => void;
}

interface LiquidAudioModel {
  load: (
    modelPath: string,
    options: {
      device: "webgpu";
      quantization: {
        decoder: "q4";
        audioEncoder: "q4";
        audioEmbedding: "q4";
        audioDetokenizer: "q4";
        vocoder: "q4";
      };
      loadAudioEncoder?: boolean;
      progressCallback?: (progress: { status: string; progress: number; file?: string }) => void;
    },
  ) => Promise<boolean>;
  generateSpeech: (
    text: string,
    options: {
      maxNewTokens: number;
      systemPrompt: string;
      textTemperature: number;
      audioTemperature: number;
      audioTopK: number;
    },
  ) => Promise<{ audioCodes: number[][]; textOutput?: string }>;
  decodeAudioCodes: (audioCodes: number[][]) => Promise<Float32Array>;
  reset?: () => void;
}

self.onmessage = (event: MessageEvent<AudioWorkerRequest>) => {
  const request = event.data;
  requestChain = requestChain.then(
    () => handleWorkerRequest(request),
    () => handleWorkerRequest(request),
  );
};

async function handleWorkerRequest(request: AudioWorkerRequest): Promise<void> {
  try {
    if (request.type !== "generateAudio" && request.type !== "warmUp") {
      throw new Error(`Unknown audio worker request: ${request.type}`);
    }

    const modelName = request.data.modelName || AUDIO_CHAT_CONFIG.defaultModel;
    postProgress(request.id, {
      phase: "queued",
      progress: 0,
      status: "Preparing LiquidAI audio model.",
      modelName,
    });
    const model = await initialize(modelName, (progress) => postProgress(request.id, progress));
    if (request.type === "warmUp") {
      postResponse({
        id: request.id,
        success: true,
        data: {
          modelName: currentModelName,
          provider: "local-liquidai",
        },
      });
      return;
    }

    const text = request.data.text?.trim();
    if (!text) {
      throw new Error("Audio generation text is empty.");
    }
    postProgress(request.id, {
      phase: "generating",
      progress: 90,
      status: "Generating speech audio.",
      modelName,
    });
    const generation = await model.generateSpeech(text, {
      maxNewTokens: AUDIO_CHAT_CONFIG.maxAudioFrames,
      systemPrompt: "Perform TTS. Use the UK female voice.",
      textTemperature: 0.7,
      audioTemperature: 0.8,
      audioTopK: 64,
    });
    if (!generation.audioCodes.length) {
      throw new Error("LiquidAI audio model completed without audio frames.");
    }
    postProgress(request.id, {
      phase: "decoding",
      progress: 97,
      status: "Decoding generated audio.",
      modelName,
    });
    const waveform = await model.decodeAudioCodes(generation.audioCodes);
    const audioBlob = createWavBlob(waveform, 24000);
    postProgress(request.id, {
      phase: "ready",
      progress: 100,
      status: "Audio reply ready.",
      modelName,
    });
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

async function initialize(modelName: string, onProgress: (progress: AudioWorkerProgress) => void): Promise<LiquidAudioModel> {
  if (audioModel && currentModelName === modelName) {
    onProgress({
      phase: "ready",
      progress: 100,
      status: "Audio model ready.",
      modelName,
    });
    return audioModel;
  }
  if (initializePromise) {
    onProgress({
      phase: "warming-up",
      progress: 5,
      status: "Waiting for the audio model to finish warming up.",
      modelName,
    });
    await initializePromise;
    if (audioModel && currentModelName === modelName) {
      onProgress({
        phase: "ready",
        progress: 100,
        status: "Audio model ready.",
        modelName,
      });
      return audioModel;
    }
  }
  initializePromise = initializePipeline(modelName, onProgress);
  try {
    await initializePromise;
  } finally {
    initializePromise = null;
  }
  if (!audioModel) {
    throw new Error("LiquidAI audio model did not initialize.");
  }
  return audioModel;
}

async function initializePipeline(modelName: string, onProgress: (progress: AudioWorkerProgress) => void): Promise<void> {
  const modelInfo = getClientAudioModelInfo(modelName);
  if (!modelInfo) {
    throw new Error(`Unsupported audio chat model: ${modelName}`);
  }
  if (!hasWebGPU()) {
    throw new Error(`${modelInfo.name} requires browser WebGPU for local audio generation.`);
  }

  onProgress({
    phase: "loading-runtime",
    progress: 3,
    status: "Loading LiquidAI audio runtime.",
    modelName,
  });
  const runtime = await loadLiquidAudioRuntime();
  onProgress({
    phase: "warming-up",
    progress: 12,
    status: "Starting local audio model.",
    modelName,
  });
  const model = new runtime.AudioModel();
  await model.load(`https://huggingface.co/${modelName}/resolve/main`, {
    device: "webgpu",
    quantization: {
      decoder: "q4",
      audioEncoder: "q4",
      audioEmbedding: "q4",
      audioDetokenizer: "q4",
      vocoder: "q4",
    },
    loadAudioEncoder: false,
    progressCallback: (progress) => {
      console.info("[AudioWorker] LiquidAI audio load", progress);
      onProgress(formatLiquidAudioLoadProgress(progress, modelName));
    },
  });
  onProgress({
    phase: "ready",
    progress: 100,
    status: "Audio model ready.",
    modelName,
  });
  audioModel = model;
  currentModelName = modelName;
}

async function loadLiquidAudioRuntime(): Promise<LiquidAudioRuntime> {
  if (liquidAudioRuntimePromise) {
    return liquidAudioRuntimePromise;
  }
  liquidAudioRuntimePromise = createLiquidAudioRuntime();
  return liquidAudioRuntimePromise;
}

async function createLiquidAudioRuntime(): Promise<LiquidAudioRuntime> {
  const [audioModelSource, audioProcessorSource] = await Promise.all([
    fetchRunnerSource("audio-model.js"),
    fetchRunnerSource("audio-processor.js"),
  ]);
  const ortWrapperUrl = URL.createObjectURL(
    new Blob(
      [
        `import * as actual from ${JSON.stringify(ortWebGpuModuleUrl)};
actual.env.logLevel = "error";
actual.env.wasm.numThreads = ${JSON.stringify(getSafeOnnxWasmThreadCount(8))};
actual.env.wasm.wasmPaths = { wasm: ${JSON.stringify(ortWasmAsyncifyWasmUrl)} };
actual.env.webgpu.powerPreference = "high-performance";
actual.env.webgpu.forceFallbackAdapter = false;
export * from ${JSON.stringify(ortWebGpuModuleUrl)};
export default actual.default ?? actual;
`,
      ],
      { type: "text/javascript" },
    ),
  );
  const audioProcessorUrl = URL.createObjectURL(
    new Blob([audioProcessorSource], { type: "text/javascript" }),
  );
  const patchedAudioModelSource = patchAudioModelSource(audioModelSource, {
    audioProcessorUrl,
    ortWrapperUrl,
    transformersWebModuleUrl,
  });
  const audioModelUrl = URL.createObjectURL(
    new Blob([patchedAudioModelSource], { type: "text/javascript" }),
  );
  try {
    const module = (await import(/* @vite-ignore */ audioModelUrl)) as { AudioModel?: new () => LiquidAudioModel };
    if (!module.AudioModel) {
      throw new Error("LiquidAI audio runner did not export AudioModel.");
    }
    return {
      AudioModel: module.AudioModel,
      revoke: () => {
        URL.revokeObjectURL(audioModelUrl);
        URL.revokeObjectURL(audioProcessorUrl);
        URL.revokeObjectURL(ortWrapperUrl);
      },
    };
  } catch (error) {
    URL.revokeObjectURL(audioModelUrl);
    URL.revokeObjectURL(audioProcessorUrl);
    URL.revokeObjectURL(ortWrapperUrl);
    throw error;
  }
}

async function fetchRunnerSource(fileName: "audio-model.js" | "audio-processor.js"): Promise<string> {
  const response = await fetch(`${AUDIO_CHAT_CONFIG.liquidAudioRunnerBaseUrl}/${fileName}`, {
    mode: "cors",
    credentials: "omit",
  });
  if (!response.ok) {
    throw new Error(`Failed to fetch LiquidAI audio runner ${fileName}: ${response.status}`);
  }
  return response.text();
}

function patchAudioModelSource(
  source: string,
  urls: {
    audioProcessorUrl: string;
    ortWrapperUrl: string;
    transformersWebModuleUrl: string;
  },
): string {
  let patched = source
    .replace("import * as ort from 'onnxruntime-web';", `import * as ort from ${JSON.stringify(urls.ortWrapperUrl)};`)
    .replace(
      "import { AutoTokenizer, env } from '@huggingface/transformers';",
      `import { AutoTokenizer, env } from ${JSON.stringify(urls.transformersWebModuleUrl)};`,
    )
    .replace(
      "import { loadMelConfig, computeMelSpectrogram, loadAudioFile } from './audio-processor.js';",
      `import { loadMelConfig, computeMelSpectrogram, loadAudioFile } from ${JSON.stringify(urls.audioProcessorUrl)};`,
    )
    .replace(
      "const { progressCallback, device = 'webgpu', quantization = null } = options;",
      "const { progressCallback, device = 'webgpu', quantization = null, loadAudioEncoder = true } = options;",
    )
    .replace(
      "this.audioEncoderSession = await loadOnnxWithExternalData('audio_encoder', 50, quantConfig.audioEncoder);",
      "if (loadAudioEncoder) { this.audioEncoderSession = await loadOnnxWithExternalData('audio_encoder', 50, quantConfig.audioEncoder); }",
    );

  if (patched === source) {
    throw new Error("LiquidAI audio runner import patch failed.");
  }

  return `// Runtime-patched from LiquidAI/LFM2.5-Audio-1.5B-transformers-js.
${patched}`;
}

function createWavBlob(samples: Float32Array, sampleRate: number): Blob {
  const numChannels = 1;
  const bytesPerSample = 2;
  const blockAlign = numChannels * bytesPerSample;
  const byteRate = sampleRate * blockAlign;
  const dataSize = samples.length * bytesPerSample;
  const bufferSize = 44 + dataSize;
  const buffer = new ArrayBuffer(bufferSize);
  const view = new DataView(buffer);

  writeString(view, 0, "RIFF");
  view.setUint32(4, bufferSize - 8, true);
  writeString(view, 8, "WAVE");
  writeString(view, 12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, numChannels, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, byteRate, true);
  view.setUint16(32, blockAlign, true);
  view.setUint16(34, bytesPerSample * 8, true);
  writeString(view, 36, "data");
  view.setUint32(40, dataSize, true);

  let offset = 44;
  for (let index = 0; index < samples.length; index += 1) {
    const sample = Math.max(-1, Math.min(1, samples[index]));
    view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true);
    offset += bytesPerSample;
  }

  return new Blob([buffer], { type: "audio/wav" });
}

function writeString(view: DataView, offset: number, value: string): void {
  for (let index = 0; index < value.length; index += 1) {
    view.setUint8(offset + index, value.charCodeAt(index));
  }
}

function hasWebGPU(): boolean {
  return AUDIO_CHAT_CONFIG.enableWebGPU && typeof navigator !== "undefined" && Boolean((navigator as { gpu?: unknown }).gpu);
}

function postProgress(id: string, progress: AudioWorkerProgress): void {
  self.postMessage({
    id,
    type: "progress",
    progress: {
      ...progress,
      progress: clampProgress(progress.progress),
    },
    success: false,
  });
}

function postResponse(response: AudioWorkerResponse): void {
  self.postMessage(response);
}

function formatLiquidAudioLoadProgress(
  progress: { status: string; progress: number; file?: string },
  modelName: string,
): AudioWorkerProgress {
  const rawProgress = Number.isFinite(progress.progress) ? progress.progress : 0;
  const normalizedProgress = rawProgress <= 1 ? rawProgress * 100 : rawProgress;
  const scaledProgress = 15 + normalizedProgress * 0.7;
  const fileDetail = progress.file ? ` ${progress.file}` : "";
  return {
    phase: "downloading-model",
    progress: scaledProgress,
    status: `Downloading audio model${fileDetail}.`,
    file: progress.file,
    modelName,
  };
}

function clampProgress(value: number): number {
  if (!Number.isFinite(value)) return 0;
  return Math.max(0, Math.min(100, Math.round(value)));
}

function formatError(error: unknown): string {
  return error instanceof Error ? error.message : String(error || "Unknown audio worker error");
}
