import { ChangeEvent, FormEvent, useEffect, useMemo, useState } from "react";
import {
  ArrowDown,
  ArrowUp,
  Bell,
  BarChart3,
  CalendarCheck,
  ClipboardCheck,
  ContactRound,
  FileUp,
  HeartHandshake,
  Home,
  KeyRound,
  Landmark,
  LockKeyhole,
  LogOut,
  Menu,
  MessageSquare,
  ShieldCheck,
  Upload,
  UsersRound
} from "lucide-react";
import {
  ActionCard,
  Badge,
  Button,
  Card,
  Field,
  LoadingIndicator,
  RequiredMarker,
  Section,
  SensitiveValue,
  StatusBanner,
  StatusIndicator,
  Stepper
} from "../components/ui";
import {
  CheckInChannel,
  ContactMethodVerificationStatus,
  DisclosureDataScope,
  DisclosureRecipientDraft,
  DisclosureRecipientType,
  EasyBotCheckStatus,
  RegistrationProfileDraft,
  RouteId,
  UploadItem,
  WalletAccessRequest
} from "../models/abby";
import {
  analyticsStudies,
  auditEvents,
  defaultCheckInPolicy,
  emptyRegistrationProfile,
  initialRecipients,
  initialAccessRequests,
  initialUploads,
  serviceMatches
} from "../services/mockAbbyService";

const routes: Array<{ id: RouteId; label: string; icon: typeof Home }> = [
  { id: "home", label: "Home", icon: Home },
  { id: "register", label: "Register", icon: ClipboardCheck },
  { id: "check-in", label: "Check in", icon: CalendarCheck },
  { id: "contacts", label: "Contacts", icon: ContactRound },
  { id: "sharing-rules", label: "Sharing", icon: ShieldCheck },
  { id: "uploads", label: "Uploads", icon: FileUp },
  { id: "social-services", label: "Services", icon: HeartHandshake },
  { id: "shelter", label: "Shelter", icon: UsersRound }
];

const secondaryRoutes: Array<{ id: RouteId; label: string; icon: typeof Home }> = [
  { id: "recipient-access", label: "Recipient access", icon: KeyRound },
  { id: "benefits-protection", label: "Benefits opt-in", icon: Landmark },
  { id: "analytics", label: "Analytics", icon: BarChart3 },
  { id: "security", label: "Security", icon: LockKeyhole },
  { id: "audit", label: "Audit", icon: ClipboardCheck }
];

const serviceNeeds = ["Shelter", "Food", "Health", "Legal", "Benefits", "Transportation"];
const uploadCategories = ["Identity", "Benefits", "Medical", "Housing", "Legal", "Notes", "Other"];
const uploadSensitivityOptions: UploadItem["sensitivity"][] = ["low", "moderate", "high", "restricted"];
const recipientTypeLabels: Record<DisclosureRecipientType, string> = {
  emergency_contact: "Emergency contact",
  social_worker: "Social worker",
  police_precinct: "Police precinct",
  shelter_staff: "Shelter staff",
  government_liaison: "Government liaison",
  benefits_agency: "Benefits agency"
};
const checkInIntervalPresets = [1, 3, 7, 14, 30];

const shelterOptions = [
  "Rose City Shelter",
  "Downtown Outreach Shelter",
  "Harbor Night Shelter",
  "Northside Family Shelter"
];

type ShelterStaffAccount = {
  id: string;
  shelter: string;
  displayName: string;
  email: string;
  verified: boolean;
  updatedAt: string;
};

type ShelterPinConfig = {
  shelter: string;
  staffPin: string;
  adminPin: string;
  updatedAt: string;
};

type ShelterAuditEvent = {
  id: string;
  shelter: string;
  actor: string;
  action: string;
  timestamp: string;
};

type AdminVerificationStatus = "idle" | "missing_pin" | "invalid_pin" | "verified";
type StateSetter<T> = (value: T | ((current: T) => T)) => void;

type ShelterUserAccount = {
  id: string;
  shelter: string;
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
  easyBotCheckStatus: EasyBotCheckStatus;
  captchaToken: string;
  localPrecinctNotified: boolean;
  foundPermanentHousing: boolean;
  createdByStaffId: string;
  createdAt: string;
};

const defaultManagedUserDraft = {
  legalName: "",
  preferredName: "",
  pronouns: "",
  dateOfBirth: "",
  photoAssetId: "",
  phone: "",
  email: "",
  currentLocation: "",
  preferredShelter: "",
  socialWorker: "",
  emergencyContactStarter: "",
  serviceNeeds: [] as string[],
  easyBotCheckStatus: "pending" as EasyBotCheckStatus,
  captchaToken: "",
  localPrecinctNotified: false,
  foundPermanentHousing: false
};

const initialShelterPinConfigs: ShelterPinConfig[] = [
  { shelter: "Rose City Shelter", staffPin: "1234", adminPin: "9001", updatedAt: "2026-05-01T09:00:00.000Z" },
  { shelter: "Downtown Outreach Shelter", staffPin: "2345", adminPin: "9002", updatedAt: "2026-05-01T09:00:00.000Z" },
  { shelter: "Harbor Night Shelter", staffPin: "3456", adminPin: "9003", updatedAt: "2026-05-01T09:00:00.000Z" },
  { shelter: "Northside Family Shelter", staffPin: "4567", adminPin: "9004", updatedAt: "2026-05-01T09:00:00.000Z" }
];

const initialShelterStaffAccounts: ShelterStaffAccount[] = [
  {
    id: "staff-rose-seed",
    shelter: "Rose City Shelter",
    displayName: "Riley Carter",
    email: "riley.staff@example.org",
    verified: true,
    updatedAt: "2026-05-01T09:15:00.000Z"
  }
];

const initialShelterUserAccounts: ShelterUserAccount[] = [
  {
    id: "user-rose-early",
    shelter: "Rose City Shelter",
    legalName: "Ari Morgan",
    preferredName: "Ari",
    pronouns: "they/them",
    dateOfBirth: "1988-04-02",
    photoAssetId: "ari-profile.webp",
    phone: "(503) 555-0140",
    email: "ari@example.org",
    currentLocation: "Rose City Shelter",
    preferredShelter: "Rose City Shelter",
    socialWorker: "Downtown Outreach",
    emergencyContactStarter: "Maya Johnson",
    serviceNeeds: ["Shelter", "Benefits"],
    easyBotCheckStatus: "passed",
    captchaToken: "mock-captcha-token",
    localPrecinctNotified: true,
    foundPermanentHousing: false,
    createdByStaffId: "staff-former-rose",
    createdAt: "2026-04-28T10:00:00.000Z"
  },
  {
    id: "user-rose-health",
    shelter: "Rose City Shelter",
    legalName: "Jordan Lee",
    preferredName: "Jordan",
    pronouns: "",
    dateOfBirth: "1979-11-18",
    photoAssetId: "jordan-profile.png",
    phone: "",
    email: "",
    currentLocation: "Downtown area",
    preferredShelter: "Rose City Shelter",
    socialWorker: "",
    emergencyContactStarter: "",
    serviceNeeds: ["Health", "Transportation"],
    easyBotCheckStatus: "failed",
    captchaToken: "mock-captcha-token",
    localPrecinctNotified: false,
    foundPermanentHousing: false,
    createdByStaffId: "staff-rose-seed",
    createdAt: "2026-04-30T14:20:00.000Z"
  },
  {
    id: "user-rose-housed",
    shelter: "Rose City Shelter",
    legalName: "Sam Rivera",
    preferredName: "Sam",
    pronouns: "he/him",
    dateOfBirth: "1992-06-12",
    photoAssetId: "sam-profile.jpg",
    phone: "",
    email: "sam@example.org",
    currentLocation: "Apartment",
    preferredShelter: "Rose City Shelter",
    socialWorker: "",
    emergencyContactStarter: "",
    serviceNeeds: ["Legal"],
    easyBotCheckStatus: "passed",
    captchaToken: "mock-captcha-token",
    localPrecinctNotified: false,
    foundPermanentHousing: true,
    createdByStaffId: "staff-rose-seed",
    createdAt: "2026-04-26T12:00:00.000Z"
  },
  {
    id: "user-downtown-prefers-rose",
    shelter: "Downtown Outreach Shelter",
    legalName: "Taylor Nguyen",
    preferredName: "Taylor",
    pronouns: "",
    dateOfBirth: "1984-08-09",
    photoAssetId: "taylor-profile.png",
    phone: "",
    email: "",
    currentLocation: "Downtown Outreach Shelter",
    preferredShelter: "Rose City Shelter",
    socialWorker: "",
    emergencyContactStarter: "",
    serviceNeeds: ["Food"],
    easyBotCheckStatus: "failed",
    captchaToken: "mock-captcha-token",
    localPrecinctNotified: true,
    foundPermanentHousing: false,
    createdByStaffId: "staff-downtown-seed",
    createdAt: "2026-05-01T08:00:00.000Z"
  }
];

const disclosureScopes: Array<{ id: DisclosureDataScope; label: string; detail: string }> = [
  { id: "identity_minimum", label: "Minimum identity", detail: "Name, birth date, and contact status" },
  { id: "profile", label: "Profile", detail: "Basic profile details and service needs" },
  { id: "photo", label: "Photo", detail: "The profile photo or photo ID image selected during setup" },
  { id: "current_location", label: "Current location", detail: "Most recent safe location or shelter" },
  { id: "uploaded_documents", label: "Uploads", detail: "Documents the user explicitly includes" },
  { id: "missed_check_in", label: "Missed check-in", detail: "Whether a check-in was missed" },
  { id: "found_permanent_housing", label: "Found permanent housing", detail: "Whether stable housing was reported" },
  { id: "medical_notes", label: "Medical notes", detail: "Sensitive health context" },
  { id: "shelter_history", label: "Shelter history", detail: "Shelter stays and staff contact details" },
  { id: "benefits_information", label: "Benefits information", detail: "Benefits identifiers and status" },
  { id: "custom", label: "Custom note", detail: "A user-written emergency note" }
];

const APP_PERSIST_KEY = "abby-ui-state-v1";
const DEFAULT_SHARING_SCOPES: DisclosureDataScope[] = ["identity_minimum", "photo"];
const PROFILE_PHOTO_ACCEPTED_TYPES = new Set(["image/jpeg", "image/png", "image/webp"]);
const PROFILE_PHOTO_ACCEPTED_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp"];
const PROFILE_PHOTO_ACCEPT_ATTR = "image/jpeg,image/png,image/webp";
const PROFILE_PHOTO_HELP = "Accepts JPEG, PNG, or WebP images. Upload PDFs in the document vault instead.";

const defaultShelterChecklist = {
  userPresent: false,
  clearBrowserData: false,
  auditLogConfirmed: false
};

const defaultSecuritySettings = {
  sessionTimeoutEnabled: true,
  recoveryRemindersEnabled: false,
  publicFormCaptchaEnabled: true,
  passkeyPlaceholderEnabled: false
};

const defaultRegistrationStaffDraft = {
  isShelterStaff: false,
  selectedShelter: "",
  currentStaffAccountId: ""
};

type PersistedAppState = {
  profile?: RegistrationProfileDraft;
  policy?: typeof defaultCheckInPolicy;
  recipients?: DisclosureRecipientDraft[];
  uploads?: UploadItem[];
  shelterStaffAccounts?: ShelterStaffAccount[];
  shelterUserAccounts?: ShelterUserAccount[];
  shelterPinConfigs?: ShelterPinConfig[];
  shelterAuditEvents?: ShelterAuditEvent[];
  activeStaffSessionId?: string;
  benefitsOptIn?: boolean;
  benefitsConsentHistory?: string[];
  analyticsOptIn?: Record<string, boolean>;
  shelterChecklist?: typeof defaultShelterChecklist;
  securitySettings?: typeof defaultSecuritySettings;
  registrationStaffDraft?: typeof defaultRegistrationStaffDraft;
};

