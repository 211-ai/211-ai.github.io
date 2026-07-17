/// <reference types="vite/client" />
import type { WalletApiConfig, WalletMagicUcan } from "../../features/wallet/lib/walletApi";
import { loadLatestWalletRecoveryBundle } from "../../features/wallet/lib/walletApi";
import { readUrlWalletApiConfig, readWalletApiConfig, readWalletApiBaseUrl } from "../services/walletConfig";
import { getRouteFromHash } from "../appState";
import { normalizeAppRoute } from "../config/navigation";
import type { RouteId } from "../../models/abby";
import { getServicePlanDocIdFromHash } from "../ServicePlanScreen";
import { getServiceDetailDocIdFromHash } from "../../agent/tools/serviceDetailTools";

// ─── Route init helper ────────────────────────────────────────────────────────

export function getInitialRouteFromHash(): RouteId {
  return getServicePlanDocIdFromHash() || getServiceDetailDocIdFromHash()
    ? "social-services"
    : normalizeAppRoute(getRouteFromHash());
}

// ─── Constants ───────────────────────────────────────────────────────────────

export const APP_SESSION_KEY = "abby-ui-session-v1";
export const MAGIC_LOGIN_PARAM = "abbyLogin";
export const MAGIC_LOGIN_TTL_MS = 10 * 60 * 1000;
export const MAGIC_LOGIN_DEMO_SIGNING_CONTEXT = "abby-static-demo-login-v1";
export const MAGIC_LOGIN_UCAN_KEY = "abby.magicLoginUcan.v1";
export const WALLET_RECOVERY_BUNDLE_CACHE_PREFIX = "abby.walletRecoveryBundle.v1.";
export const WALLET_DEVICE_RECOVERY_KEY_PREFIX = "abby.walletDeviceRecoveryKey.v1.";

// ─── Types ────────────────────────────────────────────────────────────────────

export type LoginPortal = "client" | "provider";

export type MagicLoginPayload = {
  portal: LoginPortal;
  contact: string;
  issuedAt: number;
  expiresAt: number;
  salt: string;
  digest: string;
};

export type LoginChallenge = MagicLoginPayload & {
  oneTimePad: string;
  magicLink: string;
};

export type LoginAuthResult = {
  portal: LoginPortal;
  contact: string;
  walletConfig?: WalletApiConfig;
  ucan?: WalletMagicUcan;
};

export type ServerMagicLoginResponse = {
  channel?: string;
  contact?: string;
  portal?: LoginPortal;
  valid?: boolean;
  wallet_config?: {
    actorDid?: string;
    apiBaseUrl?: string;
    walletId?: string;
  };
  ucan?: WalletMagicUcan;
};

export type WalletRecoveryQrPayload = {
  apiBaseUrl?: string;
  bundleId: string;
  passphrase?: string;
  schema: "211-ai-wallet-recovery-qr-v1";
  serverCanDecrypt: false;
  containsRecoverySecret?: true;
  walletId: string;
  wrappingMethod?: string;
};

// ─── Pure encoding helpers ────────────────────────────────────────────────────

