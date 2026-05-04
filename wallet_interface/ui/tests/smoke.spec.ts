import { expect, test, type Page } from "@playwright/test";

const SCREEN_READY_TIMEOUT_MS = 15000;

const routeReadyHeadings: Record<string, RegExp> = {
  home: /Your safety plan/i,
  analytics: /Share patterns/i,
  "benefits-protection": /Optional agency notification/i,
  "check-in": /Set your schedule/i,
  contacts: /People and services/i,
  "recipient-access": /Access requests/i,
  register: /Create your Abby profile/i,
  "sharing-rules": /Choose what each person can see/i,
  shelter: /Staff verification required|Assisted access/i,
  "social-services": /Find support/i,
  uploads: /Document and information vault/i,
  security: /Account safety/i,
  audit: /Audit history/i
};

async function expectRouteReady(page: Page, route: string) {
  await expect(page.locator(".screen")).toBeVisible({ timeout: SCREEN_READY_TIMEOUT_MS });
  await expect(page.getByRole("heading", { name: routeReadyHeadings[route] })).toBeVisible({
    timeout: SCREEN_READY_TIMEOUT_MS
  });
}

async function openRoute(page: Page, route: string) {
  await page.goto(route === "home" ? "/" : `/#/${route}`, { waitUntil: "domcontentloaded" });
  try {
    await expectRouteReady(page, route);
  } catch {
    await page.reload({ waitUntil: "domcontentloaded" });
    await expectRouteReady(page, route);
  }
}

async function reloadRoute(page: Page, route: string) {
  await page.reload({ waitUntil: "domcontentloaded" });
  try {
    await expectRouteReady(page, route);
  } catch {
    await page.reload({ waitUntil: "domcontentloaded" });
    await expectRouteReady(page, route);
  }
}

async function setRoute(page: Page, route: string) {
  await page.evaluate((targetRoute) => {
    window.location.hash = targetRoute === "home" ? "#/" : `#/${targetRoute}`;
  }, route);
  await expectRouteReady(page, route);
}

async function verifyRoseShelterStaff(page: Page) {
  await openRoute(page, "register");
  await page.getByLabel(/Legal or full name/i).fill("Riley Carter");
  await page.getByLabel(/I am shelter staff/i).check();
  await page.locator("select").first().selectOption("Rose City Shelter");
  await page.getByLabel(/Shelter staff PIN/i).fill("1234");
  await page.getByRole("button", { name: /Verify shelter staff/i }).click();
  await expect(page.getByText(/verified_staff/i)).toBeVisible();
}

async function expectShelterNavItem(page: Page, visible: boolean, isMobile: boolean) {
  if (isMobile) {
    await page.getByRole("button", { name: /Open menu/i }).click();
    const mobileNav = page.getByRole("navigation", { name: /Mobile navigation/i });
    await expect(mobileNav).toBeVisible();
    await expect(mobileNav.getByRole("button", { name: /^Shelter$/i })).toHaveCount(visible ? 1 : 0);
    await page.getByRole("button", { name: /Close menu/i }).click();
    await expect(mobileNav).not.toBeVisible();
    return;
  }

  await expect(page.getByRole("button", { name: /^Shelter$/i })).toHaveCount(visible ? 1 : 0);
}

async function seedShelterStaffIsolationFixture(page: Page) {
  await page.addInitScript(() => {
    if (window.localStorage.getItem("abby-ui-state-v1")) return;
    window.localStorage.setItem(
      "abby-ui-state-v1",
      JSON.stringify({
        shelterStaffAccounts: [
          {
            id: "staff-rose-seed",
            shelter: "Rose City Shelter",
            displayName: "Riley Carter",
            email: "riley.staff@example.org",
            verified: true,
            updatedAt: "2026-05-01T09:15:00.000Z"
          },
          {
            id: "staff-harbor-hidden",
            shelter: "Harbor Night Shelter",
            displayName: "Hidden Harbor",
            email: "hidden.harbor@example.org",
            verified: true,
            updatedAt: "2026-05-04T00:00:00.000Z"
          }
        ]
      })
    );
  });
}

async function seedShelterHealthCheckFixture(page: Page) {
  await page.addInitScript(() => {
    if (window.localStorage.getItem("abby-ui-state-v1")) return;
    window.localStorage.setItem(
      "abby-ui-state-v1",
      JSON.stringify({
        shelterStaffAccounts: [
          {
            id: "staff-rose-seed",
            shelter: "Rose City Shelter",
            displayName: "Riley Carter",
            email: "riley.staff@example.org",
            verified: true,
            updatedAt: "2026-05-01T09:15:00.000Z"
          }
        ],
        shelterUserAccounts: [
          {
            id: "user-prefers-rose-health",
            shelter: "Downtown Outreach Shelter",
            legalName: "Priya Followup",
            preferredName: "Priya",
            pronouns: "",
            dateOfBirth: "1982-02-12",
            photoAssetId: "priya-profile.png",
            phone: "",
            email: "",
            currentLocation: "Downtown Outreach Shelter",
            preferredShelter: "Rose City Shelter",
            serviceNeeds: ["Health"],
            easyBotCheckStatus: "failed",
            captchaToken: "mock-captcha-token",
            localPrecinctNotified: false,
            foundPermanentHousing: false,
            createdByStaffId: "",
            createdAt: "2026-05-02T08:00:00.000Z"
          },
          {
            id: "user-prefers-rose-passed",
            shelter: "Harbor Night Shelter",
            legalName: "Pat Passed",
            preferredName: "Pat",
            pronouns: "",
            dateOfBirth: "1990-09-09",
            photoAssetId: "pat-profile.png",
            phone: "",
            email: "",
            currentLocation: "Harbor Night Shelter",
            preferredShelter: "Rose City Shelter",
            serviceNeeds: ["Shelter"],
            easyBotCheckStatus: "passed",
            captchaToken: "mock-captcha-token",
            localPrecinctNotified: true,
            foundPermanentHousing: false,
            createdByStaffId: "",
            createdAt: "2026-05-03T08:00:00.000Z"
          },
          {
            id: "user-unrelated-failed",
            shelter: "Rose City Shelter",
            legalName: "No Shelter Followup",
            preferredName: "Noah",
            pronouns: "",
            dateOfBirth: "1977-07-17",
            photoAssetId: "noah-profile.png",
            phone: "",
            email: "",
            currentLocation: "Community intake",
            preferredShelter: "",
            serviceNeeds: ["Food"],
            easyBotCheckStatus: "failed",
            captchaToken: "mock-captcha-token",
            localPrecinctNotified: false,
            foundPermanentHousing: false,
            createdByStaffId: "",
            createdAt: "2026-05-04T08:00:00.000Z"
          }
        ]
      })
    );
  });
}

