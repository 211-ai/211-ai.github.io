import type {
  DecryptedRecordView,
  DerivedArtifactView,
  DerivedAnalysisResultView,
  WalletAccessRequest,
  WalletGrantReceipt
} from "../../models/abby";
import {
  analyzeRecordFormRedactedWithGrant,
  analyzeRecordRedactedWithGrant,
  analyzeRecordWithGrant,
  approveAccessRequest as approveWalletAccessRequest,
  approveThresholdApproval,
  createRecordVectorProfileWithGrant,
  delegateGrant as delegateWalletGrant,
  decryptRecordWithGrant,
  extractRecordTextRedactedWithGrant,
  issueRecordDecryptInvocation,
  rejectAccessRequest as rejectWalletAccessRequest,
  revokeAccessRequest as revokeWalletAccessRequest
} from "../../services/walletApi";
import type { AppActionOptions, AppActionResult, AppActionRuntime } from "../../app/appActions";
import type {
  AccessRequestDecisionCommandInput,
  AnalyzeGrantedRecordCommandInput,
  DelegateGrantCommandInput,
  RecipientAnalysisMode,
  RecordControllerApprovalCommandInput,
  RevokeAccessRequestCommandInput,
  ViewGrantedRecordCommandInput
} from "../commandSchemas";
import type { AgentCommandName } from "../commandSchemas";
import type { AgentConfirmationRisk, AgentPermissionLevel } from "../types";
import { getToolDefinition } from "../surfaceRegistry";
import { confirmationRiskForGate, getAgentToolPermissionPolicy } from "../permissionPolicy";

type AccessDecisionAction = "approve_access_request" | "reject_access_request";

const grantDelegationAbilities = ["record/analyze", "record/decrypt"] as const;

const analysisOutputTypes: Record<RecipientAnalysisMode, string[]> = {
  summary: ["derived_only", "summary"],
  redacted: ["redacted_derived_only"],
  vector: ["vector_profile", "encrypted_vector_profile"],
  "extract-text": ["redacted_extracted_text"],
  form: ["redacted_form_analysis"]
};

export async function recordControllerApprovalAction(
  runtime: AppActionRuntime,
  input: RecordControllerApprovalCommandInput,
  options: AppActionOptions
): Promise<AppActionResult> {
  const blocked = requiresConfirmation("record_controller_approval", input, options);
  if (blocked) return blocked;
  const setAccessRequests = requireSetter("record_controller_approval", runtime.setAccessRequests, "Access requests");
  if (typeof setAccessRequests !== "function") return setAccessRequests;

  const state = runtime.getState();
  const request = state.accessRequests.find((item) => item.id === input.requestId);
  if (!request) {
    return failure(
      "record_controller_approval",
      "access_request_not_found",
      `Access request ${input.requestId} was not found.`
    );
  }
  if (request.status !== "pending") {
    return failure("record_controller_approval", "access_request_not_pending", "Only pending requests can receive approvals.");
  }
  if (!request.approvalRequired) {
    return failure("record_controller_approval", "approval_not_required", "This request does not require threshold approval.");
  }
  if (hasThresholdApproval(request)) {
    return failure("record_controller_approval", "approval_threshold_satisfied", "This request already has enough approvals.");
  }

  if (runtime.walletApiConfig?.actorDid && request.approvalId) {
    try {
      await approveThresholdApproval(runtime.walletApiConfig, request.approvalId);
      await runtime.refreshWalletAccessState?.();
      await runtime.refreshWalletAuditEvents?.();
      return success("record_controller_approval", `Recorded approval for ${request.requesterName}.`, {
        artifactId: input.requestId,
        confirmation: confirmationFor("record_controller_approval", input)
      });
    } catch {
      // Keep local demo state available if a configured API is unavailable.
    }
  }

  setAccessRequests(
    state.accessRequests.map((item) =>
      item.id === input.requestId
        ? {
            ...item,
            approvalCount: Math.min(
              (item.approvalCount ?? 0) + 1,
              item.approvalThreshold ?? (item.approvalCount ?? 0) + 1
            )
          }
        : item
    )
  );
  return success("record_controller_approval", `Recorded approval for ${request.requesterName}.`, {
    artifactId: input.requestId,
    confirmation: confirmationFor("record_controller_approval", input)
  });
}

