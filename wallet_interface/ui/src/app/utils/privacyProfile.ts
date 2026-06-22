import { generateHuggingFaceWalletRouterText } from "../../lib/huggingFaceWalletRouterClient";
import { generateOpenRouterText } from "../../lib/openRouterClient";
import type { UploadItem, WalletGrantReceipt } from "../../models/abby";
import {
  analyzeRecordFormRedactedWithGrant,
  analyzeRecordRedactedWithGrant,
  createRecordVectorProfileWithGrant,
  createRedactedGraphRAG,
  extractRecordTextRedactedWithGrant,
  type WalletApiConfig
} from "../../services/walletApi";

export type RecipientAnalysisMode = "summary" | "redacted" | "vector" | "extract-text" | "form" | "graphrag";

export function receiptHasAbility(receipt: WalletGrantReceipt, ability: string) {
  return receipt.abilities.includes("*") || receipt.abilities.includes(ability);
}

export function receiptRequiresUserPresence(receipt: WalletGrantReceipt) {
  return receipt.caveats?.user_presence_required === true || receipt.caveats?.require_user_presence === true;
}

export function outputTypeForAnalysisMode(mode: RecipientAnalysisMode) {
  if (mode === "redacted") return "redacted_derived_only";
  if (mode === "vector") return "vector_profile";
  if (mode === "extract-text") return "redacted_extracted_text";
  if (mode === "form") return "redacted_form_analysis";
  if (mode === "graphrag") return "redacted_graphrag";
  return "summary";
}

export async function runDerivedAnalysis(
  apiConfig: WalletApiConfig,
  receipt: WalletGrantReceipt,
  mode: Exclude<RecipientAnalysisMode, "summary">,
  invocationToken?: string
) {
  const grantId = receipt.grantId;
  const recordId = receipt.recordId || "";
  if (mode === "redacted") return analyzeRecordRedactedWithGrant(apiConfig, { grantId, invocationToken, recordId });
  if (mode === "vector") return createRecordVectorProfileWithGrant(apiConfig, { grantId, invocationToken, recordId });
  if (mode === "extract-text") return extractRecordTextRedactedWithGrant(apiConfig, { grantId, invocationToken, recordId });
  if (mode === "form") return analyzeRecordFormRedactedWithGrant(apiConfig, { grantId, invocationToken, recordId });
  return createRedactedGraphRAG(apiConfig, { grantId, invocationToken, recordIds: [recordId] });
}

export function artifactLines(artifact: {
  artifactType: string;
  outputPolicy: string;
  encryptedPayloadRef: string;
  sourceRecordIds: string[];
}) {
  return [
    `${artifact.artifactType} · ${artifact.outputPolicy}`,
    artifact.encryptedPayloadRef,
    ...artifact.sourceRecordIds
  ];
}

export function analysisLines(result: {
  artifact: { artifactType: string; outputPolicy: string; encryptedPayloadRef: string; sourceRecordIds: string[] };
  output: Record<string, unknown>;
}) {
  return [
    ...artifactLines(result.artifact),
    summarizeDerivedOutput(result.output)
  ];
}

export function summarizeDerivedOutput(output: Record<string, unknown>) {
  const organizerProfile = output.openrouter_organizer_profile;
  if (organizerProfile && typeof organizerProfile === "object" && !Array.isArray(organizerProfile)) {
    const record = organizerProfile as Record<string, unknown>;
    const summary = typeof record.summary === "string" ? record.summary.trim() : "";
    if (summary) return summary;
  }
  if (typeof output.summary === "string" && output.summary.trim()) return output.summary;
  if (typeof output.text === "string" && output.text.trim()) return output.text;
  const profile = output.profile;
  if (profile && typeof profile === "object" && !Array.isArray(profile)) {
    const record = profile as Record<string, unknown>;
    const profileType = typeof record.profile_type === "string" ? record.profile_type : "vector profile";
    return typeof record.chunk_count === "number" ? `${profileType} · ${record.chunk_count} chunks` : profileType;
  }
  const fields = output.fields;
  if (Array.isArray(fields)) {
    const labels = fields
      .map((field) => {
        if (!field || typeof field !== "object" || Array.isArray(field)) return "";
        return String((field as Record<string, unknown>).label ?? "").trim();
      })
      .filter(Boolean)
      .slice(0, 3);
    return labels.length ? `${fields.length} redacted fields: ${labels.join(", ")}` : `${fields.length} redacted fields`;
  }
  const graph = output.graph;
  if (graph && typeof graph === "object" && !Array.isArray(graph)) {
    const record = graph as Record<string, unknown>;
    const graphType = typeof record.graph_type === "string" ? record.graph_type : "redacted graph";
    if (typeof record.node_count === "number" && typeof record.edge_count === "number") {
      return `${graphType} · ${record.node_count} nodes · ${record.edge_count} edges`;
    }
    return graphType;
  }
  return typeof output.output_policy === "string" ? output.output_policy : "Safe derived output created.";
}

