import { ChangeEvent, FormEvent, useEffect, useMemo, useRef, useState } from "react";
import {
  Archive,
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
  RefreshCw,
  Search,
  ShieldCheck,
  Smartphone,
  Sparkles,
  Upload,
  UserMinus,
  UserPlus,
  UsersRound,
  Wrench
} from "lucide-react";
import { ActionCard, Badge, Button, Field, Section, StatusBanner } from "../components/ui";
import {
  CheckInChannel,
  AuditEvent,
  AnalyticsStudy,
  DisclosureDataScope,
  DisclosureRecipientDraft,
  DisclosureRecipientType,
  DecryptedRecordView,
  DerivedArtifactView,
  EasyBotCheckStatus,
  ExportBundleView,
  RegistrationProfileDraft,
  RouteId,
  UploadItem,
  WalletAccessRequest,
  WalletGrantReceipt,
  ProofReceiptView
} from "../models/abby";
import {
  analyticsStudies,
  auditEvents,
  defaultCheckInPolicy,
  emptyRegistrationProfile,
  exportBundles,
  initialRecipients,
  initialAccessRequests,
  initialGrantReceipts,
  initialUploads,
  proofReceipts,
  serviceMatches
} from "../services/mockAbbyService";
import { abilitiesForDisclosureScopes, capabilitySummary, nonGrantedCapabilities } from "../services/capabilities";
import { answer211InfoQuestion, get211InfoRuntimeStatus, search211Info } from "../services/graphRagService";
import type { GraphRagRuntimeStatus } from "../services/graphRagService";
import type { GraphRagAnswer, SearchResult } from "../lib/graphrag";
import {
  approveAccessRequest,
  approveThresholdApproval,
  addWalletController,
  addWalletDevice,
  addBinaryDocument,
  addTextDocument,
  analyzeRecordWithGrant,
  createLocationRegionProof,
  createRecordGrant,
  createWalletAnalyticsConsent,
  createVerifiedExportBundleView,
  delegateGrant,
  decryptRecordWithGrant,
  emergencyRevoke,
  importExportBundleView,
  issueRecordDecryptInvocation,
  loadOpsHealth,
  listWalletSnapshots,
  loadExportBundleView,
  loadWalletSnapshot,
  loadWalletAccessState,
  loadWalletDetails,
  listThresholdApprovals,
  listWalletAuditEvents,
  listAnalyticsTemplates,
  listWalletAnalyticsConsents,
  listWalletDocuments,
  listWalletProofReceipts,
  rejectAccessRequest,
  repairRecordStorage,
  repairWalletStorage,
  recoverWalletController,
  removeWalletController,
  requestRecordGrantApproval,
  requestWalletAdminApproval,
  rotateRecordKey,
  revokeWalletAnalyticsConsent,
  revokeWalletDevice,
  revokeAccessRequest,
  saveWalletSnapshot,
  setWalletRecoveryPolicy,
  verifyWalletSnapshot,
  verifyWalletStorage,
  EmergencyRevokeReport,
  OpsHealthReport,
  ThresholdApprovalResponse,
  WalletDetails,
  WalletAnalyticsConsent,
  WalletAdminOperation,
  WalletStorageReportView,
  WalletSnapshotVerification,
  WalletApiConfig
} from "../services/walletApi";

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
  { id: "proof-center", label: "Proofs", icon: ShieldCheck },
  { id: "exports", label: "Exports", icon: LogOut },
  { id: "security", label: "Security", icon: LockKeyhole },
  { id: "audit", label: "Audit", icon: ClipboardCheck }
];

const serviceNeeds = ["Shelter", "Food", "Health", "Legal", "Benefits", "Transportation"];

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
  serviceNeeds: [] as string[],
  easyBotCheckStatus: "pending" as EasyBotCheckStatus,
  captchaToken: "",
  localPrecinctNotified: false,
  foundPermanentHousing: false
};

