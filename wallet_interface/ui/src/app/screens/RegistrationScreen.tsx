import { t, type SupportedLocale } from "../../lib/localization";
import type { RegistrationProfileDraft } from "../../models/abby";
import type { WalletApiConfig } from "../../services/walletApi";
import { GovernmentHelpSection } from "../components/GovernmentHelpSection";
import { ProfileInformationForm, togglePartnerHelpRequest } from "../components/ProfileInformationForm";
import { WorldIdSurfaceStatus } from "../components/WorldIdSurfaceStatus";

export function RegistrationScreen({
  apiConfig,
  onWorldIdAuditRefresh,
  profile,
  siteLocale,
  setProfile
}: {
  apiConfig?: WalletApiConfig;
  onWorldIdAuditRefresh?: () => Promise<void> | void;
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
      <WorldIdSurfaceStatus
        apiConfig={apiConfig}
        ariaLabel="Register World ID status"
        onAuditRefresh={onWorldIdAuditRefresh}
      />
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
