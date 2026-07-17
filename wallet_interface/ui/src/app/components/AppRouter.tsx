import type { Dispatch, SetStateAction } from "react";
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
} from "../../models/abby";
import type { WalletApiConfig } from "../../features/wallet/lib/walletApi";
import type { SupportedLocale } from "../../shared/lib/localization";
import type {
  ShelterCaseRecord,
  ShelterProviderMessage,
  ShelterStaffAccount,
  ShelterUserAccount,
  defaultShelterChecklist,
} from "../appState";
import type { ProviderPortalView } from "../config/navigation";
import { providerRouteIds, getProviderPortalView } from "../config/navigation";
import { AnalyticsScreen } from "../../features/wallet/components/AnalyticsScreen";
import { BenefitsProtectionScreen } from "../../features/wallet/components/BenefitsProtectionScreen";
import { CheckInScreen } from "../../features/service-navigation/components/CheckInScreen";
import { ClientMessagesScreen } from "../../features/interactions/components/ClientMessagesScreen";
import { ContactsScreen } from "../../features/wallet/components/ContactsScreen";
import { HomeScreen } from "../../features/service-navigation/components/HomeScreen";
import { ProofCenterScreen } from "../../features/wallet/components/ProofCenterScreen";
import { RecipientAccessScreen } from "../../features/wallet/components/RecipientAccessScreen";
import { RegistrationScreen } from "../../features/wallet/components/RegistrationScreen";
import { SettingsScreen } from "../../features/wallet/components/SettingsScreen";
import { ShelterScreen } from "../../features/service-navigation/components/ShelterScreen";
import { SocialServicesScreen } from "../../features/service-navigation/components/SocialServicesScreen";
import { UploadsScreen } from "../../features/wallet/components/UploadsScreen";
import { CalendarScreen } from "../../features/calendar/components/CalendarScreen";
import { InteractionsScreen } from "../../features/interactions/components/InteractionsScreen";
import { ServiceDetailScreen } from "../../features/service-navigation/components/ServiceDetailScreen";
import { ServicePlanScreen } from "../../features/service-navigation/components/ServicePlanScreen";
import { ExportCenterScreen } from "../../features/wallet/components/ExportCenterScreen";

export interface AppRouterProps {
  // Routing
  activeRoute: RouteId;
  navigate: (route: RouteId) => void;
  onOpenService: (docId: string) => void;
  onOpenPlan: (docId: string) => void;
  serviceDetailDocId: string | null;
  servicePlanDocId: string | null;

  // Session
  browserLocale: string;
  nextCheckIn: string;
  signedInUser: string;
  siteLocale: SupportedLocale;
  setSiteLocale: Dispatch<SetStateAction<SupportedLocale>>;

  // Profile / policy / recipients
  policy: CheckInPolicyDraft;
  profile: RegistrationProfileDraft;
  recipients: DisclosureRecipientDraft[];
  setPolicy: Dispatch<SetStateAction<CheckInPolicyDraft>>;
  setProfile: Dispatch<SetStateAction<RegistrationProfileDraft>>;
  setRecipients: Dispatch<SetStateAction<DisclosureRecipientDraft[]>>;

  // Wallet config
  persistWalletApiConfig: (config: WalletApiConfig) => void;
  walletApiBaseUrl?: string;
  walletApiConfig: WalletApiConfig | undefined;
  walletDeadDropReady: boolean;
  walletPortalError: string;
  walletPortalLoading: boolean;

  // Wallet refresh
  refreshWalletAccessState: () => Promise<void>;
  refreshWalletAfterSnapshotLoad: () => Promise<void>;
  refreshWalletAuditEvents: () => Promise<void>;
  refreshWalletPortalState: () => Promise<void>;

  // Uploads / files
  exportBundleViews: ExportBundleView[];
  setExportBundleViews: Dispatch<SetStateAction<ExportBundleView[]>>;
  uploads: UploadItem[];
  setUploads: Dispatch<SetStateAction<UploadItem[]>>;
  walletAuditEvents: AuditEvent[];
  walletProofReceipts: ProofReceiptView[];
  setWalletProofReceipts: Dispatch<SetStateAction<ProofReceiptView[]>>;

  // Access / grants
  accessRequests: WalletAccessRequest[];
  grantReceipts: WalletGrantReceipt[];
  recipientVerified: boolean;
  setAccessRequests: Dispatch<SetStateAction<WalletAccessRequest[]>>;
  setGrantReceipts: Dispatch<SetStateAction<WalletGrantReceipt[]>>;
  setRecipientVerified: Dispatch<SetStateAction<boolean>>;

  // Services
  savedServices: SavedService[];
  setSavedServices: Dispatch<SetStateAction<SavedService[]>>;
  serviceInteractions: ServiceInteractionEvent[];
  setServiceInteractions: Dispatch<SetStateAction<ServiceInteractionEvent[]>>;
  servicePlans: ServicePlan[];
  setServicePlans: Dispatch<SetStateAction<ServicePlan[]>>;

