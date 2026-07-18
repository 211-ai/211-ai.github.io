import { useState } from "react";
import { Badge, Button, Card, Field, Section, StatusBanner } from "../../shared/components/ui";
import type { WalletApiConfig } from "../../features/wallet/lib/walletApi";
import {
  createHmisEnrollmentDraft,
  submitHmisEnrollmentDraft,
} from "../../features/wallet/lib/walletApi";

interface HmisEnrollmentDraftPanelProps {
  apiConfig?: WalletApiConfig;
  destinationProgramRef?: string;
  localSubjectRef?: string;
}

export function HmisEnrollmentDraftPanel({
  apiConfig,
  destinationProgramRef = "",
  localSubjectRef = "",
}: HmisEnrollmentDraftPanelProps) {
  const [draftId, setDraftId] = useState("");
  const [entryDate, setEntryDate] = useState("");
  const [householdRef, setHouseholdRef] = useState("");
  const [summary, setSummary] = useState("Client enrolling in program.");
  const [status, setStatus] = useState("draft");
  const [errors, setErrors] = useState<string[]>([]);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  async function createDraft() {
    if (!apiConfig) return;
    setLoading(true);
    try {
      const result = await createHmisEnrollmentDraft(apiConfig, {
        localSubjectRef,
        destinationProgramRef,
        entryDate: entryDate || undefined,
        householdRef: householdRef || undefined,
        summary,
      });
      const nextDraft = result.enrollmentDraft ?? result.raw;
      setDraftId(String(nextDraft.enrollment_draft_id ?? ""));
      setStatus(String(nextDraft.status ?? result.status ?? "draft"));
      setErrors(
        Array.isArray(nextDraft.validation_errors)
          ? nextDraft.validation_errors.map(String)
          : [],
      );
      setMessage(result.summary ?? "Created HMIS enrollment draft.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Failed to create enrollment draft.");
    } finally {
      setLoading(false);
    }
  }

  async function submitDraft() {
    if (!apiConfig || !draftId) return;
    setLoading(true);
    try {
      const result = await submitHmisEnrollmentDraft(apiConfig, draftId);
      setStatus(result.status ?? "submitted");
      setMessage(result.summary ?? "Submitted HMIS enrollment draft.");
      setErrors([]);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Failed to submit enrollment draft.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Section title="HMIS enrollment draft" eyebrow="Phase 5 · Enrollment and program updates">
      {message ? (
        <StatusBanner tone={errors.length ? "warning" : "info"}>{message}</StatusBanner>
      ) : null}
      <div className="form-grid">
        <Field label="Local subject reference">
          <input readOnly value={localSubjectRef} />
        </Field>
        <Field label="Destination program reference">
          <input readOnly value={destinationProgramRef} />
        </Field>
        <Field label="Entry date">
          <input
            onChange={(event) => setEntryDate(event.target.value)}
            placeholder="YYYY-MM-DD"
            type="date"
            value={entryDate}
          />
        </Field>
        <Field label="Household reference (optional)">
          <input
            onChange={(event) => setHouseholdRef(event.target.value)}
            value={householdRef}
          />
        </Field>
        <Field label="Enrollment summary">
          <textarea
            onChange={(event) => setSummary(event.target.value)}
            rows={3}
            value={summary}
          />
        </Field>
      </div>
      <div className="row-actions">
        <Button loading={loading} onClick={() => void createDraft()} variant="secondary">
          Create enrollment draft
        </Button>
        <Button
          disabled={!draftId || status !== "ready"}
          onClick={() => void submitDraft()}
        >
          Submit enrollment
        </Button>
      </div>
      <Card title="Enrollment draft status">
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
          <small className="upload-machine-summary">
            Validation errors will appear here before submission.
          </small>
        )}
      </Card>
    </Section>
  );
}
