import { expect, test } from "@playwright/test";

test("mobile home exposes the two required primary cards", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("button", { name: /Emergency contacts/i })).toBeVisible();
  await expect(page.getByRole("button", { name: /Social services/i })).toBeVisible();
});

test("registration enforces minimum required profile fields", async ({ page }) => {
  await page.goto("/#/register");
  await expect(page.getByLabel(/Legal or full name/i)).toBeVisible();
  await expect(page.getByLabel(/Birth date/i)).toBeVisible();
  await expect(page.getByLabel(/Photo or photo ID/i)).toBeVisible();
  await expect(page.getByLabel(/Bot check complete/i)).toBeDisabled();
  await page.getByLabel(/Legal or full name/i).fill("Abby Example");
  await page.getByLabel(/Birth date/i).fill("1990-01-01");
  await page.getByLabel(/Quick health check complete/i).check();
  await expect(page.getByLabel(/Bot check complete/i)).toBeEnabled();
  await page.getByLabel(/Bot check complete/i).check();
  await expect(page.getByLabel(/Bot check complete/i)).toBeChecked();
});

test("check-in interval cannot exceed thirty days", async ({ page }) => {
  await page.goto("/#/check-in");
  const interval = page.getByLabel(/Interval days/i);
  await interval.fill("45");
  await expect(interval).toHaveValue("30");
});

test("hash navigation updates the active screen without a full reload", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /Your safety plan/i })).toBeVisible();
  await page.evaluate(() => {
    window.location.hash = "#/contacts";
  });
  await expect(page.getByRole("heading", { name: /People and agencies/i })).toBeVisible();
  await page.evaluate(() => {
    window.location.hash = "#/analytics";
  });
  await expect(page.getByRole("heading", { name: /Share patterns/i })).toBeVisible();
});

test("social services screen exposes local GraphRAG corpus controls", async ({ page }) => {
  await page.goto("/#/social-services");
  await expect(page.getByRole("heading", { name: /Find support/i })).toBeVisible();
  await expect(page.getByRole("heading", { name: /Search the scraped 211 corpus/i })).toBeVisible();
  await expect(page.getByLabel(/Service need/i)).toBeVisible();
  await expect(page.getByRole("button", { name: /Search corpus/i })).toBeVisible();
  await expect(page.getByRole("button", { name: /Build cited answer/i })).toBeVisible();
  await expect(page.getByRole("button", { name: /Try local model/i })).toBeVisible();
  await expect(page.getByLabel(/Use BGE-small hybrid vector search/i)).toBeVisible();
  const runtimeStatus = page.getByLabel(/GraphRAG runtime status/i);
  await expect(runtimeStatus.getByText(/Corpus ready/i)).toBeVisible({ timeout: 20000 });
  await expect(runtimeStatus.getByText(/Search worker ready/i)).toBeVisible();
  await expect(runtimeStatus.getByText(/Xenova\/bge-small-en-v1\.5/i)).toBeVisible();
});

test("social services screen searches the corpus and builds an evidence answer", async ({ page }) => {
  test.setTimeout(120000);
  await page.goto("/#/social-services");
  await page.getByLabel(/Service need/i).fill("food pantry");
  await page.getByRole("button", { name: /Search corpus/i }).click();
  await expect(page.getByText(/\d+ local matches/)).toBeVisible({ timeout: 90000 });
  const firstResult = page.locator(".graphrag-result-item").first();
  await expect(firstResult).toContainText(/food/i);
  await expect(firstResult.getByText(/CID bafkrei/i)).toBeVisible();
  await expect(firstResult.getByRole("link", { name: /Source/i })).toBeVisible();

  await page.getByRole("button", { name: /Build cited answer/i }).click();
  await expect(page.getByRole("heading", { name: /Evidence summary/i })).toBeVisible({ timeout: 90000 });
  await expect(page.locator(".graphrag-answer-card")).toContainText(/strongest local 211 corpus matches/i);
  await expect(page.locator(".graphrag-answer-card")).toContainText(/\[1\]/);
});

test("mobile menu opens navigation and routes to contacts", async ({ page }, testInfo) => {
  test.skip(!/Mobile/i.test(testInfo.project.name), "Mobile navigation is hidden on desktop layouts");
  await page.goto("/");
  await page.getByRole("button", { name: /Open menu/i }).click();
  const mobileNav = page.getByRole("navigation", { name: /Mobile navigation/i });
  await expect(mobileNav).toBeVisible();
  await mobileNav.getByRole("button", { name: /Contacts/i }).click();
  await expect(page.getByRole("heading", { name: /People and agencies/i })).toBeVisible();
  await expect(mobileNav).not.toBeVisible();
});

