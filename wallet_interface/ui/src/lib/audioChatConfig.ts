export const AUDIO_CHAT_CONFIG = {
  defaultModel:
    (import.meta.env?.VITE_CLIENT_AUDIO_MODEL as string | undefined) || "LiquidAI/LFM2.5-Audio-1.5B-ONNX",
  fallbackVoiceModel: "browser-speech-synthesis",
  enableLocalAudio: import.meta.env?.VITE_ENABLE_LOCAL_AUDIO !== "false",
  enableWebGPU: import.meta.env?.VITE_ENABLE_WEBGPU !== "false",
  requestTimeoutMs: Number.parseInt(import.meta.env?.VITE_CLIENT_AUDIO_REQUEST_TIMEOUT || "90000", 10),
  maxPromptCharacters: Number.parseInt(import.meta.env?.VITE_CLIENT_AUDIO_MAX_PROMPT_CHARS || "1200", 10),
} as const;

export type ClientAudioPipelineTask = "text-to-audio";
export type ClientAudioDevicePreference = "webgpu";
export type ClientAudioDType = "q4";

export const SUPPORTED_CLIENT_AUDIO_MODELS = {
  "LiquidAI/LFM2.5-Audio-1.5B-ONNX": {
    name: "LFM2.5 Audio 1.5B Q4",
    size: "1.5B q4",
    task: "text-to-audio",
    requiresWebGPU: true,
    preferWebGPU: true,
    device: "webgpu",
    dtype: "q4",
    description:
      "LiquidAI ONNX audio model for browser WebGPU speech generation; used as a dedicated audio-chat path, separate from text chat models.",
    quantized: true,
  },
} as const;

export type ClientAudioModel = keyof typeof SUPPORTED_CLIENT_AUDIO_MODELS;

export function getClientAudioModelInfo(modelName: string) {
  return SUPPORTED_CLIENT_AUDIO_MODELS[modelName as ClientAudioModel];
}
