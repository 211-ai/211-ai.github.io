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
    </div>
  );
}
