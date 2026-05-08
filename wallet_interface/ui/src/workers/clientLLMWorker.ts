import { env, pipeline } from "@huggingface/transformers";
import ortWasmJsepMjsUrl from "../../node_modules/@huggingface/transformers/node_modules/onnxruntime-web/dist/ort-wasm-simd-threaded.jsep.mjs?url";
import ortWasmJsepWasmUrl from "../../node_modules/@huggingface/transformers/node_modules/onnxruntime-web/dist/ort-wasm-simd-threaded.jsep.wasm?url";
import { LLM_CONFIG, SUPPORTED_CLIENT_LLM_MODELS, getClientLlmModelInfo } from "../lib/llmConfig";
import { getSafeOnnxWasmThreadCount, installWarningSuppression } from "../lib/warningSuppressionUtils";

env.allowLocalModels = false;
env.useBrowserCache = true;
env.useWasmCache = true;
installWarningSuppression();

type LlmWorkerRequest =
  | {
      id: string;
      type: "initialize" | "switchModel";
      data: { modelName?: string };
    }
  | {
      id: string;
      type: "generate";
      data: { prompt: string; maxTokens?: number };
    }
  | {
      id: string;
      type: "getCapabilities";
      data?: Record<string, never>;
    };

interface LlmWorkerResponse {
  id: string;
  success: boolean;
  data?: {
    text?: string;
    modelName?: string;
    capabilities?: {
      webGPU: boolean;
      simd: boolean;
    };
    isInitialized?: boolean;
  };
  error?: string;
}

let textGenerator: any = null;
let currentModelName = LLM_CONFIG.defaultModel;
let isInitialized = false;
let initializePromise: Promise<void> | null = null;
let initializingModelName: string | null = null;
let capabilities = { webGPU: false, simd: false };

self.onmessage = async (event: MessageEvent<LlmWorkerRequest>) => {
  const { id, type, data } = event.data;

  try {
    if (type === "getCapabilities") {
      capabilities = await detectCapabilities();
      postResponse({
        id,
        success: true,
        data: { capabilities, modelName: currentModelName, isInitialized },
      });
      return;
    }

    if (type === "initialize" || type === "switchModel") {
      const modelName = data.modelName || LLM_CONFIG.defaultModel;
      await initialize(modelName);
      postResponse({
        id,
        success: true,
        data: { capabilities, modelName: currentModelName, isInitialized },
      });
      return;
    }

    if (type === "generate") {
      await initialize(currentModelName);
      const text = await generateText(data.prompt, data.maxTokens || 180);
      postResponse({
        id,
        success: true,
        data: { text, capabilities, modelName: currentModelName, isInitialized },
      });
      return;
    }

    throw new Error(`Unknown LLM worker request: ${type}`);
  } catch (error) {
    postResponse({
      id,
      success: false,
      error: error instanceof Error ? error.message : "LLM worker failed",
    });
  }
};

async function initialize(modelName: string): Promise<void> {
  if (textGenerator && isInitialized && currentModelName === modelName) {
    return;
  }
  if (initializePromise) {
    await initializePromise;
    if (textGenerator && isInitialized && currentModelName === modelName) {
      return;
    }
    if (initializingModelName !== modelName) {
      return initialize(modelName);
    }
    return;
  }

  initializingModelName = modelName;
  initializePromise = initializePipeline(modelName);
  try {
    await initializePromise;
  } finally {
    initializePromise = null;
    initializingModelName = null;
  }
}

async function initializePipeline(modelName: string): Promise<void> {
  capabilities = await detectCapabilities();
  configureTransformersRuntime();

  const requestedModelName = getClientLlmModelInfo(modelName) ? modelName : LLM_CONFIG.fallbackModel;
  try {
    await loadPipeline(requestedModelName);
  } catch (error) {
    if (requestedModelName === LLM_CONFIG.fallbackModel) {
      throw error;
    }
    console.warn(`211 LLM model ${requestedModelName} unavailable; falling back to ${LLM_CONFIG.fallbackModel}.`, error);
    await loadPipeline(LLM_CONFIG.fallbackModel);
  }
}

async function loadPipeline(requestedModelName: string): Promise<void> {
  const modelInfo = getClientLlmModelInfo(requestedModelName) || SUPPORTED_CLIENT_LLM_MODELS[LLM_CONFIG.fallbackModel];
  if (modelInfo.requiresWebGPU && !capabilities.webGPU) {
    throw new Error(`${modelInfo.name} requires WebGPU. Use a WASM-compatible model on this browser.`);
  }

  const device = selectModelDevice(modelInfo);
  const options: Record<string, unknown> = {
    dtype: modelInfo.dtype,
    device,
  };

  try {
    textGenerator = await pipeline(modelInfo.task, requestedModelName, options);
  } catch (error) {
    if (options.device === "webgpu" || options.device === "auto") {
      textGenerator = await pipeline(modelInfo.task, requestedModelName, {
        dtype: modelInfo.dtype,
        device: "wasm",
      } as any);
    } else {
      throw error;
    }
  }

  currentModelName = requestedModelName;
  isInitialized = true;
}

async function generateText(prompt: string, maxTokens: number): Promise<string> {
  if (!textGenerator || !isInitialized) {
    throw new Error("LLM is not initialized");
  }

  const modelInfo = getClientLlmModelInfo(currentModelName) || SUPPORTED_CLIENT_LLM_MODELS[LLM_CONFIG.fallbackModel];
  const input = modelInfo.inputMode === "chat" ? buildChatGenerationMessages(prompt) : prompt;
  const output = await textGenerator(input, {
    max_new_tokens: maxTokens,
    do_sample: false,
    return_full_text: false,
  });
  return extractGeneratedText(output);
}