export async function decideAccessRequestAction(
  runtime: AppActionRuntime,
  input: AccessRequestDecisionCommandInput,
  status: "approved" | "rejected",
  action: AccessDecisionAction,
  options: AppActionOptions
): Promise<AppActionResult> {
  const blocked = requiresConfirmation(action, input, options);
  if (blocked) return blocked;
  const setAccessRequests = requireSetter(action, runtime.setAccessRequests, "Access requests");
  if (typeof setAccessRequests !== "function") return setAccessRequests;
  const state = runtime.getState();
  const request = state.accessRequests.find((item) => item.id === input.requestId);
  if (!request) return failure(action, "access_request_not_found", `Access request ${input.requestId} was not found.`);
  if (request.status !== "pending") return failure(action, "access_request_not_pending", "Only pending requests can be decided.");
  if (status === "approved" && !hasThresholdApproval(request)) {
    return failure(action, "threshold_approval_required", "This request needs more controller approvals before approval.");
  }

  if (runtime.walletApiConfig?.actorDid) {
    try {
      if (status === "approved") {
        await approveWalletAccessRequest(runtime.walletApiConfig, input.requestId);
      } else {
        await rejectWalletAccessRequest(runtime.walletApiConfig, input.requestId, input.reason || "Rejected by app action");
      }
      await runtime.refreshWalletAccessState?.();
      await runtime.refreshWalletAuditEvents?.();
      return success(action, `${status === "approved" ? "Approved" : "Rejected"} ${request.requesterName}.`, {
        artifactId: input.requestId,
        confirmation: confirmationFor(action, input)
      });
    } catch {
      // Keep the local demo state path available if a configured API is unavailable.
    }
  }

  setAccessRequests(
    state.accessRequests.map((item) =>
      item.id === input.requestId
        ? { ...item, status, grantStatus: status === "approved" ? "active" : item.grantStatus }
        : item
    )
  );

  if (
    status === "approved" &&
    runtime.setGrantReceipts &&
    !state.grantReceipts.some((receipt) => receipt.id === `receipt-${request.id}`)
  ) {
    runtime.setGrantReceipts([
      ...state.grantReceipts,
      {
        id: `receipt-${request.id}`,
        grantId: `grant-${request.id}`,
        audienceName: request.requesterName,
        audienceDid: request.audienceDid,
        resources: [`wallet://demo-wallet/records/${request.resourceLabel}`],
        recordId: undefined,
        resourceLabel: request.resourceLabel,
        abilities: request.abilities,
        purpose: request.purpose,
        receiptHash: `local-${request.id}-receipt`,
        status: "active",
        createdAt: "Just now",
        expiresAt: "30 days"
      }
    ]);
  }

  return success(action, `${status === "approved" ? "Approved" : "Rejected"} ${request.requesterName}.`, {
    artifactId: input.requestId,
    confirmation: confirmationFor(action, input)
  });
}

