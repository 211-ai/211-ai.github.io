import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { RefreshCw, ShieldCheck, UserCheck } from "lucide-react";
import { IDKitRequestWidget, proofOfHuman, type IDKitResult } from "@worldcoin/idkit";
import { Badge, Button, StatusBanner } from "./ui";
import { readRuntimeWorldIdConfig } from "../lib/runtimeConfig";
import {
  createWorldIdRpSignature,
  isWorldIdWalletApiError,
  loadWorldIdConfig as fetchWorldIdConfig,
  loadWorldIdStatus,
  registerWorldIdVerification,
  type WalletApiConfig
} from "../../services/walletApi";

const IDKitErrorCodes = {
  Cancelled: "cancelled",
  CredentialUnavailable: "credential_unavailable",
  DuplicateNonce: "duplicate_nonce",
  FailedByHostApp: "failed_by_host_app",
  IdentityAttributesNotMatched: "identity_attributes_not_matched",
  InvalidRpSignature: "invalid_rp_signature",
  InvalidTimestamp: "invalid_timestamp",
  NullifierReplayed: "nullifier_replayed",
  RpSignatureExpired: "rp_signature_expired",
  TimestampTooOld: "timestamp_too_old",
  UserRejected: "user_rejected",
  WorldId3NotAvailable: "world_id_3_not_available",
  WorldId4NotAvailable: "world_id_4_not_available"
} as const;

type IDKitErrorCode = (typeof IDKitErrorCodes)[keyof typeof IDKitErrorCodes];
type RpContext = {
  created_at: number;
  expires_at: number;
  nonce: string;
  rp_id: string;
  signature: string;
};

type WorldIdEnvironment = "production" | "staging";
type WorldIdAppId = `app_${string}`;

type WorldIdPublicConfig = {
  enabled: boolean;
  appId?: string;
  rpId?: string;
  action: string;
  environment: WorldIdEnvironment;
  credentialPolicy: string;
  allowLegacyProofs: boolean;
  requireUserPresence: boolean;
  disabledReason?: string;
};

type WorldIdStatusView = {
  verified: boolean;
  bindingId?: string;
  proofId?: string;
  verifiedAt?: string;
  action?: string;
  credentialPolicy?: string;
  activeBindingCount?: number;
};

type ActiveIdkitRequest = {
  appId: WorldIdAppId;
  action: string;
  signal: string;
  environment: WorldIdEnvironment;
  allowLegacyProofs: boolean;
  requireUserPresence: boolean;
  rpContext: RpContext;
};

type PanelPhase =
  | "idle"
  | "loading"
  | "ready"
  | "requesting_signature"
  | "idkit"
  | "verifying"
  | "refreshing"
  | "verified"
  | "cancelled"
  | "credential_unavailable"
  | "rp_expired"
  | "replay"
  | "backend_failure"
  | "disabled";

type PanelIssue = {
  phase: PanelPhase;
  tone: "info" | "success" | "warning" | "danger";
  message: string;
  source: "idkit" | "backend" | "signature" | "config" | "user";
};

