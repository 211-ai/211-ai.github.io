import { ChangeEvent, FormEvent, useMemo, useState } from "react";
import {
  Bell,
  CalendarCheck,
  CalendarClock,
  ClipboardCheck,
  ContactRound,
  HeartHandshake,
  Landmark,
  MessageSquare,
  Search,
  ShieldCheck,
  UsersRound,
  Wrench
} from "lucide-react";
import { ActionCard, Badge, Button, Field, Section, StatusBanner } from "../../../components/ui";
import {
  type DisclosureRecipientDraft,
  type ProofReceiptView,
  type RegistrationProfileDraft,
  type RouteId,
  type ShelterContactRequest
} from "../../../models/abby";
import { t, tFormat, translateServiceNeed, type SupportedLocale } from "../../../lib/localization";
import { StatusPanel } from "../../../app/components/StatusPanel";
import {
  defaultManagedUserDraft,
  defaultShelterChecklist,
  providerEligibilityCriteria,
  serviceNeeds,
  shelterOptions,
  type ShelterCasePriority,
  type ShelterCaseRecord,
  type ShelterCaseStatus,
  type ShelterEligibilityCriterion,
  type ShelterProviderMessage,
  type ShelterStaffAccount,
  type ShelterUserAccount
} from "../../../app/appState";
import { getProviderPortalView, providerRouteIds, type ProviderPortalView } from "../../../app/config/navigation";
import {
  createEntityId,
  formatContactRequestStatus,
  formatProviderMessageChannel,
  formatRequestTimestamp,
  getIdentityDocumentFileDetail,
  ID_DOCUMENT_ACCEPT_ATTR,
  isAcceptedIdentityDocument
} from "../../../app/utils/formatHelpers";
import {
  contactLabelForShelterUser,
  formatProviderActivityDate,
  formatProviderPercent,
  formatShelterDate,
  latestProviderTimestamp,
  providerActivityToneLabel,
  providerCasePriorityLabel,
  providerCasePriorityRank,
  providerCaseStatusLabel,
  providerClientCommitment,
  providerEligibilityClaim,
  providerEligibilityLabel,
  providerProofClientLabel,
  providerProofTypeLabel,
  providerProofVerificationStatusLabel
} from "../../../app/utils/providerHelpers";
import { appStableSuffix } from "../../../app/utils/serviceHelpers";

