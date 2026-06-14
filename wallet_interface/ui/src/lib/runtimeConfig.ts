export type RuntimeWalletApiConfig = {
  apiBaseUrl?: string;
  walletId?: string;
  actorDid?: string;
  issuerKeyHex?: string;
  audienceKeyHex?: string;
};

export type ResolvedRuntimeWalletApiConfig = {
  apiBaseUrl: string;
  walletId: string;
  actorDid?: string;
  issuerKeyHex?: string;
  audienceKeyHex?: string;
};

export type RuntimeFilecoinStorageConfig = {
  uploadUrl?: string;
  clientToken?: string;
};

export type ResolvedRuntimeFilecoinStorageConfig = {
  uploadUrl: string;
  clientToken?: string;
};

export type RuntimeWalrusStorageConfig = {
  publisherUrl?: string;
  aggregatorUrl?: string;
  deleteUrl?: string;
  clientToken?: string;
  epochs?: number | string;
  deletable?: boolean | string;
};

export type ResolvedRuntimeWalrusStorageConfig = {
  publisherUrl: string;
  aggregatorUrl?: string;
  deleteUrl?: string;
  clientToken?: string;
  epochs?: number;
  deletable?: boolean;
};

export type RuntimeVoiceProxyConfig = {
  enabled?: boolean | string;
  model?: string;
  baseUrl?: string;
  inferUrl?: string;
  ttsUrl?: string;
  sttUrl?: string;
  fallbackInferUrl?: string;
  fallbackTtsUrl?: string;
  fallbackSttUrl?: string;
  fallbackModel?: string;
};

export type RuntimePrecomputedAudioConfig = {
  manifestUrl?: string;
};

export type ResolvedRuntimeVoiceProxyConfig = {
  enabled?: boolean;
  model?: string;
  baseUrl?: string;
  inferUrl?: string;
  ttsUrl?: string;
  sttUrl?: string;
  fallbackInferUrl?: string;
  fallbackTtsUrl?: string;
  fallbackSttUrl?: string;
  fallbackModel?: string;
};

export type ResolvedRuntimePrecomputedAudioConfig = {
  manifestUrl: string;
};

export type RuntimeWorldIdEnvironment = "staging" | "production";

export type RuntimeWorldIdDisabledReason =
  | "backend_disabled"
  | "missing_app_id"
  | "missing_action";

export type RuntimeWorldIdConfig = {
  enabled?: boolean | string;
  appId?: string;
  action?: string;
  environment?: string;
};

export type ResolvedRuntimeWorldIdConfig = {
  enabled: boolean;
  backendEnabled: boolean;
  environment: RuntimeWorldIdEnvironment;
  action: string;
  appId?: string;
  disabledReason?: RuntimeWorldIdDisabledReason;
};

export type AbbyRuntimeConfig = {
  walletApi?: RuntimeWalletApiConfig;
  filecoinStorage?: RuntimeFilecoinStorageConfig;
  walrusStorage?: RuntimeWalrusStorageConfig;
  voiceProxy?: RuntimeVoiceProxyConfig;
  precomputedAudio?: RuntimePrecomputedAudioConfig;
  worldId?: RuntimeWorldIdConfig;
};

type RuntimeConfigGlobal = typeof globalThis & {
  __ABBY_RUNTIME_CONFIG__?: AbbyRuntimeConfig;
};

const DEFAULT_WORLD_ID_ACTION = "wallet-attach-world-id-v1";
const DEFAULT_WORLD_ID_ENVIRONMENT: RuntimeWorldIdEnvironment = "staging";

export async function loadRuntimeConfig(): Promise<void> {
  if (typeof window === "undefined") return;
  const runtimeGlobal = globalThis as RuntimeConfigGlobal;
  if (runtimeGlobal.__ABBY_RUNTIME_CONFIG__) return;

  try {
    const response = await fetch(new URL("runtime-config.json", window.location.href), { cache: "no-store" });
    if (!response.ok) {
      runtimeGlobal.__ABBY_RUNTIME_CONFIG__ = {};
      return;
    }
    const payload = (await response.json()) as AbbyRuntimeConfig;
    runtimeGlobal.__ABBY_RUNTIME_CONFIG__ = normalizeRuntimeConfig(payload);
  } catch {
    runtimeGlobal.__ABBY_RUNTIME_CONFIG__ = {};
  }
}

