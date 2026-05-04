import { expect, test } from "@playwright/test";

const walletApiBaseUrl = encodeURIComponent(`http://127.0.0.1:${process.env.PLAYWRIGHT_PORT ?? 5174}`);

function walletRoute(route: string, actorDid: string) {
  return `/?walletApiBaseUrl=${walletApiBaseUrl}&walletId=wallet-demo&actorDid=${encodeURIComponent(actorDid)}#/${route}`;
}

test("mobile home exposes the two required primary cards", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /Your safety plan/i })).toBeVisible({ timeout: 10000 });
  const overviewActions = page.locator(".home-actions .action-card");
  await expect(overviewActions).toHaveCount(2);
  await expect(overviewActions.filter({ hasText: "Contacts" })).toBeVisible();
  await expect(overviewActions.filter({ hasText: "Sharing" })).toBeVisible();
  await expect(overviewActions.filter({ hasText: /Check in/i })).toHaveCount(0);
  const quickCheckIn = page.locator(".checkin-panel");
  const checkInNowIsLargest = await quickCheckIn.evaluate((panel) => {
    const cta = panel.querySelector(".checkin-panel-cta");
    const label = panel.querySelector(".checkin-panel-label");
    const value = panel.querySelector(".checkin-panel-value");
    if (!cta || !label || !value) return false;
    const ctaSize = parseFloat(window.getComputedStyle(cta).fontSize);
    const labelSize = parseFloat(window.getComputedStyle(label).fontSize);
    const valueSize = parseFloat(window.getComputedStyle(value).fontSize);
    return ctaSize > labelSize && ctaSize > valueSize;
  });
  expect(checkInNowIsLargest).toBe(true);
  await quickCheckIn.click();
  await expect(page.getByRole("heading", { name: /Set your schedule/i })).toBeVisible();
});

