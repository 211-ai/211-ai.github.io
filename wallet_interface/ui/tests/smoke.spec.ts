import { expect, test, type Locator, type Page, type Route } from "@playwright/test";

const walletApiBaseUrl = encodeURIComponent(`http://127.0.0.1:${process.env.PLAYWRIGHT_PORT ?? 5174}`);
const appSessionKey = "abby-ui-session-v1";
const appPersistKey = "abby-ui-state-v1";

function walletRoute(route: string, actorDid: string, params: Record<string, string> = {}) {
  const query = new URLSearchParams({
    walletApiBaseUrl: decodeURIComponent(walletApiBaseUrl),
    walletId: "wallet-demo",
    actorDid,
    ...params
  });
  return `/?${query.toString()}#/${route}`;
}

async function expectLoginForm(page: Page) {
  await expect(page.locator(".login-page")).toBeVisible({ timeout: 10000 });
  await expect(page.getByRole("group", { name: /Choose portal/i })).toBeVisible();
  await expect(page.getByRole("button", { name: /^Client$/i })).toBeVisible();
  await expect(page.getByRole("button", { name: /Service provider/i })).toBeVisible();
  await expect(page.getByLabel(/Email address or telephone/i)).toBeVisible();
}

async function signInIfNeeded(page: Page) {
  const contact = page.getByLabel(/Email address or telephone/i).first();

  try {
    await contact.waitFor({ state: "visible", timeout: 1000 });
  } catch {
    return false;
  }

  await page.getByRole("button", { name: /^Client$/i }).click();
  await contact.fill("abby@example.org");
  await page.getByRole("button", { name: /Send code or magic link/i }).click();
  const oneTimePad = (await page.locator('code[aria-label="Generated one-time pad code"]').innerText()).trim();
  await page.getByRole("textbox", { name: /One-time pad number/i }).fill(oneTimePad);
  await page.getByRole("button", { name: /Verify code/i }).click();
  return true;
}

async function openAppRoute(page: Page, route: string) {
  await page.goto("/");
  const signedIn = await signInIfNeeded(page);

  if (signedIn && route !== "/") {
    await page.goto(route);
    await signInIfNeeded(page);
    return;
  }

  if (route !== "/") {
    await page.goto(route);
    await signInIfNeeded(page);
  }
}

async function expectFirstAboveSecond(first: Locator, second: Locator) {
  const firstBox = await first.boundingBox();
  const secondBox = await second.boundingBox();
  expect(firstBox, "expected first element to have a layout box").not.toBeNull();
  expect(secondBox, "expected second element to have a layout box").not.toBeNull();
  expect(firstBox!.y).toBeLessThan(secondBox!.y);
}

test("login page appears before the home screen", async ({ page }) => {
  await page.goto("/");
  await expectLoginForm(page);
  await signInIfNeeded(page);
  await expect(page.getByRole("heading", { name: /Welcome to your safety plan!/i })).toBeVisible({ timeout: 10000 });
});

test("mobile home exposes the safety plan heading and quick check-in action", async ({ page }) => {
  await openAppRoute(page, "/");
  await expect(page.getByRole("heading", { name: /Welcome to your safety plan!/i })).toBeVisible({ timeout: 10000 });
  await expect(page.locator(".home-actions")).toHaveCount(0);
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
  await openAppRoute(page, "/#/register");
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
  await page.getByLabel(/Legal or full name/i).fill("Abby Example");
  await page.getByLabel(/Birth date/i).fill("1990-01-01");
  await expect(page.locator('section[aria-labelledby="Government-help"]')).toBeVisible();
  await expect(page.getByRole("heading", { name: /^Government help$/i })).toBeVisible();
  await expect(page.getByRole("button", { name: /^Start request$/i })).toBeVisible();
  await expect(page.locator(".screen .captcha-box")).toHaveCount(0);
  await expect(page.locator(".screen .consent-box")).toHaveCount(0);

  await page.getByRole("button", { name: /^Start request$/i }).click();
  await expect(page.getByRole("button", { name: /^Clear request$/i })).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByText(/This account is flagged for service partners/i)).toBeVisible();
  await expect(page.getByText("Help requested", { exact: true })).toBeVisible();
  await page.waitForFunction(() => {
    const state = JSON.parse(window.localStorage.getItem("abby-ui-state-v1") ?? "{}");
    return state.profile?.servicePartnerHelpRequested === true && Boolean(state.profile?.servicePartnerHelpRequestedAt);
  });
  await page.goto("/#/shelter");
  await expect(page.locator("h1", { hasText: /Provider overview/i })).toBeVisible({ timeout: 10000 });
  const partnerRequests = page.getByRole("region", { name: /Partner help requests/i });
  await expect(partnerRequests).toBeVisible();
  await expect(partnerRequests.getByText(/Needs partner help/i)).toBeVisible();
});

test("client settings edits profile and less-used preferences", async ({ page }, testInfo) => {
  await openAppRoute(page, "/#/settings");
  await expect(page.getByRole("heading", { name: /^Settings$/i })).toBeVisible({ timeout: 10000 });
  await expect(page.getByLabel(/Legal or full name/i)).toBeVisible();
  await expect(page.getByLabel(/Birth date/i)).toBeVisible();
  await expect(page.getByLabel(/Photo or photo ID/i)).toBeVisible();
  await expect(page.locator('section[aria-labelledby="Government-help"]')).toBeVisible();
  await expect(page.getByLabel(/Days between check-ins/i)).toBeVisible();
  await expect(page.getByLabel(/Allow Abby to prepare benefits notices/i)).toBeVisible();
  await expect(page.getByLabel(/Housing service gaps/i)).toBeVisible();
  await expect(page.getByRole("button", { name: /Account safety/i })).toBeVisible();

  await page.getByLabel(/Legal or full name/i).fill("Settings User");
  await page.getByLabel(/Days between check-ins/i).fill("12");
  await page.getByLabel(/Allow Abby to prepare benefits notices/i).uncheck();
  await page.getByLabel(/Housing service gaps/i).uncheck();
  await expect(page.getByLabel(/Days between check-ins/i)).toHaveValue("12");

  await page.reload();
  await expect(page.getByRole("heading", { name: /^Settings$/i })).toBeVisible({ timeout: 10000 });
  await expect(page.getByLabel(/Legal or full name/i)).toHaveValue("Settings User");
  await expect(page.getByLabel(/Days between check-ins/i)).toHaveValue("12");
  await expect(page.getByLabel(/Allow Abby to prepare benefits notices/i)).not.toBeChecked();
  await expect(page.getByLabel(/Housing service gaps/i)).not.toBeChecked();

  if (!/Mobile/i.test(testInfo.project.name)) {
    const nav = page.getByRole("navigation", { name: /Portal navigation/i });
    await expect(nav.getByRole("button", { name: /^Register$/i })).toHaveCount(0);
    await expect(nav.getByRole("button", { name: /^Settings$/i })).toBeVisible();
    await expectFirstAboveSecond(
      nav.getByRole("button", { name: /^Wallet$/i }),
      nav.getByRole("button", { name: /^Settings$/i })
    );
  }
});

