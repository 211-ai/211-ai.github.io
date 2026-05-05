import { expect, test } from "@playwright/test";

import {
  commandSchemas,
  isCommandOutputFor,
  validateCommandSchemas,
  type AgentCommandName,
} from "../src/agent/commandSchemas";
import { planAgentTurn } from "../src/agent/agentPlanner";
import {
  buildPromptSafeSurfaceContext,
  compactPromptConversationHistory,
  guardAgentToolDefinitions,
  guardEvidenceBundles,
  guardPromptText,
} from "../src/agent/promptGuards";
import {
  confirmationRiskForGate,
  evaluateAgentToolPermissionPolicy,
  getAgentToolPermissionPolicy,
} from "../src/agent/permissionPolicy";
import {
  agentToolDefinitions,
  getToolDefinition,
  validateSurfaceRegistry,
} from "../src/agent/surfaceRegistry";
import { createAgentToolExecutor } from "../src/agent/toolExecutor";
import {
  buildServiceNavigationNextSteps,
  evidenceBundleFromResults,
} from "../src/agent/serviceNavigationAgent";
import type { AgentSurfaceApi } from "../src/agent/surfaceApi";
import type {
  AgentMessage,
  AgentPermissionLevel,
  AgentToolCall,
  AgentToolResult,
  EvidenceBundle,
  SurfaceContext,
} from "../src/agent/types";
import type { AppActionResult } from "../src/app/appActions";
import type { RouteId } from "../src/models/abby";
import type { SearchResult } from "../src/lib/graphrag";

const NOW = "2026-05-05T12:00:00.000Z";

function createSurfaceContext(
  route: RouteId,
  overrides: Partial<SurfaceContext> = {},
): SurfaceContext {
  return {
    route,
    routeLabel: route,
    capturedAt: NOW,
    walletUnlocked: true,
    privateContextAllowed: false,
    permissionLevel: "public",
    ...overrides,
  };
}

function createToolCall(name: string, input: unknown): AgentToolCall {
  return {
    id: `tool-${name}`,
    sessionId: "agent-session-unit",
    name,
    input,
    status: "pending",
    requestedAt: NOW,
  };
}

function createFakeSurfaceApi(
  context: SurfaceContext,
  invoked: AgentToolCall[] = [],
): AgentSurfaceApi {
  const successOutput = (name: string): AppActionResult => ({
    ok: true,
    action: name,
    summary: `Ran ${name}`,
  } as AppActionResult);

  return {
    getContext: () => context,
    invoke: async (name) => successOutput(name),
    invokeRequest: async (request) => successOutput(request.name),
    invokeToolCall: async (toolCall): Promise<AgentToolResult> => {
      invoked.push(toolCall);
      return {
        id: `tool-result-${toolCall.id}`,
        toolCallId: toolCall.id,
        name: toolCall.name,
        success: true,
        completedAt: NOW,
        output: successOutput(toolCall.name),
        auditEventId: `audit-${toolCall.id}`,
      };
    },
  };
}

function createSearchResult(docId: string, providerName: string): SearchResult {
  return {
    docId,
    contentCid: `cid-${docId}`,
    pageCid: `page-${docId}`,
    score: 9.5,
    scoreParts: { keyword: 9.5, vector: 0, metadata: 0 },
    snippet: `${providerName} offers pantry appointments and referral support.`,
    document: {
      doc_id: docId,
      doc_type: "service",
      title: `${providerName} program`,
      text: `${providerName} offers pantry appointments and referral support in Portland.`,
      text_truncated: false,
      source_url: `https://211.example.test/services/${docId}`,
      source_content_cid: `cid-${docId}`,
      source_page_cid: `page-${docId}`,
      provider_name: providerName,
      program_name: "Pantry appointments",
      categories: "Food",
      host: "211.example.test",
      city: "Portland",
      state: "OR",
    },
  };
}

