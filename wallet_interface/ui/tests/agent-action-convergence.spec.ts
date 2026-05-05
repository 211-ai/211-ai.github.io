import { expect, test } from "@playwright/test";
import type { AppActionResult, AppActionRuntime, AppActionState } from "../src/app/appActions";
import { runAppAction } from "../src/app/appActions";
import { createDefaultAppState } from "../src/app/appState";
import type { AgentCommandName } from "../src/agent/commandSchemas";
import { createAgentSurfaceApi } from "../src/agent/surfaceApi";
import type { AgentToolCall } from "../src/agent/types";
import type { RouteId } from "../src/models/abby";
import {
  auditEvents,
  exportBundles,
  initialAccessRequests,
  initialGrantReceipts,
  proofReceipts
} from "../src/services/mockAbbyService";

interface RuntimeHarness {
  runtime: AppActionRuntime;
  state: () => AppActionState;
}

test("navigation changes converge between GUI action and agent tool paths", async () => {
  const gui = makeRuntime({ activeRoute: "home" });
  const agent = makeRuntime({ activeRoute: "home" });
  const input = { route: "proof-center" as RouteId };

  const guiResult = await runGuiAction(gui.runtime, "navigate", input);
  const agentResult = await runAgentTool(agent.runtime, "navigate", input);

  expect(normalizeResult(agentResult)).toEqual(normalizeResult(guiResult));
  expect(projectState(agent.state())).toEqual(projectState(gui.state()));
  expect(gui.state().activeRoute).toBe("proof-center");
});

test("check-in draft updates clamp and persist the same policy state", async () => {
  const gui = makeRuntime({ activeRoute: "check-in" });
  const agent = makeRuntime({ activeRoute: "check-in" });
  const input = {
    intervalDays: 45,
    gracePeriodHours: 0,
    reminderChannels: ["email", "web"],
    escalationEnabled: false
  };

  const guiResult = await runGuiAction(gui.runtime, "update_check_in_policy", input, { confirmed: true });
  const agentResult = await runAgentTool(agent.runtime, "update_check_in_policy", input, { confirmed: true });

  expect(normalizeResult(agentResult)).toEqual(normalizeResult(guiResult));
  expect(projectState(agent.state())).toEqual(projectState(gui.state()));
  expect(gui.state().policy).toMatchObject({
    intervalDays: 30,
    gracePeriodHours: 0,
    reminderChannels: ["email", "web"],
    escalationEnabled: false
  });
});

test("service search returns matching evidence and leaves app state unchanged", async () => {
  const restoreFetch = installServiceSearchFetchMock();
  const gui = makeRuntime({ activeRoute: "social-services", permissionLevel: "public" });
  const agent = makeRuntime({ activeRoute: "social-services", permissionLevel: "public" });
  const input = { query: "shelter food", city: "Portland", category: "Shelter", limit: 2 };

  try {
    const before = projectState(gui.state());
    const guiResult = await runGuiAction(gui.runtime, "search_211_services", input);
    const agentResult = await runAgentTool(agent.runtime, "search_211_services", input);

    expect(normalizeResult(agentResult)).toEqual(normalizeResult(guiResult));
    expect(projectState(gui.state())).toEqual(before);
    expect(projectState(agent.state())).toEqual(before);
    expect(guiResult.ok ? guiResult.recordIds : []).toEqual(["svc-shelter-food", "svc-food-pantry"]);
  } finally {
    restoreFetch();
  }
});

test("proof creation staging requires the same confirmation without changing proof receipts", async () => {
  const gui = makeRuntime({ activeRoute: "proof-center", privateContextAllowed: true });
  const agent = makeRuntime({ activeRoute: "proof-center", privateContextAllowed: true });
  const input = {
    verifier: "211 service matcher",
    regionLabel: "multnomah_county",
    recordId: "rec-location-current"
  };

  const guiResult = await runGuiAction(gui.runtime, "create_location_region_proof", input);
  const agentResult = await runAgentTool(agent.runtime, "create_location_region_proof", input);

  expect(normalizeResult(agentResult)).toEqual(normalizeResult(guiResult));
  expect(projectState(agent.state())).toEqual(projectState(gui.state()));
  expect(guiResult).toMatchObject({ ok: false, errorCode: "confirmation_required" });
  expect(gui.state().walletProofReceipts.map((proof) => proof.id)).toEqual(proofReceipts.map((proof) => proof.id));
});

