import type { UploadItem } from "../../models/abby";
import { repairRecordStorage } from "../../services/walletApi";
import type { AppActionOptions, AppActionResult, AppActionRuntime } from "../../app/appActions";
import type {
  AgentCommandName,
  ClassifyUploadedDocumentCommandInput,
  RepairUploadStorageCommandInput,
  SummarizeUploadRequirementsCommandInput,
  ToggleUploadSharedCommandInput,
  UploadDocumentCategory,
  UploadDocumentSensitivity
} from "../commandSchemas";
import type { AgentConfirmationRisk, AgentPermissionLevel } from "../types";
import { confirmationRiskForGate, getAgentToolPermissionPolicy } from "../permissionPolicy";
import { getToolDefinition } from "../surfaceRegistry";

interface UploadClassification {
  category: UploadDocumentCategory;
  sensitivity: UploadDocumentSensitivity;
  summary: string;
  signals: string[];
}

const uploadRequirementsByGoal = [
  {
    pattern: /\b(id|identity|prove who|registration|register|benefits|snap|medicaid|clinic)\b/i,
    documents: ["photo ID", "benefits letter", "proof of address"]
  },
  {
    pattern: /\b(housing|shelter|rent|eviction|utility|address)\b/i,
    documents: ["lease or shelter letter", "utility bill", "eviction notice"]
  },
  {
    pattern: /\b(medical|health|clinic|medication|doctor|hospital)\b/i,
    documents: ["insurance card", "medical note", "appointment paperwork"]
  },
  {
    pattern: /\b(job|income|pay|employment|work)\b/i,
    documents: ["pay stub", "employment letter", "benefits award letter"]
  }
] as const;

export async function summarizeUploadRequirementsAction(
  runtime: AppActionRuntime,
  input: SummarizeUploadRequirementsCommandInput
): Promise<AppActionResult> {
  const state = runtime.getState();
  const requested = [input.goal, input.documentType].filter(Boolean).join(" ");
  const recommendations = recommendedDocuments(requested);
  const failedStorageCount = state.uploads.filter((upload) => upload.storageOk === false).length;
  const storedCount = state.uploads.filter((upload) => upload.status === "stored").length;

  return success("summarize_upload_requirements", buildUploadGuidanceSummary(recommendations, failedStorageCount), {
    metadata: {
      guidance: {
        recommendedDocuments: recommendations,
        steps: [
          "Use the upload picker to choose a file or photo.",
          "After selection, classify the uploaded record from its visible metadata.",
          "Keep uploads private unless the user confirms sharing."
        ],
        privacy: "The assistant cannot choose a local file path or read a file before the user selects it."
      },
      uploadCounts: {
        total: state.uploads.length,
        stored: storedCount,
        failedStorage: failedStorageCount,
        shared: state.uploads.filter((upload) => upload.shared).length
      }
    }
  });
}

export async function classifyUploadedDocumentAction(
  runtime: AppActionRuntime,
  input: ClassifyUploadedDocumentCommandInput
): Promise<AppActionResult> {
  if (!input.userSelected) {
    return failure(
      "classify_uploaded_document",
      "user_selected_file_required",
      "The user must select a file before Abby can classify upload metadata."
    );
  }

  const state = runtime.getState();
  const upload = findUpload(state.uploads, input);
  const classification = classifyUploadMetadata({
    fileName: input.fileName ?? upload?.fileName,
    mimeType: input.mimeType,
    machineSummary: input.machineSummary ?? upload?.machineSummary,
    categoryHint: input.categoryHint
  });

  if (upload) {
    const setUploads = requireSetter("classify_uploaded_document", runtime.setUploads, "Uploads");
    if (typeof setUploads !== "function") return setUploads;
    const updatedUpload: UploadItem = {
      ...upload,
      category: classification.category,
      sensitivity: classification.sensitivity,
      machineSummary: classification.summary
    };
    setUploads(state.uploads.map((item) => (item.id === upload.id ? updatedUpload : item)));
  }

  return success(
    "classify_uploaded_document",
    `Classified ${input.fileName ?? upload?.fileName ?? "the selected file"} as ${classification.category}.`,
    {
      artifactId: upload?.id,
      metadata: {
        classification,
        updatedUploadId: upload?.id,
        source: "user_selected_upload_metadata"
      }
    }
  );
}

