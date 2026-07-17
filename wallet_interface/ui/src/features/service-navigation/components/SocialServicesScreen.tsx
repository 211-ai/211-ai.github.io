import { FormEvent, useEffect, useState } from "react";
import { CalendarClock, HeartHandshake, Save } from "lucide-react";
import { Badge, Button, Field, Section, StatusBanner } from "../../../components/ui";
import type { SavedService, ServicePlan } from "../../../models/abby";
import {
  getPrimaryIntakeText,
  getServiceLocationLabel,
  load211GeneratedManifest,
  load211ServiceLocationsSlice,
  resolvePreferred211ServiceClusterIds,
  type SearchResult
} from "../graphrag";
import { t, tFormat, type SupportedLocale } from "../../../shared/lib/localization";
import { SavedServicesPanel } from "../../../shared/components/SavedServicesPanel";
import { ServiceQuickActions } from "../../../shared/components/ServiceQuickActions";
import { HmisLookupPanel } from "../../../components/hmis/HmisLookupPanel";
import { HmisMatchReviewDrawer } from "../../../components/hmis/HmisMatchReviewDrawer";
import { HmisReferralDraftPanel } from "../../../components/hmis/HmisReferralDraftPanel";
import { HmisReconciliationQueue } from "../../../components/hmis/HmisReconciliationQueue";
import { HmisSyncTimeline } from "../../../components/hmis/HmisSyncTimeline";
import { search211Info } from "../../../services/graphRagService";
import { serviceMatches } from "../../../services/mockAbbyService";
import { saveWalletService, type WalletApiConfig } from "../../../services/walletApi";
import {
  buildSearchResultLocationLabels,
  formatCount,
  toLocalSavedService,
  toSaveWalletServiceInput
} from "../../../app/utils/serviceHelpers";