export function randomBase64Url(byteLength: number): string {
  const bytes = new Uint8Array(byteLength);
  crypto.getRandomValues(bytes);
  let binary = "";
  bytes.forEach((byte) => {
    binary += String.fromCharCode(byte);
  });
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

export function randomHex(byteLength: number): string {
  const bytes = new Uint8Array(byteLength);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
}

export function bytesToBase64Url(bytes: Uint8Array): string {
  let binary = "";
  bytes.forEach((byte) => {
    binary += String.fromCharCode(byte);
  });
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

export function base64UrlToBytes(value: string): Uint8Array {
  const padded = value.replace(/-/g, "+").replace(/_/g, "/").padEnd(Math.ceil(value.length / 4) * 4, "=");
  const binary = atob(padded);
  return Uint8Array.from(binary, (char) => char.charCodeAt(0));
}

export function bytesToArrayBuffer(bytes: Uint8Array): ArrayBuffer {
  return bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength) as ArrayBuffer;
}

// ─── Crypto helpers ───────────────────────────────────────────────────────────

export async function deriveRecoveryPassphraseKey(passphrase: string, salt: Uint8Array, iterations: number): Promise<CryptoKey> {
  const baseKey = await crypto.subtle.importKey("raw", new TextEncoder().encode(passphrase), "PBKDF2", false, [
    "deriveKey"
  ]);
  return crypto.subtle.deriveKey(
    {
      hash: "SHA-256",
      iterations,
      name: "PBKDF2",
      salt: bytesToArrayBuffer(salt)
    },
    baseKey,
    { length: 256, name: "AES-GCM" },
    false,
    ["encrypt", "decrypt"]
  );
}

export async function sha256Base64Url(value: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
  return bytesToBase64Url(new Uint8Array(digest));
}

// ─── Device recovery key storage ─────────────────────────────────────────────

export function walletDeviceRecoveryStorageKey(walletId: string): string {
  return `${WALLET_DEVICE_RECOVERY_KEY_PREFIX}${walletId}`;
}

export function readWalletDeviceRecoveryRawKey(walletId: string): Uint8Array | undefined {
  if (typeof window === "undefined") return undefined;
  const stored = window.localStorage.getItem(walletDeviceRecoveryStorageKey(walletId));
  return stored ? base64UrlToBytes(stored) : undefined;
}

export function storeWalletDeviceRecoveryRawKey(walletId: string, raw: Uint8Array): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(walletDeviceRecoveryStorageKey(walletId), bytesToBase64Url(raw));
}

export async function getOrCreateWalletDeviceRecoveryRawKey(walletId: string): Promise<Uint8Array> {
  const stored = readWalletDeviceRecoveryRawKey(walletId);
  if (stored) return stored;
  const raw = new Uint8Array(32);
  crypto.getRandomValues(raw);
  storeWalletDeviceRecoveryRawKey(walletId, raw);
  return raw;
}

export async function getOrCreateWalletDeviceRecoveryKey(walletId: string): Promise<CryptoKey> {
  const raw = await getOrCreateWalletDeviceRecoveryRawKey(walletId);
  return crypto.subtle.importKey("raw", bytesToArrayBuffer(raw), "AES-GCM", false, ["encrypt", "decrypt"]);
}

// ─── Recovery bundle builders ─────────────────────────────────────────────────

export async function buildEncryptedRecoveryBundle({
  actorDid,
  contact,
  key,
  kdf,
  walletContentKey,
  walletId,
  wrappedKey
}: {
  actorDid: string;
  contact: string;
  key: CryptoKey;
  kdf?: Record<string, unknown>;
  walletContentKey: Uint8Array;
  walletId: string;
  wrappedKey: string;
}): Promise<{
  encryptedBundle: Record<string, unknown>;
  publicMetadata: Record<string, unknown>;
}> {
  const iv = new Uint8Array(12);
  crypto.getRandomValues(iv);
  const plaintext = new TextEncoder().encode(
    JSON.stringify({
      schema: "211-ai-wallet-recovery-secret-v1",
      walletId,
      actorDid,
      walletContentKey: bytesToBase64Url(walletContentKey),
      createdAt: new Date().toISOString(),
      note: "Client-side recovery material. The service provider never receives this plaintext."
    })
  );
  const ciphertext = await crypto.subtle.encrypt({ name: "AES-GCM", iv: bytesToArrayBuffer(iv) }, key, plaintext);
  const contactHash = await sha256Base64Url(contact.trim().toLowerCase());
  return {
    encryptedBundle: {
      schema: "211-ai-wallet-recovery-bundle-v1",
      ciphertext: bytesToBase64Url(new Uint8Array(ciphertext)),
      iv: bytesToBase64Url(iv),
      algorithm: "AES-GCM",
      wrappedKey,
      kdf: kdf ?? {},
      plaintextKeySentToServer: false
    },
    publicMetadata: {
      contactHash,
      recoveryMethods: [wrappedKey],
      serverCanDecrypt: false,
      containsPlaintextWalletKey: false
    }
  };
}