test("analytics consent shows privacy controls and derived fields", async ({ page }) => {
  await page.goto("/#/analytics");
  await expect(page.getByRole("heading", { name: /Share patterns/i })).toBeVisible();
  const housingStudy = page.getByRole("article", { name: /Housing service gaps/i });
  await expect(housingStudy.locator(".privacy-metrics").getByText(/Minimum cohort/i)).toBeVisible();
  await expect(housingStudy.locator(".privacy-metrics").getByText(/Budget left/i)).toBeVisible();
  await expect(housingStudy.getByText("county", { exact: true })).toBeVisible();
  const preview = housingStudy.getByLabel(/Housing service gaps analytics capability preview/i);
  await expect(preview.getByText(/analytics\/contribute/i)).toBeVisible();
  await expect(preview.getByText(/plaintext decrypt/i)).toBeVisible();
  await expect(preview.getByText(/analytics query/i)).toBeVisible();
  await expect(preview.getByText(/Fields used/i)).toBeVisible();
  await expect(preview.getByText(/Template status/i)).toBeVisible();
  await expect(housingStudy.getByLabel(/Consent expiration/i)).toBeVisible();
  await expect(housingStudy.getByRole("button", { name: /Save consent/i })).toHaveCount(0);
});

test("analytics API controls create and withdraw wallet consent", async ({ page }) => {
  let createRequests = 0;
  let revokeRequests = 0;
  let activeConsent: Record<string, unknown> | null = null;

  await page.route("**/analytics/templates**", async (route) => {
    await route.fulfill({
      json: {
        templates: [
          {
            template_id: "api_housing_gap_v1",
            title: "API housing gaps",
            purpose: "County-level planning through the wallet API.",
            allowed_record_types: ["location", "need"],
            allowed_derived_fields: ["county", "need_category"],
            aggregation_policy: {
              min_cohort_size: 2,
              epsilon_budget: 0.5,
              duplicate_policy: "reject_by_nullifier"
            },
            created_by: "did:key:analyst",
            status: "approved",
            expires_at: null
          },
          {
            template_id: "api_paused_gap_v1",
            title: "API paused gaps",
            purpose: "Paused study.",
            allowed_record_types: ["location"],
            allowed_derived_fields: ["county"],
            aggregation_policy: {
              min_cohort_size: 2,
              epsilon_budget: 0.5,
              duplicate_policy: "reject_by_nullifier"
            },
            created_by: "did:key:analyst",
            status: "paused",
            expires_at: null
          }
        ]
      }
    });
  });

  await page.route("**/wallets/**", async (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname;
    if (path.endsWith("/access-requests")) {
      await route.fulfill({ json: { requests: [] } });
      return;
    }
    if (path.endsWith("/grant-receipts")) {
      await route.fulfill({ json: { receipts: [] } });
      return;
    }
    if (path.endsWith("/records") && url.searchParams.get("data_type") === "document") {
      await route.fulfill({ json: { records: [] } });
      return;
    }
    if (path.endsWith("/audit")) {
      await route.fulfill({ json: { events: [] } });
      return;
    }
    if (path.endsWith("/proofs")) {
      await route.fulfill({ json: { proofs: [] } });
      return;
    }
    if (path.endsWith("/analytics/consents")) {
      await route.fulfill({ json: { consents: activeConsent ? [activeConsent] : [] } });
      return;
    }
    if (path.endsWith("/analytics/consents/from-template")) {
      createRequests += 1;
      expect(route.request().method()).toBe("POST");
      expect(await route.request().postDataJSON()).toMatchObject({
        actor_did: "did:key:owner",
        expires_at: "2026-06-30T23:59:59+00:00",
        template_id: "api_housing_gap_v1"
      });
      activeConsent = {
        consent_id: "consent-api-housing",
        wallet_id: "wallet-demo",
        template_id: "api_housing_gap_v1",
        allowed_record_types: ["location", "need"],
        allowed_derived_fields: ["county", "need_category"],
        aggregation_policy: { min_cohort_size: 2, epsilon_budget: 0.5 },
        created_at: "2026-05-04T12:00:00Z",
        expires_at: "2026-06-30T23:59:59+00:00",
        revoked_at: null,
        status: "active"
      };
      await route.fulfill({ json: activeConsent });
      return;
    }
    if (path.endsWith("/analytics/consents/consent-api-housing/revoke")) {
      revokeRequests += 1;
      expect(route.request().method()).toBe("POST");
      expect(await route.request().postDataJSON()).toMatchObject({ actor_did: "did:key:owner" });
      activeConsent = {
        ...activeConsent,
        revoked_at: "2026-05-04T12:05:00Z",
        status: "revoked"
      };
      await route.fulfill({ json: activeConsent });
      activeConsent = null;
      return;
    }
    await route.fulfill({ status: 404, json: { error: "unexpected wallet API call" } });
  });

  await page.goto(
    "/?walletApiBaseUrl=http%3A%2F%2F127.0.0.1%3A5174&walletId=wallet-demo&actorDid=did%3Akey%3Aowner#/analytics"
  );
  const apiStudy = page.getByRole("article", { name: /API housing gaps/i });
  await expect(apiStudy.getByText(/Template status/i)).toBeVisible();
  await expect(apiStudy.locator(".scope-header").first().locator(".badge").filter({ hasText: /^approved$/i })).toHaveCount(1);
  await apiStudy.getByLabel(/Consent expiration/i).fill("2026-06-30");
  await apiStudy.getByRole("button", { name: /Save consent/i }).click();
  await expect(page.getByText(/Analytics consent saved/i)).toBeVisible();
  await expect(apiStudy.getByText(/consent-api-housing/i)).toBeVisible();
  await apiStudy.getByRole("button", { name: /Withdraw consent/i }).click();
  await expect(page.getByText(/Analytics consent withdrawn/i)).toBeVisible();
  expect(createRequests).toBe(1);
  expect(revokeRequests).toBe(1);
});