function readPersistedAppState(): PersistedAppState {
  if (typeof window === "undefined") return {};
  try {
    const raw = window.localStorage.getItem(APP_PERSIST_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === "object" ? (parsed as PersistedAppState) : {};
  } catch {
    return {};
  }
}

type UploadSummaryResult = {
  title: string;
  status: NonNullable<UploadItem["summaryStatus"]>;
};

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

function getEffectiveSharingScopes(recipient: DisclosureRecipientDraft): DisclosureDataScope[] {
  const savedScopes = Array.isArray(recipient.allowedScopes) ? recipient.allowedScopes : [];
  if (recipient.sharingRuleCustomized || savedScopes.length > 0) {
    return savedScopes;
  }
  return DEFAULT_SHARING_SCOPES;
}

function getRecipientTypeLabel(type: DisclosureRecipientType): string {
  return recipientTypeLabels[type];
}

function getRecipientAccessStatus(recipient: DisclosureRecipientDraft): string {
  if (recipient.revokedAt) return "Disclosure revoked";
  if (recipient.emergencyDisclosureEnabled) return "Emergency disclosure enabled";
  if (getEffectiveSharingScopes(recipient).length) return "Review required";
  return "No scopes selected";
}

function getContactMethodStatus(
  value: string,
  savedStatus: ContactMethodVerificationStatus | undefined,
  recipientVerified = false
): ContactMethodVerificationStatus {
  if (!value.trim()) return "missing";
  return savedStatus ?? (recipientVerified ? "verified" : "unverified");
}

function getNextContactMethodStatus(
  value: string,
  existingStatus: ContactMethodVerificationStatus | undefined,
  changed: boolean
): ContactMethodVerificationStatus {
  if (!value.trim()) return "missing";
  if (changed) return "unverified";
  return existingStatus ?? "unverified";
}

function getContactMethodLabel(method: "phone" | "email", status: ContactMethodVerificationStatus): string {
  if (status === "missing") return method === "phone" ? "No phone" : "No email";
  if (status === "verified") return method === "phone" ? "Phone verified" : "Email verified";
  return method === "phone" ? "Phone needs verification" : "Email needs verification";
}

function getContactMethodTone(status: ContactMethodVerificationStatus): string {
  if (status === "verified") return "success";
  if (status === "missing") return "neutral";
  return "warning";
}

function getScopeLabel(scope: DisclosureDataScope): string {
  return disclosureScopes.find((item) => item.id === scope)?.label ?? scope.replace(/_/g, " ");
}

function getRecipientScopeSummary(recipient: DisclosureRecipientDraft): string {
  const scopes = getEffectiveSharingScopes(recipient);
  if (!scopes.length) return "No disclosure scopes selected";
  const labels = scopes.slice(0, 3).map(getScopeLabel);
  const remaining = scopes.length - labels.length;
  return remaining > 0 ? `${labels.join(", ")} +${remaining} more` : labels.join(", ");
}

function createRecipientHistoryEntry(action: string): string {
  return `${new Date().toLocaleString()}: ${action}`;
}

function normalizeRecipientSharingDefaults(recipients: DisclosureRecipientDraft[]): DisclosureRecipientDraft[] {
  return recipients.map((recipient) => ({
    ...recipient,
    emailVerificationStatus: getContactMethodStatus(
      recipient.email,
      recipient.emailVerificationStatus,
      recipient.verified
    ),
    phoneVerificationStatus: getContactMethodStatus(
      recipient.phone,
      recipient.phoneVerificationStatus,
      recipient.verified
    ),
    allowedScopes: [...getEffectiveSharingScopes(recipient)],
    emergencyDisclosureEnabled: Boolean(recipient.emergencyDisclosureEnabled),
    sharingHistory: Array.isArray(recipient.sharingHistory) ? recipient.sharingHistory : []
  }));
}

function normalizeShelterPinConfigs(configs: ShelterPinConfig[] | undefined): ShelterPinConfig[] {
  return initialShelterPinConfigs.map((fallback) => {
    const saved = configs?.find((config) => config.shelter === fallback.shelter);
    return saved ? { ...fallback, ...saved } : fallback;
  });
}

function getShelterPinConfig(configs: ShelterPinConfig[], shelter: string): ShelterPinConfig {
  return configs.find((config) => config.shelter === shelter) ?? initialShelterPinConfigs[0];
}

function createShelterAuditEvent(shelter: string, actor: string, action: string): ShelterAuditEvent {
  return {
    id: `shelter-audit-${Date.now()}-${Math.round(Math.random() * 1000)}`,
    shelter,
    actor,
    action,
    timestamp: new Date().toISOString()
  };
}

function isBotCheckReady(status: EasyBotCheckStatus, captchaToken: string): boolean {
  return status !== "pending" && Boolean(captchaToken);
}

function isShelterRelatedHealthCheckStatus(
  account: Pick<ShelterUserAccount, "easyBotCheckStatus" | "preferredShelter" | "createdByStaffId">
): boolean {
  return (
    account.easyBotCheckStatus === "failed" &&
    Boolean((account.preferredShelter ?? "").trim() || (account.createdByStaffId ?? "").trim())
  );
}

function isAcceptedProfilePhoto(file: File): boolean {
  const fileName = file.name.toLowerCase();
  if (file.type === "application/pdf" || fileName.endsWith(".pdf")) {
    return false;
  }
  return (
    PROFILE_PHOTO_ACCEPTED_TYPES.has(file.type) ||
    (!file.type && PROFILE_PHOTO_ACCEPTED_EXTENSIONS.some((extension) => fileName.endsWith(extension)))
  );
}

function createFallbackUploadSummary(file: File, status: UploadSummaryResult["status"] = "fallback"): UploadSummaryResult {
  const fileNameWithoutExtension = file.name.replace(/\.[^/.]+$/, "");
  return {
    title: toShortSummaryTitle(fileNameWithoutExtension || file.name || "Uploaded document"),
    status
  };
}

async function createUploadSummary(file: File): Promise<UploadSummaryResult> {
  try {
    if (file.type.startsWith("text/")) {
      const text = (await file.text()).trim();
      return text ? { title: toShortSummaryTitle(text), status: "generated" } : createFallbackUploadSummary(file);
    }

    if (file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf")) {
      const { getDocument, GlobalWorkerOptions } = await import("pdfjs-dist");
      GlobalWorkerOptions.workerSrc = new URL("pdfjs-dist/build/pdf.worker.min.mjs", import.meta.url).toString();

      const pdf = await getDocument({ data: await file.arrayBuffer() }).promise;
      const pageLimit = Math.min(pdf.numPages, 2);
      const pageText: string[] = [];
      for (let pageNumber = 1; pageNumber <= pageLimit; pageNumber += 1) {
        const page = await pdf.getPage(pageNumber);
        const textContent = await page.getTextContent();
        pageText.push(
          textContent.items
            .map((item) => ("str" in item ? item.str : ""))
            .join(" ")
        );
      }

      const extractedText = pageText.join(" ").trim();
      return extractedText
        ? { title: toShortSummaryTitle(extractedText), status: "generated" }
        : createFallbackUploadSummary(file);
    }

    if (file.type.startsWith("image/")) {
      if (file.size < 128) {
        return createFallbackUploadSummary(file);
      }
      const { recognize } = await import("tesseract.js");
      const result = await recognize(file, "eng");
      const ocrText = result.data.text.trim();
      return ocrText ? { title: toShortSummaryTitle(ocrText), status: "generated" } : createFallbackUploadSummary(file);
    }
  } catch {
    return createFallbackUploadSummary(file, "failed");
  }

  return createFallbackUploadSummary(file);
}

function getRouteFromHash(): RouteId {
  const route = window.location.hash.replace("#/", "") || "home";
  return [...routes, ...secondaryRoutes].some((item) => item.id === route) ? (route as RouteId) : "home";
}

export function App() {
  const persistedState = useMemo(readPersistedAppState, []);
  const [activeRoute, setActiveRoute] = useState<RouteId>(getRouteFromHash);
  const [profile, setProfile] = useState<RegistrationProfileDraft>(() => ({
    ...emptyRegistrationProfile,
    ...persistedState.profile
  }));
  const [policy, setPolicy] = useState(() => ({
    ...defaultCheckInPolicy,
    ...persistedState.policy
  }));
  const [recipients, setRecipients] = useState<DisclosureRecipientDraft[]>(() =>
    normalizeRecipientSharingDefaults(Array.isArray(persistedState.recipients) ? persistedState.recipients : initialRecipients)
  );
  const [uploads, setUploads] = useState<UploadItem[]>(() =>
    Array.isArray(persistedState.uploads)
      ? persistedState.uploads.map((upload) => {
          const legacyUpload = upload as UploadItem & { shared?: boolean };
          return {
            ...upload,
            sharingEligible: Boolean(upload.sharingEligible ?? legacyUpload.shared)
          };
        })
      : initialUploads
  );
  const [accessRequests, setAccessRequests] = useState<WalletAccessRequest[]>(initialAccessRequests);
  const [shelterStaffAccounts, setShelterStaffAccounts] = useState<ShelterStaffAccount[]>(() =>
    Array.isArray(persistedState.shelterStaffAccounts) ? persistedState.shelterStaffAccounts : initialShelterStaffAccounts
  );
  const [shelterUserAccounts, setShelterUserAccounts] = useState<ShelterUserAccount[]>(() =>
    Array.isArray(persistedState.shelterUserAccounts)
      ? persistedState.shelterUserAccounts.map((account) => ({
          ...account,
          easyBotCheckStatus: (account.easyBotCheckStatus as EasyBotCheckStatus) ?? "pending",
          localPrecinctNotified: Boolean(account.localPrecinctNotified),
          foundPermanentHousing: Boolean(account.foundPermanentHousing)
        }))
      : initialShelterUserAccounts
  );
  const [shelterPinConfigs, setShelterPinConfigs] = useState<ShelterPinConfig[]>(() =>
    normalizeShelterPinConfigs(persistedState.shelterPinConfigs)
  );
  const [shelterAuditEvents, setShelterAuditEvents] = useState<ShelterAuditEvent[]>(() =>
    Array.isArray(persistedState.shelterAuditEvents) ? persistedState.shelterAuditEvents : []
  );
  const [activeStaffSessionId, setActiveStaffSessionId] = useState(() => persistedState.activeStaffSessionId ?? "");
  const [recipientVerified, setRecipientVerified] = useState(false);
  const [benefitsOptIn, setBenefitsOptIn] = useState(() => persistedState.benefitsOptIn ?? false);
  const [benefitsConsentHistory, setBenefitsConsentHistory] = useState<string[]>(() =>
    Array.isArray(persistedState.benefitsConsentHistory) ? persistedState.benefitsConsentHistory : []
  );
  const [analyticsOptIn, setAnalyticsOptIn] = useState<Record<string, boolean>>(() =>
    persistedState.analyticsOptIn && typeof persistedState.analyticsOptIn === "object"
      ? persistedState.analyticsOptIn
      : {}
  );
  const [shelterChecklist, setShelterChecklist] = useState(() => ({
    ...defaultShelterChecklist,
    ...persistedState.shelterChecklist
  }));
  const [securitySettings, setSecuritySettings] = useState(() => ({
    ...defaultSecuritySettings,
    ...persistedState.securitySettings
  }));
  const [registrationStaffDraft, setRegistrationStaffDraft] = useState(() => ({
    ...defaultRegistrationStaffDraft,
    ...persistedState.registrationStaffDraft
  }));
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const activeStaffSession =
    shelterStaffAccounts.find((account) => account.id === activeStaffSessionId && account.verified) ?? null;
  const visibleRoutes = activeStaffSession ? routes : routes.filter((route) => route.id !== "shelter");

  useEffect(() => {
    if (activeStaffSessionId && !activeStaffSession) {
      setActiveStaffSessionId("");
    }
  }, [activeStaffSession, activeStaffSessionId]);

  useEffect(() => {
    const syncRouteFromHash = () => setActiveRoute(getRouteFromHash());
    window.addEventListener("hashchange", syncRouteFromHash);
    return () => window.removeEventListener("hashchange", syncRouteFromHash);
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    // Persist durable preferences only; transient reveal state such as photo preview toggles and PIN entry stays local.
    const payload: PersistedAppState = {
      profile,
      policy,
      recipients,
      uploads,
      shelterStaffAccounts,
      shelterUserAccounts,
      shelterPinConfigs,
      shelterAuditEvents,
      activeStaffSessionId,
      benefitsOptIn,
      benefitsConsentHistory,
      analyticsOptIn,
      shelterChecklist,
      securitySettings,
      registrationStaffDraft
    };
    window.localStorage.setItem(APP_PERSIST_KEY, JSON.stringify(payload));
  }, [
    profile,
    policy,
    recipients,
    uploads,
    shelterStaffAccounts,
    shelterUserAccounts,
    shelterPinConfigs,
    shelterAuditEvents,
    activeStaffSessionId,
    benefitsOptIn,
    benefitsConsentHistory,
    analyticsOptIn,
    shelterChecklist,
    securitySettings,
    registrationStaffDraft
  ]);

  function navigate(route: RouteId) {
    window.location.hash = route === "home" ? "#/" : `#/${route}`;
    setActiveRoute(route);
    setMobileNavOpen(false);
  }

  const nextCheckIn = useMemo(() => {
    const next = new Date(policy.lastCheckInAt);
    next.setDate(next.getDate() + policy.intervalDays);
    return next.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
  }, [policy.intervalDays, policy.lastCheckInAt]);

  useEffect(() => {
    const onInteractiveClick = (event: MouseEvent) => {
      const target = event.target as HTMLElement | null;
      if (!target) return;
      if (!target.closest("button, input[type='checkbox'], input[type='radio']")) return;

      document.body.classList.remove("playful-pulse");
      void document.body.offsetWidth;
      document.body.classList.add("playful-pulse");
      window.setTimeout(() => document.body.classList.remove("playful-pulse"), 680);
    };

    document.addEventListener("click", onInteractiveClick);
    return () => {
      document.removeEventListener("click", onInteractiveClick);
      document.body.classList.remove("playful-pulse");
    };
  }, []);

  return (
    <div className="app">
      <div aria-hidden="true" className="margin-decor margin-decor-left">
        <span className="decor-shape decor-butterfly" />
        <span className="decor-shape decor-flower" />
        <span className="decor-shape decor-butterfly" />
      </div>
      <div aria-hidden="true" className="margin-decor margin-decor-right">
        <span className="decor-shape decor-flower" />
        <span className="decor-shape decor-butterfly" />
        <span className="decor-shape decor-flower" />
      </div>
      <aside className="sidebar" aria-label="Primary navigation">
        <div className="brand">
          <span className="brand-mark">A</span>
          <div>
            <strong>Abby</strong>
            <small>Safety and services</small>
          </div>
        </div>
        <nav className="nav-list">
          {visibleRoutes.map((route) => (
            <NavButton
              active={activeRoute === route.id}
              icon={route.icon}
              key={route.id}
              label={route.label}
              onClick={() => navigate(route.id)}
            />
          ))}
        </nav>
        <div className="nav-secondary">
          {secondaryRoutes.map((route) => (
            <NavButton
              active={activeRoute === route.id}
              icon={route.icon}
              key={route.id}
              label={route.label}
              onClick={() => navigate(route.id)}
            />
          ))}
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <Button
            ariaControls="mobile-navigation"
            ariaExpanded={mobileNavOpen}
            ariaLabel={mobileNavOpen ? "Close menu" : "Open menu"}
            onClick={() => setMobileNavOpen(!mobileNavOpen)}
            variant="quiet"
          >
            <Menu size={20} />
          </Button>
          <div>
            <strong>Abby</strong>
            <small>Next check-in: {nextCheckIn}</small>
          </div>
          <Button ariaLabel="Sign out" variant="quiet">
            <LogOut size={20} />
          </Button>
        </header>

        {mobileNavOpen ? (
          <nav className="mobile-nav-panel" id="mobile-navigation" aria-label="Mobile navigation">
            {[...visibleRoutes, ...secondaryRoutes].map((route) => (
              <NavButton
                active={activeRoute === route.id}
                icon={route.icon}
                key={route.id}
                label={route.label}
                onClick={() => navigate(route.id)}
              />
            ))}
          </nav>
        ) : null}

        {activeRoute === "home" ? (
          <HomeScreen navigate={navigate} nextCheckIn={nextCheckIn} recipients={recipients} uploads={uploads} />
        ) : null}
        {activeRoute === "register" ? (
          <RegistrationScreen
            profile={profile}
            registrationStaffDraft={registrationStaffDraft}
            setRegistrationStaffDraft={setRegistrationStaffDraft}
            setProfile={setProfile}
            shelterPinConfigs={shelterPinConfigs}
            shelterStaffAccounts={shelterStaffAccounts}
            setShelterStaffAccounts={setShelterStaffAccounts}
            setActiveStaffSessionId={setActiveStaffSessionId}
            setShelterAuditEvents={setShelterAuditEvents}
          />
        ) : null}
        {activeRoute === "check-in" ? (
          <CheckInScreen nextCheckIn={nextCheckIn} policy={policy} setPolicy={setPolicy} />
        ) : null}
        {activeRoute === "contacts" ? (
          <ContactsScreen navigate={navigate} recipients={recipients} setRecipients={setRecipients} />
        ) : null}
        {activeRoute === "sharing-rules" ? (
          <SharingRulesScreen recipients={recipients} setRecipients={setRecipients} />
        ) : null}
        {activeRoute === "uploads" ? <UploadsScreen uploads={uploads} setUploads={setUploads} /> : null}
        {activeRoute === "social-services" ? <SocialServicesScreen profile={profile} /> : null}
        {activeRoute === "shelter" ? (
          <ShelterScreen
            activeStaffSession={activeStaffSession}
            checklist={shelterChecklist}
            setChecklist={setShelterChecklist}
            shelterPinConfigs={shelterPinConfigs}
            setShelterPinConfigs={setShelterPinConfigs}
            shelterAuditEvents={shelterAuditEvents}
            setShelterAuditEvents={setShelterAuditEvents}
            shelterStaffAccounts={shelterStaffAccounts}
            setShelterStaffAccounts={setShelterStaffAccounts}
            shelterUserAccounts={shelterUserAccounts}
            setShelterUserAccounts={setShelterUserAccounts}
            setActiveStaffSessionId={setActiveStaffSessionId}
          />
        ) : null}
        {activeRoute === "recipient-access" ? (
          <RecipientAccessScreen
            accessRequests={accessRequests}
            recipients={recipients}
            setAccessRequests={setAccessRequests}
            verified={recipientVerified}
            setVerified={setRecipientVerified}
          />
        ) : null}
        {activeRoute === "benefits-protection" ? (
          <BenefitsProtectionScreen
            history={benefitsConsentHistory}
            optedIn={benefitsOptIn}
            setHistory={setBenefitsConsentHistory}
            setOptedIn={setBenefitsOptIn}
          />
        ) : null}
        {activeRoute === "analytics" ? (
          <AnalyticsScreen optedIn={analyticsOptIn} setOptedIn={setAnalyticsOptIn} />
        ) : null}
        {activeRoute === "security" ? (
          <SecurityScreen securitySettings={securitySettings} setSecuritySettings={setSecuritySettings} />
        ) : null}
        {activeRoute === "audit" ? <AuditScreen /> : null}
      </main>
    </div>
  );
}

function NavButton({
  active,
  icon: Icon,
  label,
  onClick
}: {
  active: boolean;
  icon: typeof Home;
  label: string;
  onClick: () => void;
}) {
  return (
    <button aria-current={active ? "page" : undefined} className="nav-button" onClick={onClick} type="button">
      <Icon aria-hidden="true" size={19} />
      <span>{label}</span>
    </button>
  );
}

function HomeScreen({
  navigate,
  nextCheckIn,
  recipients,
  uploads
}: {
  navigate: (route: RouteId) => void;
  nextCheckIn: string;
  recipients: DisclosureRecipientDraft[];
  uploads: UploadItem[];
}) {
  const recipientsWithScopes = recipients.filter((recipient) => getEffectiveSharingScopes(recipient).length > 0).length;
  const sharingSummary = recipients.length
    ? `${recipientsWithScopes} of ${recipients.length} recipients have scopes`
    : "No recipients yet";

  return (
    <div className="screen home-screen">
      <div className="page-title">
        <p className="eyebrow">Today</p>
        <h1>Your safety plan</h1>
      </div>
      <Section title="Dashboard overview">
        <div className="dashboard-grid">
          <StatusPanel label="Check-in" onClick={() => navigate("check-in")} tone="teal" value={nextCheckIn} />
          <StatusPanel label="Contacts" onClick={() => navigate("contacts")} tone="gold" value={`${recipients.length} saved`} />
          <StatusPanel label="Services" onClick={() => navigate("social-services")} tone="red" value="Guided matching" />
          <StatusPanel label="Sharing" onClick={() => navigate("sharing-rules")} tone="teal" value={sharingSummary} />
        </div>
      </Section>
      <div className="home-actions" aria-label="Primary actions">
        <ActionCard
          detail={`${recipients.length} recipients configured`}
          icon={<ContactRound aria-hidden="true" size={28} />}
          onClick={() => navigate("contacts")}
          title="Emergency contacts"
        />
        <ActionCard
          detail="Find shelter, food, benefits, health, and legal help"
          icon={<HeartHandshake aria-hidden="true" size={28} />}
          onClick={() => navigate("social-services")}
          title="Social services"
        />
      </div>
      <Section title="Quick actions">
        <div className="quick-actions">
          <button className="checkin-panel" onClick={() => navigate("check-in")} type="button">
            <div className="checkin-panel-icon"><CalendarCheck size={24} aria-hidden="true" /></div>
            <div className="checkin-panel-text">
              <span className="checkin-panel-label">Next check-in</span>
              <span className="checkin-panel-value">{nextCheckIn}</span>
            </div>
            <span className="checkin-panel-cta">Check in now</span>
          </button>
        </div>
      </Section>
      <div className="home-footer">
        <div className="home-footer-stat">
          <small>Stored uploads</small>
          <span>{uploads.length} file{uploads.length !== 1 ? "s" : ""}</span>
        </div>
        <div className="home-footer-divider" />
        <div className="home-footer-stat">
          <small>Sharing rules</small>
          <span>{sharingSummary}</span>
          <a
            className="home-footer-link"
            href="#/sharing-rules"
            onClick={(event) => {
              event.preventDefault();
              navigate("sharing-rules");
            }}
          >
            Open sharing rules
          </a>
        </div>
      </div>
    </div>
  );
}

function StatusPanel({ label, value, tone, onClick }: { label: string; value: string; tone: string; onClick?: () => void }) {
  return (
    <div
      className={`status-panel panel-${tone}${onClick ? " status-panel-clickable" : ""}`}
      onClick={onClick}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={
        onClick
          ? (event) => {
              if (event.key !== "Enter" && event.key !== " ") return;
              event.preventDefault();
              onClick();
            }
          : undefined
      }
    >
      <small>{label}</small>
      <strong>{value}</strong>
    </div>
  );
}

function RegistrationScreen({
  profile,
  registrationStaffDraft,
  setRegistrationStaffDraft,
  setProfile,
  shelterPinConfigs,
  shelterStaffAccounts,
  setShelterStaffAccounts,
  setActiveStaffSessionId,
  setShelterAuditEvents
}: {
  profile: RegistrationProfileDraft;
  registrationStaffDraft: typeof defaultRegistrationStaffDraft;
  setRegistrationStaffDraft: (draft: typeof defaultRegistrationStaffDraft) => void;
  setProfile: (profile: RegistrationProfileDraft) => void;
  shelterPinConfigs: ShelterPinConfig[];
  shelterStaffAccounts: ShelterStaffAccount[];
  setShelterStaffAccounts: (accounts: ShelterStaffAccount[]) => void;
  setActiveStaffSessionId: (id: string) => void;
  setShelterAuditEvents: StateSetter<ShelterAuditEvent[]>;
}) {
  const [photoPreviewUrl, setPhotoPreviewUrl] = useState("");
  const [photoPreviewLabel, setPhotoPreviewLabel] = useState("");
  const [showPhotoPreview, setShowPhotoPreview] = useState(false);
  const [shelterPin, setShelterPin] = useState("");
  const [profileDraftSaved, setProfileDraftSaved] = useState(false);
  const [staffVerificationState, setStaffVerificationState] = useState<
    "idle" | "missing_shelter" | "missing_pin" | "wrong_pin" | "verified_staff" | "revoked"
  >("idle");
  const { currentStaffAccountId, isShelterStaff, selectedShelter } = registrationStaffDraft;

  const update = (patch: Partial<RegistrationProfileDraft>) => {
    setProfile({ ...profile, ...patch });
    setProfileDraftSaved(false);
  };
  const updateStaffDraft = (patch: Partial<typeof defaultRegistrationStaffDraft>) =>
    setRegistrationStaffDraft({ ...registrationStaffDraft, ...patch });

  const currentStaffAccount = shelterStaffAccounts.find((account) => account.id === currentStaffAccountId);
  const staffVerified = Boolean(currentStaffAccount?.verified);
  const profileReady = Boolean(
    profile.legalName.trim() &&
      profile.dateOfBirth &&
      profile.photoAssetId &&
      isBotCheckReady(profile.easyBotCheckStatus, profile.captchaToken)
  );

  async function handleProfileUploadChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];

    if (!file) {
      update({ photoAssetId: "" });
      setPhotoPreviewUrl("");
      setPhotoPreviewLabel("");
      setShowPhotoPreview(false);
      return;
    }

    if (!isAcceptedProfilePhoto(file)) {
      update({ photoAssetId: "" });
      event.currentTarget.value = "";
      setPhotoPreviewUrl("");
      setPhotoPreviewLabel("Use JPEG, PNG, or WebP for profile photos. Upload PDFs in the document vault.");
      setShowPhotoPreview(false);
      return;
    }

    update({ photoAssetId: file.name });
    setShowPhotoPreview(false);

    try {
      const fileReader = new FileReader();
      fileReader.onload = () => {
        setPhotoPreviewUrl(String(fileReader.result || ""));
        setPhotoPreviewLabel("Selected image preview");
      };
      fileReader.readAsDataURL(file);
      return;
    } catch {
      setPhotoPreviewUrl("");
      setPhotoPreviewLabel("Preview unavailable for this file.");
      return;
    }
  }

  function toggleNeed(need: string) {
    update({
      serviceNeeds: profile.serviceNeeds.includes(need)
        ? profile.serviceNeeds.filter((item) => item !== need)
        : [...profile.serviceNeeds, need]
    });
  }

  return (
    <div className="screen">
      <div className="page-title">
        <p className="eyebrow">Registration</p>
        <h1>Create your Abby profile</h1>
      </div>
      <StatusBanner tone="info">Only name, birth date, photo, and bot check are required to start.</StatusBanner>
      <form className="form-grid" onSubmit={(event) => event.preventDefault()}>
        <fieldset className="identity-fieldset full-span">
          <legend>Identity details</legend>
          <div className="identity-fields">
            <Field help="Used for emergency identity matching." label="Legal or full name" required>
              <input value={profile.legalName} onChange={(event) => update({ legalName: event.target.value })} />
            </Field>
            <Field help="Shown in the app when provided." label="Preferred name">
              <input value={profile.preferredName} onChange={(event) => update({ preferredName: event.target.value })} />
            </Field>
            <Field help="e.g. she/her, he/him, they/them - optional and not shared without permission." label="Pronouns">
              <input value={profile.pronouns} onChange={(event) => update({ pronouns: event.target.value })} />
            </Field>
            <Field help="Required to distinguish people with similar names." label="Birth date" required>
              <input
                type="date"
                value={profile.dateOfBirth}
                onChange={(event) => update({ dateOfBirth: event.target.value })}
              />
            </Field>
            <Field help={PROFILE_PHOTO_HELP} label="Photo or photo ID" required>
              <input
                accept={PROFILE_PHOTO_ACCEPT_ATTR}
                capture="user"
                type="file"
                onChange={handleProfileUploadChange}
              />
              {photoPreviewUrl ? (
                <div className="photo-preview-toggle">
                  <button className="preview-toggle-button" onClick={() => setShowPhotoPreview(!showPhotoPreview)} type="button">
                    {showPhotoPreview ? "Hide preview" : "See preview"}
                  </button>
                  {showPhotoPreview ? (
                    <div className="photo-preview-card">
                      <small>{photoPreviewLabel}</small>
                      <img alt="Profile upload preview" src={photoPreviewUrl} />
                    </div>
                  ) : null}
                </div>
              ) : photoPreviewLabel ? (
                <small>{photoPreviewLabel}</small>
              ) : null}
            </Field>
          </div>
        </fieldset>
        <Field help="Used for text reminders if enabled." label="Phone">
          <input value={profile.phone} onChange={(event) => update({ phone: event.target.value })} />
        </Field>
        <Field help="Used for email reminders if enabled." label="Email">
          <input type="email" value={profile.email} onChange={(event) => update({ email: event.target.value })} />
        </Field>
        <Field help="Can be a neighborhood, shelter, or general area." label="Current safe location">
          <input value={profile.currentLocation} onChange={(event) => update({ currentLocation: event.target.value })} />
        </Field>
        <Field help="Optional; useful for assisted setup." label="Preferred shelter">
          <input
            value={profile.preferredShelter}
            onChange={(event) => update({ preferredShelter: event.target.value })}
          />
        </Field>
        <Field help="Optional; helps Abby suggest who to contact only if you choose to share it." label="Social worker">
          <input value={profile.socialWorker} onChange={(event) => update({ socialWorker: event.target.value })} />
        </Field>
        <Field help="Optional starter info for your first emergency contact; you can refine it later." label="Emergency contact starter">
          <input
            value={profile.emergencyContactStarter}
            onChange={(event) => update({ emergencyContactStarter: event.target.value })}
          />
        </Field>
        <div className="full-span">
          <span className="field-label">Service needs</span>
          <small className="field-help">
            Optional categories used only for services and matching screens after you consent.
          </small>
          <div className="chip-grid">
            {serviceNeeds.map((need) => (
              <button
                aria-pressed={profile.serviceNeeds.includes(need)}
                className="choice-chip"
                key={need}
                onClick={() => toggleNeed(need)}
                type="button"
              >
                {need}
              </button>
            ))}
          </div>
        </div>
        <label className="captcha-box full-span">
          <input
            aria-required="true"
            checked={profile.easyBotCheckStatus === "passed"}
            onChange={(event) =>
              update({ easyBotCheckStatus: event.target.checked ? "passed" : "failed", captchaToken: "" })
            }
            type="checkbox"
          />
          <span>
            Quick health check complete (step 1)
            <RequiredMarker />
          </span>
        </label>
        <div className="full-span">
          <Button onClick={() => update({ easyBotCheckStatus: "failed", captchaToken: "" })} variant="secondary">
            Mark health check follow-up
          </Button>
        </div>
        <label className="captcha-box full-span">
          <input
            aria-required="true"
            checked={Boolean(profile.captchaToken)}
            disabled={profile.easyBotCheckStatus === "pending"}
            onChange={(event) => update({ captchaToken: event.target.checked ? "mock-captcha-token" : "" })}
            type="checkbox"
          />
          <span>
            Bot check complete (step 2)
            <RequiredMarker />
          </span>
        </label>
        <div className="full-span">
          <Button disabled={!profileReady} onClick={() => setProfileDraftSaved(true)} type="button">
            <ClipboardCheck size={18} /> Create profile draft
          </Button>
          {profileDraftSaved ? <small className="pin-request-note">Profile draft saved locally on this device.</small> : null}
        </div>
        <label className="consent-box full-span">
          <input
            checked={isShelterStaff}
            onChange={(event) => {
              const checked = event.target.checked;
              updateStaffDraft({ isShelterStaff: checked });
              if (!checked) {
                setShelterPin("");
                setRegistrationStaffDraft(defaultRegistrationStaffDraft);
                setStaffVerificationState("idle");
              }
            }}
            type="checkbox"
          />
          <span>
            <strong>I am shelter staff</strong>
          </span>
        </label>
        {isShelterStaff ? (
          <div className="shelter-staff-panel full-span">
            <Field help="Choose the shelter where you currently work." label="Shelter" required>
              <select
                value={selectedShelter}
                onChange={(event) => {
                  updateStaffDraft({ selectedShelter: event.target.value, currentStaffAccountId: "" });
                  setStaffVerificationState("idle");
                }}
              >
                <option value="">Select shelter</option>
                {shelterOptions.map((shelter) => (
                  <option key={shelter} value={shelter}>
                    {shelter}
                  </option>
                ))}
              </select>
            </Field>
            <Field help="Enter your assigned shelter staff PIN to verify this account." label="Shelter staff PIN" required>
              <input
                inputMode="numeric"
                maxLength={4}
                placeholder="Enter PIN"
                type="password"
                value={shelterPin}
                onChange={(event) => {
                  setShelterPin(event.target.value.replace(/\D/g, "").slice(0, 4));
                  setStaffVerificationState("idle");
                }}
              />
            </Field>
            <div>
              <Button
                onClick={() => {
                  if (!selectedShelter) {
                    setStaffVerificationState("missing_shelter");
                    return;
                  }

                  if (!shelterPin.trim()) {
                    setStaffVerificationState("missing_pin");
                    return;
                  }

                  const pinConfig = getShelterPinConfig(shelterPinConfigs, selectedShelter);
                  if (shelterPin !== pinConfig.staffPin) {
                    setStaffVerificationState("wrong_pin");
                    updateStaffDraft({ currentStaffAccountId: "" });
                    return;
                  }

                  const displayName = profile.preferredName || profile.legalName || "Shelter staff";
                  const emailKey = profile.email.trim().toLowerCase();
                  const existingAccount = shelterStaffAccounts.find(
                    (account) =>
                      account.shelter === selectedShelter &&
                      ((emailKey && account.email.toLowerCase() === emailKey) ||
                        (!emailKey && account.displayName.toLowerCase() === displayName.toLowerCase()))
                  );

                  if (existingAccount) {
                    const updated = shelterStaffAccounts.map((account) =>
                      account.id === existingAccount.id
                        ? {
                            ...account,
                            displayName,
                            email: profile.email,
                            verified: true,
                            updatedAt: new Date().toISOString()
                          }
                        : account
                    );
                    setShelterStaffAccounts(updated);
                    updateStaffDraft({ currentStaffAccountId: existingAccount.id });
                    setActiveStaffSessionId(existingAccount.id);
                    setStaffVerificationState("verified_staff");
                    setShelterAuditEvents((events) => [
                      createShelterAuditEvent(selectedShelter, displayName, "verified_staff"),
                      ...events
                    ]);
                    return;
                  }

                  const createdAccount: ShelterStaffAccount = {
                    id: `staff-${Date.now()}`,
                    shelter: selectedShelter,
                    displayName,
                    email: profile.email,
                    verified: true,
                    updatedAt: new Date().toISOString()
                  };
                  setShelterStaffAccounts([...shelterStaffAccounts, createdAccount]);
                  updateStaffDraft({ currentStaffAccountId: createdAccount.id });
                  setActiveStaffSessionId(createdAccount.id);
                  setStaffVerificationState("verified_staff");
                  setShelterAuditEvents((events) => [
                    createShelterAuditEvent(selectedShelter, displayName, "verified_staff"),
                    ...events
                  ]);
                }}
                type="button"
              >
                Verify shelter staff
              </Button>
              {staffVerificationState === "missing_shelter" ? (
                <small className="pin-error-note">missing_shelter: choose a shelter before verifying.</small>
              ) : null}
              {staffVerificationState === "missing_pin" ? (
                <small className="pin-error-note">missing_pin: enter the shelter staff PIN.</small>
              ) : null}
              {staffVerificationState === "wrong_pin" ? (
                <small className="pin-error-note">wrong_pin: that PIN does not match this shelter.</small>
              ) : null}
              {staffVerified && staffVerificationState === "verified_staff" ? (
                <small className="pin-request-note">verified_staff: Shelter portal is now available.</small>
              ) : null}
              {!staffVerified && currentStaffAccountId ? (
                <small className="pin-error-note">revoked: verification was revoked by shelter administrator.</small>
              ) : null}
              <small className="pin-request-note">
                Demo PIN validation happens in browser state for this prototype; production verification must move
                server-side.
              </small>
            </div>
          </div>
        ) : null}
      </form>
    </div>
  );
}

