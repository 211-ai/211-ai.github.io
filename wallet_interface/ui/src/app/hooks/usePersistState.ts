import { useEffect } from "react";
import { defaultShelterChecklist, writePersistedAppState } from "../appState";
import type {
  CheckInPolicyDraft,
  DisclosureRecipientDraft,
  ProofReceiptView,
  RegistrationProfileDraft,
  SavedService,
  ServiceInteractionEvent,
  ServicePlan,
  ShelterContactRequest,
  UploadItem,
} from "../../models/abby";
import type {
  ShelterCaseRecord,
  ShelterProviderMessage,
  ShelterStaffAccount,
  ShelterUserAccount,
} from "../appState";

export interface PersistableState {
  analyticsOptIn: Record<string, boolean>;
  benefitsOptIn: boolean;
  missingPersonDeadDropEnabled: boolean;
  missingPersonDeadDropLastSentForCheckInAt: string;
  policy: CheckInPolicyDraft;
  profile: RegistrationProfileDraft;
  recipients: DisclosureRecipientDraft[];
  savedServices: SavedService[];
  serviceInteractions: ServiceInteractionEvent[];
  servicePlans: ServicePlan[];
  shelterChecklist: typeof defaultShelterChecklist;
  shelterContactRequests: ShelterContactRequest[];
  shelterCaseRecords: ShelterCaseRecord[];
  shelterProviderMessages: ShelterProviderMessage[];
  shelterStaffAccounts: ShelterStaffAccount[];
  shelterUserAccounts: ShelterUserAccount[];
  uploads: UploadItem[];
  walletProofReceipts: ProofReceiptView[];
}

export function usePersistState(state: PersistableState) {
  const {
    analyticsOptIn,
    benefitsOptIn,
    missingPersonDeadDropEnabled,
    missingPersonDeadDropLastSentForCheckInAt,
    policy,
    profile,
    recipients,
    savedServices,
    serviceInteractions,
    servicePlans,
    shelterChecklist,
    shelterContactRequests,
    shelterCaseRecords,
    shelterProviderMessages,
    shelterStaffAccounts,
    shelterUserAccounts,
    uploads,
    walletProofReceipts,
  } = state;

  useEffect(() => {
    if (typeof window === "undefined") return;
    writePersistedAppState({
      profile,
      policy,
      recipients,
      uploads,
      shelterContactRequests,
      shelterStaffAccounts,
      shelterUserAccounts,
      shelterCaseRecords,
      shelterProviderMessages,
      savedServices,
      servicePlans,
      serviceInteractions,
      proofReceipts: walletProofReceipts,
      benefitsOptIn,
      analyticsOptIn,
      missingPersonDeadDropEnabled,
      missingPersonDeadDropLastSentForCheckInAt,
      shelterChecklist,
    });
  }, [
    analyticsOptIn,
    benefitsOptIn,
    missingPersonDeadDropEnabled,
    missingPersonDeadDropLastSentForCheckInAt,
    policy,
    profile,
    recipients,
    savedServices,
    serviceInteractions,
    servicePlans,
    shelterContactRequests,
    shelterCaseRecords,
    shelterChecklist,
    shelterProviderMessages,
    shelterStaffAccounts,
    shelterUserAccounts,
    uploads,
    walletProofReceipts,
  ]);
}