test("benefits opt-in previews notification capability boundaries", async ({ page }) => {
  await page.goto("/#/benefits-protection");
  await expect(page.getByRole("heading", { name: /Optional agency notification/i })).toBeVisible();
  const preview = page.getByLabel(/Benefits notification capability preview/i);
  await expect(preview.getByText(/metadata read/i)).toBeVisible();
  await expect(preview.getByText(/derived facts read/i)).toBeVisible();
  await expect(preview.getByText(/precise location read/i)).toBeVisible();
  await expect(preview.getByText(/full wallet export/i)).toBeVisible();
});

test("sharing rules preview scope-derived capabilities", async ({ page }) => {
  await page.goto("/#/sharing-rules");
  await expect(page.getByRole("heading", { name: /Choose what each person can see/i })).toBeVisible();
  const preview = page.getByLabel(/Maya Johnson sharing capability preview/i);
  await expect(preview.getByText(/coarse location read/i)).toBeVisible();
  await expect(preview.getByText(/plaintext decrypt/i)).toBeVisible();
  await expect(preview.getByText(/full wallet export/i)).toBeVisible();
});

test("proof center shows public proof inputs without private coordinates", async ({ page }) => {
  await page.goto("/#/proof-center");
  await expect(page.getByRole("heading", { name: /Verified wallet claims/i })).toBeVisible();
  await expect(page.getByRole("heading", { name: /Create location-region proof/i })).toBeVisible();
  await expect(page.getByLabel(/Create proof capability preview/i).getByText(/location\/prove_region/i)).toBeVisible();
  await expect(page.getByRole("button", { name: /Create proof/i })).toBeDisabled();
  const regionProof = page.getByRole("article", { name: /Location is in service region/i });
  const preview = regionProof.getByLabel(/Location is in service region proof capability preview/i);
  await expect(regionProof.getByText(/multnomah_county/i)).toBeVisible();
  await expect(regionProof.getByText(/location_in_region/i)).toBeVisible();
  await expect(regionProof.getByText("Simulated", { exact: true })).toBeVisible();
  await expect(preview.getByText(/proof\/verify/i)).toBeVisible();
  await expect(preview.getByText(/precise location read/i)).toBeVisible();
  await expect(regionProof.getByText(/^lat$/i)).not.toBeVisible();
  await expect(regionProof.getByText(/^lon$/i)).not.toBeVisible();
});

test("proof center can create an API-backed location region proof", async ({ page }) => {
  let createRequests = 0;
  await page.route("**/wallets/**", async (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname;
    if (path.endsWith("/access-requests")) {
      await route.fulfill({ json: { requests: [] } });
      return;
    }
    if (path.endsWith("/grant-receipts")) {
      await route.fulfill({ json: { receipts: [] } });
      return;
    }
    if (path.endsWith("/records") && url.searchParams.get("data_type") === "document") {
      await route.fulfill({ json: { records: [] } });
      return;
    }
    if (path.endsWith("/audit")) {
      await route.fulfill({ json: { events: [] } });
      return;
    }
    if (path.endsWith("/proofs")) {
      await route.fulfill({ json: { proofs: [] } });
      return;
    }
    if (path.endsWith("/locations/rec-location-current/region-proofs")) {
      createRequests += 1;
      expect(route.request().method()).toBe("POST");
      expect(await route.request().postDataJSON()).toMatchObject({
        actor_did: "did:key:owner",
        region_id: "multnomah_county"
      });
      await route.fulfill({
        json: {
          proof_id: "proof-deterministic-location",
          wallet_id: "wallet-demo",
          proof_type: "location_region",
          statement: {
            claim: "location_in_region",
            region_id: "multnomah_county",
            witness_commitment: "commitment"
          },
          verifier_id: "deterministic-location-region-v0.1",
          public_inputs: {
            claim: "location_in_region",
            region_id: "multnomah_county",
            region_policy_hash: "425551d64c5b78caa09fd67d24b099c1ca8749bc9747daa0ae84a69cf3507e3e"
          },
          proof_hash: "proofhash",
          witness_record_ids: ["rec-location-current"],
          is_simulated: false,
          proof_system: "deterministic-test-proof",
          circuit_id: "deterministic-location-region-v0.1",
          verifier_digest: "digest1234567890abcdef",
          proof_artifact_ref: "deterministic-proof://proofhash",
          verification_status: "verified",
          created_at: "2026-05-03T18:04:00Z"
        }
      });
      return;
    }
    await route.fulfill({ status: 404, json: { error: "unexpected wallet API call" } });
  });

  await page.goto(
    "/?walletApiBaseUrl=http%3A%2F%2F127.0.0.1%3A5174&walletId=wallet-demo&actorDid=did%3Akey%3Aowner#/proof-center"
  );
  await page.getByRole("button", { name: /Create proof/i }).click();
  await expect(page.getByText(/Proof receipt created/i)).toBeVisible();
  const createdProof = page.getByRole("article", { name: /location_in_region/i }).first();
  await expect(createdProof.getByText(/deterministic-test-proof/i)).toBeVisible();
  await expect(createdProof.locator(".scope-header").getByText("verified", { exact: true })).toBeVisible();
  await expect(createdProof.getByText(/multnomah_county/i)).toBeVisible();
  await expect(createdProof.getByText(/^lat$/i)).not.toBeVisible();
  await expect(createdProof.getByText(/^lon$/i)).not.toBeVisible();
  expect(createRequests).toBe(1);
});

