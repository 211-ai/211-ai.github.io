import { useEffect, useState } from "react";
import { ArrowLeft } from "lucide-react";
import { ServiceQuickActions } from "../components/services/ServiceQuickActions";
import { ServiceProvenancePanel } from "../components/services/ServiceProvenancePanel";
import { Badge, Button, Section, StatusBanner } from "../components/ui";
import {
  getPrimaryEligibilityText,
  getPrimaryIntakeText,
  getPrimaryRequiredDocumentsText,
  getServiceAddresses,
  getServiceAreaServedText,
  getServiceLocationLabel,
  getServicePhones,
  getServiceTravelInfoText,
  load211ArtifactManifest,
  load211Documents,
  load211GeneratedManifest,
  load211ServiceLocationsSlice,
  type CorpusDocument,
  type ServiceLocationRecord,
} from "../lib/graphrag";
import { build211InfoServiceProvenance } from "../services/graphRagService";

type ServiceDetailMetadata = {
  buildManifestCid: string;
  documentsArtifactCid: string;
  documentCount: number;
  loadedAt: string;
};

type ServiceDetailState =
  | { status: "loading"; document: null; metadata: null; locations: ServiceLocationRecord[]; error: "" }
  | { status: "ready"; document: CorpusDocument; metadata: ServiceDetailMetadata; locations: ServiceLocationRecord[]; error: "" }
  | { status: "not-found"; document: null; metadata: ServiceDetailMetadata | null; locations: ServiceLocationRecord[]; error: "" }
  | { status: "error"; document: null; metadata: null; locations: ServiceLocationRecord[]; error: string };

