import { expect, test } from "@playwright/test";

import { createAgentSurfaceApi } from "../src/agent/surfaceApi";
import type { AgentToolCall, AgentToolResult } from "../src/agent/types";
import { runAppAction, type AppActionResult, type AppActionRuntime, type AppActionState } from "../src/app/appActions";
import { createDefaultAppState } from "../src/app/appState";
import type { AuditEvent, ProofReceiptView, RouteId, WalletGrantReceipt } from "../src/models/abby";
import { auditEvents, initialAccessRequests, initialGrantReceipts, proofReceipts } from "../src/services/mockAbbyService";
import { listWalletAuditEvents, loadWalletAccessState, type WalletApiConfig } from "../src/services/walletApi";

test.describe.configure({ mode: "serial" });

const WALLET_API_BASE_URL = "http://wallet.test";
const WALLET_ID = "wallet-demo";
const ACTOR_DID = "did:key:abby-user";

type WalletAccessRequestRecord = {
  request_id: string;
  requester_did: string;
  audience_did: string;
  resources: string[];
  abilities: string[];
  purpose: string;
  status: "pending" | "approved" | "rejected" | "revoked";
  created_at: string;
  grant_status?: "active" | "revoked" | null;
};

type WalletGrantReceiptRecord = {
  receipt_id: string;
  grant_id: string;
  audience_did: string;
  resources: string[];
  abilities: string[];
  purpose: string;
  receipt_hash: string;
  status: "active" | "revoked";
  created_at: string;
  expires_at?: string | null;
};

type WalletAuditRecord = {
  event_id: string;
  created_at: string;
  actor_did: string;
  action: string;
  resource: string;
  decision: string;
  grant_id?: string | null;
};

type WalletProofRecord = {
  proof_id: string;
  proof_type: string;
  verifier_id: string;
  public_inputs: Record<string, unknown>;
  proof_hash: string;
  witness_record_ids: string[];
  is_simulated: boolean;
  proof_system?: string;
  circuit_id?: string | null;
  verifier_digest?: string | null;
  proof_artifact_ref?: string | null;
  verification_status?: string;
  created_at: string;
};

type WalletStubState = {
  accessRequests: WalletAccessRequestRecord[];
  grantReceipts: WalletGrantReceiptRecord[];
  audits: WalletAuditRecord[];
  proofs: WalletProofRecord[];
  proofCounter: number;
};

function cloneJson<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

function createToolCall(name: AgentToolCall["name"], input: unknown): AgentToolCall {
  return {
    id: `tool-${name}`,
    sessionId: "agent-session-demo",
    name,
    input,
    status: "pending",
    requestedAt: "2026-05-05T00:00:00.000Z",
  };
}

function jsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "content-type": "application/json" },
  });
}