test("mobile home exposes the two required primary cards", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("button", { name: /Emergency contacts/i })).toBeVisible();
  await expect(page.getByRole("button", { name: /Social services/i })).toBeVisible();
});

test("Agent A typography, required markers, and home footer remain in place", async ({ page }) => {
  await openRoute(page, "home");
  await expect(page.locator("body")).toHaveCSS("font-family", /Comic Sans/i);
  await expect(page.getByRole("button", { name: /Next check-in.*Check in now/i })).toBeVisible();
  await expect(page.locator(".home-footer")).toContainText("Stored uploads");
  await expect(page.locator(".home-footer")).toContainText("Sharing rules");
  await expect(page.getByRole("link", { name: /Open sharing rules/i })).toBeVisible();

  await openRoute(page, "register");
  const legalNameInput = page.getByLabel(/Legal or full name/i);
  await expect(legalNameInput).toHaveAttribute("required", "");
  await expect(legalNameInput).toHaveAttribute("aria-required", "true");
  await expect(page.getByLabel(/Quick health check complete/i)).toHaveAttribute("aria-required", "true");
  await expect(page.getByLabel(/Bot check complete/i)).toHaveAttribute("aria-required", "true");
  await expect(page.locator(".captcha-box .required-marker")).toHaveCount(2);
  const requiredMarkerIsLarger = await page
    .locator(".field")
    .filter({ hasText: "Legal or full name" })
    .locator(".required-marker")
    .evaluate((marker) => {
      const markerSize = parseFloat(window.getComputedStyle(marker).fontSize);
      const title = marker.closest(".field-title");
      const titleSize = title ? parseFloat(window.getComputedStyle(title).fontSize) : 0;
      return markerSize > titleSize;
    });
  expect(requiredMarkerIsLarger).toBe(true);
});

test("decorative motion respects reduced-motion preference", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  await expect(page.locator(".screen")).toBeVisible();
  await expect(page.locator(".decor-shape").first()).toHaveCSS("animation-name", "none");
});

test("registration enforces minimum required profile fields", async ({ page }) => {
  await openRoute(page, "register");
  await expect(page.getByRole("button", { name: /Create profile draft/i })).toBeDisabled();
  await expect(page.getByLabel(/Legal or full name/i)).toBeVisible();
  await expect(page.getByText(/Only name, birth date, photo, and bot check are required/i)).toBeVisible();
  await page.getByLabel(/Legal or full name/i).fill("Abby Example");
  await page.getByLabel(/Birth date/i).fill("1990-01-01");
  await page.getByLabel(/Quick health check complete/i).check();
  await page.getByLabel(/Bot check complete/i).check();
  await expect(page.locator('input[type="file"][accept="image/jpeg,image/png,image/webp"]').first()).toBeAttached();
  await expect(page.getByRole("button", { name: /Create profile draft/i })).toBeDisabled();
  await page.locator('input[type="file"][accept="image/jpeg,image/png,image/webp"]').first().setInputFiles({
    name: "abby-profile.png",
    mimeType: "image/png",
    buffer: Buffer.from("profile image placeholder")
  });
  await expect(page.getByRole("button", { name: /Create profile draft/i })).toBeEnabled();
});

test("registration persists pass/pass and shelter-related follow-up bot-check states", async ({ page }) => {
  await openRoute(page, "register");
  await page.getByLabel(/Legal or full name/i).fill("Morgan Followup");
  await page.getByLabel(/Birth date/i).fill("1986-07-22");
  await page.getByLabel(/Photo or photo ID/i).setInputFiles({
    name: "morgan-followup.png",
    mimeType: "image/png",
    buffer: Buffer.from("profile image placeholder")
  });

  await expect(page.getByLabel(/Bot check complete/i)).toBeDisabled();
  await page.getByLabel(/Quick health check complete/i).check();
  await page.getByLabel(/Bot check complete/i).check();
  await expect(page.getByRole("button", { name: /Create profile draft/i })).toBeEnabled();
  await page.getByRole("button", { name: /Create profile draft/i }).click();
  await page.waitForFunction(() => {
    const raw = window.localStorage.getItem("abby-ui-state-v1");
    if (!raw) return false;
    const state = JSON.parse(raw);
    return state.profile?.easyBotCheckStatus === "passed" && state.profile?.captchaToken === "mock-captcha-token";
  });

  await page.getByRole("button", { name: /Mark health check follow-up/i }).click();
  await page.getByLabel(/Bot check complete/i).check();
  await expect(page.getByRole("button", { name: /Create profile draft/i })).toBeEnabled();
  await page.getByRole("button", { name: /Create profile draft/i }).click();
  await page.waitForFunction(() => {
    const raw = window.localStorage.getItem("abby-ui-state-v1");
    if (!raw) return false;
    const state = JSON.parse(raw);
    return (
      state.profile?.easyBotCheckStatus === "failed" &&
      state.profile?.captchaToken === "mock-captcha-token" &&
      state.profile?.preferredShelter === ""
    );
  });

  await page.getByLabel(/Preferred shelter/i).fill("Rose City Shelter");
  await page.getByRole("button", { name: /Mark health check follow-up/i }).click();
  await expect(page.getByRole("button", { name: /Create profile draft/i })).toBeDisabled();
  await page.getByLabel(/Bot check complete/i).check();
  await expect(page.getByRole("button", { name: /Create profile draft/i })).toBeEnabled();
  await page.getByRole("button", { name: /Create profile draft/i }).click();

  await page.waitForFunction(() => {
    const raw = window.localStorage.getItem("abby-ui-state-v1");
    if (!raw) return false;
    const state = JSON.parse(raw);
    return (
      state.profile?.easyBotCheckStatus === "failed" &&
      state.profile?.captchaToken === "mock-captcha-token" &&
      state.profile?.preferredShelter === "Rose City Shelter"
    );
  });
});