export function WorldIdVerificationPanel({
  apiConfig,
  onAuditRefresh,
  onProofsRefresh
}: {
  apiConfig?: WalletApiConfig;
  onAuditRefresh?: () => Promise<void> | void;
  onProofsRefresh?: () => Promise<void> | void;
}) {
  const runtimeConfig = useMemo(() => readRuntimeWorldIdConfig(), []);
  const [worldIdConfig, setWorldIdConfig] = useState<WorldIdPublicConfig>(() =>
    configFromRuntime(runtimeConfig)
  );
  const [worldIdStatus, setWorldIdStatus] = useState<WorldIdStatusView | null>(null);
  const [phase, setPhase] = useState<PanelPhase>("idle");
  const [issue, setIssue] = useState<PanelIssue | null>(null);
  const [widgetOpen, setWidgetOpen] = useState(false);
  const [activeRequest, setActiveRequest] = useState<ActiveIdkitRequest | null>(null);
  const idkitSettledRef = useRef(false);
  const backendIssueRef = useRef<PanelIssue | null>(null);

  const statusTone = worldIdStatus?.verified ? "success" : worldIdConfig.enabled ? "warning" : "neutral";
  const statusLabel = worldIdStatus?.verified
    ? "World ID verified"
    : worldIdConfig.enabled
      ? "Not verified"
      : "Unavailable";
  const canStartVerification = Boolean(
    apiConfig?.apiBaseUrl &&
      apiConfig.walletId &&
      apiConfig.actorDid &&
      worldIdConfig.enabled &&
      worldIdConfig.appId &&
      worldIdConfig.rpId &&
      worldIdConfig.action &&
      !["loading", "requesting_signature", "idkit", "verifying", "refreshing"].includes(phase)
  );
  const disabledDetail = getDisabledDetail(apiConfig, worldIdConfig);
  const actionLabel = worldIdStatus?.action || worldIdConfig.action;
  const credentialLabel = worldIdStatus?.credentialPolicy || worldIdConfig.credentialPolicy;

  const refreshWorldIdStatus = useCallback(async (): Promise<WorldIdStatusView | null> => {
    if (!apiConfig?.actorDid) {
      setWorldIdStatus(null);
      return null;
    }
    const payload = await loadWorldIdStatus(apiConfig);
    const nextStatus = normalizeStatus(payload);
    setWorldIdStatus(nextStatus);
    return nextStatus;
  }, [apiConfig?.actorDid, apiConfig?.apiBaseUrl, apiConfig?.walletId]);

  const loadWorldIdConfig = useCallback(async (): Promise<WorldIdPublicConfig> => {
    if (!apiConfig) {
      const nextConfig = configFromRuntime(runtimeConfig);
      setWorldIdConfig(nextConfig);
      return nextConfig;
    }
    const payload = await fetchWorldIdConfig(apiConfig);
    const nextConfig = normalizeConfig(payload, runtimeConfig);
    setWorldIdConfig(nextConfig);
    return nextConfig;
  }, [apiConfig?.apiBaseUrl, apiConfig?.walletId, runtimeConfig]);

  useEffect(() => {
    let cancelled = false;

    if (!apiConfig) {
      setWorldIdConfig(configFromRuntime(runtimeConfig));
      setWorldIdStatus(null);
      setPhase(runtimeConfig.enabled ? "ready" : "disabled");
      setIssue(null);
      return () => {
        cancelled = true;
      };
    }

    setPhase("loading");
    setIssue(null);
    loadWorldIdConfig()
      .then((nextConfig) => {
        if (cancelled) return;
        if (!nextConfig.enabled) {
          setWorldIdStatus(null);
          setPhase("disabled");
          return;
        }
        setPhase("ready");
        if (apiConfig.actorDid) {
          void refreshWorldIdStatus().catch((error) => {
            if (!cancelled) {
              setIssue(classifyBackendIssue(error, "World ID status could not be refreshed."));
            }
          });
        }
      })
      .catch((error) => {
        if (cancelled) return;
        setWorldIdStatus(null);
        setPhase("backend_failure");
        setIssue(classifyBackendIssue(error, "World ID configuration is unavailable."));
      });

    return () => {
      cancelled = true;
    };
  }, [apiConfig, loadWorldIdConfig, refreshWorldIdStatus, runtimeConfig]);

  async function beginVerification() {
    if (!apiConfig?.actorDid || !canStartVerification) return;
    setPhase("requesting_signature");
    setIssue(null);
    setActiveRequest(null);
    idkitSettledRef.current = false;
    backendIssueRef.current = null;

    try {
      const latestConfig = await loadWorldIdConfig();
      if (!latestConfig.enabled) {
        setPhase("disabled");
        setIssue({
          phase: "disabled",
          tone: "warning",
          message: "World ID is disabled for this wallet.",
          source: "config"
        });
        return;
      }

      const payload = await createWorldIdRpSignature(apiConfig, { action: latestConfig.action });
      const request = normalizeSignature(payload, latestConfig, apiConfig);
      if (request.rpContext.expires_at <= Math.floor(Date.now() / 1000) + 5) {
        const nextIssue: PanelIssue = {
          phase: "rp_expired",
          tone: "warning",
          message: "The World ID request expired before it could open. Try again for a fresh request.",
          source: "signature"
        };
        setPhase(nextIssue.phase);
        setIssue(nextIssue);
        return;
      }

      setActiveRequest(request);
      setPhase("idkit");
      setWidgetOpen(true);
    } catch (error) {
      const nextIssue = classifySignatureIssue(error);
      setPhase(nextIssue.phase);
      setIssue(nextIssue);
    }
  }

  const verifyWithBackend = useCallback(
    async (result: IDKitResult): Promise<void> => {
      if (!apiConfig?.actorDid || !activeRequest) {
        const nextIssue: PanelIssue = {
          phase: "backend_failure",
          tone: "danger",
          message: "World ID verification could not be linked to this wallet session.",
          source: "backend"
        };
        backendIssueRef.current = nextIssue;
        setPhase(nextIssue.phase);
        setIssue(nextIssue);
        throw new Error(nextIssue.message);
      }

      setPhase("verifying");
      try {
        await registerWorldIdVerification(apiConfig, {
          idkitPayload: result as unknown as Record<string, unknown>
        });
        setPhase("refreshing");
        await Promise.all([
          Promise.resolve(onProofsRefresh?.()),
          Promise.resolve(onAuditRefresh?.()),
          refreshWorldIdStatus()
        ]);
        backendIssueRef.current = null;
        setIssue({
          phase: "verified",
          tone: "success",
          message: "World ID proof-of-human is now bound to this wallet.",
          source: "backend"
        });
        setPhase("verified");
      } catch (error) {
        const nextIssue = classifyBackendIssue(error, "World ID verification failed.");
        backendIssueRef.current = nextIssue;
        setIssue(nextIssue);
        setPhase(nextIssue.phase);
        throw new Error(nextIssue.message);
      }
    },
    [activeRequest, apiConfig, onAuditRefresh, onProofsRefresh, refreshWorldIdStatus]
  );

  const handleIdkitSuccess = useCallback(() => {
    idkitSettledRef.current = true;
    backendIssueRef.current = null;
    setWidgetOpen(false);
    setActiveRequest(null);
    setPhase("verified");
  }, []);

  const handleIdkitError = useCallback((errorCode: IDKitErrorCode) => {
    idkitSettledRef.current = true;
    setWidgetOpen(false);
    setActiveRequest(null);
    const backendIssue = backendIssueRef.current;
    if (errorCode === IDKitErrorCodes.FailedByHostApp && backendIssue) {
      setPhase(backendIssue.phase);
      setIssue(backendIssue);
      return;
    }
    const nextIssue = classifyIdkitIssue(errorCode);
    setIssue(nextIssue);
    setPhase(nextIssue.phase);
  }, []);

  function handleOpenChange(nextOpen: boolean) {
    if (nextOpen) {
      setWidgetOpen(true);
      return;
    }
    if (!idkitSettledRef.current && phase === "idkit") {
      const g = globalThis as typeof globalThis & { __abbyEnableWorldIdPanelTest?: boolean };
      if (g.__abbyEnableWorldIdPanelTest === true) {
        // IDKit may close while the opted-in Playwright harness is preparing its
        // simulated result. Preserve only that test request until the hook runs.
        setWidgetOpen(false);
        return;
      }
      const nextIssue: PanelIssue = {
        phase: "cancelled",
        tone: "info",
        message: "World ID verification was cancelled before a proof was returned.",
        source: "user"
      };
      setIssue(nextIssue);
      setPhase(nextIssue.phase);
      setActiveRequest(null);
    }
    setWidgetOpen(false);
  }

  // Expose test hooks only when Playwright explicitly opts in.
  useEffect(() => {
    if (!activeRequest) return;
    type WorldIdPanelTestHook = {
      simulateSuccess: (result: IDKitResult) => Promise<void>;
      simulateError: (errorCode: string) => void;
    };
    const g = globalThis as typeof globalThis & {
      __abbyEnableWorldIdPanelTest?: boolean;
      __abbyWorldIdPanelTest?: WorldIdPanelTestHook;
    };
    if (g.__abbyEnableWorldIdPanelTest !== true) return;
    g.__abbyWorldIdPanelTest = {
      // Capture the active request's handlers. IDKit may transiently clear its
      // open state after this explicit test hook is armed.
      simulateSuccess: verifyWithBackend,
      simulateError: (errorCode: string) => handleIdkitError(errorCode as IDKitErrorCode)
    };
  }, [activeRequest, handleIdkitError, verifyWithBackend]);

  useEffect(() => {
    return () => {
      const g = globalThis as typeof globalThis & { __abbyWorldIdPanelTest?: unknown };
      delete g.__abbyWorldIdPanelTest;
    };
  }, []);

  return (
    <article className="world-id-panel proof-card" aria-label="World ID verification">
      <div className="scope-header">
        <div className="world-id-title">
          <span className="world-id-mark" aria-hidden="true">
            <UserCheck size={22} />
          </span>
          <div>
            <h3>World ID verification</h3>
            <p>Proof-of-human wallet binding</p>
          </div>
        </div>
        <Badge tone={statusTone}>{statusLabel}</Badge>
      </div>

      {issue ? <StatusBanner tone={issue.tone}>{issue.message}</StatusBanner> : null}
      {!issue && phase === "loading" ? <StatusBanner tone="info">Checking World ID wallet status.</StatusBanner> : null}
      {!issue && disabledDetail ? <StatusBanner tone="warning">{disabledDetail}</StatusBanner> : null}

      <div className="world-id-status-grid">
        <div className="world-id-status-item">
          <small>Wallet</small>
          <strong>{apiConfig?.walletId ?? "Not connected"}</strong>
        </div>
        <div className="world-id-status-item">
          <small>Action</small>
          <strong>{actionLabel}</strong>
        </div>
        <div className="world-id-status-item">
          <small>Credential</small>
          <strong>{formatCredentialPolicy(credentialLabel)}</strong>
        </div>
        <div className="world-id-status-item">
          <small>Status</small>
          <strong>{formatStatusDetail(worldIdStatus, phase)}</strong>
        </div>
      </div>

      <div className="disclosure-package world-id-disclosure">
        <div className="disclosure-row">
          <strong>Public claim</strong>
          <span>World ID proof-of-human is bound to this wallet</span>
        </div>
        <div className="disclosure-row">
          <strong>Not a claim</strong>
          <span>Legal name, age, citizenship, address, or document possession</span>
        </div>
        <div className="disclosure-row">
          <strong>Private</strong>
          <span>Raw nullifier, IDKit proof payload, RP signature, Developer Portal response</span>
        </div>
      </div>

      <div className="world-id-actions">
        <Button
          disabled={!canStartVerification}
          loading={["requesting_signature", "idkit", "verifying", "refreshing"].includes(phase)}
          loadingLabel={loadingLabelForPhase(phase)}
          onClick={() => void beginVerification()}
        >
          <ShieldCheck aria-hidden="true" size={18} /> Verify with World ID
        </Button>
        <Button
          disabled={!apiConfig || phase === "loading" || phase === "refreshing"}
          onClick={() => {
            setIssue(null);
            setPhase("loading");
            void Promise.all([loadWorldIdConfig(), refreshWorldIdStatus()])
              .then(([nextConfig]) => setPhase(nextConfig.enabled ? "ready" : "disabled"))
              .catch((error) => {
                const nextIssue = classifyBackendIssue(error, "World ID status could not be refreshed.");
                setIssue(nextIssue);
                setPhase(nextIssue.phase);
              });
          }}
          variant="secondary"
        >
          <RefreshCw aria-hidden="true" size={18} /> Refresh status
        </Button>
      </div>

      {activeRequest ? (
        <IDKitRequestWidget
          open={widgetOpen}
          onOpenChange={handleOpenChange}
          app_id={activeRequest.appId}
          action={activeRequest.action}
          rp_context={activeRequest.rpContext}
          allow_legacy_proofs={activeRequest.allowLegacyProofs}
          require_user_presence={activeRequest.requireUserPresence}
          environment={activeRequest.environment}
          return_to={typeof window !== "undefined" ? window.location.href : undefined}
          preset={proofOfHuman({ signal: activeRequest.signal })}
          handleVerify={verifyWithBackend}
          onSuccess={handleIdkitSuccess}
          onError={(errorCode) => handleIdkitError(String(errorCode) as IDKitErrorCode)}
        />
      ) : null}
    </article>
  );
}

