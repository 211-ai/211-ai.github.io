import { useState } from "react";
import { ClipboardList, ExternalLink, HeartHandshake, Plus, Save } from "lucide-react";
import { Badge, Button, Section, StatusBanner } from "../ui";
import type { SavedService, ServiceInteractionEvent, ServicePlan } from "../../models/abby";
import type { SearchResult } from "../../lib/graphrag";
import {
  createWalletServiceInteraction,
  createWalletServicePlan,
  saveWalletService,
  type WalletApiConfig
} from "../../services/walletApi";

export interface ServiceCandidate {
  serviceDocId: string;
  sourceContentCid: string;
  sourcePageCid: string;
  title: string;
  providerName: string;
  programName: string;
  sourceUrl: string;
  city: string;
  state: string;
  docType: string;
  snippet?: string;
}

interface SavedServicesPanelProps {
  apiConfig?: WalletApiConfig;
  candidates?: ServiceCandidate[];
  savedServices: SavedService[];
  servicePlans: ServicePlan[];
  serviceInteractions: ServiceInteractionEvent[];
  setSavedServices: (services: SavedService[]) => void;
  setServicePlans: (plans: ServicePlan[]) => void;
  setServiceInteractions: (interactions: ServiceInteractionEvent[]) => void;
  onOpenDetail: (docId: string) => void;
  onOpenPlan: (docId: string) => void;
  refreshWalletAuditEvents?: () => Promise<void>;
}

