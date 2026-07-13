import { useState } from "react";
import { KeyRound, LockKeyhole, ShieldCheck, Share2 } from "lucide-react";
import { Badge, Button, Field, Section, StatusBanner } from "../../../components/ui";
import {
  type DecryptedRecordView,
  type DisclosureRecipientDraft,
  type WalletAccessRequest,
  type WalletGrantReceipt
} from "../../../models/abby";
import {
  analyzeRecordFormRedactedWithGrant,
  analyzeRecordRedactedWithGrant,
  analyzeRecordWithGrant,
  approveAccessRequest,
  approveThresholdApproval,
  createRecordVectorProfileWithGrant,
  createRedactedGraphRAG,
  decryptRecordWithGrant,
  delegateGrant,
  extractRecordTextRedactedWithGrant,
  issueRecordAnalysisInvocation,
  issueRecordDecryptInvocation,
  rejectAccessRequest,
  revokeAccessRequest,
  type WalletApiConfig
} from "../../../services/walletApi";
import { capabilitySummary, plainCapabilityLabel } from "../../../services/capabilities";
import { SharingCapabilityPreview, SharingScopeChecklist } from "../../../app/components/SharingScopeComponents";
import {
  formatLocalizedCapabilitySummary,
  formatLocalizedNonGrantedCapabilities,
  formatRecipientType,
  formatRequestTimestamp,
  getDisclosureScopeLabels
} from "../../../app/utils/formatHelpers";
import {
  analysisLines,
  artifactLines,
  outputTypeForAnalysisMode,
  receiptHasAbility,
  receiptRequiresUserPresence,
  runDerivedAnalysis,
  summarizeDerivedOutput,
  type RecipientAnalysisMode
} from "../../../app/utils/privacyProfile";