export async function revokeAccessRequestAction(
  runtime: AppActionRuntime,
  input: RevokeAccessRequestCommandInput,
  options: AppActionOptions
): Promise<AppActionResult> {
  const blocked = requiresConfirmation("revoke_access_request", input, options);
  if (blocked) return blocked;
  const setAccessRequests = requireSetter("revoke_access_request", runtime.setAccessRequests, "Access requests");
  if (typeof setAccessRequests !== "function") return setAccessRequests;
  const setGrantReceipts = requireSetter("revoke_access_request", runtime.setGrantReceipts, "Grant receipts");
  if (typeof setGrantReceipts !== "function") return setGrantReceipts;

  const state = runtime.getState();
  const request = state.accessRequests.find((item) => item.id === input.requestId);
  if (!request) return failure("revoke_access_request", "access_request_not_found", `Access request ${input.requestId} was not found.`);
  if (request.status !== "approved" || request.grantStatus === "revoked") {
    return failure("revoke_access_request", "active_grant_required", "Only active approved access can be revoked.");
  }

  if (runtime.walletApiConfig?.actorDid) {
    try {
      await revokeWalletAccessRequest(runtime.walletApiConfig, input.requestId, input.reason || "Revoked by app action");
      await runtime.refreshWalletAccessState?.();
      await runtime.refreshWalletAuditEvents?.();
      return success("revoke_access_request", `Revoked ${request.requesterName}.`, {
        artifactId: input.requestId,
        confirmation: confirmationFor("revoke_access_request", input)
      });
    } catch {
      // Keep the local demo state path available if a configured API is unavailable.
    }
  }

  setAccessRequests(
    state.accessRequests.map((item) => (item.id === input.requestId ? { ...item, grantStatus: "revoked" } : item))
  );
  setGrantReceipts(
    state.grantReceipts.map((receipt) =>
      receipt.audienceDid === request.audienceDid &&
      receipt.resourceLabel === request.resourceLabel &&
      receipt.status === "active"
        ? { ...receipt, status: "revoked" }
        : receipt
    )
  );
  return success("revoke_access_request", `Revoked ${request.requesterName}.`, {
    artifactId: input.requestId,
    confirmation: confirmationFor("revoke_access_request", input)
  });
}

export async function analyzeGrantedRecordAction(
  runtime: AppActionRuntime,
  input: AnalyzeGrantedRecordCommandInput,
  options: AppActionOptions
): Promise<AppActionResult> {
  const blocked = requiresConfirmation("analyze_granted_record", input, options);
  if (blocked) return blocked;
  const state = runtime.getState();
  const receipt = findGrantReceipt(state.grantReceipts, input);
  if (!receipt) return failure("analyze_granted_record", "grant_not_found", "The selected grant receipt was not found.");
  const grantFailure = validateGrantUse("analyze_granted_record", receipt, "record/analyze", input.recordId, input, options);
  if (grantFailure) return grantFailure;

  const recordId = input.recordId?.trim() || receipt.recordId || "";
  const mode = input.mode ?? "summary";
  const requiredOutputTypes = analysisOutputTypes[mode];
  if (!receiptAllowsAnyOutput(receipt, requiredOutputTypes)) {
    return failure(
      "analyze_granted_record",
      "output_policy_denied",
      `This grant does not allow ${requiredOutputTypes.join(" or ")} output.`
    );
  }

  try {
    const { artifact, outputSummary } = await createAnalysisArtifact(runtime, receipt, recordId, mode, input);
    await runtime.refreshWalletAuditEvents?.().catch(() => undefined);
    return success("analyze_granted_record", `Created ${artifact.artifactType} for ${receipt.resourceLabel}.`, {
      artifactId: artifact.id,
      recordIds: [recordId],
      confirmation: confirmationFor("analyze_granted_record", input),
      metadata: {
        derivedArtifact: artifact,
        safeOutput: outputSummary,
        outputPolicy: artifact.outputPolicy
      }
    });
  } catch {
    return failure("analyze_granted_record", "analysis_failed", "Granted record analysis failed.", {
      retryable: true,
      confirmation: confirmationFor("analyze_granted_record", input)
    });
  }
}

