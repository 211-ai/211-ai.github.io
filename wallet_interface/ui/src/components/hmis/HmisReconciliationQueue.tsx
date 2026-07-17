import { useEffect, useState } from "react";
import { Badge, Button, Card, Section, StatusBanner } from "../../shared/components/ui";
import type { WalletApiConfig } from "../../features/wallet/lib/walletApi";
import { listHmisReconciliationQueue, retryHmisReconciliationItem } from "../../features/wallet/lib/walletApi";

interface HmisReconciliationQueueProps {
  apiConfig?: WalletApiConfig;
}

export function HmisReconciliationQueue({ apiConfig }: HmisReconciliationQueueProps) {
  const [items, setItems] = useState<Array<Record<string, unknown>>>([]);
  const [error, setError] = useState("");
  const [retryingItemId, setRetryingItemId] = useState("");

  async function refresh() {
    if (!apiConfig) return;
    try {
      const result = await listHmisReconciliationQueue(apiConfig);
      setItems(result.items ?? []);
      setError("");
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Failed to load HMIS reconciliation queue.");
    }
  }

  async function retryItem(itemId: string) {
    if (!apiConfig) return;
    setRetryingItemId(itemId);
    try {
      await retryHmisReconciliationItem(apiConfig, itemId);
      await refresh();
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Failed to retry HMIS reconciliation item.");
    } finally {
      setRetryingItemId("");
    }
  }

  useEffect(() => {
    void refresh();
  }, [apiConfig]);

  return (
    <Section
      actions={
        <Button onClick={() => void refresh()} variant="secondary">
          Refresh queue
        </Button>
      }
      title="HMIS reconciliation queue"
      eyebrow="Phase 4 · Retry and review"
    >
      {error ? <StatusBanner tone="warning">{error}</StatusBanner> : null}
      <div className="list-stack">
        {items.map((item) => {
          const itemId = String(item.item_id ?? "");
          return (
            <Card
              actions={
                <Button loading={retryingItemId === itemId} onClick={() => void retryItem(itemId)} variant="secondary">
                  Retry
                </Button>
              }
              key={itemId}
              title={String(item.local_ref ?? itemId ?? "HMIS reconciliation item")}
            >
              <div className="badge-row">
                <Badge tone="info">{String(item.status ?? "open")}</Badge>
                <Badge>{String(item.retry_count ?? 0)} retries</Badge>
              </div>
              <small className="upload-machine-summary">{String(item.reason ?? item.last_error ?? "Awaiting reconciliation")}</small>
            </Card>
          );
        })}
      </div>
    </Section>
  );
}
