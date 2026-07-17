import { useMemo, useState } from "react";
import { Badge, Button, Dialog, Field, StatusBanner } from "../../shared/components/ui";
import type { WalletApiConfig } from "../../features/wallet/lib/walletApi";
import { rejectHmisMatch, verifyHmisMatch } from "../../features/wallet/lib/walletApi";

interface HmisMatchReviewDrawerProps {
  apiConfig?: WalletApiConfig;
  candidates: Array<Record<string, unknown>>;
  entityType: string;
  localRef: string;
  onClose: () => void;
  onDecision?: (decision: Record<string, unknown>) => void;
  open: boolean;
}

export function HmisMatchReviewDrawer({
  apiConfig,
  candidates,
  entityType,
  localRef,
  onClose,
  onDecision,
  open
}: HmisMatchReviewDrawerProps) {
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [rejectReason, setRejectReason] = useState("manual review blocked");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const selectedCandidate = useMemo(() => candidates[selectedIndex] ?? null, [candidates, selectedIndex]);

  async function handleVerify() {
    if (!apiConfig || !selectedCandidate) return;
    setSaving(true);
    setError("");
    try {
      const result = await verifyHmisMatch(apiConfig, {
        entityType,
        localRef,
        externalId: String(selectedCandidate.external_id ?? ""),
        confidence: Number(selectedCandidate.score ?? 0)
      });
      onDecision?.(result.raw);
      onClose();
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "HMIS verification failed.");
    } finally {
      setSaving(false);
    }
  }

  async function handleReject() {
    if (!apiConfig || !selectedCandidate) return;
    setSaving(true);
    setError("");
    try {
      const result = await rejectHmisMatch(apiConfig, {
        entityType,
        localRef,
        externalId: String(selectedCandidate.external_id ?? ""),
        reason: rejectReason
      });
      onDecision?.(result.raw);
      onClose();
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "HMIS rejection failed.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog
      actions={
        <>
          <Button loading={saving} onClick={handleReject} variant="secondary">
            Reject candidate
          </Button>
          <Button loading={saving} onClick={handleVerify}>
            Verify link
          </Button>
        </>
      }
      onClose={onClose}
      open={open}
      title="HMIS match review"
    >
      {error ? <StatusBanner tone="warning">{error}</StatusBanner> : null}
      <div className="chip-grid" aria-label="HMIS candidate selection">
        {candidates.map((candidate, index) => (
          <button className="choice-chip" key={`${String(candidate.external_id ?? index)}`} onClick={() => setSelectedIndex(index)} type="button">
            {String(candidate.name ?? candidate.household_name ?? candidate.external_id ?? `Candidate ${index + 1}`)}
          </button>
        ))}
      </div>
      {selectedCandidate ? (
        <div className="list-stack">
          <div className="badge-row">
            <Badge tone="info">{String(selectedCandidate.status ?? "proposed")}</Badge>
            <Badge tone="success">score {String(selectedCandidate.score ?? "0.00")}</Badge>
          </div>
          <small className="upload-machine-summary">
            Matched fields: {Array.isArray(selectedCandidate.matched_fields) ? selectedCandidate.matched_fields.join(", ") : "n/a"}
          </small>
          <Field label="Rejection reason">
            <textarea onChange={(event) => setRejectReason(event.target.value)} rows={3} value={rejectReason} />
          </Field>
        </div>
      ) : null}
    </Dialog>
  );
}
