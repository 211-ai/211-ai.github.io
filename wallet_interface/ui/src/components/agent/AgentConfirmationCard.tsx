import { AlertTriangle, Check, Clock, ShieldAlert, X } from "lucide-react";
import type { AgentConfirmationRequest, AgentToolCall } from "../../agent/types";
import { Button } from "../ui";

export interface AgentConfirmationCardProps {
  confirmation: AgentConfirmationRequest;
  toolCall?: AgentToolCall;
  disabled?: boolean;
  onConfirm: (confirmationId: string) => void;
  onCancel: (confirmationId: string) => void;
}

export function AgentConfirmationCard({
  confirmation,
  toolCall,
  disabled = false,
  onConfirm,
  onCancel
}: AgentConfirmationCardProps) {
  const summary = summarizeChange(confirmation, toolCall);
  const isPending = confirmation.status === "pending";
  const actionsDisabled = disabled || !isPending;
  const Icon = confirmation.risk === "restricted" || confirmation.risk === "high" ? ShieldAlert : AlertTriangle;

  return (
    <section
      aria-label={`Confirmation required: ${confirmation.title}`}
      className={`agent-confirmation-card agent-confirmation-risk-${confirmation.risk}`}
    >
      <header className="agent-card-header">
        <span className="agent-card-icon" aria-hidden="true">
          <Icon size={18} />
        </span>
        <div>
          <strong>{confirmation.title}</strong>
          <small>{riskLabel(confirmation.risk)} action</small>
        </div>
      </header>

      <p className="agent-card-summary">{confirmation.summary}</p>

      <dl className="agent-change-summary">
        <div>
          <dt>Before</dt>
          <dd>{summary.before}</dd>
        </div>
        <div>
          <dt>After</dt>
          <dd>{summary.after}</dd>
        </div>
      </dl>

      {summary.details.length ? (
        <ul className="agent-card-detail-list" aria-label="Action details">
          {summary.details.map((detail) => (
            <li key={detail}>{detail}</li>
          ))}
        </ul>
      ) : null}

      {confirmation.expiresAt ? (
        <div className="agent-card-deadline">
          <Clock aria-hidden="true" size={14} />
          <span>Expires {formatDateTime(confirmation.expiresAt)}</span>
        </div>
      ) : null}

      <div className="agent-card-actions">
        <Button
          ariaLabel={`Confirm ${confirmation.title}`}
          disabled={actionsDisabled}
          onClick={() => onConfirm(confirmation.id)}
          variant="primary"
        >
          <Check aria-hidden="true" size={16} />
          <span>Confirm</span>
        </Button>
        <Button
          ariaLabel={`Cancel ${confirmation.title}`}
          disabled={actionsDisabled}
          onClick={() => onCancel(confirmation.id)}
          variant="secondary"
        >
          <X aria-hidden="true" size={16} />
          <span>Cancel</span>
        </Button>
      </div>
    </section>
  );
}

interface ChangeSummary {
  before: string;
  after: string;
  details: string[];
}

