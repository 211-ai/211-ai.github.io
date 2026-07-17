import { useState } from "react";
import { Bell, CalendarCheck } from "lucide-react";
import { Button, Field, Section, StatusBanner } from "../../../components/ui";
import type { CheckInChannel, RegistrationProfileDraft } from "../../../models/abby";
import { defaultCheckInPolicy } from "../../../app/appState";
import { t, tFormat, type SupportedLocale } from "../../../shared/lib/localization";
import { formatCheckInChannel } from "../../../app/utils/formatHelpers";

export function CheckInScreen({
  policy,
  profile,
  setPolicy,
  nextCheckIn,
  siteLocale
}: {
  policy: typeof defaultCheckInPolicy;
  profile: RegistrationProfileDraft;
  setPolicy: (policy: typeof defaultCheckInPolicy) => void;
  nextCheckIn: string;
  siteLocale: SupportedLocale;
}) {
  const [checkInMessage, setCheckInMessage] = useState<{ tone: "success" | "warning"; text: string } | null>(null);
  const update = (patch: Partial<typeof defaultCheckInPolicy>) => setPolicy({ ...policy, ...patch });
  const channelLabels: Record<CheckInChannel, string> = {
    sms: tFormat(siteLocale, "checkin.channelAllowed", { channel: formatCheckInChannel("sms", siteLocale) }),
    email: tFormat(siteLocale, "checkin.channelAllowed", { channel: formatCheckInChannel("email", siteLocale) }),
    web: tFormat(siteLocale, "checkin.channelAllowed", { channel: formatCheckInChannel("web", siteLocale) })
  };
  const checkInMethodLabels: Record<CheckInChannel, string> = {
    sms: t(siteLocale, "checkin.methodText"),
    email: t(siteLocale, "checkin.methodEmail"),
    web: t(siteLocale, "checkin.methodWeb")
  };
  const channelIsAllowed = (channel: CheckInChannel) => policy.reminderChannels.includes(channel);
  const toggleChannel = (channel: CheckInChannel) => {
    update({
      reminderChannels: policy.reminderChannels.includes(channel)
        ? policy.reminderChannels.filter((item: CheckInChannel) => item !== channel)
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
            ? t(siteLocale, "checkin.webOff")
            : tFormat(siteLocale, "checkin.channelOff", { channel: formatCheckInChannel(channel, siteLocale) })
      });
      return;
    }

    if (channel === "sms" && !profile.phone.trim()) {
      setCheckInMessage({ tone: "warning", text: t(siteLocale, "checkin.addPhone") });
      return;
    }

    if (channel === "email" && !profile.email.trim()) {
      setCheckInMessage({ tone: "warning", text: t(siteLocale, "checkin.addEmail") });
      return;
    }

    update({ lastCheckInAt: new Date().toISOString() });
    setCheckInMessage({
      tone: "success",
      text: tFormat(siteLocale, "checkin.success", { method: checkInMethodLabels[channel] })
    });
  }

  return (
    <div className="screen">
      <div className="page-title">
        <p className="eyebrow">{t(siteLocale, "checkin.eyebrow")}</p>
        <h1>{t(siteLocale, "checkin.title")}</h1>
      </div>
      <StatusBanner tone="warning">{t(siteLocale, "checkin.warning")}</StatusBanner>
      <Section title={t(siteLocale, "checkin.schedule")}>
        <div className="form-grid">
          <Field help={t(siteLocale, "settings.daysBetweenHelp")} label={t(siteLocale, "settings.daysBetween")} required>
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
          <Field help={t(siteLocale, "settings.extraHoursHelp")} label={t(siteLocale, "settings.extraHours")}>
            <input
              min={0}
              type="number"
              value={policy.gracePeriodHours}
              onChange={(event) => update({ gracePeriodHours: Number(event.target.value || 0) })}
            />
          </Field>
        </div>
        <p className="supporting-copy">{t(siteLocale, "checkin.methodsHelp")}</p>
        <div className="channel-controls" role="group" aria-label={t(siteLocale, "checkin.allowedMethods")}>
          {(["sms", "email", "web"] as CheckInChannel[]).map((channel) => (
            <button
              aria-pressed={policy.reminderChannels.includes(channel)}
              className="choice-chip channel-toggle"
              key={channel}
              onClick={() => toggleChannel(channel)}
              type="button"
            >
              <span>{channelLabels[channel]}</span>
              <small>{channelIsAllowed(channel) ? t(siteLocale, "settings.on") : t(siteLocale, "settings.off")}</small>
            </button>
          ))}
        </div>
        {!policy.reminderChannels.length ? (
          <StatusBanner tone="warning">{t(siteLocale, "checkin.noneEnabled")}</StatusBanner>
        ) : null}
        <div className="schedule-preview">
          <CalendarCheck aria-hidden="true" size={28} />
          <div>
            <small>{t(siteLocale, "home.nextCheckIn")}</small>
            <strong>{nextCheckIn}</strong>
          </div>
        </div>
        {checkInMessage ? <StatusBanner tone={checkInMessage.tone}>{checkInMessage.text}</StatusBanner> : null}
        <div className="method-checkin-grid" role="group" aria-label={t(siteLocale, "checkin.checkInNow")}>
          {(["sms", "email", "web"] as CheckInChannel[]).map((channel) => {
            const allowed = channelIsAllowed(channel);
            return (
              <Button key={channel} onClick={() => checkInBy(channel)} variant={allowed ? "primary" : "secondary"}>
                <Bell size={18} /> {tFormat(siteLocale, "checkin.byMethod", { method: checkInMethodLabels[channel] })}{allowed ? "" : ` ${t(siteLocale, "checkin.offSuffix")}`}
              </Button>
            );
          })}
        </div>
      </Section>
    </div>
  );
}