export async function buildPassphraseWrappedRecoveryBundle({
  actorDid,
  contact,
  passphrase,
  walletId
}: {
  actorDid: string;
  contact: string;
  passphrase: string;
  walletId: string;
}): Promise<{
  encryptedBundle: Record<string, unknown>;
  kdf: Record<string, unknown>;
  publicMetadata: Record<string, unknown>;
}> {
  const salt = new Uint8Array(16);
  crypto.getRandomValues(salt);
  const iterations = 310000;
  const key = await deriveRecoveryPassphraseKey(passphrase, salt, iterations);
  const walletContentKey = await getOrCreateWalletDeviceRecoveryRawKey(walletId);
  const kdf = {
    name: "PBKDF2",
    hash: "SHA-256",
    iterations,
    salt: bytesToBase64Url(salt)
  };
  const bundle = await buildEncryptedRecoveryBundle({
    actorDid,
    contact,
    key,
    kdf,
    walletContentKey,
    walletId,
    wrappedKey: "passphrase-pbkdf2-aes-gcm"
  });
  return { ...bundle, kdf };
}

export async function decryptPassphraseRecoveryBundle(
  bundle: Record<string, unknown>,
  passphrase: string
): Promise<{ actorDid?: string; walletContentKey: Uint8Array; walletId?: string }> {
  const kdf = (bundle.kdf && typeof bundle.kdf === "object" ? bundle.kdf : {}) as Record<string, unknown>;
  const salt = typeof kdf.salt === "string" ? base64UrlToBytes(kdf.salt) : undefined;
  const iterations = typeof kdf.iterations === "number" ? kdf.iterations : 310000;
  const ciphertext = typeof bundle.ciphertext === "string" ? base64UrlToBytes(bundle.ciphertext) : undefined;
  const iv = typeof bundle.iv === "string" ? base64UrlToBytes(bundle.iv) : undefined;
  if (!salt || !ciphertext || !iv) {
    throw new Error("The recovery bundle is missing passphrase recovery metadata.");
  }
  const key = await deriveRecoveryPassphraseKey(passphrase, salt, iterations);
  const decrypted = await crypto.subtle.decrypt(
    { name: "AES-GCM", iv: bytesToArrayBuffer(iv) },
    key,
    bytesToArrayBuffer(ciphertext)
  );
  const payload = JSON.parse(new TextDecoder().decode(decrypted)) as {
    actorDid?: string;
    walletContentKey?: string;
    walletId?: string;
  };
  if (!payload.walletContentKey) {
    throw new Error("The recovery bundle did not contain a wallet key.");
  }
  return {
    actorDid: payload.actorDid,
    walletContentKey: base64UrlToBytes(payload.walletContentKey),
    walletId: payload.walletId
  };
}

export function readCachedRecoveryBundle(walletId: string): Record<string, unknown> | undefined {
  if (typeof window === "undefined") return undefined;
  const raw = window.localStorage.getItem(`${WALLET_RECOVERY_BUNDLE_CACHE_PREFIX}${walletId}`);
  if (!raw) return undefined;
  try {
    const parsed = JSON.parse(raw) as { bundle?: { encrypted_bundle?: Record<string, unknown> } };
    return parsed.bundle?.encrypted_bundle;
  } catch {
    return undefined;
  }
}

export function readMagicLoginUcan(): WalletMagicUcan | undefined {
  if (typeof window === "undefined") return undefined;
  const raw = window.localStorage.getItem(MAGIC_LOGIN_UCAN_KEY);
  if (!raw) return undefined;
  try {
    const parsed = JSON.parse(raw) as WalletMagicUcan;
    return parsed?.token ? parsed : undefined;
  } catch {
    return undefined;
  }
}

export function buildWalletRecoveryQrPayload(
  config: WalletApiConfig,
  bundleId: string,
  wrappingMethod?: string,
  passphrase?: string
): WalletRecoveryQrPayload {
  return {
    apiBaseUrl: config.apiBaseUrl,
    bundleId,
    containsRecoverySecret: passphrase ? true : undefined,
    passphrase: passphrase || undefined,
    schema: "211-ai-wallet-recovery-qr-v1",
    serverCanDecrypt: false,
    walletId: config.walletId,
    wrappingMethod
  };
}

