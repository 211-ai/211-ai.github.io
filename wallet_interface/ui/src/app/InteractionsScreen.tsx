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
import { Badge } from "../components/ui";
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
  const nextFollowUpCount = interactions.filter((interaction) => Boolean(interaction.next_follow_up_at)).length;
  const connectedSourceLabel = apiConfig ? `Connected wallet: ${apiConfig.walletId}` : "Browser session only";
  const pageNote = apiConfig
    ? `Showing service interactions synced from the connected wallet. ${nextFollowUpCount} follow-up reminders are ready to carry into Calendar.`
    : "Showing service interactions saved in this browser session.";

  return (
    <div className="screen interactions-screen">
      <div className="page-title">
        <p className="eyebrow">Services</p>
        <h1>Interaction history</h1>
      </div>
      <div className="interaction-page-intro">
        <p className="page-note">{pageNote}</p>
        <div className="badge-row">
          <Badge tone={apiConfig ? "success" : "neutral"}>{connectedSourceLabel}</Badge>
          <Badge tone="info">{interactions.length} recorded events</Badge>
          <Badge tone="neutral">{nextFollowUpCount} calendar follow-ups</Badge>
        </div>
      </div>
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
    </div>
  );
}