test("profile photo input rejects PDFs and keeps preview hidden by default", async ({ page }) => {
  await openRoute(page, "register");
  await expect(page.getByRole("heading", { name: /Create your Abby profile/i })).toBeVisible();
  const photoInput = page.locator('input[type="file"][accept="image/jpeg,image/png,image/webp"]').first();
  await expect(photoInput).toBeAttached();

  await photoInput.setInputFiles({
    name: "abby-id.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-1.4")
  });
  await expect(page.getByText(/Use JPEG, PNG, or WebP/i)).toBeVisible();

  await photoInput.setInputFiles({
    name: "spoofed-id.jpg",
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-1.4")
  });
  await expect(page.getByText(/Use JPEG, PNG, or WebP/i)).toBeVisible();

  await photoInput.setInputFiles({
    name: "abby-profile.webp",
    mimeType: "image/webp",
    buffer: Buffer.from("profile image placeholder")
  });
  await expect(page.getByRole("button", { name: "See preview", exact: true })).toBeVisible();
  await expect(page.getByAltText(/Profile upload preview/i)).toHaveCount(0);
  await page.getByRole("button", { name: "See preview", exact: true }).click();
  await expect(page.getByAltText(/Profile upload preview/i)).toHaveCount(1);
  await page.getByRole("button", { name: "Hide preview", exact: true }).click();
  await expect(page.getByAltText(/Profile upload preview/i)).toHaveCount(0);
});

test("registration staff draft persists without keeping the PIN", async ({ page }) => {
  await openRoute(page, "register");
  await page.getByLabel(/I am shelter staff/i).check();
  await page.locator("select").first().selectOption("Rose City Shelter");
  await page.getByLabel(/Shelter staff PIN/i).fill("1234");

  await page.waitForFunction(() => {
    const raw = window.localStorage.getItem("abby-ui-state-v1");
    if (!raw) return false;
    const state = JSON.parse(raw);
    return (
      state.registrationStaffDraft?.isShelterStaff === true &&
      state.registrationStaffDraft?.selectedShelter === "Rose City Shelter"
    );
  });

  await reloadRoute(page, "register");
  await expect(page.getByLabel(/I am shelter staff/i)).toBeChecked();
  await expect(page.locator("select").first()).toHaveValue("Rose City Shelter");
  await expect(page.getByLabel(/Shelter staff PIN/i)).toHaveValue("");
});

test("shelter portal is gated until staff PIN verification succeeds", async ({ page }, testInfo) => {
  const isMobile = /Mobile/i.test(testInfo.project.name);
  await openRoute(page, "home");
  await expectShelterNavItem(page, false, isMobile);

  await openRoute(page, "shelter");
  await expect(page.getByRole("heading", { name: /Staff verification required/i })).toBeVisible();

  await openRoute(page, "register");
  await expect(page.getByLabel(/Shelter staff PIN/i)).toHaveCount(0);
  await expect(page.locator("select")).toHaveCount(0);
  await page.getByLabel(/I am shelter staff/i).check();
  await expect(page.locator("select").first()).toBeVisible();
  await expect(page.getByLabel(/Shelter staff PIN/i)).toBeVisible();

  await page.getByRole("button", { name: /Verify shelter staff/i }).click();
  await expect(page.getByText(/missing_shelter/i)).toBeVisible();

  await page.locator("select").first().selectOption("Rose City Shelter");
  await page.getByRole("button", { name: /Verify shelter staff/i }).click();
  await expect(page.getByText(/missing_pin/i)).toBeVisible();

  await page.getByLabel(/Shelter staff PIN/i).fill("9999");
  await page.getByRole("button", { name: /Verify shelter staff/i }).click();
  await expect(page.getByText(/wrong_pin/i)).toBeVisible();

  await openRoute(page, "shelter");
  await expect(page.getByRole("heading", { name: /Staff verification required/i })).toBeVisible();

  await verifyRoseShelterStaff(page);
  await openRoute(page, "home");
  await expectShelterNavItem(page, true, isMobile);
  await openRoute(page, "shelter");
  await expect(page.getByRole("heading", { name: /Assisted access/i })).toBeVisible();
});

test("shelter admin tools require the admin PIN and manage staff accounts", async ({ page }) => {
  await seedShelterStaffIsolationFixture(page);
  await verifyRoseShelterStaff(page);
  await openRoute(page, "shelter");

  await page.getByLabel(/Administrator PIN/i).fill("0000");
  await page.getByRole("button", { name: /Unlock administrator tools/i }).click();
  await expect(page.getByText(/invalid_pin/i)).toBeVisible();
  await expect(page.getByRole("heading", { name: /Staff PIN management/i })).toHaveCount(0);

  await page.getByLabel(/Administrator PIN/i).fill("9001");
  await page.getByRole("button", { name: /Unlock administrator tools/i }).click();
  await expect(page.getByText(/administrator tools unlocked/i)).toBeVisible();
  await expect(page.getByRole("heading", { name: /Staff PIN management/i })).toBeVisible();

  let staffAccounts = page.locator('section[aria-labelledby="Staff-accounts"]');
  await expect(staffAccounts.getByText(/Riley Carter/i)).toBeVisible();
  await expect(staffAccounts.getByText(/Hidden Harbor/i)).toHaveCount(0);

  await page.getByLabel(/New staff PIN/i).fill("7777");
  await page.getByRole("button", { name: /Save staff PIN/i }).click();
  await expect(page.getByText(/Staff PIN changed/i)).toBeVisible();
  await page.waitForFunction(() => {
    const raw = window.localStorage.getItem("abby-ui-state-v1");
    if (!raw) return false;
    const state = JSON.parse(raw);
    return state.shelterPinConfigs?.some(
      (config: { shelter?: string; staffPin?: string }) =>
        config.shelter === "Rose City Shelter" && config.staffPin === "7777"
    );
  });
  const savedPinUpdatedAt = await page.evaluate(() => {
    const state = JSON.parse(window.localStorage.getItem("abby-ui-state-v1") ?? "{}");
    return state.shelterPinConfigs?.find((config: { shelter?: string }) => config.shelter === "Rose City Shelter")
      ?.updatedAt;
  });
  await page.getByRole("button", { name: /Rotate staff PIN for all staff/i }).click();
  await expect(page.getByText(/Staff PIN rotated/i)).toBeVisible();
  await page.waitForFunction((previousUpdatedAt) => {
    const raw = window.localStorage.getItem("abby-ui-state-v1");
    if (!raw) return false;
    const state = JSON.parse(raw);
    return state.shelterPinConfigs?.some(
      (config: { shelter?: string; staffPin?: string; updatedAt?: string }) =>
        config.shelter === "Rose City Shelter" &&
        config.updatedAt !== previousUpdatedAt &&
        /^\d{4}$/.test(config.staffPin ?? "")
    );
  }, savedPinUpdatedAt);

  await page.getByLabel(/Staff name/i).fill("Dana Admin");
  await page.getByLabel(/Staff email/i).fill("dana.staff@example.org");
  await page.getByRole("button", { name: /^Create staff account$/i }).click();
  await expect(page.getByText(/Staff account created/i)).toBeVisible();

  staffAccounts = page.locator('section[aria-labelledby="Staff-accounts"]');
  const staffAccount = staffAccounts.locator(".list-item").filter({ hasText: "Dana Admin" });
  await expect(staffAccount).toBeVisible();
  await expect(staffAccount.getByText(/Revoked/i)).toBeVisible();
  await staffAccount.getByRole("button", { name: /Re-verify/i }).click();
  await expect(page.getByText(/Staff verification updated/i)).toBeVisible();
  await expect(staffAccount.getByText(/Verified/i)).toBeVisible();
  await staffAccount.getByRole("button", { name: /Delete staff account/i }).click();
  await staffAccount.getByRole("button", { name: /Confirm delete/i }).click();
  await expect(page.getByText(/Staff account deleted/i)).toBeVisible();
  await expect(staffAccount).toHaveCount(0);

  await reloadRoute(page, "shelter");
  await page.getByLabel(/Administrator PIN/i).fill("9001");
  await page.getByRole("button", { name: /Unlock administrator tools/i }).click();
  staffAccounts = page.locator('section[aria-labelledby="Staff-accounts"]');
  await expect(staffAccounts.getByText(/Dana Admin/i)).toHaveCount(0);
  await expect(staffAccounts.getByText(/Hidden Harbor/i)).toHaveCount(0);
});

