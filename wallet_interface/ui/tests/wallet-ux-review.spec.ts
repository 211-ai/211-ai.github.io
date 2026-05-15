import { expect, test } from "@playwright/test";

const sessionKey = "abby-ui-session-v1";

test.describe("wallet UX review", () => {
  test("wallet page is scannable without horizontal overflow", async ({ page }, testInfo) => {
    await page.addInitScript((key) => {
      window.localStorage.setItem(key, JSON.stringify({ username: "wallet-reviewer" }));
    }, sessionKey);
    await page.goto("/#/uploads");
    await expect(page.getByRole("heading", { name: /^Wallet$/i })).toBeVisible();
    await expect(page.getByRole("heading", { name: /^File wallet$/i })).toBeVisible();
    await expect(page.getByLabel(/Wallet file controls/i)).toBeVisible();
    await page.screenshot({
      fullPage: true,
      path: testInfo.outputPath(`wallet-${testInfo.project.name.replace(/\W+/g, "-").toLowerCase()}.png`)
    });
    const overflow = await page.evaluate(() => {
      const width = document.documentElement.clientWidth;
      return [...document.querySelectorAll("body *")]
        .map((element) => {
          const rect = element.getBoundingClientRect();
          return {
            className: String((element as HTMLElement).className || ""),
            right: rect.right,
            tagName: element.tagName,
            text: String(element.textContent || "").trim().slice(0, 80)
          };
        })
        .filter((item) => item.right > width + 1)
        .slice(0, 8);
    });
    expect(overflow).toEqual([]);
  });
});