export function readRuntimeWalletApiConfig(): ResolvedRuntimeWalletApiConfig | undefined {
  const config = readRuntimeConfig().walletApi;
  const apiBaseUrl = resolveWalletApiBaseUrl(config?.apiBaseUrl);
  if (!apiBaseUrl || !config?.walletId) return undefined;
  return {
    apiBaseUrl,
    walletId: config.walletId,
    actorDid: config.actorDid,
    issuerKeyHex: config.issuerKeyHex,
    audienceKeyHex: config.audienceKeyHex
  };
}

export function readRuntimeWalletApiBaseUrl(): string | undefined {
  return resolveWalletApiBaseUrl(readRuntimeConfig().walletApi?.apiBaseUrl);
}

export function readRuntimeFilecoinStorageConfig(): ResolvedRuntimeFilecoinStorageConfig | undefined {
  const config = readRuntimeConfig().filecoinStorage;
  if (!config?.uploadUrl) return undefined;
  return {
    uploadUrl: config.uploadUrl,
    clientToken: config.clientToken
  };
}

export function readRuntimeWalrusStorageConfig(): ResolvedRuntimeWalrusStorageConfig | undefined {
  return normalizeWalrusStorageConfig(readRuntimeConfig().walrusStorage);
}

export function readRuntimeVoiceProxyConfig(): ResolvedRuntimeVoiceProxyConfig | undefined {
  return normalizeVoiceProxyConfig(readRuntimeConfig().voiceProxy);
}

export function readRuntimePrecomputedAudioConfig(): ResolvedRuntimePrecomputedAudioConfig | undefined {
  return normalizePrecomputedAudioConfig(readRuntimeConfig().precomputedAudio);
}

export function readRuntimePrecomputedAudioManifestUrl(): string | undefined {
  return readRuntimePrecomputedAudioConfig()?.manifestUrl;
}

export function readRuntimeWorldIdConfig(): ResolvedRuntimeWorldIdConfig {
  return (
    resolveWorldIdConfig(readRuntimeConfig().worldId ?? readEnvWorldIdConfig()) ??
    createDisabledWorldIdConfig("backend_disabled")
  );
}

export function isRuntimeWorldIdEnabled(config = readRuntimeWorldIdConfig()): boolean {
  return config.enabled;
}

function readRuntimeConfig(): AbbyRuntimeConfig {
  const runtimeGlobal = globalThis as RuntimeConfigGlobal;
  return runtimeGlobal.__ABBY_RUNTIME_CONFIG__ ?? {};
}

function normalizeRuntimeConfig(payload: AbbyRuntimeConfig | null | undefined): AbbyRuntimeConfig {
  const walletApi = normalizeWalletApiConfig(payload?.walletApi) ?? normalizeWalletApiBaseConfig(payload?.walletApi);
  const filecoinStorage = normalizeFilecoinStorageConfig(payload?.filecoinStorage);
  const walrusStorage = normalizeWalrusStorageConfig(payload?.walrusStorage);
  const voiceProxy = normalizeVoiceProxyConfig(payload?.voiceProxy);
  const precomputedAudio = normalizePrecomputedAudioConfig(payload?.precomputedAudio);
  const worldId = normalizeRuntimeWorldIdConfig(payload?.worldId);
  return {
    ...(walletApi ? { walletApi } : {}),
    ...(filecoinStorage ? { filecoinStorage } : {}),
    ...(walrusStorage ? { walrusStorage } : {}),
    ...(voiceProxy ? { voiceProxy } : {}),
    ...(precomputedAudio ? { precomputedAudio } : {}),
    ...(worldId ? { worldId } : {}),
  };
}

function normalizeWalletApiBaseConfig(
  config: RuntimeWalletApiConfig | null | undefined
): RuntimeWalletApiConfig | undefined {
  if (!config) return undefined;
  const apiBaseUrl = normalizeOptionalString(config.apiBaseUrl);
  if (!apiBaseUrl) return undefined;
  return { apiBaseUrl };
}

