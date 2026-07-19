import { useState } from "react";
import { Badge, Button, Card, Field, Section, StatusBanner } from "../../../shared/components/ui";
import type { WalletApiConfig } from "../../wallet/lib/walletApi";
import {
  createHmisReferralDraft,
  submitHmisReferralDraft,
  updateHmisReferralDraft,
  validateHmisReferralDraft
} from "../../wallet/lib/walletApi";

interface HmisReferralDraftPanelProps {
  apiConfig?: WalletApiConfig;
  destinationProgramRef?: string;
  localSubjectRef?: string;
}

export function HmisReferralDraftPanel({ apiConfig, destinationProgramRef = "", localSubjectRef = "" }: HmisReferralDraftPanelProps) {
  const [draftId, setDraftId] = useState("");
  const [providerName, setProviderName] = useState("Safe Harbor Shelter");
  const [programName, setProgramName] = useState("Emergency Shelter");
  const [summary, setSummary] = useState("Client requests emergency shelter placement.");
  const [status, setStatus] = useState("draft");
  const [errors, setErrors] = useState<string[]>([]);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  async function createDraft() {
    if (!apiConfig) return;
    setLoading(true);
    try {
      const result = await createHmisReferralDraft(apiConfig, {
        localSubjectRef,
        destinationProgramRef,
        providerName,
        programName,
        summary
      });
      const nextDraft = result.referralDraft ?? result.raw;
      setDraftId(String(nextDraft.referral_draft_id ?? ""));
      setStatus(String(nextDraft.status ?? result.status ?? "draft"));
      setErrors([]);
      setMessage(result.summary ?? "Created HMIS referral draft.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Failed to create draft.");
    } finally {
      setLoading(false);
    }
  }

  async function validateDraft() {
    if (!apiConfig || !draftId) return;
    setLoading(true);
    try {
      await updateHmisReferralDraft(apiConfig, draftId, {
        providerName,
        programName,
        summary
      });
      const result = await validateHmisReferralDraft(apiConfig, draftId);
      setStatus(result.status ?? "draft");
      setErrors(Array.isArray(result.raw.errors) ? result.raw.errors.map(String) : []);
      setMessage(result.summary ?? "Validated HMIS referral draft.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Failed to validate draft.");
    } finally {
      setLoading(false);
    }
  }

  async function submitDraft() {
    if (!apiConfig || !draftId) return;
    setLoading(true);
    try {
      const result = await submitHmisReferralDraft(apiConfig, draftId);
      setStatus(result.status ?? "submitted");
      setMessage(result.summary ?? "Submitted HMIS referral draft.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Failed to submit draft.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Section title="HMIS referral draft" eyebrow="Phase 3 · Draft and validation">
      {message ? <StatusBanner tone={errors.length ? "warning" : "info"}>{message}</StatusBanner> : null}
      <div className="form-grid">
        <Field label="Local subject reference">
          <input readOnly value={localSubjectRef} />
        </Field>
        <Field label="Destination program reference">
          <input readOnly value={destinationProgramRef} />
        </Field>
        <Field label="Provider name">
          <input onChange={(event) => setProviderName(event.target.value)} value={providerName} />
        </Field>
        <Field label="Program name">
          <input onChange={(event) => setProgramName(event.target.value)} value={programName} />
        </Field>
        <Field label="Referral summary">
          <textarea onChange={(event) => setSummary(event.target.value)} rows={4} value={summary} />
        </Field>
      </div>
      <div className="row-actions">
        <Button loading={loading} onClick={() => void createDraft()} variant="secondary">
          Create draft
        </Button>
        <Button disabled={!draftId} onClick={() => void validateDraft()} variant="secondary">
          Validate draft
        </Button>
        <Button disabled={!draftId || status !== "ready"} onClick={() => void submitDraft()}>
          Submit draft
        </Button>
      </div>
      <Card title="Draft status">
        <div className="badge-row">
          <Badge tone="info">{status}</Badge>
          {draftId ? <Badge>{draftId}</Badge> : null}
        </div>
        {errors.length ? (
          <ul>
            {errors.map((error) => (
              <li key={error}>{error}</li>
            ))}
          </ul>
        ) : (
          <small className="upload-machine-summary">Validation errors will appear here before submission.</small>
        )}
      </Card>
    </Section>
  );
}
