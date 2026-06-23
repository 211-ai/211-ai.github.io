import { useCallback, useEffect, type Dispatch, type SetStateAction } from "react";
import {
  listWalletAuditEvents,
  listWalletDocuments,
  listWalletProofReceipts,
  listWalletSavedServices,
  listWalletServiceInteractions,
  listWalletServicePlans,
  loadExportBundleView,
  loadWalletAccessState,
  loadWalletDetails,
  type WalletApiConfig,
} from "../../services/walletApi";
import {
  auditEvents,
  initialAccessRequests,
  initialGrantReceipts,
  initialUploads,
  proofReceipts,
} from "../../services/mockAbbyService";
import type {
  AuditEvent,
  ExportBundleView,
  ProofReceiptView,
  SavedService,
  ServiceInteractionEvent,
  ServicePlan,
  UploadItem,
  WalletAccessRequest,
  WalletGrantReceipt,
} from "../../models/abby";

interface WalletSyncSetters {
  setAccessRequests: Dispatch<SetStateAction<WalletAccessRequest[]>>;
  setExportBundleViews: Dispatch<SetStateAction<ExportBundleView[]>>;
  setGrantReceipts: Dispatch<SetStateAction<WalletGrantReceipt[]>>;
  setSavedServices: Dispatch<SetStateAction<SavedService[]>>;
  setServiceInteractions: Dispatch<SetStateAction<ServiceInteractionEvent[]>>;
  setServicePlans: Dispatch<SetStateAction<ServicePlan[]>>;
  setUploads: Dispatch<SetStateAction<UploadItem[]>>;
  setWalletActorResolved: (resolved: boolean) => void;
  setWalletAuditEvents: Dispatch<SetStateAction<AuditEvent[]>>;
  setWalletPortalError: (error: string) => void;
  setWalletPortalLoading: (loading: boolean) => void;
  setWalletProofReceipts: Dispatch<SetStateAction<ProofReceiptView[]>>;
}

export interface WalletSyncResult {
  refreshWalletAccessState: () => Promise<void>;
  refreshWalletAfterSnapshotLoad: () => Promise<void>;
  refreshWalletAuditEvents: () => Promise<void>;
  refreshWalletPortalState: () => Promise<void>;
}