test.describe("agent unit contracts", () => {
  test("validates command schemas and rejects malformed command payloads", () => {
    expect(validateCommandSchemas()).toEqual([]);
    expect(validateSurfaceRegistry()).toEqual([]);

    expect(commandSchemas.navigate.isInput({ route: "social-services" })).toBe(true);
    expect(commandSchemas.navigate.isInput({ route: "service-detail" })).toBe(false);

    expect(commandSchemas.search_211_services.isInput({ query: "food pantry", limit: 8 })).toBe(true);
    expect(commandSchemas.search_211_services.isInput({ query: "food pantry", limit: 0 })).toBe(false);
    expect(commandSchemas.search_211_services.isInput({ query: "   ", limit: 8 })).toBe(false);

    expect(commandSchemas.create_verified_export_bundle.isInput({
      audienceName: "Benefits clinic",
      recordIds: ["rec-1"],
      proofIds: ["proof-1"],
    })).toBe(true);
    expect(commandSchemas.create_verified_export_bundle.isInput({
      audienceName: "Benefits clinic",
      recordIds: [],
    })).toBe(false);

    expect(isCommandOutputFor("search_211_services", {
      ok: true,
      summary: "Found pantry records.",
      evidenceBundle: {
        id: "evidence-1",
        query: "pantry",
        generatedAt: NOW,
        items: [{
          id: "svc-food-1",
          title: "Neighborhood Pantry",
          source: "211 corpus",
          snippet: "Food pantry referrals.",
          citation: { label: "Neighborhood Pantry", docId: "svc-food-1" },
        }],
      } satisfies EvidenceBundle,
      recordIds: ["svc-food-1"],
    })).toBe(true);
    expect(isCommandOutputFor("search_211_services", {
      ok: true,
      summary: "Broken evidence.",
      evidenceBundle: { id: "missing-items" },
    })).toBe(false);
  });

  test("routes deterministic planner turns to app, service, wallet, and confirmation actions", () => {
    const homeContext = createSurfaceContext("home");
    const serviceSearch = planAgentTurn({
      content: "Find food pantry services near me",
      context: homeContext,
    });

    expect(serviceSearch.intentKind).toBe("service_navigation");
    expect(serviceSearch.tools.map((tool) => tool.name)).toEqual(["navigate", "search_211_services"]);
    expect(serviceSearch.tools[0].input).toEqual({ route: "social-services" });
    expect(serviceSearch.tools[1].input).toEqual({
      query: "Find food pantry services near me",
      limit: 8,
    });

    const auditTurn = planAgentTurn({
      content: "Open the latest audit history",
      context: createSurfaceContext("home"),
    });
    expect(auditTurn.tools.map((tool) => tool.name)).toEqual(["navigate", "refresh_wallet_audit"]);
    expect(auditTurn.tools[0].input).toEqual({ route: "audit" });
    expect(auditTurn.tools[1].input).toEqual({ limit: 25 });

    const saveTurn = planAgentTurn({
      content: "Save this service",
      context: createSurfaceContext("social-services", {
        selectedServiceDocId: "svc-food-1",
        visibleServiceDocIds: ["svc-food-1"],
      }),
    });
    expect(saveTurn.intentKind).toBe("wallet_action");
    expect(saveTurn.tools).toEqual([{
      name: "save_service",
      input: { serviceId: "svc-food-1" },
      title: getToolDefinition("save_service").title,
    }]);

    const confirmationTurn = planAgentTurn({
      content: "yes, go ahead",
      context: createSurfaceContext("social-services"),
      pendingConfirmations: [{
        id: "confirmation-save",
        sessionId: "agent-session-unit",
        toolCallId: "tool-save",
        title: "Save service",
        summary: "Save service svc-food-1.",
        risk: "high",
        permissionLevel: "write_wallet",
        status: "pending",
        requestedAt: NOW,
      }],
    });
    expect(confirmationTurn.confirmationDecision).toEqual({
      confirmationId: "confirmation-save",
      approved: true,
    });
  });

  test("enforces permission gates before tools can run", () => {
    const savePolicy = getAgentToolPermissionPolicy("save_service");
    expect(savePolicy.gate).toBe("write_wallet");
    expect(confirmationRiskForGate(savePolicy.gate)).toBe("high");

    expect(evaluateAgentToolPermissionPolicy("save_service", {
      route: "home",
      allowedSurfaces: ["social-services"],
      grantedPermissionLevel: "write_wallet",
      walletUnlocked: true,
      privateContextAllowed: false,
      userPresent: true,
      toolTitle: "Save service",
    })).toMatchObject({ ok: false, code: "surface_not_allowed" });

    expect(evaluateAgentToolPermissionPolicy("save_service", {
      route: "social-services",
      allowedSurfaces: ["social-services"],
      grantedPermissionLevel: "public",
      walletUnlocked: true,
      privateContextAllowed: false,
      userPresent: true,
      toolTitle: "Save service",
    })).toMatchObject({ ok: false, code: "permission_denied" });

    expect(evaluateAgentToolPermissionPolicy("save_service", {
      route: "social-services",
      allowedSurfaces: ["social-services"],
      grantedPermissionLevel: "write_wallet",
      walletUnlocked: false,
      privateContextAllowed: false,
      userPresent: true,
      toolTitle: "Save service",
    })).toMatchObject({ ok: false, code: "wallet_locked" });

    expect(evaluateAgentToolPermissionPolicy("create_service_plan", {
      route: "social-services",
      allowedSurfaces: ["social-services"],
      grantedPermissionLevel: "write_wallet",
      walletUnlocked: true,
      privateContextAllowed: false,
      userPresent: true,
      toolTitle: "Create service plan",
    })).toMatchObject({ ok: false, code: "private_context_required" });
  });

  test("requires confirmation for wallet writes and executes public reads directly", async () => {
    const invoked: AgentToolCall[] = [];
    let idCounter = 0;
    const executor = createAgentToolExecutor({
      surfaceApi: createFakeSurfaceApi(createSurfaceContext("social-services", {
        permissionLevel: "write_wallet",
        walletUnlocked: true,
      }), invoked),
      sessionId: "agent-session-unit",
      now: () => NOW,
      createId: (prefix) => `${prefix}-${++idCounter}`,
    });

    const publicRead = await executor.execute("search_211_services", { query: "pantry", limit: 3 });
    expect(publicRead.status).toBe("succeeded");
    expect(invoked.map((toolCall) => toolCall.name)).toEqual(["search_211_services"]);

    const save = await executor.execute("save_service", { serviceId: "svc-food-1" });
    expect(save.status).toBe("waiting_for_confirmation");
    expect(save.toolCall.status).toBe("waiting_for_confirmation");
    if (save.status !== "waiting_for_confirmation") {
      throw new Error("save_service should wait for confirmation");
    }
    expect(save.confirmation).toMatchObject({
      id: "agent-confirmation-3",
      sessionId: "agent-session-unit",
      toolCallId: save.toolCall.id,
      title: "Save service",
      risk: "high",
      permissionLevel: "write_wallet",
      status: "pending",
      details: {
        permissionGate: "write_wallet",
        requiresAudit: true,
        auditEventType: "agent.service.save",
      },
    });
    expect(save.confirmation.summary).toContain("Save service svc-food-1");
    expect(invoked.map((toolCall) => toolCall.name)).toEqual(["search_211_services"]);

    const confirmed = await executor.executeToolCall(save.toolCall, {
      confirmed: true,
      confirmationId: save.confirmation.id,
    });
    expect(confirmed.status).toBe("succeeded");
    expect(invoked.map((toolCall) => toolCall.name)).toEqual(["search_211_services", "save_service"]);
  });

  test("redacts private prompt context, raw history, and raw evidence queries by default", () => {
    const privateContext = createSurfaceContext("register", {
      routeLabel: "Register",
      permissionLevel: "wallet_private",
      walletUnlocked: true,
      privateContextAllowed: true,
      selectedRecordId: "rec-state-id",
      visibleRecordIds: ["rec-state-id", "rec-medical-note"],
      summary: "Jordan is at 123 Main Street and uses jordan@example.test.",
      metadata: {
        visibleCount: 2,
        phone: "503-555-0199",
        privateNotes: "notes: disclose only at intake",
        documentContents: "document: full benefits letter text",
        currentLocation: "45.5201, -122.6802",
      },
    });

    const safe = buildPromptSafeSurfaceContext(privateContext);
    expect(safe.permissionLevel).toBe("app_context");
    expect(safe.privateContextAllowed).toBe(false);
    expect(safe.summary).toBe("Register surface is active.");
    expect(safe.selectedRecordId).toBeUndefined();
    expect(safe.visibleRecordIds).toBeUndefined();
    expect(safe.metadata).toEqual({ visibleCount: 2 });
    expect(safe.redactions.join("\n")).toContain("Private route summaries are replaced");
    expect(JSON.stringify(safe)).not.toContain("jordan@example.test");
    expect(JSON.stringify(safe)).not.toContain("503-555-0199");
    expect(JSON.stringify(safe)).not.toContain("rec-state-id");

    expect(guardPromptText(
      "Email jordan@example.test, call 503-555-0199, private notes: urgent intake.",
      "user.message",
    )).toBe("Email [redacted private contact], call [redacted private contact], [redacted private notes].");

    const history: AgentMessage[] = [{
      id: "message-user",
      sessionId: "agent-session-unit",
      role: "user",
      content: "My phone is 503-555-0199. Find shelter.",
      createdAt: NOW,
      status: "complete",
    }];
    expect(compactPromptConversationHistory(history)).toEqual([{
      role: "user",
      content: "[redacted prior user query]",
      createdAt: NOW,
      status: "complete",
    }]);

    const evidence = evidenceBundleFromResults("pantry near 123 Main Street", [
      createSearchResult("svc-food-1", "Neighborhood Pantry"),
    ]);
    expect(guardEvidenceBundles([evidence])[0].query).toBe("[redacted raw query]");

    const visibleTools = guardAgentToolDefinitions(agentToolDefinitions, privateContext);
    expect(visibleTools.map((tool) => tool.name)).not.toContain("update_registration_draft");
  });

  test("allows explicitly approved private prompt context without exposing unrelated categories", () => {
    const privateContext = createSurfaceContext("register", {
      routeLabel: "Register",
      permissionLevel: "wallet_private",
      walletUnlocked: true,
      privateContextAllowed: true,
      selectedRecordId: "rec-state-id",
      visibleRecordIds: ["rec-state-id"],
      summary: "Profile email is jordan@example.test.",
      metadata: {
        phone: "503-555-0199",
        currentLocation: "45.5201, -122.6802",
        documentContents: "document: full benefits letter text",
      },
    });

    const safe = buildPromptSafeSurfaceContext(privateContext, {
      includePrivateWalletContext: true,
    });

    expect(safe.permissionLevel).toBe("wallet_private");
    expect(safe.privateContextAllowed).toBe(true);
    expect(safe.selectedRecordId).toBe("rec-state-id");
    expect(safe.summary).toBe("Profile email is jordan@example.test.");
    expect(safe.metadata).toEqual({ phone: "503-555-0199" });
    expect(JSON.stringify(safe)).not.toContain("45.5201");
    expect(JSON.stringify(safe)).not.toContain("full benefits letter text");
    expect(safe.redactions.join("\n")).toContain("metadata.currentLocation");
    expect(safe.redactions.join("\n")).toContain("metadata.documentContents");
  });

  test("maps GraphRAG evidence into citations, record IDs, and actionable next steps", () => {
    const first = createSearchResult("svc-food-1", "Neighborhood Pantry");
    const second = createSearchResult("svc-food-2", "Community Kitchen");

    const evidence = evidenceBundleFromResults("food pantry", [first, second]);
    expect(evidence.id).toMatch(/^evidence-/);
    expect(evidence.items.map((item) => item.id)).toEqual(["svc-food-1", "svc-food-2"]);
    expect(evidence.items[0]).toMatchObject({
      title: "Neighborhood Pantry program",
      source: "https://211.example.test/services/svc-food-1",
      citation: {
        label: "Neighborhood Pantry program",
        url: "https://211.example.test/services/svc-food-1",
        contentCid: "cid-svc-food-1",
        pageCid: "page-svc-food-1",
        docId: "svc-food-1",
      },
    });

    expect(buildServiceNavigationNextSteps([first, second])).toEqual([
      "Open service detail svc-food-1 to review Neighborhood Pantry.",
      "After you review a record, you can ask Abby to save it or create a follow-up plan; wallet writes require confirmation.",
    ]);
    expect(buildServiceNavigationNextSteps([])).toEqual([
      "Try a more specific service type, neighborhood, or eligibility term.",
      "For urgent service navigation, contact 211 directly.",
    ]);
  });

  test("keeps every registered tool tied to a concrete permission policy", () => {
    for (const tool of agentToolDefinitions) {
      const commandName = tool.name as AgentCommandName;
      const policy = getAgentToolPermissionPolicy(commandName);
      expect(tool.requiresConfirmation).toBe(policy.requiresConfirmation);
      expect(tool.requiresAudit).toBe(policy.requiresAudit);
      expect(tool.requiresWalletUnlock).toBe(policy.requiresWalletUnlock);
      expect(tool.requiresUserPresence).toBe(policy.requiresUserPresence);
      expect(tool.requiresPrivateContextOptIn).toBe(policy.requiresPrivateContextOptIn);
      expect(tool.permissionLevel as AgentPermissionLevel).toBeTruthy();
    }
  });
});