function selectModelDevice(modelInfo: ReturnType<typeof getClientLlmModelInfo>): "wasm" | "webgpu" | "auto" {
  if (!modelInfo) return "wasm";
  const configuredDevice = modelInfo.device as "wasm" | "webgpu" | "auto";
  if (modelInfo.requiresWebGPU) return "webgpu";
  if (configuredDevice === "auto" && modelInfo.preferWebGPU && capabilities.webGPU && LLM_CONFIG.enableWebGPU) {
    return "auto";
  }
  if (configuredDevice === "webgpu" && capabilities.webGPU && LLM_CONFIG.enableWebGPU) {
    return "webgpu";
  }
  return "wasm";
}

function buildChatGenerationMessages(prompt: string): Array<{ role: "system" | "user"; content: string }> {
  const assistantPrompt = parseAbbyAssistantResponsePrompt(prompt);
  if (assistantPrompt) {
    return [
      {
        role: "system",
        content: [
          "You are Abby, a concise assistant inside a 211 service navigation and wallet app.",
          "If the user asks what you can do, mention screen help, app navigation, public 211 service search, evidence summaries, and confirmation before wallet changes.",
          "Use the safe app context and conversation history. Do not invent service facts or completed app actions.",
          "Return only the assistant message text.",
          "",
          assistantPrompt.systemContext,
        ].join("\n"),
      },
      {
        role: "user",
        content: assistantPrompt.userMessage,
      },
    ];
  }

  const jsonMode = /\bReturn only one JSON object\b/i.test(prompt);
  return [
    {
      role: "system",
      content: jsonMode
        ? "You are Abby's app tool router. Follow the prompt exactly and return only the requested JSON object."
        : "You are Abby, a concise assistant inside a 211 service navigation and wallet app. Follow the user's prompt exactly and return only the assistant message text.",
    },
    {
      role: "user",
      content: prompt,
    },
  ];
}

function parseAbbyAssistantResponsePrompt(prompt: string): { systemContext: string; userMessage: string } | undefined {
  if (!/^Answer as Abby\b/i.test(prompt.trim())) {
    return undefined;
  }

  const marker = "\nUser message:\n";
  const markerIndex = prompt.lastIndexOf(marker);
  if (markerIndex < 0) {
    return undefined;
  }

  const systemContext = prompt.slice(0, markerIndex).trim();
  const userMessage = prompt
    .slice(markerIndex + marker.length)
    .replace(/\n\s*Abby\s*:\s*$/i, "")
    .trim();
  if (!systemContext || !userMessage) {
    return undefined;
  }

  return { systemContext, userMessage };
}

function extractGeneratedText(output: unknown): string {
  const first = Array.isArray(output) ? output[0] : output;
  if (first && typeof first === "object" && "generated_text" in first) {
    const generatedText = (first as { generated_text?: unknown }).generated_text;
    if (Array.isArray(generatedText)) {
      const lastMessage = [...generatedText]
        .reverse()
        .find((message) => message && typeof message === "object" && (message as { role?: unknown }).role === "assistant");
      const content = lastMessage && typeof (lastMessage as { content?: unknown }).content === "string"
        ? (lastMessage as { content: string }).content
        : undefined;
      if (content) return content.trim();
    }
    if (typeof generatedText === "string") {
      return generatedText.trim();
    }
  }
  if (typeof first === "string") return first.trim();
  return String(output || "").trim();
}

async function detectCapabilities(): Promise<{ webGPU: boolean; simd: boolean }> {
  return {
    webGPU: await detectWebGPU(),
    simd: detectWasmSimd(),
  };
}

async function detectWebGPU(): Promise<boolean> {
  try {
    const gpu = (navigator as Navigator & { gpu?: { requestAdapter: (options?: unknown) => Promise<any> } }).gpu;
    if (!gpu?.requestAdapter) {
      return false;
    }
    const adapter = await gpu.requestAdapter({ powerPreference: "high-performance" });
    if (!adapter) {
      return false;
    }
    const device = await adapter.requestDevice();
    device.destroy();
    return true;
  } catch {
    return false;
  }
}

function detectWasmSimd(): boolean {
  try {
    const simdModule = new Uint8Array([
      0x00, 0x61, 0x73, 0x6d, 0x01, 0x00, 0x00, 0x00, 0x01, 0x05, 0x01, 0x60, 0x00, 0x01, 0x7b,
    ]);
    return WebAssembly.validate(simdModule);
  } catch {
    return false;
  }
}

function configureTransformersRuntime(): void {
  const backends = env.backends as unknown as {
    onnx?: {
      wasm?: {
        numThreads?: number;
        simd?: boolean;
        wasmPaths?: {
          mjs: string;
          wasm: string;
        };
        wasmBinary?: ArrayBuffer;
      };
    };
  };
  if (backends.onnx?.wasm) {
    backends.onnx.wasm.numThreads = getSafeOnnxWasmThreadCount(8);
    backends.onnx.wasm.simd = capabilities.simd && LLM_CONFIG.enableSIMD;
    backends.onnx.wasm.wasmPaths = {
      mjs: ortWasmJsepMjsUrl,
      wasm: ortWasmJsepWasmUrl,
    };
  }
}

function postResponse(response: LlmWorkerResponse): void {
  self.postMessage(response);
}