function normalizeWalletApiConfig(
  config: RuntimeWalletApiConfig | null | undefined
): ResolvedRuntimeWalletApiConfig | undefined {
  if (!config) return undefined;
  const apiBaseUrl = resolveWalletApiBaseUrl(config.apiBaseUrl);
  const walletId = normalizeOptionalString(config.walletId);
  if (!apiBaseUrl || !walletId) return undefined;
  return {
    apiBaseUrl,
    walletId,
    actorDid: normalizeOptionalString(config.actorDid),
    issuerKeyHex: normalizeOptionalString(config.issuerKeyHex),
    audienceKeyHex: normalizeOptionalString(config.audienceKeyHex)
  };
}

function normalizeFilecoinStorageConfig(
  config: RuntimeFilecoinStorageConfig | null | undefined
): ResolvedRuntimeFilecoinStorageConfig | undefined {
  if (!config) return undefined;
  const uploadUrl = normalizeOptionalString(config.uploadUrl);
  if (!uploadUrl) return undefined;
  return {
    uploadUrl,
    clientToken: normalizeOptionalString(config.clientToken)
  };
}

function normalizeWalrusStorageConfig(
  config: RuntimeWalrusStorageConfig | null | undefined
): ResolvedRuntimeWalrusStorageConfig | undefined {
  if (!config) return undefined;
  const publisherUrl = normalizeOptionalString(config.publisherUrl);
  if (!publisherUrl) return undefined;
  return {
    publisherUrl,
    aggregatorUrl: normalizeOptionalString(config.aggregatorUrl),
    deleteUrl: normalizeOptionalString(config.deleteUrl),
    clientToken: normalizeOptionalString(config.clientToken),
    epochs: normalizeOptionalNumber(config.epochs),
    deletable: normalizeOptionalBoolean(config.deletable)
  };
}

function normalizeVoiceProxyConfig(
  config: RuntimeVoiceProxyConfig | null | undefined
): ResolvedRuntimeVoiceProxyConfig | undefined {
  if (!config) return undefined;
  const enabled = normalizeOptionalBoolean(config.enabled);
  const model = normalizeOptionalString(config.model);
  const baseUrl = normalizeOptionalString(config.baseUrl);
  const inferUrl = normalizeOptionalString(config.inferUrl);
  const ttsUrl = normalizeOptionalString(config.ttsUrl);
  const sttUrl = normalizeOptionalString(config.sttUrl);
  const fallbackInferUrl = normalizeOptionalString(config.fallbackInferUrl);
  const fallbackTtsUrl = normalizeOptionalString(config.fallbackTtsUrl);
  const fallbackSttUrl = normalizeOptionalString(config.fallbackSttUrl);
  const fallbackModel = normalizeOptionalString(config.fallbackModel);
  if (
    enabled === undefined &&
    !model &&
    !baseUrl &&
    !inferUrl &&
    !ttsUrl &&
    !sttUrl &&
    !fallbackInferUrl &&
    !fallbackTtsUrl &&
    !fallbackSttUrl &&
    !fallbackModel
  ) {
    return undefined;
  }
  return {
    ...(enabled !== undefined ? { enabled } : {}),
    ...(model ? { model } : {}),
    ...(baseUrl ? { baseUrl } : {}),
    ...(inferUrl ? { inferUrl } : {}),
    ...(ttsUrl ? { ttsUrl } : {}),
    ...(sttUrl ? { sttUrl } : {}),
    ...(fallbackInferUrl ? { fallbackInferUrl } : {}),
    ...(fallbackTtsUrl ? { fallbackTtsUrl } : {}),
    ...(fallbackSttUrl ? { fallbackSttUrl } : {}),
    ...(fallbackModel ? { fallbackModel } : {}),
  };
}

function normalizePrecomputedAudioConfig(
  config: RuntimePrecomputedAudioConfig | null | undefined
): ResolvedRuntimePrecomputedAudioConfig | undefined {
  if (!config) return undefined;
  const manifestUrl = normalizeOptionalString(config.manifestUrl);
  if (!manifestUrl) return undefined;
  return { manifestUrl };
}

