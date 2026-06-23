import type {
  CheckInChannel,
  DisclosureDataScope,
  DisclosureRecipientDraft,
  DisclosureRecipientType,
  ProofReceiptView,
  RegistrationProfileDraft
} from "../../models/abby";
import type { ShelterProviderMessage } from "../appState";
import { abilitiesForDisclosureScopes, plainCapabilityLabel, plainNonGrantedCapabilities } from "../../services/capabilities";
import { t, type SupportedLocale } from "../../lib/localization";

// ─── Document constants ───────────────────────────────────────────────────────

export const ID_DOCUMENT_ACCEPT_ATTR = "image/jpeg,image/png,image/webp,application/pdf,.jpg,.jpeg,.png,.webp,.pdf";
export const PROOF_QR_IMAGE_ACCEPT_ATTR = "image/jpeg,image/png,image/webp,.jpg,.jpeg,.png,.webp";
export const ID_DOCUMENT_ACCEPTED_TYPES = new Set(["image/jpeg", "image/png", "image/webp", "application/pdf"]);
export const ID_DOCUMENT_ACCEPTED_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp", ".pdf"];

// ─── Precinct/recipient constants ─────────────────────────────────────────────

export const PORTLAND_POLICE_MISSING_EMAIL = "missing@police.portlandoregon.gov";
export const DEFAULT_LOCAL_PRECINCT = "Local police precinct";
export const LOCAL_PRECINCT_OPTIONS = [DEFAULT_LOCAL_PRECINCT];
export const LOCAL_PRECINCT_RELATIONSHIP = "Local precinct";

// ─── Document file helpers ────────────────────────────────────────────────────

export function isAcceptedIdentityDocument(file: File): boolean {
  const lowerName = file.name.toLowerCase();
  return (
    ID_DOCUMENT_ACCEPTED_TYPES.has(file.type) ||
    ID_DOCUMENT_ACCEPTED_EXTENSIONS.some((extension) => lowerName.endsWith(extension))
  );
}

