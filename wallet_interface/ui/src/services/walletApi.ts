import {
  AuditEvent,
  DerivedArtifactView,
  ExportBundleView,
  ProofReceiptView,
  UploadItem,
  WalletAccessRequest,
  WalletGrantReceipt
} from "../models/abby";

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
  approval_id?: string | null;
  approval_status?: string | null;
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

interface AuditEventApiRecord {
  event_id?: string;
  created_at: string;
  actor_did: string;
  action: string;
  resource: string;
  decision: string;
  grant_id?: string | null;
}

interface AuditEventApiResponse {
  events: AuditEventApiRecord[];
}

interface WalletRecordApiRecord {
  record_id: string;
  data_type: string;
  sensitivity: "low" | "moderate" | "high" | "restricted";
  public_descriptor: string;
  status: string;
  created_at: string;
}

interface WalletRecordsApiResponse {
  records: WalletRecordApiRecord[];
}

interface ProofReceiptApiRecord {
  proof_id: string;
  proof_type: string;
  statement?: Record<string, unknown>;
  verifier_id: string;
  public_inputs: Record<string, unknown>;
  proof_hash: string;
  witness_record_ids: string[];
  is_simulated: boolean;
  proof_system?: string;
  circuit_id?: string | null;
  verifier_digest?: string | null;
  proof_artifact_ref?: string | null;
  verification_status?: string;
  created_at: string;
}

interface ProofReceiptsApiResponse {
  proofs: ProofReceiptApiRecord[];
}

interface RecordStorageApiResponse {
  ok: boolean;
}

interface WalletSnapshotListApiResponse {
  wallet_ids: string[];
}

interface WalletSnapshotMutationApiResponse {
  wallet_id: string;
  path?: string;
  loaded?: boolean;
}

export interface WalletSnapshotVerification {
  wallet_id: string;
  path: string;
  exists: boolean;
  valid: boolean;
  format?: string;
  snapshot_hash?: string;
  computed_hash?: string;
  error?: string;
}

