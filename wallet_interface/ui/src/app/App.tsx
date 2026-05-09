import { ChangeEvent, FormEvent, useEffect, useMemo, useRef, useState } from "react";
import {
  Archive,
  Bell,
  BarChart3,
  CalendarCheck,
  CalendarClock,
  ClipboardCheck,
  ContactRound,
  FileUp,
  HeartHandshake,
  History,
  Home,
  KeyRound,
  Landmark,
  LockKeyhole,
  LogOut,
  Menu,
  MessageSquare,
  Mic,
  RefreshCw,
  Save,
  ShieldCheck,
  Upload,
  UsersRound,
  Wrench
} from "lucide-react";
import { ActionCard, Badge, Button, Field, Section, StatusBanner } from "../components/ui";
import { AgentChatDrawer, type AgentChatMode } from "../components/agent/AgentChatDrawer";
import { getRouteLabel } from "../agent/surfaceRegistry";
import {
  getServiceDetailDocIdFromHash,
  openCanonicalServiceDetailRoute
} from "../agent/tools/serviceDetailTools";
import type { AppActionRuntime } from "./appActions";
import { useAgentChatService } from "../services/agentChatService";
import { ServiceDetailScreen } from "./ServiceDetailScreen";
import { InteractionsScreen } from "./InteractionsScreen";
import { CalendarScreen } from "./CalendarScreen";
import {
  getServicePlanDocIdFromHash,
  ServicePlanScreen,
  setLocationServicePlanHash
} from "./ServicePlanScreen";
import { SavedServicesPanel } from "../components/services/SavedServicesPanel";
import { ServiceQuickActions } from "../components/services/ServiceQuickActions";
import { search211Info } from "../services/graphRagService";
import { getPrimaryIntakeText, getServiceLocationLabel, load211GeneratedManifest, type SearchResult } from "../lib/graphrag";
import {
  getFilecoinStorageConfig,
  toFilecoinStoragePatch,
  uploadFileToFilecoinStorage,
  uploadWalletRecordToFilecoinStorage
} from "../services/filecoinStorage";
import {
  CheckInChannel,
  AuditEvent,
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
  approveAccessRequest,
  approveThresholdApproval,
  addBinaryDocument,
  addTextDocument,
  analyzeRecordFormRedactedWithGrant,
  analyzeRecordRedactedWithGrant,
  analyzeRecordWithGrant,
  createRecordVectorProfileWithGrant,
  createLocationRegionProof,
  createRedactedGraphRAG,
  createVerifiedExportBundleView,
  delegateGrant,
  decryptRecordWithGrant,
  extractRecordTextRedactedWithGrant,
  importExportBundleView,
  issueRecordAnalysisInvocation,
  issueRecordDecryptInvocation,
  listWalletSnapshots,
  loadWalletAccessState,
  loadExportBundleView,
  loadWalletSnapshot,
  listWalletAuditEvents,
  listWalletDocuments,
  listWalletProofReceipts,
  listWalletSavedServices,
  listWalletServiceInteractions,
  listWalletServicePlans,
  rejectAccessRequest,
  repairRecordStorage,
  revokeAccessRequest,
  saveWalletService,
  saveWalletSnapshot,
  verifyWalletSnapshot,
  WalletSnapshotVerification,
  WalletApiConfig
} from "../services/walletApi";
import {
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
const MAGIC_LOGIN_PARAM = "abbyLogin";
const MAGIC_LOGIN_TTL_MS = 10 * 60 * 1000;
const MAGIC_LOGIN_DEMO_SIGNING_CONTEXT = "abby-static-demo-login-v1";

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

const routeIcons: Record<RouteId, typeof Home> = {
  home: Home,
  register: ClipboardCheck,
  "check-in": CalendarCheck,
  calendar: CalendarClock,
  contacts: ContactRound,
  "sharing-rules": ShieldCheck,
  uploads: FileUp,
  "social-services": HeartHandshake,
  interactions: History,
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
const clientNavigationRoutes = routes.filter((route) => route.id !== "shelter");
const providerNavigationRoutes = routes.filter((route) => route.id === "shelter");

function normalizeAppRoute(route: RouteId, walletConfig = readWalletApiConfig()): RouteId {
  return removedStandaloneRoutes.has(route) && !walletConfig ? "home" : route;
}

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

function normalizeLoginContact(value: string): string {
  const trimmed = value.trim();
  if (trimmed.includes("@")) return trimmed.toLowerCase();
  return trimmed.replace(/[^\d+]/g, "");
}

function isValidLoginContact(value: string): boolean {
  const normalized = normalizeLoginContact(value);
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalized) || normalized.replace(/\D/g, "").length >= 10;
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

export function App() {
  const persistedState = useMemo(() => readPersistedAppState(), []);
  const defaultAppState = useMemo(() => createDefaultAppState(persistedState), [persistedState]);
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
  const [walletAuditEvents, setWalletAuditEvents] = useState<AuditEvent[]>(auditEvents);
  const [walletProofReceipts, setWalletProofReceipts] = useState<ProofReceiptView[]>(proofReceipts);
  const [exportBundleViews, setExportBundleViews] = useState<ExportBundleView[]>(exportBundles);
  const [accessRequests, setAccessRequests] = useState<WalletAccessRequest[]>(initialAccessRequests);
  const [grantReceipts, setGrantReceipts] = useState<WalletGrantReceipt[]>(initialGrantReceipts);
  const [savedServices, setSavedServices] = useState<SavedService[]>(() => defaultAppState.savedServices);
  const [servicePlans, setServicePlans] = useState<ServicePlan[]>(() => defaultAppState.servicePlans);
  const [serviceInteractions, setServiceInteractions] = useState<ServiceInteractionEvent[]>(
    () => defaultAppState.serviceInteractions
  );
  const [walletPortalLoading, setWalletPortalLoading] = useState(false);
  const [walletPortalError, setWalletPortalError] = useState("");
  const [recipientVerified, setRecipientVerified] = useState(false);
  const [benefitsOptIn, setBenefitsOptIn] = useState(defaultAppState.benefitsOptIn);
  const [analyticsOptIn, setAnalyticsOptIn] = useState<Record<string, boolean>>(() => defaultAppState.analyticsOptIn);
  const [shelterChecklist, setShelterChecklist] = useState(() => defaultAppState.shelterChecklist);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [agentChatOpen, setAgentChatOpen] = useState(false);
  const [agentChatMode, setAgentChatMode] = useState<AgentChatMode>("text");
  const walletApiConfig = useMemo(readWalletApiConfig, []);

  function openAgentChatMode(mode: AgentChatMode) {
    setAgentChatMode(mode);
    setAgentChatOpen(true);
  }

  function toggleAgentChatMode(mode: AgentChatMode) {
    setAgentChatMode(mode);
    setAgentChatOpen((open) => (open && agentChatMode === mode ? false : true));
  }

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
      savedServices,
      servicePlans,
      serviceInteractions,
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
    savedServices,
    serviceInteractions,
    servicePlans,
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
      window.location.hash = "#/";
    }
  }

  const nextCheckIn = useMemo(() => {
    const next = new Date(policy.lastCheckInAt);
    next.setDate(next.getDate() + policy.intervalDays);
    return next.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
  }, [policy.intervalDays, policy.lastCheckInAt]);

  if (!signedInUser) {
    return (
      <LoginScreen
        onOpenAssistant={() => {
          handleSignIn("abby");
          openAgentChatMode("audio");
        }}
        onAuthenticated={(portal, contact) => {
          handleSignIn(`${portal}:${contact}`);
          navigate(portal === "provider" ? "shelter" : "home");
        }}
      />
    );
  }

  const portalMode = activeRoute === "shelter" ? "provider" : "client";
  const portalLabel = portalMode === "provider" ? "Provider workspace" : "Client portal";

  return (
    <div className={`app portal-${portalMode} ${agentChatOpen ? "app-chat-open" : ""}`}>
      <aside className="sidebar" aria-label="Primary navigation">
        <img alt={`Abby ${portalLabel}`} className="brand-logo" src="/assets/abby-icon.png" />
        <nav className="nav-sections" aria-label="Portal navigation">
          <NavigationGroup
            activeRoute={activeRoute}
            label="Client portal"
            routes={clientNavigationRoutes}
            onNavigate={navigate}
          />
          <NavigationGroup
            activeRoute={activeRoute}
            className="nav-group-provider"
            label="Provider portal"
            routes={providerNavigationRoutes}
            onNavigate={navigate}
          />
          <NavigationGroup
            activeRoute={activeRoute}
            className="nav-group-support"
            label="Analytics tools"
            routes={secondaryNavigationRoutes}
            onNavigate={navigate}
          />
        </nav>
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
            <small>{portalMode === "client" ? `Next check-in: ${nextCheckIn}` : portalLabel}</small>
          </div>
          <div className="topbar-actions">
            <Button
              ariaControls="agent-chat-bottom-sheet"
              ariaExpanded={agentChatOpen && agentChatMode === "text"}
              ariaLabel={agentChatOpen && agentChatMode === "text" ? "Close text chat" : "Open text chat"}
              onClick={() => toggleAgentChatMode("text")}
              variant="quiet"
            >
              <MessageSquare size={20} />
            </Button>
            <Button
              ariaControls="agent-chat-bottom-sheet"
              ariaExpanded={agentChatOpen && agentChatMode === "audio"}
              ariaLabel={agentChatOpen && agentChatMode === "audio" ? "Close voice chat" : "Open voice chat"}
              onClick={() => toggleAgentChatMode("audio")}
              variant="quiet"
            >
              <Mic size={20} />
            </Button>
            <Button ariaLabel="Sign out" onClick={handleSignOut} variant="quiet">
              <LogOut size={20} />
            </Button>
          </div>
        </header>

        {mobileNavOpen ? (
          <nav className="mobile-nav-panel" id="mobile-navigation" aria-label="Mobile navigation">
            <NavigationGroup
              activeRoute={activeRoute}
              label="Client portal"
              routes={clientNavigationRoutes}
              onNavigate={navigate}
            />
            <NavigationGroup
              activeRoute={activeRoute}
              className="nav-group-provider"
              label="Provider portal"
              routes={providerNavigationRoutes}
              onNavigate={navigate}
            />
            <NavigationGroup
              activeRoute={activeRoute}
              className="nav-group-support"
              label="Analytics tools"
              routes={secondaryNavigationRoutes}
              onNavigate={navigate}
            />
          </nav>
        ) : null}

        {activeRoute === "home" ? (
          <HomeScreen
            navigate={navigate}
            nextCheckIn={nextCheckIn}
            recipients={recipients}
            showReviewActions={signedInUser.toLowerCase().includes("reviewer")}
            uploads={uploads}
          />
        ) : null}
        {activeRoute === "register" ? (
          <RegistrationScreen
            profile={profile}
            setProfile={setProfile}
          />
        ) : null}
        {activeRoute === "check-in" ? (
          <CheckInScreen nextCheckIn={nextCheckIn} policy={policy} profile={profile} setPolicy={setPolicy} />
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
            servicePlans={servicePlans}
          />
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
            recipients={recipients}
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
          <ServiceDetailScreen docId={serviceDetailDocId} onBack={() => navigate("social-services")} />
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
            walletPortalError={walletPortalError}
            walletPortalLoading={walletPortalLoading}
          />
        ) : null}
        {activeRoute === "interactions" ? (
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
        {activeRoute === "shelter" ? (
          <ShelterScreen
            checklist={shelterChecklist}
            setChecklist={setShelterChecklist}
            contactRequests={shelterContactRequests}
            profile={profile}
            recipients={recipients}
            setContactRequests={setShelterContactRequests}
            setRecipients={setRecipients}
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
          <AnalyticsScreen optedIn={analyticsOptIn} setOptedIn={setAnalyticsOptIn} />
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
          <SecurityScreen apiConfig={walletApiConfig} onSnapshotLoaded={refreshWalletAfterSnapshotLoad} />
        ) : null}
        {activeRoute === "audit" ? <AuditScreen events={walletAuditEvents} /> : null}
      </main>
      <AgentChatDrawer
        activeRouteLabel={getRouteLabel(activeRoute)}
        confirmations={agentChat.pendingConfirmations}
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
          void agentChat.sendMessage(message);
        }}
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

function NavigationGroup({
  activeRoute,
  className = "",
  label,
  routes,
  onNavigate
}: {
  activeRoute: RouteId;
  className?: string;
  label: string;
  routes: Array<{ id: RouteId; label: string; icon: typeof Home }>;
  onNavigate: (route: RouteId) => void;
}) {
  return (
    <div className={`nav-group ${className}`}>
      <p className="nav-section-label">{label}</p>
      <div className="nav-list">
        {routes.map((route) => (
          <NavButton
            active={activeRoute === route.id}
            icon={route.icon}
            key={route.id}
            label={route.label}
            onClick={() => onNavigate(route.id)}
          />
        ))}
      </div>
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

function LoginScreen({
  onAuthenticated,
  onOpenAssistant
}: {
  onAuthenticated: (portal: LoginPortal, contact: string) => void;
  onOpenAssistant: () => void;
}) {
  const [portal, setPortal] = useState<LoginPortal>("client");
  const [contact, setContact] = useState("");
  const [challenge, setChallenge] = useState<LoginChallenge | null>(null);
  const [oneTimePadEntry, setOneTimePadEntry] = useState("");
  const [loginMessage, setLoginMessage] = useState("");
  const [loginError, setLoginError] = useState("");
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
    setLoginMessage("");
  }

  async function submitLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canRequestChallenge) {
      setLoginError("Enter a valid email address or telephone number.");
      return;
    }
    setPending(true);
    setLoginError("");
    setLoginMessage("");
    try {
      const issuedAt = Date.now();
      const expiresAt = issuedAt + MAGIC_LOGIN_TTL_MS;
      const normalizedContact = normalizeLoginContact(contact);
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
      setChallenge({ ...payload, oneTimePad, magicLink: magicUrl.toString() });
      setOneTimePadEntry("");
      setLoginMessage("One-time access is ready.");
    } finally {
      setPending(false);
    }
  }

  async function verifyOneTimePad() {
    if (!challenge) return;
    if (Date.now() > challenge.expiresAt) {
      setLoginError("That one-time code expired. Request a new code.");
      return;
    }
    if (oneTimePadEntry.trim() !== challenge.oneTimePad) {
      setLoginError("The one-time code does not match.");
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
      setLoginError("The login proof could not be verified.");
      return;
    }
    completeLogin(challenge.portal, challenge.contact);
  }

  async function verifyMagicLinkToken(token: string) {
    const payload = decodeMagicLoginPayload(token);
    if (!payload) {
      setLoginError("The magic link is not valid.");
      return;
    }
    if (Date.now() > payload.expiresAt) {
      setLoginError("That magic link expired. Request a new link.");
      return;
    }
    const digest = await createMagicLoginDigest(payload);
    if (digest !== payload.digest) {
      setLoginError("The magic link proof could not be verified.");
      return;
    }
    window.history.replaceState({}, "", `${window.location.pathname}${window.location.hash || "#/"}`);
    completeLogin(payload.portal, payload.contact);
  }

  function completeLogin(nextPortal: LoginPortal, normalizedContact: string) {
    onAuthenticated(nextPortal, normalizedContact);
  }

  return (
    <main className="login-page">
      <form className="login-panel" onSubmit={submitLogin}>
        <div className="login-brand">
          <img alt="Abby" className="login-logo" src="/assets/abby-icon.png" />
          <h1 className="sr-only">Sign in to Abby</h1>
        </div>
        <div className="login-portal-actions" aria-label="Choose portal" role="group">
          <button
            aria-pressed={portal === "client"}
            className="login-portal-option"
            onClick={() => updatePortal("client")}
            type="button"
          >
            <Home aria-hidden="true" size={20} />
            <span>Client</span>
          </button>
          <button
            aria-pressed={portal === "provider"}
            className="login-portal-option"
            onClick={() => updatePortal("provider")}
            type="button"
          >
            <UsersRound aria-hidden="true" size={20} />
            <span>Service provider</span>
          </button>
        </div>
        <Field label="Email address or telephone" required>
          <input
            autoComplete="username"
            inputMode="email"
            placeholder="name@example.org or (503) 555-0100"
            value={contact}
            onChange={(event) => {
              setContact(event.target.value);
              setChallenge(null);
              setOneTimePadEntry("");
              setLoginError("");
              setLoginMessage("");
            }}
          />
        </Field>
        <Button disabled={!canRequestChallenge || pending} loading={pending} loadingLabel="Preparing access" type="submit">
          <KeyRound aria-hidden="true" size={18} /> Send code or magic link
        </Button>
        {loginError ? <StatusBanner tone="danger">{loginError}</StatusBanner> : null}
        {loginMessage ? <StatusBanner tone="success">{loginMessage}</StatusBanner> : null}
        {challenge ? (
          <div className="login-challenge-panel">
            <div className="login-code-display">
              <small>Demo one-time pad number</small>
              <code aria-label="Generated one-time pad code">{challenge.oneTimePad}</code>
            </div>
            <Field label="One-time pad number" required>
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
                Verify code
              </Button>
              <a className="button button-secondary" href={challenge.magicLink}>
                Open magic link
              </a>
            </div>
            <p className="login-proof-note">
              Login proof: SHA-256(timestamp + contact + one-time salt). Production should sign this proof with a
              server-held key before sending the code or link.
            </p>
          </div>
        ) : null}
        <Button onClick={onOpenAssistant} type="button" variant="secondary">
          <MessageSquare aria-hidden="true" size={18} /> Open assistant
        </Button>
      </form>
    </main>
  );
}

function HomeScreen({
  navigate,
  nextCheckIn,
  recipients,
  showReviewActions,
  uploads
}: {
  navigate: (route: RouteId) => void;
  nextCheckIn: string;
  recipients: DisclosureRecipientDraft[];
  showReviewActions: boolean;
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
      {showReviewActions ? (
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
      ) : null}
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
  setProfile
}: {
  profile: RegistrationProfileDraft;
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

  function togglePartnerHelpRequest() {
    update({
      servicePartnerHelpRequested: !profile.servicePartnerHelpRequested,
      servicePartnerHelpRequestedAt: profile.servicePartnerHelpRequested ? "" : new Date().toISOString()
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
      </form>
      <GovernmentHelpSection
        requested={profile.servicePartnerHelpRequested}
        requestedAt={profile.servicePartnerHelpRequestedAt}
        onToggle={togglePartnerHelpRequest}
      />
    </div>
  );
}

function GovernmentHelpSection({
  onToggle,
  requested,
  requestedAt
}: {
  onToggle: () => void;
  requested: boolean;
  requestedAt: string;
}) {
  return (
    <Section title="Government help">
      <div className={`liaison-panel partner-help-panel${requested ? " partner-help-panel-active" : ""}`}>
        <MessageSquare aria-hidden="true" size={28} />
        <div>
          <h3>Get help with benefits, ID, housing, or forms.</h3>
          <p>
            {requested
              ? "This account is flagged for service partners to follow up."
              : "Only the details you choose to share will be included in the request."}
          </p>
          {requested ? (
            <div className="badge-row" aria-label="Government help request status">
              <Badge tone="warning">Help requested</Badge>
              {requestedAt ? <Badge>{formatRequestTimestamp(requestedAt)}</Badge> : null}
            </div>
          ) : null}
        </div>
        <Button ariaPressed={requested} onClick={onToggle} variant={requested ? "secondary" : "primary"}>
          {requested ? "Clear request" : "Start request"}
        </Button>
      </div>
    </Section>
  );
}

function formatRequestTimestamp(value: string): string {
  const timestamp = new Date(value);
  if (Number.isNaN(timestamp.getTime())) return "Requested";
  return `Requested ${timestamp.toLocaleDateString(undefined, { month: "short", day: "numeric" })}`;
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
  const [contactCategory, setContactCategory] = useState<"person" | "shelter">("person");
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
    if (!draft.firstName) return;
    const displayName = [draft.firstName, draft.lastName].filter(Boolean).join(" ");
    setRecipients([
      ...recipients,
      {
        id: `rec-${Date.now()}`,
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
      <Section title="Add contact">
        <div className="contact-type-toggle">
          <label className={`contact-type-option${contactCategory === "person" ? " contact-type-option--active" : ""}`}>
            <input
              checked={contactCategory === "person"}
              name="contactCategory"
              onChange={() => setContactCategory("person")}
              type="radio"
              value="person"
            />
            Person
          </label>
          <label className={`contact-type-option${contactCategory === "shelter" ? " contact-type-option--active" : ""}`}>
            <input
              checked={contactCategory === "shelter"}
              name="contactCategory"
              onChange={() => setContactCategory("shelter")}
              type="radio"
              value="shelter"
            />
            Shelter or group
          </label>
        </div>
        {contactCategory === "person" ? (
          <form className="form-grid" onSubmit={addRecipient}>
            <Field label="First name" required>
              <input value={draft.firstName} onChange={(event) => setDraft({ ...draft, firstName: event.target.value })} />
            </Field>
            <Field label="Last name">
              <input value={draft.lastName} onChange={(event) => setDraft({ ...draft, lastName: event.target.value })} />
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
        ) : (
          <>
            <p className="section-note">
              A shelter is added only after the other side says yes. It starts with Minimum identity only.
            </p>
            <form className="form-grid" onSubmit={requestShelterContact}>
              <Field label="Shelter name">
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
          </>
        )}
      </Section>
      <Section title="Saved contacts">
        {recipients.length === 0 ? (
          <p className="empty-state">No saved contacts yet. Add a shelter, group, or person above.</p>
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
                      Edit sharing for {editingRecipient.displayName}
                    </h3>
                    <p>Save only what this contact should see.</p>
                  </div>
                  <Badge>{editingScopes.length} selected</Badge>
                </div>
                <SharingScopeChecklist
                  label={`Sharing choices for ${editingRecipient.displayName}`}
                  onToggle={(scope) => setEditingScopes(toggleScopeSelection(editingScopes, scope))}
                  scopes={editingScopes}
                />
                <SharingCapabilityPreview recipientName={editingRecipient.displayName} scopes={editingScopes} />
                <div className="row-actions">
                  <Button onClick={() => saveRecipientScopes(editingRecipient.id)}>Save sharing</Button>
                  <Button onClick={() => closeRecipientEditor(editingRecipient.id)} variant="secondary">
                    Cancel
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
  apiConfig,
  refreshWalletAuditEvents,
  recipients,
  uploads,
  setUploads
}: {
  apiConfig?: WalletApiConfig;
  refreshWalletAuditEvents: () => Promise<void>;
  recipients: DisclosureRecipientDraft[];
  uploads: UploadItem[];
  setUploads: (uploads: UploadItem[]) => void;
}) {
  const [repairingUploadIds, setRepairingUploadIds] = useState<string[]>([]);
  const [filecoinUploadIds, setFilecoinUploadIds] = useState<string[]>([]);
  const [storeNewFilesOnFilecoin, setStoreNewFilesOnFilecoin] = useState(false);
  const uploadsRef = useRef(uploads);
  const filecoinStorageConfig = useMemo(() => getFilecoinStorageConfig(), []);
  const filecoinStorageReady = Boolean(filecoinStorageConfig);
  const verifiedRecipients = recipients.filter((recipient) => recipient.verified);

  useEffect(() => {
    uploadsRef.current = uploads;
  }, [uploads]);

  async function addUpload(file: File | null) {
    if (!file) return;
    const machineSummary = await generateUploadSummary(file);
    if (apiConfig?.actorDid) {
      try {
        const uploaded = normalizeWalletUpload(await addBinaryDocument(apiConfig, { file, title: machineSummary }), file.name);
        prependUpload(uploaded);
        await refreshWalletAuditEvents();
        if (storeNewFilesOnFilecoin) {
          void storeFileUploadOnFilecoin(uploaded, file);
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
          if (storeNewFilesOnFilecoin) {
            void storeFileUploadOnFilecoin(uploaded, file);
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
        decentralizedStorageMessage: "Connect a backend Filecoin storage endpoint before uploading.",
        decentralizedStorageStatus: "not_configured"
      });
      return;
    }
    setFilecoinUploadIds((uploadIds) => [...uploadIds, upload.id]);
    updateUpload(upload.id, {
      decentralizedStorageMessage: "Uploading through the configured backend.",
      decentralizedStorageStatus: "uploading"
    });
    try {
      const result = await uploadFileToFilecoinStorage(file, {
        allowedRecipientIds: upload.allowedRecipientIds ?? [],
        clientConfig: filecoinStorageConfig,
        upload,
        walletConfig: apiConfig
      });
      updateUpload(upload.id, toFilecoinStoragePatch(result));
    } catch (error) {
      updateUpload(upload.id, {
        decentralizedStorageMessage: error instanceof Error ? error.message : "IPFS/Filecoin upload failed.",
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
      decentralizedStorageMessage: "Sending wallet record to the storage backend.",
      decentralizedStorageStatus: "uploading"
    });
    try {
      const result = await uploadWalletRecordToFilecoinStorage(upload, {
        clientConfig: filecoinStorageConfig,
        walletConfig: apiConfig
      });
      updateUpload(upload.id, toFilecoinStoragePatch(result));
    } catch (error) {
      updateUpload(upload.id, {
        decentralizedStorageMessage: error instanceof Error ? error.message : "IPFS/Filecoin upload failed.",
        decentralizedStorageStatus: "failed"
      });
    } finally {
      setFilecoinUploadIds((uploadIds) => uploadIds.filter((id) => id !== upload.id));
    }
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

  return (
    <div className="screen wallet-screen">
      <div className="page-title">
        <p className="eyebrow">Wallet</p>
        <h1>Wallet</h1>
      </div>
      <Section
        title="Add wallet file"
        actions={
          <Badge tone={filecoinStorageReady ? "success" : "warning"}>
            {filecoinStorageReady ? "IPFS/Filecoin ready" : "Backend required"}
          </Badge>
        }
      >
        <div className="wallet-storage-panel">
          <div>
            <strong>Storage destination</strong>
            <small>
              {filecoinStorageReady
                ? "New files can be sent to a backend that pins to IPFS/Filecoin."
                : "Set VITE_FILECOIN_STORAGE_UPLOAD_URL or local runtime config for IPFS/Filecoin storage."}
            </small>
          </div>
          <label className="wallet-filecoin-toggle">
            <input
              checked={storeNewFilesOnFilecoin}
              disabled={!filecoinStorageReady}
              onChange={(event) => setStoreNewFilesOnFilecoin(event.target.checked)}
              type="checkbox"
            />
            <span>Store new wallet files on IPFS/Filecoin</span>
          </label>
        </div>
        <label className="upload-dropzone">
          <Upload aria-hidden="true" size={28} />
          <span>Choose a wallet file or photo</span>
          <small>Wallet files stay private until sharing is allowed.</small>
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
          <article aria-label={`${upload.fileName} wallet file`} className="list-item upload-list-item wallet-list-item" key={upload.id}>
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
                <Badge tone={upload.shared ? "success" : "neutral"}>{sharingBadge(upload)}</Badge>
                <Badge tone={filecoinBadgeTone(upload)}>{filecoinBadge(upload)}</Badge>
              </div>
              {upload.ipfsCid ? (
                <small className="wallet-storage-reference">IPFS CID: <code>{shortStorageId(upload.ipfsCid)}</code></small>
              ) : null}
              {upload.decentralizedStorageMessage ? (
                <small className="wallet-storage-reference">{upload.decentralizedStorageMessage}</small>
              ) : null}
            </div>
            <div className="row-actions list-item-action wallet-file-actions">
              {upload.storageOk === false && upload.recordId && apiConfig?.actorDid ? (
                <Button
                  disabled={repairingUploadIds.includes(upload.id)}
                  onClick={() => repairUploadStorage(upload)}
                  variant="secondary"
                >
                  <Wrench aria-hidden="true" size={18} />
                  {repairingUploadIds.includes(upload.id) ? "Fixing" : "Fix save"}
                </Button>
              ) : null}
              {filecoinStorageReady && upload.recordId && upload.decentralizedStorageStatus !== "stored" ? (
                <Button
                  disabled={filecoinUploadIds.includes(upload.id)}
                  onClick={() => void storeWalletRecordOnFilecoin(upload)}
                  variant="secondary"
                >
                  <Upload aria-hidden="true" size={18} />
                  {filecoinUploadIds.includes(upload.id) ? "Storing" : "Store on IPFS/Filecoin"}
                </Button>
              ) : null}
              <Button
                onClick={() => (upload.shared ? makePrivate(upload) : allowSharing(upload))}
                variant="secondary"
              >
                {upload.shared ? "Make private" : "Allow sharing"}
              </Button>
            </div>
            <div className="wallet-sharing-controls" aria-label={`Sharing controls for ${upload.fileName}`}>
              <div className="wallet-sharing-mode">
                <button
                  aria-pressed={(upload.sharingMode ?? "private") === "private"}
                  className="choice-chip"
                  onClick={() => makePrivate(upload)}
                  type="button"
                >
                  Private
                </button>
                <button
                  aria-pressed={(upload.sharingMode ?? "private") === "selected_contacts"}
                  className="choice-chip"
                  onClick={() => allowSharing(upload)}
                  type="button"
                >
                  Selected contacts
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
                          <small>{recipient.verified ? "verified" : "not verified"} · {recipient.relationship || recipient.agencyName || "contact"}</small>
                        </span>
                      </label>
                    ))
                  ) : (
                    <small className="upload-machine-summary">Add contacts before allowing wallet-file sharing.</small>
                  )}
                </div>
              ) : null}
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

function sharingBadge(upload: UploadItem): string {
  const count = upload.allowedRecipientIds?.length ?? 0;
  if (!upload.shared || count === 0) return "Private";
  return `${count} selected`;
}

function filecoinBadge(upload: UploadItem): string {
  if (upload.decentralizedStorageStatus === "stored") return "IPFS/Filecoin";
  if (upload.decentralizedStorageStatus === "uploading") return "storing";
  if (upload.decentralizedStorageStatus === "failed") return "storage failed";
  return "wallet storage";
}

function filecoinBadgeTone(upload: UploadItem): "neutral" | "info" | "success" | "warning" | "danger" {
  if (upload.decentralizedStorageStatus === "stored") return "success";
  if (upload.decentralizedStorageStatus === "uploading") return "info";
  if (upload.decentralizedStorageStatus === "failed") return "danger";
  return "neutral";
}

function shortStorageId(value: string): string {
  return value.length > 18 ? `${value.slice(0, 10)}...${value.slice(-6)}` : value;
}

function SocialServicesScreen({
  apiConfig,
  onOpenDetail,
  onOpenPlan,
  refreshWalletPortalState,
  savedServices,
  servicePlans,
  setSavedServices,
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
  walletPortalError: string;
  walletPortalLoading: boolean;
}) {
  const categories = ["Shelter", "Food", "Health", "Legal", "Benefits", "Transportation", "Employment", "Crisis"];
  const suggestedPrompts = ["food pantry near Portland", "emergency shelter", "utility bill help"];
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
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
      const searchResults = await search211Info(trimmedQuery, 18);
      setResults(searchResults.slice(0, 12));
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
        <p className="eyebrow">Social services</p>
        <h1>Find support</h1>
        {catalogCounts.serviceCount > 0 ? (
          <p className="supporting-copy">
            Indexed 211 service network: {formatCount(catalogCounts.serviceCount)} services,{" "}
            {formatCount(catalogCounts.phoneCount)} with direct phone handoff,{" "}
            {formatCount(catalogCounts.addressCount)} with directions, and{" "}
            {formatCount(catalogCounts.intakeCount)} with structured intake steps.
          </p>
        ) : null}
      </div>
      <Section title={catalogCounts.serviceCount > 0 ? `Search ${formatCount(catalogCounts.serviceCount)} indexed services` : "Search the 211 service index"}>
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
        {saveError ? <StatusBanner tone="warning">{saveError}</StatusBanner> : null}
        {searchStatus === "complete" && results.length === 0 ? (
          <StatusBanner tone="info">No local 211 records matched. Try a broader need or contact 211 directly.</StatusBanner>
        ) : null}
        {results.length ? (
          <div className="list-stack" aria-label="211 service search results">
            {results.map((result) => {
              const document = result.document;
              const provider = document.provider_name || "Provider not listed";
              const program = document.program_name || document.title || "Program not listed";
              const location = getServiceLocationLabel(document);
              const intake = getPrimaryIntakeText(document);
              return (
                <article className="list-item" key={result.docId}>
                  <div>
                    <h3>{program}</h3>
                    <p>{provider}</p>
                    <small className="upload-machine-summary">{result.snippet}</small>
                    {intake ? <small className="upload-machine-summary">Apply: {intake}</small> : null}
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
                    <ServiceQuickActions document={document} />
                    <Button
                      disabled={savedServices.some((service) => service.service_doc_id === result.docId)}
                      loading={savingDocIds.includes(result.docId)}
                      loadingLabel="Saving"
                      onClick={() => void saveResult(result)}
                      variant="secondary"
                    >
                      <Save aria-hidden="true" size={18} />
                      {savedServices.some((service) => service.service_doc_id === result.docId) ? "Saved" : "Save"}
                    </Button>
                    <Button onClick={() => onOpenPlan(result.docId)} variant="secondary">
                      <CalendarClock aria-hidden="true" size={18} />
                      Plan
                    </Button>
                    <Button onClick={() => onOpenDetail(result.docId)} variant="secondary">
                      Open detail
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
        servicePlans={servicePlans}
      />
      <div className="category-grid">
        {categories.map((category) => (
          <button className="category-tile" key={category} onClick={() => void runSearch(category)} type="button">
            <HeartHandshake aria-hidden="true" size={22} />
            <span>{category}</span>
          </button>
        ))}
      </div>
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
  profile,
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
  profile: RegistrationProfileDraft;
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
      {profile.servicePartnerHelpRequested ? (
        <Section title="Partner help requests">
          <article className="list-item partner-help-request">
            <div>
              <h3>{partnerHelpDisplayName}</h3>
              <p>Government help requested for benefits, ID, housing, or forms.</p>
              <div className="badge-row">
                <Badge tone="warning">Needs partner help</Badge>
                <Badge>{formatRequestTimestamp(profile.servicePartnerHelpRequestedAt)}</Badge>
                <Badge>{partnerHelpNeeds}</Badge>
              </div>
              <small>{partnerHelpContact || "No contact method added yet"}</small>
            </div>
          </article>
        </Section>
      ) : null}
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
        <h1>Benefits notice</h1>
      </div>
      <StatusBanner tone="warning">
        Abby can ask approved agencies for help. This does not promise benefits.
      </StatusBanner>
      <Section title="Benefits choice">
        <div className="capability-preview" role="group" aria-label="Benefits notification capability preview">
          <div className="scope-header">
            <div>
              <h4>What this allows</h4>
              <p>benefits status and notice details only</p>
            </div>
            <Badge tone={optedIn ? "success" : "neutral"}>{optedIn ? "ready to save" : "off"}</Badge>
          </div>
          <div className="disclosure-package">
            <div className="disclosure-row">
              <strong>Can do</strong>
              <span>{plainCapabilitySummary(["metadata/read", "derived/read"])}</span>
            </div>
            <div className="disclosure-row">
              <strong>Items</strong>
              <span>Benefits information, Notice request</span>
            </div>
            <div className="disclosure-row">
              <strong>Not allowed</strong>
              <span>{plainNonGrantedCapabilities(["metadata/read", "derived/read"]).join(", ")}</span>
            </div>
          </div>
        </div>
        <label className="consent-box">
          <input checked={optedIn} onChange={(event) => setOptedIn(event.target.checked)} type="checkbox" />
          <span>
            <strong>Allow Abby to prepare a benefits notice for agency help.</strong>
            <small>This starts on. You can turn it off. A privacy and legal team must review this before real use.</small>
          </span>
        </label>
        <Button>
          <Landmark size={18} /> Save setting
        </Button>
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

  const selectedStudyCount = analyticsStudies.filter((study) => isStudySelected(study.id)).length;
  const pausedStudyCount = analyticsStudies.filter((study) => study.status === "paused").length;
  const availableStudyCount = analyticsStudies.length - pausedStudyCount;
  const totalPrivacyBudget = analyticsStudies.reduce((sum, study) => sum + study.epsilonBudget, 0);
  const spentPrivacyBudget = analyticsStudies.reduce((sum, study) => sum + study.spentBudget, 0);
  const privacyBudgetLeft = Math.max(0, totalPrivacyBudget - spentPrivacyBudget);

  return (
    <div className="screen analytics-screen">
      <div className="page-title">
        <p className="eyebrow">Analytics tools</p>
        <h1>Share group facts, not your name</h1>
      </div>
      <p className="page-note">
        These choices start on. You can turn off any one. We use group facts, not names or contact details.
      </p>
      <StatusBanner tone="warning">
        A privacy and legal team must review this before real use.
      </StatusBanner>
      <Section eyebrow="Admin view" title="Admin introspection">
        <p className="section-note">
          Project admins and service organization admins can inspect aggregate operations without seeing raw wallet
          records, exact locations, names, or contact details.
        </p>
        <div className="analytics-admin-grid">
          <article aria-label="211-AI project admin analytics introspection" className="analytics-card analytics-admin-card">
            <div className="scope-header">
              <div>
                <h3>211-AI project admins</h3>
                <p>Inspect template health, privacy budget use, and aggregate coverage across participating services.</p>
              </div>
              <Badge tone="success">Project admin</Badge>
            </div>
            <div className="privacy-metrics">
              <StatusPanel label="Templates" value={String(analyticsStudies.length)} tone="teal" />
              <StatusPanel label="Privacy left" value={privacyBudgetLeft.toFixed(2)} tone="gold" />
            </div>
            <div className="disclosure-package">
              <div className="disclosure-row">
                <strong>Can inspect</strong>
                <span>Template status, cohort floors, privacy spend, consent coverage, organization participation</span>
              </div>
              <div className="disclosure-row">
                <strong>Use for</strong>
                <span>System QA, grant reporting, product safety reviews, privacy and legal audit preparation</span>
              </div>
              <div className="disclosure-row">
                <strong>Not allowed</strong>
                <span>Raw wallet records, names, contact details, exact locations, files, or private notes</span>
              </div>
            </div>
          </article>
          <article
            aria-label="Service organization admin analytics introspection"
            className="analytics-card analytics-admin-card"
          >
            <div className="scope-header">
              <div>
                <h3>Service organization admins</h3>
                <p>Inspect their own service demand, referral outcomes, and approved aggregate cohorts.</p>
              </div>
              <Badge tone="info">Organization admin</Badge>
            </div>
            <div className="privacy-metrics">
              <StatusPanel label="Active" value={String(availableStudyCount)} tone="teal" />
              <StatusPanel label="Paused" value={String(pausedStudyCount)} tone="gold" />
            </div>
            <div className="disclosure-package">
              <div className="disclosure-row">
                <strong>Can inspect</strong>
                <span>Own organization programs, aggregate need categories, referral counts, consented cohort health</span>
              </div>
              <div className="disclosure-row">
                <strong>Use for</strong>
                <span>Capacity planning, service gaps, outreach coordination, and accountable reporting</span>
              </div>
              <div className="disclosure-row">
                <strong>Not allowed</strong>
                <span>Cross-organization row-level views, personal records, exact addresses, or unapproved exports</span>
              </div>
            </div>
          </article>
        </div>
      </Section>
      <Section title="Resident group fact choices">
        <div className="privacy-metrics">
          <StatusPanel label="Choices on" value={`${selectedStudyCount}/${analyticsStudies.length}`} tone="teal" />
          <StatusPanel label="Privacy left" value={privacyBudgetLeft.toFixed(2)} tone="gold" />
        </div>
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
      </Section>
    </div>
  );
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
      <p className="page-note">
        Proof receipts expose public claims and verifier details without showing raw documents or precise location.
      </p>
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
        {visibleProofCenterProofs(proofs).map((proof) => {
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
