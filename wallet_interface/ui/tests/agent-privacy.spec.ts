import { expect, test } from "@playwright/test";

import { buildAgentConversationPrompt } from "../src/agent/agentConversation";
import { createAgentToolExecutor } from "../src/agent/toolExecutor";
import type { AgentSession, AgentToolCall, EvidenceBundle, SurfaceContext } from "../src/agent/types";
import { createAgentSurfaceApi } from "../src/agent/surfaceApi";
import type { AppActionRuntime, AppActionState } from "../src/app/appActions";
import { createDefaultAppState } from "../src/app/appState";
import type { RouteId, WalletGrantReceipt } from "../src/models/abby";
import { auditEvents, initialAccessRequests, initialGrantReceipts, proofReceipts } from "../src/services/mockAbbyService";

const NOW = "2026-05-05T12:00:00.000Z";
const PRIVATE_NOTE = "case note says avoid the east entrance";
const PRECISE_LOCATION = "45.520123, -122.680456";
const DOCUMENT_TEXT = "benefits notice says household income is 417 dollars";
const RAW_QUERY = "prior raw query asked for motel vouchers near Delta Park";

function createSurfaceContext(overrides: Partial<SurfaceContext> = {}): SurfaceContext {
  return {
    route: "register",
    routeLabel: "Register",
    capturedAt: NOW,
    walletUnlocked: true,
    privateContextAllowed: true,
    permissionLevel: "wallet_write",
    summary: `Private notes: ${PRIVATE_NOTE}. Location: ${PRECISE_LOCATION}. Document: ${DOCUMENT_TEXT}.`,
    selectedRecordId: "rec-benefits-letter",
    visibleRecordIds: ["rec-benefits-letter"],
    metadata: {
      privateNotes: `notes: ${PRIVATE_NOTE}`,
      preciseLocation: PRECISE_LOCATION,
      uploadedDocumentText: `document: ${DOCUMENT_TEXT}`,
      visibleCount: 1,
    },
    ...overrides,
  };
}

function createSession(evidenceBundles: EvidenceBundle[] = []): AgentSession {
  return {
    id: "agent-session-privacy",
    title: "Privacy test",
    status: "active",
    createdAt: NOW,
    updatedAt: NOW,
    activeRoute: "register",
    permissionLevel: "wallet_write",
    privateContextAllowed: true,
    messages: [
      {
        id: "message-user-raw-query",
        sessionId: "agent-session-privacy",
        role: "user",
        content: RAW_QUERY,
        createdAt: NOW,
        status: "complete",
      },
      {
        id: "message-tool-document",
        sessionId: "agent-session-privacy",
        role: "tool",
        content: `tool output included document: ${DOCUMENT_TEXT}`,
        createdAt: NOW,
        status: "complete",
      },
    ],
    intents: [],
    plans: [],
    toolCalls: [],
    toolResults: [],
    confirmations: [],
    evidenceBundles,
  };
}

function createEvidenceBundle(): EvidenceBundle {
  return {
    id: "evidence-private-query",
    query: RAW_QUERY,
    generatedAt: NOW,
    items: [
      {
        id: "svc-public-1",
        title: "Public service",
        source: "211 corpus",
        snippet: "Public service facts only.",
        citation: { label: "Public service", docId: "svc-public-1" },
      },
    ],
  };
}

function createToolCall(name: AgentToolCall["name"], input: unknown): AgentToolCall {
  return {
    id: `tool-${name}`,
    sessionId: "agent-session-privacy",
    name,
    input,
    status: "pending",
    requestedAt: NOW,
  };
}

function createGrantReceipt(overrides: Partial<WalletGrantReceipt>): WalletGrantReceipt {
  return {
    id: "receipt-active-decrypt",
    grantId: "grant-active-decrypt",
    audienceName: "Shelter intake desk",
    audienceDid: "did:key:shelter-intake",
    resources: ["wallet://demo-wallet/records/rec-benefits-letter"],
    recordId: "rec-benefits-letter",
    resourceLabel: "Benefits letter",
    abilities: ["record/decrypt"],
    purpose: "Verify intake document",
    caveats: { output_types: ["plaintext"] },
    receiptHash: "hash-active-decrypt",
    status: "active",
    createdAt: NOW,
    expiresAt: "2026-06-05T12:00:00.000Z",
    ...overrides,
  };
}