test("registration enforces minimum required profile fields", async ({ page }) => {
  await page.goto("/#/register");
  await expect(page.getByRole("heading", { name: /Create your Abby profile/i })).toBeVisible({ timeout: 10000 });
  await expect(page.getByLabel(/Legal or full name/i)).toBeVisible();
  await expect(page.getByLabel(/Birth date/i)).toBeVisible();
  const photoOrPhotoId = page.getByLabel(/Photo or photo ID/i);
  await expect(photoOrPhotoId).toBeVisible();
  await expect(photoOrPhotoId).toHaveAttribute("accept", /pdf/i);
  expect(await photoOrPhotoId.getAttribute("capture")).toBeNull();
  await expect(page.getByPlaceholder(/call me she\/her, he\/him, they\/them/i)).toBeVisible();
  await expect(page.getByText("Used for text reminders.", { exact: true })).toBeVisible();
  await expect(page.getByText("Used for email reminders.", { exact: true })).toBeVisible();
  const helperStyles = await page
    .locator(".field")
    .filter({ hasText: /Used for (text|email) reminders/ })
    .evaluateAll((fields) =>
      fields.map((field) => {
        const title = field.querySelector(".field-title");
        const helper = field.querySelector(".field-help-text");
        if (!title || !helper) return false;
        const titleSize = parseFloat(window.getComputedStyle(title).fontSize);
        const helperSize = parseFloat(window.getComputedStyle(helper).fontSize);
        return helperSize >= 15 && helperSize < titleSize;
      })
    );
  expect(helperStyles).toEqual([true, true]);
  await photoOrPhotoId.setInputFiles({
    name: "id-card.gif",
    mimeType: "image/gif",
    buffer: Buffer.from("not accepted")
  });
  await expect(page.getByText(/We can't use this file/i)).toBeVisible();
  await expect(page.getByText(/Selected file: id-card\.gif/i)).toHaveCount(0);
  await page.waitForFunction(() => {
    const state = JSON.parse(window.localStorage.getItem("abby-ui-state-v1") ?? "{}");
    return state.profile?.photoAssetId === "";
  });
  await photoOrPhotoId.setInputFiles({
    name: "id-card.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-1.4\n")
  });
  await expect(page.getByText(/Selected file: id-card\.pdf \(PDF\)/i)).toBeVisible();
  await photoOrPhotoId.setInputFiles({
    name: "id-card.jpg",
    mimeType: "image/jpeg",
    buffer: Buffer.from("jpeg")
  });
  await expect(page.getByText(/Selected file: id-card\.jpg \(JPG\)/i)).toBeVisible();
  await expect(page.locator(".photo-preview-card, .photo-preview-toggle")).toHaveCount(0);
  await expect(page.locator(".field").filter({ hasText: "Photo or photo ID" }).locator("img, object, embed, canvas")).toHaveCount(0);
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
  await expect(page.getByRole("heading", { name: /Set your schedule/i })).toBeVisible({ timeout: 10000 });
  await expect(page.getByRole("button", { name: /Texting allowed/i })).toBeVisible();
  await expect(page.getByRole("button", { name: /Email allowed/i })).toBeVisible();
  await expect(page.getByRole("button", { name: /Web allowed/i })).toBeVisible();
  await expect(page.getByText(/check in by text, email, or web/i)).toBeVisible();
  const interval = page.getByLabel(/Days between check-ins/i);
  await interval.fill("45");
  await expect(interval).toHaveValue("30");
  await page.getByRole("button", { name: /Check in by text/i }).click();
  await expect(page.getByText(/Add a phone number/i)).toBeVisible();
  await page.getByRole("button", { name: /Email allowed/i }).click();
  await page.getByRole("button", { name: /Check in by email/i }).click();
  await expect(page.getByText(/Add an email/i)).toBeVisible();
  await page.getByRole("button", { name: /Check in by web/i }).click();
  await expect(page.getByText(/Checked in by web/i)).toBeVisible();
  await page.getByRole("button", { name: /Web allowed/i }).click();
  await page.getByRole("button", { name: /Check in by web/i }).click();
  await expect(page.getByText(/Web check-in is off/i)).toBeVisible();
  await page.reload();
  await expect(page.getByRole("heading", { name: /Set your schedule/i })).toBeVisible({ timeout: 10000 });
  await expect(page.getByRole("button", { name: /Web allowed/i })).toHaveAttribute("aria-pressed", "false");
  await page.getByRole("button", { name: /Texting allowed/i }).click();
  await page.getByRole("button", { name: /Email allowed/i }).click();
  await expect(page.getByText(/No check-in method is on/i)).toBeVisible();
  await expect(page.getByRole("button", { name: /Check in by text \(off\)/i })).toBeVisible();
  await expect(page.getByRole("button", { name: /Check in by email \(off\)/i })).toBeVisible();
  await page.getByRole("button", { name: /Texting allowed/i }).click();
  await page.getByRole("button", { name: /Email allowed/i }).click();

  await page.goto("/#/register");
  await page.getByLabel(/Phone/i).fill("(503) 555-0199");
  await page.getByLabel(/Email/i).fill("abby-checkin@example.org");
  await page.goto("/#/check-in");
  await expect(page.getByRole("heading", { name: /Set your schedule/i })).toBeVisible({ timeout: 10000 });
  await page.getByRole("button", { name: /Check in by text/i }).click();
  await expect(page.getByText(/Checked in by text/i)).toBeVisible();
  await page.getByRole("button", { name: /Check in by email/i }).click();
  await expect(page.getByText(/Checked in by email/i)).toBeVisible();
});

test("hash navigation updates the active screen without a full reload", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /Your safety plan/i })).toBeVisible();
  await page.evaluate(() => {
    window.location.hash = "#/contacts";
  });
  await expect(page.getByRole("heading", { name: /People who can help/i })).toBeVisible();
  await page.evaluate(() => {
    window.location.hash = "#/analytics";
  });
  await expect(page.getByRole("heading", { name: /Share group facts/i })).toBeVisible();
});

