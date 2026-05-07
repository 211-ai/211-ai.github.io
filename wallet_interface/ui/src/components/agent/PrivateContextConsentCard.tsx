import {
  Check,
  FileText,
  LocateFixed,
  ShieldQuestion,
  UserRound,
  WalletCards,
  X
} from "lucide-react";
import { Button } from "../ui";

export const PRIVATE_CONTEXT_CONSENT_CATEGORIES = [
  "wallet_summaries",
  "saved_services",
  "uploaded_document_summaries",
  "eligibility_notes",
  "location",
  "recipients"
] as const;

export type PrivateContextConsentCategory = (typeof PRIVATE_CONTEXT_CONSENT_CATEGORIES)[number];
export type PrivateContextConsentStatus = "pending" | "allowed" | "denied";

export interface PrivateContextConsentDecision {
  requestId: string;
  allowed: boolean;
  categories: PrivateContextConsentCategory[];
  scope: "single_response";
  reason: string;
}

export interface PrivateContextConsentCardProps {
  requestId: string;
  reason: string;
  categories?: readonly PrivateContextConsentCategory[];
  status?: PrivateContextConsentStatus;
  disabled?: boolean;
  expiresAt?: string;
  onAllow?: (decision: PrivateContextConsentDecision) => void;
  onDeny?: (decision: PrivateContextConsentDecision) => void;
}

const privateContextCategoryDetails: Record<
  PrivateContextConsentCategory,
  {
    label: string;
    description: string;
    Icon: typeof WalletCards;
  }
> = {
  wallet_summaries: {
    label: "Private wallet summaries",
    description: "Record labels, proof summaries, and wallet status needed for this answer.",
    Icon: WalletCards
  },
  saved_services: {
    label: "Saved services",
    description: "Services you saved or planned to follow up on.",
    Icon: WalletCards
  },
  uploaded_document_summaries: {
    label: "Uploaded document summaries",
    description: "Short summaries of uploaded documents, not raw document contents.",
    Icon: FileText
  },
  eligibility_notes: {
    label: "Eligibility notes",
    description: "Notes about needs, qualifications, or benefits details you already saved.",
    Icon: FileText
  },
  location: {
    label: "Location",
    description: "Location details needed to narrow service options or explain next steps.",
    Icon: LocateFixed
  },
  recipients: {
    label: "Recipients",
    description: "Saved recipients or sharing contacts relevant to the response.",
    Icon: UserRound
  }
};

export function PrivateContextConsentCard({
  requestId,
  reason,
  categories = PRIVATE_CONTEXT_CONSENT_CATEGORIES,
  status = "pending",
  disabled = false,
  expiresAt,
  onAllow,
  onDeny
}: PrivateContextConsentCardProps) {
  const requestedCategories = normalizeCategories(categories);
  const actionsDisabled = disabled || status !== "pending";

  return (
    <section
      aria-label="Private context consent request"
      className="agent-confirmation-card agent-confirmation-risk-moderate"
    >
      <header className="agent-card-header">
        <span className="agent-card-icon" aria-hidden="true">
          <ShieldQuestion size={18} />
        </span>
        <div>
          <strong>Allow private context for this response?</strong>
          <small>{statusLabel(status)}</small>
        </div>
      </header>

      <p className="agent-card-summary">
        Abby wants to use private wallet context before answering: {reason}
      </p>

      <ul className="agent-card-detail-list" aria-label="Private context Abby may use">
        {requestedCategories.map((category) => {
          const detail = privateContextCategoryDetails[category];
          const Icon = detail.Icon;
          return (
            <li key={category}>
              <Icon aria-hidden="true" size={14} />
              <span>
                <strong>{detail.label}:</strong> {detail.description}
              </span>
            </li>
          );
        })}
      </ul>

      <p className="agent-card-summary">
        This permission is only for this response. It does not share data, write wallet records, or change recipient
        access.
      </p>

      {expiresAt ? <p className="agent-card-summary">Request expires {formatDateTime(expiresAt)}.</p> : null}

      <div className="agent-card-actions">
        <Button
          ariaLabel="Allow Abby to use private context for this response"
          disabled={actionsDisabled || !onAllow}
          onClick={() => onAllow?.(buildDecision(requestId, reason, requestedCategories, true))}
          variant="primary"
        >
          <Check aria-hidden="true" size={16} />
          <span>Allow once</span>
        </Button>
        <Button
          ariaLabel="Do not allow Abby to use private context"
          disabled={actionsDisabled || !onDeny}
          onClick={() => onDeny?.(buildDecision(requestId, reason, requestedCategories, false))}
          variant="secondary"
        >
          <X aria-hidden="true" size={16} />
          <span>Keep private</span>
        </Button>
      </div>
    </section>
  );
}

function normalizeCategories(categories: readonly PrivateContextConsentCategory[]): PrivateContextConsentCategory[] {
  const requested = categories.filter((category, index) => categories.indexOf(category) === index);
  return requested.length ? requested : [...PRIVATE_CONTEXT_CONSENT_CATEGORIES];
}

function buildDecision(
  requestId: string,
  reason: string,
  categories: readonly PrivateContextConsentCategory[],
  allowed: boolean
): PrivateContextConsentDecision {
  return {
    requestId,
    allowed,
    categories: [...categories],
    scope: "single_response",
    reason
  };
}

function statusLabel(status: PrivateContextConsentStatus): string {
  if (status === "allowed") return "Allowed for one response";
  if (status === "denied") return "Private context kept out";
  return "Consent required";
}

function formatDateTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString(undefined, {
    dateStyle: "short",
    timeStyle: "short"
  });
}