function summarizeChange(confirmation: AgentConfirmationRequest, toolCall?: AgentToolCall): ChangeSummary {
  const input = getConfirmationInput(confirmation, toolCall);
  const toolName = toolCall?.name;

  if (toolName === "save_service" && isRecord(input)) {
    const serviceId = readString(input.serviceId, "selected service");
    return {
      before: "The service is not added by this action yet.",
      after: `Service ${serviceId} will be saved to the wallet-backed service list.`,
      details: readString(input.note) ? ["A note will be saved with the service."] : []
    };
  }

  if (toolName === "create_service_plan" && isRecord(input)) {
    const serviceId = readString(input.serviceId, "selected service");
    return {
      before: "No new follow-up plan exists for this request.",
      after: `A private follow-up plan will be created for ${serviceId}.`,
      details: summarizeNamedFields(input, ["goal", "steps"])
    };
  }

  if (toolName === "update_registration_draft" && isRecord(input)) {
    const fields = summarizeChangedFieldNames(input);
    return {
      before: "The registration draft remains unchanged.",
      after: fields.length ? `Registration fields will be updated: ${fields.join(", ")}.` : "Registration fields will be updated.",
      details: []
    };
  }

  if (toolName === "update_check_in_policy" && isRecord(input)) {
    const fields = summarizeChangedFieldNames(input);
    return {
      before: "The current check-in reminder policy remains active.",
      after: fields.length ? `Check-in settings will change: ${fields.join(", ")}.` : "Check-in settings will be updated.",
      details: []
    };
  }

  if ((toolName === "set_disclosure_scopes" || toolName === "update_recipient_scopes") && isRecord(input)) {
    return {
      before: "The recipient keeps the current sharing scopes.",
      after: `Recipient ${readString(input.recipientId, "selected recipient")} will be limited to the selected scopes.`,
      details: Array.isArray(input.allowedScopes) ? [`Scopes: ${input.allowedScopes.map(formatValue).join(", ")}`] : []
    };
  }

  if (toolName === "add_recipient" && isRecord(input)) {
    return {
      before: "This recipient is not saved in contacts.",
      after: `${readString(input.displayName, "The recipient")} will be added with the selected sharing scopes.`,
      details: Array.isArray(input.allowedScopes) ? [`Scopes: ${input.allowedScopes.map(formatValue).join(", ")}`] : []
    };
  }

  if (toolName === "edit_recipient" && isRecord(input)) {
    return {
      before: "The recipient keeps the current contact and sharing details.",
      after: `Recipient ${readString(input.recipientId, "selected recipient")} will be updated.`,
      details: summarizeChangedFieldNames(input).filter((field) => field !== "recipientId")
    };
  }

  if (toolName === "remove_recipient" && isRecord(input)) {
    return {
      before: "The recipient remains in contacts.",
      after: `Recipient ${readString(input.recipientId, "selected recipient")} will be removed.`,
      details: readString(input.reason) ? ["A reason will be recorded."] : []
    };
  }

  if (toolName === "request_shelter_contact" && isRecord(input)) {
    return {
      before: "No new shelter contact request is created.",
      after: `A contact request will be sent to ${readString(input.shelterName, "the selected shelter")}.`,
      details: []
    };
  }

  if (toolName === "approve_shelter_contact_request" || toolName === "deny_shelter_contact_request") {
    const verb = toolName === "approve_shelter_contact_request" ? "approved" : "denied";
    return {
      before: "The shelter contact request remains pending.",
      after: `Shelter contact request ${readString(isRecord(input) ? input.requestId : undefined, "selected request")} will be ${verb}.`,
      details: isRecord(input) && readString(input.reason) ? ["A reason will be recorded."] : []
    };
  }

  if (toolName === "approve_access_request" || toolName === "reject_access_request" || toolName === "revoke_access_request") {
    const verb =
      toolName === "approve_access_request" ? "approved" : toolName === "reject_access_request" ? "rejected" : "revoked";
    return {
      before: "The access request keeps its current status.",
      after: `Access request ${readString(isRecord(input) ? input.requestId : undefined, "selected request")} will be ${verb}.`,
      details: isRecord(input) && readString(input.reason) ? ["A reason will be recorded."] : []
    };
  }

  if (toolName === "record_controller_approval" && isRecord(input)) {
    return {
      before: "No additional controller approval is recorded by this action.",
      after: `An approval will be recorded for request ${readString(input.requestId, "selected request")}.`,
      details: []
    };
  }

  if (toolName === "analyze_granted_record" || toolName === "view_granted_record" || toolName === "delegate_grant") {
    return {
      before: "The active grant is not used until you confirm.",
      after: grantAfterSummary(toolName, input),
      details: isRecord(input) ? summarizeNamedFields(input, ["recordId", "mode", "purpose", "expiresAt"]) : []
    };
  }

  if (toolName === "create_location_region_proof" && isRecord(input)) {
    return {
      before: "No new location-region proof is created.",
      after: `A proof will be created for ${readString(input.regionLabel, "the selected region")}.`,
      details: summarizeNamedFields(input, ["claim", "verifier", "witnessLabel", "recordId"])
    };
  }

  if (toolName === "create_proof" && isRecord(input)) {
    return {
      before: "No proof request is staged.",
      after: `A proof will be staged for ${readString(input.claim, "the selected claim")}.`,
      details: summarizeNamedFields(input, ["claim", "verifier", "witnessLabel", "proofType", "recordId"])
    };
  }

  if (toolName === "create_verified_export_bundle" && isRecord(input)) {
    const recordCount = Array.isArray(input.recordIds) ? input.recordIds.length : 0;
    const proofCount = Array.isArray(input.proofIds) ? input.proofIds.length : 0;
    return {
      before: "No export bundle is created or shared.",
      after: `An export bundle will be prepared for ${readString(input.audienceName, "the selected audience")}.`,
      details: [
        recordCount ? `${recordCount} record${recordCount === 1 ? "" : "s"} included.` : "",
        proofCount ? `${proofCount} proof${proofCount === 1 ? "" : "s"} included.` : ""
      ].filter(Boolean)
    };
  }

  if (toolName === "import_export_bundle" && isRecord(input)) {
    return {
      before: "No export bundle descriptors are imported.",
      after: `Export bundle ${readString(input.bundleId, "from provided bundle data")} will be imported.`,
      details: summarizeNamedFields(input, ["bundleId", "audienceName"])
    };
  }

  if (toolName === "save_wallet_snapshot") {
    return {
      before: "No wallet backup is saved.",
      after: "An encrypted wallet snapshot will be saved.",
      details: isRecord(input) ? summarizeNamedFields(input, ["reason"]) : []
    };
  }

  if (toolName === "restore_wallet_snapshot") {
    return {
      before: "The current wallet state is not changed.",
      after: "The wallet will load the selected encrypted snapshot.",
      details: isRecord(input) ? summarizeNamedFields(input, ["walletId", "snapshotHash", "reason"]) : []
    };
  }

  return {
    before: "No wallet or app changes are applied until you confirm.",
    after: confirmation.summary,
    details: []
  };
}