test("mobile menu opens navigation and routes to contacts", async ({ page }, testInfo) => {
  test.skip(!/Mobile/i.test(testInfo.project.name), "Mobile navigation is hidden on desktop layouts");
  await page.goto("/");
  await page.getByRole("button", { name: /Open menu/i }).click();
  const mobileNav = page.getByRole("navigation", { name: /Mobile navigation/i });
  await expect(mobileNav).toBeVisible();
  await mobileNav.getByRole("button", { name: /Contacts/i }).click();
  await expect(page.getByRole("heading", { name: /People who can help/i })).toBeVisible();
  await expect(mobileNav).not.toBeVisible();
});

test("analytics consent shows privacy controls and safe details", async ({ page }) => {
  await page.goto("/#/analytics");
  await expect(page.getByRole("heading", { name: /Share group facts/i })).toBeVisible();
  const housingStudy = page.getByRole("article", { name: /Housing service gaps/i });
  await expect(housingStudy.getByLabel(/Allow this choice/i)).toBeChecked();
  await expect(housingStudy.locator(".privacy-metrics").getByText(/Group size/i)).toBeVisible();
  await expect(housingStudy.locator(".privacy-metrics").getByText(/Privacy left/i)).toBeVisible();
  await expect(housingStudy.getByText("county", { exact: true })).toBeVisible();
  await expect(housingStudy.getByText("need type", { exact: true })).toBeVisible();
  await expect(housingStudy.getByText("need_category", { exact: true })).toHaveCount(0);
  const preview = housingStudy.getByLabel(/Housing service gaps analytics capability preview/i);
  await expect(preview.getByText(/share group facts/i)).toBeVisible();
  await expect(preview.getByText(/open file contents/i)).toBeVisible();
  await expect(preview.getByText(/ask group questions/i)).toBeVisible();
});

test("analytics consent preserves opt-out after refresh", async ({ page }) => {
  await page.goto("/#/analytics");
  const housingStudy = page.getByRole("article", { name: /Housing service gaps/i });
  const studyOptIn = housingStudy.getByLabel(/Allow this choice/i);
  await studyOptIn.uncheck();
  await expect(studyOptIn).not.toBeChecked();
  await page.reload();
  const reloadedStudy = page.getByRole("article", { name: /Housing service gaps/i });
  await expect(reloadedStudy.getByLabel(/Allow this choice/i)).not.toBeChecked();
});

test("benefits opt-in previews notification capability boundaries", async ({ page }) => {
  await page.goto("/#/benefits-protection");
  await expect(page.getByRole("heading", { name: /Benefits notice/i })).toBeVisible();
  await expect(page.getByLabel(/Allow Abby to prepare/i)).toBeChecked();
  const preview = page.getByLabel(/Benefits notification capability preview/i);
  await expect(preview.getByText(/read basic info/i)).toBeVisible();
  await expect(preview.getByText(/read safe facts/i)).toBeVisible();
  await expect(preview.getByText(/read exact location/i)).toBeVisible();
  await expect(preview.getByText(/make a full wallet export/i)).toBeVisible();
});

test("benefits opt-in preserves opt-out after refresh", async ({ page }) => {
  await page.goto("/#/benefits-protection");
  await expect(page.getByRole("heading", { name: /Benefits notice/i })).toBeVisible({ timeout: 10000 });
  const optIn = page.getByLabel(/Allow Abby to prepare/i);
  await expect(optIn).toBeChecked();
  await optIn.uncheck();
  await expect(optIn).not.toBeChecked();
  await page.reload();
  await page.goto("/#/benefits-protection");
  await expect(page.getByRole("heading", { name: /Benefits notice/i })).toBeVisible({ timeout: 10000 });
  await expect(page.getByLabel(/Allow Abby to prepare/i)).not.toBeChecked();
});