function CheckInScreen({
  policy,
  setPolicy,
  nextCheckIn
}: {
  policy: typeof defaultCheckInPolicy;
  setPolicy: (policy: typeof defaultCheckInPolicy) => void;
  nextCheckIn: string;
}) {
  const update = (patch: Partial<typeof defaultCheckInPolicy>) => setPolicy({ ...policy, ...patch });
  const toggleChannel = (channel: CheckInChannel) => {
    update({
      reminderChannels: policy.reminderChannels.includes(channel)
        ? policy.reminderChannels.filter((item) => item !== channel)
        : [...policy.reminderChannels, channel]
    });
  };

  return (
    <div className="screen">
      <div className="page-title">
        <p className="eyebrow">Check-in</p>
        <h1>Set your schedule</h1>
      </div>
      <StatusBanner tone="warning">The maximum interval is 30 days before escalation.</StatusBanner>
      <Section title="Reminder schedule">
        <div>
          <span className="field-label">Safe interval presets</span>
          <div className="chip-grid">
            {checkInIntervalPresets.map((days) => (
              <button
                aria-pressed={policy.intervalDays === days}
                className="choice-chip"
                key={days}
                onClick={() => update({ intervalDays: days })}
                type="button"
              >
                {days} day{days !== 1 ? "s" : ""}
              </button>
            ))}
          </div>
        </div>
        <div className="form-grid">
          <Field help="Choose 1 to 30 days, or use a preset above." label="Custom interval days" required>
            <input
              aria-label="Interval days"
              max={30}
              min={1}
              type="number"
              value={policy.intervalDays}
              onChange={(event) =>
                update({ intervalDays: Math.max(1, Math.min(30, Number(event.target.value || 1))) })
              }
            />
          </Field>
          <Field help="Time after a missed check-in before escalation starts." label="Grace period hours">
            <input
              min={0}
              type="number"
              value={policy.gracePeriodHours}
              onChange={(event) => update({ gracePeriodHours: Number(event.target.value || 0) })}
            />
          </Field>
        </div>
        <StatusBanner tone="info">
          If a check-in is missed, Abby keeps reminders active for {policy.gracePeriodHours} hour
          {policy.gracePeriodHours === 1 ? "" : "s"} before starting the emergency disclosure review.
        </StatusBanner>
        <div className="chip-grid">
          {(["sms", "email", "web"] as CheckInChannel[]).map((channel) => (
            <button
              aria-pressed={policy.reminderChannels.includes(channel)}
              className="choice-chip"
              key={channel}
              onClick={() => toggleChannel(channel)}
              type="button"
            >
              {channel.toUpperCase()}
            </button>
          ))}
        </div>
        <div className="schedule-preview">
          <button className="checkin-panel" onClick={() => update({ lastCheckInAt: new Date().toISOString() })} type="button">
            <div className="checkin-panel-icon">
              <CalendarCheck aria-hidden="true" size={24} />
            </div>
            <div className="checkin-panel-text">
              <span className="checkin-panel-label">Next check-in</span>
              <span className="checkin-panel-value">{nextCheckIn}</span>
            </div>
            <span className="checkin-panel-cta">Check in now</span>
          </button>
        </div>
      </Section>
    </div>
  );
}