export async function viewGrantedRecordAction(
  runtime: AppActionRuntime,
  input: ViewGrantedRecordCommandInput,
  options: AppActionOptions
): Promise<AppActionResult> {
  const blocked = requiresConfirmation("view_granted_record", input, options);
  if (blocked) return blocked;
  const state = runtime.getState();
  const receipt = findGrantReceipt(state.grantReceipts, input);
  if (!receipt) return failure("view_granted_record", "grant_not_found", "The selected grant receipt was not found.");
  const grantFailure = validateGrantUse("view_granted_record", receipt, "record/decrypt", input.recordId, input, options);
  if (grantFailure) return grantFailure;
  if (!receiptAllowsAnyOutput(receipt, ["plaintext", "record_plaintext", "decrypted_record"])) {
    return failure("view_granted_record", "output_policy_denied", "This grant does not allow plaintext output.");
  }

  const recordId = input.recordId?.trim() || receipt.recordId || "";
  try {
    const decrypted = await decryptGrantedRecord(runtime, receipt, recordId, input, options);
    await runtime.refreshWalletAuditEvents?.().catch(() => undefined);
    return success("view_granted_record", `Opened ${receipt.resourceLabel} (${decrypted.sizeBytes} bytes).`, {
      artifactId: recordId,
      recordIds: [recordId],
      confirmation: confirmationFor("view_granted_record", input),
      metadata: {
        decryptedRecord: decrypted
      }
    });
  } catch {
    return failure("view_granted_record", "decrypt_failed", "Granted record view failed.", {
      retryable: true,
      confirmation: confirmationFor("view_granted_record", input)
    });
  }
}

export async function delegateGrantAction(
  runtime: AppActionRuntime,
  input: DelegateGrantCommandInput,
  options: AppActionOptions
): Promise<AppActionResult> {
  const blocked = requiresConfirmation("delegate_grant", input, options);
  if (blocked) return blocked;
  const state = runtime.getState();
  const receipt = findGrantReceipt(state.grantReceipts, input);
  if (!receipt) return failure("delegate_grant", "grant_not_found", "The selected grant receipt was not found.");
  const activeFailure = validateActiveGrant("delegate_grant", receipt);
  if (activeFailure) return activeFailure;
  if (!grantThresholdSatisfied(receipt)) {
    return failure("delegate_grant", "threshold_approval_required", "This grant needs threshold approval before delegation.");
  }
  if (!runtime.walletApiConfig?.actorDid || runtime.walletApiConfig.actorDid !== receipt.audienceDid) {
    return failure("delegate_grant", "recipient_actor_required", "Only the active grant recipient can delegate this grant.");
  }
  if (!receiptHasAnyAbility(receipt, ["record/share", "document/share", "grant/create"])) {
    return failure("delegate_grant", "ability_not_allowed", "This grant does not allow delegation.");
  }

  const abilityOptions = delegationAbilityOptions(receipt);
  const ability = input.ability?.trim() || abilityOptions[0];
  if (!ability || !abilityOptions.includes(ability)) {
    return failure("delegate_grant", "delegated_ability_not_allowed", "The requested delegated ability is not allowed.");
  }

  const resources = input.resources?.length ? input.resources : receipt.resources;
  if (!resources.length || !resources.every((resource) => receipt.resources.includes(resource))) {
    return failure("delegate_grant", "resource_not_allowed", "Delegation resources must be covered by the parent grant.");
  }

  try {
    const delegated = await delegateWalletGrant(runtime.walletApiConfig, {
      parentGrantId: receipt.grantId,
      audienceDid: input.audienceDid.trim(),
      audienceKeyHex: input.audienceKeyHex?.trim() || undefined,
      abilities: [ability],
      expiresAt: input.expiresAt?.trim() || undefined,
      purpose: input.purpose?.trim() || receipt.purpose,
      resources
    });
    await runtime.refreshWalletAccessState?.().catch(() => undefined);
    await runtime.refreshWalletAuditEvents?.().catch(() => undefined);
    return success("delegate_grant", `Delegated ${ability} to ${input.audienceDid.trim()}.`, {
      artifactId: delegated.grant_id,
      recordIds: resources.map(recordIdFromResource).filter(Boolean),
      confirmation: confirmationFor("delegate_grant", input),
      metadata: {
        delegatedGrantId: delegated.grant_id,
        audienceDid: delegated.audience_did,
        abilities: delegated.abilities,
        resources: delegated.resources
      }
    });
  } catch {
    return failure("delegate_grant", "delegation_failed", "Grant delegation failed.", {
      retryable: true,
      confirmation: confirmationFor("delegate_grant", input)
    });
  }
}

