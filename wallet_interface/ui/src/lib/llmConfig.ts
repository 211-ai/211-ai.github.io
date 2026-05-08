export const LLM_CONFIG = {
  inferenceMode: (import.meta.env?.VITE_LLM_INFERENCE_MODE as "client" | "server" | undefined) || "client",
  defaultModel: (import.meta.env?.VITE_CLIENT_LLM_MODEL as string | undefined) || "Xenova/LaMini-Flan-T5-77M",
  fallbackModel: "Xenova/distilgpt2",
  defaultEmbeddingModel:
    (import.meta.env?.VITE_DEFAULT_EMBEDDING_MODEL as string | undefined) || "Xenova/bge-small-en-v1.5",
  requestTimeoutMs: Number.parseInt(import.meta.env?.VITE_CLIENT_REQUEST_TIMEOUT || "45000", 10),
  modelDownloadTimeoutMs: Number.parseInt(import.meta.env?.VITE_MODEL_DOWNLOAD_TIMEOUT || "120000", 10),
  enableWebGPU: import.meta.env?.VITE_ENABLE_WEBGPU !== "false",
  enableSIMD: import.meta.env?.VITE_ENABLE_SIMD !== "false",
} as const;

export type ClientLlmPipelineTask = "text-generation" | "text2text-generation";

export const SUPPORTED_CLIENT_LLM_MODELS = {
  "Xenova/LaMini-Flan-T5-77M": {
    name: "LaMini-Flan-T5 77M",
    size: "small",
    task: "text2text-generation",
    requiresWebGPU: false,
    contextLength: 1024,
    description: "Instruction-tuned WASM model for browser chat and tool routing.",
    quantized: true,
  },
  "Xenova/LaMini-Flan-T5-248M": {
    name: "LaMini-Flan-T5 248M",
    size: "medium",
    task: "text2text-generation",
    requiresWebGPU: false,
    contextLength: 1024,
    description: "Higher-quality WASM model for grounded 211 answers.",
    quantized: true,
  },
  "Xenova/LaMini-Flan-T5-783M": {
    name: "LaMini-Flan-T5 783M",
    size: "large",
    task: "text2text-generation",
    requiresWebGPU: false,
    contextLength: 1024,
    description: "Largest WASM-compatible instruction model; slower initial load.",
    quantized: true,
  },
  "Xenova/distilgpt2": {
    name: "DistilGPT-2",
    size: "82MB",
    task: "text-generation",
    requiresWebGPU: false,
    contextLength: 1024,
    description: "Small WASM-compatible fallback model.",
    quantized: true,
  },
  "Xenova/LaMini-GPT-774M": {
    name: "LaMini-GPT 774M",
    size: "310MB",
    task: "text-generation",
    requiresWebGPU: false,
    contextLength: 1024,
    description: "Larger WASM-capable model for better short summaries.",
    quantized: true,
  },
} as const;

export type ClientLlmModel = keyof typeof SUPPORTED_CLIENT_LLM_MODELS;

export function getClientLlmModelInfo(modelName: string) {
  return SUPPORTED_CLIENT_LLM_MODELS[modelName as ClientLlmModel];
}

export function isSupportedClientLlmModel(modelName: string): modelName is ClientLlmModel {
  return modelName in SUPPORTED_CLIENT_LLM_MODELS;
}