function configFromRuntime(runtimeConfig: ReturnType<typeof readRuntimeWorldIdConfig>): WorldIdPublicConfig {
  return {
    enabled: runtimeConfig.enabled,
    appId: runtimeConfig.appId,
    action: runtimeConfig.action,
    environment: normalizeEnvironment(runtimeConfig.environment),
    credentialPolicy: "proof_of_human",
    allowLegacyProofs: true,
    requireUserPresence: false,
    disabledReason: runtimeConfig.disabledReason
  };
}

function normalizeConfig(payload: unknown, runtimeConfig: ReturnType<typeof readRuntimeWorldIdConfig>): WorldIdPublicConfig {
  const record = asRecord(payload);
  // Once a wallet API is configured, its public response is authoritative.
  // Never fill a missing backend app ID from browser build-time configuration.
  const enabled = readBoolean(record, "enabled") ?? false;
  const appId = readString(record, "app_id", "appId");
  const action =
    readString(record, "default_action", "defaultAction", "action") || runtimeConfig.action || "wallet-attach-world-id-v1";
  const environment = normalizeEnvironment(readString(record, "environment") || runtimeConfig.environment);
  return {
    enabled,
    appId,
    rpId: readString(record, "rp_id", "rpId"),
    action,
    environment,
    credentialPolicy: readString(record, "credential_policy", "credentialPolicy") || "proof_of_human",
    allowLegacyProofs: readBoolean(record, "allow_legacy_proofs", "allowLegacyProofs") ?? true,
    requireUserPresence: readBoolean(record, "require_user_presence", "requireUserPresence") ?? false,
    disabledReason: readString(record, "disabled_reason", "disabledReason") ?? runtimeConfig.disabledReason
  };
}