function validateGrantUse(
  action: "analyze_granted_record" | "view_granted_record",
  receipt: WalletGrantReceipt | undefined,
  ability: "record/analyze" | "record/decrypt",
  inputRecordId: string | undefined,
  input: AnalyzeGrantedRecordCommandInput | ViewGrantedRecordCommandInput,
  options: AppActionOptions
): AppActionResult | undefined {
  if (!receipt) return failure(action, "grant_not_found", "The selected grant receipt was not found.");
  const activeFailure = validateActiveGrant(action, receipt);
  if (activeFailure) return activeFailure;
  if (!grantThresholdSatisfied(receipt)) {
    return failure(action, "threshold_approval_required", "This grant needs threshold approval before use.");
  }
  if (!receiptHasAbility(receipt, ability)) {
    return failure(action, "ability_not_allowed", `This grant does not allow ${ability}.`);
  }
  const recordId = inputRecordId?.trim() || receipt.recordId;
  if (!recordId) return failure(action, "record_not_found", "This grant does not identify a record.");
  if (!receiptCoversRecord(receipt, recordId)) {
    return failure(action, "record_not_allowed", "This grant does not cover the requested record.");
  }
  if (receiptRequiresUserPresence(receipt) && !(options.userPresent ?? input.userPresent ?? true)) {
    return failure(action, "user_presence_required", "This grant requires user presence.");
  }
  return undefined;
}

function validateActiveGrant(action: AgentCommandName, receipt: WalletGrantReceipt): AppActionResult | undefined {
  if (receipt.status !== "active") {
    return failure(action, "active_grant_required", "This action requires an active grant.");
  }
  return undefined;
}

async function createAnalysisArtifact(
  runtime: AppActionRuntime,
  receipt: WalletGrantReceipt,
  recordId: string,
  mode: RecipientAnalysisMode,
  input: AnalyzeGrantedRecordCommandInput
): Promise<{ artifact: DerivedArtifactView; outputSummary?: string }> {
  if (!runtime.walletApiConfig?.actorDid) {
    return createLocalAnalysisArtifact(receipt, recordId, mode);
  }

  if (mode === "redacted") {
    return fromDerivedAnalysisResult(
      await analyzeRecordRedactedWithGrant(runtime.walletApiConfig, {
        grantId: receipt.grantId,
        recordId,
        maxChars: input.maxChars ?? 500
      })
    );
  }
  if (mode === "vector") {
    return fromDerivedAnalysisResult(
      await createRecordVectorProfileWithGrant(runtime.walletApiConfig, {
        chunkSizeWords: input.chunkSizeWords ?? 80,
        grantId: receipt.grantId,
        recordId
      })
    );
  }
  if (mode === "extract-text") {
    return fromDerivedAnalysisResult(
      await extractRecordTextRedactedWithGrant(runtime.walletApiConfig, {
        grantId: receipt.grantId,
        maxBytes: input.maxBytes ?? 200_000,
        maxChars: input.maxChars ?? 20_000,
        recordId,
        useOcr: input.useOcr ?? true
      })
    );
  }
  if (mode === "form") {
    return fromDerivedAnalysisResult(
      await analyzeRecordFormRedactedWithGrant(runtime.walletApiConfig, {
        grantId: receipt.grantId,
        maxFields: input.maxFields ?? 100,
        recordId,
        useOcr: input.useOcr ?? false
      })
    );
  }

  return {
    artifact: await analyzeRecordWithGrant(runtime.walletApiConfig, {
      grantId: receipt.grantId,
      maxChars: input.maxChars ?? 200,
      recordId
    })
  };
}

