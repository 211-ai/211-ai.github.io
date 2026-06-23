import type {
  CheckInPolicyDraft,
  DisclosureRecipientDraft,
  RegistrationProfileDraft,
  UploadItem
} from "../../models/abby";
import { PORTLAND_POLICE_MISSING_EMAIL } from "./formatHelpers";

// ─── Dead-drop timing helpers ─────────────────────────────────────────────────

export function formatDeadDropFileTimestamp(date = new Date()): string {
  return date.toISOString().replace(/[:.]/g, "-");
}

export function getMissingPersonDeadDropDueAt(policy: CheckInPolicyDraft): string {
  const lastCheckInAtMs = Date.parse(policy.lastCheckInAt);
  if (!Number.isFinite(lastCheckInAtMs)) return "";
  const intervalDays = Math.max(1, Math.round(policy.intervalDays || 1));
  const gracePeriodHours = Math.max(0, Math.round(policy.gracePeriodHours || 0));
  const dueAtMs = lastCheckInAtMs + intervalDays * 24 * 60 * 60 * 1000 + gracePeriodHours * 60 * 60 * 1000;
  return new Date(dueAtMs).toISOString();
}

export function isMissingPersonDeadDropDue(policy: CheckInPolicyDraft): boolean {
  const dueAt = getMissingPersonDeadDropDueAt(policy);
  return Boolean(dueAt) && Date.now() >= Date.parse(dueAt);
}

// ─── Dead-drop bundle builders ────────────────────────────────────────────────

export function buildMissingPersonDeadDropBundle(
  profile: RegistrationProfileDraft,
  uploads: UploadItem[],
  recipients: DisclosureRecipientDraft[]
) {
  const preferredName = profile.preferredName.trim() || profile.legalName.trim() || "Unknown";
  const policeRecipients = recipients
    .filter((recipient) => recipient.type === "police_precinct")
    .map((recipient) => ({
      name: recipient.displayName,
      precinct: recipient.precinctName,
      email: recipient.email,
      phone: recipient.phone
    }));

  return {
    schemaVersion: "abby-missing-person-dead-drop-v1",
    generatedAt: new Date().toISOString(),
    policeNotificationTarget: PORTLAND_POLICE_MISSING_EMAIL,
    person: {
      preferredName,
      legalName: profile.legalName.trim(),
      dateOfBirth: profile.dateOfBirth,
      phone: profile.phone.trim(),
      email: profile.email.trim(),
      currentLocation: profile.currentLocation.trim(),
      shelterAffiliation: profile.shelterAffiliation.trim()
    },
    walletContents: uploads.map((upload) => ({
      id: upload.id,
      fileName: upload.fileName,
      machineSummary: upload.machineSummary,
      category: upload.category,
      sensitivity: upload.sensitivity,
      status: upload.status,
      shared: upload.shared,
      sharingMode: upload.sharingMode ?? "private",
      decentralizedStorageStatus: upload.decentralizedStorageStatus ?? "not_configured",
      decentralizedStorageProvider: upload.decentralizedStorageProvider ?? "local"
    })),
    knownPoliceRecipients: policeRecipients
  };
}

export function buildMissingPersonDeadDropEmail(
  policy: CheckInPolicyDraft,
  profile: RegistrationProfileDraft,
  uploads: UploadItem[],
  recipients: DisclosureRecipientDraft[]
) {
  const bundle = buildMissingPersonDeadDropBundle(profile, uploads, recipients);
  const dueAt = getMissingPersonDeadDropDueAt(policy);
  const lastCheckInAt = Number.isFinite(Date.parse(policy.lastCheckInAt)) ? policy.lastCheckInAt : "";
  const timestampSource = dueAt || lastCheckInAt || new Date().toISOString();
  const fileName = `abby-missing-person-wallet-dead-drop-${formatDeadDropFileTimestamp(new Date(timestampSource))}.json`;
  const personLabel = bundle.person.preferredName || "Unknown";
  const walletLines = bundle.walletContents.length
    ? bundle.walletContents
        .map((item, index) => `${index + 1}. ${item.fileName} (${item.category}, ${item.sensitivity}, ${item.status})`)
        .join("\n")
    : "No wallet files are currently stored.";
  const body = [
    "Hello Portland Police Missing Persons Unit,",
    "",
    `Please use this Abby emergency dead-drop bundle to support a missing-person report for ${personLabel}.`,
    "",
    `Name: ${bundle.person.legalName || bundle.person.preferredName || "Unknown"}`,
    `Date of birth: ${bundle.person.dateOfBirth || "Unknown"}`,
    `Phone: ${bundle.person.phone || "Unknown"}`,
    `Email: ${bundle.person.email || "Unknown"}`,
    `Last known location: ${bundle.person.currentLocation || "Unknown"}`,
    "",
    `Wallet contents (${bundle.walletContents.length}):`,
    walletLines,
    "",
    `Dead-drop JSON bundle filename: ${fileName}`,
    "Please review the attached dead-drop JSON bundle for structured evidence metadata.",
    "",
    "Submitted from Abby missing-person safety setting."
  ].join("\n");
  return {
    toEmail: PORTLAND_POLICE_MISSING_EMAIL,
    subject: "Missing person report dead drop bundle",
    body,
    bundle,
    bundleFileName: fileName,
    dueAt,
    lastCheckInAt: policy.lastCheckInAt
  };
}

export function buildMissingPersonDeadDropSyncPayload(
  enabled: boolean,
  policy: CheckInPolicyDraft,
  profile: RegistrationProfileDraft,
  uploads: UploadItem[],
  recipients: DisclosureRecipientDraft[]
) {
  return {
    enabled,
    ...buildMissingPersonDeadDropEmail(policy, profile, uploads, recipients)
  };
}