export function ServiceDetailScreen({ docId, onBack }: { docId: string; onBack: () => void }) {
  const [state, setState] = useState<ServiceDetailState>({
    status: "loading",
    document: null,
    metadata: null,
    locations: [],
    error: "",
  });

  useEffect(() => {
    let canceled = false;

    async function loadServiceDetail() {
      setState({ status: "loading", document: null, metadata: null, locations: [], error: "" });
      try {
        const documentsState = await load211Documents();
        const [artifactManifestResult, generatedManifestResult] = await Promise.allSettled([
          load211ArtifactManifest(),
          load211GeneratedManifest(),
        ]);
        if (canceled) return;

        const artifactManifest =
          artifactManifestResult.status === "fulfilled" ? artifactManifestResult.value : null;
        const generatedManifest =
          generatedManifestResult.status === "fulfilled" ? generatedManifestResult.value : null;
        const document =
          documentsState.documentById.get(docId) ??
          documentsState.documentByContentCid.get(docId) ??
          documentsState.documents.find((item) => item.source_page_cid === docId) ??
          null;
        const locations = document
          ? await load211ServiceLocationsSlice({ serviceDocIds: [document.doc_id] }).catch(() => [])
          : [];
        if (canceled) return;
        const documentsArtifact = artifactManifest?.artifacts.find((artifact) => artifact.role === "documents");
        const metadata: ServiceDetailMetadata = {
          buildManifestCid:
            artifactManifest?.sourcePackage.build_manifest_cid ||
            ((generatedManifest as { sourcePackage?: { build_manifest_cid?: string } } | null)?.sourcePackage
              ?.build_manifest_cid ??
              ""),
          documentsArtifactCid: documentsArtifact?.cid ?? "",
          documentCount:
            generatedManifest?.documentCount ?? artifactManifest?.corpus.documentCount ?? documentsState.documents.length,
          loadedAt: new Date().toISOString(),
        };

        setState(
          document
            ? { status: "ready", document, metadata, locations, error: "" }
            : { status: "not-found", document: null, metadata, locations: [], error: "" },
        );
      } catch (error) {
        if (canceled) return;
        setState({
          status: "error",
          document: null,
          metadata: null,
          locations: [],
          error: error instanceof Error ? error.message : "Service detail unavailable",
        });
      }
    }

    void loadServiceDetail();

    return () => {
      canceled = true;
    };
  }, [docId]);

  if (state.status === "loading") {
    return (
      <div className="screen">
        <Button onClick={onBack} variant="quiet">
          <ArrowLeft aria-hidden="true" size={18} />
          Services
        </Button>
        <StatusBanner tone="info">Loading service detail from the local 211 corpus.</StatusBanner>
      </div>
    );
  }

  if (state.status === "error") {
    return (
      <div className="screen">
        <Button onClick={onBack} variant="quiet">
          <ArrowLeft aria-hidden="true" size={18} />
          Services
        </Button>
        <StatusBanner tone="warning">Service detail could not load: {state.error}</StatusBanner>
      </div>
    );
  }

  if (state.status === "not-found") {
    return (
      <div className="screen">
        <Button onClick={onBack} variant="quiet">
          <ArrowLeft aria-hidden="true" size={18} />
          Services
        </Button>
        <StatusBanner tone="warning">No 211 service record was found for {docId}.</StatusBanner>
        <Section title="Requested source">
          <div className="list-item">
            <div>
              <h3>Document ID or CID</h3>
              <p>{docId}</p>
            </div>
          </div>
        </Section>
      </div>
    );
  }

  const document = state.document;
  const metadata = state.metadata;
  const title = document.program_name || document.provider_name || document.title || document.doc_id;
  const provider = document.provider_name || "Provider not listed";
  const program = document.program_name || document.title || "Program not listed";
  const location = getServiceLocationLabel(document);
  const phones = getServicePhones(document);
  const addresses = getServiceAddresses(document);
  const detailedLocations = state.locations;
  const intakeText = getPrimaryIntakeText(document);
  const eligibilityText = getPrimaryEligibilityText(document);
  const requiredDocumentsText = getPrimaryRequiredDocumentsText(document);
  const areaServedText = getServiceAreaServedText(document);
  const travelInfoText = getServiceTravelInfoText(document);
  const provenance = build211InfoServiceProvenance(document, {
    buildManifestCid: metadata.buildManifestCid,
    documentsArtifactCid: metadata.documentsArtifactCid,
    documentCount: metadata.documentCount,
    generatedAt: metadata.loadedAt,
  });

  return (
    <div className="screen">
      <div className="page-title">
        <Button onClick={onBack} variant="quiet">
          <ArrowLeft aria-hidden="true" size={18} />
          Services
        </Button>
        <p className="eyebrow">Service detail</p>
        <h1>{title}</h1>
      </div>

      <Section title="Provider and program">
        <div className="list-stack">
          <article className="list-item">
            <div>
              <h3>Provider</h3>
              <p>{provider}</p>
            </div>
            <Badge>{document.doc_type}</Badge>
          </article>
          <article className="list-item">
            <div>
              <h3>Program</h3>
              <p>{program}</p>
            </div>
            {location ? <Badge tone="success">{location}</Badge> : null}
          </article>
        </div>
      </Section>

      <Section title="Actions">
        <ServiceQuickActions document={document} />
      </Section>

      <Section title="Contact and location">
        <div className="list-stack">
          {phones.length ? (
            <article className="list-item">
              <div>
                <h3>Phone</h3>
                <p>{phones.map((item) => item.value).filter(Boolean).join(" · ")}</p>
              </div>
            </article>
          ) : null}
          {addresses.length ? (
            <article className="list-item">
              <div>
                <h3>{detailedLocations.length ? "Embedded address summary" : "Address"}</h3>
                <p>{addresses.map((item) => item.address || item.maps_query).filter(Boolean).join(" · ")}</p>
              </div>
              {location ? <Badge tone="success">{location}</Badge> : null}
            </article>
          ) : null}
          {detailedLocations.map((item) => {
            const addressText = item.address || item.maps_query || [item.street, item.city, item.state, item.postal_code].filter(Boolean).join(", ");
            const mapHref = item.google_maps_url || item.apple_maps_url || item.geo_url || "";
            return (
              <article className="list-item" key={item.location_id || `${item.service_doc_id}:${item.address}`}>
                <div>
                  <h3>{item.label || "Service location"}</h3>
                  <p>{addressText || "Location available without a formatted address."}</p>
                  {item.geo_precision ? <p className="supporting-copy">Geo precision: {item.geo_precision}</p> : null}
                </div>
                {mapHref ? (
                  <a className="button button-secondary" href={mapHref} rel="noreferrer" target="_blank">
                    Open map
                  </a>
                ) : item.geo_cluster_id != null ? (
                  <Badge tone="success">Cluster {item.geo_cluster_id}</Badge>
                ) : null}
              </article>
            );
          })}
          {areaServedText ? (
            <article className="list-item">
              <div>
                <h3>Area served</h3>
                <p>{areaServedText}</p>
              </div>
            </article>
          ) : null}
          {travelInfoText ? (
            <article className="list-item">
              <div>
                <h3>Travel notes</h3>
                <p>{travelInfoText}</p>
              </div>
            </article>
          ) : null}
        </div>
      </Section>

      <Section title="How to apply">
        <div className="list-stack">
          {intakeText ? (
            <article className="list-item">
              <div>
                <h3>Intake steps</h3>
                <p>{intakeText}</p>
              </div>
            </article>
          ) : null}
          {eligibilityText ? (
            <article className="list-item">
              <div>
                <h3>Eligibility</h3>
                <p>{eligibilityText}</p>
              </div>
            </article>
          ) : null}
          {requiredDocumentsText ? (
            <article className="list-item">
              <div>
                <h3>Required documents</h3>
                <p>{requiredDocumentsText}</p>
              </div>
            </article>
          ) : null}
          {!intakeText && !eligibilityText && !requiredDocumentsText ? (
            <StatusBanner tone="info">This service record does not yet expose structured intake details in the browser corpus.</StatusBanner>
          ) : null}
        </div>
      </Section>

      <Section title="Summary">
        <div className="review-panel">
          <p className="supporting-copy" style={{ overflowWrap: "anywhere" }}>
            {toReadableSummary(document, detailedLocations)}
          </p>
        </div>
      </Section>

      <ServiceProvenancePanel report={provenance} />
    </div>
  );
}