test("sharing rules preview scope-derived capabilities", async ({ page }) => {
  await page.goto("/#/sharing-rules");
  await expect(page.getByRole("heading", { name: /Choose what each person can see/i })).toBeVisible();
  const preview = page.getByLabel(/Maya Johnson sharing capability preview/i);
  await expect(preview.getByText(/read general location/i)).toBeVisible();
  await expect(preview.getByText(/open file contents/i)).toBeVisible();
  await expect(preview.getByText(/make a full wallet export/i)).toBeVisible();
});

test("sharing rules default on and preserve unchecked scopes after refresh", async ({ page }) => {
  await page.goto("/#/sharing-rules");
  await expect(page.getByRole("heading", { name: /Choose what each person can see/i })).toBeVisible();
  const recipient = page.locator(".scope-editor").filter({ hasText: "Maya Johnson" });
  await expect(recipient).toBeVisible();
  const scopes = recipient.locator(".scope-option input");
  await expect(scopes).toHaveCount(11);
  expect(await scopes.evaluateAll((inputs) => inputs.every((input) => (input as HTMLInputElement).checked))).toBe(true);

  await recipient.getByLabel(/Medical notes/i).uncheck();
  await recipient.getByLabel(/Found permanent housing/i).uncheck();
  await expect(recipient.getByLabel(/Medical notes/i)).not.toBeChecked();
  await expect(recipient.getByLabel(/Found permanent housing/i)).not.toBeChecked();
  await page.reload();

  const reloadedRecipient = page.locator(".scope-editor").filter({ hasText: "Maya Johnson" });
  await expect(reloadedRecipient.getByLabel(/Medical notes/i)).not.toBeChecked();
  await expect(reloadedRecipient.getByLabel(/Found permanent housing/i)).not.toBeChecked();
  await expect(reloadedRecipient.getByLabel(/Minimum identity/i)).toBeChecked();
});

test("contact list shelter nudge requires user approval before adding contact", async ({ page }) => {
  await page.goto("/#/contacts");
  const addRecipientSection = page.locator('section[aria-labelledby="Add-person-or-group"]');
  await expect(addRecipientSection.locator(".centered-action").getByRole("button", { name: /Add person or group/i })).toBeVisible();
  expect(await addRecipientSection.locator(".centered-action").evaluate((node) => getComputedStyle(node).justifyContent)).toBe("center");
  await expect(addRecipientSection.locator('option[value="benefits_agency"]')).toHaveText("Benefits agency");
  const nudge = page.locator(".access-request-item").filter({ hasText: "Downtown Outreach Shelter" });
  await expect(nudge.getByText(/asked to be added to your contacts/i)).toBeVisible();
  await expect(nudge.getByRole("button", { name: /^Approve$/i })).toBeVisible();
  await expect(nudge.getByRole("button", { name: /^Deny$/i })).toBeVisible();
  await nudge.getByRole("button", { name: /^Approve$/i }).click();
  await expect(page.locator(".recipient-list-item").filter({ hasText: "Downtown Outreach Shelter" })).toBeVisible();

  await page.evaluate(() => {
    window.location.hash = "#/sharing-rules";
  });
  const shelterRules = page.locator(".scope-editor").filter({ hasText: "Downtown Outreach Shelter" });
  await expect(shelterRules.getByText("1 selected", { exact: true })).toBeVisible();
});