export async function buildOpenRouterOrganizerProfile({
  fileName,
  mimeType,
  outputs
}: {
  fileName: string;
  mimeType: string;
  outputs: Record<string, unknown>[];
}): Promise<Record<string, unknown> | undefined> {
  const safeSignals = outputs.map(toSafeOrganizerSignal).filter((signal) => Object.keys(signal).length > 0);
  const prompt = {
    prompt: "Create privacy-preserving organizer metadata from redacted wallet document signals.",
    systemPrompt: [
      "You create privacy-preserving document organizer metadata for a wallet app.",
      "Use only redacted derived signals. Do not infer names, addresses, account numbers, medical facts, legal facts, or other private content.",
      "Return only one JSON object with keys: summary, labels, browseHints, riskSignals.",
      "summary must be a short generic description. labels, browseHints, and riskSignals must be arrays of generic non-identifying strings."
    ].join("\n"),
    userPrompt: JSON.stringify({
      fileName: redactFileNameForRemoteProfile(fileName),
      mimeType,
      redactedSignals: safeSignals.slice(0, 8)
    })
  };
  try {
    const result = await generateHuggingFaceWalletRouterText({
      fallbackReason: "wallet_document_privacy_profile",
      maxTokens: 350,
      prompt
    });
    return normalizeOrganizerProfileJson(result.text, result.model);
  } catch {
    // OpenRouter is a secondary fallback after the wallet-scoped Hugging Face router.
  }
  try {
    const result = await generateOpenRouterText({
      fallbackReason: "wallet_document_privacy_profile",
      localModelName: "openrouter/free",
      maxTokens: 350,
      prompt
    });
    return normalizeOrganizerProfileJson(result.text, result.model);
  } catch {
    return undefined;
  }
}

export function toSafeOrganizerSignal(output: Record<string, unknown>): Record<string, unknown> {
  const signal: Record<string, unknown> = {
    output_policy: readString(output, "output_policy"),
    summary: safeShortText(readString(output, "summary")),
    text: safeShortText(readString(output, "text"))
  };
  const profile = output.profile;
  if (profile && typeof profile === "object" && !Array.isArray(profile)) {
    signal.profile = compactRecord({
      profile_type: readString(profile, "profile_type"),
      chunk_count: readNumber(profile, "chunk_count")
    });
  }
  const graph = output.graph;
  if (graph && typeof graph === "object" && !Array.isArray(graph)) {
    signal.graph = compactRecord({
      graph_type: readString(graph, "graph_type"),
      node_count: readNumber(graph, "node_count"),
      edge_count: readNumber(graph, "edge_count")
    });
  }
  const fields = output.fields;
  if (Array.isArray(fields)) {
    signal.field_count = fields.length;
    signal.field_labels = fields
      .map((field) => (field && typeof field === "object" && !Array.isArray(field) ? readString(field, "label") : undefined))
      .filter(Boolean)
      .slice(0, 8);
  }
  const redactionCounts = output.redaction_counts;
  if (redactionCounts && typeof redactionCounts === "object" && !Array.isArray(redactionCounts)) {
    signal.redaction_counts = Object.fromEntries(
      Object.entries(redactionCounts)
        .filter(([, value]) => typeof value === "number")
        .slice(0, 8)
    );
  }
  return compactRecord(signal);
}

export function buildPrivacySearchText(outputs: Record<string, unknown>[], publicInputs: Record<string, unknown>): string {
  return [
    "zero knowledge proof",
    "redacted vector profile",
    ...buildPrivacyVectorTerms(outputs, publicInputs),
    stringifyPrivacySearchValue(publicInputs)
  ]
    .join(" ")
    .replace(/\s+/g, " ")
    .trim();
}