function createHarness(activeRoute: RouteId, grantReceipts: WalletGrantReceipt[]) {
  const defaults = createDefaultAppState();
  let state: AppActionState = {
    activeRoute,
    profile: { ...defaults.profile },
    policy: { ...defaults.policy },
    recipients: [...defaults.recipients],
    uploads: [...defaults.uploads],
    accessRequests: [...initialAccessRequests],
    grantReceipts,
    walletAuditEvents: [...auditEvents],
    walletProofReceipts: [...proofReceipts],
    exportBundleViews: [],
    walletUnlocked: true,
    privateContextAllowed: true,
    permissionLevel: "share_or_disclose",
  };

  const runtime: AppActionRuntime = {
    getState: () => state,
    setActiveRoute: (route) => {
      state = { ...state, activeRoute: route };
    },
    setAccessRequests: (accessRequests) => {
      state = { ...state, accessRequests };
    },
    setGrantReceipts: (nextGrantReceipts) => {
      state = { ...state, grantReceipts: nextGrantReceipts };
    },
  };

  return {
    runtime,
    surfaceApi: createAgentSurfaceApi(runtime),
    getState: () => state,
  };
}

function textOf(value: unknown): string {
  return JSON.stringify(value);
}

test.describe("agent privacy controls", () => {
  test("redacts private notes, precise location, document text, and raw query history from prompts by default", () => {
    const evidence = createEvidenceBundle();
    const prompt = buildAgentConversationPrompt({
      session: createSession([evidence]),
      surfaceContext: createSurfaceContext(),
      userGoal: "Help me understand what Abby can do here.",
      evidenceBundles: [evidence],
      options: {
        includePrivateContext: false,
      },
    });

    expect(prompt.safeContext.privateContextAllowed).toBe(false);
    expect(prompt.safeContext.permissionLevel).toBe("app_context");
    expect(prompt.safeContext.selectedRecordId).toBeUndefined();
    expect(prompt.safeContext.visibleRecordIds).toBeUndefined();
    expect(prompt.safeContext.metadata).toEqual({ visibleCount: 1 });
    expect(prompt.history.map((message) => message.content)).toEqual([
      "[redacted prior user query]",
      "[redacted prior tool output]",
    ]);
    expect(prompt.evidenceBundles[0].query).toBe("[redacted raw query]");
    expect(prompt.tools.map((tool) => tool.name)).not.toContain("update_registration_draft");

    const serialized = textOf(prompt);
    expect(serialized).not.toContain(PRIVATE_NOTE);
    expect(serialized).not.toContain(PRECISE_LOCATION);
    expect(serialized).not.toContain(DOCUMENT_TEXT);
    expect(serialized).not.toContain(RAW_QUERY);
    expect(prompt.safeContext.redactions.join("\n")).toContain("metadata.privateNotes");
    expect(prompt.safeContext.redactions.join("\n")).toContain("metadata.preciseLocation");
    expect(prompt.safeContext.redactions.join("\n")).toContain("metadata.uploadedDocumentText");
  });

  test("includes private prompt categories only when context and category allowances are present", () => {
    const evidence = createEvidenceBundle();
    const deniedByContext = buildAgentConversationPrompt({
      session: createSession([evidence]),
      surfaceContext: createSurfaceContext({
        privateContextAllowed: false,
      }),
      userGoal: "Use approved private context.",
      evidenceBundles: [evidence],
      options: {
        includePrivateContext: true,
        includePrivateNotes: true,
        includePreciseLocation: true,
        includeDocumentContents: true,
        includeRawQueryHistory: true,
      },
    });

    expect(deniedByContext.safeContext.privateContextAllowed).toBe(false);
    expect(textOf(deniedByContext)).not.toContain(PRIVATE_NOTE);
    expect(textOf(deniedByContext)).not.toContain(PRECISE_LOCATION);
    expect(textOf(deniedByContext)).not.toContain(DOCUMENT_TEXT);

    const allowed = buildAgentConversationPrompt({
      session: createSession([evidence]),
      surfaceContext: createSurfaceContext(),
      userGoal: "Use approved private context.",
      evidenceBundles: [evidence],
      options: {
        includePrivateContext: true,
        includePrivateNotes: true,
        includePreciseLocation: true,
        includeDocumentContents: true,
        includeRawQueryHistory: true,
      },
    });

    const serialized = textOf(allowed);
    expect(allowed.safeContext.privateContextAllowed).toBe(true);
    expect(allowed.safeContext.permissionLevel).toBe("wallet_write");
    expect(allowed.safeContext.selectedRecordId).toBe("rec-benefits-letter");
    expect(allowed.evidenceBundles[0].query).toBe(RAW_QUERY);
    expect(allowed.history.map((message) => message.content)).toEqual([
      RAW_QUERY,
      `tool output included document: ${DOCUMENT_TEXT}`,
    ]);
    expect(allowed.tools.map((tool) => tool.name)).toContain("update_registration_draft");
    expect(serialized).toContain(PRIVATE_NOTE);
    expect(serialized).toContain(PRECISE_LOCATION);
    expect(serialized).toContain(DOCUMENT_TEXT);
    expect(serialized).toContain(RAW_QUERY);
  });

  test("blocks tools that need private context until the policy grants it", () => {
    const harness = createHarness("proof-center", [...initialGrantReceipts]);
    const executor = createAgentToolExecutor({
      surfaceApi: harness.surfaceApi,
      sessionId: "agent-session-privacy",
      permissionLevel: "share_or_disclose",
      walletUnlocked: true,
      privateContextAllowed: false,
      now: () => NOW,
    });

    const proofCall = createToolCall("create_location_region_proof", {
      verifier: "211 service matcher",
      regionLabel: "multnomah_county",
      recordId: "rec-location-current",
    });
    const denied = executor.validateToolCall(proofCall);
    expect(denied.ok).toBe(false);
    if (denied.ok) throw new Error("create_location_region_proof should require private context");
    expect(denied.result.error?.code).toBe("private_context_required");

    const allowed = executor.validateToolCall(proofCall, {
      privateContextAllowed: true,
      permissionLevel: "share_or_disclose",
      walletUnlocked: true,
      userPresent: true,
    });
    expect(allowed.ok).toBe(true);
  });

  test("prevents revoked grants from reaching granted-record tools", async () => {
    const activeGrant = createGrantReceipt({});
    const revokedGrant = createGrantReceipt({
      id: "receipt-revoked-decrypt",
      grantId: "grant-revoked-decrypt",
      receiptHash: "hash-revoked-decrypt",
      status: "revoked",
    });
    const harness = createHarness("recipient-access", [activeGrant, revokedGrant]);
    const executor = createAgentToolExecutor({
      surfaceApi: harness.surfaceApi,
      sessionId: "agent-session-privacy",
      permissionLevel: "share_or_disclose",
      walletUnlocked: true,
      privateContextAllowed: true,
      now: () => NOW,
    });

    const revoked = await executor.execute(
      "view_granted_record",
      { grantId: "grant-revoked-decrypt", recordId: "rec-benefits-letter" },
      { confirmed: true, permissionLevel: "share_or_disclose", userPresent: true },
    );
    expect(revoked.status).toBe("failed");
    if (revoked.status !== "failed") throw new Error("revoked grant should fail before decrypting");
    expect(revoked.result.error?.code).toBe("active_grant_required");
    expect(textOf(revoked.result)).not.toContain("decryptedRecord");
    expect(textOf(revoked.result)).not.toContain("Local demo decrypted document preview");

    const active = await executor.execute(
      "view_granted_record",
      { grantId: "grant-active-decrypt", recordId: "rec-benefits-letter" },
      { confirmed: true, permissionLevel: "share_or_disclose", userPresent: true },
    );
    expect(active.status).toBe("succeeded");
    if (active.status !== "succeeded") throw new Error("active grant should allow decrypting");
    expect(textOf(active.result.output)).toContain("decryptedRecord");
    expect(textOf(active.result.output)).toContain("Local demo decrypted document preview");
  });
});
