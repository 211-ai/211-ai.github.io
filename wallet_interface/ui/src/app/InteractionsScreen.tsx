import type {
  AuditEvent,
  DisclosureRecipientDraft,
  ProofReceiptView,
  SavedService,
  ServiceInteractionEvent,
  ServicePlan,
  UploadItem,
  WalletAccessRequest,
  WalletGrantReceipt
} from "../models/abby";
import { InteractionTimeline } from "../components/services/InteractionTimeline";
import { Section, StatusBanner } from "../components/ui";
import type { WalletApiConfig } from "../services/walletApi";

export function InteractionsScreen({
  accessRequests = [],
  apiConfig,
  auditEvents = [],
  error = "",
  grantReceipts = [],
  interactions,
  loading = false,
  onOpenPlan,
  onOpenService,
  onRefresh,
  proofReceipts = [],
  recipients = [],
  savedServices = [],
  servicePlans = [],
  uploads = []
}: {
  accessRequests?: WalletAccessRequest[];
  apiConfig?: WalletApiConfig;
  auditEvents?: AuditEvent[];
  error?: string;
  grantReceipts?: WalletGrantReceipt[];
  interactions: ServiceInteractionEvent[];
  loading?: boolean;
  onOpenPlan?: (docId: string) => void;
  onOpenService?: (docId: string) => void;
  onRefresh?: () => void;
  proofReceipts?: ProofReceiptView[];
  recipients?: DisclosureRecipientDraft[];
  savedServices?: SavedService[];
  servicePlans?: ServicePlan[];
  uploads?: UploadItem[];
}) {
  return (
    <div className="screen">
      <div className="page-title">
        <p className="eyebrow">Services</p>
        <h1>Interaction history</h1>
      </div>
      {!apiConfig ? (
        <p className="page-note">Showing service interactions saved in this browser session.</p>
      ) : null}
      <InteractionTimeline
        accessRequests={accessRequests}
        auditEvents={auditEvents}
        error={error}
        grantReceipts={grantReceipts}
        interactions={interactions}
        loading={loading}
        onOpenPlan={onOpenPlan}
        onOpenService={onOpenService}
        onRefresh={onRefresh}
        proofReceipts={proofReceipts}
        recipients={recipients}
        savedServices={savedServices}
        servicePlans={servicePlans}
        uploads={uploads}
      />
      <AuditHistorySection events={auditEvents} />
    </div>
  );
}

function AuditHistorySection({ events }: { events: AuditEvent[] }) {
  return (
    <Section eyebrow="Audit" title="Consent and access history">
      {!events.length ? <StatusBanner tone="info">No consent or access events have been recorded yet.</StatusBanner> : null}
      {events.length ? (
        <div className="timeline" aria-label="Consent and access history">
          {events.map((event) => (
            <article className="timeline-event" key={event.id}>
              <span aria-hidden="true" />
              <div>
                <h3>{event.action}</h3>
                <p>
                  {event.actor} · {event.timestamp}
                </p>
                {event.resource || event.decision || event.grantId ? (
                  <small>{[event.decision, event.resource, event.grantId].filter(Boolean).join(" · ")}</small>
                ) : null}
              </div>
            </article>
          ))}
        </div>
      ) : null}
    </Section>
  );
}
