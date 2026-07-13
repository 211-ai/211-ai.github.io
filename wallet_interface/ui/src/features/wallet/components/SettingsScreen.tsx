import { useEffect, useState } from "react";
import { Bell, ClipboardCheck, ShieldCheck } from "lucide-react";
import { Button, Field, Section, StatusBanner } from "../../../components/ui";
import type { CheckInChannel, RegistrationProfileDraft, RouteId } from "../../../models/abby";
import type { WalletApiConfig } from "../../../services/walletApi";
import {
  SUPPORTED_LOCALES,
  TRANSLATION_LOCALE_OPTIONS,
  getLocaleOptionLabel,
  normalizeSiteLocale,
  t,
  tFormat,
  type SupportedLocale
} from "../../../lib/localization";
import { analyticsStudies } from "../../../services/mockAbbyService";
import { defaultCheckInPolicy } from "../../../app/appState";
import { AccountSafetySection } from "../../../app/components/AccountSafetySection";
import { GovernmentHelpSection } from "../../../app/components/GovernmentHelpSection";
import { ProfileInformationForm, togglePartnerHelpRequest } from "../../../app/components/ProfileInformationForm";
import { StatusPanel } from "../../../app/components/StatusPanel";
import { WorldIdSurfaceStatus } from "../../../app/components/WorldIdSurfaceStatus";
import { PORTLAND_POLICE_MISSING_EMAIL, formatCheckInChannel } from "../../../app/utils/formatHelpers";

export function SettingsScreen({
  apiConfig,
  assistantAutoTranslate,
  assistantTranslationLocale,
  analyticsOptIn,
  benefitsOptIn,
  browserLocale,
  missingPersonDeadDropEnabled,
  navigate,
  nextCheckIn,
  onWorldIdAuditRefresh,
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
  onWorldIdAuditRefresh?: () => Promise<void> | void;
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

      <WorldIdSurfaceStatus
        apiConfig={apiConfig}
        ariaLabel="Security World ID status"
        onAuditRefresh={onWorldIdAuditRefresh}
      />

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