export function RecipientAccessScreen({
  accessRequests,
  apiConfig,
  grantReceipts,
  refreshWalletAccessState,
  refreshWalletAuditEvents,
  setAccessRequests,
  setGrantReceipts,
  verified,
  setVerified
}: {
  accessRequests: WalletAccessRequest[];
  apiConfig?: WalletApiConfig;
  grantReceipts: WalletGrantReceipt[];
  recipients: DisclosureRecipientDraft[];
  refreshWalletAccessState: () => Promise<void>;
  refreshWalletAuditEvents: () => Promise<void>;
  setAccessRequests: (requests: WalletAccessRequest[]) => void;
  setGrantReceipts: (receipts: WalletGrantReceipt[]) => void;
  verified: boolean;
  setVerified: (verified: boolean) => void;
}) {
  const [derivedArtifactsByReceiptId, setDerivedArtifactsByReceiptId] = useState<Record<string, string[]>>({});
  const [decryptedRecordsByReceiptId, setDecryptedRecordsByReceiptId] = useState<Record<string, DecryptedRecordView>>({});
  const [busyActionIds, setBusyActionIds] = useState<string[]>([]);
  const [delegationDrafts, setDelegationDrafts] = useState<Record<string, { audienceDid: string; purpose: string }>>({});
  const [delegationMessages, setDelegationMessages] = useState<Record<string, string>>({});

  async function decideRequest(requestId: string, status: "approved" | "rejected") {
    if (apiConfig?.actorDid) {
      try {
        if (status === "approved") {
          await approveAccessRequest(apiConfig, requestId);
        } else {
          await rejectAccessRequest(apiConfig, requestId);
        }
        await refreshWalletAccessState();
        await refreshWalletAuditEvents();
        return;
      } catch {
        // Keep the local demo path responsive if a configured API is unavailable.
      }
    }
    setAccessRequests(
      accessRequests.map((request) =>
        request.id === requestId
          ? { ...request, status, grantStatus: status === "approved" ? "active" : request.grantStatus }
          : request
      )
    );
  }

  async function recordControllerApproval(request: WalletAccessRequest) {
    if (apiConfig?.actorDid && request.approvalId) {
      try {
        await approveThresholdApproval(apiConfig, request.approvalId);
        await refreshWalletAccessState();
        await refreshWalletAuditEvents();
        return;
      } catch {
        // Keep the local demo path responsive if a configured API is unavailable.
      }
    }
    setAccessRequests(
      accessRequests.map((item) =>
        item.id === request.id
          ? {
              ...item,
              approvalCount: Math.min((item.approvalCount ?? 0) + 1, item.approvalThreshold ?? 1)
            }
          : item
      )
    );
  }

  async function revokeRequest(requestId: string) {
    if (apiConfig?.actorDid) {
      try {
        await revokeAccessRequest(apiConfig, requestId);
        await refreshWalletAccessState();
        await refreshWalletAuditEvents();
        return;
      } catch {
        // Keep the local demo path responsive if a configured API is unavailable.
      }
    }
    setAccessRequests(accessRequests.map((request) => (request.id === requestId ? { ...request, status: "revoked" } : request)));
    setGrantReceipts(grantReceipts.map((receipt) => (receipt.id.includes(requestId) ? { ...receipt, status: "revoked" } : receipt)));
  }

  async function analyzeReceipt(receipt: WalletGrantReceipt, mode: RecipientAnalysisMode) {
    if (!apiConfig?.actorDid || !receipt.recordId) return;
    const actionId = `${receipt.id}:${mode}`;
    setBusyActionIds((ids) => [...ids, actionId]);
    try {
      const outputType = outputTypeForAnalysisMode(mode);
      const invocationToken = receiptRequiresUserPresence(receipt)
        ? await issueRecordAnalysisInvocation(apiConfig, {
            grantId: receipt.grantId,
            outputTypes: [outputType],
            recordId: receipt.recordId,
            userPresent: true
          })
        : undefined;
      const lines =
        mode === "summary"
          ? artifactLines(
              await analyzeRecordWithGrant(apiConfig, {
                grantId: receipt.grantId,
                invocationToken,
                recordId: receipt.recordId
              })
            )
          : analysisLines(
              await runDerivedAnalysis(apiConfig, receipt, mode, invocationToken)
            );
      setDerivedArtifactsByReceiptId((items) => ({ ...items, [receipt.id]: [...(items[receipt.id] ?? []), ...lines] }));
      await refreshWalletAuditEvents().catch(() => undefined);
    } finally {
      setBusyActionIds((ids) => ids.filter((id) => id !== actionId));
    }
  }

  async function viewReceipt(receipt: WalletGrantReceipt) {
    if (!apiConfig?.actorDid || !receipt.recordId) return;
    const actionId = `${receipt.id}:view`;
    setBusyActionIds((ids) => [...ids, actionId]);
    try {
      const invocationToken = receiptRequiresUserPresence(receipt)
        ? await issueRecordDecryptInvocation(apiConfig, {
            grantId: receipt.grantId,
            recordId: receipt.recordId,
            userPresent: true
          })
        : undefined;
      const record = await decryptRecordWithGrant(apiConfig, {
        grantId: receipt.grantId,
        invocationToken,
        recordId: receipt.recordId
      });
      setDecryptedRecordsByReceiptId((records) => ({ ...records, [receipt.id]: record }));
      await refreshWalletAuditEvents().catch(() => undefined);
    } finally {
      setBusyActionIds((ids) => ids.filter((id) => id !== actionId));
    }
  }

  async function delegateReceipt(receipt: WalletGrantReceipt) {
    if (!apiConfig?.actorDid) return;
    const draft = delegationDrafts[receipt.id] ?? { audienceDid: "", purpose: receipt.purpose };
    const audienceDid = draft.audienceDid.trim();
    if (!audienceDid) return;
    const ability = receipt.abilities.includes("record/analyze") || receipt.abilities.includes("*") ? "record/analyze" : receipt.abilities[0];
    const actionId = `${receipt.id}:delegate`;
    setBusyActionIds((ids) => [...ids, actionId]);
    try {
      await delegateGrant(apiConfig, {
        abilities: [ability],
        audienceDid,
        parentGrantId: receipt.grantId,
        purpose: draft.purpose.trim() || receipt.purpose,
        resources: receipt.resources
      });
      setDelegationMessages((messages) => ({ ...messages, [receipt.id]: `Delegated to ${audienceDid}.` }));
      await refreshWalletAccessState();
      await refreshWalletAuditEvents();
    } finally {
      setBusyActionIds((ids) => ids.filter((id) => id !== actionId));
    }
  }

  return (
    <div className="screen">
      <div className="page-title">
        <p className="eyebrow">Recipient access</p>
        <h1>Requests to see my info</h1>
      </div>
      <StatusBanner tone={apiConfig ? "success" : "warning"}>
        {apiConfig ? "Wallet access is connected." : "Connect Abby before acting on live access requests."}
      </StatusBanner>
      <Section title="Safety check">
        <label className="consent-box">
          <input checked={verified} onChange={(event) => setVerified(event.target.checked)} type="checkbox" />
          <span>
            <strong>Confirm I recognize this helper before sharing.</strong>
            <small>Access can be approved, rejected, or revoked later from this screen.</small>
          </span>
        </label>
      </Section>
      <Section title="Access requests">
        <div className="list-stack">
          {accessRequests.length ? (
            accessRequests.map((request) => {
              const needsApproval =
                request.approvalRequired && (request.approvalCount ?? 0) < (request.approvalThreshold ?? 1);
              return (
                <article className="list-item access-request-item" key={request.id}>
                  <div>
                    <h3>{request.requesterName}</h3>
                    <p>{request.resourceLabel}</p>
                    <div className="badge-row">
                      <Badge>{request.status}</Badge>
                      <Badge>{capabilitySummary(request.abilities)}</Badge>
                      {needsApproval ? <Badge tone="warning">controller approval needed</Badge> : null}
                    </div>
                  </div>
                  <div className="row-actions">
                    {needsApproval ? (
                      <Button onClick={() => void recordControllerApproval(request)} variant="secondary">
                        Record approval
                      </Button>
                    ) : null}
                    <Button disabled={!verified} onClick={() => void decideRequest(request.id, "approved")} variant="secondary">
                      Approve
                    </Button>
                    <Button onClick={() => void decideRequest(request.id, "rejected")} variant="danger">
                      Reject
                    </Button>
                    <Button onClick={() => void revokeRequest(request.id)} variant="quiet">
                      Revoke
                    </Button>
                  </div>
                </article>
              );
            })
          ) : (
            <small>No pending access requests.</small>
          )}
        </div>
      </Section>
      <Section title="Shared receipts">
        <div className="list-stack">
          {grantReceipts.length ? (
            grantReceipts.map((receipt) => {
              const draft = delegationDrafts[receipt.id] ?? { audienceDid: "", purpose: receipt.purpose };
              const outputLines = derivedArtifactsByReceiptId[receipt.id] ?? [];
              const decrypted = decryptedRecordsByReceiptId[receipt.id];
              const canAnalyze = receiptHasAbility(receipt, "record/analyze") && receipt.recordId;
              const canView = receiptHasAbility(receipt, "record/decrypt") && receipt.recordId;
              const canDelegate = receiptHasAbility(receipt, "record/share") && receipt.resources.length > 0;

              return (
                <article aria-labelledby={`grant-receipt-${receipt.id}`} className="list-item recipient-list-item" key={receipt.id}>
                  <div className="recipient-summary">
                    <h3 id={`grant-receipt-${receipt.id}`}>{receipt.audienceName}</h3>
                    <p>{receipt.resourceLabel}</p>
                    <div className="badge-row">
                      <Badge tone={receipt.status === "active" ? "success" : "warning"}>{receipt.status}</Badge>
                      <Badge>{receipt.receiptHash}</Badge>
                      <Badge>Share proof code</Badge>
                    </div>
                    <small>{receipt.abilities.map(plainCapabilityLabel).join(", ")}</small>
                  </div>
                  <div className="row-actions">
                    <Button
                      disabled={!canAnalyze || busyActionIds.includes(`${receipt.id}:summary`)}
                      onClick={() => void analyzeReceipt(receipt, "summary")}
                      variant="secondary"
                    >
                      {busyActionIds.includes(`${receipt.id}:summary`) ? "Making summary" : "Make safe summary"}
                    </Button>
                    <Button disabled={!canAnalyze} onClick={() => void analyzeReceipt(receipt, "redacted")} variant="secondary">
                      Redacted analysis
                    </Button>
                    <Button disabled={!canAnalyze} onClick={() => void analyzeReceipt(receipt, "vector")} variant="secondary">
                      Vector profile
                    </Button>
                    <Button disabled={!canAnalyze} onClick={() => void analyzeReceipt(receipt, "extract-text")} variant="secondary">
                      Extract text
                    </Button>
                    <Button disabled={!canAnalyze} onClick={() => void analyzeReceipt(receipt, "form")} variant="secondary">
                      Analyze form
                    </Button>
                    <Button disabled={!canAnalyze} onClick={() => void analyzeReceipt(receipt, "graphrag")} variant="secondary">
                      Build GraphRAG
                    </Button>
                    <Button disabled={!canView} onClick={() => void viewReceipt(receipt)} variant="secondary">
                      View document
                    </Button>
                  </div>
                  {outputLines.length || decrypted ? (
                    <div className="disclosure-package">
                      {outputLines.map((line) => (
                        <div className="disclosure-row" key={line}>
                          <strong>Output</strong>
                          <span>{line}</span>
                        </div>
                      ))}
                      {decrypted ? (
                        <>
                          <div className="disclosure-row">
                            <strong>Document</strong>
                            <span>{decrypted.text}</span>
                          </div>
                          <div className="disclosure-row">
                            <strong>Size</strong>
                            <span>{decrypted.sizeBytes} bytes</span>
                          </div>
                        </>
                      ) : null}
                    </div>
                  ) : null}
                  {canDelegate ? (
                    <form className="delegation-form" onSubmit={(event) => {
                      event.preventDefault();
                      void delegateReceipt(receipt);
                    }}>
                      <Field label="Delegate DID">
                        <input
                          onChange={(event) =>
                            setDelegationDrafts({
                              ...delegationDrafts,
                              [receipt.id]: { ...draft, audienceDid: event.target.value }
                            })
                          }
                          placeholder="did:key:case-worker"
                          value={draft.audienceDid}
                        />
                      </Field>
                      <Field label="Delegated purpose">
                        <input
                          onChange={(event) =>
                            setDelegationDrafts({
                              ...delegationDrafts,
                              [receipt.id]: { ...draft, purpose: event.target.value }
                            })
                          }
                          value={draft.purpose}
                        />
                      </Field>
                      <div className="row-actions">
                        <Button disabled={!draft.audienceDid.trim() || busyActionIds.includes(`${receipt.id}:delegate`)} type="submit">
                          {busyActionIds.includes(`${receipt.id}:delegate`) ? "Delegating" : "Delegate access"}
                        </Button>
                      </div>
                      {delegationMessages[receipt.id] ? <p className="delegation-message">{delegationMessages[receipt.id]}</p> : null}
                    </form>
                  ) : null}
                </article>
              );
            })
          ) : (
            <small>No active grant receipts.</small>
          )}
        </div>
      </Section>
    </div>
  );
}