function createCorpusPayload() {
  const documents = [
    {
      doc_id: "svc-shelter-1",
      doc_type: "service",
      title: "Emergency shelter intake",
      text: "Emergency shelter intake for adults in Portland with same-day bed availability.",
      text_truncated: false,
      source_url: "https://211.example.org/shelter/intake",
      source_content_cid: "bafy-shelter-1",
      source_page_cid: "bafy-page-shelter-1",
      provider_name: "Shelter Access Center",
      program_name: "Emergency Shelter Intake",
      categories: "Shelter",
      host: "211.example.org",
      city: "Portland",
      state: "OR",
    },
    {
      doc_id: "svc-shelter-2",
      doc_type: "service",
      title: "Family shelter placements",
      text: "Family shelter placements and motel vouchers for families in Portland.",
      text_truncated: false,
      source_url: "https://211.example.org/shelter/family",
      source_content_cid: "bafy-shelter-2",
      source_page_cid: "bafy-page-shelter-2",
      provider_name: "Family Shelter Network",
      program_name: "Family Shelter Placement",
      categories: "Shelter",
      host: "211.example.org",
      city: "Portland",
      state: "OR",
    },
    {
      doc_id: "svc-food-1",
      doc_type: "service",
      title: "Food pantry referrals",
      text: "Food pantry referrals and grocery pickup help in Portland.",
      text_truncated: false,
      source_url: "https://211.example.org/food/pantry",
      source_content_cid: "bafy-food-1",
      source_page_cid: "bafy-page-food-1",
      provider_name: "Neighborhood Pantry",
      program_name: "Pantry Referral",
      categories: "Food",
      host: "211.example.org",
      city: "Portland",
      state: "OR",
    },
  ];

  return {
    documents,
    bm25: {
      schemaVersion: 1,
      documents: [
        {
          doc_id: "svc-shelter-1",
          doc_type: "service",
          source_url: "https://211.example.org/shelter/intake",
          source_content_cid: "bafy-shelter-1",
          source_page_cid: "bafy-page-shelter-1",
          document_length: 12,
          terms: { shelter: 3, emergency: 2, intake: 2, portland: 1 },
          term_idf: { shelter: 2.3, emergency: 1.5, intake: 1.2, portland: 0.8 },
        },
        {
          doc_id: "svc-shelter-2",
          doc_type: "service",
          source_url: "https://211.example.org/shelter/family",
          source_content_cid: "bafy-shelter-2",
          source_page_cid: "bafy-page-shelter-2",
          document_length: 11,
          terms: { shelter: 2, family: 3, portland: 1, vouchers: 1 },
          term_idf: { shelter: 2.3, family: 1.7, portland: 0.8, vouchers: 1.1 },
        },
        {
          doc_id: "svc-food-1",
          doc_type: "service",
          source_url: "https://211.example.org/food/pantry",
          source_content_cid: "bafy-food-1",
          source_page_cid: "bafy-page-food-1",
          document_length: 10,
          terms: { food: 3, pantry: 3, referrals: 1, portland: 1 },
          term_idf: { food: 2.2, pantry: 2.0, referrals: 1.1, portland: 0.8 },
        },
      ],
      documentFrequency: { shelter: 2, emergency: 1, intake: 1, family: 1, food: 1, pantry: 1 },
      k1: 1.2,
      b: 0.75,
      avgdl: 11,
      documentCount: 3,
      maxTermsPerDocument: 8,
    },
  };
}

function createWalletStubState(): WalletStubState {
  return {
    accessRequests: [
      {
        request_id: "access-1",
        requester_did: "did:key:benefits-clinic",
        audience_did: "did:key:benefits-clinic",
        resources: [`wallet://${WALLET_ID}/records/rec-benefits-letter`],
        abilities: ["record/analyze"],
        purpose: "Check if you can get food, bill, or housing help",
        status: "pending",
        created_at: "2026-05-05T09:12:00.000Z",
      },
      {
        request_id: "access-2",
        requester_did: "did:key:outreach",
        audience_did: "did:key:outreach",
        resources: [`wallet://${WALLET_ID}/records/rec-state-id`],
        abilities: ["record/decrypt"],
        purpose: "Check your ID for shelter sign-up",
        status: "pending",
        created_at: "2026-05-04T16:18:00.000Z",
      },
      {
        request_id: "access-3",
        requester_did: "did:key:legal-aid",
        audience_did: "did:key:legal-aid",
        resources: [`wallet://${WALLET_ID}/records/rec-housing-notice`],
        abilities: ["record/analyze"],
        purpose: "Help plan an appeal",
        status: "approved",
        created_at: "2026-04-30T15:05:00.000Z",
        grant_status: "active",
      },
    ],
    grantReceipts: [
      {
        receipt_id: "receipt-1",
        grant_id: "grant-legal-aid",
        audience_did: "did:key:legal-aid",
        resources: [`wallet://${WALLET_ID}/records/rec-housing-notice`],
        abilities: ["record/analyze"],
        purpose: "Help plan an appeal",
        receipt_hash: "hash-legal-aid",
        status: "active",
        created_at: "2026-04-30T15:05:00.000Z",
        expires_at: "2026-05-30T15:05:00.000Z",
      },
    ],
    audits: [
      {
        event_id: "audit-1",
        created_at: "2026-05-05T10:00:00.000Z",
        actor_did: ACTOR_DID,
        action: "wallet.open",
        resource: `wallet://${WALLET_ID}`,
        decision: "allow",
      },
    ],
    proofs: [
      {
        proof_id: "proof-1",
        proof_type: "location_region",
        verifier_id: "211 service matcher",
        public_inputs: {
          region_id: "multnomah_county",
          claim: "location_in_region",
          region_policy_hash: "digest-proof-1",
        },
        proof_hash: "hash-proof-1",
        witness_record_ids: [`wallet://${WALLET_ID}/records/rec-location-current`],
        is_simulated: true,
        proof_system: "simulated",
        circuit_id: "simulated-location-region",
        verifier_digest: "digest-proof-1",
        verification_status: "verified",
        created_at: "2026-05-05T10:38:00.000Z",
      },
    ],
    proofCounter: 1,
  };
}

