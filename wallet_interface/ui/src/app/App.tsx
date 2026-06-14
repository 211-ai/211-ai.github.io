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
  ShieldCheck,
  Upload,
  UsersRound,
  Wrench
} from "lucide-react";
import { ActionCard, Badge, Button, Field, Section, StatusBanner } from "../components/ui";
import { AgentChatDrawer } from "../components/agent/AgentChatDrawer";
import { WorldIdVerificationPanel } from "../components/world-id/WorldIdVerificationPanel";
import { getRouteLabel } from "../agent/surfaceRegistry";
import {
  getServiceDetailDocIdFromHash,
  openCanonicalServiceDetailRoute,
  setLocationServiceDetailHash
} from "../agent/tools/serviceDetailTools";
import type { AppActionRuntime } from "./appActions";
import { useAgentChatService } from "../services/agentChatService";
import { ServiceDetailScreen } from "./ServiceDetailScreen";
import { search211Info } from "../services/graphRagService";
import type { SearchResult } from "../lib/graphrag";
import {
  CheckInChannel,
  AuditEvent,
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
  nonGrantedCapabilities,
  plainCapabilitySummary,
  plainNonGrantedCapabilities
} from "../services/capabilities";
import {
  addBinaryDocument,
  addTextDocument,
  createLocationRegionProof,
  createVerifiedExportBundleView,
  importExportBundleView,
  listWalletSnapshots,
  loadWalletAccessState,
  loadExportBundleView,
  loadWalletSnapshot,
  listWalletAuditEvents,
  listWalletDocuments,
  listWalletProofReceipts,
  repairRecordStorage,
  saveWalletSnapshot,
  verifyWalletSnapshot,
  WalletSnapshotVerification,
  WalletApiConfig
} from "../services/walletApi";
import {
  APP_PERSIST_KEY,
  appRoutes,
  createDefaultAppState,
  defaultManagedUserDraft,
  defaultShelterChecklist,
  disclosureScopes,
  getRouteFromHash,
  primaryRoutes,
  readPersistedAppState,
  secondaryRoutes,
  serviceNeeds,
  setLocationRouteHash,
  shelterOptions,
  ShelterStaffAccount,
  ShelterUserAccount,
  writePersistedAppState
} from "./appState";

const APP_SESSION_KEY = "abby-ui-session-v1";
const WALLET_API_CONFIG_KEY = "abby-wallet-api-config";
const ID_DOCUMENT_ACCEPT_ATTR = "image/jpeg,image/png,image/webp,application/pdf,.jpg,.jpeg,.png,.webp,.pdf";
const ID_DOCUMENT_ACCEPTED_TYPES = new Set(["image/jpeg", "image/png", "image/webp", "application/pdf"]);
const ID_DOCUMENT_ACCEPTED_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp", ".pdf"];

const routeIcons: Record<RouteId, typeof Home> = {
  home: Home,
  register: ClipboardCheck,
  "check-in": CalendarCheck,
  contacts: ContactRound,
  "sharing-rules": ShieldCheck,
  uploads: FileUp,
  "social-services": HeartHandshake,
  shelter: UsersRound,
  "recipient-access": KeyRound,
  "benefits-protection": Landmark,
  analytics: BarChart3,
  "proof-center": ShieldCheck,
  exports: LogOut,
  security: LockKeyhole,
  audit: ClipboardCheck
};

const removedStandaloneRoutes = new Set<RouteId>(["sharing-rules", "recipient-access", "benefits-protection"]);
const routes = primaryRoutes
  .filter((route) => !removedStandaloneRoutes.has(route.id))
  .map((route) => ({ ...route, icon: routeIcons[route.id] }));
const secondaryNavigationRoutes = secondaryRoutes
  .filter((route) => !removedStandaloneRoutes.has(route.id))
  .map((route) => ({ ...route, icon: routeIcons[route.id] }));
const navigationRoutes = [...routes, ...secondaryNavigationRoutes];

function normalizeAppRoute(route: RouteId): RouteId {
  return removedStandaloneRoutes.has(route) ? "home" : route;
}

function getInitialRouteFromHash(): RouteId {
  return getServiceDetailDocIdFromHash() ? "social-services" : normalizeAppRoute(getRouteFromHash());
}

