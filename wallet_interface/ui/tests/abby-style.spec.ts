import { expect, test } from "@playwright/test";

async function signIn(page: import("@playwright/test").Page) {
  await page.goto("/");
  await page.getByLabel(/username/i).fill("abby");
  await page.getByLabel(/password/i).fill("safety-plan");
  await page.getByRole("button", { name: /sign in/i }).click();
}

test("home screen uses ABBY watercolor styling and captures review screenshot", async ({ page }, testInfo) => {
  await signIn(page);

  await expect(page.getByRole("heading", { name: /Welcome to your safety plan!/i })).toBeVisible();
  const homeActions = page.locator(".home-actions");
  await expect(homeActions.getByRole("button", { name: /Contacts/i })).toBeVisible();
  await expect(homeActions.getByRole("button", { name: /Sharing/i })).toBeVisible();
  await expect(page.locator(".checkin-panel")).toBeVisible();
  await expect(page.getByRole("region", { name: /Need help today/i })).toBeVisible();

  const heroArtwork = await page.locator(".home-hero").evaluate((element) => {
    return window.getComputedStyle(element, "::after").backgroundImage;
  });
  expect(heroArtwork).toContain("preview-header-landscape.png");

  const supportArtwork = await page.locator(".support-card").evaluate((element) => {
    return window.getComputedStyle(element).backgroundImage;
  });
  expect(supportArtwork).toContain("preview-support-bridge-watermark.png");

  await page.screenshot({
    fullPage: true,
    path: testInfo.outputPath("abby-home-style.png")
  });
});
