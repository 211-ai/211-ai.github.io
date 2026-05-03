import { ExportBundleView, WalletAccessRequest, WalletGrantReceipt } from "../models/abby";

interface AccessRequestApiRecord {
  request_id: string;
  requester_did: string;
  audience_did: string;
  resources: string[];
  abilities: string[];
  purpose: string;
  status: "pending" | "approved" | "rejected" | "revoked";
  created_at: string;
  approval_required?: boolean;
  approval_threshold?: number | null;
  approval_count?: number;
  grant_status?: "active" | "revoked" | null;
}

interface AccessRequestApiResponse {
  requests: AccessRequestApiRecord[];
}

interface GrantReceiptApiRecord {
  receipt_id: string;
  grant_id: string;
  audience_did: string;
  resources: string[];
  abilities: string[];
  purpose: string | null;
  receipt_hash: string;
  status: "active" | "revoked";
  created_at: string;
  expires_at?: string | null;
}

interface GrantReceiptApiResponse {
  receipts: GrantReceiptApiRecord[];
}

export interface ExportBundleApi {
  actor_did?: string;
  bundle_id?: string;
  bundle_hash?: string;
  created_at?: string;
  records?: Array<Record<string, unknown>>;
  proofs?: Array<Record<string, unknown>>;
  wallet?: {
    wallet_id?: string;
    owner_did?: string;
  };
  [key: string]: unknown;
}

export interface ExportBundleVerifyResponse {
  valid: boolean;
  bundle_id?: string;
  bundle_hash?: string;
  computed_hash: string;
}

export interface ExportBundleImportResponse {
  wallet_id: string;
  bundle_id?: string;
  bundle_hash?: string;
  record_count: number;
  version_count: number;
  proof_count: number;
  derived_artifact_count: number;
}

export interface ExportBundleStorageResponse {
  bundle_id?: string;
  bundle_hash?: string;
  wallet_id: string;
  ok: boolean;
  record_count: number;
  reports: Array<Record<string, unknown>>;
}

export interface ExportGrantResponse {
  grant_id: string;
  audience_did: string;
  resources: string[];
  abilities: string[];
  caveats?: Record<string, unknown>;
  status?: string;
  created_at?: string;
}

export interface ExportInvocationResponse {
  invocation_id: string;
  grant_id: string;
  actor_did: string;
  invocation_token: string;
  caveats?: Record<string, unknown>;
  created_at?: string;
}

export interface WalletApiConfig {
  apiBaseUrl: string;
  walletId: string;
  actorDid?: string;
  issuerKeyHex?: string;
  audienceKeyHex?: string;
}

export async function loadWalletAccessState(config: Pick<WalletApiConfig, "apiBaseUrl" | "walletId">): Promise<{
  accessRequests: WalletAccessRequest[];
  grantReceipts: WalletGrantReceipt[];
}> {
  const [accessRequests, grantReceipts] = await Promise.all([
    listAccessRequests(config),
    listGrantReceipts(config)
  ]);
  return { accessRequests, grantReceipts };
}

export async function listAccessRequests({
  apiBaseUrl,
  walletId,
  requesterDid,
  audienceDid,
  status = "all"
}: {
  apiBaseUrl: string;
  walletId: string;
  requesterDid?: string;
  audienceDid?: string;
  status?: "pending" | "approved" | "rejected" | "revoked" | "all";
}): Promise<WalletAccessRequest[]> {
  const url = new URL(`/wallets/${walletId}/access-requests`, normalizedBaseUrl(apiBaseUrl));
  url.searchParams.set("status", status);
  if (requesterDid) {
    url.searchParams.set("requester_did", requesterDid);
  }
  if (audienceDid) {
    url.searchParams.set("audience_did", audienceDid);
  }
  const data = await fetchJson<AccessRequestApiResponse>(url, "Access request");
  return data.requests.map(toAccessRequestView);
}

export async function approveAccessRequest(
  config: WalletApiConfig,
  requestId: string
): Promise<WalletAccessRequest> {
  const data = await postAccessRequestDecision(config, requestId, "approve", {
    actor_did: requiredActorDid(config),
    issuer_key_hex: config.issuerKeyHex,
    audience_key_hex: config.audienceKeyHex,
    issue_invocation: false
  });
  return toAccessRequestView(data);
}

export async function rejectAccessRequest(
  config: WalletApiConfig,
  requestId: string,
  reason = "Rejected in wallet UI"
): Promise<WalletAccessRequest> {
  const data = await postAccessRequestDecision(config, requestId, "reject", {
    actor_did: requiredActorDid(config),
    reason
  });
  return toAccessRequestView(data);
}

export async function revokeAccessRequest(
  config: WalletApiConfig,
  requestId: string,
  reason = "Revoked in wallet UI"
): Promise<WalletAccessRequest> {
  const data = await postAccessRequestDecision(config, requestId, "revoke", {
    actor_did: requiredActorDid(config),
    reason
  });
  return toAccessRequestView(data);
}

