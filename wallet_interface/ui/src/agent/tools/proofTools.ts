import type { ProofReceiptView } from "../../models/abby";
import { createLocationRegionProof, listWalletProofReceipts } from "../../services/walletApi";
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
  CreateLocationRegionProofCommandInput,
  CreateProofCommandInput,
  ProofReceiptReferenceCommandInput
} from "../commandSchemas";
import type { AgentConfirmationRisk, AgentPermissionLevel } from "../types";
import { confirmationRiskForGate, getAgentToolPermissionPolicy } from "../permissionPolicy";
import { getToolDefinition } from "../surfaceRegistry";

const defaultLocationProofClaim = "Location is in service region";
const defaultLocationWitnessLabel = "Current location";

export async function createProofAction(
  runtime: AppActionRuntime,
  input: CreateProofCommandInput,
  options: AppActionOptions
): Promise<AppActionResult> {
  const blocked = requiresConfirmation("create_proof", input, options);
  if (blocked) return blocked;
  const setProofs = requireSetter("create_proof", runtime.setWalletProofReceipts, "Proof receipts");
  if (typeof setProofs !== "function") return setProofs;

  const state = runtime.getState();
  const proofType = clean(input.proofType) || "location_region";
  const requested = normalizeCreateProofInput(input, proofType);

  try {
    const proof =
      runtime.walletApiConfig?.actorDid && proofType === "location_region"
        ? await createLocationRegionProof(runtime.walletApiConfig, {
            grantId: clean(input.grantId) || undefined,
            locationRecordId: clean(input.recordId) || "rec-location-current",
            regionId: clean(input.regionLabel) || clean(input.publicInputs?.region_id) || "selected_region"
          }).then((receipt) => decorateReceipt(receipt, requested))
        : createStagedProofReceipt(requested);

    setProofs([proof, ...state.walletProofReceipts.filter((item) => item.id !== proof.id)]);
    await runtime.refreshWalletAuditEvents?.().catch(() => undefined);
    return success(
      "create_proof",
      proof.proofSystem === "staged"
        ? `Staged proof creation for "${requested.claim}".`
        : `Created proof receipt for "${requested.claim}".`,
      {
        artifactId: proof.id,
        confirmation: confirmationFor("create_proof", input),
        metadata: {
          proof,
          auditBehavior: "Proof creation requires confirmation and emits an agent proof audit event."
        }
      }
    );
  } catch {
    return failure("create_proof", "proof_creation_failed", "Proof creation failed.", {
      retryable: true,
      confirmation: confirmationFor("create_proof", input)
    });
  }
}

export async function createLocationRegionProofAction(
  runtime: AppActionRuntime,
  input: CreateLocationRegionProofCommandInput,
  options: AppActionOptions
): Promise<AppActionResult> {
  const blocked = requiresConfirmation("create_location_region_proof", input, options);
  if (blocked) return blocked;
  return createProofAction(
    runtime,
    {
      claim: clean(input.claim) || defaultLocationProofClaim,
      verifier: input.verifier,
      witnessLabel: clean(input.witnessLabel) || defaultLocationWitnessLabel,
      proofType: "location_region",
      regionLabel: input.regionLabel,
      recordId: input.recordId,
      grantId: input.grantId,
      publicInputs: {
        claim: "location_in_region",
        region_id: input.regionLabel
      }
    },
    { ...options, confirmed: true }
  ).then((result) => remapAction(result, "create_location_region_proof", input));
}

export async function explainProofReceiptAction(
  runtime: AppActionRuntime,
  input: ProofReceiptReferenceCommandInput
): Promise<AppActionResult> {
  const proof = findProofReceipt(runtime.getState().walletProofReceipts, input);
  if (!proof) {
    return failure("explain_proof_receipt", "proof_receipt_not_found", "The selected proof receipt was not found.");
  }

  return success("explain_proof_receipt", buildProofReceiptExplanation(proof), {
    artifactId: proof.id,
    metadata: {
      proofId: proof.id,
      publicInputs: proof.publicInputs,
      rawWitnessExposed: false
    }
  });
}