export function buildPrivacyVectorTerms(outputs: Record<string, unknown>[], publicInputs: Record<string, unknown>): string[] {
  const terms = new Set<string>();
  const add = (value: unknown) => {
    for (const part of privacySearchParts(value)) {
      const normalized = part.trim().toLocaleLowerCase();
      if (normalized.length >= 2 && normalized.length <= 80) terms.add(normalized);
    }
  };
  add(publicInputs);
  for (const output of outputs) {
    add(toSafeOrganizerSignal(output));
  }
  return Array.from(terms).slice(0, 80);
}

export function stringifyPrivacySearchValue(value: unknown): string {
  return privacySearchParts(value).join(" ");
}

function privacySearchParts(value: unknown): string[] {
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") return [String(value)];
  if (Array.isArray(value)) return value.flatMap(privacySearchParts);
  if (value && typeof value === "object") {
    return Object.entries(value as Record<string, unknown>).flatMap(([key, nestedValue]) => [key, ...privacySearchParts(nestedValue)]);
  }
  return [];
}

function normalizeOrganizerProfileJson(text: string, model: string): Record<string, unknown> | undefined {
  const parsed = parseFirstJsonObject(text);
  if (!parsed) return undefined;
  const summary = safeShortText(typeof parsed.summary === "string" ? parsed.summary : "");
  const labels = readSafeStringList(parsed.labels, 6);
  const browseHints = readSafeStringList(parsed.browseHints, 6);
  const riskSignals = readSafeStringList(parsed.riskSignals, 6);
  if (!summary && !labels.length && !browseHints.length && !riskSignals.length) return undefined;
  return compactRecord({
    browseHints,
    labels,
    model,
    riskSignals,
    summary
  });
}

function parseFirstJsonObject(text: string): Record<string, unknown> | undefined {
  const trimmed = text.trim();
  const start = trimmed.indexOf("{");
  const end = trimmed.lastIndexOf("}");
  if (start < 0 || end <= start) return undefined;
  try {
    const parsed = JSON.parse(trimmed.slice(start, end + 1));
    return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed as Record<string, unknown> : undefined;
  } catch {
    return undefined;
  }
}

function readSafeStringList(value: unknown, limit: number): string[] {
  if (!Array.isArray(value)) return [];
  return value
    .map((item) => safeShortText(typeof item === "string" ? item : ""))
    .filter(Boolean)
    .slice(0, limit);
}

function safeShortText(value: string | undefined): string {
  return (value || "")
    .replace(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi, "[email]")
    .replace(/\b(?:\+?1[\s.-]?)?(?:\(\d{3}\)|\d{3})[\s.-]?\d{3}[\s.-]?\d{4}\b/g, "[phone]")
    .replace(/\b\d{4,}\b/g, "[number]")
    .trim()
    .slice(0, 240);
}

function redactFileNameForRemoteProfile(fileName: string): string {
  const extension = fileName.split(".").pop()?.toLowerCase();
  return extension && extension !== fileName.toLowerCase() ? `document.${extension}` : "document";
}

export function buildFallbackDocumentProfileOutput(upload: UploadItem, mimeType: string): Record<string, unknown> {
  return {
    output_policy: "local_metadata_only",
    profile: {
      chunk_count: 0,
      profile_type: "metadata fallback"
    },
    summary: `${mimeType} wallet file queued for redacted profiling.`,
    upload_state: compactRecord({
      decentralizedStorageStatus: upload.decentralizedStorageStatus,
      hasIpfsCid: Boolean(upload.ipfsCid),
      mimeType
    })
  };
}