test("access-request approve and reject decisions converge on request and grant state", async () => {
  const approveGui = makeRuntime({ activeRoute: "recipient-access" });
  const approveAgent = makeRuntime({ activeRoute: "recipient-access" });
  const approveInput = { requestId: "access-1", reason: "User approved in review" };

  const approveGuiResult = await runGuiAction(approveGui.runtime, "approve_access_request", approveInput, {
    confirmed: true
  });
  const approveAgentResult = await runAgentTool(approveAgent.runtime, "approve_access_request", approveInput, {
    confirmed: true
  });

  expect(normalizeResult(approveAgentResult)).toEqual(normalizeResult(approveGuiResult));
  expect(projectState(approveAgent.state())).toEqual(projectState(approveGui.state()));
  expect(approveGui.state().accessRequests.find((request) => request.id === "access-1")?.status).toBe("approved");
  expect(approveGui.state().grantReceipts.some((receipt) => receipt.id === "receipt-access-1")).toBe(true);

  const rejectGui = makeRuntime({ activeRoute: "recipient-access" });
  const rejectAgent = makeRuntime({ activeRoute: "recipient-access" });
  const rejectInput = { requestId: "access-2", reason: "User declined sharing for now" };

  const rejectGuiResult = await runGuiAction(rejectGui.runtime, "reject_access_request", rejectInput, {
    confirmed: true
  });
  const rejectAgentResult = await runAgentTool(rejectAgent.runtime, "reject_access_request", rejectInput, {
    confirmed: true
  });

  expect(normalizeResult(rejectAgentResult)).toEqual(normalizeResult(rejectGuiResult));
  expect(projectState(rejectAgent.state())).toEqual(projectState(rejectGui.state()));
  expect(rejectGui.state().accessRequests.find((request) => request.id === "access-2")?.status).toBe("rejected");
});

async function runGuiAction(
  runtime: AppActionRuntime,
  action: AgentCommandName,
  input: unknown,
  options: { confirmed?: boolean } = {}
) {
  return runAppAction(runtime, action, input, options);
}

async function runAgentTool(
  runtime: AppActionRuntime,
  action: AgentCommandName,
  input: unknown,
  options: { confirmed?: boolean } = {}
) {
  const toolCall: AgentToolCall = {
    id: `tool-${action}`,
    sessionId: "agent-action-convergence",
    name: action,
    input,
    status: "running",
    requestedAt: "2026-05-05T00:00:00.000Z"
  };
  const result = await createAgentSurfaceApi(runtime).invokeToolCall(toolCall, options);
  expect(result.success).toBe(Boolean((result.output as AppActionResult | undefined)?.ok));
  return result.output as AppActionResult;
}

function makeRuntime(overrides: Partial<AppActionState> = {}): RuntimeHarness {
  const defaultState = createDefaultAppState();
  let state: AppActionState = clone({
    activeRoute: "home",
    profile: defaultState.profile,
    policy: defaultState.policy,
    recipients: defaultState.recipients,
    uploads: defaultState.uploads,
    accessRequests: initialAccessRequests,
    grantReceipts: initialGrantReceipts,
    walletAuditEvents: auditEvents,
    walletProofReceipts: proofReceipts,
    exportBundleViews: exportBundles,
    walletUnlocked: true,
    privateContextAllowed: true,
    permissionLevel: "wallet_write",
    ...overrides
  });

  const runtime: AppActionRuntime = {
    getState: () => state,
    setActiveRoute: (activeRoute) => {
      state = { ...state, activeRoute };
    },
    setMobileNavOpen: () => undefined,
    setProfile: (profile) => {
      state = { ...state, profile: clone(profile) };
    },
    setPolicy: (policy) => {
      state = { ...state, policy: clone(policy) };
    },
    setRecipients: (recipients) => {
      state = { ...state, recipients: clone(recipients) };
    },
    setAccessRequests: (accessRequests) => {
      state = { ...state, accessRequests: clone(accessRequests) };
    },
    setGrantReceipts: (grantReceipts) => {
      state = { ...state, grantReceipts: clone(grantReceipts) };
    },
    setWalletAuditEvents: (walletAuditEvents) => {
      state = { ...state, walletAuditEvents: clone(walletAuditEvents) };
    },
    setWalletProofReceipts: (walletProofReceipts) => {
      state = { ...state, walletProofReceipts: clone(walletProofReceipts) };
    },
    setExportBundleViews: (exportBundleViews) => {
      state = { ...state, exportBundleViews: clone(exportBundleViews) };
    }
  };

  return { runtime, state: () => state };
}