test("verified shelter staff can create a client account that persists after reload", async ({ page }) => {
  await verifyRoseShelterStaff(page);
  await openRoute(page, "shelter");

  await page.getByLabel(/Legal or full name/i).fill("Casey Client");
  await page.getByLabel(/Preferred name/i).fill("Casey");
  await page.getByLabel(/Birth date/i).fill("1991-03-14");
  await page.getByLabel(/Photo or photo ID/i).setInputFiles({
    name: "casey-client.png",
    mimeType: "image/png",
    buffer: Buffer.from("profile image placeholder")
  });
  await expect(page.getByRole("button", { name: "See preview", exact: true })).toBeVisible();
  await expect(page.getByAltText(/Client upload preview/i)).toHaveCount(0);
  await page.getByRole("button", { name: "See preview", exact: true }).click();
  await expect(page.getByAltText(/Client upload preview/i)).toHaveCount(1);
  await page.getByRole("button", { name: "Hide preview", exact: true }).click();
  await expect(page.getByAltText(/Client upload preview/i)).toHaveCount(0);
  await page.getByRole("button", { name: /Mark health check follow-up/i }).click();
  await page.getByLabel(/Bot check complete/i).check();
  await page.getByRole("button", { name: /^Create user account$/i }).click();

  const recentAccounts = page.locator('section[aria-labelledby="Recently-created-client-accounts"]');
  const caseyAccount = recentAccounts.locator(".list-item").filter({ hasText: "Casey Client" });
  await expect(caseyAccount).toHaveCount(1);
  await expect(caseyAccount.getByRole("heading", { name: "Casey", exact: true })).toBeVisible();
  await expect(caseyAccount.getByText("Casey Client", { exact: true })).toBeVisible();
  await expect(caseyAccount.getByText(/Health check/i)).toBeVisible();
  const oversight = page.locator('section[aria-labelledby="Shelter-user-oversight"]');
  const caseyOversight = oversight.locator(".list-stack").first().locator(".list-item").filter({ hasText: "Casey Client" });
  await expect(caseyOversight.getByText(/Health check/i)).toBeVisible();

  await reloadRoute(page, "shelter");
  await expect(caseyAccount).toHaveCount(1);
  await expect(caseyAccount.getByRole("heading", { name: "Casey", exact: true })).toBeVisible();
  await expect(caseyAccount.getByText("Casey Client", { exact: true })).toBeVisible();
  await expect(caseyAccount.getByText(/Health check/i)).toBeVisible();
  await expect(caseyOversight.getByText(/Health check/i)).toBeVisible();
});

test("shelter oversight separates staff-created users from preferred-shelter mentions", async ({ page }) => {
  await verifyRoseShelterStaff(page);
  await openRoute(page, "shelter");

  const oversight = page.locator('section[aria-labelledby="Shelter-user-oversight"]');
  const staffCreatedNames = oversight.locator(".list-stack").first().locator("article.list-item h3");
  await expect(staffCreatedNames).toHaveText(["Ari", "Jordan", "Sam"]);
  await expect(oversight.getByText(/Preferred-shelter mentions/i)).toBeVisible();
  await expect(oversight.getByRole("heading", { name: "Taylor", exact: true })).toBeVisible();
  await expect(oversight.getByText(/Health check/i).first()).toBeVisible();
  await expect(oversight.getByText(/Found housing/i)).toBeVisible();
});

test("shelter health-check tags stay limited to shelter-related failed bot checks", async ({ page }) => {
  await seedShelterHealthCheckFixture(page);
  await verifyRoseShelterStaff(page);
  await openRoute(page, "shelter");

  const oversight = page.locator('section[aria-labelledby="Shelter-user-oversight"]');
  const staffCreatedList = oversight.locator(".list-stack").first();
  const preferredList = oversight.locator(".list-stack").nth(1);

  await expect(staffCreatedList.getByText(/No Shelter Followup/i)).toHaveCount(0);

  const preferredFollowup = preferredList.locator(".list-item").filter({ hasText: "Priya Followup" });
  await expect(preferredFollowup.getByText(/Health check/i)).toBeVisible();

  const preferredPassed = preferredList.locator(".list-item").filter({ hasText: "Pat Passed" });
  await expect(preferredPassed).toBeVisible();
  await expect(preferredPassed.getByText(/Health check/i)).toHaveCount(0);
});

test("check-in interval cannot exceed thirty days", async ({ page }) => {
  await openRoute(page, "check-in");
  const interval = page.getByLabel(/Interval days/i);
  await interval.fill("45");
  await expect(interval).toHaveValue("30");
});

test("check-in presets and missed-check-in grace explanation update together", async ({ page }) => {
  await openRoute(page, "check-in");
  await page.getByRole("button", { name: "14 days" }).click();
  await expect(page.getByLabel(/Interval days/i)).toHaveValue("14");
  await page.getByLabel(/Grace period hours/i).fill("6");
  await expect(page.getByText(/Abby keeps reminders active for 6 hours/i)).toBeVisible();
  await expect(page.getByRole("button", { name: "14 days" })).toHaveAttribute("aria-pressed", "true");
});

test("home check-in card routes to check-in setup", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /Check in now/i }).click();
  await expect(page).toHaveURL(/#\/check-in$/);
  await expect(page.getByRole("heading", { name: /Set your schedule/i })).toBeVisible();
});