export function buildDocumentPrivacyProfilePublicInputs({
  artifactIds,
  file,
  fileName,
  mimeType,
  outputs
}: {
  artifactIds: string[];
  file?: File;
  fileName: string;
  mimeType: string;
  outputs: Record<string, unknown>[];
}): Record<string, unknown> {
  const graphOutput = outputs
    .map((output) => output.graph)
    .find((graph) => graph && typeof graph === "object" && !Array.isArray(graph)) as Record<string, unknown> | undefined;
  const profileOutput = outputs
    .map((output) => output.profile)
    .find((profile) => profile && typeof profile === "object" && !Array.isArray(profile)) as Record<string, unknown> | undefined;
  const organizerProfile = outputs
    .map((output) => output.openrouter_organizer_profile)
    .find((profile) => profile && typeof profile === "object" && !Array.isArray(profile)) as Record<string, unknown> | undefined;
  const redactionCount = outputs.reduce((count, output) => {
    const counts = output.redaction_counts;
    if (!counts || typeof counts !== "object" || Array.isArray(counts)) return count;
    return count + Object.values(counts).reduce((sum, value) => sum + (typeof value === "number" ? value : 0), 0);
  }, 0);
  const publicMimeType = normalizePublicMimeType(mimeType, file?.name || fileName);
  return {
    artifact_ids: artifactIds,
    chunk_count: readNumber(profileOutput, "chunk_count"),
    edge_count: readNumber(graphOutput, "edge_count"),
    graph_type: readString(graphOutput, "graph_type"),
    mime_family: publicMimeType.split("/")[0] || "application",
    mime_type: publicMimeType,
    node_count: readNumber(graphOutput, "node_count"),
    openrouter_model: readString(organizerProfile, "model"),
    organizer_labels: readStringArray(organizerProfile, "labels") || defaultLabelsForMimeType(publicMimeType),
    organizer_summary: readString(organizerProfile, "summary") || displayMimeType(publicMimeType),
    output_policies: Array.from(new Set(outputs.map((output) => readString(output, "output_policy")).filter(Boolean))),
    privacy_policy: "no_plaintext_public_inputs",
    profile_methods: Array.from(new Set(outputs.map((output) => readString(output, "output_policy")).filter(Boolean))),
    redaction_count: redactionCount,
    size_bucket: typeof file?.size === "number" ? sizeBucket(file.size) : "unknown",
    summary: "Redacted GraphRAG, vector metadata, and derived descriptors created inside the wallet boundary."
  };
}

export function summarizeDocumentPrivacyProfile(publicInputs: Record<string, unknown>) {
  const mimeType = typeof publicInputs.mime_type === "string" ? publicInputs.mime_type : "document";
  const graphType = typeof publicInputs.graph_type === "string" ? publicInputs.graph_type : "redacted graph";
  const nodes = typeof publicInputs.node_count === "number" ? `${publicInputs.node_count} nodes` : "safe graph";
  const chunks = typeof publicInputs.chunk_count === "number" ? `${publicInputs.chunk_count} chunks` : "vector metadata";
  return `${mimeType} · ${graphType} · ${nodes} · ${chunks}`;
}

export function classifyDocumentProfile(publicInputs: Record<string, unknown>) {
  const organizerSummary = readString(publicInputs, "organizer_summary");
  if (organizerSummary) return organizerSummary;
  const labels = readStringArray(publicInputs, "organizer_labels");
  if (labels?.length) return labels.slice(0, 3).join(", ");
  return displayMimeType(readString(publicInputs, "mime_type") || "");
}

export function displayMimeType(mimeType: string) {
  const normalized = mimeType.trim().toLowerCase();
  if (!normalized) return "Unknown file";
  if (normalized === "application/pdf") return "PDF document";
  if (normalized.startsWith("image/")) return `${normalized.split("/")[1]?.toUpperCase() || "Image"} image`;
  if (normalized.startsWith("text/")) return "Text document";
  if (normalized.includes("json")) return "JSON data";
  if (normalized.includes("spreadsheet") || normalized.includes("excel") || normalized.includes("csv")) return "Spreadsheet";
  if (normalized.includes("wordprocessing") || normalized.includes("msword")) return "Word document";
  if (normalized.includes("presentation") || normalized.includes("powerpoint")) return "Presentation";
  if (normalized.startsWith("audio/")) return "Audio file";
  if (normalized.startsWith("video/")) return "Video file";
  if (normalized === "application/octet-stream") return "Encrypted/binary file";
  return normalized;
}

export function detectDecryptedMimeType(bytes: Uint8Array, fileName: string, text: string) {
  const signature = Array.from(bytes.slice(0, 16));
  if (startsWithBytes(signature, [0x25, 0x50, 0x44, 0x46])) return "application/pdf";
  if (startsWithBytes(signature, [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a])) return "image/png";
  if (startsWithBytes(signature, [0xff, 0xd8, 0xff])) return "image/jpeg";
  if (startsWithBytes(signature, [0x47, 0x49, 0x46, 0x38])) return "image/gif";
  if (startsWithBytes(signature, [0x50, 0x4b, 0x03, 0x04])) return officeOrZipMimeType(fileName);
  const trimmed = text.trim();
  if ((trimmed.startsWith("{") && trimmed.endsWith("}")) || (trimmed.startsWith("[") && trimmed.endsWith("]"))) {
    try {
      JSON.parse(trimmed);
      return "application/json";
    } catch {
      // Fall back to extension/text detection below.
    }
  }
  const extensionMimeType = mimeTypeFromFileName(fileName);
  if (extensionMimeType) return extensionMimeType;
  return looksLikeText(bytes) ? "text/plain" : "application/octet-stream";
}