function createLocalAnalysisArtifact(
  receipt: WalletGrantReceipt,
  recordId: string,
  mode: RecipientAnalysisMode
): { artifact: DerivedArtifactView; outputSummary?: string } {
  const artifactTypes: Record<RecipientAnalysisMode, string> = {
    summary: "summary",
    redacted: "redacted_document_analysis",
    vector: "redacted_document_vector_profile",
    "extract-text": "redacted_document_text_extraction",
    form: "redacted_document_form_analysis"
  };
  const outputPolicies: Record<RecipientAnalysisMode, string> = {
    summary: "derived_only",
    redacted: "redacted_derived_only",
    vector: "encrypted_vector_profile",
    "extract-text": "redacted_extracted_text",
    form: "redacted_form_analysis"
  };
  const outputSummaries: Partial<Record<RecipientAnalysisMode, string>> = {
    redacted: "Local demo redacted derived output.",
    vector: "redacted_lexical_hash_vector · local chunks",
    "extract-text": "Local demo redacted extracted text.",
    form: "Local demo redacted form fields."
  };
  return {
    artifact: {
      id: `artifact-${mode}-${receipt.id}`,
      artifactType: artifactTypes[mode],
      createdAt: "Just now",
      encryptedPayloadRef: "local encrypted derived artifact",
      outputPolicy: outputPolicies[mode],
      sourceRecordIds: [recordId]
    },
    outputSummary: outputSummaries[mode]
  };
}

async function decryptGrantedRecord(
  runtime: AppActionRuntime,
  receipt: WalletGrantReceipt,
  recordId: string,
  input: ViewGrantedRecordCommandInput,
  options: AppActionOptions
): Promise<DecryptedRecordView> {
  if (!runtime.walletApiConfig?.actorDid) {
    return {
      recordId,
      text: "Local demo decrypted document preview.",
      sizeBytes: "Local demo decrypted document preview.".length
    };
  }

  let invocationToken: string | undefined;
  if (runtime.walletApiConfig.audienceKeyHex || runtime.walletApiConfig.issuerKeyHex) {
    try {
      invocationToken = await issueRecordDecryptInvocation(runtime.walletApiConfig, {
        grantId: receipt.grantId,
        recordId,
        userPresent: options.userPresent ?? input.userPresent ?? true
      });
    } catch {
      invocationToken = undefined;
    }
  }

  return decryptRecordWithGrant(runtime.walletApiConfig, {
    grantId: invocationToken ? undefined : receipt.grantId,
    invocationToken,
    recordId
  });
}

function fromDerivedAnalysisResult(result: DerivedAnalysisResultView): { artifact: DerivedArtifactView; outputSummary?: string } {
  return {
    artifact: result.artifact,
    outputSummary: summarizeDerivedOutput(result.output)
  };
}

function summarizeDerivedOutput(output: Record<string, unknown>): string {
  if (typeof output.summary === "string" && output.summary.trim()) return output.summary;
  if (typeof output.text === "string" && output.text.trim()) return output.text;
  const profile = output.profile;
  if (profile && typeof profile === "object" && !Array.isArray(profile)) {
    const profileRecord = profile as Record<string, unknown>;
    const profileType = typeof profileRecord.profile_type === "string" ? profileRecord.profile_type : "vector profile";
    const chunkCount = typeof profileRecord.chunk_count === "number" ? profileRecord.chunk_count : undefined;
    return chunkCount === undefined ? profileType : `${profileType} · ${chunkCount} chunks`;
  }
  const fields = output.fields;
  if (Array.isArray(fields)) {
    const fieldLabels = fields
      .map((field) => {
        if (!field || typeof field !== "object" || Array.isArray(field)) return "";
        const fieldRecord = field as Record<string, unknown>;
        return String(fieldRecord.label ?? fieldRecord.name ?? "").trim();
      })
      .filter(Boolean)
      .slice(0, 3);
    return fieldLabels.length > 0
      ? `${fields.length} redacted fields: ${fieldLabels.join(", ")}`
      : `${fields.length} redacted fields`;
  }
  const form = output.form;
  if (form && typeof form === "object" && !Array.isArray(form)) {
    const formRecord = form as Record<string, unknown>;
    const fieldCount = typeof formRecord.field_count === "number" ? formRecord.field_count : undefined;
    if (fieldCount !== undefined) return `${fieldCount} redacted form fields`;
  }
  if (typeof output.output_policy === "string") return output.output_policy;
  return "Safe derived output created.";
}

