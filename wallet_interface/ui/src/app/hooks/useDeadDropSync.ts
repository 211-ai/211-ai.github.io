import { useCallback, useEffect, useRef } from "react";
import { dispatchMissingPersonDeadDrop, saveMissingPersonDeadDrop } from "../../services/walletApi";
import { isMissingPersonDeadDropDue } from "../utils/deadDropHelpers";
import { buildMissingPersonDeadDropSyncPayload } from "../utils/deadDropHelpers";
import type { CheckInPolicyDraft, DisclosureRecipientDraft, UploadItem, RegistrationProfileDraft } from "../../models/abby";
import type { WalletApiConfig } from "../../services/walletApi";

interface DeadDropSyncDeps {
  missingPersonDeadDropEnabled: boolean;
  missingPersonDeadDropLastSentForCheckInAt: string;
  policy: CheckInPolicyDraft;
  profile: RegistrationProfileDraft;
  recipients: DisclosureRecipientDraft[];
  setMissingPersonDeadDropLastSentForCheckInAt: (value: string) => void;
  uploads: UploadItem[];
  walletApiConfig: WalletApiConfig | undefined;
  walletDeadDropReady: boolean;
}

export function useDeadDropSync({
  missingPersonDeadDropEnabled,
  missingPersonDeadDropLastSentForCheckInAt,
  policy,
  profile,
  recipients,
  setMissingPersonDeadDropLastSentForCheckInAt,
  uploads,
  walletApiConfig,
  walletDeadDropReady,
}: DeadDropSyncDeps) {
  const lastSyncedDeadDropPayloadRef = useRef("");

  const sendMissingPersonDeadDrop = useCallback(async (): Promise<boolean> => {
    if (!walletApiConfig || !walletDeadDropReady) {
      return false;
    }
    try {
      const request = buildMissingPersonDeadDropSyncPayload(true, policy, profile, uploads, recipients);
      await saveMissingPersonDeadDrop(walletApiConfig, {
        toEmail: request.toEmail,
        subject: request.subject,
        body: request.body,
        bundle: request.bundle,
        bundleFileName: request.bundleFileName,
        dueAt: request.dueAt,
        enabled: request.enabled,
        lastCheckInAt: request.lastCheckInAt,
      });
      await dispatchMissingPersonDeadDrop(walletApiConfig);
      lastSyncedDeadDropPayloadRef.current = JSON.stringify(request);
      if (isMissingPersonDeadDropDue(policy)) {
        setMissingPersonDeadDropLastSentForCheckInAt(policy.lastCheckInAt);
      }
      return true;
    } catch (error) {
      if (import.meta.env.DEV) {
        console.error("Missing-person dead-drop preparation failed", error);
      }
      return false;
    }
  }, [policy, profile, recipients, uploads, walletApiConfig, walletDeadDropReady, setMissingPersonDeadDropLastSentForCheckInAt]);

  useEffect(() => {
    if (!walletApiConfig || !walletDeadDropReady) {
      lastSyncedDeadDropPayloadRef.current = "";
      return;
    }
    const request = buildMissingPersonDeadDropSyncPayload(
      missingPersonDeadDropEnabled,
      policy,
      profile,
      uploads,
      recipients
    );
    const payload = JSON.stringify(request);
    if (lastSyncedDeadDropPayloadRef.current === payload) {
      return;
    }
    let cancelled = false;
    void saveMissingPersonDeadDrop(walletApiConfig, {
      enabled: missingPersonDeadDropEnabled,
      toEmail: request.toEmail,
      subject: request.subject,
      body: request.body,
      bundle: request.bundle,
      bundleFileName: request.bundleFileName,
      dueAt: request.dueAt,
      lastCheckInAt: request.lastCheckInAt,
    })
      .then(() => {
        if (!cancelled) {
          lastSyncedDeadDropPayloadRef.current = payload;
        }
      })
      .catch((error) => {
        if (!cancelled && import.meta.env.DEV) {
          console.error("Missing-person dead-drop arming failed", error);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [missingPersonDeadDropEnabled, policy, profile, recipients, uploads, walletApiConfig, walletDeadDropReady]);

  useEffect(() => {
    if (!missingPersonDeadDropEnabled || !policy.escalationEnabled) return;
    if (!isMissingPersonDeadDropDue(policy)) return;
    if (missingPersonDeadDropLastSentForCheckInAt === policy.lastCheckInAt) return;

    void sendMissingPersonDeadDrop();
  }, [
    missingPersonDeadDropEnabled,
    missingPersonDeadDropLastSentForCheckInAt,
    policy,
    sendMissingPersonDeadDrop,
  ]);

  return { sendMissingPersonDeadDrop };
}