  // Analytics / benefits / settings
  analyticsOptIn: Record<string, boolean>;
  assistantAutoTranslate: boolean;
  assistantTranslationLocale: string;
  benefitsOptIn: boolean;
  missingPersonDeadDropEnabled: boolean;
  sendMissingPersonDeadDrop: () => Promise<boolean>;
  setAnalyticsOptIn: Dispatch<SetStateAction<Record<string, boolean>>>;
  setAssistantAutoTranslate: Dispatch<SetStateAction<boolean>>;
  setAssistantTranslationLocale: Dispatch<SetStateAction<string>>;
  setBenefitsOptIn: Dispatch<SetStateAction<boolean>>;
  setMissingPersonDeadDropEnabled: Dispatch<SetStateAction<boolean>>;

  // Shelter / provider
  setShelterCaseRecords: Dispatch<SetStateAction<ShelterCaseRecord[]>>;
  setShelterChecklist: Dispatch<SetStateAction<typeof defaultShelterChecklist>>;
  setShelterContactRequests: Dispatch<SetStateAction<ShelterContactRequest[]>>;
  setShelterProviderMessages: Dispatch<SetStateAction<ShelterProviderMessage[]>>;
  setShelterStaffAccounts: Dispatch<SetStateAction<ShelterStaffAccount[]>>;
  setShelterUserAccounts: Dispatch<SetStateAction<ShelterUserAccount[]>>;
  shelterCaseRecords: ShelterCaseRecord[];
  shelterChecklist: typeof defaultShelterChecklist;
  shelterContactRequests: ShelterContactRequest[];
  shelterProviderMessages: ShelterProviderMessage[];
  shelterStaffAccounts: ShelterStaffAccount[];
  shelterUserAccounts: ShelterUserAccount[];
}

