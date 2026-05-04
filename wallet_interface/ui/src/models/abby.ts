export type RouteId =
  | "home"
  | "register"
  | "check-in"
  | "contacts"
  | "sharing-rules"
  | "uploads"
  | "social-services"
  | "shelter"
  | "recipient-access"
  | "benefits-protection"
  | "analytics"
  | "proof-center"
  | "exports"
  | "security"
  | "audit";

export type CheckInChannel = "email" | "sms" | "web";

export type DisclosureRecipientType =
  | "emergency_contact"
  | "police_precinct"
  | "social_worker"
  | "shelter_staff"
  | "government_liaison"
  | "benefits_agency";

export type DisclosureDataScope =
  | "identity_minimum"
  | "profile"
  | "photo"
  | "current_location"
  | "uploaded_documents"
  | "missed_check_in"
  | "found_permanent_housing"
  | "medical_notes"
  | "shelter_history"
  | "benefits_information"
  | "custom";

export type EasyBotCheckStatus = "pending" | "passed" | "failed";

export interface RegistrationProfileDraft {
  legalName: string;
  preferredName: string;
  pronouns: string;
  dateOfBirth: string;
  photoAssetId: string;
  phone: string;
  email: string;
  currentLocation: string;
  shelterAffiliation: string;
  serviceNeeds: string[];
  preferredCheckInChannels: CheckInChannel[];
  easyBotCheckStatus: EasyBotCheckStatus;
  captchaToken: string;
}

export interface CheckInPolicyDraft {
  intervalDays: number;
  reminderChannels: CheckInChannel[];
  gracePeriodHours: number;
  escalationEnabled: boolean;
  lastCheckInAt: string;
}

export interface DisclosureRecipientDraft {
  id: string;
  type: DisclosureRecipientType;
  displayName: string;
  relationship: string;
  email: string;
  phone: string;
  agencyName: string;
  precinctName: string;
  verified: boolean;
  allowedScopes: DisclosureDataScope[];
}

export interface UploadItem {
  id: string;
  recordId?: string;
  fileName: string;
  machineSummary: string;
  category: string;
  sensitivity: "low" | "moderate" | "high" | "restricted";
  status: "stored" | "encrypting" | "failed";
  storageOk?: boolean;
  shared: boolean;
}

export interface ServiceMatch {
  id: string;
  name: string;
  category: string;
  distance: string;
  availability: string;
}

export interface AuditEvent {
  id: string;
  actor: string;
  action: string;
  timestamp: string;
  resource?: string;
  decision?: string;
  grantId?: string;
}

export interface AnalyticsStudy {
  id: string;
  title: string;
  purpose: string;
  fields: string[];
  minCohortSize: number;
  epsilonBudget: number;
  spentBudget: number;
  status: "available" | "consented" | "draft" | "approved" | "paused" | "retired" | string;
}

export interface WalletAccessRequest {
  id: string;
  requesterName: string;
  requesterDid: string;
  audienceDid: string;
  resourceLabel: string;
  abilities: string[];
  purpose: string;
  status: "pending" | "approved" | "rejected" | "revoked";
  createdAt: string;
  approvalRequired?: boolean;
  approvalId?: string;
  approvalStatus?: "pending" | "approved" | "rejected" | string;
  approvalThreshold?: number;
  approvalCount?: number;
  grantStatus?: "active" | "revoked";
}

export interface WalletGrantReceipt {
  id: string;
  grantId: string;
  audienceName: string;
  audienceDid: string;
  resources: string[];
  recordId?: string;
  resourceLabel: string;
  abilities: string[];
  purpose: string;
  caveats?: Record<string, unknown>;
  receiptHash: string;
  status: "active" | "revoked";
  createdAt: string;
  expiresAt?: string;
}

export interface DerivedArtifactView {
  id: string;
  sourceRecordIds: string[];
  artifactType: string;
  outputPolicy: string;
  encryptedPayloadRef: string;
  createdAt: string;
}

export interface DerivedAnalysisResultView {
  artifact: DerivedArtifactView;
  output: Record<string, unknown>;
}

export interface DecryptedRecordView {
  recordId: string;
  text: string;
  sizeBytes: number;
}

export interface ProofReceiptView {
  id: string;
  proofType: string;
  claim: string;
  verifier: string;
  proofSystem: string;
  verificationStatus: string;
  circuitId?: string;
  verifierDigest?: string;
  proofArtifactRef?: string;
  publicInputs: Record<string, string>;
  witnessLabel: string;
  simulated: boolean;
  createdAt: string;
}

export interface ExportBundleView {
  id: string;
  bundleId: string;
  bundleHash: string;
  audienceName: string;
  bundle?: Record<string, unknown>;
  recordCount: number;
  proofCount: number;
  storageOk: boolean;
  imported: boolean;
  createdAt: string;
}
