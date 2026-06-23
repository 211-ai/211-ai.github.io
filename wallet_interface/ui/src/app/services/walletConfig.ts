import type { WalletApiConfig } from "../../services/walletApi";
import { readRuntimeWalletApiBaseUrl, readRuntimeWalletApiConfig } from "../../lib/runtimeConfig";

export const WALLET_API_CONFIG_KEY = "abby-wallet-api-config";

export function readWalletApiConfig(): WalletApiConfig | undefined {
  const apiBaseUrl = resolveWalletApiBaseUrl(import.meta.env.VITE_WALLET_API_BASE_URL as string | undefined);
  const walletId = import.meta.env.VITE_DEMO_WALLET_ID as string | undefined;
  const runtimeConfig = readRuntimeWalletApiConfig();
  const envConfig =
    apiBaseUrl && walletId
      ? {
          apiBaseUrl,
          walletId,
          actorDid: import.meta.env.VITE_DEMO_ACTOR_DID as string | undefined,
          issuerKeyHex: import.meta.env.VITE_DEMO_ISSUER_KEY_HEX as string | undefined,
          audienceKeyHex: import.meta.env.VITE_DEMO_AUDIENCE_KEY_HEX as string | undefined
        }
      : undefined;
  return (
    readUrlWalletApiConfig() ??
    (runtimeConfig
      ? {
          apiBaseUrl: runtimeConfig.apiBaseUrl,
          walletId: runtimeConfig.walletId,
          actorDid: runtimeConfig.actorDid,
          issuerKeyHex: runtimeConfig.issuerKeyHex,
          audienceKeyHex: runtimeConfig.audienceKeyHex
        }
      : undefined) ??
    readStoredWalletApiConfig() ??
    envConfig
  );
}

export function readWalletApiBaseUrl(): string | undefined {
  const urlBaseUrl = readUrlWalletApiBaseUrl();
  if (urlBaseUrl) return urlBaseUrl;
  const runtimeBaseUrl = readRuntimeWalletApiBaseUrl();
  if (runtimeBaseUrl) return runtimeBaseUrl;
  const storedBaseUrl = readStoredWalletApiBaseUrl();
  if (storedBaseUrl) return storedBaseUrl;
  const envBaseUrl = resolveWalletApiBaseUrl(import.meta.env.VITE_WALLET_API_BASE_URL as string | undefined);
  if (envBaseUrl) return envBaseUrl;
  return readProductionWalletApiBaseUrl();
}

function readUrlWalletApiBaseUrl(): string | undefined {
  if (typeof window === "undefined") return undefined;
  return new URL(window.location.href).searchParams.get("walletApiBaseUrl") ?? undefined;
}

function readProductionWalletApiBaseUrl(): string | undefined {
  if (typeof window === "undefined") return undefined;
  return window.location.hostname === "211-ai.com" || window.location.hostname === "www.211-ai.com"
    ? window.location.origin
    : undefined;
}

function resolveWalletApiBaseUrl(apiBaseUrl: string | undefined): string | undefined {
  const trimmed = apiBaseUrl?.trim();
  if (!trimmed) return undefined;
  return trimmed === "same-origin" ? window.location.origin : trimmed;
}

export function readUrlWalletApiConfig(): WalletApiConfig | undefined {
  if (typeof window === "undefined") return undefined;
  const params = new URL(window.location.href).searchParams;
  const apiBaseUrl = params.get("walletApiBaseUrl") ?? undefined;
  const walletId = params.get("walletId") ?? undefined;
  if (!apiBaseUrl || !walletId) return undefined;
  return {
    apiBaseUrl,
    walletId,
    actorDid: params.get("actorDid") ?? undefined,
    issuerKeyHex: params.get("issuerKeyHex") ?? undefined,
    audienceKeyHex: params.get("audienceKeyHex") ?? undefined
  };
}

function readStoredWalletApiConfig(): WalletApiConfig | undefined {
  if (typeof window === "undefined") return undefined;
  try {
    const storedConfig = JSON.parse(window.localStorage.getItem(WALLET_API_CONFIG_KEY) ?? "null") as Partial<
      WalletApiConfig
    > | null;
    if (!storedConfig?.apiBaseUrl || !storedConfig.walletId) return undefined;
    return {
      apiBaseUrl: storedConfig.apiBaseUrl,
      walletId: storedConfig.walletId,
      actorDid: storedConfig.actorDid,
      issuerKeyHex: storedConfig.issuerKeyHex,
      audienceKeyHex: storedConfig.audienceKeyHex
    };
  } catch {
    return undefined;
  }
}

function readStoredWalletApiBaseUrl(): string | undefined {
  if (typeof window === "undefined") return undefined;
  try {
    const storedConfig = JSON.parse(window.localStorage.getItem(WALLET_API_CONFIG_KEY) ?? "null") as Partial<
      WalletApiConfig
    > | null;
    return storedConfig?.apiBaseUrl ?? undefined;
  } catch {
    return undefined;
  }
}