function installFetchStub() {
  const originalFetch = globalThis.fetch.bind(globalThis);
  const corpus = createCorpusPayload();
  const wallet = createWalletStubState();

  async function stubbedFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
    const inputUrl = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
    const url = new URL(inputUrl, WALLET_API_BASE_URL);
    const method = init?.method ?? (typeof input !== "string" && !(input instanceof URL) ? input.method : "GET");

    if (url.pathname === "/corpus/211-info/current/generated/documents.json") {
      return jsonResponse(corpus.documents);
    }
    if (url.pathname === "/corpus/211-info/current/generated/bm25-documents.json") {
      return jsonResponse(corpus.bm25);
    }

    if (!url.pathname.startsWith(`/wallets/${WALLET_ID}`)) {
      return new Response("Not found", { status: 404 });
    }

    if (url.pathname === `/wallets/${WALLET_ID}/access-requests` && method === "GET") {
      return jsonResponse({ requests: wallet.accessRequests });
    }
    if (url.pathname === `/wallets/${WALLET_ID}/grant-receipts` && method === "GET") {
      return jsonResponse({ receipts: wallet.grantReceipts });
    }
    if (url.pathname === `/wallets/${WALLET_ID}/audit` && method === "GET") {
      return jsonResponse({ events: wallet.audits });
    }
    if (url.pathname === `/wallets/${WALLET_ID}/proofs` && method === "GET") {
      return jsonResponse({ proofs: wallet.proofs });
    }

    if (url.pathname === `/wallets/${WALLET_ID}/locations/rec-location-current/region-proofs` && method === "POST") {
      const rawBody = typeof init?.body === "string" ? init.body : "{}";
      const body = JSON.parse(rawBody) as { region_id?: string };
      wallet.proofCounter += 1;
      const proofId = `proof-${wallet.proofCounter}`;
      const proof: WalletProofRecord = {
        proof_id: proofId,
        proof_type: "location_region",
        verifier_id: "211 service matcher",
        public_inputs: {
          region_id: body.region_id || "unknown_region",
          claim: "location_in_region",
          region_policy_hash: `digest-${proofId}`,
        },
        proof_hash: `hash-${proofId}`,
        witness_record_ids: [`wallet://${WALLET_ID}/records/rec-location-current`],
        is_simulated: false,
        proof_system: "groth16",
        circuit_id: "location-region-v1",
        verifier_digest: `digest-${proofId}`,
        verification_status: "verified",
        created_at: "2026-05-05T11:20:00.000Z",
      };
      wallet.proofs = [proof, ...wallet.proofs.filter((item) => item.proof_id !== proofId)];
      wallet.audits = [
        {
          event_id: `audit-proof-${proofId}`,
          created_at: "2026-05-05T11:20:01.000Z",
          actor_did: ACTOR_DID,
          action: "location_region_proof.created",
          resource: `wallet://${WALLET_ID}/records/rec-location-current`,
          decision: "allow",
        },
        ...wallet.audits,
      ];
      return jsonResponse(proof);
    }

    const accessDecisionMatch = url.pathname.match(
      new RegExp(`^/wallets/${WALLET_ID}/access-requests/([^/]+)/(approve|reject)$`),
    );
    if (accessDecisionMatch && method === "POST") {
      const [, requestId, decision] = accessDecisionMatch;
      const request = wallet.accessRequests.find((item) => item.request_id === requestId);
      if (!request) {
        return new Response("Not found", { status: 404 });
      }
      request.status = decision === "approve" ? "approved" : "rejected";
      request.grant_status = decision === "approve" ? "active" : request.grant_status ?? null;
      if (decision === "approve" && !wallet.grantReceipts.some((item) => item.receipt_id === `receipt-${requestId}`)) {
        wallet.grantReceipts = [
          ...wallet.grantReceipts,
          {
            receipt_id: `receipt-${requestId}`,
            grant_id: `grant-${requestId}`,
            audience_did: request.audience_did,
            resources: request.resources,
            abilities: request.abilities,
            purpose: request.purpose,
            receipt_hash: `hash-${requestId}`,
            status: "active",
            created_at: "2026-05-05T11:40:00.000Z",
            expires_at: "2026-06-05T11:40:00.000Z",
          },
        ];
      }
      wallet.audits = [
        {
          event_id: `audit-${decision}-${requestId}`,
          created_at: "2026-05-05T11:40:01.000Z",
          actor_did: ACTOR_DID,
          action: `access_request.${decision}`,
          resource: request.resources[0] ?? `wallet://${WALLET_ID}`,
          decision,
          grant_id: decision === "approve" ? `grant-${requestId}` : null,
        },
        ...wallet.audits,
      ];
      return jsonResponse(request);
    }

    return new Response("Not found", { status: 404 });
  }

  globalThis.fetch = stubbedFetch as typeof globalThis.fetch;
  return {
    restore() {
      globalThis.fetch = originalFetch;
    },
  };
}