function normalizeStatus(payload: unknown): WorldIdStatusView {
  const record = asRecord(payload);
  const wallet = asRecord(record.wallet);
  const binding = asOptionalRecord(record.binding) ?? asOptionalRecord(record.active_binding) ?? {};
  const activeBindingCount =
    readNumber(wallet, "active_binding_count", "activeBindingCount") ??
    readNumber(record, "active_binding_count", "activeBindingCount");
  const verified =
    readBoolean(record, "verified") ??
    readBoolean(binding, "verified") ??
    (typeof activeBindingCount === "number" ? activeBindingCount > 0 : readString(binding, "status") === "active");
  return {
    verified,
    bindingId: readString(record, "binding_id", "bindingId") ?? readString(binding, "binding_id", "bindingId"),
    proofId:
      readString(record, "proof_id", "proofId") ??
      readString(binding, "proof_id", "proofId", "proof_receipt_id", "proofReceiptId"),
    verifiedAt: readString(record, "verified_at", "verifiedAt") ?? readString(binding, "verified_at", "verifiedAt"),
    action: readString(record, "action") ?? readString(binding, "action"),
    credentialPolicy:
      readString(record, "credential_policy", "credentialPolicy") ??
      readString(binding, "credential_policy", "credentialPolicy"),
    activeBindingCount
  };
}

