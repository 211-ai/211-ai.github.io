import { useCallback, useMemo, useRef, useState } from "react";
import { LogOut, Menu, MessageSquare, Mic } from "lucide-react";
import { Button } from "../shared/components/ui";
import { AgentChatDrawer, type AgentChatMode } from "../features/agent/components/AgentChatDrawer";
import { primeVoiceChatActivation } from "../features/agent/components/AgentAudioChatSurface";
import type { AppActionRuntime } from "./appActions";
import { useAgentChatService } from "../features/agent/lib/agentChatService";
import { getServicePlanDocIdFromHash, setLocationServicePlanHash } from "../features/service-navigation/components/ServicePlanScreen";
import { getServiceDetailDocIdFromHash, openCanonicalServiceDetailRoute } from "../features/agent/lib/tools/serviceDetailTools";
import { getRouteLabel } from "../features/agent/lib/surfaceRegistry";
import type {
  AuditEvent,
  CheckInPolicyDraft,
  DisclosureRecipientDraft,
  ExportBundleView,
  ProofReceiptView,
  RegistrationProfileDraft,
  RouteId,
  SavedService,
  ServiceInteractionEvent,
  ServicePlan,
  ShelterContactRequest,
  UploadItem,
  WalletAccessRequest,
  WalletGrantReceipt,
} from "../models/abby";
import type { WalletApiConfig } from "../features/wallet/lib/walletApi";
import {
  auditEvents,
  exportBundles,
  initialAccessRequests,
  initialGrantReceipts,
  proofReceipts,
} from "../features/wallet/lib/mockAbbyService";
import {
  createDefaultAppState,
  defaultShelterChecklist,
  readPersistedAppState,
  setLocationRouteHash,
  type ShelterCaseRecord,
  type ShelterProviderMessage,
  type ShelterStaffAccount,
  type ShelterUserAccount,
} from "./appState";
import {
  detectBrowserLocale,
  normalizeSiteLocale,
  readAssistantAutoTranslatePreference,
  readAssistantTranslationLocalePreference,
  readSiteLocalePreference,
  SUPPORTED_LOCALES,
  t,
  translateRouteLabel,
  type SupportedLocale,
} from "../shared/lib/localization";
import { NavigationGroup } from "./components/NavigationGroup";
import {
  clientNavigationRoutes,
  normalizeAppRoute,
  providerNavigationRoutes,
  providerRouteIds,
  secondaryNavigationRoutes,
} from "./config/navigation";
import { readWalletApiBaseUrl, readWalletApiConfig, WALLET_API_CONFIG_KEY } from "./services/walletConfig";
import { LoginScreen } from "../features/wallet/components/LoginScreen";
import {
  APP_SESSION_KEY,
  cacheEncryptedRecoveryBundleFromMagicLogin,
  getInitialRouteFromHash,
  MAGIC_LOGIN_UCAN_KEY,
  readSignedInUser,
} from "./utils/authHelpers";
import { useHashRouteSync } from "./hooks/useHashRouteSync";
import { usePersistState } from "./hooks/usePersistState";
import { useLocaleSync } from "./hooks/useLocaleSync";
import { useWalletSync } from "./hooks/useWalletSync";
import { useDeadDropSync } from "./hooks/useDeadDropSync";
import { AppRouter } from "./components/AppRouter";

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
  const [policy, setPolicy] = useState<CheckInPolicyDraft>(() => defaultAppState.policy);
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
  const [siteLocale, setSiteLocale] = useState<SupportedLocale>(
    () => readSiteLocalePreference() ?? normalizeSiteLocale(browserLocale)
  );
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
  const [analyticsOptIn, setAnalyticsOptIn] = useState<Record<string, boolean>>(
    () => defaultAppState.analyticsOptIn
  );
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

  const {
    refreshWalletAccessState,
    refreshWalletAfterSnapshotLoad,
    refreshWalletAuditEvents,
    refreshWalletPortalState,
  } = useWalletSync(walletApiConfig, persistWalletApiConfig, {
    setAccessRequests,
    setExportBundleViews,
    setGrantReceipts,
    setSavedServices,
    setServiceInteractions,
    setServicePlans,
    setUploads,
    setWalletActorResolved,
    setWalletAuditEvents,
    setWalletPortalError,
    setWalletPortalLoading,
    setWalletProofReceipts,
  });

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
        permissionLevel: "wallet_write" as const,
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
      refreshWalletAuditEvents,
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
      walletProofReceipts,
      refreshWalletAccessState,
      refreshWalletAuditEvents,
    ]
  );
  const agentChat = useAgentChatService(agentRuntime);

  const { sendMissingPersonDeadDrop } = useDeadDropSync({
    missingPersonDeadDropEnabled,
    missingPersonDeadDropLastSentForCheckInAt,
    policy,
    profile,
    recipients,
    setMissingPersonDeadDropLastSentForCheckInAt,
    uploads,
    walletApiConfig,
    walletDeadDropReady,
  });

  useHashRouteSync({ activeRouteRef, setActiveRoute, setMobileNavOpen, setServiceDetailDocId, setServicePlanDocId });

  usePersistState({
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
    shelterChecklist,
    shelterContactRequests,
    shelterCaseRecords,
    shelterProviderMessages,
    shelterStaffAccounts,
    shelterUserAccounts,
    uploads,
    walletProofReceipts,
  });

  useLocaleSync(siteLocale, assistantTranslationLocale, assistantAutoTranslate);

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
      setMobileNavOpen,
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

        <AppRouter
          accessRequests={accessRequests}
          activeRoute={activeRoute}
          analyticsOptIn={analyticsOptIn}
          assistantAutoTranslate={assistantAutoTranslate}
          assistantTranslationLocale={assistantTranslationLocale}
          benefitsOptIn={benefitsOptIn}
          browserLocale={browserLocale}
          exportBundleViews={exportBundleViews}
          grantReceipts={grantReceipts}
          missingPersonDeadDropEnabled={missingPersonDeadDropEnabled}
          navigate={navigate}
          nextCheckIn={nextCheckIn}
          onOpenPlan={openServicePlanFromServices}
          onOpenService={openServiceDetailFromServices}
          persistWalletApiConfig={persistWalletApiConfig}
          policy={policy}
          profile={profile}
          recipients={recipients}
          recipientVerified={recipientVerified}
          refreshWalletAccessState={refreshWalletAccessState}
          refreshWalletAfterSnapshotLoad={refreshWalletAfterSnapshotLoad}
          refreshWalletAuditEvents={refreshWalletAuditEvents}
          refreshWalletPortalState={refreshWalletPortalState}
          savedServices={savedServices}
          sendMissingPersonDeadDrop={sendMissingPersonDeadDrop}
          serviceDetailDocId={serviceDetailDocId}
          serviceInteractions={serviceInteractions}
          servicePlanDocId={servicePlanDocId}
          servicePlans={servicePlans}
          setAccessRequests={setAccessRequests}
          setAnalyticsOptIn={setAnalyticsOptIn}
          setAssistantAutoTranslate={setAssistantAutoTranslate}
          setAssistantTranslationLocale={setAssistantTranslationLocale}
          setBenefitsOptIn={setBenefitsOptIn}
          setSavedServices={setSavedServices}
          setExportBundleViews={setExportBundleViews}
          setGrantReceipts={setGrantReceipts}
          setMissingPersonDeadDropEnabled={setMissingPersonDeadDropEnabled}
          setPolicy={setPolicy}
          setProfile={setProfile}
          setRecipientVerified={setRecipientVerified}
          setRecipients={setRecipients}
          setShelterCaseRecords={setShelterCaseRecords}
          setShelterChecklist={setShelterChecklist}
          setShelterContactRequests={setShelterContactRequests}
          setShelterProviderMessages={setShelterProviderMessages}
          setShelterStaffAccounts={setShelterStaffAccounts}
          setShelterUserAccounts={setShelterUserAccounts}
          setServiceInteractions={setServiceInteractions}
          setServicePlans={setServicePlans}
          setSiteLocale={setSiteLocale}
          setUploads={setUploads}
          setWalletProofReceipts={setWalletProofReceipts}
          shelterCaseRecords={shelterCaseRecords}
          shelterChecklist={shelterChecklist}
          shelterContactRequests={shelterContactRequests}
          shelterProviderMessages={shelterProviderMessages}
          shelterStaffAccounts={shelterStaffAccounts}
          shelterUserAccounts={shelterUserAccounts}
          signedInUser={signedInUser}
          siteLocale={siteLocale}
          uploads={uploads}
          walletAuditEvents={walletAuditEvents}
          walletApiBaseUrl={walletApiBaseUrl}
          walletApiConfig={walletApiConfig}
          walletDeadDropReady={walletDeadDropReady}
          walletPortalError={walletPortalError}
          walletPortalLoading={walletPortalLoading}
          walletProofReceipts={walletProofReceipts}
        />
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
            setMobileNavOpen,
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