function readSignedInUser(): string {
  if (typeof window === "undefined") return "";
  try {
    const raw = window.localStorage.getItem(APP_SESSION_KEY);
    if (!raw) return "";
    const parsed = JSON.parse(raw);
    return typeof parsed?.username === "string" ? parsed.username : "";
  } catch {
    return "";
  }
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

function formatRecipientType(type: DisclosureRecipientType): string {
  const labels: Record<DisclosureRecipientType, string> = {
    benefits_agency: "Benefits agency",
    emergency_contact: "Emergency contact",
    government_liaison: "Government help",
    police_precinct: "Police precinct",
    shelter_staff: "Shelter staff",
    social_worker: "Social worker"
  };
  return labels[type];
}

function formatAnalyticsField(field: string): string {
  const labels: Record<string, string> = {
    county: "county",
    need_category: "need type"
  };
  return labels[field] ?? field.replace(/_/g, " ");
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

export function App() {
  const persistedState = useMemo(() => readPersistedAppState(), []);
  const defaultAppState = useMemo(() => createDefaultAppState(persistedState), [persistedState]);
  const [signedInUser, setSignedInUser] = useState(readSignedInUser);
  const activeRouteRef = useRef<RouteId>(getInitialRouteFromHash());
  const [activeRoute, setActiveRoute] = useState<RouteId>(activeRouteRef.current);
  const [serviceDetailDocId, setServiceDetailDocId] = useState<string | null>(getServiceDetailDocIdFromHash());
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
  const [walletAuditEvents, setWalletAuditEvents] = useState<AuditEvent[]>(auditEvents);
  const [walletProofReceipts, setWalletProofReceipts] = useState<ProofReceiptView[]>(proofReceipts);
  const [exportBundleViews, setExportBundleViews] = useState<ExportBundleView[]>(exportBundles);
  const [accessRequests, setAccessRequests] = useState(initialAccessRequests);
  const [grantReceipts, setGrantReceipts] = useState(initialGrantReceipts);
  const [savedServices, setSavedServices] = useState<SavedService[]>([]);
  const [servicePlans, setServicePlans] = useState<ServicePlan[]>([]);
  const [serviceInteractions, setServiceInteractions] = useState<ServiceInteractionEvent[]>([]);
  const [benefitsOptIn] = useState(defaultAppState.benefitsOptIn);
  const [analyticsOptIn, setAnalyticsOptIn] = useState<Record<string, boolean>>(() => defaultAppState.analyticsOptIn);
  const [shelterChecklist, setShelterChecklist] = useState(() => defaultAppState.shelterChecklist);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [agentChatOpen, setAgentChatOpen] = useState(false);
  const walletApiConfig = useMemo(readWalletApiConfig, []);

  async function refreshWalletAccessState() {
    if (!walletApiConfig) return;
    const state = await loadWalletAccessState(walletApiConfig);
    setAccessRequests(state.accessRequests.length ? state.accessRequests : initialAccessRequests);
    setGrantReceipts(state.grantReceipts.length ? state.grantReceipts : initialGrantReceipts);
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
      refreshWalletAuditEvents().catch(() => setWalletAuditEvents(auditEvents)),
      refreshWalletDocuments().catch(() => setUploads(initialUploads)),
      refreshWalletProofReceipts().catch(() => setWalletProofReceipts(proofReceipts))
    ]);
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
        uploads,
        accessRequests,
        grantReceipts,
        walletAuditEvents,
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
      analyticsOptIn,
      policy,
      profile,
      recipients,
      savedServices,
      serviceInteractions,
      servicePlans,
      shelterContactRequests,
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
    activeRouteRef.current = activeRoute;
  }, [activeRoute]);

  useEffect(() => {
    const syncRouteFromHash = () => {
      const detailDocId = getServiceDetailDocIdFromHash();
      const nextRoute = detailDocId ? "social-services" : normalizeAppRoute(getRouteFromHash());
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
      benefitsOptIn,
      analyticsOptIn,
      shelterChecklist
    });
  }, [
    analyticsOptIn,
    benefitsOptIn,
    policy,
    profile,
    recipients,
    shelterContactRequests,
    shelterChecklist,
    shelterStaffAccounts,
    shelterUserAccounts,
    uploads
  ]);

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
    setServiceDetailDocId(null);
    setMobileNavOpen(false);
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
      window.location.hash = "#/";
    }
  }

  const nextCheckIn = useMemo(() => {
    const next = new Date(policy.lastCheckInAt);
    next.setDate(next.getDate() + policy.intervalDays);
    return next.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
  }, [policy.intervalDays, policy.lastCheckInAt]);

  const routes = useMemo(() => primaryRoutes.map((route) => ({ ...route, icon: routeIcons[route.id] })), []);
  const secondaryNavigationRoutes = useMemo(() => secondaryRoutes.map((route) => ({ ...route, icon: routeIcons[route.id] })), []);
  const navigationRoutes = useMemo(() => appRoutes.map((route) => ({ ...route, icon: routeIcons[route.id] })), []);

  if (!signedInUser) {
    return <LoginScreen onSignIn={handleSignIn} />;
  }

  return (
    <div className={`app ${agentChatOpen ? "app-chat-open" : ""}`}>
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
          {secondaryNavigationRoutes.map((route) => (
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
          <div className="topbar-actions">
            <Button
              ariaControls="agent-chat-bottom-sheet"
              ariaExpanded={agentChatOpen}
              ariaLabel={agentChatOpen ? "Close assistant" : "Open assistant"}
              onClick={() => setAgentChatOpen((open) => !open)}
              variant="quiet"
            >
              <MessageSquare size={20} />
            </Button>
            <Button ariaLabel="Sign out" onClick={handleSignOut} variant="quiet">
              <LogOut size={20} />
            </Button>
          </div>
        </header>

        {mobileNavOpen ? (
          <nav className="mobile-nav-panel" id="mobile-navigation" aria-label="Mobile navigation">
            {navigationRoutes.map((route) => (
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
          <CheckInScreen nextCheckIn={nextCheckIn} policy={policy} profile={profile} setPolicy={setPolicy} />
        ) : null}
        {activeRoute === "contacts" ? (
          <ContactsScreen
            contactRequests={shelterContactRequests}
            profile={profile}
            recipients={recipients}
            setContactRequests={setShelterContactRequests}
            setRecipients={setRecipients}
          />
        ) : null}
        {activeRoute === "uploads" ? (
          <UploadsScreen
            apiConfig={walletApiConfig}
            refreshWalletAuditEvents={refreshWalletAuditEvents}
            uploads={uploads}
            setUploads={setUploads}
          />
        ) : null}
        {serviceDetailDocId ? (
          <ServiceDetailScreen docId={serviceDetailDocId} onBack={() => navigate("social-services")} />
        ) : null}
        {activeRoute === "social-services" && !serviceDetailDocId ? <SocialServicesScreen /> : null}
        {activeRoute === "shelter" ? (
          <ShelterScreen
            checklist={shelterChecklist}
            setChecklist={setShelterChecklist}
            contactRequests={shelterContactRequests}
            recipients={recipients}
            setContactRequests={setShelterContactRequests}
            setRecipients={setRecipients}
            shelterStaffAccounts={shelterStaffAccounts}
            setShelterStaffAccounts={setShelterStaffAccounts}
            shelterUserAccounts={shelterUserAccounts}
            setShelterUserAccounts={setShelterUserAccounts}
          />
        ) : null}
        {activeRoute === "analytics" ? (
          <AnalyticsScreen optedIn={analyticsOptIn} setOptedIn={setAnalyticsOptIn} />
        ) : null}
        {activeRoute === "proof-center" ? (
          <ProofCenterScreen
            apiConfig={walletApiConfig}
            proofs={walletProofReceipts}
            refreshWalletAuditEvents={refreshWalletAuditEvents}
            refreshWalletProofReceipts={refreshWalletProofReceipts}
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
          <SecurityScreen apiConfig={walletApiConfig} onSnapshotLoaded={refreshWalletAfterSnapshotLoad} />
        ) : null}
        {activeRoute === "audit" ? <AuditScreen events={walletAuditEvents} /> : null}
      </main>
      <AgentChatDrawer
        activeRouteLabel={getRouteLabel(activeRoute)}
        confirmations={agentChat.pendingConfirmations}
        evidenceBundles={agentChat.snapshot.session.evidenceBundles}
        messages={agentChat.messages}
        onCancelConfirmation={(confirmationId) => agentChat.denyConfirmation(confirmationId)}
        onClose={() => setAgentChatOpen(false)}
        onConfirmConfirmation={(confirmationId) => agentChat.approveConfirmation(confirmationId)}
        onOpenServiceDetail={(docId) =>
          openCanonicalServiceDetailRoute(docId, {
            setActiveRoute: (route) => {
              const nextRoute = normalizeAppRoute(route);
              activeRouteRef.current = nextRoute;
              setActiveRoute(nextRoute);
            },
            setServiceDetailDocId,
            setMobileNavOpen
          })
        }
        onSend={(message) => {
          void agentChat.sendMessage(message);
        }}
        onToggle={() => setAgentChatOpen((open) => !open)}
        open={agentChatOpen}
        responding={agentChat.responding}
        toolCalls={agentChat.snapshot.session.toolCalls}
        toolResults={agentChat.snapshot.session.toolResults}
      />
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

function LoginScreen({ onSignIn }: { onSignIn: (username: string) => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const canSignIn = username.trim().length > 0 && password.trim().length > 0;

  function submitLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (canSignIn) {
      onSignIn(username);
    }
  }

  return (
    <main className="login-page">
      <form className="login-panel" onSubmit={submitLogin}>
        <div className="login-brand">
          <span className="login-mark">A</span>
          <div>
            <p className="eyebrow">Abby</p>
            <h1>Sign in</h1>
          </div>
        </div>
        <Field label="Username" required>
          <input
            autoComplete="username"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
          />
        </Field>
        <Field label="Password" required>
          <input
            autoComplete="current-password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </Field>
        <Button disabled={!canSignIn} type="submit">
          <LockKeyhole aria-hidden="true" size={18} /> Sign in
        </Button>
      </form>
    </main>
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
      <div className="page-title home-hero">
        <p className="eyebrow">Today</p>
        <h1>Welcome to your safety plan!</h1>
      </div>
      <Section title="Quick actions">
        <div className="quick-actions">
          <button className="checkin-panel" onClick={() => navigate("check-in")} type="button">
            <div className="checkin-panel-icon">
              <CalendarCheck size={24} aria-hidden="true" />
            </div>
            <div className="checkin-panel-text">
              <span className="checkin-panel-label">Next check-in</span>
              <span className="checkin-panel-value">{nextCheckIn}</span>
            </div>
            <span className="checkin-panel-cta">Check in now</span>
          </button>
        </div>
      </Section>
      <div className="home-actions" aria-label="Safety plan setup">
        <ActionCard
          detail={`${recipients.length} people or services set up`}
          icon={<ContactRound aria-hidden="true" size={28} />}
          onClick={() => navigate("contacts")}
          title="Contacts"
        />
        <ActionCard
          detail="Review what helpers can see"
          icon={<ShieldCheck aria-hidden="true" size={28} />}
          onClick={() => navigate("contacts")}
          title="Sharing"
        />
      </div>
      <div className="home-footer">
        <div className="home-footer-stat">
          <small>Saved files</small>
          <span>{uploads.length} file{uploads.length !== 1 ? "s" : ""}</span>
        </div>
        <div className="home-footer-divider" />
        <div className="home-footer-stat">
          <small>Contact sharing</small>
          <span>Ready to review</span>
        </div>
      </div>
      <section className="support-card" aria-labelledby="support-card-title">
        <span className="support-card-badge" aria-hidden="true" />
        <div className="support-card-content">
          <h2 id="support-card-title">Need help today?</h2>
          <p>Find shelter, services, and support through your local 211 network.</p>
          <Button onClick={() => navigate("social-services")}>
            <HeartHandshake aria-hidden="true" size={18} /> Find help near you
          </Button>
        </div>
      </section>
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
  const [photoFileDetail, setPhotoFileDetail] = useState("");
  const [photoUploadError, setPhotoUploadError] = useState("");
  const [isShelterStaff, setIsShelterStaff] = useState(false);
  const [selectedShelter, setSelectedShelter] = useState("");
  const [shelterPin, setShelterPin] = useState("");
  const [currentStaffAccountId, setCurrentStaffAccountId] = useState("");

  const currentStaffAccount = shelterStaffAccounts.find((account) => account.id === currentStaffAccountId);
  const staffVerified = Boolean(currentStaffAccount?.verified);

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
      setPhotoUploadError("We can't use this file. Use JPG, PNG, WebP, or PDF.");
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
    <div className="screen">
      <div className="page-title">
        <p className="eyebrow">Registration</p>
        <h1>Create your Abby profile</h1>
      </div>
      <p className="page-note">To start, add your name, birth date, photo or ID.</p>
      <form className="form-grid" onSubmit={(event) => event.preventDefault()}>
        <Field help="This helps us know it is you in an emergency." label="Legal or full name" required>
          <input value={profile.legalName} onChange={(event) => update({ legalName: event.target.value })} />
        </Field>
        <Field help="Shown in the app when provided." label="Preferred name">
          <input value={profile.preferredName} onChange={(event) => update({ preferredName: event.target.value })} />
        </Field>
        <Field help="Optional. You can use any words you want." label="Pronouns">
          <input
            placeholder="call me she/her, he/him, they/them"
            value={profile.pronouns}
            onChange={(event) => update({ pronouns: event.target.value })}
          />
        </Field>
        <Field help="This helps tell people with the same name apart." label="Birth date" required>
          <input
            type="date"
            value={profile.dateOfBirth}
            onChange={(event) => update({ dateOfBirth: event.target.value })}
          />
        </Field>
        <Field
          error={photoUploadError}
          help="Use a JPG, PNG, WebP, or PDF file. We will not show a preview."
          label="Photo or photo ID"
          required
        >
          <input
            accept={ID_DOCUMENT_ACCEPT_ATTR}
            type="file"
            onChange={handleProfileUploadChange}
          />
          {photoFileDetail ? (
            <small className="registration-file-detail" aria-live="polite">
              Selected file: {photoFileDetail}
            </small>
          ) : null}
        </Field>
        <hr className="form-divider full-span" />
        <Field help="Used for text reminders." label="Phone">
          <input value={profile.phone} onChange={(event) => update({ phone: event.target.value })} />
        </Field>
        <Field help="Used for email reminders." label="Email">
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
  profile,
  setPolicy,
  nextCheckIn
}: {
  policy: typeof defaultCheckInPolicy;
  profile: RegistrationProfileDraft;
  setPolicy: (policy: typeof defaultCheckInPolicy) => void;
  nextCheckIn: string;
}) {
  const [checkInMessage, setCheckInMessage] = useState<{ tone: "success" | "warning"; text: string } | null>(null);
  const update = (patch: Partial<typeof defaultCheckInPolicy>) => setPolicy({ ...policy, ...patch });
  const channelLabels: Record<CheckInChannel, string> = {
    sms: "Texting allowed",
    email: "Email allowed",
    web: "Web allowed"
  };
  const checkInMethodLabels: Record<CheckInChannel, string> = {
    sms: "text",
    email: "email",
    web: "web"
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
            ? "Web check-in is off. Choose an allowed check-in method."
            : `${channel === "sms" ? "Texting" : "Email"} is off. Choose an allowed check-in method.`
      });
      return;
    }

    if (channel === "sms" && !profile.phone.trim()) {
      setCheckInMessage({
        tone: "warning",
        text: "Add a phone number to your account, or use another allowed check-in method."
      });
      return;
    }

    if (channel === "email" && !profile.email.trim()) {
      setCheckInMessage({
        tone: "warning",
        text: "Add an email to your account, or use another allowed check-in method."
      });
      return;
    }

    update({ lastCheckInAt: new Date().toISOString() });
    setCheckInMessage({
      tone: "success",
      text: `Checked in by ${channel === "sms" ? "text" : channel}.`
    });
  }

  return (
    <div className="screen">
      <div className="page-title">
        <p className="eyebrow">Check-in</p>
        <h1>Set your schedule</h1>
      </div>
      <StatusBanner tone="warning">You can wait up to 30 days between check-ins. After that, Abby starts the next help step.</StatusBanner>
      <Section title="Reminder schedule">
        <div className="form-grid">
          <Field help="Choose 1 to 30 days." label="Days between check-ins" required>
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
          <Field help="Extra time after a missed check-in before Abby starts the next help step." label="Extra hours after a missed check-in">
            <input
              min={0}
              type="number"
              value={policy.gracePeriodHours}
              onChange={(event) => update({ gracePeriodHours: Number(event.target.value || 0) })}
            />
          </Field>
        </div>
        <p className="supporting-copy">You can check in by text, email, or web when that method is allowed.</p>
        <div className="channel-controls" role="group" aria-label="Allowed check-in methods">
          {(["sms", "email", "web"] as CheckInChannel[]).map((channel) => (
            <button
              aria-pressed={policy.reminderChannels.includes(channel)}
              className="choice-chip channel-toggle"
              key={channel}
              onClick={() => toggleChannel(channel)}
              type="button"
            >
              <span>{channelLabels[channel]}</span>
              <small>{channelIsAllowed(channel) ? "On" : "Off"}</small>
            </button>
          ))}
        </div>
        {!policy.reminderChannels.length ? (
          <StatusBanner tone="warning">No check-in method is on. Turn on text, email, or web to check in.</StatusBanner>
        ) : null}
        <div className="schedule-preview">
          <CalendarCheck aria-hidden="true" size={28} />
          <div>
            <small>Next check-in</small>
            <strong>{nextCheckIn}</strong>
          </div>
        </div>
        {checkInMessage ? <StatusBanner tone={checkInMessage.tone}>{checkInMessage.text}</StatusBanner> : null}
        <div className="method-checkin-grid" role="group" aria-label="Check in now">
          {(["sms", "email", "web"] as CheckInChannel[]).map((channel) => {
            const allowed = channelIsAllowed(channel);
            return (
              <Button key={channel} onClick={() => checkInBy(channel)} variant={allowed ? "primary" : "secondary"}>
                <Bell size={18} /> Check in by {checkInMethodLabels[channel]}{allowed ? "" : " (off)"}
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
  help
}: {
  label: string;
  scopes: DisclosureDataScope[];
  onToggle: (scope: DisclosureDataScope) => void;
  help?: string;
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
              <strong>{scope.label}</strong>
              <small>{scope.detail}</small>
            </span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}

function getDisclosureScopeLabels(scopes: DisclosureDataScope[]): string {
  return scopes.map((scope) => disclosureScopes.find((item) => item.id === scope)?.label ?? scope).join(", ");
}

function SharingCapabilityPreview({ recipientName, scopes }: { recipientName: string; scopes: DisclosureDataScope[] }) {
  const abilities = abilitiesForDisclosureScopes(scopes);

  return (
    <div className="capability-preview" role="group" aria-label={`${recipientName} sharing capability preview`}>
      <div className="scope-header">
        <div>
          <h4>What this allows</h4>
          <p>{scopes.length} selected items</p>
        </div>
        <Badge tone={scopes.length > 0 ? "success" : "warning"}>{scopes.length > 0 ? "limited share" : "no access"}</Badge>
      </div>
      <div className="disclosure-package">
        <div className="disclosure-row">
          <strong>Can do</strong>
          <span>{plainCapabilitySummary(abilities) || "No access selected"}</span>
        </div>
        <div className="disclosure-row">
          <strong>Items</strong>
          <span>{getDisclosureScopeLabels(scopes) || "No items selected"}</span>
        </div>
        <div className="disclosure-row">
          <strong>Not allowed</strong>
          <span>{plainNonGrantedCapabilities(abilities).join(", ")}</span>
        </div>
      </div>
    </div>
  );
}

function ContactsScreen({
  contactRequests,
  profile,
  recipients,
  setContactRequests,
  setRecipients
}: {
  contactRequests: ShelterContactRequest[];
  profile: RegistrationProfileDraft;
  recipients: DisclosureRecipientDraft[];
  setContactRequests: (requests: ShelterContactRequest[]) => void;
  setRecipients: (recipients: DisclosureRecipientDraft[]) => void;
}) {
  const [draft, setDraft] = useState({
    displayName: "",
    relationship: "",
    email: "",
    phone: "",
    type: "emergency_contact" as DisclosureRecipientType
  });
  const [draftScopes, setDraftScopes] = useState<DisclosureDataScope[]>([...defaultDisclosureScopes]);
  const [editingRecipientId, setEditingRecipientId] = useState<string | null>(null);
  const [editingScopes, setEditingScopes] = useState<DisclosureDataScope[]>([]);
  const [requestedShelter, setRequestedShelter] = useState(shelterOptions[0]);

  const userName = profile.preferredName || profile.legalName || "Abby Example";
  const userContact = profile.email || profile.phone || "abby@example.org";
  const userContactKey = userContact.trim().toLowerCase();
  const requestBelongsToCurrentUser = (request: ShelterContactRequest) =>
    request.userName.trim().toLowerCase() === userName.trim().toLowerCase() ||
    request.userContact.trim().toLowerCase() === userContactKey;
  const userShelterRequests = contactRequests.filter(requestBelongsToCurrentUser);
  const incomingShelterNudges = contactRequests.filter(
    (request) =>
      request.direction === "shelter_to_user" && request.status === "pending" && requestBelongsToCurrentUser(request)
  );
  const hasPendingRequestedShelter = contactRequests.some(
    (request) =>
      request.status === "pending" &&
      request.shelterName === requestedShelter &&
      requestBelongsToCurrentUser(request)
  );
  const editingRecipient = recipients.find((recipient) => recipient.id === editingRecipientId);

  function addShelterRecipient(shelterName: string) {
    if (recipients.some((recipient) => recipient.type === "shelter_staff" && recipient.agencyName === shelterName)) {
      return;
    }

    setRecipients([
      ...recipients,
      {
        id: `rec-${Date.now()}`,
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
    if (!draft.displayName) return;
    setRecipients([
      ...recipients,
      {
        id: `rec-${Date.now()}`,
        ...draft,
        agencyName: "",
        precinctName: "",
        verified: false,
        allowedScopes: [...draftScopes]
      }
    ]);
    setDraft({ displayName: "", relationship: "", email: "", phone: "", type: "emergency_contact" });
    setDraftScopes([...defaultDisclosureScopes]);
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
        <p className="eyebrow">Emergency contacts</p>
        <h1>People who can help</h1>
      </div>
      <p className="page-note">
        Sharing choices live with each saved contact. Open a contact below to change what they can see.
      </p>
      <Section title="Add shelter or group">
        <p className="section-note">
          A shelter is added only after the other side says yes. It starts with Minimum identity only.
        </p>
        <form className="form-grid" onSubmit={requestShelterContact}>
          <Field label="Shelter">
            <select value={requestedShelter} onChange={(event) => setRequestedShelter(event.target.value)}>
              {shelterOptions.map((shelter) => (
                <option key={shelter} value={shelter}>
                  {shelter}
                </option>
              ))}
            </select>
          </Field>
          <div className="full-span centered-action">
            <Button disabled={hasPendingRequestedShelter} type="submit" variant="secondary">
              <MessageSquare aria-hidden="true" size={18} /> Ask to add shelter
            </Button>
          </div>
          {hasPendingRequestedShelter ? (
            <small className="full-span pin-request-note">
              A request is already waiting for this shelter and person.
            </small>
          ) : null}
        </form>
        <div className="list-stack">
          {incomingShelterNudges.map((request) => (
            <article className="list-item access-request-item" key={request.id}>
              <div>
                <h3>{request.shelterName}</h3>
                <p>{request.staffName || "Shelter staff"} asked to be added to your contacts.</p>
                <Badge>{request.status}</Badge>
              </div>
              <div className="row-actions">
                <Button onClick={() => decideShelterNudge(request.id, "approved")} variant="secondary">
                  Approve
                </Button>
                <Button onClick={() => decideShelterNudge(request.id, "denied")} variant="danger">
                  Deny
                </Button>
              </div>
            </article>
          ))}
          {userShelterRequests.map((request) => (
            <article className="list-item" key={`status-${request.id}`}>
              <div>
                <h3>{request.shelterName}</h3>
                <p>{request.direction === "user_to_shelter" ? "You asked this shelter." : "Shelter asked you."}</p>
              </div>
              <div className="row-actions">
                <Badge tone={request.status === "approved" ? "success" : request.status === "denied" ? "warning" : "neutral"}>
                  {request.status}
                </Badge>
                {request.direction === "user_to_shelter" && request.status === "pending" ? (
                  <Button onClick={() => cancelShelterRequest(request.id)} variant="secondary">
                    Cancel
                  </Button>
                ) : null}
              </div>
            </article>
          ))}
        </div>
      </Section>
      <Section title="Add person">
        <form className="form-grid" onSubmit={addRecipient}>
          <Field label="Name or group" required>
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
              <option value="government_liaison">Government help</option>
              <option value="benefits_agency">Benefits agency</option>
            </select>
          </Field>
          <SharingScopeChecklist
            help="These start on. Turn off anything this person should not see."
            label="Sharing choices for this person"
            onToggle={(scope) => setDraftScopes(toggleScopeSelection(draftScopes, scope))}
            scopes={draftScopes}
          />
          <div className="full-span centered-action">
            <Button type="submit">
              <UsersRound aria-hidden="true" size={18} /> Add person
            </Button>
          </div>
        </form>
      </Section>
      <Section title="Saved contacts">
        {recipients.length === 0 ? (
          <p className="empty-state">No saved contacts yet. Add a shelter, group, or person above.</p>
        ) : (
          <div className="list-stack">
            {recipients.map((recipient) => {
              const isEditing = editingRecipient?.id === recipient.id;

              return (
                <article className="list-item recipient-list-item" key={recipient.id}>
                  <div className="recipient-row">
                    <button
                      aria-controls={`recipient-edit-${recipient.id}`}
                      aria-expanded={isEditing}
                      aria-label={`Edit sharing for ${recipient.displayName}`}
                      className="recipient-open-button"
                      id={`recipient-open-${recipient.id}`}
                      onClick={() => openRecipientEditor(recipient)}
                      type="button"
                    >
                      <span className="recipient-summary">
                        <span className="recipient-name">{recipient.displayName}</span>
                        <span className="recipient-details">
                          <span>{recipient.relationship || recipient.agencyName || formatRecipientType(recipient.type)}</span>
                          {recipient.email ? <span>{recipient.email}</span> : null}
                          {recipient.phone ? <span>{recipient.phone}</span> : null}
                        </span>
                        <span className="badge-row" aria-label={`${recipient.displayName} status`}>
                          <Badge tone={recipient.verified ? "success" : "warning"}>
                            {recipient.verified ? "Verified" : "Needs a check"}
                          </Badge>
                          <Badge>{recipient.allowedScopes.length} items</Badge>
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
                        Edit sharing
                      </Button>
                      <Button
                        ariaLabel={`Remove ${recipient.displayName}`}
                        className="compact-list-action"
                        onClick={() => removeRecipient(recipient.id)}
                        variant="quiet"
                      >
                        Remove
                      </Button>
                    </div>
                  </div>
                  {isEditing ? (
                    <div
                      aria-labelledby={`recipient-edit-heading-${recipient.id}`}
                      className="recipient-edit-panel"
                      id={`recipient-edit-${recipient.id}`}
                      role="region"
                      tabIndex={-1}
                    >
                      <div className="scope-header">
                        <div>
                          <h3 id={`recipient-edit-heading-${recipient.id}`}>Edit sharing for {recipient.displayName}</h3>
                          <p>Save only what this contact should see.</p>
                        </div>
                        <Badge>{editingScopes.length} selected</Badge>
                      </div>
                      <SharingScopeChecklist
                        label={`Sharing choices for ${recipient.displayName}`}
                        onToggle={(scope) => setEditingScopes(toggleScopeSelection(editingScopes, scope))}
                        scopes={editingScopes}
                      />
                      <SharingCapabilityPreview recipientName={recipient.displayName} scopes={editingScopes} />
                      <div className="row-actions">
                        <Button onClick={() => saveRecipientScopes(recipient.id)}>Save sharing</Button>
                        <Button onClick={() => closeRecipientEditor(recipient.id)} variant="secondary">
                          Cancel
                        </Button>
                      </div>
                    </div>
                  ) : null}
                </article>
              );
            })}
          </div>
        )}
      </Section>
    </div>
  );
}

function UploadsScreen({
  apiConfig,
  refreshWalletAuditEvents,
  uploads,
  setUploads
}: {
  apiConfig?: WalletApiConfig;
  refreshWalletAuditEvents: () => Promise<void>;
  uploads: UploadItem[];
  setUploads: (uploads: UploadItem[]) => void;
}) {
  const [repairingUploadIds, setRepairingUploadIds] = useState<string[]>([]);

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

<<<<<<< HEAD
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

  async function storeFileUploadOnWalrus(upload: UploadItem, file: File) {
    if (!walrusStorageConfig) {
      updateUpload(upload.id, {
        decentralizedStorageMessage: t(siteLocale, "wallet.walrusConnectBeforeUpload"),
        decentralizedStorageStatus: "not_configured"
      });
      return;
    }
    setWalrusUploadIds((uploadIds) => [...uploadIds, upload.id]);
    updateUpload(upload.id, {
      decentralizedStorageMessage: t(siteLocale, "wallet.walrusUploading"),
      decentralizedStorageStatus: "uploading"
    });
    try {
      const result = await uploadFileToWalrusStorage(file, {
        allowedRecipientIds: upload.allowedRecipientIds ?? [],
        clientConfig: walrusStorageConfig,
        upload,
        walletConfig: apiConfig
      });
      const patch = toWalrusStoragePatch(result, walrusStorageConfig);
      updateUpload(upload.id, patch);
      void persistUploadMetadata(upload, patch);
    } catch (error) {
      updateUpload(upload.id, {
        decentralizedStorageMessage: error instanceof Error ? error.message : t(siteLocale, "wallet.walrusUploadFailed"),
        decentralizedStorageStatus: "failed"
      });
    } finally {
      setWalrusUploadIds((uploadIds) => uploadIds.filter((id) => id !== upload.id));
    }
  }

  async function storeWalletRecordOnWalrus(upload: UploadItem) {
    if (!walrusStorageConfig) return;
    setWalrusUploadIds((uploadIds) => [...uploadIds, upload.id]);
    updateUpload(upload.id, {
      decentralizedStorageMessage: t(siteLocale, "wallet.walrusSendRecord"),
      decentralizedStorageStatus: "uploading"
    });
    try {
      const result = await uploadWalletRecordToWalrusStorage(upload, {
        clientConfig: walrusStorageConfig,
        walletConfig: apiConfig
      });
      const patch = toWalrusStoragePatch(result, walrusStorageConfig);
      const nextUpload = { ...upload, ...patch };
      updateUpload(upload.id, patch);
      void persistUploadMetadata(upload, patch);
      if (!nextUpload.privacyProfileStatus || nextUpload.privacyProfileNeedsRefresh) {
        void profileWalletUpload(nextUpload);
      }
    } catch (error) {
      updateUpload(upload.id, {
        decentralizedStorageMessage: error instanceof Error ? error.message : t(siteLocale, "wallet.walrusUploadFailed"),
        decentralizedStorageStatus: "failed"
      });
    } finally {
      setWalrusUploadIds((uploadIds) => uploadIds.filter((id) => id !== upload.id));
    }
  }

  async function storeUploadOnWalrus(upload: UploadItem) {
    if (upload.recordId) {
      await storeWalletRecordOnWalrus(upload);
      return;
    }
    const originalFile = originalUploadFilesRef.current.get(upload.id);
    if (originalFile) {
      await storeFileUploadOnWalrus(upload, originalFile);
    }
  }

  async function deleteWalrusBlobForUpload(upload: UploadItem): Promise<Partial<UploadItem> | undefined> {
    if (!upload.walrusBlobId) return;
    if (!walrusDeleteReady) {
      throw new Error(t(siteLocale, "wallet.walrusDeleteBackendRequired"));
    }
    setWalrusDeleteIds((uploadIds) => [...new Set([...uploadIds, upload.id])]);
    updateUpload(upload.id, {
      decentralizedStorageMessage: t(siteLocale, "wallet.walrusDeleting"),
      decentralizedStorageStatus: "uploading"
    });
    try {
      await deleteWalrusBlobFromStorage(upload, {
        clientConfig: walrusStorageConfig,
        walletConfig: apiConfig
      });
      return {
        decentralizedStorageMessage: t(siteLocale, "wallet.walrusDeleted"),
        decentralizedStorageProvider: upload.ipfsCid ? "ipfs-filecoin" : upload.recordId ? "wallet-api" : "local",
        decentralizedStorageStatus: upload.ipfsCid ? "stored" : "ready",
        walrusBlobId: undefined,
        walrusEndEpoch: undefined,
        walrusGatewayUrl: undefined,
        walrusObjectId: undefined,
        walrusStorageCost: undefined,
        walrusTxDigest: undefined
      };
    } finally {
      setWalrusDeleteIds((uploadIds) => uploadIds.filter((id) => id !== upload.id));
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
    const originalFile = originalUploadFilesRef.current.get(upload.id);
    if (originalFile) {
      downloadBlob(originalFile, upload.fileName || originalFile.name || "wallet-file");
      return;
    }
    setDownloadingUploadIds((uploadIds) => [...uploadIds, upload.id]);
    try {
      if (!apiConfig?.actorDid || !upload.recordId) {
        await downloadStoredUploadBlob(upload);
        return;
      }
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
      downloadBlob(new Blob([payload], { type: decryptedMimeType }), upload.fileName || `${upload.recordId}.bin`);
    } catch (error) {
      updateUpload(upload.id, {
        decentralizedStorageMessage:
          error instanceof Error
            ? tFormat(siteLocale, "wallet.downloadFailedDetail", { error: error.message })
            : t(siteLocale, "wallet.downloadFailed")
      });
    } finally {
      setDownloadingUploadIds((uploadIds) => uploadIds.filter((id) => id !== upload.id));
    }
  }

  async function downloadStoredUploadBlob(upload: UploadItem) {
    const href = walrusGatewayHref(upload) || (upload.ipfsCid ? ipfsGatewayHref(upload) : undefined);
    if (!href || href === "#") throw new Error("No downloadable wallet file source is available.");
    const response = await fetch(href);
    if (!response.ok) throw new Error(`Storage download failed with ${response.status}.`);
    downloadBlob(await response.blob(), upload.fileName || `${upload.walrusBlobId || upload.ipfsCid || upload.id}.bin`);
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
      walrusBlobId: upload.walrusBlobId,
      walrusEndEpoch: upload.walrusEndEpoch,
      walrusGatewayUrl: upload.walrusGatewayUrl,
      walrusObjectId: upload.walrusObjectId,
      walrusStorageCost: upload.walrusStorageCost,
      walrusTxDigest: upload.walrusTxDigest,
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
      decentralizedStorageStatus:
        upload.decentralizedStorageStatus ?? (filecoinStorageReady || walrusStorageReady ? "ready" : "not_configured"),
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

  async function deleteOrRemoveUpload(upload: UploadItem) {
    const confirmed = window.confirm(
      tFormat(siteLocale, upload.recordId && apiConfig?.actorDid ? "wallet.deleteConfirm" : "wallet.removeLocalConfirm", {
        name: upload.fileName
      })
    );
    if (!confirmed) return;
    setDeletingUploadIds((uploadIds) => [...new Set([...uploadIds, upload.id])]);
    try {
      let walrusPatch: Partial<UploadItem> = {};
      if (upload.walrusBlobId) {
        try {
          walrusPatch = await deleteWalrusBlobForUpload(upload) ?? {};
        } catch (error) {
          walrusPatch = {
            decentralizedStorageMessage:
              error instanceof Error
                ? tFormat(siteLocale, "wallet.walrusDeleteFailedDetail", { error: error.message })
                : t(siteLocale, "wallet.walrusDeleteFailed"),
            decentralizedStorageStatus: "failed"
          };
        }
      }
      if (apiConfig?.actorDid && upload.recordId) {
        await deleteWalletRecord(apiConfig, upload.recordId, { unpinIpfs: true });
      }
      originalUploadFilesRef.current.delete(upload.id);
      replaceUploads(uploadsRef.current.filter((item) => item.id !== upload.id));
      if (upload.recordId && Object.keys(walrusPatch).length) {
        void persistUploadMetadata(upload, walrusPatch);
      }
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

  function storageDetailsExpanded(uploadId: string): boolean {
    return expandedStorageDetailIds.includes(uploadId);
  }

  function toggleStorageDetails(uploadId: string) {
    setExpandedStorageDetailIds((ids) =>
      ids.includes(uploadId) ? ids.filter((id) => id !== uploadId) : [...ids, uploadId]
    );
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

=======
>>>>>>> a90409846cc36413f571329274065072a8136277
  return (
    <div className="screen">
      <div className="page-title">
        <p className="eyebrow">Uploads</p>
        <h1>Saved files and info</h1>
      </div>
      <Section title="Add information">
        <label className="upload-dropzone">
          <Upload aria-hidden="true" size={28} />
          <span>Choose a file or photo</span>
          <small>Files stay private until you choose to share them.</small>
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
        {uploads.map((upload) => (
          <article className="list-item upload-list-item" key={upload.id}>
            <div>
              <h3>{upload.fileName}</h3>
              <p>{upload.category}</p>
              <small className="upload-machine-summary">{toShortSummaryTitle(upload.machineSummary)}</small>
              <div className="badge-row">
                <Badge tone="success">{upload.status}</Badge>
                {upload.storageOk !== undefined ? (
                  <Badge tone={upload.storageOk ? "success" : "warning"}>
                    {upload.storageOk ? "saved" : "save needs fix"}
                  </Badge>
                ) : null}
                <Badge>{upload.shared ? "Shared" : "Private"}</Badge>
              </div>
            </div>
            <div className="row-actions list-item-action">
              {upload.storageOk === false && upload.recordId && apiConfig?.actorDid ? (
                <Button
                  disabled={repairingUploadIds.includes(upload.id)}
                  onClick={() => repairUploadStorage(upload)}
                  variant="secondary"
                >
                  <Wrench aria-hidden="true" size={18} />
<<<<<<< HEAD
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
              {walrusStorageReady && canStoreUploadOnWalrus(upload, originalUploadFilesRef.current.has(upload.id)) ? (
                <Button
                  disabled={walrusUploadIds.includes(upload.id)}
                  onClick={() => void storeUploadOnWalrus(upload)}
                  variant="secondary"
                >
                  <Upload aria-hidden="true" size={18} />
                  {walrusActionLabel(walrusUploadIds.includes(upload.id), siteLocale)}
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
=======
                  {repairingUploadIds.includes(upload.id) ? "Fixing" : "Fix save"}
>>>>>>> a90409846cc36413f571329274065072a8136277
                </Button>
              ) : null}
              <Button
                onClick={() =>
                  setUploads(uploads.map((item) => (item.id === upload.id ? { ...item, shared: !item.shared } : item)))
                }
                variant="secondary"
              >
                {upload.shared ? "Make private" : "Allow sharing"}
              </Button>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

<<<<<<< HEAD
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
  if (upload.walrusBlobId && !upload.ipfsCid) return t(locale, "wallet.walrus");
  if (upload.filecoinPinStatus === "queued") return t(locale, "wallet.filecoinQueued");
  if (upload.filecoinPinStatus === "pinning") return t(locale, "wallet.filecoinPinning");
  if (upload.filecoinPinStatus === "failed") return t(locale, "wallet.ipfsOnly");
  if (upload.decentralizedStorageProvider === "walrus") return t(locale, "wallet.walrus");
  if (upload.decentralizedStorageStatus === "stored") return t(locale, "wallet.ipfsFilecoin");
  if (upload.decentralizedStorageStatus === "uploading") return t(locale, "wallet.storing");
  if (upload.decentralizedStorageStatus === "failed") return t(locale, "wallet.storageFailed");
  return t(locale, "wallet.walletStorage");
}

function isWalrusBackedUpload(upload: UploadItem): boolean {
  return Boolean(upload.walrusBlobId || upload.decentralizedStorageProvider === "walrus");
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
  return !upload.ipfsCid || upload.filecoinPinStatus === "failed";
}

function filecoinActionLabel(upload: UploadItem, inProgress: boolean, locale: SupportedLocale): string {
  if (upload.filecoinPinStatus === "failed") {
    return inProgress ? t(locale, "wallet.retrying") : t(locale, "wallet.retryFilecoin");
  }
  return inProgress ? t(locale, "wallet.storing") : t(locale, "wallet.storeOnFilecoin");
}

function shouldShowWalrusAction(upload: UploadItem): boolean {
  return !upload.walrusBlobId;
}

function canStoreUploadOnWalrus(upload: UploadItem, hasOriginalFile: boolean): boolean {
  return shouldShowWalrusAction(upload) && (Boolean(upload.recordId) || hasOriginalFile);
}

function walrusActionLabel(inProgress: boolean, locale: SupportedLocale): string {
  return inProgress ? t(locale, "wallet.storing") : t(locale, "wallet.storeOnWalrus");
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

function walrusGatewayHref(upload: UploadItem): string | undefined {
  return upload.walrusGatewayUrl || buildWalrusBlobUrl(upload.walrusBlobId, getWalrusStorageConfig()?.aggregatorUrl);
}

function canDownloadUpload(upload: UploadItem, hasOriginalFile: boolean, apiConfig: WalletApiConfig | undefined): boolean {
  return hasOriginalFile || Boolean(upload.recordId && apiConfig?.actorDid) || Boolean(walrusGatewayHref(upload) || upload.ipfsCid);
}

function downloadBlob(blob: Blob, fileName: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = fileName || "wallet-file";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
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
=======
function SocialServicesScreen() {
  const categories = ["Shelter", "Food", "Health", "Legal", "Benefits", "Transportation", "Employment", "Crisis"];
  const suggestedPrompts = ["food pantry near Portland", "emergency shelter", "utility bill help"];
>>>>>>> a90409846cc36413f571329274065072a8136277
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [searchStatus, setSearchStatus] = useState<"idle" | "loading" | "complete" | "error">("idle");
  const [searchError, setSearchError] = useState("");

  async function runSearch(nextQuery = query) {
    const trimmedQuery = nextQuery.trim();
    if (!trimmedQuery) return;

    setQuery(trimmedQuery);
    setSearchStatus("loading");
    setSearchError("");
    try {
      const searchResults = await search211Info(trimmedQuery, 18);
      const serviceResults = searchResults.filter((result) => result.document.doc_type === "service");
      setResults((serviceResults.length ? serviceResults : searchResults).slice(0, 8));
      setSearchStatus("complete");
    } catch (error) {
      setResults([]);
      setSearchStatus("error");
      setSearchError(error instanceof Error ? error.message : "Search failed");
    }
  }

  function handleSearchSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void runSearch();
  }

  return (
    <div className="screen">
      <div className="page-title">
        <p className="eyebrow">Social services</p>
        <h1>Find support</h1>
      </div>
      <Section title="Search 211 services">
        <form className="form-grid" onSubmit={handleSearchSubmit}>
          <Field label="Search by need, provider, or place">
            <input
              placeholder="food pantry near Beaverton"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
          </Field>
          <div className="row-actions">
            <Button disabled={!query.trim()} loading={searchStatus === "loading"} loadingLabel="Searching" type="submit">
              Search
            </Button>
          </div>
        </form>
        <div className="chip-grid" aria-label="Suggested searches">
          {suggestedPrompts.map((prompt) => (
            <button className="choice-chip" key={prompt} onClick={() => void runSearch(prompt)} type="button">
              {prompt}
            </button>
          ))}
        </div>
        {searchStatus === "error" ? (
          <StatusBanner tone="warning">211 service search is unavailable: {searchError}</StatusBanner>
        ) : null}
        {searchStatus === "complete" && results.length === 0 ? (
          <StatusBanner tone="info">No local 211 records matched. Try a broader need or contact 211 directly.</StatusBanner>
        ) : null}
        {results.length ? (
          <div className="list-stack" aria-label="211 service search results">
            {results.map((result) => {
              const document = result.document;
              const provider = document.provider_name || "Provider not listed";
              const program = document.program_name || document.title || "Program not listed";
              return (
                <article className="list-item" key={result.docId}>
                  <div>
                    <h3>{program}</h3>
                    <p>{provider}</p>
                    <small className="upload-machine-summary">{result.snippet}</small>
                    <div className="badge-row">
                      <Badge>{document.doc_type}</Badge>
                      {document.city || document.state ? (
                        <Badge>
                          {[document.city, document.state].filter(Boolean).join(", ")}
                        </Badge>
                      ) : null}
                    </div>
                  </div>
                  <div className="row-actions list-item-action">
                    {document.source_url ? <Badge tone="success">source</Badge> : null}
                    <Button onClick={() => setLocationServiceDetailHash(result.docId)} variant="secondary">
                      Open detail
                    </Button>
                  </div>
                </article>
              );
            })}
          </div>
        ) : null}
      </Section>
      <div className="category-grid">
        {categories.map((category) => (
          <button className="category-tile" key={category} onClick={() => void runSearch(category)} type="button">
            <HeartHandshake aria-hidden="true" size={22} />
            <span>{category}</span>
          </button>
        ))}
      </div>
      <Section title="Government help">
        <div className="liaison-panel">
          <MessageSquare aria-hidden="true" size={28} />
          <div>
            <h3>Get help with benefits, ID, housing, or forms.</h3>
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
  contactRequests,
  recipients,
  setContactRequests,
  setRecipients,
  shelterStaffAccounts,
  setShelterStaffAccounts,
  shelterUserAccounts,
  setShelterUserAccounts
}: {
  checklist: typeof defaultShelterChecklist;
  setChecklist: (value: typeof defaultShelterChecklist) => void;
  contactRequests: ShelterContactRequest[];
  recipients: DisclosureRecipientDraft[];
  setContactRequests: (requests: ShelterContactRequest[]) => void;
  setRecipients: (recipients: DisclosureRecipientDraft[]) => void;
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
  const [nudgeDraft, setNudgeDraft] = useState({ userName: "Abby Example", userContact: "abby@example.org" });
  const [managedUserFileDetail, setManagedUserFileDetail] = useState("");
  const [managedUserUploadError, setManagedUserUploadError] = useState("");

  const staffForShelter = shelterStaffAccounts.filter((account) => account.shelter === adminShelter);
  const verifiedStaffForOperatorShelter = shelterStaffAccounts.filter(
    (account) => account.shelter === operatorShelter && account.verified
  );
  const selectedOperator = shelterStaffAccounts.find((account) => account.id === operatorStaffId && account.verified);
  const usersForOperatorShelter = shelterUserAccounts.filter((account) => account.shelter === operatorShelter);
  const requestsForOperatorShelter = contactRequests.filter((request) => request.shelterName === operatorShelter);
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
      setManagedUserUploadError("We can't use this file. Use JPG, PNG, WebP, or PDF.");
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
    setUserDraft(defaultManagedUserDraft);
    setManagedUserFileDetail("");
    setManagedUserUploadError("");
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

  function shelterRecipientExists(shelterName: string) {
    return recipients.some((recipient) => recipient.type === "shelter_staff" && recipient.agencyName === shelterName);
  }

  function addShelterRecipient(shelterName: string) {
    if (shelterRecipientExists(shelterName)) return;

    setRecipients([
      ...recipients,
      {
        id: `rec-${Date.now()}`,
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

  return (
    <div className="screen">
      <div className="page-title">
        <p className="eyebrow">Shelter portal</p>
        <h1>Assisted access</h1>
      </div>
      <p className="page-note">Shelter workflows are free and keep user sharing choices separate from staff access.</p>
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
                      placeholder="call me she/her, he/him, they/them"
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
                  <Field
                    error={managedUserUploadError}
                    help="Use a JPG, PNG, WebP, or PDF file. We will not show a preview."
                    label="Photo or photo ID"
                    required
                  >
                    <input
                      accept={ID_DOCUMENT_ACCEPT_ATTR}
                      type="file"
                      onChange={handleManagedUserUploadChange}
                    />
                    {managedUserFileDetail ? (
                      <small className="registration-file-detail" aria-live="polite">
                        Selected file: {managedUserFileDetail}
                      </small>
                    ) : null}
                  </Field>
                  <Field help="Used for text reminders." label="Phone">
                    <input
                      value={userDraft.phone}
                      onChange={(event) => setUserDraft({ ...userDraft, phone: event.target.value })}
                    />
                  </Field>
                  <Field help="Used for email reminders." label="Email">
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

              <Section title="Contact list requests">
                <p className="section-note">
                  Send a request only. The person must approve before this shelter is added.
                </p>
                <form className="form-grid" onSubmit={sendShelterNudge}>
                  <Field label="Person name" required>
                    <input
                      value={nudgeDraft.userName}
                      onChange={(event) => setNudgeDraft({ ...nudgeDraft, userName: event.target.value })}
                    />
                  </Field>
                  <Field label="Phone or email" required>
                    <input
                      value={nudgeDraft.userContact}
                      onChange={(event) => setNudgeDraft({ ...nudgeDraft, userContact: event.target.value })}
                    />
                  </Field>
                  <div className="full-span centered-action">
                    <Button disabled={hasPendingShelterNudge()} type="submit" variant="secondary">
                      <MessageSquare size={18} /> Send contact request
                    </Button>
                  </div>
                  {hasPendingShelterNudge() ? (
                    <small className="full-span pin-request-note">
                      A request is already waiting for this shelter and person.
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
                              ? `User asked to add ${request.shelterName}.`
                              : `${request.shelterName} asked this user.`}
                          </p>
                          <div className="badge-row">
                            <Badge>{request.userContact}</Badge>
                            <Badge tone={request.status === "approved" ? "success" : request.status === "denied" ? "warning" : "neutral"}>
                              {request.status}
                            </Badge>
                          </div>
                        </div>
                        {request.direction === "user_to_shelter" && request.status === "pending" ? (
                          <div className="row-actions">
                            <Button onClick={() => decideUserShelterRequest(request.id, "approved")} variant="secondary">
                              Approve
                            </Button>
                            <Button onClick={() => decideUserShelterRequest(request.id, "denied")} variant="danger">
                              Deny
                            </Button>
                          </div>
                        ) : null}
                      </article>
                    ))
                  ) : (
                    <small>No contact list requests for this shelter yet.</small>
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

function AnalyticsScreen({
  optedIn,
  setOptedIn
}: {
  optedIn: Record<string, boolean>;
  setOptedIn: (value: Record<string, boolean>) => void;
}) {
  function toggleStudy(studyId: string) {
    setOptedIn({ ...optedIn, [studyId]: !isStudySelected(studyId) });
  }

  function isStudySelected(studyId: string) {
    return optedIn[studyId] ?? true;
  }

  return (
    <div className="screen">
      <div className="page-title">
        <p className="eyebrow">Group facts choice</p>
        <h1>Share group facts, not your name</h1>
      </div>
      <p className="page-note">
        These choices start on. You can turn off any one. We use group facts, not names or contact details.
      </p>
      <StatusBanner tone="warning">
        A privacy and legal team must review this before real use.
      </StatusBanner>
      <div className="analytics-grid">
        {analyticsStudies.map((study) => {
          const selected = isStudySelected(study.id);
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
                  {study.status === "paused" ? "paused" : selected ? "on" : "off"}
                </Badge>
              </div>
              <div className="privacy-metrics">
                <StatusPanel label="Group size" value={String(study.minCohortSize)} tone="teal" />
                <StatusPanel label="Privacy left" value={budgetRemaining.toFixed(2)} tone="gold" />
              </div>
              <div className="badge-row">
                {study.fields.map((field) => (
                  <Badge key={field}>{formatAnalyticsField(field)}</Badge>
                ))}
              </div>
              <div
                className="capability-preview"
                role="group"
                aria-label={`${study.title} analytics capability preview`}
              >
                <div className="scope-header">
                  <div>
                    <h4>What this allows</h4>
                    <p>{study.fields.length} safe details · group size {study.minCohortSize}</p>
                  </div>
                  <Badge tone={study.status === "paused" ? "warning" : "success"}>
                    {study.status === "paused" ? "paused" : "limited group share"}
                  </Badge>
                </div>
                <div className="disclosure-package">
                  <div className="disclosure-row">
                    <strong>Can do</strong>
                    <span>{plainCapabilitySummary(["analytics/contribute"])}</span>
                  </div>
                  <div className="disclosure-row">
                    <strong>Safe details</strong>
                    <span>{study.fields.map(formatAnalyticsField).join(", ")}</span>
                  </div>
                  <div className="disclosure-row">
                    <strong>Not allowed</strong>
                    <span>{plainNonGrantedCapabilities(["analytics/contribute"]).join(", ")}</span>
                  </div>
                </div>
              </div>
              <label className="consent-box">
                <input
                  checked={selected}
                  onChange={() => toggleStudy(study.id)}
                  type="checkbox"
                />
                <span>
                  <strong>Allow this choice to use the group facts listed above.</strong>
                  <small>Exact location, files, names, and contact details are not used.</small>
                </span>
              </label>
            </article>
          );
        })}
      </div>
    </div>
  );
}

function ProofCenterScreen({
  apiConfig,
  proofs,
  refreshWalletAuditEvents,
  refreshWalletProofReceipts,
  setProofs
}: {
  apiConfig?: WalletApiConfig;
  proofs: ProofReceiptView[];
  refreshWalletAuditEvents: () => Promise<void>;
  refreshWalletProofReceipts: () => Promise<void>;
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
      <p className="page-note">
        Proof receipts expose public claims and verifier details without showing raw documents or precise location.
      </p>
      <WorldIdVerificationPanel
        apiConfig={apiConfig}
        onAuditRefresh={refreshWalletAuditEvents}
        onProofsRefresh={refreshWalletProofReceipts}
      />
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
                <strong>Not allowed</strong>
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
                    <h4>What this allows</h4>
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
                    <strong>Not allowed</strong>
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
      <p className="page-note">
        Export bundles carry encrypted records, receipt hashes, and storage reports. Importing a bundle does not reveal plaintext.
      </p>
      {!apiConfig ? (
        <StatusBanner tone="warning">Connect Abby before you make live export bundles.</StatusBanner>
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
                <h3>What this allows</h3>
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
                <strong>Not allowed</strong>
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
                <Badge tone={bundle.verificationOk && bundle.storageOk ? "success" : "warning"}>
                  {!bundle.verificationOk ? "receipt invalid" : bundle.storageOk ? "storage verified" : "storage missing"}
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
                <Badge tone={bundle.hashOk ? "success" : "warning"}>
                  {bundle.hashOk ? "hash verified" : "hash mismatch"}
                </Badge>
                <Badge tone={bundle.schemaOk ? "success" : "warning"}>
                  {bundle.schemaOk ? "schema verified" : "schema failed"}
                </Badge>
                <Badge>{bundle.createdAt}</Badge>
                <Badge tone={bundle.imported ? "success" : "neutral"}>
                  {bundle.imported ? "import verified" : "not imported"}
                </Badge>
              </div>
              {bundle.schemaError ? <p className="receipt-error">{bundle.schemaError}</p> : null}
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

function SecurityScreen({
  apiConfig,
  onSnapshotLoaded
}: {
  apiConfig?: WalletApiConfig;
  onSnapshotLoaded: () => Promise<void> | void;
}) {
  const [snapshotIds, setSnapshotIds] = useState<string[]>([]);
  const [snapshotStatus, setSnapshotStatus] = useState<"idle" | "saving" | "saved" | "loading" | "loaded" | "failed">(
    "idle"
  );
  const [snapshotReport, setSnapshotReport] = useState<WalletSnapshotVerification | null>(null);
  const hasCurrentSnapshot = Boolean(apiConfig && snapshotIds.includes(apiConfig.walletId));

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

  useEffect(() => {
    if (!apiConfig) return;
    let cancelled = false;
    refreshSnapshotState()
      .then(() => undefined)
      .catch(() => {
        if (!cancelled) {
          setSnapshotReport(null);
        }
      })
    return () => {
      cancelled = true;
    };
  }, [apiConfig]);

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
      setSnapshotStatus("loaded");
    } catch {
      setSnapshotStatus("failed");
    }
  }

  return (
    <div className="screen">
      <div className="page-title">
        <p className="eyebrow">Security</p>
        <h1>Account safety</h1>
      </div>
      {!apiConfig ? (
        <StatusBanner tone="warning">Connect Abby to save and load wallet backups.</StatusBanner>
      ) : null}
      {snapshotStatus === "saved" ? <StatusBanner tone="success">Wallet backup saved.</StatusBanner> : null}
      {snapshotStatus === "loaded" ? <StatusBanner tone="success">Wallet backup loaded.</StatusBanner> : null}
      {snapshotStatus === "failed" ? <StatusBanner tone="warning">Wallet backup action failed.</StatusBanner> : null}
      <Section
        title="Wallet backups"
        actions={
          <Badge tone={hasCurrentSnapshot ? "success" : "warning"}>
            {hasCurrentSnapshot ? "backup ready" : "no backup"}
          </Badge>
        }
      >
        <div className="disclosure-package">
          <div className="disclosure-row">
            <strong>Wallet</strong>
            <span>{apiConfig?.walletId ?? "Not connected"}</span>
          </div>
          <div className="disclosure-row">
            <strong>Backups</strong>
            <span>{snapshotIds.length}</span>
          </div>
          <div className="disclosure-row">
            <strong>Backup place</strong>
            <span>{apiConfig ? "backup store" : "API required"}</span>
          </div>
          <div className="disclosure-row">
            <strong>Backup check</strong>
            <span>{snapshotReport ? (snapshotReport.valid ? "verified" : "failed") : "not checked"}</span>
          </div>
          <div className="disclosure-row">
            <strong>Backup code</strong>
            <span>{snapshotReport?.computed_hash ? <code>{shortHash(snapshotReport.computed_hash)}</code> : "Unavailable"}</span>
          </div>
        </div>
        <div className="row-actions">
          <Button disabled={!apiConfig || snapshotStatus === "saving" || snapshotStatus === "loading"} onClick={saveSnapshot}>
            <Archive size={18} /> {snapshotStatus === "saving" ? "Saving" : "Save backup"}
          </Button>
          <Button
            disabled={!apiConfig || !hasCurrentSnapshot || snapshotStatus === "saving" || snapshotStatus === "loading"}
            onClick={restoreSnapshot}
            variant="secondary"
          >
            <RefreshCw size={18} /> {snapshotStatus === "loading" ? "Loading" : "Load backup"}
          </Button>
        </div>
      </Section>
      <div className="tool-grid">
        <button className="tool-tile" type="button">
          <LockKeyhole size={24} /> Session timeout
        </button>
        <button className="tool-tile" type="button">
          <KeyRound size={24} /> Recovery settings
        </button>
        <button className="tool-tile" type="button">
          <ShieldCheck size={24} /> Bot check settings
        </button>
      </div>
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
  return (
    <div className="screen">
      <div className="page-title">
        <p className="eyebrow">Recipient access</p>
        <h1>Who can see your info</h1>
      </div>
      {accessRequests.length === 0 && grantReceipts.length === 0 ? (
        <p>No access requests or grant receipts yet.</p>
      ) : null}
      {accessRequests.length > 0 ? (
        <Section title="Access requests">
          {accessRequests.map((req) => (
            <ActionCard key={req.id} title={req.requesterName} detail={req.purpose} icon={<KeyRound size={18} />} onClick={() => undefined} />
          ))}
        </Section>
      ) : null}
      {grantReceipts.length > 0 ? (
        <Section title="Grant receipts">
          {grantReceipts.map((receipt) => (
            <ActionCard key={receipt.id} title={receipt.audienceName} detail={receipt.purpose} icon={<ShieldCheck size={18} />} onClick={() => undefined} />
          ))}
        </Section>
      ) : null}
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
        <h1>Protect your benefits</h1>
      </div>
      <Section title="Benefits opt-in">
        <label>
          <input
            type="checkbox"
            checked={optedIn}
            onChange={(e) => setOptedIn(e.target.checked)}
          />
          {" "}Enable benefits protection
        </label>
      </Section>
    </div>
  );
}
