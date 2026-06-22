import type { UploadItem } from "../../models/abby";
import { normalizeIpfsGatewayUrl, sameOriginIpfsGatewayUrl } from "../../services/filecoinStorage";
import { t, tFormat, type SupportedLocale } from "../../lib/localization";

export function sharingBadge(upload: UploadItem, locale: SupportedLocale): string {
  const count = upload.allowedRecipientIds?.length ?? 0;
  if (!upload.shared || count === 0) return t(locale, "wallet.private");
  return tFormat(locale, "wallet.selectedCount", { count: String(count) });
}

export type WalletFileSortMode = "newest" | "oldest" | "name" | "type" | "profile" | "storage";
export type WalletFileFilterMode = "all" | "profiled" | "needs_proof" | "stored" | "shared";

export function getWalletFileFilterOptions(locale: SupportedLocale): Array<{ label: string; value: WalletFileFilterMode }> {
  return [
    { label: t(locale, "wallet.filter.all"), value: "all" },
    { label: t(locale, "wallet.filter.profiled"), value: "profiled" },
    { label: t(locale, "wallet.filter.needsProof"), value: "needs_proof" },
    { label: t(locale, "wallet.filter.stored"), value: "stored" },
    { label: t(locale, "wallet.filter.shared"), value: "shared" }
  ];
}

export function searchWalletFiles(
  uploads: UploadItem[],
  query: string,
  sortMode: WalletFileSortMode,
  filterMode: WalletFileFilterMode
): UploadItem[] {
  const filtered = filterWalletFilesByMode(uploads, filterMode);
  const tokens = query
    .trim()
    .toLocaleLowerCase()
    .split(/\s+/)
    .filter(Boolean);
  if (!tokens.length) return sortWalletFiles(filtered, sortMode);
  return filtered
    .map((upload) => ({ score: walletFileSearchScore(upload, tokens), upload }))
    .filter((item) => item.score > 0)
    .sort((left, right) => right.score - left.score || compareWalletFiles(left.upload, right.upload, sortMode))
    .map((item) => item.upload);
}

export function filterWalletFilesByMode(uploads: UploadItem[], filterMode: WalletFileFilterMode): UploadItem[] {
  switch (filterMode) {
    case "profiled":
      return uploads.filter((upload) => upload.privacyProfileStatus === "profiled");
    case "needs_proof":
      return uploads.filter((upload) => upload.recordId && upload.privacyProfileStatus !== "profiled");
    case "stored":
      return uploads.filter((upload) => upload.decentralizedStorageStatus === "stored" || Boolean(upload.ipfsCid));
    case "shared":
      return uploads.filter((upload) => upload.shared || (upload.allowedRecipientIds?.length ?? 0) > 0);
    case "all":
    default:
      return uploads;
  }
}

export function buildWalletFileStats(uploads: UploadItem[]) {
  return {
    ipldLinked: uploads.filter((upload) => upload.ipldLinks?.length || upload.metadataCid).length,
    profiled: uploads.filter((upload) => upload.privacyProfileStatus === "profiled").length
  };
}

export function sortWalletFiles(uploads: UploadItem[], sortMode: WalletFileSortMode): UploadItem[] {
  const sorted = [...uploads];
  sorted.sort((left, right) => compareWalletFiles(left, right, sortMode));
  return sorted;
}

function compareWalletFiles(left: UploadItem, right: UploadItem, sortMode: WalletFileSortMode): number {
  switch (sortMode) {
    case "oldest":
      return uploadCreatedTime(left) - uploadCreatedTime(right);
    case "name":
      return left.fileName.localeCompare(right.fileName) || uploadCreatedTime(right) - uploadCreatedTime(left);
    case "type":
      return uploadTypeLabel(left).localeCompare(uploadTypeLabel(right)) || left.fileName.localeCompare(right.fileName);
    case "profile":
      return uploadProfileSortRank(left) - uploadProfileSortRank(right) || left.fileName.localeCompare(right.fileName);
    case "storage":
      return uploadStorageSortRank(left) - uploadStorageSortRank(right) || left.fileName.localeCompare(right.fileName);
    case "newest":
    default:
      return uploadCreatedTime(right) - uploadCreatedTime(left);
  }
}

function walletFileSearchScore(upload: UploadItem, tokens: string[]): number {
  const proofIndex = [
    upload.privacyProfileSearchText,
    upload.privacyProfileVectorTerms?.join(" "),
    stringifySearchRecord(upload.privacyProfilePublicInputs)
  ]
    .filter(Boolean)
    .join(" ")
    .toLocaleLowerCase();
  const visibleIndex = [
    upload.fileName,
    upload.category,
    upload.machineSummary,
    upload.decentralizedStorageProvider,
    upload.decentralizedStorageStatus,
    upload.decryptedClassification,
    upload.decryptedMimeType,
    upload.filecoinPinStatus,
    upload.privacyProfileClassification,
    upload.privacyProfileLabels?.join(" "),
    upload.privacyProfileMimeType,
    upload.privacyProfileStatus,
    upload.privacyProfileSummary,
    upload.status
  ]
    .filter(Boolean)
    .join(" ")
    .toLocaleLowerCase();
  let score = 0;
  for (const token of tokens) {
    if (proofIndex.includes(token)) {
      score += 4;
      continue;
    }
    if (visibleIndex.includes(token)) {
      score += 1;
    } else {
      return 0;
    }
  }
  if (upload.privacyProfileProofId) score += 0.5;
  if (upload.privacyProfileVectorTerms?.length) score += 0.5;
  return score;
}