function normalizeSignature(payload: unknown, config: WorldIdPublicConfig, apiConfig: WalletApiConfig): ActiveIdkitRequest {
  const record = asRecord(payload);
  const rpContextRecord = asRecord(record.rp_context) || record;
  const appId = readString(record, "app_id", "appId") || config.appId;
  const rpId = readString(rpContextRecord, "rp_id", "rpId") || readString(record, "rp_id", "rpId") || config.rpId;
  const signature =
    readString(rpContextRecord, "signature", "sig") || readString(record, "signature", "sig");
  const nonce = readString(rpContextRecord, "nonce") || readString(record, "nonce");
  const createdAt =
    readNumber(rpContextRecord, "created_at", "createdAt") ?? readNumber(record, "created_at", "createdAt");
  const expiresAt =
    readNumber(rpContextRecord, "expires_at", "expiresAt") ?? readNumber(record, "expires_at", "expiresAt");

  if (!appId || !appId.startsWith("app_")) {
    throw new Error("World ID app ID is missing from the backend response.");
  }
  if (!rpId || !signature || !nonce || !createdAt || !expiresAt) {
    throw new Error("World ID RP signature response is incomplete.");
  }

  return {
    appId: appId as WorldIdAppId,
    action: readString(record, "action") || config.action,
    signal:
      readString(record, "signal") ||
      `211-ai:wallet-world-id:v1:${apiConfig.walletId}:${apiConfig.actorDid || "unknown-actor"}`,
    environment: normalizeEnvironment(readString(record, "environment") || config.environment),
    allowLegacyProofs: readBoolean(record, "allow_legacy_proofs", "allowLegacyProofs") ?? config.allowLegacyProofs,
    requireUserPresence:
      readBoolean(record, "require_user_presence", "requireUserPresence") ?? config.requireUserPresence,
    rpContext: {
      rp_id: rpId,
      nonce,
      created_at: createdAt,
      expires_at: expiresAt,
      signature
    }
  };
}