test("hash navigation updates the active screen without a full reload", async ({ page }) => {
  await openRoute(page, "home");
  await page.evaluate(() => {
    window.location.hash = "#/contacts";
  });
  await expect(page.getByRole("heading", { name: /People and services/i })).toBeVisible();
  await page.evaluate(() => {
    window.location.hash = "#/analytics";
  });
  await expect(page.getByRole("heading", { name: /Share patterns/i })).toBeVisible();
});

test("mobile menu opens navigation and routes to contacts", async ({ page }, testInfo) => {
  test.skip(!/Mobile/i.test(testInfo.project.name), "Mobile navigation is hidden on desktop layouts");
  await openRoute(page, "home");
  await page.getByRole("button", { name: /Open menu/i }).click();
  const mobileNav = page.getByRole("navigation", { name: /Mobile navigation/i });
  await expect(mobileNav).toBeVisible();
  await mobileNav.getByRole("button", { name: /Contacts/i }).click();
  await expect(page.getByRole("heading", { name: /People and services/i })).toBeVisible();
  await expect(mobileNav).not.toBeVisible();
});

test("contact type dropdown exposes supported recipient domains", async ({ page }) => {
  await openRoute(page, "contacts");
  const typeSelect = page.getByLabel(/Type/i);
  await expect(typeSelect).toBeVisible();

  const optionValues = await typeSelect.locator("option").evaluateAll((options) =>
    options.map((option) => option.getAttribute("value") ?? "")
  );

  for (const value of [
    "emergency_contact",
    "social_worker",
    "police_precinct",
    "shelter_staff",
    "government_liaison",
    "benefits_agency"
  ]) {
    expect(optionValues).toContain(value);
  }
});

test("contact rows support edit, scope review, and removal", async ({ page }) => {
  await openRoute(page, "contacts");
  await page.getByLabel(/Name or agency/i).fill("Jordan Helper");
  await page.getByLabel(/Relationship or role/i).fill("Friend");
  await page.getByRole("button", { name: /Add recipient/i }).click();

  const recipient = page.locator(".recipient-list-item").filter({ hasText: "Jordan Helper" });
  await expect(recipient).toBeVisible();
  await recipient.getByRole("button", { name: /Edit Jordan Helper/i }).click();
  await page.getByLabel(/Relationship or role/i).fill("Outreach helper");
  await page.getByRole("button", { name: /Save recipient/i }).click();
  await expect(recipient.getByText("Outreach helper")).toBeVisible();

  await recipient.getByRole("button", { name: /Review scopes for Jordan Helper/i }).click();
  await expect(page.getByRole("heading", { name: /Choose what each person can see/i })).toBeVisible();

  await openRoute(page, "contacts");
  const reloadedRecipient = page.locator(".recipient-list-item").filter({ hasText: "Jordan Helper" });
  await reloadedRecipient.getByRole("button", { name: /Remove Jordan Helper/i }).click();
  await expect(reloadedRecipient).toHaveCount(0);
});

test("agency escalation recipients can be added with domain-specific fields", async ({ page }) => {
  await openRoute(page, "contacts");
  await page.getByLabel(/Type/i).selectOption("police_precinct");
  await page.getByLabel(/Name or agency/i).fill("Central Precinct desk");
  await page.getByLabel(/Relationship or role/i).fill("Local safety desk");
  await page.getByLabel(/Precinct name/i).fill("Central Precinct");
  await page.getByRole("button", { name: /Add recipient/i }).click();

  const precinct = page.locator(".recipient-list-item").filter({ hasText: "Central Precinct desk" });
  await expect(precinct.getByText("Police precinct")).toBeVisible();
  await expect(precinct.locator(".recipient-details span").filter({ hasText: /^Central Precinct$/ })).toBeVisible();
  await expect(precinct.locator(".badge").filter({ hasText: "Review required" })).toBeVisible();
  await expect(precinct.getByText(/Can access: Minimum identity, Photo/i)).toBeVisible();
});

test("contact rows track phone and email verification separately", async ({ page }) => {
  await openRoute(page, "contacts");
  await page.getByLabel(/Name or agency/i).fill("Morgan Verifier");
  await page.getByLabel(/Relationship or role/i).fill("Outreach case worker");
  await page.getByLabel("Phone", { exact: true }).fill("(503) 555-0188");
  await page.getByLabel("Email", { exact: true }).fill("morgan@example.org");
  await page.getByLabel(/Type/i).selectOption("social_worker");
  await page.getByLabel(/Agency or service/i).fill("Downtown Outreach");
  await page.getByRole("button", { name: /Add recipient/i }).click();

  const recipient = page.locator(".recipient-list-item").filter({ hasText: "Morgan Verifier" });
  await expect(recipient.getByText(/Phone needs verification/i)).toBeVisible();
  await expect(recipient.getByText(/Email needs verification/i)).toBeVisible();

  await recipient.getByRole("button", { name: /Verify phone/i }).click();
  await expect(recipient.getByText(/Phone verified/i)).toBeVisible();
  await expect(recipient.getByText(/Email needs verification/i)).toBeVisible();

  await recipient.getByRole("button", { name: /Verify email/i }).click();
  await expect(recipient.getByText(/Recipient verified/i)).toBeVisible();
  await expect(recipient.getByText(/Email verified/i)).toBeVisible();

  await recipient.getByRole("button", { name: /Edit Morgan Verifier/i }).click();
  await page.getByLabel("Phone", { exact: true }).fill("(503) 555-0199");
  await page.getByRole("button", { name: /Save recipient/i }).click();
  await expect(recipient.getByText(/Needs method verification/i)).toBeVisible();
  await expect(recipient.getByText(/Phone needs verification/i)).toBeVisible();
  await expect(recipient.getByText(/Email verified/i)).toBeVisible();
});