export function SavedServicesPanel({
  apiConfig,
  candidates = [],
  savedServices,
  servicePlans,
  serviceInteractions,
  setSavedServices,
  setServicePlans,
  setServiceInteractions,
  onOpenDetail,
  onOpenPlan,
  refreshWalletAuditEvents
}: SavedServicesPanelProps) {
  const [busyKey, setBusyKey] = useState("");
  const [notice, setNotice] = useState<{ tone: "success" | "warning"; text: string } | null>(null);

  async function saveCandidate(candidate: ServiceCandidate) {
    const key = `save-${candidate.serviceDocId}`;
    setBusyKey(key);
    setNotice(null);
    try {
      const saved = apiConfig?.actorDid
        ? await saveWalletService(apiConfig, {
            serviceDocId: candidate.serviceDocId,
            sourceContentCid: candidate.sourceContentCid,
            sourcePageCid: candidate.sourcePageCid,
            title: candidate.title,
            providerName: candidate.providerName,
            programName: candidate.programName,
            sourceUrl: candidate.sourceUrl,
            label: candidate.title,
            reason: "Saved from service search"
          })
        : createLocalSavedService(candidate, { reason: "Saved from service search" }, apiConfig?.walletId);

      const interaction = apiConfig?.actorDid
        ? await createWalletServiceInteraction(apiConfig, {
            serviceDocId: candidate.serviceDocId,
            sourceContentCid: candidate.sourceContentCid,
            sourcePageCid: candidate.sourcePageCid,
            providerName: candidate.providerName,
            programName: candidate.programName,
            interactionType: "saved_service",
            channel: "web",
            status: "recorded",
            sourceActionUrl: candidate.sourceUrl,
            privacyLevel: "private",
            metadata: { source: "saved_services_panel" }
          }).catch(() => undefined)
        : createLocalServiceInteraction(candidate, "saved_service", apiConfig?.walletId);

      setSavedServices(upsertSavedService(savedServices, saved));
      if (interaction) {
        setServiceInteractions(upsertServiceInteraction(serviceInteractions, interaction));
      }
      await refreshWalletAuditEvents?.().catch(() => undefined);
      setNotice({ tone: "success", text: "Service saved to your wallet workspace." });
    } catch (error) {
      setNotice({
        tone: "warning",
        text: error instanceof Error ? error.message : "Service could not be saved."
      });
    } finally {
      setBusyKey("");
    }
  }

  async function createPlan(candidate: ServiceCandidate) {
    const key = `plan-${candidate.serviceDocId}`;
    const existingPlan = findPlanForService(servicePlans, candidate.serviceDocId);
    if (existingPlan) {
      onOpenPlan(candidate.serviceDocId);
      return;
    }

    setBusyKey(key);
    setNotice(null);
    try {
      const saved = findSavedService(savedServices, candidate.serviceDocId);
      if (!saved) {
        const createdSaved = apiConfig?.actorDid
          ? await saveWalletService(apiConfig, {
              serviceDocId: candidate.serviceDocId,
              sourceContentCid: candidate.sourceContentCid,
              sourcePageCid: candidate.sourcePageCid,
              title: candidate.title,
              providerName: candidate.providerName,
              programName: candidate.programName,
              sourceUrl: candidate.sourceUrl,
              label: candidate.title,
              reason: "Saved with service plan"
            })
          : createLocalSavedService(candidate, { reason: "Saved with service plan" }, apiConfig?.walletId);
        setSavedServices(upsertSavedService(savedServices, createdSaved));
      }

      const plan = apiConfig?.actorDid
        ? await createWalletServicePlan(apiConfig, {
            serviceDocId: candidate.serviceDocId,
            sourceContentCid: candidate.sourceContentCid,
            sourcePageCid: candidate.sourcePageCid,
            serviceTitle: candidate.title,
            providerName: candidate.providerName,
            goal: `Contact ${candidate.providerName || candidate.title}`,
            steps: ["Confirm eligibility", "Ask how to apply", "Write down next follow-up"],
            questionsToAsk: ["What should I bring?", "When should I call or visit?"],
            travelTarget: candidate.city || candidate.sourceUrl ? serviceLocation(candidate) : ""
          })
        : createLocalServicePlan(
            candidate,
            {
              goal: `Contact ${candidate.providerName || candidate.title}`,
              steps: ["Confirm eligibility", "Ask how to apply", "Write down next follow-up"],
              questionsToAsk: ["What should I bring?", "When should I call or visit?"],
              travelTarget: candidate.city || candidate.sourceUrl ? serviceLocation(candidate) : ""
            },
            apiConfig?.walletId
          );

      setServicePlans(upsertServicePlan(servicePlans, plan));
      await refreshWalletAuditEvents?.().catch(() => undefined);
      setNotice({ tone: "success", text: "Service plan created." });
      onOpenPlan(candidate.serviceDocId);
    } catch (error) {
      setNotice({
        tone: "warning",
        text: error instanceof Error ? error.message : "Service plan could not be created."
      });
    } finally {
      setBusyKey("");
    }
  }

  const savedCount = savedServices.filter((item) => item.status !== "revoked").length;

  return (
    <Section
      eyebrow="Wallet"
      title="Saved services"
      actions={savedCount ? <Badge tone="success">{savedCount} saved</Badge> : <Badge>0 saved</Badge>}
    >
      {notice ? <StatusBanner tone={notice.tone}>{notice.text}</StatusBanner> : null}

      {candidates.length ? (
        <div className="list-stack" aria-label="Save search results">
          {candidates.slice(0, 4).map((candidate) => {
            const saved = findSavedService(savedServices, candidate.serviceDocId);
            const plan = findPlanForService(servicePlans, candidate.serviceDocId);
            const location = serviceLocation(candidate);
            return (
              <article className="list-item access-request-item" key={`candidate-${candidate.serviceDocId}`}>
                <div>
                  <h3>{candidate.title}</h3>
                  <p>{candidate.providerName || "Provider not listed"}</p>
                  {candidate.snippet ? <small className="upload-machine-summary">{candidate.snippet}</small> : null}
                  <div className="badge-row">
                    {saved ? <Badge tone="success">saved</Badge> : <Badge>{candidate.docType || "service"}</Badge>}
                    {plan ? <Badge tone="success">plan ready</Badge> : null}
                    {location ? <Badge>{location}</Badge> : null}
                  </div>
                </div>
                <div className="row-actions">
                  <Button onClick={() => onOpenDetail(candidate.serviceDocId)} variant="secondary">
                    <ExternalLink aria-hidden="true" size={18} />
                    Detail
                  </Button>
                  <Button
                    disabled={Boolean(saved)}
                    loading={busyKey === `save-${candidate.serviceDocId}`}
                    loadingLabel="Saving"
                    onClick={() => saveCandidate(candidate)}
                    variant={saved ? "secondary" : "primary"}
                  >
                    <Save aria-hidden="true" size={18} />
                    {saved ? "Saved" : "Save"}
                  </Button>
                  <Button
                    loading={busyKey === `plan-${candidate.serviceDocId}`}
                    loadingLabel="Creating"
                    onClick={() => createPlan(candidate)}
                    variant="secondary"
                  >
                    <ClipboardList aria-hidden="true" size={18} />
                    {plan ? "Open plan" : "Plan"}
                  </Button>
                </div>
              </article>
            );
          })}
        </div>
      ) : null}

      {savedServices.length ? (
        <div className="list-stack" aria-label="Saved services">
          {savedServices.map((service) => {
            const plan = findPlanForService(servicePlans, service.service_doc_id);
            return (
              <article className="list-item" key={service.saved_service_id}>
                <div>
                  <h3>{savedServiceTitle(service)}</h3>
                  <p>{service.provider_name || service.program_name || "Provider not listed"}</p>
                  <div className="badge-row">
                    <Badge tone={service.priority === "high" ? "warning" : "neutral"}>{service.priority || "normal"}</Badge>
                    <Badge>{service.status || "saved"}</Badge>
                    {service.private_notes_record_id ? <Badge tone="success">encrypted notes</Badge> : null}
                    {plan ? <Badge tone="success">plan</Badge> : null}
                  </div>
                </div>
                <div className="row-actions list-item-action">
                  <Button onClick={() => onOpenDetail(service.service_doc_id)} variant="secondary">
                    Detail
                  </Button>
                  <Button onClick={() => onOpenPlan(service.service_doc_id)} variant={plan ? "primary" : "secondary"}>
                    {plan ? (
                      <ClipboardList aria-hidden="true" size={18} />
                    ) : (
                      <Plus aria-hidden="true" size={18} />
                    )}
                    {plan ? "Open plan" : "Create plan"}
                  </Button>
                </div>
              </article>
            );
          })}
        </div>
      ) : candidates.length ? null : (
        <div className="review-panel">
          <HeartHandshake aria-hidden="true" size={24} />
          <p className="supporting-copy">Saved services and plans will appear here after you choose a service.</p>
        </div>
      )}
    </Section>
  );
}