function normalizeResult(result: AppActionResult) {
  if (!result.ok) {
    return {
      ok: false,
      action: result.action,
      errorCode: result.errorCode,
      message: result.message,
      retryable: result.retryable,
      confirmation: result.confirmation
    };
  }

  return {
    ok: true,
    action: result.action,
    summary: result.summary,
    route: result.route,
    recordIds: result.recordIds,
    artifactId: result.artifactId,
    confirmation: result.confirmation,
    evidenceBundle: result.evidenceBundle
      ? {
          query: result.evidenceBundle.query,
          items: result.evidenceBundle.items.map((item) => ({
            id: item.id,
            title: item.title,
            source: item.source,
            snippet: item.snippet,
            score: item.score,
            citation: item.citation
          }))
        }
      : undefined
  };
}

function projectState(state: AppActionState) {
  return {
    activeRoute: state.activeRoute,
    policy: state.policy,
    accessRequests: state.accessRequests.map((request) => ({
      id: request.id,
      status: request.status,
      grantStatus: request.grantStatus,
      approvalCount: request.approvalCount
    })),
    grantReceipts: state.grantReceipts.map((receipt) => ({
      id: receipt.id,
      audienceName: receipt.audienceName,
      audienceDid: receipt.audienceDid,
      resourceLabel: receipt.resourceLabel,
      abilities: receipt.abilities,
      status: receipt.status
    })),
    proofReceiptIds: state.walletProofReceipts.map((proof) => proof.id)
  };
}

function installServiceSearchFetchMock() {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.endsWith("/generated/documents.json")) {
      return jsonResponse([
        {
          doc_id: "svc-shelter-food",
          doc_type: "service",
          title: "Emergency shelter and food access",
          text: "Emergency shelter beds and food support in Portland for people who need help tonight.",
          text_truncated: false,
          source_url: "https://211.example/shelter-food",
          source_content_cid: "cid-shelter-food",
          source_page_cid: "page-shelter-food",
          provider_name: "Portland Help Center",
          program_name: "Night shelter",
          categories: "Shelter, Food",
          host: "211.example",
          city: "Portland",
          state: "OR"
        },
        {
          doc_id: "svc-food-pantry",
          doc_type: "service",
          title: "Neighborhood food pantry",
          text: "Food boxes and walk-in pantry support near downtown Portland.",
          text_truncated: false,
          source_url: "https://211.example/food-pantry",
          source_content_cid: "cid-food-pantry",
          source_page_cid: "page-food-pantry",
          provider_name: "Neighborhood Pantry",
          program_name: "Food boxes",
          categories: "Food",
          host: "211.example",
          city: "Portland",
          state: "OR"
        }
      ]);
    }

    if (url.endsWith("/generated/bm25-documents.json")) {
      return jsonResponse({
        schemaVersion: 1,
        documents: [
          {
            doc_id: "svc-shelter-food",
            doc_type: "service",
            source_url: "https://211.example/shelter-food",
            source_content_cid: "cid-shelter-food",
            source_page_cid: "page-shelter-food",
            document_length: 12,
            terms: { shelter: 2, food: 1, portland: 1 },
            term_idf: { shelter: 2, food: 1, portland: 1 }
          },
          {
            doc_id: "svc-food-pantry",
            doc_type: "service",
            source_url: "https://211.example/food-pantry",
            source_content_cid: "cid-food-pantry",
            source_page_cid: "page-food-pantry",
            document_length: 9,
            terms: { food: 2, portland: 1 },
            term_idf: { food: 1, portland: 1 }
          }
        ],
        documentFrequency: { shelter: 1, food: 2, portland: 2 },
        k1: 1.2,
        b: 0.75,
        avgdl: 10,
        documentCount: 2,
        maxTermsPerDocument: 128
      });
    }

    return new Response("Not found", { status: 404 });
  };

  return () => {
    globalThis.fetch = originalFetch;
  };
}

function jsonResponse(body: unknown) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "content-type": "application/json" }
  });
}

function clone<T>(value: T): T {
  return structuredClone(value);
}