test("check-in interval cannot exceed thirty days", async ({ page }) => {
  await openAppRoute(page, "/#/check-in");
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

  await openAppRoute(page, "/#/register");
  await page.getByLabel(/Phone/i).fill("(503) 555-0199");
  await page.getByLabel(/Email/i).fill("abby-checkin@example.org");
  await openAppRoute(page, "/#/check-in");
  await expect(page.getByRole("heading", { name: /Set your schedule/i })).toBeVisible({ timeout: 10000 });
  await page.getByRole("button", { name: /Check in by text/i }).click();
  await expect(page.getByText(/Checked in by text/i)).toBeVisible();
  await page.getByRole("button", { name: /Check in by email/i }).click();
  await expect(page.getByText(/Checked in by email/i)).toBeVisible();
});

test("calendar collects service appointments and follow-ups", async ({ page }) => {
  const now = Date.now();
  const appointmentAt = new Date(now + 36 * 60 * 60 * 1000).toISOString();
  const reminderAt = new Date(now + 34 * 60 * 60 * 1000).toISOString();
  const followUpAt = new Date(now + 72 * 60 * 60 * 1000).toISOString();
  const lastCheckInAt = new Date(now).toISOString();

  await page.addInitScript(
    ({ appointmentAt, appPersistKey, appSessionKey, followUpAt, lastCheckInAt, reminderAt }) => {
      window.localStorage.setItem(appSessionKey, JSON.stringify({ username: "calendar-reviewer" }));
      window.localStorage.setItem(
        appPersistKey,
        JSON.stringify({
          policy: {
            intervalDays: 2,
            reminderChannels: ["email", "sms"],
            gracePeriodHours: 12,
            escalationEnabled: true,
            lastCheckInAt
          },
          servicePlans: [
            {
              plan_id: "plan-calendar-test",
              wallet_id: "wallet-demo",
              service_doc_id: "svc-food-pantry-1",
              source_content_cid: "cid-food",
              source_page_cid: "page-food",
              service_title: "Food pantry intake",
              provider_name: "Neighborhood Food Pantry",
              goal: "Attend pantry appointment",
              steps: ["Bring photo ID"],
              documents_needed: ["Photo ID"],
              questions_to_ask: ["What should I bring next time?"],
              appointment_at: appointmentAt,
              reminder_at: reminderAt,
              travel_target: "Bus 12 to 4th Ave",
              assigned_worker_recipient_id: "",
              status: "active",
              related_interaction_ids: [],
              private_notes_record_id: "",
              created_at: lastCheckInAt,
              updated_at: lastCheckInAt
            }
          ],
          serviceInteractions: [
            {
              interaction_id: "int-follow-up-test",
              wallet_id: "wallet-demo",
              service_doc_id: "svc-clinic-1",
              source_content_cid: "cid-clinic",
              source_page_cid: "page-clinic",
              provider_name: "Health Clinic",
              program_name: "Clinic intake",
              interaction_type: "appointment_scheduled",
              channel: "phone",
              actor_did: "did:example:user",
              counterparty_name: "Clinic desk",
              counterparty_contact: "503-555-0100",
              timestamp: lastCheckInAt,
              status: "active",
              outcome: "Call confirmed",
              notes_record_id: "",
              next_action: "Bring paperwork",
              next_follow_up_at: followUpAt,
              source_action_url: "",
              related_grant_ids: [],
              related_record_ids: [],
              privacy_level: "private",
              created_at: lastCheckInAt,
              updated_at: lastCheckInAt,
              metadata: {}
            }
          ]
        })
      );
    },
    { appointmentAt, appPersistKey, appSessionKey, followUpAt, lastCheckInAt, reminderAt }
  );

  await page.goto("/#/calendar");
  await expect(page.getByRole("heading", { name: /^Calendar$/i })).toBeVisible({ timeout: 10000 });
  const foodAppointment = page.getByRole("article").filter({ hasText: /Food pantry intake/i });
  const clinicFollowUp = page.getByRole("article").filter({ hasText: /Bring paperwork/i });
  const checkInReminder = page.getByRole("article").filter({ hasText: /Check in with Abby/i });
  await expect(foodAppointment).toBeVisible();
  await expect(foodAppointment.getByText(/Bus 12 to 4th Ave/i)).toBeVisible();
  await expect(clinicFollowUp).toBeVisible();
  await expect(checkInReminder).toBeVisible();
  await expect(page.getByRole("button", { name: /Open plan/i })).toBeVisible();
  await expect(page.getByRole("button", { name: /Add to calendar/i }).first()).toBeVisible();
});

test("hash navigation updates the active screen without a full reload", async ({ page }) => {
  await openAppRoute(page, "/");
  await expect(page.getByRole("heading", { name: /Welcome to your safety plan!/i })).toBeVisible();
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
  await openAppRoute(page, "/");
  await page.getByRole("button", { name: /Open menu/i }).click();
  const mobileNav = page.getByRole("navigation", { name: /Mobile navigation/i });
  await expect(mobileNav).toBeVisible();
  await expect(mobileNav.getByRole("button", { name: /Sharing/i })).toHaveCount(0);
  await expect(mobileNav.getByRole("button", { name: /Benefits/i })).toHaveCount(0);
  await expect(mobileNav.getByRole("button", { name: /Who can see info/i })).toHaveCount(0);
  await expectFirstAboveSecond(
    mobileNav.getByRole("button", { name: /Services/i }),
    mobileNav.getByRole("button", { name: /Wallet/i })
  );
  await mobileNav.getByRole("button", { name: /Contacts/i }).click();
  await expect(page.getByRole("heading", { name: /People who can help/i })).toBeVisible();
  await expect(mobileNav).not.toBeVisible();
});

test("analytics consent shows privacy controls and safe details", async ({ page }) => {
  await openAppRoute(page, "/#/analytics");
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
  await openAppRoute(page, "/#/analytics");
  const housingStudy = page.getByRole("article", { name: /Housing service gaps/i });
  const studyOptIn = housingStudy.getByLabel(/Allow this choice/i);
  await studyOptIn.uncheck();
  await expect(studyOptIn).not.toBeChecked();
  await page.reload();
  const reloadedStudy = page.getByRole("article", { name: /Housing service gaps/i });
  await expect(reloadedStudy.getByLabel(/Allow this choice/i)).not.toBeChecked();
});

test("removed standalone sharing, benefits, and recipient routes fall back home", async ({ page }) => {
  for (const route of ["/#/sharing-rules", "/#/benefits-protection", "/#/recipient-access"]) {
    await openAppRoute(page, route);
    await expect(page.getByRole("heading", { name: /Welcome to your safety plan!/i })).toBeVisible({ timeout: 10000 });
    await expect(page.getByRole("heading", { name: /Benefits notice|Requests to see my info/i })).toHaveCount(0);
  }
});