export async function verifyProofStatusAction(
  runtime: AppActionRuntime,
  input: ProofReceiptReferenceCommandInput
): Promise<AppActionResult> {
  let proofs = runtime.getState().walletProofReceipts;
  if (runtime.walletApiConfig && runtime.setWalletProofReceipts) {
    try {
      proofs = await listWalletProofReceipts(runtime.walletApiConfig);
      runtime.setWalletProofReceipts(proofs);
    } catch {
      proofs = runtime.getState().walletProofReceipts;
    }
  }

  const proof = findProofReceipt(proofs, input);
  if (!proof) {
    return failure("verify_proof_status", "proof_receipt_not_found", "The selected proof receipt was not found.");
  }

  return success("verify_proof_status", buildProofStatusSummary(proof), {
    artifactId: proof.id,
    metadata: {
      proofId: proof.id,
      verificationStatus: proof.verificationStatus,
      simulated: proof.simulated,
      proofSystem: proof.proofSystem
    }
  });
}

export function findProofReceipt(
  proofs: ProofReceiptView[],
  input: ProofReceiptReferenceCommandInput
): ProofReceiptView | undefined {
  const proofId = clean(input.proofId);
  const receiptId = clean(input.receiptId);
  return proofs.find((proof) => proof.id === proofId || proof.id === receiptId);
}

export function buildProofReceiptExplanation(proof: ProofReceiptView): string {
  const publicInputNames = Object.keys(proof.publicInputs);
  const inputSummary = publicInputNames.length ? publicInputNames.join(", ") : "no public inputs";
  const simulated = proof.simulated ? " It is marked simulated, so treat it as a development proof." : "";
  return `${proof.claim} is a ${proof.proofType} receipt for verifier ${proof.verifier}. It uses ${proof.proofSystem}, status ${proof.verificationStatus}, witness label "${proof.witnessLabel}", and exposes ${inputSummary}; it does not expose the raw witness record.${simulated}`;
}

export function buildProofStatusSummary(proof: ProofReceiptView): string {
  const qualifier = proof.simulated ? "simulated " : "";
  return `Proof ${proof.id} is ${qualifier}${proof.verificationStatus} for "${proof.claim}" by ${proof.verifier}.`;
}

function normalizeCreateProofInput(input: CreateProofCommandInput, proofType: string): ProofReceiptView {
  return {
    id: "",
    proofType,
    claim: input.claim.trim(),
    verifier: input.verifier.trim(),
    proofSystem: "staged",
    verificationStatus: "staged",
    publicInputs: sanitizePublicInputs(input.publicInputs, input),
    witnessLabel: input.witnessLabel.trim(),
    simulated: true,
    createdAt: "Just now"
  };
}

function createStagedProofReceipt(requested: ProofReceiptView): ProofReceiptView {
  return {
    ...requested,
    id: `proof-staged-${Date.now()}`,
    circuitId: `staged-${requested.proofType}`,
    proofArtifactRef: "agent-staged-proof-request"
  };
}

function decorateReceipt(receipt: ProofReceiptView, requested: ProofReceiptView): ProofReceiptView {
  return {
    ...receipt,
    claim: requested.claim,
    verifier: requested.verifier,
    witnessLabel: requested.witnessLabel,
    publicInputs: {
      ...receipt.publicInputs,
      ...requested.publicInputs
    }
  };
}

function sanitizePublicInputs(
  publicInputs: Record<string, string> | undefined,
  input: CreateProofCommandInput
): Record<string, string> {
  const entries = Object.entries(publicInputs ?? {})
    .map(([key, value]) => [key.trim(), value.trim()] as const)
    .filter(([key, value]) => key.length > 0 && value.length > 0);
  const sanitized = Object.fromEntries(entries);
  sanitized.claim = sanitized.claim || input.claim.trim();
  const regionLabel = clean(input.regionLabel);
  if (regionLabel) sanitized.region_id = sanitized.region_id || regionLabel;
  return sanitized;
}

function remapAction(
  result: AppActionResult,
  action: "create_location_region_proof",
  input: CreateLocationRegionProofCommandInput
): AppActionResult {
  const confirmation = confirmationFor(action, input);
  if (!result.ok) {
    return {
      ...result,
      action,
      confirmation: result.confirmation ? confirmation : undefined
    };
  }
  return {
    ...result,
    action,
    summary:
      result.summary.startsWith("Staged proof creation") || result.summary.startsWith("Created proof receipt")
        ? result.summary.replace(/"([^"]+)"/, input.regionLabel)
        : result.summary,
    confirmation
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
    if (action === "create_proof") {
      return `Stage proof "${String(input.claim ?? "")}" for verifier ${String(input.verifier ?? "")} using witness label ${String(
        input.witnessLabel ?? ""
      )}.`;
    }
    if (action === "create_location_region_proof") {
      return `Create a location-region proof for ${String(input.regionLabel ?? "the selected region")}.`;
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

function clean(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}
