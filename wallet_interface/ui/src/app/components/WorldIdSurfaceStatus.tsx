import { useEffect, useState } from "react";
import { Badge } from "../../components/ui";
import { WorldIdVerificationPanel } from "../../components/world-id/WorldIdVerificationPanel";
import { loadWalletWorldIdStatus, type WalletApiConfig, type WorldIdWalletStatus } from "../../services/walletApi";
import { StatusPanel } from "./StatusPanel";

type FlexibleWorldIdWalletStatus = WorldIdWalletStatus & {
  active_binding_count?: number;
  verified?: boolean;
};

type WorldIdSurfacePhase = "checking" | "verified" | "unverified" | "failed";

export function WorldIdSurfaceStatus({
  apiConfig,
  ariaLabel,
  onAuditRefresh,
  onProofsRefresh
}: {
  apiConfig?: WalletApiConfig;
  ariaLabel: string;
  onAuditRefresh?: () => Promise<void> | void;
  onProofsRefresh?: () => Promise<void> | void;
}) {
  const [phase, setPhase] = useState<WorldIdSurfacePhase>(apiConfig?.actorDid ? "checking" : "unverified");

  useEffect(() => {
    let cancelled = false;

    if (!apiConfig?.actorDid) {
      setPhase("unverified");
      return () => {
        cancelled = true;
      };
    }

    setPhase("checking");
    void loadWalletWorldIdStatus(apiConfig)
      .then((status) => {
        if (!cancelled) {
          setPhase(isWorldIdVerified(status as FlexibleWorldIdWalletStatus) ? "verified" : "unverified");
        }
      })
      .catch(() => {
        if (!cancelled) setPhase("failed");
      });

    return () => {
      cancelled = true;
    };
  }, [apiConfig]);

  const hasActorDid = Boolean(apiConfig?.actorDid);
  const verified = phase === "verified";
  const statusLabel = verified ? "World ID verified" : "World ID unverified";
  const badgeLabel = hasActorDid ? (verified ? "verified" : phase === "checking" ? "checking" : "not verified") : statusLabel;
  const detailLabel = !apiConfig
    ? "Wallet API required"
    : !apiConfig.actorDid
      ? "Actor DID required"
      : phase === "checking"
        ? "Checking status"
        : phase === "failed"
          ? "Status unavailable"
          : verified
            ? "Ready"
            : "Proof-of-human not verified";

  return (
    <section aria-label={ariaLabel} className="world-id-surface">
      <article className="world-id-surface-summary">
        <div className="scope-header">
          <div>
            <h2>{verified ? "Verified proof-of-human" : "Proof-of-human status"}</h2>
            <p className="world-id-surface-copy">
              Emergency and essential-service flows remain available even when World ID is unavailable or not verified.
              World ID proof-of-human does not disclose or prove legal name, age, citizenship, address, or document possession.
            </p>
          </div>
          <Badge tone={verified ? "success" : hasActorDid ? "warning" : "neutral"}>{badgeLabel}</Badge>
        </div>
        <div className="world-id-surface-facts">
          <StatusPanel label="Wallet" value={apiConfig?.walletId ?? "Not connected"} tone={hasActorDid ? "teal" : "gold"} />
          <StatusPanel label="Proof" value={verified ? "Bound to wallet" : "Not verified"} tone={verified ? "teal" : "gold"} />
          <StatusPanel label="Setup" value={detailLabel} tone={verified ? "teal" : hasActorDid ? "gold" : "rose"} />
        </div>
      </article>
      {hasActorDid ? (
        <WorldIdVerificationPanel apiConfig={apiConfig} onAuditRefresh={onAuditRefresh} onProofsRefresh={onProofsRefresh} />
      ) : null}
    </section>
  );
}

function isWorldIdVerified(status: FlexibleWorldIdWalletStatus): boolean {
  if (typeof status.verified === "boolean") return status.verified;
  if (typeof status.active_binding_count === "number") return status.active_binding_count > 0;
  if (typeof status.wallet?.active_binding_count === "number") return status.wallet.active_binding_count > 0;
  return false;
}