test("contact rows reorder and warn before removing the last active recipient", async ({ page }) => {
  await openRoute(page, "contacts");
  await page
    .locator(".recipient-list-item")
    .filter({ hasText: "Case Worker Desk" })
    .getByRole("button", { name: /Move Case Worker Desk up/i })
    .click();
  await expect(page.locator(".recipient-list-item h3").first()).toHaveText("Case Worker Desk");

  await reloadRoute(page, "contacts");
  await expect(page.locator(".recipient-list-item h3").first()).toHaveText("Case Worker Desk");

  await page.evaluate(() => {
    window.localStorage.setItem(
      "abby-ui-state-v1",
      JSON.stringify({
        recipients: [
          {
            id: "solo-recipient",
            type: "emergency_contact",
            displayName: "Solo Helper",
            relationship: "Friend",
            email: "solo@example.org",
            phone: "(503) 555-0101",
            agencyName: "",
            precinctName: "",
            verified: true,
            emailVerificationStatus: "verified",
            phoneVerificationStatus: "verified",
            allowedScopes: ["identity_minimum", "photo"],
            emergencyDisclosureEnabled: true,
            sharingHistory: []
          }
        ]
      })
    );
  });
  await reloadRoute(page, "contacts");

  const solo = page.locator(".recipient-list-item").filter({ hasText: "Solo Helper" });
  await solo.getByRole("button", { name: /Remove Solo Helper/i }).click();
  await expect(solo.getByText(/leaves no active emergency recipient/i)).toBeVisible();
  await expect(solo).toHaveCount(1);
  await solo.getByRole("button", { name: /Confirm remove Solo Helper/i }).click();
  await expect(solo).toHaveCount(0);
});

test("analytics consent shows privacy controls and derived fields", async ({ page }) => {
  await openRoute(page, "analytics");
  await expect(page.getByRole("heading", { name: /Share patterns/i })).toBeVisible();
  const housingStudy = page.getByRole("article", { name: /Housing service gaps/i });
  await expect(housingStudy.getByText(/Minimum cohort/i)).toBeVisible();
  await expect(housingStudy.getByText(/Budget left/i)).toBeVisible();
  await expect(housingStudy.getByText("county", { exact: true })).toBeVisible();
});

test("security settings persist across reloads", async ({ page }) => {
  await openRoute(page, "security");
  await expect(page.getByRole("heading", { name: /Account safety/i })).toBeVisible();

  await page.getByLabel(/Send recovery reminder prompts/i).check();
  await page.getByLabel(/Require bot checks on public forms/i).uncheck();
  await page.getByLabel(/Show passkey or device-key placeholders/i).check();
  await reloadRoute(page, "security");

  await expect(page.getByLabel(/Send recovery reminder prompts/i)).toBeChecked();
  await expect(page.getByLabel(/Require bot checks on public forms/i)).not.toBeChecked();
  await expect(page.getByLabel(/Show passkey or device-key placeholders/i)).toBeChecked();
  await expect(page.getByText(/Email or wallet sign-in placeholder/i)).toBeVisible();
  await expect(page.getByText(/trusted devices securely/i)).toBeVisible();
});

test("design system foundation exposes tokens, reveal, loading, and responsive breakpoints", async ({ page }) => {
  await page.setViewportSize({ width: 500, height: 900 });
  await openRoute(page, "security");

  const mobileTokens = await page.evaluate(() => {
    const style = window.getComputedStyle(document.documentElement);
    return {
      mobile: style.getPropertyValue("--abby-breakpoint-mobile").trim(),
      tablet: style.getPropertyValue("--abby-breakpoint-tablet").trim(),
      desktop: style.getPropertyValue("--abby-breakpoint-desktop").trim(),
      active: style.getPropertyValue("--abby-active-breakpoint").trim(),
      focus: style.getPropertyValue("--abby-color-focus").trim()
    };
  });

  expect(mobileTokens).toEqual({
    mobile: "320px",
    tablet: "640px",
    desktop: "760px",
    active: "mobile",
    focus: "#0f766e"
  });

  await page.setViewportSize({ width: 700, height: 900 });
  await reloadRoute(page, "security");
  await expect
    .poll(() => page.evaluate(() => window.getComputedStyle(document.documentElement).getPropertyValue("--abby-active-breakpoint").trim()))
    .toBe("tablet");

  await page.setViewportSize({ width: 900, height: 900 });
  await reloadRoute(page, "security");
  await expect
    .poll(() => page.evaluate(() => window.getComputedStyle(document.documentElement).getPropertyValue("--abby-active-breakpoint").trim()))
    .toBe("desktop");

  await expect(page.getByLabel("Recovery contact redacted")).toHaveText("m***@example.org");
  await expect(page.getByText(/Copy disabled/i)).toBeVisible();
  await page.getByRole("button", { name: /Reveal Recovery contact/i }).click();
  await expect(page.getByLabel("Recovery contact revealed")).toHaveText("maya@example.org");
  await expect(page.getByRole("list", { name: /Secure reveal steps/i })).toBeVisible();

  await page.getByRole("button", { name: /Check recovery route/i }).click();
  await expect(page.getByRole("button", { name: /Checking recovery route/i })).toBeDisabled();
  await expect(page.getByRole("status").filter({ hasText: /Checking recovery route/i })).toBeVisible();
});

test("core mobile touch targets stay at least forty four pixels tall", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await openRoute(page, "contacts");

  const undersizedContactsButtons = await page.locator("button").evaluateAll((buttons) =>
    buttons
      .filter((button) => {
        const style = window.getComputedStyle(button);
        const box = button.getBoundingClientRect();
        return style.display !== "none" && style.visibility !== "hidden" && box.width > 0 && box.height > 0;
      })
      .map((button) => ({
        label: button.getAttribute("aria-label") || button.textContent?.trim() || "unlabeled",
        height: button.getBoundingClientRect().height
      }))
      .filter((button) => button.height < 44)
  );
  expect(undersizedContactsButtons).toEqual([]);

  await openRoute(page, "register");
  const undersizedRegisterButtons = await page.locator("button").evaluateAll((buttons) =>
    buttons
      .filter((button) => {
        const style = window.getComputedStyle(button);
        const box = button.getBoundingClientRect();
        return style.display !== "none" && style.visibility !== "hidden" && box.width > 0 && box.height > 0;
      })
      .map((button) => ({
        label: button.getAttribute("aria-label") || button.textContent?.trim() || "unlabeled",
        height: button.getBoundingClientRect().height
      }))
      .filter((button) => button.height < 44)
  );
  expect(undersizedRegisterButtons).toEqual([]);
});