test("contacts add flow saves sharing choices and opens edit panel by keyboard", async ({ page }) => {
  await openAppRoute(page, "/#/contacts");
  await expect(page.getByRole("heading", { name: /People who can help/i })).toBeVisible({ timeout: 10000 });
  const addPersonSection = page.getByRole("region", { name: "Add contact" });
  await addPersonSection.getByRole("radio", { name: /^Person$/i }).check();
  await expectFirstAboveSecond(
    addPersonSection.getByLabel(/Type/i),
    addPersonSection.getByText(/Sharing choices for this person/i)
  );
  await addPersonSection.getByLabel(/First name/i).fill("Morgan");
  await addPersonSection.getByLabel(/Last name/i).fill("Caseworker");
  await addPersonSection.getByLabel(/Relationship or role/i).fill("Outreach case worker");
  await addPersonSection.getByLabel("Phone", { exact: true }).fill("(503) 555-0188");
  await addPersonSection.getByLabel("Email", { exact: true }).fill("morgan@example.org");
  await addPersonSection.getByLabel(/Type/i).selectOption("social_worker");
  await addPersonSection.getByLabel(/Medical notes/i).uncheck();
  await addPersonSection.getByLabel(/Found permanent housing/i).uncheck();
  await addPersonSection.getByRole("button", { name: /^Add person$/i }).click();

  const savedContacts = page.locator('section[aria-labelledby="Saved-contacts"]');
  const savedMorgan = savedContacts.locator(".recipient-list-item").filter({ hasText: "Morgan Caseworker" });
  await expect(savedMorgan.getByText("9 items", { exact: true })).toBeVisible();
  await savedMorgan.locator(".recipient-open-button").focus();
  await page.keyboard.press("Enter");
  await expect(savedMorgan.getByRole("region", { name: /Edit sharing for Morgan Caseworker/i })).toHaveCount(0);
  const editPanel = savedContacts.getByRole("region", { name: /Edit sharing for Morgan Caseworker/i });
  await expect(editPanel).toBeVisible();
  await expect(editPanel.getByLabel(/Minimum identity/i)).toBeChecked();
  await expect(editPanel.getByLabel(/Medical notes/i)).not.toBeChecked();
  await expect(editPanel.getByLabel(/Found permanent housing/i)).not.toBeChecked();
  await editPanel.getByLabel(/Benefits information/i).uncheck();
  await editPanel.getByRole("button", { name: /Save sharing/i }).click();

  await page.reload();
  const reloadedMorgan = page.locator('section[aria-labelledby="Saved-contacts"] .recipient-list-item').filter({
    hasText: "Morgan Caseworker"
  });
  await expect(reloadedMorgan.getByText("8 items", { exact: true })).toBeVisible();
  await reloadedMorgan.locator(".recipient-open-button").focus();
  await page.keyboard.press("Space");
  await expect(reloadedMorgan.getByRole("region", { name: /Edit sharing for Morgan Caseworker/i })).toHaveCount(0);
  const reloadedPanel = page
    .locator('section[aria-labelledby="Saved-contacts"]')
    .getByRole("region", { name: /Edit sharing for Morgan Caseworker/i });
  await expect(reloadedPanel.getByLabel(/Benefits information/i)).not.toBeChecked();
});

test("contact list shelter nudge requires user approval before adding contact", async ({ page }) => {
  await openAppRoute(page, "/#/contacts");
  const addContactSection = page.getByRole("region", { name: "Add contact" });
  const savedContacts = page.locator('section[aria-labelledby="Saved-contacts"]');
  await expect(addContactSection).toBeVisible();
  await expect(savedContacts.locator(".recipient-list-item").filter({ hasText: "Maya Johnson" })).toBeVisible();
  await expect(addContactSection.locator(".centered-action").getByRole("button", { name: /^Add person$/i })).toBeVisible();
  expect(await addContactSection.locator(".centered-action").evaluate((node) => getComputedStyle(node).justifyContent)).toBe("center");
  await expect(addContactSection.locator('option[value="benefits_agency"]')).toHaveText("Benefits agency");
  await expect(addContactSection.getByLabel(/Minimum identity/i)).toBeChecked();
  await expect(addContactSection.getByText("name, birthdate and contact status").first()).toBeVisible();
  await addContactSection.getByRole("radio", { name: /Shelter or group/i }).check();
  const nudge = addContactSection.locator(".access-request-item").filter({ hasText: "Downtown Outreach Shelter" });
  await expect(nudge.getByText(/asked to be added to your contacts/i)).toBeVisible();
  await expect(nudge.getByRole("button", { name: /^Approve$/i })).toBeVisible();
  await expect(nudge.getByRole("button", { name: /^Deny$/i })).toBeVisible();
  await nudge.getByRole("button", { name: /^Approve$/i }).click();
  await expect(page.locator(".recipient-list-item").filter({ hasText: "Downtown Outreach Shelter" })).toBeVisible();
  const shelterRules = page.locator(".recipient-list-item").filter({ hasText: "Downtown Outreach Shelter" });
  await expect(shelterRules.getByText("1 items", { exact: true })).toBeVisible();
  await shelterRules.getByRole("button", { name: /^Edit sharing$/i }).click();
  await expect(shelterRules.getByRole("region", { name: /Edit sharing for Downtown Outreach Shelter/i })).toHaveCount(0);
  const shelterPanel = savedContacts.getByRole("region", { name: /Edit sharing for Downtown Outreach Shelter/i });
  await expect(shelterPanel.getByText("1 selected", { exact: true })).toBeVisible();
  await expect(shelterPanel.getByLabel(/Minimum identity/i)).toBeChecked();
  await expect(shelterPanel.getByLabel(/Profile/i)).not.toBeChecked();
});

test("user can request a shelter contact and shelter staff can approve it", async ({ page }) => {
  await openAppRoute(page, "/#/contacts");
  await expect(page.getByRole("heading", { name: /People who can help/i })).toBeVisible({ timeout: 10000 });
  const shelterRequests = page.getByRole("region", { name: "Add contact" });
  await shelterRequests.getByRole("radio", { name: /Shelter or group/i }).check();
  await expect(shelterRequests.getByRole("button", { name: /Ask to add shelter/i })).toBeDisabled();
  await expect(shelterRequests.getByText(/already waiting/i)).toBeVisible();
  await shelterRequests.getByLabel(/Shelter name/i).selectOption("Downtown Outreach Shelter");
  await expect(shelterRequests.getByRole("button", { name: /Ask to add shelter/i })).toBeDisabled();
  await shelterRequests.getByLabel(/Shelter name/i).selectOption("Harbor Night Shelter");
  await expect(shelterRequests.getByRole("button", { name: /Ask to add shelter/i })).toBeEnabled();
  await shelterRequests.getByRole("button", { name: /Ask to add shelter/i }).click();
  await expect(page.locator(".list-item").filter({ hasText: "Harbor Night Shelter" }).getByText(/pending/i)).toBeVisible();

  await page.evaluate(() => {
    window.location.hash = "#/provider-operations";
  });
  await page.getByLabel(/Service organization/i).selectOption("Harbor Night Shelter");
  await page.getByLabel(/Staff identity/i).selectOption({ label: "Riley Chen" });
  const request = page.locator(".access-request-item").filter({ hasText: "Harbor Night Shelter" }).filter({ hasText: "User asked" });
  await request.getByRole("button", { name: /^Approve$/i }).click();
  await expect(request.getByText(/approved/i)).toBeVisible();
  await page.evaluate(() => {
    window.location.hash = "#/contacts";
  });
  await expect(page.locator(".recipient-list-item").filter({ hasText: "Harbor Night Shelter" })).toBeVisible();
});