const disclosureScopes: Array<{ id: DisclosureDataScope; label: string; detail: string }> = [
  { id: "identity_minimum", label: "Minimum identity", detail: "Name, birth date, and contact status" },
  { id: "profile", label: "Profile", detail: "Basic profile details and service needs" },
  { id: "photo", label: "Photo", detail: "The account photo selected during setup" },
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
const WALLET_API_CONFIG_KEY = "abby-wallet-api-config";

const defaultShelterChecklist = {
  userPresent: false,
  clearBrowserData: false,
  auditLogConfirmed: false
};

type PersistedAppState = {
  profile?: RegistrationProfileDraft;
  policy?: typeof defaultCheckInPolicy;
  recipients?: DisclosureRecipientDraft[];
  uploads?: UploadItem[];
  shelterStaffAccounts?: ShelterStaffAccount[];
  shelterUserAccounts?: ShelterUserAccount[];
  benefitsOptIn?: boolean;
  analyticsOptIn?: Record<string, boolean>;
  shelterChecklist?: typeof defaultShelterChecklist;
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
    Array.isArray(persistedState.recipients) ? persistedState.recipients : initialRecipients
  );
  const [uploads, setUploads] = useState<UploadItem[]>(() =>
    Array.isArray(persistedState.uploads) ? persistedState.uploads : initialUploads
  );
  const [accessRequests, setAccessRequests] = useState<WalletAccessRequest[]>(initialAccessRequests);
  const [shelterStaffAccounts, setShelterStaffAccounts] = useState<ShelterStaffAccount[]>(() =>
    Array.isArray(persistedState.shelterStaffAccounts) ? persistedState.shelterStaffAccounts : []
  );
  const [shelterUserAccounts, setShelterUserAccounts] = useState<ShelterUserAccount[]>(() =>
    Array.isArray(persistedState.shelterUserAccounts) ? persistedState.shelterUserAccounts : []
  );
  const [grantReceipts, setGrantReceipts] = useState<WalletGrantReceipt[]>(initialGrantReceipts);
  const [walletAuditEvents, setWalletAuditEvents] = useState<AuditEvent[]>(auditEvents);
  const [walletProofReceipts, setWalletProofReceipts] = useState<ProofReceiptView[]>(proofReceipts);
  const [exportBundleViews, setExportBundleViews] = useState<ExportBundleView[]>(exportBundles);
  const [recipientVerified, setRecipientVerified] = useState(false);
  const [benefitsOptIn, setBenefitsOptIn] = useState(() => persistedState.benefitsOptIn ?? false);
  const [analyticsOptIn, setAnalyticsOptIn] = useState<Record<string, boolean>>(() =>
    persistedState.analyticsOptIn && typeof persistedState.analyticsOptIn === "object"
      ? persistedState.analyticsOptIn
      : {}
  );
  const [shelterChecklist, setShelterChecklist] = useState(() => ({
    ...defaultShelterChecklist,
    ...persistedState.shelterChecklist
  }));
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const walletApiConfig = useMemo(readWalletApiConfig, []);

  async function refreshWalletAccessState() {
    if (!walletApiConfig) return;
    const walletState = await loadWalletAccessState(walletApiConfig);
    setAccessRequests(walletState.accessRequests);
    setGrantReceipts(walletState.grantReceipts);
  }

  async function refreshWalletAuditEvents() {
    if (!walletApiConfig) return;
    const events = await listWalletAuditEvents(walletApiConfig);
    setWalletAuditEvents(events.length ? events : auditEvents);
  }

  async function refreshWalletDocuments() {
    if (!walletApiConfig) return;
    const documents = await listWalletDocuments(walletApiConfig);
    setUploads(documents.length ? documents : initialUploads);
  }

  async function refreshWalletProofReceipts() {
    if (!walletApiConfig) return;
    const proofs = await listWalletProofReceipts(walletApiConfig);
    setWalletProofReceipts(proofs.length ? proofs : proofReceipts);
  }

  async function refreshWalletAfterSnapshotLoad() {
    if (!walletApiConfig) return;
    await Promise.all([
      refreshWalletAccessState().catch(() => {
        setAccessRequests(initialAccessRequests);
        setGrantReceipts(initialGrantReceipts);
      }),
      refreshWalletAuditEvents().catch(() => setWalletAuditEvents(auditEvents)),
      refreshWalletDocuments().catch(() => setUploads(initialUploads)),
      refreshWalletProofReceipts().catch(() => setWalletProofReceipts(proofReceipts))
    ]);
  }

  useEffect(() => {
    const syncRouteFromHash = () => {
      setActiveRoute(getRouteFromHash());
      setMobileNavOpen(false);
    };
    window.addEventListener("hashchange", syncRouteFromHash);
    return () => window.removeEventListener("hashchange", syncRouteFromHash);
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    window.localStorage.setItem(
      APP_PERSIST_KEY,
      JSON.stringify({
        profile,
        policy,
        recipients,
        uploads,
        shelterStaffAccounts,
        shelterUserAccounts,
        benefitsOptIn,
        analyticsOptIn,
        shelterChecklist
      })
    );
  }, [
    analyticsOptIn,
    benefitsOptIn,
    policy,
    profile,
    recipients,
    shelterChecklist,
    shelterStaffAccounts,
    shelterUserAccounts,
    uploads
  ]);

  useEffect(() => {
    if (!walletApiConfig) return;
    refreshWalletAccessState().catch(() => {
      setAccessRequests(initialAccessRequests);
      setGrantReceipts(initialGrantReceipts);
    });
  }, [walletApiConfig]);

  useEffect(() => {
    if (!walletApiConfig) return;
    refreshWalletDocuments().catch(() => setUploads(initialUploads));
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
    window.location.hash = route === "home" ? "#/" : `#/${route}`;
    setActiveRoute(route);
    setMobileNavOpen(false);
  }

  const nextCheckIn = useMemo(() => {
    const next = new Date(policy.lastCheckInAt);
    next.setDate(next.getDate() + policy.intervalDays);
    return next.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
  }, [policy.intervalDays, policy.lastCheckInAt]);

  return (
    <div className="app">
      <aside className="sidebar" aria-label="Primary navigation">
        <div className="brand">
          <span className="brand-mark">A</span>
          <div>
            <strong>Abby</strong>
            <small>Safety and services</small>
          </div>
        </div>
        <nav className="nav-list">
          {routes.map((route) => (
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
            {[...routes, ...secondaryRoutes].map((route) => (
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
            setProfile={setProfile}
            shelterStaffAccounts={shelterStaffAccounts}
            setShelterStaffAccounts={setShelterStaffAccounts}
          />
        ) : null}
        {activeRoute === "check-in" ? (
          <CheckInScreen nextCheckIn={nextCheckIn} policy={policy} setPolicy={setPolicy} />
        ) : null}
        {activeRoute === "contacts" ? <ContactsScreen recipients={recipients} setRecipients={setRecipients} /> : null}
        {activeRoute === "sharing-rules" ? (
          <SharingRulesScreen recipients={recipients} setRecipients={setRecipients} />
        ) : null}
        {activeRoute === "uploads" ? (
          <UploadsScreen
            apiConfig={walletApiConfig}
            refreshWalletAccessState={refreshWalletAccessState}
            refreshWalletAuditEvents={refreshWalletAuditEvents}
            uploads={uploads}
            setUploads={setUploads}
          />
        ) : null}
        {activeRoute === "social-services" ? <SocialServicesScreen /> : null}
        {activeRoute === "shelter" ? (
          <ShelterScreen
            checklist={shelterChecklist}
            setChecklist={setShelterChecklist}
            shelterStaffAccounts={shelterStaffAccounts}
            setShelterStaffAccounts={setShelterStaffAccounts}
            shelterUserAccounts={shelterUserAccounts}
            setShelterUserAccounts={setShelterUserAccounts}
          />
        ) : null}
        {activeRoute === "recipient-access" ? (
          <RecipientAccessScreen
            accessRequests={accessRequests}
            apiConfig={walletApiConfig}
            grantReceipts={grantReceipts}
            recipients={recipients}
            refreshWalletAuditEvents={refreshWalletAuditEvents}
            refreshWalletAccessState={refreshWalletAccessState}
            setAccessRequests={setAccessRequests}
            setGrantReceipts={setGrantReceipts}
            verified={recipientVerified}
            setVerified={setRecipientVerified}
          />
        ) : null}
        {activeRoute === "benefits-protection" ? (
          <BenefitsProtectionScreen optedIn={benefitsOptIn} setOptedIn={setBenefitsOptIn} />
        ) : null}
        {activeRoute === "analytics" ? (
          <AnalyticsScreen
            apiConfig={walletApiConfig}
            optedIn={analyticsOptIn}
            refreshWalletAuditEvents={refreshWalletAuditEvents}
            setOptedIn={setAnalyticsOptIn}
          />
        ) : null}
        {activeRoute === "proof-center" ? (
          <ProofCenterScreen
            apiConfig={walletApiConfig}
            proofs={walletProofReceipts}
            refreshWalletAuditEvents={refreshWalletAuditEvents}
            setProofs={setWalletProofReceipts}
          />
        ) : null}
        {activeRoute === "exports" ? (
          <ExportCenterScreen
            apiConfig={walletApiConfig}
            bundles={exportBundleViews}
            setBundles={setExportBundleViews}
          />
        ) : null}
        {activeRoute === "security" ? (
          <SecurityScreen
            apiConfig={walletApiConfig}
            onSnapshotLoaded={refreshWalletAfterSnapshotLoad}
            refreshWalletAuditEvents={refreshWalletAuditEvents}
          />
        ) : null}
        {activeRoute === "audit" ? <AuditScreen events={walletAuditEvents} /> : null}
      </main>
    </div>
  );
}

function readWalletApiConfig(): WalletApiConfig | undefined {
  const apiBaseUrl = import.meta.env.VITE_WALLET_API_BASE_URL as string | undefined;
  const walletId = import.meta.env.VITE_DEMO_WALLET_ID as string | undefined;
  const envConfig =
    apiBaseUrl && walletId
      ? {
          apiBaseUrl,
          walletId,
          actorDid: import.meta.env.VITE_DEMO_ACTOR_DID as string | undefined,
          issuerKeyHex: import.meta.env.VITE_DEMO_ISSUER_KEY_HEX as string | undefined,
          audienceKeyHex: import.meta.env.VITE_DEMO_AUDIENCE_KEY_HEX as string | undefined
        }
      : undefined;
  return envConfig ?? readUrlWalletApiConfig() ?? readStoredWalletApiConfig();
}

function readUrlWalletApiConfig(): WalletApiConfig | undefined {
  if (typeof window === "undefined") return undefined;
  const params = new URL(window.location.href).searchParams;
  const apiBaseUrl = params.get("walletApiBaseUrl") ?? undefined;
  const walletId = params.get("walletId") ?? undefined;
  if (!apiBaseUrl || !walletId) return undefined;
  return {
    apiBaseUrl,
    walletId,
    actorDid: params.get("actorDid") ?? undefined,
    issuerKeyHex: params.get("issuerKeyHex") ?? undefined,
    audienceKeyHex: params.get("audienceKeyHex") ?? undefined
  };
}

function readStoredWalletApiConfig(): WalletApiConfig | undefined {
  if (typeof window === "undefined") return undefined;
  try {
    const storedConfig = JSON.parse(window.localStorage.getItem(WALLET_API_CONFIG_KEY) ?? "null") as Partial<
      WalletApiConfig
    > | null;
    if (!storedConfig?.apiBaseUrl || !storedConfig.walletId) return undefined;
    return {
      apiBaseUrl: storedConfig.apiBaseUrl,
      walletId: storedConfig.walletId,
      actorDid: storedConfig.actorDid,
      issuerKeyHex: storedConfig.issuerKeyHex,
      audienceKeyHex: storedConfig.audienceKeyHex
    };
  } catch {
    return undefined;
  }
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
  return (
    <div className="screen home-screen">
      <div className="page-title">
        <p className="eyebrow">Today</p>
        <h1>Your safety plan</h1>
      </div>
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
      <button className="checkin-panel" onClick={() => navigate("check-in")}>
        <div className="checkin-panel-icon"><CalendarCheck size={24} aria-hidden="true" /></div>
        <div className="checkin-panel-text">
          <span className="checkin-panel-label">Next check-in</span>
          <span className="checkin-panel-value">{nextCheckIn}</span>
        </div>
        <span className="checkin-panel-cta">Check in now</span>
      </button>
      <Section title="Quick actions">
        <div className="quick-actions">
          <Button onClick={() => navigate("sharing-rules")} variant="secondary">
            <ShieldCheck size={18} /> Review sharing
          </Button>
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
          <button className="home-footer-link" onClick={() => navigate("sharing-rules")}>Review due</button>
        </div>
      </div>
    </div>
  );
}

function StatusPanel({ label, value, tone, onClick }: { label: string; value: string; tone: string; onClick?: () => void }) {
  return (
    <div className={`status-panel panel-${tone}${onClick ? " status-panel-clickable" : ""}`} onClick={onClick} role={onClick ? "button" : undefined} tabIndex={onClick ? 0 : undefined} onKeyDown={onClick ? (e) => (e.key === "Enter" || e.key === " ") && onClick() : undefined}>
      <small>{label}</small>
      <strong>{value}</strong>
    </div>
  );
}

function RegistrationScreen({
  profile,
  setProfile,
  shelterStaffAccounts,
  setShelterStaffAccounts
}: {
  profile: RegistrationProfileDraft;
  setProfile: (profile: RegistrationProfileDraft) => void;
  shelterStaffAccounts: ShelterStaffAccount[];
  setShelterStaffAccounts: (accounts: ShelterStaffAccount[]) => void;
}) {
  const update = (patch: Partial<RegistrationProfileDraft>) => setProfile({ ...profile, ...patch });
  const [photoPreviewUrl, setPhotoPreviewUrl] = useState("");
  const [photoPreviewLabel, setPhotoPreviewLabel] = useState("");
  const [showPhotoPreview, setShowPhotoPreview] = useState(false);
  const [isShelterStaff, setIsShelterStaff] = useState(false);
  const [selectedShelter, setSelectedShelter] = useState("");
  const [shelterPin, setShelterPin] = useState("");
  const [currentStaffAccountId, setCurrentStaffAccountId] = useState("");

  const currentStaffAccount = shelterStaffAccounts.find((account) => account.id === currentStaffAccountId);
  const staffVerified = Boolean(currentStaffAccount?.verified);

  async function handleProfileUploadChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    update({ photoAssetId: file?.name ?? "" });

    if (!file) {
      setPhotoPreviewUrl("");
      setPhotoPreviewLabel("");
      setShowPhotoPreview(false);
      return;
    }

    setShowPhotoPreview(false);

    try {
      if (file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf")) {
        const { getDocument, GlobalWorkerOptions } = await import("pdfjs-dist");
        GlobalWorkerOptions.workerSrc = new URL("pdfjs-dist/build/pdf.worker.min.mjs", import.meta.url).toString();

        const bytes = await file.arrayBuffer();
        const pdf = await getDocument({ data: bytes }).promise;
        const firstPage = await pdf.getPage(1);
        const viewport = firstPage.getViewport({ scale: 1.2 });
        const canvas = document.createElement("canvas");
        const context = canvas.getContext("2d");
        if (!context) throw new Error("Canvas unavailable");

        canvas.width = Math.ceil(viewport.width);
        canvas.height = Math.ceil(viewport.height);
        await firstPage.render({ canvas: canvas as HTMLCanvasElement, canvasContext: context, viewport }).promise;

        setPhotoPreviewUrl(canvas.toDataURL("image/png"));
        setPhotoPreviewLabel("PDF first page preview");
        return;
      }

      if (file.type.startsWith("image/")) {
        const fileReader = new FileReader();
        fileReader.onload = () => {
          setPhotoPreviewUrl(String(fileReader.result || ""));
          setPhotoPreviewLabel("Selected image preview");
        };
        fileReader.readAsDataURL(file);
        return;
      }
    } catch {
      setPhotoPreviewUrl("");
      setPhotoPreviewLabel("Preview unavailable for this file.");
      return;
    }

    setPhotoPreviewUrl("");
    setPhotoPreviewLabel("Preview unavailable for this file.");
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
        <Field help="Used for emergency identity matching." label="Legal or full name" required>
          <input value={profile.legalName} onChange={(event) => update({ legalName: event.target.value })} />
        </Field>
        <Field help="Shown in the app when provided." label="Preferred name">
          <input value={profile.preferredName} onChange={(event) => update({ preferredName: event.target.value })} />
        </Field>
        <Field help="e.g. she/her, he/him, they/them — optional and not shared without permission." label="Pronouns">
          <input value={profile.pronouns} onChange={(event) => update({ pronouns: event.target.value })} />
        </Field>
        <Field help="Required to distinguish people with similar names." label="Birth date" required>
          <input
            type="date"
            value={profile.dateOfBirth}
            onChange={(event) => update({ dateOfBirth: event.target.value })}
          />
        </Field>
        <Field help="Use camera on mobile, upload an image, or upload a PDF photo ID." label="Photo or photo ID" required>
          <input
            accept="image/*,.pdf,application/pdf"
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
        <hr className="form-divider full-span" />
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
            value={profile.shelterAffiliation}
            onChange={(event) => update({ shelterAffiliation: event.target.value })}
          />
        </Field>
        <div className="full-span">
          <span className="field-label">Service needs</span>
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
            checked={profile.easyBotCheckStatus === "passed"}
            onChange={(event) =>
              update({ easyBotCheckStatus: event.target.checked ? "passed" : "failed", captchaToken: "" })
            }
            type="checkbox"
          />
          <span>Quick health check complete (step 1)</span>
        </label>
        <label className="captcha-box full-span">
          <input
            checked={Boolean(profile.captchaToken)}
            disabled={profile.easyBotCheckStatus !== "passed"}
            onChange={(event) => update({ captchaToken: event.target.checked ? "mock-captcha-token" : "" })}
            type="checkbox"
          />
          <span>Bot check complete (step 2)</span>
        </label>
        <label className="consent-box full-span">
          <input
            checked={isShelterStaff}
            onChange={(event) => {
              const checked = event.target.checked;
              setIsShelterStaff(checked);
              if (!checked) {
                setSelectedShelter("");
                setShelterPin("");
                setCurrentStaffAccountId("");
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
                  setSelectedShelter(event.target.value);
                  setCurrentStaffAccountId("");
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
                placeholder="Enter PIN"
                value={shelterPin}
                onChange={(event) => setShelterPin(event.target.value)}
              />
            </Field>
            <div>
              <Button
                disabled={!selectedShelter || !shelterPin.trim()}
                onClick={() => {
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
                    setCurrentStaffAccountId(existingAccount.id);
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
                  setCurrentStaffAccountId(createdAccount.id);
                }}
                type="button"
              >
                Verify shelter staff
              </Button>
              {staffVerified ? <small className="pin-request-note">Shelter staff verified.</small> : null}
              {!staffVerified && currentStaffAccountId ? (
                <small className="pin-request-note">Verification revoked by shelter administrator.</small>
              ) : null}
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
        <div className="form-grid">
          <Field help="Choose 1 to 30 days." label="Interval days" required>
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
          <Field help="Time after a missed check-in before escalation starts." label="Grace period hours">
            <input
              min={0}
              type="number"
              value={policy.gracePeriodHours}
              onChange={(event) => update({ gracePeriodHours: Number(event.target.value || 0) })}
            />
          </Field>
        </div>
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
          <CalendarCheck aria-hidden="true" size={28} />
          <div>
            <small>Next check-in</small>
            <strong>{nextCheckIn}</strong>
          </div>
        </div>
        <Button onClick={() => update({ lastCheckInAt: new Date().toISOString() })}>
          <Bell size={18} /> Check in now
        </Button>
      </Section>
    </div>
  );
}

function ContactsScreen({
  recipients,
  setRecipients
}: {
  recipients: DisclosureRecipientDraft[];
  setRecipients: (recipients: DisclosureRecipientDraft[]) => void;
}) {
  const [draft, setDraft] = useState({
    displayName: "",
    relationship: "",
    email: "",
    phone: "",
    type: "emergency_contact" as DisclosureRecipientType
  });

  function addRecipient(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!draft.displayName) return;
    setRecipients([
      ...recipients,
      {
        id: `rec-${Date.now()}`,
        ...draft,
        agencyName: "",
        precinctName: "",
        verified: false,
        allowedScopes: ["identity_minimum", "photo"]
      }
    ]);
    setDraft({ displayName: "", relationship: "", email: "", phone: "", type: "emergency_contact" });
  }

  return (
    <div className="screen">
      <div className="page-title">
        <p className="eyebrow">Emergency contacts</p>
        <h1>People and agencies</h1>
      </div>
      <div className="list-stack">
        {recipients.map((recipient) => (
          <article className="list-item recipient-list-item" key={recipient.id}>
            <div>
              <h3>{recipient.displayName}</h3>
              <p>{recipient.relationship || recipient.agencyName || recipient.type.replace("_", " ")}</p>
              <div className="badge-row">
                <Badge tone={recipient.verified ? "success" : "warning"}>
                  {recipient.verified ? "Verified" : "Needs verification"}
                </Badge>
                <Badge>{recipient.allowedScopes.length} scopes</Badge>
              </div>
            </div>
            <Button
              ariaLabel={`Remove ${recipient.displayName}`}
              className="compact-list-action"
              onClick={() => setRecipients(recipients.filter((item) => item.id !== recipient.id))}
              variant="quiet"
            >
              Remove
            </Button>
          </article>
        ))}
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
            </select>
          </Field>
          <div className="full-span">
            <Button type="submit">
              <UsersRound size={18} /> Add recipient
            </Button>
          </div>
        </form>
      </Section>
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
          ? {
              ...recipient,
              allowedScopes: recipient.allowedScopes.includes(scope)
                ? recipient.allowedScopes.filter((item) => item !== scope)
                : [...recipient.allowedScopes, scope]
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
      <StatusBanner tone="info">No recipient receives new information unless a scope is selected here.</StatusBanner>
      <div className="list-stack">
        {recipients.map((recipient) => (
          <article className="scope-editor" key={recipient.id}>
            <div className="scope-header">
              <div>
                <h3>{recipient.displayName}</h3>
                <p>{recipient.type.replace("_", " ")}</p>
              </div>
              <Badge>{recipient.allowedScopes.length} selected</Badge>
            </div>
            <div className="scope-grid">
              {disclosureScopes.map((scope) => (
                <label className="scope-option" key={scope.id}>
                  <input
                    checked={recipient.allowedScopes.includes(scope.id)}
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
            <div
              className="capability-preview"
              role="group"
              aria-label={`${recipient.displayName} sharing capability preview`}
            >
              <div className="scope-header">
                <div>
                  <h4>Capability preview</h4>
                  <p>{recipient.allowedScopes.length} selected scopes</p>
                </div>
                <Badge tone={recipient.allowedScopes.length > 0 ? "success" : "warning"}>
                  {recipient.allowedScopes.length > 0 ? "bounded share" : "no access"}
                </Badge>
              </div>
              <div className="disclosure-package">
                <div className="disclosure-row">
                  <strong>Abilities</strong>
                  <span>{capabilitySummary(abilitiesForDisclosureScopes(recipient.allowedScopes))}</span>
                </div>
                <div className="disclosure-row">
                  <strong>Scopes</strong>
                  <span>{recipient.allowedScopes.join(", ") || "No scopes selected"}</span>
                </div>
                <div className="disclosure-row">
                  <strong>Not granted</strong>
                  <span>{nonGrantedCapabilities(abilitiesForDisclosureScopes(recipient.allowedScopes)).join(", ")}</span>
                </div>
              </div>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

type UploadSharePermission = "analyze" | "view" | "analyze_view" | "analyze_view_share";

interface UploadShareDraft {
  audienceDid: string;
  audienceKeyHex: string;
  permission: UploadSharePermission;
  purpose: string;
  expiresAt: string;
  approvalId: string;
  requirePresence: boolean;
}

function defaultUploadShareDraft(): UploadShareDraft {
  return {
    audienceDid: "",
    audienceKeyHex: "",
    permission: "analyze",
    purpose: "service_matching",
    expiresAt: "",
    approvalId: "",
    requirePresence: false
  };
}

function uploadShareAbilities(permission: UploadSharePermission): string[] {
  if (permission === "view") return ["record/decrypt"];
  if (permission === "analyze_view") return ["record/analyze", "record/decrypt"];
  if (permission === "analyze_view_share") return ["record/analyze", "record/decrypt", "record/share"];
  return ["record/analyze"];
}

function uploadShareNeedsApproval(permission: UploadSharePermission) {
  return uploadShareAbilities(permission).some((ability) => ability === "record/decrypt" || ability === "record/share");
}

function uploadShareCanRequirePresence(permission: UploadSharePermission) {
  return uploadShareAbilities(permission).includes("record/decrypt");
}

function receiptRequiresUserPresence(receipt: WalletGrantReceipt) {
  return Boolean(receipt.caveats?.user_presence_required || receipt.caveats?.require_user_presence);
}

function UploadsScreen({
  apiConfig,
  refreshWalletAccessState,
  refreshWalletAuditEvents,
  uploads,
  setUploads
}: {
  apiConfig?: WalletApiConfig;
  refreshWalletAccessState: () => Promise<void>;
  refreshWalletAuditEvents: () => Promise<void>;
  uploads: UploadItem[];
  setUploads: (uploads: UploadItem[]) => void;
}) {
  const [repairingUploadIds, setRepairingUploadIds] = useState<string[]>([]);
  const [rotatingUploadIds, setRotatingUploadIds] = useState<string[]>([]);
  const [viewingUploadIds, setViewingUploadIds] = useState<string[]>([]);
  const [decryptedUploadsById, setDecryptedUploadsById] = useState<Record<string, DecryptedRecordView>>({});
  const [shareDraftsById, setShareDraftsById] = useState<Record<string, UploadShareDraft>>({});
  const [sharingUploadIds, setSharingUploadIds] = useState<string[]>([]);
  const [requestingShareApprovalIds, setRequestingShareApprovalIds] = useState<string[]>([]);
  const [shareMessagesById, setShareMessagesById] = useState<Record<string, string>>({});

  function shareDraftFor(upload: UploadItem) {
    return shareDraftsById[upload.id] ?? defaultUploadShareDraft();
  }

  function updateShareDraft(upload: UploadItem, patch: Partial<UploadShareDraft>) {
    setShareDraftsById((drafts) => ({
      ...drafts,
      [upload.id]: {
        ...(drafts[upload.id] ?? defaultUploadShareDraft()),
        ...patch
      }
    }));
  }

  async function addUpload(file: File | null) {
    if (!file) return;
    const machineSummary = await generateUploadSummary(file);
    if (apiConfig?.actorDid) {
      try {
        const uploaded = await addBinaryDocument(apiConfig, { file, title: machineSummary });
        setUploads([uploaded, ...uploads]);
        await refreshWalletAuditEvents();
        return;
      } catch {
        try {
          const uploaded = await addTextDocument(apiConfig, {
            filename: file.name,
            text: await file.text(),
            title: machineSummary
          });
          setUploads([uploaded, ...uploads]);
          await refreshWalletAuditEvents();
          return;
        } catch {
          // Keep local document capture available if the configured API is unavailable.
        }
      }
    }
    setUploads([
      ...uploads,
      {
        id: `up-${Date.now()}`,
        fileName: file.name,
        machineSummary,
        category: "Uncategorized",
        sensitivity: "high",
        status: "stored",
        shared: false
      }
    ]);
  }

  async function repairUploadStorage(upload: UploadItem) {
    if (!apiConfig?.actorDid || !upload.recordId) return;
    setRepairingUploadIds((uploadIds) => [...uploadIds, upload.id]);
    try {
      const storageOk = await repairRecordStorage(apiConfig, upload.recordId);
      setUploads(
        uploads.map((item) =>
          item.id === upload.id
            ? {
                ...item,
                status: storageOk ? "stored" : item.status,
                storageOk
              }
            : item
        )
      );
      await refreshWalletAuditEvents();
    } catch {
      setUploads(uploads.map((item) => (item.id === upload.id ? { ...item, storageOk: false } : item)));
    } finally {
      setRepairingUploadIds((uploadIds) => uploadIds.filter((id) => id !== upload.id));
    }
  }

  async function rotateUploadKey(upload: UploadItem) {
    if (!apiConfig?.actorDid || !upload.recordId) return;
    setRotatingUploadIds((uploadIds) => [...uploadIds, upload.id]);
    try {
      await rotateRecordKey(apiConfig, upload.recordId);
      await refreshWalletAuditEvents();
    } finally {
      setRotatingUploadIds((uploadIds) => uploadIds.filter((id) => id !== upload.id));
    }
  }

  async function viewUpload(upload: UploadItem) {
    if (!apiConfig?.actorDid || !upload.recordId) return;
    setViewingUploadIds((uploadIds) => [...uploadIds, upload.id]);
    try {
      const decrypted = await decryptRecordWithGrant(apiConfig, { recordId: upload.recordId });
      setDecryptedUploadsById({
        ...decryptedUploadsById,
        [upload.id]: decrypted
      });
      await refreshWalletAuditEvents();
    } catch {
      setDecryptedUploadsById({
        ...decryptedUploadsById,
        [upload.id]: {
          recordId: upload.recordId,
          text: "Document view unavailable.",
          sizeBytes: 0
        }
      });
    } finally {
      setViewingUploadIds((uploadIds) => uploadIds.filter((id) => id !== upload.id));
    }
  }

  async function shareUpload(event: FormEvent<HTMLFormElement>, upload: UploadItem) {
    event.preventDefault();
    if (!apiConfig?.actorDid || !upload.recordId) return;
    const draft = shareDraftFor(upload);
    const audienceDid = draft.audienceDid.trim();
    if (!audienceDid) return;
    setSharingUploadIds((uploadIds) => [...uploadIds, upload.id]);
    setShareMessagesById({ ...shareMessagesById, [upload.id]: "" });
    try {
      const grant = await createRecordGrant(apiConfig, {
        recordId: upload.recordId,
        audienceDid,
        audienceKeyHex: draft.audienceKeyHex.trim() || undefined,
        abilities: uploadShareAbilities(draft.permission),
        purpose: draft.purpose.trim() || "service_matching",
        expiresAt: dateInputValueToIso(draft.expiresAt),
        approvalId: draft.approvalId.trim() || undefined,
        maxDelegationDepth: draft.permission === "analyze_view_share" ? 1 : undefined,
        userPresenceRequired: uploadShareCanRequirePresence(draft.permission) ? draft.requirePresence : false
      });
      setUploads(uploads.map((item) => (item.id === upload.id ? { ...item, shared: true } : item)));
      setShareDraftsById({
        ...shareDraftsById,
        [upload.id]: defaultUploadShareDraft()
      });
      setShareMessagesById({
        ...shareMessagesById,
        [upload.id]: `Shared with ${audienceDid}: ${grant.abilities.join(", ")}.`
      });
      await refreshWalletAccessState();
      await refreshWalletAuditEvents();
    } catch {
      setShareMessagesById({
        ...shareMessagesById,
        [upload.id]: "Document share failed. Check the DID, key, or required approval."
      });
    } finally {
      setSharingUploadIds((uploadIds) => uploadIds.filter((id) => id !== upload.id));
    }
  }

  async function requestShareApproval(upload: UploadItem) {
    if (!apiConfig?.actorDid || !upload.recordId) return;
    const draft = shareDraftFor(upload);
    const abilities = uploadShareAbilities(draft.permission);
    setRequestingShareApprovalIds((uploadIds) =>
      uploadIds.includes(upload.id) ? uploadIds : [...uploadIds, upload.id]
    );
    setShareMessagesById((messages) => ({ ...messages, [upload.id]: "" }));
    try {
      const approval = await requestRecordGrantApproval(apiConfig, {
        recordId: upload.recordId,
        abilities,
        requestedBy: apiConfig.actorDid,
        expiresAt: dateInputValueToIso(draft.expiresAt)
      });
      updateShareDraft(upload, { approvalId: approval.approval_id });
      setShareMessagesById((messages) => ({
        ...messages,
        [upload.id]: `Approval ${approval.approval_id} requested.`
      }));
    } catch {
      setShareMessagesById((messages) => ({ ...messages, [upload.id]: "Approval request failed." }));
    } finally {
      setRequestingShareApprovalIds((uploadIds) => uploadIds.filter((id) => id !== upload.id));
    }
  }

  return (
    <div className="screen">
      <div className="page-title">
        <p className="eyebrow">Uploads</p>
        <h1>Document and information vault</h1>
      </div>
      <Section title="Add information">
        <label className="upload-dropzone">
          <Upload aria-hidden="true" size={28} />
          <span>Choose a file or photo</span>
          <small>Stored items stay private until added to a sharing rule.</small>
          <span className="upload-picker">
            <FileUp aria-hidden="true" size={18} /> Select file
          </span>
          <input
            type="file"
            onChange={(event) => addUpload(event.target.files?.[0] ?? null)}
            aria-label="Choose file to upload"
          />
        </label>
      </Section>
      <div className="list-stack">
        {uploads.map((upload) => {
          const decryptedUpload = decryptedUploadsById[upload.id];
          const shareDraft = shareDraftFor(upload);
          const shareFormOpen = Boolean(shareDraftsById[upload.id]);
          const shareMessage = shareMessagesById[upload.id];
          const shareApprovalRequired = uploadShareNeedsApproval(shareDraft.permission);
          const sharePresenceAvailable = uploadShareCanRequirePresence(shareDraft.permission);
          return (
            <article className="list-item upload-list-item" key={upload.id}>
              <div className="upload-list-main">
                <div>
                  <h3>{upload.fileName}</h3>
                  <p>{upload.category}</p>
                  <small className="upload-machine-summary">{toShortSummaryTitle(upload.machineSummary)}</small>
                  <div className="badge-row">
                    <Badge tone="success">{upload.status}</Badge>
                    <Badge tone="warning">{upload.sensitivity}</Badge>
                    {upload.storageOk !== undefined ? (
                      <Badge tone={upload.storageOk ? "success" : "warning"}>
                        {upload.storageOk ? "storage verified" : "storage needs repair"}
                      </Badge>
                    ) : null}
                    <Badge>{upload.shared ? "Shared" : "Private"}</Badge>
                  </div>
                </div>
                <div className="row-actions list-item-action">
                  {upload.recordId && apiConfig?.actorDid ? (
                    <Button
                      onClick={() => updateShareDraft(upload, {})}
                      variant="secondary"
                    >
                      <UserPlus aria-hidden="true" size={18} />
                      Share document
                    </Button>
                  ) : null}
                  {upload.recordId && apiConfig?.actorDid ? (
                    <Button
                      disabled={viewingUploadIds.includes(upload.id)}
                      onClick={() => viewUpload(upload)}
                      variant="secondary"
                    >
                      <LockKeyhole aria-hidden="true" size={18} />
                      {viewingUploadIds.includes(upload.id) ? "Opening" : "View document"}
                    </Button>
                  ) : null}
                  {upload.recordId && apiConfig?.actorDid ? (
                    <Button
                      disabled={rotatingUploadIds.includes(upload.id)}
                      onClick={() => rotateUploadKey(upload)}
                      variant="secondary"
                    >
                      <KeyRound aria-hidden="true" size={18} />
                      {rotatingUploadIds.includes(upload.id) ? "Rotating" : "Rotate key"}
                    </Button>
                  ) : null}
                  {upload.storageOk === false && upload.recordId && apiConfig?.actorDid ? (
                    <Button
                      disabled={repairingUploadIds.includes(upload.id)}
                      onClick={() => repairUploadStorage(upload)}
                      variant="secondary"
                    >
                      <Wrench aria-hidden="true" size={18} />
                      {repairingUploadIds.includes(upload.id) ? "Repairing" : "Repair storage"}
                    </Button>
                  ) : null}
                  <Button
                    onClick={() =>
                      setUploads(
                        uploads.map((item) => (item.id === upload.id ? { ...item, shared: !item.shared } : item))
                      )
                    }
                    variant="secondary"
                  >
                    {upload.shared ? "Mark private" : "Mark eligible"}
                  </Button>
                </div>
              </div>
              {shareFormOpen ? (
                <form className="form-grid" onSubmit={(event) => shareUpload(event, upload)}>
                  <Field label="Recipient DID" required>
                    <input
                      onChange={(event) => updateShareDraft(upload, { audienceDid: event.target.value })}
                      placeholder="did:key:case-worker"
                      value={shareDraft.audienceDid}
                    />
                  </Field>
                  <Field label="Permission">
                    <select
                      onChange={(event) =>
                        updateShareDraft(upload, { permission: event.target.value as UploadSharePermission })
                      }
                      value={shareDraft.permission}
                    >
                      <option value="analyze">Analyze only</option>
                      <option value="view">View document</option>
                      <option value="analyze_view">Analyze and view</option>
                      <option value="analyze_view_share">Analyze, view, and delegate</option>
                    </select>
                  </Field>
                  <Field label="Purpose">
                    <input
                      onChange={(event) => updateShareDraft(upload, { purpose: event.target.value })}
                      placeholder="service_matching"
                      value={shareDraft.purpose}
                    />
                  </Field>
                  <Field label="Expires">
                    <input
                      onChange={(event) => updateShareDraft(upload, { expiresAt: event.target.value })}
                      type="date"
                      value={shareDraft.expiresAt}
                    />
                  </Field>
                  <Field label="Recipient key hex">
                    <input
                      onChange={(event) => updateShareDraft(upload, { audienceKeyHex: event.target.value })}
                      placeholder="optional"
                      value={shareDraft.audienceKeyHex}
                    />
                  </Field>
                  <Field label="Approval ID">
                    <input
                      onChange={(event) => updateShareDraft(upload, { approvalId: event.target.value })}
                      placeholder="optional for multi-sig"
                      value={shareDraft.approvalId}
                    />
                  </Field>
                  {sharePresenceAvailable ? (
                    <label className="captcha-box full-span">
                      <input
                        checked={shareDraft.requirePresence}
                        onChange={(event) => updateShareDraft(upload, { requirePresence: event.target.checked })}
                        type="checkbox"
                      />
                      <span>Require recipient presence before viewing</span>
                    </label>
                  ) : null}
                  <div className="row-actions full-span">
                    {shareApprovalRequired ? (
                      <Button
                        disabled={requestingShareApprovalIds.includes(upload.id)}
                        onClick={() => requestShareApproval(upload)}
                        type="button"
                        variant="secondary"
                      >
                        <ShieldCheck aria-hidden="true" size={18} />
                        {requestingShareApprovalIds.includes(upload.id) ? "Requesting" : "Request approval"}
                      </Button>
                    ) : null}
                    <Button
                      disabled={!shareDraft.audienceDid.trim() || sharingUploadIds.includes(upload.id)}
                      type="submit"
                      variant="secondary"
                    >
                      <ShieldCheck aria-hidden="true" size={18} />
                      {sharingUploadIds.includes(upload.id) ? "Sharing" : "Create grant"}
                    </Button>
                  </div>
                </form>
              ) : null}
              {shareMessage ? (
                <StatusBanner tone={shareMessage.includes("failed") ? "warning" : "success"}>
                  {shareMessage}
                </StatusBanner>
              ) : null}
              {decryptedUpload ? (
                <div className="disclosure-package">
                  <div className="disclosure-row">
                    <strong>Document view</strong>
                    <span className="document-preview-text">{decryptedUpload.text}</span>
                  </div>
                  <div className="disclosure-row">
                    <strong>Plaintext size</strong>
                    <span>{decryptedUpload.sizeBytes} bytes</span>
                  </div>
                </div>
              ) : null}
            </article>
          );
        })}
      </div>
    </div>
  );
}

type GraphRagUiStatus = "idle" | "loading" | "ready" | "error";

const defaultServiceGraphQuery = "emergency food, shelter, benefits, and crisis support";

function graphRagDocumentTitle(result: SearchResult): string {
  const document = result.document;
  return document.provider_name || document.program_name || document.title || result.docId;
}

function graphRagDocumentDetails(result: SearchResult): string {
  const document = result.document;
  const details = [
    document.program_name && document.program_name !== document.provider_name ? document.program_name : "",
    document.categories,
    [document.city, document.state].filter(Boolean).join(", "),
    document.host
  ].filter(Boolean);
  return details.length ? details.join(" · ") : document.doc_type;
}

function shortCid(cid: string): string {
  return cid.length > 18 ? `${cid.slice(0, 18)}...` : cid;
}

function graphRagStatusTone(ready: boolean): string {
  return ready ? "success" : "warning";
}

function graphRagBackendSummary(status: GraphRagRuntimeStatus): string {
  const capabilities = status.backend.capabilities;
  if (!capabilities) {
    return status.backend.error || "Backend detection unavailable";
  }
  return [
    capabilities.webgpu ? "WebGPU" : "",
    capabilities.webnn ? "WebNN detection" : "",
    capabilities.wasm ? "WASM" : "",
    capabilities.simd ? "SIMD" : "",
    capabilities.threads ? "threads" : "",
  ].filter(Boolean).join(" · ") || "JavaScript fallback";
}

function SocialServicesScreen() {
  const categories = ["Shelter", "Food", "Health", "Legal", "Benefits", "Transportation", "Employment", "Crisis"];
  const [query, setQuery] = useState(defaultServiceGraphQuery);
  const [selectedCategory, setSelectedCategory] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [answer, setAnswer] = useState<GraphRagAnswer | null>(null);
  const [searchStatus, setSearchStatus] = useState<GraphRagUiStatus>("idle");
  const [answerStatus, setAnswerStatus] = useState<GraphRagUiStatus>("idle");
  const [answerMode, setAnswerMode] = useState<"summary" | "model" | "">("");
  const [useHybridSearch, setUseHybridSearch] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const searchRequestIdRef = useRef(0);
  const answerRequestIdRef = useRef(0);
  const [runtimeStatus, setRuntimeStatus] = useState<GraphRagRuntimeStatus | null>(null);
  const [runtimeStatusLoading, setRuntimeStatusLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function loadRuntimeStatus() {
      setRuntimeStatusLoading(true);
      try {
        const nextStatus = await get211InfoRuntimeStatus();
        if (!cancelled) {
          setRuntimeStatus(nextStatus);
        }
      } catch (error) {
        if (!cancelled) {
          console.warn("211 GraphRAG runtime status failed", error);
        }
      } finally {
        if (!cancelled) {
          setRuntimeStatusLoading(false);
        }
      }
    }

    void loadRuntimeStatus();
    return () => {
      cancelled = true;
    };
  }, []);

  async function refreshRuntimeStatus() {
    setRuntimeStatusLoading(true);
    try {
      setRuntimeStatus(await get211InfoRuntimeStatus());
    } catch (error) {
      console.warn("211 GraphRAG runtime status refresh failed", error);
    } finally {
      setRuntimeStatusLoading(false);
    }
  }

  async function runGraphSearchFor(nextQuery: string) {
    const trimmedQuery = nextQuery.trim();
    const requestId = searchRequestIdRef.current + 1;
    searchRequestIdRef.current = requestId;
    answerRequestIdRef.current += 1;

    if (!trimmedQuery) {
      setErrorMessage("Enter a service need before searching the local 211 corpus.");
      setSearchStatus("error");
      return;
    }

    setErrorMessage("");
    setSearchStatus("loading");
    setAnswer(null);
    setAnswerStatus("idle");
    setAnswerMode("");

    try {
      const nextResults = await search211Info(trimmedQuery, 6, { useEmbedding: useHybridSearch });
      if (searchRequestIdRef.current !== requestId) {
        return;
      }
      setResults(nextResults);
      setSearchStatus("ready");
    } catch (error) {
      if (searchRequestIdRef.current !== requestId) {
        return;
      }
      console.error("211 GraphRAG search failed", error);
      setErrorMessage(error instanceof Error ? error.message : "The local 211 corpus search failed.");
      setSearchStatus("error");
    }
  }

  function runGraphSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSelectedCategory("");
    void runGraphSearchFor(query);
  }

  async function buildAnswer(useLocalModel: boolean) {
    const trimmedQuery = query.trim();
    const requestId = answerRequestIdRef.current + 1;
    answerRequestIdRef.current = requestId;

    if (!trimmedQuery) {
      setErrorMessage("Enter a service need before building a cited answer.");
      setAnswerStatus("error");
      return;
    }

    setErrorMessage("");
    setAnswerStatus("loading");
    setAnswerMode(useLocalModel ? "model" : "summary");

    try {
      const nextAnswer = await answer211InfoQuestion(trimmedQuery, {
        useLocalModel,
        useEmbedding: useHybridSearch,
        maxTokens: 220
      });
      if (answerRequestIdRef.current !== requestId) {
        return;
      }
      setAnswer(nextAnswer);
      setResults(nextAnswer.evidence.results);
      setSearchStatus("ready");
      setAnswerStatus("ready");
    } catch (error) {
      if (answerRequestIdRef.current !== requestId) {
        return;
      }
      console.error("211 GraphRAG answer failed", error);
      setErrorMessage(error instanceof Error ? error.message : "The local 211 GraphRAG answer failed.");
      setAnswerStatus("error");
    } finally {
      if (answerRequestIdRef.current === requestId) {
        setAnswerMode("");
      }
    }
  }

  return (
    <div className="screen">
      <div className="page-title">
        <p className="eyebrow">Social services</p>
        <h1>Find support</h1>
      </div>
      <div className="category-grid">
        {categories.map((category) => (
          <button
            aria-pressed={selectedCategory === category}
            className="category-tile"
            key={category}
            onClick={() => {
              setSelectedCategory(category);
              setQuery(category);
              void runGraphSearchFor(category);
            }}
            type="button"
          >
            <HeartHandshake aria-hidden="true" size={22} />
            <span>{category}</span>
          </button>
        ))}
      </div>
      <Section
        actions={
          <Badge tone={results.length > 0 ? "success" : "neutral"}>
            {results.length > 0 ? `${results.length} local matches` : "Local corpus"}
          </Badge>
        }
        eyebrow="Browser GraphRAG"
        title="Search the scraped 211 corpus"
      >
        <div className="graphrag-panel">
          <form className="graphrag-search-form" onSubmit={runGraphSearch}>
            <Field
              help="Searches the local 211 browser package with BM25, graph neighborhoods, and embeddings when available."
              label="Service need"
            >
              <input
                onChange={(event) => {
                  setQuery(event.target.value);
                  setSelectedCategory("");
                }}
                placeholder="food pantry near Beaverton, rental assistance, detox support"
                value={query}
              />
            </Field>
            <div className="graphrag-search-actions">
              <Button loading={searchStatus === "loading"} loadingLabel="Searching" type="submit">
                <Search aria-hidden="true" size={18} />
                Search corpus
              </Button>
              <Button
                disabled={answerStatus === "loading"}
                loading={answerStatus === "loading" && answerMode === "summary"}
                loadingLabel="Building answer"
                onClick={() => void buildAnswer(false)}
                variant="secondary"
              >
                Build cited answer
              </Button>
              <Button
                disabled={answerStatus === "loading"}
                loading={answerStatus === "loading" && answerMode === "model"}
                loadingLabel="Running model"
                onClick={() => void buildAnswer(true)}
                variant="secondary"
              >
                <Sparkles aria-hidden="true" size={18} />
                Try local model
              </Button>
            </div>
            <label className="graphrag-option">
              <input
                checked={useHybridSearch}
                onChange={(event) => setUseHybridSearch(event.target.checked)}
                type="checkbox"
              />
              <span>
                <strong>Use BGE-small hybrid vector search</strong>
                <small>Downloads the browser embedding model on first use; leave off for faster BM25 and graph search.</small>
              </span>
            </label>
            <div className="graphrag-runtime-panel" aria-label="GraphRAG runtime status">
              <div className="graphrag-runtime-heading">
                <div>
                  <strong>Runtime status</strong>
                  <small>
                    {runtimeStatus
                      ? `Corpus base: ${runtimeStatus.corpusBaseUrl}`
                      : runtimeStatusLoading
                        ? "Checking corpus, workers, and browser backend..."
                        : "Runtime status has not loaded yet."}
                  </small>
                </div>
                <Button
                  loading={runtimeStatusLoading}
                  loadingLabel="Checking"
                  onClick={() => void refreshRuntimeStatus()}
                  variant="secondary"
                >
                  <RefreshCw aria-hidden="true" size={16} />
                  Refresh status
                </Button>
              </div>
              {runtimeStatus ? (
                <div className="graphrag-runtime-grid">
                  <article>
                    <Badge tone={graphRagStatusTone(runtimeStatus.corpus.available)}>
                      {runtimeStatus.corpus.available ? "Corpus ready" : "Corpus unavailable"}
                    </Badge>
                    <strong>{runtimeStatus.corpus.documentCount.toLocaleString()} documents</strong>
                    <small>
                      {runtimeStatus.corpus.embeddingCount.toLocaleString()} vectors · {runtimeStatus.corpus.embeddingDimension}d ·{" "}
                      {runtimeStatus.corpus.graphNeighborhoodShardCount} graph shards
                    </small>
                  </article>
                  <article>
                    <Badge tone={graphRagStatusTone(runtimeStatus.retrievalWorker.ready)}>
                      {runtimeStatus.retrievalWorker.ready ? "Search worker ready" : "Search fallback"}
                    </Badge>
                    <strong>{runtimeStatus.retrievalWorker.hasWorker ? "Worker available" : "Main thread only"}</strong>
                    <small>BM25 and graph retrieval stay off the UI thread when this is ready.</small>
                  </article>
                  <article>
                    <Badge tone={graphRagStatusTone(runtimeStatus.embeddingWorker.hasWorker)}>
                      {runtimeStatus.embeddingWorker.hasWorker ? "Embedding worker available" : "Embedding unavailable"}
                    </Badge>
                    <strong>{runtimeStatus.embeddingWorker.modelName}</strong>
                    <small>
                      {runtimeStatus.embeddingWorker.isInitialized
                        ? "Model initialized for hybrid search."
                        : "Model loads only if hybrid vector search is enabled."}
                    </small>
                  </article>
                  <article>
                    <Badge tone={runtimeStatus.backend.available ? "success" : "warning"}>
                      {runtimeStatus.backend.recommendedBackend}
                    </Badge>
                    <strong>{graphRagBackendSummary(runtimeStatus)}</strong>
                    <small>
                      {runtimeStatus.backend.crossOriginIsolated
                        ? "Cross-origin isolation is enabled."
                        : "WASM thread acceleration may be unavailable without cross-origin isolation."}
                    </small>
                  </article>
                </div>
              ) : null}
            </div>
          </form>

          {errorMessage ? <StatusBanner tone="danger">{errorMessage}</StatusBanner> : null}
          {searchStatus === "idle" ? (
            <StatusBanner tone="info">
              Choose a category or search directly. Default searches use the local BM25 and graph indexes without downloading model weights.
            </StatusBanner>
          ) : null}
          {searchStatus === "ready" && results.length === 0 ? (
            <StatusBanner tone="warning">
              No local 211 matches were found for this query. Try a broader need or contact 211 directly.
            </StatusBanner>
          ) : null}

          {answer ? (
            <article className="graphrag-answer-card" aria-live="polite">
              <div className="graphrag-answer-heading">
                <div>
                  <p className="eyebrow">Cited answer</p>
                  <h3>{answer.usedLocalModel ? "Local model answer" : "Evidence summary"}</h3>
                </div>
                <Badge tone={answer.usedLocalModel ? "success" : "neutral"}>
                  {answer.evidence.nodes.length} graph nodes
                </Badge>
              </div>
              <p className="graphrag-answer-text">{answer.answer}</p>
            </article>
          ) : null}

          {results.length > 0 ? (
            <div className="list-stack graphrag-result-list">
              {results.map((result, index) => (
                <article className="list-item graphrag-result-item" key={result.docId}>
                  <div className="graphrag-result-body">
                    <div className="graphrag-result-title-row">
                      <span className="graphrag-rank">{index + 1}</span>
                      <div>
                        <h3>{graphRagDocumentTitle(result)}</h3>
                        <p>{graphRagDocumentDetails(result)}</p>
                      </div>
                    </div>
                    <p className="graphrag-snippet">{result.snippet || result.document.text.slice(0, 280)}</p>
                    <small className="graphrag-cid-row">
                      CID {shortCid(result.contentCid)} · score {result.score.toFixed(2)}
                    </small>
                  </div>
                  <div className="graphrag-result-actions">
                    <Badge tone={result.document.doc_type === "service" ? "success" : "neutral"}>
                      {result.document.doc_type}
                    </Badge>
                    {result.document.source_url ? (
                      <a className="graphrag-source-link" href={result.document.source_url} rel="noreferrer" target="_blank">
                        Source
                      </a>
                    ) : null}
                  </div>
                </article>
              ))}
            </div>
          ) : null}
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

function ShelterScreen({
  checklist,
  setChecklist,
  shelterStaffAccounts,
  setShelterStaffAccounts,
  shelterUserAccounts,
  setShelterUserAccounts
}: {
  checklist: typeof defaultShelterChecklist;
  setChecklist: (value: typeof defaultShelterChecklist) => void;
  shelterStaffAccounts: ShelterStaffAccount[];
  setShelterStaffAccounts: (accounts: ShelterStaffAccount[]) => void;
  shelterUserAccounts: ShelterUserAccount[];
  setShelterUserAccounts: (accounts: ShelterUserAccount[]) => void;
}) {
  const [isShelterAdmin, setIsShelterAdmin] = useState(false);
  const [adminShelter, setAdminShelter] = useState(shelterOptions[0]);
  const [operatorShelter, setOperatorShelter] = useState(shelterOptions[0]);
  const [operatorStaffId, setOperatorStaffId] = useState("");
  const [userDraft, setUserDraft] = useState(defaultManagedUserDraft);
  const [staffDraft, setStaffDraft] = useState({ displayName: "", email: "" });

  const staffForShelter = shelterStaffAccounts.filter((account) => account.shelter === adminShelter);
  const verifiedStaffForOperatorShelter = shelterStaffAccounts.filter(
    (account) => account.shelter === operatorShelter && account.verified
  );
  const selectedOperator = shelterStaffAccounts.find((account) => account.id === operatorStaffId && account.verified);
  const usersForOperatorShelter = shelterUserAccounts.filter((account) => account.shelter === operatorShelter);
  const oversightShelter = isShelterAdmin ? adminShelter : operatorShelter;

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
    setUserDraft(defaultManagedUserDraft);
  }

  function createStaffAccount(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedOperator || !staffDraft.displayName.trim()) return;

    const newStaff: ShelterStaffAccount = {
      id: `staff-${Date.now()}`,
      shelter: operatorShelter,
      displayName: staffDraft.displayName.trim(),
      email: staffDraft.email.trim(),
      verified: false,
      updatedAt: new Date().toISOString()
    };
    setShelterStaffAccounts([...shelterStaffAccounts, newStaff]);
    setStaffDraft({ displayName: "", email: "" });
  }

  return (
    <div className="screen">
      <div className="page-title">
        <p className="eyebrow">Shelter portal</p>
        <h1>Assisted access</h1>
      </div>
      <StatusBanner tone="info">Shelter workflows are free and keep user sharing choices separate from staff access.</StatusBanner>
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
      <Section title="Verified staff workspace">
        <div className="shelter-staff-panel">
          <Field label="Shelter" required>
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
          <Field help="Only verified staff can create accounts." label="Verified staff operator" required>
            <select value={operatorStaffId} onChange={(event) => setOperatorStaffId(event.target.value)}>
              <option value="">Select verified staff</option>
              {verifiedStaffForOperatorShelter.map((staff) => (
                <option key={staff.id} value={staff.id}>
                  {staff.displayName}
                </option>
              ))}
            </select>
          </Field>
          {!selectedOperator ? (
            <small className="pin-request-note">Select a verified staff operator to create client or staff accounts.</small>
          ) : (
            <>
              <Section title="Create user account">
                <form className="form-grid" onSubmit={createManagedUserAccount}>
                  <Field label="Legal or full name" required>
                    <input
                      value={userDraft.legalName}
                      onChange={(event) => setUserDraft({ ...userDraft, legalName: event.target.value })}
                    />
                  </Field>
                  <Field label="Preferred name">
                    <input
                      value={userDraft.preferredName}
                      onChange={(event) => setUserDraft({ ...userDraft, preferredName: event.target.value })}
                    />
                  </Field>
                  <Field label="Pronouns">
                    <input
                      value={userDraft.pronouns}
                      onChange={(event) => setUserDraft({ ...userDraft, pronouns: event.target.value })}
                    />
                  </Field>
                  <Field label="Birth date">
                    <input
                      type="date"
                      value={userDraft.dateOfBirth}
                      onChange={(event) => setUserDraft({ ...userDraft, dateOfBirth: event.target.value })}
                    />
                  </Field>
                  <Field label="Photo or photo ID" required>
                    <input
                      accept="image/*,.pdf,application/pdf"
                      capture="user"
                      type="file"
                      onChange={(event) =>
                        setUserDraft({ ...userDraft, photoAssetId: event.target.files?.[0]?.name ?? "" })
                      }
                    />
                  </Field>
                  <Field label="Phone">
                    <input
                      value={userDraft.phone}
                      onChange={(event) => setUserDraft({ ...userDraft, phone: event.target.value })}
                    />
                  </Field>
                  <Field label="Email">
                    <input
                      type="email"
                      value={userDraft.email}
                      onChange={(event) => setUserDraft({ ...userDraft, email: event.target.value })}
                    />
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
                    <span>Quick health check complete (step 1)</span>
                  </label>
                  <div className="full-span">
                    <span className="field-label">Service needs</span>
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
                      checked={Boolean(userDraft.captchaToken)}
                      disabled={userDraft.easyBotCheckStatus !== "passed"}
                      onChange={(event) =>
                        setUserDraft({ ...userDraft, captchaToken: event.target.checked ? "mock-captcha-token" : "" })
                      }
                      type="checkbox"
                    />
                    <span>Bot check complete (step 2)</span>
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
                        !userDraft.photoAssetId ||
                        (userDraft.easyBotCheckStatus === "pending") ||
                        (userDraft.easyBotCheckStatus === "passed" && !userDraft.captchaToken)
                      }
                      type="submit"
                    >
                      Create user account
                    </Button>
                  </div>
                </form>
              </Section>

              <Section title="Create staff account">
                <form className="form-grid" onSubmit={createStaffAccount}>
                  <Field label="Staff name" required>
                    <input
                      value={staffDraft.displayName}
                      onChange={(event) => setStaffDraft({ ...staffDraft, displayName: event.target.value })}
                    />
                  </Field>
                  <Field label="Staff email">
                    <input
                      type="email"
                      value={staffDraft.email}
                      onChange={(event) => setStaffDraft({ ...staffDraft, email: event.target.value })}
                    />
                  </Field>
                  <div className="full-span">
                    <Button type="submit">Create staff account</Button>
                  </div>
                </form>
              </Section>

              <div className="list-stack">
                {usersForOperatorShelter.length ? (
                  usersForOperatorShelter.map((account) => (
                    <article className="list-item" key={account.id}>
                      <div>
                        <h3>{account.preferredName || account.legalName}</h3>
                        <p>{account.legalName}</p>
                        <small>
                          Created by {shelterStaffAccounts.find((item) => item.id === account.createdByStaffId)?.displayName ?? "Staff"}
                          {account.dateOfBirth ? ` · DOB ${account.dateOfBirth}` : ""}
                        </small>
                      </div>
                      <Badge>User account</Badge>
                    </article>
                  ))
                ) : (
                  <small>No user accounts created for this shelter yet.</small>
                )}
              </div>

              <Section title="Shelter user oversight">
                <div className="list-stack">
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
                            {account.easyBotCheckStatus === "failed" ? <Badge tone="warning">Health check</Badge> : null}
                          </div>
                        </div>
                      </article>
                    ))
                  ) : (
                    <small>No shelter-registered users for this shelter yet.</small>
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
                              {account.localPrecinctNotified ? "Precinct notified" : "Precinct not notified"}
                            </Badge>
                            <Badge tone={account.foundPermanentHousing ? "success" : "neutral"}>
                              {account.foundPermanentHousing ? "Found housing" : "Housing not found"}
                            </Badge>
                            {account.easyBotCheckStatus === "failed" ? <Badge tone="warning">Health check</Badge> : null}
                          </div>
                        </div>
                      </article>
                    ))
                  ) : (
                    <small>No users listed this shelter as preferred shelter.</small>
                  )}
                </div>
              </Section>
            </>
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
        <label className="consent-box">
          <input
            checked={isShelterAdmin}
            onChange={(event) => setIsShelterAdmin(event.target.checked)}
            type="checkbox"
          />
          <span>
            <strong>I am shelter administrator</strong>
          </span>
        </label>
        {isShelterAdmin ? (
          <div className="shelter-staff-panel">
            <Field label="Shelter" required>
              <select value={adminShelter} onChange={(event) => setAdminShelter(event.target.value)}>
                {shelterOptions.map((shelter) => (
                  <option key={shelter} value={shelter}>
                    {shelter}
                  </option>
                ))}
              </select>
            </Field>
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
                    <Button
                      onClick={() =>
                        setShelterStaffAccounts(
                          shelterStaffAccounts.map((item) =>
                            item.id === account.id
                              ? { ...item, verified: !item.verified, updatedAt: new Date().toISOString() }
                              : item
                          )
                        )
                      }
                      variant="secondary"
                    >
                      {account.verified ? "Revoke verification" : "Re-verify"}
                    </Button>
                  </article>
                ))
              ) : (
                <small>No staff accounts registered for this shelter yet.</small>
              )}
            </div>
          </div>
        ) : null}
      </Section>
    </div>
  );
}

function RecipientAccessScreen({
  accessRequests,
  apiConfig,
  grantReceipts,
  recipients,
  refreshWalletAuditEvents,
  refreshWalletAccessState,
  setAccessRequests,
  setGrantReceipts,
  verified,
  setVerified
}: {
  accessRequests: WalletAccessRequest[];
  apiConfig?: WalletApiConfig;
  grantReceipts: WalletGrantReceipt[];
  recipients: DisclosureRecipientDraft[];
  refreshWalletAuditEvents: () => Promise<void>;
  refreshWalletAccessState: () => Promise<void>;
  setAccessRequests: (requests: WalletAccessRequest[]) => void;
  setGrantReceipts: (receipts: WalletGrantReceipt[]) => void;
  verified: boolean;
  setVerified: (verified: boolean) => void;
}) {
  const recipient = recipients[0];
  const [derivedArtifactsByReceiptId, setDerivedArtifactsByReceiptId] = useState<Record<string, DerivedArtifactView>>(
    {}
  );
  const [decryptedRecordsByReceiptId, setDecryptedRecordsByReceiptId] = useState<Record<string, DecryptedRecordView>>(
    {}
  );
  const [analyzingReceiptIds, setAnalyzingReceiptIds] = useState<string[]>([]);
  const [decryptingReceiptIds, setDecryptingReceiptIds] = useState<string[]>([]);
  const [delegatingReceiptIds, setDelegatingReceiptIds] = useState<string[]>([]);
  const [delegationDrafts, setDelegationDrafts] = useState<
    Record<string, { audienceDid: string; audienceKeyHex: string; purpose: string; ability: string }>
  >({});
  const [delegationMessages, setDelegationMessages] = useState<Record<string, string>>({});

  function hasThresholdApproval(request: WalletAccessRequest) {
    if (!request.approvalRequired) return true;
    return (request.approvalCount ?? 0) >= (request.approvalThreshold ?? 1);
  }

  function delegationAbilityOptions(receipt: WalletGrantReceipt) {
    const abilities = receipt.abilities.includes("*") ? ["record/analyze", "record/decrypt"] : receipt.abilities;
    return ["record/analyze", "record/decrypt"].filter((ability) => abilities.includes(ability));
  }

  function receiptHasAbility(receipt: WalletGrantReceipt, ability: string) {
    return receipt.abilities.includes("*") || receipt.abilities.includes(ability);
  }

  function canDelegateReceipt(receipt: WalletGrantReceipt, abilityOptions: string[]) {
    const hasShare = receipt.abilities.some(
      (ability) => ability === "*" || ability === "record/share" || ability === "document/share"
    );
    return (
      Boolean(apiConfig?.actorDid) &&
      apiConfig?.actorDid === receipt.audienceDid &&
      receipt.status === "active" &&
      hasShare &&
      abilityOptions.length > 0 &&
      receipt.resources.length > 0
    );
  }

  function delegationDraftFor(receipt: WalletGrantReceipt, abilityOptions: string[]) {
    const draft = delegationDrafts[receipt.id];
    const fallbackAbility = abilityOptions[0] ?? "record/analyze";
    if (!draft) {
      return {
        audienceDid: "",
        audienceKeyHex: "",
        purpose: receipt.purpose,
        ability: fallbackAbility
      };
    }
    return {
      ...draft,
      ability: abilityOptions.includes(draft.ability) ? draft.ability : fallbackAbility
    };
  }

  function updateDelegationDraft(
    receipt: WalletGrantReceipt,
    abilityOptions: string[],
    patch: Partial<{ audienceDid: string; audienceKeyHex: string; purpose: string; ability: string }>
  ) {
    setDelegationDrafts({
      ...delegationDrafts,
      [receipt.id]: {
        ...delegationDraftFor(receipt, abilityOptions),
        ...patch
      }
    });
  }

  async function recordControllerApproval(requestId: string) {
    const request = accessRequests.find((item) => item.id === requestId);
    if (apiConfig?.actorDid && request?.approvalId) {
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

  async function decideRequest(requestId: string, status: "approved" | "rejected") {
    const request = accessRequests.find((item) => item.id === requestId);
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
    if (status === "approved" && request && !grantReceipts.some((receipt) => receipt.id === `receipt-${request.id}`)) {
      setGrantReceipts([
        ...grantReceipts,
        {
          id: `receipt-${request.id}`,
          grantId: `grant-${request.id}`,
          audienceName: request.requesterName,
          audienceDid: request.audienceDid,
          resources: [`wallet://demo-wallet/records/${request.resourceLabel}`],
          recordId: undefined,
          resourceLabel: request.resourceLabel,
          abilities: request.abilities,
          purpose: request.purpose,
          receiptHash: `local-${request.id}-receipt`,
          status: "active",
          createdAt: "Just now",
          expiresAt: "30 days"
        }
      ]);
    }
  }

  async function revokeRequest(requestId: string) {
    const request = accessRequests.find((item) => item.id === requestId);
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
    setAccessRequests(
      accessRequests.map((request) =>
        request.id === requestId ? { ...request, grantStatus: "revoked" } : request
      )
    );
    if (request) {
      setGrantReceipts(
        grantReceipts.map((receipt) =>
          receipt.audienceDid === request.audienceDid &&
          receipt.resourceLabel === request.resourceLabel &&
          receipt.status === "active"
            ? { ...receipt, status: "revoked" }
            : receipt
        )
      );
    }
  }

  async function analyzeReceipt(receipt: WalletGrantReceipt) {
    if (!receipt.recordId || receipt.status !== "active" || !receiptHasAbility(receipt, "record/analyze")) return;
    setAnalyzingReceiptIds((receiptIds) => [...receiptIds, receipt.id]);
    try {
      const artifact =
        apiConfig?.actorDid
          ? await analyzeRecordWithGrant(apiConfig, {
              grantId: receipt.grantId,
              recordId: receipt.recordId,
              maxChars: 200
            })
          : {
              id: `artifact-${receipt.id}`,
              sourceRecordIds: [receipt.recordId],
              artifactType: "summary",
              outputPolicy: "derived_only",
              encryptedPayloadRef: "local encrypted derived artifact",
              createdAt: "Just now"
            };
      setDerivedArtifactsByReceiptId({
        ...derivedArtifactsByReceiptId,
        [receipt.id]: artifact
      });
      await refreshWalletAuditEvents();
    } catch {
      setDerivedArtifactsByReceiptId({
        ...derivedArtifactsByReceiptId,
        [receipt.id]: {
          id: `artifact-error-${receipt.id}`,
          sourceRecordIds: [receipt.recordId],
          artifactType: "unavailable",
          outputPolicy: "derived_only",
          encryptedPayloadRef: "analysis unavailable",
          createdAt: "Just now"
        }
      });
    } finally {
      setAnalyzingReceiptIds((receiptIds) => receiptIds.filter((id) => id !== receipt.id));
    }
  }

  async function viewReceipt(receipt: WalletGrantReceipt) {
    if (!receipt.recordId || receipt.status !== "active" || !receiptHasAbility(receipt, "record/decrypt")) return;
    const recordId = receipt.recordId;
    setDecryptingReceiptIds((receiptIds) => [...receiptIds, receipt.id]);
    try {
      const decrypted =
        apiConfig?.actorDid
          ? await (async () => {
              let invocationToken: string | undefined;
              if (apiConfig.audienceKeyHex || apiConfig.issuerKeyHex) {
                try {
                  invocationToken = await issueRecordDecryptInvocation(apiConfig, {
                    grantId: receipt.grantId,
                    recordId,
                    userPresent: receiptRequiresUserPresence(receipt)
                  });
                } catch {
                  invocationToken = undefined;
                }
              }
              return decryptRecordWithGrant(apiConfig, {
                grantId: invocationToken ? undefined : receipt.grantId,
                invocationToken,
                recordId
              });
            })()
          : {
              recordId,
              text: "Local demo decrypted document preview.",
              sizeBytes: "Local demo decrypted document preview.".length
            };
      setDecryptedRecordsByReceiptId({
        ...decryptedRecordsByReceiptId,
        [receipt.id]: decrypted
      });
      await refreshWalletAuditEvents();
    } catch {
      setDecryptedRecordsByReceiptId({
        ...decryptedRecordsByReceiptId,
        [receipt.id]: {
          recordId,
          text: "Document view unavailable.",
          sizeBytes: 0
        }
      });
    } finally {
      setDecryptingReceiptIds((receiptIds) => receiptIds.filter((id) => id !== receipt.id));
    }
  }

  async function delegateReceipt(event: FormEvent<HTMLFormElement>, receipt: WalletGrantReceipt) {
    event.preventDefault();
    const abilityOptions = delegationAbilityOptions(receipt);
    const draft = delegationDraftFor(receipt, abilityOptions);
    if (!apiConfig?.actorDid || !draft.audienceDid.trim() || !canDelegateReceipt(receipt, abilityOptions)) return;
    setDelegatingReceiptIds((receiptIds) => [...receiptIds, receipt.id]);
    setDelegationMessages((messages) => ({ ...messages, [receipt.id]: "" }));
    try {
      await delegateGrant(apiConfig, {
        parentGrantId: receipt.grantId,
        audienceDid: draft.audienceDid.trim(),
        audienceKeyHex: draft.audienceKeyHex.trim() || undefined,
        resources: receipt.resources,
        abilities: [draft.ability],
        purpose: draft.purpose.trim() || receipt.purpose
      });
      setDelegationDrafts({
        ...delegationDrafts,
        [receipt.id]: {
          audienceDid: "",
          audienceKeyHex: "",
          purpose: receipt.purpose,
          ability: abilityOptions[0] ?? "record/analyze"
        }
      });
      setDelegationMessages((messages) => ({
        ...messages,
        [receipt.id]: `Delegated to ${draft.audienceDid.trim()}.`
      }));
      await refreshWalletAccessState();
      await refreshWalletAuditEvents();
    } catch {
      setDelegationMessages((messages) => ({
        ...messages,
        [receipt.id]: "Delegation failed."
      }));
    } finally {
      setDelegatingReceiptIds((receiptIds) => receiptIds.filter((id) => id !== receipt.id));
    }
  }

  return (
    <div className="screen">
      <div className="page-title">
        <p className="eyebrow">Secure access</p>
        <h1>Access requests</h1>
      </div>
      <Section title="Review requested access">
        <div className="list-stack">
          {accessRequests.map((request) => {
            const isRevoked = request.status === "approved" && request.grantStatus === "revoked";
            const statusLabel = isRevoked ? "revoked" : request.status;
            const statusTone = isRevoked
              ? "warning"
              : request.status === "approved"
                ? "success"
                : request.status === "rejected"
                  ? "warning"
                  : "neutral";

            return (
              <article className={`list-item access-request-item${isRevoked ? " access-request-revoked" : ""}`} key={request.id}>
                <div>
                  <div className="scope-header">
                    <div>
                      <h3>{request.requesterName}</h3>
                      <p>{request.resourceLabel} · {request.purpose}</p>
                    </div>
                    <Badge tone={statusTone}>{statusLabel}</Badge>
                  </div>
                  <div className="badge-row">
                    {request.abilities.map((ability) => (
                      <Badge key={ability}>{ability}</Badge>
                    ))}
                    <Badge>{request.createdAt}</Badge>
                    {request.approvalRequired ? (
                      <Badge tone={hasThresholdApproval(request) ? "success" : "warning"}>
                        {request.approvalCount ?? 0}/{request.approvalThreshold ?? 1} approvals
                      </Badge>
                    ) : null}
                    {request.status === "approved" && request.grantStatus !== "revoked" ? (
                      <Badge tone="success">active grant</Badge>
                    ) : null}
                  </div>
                  {isRevoked ? (
                    <p className="revoked-note">
                      Access was revoked. This recipient no longer has decrypt or analysis access.
                    </p>
                  ) : null}
                  {request.approvalRequired && !hasThresholdApproval(request) ? (
                    <p className="approval-note">Multi-sig approval is required before this access can be granted.</p>
                  ) : null}
                  <div
                    className="capability-preview"
                    role="group"
                    aria-label={`${request.requesterName} access capability preview`}
                  >
                    <div className="scope-header">
                      <div>
                        <h4>Capability preview</h4>
                        <p>{request.resourceLabel} · {request.purpose}</p>
                      </div>
                      <Badge tone={hasThresholdApproval(request) ? "success" : "warning"}>
                        {hasThresholdApproval(request) ? "approval ready" : "approval pending"}
                      </Badge>
                    </div>
                    <div className="disclosure-package">
                      <div className="disclosure-row">
                        <strong>Abilities</strong>
                        <span>{request.abilities.join(", ")}</span>
                      </div>
                      <div className="disclosure-row">
                        <strong>Recipient DID</strong>
                        <span>{request.audienceDid}</span>
                      </div>
                      <div className="disclosure-row">
                        <strong>Not granted</strong>
                        <span>{nonGrantedCapabilities(request.abilities).join(", ")}</span>
                      </div>
                    </div>
                  </div>
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
                ) : request.status === "approved" && request.grantStatus !== "revoked" ? (
                  <div className="row-actions">
                    <Button onClick={() => revokeRequest(request.id)} variant="danger">
                      Revoke
                    </Button>
                  </div>
                ) : null}
              </article>
            );
          })}
        </div>
      </Section>
      <Section title="Sharing receipts">
        <div className="list-stack">
          {grantReceipts.map((receipt) => {
            const canAnalyze =
              receipt.status === "active" && receiptHasAbility(receipt, "record/analyze") && Boolean(receipt.recordId);
            const canView =
              receipt.status === "active" && receiptHasAbility(receipt, "record/decrypt") && Boolean(receipt.recordId);
            const artifact = derivedArtifactsByReceiptId[receipt.id];
            const decryptedRecord = decryptedRecordsByReceiptId[receipt.id];
            const delegationOptions = delegationAbilityOptions(receipt);
            const canDelegate = canDelegateReceipt(receipt, delegationOptions);
            const delegationDraft = delegationDraftFor(receipt, delegationOptions);
            const delegationMessage = delegationMessages[receipt.id];
            return (
            <article
                aria-labelledby={`grant-receipt-${receipt.id}`}
                className={`grant-receipt-card${receipt.status === "revoked" ? " grant-receipt-revoked" : ""}`}
                key={receipt.id}
              >
              <div className="scope-header">
                <div>
                  <h3 id={`grant-receipt-${receipt.id}`}>{receipt.audienceName}</h3>
                  <p>{receipt.resourceLabel} · {receipt.purpose}</p>
                </div>
                <Badge tone={receipt.status === "active" ? "success" : "warning"}>{receipt.status}</Badge>
              </div>
              <div className="badge-row">
                {receipt.abilities.map((ability) => (
                  <Badge key={ability}>{ability}</Badge>
                ))}
                <Badge>{receipt.createdAt}</Badge>
                {receipt.expiresAt ? <Badge>expires {receipt.expiresAt}</Badge> : null}
              </div>
              <div className="receipt-hash-row">
                <span>Receipt hash</span>
                <code>{receipt.receiptHash}</code>
              </div>
              <div
                className="capability-preview"
                role="group"
                aria-label={`${receipt.audienceName} receipt capability preview`}
              >
                <div className="scope-header">
                  <div>
                    <h4>Capability preview</h4>
                    <p>{receipt.resourceLabel} · {receipt.purpose}</p>
                  </div>
                  <Badge tone={receipt.status === "active" ? "success" : "warning"}>
                    {receipt.status === "active" ? "currently active" : "revoked"}
                  </Badge>
                </div>
                <div className="disclosure-package">
                  <div className="disclosure-row">
                    <strong>Abilities</strong>
                    <span>{receipt.abilities.join(", ")}</span>
                  </div>
                  <div className="disclosure-row">
                    <strong>Recipient DID</strong>
                    <span>{receipt.audienceDid}</span>
                  </div>
                  <div className="disclosure-row">
                    <strong>Not granted</strong>
                    <span>{nonGrantedCapabilities(receipt.abilities).join(", ")}</span>
                  </div>
                </div>
              </div>
              {canDelegate ? (
                <form className="form-grid" onSubmit={(event) => delegateReceipt(event, receipt)}>
                  <Field label="Delegate DID" required>
                    <input
                      onChange={(event) =>
                        updateDelegationDraft(receipt, delegationOptions, { audienceDid: event.target.value })
                      }
                      placeholder="did:key:case-worker"
                      value={delegationDraft.audienceDid}
                    />
                  </Field>
                  <Field label="Delegated purpose">
                    <input
                      onChange={(event) =>
                        updateDelegationDraft(receipt, delegationOptions, { purpose: event.target.value })
                      }
                      placeholder={receipt.purpose}
                      value={delegationDraft.purpose}
                    />
                  </Field>
                  <Field label="Delegated ability">
                    <select
                      onChange={(event) =>
                        updateDelegationDraft(receipt, delegationOptions, { ability: event.target.value })
                      }
                      value={delegationDraft.ability}
                    >
                      {delegationOptions.map((ability) => (
                        <option key={ability} value={ability}>
                          {ability}
                        </option>
                      ))}
                    </select>
                  </Field>
                  <Field label="Delegate key hex">
                    <input
                      onChange={(event) =>
                        updateDelegationDraft(receipt, delegationOptions, { audienceKeyHex: event.target.value })
                      }
                      placeholder="optional"
                      value={delegationDraft.audienceKeyHex}
                    />
                  </Field>
                  <div className="row-actions full-span">
                    <Button
                      disabled={!delegationDraft.audienceDid.trim() || delegatingReceiptIds.includes(receipt.id)}
                      type="submit"
                      variant="secondary"
                    >
                      <UserPlus size={18} />
                      {delegatingReceiptIds.includes(receipt.id) ? "Delegating" : "Delegate access"}
                    </Button>
                  </div>
                </form>
              ) : null}
              {delegationMessage ? (
                <StatusBanner tone={delegationMessage.includes("failed") ? "warning" : "success"}>
                  {delegationMessage}
                </StatusBanner>
              ) : null}
              {artifact ? (
                <div className="disclosure-package">
                  <div className="disclosure-row">
                    <strong>Derived artifact</strong>
                    <span>{artifact.artifactType} · {artifact.outputPolicy}</span>
                  </div>
                  <div className="disclosure-row">
                    <strong>Encrypted result</strong>
                    <span>{artifact.encryptedPayloadRef}</span>
                  </div>
                  <div className="disclosure-row">
                    <strong>Sources</strong>
                    <span>{artifact.sourceRecordIds.join(", ") || "No source records"}</span>
                  </div>
                </div>
              ) : null}
              {decryptedRecord ? (
                <div className="disclosure-package">
                  <div className="disclosure-row">
                    <strong>Document view</strong>
                    <span className="document-preview-text">{decryptedRecord.text}</span>
                  </div>
                  <div className="disclosure-row">
                    <strong>Plaintext size</strong>
                    <span>{decryptedRecord.sizeBytes} bytes</span>
                  </div>
                </div>
              ) : null}
              {canAnalyze || canView ? (
                <div className="row-actions">
                  {canAnalyze ? (
                    <Button
                      disabled={analyzingReceiptIds.includes(receipt.id)}
                      onClick={() => analyzeReceipt(receipt)}
                      variant="secondary"
                    >
                      <ShieldCheck size={18} />
                      {analyzingReceiptIds.includes(receipt.id) ? "Analyzing" : "Analyze safely"}
                    </Button>
                  ) : null}
                  {canView ? (
                    <Button
                      disabled={decryptingReceiptIds.includes(receipt.id)}
                      onClick={() => viewReceipt(receipt)}
                      variant="secondary"
                    >
                      <LockKeyhole size={18} />
                      {decryptingReceiptIds.includes(receipt.id) ? "Opening" : "View document"}
                    </Button>
                  ) : null}
                </div>
              ) : null}
              <small>{receipt.audienceDid}</small>
            </article>
            );
          })}
        </div>
      </Section>
      {!verified ? (
        <Section title="Verify recipient">
          <StatusBanner tone="warning">Sensitive information is hidden until recipient verification is complete.</StatusBanner>
          <div className="form-grid">
            <Field label="Access code">
              <input placeholder="Enter code" />
            </Field>
            <Field label="Recipient phone or email">
              <input placeholder="Confirm contact method" />
            </Field>
          </div>
          <Button onClick={() => setVerified(true)}>
            <KeyRound size={18} /> Verify and view
          </Button>
        </Section>
      ) : (
        <Section title={`Authorized for ${recipient.displayName}`}>
          <div className="disclosure-package">
            {recipient.allowedScopes.map((scope) => (
              <div className="disclosure-row" key={scope}>
                <strong>{disclosureScopes.find((item) => item.id === scope)?.label ?? scope}</strong>
                <span>Available in this emergency package</span>
              </div>
            ))}
          </div>
          <Button variant="secondary">Contact liaison</Button>
        </Section>
      )}
    </div>
  );
}

function BenefitsProtectionScreen({
  optedIn,
  setOptedIn
}: {
  optedIn: boolean;
  setOptedIn: (optedIn: boolean) => void;
}) {
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
        <div
          className="capability-preview"
          role="group"
          aria-label="Benefits notification capability preview"
        >
          <div className="scope-header">
            <div>
              <h4>Capability preview</h4>
              <p>missed check-in and benefits status only</p>
            </div>
            <Badge tone={optedIn ? "success" : "neutral"}>{optedIn ? "ready to save" : "not enabled"}</Badge>
          </div>
          <div className="disclosure-package">
            <div className="disclosure-row">
              <strong>Abilities</strong>
              <span>{capabilitySummary(["metadata/read", "derived/read"])}</span>
            </div>
            <div className="disclosure-row">
              <strong>Scope</strong>
              <span>missed_check_in, benefits_information</span>
            </div>
            <div className="disclosure-row">
              <strong>Not granted</strong>
              <span>{nonGrantedCapabilities(["metadata/read", "derived/read"]).join(", ")}</span>
            </div>
          </div>
        </div>
        <label className="consent-box">
          <input checked={optedIn} onChange={(event) => setOptedIn(event.target.checked)} type="checkbox" />
          <span>
            <strong>Allow Abby to prepare a benefits-protection notification after missed check-ins.</strong>
            <small>Legal and policy review must be completed before this can be sent in production.</small>
          </span>
        </label>
        <Button disabled={!optedIn}>
          <Landmark size={18} /> Save opt-in
        </Button>
      </Section>
    </div>
  );
}

function AnalyticsScreen({
  apiConfig,
  optedIn,
  refreshWalletAuditEvents,
  setOptedIn
}: {
  apiConfig?: WalletApiConfig;
  optedIn: Record<string, boolean>;
  refreshWalletAuditEvents: () => Promise<void>;
  setOptedIn: (value: Record<string, boolean>) => void;
}) {
  const [apiStudies, setApiStudies] = useState<AnalyticsStudy[]>([]);
  const [apiConsents, setApiConsents] = useState<WalletAnalyticsConsent[]>([]);
  const [expirationByStudy, setExpirationByStudy] = useState<Record<string, string>>({});
  const [busyStudyId, setBusyStudyId] = useState<string | null>(null);
  const [analyticsStatus, setAnalyticsStatus] = useState<{
    tone: "info" | "success" | "warning" | "danger";
    text: string;
  } | null>(null);

  const activeConsentsByTemplate = useMemo(() => {
    const entries = apiConsents
      .filter((consent) => consent.status === "active")
      .map((consent) => [consent.templateId, consent] as const);
    return new Map(entries);
  }, [apiConsents]);
  const studies = apiConfig && apiStudies.length ? apiStudies : analyticsStudies;

  async function refreshAnalyticsState() {
    if (!apiConfig) return;
    const [templates, consents] = await Promise.all([
      listAnalyticsTemplates({ apiBaseUrl: apiConfig.apiBaseUrl, includeInactive: true }),
      listWalletAnalyticsConsents(apiConfig)
    ]);
    setApiStudies(templates.length ? templates : analyticsStudies);
    setApiConsents(consents);
    setExpirationByStudy((current) => {
      const next = { ...current };
      for (const consent of consents) {
        if (consent.status === "active" && consent.expiresAtRaw) {
          next[consent.templateId] = isoToDateInputValue(consent.expiresAtRaw);
        }
      }
      return next;
    });
  }

  useEffect(() => {
    if (!apiConfig) return;
    refreshAnalyticsState().catch(() => {
      setApiStudies([]);
      setApiConsents([]);
      setAnalyticsStatus({ tone: "warning", text: "Wallet analytics state could not be loaded." });
    });
  }, [apiConfig]);

  function toggleStudy(studyId: string) {
    setOptedIn({ ...optedIn, [studyId]: !optedIn[studyId] });
  }

  async function createConsent(study: AnalyticsStudy) {
    if (!apiConfig || !isStudyConsentable(study.status)) return;
    setBusyStudyId(study.id);
    setAnalyticsStatus(null);
    try {
      await createWalletAnalyticsConsent(apiConfig, study.id, dateInputValueToIso(expirationByStudy[study.id]));
      await refreshAnalyticsState();
      await refreshWalletAuditEvents().catch(() => undefined);
      setAnalyticsStatus({ tone: "success", text: "Analytics consent saved." });
    } catch (error) {
      setAnalyticsStatus({ tone: "danger", text: error instanceof Error ? error.message : "Consent request failed." });
    } finally {
      setBusyStudyId(null);
    }
  }

  async function withdrawConsent(study: AnalyticsStudy, consent?: WalletAnalyticsConsent) {
    if (!apiConfig || !consent) return;
    setBusyStudyId(study.id);
    setAnalyticsStatus(null);
    try {
      await revokeWalletAnalyticsConsent(apiConfig, consent.id);
      await refreshAnalyticsState();
      await refreshWalletAuditEvents().catch(() => undefined);
      setAnalyticsStatus({ tone: "success", text: "Analytics consent withdrawn." });
    } catch (error) {
      setAnalyticsStatus({ tone: "danger", text: error instanceof Error ? error.message : "Withdrawal request failed." });
    } finally {
      setBusyStudyId(null);
    }
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
      {analyticsStatus ? <StatusBanner tone={analyticsStatus.tone}>{analyticsStatus.text}</StatusBanner> : null}
      <div className="analytics-grid">
        {studies.map((study) => {
          const activeConsent = activeConsentsByTemplate.get(study.id);
          const selected = apiConfig ? Boolean(activeConsent) : Boolean(optedIn[study.id]);
          const budgetRemaining = Math.max(0, study.epsilonBudget - study.spentBudget);
          const titleId = `analytics-title-${study.id}`;
          const consentable = isStudyConsentable(study.status);
          const busy = busyStudyId === study.id;
          return (
            <article aria-labelledby={titleId} className="analytics-card" key={study.id}>
              <div className="scope-header">
                <div>
                  <h3 id={titleId}>{study.title}</h3>
	                  <p>{study.purpose}</p>
	                </div>
                <Badge tone={selected ? "success" : analyticsStatusTone(study.status)}>
                  {selected ? "consented" : analyticsStatusLabel(study.status)}
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
              <div
                className="capability-preview"
                role="group"
                aria-label={`${study.title} analytics capability preview`}
              >
                <div className="scope-header">
                  <div>
                    <h4>Capability preview</h4>
                    <p>{study.fields.length} derived fields · minimum cohort {study.minCohortSize}</p>
                  </div>
                  <Badge tone={study.status === "paused" ? "warning" : "success"}>
                    {study.status === "paused" ? "paused" : "bounded contribution"}
                  </Badge>
                </div>
	                <div className="disclosure-package">
	                  <div className="disclosure-row">
	                    <strong>Ability</strong>
	                    <span>analytics/contribute</span>
	                  </div>
	                  <div className="disclosure-row">
	                    <strong>Fields used</strong>
	                    <span>{study.fields.join(", ")}</span>
	                  </div>
                    <div className="disclosure-row">
                      <strong>Template status</strong>
                      <span>{analyticsStatusLabel(study.status)}</span>
                    </div>
                    <div className="disclosure-row">
                      <strong>Consent expiration</strong>
                      <span>{activeConsent?.expiresAt ?? "not set"}</span>
                    </div>
	                  <div className="disclosure-row">
	                    <strong>Not granted</strong>
	                    <span>{nonGrantedCapabilities(["analytics/contribute"]).join(", ")}</span>
	                  </div>
	                </div>
	              </div>
              <div className="analytics-consent-controls">
                <Field label="Consent expiration" help="Optional end date">
                  <input
                    disabled={Boolean(apiConfig && selected)}
                    onChange={(event) =>
                      setExpirationByStudy({ ...expirationByStudy, [study.id]: event.target.value })
                    }
                    type="date"
                    value={expirationByStudy[study.id] ?? ""}
                  />
                </Field>
              </div>
	              <label className="consent-box">
	                <input
	                  checked={selected}
	                  disabled={busy || !consentable}
	                  onChange={(event) => {
                      if (!apiConfig) {
                        toggleStudy(study.id);
                        return;
                      }
                      if (event.target.checked) {
                        void createConsent(study);
                      } else {
                        void withdrawConsent(study, activeConsent);
                      }
                    }}
	                  type="checkbox"
	                />
	                <span>
	                  <strong>Allow this study to use the listed derived fields.</strong>
	                  <small>
                      {selected
                        ? `Consent ${activeConsent?.id ?? "saved"} is active.`
                        : "Precise location, raw documents, names, and contact details are excluded."}
                    </small>
	                </span>
	              </label>
              {apiConfig ? (
                <div className="row-actions analytics-actions">
                  {selected ? (
                    <Button
                      disabled={busy}
                      loading={busy}
                      loadingLabel="Withdrawing"
                      onClick={() => void withdrawConsent(study, activeConsent)}
                      variant="danger"
                    >
                      <UserMinus size={18} /> Withdraw consent
                    </Button>
                  ) : (
                    <Button
                      disabled={busy || !consentable}
                      loading={busy}
                      loadingLabel="Saving"
                      onClick={() => void createConsent(study)}
                    >
                      <ShieldCheck size={18} /> Save consent
                    </Button>
                  )}
                </div>
              ) : null}
            </article>
          );
        })}
      </div>
    </div>
  );
}

function analyticsStatusLabel(status: string): string {
  if (status === "active") return "approved";
  if (status === "available") return "approved";
  return status;
}

function analyticsStatusTone(status: string): "neutral" | "success" | "warning" | "danger" {
  if (status === "approved" || status === "active" || status === "available") return "success";
  if (status === "paused" || status === "draft") return "warning";
  if (status === "retired") return "danger";
  return "neutral";
}

function isStudyConsentable(status: string): boolean {
  return status === "approved" || status === "active" || status === "available" || status === "consented";
}

function dateInputValueToIso(value?: string): string | undefined {
  if (!value) return undefined;
  return `${value}T23:59:59+00:00`;
}

function isoToDateInputValue(value: string): string {
  const match = value.match(/^\d{4}-\d{2}-\d{2}/);
  return match ? match[0] : "";
}

function ProofCenterScreen({
  apiConfig,
  proofs,
  refreshWalletAuditEvents,
  setProofs
}: {
  apiConfig?: WalletApiConfig;
  proofs: ProofReceiptView[];
  refreshWalletAuditEvents: () => Promise<void>;
  setProofs: (proofs: ProofReceiptView[]) => void;
}) {
  const [locationRecordId, setLocationRecordId] = useState(
    (import.meta.env.VITE_DEMO_LOCATION_RECORD_ID as string | undefined) ?? "rec-location-current"
  );
  const [regionId, setRegionId] = useState("multnomah_county");
  const [grantId, setGrantId] = useState("");
  const [proofStatus, setProofStatus] = useState<"idle" | "creating" | "created" | "failed">("idle");

  async function createProof(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!apiConfig?.actorDid || !locationRecordId.trim() || !regionId.trim()) {
      setProofStatus("failed");
      return;
    }
    setProofStatus("creating");
    try {
      const proof = await createLocationRegionProof(apiConfig, {
        grantId: grantId.trim() || undefined,
        locationRecordId: locationRecordId.trim(),
        regionId: regionId.trim()
      });
      setProofs([proof, ...proofs.filter((item) => item.id !== proof.id)]);
      await refreshWalletAuditEvents().catch(() => undefined);
      setProofStatus("created");
    } catch {
      setProofStatus("failed");
    }
  }

  return (
    <div className="screen">
      <div className="page-title">
        <p className="eyebrow">Proof center</p>
        <h1>Verified wallet claims</h1>
      </div>
      <StatusBanner tone="info">
        Proof receipts expose public claims and verifier details without showing raw documents or precise location.
      </StatusBanner>
      <article className="proof-card" aria-label="Create location region proof">
        <div className="scope-header">
          <div>
            <h3>Create location-region proof</h3>
            <p>location/prove_region · public inputs only</p>
          </div>
          <Badge tone={apiConfig ? "success" : "warning"}>{apiConfig ? "API connected" : "API required"}</Badge>
        </div>
        <form className="form-grid" onSubmit={createProof}>
          <Field label="Location record ID" required>
            <input
              onChange={(event) => setLocationRecordId(event.target.value)}
              placeholder="rec-location-current"
              value={locationRecordId}
            />
          </Field>
          <Field label="Region ID" required>
            <input
              onChange={(event) => setRegionId(event.target.value)}
              placeholder="multnomah_county"
              value={regionId}
            />
          </Field>
          <Field label="Grant ID">
            <input
              onChange={(event) => setGrantId(event.target.value)}
              placeholder="Owner wallets can leave this blank"
              value={grantId}
            />
          </Field>
          <div className="capability-preview" role="group" aria-label="Create proof capability preview">
            <div className="disclosure-package">
              <div className="disclosure-row">
                <strong>Ability</strong>
                <span>location/prove_region</span>
              </div>
              <div className="disclosure-row">
                <strong>Public output</strong>
                <span>region_id, claim, region_policy_hash</span>
              </div>
              <div className="disclosure-row">
                <strong>Not granted</strong>
                <span>{nonGrantedCapabilities(["proof/verify", "location/prove_region"]).join(", ")}</span>
              </div>
            </div>
          </div>
          {proofStatus === "created" ? (
            <StatusBanner tone="success">Proof receipt created and added to the wallet timeline.</StatusBanner>
          ) : null}
          {proofStatus === "failed" ? (
            <StatusBanner tone="warning">Proof creation failed. Check the record ID, grant, and API proof mode.</StatusBanner>
          ) : null}
          <Button disabled={!apiConfig?.actorDid || proofStatus === "creating"} type="submit" variant="secondary">
            {proofStatus === "creating" ? "Creating proof..." : "Create proof"}
          </Button>
        </form>
      </article>
      <div className="list-stack">
        {proofs.map((proof) => {
          const titleId = `proof-title-${proof.id}`;

          return (
            <article aria-labelledby={titleId} className="proof-card" key={proof.id}>
              <div className="scope-header">
                <div>
                  <h3 id={titleId}>{proof.claim}</h3>
                  <p>
                    {proof.proofType} · {proof.proofSystem} · {proof.verifier}
                  </p>
                </div>
                <Badge tone={proof.simulated ? "warning" : "success"}>
                  {proof.simulated ? "Simulated" : proof.verificationStatus}
                </Badge>
              </div>
              <div className="badge-row">
                <Badge>{proof.createdAt}</Badge>
                <Badge>{proof.witnessLabel}</Badge>
              </div>
              <div
                className="capability-preview"
                role="group"
                aria-label={`${proof.claim} proof capability preview`}
              >
                <div className="scope-header">
                  <div>
                    <h4>Capability preview</h4>
                    <p>{proof.proofType} · public inputs only</p>
                  </div>
                  <Badge tone={proof.simulated ? "warning" : "success"}>
                    {proof.simulated ? "development proof" : "verified proof"}
                  </Badge>
                </div>
                <div className="disclosure-package">
                  <div className="disclosure-row">
                    <strong>Ability</strong>
                    <span>proof/verify</span>
                  </div>
                  <div className="disclosure-row">
                    <strong>Verification</strong>
                    <span>{proof.verificationStatus}</span>
                  </div>
                  {proof.circuitId ? (
                    <div className="disclosure-row">
                      <strong>Circuit</strong>
                      <span>{proof.circuitId}</span>
                    </div>
                  ) : null}
                  {proof.verifierDigest ? (
                    <div className="disclosure-row">
                      <strong>Verifier digest</strong>
                      <span>{proof.verifierDigest.slice(0, 16)}...</span>
                    </div>
                  ) : null}
                  <div className="disclosure-row">
                    <strong>Public inputs</strong>
                    <span>{Object.keys(proof.publicInputs).join(", ")}</span>
                  </div>
                  <div className="disclosure-row">
                    <strong>Not granted</strong>
                    <span>{nonGrantedCapabilities(["proof/verify"]).join(", ")}</span>
                  </div>
                </div>
              </div>
              <div className="proof-inputs" aria-label={`${proof.claim} public inputs`}>
                {Object.entries(proof.publicInputs).map(([key, value]) => (
                  <div className="disclosure-row" key={key}>
                    <strong>{key}</strong>
                    <span>{value}</span>
                  </div>
                ))}
              </div>
            </article>
          );
        })}
      </div>
    </div>
  );
}

function ExportCenterScreen({
  apiConfig,
  bundles,
  setBundles
}: {
  apiConfig?: WalletApiConfig;
  bundles: ExportBundleView[];
  setBundles: (bundles: ExportBundleView[]) => void;
}) {
  const [audienceDid, setAudienceDid] = useState("did:key:legal-aid-desk");
  const [audienceName, setAudienceName] = useState("Legal Aid desk");
  const [recordIds, setRecordIds] = useState("rec-document-benefits\nrec-location-current");
  const [purpose, setPurpose] = useState("user_export");
  const [exportStatus, setExportStatus] = useState<"idle" | "creating" | "created" | "failed">("idle");
  const [importingBundleId, setImportingBundleId] = useState<string | null>(null);
  const [importStatus, setImportStatus] = useState<"idle" | "imported" | "failed">("idle");
  const exportRecordIds = useMemo(() => parseRecordIds(recordIds), [recordIds]);

  async function createBundle(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!apiConfig) return;
    if (!audienceDid.trim() || exportRecordIds.length === 0) {
      setExportStatus("failed");
      return;
    }
    setExportStatus("creating");
    try {
      const bundleView = await createVerifiedExportBundleView(apiConfig, {
        audienceDid: audienceDid.trim(),
        audienceName: audienceName.trim() || undefined,
        purpose: purpose.trim() || "user_export",
        recordIds: exportRecordIds
      });
      setBundles([bundleView, ...bundles.filter((bundle) => bundle.bundleId !== bundleView.bundleId)]);
      setExportStatus("created");
    } catch {
      setExportStatus("failed");
    }
  }

  async function importBundle(bundleView: ExportBundleView) {
    if (!apiConfig || !bundleView.bundle || bundleView.imported) return;
    setImportingBundleId(bundleView.bundleId);
    setImportStatus("idle");
    try {
      const importedBundle = await importExportBundleView({
        apiBaseUrl: apiConfig.apiBaseUrl,
        bundleView
      });
      setBundles(bundles.map((bundle) => (bundle.bundleId === importedBundle.bundleId ? importedBundle : bundle)));
      setImportStatus("imported");
    } catch {
      setImportStatus("failed");
    } finally {
      setImportingBundleId(null);
    }
  }

  return (
    <div className="screen">
      <div className="page-title">
        <p className="eyebrow">Encrypted exports</p>
        <h1>Shareable wallet bundles</h1>
      </div>
      <StatusBanner tone="info">
        Export bundles carry encrypted records, receipt hashes, and storage reports. Importing a bundle does not reveal plaintext.
      </StatusBanner>
      {!apiConfig ? (
        <StatusBanner tone="warning">Connect the wallet API environment to build live export bundles.</StatusBanner>
      ) : null}
      {exportStatus === "created" ? <StatusBanner tone="success">Export bundle verified.</StatusBanner> : null}
      {exportStatus === "failed" ? <StatusBanner tone="warning">Export bundle creation failed.</StatusBanner> : null}
      {importStatus === "imported" ? <StatusBanner tone="success">Export descriptors imported.</StatusBanner> : null}
      {importStatus === "failed" ? <StatusBanner tone="warning">Export import failed.</StatusBanner> : null}
      <Section title="Create export bundle">
        <form className="form-grid export-builder" onSubmit={createBundle}>
          <Field label="Recipient DID" required>
            <input
              onChange={(event) => setAudienceDid(event.target.value)}
              placeholder="did:key:recipient"
              value={audienceDid}
            />
          </Field>
          <Field label="Recipient label">
            <input
              onChange={(event) => setAudienceName(event.target.value)}
              placeholder="Legal Aid desk"
              value={audienceName}
            />
          </Field>
          <Field label="Purpose">
            <input onChange={(event) => setPurpose(event.target.value)} value={purpose} />
          </Field>
          <Field label="Record IDs" required>
            <textarea
              onChange={(event) => setRecordIds(event.target.value)}
              placeholder="rec-document-benefits"
              rows={3}
              value={recordIds}
            />
          </Field>
          <div className="row-actions full-span">
            <Button disabled={!apiConfig || exportStatus === "creating"} type="submit" variant="secondary">
              <ShieldCheck size={18} /> {exportStatus === "creating" ? "Creating" : "Create bundle"}
            </Button>
          </div>
          <div className="capability-preview full-span" role="group" aria-label="Export capability preview">
            <div className="scope-header">
              <div>
                <h3>Capability preview</h3>
                <p>{audienceName.trim() || audienceDid.trim() || "Recipient"} · {purpose.trim() || "user_export"}</p>
              </div>
              <Badge tone={exportRecordIds.length > 0 ? "success" : "warning"}>
                {exportRecordIds.length} records
              </Badge>
            </div>
            <div className="disclosure-package">
              <div className="disclosure-row">
                <strong>Ability</strong>
                <span>export/create</span>
              </div>
              <div className="disclosure-row">
                <strong>Records</strong>
                <span>{exportRecordIds.length > 0 ? exportRecordIds.join(", ") : "No records selected"}</span>
              </div>
              <div className="disclosure-row">
                <strong>Outputs</strong>
                <span>Encrypted descriptors, proof receipts, derived artifacts, storage report</span>
              </div>
              <div className="disclosure-row">
                <strong>Not granted</strong>
                <span>{nonGrantedCapabilities(["export/create"]).join(", ")}</span>
              </div>
            </div>
          </div>
        </form>
      </Section>
      <div className="list-stack">
        {bundles.map((bundle) => {
          const titleId = `export-title-${bundle.id}`;

          return (
            <article aria-labelledby={titleId} className="export-card" key={bundle.id}>
              <div className="scope-header">
                <div>
                  <h3 id={titleId}>{bundle.audienceName}</h3>
                  <p>{bundle.bundleId}</p>
                </div>
                <Badge tone={bundle.storageOk ? "success" : "warning"}>
                  {bundle.storageOk ? "storage verified" : "storage missing"}
                </Badge>
              </div>
              <div className="privacy-metrics">
                <StatusPanel label="Records" value={String(bundle.recordCount)} tone="teal" />
                <StatusPanel label="Proofs" value={String(bundle.proofCount)} tone="gold" />
              </div>
              <div className="receipt-hash-row">
                <span>Bundle hash</span>
                <code>{bundle.bundleHash}</code>
              </div>
              <div className="badge-row">
                <Badge>{bundle.createdAt}</Badge>
                <Badge tone={bundle.imported ? "success" : "neutral"}>
                  {bundle.imported ? "import verified" : "not imported"}
                </Badge>
              </div>
              <div className="row-actions">
                <Button
                  disabled={!apiConfig || !bundle.bundle || bundle.imported || importingBundleId === bundle.bundleId}
                  onClick={() => importBundle(bundle)}
                  variant="secondary"
                >
                  <ShieldCheck size={18} /> {importingBundleId === bundle.bundleId ? "Importing" : "Import descriptors"}
                </Button>
              </div>
            </article>
          );
        })}
      </div>
    </div>
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

function shortHash(value?: string): string {
  if (!value) return "Unavailable";
  return value.length > 24 ? `${value.slice(0, 12)}...${value.slice(-8)}` : value;
}

function thresholdApprovalCount(approval: ThresholdApprovalResponse): number {
  const approvers = new Set(approval.approver_dids ?? []);
  return Object.keys(approval.approvals ?? {}).filter((did) => approvers.size === 0 || approvers.has(did)).length;
}

function thresholdApprovalTone(status: string): "neutral" | "success" | "warning" {
  if (status === "approved") return "success";
  if (status === "pending") return "warning";
  return "neutral";
}

function thresholdApprovalDateLabel(value?: string): string {
  if (!value) return "Unavailable";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

function opsHealthTone(status?: string): string {
  if (status === "error") return "warning";
  if (status === "warning") return "info";
  if (status === "ok") return "success";
  return "neutral";
}

function stringDetail(details: Record<string, unknown> | undefined, key: string): string | null {
  const value = details?.[key];
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function objectDetail(details: Record<string, unknown> | undefined, key: string): Record<string, unknown> | null {
  const value = details?.[key];
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  return value as Record<string, unknown>;
}

function SecurityScreen({
  apiConfig,
  onSnapshotLoaded,
  refreshWalletAuditEvents
}: {
  apiConfig?: WalletApiConfig;
  onSnapshotLoaded: () => Promise<void> | void;
  refreshWalletAuditEvents: () => Promise<void>;
}) {
  const [snapshotIds, setSnapshotIds] = useState<string[]>([]);
  const [snapshotStatus, setSnapshotStatus] = useState<"idle" | "saving" | "saved" | "loading" | "loaded" | "failed">(
    "idle"
  );
  const [snapshotReport, setSnapshotReport] = useState<WalletSnapshotVerification | null>(null);
  const [storageStatus, setStorageStatus] = useState<"idle" | "checking" | "verified" | "repairing" | "repaired" | "failed">("idle");
  const [walletStorageReport, setWalletStorageReport] = useState<WalletStorageReportView | null>(null);
  const [opsStatus, setOpsStatus] = useState<"idle" | "checking" | "checked" | "failed">("idle");
  const [opsHealthReport, setOpsHealthReport] = useState<OpsHealthReport | null>(null);
  const [walletDetails, setWalletDetails] = useState<WalletDetails | null>(null);
  const [thresholdApprovals, setThresholdApprovals] = useState<ThresholdApprovalResponse[]>([]);
  const [approvalQueueStatus, setApprovalQueueStatus] = useState<
    "idle" | "loading" | "loaded" | "approving" | "failed"
  >("idle");
  const [controllerDid, setControllerDid] = useState("");
  const [controllerApprovalId, setControllerApprovalId] = useState("");
  const [deviceDid, setDeviceDid] = useState("");
  const [deviceApprovalId, setDeviceApprovalId] = useState("");
  const [recoveryContactDids, setRecoveryContactDids] = useState("");
  const [recoveryThreshold, setRecoveryThreshold] = useState(1);
  const [recoveryPolicyApprovalId, setRecoveryPolicyApprovalId] = useState("");
  const [recoveryActorDid, setRecoveryActorDid] = useState("");
  const [recoveredControllerDid, setRecoveredControllerDid] = useState("");
  const [recoveryControllerApprovalId, setRecoveryControllerApprovalId] = useState("");
  const [emergencyApprovalId, setEmergencyApprovalId] = useState("");
  const [emergencyReason, setEmergencyReason] = useState("suspected compromise");
  const [emergencyRotateKeys, setEmergencyRotateKeys] = useState(true);
  const [emergencyReport, setEmergencyReport] = useState<EmergencyRevokeReport | null>(null);
  const [governanceStatus, setGovernanceStatus] = useState<"idle" | "saving" | "requested" | "saved" | "failed">(
    "idle"
  );
  const [governanceMessage, setGovernanceMessage] = useState("");
  const hasCurrentSnapshot = Boolean(apiConfig && snapshotIds.includes(apiConfig.walletId));
  const governanceThreshold = walletDetails?.governance_policy?.threshold ?? 1;
  const governanceApprovals =
    walletDetails?.governance_policy?.approver_dids ?? walletDetails?.controller_dids ?? [];
  const recoveryPolicy = walletDetails?.governance_policy?.recovery_policy;
  const recoveryContacts = recoveryPolicy?.contact_dids ?? [];
  const pendingThresholdApprovals = thresholdApprovals.filter((approval) => approval.status === "pending");
  const opsCheckSummary = opsHealthReport
    ? opsHealthReport.checks.map((check) => `${check.name}: ${check.status}`).join(", ")
    : "Not checked";
  const proofRegistryCheck = opsHealthReport?.checks.find((check) => check.name === "proof_registry") ?? null;
  const proofRegistryDetails = proofRegistryCheck?.details;
  const proofBackendHealth = objectDetail(proofRegistryDetails, "backend_health");
  const proofBackendVerifier = [stringDetail(proofRegistryDetails, "verifier_id"), stringDetail(proofRegistryDetails, "proof_system")]
    .filter(Boolean)
    .join(" / ");
  const proofBackendMode = stringDetail(proofRegistryDetails, "backend_mode");
  const proofBackendHealthStatus = stringDetail(proofBackendHealth ?? undefined, "status");
  const proofBackendHealthError = stringDetail(proofBackendHealth ?? undefined, "error");
  const storageProviderSummary =
    walletStorageReport && Object.keys(walletStorageReport.storage_types).length
      ? Object.entries(walletStorageReport.storage_types)
          .map(([storageType, count]) => `${storageType}: ${count}`)
          .join(", ")
      : "Not checked";
  const emergencyRotationErrors = Object.entries(emergencyReport?.rotation_errors ?? {});

  async function refreshSnapshotState(): Promise<string[]> {
    if (!apiConfig) return [];
    const ids = await listWalletSnapshots(apiConfig);
    setSnapshotIds(ids);
    if (ids.includes(apiConfig.walletId)) {
      setSnapshotReport(await verifyWalletSnapshot(apiConfig));
    } else {
      setSnapshotReport(null);
    }
    return ids;
  }

  async function refreshWalletDetails() {
    if (!apiConfig) {
      setWalletDetails(null);
      return;
    }
    setWalletDetails(await loadWalletDetails(apiConfig));
  }

  async function refreshThresholdApprovalQueue() {
    if (!apiConfig) {
      setThresholdApprovals([]);
      setApprovalQueueStatus("idle");
      return;
    }
    setApprovalQueueStatus("loading");
    try {
      const approvals = await listThresholdApprovals(apiConfig, "all");
      setThresholdApprovals(approvals);
      setApprovalQueueStatus("loaded");
    } catch {
      setThresholdApprovals([]);
      setApprovalQueueStatus("failed");
    }
  }

  useEffect(() => {
    if (!apiConfig) return;
    let cancelled = false;
    Promise.all([refreshSnapshotState(), refreshWalletDetails(), refreshThresholdApprovalQueue()])
      .then(() => undefined)
      .catch(() => {
        if (!cancelled) {
          setSnapshotReport(null);
          setWalletDetails(null);
          setThresholdApprovals([]);
        }
      })
    return () => {
      cancelled = true;
    };
  }, [apiConfig]);

  useEffect(() => {
    if (apiConfig?.actorDid && !recoveryActorDid) {
      setRecoveryActorDid(apiConfig.actorDid);
    }
  }, [apiConfig?.actorDid, recoveryActorDid]);

  async function saveSnapshot() {
    if (!apiConfig) return;
    setSnapshotStatus("saving");
    try {
      await saveWalletSnapshot(apiConfig);
      await refreshSnapshotState();
      setSnapshotStatus("saved");
    } catch {
      setSnapshotStatus("failed");
    }
  }

  async function restoreSnapshot() {
    if (!apiConfig || !hasCurrentSnapshot) return;
    setSnapshotStatus("loading");
    try {
      await loadWalletSnapshot(apiConfig);
      setSnapshotReport(await verifyWalletSnapshot(apiConfig));
      await onSnapshotLoaded();
      await refreshWalletDetails();
      setSnapshotStatus("loaded");
    } catch {
      setSnapshotStatus("failed");
    }
  }

  async function checkWalletStorage() {
    if (!apiConfig) return;
    setStorageStatus("checking");
    try {
      const report = await verifyWalletStorage(apiConfig);
      setWalletStorageReport(report);
      setStorageStatus("verified");
      await refreshWalletAuditEvents();
    } catch {
      setWalletStorageReport(null);
      setStorageStatus("failed");
    }
  }

  async function repairWalletStorageReplicas() {
    if (!apiConfig?.actorDid) return;
    setStorageStatus("repairing");
    try {
      const report = await repairWalletStorage(apiConfig);
      setWalletStorageReport(report);
      setStorageStatus("repaired");
      await refreshWalletAuditEvents();
    } catch {
      setStorageStatus("failed");
    }
  }

  async function checkOpsHealth() {
    if (!apiConfig) return;
    setOpsStatus("checking");
    try {
      const report = await loadOpsHealth(apiConfig, true);
      setOpsHealthReport(report);
      setOpsStatus("checked");
      await refreshWalletAuditEvents();
    } catch {
      setOpsHealthReport(null);
      setOpsStatus("failed");
    }
  }

  async function requestGovernanceApproval(operation: WalletAdminOperation, requestedBy?: string) {
    if (!apiConfig) return;
    setGovernanceStatus("saving");
    try {
      const approval = await requestWalletAdminApproval(apiConfig, operation, requestedBy);
      if (operation.startsWith("wallet/controller")) {
        if (operation === "wallet/controller_recover") {
          setRecoveryControllerApprovalId(approval.approval_id);
        } else {
          setControllerApprovalId(approval.approval_id);
        }
      } else if (operation.startsWith("wallet/device")) {
        setDeviceApprovalId(approval.approval_id);
      } else if (operation === "wallet/recovery_policy_set") {
        setRecoveryPolicyApprovalId(approval.approval_id);
      } else {
        setEmergencyApprovalId(approval.approval_id);
      }
      setGovernanceMessage(`Approval ${approval.approval_id}`);
      setGovernanceStatus("requested");
      await refreshThresholdApprovalQueue();
    } catch {
      setGovernanceMessage("Wallet approval request failed.");
      setGovernanceStatus("failed");
    }
  }

  async function applyRecoveryPolicy(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!apiConfig) return;
    const contactDids = parseRecordIds(recoveryContactDids);
    setGovernanceStatus("saving");
    try {
      const wallet = await setWalletRecoveryPolicy(apiConfig, {
        approvalId: recoveryPolicyApprovalId.trim() || undefined,
        contactDids,
        threshold: recoveryThreshold
      });
      setWalletDetails(wallet);
      setGovernanceMessage("Recovery policy updated.");
      setGovernanceStatus("saved");
    } catch {
      setGovernanceMessage("Recovery policy update failed.");
      setGovernanceStatus("failed");
    }
  }

  async function requestRecoveryControllerApproval() {
    if (!apiConfig || !recoveryActorDid.trim()) return;
    await requestGovernanceApproval("wallet/controller_recover", recoveryActorDid.trim());
  }

  async function applyControllerRecovery(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!apiConfig || !recoveryActorDid.trim() || !recoveredControllerDid.trim()) return;
    setGovernanceStatus("saving");
    try {
      const wallet = await recoverWalletController(apiConfig, {
        actorDid: recoveryActorDid.trim(),
        approvalId: recoveryControllerApprovalId.trim() || undefined,
        controllerDid: recoveredControllerDid.trim()
      });
      setWalletDetails(wallet);
      setRecoveredControllerDid("");
      setRecoveryControllerApprovalId("");
      setGovernanceMessage("Controller recovered.");
      setGovernanceStatus("saved");
    } catch {
      setGovernanceMessage("Controller recovery failed.");
      setGovernanceStatus("failed");
    }
  }

  async function recordGovernanceApproval(approvalId: string) {
    if (!apiConfig || !approvalId.trim()) return;
    setGovernanceStatus("saving");
    setApprovalQueueStatus("approving");
    try {
      const approval = await approveThresholdApproval(apiConfig, approvalId.trim());
      setThresholdApprovals((approvals) =>
        approvals.map((item) => (item.approval_id === approval.approval_id ? approval : item))
      );
      await refreshThresholdApprovalQueue();
      setGovernanceMessage("Approval recorded.");
      setGovernanceStatus("saved");
    } catch {
      setGovernanceMessage("Approval failed.");
      setGovernanceStatus("failed");
      setApprovalQueueStatus("failed");
    }
  }

  async function applyControllerAdd(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!apiConfig || !controllerDid.trim()) return;
    setGovernanceStatus("saving");
    try {
      const wallet = await addWalletController(apiConfig, controllerDid.trim(), controllerApprovalId.trim() || undefined);
      setWalletDetails(wallet);
      setControllerDid("");
      setControllerApprovalId("");
      setGovernanceMessage("Controller updated.");
      setGovernanceStatus("saved");
    } catch {
      setGovernanceMessage("Controller update failed.");
      setGovernanceStatus("failed");
    }
  }

  async function applyControllerRemove(controller: string) {
    if (!apiConfig) return;
    setGovernanceStatus("saving");
    try {
      const wallet = await removeWalletController(apiConfig, controller, controllerApprovalId.trim() || undefined);
      setWalletDetails(wallet);
      setControllerApprovalId("");
      setGovernanceMessage("Controller removed.");
      setGovernanceStatus("saved");
    } catch {
      setGovernanceMessage("Controller removal failed.");
      setGovernanceStatus("failed");
    }
  }

  async function applyDeviceAdd(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!apiConfig || !deviceDid.trim()) return;
    setGovernanceStatus("saving");
    try {
      const wallet = await addWalletDevice(apiConfig, deviceDid.trim(), deviceApprovalId.trim() || undefined);
      setWalletDetails(wallet);
      setDeviceDid("");
      setDeviceApprovalId("");
      setGovernanceMessage("Device updated.");
      setGovernanceStatus("saved");
    } catch {
      setGovernanceMessage("Device update failed.");
      setGovernanceStatus("failed");
    }
  }

  async function applyDeviceRevoke(device: string) {
    if (!apiConfig) return;
    setGovernanceStatus("saving");
    try {
      const wallet = await revokeWalletDevice(apiConfig, device, deviceApprovalId.trim() || undefined);
      setWalletDetails(wallet);
      setDeviceApprovalId("");
      setGovernanceMessage("Device revoked.");
      setGovernanceStatus("saved");
    } catch {
      setGovernanceMessage("Device revocation failed.");
      setGovernanceStatus("failed");
    }
  }

  async function applyEmergencyRevoke(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!apiConfig) return;
    setGovernanceStatus("saving");
    try {
      const report = await emergencyRevoke(apiConfig, {
        approvalId: emergencyApprovalId.trim() || undefined,
        reason: emergencyReason.trim() || undefined,
        rotateKeys: emergencyRotateKeys
      });
      setEmergencyReport(report);
      setEmergencyApprovalId("");
      setGovernanceMessage(
        `Emergency revoke completed: ${report.revoked_grant_count} grants revoked, ${report.rotated_record_count} records rotated.`
      );
      setGovernanceStatus("saved");
      await refreshWalletDetails();
    } catch {
      setGovernanceMessage("Emergency revoke failed.");
      setGovernanceStatus("failed");
    }
  }

  return (
    <div className="screen">
      <div className="page-title">
        <p className="eyebrow">Security</p>
        <h1>Account safety</h1>
      </div>
      {!apiConfig ? (
        <StatusBanner tone="warning">Connect the wallet API environment to use persisted wallet snapshots.</StatusBanner>
      ) : null}
      {snapshotStatus === "saved" ? <StatusBanner tone="success">Wallet snapshot saved.</StatusBanner> : null}
      {snapshotStatus === "loaded" ? <StatusBanner tone="success">Wallet snapshot loaded.</StatusBanner> : null}
      {snapshotStatus === "failed" ? <StatusBanner tone="warning">Wallet snapshot action failed.</StatusBanner> : null}
      {storageStatus === "verified" && walletStorageReport ? (
        <StatusBanner tone={walletStorageReport.ok ? "success" : "warning"}>
          {walletStorageReport.ok ? "Encrypted storage replicas verified." : "Encrypted storage needs repair."}
        </StatusBanner>
      ) : null}
      {storageStatus === "repaired" && walletStorageReport ? (
        <StatusBanner tone={walletStorageReport.ok ? "success" : "warning"}>
          {walletStorageReport.ok ? "Encrypted storage replicas repaired." : "Encrypted storage repair incomplete."}
        </StatusBanner>
      ) : null}
      {storageStatus === "failed" ? <StatusBanner tone="warning">Wallet storage verification failed.</StatusBanner> : null}
      {opsStatus === "checked" && opsHealthReport ? (
        <StatusBanner tone={opsHealthReport.status === "error" ? "warning" : "success"}>
          Operations health: {opsHealthReport.status}.
        </StatusBanner>
      ) : null}
      {opsStatus === "failed" ? <StatusBanner tone="warning">Operations health check failed.</StatusBanner> : null}
      {governanceStatus === "requested" ? <StatusBanner tone="info">{governanceMessage}</StatusBanner> : null}
      {governanceStatus === "saved" ? <StatusBanner tone="success">{governanceMessage}</StatusBanner> : null}
      {governanceStatus === "failed" ? <StatusBanner tone="warning">{governanceMessage}</StatusBanner> : null}
      <Section
        title="Wallet persistence"
        actions={
          <Badge tone={hasCurrentSnapshot ? "success" : "warning"}>
            {hasCurrentSnapshot ? "snapshot ready" : "no snapshot"}
          </Badge>
        }
      >
        <div className="disclosure-package">
          <div className="disclosure-row">
            <strong>Wallet</strong>
            <span>{apiConfig?.walletId ?? "Not connected"}</span>
          </div>
          <div className="disclosure-row">
            <strong>Snapshots</strong>
            <span>{snapshotIds.length}</span>
          </div>
          <div className="disclosure-row">
            <strong>Repository</strong>
            <span>{apiConfig ? "metadata snapshot store" : "API required"}</span>
          </div>
          <div className="disclosure-row">
            <strong>Integrity</strong>
            <span>{snapshotReport ? (snapshotReport.valid ? "verified" : "failed") : "not checked"}</span>
          </div>
          <div className="disclosure-row">
            <strong>Encrypted storage</strong>
            <span>
              {walletStorageReport
                ? walletStorageReport.ok
                  ? "verified"
                  : `${walletStorageReport.failed_replica_count} failed replicas`
                : "not checked"}
            </span>
          </div>
          <div className="disclosure-row">
            <strong>Replicas</strong>
            <span>{walletStorageReport ? `${walletStorageReport.replica_count} across ${walletStorageReport.record_count} records` : "Not checked"}</span>
          </div>
          <div className="disclosure-row">
            <strong>Providers</strong>
            <span>{storageProviderSummary}</span>
          </div>
          <div className="disclosure-row">
            <strong>Snapshot hash</strong>
            <span>{snapshotReport?.computed_hash ? <code>{shortHash(snapshotReport.computed_hash)}</code> : "Unavailable"}</span>
          </div>
          <div className="disclosure-row">
            <strong>Ops health</strong>
            <span>{opsHealthReport ? opsHealthReport.status : "not checked"}</span>
          </div>
          <div className="disclosure-row">
            <strong>Ops checks</strong>
            <span>{opsCheckSummary}</span>
          </div>
          <div className="disclosure-row">
            <strong>Proof backend</strong>
            <span>{proofBackendVerifier || proofBackendMode || "Not checked"}</span>
          </div>
          <div className="disclosure-row">
            <strong>Proof backend health</strong>
            <span>
              {proofRegistryCheck ? (
                <>
                  <Badge tone={opsHealthTone(proofRegistryCheck.status)}>{proofRegistryCheck.status}</Badge>
                  {proofBackendHealthStatus ? ` ${proofBackendHealthStatus}` : ""}
                  {proofBackendHealthError ? ` (${proofBackendHealthError})` : ""}
                </>
              ) : (
                "Not checked"
              )}
            </span>
          </div>
        </div>
        {opsHealthReport ? (
          <div className="disclosure-package" aria-live="polite">
            {opsHealthReport.checks.map((check) => {
              const verifierLabel =
                check.name === "proof_registry"
                  ? [stringDetail(check.details, "verifier_id"), stringDetail(check.details, "proof_system")]
                      .filter(Boolean)
                      .join(" / ")
                  : null;
              const health = objectDetail(check.details, "backend_health");
              const healthStatus = stringDetail(health ?? undefined, "status");
              const healthError = stringDetail(health ?? undefined, "error");
              return (
                <div className="disclosure-row" key={check.name}>
                  <strong>{check.name}</strong>
                  <span>
                    <Badge tone={opsHealthTone(check.status)}>{check.status}</Badge> {check.summary}
                    {verifierLabel ? ` (${verifierLabel})` : ""}
                    {healthStatus ? ` [${healthStatus}]` : ""}
                    {healthError ? ` ${healthError}` : ""}
                  </span>
                </div>
              );
            })}
          </div>
        ) : null}
        <div className="row-actions">
          <Button disabled={!apiConfig || snapshotStatus === "saving" || snapshotStatus === "loading"} onClick={saveSnapshot}>
            <Archive size={18} /> {snapshotStatus === "saving" ? "Saving" : "Save snapshot"}
          </Button>
          <Button
            disabled={!apiConfig || !hasCurrentSnapshot || snapshotStatus === "saving" || snapshotStatus === "loading"}
            onClick={restoreSnapshot}
            variant="secondary"
          >
            <RefreshCw size={18} /> {snapshotStatus === "loading" ? "Loading" : "Load snapshot"}
          </Button>
          <Button
            disabled={!apiConfig || storageStatus === "checking" || storageStatus === "repairing"}
            onClick={checkWalletStorage}
            variant="secondary"
          >
            <Wrench size={18} /> {storageStatus === "checking" ? "Checking" : "Check storage"}
          </Button>
          <Button
            disabled={!apiConfig?.actorDid || storageStatus === "checking" || storageStatus === "repairing"}
            onClick={repairWalletStorageReplicas}
            variant="secondary"
          >
            <RefreshCw size={18} /> {storageStatus === "repairing" ? "Repairing" : "Repair storage"}
          </Button>
          <Button disabled={!apiConfig || opsStatus === "checking"} onClick={checkOpsHealth} variant="secondary">
            <ShieldCheck size={18} /> {opsStatus === "checking" ? "Checking" : "Run ops health"}
          </Button>
        </div>
      </Section>
      <Section
        title="Approval queue"
        actions={
          <Badge tone={pendingThresholdApprovals.length ? "warning" : "success"}>
            {pendingThresholdApprovals.length ? `${pendingThresholdApprovals.length} pending` : "clear"}
          </Badge>
        }
      >
        {approvalQueueStatus === "failed" ? (
          <StatusBanner tone="warning">Approval queue unavailable.</StatusBanner>
        ) : null}
        <div className="row-actions">
          <Button
            disabled={!apiConfig || approvalQueueStatus === "loading" || approvalQueueStatus === "approving"}
            onClick={refreshThresholdApprovalQueue}
            variant="secondary"
          >
            <RefreshCw size={18} /> {approvalQueueStatus === "loading" ? "Loading" : "Refresh approvals"}
          </Button>
        </div>
        <div className="list-stack">
          {thresholdApprovals.length ? (
            thresholdApprovals.map((approval) => {
              const approvedCount = thresholdApprovalCount(approval);
              const actorDid = apiConfig?.actorDid ?? "";
              const actorRecorded = Boolean(actorDid && approval.approvals?.[actorDid]);
              const canRecord = Boolean(apiConfig?.actorDid && approval.status === "pending" && !actorRecorded);
              return (
                <article className="list-item" key={approval.approval_id}>
                  <div>
                    <div className="scope-header">
                      <div>
                        <h3>{approval.operation}</h3>
                        <p>{approval.requested_by}</p>
                      </div>
                      <Badge tone={thresholdApprovalTone(approval.status)}>{approval.status}</Badge>
                    </div>
                    <div className="badge-row">
                      <Badge>{shortHash(approval.approval_id)}</Badge>
                      <Badge tone={approvedCount >= approval.threshold ? "success" : "warning"}>
                        {approvedCount}/{approval.threshold} approvals
                      </Badge>
                      <Badge>{thresholdApprovalDateLabel(approval.created_at)}</Badge>
                    </div>
                    <div className="disclosure-package">
                      <div className="disclosure-row">
                        <strong>Abilities</strong>
                        <span>{approval.abilities.join(", ")}</span>
                      </div>
                      <div className="disclosure-row">
                        <strong>Resources</strong>
                        <span>{approval.resources.join(", ")}</span>
                      </div>
                      <div className="disclosure-row">
                        <strong>Approvers</strong>
                        <span>{approval.approver_dids?.join(", ") || "Wallet controllers"}</span>
                      </div>
                    </div>
                  </div>
                  <div className="row-actions">
                    <Button
                      disabled={!canRecord || approvalQueueStatus === "approving" || governanceStatus === "saving"}
                      onClick={() => recordGovernanceApproval(approval.approval_id)}
                      variant="secondary"
                    >
                      <KeyRound size={18} /> {actorRecorded ? "Recorded" : "Record approval"}
                    </Button>
                  </div>
                </article>
              );
            })
          ) : (
            <small>No threshold approvals are waiting on this wallet.</small>
          )}
        </div>
      </Section>
      <Section
        title="Wallet governance"
        actions={
          <Badge tone={governanceThreshold > 1 ? "warning" : "success"}>
            {governanceThreshold > 1 ? `${governanceThreshold} approvals` : "single approval"}
          </Badge>
        }
      >
        <div className="disclosure-package">
          <div className="disclosure-row">
            <strong>Owner</strong>
            <span>{walletDetails?.owner_did ?? "Unavailable"}</span>
          </div>
          <div className="disclosure-row">
            <strong>Current actor</strong>
            <span>{apiConfig?.actorDid ?? "Not configured"}</span>
          </div>
          <div className="disclosure-row">
            <strong>Approvers</strong>
            <span>{governanceApprovals.length ? governanceApprovals.join(", ") : "Unavailable"}</span>
          </div>
          <div className="disclosure-row">
            <strong>Manifest</strong>
            <span>{walletDetails?.manifest_head ? <code>{shortHash(walletDetails.manifest_head)}</code> : "Unavailable"}</span>
          </div>
        </div>
        <form className="form-grid" onSubmit={applyControllerAdd}>
          <Field label="Controller DID" required>
            <input
              disabled={!apiConfig}
              onChange={(event) => setControllerDid(event.target.value)}
              placeholder="did:key:new-controller"
              value={controllerDid}
            />
          </Field>
          <Field label="Wallet admin approval ID">
            <input
              disabled={!apiConfig}
              onChange={(event) => setControllerApprovalId(event.target.value)}
              placeholder="approval-..."
              value={controllerApprovalId}
            />
          </Field>
          <div className="row-actions full-span">
            <Button
              disabled={!apiConfig || !controllerDid.trim() || governanceStatus === "saving"}
              onClick={() => requestGovernanceApproval("wallet/controller_add")}
              variant="secondary"
            >
              <ShieldCheck size={18} /> Request add approval
            </Button>
            <Button
              disabled={!apiConfig || governanceStatus === "saving"}
              onClick={() => requestGovernanceApproval("wallet/controller_remove")}
              variant="secondary"
            >
              <ShieldCheck size={18} /> Request remove approval
            </Button>
            <Button
              disabled={!apiConfig || !controllerApprovalId.trim() || governanceStatus === "saving"}
              onClick={() => recordGovernanceApproval(controllerApprovalId)}
              variant="secondary"
            >
              <KeyRound size={18} /> Record approval
            </Button>
            <Button disabled={!apiConfig || !controllerDid.trim() || governanceStatus === "saving"} type="submit">
              <UserPlus size={18} /> Add controller
            </Button>
          </div>
        </form>
        <div className="list-stack">
          {(walletDetails?.controller_dids ?? []).map((controller) => (
            <article className="list-item" key={controller}>
              <div>
                <h3>{controller === walletDetails?.owner_did ? "Owner controller" : "Controller"}</h3>
                <p>{controller}</p>
                <div className="badge-row">
                  <Badge tone={governanceApprovals.includes(controller) ? "success" : "neutral"}>
                    {governanceApprovals.includes(controller) ? "approver" : "controller"}
                  </Badge>
                </div>
              </div>
              {controller !== walletDetails?.owner_did ? (
                <div className="row-actions">
                  <Button
                    disabled={!apiConfig || governanceStatus === "saving"}
                    onClick={() => applyControllerRemove(controller)}
                    variant="danger"
                  >
                    <UserMinus size={18} /> Remove
                  </Button>
                </div>
              ) : null}
            </article>
          ))}
        </div>
      </Section>
      <Section
        title="Recovery policy"
        actions={
          <Badge tone={recoveryPolicy?.status === "active" ? "success" : "warning"}>
            {recoveryPolicy?.status === "active" ? `${recoveryPolicy.threshold} recovery approvals` : "not active"}
          </Badge>
        }
      >
        <div className="disclosure-package">
          <div className="disclosure-row">
            <strong>Contacts</strong>
            <span>{recoveryContacts.length ? recoveryContacts.join(", ") : "Unavailable"}</span>
          </div>
          <div className="disclosure-row">
            <strong>Threshold</strong>
            <span>{recoveryPolicy?.threshold ?? "Unavailable"}</span>
          </div>
          <div className="disclosure-row">
            <strong>Status</strong>
            <span>{recoveryPolicy?.status ?? "Unavailable"}</span>
          </div>
        </div>
        <form className="form-grid" onSubmit={applyRecoveryPolicy}>
          <Field label="Recovery contact DIDs" required>
            <textarea
              disabled={!apiConfig}
              onChange={(event) => setRecoveryContactDids(event.target.value)}
              placeholder="did:key:recovery-a, did:key:recovery-b"
              rows={3}
              value={recoveryContactDids}
            />
          </Field>
          <Field label="Recovery threshold" required>
            <input
              disabled={!apiConfig}
              min={1}
              onChange={(event) => setRecoveryThreshold(Number(event.target.value))}
              type="number"
              value={recoveryThreshold}
            />
          </Field>
          <Field label="Wallet admin approval ID">
            <input
              disabled={!apiConfig}
              onChange={(event) => setRecoveryPolicyApprovalId(event.target.value)}
              placeholder="approval-..."
              value={recoveryPolicyApprovalId}
            />
          </Field>
          <div className="row-actions full-span">
            <Button
              disabled={!apiConfig || governanceStatus === "saving"}
              onClick={() => requestGovernanceApproval("wallet/recovery_policy_set")}
              variant="secondary"
            >
              <ShieldCheck size={18} /> Request policy approval
            </Button>
            <Button
              disabled={!apiConfig || !recoveryPolicyApprovalId.trim() || governanceStatus === "saving"}
              onClick={() => recordGovernanceApproval(recoveryPolicyApprovalId)}
              variant="secondary"
            >
              <KeyRound size={18} /> Record approval
            </Button>
            <Button disabled={!apiConfig || governanceStatus === "saving"} type="submit">
              <UsersRound size={18} /> Save recovery policy
            </Button>
          </div>
        </form>
        <form className="form-grid" onSubmit={applyControllerRecovery}>
          <Field label="Recovery actor DID" required>
            <input
              disabled={!apiConfig}
              onChange={(event) => setRecoveryActorDid(event.target.value)}
              placeholder="did:key:recovery-a"
              value={recoveryActorDid}
            />
          </Field>
          <Field label="Recovered controller DID" required>
            <input
              disabled={!apiConfig}
              onChange={(event) => setRecoveredControllerDid(event.target.value)}
              placeholder="did:key:recovered-controller"
              value={recoveredControllerDid}
            />
          </Field>
          <Field label="Recovery approval ID">
            <input
              disabled={!apiConfig}
              onChange={(event) => setRecoveryControllerApprovalId(event.target.value)}
              placeholder="approval-..."
              value={recoveryControllerApprovalId}
            />
          </Field>
          <div className="row-actions full-span">
            <Button
              disabled={!apiConfig || !recoveryActorDid.trim() || governanceStatus === "saving"}
              onClick={requestRecoveryControllerApproval}
              variant="secondary"
            >
              <ShieldCheck size={18} /> Request recovery approval
            </Button>
            <Button
              disabled={!apiConfig || !recoveryControllerApprovalId.trim() || governanceStatus === "saving"}
              onClick={() => recordGovernanceApproval(recoveryControllerApprovalId)}
              variant="secondary"
            >
              <KeyRound size={18} /> Record approval
            </Button>
            <Button
              disabled={!apiConfig || !recoveryActorDid.trim() || !recoveredControllerDid.trim() || governanceStatus === "saving"}
              type="submit"
            >
              <UserPlus size={18} /> Recover controller
            </Button>
          </div>
        </form>
      </Section>
      <Section title="Trusted devices">
        <form className="form-grid" onSubmit={applyDeviceAdd}>
          <Field label="Device DID" required>
            <input
              disabled={!apiConfig}
              onChange={(event) => setDeviceDid(event.target.value)}
              placeholder="did:key:phone-or-tablet"
              value={deviceDid}
            />
          </Field>
          <Field label="Wallet admin approval ID">
            <input
              disabled={!apiConfig}
              onChange={(event) => setDeviceApprovalId(event.target.value)}
              placeholder="approval-..."
              value={deviceApprovalId}
            />
          </Field>
          <div className="row-actions full-span">
            <Button
              disabled={!apiConfig || !deviceDid.trim() || governanceStatus === "saving"}
              onClick={() => requestGovernanceApproval("wallet/device_add")}
              variant="secondary"
            >
              <ShieldCheck size={18} /> Request add approval
            </Button>
            <Button
              disabled={!apiConfig || governanceStatus === "saving"}
              onClick={() => requestGovernanceApproval("wallet/device_revoke")}
              variant="secondary"
            >
              <ShieldCheck size={18} /> Request revoke approval
            </Button>
            <Button
              disabled={!apiConfig || !deviceApprovalId.trim() || governanceStatus === "saving"}
              onClick={() => recordGovernanceApproval(deviceApprovalId)}
              variant="secondary"
            >
              <KeyRound size={18} /> Record approval
            </Button>
            <Button disabled={!apiConfig || !deviceDid.trim() || governanceStatus === "saving"} type="submit">
              <Smartphone size={18} /> Add device
            </Button>
          </div>
        </form>
        <div className="list-stack">
          {(walletDetails?.device_dids ?? []).map((device) => (
            <article className="list-item" key={device}>
              <div>
                <h3>{device === walletDetails?.owner_did ? "Primary device" : "Trusted device"}</h3>
                <p>{device}</p>
                <div className="badge-row">
                  <Badge tone="success">active</Badge>
                </div>
              </div>
              {device !== walletDetails?.owner_did ? (
                <div className="row-actions">
                  <Button
                    disabled={!apiConfig || governanceStatus === "saving"}
                    onClick={() => applyDeviceRevoke(device)}
                    variant="danger"
                  >
                    <UserMinus size={18} /> Revoke
                  </Button>
                </div>
              ) : null}
            </article>
          ))}
        </div>
      </Section>
      <Section
        title="Emergency revoke"
        actions={
          <Badge tone={emergencyReport ? (emergencyRotationErrors.length ? "warning" : "success") : "danger"}>
            {emergencyReport ? "completed" : "wallet-wide"}
          </Badge>
        }
      >
        <form className="form-grid" onSubmit={applyEmergencyRevoke}>
          <Field label="Incident reason">
            <input
              disabled={!apiConfig}
              onChange={(event) => setEmergencyReason(event.target.value)}
              placeholder="suspected compromise"
              value={emergencyReason}
            />
          </Field>
          <Field label="Wallet admin approval ID">
            <input
              disabled={!apiConfig}
              onChange={(event) => setEmergencyApprovalId(event.target.value)}
              placeholder="approval-..."
              value={emergencyApprovalId}
            />
          </Field>
          <label className="consent-box full-span">
            <input
              checked={emergencyRotateKeys}
              disabled={!apiConfig}
              onChange={(event) => setEmergencyRotateKeys(event.target.checked)}
              type="checkbox"
            />
            <span>
              <strong>Rotate record keys</strong>
            </span>
          </label>
          <div className="row-actions full-span">
            <Button
              disabled={!apiConfig || governanceStatus === "saving"}
              onClick={() => requestGovernanceApproval("wallet/emergency_revoke")}
              variant="secondary"
            >
              <ShieldCheck size={18} /> Request emergency approval
            </Button>
            <Button
              disabled={!apiConfig || !emergencyApprovalId.trim() || governanceStatus === "saving"}
              onClick={() => recordGovernanceApproval(emergencyApprovalId)}
              variant="secondary"
            >
              <KeyRound size={18} /> Record approval
            </Button>
            <Button disabled={!apiConfig || governanceStatus === "saving"} type="submit" variant="danger">
              <LockKeyhole size={18} /> Revoke access
            </Button>
          </div>
        </form>
        {emergencyReport ? (
          <div className="disclosure-package" aria-live="polite">
            <div className="disclosure-row">
              <strong>Revoked grants</strong>
              <span>{emergencyReport.revoked_grant_count}</span>
            </div>
            <div className="disclosure-row">
              <strong>Rotated records</strong>
              <span>{emergencyReport.rotated_record_count}</span>
            </div>
            <div className="disclosure-row">
              <strong>Key rotation errors</strong>
              <span>
                {emergencyRotationErrors.length
                  ? emergencyRotationErrors.map(([recordId, error]) => `${recordId}: ${error}`).join(", ")
                  : "None"}
              </span>
            </div>
            <div className="disclosure-row">
              <strong>Reason</strong>
              <span>{emergencyReport.reason || "Not recorded"}</span>
            </div>
          </div>
        ) : null}
      </Section>
    </div>
  );
}

function AuditScreen({ events }: { events: AuditEvent[] }) {
  return (
    <div className="screen">
      <div className="page-title">
        <p className="eyebrow">Audit</p>
        <h1>Consent and access history</h1>
      </div>
      <div className="timeline">
        {events.map((event) => (
          <article className="timeline-event" key={event.id}>
            <span aria-hidden="true" />
            <div>
              <h3>{event.action}</h3>
              <p>
                {event.actor} · {event.timestamp}
              </p>
              {event.resource || event.decision || event.grantId ? (
                <small>
                  {[event.decision, event.resource, event.grantId].filter(Boolean).join(" · ")}
                </small>
              ) : null}
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