interface DerivedArtifactApiResponse {
  artifact_id: string;
  source_record_ids: string[];
  artifact_type: string;
  output_policy: string;
  encrypted_payload_ref?: {
    uri?: string;
    storage_type?: string;
    digest?: string;
  };
  created_at: string;
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

export async function listWalletAuditEvents(config: Pick<WalletApiConfig, "apiBaseUrl" | "walletId">): Promise<AuditEvent[]> {
  const url = new URL(`/wallets/${config.walletId}/audit`, normalizedBaseUrl(config.apiBaseUrl));
  const data = await fetchJson<AuditEventApiResponse>(url, "Wallet audit");
  return data.events.map(toAuditEventView);
}

export async function listWalletDocuments(config: Pick<WalletApiConfig, "apiBaseUrl" | "walletId">): Promise<UploadItem[]> {
  const url = new URL(`/wallets/${config.walletId}/records`, normalizedBaseUrl(config.apiBaseUrl));
  url.searchParams.set("data_type", "document");
  const data = await fetchJson<WalletRecordsApiResponse>(url, "Wallet records");
  return Promise.all(data.records.map((record) => toUploadItemViewWithStorage(config, record)));
}

export async function listWalletProofReceipts(
  config: Pick<WalletApiConfig, "apiBaseUrl" | "walletId">
): Promise<ProofReceiptView[]> {
  const url = new URL(`/wallets/${config.walletId}/proofs`, normalizedBaseUrl(config.apiBaseUrl));
  const data = await fetchJson<ProofReceiptsApiResponse>(url, "Proof receipts");
  return data.proofs.map(toProofReceiptView);
}

export async function createLocationRegionProof(
  config: WalletApiConfig,
  {
    locationRecordId,
    regionId,
    grantId
  }: {
    locationRecordId: string;
    regionId: string;
    grantId?: string;
  }
): Promise<ProofReceiptView> {
  const url = new URL(
    `/wallets/${config.walletId}/locations/${locationRecordId}/region-proofs`,
    normalizedBaseUrl(config.apiBaseUrl)
  );
  const proof = await postJson<ProofReceiptApiRecord>(url, "Location region proof", {
    actor_did: requiredActorDid(config),
    grant_id: grantId || undefined,
    region_id: regionId
  });
  return toProofReceiptView(proof);
}

export async function addTextDocument(
  config: WalletApiConfig,
  {
    filename,
    text,
    title
  }: {
    filename: string;
    text: string;
    title?: string;
  }
): Promise<UploadItem> {
  const url = new URL(`/wallets/${config.walletId}/documents/text`, normalizedBaseUrl(config.apiBaseUrl));
  const record = await postJson<WalletRecordApiRecord>(url, "Document upload", {
    actor_did: requiredActorDid(config),
    key_hex: config.issuerKeyHex,
    filename,
    title,
    text
  });
  return toUploadItemViewWithStorage(config, record);
}

export async function addBinaryDocument(
  config: WalletApiConfig,
  {
    file,
    title
  }: {
    file: File;
    title?: string;
  }
): Promise<UploadItem> {
  const url = new URL(`/wallets/${config.walletId}/documents`, normalizedBaseUrl(config.apiBaseUrl));
  const form = new FormData();
  form.set("actor_did", requiredActorDid(config));
  if (config.issuerKeyHex) {
    form.set("key_hex", config.issuerKeyHex);
  }
  if (title) {
    form.set("title", title);
  }
  form.set("file", file, file.name);
  const response = await fetch(url, {
    body: form,
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(`Document upload request failed with status ${response.status}`);
  }
  return toUploadItemViewWithStorage(config, (await response.json()) as WalletRecordApiRecord);
}

export async function verifyRecordStorage(
  config: Pick<WalletApiConfig, "apiBaseUrl" | "walletId">,
  recordId: string
): Promise<boolean> {
  const url = new URL(`/wallets/${config.walletId}/records/${recordId}/storage`, normalizedBaseUrl(config.apiBaseUrl));
  const report = await fetchJson<RecordStorageApiResponse>(url, "Record storage");
  return report.ok;
}

export async function repairRecordStorage(config: WalletApiConfig, recordId: string): Promise<boolean> {
  const url = new URL(
    `/wallets/${config.walletId}/records/${recordId}/storage/repair`,
    normalizedBaseUrl(config.apiBaseUrl)
  );
  const report = await postJson<RecordStorageApiResponse>(url, "Record storage repair", {
    actor_did: requiredActorDid(config)
  });
  return report.ok;
}

export async function listWalletSnapshots(config: Pick<WalletApiConfig, "apiBaseUrl">): Promise<string[]> {
  const url = new URL("/wallets/snapshots", normalizedBaseUrl(config.apiBaseUrl));
  const data = await fetchJson<WalletSnapshotListApiResponse>(url, "Wallet snapshots");
  return data.wallet_ids;
}

export async function saveWalletSnapshot(
  config: Pick<WalletApiConfig, "apiBaseUrl" | "walletId">
): Promise<WalletSnapshotMutationApiResponse> {
  const url = new URL(`/wallets/${config.walletId}/snapshot`, normalizedBaseUrl(config.apiBaseUrl));
  return postJson<WalletSnapshotMutationApiResponse>(url, "Wallet snapshot save", {});
}

export async function verifyWalletSnapshot(
  config: Pick<WalletApiConfig, "apiBaseUrl" | "walletId">
): Promise<WalletSnapshotVerification> {
  const url = new URL(`/wallets/${config.walletId}/snapshot`, normalizedBaseUrl(config.apiBaseUrl));
  return fetchJson<WalletSnapshotVerification>(url, "Wallet snapshot verification");
}

export async function loadWalletSnapshot(
  config: Pick<WalletApiConfig, "apiBaseUrl" | "walletId">
): Promise<WalletSnapshotMutationApiResponse> {
  const url = new URL(`/wallets/${config.walletId}/snapshot/load`, normalizedBaseUrl(config.apiBaseUrl));
  return postJson<WalletSnapshotMutationApiResponse>(url, "Wallet snapshot load", {});
}

export async function analyzeRecordWithGrant(
  config: WalletApiConfig,
  {
    recordId,
    grantId,
    maxChars = 200
  }: {
    recordId: string;
    grantId: string;
    maxChars?: number;
  }
): Promise<DerivedArtifactView> {
  const url = new URL(`/wallets/${config.walletId}/records/${recordId}/analyze`, normalizedBaseUrl(config.apiBaseUrl));
  const artifact = await postJson<DerivedArtifactApiResponse>(url, "Record analysis", {
    actor_did: requiredActorDid(config),
    actor_key_hex: config.audienceKeyHex,
    grant_id: grantId,
    max_chars: maxChars
  });
  return toDerivedArtifactView(artifact);
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

export async function approveThresholdApproval(config: WalletApiConfig, approvalId: string): Promise<void> {
  const url = new URL(
    `/wallets/${config.walletId}/approvals/${approvalId}/approve`,
    normalizedBaseUrl(config.apiBaseUrl)
  );
  await postJson<Record<string, unknown>>(url, "Threshold approval", {
    approver_did: requiredActorDid(config)
  });
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

export async function importExportBundleView({
  apiBaseUrl,
  bundleView
}: {
  apiBaseUrl: string;
  bundleView: ExportBundleView;
}): Promise<ExportBundleView> {
  if (!bundleView.bundle) {
    throw new Error("A complete export bundle is required for import");
  }
  await importExportBundle({ apiBaseUrl, bundle: bundleView.bundle });
  return { ...bundleView, imported: true };
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
    bundle,
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
    approvalId: request.approval_id ?? undefined,
    approvalStatus: request.approval_status ?? undefined,
    approvalThreshold: request.approval_threshold ?? undefined,
    approvalCount: request.approval_count,
    grantStatus
  };
}

function toGrantReceiptView(receipt: GrantReceiptApiRecord): WalletGrantReceipt {
  const resource = receipt.resources[0] ?? "wallet resource";
  return {
    id: receipt.receipt_id,
    grantId: receipt.grant_id,
    audienceName: labelFromDid(receipt.audience_did),
    audienceDid: receipt.audience_did,
    resources: receipt.resources,
    recordId: recordIdFromResource(resource),
    resourceLabel: labelFromResource(resource),
    abilities: receipt.abilities,
    purpose: receipt.purpose ?? "Shared wallet access",
    receiptHash: receipt.receipt_hash,
    status: receipt.status,
    createdAt: formatTimestamp(receipt.created_at),
    expiresAt: receipt.expires_at ? formatTimestamp(receipt.expires_at) : undefined
  };
}

function toDerivedArtifactView(artifact: DerivedArtifactApiResponse): DerivedArtifactView {
  return {
    id: artifact.artifact_id,
    sourceRecordIds: artifact.source_record_ids,
    artifactType: artifact.artifact_type,
    outputPolicy: artifact.output_policy,
    encryptedPayloadRef:
      artifact.encrypted_payload_ref?.uri ??
      artifact.encrypted_payload_ref?.digest ??
      artifact.encrypted_payload_ref?.storage_type ??
      "encrypted derived artifact",
    createdAt: formatTimestamp(artifact.created_at)
  };
}

function toProofReceiptView(proof: ProofReceiptApiRecord): ProofReceiptView {
  const claim = stringValue(proof.public_inputs.claim) || proof.proof_type;
  return {
    id: proof.proof_id,
    proofType: proof.proof_type,
    claim,
    verifier: proof.verifier_id,
    proofSystem: proof.proof_system ?? (proof.is_simulated ? "simulated" : "unknown"),
    verificationStatus: proof.verification_status ?? "unknown",
    circuitId: proof.circuit_id ?? undefined,
    verifierDigest: proof.verifier_digest ?? undefined,
    proofArtifactRef: proof.proof_artifact_ref ?? undefined,
    publicInputs: Object.fromEntries(
      Object.entries(proof.public_inputs).map(([key, value]) => [key, stringValue(value)])
    ),
    witnessLabel: proof.witness_record_ids.length
      ? proof.witness_record_ids.map(labelFromResource).join(", ")
      : "Wallet witness",
    simulated: proof.is_simulated,
    createdAt: formatTimestamp(proof.created_at)
  };
}

function toAuditEventView(event: AuditEventApiRecord): AuditEvent {
  return {
    id: event.event_id ?? `${event.action}-${event.created_at}`,
    actor: labelFromDid(event.actor_did),
    action: event.action,
    timestamp: formatTimestamp(event.created_at),
    resource: event.resource,
    decision: event.decision,
    grantId: event.grant_id ?? undefined
  };
}

function toUploadItemView(record: WalletRecordApiRecord): UploadItem {
  return {
    id: record.record_id,
    recordId: record.record_id,
    fileName: labelFromResource(record.record_id),
    machineSummary: `${record.data_type} record stored ${formatTimestamp(record.created_at)}`,
    category: record.public_descriptor || record.data_type,
    sensitivity: record.sensitivity,
    status: record.status === "active" ? "stored" : "failed",
    shared: false
  };
}

async function toUploadItemViewWithStorage(
  config: Pick<WalletApiConfig, "apiBaseUrl" | "walletId">,
  record: WalletRecordApiRecord
): Promise<UploadItem> {
  const item = toUploadItemView(record);
  try {
    return { ...item, storageOk: await verifyRecordStorage(config, record.record_id) };
  } catch {
    return { ...item, storageOk: false };
  }
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

function stringValue(value: unknown): string {
  if (value === null || value === undefined) {
    return "";
  }
  if (typeof value === "string") {
    return value;
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return JSON.stringify(value);
}

function labelFromResource(resource: string): string {
  const parts = resource.split("/").filter(Boolean);
  const last = parts[parts.length - 1] ?? resource;
  return last.replace(/^rec-/, "Record ");
}

function recordIdFromResource(resource: string): string | undefined {
  const parts = resource.split("/").filter(Boolean);
  const recordsIndex = parts.lastIndexOf("records");
  return recordsIndex >= 0 ? parts[recordsIndex + 1] : undefined;
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
