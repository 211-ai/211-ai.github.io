import { useEffect, useState } from "react";
import { Archive, KeyRound, LockKeyhole, RefreshCw, ShieldCheck } from "lucide-react";
import { Badge, Button, Section, StatusBanner } from "../../components/ui";
import {
  listWalletSnapshots,
  loadWalletSnapshot,
  saveWalletSnapshot,
  verifyWalletSnapshot,
  type WalletApiConfig,
  type WalletSnapshotVerification
} from "../../features/wallet/lib/walletApi";

function shortHash(value?: string): string {
  if (!value) return "Unavailable";
  return value.length > 24 ? `${value.slice(0, 12)}...${value.slice(-8)}` : value;
}

export function AccountSafetySection({
  apiConfig,
  onSnapshotLoaded
}: {
  apiConfig?: WalletApiConfig;
  onSnapshotLoaded: () => Promise<void> | void;
}) {
  const [snapshotIds, setSnapshotIds] = useState<string[]>([]);
  const [snapshotStatus, setSnapshotStatus] = useState<"idle" | "saving" | "saved" | "loading" | "loaded" | "failed">(
    "idle"
  );
  const [snapshotReport, setSnapshotReport] = useState<WalletSnapshotVerification | null>(null);
  const hasCurrentSnapshot = Boolean(apiConfig && snapshotIds.includes(apiConfig.walletId));

  async function refreshSnapshotState(): Promise<string[]> {
    if (!apiConfig) return [];
    const ids = await listWalletSnapshots(apiConfig);
    setSnapshotIds(ids);
    if (ids.includes(apiConfig.walletId)) {
      setSnapshotReport(await verifyWalletSnapshot(apiConfig));
    } else {
      setSnapshotReport(null);
    }
    return ids;
  }

  useEffect(() => {
    if (!apiConfig) return;
    let cancelled = false;
    refreshSnapshotState()
      .then(() => undefined)
      .catch(() => {
        if (!cancelled) {
          setSnapshotReport(null);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [apiConfig?.actorDid, apiConfig?.apiBaseUrl, apiConfig?.walletId]);

  async function saveSnapshot() {
    if (!apiConfig) return;
    setSnapshotStatus("saving");
    try {
      await saveWalletSnapshot(apiConfig);
      await refreshSnapshotState();
      setSnapshotStatus("saved");
    } catch {
      setSnapshotStatus("failed");
    }
  }

  async function restoreSnapshot() {
    if (!apiConfig || !hasCurrentSnapshot) return;
    setSnapshotStatus("loading");
    try {
      await loadWalletSnapshot(apiConfig);
      setSnapshotReport(await verifyWalletSnapshot(apiConfig));
      await onSnapshotLoaded();
      setSnapshotStatus("loaded");
    } catch {
      setSnapshotStatus("failed");
    }
  }

  return (
    <Section
      title="Account safety"
      actions={
        <Badge tone={hasCurrentSnapshot ? "success" : "warning"}>{hasCurrentSnapshot ? "backup ready" : "no backup"}</Badge>
      }
    >
      {!apiConfig ? (
        <StatusBanner tone="warning">Connect Abby to save and load wallet backups.</StatusBanner>
      ) : null}
      {snapshotStatus === "saved" ? <StatusBanner tone="success">Wallet backup saved.</StatusBanner> : null}
      {snapshotStatus === "loaded" ? <StatusBanner tone="success">Wallet backup loaded.</StatusBanner> : null}
      {snapshotStatus === "failed" ? <StatusBanner tone="warning">Wallet backup action failed.</StatusBanner> : null}
      <div className="disclosure-package">
        <div className="disclosure-row">
          <strong>Wallet</strong>
          <span>{apiConfig?.walletId ?? "Not connected"}</span>
        </div>
        <div className="disclosure-row">
          <strong>Backups</strong>
          <span>{snapshotIds.length}</span>
        </div>
        <div className="disclosure-row">
          <strong>Backup place</strong>
          <span>{apiConfig ? "backup store" : "API required"}</span>
        </div>
        <div className="disclosure-row">
          <strong>Backup check</strong>
          <span>{snapshotReport ? (snapshotReport.valid ? "verified" : "failed") : "not checked"}</span>
        </div>
        <div className="disclosure-row">
          <strong>Backup code</strong>
          <span>{snapshotReport?.computed_hash ? <code>{shortHash(snapshotReport.computed_hash)}</code> : "Unavailable"}</span>
        </div>
      </div>
      <div className="row-actions">
        <Button disabled={!apiConfig || snapshotStatus === "saving" || snapshotStatus === "loading"} onClick={saveSnapshot}>
          <Archive size={18} /> {snapshotStatus === "saving" ? "Saving" : "Save backup"}
        </Button>
        <Button
          disabled={!apiConfig || !hasCurrentSnapshot || snapshotStatus === "saving" || snapshotStatus === "loading"}
          onClick={restoreSnapshot}
          variant="secondary"
        >
          <RefreshCw size={18} /> {snapshotStatus === "loading" ? "Loading" : "Load backup"}
        </Button>
      </div>
      <div className="tool-grid">
        <button className="tool-tile" type="button">
          <LockKeyhole size={24} /> Session timeout
        </button>
        <button className="tool-tile" type="button">
          <KeyRound size={24} /> Recovery settings
        </button>
        <button className="tool-tile" type="button">
          <ShieldCheck size={24} /> Bot check settings
        </button>
      </div>
    </Section>
  );
}
