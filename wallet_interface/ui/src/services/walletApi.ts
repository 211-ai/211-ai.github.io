import {
  AuditEvent,
  AnalyticsStudy,
  DecryptedRecordView,
  DerivedAnalysisResultView,
  DerivedArtifactView,
  ExportBundleView,
  ProofReceiptView,
  SavedService,
  ServiceInteractionEvent,
  ServicePlan,
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
  caveats?: Record<string, unknown>;
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
  metadata?: Record<string, unknown>;
}

interface WalletRecordsApiResponse {
  records: WalletRecordApiRecord[];
}

export interface DeleteWalletRecordResult {
  artifact_ids: string[];
  deleted: boolean;
  ipfs_cids: string[];
  metadata_deleted: boolean;
  proof_ids: string[];
  record_id: string;
  unpin_results: Array<{ cid: string; ok: boolean; error?: string }>;
  version_ids: string[];
  wallet_id: string;
}

interface SavedServicesApiResponse {
  saved_services: SavedService[];
}

interface ServicePlansApiResponse {
  plans: ServicePlan[];
}

interface ServiceInteractionsApiResponse {
  interactions: ServiceInteractionEvent[];
}

interface ServicePlanShareGrantApiResponse {
  grant_id: string;
  plan_id: string;
  interaction_id: string;
  grant: RecordGrantResponse;
  receipt?: GrantReceiptApiRecord;
  plan: ServicePlan;
  interaction: ServiceInteractionEvent;
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

export interface StorageReplicaStatusView {
  uri: string;
  storage_type: string;
  role: string;
  ok: boolean;
  size_bytes?: number | null;
  sha256?: string | null;
  error?: string | null;
  repaired?: boolean;
}

export interface RecordStorageReportView {
  wallet_id: string;
  record_id: string;
  version_id: string;
  payload: StorageReplicaStatusView[];
  metadata: StorageReplicaStatusView[];
  ok: boolean;
  repaired?: boolean;
  created_at: string;
}

export interface WalletStorageReportView {
  wallet_id: string;
  record_count: number;
  reports: RecordStorageReportView[];
  ok: boolean;
  replica_count: number;
  failed_replica_count: number;
  repaired?: boolean;
  repaired_replica_count?: number;
  storage_types: Record<string, number>;
  created_at: string;
}

interface WalletSnapshotListApiResponse {
  wallet_ids: string[];
}

interface WalletSnapshotMutationApiResponse {
  wallet_id: string;
  path?: string;
  loaded?: boolean;
}

interface AnalyticsTemplateApiRecord {
  template_id: string;
  title: string;
  purpose: string;
  allowed_record_types: string[];
  allowed_derived_fields: string[];
  aggregation_policy: Record<string, unknown>;
  created_by: string;
  status: string;
  expires_at?: string | null;
}

interface AnalyticsTemplatesApiResponse {
  templates: AnalyticsTemplateApiRecord[];
}

interface AnalyticsConsentApiRecord {
  consent_id: string;
  wallet_id: string;
  template_id: string;
  allowed_record_types: string[];
  allowed_derived_fields: string[];
  aggregation_policy: Record<string, unknown>;
  created_at: string;
  expires_at?: string | null;
  revoked_at?: string | null;
  status: "active" | "revoked" | string;
}

interface AnalyticsConsentsApiResponse {
  consents: AnalyticsConsentApiRecord[];
}

export interface WalletGovernancePolicy {
  approver_dids?: string[];
  threshold?: number;
  sensitive_abilities?: string[];
  sensitive_operations?: string[];
  recovery_policy?: WalletRecoveryPolicy;
  [key: string]: unknown;
}

export interface WalletRecoveryPolicy {
  contact_dids: string[];
  threshold: number;
  status: "active" | "disabled" | string;
  updated_at?: string;
}

export interface WalletDetails {
  wallet_id: string;
  owner_did: string;
  controller_dids: string[];
  device_dids: string[];
  governance_policy: WalletGovernancePolicy;
  manifest_head?: string | null;
  updated_at?: string;
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

export interface WalletAnalyticsConsent {
  id: string;
  templateId: string;
  fields: string[];
  status: "active" | "revoked" | string;
  createdAt: string;
  expiresAt?: string;
  expiresAtRaw?: string;
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

interface DerivedAnalysisResultApiResponse {
  artifact: DerivedArtifactApiResponse;
  output: Record<string, unknown>;
}

interface DecryptedRecordApiResponse {
  base64?: string;
  record_id?: string;
  text: string;
  size_bytes: number;
}

interface RecordInvocationApiResponse {
  token: string;
  invocation: {
    invocation_id: string;
    grant_id: string;
    audience_did: string;
    resource: string;
    ability: string;
  };
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
  hash_valid?: boolean;
  schema_valid?: boolean;
  schema_error?: string;
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

export interface DelegatedGrantResponse {
  grant_id: string;
  issuer_did: string;
  audience_did: string;
  resources: string[];
  abilities: string[];
  caveats?: Record<string, unknown>;
  proof_chain?: string[];
  status?: string;
  created_at?: string;
  expires_at?: string | null;
}

export interface RecordGrantResponse {
  grant_id: string;
  issuer_did: string;
  audience_did: string;
  resources: string[];
  abilities: string[];
  caveats?: Record<string, unknown>;
  status?: string;
  created_at?: string;
  expires_at?: string | null;
}

export interface ServicePlanShareGrantResponse {
  grantId: string;
  planId: string;
  interactionId: string;
  grant: RecordGrantResponse;
  receipt?: WalletGrantReceipt;
  plan: ServicePlan;
  interaction: ServiceInteractionEvent;
}

export interface ThresholdApprovalResponse {
  approval_id: string;
  wallet_id: string;
  operation: string;
  requested_by: string;
  resources: string[];
  abilities: string[];
  threshold: number;
  approver_dids?: string[];
  approvals?: Record<string, string>;
  status: string;
  created_at?: string;
  expires_at?: string | null;
  details?: Record<string, unknown>;
}

interface ThresholdApprovalListResponse {
  approvals: ThresholdApprovalResponse[];
}

export type WalletAdminOperation =
  | "wallet/controller_add"
  | "wallet/controller_remove"
  | "wallet/device_add"
  | "wallet/device_revoke"
  | "wallet/recovery_policy_set"
  | "wallet/controller_recover"
  | "wallet/emergency_revoke";

export interface OpsHealthCheck {
  name: string;
  status: "ok" | "warning" | "error" | string;
  summary: string;
  details: Record<string, unknown>;
}

export interface OpsHealthReport {
  status: "ok" | "warning" | "error" | string;
  generated_at: string;
  wallet_count: number;
  check_count: number;
  checks: OpsHealthCheck[];
}

export interface EmergencyRevokeReport {
  wallet_id: string;
  revoked_grant_ids: string[];
  revoked_grant_count: number;
  rotated_record_ids: string[];
  rotated_record_count: number;
  rotation_errors?: Record<string, string>;
  rotate_keys: boolean;
  reason?: string | null;
}

export interface WalletApiConfig {
  apiBaseUrl: string;
  walletId: string;
  actorDid?: string;
  issuerKeyHex?: string;
  audienceKeyHex?: string;
}

export async function createWallet({
  apiBaseUrl,
  approvalThreshold,
  controllerDids,
  ownerDid
}: {
  apiBaseUrl: string;
  ownerDid: string;
  controllerDids?: string[];
  approvalThreshold?: number;
}): Promise<WalletDetails> {
  const url = new URL("/wallets", normalizedBaseUrl(apiBaseUrl));
  return postJson<WalletDetails>(url, "Create wallet", {
    approval_threshold: approvalThreshold,
    controller_dids: controllerDids,
    owner_did: ownerDid
  });
}

export interface MissingPersonDeadDropDispatchResponse {
  wallet_id: string;
  status: string;
  to_email: string;
  subject: string;
  bundle_filename: string;
  message_id?: string;
}

export interface MissingPersonDeadDropConfig {
  wallet_id: string;
  actor_did: string;
  enabled: boolean;
  to_email: string;
  subject: string;
  body: string;
  bundle: Record<string, unknown>;
  bundle_filename: string;
  due_at: string;
  last_check_in_at: string;
  last_sent_at?: string;
  last_sent_for_check_in_at?: string;
  last_message_id?: string;
  last_error?: string;
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

export async function sendMissingPersonDeadDropEmail(
  config: WalletApiConfig,
  {
    toEmail,
    subject,
    body,
    bundle,
    bundleFileName
  }: {
    toEmail: string;
    subject: string;
    body: string;
    bundle: Record<string, unknown>;
    bundleFileName: string;
  }
): Promise<MissingPersonDeadDropDispatchResponse> {
  const url = new URL(`/wallets/${config.walletId}/dead-drops/missing-person`, normalizedBaseUrl(config.apiBaseUrl));
  return postJson<MissingPersonDeadDropDispatchResponse>(url, "Missing-person dead-drop email", {
    actor_did: requiredActorDid(config),
    to_email: toEmail,
    subject,
    body,
    bundle,
    bundle_filename: bundleFileName
  });
}

export async function saveMissingPersonDeadDrop(
  config: WalletApiConfig,
  {
    enabled,
    toEmail,
    subject,
    body,
    bundle,
    bundleFileName,
    dueAt,
    lastCheckInAt
  }: {
    enabled: boolean;
    toEmail: string;
    subject: string;
    body: string;
    bundle: Record<string, unknown>;
    bundleFileName: string;
    dueAt: string;
    lastCheckInAt: string;
  }
): Promise<MissingPersonDeadDropConfig> {
  const url = new URL(`/wallets/${config.walletId}/dead-drops/missing-person`, normalizedBaseUrl(config.apiBaseUrl));
  return putJson<MissingPersonDeadDropConfig>(url, "Missing-person dead-drop configuration", {
    actor_did: requiredActorDid(config),
    enabled,
    to_email: toEmail,
    subject,
    body,
    bundle,
    bundle_filename: bundleFileName,
    due_at: dueAt,
    last_check_in_at: lastCheckInAt
  });
}

export async function dispatchMissingPersonDeadDrop(config: WalletApiConfig): Promise<MissingPersonDeadDropDispatchResponse> {
  const url = new URL(`/wallets/${config.walletId}/dead-drops/missing-person/dispatch`, normalizedBaseUrl(config.apiBaseUrl));
  return postJson<MissingPersonDeadDropDispatchResponse>(url, "Missing-person dead-drop dispatch", {
    actor_did: requiredActorDid(config)
  });
}

export async function loadWalletDetails(
  config: Pick<WalletApiConfig, "apiBaseUrl" | "walletId">
): Promise<WalletDetails> {
  const url = new URL(`/wallets/${config.walletId}`, normalizedBaseUrl(config.apiBaseUrl));
  return fetchJson<WalletDetails>(url, "Wallet details");
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

export async function listAnalyticsTemplates({
  apiBaseUrl,
  includeInactive = true
}: Pick<WalletApiConfig, "apiBaseUrl"> & { includeInactive?: boolean }): Promise<AnalyticsStudy[]> {
  const url = new URL("/analytics/templates", normalizedBaseUrl(apiBaseUrl));
  if (includeInactive) {
    url.searchParams.set("include_inactive", "true");
  }
  const data = await fetchJson<AnalyticsTemplatesApiResponse>(url, "Analytics templates");
  return data.templates.map(toAnalyticsStudyView);
}

export async function listWalletAnalyticsConsents(
  config: Pick<WalletApiConfig, "apiBaseUrl" | "walletId">
): Promise<WalletAnalyticsConsent[]> {
  const url = new URL(`/wallets/${config.walletId}/analytics/consents`, normalizedBaseUrl(config.apiBaseUrl));
  const data = await fetchJson<AnalyticsConsentsApiResponse>(url, "Analytics consents");
  return data.consents.map(toWalletAnalyticsConsentView);
}

export async function createWalletAnalyticsConsent(
  config: WalletApiConfig,
  templateId: string,
  expiresAt?: string
): Promise<WalletAnalyticsConsent> {
  const url = new URL(
    `/wallets/${config.walletId}/analytics/consents/from-template`,
    normalizedBaseUrl(config.apiBaseUrl)
  );
  const consent = await postJson<AnalyticsConsentApiRecord>(url, "Analytics consent", {
    actor_did: requiredActorDid(config),
    expires_at: expiresAt || undefined,
    template_id: templateId
  });
  return toWalletAnalyticsConsentView(consent);
}

export async function revokeWalletAnalyticsConsent(
  config: WalletApiConfig,
  consentId: string
): Promise<WalletAnalyticsConsent> {
  const url = new URL(
    `/wallets/${config.walletId}/analytics/consents/${consentId}/revoke`,
    normalizedBaseUrl(config.apiBaseUrl)
  );
  const consent = await postJson<AnalyticsConsentApiRecord>(url, "Analytics consent revoke", {
    actor_did: requiredActorDid(config)
  });
  return toWalletAnalyticsConsentView(consent);
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

export async function createLocationDistanceProof(
  config: WalletApiConfig,
  {
    locationRecordId,
    targetId,
    targetLat,
    targetLon,
    maxDistanceKm,
    grantId
  }: {
    locationRecordId: string;
    targetId: string;
    targetLat: number;
    targetLon: number;
    maxDistanceKm: number;
    grantId?: string;
  }
): Promise<ProofReceiptView> {
  const url = new URL(
    `/wallets/${config.walletId}/locations/${locationRecordId}/distance-proofs`,
    normalizedBaseUrl(config.apiBaseUrl)
  );
  const proof = await postJson<ProofReceiptApiRecord>(url, "Location distance proof", {
    actor_did: requiredActorDid(config),
    grant_id: grantId || undefined,
    max_distance_km: maxDistanceKm,
    target_id: targetId,
    target_lat: targetLat,
    target_lon: targetLon
  });
  return toProofReceiptView(proof);
}

export async function createDocumentPrivacyProfileProof(
  config: WalletApiConfig,
  {
    recordId,
    publicInputs
  }: {
    recordId: string;
    publicInputs: Record<string, unknown>;
  }
): Promise<ProofReceiptView> {
  const url = new URL(
    `/wallets/${config.walletId}/records/${recordId}/document-profile-proofs`,
    normalizedBaseUrl(config.apiBaseUrl)
  );
  const proof = await postJson<ProofReceiptApiRecord>(url, "Document privacy profile proof", {
    actor_did: requiredActorDid(config),
    public_inputs: publicInputs
  });
  return toProofReceiptView(proof);
}

export async function listWalletSavedServices(
  config: Pick<WalletApiConfig, "apiBaseUrl" | "walletId">,
  status?: string
): Promise<SavedService[]> {
  const url = new URL(`/wallets/${config.walletId}/portal/saved-services`, normalizedBaseUrl(config.apiBaseUrl));
  if (status) url.searchParams.set("status", status);
  const data = await fetchJson<SavedServicesApiResponse>(url, "Saved services");
  return data.saved_services;
}

export async function saveWalletService(
  config: WalletApiConfig,
  input: {
    serviceDocId: string;
    sourceContentCid: string;
    sourcePageCid?: string;
    title?: string;
    providerName?: string;
    programName?: string;
    sourceUrl?: string;
    label?: string;
    reason?: string;
    priority?: string;
    status?: string;
    privateNotesRecordId?: string;
    metadata?: Record<string, unknown>;
  }
): Promise<SavedService> {
  const url = new URL(`/wallets/${config.walletId}/portal/saved-services`, normalizedBaseUrl(config.apiBaseUrl));
  return postJson<SavedService>(url, "Saved service", {
    actor_did: requiredActorDid(config),
    service_doc_id: input.serviceDocId,
    source_content_cid: input.sourceContentCid,
    source_page_cid: input.sourcePageCid || "",
    title: input.title || "",
    provider_name: input.providerName || "",
    program_name: input.programName || "",
    source_url: input.sourceUrl || "",
    label: input.label || "",
    reason: input.reason || "",
    priority: input.priority || "normal",
    status: input.status || "saved",
    private_notes_record_id: input.privateNotesRecordId || "",
    metadata: input.metadata || {}
  });
}

export async function listWalletServicePlans(
  config: Pick<WalletApiConfig, "apiBaseUrl" | "walletId">,
  filters: { serviceDocId?: string; status?: string } = {}
): Promise<ServicePlan[]> {
  const url = new URL(`/wallets/${config.walletId}/portal/plans`, normalizedBaseUrl(config.apiBaseUrl));
  if (filters.serviceDocId) url.searchParams.set("service_doc_id", filters.serviceDocId);
  if (filters.status) url.searchParams.set("status", filters.status);
  const data = await fetchJson<ServicePlansApiResponse>(url, "Service plans");
  return data.plans;
}

export async function createWalletServicePlan(
  config: WalletApiConfig,
  input: {
    serviceDocId: string;
    sourceContentCid?: string;
    sourcePageCid?: string;
    serviceTitle?: string;
    providerName?: string;
    goal?: string;
    steps?: string[];
    documentsNeeded?: string[];
    questionsToAsk?: string[];
    appointmentAt?: string;
    reminderAt?: string;
    travelTarget?: string;
    assignedWorkerRecipientId?: string;
    status?: string;
    relatedInteractionIds?: string[];
    privateNotesRecordId?: string;
  }
): Promise<ServicePlan> {
  const url = new URL(`/wallets/${config.walletId}/portal/plans`, normalizedBaseUrl(config.apiBaseUrl));
  return postJson<ServicePlan>(url, "Service plan", {
    actor_did: requiredActorDid(config),
    service_doc_id: input.serviceDocId,
    source_content_cid: input.sourceContentCid || "",
    source_page_cid: input.sourcePageCid || "",
    service_title: input.serviceTitle || "",
    provider_name: input.providerName || "",
    goal: input.goal || "",
    steps: input.steps || [],
    documents_needed: input.documentsNeeded || [],
    questions_to_ask: input.questionsToAsk || [],
    appointment_at: input.appointmentAt || "",
    reminder_at: input.reminderAt || "",
    travel_target: input.travelTarget || "",
    assigned_worker_recipient_id: input.assignedWorkerRecipientId || "",
    status: input.status || "active",
    related_interaction_ids: input.relatedInteractionIds || [],
    private_notes_record_id: input.privateNotesRecordId || ""
  });
}

export async function updateWalletServicePlan(
  config: WalletApiConfig,
  planId: string,
  input: {
    sourceContentCid?: string;
    sourcePageCid?: string;
    serviceTitle?: string;
    providerName?: string;
    goal?: string;
    steps?: string[];
    documentsNeeded?: string[];
    questionsToAsk?: string[];
    appointmentAt?: string;
    reminderAt?: string;
    travelTarget?: string;
    assignedWorkerRecipientId?: string;
    status?: string;
    relatedInteractionIds?: string[];
    privateNotesRecordId?: string;
  }
): Promise<ServicePlan> {
  const url = new URL(`/wallets/${config.walletId}/portal/plans/${planId}`, normalizedBaseUrl(config.apiBaseUrl));
  return patchJson<ServicePlan>(url, "Service plan update", {
    actor_did: requiredActorDid(config),
    source_content_cid: input.sourceContentCid,
    source_page_cid: input.sourcePageCid,
    service_title: input.serviceTitle,
    provider_name: input.providerName,
    goal: input.goal,
    steps: input.steps,
    documents_needed: input.documentsNeeded,
    questions_to_ask: input.questionsToAsk,
    appointment_at: input.appointmentAt,
    reminder_at: input.reminderAt,
    travel_target: input.travelTarget,
    assigned_worker_recipient_id: input.assignedWorkerRecipientId,
    status: input.status,
    related_interaction_ids: input.relatedInteractionIds,
    private_notes_record_id: input.privateNotesRecordId
  });
}

export async function createWalletServicePlanShareGrant(
  config: WalletApiConfig,
  planId: string,
  input: {
    audienceDid: string;
    scopes: string[];
    purpose?: string;
    workerRecipientId?: string;
    workerName?: string;
    expiresAt?: string;
    approvalId?: string;
    audienceKeyHex?: string;
    caveats?: Record<string, unknown>;
  }
): Promise<ServicePlanShareGrantResponse> {
  const url = new URL(
    `/wallets/${config.walletId}/portal/plans/${planId}/share-grants`,
    normalizedBaseUrl(config.apiBaseUrl)
  );
  const data = await postJson<ServicePlanShareGrantApiResponse>(url, "Service plan share grant", {
    actor_did: requiredActorDid(config),
    audience_did: input.audienceDid,
    audience_key_hex: input.audienceKeyHex || undefined,
    caveats: input.caveats || {},
    expires_at: input.expiresAt || undefined,
    issuer_key_hex: config.issuerKeyHex,
    approval_id: input.approvalId || undefined,
    purpose: input.purpose || "service_plan_collaboration",
    scopes: input.scopes,
    worker_name: input.workerName || "",
    worker_recipient_id: input.workerRecipientId || ""
  });
  return {
    grantId: data.grant_id,
    planId: data.plan_id,
    interactionId: data.interaction_id,
    grant: data.grant,
    receipt: data.receipt ? toGrantReceiptView(data.receipt) : undefined,
    plan: data.plan,
    interaction: data.interaction
  };
}

export async function listWalletServiceInteractions(
  config: Pick<WalletApiConfig, "apiBaseUrl" | "walletId">,
  filters: { serviceDocId?: string; interactionType?: string; status?: string } = {}
): Promise<ServiceInteractionEvent[]> {
  const url = new URL(`/wallets/${config.walletId}/portal/interactions`, normalizedBaseUrl(config.apiBaseUrl));
  if (filters.serviceDocId) url.searchParams.set("service_doc_id", filters.serviceDocId);
  if (filters.interactionType) url.searchParams.set("interaction_type", filters.interactionType);
  if (filters.status) url.searchParams.set("status", filters.status);
  const data = await fetchJson<ServiceInteractionsApiResponse>(url, "Service interactions");
  return data.interactions;
}

export async function createWalletServiceInteraction(
  config: WalletApiConfig,
  input: {
    serviceDocId: string;
    sourceContentCid?: string;
    sourcePageCid?: string;
    providerName?: string;
    programName?: string;
    interactionType: string;
    channel?: string;
    counterpartyName?: string;
    counterpartyContact?: string;
    timestamp?: string;
    status?: string;
    outcome?: string;
    notesRecordId?: string;
    nextAction?: string;
    nextFollowUpAt?: string;
    sourceActionUrl?: string;
    relatedGrantIds?: string[];
    relatedRecordIds?: string[];
    privacyLevel?: string;
    metadata?: Record<string, unknown>;
  }
): Promise<ServiceInteractionEvent> {
  const url = new URL(`/wallets/${config.walletId}/portal/interactions`, normalizedBaseUrl(config.apiBaseUrl));
  return postJson<ServiceInteractionEvent>(url, "Service interaction", {
    actor_did: requiredActorDid(config),
    service_doc_id: input.serviceDocId,
    source_content_cid: input.sourceContentCid || "",
    source_page_cid: input.sourcePageCid || "",
    provider_name: input.providerName || "",
    program_name: input.programName || "",
    interaction_type: input.interactionType,
    channel: input.channel || "",
    counterparty_name: input.counterpartyName || "",
    counterparty_contact: input.counterpartyContact || "",
    timestamp: input.timestamp || "",
    status: input.status || "",
    outcome: input.outcome || "",
    notes_record_id: input.notesRecordId || "",
    next_action: input.nextAction || "",
    next_follow_up_at: input.nextFollowUpAt || "",
    source_action_url: input.sourceActionUrl || "",
    related_grant_ids: input.relatedGrantIds || [],
    related_record_ids: input.relatedRecordIds || [],
    privacy_level: input.privacyLevel || "private",
    metadata: input.metadata || {}
  });
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

export async function updateWalletRecordMetadata(
  config: WalletApiConfig,
  recordId: string,
  metadata: Record<string, unknown>
): Promise<UploadItem> {
  const url = new URL(`/wallets/${config.walletId}/records/${recordId}/metadata`, normalizedBaseUrl(config.apiBaseUrl));
  const record = await patchJson<WalletRecordApiRecord>(url, "Wallet record metadata", {
    actor_did: requiredActorDid(config),
    metadata
  });
  return toUploadItemViewWithStorage(config, record);
}

export async function deleteWalletRecord(
  config: WalletApiConfig,
  recordId: string,
  { unpinIpfs = true }: { unpinIpfs?: boolean } = {}
): Promise<DeleteWalletRecordResult> {
  const url = new URL(`/wallets/${config.walletId}/records/${recordId}`, normalizedBaseUrl(config.apiBaseUrl));
  return deleteJson<DeleteWalletRecordResult>(url, "Wallet record delete", {
    actor_did: requiredActorDid(config),
    unpin_ipfs: unpinIpfs
  });
}

export async function verifyRecordStorage(
  config: Pick<WalletApiConfig, "apiBaseUrl" | "walletId">,
  recordId: string
): Promise<boolean> {
  const url = new URL(`/wallets/${config.walletId}/records/${recordId}/storage`, normalizedBaseUrl(config.apiBaseUrl));
  const report = await fetchJson<RecordStorageApiResponse>(url, "Record storage");
  return report.ok;
}

export async function verifyWalletStorage(
  config: Pick<WalletApiConfig, "apiBaseUrl" | "walletId">
): Promise<WalletStorageReportView> {
  const url = new URL(`/wallets/${config.walletId}/storage`, normalizedBaseUrl(config.apiBaseUrl));
  return fetchJson<WalletStorageReportView>(url, "Wallet storage");
}

export async function repairWalletStorage(config: WalletApiConfig): Promise<WalletStorageReportView> {
  const url = new URL(`/wallets/${config.walletId}/storage/repair`, normalizedBaseUrl(config.apiBaseUrl));
  return postJson<WalletStorageReportView>(url, "Wallet storage repair", {
    actor_did: requiredActorDid(config)
  });
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

export async function rotateRecordKey(config: WalletApiConfig, recordId: string): Promise<void> {
  const url = new URL(
    `/wallets/${config.walletId}/records/${recordId}/rotate-key`,
    normalizedBaseUrl(config.apiBaseUrl)
  );
  await postJson<Record<string, unknown>>(url, "Record key rotation", {
    actor_did: requiredActorDid(config),
    actor_key_hex: config.issuerKeyHex
  });
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

export async function loadOpsHealth(
  config: Pick<WalletApiConfig, "apiBaseUrl">,
  verifyStorage = false
): Promise<OpsHealthReport> {
  const url = new URL("/ops/health", normalizedBaseUrl(config.apiBaseUrl));
  if (verifyStorage) {
    url.searchParams.set("verify_storage", "true");
  }
  return fetchJson<OpsHealthReport>(url, "Ops health");
}

export async function analyzeRecordWithGrant(
  config: WalletApiConfig,
  {
    recordId,
    grantId,
    invocationToken,
    maxChars = 200
  }: {
    recordId: string;
    grantId: string;
    invocationToken?: string;
    maxChars?: number;
  }
): Promise<DerivedArtifactView> {
  const url = new URL(`/wallets/${config.walletId}/records/${recordId}/analyze`, normalizedBaseUrl(config.apiBaseUrl));
  const artifact = await postJson<DerivedArtifactApiResponse>(url, "Record analysis", {
    actor_did: requiredActorDid(config),
    actor_key_hex: config.audienceKeyHex,
    grant_id: grantId,
    invocation_token: invocationToken || undefined,
    max_chars: maxChars
  });
  return toDerivedArtifactView(artifact);
}

export async function issueRecordAnalysisInvocation(
  config: WalletApiConfig,
  {
    recordId,
    grantId,
    outputTypes,
    userPresent = false
  }: {
    recordId: string;
    grantId: string;
    outputTypes?: string[];
    userPresent?: boolean;
  }
): Promise<string> {
  const url = new URL(
    `/wallets/${config.walletId}/records/${recordId}/analysis-invocations`,
    normalizedBaseUrl(config.apiBaseUrl)
  );
  const response = await postJson<RecordInvocationApiResponse>(url, "Record analysis invocation", {
    actor_did: requiredActorDid(config),
    actor_key_hex: config.audienceKeyHex || config.issuerKeyHex,
    grant_id: grantId,
    output_types: outputTypes?.length ? outputTypes : undefined,
    user_present: userPresent
  });
  return response.token;
}

export async function analyzeRecordRedactedWithGrant(
  config: WalletApiConfig,
  {
    recordId,
    grantId,
    invocationToken,
    maxChars = 500
  }: {
    recordId: string;
    grantId?: string;
    invocationToken?: string;
    maxChars?: number;
  }
): Promise<DerivedAnalysisResultView> {
  const url = new URL(
    `/wallets/${config.walletId}/records/${recordId}/analyze/redacted`,
    normalizedBaseUrl(config.apiBaseUrl)
  );
  const result = await postJson<DerivedAnalysisResultApiResponse>(url, "Redacted record analysis", {
    actor_did: requiredActorDid(config),
    actor_key_hex: config.audienceKeyHex || config.issuerKeyHex,
    grant_id: grantId || undefined,
    invocation_token: invocationToken || undefined,
    max_chars: maxChars
  });
  return toDerivedAnalysisResultView(result);
}

export async function createRecordVectorProfileWithGrant(
  config: WalletApiConfig,
  {
    recordId,
    grantId,
    invocationToken,
    chunkSizeWords = 80
  }: {
    recordId: string;
    grantId?: string;
    invocationToken?: string;
    chunkSizeWords?: number;
  }
): Promise<DerivedAnalysisResultView> {
  const url = new URL(
    `/wallets/${config.walletId}/records/${recordId}/vector-profile`,
    normalizedBaseUrl(config.apiBaseUrl)
  );
  const result = await postJson<DerivedAnalysisResultApiResponse>(url, "Record vector profile", {
    actor_did: requiredActorDid(config),
    actor_key_hex: config.audienceKeyHex || config.issuerKeyHex,
    grant_id: grantId || undefined,
    invocation_token: invocationToken || undefined,
    chunk_size_words: chunkSizeWords
  });
  return toDerivedAnalysisResultView(result);
}

export async function extractRecordTextRedactedWithGrant(
  config: WalletApiConfig,
  {
    recordId,
    grantId,
    invocationToken,
    maxChars = 20_000,
    maxBytes = 200_000,
    useOcr = true
  }: {
    recordId: string;
    grantId?: string;
    invocationToken?: string;
    maxChars?: number;
    maxBytes?: number;
    useOcr?: boolean;
  }
): Promise<DerivedAnalysisResultView> {
  const url = new URL(
    `/wallets/${config.walletId}/records/${recordId}/extract-text/redacted`,
    normalizedBaseUrl(config.apiBaseUrl)
  );
  const result = await postJson<DerivedAnalysisResultApiResponse>(url, "Redacted text extraction", {
    actor_did: requiredActorDid(config),
    actor_key_hex: config.audienceKeyHex || config.issuerKeyHex,
    grant_id: grantId || undefined,
    invocation_token: invocationToken || undefined,
    max_chars: maxChars,
    max_bytes: maxBytes,
    use_ocr: useOcr
  });
  return toDerivedAnalysisResultView(result);
}

export async function analyzeRecordFormRedactedWithGrant(
  config: WalletApiConfig,
  {
    recordId,
    grantId,
    invocationToken,
    maxFields = 100,
    useOcr = false
  }: {
    recordId: string;
    grantId?: string;
    invocationToken?: string;
    maxFields?: number;
    useOcr?: boolean;
  }
): Promise<DerivedAnalysisResultView> {
  const url = new URL(
    `/wallets/${config.walletId}/records/${recordId}/forms/analyze/redacted`,
    normalizedBaseUrl(config.apiBaseUrl)
  );
  const result = await postJson<DerivedAnalysisResultApiResponse>(url, "Redacted form analysis", {
    actor_did: requiredActorDid(config),
    actor_key_hex: config.audienceKeyHex || config.issuerKeyHex,
    grant_id: grantId || undefined,
    invocation_token: invocationToken || undefined,
    max_fields: maxFields,
    use_ocr: useOcr
  });
  return toDerivedAnalysisResultView(result);
}

export async function createRedactedGraphRAG(
  config: WalletApiConfig,
  {
    recordIds,
    grantId,
    invocationToken,
    maxCharsPerRecord = 20_000,
    maxBytesPerRecord = 200_000,
    useOcr = true
  }: {
    recordIds: string[];
    grantId?: string;
    invocationToken?: string;
    maxCharsPerRecord?: number;
    maxBytesPerRecord?: number;
    useOcr?: boolean;
  }
): Promise<DerivedAnalysisResultView> {
  const url = new URL(
    `/wallets/${config.walletId}/records/graphrag/redacted`,
    normalizedBaseUrl(config.apiBaseUrl)
  );
  const result = await postJson<DerivedAnalysisResultApiResponse>(url, "Redacted GraphRAG", {
    actor_did: requiredActorDid(config),
    actor_key_hex: config.audienceKeyHex || config.issuerKeyHex,
    grant_id: grantId || undefined,
    invocation_token: invocationToken || undefined,
    record_ids: recordIds,
    max_chars_per_record: maxCharsPerRecord,
    max_bytes_per_record: maxBytesPerRecord,
    use_ocr: useOcr
  });
  return toDerivedAnalysisResultView(result);
}

export async function decryptRecordWithGrant(
  config: WalletApiConfig,
  {
    recordId,
    grantId,
    invocationToken
  }: {
    recordId: string;
    grantId?: string;
    invocationToken?: string;
  }
): Promise<DecryptedRecordView> {
  const url = new URL(`/wallets/${config.walletId}/records/${recordId}/decrypt`, normalizedBaseUrl(config.apiBaseUrl));
  const decrypted = await postJson<DecryptedRecordApiResponse>(url, "Record decrypt", {
    actor_did: requiredActorDid(config),
    actor_key_hex: config.audienceKeyHex || config.issuerKeyHex,
    grant_id: grantId || undefined,
    invocation_token: invocationToken || undefined
  });
  return {
    base64: decrypted.base64,
    recordId: decrypted.record_id ?? recordId,
    text: decrypted.text,
    sizeBytes: decrypted.size_bytes
  };
}

export async function issueRecordDecryptInvocation(
  config: WalletApiConfig,
  {
    recordId,
    grantId,
    userPresent = false
  }: {
    recordId: string;
    grantId: string;
    userPresent?: boolean;
  }
): Promise<string> {
  const url = new URL(
    `/wallets/${config.walletId}/records/${recordId}/decrypt-invocations`,
    normalizedBaseUrl(config.apiBaseUrl)
  );
  const response = await postJson<RecordInvocationApiResponse>(url, "Record decrypt invocation", {
    actor_did: requiredActorDid(config),
    actor_key_hex: config.audienceKeyHex || config.issuerKeyHex,
    grant_id: grantId,
    user_present: userPresent
  });
  return response.token;
}

export async function createRecordGrant(
  config: WalletApiConfig,
  {
    recordId,
    audienceDid,
    audienceKeyHex,
    abilities,
    purpose,
    expiresAt,
    approvalId,
    maxDelegationDepth,
    userPresenceRequired,
    outputTypes,
    caveats
  }: {
    recordId: string;
    audienceDid: string;
    audienceKeyHex?: string;
    abilities: string[];
    purpose?: string;
    expiresAt?: string;
    approvalId?: string;
    maxDelegationDepth?: number;
    userPresenceRequired?: boolean;
    outputTypes?: string[];
    caveats?: Record<string, unknown>;
  }
): Promise<RecordGrantResponse> {
  const url = new URL(`/wallets/${config.walletId}/records/${recordId}/grants`, normalizedBaseUrl(config.apiBaseUrl));
  return postJson<RecordGrantResponse>(url, "Record grant", {
    abilities,
    approval_id: approvalId || undefined,
    audience_did: audienceDid,
    audience_key_hex: audienceKeyHex || undefined,
    expires_at: expiresAt || undefined,
    issuer_did: requiredActorDid(config),
    issuer_key_hex: config.issuerKeyHex,
    max_delegation_depth: maxDelegationDepth,
    output_types: outputTypes?.length ? outputTypes : undefined,
    purpose: purpose || "service_matching",
    user_presence_required: userPresenceRequired || undefined,
    caveats: caveats || undefined
  });
}

export async function requestRecordGrantApproval(
  config: WalletApiConfig,
  {
    recordId,
    abilities,
    requestedBy = requiredActorDid(config),
    expiresAt
  }: {
    recordId: string;
    abilities: string[];
    requestedBy?: string;
    expiresAt?: string;
  }
): Promise<ThresholdApprovalResponse> {
  const url = new URL(`/wallets/${config.walletId}/approvals`, normalizedBaseUrl(config.apiBaseUrl));
  return postJson<ThresholdApprovalResponse>(url, "Record grant approval", {
    abilities,
    expires_at: expiresAt || undefined,
    operation: "grant/create",
    requested_by: requestedBy,
    resources: [`wallet://${config.walletId}/records/${recordId}`]
  });
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

export async function approveThresholdApproval(
  config: WalletApiConfig,
  approvalId: string
): Promise<ThresholdApprovalResponse> {
  const url = new URL(
    `/wallets/${config.walletId}/approvals/${approvalId}/approve`,
    normalizedBaseUrl(config.apiBaseUrl)
  );
  return postJson<ThresholdApprovalResponse>(url, "Threshold approval", {
    approver_did: requiredActorDid(config)
  });
}

export async function listThresholdApprovals(
  config: Pick<WalletApiConfig, "apiBaseUrl" | "walletId">,
  status = "all"
): Promise<ThresholdApprovalResponse[]> {
  const url = new URL(`/wallets/${config.walletId}/approvals`, normalizedBaseUrl(config.apiBaseUrl));
  url.searchParams.set("status", status);
  const data = await fetchJson<ThresholdApprovalListResponse>(url, "Threshold approvals");
  return data.approvals;
}

export async function requestWalletAdminApproval(
  config: WalletApiConfig,
  operation: WalletAdminOperation,
  requestedBy = requiredActorDid(config)
): Promise<ThresholdApprovalResponse> {
  const url = new URL(`/wallets/${config.walletId}/approvals`, normalizedBaseUrl(config.apiBaseUrl));
  return postJson<ThresholdApprovalResponse>(url, "Wallet admin approval", {
    abilities: ["wallet/admin"],
    operation,
    requested_by: requestedBy,
    resources: [`wallet://${config.walletId}`]
  });
}

export async function setWalletRecoveryPolicy(
  config: WalletApiConfig,
  {
    contactDids,
    threshold,
    approvalId
  }: {
    contactDids: string[];
    threshold: number;
    approvalId?: string;
  }
): Promise<WalletDetails> {
  const url = new URL(`/wallets/${config.walletId}/recovery-policy`, normalizedBaseUrl(config.apiBaseUrl));
  return postJson<WalletDetails>(url, "Wallet recovery policy", {
    actor_did: requiredActorDid(config),
    approval_id: approvalId || undefined,
    contact_dids: contactDids,
    threshold
  });
}

export async function recoverWalletController(
  config: WalletApiConfig,
  {
    actorDid,
    controllerDid,
    approvalId
  }: {
    actorDid: string;
    controllerDid: string;
    approvalId?: string;
  }
): Promise<WalletDetails> {
  const url = new URL(`/wallets/${config.walletId}/controllers/recover`, normalizedBaseUrl(config.apiBaseUrl));
  return postJson<WalletDetails>(url, "Wallet controller recovery", {
    actor_did: actorDid,
    approval_id: approvalId || undefined,
    controller_did: controllerDid
  });
}

export async function emergencyRevoke(
  config: WalletApiConfig,
  {
    approvalId,
    rotateKeys = true,
    reason
  }: {
    approvalId?: string;
    rotateKeys?: boolean;
    reason?: string;
  }
): Promise<EmergencyRevokeReport> {
  const url = new URL(`/wallets/${config.walletId}/emergency-revoke`, normalizedBaseUrl(config.apiBaseUrl));
  return postJson<EmergencyRevokeReport>(url, "Emergency revoke", {
    actor_did: requiredActorDid(config),
    actor_key_hex: config.issuerKeyHex,
    approval_id: approvalId || undefined,
    reason: reason || undefined,
    rotate_keys: rotateKeys
  });
}

export async function delegateGrant(
  config: WalletApiConfig,
  {
    parentGrantId,
    audienceDid,
    resources,
    abilities,
    purpose,
    expiresAt,
    audienceKeyHex
  }: {
    parentGrantId: string;
    audienceDid: string;
    resources: string[];
    abilities: string[];
    purpose?: string;
    expiresAt?: string;
    audienceKeyHex?: string;
  }
): Promise<DelegatedGrantResponse> {
  const url = new URL(
    `/wallets/${config.walletId}/grants/${parentGrantId}/delegate`,
    normalizedBaseUrl(config.apiBaseUrl)
  );
  return postJson<DelegatedGrantResponse>(url, "Grant delegation", {
    abilities,
    audience_did: audienceDid,
    audience_key_hex: audienceKeyHex || undefined,
    caveats: purpose ? { purpose } : {},
    expires_at: expiresAt || undefined,
    issuer_did: requiredActorDid(config),
    issuer_key_hex: config.audienceKeyHex || config.issuerKeyHex,
    resources
  });
}

export async function addWalletController(
  config: WalletApiConfig,
  controllerDid: string,
  approvalId?: string
): Promise<WalletDetails> {
  const url = new URL(`/wallets/${config.walletId}/controllers`, normalizedBaseUrl(config.apiBaseUrl));
  return postJson<WalletDetails>(url, "Wallet controller add", {
    actor_did: requiredActorDid(config),
    approval_id: approvalId || undefined,
    controller_did: controllerDid
  });
}

export async function removeWalletController(
  config: WalletApiConfig,
  controllerDid: string,
  approvalId?: string
): Promise<WalletDetails> {
  const url = new URL(`/wallets/${config.walletId}/controllers/remove`, normalizedBaseUrl(config.apiBaseUrl));
  return postJson<WalletDetails>(url, "Wallet controller remove", {
    actor_did: requiredActorDid(config),
    approval_id: approvalId || undefined,
    controller_did: controllerDid
  });
}

export async function addWalletDevice(
  config: WalletApiConfig,
  deviceDid: string,
  approvalId?: string
): Promise<WalletDetails> {
  const url = new URL(`/wallets/${config.walletId}/devices`, normalizedBaseUrl(config.apiBaseUrl));
  return postJson<WalletDetails>(url, "Wallet device add", {
    actor_did: requiredActorDid(config),
    approval_id: approvalId || undefined,
    device_did: deviceDid
  });
}

export async function revokeWalletDevice(
  config: WalletApiConfig,
  deviceDid: string,
  approvalId?: string
): Promise<WalletDetails> {
  const url = new URL(`/wallets/${config.walletId}/devices/revoke`, normalizedBaseUrl(config.apiBaseUrl));
  return postJson<WalletDetails>(url, "Wallet device revoke", {
    actor_did: requiredActorDid(config),
    approval_id: approvalId || undefined,
    device_did: deviceDid
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
  const hashOk = verification.hash_valid ?? verification.valid;
  const schemaOk = verification.schema_valid ?? verification.valid;
  return {
    id: bundleId,
    bundleId,
    bundleHash,
    audienceName: audienceName ?? labelFromDid(bundle.actor_did ?? bundle.wallet?.owner_did ?? "did:unknown:recipient"),
    bundle,
    recordCount: storage.record_count || bundle.records?.length || 0,
    proofCount: bundle.proofs?.length ?? 0,
    verificationOk: verification.valid,
    hashOk,
    schemaOk,
    schemaError: verification.schema_error,
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
    caveats: receipt.caveats,
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

function toDerivedAnalysisResultView(result: DerivedAnalysisResultApiResponse): DerivedAnalysisResultView {
  return {
    artifact: toDerivedArtifactView(result.artifact),
    output: result.output
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

function toAnalyticsStudyView(template: AnalyticsTemplateApiRecord): AnalyticsStudy {
  return {
    id: template.template_id,
    title: template.title,
    purpose: template.purpose,
    fields: template.allowed_derived_fields,
    minCohortSize: numberFromPolicy(template.aggregation_policy.min_cohort_size, 10),
    epsilonBudget: numberFromPolicy(template.aggregation_policy.epsilon_budget, 1),
    spentBudget: 0,
    status: template.status === "active" ? "approved" : template.status
  };
}

function toWalletAnalyticsConsentView(consent: AnalyticsConsentApiRecord): WalletAnalyticsConsent {
  return {
    id: consent.consent_id,
    templateId: consent.template_id,
    fields: consent.allowed_derived_fields,
    status: consent.status,
    createdAt: formatTimestamp(consent.created_at),
    expiresAt: consent.expires_at ? formatTimestamp(consent.expires_at) : undefined,
    expiresAtRaw: consent.expires_at ?? undefined
  };
}

function toUploadItemView(record: WalletRecordApiRecord): UploadItem {
  const metadata = isPlainRecord(record.metadata) ? record.metadata : {};
  return {
    id: record.record_id,
    recordId: record.record_id,
    createdAt: formatTimestamp(record.created_at),
    createdAtRaw: record.created_at,
    fileName: readMetadataString(metadata, "fileName") || readMetadataString(metadata, "filename") || labelFromResource(record.record_id),
    machineSummary:
      readMetadataString(metadata, "machineSummary") ||
      readMetadataString(metadata, "title") ||
      `${record.data_type} record stored ${formatTimestamp(record.created_at)}`,
    category: record.public_descriptor || record.data_type,
    sensitivity: record.sensitivity,
    status: record.status === "active" ? "stored" : "failed",
    shared: false,
    sharingMode: "private",
    allowedRecipientIds: [],
    decentralizedStorageStatus:
      readMetadataString(metadata, "decentralizedStorageStatus") as UploadItem["decentralizedStorageStatus"] || "ready",
    decentralizedStorageProvider:
      readMetadataString(metadata, "decentralizedStorageProvider") as UploadItem["decentralizedStorageProvider"] || "wallet-api",
    decentralizedStorageMessage: readMetadataString(metadata, "decentralizedStorageMessage"),
    decryptedClassification: readMetadataString(metadata, "decryptedClassification"),
    decryptedLabels: readMetadataStringArray(metadata, "decryptedLabels"),
    decryptedMimeType: readMetadataString(metadata, "decryptedMimeType"),
    encryptedMetadataCid: readMetadataString(metadata, "encryptedMetadataCid"),
    encryptedPayloadCid: readMetadataString(metadata, "encryptedPayloadCid"),
    filecoinDealId: readMetadataString(metadata, "filecoinDealId"),
    filecoinPieceCid: readMetadataString(metadata, "filecoinPieceCid"),
    filecoinPinRequestId: readMetadataString(metadata, "filecoinPinRequestId"),
    filecoinPinStatus: readMetadataString(metadata, "filecoinPinStatus") as UploadItem["filecoinPinStatus"],
    filecoinPinStatusUrl: readMetadataString(metadata, "filecoinPinStatusUrl"),
    ipfsCid: readMetadataString(metadata, "ipfsCid"),
    ipfsGatewayUrl: readMetadataString(metadata, "ipfsGatewayUrl"),
    ipfsRootCid: readMetadataString(metadata, "ipfsRootCid"),
    ipldLinks: readMetadataIpldLinks(metadata, "ipldLinks"),
    metadataCid: readMetadataString(metadata, "metadataCid"),
    metadataFilecoinPinRequestId: readMetadataString(metadata, "metadataFilecoinPinRequestId"),
    metadataFilecoinPinStatus: readMetadataString(metadata, "metadataFilecoinPinStatus") as UploadItem["metadataFilecoinPinStatus"],
    metadataFilecoinPinStatusUrl: readMetadataString(metadata, "metadataFilecoinPinStatusUrl"),
    metadataGatewayUrl: readMetadataString(metadata, "metadataGatewayUrl"),
    metadataIpldCid: readMetadataString(metadata, "metadataIpldCid"),
    metadataIpldLink: readMetadataIpldLink(metadata, "metadataIpldLink"),
    metadataStorageMessage: readMetadataString(metadata, "metadataStorageMessage"),
    privacyProfileArtifactIds: readMetadataStringArray(metadata, "privacyProfileArtifactIds"),
    privacyProfileClassification: readMetadataString(metadata, "privacyProfileClassification"),
    privacyProfileLabels: readMetadataStringArray(metadata, "privacyProfileLabels"),
    privacyProfileMessage: readMetadataString(metadata, "privacyProfileMessage"),
    privacyProfileMimeType: readMetadataString(metadata, "privacyProfileMimeType"),
    privacyProfileNeedsRefresh: Boolean(metadata.privacyProfileNeedsRefresh),
    privacyProfileProofId: readMetadataString(metadata, "privacyProfileProofId"),
    privacyProfilePublicInputs: readMetadataRecord(metadata, "privacyProfilePublicInputs"),
    privacyProfileSearchText: readMetadataString(metadata, "privacyProfileSearchText"),
    privacyProfileStatus: readMetadataString(metadata, "privacyProfileStatus") as UploadItem["privacyProfileStatus"],
    privacyProfileSummary: readMetadataString(metadata, "privacyProfileSummary"),
    privacyProfileVectorTerms: readMetadataStringArray(metadata, "privacyProfileVectorTerms")
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

function isPlainRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function readMetadataString(metadata: Record<string, unknown>, key: string): string | undefined {
  const value = metadata[key];
  return typeof value === "string" && value.trim() ? value : undefined;
}

function readMetadataStringArray(metadata: Record<string, unknown>, key: string): string[] | undefined {
  const value = metadata[key];
  if (!Array.isArray(value)) return undefined;
  const strings = value.filter((item): item is string => typeof item === "string" && item.trim().length > 0);
  return strings.length ? strings : undefined;
}

function readMetadataRecord(metadata: Record<string, unknown>, key: string): Record<string, unknown> | undefined {
  const value = metadata[key];
  return isPlainRecord(value) ? value : undefined;
}

function readMetadataIpldLinks(
  metadata: Record<string, unknown>,
  key: string
): Array<{ "/"?: string; cid?: string; mediaType?: string; name: string }> | undefined {
  const value = metadata[key];
  if (!Array.isArray(value)) return undefined;
  const links = value.flatMap((item) => {
    if (!isPlainRecord(item)) return [];
    const name = typeof item.name === "string" && item.name.trim() ? item.name : undefined;
    const slashCid = typeof item["/"] === "string" && item["/"].trim() ? item["/"] : undefined;
    const cid = typeof item.cid === "string" && item.cid.trim() ? item.cid : undefined;
    if (!name || !(slashCid || cid)) return [];
    return [{
      "/": slashCid,
      cid,
      mediaType: typeof item.mediaType === "string" && item.mediaType.trim() ? item.mediaType : undefined,
      name
    }];
  });
  return links.length ? links : undefined;
}

function readMetadataIpldLink(
  metadata: Record<string, unknown>,
  key: string
): { "/"?: string; cid?: string; mediaType?: string; name: string } | undefined {
  const value = metadata[key];
  if (!isPlainRecord(value)) return undefined;
  return readMetadataIpldLinks({ [key]: [value] }, key)?.[0];
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

async function putJson<T>(url: URL, label: string, body: unknown): Promise<T> {
  const response = await fetch(url, {
    body: JSON.stringify(body),
    headers: { "Content-Type": "application/json" },
    method: "PUT"
  });
  if (!response.ok) {
    throw new Error(`${label} request failed with status ${response.status}`);
  }
  return (await response.json()) as T;
}

async function patchJson<T>(url: URL, label: string, body: unknown): Promise<T> {
  const response = await fetch(url, {
    body: JSON.stringify(body),
    headers: { "Content-Type": "application/json" },
    method: "PATCH"
  });
  if (!response.ok) {
    throw new Error(`${label} request failed with status ${response.status}`);
  }
  return (await response.json()) as T;
}

async function deleteJson<T>(url: URL, label: string, body: unknown): Promise<T> {
  const response = await fetch(url, {
    body: JSON.stringify(body),
    headers: { "Content-Type": "application/json" },
    method: "DELETE"
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
    throw new Error("VITE_DEMO_ACTOR_DID is required for wallet mutations");
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

function numberFromPolicy(value: unknown, fallback: number): number {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string") {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }
  return fallback;
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