export function SocialServicesScreen({
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
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [resultLocationLabels, setResultLocationLabels] = useState<Record<string, string>>({});
  const [searchStatus, setSearchStatus] = useState<"idle" | "loading" | "complete" | "error">("idle");
  const [searchError, setSearchError] = useState("");
  const [savingDocIds, setSavingDocIds] = useState<string[]>([]);
  const [saveError, setSaveError] = useState("");
  const [selectedHmisCandidates, setSelectedHmisCandidates] = useState<Array<Record<string, unknown>>>([]);
  const [hmisDrawerOpen, setHmisDrawerOpen] = useState(false);
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
      const [searchResults, preferredClusterIds] = await Promise.all([
        search211Info(trimmedQuery, 18),
        resolvePreferred211ServiceClusterIds(trimmedQuery, 8).catch(() => []),
      ]);
      const visibleResults = searchResults.slice(0, 12);
      const locationRows = visibleResults.length
        ? await load211ServiceLocationsSlice({
            serviceDocIds: visibleResults.map((result) => result.docId),
          }).catch(() => [])
        : [];
      setResults(visibleResults);
      setResultLocationLabels(buildSearchResultLocationLabels(visibleResults, locationRows, preferredClusterIds));
      setSearchStatus("complete");
    } catch (error) {
      setResults([]);
      setResultLocationLabels({});
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
        <p className="eyebrow">{t(siteLocale, "services.eyebrow")}</p>
        <h1>{t(siteLocale, "services.title")}</h1>
        {catalogCounts.serviceCount > 0 ? (
          <p className="supporting-copy">
            {tFormat(siteLocale, "services.indexedSummary", {
              serviceCount: formatCount(catalogCounts.serviceCount),
              phoneCount: formatCount(catalogCounts.phoneCount),
              addressCount: formatCount(catalogCounts.addressCount),
              intakeCount: formatCount(catalogCounts.intakeCount),
            })}
          </p>
        ) : null}
      </div>
      <Section title={catalogCounts.serviceCount > 0 ? tFormat(siteLocale, "services.searchIndexedTitle", { count: formatCount(catalogCounts.serviceCount) }) : t(siteLocale, "services.searchIndexTitle")}>
        <form className="form-grid" onSubmit={handleSearchSubmit}>
          <Field label={t(siteLocale, "services.searchLabel")}>
            <input
              placeholder={t(siteLocale, "services.searchPlaceholder")}
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
          </Field>
          <div className="row-actions">
            <Button disabled={!query.trim()} loading={searchStatus === "loading"} loadingLabel={t(siteLocale, "services.searching")} type="submit">
              {t(siteLocale, "services.searchButton")}
            </Button>
          </div>
        </form>
        <div className="chip-grid" aria-label={t(siteLocale, "services.suggestedSearches")}>
          {suggestedPrompts.map((prompt) => (
            <button className="choice-chip" key={prompt.query} onClick={() => void runSearch(prompt.query)} type="button">
              {prompt.label}
            </button>
          ))}
        </div>
        {searchStatus === "error" ? (
          <StatusBanner tone="warning">{tFormat(siteLocale, "services.searchUnavailable", { error: searchError })}</StatusBanner>
        ) : null}
        {saveError ? <StatusBanner tone="warning">{saveError}</StatusBanner> : null}
        {searchStatus === "complete" && results.length === 0 ? (
          <StatusBanner tone="info">{t(siteLocale, "services.noMatches")}</StatusBanner>
        ) : null}
        {results.length ? (
          <div className="list-stack" aria-label={t(siteLocale, "services.resultsAria")}>
            {results.map((result) => {
              const document = result.document;
              const provider = document.provider_name || t(siteLocale, "services.providerNotListed");
              const program = document.program_name || document.title || t(siteLocale, "services.programNotListed");
              const location = resultLocationLabels[result.docId] || getServiceLocationLabel(document);
              const intake = getPrimaryIntakeText(document);
              return (
                <article className="list-item" key={result.docId}>
                  <div>
                    <h3>{program}</h3>
                    <p>{provider}</p>
                    <small className="upload-machine-summary">{result.snippet}</small>
                    {intake ? <small className="upload-machine-summary">{t(siteLocale, "services.applyPrefix")}: {intake}</small> : null}
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
                    <ServiceQuickActions document={document} siteLocale={siteLocale} />
                    <Button
                      disabled={savedServices.some((service) => service.service_doc_id === result.docId)}
                      loading={savingDocIds.includes(result.docId)}
                      loadingLabel={t(siteLocale, "services.saving")}
                      onClick={() => void saveResult(result)}
                      variant="secondary"
                    >
                      <Save aria-hidden="true" size={18} />
                      {savedServices.some((service) => service.service_doc_id === result.docId) ? t(siteLocale, "services.saved") : t(siteLocale, "services.save")}
                    </Button>
                    <Button onClick={() => onOpenPlan(result.docId)} variant="secondary">
                      <CalendarClock aria-hidden="true" size={18} />
                      {t(siteLocale, "services.plan")}
                    </Button>
                    <Button onClick={() => onOpenDetail(result.docId)} variant="secondary">
                      {t(siteLocale, "services.openDetail")}
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
        siteLocale={siteLocale}
        servicePlans={servicePlans}
      />
      {apiConfig?.walletId && apiConfig?.actorDid ? (
        <>
          <HmisLookupPanel
            apiConfig={apiConfig}
            onSelectCandidate={(candidate) => {
              setSelectedHmisCandidates([candidate]);
              setHmisDrawerOpen(true);
            }}
          />
          <HmisReferralDraftPanel
            apiConfig={apiConfig}
            destinationProgramRef="shelter-a"
            localSubjectRef={`wallet:${apiConfig.walletId}`}
          />
          <HmisSyncTimeline apiConfig={apiConfig} />
          <HmisReconciliationQueue apiConfig={apiConfig} />
          <HmisMatchReviewDrawer
            apiConfig={apiConfig}
            candidates={selectedHmisCandidates}
            entityType="client"
            localRef={`wallet:${apiConfig.walletId}`}
            onClose={() => setHmisDrawerOpen(false)}
            open={hmisDrawerOpen}
          />
        </>
      ) : null}
      <div className="category-grid">
        {categories.map((category) => (
          <button className="category-tile" key={category.query} onClick={() => void runSearch(category.query)} type="button">
            <HeartHandshake aria-hidden="true" size={22} />
            <span>{category.label}</span>
          </button>
        ))}
      </div>
      <Section title={t(siteLocale, "services.matchedServices")}>
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
