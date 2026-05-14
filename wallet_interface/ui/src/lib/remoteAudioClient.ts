import { AUDIO_CHAT_CONFIG } from "./audioChatConfig";
import { resolvePublicHttpsUrl } from "./publicEndpointPolicy";
import { createVoiceProxyFormData, createVoiceProxyTtsBody } from "./voiceProxyPayload";

export interface RemoteAudioGenerationResult {
  audioBlob?: Blob;
  mimeType?: string;
  modelName: string;
  text?: string;
}

export function isRemoteVoiceProxyConfigured(): boolean {
  return Boolean(getRemoteVoiceProxyEndpoint("tts") || getRemoteVoiceProxyEndpoint("voice-reply"));
}

export async function generateRemoteAudio(options: {
  mode: "tts" | "voice-reply";
  text: string;
  systemPrompt?: string;
  userPrompt?: string;
  fallbackText?: string;
  localModelName?: string;
  audioBlob?: Blob;
}): Promise<RemoteAudioGenerationResult> {
  const endpoint = getRemoteVoiceProxyEndpoint(options.mode);
  if (!AUDIO_CHAT_CONFIG.voiceProxyEnabled || !endpoint) {
    throw new Error("Voice proxy is unavailable.");
  }

  let response: Response;
  try {
    response = await fetchWithTimeout(endpoint, buildRequestInit(options));
  } catch (error) {
    throw new Error(formatRemoteAudioNetworkError(endpoint, error));
  }

  if (!response.ok) {
    throw new Error(`Voice proxy request failed with ${response.status}: ${await response.text()}`);
  }

  const contentType = (response.headers.get("Content-Type") || "").toLowerCase();
  if (contentType.startsWith("audio/")) {
    const audioBlob = await response.blob();
    return {
      audioBlob,
      mimeType: audioBlob.type || contentType || "audio/wav",
      modelName: AUDIO_CHAT_CONFIG.voiceProxyModel,
    };
  }

  const payload = await response.json();
  const normalized = normalizeJsonPayload(payload);
  if (!normalized.audioBlob && !normalized.text) {
    throw new Error("Voice proxy returned no audio payload.");
  }
  return normalized;
}

function getRemoteVoiceProxyEndpoint(mode: "tts" | "voice-reply"): string {
  if (mode === "tts") {
    return resolvePublicHttpsUrl(AUDIO_CHAT_CONFIG.voiceProxyTtsUrl);
  }
  return resolvePublicHttpsUrl(AUDIO_CHAT_CONFIG.voiceProxyInferUrl);
}

function buildHeaders(mode: "tts" | "voice-reply"): HeadersInit {
  const headers: Record<string, string> = {
    Accept: "audio/wav, audio/*, application/json",
  };
  if (mode === "tts") {
    headers["Content-Type"] = "application/x-www-form-urlencoded;charset=UTF-8";
  }
  const origin = getBrowserOrigin();
  if (origin) {
    headers["X-Title"] = "Abby 211";
    headers["X-Client-Origin"] = origin;
  }
  return headers;
}

function buildRequestInit(options: {
  mode: "tts" | "voice-reply";
  text: string;
  systemPrompt?: string;
  userPrompt?: string;
  fallbackText?: string;
  audioBlob?: Blob;
}): RequestInit {
  if (options.mode === "tts") {
    return {
      method: "POST",
      headers: buildHeaders(options.mode),
      body: createVoiceProxyTtsBody({ text: options.text }),
    };
  }
  return {
    method: "POST",
    headers: buildHeaders(options.mode),
    body: createVoiceProxyFormData({
      mode: options.mode,
      audioBlob: options.audioBlob,
      text: options.text,
      systemPrompt: options.systemPrompt,
      userPrompt: options.userPrompt,
      fallbackText: options.fallbackText,
    }),
  };
}

async function fetchWithTimeout(endpoint: string, init: RequestInit): Promise<Response> {
  const controller = new AbortController();
  const timeout = globalThis.setTimeout(() => controller.abort(), AUDIO_CHAT_CONFIG.remoteRequestTimeoutMs);
  try {
    return await fetch(endpoint, {
      ...init,
      signal: controller.signal,
    });
  } finally {
    globalThis.clearTimeout(timeout);
  }
}

function normalizeJsonPayload(payload: unknown): RemoteAudioGenerationResult {
  if (!isRecord(payload)) {
    throw new Error("Voice proxy returned an invalid JSON payload.");
  }

  const generatedText = firstString(payload, ["text", "outputText", "output_text"]);
  const modelName = firstString(payload, ["model", "modelName", "model_name"]) || AUDIO_CHAT_CONFIG.voiceProxyModel;
  const audioBase64 = firstString(payload, ["audioBase64", "audio_base64", "audio", "wavBase64", "wav_base64"]);
  if (audioBase64) {
    const mimeType = firstString(payload, ["mimeType", "mime_type"]) || "audio/wav";
    return {
      audioBlob: base64ToBlob(audioBase64, mimeType),
      mimeType,
      modelName,
      text: generatedText,
    };
  }

  if (generatedText) {
    return {
      modelName,
      text: generatedText,
    };
  }

  throw new Error("Voice proxy JSON response did not include base64 audio.");
}

function firstString(payload: Record<string, unknown>, keys: string[]): string | undefined {
  for (const key of keys) {
    const value = payload[key];
    if (typeof value === "string" && value.trim()) {
      return value.trim();
    }
  }
  return undefined;
}

function base64ToBlob(value: string, mimeType: string): Blob {
  const normalized = value.includes(",") ? value.slice(value.indexOf(",") + 1) : value;
  if (typeof atob === "function") {
    const binary = atob(normalized);
    const bytes = new Uint8Array(binary.length);
    for (let index = 0; index < binary.length; index += 1) {
      bytes[index] = binary.charCodeAt(index);
    }
    return new Blob([bytes], { type: mimeType });
  }
  const bufferCtor = (globalThis as { Buffer?: { from: (input: string, encoding: string) => Uint8Array } }).Buffer;
  if (bufferCtor) {
    const bytes = Uint8Array.from(bufferCtor.from(normalized, "base64"));
    return new Blob([bytes], { type: mimeType });
  }
  throw new Error("Base64 audio decoding is unavailable in this browser.");
}

function getBrowserOrigin(): string {
  try {
    return typeof window !== "undefined" ? window.location.origin : "";
  } catch {
    return "";
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function formatRemoteAudioNetworkError(endpoint: string, error: unknown): string {
  if (error instanceof DOMException && error.name === "AbortError") {
    return `Voice proxy request to ${endpoint} timed out before any HTTP response. local fallback attempted: pending caller decision.`;
  }
  const message = error instanceof Error ? error.message.trim() : String(error).trim();
  if (/failed to fetch/i.test(message) || /networkerror/i.test(message)) {
    return `Voice proxy request to ${endpoint} failed before any HTTP response. Failure type: network, CORS, TLS, or connection refused. local fallback attempted: pending caller decision.`;
  }
  return `Voice proxy request to ${endpoint} failed: ${message || "Unknown network error."}`;
}