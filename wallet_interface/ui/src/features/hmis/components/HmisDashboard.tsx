import { useEffect, useState } from "react";
import { Badge, Button, Card, Section, StatusBanner } from "../../../shared/components/ui";
import type { WalletApiConfig } from "../../wallet/lib/walletApi";
import {
  listHmisEnrollmentDrafts,
  listHmisReconciliationQueue,
  listHmisSyncTimeline,
  retryHmisReconciliationItem,
} from "../../wallet/lib/walletApi";

interface HmisDashboardProps {
  apiConfig?: WalletApiConfig;
}

function statusTone(
  status: string,
): "neutral" | "success" | "warning" | "danger" | "info" {
  if (["submitted", "success", "resolved", "active"].includes(status)) return "success";
  if (["draft", "pending", "ready"].includes(status)) return "neutral";
  if (["retryable", "open"].includes(status)) return "warning";
  if (["needs_review", "error", "failed"].includes(status)) return "danger";
  return "info";
}

export function HmisDashboard({ apiConfig }: HmisDashboardProps) {
  const [reconciliationItems, setReconciliationItems] = useState<
    Array<Record<string, unknown>>
  >([]);
  const [enrollmentDrafts, setEnrollmentDrafts] = useState<
    Array<Record<string, unknown>>
  >([]);
  const [timelineEvents, setTimelineEvents] = useState<
    Array<Record<string, unknown>>
  >([]);
  const [error, setError] = useState("");
  const [retryingItemId, setRetryingItemId] = useState("");
  const [loading, setLoading] = useState(false);

  async function refresh() {
    if (!apiConfig) return;
    setLoading(true);
    setError("");
    try {
      const [queueResult, enrollmentsResult, timelineResult] = await Promise.all([
        listHmisReconciliationQueue(apiConfig),
        listHmisEnrollmentDrafts(apiConfig),
        listHmisSyncTimeline(apiConfig),
      ]);
      setReconciliationItems(queueResult.items ?? []);
      setEnrollmentDrafts(enrollmentsResult.enrollmentDrafts ?? []);
      setTimelineEvents((timelineResult.events ?? []).slice(0, 20));
    } catch (nextError) {
      setError(
        nextError instanceof Error
          ? nextError.message
          : "Failed to load HMIS dashboard.",
      );
    } finally {
      setLoading(false);
    }
  }

  async function retryItem(itemId: string) {
    if (!apiConfig) return;
    setRetryingItemId(itemId);
    try {
      await retryHmisReconciliationItem(apiConfig, itemId);
      await refresh();
    } catch (nextError) {
      setError(
        nextError instanceof Error
          ? nextError.message
          : "Failed to retry reconciliation item.",
      );
    } finally {
      setRetryingItemId("");
    }
  }

  useEffect(() => {
    void refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiConfig]);

  const openItems = reconciliationItems.filter(
    (item) => item.status === "open" || item.status === "retryable",
  );
  const needsReviewItems = reconciliationItems.filter(
    (item) => item.status === "needs_review",
  );

  return (
    <Section
      actions={
        <Button loading={loading} onClick={() => void refresh()} variant="secondary">
          Refresh dashboard
        </Button>
      }
      eyebrow="Phase 5 · Operational overview"
      title="HMIS operational dashboard"
    >
      {error ? <StatusBanner tone="warning">{error}</StatusBanner> : null}

      {/* Summary counters */}
      <div className="chip-grid" aria-label="HMIS dashboard summary">
        <Card title="Reconciliation queue">
          <div className="badge-row">
            <Badge tone={openItems.length > 0 ? "warning" : "success"}>
              {openItems.length} open
            </Badge>
            <Badge tone={needsReviewItems.length > 0 ? "danger" : "neutral"}>
              {needsReviewItems.length} needs review
            </Badge>
          </div>
        </Card>
        <Card title="Enrollment drafts">
          <div className="badge-row">
            <Badge tone="info">
              {
                enrollmentDrafts.filter((d) => d.status === "submitted").length
              }{" "}
              submitted
            </Badge>
            <Badge>
              {
                enrollmentDrafts.filter((d) => d.status === "ready").length
              }{" "}
              ready
            </Badge>
          </div>
        </Card>
        <Card title="Recent sync events">
          <div className="badge-row">
            <Badge tone="info">{timelineEvents.length} events</Badge>
          </div>
        </Card>
      </div>

      {/* Reconciliation items needing attention */}
      {reconciliationItems.length > 0 ? (
        <Section eyebrow="Reconciliation" title="Items needing attention">
          <div className="list-stack">
            {reconciliationItems.map((item) => {
              const itemId = String(item.item_id ?? "");
              const itemStatus = String(item.status ?? "open");
              return (
                <Card
                  actions={
                    itemStatus === "open" || itemStatus === "retryable" ? (
                      <Button
                        loading={retryingItemId === itemId}
                        onClick={() => void retryItem(itemId)}
                        variant="secondary"
                      >
                        Retry
                      </Button>
                    ) : undefined
                  }
                  key={itemId}
                  title={String(item.local_ref ?? itemId)}
                >
                  <div className="badge-row">
                    <Badge tone={statusTone(itemStatus)}>{itemStatus}</Badge>
                    <Badge>{String(item.retry_count ?? 0)} retries</Badge>
                  </div>
                  <small className="upload-machine-summary">
                    {String(item.reason ?? item.last_error ?? "")}
                  </small>
                </Card>
              );
            })}
          </div>
        </Section>
      ) : null}

      {/* Enrollment drafts */}
      {enrollmentDrafts.length > 0 ? (
        <Section eyebrow="Enrollment" title="Enrollment drafts">
          <div className="list-stack">
            {enrollmentDrafts.map((draft) => {
              const draftId = String(draft.enrollment_draft_id ?? "");
              const draftStatus = String(draft.status ?? "draft");
              return (
                <Card key={draftId} title={draftId}>
                  <div className="badge-row">
                    <Badge tone={statusTone(draftStatus)}>{draftStatus}</Badge>
                    {draft.destination_program_ref ? (
                      <Badge>{String(draft.destination_program_ref)}</Badge>
                    ) : null}
                  </div>
                  <small className="upload-machine-summary">
                    {String(draft.local_subject_ref ?? "")}
                  </small>
                </Card>
              );
            })}
          </div>
        </Section>
      ) : null}

      {/* Recent timeline events */}
      {timelineEvents.length > 0 ? (
        <Section eyebrow="Audit" title="Recent sync events">
          <div className="list-stack">
            {timelineEvents.map((event) => {
              const eventId = String(event.event_id ?? "");
              const eventStatus = String(event.status ?? "");
              return (
                <Card key={eventId} title={String(event.action_type ?? eventId)}>
                  <div className="badge-row">
                    <Badge tone={statusTone(eventStatus)}>{eventStatus}</Badge>
                    <Badge>{String(event.actor_id ?? "")}</Badge>
                  </div>
                  <small className="upload-machine-summary">
                    {String(event.response_summary ?? "")}
                  </small>
                </Card>
              );
            })}
          </div>
        </Section>
      ) : null}
    </Section>
  );
}