export async function listGrantReceipts({
  apiBaseUrl,
  walletId,
  audienceDid,
  status = "all"
}: {
  apiBaseUrl: string;
  walletId: string;
  audienceDid?: string;
  status?: "active" | "revoked" | "all";
}): Promise<WalletGrantReceipt[]> {
  const url = new URL(`/wallets/${walletId}/grant-receipts`, normalizedBaseUrl(apiBaseUrl));
  url.searchParams.set("status", status);
  if (audienceDid) {
    url.searchParams.set("audience_did", audienceDid);
  }
  const data = await fetchJson<GrantReceiptApiResponse>(url, "Grant receipt");
  return data.receipts.map(toGrantReceiptView);
}

export async function verifyExportBundle({
  apiBaseUrl,
  bundle
}: {
  apiBaseUrl: string;
  bundle: ExportBundleApi;
}): Promise<ExportBundleVerifyResponse> {
  const url = new URL("/exports/verify", normalizedBaseUrl(apiBaseUrl));
  return postJson<ExportBundleVerifyResponse>(url, "Export bundle verification", { bundle });
}

export async function importExportBundle({
  apiBaseUrl,
  bundle
}: {
  apiBaseUrl: string;
  bundle: ExportBundleApi;
}): Promise<ExportBundleImportResponse> {
  const url = new URL("/exports/import", normalizedBaseUrl(apiBaseUrl));
  return postJson<ExportBundleImportResponse>(url, "Export bundle import", { bundle });
}

export async function verifyExportBundleStorage({
  apiBaseUrl,
  bundle
}: {
  apiBaseUrl: string;
  bundle: ExportBundleApi;
}): Promise<ExportBundleStorageResponse> {
  const url = new URL("/exports/storage", normalizedBaseUrl(apiBaseUrl));
  return postJson<ExportBundleStorageResponse>(url, "Export bundle storage", { bundle });
}

export async function createExportGrant(
  config: WalletApiConfig,
  {
    audienceDid,
    recordIds,
    purpose = "user_export",
    expiresAt
  }: {
    audienceDid: string;
    recordIds: string[];
    purpose?: string;
    expiresAt?: string;
  }
): Promise<ExportGrantResponse> {
  const url = new URL(`/wallets/${config.walletId}/exports/grants`, normalizedBaseUrl(config.apiBaseUrl));
  return postJson<ExportGrantResponse>(url, "Export grant", {
    audience_did: audienceDid,
    audience_key_hex: config.audienceKeyHex,
    expires_at: expiresAt,
    issuer_did: requiredActorDid(config),
    issuer_key_hex: config.issuerKeyHex,
    purpose,
    record_ids: recordIds
  });
}

export async function issueExportInvocation(
  config: WalletApiConfig,
  {
    actorDid,
    grantId,
    recordIds,
    expiresAt
  }: {
    actorDid: string;
    grantId: string;
    recordIds?: string[];
    expiresAt?: string;
  }
): Promise<ExportInvocationResponse> {
  const url = new URL(`/wallets/${config.walletId}/exports/invocations`, normalizedBaseUrl(config.apiBaseUrl));
  return postJson<ExportInvocationResponse>(url, "Export invocation", {
    actor_did: actorDid,
    actor_key_hex: config.audienceKeyHex,
    expires_at: expiresAt,
    grant_id: grantId,
    record_ids: recordIds
  });
}

export async function createExportBundle(
  config: Pick<WalletApiConfig, "apiBaseUrl" | "walletId" | "audienceKeyHex">,
  {
    actorDid,
    grantId,
    invocationToken,
    recordIds,
    includeDerivedArtifacts = true,
    includeProofs = true
  }: {
    actorDid: string;
    grantId?: string;
    invocationToken?: string;
    recordIds?: string[];
    includeDerivedArtifacts?: boolean;
    includeProofs?: boolean;
  }
): Promise<ExportBundleApi> {
  const url = new URL(`/wallets/${config.walletId}/exports`, normalizedBaseUrl(config.apiBaseUrl));
  return postJson<ExportBundleApi>(url, "Export bundle", {
    actor_did: actorDid,
    actor_key_hex: config.audienceKeyHex,
    grant_id: grantId,
    include_derived_artifacts: includeDerivedArtifacts,
    include_proofs: includeProofs,
    invocation_token: invocationToken,
    record_ids: recordIds
  });
}