test("user can request a shelter contact and shelter staff can approve it", async ({ page }) => {
  await page.goto("/#/contacts");
  await expect(page.getByRole("heading", { name: /People who can help/i })).toBeVisible({ timeout: 10000 });
  const shelterRequests = page.locator('section[aria-labelledby="Shelter-requests"]');
  await expect(shelterRequests.getByRole("button", { name: /Ask to add shelter/i })).toBeDisabled();
  await expect(shelterRequests.getByText(/already waiting/i)).toBeVisible();
  await shelterRequests.locator("select").selectOption("Downtown Outreach Shelter");
  await expect(shelterRequests.getByRole("button", { name: /Ask to add shelter/i })).toBeDisabled();
  await shelterRequests.locator("select").selectOption("Harbor Night Shelter");
  await expect(shelterRequests.getByRole("button", { name: /Ask to add shelter/i })).toBeEnabled();
  await shelterRequests.getByRole("button", { name: /Ask to add shelter/i }).click();
  await expect(page.locator(".list-item").filter({ hasText: "Harbor Night Shelter" }).getByText(/pending/i)).toBeVisible();

  await page.evaluate(() => {
    window.location.hash = "#/shelter";
  });
  await page.getByLabel("Shelter").first().selectOption("Harbor Night Shelter");
  await page.getByLabel(/Verified staff operator/i).selectOption({ label: "Riley Chen" });
  const request = page.locator(".access-request-item").filter({ hasText: "Harbor Night Shelter" }).filter({ hasText: "User asked" });
  await request.getByRole("button", { name: /^Approve$/i }).click();
  await expect(request.getByText(/approved/i)).toBeVisible();
  await page.evaluate(() => {
    window.location.hash = "#/contacts";
  });
  await expect(page.locator(".recipient-list-item").filter({ hasText: "Harbor Night Shelter" })).toBeVisible();
});

test("user can cancel a pending shelter contact request", async ({ page }) => {
  await page.goto("/#/contacts");
  const shelterRequests = page.locator('section[aria-labelledby="Shelter-requests"]');
  await shelterRequests.locator("select").selectOption("Harbor Night Shelter");
  await shelterRequests.getByRole("button", { name: /Ask to add shelter/i }).click();
  const request = page.locator(".list-item").filter({ hasText: "Harbor Night Shelter" }).filter({ hasText: "You asked this shelter." });
  await expect(request.getByText(/pending/i)).toBeVisible();
  await expect(shelterRequests.getByRole("button", { name: /Ask to add shelter/i })).toBeDisabled();
  await request.getByRole("button", { name: /^Cancel$/i }).click();
  await expect(request.getByText(/canceled/i)).toBeVisible();
  await expect(shelterRequests.getByRole("button", { name: /Ask to add shelter/i })).toBeEnabled();
});

