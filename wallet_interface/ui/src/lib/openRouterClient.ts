import { buildClientLlmChatMessages, getClientLlmGenerationParameters } from "./clientLlmPrompting";
import { LLM_CONFIG } from "./llmConfig";

export const OPENROUTER_API_KEY_STORAGE_KEY = "abby-openrouter-api-key";

export interface OpenRouterRuntimeStatus {
  enabled: boolean;
  configured: boolean;
  credentialSource: "browser" | "build" | "proxy" | "none";
  endpoint: string;
  model: string;
  fallbackDelayMs: number;
  lastError?: string;
  lastUsedAt?: string;
}

export interface OpenRouterGenerationResult {
  model: string;
  text: string;
}

export function getOpenRouterRuntimeStatus(
  options: {
    localModelName?: string;
    lastError?: string;
    lastUsedAt?: string;
  } = {},
): OpenRouterRuntimeStatus {
  const credentialSource = getOpenRouterCredentialSource();
  return {
    enabled: LLM_CONFIG.openRouterEnabled,
    configured: LLM_CONFIG.openRouterEnabled && credentialSource !== "none",
    credentialSource,
    endpoint: getOpenRouterEndpoint(),
    model: selectOpenRouterModel(options.localModelName || LLM_CONFIG.defaultModel),
    fallbackDelayMs: LLM_CONFIG.openRouterFallbackDelayMs,
    lastError: options.lastError,
    lastUsedAt: options.lastUsedAt,
  };
}

export function saveOpenRouterApiKey(apiKey: string): void {
  const trimmed = apiKey.trim();
  if (!trimmed) {
    clearOpenRouterApiKey();
    return;
  }
  getStorage()?.setItem(OPENROUTER_API_KEY_STORAGE_KEY, trimmed);
}

export function clearOpenRouterApiKey(): void {
  getStorage()?.removeItem(OPENROUTER_API_KEY_STORAGE_KEY);
}

export async function generateOpenRouterText(options: {
  prompt: string;
  maxTokens: number;
  localModelName: string;
  fallbackReason: string;
}): Promise<OpenRouterGenerationResult> {
  const status = getOpenRouterRuntimeStatus({ localModelName: options.localModelName });
  if (!status.enabled) {
    throw new Error("OpenRouter fallback is disabled.");
  }
  if (!status.configured) {
    throw new Error("OpenRouter fallback needs an API key or proxy endpoint.");
  }

  const model = selectOpenRouterModel(options.localModelName);
  const { do_sample: _doSample, ...generationParameters } = getClientLlmGenerationParameters(model);
  const body = {
    model,
    messages: buildClientLlmChatMessages(options.prompt),
    max_tokens: Math.max(16, options.maxTokens),
    ...generationParameters,
    metadata: {
      app: "abby-211",
      fallback_reason: options.fallbackReason.slice(0, 128),
    },
  };

  const response = await fetchWithTimeout(getOpenRouterEndpoint(), {
    body: JSON.stringify(body),
    headers: buildOpenRouterHeaders(),
    method: "POST",
  });

  if (!response.ok) {
    throw new Error(`OpenRouter request failed with ${response.status}: ${await response.text()}`);
  }

  const payload = await response.json();
  const text = extractOpenRouterText(payload);
  if (!text) {
    throw new Error("OpenRouter returned an empty response.");
  }

  return {
    model: typeof payload?.model === "string" ? payload.model : model,
    text,
  };
}

function selectOpenRouterModel(localModelName: string): string {
  return /thinking/i.test(localModelName)
    ? LLM_CONFIG.openRouterThinkingModel
    : LLM_CONFIG.openRouterInstructModel;
}

function getOpenRouterEndpoint(): string {
  return LLM_CONFIG.openRouterProxyUrl || LLM_CONFIG.openRouterEndpoint;
}

function getOpenRouterCredentialSource(): OpenRouterRuntimeStatus["credentialSource"] {
  if (LLM_CONFIG.openRouterProxyUrl) {
    return "proxy";
  }
  if (readStoredOpenRouterApiKey()) {
    return "browser";
  }
  if (LLM_CONFIG.openRouterApiKey.trim()) {
    return "build";
  }
  return "none";
}

function buildOpenRouterHeaders(): HeadersInit {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-OpenRouter-Experimental-Metadata": "enabled",
  };
  if (!LLM_CONFIG.openRouterProxyUrl) {
    const apiKey = readStoredOpenRouterApiKey() || LLM_CONFIG.openRouterApiKey.trim();
    if (apiKey) {
      headers.Authorization = `Bearer ${apiKey}`;
    }
  }
  const origin = getBrowserOrigin();
  if (origin) {
    headers["HTTP-Referer"] = origin;
    headers["X-Title"] = "Abby 211";
  }
  return headers;
}

async function fetchWithTimeout(endpoint: string, init: RequestInit): Promise<Response> {
  const controller = new AbortController();
  const timeout = globalThis.setTimeout(() => controller.abort(), LLM_CONFIG.openRouterRequestTimeoutMs);
  try {
    return await fetch(endpoint, {
      ...init,
      signal: controller.signal,
    });
  } finally {
    globalThis.clearTimeout(timeout);
  }
}

function extractOpenRouterText(payload: unknown): string {
  if (!isRecord(payload)) {
    return "";
  }
  const choice = Array.isArray(payload.choices) ? payload.choices[0] : undefined;
  if (!isRecord(choice) || !isRecord(choice.message)) {
    return "";
  }
  const content = choice.message.content;
  if (typeof content === "string") {
    return content.trim();
  }
  if (Array.isArray(content)) {
    return content
      .map((part) => (isRecord(part) && typeof part.text === "string" ? part.text : ""))
      .join("")
      .trim();
  }
  return "";
}

function readStoredOpenRouterApiKey(): string {
  return getStorage()?.getItem(OPENROUTER_API_KEY_STORAGE_KEY)?.trim() || "";
}

function getStorage(): Storage | undefined {
  try {
    return typeof globalThis.localStorage !== "undefined" ? globalThis.localStorage : undefined;
  } catch {
    return undefined;
  }
}

function getBrowserOrigin(): string {
  try {
    return typeof window !== "undefined" ? window.location.origin : "";
  } catch {
    return "";
  }
}

function isRecord(value: unknown): value is Record<string, any> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