export async function repairUploadStorageAction(
  runtime: AppActionRuntime,
  input: RepairUploadStorageCommandInput,
  options: AppActionOptions
): Promise<AppActionResult> {
  const blocked = requiresConfirmation("repair_upload_storage", input, options);
  if (blocked) return blocked;
  const setUploads = requireSetter("repair_upload_storage", runtime.setUploads, "Uploads");
  if (typeof setUploads !== "function") return setUploads;
  if (!runtime.walletApiConfig?.actorDid) {
    return failure("repair_upload_storage", "wallet_api_required", "Connect a wallet API before repairing upload storage.");
  }

  const state = runtime.getState();
  const upload = findUpload(state.uploads, input);
  if (!upload) return failure("repair_upload_storage", "upload_not_found", "The requested upload was not found.");
  const recordId = input.recordId?.trim() || upload.recordId;
  if (!recordId) {
    return failure("repair_upload_storage", "record_id_required", "Storage repair requires an uploaded wallet record ID.");
  }

  try {
    const storageOk = await repairRecordStorage(runtime.walletApiConfig, recordId);
    setUploads(
      state.uploads.map((item) =>
        item.id === upload.id
          ? {
              ...item,
              recordId,
              status: storageOk ? "stored" : item.status,
              storageOk
            }
          : item
      )
    );
    await runtime.refreshWalletAuditEvents?.().catch(() => undefined);
    return success("repair_upload_storage", storageOk ? "Repaired upload storage." : "Storage repair ran but still needs attention.", {
      artifactId: upload.id,
      confirmation: confirmationFor("repair_upload_storage", input),
      metadata: {
        uploadId: upload.id,
        recordId,
        storageOk
      }
    });
  } catch {
    setUploads(state.uploads.map((item) => (item.id === upload.id ? { ...item, storageOk: false } : item)));
    return failure("repair_upload_storage", "storage_repair_failed", "Upload storage repair failed.", {
      retryable: true,
      confirmation: confirmationFor("repair_upload_storage", input)
    });
  }
}

export async function toggleUploadSharedAction(
  runtime: AppActionRuntime,
  input: ToggleUploadSharedCommandInput,
  options: AppActionOptions
): Promise<AppActionResult> {
  const blocked = requiresConfirmation("toggle_upload_shared", input, options);
  if (blocked) return blocked;
  const setUploads = requireSetter("toggle_upload_shared", runtime.setUploads, "Uploads");
  if (typeof setUploads !== "function") return setUploads;

  const state = runtime.getState();
  const upload = state.uploads.find((item) => item.id === input.uploadId);
  if (!upload) return failure("toggle_upload_shared", "upload_not_found", `Upload ${input.uploadId} was not found.`);

  setUploads(state.uploads.map((item) => (item.id === input.uploadId ? { ...item, shared: input.shared } : item)));
  return success("toggle_upload_shared", `${upload.fileName} is now ${input.shared ? "shareable" : "private"}.`, {
    artifactId: upload.id,
    confirmation: confirmationFor("toggle_upload_shared", input),
    metadata: {
      uploadId: upload.id,
      fileName: upload.fileName,
      shared: input.shared,
      reason: input.reason
    }
  });
}

export function classifyUploadMetadata({
  fileName,
  mimeType,
  machineSummary,
  categoryHint
}: {
  fileName?: string;
  mimeType?: string;
  machineSummary?: string;
  categoryHint?: UploadDocumentCategory;
}): UploadClassification {
  const text = `${fileName ?? ""} ${mimeType ?? ""} ${machineSummary ?? ""}`.toLowerCase();
  const category = categoryHint ?? inferUploadCategory(text);
  const sensitivity = inferUploadSensitivity(text, category);
  const signals = buildClassificationSignals(text, category, sensitivity);
  return {
    category,
    sensitivity,
    summary: buildMachineSummary(fileName, category, sensitivity),
    signals
  };
}

function recommendedDocuments(requested: string): string[] {
  const normalized = requested.trim();
  const match = uploadRequirementsByGoal.find((item) => item.pattern.test(normalized));
  return [...(match?.documents ?? ["photo ID", "benefits or service letters", "proof of address"])];
}

function buildUploadGuidanceSummary(recommendations: string[], failedStorageCount: number): string {
  const repairNote = failedStorageCount
    ? ` ${failedStorageCount} saved upload${failedStorageCount === 1 ? "" : "s"} need storage repair.`
    : "";
  return `Use the upload picker to select files, then Abby can classify the selected upload from its metadata. Helpful documents: ${recommendations.join(", ")}.${repairNote}`;
}