function createHarness(activeRoute: RouteId, walletApiConfig?: WalletApiConfig) {
  const defaults = createDefaultAppState();
  let mobileNavOpen = true;
  let state: AppActionState = {
    activeRoute,
    profile: cloneJson(defaults.profile),
    policy: cloneJson(defaults.policy),
    recipients: cloneJson(defaults.recipients),
    uploads: cloneJson(defaults.uploads),
    accessRequests: cloneJson(initialAccessRequests),
    grantReceipts: cloneJson(initialGrantReceipts),
    walletAuditEvents: cloneJson(auditEvents),
    walletProofReceipts: cloneJson(proofReceipts),
    exportBundleViews: [],
    walletUnlocked: true,
    privateContextAllowed: true,
    permissionLevel: "wallet_write",
  };

  const runtime: AppActionRuntime = {
    getState: () => state,
    setActiveRoute: (route) => {
      state = { ...state, activeRoute: route };
    },
    setMobileNavOpen: (open) => {
      mobileNavOpen = open;
    },
    setProfile: (profile) => {
      state = { ...state, profile };
    },
    setPolicy: (policy) => {
      state = { ...state, policy };
    },
    setRecipients: (recipients) => {
      state = { ...state, recipients };
    },
    setAccessRequests: (accessRequests) => {
      state = { ...state, accessRequests };
    },
    setGrantReceipts: (grantReceipts) => {
      state = { ...state, grantReceipts };
    },
    setWalletAuditEvents: (walletAuditEvents) => {
      state = { ...state, walletAuditEvents };
    },
    setWalletProofReceipts: (walletProofReceipts) => {
      state = { ...state, walletProofReceipts };
    },
    setExportBundleViews: (exportBundleViews) => {
      state = { ...state, exportBundleViews };
    },
    walletApiConfig,
    refreshWalletAccessState: async () => {
      if (!walletApiConfig) return;
      const walletState = await loadWalletAccessState(walletApiConfig);
      state = {
        ...state,
        accessRequests: walletState.accessRequests,
        grantReceipts: walletState.grantReceipts,
      };
    },
    refreshWalletAuditEvents: async () => {
      if (!walletApiConfig) return;
      const events = await listWalletAuditEvents(walletApiConfig);
      state = { ...state, walletAuditEvents: events };
    },
  };

  return {
    runtime,
    surfaceApi: createAgentSurfaceApi(runtime),
    getState: () => state,
    getMobileNavOpen: () => mobileNavOpen,
  };
}