function ContactsScreen({
  navigate,
  recipients,
  setRecipients
}: {
  navigate: (route: RouteId) => void;
  recipients: DisclosureRecipientDraft[];
  setRecipients: (recipients: DisclosureRecipientDraft[]) => void;
}) {
  const [editingRecipientId, setEditingRecipientId] = useState("");
  const [pendingRemovalId, setPendingRemovalId] = useState("");
  const [draft, setDraft] = useState({
    displayName: "",
    relationship: "",
    email: "",
    phone: "",
    type: "emergency_contact" as DisclosureRecipientType,
    agencyName: "",
    precinctName: ""
  });

  function addRecipient(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const displayName = draft.displayName.trim();
    if (!displayName) return;

    const relationship = draft.relationship.trim();
    const email = draft.email.trim();
    const phone = draft.phone.trim();
    const agencyName = draft.agencyName.trim();
    const precinctName = draft.precinctName.trim();

    if (editingRecipientId) {
      setRecipients(
        recipients.map((recipient) =>
          recipient.id === editingRecipientId
            ? (() => {
                const emailStatus = getNextContactMethodStatus(
                  email,
                  recipient.emailVerificationStatus,
                  recipient.email.trim().toLowerCase() !== email.toLowerCase()
                );
                const phoneStatus = getNextContactMethodStatus(
                  phone,
                  recipient.phoneVerificationStatus,
                  recipient.phone.trim() !== phone
                );
                const presentMethodStatuses = [emailStatus, phoneStatus].filter((status) => status !== "missing");
                return {
                  ...recipient,
                  displayName,
                  relationship,
                  email,
                  phone,
                  type: draft.type,
                  agencyName,
                  precinctName,
                  emailVerificationStatus: emailStatus,
                  phoneVerificationStatus: phoneStatus,
                  verified:
                    presentMethodStatuses.length > 0 &&
                    presentMethodStatuses.every((status) => status === "verified")
                };
              })()
            : recipient
        )
      );
      setEditingRecipientId("");
    } else {
      const emailStatus = getContactMethodStatus(email, undefined);
      const phoneStatus = getContactMethodStatus(phone, undefined);
      setRecipients([
        ...recipients,
        {
          id: `rec-${Date.now()}`,
          displayName,
          relationship,
          email,
          phone,
          type: draft.type,
          agencyName,
          precinctName,
          verified: false,
          emailVerificationStatus: emailStatus,
          phoneVerificationStatus: phoneStatus,
          allowedScopes: [...DEFAULT_SHARING_SCOPES],
          sharingRuleCustomized: false,
          emergencyDisclosureEnabled: false,
          sharingHistory: [createRecipientHistoryEntry("Recipient added; disclosure review required")]
        }
      ]);
    }
    setPendingRemovalId("");
    setDraft({
      displayName: "",
      relationship: "",
      email: "",
      phone: "",
      type: "emergency_contact",
      agencyName: "",
      precinctName: ""
    });
  }

  function editRecipient(recipient: DisclosureRecipientDraft) {
    setEditingRecipientId(recipient.id);
    setPendingRemovalId("");
    setDraft({
      displayName: recipient.displayName,
      relationship: recipient.relationship,
      email: recipient.email,
      phone: recipient.phone,
      type: recipient.type,
      agencyName: recipient.agencyName,
      precinctName: recipient.precinctName
    });
  }

  function clearRecipientDraft() {
    setEditingRecipientId("");
    setPendingRemovalId("");
    setDraft({
      displayName: "",
      relationship: "",
      email: "",
      phone: "",
      type: "emergency_contact",
      agencyName: "",
      precinctName: ""
    });
  }

  function verifyContactMethod(recipientId: string, method: "phone" | "email") {
    setPendingRemovalId("");
    setRecipients(
      recipients.map((recipient) =>
        recipient.id === recipientId
          ? (() => {
              const emailStatus =
                method === "email"
                  ? getContactMethodStatus(recipient.email, "verified")
                  : getContactMethodStatus(recipient.email, recipient.emailVerificationStatus, recipient.verified);
              const phoneStatus =
                method === "phone"
                  ? getContactMethodStatus(recipient.phone, "verified")
                  : getContactMethodStatus(recipient.phone, recipient.phoneVerificationStatus, recipient.verified);
              const presentMethodStatuses = [emailStatus, phoneStatus].filter((status) => status !== "missing");
              return {
                ...recipient,
                emailVerificationStatus: emailStatus,
                phoneVerificationStatus: phoneStatus,
                verified:
                  presentMethodStatuses.length > 0 &&
                  presentMethodStatuses.every((status) => status === "verified"),
                sharingHistory: [
                  createRecipientHistoryEntry(`${method === "phone" ? "Phone" : "Email"} verified`),
                  ...(recipient.sharingHistory ?? [])
                ]
              };
            })()
          : recipient
      )
    );
  }

  function moveRecipient(recipientId: string, direction: -1 | 1) {
    const currentIndex = recipients.findIndex((recipient) => recipient.id === recipientId);
    const targetIndex = currentIndex + direction;
    if (currentIndex < 0 || targetIndex < 0 || targetIndex >= recipients.length) return;
    const nextRecipients = [...recipients];
    const [recipient] = nextRecipients.splice(currentIndex, 1);
    nextRecipients.splice(targetIndex, 0, recipient);
    setPendingRemovalId("");
    setRecipients(nextRecipients);
  }

  function removeRecipient(recipient: DisclosureRecipientDraft) {
    const activeRecipients = recipients.filter((item) => !item.revokedAt);
    if (!recipient.revokedAt && activeRecipients.length <= 1 && pendingRemovalId !== recipient.id) {
      setPendingRemovalId(recipient.id);
      return;
    }

    setPendingRemovalId("");
    setRecipients(recipients.filter((item) => item.id !== recipient.id));
  }

  return (
    <div className="screen">
      <div className="page-title">
        <p className="eyebrow">Emergency contacts</p>
        <h1>People and services</h1>
      </div>
      <Section title="Add recipient">
        <form className="form-grid" onSubmit={addRecipient}>
          <Field label="Name or agency" required>
            <input value={draft.displayName} onChange={(event) => setDraft({ ...draft, displayName: event.target.value })} />
          </Field>
          <Field label="Relationship or role">
            <input value={draft.relationship} onChange={(event) => setDraft({ ...draft, relationship: event.target.value })} />
          </Field>
          <Field label="Phone">
            <input value={draft.phone} onChange={(event) => setDraft({ ...draft, phone: event.target.value })} />
          </Field>
          <Field label="Email">
            <input type="email" value={draft.email} onChange={(event) => setDraft({ ...draft, email: event.target.value })} />
          </Field>
          <Field label="Type">
            <select
              value={draft.type}
              onChange={(event) => setDraft({ ...draft, type: event.target.value as DisclosureRecipientType })}
            >
              <option value="emergency_contact">Emergency contact</option>
              <option value="social_worker">Social worker</option>
              <option value="police_precinct">Police precinct</option>
              <option value="shelter_staff">Shelter staff</option>
              <option value="government_liaison">Government liaison</option>
              <option value="benefits_agency">Benefits agency</option>
            </select>
          </Field>
          {draft.type === "police_precinct" ? (
            <Field help="Optional; useful when the recipient is a local precinct." label="Precinct name">
              <input
                value={draft.precinctName}
                onChange={(event) => setDraft({ ...draft, precinctName: event.target.value })}
              />
            </Field>
          ) : null}
          {draft.type !== "emergency_contact" && draft.type !== "police_precinct" ? (
            <Field help="Optional service, shelter, or agency name." label="Agency or service">
              <input
                value={draft.agencyName}
                onChange={(event) => setDraft({ ...draft, agencyName: event.target.value })}
              />
            </Field>
          ) : null}
          <div className="full-span">
            <Button type="submit">
              <UsersRound size={18} /> {editingRecipientId ? "Save recipient" : "Add recipient"}
            </Button>
            {editingRecipientId ? (
              <Button onClick={clearRecipientDraft} type="button" variant="quiet">
                Cancel edit
              </Button>
            ) : null}
          </div>
        </form>
      </Section>
      <div className="list-stack">
        {recipients.map((recipient, index) => {
          const phoneStatus = getContactMethodStatus(
            recipient.phone,
            recipient.phoneVerificationStatus,
            recipient.verified
          );
          const emailStatus = getContactMethodStatus(
            recipient.email,
            recipient.emailVerificationStatus,
            recipient.verified
          );
          const scopeCount = getEffectiveSharingScopes(recipient).length;
          const pendingLastActiveRemoval = pendingRemovalId === recipient.id;

          return (
            <article className="list-item recipient-list-item" key={recipient.id}>
              <div className="recipient-summary">
                <div>
                  <h3>{recipient.displayName}</h3>
                  <p>
                    {recipient.relationship ||
                      recipient.precinctName ||
                      recipient.agencyName ||
                      getRecipientTypeLabel(recipient.type)}
                  </p>
                </div>
                <div className="recipient-details">
                  <span>{getRecipientTypeLabel(recipient.type)}</span>
                  {recipient.agencyName ? <span>{recipient.agencyName}</span> : null}
                  {recipient.precinctName ? <span>{recipient.precinctName}</span> : null}
                  {recipient.phone ? <span>{recipient.phone}</span> : null}
                  {recipient.email ? <span>{recipient.email}</span> : null}
                </div>
                <div className="badge-row">
                  <Badge tone={recipient.verified ? "success" : "warning"}>
                    {recipient.verified ? "Recipient verified" : "Needs method verification"}
                  </Badge>
                  <Badge tone={recipient.emergencyDisclosureEnabled ? "success" : recipient.revokedAt ? "warning" : "neutral"}>
                    {getRecipientAccessStatus(recipient)}
                  </Badge>
                  <Badge>{scopeCount === 1 ? "1 scope" : `${scopeCount} scopes`}</Badge>
                  <Badge tone={getContactMethodTone(phoneStatus)}>
                    {getContactMethodLabel("phone", phoneStatus)}
                  </Badge>
                  <Badge tone={getContactMethodTone(emailStatus)}>
                    {getContactMethodLabel("email", emailStatus)}
                  </Badge>
                </div>
                <small className="scope-summary">Can access: {getRecipientScopeSummary(recipient)}</small>
                {pendingLastActiveRemoval ? (
                  <div className="inline-warning" role="status">
                    Removing this person leaves no active emergency recipient. Press confirm remove to continue.
                  </div>
                ) : null}
              </div>
              <div className="row-actions">
                <Button
                  ariaLabel={`Move ${recipient.displayName} up`}
                  className="compact-list-action"
                  disabled={index === 0}
                  onClick={() => moveRecipient(recipient.id, -1)}
                  variant="quiet"
                >
                  <ArrowUp aria-hidden="true" size={16} /> Up
                </Button>
                <Button
                  ariaLabel={`Move ${recipient.displayName} down`}
                  className="compact-list-action"
                  disabled={index === recipients.length - 1}
                  onClick={() => moveRecipient(recipient.id, 1)}
                  variant="quiet"
                >
                  <ArrowDown aria-hidden="true" size={16} /> Down
                </Button>
                {phoneStatus === "unverified" ? (
                  <Button
                    ariaLabel={`Verify phone for ${recipient.displayName}`}
                    className="compact-list-action"
                    onClick={() => verifyContactMethod(recipient.id, "phone")}
                    variant="quiet"
                  >
                    Verify phone
                  </Button>
                ) : null}
                {emailStatus === "unverified" ? (
                  <Button
                    ariaLabel={`Verify email for ${recipient.displayName}`}
                    className="compact-list-action"
                    onClick={() => verifyContactMethod(recipient.id, "email")}
                    variant="quiet"
                  >
                    Verify email
                  </Button>
                ) : null}
                <Button
                  ariaLabel={`Edit ${recipient.displayName}`}
                  className="compact-list-action"
                  onClick={() => editRecipient(recipient)}
                  variant="quiet"
                >
                  Edit
                </Button>
                <Button
                  ariaLabel={`Review scopes for ${recipient.displayName}`}
                  className="compact-list-action"
                  onClick={() => navigate("sharing-rules")}
                  variant="quiet"
                >
                  Review scopes
                </Button>
                <Button
                  ariaLabel={
                    pendingLastActiveRemoval
                      ? `Confirm remove ${recipient.displayName}`
                      : `Remove ${recipient.displayName}`
                  }
                  className="compact-list-action"
                  onClick={() => removeRecipient(recipient)}
                  variant="quiet"
                >
                  {pendingLastActiveRemoval ? "Confirm remove" : "Remove"}
                </Button>
              </div>
            </article>
          );
        })}
      </div>
    </div>
  );
}