export function useWalletSync(
  walletApiConfig: WalletApiConfig | undefined,
  persistWalletApiConfig: (config: WalletApiConfig) => void,
  setters: WalletSyncSetters
): WalletSyncResult {
  const {
    setAccessRequests,
    setExportBundleViews,
    setGrantReceipts,
    setSavedServices,
    setServiceInteractions,
    setServicePlans,
    setUploads,
    setWalletActorResolved,
    setWalletAuditEvents,
    setWalletPortalError,
    setWalletPortalLoading,
    setWalletProofReceipts,
  } = setters;

  const refreshWalletAuditEvents = useCallback(async () => {
    if (!walletApiConfig) return;
    const events = await listWalletAuditEvents(walletApiConfig);
    setWalletAuditEvents(events);
  }, [walletApiConfig, setWalletAuditEvents]);

  const refreshWalletDocuments = useCallback(async () => {
    if (!walletApiConfig) return;
    const documents = await listWalletDocuments(walletApiConfig);
    setUploads(documents);
  }, [walletApiConfig, setUploads]);

  const refreshWalletProofReceipts = useCallback(async () => {
    if (!walletApiConfig) return;
    const proofs = await listWalletProofReceipts(walletApiConfig);
    setWalletProofReceipts(proofs);
  }, [walletApiConfig, setWalletProofReceipts]);

  const refreshWalletPortalState = useCallback(async () => {
    if (!walletApiConfig) return;
    setWalletPortalLoading(true);
    setWalletPortalError("");
    try {
      const [nextSavedServices, nextServicePlans, nextServiceInteractions] = await Promise.all([
        listWalletSavedServices(walletApiConfig),
        listWalletServicePlans(walletApiConfig),
        listWalletServiceInteractions(walletApiConfig),
      ]);
      setSavedServices(nextSavedServices);
      setServicePlans(nextServicePlans);
      setServiceInteractions(nextServiceInteractions);
    } catch (error) {
      setWalletPortalError(error instanceof Error ? error.message : "Wallet portal state unavailable");
    } finally {
      setWalletPortalLoading(false);
    }
  }, [
    walletApiConfig,
    setWalletPortalLoading,
    setWalletPortalError,
    setSavedServices,
    setServicePlans,
    setServiceInteractions,
  ]);

  const refreshWalletAfterSnapshotLoad = useCallback(async () => {
    if (!walletApiConfig) return;
    await Promise.all([
      refreshWalletAuditEvents().catch(() => setWalletAuditEvents(auditEvents)),
      refreshWalletDocuments().catch(() => setUploads(initialUploads)),
      refreshWalletProofReceipts().catch(() => setWalletProofReceipts(proofReceipts)),
      refreshWalletPortalState(),
    ]);
  }, [
    walletApiConfig,
    refreshWalletAuditEvents,
    refreshWalletDocuments,
    refreshWalletProofReceipts,
    refreshWalletPortalState,
    setWalletAuditEvents,
    setUploads,
    setWalletProofReceipts,
  ]);

  const refreshWalletAccessState = useCallback(async () => {
    if (!walletApiConfig) return;
    const state = await loadWalletAccessState(walletApiConfig);
    setAccessRequests(state.accessRequests.length ? state.accessRequests : initialAccessRequests);
    setGrantReceipts(state.grantReceipts.length ? state.grantReceipts : initialGrantReceipts);
  }, [walletApiConfig, setAccessRequests, setGrantReceipts]);

  // Resolve wallet actor DID when config changes
  useEffect(() => {
    if (!walletApiConfig) {
      setWalletActorResolved(false);
      return;
    }
    let cancelled = false;
    setWalletActorResolved(false);
    void loadWalletDetails({
      apiBaseUrl: walletApiConfig.apiBaseUrl,
      walletId: walletApiConfig.walletId,
    })
      .then((wallet) => {
        if (cancelled) return;
        const ownerDid = wallet.owner_did.trim();
        if (ownerDid && ownerDid !== walletApiConfig.actorDid) {
          persistWalletApiConfig({ ...walletApiConfig, actorDid: ownerDid });
          return;
        }
        setWalletActorResolved(Boolean(ownerDid || walletApiConfig.actorDid));
      })
      .catch(() => {
        if (!cancelled) {
          setWalletActorResolved(Boolean(walletApiConfig.actorDid));
        }
      });
    return () => {
      cancelled = true;
    };
  }, [persistWalletApiConfig, walletApiConfig, setWalletActorResolved]);

  useEffect(() => {
    if (!walletApiConfig) return;
    void refreshWalletDocuments().catch(() => setUploads(initialUploads));
  }, [walletApiConfig]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!walletApiConfig) return;
    void refreshWalletAccessState().catch(() => {
      setAccessRequests(initialAccessRequests);
      setGrantReceipts(initialGrantReceipts);
    });
  }, [walletApiConfig]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!walletApiConfig) return;
    void refreshWalletAuditEvents().catch(() => setWalletAuditEvents(auditEvents));
  }, [walletApiConfig]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!walletApiConfig) return;
    void refreshWalletProofReceipts().catch(() => setWalletProofReceipts(proofReceipts));
  }, [walletApiConfig]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!walletApiConfig) return;
    void refreshWalletPortalState();
  }, [walletApiConfig]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!walletApiConfig) return;
    const demoBundleJson = import.meta.env.VITE_DEMO_EXPORT_BUNDLE_JSON as string | undefined;
    if (!demoBundleJson) return;

    try {
      const bundle = JSON.parse(demoBundleJson);
      loadExportBundleView({
        apiBaseUrl: walletApiConfig.apiBaseUrl,
        bundle,
        imported: true,
      })
        .then((bundleView) => {
          setExportBundleViews((current) =>
            current.some((item) => item.id === bundleView.id) ? current : [bundleView, ...current]
          );
        })
        .catch(() => undefined);
    } catch {
      // Ignore malformed optional demo data and keep the static bundle examples.
    }
  }, [walletApiConfig]); // eslint-disable-line react-hooks/exhaustive-deps

  return {
    refreshWalletAccessState,
    refreshWalletAfterSnapshotLoad,
    refreshWalletAuditEvents,
    refreshWalletPortalState,
  };
}
