import { expect, test, type Page } from "@playwright/test";
import { spawn, type ChildProcess } from "node:child_process";
import { mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { createServer } from "node:net";

type ApiServer = {
  baseUrl: string;
  logs: string[];
  process: ChildProcess;
  tempDir: string;
};

type WalletRecord = {
  record_id: string;
};

type WalletGrant = {
  grant_id: string;
  abilities?: string[];
  caveats?: Record<string, unknown>;
};

type WalletRecordsResponse = {
  records: Array<{
    record_id: string;
    data_type: string;
    public_descriptor?: string;
  }>;
};

type WalletProof = {
  proof_id: string;
  proof_type: string;
  public_inputs: Record<string, unknown>;
};

type WalletProofsResponse = {
  proofs: WalletProof[];
};

type WalletAuditResponse = {
  events: Array<{ action: string }>;
};

type PageDiagnostics = {
  apiErrors: string[];
  browserErrors: string[];
};

const repoRoot = path.resolve(process.cwd(), "../..");
const playwrightPort = Number(process.env.PLAYWRIGHT_PORT ?? 5174);
const uiOrigin = `http://127.0.0.1:${playwrightPort}`;

function delay(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function freePort(): Promise<number> {
  return new Promise((resolve, reject) => {
    const server = createServer();
    server.on("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const address = server.address();
      server.close(() => {
        if (address && typeof address === "object") {
          resolve(address.port);
          return;
        }
        reject(new Error("Could not allocate a local port"));
      });
    });
  });
}

async function apiJson<T>(baseUrl: string, method: string, route: string, payload?: unknown): Promise<T> {
  const response = await fetch(new URL(route, baseUrl), {
    body: payload === undefined ? undefined : JSON.stringify(payload),
    headers: payload === undefined ? undefined : { "content-type": "application/json" },
    method
  });
  const body = (await response.json()) as T;
  if (!response.ok) {
    throw new Error(`${method} ${route} failed with ${response.status}: ${JSON.stringify(body)}`);
  }
  return body;
}

async function apiStatus<T>(
  baseUrl: string,
  method: string,
  route: string,
  payload?: unknown
): Promise<{ body: T; status: number }> {
  const response = await fetch(new URL(route, baseUrl), {
    body: payload === undefined ? undefined : JSON.stringify(payload),
    headers: payload === undefined ? undefined : { "content-type": "application/json" },
    method
  });
  return { body: (await response.json()) as T, status: response.status };
}

async function startWalletApi(): Promise<ApiServer> {
  const tempDir = await mkdtemp(path.join(tmpdir(), "abby-wallet-fullstack-"));
  const servicesJsonl = path.join(tempDir, "services.jsonl");
  await writeFile(
    servicesJsonl,
    [
      JSON.stringify({
        categories: "housing shelter rent case management",
        city: "Portland",
        description: "Rent assistance, shelter placement, and housing case management.",
        id: "housing-navigation",
        name: "Portland Housing Navigation",
        state: "OR"
      }),
      JSON.stringify({
        categories: "food snap benefits",
        city: "Portland",
        description: "SNAP screening and grocery support.",
        id: "food-benefits",
        name: "Food Benefits Desk",
        state: "OR"
      })
    ].join("\n") + "\n",
    "utf-8"
  );
  const port = await freePort();
  const baseUrl = `http://127.0.0.1:${port}`;
  const pythonPath = [path.join(repoRoot, "ipfs_datasets_py"), repoRoot, process.env.PYTHONPATH]
    .filter(Boolean)
    .join(":");
  const logs: string[] = [];
  const apiProcess = spawn(process.env.PYTHON ?? "python3", [
    "-m",
    "uvicorn",
    "wallet_interface.asgi:app",
    "--host",
    "127.0.0.1",
    "--port",
    String(port),
    "--log-level",
    "warning"
  ], {
    cwd: repoRoot,
    env: {
      ...process.env,
      IPFS_AUTO_INSTALL: "false",
      IPFS_DATASETS_AUTO_INSTALL: "false",
      IPFS_DATASETS_PY_MINIMAL_IMPORTS: "1",
      PYTHONPATH: pythonPath,
      WALLET_API_CORS_ORIGINS: uiOrigin,
      WALLET_AUTO_LOAD_REPOSITORY: "true",
      WALLET_AUTO_PERSIST: "true",
      WALLET_REPOSITORY_ROOT: path.join(tempDir, "wallet-repository"),
      WALLET_SERVICES_JSONL: servicesJsonl,
      WALLET_STORAGE_CONFIG: JSON.stringify({
        primary: { type: "local", root: path.join(tempDir, "wallet-blobs") }
      })
    },
    stdio: ["ignore", "pipe", "pipe"]
  });
  apiProcess.stdout?.on("data", (chunk) => logs.push(String(chunk)));
  apiProcess.stderr?.on("data", (chunk) => logs.push(String(chunk)));

  const deadline = Date.now() + 15_000;
  let lastError = "";
  while (Date.now() < deadline) {
    if (apiProcess.exitCode !== null) {
      throw new Error(`wallet API exited early with ${apiProcess.exitCode}:\n${logs.join("")}`);
    }
    try {
      const health = await apiJson<{ status: string }>(baseUrl, "GET", "/health");
      if (health.status === "ok") {
        return { baseUrl, logs, process: apiProcess, tempDir };
      }
    } catch (error) {
      lastError = String(error);
    }
    await delay(100);
  }
  await stopWalletApi({ baseUrl, logs, process: apiProcess, tempDir });
  throw new Error(`wallet API did not become healthy: ${lastError}\n${logs.join("")}`);
}

async function stopWalletApi(server: ApiServer) {
  let exited = server.process.exitCode !== null;
  server.process.once("exit", () => {
    exited = true;
  });
  if (!exited) {
    server.process.kill("SIGTERM");
    await Promise.race([new Promise((resolve) => server.process.once("exit", resolve)), delay(5_000)]).then(
      () => undefined
    );
    if (!exited && server.process.exitCode === null) {
      server.process.kill("SIGKILL");
      await Promise.race([new Promise((resolve) => server.process.once("exit", resolve)), delay(5_000)]).then(
        () => undefined
      );
    }
  }
  await rm(server.tempDir, { force: true, recursive: true });
}

function walletRoute(
  route: string,
  apiBaseUrl: string,
  walletId: string,
  actorDid: string,
  params: Record<string, string>
) {
  const query = new URLSearchParams({
    actorDid,
    walletApiBaseUrl: apiBaseUrl,
    walletId,
    ...params
  });
  return `/?${query.toString()}#/${route}`;
}

function collectPageDiagnostics(page: Page, apiBaseUrl: string): PageDiagnostics {
  const diagnostics: PageDiagnostics = {
    apiErrors: [],
    browserErrors: []
  };
  page.on("pageerror", (error) => {
    diagnostics.browserErrors.push(error.message);
  });
  page.on("console", (message) => {
    if (message.type() === "error") {
      diagnostics.browserErrors.push(message.text());
    }
  });
  page.on("response", (response) => {
    if (!response.url().startsWith(apiBaseUrl) || response.status() < 400) return;
    void response.text().then((body) => {
      diagnostics.apiErrors.push(`${response.status()} ${new URL(response.url()).pathname}: ${body.slice(0, 500)}`);
    });
  });
  return diagnostics;
}

async function signInIfNeeded(page: Page, username = "abby"): Promise<void> {
  const usernameField = page.getByLabel(/username/i).first();
  try {
    await usernameField.waitFor({ state: "visible", timeout: 1_000 });
  } catch {
    return;
  }
  await usernameField.fill(username);
  await page.getByLabel(/password/i).fill("safety-plan");
  await page.getByRole("button", { name: /log in|login|sign in|continue/i }).click();
}

async function visibleHeadingOrDiagnostics(page: Page, name: RegExp, diagnostics: PageDiagnostics) {
  await expect.poll(() => diagnostics.browserErrors).toEqual([]);
  await expect(page.getByRole("heading", { name }))
    .toBeVisible({ timeout: 15_000 })
    .catch(async (error) => {
      const body = await page.locator("body").innerText({ timeout: 1_000 }).catch(() => "");
      throw new Error(
        `${error instanceof Error ? error.message : String(error)}\nURL: ${page.url()}\nBody: ${body.slice(0, 2_000)}`
      );
    });
}

test("service partner pilot workflow is demonstrable through live UI and wallet API", async ({ page }) => {
  const api = await startWalletApi();
  const ownerDid = "did:key:pilot-owner";
  const ownerKeyHex = "55".repeat(32);
  const partnerDid = "did:key:pilot-housing-partner";
  const partnerKeyHex = "66".repeat(32);
  const exactLat = "45.515232";
  const exactLon = "-122.678385";

  try {
    const diagnostics = collectPageDiagnostics(page, api.baseUrl);
    const wallet = await apiJson<{ wallet_id: string }>(api.baseUrl, "POST", "/wallets", { owner_did: ownerDid });

    await page.goto(
      walletRoute("uploads", api.baseUrl, wallet.wallet_id, ownerDid, {
        issuerKeyHex: ownerKeyHex
      })
    );
    await signInIfNeeded(page, ownerDid);
    await visibleHeadingOrDiagnostics(page, /Saved files and info/i, diagnostics);
    await page.getByLabel(/Choose file to upload/i).setInputFiles({
      buffer: Buffer.from(
        [
          "Pilot housing intake",
          "Jane Example can be reached at jane@example.org.",
          "Needs rent assistance, shelter navigation, SNAP, and clinic referral."
        ].join("\n")
      ),
      mimeType: "text/plain",
      name: "pilot-benefits-intake.txt"
    });

    await expect
      .poll(async () => {
        const records = await apiJson<WalletRecordsResponse>(
          api.baseUrl,
          "GET",
          `/wallets/${wallet.wallet_id}/records?data_type=document`
        );
        return records.records[0]?.record_id ?? "";
      })
      .not.toBe("");
    const uploadedRecords = await apiJson<WalletRecordsResponse>(
      api.baseUrl,
      "GET",
      `/wallets/${wallet.wallet_id}/records?data_type=document`
    );
    const documentId = uploadedRecords.records[0].record_id;

    const location = await apiJson<WalletRecord>(api.baseUrl, "POST", `/wallets/${wallet.wallet_id}/locations`, {
      actor_did: ownerDid,
      lat: Number(exactLat),
      lon: Number(exactLon)
    });

    const analysisGrant = await apiJson<WalletGrant>(
      api.baseUrl,
      "POST",
      `/wallets/${wallet.wallet_id}/records/${documentId}/grants`,
      {
        abilities: ["record/analyze"],
        audience_did: partnerDid,
        audience_key_hex: partnerKeyHex,
        issuer_did: ownerDid,
        issuer_key_hex: ownerKeyHex,
        output_types: ["redacted_derived_only"],
        purpose: "housing_navigation_referral",
        user_presence_required: true
      }
    );
    expect(analysisGrant.abilities).toEqual(["record/analyze"]);
    expect(analysisGrant.caveats?.purpose).toBe("housing_navigation_referral");
    expect(analysisGrant.caveats?.output_types).toEqual(["redacted_derived_only"]);

    await page.goto(
      walletRoute("recipient-access", api.baseUrl, wallet.wallet_id, partnerDid, {
        audienceKeyHex: partnerKeyHex
      })
    );
    await signInIfNeeded(page, partnerDid);
    await visibleHeadingOrDiagnostics(page, /Requests to see my info/i, diagnostics);
    const receipt = page.getByRole("article", { name: /Pilot Housing Partner/i }).filter({ hasText: "Share proof code" });
    await expect(receipt).toBeVisible({ timeout: 15_000 });
    await receipt.getByRole("button", { name: /Redacted analysis/i }).click();
    await expect.poll(() => diagnostics.apiErrors).toEqual([]);
    await expect(receipt).toContainText("redacted_document_analysis · redacted_derived_only", { timeout: 15_000 });
    await expect(receipt.getByText(/jane@example\.org/i)).toHaveCount(0);

    const coarseGrant = await apiJson<WalletGrant>(
      api.baseUrl,
      "POST",
      `/wallets/${wallet.wallet_id}/locations/${location.record_id}/coarse-grants`,
      {
        audience_did: partnerDid,
        audience_key_hex: partnerKeyHex,
        issuer_did: ownerDid,
        issuer_key_hex: ownerKeyHex
      }
    );
    const coarseInvocation = await apiJson<{ token: string }>(
      api.baseUrl,
      "POST",
      `/wallets/${wallet.wallet_id}/locations/${location.record_id}/coarse-invocations`,
      {
        actor_did: partnerDid,
        actor_key_hex: partnerKeyHex,
        grant_id: coarseGrant.grant_id,
        purpose: "service_matching"
      }
    );
    const serviceMatches = await apiJson<{ matches: Array<{ service: { id: string }; reasons: string[] }> }>(
      api.baseUrl,
      "POST",
      `/wallets/${wallet.wallet_id}/services/match`,
      {
        actor_did: partnerDid,
        actor_key_hex: partnerKeyHex,
        invocation_token: coarseInvocation.token,
        limit: 5,
        location_record_id: location.record_id,
        need_terms: ["housing"]
      }
    );
    expect(serviceMatches.matches[0].service.id).toBe("housing-navigation");
    expect(JSON.stringify(serviceMatches)).not.toContain(exactLat);
    expect(JSON.stringify(serviceMatches)).not.toContain(exactLon);

    await page.goto(
      walletRoute("proof-center", api.baseUrl, wallet.wallet_id, ownerDid, {
        issuerKeyHex: ownerKeyHex
      })
    );
    await signInIfNeeded(page, ownerDid);
    await visibleHeadingOrDiagnostics(page, /Verified wallet claims/i, diagnostics);
    await page.getByLabel(/Location record ID/i).fill(location.record_id);
    await page.getByLabel(/Region ID/i).fill("multnomah_county");
    await page.getByRole("button", { name: /Create proof/i }).click();
    await expect(page.getByText(/Proof receipt created/i)).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText("multnomah_county")).toBeVisible();
    await expect(page.getByText(exactLat)).toHaveCount(0);
    await expect(page.getByText(exactLon)).toHaveCount(0);
    const proofs = await apiJson<WalletProofsResponse>(api.baseUrl, "GET", `/wallets/${wallet.wallet_id}/proofs`);
    const regionProof = proofs.proofs.find((proof) => proof.proof_type === "location_region");
    expect(regionProof?.public_inputs.claim).toBe("location_in_region");
    expect(JSON.stringify(regionProof?.public_inputs ?? {})).not.toMatch(/lat|lon|witness|45\.515232|-122\.678385/i);

    await apiJson(api.baseUrl, "POST", "/analytics/templates", {
      allowed_derived_fields: ["county", "need_category"],
      allowed_record_types: ["location", "need"],
      created_by: "did:key:pilot-analytics-reviewer",
      epsilon_budget: 0.5,
      min_cohort_size: 2,
      purpose: "Approved pilot aggregate housing gap reporting",
      template_id: "pilot_housing_gap_v1",
      title: "Pilot housing service gaps"
    });
    const pilotConsent = await apiJson<{ consent_id: string }>(
      api.baseUrl,
      "POST",
      `/wallets/${wallet.wallet_id}/analytics/consents/from-template`,
      {
        actor_did: ownerDid,
        template_id: "pilot_housing_gap_v1"
      }
    );
    await apiJson(api.baseUrl, "POST", `/wallets/${wallet.wallet_id}/analytics/contributions`, {
      actor_did: ownerDid,
      consent_id: pilotConsent.consent_id,
      fields: { county: "Multnomah", need_category: "housing" },
      template_id: "pilot_housing_gap_v1"
    });
    const cohortWallet = await apiJson<{ wallet_id: string }>(api.baseUrl, "POST", "/wallets", {
      owner_did: "did:key:pilot-cohort-owner"
    });
    const cohortConsent = await apiJson<{ consent_id: string }>(
      api.baseUrl,
      "POST",
      `/wallets/${cohortWallet.wallet_id}/analytics/consents/from-template`,
      {
        actor_did: "did:key:pilot-cohort-owner",
        template_id: "pilot_housing_gap_v1"
      }
    );
    await apiJson(api.baseUrl, "POST", `/wallets/${cohortWallet.wallet_id}/analytics/contributions`, {
      actor_did: "did:key:pilot-cohort-owner",
      consent_id: cohortConsent.consent_id,
      fields: { county: "Multnomah", need_category: "housing" },
      template_id: "pilot_housing_gap_v1"
    });
    const aggregate = await apiJson<{ released: boolean; suppressed: boolean }>(
      api.baseUrl,
      "POST",
      "/analytics/pilot_housing_gap_v1/count-by-fields",
      {
        group_by: ["county", "need_category"],
        min_cohort_size: 2
      }
    );
    expect(aggregate.released).toBe(true);
    expect(aggregate.suppressed).toBe(false);

    await apiJson(api.baseUrl, "POST", `/wallets/${wallet.wallet_id}/grants/${analysisGrant.grant_id}/revoke`, {
      actor_did: ownerDid
    });
    await apiJson(api.baseUrl, "POST", `/wallets/${wallet.wallet_id}/grants/${coarseGrant.grant_id}/revoke`, {
      actor_did: ownerDid
    });
    await apiJson(
      api.baseUrl,
      "POST",
      `/wallets/${wallet.wallet_id}/analytics/consents/${pilotConsent.consent_id}/revoke`,
      {
        actor_did: ownerDid
      }
    );
    const blockedAnalysis = await apiStatus<Record<string, unknown>>(
      api.baseUrl,
      "POST",
      `/wallets/${wallet.wallet_id}/records/${documentId}/analyze/redacted`,
      {
        actor_did: partnerDid,
        actor_key_hex: partnerKeyHex,
        grant_id: analysisGrant.grant_id
      }
    );
    expect(blockedAnalysis.status).toBeGreaterThanOrEqual(400);

    await page.goto(
      walletRoute("recipient-access", api.baseUrl, wallet.wallet_id, partnerDid, {
        audienceKeyHex: partnerKeyHex
      })
    );
    await signInIfNeeded(page, partnerDid);
    await expect(
      page.getByRole("article", { name: /Pilot Housing Partner/i }).filter({ hasText: "revoked" }).first()
    ).toBeVisible({ timeout: 15_000 });

    await page.goto(walletRoute("audit", api.baseUrl, wallet.wallet_id, ownerDid, { issuerKeyHex: ownerKeyHex }));
    await signInIfNeeded(page, ownerDid);
    await visibleHeadingOrDiagnostics(page, /Consent and access history/i, diagnostics);
    for (const action of [
      "record/add",
      "grant/create",
      "record/analyze_redacted",
      "location/read_coarse",
      "proof/create",
      "analytics/consent_create",
      "analytics/contribute",
      "analytics/consent_revoke",
      "grant/revoke"
    ]) {
      await expect(page.getByRole("heading", { name: action }).first()).toBeVisible({ timeout: 15_000 });
    }

    const audit = await apiJson<WalletAuditResponse>(api.baseUrl, "GET", `/wallets/${wallet.wallet_id}/audit`);
    expect(audit.events.map((event) => event.action)).toEqual(
      expect.arrayContaining([
        "record/add",
        "grant/create",
        "invocation/issue",
        "invocation/verify",
        "record/analyze_redacted",
        "location/read_coarse",
        "proof/create",
        "analytics/consent_create",
        "analytics/contribute",
        "analytics/consent_revoke",
        "grant/revoke"
      ])
    );
  } finally {
    await stopWalletApi(api);
  }
});