export async function createVerifiedExportBundleView(
  config: WalletApiConfig,
  {
    audienceDid,
    audienceName,
    recordIds,
    purpose = "user_export"
  }: {
    audienceDid: string;
    audienceName?: string;
    recordIds: string[];
    purpose?: string;
  }
): Promise<ExportBundleView> {
  const grant = await createExportGrant(config, { audienceDid, recordIds, purpose });
  const invocation = await issueExportInvocation(config, {
    actorDid: audienceDid,
    grantId: grant.grant_id,
    recordIds
  });
  const bundle = await createExportBundle(config, {
    actorDid: audienceDid,
    invocationToken: invocation.invocation_token,
    recordIds
  });
  return loadExportBundleView({
    apiBaseUrl: config.apiBaseUrl,
    audienceName: audienceName || labelFromDid(audienceDid),
    bundle
  });
}

export async function loadExportBundleView({
  apiBaseUrl,
  bundle,
  audienceName,
  imported = false
}: {
  apiBaseUrl: string;
  bundle: ExportBundleApi;
  audienceName?: string;
  imported?: boolean;
}): Promise<ExportBundleView> {
  const [verification, storage] = await Promise.all([
    verifyExportBundle({ apiBaseUrl, bundle }),
    verifyExportBundleStorage({ apiBaseUrl, bundle })
  ]);
  const bundleId = verification.bundle_id ?? bundle.bundle_id ?? "export-bundle";
  const bundleHash = verification.bundle_hash ?? bundle.bundle_hash ?? verification.computed_hash;
  return {
    id: bundleId,
    bundleId,
    bundleHash,
    audienceName: audienceName ?? labelFromDid(bundle.actor_did ?? bundle.wallet?.owner_did ?? "did:unknown:recipient"),
    recordCount: storage.record_count || bundle.records?.length || 0,
    proofCount: bundle.proofs?.length ?? 0,
    storageOk: verification.valid && storage.ok,
    imported,
    createdAt: formatTimestamp(bundle.created_at ?? new Date().toISOString())
  };
}

function toAccessRequestView(request: AccessRequestApiRecord): WalletAccessRequest {
  const grantStatus = request.status === "revoked" ? "revoked" : request.grant_status ?? undefined;
  return {
    id: request.request_id,
    requesterName: labelFromDid(request.requester_did),
    requesterDid: request.requester_did,
    audienceDid: request.audience_did,
    resourceLabel: labelFromResource(request.resources[0] ?? "wallet resource"),
    abilities: request.abilities,
    purpose: request.purpose,
    status: request.status === "revoked" ? "approved" : request.status,
    createdAt: formatTimestamp(request.created_at),
    approvalRequired: request.approval_required,
    approvalThreshold: request.approval_threshold ?? undefined,
    approvalCount: request.approval_count,
    grantStatus
  };
}

function toGrantReceiptView(receipt: GrantReceiptApiRecord): WalletGrantReceipt {
  return {
    id: receipt.receipt_id,
    grantId: receipt.grant_id,
    audienceName: labelFromDid(receipt.audience_did),
    audienceDid: receipt.audience_did,
    resourceLabel: labelFromResource(receipt.resources[0] ?? "wallet resource"),
    abilities: receipt.abilities,
    purpose: receipt.purpose ?? "Shared wallet access",
    receiptHash: receipt.receipt_hash,
    status: receipt.status,
    createdAt: formatTimestamp(receipt.created_at),
    expiresAt: receipt.expires_at ? formatTimestamp(receipt.expires_at) : undefined
  };
}

async function fetchJson<T>(url: URL, label: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`${label} request failed with status ${response.status}`);
  }
  return (await response.json()) as T;
}

async function postJson<T>(url: URL, label: string, body: unknown): Promise<T> {
  const response = await fetch(url, {
    body: JSON.stringify(body),
    headers: { "Content-Type": "application/json" },
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(`${label} request failed with status ${response.status}`);
  }
  return (await response.json()) as T;
}

async function postAccessRequestDecision(
  config: WalletApiConfig,
  requestId: string,
  action: "approve" | "reject" | "revoke",
  body: Record<string, unknown>
): Promise<AccessRequestApiRecord> {
  const url = new URL(
    `/wallets/${config.walletId}/access-requests/${requestId}/${action}`,
    normalizedBaseUrl(config.apiBaseUrl)
  );
  return postJson<AccessRequestApiRecord>(url, `Access request ${action}`, body);
}

function requiredActorDid(config: WalletApiConfig): string {
  if (!config.actorDid) {
    throw new Error("VITE_DEMO_ACTOR_DID is required for access-request mutations");
  }
  return config.actorDid;
}

function normalizedBaseUrl(apiBaseUrl: string): string {
  return apiBaseUrl.endsWith("/") ? apiBaseUrl : `${apiBaseUrl}/`;
}

function labelFromResource(resource: string): string {
  const parts = resource.split("/").filter(Boolean);
  const last = parts[parts.length - 1] ?? resource;
  return last.replace(/^rec-/, "Record ");
}

function labelFromDid(did: string): string {
  const last = did.split(":").pop() ?? did;
  return last
    .split(/[-_]/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function formatTimestamp(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit"
  });
}