function classifyIdkitIssue(errorCode: IDKitErrorCode): PanelIssue {
  if (errorCode === IDKitErrorCodes.Cancelled || errorCode === IDKitErrorCodes.UserRejected) {
    return {
      phase: "cancelled",
      tone: "info",
      message: "World ID verification was cancelled before a proof was returned.",
      source: "idkit"
    };
  }
  if (
    errorCode === IDKitErrorCodes.CredentialUnavailable ||
    errorCode === IDKitErrorCodes.WorldId4NotAvailable ||
    errorCode === IDKitErrorCodes.WorldId3NotAvailable ||
    errorCode === IDKitErrorCodes.IdentityAttributesNotMatched
  ) {
    return {
      phase: "credential_unavailable",
      tone: "warning",
      message: "The requested World ID proof-of-human credential is unavailable for this account.",
      source: "idkit"
    };
  }
  if (
    errorCode === IDKitErrorCodes.RpSignatureExpired ||
    errorCode === IDKitErrorCodes.TimestampTooOld ||
    errorCode === IDKitErrorCodes.InvalidRpSignature ||
    errorCode === IDKitErrorCodes.InvalidTimestamp
  ) {
    return {
      phase: "rp_expired",
      tone: "warning",
      message: "The World ID request expired or was rejected by the relying-party signature check.",
      source: "idkit"
    };
  }
  if (errorCode === IDKitErrorCodes.NullifierReplayed || errorCode === IDKitErrorCodes.DuplicateNonce) {
    return {
      phase: "replay",
      tone: "warning",
      message: "This World ID proof has already been used for another active wallet binding.",
      source: "idkit"
    };
  }
  return {
    phase: "backend_failure",
    tone: "danger",
    message: "World ID verification could not be completed. The wallet was not updated.",
    source: "idkit"
  };
}

function classifySignatureIssue(error: unknown): PanelIssue {
  const detail = errorMessage(error);
  if (looksExpired(detail)) {
    return {
      phase: "rp_expired",
      tone: "warning",
      message: "The World ID request expired before IDKit opened. Try again for a fresh request.",
      source: "signature"
    };
  }
  return {
    phase: "backend_failure",
    tone: "danger",
    message: detail || "A fresh World ID request could not be created.",
    source: "signature"
  };
}

function classifyBackendIssue(error: unknown, fallback: string): PanelIssue {
  const detail = errorMessage(error) || fallback;
  if (isWorldIdWalletApiError(error) && error.status === 409) {
    return {
      phase: "replay",
      tone: "warning",
      message: "This World ID proof is already bound to another wallet.",
      source: "backend"
    };
  }
  if (looksReplay(detail)) {
    return {
      phase: "replay",
      tone: "warning",
      message: "This World ID proof has already been used for another active wallet binding.",
      source: "backend"
    };
  }
  if (looksExpired(detail)) {
    return {
      phase: "rp_expired",
      tone: "warning",
      message: "The World ID request expired. Start again to request a fresh RP signature.",
      source: "backend"
    };
  }
  if (looksCredentialUnavailable(detail)) {
    return {
      phase: "credential_unavailable",
      tone: "warning",
      message: "The requested World ID proof-of-human credential is unavailable for this account.",
      source: "backend"
    };
  }
  return {
    phase: "backend_failure",
    tone: "danger",
    message: detail,
    source: "backend"
  };
}