function configuredWalletApi(): WalletApiConfig {
  return {
    apiBaseUrl: WALLET_API_BASE_URL,
    walletId: WALLET_ID,
    actorDid: ACTOR_DID,
  };
}

function unwrapToolOutput(result: AgentToolResult): AppActionResult {
  expect(result.success).toBe(true);
  return result.output as AppActionResult;
}

function actionSnapshot(result: AppActionResult) {
  if (!result.ok) {
    return {
      ok: false as const,
      action: result.action,
      errorCode: result.errorCode,
      message: result.message,
      confirmation: result.confirmation
        ? {
            required: result.confirmation.required,
            title: result.confirmation.title,
            summary: result.confirmation.summary,
            risk: result.confirmation.risk,
            permissionLevel: result.confirmation.permissionLevel,
          }
        : undefined,
    };
  }

  return {
    ok: true as const,
    action: result.action,
    summary: result.summary,
    route: result.route,
    recordIds: result.recordIds,
    artifactId: result.artifactId,
    confirmation: result.confirmation
      ? {
          required: result.confirmation.required,
          title: result.confirmation.title,
          summary: result.confirmation.summary,
          risk: result.confirmation.risk,
          permissionLevel: result.confirmation.permissionLevel,
        }
      : undefined,
    evidenceItems: result.evidenceBundle?.items.map((item) => ({
      id: item.id,
      title: item.title,
      source: item.source,
      citation: item.citation,
    })),
  };
}

function policySnapshot(state: AppActionState) {
  return cloneJson(state.policy);
}

function proofSnapshot(proofs: ProofReceiptView[]) {
  return proofs.map((proof) => ({
    id: proof.id,
    proofType: proof.proofType,
    claim: proof.claim,
    verificationStatus: proof.verificationStatus,
    verifier: proof.verifier,
    publicInputs: proof.publicInputs,
    simulated: proof.simulated,
  }));
}

function accessSnapshot(state: AppActionState) {
  return {
    accessRequests: state.accessRequests.map((request) => ({
      id: request.id,
      status: request.status,
      grantStatus: request.grantStatus,
      requesterName: request.requesterName,
      resourceLabel: request.resourceLabel,
    })),
    grantReceipts: state.grantReceipts.map((receipt: WalletGrantReceipt) => ({
      id: receipt.id,
      status: receipt.status,
      grantId: receipt.grantId,
      audienceDid: receipt.audienceDid,
      resourceLabel: receipt.resourceLabel,
    })),
    walletAuditEvents: state.walletAuditEvents.map((event: AuditEvent) => ({
      id: event.id,
      action: event.action,
      decision: event.decision,
      resource: event.resource,
    })),
  };
}

test("GUI navigation and agent navigate tool converge on route state", async () => {
  const gui = createHarness("home");
  const guiResult = await runAppAction(gui.runtime, "navigate", { route: "social-services" });

  const agent = createHarness("home");
  const agentResult = unwrapToolOutput(
    await agent.surfaceApi.invokeToolCall(createToolCall("navigate", { route: "social-services" })),
  );

  expect(actionSnapshot(guiResult)).toEqual(actionSnapshot(agentResult));
  expect(gui.getState().activeRoute).toBe("social-services");
  expect(agent.getState().activeRoute).toBe("social-services");
  expect(gui.getMobileNavOpen()).toBe(false);
  expect(agent.getMobileNavOpen()).toBe(false);
});

test("GUI check-in policy updates and agent tool updates converge on policy state", async () => {
  const input = {
    intervalDays: 45,
    reminderChannels: ["email", "web"] as const,
    gracePeriodHours: 12,
    escalationEnabled: false,
  };

  const gui = createHarness("check-in");
  const guiResult = await runAppAction(gui.runtime, "update_check_in_policy", input, { confirmed: true });

  const agent = createHarness("check-in");
  const agentResult = unwrapToolOutput(
    await agent.surfaceApi.invokeToolCall(createToolCall("update_check_in_policy", input), { confirmed: true }),
  );

  expect(actionSnapshot(guiResult)).toEqual(actionSnapshot(agentResult));
  expect(policySnapshot(gui.getState())).toEqual(policySnapshot(agent.getState()));
  expect(gui.getState().policy.intervalDays).toBe(30);
  expect(agent.getState().policy.intervalDays).toBe(30);
});