test("exports show receipt hashes and storage status", async ({ page }) => {
  await page.goto("/#/exports");
  await expect(page.getByRole("heading", { name: /Shareable wallet bundles/i })).toBeVisible();
  await expect(page.getByRole("heading", { name: /Create export bundle/i })).toBeVisible();
  await expect(page.getByRole("button", { name: /Create bundle/i })).toBeDisabled();
  const preview = page.getByLabel("Export capability preview");
  await expect(preview.getByText(/export\/create/i)).toBeVisible();
  await expect(preview.getByText(/Plaintext decrypt/i)).toBeVisible();
  const legalAidExport = page.getByRole("article", { name: /Legal Aid desk/i });
  await expect(legalAidExport.getByText(/Bundle hash/i)).toBeVisible();
  await expect(legalAidExport.getByText(/storage verified/i)).toBeVisible();
  await expect(legalAidExport.getByText(/import verified/i)).toBeVisible();
  await expect(legalAidExport.getByRole("button", { name: /Import descriptors/i })).toBeDisabled();
  const benefitsExport = page.getByRole("article", { name: /Benefits navigation clinic/i });
  await expect(benefitsExport.getByText(/storage missing/i)).toBeVisible();
});

test("security screen saves and restores wallet snapshots", async ({ page }) => {
  let saved = false;
  let saveRequests = 0;
  let loadRequests = 0;
  let emergencyRequests = 0;
  let storageRequests = 0;
  let storageRepairRequests = 0;
  await page.route("**/wallets/**", async (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname;
    if (path === "/wallets/snapshots") {
      await route.fulfill({ json: { wallet_ids: saved ? ["wallet-demo"] : [] } });
      return;
    }
    if (path === "/wallets/wallet-demo" && route.request().method() === "GET") {
      await route.fulfill({
        json: {
          wallet_id: "wallet-demo",
          owner_did: "did:key:owner",
          controller_dids: ["did:key:owner", "did:key:case-manager"],
          device_dids: ["did:key:owner", "did:key:phone"],
          default_privacy_policy: {},
          governance_policy: {
            threshold: 2,
            approver_dids: ["did:key:owner", "did:key:case-manager"],
            sensitive_abilities: ["wallet/admin"]
          },
          manifest_head: "manifest1234567890abcdefmanifest1234567890abcdef",
          created_at: "2026-05-03T18:00:00Z",
          updated_at: "2026-05-03T18:01:00Z"
        }
      });
      return;
    }
    if (path.endsWith("/snapshot/load")) {
      loadRequests += 1;
      expect(route.request().method()).toBe("POST");
      await route.fulfill({ json: { wallet_id: "wallet-demo", loaded: true } });
      return;
    }
    if (path.endsWith("/snapshot") && route.request().method() === "GET") {
      await route.fulfill({
        json: {
          wallet_id: "wallet-demo",
          path: "/tmp/wallet-demo.json",
          exists: true,
          valid: true,
          format: "envelope",
          snapshot_hash: "abc123def456abc123def456abc123def456abc123def456abc123def456abcd",
          computed_hash: "abc123def456abc123def456abc123def456abc123def456abc123def456abcd"
        }
      });
      return;
    }
    if (path.endsWith("/snapshot")) {
      saveRequests += 1;
      saved = true;
      expect(route.request().method()).toBe("POST");
      await route.fulfill({ json: { wallet_id: "wallet-demo", path: "/tmp/wallet-demo.json" } });
      return;
    }
    if (path === "/wallets/wallet-demo/storage") {
      storageRequests += 1;
      expect(route.request().method()).toBe("GET");
      await route.fulfill({
        json: {
          wallet_id: "wallet-demo",
          record_count: 2,
          reports: [],
          ok: true,
          replica_count: 5,
          failed_replica_count: 0,
          storage_types: {
            ipfs: 2,
            s3: 2,
            filecoin: 1
          },
          created_at: "2026-05-03T18:02:00Z"
        }
      });
      return;
    }
    if (path === "/wallets/wallet-demo/storage/repair") {
      storageRepairRequests += 1;
      expect(route.request().method()).toBe("POST");
      expect(await route.request().postDataJSON()).toMatchObject({ actor_did: "did:key:owner" });
      await route.fulfill({
        json: {
          wallet_id: "wallet-demo",
          record_count: 2,
          reports: [],
          ok: true,
          replica_count: 5,
          failed_replica_count: 0,
          repaired: true,
          repaired_replica_count: 1,
          storage_types: {
            ipfs: 2,
            s3: 2,
            filecoin: 1
          },
          created_at: "2026-05-03T18:04:00Z"
        }
      });
      return;
    }
    if (path.endsWith("/emergency-revoke")) {
      emergencyRequests += 1;
      expect(route.request().method()).toBe("POST");
      const body = await route.request().postDataJSON();
      expect(body).toMatchObject({
        actor_did: "did:key:owner",
        reason: "suspected compromise",
        rotate_keys: true
      });
      await route.fulfill({
        json: {
          wallet_id: "wallet-demo",
          revoked_grant_ids: ["grant-parent", "grant-child"],
          revoked_grant_count: 2,
          rotated_record_ids: ["rec-benefits-letter"],
          rotated_record_count: 1,
          rotation_errors: {},
          rotate_keys: true,
          reason: body.reason
        }
      });
      return;
    }
    if (path.endsWith("/access-requests")) {
      await route.fulfill({ json: { requests: [] } });
      return;
    }
    if (path.endsWith("/grant-receipts")) {
      await route.fulfill({ json: { receipts: [] } });
      return;
    }
    if (path.endsWith("/records") && url.searchParams.get("data_type") === "document") {
      await route.fulfill({ json: { records: [] } });
      return;
    }
    if (path.endsWith("/audit")) {
      await route.fulfill({ json: { events: [] } });
      return;
    }
    await route.fulfill({ status: 404, json: { error: "unexpected wallet API call" } });
  });
  await page.goto(
    "/?walletApiBaseUrl=http%3A%2F%2F127.0.0.1%3A5174&walletId=wallet-demo&actorDid=did%3Akey%3Aowner#/security"
  );

  await expect(page.getByRole("heading", { name: /Account safety/i })).toBeVisible();
  await expect(page.getByText(/no snapshot/i)).toBeVisible();
  await expect(page.getByRole("heading", { name: /Wallet governance/i })).toBeVisible();
  await expect(page.getByText("did:key:case-manager", { exact: true })).toBeVisible();
  await expect(page.getByText("did:key:phone", { exact: true })).toBeVisible();
  const emergencySection = page.locator("section").filter({ hasText: "Emergency revoke" });
  await expect(emergencySection.getByRole("button", { name: /Revoke access/i })).toBeVisible();
  await page.getByRole("button", { name: /Save snapshot/i }).click();
  await expect(page.getByText(/Wallet snapshot saved/i)).toBeVisible();
  await expect(page.getByText(/snapshot ready/i)).toBeVisible();
  await expect(page.getByText(/verified/i)).toBeVisible();
  await expect(page.getByText(/abc123def456/i)).toBeVisible();
  await page.getByRole("button", { name: /Load snapshot/i }).click();
  await expect(page.getByText(/Wallet snapshot loaded/i)).toBeVisible();
  await page.getByRole("button", { name: /Check storage/i }).click();
  await expect(page.getByText(/Encrypted storage replicas verified/i)).toBeVisible();
  await expect(page.getByText(/5 across 2 records/i)).toBeVisible();
  await expect(page.getByText(/ipfs: 2, s3: 2, filecoin: 1/i)).toBeVisible();
  await page.getByRole("button", { name: /Repair storage/i }).click();
  await expect(page.getByText(/Encrypted storage replicas repaired/i)).toBeVisible();
  await emergencySection.getByRole("button", { name: /Revoke access/i }).click();
  await expect(page.getByText(/Emergency revoke completed/i)).toBeVisible();
  await expect(emergencySection.getByText(/Revoked grants/i)).toBeVisible();
  await expect(emergencySection.getByText(/Rotated records/i)).toBeVisible();
  await expect(emergencySection.getByText("2", { exact: true })).toBeVisible();
  await expect(emergencySection.getByText("1", { exact: true })).toBeVisible();
  expect(saveRequests).toBe(1);
  expect(loadRequests).toBe(1);
  expect(emergencyRequests).toBe(1);
  expect(storageRequests).toBe(1);
  expect(storageRepairRequests).toBe(1);
});