function getDisabledDetail(apiConfig: WalletApiConfig | undefined, config: WorldIdPublicConfig): string {
  if (!apiConfig) return "Connect the wallet API before starting World ID verification.";
  if (!apiConfig.actorDid) return "An actor DID is required before starting World ID verification.";
  if (!config.enabled) return formatRuntimeDisabledReason(config.disabledReason);
  if (!config.appId || !config.rpId) return "World ID app configuration is missing.";
  return "";
}

function formatRuntimeDisabledReason(reason: string | undefined): string {
  if (reason === "missing_app_id") return "World ID is unavailable because the public app ID is missing.";
  if (reason === "missing_action") return "World ID is unavailable because the action is missing.";
  return "World ID is disabled for this wallet.";
}

function formatCredentialPolicy(value: string | undefined): string {
  return (value || "proof_of_human").replace(/_/g, " ");
}

function formatStatusDetail(status: WorldIdStatusView | null, phase: PanelPhase): string {
  if (phase === "requesting_signature") return "requesting signature";
  if (phase === "idkit") return "waiting for IDKit";
  if (phase === "verifying") return "checking proof";
  if (phase === "refreshing") return "refreshing wallet";
  if (status?.verified) return status.verifiedAt ? `verified ${formatDate(status.verifiedAt)}` : "verified";
  if (typeof status?.activeBindingCount === "number") return `${status.activeBindingCount} active bindings`;
  return "not verified";
}

function loadingLabelForPhase(phase: PanelPhase): string {
  if (phase === "requesting_signature") return "Requesting signature";
  if (phase === "verifying") return "Checking proof";
  if (phase === "refreshing") return "Refreshing wallet";
  return "Opening IDKit";
}

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

function errorMessage(error: unknown): string {
  if (error instanceof Error) return error.message;
  return typeof error === "string" ? error : "";
}

function looksReplay(value: string): boolean {
  return /replay|reused|nullifier|conflict|already bound/i.test(value);
}

function looksExpired(value: string): boolean {
  return /expired|expiry|rp_signature_expired|timestamp_too_old|signature.*old/i.test(value);
}

function looksCredentialUnavailable(value: string): boolean {
  return /credential.*unavailable|world_id_4_not_available|world_id_3_not_available|identity.*not.*matched/i.test(value);
}

function normalizeEnvironment(value: string | undefined): WorldIdEnvironment {
  return value === "production" ? "production" : "staging";
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

function asOptionalRecord(value: unknown): Record<string, unknown> | undefined {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : undefined;
}

function readString(record: Record<string, unknown>, ...keys: string[]): string | undefined {
  for (const key of keys) {
    const value = record[key];
    if (typeof value === "string" && value.trim()) return value.trim();
  }
  return undefined;
}

function readBoolean(record: Record<string, unknown>, ...keys: string[]): boolean | undefined {
  for (const key of keys) {
    const value = record[key];
    if (typeof value === "boolean") return value;
    if (typeof value === "string") {
      const normalized = value.trim().toLowerCase();
      if (["1", "true", "yes", "on"].includes(normalized)) return true;
      if (["0", "false", "no", "off"].includes(normalized)) return false;
    }
  }
  return undefined;
}

function readNumber(record: Record<string, unknown>, ...keys: string[]): number | undefined {
  for (const key of keys) {
    const value = record[key];
    if (typeof value === "number" && Number.isFinite(value)) return value;
    if (typeof value === "string" && value.trim()) {
      const parsed = Number(value);
      if (Number.isFinite(parsed)) return parsed;
      const timestamp = Date.parse(value);
      if (Number.isFinite(timestamp)) return Math.floor(timestamp / 1000);
    }
  }
  return undefined;
}
