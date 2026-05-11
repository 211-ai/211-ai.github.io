export const AUDIO_CHAT_CONFIG = {
  defaultModel:
    (import.meta.env?.VITE_CLIENT_AUDIO_MODEL as string | undefined) || "LiquidAI/LFM2.5-Audio-1.5B-ONNX",
  fallbackVoiceModel: "browser-speech-synthesis",
  voiceProxyModel: (import.meta.env?.VITE_VOICE_PROXY_MODEL as string | undefined) || "remote-voice-proxy",
  voiceProxyEnabled: import.meta.env?.VITE_VOICE_PROXY_ENABLED !== "false",
  voiceProxyBaseUrl:
    (import.meta.env?.VITE_VOICE_PROXY_BASE_URL as string | undefined) || "https://animegf.chat:8790/api/voice",
  voiceProxyInferUrl:
    (import.meta.env?.VITE_VOICE_PROXY_INFER_URL as string | undefined) || "https://animegf.chat:8790/api/voice/infer",
  voiceProxyTtsUrl:
    (import.meta.env?.VITE_VOICE_PROXY_TTS_URL as string | undefined) || "https://animegf.chat:8790/api/voice/tts",
  voiceProxySttUrl:
    (import.meta.env?.VITE_VOICE_PROXY_STT_URL as string | undefined) || "https://animegf.chat:8790/api/voice/stt",
  enableLocalAudio: import.meta.env?.VITE_ENABLE_LOCAL_AUDIO !== "false",
  enableMobileLocalAudio: import.meta.env?.VITE_ENABLE_MOBILE_LOCAL_AUDIO === "true",
  enableWebGPU: import.meta.env?.VITE_ENABLE_WEBGPU !== "false",
  requestTimeoutMs: Number.parseInt(import.meta.env?.VITE_CLIENT_AUDIO_REQUEST_TIMEOUT || "12000", 10),
  warmupTimeoutMs: Number.parseInt(import.meta.env?.VITE_CLIENT_AUDIO_WARMUP_TIMEOUT || "10000", 10),
  remoteRequestTimeoutMs: Number.parseInt(import.meta.env?.VITE_REMOTE_AUDIO_REQUEST_TIMEOUT || "45000", 10),
  maxPromptCharacters: Number.parseInt(import.meta.env?.VITE_CLIENT_AUDIO_MAX_PROMPT_CHARS || "1200", 10),
  maxAudioFrames: Number.parseInt(import.meta.env?.VITE_CLIENT_AUDIO_MAX_FRAMES || "160", 10),
  liquidAudioRunnerBaseUrl:
    (import.meta.env?.VITE_LIQUID_AUDIO_RUNNER_BASE_URL as string | undefined) ||
    "https://huggingface.co/spaces/LiquidAI/LFM2.5-Audio-1.5B-transformers-js/raw/main",
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
