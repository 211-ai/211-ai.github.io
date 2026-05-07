import { useMemo, useState } from "react";
import { BookmarkPlus, ClipboardList, ExternalLink } from "lucide-react";
import type { SavedService, ServicePlan } from "../../models/abby";
import { saveWalletService, type WalletApiConfig } from "../../services/walletApi";
import { Badge, Button, Field, Section, StatusBanner } from "../ui";

export interface ServiceReference {
  serviceDocId: string;
  sourceContentCid: string;
  sourcePageCid?: string;
  title: string;
  providerName?: string;
  programName?: string;
  sourceUrl?: string;
  city?: string;
  state?: string;
}

interface SavedServicesPanelProps {
  savedServices: SavedService[];
  servicePlans: ServicePlan[];
  candidateServices?: ServiceReference[];
  walletApiConfig?: WalletApiConfig;
  onSavedServicesChange: (services: SavedService[]) => void;
  onOpenDetail?: (docId: string) => void;
  onOpenPlan?: (docId: string) => void;
}

export function SavedServicesPanel({
  savedServices,
  servicePlans,
  candidateServices = [],
  walletApiConfig,
  onSavedServicesChange,
  onOpenDetail,
  onOpenPlan,
}: SavedServicesPanelProps) {
  const [selectedServiceId, setSelectedServiceId] = useState(candidateServices[0]?.serviceDocId ?? "");
  const [reason, setReason] = useState("");
  const [priority, setPriority] = useState("normal");
  const [status, setStatus] = useState<"idle" | "saving" | "saved" | "failed">("idle");

  const selectedService = useMemo(
    () => candidateServices.find((service) => service.serviceDocId === selectedServiceId) ?? candidateServices[0],
    [candidateServices, selectedServiceId],
  );
  const savedByDocId = useMemo(
    () => new Map(savedServices.map((service) => [service.service_doc_id, service])),
    [savedServices],
  );
  const plansByDocId = useMemo(
    () => new Map(servicePlans.map((plan) => [plan.service_doc_id, plan])),
    [servicePlans],
  );

  async function saveReference(reference: ServiceReference, options: { openPlanAfterSave?: boolean } = {}) {
    setStatus("saving");
    try {
      const saved =
        walletApiConfig?.actorDid
          ? await saveWalletService(walletApiConfig, {
              serviceDocId: reference.serviceDocId,
              sourceContentCid: reference.sourceContentCid || fallbackCid(reference.serviceDocId),
              sourcePageCid: reference.sourcePageCid,
              title: reference.title,
              providerName: reference.providerName,
              programName: reference.programName,
              sourceUrl: reference.sourceUrl,
              label: reference.title,
              reason,
              priority,
              status: "saved",
              metadata: { saved_from: "services_panel" },
            })
          : createLocalSavedService(reference, { reason, priority, walletId: walletApiConfig?.walletId });

      onSavedServicesChange(upsertSavedService(savedServices, saved));
      setStatus("saved");
      if (options.openPlanAfterSave) {
        onOpenPlan?.(reference.serviceDocId);
      }
    } catch {
      setStatus("failed");
    }
  }

  return (
    <Section
      eyebrow="Wallet"
      title="Saved services"
      actions={
        <Badge tone={walletApiConfig?.actorDid ? "success" : "warning"}>
          {walletApiConfig?.actorDid ? "Wallet backed" : "Local draft"}
        </Badge>
      }
    >
      {status === "saved" ? <StatusBanner tone="success">Service saved to your wallet workspace.</StatusBanner> : null}
      {status === "failed" ? <StatusBanner tone="warning">Service could not be saved. Try again.</StatusBanner> : null}

      {candidateServices.length ? (
        <div className="review-panel">
          <div className="form-grid">
            <Field label="Service to save">
              <select value={selectedService?.serviceDocId ?? ""} onChange={(event) => setSelectedServiceId(event.target.value)}>
                {candidateServices.map((service) => (
                  <option key={service.serviceDocId} value={service.serviceDocId}>
                    {service.title}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Why save it">
              <input
                onChange={(event) => setReason(event.target.value)}
                placeholder="Example: call about intake hours"
                value={reason}
              />
            </Field>
            <Field label="Priority">
              <select onChange={(event) => setPriority(event.target.value)} value={priority}>
                <option value="normal">Normal</option>
                <option value="high">High</option>
                <option value="urgent">Urgent</option>
              </select>
            </Field>
            <div className="row-actions">
              <Button disabled={!selectedService || status === "saving"} onClick={() => selectedService && saveReference(selectedService)}>
                <BookmarkPlus aria-hidden="true" size={18} />
                Save selected
              </Button>
              <Button
                disabled={!selectedService || status === "saving"}
                onClick={() => selectedService && saveReference(selectedService, { openPlanAfterSave: true })}
                variant="secondary"
              >
                <ClipboardList aria-hidden="true" size={18} />
                Save and plan
              </Button>
            </div>
          </div>
        </div>
      ) : null}

      {candidateServices.length ? (
        <div className="list-stack" aria-label="Current service results">
          {candidateServices.slice(0, 3).map((service) => {
            const saved = savedByDocId.get(service.serviceDocId);
            const plan = plansByDocId.get(service.serviceDocId);
            return (
              <article className="list-item" key={service.serviceDocId}>
                <div>
                  <h3>{service.title}</h3>
                  <p>{service.providerName || "Provider not listed"}</p>
                  <div className="badge-row">
                    {saved ? <Badge tone="success">saved</Badge> : <Badge>not saved</Badge>}
                    {plan ? <Badge tone="success">plan ready</Badge> : null}
                    {service.city || service.state ? <Badge>{[service.city, service.state].filter(Boolean).join(", ")}</Badge> : null}
                  </div>
                </div>
                <div className="row-actions list-item-action">
                  <Button
                    ariaLabel={`Save service ${service.title}`}
                    disabled={Boolean(saved) || status === "saving"}
                    onClick={() => saveReference(service)}
                    variant="secondary"
                  >
                    <BookmarkPlus aria-hidden="true" size={18} />
                    {saved ? "Saved" : "Save"}
                  </Button>
                  <Button ariaLabel={`Plan service ${service.title}`} onClick={() => onOpenPlan?.(service.serviceDocId)} variant="secondary">
                    <ClipboardList aria-hidden="true" size={18} />
                    Plan
                  </Button>
                  {onOpenDetail ? (
                    <Button ariaLabel={`Open detail ${service.title}`} onClick={() => onOpenDetail(service.serviceDocId)} variant="quiet">
                      <ExternalLink aria-hidden="true" size={18} />
                    </Button>
                  ) : null}
                </div>
              </article>
            );
          })}
        </div>
      ) : null}

      {savedServices.length ? (
        <div className="list-stack" aria-label="Saved services list">
          {savedServices.map((service) => {
            const plan = plansByDocId.get(service.service_doc_id);
            const title = service.label || service.program_name || service.title || service.service_doc_id;
            return (
              <article className="list-item" key={service.saved_service_id}>
                <div>
                  <h3>{title}</h3>
                  <p>{service.provider_name || "Provider not listed"}</p>
                  {service.reason ? <small className="upload-machine-summary">{service.reason}</small> : null}
                  <div className="badge-row">
                    <Badge tone={service.status === "saved" ? "success" : "neutral"}>{service.status}</Badge>
                    <Badge>{service.priority || "normal"}</Badge>
                    {plan ? <Badge tone="success">plan</Badge> : null}
                    {service.private_notes_record_id ? <Badge tone="success">encrypted note</Badge> : null}
                  </div>
                </div>
                <div className="row-actions list-item-action">
                  <Button onClick={() => onOpenPlan?.(service.service_doc_id)} variant="secondary">
                    <ClipboardList aria-hidden="true" size={18} />
                    {plan ? "Open plan" : "Create plan"}
                  </Button>
                  {onOpenDetail ? (
                    <Button onClick={() => onOpenDetail(service.service_doc_id)} variant="quiet">
                      <ExternalLink aria-hidden="true" size={18} />
                    </Button>
                  ) : null}
                </div>
              </article>
            );
          })}
        </div>
      ) : !candidateServices.length ? (
        <StatusBanner tone="info">Search for a service, then save it here for follow-up.</StatusBanner>
      ) : null}
    </Section>
  );
}

function upsertSavedService(current: SavedService[], saved: SavedService): SavedService[] {
  return [saved, ...current.filter((service) => service.saved_service_id !== saved.saved_service_id)];
}

function createLocalSavedService(
  reference: ServiceReference,
  {
    reason,
    priority,
    walletId,
  }: {
    reason: string;
    priority: string;
    walletId?: string;
  },
): SavedService {
  const now = new Date().toISOString();
  return {
    saved_service_id: `local-saved-${stableSuffix(reference.serviceDocId)}`,
    wallet_id: walletId || "local-wallet",
    service_doc_id: reference.serviceDocId,
    source_content_cid: reference.sourceContentCid || fallbackCid(reference.serviceDocId),
    source_page_cid: reference.sourcePageCid || "",
    title: reference.title,
    provider_name: reference.providerName || "",
    program_name: reference.programName || "",
    source_url: reference.sourceUrl || "",
    label: reference.title,
    reason: reason.trim(),
    priority,
    status: "saved",
    created_at: now,
    updated_at: now,
    private_notes_record_id: "",
    metadata: { saved_from: "services_panel", storage: "local" },
  };
}

function fallbackCid(serviceDocId: string): string {
  return `local-unresolved-${stableSuffix(serviceDocId)}`;
}

function stableSuffix(value: string): string {
  let hash = 5381;
  for (let index = 0; index < value.length; index += 1) {
    hash = (hash * 33) ^ value.charCodeAt(index);
  }
  return (hash >>> 0).toString(36);
}