test("verified shelter staff can send a contact-list nudge", async ({ page }) => {
  await page.goto("/#/shelter");
  await page.getByLabel("Shelter").first().selectOption("Rose City Shelter");
  await page.getByLabel(/Verified staff operator/i).selectOption({ label: "Avery Patel" });
  await expect(page.getByRole("button", { name: /Send contact request/i })).toBeDisabled();
  await expect(page.getByText(/already waiting/i)).toBeVisible();
  const createUser = page.locator('section[aria-labelledby="Create-user-account"]');
  await expect(createUser.getByPlaceholder(/call me she\/her, he\/him, they\/them/i)).toBeVisible();
  await expect(createUser.getByText("Used for text reminders.", { exact: true })).toBeVisible();
  await expect(createUser.getByText("Used for email reminders.", { exact: true })).toBeVisible();
  const staffHelperStyles = await createUser
    .locator(".field")
    .filter({ hasText: /Used for (text|email) reminders/ })
    .evaluateAll((fields) =>
      fields.map((field) => {
        const title = field.querySelector(".field-title");
        const helper = field.querySelector(".field-help-text");
        if (!title || !helper) return false;
        const titleSize = parseFloat(window.getComputedStyle(title).fontSize);
        const helperSize = parseFloat(window.getComputedStyle(helper).fontSize);
        return helperSize >= 15 && helperSize < titleSize;
      })
    );
  expect(staffHelperStyles).toEqual([true, true]);
  const staffPhotoOrPhotoId = createUser.getByLabel(/Photo or photo ID/i);
  await expect(staffPhotoOrPhotoId).toHaveAttribute("accept", /pdf/i);
  expect(await staffPhotoOrPhotoId.getAttribute("capture")).toBeNull();
  await staffPhotoOrPhotoId.setInputFiles({
    name: "client-id.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("not accepted")
  });
  await expect(createUser.getByText(/We can't use this file/i)).toBeVisible();
  await expect(createUser.getByText(/Selected file: client-id\.txt/i)).toHaveCount(0);
  await staffPhotoOrPhotoId.setInputFiles({
    name: "client-id.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-1.4\n")
  });
  await expect(createUser.getByText(/Selected file: client-id\.pdf \(PDF\)/i)).toBeVisible();
  await expect(createUser.locator("img, object, embed, canvas")).toHaveCount(0);
  await page.getByLabel(/Person name/i).fill("Casey Example");
  await page.getByLabel(/Phone or email/i).fill("casey@example.org");
  await page.getByRole("button", { name: /Send contact request/i }).click();
  const nudge = page.locator(".access-request-item").filter({ hasText: "Casey Example" });
  await expect(nudge.getByText(/Shelter asked this user/i)).toBeVisible();
  await expect(nudge.getByText(/pending/i)).toBeVisible();
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

  await page.goto(walletRoute("proof-center", "did:key:owner"));
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
  const benefitsExport = page.getByRole("article", { name: /Benefits help clinic/i });
  await expect(benefitsExport.getByText(/storage missing/i)).toBeVisible();
});

test("security screen saves and restores wallet snapshots", async ({ page }) => {
  let saved = false;
  let saveRequests = 0;
  let loadRequests = 0;
  await page.route("**/wallets/**", async (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname;
    if (path === "/wallets/snapshots") {
      await route.fulfill({ json: { wallet_ids: saved ? ["wallet-demo"] : [] } });
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
  await page.goto(walletRoute("security", "did:key:owner"));

  await expect(page.getByRole("heading", { name: /Account safety/i })).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText(/no backup/i)).toBeVisible();
  await page.getByRole("button", { name: /Save backup/i }).click();
  await expect(page.getByText(/Wallet backup saved/i)).toBeVisible();
  await expect(page.getByText(/backup ready/i)).toBeVisible();
  await expect(page.getByText(/verified/i)).toBeVisible();
  await expect(page.getByText(/abc123def456/i)).toBeVisible();
  await page.getByRole("button", { name: /Load backup/i }).click();
  await expect(page.getByText(/Wallet backup loaded/i)).toBeVisible();
  expect(saveRequests).toBe(1);
  expect(loadRequests).toBe(1);
});

test("uploads can repair API-backed document storage", async ({ page }) => {
  let repairRequests = 0;
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
  await page.goto(walletRoute("uploads", "did:key:owner"));
  const upload = page.locator(".upload-list-item").filter({ hasText: "Benefits letter" });
  await expect(upload.getByText(/save needs fix/i)).toBeVisible();
  await expect(upload.getByText(/^high$/i)).not.toBeVisible();
  await upload.getByRole("button", { name: /Fix save/i }).click();
  await expect(upload.getByText(/^saved$/i)).toBeVisible();
  await expect(upload.getByRole("button", { name: /Fix save/i })).toHaveCount(0);
  await page.evaluate(() => {
    window.location.hash = "#/audit";
  });
  await expect(page.getByText(/storage\/repair/i)).toBeVisible();
  await expect(page.getByText(/wallet:\/\/wallet-demo\/records\/rec-benefits-letter/i)).toBeVisible();
  expect(repairRequests).toBe(1);
});

test("recipient receipt can create an encrypted derived analysis artifact", async ({ page }) => {
  test.setTimeout(60_000);
  let analysisRequests = 0;
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
          receipts: [
            {
              receipt_id: "receipt-analysis",
              grant_id: "grant-analysis",
              audience_did: "did:key:delegate",
              resources: ["wallet://wallet-demo/records/rec-benefits-letter"],
              abilities: ["record/analyze"],
              purpose: "service_matching",
              receipt_hash: "receipt-hash-analysis",
              status: "active",
              created_at: "2026-05-03T18:00:00Z"
            }
          ]
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
    if (path.endsWith("/audit")) {
      await route.fulfill({ json: { events: auditEvents } });
      return;
    }
    await route.fulfill({ status: 404, json: { error: "unexpected wallet API call" } });
  });

  await page.goto(walletRoute("recipient-access", "did:key:delegate"));
  const receipt = page.getByRole("article", { name: /delegate/i }).filter({ hasText: "Share proof code" });
  await expect(receipt).toBeVisible({ timeout: 15_000 });
  const analyzeButton = receipt.getByRole("button", { name: /Make safe summary/i });
  await expect(analyzeButton).toBeVisible({ timeout: 15_000 });
  await analyzeButton.scrollIntoViewIfNeeded();
  await analyzeButton.click();
  await expect(receipt.getByText(/summary · derived_only/i)).toBeVisible();
  await expect(receipt.getByText(/mem:\/\/derived-artifact/i)).toBeVisible();
  await expect(receipt.getByText(/rec-benefits-letter/i)).toBeVisible();
  await page.evaluate(() => {
    window.location.hash = "#/audit";
  });
  await expect(page.getByRole("heading", { name: /Consent and access history/i })).toBeVisible();
  await expect(page.getByText(/record\/analyze/i).first()).toBeVisible();
  await expect(page.getByText(/grant-analysis/i)).toBeVisible();
  expect(analysisRequests).toBe(1);
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

  await page.goto(walletRoute("audit", "did:key:owner"));
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
  await expect(preview.getByText(/open file contents/i)).toBeVisible();
  await expect(preview.getByText(/approval pending/i)).toBeVisible();
  await expect(preview.getByText(/ask group questions/i)).toBeVisible();
  await expect(request.getByText(/1\/2 approvals/i)).toBeVisible();
  await expect(request.getByRole("button", { name: /^Approve$/i })).toBeDisabled();
  await request.getByRole("button", { name: /Record approval/i }).click();
  await expect(preview.getByText(/approval ready/i)).toBeVisible();
  await expect(request.getByText(/2\/2 approvals/i)).toBeVisible();
  await request.getByRole("button", { name: /^Approve$/i }).click();
  await expect(request.getByText("approved", { exact: true })).toBeVisible();
  const receipt = page.getByRole("article", { name: /Downtown Outreach/i }).filter({ hasText: "Share proof code" });
  const receiptPreview = receipt.getByLabel(/Downtown Outreach receipt capability preview/i);
  await expect(receipt.locator(".badge-row").getByText(/open file contents/i)).toBeVisible();
  await expect(receipt.locator(":scope > .scope-header").getByText("active", { exact: true })).toBeVisible();
  await expect(receiptPreview.getByText(/currently active/i)).toBeVisible();
  await expect(receiptPreview.getByText(/make a full wallet export/i)).toBeVisible();
});

test("recipient access can revoke an active grant", async ({ page }) => {
  await page.goto("/#/recipient-access");
  const request = page.locator(".access-request-item").filter({ hasText: "Legal Aid desk" });
  await expect(request.getByText(/active grant/i)).toBeVisible();
  await request.getByRole("button", { name: /Revoke/i }).click();
  await expect(request.getByText("revoked", { exact: true })).toBeVisible();
  await expect(request.getByRole("button", { name: /Revoke/i })).toHaveCount(0);
  const receipt = page.getByRole("article", { name: /Legal Aid desk/i }).filter({ hasText: "Share proof code" });
  await expect(receipt.locator(":scope > .scope-header").getByText("revoked", { exact: true })).toBeVisible();
  await expect(receipt.getByLabel(/Legal Aid desk receipt capability preview/i).getByText(/revoked/i)).toBeVisible();
});