test("export center works against a live wallet API", async ({ page }) => {
  const api = await startWalletApi();
  const ownerDid = "did:key:fullstack-owner";
  const ownerKeyHex = "11".repeat(32);
  const delegateDid = "did:key:fullstack-clinic";
  const delegateKeyHex = "22".repeat(32);

  try {
    const diagnostics = collectPageDiagnostics(page, api.baseUrl);
    const wallet = await apiJson<{ wallet_id: string }>(api.baseUrl, "POST", "/wallets", { owner_did: ownerDid });
    const document = await apiJson<WalletRecord>(api.baseUrl, "POST", `/wallets/${wallet.wallet_id}/documents/text`, {
      actor_did: ownerDid,
      filename: "fullstack-benefits.txt",
      key_hex: ownerKeyHex,
      text: "Full-stack export note for benefits portability. Email jane@example.org must not appear in exports.",
      title: "Full-stack benefits note"
    });
    const location = await apiJson<WalletRecord>(api.baseUrl, "POST", `/wallets/${wallet.wallet_id}/locations`, {
      actor_did: ownerDid,
      lat: 45.515232,
      lon: -122.678385
    });

    await page.goto(
      walletRoute("exports", api.baseUrl, wallet.wallet_id, ownerDid, {
        audienceKeyHex: delegateKeyHex,
        issuerKeyHex: ownerKeyHex
      })
    );
    await signInIfNeeded(page, ownerDid);
    await visibleHeadingOrDiagnostics(page, /Shareable wallet bundles/i, diagnostics);
    await page.getByLabel(/Recipient DID/i).fill(delegateDid);
    await page.getByLabel(/Recipient label/i).fill("Full-stack Clinic");
    await page.getByLabel(/Purpose/i).fill("benefits_portability");
    await page.getByLabel(/Record IDs/i).fill(`${document.record_id}\n${location.record_id}`);
    await page.getByRole("button", { name: /Create bundle/i }).click();

    await expect(page.getByText(/Export bundle verified/i)).toBeVisible({ timeout: 15_000 });
    const createdBundle = page.getByRole("article", { name: /Full-stack Clinic/i });
    await expect(createdBundle.getByText(/storage verified/i)).toBeVisible();
    await expect(createdBundle.getByText(/hash verified/i)).toBeVisible();
    await expect(createdBundle.getByText(/schema verified/i)).toBeVisible();
    await createdBundle.getByRole("button", { name: /Import descriptors/i }).click();
    await expect(page.getByText(/Export descriptors imported/i)).toBeVisible();
    await expect(createdBundle.getByText(/import verified/i)).toBeVisible();

    await expect
      .poll(async () => {
        const audit = await apiJson<{ events: Array<{ action: string }> }>(
          api.baseUrl,
          "GET",
          `/wallets/${wallet.wallet_id}/audit`
        );
        return audit.events.map((event) => event.action);
      })
      .toEqual(expect.arrayContaining(["export/create"]));
  } finally {
    await stopWalletApi(api);
  }
});