test("uploads can repair API-backed document storage", async ({ page }) => {
  let repairRequests = 0;
  let rotationRequests = 0;
  const auditEvents: Array<Record<string, unknown>> = [];
  await page.route("**/wallets/**", async (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname;
    if (path.endsWith("/access-requests")) {
      await route.fulfill({ json: { requests: [] } });
      return;
    }
    if (path.endsWith("/grant-receipts")) {
      await route.fulfill({ json: { receipts: [] } });
      return;
    }
    if (path.endsWith("/records") && url.searchParams.get("data_type") === "document") {
      await route.fulfill({
        json: {
          records: [
            {
              record_id: "rec-benefits-letter",
              data_type: "document",
              sensitivity: "high",
              public_descriptor: "Benefits letter",
              status: "active",
              created_at: "2026-05-03T18:00:00Z"
            }
          ]
        }
      });
      return;
    }
    if (path.endsWith("/records/rec-benefits-letter/storage/repair")) {
      repairRequests += 1;
      expect(route.request().method()).toBe("POST");
      expect(await route.request().postDataJSON()).toMatchObject({ actor_did: "did:key:owner" });
      auditEvents.push({
        event_id: "audit-storage-repair",
        created_at: "2026-05-03T18:03:00Z",
        actor_did: "did:key:owner",
        action: "storage/repair",
        resource: "wallet://wallet-demo/records/rec-benefits-letter",
        decision: "allow",
        grant_id: null
      });
      await route.fulfill({ json: { ok: true } });
      return;
    }
    if (path.endsWith("/records/rec-benefits-letter/rotate-key")) {
      rotationRequests += 1;
      expect(route.request().method()).toBe("POST");
      expect(await route.request().postDataJSON()).toMatchObject({ actor_did: "did:key:owner" });
      auditEvents.push({
        event_id: "audit-key-rotate",
        created_at: "2026-05-03T18:04:00Z",
        actor_did: "did:key:owner",
        action: "record/key_rotate",
        resource: "wallet://wallet-demo/records/rec-benefits-letter",
        decision: "allow",
        grant_id: null
      });
      await route.fulfill({
        json: {
          version_id: "ver-rotated",
          record_id: "rec-benefits-letter",
          encrypted_payload_ref: {},
          encrypted_metadata_ref: null,
          ciphertext_hash: "rotated-hash",
          encryption_suite: "AES-256-GCM",
          key_wraps: []
        }
      });
      return;
    }
    if (path.endsWith("/audit")) {
      await route.fulfill({ json: { events: auditEvents } });
      return;
    }
    if (path.endsWith("/records/rec-benefits-letter/storage")) {
      await route.fulfill({ json: { ok: false } });
      return;
    }
    await route.fulfill({ status: 404, json: { error: "unexpected wallet API call" } });
  });
  await page.goto(
    "/?walletApiBaseUrl=http%3A%2F%2F127.0.0.1%3A5174&walletId=wallet-demo&actorDid=did%3Akey%3Aowner#/uploads"
  );
  const upload = page.locator(".upload-list-item").filter({ hasText: "Benefits letter" });
  await expect(upload.getByText(/storage needs repair/i)).toBeVisible();
  await upload.getByRole("button", { name: /Repair storage/i }).click();
  await expect(upload.getByText(/storage verified/i)).toBeVisible();
  await expect(upload.getByRole("button", { name: /Repair storage/i })).toHaveCount(0);
  await upload.getByRole("button", { name: /Rotate key/i }).click();
  await page.evaluate(() => {
    window.location.hash = "#/audit";
  });
  const storageRepairEvent = page.getByRole("article").filter({ hasText: "storage/repair" });
  const keyRotateEvent = page.getByRole("article").filter({ hasText: "record/key_rotate" });
  await expect(storageRepairEvent.getByText(/wallet:\/\/wallet-demo\/records\/rec-benefits-letter/i)).toBeVisible();
  await expect(keyRotateEvent.getByText(/wallet:\/\/wallet-demo\/records\/rec-benefits-letter/i)).toBeVisible();
  expect(repairRequests).toBe(1);
  expect(rotationRequests).toBe(1);
});