function SharingRulesScreen({
  recipients,
  setRecipients
}: {
  recipients: DisclosureRecipientDraft[];
  setRecipients: (recipients: DisclosureRecipientDraft[]) => void;
}) {
  function toggleScope(recipientId: string, scope: DisclosureDataScope) {
    setRecipients(
      recipients.map((recipient) =>
        recipient.id === recipientId
          ? (() => {
              const currentScopes = getEffectiveSharingScopes(recipient);
              const nextScopes = currentScopes.includes(scope)
                ? currentScopes.filter((item) => item !== scope)
                : [...currentScopes, scope];
              return {
                ...recipient,
                allowedScopes: nextScopes,
                sharingRuleCustomized: true,
                emergencyDisclosureEnabled: false,
                revokedAt: undefined,
                sharingHistory: [
                  createRecipientHistoryEntry("Scopes changed; emergency disclosure needs review"),
                  ...(recipient.sharingHistory ?? [])
                ]
              };
            })()
          : recipient
      )
    );
  }

  function confirmDisclosure(recipientId: string) {
    setRecipients(
      recipients.map((recipient) =>
        recipient.id === recipientId
          ? {
              ...recipient,
              emergencyDisclosureEnabled: true,
              revokedAt: undefined,
              sharingReviewConfirmedAt: new Date().toISOString(),
              sharingHistory: [
                createRecipientHistoryEntry("Emergency disclosure confirmed"),
                ...(recipient.sharingHistory ?? [])
              ]
            }
          : recipient
      )
    );
  }

  function revokeDisclosure(recipientId: string) {
    setRecipients(
      recipients.map((recipient) =>
        recipient.id === recipientId
          ? {
              ...recipient,
              emergencyDisclosureEnabled: false,
              revokedAt: new Date().toISOString(),
              sharingHistory: [createRecipientHistoryEntry("Emergency disclosure revoked"), ...(recipient.sharingHistory ?? [])]
            }
          : recipient
      )
    );
  }

  return (
    <div className="screen">
      <div className="page-title">
        <p className="eyebrow">Sharing rules</p>
        <h1>Choose what each person can see</h1>
      </div>
      <StatusBanner tone="info">
        Minimum identity and Photo are preselected for recipients without a saved custom choice. You can remove them
        before disclosure. Changes auto-save locally in this prototype.
      </StatusBanner>
      <div className="list-stack">
        {recipients.map((recipient) => {
          const effectiveScopes = getEffectiveSharingScopes(recipient);
          return (
            <article className="scope-editor" key={recipient.id}>
              <div className="scope-header">
                <div>
                  <h3>{recipient.displayName}</h3>
                  <p>{getRecipientTypeLabel(recipient.type)}</p>
                </div>
                <div className="badge-row">
                  <Badge>{effectiveScopes.length} selected</Badge>
                  <Badge tone={recipient.emergencyDisclosureEnabled ? "success" : recipient.revokedAt ? "warning" : "neutral"}>
                    {getRecipientAccessStatus(recipient)}
                  </Badge>
                </div>
              </div>
              <div className="scope-grid">
                {disclosureScopes.map((scope) => (
                  <label className="scope-option" key={scope.id}>
                    <input
                      checked={effectiveScopes.includes(scope.id)}
                      onChange={() => toggleScope(recipient.id, scope.id)}
                      type="checkbox"
                    />
                    <span>
                      <strong>{scope.label}</strong>
                      <small>{scope.detail}</small>
                    </span>
                  </label>
                ))}
              </div>
              <div className="review-panel">
                <div>
                  <strong>Review before emergency disclosure</strong>
                  <small>
                    Confirm only after checking the recipient, scopes, and the next review reminder. Changes to scopes
                    turn disclosure off until reviewed again.
                  </small>
                  <small>
                    Review reminder:{" "}
                    {recipient.sharingReviewConfirmedAt
                      ? new Date(recipient.sharingReviewConfirmedAt).toLocaleDateString()
                      : "not confirmed yet"}
                  </small>
                </div>
                <div className="row-actions">
                  <Button
                    disabled={!effectiveScopes.length}
                    onClick={() => confirmDisclosure(recipient.id)}
                    type="button"
                    variant="secondary"
                  >
                    Confirm emergency disclosure
                  </Button>
                  <Button
                    disabled={!recipient.emergencyDisclosureEnabled && !recipient.revokedAt}
                    onClick={() => revokeDisclosure(recipient.id)}
                    type="button"
                    variant="danger"
                  >
                    Revoke disclosure
                  </Button>
                </div>
                <div className="history-list">
                  {(recipient.sharingHistory ?? []).slice(0, 3).map((entry) => (
                    <small key={entry}>{entry}</small>
                  ))}
                  {recipient.sharingHistory?.length ? null : <small>No disclosure history yet.</small>}
                </div>
              </div>
            </article>
          );
        })}
      </div>
    </div>
  );
}