test("user can cancel a pending shelter contact request", async ({ page }) => {
  await openAppRoute(page, "/#/contacts");
  const shelterRequests = page.getByRole("region", { name: "Add contact" });
  await shelterRequests.getByRole("radio", { name: /Shelter or group/i }).check();
  await shelterRequests.getByLabel(/Shelter name/i).selectOption("Harbor Night Shelter");
  await shelterRequests.getByRole("button", { name: /Ask to add shelter/i }).click();
  const request = page.locator(".list-item").filter({ hasText: "Harbor Night Shelter" }).filter({ hasText: "You asked this shelter." });
  await expect(request.getByText(/pending/i)).toBeVisible();
  await expect(shelterRequests.getByRole("button", { name: /Ask to add shelter/i })).toBeDisabled();
  await request.getByRole("button", { name: /^Cancel$/i }).click();
  await expect(request.getByText(/canceled/i)).toBeVisible();
  await expect(shelterRequests.getByRole("button", { name: /Ask to add shelter/i })).toBeEnabled();
});

test("verified shelter staff can send a contact-list nudge", async ({ page }) => {
  await openAppRoute(page, "/#/provider-operations");
  await page.getByLabel(/Service organization/i).selectOption("Rose City Shelter");
  await page.getByLabel(/Staff identity/i).selectOption({ label: "Avery Patel" });
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

test("provider administrator can add and remove staff", async ({ page }) => {
  await openAppRoute(page, "/#/provider-operations");
  await page.getByLabel(/Service organization/i).selectOption("Rose City Shelter");
  await expect(page.getByRole("region", { name: /Add staff member/i })).toHaveCount(0);

  await page.getByLabel(/I am an administrator for this provider/i).check();
  const addStaff = page.getByRole("region", { name: /Add staff member/i });
  await addStaff.getByLabel(/Staff name/i).fill("Taylor Admin");
  await addStaff.getByLabel(/Staff email/i).fill("taylor@rose.example");
  await addStaff.getByRole("button", { name: /Add staff member/i }).click();

  const roster = page.getByRole("region", { name: /Provider staff roster/i });
  const newStaff = roster.locator(".provider-staff-roster-item").filter({ hasText: "Taylor Admin" });
  await expect(newStaff.getByText(/Verified/i)).toBeVisible();
  await newStaff.getByRole("button", { name: /Revoke access/i }).click();
  await expect(newStaff.getByText(/Revoked/i)).toBeVisible();
  await newStaff.getByRole("button", { name: /Re-verify/i }).click();
  await expect(newStaff.getByText(/Verified/i)).toBeVisible();
  await newStaff.getByRole("button", { name: /Remove staff/i }).click();
  await expect(roster.locator(".provider-staff-roster-item").filter({ hasText: "Taylor Admin" })).toHaveCount(0);
});

test("provider case management sends messages and proves eligibility criteria", async ({ page }) => {
  await openAppRoute(page, "/#/provider-cases");
  await expect(page.locator("h1", { hasText: /Case management/i })).toBeVisible();
  const caseSection = page.locator('section[aria-labelledby="Case-management"]');
  const abbyCase = caseSection.locator(".provider-case-item").filter({ hasText: "Abby" });
  await expect(abbyCase.getByLabel("Next step")).toHaveValue(/Verify citizenship eligibility/i);
  await abbyCase.getByLabel("Status").selectOption("eligible");
  await expect(abbyCase.getByLabel("Status")).toHaveValue("eligible");

  await abbyCase.getByRole("button", { name: /Message client/i }).click();
  const messageSection = page.locator('section[aria-labelledby="Client-notifications-and-messages"]');
  await expect(page.locator("h1", { hasText: /Client messages/i })).toBeVisible();
  await messageSection.getByRole("textbox", { name: /Message/i }).fill("Your case is ready for eligibility verification.");
  await messageSection.getByRole("button", { name: /Send message/i }).click();
  await expect(messageSection.locator(".provider-message-item").filter({ hasText: /ready for eligibility verification/i })).toBeVisible();

  await page.goto("/#/provider-cases");
  const refreshedAbbyCase = page.locator('section[aria-labelledby="Case-management"] .provider-case-item').filter({ hasText: "Abby" });
  await refreshedAbbyCase.getByRole("button", { name: /Prove US citizen/i }).click();
  const proofSection = page.locator('section[aria-labelledby="Zero-knowledge-proof-certificates"]');
  await expect(page.locator("h1", { hasText: /Zero-knowledge certificates/i })).toBeVisible();
  await expect(proofSection.getByLabel("Eligibility criterion")).toHaveValue("us_citizen");
  await expect(proofSection.getByLabel("Certificate type")).toHaveValue("us_citizenship");
  await proofSection.getByRole("button", { name: /Process certificate/i }).click();

  const transparencyLog = page.getByRole("region", { name: /Verifier transparency log/i });
  const citizenshipProof = transparencyLog.locator(".provider-proof-item").filter({ hasText: /US citizenship criteria/i });
  await expect(citizenshipProof).toBeVisible();
  await expect(citizenshipProof.getByText("US citizen", { exact: true })).toBeVisible();
  await expect(citizenshipProof.getByText(/Client commitment/i)).toBeVisible();

  await page.goto("/#/provider-cases");
  const provedCase = page.locator('section[aria-labelledby="Case-management"] .provider-case-item').filter({ hasText: "Abby" });
  await expect(provedCase.getByText(/US citizen proved/i)).toBeVisible();
});

test("provider portal sends client messages and processes ZK certificates", async ({ page }) => {
  await openAppRoute(page, "/#/shelter");
  await expect(page.locator("h1", { hasText: /Provider overview/i })).toBeVisible();
  await page.goto("/#/provider-clients");
  await expect(page.locator("h1", { hasText: /Clients served/i })).toBeVisible();
  await page.locator(".provider-client-list").getByRole("button", { name: /^Message$/i }).first().click();

  const messageSection = page.locator('section[aria-labelledby="Client-notifications-and-messages"]');
  await expect(page.locator("h1", { hasText: /Client messages/i })).toBeVisible();
  await page.getByLabel(/Staff identity/i).selectOption({ label: "Avery Patel" });
  await messageSection.locator("select").first().selectOption({ label: "Abby" });
  await messageSection.getByRole("textbox", { name: /Message/i }).fill("Please arrive 10 minutes early for your service appointment.");
  await messageSection.getByRole("button", { name: /Send message/i }).click();
  const sentMessage = messageSection.locator(".provider-message-item").filter({ hasText: /Please arrive 10 minutes early/i });
  await expect(sentMessage).toBeVisible();
  await expect(sentMessage.getByText(/Sent by Avery Patel/i)).toBeVisible();

  await page.goto("/#/messages");
  const clientInbox = page.locator('section[aria-labelledby="Service-staff-messages"]');
  await expect(page.getByRole("heading", { name: /^Messages$/i })).toBeVisible();
  await expect(clientInbox.getByText(/Please arrive 10 minutes early/i)).toBeVisible();
  await clientInbox.getByRole("button", { name: /Mark read/i }).first().click();
  await expect(clientInbox.getByText("Read", { exact: true }).first()).toBeVisible();

  await page.goto("/#/provider-proofs");
  await page.getByLabel(/Staff identity/i).selectOption({ label: "Avery Patel" });
  const proofSection = page.locator('section[aria-labelledby="Zero-knowledge-proof-certificates"]');
  await proofSection.locator("select").first().selectOption({ label: "Abby" });
  await proofSection.getByLabel("Certificate type").selectOption("benefits_referral");
  await proofSection.getByLabel("Public claim").fill("Client received a benefits referral without exposing private documents.");
  await proofSection.getByRole("button", { name: /Process certificate/i }).click();
  const processedProof = page
    .getByRole("region", { name: /Verifier transparency log/i })
    .locator(".provider-proof-item")
    .filter({ hasText: /Client received a benefits referral/i });
  await expect(processedProof).toBeVisible();
  await expect(processedProof.getByText(/Client commitment/i)).toBeVisible();
  await expect(processedProof.getByText(/verified/i)).toBeVisible();
});

test("provider analytics and proof menus expose operational insights", async ({ page }) => {
  await openAppRoute(page, "/#/provider-analytics");
  await expect(page.locator("h1", { hasText: /Staff analytics/i })).toBeVisible();
  await expect(page.getByRole("region", { name: /Operational insights/i })).toContainText(/Proof coverage/i);
  await expect(page.getByRole("region", { name: /Operational insights/i })).toContainText(/Message reach/i);
  await expect(page.getByRole("region", { name: /Client need distribution/i })).toContainText(/Shelter/i);
  await expect(page.getByRole("region", { name: /Recent provider activity/i })).toContainText(/Message sent/i);

  await page.goto("/#/provider-proofs");
  await expect(page.locator("h1", { hasText: /Zero-knowledge certificates/i })).toBeVisible();
  await expect(page.getByRole("region", { name: /Zero-knowledge proof certificates/i })).toContainText(/Client coverage/i);
  await expect(page.getByRole("region", { name: /Certificate queue/i })).toContainText(/Needs certificate/i);
  await expect(page.getByRole("region", { name: /Verifier transparency log/i })).toBeVisible();
});

test("proof center shows public proof inputs without private coordinates", async ({ page }) => {
  await openAppRoute(page, "/#/proof-center");
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

test("proof center reviews proof certificates from a wallet QR screenshot", async ({ page }) => {
  await page.addInitScript(() => {
    class MockBarcodeDetector {
      async detect() {
        return [{ rawValue: "ipfs://bafyproofbundlecid" }];
      }
    }

    Object.defineProperty(window, "BarcodeDetector", {
      configurable: true,
      value: MockBarcodeDetector
    });
  });

  await page.route("https://w3s.link/ipfs/bafyproofbundlecid", async (route) => {
    await route.fulfill({
      json: {
        title: "Homeless services proof bundle",
        proofs: [
          {
            proof_id: "proof-us-citizenship",
            proof_type: "us_citizenship",
            claim: "US citizenship verified",
            verifier_id: "shelter-enrollment-verifier",
            proof_system: "groth16",
            verification_status: "verified",
            public_inputs: {
              claim: "us_citizenship_verified",
              issuing_authority: "State identity verifier"
            },
            witness_label: "Citizenship certificate",
            created_at: "2026-05-08T10:30:00Z"
          },
          {
            proof_id: "proof-income",
            proof_type: "income_eligibility",
            claim: "Income eligibility verified",
            verifier_id: "housing-benefits-verifier",
            proof_system: "groth16",
            verification_status: "verified",
            public_inputs: {
              claim: "income_eligible",
              program: "Rapid rehousing"
            },
            witness_label: "Income proof",
            created_at: "2026-05-08T10:31:00Z"
          }
        ]
      }
    });
  });

  await openAppRoute(page, "/#/proof-center");
  await page.getByLabel(/Choose proof QR screenshot/i).setInputFiles({
    buffer: Buffer.from(
      "iVBORw0KGgoAAAANSUhEUgAAAUoAAAFKAQAAAABTUiuoAAAB+UlEQVR4nO2bQYrjMBBFX40MvbRhDpCjyFebI80NrKPkBvLSoPBnIdmdpofB3eDYA1WLJCRv8eFTpa9KYmJnpR97SXDUUUcdddTRI1Fr1UEaHmY2AMzr2+PhAhzdVV19ihPA/BOLGcHcFSAUAOxIAY5+A523Fpo72iug9tsrBDj6HTQNQLoVbDxHgKP7UU087EwBjv6j1jnXC5iBmAdg7oqY4fnufLpWRxuazGoStJEgYgYbedRI+AoBju6p2lvPLdQXBIu1fjtagKNfv2+NAMxtLppZh35ZV5vuBQIc3VeSJOgLRKkOQWIGSQUgqNZ0ulZHn9zStDmjvH46QbXR3boYGlVosWJrNXrpL+gxAhzdhUr3N1WjoiQbCYLZjJgffm5dBl0nIUHt3JKkqS/U6SgV/Ny6CtrcijVRQBuCmQ+hw926Btq9vxSAxd8ddY2RLJRn9HStjm5uBZFGgL50BqEYdWO4WXa6VkdbyphgDYH1BNsy4WsEOLqv1pQBQFD1jV4i5tASvJ9b10Lj+524l6T7dunyBH8hdM2EGYg5SMrh4zLXN08XRtNtMSkH1UXU1C/+K5rrojEHkW6LQb8Y8f7mm6fLoJ++O05jKBbvHe1h2u5cp2t1tLmVapQIWBRALywNoZCGfKwAR7+Amv9rwVFHHXXU0f8I/QOFNg2uEDfTqgAAAABJRU5ErkJggg==",
      "base64"
    ),
    mimeType: "image/png",
    name: "wallet-qr.png"
  });

  await expect(page.getByLabel(/QR proof bundle summary/i)).toContainText(/Homeless services proof bundle/i);
  await expect(page.getByLabel(/QR proof bundle summary/i)).toContainText(/US citizenship verified/i);
  await expect(page.getByLabel(/QR proof bundle summary/i)).toContainText(/Income eligibility verified/i);
  const citizenshipProof = page.getByRole("article", { name: /US citizenship verified/i });
  await expect(citizenshipProof).toContainText(/From QR bundle/i);
  await expect(citizenshipProof).toContainText(/State identity verifier/i);
  const incomeProof = page.getByRole("article", { name: /Income eligibility verified/i });
  await expect(incomeProof).toContainText(/Rapid rehousing/i);
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

  await openAppRoute(page, walletRoute("proof-center", "did:key:owner"));
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
  await openAppRoute(page, "/#/exports");
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

test("configured exports create verify and import encrypted descriptors", async ({ page }) => {
  const calls: string[] = [];
  const bundle = {
    actor_did: "did:key:dispatch-clinic",
    bundle_id: "export-ui-live",
    bundle_hash: "ui-live-hash",
    bundle_type: "wallet_export_v1",
    created_at: "2026-05-05T12:00:00Z",
    records: [{ record_id: "rec-document-benefits", data_type: "document" }],
    proofs: [{ proof_id: "proof-ui-live", proof_type: "location_region" }],
    versions: [{ record_id: "rec-document-benefits", encrypted_payload_ref: { uri: "memory://payload" } }],
    wallet: { wallet_id: "wallet-demo", owner_did: "did:key:owner" }
  };

  const handleWalletApiRoute = async (route: Route) => {
    const url = new URL(route.request().url());
    const path = url.pathname;
    if (path.endsWith("/exports/grants")) {
      calls.push("grant");
      const request = route.request().postDataJSON();
      expect(request.record_ids).toEqual(["rec-document-benefits", "rec-location-current"]);
      await route.fulfill({
        json: {
          grant_id: "grant-ui-live",
          audience_did: "did:key:dispatch-clinic",
          resources: ["wallet://wallet-demo/exports"],
          abilities: ["export/create"],
          caveats: { output_types: ["encrypted_export_bundle"] },
          status: "active"
        }
      });
      return;
    }
    if (path.endsWith("/exports/invocations")) {
      calls.push("invocation");
      const request = route.request().postDataJSON();
      expect(request.grant_id).toBe("grant-ui-live");
      await route.fulfill({
        json: {
          invocation_id: "invocation-ui-live",
          grant_id: "grant-ui-live",
          actor_did: "did:key:dispatch-clinic",
          invocation_token: "wallet-ucan-v1.ui-live",
          caveats: { output_types: ["encrypted_export_bundle"] }
        }
      });
      return;
    }
    if (path.endsWith("/wallet-demo/exports")) {
      calls.push("bundle");
      const request = route.request().postDataJSON();
      expect(request.invocation_token).toBe("wallet-ucan-v1.ui-live");
      await route.fulfill({ json: bundle });
      return;
    }
    if (path === "/exports/verify") {
      calls.push("verify");
      await route.fulfill({
        json: {
          valid: true,
          hash_valid: true,
          schema_valid: true,
          bundle_id: bundle.bundle_id,
          bundle_hash: bundle.bundle_hash,
          computed_hash: bundle.bundle_hash
        }
      });
      return;
    }
    if (path === "/exports/storage") {
      calls.push("storage");
      await route.fulfill({
        json: {
          bundle_id: bundle.bundle_id,
          bundle_hash: bundle.bundle_hash,
          wallet_id: "wallet-demo",
          ok: true,
          record_count: 1,
          reports: []
        }
      });
      return;
    }
    if (path === "/exports/import") {
      calls.push("import");
      const request = route.request().postDataJSON();
      expect(request.bundle.bundle_id).toBe(bundle.bundle_id);
      await route.fulfill({
        json: {
          wallet_id: "wallet-demo",
          bundle_id: bundle.bundle_id,
          bundle_hash: bundle.bundle_hash,
          record_count: 1,
          version_count: 1,
          proof_count: 1,
          derived_artifact_count: 0
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
    if (path.endsWith("/records")) {
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
    await route.fulfill({ status: 404, json: { error: "unexpected export UI call", path } });
  };

  await page.route("**/wallets/**", handleWalletApiRoute);
  await page.route("**/exports/**", handleWalletApiRoute);

  await page.goto(
    walletRoute("exports", "did:key:owner", {
      audienceKeyHex: "22".repeat(32),
      issuerKeyHex: "11".repeat(32)
    })
  );
  await page.getByLabel(/Recipient DID/i).fill("did:key:dispatch-clinic");
  await page.getByLabel(/Recipient label/i).fill("Dispatch Clinic");
  await page.getByRole("button", { name: /Create bundle/i }).click();

  await expect(page.getByText(/Export bundle verified/i)).toBeVisible();
  const createdBundle = page.getByRole("article", { name: /Dispatch Clinic/i });
  await expect(createdBundle.getByText(/storage verified/i)).toBeVisible();
  await expect(createdBundle.getByText(/hash verified/i)).toBeVisible();
  await expect(createdBundle.getByText(/schema verified/i)).toBeVisible();
  await expect(createdBundle.getByText(/not imported/i)).toBeVisible();
  await createdBundle.getByRole("button", { name: /Import descriptors/i }).click();
  await expect(page.getByText(/Export descriptors imported/i)).toBeVisible();
  await expect(createdBundle.getByText(/import verified/i)).toBeVisible();
  expect(calls).toEqual(["grant", "invocation", "bundle", "verify", "storage", "import"]);
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
  await openAppRoute(page, walletRoute("security", "did:key:owner"));

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
  await openAppRoute(page, walletRoute("uploads", "did:key:owner"));
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

test("wallet file uploads can use a configured IPFS and Filecoin backend", async ({ page }) => {
  let storageRequests = 0;
  await page.addInitScript(() => {
    window.localStorage.setItem(
      "abby-filecoin-storage-config",
      JSON.stringify({ uploadUrl: "/filecoin-upload" })
    );
  });
  await page.route("**/filecoin-upload", async (route) => {
    storageRequests += 1;
    expect(route.request().method()).toBe("POST");
    expect(route.request().headers()["content-type"]).toContain("multipart/form-data");
    await route.fulfill({
      json: {
        filecoinDealId: "42",
        filecoinPieceCid: "baga-wallet-piece",
        ipfsCid: "bafywallet",
        message: "Pinned through Synapse.",
        provider: "ipfs-filecoin"
      }
    });
  });

  await openAppRoute(page, "/#/uploads");
  await expect(page.getByRole("heading", { name: /^Wallet$/i })).toBeVisible();
  await page.getByLabel(/Store new wallet files on IPFS\/Filecoin/i).check();
  await page.getByLabel(/Choose file to upload/i).setInputFiles({
    name: "benefits-update.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-1.4\n")
  });
  const walletFile = page.locator(".upload-list-item").filter({ hasText: "benefits-update.pdf" });
  await expect(walletFile.getByText(/IPFS\/Filecoin/i)).toBeVisible();
  await expect(walletFile.getByText(/bafywallet/i)).toBeVisible();
  await expect(walletFile.getByText(/Pinned through Synapse/i)).toBeVisible();
  expect(storageRequests).toBe(1);
});

test("wallet page renders a scannable proof QR that opens proof center review", async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem(
      "abby-filecoin-storage-config",
      JSON.stringify({ uploadUrl: "/filecoin-upload" })
    );
  });
  await page.route("**/filecoin-upload", async (route) => {
    await route.fulfill({
      json: {
        ipfsCid: "bafywalletproofbundlecid",
        message: "Stored wallet proof bundle.",
        provider: "ipfs-filecoin"
      }
    });
  });
  await page.route("https://w3s.link/ipfs/bafywalletproofbundlecid", async (route) => {
    await route.fulfill({
      json: {
        title: "Client wallet proof bundle",
        proofs: [
          {
            claim: "Location is in service region",
            id: "proof-1",
            proofSystem: "simulated",
            proofType: "location_region",
            publicInputs: {
              claim: "location_in_region",
              region_id: "multnomah_county"
            },
            simulated: true,
            verificationStatus: "verified",
            verifier: "211 service matcher",
            witnessLabel: "Current location"
          },
          {
            claim: "Contribution follows study consent",
            id: "proof-2",
            proofSystem: "simulated",
            proofType: "analytics_contribution",
            publicInputs: {
              fields: "county, need_category",
              template_id: "housing_service_gap_v1"
            },
            simulated: true,
            verificationStatus: "verified",
            verifier: "Analytics template verifier",
            witnessLabel: "Derived service needs"
          }
        ]
      }
    });
  });
  await openAppRoute(page, "/#/uploads");
  await expect(page.getByRole("heading", { name: /^Wallet$/i })).toBeVisible();
  const qrImage = page.getByRole("img", { name: /Wallet proof QR code/i });
  await expect(qrImage).toBeVisible();
  await expect(page.getByText(/Scan to open the client proof bundle/i)).toBeVisible();
  await expect(page.getByText(/IPFS CID QR/i)).toBeVisible();
  await expect(page.getByText(/bafywalletproofbundlecid/i)).toBeVisible();
  await expect(page.getByText(/Location is in service region/i)).toBeVisible();
  await expect(page.getByRole("link", { name: /Open proof review/i })).toBeVisible();
  const qrSource = await qrImage.getAttribute("src");
  expect(qrSource).toMatch(/^data:image\/png;base64,/);

  await page.getByRole("link", { name: /Open proof review/i }).click();
  await expect(page.getByRole("heading", { name: /Verified wallet claims/i })).toBeVisible();
  await expect(page.getByLabel(/QR proof bundle summary/i)).toContainText(/Client wallet proof bundle/i);
  await expect(page.getByRole("article", { name: /Location is in service region/i }).first()).toContainText(/From QR bundle|Wallet proof bundle link/i);
});

test("recipient receipt can create an encrypted derived analysis artifact", async ({ page }) => {
  test.setTimeout(60_000);
  let analysisRequests = 0;
  let redactedAnalysisRequests = 0;
  let vectorProfileRequests = 0;
  let textExtractionRequests = 0;
  let formAnalysisRequests = 0;
  let graphRagRequests = 0;
  let analysisInvocationRequests = 0;
  let decryptRequests = 0;
  let decryptInvocationRequests = 0;
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
      caveats: { purpose: "service_matching", user_presence_required: true },
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
    if (path.endsWith("/records/rec-benefits-letter/analysis-invocations")) {
      analysisInvocationRequests += 1;
      expect(route.request().method()).toBe("POST");
      const request = await route.request().postDataJSON();
      expect(request).toMatchObject({
        actor_did: "did:key:delegate",
        actor_key_hex: "delegate-key",
        grant_id: "grant-analysis",
        user_present: true
      });
      await route.fulfill({
        json: {
          invocation: {
            invocation_id: `invocation-analysis-${analysisInvocationRequests}`,
            grant_id: "grant-analysis",
            audience_did: "did:key:delegate",
            resource: "wallet://wallet-demo/records/rec-benefits-letter",
            ability: "record/analyze",
            caveats: { output_types: request.output_types, purpose: "service_matching", user_present: true },
            issued_at: "2026-05-03T18:01:00Z",
            expires_at: null,
            nonce: `nonce-analysis-${analysisInvocationRequests}`,
            signature: `sig-analysis-${analysisInvocationRequests}`
          },
          token: `wallet-ucan-v1.analysis-${analysisInvocationRequests}`
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
    if (path.endsWith("/records/rec-benefits-letter/analyze/redacted")) {
      redactedAnalysisRequests += 1;
      expect(route.request().method()).toBe("POST");
      expect(await route.request().postDataJSON()).toMatchObject({
        actor_did: "did:key:delegate",
        actor_key_hex: "delegate-key",
        grant_id: "grant-analysis",
        max_chars: 500
      });
      await route.fulfill({
        json: {
          artifact: {
            artifact_id: "artifact-redacted-analysis",
            source_record_ids: ["rec-benefits-letter"],
            artifact_type: "redacted_document_analysis",
            output_policy: "redacted_derived_only",
            encrypted_payload_ref: {
              uri: "mem://redacted-analysis",
              storage_type: "memory",
              digest: "sha256:redacted-analysis"
            },
            created_at: "2026-05-03T18:01:05Z"
          },
          output: {
            summary: "Detected need categories across authorized text: housing, food.",
            output_policy: "redacted_derived_only",
            derived_facts: { need_categories: ["housing", "food"] }
          }
        }
      });
      return;
    }
    if (path.endsWith("/records/rec-benefits-letter/vector-profile")) {
      vectorProfileRequests += 1;
      expect(route.request().method()).toBe("POST");
      expect(await route.request().postDataJSON()).toMatchObject({
        actor_did: "did:key:delegate",
        actor_key_hex: "delegate-key",
        grant_id: "grant-analysis",
        chunk_size_words: 80
      });
      await route.fulfill({
        json: {
          artifact: {
            artifact_id: "artifact-vector-profile",
            source_record_ids: ["rec-benefits-letter"],
            artifact_type: "redacted_document_vector_profile",
            output_policy: "encrypted_vector_profile",
            encrypted_payload_ref: {
              uri: "mem://vector-profile",
              storage_type: "memory",
              digest: "sha256:vector-profile"
            },
            created_at: "2026-05-03T18:01:10Z"
          },
          output: {
            output_policy: "encrypted_vector_profile",
            profile: {
              profile_type: "redacted_lexical_hash_vector",
              chunk_count: 2
            }
          }
        }
      });
      return;
    }
    if (path.endsWith("/records/rec-benefits-letter/extract-text/redacted")) {
      textExtractionRequests += 1;
      expect(route.request().method()).toBe("POST");
      expect(await route.request().postDataJSON()).toMatchObject({
        actor_did: "did:key:delegate",
        actor_key_hex: "delegate-key",
        grant_id: "grant-analysis",
        max_chars: 20_000,
        max_bytes: 200_000,
        use_ocr: true
      });
      await route.fulfill({
        json: {
          artifact: {
            artifact_id: "artifact-text-extraction",
            source_record_ids: ["rec-benefits-letter"],
            artifact_type: "redacted_document_text_extraction",
            output_policy: "redacted_extracted_text",
            encrypted_payload_ref: {
              uri: "mem://redacted-text",
              storage_type: "memory",
              digest: "sha256:redacted-text"
            },
            created_at: "2026-05-03T18:01:15Z"
          },
          output: {
            text: "Full name: [REDACTED_PERSON]\nEmail: [REDACTED_EMAIL]",
            output_policy: "redacted_extracted_text",
            redaction_counts: { email: 1, person: 1 }
          }
        }
      });
      return;
    }
    if (path.endsWith("/records/rec-benefits-letter/forms/analyze/redacted")) {
      formAnalysisRequests += 1;
      expect(route.request().method()).toBe("POST");
      expect(await route.request().postDataJSON()).toMatchObject({
        actor_did: "did:key:delegate",
        actor_key_hex: "delegate-key",
        grant_id: "grant-analysis",
        max_fields: 100,
        use_ocr: false
      });
      await route.fulfill({
        json: {
          artifact: {
            artifact_id: "artifact-form-analysis",
            source_record_ids: ["rec-benefits-letter"],
            artifact_type: "redacted_document_form_analysis",
            output_policy: "redacted_form_analysis",
            encrypted_payload_ref: {
              uri: "mem://form-analysis",
              storage_type: "memory",
              digest: "sha256:form-analysis"
            },
            created_at: "2026-05-03T18:01:20Z"
          },
          output: {
            output_policy: "redacted_form_analysis",
            form: { field_count: 2, data_type_counts: { email: 1, person: 1 } },
            fields: [
              { label: "Full name", data_type: "person", required: false },
              { label: "Email", data_type: "email", required: false }
            ]
          }
        }
      });
      return;
    }
    if (path.endsWith("/records/graphrag/redacted")) {
      graphRagRequests += 1;
      expect(route.request().method()).toBe("POST");
      expect(await route.request().postDataJSON()).toMatchObject({
        actor_did: "did:key:delegate",
        actor_key_hex: "delegate-key",
        grant_id: "grant-analysis",
        record_ids: ["rec-benefits-letter"],
        max_chars_per_record: 20_000,
        max_bytes_per_record: 200_000,
        use_ocr: true
      });
      await route.fulfill({
        json: {
          artifact: {
            artifact_id: "artifact-graphrag",
            source_record_ids: ["rec-benefits-letter"],
            artifact_type: "redacted_document_graphrag",
            output_policy: "redacted_graphrag",
            encrypted_payload_ref: {
              uri: "mem://redacted-graphrag",
              storage_type: "memory",
              digest: "sha256:redacted-graphrag"
            },
            created_at: "2026-05-03T18:01:25Z"
          },
          output: {
            output_policy: "redacted_graphrag",
            graph: {
              graph_type: "redacted_category_entity_graph",
              node_count: 4,
              edge_count: 3,
              category_record_counts: { housing: 1, food: 1 },
              redaction_counts: { email: 1, person: 1 }
            },
            source_record_ids: ["rec-benefits-letter"],
            source_record_count: 1
          }
        }
      });
      return;
    }
    if (path.endsWith("/records/rec-benefits-letter/analyze")) {
      analysisRequests += 1;
      expect(route.request().method()).toBe("POST");
      expect(await route.request().postDataJSON()).toMatchObject({
        actor_did: "did:key:delegate",
        actor_key_hex: "delegate-key",
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
    if (path.endsWith("/records/rec-benefits-letter/decrypt-invocations")) {
      decryptInvocationRequests += 1;
      expect(route.request().method()).toBe("POST");
      expect(await route.request().postDataJSON()).toMatchObject({
        actor_did: "did:key:delegate",
        actor_key_hex: "delegate-key",
        grant_id: "grant-analysis",
        user_present: true
      });
      await route.fulfill({
        json: {
          invocation: {
            invocation_id: "invocation-presence",
            grant_id: "grant-analysis",
            audience_did: "did:key:delegate",
            resource: "wallet://wallet-demo/records/rec-benefits-letter",
            ability: "record/decrypt",
            caveats: { purpose: "service_matching", user_present: true },
            issued_at: "2026-05-03T18:02:20Z",
            expires_at: null,
            nonce: "nonce-presence",
            signature: "sig-presence"
          },
          token: "wallet-ucan-v1.presence"
        }
      });
      return;
    }
    if (path.endsWith("/records/rec-benefits-letter/decrypt")) {
      decryptRequests += 1;
      expect(route.request().method()).toBe("POST");
      expect(await route.request().postDataJSON()).toMatchObject({
        actor_did: "did:key:delegate",
        actor_key_hex: "delegate-key",
        invocation_token: "wallet-ucan-v1.presence"
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
    if (path.endsWith("/grants/grant-analysis/delegate")) {
      delegationRequests += 1;
      expect(route.request().method()).toBe("POST");
      expect(await route.request().postDataJSON()).toMatchObject({
        abilities: ["record/analyze"],
        audience_did: "did:key:case-worker",
        issuer_did: "did:key:delegate",
        issuer_key_hex: "delegate-key",
        resources: ["wallet://wallet-demo/records/rec-benefits-letter"]
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
        action: "grant/delegate",
        resource: "wallet://wallet-demo/records/rec-benefits-letter",
        decision: "allow",
        grant_id: "grant-analysis"
      });
      await route.fulfill({
        json: {
          grant_id: "grant-child",
          receipt_hash: "receipt-hash-child"
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

  await openAppRoute(page, walletRoute("recipient-access", "did:key:delegate", { audienceKeyHex: "delegate-key" }));
  const receipt = page.getByRole("article", { name: /delegate/i }).filter({ hasText: "Share proof code" });
  await expect(receipt).toBeVisible({ timeout: 15_000 });
  const analyzeButton = receipt.getByRole("button", { name: /Make safe summary/i });
  await expect(analyzeButton).toBeVisible({ timeout: 15_000 });
  await analyzeButton.scrollIntoViewIfNeeded();
  await analyzeButton.click();
  await expect(receipt.getByText(/summary · derived_only/i)).toBeVisible();
  await expect(receipt.getByText(/mem:\/\/derived-artifact/i)).toBeVisible();
  await expect(receipt.getByText(/rec-benefits-letter/i)).toBeVisible();
  await receipt.getByRole("button", { name: /Redacted analysis/i }).click();
  await expect(receipt.getByText(/redacted_document_analysis · redacted_derived_only/i)).toBeVisible();
  await expect(receipt.getByText(/Detected need categories across authorized text/i)).toBeVisible();
  await receipt.getByRole("button", { name: /Vector profile/i }).click();
  await expect(receipt.getByText(/redacted_document_vector_profile · encrypted_vector_profile/i)).toBeVisible();
  await expect(receipt.getByText(/redacted_lexical_hash_vector · 2 chunks/i)).toBeVisible();
  await receipt.getByRole("button", { name: /Extract text/i }).click();
  await expect(receipt.getByText(/redacted_document_text_extraction · redacted_extracted_text/i)).toBeVisible();
  await expect(receipt.getByText(/\[REDACTED_EMAIL\]/i)).toBeVisible();
  await receipt.getByRole("button", { name: /Analyze form/i }).click();
  await expect(receipt.getByText(/redacted_document_form_analysis · redacted_form_analysis/i)).toBeVisible();
  await expect(receipt.getByText(/2 redacted fields: Full name, Email/i)).toBeVisible();
  await receipt.getByRole("button", { name: /Build GraphRAG/i }).click();
  await expect(receipt.getByText(/redacted_document_graphrag · redacted_graphrag/i)).toBeVisible();
  await expect(receipt.getByText(/redacted_category_entity_graph · 4 nodes · 3 edges/i)).toBeVisible();
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
  await expect(page.getByRole("heading", { name: /Consent and access history/i })).toBeVisible();
  await expect(page.getByText(/record\/analyze/i).first()).toBeVisible();
  await expect(page.getByText(/grant-analysis/i).first()).toBeVisible();
  expect(analysisRequests).toBe(1);
  expect(redactedAnalysisRequests).toBe(1);
  expect(vectorProfileRequests).toBe(1);
  expect(textExtractionRequests).toBe(1);
  expect(formAnalysisRequests).toBe(1);
  expect(graphRagRequests).toBe(1);
  expect(analysisInvocationRequests).toBe(6);
  expect(decryptRequests).toBe(1);
  expect(decryptInvocationRequests).toBe(1);
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

  await openAppRoute(page, walletRoute("audit", "did:key:owner"));
  await expect(page.getByRole("heading", { name: /Consent and access history/i })).toBeVisible();
  await expect(page.getByText(/record\/analyze/i)).toBeVisible();
  await expect(page.getByText(/storage\/repair/i)).toBeVisible();
  await expect(page.getByText(/wallet:\/\/wallet-demo\/records\/rec-benefits-letter/i).first()).toBeVisible();
  await expect(page.getByText(/grant-analysis/i)).toBeVisible();
});