export function AppRouter({
  accessRequests,
  activeRoute,
  analyticsOptIn,
  assistantAutoTranslate,
  assistantTranslationLocale,
  benefitsOptIn,
  browserLocale,
  exportBundleViews,
  grantReceipts,
  missingPersonDeadDropEnabled,
  navigate,
  nextCheckIn,
  onOpenPlan,
  onOpenService,
  persistWalletApiConfig,
  policy,
  profile,
  recipients,
  recipientVerified,
  refreshWalletAccessState,
  refreshWalletAfterSnapshotLoad,
  refreshWalletAuditEvents,
  refreshWalletPortalState,
  savedServices,
  sendMissingPersonDeadDrop,
  serviceDetailDocId,
  serviceInteractions,
  servicePlanDocId,
  servicePlans,
  setAccessRequests,
  setAnalyticsOptIn,
  setAssistantAutoTranslate,
  setAssistantTranslationLocale,
  setBenefitsOptIn,
  setExportBundleViews,
  setGrantReceipts,
  setMissingPersonDeadDropEnabled,
  setPolicy,
  setProfile,
  setRecipientVerified,
  setRecipients,
  setSavedServices,
  setShelterCaseRecords,
  setShelterChecklist,
  setShelterContactRequests,
  setShelterProviderMessages,
  setShelterStaffAccounts,
  setShelterUserAccounts,
  setServiceInteractions,
  setServicePlans,
  setSiteLocale,
  setUploads,
  setWalletProofReceipts,
  shelterCaseRecords,
  shelterChecklist,
  shelterContactRequests,
  shelterProviderMessages,
  shelterStaffAccounts,
  shelterUserAccounts,
  signedInUser,
  siteLocale,
  uploads,
  walletAuditEvents,
  walletApiBaseUrl,
  walletApiConfig,
  walletDeadDropReady,
  walletPortalError,
  walletPortalLoading,
  walletProofReceipts,
}: AppRouterProps) {
  return (
    <>
      {activeRoute === "home" ? (
        <HomeScreen
          navigate={navigate}
          nextCheckIn={nextCheckIn}
          onOpenService={onOpenService}
          policy={policy}
          profile={profile}
          providerMessages={shelterProviderMessages}
          recipients={recipients}
          serviceInteractions={serviceInteractions}
          servicePlans={servicePlans}
          showReviewActions={signedInUser.toLowerCase().includes("reviewer")}
          signedInUser={signedInUser}
          siteLocale={siteLocale}
          uploads={uploads}
        />
      ) : null}
      {activeRoute === "register" ? (
        <RegistrationScreen
          apiConfig={walletApiConfig}
          onWorldIdAuditRefresh={refreshWalletAuditEvents}
          profile={profile}
          setProfile={setProfile}
          siteLocale={siteLocale}
        />
      ) : null}
      {activeRoute === "settings" ? (
        <SettingsScreen
          analyticsOptIn={analyticsOptIn}
          apiConfig={walletApiConfig}
          assistantAutoTranslate={assistantAutoTranslate}
          assistantTranslationLocale={assistantTranslationLocale}
          benefitsOptIn={benefitsOptIn}
          browserLocale={browserLocale}
          missingPersonDeadDropEnabled={missingPersonDeadDropEnabled}
          navigate={navigate}
          nextCheckIn={nextCheckIn}
          onWorldIdAuditRefresh={refreshWalletAuditEvents}
          onSnapshotLoaded={refreshWalletAfterSnapshotLoad}
          policy={policy}
          profile={profile}
          sendMissingPersonDeadDrop={sendMissingPersonDeadDrop}
          setAnalyticsOptIn={setAnalyticsOptIn}
          setAssistantAutoTranslate={setAssistantAutoTranslate}
          setAssistantTranslationLocale={setAssistantTranslationLocale}
          setBenefitsOptIn={setBenefitsOptIn}
          setMissingPersonDeadDropEnabled={setMissingPersonDeadDropEnabled}
          setPolicy={setPolicy}
          setProfile={setProfile}
          setSiteLocale={setSiteLocale}
          siteLocale={siteLocale}
          walletConnected={Boolean(walletApiConfig)}
          walletDeadDropReady={walletDeadDropReady}
        />
      ) : null}
      {activeRoute === "check-in" ? (
        <CheckInScreen
          nextCheckIn={nextCheckIn}
          policy={policy}
          profile={profile}
          setPolicy={setPolicy}
          siteLocale={siteLocale}
        />
      ) : null}
      {activeRoute === "calendar" ? (
        <CalendarScreen
          interactions={serviceInteractions}
          onOpenPlan={onOpenPlan}
          onOpenService={onOpenService}
          policy={policy}
          servicePlans={servicePlans}
          siteLocale={siteLocale}
        />
      ) : null}
      {activeRoute === "messages" ? (
        <ClientMessagesScreen
          profile={profile}
          providerMessages={shelterProviderMessages}
          setProviderMessages={setShelterProviderMessages}
          signedInUser={signedInUser}
          siteLocale={siteLocale}
        />
      ) : null}
      {activeRoute === "contacts" ? (
        <ContactsScreen
          contactRequests={shelterContactRequests}
          profile={profile}
          recipients={recipients}
          setContactRequests={setShelterContactRequests}
          setRecipients={setRecipients}
          siteLocale={siteLocale}
        />
      ) : null}
      {activeRoute === "uploads" ? (
        <UploadsScreen
          apiBaseUrl={walletApiBaseUrl}
          apiConfig={walletApiConfig}
          bundles={exportBundleViews}
          proofs={walletProofReceipts}
          recipients={recipients}
          refreshWalletAuditEvents={refreshWalletAuditEvents}
          setApiConfig={persistWalletApiConfig}
          setBundles={setExportBundleViews}
          setUploads={setUploads}
          signedInUser={signedInUser}
          siteLocale={siteLocale}
          uploads={uploads}
        />
      ) : null}
      {servicePlanDocId ? (
        <ServicePlanScreen
          apiConfig={walletApiConfig}
          docId={servicePlanDocId}
          grantReceipts={grantReceipts}
          onBack={() => navigate("social-services")}
          onOpenDetail={onOpenService}
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
        <ServiceDetailScreen
          apiConfig={walletApiConfig}
          docId={serviceDetailDocId}
          onBack={() => navigate("social-services")}
          onInteract={(event) => setServiceInteractions((prev) => [event, ...prev])}
          siteLocale={siteLocale}
        />
      ) : null}
      {activeRoute === "social-services" && !serviceDetailDocId && !servicePlanDocId ? (
        <SocialServicesScreen
          apiConfig={walletApiConfig}
          onOpenDetail={onOpenService}
          onOpenPlan={onOpenPlan}
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
          onOpenPlan={onOpenPlan}
          onOpenService={onOpenService}
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
          contactRequests={shelterContactRequests}
          navigate={navigate}
          profile={profile}
          proofReceipts={walletProofReceipts}
          providerMessages={shelterProviderMessages}
          recipients={recipients}
          setChecklist={setShelterChecklist}
          setContactRequests={setShelterContactRequests}
          setProofReceipts={setWalletProofReceipts}
          setProviderMessages={setShelterProviderMessages}
          setRecipients={setRecipients}
          setShelterCaseRecords={setShelterCaseRecords}
          setShelterStaffAccounts={setShelterStaffAccounts}
          setShelterUserAccounts={setShelterUserAccounts}
          shelterCaseRecords={shelterCaseRecords}
          shelterStaffAccounts={shelterStaffAccounts}
          shelterUserAccounts={shelterUserAccounts}
          siteLocale={siteLocale}
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
      {activeRoute === "exports" ? (
        <ExportCenterScreen
          apiConfig={walletApiConfig}
          bundles={exportBundleViews}
          setBundles={setExportBundleViews}
        />
      ) : null}
    </>
  );
}