test("recipient receipt can create an encrypted derived analysis artifact", async ({ page }) => {
  let analysisRequests = 0;
  let decryptRequests = 0;
  let delegationRequests = 0;
  const documentPlaintext = "Delegate may view this identity document.";
  const receipts: Array<Record<string, unknown>> = [
    {
      receipt_id: "receipt-analysis",
      grant_id: "grant-analysis",
      audience_did: "did:key:delegate",
      resources: ["wallet://wallet-demo/records/rec-benefits-letter"],
      abilities: ["record/analyze", "record/decrypt", "record/share"],
      purpose: "service_matching",
      receipt_hash: "receipt-hash-analysis",
      status: "active",
      created_at: "2026-05-03T18:00:00Z"
    }
  ];
  const auditEvents: Array<Record<string, unknown>> = [];
  await page.route("**/wallets/**", async (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname;
    if (path.endsWith("/access-requests")) {
      await route.fulfill({ json: { requests: [] } });
      return;
    }
    if (path.endsWith("/grant-receipts")) {
      await route.fulfill({
        json: {
          receipts
        }
      });
      return;
    }
    if (path.endsWith("/grants/grant-analysis/delegate")) {
      delegationRequests += 1;
      expect(route.request().method()).toBe("POST");
      expect(await route.request().postDataJSON()).toMatchObject({
        issuer_did: "did:key:delegate",
        audience_did: "did:key:case-worker",
        resources: ["wallet://wallet-demo/records/rec-benefits-letter"],
        abilities: ["record/analyze"],
        caveats: { purpose: "warm_handoff" }
      });
      receipts.push({
        receipt_id: "receipt-child",
        grant_id: "grant-child",
        audience_did: "did:key:case-worker",
        resources: ["wallet://wallet-demo/records/rec-benefits-letter"],
        abilities: ["record/analyze"],
        purpose: "warm_handoff",
        receipt_hash: "receipt-hash-child",
        status: "active",
        created_at: "2026-05-03T18:03:00Z"
      });
      auditEvents.push({
        event_id: "audit-grant-delegate",
        created_at: "2026-05-03T18:03:00Z",
        actor_did: "did:key:delegate",
        action: "grant/create",
        resource: "wallet://wallet-demo/records/rec-benefits-letter",
        decision: "allow",
        grant_id: "grant-child"
      });
      await route.fulfill({
        json: {
          grant_id: "grant-child",
          issuer_did: "did:key:delegate",
          audience_did: "did:key:case-worker",
          resources: ["wallet://wallet-demo/records/rec-benefits-letter"],
          abilities: ["record/analyze"],
          caveats: { purpose: "warm_handoff" },
          proof_chain: ["grant-analysis"],
          status: "active",
          created_at: "2026-05-03T18:03:00Z"
        }
      });
      return;
    }
    if (path.endsWith("/records/rec-benefits-letter")) {
      await route.fulfill({ status: 404, json: { error: "unexpected record detail call" } });
      return;
    }
    if (path.endsWith("/records/rec-benefits-letter/analyze")) {
      analysisRequests += 1;
      expect(route.request().method()).toBe("POST");
      expect(await route.request().postDataJSON()).toMatchObject({
        actor_did: "did:key:delegate",
        grant_id: "grant-analysis",
        max_chars: 200
      });
      auditEvents.push({
        event_id: "audit-record-analyze",
        created_at: "2026-05-03T18:02:00Z",
        actor_did: "did:key:delegate",
        action: "record/analyze",
        resource: "wallet://wallet-demo/records/rec-benefits-letter",
        decision: "allow",
        grant_id: "grant-analysis"
      });
      await route.fulfill({
        json: {
          artifact_id: "artifact-analysis",
          source_record_ids: ["rec-benefits-letter"],
          artifact_type: "summary",
          output_policy: "derived_only",
          encrypted_payload_ref: {
            uri: "mem://derived-artifact",
            storage_type: "memory",
            digest: "sha256:derived"
          },
          created_at: "2026-05-03T18:01:00Z"
        }
      });
      return;
    }
    if (path.endsWith("/records/rec-benefits-letter/decrypt")) {
      decryptRequests += 1;
      expect(route.request().method()).toBe("POST");
      expect(await route.request().postDataJSON()).toMatchObject({
        actor_did: "did:key:delegate",
        grant_id: "grant-analysis"
      });
      auditEvents.push({
        event_id: "audit-record-decrypt",
        created_at: "2026-05-03T18:02:30Z",
        actor_did: "did:key:delegate",
        action: "record/decrypt",
        resource: "wallet://wallet-demo/records/rec-benefits-letter",
        decision: "allow",
        grant_id: "grant-analysis"
      });
      await route.fulfill({
        json: {
          record_id: "rec-benefits-letter",
          text: documentPlaintext,
          size_bytes: documentPlaintext.length
        }
      });
      return;
    }
    if (path.endsWith("/audit")) {
      await route.fulfill({ json: { events: auditEvents } });
      return;
    }
    await route.fulfill({ status: 404, json: { error: "unexpected wallet API call" } });
  });

  await page.goto(
    "/?walletApiBaseUrl=http%3A%2F%2F127.0.0.1%3A5174&walletId=wallet-demo&actorDid=did%3Akey%3Adelegate#/recipient-access"
  );
  const receipt = page.getByRole("article", { name: /delegate/i }).filter({ hasText: "Receipt hash" });
  await receipt.getByRole("button", { name: /Analyze safely/i }).click();
  await expect(receipt.getByText(/summary · derived_only/i)).toBeVisible();
  await expect(receipt.getByText(/mem:\/\/derived-artifact/i)).toBeVisible();
  await expect(receipt.getByText(/rec-benefits-letter/i)).toBeVisible();
  await receipt.getByRole("button", { name: /View document/i }).click();
  await expect(receipt.getByText(documentPlaintext)).toBeVisible();
  await expect(receipt.getByText(`${documentPlaintext.length} bytes`)).toBeVisible();
  await receipt.getByLabel(/Delegate DID/i).fill("did:key:case-worker");
  await receipt.getByLabel(/Delegated purpose/i).fill("warm_handoff");
  await receipt.getByRole("button", { name: /Delegate access/i }).click();
  await expect(receipt.getByText(/Delegated to did:key:case-worker/i)).toBeVisible();
  await expect(page.getByRole("article", { name: /Case Worker/i }).filter({ hasText: "receipt-hash-child" })).toBeVisible();
  await page.evaluate(() => {
    window.location.hash = "#/audit";
  });
  await expect(page.getByText(/record\/analyze/i)).toBeVisible();
  await expect(page.getByText(/record\/decrypt/i)).toBeVisible();
  await expect(page.getByText(/grant-analysis/i).first()).toBeVisible();
  await expect(page.getByText(/grant-child/i)).toBeVisible();
  expect(analysisRequests).toBe(1);
  expect(decryptRequests).toBe(1);
  expect(delegationRequests).toBe(1);
});