test("recipient access runs live redacted analysis workflows", async ({ page }) => {
  const api = await startWalletApi();
  const ownerDid = "did:key:fullstack-owner";
  const ownerKeyHex = "33".repeat(32);
  const delegateDid = "did:key:fullstack-clinic";
  const delegateKeyHex = "44".repeat(32);
  const plaintext = [
    "Full name: Jane Example",
    "Email: jane@example.org",
    "Phone: 503-555-1212",
    "SSN: 123-45-6789",
    "Rent assistance required: yes",
    "SNAP enrollment: yes",
    "Clinic referral needed: yes"
  ].join("\n");

  try {
    const diagnostics = collectPageDiagnostics(page, api.baseUrl);
    const wallet = await apiJson<{ wallet_id: string }>(api.baseUrl, "POST", "/wallets", { owner_did: ownerDid });
    const document = await apiJson<WalletRecord>(
      api.baseUrl,
      "POST",
      `/wallets/${wallet.wallet_id}/documents/text`,
      {
        actor_did: ownerDid,
        filename: "fullstack-intake-form.txt",
        key_hex: ownerKeyHex,
        text: plaintext,
        title: "Full-stack intake form"
      }
    );
    await apiJson<WalletGrant>(
      api.baseUrl,
      "POST",
      `/wallets/${wallet.wallet_id}/records/${document.record_id}/grants`,
      {
        issuer_did: ownerDid,
        audience_did: delegateDid,
        issuer_key_hex: ownerKeyHex,
        audience_key_hex: delegateKeyHex,
        abilities: ["record/analyze", "record/decrypt"],
        output_types: [
          "summary",
          "plaintext",
          "redacted_derived_only",
          "vector_profile",
          "redacted_extracted_text",
          "redacted_form_analysis",
          "redacted_graphrag"
        ],
        purpose: "service_matching",
        user_presence_required: true
      }
    );

    await page.goto(
      walletRoute("recipient-access", api.baseUrl, wallet.wallet_id, delegateDid, {
        audienceKeyHex: delegateKeyHex
      })
    );
    await signInIfNeeded(page, delegateDid);
    await visibleHeadingOrDiagnostics(page, /Requests to see my info/i, diagnostics);
    const receipt = page.getByRole("article", { name: /Fullstack Clinic/i }).filter({ hasText: "Share proof code" });
    await expect(receipt).toBeVisible({ timeout: 15_000 });

    await receipt.getByRole("button", { name: /Make safe summary/i }).click();
    await expect(receipt.getByText(/summary · derived_only/i)).toBeVisible({ timeout: 15_000 });
    await expect(receipt.getByText(document.record_id)).toBeVisible();

    await receipt.getByRole("button", { name: /Redacted analysis/i }).click();
    await expect.poll(() => diagnostics.apiErrors).toEqual([]);
    await expect(receipt).toContainText("redacted_document_analysis · redacted_derived_only", { timeout: 15_000 });
    await expect(receipt.getByText(/jane@example\.org/i)).toHaveCount(0);
    await expect(receipt.getByText(/503-555-1212/i)).toHaveCount(0);
    await expect(receipt.getByText(/123-45-6789/i)).toHaveCount(0);

    await receipt.getByRole("button", { name: /Vector profile/i }).click();
    await expect.poll(() => diagnostics.apiErrors).toEqual([]);
    await expect(receipt).toContainText("redacted_document_vector_profile · encrypted_vector_profile", {
      timeout: 15_000
    });
    await expect(receipt).toContainText("redacted_lexical_hash_vector");

    await receipt.getByRole("button", { name: /Extract text/i }).click();
    await expect.poll(() => diagnostics.apiErrors).toEqual([]);
    await expect(receipt).toContainText("redacted_document_text_extraction · redacted_extracted_text", {
      timeout: 15_000
    });
    await expect(receipt).toContainText("[REDACTED_EMAIL]");
    await expect(receipt.getByText(/jane@example\.org/i)).toHaveCount(0);
    await expect(receipt.getByText(/503-555-1212/i)).toHaveCount(0);
    await expect(receipt.getByText(/123-45-6789/i)).toHaveCount(0);

    await receipt.getByRole("button", { name: /Analyze form/i }).click();
    await expect.poll(() => diagnostics.apiErrors).toEqual([]);
    await expect(receipt).toContainText("redacted_document_form_analysis · redacted_form_analysis", {
      timeout: 15_000
    });
    await expect(receipt).toContainText("redacted fields");

    await receipt.getByRole("button", { name: /Build GraphRAG/i }).click();
    await expect.poll(() => diagnostics.apiErrors).toEqual([]);
    await expect(receipt).toContainText("redacted_document_graphrag · redacted_graphrag", { timeout: 15_000 });
    await expect(receipt).toContainText("redacted_category_entity_graph");

    await receipt.getByRole("button", { name: /View document/i }).click();
    await expect.poll(() => diagnostics.apiErrors).toEqual([]);
    await expect(receipt.getByText(plaintext)).toBeVisible();
    await expect(receipt.getByText(`${plaintext.length} bytes`)).toBeVisible();

    await expect
      .poll(async () => {
        const audit = await apiJson<{ events: Array<{ action: string }> }>(
          api.baseUrl,
          "GET",
          `/wallets/${wallet.wallet_id}/audit`
        );
        return audit.events.map((event) => event.action);
      })
      .toEqual(
        expect.arrayContaining([
          "record/analyze",
          "record/analyze_redacted",
          "record/vector_profile",
          "record/extract_text_redacted",
          "record/analyze_form_redacted",
          "record/graphrag_redacted",
          "record/decrypt",
          "invocation/issue",
          "invocation/verify"
        ])
      );
  } finally {
    await stopWalletApi(api);
  }
});
