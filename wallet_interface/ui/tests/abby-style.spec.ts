import { expect, test, type Page } from "@playwright/test";

const appSessionKey = "abby-ui-session-v1";

async function signIn(page: Page) {
  await page.goto("/");
  await page.evaluate((key) => window.localStorage.setItem(key, JSON.stringify({ username: "style-reviewer" })), appSessionKey);
  await page.reload();
  await expect(page.getByRole("heading", { name: /Welcome to your safety plan!/i })).toBeVisible();
}

test("home screen uses ABBY watercolor styling and captures a review screenshot", async ({ page }, testInfo) => {
  await signIn(page);

  await expect(page.locator(".home-actions")).toBeVisible();
  await expect(page.getByRole("region", { name: /Need help today/i })).toBeVisible();

  const theme = await page.evaluate(() => {
    const root = getComputedStyle(document.documentElement);
    const hero = getComputedStyle(document.querySelector(".home-hero")!, "::after");
    const checkIn = getComputedStyle(document.querySelector(".checkin-panel")!);
    const support = getComputedStyle(document.querySelector(".support-card")!, "::after");
    return {
      fontFamily: root.getPropertyValue("--abby-font-family"),
      heroBackground: hero.backgroundImage,
      checkInBackground: checkIn.backgroundImage,
      supportBackground: support.backgroundImage
    };
  });

  expect(theme.fontFamily).not.toContain("Comic");
  expect(theme.heroBackground).toContain("preview-header-landscape.png");
  expect(theme.checkInBackground).toContain("preview-quick-action-wash.png");
  expect(theme.supportBackground).toContain("preview-support-bridge-watermark.png");

  await page.screenshot({ fullPage: true, path: testInfo.outputPath("abby-home-style.png") });
});

test("mobile navigation keeps the ABBY palette and current route set", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await signIn(page);
  await page.getByRole("button", { name: /Open menu/i }).click();

  const navigation = page.locator("#mobile-navigation");
  await expect(navigation.getByRole("button", { name: "Home", exact: true })).toBeVisible();
  await expect(navigation.getByRole("button", { name: "Register", exact: true })).toBeVisible();
  await expect(navigation.getByRole("button", { name: "Services", exact: true })).toBeVisible();
  await expect(navigation.getByRole("button", { name: "Who can see info", exact: true })).toHaveCount(0);
  await expect(navigation.getByRole("button", { name: "Benefits", exact: true })).toHaveCount(0);

  const activeRouteColor = await navigation
    .getByRole("button", { name: "Home", exact: true })
    .evaluate((node) => getComputedStyle(node).color);
  expect(activeRouteColor).toBe("rgb(15, 124, 115)");
});