test("core submitted preferences persist across reloads", async ({ page }) => {
  await openRoute(page, "check-in");
  await page.getByLabel(/Interval days/i).fill("12");
  await page.getByRole("button", { name: "EMAIL" }).click();
  await reloadRoute(page, "check-in");
  await expect(page.getByLabel(/Interval days/i)).toHaveValue("12");
  await expect(page.getByRole("button", { name: "EMAIL" })).toHaveAttribute("aria-pressed", "true");

  await openRoute(page, "register");
  await page.getByLabel(/I am shelter staff/i).check();
  await page.locator("select").first().selectOption("Rose City Shelter");
  await page.getByLabel(/Shelter staff PIN/i).fill("1234");
  await page.getByRole("button", { name: /Verify shelter staff/i }).click();
  await expect(page.getByText(/verified_staff/i)).toBeVisible();

  await openRoute(page, "shelter");
  await page.getByLabel(/Confirm user is present/i).check();
  await page.getByLabel(/Clear browser data/i).check();
  await reloadRoute(page, "shelter");
  await expect(page.getByLabel(/Confirm user is present/i)).toBeChecked();
  await expect(page.getByLabel(/Clear browser data/i)).toBeChecked();

  await openRoute(page, "benefits-protection");
  await page.getByLabel(/Allow Abby to prepare/i).check();
  await reloadRoute(page, "benefits-protection");
  await expect(page.getByLabel(/Allow Abby to prepare/i)).toBeChecked();

  await openRoute(page, "analytics");
  const housingStudy = page.getByRole("article", { name: /Housing service gaps/i });
  await housingStudy.getByRole("checkbox").check();
  await reloadRoute(page, "analytics");
  await expect(page.getByRole("article", { name: /Housing service gaps/i }).getByRole("checkbox")).toBeChecked();
});

test("sharing rules default to minimum identity and photo, then persist custom empty scopes", async ({ page }) => {
  await openRoute(page, "contacts");
  await page.getByLabel(/Name or agency/i).fill("Jordan Default");
  await page.getByRole("button", { name: /Add recipient/i }).click();

  await setRoute(page, "sharing-rules");
  const editor = page.locator(".scope-editor").filter({ hasText: "Jordan Default" });
  await expect(editor.getByRole("checkbox", { name: /Minimum identity/i })).toBeChecked();
  await expect(editor.getByRole("checkbox", { name: /^Photo/i })).toBeChecked();

  await editor.getByRole("checkbox", { name: /Minimum identity/i }).uncheck();
  await editor.getByRole("checkbox", { name: /^Photo/i }).uncheck();
  await expect(editor.getByText(/0 selected/i)).toBeVisible();
  await page.waitForFunction(() => {
    const raw = window.localStorage.getItem("abby-ui-state-v1");
    if (!raw) return false;
    const state = JSON.parse(raw);
    return state.recipients?.some(
      (recipient: { displayName?: string; allowedScopes?: string[]; sharingRuleCustomized?: boolean }) =>
        recipient.displayName === "Jordan Default" &&
        recipient.sharingRuleCustomized === true &&
        Array.isArray(recipient.allowedScopes) &&
        recipient.allowedScopes.length === 0
    );
  });

  await reloadRoute(page, "sharing-rules");
  const reloadedEditor = page.locator(".scope-editor").filter({ hasText: "Jordan Default" });
  await expect(reloadedEditor).toBeVisible();
  await expect(reloadedEditor.getByRole("checkbox", { name: /Minimum identity/i })).not.toBeChecked();
  await expect(reloadedEditor.getByRole("checkbox", { name: /^Photo/i })).not.toBeChecked();
});

test("sharing rules include missed check-in and housing scopes that persist", async ({ page }) => {
  await openRoute(page, "contacts");
  await page.getByLabel(/Name or agency/i).fill("Taylor Scope");
  await page.getByRole("button", { name: /Add recipient/i }).click();

  await setRoute(page, "sharing-rules");
  const editor = page.locator(".scope-editor").filter({ hasText: "Taylor Scope" });
  await expect(editor.getByRole("checkbox", { name: /Missed check-in/i })).not.toBeChecked();
  await expect(editor.getByRole("checkbox", { name: /Found permanent housing/i })).not.toBeChecked();

  await editor.getByRole("checkbox", { name: /Missed check-in/i }).check();
  await editor.getByRole("checkbox", { name: /Found permanent housing/i }).check();
  await expect(editor.getByText(/4 selected/i)).toBeVisible();
  await page.waitForFunction(() => {
    const raw = window.localStorage.getItem("abby-ui-state-v1");
    if (!raw) return false;
    const state = JSON.parse(raw);
    const recipient = state.recipients?.find(
      (item: { displayName?: string }) => item.displayName === "Taylor Scope"
    );
    return (
      recipient?.allowedScopes?.includes("missed_check_in") &&
      recipient?.allowedScopes?.includes("found_permanent_housing") &&
      recipient?.sharingRuleCustomized === true
    );
  });

  await reloadRoute(page, "sharing-rules");
  const reloadedEditor = page.locator(".scope-editor").filter({ hasText: "Taylor Scope" });
  await expect(reloadedEditor).toBeVisible();
  await expect(reloadedEditor.getByRole("checkbox", { name: /Missed check-in/i })).toBeChecked();
  await expect(reloadedEditor.getByRole("checkbox", { name: /Found permanent housing/i })).toBeChecked();
});

test("sharing rules require confirmation before emergency disclosure and support revocation history", async ({ page }) => {
  await openRoute(page, "contacts");
  await page.getByLabel(/Name or agency/i).fill("Robin Review");
  await page.getByRole("button", { name: /Add recipient/i }).click();

  await setRoute(page, "sharing-rules");
  const editor = page.locator(".scope-editor").filter({ hasText: "Robin Review" });
  await expect(editor.locator(".badge").filter({ hasText: "Review required" })).toBeVisible();
  await editor.getByRole("button", { name: /Confirm emergency disclosure/i }).click();
  await expect(editor.locator(".badge").filter({ hasText: "Emergency disclosure enabled" })).toBeVisible();
  await expect(editor.locator(".history-list").getByText(/Emergency disclosure confirmed/i)).toBeVisible();
  await editor.getByRole("button", { name: /Revoke disclosure/i }).click();
  await expect(editor.locator(".badge").filter({ hasText: "Disclosure revoked" })).toBeVisible();
  await expect(editor.locator(".history-list").getByText(/Emergency disclosure revoked/i)).toBeVisible();
});

test("social services can use consented profile needs and guided intake for matching", async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem(
      "abby-ui-state-v1",
      JSON.stringify({
        profile: {
          legalName: "",
          preferredName: "",
          pronouns: "",
          dateOfBirth: "",
          photoAssetId: "",
          phone: "",
          email: "",
          currentLocation: "",
          preferredShelter: "",
          serviceNeeds: ["Benefits"],
          preferredCheckInChannels: ["web"],
          easyBotCheckStatus: "pending",
          captchaToken: ""
        }
      })
    );
  });

  await openRoute(page, "social-services");
  await expect(page.getByText(/Emergency shelter intake/i)).toBeVisible();
  await page.locator(".category-grid").getByRole("button", { name: "Health" }).click();
  await page.getByLabel(/Use my selected service needs/i).check();
  await expect(page.getByText(/Benefits navigation clinic/i)).toBeVisible();
  await expect(page.getByText(/Mobile health outreach/i)).toBeVisible();
  await expect(page.getByText(/Emergency shelter intake/i)).toHaveCount(0);
});

