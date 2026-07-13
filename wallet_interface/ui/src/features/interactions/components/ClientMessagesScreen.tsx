import { useState } from "react";
import { Badge, Button, Field, Section } from "../../../components/ui";
import type { RegistrationProfileDraft } from "../../../models/abby";
import type { ShelterProviderMessage } from "../../../app/appState";
import { StatusPanel } from "../../../app/components/StatusPanel";
import { t, tFormat, type SupportedLocale } from "../../../lib/localization";
import { formatProviderMessageChannel, messageMatchesClient } from "../../../app/utils/formatHelpers";
import { formatShelterDate } from "../../../app/utils/providerHelpers";

export function ClientMessagesScreen({
  profile,
  providerMessages,
  setProviderMessages,
  siteLocale,
  signedInUser
}: {
  profile: RegistrationProfileDraft;
  providerMessages: ShelterProviderMessage[];
  setProviderMessages: (messages: ShelterProviderMessage[]) => void;
  siteLocale: SupportedLocale;
  signedInUser: string;
}) {
  const [messageFilter, setMessageFilter] = useState<"inbox" | "unread" | "archived" | "all">("inbox");
  const clientMessages = providerMessages
    .filter((message) => messageMatchesClient(message, profile, signedInUser))
    .sort((left, right) => new Date(right.createdAt).getTime() - new Date(left.createdAt).getTime());
  const inboxMessages = clientMessages.filter((message) => !message.clientArchivedAt);
  const unreadMessages = inboxMessages.filter((message) => !message.clientReadAt);
  const archivedMessages = clientMessages.filter((message) => message.clientArchivedAt);
  const visibleMessages =
    messageFilter === "unread"
      ? unreadMessages
      : messageFilter === "archived"
        ? archivedMessages
        : messageFilter === "all"
          ? clientMessages
          : inboxMessages;

  function updateMessage(messageId: string, patch: Partial<ShelterProviderMessage>) {
    setProviderMessages(
      providerMessages.map((message) => (message.id === messageId ? { ...message, ...patch } : message))
    );
  }

  function markMessageRead(message: ShelterProviderMessage) {
    updateMessage(message.id, { clientReadAt: message.clientReadAt ? undefined : new Date().toISOString() });
  }

  function toggleMessageArchive(message: ShelterProviderMessage) {
    updateMessage(message.id, {
      clientArchivedAt: message.clientArchivedAt ? undefined : new Date().toISOString(),
      clientReadAt: message.clientReadAt ?? new Date().toISOString()
    });
  }

  return (
    <div className="screen client-messages-screen">
      <div className="page-title">
        <p className="eyebrow">{t(siteLocale, "portal.client")}</p>
        <h1>{t(siteLocale, "messages.title")}</h1>
      </div>
      <p className="page-note">{t(siteLocale, "messages.note")}</p>
      <Section title={t(siteLocale, "messages.summary")}>
        <div className="dashboard-grid">
          <StatusPanel label={t(siteLocale, "messages.inbox")} value={String(inboxMessages.length)} tone="teal" />
          <StatusPanel label={t(siteLocale, "messages.unread")} value={String(unreadMessages.length)} tone="gold" />
          <StatusPanel label={t(siteLocale, "messages.archived")} value={String(archivedMessages.length)} tone="teal" />
        </div>
      </Section>
      <Section title={t(siteLocale, "messages.staffMessages")}>
        <div className="message-toolbar">
          <Field label={t(siteLocale, "messages.view")}>
            <select value={messageFilter} onChange={(event) => setMessageFilter(event.target.value as typeof messageFilter)}>
              <option value="inbox">{t(siteLocale, "messages.inbox")}</option>
              <option value="unread">{t(siteLocale, "messages.unread")}</option>
              <option value="archived">{t(siteLocale, "messages.archived")}</option>
              <option value="all">{t(siteLocale, "messages.all")}</option>
            </select>
          </Field>
        </div>
        <div className="list-stack client-message-list">
          {visibleMessages.length ? (
            visibleMessages.map((message) => (
              <article className="list-item client-message-item" key={message.id}>
                <div>
                  <h3>{message.subject}</h3>
                  <p>{message.body}</p>
                  <div className="badge-row">
                    <Badge>{message.shelter}</Badge>
                    <Badge>{message.staffName}</Badge>
                    <Badge>{formatProviderMessageChannel(message.channel, siteLocale)}</Badge>
                    <Badge tone={message.clientReadAt ? "neutral" : "warning"}>
                      {message.clientReadAt ? t(siteLocale, "messages.read") : t(siteLocale, "messages.unread")}
                    </Badge>
                    <Badge>{formatShelterDate(message.createdAt)}</Badge>
                  </div>
                  <small>{tFormat(siteLocale, "messages.sentTo", { contact: message.clientContact })}</small>
                </div>
                <div className="row-actions">
                  <Button onClick={() => markMessageRead(message)} variant="secondary">
                    {message.clientReadAt ? t(siteLocale, "messages.markUnread") : t(siteLocale, "messages.markRead")}
                  </Button>
                  <Button onClick={() => toggleMessageArchive(message)} variant="secondary">
                    {message.clientArchivedAt ? t(siteLocale, "messages.restore") : t(siteLocale, "messages.archive")}
                  </Button>
                </div>
              </article>
            ))
          ) : (
            <div className="empty-state">
              <h3>{t(siteLocale, "messages.emptyTitle")}</h3>
              <p>{t(siteLocale, "messages.emptyBody")}</p>
            </div>
          )}
        </div>
      </Section>
    </div>
  );
}