const SUMMARY_NOISE_PATTERNS = [
  /Print\s*&\s*Share\s*X\s*Print\s*&\s*Share\s*Print\s*PDF/gi,
  /Print\s*&\s*Share/gi,
  /Get Directions/gi,
  /Visit Website/gi,
  /Main phone/gi,
];

function toReadableSummary(document: CorpusDocument, detailedLocations: ServiceLocationRecord[]): string {
  const cleanText = sanitizeSummaryText(document.text);
  if (!cleanText) return "No source summary is available for this 211 record.";

  const exclusionValues = buildSummaryExclusionValues(document, detailedLocations);
  const summarySegments = cleanText
    .split(/(?<=[.!?])\s+|\s{2,}|\s+[\u2022\-]\s+/)
    .map((segment) => segment.trim())
    .filter(Boolean)
    .filter((segment) => !isDuplicateStructuredSummarySegment(segment, exclusionValues));

  const summary = summarySegments.join(" ").replace(/\s+/g, " ").trim();
  if (!summary) return "No non-duplicative source summary is available for this 211 record.";
  return summary.length > 700 ? `${summary.slice(0, 700).trim()}...` : summary;
}

function sanitizeSummaryText(text: string): string {
  let value = text.replace(/\s+/g, " ").trim();
  for (const pattern of SUMMARY_NOISE_PATTERNS) {
    value = value.replace(pattern, " ");
  }
  return value.replace(/\s+/g, " ").trim();
}

function buildSummaryExclusionValues(document: CorpusDocument, detailedLocations: ServiceLocationRecord[]): string[] {
  const addressValues = getServiceAddresses(document)
    .flatMap((item) => [item.label, item.address, item.maps_query, item.street, item.city, item.state, item.postal_code]);
  const locationValues = detailedLocations.flatMap((item) => [
    item.label,
    item.address,
    item.maps_query,
    item.street,
    item.city,
    item.state,
    item.postal_code,
  ]);
  const phoneValues = getServicePhones(document).flatMap((item) => [item.label, item.value]);
  const exclusionValues = [
    document.provider_name,
    document.program_name,
    document.title,
    getServiceLocationLabel(document),
    getPrimaryIntakeText(document),
    getPrimaryEligibilityText(document),
    getPrimaryRequiredDocumentsText(document),
    getServiceAreaServedText(document),
    getServiceTravelInfoText(document),
    ...addressValues,
    ...locationValues,
    ...phoneValues,
  ];
  return exclusionValues
    .map(normalizeSummaryComparisonText)
    .filter((value) => value.length >= 12);
}

function isDuplicateStructuredSummarySegment(segment: string, exclusionValues: string[]): boolean {
  const normalizedSegment = normalizeSummaryComparisonText(segment);
  if (!normalizedSegment || normalizedSegment.length < 12) {
    return false;
  }
  return exclusionValues.some(
    (value) => normalizedSegment.includes(value) || value.includes(normalizedSegment),
  );
}

function normalizeSummaryComparisonText(value: string | undefined): string {
  return String(value || "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}