test("text uploads receive a short generated title that persists after reload", async ({ page }) => {
  await openRoute(page, "uploads");
  await page.getByLabel(/Category/i).selectOption("Benefits");
  await page.getByLabel(/Sensitivity/i).selectOption("restricted");
  await expect(page.getByLabel(/Take photo to upload/i)).toHaveAttribute("capture", "environment");
  await page.getByLabel(/Choose file to upload/i).setInputFiles({
    name: "rental-note.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("Rental assistance approval letter for May 2026")
  });

  const upload = page.locator(".upload-list-item").filter({ hasText: "rental-note.txt" });
  await expect(upload.getByText("Rental Assistance Approval Letter")).toBeVisible();
  await expect(upload.getByText("Benefits")).toBeVisible();
  await expect(upload.getByText("restricted")).toBeVisible();
  await upload.getByRole("button", { name: /Mark eligible/i }).click();
  await expect(upload.getByText("Sharing eligible")).toBeVisible();

  await reloadRoute(page, "uploads");
  await expect(upload.getByText("Rental Assistance Approval Letter")).toBeVisible();
  await expect(upload.getByText("Sharing eligible")).toBeVisible();
});

test("unsupported uploads fall back to a filename title", async ({ page }) => {
  await openRoute(page, "uploads");
  await page.getByLabel(/Choose file to upload/i).setInputFiles({
    name: "medical-card-backup.bin",
    mimeType: "application/octet-stream",
    buffer: Buffer.from("not text or image")
  });

  const upload = page.locator(".upload-list-item").filter({ hasText: "medical-card-backup.bin" });
  await expect(upload.getByText("Medical Card Backup")).toBeVisible();
  await expect(upload.getByText("Filename fallback")).toBeVisible();
});

test("image uploads receive a short fallback title when OCR has no text", async ({ page }) => {
  await openRoute(page, "uploads");
  await page.getByLabel(/Choose file to upload/i).setInputFiles({
    name: "clinic-card-front.png",
    mimeType: "image/png",
    buffer: Buffer.from("iVBORw0KGgo=", "base64")
  });

  const upload = page.locator(".upload-list-item").filter({ hasText: "clinic-card-front.png" });
  await expect(upload.getByText("Clinic Card Front")).toBeVisible();
  await expect(upload.getByText("Filename fallback")).toBeVisible();
});

test("failed upload extraction falls back to a filename title with a failed summary state", async ({ page }) => {
  await openRoute(page, "uploads");
  await page.getByLabel(/Choose file to upload/i).setInputFiles({
    name: "broken-vault.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("")
  });

  const upload = page.locator(".upload-list-item").filter({ hasText: "broken-vault.pdf" });
  await expect(upload.getByText("Broken Vault")).toBeVisible({ timeout: 10000 });
  await expect(upload.getByText("Summary failed")).toBeVisible();
  await expect(upload.getByText("failed", { exact: true })).toBeVisible();
  await expect(upload.getByRole("button", { name: /Mark eligible/i })).toBeDisabled();
  await upload.getByRole("button", { name: /Retry/i }).click();
  await expect(upload.getByText("stored", { exact: true })).toBeVisible();
  await expect(upload.getByText("Filename fallback")).toBeVisible();
  await upload.getByRole("button", { name: /Remove/i }).click();
  await expect(upload).toHaveCount(0);
});

test("uploads screen shows an empty vault state", async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem("abby-ui-state-v1", JSON.stringify({ uploads: [] }));
  });
  await openRoute(page, "uploads");
  await expect(page.getByText(/No stored items yet/i)).toBeVisible();
});

test("recipient access requires multi-sig approval before decrypt sharing", async ({ page }) => {
  await openRoute(page, "recipient-access");
  const request = page.locator(".access-request-item").filter({ hasText: "Downtown Outreach" });
  await expect(request.getByText(/1\/2 approvals/i)).toBeVisible();
  await expect(request.getByRole("button", { name: /^Approve$/i })).toBeDisabled();
  await request.getByRole("button", { name: /Record approval/i }).click();
  await expect(request.getByText(/2\/2 approvals/i)).toBeVisible();
  await request.getByRole("button", { name: /^Approve$/i }).click();
  await expect(request.getByText("approved", { exact: true })).toBeVisible();
});

test("recipient secure link hides data before verification, shows only authorized scopes, and handles expiry", async ({ page }) => {
  await openRoute(page, "recipient-access");
  await expect(page.getByText(/Sensitive information is hidden/i)).toBeVisible();
  await expect(page.getByText(/Expires Today/i).first()).toBeVisible();
  await page.getByLabel(/Access code/i).fill("123456");
  await page.getByLabel(/Recipient phone or email/i).fill("maya@example.org");
  await page.getByRole("button", { name: /Verify and view/i }).click();
  await expect(page.getByRole("heading", { name: /Authorized for Maya Johnson/i })).toBeVisible();
  await expect(page.getByText(/Minimum identity/i)).toBeVisible();
  await expect(page.getByText(/Medical notes/i)).toHaveCount(0);
  await expect(page.getByText(/Contact user or shelter/i)).toBeVisible();
  await page.getByRole("button", { name: /Simulate expired link/i }).click();
  await expect(page.getByText(/expired-link recovery required/i)).toBeVisible();
  await expect(page.getByRole("button", { name: /Verify and view/i })).toBeDisabled();
  await expect(page.getByLabel(/Access code/i)).toHaveAttribute("aria-invalid", "true");
  await expect(page.getByRole("alert")).toContainText(/Request a new secure link/i);
});

test("benefits protection has consent review, revocation, and history", async ({ page }) => {
  await openRoute(page, "benefits-protection");
  await expect(page.getByText(/Minimum data only/i)).toBeVisible();
  await page.getByLabel(/Allow Abby to prepare/i).check();
  await expect(page.getByText(/Benefits preparation is enabled/i)).toBeVisible();
  await expect(page.getByRole("heading", { name: "Consent enabled" })).toBeVisible();
  await page.getByRole("button", { name: /Revoke benefits consent/i }).click();
  await expect(page.getByLabel(/Allow Abby to prepare/i)).not.toBeChecked();
  await expect(page.getByRole("heading", { name: "Consent revoked" })).toBeVisible();
});