test("audit screen loads wallet API event chain metadata", async ({ page }) => {
  await page.route("**/wallets/**", async (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname;
    if (path.endsWith("/access-requests")) {
      await route.fulfill({ json: { requests: [] } });
      return;
    }
    if (path.endsWith("/grant-receipts")) {
      await route.fulfill({ json: { receipts: [] } });
      return;
    }
    if (path.endsWith("/records") && url.searchParams.get("data_type") === "document") {
      await route.fulfill({ json: { records: [] } });
      return;
    }
    if (path.endsWith("/audit")) {
      await route.fulfill({
        json: {
          events: [
            {
              event_id: "audit-record-analyze",
              created_at: "2026-05-03T18:02:00Z",
              actor_did: "did:key:delegate",
              action: "record/analyze",
              resource: "wallet://wallet-demo/records/rec-benefits-letter",
              decision: "allow",
              grant_id: "grant-analysis"
            },
            {
              event_id: "audit-storage-repair",
              created_at: "2026-05-03T18:03:00Z",
              actor_did: "did:key:owner",
              action: "storage/repair",
              resource: "wallet://wallet-demo/records/rec-benefits-letter",
              decision: "allow",
              grant_id: null
            }
          ]
        }
      });
      return;
    }
    await route.fulfill({ status: 404, json: { error: "unexpected wallet API call" } });
  });

  await page.goto(
    "/?walletApiBaseUrl=http%3A%2F%2F127.0.0.1%3A5174&walletId=wallet-demo&actorDid=did%3Akey%3Aowner#/audit"
  );
  await expect(page.getByRole("heading", { name: /Consent and access history/i })).toBeVisible();
  await expect(page.getByText(/record\/analyze/i)).toBeVisible();
  await expect(page.getByText(/storage\/repair/i)).toBeVisible();
  await expect(page.getByText(/wallet:\/\/wallet-demo\/records\/rec-benefits-letter/i).first()).toBeVisible();
  await expect(page.getByText(/grant-analysis/i)).toBeVisible();
});

