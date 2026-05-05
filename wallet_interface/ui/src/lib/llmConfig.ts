export const LLM_CONFIG = {
  inferenceMode: (import.meta.env?.VITE_LLM_INFERENCE_MODE as "client" | "server" | undefined) || "client",
  defaultModel: (import.meta.env?.VITE_CLIENT_LLM_MODEL as string | undefined) || "Xenova/distilgpt2",
  defaultEmbeddingModel:
    (import.meta.env?.VITE_DEFAULT_EMBEDDING_MODEL as string | undefined) || "Xenova/bge-small-en-v1.5",
  requestTimeoutMs: Number.parseInt(import.meta.env?.VITE_CLIENT_REQUEST_TIMEOUT || "45000", 10),
  modelDownloadTimeoutMs: Number.parseInt(import.meta.env?.VITE_MODEL_DOWNLOAD_TIMEOUT || "120000", 10),
  enableWebGPU: import.meta.env?.VITE_ENABLE_WEBGPU !== "false",
  enableSIMD: import.meta.env?.VITE_ENABLE_SIMD !== "false",
} as const;

export const SUPPORTED_CLIENT_LLM_MODELS = {
  "Xenova/distilgpt2": {
    name: "DistilGPT-2",
    size: "82MB",
    requiresWebGPU: false,
    contextLength: 1024,
    description: "Small WASM-compatible fallback model.",
    quantized: true,
  },
  "Xenova/LaMini-GPT-774M": {
    name: "LaMini-GPT 774M",
    size: "310MB",
    requiresWebGPU: false,
    contextLength: 1024,
    description: "Larger WASM-capable model for better short summaries.",
    quantized: true,
  },
  "onnx-community/Llama-3.2-1B-Instruct": {
    name: "Llama 3.2 1B Instruct",
    size: "637MB",
    requiresWebGPU: true,
    contextLength: 2048,
    description: "Instruction model for WebGPU-capable browsers.",
    quantized: false,
  },
  "onnx-community/Llama-3.2-3B-Instruct": {
    name: "Llama 3.2 3B Instruct",
    size: "1.9GB",
    requiresWebGPU: true,
    contextLength: 2048,
    description: "Higher-quality instruction model for machines with enough GPU memory.",
    quantized: false,
  },
} as const;

export type ClientLlmModel = keyof typeof SUPPORTED_CLIENT_LLM_MODELS;

export function getClientLlmModelInfo(modelName: string) {
  return SUPPORTED_CLIENT_LLM_MODELS[modelName as ClientLlmModel];
}

export function isSupportedClientLlmModel(modelName: string): modelName is ClientLlmModel {
  return modelName in SUPPORTED_CLIENT_LLM_MODELS;
}
