import { ChangeEvent, FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Archive,
  Bell,
  BarChart3,
  Camera,
  CalendarCheck,
  CalendarClock,
  ClipboardCheck,
  ContactRound,
  Download,
  FileUp,
  HeartHandshake,
  History,
  Home,
  KeyRound,
  Landmark,
  LockKeyhole,
  LogOut,
  Menu,
  Mic,
  MessageSquare,
  RefreshCw,
  Save,
  Search,
  Settings as SettingsIcon,
  ShieldCheck,
  Share2,
  Trash2,
  Upload,
  UsersRound,
  Wrench,
} from "lucide-react";
import QRCode from "qrcode";
import { ActionCard, Badge, Button, Field, Section, StatusBanner } from "../components/ui";
import { AgentChatDrawer, type AgentChatMode } from "../components/agent/AgentChatDrawer";
import { primeVoiceChatActivation } from "../components/agent/AgentAudioChatSurface";
import type { AppActionRuntime } from "./appActions";
import { useAgentChatService } from "../services/agentChatService";
import { ServiceDetailScreen } from "./ServiceDetailScreen";
import { InteractionsScreen } from "./InteractionsScreen";
import { CalendarScreen } from "./CalendarScreen";
import { getServicePlanDocIdFromHash, ServicePlanScreen, setLocationServicePlanHash } from "./ServicePlanScreen";
import { ServiceQuickActions } from "../components/services/ServiceQuickActions";
import { SavedServicesPanel } from "../components/services/SavedServicesPanel";
import { getServiceDetailDocIdFromHash, openCanonicalServiceDetailRoute } from "../agent/tools/serviceDetailTools";
import { getRouteLabel } from "../agent/surfaceRegistry";
import { search211Info } from "../services/graphRagService";
import {
  getPrimaryIntakeText,
  getServiceLocationLabel,
  load211GeneratedManifest,
  load211ServiceLocationsSlice,
  resolvePreferred211ServiceClusterIds,
  type SearchResult,
  type ServiceLocationRecord
} from "../lib/graphrag";
import {
  getFilecoinStorageConfig,
  normalizeIpfsGatewayUrl,
  pollFilecoinStorageStatus,
  sameOriginIpfsGatewayUrl,
  toFilecoinStoragePatch,
  uploadFileToFilecoinStorage,
  uploadProofBundleToFilecoinStorage,
  uploadRecoveryBundleToFilecoinStorage,
  uploadWalletRecordToFilecoinStorage
} from "../services/filecoinStorage";
import {
  buildWalletProofBundlePayload,
  buildWalletProofReviewUrl,
  readQrValue,
  readWalletProofBundlePayloadFromUrl,
  reviewWalletProofBundleReference,
  reviewWalletProofQrScreenshot,
  type WalletEncryptedRecordLink,
  type WalletProofQrReview
} from "../services/walletProofReview";
import {
  CheckInChannel,
  AuditEvent,
  CheckInPolicyDraft,
  DecryptedRecordView,
  DisclosureDataScope,
  DisclosureRecipientDraft,
  DisclosureRecipientType,
  EasyBotCheckStatus,
  ExportBundleView,
  RegistrationProfileDraft,
  RouteId,
  SavedService,
  ServiceInteractionEvent,
  ServicePlan,
  ShelterContactRequest,
  UploadItem,
  ProofReceiptView,
  WalletAccessRequest,
  WalletGrantReceipt
} from "../models/abby";
import {
  analyticsStudies,
  auditEvents,
  defaultDisclosureScopes,
  defaultCheckInPolicy,
  exportBundles,
  initialAccessRequests,
  initialGrantReceipts,
  initialRecipients,
  initialShelterContactRequests,
  initialUploads,
  proofReceipts,
  serviceMatches
} from "../services/mockAbbyService";
import {
  abilitiesForDisclosureScopes,
  capabilitySummary,
  nonGrantedCapabilities,
  plainCapabilityLabel,
  plainCapabilitySummary,
  plainNonGrantedCapabilities
} from "../services/capabilities";
import {
  analyzeRecordFormRedactedWithGrant,
  analyzeRecordRedactedWithGrant,
  analyzeRecordWithGrant,
  approveAccessRequest,
  approveThresholdApproval,
  createDocumentPrivacyProfileProof,
  createRecordVectorProfileWithGrant,
  createLocationRegionProof,
  createRedactedGraphRAG,
  createVerifiedExportBundleView,
  createWallet,
  addBinaryDocument,
  addTextDocument,
  deleteWalletRecord,
  dispatchMissingPersonDeadDrop,
  delegateGrant,
  decryptRecordWithGrant,
  extractRecordTextRedactedWithGrant,
  generateWalletRecordMetadata,
  importExportBundleView,
  issueRecordAnalysisInvocation,
  issueRecordDecryptInvocation,
  listWalletSnapshots,
  loadWalletAccessState,
  loadExportBundleView,
  loadWalletDetails,
  loadWalletSnapshot,
  listWalletAuditEvents,
  listWalletDocuments,
  listWalletProofReceipts,
  listWalletSavedServices,
  listWalletServiceInteractions,
  listWalletServicePlans,
  loadLatestWalletRecoveryBundle,
  loadWalletRecoveryBundleById,
  rejectAccessRequest,
  repairRecordStorage,
  revokeAccessRequest,
  saveWalletService,
  saveMissingPersonDeadDrop,
  saveWalletSnapshot,
  sendMissingPersonDeadDropEmail,
  storeWalletRecoveryBundle,
  updateWalletRecordMetadata,
  verifyWalletSnapshot,
  WalletMagicUcan,
  WalletSnapshotVerification,
  WalletApiConfig
} from "../services/walletApi";
import {
  createDefaultAppState,
  defaultManagedUserDraft,
  defaultShelterChecklist,
  getRouteFromHash,
  providerEligibilityCriteria,
  readPersistedAppState,
  setLocationRouteHash,
  shelterOptions,
  disclosureScopes,
  serviceNeeds,
  ShelterCasePriority,
  ShelterCaseRecord,
  ShelterCaseStatus,
  ShelterEligibilityCriterion,
  ShelterProviderMessage,
  ShelterStaffAccount,
  ShelterUserAccount,
  writePersistedAppState,
} from "./appState";
import {
  detectBrowserLocale,
  normalizeSiteLocale,
  readAssistantAutoTranslatePreference,
  readAssistantTranslationLocalePreference,
  readSiteLocalePreference,
  SUPPORTED_LOCALES,
  syncDocumentLocale,
  t,
  tFormat,
  TRANSLATION_LOCALE_OPTIONS,
  getLocaleOptionLabel,
  translateRouteLabel,
  translateServiceNeed,
  type SupportedLocale,
  writeAssistantAutoTranslatePreference,
  writeAssistantTranslationLocalePreference,
  writeSiteLocalePreference
} from "../lib/localization";
import { generateHuggingFaceWalletRouterText } from "../lib/huggingFaceWalletRouterClient";
import { generateOpenRouterText } from "../lib/openRouterClient";
import { NavigationGroup } from "./components/NavigationGroup";
import { StatusPanel } from "./components/StatusPanel";
import { AccountSafetySection } from "./components/AccountSafetySection";
import {
  clientNavigationRoutes,
  getProviderPortalView,
  normalizeAppRoute,
  type ProviderPortalView,
  providerNavigationRoutes,
  providerRouteIds,
  secondaryNavigationRoutes,
} from "./config/navigation";
import { WALLET_API_CONFIG_KEY, readUrlWalletApiConfig, readWalletApiBaseUrl, readWalletApiConfig } from "./services/walletConfig";
import { AnalyticsScreen } from "./screens/AnalyticsScreen";
import { BenefitsProtectionScreen } from "./screens/BenefitsProtectionScreen";
import { ExportCenterScreen } from "./screens/ExportCenterScreen";
import { ProofCenterScreen } from "./screens/ProofCenterScreen";
const APP_SESSION_KEY = "abby-ui-session-v1";
const ID_DOCUMENT_ACCEPT_ATTR = "image/jpeg,image/png,image/webp,application/pdf,.jpg,.jpeg,.png,.webp,.pdf";
const PROOF_QR_IMAGE_ACCEPT_ATTR = "image/jpeg,image/png,image/webp,.jpg,.jpeg,.png,.webp";
const ID_DOCUMENT_ACCEPTED_TYPES = new Set(["image/jpeg", "image/png", "image/webp", "application/pdf"]);
const ID_DOCUMENT_ACCEPTED_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp", ".pdf"];
const MAGIC_LOGIN_PARAM = "abbyLogin";
const MAGIC_LOGIN_TTL_MS = 10 * 60 * 1000;
const MAGIC_LOGIN_DEMO_SIGNING_CONTEXT = "abby-static-demo-login-v1";
const MAGIC_LOGIN_UCAN_KEY = "abby.magicLoginUcan.v1";
const WALLET_RECOVERY_BUNDLE_CACHE_PREFIX = "abby.walletRecoveryBundle.v1.";
const WALLET_DEVICE_RECOVERY_KEY_PREFIX = "abby.walletDeviceRecoveryKey.v1.";
const PORTLAND_POLICE_MISSING_EMAIL = "missing@police.portlandoregon.gov";
const DEFAULT_LOCAL_PRECINCT = "Local police precinct";
const LOCAL_PRECINCT_OPTIONS = [DEFAULT_LOCAL_PRECINCT];
const LOCAL_PRECINCT_RELATIONSHIP = "Local precinct";

type LoginPortal = "client" | "provider";

type MagicLoginPayload = {
  portal: LoginPortal;
  contact: string;
  issuedAt: number;
  expiresAt: number;
  salt: string;
  digest: string;
};

type LoginChallenge = MagicLoginPayload & {
  oneTimePad: string;
  magicLink: string;
};

type LoginAuthResult = {
  portal: LoginPortal;
  contact: string;
  walletConfig?: WalletApiConfig;
  ucan?: WalletMagicUcan;
};

type ServerMagicLoginResponse = {
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

function getInitialRouteFromHash(): RouteId {
  return getServicePlanDocIdFromHash() || getServiceDetailDocIdFromHash()
    ? "social-services"
    : normalizeAppRoute(getRouteFromHash());
}

function readSignedInUser(): string {
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

function createGeneratedWalletOwnerDid(seed?: string): string {
  const normalizedSeed = seed?.trim().toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
  return `did:key:${normalizedSeed ? `${normalizedSeed}-` : ""}${randomBase64Url(16)}`;
}

function resolveWalletOwnerDid(signedInUser: string, walletConfig?: WalletApiConfig): string {
  if (walletConfig?.actorDid?.startsWith("did:")) return walletConfig.actorDid;
  if (signedInUser.startsWith("did:")) return signedInUser;
  if (signedInUser.startsWith("client:")) return createGeneratedWalletOwnerDid(signedInUser.slice("client:".length));
  if (signedInUser.startsWith("provider:")) return createGeneratedWalletOwnerDid(signedInUser.slice("provider:".length));
  return createGeneratedWalletOwnerDid(signedInUser);
}

function isAcceptedIdentityDocument(file: File): boolean {
  const lowerName = file.name.toLowerCase();
  return (
    ID_DOCUMENT_ACCEPTED_TYPES.has(file.type) ||
    ID_DOCUMENT_ACCEPTED_EXTENSIONS.some((extension) => lowerName.endsWith(extension))
  );
}

function getIdentityDocumentFileDetail(file: File): string {
  const lowerName = file.name.toLowerCase();
  let fileType = "image";
  if (file.type === "application/pdf" || lowerName.endsWith(".pdf")) {
    fileType = "PDF";
  } else if (file.type === "image/jpeg" || lowerName.endsWith(".jpg") || lowerName.endsWith(".jpeg")) {
    fileType = "JPG";
  } else if (file.type === "image/png" || lowerName.endsWith(".png")) {
    fileType = "PNG";
  } else if (file.type === "image/webp" || lowerName.endsWith(".webp")) {
    fileType = "WebP";
  }
  return `${file.name} (${fileType})`;
}

function formatRecipientType(type: DisclosureRecipientType, locale: SupportedLocale): string {
  const labels: Record<DisclosureRecipientType, string> = {
    benefits_agency: t(locale, "contacts.recipientType.benefits_agency"),
    emergency_contact: t(locale, "contacts.recipientType.emergency_contact"),
    government_liaison: t(locale, "contacts.recipientType.government_liaison"),
    police_precinct: t(locale, "contacts.recipientType.police_precinct"),
    shelter_staff: t(locale, "contacts.recipientType.shelter_staff"),
    social_worker: t(locale, "contacts.recipientType.social_worker")
  };
  return labels[type];
}

function localizedPrecinctName(name: string, locale: SupportedLocale): string {
  return name === DEFAULT_LOCAL_PRECINCT ? t(locale, "contacts.defaultPrecinct") : name;
}

function localizedRelationshipName(name: string, locale: SupportedLocale): string {
  if (name === "Shelter") return t(locale, "contacts.shelterGroup");
  return name === LOCAL_PRECINCT_RELATIONSHIP ? t(locale, "contacts.localPrecinctRelationship") : name;
}

function formatContactRequestStatus(status: string, locale: SupportedLocale): string {
  if (status === "approved") return t(locale, "contacts.status.approved");
  if (status === "denied") return t(locale, "contacts.status.denied");
  if (status === "canceled") return t(locale, "contacts.status.canceled");
  return t(locale, "contacts.status.pending");
}

function disclosureScopeLabelKey(scope: DisclosureDataScope) {
  switch (scope) {
    case "identity_minimum":
      return "sharing.scope.identity_minimum.label" as const;
    case "profile":
      return "sharing.scope.profile.label" as const;
    case "photo":
      return "sharing.scope.photo.label" as const;
    case "current_location":
      return "sharing.scope.current_location.label" as const;
    case "uploaded_documents":
      return "sharing.scope.uploaded_documents.label" as const;
    case "missed_check_in":
      return "sharing.scope.missed_check_in.label" as const;
    case "found_permanent_housing":
      return "sharing.scope.found_permanent_housing.label" as const;
    case "medical_notes":
      return "sharing.scope.medical_notes.label" as const;
    case "shelter_history":
      return "sharing.scope.shelter_history.label" as const;
    case "benefits_information":
      return "sharing.scope.benefits_information.label" as const;
    case "custom":
      return "sharing.scope.custom.label" as const;
  }
}

function disclosureScopeDetailKey(scope: DisclosureDataScope) {
  switch (scope) {
    case "identity_minimum":
      return "sharing.scope.identity_minimum.detail" as const;
    case "profile":
      return "sharing.scope.profile.detail" as const;
    case "photo":
      return "sharing.scope.photo.detail" as const;
    case "current_location":
      return "sharing.scope.current_location.detail" as const;
    case "uploaded_documents":
      return "sharing.scope.uploaded_documents.detail" as const;
    case "missed_check_in":
      return "sharing.scope.missed_check_in.detail" as const;
    case "found_permanent_housing":
      return "sharing.scope.found_permanent_housing.detail" as const;
    case "medical_notes":
      return "sharing.scope.medical_notes.detail" as const;
    case "shelter_history":
      return "sharing.scope.shelter_history.detail" as const;
    case "benefits_information":
      return "sharing.scope.benefits_information.detail" as const;
    case "custom":
      return "sharing.scope.custom.detail" as const;
  }
}

function formatLocalizedCapability(ability: string, locale: SupportedLocale): string {
  const labels: Record<string, string> = {
    "analytics/contribute": t(locale, "sharing.capability.shareGroupFacts"),
    "analytics/query": t(locale, "sharing.capability.askGroupQuestions"),
    "derived/read": t(locale, "sharing.capability.readSafeFacts"),
    "export/create": t(locale, "sharing.capability.makeFullExport"),
    "grant/create": t(locale, "sharing.capability.shareAgain"),
    "location/read_coarse": t(locale, "sharing.capability.readGeneralLocation"),
    "location/read_precise": t(locale, "sharing.capability.readExactLocation"),
    "metadata/read": t(locale, "sharing.capability.readBasicInfo"),
    "proof/verify": t(locale, "sharing.capability.checkProof"),
    "record/analyze": t(locale, "sharing.capability.makeSafeSummary"),
    "record/decrypt": t(locale, "sharing.capability.openFileContents")
  };
  return labels[ability] ?? plainCapabilityLabel(ability);
}

function formatLocalizedCapabilitySummary(abilities: string[], locale: SupportedLocale): string {
  return abilities.map((ability) => formatLocalizedCapability(ability, locale)).join(", ");
}

function formatLocalizedNonGrantedCapabilities(abilities: string[], locale: SupportedLocale): string {
  return plainNonGrantedCapabilities(abilities)
    .map((ability) => {
      const labels: Record<string, string> = {
        "share group facts": t(locale, "sharing.capability.shareGroupFacts"),
        "ask group questions": t(locale, "sharing.capability.askGroupQuestions"),
        "read safe facts": t(locale, "sharing.capability.readSafeFacts"),
        "make a full wallet export": t(locale, "sharing.capability.makeFullExport"),
        "share again with someone else": t(locale, "sharing.capability.shareAgain"),
        "read general location": t(locale, "sharing.capability.readGeneralLocation"),
        "read exact location": t(locale, "sharing.capability.readExactLocation"),
        "read basic info": t(locale, "sharing.capability.readBasicInfo"),
        "check proof": t(locale, "sharing.capability.checkProof"),
        "make a safe summary": t(locale, "sharing.capability.makeSafeSummary"),
        "open file contents": t(locale, "sharing.capability.openFileContents")
      };
      return labels[ability] ?? ability;
    })
    .join(", ");
}

function formatAnalyticsField(field: string): string {
  const labels: Record<string, string> = {
    age_group: "age group",
    county: "county",
    housing_outcome: "housing outcome",
    need_category: "need type",
    service_type: "service type"
  };
  return labels[field] ?? field.replace(/_/g, " ");
}

function createEntityId(prefix: string): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return `${prefix}-${crypto.randomUUID()}`;
  }
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function isLocalPrecinctRecipient(recipient: DisclosureRecipientDraft, precinctName: string): boolean {
  return recipient.type === "police_precinct" && (recipient.precinctName === precinctName || recipient.displayName === precinctName);
}

const analyticsNeverPublishedText =
  "No names, contact details, exact locations, files, staff actions, case notes, or individual service histories";
const analyticsProviderPublicationFloor = 3;

function parseAnalyticsProofNumber(value: string | undefined): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function calculatePercent(value: number, total: number): number {
  if (!total) return 0;
  return Math.round((value / total) * 100);
}

function formatAnalyticsProofValue(value: string | undefined): string {
  if (!value) return "";
  const numeric = Number(value);
  if (Number.isFinite(numeric)) return numeric.toLocaleString();
  return value
    .split("_")
    .map((part) => `${part.charAt(0).toUpperCase()}${part.slice(1)}`)
    .join(" ");
}

function toShortSummaryTitle(text: string): string {
  const cleaned = text
    .replace(/machine\s+summary\s*:\s*/gi, " ")
    .replace(/[_-]+/g, " ")
    .replace(/[^a-zA-Z0-9\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  if (!cleaned) return "Uploaded document";

  const words = cleaned
    .split(" ")
    .filter((word) => word.length > 1)
    .slice(0, 4);
  if (!words.length) return "Uploaded document";

  const title = words
    .map((word) => `${word[0].toUpperCase()}${word.slice(1).toLowerCase()}`)
    .join(" ");
  return title;
}

function formatDeadDropFileTimestamp(date = new Date()): string {
  return date.toISOString().replace(/[:.]/g, "-");
}

function getMissingPersonDeadDropDueAt(policy: CheckInPolicyDraft): string {
  const lastCheckInAtMs = Date.parse(policy.lastCheckInAt);
  if (!Number.isFinite(lastCheckInAtMs)) return "";
  const intervalDays = Math.max(1, Math.round(policy.intervalDays || 1));
  const gracePeriodHours = Math.max(0, Math.round(policy.gracePeriodHours || 0));
  const dueAtMs = lastCheckInAtMs + intervalDays * 24 * 60 * 60 * 1000 + gracePeriodHours * 60 * 60 * 1000;
  return new Date(dueAtMs).toISOString();
}

function isMissingPersonDeadDropDue(policy: CheckInPolicyDraft): boolean {
  const dueAt = getMissingPersonDeadDropDueAt(policy);
  return Boolean(dueAt) && Date.now() >= Date.parse(dueAt);
}

function buildMissingPersonDeadDropBundle(
  profile: RegistrationProfileDraft,
  uploads: UploadItem[],
  recipients: DisclosureRecipientDraft[]
) {
  const preferredName = profile.preferredName.trim() || profile.legalName.trim() || "Unknown";
  const policeRecipients = recipients
    .filter((recipient) => recipient.type === "police_precinct")
    .map((recipient) => ({
      name: recipient.displayName,
      precinct: recipient.precinctName,
      email: recipient.email,
      phone: recipient.phone
    }));

  return {
    schemaVersion: "abby-missing-person-dead-drop-v1",
    generatedAt: new Date().toISOString(),
    policeNotificationTarget: PORTLAND_POLICE_MISSING_EMAIL,
    person: {
      preferredName,
      legalName: profile.legalName.trim(),
      dateOfBirth: profile.dateOfBirth,
      phone: profile.phone.trim(),
      email: profile.email.trim(),
      currentLocation: profile.currentLocation.trim(),
      shelterAffiliation: profile.shelterAffiliation.trim()
    },
    walletContents: uploads.map((upload) => ({
      id: upload.id,
      fileName: upload.fileName,
      machineSummary: upload.machineSummary,
      category: upload.category,
      sensitivity: upload.sensitivity,
      status: upload.status,
      shared: upload.shared,
      sharingMode: upload.sharingMode ?? "private",
      decentralizedStorageStatus: upload.decentralizedStorageStatus ?? "not_configured",
      decentralizedStorageProvider: upload.decentralizedStorageProvider ?? "local"
    })),
    knownPoliceRecipients: policeRecipients
  };
}

function buildMissingPersonDeadDropEmail(
  policy: CheckInPolicyDraft,
  profile: RegistrationProfileDraft,
  uploads: UploadItem[],
  recipients: DisclosureRecipientDraft[]
) {
  const bundle = buildMissingPersonDeadDropBundle(profile, uploads, recipients);
  const dueAt = getMissingPersonDeadDropDueAt(policy);
  const lastCheckInAt = Number.isFinite(Date.parse(policy.lastCheckInAt)) ? policy.lastCheckInAt : "";
  const timestampSource = dueAt || lastCheckInAt || new Date().toISOString();
  const fileName = `abby-missing-person-wallet-dead-drop-${formatDeadDropFileTimestamp(new Date(timestampSource))}.json`;
  const personLabel = bundle.person.preferredName || "Unknown";
  const walletLines = bundle.walletContents.length
    ? bundle.walletContents
        .map((item, index) => `${index + 1}. ${item.fileName} (${item.category}, ${item.sensitivity}, ${item.status})`)
        .join("\n")
    : "No wallet files are currently stored.";
  const body = [
    "Hello Portland Police Missing Persons Unit,",
    "",
    `Please use this Abby emergency dead-drop bundle to support a missing-person report for ${personLabel}.`,
    "",
    `Name: ${bundle.person.legalName || bundle.person.preferredName || "Unknown"}`,
    `Date of birth: ${bundle.person.dateOfBirth || "Unknown"}`,
    `Phone: ${bundle.person.phone || "Unknown"}`,
    `Email: ${bundle.person.email || "Unknown"}`,
    `Last known location: ${bundle.person.currentLocation || "Unknown"}`,
    "",
    `Wallet contents (${bundle.walletContents.length}):`,
    walletLines,
    "",
    `Dead-drop JSON bundle filename: ${fileName}`,
    "Please review the attached dead-drop JSON bundle for structured evidence metadata.",
    "",
    "Submitted from Abby missing-person safety setting."
  ].join("\n");
  return {
    toEmail: PORTLAND_POLICE_MISSING_EMAIL,
    subject: "Missing person report dead drop bundle",
    body,
    bundle,
    bundleFileName: fileName,
    dueAt,
    lastCheckInAt: policy.lastCheckInAt
  };
}

function buildMissingPersonDeadDropSyncPayload(
  enabled: boolean,
  policy: CheckInPolicyDraft,
  profile: RegistrationProfileDraft,
  uploads: UploadItem[],
  recipients: DisclosureRecipientDraft[]
) {
  return {
    enabled,
    ...buildMissingPersonDeadDropEmail(policy, profile, uploads, recipients)
  };
}

function normalizeLoginContact(value: string): string {
  const trimmed = value.trim();
  if (trimmed.includes("@")) return trimmed.toLowerCase();
  return trimmed.replace(/[^\d+]/g, "");
}

function isValidLoginContact(value: string): boolean {
  const normalized = normalizeLoginContact(value);
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalized) || normalized.replace(/\D/g, "").length >= 10;
}

function resolveMagicLoginApiBaseUrl(): string {
  const configured = (import.meta.env.VITE_MAGIC_LOGIN_API_BASE_URL as string | undefined)?.trim();
  if (configured) return configured;
  if (typeof window !== "undefined" && window.location.hostname === "211-ai.github.io") {
    return "https://211-ai.com";
  }
  return readWalletApiBaseUrl() ?? (typeof window !== "undefined" ? window.location.origin : "");
}

function normalizeServerWalletConfig(value: ServerMagicLoginResponse["wallet_config"]): WalletApiConfig | undefined {
  if (!value?.apiBaseUrl || !value.walletId) return undefined;
  return {
    actorDid: value.actorDid,
    apiBaseUrl: value.apiBaseUrl,
    walletId: value.walletId
  };
}

async function requestServerMagicLogin({
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

async function verifyServerMagicLogin(token: string): Promise<LoginAuthResult> {
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

function shouldAllowLocalMagicLoginFallback(): boolean {
  if (typeof window === "undefined") return false;
  return ["localhost", "127.0.0.1", "0.0.0.0"].includes(window.location.hostname);
}

function randomBase64Url(byteLength: number): string {
  const bytes = new Uint8Array(byteLength);
  crypto.getRandomValues(bytes);
  let binary = "";
  bytes.forEach((byte) => {
    binary += String.fromCharCode(byte);
  });
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

function randomHex(byteLength: number): string {
  const bytes = new Uint8Array(byteLength);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
}

function bytesToBase64Url(bytes: Uint8Array): string {
  let binary = "";
  bytes.forEach((byte) => {
    binary += String.fromCharCode(byte);
  });
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

function base64UrlToBytes(value: string): Uint8Array {
  const padded = value.replace(/-/g, "+").replace(/_/g, "/").padEnd(Math.ceil(value.length / 4) * 4, "=");
  const binary = atob(padded);
  return Uint8Array.from(binary, (char) => char.charCodeAt(0));
}

function bytesToArrayBuffer(bytes: Uint8Array): ArrayBuffer {
  return bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength) as ArrayBuffer;
}

async function deriveRecoveryPassphraseKey(passphrase: string, salt: Uint8Array, iterations: number): Promise<CryptoKey> {
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

async function sha256Base64Url(value: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
  return bytesToBase64Url(new Uint8Array(digest));
}

function walletDeviceRecoveryStorageKey(walletId: string): string {
  return `${WALLET_DEVICE_RECOVERY_KEY_PREFIX}${walletId}`;
}

function readWalletDeviceRecoveryRawKey(walletId: string): Uint8Array | undefined {
  if (typeof window === "undefined") return undefined;
  const stored = window.localStorage.getItem(walletDeviceRecoveryStorageKey(walletId));
  return stored ? base64UrlToBytes(stored) : undefined;
}

function storeWalletDeviceRecoveryRawKey(walletId: string, raw: Uint8Array): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(walletDeviceRecoveryStorageKey(walletId), bytesToBase64Url(raw));
}

async function getOrCreateWalletDeviceRecoveryRawKey(walletId: string): Promise<Uint8Array> {
  const stored = readWalletDeviceRecoveryRawKey(walletId);
  if (stored) return stored;
  const raw = new Uint8Array(32);
  crypto.getRandomValues(raw);
  storeWalletDeviceRecoveryRawKey(walletId, raw);
  return raw;
}

async function getOrCreateWalletDeviceRecoveryKey(walletId: string): Promise<CryptoKey> {
  const raw = await getOrCreateWalletDeviceRecoveryRawKey(walletId);
  return crypto.subtle.importKey("raw", bytesToArrayBuffer(raw), "AES-GCM", false, ["encrypt", "decrypt"]);
}

async function buildEncryptedRecoveryBundle({
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

async function buildPassphraseWrappedRecoveryBundle({
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

async function decryptPassphraseRecoveryBundle(
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

function readCachedRecoveryBundle(walletId: string): Record<string, unknown> | undefined {
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

function readMagicLoginUcan(): WalletMagicUcan | undefined {
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

type WalletRecoveryQrPayload = {
  apiBaseUrl?: string;
  bundleId: string;
  passphrase?: string;
  schema: "211-ai-wallet-recovery-qr-v1";
  serverCanDecrypt: false;
  containsRecoverySecret?: true;
  walletId: string;
  wrappingMethod?: string;
};

function buildWalletRecoveryQrPayload(
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

function parseWalletRecoveryQrPayload(value: string): WalletRecoveryQrPayload {
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

async function buildClientWrappedRecoveryBundle({
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

async function cacheEncryptedRecoveryBundleFromMagicLogin(walletConfig: WalletApiConfig, ucan: WalletMagicUcan): Promise<void> {
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

function randomOneTimePad(length = 6): string {
  const bytes = new Uint8Array(length);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (byte) => String(byte % 10)).join("");
}

function encodeMagicLoginPayload(payload: MagicLoginPayload): string {
  return btoa(JSON.stringify(payload)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

function decodeMagicLoginPayload(token: string): MagicLoginPayload | undefined {
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

async function createMagicLoginDigest({
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

async function generateUploadSummary(file: File): Promise<string> {
  try {
    if (file.type.startsWith("text/")) {
      return toShortSummaryTitle(await file.text());
    }

    if (file.type.startsWith("image/")) {
      const { recognize } = await import("tesseract.js");
      const result = await recognize(file, "eng");
      return toShortSummaryTitle(result.data.text || file.name);
    }
  } catch {
    // Fall through to a safe fallback summary when extraction/OCR fails.
  }

  const fileNameWithoutExtension = file.name.replace(/\.[^/.]+$/, "");
  return toShortSummaryTitle(fileNameWithoutExtension || "Uploaded document");
}

const hiddenProofCenterProofTypes = new Set(["location" + "_distance"]);

function visibleProofCenterProofs(proofs: ProofReceiptView[]) {
  return proofs.filter((proof) => !hiddenProofCenterProofTypes.has(proof.proofType));
}

function summarizeWalletProofClaims(proofs: ProofReceiptView[]) {
  const claims = proofs.map((proof) => proof.claim);
  if (claims.length <= 3) return claims.join(", ") || "Wallet proof summary";
  return `${claims.slice(0, 3).join(", ")}, +${claims.length - 3} more`;
}

export function App() {
  const persistedState = useMemo(() => readPersistedAppState(), []);
  const defaultAppState = useMemo(() => createDefaultAppState(persistedState), [persistedState]);
  const browserLocale = useMemo(() => detectBrowserLocale(), []);
  const [signedInUser, setSignedInUser] = useState(readSignedInUser);
  const activeRouteRef = useRef<RouteId>(getInitialRouteFromHash());
  const [activeRoute, setActiveRoute] = useState<RouteId>(activeRouteRef.current);
  const [servicePlanDocId, setServicePlanDocId] = useState<string | null>(getServicePlanDocIdFromHash());
  const [serviceDetailDocId, setServiceDetailDocId] = useState<string | null>(
    getServicePlanDocIdFromHash() ? null : getServiceDetailDocIdFromHash()
  );
  const [profile, setProfile] = useState<RegistrationProfileDraft>(() => defaultAppState.profile);
  const [policy, setPolicy] = useState(() => defaultAppState.policy);
  const [recipients, setRecipients] = useState<DisclosureRecipientDraft[]>(() => defaultAppState.recipients);
  const [uploads, setUploads] = useState<UploadItem[]>(() => defaultAppState.uploads);
  const [shelterContactRequests, setShelterContactRequests] = useState<ShelterContactRequest[]>(
    () => defaultAppState.shelterContactRequests
  );
  const [shelterStaffAccounts, setShelterStaffAccounts] = useState<ShelterStaffAccount[]>(
    () => defaultAppState.shelterStaffAccounts
  );
  const [shelterUserAccounts, setShelterUserAccounts] = useState<ShelterUserAccount[]>(
    () => defaultAppState.shelterUserAccounts
  );
  const [shelterCaseRecords, setShelterCaseRecords] = useState<ShelterCaseRecord[]>(
    () => defaultAppState.shelterCaseRecords
  );
  const [shelterProviderMessages, setShelterProviderMessages] = useState<ShelterProviderMessage[]>(
    () => defaultAppState.shelterProviderMessages
  );
  const [walletAuditEvents, setWalletAuditEvents] = useState<AuditEvent[]>(auditEvents);
  const [walletProofReceipts, setWalletProofReceipts] = useState<ProofReceiptView[]>(
    () => (defaultAppState.proofReceipts.length ? defaultAppState.proofReceipts : proofReceipts)
  );
  const [exportBundleViews, setExportBundleViews] = useState<ExportBundleView[]>(exportBundles);
  const [accessRequests, setAccessRequests] = useState<WalletAccessRequest[]>(initialAccessRequests);
  const [grantReceipts, setGrantReceipts] = useState<WalletGrantReceipt[]>(initialGrantReceipts);
  const [savedServices, setSavedServices] = useState<SavedService[]>(() => defaultAppState.savedServices);
  const [servicePlans, setServicePlans] = useState<ServicePlan[]>(() => defaultAppState.servicePlans);
  const [serviceInteractions, setServiceInteractions] = useState<ServiceInteractionEvent[]>(
    () => defaultAppState.serviceInteractions
  );
  const [siteLocale, setSiteLocale] = useState<SupportedLocale>(() => readSiteLocalePreference() ?? normalizeSiteLocale(browserLocale));
  const [assistantTranslationLocale, setAssistantTranslationLocale] = useState<string>(
    () => readAssistantTranslationLocalePreference() ?? browserLocale
  );
  const [assistantAutoTranslate, setAssistantAutoTranslate] = useState<boolean>(
    () => readAssistantAutoTranslatePreference() ?? !/^en\b/i.test(browserLocale)
  );
  const [walletPortalLoading, setWalletPortalLoading] = useState(false);
  const [walletPortalError, setWalletPortalError] = useState("");
  const [walletActorResolved, setWalletActorResolved] = useState(false);
  const [recipientVerified, setRecipientVerified] = useState(false);
  const [benefitsOptIn, setBenefitsOptIn] = useState(defaultAppState.benefitsOptIn);
  const [analyticsOptIn, setAnalyticsOptIn] = useState<Record<string, boolean>>(() => defaultAppState.analyticsOptIn);
  const [missingPersonDeadDropEnabled, setMissingPersonDeadDropEnabled] = useState(
    defaultAppState.missingPersonDeadDropEnabled
  );
  const [missingPersonDeadDropLastSentForCheckInAt, setMissingPersonDeadDropLastSentForCheckInAt] = useState(
    defaultAppState.missingPersonDeadDropLastSentForCheckInAt
  );
  const [shelterChecklist, setShelterChecklist] = useState(() => defaultAppState.shelterChecklist);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [agentChatOpen, setAgentChatOpen] = useState(false);
  const [agentChatMode, setAgentChatMode] = useState<AgentChatMode>("text");
  const [walletApiConfig, setWalletApiConfig] = useState<WalletApiConfig | undefined>(() => readWalletApiConfig());
  const lastSyncedDeadDropPayloadRef = useRef("");
  const walletApiBaseUrl = walletApiConfig?.apiBaseUrl ?? readWalletApiBaseUrl();
  const walletDeadDropReady = Boolean(walletApiConfig?.actorDid && walletActorResolved);
  const localizedClientNavigationRoutes = useMemo(
    () => clientNavigationRoutes.map((route) => ({ ...route, label: translateRouteLabel(siteLocale, route.id, route.label) })),
    [siteLocale]
  );
  const localizedProviderNavigationRoutes = useMemo(
    () => providerNavigationRoutes.map((route) => ({ ...route, label: translateRouteLabel(siteLocale, route.id, route.label) })),
    [siteLocale]
  );
  const localizedSecondaryNavigationRoutes = useMemo(
    () => secondaryNavigationRoutes.map((route) => ({ ...route, label: translateRouteLabel(siteLocale, route.id, route.label) })),
    [siteLocale]
  );

  const persistWalletApiConfig = useCallback((nextConfig: WalletApiConfig) => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(WALLET_API_CONFIG_KEY, JSON.stringify(nextConfig));
      const url = new URL(window.location.href);
      url.searchParams.set("walletApiBaseUrl", nextConfig.apiBaseUrl);
      url.searchParams.set("walletId", nextConfig.walletId);
      if (nextConfig.actorDid) {
        url.searchParams.set("actorDid", nextConfig.actorDid);
      } else {
        url.searchParams.delete("actorDid");
      }
      if (nextConfig.issuerKeyHex) {
        url.searchParams.set("issuerKeyHex", nextConfig.issuerKeyHex);
      } else {
        url.searchParams.delete("issuerKeyHex");
      }
      if (nextConfig.audienceKeyHex) {
        url.searchParams.set("audienceKeyHex", nextConfig.audienceKeyHex);
      } else {
        url.searchParams.delete("audienceKeyHex");
      }
      window.history.replaceState({}, "", url.toString());
    }
    setWalletApiConfig(nextConfig);
  }, []);

  function openAgentChatMode(mode: AgentChatMode) {
    if (mode === "audio") {
      primeVoiceChatActivation();
    }
    setAgentChatMode(mode);
    setAgentChatOpen(true);
  }

  function toggleAgentChatMode(mode: AgentChatMode) {
    const nextOpen = !(agentChatOpen && agentChatMode === mode);
    if (mode === "audio" && nextOpen) {
      primeVoiceChatActivation();
    }
    setAgentChatMode(mode);
    setAgentChatOpen(nextOpen);
  }

  async function refreshWalletAuditEvents() {
    if (!walletApiConfig) return;
    const events = await listWalletAuditEvents(walletApiConfig);
    setWalletAuditEvents(events);
  }

  async function refreshWalletDocuments() {
    if (!walletApiConfig) return;
    const documents = await listWalletDocuments(walletApiConfig);
    setUploads(documents);
  }

  async function refreshWalletProofReceipts() {
    if (!walletApiConfig) return;
    const proofs = await listWalletProofReceipts(walletApiConfig);
    setWalletProofReceipts(proofs);
  }

  async function refreshWalletPortalState() {
    if (!walletApiConfig) return;
    setWalletPortalLoading(true);
    setWalletPortalError("");
    try {
      const [nextSavedServices, nextServicePlans, nextServiceInteractions] = await Promise.all([
        listWalletSavedServices(walletApiConfig),
        listWalletServicePlans(walletApiConfig),
        listWalletServiceInteractions(walletApiConfig)
      ]);
      setSavedServices(nextSavedServices);
      setServicePlans(nextServicePlans);
      setServiceInteractions(nextServiceInteractions);
    } catch (error) {
      setWalletPortalError(error instanceof Error ? error.message : "Wallet portal state unavailable");
    } finally {
      setWalletPortalLoading(false);
    }
  }

  async function refreshWalletAfterSnapshotLoad() {
    if (!walletApiConfig) return;
    await Promise.all([
      refreshWalletAuditEvents().catch(() => setWalletAuditEvents(auditEvents)),
      refreshWalletDocuments().catch(() => setUploads(initialUploads)),
      refreshWalletProofReceipts().catch(() => setWalletProofReceipts(proofReceipts)),
      refreshWalletPortalState()
    ]);
  }

  async function refreshWalletAccessState() {
    if (!walletApiConfig) return;
    const state = await loadWalletAccessState(walletApiConfig);
    setAccessRequests(state.accessRequests.length ? state.accessRequests : initialAccessRequests);
    setGrantReceipts(state.grantReceipts.length ? state.grantReceipts : initialGrantReceipts);
  }

  const agentRuntime = useMemo<AppActionRuntime>(
    () => ({
      getState: () => ({
        activeRoute: activeRouteRef.current,
        profile,
        policy,
        recipients,
        shelterContactRequests,
        shelterStaffAccounts,
        shelterUserAccounts,
        shelterCaseRecords,
        shelterProviderMessages,
        uploads,
        accessRequests,
        grantReceipts,
        walletAuditEvents,
        benefitsOptIn,
        analyticsOptIn,
        walletProofReceipts,
        exportBundleViews,
        savedServices,
        servicePlans,
        serviceInteractions,
        walletUnlocked: true,
        privateContextAllowed: false,
        permissionLevel: "wallet_write" as const
      }),
      setActiveRoute: (route: RouteId) => {
        const nextRoute = normalizeAppRoute(route);
        activeRouteRef.current = nextRoute;
        setActiveRoute(nextRoute);
      },
      setServiceDetailDocId,
      setMobileNavOpen,
      setProfile,
      setPolicy,
      setRecipients,
      setShelterContactRequests,
      setShelterStaffAccounts,
      setShelterUserAccounts,
      setUploads,
      setAccessRequests,
      setGrantReceipts,
      setWalletAuditEvents,
      setAnalyticsOptIn,
      setWalletProofReceipts,
      setExportBundleViews,
      setSavedServices,
      setServicePlans,
      setServiceInteractions,
      walletApiConfig,
      refreshWalletAccessState,
      refreshWalletAuditEvents
    }),
    [
      accessRequests,
      exportBundleViews,
      grantReceipts,
      benefitsOptIn,
      analyticsOptIn,
      policy,
      profile,
      recipients,
      savedServices,
      serviceInteractions,
      servicePlans,
      shelterContactRequests,
      shelterCaseRecords,
      shelterProviderMessages,
      shelterStaffAccounts,
      shelterUserAccounts,
      uploads,
      walletApiConfig,
      walletAuditEvents,
      walletProofReceipts
    ]
  );
  const agentChat = useAgentChatService(agentRuntime);

  useEffect(() => {
    const syncRouteFromHash = () => {
      const planDocId = getServicePlanDocIdFromHash();
      const detailDocId = planDocId ? null : getServiceDetailDocIdFromHash();
      const nextRoute = planDocId || detailDocId ? "social-services" : normalizeAppRoute(getRouteFromHash());
      setServicePlanDocId(planDocId);
      setServiceDetailDocId(detailDocId);
      activeRouteRef.current = nextRoute;
      setActiveRoute(nextRoute);
      setMobileNavOpen(false);
    };
    window.addEventListener("hashchange", syncRouteFromHash);
    return () => window.removeEventListener("hashchange", syncRouteFromHash);
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    writePersistedAppState({
      profile,
      policy,
      recipients,
      uploads,
      shelterContactRequests,
      shelterStaffAccounts,
      shelterUserAccounts,
      shelterCaseRecords,
      shelterProviderMessages,
      savedServices,
      servicePlans,
      serviceInteractions,
      proofReceipts: walletProofReceipts,
      benefitsOptIn,
      analyticsOptIn,
      missingPersonDeadDropEnabled,
      missingPersonDeadDropLastSentForCheckInAt,
      shelterChecklist
    });
  }, [
    analyticsOptIn,
    benefitsOptIn,
    missingPersonDeadDropEnabled,
    missingPersonDeadDropLastSentForCheckInAt,
    policy,
    profile,
    recipients,
    savedServices,
    serviceInteractions,
    servicePlans,
    shelterContactRequests,
    shelterCaseRecords,
    shelterChecklist,
    shelterProviderMessages,
    shelterStaffAccounts,
    shelterUserAccounts,
    uploads,
    walletProofReceipts
  ]);

  useEffect(() => {
    syncDocumentLocale(siteLocale);
    writeSiteLocalePreference(siteLocale);
  }, [siteLocale]);

  useEffect(() => {
    writeAssistantTranslationLocalePreference(assistantTranslationLocale);
  }, [assistantTranslationLocale]);

  useEffect(() => {
    writeAssistantAutoTranslatePreference(assistantAutoTranslate);
  }, [assistantAutoTranslate]);

  useEffect(() => {
    if (!walletApiConfig) {
      setWalletActorResolved(false);
      return;
    }
    let cancelled = false;
    setWalletActorResolved(false);
    void loadWalletDetails({
      apiBaseUrl: walletApiConfig.apiBaseUrl,
      walletId: walletApiConfig.walletId
    })
      .then((wallet) => {
        if (cancelled) return;
        const ownerDid = wallet.owner_did.trim();
        if (ownerDid && ownerDid !== walletApiConfig.actorDid) {
          persistWalletApiConfig({
            ...walletApiConfig,
            actorDid: ownerDid
          });
          return;
        }
        setWalletActorResolved(Boolean(ownerDid || walletApiConfig.actorDid));
      })
      .catch(() => {
        if (!cancelled) {
          setWalletActorResolved(Boolean(walletApiConfig.actorDid));
        }
      });
    return () => {
      cancelled = true;
    };
  }, [persistWalletApiConfig, walletApiConfig]);

  useEffect(() => {
    if (!walletApiConfig) return;
    refreshWalletDocuments().catch(() => setUploads(initialUploads));
  }, [walletApiConfig]);

  useEffect(() => {
    if (!walletApiConfig) return;
    refreshWalletAccessState().catch(() => {
      setAccessRequests(initialAccessRequests);
      setGrantReceipts(initialGrantReceipts);
    });
  }, [walletApiConfig]);

  useEffect(() => {
    if (!walletApiConfig) return;
    refreshWalletAuditEvents().catch(() => setWalletAuditEvents(auditEvents));
  }, [walletApiConfig]);

  useEffect(() => {
    if (!walletApiConfig) return;
    refreshWalletProofReceipts().catch(() => setWalletProofReceipts(proofReceipts));
  }, [walletApiConfig]);

  useEffect(() => {
    if (!walletApiConfig) return;
    void refreshWalletPortalState();
  }, [walletApiConfig]);

  useEffect(() => {
    if (!walletApiConfig) return;
    const demoBundleJson = import.meta.env.VITE_DEMO_EXPORT_BUNDLE_JSON as string | undefined;
    if (!demoBundleJson) return;

    try {
      const bundle = JSON.parse(demoBundleJson);
      loadExportBundleView({
        apiBaseUrl: walletApiConfig.apiBaseUrl,
        bundle,
        imported: true
      })
        .then((bundleView) => {
          setExportBundleViews((current) =>
            current.some((item) => item.id === bundleView.id) ? current : [bundleView, ...current]
          );
        })
        .catch(() => undefined);
    } catch {
      // Ignore malformed optional demo data and keep the static bundle examples.
    }
  }, [walletApiConfig]);

  function navigate(route: RouteId) {
    const nextRoute = normalizeAppRoute(route);
    setLocationRouteHash(nextRoute);
    activeRouteRef.current = nextRoute;
    setActiveRoute(nextRoute);
    setServicePlanDocId(null);
    setServiceDetailDocId(null);
    setMobileNavOpen(false);
  }

  const sendMissingPersonDeadDrop = useCallback(async (): Promise<boolean> => {
    if (!walletApiConfig || !walletDeadDropReady) {
      return false;
    }
    try {
      const request = buildMissingPersonDeadDropSyncPayload(true, policy, profile, uploads, recipients);
      await saveMissingPersonDeadDrop(walletApiConfig, {
        toEmail: request.toEmail,
        subject: request.subject,
        body: request.body,
        bundle: request.bundle,
        bundleFileName: request.bundleFileName,
        dueAt: request.dueAt,
        enabled: request.enabled,
        lastCheckInAt: request.lastCheckInAt
      });
      await dispatchMissingPersonDeadDrop(walletApiConfig);
      lastSyncedDeadDropPayloadRef.current = JSON.stringify(request);
      if (isMissingPersonDeadDropDue(policy)) {
        setMissingPersonDeadDropLastSentForCheckInAt(policy.lastCheckInAt);
      }
      return true;
    } catch (error) {
      if (import.meta.env.DEV) {
        console.error("Missing-person dead-drop preparation failed", error);
      }
      return false;
    }
  }, [policy, profile, recipients, uploads, walletApiConfig, walletDeadDropReady]);

  useEffect(() => {
    if (!walletApiConfig || !walletDeadDropReady) {
      lastSyncedDeadDropPayloadRef.current = "";
      return;
    }
    const request = buildMissingPersonDeadDropSyncPayload(
      missingPersonDeadDropEnabled,
      policy,
      profile,
      uploads,
      recipients
    );
    const payload = JSON.stringify(request);
    if (lastSyncedDeadDropPayloadRef.current === payload) {
      return;
    }
    let cancelled = false;
    void saveMissingPersonDeadDrop(walletApiConfig, {
      enabled: missingPersonDeadDropEnabled,
      toEmail: request.toEmail,
      subject: request.subject,
      body: request.body,
      bundle: request.bundle,
      bundleFileName: request.bundleFileName,
      dueAt: request.dueAt,
      lastCheckInAt: request.lastCheckInAt
    })
      .then(() => {
        if (!cancelled) {
          lastSyncedDeadDropPayloadRef.current = payload;
        }
      })
      .catch((error) => {
        if (!cancelled && import.meta.env.DEV) {
          console.error("Missing-person dead-drop arming failed", error);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [missingPersonDeadDropEnabled, policy, profile, recipients, uploads, walletApiConfig, walletDeadDropReady]);

  useEffect(() => {
    if (!missingPersonDeadDropEnabled || !policy.escalationEnabled) return;
    if (!isMissingPersonDeadDropDue(policy)) return;
    if (missingPersonDeadDropLastSentForCheckInAt === policy.lastCheckInAt) return;

    void sendMissingPersonDeadDrop();
  }, [
    missingPersonDeadDropEnabled,
    missingPersonDeadDropLastSentForCheckInAt,
    policy,
    sendMissingPersonDeadDrop
  ]);

  function openServiceDetailFromServices(docId: string) {
    setServicePlanDocId(null);
    openCanonicalServiceDetailRoute(docId, {
      setActiveRoute: (route) => {
        const nextRoute = normalizeAppRoute(route);
        activeRouteRef.current = nextRoute;
        setActiveRoute(nextRoute);
      },
      setServiceDetailDocId,
      setMobileNavOpen
    });
  }

  function handleSignIn(username: string) {
    const nextUsername = username.trim();
    setSignedInUser(nextUsername);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(APP_SESSION_KEY, JSON.stringify({ username: nextUsername }));
    }
  }

  function handleSignOut() {
    setSignedInUser("");
    setActiveRoute("home");
    setMobileNavOpen(false);
    if (typeof window !== "undefined") {
      window.localStorage.removeItem(APP_SESSION_KEY);
      window.localStorage.removeItem(MAGIC_LOGIN_UCAN_KEY);
      window.location.hash = "#/";
    }
  }

  const nextCheckIn = useMemo(() => {
    const next = new Date(policy.lastCheckInAt);
    next.setDate(next.getDate() + policy.intervalDays);
    return next.toLocaleDateString(siteLocale, { month: "short", day: "numeric", year: "numeric" });
  }, [policy.intervalDays, policy.lastCheckInAt, siteLocale]);

  if (!signedInUser) {
    return (
      <LoginScreen
        siteLocale={siteLocale}
        onOpenAssistant={() => {
          handleSignIn("abby");
          openAgentChatMode("audio");
        }}
        onAuthenticated={({ contact, portal, ucan, walletConfig }) => {
          if (walletConfig) {
            persistWalletApiConfig(walletConfig);
          }
          if (ucan && typeof window !== "undefined") {
            window.localStorage.setItem(MAGIC_LOGIN_UCAN_KEY, JSON.stringify(ucan));
          }
          if (walletConfig && ucan) {
            void cacheEncryptedRecoveryBundleFromMagicLogin(walletConfig, ucan).catch((error) => {
              if (import.meta.env.DEV) {
                console.warn("Encrypted recovery bundle was not available for this magic-link login", error);
              }
            });
          }
          handleSignIn(`${portal}:${contact}`);
          navigate(portal === "provider" ? "shelter" : "home");
        }}
      />
    );
  }

  const portalMode = providerRouteIds.has(activeRoute) ? "provider" : "client";
  const portalLabel = portalMode === "provider" ? t(siteLocale, "portal.provider") : t(siteLocale, "portal.client");
  const showClientNavigation = !providerRouteIds.has(activeRoute);
  const showProviderNavigation = signedInUser.startsWith("provider:") || providerRouteIds.has(activeRoute);

  return (
    <div className={`app portal-${portalMode} ${agentChatOpen ? "app-chat-open" : ""}`}>
      <aside className="sidebar" aria-label="Primary navigation">
        <img alt={`Abby ${portalLabel}`} className="brand-logo" src="/assets/abby-icon.png" />
        <nav className="nav-sections" aria-label="Portal navigation">
          {showClientNavigation ? (
            <NavigationGroup
              activeRoute={activeRoute}
              label={t(siteLocale, "nav.clientPortal")}
              routes={localizedClientNavigationRoutes}
              onNavigate={navigate}
            />
          ) : null}
          {showProviderNavigation ? (
            <NavigationGroup
              activeRoute={activeRoute}
              className="nav-group-provider"
              label={t(siteLocale, "nav.providerPortal")}
              routes={localizedProviderNavigationRoutes}
              onNavigate={navigate}
            />
          ) : null}
          <NavigationGroup
            activeRoute={activeRoute}
            className="nav-group-support"
            label={t(siteLocale, "nav.analyticsTools")}
            routes={localizedSecondaryNavigationRoutes}
            onNavigate={navigate}
          />
        </nav>
        <footer className="sidebar-footer">
          <a className="sidebar-footer-link" href="/terms.html">
            Terms and Conditions
          </a>
          <a className="sidebar-footer-link" href="/privacy.html">
            Privacy Policy
          </a>
        </footer>
      </aside>

      <main className="main">
        <header className="topbar">
          <Button
            ariaControls="mobile-navigation"
            ariaExpanded={mobileNavOpen}
            ariaLabel={mobileNavOpen ? t(siteLocale, "topbar.closeMenu") : t(siteLocale, "topbar.openMenu")}
            onClick={() => setMobileNavOpen(!mobileNavOpen)}
            variant="quiet"
          >
            <Menu size={20} />
          </Button>
          <div>
            <strong>Abby</strong>
            <small>{portalMode === "client" ? `${t(siteLocale, "topbar.nextCheckIn")}: ${nextCheckIn}` : portalLabel}</small>
          </div>
          <div className="topbar-actions">
            <label className="topbar-locale-control">
              <span className="sr-only">{t(siteLocale, "settings.siteLanguage")}</span>
              <select value={siteLocale} onChange={(event) => setSiteLocale(normalizeSiteLocale(event.target.value))}>
                {SUPPORTED_LOCALES.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <Button
              ariaControls="agent-chat-bottom-sheet"
              ariaExpanded={agentChatOpen && agentChatMode === "text"}
              ariaLabel={
                agentChatOpen && agentChatMode === "text"
                  ? t(siteLocale, "topbar.closeTextChat")
                  : t(siteLocale, "topbar.openTextChat")
              }
              onClick={() => toggleAgentChatMode("text")}
              variant="quiet"
            >
              <MessageSquare size={20} />
            </Button>
            <Button
              ariaControls="agent-chat-bottom-sheet"
              ariaExpanded={agentChatOpen && agentChatMode === "audio"}
              ariaLabel={
                agentChatOpen && agentChatMode === "audio"
                  ? t(siteLocale, "topbar.closeVoiceChat")
                  : t(siteLocale, "topbar.openVoiceChat")
              }
              onClick={() => toggleAgentChatMode("audio")}
              variant="quiet"
            >
              <Mic size={20} />
            </Button>
            <Button ariaLabel={t(siteLocale, "topbar.signOut")} onClick={handleSignOut} variant="quiet">
              <LogOut size={20} />
            </Button>
          </div>
        </header>

        {mobileNavOpen ? (
          <nav className="mobile-nav-panel" id="mobile-navigation" aria-label="Mobile navigation">
            {showClientNavigation ? (
              <NavigationGroup
                activeRoute={activeRoute}
                label={t(siteLocale, "nav.clientPortal")}
                routes={localizedClientNavigationRoutes}
                onNavigate={navigate}
              />
            ) : null}
            {showProviderNavigation ? (
              <NavigationGroup
                activeRoute={activeRoute}
                className="nav-group-provider"
                label={t(siteLocale, "nav.providerPortal")}
                routes={localizedProviderNavigationRoutes}
                onNavigate={navigate}
              />
            ) : null}
            <NavigationGroup
              activeRoute={activeRoute}
              className="nav-group-support"
              label={t(siteLocale, "nav.analyticsTools")}
              routes={localizedSecondaryNavigationRoutes}
              onNavigate={navigate}
            />
          </nav>
        ) : null}

        {activeRoute === "home" ? (
          <HomeScreen
            navigate={navigate}
            nextCheckIn={nextCheckIn}
            onOpenService={openServiceDetailFromServices}
            policy={policy}
            profile={profile}
            recipients={recipients}
            siteLocale={siteLocale}
            serviceInteractions={serviceInteractions}
            servicePlans={servicePlans}
            showReviewActions={signedInUser.toLowerCase().includes("reviewer")}
            signedInUser={signedInUser}
            providerMessages={shelterProviderMessages}
            uploads={uploads}
          />
        ) : null}
        {activeRoute === "register" ? (
          <RegistrationScreen
            profile={profile}
            siteLocale={siteLocale}
            setProfile={setProfile}
          />
        ) : null}
        {activeRoute === "settings" ? (
          <SettingsScreen
            apiConfig={walletApiConfig}
            assistantAutoTranslate={assistantAutoTranslate}
            assistantTranslationLocale={assistantTranslationLocale}
            analyticsOptIn={analyticsOptIn}
            benefitsOptIn={benefitsOptIn}
            browserLocale={browserLocale}
            missingPersonDeadDropEnabled={missingPersonDeadDropEnabled}
            navigate={navigate}
            nextCheckIn={nextCheckIn}
            onSnapshotLoaded={refreshWalletAfterSnapshotLoad}
            policy={policy}
            profile={profile}
            setAssistantAutoTranslate={setAssistantAutoTranslate}
            setAssistantTranslationLocale={setAssistantTranslationLocale}
            setAnalyticsOptIn={setAnalyticsOptIn}
            setBenefitsOptIn={setBenefitsOptIn}
            setMissingPersonDeadDropEnabled={setMissingPersonDeadDropEnabled}
            setPolicy={setPolicy}
            setProfile={setProfile}
            setSiteLocale={setSiteLocale}
            sendMissingPersonDeadDrop={sendMissingPersonDeadDrop}
            siteLocale={siteLocale}
            walletDeadDropReady={walletDeadDropReady}
            walletConnected={Boolean(walletApiConfig)}
          />
        ) : null}
        {activeRoute === "check-in" ? (
          <CheckInScreen nextCheckIn={nextCheckIn} policy={policy} profile={profile} setPolicy={setPolicy} siteLocale={siteLocale} />
        ) : null}
        {activeRoute === "calendar" ? (
          <CalendarScreen
            interactions={serviceInteractions}
            onOpenPlan={(nextDocId) => {
              setLocationServicePlanHash(nextDocId);
              setServicePlanDocId(nextDocId);
              setServiceDetailDocId(null);
              activeRouteRef.current = "social-services";
              setActiveRoute("social-services");
              setMobileNavOpen(false);
            }}
            onOpenService={openServiceDetailFromServices}
            policy={policy}
            siteLocale={siteLocale}
            servicePlans={servicePlans}
          />
        ) : null}
        {activeRoute === "messages" ? (
          <ClientMessagesScreen
            profile={profile}
            providerMessages={shelterProviderMessages}
            setProviderMessages={setShelterProviderMessages}
            siteLocale={siteLocale}
            signedInUser={signedInUser}
          />
        ) : null}
        {activeRoute === "contacts" ? (
          <ContactsScreen
            contactRequests={shelterContactRequests}
            profile={profile}
            recipients={recipients}
            siteLocale={siteLocale}
            setContactRequests={setShelterContactRequests}
            setRecipients={setRecipients}
          />
        ) : null}
        {activeRoute === "uploads" ? (
          <UploadsScreen
            apiBaseUrl={walletApiBaseUrl}
            apiConfig={walletApiConfig}
            bundles={exportBundleViews}
            proofs={walletProofReceipts}
            refreshWalletAuditEvents={refreshWalletAuditEvents}
            recipients={recipients}
            setApiConfig={persistWalletApiConfig}
            setBundles={setExportBundleViews}
            siteLocale={siteLocale}
            signedInUser={signedInUser}
            uploads={uploads}
            setUploads={setUploads}
          />
        ) : null}
        {servicePlanDocId ? (
          <ServicePlanScreen
            apiConfig={walletApiConfig}
            docId={servicePlanDocId}
            grantReceipts={grantReceipts}
            onBack={() => navigate("social-services")}
            onOpenDetail={openServiceDetailFromServices}
            recipients={recipients}
            refreshWalletPortalState={refreshWalletPortalState}
            savedServices={savedServices}
            servicePlans={servicePlans}
            setGrantReceipts={setGrantReceipts}
            setSavedServices={setSavedServices}
            setServicePlans={setServicePlans}
          />
        ) : null}
        {serviceDetailDocId && !servicePlanDocId ? (
          <ServiceDetailScreen docId={serviceDetailDocId} onBack={() => navigate("social-services")} siteLocale={siteLocale} />
        ) : null}
        {activeRoute === "social-services" && !serviceDetailDocId && !servicePlanDocId ? (
          <SocialServicesScreen
            apiConfig={walletApiConfig}
            onOpenDetail={openServiceDetailFromServices}
            onOpenPlan={(nextDocId) => {
              setLocationServicePlanHash(nextDocId);
              setServicePlanDocId(nextDocId);
              setServiceDetailDocId(null);
              activeRouteRef.current = "social-services";
              setActiveRoute("social-services");
              setMobileNavOpen(false);
            }}
            refreshWalletPortalState={refreshWalletPortalState}
            savedServices={savedServices}
            servicePlans={servicePlans}
            setSavedServices={setSavedServices}
            siteLocale={siteLocale}
            walletPortalError={walletPortalError}
            walletPortalLoading={walletPortalLoading}
          />
        ) : null}
        {activeRoute === "interactions" || activeRoute === "audit" ? (
          <InteractionsScreen
            accessRequests={accessRequests}
            apiConfig={walletApiConfig}
            auditEvents={walletAuditEvents}
            error={walletPortalError}
            grantReceipts={grantReceipts}
            interactions={serviceInteractions}
            loading={walletPortalLoading}
            onOpenPlan={(nextDocId) => {
              setLocationServicePlanHash(nextDocId);
              setServicePlanDocId(nextDocId);
              setServiceDetailDocId(null);
              activeRouteRef.current = "social-services";
              setActiveRoute("social-services");
              setMobileNavOpen(false);
            }}
            onOpenService={openServiceDetailFromServices}
            onRefresh={refreshWalletPortalState ? () => void refreshWalletPortalState() : undefined}
            proofReceipts={walletProofReceipts}
            recipients={recipients}
            savedServices={savedServices}
            servicePlans={servicePlans}
            uploads={uploads}
          />
        ) : null}
        {providerRouteIds.has(activeRoute) ? (
          <ShelterScreen
            checklist={shelterChecklist}
            setChecklist={setShelterChecklist}
            contactRequests={shelterContactRequests}
            navigate={navigate}
            profile={profile}
            proofReceipts={walletProofReceipts}
            shelterCaseRecords={shelterCaseRecords}
            providerMessages={shelterProviderMessages}
            recipients={recipients}
            siteLocale={siteLocale}
            setContactRequests={setShelterContactRequests}
            setShelterCaseRecords={setShelterCaseRecords}
            setProofReceipts={setWalletProofReceipts}
            setProviderMessages={setShelterProviderMessages}
            setRecipients={setRecipients}
            shelterStaffAccounts={shelterStaffAccounts}
            setShelterStaffAccounts={setShelterStaffAccounts}
            shelterUserAccounts={shelterUserAccounts}
            setShelterUserAccounts={setShelterUserAccounts}
            view={getProviderPortalView(activeRoute)}
          />
        ) : null}
        {activeRoute === "recipient-access" ? (
          <RecipientAccessScreen
            accessRequests={accessRequests}
            apiConfig={walletApiConfig}
            grantReceipts={grantReceipts}
            recipients={recipients}
            refreshWalletAccessState={refreshWalletAccessState}
            refreshWalletAuditEvents={refreshWalletAuditEvents}
            setAccessRequests={setAccessRequests}
            setGrantReceipts={setGrantReceipts}
            setVerified={setRecipientVerified}
            verified={recipientVerified}
          />
        ) : null}
        {activeRoute === "benefits-protection" ? (
          <BenefitsProtectionScreen optedIn={benefitsOptIn} setOptedIn={setBenefitsOptIn} />
        ) : null}
        {activeRoute === "analytics" ? (
          <AnalyticsScreen optedIn={analyticsOptIn} proofs={walletProofReceipts} setOptedIn={setAnalyticsOptIn} />
        ) : null}
        {activeRoute === "proof-center" ? (
          <ProofCenterScreen
            apiConfig={walletApiConfig}
            proofs={walletProofReceipts}
            refreshWalletAuditEvents={refreshWalletAuditEvents}
            setProofs={setWalletProofReceipts}
            uploads={uploads}
          />
        ) : null}
      </main>
      <AgentChatDrawer
        activeRouteLabel={translateRouteLabel(siteLocale, activeRoute, getRouteLabel(activeRoute))}
        assistantLabel={t(siteLocale, "chat.assistant")}
        autoTranslateAssistant={assistantAutoTranslate}
        composerLabel={t(siteLocale, "composer.label")}
        composerPlaceholder={t(siteLocale, "composer.placeholder")}
        confirmations={agentChat.pendingConfirmations}
        currentTaskDetail={t(siteLocale, "chat.appAwareDetail")}
        currentTaskLabel={t(siteLocale, "chat.appAware")}
        evidenceBundles={agentChat.snapshot.session.evidenceBundles}
        mode={agentChatMode}
        messages={agentChat.messages}
        onCancelConfirmation={(confirmationId) => agentChat.denyConfirmation(confirmationId)}
        onClose={() => setAgentChatOpen(false)}
        onConfirmConfirmation={(confirmationId) => agentChat.approveConfirmation(confirmationId)}
        onOpenAudio={() => openAgentChatMode("audio")}
        onOpenText={() => openAgentChatMode("text")}
        onOpenServiceDetail={(docId) => {
          setServicePlanDocId(null);
          return openCanonicalServiceDetailRoute(docId, {
            setActiveRoute: (route) => {
              const nextRoute = normalizeAppRoute(route);
              activeRouteRef.current = nextRoute;
              setActiveRoute(nextRoute);
            },
            setServiceDetailDocId,
            setMobileNavOpen
          });
        }}
        onSend={(message) => {
          void agentChat.sendMessage(message, {
            disableLocalLlmReasoning: agentChatMode === "audio",
            preferGraphRagForGeneralQuestions: agentChatMode === "audio",
          });
        }}
        onAudioReply={(messageId, record) => {
          agentChat.patchMessageMetadata(messageId, { audioReply: record });
        }}
        open={agentChatOpen}
        responding={agentChat.responding}
        respondingLabel={t(siteLocale, "chat.responding")}
        siteLocale={siteLocale}
        toolCalls={agentChat.snapshot.session.toolCalls}
        toolResults={agentChat.snapshot.session.toolResults}
        translationLocale={assistantTranslationLocale}
        voiceLabel={t(siteLocale, "chat.voice")}
      />
    </div>
  );
}

function LoginScreen({
  onAuthenticated,
  onOpenAssistant,
  siteLocale
}: {
  onAuthenticated: (result: LoginAuthResult) => void;
  onOpenAssistant: () => void;
  siteLocale: SupportedLocale;
}) {
  const [portal, setPortal] = useState<LoginPortal>("client");
  const [contact, setContact] = useState("");
  const [challenge, setChallenge] = useState<LoginChallenge | null>(null);
  const [oneTimePadEntry, setOneTimePadEntry] = useState("");
  const [loginMessage, setLoginMessage] = useState("");
  const [loginError, setLoginError] = useState("");
  const [loginSmsWarning, setLoginSmsWarning] = useState("");
  const [pending, setPending] = useState(false);
  const canRequestChallenge = isValidLoginContact(contact);

  useEffect(() => {
    const token = new URLSearchParams(window.location.search).get(MAGIC_LOGIN_PARAM);
    if (!token) return;
    void verifyMagicLinkToken(token);
  }, []);

  function updatePortal(nextPortal: LoginPortal) {
    setPortal(nextPortal);
    setChallenge(null);
    setOneTimePadEntry("");
    setLoginError("");
    setLoginSmsWarning("");
    setLoginMessage("");
  }

  async function submitLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canRequestChallenge) {
      setLoginError(t(siteLocale, "login.invalidContact"));
      return;
    }
    setPending(true);
    setLoginError("");
    setLoginSmsWarning("");
    setLoginMessage("");
    try {
      const normalizedContact = normalizeLoginContact(contact);
      try {
        const response = await requestServerMagicLogin({ contact: normalizedContact, portal });
        setChallenge(null);
        setOneTimePadEntry("");
        setLoginMessage(
          response.channel === "email"
            ? t(siteLocale, "login.emailSent")
            : t(siteLocale, "login.textSent")
        );
        return;
      } catch (error) {
        if (!shouldAllowLocalMagicLoginFallback()) {
          setLoginError(error instanceof Error ? error.message : t(siteLocale, "login.magicLinkFailed"));
          return;
        }
        setLoginSmsWarning(t(siteLocale, "login.localFallbackWarning"));
      }
      const issuedAt = Date.now();
      const expiresAt = issuedAt + MAGIC_LOGIN_TTL_MS;
      const oneTimePad = randomOneTimePad();
      const basePayload = {
        portal,
        contact: normalizedContact,
        issuedAt,
        expiresAt,
        salt: `${oneTimePad}.${randomBase64Url(18)}`
      };
      const digest = await createMagicLoginDigest(basePayload);
      const payload = { ...basePayload, digest };
      const magicUrl = new URL(window.location.href);
      magicUrl.search = "";
      magicUrl.hash = "#/";
      magicUrl.searchParams.set(MAGIC_LOGIN_PARAM, encodeMagicLoginPayload(payload));
      const magicLink = magicUrl.toString();
      setChallenge({ ...payload, oneTimePad, magicLink });
      setOneTimePadEntry("");
      setLoginMessage(t(siteLocale, "login.localReady"));
    } finally {
      setPending(false);
    }
  }

  async function verifyOneTimePad() {
    if (!challenge) return;
    if (Date.now() > challenge.expiresAt) {
      setLoginError(t(siteLocale, "login.codeExpired"));
      return;
    }
    if (oneTimePadEntry.trim() !== challenge.oneTimePad) {
      setLoginError(t(siteLocale, "login.codeMismatch"));
      return;
    }
    const digest = await createMagicLoginDigest({
      contact: challenge.contact,
      expiresAt: challenge.expiresAt,
      issuedAt: challenge.issuedAt,
      portal: challenge.portal,
      salt: challenge.salt
    });
    if (digest !== challenge.digest) {
      setLoginError(t(siteLocale, "login.codeVerifyFailed"));
      return;
    }
    completeLogin({ contact: challenge.contact, portal: challenge.portal });
  }

  async function verifyMagicLinkToken(token: string) {
    try {
      const result = await verifyServerMagicLogin(token);
      window.history.replaceState({}, "", `${window.location.pathname}${window.location.hash || "#/"}`);
      completeLogin(result);
      return;
    } catch (error) {
      if (!shouldAllowLocalMagicLoginFallback()) {
        setLoginError(error instanceof Error ? error.message : "The magic link could not be verified.");
        return;
      }
    }
    const payload = decodeMagicLoginPayload(token);
    if (!payload) {
      setLoginError(t(siteLocale, "login.magicInvalid"));
      return;
    }
    if (Date.now() > payload.expiresAt) {
      setLoginError(t(siteLocale, "login.magicExpired"));
      return;
    }
    const digest = await createMagicLoginDigest(payload);
    if (digest !== payload.digest) {
      setLoginError(t(siteLocale, "login.magicVerifyFailed"));
      return;
    }
    window.history.replaceState({}, "", `${window.location.pathname}${window.location.hash || "#/"}`);
    completeLogin({ contact: payload.contact, portal: payload.portal });
  }

  function completeLogin(result: LoginAuthResult) {
    onAuthenticated(result);
  }

  return (
    <main className="login-page">
      <form className="login-panel" onSubmit={submitLogin}>
        <div className="login-brand">
          <img alt="Abby logo" className="login-logo" src="/assets/abby-logo.png" />
          <h1 className="sr-only">{t(siteLocale, "login.signIn")}</h1>
        </div>
        <div className="login-portal-actions" aria-label={t(siteLocale, "login.choosePortal")} role="group">
          <button
            aria-pressed={portal === "client"}
            className="login-portal-option"
            onClick={() => updatePortal("client")}
            type="button"
          >
            <Home aria-hidden="true" size={20} />
            <span>{t(siteLocale, "login.client")}</span>
          </button>
          <button
            aria-pressed={portal === "provider"}
            className="login-portal-option"
            onClick={() => updatePortal("provider")}
            type="button"
          >
            <UsersRound aria-hidden="true" size={20} />
            <span>{t(siteLocale, "login.provider")}</span>
          </button>
        </div>
        <Field label={t(siteLocale, "login.contactLabel")} required>
          <input
            autoComplete="username"
            inputMode="email"
            placeholder={t(siteLocale, "login.contactPlaceholder")}
            value={contact}
            onChange={(event) => {
              setContact(event.target.value);
              setChallenge(null);
              setOneTimePadEntry("");
              setLoginError("");
              setLoginSmsWarning("");
              setLoginMessage("");
            }}
          />
        </Field>
        <Button disabled={!canRequestChallenge || pending} loading={pending} loadingLabel={t(siteLocale, "login.prepareAccess")} type="submit">
          <KeyRound aria-hidden="true" size={18} /> {t(siteLocale, "login.sendLink")}
        </Button>
        {loginError ? <StatusBanner tone="danger">{loginError}</StatusBanner> : null}
        {loginSmsWarning ? <StatusBanner tone="warning">{loginSmsWarning}</StatusBanner> : null}
        {loginMessage ? <StatusBanner tone="success">{loginMessage}</StatusBanner> : null}
        {challenge ? (
          <div className="login-challenge-panel">
            <div className="login-code-display">
              <small>{t(siteLocale, "login.demoPad")}</small>
              <code aria-label="Generated one-time pad code">{challenge.oneTimePad}</code>
            </div>
            <Field label={t(siteLocale, "login.codeLabel")} required>
              <input
                autoComplete="one-time-code"
                inputMode="numeric"
                maxLength={6}
                value={oneTimePadEntry}
                onChange={(event) => {
                  setOneTimePadEntry(event.target.value.replace(/\D/g, "").slice(0, 6));
                  setLoginError("");
                }}
              />
            </Field>
            <div className="login-challenge-actions">
              <Button disabled={oneTimePadEntry.length !== 6} onClick={verifyOneTimePad} type="button">
                {t(siteLocale, "login.verifyCode")}
              </Button>
              <a className="button button-secondary" href={challenge.magicLink}>
                {t(siteLocale, "login.openMagicLink")}
              </a>
            </div>
            <p className="login-proof-note">
              {t(siteLocale, "login.localDevNote")}
            </p>
          </div>
        ) : null}
        <Button onClick={onOpenAssistant} type="button" variant="secondary">
          <MessageSquare aria-hidden="true" size={18} /> {t(siteLocale, "login.openAssistant")}
        </Button>
      </form>
    </main>
  );
}

function HomeScreen({
  navigate,
  nextCheckIn,
  onOpenService,
  policy,
  profile,
  providerMessages,
  recipients,
  siteLocale,
  serviceInteractions,
  servicePlans,
  showReviewActions,
  signedInUser,
  uploads
}: {
  navigate: (route: RouteId) => void;
  nextCheckIn: string;
  onOpenService: (docId: string) => void;
  policy: CheckInPolicyDraft;
  profile: RegistrationProfileDraft;
  providerMessages: ShelterProviderMessage[];
  recipients: DisclosureRecipientDraft[];
  siteLocale: SupportedLocale;
  serviceInteractions: ServiceInteractionEvent[];
  servicePlans: ServicePlan[];
  showReviewActions: boolean;
  signedInUser: string;
  uploads: UploadItem[];
}) {
  const [homeSuggestions, setHomeSuggestions] = useState<HomeServiceSuggestion[]>([]);
  const [homeSuggestionsLoading, setHomeSuggestionsLoading] = useState(false);
  const selectedNeeds = useMemo(
    () => Array.from(new Set(profile.serviceNeeds.map((value) => value.trim()).filter(Boolean))).slice(0, 3),
    [profile.serviceNeeds]
  );
  const selectedNeedLabels = useMemo(() => selectedNeeds.map((need) => translateServiceNeed(siteLocale, need)), [selectedNeeds, siteLocale]);
  const inboxMessages = useMemo(
    () =>
      providerMessages
        .filter((message) => messageMatchesClient(message, profile, signedInUser))
        .filter((message) => !message.clientArchivedAt)
        .sort((left, right) => new Date(right.createdAt).getTime() - new Date(left.createdAt).getTime()),
    [profile, providerMessages, signedInUser]
  );
  const featuredMessages = useMemo(() => {
    const unread = inboxMessages.filter((message) => !message.clientReadAt);
    return (unread.length ? unread : inboxMessages).slice(0, 3);
  }, [inboxMessages]);
  const urgentCalendarItems = useMemo(
    () => buildHomeCalendarItems({ policy, serviceInteractions, servicePlans }).slice(0, 3),
    [policy, serviceInteractions, servicePlans]
  );

  useEffect(() => {
    let canceled = false;

    async function loadHomeSuggestions() {
      if (!selectedNeeds.length) {
        setHomeSuggestions([]);
        return;
      }

      setHomeSuggestionsLoading(true);
      try {
        const searchBundles = await Promise.all(
          selectedNeeds.map(async (need) => {
            const query = `${need} near me`;
            const [results, preferredClusterIds] = await Promise.all([
              search211Info(query, 3).catch(() => []),
              resolvePreferred211ServiceClusterIds(query, 8).catch(() => []),
            ]);
            return {
              need,
              results: results.slice(0, 2),
              preferredClusterIds,
            };
          })
        );

        const uniqueResults: Array<{ need: string; result: SearchResult }> = [];
        const seenDocIds = new Set<string>();
        const allPreferredClusterIds = new Set<number>();
        for (const bundle of searchBundles) {
          for (const clusterId of bundle.preferredClusterIds) {
            allPreferredClusterIds.add(clusterId);
          }
          for (const result of bundle.results) {
            if (seenDocIds.has(result.docId)) continue;
            seenDocIds.add(result.docId);
            uniqueResults.push({ need: bundle.need, result });
          }
        }

        const visibleResults = uniqueResults.slice(0, 4);
        const locationRows = visibleResults.length
          ? await load211ServiceLocationsSlice({
              serviceDocIds: visibleResults.map((entry) => entry.result.docId),
            }).catch(() => [])
          : [];
        const locationLabels = buildSearchResultLocationLabels(
          visibleResults.map((entry) => entry.result),
          locationRows,
          Array.from(allPreferredClusterIds)
        );

        if (canceled) return;
        setHomeSuggestions(
          visibleResults.map(({ need, result }) => ({
            need,
            result,
            locationLabel: locationLabels[result.docId] || getServiceLocationLabel(result.document),
          }))
        );
      } finally {
        if (!canceled) {
          setHomeSuggestionsLoading(false);
        }
      }
    }

    void loadHomeSuggestions();
    return () => {
      canceled = true;
    };
  }, [selectedNeeds]);

  return (
    <div className="screen home-screen">
      <div className="page-title home-hero">
        <p className="eyebrow">{t(siteLocale, "home.today")}</p>
        <h1>{t(siteLocale, "home.welcome")}</h1>
      </div>
      <Section title={t(siteLocale, "home.quickActions")}>
        <div className="quick-actions">
          <button className="checkin-panel" onClick={() => navigate("check-in")} type="button">
            <div className="checkin-panel-icon">
              <CalendarCheck size={24} aria-hidden="true" />
            </div>
            <div className="checkin-panel-text">
              <span className="checkin-panel-label">{t(siteLocale, "home.nextCheckIn")}</span>
              <span className="checkin-panel-value">{nextCheckIn}</span>
            </div>
            <span className="checkin-panel-cta">{t(siteLocale, "home.checkInNow")}</span>
          </button>
        </div>
      </Section>
      <Section title={t(siteLocale, "home.closestHelp")}>
        {selectedNeeds.length ? (
          homeSuggestionsLoading ? (
            <StatusBanner tone="info">{t(siteLocale, "home.findingNearby")} {selectedNeedLabels.join(", ")}.</StatusBanner>
          ) : homeSuggestions.length ? (
            <div className="list-stack" aria-label="Nearby services for selected needs">
              {homeSuggestions.map(({ need, result, locationLabel }) => {
                const document = result.document;
                const program = document.program_name || document.title || "Program not listed";
                const provider = document.provider_name || "Provider not listed";
                return (
                  <article className="list-item" key={`${need}:${result.docId}`}>
                    <div>
                      <h3>{program}</h3>
                      <p>{provider}</p>
                      <small className="upload-machine-summary">{result.snippet}</small>
                      <div className="badge-row">
                        <Badge>{translateServiceNeed(siteLocale, need)}</Badge>
                        {locationLabel ? <Badge>{locationLabel}</Badge> : null}
                      </div>
                    </div>
                    <div className="row-actions list-item-action">
                      <Button onClick={() => onOpenService(result.docId)} variant="secondary">
                        {t(siteLocale, "action.openService")}
                      </Button>
                    </div>
                  </article>
                );
              })}
            </div>
          ) : (
            <StatusBanner tone="info">{t(siteLocale, "home.noNearbyMatches")}</StatusBanner>
          )
        ) : (
          <div className="empty-state">
            <h3>{t(siteLocale, "home.noCategories")}</h3>
            <p>{t(siteLocale, "home.addHelpSettings")}</p>
            <div className="row-actions">
              <Button onClick={() => navigate("settings")} variant="secondary">{t(siteLocale, "home.updateSettings")}</Button>
            </div>
          </div>
        )}
      </Section>
      <Section title={t(siteLocale, "home.newMessages")}>
        {featuredMessages.length ? (
          <div className="list-stack" aria-label={t(siteLocale, "home.newMessagesAria")}>
            {featuredMessages.map((message) => (
              <article className="list-item" key={message.id}>
                <div>
                  <h3>{message.subject}</h3>
                  <p>{message.body}</p>
                  <div className="badge-row">
                    <Badge>{message.shelter}</Badge>
                    <Badge tone={message.clientReadAt ? "neutral" : "warning"}>
                      {message.clientReadAt ? t(siteLocale, "home.read") : t(siteLocale, "home.unread")}
                    </Badge>
                    <Badge>{formatShelterDate(message.createdAt)}</Badge>
                  </div>
                  <small>{t(siteLocale, "home.from")} {message.staffName}</small>
                </div>
                <div className="row-actions list-item-action">
                  <Button onClick={() => navigate("messages")} variant="secondary">
                    {t(siteLocale, "home.openMessages")}
                  </Button>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <StatusBanner tone="info">{t(siteLocale, "home.noMessages")}</StatusBanner>
        )}
      </Section>
      <Section title={t(siteLocale, "home.urgentItems")}>
        {urgentCalendarItems.length ? (
          <div className="list-stack" aria-label={t(siteLocale, "home.urgentItemsAria")}>
            {urgentCalendarItems.map((item) => {
              const serviceDocId = item.serviceDocId;
              return (
                <article className="list-item" key={item.id}>
                  <div>
                    <h3>{item.title}</h3>
                    <p>{item.detail}</p>
                    <div className="badge-row">
                      <Badge>{item.kindLabel}</Badge>
                      <Badge tone={item.urgencyTone}>{item.urgencyLabel}</Badge>
                      {item.location ? <Badge>{item.location}</Badge> : null}
                    </div>
                    <small>{formatHomeDateTime(item.startsAt)}</small>
                  </div>
                  <div className="row-actions list-item-action">
                    <Button onClick={() => navigate("calendar")} variant="secondary">
                      {t(siteLocale, "home.openCalendar")}
                    </Button>
                    {serviceDocId ? (
                      <Button onClick={() => onOpenService(serviceDocId)} variant="secondary">
                        {t(siteLocale, "action.openService")}
                      </Button>
                    ) : null}
                  </div>
                </article>
              );
            })}
          </div>
        ) : (
          <StatusBanner tone="info">{t(siteLocale, "home.noUrgentItems")}</StatusBanner>
        )}
      </Section>
      {showReviewActions ? (
        <div className="home-actions" aria-label={t(siteLocale, "home.safetyPlanSetup")}>
          <ActionCard
            detail={`${recipients.length} ${t(siteLocale, "home.contactsDetail")}`}
            icon={<ContactRound aria-hidden="true" size={28} />}
            onClick={() => navigate("contacts")}
            title={t(siteLocale, "home.contacts")}
          />
          <ActionCard
            detail={t(siteLocale, "home.sharingDetail")}
            icon={<ShieldCheck aria-hidden="true" size={28} />}
            onClick={() => navigate("contacts")}
            title={t(siteLocale, "home.sharing")}
          />
        </div>
      ) : null}
      <div className="home-footer">
        <div className="home-footer-stat">
          <small>{t(siteLocale, "home.savedFiles")}</small>
          <span>{uploads.length} {uploads.length !== 1 ? t(siteLocale, "home.filePlural") : t(siteLocale, "home.fileSingular")}</span>
        </div>
        <div className="home-footer-divider" />
        <div className="home-footer-stat">
          <small>{t(siteLocale, "home.contactSharing")}</small>
          <span>{t(siteLocale, "home.reviewReady")}</span>
        </div>
        <div className="home-footer-divider" />
        <div className="home-footer-stat">
          <small>{t(siteLocale, "home.legal")}</small>
          <div className="home-footer-links">
            <a className="home-footer-link" href="/terms.html">
              {t(siteLocale, "home.terms")}
            </a>
            <a className="home-footer-link" href="/privacy.html">
              {t(siteLocale, "home.privacy")}
            </a>
          </div>
        </div>
      </div>
      <section className="support-card" aria-labelledby="support-card-title">
        <span className="support-card-badge" aria-hidden="true" />
        <div className="support-card-content">
          <h2 id="support-card-title">{t(siteLocale, "home.needHelpToday")}</h2>
          <p>{t(siteLocale, "home.supportDescription")}</p>
          <Button onClick={() => navigate("social-services")}>
            <HeartHandshake aria-hidden="true" size={18} /> {t(siteLocale, "home.findHelp")}
          </Button>
        </div>
      </section>
    </div>
  );
}

function RegistrationScreen({
  profile,
  siteLocale,
  setProfile
}: {
  profile: RegistrationProfileDraft;
  siteLocale: SupportedLocale;
  setProfile: (profile: RegistrationProfileDraft) => void;
}) {
  return (
    <div className="screen">
      <div className="page-title">
        <p className="eyebrow">{t(siteLocale, "registration.eyebrow")}</p>
        <h1>{t(siteLocale, "registration.title")}</h1>
      </div>
      <p className="page-note">{t(siteLocale, "registration.note")}</p>
      <ProfileInformationForm profile={profile} setProfile={setProfile} siteLocale={siteLocale} />
      <GovernmentHelpSection
        siteLocale={siteLocale}
        requested={profile.servicePartnerHelpRequested}
        requestedAt={profile.servicePartnerHelpRequestedAt}
        onToggle={() => togglePartnerHelpRequest(profile, setProfile)}
      />
    </div>
  );
}

function ProfileInformationForm({
  profile,
  siteLocale,
  setProfile
}: {
  profile: RegistrationProfileDraft;
  siteLocale: SupportedLocale;
  setProfile: (profile: RegistrationProfileDraft) => void;
}) {
  const update = (patch: Partial<RegistrationProfileDraft>) => setProfile({ ...profile, ...patch });
  const [photoFileDetail, setPhotoFileDetail] = useState("");
  const [photoUploadError, setPhotoUploadError] = useState("");

  async function handleProfileUploadChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];

    if (!file) {
      update({ photoAssetId: "" });
      setPhotoFileDetail("");
      setPhotoUploadError("");
      return;
    }

    if (!isAcceptedIdentityDocument(file)) {
      update({ photoAssetId: "" });
      setPhotoFileDetail("");
      setPhotoUploadError(t(siteLocale, "profile.badFile"));
      return;
    }

    update({ photoAssetId: file.name });
    setPhotoFileDetail(getIdentityDocumentFileDetail(file));
    setPhotoUploadError("");
  }

  function toggleNeed(need: string) {
    update({
      serviceNeeds: profile.serviceNeeds.includes(need)
        ? profile.serviceNeeds.filter((item) => item !== need)
        : [...profile.serviceNeeds, need]
    });
  }

  return (
    <form className="form-grid" onSubmit={(event) => event.preventDefault()}>
      <Field help={t(siteLocale, "profile.legalNameHelp")} label={t(siteLocale, "profile.legalName")} required>
        <input value={profile.legalName} onChange={(event) => update({ legalName: event.target.value })} />
      </Field>
      <Field help={t(siteLocale, "profile.preferredNameHelp")} label={t(siteLocale, "profile.preferredName")}>
        <input value={profile.preferredName} onChange={(event) => update({ preferredName: event.target.value })} />
      </Field>
      <Field help={t(siteLocale, "profile.pronounsHelp")} label={t(siteLocale, "profile.pronouns")}>
        <input
          placeholder={t(siteLocale, "profile.pronounsPlaceholder")}
          value={profile.pronouns}
          onChange={(event) => update({ pronouns: event.target.value })}
        />
      </Field>
      <Field help={t(siteLocale, "profile.birthDateHelp")} label={t(siteLocale, "profile.birthDate")} required>
        <input
          type="date"
          value={profile.dateOfBirth}
          onChange={(event) => update({ dateOfBirth: event.target.value })}
        />
      </Field>
      <Field
        error={photoUploadError}
        help={t(siteLocale, "profile.photoIdHelp")}
        label={t(siteLocale, "profile.photoId")}
        required
      >
        <input
          accept={ID_DOCUMENT_ACCEPT_ATTR}
          type="file"
          onChange={handleProfileUploadChange}
        />
        {photoFileDetail ? (
          <small className="registration-file-detail" aria-live="polite">
            {t(siteLocale, "profile.selectedFile")}: {photoFileDetail}
          </small>
        ) : null}
      </Field>
      <hr className="form-divider full-span" />
      <Field help={t(siteLocale, "profile.phoneHelp")} label={t(siteLocale, "profile.phone")}>
        <input value={profile.phone} onChange={(event) => update({ phone: event.target.value })} />
      </Field>
      <Field help={t(siteLocale, "profile.emailHelp")} label={t(siteLocale, "profile.email")}>
        <input type="email" value={profile.email} onChange={(event) => update({ email: event.target.value })} />
      </Field>
      <Field help={t(siteLocale, "profile.locationHelp")} label={t(siteLocale, "profile.location")}>
        <input value={profile.currentLocation} onChange={(event) => update({ currentLocation: event.target.value })} />
      </Field>
      <Field help={t(siteLocale, "profile.shelterHelp")} label={t(siteLocale, "profile.shelter")}>
        <input
          value={profile.shelterAffiliation}
          onChange={(event) => update({ shelterAffiliation: event.target.value })}
        />
      </Field>
      <div className="full-span">
        <span className="field-label">{t(siteLocale, "profile.serviceNeeds")}</span>
        <div className="chip-grid">
          {serviceNeeds.map((need) => (
            <button
              aria-pressed={profile.serviceNeeds.includes(need)}
              className="choice-chip"
              key={need}
              onClick={() => toggleNeed(need)}
              type="button"
            >
              {translateServiceNeed(siteLocale, need)}
            </button>
          ))}
        </div>
      </div>
    </form>
  );
}

function togglePartnerHelpRequest(
  profile: RegistrationProfileDraft,
  setProfile: (profile: RegistrationProfileDraft) => void
) {
  setProfile({
    ...profile,
    servicePartnerHelpRequested: !profile.servicePartnerHelpRequested,
    servicePartnerHelpRequestedAt: profile.servicePartnerHelpRequested ? "" : new Date().toISOString()
  });
}

function GovernmentHelpSection({
  onToggle,
  requested,
  siteLocale,
  requestedAt
}: {
  onToggle: () => void;
  requested: boolean;
  siteLocale: SupportedLocale;
  requestedAt: string;
}) {
  return (
    <Section title={t(siteLocale, "government.title")}>
      <div className={`liaison-panel partner-help-panel${requested ? " partner-help-panel-active" : ""}`}>
        <MessageSquare aria-hidden="true" size={28} />
        <div>
          <h3>{t(siteLocale, "government.heading")}</h3>
          <p>
            {requested
              ? t(siteLocale, "government.requestedText")
              : t(siteLocale, "government.unrequestedText")}
          </p>
          {requested ? (
            <div className="badge-row" aria-label="Government help request status">
              <Badge tone="warning">{t(siteLocale, "government.requestedBadge")}</Badge>
              {requestedAt ? <Badge>{formatRequestTimestamp(requestedAt, siteLocale)}</Badge> : null}
            </div>
          ) : null}
        </div>
        <Button ariaPressed={requested} onClick={onToggle} variant={requested ? "secondary" : "primary"}>
          {requested ? t(siteLocale, "government.clearRequest") : t(siteLocale, "government.startRequest")}
        </Button>
      </div>
    </Section>
  );
}

function formatRequestTimestamp(value: string, locale: SupportedLocale): string {
  const timestamp = new Date(value);
  if (Number.isNaN(timestamp.getTime())) return t(locale, "government.requestedOn");
  return `${t(locale, "government.requestedOn")} ${timestamp.toLocaleDateString(locale, { month: "short", day: "numeric" })}`;
}

function SettingsScreen({
  apiConfig,
  assistantAutoTranslate,
  assistantTranslationLocale,
  analyticsOptIn,
  benefitsOptIn,
  browserLocale,
  missingPersonDeadDropEnabled,
  navigate,
  nextCheckIn,
  onSnapshotLoaded,
  policy,
  profile,
  setAssistantAutoTranslate,
  setAssistantTranslationLocale,
  setAnalyticsOptIn,
  setBenefitsOptIn,
  setMissingPersonDeadDropEnabled,
  setPolicy,
  setProfile,
  setSiteLocale,
  sendMissingPersonDeadDrop,
  siteLocale,
  walletDeadDropReady,
  walletConnected
}: {
  apiConfig?: WalletApiConfig;
  assistantAutoTranslate: boolean;
  assistantTranslationLocale: string;
  analyticsOptIn: Record<string, boolean>;
  benefitsOptIn: boolean;
  browserLocale: string;
  missingPersonDeadDropEnabled: boolean;
  navigate: (route: RouteId) => void;
  nextCheckIn: string;
  onSnapshotLoaded: () => Promise<void> | void;
  policy: typeof defaultCheckInPolicy;
  profile: RegistrationProfileDraft;
  setAssistantAutoTranslate: (enabled: boolean) => void;
  setAssistantTranslationLocale: (value: string) => void;
  setAnalyticsOptIn: (value: Record<string, boolean>) => void;
  setBenefitsOptIn: (optedIn: boolean) => void;
  setMissingPersonDeadDropEnabled: (enabled: boolean) => void;
  setPolicy: (policy: typeof defaultCheckInPolicy) => void;
  setProfile: (profile: RegistrationProfileDraft) => void;
  setSiteLocale: (locale: SupportedLocale) => void;
  sendMissingPersonDeadDrop: () => Promise<boolean>;
  siteLocale: SupportedLocale;
  walletDeadDropReady: boolean;
  walletConnected: boolean;
}) {
  const updatePolicy = (patch: Partial<typeof defaultCheckInPolicy>) => setPolicy({ ...policy, ...patch });
  const toggleReminderChannel = (channel: CheckInChannel) => {
    updatePolicy({
      reminderChannels: policy.reminderChannels.includes(channel)
        ? policy.reminderChannels.filter((item) => item !== channel)
        : [...policy.reminderChannels, channel]
    });
  };
  const profileComplete = Boolean(profile.legalName.trim() && profile.dateOfBirth && profile.photoAssetId);
  const selectedAnalyticsStudyCount = analyticsStudies.filter((study) => analyticsOptIn[study.id] ?? true).length;
  const [deadDropStatus, setDeadDropStatus] = useState<"idle" | "sent" | "failed">("idle");

  function toggleAnalyticsStudy(studyId: string) {
    setAnalyticsOptIn({ ...analyticsOptIn, [studyId]: !(analyticsOptIn[studyId] ?? true) });
  }

  useEffect(() => {
    if (!missingPersonDeadDropEnabled) {
      setDeadDropStatus("idle");
    }
  }, [missingPersonDeadDropEnabled]);

  async function handleSendMissingPersonDeadDrop() {
    const sent = await sendMissingPersonDeadDrop();
    setDeadDropStatus(sent ? "sent" : "failed");
  }

  return (
    <div className="screen settings-screen">
      <div className="page-title">
        <p className="eyebrow">{t(siteLocale, "portal.client")}</p>
        <h1>{t(siteLocale, "settings.title")}</h1>
      </div>
      <p className="page-note">{t(siteLocale, "settings.note")}</p>
      <div className="privacy-metrics settings-summary">
        <StatusPanel label={t(siteLocale, "settings.profileStatus")} value={profileComplete ? t(siteLocale, "settings.ready") : t(siteLocale, "settings.needsReview")} tone={profileComplete ? "teal" : "gold"} />
        <StatusPanel label={t(siteLocale, "settings.checkIns")} value={`${policy.intervalDays} ${t(siteLocale, "settings.days")}`} tone="teal" />
        <StatusPanel label={t(siteLocale, "settings.groupFacts")} value={`${selectedAnalyticsStudyCount}/${analyticsStudies.length} ${t(siteLocale, "settings.enabledShort")}`} tone="gold" />
        <StatusPanel label={t(siteLocale, "settings.wallet")} value={walletConnected ? t(siteLocale, "settings.connected") : t(siteLocale, "settings.localDemo")} tone={walletConnected ? "teal" : "gold"} />
      </div>

      <Section title={t(siteLocale, "settings.personalInformation")}>
        <ProfileInformationForm profile={profile} setProfile={setProfile} siteLocale={siteLocale} />
      </Section>
      <GovernmentHelpSection
        siteLocale={siteLocale}
        requested={profile.servicePartnerHelpRequested}
        requestedAt={profile.servicePartnerHelpRequestedAt}
        onToggle={() => togglePartnerHelpRequest(profile, setProfile)}
      />

      <Section title={t(siteLocale, "settings.reminderPreferences")}>
        <div className="form-grid">
          <Field help={t(siteLocale, "settings.daysBetweenHelp")} label={t(siteLocale, "settings.daysBetween")} required>
            <input
              max={30}
              min={1}
              type="number"
              value={policy.intervalDays}
              onChange={(event) =>
                updatePolicy({ intervalDays: Math.max(1, Math.min(30, Number(event.target.value || 1))) })
              }
            />
          </Field>
          <Field help={t(siteLocale, "settings.extraHoursHelp")} label={t(siteLocale, "settings.extraHours")}>
            <input
              min={0}
              type="number"
              value={policy.gracePeriodHours}
              onChange={(event) => updatePolicy({ gracePeriodHours: Number(event.target.value || 0) })}
            />
          </Field>
        </div>
        <div className="channel-controls" role="group" aria-label={t(siteLocale, "settings.allowedMethods")}>
          {(["sms", "email", "web"] as CheckInChannel[]).map((channel) => (
            <button
              aria-pressed={policy.reminderChannels.includes(channel)}
              className="choice-chip channel-toggle"
              key={channel}
              onClick={() => toggleReminderChannel(channel)}
              type="button"
            >
              <span>{formatCheckInChannel(channel, siteLocale)} {t(siteLocale, "settings.allowedSuffix")}</span>
              <small>{policy.reminderChannels.includes(channel) ? t(siteLocale, "settings.on") : t(siteLocale, "settings.off")}</small>
            </button>
          ))}
        </div>
        <label className="scope-option settings-toggle">
          <input
            checked={policy.escalationEnabled}
            onChange={(event) => updatePolicy({ escalationEnabled: event.target.checked })}
            type="checkbox"
          />
          <span>
            <strong>{t(siteLocale, "settings.startNextStep")}</strong>
            <small>{t(siteLocale, "settings.nextScheduledCheckIn")}: {nextCheckIn}</small>
          </span>
        </label>
      </Section>

      <Section title={t(siteLocale, "settings.privacyChoices")}>
        <div className="settings-option-list">
          <label className="scope-option settings-toggle">
            <input checked={benefitsOptIn} onChange={(event) => setBenefitsOptIn(event.target.checked)} type="checkbox" />
            <span>
              <strong>{t(siteLocale, "settings.benefitsNotices")}</strong>
              <small>{t(siteLocale, "settings.benefitsNoticesHelp")}</small>
            </span>
          </label>
          {analyticsStudies.map((study) => {
            const selected = analyticsOptIn[study.id] ?? true;
            return (
              <label className="scope-option settings-toggle" key={study.id}>
                <input checked={selected} onChange={() => toggleAnalyticsStudy(study.id)} type="checkbox" />
                <span>
                  <strong>{study.title}</strong>
                  <small>{study.purpose}</small>
                </span>
              </label>
            );
          })}
          <label className="scope-option settings-toggle">
            <input
              checked={missingPersonDeadDropEnabled}
              onChange={(event) => setMissingPersonDeadDropEnabled(event.target.checked)}
              disabled={!walletDeadDropReady}
              type="checkbox"
            />
            <span>
              <strong>{t(siteLocale, "settings.deadDrop")}</strong>
              <small>
                {walletDeadDropReady
                  ? tFormat(siteLocale, "settings.deadDropEnabledHelp", { email: PORTLAND_POLICE_MISSING_EMAIL })
                  : t(siteLocale, "settings.deadDropDisabledHelp")}
              </small>
            </span>
          </label>
          <div className="row-actions">
            <Button
              ariaLabel={
                missingPersonDeadDropEnabled
                  ? t(siteLocale, "settings.deadDropPrepare")
                  : t(siteLocale, "settings.deadDropPrepareDisabled")
              }
              disabled={!missingPersonDeadDropEnabled || !walletDeadDropReady}
              onClick={handleSendMissingPersonDeadDrop}
              variant="secondary"
            >
              <Bell size={18} /> {t(siteLocale, "settings.deadDropPrepare")}
            </Button>
          </div>
          {deadDropStatus === "sent" ? (
            <StatusBanner tone="success">
              {t(siteLocale, "settings.deadDropPrepared")}
            </StatusBanner>
          ) : null}
          {deadDropStatus === "failed" ? (
            <StatusBanner tone="warning">{t(siteLocale, "settings.deadDropPrepareFailed")}</StatusBanner>
          ) : null}
        </div>
      </Section>

      <Section title={t(siteLocale, "settings.languageTitle")}>
        <p className="page-note">{t(siteLocale, "settings.languageHelp")}</p>
        <div className="form-grid">
          <Field label={t(siteLocale, "settings.browserLanguage")} help={t(siteLocale, "settings.browserLanguageHelp")}>
            <input readOnly type="text" value={getLocaleOptionLabel(browserLocale)} />
          </Field>
          <Field label={t(siteLocale, "settings.siteLanguage")}>
            <select value={siteLocale} onChange={(event) => setSiteLocale(normalizeSiteLocale(event.target.value))}>
              {SUPPORTED_LOCALES.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </Field>
          <Field label={t(siteLocale, "settings.assistantLanguage")}>
            <select value={assistantTranslationLocale} onChange={(event) => setAssistantTranslationLocale(event.target.value)}>
              {TRANSLATION_LOCALE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </Field>
        </div>
        <label className="scope-option settings-toggle">
          <input
            checked={assistantAutoTranslate}
            onChange={(event) => setAssistantAutoTranslate(event.target.checked)}
            type="checkbox"
          />
          <span>
            <strong>{t(siteLocale, "settings.autoTranslate")}</strong>
            <small>{t(siteLocale, "settings.autoTranslateHelp")}</small>
          </span>
        </label>
      </Section>

      <AccountSafetySection apiConfig={apiConfig} onSnapshotLoaded={onSnapshotLoaded} />

      <Section title={t(siteLocale, "settings.lessUsedTools")}>
        <div className="tool-grid">
          <button className="tool-tile" onClick={() => navigate("proof-center")} type="button">
            <ShieldCheck size={24} /> {t(siteLocale, "settings.proofSettings")}
          </button>
          <button className="tool-tile" onClick={() => navigate("audit")} type="button">
            <ClipboardCheck size={24} /> {t(siteLocale, "settings.consentHistory")}
          </button>
        </div>
      </Section>
    </div>
  );
}

function formatCheckInChannel(channel: CheckInChannel, locale: SupportedLocale): string {
  if (channel === "sms") return t(locale, "channel.sms");
  if (channel === "email") return t(locale, "channel.email");
  return t(locale, "channel.web");
}

function CheckInScreen({
  policy,
  profile,
  setPolicy,
  nextCheckIn,
  siteLocale
}: {
  policy: typeof defaultCheckInPolicy;
  profile: RegistrationProfileDraft;
  setPolicy: (policy: typeof defaultCheckInPolicy) => void;
  nextCheckIn: string;
  siteLocale: SupportedLocale;
}) {
  const [checkInMessage, setCheckInMessage] = useState<{ tone: "success" | "warning"; text: string } | null>(null);
  const update = (patch: Partial<typeof defaultCheckInPolicy>) => setPolicy({ ...policy, ...patch });
  const channelLabels: Record<CheckInChannel, string> = {
    sms: tFormat(siteLocale, "checkin.channelAllowed", { channel: formatCheckInChannel("sms", siteLocale) }),
    email: tFormat(siteLocale, "checkin.channelAllowed", { channel: formatCheckInChannel("email", siteLocale) }),
    web: tFormat(siteLocale, "checkin.channelAllowed", { channel: formatCheckInChannel("web", siteLocale) })
  };
  const checkInMethodLabels: Record<CheckInChannel, string> = {
    sms: t(siteLocale, "checkin.methodText"),
    email: t(siteLocale, "checkin.methodEmail"),
    web: t(siteLocale, "checkin.methodWeb")
  };
  const channelIsAllowed = (channel: CheckInChannel) => policy.reminderChannels.includes(channel);
  const toggleChannel = (channel: CheckInChannel) => {
    update({
      reminderChannels: policy.reminderChannels.includes(channel)
        ? policy.reminderChannels.filter((item) => item !== channel)
        : [...policy.reminderChannels, channel]
    });
    setCheckInMessage(null);
  };

  function checkInBy(channel: CheckInChannel) {
    if (!channelIsAllowed(channel)) {
      setCheckInMessage({
        tone: "warning",
        text:
          channel === "web"
            ? t(siteLocale, "checkin.webOff")
            : tFormat(siteLocale, "checkin.channelOff", { channel: formatCheckInChannel(channel, siteLocale) })
      });
      return;
    }

    if (channel === "sms" && !profile.phone.trim()) {
      setCheckInMessage({
        tone: "warning",
        text: t(siteLocale, "checkin.addPhone")
      });
      return;
    }

    if (channel === "email" && !profile.email.trim()) {
      setCheckInMessage({
        tone: "warning",
        text: t(siteLocale, "checkin.addEmail")
      });
      return;
    }

    update({ lastCheckInAt: new Date().toISOString() });
    setCheckInMessage({
      tone: "success",
      text: tFormat(siteLocale, "checkin.success", { method: checkInMethodLabels[channel] })
    });
  }

  return (
    <div className="screen">
      <div className="page-title">
        <p className="eyebrow">{t(siteLocale, "checkin.eyebrow")}</p>
        <h1>{t(siteLocale, "checkin.title")}</h1>
      </div>
      <StatusBanner tone="warning">{t(siteLocale, "checkin.warning")}</StatusBanner>
      <Section title={t(siteLocale, "checkin.schedule")}>
        <div className="form-grid">
          <Field help={t(siteLocale, "settings.daysBetweenHelp")} label={t(siteLocale, "settings.daysBetween")} required>
            <input
              max={30}
              min={1}
              type="number"
              value={policy.intervalDays}
              onChange={(event) =>
                update({ intervalDays: Math.max(1, Math.min(30, Number(event.target.value || 1))) })
              }
            />
          </Field>
          <Field help={t(siteLocale, "settings.extraHoursHelp")} label={t(siteLocale, "settings.extraHours")}>
            <input
              min={0}
              type="number"
              value={policy.gracePeriodHours}
              onChange={(event) => update({ gracePeriodHours: Number(event.target.value || 0) })}
            />
          </Field>
        </div>
        <p className="supporting-copy">{t(siteLocale, "checkin.methodsHelp")}</p>
        <div className="channel-controls" role="group" aria-label={t(siteLocale, "checkin.allowedMethods")}>
          {(["sms", "email", "web"] as CheckInChannel[]).map((channel) => (
            <button
              aria-pressed={policy.reminderChannels.includes(channel)}
              className="choice-chip channel-toggle"
              key={channel}
              onClick={() => toggleChannel(channel)}
              type="button"
            >
              <span>{channelLabels[channel]}</span>
              <small>{channelIsAllowed(channel) ? t(siteLocale, "settings.on") : t(siteLocale, "settings.off")}</small>
            </button>
          ))}
        </div>
        {!policy.reminderChannels.length ? (
          <StatusBanner tone="warning">{t(siteLocale, "checkin.noneEnabled")}</StatusBanner>
        ) : null}
        <div className="schedule-preview">
          <CalendarCheck aria-hidden="true" size={28} />
          <div>
            <small>{t(siteLocale, "home.nextCheckIn")}</small>
            <strong>{nextCheckIn}</strong>
          </div>
        </div>
        {checkInMessage ? <StatusBanner tone={checkInMessage.tone}>{checkInMessage.text}</StatusBanner> : null}
        <div className="method-checkin-grid" role="group" aria-label={t(siteLocale, "checkin.checkInNow")}>
          {(["sms", "email", "web"] as CheckInChannel[]).map((channel) => {
            const allowed = channelIsAllowed(channel);
            return (
              <Button key={channel} onClick={() => checkInBy(channel)} variant={allowed ? "primary" : "secondary"}>
                <Bell size={18} /> {tFormat(siteLocale, "checkin.byMethod", { method: checkInMethodLabels[channel] })}{allowed ? "" : ` ${t(siteLocale, "checkin.offSuffix")}`}
              </Button>
            );
          })}
        </div>
      </Section>
    </div>
  );
}

function toggleScopeSelection(scopes: DisclosureDataScope[], scope: DisclosureDataScope): DisclosureDataScope[] {
  return scopes.includes(scope) ? scopes.filter((item) => item !== scope) : [...scopes, scope];
}

function SharingScopeChecklist({
  label,
  scopes,
  onToggle,
  help,
  siteLocale
}: {
  label: string;
  scopes: DisclosureDataScope[];
  onToggle: (scope: DisclosureDataScope) => void;
  help?: string;
  siteLocale: SupportedLocale;
}) {
  return (
    <fieldset className="scope-fieldset">
      <legend>{label}</legend>
      {help ? <p className="scope-help">{help}</p> : null}
      <div className="scope-grid">
        {disclosureScopes.map((scope) => (
          <label className="scope-option" key={scope.id}>
            <input checked={scopes.includes(scope.id)} onChange={() => onToggle(scope.id)} type="checkbox" />
            <span>
              <strong>{t(siteLocale, disclosureScopeLabelKey(scope.id))}</strong>
              <small>{t(siteLocale, disclosureScopeDetailKey(scope.id))}</small>
            </span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}

function getDisclosureScopeLabels(scopes: DisclosureDataScope[], locale: SupportedLocale): string {
  return scopes.map((scope) => t(locale, disclosureScopeLabelKey(scope))).join(", ");
}

function SharingCapabilityPreview({ recipientName, scopes, siteLocale }: { recipientName: string; scopes: DisclosureDataScope[]; siteLocale: SupportedLocale }) {
  const abilities = abilitiesForDisclosureScopes(scopes);

  return (
    <div className="capability-preview" role="group" aria-label={tFormat(siteLocale, "contacts.editSharingFor", { name: recipientName })}>
      <div className="scope-header">
        <div>
          <h4>{t(siteLocale, "sharing.whatAllows")}</h4>
          <p>{tFormat(siteLocale, "sharing.selectedItems", { count: String(scopes.length) })}</p>
        </div>
        <Badge tone={scopes.length > 0 ? "success" : "warning"}>{scopes.length > 0 ? t(siteLocale, "sharing.limitedShare") : t(siteLocale, "sharing.noAccess")}</Badge>
      </div>
      <div className="disclosure-package">
        <div className="disclosure-row">
          <strong>{t(siteLocale, "sharing.canDo")}</strong>
          <span>{formatLocalizedCapabilitySummary(abilities, siteLocale) || t(siteLocale, "sharing.noAccessSelected")}</span>
        </div>
        <div className="disclosure-row">
          <strong>{t(siteLocale, "sharing.items")}</strong>
          <span>{getDisclosureScopeLabels(scopes, siteLocale) || t(siteLocale, "sharing.noItemsSelected")}</span>
        </div>
        <div className="disclosure-row">
          <strong>{t(siteLocale, "sharing.notAllowed")}</strong>
          <span>{formatLocalizedNonGrantedCapabilities(abilities, siteLocale)}</span>
        </div>
      </div>
    </div>
  );
}

function ClientMessagesScreen({
  profile,
  providerMessages,
  setProviderMessages,
  siteLocale,
  signedInUser
}: {
  profile: RegistrationProfileDraft;
  providerMessages: ShelterProviderMessage[];
  setProviderMessages: (messages: ShelterProviderMessage[]) => void;
  siteLocale: SupportedLocale;
  signedInUser: string;
}) {
  const [messageFilter, setMessageFilter] = useState<"inbox" | "unread" | "archived" | "all">("inbox");
  const clientMessages = providerMessages
    .filter((message) => messageMatchesClient(message, profile, signedInUser))
    .sort((left, right) => new Date(right.createdAt).getTime() - new Date(left.createdAt).getTime());
  const inboxMessages = clientMessages.filter((message) => !message.clientArchivedAt);
  const unreadMessages = inboxMessages.filter((message) => !message.clientReadAt);
  const archivedMessages = clientMessages.filter((message) => message.clientArchivedAt);
  const visibleMessages =
    messageFilter === "unread"
      ? unreadMessages
      : messageFilter === "archived"
        ? archivedMessages
        : messageFilter === "all"
          ? clientMessages
          : inboxMessages;

  function updateMessage(messageId: string, patch: Partial<ShelterProviderMessage>) {
    setProviderMessages(
      providerMessages.map((message) => (message.id === messageId ? { ...message, ...patch } : message))
    );
  }

  function markMessageRead(message: ShelterProviderMessage) {
    updateMessage(message.id, { clientReadAt: message.clientReadAt ? undefined : new Date().toISOString() });
  }

  function toggleMessageArchive(message: ShelterProviderMessage) {
    updateMessage(message.id, {
      clientArchivedAt: message.clientArchivedAt ? undefined : new Date().toISOString(),
      clientReadAt: message.clientReadAt ?? new Date().toISOString()
    });
  }

  return (
    <div className="screen client-messages-screen">
      <div className="page-title">
        <p className="eyebrow">{t(siteLocale, "portal.client")}</p>
        <h1>{t(siteLocale, "messages.title")}</h1>
      </div>
      <p className="page-note">{t(siteLocale, "messages.note")}</p>
      <Section title={t(siteLocale, "messages.summary")}>
        <div className="dashboard-grid">
          <StatusPanel label={t(siteLocale, "messages.inbox")} value={String(inboxMessages.length)} tone="teal" />
          <StatusPanel label={t(siteLocale, "messages.unread")} value={String(unreadMessages.length)} tone="gold" />
          <StatusPanel label={t(siteLocale, "messages.archived")} value={String(archivedMessages.length)} tone="teal" />
        </div>
      </Section>
      <Section title={t(siteLocale, "messages.staffMessages")}>
        <div className="message-toolbar">
          <Field label={t(siteLocale, "messages.view")}>
            <select value={messageFilter} onChange={(event) => setMessageFilter(event.target.value as typeof messageFilter)}>
              <option value="inbox">{t(siteLocale, "messages.inbox")}</option>
              <option value="unread">{t(siteLocale, "messages.unread")}</option>
              <option value="archived">{t(siteLocale, "messages.archived")}</option>
              <option value="all">{t(siteLocale, "messages.all")}</option>
            </select>
          </Field>
        </div>
        <div className="list-stack client-message-list">
          {visibleMessages.length ? (
            visibleMessages.map((message) => (
              <article className="list-item client-message-item" key={message.id}>
                <div>
                  <h3>{message.subject}</h3>
                  <p>{message.body}</p>
                  <div className="badge-row">
                    <Badge>{message.shelter}</Badge>
                    <Badge>{message.staffName}</Badge>
                    <Badge>{formatProviderMessageChannel(message.channel, siteLocale)}</Badge>
                    <Badge tone={message.clientReadAt ? "neutral" : "warning"}>
                      {message.clientReadAt ? t(siteLocale, "messages.read") : t(siteLocale, "messages.unread")}
                    </Badge>
                    <Badge>{formatShelterDate(message.createdAt)}</Badge>
                  </div>
                  <small>{tFormat(siteLocale, "messages.sentTo", { contact: message.clientContact })}</small>
                </div>
                <div className="row-actions">
                  <Button onClick={() => markMessageRead(message)} variant="secondary">
                    {message.clientReadAt ? t(siteLocale, "messages.markUnread") : t(siteLocale, "messages.markRead")}
                  </Button>
                  <Button onClick={() => toggleMessageArchive(message)} variant="secondary">
                    {message.clientArchivedAt ? t(siteLocale, "messages.restore") : t(siteLocale, "messages.archive")}
                  </Button>
                </div>
              </article>
            ))
          ) : (
            <div className="empty-state">
              <h3>{t(siteLocale, "messages.emptyTitle")}</h3>
              <p>{t(siteLocale, "messages.emptyBody")}</p>
            </div>
          )}
        </div>
      </Section>
    </div>
  );
}

function formatProviderMessageChannel(channel: ShelterProviderMessage["channel"], locale: SupportedLocale): string {
  if (channel === "sms") return t(locale, "channel.sms");
  if (channel === "email") return t(locale, "channel.email");
  return t(locale, "messages.inApp");
}

function messageMatchesClient(
  message: ShelterProviderMessage,
  profile: RegistrationProfileDraft,
  signedInUser: string
): boolean {
  const profileKeys = [profile.phone, profile.email, profile.preferredName, profile.legalName]
    .map(normalizeClientMessageKey)
    .filter(Boolean);
  const loginContact = signedInUser.startsWith("client:") ? signedInUser.slice("client:".length) : signedInUser;
  const loginKey = normalizeClientMessageKey(loginContact);
  const messageKeys = [message.clientContact, message.clientName].map(normalizeClientMessageKey).filter(Boolean);

  if (loginKey && messageKeys.some((key) => key.includes(loginKey) || loginKey.includes(key))) return true;
  if (profileKeys.length && profileKeys.some((profileKey) => messageKeys.some((key) => key.includes(profileKey)))) {
    return true;
  }
  return signedInUser === "abby" && normalizeClientMessageKey(message.clientName).includes("abby");
}

function normalizeClientMessageKey(value: string): string {
  const trimmed = value.trim().toLowerCase();
  if (!trimmed) return "";
  if (trimmed.includes("@")) return trimmed;
  const digits = trimmed.replace(/\D/g, "");
  return digits.length >= 7 ? digits : trimmed.replace(/[^a-z0-9]+/g, " ");
}

function ContactsScreen({
  contactRequests,
  profile,
  recipients,
  siteLocale,
  setContactRequests,
  setRecipients
}: {
  contactRequests: ShelterContactRequest[];
  profile: RegistrationProfileDraft;
  recipients: DisclosureRecipientDraft[];
  siteLocale: SupportedLocale;
  setContactRequests: (requests: ShelterContactRequest[]) => void;
  setRecipients: (recipients: DisclosureRecipientDraft[]) => void;
}) {
  const [contactCategory, setContactCategory] = useState<"person" | "shelter">("person");
  const [providerType, setProviderType] = useState<"shelter" | "police_precinct">("shelter");
  const [draft, setDraft] = useState({
    firstName: "",
    lastName: "",
    relationship: "",
    email: "",
    phone: "",
    type: "emergency_contact" as DisclosureRecipientType
  });
  const [draftScopes, setDraftScopes] = useState<DisclosureDataScope[]>([...defaultDisclosureScopes]);
  const [editingRecipientId, setEditingRecipientId] = useState<string | null>(null);
  const [editingScopes, setEditingScopes] = useState<DisclosureDataScope[]>([]);
  const [requestedShelter, setRequestedShelter] = useState(shelterOptions[0]);
  const [requestedPrecinct, setRequestedPrecinct] = useState(LOCAL_PRECINCT_OPTIONS[0]);

  const userName = profile.preferredName || profile.legalName || "Abby Example";
  const userContact = [profile.phone, profile.email].map((item) => item.trim()).filter(Boolean).join(" / ");
  const requestBelongsToCurrentUser = (request: ShelterContactRequest) =>
    request.userName.trim().toLowerCase() === userName.trim().toLowerCase() ||
    request.userContact.trim().toLowerCase() === userContact.trim().toLowerCase();
  const userShelterRequests = contactRequests.filter(requestBelongsToCurrentUser);
  const incomingShelterNudges = contactRequests.filter(
    (request) =>
      request.direction === "shelter_to_user" && request.status === "pending" && requestBelongsToCurrentUser(request)
  );
  const hasPendingRequestedShelter = contactRequests.some(
    (request) =>
      request.direction === "user_to_shelter" &&
      request.status === "pending" &&
      request.shelterName === requestedShelter &&
      requestBelongsToCurrentUser(request)
  );
  const hasSavedRequestedPrecinct = recipients.some((recipient) => isLocalPrecinctRecipient(recipient, requestedPrecinct));
  const editingRecipient = recipients.find((recipient) => recipient.id === editingRecipientId) ?? null;

  function addShelterRecipient(shelterName: string) {
    if (recipients.some((recipient) => recipient.type === "shelter_staff" && recipient.agencyName === shelterName)) {
      return;
    }

    setRecipients([
      ...recipients,
      {
        id: createEntityId("rec"),
        type: "shelter_staff",
        displayName: shelterName,
        relationship: "Shelter",
        email: "",
        phone: "",
        agencyName: shelterName,
        precinctName: "",
        verified: true,
        allowedScopes: ["identity_minimum"]
      }
    ]);
  }

  function addRecipient(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!draft.firstName) return;
    const displayName = [draft.firstName, draft.lastName].filter(Boolean).join(" ");
    setRecipients([
      ...recipients,
      {
        id: createEntityId("rec"),
        displayName,
        relationship: draft.relationship,
        email: draft.email,
        phone: draft.phone,
        type: draft.type,
        agencyName: "",
        precinctName: "",
        verified: false,
        allowedScopes: [...draftScopes]
      }
    ]);
    setDraft({ firstName: "", lastName: "", relationship: "", email: "", phone: "", type: "emergency_contact" });
    setDraftScopes([...defaultDisclosureScopes]);
  }

  function addPrecinctRecipient(precinctName: string) {
    if (recipients.some((recipient) => isLocalPrecinctRecipient(recipient, precinctName))) {
      return;
    }

    setRecipients([
      ...recipients,
      {
        id: createEntityId("rec"),
        type: "police_precinct",
        displayName: precinctName,
        relationship: LOCAL_PRECINCT_RELATIONSHIP,
        email: "",
        phone: "",
        agencyName: "",
        precinctName,
        verified: true,
        allowedScopes: ["identity_minimum"]
      }
    ]);
  }

  function openRecipientEditor(recipient: DisclosureRecipientDraft) {
    setEditingRecipientId(recipient.id);
    setEditingScopes([...recipient.allowedScopes]);
    window.setTimeout(() => document.getElementById(`recipient-edit-${recipient.id}`)?.focus(), 0);
  }

  function closeRecipientEditor(recipientId: string) {
    setEditingRecipientId(null);
    setEditingScopes([]);
    window.setTimeout(() => document.getElementById(`recipient-open-${recipientId}`)?.focus(), 0);
  }

  function saveRecipientScopes(recipientId: string) {
    setRecipients(
      recipients.map((recipient) =>
        recipient.id === recipientId ? { ...recipient, allowedScopes: [...editingScopes] } : recipient
      )
    );
    closeRecipientEditor(recipientId);
  }

  function removeRecipient(recipientId: string) {
    setRecipients(recipients.filter((item) => item.id !== recipientId));
    if (editingRecipientId === recipientId) {
      setEditingRecipientId(null);
      setEditingScopes([]);
    }
  }

  function requestShelterContact(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (hasPendingRequestedShelter) return;

    setContactRequests([
      ...contactRequests,
      {
        id: `shelter-request-${Date.now()}`,
        direction: "user_to_shelter",
        status: "pending",
        shelterName: requestedShelter,
        userName,
        userContact,
        createdAt: new Date().toISOString()
      }
    ]);
  }

  function decideShelterNudge(requestId: string, status: "approved" | "denied") {
    const request = contactRequests.find((item) => item.id === requestId);
    if (!request) return;

    if (status === "approved") {
      addShelterRecipient(request.shelterName);
    }

    setContactRequests(
      contactRequests.map((item) =>
        item.id === requestId ? { ...item, status, decidedAt: new Date().toISOString() } : item
      )
    );
  }

  function cancelShelterRequest(requestId: string) {
    setContactRequests(
      contactRequests.map((item) =>
        item.id === requestId && item.direction === "user_to_shelter" && item.status === "pending"
          ? { ...item, status: "canceled", decidedAt: new Date().toISOString() }
          : item
      )
    );
  }

  return (
    <div className="screen">
      <div className="page-title">
        <p className="eyebrow">{t(siteLocale, "contacts.eyebrow")}</p>
        <h1>{t(siteLocale, "contacts.title")}</h1>
      </div>
      <p className="page-note">{t(siteLocale, "contacts.note")}</p>
      <Section title={t(siteLocale, "contacts.addContact")}>
        <div className="contact-type-toggle">
          <label className={`contact-type-option${contactCategory === "person" ? " contact-type-option--active" : ""}`}>
            <input
              checked={contactCategory === "person"}
              name="contactCategory"
              onChange={() => setContactCategory("person")}
              type="radio"
              value="person"
            />
            {t(siteLocale, "contacts.person")}
          </label>
          <label className={`contact-type-option${contactCategory === "shelter" ? " contact-type-option--active" : ""}`}>
            <input
              checked={contactCategory === "shelter"}
              name="contactCategory"
              onChange={() => setContactCategory("shelter")}
              type="radio"
              value="shelter"
            />
            {t(siteLocale, "contacts.shelterGroup")}
          </label>
        </div>
        {contactCategory === "person" ? (
          <form className="form-grid" onSubmit={addRecipient}>
            <Field label={t(siteLocale, "contacts.firstName")} required>
              <input value={draft.firstName} onChange={(event) => setDraft({ ...draft, firstName: event.target.value })} />
            </Field>
            <Field label={t(siteLocale, "contacts.lastName")}>
              <input value={draft.lastName} onChange={(event) => setDraft({ ...draft, lastName: event.target.value })} />
            </Field>
            <Field label={t(siteLocale, "contacts.relationshipRole")}>
              <input value={draft.relationship} onChange={(event) => setDraft({ ...draft, relationship: event.target.value })} />
            </Field>
            <Field label={t(siteLocale, "contacts.phone")}>
              <input value={draft.phone} onChange={(event) => setDraft({ ...draft, phone: event.target.value })} />
            </Field>
            <Field label={t(siteLocale, "contacts.email")}>
              <input type="email" value={draft.email} onChange={(event) => setDraft({ ...draft, email: event.target.value })} />
            </Field>
            <Field label={t(siteLocale, "contacts.type")}>
              <select
                value={draft.type}
                onChange={(event) => setDraft({ ...draft, type: event.target.value as DisclosureRecipientType })}
              >
                <option value="emergency_contact">{t(siteLocale, "contacts.recipientType.emergency_contact")}</option>
                <option value="social_worker">{t(siteLocale, "contacts.recipientType.social_worker")}</option>
                <option value="police_precinct">{t(siteLocale, "contacts.recipientType.police_precinct")}</option>
                <option value="government_liaison">{t(siteLocale, "contacts.recipientType.government_liaison")}</option>
                <option value="benefits_agency">{t(siteLocale, "contacts.recipientType.benefits_agency")}</option>
              </select>
            </Field>
            <SharingScopeChecklist
              help={t(siteLocale, "contacts.scopeHelp")}
              label={t(siteLocale, "contacts.scopeForPerson")}
              onToggle={(scope) => setDraftScopes(toggleScopeSelection(draftScopes, scope))}
              scopes={draftScopes}
              siteLocale={siteLocale}
            />
            <div className="full-span centered-action">
              <Button type="submit">
                <UsersRound aria-hidden="true" size={18} /> {t(siteLocale, "contacts.addPerson")}
              </Button>
            </div>
          </form>
        ) : (
          <>
            <p className="section-note">
              {providerType === "shelter"
                ? t(siteLocale, "contacts.providerNoteShelter")
                : t(siteLocale, "contacts.providerNotePrecinct")}
            </p>
            <form
              className="form-grid"
              onSubmit={(event) => {
                if (providerType === "shelter") {
                  requestShelterContact(event);
                  return;
                }
                event.preventDefault();
                addPrecinctRecipient(requestedPrecinct);
              }}
            >
              <Field label={t(siteLocale, "contacts.providerType")}>
                <select
                  value={providerType}
                  onChange={(event) => setProviderType(event.target.value as "shelter" | "police_precinct")}
                >
                  <option value="shelter">{t(siteLocale, "contacts.shelterGroup")}</option>
                  <option value="police_precinct">{t(siteLocale, "contacts.defaultPrecinct")}</option>
                </select>
              </Field>
              <Field label={providerType === "shelter" ? t(siteLocale, "contacts.shelterName") : t(siteLocale, "contacts.localPrecinct")}>
                <select
                  value={providerType === "shelter" ? requestedShelter : requestedPrecinct}
                  onChange={(event) =>
                    providerType === "shelter"
                      ? setRequestedShelter(event.target.value)
                      : setRequestedPrecinct(event.target.value)
                  }
                >
                  {(providerType === "shelter" ? shelterOptions : LOCAL_PRECINCT_OPTIONS).map((providerName) => (
                    <option key={providerName} value={providerName}>
                      {providerType === "shelter" ? providerName : localizedPrecinctName(providerName, siteLocale)}
                    </option>
                  ))}
                </select>
              </Field>
              <div className="full-span centered-action">
                <Button
                  disabled={providerType === "shelter" ? hasPendingRequestedShelter : hasSavedRequestedPrecinct}
                  type="submit"
                  variant="secondary"
                >
                  <MessageSquare aria-hidden="true" size={18} />{" "}
                  {providerType === "shelter" ? t(siteLocale, "contacts.askAddShelter") : t(siteLocale, "contacts.addLocalPrecinct")}
                </Button>
              </div>
              {(providerType === "shelter" ? hasPendingRequestedShelter : hasSavedRequestedPrecinct) ? (
                <small className="full-span pin-request-note">
                  {providerType === "shelter"
                    ? t(siteLocale, "contacts.pendingShelterRequest")
                    : t(siteLocale, "contacts.savedPrecinctExists")}
                </small>
              ) : null}
            </form>
            <div className="list-stack">
              {incomingShelterNudges.map((request) => (
                <article className="list-item access-request-item" key={request.id}>
                  <div>
                    <h3>{request.shelterName}</h3>
                    <p>{tFormat(siteLocale, "contacts.staffAsked", { staff: request.staffName || t(siteLocale, "contacts.defaultStaffName") })}</p>
                    <Badge>{formatContactRequestStatus(request.status, siteLocale)}</Badge>
                  </div>
                  <div className="row-actions">
                    <Button onClick={() => decideShelterNudge(request.id, "approved")} variant="secondary">
                      {t(siteLocale, "contacts.approve")}
                    </Button>
                    <Button onClick={() => decideShelterNudge(request.id, "denied")} variant="danger">
                      {t(siteLocale, "contacts.deny")}
                    </Button>
                  </div>
                </article>
              ))}
              {userShelterRequests.map((request) => (
                <article className="list-item" key={`status-${request.id}`}>
                  <div>
                    <h3>{request.shelterName}</h3>
                    <p>{request.direction === "user_to_shelter" ? t(siteLocale, "contacts.youAskedShelter") : t(siteLocale, "contacts.shelterAskedYou")}</p>
                  </div>
                  <div className="row-actions">
                    <Badge tone={request.status === "approved" ? "success" : request.status === "denied" ? "warning" : "neutral"}>
                      {formatContactRequestStatus(request.status, siteLocale)}
                    </Badge>
                    {request.direction === "user_to_shelter" && request.status === "pending" ? (
                      <Button onClick={() => cancelShelterRequest(request.id)} variant="secondary">
                        {t(siteLocale, "contacts.cancel")}
                      </Button>
                    ) : null}
                  </div>
                </article>
              ))}
            </div>
          </>
        )}
      </Section>
      <Section title={t(siteLocale, "contacts.savedContacts")}>
        {recipients.length === 0 ? (
          <p className="empty-state">{t(siteLocale, "contacts.emptySavedContacts")}</p>
        ) : (
          <>
            <div className="list-stack">
              {recipients.map((recipient) => {
                const isEditing = editingRecipient?.id === recipient.id;

                return (
                  <article className="list-item recipient-list-item" key={recipient.id}>
                    <div className="recipient-row">
                      <button
                        aria-controls={`recipient-edit-${recipient.id}`}
                        aria-expanded={isEditing}
                        aria-label={tFormat(siteLocale, "contacts.editSharingFor", { name: recipient.displayName })}
                        className="recipient-open-button"
                        id={`recipient-open-${recipient.id}`}
                        onClick={() => openRecipientEditor(recipient)}
                        type="button"
                      >
                        <span className="recipient-summary">
                          <span className="recipient-name">{recipient.displayName}</span>
                          <span className="recipient-details">
                            <span>{localizedRelationshipName(recipient.relationship || recipient.agencyName || formatRecipientType(recipient.type, siteLocale), siteLocale)}</span>
                            {recipient.email ? <span>{recipient.email}</span> : null}
                            {recipient.phone ? <span>{recipient.phone}</span> : null}
                          </span>
                          <span className="badge-row" aria-label={`${recipient.displayName} status`}>
                            <Badge tone={recipient.verified ? "success" : "warning"}>
                              {recipient.verified ? t(siteLocale, "contacts.verified") : t(siteLocale, "contacts.needsCheck")}
                            </Badge>
                            <Badge>{recipient.allowedScopes.length} {t(siteLocale, "contacts.items")}</Badge>
                          </span>
                        </span>
                      </button>
                      <div className="row-actions">
                        <Button
                          ariaControls={`recipient-edit-${recipient.id}`}
                          ariaExpanded={isEditing}
                          className="compact-list-action"
                          onClick={() => openRecipientEditor(recipient)}
                          variant="secondary"
                        >
                          {t(siteLocale, "contacts.editSharing")}
                        </Button>
                        <Button
                          ariaLabel={`${t(siteLocale, "contacts.remove")} ${recipient.displayName}`}
                          className="compact-list-action"
                          onClick={() => removeRecipient(recipient.id)}
                          variant="quiet"
                        >
                          {t(siteLocale, "contacts.remove")}
                        </Button>
                      </div>
                    </div>
                  </article>
                );
              })}
            </div>
            {editingRecipient ? (
              <div
                aria-labelledby={`recipient-edit-heading-${editingRecipient.id}`}
                className="recipient-edit-panel"
                id={`recipient-edit-${editingRecipient.id}`}
                role="region"
                tabIndex={-1}
              >
                <div className="scope-header">
                  <div>
                    <h3 id={`recipient-edit-heading-${editingRecipient.id}`}>
                      {tFormat(siteLocale, "contacts.editSharingFor", { name: editingRecipient.displayName })}
                    </h3>
                    <p>{t(siteLocale, "contacts.saveOnlyWhatContactShouldSee")}</p>
                  </div>
                  <Badge>{editingScopes.length} {t(siteLocale, "contacts.selected")}</Badge>
                </div>
                <SharingScopeChecklist
                  label={tFormat(siteLocale, "contacts.scopeForName", { name: editingRecipient.displayName })}
                  onToggle={(scope) => setEditingScopes(toggleScopeSelection(editingScopes, scope))}
                  scopes={editingScopes}
                  siteLocale={siteLocale}
                />
                <SharingCapabilityPreview recipientName={editingRecipient.displayName} scopes={editingScopes} siteLocale={siteLocale} />
                <div className="row-actions">
                  <Button onClick={() => saveRecipientScopes(editingRecipient.id)}>{t(siteLocale, "contacts.saveSharing")}</Button>
                  <Button onClick={() => closeRecipientEditor(editingRecipient.id)} variant="secondary">
                    {t(siteLocale, "contacts.cancel")}
                  </Button>
                </div>
              </div>
            ) : null}
          </>
        )}
      </Section>
    </div>
  );
}

function UploadsScreen({
  apiBaseUrl,
  apiConfig,
  bundles,
  proofs,
  refreshWalletAuditEvents,
  recipients,
  setApiConfig,
  setBundles,
  siteLocale,
  signedInUser,
  uploads,
  setUploads
}: {
  apiBaseUrl?: string;
  apiConfig?: WalletApiConfig;
  bundles: ExportBundleView[];
  proofs: ProofReceiptView[];
  refreshWalletAuditEvents: () => Promise<void>;
  recipients: DisclosureRecipientDraft[];
  setApiConfig: (config: WalletApiConfig) => void;
  setBundles: (bundles: ExportBundleView[]) => void;
  siteLocale: SupportedLocale;
  signedInUser: string;
  uploads: UploadItem[];
  setUploads: (uploads: UploadItem[]) => void;
}) {
  const [repairingUploadIds, setRepairingUploadIds] = useState<string[]>([]);
  const [filecoinUploadIds, setFilecoinUploadIds] = useState<string[]>([]);
  const [downloadingUploadIds, setDownloadingUploadIds] = useState<string[]>([]);
  const [deletingUploadIds, setDeletingUploadIds] = useState<string[]>([]);
  const [walletFileQuery, setWalletFileQuery] = useState("");
  const [walletFileFilter, setWalletFileFilter] = useState<WalletFileFilterMode>("all");
  const [walletFileSort, setWalletFileSort] = useState<WalletFileSortMode>("newest");
  const [storeNewFilesOnFilecoin, setStoreNewFilesOnFilecoin] = useState(true);
  const uploadsRef = useRef(uploads);
  const filecoinStorageConfig = useMemo(() => getFilecoinStorageConfig(), []);
  const filecoinStorageReady = Boolean(filecoinStorageConfig);
  const verifiedRecipients = recipients.filter((recipient) => recipient.verified);
  const [walletQrCodeUrl, setWalletQrCodeUrl] = useState("");
  const [walletQrStatus, setWalletQrStatus] = useState<"loading" | "ready" | "failed">("loading");
  const [walletProofBundleCid, setWalletProofBundleCid] = useState("");
  const [walletPublishedProofReviewUrl, setWalletPublishedProofReviewUrl] = useState("");
  const [walletCreateStatus, setWalletCreateStatus] = useState<"idle" | "creating" | "created" | "failed">("idle");
  const [walletCreateError, setWalletCreateError] = useState("");
  const [recoveryPassphrase, setRecoveryPassphrase] = useState("");
  const [recoveryStatus, setRecoveryStatus] = useState<"idle" | "saving" | "unlocking" | "ready" | "failed">("idle");
  const [recoveryMessage, setRecoveryMessage] = useState("");
  const [recoveryQrCodeUrl, setRecoveryQrCodeUrl] = useState("");
  const [recoveryQrPayloadLabel, setRecoveryQrPayloadLabel] = useState("");
  const walletQrProofs = useMemo(() => visibleProofCenterProofs(proofs), [proofs]);
  const walletProofBundlePayload = useMemo(
    () => buildWalletProofBundlePayload({ actorDid: apiConfig?.actorDid, proofs: walletQrProofs, walletId: apiConfig?.walletId }),
    [apiConfig?.actorDid, apiConfig?.walletId, walletQrProofs]
  );
  const walletProofBundleReference = walletProofBundleCid ? `ipfs://${walletProofBundleCid}` : walletProofBundlePayload;
  const walletProofReviewUrl = useMemo(
    () => buildWalletProofReviewUrl(walletProofBundleReference),
    [walletProofBundleReference]
  );
  const walletProofReviewHref = walletPublishedProofReviewUrl || walletProofReviewUrl;
  const walletQrPayloadLabel = filecoinStorageReady
    ? walletProofBundleCid || t(siteLocale, "wallet.publishingCid")
    : t(siteLocale, "wallet.connectStorageCid");
  const walletFileFilterOptions = getWalletFileFilterOptions(siteLocale);
  const visibleUploads = useMemo(
    () => searchWalletFiles(uploads, walletFileQuery, walletFileSort, walletFileFilter),
    [uploads, walletFileFilter, walletFileQuery, walletFileSort]
  );
  const walletFileStats = useMemo(() => buildWalletFileStats(uploads), [uploads]);

  useEffect(() => {
    uploadsRef.current = uploads;
  }, [uploads]);

  useEffect(() => {
    if (!apiConfig?.actorDid) return;
    uploads
      .filter((upload) => upload.recordId && (!upload.privacyProfileStatus || upload.privacyProfileNeedsRefresh))
      .forEach((upload) => {
        void profileWalletUpload(upload);
      });
  }, [apiConfig?.actorDid, uploads]);

  useEffect(() => {
    let cancelled = false;
    if (!filecoinStorageConfig) {
      setWalletProofBundleCid("");
      setWalletPublishedProofReviewUrl("");
      if (walletProofReviewUrl.length <= 2500) {
        setWalletQrStatus("loading");
        void QRCode.toDataURL(walletProofReviewUrl, {
          errorCorrectionLevel: "M",
          margin: 1,
          width: 220
        })
          .then((qrCodeUrl) => {
            if (!cancelled) {
              setWalletQrCodeUrl(qrCodeUrl);
              setWalletQrStatus("ready");
            }
          })
          .catch(() => {
            if (!cancelled) {
              setWalletQrCodeUrl("");
              setWalletQrStatus("failed");
            }
          });
      } else {
        setWalletQrCodeUrl("");
        setWalletQrStatus("failed");
      }
      return () => {
        cancelled = true;
      };
    }

    setWalletQrStatus("loading");
    const walletRecordLinks: WalletEncryptedRecordLink[] = uploads
      .filter((upload) => upload.recordId && upload.ipfsCid)
      .map((upload) => ({
        cid: upload.ipfsCid!,
        fileName: upload.fileName,
        links: upload.ipldLinks?.length
          ? upload.ipldLinks
          : [{ "/": upload.ipfsCid!, cid: upload.ipfsCid!, name: "encrypted_record" }],
        recordId: upload.recordId,
        root: upload.ipfsRootCid ? { "/": upload.ipfsRootCid } : { "/": upload.ipfsCid! }
      }));
    void Promise.resolve(walletRecordLinks)
      .then((recordLinks) =>
        uploadProofBundleToFilecoinStorage(
          buildWalletProofBundlePayload({
            actorDid: apiConfig?.actorDid,
            encryptedRecordLinks: recordLinks.filter((link): link is WalletEncryptedRecordLink => Boolean(link)),
            proofs: walletQrProofs,
            walletId: apiConfig?.walletId
          }),
          {
            clientConfig: filecoinStorageConfig,
            walletConfig: apiConfig
          }
        )
      )
      .then(async (result) => {
        const cid = result.ipfsCid || result.cid;
        if (!cid) throw new Error("The storage backend did not return a CID. Verify the IPFS/Filecoin storage configuration.");
        const nextReviewUrl = buildWalletProofReviewUrl(`ipfs://${cid}`);
        const nextQrCodeUrl = await QRCode.toDataURL(nextReviewUrl, {
          errorCorrectionLevel: "M",
          margin: 1,
          width: 220
        });
        if (!cancelled) {
          setWalletProofBundleCid(cid);
          setWalletPublishedProofReviewUrl(nextReviewUrl);
          setWalletQrCodeUrl(nextQrCodeUrl);
          setWalletQrStatus("ready");
        }
      })
      .catch(() => {
        if (!cancelled) {
          setWalletProofBundleCid("");
          setWalletQrCodeUrl("");
          setWalletPublishedProofReviewUrl("");
          setWalletQrStatus("failed");
        }
      });

    return () => {
      cancelled = true;
    };
  }, [apiConfig, filecoinStorageConfig, uploads, walletProofReviewUrl, walletQrProofs]);

  async function addUpload(file: File | null) {
    if (!file) return;
    const machineSummary = await generateUploadSummary(file);
    if (apiConfig?.actorDid) {
      try {
        const uploaded = normalizeWalletUpload(await addBinaryDocument(apiConfig, { file, title: machineSummary }), file.name);
        prependUpload(uploaded);
        await refreshWalletAuditEvents();
        void persistUploadMetadata(uploaded, {
          fileName: file.name,
          machineSummary,
          privacyProfileMimeType: file.type || "application/octet-stream",
          privacyProfileNeedsRefresh: true,
          privacyProfileStatus: "not_started"
        });
        void profileWalletUpload(uploaded, file);
        if (storeNewFilesOnFilecoin) {
          void storeWalletRecordOnFilecoin(uploaded);
        }
        return;
      } catch {
        try {
          const uploaded = normalizeWalletUpload(await addTextDocument(apiConfig, {
            filename: file.name,
            text: await file.text(),
            title: machineSummary
          }), file.name);
          prependUpload(uploaded);
          await refreshWalletAuditEvents();
          void persistUploadMetadata(uploaded, {
            fileName: file.name,
            machineSummary,
            privacyProfileMimeType: file.type || "application/octet-stream",
            privacyProfileNeedsRefresh: true,
            privacyProfileStatus: "not_started"
          });
          void profileWalletUpload(uploaded, file);
          if (storeNewFilesOnFilecoin) {
            void storeWalletRecordOnFilecoin(uploaded);
          }
          return;
        } catch {
          // Keep local document capture available if the configured API is unavailable.
        }
      }
    }
    const localUpload = normalizeWalletUpload(
      {
        id: `up-${Date.now()}`,
        fileName: file.name,
        machineSummary,
        category: "Uncategorized",
        sensitivity: "high",
        status: "stored",
        shared: false
      },
      file.name
    );
    prependUpload(localUpload);
    if (storeNewFilesOnFilecoin) {
      void storeFileUploadOnFilecoin(localUpload, file);
    }
  }

  async function repairUploadStorage(upload: UploadItem) {
    if (!apiConfig?.actorDid || !upload.recordId) return;
    setRepairingUploadIds((uploadIds) => [...uploadIds, upload.id]);
    try {
      const storageOk = await repairRecordStorage(apiConfig, upload.recordId);
      updateUpload(upload.id, {
        status: storageOk ? "stored" : upload.status,
        storageOk
      });
      await refreshWalletAuditEvents();
    } catch {
      updateUpload(upload.id, { storageOk: false });
    } finally {
      setRepairingUploadIds((uploadIds) => uploadIds.filter((id) => id !== upload.id));
    }
  }

  async function storeFileUploadOnFilecoin(upload: UploadItem, file: File) {
    if (!filecoinStorageConfig) {
      updateUpload(upload.id, {
        decentralizedStorageMessage: t(siteLocale, "wallet.storageConnectBeforeUpload"),
        decentralizedStorageStatus: "not_configured"
      });
      return;
    }
    setFilecoinUploadIds((uploadIds) => [...uploadIds, upload.id]);
    updateUpload(upload.id, {
      filecoinPinRequestId: undefined,
      filecoinPinStatus: undefined,
      filecoinPinStatusUrl: undefined,
      decentralizedStorageMessage: t(siteLocale, "wallet.storageUploading"),
      decentralizedStorageStatus: "uploading"
    });
    try {
      const result = await uploadFileToFilecoinStorage(file, {
        allowedRecipientIds: upload.allowedRecipientIds ?? [],
        clientConfig: filecoinStorageConfig,
        upload,
        walletConfig: apiConfig
      });
      const patch = toFilecoinStoragePatch(result);
      updateUpload(upload.id, patch);
      void persistUploadMetadata(upload, patch);
      void monitorFilecoinPersistence(upload.id, result);
    } catch (error) {
      updateUpload(upload.id, {
        decentralizedStorageMessage: error instanceof Error ? error.message : t(siteLocale, "wallet.storageUploadFailed"),
        decentralizedStorageStatus: "failed"
      });
    } finally {
      setFilecoinUploadIds((uploadIds) => uploadIds.filter((id) => id !== upload.id));
    }
  }

  async function storeWalletRecordOnFilecoin(upload: UploadItem) {
    if (!filecoinStorageConfig) return;
    setFilecoinUploadIds((uploadIds) => [...uploadIds, upload.id]);
    updateUpload(upload.id, {
      filecoinPinRequestId: undefined,
      filecoinPinStatus: undefined,
      filecoinPinStatusUrl: undefined,
      decentralizedStorageMessage:
        upload.filecoinPinStatus === "failed"
          ? t(siteLocale, "wallet.storageRetryRecord")
          : t(siteLocale, "wallet.storageSendRecord"),
      decentralizedStorageStatus: "uploading"
    });
    try {
      const result = await uploadWalletRecordToFilecoinStorage(upload, {
        clientConfig: filecoinStorageConfig,
        walletConfig: apiConfig
      });
      const patch = toFilecoinStoragePatch(result);
      const nextUpload = { ...upload, ...patch };
      updateUpload(upload.id, patch);
      void persistUploadMetadata(upload, patch);
      if (!nextUpload.privacyProfileStatus || nextUpload.privacyProfileNeedsRefresh) {
        void profileWalletUpload(nextUpload);
      }
      void monitorFilecoinPersistence(upload.id, result);
    } catch (error) {
      updateUpload(upload.id, {
        decentralizedStorageMessage: error instanceof Error ? error.message : t(siteLocale, "wallet.storageUploadFailed"),
        decentralizedStorageStatus: "failed"
      });
    } finally {
      setFilecoinUploadIds((uploadIds) => uploadIds.filter((id) => id !== upload.id));
    }
  }

  async function profileWalletUpload(upload: UploadItem, file?: File) {
    if (!apiConfig?.actorDid || !upload.recordId) return;
    const mimeType = normalizePublicMimeType(
      file?.type || upload.privacyProfileMimeType || "",
      file?.name || upload.fileName || upload.recordId
    );
    updateUpload(upload.id, {
      privacyProfileMessage: t(siteLocale, "wallet.profileCreating"),
      privacyProfileMimeType: mimeType,
      privacyProfileStatus: "profiling"
    });
    void persistUploadMetadata(upload, {
      privacyProfileMessage: t(siteLocale, "wallet.profileCreating"),
      privacyProfileMimeType: mimeType,
      privacyProfileStatus: "profiling"
    });
    try {
      try {
        const serverProfile = await generateWalletRecordMetadata(apiConfig, upload.recordId, {
          fileName: upload.fileName,
          mimeType,
          walletCid: upload.ipfsRootCid || upload.ipfsCid || upload.metadataIpldCid || upload.recordId
        });
        updateUpload(upload.id, {
          ...serverProfile,
          id: upload.id,
          recordId: serverProfile.recordId ?? upload.recordId,
          storageOk: serverProfile.storageOk ?? upload.storageOk
        });
        await refreshWalletAuditEvents().catch(() => {});
        return;
      } catch (serverError) {
        console.warn("Wallet router metadata generation failed; falling back to browser orchestration", serverError);
      }
      const [redacted, vector, graphrag, extracted, form] = await Promise.allSettled([
        analyzeRecordRedactedWithGrant(apiConfig, { recordId: upload.recordId, maxChars: 500 }),
        createRecordVectorProfileWithGrant(apiConfig, { recordId: upload.recordId, chunkSizeWords: 80 }),
        createRedactedGraphRAG(apiConfig, {
          recordIds: [upload.recordId],
          maxBytesPerRecord: 200_000,
          maxCharsPerRecord: 20_000,
          useOcr: true
        }),
        extractRecordTextRedactedWithGrant(apiConfig, {
          recordId: upload.recordId,
          maxBytes: 200_000,
          maxChars: 12_000,
          useOcr: true
        }),
        analyzeRecordFormRedactedWithGrant(apiConfig, {
          recordId: upload.recordId,
          maxFields: 100,
          useOcr: true
        })
      ]);
      const fulfilled = [redacted, vector, graphrag, extracted, form].filter(
        (result): result is PromiseFulfilledResult<Awaited<ReturnType<typeof analyzeRecordRedactedWithGrant>>> =>
          result.status === "fulfilled"
      );
      const outputs = fulfilled.map((result) => result.value.output);
      const organizerProfile = await buildOpenRouterOrganizerProfile({
        fileName: upload.fileName,
        mimeType,
        outputs
      });
      if (organizerProfile) {
        outputs.push({ openrouter_organizer_profile: organizerProfile, output_policy: "redacted_remote_organizer" });
      }
      if (!outputs.length) outputs.push(buildFallbackDocumentProfileOutput(upload, mimeType));
      const artifactIds = fulfilled.map((result) => result.value.artifact.id);
      const publicInputs = buildDocumentPrivacyProfilePublicInputs({
        artifactIds,
        file,
        fileName: upload.fileName,
        mimeType,
        outputs
      });
      const proof = await createDocumentPrivacyProfileProof(apiConfig, {
        publicInputs,
        recordId: upload.recordId
      });
      const patch: Partial<UploadItem> = {
        privacyProfileArtifactIds: artifactIds,
        privacyProfileClassification: classifyDocumentProfile(publicInputs),
        privacyProfileLabels: readStringArray(publicInputs, "organizer_labels") || defaultLabelsForMimeType(mimeType),
        privacyProfileMessage: t(siteLocale, "wallet.profileReady"),
        privacyProfileMimeType: mimeType,
        privacyProfileNeedsRefresh: false,
        privacyProfileProofId: proof.id,
        privacyProfilePublicInputs: proof.publicInputs,
        privacyProfileSearchText: buildPrivacySearchText(outputs, proof.publicInputs),
        privacyProfileStatus: "profiled",
        privacyProfileSummary: summarizeDocumentPrivacyProfile(publicInputs),
        privacyProfileVectorTerms: buildPrivacyVectorTerms(outputs, proof.publicInputs)
      };
      updateUpload(upload.id, patch);
      await persistUploadMetadata(upload, patch);
      await refreshWalletAuditEvents().catch(() => {});
    } catch (error) {
      const patch: Partial<UploadItem> = {
        privacyProfileMessage:
          error instanceof Error ? error.message : t(siteLocale, "wallet.profileError"),
        privacyProfileStatus: "failed"
      };
      updateUpload(upload.id, patch);
      void persistUploadMetadata(upload, patch);
    }
  }

  async function downloadDecryptedUpload(upload: UploadItem) {
    if (!apiConfig?.actorDid || !upload.recordId) return;
    setDownloadingUploadIds((uploadIds) => [...uploadIds, upload.id]);
    try {
      const decrypted = await decryptRecordWithGrant(apiConfig, { recordId: upload.recordId });
      const bytes = decrypted.base64 ? base64ToBytes(decrypted.base64) : new TextEncoder().encode(decrypted.text);
      const decryptedMimeType = detectDecryptedMimeType(bytes, upload.fileName, decrypted.text);
      const decryptedClassification = displayMimeType(decryptedMimeType);
      const decryptedLabels = defaultLabelsForMimeType(decryptedMimeType);
      updateUpload(upload.id, {
        decryptedClassification,
        decryptedLabels,
        decryptedMimeType
      });
      void persistUploadMetadata(upload, {
        decryptedClassification,
        decryptedLabels,
        decryptedMimeType
      });
      const payload = new Uint8Array(bytes).buffer as ArrayBuffer;
      const blob = new Blob([payload], { type: decryptedMimeType });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = upload.fileName || `${upload.recordId}.bin`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    } finally {
      setDownloadingUploadIds((uploadIds) => uploadIds.filter((id) => id !== upload.id));
    }
  }

  async function persistUploadMetadata(upload: UploadItem, patch: Partial<UploadItem> = {}) {
    if (!apiConfig?.actorDid || !upload.recordId) return;
    try {
      const saved = await updateWalletRecordMetadata(
        apiConfig,
        upload.recordId,
        serializeUploadMetadata({ ...upload, ...patch })
      );
      updateUpload(upload.id, {
        ...saved,
        id: upload.id,
        recordId: saved.recordId ?? upload.recordId,
        storageOk: saved.storageOk ?? upload.storageOk
      });
    } catch (error) {
      console.warn("Wallet file metadata persistence failed", error);
      // Metadata persistence is best-effort so uploads, pins, and proofs can still complete.
    }
  }

  function serializeUploadMetadata(upload: UploadItem): Record<string, unknown> {
    return compactRecord({
      decentralizedStorageMessage: upload.decentralizedStorageMessage,
      decentralizedStorageProvider: upload.decentralizedStorageProvider,
      decentralizedStorageStatus: upload.decentralizedStorageStatus,
      decryptedClassification: upload.decryptedClassification,
      decryptedLabels: upload.decryptedLabels,
      decryptedMimeType: upload.decryptedMimeType,
      encryptedMetadataCid: upload.encryptedMetadataCid,
      encryptedPayloadCid: upload.encryptedPayloadCid,
      fileName: upload.fileName,
      filecoinDealId: upload.filecoinDealId,
      filecoinPieceCid: upload.filecoinPieceCid,
      filecoinPinRequestId: upload.filecoinPinRequestId,
      filecoinPinStatus: upload.filecoinPinStatus,
      filecoinPinStatusUrl: upload.filecoinPinStatusUrl,
      ipfsCid: upload.ipfsCid,
      ipfsGatewayUrl: upload.ipfsGatewayUrl,
      ipfsRootCid: upload.ipfsRootCid,
      ipldLinks: upload.ipldLinks,
      machineSummary: upload.machineSummary,
      metadataCid: upload.metadataCid,
      metadataFilecoinPinRequestId: upload.metadataFilecoinPinRequestId,
      metadataFilecoinPinStatus: upload.metadataFilecoinPinStatus,
      metadataFilecoinPinStatusUrl: upload.metadataFilecoinPinStatusUrl,
      metadataGatewayUrl: upload.metadataGatewayUrl,
      metadataIpldCid: upload.metadataIpldCid,
      metadataIpldLink: upload.metadataIpldLink,
      metadataStorageMessage: upload.metadataStorageMessage,
      privacyProfileArtifactIds: upload.privacyProfileArtifactIds,
      privacyProfileClassification: upload.privacyProfileClassification,
      privacyProfileLabels: upload.privacyProfileLabels,
      privacyProfileMessage: upload.privacyProfileMessage,
      privacyProfileMimeType: upload.privacyProfileMimeType,
      privacyProfileNeedsRefresh: upload.privacyProfileNeedsRefresh,
      privacyProfileProofId: upload.privacyProfileProofId,
      privacyProfilePublicInputs: upload.privacyProfilePublicInputs,
      privacyProfileSearchText: upload.privacyProfileSearchText,
      privacyProfileStatus: upload.privacyProfileStatus,
      privacyProfileSummary: upload.privacyProfileSummary,
      privacyProfileVectorTerms: upload.privacyProfileVectorTerms
    });
  }

  function normalizeWalletUpload(upload: UploadItem, fileName: string): UploadItem {
    return {
      ...upload,
      allowedRecipientIds: upload.allowedRecipientIds ?? [],
      decentralizedStorageProvider: upload.decentralizedStorageProvider ?? (upload.recordId ? "wallet-api" : "local"),
      decentralizedStorageStatus: upload.decentralizedStorageStatus ?? (filecoinStorageReady ? "ready" : "not_configured"),
      fileName,
      shared: upload.shared ?? false,
      sharingMode: upload.sharingMode ?? "private"
    };
  }

  function prependUpload(upload: UploadItem) {
    replaceUploads([upload, ...uploadsRef.current]);
  }

  function replaceUploads(nextUploads: UploadItem[]) {
    uploadsRef.current = nextUploads;
    setUploads(nextUploads);
  }

  function updateUpload(uploadId: string, patch: Partial<UploadItem>) {
    replaceUploads(uploadsRef.current.map((item) => (item.id === uploadId ? { ...item, ...patch } : item)));
  }

  async function deleteWalletUpload(upload: UploadItem) {
    if (!apiConfig?.actorDid || !upload.recordId) return;
    const confirmed = window.confirm(
      tFormat(siteLocale, "wallet.deleteConfirm", { name: upload.fileName })
    );
    if (!confirmed) return;
    setDeletingUploadIds((uploadIds) => [...new Set([...uploadIds, upload.id])]);
    try {
      await deleteWalletRecord(apiConfig, upload.recordId, { unpinIpfs: true });
      replaceUploads(uploadsRef.current.filter((item) => item.id !== upload.id));
      await refreshWalletAuditEvents().catch(() => undefined);
    } catch (error) {
      updateUpload(upload.id, {
        decentralizedStorageMessage:
          error instanceof Error
            ? tFormat(siteLocale, "wallet.deleteFailedDetail", { error: error.message })
            : t(siteLocale, "wallet.deleteFailed")
      });
    } finally {
      setDeletingUploadIds((uploadIds) => uploadIds.filter((id) => id !== upload.id));
    }
  }

  async function monitorFilecoinPersistence(uploadId: string, initialResult: Parameters<typeof toFilecoinStoragePatch>[0]) {
    if (!filecoinStorageConfig) return;
    if (!(initialResult.filecoinPinRequestId || initialResult.requestId)) return;
    try {
      await pollFilecoinStorageStatus(initialResult, {
        clientConfig: filecoinStorageConfig,
        onUpdate: (nextResult) => {
          const patch = toFilecoinStoragePatch(nextResult);
          const upload = uploadsRef.current.find((item) => item.id === uploadId);
          updateUpload(uploadId, patch);
          if (upload) {
            void persistUploadMetadata(upload, patch);
          }
        }
      });
    } catch (error) {
      updateUpload(uploadId, {
        decentralizedStorageMessage:
          error instanceof Error
            ? tFormat(siteLocale, "wallet.pollFailedDetail", { error: error.message })
            : t(siteLocale, "wallet.pollFailed")
      });
    }
  }

  function allowSharing(upload: UploadItem) {
    const selectedRecipients =
      upload.allowedRecipientIds?.length
        ? upload.allowedRecipientIds
        : (verifiedRecipients.length ? verifiedRecipients : recipients).slice(0, 2).map((recipient) => recipient.id);
    updateUpload(upload.id, {
      allowedRecipientIds: selectedRecipients,
      shared: selectedRecipients.length > 0,
      sharingMode: "selected_contacts"
    });
  }

  function makePrivate(upload: UploadItem) {
    updateUpload(upload.id, {
      allowedRecipientIds: [],
      shared: false,
      sharingMode: "private"
    });
  }

  function toggleSharingRecipient(upload: UploadItem, recipientId: string) {
    const currentRecipients = upload.allowedRecipientIds ?? [];
    const allowedRecipientIds = currentRecipients.includes(recipientId)
      ? currentRecipients.filter((id) => id !== recipientId)
      : [...currentRecipients, recipientId];
    updateUpload(upload.id, {
      allowedRecipientIds,
      shared: allowedRecipientIds.length > 0,
      sharingMode: allowedRecipientIds.length > 0 ? "selected_contacts" : "private"
    });
  }

  function walletLoginContact() {
    return signedInUser.includes(":") ? signedInUser.split(":").slice(1).join(":") : signedInUser;
  }

  async function generateWallet() {
    if (!apiBaseUrl) return;
    setWalletCreateStatus("creating");
    setWalletCreateError("");
    const ownerDid = resolveWalletOwnerDid(signedInUser, apiConfig);
    const issuerKeyHex = randomHex(32);

    try {
      const wallet = await createWallet({ apiBaseUrl, ownerDid });
      const nextConfig = {
        apiBaseUrl,
        walletId: wallet.wallet_id,
        actorDid: wallet.owner_did,
        issuerKeyHex,
        audienceKeyHex: undefined
      };
      setApiConfig(nextConfig);
      try {
        const recoveryBundle = await buildClientWrappedRecoveryBundle({
          actorDid: wallet.owner_did,
          contact: walletLoginContact(),
          walletId: wallet.wallet_id
        });
        await storeWalletRecoveryBundle(nextConfig, {
          encryptedBundle: recoveryBundle.encryptedBundle,
          publicMetadata: recoveryBundle.publicMetadata,
          recoveryHint: "This wallet recovery bundle is encrypted to this browser's local recovery key.",
          wrappingMethod: "device-local-key"
        });
      } catch (error) {
        if (import.meta.env.DEV) {
          console.warn("Client-side wallet recovery bundle could not be stored", error);
        }
      }
      setWalletCreateStatus("created");
    } catch (error) {
      setWalletCreateStatus("failed");
      setWalletCreateError(error instanceof Error ? error.message : t(siteLocale, "wallet.generationFailed"));
    }
  }

  async function savePassphraseRecoveryBundle() {
    if (!apiConfig?.actorDid || !recoveryPassphrase.trim()) return;
    setRecoveryStatus("saving");
    setRecoveryMessage("");
    try {
      const bundle = await buildPassphraseWrappedRecoveryBundle({
        actorDid: apiConfig.actorDid,
        contact: walletLoginContact(),
        passphrase: recoveryPassphrase,
        walletId: apiConfig.walletId
      });
      const response = await storeWalletRecoveryBundle(apiConfig, {
        encryptedBundle: bundle.encryptedBundle,
        kdf: bundle.kdf,
        publicMetadata: {
          ...bundle.publicMetadata,
          recoveryMethods: ["passphrase-pbkdf2-aes-gcm"]
        },
        recoveryHint: "Passphrase recovery bundle. The passphrase and wallet key are never sent to 211 AI.",
        wrappingMethod: "passphrase"
      });
      const recoveryQrPayload = buildWalletRecoveryQrPayload(
        apiConfig,
        response.bundle.bundle_id,
        "passphrase",
        recoveryPassphrase
      );
      const recoveryQrText = JSON.stringify(recoveryQrPayload);
      setRecoveryQrPayloadLabel(response.bundle.bundle_id);
      setRecoveryQrCodeUrl(
        await QRCode.toDataURL(recoveryQrText, {
          errorCorrectionLevel: "M",
          margin: 1,
          width: 220
        })
      );
      let backupMessage = "";
      if (filecoinStorageConfig) {
        const recoveryBackupPayload = JSON.stringify({
          schema: "211-ai-wallet-recovery-backup-v1",
          bundleId: response.bundle.bundle_id,
          containsPassphrase: false,
          containsPlaintextWalletKey: false,
          encryptedBundle: response.bundle.encrypted_bundle,
          publicMetadata: response.bundle.public_metadata,
          serverCanDecrypt: false,
          walletId: apiConfig.walletId,
          wrappingMethod: response.bundle.wrapping_method
        });
        const backup = await uploadRecoveryBundleToFilecoinStorage(recoveryBackupPayload, {
          clientConfig: filecoinStorageConfig,
          walletConfig: apiConfig
        });
        const backupCid = backup.ipfsCid || backup.cid || backup.root?.["/"];
        backupMessage = backupCid
          ? tFormat(siteLocale, "wallet.recoveryBackupQueuedWithCid", { cid: backupCid })
          : t(siteLocale, "wallet.recoveryBackupQueued");
      }
      setRecoveryStatus("ready");
      setRecoveryMessage(tFormat(siteLocale, "wallet.recoveryReady", { backup: backupMessage }));
    } catch (error) {
      setRecoveryStatus("failed");
      setRecoveryMessage(error instanceof Error ? error.message : t(siteLocale, "wallet.recoverySetupFailed"));
    }
  }

  async function importRecoveryQr(file: File | null) {
    if (!file) return;
    const ucan = readMagicLoginUcan();
    if (!ucan?.token) {
      setRecoveryStatus("failed");
      setRecoveryMessage(t(siteLocale, "wallet.recoveryNeedMagicLink"));
      return;
    }
    setRecoveryStatus("unlocking");
    setRecoveryMessage("");
    try {
      const qrValue = await readQrValue(file);
      const payload = parseWalletRecoveryQrPayload(qrValue);
      const config = {
        ...(apiConfig ?? {
          apiBaseUrl: payload.apiBaseUrl || resolveMagicLoginApiBaseUrl(),
          walletId: payload.walletId
        }),
        apiBaseUrl: payload.apiBaseUrl || apiConfig?.apiBaseUrl || resolveMagicLoginApiBaseUrl(),
        walletId: payload.walletId
      };
      const response = await loadWalletRecoveryBundleById(config, payload.bundleId, ucan.token);
      if (typeof window !== "undefined") {
        window.localStorage.setItem(
          `${WALLET_RECOVERY_BUNDLE_CACHE_PREFIX}${payload.walletId}`,
          JSON.stringify({
            cachedAt: new Date().toISOString(),
            bundle: response.bundle,
            privacy: response.privacy,
            source: "magic-link-plus-qr",
            ucan: {
              audience: ucan.audience,
              expires_at: ucan.expires_at,
              profile: ucan.profile
            }
          })
        );
      }
      if (!apiConfig) {
        setApiConfig(config);
      }
      setRecoveryQrPayloadLabel(payload.bundleId);
      if (payload.passphrase) {
        const recovered = await decryptPassphraseRecoveryBundle(response.bundle.encrypted_bundle, payload.passphrase);
        if (recovered.walletId && recovered.walletId !== config.walletId) {
          throw new Error(t(siteLocale, "wallet.recoveryWrongWallet"));
        }
        storeWalletDeviceRecoveryRawKey(config.walletId, recovered.walletContentKey);
        if (recovered.actorDid && recovered.actorDid !== config.actorDid) {
          setApiConfig({ ...config, actorDid: recovered.actorDid });
        }
        setRecoveryPassphrase("");
        setRecoveryStatus("ready");
        setRecoveryMessage(t(siteLocale, "wallet.recoveryUnlockedLocal"));
        return;
      }
      setRecoveryStatus("ready");
      setRecoveryMessage(t(siteLocale, "wallet.recoveryImported"));
    } catch (error) {
      setRecoveryStatus("failed");
      setRecoveryMessage(error instanceof Error ? error.message : t(siteLocale, "wallet.recoveryImportFailed"));
    }
  }

  async function unlockCachedPassphraseRecoveryBundle() {
    if (!apiConfig || !recoveryPassphrase.trim()) return;
    setRecoveryStatus("unlocking");
    setRecoveryMessage("");
    try {
      const bundle = readCachedRecoveryBundle(apiConfig.walletId);
      if (!bundle) {
        throw new Error(t(siteLocale, "wallet.recoveryNoCachedBundle"));
      }
      const recovered = await decryptPassphraseRecoveryBundle(bundle, recoveryPassphrase);
      if (recovered.walletId && recovered.walletId !== apiConfig.walletId) {
        throw new Error(t(siteLocale, "wallet.recoveryWrongWallet"));
      }
      storeWalletDeviceRecoveryRawKey(apiConfig.walletId, recovered.walletContentKey);
      if (recovered.actorDid && recovered.actorDid !== apiConfig.actorDid) {
        setApiConfig({ ...apiConfig, actorDid: recovered.actorDid });
      }
      setRecoveryStatus("ready");
      setRecoveryMessage(t(siteLocale, "wallet.recoveryRestored"));
    } catch (error) {
      setRecoveryStatus("failed");
      setRecoveryMessage(error instanceof Error ? error.message : t(siteLocale, "wallet.recoveryFailed"));
    }
  }

  return (
    <div className="screen wallet-screen">
      <div className="page-title">
        <p className="eyebrow">{t(siteLocale, "wallet.eyebrow")}</p>
        <h1>{t(siteLocale, "wallet.title")}</h1>
      </div>
      {walletCreateStatus === "created" ? <StatusBanner tone="success">{t(siteLocale, "wallet.generatedConnected")}</StatusBanner> : null}
      {walletCreateStatus === "failed" ? <StatusBanner tone="warning">{walletCreateError || t(siteLocale, "wallet.generationFailed")}</StatusBanner> : null}
      <div className="wallet-status-strip" aria-label={t(siteLocale, "wallet.statusAria")}>
        <div>
          <span>{t(siteLocale, "wallet.status.wallet")}</span>
          <strong>
            {apiConfig
              ? t(siteLocale, "wallet.status.connected")
              : apiBaseUrl
                ? t(siteLocale, "wallet.status.ready")
                : t(siteLocale, "wallet.status.needsApi")}
          </strong>
        </div>
        <div>
          <span>{t(siteLocale, "wallet.status.files")}</span>
          <strong>{uploads.length}</strong>
        </div>
        <div>
          <span>{t(siteLocale, "wallet.status.proofs")}</span>
          <strong>{walletFileStats.profiled}</strong>
        </div>
        <div>
          <span>{t(siteLocale, "wallet.status.ipld")}</span>
          <strong>{walletFileStats.ipldLinked}</strong>
        </div>
      </div>
      <Section
        title={t(siteLocale, "wallet.connectionTitle")}
        actions={
          <Badge tone={apiConfig ? "success" : apiBaseUrl ? "warning" : "neutral"}>
            {apiConfig
              ? t(siteLocale, "wallet.connection.connected")
              : apiBaseUrl
                ? t(siteLocale, "wallet.connection.readyToCreate")
                : t(siteLocale, "wallet.connection.apiRequired")}
          </Badge>
        }
      >
        <div className="disclosure-package">
          <div className="disclosure-row">
            <strong>{t(siteLocale, "wallet.connection.wallet")}</strong>
            <span>{apiConfig?.walletId ?? t(siteLocale, "wallet.connection.notConnected")}</span>
          </div>
          <div className="disclosure-row">
            <strong>{t(siteLocale, "wallet.connection.ownerDid")}</strong>
            <span>{apiConfig?.actorDid ?? t(siteLocale, "wallet.connection.ownerDidPending")}</span>
          </div>
          <div className="disclosure-row">
            <strong>{t(siteLocale, "wallet.connection.backend")}</strong>
            <span>{apiBaseUrl ?? t(siteLocale, "wallet.connection.backendHelp")}</span>
          </div>
        </div>
        <div className="row-actions">
          <Button
            ariaLabel={walletCreateStatus === "creating" ? t(siteLocale, "wallet.connection.generating") : t(siteLocale, "wallet.connection.generate")}
            disabled={!apiBaseUrl || walletCreateStatus === "creating"}
            onClick={() => void generateWallet()}
          >
            <Archive size={18} /> {walletCreateStatus === "creating" ? t(siteLocale, "wallet.connection.generating") : t(siteLocale, "wallet.connection.generate")}
          </Button>
        </div>
        <div className="wallet-recovery-panel">
          <div>
            <strong>{t(siteLocale, "wallet.recoveryTitle")}</strong>
            <small>{t(siteLocale, "wallet.recoveryHelp")}</small>
          </div>
          <Field label={t(siteLocale, "wallet.recoveryPassphrase")}>
            <input
              autoComplete="new-password"
              disabled={!apiConfig}
              onChange={(event) => {
                setRecoveryPassphrase(event.target.value);
                setRecoveryMessage("");
                setRecoveryStatus("idle");
              }}
              placeholder={t(siteLocale, "wallet.recoveryPassphrasePlaceholder")}
              type="password"
              value={recoveryPassphrase}
            />
          </Field>
          <div className="row-actions">
            <Button
              disabled={!apiConfig?.actorDid || recoveryPassphrase.trim().length < 8 || recoveryStatus === "saving"}
              loading={recoveryStatus === "saving"}
              loadingLabel={t(siteLocale, "wallet.recoverySaving")}
              onClick={() => void savePassphraseRecoveryBundle()}
              type="button"
              variant="secondary"
            >
              <LockKeyhole size={18} /> {t(siteLocale, "wallet.recoverySave")}
            </Button>
            <Button
              disabled={!apiConfig || recoveryPassphrase.trim().length < 8 || recoveryStatus === "unlocking"}
              loading={recoveryStatus === "unlocking"}
              loadingLabel={t(siteLocale, "wallet.recoveryUnlocking")}
              onClick={() => void unlockCachedPassphraseRecoveryBundle()}
              type="button"
              variant="secondary"
            >
              <KeyRound size={18} /> {t(siteLocale, "wallet.recoveryUnlock")}
            </Button>
          </div>
          <div className="wallet-recovery-qr-grid">
            {recoveryQrCodeUrl ? (
              <img
                alt={t(siteLocale, "wallet.recoveryQrAlt")}
                className="wallet-proof-qr-image"
                height={180}
                src={recoveryQrCodeUrl}
                width={180}
              />
            ) : (
              <div className="wallet-proof-qr-placeholder">{t(siteLocale, "wallet.recoveryQrPlaceholder")}</div>
            )}
            <div className="wallet-recovery-qr-actions">
              <strong>{t(siteLocale, "wallet.recoveryMagicQrTitle")}</strong>
              <small>{t(siteLocale, "wallet.recoveryMagicQrHelp")}</small>
              <div className="disclosure-package">
                <div className="disclosure-row">
                  <strong>{t(siteLocale, "wallet.recoveryBundle")}</strong>
                  <span>{recoveryQrPayloadLabel || t(siteLocale, "wallet.recoveryBundleMissing")}</span>
                </div>
                <div className="disclosure-row">
                  <strong>{t(siteLocale, "wallet.serverAccess")}</strong>
                  <span>{t(siteLocale, "wallet.serverAccessDetail")}</span>
                </div>
                <div className="disclosure-row">
                  <strong>{t(siteLocale, "wallet.qrAccess")}</strong>
                  <span>{t(siteLocale, "wallet.qrAccessDetail")}</span>
                </div>
              </div>
              <label className="button button-secondary">
                <Camera aria-hidden="true" size={18} /> {t(siteLocale, "wallet.importRecoveryQr")}
                <input
                  accept={PROOF_QR_IMAGE_ACCEPT_ATTR}
                  aria-label={t(siteLocale, "wallet.importRecoveryQrPicture")}
                  className="sr-only"
                  onChange={(event) => {
                    void importRecoveryQr(event.target.files?.[0] ?? null);
                    event.currentTarget.value = "";
                  }}
                  type="file"
                />
              </label>
            </div>
          </div>
          {recoveryMessage ? (
            <StatusBanner tone={recoveryStatus === "failed" ? "warning" : "success"}>{recoveryMessage}</StatusBanner>
          ) : null}
        </div>
      </Section>
      <Section
        title={t(siteLocale, "wallet.shareProofQrTitle")}
        actions={
          <Badge tone={walletQrProofs.length > 0 ? "success" : "warning"}>
            {tFormat(siteLocale, "wallet.proofClaims", { count: String(walletQrProofs.length) })}
          </Badge>
        }
      >
        <div className="wallet-proof-qr-panel">
          {walletQrCodeUrl ? (
            <img
              alt={t(siteLocale, "wallet.shareProofQrTitle")}
              className="wallet-proof-qr-image"
              height={220}
              src={walletQrCodeUrl}
              width={220}
            />
          ) : (
            <div aria-live="polite" className="wallet-proof-qr-placeholder">
              {walletQrStatus === "loading"
                ? t(siteLocale, "wallet.proofPublishing")
                : filecoinStorageReady
                  ? t(siteLocale, "wallet.proofUnavailable")
                  : t(siteLocale, "wallet.proofConnectStorage")}
            </div>
          )}
          <div className="wallet-proof-qr-details">
            <strong>{t(siteLocale, "wallet.scanProofTitle")}</strong>
            <small>{t(siteLocale, "wallet.scanProofHelp")}</small>
            <div className="badge-row">
              <Badge tone="info">{t(siteLocale, "wallet.ipfsWalletRootQr")}</Badge>
              <Badge>{apiConfig?.walletId ?? t(siteLocale, "wallet.localWallet")}</Badge>
              {apiConfig?.actorDid ? <Badge>{apiConfig.actorDid}</Badge> : <Badge>{t(siteLocale, "wallet.offlineWalletPreview")}</Badge>}
            </div>
            <div className="disclosure-package">
              <div className="disclosure-row">
                <strong>{t(siteLocale, "wallet.qrPayload")}</strong>
                <span>{walletQrPayloadLabel}</span>
              </div>
              <div className="disclosure-row">
                <strong>{t(siteLocale, "wallet.includes")}</strong>
                <span>
                  {uploads.filter((upload) => upload.recordId).length} encrypted wallet records;{" "}
                  {summarizeWalletProofClaims(walletQrProofs)}
                </span>
              </div>
              <div className="disclosure-row">
                <strong>{t(siteLocale, "wallet.opens")}</strong>
                <span>{t(siteLocale, "wallet.opensDetail")}</span>
              </div>
            </div>
            <a className="button button-secondary" href={walletProofReviewHref}>
              {t(siteLocale, "wallet.openProofReview")}
            </a>
          </div>
        </div>
      </Section>
      <Section
        title={t(siteLocale, "wallet.addFileTitle")}
        actions={
          <Badge tone={filecoinStorageReady ? "success" : "warning"}>
            {filecoinStorageReady ? t(siteLocale, "wallet.storageReady") : t(siteLocale, "wallet.backendRequired")}
          </Badge>
        }
      >
        <div className="wallet-storage-panel">
          <div>
            <strong>{t(siteLocale, "wallet.storageDestination")}</strong>
            <small>
              {filecoinStorageReady
                ? t(siteLocale, "wallet.storageReadyHelp")
                : t(siteLocale, "wallet.storageMissingHelp")}
            </small>
          </div>
          <label className="wallet-filecoin-toggle">
            <input
              checked={storeNewFilesOnFilecoin}
              disabled={!filecoinStorageReady}
              onChange={(event) => setStoreNewFilesOnFilecoin(event.target.checked)}
              type="checkbox"
            />
            <span>{t(siteLocale, "wallet.storeNewFiles")}</span>
          </label>
        </div>
        <label className="upload-dropzone">
          <Upload aria-hidden="true" size={28} />
          <span>{t(siteLocale, "wallet.chooseFile")}</span>
          <small>{t(siteLocale, "wallet.filesPrivateUntilShared")}</small>
          <span className="upload-picker">
            <FileUp aria-hidden="true" size={18} /> {t(siteLocale, "wallet.selectFile")}
          </span>
          <input
            type="file"
            onChange={(event) => addUpload(event.target.files?.[0] ?? null)}
            aria-label={t(siteLocale, "wallet.chooseFileAria")}
          />
        </label>
      </Section>
      <Section
        title={t(siteLocale, "wallet.fileWalletTitle")}
        actions={
          <Badge tone={visibleUploads.length === uploads.length ? "neutral" : "info"}>
            {tFormat(siteLocale, "wallet.fileCount", { total: String(uploads.length), visible: String(visibleUploads.length) })}
          </Badge>
        }
      >
        <div className="wallet-file-workbench">
          <div className="wallet-file-controls" aria-label={t(siteLocale, "wallet.fileControlsAria")}>
            <Field label={t(siteLocale, "wallet.findFiles")}>
              <div className="wallet-file-search-field">
                <Search aria-hidden="true" size={18} />
                <input
                  autoComplete="off"
                  onChange={(event) => setWalletFileQuery(event.target.value)}
                  placeholder={t(siteLocale, "wallet.searchPlaceholder")}
                  type="search"
                  value={walletFileQuery}
                />
              </div>
            </Field>
            <Field label={t(siteLocale, "wallet.sort")}>
              <select
                onChange={(event) => setWalletFileSort(event.target.value as WalletFileSortMode)}
                value={walletFileSort}
              >
                <option value="newest">{t(siteLocale, "wallet.sortNewest")}</option>
                <option value="oldest">{t(siteLocale, "wallet.sortOldest")}</option>
                <option value="name">{t(siteLocale, "wallet.sortName")}</option>
                <option value="type">{t(siteLocale, "wallet.sortType")}</option>
                <option value="profile">{t(siteLocale, "wallet.sortProfile")}</option>
                <option value="storage">{t(siteLocale, "wallet.sortStorage")}</option>
              </select>
            </Field>
          </div>
          <div className="wallet-file-filter-row" aria-label={t(siteLocale, "wallet.filtersAria")}>
            {walletFileFilterOptions.map((option) => (
              <button
                aria-pressed={walletFileFilter === option.value}
                className="choice-chip"
                key={option.value}
                onClick={() => setWalletFileFilter(option.value)}
                type="button"
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>
        <div className="list-stack wallet-file-list">
          {visibleUploads.length === 0 ? (
            <div className="wallet-empty-state">
              <strong>{t(siteLocale, "wallet.emptyTitle")}</strong>
              <small>{t(siteLocale, "wallet.emptyBody")}</small>
            </div>
          ) : null}
        {visibleUploads.map((upload) => (
          <article
            aria-label={tFormat(siteLocale, "wallet.fileAria", { name: upload.fileName })}
            className="list-item upload-list-item wallet-list-item"
            key={upload.id}
          >
            <div className="wallet-file-primary">
              <h3>{upload.fileName}</h3>
              <p>{uploadTypeLabel(upload)}</p>
              <small className="upload-machine-summary">{toShortSummaryTitle(upload.machineSummary)}</small>
              <div className="badge-row">
                <Badge tone="success">{upload.status}</Badge>
                {upload.storageOk !== undefined ? (
                  <Badge tone={upload.storageOk ? "success" : "warning"}>
                    {upload.storageOk ? t(siteLocale, "wallet.saved") : t(siteLocale, "wallet.saveNeedsFix")}
                  </Badge>
                ) : null}
                <Badge tone={upload.shared ? "success" : "neutral"}>{sharingBadge(upload, siteLocale)}</Badge>
                <Badge tone={filecoinBadgeTone(upload)}>{filecoinBadge(upload, siteLocale)}</Badge>
                {upload.decryptedMimeType ? (
                  <Badge tone="success">{displayMimeType(upload.decryptedMimeType)}</Badge>
                ) : null}
                {upload.privacyProfileMimeType ? (
                  <Badge tone="info">{displayMimeType(upload.privacyProfileMimeType)}</Badge>
                ) : null}
                {upload.privacyProfileClassification ? (
                  <Badge tone="info">{upload.privacyProfileClassification}</Badge>
                ) : null}
                {upload.privacyProfileStatus ? (
                  <Badge tone={privacyProfileBadgeTone(upload)}>
                    {privacyProfileBadge(upload, siteLocale)}
                  </Badge>
                ) : null}
              </div>
              {upload.ipfsCid ? (
                <div className="wallet-evidence-row">
                  <span>IPFS</span>
                  <a href={ipfsGatewayHref(upload)} rel="noreferrer" target="_blank">
                    <code>{upload.ipfsCid}</code>
                  </a>
                </div>
              ) : null}
              {upload.ipldLinks?.length ? (
                <div className="wallet-evidence-row">
                  <span>IPLD</span>
                  <strong>
                    {upload.ipldLinks.length} {upload.ipldLinks.length === 1 ? t(siteLocale, "wallet.objectSingular") : t(siteLocale, "wallet.objectPlural")}
                  </strong>
                </div>
              ) : null}
              {upload.metadataCid ? (
                <div className="wallet-evidence-row">
                  <span>{t(siteLocale, "wallet.metadata")}</span>
                  <a href={normalizeIpfsGatewayUrl(upload.metadataGatewayUrl) || ipfsGatewayHref({ ...upload, ipfsCid: upload.metadataCid, ipfsGatewayUrl: undefined })} rel="noreferrer" target="_blank">
                    <code>{upload.metadataCid}</code>
                  </a>
                </div>
              ) : null}
              {upload.metadataStorageMessage ? (
                <small className="wallet-storage-reference">{upload.metadataStorageMessage}</small>
              ) : null}
              {upload.privacyProfileSummary ? (
                <small className="wallet-storage-reference">{tFormat(siteLocale, "wallet.privateProfile", { value: upload.privacyProfileSummary })}</small>
              ) : null}
              {upload.decryptedClassification || upload.decryptedMimeType ? (
                <small className="wallet-storage-reference">
                  {tFormat(siteLocale, "wallet.decryptedDownload", {
                    value: `${upload.decryptedClassification || displayMimeType(upload.decryptedMimeType || "")}${upload.decryptedMimeType ? ` (${upload.decryptedMimeType})` : ""}`
                  })}
                </small>
              ) : null}
              {upload.decryptedLabels?.length ? (
                <small className="wallet-storage-reference">
                  {tFormat(siteLocale, "wallet.decryptedContents", { value: upload.decryptedLabels.slice(0, 6).join(", ") })}
                </small>
              ) : null}
              {upload.privacyProfileClassification || upload.privacyProfileMimeType ? (
                <small className="wallet-storage-reference">
                  {tFormat(siteLocale, "wallet.profiledType", {
                    value: `${upload.privacyProfileClassification || displayMimeType(upload.privacyProfileMimeType || "")}${upload.privacyProfileMimeType ? ` (${upload.privacyProfileMimeType})` : ""}`
                  })}
                </small>
              ) : null}
              {upload.privacyProfileLabels?.length ? (
                <small className="wallet-storage-reference">
                  {tFormat(siteLocale, "wallet.contents", { value: upload.privacyProfileLabels.slice(0, 6).join(", ") })}
                </small>
              ) : null}
              {upload.privacyProfileProofId ? (
                <small className="wallet-storage-reference">{tFormat(siteLocale, "wallet.proof", { value: shortStorageId(upload.privacyProfileProofId) })}</small>
              ) : null}
              {upload.privacyProfileMessage ? (
                <small className="wallet-storage-reference">{upload.privacyProfileMessage}</small>
              ) : null}
              {upload.decentralizedStorageMessage ? (
                <small className="wallet-storage-reference">{upload.decentralizedStorageMessage}</small>
              ) : null}
            </div>
            <div className="wallet-sharing-controls" aria-label={tFormat(siteLocale, "wallet.sharingControlsFor", { name: upload.fileName })}>
              <div className="wallet-sharing-mode">
                <button
                  aria-pressed={(upload.sharingMode ?? "private") === "private"}
                  className="choice-chip"
                  onClick={() => makePrivate(upload)}
                  type="button"
                >
                  {t(siteLocale, "wallet.private")}
                </button>
                <button
                  aria-pressed={(upload.sharingMode ?? "private") === "selected_contacts"}
                  className="choice-chip"
                  onClick={() => allowSharing(upload)}
                  type="button"
                >
                  {t(siteLocale, "wallet.selectedContacts")}
                </button>
              </div>
              {(upload.sharingMode ?? "private") === "selected_contacts" ? (
                <div className="wallet-recipient-grid">
                  {recipients.length ? (
                    recipients.map((recipient) => (
                      <label className="wallet-recipient-option" key={recipient.id}>
                        <input
                          checked={(upload.allowedRecipientIds ?? []).includes(recipient.id)}
                          onChange={() => toggleSharingRecipient(upload, recipient.id)}
                          type="checkbox"
                        />
                        <span>
                          {recipient.displayName}
                          <small>
                            {recipient.verified ? t(siteLocale, "wallet.contactVerified") : t(siteLocale, "wallet.contactNotVerified")} · {recipient.relationship || recipient.agencyName || t(siteLocale, "wallet.contactFallback")}
                          </small>
                        </span>
                      </label>
                    ))
                  ) : (
                    <small className="upload-machine-summary">{t(siteLocale, "wallet.addContactsBeforeSharing")}</small>
                  )}
                </div>
              ) : null}
            </div>
            <div className="wallet-file-footer-actions" aria-label={tFormat(siteLocale, "wallet.actionsFor", { name: upload.fileName })}>
              {upload.storageOk === false && upload.recordId && apiConfig?.actorDid ? (
                <Button
                  disabled={repairingUploadIds.includes(upload.id)}
                  onClick={() => repairUploadStorage(upload)}
                  variant="secondary"
                >
                  <Wrench aria-hidden="true" size={18} />
                  {repairingUploadIds.includes(upload.id) ? t(siteLocale, "wallet.fixing") : t(siteLocale, "wallet.fixSave")}
                </Button>
              ) : null}
              {filecoinStorageReady && upload.recordId && shouldShowFilecoinAction(upload) ? (
                <Button
                  disabled={filecoinUploadIds.includes(upload.id)}
                  onClick={() => void storeWalletRecordOnFilecoin(upload)}
                  variant="secondary"
                >
                  <Upload aria-hidden="true" size={18} />
                  {filecoinActionLabel(upload, filecoinUploadIds.includes(upload.id), siteLocale)}
                </Button>
              ) : null}
              {upload.recordId && apiConfig?.actorDid && upload.privacyProfileStatus !== "profiled" ? (
                <Button
                  disabled={upload.privacyProfileStatus === "profiling"}
                  onClick={() => void profileWalletUpload(upload)}
                  variant="secondary"
                >
                  <ShieldCheck aria-hidden="true" size={18} />
                  {upload.privacyProfileStatus === "profiling" ? t(siteLocale, "wallet.profiling") : t(siteLocale, "wallet.generateProof")}
                </Button>
              ) : null}
              {upload.recordId && apiConfig?.actorDid ? (
                <Button
                  disabled={downloadingUploadIds.includes(upload.id)}
                  onClick={() => void downloadDecryptedUpload(upload)}
                  variant="secondary"
                >
                  <Download aria-hidden="true" size={18} />
                  {downloadingUploadIds.includes(upload.id) ? t(siteLocale, "wallet.decrypting") : t(siteLocale, "wallet.downloadDecrypted")}
                </Button>
              ) : null}
              <Button
                onClick={() => (upload.shared ? makePrivate(upload) : allowSharing(upload))}
                variant="secondary"
              >
                {upload.shared ? t(siteLocale, "wallet.makePrivate") : t(siteLocale, "wallet.allowSharing")}
              </Button>
              {upload.recordId && apiConfig?.actorDid ? (
                <Button
                  disabled={deletingUploadIds.includes(upload.id)}
                  onClick={() => void deleteWalletUpload(upload)}
                  variant="secondary"
                >
                  <Trash2 aria-hidden="true" size={18} />
                  {deletingUploadIds.includes(upload.id) ? t(siteLocale, "wallet.deleting") : t(siteLocale, "wallet.delete")}
                </Button>
              ) : null}
            </div>
          </article>
        ))}
      </div>
      </Section>
      <ExportCenterScreen apiConfig={apiConfig} bundles={bundles} setBundles={setBundles} />
    </div>
  );
}

function sharingBadge(upload: UploadItem, locale: SupportedLocale): string {
  const count = upload.allowedRecipientIds?.length ?? 0;
  if (!upload.shared || count === 0) return t(locale, "wallet.private");
  return tFormat(locale, "wallet.selectedCount", { count: String(count) });
}

type WalletFileSortMode = "newest" | "oldest" | "name" | "type" | "profile" | "storage";
type WalletFileFilterMode = "all" | "profiled" | "needs_proof" | "stored" | "shared";

function getWalletFileFilterOptions(locale: SupportedLocale): Array<{ label: string; value: WalletFileFilterMode }> {
  return [
    { label: t(locale, "wallet.filter.all"), value: "all" },
    { label: t(locale, "wallet.filter.profiled"), value: "profiled" },
    { label: t(locale, "wallet.filter.needsProof"), value: "needs_proof" },
    { label: t(locale, "wallet.filter.stored"), value: "stored" },
    { label: t(locale, "wallet.filter.shared"), value: "shared" }
  ];
}

function searchWalletFiles(
  uploads: UploadItem[],
  query: string,
  sortMode: WalletFileSortMode,
  filterMode: WalletFileFilterMode
): UploadItem[] {
  const filtered = filterWalletFilesByMode(uploads, filterMode);
  const tokens = query
    .trim()
    .toLocaleLowerCase()
    .split(/\s+/)
    .filter(Boolean);
  if (!tokens.length) return sortWalletFiles(filtered, sortMode);
  return filtered
    .map((upload) => ({ score: walletFileSearchScore(upload, tokens), upload }))
    .filter((item) => item.score > 0)
    .sort((left, right) => right.score - left.score || compareWalletFiles(left.upload, right.upload, sortMode))
    .map((item) => item.upload);
}

function filterWalletFilesByMode(uploads: UploadItem[], filterMode: WalletFileFilterMode): UploadItem[] {
  switch (filterMode) {
    case "profiled":
      return uploads.filter((upload) => upload.privacyProfileStatus === "profiled");
    case "needs_proof":
      return uploads.filter((upload) => upload.recordId && upload.privacyProfileStatus !== "profiled");
    case "stored":
      return uploads.filter((upload) => upload.decentralizedStorageStatus === "stored" || Boolean(upload.ipfsCid));
    case "shared":
      return uploads.filter((upload) => upload.shared || (upload.allowedRecipientIds?.length ?? 0) > 0);
    case "all":
    default:
      return uploads;
  }
}

function buildWalletFileStats(uploads: UploadItem[]) {
  return {
    ipldLinked: uploads.filter((upload) => upload.ipldLinks?.length || upload.metadataCid).length,
    profiled: uploads.filter((upload) => upload.privacyProfileStatus === "profiled").length
  };
}

function sortWalletFiles(uploads: UploadItem[], sortMode: WalletFileSortMode): UploadItem[] {
  const sorted = [...uploads];
  sorted.sort((left, right) => compareWalletFiles(left, right, sortMode));
  return sorted;
}

function compareWalletFiles(left: UploadItem, right: UploadItem, sortMode: WalletFileSortMode): number {
  switch (sortMode) {
    case "oldest":
      return uploadCreatedTime(left) - uploadCreatedTime(right);
    case "name":
      return left.fileName.localeCompare(right.fileName) || uploadCreatedTime(right) - uploadCreatedTime(left);
    case "type":
      return uploadTypeLabel(left).localeCompare(uploadTypeLabel(right)) || left.fileName.localeCompare(right.fileName);
    case "profile":
      return uploadProfileSortRank(left) - uploadProfileSortRank(right) || left.fileName.localeCompare(right.fileName);
    case "storage":
      return uploadStorageSortRank(left) - uploadStorageSortRank(right) || left.fileName.localeCompare(right.fileName);
    case "newest":
    default:
      return uploadCreatedTime(right) - uploadCreatedTime(left);
  }
}

function walletFileSearchScore(upload: UploadItem, tokens: string[]): number {
  const proofIndex = [
    upload.privacyProfileSearchText,
    upload.privacyProfileVectorTerms?.join(" "),
    stringifySearchRecord(upload.privacyProfilePublicInputs)
  ]
    .filter(Boolean)
    .join(" ")
    .toLocaleLowerCase();
  const visibleIndex = [
    upload.fileName,
    upload.category,
    upload.machineSummary,
    upload.decentralizedStorageProvider,
    upload.decentralizedStorageStatus,
    upload.decryptedClassification,
    upload.decryptedMimeType,
    upload.filecoinPinStatus,
    upload.privacyProfileClassification,
    upload.privacyProfileLabels?.join(" "),
    upload.privacyProfileMimeType,
    upload.privacyProfileStatus,
    upload.privacyProfileSummary,
    upload.status
  ]
    .filter(Boolean)
    .join(" ")
    .toLocaleLowerCase();
  let score = 0;
  for (const token of tokens) {
    if (proofIndex.includes(token)) {
      score += 4;
      continue;
    }
    if (visibleIndex.includes(token)) {
      score += 1;
    } else {
      return 0;
    }
  }
  if (upload.privacyProfileProofId) score += 0.5;
  if (upload.privacyProfileVectorTerms?.length) score += 0.5;
  return score;
}

function stringifySearchRecord(record: Record<string, unknown> | undefined): string {
  if (!record) return "";
  return Object.entries(record)
    .flatMap(([key, value]) => [key, ...searchValueParts(value)])
    .join(" ");
}

function searchValueParts(value: unknown): string[] {
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") return [String(value)];
  if (Array.isArray(value)) return value.flatMap(searchValueParts);
  if (value && typeof value === "object") return Object.values(value as Record<string, unknown>).flatMap(searchValueParts);
  return [];
}

function uploadCreatedTime(upload: UploadItem): number {
  const time = Date.parse(upload.createdAtRaw || upload.createdAt || "");
  return Number.isFinite(time) ? time : 0;
}

function uploadTypeLabel(upload: UploadItem): string {
  return upload.privacyProfileClassification || upload.decryptedClassification || upload.privacyProfileMimeType || upload.decryptedMimeType || upload.category;
}

function uploadProfileSortRank(upload: UploadItem): number {
  if (upload.privacyProfileStatus === "profiled") return 0;
  if (upload.privacyProfileStatus === "profiling") return 1;
  if (upload.privacyProfileStatus === "failed") return 2;
  return 3;
}

function uploadStorageSortRank(upload: UploadItem): number {
  if (upload.decentralizedStorageStatus === "stored" && upload.storageOk !== false) return 0;
  if (upload.decentralizedStorageStatus === "uploading") return 1;
  if (upload.storageOk === false) return 2;
  if (upload.decentralizedStorageStatus === "failed") return 3;
  return 4;
}

function filecoinBadge(upload: UploadItem, locale: SupportedLocale): string {
  if (upload.filecoinPinStatus === "queued") return t(locale, "wallet.filecoinQueued");
  if (upload.filecoinPinStatus === "pinning") return t(locale, "wallet.filecoinPinning");
  if (upload.filecoinPinStatus === "failed") return t(locale, "wallet.ipfsOnly");
  if (upload.decentralizedStorageStatus === "stored") return t(locale, "wallet.ipfsFilecoin");
  if (upload.decentralizedStorageStatus === "uploading") return t(locale, "wallet.storing");
  if (upload.decentralizedStorageStatus === "failed") return t(locale, "wallet.storageFailed");
  return t(locale, "wallet.walletStorage");
}

function filecoinBadgeTone(upload: UploadItem): "neutral" | "info" | "success" | "warning" | "danger" {
  if (upload.filecoinPinStatus === "queued" || upload.filecoinPinStatus === "pinning") return "info";
  if (upload.filecoinPinStatus === "failed") return "warning";
  if (upload.decentralizedStorageStatus === "stored") return "success";
  if (upload.decentralizedStorageStatus === "uploading") return "info";
  if (upload.decentralizedStorageStatus === "failed") return "danger";
  return "neutral";
}

function shouldShowFilecoinAction(upload: UploadItem): boolean {
  return upload.decentralizedStorageStatus !== "stored" || upload.filecoinPinStatus === "failed";
}

function filecoinActionLabel(upload: UploadItem, inProgress: boolean, locale: SupportedLocale): string {
  if (upload.filecoinPinStatus === "failed") {
    return inProgress ? t(locale, "wallet.retrying") : t(locale, "wallet.retryFilecoin");
  }
  return inProgress ? t(locale, "wallet.storing") : t(locale, "wallet.storeOnFilecoin");
}

function privacyProfileBadge(upload: UploadItem, locale: SupportedLocale): string {
  if (upload.privacyProfileStatus === "profiled") return t(locale, "wallet.privacyProof");
  if (upload.privacyProfileStatus === "profiling") return t(locale, "wallet.profiling");
  if (upload.privacyProfileStatus === "failed") return t(locale, "wallet.profileFailed");
  return t(locale, "wallet.profilePending");
}

function privacyProfileBadgeTone(upload: UploadItem): "neutral" | "info" | "success" | "warning" | "danger" {
  if (upload.privacyProfileStatus === "profiled") return "success";
  if (upload.privacyProfileStatus === "profiling") return "info";
  if (upload.privacyProfileStatus === "failed") return "warning";
  return "neutral";
}

function ipfsGatewayHref(upload: UploadItem): string {
  return normalizeIpfsGatewayUrl(upload.ipfsGatewayUrl) || sameOriginIpfsGatewayUrl(upload.ipfsCid) || "#";
}

function shortStorageId(value: string): string {
  return value.length > 18 ? `${value.slice(0, 10)}...${value.slice(-6)}` : value;
}

function base64ToBytes(value: string): Uint8Array {
  const binary = atob(value);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }
  return bytes;
}

function SocialServicesScreen({
  apiConfig,
  onOpenDetail,
  onOpenPlan,
  refreshWalletPortalState,
  savedServices,
  servicePlans,
  setSavedServices,
  siteLocale,
  walletPortalError,
  walletPortalLoading
}: {
  apiConfig?: WalletApiConfig;
  onOpenDetail: (docId: string) => void;
  onOpenPlan: (docId: string) => void;
  refreshWalletPortalState?: () => Promise<void>;
  savedServices: SavedService[];
  servicePlans: ServicePlan[];
  setSavedServices: (services: SavedService[]) => void;
  siteLocale: SupportedLocale;
  walletPortalError: string;
  walletPortalLoading: boolean;
}) {
  const categories = [
    { label: t(siteLocale, "services.category.shelter"), query: "Shelter" },
    { label: t(siteLocale, "services.category.food"), query: "Food" },
    { label: t(siteLocale, "services.category.health"), query: "Health" },
    { label: t(siteLocale, "services.category.legal"), query: "Legal" },
    { label: t(siteLocale, "services.category.benefits"), query: "Benefits" },
    { label: t(siteLocale, "services.category.transportation"), query: "Transportation" },
    { label: t(siteLocale, "services.category.employment"), query: "Employment" },
    { label: t(siteLocale, "services.category.crisis"), query: "Crisis" },
  ];
  const suggestedPrompts = [
    { label: t(siteLocale, "services.prompt.foodPantry"), query: "food pantry near Portland" },
    { label: t(siteLocale, "services.prompt.emergencyShelter"), query: "emergency shelter" },
    { label: t(siteLocale, "services.prompt.utilityHelp"), query: "utility bill help" },
  ];
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [resultLocationLabels, setResultLocationLabels] = useState<Record<string, string>>({});
  const [searchStatus, setSearchStatus] = useState<"idle" | "loading" | "complete" | "error">("idle");
  const [searchError, setSearchError] = useState("");
  const [savingDocIds, setSavingDocIds] = useState<string[]>([]);
  const [saveError, setSaveError] = useState("");
  const [catalogCounts, setCatalogCounts] = useState({
    serviceCount: 0,
    phoneCount: 0,
    addressCount: 0,
    intakeCount: 0
  });

  useEffect(() => {
    let canceled = false;
    load211GeneratedManifest()
      .then((manifest) => {
        if (canceled) return;
        setCatalogCounts({
          serviceCount: manifest.serviceDocumentCount ?? 0,
          phoneCount: manifest.servicePhoneCount ?? 0,
          addressCount: manifest.serviceAddressCount ?? 0,
          intakeCount: manifest.serviceIntakeStepCount ?? 0
        });
      })
      .catch(() => undefined);
    return () => {
      canceled = true;
    };
  }, []);

  async function runSearch(nextQuery = query) {
    const trimmedQuery = nextQuery.trim();
    if (!trimmedQuery) return;

    setQuery(trimmedQuery);
    setSearchStatus("loading");
    setSearchError("");
    try {
      const [searchResults, preferredClusterIds] = await Promise.all([
        search211Info(trimmedQuery, 18),
        resolvePreferred211ServiceClusterIds(trimmedQuery, 8).catch(() => []),
      ]);
      const visibleResults = searchResults.slice(0, 12);
      const locationRows = visibleResults.length
        ? await load211ServiceLocationsSlice({
            serviceDocIds: visibleResults.map((result) => result.docId),
          }).catch(() => [])
        : [];
      setResults(visibleResults);
      setResultLocationLabels(buildSearchResultLocationLabels(visibleResults, locationRows, preferredClusterIds));
      setSearchStatus("complete");
    } catch (error) {
      setResults([]);
      setResultLocationLabels({});
      setSearchStatus("error");
      setSearchError(error instanceof Error ? error.message : "Search failed");
    }
  }

  function handleSearchSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void runSearch();
  }

  async function saveResult(result: SearchResult) {
    if (savingDocIds.includes(result.docId)) return;
    setSavingDocIds([...savingDocIds, result.docId]);
    setSaveError("");
    try {
      const saved =
        apiConfig?.actorDid
          ? await saveWalletService(apiConfig, toSaveWalletServiceInput(result))
          : toLocalSavedService(result, apiConfig?.walletId);
      setSavedServices([saved, ...savedServices.filter((service) => service.saved_service_id !== saved.saved_service_id)]);
      await refreshWalletPortalState?.().catch(() => undefined);
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : "Service could not be saved.");
    } finally {
      setSavingDocIds((current) => current.filter((docId) => docId !== result.docId));
    }
  }

  return (
    <div className="screen">
      <div className="page-title">
        <p className="eyebrow">{t(siteLocale, "services.eyebrow")}</p>
        <h1>{t(siteLocale, "services.title")}</h1>
        {catalogCounts.serviceCount > 0 ? (
          <p className="supporting-copy">
            {tFormat(siteLocale, "services.indexedSummary", {
              serviceCount: formatCount(catalogCounts.serviceCount),
              phoneCount: formatCount(catalogCounts.phoneCount),
              addressCount: formatCount(catalogCounts.addressCount),
              intakeCount: formatCount(catalogCounts.intakeCount),
            })}
          </p>
        ) : null}
      </div>
      <Section title={catalogCounts.serviceCount > 0 ? tFormat(siteLocale, "services.searchIndexedTitle", { count: formatCount(catalogCounts.serviceCount) }) : t(siteLocale, "services.searchIndexTitle")}>
        <form className="form-grid" onSubmit={handleSearchSubmit}>
          <Field label={t(siteLocale, "services.searchLabel")}>
            <input
              placeholder={t(siteLocale, "services.searchPlaceholder")}
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
          </Field>
          <div className="row-actions">
            <Button disabled={!query.trim()} loading={searchStatus === "loading"} loadingLabel={t(siteLocale, "services.searching")} type="submit">
              {t(siteLocale, "services.searchButton")}
            </Button>
          </div>
        </form>
        <div className="chip-grid" aria-label={t(siteLocale, "services.suggestedSearches")}>
          {suggestedPrompts.map((prompt) => (
            <button className="choice-chip" key={prompt.query} onClick={() => void runSearch(prompt.query)} type="button">
              {prompt.label}
            </button>
          ))}
        </div>
        {searchStatus === "error" ? (
          <StatusBanner tone="warning">{tFormat(siteLocale, "services.searchUnavailable", { error: searchError })}</StatusBanner>
        ) : null}
        {saveError ? <StatusBanner tone="warning">{saveError}</StatusBanner> : null}
        {searchStatus === "complete" && results.length === 0 ? (
          <StatusBanner tone="info">{t(siteLocale, "services.noMatches")}</StatusBanner>
        ) : null}
        {results.length ? (
          <div className="list-stack" aria-label={t(siteLocale, "services.resultsAria")}>
            {results.map((result) => {
              const document = result.document;
              const provider = document.provider_name || t(siteLocale, "services.providerNotListed");
              const program = document.program_name || document.title || t(siteLocale, "services.programNotListed");
              const location = resultLocationLabels[result.docId] || getServiceLocationLabel(document);
              const intake = getPrimaryIntakeText(document);
              return (
                <article className="list-item" key={result.docId}>
                  <div>
                    <h3>{program}</h3>
                    <p>{provider}</p>
                    <small className="upload-machine-summary">{result.snippet}</small>
                    {intake ? <small className="upload-machine-summary">{t(siteLocale, "services.applyPrefix")}: {intake}</small> : null}
                    <div className="badge-row">
                      <Badge>{document.doc_type}</Badge>
                      {location ? (
                        <Badge>
                          {location}
                        </Badge>
                      ) : null}
                    </div>
                  </div>
                  <div className="row-actions list-item-action">
                    <ServiceQuickActions document={document} siteLocale={siteLocale} />
                    <Button
                      disabled={savedServices.some((service) => service.service_doc_id === result.docId)}
                      loading={savingDocIds.includes(result.docId)}
                      loadingLabel={t(siteLocale, "services.saving")}
                      onClick={() => void saveResult(result)}
                      variant="secondary"
                    >
                      <Save aria-hidden="true" size={18} />
                      {savedServices.some((service) => service.service_doc_id === result.docId) ? t(siteLocale, "services.saved") : t(siteLocale, "services.save")}
                    </Button>
                    <Button onClick={() => onOpenPlan(result.docId)} variant="secondary">
                      <CalendarClock aria-hidden="true" size={18} />
                      {t(siteLocale, "services.plan")}
                    </Button>
                    <Button onClick={() => onOpenDetail(result.docId)} variant="secondary">
                      {t(siteLocale, "services.openDetail")}
                    </Button>
                  </div>
                </article>
              );
            })}
          </div>
        ) : null}
      </Section>
      <SavedServicesPanel
        error={walletPortalError}
        loading={walletPortalLoading}
        onOpenDetail={onOpenDetail}
        onOpenPlan={onOpenPlan}
        onRefresh={refreshWalletPortalState ? () => void refreshWalletPortalState() : undefined}
        savedServices={savedServices}
        siteLocale={siteLocale}
        servicePlans={servicePlans}
      />
      <div className="category-grid">
        {categories.map((category) => (
          <button className="category-tile" key={category.query} onClick={() => void runSearch(category.query)} type="button">
            <HeartHandshake aria-hidden="true" size={22} />
            <span>{category.label}</span>
          </button>
        ))}
      </div>
      <Section title={t(siteLocale, "services.matchedServices")}>
        <div className="list-stack">
          {serviceMatches.map((service) => (
            <article className="list-item" key={service.id}>
              <div>
                <h3>{service.name}</h3>
                <p>
                  {service.category} · {service.distance}
                </p>
              </div>
              <Badge tone="success">{service.availability}</Badge>
            </article>
          ))}
        </div>
      </Section>
    </div>
  );
}

function toSaveWalletServiceInput(result: SearchResult) {
  const document = result.document;
  const title = document.program_name || document.provider_name || document.title || result.docId;
  return {
    serviceDocId: result.docId,
    sourceContentCid: result.contentCid || document.source_content_cid || `ui-unresolved-${appStableSuffix(result.docId)}`,
    sourcePageCid: result.pageCid || document.source_page_cid || "",
    title,
    providerName: document.provider_name || "",
    programName: document.program_name || document.title || "",
    sourceUrl: document.source_url || "",
    label: title,
    priority: "normal",
    reason: "",
    status: "saved",
    metadata: {
      saved_from: "services_search"
    }
  };
}

function toLocalSavedService(result: SearchResult, walletId = "local-wallet"): SavedService {
  const now = new Date().toISOString();
  const input = toSaveWalletServiceInput(result);
  return {
    created_at: now,
    label: input.label,
    metadata: input.metadata,
    priority: input.priority,
    private_notes_record_id: "",
    program_name: input.programName,
    provider_name: input.providerName,
    reason: input.reason,
    saved_service_id: `saved-local-${appStableSuffix(input.serviceDocId)}`,
    service_doc_id: input.serviceDocId,
    source_content_cid: input.sourceContentCid,
    source_page_cid: input.sourcePageCid,
    source_url: input.sourceUrl,
    status: input.status,
    title: input.title,
    updated_at: now,
    wallet_id: walletId
  };
}

function formatCount(value: number): string {
  return new Intl.NumberFormat("en-US").format(Math.max(0, Math.trunc(value || 0)));
}

type HomeServiceSuggestion = {
  need: string;
  result: SearchResult;
  locationLabel: string;
};

type HomeCalendarItem = {
  id: string;
  title: string;
  detail: string;
  kindLabel: string;
  urgencyLabel: string;
  urgencyTone: "neutral" | "warning" | "info";
  startsAt: Date;
  location?: string;
  serviceDocId?: string;
};

function buildHomeCalendarItems({
  policy,
  serviceInteractions,
  servicePlans,
}: {
  policy: CheckInPolicyDraft;
  serviceInteractions: ServiceInteractionEvent[];
  servicePlans: ServicePlan[];
}): HomeCalendarItem[] {
  const now = new Date();
  const twoWeeksAhead = now.getTime() + 14 * 24 * 60 * 60 * 1000;
  const items: HomeCalendarItem[] = [];

  for (const plan of servicePlans) {
    const startsAt = parseHomeDate(plan.appointment_at);
    if (!startsAt) continue;
    const urgency = describeHomeUrgency(startsAt, now);
    if (!urgency || startsAt.getTime() > twoWeeksAhead) continue;
    items.push({
      id: `plan:${plan.plan_id}`,
      title: plan.service_title || plan.provider_name || "Service appointment",
      detail: plan.goal || "Scheduled service appointment.",
      kindLabel: "Appointment",
      urgencyLabel: urgency.label,
      urgencyTone: urgency.tone,
      startsAt,
      location: plan.travel_target.trim() || undefined,
      serviceDocId: plan.service_doc_id || undefined,
    });
  }

  for (const interaction of serviceInteractions) {
    const startsAt = parseHomeDate(interaction.next_follow_up_at);
    if (!startsAt) continue;
    const urgency = describeHomeUrgency(startsAt, now);
    if (!urgency || startsAt.getTime() > twoWeeksAhead) continue;
    items.push({
      id: `follow-up:${interaction.interaction_id}`,
      title: interaction.next_action || interaction.program_name || interaction.provider_name || "Service follow-up",
      detail: interaction.outcome || interaction.program_name || "Follow up with this provider.",
      kindLabel: "Follow-up",
      urgencyLabel: urgency.label,
      urgencyTone: urgency.tone,
      startsAt,
      serviceDocId: interaction.service_doc_id || undefined,
    });
  }

  const nextCheckInAt = parseHomeDate(policy.lastCheckInAt);
  if (nextCheckInAt && policy.intervalDays > 0) {
    nextCheckInAt.setDate(nextCheckInAt.getDate() + policy.intervalDays);
    const urgency = describeHomeUrgency(nextCheckInAt, now);
    if (urgency) {
      items.push({
        id: `check-in:${policy.lastCheckInAt}:${policy.intervalDays}`,
        title: "Check in with Abby",
        detail: `Reminder channels: ${policy.reminderChannels.join(", ") || "web"}.`,
        kindLabel: "Check-in",
        urgencyLabel: urgency.label,
        urgencyTone: urgency.tone,
        startsAt: nextCheckInAt,
      });
    }
  }

  return items.sort((left, right) => left.startsAt.getTime() - right.startsAt.getTime());
}

function parseHomeDate(value: string): Date | null {
  if (!value.trim()) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

function describeHomeUrgency(
  startsAt: Date,
  now: Date,
): { label: string; tone: "neutral" | "warning" | "info" } | null {
  const deltaMs = startsAt.getTime() - now.getTime();
  const dayMs = 24 * 60 * 60 * 1000;
  if (deltaMs < 0) {
    return { label: "Overdue", tone: "warning" };
  }
  if (deltaMs <= dayMs) {
    return { label: "Today", tone: "warning" };
  }
  if (deltaMs <= 2 * dayMs) {
    return { label: "Tomorrow", tone: "warning" };
  }
  if (deltaMs <= 7 * dayMs) {
    return { label: `In ${Math.round(deltaMs / dayMs)} days`, tone: "info" };
  }
  return { label: formatShelterDate(startsAt.toISOString()), tone: "neutral" };
}

function formatHomeDateTime(value: Date): string {
  return value.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function buildSearchResultLocationLabels(
  results: SearchResult[],
  locationRows: ServiceLocationRecord[],
  preferredClusterIds: number[],
): Record<string, string> {
  const preferredClusterSet = new Set(preferredClusterIds);
  const rowsByDocId = new Map<string, ServiceLocationRecord[]>();
  for (const row of locationRows) {
    if (!row.service_doc_id) continue;
    const existing = rowsByDocId.get(row.service_doc_id) || [];
    existing.push(row);
    rowsByDocId.set(row.service_doc_id, existing);
  }

  const labels: Record<string, string> = {};
  for (const result of results) {
    const row = choosePreferredServiceLocation(rowsByDocId.get(result.docId) || [], preferredClusterSet);
    const label = formatServiceLocationLabel(row);
    if (label) {
      labels[result.docId] = label;
    }
  }
  return labels;
}

function choosePreferredServiceLocation(
  rows: ServiceLocationRecord[],
  preferredClusterIds: Set<number>,
): ServiceLocationRecord | null {
  if (!rows.length) return null;
  const rankedRows = [...rows].sort((left, right) => {
    const leftPreferred = left.geo_cluster_id != null && preferredClusterIds.has(left.geo_cluster_id) ? 1 : 0;
    const rightPreferred = right.geo_cluster_id != null && preferredClusterIds.has(right.geo_cluster_id) ? 1 : 0;
    if (leftPreferred !== rightPreferred) return rightPreferred - leftPreferred;
    const leftHasAddress = formatServiceLocationLabel(left) ? 1 : 0;
    const rightHasAddress = formatServiceLocationLabel(right) ? 1 : 0;
    if (leftHasAddress !== rightHasAddress) return rightHasAddress - leftHasAddress;
    return String(left.location_id).localeCompare(String(right.location_id));
  });
  return rankedRows[0] || null;
}

function formatServiceLocationLabel(location: ServiceLocationRecord | null | undefined): string {
  if (!location) return "";
  return (
    location.address ||
    location.maps_query ||
    [location.street, location.city, location.state, location.postal_code].filter(Boolean).join(", ")
  );
}

function appStableSuffix(value: string): string {
  let hash = 5381;
  for (let index = 0; index < value.length; index += 1) {
    hash = (hash * 33) ^ value.charCodeAt(index);
  }
  return (hash >>> 0).toString(36);
}

function ShelterScreen({
  checklist,
  setChecklist,
  contactRequests,
  navigate,
  profile,
  proofReceipts,
  shelterCaseRecords,
  providerMessages,
  recipients,
  siteLocale,
  setContactRequests,
  setShelterCaseRecords,
  setProofReceipts,
  setProviderMessages,
  setRecipients,
  shelterStaffAccounts,
  setShelterStaffAccounts,
  shelterUserAccounts,
  setShelterUserAccounts,
  view
}: {
  checklist: typeof defaultShelterChecklist;
  setChecklist: (value: typeof defaultShelterChecklist) => void;
  contactRequests: ShelterContactRequest[];
  navigate: (route: RouteId) => void;
  profile: RegistrationProfileDraft;
  proofReceipts: ProofReceiptView[];
  shelterCaseRecords: ShelterCaseRecord[];
  providerMessages: ShelterProviderMessage[];
  recipients: DisclosureRecipientDraft[];
  siteLocale: SupportedLocale;
  setContactRequests: (requests: ShelterContactRequest[]) => void;
  setShelterCaseRecords: (records: ShelterCaseRecord[]) => void;
  setProofReceipts: (proofs: ProofReceiptView[]) => void;
  setProviderMessages: (messages: ShelterProviderMessage[]) => void;
  setRecipients: (recipients: DisclosureRecipientDraft[]) => void;
  shelterStaffAccounts: ShelterStaffAccount[];
  setShelterStaffAccounts: (accounts: ShelterStaffAccount[]) => void;
  shelterUserAccounts: ShelterUserAccount[];
  setShelterUserAccounts: (accounts: ShelterUserAccount[]) => void;
  view: ProviderPortalView;
}) {
  const [isShelterAdmin, setIsShelterAdmin] = useState(false);
  const [adminShelter, setAdminShelter] = useState(shelterOptions[0]);
  const [operatorShelter, setOperatorShelter] = useState(shelterOptions[0]);
  const [operatorStaffId, setOperatorStaffId] = useState("");
  const [userDraft, setUserDraft] = useState(defaultManagedUserDraft);
  const [staffDraft, setStaffDraft] = useState({ displayName: "", email: "" });
  const [nudgeDraft, setNudgeDraft] = useState({ userName: "Abby Example", userContact: "abby@example.org" });
  const [managedUserFileDetail, setManagedUserFileDetail] = useState("");
  const [managedUserUploadError, setManagedUserUploadError] = useState("");
  const [messageDraft, setMessageDraft] = useState({
    clientId: "",
    channel: "sms" as ShelterProviderMessage["channel"],
    subject: t(siteLocale, "providerPortal.messages.defaultSubject"),
    body: t(siteLocale, "providerPortal.messages.defaultBody")
  });
  const [proofDraft, setProofDraft] = useState({
    clientId: "",
    proofType: "service_attendance",
    criterionId: "" as ShelterEligibilityCriterion | "",
    caseId: "",
    verifier: t(siteLocale, "providerPortal.proofs.defaultVerifier"),
    claim: t(siteLocale, "providerPortal.proofs.defaultClaim")
  });
  const [caseStatusFilter, setCaseStatusFilter] = useState<ShelterCaseStatus | "all">("all");

  const staffForShelter = shelterStaffAccounts.filter((account) => account.shelter === adminShelter);
  const verifiedStaffForOperatorShelter = shelterStaffAccounts.filter(
    (account) => account.shelter === operatorShelter && account.verified
  );
  const selectedOperator = shelterStaffAccounts.find((account) => account.id === operatorStaffId && account.verified);
  const activeProviderOperator = selectedOperator ?? verifiedStaffForOperatorShelter[0];
  const usersForOperatorShelter = shelterUserAccounts.filter((account) => account.shelter === operatorShelter);
  const caseRecordsForShelter = shelterCaseRecords.filter((record) => record.shelter === operatorShelter);
  const requestsForOperatorShelter = contactRequests.filter((request) => request.shelterName === operatorShelter);
  const providerMessagesForShelter = providerMessages
    .filter((message) => message.shelter === operatorShelter)
    .sort((left, right) => new Date(right.createdAt).getTime() - new Date(left.createdAt).getTime());
  const providerProofsForShelter = proofReceipts
    .filter((proof) => proof.proofType.startsWith("provider_") && proof.publicInputs.shelter === operatorShelter)
    .sort((left, right) => new Date(right.createdAt).getTime() - new Date(left.createdAt).getTime());
  const oversightShelter = isShelterAdmin ? adminShelter : operatorShelter;
  const partnerHelpDisplayName = profile.preferredName || profile.legalName || "Current client";
  const partnerHelpContact = [profile.phone, profile.email].map((item) => item.trim()).filter(Boolean).join(" / ");
  const partnerHelpNeeds = profile.serviceNeeds.length ? profile.serviceNeeds.join(", ") : "Needs not selected";

  function accountSortByHousingThenDate(a: ShelterUserAccount, b: ShelterUserAccount) {
    if (a.foundPermanentHousing !== b.foundPermanentHousing) {
      return a.foundPermanentHousing ? 1 : -1;
    }
    return new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime();
  }

  const staffRegisteredUsersForShelter = shelterUserAccounts
    .filter((account) => account.shelter === oversightShelter)
    .sort(accountSortByHousingThenDate);

  const preferredShelterMentionUsers = shelterUserAccounts
    .filter(
      (account) =>
        account.shelter !== oversightShelter &&
        account.preferredShelter.toLowerCase().includes(oversightShelter.toLowerCase())
    )
    .sort(accountSortByHousingThenDate);
  const selectedMessageClient = usersForOperatorShelter.find((account) => account.id === messageDraft.clientId);
  const selectedProofClient = usersForOperatorShelter.find((account) => account.id === proofDraft.clientId);
  const pendingContactRequestCount = requestsForOperatorShelter.filter((request) => request.status === "pending").length;
  const housedClientCount = usersForOperatorShelter.filter((account) => account.foundPermanentHousing).length;
  const activeClientCount = Math.max(0, usersForOperatorShelter.length - housedClientCount);
  const verifiedStaffCount = verifiedStaffForOperatorShelter.length;
  const allStaffForOperatorShelter = shelterStaffAccounts.filter((account) => account.shelter === operatorShelter);
  const unverifiedStaffCount = allStaffForOperatorShelter.filter((account) => !account.verified).length;
  const caseRows = caseRecordsForShelter
    .map((record) => ({
      record,
      client: usersForOperatorShelter.find((account) => account.id === record.clientId),
      caseManager: shelterStaffAccounts.find((account) => account.id === record.caseManagerStaffId)
    }))
    .filter((row): row is { record: ShelterCaseRecord; client: ShelterUserAccount; caseManager: ShelterStaffAccount | undefined } =>
      Boolean(row.client)
    )
    .filter((row) => caseStatusFilter === "all" || row.record.status === caseStatusFilter)
    .sort(
      (left, right) =>
        providerCasePriorityRank(left.record.priority) - providerCasePriorityRank(right.record.priority) ||
        new Date(left.record.dueDate).getTime() - new Date(right.record.dueDate).getTime()
    );
  const openCaseCount = caseRecordsForShelter.filter((record) => record.status !== "closed").length;
  const urgentCaseCount = caseRecordsForShelter.filter((record) => record.priority === "urgent" && record.status !== "closed").length;
  const waitingCaseCount = caseRecordsForShelter.filter((record) => record.status === "waiting_on_client").length;
  const eligibilityProofCount = providerProofsForShelter.filter((proof) => proof.publicInputs.eligibility_criterion).length;
  const clientAnalytics = usersForOperatorShelter.map((client) => {
    const clientMessages = providerMessagesForShelter.filter((message) => message.clientId === client.id);
    const clientProofs = providerProofsForShelter.filter(
      (proof) => proof.publicInputs.client_commitment === providerClientCommitment(client)
    );
    return {
      client,
      messageCount: clientMessages.length,
      proofCount: clientProofs.length,
      latestMessageAt: latestProviderTimestamp(clientMessages.map((message) => message.createdAt)),
      latestProofAt: latestProviderTimestamp(clientProofs.map((proof) => proof.createdAt))
    };
  });
  const clientsWithMessagesCount = clientAnalytics.filter((item) => item.messageCount > 0).length;
  const clientsWithProofsCount = clientAnalytics.filter((item) => item.proofCount > 0).length;
  const clientsWithoutMessagesCount = Math.max(0, usersForOperatorShelter.length - clientsWithMessagesCount);
  const clientsWithoutProofsCount = Math.max(0, usersForOperatorShelter.length - clientsWithProofsCount);
  const clientsMissingEmergencyContactCount = usersForOperatorShelter.filter(
    (account) => !account.localPrecinctNotified && !account.foundPermanentHousing
  ).length;
  const failedHealthCheckCount = usersForOperatorShelter.filter((account) => account.easyBotCheckStatus === "failed").length;
  const providerServiceNeedCounts = serviceNeeds
    .map((need) => ({
      need,
      count: usersForOperatorShelter.filter((account) => account.serviceNeeds.includes(need)).length
    }))
    .filter((item) => item.count > 0)
    .sort((left, right) => right.count - left.count || left.need.localeCompare(right.need));
  const topServiceNeed = providerServiceNeedCounts[0];
  const providerProofTypeCounts = providerProofsForShelter.reduce<Record<string, number>>((counts, proof) => {
    const proofType = proof.publicInputs.certificate_type || proof.proofType.replace("provider_", "");
    counts[proofType] = (counts[proofType] ?? 0) + 1;
    return counts;
  }, {});
  const providerProofTypeRows = Object.entries(providerProofTypeCounts).sort(
    ([leftType, leftCount], [rightType, rightCount]) => rightCount - leftCount || leftType.localeCompare(rightType)
  );
  const providerProofStaffRows = allStaffForOperatorShelter
    .map((staff) => {
      const proofs = providerProofsForShelter.filter((proof) => proof.publicInputs.staff_id === staff.id);
      return {
        staff,
        proofCount: proofs.length,
        latestProofAt: latestProviderTimestamp(proofs.map((proof) => proof.createdAt))
      };
    })
    .sort((left, right) => right.proofCount - left.proofCount || left.staff.displayName.localeCompare(right.staff.displayName));
  const providerRecentActivity: Array<{
    createdAt: string;
    detail: string;
    id: string;
    title: string;
    tone: "neutral" | "success" | "warning";
  }> = [
    ...usersForOperatorShelter.map((account) => ({
      id: `client-${account.id}`,
      title: tFormat(siteLocale, "providerPortal.analytics.activityClientAdded", {
        name: account.preferredName || account.legalName
      }),
      detail: tFormat(siteLocale, "providerPortal.analytics.activityClientDetail", {
        needs: account.serviceNeeds.length
          ? account.serviceNeeds.map((need) => translateServiceNeed(siteLocale, need)).join(", ")
          : t(siteLocale, "providerPortal.analytics.noNeedsSelected"),
        staff: shelterStaffAccounts.find((item) => item.id === account.createdByStaffId)?.displayName ?? t(siteLocale, "providerPortal.clients.staffFallback")
      }),
      tone: account.foundPermanentHousing ? ("success" as const) : ("warning" as const),
      createdAt: account.createdAt
    })),
    ...providerMessagesForShelter.map((message) => ({
      id: `message-${message.id}`,
      title: tFormat(siteLocale, "providerPortal.analytics.activityMessageSent", { name: message.clientName }),
      detail: tFormat(siteLocale, "providerPortal.analytics.activityMessageDetail", {
        staff: message.staffName,
        subject: message.subject
      }),
      tone: "neutral" as const,
      createdAt: message.createdAt
    })),
    ...providerProofsForShelter.map((proof) => ({
      id: `proof-${proof.id}`,
      title: tFormat(siteLocale, "providerPortal.analytics.activityProofProcessed", {
        name: providerProofClientLabel(proof, usersForOperatorShelter)
      }),
      detail: tFormat(siteLocale, "providerPortal.analytics.activityProofDetail", {
        certificate: providerProofTypeLabel(proof.publicInputs.certificate_type || proof.proofType.replace("provider_", ""), siteLocale),
        verifier: proof.verifier
      }),
      tone: "success" as const,
      createdAt: proof.createdAt
    })),
    ...requestsForOperatorShelter.map((request) => ({
      id: `request-${request.id}`,
      title: tFormat(siteLocale, "providerPortal.analytics.activityContactRequest", {
        status: formatContactRequestStatus(request.status, siteLocale)
      }),
      detail: tFormat(siteLocale, "providerPortal.analytics.activityContactRequestDetail", {
        direction:
          request.direction === "user_to_shelter"
            ? t(siteLocale, "providerPortal.analytics.clientInitiated")
            : t(siteLocale, "providerPortal.analytics.providerInitiated"),
        name: request.userName
      }),
      tone:
        request.status === "pending"
          ? ("warning" as const)
          : request.status === "approved"
            ? ("success" as const)
            : ("neutral" as const),
      createdAt: request.decidedAt ?? request.createdAt
    }))
  ].sort((left, right) => new Date(right.createdAt).getTime() - new Date(left.createdAt).getTime()).slice(0, 8);
  const staffAnalytics = shelterStaffAccounts
    .filter((account) => account.shelter === operatorShelter)
    .map((staff) => {
      const servedClients = usersForOperatorShelter.filter((account) => account.createdByStaffId === staff.id);
      const staffMessages = providerMessagesForShelter.filter((message) => message.staffId === staff.id);
      const staffProofs = providerProofsForShelter.filter((proof) => proof.publicInputs.staff_id === staff.id);
      const clientsWithProofs = servedClients.filter((client) =>
        staffProofs.some((proof) => proof.publicInputs.client_commitment === providerClientCommitment(client))
      ).length;
      return {
        staff,
        servedCount: servedClients.length,
        activeCount: servedClients.filter((account) => !account.foundPermanentHousing).length,
        housedCount: servedClients.filter((account) => account.foundPermanentHousing).length,
        messageCount: staffMessages.length,
        proofCount: staffProofs.length,
        clientsNeedingProofCount: Math.max(0, servedClients.length - clientsWithProofs),
        proofCoverage: formatProviderPercent(clientsWithProofs, servedClients.length),
        lastActivityAt:
          latestProviderTimestamp([
            staff.updatedAt,
            ...servedClients.map((account) => account.createdAt),
            ...staffMessages.map((message) => message.createdAt),
            ...staffProofs.map((proof) => proof.createdAt)
          ]) ?? staff.updatedAt
      };
    })
    .sort((left, right) => right.servedCount - left.servedCount || left.staff.displayName.localeCompare(right.staff.displayName));

  function toggleManagedUserNeed(need: string) {
    setUserDraft((prev) => ({
      ...prev,
      serviceNeeds: prev.serviceNeeds.includes(need)
        ? prev.serviceNeeds.filter((item) => item !== need)
        : [...prev.serviceNeeds, need]
    }));
  }

  function handleManagedUserUploadChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];

    if (!file) {
      setUserDraft({ ...userDraft, photoAssetId: "" });
      setManagedUserFileDetail("");
      setManagedUserUploadError("");
      return;
    }

    if (!isAcceptedIdentityDocument(file)) {
      setUserDraft({ ...userDraft, photoAssetId: "" });
      setManagedUserFileDetail("");
      setManagedUserUploadError(t(siteLocale, "providerPortal.operations.invalidUpload"));
      return;
    }

    setUserDraft({ ...userDraft, photoAssetId: file.name });
    setManagedUserFileDetail(getIdentityDocumentFileDetail(file));
    setManagedUserUploadError("");
  }

  function createManagedUserAccount(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const hasRequiredIdentity = userDraft.legalName.trim() && userDraft.photoAssetId;
    const botCheckReady =
      userDraft.easyBotCheckStatus === "failed" ||
      (userDraft.easyBotCheckStatus === "passed" && Boolean(userDraft.captchaToken));
    if (!selectedOperator || !hasRequiredIdentity || !botCheckReady) return;

    const newUser: ShelterUserAccount = {
      id: `user-${Date.now()}`,
      shelter: operatorShelter,
      legalName: userDraft.legalName.trim(),
      preferredName: userDraft.preferredName.trim(),
      pronouns: userDraft.pronouns.trim(),
      dateOfBirth: userDraft.dateOfBirth,
      photoAssetId: userDraft.photoAssetId,
      phone: userDraft.phone.trim(),
      email: userDraft.email.trim(),
      currentLocation: userDraft.currentLocation.trim(),
      preferredShelter: userDraft.preferredShelter.trim(),
      serviceNeeds: userDraft.serviceNeeds,
      easyBotCheckStatus: userDraft.easyBotCheckStatus,
      captchaToken: userDraft.captchaToken,
      localPrecinctNotified: userDraft.localPrecinctNotified,
      foundPermanentHousing: userDraft.foundPermanentHousing,
      createdByStaffId: selectedOperator.id,
      createdAt: new Date().toISOString()
    };
    setShelterUserAccounts([...shelterUserAccounts, newUser]);
    setShelterCaseRecords([
      ...shelterCaseRecords,
      {
        id: `case-${Date.now()}`,
        shelter: operatorShelter,
        clientId: newUser.id,
        caseManagerStaffId: selectedOperator.id,
        status: "intake",
        priority: userDraft.localPrecinctNotified ? "standard" : "urgent",
        goal: t(siteLocale, "providerPortal.operations.defaultCaseGoal"),
        nextStep: t(siteLocale, "providerPortal.operations.defaultCaseNextStep"),
        dueDate: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10),
        services: userDraft.serviceNeeds,
        notes: t(siteLocale, "providerPortal.operations.defaultCaseNotes"),
        eligibilityCriteria: ["identity_verified"],
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString()
      }
    ]);
    setUserDraft(defaultManagedUserDraft);
    setManagedUserFileDetail("");
    setManagedUserUploadError("");
  }

  function createStaffAccount(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!isShelterAdmin || !staffDraft.displayName.trim()) return;

    const newStaff: ShelterStaffAccount = {
      id: `staff-${Date.now()}`,
      shelter: adminShelter,
      displayName: staffDraft.displayName.trim(),
      email: staffDraft.email.trim(),
      verified: true,
      updatedAt: new Date().toISOString()
    };
    setShelterStaffAccounts([...shelterStaffAccounts, newStaff]);
    setStaffDraft({ displayName: "", email: "" });
  }

  function removeStaffAccount(staffId: string) {
    setShelterStaffAccounts(shelterStaffAccounts.filter((account) => account.id !== staffId));
    if (operatorStaffId === staffId) {
      setOperatorStaffId("");
    }
  }

  function updateStaffVerification(staffId: string, verified: boolean) {
    setShelterStaffAccounts(
      shelterStaffAccounts.map((item) =>
        item.id === staffId ? { ...item, verified, updatedAt: new Date().toISOString() } : item
      )
    );
    if (!verified && operatorStaffId === staffId) {
      setOperatorStaffId("");
    }
  }

  function shelterRecipientExists(shelterName: string) {
    return recipients.some((recipient) => recipient.type === "shelter_staff" && recipient.agencyName === shelterName);
  }

  function addShelterRecipient(shelterName: string) {
    if (shelterRecipientExists(shelterName)) return;

    setRecipients([
      ...recipients,
      {
        id: createEntityId("rec"),
        type: "shelter_staff",
        displayName: shelterName,
        relationship: "Shelter",
        email: "",
        phone: "",
        agencyName: shelterName,
        precinctName: "",
        verified: true,
        allowedScopes: ["identity_minimum"]
      }
    ]);
  }

  function hasPendingShelterNudge() {
    const nudgeContactKey = nudgeDraft.userContact.trim().toLowerCase();
    const nudgeNameKey = nudgeDraft.userName.trim().toLowerCase();
    return contactRequests.some(
      (request) =>
        request.status === "pending" &&
        request.shelterName === operatorShelter &&
        (request.userContact.trim().toLowerCase() === nudgeContactKey ||
          request.userName.trim().toLowerCase() === nudgeNameKey)
    );
  }

  function sendShelterNudge(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedOperator || !nudgeDraft.userName.trim() || !nudgeDraft.userContact.trim() || hasPendingShelterNudge()) {
      return;
    }

    setContactRequests([
      ...contactRequests,
      {
        id: `shelter-request-${Date.now()}`,
        direction: "shelter_to_user",
        status: "pending",
        shelterName: operatorShelter,
        userName: nudgeDraft.userName.trim(),
        userContact: nudgeDraft.userContact.trim(),
        staffId: selectedOperator.id,
        staffName: selectedOperator.displayName,
        createdAt: new Date().toISOString()
      }
    ]);
  }

  function prepareProviderMessage(client: ShelterUserAccount) {
    setMessageDraft({
      clientId: client.id,
      channel: client.phone ? "sms" : client.email ? "email" : "in_app",
      subject: t(siteLocale, "providerPortal.messages.serviceReminderSubject"),
      body: tFormat(siteLocale, "providerPortal.messages.serviceReminderBody", {
        client: client.preferredName || client.legalName,
        shelter: operatorShelter,
        staff: activeProviderOperator?.displayName ?? t(siteLocale, "providerPortal.messages.senderFallback")
      })
    });
    navigate("provider-messages");
  }

  function prepareCaseMessage(caseRecord: ShelterCaseRecord, client: ShelterUserAccount) {
    setMessageDraft({
      clientId: client.id,
      channel: client.phone ? "sms" : client.email ? "email" : "in_app",
      subject: tFormat(siteLocale, "providerPortal.messages.caseUpdateSubject", { goal: caseRecord.goal }),
      body: tFormat(siteLocale, "providerPortal.messages.caseUpdateBody", {
        client: client.preferredName || client.legalName,
        shelter: operatorShelter,
        staff: activeProviderOperator?.displayName ?? t(siteLocale, "providerPortal.messages.senderFallback"),
        step: caseRecord.nextStep
      })
    });
    navigate("provider-messages");
  }

  function sendProviderMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!activeProviderOperator || !selectedMessageClient || !messageDraft.body.trim()) return;

    const nextMessage: ShelterProviderMessage = {
      id: `provider-message-${Date.now()}`,
      shelter: operatorShelter,
      clientId: selectedMessageClient.id,
      clientName: selectedMessageClient.preferredName || selectedMessageClient.legalName,
      clientContact: contactLabelForShelterUser(selectedMessageClient, siteLocale),
      channel: messageDraft.channel,
      subject: messageDraft.subject.trim() || t(siteLocale, "providerPortal.messages.fallbackSubject"),
      body: messageDraft.body.trim(),
      staffId: activeProviderOperator.id,
      staffName: activeProviderOperator.displayName,
      status: "sent",
      createdAt: new Date().toISOString()
    };
    setProviderMessages([nextMessage, ...providerMessages]);
  }

  function prepareProviderProof(client: ShelterUserAccount) {
    setProofDraft({
      clientId: client.id,
      proofType: "service_attendance",
      criterionId: "",
      caseId: "",
      verifier: tFormat(siteLocale, "providerPortal.proofs.certificateVerifier", { shelter: operatorShelter }),
      claim: t(siteLocale, "providerPortal.proofs.certificateClaim")
    });
    navigate("provider-proofs");
  }

  function prepareEligibilityProof(
    client: ShelterUserAccount,
    criterionId: ShelterEligibilityCriterion,
    caseRecord?: ShelterCaseRecord
  ) {
    setProofDraft({
      clientId: client.id,
      proofType: providerEligibilityCriteria.find((item) => item.id === criterionId)?.certificateType ?? "eligibility",
      criterionId,
      caseId: caseRecord?.id ?? "",
      verifier: tFormat(siteLocale, "providerPortal.proofs.eligibilityVerifier", { shelter: operatorShelter }),
      claim: providerEligibilityClaim(criterionId, siteLocale)
    });
    navigate("provider-proofs");
  }

  function selectProofCriterion(criterionId: ShelterEligibilityCriterion | "") {
    const criterion = providerEligibilityCriteria.find((item) => item.id === criterionId);
    setProofDraft({
      ...proofDraft,
      criterionId,
      proofType: criterion?.certificateType ?? proofDraft.proofType,
      claim: criterionId ? providerEligibilityClaim(criterionId, siteLocale) : proofDraft.claim
    });
  }

  function updateCaseRecord(caseId: string, patch: Partial<ShelterCaseRecord>) {
    setShelterCaseRecords(
      shelterCaseRecords.map((record) =>
        record.id === caseId ? { ...record, ...patch, updatedAt: new Date().toISOString() } : record
      )
    );
  }

  function processProviderProofCertificate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!activeProviderOperator || !selectedProofClient || !proofDraft.claim.trim() || !proofDraft.verifier.trim()) return;

    const createdAt = new Date().toISOString();
    const proofSeed = [
      operatorShelter,
      selectedProofClient.id,
      activeProviderOperator.id,
      proofDraft.proofType,
      proofDraft.claim,
      createdAt
    ].join("|");
    const proof: ProofReceiptView = {
      id: `provider-proof-${Date.now()}`,
      proofType: `provider_${proofDraft.proofType}`,
      claim: proofDraft.claim.trim(),
      verifier: proofDraft.verifier.trim(),
      proofSystem: "simulated_zk_certificate",
      verificationStatus: "verified",
      circuitId: `provider-${proofDraft.proofType}-v1`,
      verifierDigest: appStableSuffix(proofSeed),
      proofArtifactRef: `zk-cert-${appStableSuffix(`${proofSeed}:artifact`)}`,
      publicInputs: {
        shelter: operatorShelter,
        client_commitment: appStableSuffix(`${selectedProofClient.id}:${selectedProofClient.dateOfBirth}`),
        staff_id: activeProviderOperator.id,
        certificate_type: proofDraft.proofType,
        ...(proofDraft.criterionId
          ? {
              eligibility_criterion: proofDraft.criterionId,
              eligibility_result: "meets_criteria"
            }
          : {}),
        ...(proofDraft.caseId ? { case_id: proofDraft.caseId } : {}),
        issued_at: createdAt
      },
      witnessLabel: `${selectedProofClient.preferredName || selectedProofClient.legalName} service record`,
      simulated: true,
      createdAt
    };

    setProofReceipts([proof, ...proofReceipts.filter((item) => item.id !== proof.id)]);
  }

  function decideUserShelterRequest(requestId: string, status: "approved" | "denied") {
    const request = contactRequests.find((item) => item.id === requestId);
    if (!request) return;

    if (status === "approved") {
      addShelterRecipient(request.shelterName);
    }

    setContactRequests(
      contactRequests.map((item) =>
        item.id === requestId ? { ...item, status, decidedAt: new Date().toISOString() } : item
      )
    );
  }

  const providerViewTitle: Record<ProviderPortalView, string> = {
    overview: t(siteLocale, "providerPortal.view.overview"),
    clients: t(siteLocale, "providerPortal.view.clients"),
    cases: t(siteLocale, "providerPortal.view.cases"),
    messages: t(siteLocale, "providerPortal.view.messages"),
    analytics: t(siteLocale, "providerPortal.view.analytics"),
    proofs: t(siteLocale, "providerPortal.view.proofs"),
    operations: t(siteLocale, "providerPortal.view.operations")
  };

  return (
    <div className="screen">
      <div className="page-title">
        <p className="eyebrow">{t(siteLocale, "providerPortal.eyebrow")}</p>
        <h1>{providerViewTitle[view]}</h1>
      </div>
      <p className="page-note">{t(siteLocale, "providerPortal.note")}</p>
      <Section title={t(siteLocale, "providerPortal.workspace")}>
        <div className="provider-workspace-controls">
          <Field label={t(siteLocale, "providerPortal.organization")} required>
            <select
              value={operatorShelter}
              onChange={(event) => {
                setOperatorShelter(event.target.value);
                setOperatorStaffId("");
              }}
            >
              {shelterOptions.map((shelter) => (
                <option key={shelter} value={shelter}>
                  {shelter}
                </option>
              ))}
            </select>
          </Field>
          <Field help={t(siteLocale, "providerPortal.staffIdentityHelp")} label={t(siteLocale, "providerPortal.staffIdentity")}>
            <select value={operatorStaffId} onChange={(event) => setOperatorStaffId(event.target.value)}>
              <option value="">{t(siteLocale, "providerPortal.defaultVerifiedStaff")}</option>
              {verifiedStaffForOperatorShelter.map((staff) => (
                <option key={staff.id} value={staff.id}>
                  {staff.displayName}
                </option>
              ))}
            </select>
          </Field>
          <div className="provider-route-actions" aria-label={t(siteLocale, "providerPortal.routeShortcuts")}>
            <Button onClick={() => navigate("provider-clients")} variant="secondary">
              <ContactRound aria-hidden="true" size={18} />
              {t(siteLocale, "providerPortal.shortcut.clients")}
            </Button>
            <Button onClick={() => navigate("provider-cases")} variant="secondary">
              <ClipboardCheck aria-hidden="true" size={18} />
              {t(siteLocale, "providerPortal.shortcut.cases")}
            </Button>
            <Button onClick={() => navigate("provider-messages")} variant="secondary">
              <MessageSquare aria-hidden="true" size={18} />
              {t(siteLocale, "providerPortal.shortcut.messages")}
            </Button>
            <Button onClick={() => navigate("provider-proofs")} variant="secondary">
              <ShieldCheck aria-hidden="true" size={18} />
              {t(siteLocale, "providerPortal.shortcut.proofs")}
            </Button>
          </div>
        </div>
      </Section>
      {view === "overview" ? (
        <>
      <Section title={t(siteLocale, "providerPortal.staffTools")}>
        <div className="tool-grid">
          <button className="tool-tile" onClick={() => navigate("provider-operations")} type="button">
            <ClipboardCheck size={24} /> {t(siteLocale, "providerPortal.tool.assistRegistration")}
          </button>
          <button className="tool-tile" onClick={() => navigate("provider-operations")} type="button">
            <UsersRound size={24} /> {t(siteLocale, "providerPortal.tool.verifyContact")}
          </button>
          <button className="tool-tile" onClick={() => navigate("provider-cases")} type="button">
            <ClipboardCheck size={24} /> {t(siteLocale, "providerPortal.tool.manageCases")}
          </button>
          <button className="tool-tile" onClick={() => navigate("provider-analytics")} type="button">
            <ShieldCheck size={24} /> {t(siteLocale, "providerPortal.tool.reviewAudit")}
          </button>
        </div>
      </Section>
      {profile.servicePartnerHelpRequested ? (
        <Section title={t(siteLocale, "providerPortal.partnerHelp")}>
          <article className="list-item partner-help-request">
            <div>
              <h3>{partnerHelpDisplayName}</h3>
              <p>{t(siteLocale, "providerPortal.partnerHelpDescription")}</p>
              <div className="badge-row">
                <Badge tone="warning">{t(siteLocale, "providerPortal.needsPartnerHelp")}</Badge>
                <Badge>{formatRequestTimestamp(profile.servicePartnerHelpRequestedAt, siteLocale)}</Badge>
                <Badge>{partnerHelpNeeds}</Badge>
              </div>
              <small>{partnerHelpContact || t(siteLocale, "providerPortal.noContactMethod")}</small>
            </div>
          </article>
        </Section>
      ) : null}
      <Section title={t(siteLocale, "providerPortal.overview")}>
        <div className="dashboard-grid">
          <StatusPanel label={t(siteLocale, "providerPortal.overview.clientsServed")} value={String(usersForOperatorShelter.length)} tone="teal" />
          <StatusPanel label={t(siteLocale, "providerPortal.overview.openCases")} value={String(openCaseCount)} tone="teal" />
          <StatusPanel label={t(siteLocale, "providerPortal.overview.activeSupport")} value={String(activeClientCount)} tone="gold" />
          <StatusPanel label={t(siteLocale, "providerPortal.overview.urgentCases")} value={String(urgentCaseCount)} tone="red" />
          <StatusPanel label={t(siteLocale, "providerPortal.overview.messagesSent")} value={String(providerMessagesForShelter.length)} tone="teal" />
          <StatusPanel label={t(siteLocale, "providerPortal.overview.zkCertificates")} value={String(providerProofsForShelter.length)} tone="gold" />
          <StatusPanel label={t(siteLocale, "providerPortal.overview.verifiedStaff")} value={String(verifiedStaffCount)} tone="teal" />
          <StatusPanel label={t(siteLocale, "providerPortal.overview.pendingRequests")} value={String(pendingContactRequestCount)} tone="red" />
        </div>
        <p className="section-note">
          {t(siteLocale, "providerPortal.overviewNote")}
        </p>
      </Section>
        </>
      ) : null}
      {view === "clients" ? (
      <Section title={t(siteLocale, "providerPortal.view.clients")}>
        <div className="list-stack provider-client-list">
          {usersForOperatorShelter.length ? (
            usersForOperatorShelter.map((account) => (
              <article className="list-item provider-client-item" key={`served-${account.id}`}>
                <div>
                  <h3>{account.preferredName || account.legalName}</h3>
                  <p>{account.serviceNeeds.length ? account.serviceNeeds.join(", ") : t(siteLocale, "providerPortal.clients.noServiceNeeds")}</p>
                  <small>
                    {tFormat(siteLocale, "providerPortal.clients.servedBy", {
                      name: shelterStaffAccounts.find((item) => item.id === account.createdByStaffId)?.displayName ?? t(siteLocale, "providerPortal.clients.staffFallback")
                    })}
                    {" · "}
                    {formatShelterDate(account.createdAt)}
                  </small>
                  <div className="badge-row">
                    <Badge>{contactLabelForShelterUser(account, siteLocale)}</Badge>
                    <Badge tone={account.foundPermanentHousing ? "success" : "warning"}>
                      {account.foundPermanentHousing ? t(siteLocale, "providerPortal.clients.housingFound") : t(siteLocale, "providerPortal.clients.needsSupport")}
                    </Badge>
                    <Badge tone={account.localPrecinctNotified ? "success" : "neutral"}>
                      {account.localPrecinctNotified ? t(siteLocale, "providerPortal.clients.emergencyContactSet") : t(siteLocale, "providerPortal.clients.noPrecinctContact")}
                    </Badge>
                  </div>
                </div>
                <div className="row-actions">
                  <Button disabled={!activeProviderOperator} onClick={() => prepareProviderMessage(account)} variant="secondary">
                    <MessageSquare aria-hidden="true" size={18} />
                    {t(siteLocale, "providerPortal.clients.message")}
                  </Button>
                  <Button disabled={!activeProviderOperator} onClick={() => prepareProviderProof(account)} variant="secondary">
                    <ShieldCheck aria-hidden="true" size={18} />
                    {t(siteLocale, "providerPortal.clients.zkCertificate")}
                  </Button>
                </div>
              </article>
            ))
          ) : (
            <div className="empty-state">
              <h3>{t(siteLocale, "providerPortal.clients.emptyTitle")}</h3>
              <p>{t(siteLocale, "providerPortal.clients.emptyBody")}</p>
            </div>
          )}
        </div>
      </Section>
      ) : null}
      {view === "cases" ? (
        <>
          <Section title={t(siteLocale, "providerPortal.cases.title")}>
            <div className="dashboard-grid">
              <StatusPanel label={t(siteLocale, "providerPortal.cases.openCases")} value={String(openCaseCount)} tone="teal" />
              <StatusPanel label={t(siteLocale, "providerPortal.cases.urgentCases")} value={String(urgentCaseCount)} tone="red" />
              <StatusPanel label={t(siteLocale, "providerPortal.cases.waitingOnClient")} value={String(waitingCaseCount)} tone="gold" />
              <StatusPanel label={t(siteLocale, "providerPortal.cases.eligibilityProofs")} value={String(eligibilityProofCount)} tone="teal" />
            </div>
            <div className="message-toolbar">
              <Field label={t(siteLocale, "providerPortal.cases.caseStatus")}>
                <select value={caseStatusFilter} onChange={(event) => setCaseStatusFilter(event.target.value as typeof caseStatusFilter)}>
                  <option value="all">{t(siteLocale, "providerPortal.cases.allCases")}</option>
                  <option value="intake">{t(siteLocale, "providerPortal.cases.intake")}</option>
                  <option value="active">{t(siteLocale, "providerPortal.cases.active")}</option>
                  <option value="waiting_on_client">{t(siteLocale, "providerPortal.cases.waitingOnClient")}</option>
                  <option value="eligible">{t(siteLocale, "providerPortal.cases.eligible")}</option>
                  <option value="closed">{t(siteLocale, "providerPortal.cases.closed")}</option>
                </select>
              </Field>
            </div>
            <div className="list-stack provider-case-list">
              {caseRows.length ? (
                caseRows.map(({ record, client, caseManager }) => {
                  const clientProofs = providerProofsForShelter.filter(
                    (proof) =>
                      proof.publicInputs.client_commitment === providerClientCommitment(client) &&
                      (!proof.publicInputs.case_id || proof.publicInputs.case_id === record.id)
                  );
                  return (
                    <article className="list-item provider-case-item" key={record.id}>
                      <div>
                        <h3>{client.preferredName || client.legalName}</h3>
                        <p>{record.goal}</p>
                        <div className="badge-row">
                          <Badge tone={record.priority === "urgent" ? "warning" : "neutral"}>
                            {providerCasePriorityLabel(record.priority, siteLocale)}
                          </Badge>
                          <Badge>{providerCaseStatusLabel(record.status, siteLocale)}</Badge>
                          <Badge>{tFormat(siteLocale, "providerPortal.cases.due", { date: formatShelterDate(record.dueDate) })}</Badge>
                          <Badge>{caseManager?.displayName ?? t(siteLocale, "providerPortal.cases.unassigned")}</Badge>
                          <Badge>
                            {clientProofs.length} {t(siteLocale, clientProofs.length === 1 ? "providerPortal.cases.proofSingular" : "providerPortal.cases.proofPlural")}
                          </Badge>
                        </div>
                        <small>
                          {record.services.length
                            ? record.services.map((service) => translateServiceNeed(siteLocale, service)).join(", ")
                            : t(siteLocale, "providerPortal.cases.noServices")}
                        </small>
                      </div>
                      <div className="provider-case-controls">
                        <Field label={t(siteLocale, "providerPortal.cases.statusField")}>
                          <select
                            value={record.status}
                            onChange={(event) =>
                              updateCaseRecord(record.id, { status: event.target.value as ShelterCaseStatus })
                            }
                          >
                            <option value="intake">{t(siteLocale, "providerPortal.cases.intake")}</option>
                            <option value="active">{t(siteLocale, "providerPortal.cases.active")}</option>
                            <option value="waiting_on_client">{t(siteLocale, "providerPortal.cases.waitingOnClient")}</option>
                            <option value="eligible">{t(siteLocale, "providerPortal.cases.eligible")}</option>
                            <option value="closed">{t(siteLocale, "providerPortal.cases.closed")}</option>
                          </select>
                        </Field>
                        <Field label={t(siteLocale, "providerPortal.cases.priorityField")}>
                          <select
                            value={record.priority}
                            onChange={(event) =>
                              updateCaseRecord(record.id, { priority: event.target.value as ShelterCasePriority })
                            }
                          >
                            <option value="urgent">{t(siteLocale, "providerPortal.cases.urgent")}</option>
                            <option value="standard">{t(siteLocale, "providerPortal.cases.standard")}</option>
                            <option value="monitor">{t(siteLocale, "providerPortal.cases.monitor")}</option>
                          </select>
                        </Field>
                        <Field label={t(siteLocale, "providerPortal.cases.dueDate")}>
                          <input
                            type="date"
                            value={record.dueDate}
                            onChange={(event) => updateCaseRecord(record.id, { dueDate: event.target.value })}
                          />
                        </Field>
                        <Field label={t(siteLocale, "providerPortal.cases.nextStep")}>
                          <input
                            value={record.nextStep}
                            onChange={(event) => updateCaseRecord(record.id, { nextStep: event.target.value })}
                          />
                        </Field>
                        <Field label={t(siteLocale, "providerPortal.cases.notes")}>
                          <textarea
                            rows={3}
                            value={record.notes}
                            onChange={(event) => updateCaseRecord(record.id, { notes: event.target.value })}
                          />
                        </Field>
                      </div>
                      <div className="provider-case-criteria">
                        {record.eligibilityCriteria.map((criterionId) => {
                          const proven = clientProofs.some(
                            (proof) => proof.publicInputs.eligibility_criterion === criterionId
                          );
                          return (
                            <div className="provider-case-criterion" key={`${record.id}-${criterionId}`}>
                              <Badge tone={proven ? "success" : "warning"}>
                                {providerEligibilityLabel(criterionId, siteLocale)} {t(siteLocale, proven ? "providerPortal.cases.proved" : "providerPortal.cases.needed")}
                              </Badge>
                              <Button
                                disabled={!activeProviderOperator}
                                onClick={() => prepareEligibilityProof(client, criterionId, record)}
                                variant="secondary"
                              >
                                {criterionId === "us_citizen"
                                  ? t(siteLocale, "providerPortal.cases.proveUsCitizen")
                                  : t(siteLocale, "providerPortal.cases.prepareProof")}
                              </Button>
                            </div>
                          );
                        })}
                      </div>
                      <div className="row-actions">
                        <Button disabled={!activeProviderOperator} onClick={() => prepareCaseMessage(record, client)} variant="secondary">
                          <MessageSquare aria-hidden="true" size={18} />
                          {t(siteLocale, "providerPortal.cases.messageClient")}
                        </Button>
                        <Button
                          disabled={!activeProviderOperator}
                          onClick={() => prepareEligibilityProof(client, record.eligibilityCriteria[0] ?? "identity_verified", record)}
                          variant="secondary"
                        >
                          <ShieldCheck aria-hidden="true" size={18} />
                          {t(siteLocale, "providerPortal.cases.eligibilityProof")}
                        </Button>
                      </div>
                    </article>
                  );
                })
              ) : (
                <div className="empty-state">
                  <h3>{t(siteLocale, "providerPortal.cases.emptyTitle")}</h3>
                  <p>{t(siteLocale, "providerPortal.cases.emptyBody")}</p>
                </div>
              )}
            </div>
          </Section>
        </>
      ) : null}
      {view === "messages" ? (
      <Section title={t(siteLocale, "providerPortal.messages.title")}>
        {!activeProviderOperator ? (
          <StatusBanner tone="info">{t(siteLocale, "providerPortal.messages.needStaff")}</StatusBanner>
        ) : !selectedOperator ? (
          <StatusBanner tone="info">
            {tFormat(siteLocale, "providerPortal.messages.defaultSender", { name: activeProviderOperator.displayName })}
          </StatusBanner>
        ) : null}
        <form className="form-grid provider-message-form" id="provider-message-composer" onSubmit={sendProviderMessage}>
          <Field label={t(siteLocale, "providerPortal.messages.client")} required>
            <select
              value={messageDraft.clientId}
              onChange={(event) => setMessageDraft({ ...messageDraft, clientId: event.target.value })}
            >
              <option value="">{t(siteLocale, "providerPortal.messages.selectClient")}</option>
              {usersForOperatorShelter.map((account) => (
                <option key={`message-${account.id}`} value={account.id}>
                  {account.preferredName || account.legalName}
                </option>
              ))}
            </select>
          </Field>
          <Field label={t(siteLocale, "providerPortal.messages.channel")} required>
            <select
              value={messageDraft.channel}
              onChange={(event) =>
                setMessageDraft({ ...messageDraft, channel: event.target.value as ShelterProviderMessage["channel"] })
              }
            >
              <option value="sms">{t(siteLocale, "channel.sms")}</option>
              <option value="email">{t(siteLocale, "channel.email")}</option>
              <option value="in_app">{t(siteLocale, "messages.inApp")}</option>
            </select>
          </Field>
          <Field label={t(siteLocale, "providerPortal.messages.subject")}>
            <input
              value={messageDraft.subject}
              onChange={(event) => setMessageDraft({ ...messageDraft, subject: event.target.value })}
            />
          </Field>
          <Field label={t(siteLocale, "providerPortal.messages.body")} required>
            <textarea
              rows={4}
              value={messageDraft.body}
              onChange={(event) => setMessageDraft({ ...messageDraft, body: event.target.value })}
            />
          </Field>
          <div className="full-span row-actions">
            <Button
              disabled={!activeProviderOperator || !selectedMessageClient || !messageDraft.body.trim()}
              type="submit"
            >
              <MessageSquare aria-hidden="true" size={18} />
              {t(siteLocale, "providerPortal.messages.send")}
            </Button>
          </div>
        </form>
        <div className="list-stack">
          {providerMessagesForShelter.length ? (
            providerMessagesForShelter.slice(0, 6).map((message) => (
              <article className="list-item provider-message-item" key={message.id}>
                <div>
                  <h3>{message.subject}</h3>
                  <p>{message.body}</p>
                  <div className="badge-row">
                    <Badge>{message.clientName}</Badge>
                    <Badge>{formatProviderMessageChannel(message.channel, siteLocale)}</Badge>
                    <Badge tone="success">{message.status}</Badge>
                    <Badge>{formatShelterDate(message.createdAt)}</Badge>
                  </div>
                  <small>
                    {tFormat(siteLocale, "providerPortal.messages.sentByTo", {
                      contact: message.clientContact,
                      staff: message.staffName
                    })}
                  </small>
                </div>
              </article>
            ))
          ) : (
            <small>{t(siteLocale, "providerPortal.messages.empty")}</small>
          )}
        </div>
      </Section>
      ) : null}
      {view === "analytics" ? (
        <>
          <Section title={t(siteLocale, "providerPortal.analytics.title")}>
            <div className="dashboard-grid">
              <StatusPanel label={t(siteLocale, "providerPortal.analytics.housingRate")} value={formatProviderPercent(housedClientCount, usersForOperatorShelter.length)} tone="teal" />
              <StatusPanel label={t(siteLocale, "providerPortal.analytics.messageReach")} value={formatProviderPercent(clientsWithMessagesCount, usersForOperatorShelter.length)} tone="gold" />
              <StatusPanel label={t(siteLocale, "providerPortal.analytics.proofCoverage")} value={formatProviderPercent(clientsWithProofsCount, usersForOperatorShelter.length)} tone="teal" />
              <StatusPanel label={t(siteLocale, "providerPortal.analytics.missingContact")} value={String(clientsMissingEmergencyContactCount)} tone="red" />
              <StatusPanel label={t(siteLocale, "providerPortal.analytics.healthChecks")} value={String(failedHealthCheckCount)} tone="gold" />
              <StatusPanel label={t(siteLocale, "providerPortal.analytics.staffInactive")} value={String(unverifiedStaffCount)} tone="red" />
            </div>
            <div className="provider-insight-grid">
              <article className="provider-insight-card">
                <h3>{t(siteLocale, "providerPortal.analytics.clientSupportSignals")}</h3>
                <p>
                  {tFormat(siteLocale, "providerPortal.analytics.activeClientsNeedSupport", {
                    count: String(activeClientCount),
                    label: activeClientCount === 1 ? t(siteLocale, "providerPortal.analytics.clientSingular") : t(siteLocale, "providerPortal.analytics.clientPlural")
                  })}{" "}
                  {topServiceNeed
                    ? tFormat(siteLocale, "providerPortal.analytics.topNeed", {
                        need: translateServiceNeed(siteLocale, topServiceNeed.need)
                      })
                    : t(siteLocale, "providerPortal.analytics.noNeedsSelected")}
                </p>
                <div className="provider-staff-metrics" aria-label={t(siteLocale, "providerPortal.analytics.clientSupportMetrics")}>
                  <span><strong>{clientsWithoutMessagesCount}</strong> {t(siteLocale, "providerPortal.analytics.noMessages")}</span>
                  <span><strong>{clientsWithoutProofsCount}</strong> {t(siteLocale, "providerPortal.analytics.noProofs")}</span>
                  <span><strong>{pendingContactRequestCount}</strong> {t(siteLocale, "providerPortal.analytics.pendingRequests")}</span>
                </div>
              </article>
              <article className="provider-insight-card">
                <h3>{t(siteLocale, "providerPortal.analytics.staffPicture")}</h3>
                <p>
                  {tFormat(siteLocale, "providerPortal.analytics.staffCanAct", {
                    count: String(verifiedStaffCount),
                    label: verifiedStaffCount === 1 ? t(siteLocale, "providerPortal.analytics.staffMemberSingular") : t(siteLocale, "providerPortal.analytics.staffMemberPlural"),
                    shelter: operatorShelter
                  })}{" "}
                  {unverifiedStaffCount
                    ? tFormat(siteLocale, "providerPortal.analytics.staffNeedReview", {
                        count: String(unverifiedStaffCount),
                        label: unverifiedStaffCount === 1 ? t(siteLocale, "providerPortal.analytics.staffAccountSingular") : t(siteLocale, "providerPortal.analytics.staffAccountPlural")
                      })
                    : t(siteLocale, "providerPortal.analytics.allStaffVerified")}
                </p>
                <div className="provider-staff-metrics" aria-label={t(siteLocale, "providerPortal.analytics.staffActivityMetrics")}>
                  <span><strong>{providerMessagesForShelter.length}</strong> {t(siteLocale, "providerPortal.analytics.messages")}</span>
                  <span><strong>{providerProofsForShelter.length}</strong> {t(siteLocale, "providerPortal.analytics.zkProofs")}</span>
                  <span><strong>{providerRecentActivity.length}</strong> {t(siteLocale, "providerPortal.analytics.timelineEvents")}</span>
                </div>
              </article>
            </div>
          </Section>
          <Section title={t(siteLocale, "providerPortal.analytics.needDistribution")}>
            <div className="provider-insight-grid">
              {providerServiceNeedCounts.length ? (
                providerServiceNeedCounts.map((item) => (
                  <article className="provider-need-card" key={item.need}>
                    <strong>{translateServiceNeed(siteLocale, item.need)}</strong>
                    <span>{tFormat(siteLocale, "providerPortal.analytics.clientsCount", {
                      count: String(item.count),
                      label: item.count === 1 ? t(siteLocale, "providerPortal.analytics.clientSingular") : t(siteLocale, "providerPortal.analytics.clientPlural")
                    })}</span>
                    <div className="provider-meter" aria-label={tFormat(siteLocale, "providerPortal.analytics.clientsMeter", { need: translateServiceNeed(siteLocale, item.need) })}>
                      <span style={{ width: formatProviderPercent(item.count, usersForOperatorShelter.length) }} />
                    </div>
                  </article>
                ))
              ) : (
                <small>{t(siteLocale, "providerPortal.analytics.noNeedData")}</small>
              )}
            </div>
          </Section>
          <Section title={t(siteLocale, "providerPortal.analytics.staffAnalytics")}>
            <div className="list-stack provider-staff-analytics">
              {staffAnalytics.length ? (
                staffAnalytics.map((item) => (
                  <article className="list-item provider-staff-row" key={`analytics-${item.staff.id}`}>
                    <div>
                      <h3>{item.staff.displayName}</h3>
                      <p>{item.staff.email || t(siteLocale, "providerPortal.analytics.noEmail")}</p>
                      <div className="provider-staff-metrics" aria-label={tFormat(siteLocale, "providerPortal.analytics.staffAnalyticsAria", { name: item.staff.displayName })}>
                        <span><strong>{item.servedCount}</strong> {t(siteLocale, "providerPortal.analytics.served")}</span>
                        <span><strong>{item.activeCount}</strong> {t(siteLocale, "providerPortal.analytics.active")}</span>
                        <span><strong>{item.housedCount}</strong> {t(siteLocale, "providerPortal.analytics.housed")}</span>
                        <span><strong>{item.messageCount}</strong> {t(siteLocale, "providerPortal.analytics.messages")}</span>
                        <span><strong>{item.proofCount}</strong> {t(siteLocale, "providerPortal.analytics.proofs")}</span>
                        <span><strong>{item.proofCoverage}</strong> {t(siteLocale, "providerPortal.analytics.proofCoverage")}</span>
                        <span><strong>{item.clientsNeedingProofCount}</strong> {t(siteLocale, "providerPortal.analytics.needProofs")}</span>
                      </div>
                      <small>{tFormat(siteLocale, "providerPortal.analytics.lastActivity", { value: formatProviderActivityDate(item.lastActivityAt, siteLocale) })}</small>
                    </div>
                    <Badge tone={item.staff.verified ? "success" : "warning"}>
                      {item.staff.verified ? t(siteLocale, "contacts.verified") : t(siteLocale, "providerPortal.analytics.verificationOff")}
                    </Badge>
                  </article>
                ))
              ) : (
                <small>{t(siteLocale, "providerPortal.analytics.noStaffAnalytics")}</small>
              )}
            </div>
          </Section>
          <Section title={t(siteLocale, "providerPortal.analytics.recentActivity")}>
            <div className="list-stack provider-activity-list">
              {providerRecentActivity.length ? (
                providerRecentActivity.map((activity) => (
                  <article className="list-item provider-activity-item" key={activity.id}>
                    <div>
                      <h3>{activity.title}</h3>
                      <p>{activity.detail}</p>
                      <small>{formatProviderActivityDate(activity.createdAt, siteLocale)}</small>
                    </div>
                    <Badge tone={activity.tone}>{providerActivityToneLabel(activity.tone, siteLocale)}</Badge>
                  </article>
                ))
              ) : (
                <small>{t(siteLocale, "providerPortal.analytics.noProviderActivity")}</small>
              )}
            </div>
          </Section>
        </>
      ) : null}
      {view === "proofs" ? (
        <>
          <Section title={t(siteLocale, "providerPortal.proofs.title")}>
            <p className="section-note">
              {t(siteLocale, "providerPortal.proofs.note")}
            </p>
            <div className="dashboard-grid">
              <StatusPanel label={t(siteLocale, "providerPortal.proofs.verifiedProofs")} value={String(providerProofsForShelter.length)} tone="teal" />
              <StatusPanel label={t(siteLocale, "providerPortal.proofs.clientCoverage")} value={formatProviderPercent(clientsWithProofsCount, usersForOperatorShelter.length)} tone="gold" />
              <StatusPanel label={t(siteLocale, "providerPortal.proofs.needCertificates")} value={String(clientsWithoutProofsCount)} tone="red" />
              <StatusPanel label={t(siteLocale, "providerPortal.proofs.certificateTypes")} value={String(providerProofTypeRows.length)} tone="teal" />
            </div>
            <div className="provider-insight-grid">
              <article className="provider-insight-card">
                <h3>{t(siteLocale, "providerPortal.proofs.certificateMix")}</h3>
                <div className="provider-staff-metrics" aria-label={t(siteLocale, "providerPortal.proofs.proofTypeCounts")}>
                  {providerProofTypeRows.length ? (
                    providerProofTypeRows.map(([proofType, count]) => (
                      <span key={proofType}>
                        <strong>{count}</strong> {providerProofTypeLabel(proofType, siteLocale)}
                      </span>
                    ))
                  ) : (
                    <span><strong>0</strong> {t(siteLocale, "providerPortal.proofs.certificates")}</span>
                  )}
                </div>
              </article>
              <article className="provider-insight-card">
                <h3>{t(siteLocale, "providerPortal.proofs.issuerActivity")}</h3>
                <div className="provider-staff-metrics" aria-label={t(siteLocale, "providerPortal.proofs.issuerCounts")}>
                  {providerProofStaffRows.length ? (
                    providerProofStaffRows.map((item) => (
                      <span key={`proof-staff-${item.staff.id}`}>
                        <strong>{item.proofCount}</strong> {item.staff.displayName}
                      </span>
                    ))
                  ) : (
                    <span><strong>0</strong> {t(siteLocale, "providerPortal.proofs.issuers")}</span>
                  )}
                </div>
              </article>
            </div>
            <form className="form-grid provider-proof-form" onSubmit={processProviderProofCertificate}>
              <Field label={t(siteLocale, "providerPortal.proofs.client")} required>
                <select
                  value={proofDraft.clientId}
                  onChange={(event) => setProofDraft({ ...proofDraft, clientId: event.target.value })}
                >
                  <option value="">{t(siteLocale, "providerPortal.proofs.selectClient")}</option>
                  {usersForOperatorShelter.map((account) => (
                    <option key={`proof-${account.id}`} value={account.id}>
                      {account.preferredName || account.legalName}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label={t(siteLocale, "providerPortal.proofs.certificateType")} required>
                <select
                  value={proofDraft.proofType}
                  onChange={(event) => setProofDraft({ ...proofDraft, proofType: event.target.value })}
                >
                  <option value="service_attendance">{providerProofTypeLabel("service_attendance", siteLocale)}</option>
                  <option value="document_reviewed">{providerProofTypeLabel("document_reviewed", siteLocale)}</option>
                  <option value="benefits_referral">{providerProofTypeLabel("benefits_referral", siteLocale)}</option>
                  <option value="housing_step">{providerProofTypeLabel("housing_step", siteLocale)}</option>
                  <option value="us_citizenship">{providerProofTypeLabel("us_citizenship", siteLocale)}</option>
                  <option value="service_area_residency">{providerProofTypeLabel("service_area_residency", siteLocale)}</option>
                  <option value="income_eligibility">{providerProofTypeLabel("income_eligibility", siteLocale)}</option>
                  <option value="identity_verified">{providerProofTypeLabel("identity_verified", siteLocale)}</option>
                </select>
              </Field>
              <Field help={t(siteLocale, "providerPortal.proofs.eligibilityHelp")} label={t(siteLocale, "providerPortal.proofs.eligibilityCriterion")}>
                <select
                  value={proofDraft.criterionId}
                  onChange={(event) => selectProofCriterion(event.target.value as ShelterEligibilityCriterion | "")}
                >
                  <option value="">{t(siteLocale, "providerPortal.proofs.noEligibilityCriterion")}</option>
                  {providerEligibilityCriteria.map((criterion) => (
                    <option key={criterion.id} value={criterion.id}>
                      {providerEligibilityLabel(criterion.id, siteLocale)}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label={t(siteLocale, "providerPortal.proofs.verifier")} required>
                <input
                  value={proofDraft.verifier}
                  onChange={(event) => setProofDraft({ ...proofDraft, verifier: event.target.value })}
                />
              </Field>
              <Field label={t(siteLocale, "providerPortal.proofs.publicClaim")} required>
                <textarea
                  rows={3}
                  value={proofDraft.claim}
                  onChange={(event) => setProofDraft({ ...proofDraft, claim: event.target.value })}
                />
              </Field>
              <div className="full-span row-actions">
                <Button
                  disabled={!activeProviderOperator || !selectedProofClient || !proofDraft.claim.trim() || !proofDraft.verifier.trim()}
                  type="submit"
                >
                  <ShieldCheck aria-hidden="true" size={18} />
                  {t(siteLocale, "providerPortal.proofs.processCertificate")}
                </Button>
              </div>
            </form>
          </Section>
          <Section title={t(siteLocale, "providerPortal.proofs.queue")}>
            <div className="list-stack provider-proof-queue">
              {clientAnalytics.length ? (
                clientAnalytics.map((item) => (
                  <article className="list-item provider-proof-item" key={`proof-queue-${item.client.id}`}>
                    <div>
                      <h3>{item.client.preferredName || item.client.legalName}</h3>
                      <p>{item.client.serviceNeeds.length ? item.client.serviceNeeds.map((need) => translateServiceNeed(siteLocale, need)).join(", ") : t(siteLocale, "providerPortal.clients.noServiceNeeds")}</p>
                      <div className="badge-row">
                        <Badge tone={item.proofCount ? "success" : "warning"}>
                          {item.proofCount
                            ? `${item.proofCount} ${t(siteLocale, item.proofCount === 1 ? "providerPortal.cases.proofSingular" : "providerPortal.cases.proofPlural")}`
                            : t(siteLocale, "providerPortal.proofs.needsCertificate")}
                        </Badge>
                        <Badge>{item.messageCount} {t(siteLocale, "providerPortal.analytics.messages")}</Badge>
                        {item.latestProofAt ? <Badge>{formatProviderActivityDate(item.latestProofAt, siteLocale)}</Badge> : null}
                      </div>
                    </div>
                    <Button disabled={!activeProviderOperator} onClick={() => prepareProviderProof(item.client)} variant="secondary">
                      {t(siteLocale, "providerPortal.proofs.prepareCertificate")}
                    </Button>
                  </article>
                ))
              ) : (
                <small>{t(siteLocale, "providerPortal.proofs.noClients")}</small>
              )}
            </div>
          </Section>
          <Section title={t(siteLocale, "providerPortal.proofs.transparencyLog")}>
            <div className="list-stack">
              {providerProofsForShelter.length ? (
                providerProofsForShelter.slice(0, 8).map((proof) => (
                  <article className="list-item provider-proof-item" key={proof.id}>
                    <div>
                      <h3>{proof.claim}</h3>
                      <p>{proof.verifier}</p>
                      <div className="badge-row">
                        <Badge tone="success">{providerProofVerificationStatusLabel(proof.verificationStatus, siteLocale)}</Badge>
                        <Badge>{providerProofClientLabel(proof, usersForOperatorShelter)}</Badge>
                        <Badge>{providerProofTypeLabel(proof.publicInputs.certificate_type, siteLocale)}</Badge>
                        {proof.publicInputs.eligibility_criterion ? (
                          <Badge>{providerEligibilityLabel(proof.publicInputs.eligibility_criterion as ShelterEligibilityCriterion, siteLocale)}</Badge>
                        ) : null}
                        <Badge>{formatProviderActivityDate(proof.createdAt, siteLocale)}</Badge>
                      </div>
                      <small>
                        {t(siteLocale, "providerPortal.proofs.clientCommitment")} <code>{proof.publicInputs.client_commitment}</code> · {t(siteLocale, "providerPortal.proofs.artifact")}{" "}
                        <code>{proof.proofArtifactRef}</code> · {t(siteLocale, "providerPortal.proofs.circuit")} <code>{proof.circuitId}</code>
                      </small>
                    </div>
                  </article>
                ))
              ) : (
                <small>{t(siteLocale, "providerPortal.proofs.noneProcessed")}</small>
              )}
            </div>
          </Section>
        </>
      ) : null}
      {view === "operations" ? (
        <>
      <Section title={t(siteLocale, "providerPortal.operations.title")}>
        <div className="shelter-staff-panel">
          {!selectedOperator ? (
            <small className="pin-request-note">{t(siteLocale, "providerPortal.operations.needVerifiedOperator")}</small>
          ) : (
            <>
              <Section title={t(siteLocale, "providerPortal.operations.createUserAccount")}>
                <form className="form-grid" onSubmit={createManagedUserAccount}>
                  <Field label={t(siteLocale, "providerPortal.operations.legalName")} required>
                    <input
                      value={userDraft.legalName}
                      onChange={(event) => setUserDraft({ ...userDraft, legalName: event.target.value })}
                    />
                  </Field>
                  <Field label={t(siteLocale, "profile.preferredName")}>
                    <input
                      value={userDraft.preferredName}
                      onChange={(event) => setUserDraft({ ...userDraft, preferredName: event.target.value })}
                    />
                  </Field>
                  <Field label={t(siteLocale, "providerPortal.operations.pronouns")}>
                    <input
                      placeholder={t(siteLocale, "providerPortal.operations.pronounsPlaceholder")}
                      value={userDraft.pronouns}
                      onChange={(event) => setUserDraft({ ...userDraft, pronouns: event.target.value })}
                    />
                  </Field>
                  <Field label={t(siteLocale, "profile.birthDate")}>
                    <input
                      type="date"
                      value={userDraft.dateOfBirth}
                      onChange={(event) => setUserDraft({ ...userDraft, dateOfBirth: event.target.value })}
                    />
                  </Field>
                  <Field
                    error={managedUserUploadError}
                    help={t(siteLocale, "providerPortal.operations.photoIdHelp")}
                    label={t(siteLocale, "providerPortal.operations.photoId")}
                    required
                  >
                    <input
                      accept={ID_DOCUMENT_ACCEPT_ATTR}
                      type="file"
                      onChange={handleManagedUserUploadChange}
                    />
                    {managedUserFileDetail ? (
                      <small className="registration-file-detail" aria-live="polite">
                        {tFormat(siteLocale, "providerPortal.operations.selectedFile", { value: managedUserFileDetail })}
                      </small>
                    ) : null}
                  </Field>
                  <Field help={t(siteLocale, "profile.phoneHelp")} label={t(siteLocale, "profile.phone")}>
                    <input
                      value={userDraft.phone}
                      onChange={(event) => setUserDraft({ ...userDraft, phone: event.target.value })}
                    />
                  </Field>
                  <Field help={t(siteLocale, "profile.emailHelp")} label={t(siteLocale, "profile.email")}>
                    <input
                      type="email"
                      value={userDraft.email}
                      onChange={(event) => setUserDraft({ ...userDraft, email: event.target.value })}
                    />
                  </Field>
                  <Field label={t(siteLocale, "providerPortal.operations.currentSafeLocation")}>
                    <input
                      value={userDraft.currentLocation}
                      onChange={(event) => setUserDraft({ ...userDraft, currentLocation: event.target.value })}
                    />
                  </Field>
                  <Field label={t(siteLocale, "profile.shelter")}>
                    <input
                      value={userDraft.preferredShelter}
                      onChange={(event) => setUserDraft({ ...userDraft, preferredShelter: event.target.value })}
                    />
                  </Field>
                  <label className="captcha-box full-span">
                    <input
                      checked={userDraft.easyBotCheckStatus === "passed"}
                      onChange={(event) =>
                        setUserDraft({
                          ...userDraft,
                          easyBotCheckStatus: event.target.checked ? "passed" : "failed",
                          captchaToken: ""
                        })
                      }
                      type="checkbox"
                    />
                    <span>{t(siteLocale, "providerPortal.operations.quickHealthCheck")}</span>
                  </label>
                  <div className="full-span">
                    <span className="field-label">{t(siteLocale, "profile.serviceNeeds")}</span>
                    <div className="chip-grid">
                      {serviceNeeds.map((need) => (
                        <button
                          aria-pressed={userDraft.serviceNeeds.includes(need)}
                          className="choice-chip"
                          key={need}
                          onClick={() => toggleManagedUserNeed(need)}
                          type="button"
                        >
                          {translateServiceNeed(siteLocale, need)}
                        </button>
                      ))}
                    </div>
                  </div>
                  <label className="captcha-box full-span">
                    <input
                      checked={Boolean(userDraft.captchaToken)}
                      disabled={userDraft.easyBotCheckStatus !== "passed"}
                      onChange={(event) =>
                        setUserDraft({ ...userDraft, captchaToken: event.target.checked ? "mock-captcha-token" : "" })
                      }
                      type="checkbox"
                    />
                    <span>{t(siteLocale, "providerPortal.operations.botCheck")}</span>
                  </label>
                  <label className="consent-box full-span">
                    <input
                      checked={userDraft.localPrecinctNotified}
                      onChange={(event) => setUserDraft({ ...userDraft, localPrecinctNotified: event.target.checked })}
                      type="checkbox"
                    />
                    <span>
                      <strong>{t(siteLocale, "providerPortal.operations.localPrecinctNotified")}</strong>
                    </span>
                  </label>
                  <label className="consent-box full-span">
                    <input
                      checked={userDraft.foundPermanentHousing}
                      onChange={(event) => setUserDraft({ ...userDraft, foundPermanentHousing: event.target.checked })}
                      type="checkbox"
                    />
                    <span>
                      <strong>{t(siteLocale, "providerPortal.operations.foundPermanentHousing")}</strong>
                    </span>
                  </label>
                  <div className="full-span">
                    <Button
                      disabled={
                        !userDraft.legalName.trim() ||
                        !userDraft.photoAssetId ||
                        (userDraft.easyBotCheckStatus === "pending") ||
                        (userDraft.easyBotCheckStatus === "passed" && !userDraft.captchaToken)
                      }
                      type="submit"
                    >
                      {t(siteLocale, "providerPortal.operations.createUser")}
                    </Button>
                  </div>
                </form>
              </Section>

              <Section title={t(siteLocale, "providerPortal.operations.contactListRequests")}>
                <p className="section-note">
                  {t(siteLocale, "providerPortal.operations.contactListNote")}
                </p>
                <form className="form-grid" onSubmit={sendShelterNudge}>
                  <Field label={t(siteLocale, "providerPortal.operations.personName")} required>
                    <input
                      value={nudgeDraft.userName}
                      onChange={(event) => setNudgeDraft({ ...nudgeDraft, userName: event.target.value })}
                    />
                  </Field>
                  <Field label={t(siteLocale, "providerPortal.operations.phoneOrEmail")} required>
                    <input
                      value={nudgeDraft.userContact}
                      onChange={(event) => setNudgeDraft({ ...nudgeDraft, userContact: event.target.value })}
                    />
                  </Field>
                  <div className="full-span centered-action">
                    <Button disabled={hasPendingShelterNudge()} type="submit" variant="secondary">
                      <MessageSquare size={18} /> {t(siteLocale, "providerPortal.operations.sendContactRequest")}
                    </Button>
                  </div>
                  {hasPendingShelterNudge() ? (
                    <small className="full-span pin-request-note">
                      {t(siteLocale, "providerPortal.operations.pendingRequestExists")}
                    </small>
                  ) : null}
                </form>
                <div className="list-stack">
                  {requestsForOperatorShelter.length ? (
                    requestsForOperatorShelter.map((request) => (
                      <article className="list-item access-request-item" key={`shelter-contact-${request.id}`}>
                        <div>
                          <h3>{request.userName}</h3>
                          <p>
                            {request.direction === "user_to_shelter"
                              ? tFormat(siteLocale, "providerPortal.operations.userAskedAdd", { shelter: request.shelterName })
                              : tFormat(siteLocale, "providerPortal.operations.shelterAskedUser", { shelter: request.shelterName })}
                          </p>
                          <div className="badge-row">
                            <Badge>{request.userContact}</Badge>
                            <Badge tone={request.status === "approved" ? "success" : request.status === "denied" ? "warning" : "neutral"}>
                              {formatContactRequestStatus(request.status, siteLocale)}
                            </Badge>
                          </div>
                        </div>
                        {request.direction === "user_to_shelter" && request.status === "pending" ? (
                          <div className="row-actions">
                            <Button onClick={() => decideUserShelterRequest(request.id, "approved")} variant="secondary">
                              {t(siteLocale, "providerPortal.operations.approve")}
                            </Button>
                            <Button onClick={() => decideUserShelterRequest(request.id, "denied")} variant="danger">
                              {t(siteLocale, "providerPortal.operations.deny")}
                            </Button>
                          </div>
                        ) : null}
                      </article>
                    ))
                  ) : (
                    <small>{t(siteLocale, "providerPortal.operations.noContactRequests")}</small>
                  )}
                </div>
              </Section>

              <div className="list-stack">
                {usersForOperatorShelter.length ? (
                  usersForOperatorShelter.map((account) => (
                    <article className="list-item" key={account.id}>
                      <div>
                        <h3>{account.preferredName || account.legalName}</h3>
                        <p>{account.legalName}</p>
                        <small>
                          {tFormat(siteLocale, "providerPortal.operations.createdBy", {
                            name: shelterStaffAccounts.find((item) => item.id === account.createdByStaffId)?.displayName ?? t(siteLocale, "providerPortal.clients.staffFallback")
                          })}
                          {account.dateOfBirth ? ` · ${tFormat(siteLocale, "providerPortal.operations.dob", { value: account.dateOfBirth })}` : ""}
                        </small>
                      </div>
                      <Badge>{t(siteLocale, "providerPortal.operations.userAccount")}</Badge>
                    </article>
                  ))
                ) : (
                  <small>{t(siteLocale, "providerPortal.operations.noUserAccounts")}</small>
                )}
              </div>

              <Section title={t(siteLocale, "providerPortal.operations.userOversight")}>
                <div className="list-stack">
                  {staffRegisteredUsersForShelter.length ? (
                    staffRegisteredUsersForShelter.map((account) => (
                      <article className="list-item" key={`overview-${account.id}`}>
                        <div>
                          <h3>{account.preferredName || account.legalName}</h3>
                          <p>{account.legalName}</p>
                          <div className="badge-row">
                            <Badge tone={account.localPrecinctNotified ? "success" : "warning"}>
                              {account.localPrecinctNotified ? t(siteLocale, "providerPortal.operations.precinctNotified") : t(siteLocale, "providerPortal.operations.precinctNotNotified")}
                            </Badge>
                            <Badge tone={account.foundPermanentHousing ? "success" : "neutral"}>
                              {account.foundPermanentHousing ? t(siteLocale, "providerPortal.operations.housingFound") : t(siteLocale, "providerPortal.operations.housingNotFound")}
                            </Badge>
                            {account.easyBotCheckStatus === "failed" ? <Badge tone="warning">{t(siteLocale, "providerPortal.operations.healthCheck")}</Badge> : null}
                          </div>
                        </div>
                      </article>
                    ))
                  ) : (
                    <small>{t(siteLocale, "providerPortal.operations.noShelterUsers")}</small>
                  )}
                </div>
                <div className="list-stack">
                  {preferredShelterMentionUsers.length ? (
                    preferredShelterMentionUsers.map((account) => (
                      <article className="list-item" key={`preferred-${account.id}`}>
                        <div>
                          <h3>{account.preferredName || account.legalName}</h3>
                          <p>{account.legalName}</p>
                          <div className="badge-row">
                            <Badge tone={account.localPrecinctNotified ? "success" : "warning"}>
                              {account.localPrecinctNotified ? t(siteLocale, "providerPortal.operations.precinctNotified") : t(siteLocale, "providerPortal.operations.precinctNotNotified")}
                            </Badge>
                            <Badge tone={account.foundPermanentHousing ? "success" : "neutral"}>
                              {account.foundPermanentHousing ? t(siteLocale, "providerPortal.operations.housingFound") : t(siteLocale, "providerPortal.operations.housingNotFound")}
                            </Badge>
                            {account.easyBotCheckStatus === "failed" ? <Badge tone="warning">{t(siteLocale, "providerPortal.operations.healthCheck")}</Badge> : null}
                          </div>
                        </div>
                      </article>
                    ))
                  ) : (
                    <small>{t(siteLocale, "providerPortal.operations.noPreferredUsers")}</small>
                  )}
                </div>
              </Section>
            </>
          )}
        </div>
      </Section>
      <Section title={t(siteLocale, "providerPortal.operations.sharedDeviceSafety")}>
        <div className="checklist">
          <label>
            <input
              checked={checklist.userPresent}
              onChange={(event) => setChecklist({ ...checklist, userPresent: event.target.checked })}
              type="checkbox"
            />{" "}
            {t(siteLocale, "providerPortal.operations.confirmUserPresent")}
          </label>
          <label>
            <input
              checked={checklist.clearBrowserData}
              onChange={(event) => setChecklist({ ...checklist, clearBrowserData: event.target.checked })}
              type="checkbox"
            />{" "}
            {t(siteLocale, "providerPortal.operations.clearBrowserData")}
          </label>
          <label>
            <input
              checked={checklist.auditLogConfirmed}
              onChange={(event) => setChecklist({ ...checklist, auditLogConfirmed: event.target.checked })}
              type="checkbox"
            />{" "}
            {t(siteLocale, "providerPortal.operations.auditLog")}
          </label>
        </div>
      </Section>
      <Section title={t(siteLocale, "providerPortal.operations.providerAdministrator")}>
        <label className="consent-box">
          <input
            checked={isShelterAdmin}
            onChange={(event) => {
              setIsShelterAdmin(event.target.checked);
              if (event.target.checked) {
                setAdminShelter(operatorShelter);
              }
            }}
            type="checkbox"
          />
          <span>
            <strong>{t(siteLocale, "providerPortal.operations.isAdministrator")}</strong>
          </span>
        </label>
        {isShelterAdmin ? (
          <div className="shelter-staff-panel provider-admin-panel">
            <Field label={t(siteLocale, "providerPortal.operations.provider")} required>
              <select value={adminShelter} onChange={(event) => setAdminShelter(event.target.value)}>
                {shelterOptions.map((shelter) => (
                  <option key={shelter} value={shelter}>
                    {shelter}
                  </option>
                ))}
              </select>
            </Field>
            <Section title={t(siteLocale, "providerPortal.operations.addStaffMember")}>
              <form className="form-grid provider-admin-staff-form" onSubmit={createStaffAccount}>
                <Field label={t(siteLocale, "providerPortal.operations.staffName")} required>
                  <input
                    value={staffDraft.displayName}
                    onChange={(event) => setStaffDraft({ ...staffDraft, displayName: event.target.value })}
                  />
                </Field>
                <Field label={t(siteLocale, "providerPortal.operations.staffEmail")}>
                  <input
                    type="email"
                    value={staffDraft.email}
                    onChange={(event) => setStaffDraft({ ...staffDraft, email: event.target.value })}
                  />
                </Field>
                <div className="full-span row-actions">
                  <Button disabled={!staffDraft.displayName.trim()} type="submit">
                    <UsersRound aria-hidden="true" size={18} />
                    {t(siteLocale, "providerPortal.operations.addStaff")}
                  </Button>
                </div>
              </form>
            </Section>
            <Section title={t(siteLocale, "providerPortal.operations.staffRoster")}>
            <div className="list-stack">
              {staffForShelter.length ? (
                staffForShelter.map((account) => (
                  <article className="list-item provider-staff-roster-item" key={account.id}>
                    <div>
                      <h3>{account.displayName}</h3>
                      <p>{account.email || t(siteLocale, "providerPortal.analytics.noEmail")}</p>
                      <div className="badge-row">
                        <Badge tone={account.verified ? "success" : "warning"}>
                          {account.verified ? t(siteLocale, "contacts.verified") : t(siteLocale, "providerPortal.operations.revoked")}
                        </Badge>
                        <Badge>{formatShelterDate(account.updatedAt)}</Badge>
                      </div>
                    </div>
                    <div className="row-actions">
                      <Button onClick={() => updateStaffVerification(account.id, !account.verified)} variant="secondary">
                        {account.verified ? t(siteLocale, "providerPortal.operations.revokeAccess") : t(siteLocale, "providerPortal.operations.reverify")}
                      </Button>
                      <Button onClick={() => removeStaffAccount(account.id)} variant="danger">
                        {t(siteLocale, "providerPortal.operations.removeStaff")}
                      </Button>
                    </div>
                  </article>
                ))
              ) : (
                <small>{t(siteLocale, "providerPortal.operations.noStaffAccounts")}</small>
              )}
            </div>
            </Section>
          </div>
        ) : null}
      </Section>
        </>
      ) : null}
    </div>
  );
}

function contactLabelForShelterUser(account: ShelterUserAccount, locale: SupportedLocale): string {
  return account.phone || account.email || t(locale, "providerPortal.operations.noContact");
}

function formatShelterDate(value: string): string {
  const dateOnly = value.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  const date = dateOnly
    ? new Date(Number(dateOnly[1]), Number(dateOnly[2]) - 1, Number(dateOnly[3]))
    : new Date(value);
  if (Number.isNaN(date.getTime())) return value || "Date unavailable";
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

function providerClientCommitment(account: ShelterUserAccount): string {
  return appStableSuffix(`${account.id}:${account.dateOfBirth}`);
}

function providerProofClientLabel(proof: ProofReceiptView, accounts: ShelterUserAccount[]): string {
  const client = accounts.find((account) => providerClientCommitment(account) === proof.publicInputs.client_commitment);
  return client ? client.preferredName || client.legalName : "Committed client";
}

function providerCasePriorityRank(priority: ShelterCasePriority): number {
  if (priority === "urgent") return 0;
  if (priority === "standard") return 1;
  return 2;
}

function providerCasePriorityLabel(priority: ShelterCasePriority, locale: SupportedLocale): string {
  if (priority === "urgent") return t(locale, "providerPortal.cases.urgent");
  if (priority === "standard") return t(locale, "providerPortal.cases.standard");
  return t(locale, "providerPortal.cases.monitor");
}

function providerCaseStatusLabel(status: ShelterCaseStatus, locale: SupportedLocale): string {
  if (status === "intake") return t(locale, "providerPortal.cases.intake");
  if (status === "active") return t(locale, "providerPortal.cases.active");
  if (status === "waiting_on_client") return t(locale, "providerPortal.cases.waitingOnClient");
  if (status === "eligible") return t(locale, "providerPortal.cases.eligible");
  return t(locale, "providerPortal.cases.closed");
}

function providerEligibilityLabel(criterionId: ShelterEligibilityCriterion, locale: SupportedLocale): string {
  if (criterionId === "us_citizen") return t(locale, "providerPortal.criteria.usCitizen");
  if (criterionId === "service_area_resident") return t(locale, "providerPortal.criteria.serviceAreaResident");
  if (criterionId === "income_eligible") return t(locale, "providerPortal.criteria.incomeEligible");
  if (criterionId === "identity_verified") return t(locale, "providerPortal.criteria.identityVerified");
  return providerEligibilityCriteria.find((criterion) => criterion.id === criterionId)?.label ?? criterionId;
}

function providerEligibilityClaim(criterionId: ShelterEligibilityCriterion, locale: SupportedLocale): string {
  if (criterionId === "us_citizen") return t(locale, "providerPortal.criteria.claim.usCitizen");
  if (criterionId === "service_area_resident") return t(locale, "providerPortal.criteria.claim.serviceAreaResident");
  if (criterionId === "income_eligible") return t(locale, "providerPortal.criteria.claim.incomeEligible");
  if (criterionId === "identity_verified") return t(locale, "providerPortal.criteria.claim.identityVerified");
  return t(locale, "providerPortal.proofs.defaultEligibilityClaim");
}

function providerProofTypeLabel(proofType: string | undefined, locale: SupportedLocale): string {
  if (!proofType) return "";
  if (proofType === "service_attendance") return t(locale, "providerPortal.proofs.proofType.serviceAttendance");
  if (proofType === "document_reviewed") return t(locale, "providerPortal.proofs.proofType.documentReviewed");
  if (proofType === "benefits_referral") return t(locale, "providerPortal.proofs.proofType.benefitsReferral");
  if (proofType === "housing_step") return t(locale, "providerPortal.proofs.proofType.housingStep");
  if (proofType === "us_citizenship") return t(locale, "providerPortal.proofs.proofType.usCitizenship");
  if (proofType === "service_area_residency") return t(locale, "providerPortal.proofs.proofType.serviceAreaResidency");
  if (proofType === "income_eligibility") return t(locale, "providerPortal.proofs.proofType.incomeEligibility");
  if (proofType === "identity_verified") return t(locale, "providerPortal.proofs.proofType.identityVerified");
  return proofType.replace(/_/g, " ");
}

function providerProofVerificationStatusLabel(status: string, locale: SupportedLocale): string {
  if (status === "verified") return t(locale, "providerPortal.proofs.verificationStatus.verified");
  return status;
}

function formatProviderPercent(value: number, total: number): string {
  if (!total) return "0%";
  return `${Math.round((value / total) * 100)}%`;
}

function latestProviderTimestamp(values: string[]): string | undefined {
  return values
    .map((value) => ({ value, time: new Date(value).getTime() }))
    .filter((item) => Number.isFinite(item.time))
    .sort((left, right) => right.time - left.time)[0]?.value;
}

function formatProviderActivityDate(value: string | undefined, locale: SupportedLocale): string {
  if (!value) return t(locale, "providerPortal.analytics.noActivity");
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString(locale, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}

function providerActivityToneLabel(tone: "neutral" | "warning" | "success", locale: SupportedLocale): string {
  if (tone === "success") return t(locale, "providerPortal.analytics.toneSuccess");
  if (tone === "warning") return t(locale, "providerPortal.analytics.toneWarning");
  return t(locale, "providerPortal.analytics.toneNeutral");
}

type RecipientAnalysisMode = "summary" | "redacted" | "vector" | "extract-text" | "form" | "graphrag";

function RecipientAccessScreen({
  accessRequests,
  apiConfig,
  grantReceipts,
  refreshWalletAccessState,
  refreshWalletAuditEvents,
  setAccessRequests,
  setGrantReceipts,
  verified,
  setVerified
}: {
  accessRequests: WalletAccessRequest[];
  apiConfig?: WalletApiConfig;
  grantReceipts: WalletGrantReceipt[];
  recipients: DisclosureRecipientDraft[];
  refreshWalletAccessState: () => Promise<void>;
  refreshWalletAuditEvents: () => Promise<void>;
  setAccessRequests: (requests: WalletAccessRequest[]) => void;
  setGrantReceipts: (receipts: WalletGrantReceipt[]) => void;
  verified: boolean;
  setVerified: (verified: boolean) => void;
}) {
  const [derivedArtifactsByReceiptId, setDerivedArtifactsByReceiptId] = useState<Record<string, string[]>>({});
  const [decryptedRecordsByReceiptId, setDecryptedRecordsByReceiptId] = useState<Record<string, DecryptedRecordView>>({});
  const [busyActionIds, setBusyActionIds] = useState<string[]>([]);
  const [delegationDrafts, setDelegationDrafts] = useState<Record<string, { audienceDid: string; purpose: string }>>({});
  const [delegationMessages, setDelegationMessages] = useState<Record<string, string>>({});

  async function decideRequest(requestId: string, status: "approved" | "rejected") {
    if (apiConfig?.actorDid) {
      try {
        if (status === "approved") {
          await approveAccessRequest(apiConfig, requestId);
        } else {
          await rejectAccessRequest(apiConfig, requestId);
        }
        await refreshWalletAccessState();
        await refreshWalletAuditEvents();
        return;
      } catch {
        // Keep the local demo path responsive if a configured API is unavailable.
      }
    }
    setAccessRequests(
      accessRequests.map((request) =>
        request.id === requestId
          ? { ...request, status, grantStatus: status === "approved" ? "active" : request.grantStatus }
          : request
      )
    );
  }

  async function recordControllerApproval(request: WalletAccessRequest) {
    if (apiConfig?.actorDid && request.approvalId) {
      try {
        await approveThresholdApproval(apiConfig, request.approvalId);
        await refreshWalletAccessState();
        await refreshWalletAuditEvents();
        return;
      } catch {
        // Keep the local demo path responsive if a configured API is unavailable.
      }
    }
    setAccessRequests(
      accessRequests.map((item) =>
        item.id === request.id
          ? {
              ...item,
              approvalCount: Math.min((item.approvalCount ?? 0) + 1, item.approvalThreshold ?? 1)
            }
          : item
      )
    );
  }

  async function revokeRequest(requestId: string) {
    if (apiConfig?.actorDid) {
      try {
        await revokeAccessRequest(apiConfig, requestId);
        await refreshWalletAccessState();
        await refreshWalletAuditEvents();
        return;
      } catch {
        // Keep the local demo path responsive if a configured API is unavailable.
      }
    }
    setAccessRequests(accessRequests.map((request) => (request.id === requestId ? { ...request, status: "revoked" } : request)));
    setGrantReceipts(grantReceipts.map((receipt) => (receipt.id.includes(requestId) ? { ...receipt, status: "revoked" } : receipt)));
  }

  async function analyzeReceipt(receipt: WalletGrantReceipt, mode: RecipientAnalysisMode) {
    if (!apiConfig?.actorDid || !receipt.recordId) return;
    const actionId = `${receipt.id}:${mode}`;
    setBusyActionIds((ids) => [...ids, actionId]);
    try {
      const outputType = outputTypeForAnalysisMode(mode);
      const invocationToken = receiptRequiresUserPresence(receipt)
        ? await issueRecordAnalysisInvocation(apiConfig, {
            grantId: receipt.grantId,
            outputTypes: [outputType],
            recordId: receipt.recordId,
            userPresent: true
          })
        : undefined;
      const lines =
        mode === "summary"
          ? artifactLines(
              await analyzeRecordWithGrant(apiConfig, {
                grantId: receipt.grantId,
                invocationToken,
                recordId: receipt.recordId
              })
            )
          : analysisLines(
              await runDerivedAnalysis(apiConfig, receipt, mode, invocationToken)
            );
      setDerivedArtifactsByReceiptId((items) => ({ ...items, [receipt.id]: [...(items[receipt.id] ?? []), ...lines] }));
      await refreshWalletAuditEvents().catch(() => undefined);
    } finally {
      setBusyActionIds((ids) => ids.filter((id) => id !== actionId));
    }
  }

  async function viewReceipt(receipt: WalletGrantReceipt) {
    if (!apiConfig?.actorDid || !receipt.recordId) return;
    const actionId = `${receipt.id}:view`;
    setBusyActionIds((ids) => [...ids, actionId]);
    try {
      const invocationToken = receiptRequiresUserPresence(receipt)
        ? await issueRecordDecryptInvocation(apiConfig, {
            grantId: receipt.grantId,
            recordId: receipt.recordId,
            userPresent: true
          })
        : undefined;
      const record = await decryptRecordWithGrant(apiConfig, {
        grantId: receipt.grantId,
        invocationToken,
        recordId: receipt.recordId
      });
      setDecryptedRecordsByReceiptId((records) => ({ ...records, [receipt.id]: record }));
      await refreshWalletAuditEvents().catch(() => undefined);
    } finally {
      setBusyActionIds((ids) => ids.filter((id) => id !== actionId));
    }
  }

  async function delegateReceipt(receipt: WalletGrantReceipt) {
    if (!apiConfig?.actorDid) return;
    const draft = delegationDrafts[receipt.id] ?? { audienceDid: "", purpose: receipt.purpose };
    const audienceDid = draft.audienceDid.trim();
    if (!audienceDid) return;
    const ability = receipt.abilities.includes("record/analyze") || receipt.abilities.includes("*") ? "record/analyze" : receipt.abilities[0];
    const actionId = `${receipt.id}:delegate`;
    setBusyActionIds((ids) => [...ids, actionId]);
    try {
      await delegateGrant(apiConfig, {
        abilities: [ability],
        audienceDid,
        parentGrantId: receipt.grantId,
        purpose: draft.purpose.trim() || receipt.purpose,
        resources: receipt.resources
      });
      setDelegationMessages((messages) => ({ ...messages, [receipt.id]: `Delegated to ${audienceDid}.` }));
      await refreshWalletAccessState();
      await refreshWalletAuditEvents();
    } finally {
      setBusyActionIds((ids) => ids.filter((id) => id !== actionId));
    }
  }

  return (
    <div className="screen">
      <div className="page-title">
        <p className="eyebrow">Recipient access</p>
        <h1>Requests to see my info</h1>
      </div>
      <StatusBanner tone={apiConfig ? "success" : "warning"}>
        {apiConfig ? "Wallet access is connected." : "Connect Abby before acting on live access requests."}
      </StatusBanner>
      <Section title="Safety check">
        <label className="consent-box">
          <input checked={verified} onChange={(event) => setVerified(event.target.checked)} type="checkbox" />
          <span>
            <strong>Confirm I recognize this helper before sharing.</strong>
            <small>Access can be approved, rejected, or revoked later from this screen.</small>
          </span>
        </label>
      </Section>
      <Section title="Access requests">
        <div className="list-stack">
          {accessRequests.length ? (
            accessRequests.map((request) => {
              const needsApproval =
                request.approvalRequired && (request.approvalCount ?? 0) < (request.approvalThreshold ?? 1);
              return (
                <article className="list-item access-request-item" key={request.id}>
                  <div>
                    <h3>{request.requesterName}</h3>
                    <p>{request.resourceLabel}</p>
                    <div className="badge-row">
                      <Badge>{request.status}</Badge>
                      <Badge>{capabilitySummary(request.abilities)}</Badge>
                      {needsApproval ? <Badge tone="warning">controller approval needed</Badge> : null}
                    </div>
                  </div>
                  <div className="row-actions">
                    {needsApproval ? (
                      <Button onClick={() => void recordControllerApproval(request)} variant="secondary">
                        Record approval
                      </Button>
                    ) : null}
                    <Button disabled={!verified} onClick={() => void decideRequest(request.id, "approved")} variant="secondary">
                      Approve
                    </Button>
                    <Button onClick={() => void decideRequest(request.id, "rejected")} variant="danger">
                      Reject
                    </Button>
                    <Button onClick={() => void revokeRequest(request.id)} variant="quiet">
                      Revoke
                    </Button>
                  </div>
                </article>
              );
            })
          ) : (
            <small>No pending access requests.</small>
          )}
        </div>
      </Section>
      <Section title="Shared receipts">
        <div className="list-stack">
          {grantReceipts.length ? (
            grantReceipts.map((receipt) => {
              const draft = delegationDrafts[receipt.id] ?? { audienceDid: "", purpose: receipt.purpose };
              const outputLines = derivedArtifactsByReceiptId[receipt.id] ?? [];
              const decrypted = decryptedRecordsByReceiptId[receipt.id];
              const canAnalyze = receiptHasAbility(receipt, "record/analyze") && receipt.recordId;
              const canView = receiptHasAbility(receipt, "record/decrypt") && receipt.recordId;
              const canDelegate = receiptHasAbility(receipt, "record/share") && receipt.resources.length > 0;

              return (
                <article aria-labelledby={`grant-receipt-${receipt.id}`} className="list-item recipient-list-item" key={receipt.id}>
                  <div className="recipient-summary">
                    <h3 id={`grant-receipt-${receipt.id}`}>{receipt.audienceName}</h3>
                    <p>{receipt.resourceLabel}</p>
                    <div className="badge-row">
                      <Badge tone={receipt.status === "active" ? "success" : "warning"}>{receipt.status}</Badge>
                      <Badge>{receipt.receiptHash}</Badge>
                      <Badge>Share proof code</Badge>
                    </div>
                    <small>{receipt.abilities.map(plainCapabilityLabel).join(", ")}</small>
                  </div>
                  <div className="row-actions">
                    <Button
                      disabled={!canAnalyze || busyActionIds.includes(`${receipt.id}:summary`)}
                      onClick={() => void analyzeReceipt(receipt, "summary")}
                      variant="secondary"
                    >
                      {busyActionIds.includes(`${receipt.id}:summary`) ? "Making summary" : "Make safe summary"}
                    </Button>
                    <Button disabled={!canAnalyze} onClick={() => void analyzeReceipt(receipt, "redacted")} variant="secondary">
                      Redacted analysis
                    </Button>
                    <Button disabled={!canAnalyze} onClick={() => void analyzeReceipt(receipt, "vector")} variant="secondary">
                      Vector profile
                    </Button>
                    <Button disabled={!canAnalyze} onClick={() => void analyzeReceipt(receipt, "extract-text")} variant="secondary">
                      Extract text
                    </Button>
                    <Button disabled={!canAnalyze} onClick={() => void analyzeReceipt(receipt, "form")} variant="secondary">
                      Analyze form
                    </Button>
                    <Button disabled={!canAnalyze} onClick={() => void analyzeReceipt(receipt, "graphrag")} variant="secondary">
                      Build GraphRAG
                    </Button>
                    <Button disabled={!canView} onClick={() => void viewReceipt(receipt)} variant="secondary">
                      View document
                    </Button>
                  </div>
                  {outputLines.length || decrypted ? (
                    <div className="disclosure-package">
                      {outputLines.map((line) => (
                        <div className="disclosure-row" key={line}>
                          <strong>Output</strong>
                          <span>{line}</span>
                        </div>
                      ))}
                      {decrypted ? (
                        <>
                          <div className="disclosure-row">
                            <strong>Document</strong>
                            <span>{decrypted.text}</span>
                          </div>
                          <div className="disclosure-row">
                            <strong>Size</strong>
                            <span>{decrypted.sizeBytes} bytes</span>
                          </div>
                        </>
                      ) : null}
                    </div>
                  ) : null}
                  {canDelegate ? (
                    <form className="delegation-form" onSubmit={(event) => {
                      event.preventDefault();
                      void delegateReceipt(receipt);
                    }}>
                      <Field label="Delegate DID">
                        <input
                          onChange={(event) =>
                            setDelegationDrafts({
                              ...delegationDrafts,
                              [receipt.id]: { ...draft, audienceDid: event.target.value }
                            })
                          }
                          placeholder="did:key:case-worker"
                          value={draft.audienceDid}
                        />
                      </Field>
                      <Field label="Delegated purpose">
                        <input
                          onChange={(event) =>
                            setDelegationDrafts({
                              ...delegationDrafts,
                              [receipt.id]: { ...draft, purpose: event.target.value }
                            })
                          }
                          value={draft.purpose}
                        />
                      </Field>
                      <div className="row-actions">
                        <Button disabled={!draft.audienceDid.trim() || busyActionIds.includes(`${receipt.id}:delegate`)} type="submit">
                          {busyActionIds.includes(`${receipt.id}:delegate`) ? "Delegating" : "Delegate access"}
                        </Button>
                      </div>
                      {delegationMessages[receipt.id] ? <p className="delegation-message">{delegationMessages[receipt.id]}</p> : null}
                    </form>
                  ) : null}
                </article>
              );
            })
          ) : (
            <small>No active grant receipts.</small>
          )}
        </div>
      </Section>
    </div>
  );
}

function receiptHasAbility(receipt: WalletGrantReceipt, ability: string) {
  return receipt.abilities.includes("*") || receipt.abilities.includes(ability);
}

function receiptRequiresUserPresence(receipt: WalletGrantReceipt) {
  return receipt.caveats?.user_presence_required === true || receipt.caveats?.require_user_presence === true;
}

function outputTypeForAnalysisMode(mode: RecipientAnalysisMode) {
  if (mode === "redacted") return "redacted_derived_only";
  if (mode === "vector") return "vector_profile";
  if (mode === "extract-text") return "redacted_extracted_text";
  if (mode === "form") return "redacted_form_analysis";
  if (mode === "graphrag") return "redacted_graphrag";
  return "summary";
}

async function runDerivedAnalysis(
  apiConfig: WalletApiConfig,
  receipt: WalletGrantReceipt,
  mode: Exclude<RecipientAnalysisMode, "summary">,
  invocationToken?: string
) {
  const grantId = receipt.grantId;
  const recordId = receipt.recordId || "";
  if (mode === "redacted") return analyzeRecordRedactedWithGrant(apiConfig, { grantId, invocationToken, recordId });
  if (mode === "vector") return createRecordVectorProfileWithGrant(apiConfig, { grantId, invocationToken, recordId });
  if (mode === "extract-text") return extractRecordTextRedactedWithGrant(apiConfig, { grantId, invocationToken, recordId });
  if (mode === "form") return analyzeRecordFormRedactedWithGrant(apiConfig, { grantId, invocationToken, recordId });
  return createRedactedGraphRAG(apiConfig, { grantId, invocationToken, recordIds: [recordId] });
}

function artifactLines(artifact: { artifactType: string; outputPolicy: string; encryptedPayloadRef: string; sourceRecordIds: string[] }) {
  return [
    `${artifact.artifactType} · ${artifact.outputPolicy}`,
    artifact.encryptedPayloadRef,
    ...artifact.sourceRecordIds
  ];
}

function analysisLines(result: {
  artifact: { artifactType: string; outputPolicy: string; encryptedPayloadRef: string; sourceRecordIds: string[] };
  output: Record<string, unknown>;
}) {
  return [
    ...artifactLines(result.artifact),
    summarizeDerivedOutput(result.output)
  ];
}

function summarizeDerivedOutput(output: Record<string, unknown>) {
  const organizerProfile = output.openrouter_organizer_profile;
  if (organizerProfile && typeof organizerProfile === "object" && !Array.isArray(organizerProfile)) {
    const record = organizerProfile as Record<string, unknown>;
    const summary = typeof record.summary === "string" ? record.summary.trim() : "";
    if (summary) return summary;
  }
  if (typeof output.summary === "string" && output.summary.trim()) return output.summary;
  if (typeof output.text === "string" && output.text.trim()) return output.text;
  const profile = output.profile;
  if (profile && typeof profile === "object" && !Array.isArray(profile)) {
    const record = profile as Record<string, unknown>;
    const profileType = typeof record.profile_type === "string" ? record.profile_type : "vector profile";
    return typeof record.chunk_count === "number" ? `${profileType} · ${record.chunk_count} chunks` : profileType;
  }
  const fields = output.fields;
  if (Array.isArray(fields)) {
    const labels = fields
      .map((field) => {
        if (!field || typeof field !== "object" || Array.isArray(field)) return "";
        return String((field as Record<string, unknown>).label ?? "").trim();
      })
      .filter(Boolean)
      .slice(0, 3);
    return labels.length ? `${fields.length} redacted fields: ${labels.join(", ")}` : `${fields.length} redacted fields`;
  }
  const graph = output.graph;
  if (graph && typeof graph === "object" && !Array.isArray(graph)) {
    const record = graph as Record<string, unknown>;
    const graphType = typeof record.graph_type === "string" ? record.graph_type : "redacted graph";
    if (typeof record.node_count === "number" && typeof record.edge_count === "number") {
      return `${graphType} · ${record.node_count} nodes · ${record.edge_count} edges`;
    }
    return graphType;
  }
  return typeof output.output_policy === "string" ? output.output_policy : "Safe derived output created.";
}

async function buildOpenRouterOrganizerProfile({
  fileName,
  mimeType,
  outputs
}: {
  fileName: string;
  mimeType: string;
  outputs: Record<string, unknown>[];
}): Promise<Record<string, unknown> | undefined> {
  const safeSignals = outputs.map(toSafeOrganizerSignal).filter((signal) => Object.keys(signal).length > 0);
  const prompt = {
    prompt: "Create privacy-preserving organizer metadata from redacted wallet document signals.",
    systemPrompt: [
      "You create privacy-preserving document organizer metadata for a wallet app.",
      "Use only redacted derived signals. Do not infer names, addresses, account numbers, medical facts, legal facts, or other private content.",
      "Return only one JSON object with keys: summary, labels, browseHints, riskSignals.",
      "summary must be a short generic description. labels, browseHints, and riskSignals must be arrays of generic non-identifying strings."
    ].join("\n"),
    userPrompt: JSON.stringify({
      fileName: redactFileNameForRemoteProfile(fileName),
      mimeType,
      redactedSignals: safeSignals.slice(0, 8)
    })
  };
  try {
    const result = await generateHuggingFaceWalletRouterText({
      fallbackReason: "wallet_document_privacy_profile",
      maxTokens: 350,
      prompt
    });
    return normalizeOrganizerProfileJson(result.text, result.model);
  } catch {
    // OpenRouter is a secondary fallback after the wallet-scoped Hugging Face router.
  }
  try {
    const result = await generateOpenRouterText({
      fallbackReason: "wallet_document_privacy_profile",
      localModelName: "openrouter/free",
      maxTokens: 350,
      prompt
    });
    return normalizeOrganizerProfileJson(result.text, result.model);
  } catch {
    return undefined;
  }
}

function toSafeOrganizerSignal(output: Record<string, unknown>): Record<string, unknown> {
  const signal: Record<string, unknown> = {
    output_policy: readString(output, "output_policy"),
    summary: safeShortText(readString(output, "summary")),
    text: safeShortText(readString(output, "text"))
  };
  const profile = output.profile;
  if (profile && typeof profile === "object" && !Array.isArray(profile)) {
    signal.profile = compactRecord({
      profile_type: readString(profile, "profile_type"),
      chunk_count: readNumber(profile, "chunk_count")
    });
  }
  const graph = output.graph;
  if (graph && typeof graph === "object" && !Array.isArray(graph)) {
    signal.graph = compactRecord({
      graph_type: readString(graph, "graph_type"),
      node_count: readNumber(graph, "node_count"),
      edge_count: readNumber(graph, "edge_count")
    });
  }
  const fields = output.fields;
  if (Array.isArray(fields)) {
    signal.field_count = fields.length;
    signal.field_labels = fields
      .map((field) => (field && typeof field === "object" && !Array.isArray(field) ? readString(field, "label") : undefined))
      .filter(Boolean)
      .slice(0, 8);
  }
  const redactionCounts = output.redaction_counts;
  if (redactionCounts && typeof redactionCounts === "object" && !Array.isArray(redactionCounts)) {
    signal.redaction_counts = Object.fromEntries(
      Object.entries(redactionCounts)
        .filter(([, value]) => typeof value === "number")
        .slice(0, 8)
    );
  }
  return compactRecord(signal);
}

function buildPrivacySearchText(outputs: Record<string, unknown>[], publicInputs: Record<string, unknown>): string {
  return [
    "zero knowledge proof",
    "redacted vector profile",
    ...buildPrivacyVectorTerms(outputs, publicInputs),
    stringifyPrivacySearchValue(publicInputs)
  ]
    .join(" ")
    .replace(/\s+/g, " ")
    .trim();
}

function buildPrivacyVectorTerms(outputs: Record<string, unknown>[], publicInputs: Record<string, unknown>): string[] {
  const terms = new Set<string>();
  const add = (value: unknown) => {
    for (const part of privacySearchParts(value)) {
      const normalized = part.trim().toLocaleLowerCase();
      if (normalized.length >= 2 && normalized.length <= 80) terms.add(normalized);
    }
  };
  add(publicInputs);
  for (const output of outputs) {
    add(toSafeOrganizerSignal(output));
  }
  return Array.from(terms).slice(0, 80);
}

function stringifyPrivacySearchValue(value: unknown): string {
  return privacySearchParts(value).join(" ");
}

function privacySearchParts(value: unknown): string[] {
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") return [String(value)];
  if (Array.isArray(value)) return value.flatMap(privacySearchParts);
  if (value && typeof value === "object") {
    return Object.entries(value as Record<string, unknown>).flatMap(([key, nestedValue]) => [key, ...privacySearchParts(nestedValue)]);
  }
  return [];
}

function normalizeOrganizerProfileJson(text: string, model: string): Record<string, unknown> | undefined {
  const parsed = parseFirstJsonObject(text);
  if (!parsed) return undefined;
  const summary = safeShortText(typeof parsed.summary === "string" ? parsed.summary : "");
  const labels = readSafeStringList(parsed.labels, 6);
  const browseHints = readSafeStringList(parsed.browseHints, 6);
  const riskSignals = readSafeStringList(parsed.riskSignals, 6);
  if (!summary && !labels.length && !browseHints.length && !riskSignals.length) return undefined;
  return compactRecord({
    browseHints,
    labels,
    model,
    riskSignals,
    summary
  });
}

function parseFirstJsonObject(text: string): Record<string, unknown> | undefined {
  const trimmed = text.trim();
  const start = trimmed.indexOf("{");
  const end = trimmed.lastIndexOf("}");
  if (start < 0 || end <= start) return undefined;
  try {
    const parsed = JSON.parse(trimmed.slice(start, end + 1));
    return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed as Record<string, unknown> : undefined;
  } catch {
    return undefined;
  }
}

function readSafeStringList(value: unknown, limit: number): string[] {
  if (!Array.isArray(value)) return [];
  return value
    .map((item) => safeShortText(typeof item === "string" ? item : ""))
    .filter(Boolean)
    .slice(0, limit);
}

function safeShortText(value: string | undefined): string {
  return (value || "")
    .replace(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi, "[email]")
    .replace(/\b(?:\+?1[\s.-]?)?(?:\(\d{3}\)|\d{3})[\s.-]?\d{3}[\s.-]?\d{4}\b/g, "[phone]")
    .replace(/\b\d{4,}\b/g, "[number]")
    .trim()
    .slice(0, 240);
}

function redactFileNameForRemoteProfile(fileName: string): string {
  const extension = fileName.split(".").pop()?.toLowerCase();
  return extension && extension !== fileName.toLowerCase() ? `document.${extension}` : "document";
}

function buildFallbackDocumentProfileOutput(upload: UploadItem, mimeType: string): Record<string, unknown> {
  return {
    output_policy: "local_metadata_only",
    profile: {
      chunk_count: 0,
      profile_type: "metadata fallback"
    },
    summary: `${mimeType} wallet file queued for redacted profiling.`,
    upload_state: compactRecord({
      decentralizedStorageStatus: upload.decentralizedStorageStatus,
      hasIpfsCid: Boolean(upload.ipfsCid),
      mimeType
    })
  };
}

function buildDocumentPrivacyProfilePublicInputs({
  artifactIds,
  file,
  fileName,
  mimeType,
  outputs
}: {
  artifactIds: string[];
  file?: File;
  fileName: string;
  mimeType: string;
  outputs: Record<string, unknown>[];
}): Record<string, unknown> {
  const graphOutput = outputs
    .map((output) => output.graph)
    .find((graph) => graph && typeof graph === "object" && !Array.isArray(graph)) as Record<string, unknown> | undefined;
  const profileOutput = outputs
    .map((output) => output.profile)
    .find((profile) => profile && typeof profile === "object" && !Array.isArray(profile)) as Record<string, unknown> | undefined;
  const organizerProfile = outputs
    .map((output) => output.openrouter_organizer_profile)
    .find((profile) => profile && typeof profile === "object" && !Array.isArray(profile)) as Record<string, unknown> | undefined;
  const redactionCount = outputs.reduce((count, output) => {
    const counts = output.redaction_counts;
    if (!counts || typeof counts !== "object" || Array.isArray(counts)) return count;
    return count + Object.values(counts).reduce((sum, value) => sum + (typeof value === "number" ? value : 0), 0);
  }, 0);
  const publicMimeType = normalizePublicMimeType(mimeType, file?.name || fileName);
  return {
    artifact_ids: artifactIds,
    chunk_count: readNumber(profileOutput, "chunk_count"),
    edge_count: readNumber(graphOutput, "edge_count"),
      graph_type: readString(graphOutput, "graph_type"),
      mime_family: publicMimeType.split("/")[0] || "application",
      mime_type: publicMimeType,
      node_count: readNumber(graphOutput, "node_count"),
      openrouter_model: readString(organizerProfile, "model"),
      organizer_labels: readStringArray(organizerProfile, "labels") || defaultLabelsForMimeType(publicMimeType),
      organizer_summary: readString(organizerProfile, "summary") || displayMimeType(publicMimeType),
    output_policies: Array.from(new Set(outputs.map((output) => readString(output, "output_policy")).filter(Boolean))),
    privacy_policy: "no_plaintext_public_inputs",
    profile_methods: Array.from(new Set(outputs.map((output) => readString(output, "output_policy")).filter(Boolean))),
    redaction_count: redactionCount,
    size_bucket: typeof file?.size === "number" ? sizeBucket(file.size) : "unknown",
    summary: "Redacted GraphRAG, vector metadata, and derived descriptors created inside the wallet boundary."
  };
}

function summarizeDocumentPrivacyProfile(publicInputs: Record<string, unknown>) {
  const mimeType = typeof publicInputs.mime_type === "string" ? publicInputs.mime_type : "document";
  const graphType = typeof publicInputs.graph_type === "string" ? publicInputs.graph_type : "redacted graph";
  const nodes = typeof publicInputs.node_count === "number" ? `${publicInputs.node_count} nodes` : "safe graph";
  const chunks = typeof publicInputs.chunk_count === "number" ? `${publicInputs.chunk_count} chunks` : "vector metadata";
  return `${mimeType} · ${graphType} · ${nodes} · ${chunks}`;
}

function classifyDocumentProfile(publicInputs: Record<string, unknown>) {
  const organizerSummary = readString(publicInputs, "organizer_summary");
  if (organizerSummary) return organizerSummary;
  const labels = readStringArray(publicInputs, "organizer_labels");
  if (labels?.length) return labels.slice(0, 3).join(", ");
  return displayMimeType(readString(publicInputs, "mime_type") || "");
}

function displayMimeType(mimeType: string) {
  const normalized = mimeType.trim().toLowerCase();
  if (!normalized) return "Unknown file";
  if (normalized === "application/pdf") return "PDF document";
  if (normalized.startsWith("image/")) return `${normalized.split("/")[1]?.toUpperCase() || "Image"} image`;
  if (normalized.startsWith("text/")) return "Text document";
  if (normalized.includes("json")) return "JSON data";
  if (normalized.includes("spreadsheet") || normalized.includes("excel") || normalized.includes("csv")) return "Spreadsheet";
  if (normalized.includes("wordprocessing") || normalized.includes("msword")) return "Word document";
  if (normalized.includes("presentation") || normalized.includes("powerpoint")) return "Presentation";
  if (normalized.startsWith("audio/")) return "Audio file";
  if (normalized.startsWith("video/")) return "Video file";
  if (normalized === "application/octet-stream") return "Encrypted/binary file";
  return normalized;
}

function detectDecryptedMimeType(bytes: Uint8Array, fileName: string, text: string) {
  const signature = Array.from(bytes.slice(0, 16));
  if (startsWithBytes(signature, [0x25, 0x50, 0x44, 0x46])) return "application/pdf";
  if (startsWithBytes(signature, [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a])) return "image/png";
  if (startsWithBytes(signature, [0xff, 0xd8, 0xff])) return "image/jpeg";
  if (startsWithBytes(signature, [0x47, 0x49, 0x46, 0x38])) return "image/gif";
  if (startsWithBytes(signature, [0x50, 0x4b, 0x03, 0x04])) return officeOrZipMimeType(fileName);
  const trimmed = text.trim();
  if ((trimmed.startsWith("{") && trimmed.endsWith("}")) || (trimmed.startsWith("[") && trimmed.endsWith("]"))) {
    try {
      JSON.parse(trimmed);
      return "application/json";
    } catch {
      // Fall back to extension/text detection below.
    }
  }
  const extensionMimeType = mimeTypeFromFileName(fileName);
  if (extensionMimeType) return extensionMimeType;
  return looksLikeText(bytes) ? "text/plain" : "application/octet-stream";
}

function startsWithBytes(bytes: number[], prefix: number[]) {
  return prefix.every((value, index) => bytes[index] === value);
}

function officeOrZipMimeType(fileName: string) {
  const extensionMimeType = mimeTypeFromFileName(fileName);
  return extensionMimeType || "application/zip";
}

function mimeTypeFromFileName(fileName: string) {
  const extension = fileName.split(".").pop()?.toLowerCase() ?? "";
  if (extension === "pdf") return "application/pdf";
  if (["jpg", "jpeg"].includes(extension)) return "image/jpeg";
  if (extension === "png") return "image/png";
  if (extension === "gif") return "image/gif";
  if (extension === "txt") return "text/plain";
  if (extension === "json") return "application/json";
  if (extension === "csv") return "text/csv";
  if (extension === "doc") return "application/msword";
  if (extension === "docx") return "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
  if (extension === "xls") return "application/vnd.ms-excel";
  if (extension === "xlsx") return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
  if (extension === "ppt") return "application/vnd.ms-powerpoint";
  if (extension === "pptx") return "application/vnd.openxmlformats-officedocument.presentationml.presentation";
  if (extension === "zip") return "application/zip";
  return "";
}

function looksLikeText(bytes: Uint8Array) {
  const sample = bytes.slice(0, Math.min(bytes.length, 512));
  if (!sample.length) return true;
  let printable = 0;
  for (const byte of sample) {
    if (byte === 9 || byte === 10 || byte === 13 || (byte >= 32 && byte < 127) || byte >= 194) {
      printable += 1;
    }
  }
  return printable / sample.length > 0.85;
}

function defaultLabelsForMimeType(mimeType: string) {
  const label = displayMimeType(mimeType);
  return label === "Unknown file" ? [] : [label];
}

function normalizePublicMimeType(mimeType: string, fileName: string) {
  const trimmed = mimeType.trim().toLowerCase();
  if (trimmed) return trimmed;
  const extension = fileName.split(".").pop()?.toLowerCase() ?? "";
  if (extension === "pdf") return "application/pdf";
  if (["jpg", "jpeg"].includes(extension)) return "image/jpeg";
  if (extension === "png") return "image/png";
  if (extension === "txt") return "text/plain";
  if (extension === "json") return "application/json";
  return "application/octet-stream";
}

function sizeBucket(sizeBytes: number) {
  if (sizeBytes < 100_000) return "under_100kb";
  if (sizeBytes < 1_000_000) return "100kb_to_1mb";
  if (sizeBytes < 10_000_000) return "1mb_to_10mb";
  if (sizeBytes < 100_000_000) return "10mb_to_100mb";
  return "over_100mb";
}

function readString(record: unknown, key: string) {
  if (!record || typeof record !== "object" || Array.isArray(record)) return undefined;
  const value = (record as Record<string, unknown>)[key];
  return typeof value === "string" && value.trim() ? value : undefined;
}

function readStringArray(record: unknown, key: string) {
  if (!record || typeof record !== "object" || Array.isArray(record)) return undefined;
  const value = (record as Record<string, unknown>)[key];
  if (!Array.isArray(value)) return undefined;
  const strings = value.filter((item): item is string => typeof item === "string" && item.trim().length > 0);
  return strings.length ? strings.slice(0, 12) : undefined;
}

function readNumber(record: unknown, key: string) {
  if (!record || typeof record !== "object" || Array.isArray(record)) return undefined;
  const value = (record as Record<string, unknown>)[key];
  return typeof value === "number" && Number.isFinite(value) ? value : undefined;
}

function compactRecord(record: Record<string, unknown>): Record<string, unknown> {
  return Object.fromEntries(
    Object.entries(record).filter(([, value]) => {
      if (value === undefined || value === null) return false;
      if (typeof value === "string") return value.trim().length > 0;
      if (Array.isArray(value)) return value.length > 0;
      return true;
    })
  );
}


function parseRecordIds(value: string): string[] {
  return Array.from(
    new Set(
      value
        .split(/[\n,]/)
        .map((recordId) => recordId.trim())
        .filter(Boolean)
    )
  );
}