export function getIdentityDocumentFileDetail(file: File): string {
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

// ─── Recipient/contact formatters ─────────────────────────────────────────────

export function formatRecipientType(type: DisclosureRecipientType, locale: SupportedLocale): string {
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

export function localizedPrecinctName(name: string, locale: SupportedLocale): string {
  return name === DEFAULT_LOCAL_PRECINCT ? t(locale, "contacts.defaultPrecinct") : name;
}

export function localizedRelationshipName(name: string, locale: SupportedLocale): string {
  if (name === "Shelter") return t(locale, "contacts.shelterGroup");
  return name === LOCAL_PRECINCT_RELATIONSHIP ? t(locale, "contacts.localPrecinctRelationship") : name;
}

export function formatContactRequestStatus(status: string, locale: SupportedLocale): string {
  if (status === "approved") return t(locale, "contacts.status.approved");
  if (status === "denied") return t(locale, "contacts.status.denied");
  if (status === "canceled") return t(locale, "contacts.status.canceled");
  return t(locale, "contacts.status.pending");
}

export function isLocalPrecinctRecipient(recipient: DisclosureRecipientDraft, precinctName: string): boolean {
  return recipient.type === "police_precinct" && (recipient.precinctName === precinctName || recipient.displayName === precinctName);
}

export function createEntityId(prefix: string): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return `${prefix}-${crypto.randomUUID()}`;
  }
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

// ─── Disclosure scope helpers ─────────────────────────────────────────────────

export function disclosureScopeLabelKey(scope: DisclosureDataScope) {
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

export function disclosureScopeDetailKey(scope: DisclosureDataScope) {
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

export function getDisclosureScopeLabels(scopes: DisclosureDataScope[], locale: SupportedLocale): string {
  return scopes.map((scope) => t(locale, disclosureScopeLabelKey(scope))).join(", ");
}

export function toggleScopeSelection(scopes: DisclosureDataScope[], scope: DisclosureDataScope): DisclosureDataScope[] {
  return scopes.includes(scope) ? scopes.filter((item) => item !== scope) : [...scopes, scope];
}

// ─── Capability helpers ───────────────────────────────────────────────────────

export function formatLocalizedCapability(ability: string, locale: SupportedLocale): string {
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

export function formatLocalizedCapabilitySummary(abilities: string[], locale: SupportedLocale): string {
  return abilities.map((ability) => formatLocalizedCapability(ability, locale)).join(", ");
}

export function formatLocalizedNonGrantedCapabilities(abilities: string[], locale: SupportedLocale): string {
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

export function abilitiesForScopes(scopes: DisclosureDataScope[]): string[] {
  return abilitiesForDisclosureScopes(scopes);
}

// ─── Analytics helpers ────────────────────────────────────────────────────────

export const analyticsNeverPublishedText =
  "No names, contact details, exact locations, files, staff actions, case notes, or individual service histories";
export const analyticsProviderPublicationFloor = 3;

export function parseAnalyticsProofNumber(value: string | undefined): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

export function calculatePercent(value: number, total: number): number {
  if (!total) return 0;
  return Math.round((value / total) * 100);
}

export function formatAnalyticsProofValue(value: string | undefined): string {
  if (!value) return "";
  const numeric = Number(value);
  if (Number.isFinite(numeric)) return numeric.toLocaleString();
  return value
    .split("_")
    .map((part) => `${part.charAt(0).toUpperCase()}${part.slice(1)}`)
    .join(" ");
}

export function formatAnalyticsField(field: string): string {
  const labels: Record<string, string> = {
    age_group: "age group",
    county: "county",
    housing_outcome: "housing outcome",
    need_category: "need type",
    service_type: "service type"
  };
  return labels[field] ?? field.replace(/_/g, " ");
}

// ─── Proof center helpers ─────────────────────────────────────────────────────

export const hiddenProofCenterProofTypes = new Set(["location_distance"]);

export function visibleProofCenterProofs(proofs: ProofReceiptView[]): ProofReceiptView[] {
  return proofs.filter((proof) => !hiddenProofCenterProofTypes.has(proof.proofType));
}

export function summarizeWalletProofClaims(proofs: ProofReceiptView[]): string {
  const claims = proofs.map((proof) => proof.claim);
  if (claims.length <= 3) return claims.join(", ") || "Wallet proof summary";
  return `${claims.slice(0, 3).join(", ")}, +${claims.length - 3} more`;
}

// ─── Upload / summary helpers ─────────────────────────────────────────────────

export function toShortSummaryTitle(text: string): string {
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

export async function generateUploadSummary(file: File): Promise<string> {
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

// ─── Channel/timestamp formatters ────────────────────────────────────────────

export function formatCheckInChannel(channel: CheckInChannel, locale: SupportedLocale): string {
  if (channel === "sms") return t(locale, "channel.sms");
  if (channel === "email") return t(locale, "channel.email");
  return t(locale, "channel.web");
}

export function formatProviderMessageChannel(channel: ShelterProviderMessage["channel"], locale: SupportedLocale): string {
  if (channel === "sms") return t(locale, "channel.sms");
  if (channel === "email") return t(locale, "channel.email");
  return t(locale, "messages.inApp");
}

export function formatRequestTimestamp(value: string, locale: SupportedLocale): string {
  const timestamp = new Date(value);
  if (Number.isNaN(timestamp.getTime())) return t(locale, "government.requestedOn");
  return `${t(locale, "government.requestedOn")} ${timestamp.toLocaleDateString(locale, { month: "short", day: "numeric" })}`;
}

// ─── Message matching ─────────────────────────────────────────────────────────

export function normalizeClientMessageKey(value: string): string {
  const trimmed = value.trim().toLowerCase();
  if (!trimmed) return "";
  if (trimmed.includes("@")) return trimmed;
  const digits = trimmed.replace(/\D/g, "");
  return digits.length >= 7 ? digits : trimmed.replace(/[^a-z0-9]+/g, " ");
}

export function messageMatchesClient(
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