export function serviceCandidateFromSearchResult(result: SearchResult): ServiceCandidate {
  const document = result.document;
  return {
    serviceDocId: document.doc_id || result.docId,
    sourceContentCid: document.source_content_cid || result.contentCid || fallbackCid(result.docId),
    sourcePageCid: document.source_page_cid || result.pageCid || "",
    title: document.program_name || document.provider_name || document.title || result.docId,
    providerName: document.provider_name || "",
    programName: document.program_name || document.title || "",
    sourceUrl: document.source_url || "",
    city: document.city || "",
    state: document.state || "",
    docType: document.doc_type || "service",
    snippet: result.snippet
  };
}

export function serviceLocation(candidate: Pick<ServiceCandidate, "city" | "state">): string {
  return [candidate.city, candidate.state].filter(Boolean).join(", ");
}

export function savedServiceTitle(service: SavedService): string {
  return service.label || service.title || service.program_name || service.provider_name || service.service_doc_id;
}

export function findSavedService(savedServices: SavedService[], serviceDocId: string): SavedService | undefined {
  return savedServices.find((service) => service.service_doc_id === serviceDocId && service.status !== "revoked");
}

export function findPlanForService(servicePlans: ServicePlan[], serviceDocId: string): ServicePlan | undefined {
  return servicePlans
    .filter((plan) => plan.service_doc_id === serviceDocId && plan.status !== "revoked")
    .sort((a, b) => new Date(b.updated_at || b.created_at).getTime() - new Date(a.updated_at || a.created_at).getTime())[0];
}

export function upsertSavedService(savedServices: SavedService[], saved: SavedService): SavedService[] {
  return [saved, ...savedServices.filter((item) => item.saved_service_id !== saved.saved_service_id)];
}

export function upsertServicePlan(servicePlans: ServicePlan[], plan: ServicePlan): ServicePlan[] {
  return [plan, ...servicePlans.filter((item) => item.plan_id !== plan.plan_id)];
}

export function upsertServiceInteraction(
  serviceInteractions: ServiceInteractionEvent[],
  interaction: ServiceInteractionEvent
): ServiceInteractionEvent[] {
  return [
    interaction,
    ...serviceInteractions.filter((item) => item.interaction_id !== interaction.interaction_id)
  ];
}

