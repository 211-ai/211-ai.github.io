import { useEffect, useState } from "react";
import { Badge, Button, Card, Section, StatusBanner } from "../../shared/components/ui";
import type { WalletApiConfig } from "../../features/wallet/lib/walletApi";
import { listHmisSyncTimeline } from "../../features/wallet/lib/walletApi";

interface HmisSyncTimelineProps {
  apiConfig?: WalletApiConfig;
  localRef?: string;
}

export function HmisSyncTimeline({ apiConfig, localRef }: HmisSyncTimelineProps) {
  const [events, setEvents] = useState<Array<Record<string, unknown>>>([]);
  const [error, setError] = useState("");

  async function refresh() {
    if (!apiConfig) return;
    try {
      const result = await listHmisSyncTimeline(apiConfig, { localRef });
      setEvents(result.events ?? []);
      setError("");
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Failed to load HMIS sync timeline.");
    }
  }

  useEffect(() => {
    void refresh();
  }, [apiConfig, localRef]);

  return (
    <Section
      actions={
        <Button onClick={() => void refresh()} variant="secondary">
          Refresh
        </Button>
      }
      title="HMIS sync timeline"
      eyebrow="Phase 4 · Submission history"
    >
      {error ? <StatusBanner tone="warning">{error}</StatusBanner> : null}
      <div className="list-stack">
        {events.map((event) => (
          <Card key={String(event.event_id ?? event.local_ref ?? Math.random())} title={String(event.action_type ?? "HMIS event")}>
            <div className="badge-row">
              <Badge tone="info">{String(event.status ?? "pending")}</Badge>
              <Badge>{String(event.adapter_name ?? "adapter")}</Badge>
            </div>
            <small className="upload-machine-summary">{String(event.response_summary ?? "No summary available")}</small>
            <small className="upload-machine-summary">{String(event.occurred_at ?? "")}</small>
          </Card>
        ))}
      </div>
    </Section>
  );
}
