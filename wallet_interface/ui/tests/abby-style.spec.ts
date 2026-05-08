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
    const brandMark = document.querySelector(".brand-mark");
    const hero = getComputedStyle(document.querySelector(".home-hero")!, "::after");
    const checkIn = getComputedStyle(document.querySelector(".checkin-panel")!);
    const support = getComputedStyle(document.querySelector(".support-card")!);
    return {
      fontFamily: root.getPropertyValue("--abby-font-family"),
      brandMarkBackground: brandMark
        ? getComputedStyle(brandMark).backgroundImage
        : root.getPropertyValue("--abby-logo-mark"),
      heroBackground: hero.backgroundImage,
      checkInBackground: checkIn.backgroundImage,
      supportBackground: support.backgroundImage
    };
  });

  expect(theme.fontFamily).not.toContain("Comic");
  expect(theme.brandMarkBackground).toContain("abby-logo-mark.svg");
  expect(theme.heroBackground).toContain("preview-header-landscape.png");
  expect(theme.checkInBackground).toContain("preview-quick-action-wash.png");
  expect(theme.supportBackground).toContain("preview-support-bridge-watermark.png");

  await page.screenshot({ fullPage: true, path: testInfo.outputPath("abby-home-style.png") });
});

test("login and inner route chrome use production ABBY assets", async ({ page }, testInfo) => {
  await page.goto("/");
  await expect(page.getByRole("button", { name: /Client portal/i })).toBeVisible();
  await expect(page.getByRole("button", { name: /Provider portal/i })).toBeVisible();

  const loginTheme = await page.evaluate(() => {
    const loginMark = getComputedStyle(document.querySelector(".login-mark")!);
    const loginPanel = getComputedStyle(document.querySelector(".login-panel")!);
    const favicon = document.querySelector<HTMLLinkElement>('link[rel="icon"]');
    return {
      loginMarkBackground: loginMark.backgroundImage,
      loginPanelBackground: loginPanel.backgroundImage,
      faviconHref: favicon?.getAttribute("href") ?? ""
    };
  });

  expect(loginTheme.loginMarkBackground).toContain("abby-logo-mark.svg");
  expect(loginTheme.loginPanelBackground).toContain("preview-support-bridge-watermark.png");
  expect(loginTheme.faviconHref).toContain("assets/favicon.svg");

  await page.screenshot({ fullPage: true, path: testInfo.outputPath("abby-login-style.png") });

  await signIn(page);
  await page.goto("/#/register");
  await expect(page.getByRole("heading", { name: /Create your Abby profile/i })).toBeVisible();

  const routeTheme = await page.evaluate(() => {
    const routeHeader = getComputedStyle(document.querySelector(".screen > .page-title")!, "::after");
    return {
      routeHeaderBackground: routeHeader.backgroundImage
    };
  });

  expect(routeTheme.routeHeaderBackground).toContain("preview-header-landscape.png");
});

test("mobile navigation keeps the ABBY palette and current route set", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await signIn(page);
  await page.getByRole("button", { name: /Open menu/i }).click();

  const menuButtonBox = await page.getByRole("button", { name: /Close menu/i }).boundingBox();
  expect(menuButtonBox?.width).toBeLessThanOrEqual(52);
  expect(menuButtonBox?.height).toBeLessThanOrEqual(52);

  const navigation = page.locator("#mobile-navigation");
  await expect(navigation.getByText("Client portal", { exact: true })).toBeVisible();
  await expect(navigation.getByText("Provider portal", { exact: true })).toBeVisible();
  await expect(navigation.getByText("Analytics tools", { exact: true })).toBeVisible();
  await expect(navigation.getByRole("button", { name: "Home", exact: true })).toBeVisible();
  await expect(navigation.getByRole("button", { name: "Register", exact: true })).toBeVisible();
  await expect(navigation.getByRole("button", { name: "Services", exact: true })).toBeVisible();
  await expect(navigation.getByRole("button", { name: "Shelter staff", exact: true })).toBeVisible();
  await expect(navigation.getByRole("button", { name: "Analytics", exact: true })).toBeVisible();
  await expect(navigation.getByRole("button", { name: "Group facts", exact: true })).toHaveCount(0);
  await expect(navigation.getByRole("button", { name: "Who can see info", exact: true })).toHaveCount(0);
  await expect(navigation.getByRole("button", { name: "Benefits", exact: true })).toHaveCount(0);

  const activeRouteColor = await navigation
    .getByRole("button", { name: "Home", exact: true })
    .evaluate((node) => getComputedStyle(node).color);
  expect(activeRouteColor).toBe("rgb(15, 124, 115)");
});

test("desktop sidebar spacing stays stable across long pages and portal modes", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await signIn(page);

  async function sidebarMetrics(routePath: string) {
    await page.goto(routePath);
    await expect(page.locator(".screen")).toBeVisible();
    return page.evaluate(() => {
      const rect = (selector: string) => {
        const node = document.querySelector(selector);
        if (!node) throw new Error(`Missing ${selector}`);
        const box = node.getBoundingClientRect();
        return { height: box.height, top: box.top, y: box.y };
      };
      return {
        appClass: document.querySelector(".app")?.className ?? "",
        brandCaption: document.querySelector(".brand small")?.textContent ?? "",
        clientTop: rect(".nav-group:not(.nav-group-provider):not(.nav-group-support)").y,
        providerTop: rect(".nav-group-provider").y,
        sidebarHeight: rect(".sidebar").height,
        supportTop: rect(".nav-group-support").y
      };
    });
  }

  const homeMetrics = await sidebarMetrics("/");
  const proofMetrics = await sidebarMetrics("/#/proof-center");
  const providerMetrics = await sidebarMetrics("/#/shelter");

  expect(Math.round(homeMetrics.sidebarHeight)).toBe(1000);
  expect(Math.round(proofMetrics.sidebarHeight)).toBe(1000);
  expect(Math.abs(homeMetrics.providerTop - proofMetrics.providerTop)).toBeLessThanOrEqual(1);
  expect(Math.abs(homeMetrics.supportTop - proofMetrics.supportTop)).toBeLessThanOrEqual(1);
  expect(homeMetrics.brandCaption).toBe("Client portal");
  expect(providerMetrics.appClass).toContain("portal-provider");
  expect(providerMetrics.brandCaption).toBe("Provider workspace");
});

test("analytics tools expose project and service organization admin introspection", async ({ page }) => {
  await signIn(page);
  await page.goto("/#/analytics");

  await expect(page.getByRole("heading", { name: /Share group facts, not your name/i })).toBeVisible();
  await expect(page.getByRole("region", { name: /Admin introspection/i })).toBeVisible();
  await expect(page.getByRole("article", { name: /211-AI project admin analytics introspection/i })).toContainText(
    "Template status"
  );
  await expect(page.getByRole("article", { name: /Service organization admin analytics introspection/i })).toContainText(
    "Own organization programs"
  );
  await expect(page.getByText(/Raw wallet records, names, contact details/i)).toBeVisible();
});