function UploadsScreen({
  uploads,
  setUploads
}: {
  uploads: UploadItem[];
  setUploads: StateSetter<UploadItem[]>;
}) {
  const [uploadCategory, setUploadCategory] = useState(uploadCategories[0]);
  const [uploadSensitivity, setUploadSensitivity] = useState<UploadItem["sensitivity"]>("high");

  async function addUpload(file: File | null) {
    if (!file) return;
    const uploadId = `up-${Date.now()}`;
    const pendingUpload: UploadItem = {
      id: uploadId,
      fileName: file.name,
      machineSummary: "Generating title",
      summaryStatus: "generating",
      category: uploadCategory,
      sensitivity: uploadSensitivity,
      status: "encrypting",
      sharingEligible: false
    };
    setUploads((currentUploads) => [...currentUploads, pendingUpload]);

    if (file.size === 0) {
      const fallback = createFallbackUploadSummary(file, "failed");
      setUploads((currentUploads) =>
        currentUploads.map((upload) =>
          upload.id === uploadId
            ? {
                ...upload,
                machineSummary: fallback.title,
                summaryStatus: "failed",
                status: "failed"
              }
            : upload
        )
      );
      return;
    }

    const summary = await createUploadSummary(file);
    setUploads((currentUploads) =>
      currentUploads.map((upload) =>
        upload.id === uploadId
          ? {
              ...upload,
              machineSummary: summary.title,
              summaryStatus: summary.status,
              status: "stored"
            }
          : upload
      )
    );
  }

  function retryUpload(uploadId: string) {
    setUploads((currentUploads) =>
      currentUploads.map((upload) =>
        upload.id === uploadId
          ? {
              ...upload,
              status: "stored",
              summaryStatus: upload.summaryStatus === "failed" ? "fallback" : upload.summaryStatus,
              machineSummary: upload.machineSummary || "Uploaded document"
            }
          : upload
      )
    );
  }

  function removeUpload(uploadId: string) {
    setUploads((currentUploads) => currentUploads.filter((upload) => upload.id !== uploadId));
  }

  return (
    <div className="screen">
      <div className="page-title">
        <p className="eyebrow">Uploads</p>
        <h1>Document and information vault</h1>
      </div>
      <Section title="Add information">
        <div className="upload-controls">
          <Field label="Category">
            <select value={uploadCategory} onChange={(event) => setUploadCategory(event.target.value)}>
              {uploadCategories.map((category) => (
                <option key={category} value={category}>
                  {category}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Sensitivity">
            <select
              value={uploadSensitivity}
              onChange={(event) => setUploadSensitivity(event.target.value as UploadItem["sensitivity"])}
            >
              {uploadSensitivityOptions.map((sensitivity) => (
                <option key={sensitivity} value={sensitivity}>
                  {sensitivity}
                </option>
              ))}
            </select>
          </Field>
        </div>
        <label className="upload-dropzone">
          <Upload aria-hidden="true" size={28} />
          <span>Choose a file or photo</span>
          <small>Stored items stay private until marked sharing-eligible and added to a sharing rule.</small>
          <span className="upload-picker">
            <FileUp aria-hidden="true" size={18} /> Select file
          </span>
          <input
            accept="image/*,application/pdf,text/plain,.txt,.md,.pdf"
            type="file"
            onChange={(event) => addUpload(event.target.files?.[0] ?? null)}
            aria-label="Choose file to upload"
          />
        </label>
        <label className="upload-camera-option">
          <span>
            <strong>Camera upload</strong>
            <small>Use a phone camera for IDs, cards, letters, or receipts.</small>
          </span>
          <input
            accept="image/*"
            capture="environment"
            type="file"
            onChange={(event) => addUpload(event.target.files?.[0] ?? null)}
            aria-label="Take photo to upload"
          />
        </label>
      </Section>
      <div className="list-stack">
        {uploads.length ? (
          uploads.map((upload) => (
          <article className="list-item upload-list-item" key={upload.id}>
            <div>
              <h3>{upload.fileName}</h3>
              <p>{upload.category}</p>
              <small className="upload-machine-summary">
                {upload.summaryStatus === "generating"
                  ? "Generating short title..."
                  : toShortSummaryTitle(upload.machineSummary)}
              </small>
              <div className="badge-row">
                <Badge tone={upload.status === "stored" ? "success" : upload.status === "failed" ? "warning" : "neutral"}>
                  {upload.status}
                </Badge>
                <Badge tone="warning">{upload.sensitivity}</Badge>
                <Badge tone={upload.summaryStatus === "fallback" || upload.summaryStatus === "failed" ? "warning" : "neutral"}>
                  {upload.summaryStatus === "generating"
                    ? "Summarizing"
                    : upload.summaryStatus === "failed"
                      ? "Summary failed"
                      : upload.summaryStatus === "fallback"
                        ? "Filename fallback"
                        : "Generated title"}
                </Badge>
                <Badge tone={upload.sharingEligible ? "success" : "neutral"}>
                  {upload.sharingEligible ? "Sharing eligible" : "Private"}
                </Badge>
              </div>
            </div>
            <div className="row-actions">
              {upload.status === "failed" ? (
                <Button className="list-item-action" onClick={() => retryUpload(upload.id)} variant="secondary">
                  Retry
                </Button>
              ) : null}
              <Button
                className="list-item-action"
                disabled={upload.status === "failed"}
                onClick={() =>
                  setUploads((currentUploads) =>
                    currentUploads.map((item) =>
                      item.id === upload.id ? { ...item, sharingEligible: !item.sharingEligible } : item
                    )
                  )
                }
                variant="secondary"
              >
                {upload.sharingEligible ? "Mark private" : "Mark eligible"}
              </Button>
              <Button className="list-item-action" onClick={() => removeUpload(upload.id)} variant="quiet">
                Remove
              </Button>
            </div>
          </article>
        ))
        ) : (
          <article className="empty-state">
            <h3>No stored items yet</h3>
            <p>Upload documents, photos, notes, or other information when you are ready.</p>
          </article>
        )}
      </div>
    </div>
  );
}

function SocialServicesScreen({ profile }: { profile: RegistrationProfileDraft }) {
  const categories = ["Shelter", "Food", "Health", "Legal", "Benefits", "Transportation", "Employment", "Crisis"];
  const [matchingConsented, setMatchingConsented] = useState(false);
  const [guidedNeed, setGuidedNeed] = useState("");
  const profileNeeds = profile.serviceNeeds.length ? profile.serviceNeeds : [];
  const selectedNeedCategories = matchingConsented ? [...new Set([...profileNeeds, guidedNeed].filter(Boolean))] : [];
  const matchedServices =
    selectedNeedCategories.length > 0
      ? serviceMatches.filter((service) => selectedNeedCategories.includes(service.category))
      : serviceMatches;

  return (
    <div className="screen">
      <div className="page-title">
        <p className="eyebrow">Social services</p>
        <h1>Find support</h1>
      </div>
      <div className="category-grid">
        {categories.map((category) => (
          <button
            aria-pressed={guidedNeed === category}
            className="category-tile"
            key={category}
            onClick={() => setGuidedNeed(guidedNeed === category ? "" : category)}
            type="button"
          >
            <HeartHandshake aria-hidden="true" size={22} />
            <span>{category}</span>
          </button>
        ))}
      </div>
      <Section title="Guided intake">
        <label className="consent-box">
          <input checked={matchingConsented} onChange={(event) => setMatchingConsented(event.target.checked)} type="checkbox" />
          <span>
            <strong>Use my selected service needs for 211-style matching.</strong>
            <small>
              Abby uses only consented categories and coarse profile context here, not raw documents or hidden notes.
            </small>
          </span>
        </label>
        <div className="guided-intake-panel">
          <strong>Not sure where to start?</strong>
          <small>Choose the closest category above. The matched list updates after you allow category-based matching.</small>
          <div className="badge-row">
            {selectedNeedCategories.length ? (
              selectedNeedCategories.map((need) => <Badge key={need}>{need}</Badge>)
            ) : (
              <Badge>No matching consent yet</Badge>
            )}
          </div>
        </div>
      </Section>
      <Section title="Government services liaison">
        <div className="liaison-panel">
          <MessageSquare aria-hidden="true" size={28} />
          <div>
            <h3>Request help navigating benefits, IDs, housing, or agency paperwork.</h3>
            <p>Only the details you choose to share will be included in the request.</p>
          </div>
          <Button>Start request</Button>
        </div>
      </Section>
      <Section title="Matched services">
        <div className="list-stack">
          {matchedServices.map((service) => (
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

function ShelterScreen({
  activeStaffSession,
  checklist,
  setChecklist,
  shelterPinConfigs,
  setShelterPinConfigs,
  shelterAuditEvents,
  setShelterAuditEvents,
  shelterStaffAccounts,
  setShelterStaffAccounts,
  shelterUserAccounts,
  setShelterUserAccounts,
  setActiveStaffSessionId
}: {
  activeStaffSession: ShelterStaffAccount | null;
  checklist: typeof defaultShelterChecklist;
  setChecklist: (value: typeof defaultShelterChecklist) => void;
  shelterPinConfigs: ShelterPinConfig[];
  setShelterPinConfigs: (configs: ShelterPinConfig[]) => void;
  shelterAuditEvents: ShelterAuditEvent[];
  setShelterAuditEvents: StateSetter<ShelterAuditEvent[]>;
  shelterStaffAccounts: ShelterStaffAccount[];
  setShelterStaffAccounts: (accounts: ShelterStaffAccount[]) => void;
  shelterUserAccounts: ShelterUserAccount[];
  setShelterUserAccounts: (accounts: ShelterUserAccount[]) => void;
  setActiveStaffSessionId: (id: string) => void;
}) {
  const [adminPin, setAdminPin] = useState("");
  const [adminUnlocked, setAdminUnlocked] = useState(false);
  const [adminStatus, setAdminStatus] = useState<AdminVerificationStatus>("idle");
  const [newStaffPin, setNewStaffPin] = useState("");
  const [staffPinStatus, setStaffPinStatus] = useState<"idle" | "invalid" | "updated" | "rotated">("idle");
  const [staffAccountStatus, setStaffAccountStatus] = useState<"idle" | "created" | "deleted" | "updated">("idle");
  const [staffDeleteConfirmId, setStaffDeleteConfirmId] = useState("");
  const [userDraft, setUserDraft] = useState(defaultManagedUserDraft);
  const [staffDraft, setStaffDraft] = useState({ displayName: "", email: "" });
  const [clientPhotoError, setClientPhotoError] = useState("");
  const [clientPhotoPreviewUrl, setClientPhotoPreviewUrl] = useState("");
  const [clientPhotoPreviewLabel, setClientPhotoPreviewLabel] = useState("");
  const [showClientPhotoPreview, setShowClientPhotoPreview] = useState(false);

  const operatorShelter = activeStaffSession?.shelter ?? shelterOptions[0];
  const staffForShelter = shelterStaffAccounts.filter((account) => account.shelter === operatorShelter);
  const usersForOperatorShelter = shelterUserAccounts.filter(
    (account) => account.shelter === operatorShelter && Boolean((account.createdByStaffId ?? "").trim())
  );

  // Deterministic shelter sort: unresolved housing first, then oldest registration date, then stable id.
  function accountSortByHousingThenDate(a: ShelterUserAccount, b: ShelterUserAccount) {
    if (a.foundPermanentHousing !== b.foundPermanentHousing) {
      return a.foundPermanentHousing ? 1 : -1;
    }
    const dateDelta = new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime();
    return dateDelta || a.id.localeCompare(b.id);
  }

  const staffRegisteredUsersForShelter = shelterUserAccounts
    .filter((account) => account.shelter === operatorShelter && Boolean((account.createdByStaffId ?? "").trim()))
    .sort(accountSortByHousingThenDate);

  const preferredShelterMentionUsers = shelterUserAccounts
    .filter(
      (account) =>
        account.shelter !== operatorShelter &&
        (account.preferredShelter ?? "").toLowerCase().includes(operatorShelter.toLowerCase())
    )
    .sort(accountSortByHousingThenDate);

  const recentShelterAuditEvents = shelterAuditEvents
    .filter((event) => event.shelter === operatorShelter)
    .slice(0, 6);

  function appendShelterAudit(action: string, actor = activeStaffSession?.displayName ?? "Shelter staff") {
    if (!activeStaffSession) return;
    setShelterAuditEvents((events) => [
      createShelterAuditEvent(operatorShelter, actor, action),
      ...events
    ].slice(0, 30));
  }

  function toggleManagedUserNeed(need: string) {
    setUserDraft((prev) => ({
      ...prev,
      serviceNeeds: prev.serviceNeeds.includes(need)
        ? prev.serviceNeeds.filter((item) => item !== need)
        : [...prev.serviceNeeds, need]
    }));
  }

  function createManagedUserAccount(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!activeStaffSession) return;
    const hasRequiredIdentity = userDraft.legalName.trim() && userDraft.dateOfBirth && userDraft.photoAssetId;
    if (!hasRequiredIdentity || !isBotCheckReady(userDraft.easyBotCheckStatus, userDraft.captchaToken)) return;

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
      preferredShelter: userDraft.preferredShelter.trim() || operatorShelter,
      socialWorker: userDraft.socialWorker.trim(),
      emergencyContactStarter: userDraft.emergencyContactStarter.trim(),
      serviceNeeds: userDraft.serviceNeeds,
      easyBotCheckStatus: userDraft.easyBotCheckStatus,
      captchaToken: userDraft.captchaToken,
      localPrecinctNotified: userDraft.localPrecinctNotified,
      foundPermanentHousing: userDraft.foundPermanentHousing,
      createdByStaffId: activeStaffSession.id,
      createdAt: new Date().toISOString()
    };
    setShelterUserAccounts([...shelterUserAccounts, newUser]);
    appendShelterAudit(
      isShelterRelatedHealthCheckStatus(newUser) ? "created_client_account_health_check" : "created_client_account"
    );
    setUserDraft(defaultManagedUserDraft);
    setClientPhotoError("");
    setClientPhotoPreviewUrl("");
    setClientPhotoPreviewLabel("");
    setShowClientPhotoPreview(false);
  }

  function createStaffAccount(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!activeStaffSession || !staffDraft.displayName.trim()) return;

    const newStaff: ShelterStaffAccount = {
      id: `staff-${Date.now()}`,
      shelter: operatorShelter,
      displayName: staffDraft.displayName.trim(),
      email: staffDraft.email.trim(),
      verified: false,
      updatedAt: new Date().toISOString()
    };
    setShelterStaffAccounts([...shelterStaffAccounts, newStaff]);
    appendShelterAudit("created_staff_account");
    setStaffDraft({ displayName: "", email: "" });
    setStaffAccountStatus("created");
  }

  function unlockAdminTools() {
    if (!adminPin.trim()) {
      setAdminStatus("missing_pin");
      setAdminUnlocked(false);
      return;
    }

    const pinConfig = getShelterPinConfig(shelterPinConfigs, operatorShelter);
    if (adminPin !== pinConfig.adminPin) {
      setAdminStatus("invalid_pin");
      setAdminUnlocked(false);
      return;
    }

    setAdminStatus("verified");
    setAdminUnlocked(true);
    appendShelterAudit("administrator_pin_verified");
  }

  function updateStaffPin(pin: string, status: "updated" | "rotated") {
    if (!/^\d{4}$/.test(pin)) {
      setStaffPinStatus("invalid");
      return;
    }

    setShelterPinConfigs(
      shelterPinConfigs.map((config) =>
        config.shelter === operatorShelter ? { ...config, staffPin: pin, updatedAt: new Date().toISOString() } : config
      )
    );
    setStaffPinStatus(status);
    appendShelterAudit(status === "rotated" ? "rotated_staff_pin" : "changed_staff_pin");
    setNewStaffPin("");
  }

  function rotateStaffPin() {
    const rotatedPin = String(Math.floor(1000 + Math.random() * 9000));
    updateStaffPin(rotatedPin, "rotated");
  }

  function deleteStaffAccount(account: ShelterStaffAccount) {
    setShelterStaffAccounts(shelterStaffAccounts.filter((item) => item.id !== account.id));
    appendShelterAudit("deleted_staff_account");
    if (account.id === activeStaffSession?.id) {
      setActiveStaffSessionId("");
    }
    setStaffDeleteConfirmId("");
    setStaffAccountStatus("deleted");
  }

  if (!activeStaffSession) {
    return (
      <div className="screen">
        <div className="page-title">
          <p className="eyebrow">Shelter portal</p>
          <h1>Staff verification required</h1>
        </div>
        <StatusBanner tone="warning">
          Assisted access is shown only after a shelter staff account is verified from registration.
        </StatusBanner>
        <Section title="How to unlock">
          <p className="supporting-copy">
            Open Register, check "I am shelter staff", choose your shelter, and enter the shelter staff PIN.
          </p>
        </Section>
      </div>
    );
  }

  return (
    <div className="screen">
      <div className="page-title">
        <p className="eyebrow">Shelter portal</p>
        <h1>Assisted access</h1>
      </div>
      <StatusBanner tone="info">
        Shelter workflows are available only to verified shelter staff. Signed in as {activeStaffSession.displayName} at{" "}
        {operatorShelter}.
      </StatusBanner>
      <Section title="Staff tools">
        <div className="tool-grid">
          <button className="tool-tile" type="button">
            <ClipboardCheck size={24} /> Assist registration
          </button>
          <button className="tool-tile" type="button">
            <UsersRound size={24} /> Verify contact
          </button>
          <button className="tool-tile" type="button">
            <ShieldCheck size={24} /> Review staff audit
          </button>
        </div>
      </Section>
      <Section title="Create user account">
        <StatusBanner tone="info">
          These are client user accounts associated with {operatorShelter}, not staff accounts.
        </StatusBanner>
        <form className="form-grid" onSubmit={createManagedUserAccount}>
          <Field label="Legal or full name" required>
            <input value={userDraft.legalName} onChange={(event) => setUserDraft({ ...userDraft, legalName: event.target.value })} />
          </Field>
          <Field label="Preferred name">
            <input
              value={userDraft.preferredName}
              onChange={(event) => setUserDraft({ ...userDraft, preferredName: event.target.value })}
            />
          </Field>
          <Field label="Pronouns">
            <input value={userDraft.pronouns} onChange={(event) => setUserDraft({ ...userDraft, pronouns: event.target.value })} />
          </Field>
          <Field label="Birth date" required>
            <input
              type="date"
              value={userDraft.dateOfBirth}
              onChange={(event) => setUserDraft({ ...userDraft, dateOfBirth: event.target.value })}
            />
          </Field>
          <Field help={PROFILE_PHOTO_HELP} label="Photo or photo ID" required>
            <input
              accept={PROFILE_PHOTO_ACCEPT_ATTR}
              capture="user"
              type="file"
              onChange={(event) => {
                const file = event.target.files?.[0] ?? null;
                if (!file) {
                  setUserDraft({ ...userDraft, photoAssetId: "" });
                  setClientPhotoError("");
                  setClientPhotoPreviewUrl("");
                  setClientPhotoPreviewLabel("");
                  setShowClientPhotoPreview(false);
                  return;
                }
                if (!isAcceptedProfilePhoto(file)) {
                  event.currentTarget.value = "";
                  setUserDraft({ ...userDraft, photoAssetId: "" });
                  setClientPhotoError("Use JPEG, PNG, or WebP for profile photos. Upload PDFs in the document vault.");
                  setClientPhotoPreviewUrl("");
                  setClientPhotoPreviewLabel("");
                  setShowClientPhotoPreview(false);
                  return;
                }
                setClientPhotoError("");
                setUserDraft({ ...userDraft, photoAssetId: file.name });
                setShowClientPhotoPreview(false);

                try {
                  const fileReader = new FileReader();
                  fileReader.onload = () => {
                    setClientPhotoPreviewUrl(String(fileReader.result || ""));
                    setClientPhotoPreviewLabel("Selected image preview");
                  };
                  fileReader.readAsDataURL(file);
                } catch {
                  setClientPhotoPreviewUrl("");
                  setClientPhotoPreviewLabel("Preview unavailable for this file.");
                }
              }}
            />
            {clientPhotoPreviewUrl ? (
              <div className="photo-preview-toggle">
                <button
                  className="preview-toggle-button"
                  onClick={() => setShowClientPhotoPreview(!showClientPhotoPreview)}
                  type="button"
                >
                  {showClientPhotoPreview ? "Hide preview" : "See preview"}
                </button>
                {showClientPhotoPreview ? (
                  <div className="photo-preview-card">
                    <small>{clientPhotoPreviewLabel}</small>
                    <img alt="Client upload preview" src={clientPhotoPreviewUrl} />
                  </div>
                ) : null}
              </div>
            ) : clientPhotoPreviewLabel ? (
              <small>{clientPhotoPreviewLabel}</small>
            ) : null}
            {clientPhotoError ? <small className="pin-error-note">{clientPhotoError}</small> : null}
          </Field>
          <Field label="Phone">
            <input value={userDraft.phone} onChange={(event) => setUserDraft({ ...userDraft, phone: event.target.value })} />
          </Field>
          <Field label="Email">
            <input type="email" value={userDraft.email} onChange={(event) => setUserDraft({ ...userDraft, email: event.target.value })} />
          </Field>
          <Field label="Current safe location">
            <input
              value={userDraft.currentLocation}
              onChange={(event) => setUserDraft({ ...userDraft, currentLocation: event.target.value })}
            />
          </Field>
          <Field label="Preferred shelter">
            <input
              value={userDraft.preferredShelter}
              onChange={(event) => setUserDraft({ ...userDraft, preferredShelter: event.target.value })}
              placeholder={operatorShelter}
            />
          </Field>
          <Field label="Social worker">
            <input
              value={userDraft.socialWorker}
              onChange={(event) => setUserDraft({ ...userDraft, socialWorker: event.target.value })}
            />
          </Field>
          <Field label="Emergency contact starter">
            <input
              value={userDraft.emergencyContactStarter}
              onChange={(event) => setUserDraft({ ...userDraft, emergencyContactStarter: event.target.value })}
            />
          </Field>
          <div className="full-span">
            <span className="field-label">Service needs</span>
            <small className="field-help">Optional service categories for the client's own account setup.</small>
            <div className="chip-grid">
              {serviceNeeds.map((need) => (
                <button
                  aria-pressed={userDraft.serviceNeeds.includes(need)}
                  className="choice-chip"
                  key={need}
                  onClick={() => toggleManagedUserNeed(need)}
                  type="button"
                >
                  {need}
                </button>
              ))}
            </div>
          </div>
          <label className="captcha-box full-span">
            <input
              aria-required="true"
              checked={userDraft.easyBotCheckStatus === "passed"}
              onChange={(event) =>
                setUserDraft({ ...userDraft, easyBotCheckStatus: event.target.checked ? "passed" : "failed", captchaToken: "" })
              }
              type="checkbox"
            />
            <span>
              Quick health check complete (step 1)
              <RequiredMarker />
            </span>
          </label>
          <div className="full-span">
            <Button
              onClick={() => setUserDraft({ ...userDraft, easyBotCheckStatus: "failed", captchaToken: "" })}
              variant="secondary"
            >
              Mark health check follow-up
            </Button>
          </div>
          <label className="captcha-box full-span">
            <input
              aria-required="true"
              checked={Boolean(userDraft.captchaToken)}
              disabled={userDraft.easyBotCheckStatus === "pending"}
              onChange={(event) => setUserDraft({ ...userDraft, captchaToken: event.target.checked ? "mock-captcha-token" : "" })}
              type="checkbox"
            />
            <span>
              Bot check complete (step 2)
              <RequiredMarker />
            </span>
          </label>
          <label className="consent-box full-span">
            <input
              checked={userDraft.localPrecinctNotified}
              onChange={(event) => setUserDraft({ ...userDraft, localPrecinctNotified: event.target.checked })}
              type="checkbox"
            />
            <span>
              <strong>Local precinct notified as emergency contact</strong>
            </span>
          </label>
          <label className="consent-box full-span">
            <input
              checked={userDraft.foundPermanentHousing}
              onChange={(event) => setUserDraft({ ...userDraft, foundPermanentHousing: event.target.checked })}
              type="checkbox"
            />
            <span>
              <strong>Found permanent housing</strong>
            </span>
          </label>
          <div className="full-span">
            <Button
              disabled={
                !userDraft.legalName.trim() ||
                !userDraft.dateOfBirth ||
                !userDraft.photoAssetId ||
                !isBotCheckReady(userDraft.easyBotCheckStatus, userDraft.captchaToken)
              }
              type="submit"
            >
              Create user account
            </Button>
          </div>
        </form>
      </Section>
      <Section title="Recently created client accounts">
        <div className="list-stack">
          {usersForOperatorShelter.length ? (
            usersForOperatorShelter.map((account) => (
              <article className="list-item" key={account.id}>
                <div>
                  <h3>{account.preferredName || account.legalName}</h3>
                  <p>{account.legalName}</p>
                  <small>
                    Created by {shelterStaffAccounts.find((item) => item.id === account.createdByStaffId)?.displayName ?? "Former staff"}
                    {account.dateOfBirth ? ` - DOB ${account.dateOfBirth}` : ""}
                  </small>
                </div>
                <div className="badge-row">
                  <Badge>User account</Badge>
                  {isShelterRelatedHealthCheckStatus(account) ? <Badge tone="warning">Health check</Badge> : null}
                </div>
              </article>
            ))
          ) : (
            <small>No user accounts created for this shelter yet.</small>
          )}
        </div>
      </Section>
      <Section title="Shelter user oversight">
        <div className="list-stack">
          <h3>Staff-created users</h3>
          {staffRegisteredUsersForShelter.length ? (
            staffRegisteredUsersForShelter.map((account) => (
              <article className="list-item" key={`overview-${account.id}`}>
                <div>
                  <h3>{account.preferredName || account.legalName}</h3>
                  <p>{account.legalName}</p>
                  <div className="badge-row">
                    <Badge tone={account.localPrecinctNotified ? "success" : "warning"}>
                      {account.localPrecinctNotified ? "Precinct notified" : "Precinct not notified"}
                    </Badge>
                    <Badge tone={account.foundPermanentHousing ? "success" : "neutral"}>
                      {account.foundPermanentHousing ? "Found housing" : "Housing not found"}
                    </Badge>
                    {isShelterRelatedHealthCheckStatus(account) ? <Badge tone="warning">Health check</Badge> : null}
                  </div>
                </div>
              </article>
            ))
          ) : (
            <small>No shelter-registered users for this shelter yet.</small>
          )}
        </div>
        <div className="list-stack">
          <h3>Preferred-shelter mentions</h3>
          {preferredShelterMentionUsers.length ? (
            preferredShelterMentionUsers.map((account) => (
              <article className="list-item" key={`preferred-${account.id}`}>
                <div>
                  <h3>{account.preferredName || account.legalName}</h3>
                  <p>{account.legalName}</p>
                  <div className="badge-row">
                    <Badge tone={account.localPrecinctNotified ? "success" : "warning"}>
                      {account.localPrecinctNotified ? "Precinct notified" : "Precinct not notified"}
                    </Badge>
                    <Badge tone={account.foundPermanentHousing ? "success" : "neutral"}>
                      {account.foundPermanentHousing ? "Found housing" : "Housing not found"}
                    </Badge>
                    {isShelterRelatedHealthCheckStatus(account) ? <Badge tone="warning">Health check</Badge> : null}
                  </div>
                </div>
              </article>
            ))
          ) : (
            <small>No users listed this shelter as preferred shelter.</small>
          )}
        </div>
      </Section>
      <Section title="Shared-device safety">
        <div className="checklist">
          <label>
            <input
              checked={checklist.userPresent}
              onChange={(event) => setChecklist({ ...checklist, userPresent: event.target.checked })}
              type="checkbox"
            />{" "}
            Confirm user is present for assisted setup
          </label>
          <label>
            <input
              checked={checklist.clearBrowserData}
              onChange={(event) => setChecklist({ ...checklist, clearBrowserData: event.target.checked })}
              type="checkbox"
            />{" "}
            Clear browser data after shared-device session
          </label>
          <label>
            <input
              checked={checklist.auditLogConfirmed}
              onChange={(event) => setChecklist({ ...checklist, auditLogConfirmed: event.target.checked })}
              type="checkbox"
            />{" "}
            Staff action will be added to the audit log
          </label>
        </div>
      </Section>
      <Section title="Shelter administrator">
        <StatusBanner tone="warning">
          Demo administrator PIN checks happen in browser state. Production PIN verification must move server-side.
        </StatusBanner>
        <div className="shelter-staff-panel">
          <Field help={`Unlock administrator tools for ${operatorShelter}.`} label="Administrator PIN" required>
            <input
              inputMode="numeric"
              maxLength={4}
              placeholder="Enter admin PIN"
              type="password"
              value={adminPin}
              onChange={(event) => {
                setAdminPin(event.target.value.replace(/\D/g, "").slice(0, 4));
                setAdminStatus("idle");
              }}
            />
          </Field>
          <div>
            <Button onClick={unlockAdminTools} type="button">
              <ShieldCheck size={18} /> Unlock administrator tools
            </Button>
            {adminStatus === "missing_pin" ? <small className="pin-error-note">missing_pin: enter the administrator PIN.</small> : null}
            {adminStatus === "invalid_pin" ? <small className="pin-error-note">invalid_pin: administrator PIN did not match.</small> : null}
            {adminStatus === "verified" ? <small className="pin-request-note">verified: administrator tools unlocked.</small> : null}
          </div>
        </div>
        {adminUnlocked ? (
          <div className="shelter-staff-panel">
            <Section title="Staff PIN management">
              <div className="form-grid">
                <Field help="Use four digits. The current PIN is not shown." label="New staff PIN">
                  <input
                    inputMode="numeric"
                    maxLength={4}
                    placeholder="New staff PIN"
                    type="password"
                    value={newStaffPin}
                    onChange={(event) => {
                      setNewStaffPin(event.target.value.replace(/\D/g, "").slice(0, 4));
                      setStaffPinStatus("idle");
                    }}
                  />
                </Field>
                <div className="row-actions">
                  <Button onClick={() => updateStaffPin(newStaffPin, "updated")} type="button">
                    Save staff PIN
                  </Button>
                  <Button onClick={rotateStaffPin} type="button" variant="secondary">
                    Rotate staff PIN for all staff
                  </Button>
                </div>
              </div>
              {staffPinStatus === "invalid" ? <small className="pin-error-note">Enter a four-digit staff PIN.</small> : null}
              {staffPinStatus === "updated" ? <small className="pin-request-note">Staff PIN changed for future staff verification.</small> : null}
              {staffPinStatus === "rotated" ? <small className="pin-request-note">Staff PIN rotated for this shelter.</small> : null}
            </Section>
            <Section title="Create staff account">
              <form className="form-grid" onSubmit={createStaffAccount}>
                <Field label="Staff name" required>
                  <input
                    value={staffDraft.displayName}
                    onChange={(event) => {
                      setStaffDraft({ ...staffDraft, displayName: event.target.value });
                      setStaffAccountStatus("idle");
                    }}
                  />
                </Field>
                <Field label="Staff email">
                  <input
                    type="email"
                    value={staffDraft.email}
                    onChange={(event) => {
                      setStaffDraft({ ...staffDraft, email: event.target.value });
                      setStaffAccountStatus("idle");
                    }}
                  />
                </Field>
                <div className="full-span">
                  <Button type="submit">Create staff account</Button>
                </div>
              </form>
            </Section>
            <Section title="Staff accounts">
              <div className="list-stack">
                {staffForShelter.length ? (
                  staffForShelter.map((account) => (
                  <article className="list-item" key={account.id}>
                    <div>
                      <h3>{account.displayName}</h3>
                      <p>{account.email || "No email provided"}</p>
                      <div className="badge-row">
                        <Badge tone={account.verified ? "success" : "warning"}>
                          {account.verified ? "Verified" : "Revoked"}
                        </Badge>
                      </div>
                    </div>
                    <div className="row-actions">
                      <Button
                        onClick={() => {
                          setShelterStaffAccounts(
                            shelterStaffAccounts.map((item) =>
                              item.id === account.id
                                ? { ...item, verified: !item.verified, updatedAt: new Date().toISOString() }
                                : item
                            )
                          );
                          appendShelterAudit(account.verified ? "revoked_staff_verification" : "restored_staff_verification");
                          setStaffAccountStatus("updated");
                          if (account.verified && account.id === activeStaffSession.id) {
                            setActiveStaffSessionId("");
                          }
                        }}
                        variant="secondary"
                      >
                        {account.verified ? "Revoke verification" : "Re-verify"}
                      </Button>
                      {staffDeleteConfirmId === account.id ? (
                        <>
                          <Button onClick={() => deleteStaffAccount(account)} type="button" variant="danger">
                            Confirm delete
                          </Button>
                          <Button onClick={() => setStaffDeleteConfirmId("")} type="button" variant="quiet">
                            Cancel
                          </Button>
                        </>
                      ) : (
                        <Button onClick={() => setStaffDeleteConfirmId(account.id)} type="button" variant="danger">
                          Delete staff account
                        </Button>
                      )}
                    </div>
                  </article>
                ))
              ) : (
                <small>No staff accounts registered for this shelter yet.</small>
              )}
                {staffAccountStatus === "created" ? <small className="pin-request-note">Staff account created.</small> : null}
                {staffAccountStatus === "deleted" ? <small className="pin-request-note">Staff account deleted.</small> : null}
                {staffAccountStatus === "updated" ? <small className="pin-request-note">Staff verification updated.</small> : null}
              </div>
            </Section>
            <Section title="Shelter audit events">
              <div className="timeline">
                {recentShelterAuditEvents.length ? (
                  recentShelterAuditEvents.map((event) => (
                    <article className="timeline-event" key={event.id}>
                      <span aria-hidden="true" />
                      <div>
                        <h3>{event.action.replace(/_/g, " ")}</h3>
                        <p>{event.actor}</p>
                        <small>{new Date(event.timestamp).toLocaleString()}</small>
                      </div>
                    </article>
                  ))
                ) : (
                  <small>No shelter audit events yet.</small>
                )}
              </div>
            </Section>
          </div>
        ) : null}
      </Section>
    </div>
  );
}

function RecipientAccessScreen({
  accessRequests,
  recipients,
  setAccessRequests,
  verified,
  setVerified
}: {
  accessRequests: WalletAccessRequest[];
  recipients: DisclosureRecipientDraft[];
  setAccessRequests: (requests: WalletAccessRequest[]) => void;
  verified: boolean;
  setVerified: (verified: boolean) => void;
}) {
  const recipient = recipients[0];
  const [secureLinkExpired, setSecureLinkExpired] = useState(false);
  const authorizedScopes =
    recipient && recipient.emergencyDisclosureEnabled && !recipient.revokedAt ? getEffectiveSharingScopes(recipient) : [];

  function hasThresholdApproval(request: WalletAccessRequest) {
    if (!request.approvalRequired) return true;
    return (request.approvalCount ?? 0) >= (request.approvalThreshold ?? 1);
  }

  function recordControllerApproval(requestId: string) {
    setAccessRequests(
      accessRequests.map((request) =>
        request.id === requestId
          ? {
              ...request,
              approvalCount: Math.min(
                (request.approvalCount ?? 0) + 1,
                request.approvalThreshold ?? (request.approvalCount ?? 0) + 1
              )
            }
          : request
      )
    );
  }

  



  function decideRequest(requestId: string, status: "approved" | "rejected") {
    setAccessRequests(accessRequests.map((request) => (request.id === requestId ? { ...request, status } : request)));
  }

  return (
    <div className="screen">
      <div className="page-title">
        <p className="eyebrow">Secure access</p>
        <h1>Access requests</h1>
      </div>
      <StatusBanner tone={secureLinkExpired ? "warning" : "info"}>
        {secureLinkExpired
          ? "This secure link is expired. Ask the sender or shelter liaison to issue a new link."
          : "Secure links show only the scopes the user authorized for this recipient and expire after the listed window."}
      </StatusBanner>
      <Section title="Review requested access">
        <div className="list-stack">
          {accessRequests.map((request) => (
            <article className="list-item access-request-item" key={request.id}>
              <div>
                <div className="scope-header">
                  <div>
                    <h3>{request.requesterName}</h3>
                    <p>{request.resourceLabel} · {request.purpose}</p>
                  </div>
                  <Badge tone={request.status === "approved" ? "success" : request.status === "rejected" ? "warning" : "neutral"}>
                    {request.status}
                  </Badge>
                </div>
                <div className="badge-row">
                  {request.abilities.map((ability) => (
                    <Badge key={ability}>{ability}</Badge>
                  ))}
                  <Badge>{request.createdAt}</Badge>
                  {request.expiresAt ? <Badge tone="warning">Expires {request.expiresAt}</Badge> : null}
                  {request.approvalRequired ? (
                    <Badge tone={hasThresholdApproval(request) ? "success" : "warning"}>
                      {request.approvalCount ?? 0}/{request.approvalThreshold ?? 1} approvals
                    </Badge>
                  ) : null}
                </div>
                {request.approvalRequired && !hasThresholdApproval(request) ? (
                  <p className="approval-note">Multi-sig approval is required before this access can be granted.</p>
                ) : null}
                <small>{request.requesterDid}</small>
              </div>
              {request.status === "pending" ? (
                <div className="row-actions">
                  {request.approvalRequired && !hasThresholdApproval(request) ? (
                    <Button onClick={() => recordControllerApproval(request.id)} variant="secondary">
                      <ShieldCheck size={18} /> Record approval
                    </Button>
                  ) : null}
                  <Button
                    disabled={!hasThresholdApproval(request)}
                    onClick={() => decideRequest(request.id, "approved")}
                    variant="secondary"
                  >
                    <ShieldCheck size={18} /> Approve
                  </Button>
                  <Button onClick={() => decideRequest(request.id, "rejected")} variant="danger">
                    Reject
                  </Button>
                </div>
               ) : null}
            </article>
          ))}
        </div>
      </Section>
      <Section title="Secure link status">
        <div className="row-actions">
          <Button onClick={() => setSecureLinkExpired(!secureLinkExpired)} type="button" variant="secondary">
            {secureLinkExpired ? "Restore demo link" : "Simulate expired link"}
          </Button>
        </div>
        <small>
          Link recovery state: {secureLinkExpired ? "expired-link recovery required" : "active until the expiration time"}.
        </small>
      </Section>
      {!verified || secureLinkExpired ? (
        <Section title="Verify recipient">
          <StatusBanner tone="warning">Sensitive information is hidden until recipient verification is complete.</StatusBanner>
          <div className="form-grid">
            <Field
              error={secureLinkExpired ? "Expired links cannot reveal data. Request a new secure link." : undefined}
              label="Access code"
            >
              <input placeholder="Enter code" />
            </Field>
            <Field label="Recipient phone or email">
              <input placeholder="Confirm contact method" />
            </Field>
          </div>
          <Button disabled={secureLinkExpired} onClick={() => setVerified(true)}>
            <KeyRound size={18} /> Verify and view
          </Button>
        </Section>
      ) : (
        <Section title={`Authorized for ${recipient.displayName}`}>
          <div className="disclosure-package">
            {authorizedScopes.length ? (
              authorizedScopes.map((scope) => (
                <div className="disclosure-row" key={scope}>
                  <strong>{disclosureScopes.find((item) => item.id === scope)?.label ?? scope}</strong>
                  <span>Available in this emergency package</span>
                </div>
              ))
            ) : (
              <div className="disclosure-row">
                <strong>No active disclosure scopes</strong>
                <span>The user has not enabled emergency disclosure for this recipient.</span>
              </div>
            )}
          </div>
          <div className="next-step-grid">
            <StatusPanel label="Next step" value="Contact user or shelter" tone="teal" />
            <StatusPanel label="If unavailable" value="Contact social worker" tone="gold" />
            <StatusPanel label="For access issues" value="Contact liaison" tone="red" />
          </div>
          <Button variant="secondary">Contact liaison</Button>
        </Section>
      )}
    </div>
  );
}

function BenefitsProtectionScreen({
  history,
  optedIn,
  setHistory,
  setOptedIn
}: {
  history: string[];
  optedIn: boolean;
  setHistory: (history: string[]) => void;
  setOptedIn: (optedIn: boolean) => void;
}) {
  function updateBenefitsConsent(nextValue: boolean) {
    setOptedIn(nextValue);
    setHistory([
      `${new Date().toLocaleString()}: Benefits protection consent ${nextValue ? "enabled" : "revoked"}`,
      ...history
    ]);
  }

  return (
    <div className="screen">
      <div className="page-title">
        <p className="eyebrow">Benefits protection</p>
        <h1>Optional agency notification</h1>
      </div>
      <StatusBanner tone="warning">
        This can only request or notify through approved agency workflows. It does not guarantee agency action.
      </StatusBanner>
      <Section title="Explicit opt-in">
        <label className="consent-box">
          <input checked={optedIn} onChange={(event) => updateBenefitsConsent(event.target.checked)} type="checkbox" />
          <span>
            <strong>Allow Abby to prepare a benefits-protection notification after missed check-ins.</strong>
            <small>Legal and policy review must be completed before this can be sent in production.</small>
          </span>
        </label>
        <small className="pin-request-note">
          This prototype auto-saves the local opt-in choice. Production notifications still require approved agency
          workflows.
        </small>
      </Section>
      <Section title="Consent review">
        <div className="review-panel">
          <div>
            <strong>{optedIn ? "Benefits preparation is enabled" : "Benefits preparation is off"}</strong>
            <small>
              Minimum data only: legal name, missed check-in status, selected benefits need, and approved contact path.
            </small>
            <small>
              This consent is separate from emergency disclosure scopes and can be revoked without changing other sharing
              rules.
            </small>
          </div>
          <div className="row-actions">
            <Button disabled={!optedIn} onClick={() => updateBenefitsConsent(false)} type="button" variant="danger">
              Revoke benefits consent
            </Button>
          </div>
        </div>
      </Section>
      <Section title="Benefits consent history">
        <div className="timeline">
          {history.length ? (
            history.slice(0, 4).map((entry) => (
              <article className="timeline-event" key={entry}>
                <span aria-hidden="true" />
                <div>
                  <h3>{entry.includes("revoked") ? "Consent revoked" : "Consent enabled"}</h3>
                  <p>{entry}</p>
                </div>
              </article>
            ))
          ) : (
            <small>No benefits consent changes yet.</small>
          )}
        </div>
      </Section>
    </div>
  );
}

function AnalyticsScreen({
  optedIn,
  setOptedIn
}: {
  optedIn: Record<string, boolean>;
  setOptedIn: (value: Record<string, boolean>) => void;
}) {
  function toggleStudy(studyId: string) {
    setOptedIn({ ...optedIn, [studyId]: !optedIn[studyId] });
  }

  return (
    <div className="screen">
      <div className="page-title">
        <p className="eyebrow">Analytics consent</p>
        <h1>Share patterns, not personal records</h1>
      </div>
      <StatusBanner tone="info">
        Only derived fields are used. Exact counts stay hidden until privacy thresholds and budget checks pass.
      </StatusBanner>
      <div className="analytics-grid">
        {analyticsStudies.map((study) => {
          const selected = Boolean(optedIn[study.id]);
          const budgetRemaining = Math.max(0, study.epsilonBudget - study.spentBudget);
          const titleId = `analytics-title-${study.id}`;
          return (
            <article aria-labelledby={titleId} className="analytics-card" key={study.id}>
              <div className="scope-header">
                <div>
                  <h3 id={titleId}>{study.title}</h3>
                  <p>{study.purpose}</p>
                </div>
                <Badge tone={study.status === "paused" ? "warning" : selected ? "success" : "neutral"}>
                  {selected ? "Consented" : study.status}
                </Badge>
              </div>
              <div className="privacy-metrics">
                <StatusPanel label="Minimum cohort" value={String(study.minCohortSize)} tone="teal" />
                <StatusPanel label="Budget left" value={budgetRemaining.toFixed(2)} tone="gold" />
              </div>
              <div className="badge-row">
                {study.fields.map((field) => (
                  <Badge key={field}>{field}</Badge>
                ))}
              </div>
              <label className="consent-box">
                <input
                  checked={selected}
                  disabled={study.status === "paused"}
                  onChange={() => toggleStudy(study.id)}
                  type="checkbox"
                />
                <span>
                  <strong>Allow this study to use the listed derived fields.</strong>
                  <small>Precise location, raw documents, names, and contact details are excluded.</small>
                </span>
              </label>
            </article>
          );
        })}
      </div>
    </div>
  );
}

function SecurityScreen({
  securitySettings,
  setSecuritySettings
}: {
  securitySettings: typeof defaultSecuritySettings;
  setSecuritySettings: (settings: typeof defaultSecuritySettings) => void;
}) {
  const [recoveryCheckRunning, setRecoveryCheckRunning] = useState(false);
  const updateSecuritySetting = (patch: Partial<typeof defaultSecuritySettings>) =>
    setSecuritySettings({ ...securitySettings, ...patch });

  return (
    <div className="screen">
      <div className="page-title">
        <p className="eyebrow">Security</p>
        <h1>Account safety</h1>
      </div>
      <StatusBanner tone="info">Saved security choices stay on this device. Temporary reveal states do not persist.</StatusBanner>
      <Section title="Session and recovery">
        <div className="dashboard-grid">
          <StatusPanel label="Login" value="Email or wallet sign-in placeholder" tone="teal" />
          <StatusPanel label="Logout" value="Clears active session on shared devices" tone="gold" />
          <StatusPanel label="Recovery" value="Device and contact checks required" tone="red" />
        </div>
      </Section>
      <Section title="Security settings">
        <div className="list-stack">
          <label className="consent-box">
            <input
              checked={securitySettings.sessionTimeoutEnabled}
              onChange={(event) => updateSecuritySetting({ sessionTimeoutEnabled: event.target.checked })}
              type="checkbox"
            />
            <span>
              <strong>
                <LockKeyhole size={18} /> End idle sessions on shared devices
              </strong>
              <small>Keep this on for public or shelter computers.</small>
            </span>
          </label>
          <label className="consent-box">
            <input
              checked={securitySettings.recoveryRemindersEnabled}
              onChange={(event) => updateSecuritySetting({ recoveryRemindersEnabled: event.target.checked })}
              type="checkbox"
            />
            <span>
              <strong>
                <KeyRound size={18} /> Send recovery reminder prompts
              </strong>
              <small>Reminder content avoids exposing sensitive account details.</small>
            </span>
          </label>
          <label className="consent-box">
            <input
              checked={securitySettings.publicFormCaptchaEnabled}
              onChange={(event) => updateSecuritySetting({ publicFormCaptchaEnabled: event.target.checked })}
              type="checkbox"
            />
            <span>
              <strong>
                <ShieldCheck size={18} /> Require bot checks on public forms
              </strong>
              <small>This prototype saves the preference locally; production enforcement belongs on the server.</small>
            </span>
          </label>
          <label className="consent-box">
            <input
              checked={securitySettings.passkeyPlaceholderEnabled}
              onChange={(event) => updateSecuritySetting({ passkeyPlaceholderEnabled: event.target.checked })}
              type="checkbox"
            />
            <span>
              <strong>
                <KeyRound size={18} /> Show passkey or device-key placeholders
              </strong>
              <small>Reserved for a future wallet backend that can register trusted devices securely.</small>
            </span>
          </label>
        </div>
      </Section>
      <Section title="Sensitive recovery details">
        <div className="security-pattern-grid">
          <Card title="Recovery contact">
            <SensitiveValue label="Recovery contact" redactedValue="m***@example.org" value="maya@example.org" />
            <StatusIndicator
              detail="Revealed values stay local and block direct copy."
              label="Copy-disabled reveal"
              tone="warning"
            />
          </Card>
          <Card title="Secure reveal steps">
            <Stepper currentStep={1} label="Secure reveal steps" steps={["Verify", "Review scope", "Reveal"]} />
            <StatusIndicator detail="Only authorized recovery steps can reveal the contact." label="Verified contact required" tone="success" />
          </Card>
          <Card title="Recovery check">
            {recoveryCheckRunning ? <LoadingIndicator label="Checking recovery route" /> : null}
            <Button
              loading={recoveryCheckRunning}
              loadingLabel="Checking recovery route"
              onClick={() => setRecoveryCheckRunning(true)}
              type="button"
              variant="secondary"
            >
              Check recovery route
            </Button>
          </Card>
        </div>
      </Section>
      <Section title="Device verification placeholders">
        <div className="list-stack">
          <article className="list-item">
            <div>
              <h3>Session timeout</h3>
              <p>When enabled, idle shared-device sessions should require a fresh login before showing sensitive data.</p>
            </div>
            <Badge tone={securitySettings.sessionTimeoutEnabled ? "success" : "warning"}>
              {securitySettings.sessionTimeoutEnabled ? "On" : "Off"}
            </Badge>
          </article>
          <article className="list-item">
            <div>
              <h3>Account recovery</h3>
              <p>Recovery should use verified contact methods and avoid revealing profile or shelter details.</p>
            </div>
            <Badge tone={securitySettings.recoveryRemindersEnabled ? "success" : "neutral"}>
              {securitySettings.recoveryRemindersEnabled ? "Reminders on" : "No reminders"}
            </Badge>
          </article>
          <article className="list-item">
            <div>
              <h3>Passkey readiness</h3>
              <p>Passkey UI is a placeholder until the backend supports device-key registration.</p>
            </div>
            <Badge tone={securitySettings.passkeyPlaceholderEnabled ? "success" : "neutral"}>
              {securitySettings.passkeyPlaceholderEnabled ? "Placeholder shown" : "Placeholder hidden"}
            </Badge>
          </article>
        </div>
      </Section>
    </div>
  );
}

function AuditScreen() {
  return (
    <div className="screen">
      <div className="page-title">
        <p className="eyebrow">Audit</p>
        <h1>Consent and access history</h1>
      </div>
      <div className="timeline">
        {auditEvents.map((event) => (
          <article className="timeline-event" key={event.id}>
            <span aria-hidden="true" />
            <div>
              <h3>{event.action}</h3>
              <p>
                {event.actor} · {event.timestamp}
              </p>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

