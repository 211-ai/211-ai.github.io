import type { UploadItem } from "../models/abby";
import { readRuntimeFilecoinStorageConfig } from "../lib/runtimeConfig";
import type { WalletApiConfig } from "./walletApi";

const FILECOIN_STORAGE_CONFIG_KEY = "abby-filecoin-storage-config";

type StoredFilecoinStorageConfig = {
  uploadUrl?: string;
  clientToken?: string;
};

export type FilecoinStorageClientConfig = {
  uploadUrl: string;
  clientToken?: string;
};

export type FilecoinUploadRequestMetadata = {
  actorDid?: string;
  allowedRecipientIds?: string[];
  fileName?: string;
  mimeType?: string;
  recordId?: string;
  sha256?: string;
  sharingMode?: UploadItem["sharingMode"];
  sizeBytes?: number;
  walletId?: string;
};

export type FilecoinUploadResponse = {
  cid?: string;
  dealId?: string;
  filecoinDealId?: string;
  filecoinPieceCid?: string;
  gatewayUrl?: string;
  ipfsCid?: string;
  message?: string;
  pieceCid?: string;
  provider?: UploadItem["decentralizedStorageProvider"] | string;
  requestId?: string;
  status?: string;
  url?: string;
};

export function getFilecoinStorageConfig(): FilecoinStorageClientConfig | undefined {
  const uploadUrl =
    readStoredFilecoinStorageConfig().uploadUrl ||
    readRuntimeFilecoinStorageConfig()?.uploadUrl ||
    readEnv("VITE_FILECOIN_STORAGE_UPLOAD_URL") ||
    readEnv("VITE_IPFS_FILECOIN_UPLOAD_URL");
  if (!uploadUrl) return undefined;
  return {
    uploadUrl,
    clientToken:
      readStoredFilecoinStorageConfig().clientToken ||
      readRuntimeFilecoinStorageConfig()?.clientToken ||
      readEnv("VITE_FILECOIN_STORAGE_CLIENT_TOKEN") ||
      readEnv("VITE_IPFS_FILECOIN_CLIENT_TOKEN")
  };
}

export function filecoinStorageConfigured(): boolean {
  return Boolean(getFilecoinStorageConfig()?.uploadUrl);
}

export async function uploadFileToFilecoinStorage(
  file: File,
  {
    allowedRecipientIds = [],
    clientConfig = getFilecoinStorageConfig(),
    upload,
    walletConfig
  }: {
    allowedRecipientIds?: string[];
    clientConfig?: FilecoinStorageClientConfig;
    upload: UploadItem;
    walletConfig?: WalletApiConfig;
  }
): Promise<FilecoinUploadResponse> {
  if (!clientConfig) throw new Error("Filecoin storage backend is not configured.");
  const metadata: FilecoinUploadRequestMetadata = {
    actorDid: walletConfig?.actorDid,
    allowedRecipientIds,
    fileName: file.name,
    mimeType: file.type || "application/octet-stream",
    recordId: upload.recordId,
    sha256: await sha256Hex(file),
    sharingMode: upload.sharingMode ?? "private",
    sizeBytes: file.size,
    walletId: walletConfig?.walletId
  };
  const form = new FormData();
  form.set("file", file, file.name);
  form.set("metadata", JSON.stringify(metadata));
  return postToFilecoinStorage(clientConfig, form);
}

export async function uploadWalletRecordToFilecoinStorage(
  upload: UploadItem,
  {
    allowedRecipientIds = upload.allowedRecipientIds ?? [],
    clientConfig = getFilecoinStorageConfig(),
    walletConfig
  }: {
    allowedRecipientIds?: string[];
    clientConfig?: FilecoinStorageClientConfig;
    walletConfig?: WalletApiConfig;
  }
): Promise<FilecoinUploadResponse> {
  if (!clientConfig) throw new Error("Filecoin storage backend is not configured.");
  if (!upload.recordId) throw new Error("A wallet record ID is required for backend Filecoin storage.");
  const body = JSON.stringify({
    actorDid: walletConfig?.actorDid,
    allowedRecipientIds,
    fileName: upload.fileName,
    recordId: upload.recordId,
    sharingMode: upload.sharingMode ?? "private",
    walletApiBaseUrl: walletConfig?.apiBaseUrl,
    walletId: walletConfig?.walletId
  });
  return postToFilecoinStorage(clientConfig, body, "application/json");
}

