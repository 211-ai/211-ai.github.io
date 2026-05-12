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

export type AbbyRuntimeConfig = {
  walletApi?: RuntimeWalletApiConfig;
  filecoinStorage?: RuntimeFilecoinStorageConfig;
};

type RuntimeConfigGlobal = typeof globalThis & {
  __ABBY_RUNTIME_CONFIG__?: AbbyRuntimeConfig;
};

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
  return readRuntimeWalletApiConfig()?.apiBaseUrl;
}

export function readRuntimeFilecoinStorageConfig(): ResolvedRuntimeFilecoinStorageConfig | undefined {
  const config = readRuntimeConfig().filecoinStorage;
  if (!config?.uploadUrl) return undefined;
  return {
    uploadUrl: config.uploadUrl,
    clientToken: config.clientToken
  };
}

function readRuntimeConfig(): AbbyRuntimeConfig {
  const runtimeGlobal = globalThis as RuntimeConfigGlobal;
  return runtimeGlobal.__ABBY_RUNTIME_CONFIG__ ?? {};
}

function normalizeRuntimeConfig(payload: AbbyRuntimeConfig | null | undefined): AbbyRuntimeConfig {
  const walletApi = normalizeWalletApiConfig(payload?.walletApi);
  const filecoinStorage = normalizeFilecoinStorageConfig(payload?.filecoinStorage);
  return {
    ...(walletApi ? { walletApi } : {}),
    ...(filecoinStorage ? { filecoinStorage } : {})
  };
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

function normalizeOptionalString(value: string | null | undefined): string | undefined {
  const trimmed = value?.trim();
  return trimmed ? trimmed : undefined;
}

function resolveWalletApiBaseUrl(value: string | null | undefined): string | undefined {
  const normalized = normalizeOptionalString(value);
  if (!normalized) return undefined;
  if (normalized !== "same-origin") return normalized;
  if (typeof window === "undefined") return undefined;
  return window.location.origin;
}