function grantAfterSummary(toolName: string, input: unknown): string {
  const grantId = readString(isRecord(input) ? input.grantId ?? input.receiptId : undefined, "selected grant");
  if (toolName === "view_granted_record") return `A record covered by ${grantId} will be opened.`;
  if (toolName === "delegate_grant") return `Access from ${grantId} will be delegated to the selected audience.`;
  return `A permitted analysis will run against a record covered by ${grantId}.`;
}

function getConfirmationInput(confirmation: AgentConfirmationRequest, toolCall?: AgentToolCall): unknown {
  if (toolCall) return toolCall.input;
  const detailsInput = confirmation.details?.input;
  return detailsInput;
}

function summarizeNamedFields(input: Record<string, unknown>, fields: string[]): string[] {
  return fields
    .filter((field) => input[field] !== undefined)
    .map((field) => `${formatFieldName(field)}: ${formatValue(input[field])}`);
}

function summarizeChangedFieldNames(input: Record<string, unknown>): string[] {
  return Object.keys(input)
    .filter((key) => input[key] !== undefined)
    .map(formatFieldName);
}

function formatFieldName(value: string): string {
  return value
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replace(/[_-]+/g, " ")
    .toLowerCase();
}

function formatValue(value: unknown): string {
  if (Array.isArray(value)) return value.map(formatValue).join(", ");
  if (typeof value === "boolean") return value ? "on" : "off";
  if (typeof value === "number") return String(value);
  if (typeof value === "string") return value.trim() || "blank";
  return "set";
}

function readString(value: unknown, fallback = ""): string {
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}

function riskLabel(risk: AgentConfirmationRequest["risk"]): string {
  if (risk === "restricted") return "Restricted";
  if (risk === "high") return "High-risk";
  if (risk === "moderate") return "Moderate-risk";
  return "Low-risk";
}

function formatDateTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString(undefined, {
    dateStyle: "short",
    timeStyle: "short"
  });
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
