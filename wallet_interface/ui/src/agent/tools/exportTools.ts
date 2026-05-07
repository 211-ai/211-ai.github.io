import type { ExportBundleView } from "../../models/abby";
import {
  createVerifiedExportBundleView,
  importExportBundleView,
  loadExportBundleView,
  type ExportBundleApi
} from "../../services/walletApi";
import type {
  AppActionConfirmationMetadata,
  AppActionFailure,
  AppActionOptions,
  AppActionResult,
  AppActionRuntime,
  AppActionSuccess
} from "../../app/appActions";
import type {
  AgentCommandName,
  CreateVerifiedExportBundleCommandInput,
  ImportExportBundleCommandInput
} from "../commandSchemas";
import type { AgentConfirmationRisk, AgentPermissionLevel } from "../types";
import { confirmationRiskForGate, getAgentToolPermissionPolicy } from "../permissionPolicy";
import { getToolDefinition } from "../surfaceRegistry";

export async function createVerifiedExportBundleAction(
  runtime: AppActionRuntime,
  input: CreateVerifiedExportBundleCommandInput,
  options: AppActionOptions
): Promise<AppActionResult> {
  const blocked = requiresConfirmation("create_verified_export_bundle", input, options);
  if (blocked) return blocked;
  const setBundles = requireSetter("create_verified_export_bundle", runtime.setExportBundleViews, "Export bundles");
  if (typeof setBundles !== "function") return setBundles;

  const state = runtime.getState();
  try {
    const bundle =
      runtime.walletApiConfig && !input.stageOnly
        ? await createLiveExportBundle(runtime, input)
        : createStagedExportBundle(runtime, input);

    setBundles([bundle, ...state.exportBundleViews.filter((item) => item.bundleId !== bundle.bundleId)]);
    await runtime.refreshWalletAuditEvents?.().catch(() => undefined);
    return success(
      "create_verified_export_bundle",
      `${bundle.verificationOk ? "Created" : "Staged"} export bundle for ${bundle.audienceName} with ${bundle.recordCount} record${plural(
        bundle.recordCount
      )} and ${bundle.proofCount} proof${plural(bundle.proofCount)}.`,
      {
        artifactId: bundle.bundleId,
        recordIds: [...input.recordIds],
        confirmation: confirmationFor("create_verified_export_bundle", input),
        metadata: {
          exportBundle: summarizeBundle(bundle),
          rawRecordsExposed: false,
          rawProofsExposed: false,
          stagedOnly: input.stageOnly === true || !runtime.walletApiConfig
        }
      }
    );
  } catch {
    return failure("create_verified_export_bundle", "export_creation_failed", "Export bundle creation failed.", {
      retryable: true,
      confirmation: confirmationFor("create_verified_export_bundle", input)
    });
  }
}

export async function importExportBundleAction(
  runtime: AppActionRuntime,
  input: ImportExportBundleCommandInput,
  options: AppActionOptions
): Promise<AppActionResult> {
  const blocked = requiresConfirmation("import_export_bundle", input, options);
  if (blocked) return blocked;
  const setBundles = requireSetter("import_export_bundle", runtime.setExportBundleViews, "Export bundles");
  if (typeof setBundles !== "function") return setBundles;

  const state = runtime.getState();
  const existing = input.bundleId ? findBundle(state.exportBundleViews, input.bundleId) : undefined;
  if (input.bundleId && !existing && !input.bundle) {
    return failure("import_export_bundle", "export_bundle_not_found", `Export bundle ${input.bundleId} was not found.`);
  }

  try {
    const imported =
      runtime.walletApiConfig && !input.stageOnly
        ? await importLiveExportBundle(runtime, input, existing)
        : importStagedExportBundle(input, existing);

    setBundles(upsertBundle(state.exportBundleViews, imported));
    await runtime.refreshWalletAuditEvents?.().catch(() => undefined);
    return success("import_export_bundle", `Imported export bundle ${imported.bundleId}.`, {
      artifactId: imported.bundleId,
      confirmation: confirmationFor("import_export_bundle", input),
      metadata: {
        exportBundle: summarizeBundle(imported),
        rawBundleExposed: false,
        stagedOnly: input.stageOnly === true || !runtime.walletApiConfig
      }
    });
  } catch {
    return failure("import_export_bundle", "export_import_failed", "Export bundle import failed.", {
      retryable: true,
      confirmation: confirmationFor("import_export_bundle", input)
    });
  }
}

async function createLiveExportBundle(
  runtime: AppActionRuntime,
  input: CreateVerifiedExportBundleCommandInput
): Promise<ExportBundleView> {
  if (!runtime.walletApiConfig) throw new Error("Wallet API required");
  const audienceDid = clean(input.audienceDid) || clean(input.audienceName);
  if (!audienceDid.startsWith("did:")) {
    throw new Error("Recipient DID required for live export bundle creation");
  }
  return createVerifiedExportBundleView(runtime.walletApiConfig, {
    audienceDid,
    audienceName: clean(input.audienceName) || undefined,
    purpose: clean(input.purpose) || "user_export",
    recordIds: uniqueStrings(input.recordIds)
  });
}

async function importLiveExportBundle(
  runtime: AppActionRuntime,
  input: ImportExportBundleCommandInput,
  existing: ExportBundleView | undefined
): Promise<ExportBundleView> {
  if (!runtime.walletApiConfig) throw new Error("Wallet API required");
  if (existing) {
    return importExportBundleView({
      apiBaseUrl: runtime.walletApiConfig.apiBaseUrl,
      bundleView: existing
    });
  }
  if (!input.bundle) throw new Error("Export bundle required");
  const bundleView = await loadExportBundleView({
    apiBaseUrl: runtime.walletApiConfig.apiBaseUrl,
    audienceName: input.audienceName,
    bundle: input.bundle as ExportBundleApi,
    imported: false
  });
  return importExportBundleView({
    apiBaseUrl: runtime.walletApiConfig.apiBaseUrl,
    bundleView
  });
}

