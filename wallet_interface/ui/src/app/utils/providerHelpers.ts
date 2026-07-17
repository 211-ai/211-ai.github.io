import type {
  ProofReceiptView
} from "../../models/abby";
import { t, type SupportedLocale } from "../../shared/lib/localization";
import {
  providerEligibilityCriteria,
  type ShelterCasePriority,
  type ShelterCaseStatus,
  type ShelterEligibilityCriterion,
  type ShelterUserAccount
} from "../appState";

function generateStableClientIdSuffix(value: string): string {
  let hash = 5381;
  for (let index = 0; index < value.length; index += 1) {
    hash = (hash * 33) ^ value.charCodeAt(index);
  }
  return (hash >>> 0).toString(36);
}

export function contactLabelForShelterUser(account: ShelterUserAccount, locale: SupportedLocale): string {
  return account.phone || account.email || t(locale, "providerPortal.operations.noContact");
}

export function formatShelterDate(value: string): string {
  const dateOnly = value.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  const date = dateOnly
    ? new Date(Number(dateOnly[1]), Number(dateOnly[2]) - 1, Number(dateOnly[3]))
    : new Date(value);
  if (Number.isNaN(date.getTime())) return value || "Date unavailable";
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

export function providerClientCommitment(account: ShelterUserAccount): string {
  return generateStableClientIdSuffix(`${account.id}:${account.dateOfBirth}`);
}

export function providerProofClientLabel(proof: ProofReceiptView, accounts: ShelterUserAccount[]): string {
  const client = accounts.find((account) => providerClientCommitment(account) === proof.publicInputs.client_commitment);
  return client ? client.preferredName || client.legalName : "Committed client";
}

export function providerCasePriorityRank(priority: ShelterCasePriority): number {
  if (priority === "urgent") return 0;
  if (priority === "standard") return 1;
  return 2;
}

export function providerCasePriorityLabel(priority: ShelterCasePriority, locale: SupportedLocale): string {
  if (priority === "urgent") return t(locale, "providerPortal.cases.urgent");
  if (priority === "standard") return t(locale, "providerPortal.cases.standard");
  return t(locale, "providerPortal.cases.monitor");
}

export function providerCaseStatusLabel(status: ShelterCaseStatus, locale: SupportedLocale): string {
  if (status === "intake") return t(locale, "providerPortal.cases.intake");
  if (status === "active") return t(locale, "providerPortal.cases.active");
  if (status === "waiting_on_client") return t(locale, "providerPortal.cases.waitingOnClient");
  if (status === "eligible") return t(locale, "providerPortal.cases.eligible");
  return t(locale, "providerPortal.cases.closed");
}

export function providerEligibilityLabel(criterionId: ShelterEligibilityCriterion, locale: SupportedLocale): string {
  if (criterionId === "us_citizen") return t(locale, "providerPortal.criteria.usCitizen");
  if (criterionId === "service_area_resident") return t(locale, "providerPortal.criteria.serviceAreaResident");
  if (criterionId === "income_eligible") return t(locale, "providerPortal.criteria.incomeEligible");
  if (criterionId === "identity_verified") return t(locale, "providerPortal.criteria.identityVerified");
  return providerEligibilityCriteria.find((criterion) => criterion.id === criterionId)?.label ?? criterionId;
}

export function providerEligibilityClaim(criterionId: ShelterEligibilityCriterion, locale: SupportedLocale): string {
  if (criterionId === "us_citizen") return t(locale, "providerPortal.criteria.claim.usCitizen");
  if (criterionId === "service_area_resident") return t(locale, "providerPortal.criteria.claim.serviceAreaResident");
  if (criterionId === "income_eligible") return t(locale, "providerPortal.criteria.claim.incomeEligible");
  if (criterionId === "identity_verified") return t(locale, "providerPortal.criteria.claim.identityVerified");
  return t(locale, "providerPortal.proofs.defaultEligibilityClaim");
}

export function providerProofTypeLabel(proofType: string | undefined, locale: SupportedLocale): string {
  if (!proofType) return "";
  if (proofType === "service_attendance") return t(locale, "providerPortal.proofs.proofType.serviceAttendance");
  if (proofType === "document_reviewed") return t(locale, "providerPortal.proofs.proofType.documentReviewed");
  if (proofType === "benefits_referral") return t(locale, "providerPortal.proofs.proofType.benefitsReferral");
  if (proofType === "housing_step") return t(locale, "providerPortal.proofs.proofType.housingStep");
  if (proofType === "us_citizenship") return t(locale, "providerPortal.proofs.proofType.usCitizenship");
  if (proofType === "service_area_residency") return t(locale, "providerPortal.proofs.proofType.serviceAreaResidency");
  if (proofType === "income_eligibility") return t(locale, "providerPortal.proofs.proofType.incomeEligibility");
  if (proofType === "identity_verified") return t(locale, "providerPortal.proofs.proofType.identityVerified");
  return proofType.replace(/_/g, " ");
}

export function providerProofVerificationStatusLabel(status: string, locale: SupportedLocale): string {
  if (status === "verified") return t(locale, "providerPortal.proofs.verificationStatus.verified");
  return status;
}

export function formatProviderPercent(value: number, total: number): string {
  if (!total) return "0%";
  return `${Math.round((value / total) * 100)}%`;
}

export function latestProviderTimestamp(values: string[]): string | undefined {
  return values
    .map((value) => ({ value, time: new Date(value).getTime() }))
    .filter((item) => Number.isFinite(item.time))
    .sort((left, right) => right.time - left.time)[0]?.value;
}

export function formatProviderActivityDate(value: string | undefined, locale: SupportedLocale): string {
  if (!value) return t(locale, "providerPortal.analytics.noActivity");
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString(locale, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}

export function providerActivityToneLabel(tone: "neutral" | "warning" | "success", locale: SupportedLocale): string {
  if (tone === "success") return t(locale, "providerPortal.analytics.toneSuccess");
  if (tone === "warning") return t(locale, "providerPortal.analytics.toneWarning");
  return t(locale, "providerPortal.analytics.toneNeutral");
}