function inferUploadCategory(text: string): UploadDocumentCategory {
  if (/\b(id|license|passport|birth certificate|social security|ssn)\b/.test(text)) return "Identity";
  if (/\b(snap|ebt|medicaid|medicare|benefit|tanf|ssi|ssdi|award letter)\b/.test(text)) return "Benefits";
  if (/\b(lease|rent|eviction|shelter|utility|address|housing)\b/.test(text)) return "Housing";
  if (/\b(medical|health|clinic|doctor|hospital|diagnosis|prescription|insurance)\b/.test(text)) return "Medical";
  if (/\b(court|legal|attorney|case|citation|protective order)\b/.test(text)) return "Legal";
  if (/\b(paystub|pay stub|income|wage|employment|job|tax|w2|1099)\b/.test(text)) return "Income";
  if (/\b(phone|email|contact|emergency contact)\b/.test(text)) return "Contact";
  return "Other";
}

function inferUploadSensitivity(text: string, category: UploadDocumentCategory): UploadDocumentSensitivity {
  if (/\b(ssn|social security|passport|birth certificate|protective order|diagnosis|immigration)\b/.test(text)) {
    return "restricted";
  }
  if (category === "Identity" || category === "Medical" || category === "Legal" || category === "Benefits") {
    return "high";
  }
  if (category === "Housing" || category === "Income" || category === "Contact") return "moderate";
  return "low";
}

function buildClassificationSignals(
  text: string,
  category: UploadDocumentCategory,
  sensitivity: UploadDocumentSensitivity
): string[] {
  const signals = [`category:${category}`, `sensitivity:${sensitivity}`];
  if (/\b(image|png|jpg|jpeg|heic)\b/.test(text)) signals.push("file:image");
  if (/\b(pdf)\b/.test(text)) signals.push("file:pdf");
  if (/\b(text|plain|txt)\b/.test(text)) signals.push("file:text");
  return signals;
}

function buildMachineSummary(
  fileName: string | undefined,
  category: UploadDocumentCategory,
  sensitivity: UploadDocumentSensitivity
): string {
  const cleanName = fileName?.replace(/\.[^/.]+$/, "").replace(/[_-]+/g, " ").trim();
  return `${cleanName || "Selected upload"} classified as ${category} with ${sensitivity} sensitivity`;
}

function findUpload(
  uploads: UploadItem[],
  input: { uploadId?: string; recordId?: string }
): UploadItem | undefined {
  const uploadId = input.uploadId?.trim();
  const recordId = input.recordId?.trim();
  return uploads.find((upload) => (uploadId && upload.id === uploadId) || (recordId && upload.recordId === recordId));
}

function success(
  action: AgentCommandName,
  summary: string,
  extra: Omit<Extract<AppActionResult, { ok: true }>, "ok" | "action" | "summary"> = {}
): AppActionResult {
  return {
    ok: true,
    action,
    summary,
    ...extra
  };
}

function failure(
  action: AgentCommandName,
  errorCode: string,
  message: string,
  extra: Omit<Extract<AppActionResult, { ok: false }>, "ok" | "action" | "errorCode" | "message"> = {}
): AppActionResult {
  return {
    ok: false,
    action,
    errorCode,
    message,
    ...extra
  };
}

function confirmationFor(action: AgentCommandName, input: unknown) {
  const tool = getToolDefinition(action);
  const policy = getAgentToolPermissionPolicy(action);
  return {
    required: tool.requiresConfirmation,
    title: tool.title,
    summary: summarizeConfirmation(action, input),
    risk: confirmationRiskForGate(policy.gate) as AgentConfirmationRisk,
    permissionLevel: tool.permissionLevel as AgentPermissionLevel,
    auditEventType: tool.auditEventType,
    details: input && typeof input === "object" ? { input, permissionGate: policy.gate, requiresAudit: policy.requiresAudit } : undefined
  };
}

function summarizeConfirmation(action: AgentCommandName, input: unknown): string {
  if (action === "repair_upload_storage" && isRecord(input)) {
    return `Repair storage for upload ${String(input.uploadId ?? input.recordId ?? "")}.`;
  }
  if (action === "toggle_upload_shared" && isRecord(input)) {
    return `${input.shared ? "Allow sharing for" : "Make private"} upload ${String(input.uploadId ?? "")}.`;
  }
  return getToolDefinition(action).title;
}

function requiresConfirmation(action: AgentCommandName, input: unknown, options: AppActionOptions): AppActionResult | undefined {
  const confirmation = confirmationFor(action, input);
  if (!confirmation.required || options.confirmed) return undefined;
  return failure(action, "confirmation_required", confirmation.summary, { confirmation });
}

function requireSetter<T>(
  action: AgentCommandName,
  setter: ((value: T) => void) | undefined,
  label: string
): ((value: T) => void) | AppActionResult {
  if (setter) return setter;
  return failure(action, "missing_app_setter", `${label} is not writable in this app action runtime.`);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