function stringifySearchRecord(record: Record<string, unknown> | undefined): string {
  if (!record) return "";
  return Object.entries(record)
    .flatMap(([key, value]) => [key, ...searchValueParts(value)])
    .join(" ");
}

function searchValueParts(value: unknown): string[] {
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") return [String(value)];
  if (Array.isArray(value)) return value.flatMap(searchValueParts);
  if (value && typeof value === "object") return Object.values(value as Record<string, unknown>).flatMap(searchValueParts);
  return [];
}

function uploadCreatedTime(upload: UploadItem): number {
  const time = Date.parse(upload.createdAtRaw || upload.createdAt || "");
  return Number.isFinite(time) ? time : 0;
}

export function uploadTypeLabel(upload: UploadItem): string {
  return upload.privacyProfileClassification || upload.decryptedClassification || upload.privacyProfileMimeType || upload.decryptedMimeType || upload.category;
}

function uploadProfileSortRank(upload: UploadItem): number {
  if (upload.privacyProfileStatus === "profiled") return 0;
  if (upload.privacyProfileStatus === "profiling") return 1;
  if (upload.privacyProfileStatus === "failed") return 2;
  return 3;
}

function uploadStorageSortRank(upload: UploadItem): number {
  if (upload.decentralizedStorageStatus === "stored" && upload.storageOk !== false) return 0;
  if (upload.decentralizedStorageStatus === "uploading") return 1;
  if (upload.storageOk === false) return 2;
  if (upload.decentralizedStorageStatus === "failed") return 3;
  return 4;
}

export function filecoinBadge(upload: UploadItem, locale: SupportedLocale): string {
  if (upload.filecoinPinStatus === "queued") return t(locale, "wallet.filecoinQueued");
  if (upload.filecoinPinStatus === "pinning") return t(locale, "wallet.filecoinPinning");
  if (upload.filecoinPinStatus === "failed") return t(locale, "wallet.ipfsOnly");
  if (upload.decentralizedStorageStatus === "stored") return t(locale, "wallet.ipfsFilecoin");
  if (upload.decentralizedStorageStatus === "uploading") return t(locale, "wallet.storing");
  if (upload.decentralizedStorageStatus === "failed") return t(locale, "wallet.storageFailed");
  return t(locale, "wallet.walletStorage");
}

export function filecoinBadgeTone(upload: UploadItem): "neutral" | "info" | "success" | "warning" | "danger" {
  if (upload.filecoinPinStatus === "queued" || upload.filecoinPinStatus === "pinning") return "info";
  if (upload.filecoinPinStatus === "failed") return "warning";
  if (upload.decentralizedStorageStatus === "stored") return "success";
  if (upload.decentralizedStorageStatus === "uploading") return "info";
  if (upload.decentralizedStorageStatus === "failed") return "danger";
  return "neutral";
}

export function shouldShowFilecoinAction(upload: UploadItem): boolean {
  return upload.decentralizedStorageStatus !== "stored" || upload.filecoinPinStatus === "failed";
}

export function filecoinActionLabel(upload: UploadItem, inProgress: boolean, locale: SupportedLocale): string {
  if (upload.filecoinPinStatus === "failed") {
    return inProgress ? t(locale, "wallet.retrying") : t(locale, "wallet.retryFilecoin");
  }
  return inProgress ? t(locale, "wallet.storing") : t(locale, "wallet.storeOnFilecoin");
}

export function privacyProfileBadge(upload: UploadItem, locale: SupportedLocale): string {
  if (upload.privacyProfileStatus === "profiled") return t(locale, "wallet.privacyProof");
  if (upload.privacyProfileStatus === "profiling") return t(locale, "wallet.profiling");
  if (upload.privacyProfileStatus === "failed") return t(locale, "wallet.profileFailed");
  return t(locale, "wallet.profilePending");
}

export function privacyProfileBadgeTone(upload: UploadItem): "neutral" | "info" | "success" | "warning" | "danger" {
  if (upload.privacyProfileStatus === "profiled") return "success";
  if (upload.privacyProfileStatus === "profiling") return "info";
  if (upload.privacyProfileStatus === "failed") return "warning";
  return "neutral";
}

export function ipfsGatewayHref(upload: UploadItem): string {
  return normalizeIpfsGatewayUrl(upload.ipfsGatewayUrl) || sameOriginIpfsGatewayUrl(upload.ipfsCid) || "#";
}

export function shortStorageId(value: string): string {
  return value.length > 18 ? `${value.slice(0, 10)}...${value.slice(-6)}` : value;
}

export function base64ToBytes(value: string): Uint8Array {
  const binary = atob(value);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }
  return bytes;
}