export function createLocalSavedService(
  candidate: ServiceCandidate,
  input: {
    label?: string;
    reason?: string;
    priority?: string;
    status?: string;
    privateNotesRecordId?: string;
  } = {},
  walletId = "local-wallet"
): SavedService {
  const now = new Date().toISOString();
  return {
    saved_service_id: `saved-${stableSuffix(candidate.serviceDocId)}`,
    wallet_id: walletId,
    service_doc_id: candidate.serviceDocId,
    source_content_cid: candidate.sourceContentCid || fallbackCid(candidate.serviceDocId),
    source_page_cid: candidate.sourcePageCid,
    title: candidate.title,
    provider_name: candidate.providerName,
    program_name: candidate.programName,
    source_url: candidate.sourceUrl,
    label: input.label || candidate.title,
    reason: input.reason || "",
    priority: input.priority || "normal",
    status: input.status || "saved",
    created_at: now,
    updated_at: now,
    private_notes_record_id: input.privateNotesRecordId || "",
    metadata: {}
  };
}

export function createLocalServicePlan(
  candidate: ServiceCandidate,
  input: {
    goal?: string;
    steps?: string[];
    documentsNeeded?: string[];
    questionsToAsk?: string[];
    appointmentAt?: string;
    reminderAt?: string;
    travelTarget?: string;
    assignedWorkerRecipientId?: string;
    status?: string;
    privateNotesRecordId?: string;
  } = {},
  walletId = "local-wallet"
): ServicePlan {
  const now = new Date().toISOString();
  return {
    plan_id: `plan-${stableSuffix(`${candidate.serviceDocId}-${now}`)}`,
    wallet_id: walletId,
    service_doc_id: candidate.serviceDocId,
    source_content_cid: candidate.sourceContentCid || fallbackCid(candidate.serviceDocId),
    source_page_cid: candidate.sourcePageCid,
    service_title: candidate.title,
    provider_name: candidate.providerName,
    goal: input.goal || "",
    steps: cleanList(input.steps),
    documents_needed: cleanList(input.documentsNeeded),
    questions_to_ask: cleanList(input.questionsToAsk),
    appointment_at: input.appointmentAt || "",
    reminder_at: input.reminderAt || "",
    travel_target: input.travelTarget || "",
    assigned_worker_recipient_id: input.assignedWorkerRecipientId || "",
    status: input.status || "active",
    related_interaction_ids: [],
    private_notes_record_id: input.privateNotesRecordId || "",
    created_at: now,
    updated_at: now
  };
}

export function createLocalServiceInteraction(
  candidate: ServiceCandidate,
  interactionType: string,
  walletId = "local-wallet"
): ServiceInteractionEvent {
  const now = new Date().toISOString();
  return {
    interaction_id: `interaction-${stableSuffix(`${candidate.serviceDocId}-${interactionType}-${now}`)}`,
    wallet_id: walletId,
    service_doc_id: candidate.serviceDocId,
    source_content_cid: candidate.sourceContentCid || fallbackCid(candidate.serviceDocId),
    source_page_cid: candidate.sourcePageCid,
    provider_name: candidate.providerName,
    program_name: candidate.programName,
    interaction_type: interactionType,
    channel: "web",
    actor_did: "local-user",
    counterparty_name: "",
    counterparty_contact: "",
    timestamp: now,
    status: "recorded",
    outcome: "",
    notes_record_id: "",
    next_action: "",
    next_follow_up_at: "",
    source_action_url: candidate.sourceUrl,
    related_grant_ids: [],
    related_record_ids: [],
    privacy_level: "private",
    created_at: now,
    updated_at: now,
    metadata: {}
  };
}

export function candidateFromSavedService(service: SavedService): ServiceCandidate {
  return {
    serviceDocId: service.service_doc_id,
    sourceContentCid: service.source_content_cid || fallbackCid(service.service_doc_id),
    sourcePageCid: service.source_page_cid || "",
    title: savedServiceTitle(service),
    providerName: service.provider_name,
    programName: service.program_name,
    sourceUrl: service.source_url,
    city: "",
    state: "",
    docType: "service"
  };
}

export function cleanList(values: string[] | undefined): string[] {
  return Array.from(new Set((values ?? []).map((value) => value.trim()).filter(Boolean)));
}

export function stableSuffix(value: string): string {
  let hash = 5381;
  for (let index = 0; index < value.length; index += 1) {
    hash = (hash * 33) ^ value.charCodeAt(index);
  }
  return (hash >>> 0).toString(36);
}

function fallbackCid(serviceDocId: string): string {
  return `ui-unresolved-${stableSuffix(serviceDocId)}`;
}
