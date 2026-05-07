import { expect, test } from "@playwright/test";

import {
  extractShellAssetUrls,
  isPrivateWalletUrl,
  isPublicPortalDetailAssetUrl,
  shouldHandlePortalRequest,
} from "../src/pwa/serviceWorker";

const origin = "http://127.0.0.1:5174";

test.describe("portal service worker cache policy", () => {
  test("handles only public shell and service detail assets", () => {
    expect(
      shouldHandlePortalRequest(new Request(`${origin}/corpus/211-info/current/generated/documents.json`), origin),
    ).toBe(true);
    expect(
      shouldHandlePortalRequest(new Request(`${origin}/corpus/211-info/current/generated/generated-manifest.json`), origin),
    ).toBe(true);
    expect(
      shouldHandlePortalRequest(new Request(`${origin}/corpus/211-info/current/generated/bm25-documents.json`), origin),
    ).toBe(false);
    expect(shouldHandlePortalRequest(new Request("https://example.test/assets/app.js"), origin)).toBe(false);
  });

  test("bypasses wallet and plaintext-bearing requests", () => {
    expect(isPrivateWalletUrl(new URL(`${origin}/wallets/wallet-demo/portal/saved-services`))).toBe(true);
    expect(isPrivateWalletUrl(new URL(`${origin}/wallets/wallet-demo/records/rec-1/decrypt`))).toBe(true);
    expect(isPrivateWalletUrl(new URL(`${origin}/?walletId=wallet-demo&actorDid=did:example:abby`))).toBe(true);

    expect(
      shouldHandlePortalRequest(new Request(`${origin}/wallets/wallet-demo/portal/plans`), origin),
    ).toBe(false);
    expect(
      shouldHandlePortalRequest(
        new Request(`${origin}/assets/app.js`, { headers: { authorization: "Bearer secret" } }),
        origin,
      ),
    ).toBe(false);
    expect(
      shouldHandlePortalRequest(new Request(`${origin}/wallets/wallet-demo/portal/plans`, { method: "POST" }), origin),
    ).toBe(false);
  });

  test("normalizes private launch query strings to the public app shell", () => {
    const launchRequest = new Request(`${origin}/?walletId=wallet-demo&actorDid=did:example:abby#/social-services`, {
      headers: { accept: "text/html" },
    });

    expect(shouldHandlePortalRequest(launchRequest, origin)).toBe(true);
    expect(isPublicPortalDetailAssetUrl(new URL(`${origin}/corpus/211-info/current/generated/documents.json`), origin)).toBe(
      true,
    );
  });

  test("discovers built shell assets for first-install offline use", () => {
    const html = `
      <link rel="manifest" href="./manifest.webmanifest" />
      <link rel="stylesheet" href="./assets/app-demo.css" />
      <script type="module" src="./assets/app-demo.js"></script>
      <img src="https://cdn.example.test/private.png" />
    `;

    expect(extractShellAssetUrls(html, `${origin}/`)).toEqual([
      `${origin}/manifest.webmanifest`,
      `${origin}/assets/app-demo.css`,
      `${origin}/assets/app-demo.js`,
    ]);
  });
});