function findGrantReceipt(
  receipts: WalletGrantReceipt[],
  input: { grantId?: string; receiptId?: string }
): WalletGrantReceipt | undefined {
  const grantId = input.grantId?.trim();
  const receiptId = input.receiptId?.trim();
  return receipts.find((receipt) => receipt.id === receiptId || receipt.grantId === grantId || receipt.id === grantId);
}

function hasThresholdApproval(request: WalletAccessRequest): boolean {
  if (!request.approvalRequired) return true;
  return (request.approvalCount ?? 0) >= (request.approvalThreshold ?? 1);
}

function grantThresholdSatisfied(receipt: WalletGrantReceipt): boolean {
  const caveats = receipt.caveats;
  if (!caveats) return true;
  const approvalRequired = caveats.approval_required === true || caveats.threshold_approval_required === true;
  if (!approvalRequired) return true;
  if (caveats.approval_status === "approved") return true;
  const approvalCount = typeof caveats.approval_count === "number" ? caveats.approval_count : 0;
  const approvalThreshold = typeof caveats.approval_threshold === "number" ? caveats.approval_threshold : 1;
  return approvalCount >= approvalThreshold;
}

function receiptHasAbility(receipt: WalletGrantReceipt, ability: string): boolean {
  return receipt.abilities.includes("*") || receipt.abilities.includes(ability);
}

function receiptHasAnyAbility(receipt: WalletGrantReceipt, abilities: string[]): boolean {
  return receipt.abilities.includes("*") || abilities.some((ability) => receipt.abilities.includes(ability));
}

function receiptOutputTypes(receipt: WalletGrantReceipt): string[] {
  const rawOutputTypes = receipt.caveats?.output_types ?? receipt.caveats?.allowed_output_types;
  if (!rawOutputTypes) return [];
  if (Array.isArray(rawOutputTypes)) return rawOutputTypes.map(String);
  return [String(rawOutputTypes)];
}

function receiptAllowsOutput(receipt: WalletGrantReceipt, outputType: string): boolean {
  const outputTypes = receiptOutputTypes(receipt);
  return outputTypes.length === 0 || outputTypes.includes(outputType);
}

function receiptAllowsAnyOutput(receipt: WalletGrantReceipt, outputTypes: string[]): boolean {
  return outputTypes.some((outputType) => receiptAllowsOutput(receipt, outputType));
}

function receiptRequiresUserPresence(receipt: WalletGrantReceipt): boolean {
  return receipt.caveats?.user_presence_required === true || receipt.caveats?.require_user_presence === true;
}

function receiptCoversRecord(receipt: WalletGrantReceipt, recordId: string): boolean {
  if (receipt.recordId === recordId) return true;
  return receipt.resources.some((resource) => recordIdFromResource(resource) === recordId || resource.endsWith(`/${recordId}`));
}

function recordIdFromResource(resource: string): string {
  return resource.split("/").filter(Boolean).pop() ?? "";
}

function delegationAbilityOptions(receipt: WalletGrantReceipt): string[] {
  const abilities = receipt.abilities.includes("*") ? [...grantDelegationAbilities] : receipt.abilities;
  return grantDelegationAbilities.filter((ability) => abilities.includes(ability));
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
  if (isRecord(input)) {
    if (action === "record_controller_approval") return `Record controller approval for request ${String(input.requestId ?? "")}.`;
    if (action === "approve_access_request") return `Approve access request ${String(input.requestId ?? "")}.`;
    if (action === "reject_access_request") return `Reject access request ${String(input.requestId ?? "")}.`;
    if (action === "revoke_access_request") return `Revoke access request ${String(input.requestId ?? "")}.`;
    if (action === "analyze_granted_record") return `Analyze granted record for grant ${String(input.grantId ?? input.receiptId ?? "")}.`;
    if (action === "view_granted_record") return `View granted record for grant ${String(input.grantId ?? input.receiptId ?? "")}.`;
    if (action === "delegate_grant") return `Delegate grant ${String(input.grantId ?? input.receiptId ?? "")} to ${String(input.audienceDid ?? "")}.`;
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
