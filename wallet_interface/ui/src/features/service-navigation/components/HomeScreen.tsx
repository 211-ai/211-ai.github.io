import { useEffect, useMemo, useState } from "react";
import { ActionCard, Badge, Button, Section, StatusBanner } from "../../../components/ui";
import { CalendarCheck, ContactRound, HeartHandshake, ShieldCheck } from "lucide-react";
import type {
  CheckInPolicyDraft,
  DisclosureRecipientDraft,
  RegistrationProfileDraft,
  RouteId,
  ServiceInteractionEvent,
  ServicePlan,
  UploadItem
} from "../../../models/abby";
import type { ShelterProviderMessage } from "../../../app/appState";
import { t, translateServiceNeed, type SupportedLocale } from "../../../lib/localization";
import { search211Info } from "../../../services/graphRagService";
import {
  getServiceLocationLabel,
  load211ServiceLocationsSlice,
  resolvePreferred211ServiceClusterIds,
  type SearchResult
} from "../../../lib/graphrag";
import { formatShelterDate } from "../../../app/utils/providerHelpers";
import {
  buildHomeCalendarItems,
  buildSearchResultLocationLabels,
  formatHomeDateTime,
  type HomeServiceSuggestion
} from "../../../app/utils/serviceHelpers";
import { messageMatchesClient } from "../../../app/utils/formatHelpers";