export function parseWalletRecoveryQrPayload(value: string): WalletRecoveryQrPayload {
  const parsed = JSON.parse(value) as Partial<WalletRecoveryQrPayload>;
  if (
    parsed.schema !== "211-ai-wallet-recovery-qr-v1" ||
    !parsed.walletId ||
    !parsed.bundleId ||
    parsed.serverCanDecrypt !== false
  ) {
    throw new Error("That QR is not a supported Abby wallet recovery QR.");
  }
  return parsed as WalletRecoveryQrPayload;
}

export async function buildClientWrappedRecoveryBundle({
  actorDid,
  contact,
  walletId
}: {
  actorDid: string;
  contact: string;
  walletId: string;
}): Promise<{
  encryptedBundle: Record<string, unknown>;
  publicMetadata: Record<string, unknown>;
}> {
  const walletContentKey = await getOrCreateWalletDeviceRecoveryRawKey(walletId);
  const deviceKey = await getOrCreateWalletDeviceRecoveryKey(walletId);
  return buildEncryptedRecoveryBundle({
    actorDid,
    contact,
    key: deviceKey,
    walletContentKey,
    walletId,
    wrappedKey: "device-local-aes-gcm-key"
  });
}

export async function cacheEncryptedRecoveryBundleFromMagicLogin(walletConfig: WalletApiConfig, ucan: WalletMagicUcan): Promise<void> {
  if (!ucan.token || typeof window === "undefined") return;
  const response = await loadLatestWalletRecoveryBundle(walletConfig, ucan.token);
  window.localStorage.setItem(
    `${WALLET_RECOVERY_BUNDLE_CACHE_PREFIX}${walletConfig.walletId}`,
    JSON.stringify({
      cachedAt: new Date().toISOString(),
      bundle: response.bundle,
      privacy: response.privacy,
      ucan: {
        audience: ucan.audience,
        expires_at: ucan.expires_at,
        profile: ucan.profile
      }
    })
  );
}

// ─── Magic login helpers ──────────────────────────────────────────────────────

export function randomOneTimePad(length = 6): string {
  const bytes = new Uint8Array(length);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (byte) => String(byte % 10)).join("");
}

export function encodeMagicLoginPayload(payload: MagicLoginPayload): string {
  return btoa(JSON.stringify(payload)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

export function decodeMagicLoginPayload(token: string): MagicLoginPayload | undefined {
  try {
    const padded = token.replace(/-/g, "+").replace(/_/g, "/").padEnd(Math.ceil(token.length / 4) * 4, "=");
    const parsed = JSON.parse(atob(padded));
    if (
      parsed &&
      (parsed.portal === "client" || parsed.portal === "provider") &&
      typeof parsed.contact === "string" &&
      typeof parsed.issuedAt === "number" &&
      typeof parsed.expiresAt === "number" &&
      typeof parsed.salt === "string" &&
      typeof parsed.digest === "string"
    ) {
      return parsed;
    }
  } catch {
    return undefined;
  }
  return undefined;
}

export async function createMagicLoginDigest({
  contact,
  expiresAt,
  issuedAt,
  portal,
  salt
}: Omit<MagicLoginPayload, "digest">): Promise<string> {
  const input = [MAGIC_LOGIN_DEMO_SIGNING_CONTEXT, portal, contact, issuedAt, expiresAt, salt].join("|");
  const hash = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(input));
  return Array.from(new Uint8Array(hash), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

// ─── Login contact helpers ────────────────────────────────────────────────────

export function normalizeLoginContact(value: string): string {
  const trimmed = value.trim();
  if (trimmed.includes("@")) return trimmed.toLowerCase();
  return trimmed.replace(/[^\d+]/g, "");
}

export function isValidLoginContact(value: string): boolean {
  const normalized = normalizeLoginContact(value);
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalized) || normalized.replace(/\D/g, "").length >= 10;
}

export function normalizeServerWalletConfig(value: ServerMagicLoginResponse["wallet_config"]): WalletApiConfig | undefined {
  if (!value?.apiBaseUrl || !value.walletId) return undefined;
  return {
    actorDid: value.actorDid,
    apiBaseUrl: value.apiBaseUrl,
    walletId: value.walletId
  };
}

export function resolveMagicLoginApiBaseUrl(): string {
  const configured = (import.meta.env.VITE_MAGIC_LOGIN_API_BASE_URL as string | undefined)?.trim();
  if (configured) return configured;
  if (typeof window !== "undefined" && window.location.hostname === "211-ai.github.io") {
    return "https://211-ai.com";
  }
  return readWalletApiBaseUrl() ?? (typeof window !== "undefined" ? window.location.origin : "");
}

export function shouldAllowLocalMagicLoginFallback(): boolean {
  if (typeof window === "undefined") return false;
  return ["localhost", "127.0.0.1", "0.0.0.0"].includes(window.location.hostname);
}

export async function requestServerMagicLogin({
  contact,
  portal
}: {
  contact: string;
  portal: LoginPortal;
}): Promise<ServerMagicLoginResponse> {
  const apiBaseUrl = resolveMagicLoginApiBaseUrl();
  if (!apiBaseUrl) throw new Error("Wallet API is unavailable.");
  const walletConfig = readWalletApiConfig();
  const response = await fetch(new URL("/auth/magic-link/request", apiBaseUrl), {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      actor_did: walletConfig?.actorDid ?? "",
      base_url: typeof window !== "undefined" ? window.location.origin + window.location.pathname : "",
      contact,
      portal,
      wallet_api_base_url: walletConfig?.apiBaseUrl ?? readWalletApiBaseUrl() ?? "",
      wallet_id: walletConfig?.walletId ?? ""
    })
  });
  const payload = (await response.json().catch(() => ({}))) as ServerMagicLoginResponse & { detail?: unknown; status?: string };
  if (!response.ok || payload.status !== "sent") {
    throw new Error(typeof payload.detail === "string" ? payload.detail : `Magic link request failed (${response.status}).`);
  }
  return payload;
}

