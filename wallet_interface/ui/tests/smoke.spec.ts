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
  await expect(housingStudy.getByText(/Minimum cohort/i)).toBeVisible();
  await expect(housingStudy.getByText(/Budget left/i)).toBeVisible();
  await expect(housingStudy.getByText("county", { exact: true })).toBeVisible();
});

test("proof center shows public proof inputs without private coordinates", async ({ page }) => {
  await page.goto("/#/proof-center");
  await expect(page.getByRole("heading", { name: /Verified wallet claims/i })).toBeVisible();
  const regionProof = page.getByRole("article", { name: /Location is in service region/i });
  await expect(regionProof.getByText(/multnomah_county/i)).toBeVisible();
  await expect(regionProof.getByText(/location_in_region/i)).toBeVisible();
  await expect(regionProof.getByText(/Simulated/i)).toBeVisible();
  await expect(regionProof.getByText(/^lat$/i)).not.toBeVisible();
  await expect(regionProof.getByText(/^lon$/i)).not.toBeVisible();
});

test("exports show receipt hashes and storage status", async ({ page }) => {
  await page.goto("/#/exports");
  await expect(page.getByRole("heading", { name: /Shareable wallet bundles/i })).toBeVisible();
  await expect(page.getByRole("heading", { name: /Create export bundle/i })).toBeVisible();
  await expect(page.getByRole("button", { name: /Create bundle/i })).toBeDisabled();
  const legalAidExport = page.getByRole("article", { name: /Legal Aid desk/i });
  await expect(legalAidExport.getByText(/Bundle hash/i)).toBeVisible();
  await expect(legalAidExport.getByText(/storage verified/i)).toBeVisible();
  await expect(legalAidExport.getByText(/import verified/i)).toBeVisible();
  const benefitsExport = page.getByRole("article", { name: /Benefits navigation clinic/i });
  await expect(benefitsExport.getByText(/storage missing/i)).toBeVisible();
});

test("recipient access requires multi-sig approval before decrypt sharing", async ({ page }) => {
  await page.goto("/#/recipient-access");
  const request = page.locator(".access-request-item").filter({ hasText: "Downtown Outreach" });
  await expect(request.getByText(/1\/2 approvals/i)).toBeVisible();
  await expect(request.getByRole("button", { name: /^Approve$/i })).toBeDisabled();
  await request.getByRole("button", { name: /Record approval/i }).click();
  await expect(request.getByText(/2\/2 approvals/i)).toBeVisible();
  await request.getByRole("button", { name: /^Approve$/i }).click();
  await expect(request.getByText("approved", { exact: true })).toBeVisible();
  const receipt = page.getByRole("article", { name: /Downtown Outreach/i }).filter({ hasText: "Receipt hash" });
  await expect(receipt.getByText(/record\/decrypt/i)).toBeVisible();
  await expect(receipt.getByText(/active/i)).toBeVisible();
});

test("recipient access can revoke an active grant", async ({ page }) => {
  await page.goto("/#/recipient-access");
  const request = page.locator(".access-request-item").filter({ hasText: "Legal Aid desk" });
  await expect(request.getByText(/active grant/i)).toBeVisible();
  await request.getByRole("button", { name: /Revoke/i }).click();
  await expect(request.getByText("revoked", { exact: true })).toBeVisible();
  await expect(request.getByRole("button", { name: /Revoke/i })).toHaveCount(0);
  const receipt = page.getByRole("article", { name: /Legal Aid desk/i }).filter({ hasText: "Receipt hash" });
  await expect(receipt.getByText("revoked", { exact: true })).toBeVisible();
});
