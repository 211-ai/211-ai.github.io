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

export type ContactMethodVerificationStatus = "missing" | "unverified" | "verified";

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
  preferredShelter: string;
  socialWorker: string;
  emergencyContactStarter: string;
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
  emailVerificationStatus?: ContactMethodVerificationStatus;
  phoneVerificationStatus?: ContactMethodVerificationStatus;
  allowedScopes: DisclosureDataScope[];
  sharingRuleCustomized?: boolean;
  emergencyDisclosureEnabled?: boolean;
  sharingReviewConfirmedAt?: string;
  revokedAt?: string;
  sharingHistory?: string[];
}

export interface UploadItem {
  id: string;
  fileName: string;
  machineSummary: string;
  summaryStatus?: "generating" | "generated" | "fallback" | "failed";
  category: string;
  sensitivity: "low" | "moderate" | "high" | "restricted";
  status: "stored" | "encrypting" | "failed";
  sharingEligible: boolean;
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
}

export interface AnalyticsStudy {
  id: string;
  title: string;
  purpose: string;
  fields: string[];
  minCohortSize: number;
  epsilonBudget: number;
  spentBudget: number;
  status: "available" | "consented" | "paused";
}

export interface WalletAccessRequest {
  id: string;
  requesterName: string;
  requesterDid: string;
  audienceDid: string;
  resourceLabel: string;
  abilities: string[];
  purpose: string;
  status: "pending" | "approved" | "rejected";
  createdAt: string;
  expiresAt?: string;
  approvalRequired?: boolean;
  approvalThreshold?: number;
  approvalCount?: number;
  grantStatus?: "active" | "revoked";
}

export interface WalletGrantReceipt {
  id: string;
  grantId: string;
  audienceName: string;
  audienceDid: string;
  resourceLabel: string;
  abilities: string[];
  purpose: string;
  receiptHash: string;
  status: "active" | "revoked";
  createdAt: string;
  expiresAt?: string;
}

export interface ExportBundleView {
  id: string;
  bundleId: string;
  bundleHash: string;
  audienceName: string;
  recordCount: number;
  proofCount: number;
  storageOk: boolean;
  imported: boolean;
  createdAt: string;
}