function startsWithBytes(bytes: number[], prefix: number[]) {
  return prefix.every((value, index) => bytes[index] === value);
}

function officeOrZipMimeType(fileName: string) {
  const extensionMimeType = mimeTypeFromFileName(fileName);
  return extensionMimeType || "application/zip";
}

function mimeTypeFromFileName(fileName: string) {
  const extension = fileName.split(".").pop()?.toLowerCase() ?? "";
  if (extension === "pdf") return "application/pdf";
  if (["jpg", "jpeg"].includes(extension)) return "image/jpeg";
  if (extension === "png") return "image/png";
  if (extension === "gif") return "image/gif";
  if (extension === "txt") return "text/plain";
  if (extension === "json") return "application/json";
  if (extension === "csv") return "text/csv";
  if (extension === "doc") return "application/msword";
  if (extension === "docx") return "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
  if (extension === "xls") return "application/vnd.ms-excel";
  if (extension === "xlsx") return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
  if (extension === "ppt") return "application/vnd.ms-powerpoint";
  if (extension === "pptx") return "application/vnd.openxmlformats-officedocument.presentationml.presentation";
  if (extension === "zip") return "application/zip";
  return "";
}

function looksLikeText(bytes: Uint8Array) {
  const sample = bytes.slice(0, Math.min(bytes.length, 512));
  if (!sample.length) return true;
  let printable = 0;
  for (const byte of sample) {
    if (byte === 9 || byte === 10 || byte === 13 || (byte >= 32 && byte < 127) || byte >= 194) {
      printable += 1;
    }
  }
  return printable / sample.length > 0.85;
}

export function defaultLabelsForMimeType(mimeType: string) {
  const label = displayMimeType(mimeType);
  return label === "Unknown file" ? [] : [label];
}

export function normalizePublicMimeType(mimeType: string, fileName: string) {
  const trimmed = mimeType.trim().toLowerCase();
  if (trimmed) return trimmed;
  const extension = fileName.split(".").pop()?.toLowerCase() ?? "";
  if (extension === "pdf") return "application/pdf";
  if (["jpg", "jpeg"].includes(extension)) return "image/jpeg";
  if (extension === "png") return "image/png";
  if (extension === "txt") return "text/plain";
  if (extension === "json") return "application/json";
  return "application/octet-stream";
}

function sizeBucket(sizeBytes: number) {
  if (sizeBytes < 100_000) return "under_100kb";
  if (sizeBytes < 1_000_000) return "100kb_to_1mb";
  if (sizeBytes < 10_000_000) return "1mb_to_10mb";
  if (sizeBytes < 100_000_000) return "10mb_to_100mb";
  return "over_100mb";
}

export function readString(record: unknown, key: string) {
  if (!record || typeof record !== "object" || Array.isArray(record)) return undefined;
  const value = (record as Record<string, unknown>)[key];
  return typeof value === "string" && value.trim() ? value : undefined;
}

export function readStringArray(record: unknown, key: string) {
  if (!record || typeof record !== "object" || Array.isArray(record)) return undefined;
  const value = (record as Record<string, unknown>)[key];
  if (!Array.isArray(value)) return undefined;
  const strings = value.filter((item): item is string => typeof item === "string" && item.trim().length > 0);
  return strings.length ? strings.slice(0, 12) : undefined;
}

function readNumber(record: unknown, key: string) {
  if (!record || typeof record !== "object" || Array.isArray(record)) return undefined;
  const value = (record as Record<string, unknown>)[key];
  return typeof value === "number" && Number.isFinite(value) ? value : undefined;
}

export function compactRecord(record: Record<string, unknown>): Record<string, unknown> {
  return Object.fromEntries(
    Object.entries(record).filter(([, value]) => {
      if (value === undefined || value === null) return false;
      if (typeof value === "string") return value.trim().length > 0;
      if (Array.isArray(value)) return value.length > 0;
      return true;
    })
  );
}