export async function verifyServerMagicLogin(token: string): Promise<LoginAuthResult> {
  const apiBaseUrl = resolveMagicLoginApiBaseUrl();
  if (!apiBaseUrl) throw new Error("Wallet API is unavailable.");
  const response = await fetch(new URL("/auth/magic-link/verify", apiBaseUrl), {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ token })
  });
  const payload = (await response.json().catch(() => ({}))) as ServerMagicLoginResponse & { detail?: unknown };
  if (!response.ok || !payload.valid || !payload.portal || !payload.contact) {
    throw new Error(typeof payload.detail === "string" ? payload.detail : "The magic link could not be verified.");
  }
  return {
    contact: payload.contact,
    portal: payload.portal,
    ucan: payload.ucan,
    walletConfig: normalizeServerWalletConfig(payload.wallet_config)
  };
}

// ─── Session helpers ──────────────────────────────────────────────────────────

export function readSignedInUser(): string {
  if (typeof window === "undefined") return "";
  const urlActorDid = readUrlWalletApiConfig()?.actorDid;
  if (urlActorDid) return urlActorDid;
  try {
    const raw = window.localStorage.getItem(APP_SESSION_KEY);
    if (!raw) return "";
    const parsed = JSON.parse(raw);
    return typeof parsed?.username === "string" ? parsed.username : "";
  } catch {
    return "";
  }
}

export function createGeneratedWalletOwnerDid(seed?: string): string {
  const normalizedSeed = seed?.trim().toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
  return `did:key:${normalizedSeed ? `${normalizedSeed}-` : ""}${randomBase64Url(16)}`;
}

export function resolveWalletOwnerDid(signedInUser: string, walletConfig?: WalletApiConfig): string {
  if (walletConfig?.actorDid?.startsWith("did:")) return walletConfig.actorDid;
  if (signedInUser.startsWith("did:")) return signedInUser;
  if (signedInUser.startsWith("client:")) return createGeneratedWalletOwnerDid(signedInUser.slice("client:".length));
  if (signedInUser.startsWith("provider:")) return createGeneratedWalletOwnerDid(signedInUser.slice("provider:".length));
  return createGeneratedWalletOwnerDid(signedInUser);
}