function normalizeRuntimeWorldIdConfig(
  config: RuntimeWorldIdConfig | null | undefined
): ResolvedRuntimeWorldIdConfig | undefined {
  return resolveWorldIdConfig(config);
}

function readEnvWorldIdConfig(): RuntimeWorldIdConfig | undefined {
  const enabled =
    readEnv("VITE_WORLD_ID_ENABLED") ??
    readEnv("VITE_WALLET_WORLD_ID_ENABLED");
  const appId =
    readEnv("VITE_WORLD_ID_APP_ID") ??
    readEnv("VITE_WALLET_WORLD_ID_APP_ID");
  const action =
    readEnv("VITE_WORLD_ID_ACTION") ??
    readEnv("VITE_WALLET_WORLD_ID_ACTION");
  const environment =
    readEnv("VITE_WORLD_ID_ENVIRONMENT") ??
    readEnv("VITE_WALLET_WORLD_ID_ENVIRONMENT");
  if (enabled === undefined && !appId && !action && !environment) return undefined;
  return { enabled, appId, action, environment };
}

function resolveWorldIdConfig(
  config: RuntimeWorldIdConfig | null | undefined
): ResolvedRuntimeWorldIdConfig | undefined {
  if (!config) return undefined;
  const enabled = normalizeOptionalBoolean(config.enabled) ?? false;
  const appId = normalizeOptionalString(config.appId);
  const action = normalizeOptionalString(config.action) ?? DEFAULT_WORLD_ID_ACTION;
  const environment = normalizeWorldIdEnvironment(config.environment);
  if (!enabled) return createDisabledWorldIdConfig("backend_disabled", { appId, action, environment });
  if (!appId) return createDisabledWorldIdConfig("missing_app_id", { action, environment });
  if (!action) return createDisabledWorldIdConfig("missing_action", { appId, environment });
  return {
    enabled: true,
    backendEnabled: true,
    environment,
    action,
    appId
  };
}

function createDisabledWorldIdConfig(
  disabledReason: RuntimeWorldIdDisabledReason,
  {
    action = DEFAULT_WORLD_ID_ACTION,
    appId,
    environment = DEFAULT_WORLD_ID_ENVIRONMENT
  }: {
    action?: string;
    appId?: string;
    environment?: RuntimeWorldIdEnvironment;
  } = {}
): ResolvedRuntimeWorldIdConfig {
  return {
    enabled: false,
    backendEnabled: false,
    environment,
    action,
    ...(appId ? { appId } : {}),
    disabledReason
  };
}

function normalizeWorldIdEnvironment(value: string | null | undefined): RuntimeWorldIdEnvironment {
  return normalizeOptionalString(value) === "production" ? "production" : DEFAULT_WORLD_ID_ENVIRONMENT;
}

function readEnv(key: string): string | undefined {
  const value = import.meta.env[key];
  return typeof value === "string" && value.trim() ? value : undefined;
}

function normalizeOptionalString(value: number | string | null | undefined): string | undefined {
  const trimmed = typeof value === "number" ? String(value) : value?.trim();
  return trimmed ? trimmed : undefined;
}

function normalizeOptionalBoolean(value: boolean | string | null | undefined): boolean | undefined {
  if (typeof value === "boolean") return value;
  const normalized = normalizeOptionalString(value);
  if (!normalized) return undefined;
  if (["1", "true", "yes", "on"].includes(normalized.toLowerCase())) return true;
  if (["0", "false", "no", "off"].includes(normalized.toLowerCase())) return false;
  return undefined;
}

function normalizeOptionalNumber(value: number | string | null | undefined): number | undefined {
  if (typeof value === "number" && Number.isFinite(value) && value > 0) return value;
  const normalized = normalizeOptionalString(value);
  if (!normalized) return undefined;
  const parsed = Number(normalized);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : undefined;
}

function resolveWalletApiBaseUrl(value: string | null | undefined): string | undefined {
  const normalized = normalizeOptionalString(value);
  if (!normalized) return undefined;
  if (normalized !== "same-origin") return normalized;
  if (typeof window === "undefined") return undefined;
  return window.location.origin;
}
