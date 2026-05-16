import { useEffect, useMemo, useState } from "react";
import { CalendarClock, ExternalLink, RefreshCw } from "lucide-react";
import { getServiceLocationLabel, load211DocumentsByReference, type CorpusDocument } from "../../lib/graphrag";
import type { SavedService, ServicePlan } from "../../models/abby";
import { Badge, Button, Section, StatusBanner } from "../ui";
import { ServiceQuickActions } from "./ServiceQuickActions";

export function SavedServicesPanel({
  error = "",
  loading = false,
  onOpenDetail,
  onOpenPlan,
  onRefresh,
  savedServices,
  servicePlans
}: {
  error?: string;
  loading?: boolean;
  onOpenDetail: (docId: string) => void;
  onOpenPlan: (docId: string) => void;
  onRefresh?: () => void;
  savedServices: SavedService[];
  servicePlans: ServicePlan[];
}) {
  const [documentById, setDocumentById] = useState<Map<string, CorpusDocument>>(new Map());
  const serviceByDoc = new Map(savedServices.map((service) => [service.service_doc_id, service]));
  const planByService = new Map(servicePlans.map((plan) => [plan.service_doc_id, plan]));
  const rows = [
    ...savedServices.map((service) => ({ service, plan: planByService.get(service.service_doc_id) })),
    ...servicePlans
      .filter((plan) => !serviceByDoc.has(plan.service_doc_id))
      .map((plan) => ({ service: undefined, plan }))
  ];
  const serviceDocIds = useMemo(
    () =>
      [...new Set(rows.map(({ plan, service }) => service?.service_doc_id || plan?.service_doc_id || "").filter(Boolean))],
    [rows]
  );
  const serviceDocIdKey = serviceDocIds.join("\u0000");

  useEffect(() => {
    let canceled = false;
    if (!serviceDocIds.length) {
      setDocumentById(new Map());
      return () => {
        canceled = true;
      };
    }
    load211DocumentsByReference(serviceDocIds, { docTypes: ["service"], limit: serviceDocIds.length })
      .then((state) => {
        if (!canceled) {
          setDocumentById(state.documentById);
        }
      })
      .catch(() => undefined);
    return () => {
      canceled = true;
    };
  }, [serviceDocIdKey]);

  return (
    <Section
      actions={
        onRefresh ? (
          <Button
            ariaLabel="Refresh saved services"
            loading={loading}
            loadingLabel="Refreshing"
            onClick={onRefresh}
            variant="quiet"
          >
            <RefreshCw aria-hidden="true" size={18} />
          </Button>
        ) : null
      }
      title="Saved services"
    >
      {error ? <StatusBanner tone="warning">Saved services could not refresh: {error}</StatusBanner> : null}
      {!rows.length ? (
        <StatusBanner tone="info">Save a service from search results to keep it in your private service list.</StatusBanner>
      ) : (
        <div className="list-stack" aria-label="Saved services">
          {rows.map(({ plan, service }) => {
            const serviceDocId = service?.service_doc_id || plan?.service_doc_id || "";
            const serviceDocument = serviceDocId ? documentById.get(serviceDocId) : undefined;
            const title =
              service?.label ||
              service?.program_name ||
              serviceDocument?.program_name ||
              service?.title ||
              serviceDocument?.title ||
              plan?.service_title ||
              serviceDocId;
            const provider =
              service?.provider_name || plan?.provider_name || serviceDocument?.provider_name || "Provider not listed";
            const location = serviceDocument ? getServiceLocationLabel(serviceDocument) : "";
            return (
              <article className="list-item" key={service?.saved_service_id || plan?.plan_id || serviceDocId}>
                <div>
                  <h3>{title}</h3>
                  <p>{provider}</p>
                  {service?.reason ? <small className="upload-machine-summary">{service.reason}</small> : null}
                  <div className="badge-row">
                    {service ? (
                      <Badge tone={service.priority === "high" ? "warning" : "neutral"}>
                        {service.priority || "normal"}
                      </Badge>
                    ) : null}
                    <Badge tone={service?.status === "saved" || !service ? "success" : "neutral"}>
                      {service?.status || "planned"}
                    </Badge>
                    {plan ? <Badge tone="info">plan {plan.status || "active"}</Badge> : null}
                    {service?.private_notes_record_id || plan?.private_notes_record_id ? (
                      <Badge tone="success">encrypted notes</Badge>
                    ) : null}
                    {location ? <Badge>{location}</Badge> : null}
                  </div>
                </div>
                <div className="row-actions list-item-action">
                  {serviceDocument ? <ServiceQuickActions document={serviceDocument} /> : null}
                  {service?.source_url ? (
                    <a className="button button-secondary" href={service.source_url} rel="noreferrer" target="_blank">
                      <ExternalLink aria-hidden="true" size={18} />
                      Source
                    </a>
                  ) : null}
                  <Button onClick={() => onOpenDetail(serviceDocId)} variant="secondary">
                    Open detail
                  </Button>
                  <Button onClick={() => onOpenPlan(serviceDocId)} variant={plan ? "secondary" : "primary"}>
                    <CalendarClock aria-hidden="true" size={18} />
                    {plan ? "Edit plan" : "Create plan"}
                  </Button>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </Section>
  );
}