export async function uploadProofBundleToFilecoinStorage(
  bundlePayload: string,
  {
    clientConfig = getFilecoinStorageConfig(),
    walletConfig
  }: {
    clientConfig?: FilecoinStorageClientConfig;
    walletConfig?: WalletApiConfig;
  } = {}
): Promise<FilecoinUploadResponse> {
  if (!clientConfig) throw new Error("Filecoin storage backend is not configured.");
  const file = new File([bundlePayload], "wallet-proof-bundle.json", { type: "application/json" });
  const metadata: FilecoinUploadRequestMetadata = {
    actorDid: walletConfig?.actorDid,
    fileName: file.name,
    mimeType: file.type,
    sha256: await sha256Hex(file),
    sizeBytes: file.size,
    walletId: walletConfig?.walletId
  };
  const form = new FormData();
  form.set("file", file, file.name);
  form.set("metadata", JSON.stringify(metadata));
  return postToFilecoinStorage(clientConfig, form);
}

export function toFilecoinStoragePatch(result: FilecoinUploadResponse): Partial<UploadItem> {
  const ipfsCid = result.ipfsCid || result.cid;
  return {
    decentralizedStorageMessage: result.message || (ipfsCid ? "Stored on IPFS/Filecoin." : "Storage request completed."),
    decentralizedStorageProvider: normalizeStorageProvider(result.provider),
    decentralizedStorageStatus: "stored",
    filecoinDealId: result.filecoinDealId || result.dealId,
    filecoinPieceCid: result.filecoinPieceCid || result.pieceCid,
    ipfsCid
  };
}

function readStoredFilecoinStorageConfig(): StoredFilecoinStorageConfig {
  if (typeof window === "undefined") return {};
  try {
    const parsed = JSON.parse(window.localStorage.getItem(FILECOIN_STORAGE_CONFIG_KEY) || "{}");
    if (!parsed || typeof parsed !== "object") return {};
    return {
      clientToken: typeof parsed.clientToken === "string" ? parsed.clientToken : undefined,
      uploadUrl: typeof parsed.uploadUrl === "string" ? parsed.uploadUrl : undefined
    };
  } catch {
    return {};
  }
}

function readEnv(key: string): string | undefined {
  const value = (import.meta.env[key] as string | undefined)?.trim();
  return value || undefined;
}

async function postToFilecoinStorage(
  clientConfig: FilecoinStorageClientConfig,
  body: BodyInit,
  contentType?: string
): Promise<FilecoinUploadResponse> {
  const headers = new Headers();
  if (contentType) headers.set("content-type", contentType);
  if (clientConfig.clientToken) headers.set("authorization", `Bearer ${clientConfig.clientToken}`);
  const response = await fetch(clientConfig.uploadUrl, {
    body,
    headers,
    method: "POST"
  });
  const payload = await readJsonResponse(response);
  if (!response.ok) {
    const errorPayload = payload as { error?: string; message?: string };
    throw new Error(errorPayload.message || errorPayload.error || `Filecoin storage request failed with ${response.status}.`);
  }
  return payload as FilecoinUploadResponse;
}

async function readJsonResponse(response: Response): Promise<Record<string, string> | FilecoinUploadResponse> {
  const text = await response.text();
  if (!text) return {};
  try {
    return JSON.parse(text);
  } catch {
    return { message: text };
  }
}

async function sha256Hex(file: File): Promise<string> {
  const hash = await crypto.subtle.digest("SHA-256", await file.arrayBuffer());
  return Array.from(new Uint8Array(hash), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

function normalizeStorageProvider(provider: FilecoinUploadResponse["provider"]): UploadItem["decentralizedStorageProvider"] {
  if (provider === "ipfs" || provider === "filecoin" || provider === "wallet-api" || provider === "local") {
    return provider;
  }
  return "ipfs-filecoin";
}
