import { auditEvents } from "../../services/mockAbbyService";
import {
  listWalletAuditEvents,
  loadWalletSnapshot,
  saveWalletSnapshot,
  verifyWalletSnapshot
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
  RefreshWalletAuditCommandInput,
  RestoreWalletSnapshotCommandInput,
  SaveWalletSnapshotCommandInput
} from "../commandSchemas";
import type { AgentConfirmationRisk, AgentPermissionLevel } from "../types";
import { confirmationRiskForGate, getAgentToolPermissionPolicy } from "../permissionPolicy";
import { getToolDefinition } from "../surfaceRegistry";

export async function saveWalletSnapshotAction(
  runtime: AppActionRuntime,
  input: SaveWalletSnapshotCommandInput,
  options: AppActionOptions
): Promise<AppActionResult> {
  const blocked = requiresConfirmation("save_wallet_snapshot", input, options);
  if (blocked) return blocked;

  try {
    const report = runtime.walletApiConfig
      ? await saveLiveWalletSnapshot(runtime)
      : createStagedSnapshotReport("save", runtime.getState().activeRoute);
    await runtime.refreshWalletAuditEvents?.().catch(() => undefined);
    return success("save_wallet_snapshot", `Saved wallet snapshot for ${report.walletId}.`, {
      artifactId: report.snapshotHash || report.walletId,
      confirmation: confirmationFor("save_wallet_snapshot", input),
      metadata: {
        snapshot: report,
        rawWalletDataExposed: false,
        stagedOnly: !runtime.walletApiConfig
      }
    });
  } catch {
    return failure("save_wallet_snapshot", "snapshot_save_failed", "Wallet snapshot save failed.", {
      retryable: true,
      confirmation: confirmationFor("save_wallet_snapshot", input)
    });
  }
}

export async function restoreWalletSnapshotAction(
  runtime: AppActionRuntime,
  input: RestoreWalletSnapshotCommandInput,
  options: AppActionOptions
): Promise<AppActionResult> {
  const blocked = requiresConfirmation("restore_wallet_snapshot", input, options);
  if (blocked) return blocked;

  try {
    const report = runtime.walletApiConfig
      ? await restoreLiveWalletSnapshot(runtime)
      : createStagedSnapshotReport("restore", input.walletId || runtime.getState().activeRoute);
    await runtime.refreshWalletAccessState?.().catch(() => undefined);
    await runtime.refreshWalletAuditEvents?.().catch(() => undefined);
    return success("restore_wallet_snapshot", `Restored wallet snapshot for ${report.walletId}.`, {
      artifactId: report.snapshotHash || report.walletId,
      confirmation: confirmationFor("restore_wallet_snapshot", input),
      metadata: {
        snapshot: report,
        rawWalletDataExposed: false,
        stagedOnly: !runtime.walletApiConfig
      }
    });
  } catch {
    return failure("restore_wallet_snapshot", "snapshot_restore_failed", "Wallet snapshot restore failed.", {
      retryable: true,
      confirmation: confirmationFor("restore_wallet_snapshot", input)
    });
  }
}

export async function refreshWalletAuditAction(
  runtime: AppActionRuntime,
  input: RefreshWalletAuditCommandInput
): Promise<AppActionResult> {
  const setWalletAuditEvents = requireSetter("refresh_wallet_audit", runtime.setWalletAuditEvents, "Wallet audit");
  if (typeof setWalletAuditEvents !== "function") return setWalletAuditEvents;
  if (!runtime.walletApiConfig) {
    const limitedEvents = auditEvents.slice(0, input.limit ?? auditEvents.length);
    setWalletAuditEvents(limitedEvents);
    return success("refresh_wallet_audit", `Loaded ${limitedEvents.length} local audit events.`);
  }
  const events = await listWalletAuditEvents(runtime.walletApiConfig);
  const limitedEvents = events.slice(0, input.limit ?? events.length);
  setWalletAuditEvents(limitedEvents.length ? limitedEvents : auditEvents);
  return success("refresh_wallet_audit", `Loaded ${limitedEvents.length || auditEvents.length} audit events.`);
}

async function saveLiveWalletSnapshot(runtime: AppActionRuntime) {
  if (!runtime.walletApiConfig) throw new Error("Wallet API required");
  const mutation = await saveWalletSnapshot(runtime.walletApiConfig);
  const verification = await verifyWalletSnapshot(runtime.walletApiConfig).catch(() => undefined);
  return {
    walletId: mutation.wallet_id || runtime.walletApiConfig.walletId,
    exists: verification?.exists ?? true,
    valid: verification?.valid ?? true,
    format: verification?.format,
    snapshotHash: verification?.computed_hash || verification?.snapshot_hash,
    loaded: mutation.loaded === true
  };
}

async function restoreLiveWalletSnapshot(runtime: AppActionRuntime) {
  if (!runtime.walletApiConfig) throw new Error("Wallet API required");
  const mutation = await loadWalletSnapshot(runtime.walletApiConfig);
  const verification = await verifyWalletSnapshot(runtime.walletApiConfig).catch(() => undefined);
  return {
    walletId: mutation.wallet_id || runtime.walletApiConfig.walletId,
    exists: verification?.exists ?? true,
    valid: verification?.valid ?? true,
    format: verification?.format,
    snapshotHash: verification?.computed_hash || verification?.snapshot_hash,
    loaded: mutation.loaded === true
  };
}

function createStagedSnapshotReport(action: "save" | "restore", walletId: string) {
  const id = walletId.trim() || "wallet";
  return {
    walletId: id,
    exists: action === "restore",
    valid: false,
    snapshotHash: `staged-${action}-${Date.now()}`,
    loaded: action === "restore"
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
  if (action === "save_wallet_snapshot") return "Save an encrypted wallet snapshot.";
  if (action === "restore_wallet_snapshot" && isRecord(input)) {
    return `Restore wallet snapshot${input.walletId ? ` for ${String(input.walletId)}` : ""}.`;
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

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}