export function ShelterScreen({
  checklist,
  setChecklist,
  contactRequests,
  navigate,
  profile,
  proofReceipts,
  shelterCaseRecords,
  providerMessages,
  recipients,
  siteLocale,
  setContactRequests,
  setShelterCaseRecords,
  setProofReceipts,
  setProviderMessages,
  setRecipients,
  shelterStaffAccounts,
  setShelterStaffAccounts,
  shelterUserAccounts,
  setShelterUserAccounts,
  view
}: {
  checklist: typeof defaultShelterChecklist;
  setChecklist: (value: typeof defaultShelterChecklist) => void;
  contactRequests: ShelterContactRequest[];
  navigate: (route: RouteId) => void;
  profile: RegistrationProfileDraft;
  proofReceipts: ProofReceiptView[];
  shelterCaseRecords: ShelterCaseRecord[];
  providerMessages: ShelterProviderMessage[];
  recipients: DisclosureRecipientDraft[];
  siteLocale: SupportedLocale;
  setContactRequests: (requests: ShelterContactRequest[]) => void;
  setShelterCaseRecords: (records: ShelterCaseRecord[]) => void;
  setProofReceipts: (proofs: ProofReceiptView[]) => void;
  setProviderMessages: (messages: ShelterProviderMessage[]) => void;
  setRecipients: (recipients: DisclosureRecipientDraft[]) => void;
  shelterStaffAccounts: ShelterStaffAccount[];
  setShelterStaffAccounts: (accounts: ShelterStaffAccount[]) => void;
  shelterUserAccounts: ShelterUserAccount[];
  setShelterUserAccounts: (accounts: ShelterUserAccount[]) => void;
  view: ProviderPortalView;
}) {
  const [isShelterAdmin, setIsShelterAdmin] = useState(false);
  const [adminShelter, setAdminShelter] = useState(shelterOptions[0]);
  const [operatorShelter, setOperatorShelter] = useState(shelterOptions[0]);
  const [operatorStaffId, setOperatorStaffId] = useState("");
  const [userDraft, setUserDraft] = useState(defaultManagedUserDraft);
  const [staffDraft, setStaffDraft] = useState({ displayName: "", email: "" });
  const [nudgeDraft, setNudgeDraft] = useState({ userName: "Abby Example", userContact: "abby@example.org" });
  const [managedUserFileDetail, setManagedUserFileDetail] = useState("");
  const [managedUserUploadError, setManagedUserUploadError] = useState("");
  const [messageDraft, setMessageDraft] = useState({
    clientId: "",
    channel: "sms" as ShelterProviderMessage["channel"],
    subject: t(siteLocale, "providerPortal.messages.defaultSubject"),
    body: t(siteLocale, "providerPortal.messages.defaultBody")
  });
  const [proofDraft, setProofDraft] = useState({
    clientId: "",
    proofType: "service_attendance",
    criterionId: "" as ShelterEligibilityCriterion | "",
    caseId: "",
    verifier: t(siteLocale, "providerPortal.proofs.defaultVerifier"),
    claim: t(siteLocale, "providerPortal.proofs.defaultClaim")
  });
  const [caseStatusFilter, setCaseStatusFilter] = useState<ShelterCaseStatus | "all">("all");

  const staffForShelter = shelterStaffAccounts.filter((account) => account.shelter === adminShelter);
  const verifiedStaffForOperatorShelter = shelterStaffAccounts.filter(
    (account) => account.shelter === operatorShelter && account.verified
  );
  const selectedOperator = shelterStaffAccounts.find((account) => account.id === operatorStaffId && account.verified);
  const activeProviderOperator = selectedOperator ?? verifiedStaffForOperatorShelter[0];
  const usersForOperatorShelter = shelterUserAccounts.filter((account) => account.shelter === operatorShelter);
  const caseRecordsForShelter = shelterCaseRecords.filter((record) => record.shelter === operatorShelter);
  const requestsForOperatorShelter = contactRequests.filter((request) => request.shelterName === operatorShelter);
  const providerMessagesForShelter = providerMessages
    .filter((message) => message.shelter === operatorShelter)
    .sort((left, right) => new Date(right.createdAt).getTime() - new Date(left.createdAt).getTime());
  const providerProofsForShelter = proofReceipts
    .filter((proof) => proof.proofType.startsWith("provider_") && proof.publicInputs.shelter === operatorShelter)
    .sort((left, right) => new Date(right.createdAt).getTime() - new Date(left.createdAt).getTime());
  const oversightShelter = isShelterAdmin ? adminShelter : operatorShelter;
  const partnerHelpDisplayName = profile.preferredName || profile.legalName || "Current client";
  const partnerHelpContact = [profile.phone, profile.email].map((item) => item.trim()).filter(Boolean).join(" / ");
  const partnerHelpNeeds = profile.serviceNeeds.length ? profile.serviceNeeds.join(", ") : "Needs not selected";

  function accountSortByHousingThenDate(a: ShelterUserAccount, b: ShelterUserAccount) {
    if (a.foundPermanentHousing !== b.foundPermanentHousing) {
      return a.foundPermanentHousing ? 1 : -1;
    }
    return new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime();
  }

  const staffRegisteredUsersForShelter = shelterUserAccounts
    .filter((account) => account.shelter === oversightShelter)
    .sort(accountSortByHousingThenDate);

  const preferredShelterMentionUsers = shelterUserAccounts
    .filter(
      (account) =>
        account.shelter !== oversightShelter &&
        account.preferredShelter.toLowerCase().includes(oversightShelter.toLowerCase())
    )
    .sort(accountSortByHousingThenDate);
  const selectedMessageClient = usersForOperatorShelter.find((account) => account.id === messageDraft.clientId);
  const selectedProofClient = usersForOperatorShelter.find((account) => account.id === proofDraft.clientId);
  const pendingContactRequestCount = requestsForOperatorShelter.filter((request) => request.status === "pending").length;
  const housedClientCount = usersForOperatorShelter.filter((account) => account.foundPermanentHousing).length;
  const activeClientCount = Math.max(0, usersForOperatorShelter.length - housedClientCount);
  const verifiedStaffCount = verifiedStaffForOperatorShelter.length;
  const allStaffForOperatorShelter = shelterStaffAccounts.filter((account) => account.shelter === operatorShelter);
  const unverifiedStaffCount = allStaffForOperatorShelter.filter((account) => !account.verified).length;
  const caseRows = caseRecordsForShelter
    .map((record) => ({
      record,
      client: usersForOperatorShelter.find((account) => account.id === record.clientId),
      caseManager: shelterStaffAccounts.find((account) => account.id === record.caseManagerStaffId)
    }))
    .filter((row): row is { record: ShelterCaseRecord; client: ShelterUserAccount; caseManager: ShelterStaffAccount | undefined } =>
      Boolean(row.client)
    )
    .filter((row) => caseStatusFilter === "all" || row.record.status === caseStatusFilter)
    .sort(
      (left, right) =>
        providerCasePriorityRank(left.record.priority) - providerCasePriorityRank(right.record.priority) ||
        new Date(left.record.dueDate).getTime() - new Date(right.record.dueDate).getTime()
    );
  const openCaseCount = caseRecordsForShelter.filter((record) => record.status !== "closed").length;
  const urgentCaseCount = caseRecordsForShelter.filter((record) => record.priority === "urgent" && record.status !== "closed").length;
  const waitingCaseCount = caseRecordsForShelter.filter((record) => record.status === "waiting_on_client").length;
  const eligibilityProofCount = providerProofsForShelter.filter((proof) => proof.publicInputs.eligibility_criterion).length;
  const clientAnalytics = usersForOperatorShelter.map((client) => {
    const clientMessages = providerMessagesForShelter.filter((message) => message.clientId === client.id);
    const clientProofs = providerProofsForShelter.filter(
      (proof) => proof.publicInputs.client_commitment === providerClientCommitment(client)
    );
    return {
      client,
      messageCount: clientMessages.length,
      proofCount: clientProofs.length,
      latestMessageAt: latestProviderTimestamp(clientMessages.map((message) => message.createdAt)),
      latestProofAt: latestProviderTimestamp(clientProofs.map((proof) => proof.createdAt))
    };
  });
  const clientsWithMessagesCount = clientAnalytics.filter((item) => item.messageCount > 0).length;
  const clientsWithProofsCount = clientAnalytics.filter((item) => item.proofCount > 0).length;
  const clientsWithoutMessagesCount = Math.max(0, usersForOperatorShelter.length - clientsWithMessagesCount);
  const clientsWithoutProofsCount = Math.max(0, usersForOperatorShelter.length - clientsWithProofsCount);
  const clientsMissingEmergencyContactCount = usersForOperatorShelter.filter(
    (account) => !account.localPrecinctNotified && !account.foundPermanentHousing
  ).length;
  const failedHealthCheckCount = usersForOperatorShelter.filter((account) => account.easyBotCheckStatus === "failed").length;
  const providerServiceNeedCounts = serviceNeeds
    .map((need) => ({
      need,
      count: usersForOperatorShelter.filter((account) => account.serviceNeeds.includes(need)).length
    }))
    .filter((item) => item.count > 0)
    .sort((left, right) => right.count - left.count || left.need.localeCompare(right.need));
  const topServiceNeed = providerServiceNeedCounts[0];
  const providerProofTypeCounts = providerProofsForShelter.reduce<Record<string, number>>((counts, proof) => {
    const proofType = proof.publicInputs.certificate_type || proof.proofType.replace("provider_", "");
    counts[proofType] = (counts[proofType] ?? 0) + 1;
    return counts;
  }, {});
  const providerProofTypeRows = Object.entries(providerProofTypeCounts).sort(
    ([leftType, leftCount], [rightType, rightCount]) => rightCount - leftCount || leftType.localeCompare(rightType)
  );
  const providerProofStaffRows = allStaffForOperatorShelter
    .map((staff) => {
      const proofs = providerProofsForShelter.filter((proof) => proof.publicInputs.staff_id === staff.id);
      return {
        staff,
        proofCount: proofs.length,
        latestProofAt: latestProviderTimestamp(proofs.map((proof) => proof.createdAt))
      };
    })
    .sort((left, right) => right.proofCount - left.proofCount || left.staff.displayName.localeCompare(right.staff.displayName));
  const providerRecentActivity: Array<{
    createdAt: string;
    detail: string;
    id: string;
    title: string;
    tone: "neutral" | "success" | "warning";
  }> = [
    ...usersForOperatorShelter.map((account) => ({
      id: `client-${account.id}`,
      title: tFormat(siteLocale, "providerPortal.analytics.activityClientAdded", {
        name: account.preferredName || account.legalName
      }),
      detail: tFormat(siteLocale, "providerPortal.analytics.activityClientDetail", {
        needs: account.serviceNeeds.length
          ? account.serviceNeeds.map((need) => translateServiceNeed(siteLocale, need)).join(", ")
          : t(siteLocale, "providerPortal.analytics.noNeedsSelected"),
        staff: shelterStaffAccounts.find((item) => item.id === account.createdByStaffId)?.displayName ?? t(siteLocale, "providerPortal.clients.staffFallback")
      }),
      tone: account.foundPermanentHousing ? ("success" as const) : ("warning" as const),
      createdAt: account.createdAt
    })),
    ...providerMessagesForShelter.map((message) => ({
      id: `message-${message.id}`,
      title: tFormat(siteLocale, "providerPortal.analytics.activityMessageSent", { name: message.clientName }),
      detail: tFormat(siteLocale, "providerPortal.analytics.activityMessageDetail", {
        staff: message.staffName,
        subject: message.subject
      }),
      tone: "neutral" as const,
      createdAt: message.createdAt
    })),
    ...providerProofsForShelter.map((proof) => ({
      id: `proof-${proof.id}`,
      title: tFormat(siteLocale, "providerPortal.analytics.activityProofProcessed", {
        name: providerProofClientLabel(proof, usersForOperatorShelter)
      }),
      detail: tFormat(siteLocale, "providerPortal.analytics.activityProofDetail", {
        certificate: providerProofTypeLabel(proof.publicInputs.certificate_type || proof.proofType.replace("provider_", ""), siteLocale),
        verifier: proof.verifier
      }),
      tone: "success" as const,
      createdAt: proof.createdAt
    })),
    ...requestsForOperatorShelter.map((request) => ({
      id: `request-${request.id}`,
      title: tFormat(siteLocale, "providerPortal.analytics.activityContactRequest", {
        status: formatContactRequestStatus(request.status, siteLocale)
      }),
      detail: tFormat(siteLocale, "providerPortal.analytics.activityContactRequestDetail", {
        direction:
          request.direction === "user_to_shelter"
            ? t(siteLocale, "providerPortal.analytics.clientInitiated")
            : t(siteLocale, "providerPortal.analytics.providerInitiated"),
        name: request.userName
      }),
      tone:
        request.status === "pending"
          ? ("warning" as const)
          : request.status === "approved"
            ? ("success" as const)
            : ("neutral" as const),
      createdAt: request.decidedAt ?? request.createdAt
    }))
  ].sort((left, right) => new Date(right.createdAt).getTime() - new Date(left.createdAt).getTime()).slice(0, 8);
  const staffAnalytics = shelterStaffAccounts
    .filter((account) => account.shelter === operatorShelter)
    .map((staff) => {
      const servedClients = usersForOperatorShelter.filter((account) => account.createdByStaffId === staff.id);
      const staffMessages = providerMessagesForShelter.filter((message) => message.staffId === staff.id);
      const staffProofs = providerProofsForShelter.filter((proof) => proof.publicInputs.staff_id === staff.id);
      const clientsWithProofs = servedClients.filter((client) =>
        staffProofs.some((proof) => proof.publicInputs.client_commitment === providerClientCommitment(client))
      ).length;
      return {
        staff,
        servedCount: servedClients.length,
        activeCount: servedClients.filter((account) => !account.foundPermanentHousing).length,
        housedCount: servedClients.filter((account) => account.foundPermanentHousing).length,
        messageCount: staffMessages.length,
        proofCount: staffProofs.length,
        clientsNeedingProofCount: Math.max(0, servedClients.length - clientsWithProofs),
        proofCoverage: formatProviderPercent(clientsWithProofs, servedClients.length),
        lastActivityAt:
          latestProviderTimestamp([
            staff.updatedAt,
            ...servedClients.map((account) => account.createdAt),
            ...staffMessages.map((message) => message.createdAt),
            ...staffProofs.map((proof) => proof.createdAt)
          ]) ?? staff.updatedAt
      };
    })
    .sort((left, right) => right.servedCount - left.servedCount || left.staff.displayName.localeCompare(right.staff.displayName));

  function toggleManagedUserNeed(need: string) {
    setUserDraft((prev) => ({
      ...prev,
      serviceNeeds: prev.serviceNeeds.includes(need)
        ? prev.serviceNeeds.filter((item) => item !== need)
        : [...prev.serviceNeeds, need]
    }));
  }

  function handleManagedUserUploadChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];

    if (!file) {
      setUserDraft({ ...userDraft, photoAssetId: "" });
      setManagedUserFileDetail("");
      setManagedUserUploadError("");
      return;
    }

    if (!isAcceptedIdentityDocument(file)) {
      setUserDraft({ ...userDraft, photoAssetId: "" });
      setManagedUserFileDetail("");
      setManagedUserUploadError(t(siteLocale, "providerPortal.operations.invalidUpload"));
      return;
    }

    setUserDraft({ ...userDraft, photoAssetId: file.name });
    setManagedUserFileDetail(getIdentityDocumentFileDetail(file));
    setManagedUserUploadError("");
  }

  function createManagedUserAccount(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const hasRequiredIdentity = userDraft.legalName.trim() && userDraft.photoAssetId;
    const botCheckReady =
      userDraft.easyBotCheckStatus === "failed" ||
      (userDraft.easyBotCheckStatus === "passed" && Boolean(userDraft.captchaToken));
    if (!selectedOperator || !hasRequiredIdentity || !botCheckReady) return;

    const newUser: ShelterUserAccount = {
      id: `user-${Date.now()}`,
      shelter: operatorShelter,
      legalName: userDraft.legalName.trim(),
      preferredName: userDraft.preferredName.trim(),
      pronouns: userDraft.pronouns.trim(),
      dateOfBirth: userDraft.dateOfBirth,
      photoAssetId: userDraft.photoAssetId,
      phone: userDraft.phone.trim(),
      email: userDraft.email.trim(),
      currentLocation: userDraft.currentLocation.trim(),
      preferredShelter: userDraft.preferredShelter.trim(),
      serviceNeeds: userDraft.serviceNeeds,
      easyBotCheckStatus: userDraft.easyBotCheckStatus,
      captchaToken: userDraft.captchaToken,
      localPrecinctNotified: userDraft.localPrecinctNotified,
      foundPermanentHousing: userDraft.foundPermanentHousing,
      createdByStaffId: selectedOperator.id,
      createdAt: new Date().toISOString()
    };
    setShelterUserAccounts([...shelterUserAccounts, newUser]);
    setShelterCaseRecords([
      ...shelterCaseRecords,
      {
        id: `case-${Date.now()}`,
        shelter: operatorShelter,
        clientId: newUser.id,
        caseManagerStaffId: selectedOperator.id,
        status: "intake",
        priority: userDraft.localPrecinctNotified ? "standard" : "urgent",
        goal: t(siteLocale, "providerPortal.operations.defaultCaseGoal"),
        nextStep: t(siteLocale, "providerPortal.operations.defaultCaseNextStep"),
        dueDate: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10),
        services: userDraft.serviceNeeds,
        notes: t(siteLocale, "providerPortal.operations.defaultCaseNotes"),
        eligibilityCriteria: ["identity_verified"],
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString()
      }
    ]);
    setUserDraft(defaultManagedUserDraft);
    setManagedUserFileDetail("");
    setManagedUserUploadError("");
  }

  function createStaffAccount(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!isShelterAdmin || !staffDraft.displayName.trim()) return;

    const newStaff: ShelterStaffAccount = {
      id: `staff-${Date.now()}`,
      shelter: adminShelter,
      displayName: staffDraft.displayName.trim(),
      email: staffDraft.email.trim(),
      verified: true,
      updatedAt: new Date().toISOString()
    };
    setShelterStaffAccounts([...shelterStaffAccounts, newStaff]);
    setStaffDraft({ displayName: "", email: "" });
  }

  function removeStaffAccount(staffId: string) {
    setShelterStaffAccounts(shelterStaffAccounts.filter((account) => account.id !== staffId));
    if (operatorStaffId === staffId) {
      setOperatorStaffId("");
    }
  }

  function updateStaffVerification(staffId: string, verified: boolean) {
    setShelterStaffAccounts(
      shelterStaffAccounts.map((item) =>
        item.id === staffId ? { ...item, verified, updatedAt: new Date().toISOString() } : item
      )
    );
    if (!verified && operatorStaffId === staffId) {
      setOperatorStaffId("");
    }
  }

  function shelterRecipientExists(shelterName: string) {
    return recipients.some((recipient) => recipient.type === "shelter_staff" && recipient.agencyName === shelterName);
  }

  function addShelterRecipient(shelterName: string) {
    if (shelterRecipientExists(shelterName)) return;

    setRecipients([
      ...recipients,
      {
        id: createEntityId("rec"),
        type: "shelter_staff",
        displayName: shelterName,
        relationship: "Shelter",
        email: "",
        phone: "",
        agencyName: shelterName,
        precinctName: "",
        verified: true,
        allowedScopes: ["identity_minimum"]
      }
    ]);
  }

  function hasPendingShelterNudge() {
    const nudgeContactKey = nudgeDraft.userContact.trim().toLowerCase();
    const nudgeNameKey = nudgeDraft.userName.trim().toLowerCase();
    return contactRequests.some(
      (request) =>
        request.status === "pending" &&
        request.shelterName === operatorShelter &&
        (request.userContact.trim().toLowerCase() === nudgeContactKey ||
          request.userName.trim().toLowerCase() === nudgeNameKey)
    );
  }

  function sendShelterNudge(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedOperator || !nudgeDraft.userName.trim() || !nudgeDraft.userContact.trim() || hasPendingShelterNudge()) {
      return;
    }

    setContactRequests([
      ...contactRequests,
      {
        id: `shelter-request-${Date.now()}`,
        direction: "shelter_to_user",
        status: "pending",
        shelterName: operatorShelter,
        userName: nudgeDraft.userName.trim(),
        userContact: nudgeDraft.userContact.trim(),
        staffId: selectedOperator.id,
        staffName: selectedOperator.displayName,
        createdAt: new Date().toISOString()
      }
    ]);
  }

  function prepareProviderMessage(client: ShelterUserAccount) {
    setMessageDraft({
      clientId: client.id,
      channel: client.phone ? "sms" : client.email ? "email" : "in_app",
      subject: t(siteLocale, "providerPortal.messages.serviceReminderSubject"),
      body: tFormat(siteLocale, "providerPortal.messages.serviceReminderBody", {
        client: client.preferredName || client.legalName,
        shelter: operatorShelter,
        staff: activeProviderOperator?.displayName ?? t(siteLocale, "providerPortal.messages.senderFallback")
      })
    });
    navigate("provider-messages");
  }

  function prepareCaseMessage(caseRecord: ShelterCaseRecord, client: ShelterUserAccount) {
    setMessageDraft({
      clientId: client.id,
      channel: client.phone ? "sms" : client.email ? "email" : "in_app",
      subject: tFormat(siteLocale, "providerPortal.messages.caseUpdateSubject", { goal: caseRecord.goal }),
      body: tFormat(siteLocale, "providerPortal.messages.caseUpdateBody", {
        client: client.preferredName || client.legalName,
        shelter: operatorShelter,
        staff: activeProviderOperator?.displayName ?? t(siteLocale, "providerPortal.messages.senderFallback"),
        step: caseRecord.nextStep
      })
    });
    navigate("provider-messages");
  }

  function sendProviderMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!activeProviderOperator || !selectedMessageClient || !messageDraft.body.trim()) return;

    const nextMessage: ShelterProviderMessage = {
      id: `provider-message-${Date.now()}`,
      shelter: operatorShelter,
      clientId: selectedMessageClient.id,
      clientName: selectedMessageClient.preferredName || selectedMessageClient.legalName,
      clientContact: contactLabelForShelterUser(selectedMessageClient, siteLocale),
      channel: messageDraft.channel,
      subject: messageDraft.subject.trim() || t(siteLocale, "providerPortal.messages.fallbackSubject"),
      body: messageDraft.body.trim(),
      staffId: activeProviderOperator.id,
      staffName: activeProviderOperator.displayName,
      status: "sent",
      createdAt: new Date().toISOString()
    };
    setProviderMessages([nextMessage, ...providerMessages]);
  }

  function prepareProviderProof(client: ShelterUserAccount) {
    setProofDraft({
      clientId: client.id,
      proofType: "service_attendance",
      criterionId: "",
      caseId: "",
      verifier: tFormat(siteLocale, "providerPortal.proofs.certificateVerifier", { shelter: operatorShelter }),
      claim: t(siteLocale, "providerPortal.proofs.certificateClaim")
    });
    navigate("provider-proofs");
  }

  function prepareEligibilityProof(
    client: ShelterUserAccount,
    criterionId: ShelterEligibilityCriterion,
    caseRecord?: ShelterCaseRecord
  ) {
    setProofDraft({
      clientId: client.id,
      proofType: providerEligibilityCriteria.find((item) => item.id === criterionId)?.certificateType ?? "eligibility",
      criterionId,
      caseId: caseRecord?.id ?? "",
      verifier: tFormat(siteLocale, "providerPortal.proofs.eligibilityVerifier", { shelter: operatorShelter }),
      claim: providerEligibilityClaim(criterionId, siteLocale)
    });
    navigate("provider-proofs");
  }

  function selectProofCriterion(criterionId: ShelterEligibilityCriterion | "") {
    const criterion = providerEligibilityCriteria.find((item) => item.id === criterionId);
    setProofDraft({
      ...proofDraft,
      criterionId,
      proofType: criterion?.certificateType ?? proofDraft.proofType,
      claim: criterionId ? providerEligibilityClaim(criterionId, siteLocale) : proofDraft.claim
    });
  }

  function updateCaseRecord(caseId: string, patch: Partial<ShelterCaseRecord>) {
    setShelterCaseRecords(
      shelterCaseRecords.map((record) =>
        record.id === caseId ? { ...record, ...patch, updatedAt: new Date().toISOString() } : record
      )
    );
  }

  function processProviderProofCertificate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!activeProviderOperator || !selectedProofClient || !proofDraft.claim.trim() || !proofDraft.verifier.trim()) return;

    const createdAt = new Date().toISOString();
    const proofSeed = [
      operatorShelter,
      selectedProofClient.id,
      activeProviderOperator.id,
      proofDraft.proofType,
      proofDraft.claim,
      createdAt
    ].join("|");
    const proof: ProofReceiptView = {
      id: `provider-proof-${Date.now()}`,
      proofType: `provider_${proofDraft.proofType}`,
      claim: proofDraft.claim.trim(),
      verifier: proofDraft.verifier.trim(),
      proofSystem: "simulated_zk_certificate",
      verificationStatus: "verified",
      circuitId: `provider-${proofDraft.proofType}-v1`,
      verifierDigest: appStableSuffix(proofSeed),
      proofArtifactRef: `zk-cert-${appStableSuffix(`${proofSeed}:artifact`)}`,
      publicInputs: {
        shelter: operatorShelter,
        client_commitment: appStableSuffix(`${selectedProofClient.id}:${selectedProofClient.dateOfBirth}`),
        staff_id: activeProviderOperator.id,
        certificate_type: proofDraft.proofType,
        ...(proofDraft.criterionId
          ? {
              eligibility_criterion: proofDraft.criterionId,
              eligibility_result: "meets_criteria"
            }
          : {}),
        ...(proofDraft.caseId ? { case_id: proofDraft.caseId } : {}),
        issued_at: createdAt
      },
      witnessLabel: `${selectedProofClient.preferredName || selectedProofClient.legalName} service record`,
      simulated: true,
      createdAt
    };

    setProofReceipts([proof, ...proofReceipts.filter((item) => item.id !== proof.id)]);
  }

  function decideUserShelterRequest(requestId: string, status: "approved" | "denied") {
    const request = contactRequests.find((item) => item.id === requestId);
    if (!request) return;

    if (status === "approved") {
      addShelterRecipient(request.shelterName);
    }

    setContactRequests(
      contactRequests.map((item) =>
        item.id === requestId ? { ...item, status, decidedAt: new Date().toISOString() } : item
      )
    );
  }

  const providerViewTitle: Record<ProviderPortalView, string> = {
    overview: t(siteLocale, "providerPortal.view.overview"),
    clients: t(siteLocale, "providerPortal.view.clients"),
    cases: t(siteLocale, "providerPortal.view.cases"),
    messages: t(siteLocale, "providerPortal.view.messages"),
    analytics: t(siteLocale, "providerPortal.view.analytics"),
    proofs: t(siteLocale, "providerPortal.view.proofs"),
    operations: t(siteLocale, "providerPortal.view.operations")
  };

  return (
    <div className="screen">
      <div className="page-title">
        <p className="eyebrow">{t(siteLocale, "providerPortal.eyebrow")}</p>
        <h1>{providerViewTitle[view]}</h1>
      </div>
      <p className="page-note">{t(siteLocale, "providerPortal.note")}</p>
      <Section title={t(siteLocale, "providerPortal.workspace")}>
        <div className="provider-workspace-controls">
          <Field label={t(siteLocale, "providerPortal.organization")} required>
            <select
              value={operatorShelter}
              onChange={(event) => {
                setOperatorShelter(event.target.value);
                setOperatorStaffId("");
              }}
            >
              {shelterOptions.map((shelter) => (
                <option key={shelter} value={shelter}>
                  {shelter}
                </option>
              ))}
            </select>
          </Field>
          <Field help={t(siteLocale, "providerPortal.staffIdentityHelp")} label={t(siteLocale, "providerPortal.staffIdentity")}>
            <select value={operatorStaffId} onChange={(event) => setOperatorStaffId(event.target.value)}>
              <option value="">{t(siteLocale, "providerPortal.defaultVerifiedStaff")}</option>
              {verifiedStaffForOperatorShelter.map((staff) => (
                <option key={staff.id} value={staff.id}>
                  {staff.displayName}
                </option>
              ))}
            </select>
          </Field>
          <div className="provider-route-actions" aria-label={t(siteLocale, "providerPortal.routeShortcuts")}>
            <Button onClick={() => navigate("provider-clients")} variant="secondary">
              <ContactRound aria-hidden="true" size={18} />
              {t(siteLocale, "providerPortal.shortcut.clients")}
            </Button>
            <Button onClick={() => navigate("provider-cases")} variant="secondary">
              <ClipboardCheck aria-hidden="true" size={18} />
              {t(siteLocale, "providerPortal.shortcut.cases")}
            </Button>
            <Button onClick={() => navigate("provider-messages")} variant="secondary">
              <MessageSquare aria-hidden="true" size={18} />
              {t(siteLocale, "providerPortal.shortcut.messages")}
            </Button>
            <Button onClick={() => navigate("provider-proofs")} variant="secondary">
              <ShieldCheck aria-hidden="true" size={18} />
              {t(siteLocale, "providerPortal.shortcut.proofs")}
            </Button>
          </div>
        </div>
      </Section>
      {view === "overview" ? (
        <>
      <Section title={t(siteLocale, "providerPortal.staffTools")}>
        <div className="tool-grid">
          <button className="tool-tile" onClick={() => navigate("provider-operations")} type="button">
            <ClipboardCheck size={24} /> {t(siteLocale, "providerPortal.tool.assistRegistration")}
          </button>
          <button className="tool-tile" onClick={() => navigate("provider-operations")} type="button">
            <UsersRound size={24} /> {t(siteLocale, "providerPortal.tool.verifyContact")}
          </button>
          <button className="tool-tile" onClick={() => navigate("provider-cases")} type="button">
            <ClipboardCheck size={24} /> {t(siteLocale, "providerPortal.tool.manageCases")}
          </button>
          <button className="tool-tile" onClick={() => navigate("provider-analytics")} type="button">
            <ShieldCheck size={24} /> {t(siteLocale, "providerPortal.tool.reviewAudit")}
          </button>
        </div>
      </Section>
      {profile.servicePartnerHelpRequested ? (
        <Section title={t(siteLocale, "providerPortal.partnerHelp")}>
          <article className="list-item partner-help-request">
            <div>
              <h3>{partnerHelpDisplayName}</h3>
              <p>{t(siteLocale, "providerPortal.partnerHelpDescription")}</p>
              <div className="badge-row">
                <Badge tone="warning">{t(siteLocale, "providerPortal.needsPartnerHelp")}</Badge>
                <Badge>{formatRequestTimestamp(profile.servicePartnerHelpRequestedAt, siteLocale)}</Badge>
                <Badge>{partnerHelpNeeds}</Badge>
              </div>
              <small>{partnerHelpContact || t(siteLocale, "providerPortal.noContactMethod")}</small>
            </div>
          </article>
        </Section>
      ) : null}
      <Section title={t(siteLocale, "providerPortal.overview")}>
        <div className="dashboard-grid">
          <StatusPanel label={t(siteLocale, "providerPortal.overview.clientsServed")} value={String(usersForOperatorShelter.length)} tone="teal" />
          <StatusPanel label={t(siteLocale, "providerPortal.overview.openCases")} value={String(openCaseCount)} tone="teal" />
          <StatusPanel label={t(siteLocale, "providerPortal.overview.activeSupport")} value={String(activeClientCount)} tone="gold" />
          <StatusPanel label={t(siteLocale, "providerPortal.overview.urgentCases")} value={String(urgentCaseCount)} tone="red" />
          <StatusPanel label={t(siteLocale, "providerPortal.overview.messagesSent")} value={String(providerMessagesForShelter.length)} tone="teal" />
          <StatusPanel label={t(siteLocale, "providerPortal.overview.zkCertificates")} value={String(providerProofsForShelter.length)} tone="gold" />
          <StatusPanel label={t(siteLocale, "providerPortal.overview.verifiedStaff")} value={String(verifiedStaffCount)} tone="teal" />
          <StatusPanel label={t(siteLocale, "providerPortal.overview.pendingRequests")} value={String(pendingContactRequestCount)} tone="red" />
        </div>
        <p className="section-note">
          {t(siteLocale, "providerPortal.overviewNote")}
        </p>
      </Section>
        </>
      ) : null}
      {view === "clients" ? (
      <Section title={t(siteLocale, "providerPortal.view.clients")}>
        <div className="list-stack provider-client-list">
          {usersForOperatorShelter.length ? (
            usersForOperatorShelter.map((account) => (
              <article className="list-item provider-client-item" key={`served-${account.id}`}>
                <div>
                  <h3>{account.preferredName || account.legalName}</h3>
                  <p>{account.serviceNeeds.length ? account.serviceNeeds.join(", ") : t(siteLocale, "providerPortal.clients.noServiceNeeds")}</p>
                  <small>
                    {tFormat(siteLocale, "providerPortal.clients.servedBy", {
                      name: shelterStaffAccounts.find((item) => item.id === account.createdByStaffId)?.displayName ?? t(siteLocale, "providerPortal.clients.staffFallback")
                    })}
                    {" · "}
                    {formatShelterDate(account.createdAt)}
                  </small>
                  <div className="badge-row">
                    <Badge>{contactLabelForShelterUser(account, siteLocale)}</Badge>
                    <Badge tone={account.foundPermanentHousing ? "success" : "warning"}>
                      {account.foundPermanentHousing ? t(siteLocale, "providerPortal.clients.housingFound") : t(siteLocale, "providerPortal.clients.needsSupport")}
                    </Badge>
                    <Badge tone={account.localPrecinctNotified ? "success" : "neutral"}>
                      {account.localPrecinctNotified ? t(siteLocale, "providerPortal.clients.emergencyContactSet") : t(siteLocale, "providerPortal.clients.noPrecinctContact")}
                    </Badge>
                  </div>
                </div>
                <div className="row-actions">
                  <Button disabled={!activeProviderOperator} onClick={() => prepareProviderMessage(account)} variant="secondary">
                    <MessageSquare aria-hidden="true" size={18} />
                    {t(siteLocale, "providerPortal.clients.message")}
                  </Button>
                  <Button disabled={!activeProviderOperator} onClick={() => prepareProviderProof(account)} variant="secondary">
                    <ShieldCheck aria-hidden="true" size={18} />
                    {t(siteLocale, "providerPortal.clients.zkCertificate")}
                  </Button>
                </div>
              </article>
            ))
          ) : (
            <div className="empty-state">
              <h3>{t(siteLocale, "providerPortal.clients.emptyTitle")}</h3>
              <p>{t(siteLocale, "providerPortal.clients.emptyBody")}</p>
            </div>
          )}
        </div>
      </Section>
      ) : null}
      {view === "cases" ? (
        <>
          <Section title={t(siteLocale, "providerPortal.cases.title")}>
            <div className="dashboard-grid">
              <StatusPanel label={t(siteLocale, "providerPortal.cases.openCases")} value={String(openCaseCount)} tone="teal" />
              <StatusPanel label={t(siteLocale, "providerPortal.cases.urgentCases")} value={String(urgentCaseCount)} tone="red" />
              <StatusPanel label={t(siteLocale, "providerPortal.cases.waitingOnClient")} value={String(waitingCaseCount)} tone="gold" />
              <StatusPanel label={t(siteLocale, "providerPortal.cases.eligibilityProofs")} value={String(eligibilityProofCount)} tone="teal" />
            </div>
            <div className="message-toolbar">
              <Field label={t(siteLocale, "providerPortal.cases.caseStatus")}>
                <select value={caseStatusFilter} onChange={(event) => setCaseStatusFilter(event.target.value as typeof caseStatusFilter)}>
                  <option value="all">{t(siteLocale, "providerPortal.cases.allCases")}</option>
                  <option value="intake">{t(siteLocale, "providerPortal.cases.intake")}</option>
                  <option value="active">{t(siteLocale, "providerPortal.cases.active")}</option>
                  <option value="waiting_on_client">{t(siteLocale, "providerPortal.cases.waitingOnClient")}</option>
                  <option value="eligible">{t(siteLocale, "providerPortal.cases.eligible")}</option>
                  <option value="closed">{t(siteLocale, "providerPortal.cases.closed")}</option>
                </select>
              </Field>
            </div>
            <div className="list-stack provider-case-list">
              {caseRows.length ? (
                caseRows.map(({ record, client, caseManager }) => {
                  const clientProofs = providerProofsForShelter.filter(
                    (proof) =>
                      proof.publicInputs.client_commitment === providerClientCommitment(client) &&
                      (!proof.publicInputs.case_id || proof.publicInputs.case_id === record.id)
                  );
                  return (
                    <article className="list-item provider-case-item" key={record.id}>
                      <div>
                        <h3>{client.preferredName || client.legalName}</h3>
                        <p>{record.goal}</p>
                        <div className="badge-row">
                          <Badge tone={record.priority === "urgent" ? "warning" : "neutral"}>
                            {providerCasePriorityLabel(record.priority, siteLocale)}
                          </Badge>
                          <Badge>{providerCaseStatusLabel(record.status, siteLocale)}</Badge>
                          <Badge>{tFormat(siteLocale, "providerPortal.cases.due", { date: formatShelterDate(record.dueDate) })}</Badge>
                          <Badge>{caseManager?.displayName ?? t(siteLocale, "providerPortal.cases.unassigned")}</Badge>
                          <Badge>
                            {clientProofs.length} {t(siteLocale, clientProofs.length === 1 ? "providerPortal.cases.proofSingular" : "providerPortal.cases.proofPlural")}
                          </Badge>
                        </div>
                        <small>
                          {record.services.length
                            ? record.services.map((service) => translateServiceNeed(siteLocale, service)).join(", ")
                            : t(siteLocale, "providerPortal.cases.noServices")}
                        </small>
                      </div>
                      <div className="provider-case-controls">
                        <Field label={t(siteLocale, "providerPortal.cases.statusField")}>
                          <select
                            value={record.status}
                            onChange={(event) =>
                              updateCaseRecord(record.id, { status: event.target.value as ShelterCaseStatus })
                            }
                          >
                            <option value="intake">{t(siteLocale, "providerPortal.cases.intake")}</option>
                            <option value="active">{t(siteLocale, "providerPortal.cases.active")}</option>
                            <option value="waiting_on_client">{t(siteLocale, "providerPortal.cases.waitingOnClient")}</option>
                            <option value="eligible">{t(siteLocale, "providerPortal.cases.eligible")}</option>
                            <option value="closed">{t(siteLocale, "providerPortal.cases.closed")}</option>
                          </select>
                        </Field>
                        <Field label={t(siteLocale, "providerPortal.cases.priorityField")}>
                          <select
                            value={record.priority}
                            onChange={(event) =>
                              updateCaseRecord(record.id, { priority: event.target.value as ShelterCasePriority })
                            }
                          >
                            <option value="urgent">{t(siteLocale, "providerPortal.cases.urgent")}</option>
                            <option value="standard">{t(siteLocale, "providerPortal.cases.standard")}</option>
                            <option value="monitor">{t(siteLocale, "providerPortal.cases.monitor")}</option>
                          </select>
                        </Field>
                        <Field label={t(siteLocale, "providerPortal.cases.dueDate")}>
                          <input
                            type="date"
                            value={record.dueDate}
                            onChange={(event) => updateCaseRecord(record.id, { dueDate: event.target.value })}
                          />
                        </Field>
                        <Field label={t(siteLocale, "providerPortal.cases.nextStep")}>
                          <input
                            value={record.nextStep}
                            onChange={(event) => updateCaseRecord(record.id, { nextStep: event.target.value })}
                          />
                        </Field>
                        <Field label={t(siteLocale, "providerPortal.cases.notes")}>
                          <textarea
                            rows={3}
                            value={record.notes}
                            onChange={(event) => updateCaseRecord(record.id, { notes: event.target.value })}
                          />
                        </Field>
                      </div>
                      <div className="provider-case-criteria">
                        {record.eligibilityCriteria.map((criterionId) => {
                          const proven = clientProofs.some(
                            (proof) => proof.publicInputs.eligibility_criterion === criterionId
                          );
                          return (
                            <div className="provider-case-criterion" key={`${record.id}-${criterionId}`}>
                              <Badge tone={proven ? "success" : "warning"}>
                                {providerEligibilityLabel(criterionId, siteLocale)} {t(siteLocale, proven ? "providerPortal.cases.proved" : "providerPortal.cases.needed")}
                              </Badge>
                              <Button
                                disabled={!activeProviderOperator}
                                onClick={() => prepareEligibilityProof(client, criterionId, record)}
                                variant="secondary"
                              >
                                {criterionId === "us_citizen"
                                  ? t(siteLocale, "providerPortal.cases.proveUsCitizen")
                                  : t(siteLocale, "providerPortal.cases.prepareProof")}
                              </Button>
                            </div>
                          );
                        })}
                      </div>
                      <div className="row-actions">
                        <Button disabled={!activeProviderOperator} onClick={() => prepareCaseMessage(record, client)} variant="secondary">
                          <MessageSquare aria-hidden="true" size={18} />
                          {t(siteLocale, "providerPortal.cases.messageClient")}
                        </Button>
                        <Button
                          disabled={!activeProviderOperator}
                          onClick={() => prepareEligibilityProof(client, record.eligibilityCriteria[0] ?? "identity_verified", record)}
                          variant="secondary"
                        >
                          <ShieldCheck aria-hidden="true" size={18} />
                          {t(siteLocale, "providerPortal.cases.eligibilityProof")}
                        </Button>
                      </div>
                    </article>
                  );
                })
              ) : (
                <div className="empty-state">
                  <h3>{t(siteLocale, "providerPortal.cases.emptyTitle")}</h3>
                  <p>{t(siteLocale, "providerPortal.cases.emptyBody")}</p>
                </div>
              )}
            </div>
          </Section>
        </>
      ) : null}
      {view === "messages" ? (
      <Section title={t(siteLocale, "providerPortal.messages.title")}>
        {!activeProviderOperator ? (
          <StatusBanner tone="info">{t(siteLocale, "providerPortal.messages.needStaff")}</StatusBanner>
        ) : !selectedOperator ? (
          <StatusBanner tone="info">
            {tFormat(siteLocale, "providerPortal.messages.defaultSender", { name: activeProviderOperator.displayName })}
          </StatusBanner>
        ) : null}
        <form className="form-grid provider-message-form" id="provider-message-composer" onSubmit={sendProviderMessage}>
          <Field label={t(siteLocale, "providerPortal.messages.client")} required>
            <select
              value={messageDraft.clientId}
              onChange={(event) => setMessageDraft({ ...messageDraft, clientId: event.target.value })}
            >
              <option value="">{t(siteLocale, "providerPortal.messages.selectClient")}</option>
              {usersForOperatorShelter.map((account) => (
                <option key={`message-${account.id}`} value={account.id}>
                  {account.preferredName || account.legalName}
                </option>
              ))}
            </select>
          </Field>
          <Field label={t(siteLocale, "providerPortal.messages.channel")} required>
            <select
              value={messageDraft.channel}
              onChange={(event) =>
                setMessageDraft({ ...messageDraft, channel: event.target.value as ShelterProviderMessage["channel"] })
              }
            >
              <option value="sms">{t(siteLocale, "channel.sms")}</option>
              <option value="email">{t(siteLocale, "channel.email")}</option>
              <option value="in_app">{t(siteLocale, "messages.inApp")}</option>
            </select>
          </Field>
          <Field label={t(siteLocale, "providerPortal.messages.subject")}>
            <input
              value={messageDraft.subject}
              onChange={(event) => setMessageDraft({ ...messageDraft, subject: event.target.value })}
            />
          </Field>
          <Field label={t(siteLocale, "providerPortal.messages.body")} required>
            <textarea
              rows={4}
              value={messageDraft.body}
              onChange={(event) => setMessageDraft({ ...messageDraft, body: event.target.value })}
            />
          </Field>
          <div className="full-span row-actions">
            <Button
              disabled={!activeProviderOperator || !selectedMessageClient || !messageDraft.body.trim()}
              type="submit"
            >
              <MessageSquare aria-hidden="true" size={18} />
              {t(siteLocale, "providerPortal.messages.send")}
            </Button>
          </div>
        </form>
        <div className="list-stack">
          {providerMessagesForShelter.length ? (
            providerMessagesForShelter.slice(0, 6).map((message) => (
              <article className="list-item provider-message-item" key={message.id}>
                <div>
                  <h3>{message.subject}</h3>
                  <p>{message.body}</p>
                  <div className="badge-row">
                    <Badge>{message.clientName}</Badge>
                    <Badge>{formatProviderMessageChannel(message.channel, siteLocale)}</Badge>
                    <Badge tone="success">{message.status}</Badge>
                    <Badge>{formatShelterDate(message.createdAt)}</Badge>
                  </div>
                  <small>
                    {tFormat(siteLocale, "providerPortal.messages.sentByTo", {
                      contact: message.clientContact,
                      staff: message.staffName
                    })}
                  </small>
                </div>
              </article>
            ))
          ) : (
            <small>{t(siteLocale, "providerPortal.messages.empty")}</small>
          )}
        </div>
      </Section>
      ) : null}
      {view === "analytics" ? (
        <>
          <Section title={t(siteLocale, "providerPortal.analytics.title")}>
            <div className="dashboard-grid">
              <StatusPanel label={t(siteLocale, "providerPortal.analytics.housingRate")} value={formatProviderPercent(housedClientCount, usersForOperatorShelter.length)} tone="teal" />
              <StatusPanel label={t(siteLocale, "providerPortal.analytics.messageReach")} value={formatProviderPercent(clientsWithMessagesCount, usersForOperatorShelter.length)} tone="gold" />
              <StatusPanel label={t(siteLocale, "providerPortal.analytics.proofCoverage")} value={formatProviderPercent(clientsWithProofsCount, usersForOperatorShelter.length)} tone="teal" />
              <StatusPanel label={t(siteLocale, "providerPortal.analytics.missingContact")} value={String(clientsMissingEmergencyContactCount)} tone="red" />
              <StatusPanel label={t(siteLocale, "providerPortal.analytics.healthChecks")} value={String(failedHealthCheckCount)} tone="gold" />
              <StatusPanel label={t(siteLocale, "providerPortal.analytics.staffInactive")} value={String(unverifiedStaffCount)} tone="red" />
            </div>
            <div className="provider-insight-grid">
              <article className="provider-insight-card">
                <h3>{t(siteLocale, "providerPortal.analytics.clientSupportSignals")}</h3>
                <p>
                  {tFormat(siteLocale, "providerPortal.analytics.activeClientsNeedSupport", {
                    count: String(activeClientCount),
                    label: activeClientCount === 1 ? t(siteLocale, "providerPortal.analytics.clientSingular") : t(siteLocale, "providerPortal.analytics.clientPlural")
                  })}{" "}
                  {topServiceNeed
                    ? tFormat(siteLocale, "providerPortal.analytics.topNeed", {
                        need: translateServiceNeed(siteLocale, topServiceNeed.need)
                      })
                    : t(siteLocale, "providerPortal.analytics.noNeedsSelected")}
                </p>
                <div className="provider-staff-metrics" aria-label={t(siteLocale, "providerPortal.analytics.clientSupportMetrics")}>
                  <span><strong>{clientsWithoutMessagesCount}</strong> {t(siteLocale, "providerPortal.analytics.noMessages")}</span>
                  <span><strong>{clientsWithoutProofsCount}</strong> {t(siteLocale, "providerPortal.analytics.noProofs")}</span>
                  <span><strong>{pendingContactRequestCount}</strong> {t(siteLocale, "providerPortal.analytics.pendingRequests")}</span>
                </div>
              </article>
              <article className="provider-insight-card">
                <h3>{t(siteLocale, "providerPortal.analytics.staffPicture")}</h3>
                <p>
                  {tFormat(siteLocale, "providerPortal.analytics.staffCanAct", {
                    count: String(verifiedStaffCount),
                    label: verifiedStaffCount === 1 ? t(siteLocale, "providerPortal.analytics.staffMemberSingular") : t(siteLocale, "providerPortal.analytics.staffMemberPlural"),
                    shelter: operatorShelter
                  })}{" "}
                  {unverifiedStaffCount
                    ? tFormat(siteLocale, "providerPortal.analytics.staffNeedReview", {
                        count: String(unverifiedStaffCount),
                        label: unverifiedStaffCount === 1 ? t(siteLocale, "providerPortal.analytics.staffAccountSingular") : t(siteLocale, "providerPortal.analytics.staffAccountPlural")
                      })
                    : t(siteLocale, "providerPortal.analytics.allStaffVerified")}
                </p>
                <div className="provider-staff-metrics" aria-label={t(siteLocale, "providerPortal.analytics.staffActivityMetrics")}>
                  <span><strong>{providerMessagesForShelter.length}</strong> {t(siteLocale, "providerPortal.analytics.messages")}</span>
                  <span><strong>{providerProofsForShelter.length}</strong> {t(siteLocale, "providerPortal.analytics.zkProofs")}</span>
                  <span><strong>{providerRecentActivity.length}</strong> {t(siteLocale, "providerPortal.analytics.timelineEvents")}</span>
                </div>
              </article>
            </div>
          </Section>
          <Section title={t(siteLocale, "providerPortal.analytics.needDistribution")}>
            <div className="provider-insight-grid">
              {providerServiceNeedCounts.length ? (
                providerServiceNeedCounts.map((item) => (
                  <article className="provider-need-card" key={item.need}>
                    <strong>{translateServiceNeed(siteLocale, item.need)}</strong>
                    <span>{tFormat(siteLocale, "providerPortal.analytics.clientsCount", {
                      count: String(item.count),
                      label: item.count === 1 ? t(siteLocale, "providerPortal.analytics.clientSingular") : t(siteLocale, "providerPortal.analytics.clientPlural")
                    })}</span>
                    <div className="provider-meter" aria-label={tFormat(siteLocale, "providerPortal.analytics.clientsMeter", { need: translateServiceNeed(siteLocale, item.need) })}>
                      <span style={{ width: formatProviderPercent(item.count, usersForOperatorShelter.length) }} />
                    </div>
                  </article>
                ))
              ) : (
                <small>{t(siteLocale, "providerPortal.analytics.noNeedData")}</small>
              )}
            </div>
          </Section>
          <Section title={t(siteLocale, "providerPortal.analytics.staffAnalytics")}>
            <div className="list-stack provider-staff-analytics">
              {staffAnalytics.length ? (
                staffAnalytics.map((item) => (
                  <article className="list-item provider-staff-row" key={`analytics-${item.staff.id}`}>
                    <div>
                      <h3>{item.staff.displayName}</h3>
                      <p>{item.staff.email || t(siteLocale, "providerPortal.analytics.noEmail")}</p>
                      <div className="provider-staff-metrics" aria-label={tFormat(siteLocale, "providerPortal.analytics.staffAnalyticsAria", { name: item.staff.displayName })}>
                        <span><strong>{item.servedCount}</strong> {t(siteLocale, "providerPortal.analytics.served")}</span>
                        <span><strong>{item.activeCount}</strong> {t(siteLocale, "providerPortal.analytics.active")}</span>
                        <span><strong>{item.housedCount}</strong> {t(siteLocale, "providerPortal.analytics.housed")}</span>
                        <span><strong>{item.messageCount}</strong> {t(siteLocale, "providerPortal.analytics.messages")}</span>
                        <span><strong>{item.proofCount}</strong> {t(siteLocale, "providerPortal.analytics.proofs")}</span>
                        <span><strong>{item.proofCoverage}</strong> {t(siteLocale, "providerPortal.analytics.proofCoverage")}</span>
                        <span><strong>{item.clientsNeedingProofCount}</strong> {t(siteLocale, "providerPortal.analytics.needProofs")}</span>
                      </div>
                      <small>{tFormat(siteLocale, "providerPortal.analytics.lastActivity", { value: formatProviderActivityDate(item.lastActivityAt, siteLocale) })}</small>
                    </div>
                    <Badge tone={item.staff.verified ? "success" : "warning"}>
                      {item.staff.verified ? t(siteLocale, "contacts.verified") : t(siteLocale, "providerPortal.analytics.verificationOff")}
                    </Badge>
                  </article>
                ))
              ) : (
                <small>{t(siteLocale, "providerPortal.analytics.noStaffAnalytics")}</small>
              )}
            </div>
          </Section>
          <Section title={t(siteLocale, "providerPortal.analytics.recentActivity")}>
            <div className="list-stack provider-activity-list">
              {providerRecentActivity.length ? (
                providerRecentActivity.map((activity) => (
                  <article className="list-item provider-activity-item" key={activity.id}>
                    <div>
                      <h3>{activity.title}</h3>
                      <p>{activity.detail}</p>
                      <small>{formatProviderActivityDate(activity.createdAt, siteLocale)}</small>
                    </div>
                    <Badge tone={activity.tone}>{providerActivityToneLabel(activity.tone, siteLocale)}</Badge>
                  </article>
                ))
              ) : (
                <small>{t(siteLocale, "providerPortal.analytics.noProviderActivity")}</small>
              )}
            </div>
          </Section>
        </>
      ) : null}
      {view === "proofs" ? (
        <>
          <Section title={t(siteLocale, "providerPortal.proofs.title")}>
            <p className="section-note">
              {t(siteLocale, "providerPortal.proofs.note")}
            </p>
            <div className="dashboard-grid">
              <StatusPanel label={t(siteLocale, "providerPortal.proofs.verifiedProofs")} value={String(providerProofsForShelter.length)} tone="teal" />
              <StatusPanel label={t(siteLocale, "providerPortal.proofs.clientCoverage")} value={formatProviderPercent(clientsWithProofsCount, usersForOperatorShelter.length)} tone="gold" />
              <StatusPanel label={t(siteLocale, "providerPortal.proofs.needCertificates")} value={String(clientsWithoutProofsCount)} tone="red" />
              <StatusPanel label={t(siteLocale, "providerPortal.proofs.certificateTypes")} value={String(providerProofTypeRows.length)} tone="teal" />
            </div>
            <div className="provider-insight-grid">
              <article className="provider-insight-card">
                <h3>{t(siteLocale, "providerPortal.proofs.certificateMix")}</h3>
                <div className="provider-staff-metrics" aria-label={t(siteLocale, "providerPortal.proofs.proofTypeCounts")}>
                  {providerProofTypeRows.length ? (
                    providerProofTypeRows.map(([proofType, count]) => (
                      <span key={proofType}>
                        <strong>{count}</strong> {providerProofTypeLabel(proofType, siteLocale)}
                      </span>
                    ))
                  ) : (
                    <span><strong>0</strong> {t(siteLocale, "providerPortal.proofs.certificates")}</span>
                  )}
                </div>
              </article>
              <article className="provider-insight-card">
                <h3>{t(siteLocale, "providerPortal.proofs.issuerActivity")}</h3>
                <div className="provider-staff-metrics" aria-label={t(siteLocale, "providerPortal.proofs.issuerCounts")}>
                  {providerProofStaffRows.length ? (
                    providerProofStaffRows.map((item) => (
                      <span key={`proof-staff-${item.staff.id}`}>
                        <strong>{item.proofCount}</strong> {item.staff.displayName}
                      </span>
                    ))
                  ) : (
                    <span><strong>0</strong> {t(siteLocale, "providerPortal.proofs.issuers")}</span>
                  )}
                </div>
              </article>
            </div>
            <form className="form-grid provider-proof-form" onSubmit={processProviderProofCertificate}>
              <Field label={t(siteLocale, "providerPortal.proofs.client")} required>
                <select
                  value={proofDraft.clientId}
                  onChange={(event) => setProofDraft({ ...proofDraft, clientId: event.target.value })}
                >
                  <option value="">{t(siteLocale, "providerPortal.proofs.selectClient")}</option>
                  {usersForOperatorShelter.map((account) => (
                    <option key={`proof-${account.id}`} value={account.id}>
                      {account.preferredName || account.legalName}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label={t(siteLocale, "providerPortal.proofs.certificateType")} required>
                <select
                  value={proofDraft.proofType}
                  onChange={(event) => setProofDraft({ ...proofDraft, proofType: event.target.value })}
                >
                  <option value="service_attendance">{providerProofTypeLabel("service_attendance", siteLocale)}</option>
                  <option value="document_reviewed">{providerProofTypeLabel("document_reviewed", siteLocale)}</option>
                  <option value="benefits_referral">{providerProofTypeLabel("benefits_referral", siteLocale)}</option>
                  <option value="housing_step">{providerProofTypeLabel("housing_step", siteLocale)}</option>
                  <option value="us_citizenship">{providerProofTypeLabel("us_citizenship", siteLocale)}</option>
                  <option value="service_area_residency">{providerProofTypeLabel("service_area_residency", siteLocale)}</option>
                  <option value="income_eligibility">{providerProofTypeLabel("income_eligibility", siteLocale)}</option>
                  <option value="identity_verified">{providerProofTypeLabel("identity_verified", siteLocale)}</option>
                </select>
              </Field>
              <Field help={t(siteLocale, "providerPortal.proofs.eligibilityHelp")} label={t(siteLocale, "providerPortal.proofs.eligibilityCriterion")}>
                <select
                  value={proofDraft.criterionId}
                  onChange={(event) => selectProofCriterion(event.target.value as ShelterEligibilityCriterion | "")}
                >
                  <option value="">{t(siteLocale, "providerPortal.proofs.noEligibilityCriterion")}</option>
                  {providerEligibilityCriteria.map((criterion) => (
                    <option key={criterion.id} value={criterion.id}>
                      {providerEligibilityLabel(criterion.id, siteLocale)}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label={t(siteLocale, "providerPortal.proofs.verifier")} required>
                <input
                  value={proofDraft.verifier}
                  onChange={(event) => setProofDraft({ ...proofDraft, verifier: event.target.value })}
                />
              </Field>
              <Field label={t(siteLocale, "providerPortal.proofs.publicClaim")} required>
                <textarea
                  rows={3}
                  value={proofDraft.claim}
                  onChange={(event) => setProofDraft({ ...proofDraft, claim: event.target.value })}
                />
              </Field>
              <div className="full-span row-actions">
                <Button
                  disabled={!activeProviderOperator || !selectedProofClient || !proofDraft.claim.trim() || !proofDraft.verifier.trim()}
                  type="submit"
                >
                  <ShieldCheck aria-hidden="true" size={18} />
                  {t(siteLocale, "providerPortal.proofs.processCertificate")}
                </Button>
              </div>
            </form>
          </Section>
          <Section title={t(siteLocale, "providerPortal.proofs.queue")}>
            <div className="list-stack provider-proof-queue">
              {clientAnalytics.length ? (
                clientAnalytics.map((item) => (
                  <article className="list-item provider-proof-item" key={`proof-queue-${item.client.id}`}>
                    <div>
                      <h3>{item.client.preferredName || item.client.legalName}</h3>
                      <p>{item.client.serviceNeeds.length ? item.client.serviceNeeds.map((need) => translateServiceNeed(siteLocale, need)).join(", ") : t(siteLocale, "providerPortal.clients.noServiceNeeds")}</p>
                      <div className="badge-row">
                        <Badge tone={item.proofCount ? "success" : "warning"}>
                          {item.proofCount
                            ? `${item.proofCount} ${t(siteLocale, item.proofCount === 1 ? "providerPortal.cases.proofSingular" : "providerPortal.cases.proofPlural")}`
                            : t(siteLocale, "providerPortal.proofs.needsCertificate")}
                        </Badge>
                        <Badge>{item.messageCount} {t(siteLocale, "providerPortal.analytics.messages")}</Badge>
                        {item.latestProofAt ? <Badge>{formatProviderActivityDate(item.latestProofAt, siteLocale)}</Badge> : null}
                      </div>
                    </div>
                    <Button disabled={!activeProviderOperator} onClick={() => prepareProviderProof(item.client)} variant="secondary">
                      {t(siteLocale, "providerPortal.proofs.prepareCertificate")}
                    </Button>
                  </article>
                ))
              ) : (
                <small>{t(siteLocale, "providerPortal.proofs.noClients")}</small>
              )}
            </div>
          </Section>
          <Section title={t(siteLocale, "providerPortal.proofs.transparencyLog")}>
            <div className="list-stack">
              {providerProofsForShelter.length ? (
                providerProofsForShelter.slice(0, 8).map((proof) => (
                  <article className="list-item provider-proof-item" key={proof.id}>
                    <div>
                      <h3>{proof.claim}</h3>
                      <p>{proof.verifier}</p>
                      <div className="badge-row">
                        <Badge tone="success">{providerProofVerificationStatusLabel(proof.verificationStatus, siteLocale)}</Badge>
                        <Badge>{providerProofClientLabel(proof, usersForOperatorShelter)}</Badge>
                        <Badge>{providerProofTypeLabel(proof.publicInputs.certificate_type, siteLocale)}</Badge>
                        {proof.publicInputs.eligibility_criterion ? (
                          <Badge>{providerEligibilityLabel(proof.publicInputs.eligibility_criterion as ShelterEligibilityCriterion, siteLocale)}</Badge>
                        ) : null}
                        <Badge>{formatProviderActivityDate(proof.createdAt, siteLocale)}</Badge>
                      </div>
                      <small>
                        {t(siteLocale, "providerPortal.proofs.clientCommitment")} <code>{proof.publicInputs.client_commitment}</code> · {t(siteLocale, "providerPortal.proofs.artifact")}{" "}
                        <code>{proof.proofArtifactRef}</code> · {t(siteLocale, "providerPortal.proofs.circuit")} <code>{proof.circuitId}</code>
                      </small>
                    </div>
                  </article>
                ))
              ) : (
                <small>{t(siteLocale, "providerPortal.proofs.noneProcessed")}</small>
              )}
            </div>
          </Section>
        </>
      ) : null}
      {view === "operations" ? (
        <>
      <Section title={t(siteLocale, "providerPortal.operations.title")}>
        <div className="shelter-staff-panel">
          {!selectedOperator ? (
            <small className="pin-request-note">{t(siteLocale, "providerPortal.operations.needVerifiedOperator")}</small>
          ) : (
            <>
              <Section title={t(siteLocale, "providerPortal.operations.createUserAccount")}>
                <form className="form-grid" onSubmit={createManagedUserAccount}>
                  <Field label={t(siteLocale, "providerPortal.operations.legalName")} required>
                    <input
                      value={userDraft.legalName}
                      onChange={(event) => setUserDraft({ ...userDraft, legalName: event.target.value })}
                    />
                  </Field>
                  <Field label={t(siteLocale, "profile.preferredName")}>
                    <input
                      value={userDraft.preferredName}
                      onChange={(event) => setUserDraft({ ...userDraft, preferredName: event.target.value })}
                    />
                  </Field>
                  <Field label={t(siteLocale, "providerPortal.operations.pronouns")}>
                    <input
                      placeholder={t(siteLocale, "providerPortal.operations.pronounsPlaceholder")}
                      value={userDraft.pronouns}
                      onChange={(event) => setUserDraft({ ...userDraft, pronouns: event.target.value })}
                    />
                  </Field>
                  <Field label={t(siteLocale, "profile.birthDate")}>
                    <input
                      type="date"
                      value={userDraft.dateOfBirth}
                      onChange={(event) => setUserDraft({ ...userDraft, dateOfBirth: event.target.value })}
                    />
                  </Field>
                  <Field
                    error={managedUserUploadError}
                    help={t(siteLocale, "providerPortal.operations.photoIdHelp")}
                    label={t(siteLocale, "providerPortal.operations.photoId")}
                    required
                  >
                    <input
                      accept={ID_DOCUMENT_ACCEPT_ATTR}
                      type="file"
                      onChange={handleManagedUserUploadChange}
                    />
                    {managedUserFileDetail ? (
                      <small className="registration-file-detail" aria-live="polite">
                        {tFormat(siteLocale, "providerPortal.operations.selectedFile", { value: managedUserFileDetail })}
                      </small>
                    ) : null}
                  </Field>
                  <Field help={t(siteLocale, "profile.phoneHelp")} label={t(siteLocale, "profile.phone")}>
                    <input
                      value={userDraft.phone}
                      onChange={(event) => setUserDraft({ ...userDraft, phone: event.target.value })}
                    />
                  </Field>
                  <Field help={t(siteLocale, "profile.emailHelp")} label={t(siteLocale, "profile.email")}>
                    <input
                      type="email"
                      value={userDraft.email}
                      onChange={(event) => setUserDraft({ ...userDraft, email: event.target.value })}
                    />
                  </Field>
                  <Field label={t(siteLocale, "providerPortal.operations.currentSafeLocation")}>
                    <input
                      value={userDraft.currentLocation}
                      onChange={(event) => setUserDraft({ ...userDraft, currentLocation: event.target.value })}
                    />
                  </Field>
                  <Field label={t(siteLocale, "profile.shelter")}>
                    <input
                      value={userDraft.preferredShelter}
                      onChange={(event) => setUserDraft({ ...userDraft, preferredShelter: event.target.value })}
                    />
                  </Field>
                  <label className="captcha-box full-span">
                    <input
                      checked={userDraft.easyBotCheckStatus === "passed"}
                      onChange={(event) =>
                        setUserDraft({
                          ...userDraft,
                          easyBotCheckStatus: event.target.checked ? "passed" : "failed",
                          captchaToken: ""
                        })
                      }
                      type="checkbox"
                    />
                    <span>{t(siteLocale, "providerPortal.operations.quickHealthCheck")}</span>
                  </label>
                  <div className="full-span">
                    <span className="field-label">{t(siteLocale, "profile.serviceNeeds")}</span>
                    <div className="chip-grid">
                      {serviceNeeds.map((need) => (
                        <button
                          aria-pressed={userDraft.serviceNeeds.includes(need)}
                          className="choice-chip"
                          key={need}
                          onClick={() => toggleManagedUserNeed(need)}
                          type="button"
                        >
                          {translateServiceNeed(siteLocale, need)}
                        </button>
                      ))}
                    </div>
                  </div>
                  <label className="captcha-box full-span">
                    <input
                      checked={Boolean(userDraft.captchaToken)}
                      disabled={userDraft.easyBotCheckStatus !== "passed"}
                      onChange={(event) =>
                        setUserDraft({ ...userDraft, captchaToken: event.target.checked ? "mock-captcha-token" : "" })
                      }
                      type="checkbox"
                    />
                    <span>{t(siteLocale, "providerPortal.operations.botCheck")}</span>
                  </label>
                  <label className="consent-box full-span">
                    <input
                      checked={userDraft.localPrecinctNotified}
                      onChange={(event) => setUserDraft({ ...userDraft, localPrecinctNotified: event.target.checked })}
                      type="checkbox"
                    />
                    <span>
                      <strong>{t(siteLocale, "providerPortal.operations.localPrecinctNotified")}</strong>
                    </span>
                  </label>
                  <label className="consent-box full-span">
                    <input
                      checked={userDraft.foundPermanentHousing}
                      onChange={(event) => setUserDraft({ ...userDraft, foundPermanentHousing: event.target.checked })}
                      type="checkbox"
                    />
                    <span>
                      <strong>{t(siteLocale, "providerPortal.operations.foundPermanentHousing")}</strong>
                    </span>
                  </label>
                  <div className="full-span">
                    <Button
                      disabled={
                        !userDraft.legalName.trim() ||
                        !userDraft.photoAssetId ||
                        (userDraft.easyBotCheckStatus === "pending") ||
                        (userDraft.easyBotCheckStatus === "passed" && !userDraft.captchaToken)
                      }
                      type="submit"
                    >
                      {t(siteLocale, "providerPortal.operations.createUser")}
                    </Button>
                  </div>
                </form>
              </Section>

              <Section title={t(siteLocale, "providerPortal.operations.contactListRequests")}>
                <p className="section-note">
                  {t(siteLocale, "providerPortal.operations.contactListNote")}
                </p>
                <form className="form-grid" onSubmit={sendShelterNudge}>
                  <Field label={t(siteLocale, "providerPortal.operations.personName")} required>
                    <input
                      value={nudgeDraft.userName}
                      onChange={(event) => setNudgeDraft({ ...nudgeDraft, userName: event.target.value })}
                    />
                  </Field>
                  <Field label={t(siteLocale, "providerPortal.operations.phoneOrEmail")} required>
                    <input
                      value={nudgeDraft.userContact}
                      onChange={(event) => setNudgeDraft({ ...nudgeDraft, userContact: event.target.value })}
                    />
                  </Field>
                  <div className="full-span centered-action">
                    <Button disabled={hasPendingShelterNudge()} type="submit" variant="secondary">
                      <MessageSquare size={18} /> {t(siteLocale, "providerPortal.operations.sendContactRequest")}
                    </Button>
                  </div>
                  {hasPendingShelterNudge() ? (
                    <small className="full-span pin-request-note">
                      {t(siteLocale, "providerPortal.operations.pendingRequestExists")}
                    </small>
                  ) : null}
                </form>
                <div className="list-stack">
                  {requestsForOperatorShelter.length ? (
                    requestsForOperatorShelter.map((request) => (
                      <article className="list-item access-request-item" key={`shelter-contact-${request.id}`}>
                        <div>
                          <h3>{request.userName}</h3>
                          <p>
                            {request.direction === "user_to_shelter"
                              ? tFormat(siteLocale, "providerPortal.operations.userAskedAdd", { shelter: request.shelterName })
                              : tFormat(siteLocale, "providerPortal.operations.shelterAskedUser", { shelter: request.shelterName })}
                          </p>
                          <div className="badge-row">
                            <Badge>{request.userContact}</Badge>
                            <Badge tone={request.status === "approved" ? "success" : request.status === "denied" ? "warning" : "neutral"}>
                              {formatContactRequestStatus(request.status, siteLocale)}
                            </Badge>
                          </div>
                        </div>
                        {request.direction === "user_to_shelter" && request.status === "pending" ? (
                          <div className="row-actions">
                            <Button onClick={() => decideUserShelterRequest(request.id, "approved")} variant="secondary">
                              {t(siteLocale, "providerPortal.operations.approve")}
                            </Button>
                            <Button onClick={() => decideUserShelterRequest(request.id, "denied")} variant="danger">
                              {t(siteLocale, "providerPortal.operations.deny")}
                            </Button>
                          </div>
                        ) : null}
                      </article>
                    ))
                  ) : (
                    <small>{t(siteLocale, "providerPortal.operations.noContactRequests")}</small>
                  )}
                </div>
              </Section>

              <div className="list-stack">
                {usersForOperatorShelter.length ? (
                  usersForOperatorShelter.map((account) => (
                    <article className="list-item" key={account.id}>
                      <div>
                        <h3>{account.preferredName || account.legalName}</h3>
                        <p>{account.legalName}</p>
                        <small>
                          {tFormat(siteLocale, "providerPortal.operations.createdBy", {
                            name: shelterStaffAccounts.find((item) => item.id === account.createdByStaffId)?.displayName ?? t(siteLocale, "providerPortal.clients.staffFallback")
                          })}
                          {account.dateOfBirth ? ` · ${tFormat(siteLocale, "providerPortal.operations.dob", { value: account.dateOfBirth })}` : ""}
                        </small>
                      </div>
                      <Badge>{t(siteLocale, "providerPortal.operations.userAccount")}</Badge>
                    </article>
                  ))
                ) : (
                  <small>{t(siteLocale, "providerPortal.operations.noUserAccounts")}</small>
                )}
              </div>

              <Section title={t(siteLocale, "providerPortal.operations.userOversight")}>
                <div className="list-stack">
                  {staffRegisteredUsersForShelter.length ? (
                    staffRegisteredUsersForShelter.map((account) => (
                      <article className="list-item" key={`overview-${account.id}`}>
                        <div>
                          <h3>{account.preferredName || account.legalName}</h3>
                          <p>{account.legalName}</p>
                          <div className="badge-row">
                            <Badge tone={account.localPrecinctNotified ? "success" : "warning"}>
                              {account.localPrecinctNotified ? t(siteLocale, "providerPortal.operations.precinctNotified") : t(siteLocale, "providerPortal.operations.precinctNotNotified")}
                            </Badge>
                            <Badge tone={account.foundPermanentHousing ? "success" : "neutral"}>
                              {account.foundPermanentHousing ? t(siteLocale, "providerPortal.operations.housingFound") : t(siteLocale, "providerPortal.operations.housingNotFound")}
                            </Badge>
                            {account.easyBotCheckStatus === "failed" ? <Badge tone="warning">{t(siteLocale, "providerPortal.operations.healthCheck")}</Badge> : null}
                          </div>
                        </div>
                      </article>
                    ))
                  ) : (
                    <small>{t(siteLocale, "providerPortal.operations.noShelterUsers")}</small>
                  )}
                </div>
                <div className="list-stack">
                  {preferredShelterMentionUsers.length ? (
                    preferredShelterMentionUsers.map((account) => (
                      <article className="list-item" key={`preferred-${account.id}`}>
                        <div>
                          <h3>{account.preferredName || account.legalName}</h3>
                          <p>{account.legalName}</p>
                          <div className="badge-row">
                            <Badge tone={account.localPrecinctNotified ? "success" : "warning"}>
                              {account.localPrecinctNotified ? t(siteLocale, "providerPortal.operations.precinctNotified") : t(siteLocale, "providerPortal.operations.precinctNotNotified")}
                            </Badge>
                            <Badge tone={account.foundPermanentHousing ? "success" : "neutral"}>
                              {account.foundPermanentHousing ? t(siteLocale, "providerPortal.operations.housingFound") : t(siteLocale, "providerPortal.operations.housingNotFound")}
                            </Badge>
                            {account.easyBotCheckStatus === "failed" ? <Badge tone="warning">{t(siteLocale, "providerPortal.operations.healthCheck")}</Badge> : null}
                          </div>
                        </div>
                      </article>
                    ))
                  ) : (
                    <small>{t(siteLocale, "providerPortal.operations.noPreferredUsers")}</small>
                  )}
                </div>
              </Section>
            </>
          )}
        </div>
      </Section>
      <Section title={t(siteLocale, "providerPortal.operations.sharedDeviceSafety")}>
        <div className="checklist">
          <label>
            <input
              checked={checklist.userPresent}
              onChange={(event) => setChecklist({ ...checklist, userPresent: event.target.checked })}
              type="checkbox"
            />{" "}
            {t(siteLocale, "providerPortal.operations.confirmUserPresent")}
          </label>
          <label>
            <input
              checked={checklist.clearBrowserData}
              onChange={(event) => setChecklist({ ...checklist, clearBrowserData: event.target.checked })}
              type="checkbox"
            />{" "}
            {t(siteLocale, "providerPortal.operations.clearBrowserData")}
          </label>
          <label>
            <input
              checked={checklist.auditLogConfirmed}
              onChange={(event) => setChecklist({ ...checklist, auditLogConfirmed: event.target.checked })}
              type="checkbox"
            />{" "}
            {t(siteLocale, "providerPortal.operations.auditLog")}
          </label>
        </div>
      </Section>
      <Section title={t(siteLocale, "providerPortal.operations.providerAdministrator")}>
        <label className="consent-box">
          <input
            checked={isShelterAdmin}
            onChange={(event) => {
              setIsShelterAdmin(event.target.checked);
              if (event.target.checked) {
                setAdminShelter(operatorShelter);
              }
            }}
            type="checkbox"
          />
          <span>
            <strong>{t(siteLocale, "providerPortal.operations.isAdministrator")}</strong>
          </span>
        </label>
        {isShelterAdmin ? (
          <div className="shelter-staff-panel provider-admin-panel">
            <Field label={t(siteLocale, "providerPortal.operations.provider")} required>
              <select value={adminShelter} onChange={(event) => setAdminShelter(event.target.value)}>
                {shelterOptions.map((shelter) => (
                  <option key={shelter} value={shelter}>
                    {shelter}
                  </option>
                ))}
              </select>
            </Field>
            <Section title={t(siteLocale, "providerPortal.operations.addStaffMember")}>
              <form className="form-grid provider-admin-staff-form" onSubmit={createStaffAccount}>
                <Field label={t(siteLocale, "providerPortal.operations.staffName")} required>
                  <input
                    value={staffDraft.displayName}
                    onChange={(event) => setStaffDraft({ ...staffDraft, displayName: event.target.value })}
                  />
                </Field>
                <Field label={t(siteLocale, "providerPortal.operations.staffEmail")}>
                  <input
                    type="email"
                    value={staffDraft.email}
                    onChange={(event) => setStaffDraft({ ...staffDraft, email: event.target.value })}
                  />
                </Field>
                <div className="full-span row-actions">
                  <Button disabled={!staffDraft.displayName.trim()} type="submit">
                    <UsersRound aria-hidden="true" size={18} />
                    {t(siteLocale, "providerPortal.operations.addStaff")}
                  </Button>
                </div>
              </form>
            </Section>
            <Section title={t(siteLocale, "providerPortal.operations.staffRoster")}>
            <div className="list-stack">
              {staffForShelter.length ? (
                staffForShelter.map((account) => (
                  <article className="list-item provider-staff-roster-item" key={account.id}>
                    <div>
                      <h3>{account.displayName}</h3>
                      <p>{account.email || t(siteLocale, "providerPortal.analytics.noEmail")}</p>
                      <div className="badge-row">
                        <Badge tone={account.verified ? "success" : "warning"}>
                          {account.verified ? t(siteLocale, "contacts.verified") : t(siteLocale, "providerPortal.operations.revoked")}
                        </Badge>
                        <Badge>{formatShelterDate(account.updatedAt)}</Badge>
                      </div>
                    </div>
                    <div className="row-actions">
                      <Button onClick={() => updateStaffVerification(account.id, !account.verified)} variant="secondary">
                        {account.verified ? t(siteLocale, "providerPortal.operations.revokeAccess") : t(siteLocale, "providerPortal.operations.reverify")}
                      </Button>
                      <Button onClick={() => removeStaffAccount(account.id)} variant="danger">
                        {t(siteLocale, "providerPortal.operations.removeStaff")}
                      </Button>
                    </div>
                  </article>
                ))
              ) : (
                <small>{t(siteLocale, "providerPortal.operations.noStaffAccounts")}</small>
              )}
            </div>
            </Section>
          </div>
        ) : null}
      </Section>
        </>
      ) : null}
    </div>
  );
}
