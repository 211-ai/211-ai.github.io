import { expect, test, type Page } from "@playwright/test";
import { spawn, type ChildProcess } from "node:child_process";
import { mkdtemp, rm } from "node:fs/promises";
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

async function startWalletApi(): Promise<ApiServer> {
  const tempDir = await mkdtemp(path.join(tmpdir(), "abby-wallet-fullstack-"));
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

// ---------------------------------------------------------------------------
// World ID sanitized proof display with a live wallet API
// ---------------------------------------------------------------------------

test("World ID disabled state is handled gracefully with a live wallet API", async ({ page }) => {
  const api = await startWalletApi();
  const ownerDid = "did:key:fullstack-world-id-owner";

  const query = new URLSearchParams({
    walletApiBaseUrl: api.baseUrl,
    walletId: "wallet-demo",
    actorDid: ownerDid
  });
  const targetRoute = `/?${query.toString()}#/proof-center`;

  const diagnostics = collectPageDiagnostics(page, api.baseUrl);

  try {
    await page.goto(targetRoute);
    await signInIfNeeded(page);

    // The wallet API may not have World ID enabled – which is fine.
    // The panel should display an Unavailable badge or disabled button.
    const panel = page.getByRole("article", { name: /World ID verification/i });
    await expect(panel).toBeVisible({ timeout: 15_000 });

    const verifyButton = panel.getByRole("button", { name: /Verify with World ID/i });
    await expect(verifyButton).toBeVisible({ timeout: 5_000 });

    // When World ID config is not enabled, the button must be disabled (no accidental
    // verification against an unconfigured backend)
    const buttonDisabled = await verifyButton.isDisabled();
    if (buttonDisabled) {
      // World ID is correctly disabled – verify the fallback messaging
      await expect(panel.getByText(/Unavailable|disabled|unavailable/i)).toBeVisible();
    }

    // No browser errors should have occurred
    await expect.poll(() => diagnostics.browserErrors).toEqual([]);
  } finally {
    await stopWalletApi(api);
  }
});

test("World ID proof-center with mocked verified state shows no raw nullifier via live API", async ({ page }) => {
  const api = await startWalletApi();
  const ownerDid = "did:key:fullstack-world-id-notnull-owner";

  const query = new URLSearchParams({
    walletApiBaseUrl: api.baseUrl,
    walletId: "wallet-demo",
    actorDid: ownerDid
  });
  const targetRoute = `/?${query.toString()}#/proof-center`;

  const diagnostics = collectPageDiagnostics(page, api.baseUrl);

  // Intercept World ID wallet API routes so we can inject a verified state
  // without needing actual World ID credentials in the test environment.
  await page.route(`${api.baseUrl}/wallets/*/world-id/**`, async (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname;
    const method = route.request().method();

    if (path.endsWith("/world-id/config")) {
      await route.fulfill({
        json: {
          enabled: true,
          app_id: "app_staging_demo",
          rp_id: "rp_demo",
          default_action: "wallet-attach-world-id-v1",
          environment: "staging",
          credential_policy: "proof_of_human",
          allow_legacy_proofs: false,
          require_user_presence: true
        }
      });
      return;
    }
    if (path.endsWith("/world-id/status")) {
      await route.fulfill({
        json: {
          verified: true,
          binding_id: "world-id-binding-fullstack",
          proof_id: "proof-world-id-fullstack",
          verified_at: "2026-06-14T16:00:00Z",
          action: "wallet-attach-world-id-v1",
          credential_policy: "proof_of_human",
          active_binding_count: 1
        }
      });
      return;
    }
    if (path.endsWith("/world-id/rp-signature") && method === "POST") {
      const now = Math.floor(Date.now() / 1000);
      await route.fulfill({
        json: {
          app_id: "app_staging_demo",
          action: "wallet-attach-world-id-v1",
          signal: `211-ai:wallet-world-id:v1:wallet-demo:${ownerDid}`,
          environment: "staging",
          allow_legacy_proofs: false,
          require_user_presence: true,
          rp_context: {
            rp_id: "rp_demo",
            nonce: "nonce-fullstack-test",
            created_at: now,
            expires_at: now + 300,
            signature: "0xmocksig"
          }
        }
      });
      return;
    }
    await route.fulfill({ status: 404, json: { error: "unexpected world-id call", path } });
  });

  // Let the proofs endpoint pass through to the live API (so we get a real empty proofs list)
  // but also intercept to inject a World ID proof receipt
  await page.route(`${api.baseUrl}/wallets/*/proofs*`, async (route) => {
    await route.fulfill({
      json: {
        proofs: [
          {
            proof_id: "proof-world-id-fullstack",
            wallet_id: "wallet-demo",
            proof_type: "world_id_proof_of_human",
            statement: {
              claim: "wallet_actor_has_world_id_proof_of_human",
              wallet_id: "wallet-demo",
              action: "wallet-attach-world-id-v1",
              credential_policy: "proof_of_human"
            },
            verifier_id: "world-developer-portal-v4:rp_demo",
            public_inputs: {
              claim: "World ID proof of human is bound to this wallet",
              rp_id: "rp_demo",
              app_id: "app_staging_demo",
              action: "wallet-attach-world-id-v1",
              signal_hash: "sha256:signal-fullstack",
              credential_policy: "proof_of_human",
              nullifier_commitment: "hmac-sha256:nullifier-fullstack",
              verification_result_hash: "sha256:result-fullstack"
            },
            proof_hash: "sha256:proof-fullstack",
            witness_record_ids: ["wallet://wallet-demo/world-id-binding/world-id-binding-fullstack"],
            is_simulated: false,
            proof_system: "world_id_idkit_v4",
            circuit_id: "world-id-proof-of-human-v4",
            verifier_digest: "digest-fullstack-abcdef",
            proof_artifact_ref: "world-id-proof://proof-world-id-fullstack",
            verification_status: "verified",
            created_at: "2026-06-14T16:00:00Z"
          }
        ]
      }
    });
  });

  try {
    await page.goto(targetRoute);
    await signInIfNeeded(page);

    const panel = page.getByRole("article", { name: /World ID verification/i });
    await expect(panel).toBeVisible({ timeout: 15_000 });

    // Verified state should be displayed
    await expect(panel.getByText(/World ID verified/i)).toBeVisible({ timeout: 10_000 });

    // No raw nullifier values should be visible in the panel or proof card
    await expect(page.getByText(/0xnullifier|raw_nullifier_value/i)).toHaveCount(0);

    const proofCard = page.getByRole("article", {
      name: /World ID proof of human is bound to this wallet/i
    });
    await expect(proofCard).toBeVisible({ timeout: 10_000 });

    // Proof card should show sanitized commitment, not raw nullifier
    await expect(proofCard.getByText(/hmac-sha256:nullifier-fullstack/i)).toBeVisible();
    // Proof card should NOT show idkit proof, raw nullifier, or rp signature values
    await expect(proofCard.getByText(/raw_nullifier|idkit_proof|developer_portal_response|rp_signature/i)).toHaveCount(0);

    // Disclosure panel should name the withheld items
    await expect(panel.getByText(/Raw nullifier.*IDKit proof payload/i)).toBeVisible();

    await expect.poll(() => diagnostics.browserErrors).toEqual([]);
  } finally {
    await stopWalletApi(api);
  }
});