function createStagedExportBundle(
  runtime: AppActionRuntime,
  input: CreateVerifiedExportBundleCommandInput
): ExportBundleView {
  const recordIds = uniqueStrings(input.recordIds);
  const proofIds = uniqueStrings(input.proofIds ?? []);
  const now = new Date();
  const bundleId = `export-staged-${now.getTime()}`;
  const bundleHash = localHash([bundleId, input.audienceName, ...recordIds, ...proofIds].join("|"));
  return {
    id: bundleId,
    bundleId,
    bundleHash,
    audienceName: clean(input.audienceName) || clean(input.audienceDid) || "Selected audience",
    bundle: {
      bundle_id: bundleId,
      bundle_hash: bundleHash,
      created_at: now.toISOString(),
      wallet: { wallet_id: runtime.walletApiConfig?.walletId ?? "local-wallet" },
      records: recordIds.map((recordId) => ({ record_id: recordId, encrypted_descriptor: true })),
      proofs: proofIds.map((proofId) => ({ proof_id: proofId }))
    },
    recordCount: recordIds.length,
    proofCount: proofIds.length,
    verificationOk: false,
    hashOk: true,
    schemaOk: true,
    storageOk: false,
    imported: false,
    createdAt: "Just now"
  };
}

function importStagedExportBundle(
  input: ImportExportBundleCommandInput,
  existing: ExportBundleView | undefined
): ExportBundleView {
  if (existing) return { ...existing, imported: true };
  const bundle = input.bundle;
  const bundleId = clean(bundle?.bundle_id) || clean(input.bundleId) || `export-import-staged-${Date.now()}`;
  const bundleHash = clean(bundle?.bundle_hash) || localHash(bundleId);
  return {
    id: bundleId,
    bundleId,
    bundleHash,
    audienceName: clean(input.audienceName) || "Imported bundle",
    bundle: bundle ? { ...bundle } : undefined,
    recordCount: Array.isArray(bundle?.records) ? bundle.records.length : 0,
    proofCount: Array.isArray(bundle?.proofs) ? bundle.proofs.length : 0,
    verificationOk: false,
    hashOk: Boolean(bundleHash),
    schemaOk: true,
    storageOk: false,
    imported: true,
    createdAt: "Just now"
  };
}

function upsertBundle(bundles: ExportBundleView[], imported: ExportBundleView): ExportBundleView[] {
  return bundles.some((bundle) => bundle.bundleId === imported.bundleId)
    ? bundles.map((bundle) => (bundle.bundleId === imported.bundleId ? imported : bundle))
    : [imported, ...bundles];
}

function findBundle(bundles: ExportBundleView[], bundleId: string): ExportBundleView | undefined {
  const normalized = bundleId.trim();
  return bundles.find((bundle) => bundle.bundleId === normalized || bundle.id === normalized);
}

function summarizeBundle(bundle: ExportBundleView): Record<string, unknown> {
  return {
    bundleId: bundle.bundleId,
    bundleHash: shortHash(bundle.bundleHash),
    audienceName: bundle.audienceName,
    recordCount: bundle.recordCount,
    proofCount: bundle.proofCount,
    verificationOk: bundle.verificationOk,
    hashOk: bundle.hashOk,
    schemaOk: bundle.schemaOk,
    storageOk: bundle.storageOk,
    imported: bundle.imported
  };
}

function success(
  action: AgentCommandName,
  summary: string,
  extra: Omit<AppActionSuccess, "ok" | "action" | "summary"> = {}
): AppActionSuccess {
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
  extra: Omit<AppActionFailure, "ok" | "action" | "errorCode" | "message"> = {}
): AppActionFailure {
  return {
    ok: false,
    action,
    errorCode,
    message,
    ...extra
  };
}

function requiresConfirmation(
  action: AgentCommandName,
  input: unknown,
  options: AppActionOptions
): AppActionFailure | undefined {
  const confirmation = confirmationFor(action, input);
  if (!confirmation.required || options.confirmed) return undefined;
  return failure(action, "confirmation_required", confirmation.summary, { confirmation });
}

function confirmationFor(action: AgentCommandName, input: unknown): AppActionConfirmationMetadata {
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
  if (isRecord(input)) {
    if (action === "create_verified_export_bundle") {
      return `Create an export bundle for ${String(input.audienceName ?? "the selected recipient")}.`;
    }
    if (action === "import_export_bundle") {
      return `Import export bundle ${String(input.bundleId ?? "from provided bundle data")}.`;
    }
  }
  return getToolDefinition(action).title;
}

function requireSetter<T>(
  action: AgentCommandName,
  setter: ((value: T) => void) | undefined,
  label: string
): ((value: T) => void) | AppActionFailure {
  if (setter) return setter;
  return failure(action, "missing_app_setter", `${label} is not writable in this app action runtime.`);
}

function uniqueStrings(values: string[]): string[] {
  return Array.from(new Set(values.map((value) => value.trim()).filter(Boolean)));
}

function shortHash(value: string): string {
  return value.length > 24 ? `${value.slice(0, 12)}...${value.slice(-8)}` : value;
}

function localHash(value: string): string {
  let hash = 2166136261;
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return `local-${(hash >>> 0).toString(16).padStart(8, "0")}`;
}

function plural(count: number): string {
  return count === 1 ? "" : "s";
}

function clean(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}
