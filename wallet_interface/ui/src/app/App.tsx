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
import {
  base64ToBytes,
  buildWalletFileStats,
  filecoinActionLabel,
  filecoinBadge,
  filecoinBadgeTone,
  getWalletFileFilterOptions,
  ipfsGatewayHref,
  privacyProfileBadge,
  privacyProfileBadgeTone,
  searchWalletFiles,
  sharingBadge,
  shortStorageId,
  shouldShowFilecoinAction,
  uploadTypeLabel,
  type WalletFileFilterMode,
  type WalletFileSortMode
} from "./utils/walletFiles";
import {
  contactLabelForShelterUser,
  formatProviderActivityDate,
  formatProviderPercent,
  formatShelterDate,
  latestProviderTimestamp,
  providerActivityToneLabel,
  providerCasePriorityLabel,
  providerCasePriorityRank,
  providerCaseStatusLabel,
  providerClientCommitment,
  providerEligibilityClaim,
  providerEligibilityLabel,
  providerProofClientLabel,
  providerProofTypeLabel,
  providerProofVerificationStatusLabel
} from "./utils/providerHelpers";
import {
  analysisLines,
  artifactLines,
  buildDocumentPrivacyProfilePublicInputs,
  buildFallbackDocumentProfileOutput,
  buildOpenRouterOrganizerProfile,
  buildPrivacySearchText,
  buildPrivacyVectorTerms,
  classifyDocumentProfile,
  compactRecord,
  defaultLabelsForMimeType,
  detectDecryptedMimeType,
  displayMimeType,
  normalizePublicMimeType,
  outputTypeForAnalysisMode,
  readStringArray,
  receiptHasAbility,
  receiptRequiresUserPresence,
  runDerivedAnalysis,
  summarizeDerivedOutput,
  summarizeDocumentPrivacyProfile,
  toSafeOrganizerSignal,
  type RecipientAnalysisMode
} from "./utils/privacyProfile";
import { LoginScreen } from "./screens/LoginScreen";
import { HomeScreen } from "./screens/HomeScreen";
import { RegistrationScreen } from "./screens/RegistrationScreen";
import { SettingsScreen } from "./screens/SettingsScreen";
import { CheckInScreen } from "./screens/CheckInScreen";
import { ClientMessagesScreen } from "./screens/ClientMessagesScreen";
import { ContactsScreen } from "./screens/ContactsScreen";
import { SocialServicesScreen } from "./screens/SocialServicesScreen";
import { ShelterScreen } from "./screens/ShelterScreen";
import { RecipientAccessScreen } from "./screens/RecipientAccessScreen";
import { UploadsScreen } from "./screens/UploadsScreen";
import { ProfileInformationForm, togglePartnerHelpRequest } from "./components/ProfileInformationForm";
import { GovernmentHelpSection } from "./components/GovernmentHelpSection";
import { SharingScopeChecklist, SharingCapabilityPreview } from "./components/SharingScopeComponents";
import {
  APP_SESSION_KEY, MAGIC_LOGIN_PARAM, MAGIC_LOGIN_TTL_MS, MAGIC_LOGIN_UCAN_KEY,
  WALLET_RECOVERY_BUNDLE_CACHE_PREFIX, WALLET_DEVICE_RECOVERY_KEY_PREFIX,
  randomBase64Url, randomHex, bytesToBase64Url, base64UrlToBytes, bytesToArrayBuffer,
  deriveRecoveryPassphraseKey, sha256Base64Url,
  walletDeviceRecoveryStorageKey, readWalletDeviceRecoveryRawKey, storeWalletDeviceRecoveryRawKey,
  getOrCreateWalletDeviceRecoveryRawKey, getOrCreateWalletDeviceRecoveryKey,
  buildEncryptedRecoveryBundle, buildPassphraseWrappedRecoveryBundle, decryptPassphraseRecoveryBundle,
  readCachedRecoveryBundle, readMagicLoginUcan, buildWalletRecoveryQrPayload, parseWalletRecoveryQrPayload,
  buildClientWrappedRecoveryBundle, cacheEncryptedRecoveryBundleFromMagicLogin,
  randomOneTimePad, encodeMagicLoginPayload, decodeMagicLoginPayload, createMagicLoginDigest,
  normalizeLoginContact, isValidLoginContact, resolveMagicLoginApiBaseUrl, normalizeServerWalletConfig,
  requestServerMagicLogin, verifyServerMagicLogin, shouldAllowLocalMagicLoginFallback,
  getInitialRouteFromHash, readSignedInUser, createGeneratedWalletOwnerDid, resolveWalletOwnerDid,
  type LoginPortal, type MagicLoginPayload, type LoginChallenge, type LoginAuthResult,
  type ServerMagicLoginResponse, type WalletRecoveryQrPayload,
} from "./utils/authHelpers";
import {
  ID_DOCUMENT_ACCEPT_ATTR, PROOF_QR_IMAGE_ACCEPT_ATTR, ID_DOCUMENT_ACCEPTED_TYPES, ID_DOCUMENT_ACCEPTED_EXTENSIONS,
  PORTLAND_POLICE_MISSING_EMAIL, DEFAULT_LOCAL_PRECINCT, LOCAL_PRECINCT_OPTIONS, LOCAL_PRECINCT_RELATIONSHIP,
  isAcceptedIdentityDocument, getIdentityDocumentFileDetail,
  formatRecipientType, localizedPrecinctName, localizedRelationshipName, formatContactRequestStatus,
  isLocalPrecinctRecipient, createEntityId,
  disclosureScopeLabelKey, disclosureScopeDetailKey, getDisclosureScopeLabels, toggleScopeSelection,
  formatLocalizedCapability, formatLocalizedCapabilitySummary, formatLocalizedNonGrantedCapabilities,
  analyticsNeverPublishedText, analyticsProviderPublicationFloor,
  parseAnalyticsProofNumber, calculatePercent, formatAnalyticsProofValue, formatAnalyticsField,
  hiddenProofCenterProofTypes, visibleProofCenterProofs, summarizeWalletProofClaims,
  toShortSummaryTitle, generateUploadSummary,
  formatCheckInChannel, formatProviderMessageChannel, formatRequestTimestamp,
  normalizeClientMessageKey, messageMatchesClient,
} from "./utils/formatHelpers";
import {
  formatDeadDropFileTimestamp, getMissingPersonDeadDropDueAt, isMissingPersonDeadDropDue,
  buildMissingPersonDeadDropBundle, buildMissingPersonDeadDropEmail, buildMissingPersonDeadDropSyncPayload,
} from "./utils/deadDropHelpers";
import {
  appStableSuffix, toSaveWalletServiceInput, toLocalSavedService, formatCount,
  parseHomeDate, describeHomeUrgency, formatHomeDateTime, buildHomeCalendarItems,
  formatServiceLocationLabel, choosePreferredServiceLocation, buildSearchResultLocationLabels,
  type HomeServiceSuggestion, type HomeCalendarItem,
} from "./utils/serviceHelpers";
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

  const openServicePlanFromServices = useCallback((nextDocId: string) => {
    setLocationServicePlanHash(nextDocId);
    setServicePlanDocId(nextDocId);
    setServiceDetailDocId(null);
    activeRouteRef.current = "social-services";
    setActiveRoute("social-services");
    setMobileNavOpen(false);
  }, []);

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
            onOpenPlan={openServicePlanFromServices}
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
            onOpenPlan={openServicePlanFromServices}
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
            onOpenPlan={openServicePlanFromServices}
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