test("recipient access requires multi-sig approval before decrypt sharing", async ({ page }) => {
  await page.goto("/#/recipient-access");
  const request = page.locator(".access-request-item").filter({ hasText: "Downtown Outreach" });
  const preview = request.getByLabel(/Downtown Outreach access capability preview/i);
  await expect(preview.getByText(/record\/decrypt/i)).toBeVisible();
  await expect(preview.getByText(/approval pending/i)).toBeVisible();
  await expect(preview.getByText(/analytics query/i)).toBeVisible();
  await expect(request.getByText(/1\/2 approvals/i)).toBeVisible();
  await expect(request.getByRole("button", { name: /^Approve$/i })).toBeDisabled();
  await request.getByRole("button", { name: /Record approval/i }).click();
  await expect(preview.getByText(/approval ready/i)).toBeVisible();
  await expect(request.getByText(/2\/2 approvals/i)).toBeVisible();
  await request.getByRole("button", { name: /^Approve$/i }).click();
  await expect(request.getByText("approved", { exact: true })).toBeVisible();
  const receipt = page.getByRole("article", { name: /Downtown Outreach/i }).filter({ hasText: "Receipt hash" });
  const receiptPreview = receipt.getByLabel(/Downtown Outreach receipt capability preview/i);
  await expect(receipt.locator(".badge-row").getByText(/record\/decrypt/i)).toBeVisible();
  await expect(receipt.locator(":scope > .scope-header").getByText("active", { exact: true })).toBeVisible();
  await expect(receiptPreview.getByText(/currently active/i)).toBeVisible();
  await expect(receiptPreview.getByText(/full wallet export/i)).toBeVisible();
});

test("recipient access can revoke an active grant", async ({ page }) => {
  await page.goto("/#/recipient-access");
  const request = page.locator(".access-request-item").filter({ hasText: "Legal Aid desk" });
  await expect(request.getByText(/active grant/i)).toBeVisible();
  await request.getByRole("button", { name: /Revoke/i }).click();
  await expect(request.getByText("revoked", { exact: true })).toBeVisible();
  await expect(request.getByRole("button", { name: /Revoke/i })).toHaveCount(0);
  const receipt = page.getByRole("article", { name: /Legal Aid desk/i }).filter({ hasText: "Receipt hash" });
  await expect(receipt.locator(":scope > .scope-header").getByText("revoked", { exact: true })).toBeVisible();
  await expect(receipt.getByLabel(/Legal Aid desk receipt capability preview/i).getByText(/revoked/i)).toBeVisible();
});