test("GUI service search and search_211_services tool return the same evidence set", async () => {
  const searchInput = { query: "shelter", limit: 2 };

  const guiFetch = installFetchStub();
  const gui = createHarness("social-services");
  const guiResult = await runAppAction(gui.runtime, "search_211_services", searchInput);
  guiFetch.restore();

  const agentFetch = installFetchStub();
  const agent = createHarness("social-services");
  const agentResult = unwrapToolOutput(
    await agent.surfaceApi.invokeToolCall(createToolCall("search_211_services", searchInput)),
  );
  agentFetch.restore();

  expect(actionSnapshot(guiResult)).toEqual(actionSnapshot(agentResult));
  expect(gui.getState().activeRoute).toBe("social-services");
  expect(agent.getState().activeRoute).toBe("social-services");
});

test("GUI proof creation and create_location_region_proof tool stage the same proof receipt", async () => {
  const proofInput = {
    verifier: "211 service matcher",
    regionLabel: "multnomah_county",
    recordId: "rec-location-current",
  };

  const guiFetch = installFetchStub();
  const gui = createHarness("proof-center", configuredWalletApi());
  const guiResult = await runAppAction(gui.runtime, "create_location_region_proof", proofInput, { confirmed: true });
  guiFetch.restore();

  const agentFetch = installFetchStub();
  const agent = createHarness("proof-center", configuredWalletApi());
  const agentResult = unwrapToolOutput(
    await agent.surfaceApi.invokeToolCall(createToolCall("create_location_region_proof", proofInput), {
      confirmed: true,
    }),
  );
  agentFetch.restore();

  expect(actionSnapshot(guiResult)).toEqual(actionSnapshot(agentResult));
  expect(proofSnapshot(gui.getState().walletProofReceipts)).toEqual(proofSnapshot(agent.getState().walletProofReceipts));
  expect(gui.getState().walletProofReceipts[0]?.id).toBe("proof-2");
  expect(agent.getState().walletProofReceipts[0]?.id).toBe("proof-2");
});

test("GUI and agent access-request decisions converge on request, grant, and audit state", async () => {
  const guiFetch = installFetchStub();
  const gui = createHarness("recipient-access", configuredWalletApi());
  await gui.runtime.refreshWalletAccessState?.();
  await gui.runtime.refreshWalletAuditEvents?.();
  const guiApprove = await runAppAction(gui.runtime, "approve_access_request", { requestId: "access-1" }, { confirmed: true });
  const guiReject = await runAppAction(
    gui.runtime,
    "reject_access_request",
    { requestId: "access-2", reason: "Not needed for this visit" },
    { confirmed: true },
  );
  guiFetch.restore();

  const agentFetch = installFetchStub();
  const agent = createHarness("recipient-access", configuredWalletApi());
  await agent.runtime.refreshWalletAccessState?.();
  await agent.runtime.refreshWalletAuditEvents?.();
  const agentApprove = unwrapToolOutput(
    await agent.surfaceApi.invokeToolCall(createToolCall("approve_access_request", { requestId: "access-1" }), {
      confirmed: true,
    }),
  );
  const agentReject = unwrapToolOutput(
    await agent.surfaceApi.invokeToolCall(
      createToolCall("reject_access_request", { requestId: "access-2", reason: "Not needed for this visit" }),
      { confirmed: true },
    ),
  );
  agentFetch.restore();

  expect(actionSnapshot(guiApprove)).toEqual(actionSnapshot(agentApprove));
  expect(actionSnapshot(guiReject)).toEqual(actionSnapshot(agentReject));
  expect(accessSnapshot(gui.getState())).toEqual(accessSnapshot(agent.getState()));
});