export function HomeScreen({
  navigate,
  nextCheckIn,
  onOpenService,
  policy,
  profile,
  providerMessages,
  recipients,
  siteLocale,
  serviceInteractions,
  servicePlans,
  showReviewActions,
  signedInUser,
  uploads
}: {
  navigate: (route: RouteId) => void;
  nextCheckIn: string;
  onOpenService: (docId: string) => void;
  policy: CheckInPolicyDraft;
  profile: RegistrationProfileDraft;
  providerMessages: ShelterProviderMessage[];
  recipients: DisclosureRecipientDraft[];
  siteLocale: SupportedLocale;
  serviceInteractions: ServiceInteractionEvent[];
  servicePlans: ServicePlan[];
  showReviewActions: boolean;
  signedInUser: string;
  uploads: UploadItem[];
}) {
  const [homeSuggestions, setHomeSuggestions] = useState<HomeServiceSuggestion[]>([]);
  const [homeSuggestionsLoading, setHomeSuggestionsLoading] = useState(false);
  const selectedNeeds = useMemo(
    () => Array.from(new Set(profile.serviceNeeds.map((value) => value.trim()).filter(Boolean))).slice(0, 3),
    [profile.serviceNeeds]
  );
  const selectedNeedLabels = useMemo(() => selectedNeeds.map((need) => translateServiceNeed(siteLocale, need)), [selectedNeeds, siteLocale]);
  const inboxMessages = useMemo(
    () =>
      providerMessages
        .filter((message) => messageMatchesClient(message, profile, signedInUser))
        .filter((message) => !message.clientArchivedAt)
        .sort((left, right) => new Date(right.createdAt).getTime() - new Date(left.createdAt).getTime()),
    [profile, providerMessages, signedInUser]
  );
  const featuredMessages = useMemo(() => {
    const unread = inboxMessages.filter((message) => !message.clientReadAt);
    return (unread.length ? unread : inboxMessages).slice(0, 3);
  }, [inboxMessages]);
  const urgentCalendarItems = useMemo(
    () => buildHomeCalendarItems({ policy, serviceInteractions, servicePlans }).slice(0, 3),
    [policy, serviceInteractions, servicePlans]
  );

  useEffect(() => {
    let canceled = false;

    async function loadHomeSuggestions() {
      if (!selectedNeeds.length) {
        setHomeSuggestions([]);
        return;
      }

      setHomeSuggestionsLoading(true);
      try {
        const searchBundles = await Promise.all(
          selectedNeeds.map(async (need) => {
            const query = `${need} near me`;
            const [results, preferredClusterIds] = await Promise.all([
              search211Info(query, 3).catch(() => []),
              resolvePreferred211ServiceClusterIds(query, 8).catch(() => [])
            ]);
            return {
              need,
              results: results.slice(0, 2),
              preferredClusterIds
            };
          })
        );

        const uniqueResults: Array<{ need: string; result: SearchResult }> = [];
        const seenDocIds = new Set<string>();
        const allPreferredClusterIds = new Set<number>();
        for (const bundle of searchBundles) {
          for (const clusterId of bundle.preferredClusterIds) {
            allPreferredClusterIds.add(clusterId);
          }
          for (const result of bundle.results) {
            if (seenDocIds.has(result.docId)) continue;
            seenDocIds.add(result.docId);
            uniqueResults.push({ need: bundle.need, result });
          }
        }

        const visibleResults = uniqueResults.slice(0, 4);
        const locationRows = visibleResults.length
          ? await load211ServiceLocationsSlice({
              serviceDocIds: visibleResults.map((entry) => entry.result.docId)
            }).catch(() => [])
          : [];
        const locationLabels = buildSearchResultLocationLabels(
          visibleResults.map((entry) => entry.result),
          locationRows,
          Array.from(allPreferredClusterIds)
        );

        if (canceled) return;
        setHomeSuggestions(
          visibleResults.map(({ need, result }) => ({
            need,
            result,
            locationLabel: locationLabels[result.docId] || getServiceLocationLabel(result.document)
          }))
        );
      } finally {
        if (!canceled) {
          setHomeSuggestionsLoading(false);
        }
      }
    }

    void loadHomeSuggestions();
    return () => {
      canceled = true;
    };
  }, [selectedNeeds]);

  return (
    <div className="screen home-screen">
      <div className="page-title home-hero">
        <p className="eyebrow">{t(siteLocale, "home.today")}</p>
        <h1>{t(siteLocale, "home.welcome")}</h1>
      </div>
      <Section title={t(siteLocale, "home.quickActions")}>
        <div className="quick-actions">
          <button className="checkin-panel" onClick={() => navigate("check-in")} type="button">
            <div className="checkin-panel-icon">
              <CalendarCheck size={24} aria-hidden="true" />
            </div>
            <div className="checkin-panel-text">
              <span className="checkin-panel-label">{t(siteLocale, "home.nextCheckIn")}</span>
              <span className="checkin-panel-value">{nextCheckIn}</span>
            </div>
            <span className="checkin-panel-cta">{t(siteLocale, "home.checkInNow")}</span>
          </button>
        </div>
      </Section>
      <Section title={t(siteLocale, "home.closestHelp")}>
        {selectedNeeds.length ? (
          homeSuggestionsLoading ? (
            <StatusBanner tone="info">{t(siteLocale, "home.findingNearby")} {selectedNeedLabels.join(", ")}.</StatusBanner>
          ) : homeSuggestions.length ? (
            <div className="list-stack" aria-label="Nearby services for selected needs">
              {homeSuggestions.map(({ need, result, locationLabel }) => {
                const document = result.document;
                const program = document.program_name || document.title || "Program not listed";
                const provider = document.provider_name || "Provider not listed";
                return (
                  <article className="list-item" key={`${need}:${result.docId}`}>
                    <div>
                      <h3>{program}</h3>
                      <p>{provider}</p>
                      <small className="upload-machine-summary">{result.snippet}</small>
                      <div className="badge-row">
                        <Badge>{translateServiceNeed(siteLocale, need)}</Badge>
                        {locationLabel ? <Badge>{locationLabel}</Badge> : null}
                      </div>
                    </div>
                    <div className="row-actions list-item-action">
                      <Button onClick={() => onOpenService(result.docId)} variant="secondary">
                        {t(siteLocale, "action.openService")}
                      </Button>
                    </div>
                  </article>
                );
              })}
            </div>
          ) : (
            <StatusBanner tone="info">{t(siteLocale, "home.noNearbyMatches")}</StatusBanner>
          )
        ) : (
          <div className="empty-state">
            <h3>{t(siteLocale, "home.noCategories")}</h3>
            <p>{t(siteLocale, "home.addHelpSettings")}</p>
            <div className="row-actions">
              <Button onClick={() => navigate("settings")} variant="secondary">{t(siteLocale, "home.updateSettings")}</Button>
            </div>
          </div>
        )}
      </Section>
      <Section title={t(siteLocale, "home.newMessages")}>
        {featuredMessages.length ? (
          <div className="list-stack" aria-label={t(siteLocale, "home.newMessagesAria")}>
            {featuredMessages.map((message) => (
              <article className="list-item" key={message.id}>
                <div>
                  <h3>{message.subject}</h3>
                  <p>{message.body}</p>
                  <div className="badge-row">
                    <Badge>{message.shelter}</Badge>
                    <Badge tone={message.clientReadAt ? "neutral" : "warning"}>
                      {message.clientReadAt ? t(siteLocale, "home.read") : t(siteLocale, "home.unread")}
                    </Badge>
                    <Badge>{formatShelterDate(message.createdAt)}</Badge>
                  </div>
                  <small>{t(siteLocale, "home.from")} {message.staffName}</small>
                </div>
                <div className="row-actions list-item-action">
                  <Button onClick={() => navigate("messages")} variant="secondary">
                    {t(siteLocale, "home.openMessages")}
                  </Button>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <StatusBanner tone="info">{t(siteLocale, "home.noMessages")}</StatusBanner>
        )}
      </Section>
      <Section title={t(siteLocale, "home.urgentItems")}>
        {urgentCalendarItems.length ? (
          <div className="list-stack" aria-label={t(siteLocale, "home.urgentItemsAria")}>
            {urgentCalendarItems.map((item) => {
              const serviceDocId = item.serviceDocId;
              return (
                <article className="list-item" key={item.id}>
                  <div>
                    <h3>{item.title}</h3>
                    <p>{item.detail}</p>
                    <div className="badge-row">
                      <Badge>{item.kindLabel}</Badge>
                      <Badge tone={item.urgencyTone}>{item.urgencyLabel}</Badge>
                      {item.location ? <Badge>{item.location}</Badge> : null}
                    </div>
                    <small>{formatHomeDateTime(item.startsAt)}</small>
                  </div>
                  <div className="row-actions list-item-action">
                    <Button onClick={() => navigate("calendar")} variant="secondary">
                      {t(siteLocale, "home.openCalendar")}
                    </Button>
                    {serviceDocId ? (
                      <Button onClick={() => onOpenService(serviceDocId)} variant="secondary">
                        {t(siteLocale, "action.openService")}
                      </Button>
                    ) : null}
                  </div>
                </article>
              );
            })}
          </div>
        ) : (
          <StatusBanner tone="info">{t(siteLocale, "home.noUrgentItems")}</StatusBanner>
        )}
      </Section>
      {showReviewActions ? (
        <div className="home-actions" aria-label={t(siteLocale, "home.safetyPlanSetup")}>
          <ActionCard
            detail={`${recipients.length} ${t(siteLocale, "home.contactsDetail")}`}
            icon={<ContactRound aria-hidden="true" size={28} />}
            onClick={() => navigate("contacts")}
            title={t(siteLocale, "home.contacts")}
          />
          <ActionCard
            detail={t(siteLocale, "home.sharingDetail")}
            icon={<ShieldCheck aria-hidden="true" size={28} />}
            onClick={() => navigate("contacts")}
            title={t(siteLocale, "home.sharing")}
          />
        </div>
      ) : null}
      <div className="home-footer">
        <div className="home-footer-stat">
          <small>{t(siteLocale, "home.savedFiles")}</small>
          <span>{uploads.length} {uploads.length !== 1 ? t(siteLocale, "home.filePlural") : t(siteLocale, "home.fileSingular")}</span>
        </div>
        <div className="home-footer-divider" />
        <div className="home-footer-stat">
          <small>{t(siteLocale, "home.contactSharing")}</small>
          <span>{t(siteLocale, "home.reviewReady")}</span>
        </div>
        <div className="home-footer-divider" />
        <div className="home-footer-stat">
          <small>{t(siteLocale, "home.legal")}</small>
          <div className="home-footer-links">
            <a className="home-footer-link" href="/terms.html">
              {t(siteLocale, "home.terms")}
            </a>
            <a className="home-footer-link" href="/privacy.html">
              {t(siteLocale, "home.privacy")}
            </a>
          </div>
        </div>
      </div>
      <section className="support-card" aria-labelledby="support-card-title">
        <span className="support-card-badge" aria-hidden="true" />
        <div className="support-card-content">
          <h2 id="support-card-title">{t(siteLocale, "home.needHelpToday")}</h2>
          <p>{t(siteLocale, "home.supportDescription")}</p>
          <Button onClick={() => navigate("social-services")}>
            <HeartHandshake aria-hidden="true" size={18} /> {t(siteLocale, "home.findHelp")}
          </Button>
        </div>
      </section>
    </div>
  );
}
