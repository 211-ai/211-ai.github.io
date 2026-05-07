const CACHE_VERSION = "portal-070-v1";
const CACHE_PREFIX = "abby-portal";

export const PORTAL_SHELL_CACHE = `${CACHE_PREFIX}-shell-${CACHE_VERSION}`;
export const PORTAL_PUBLIC_DETAIL_CACHE = `${CACHE_PREFIX}-public-detail-${CACHE_VERSION}`;

const ACTIVE_CACHES = new Set([PORTAL_SHELL_CACHE, PORTAL_PUBLIC_DETAIL_CACHE]);
const STATIC_DESTINATIONS = new Set(["font", "image", "manifest", "script", "style", "worker"]);
const STATIC_EXTENSIONS = [
  ".css",
  ".ico",
  ".js",
  ".json",
  ".png",
  ".svg",
  ".webmanifest",
  ".woff",
  ".woff2",
];
const PRIVATE_API_SEGMENTS = new Set([
  "analytics",
  "approvals",
  "documents",
  "exports",
  "grants",
  "locations",
  "ops",
  "records",
  "storage",
  "wallets",
]);
const PRIVATE_QUERY_KEYS = new Set([
  "actordid",
  "audiencekeyhex",
  "grantid",
  "issuerkeyhex",
  "private_notes_record_id",
  "recordid",
  "record_id",
  "token",
  "walletapibaseurl",
  "walletid",
]);
const PUBLIC_DETAIL_ASSET_SUFFIXES = [
  "/corpus/211-info/current/artifacts.manifest.json",
  "/corpus/211-info/current/generated/document-index.json",
  "/corpus/211-info/current/generated/documents.json",
  "/corpus/211-info/current/generated/generated-manifest.json",
];
const SHELL_ASSET_ATTRIBUTE_PATTERN = /\b(?:href|src)=["']([^"']+)["']/g;

type ExtendableEventLike = Event & {
  waitUntil(promise: Promise<unknown>): void;
};

type FetchEventLike = Event & {
  request: Request;
  respondWith(response: Promise<Response> | Response): void;
};

type ServiceWorkerGlobalLike = typeof globalThis & {
  clients?: {
    claim(): Promise<void>;
  };
  registration?: {
    scope: string;
  };
  skipWaiting?: () => Promise<void>;
};

const workerGlobal = globalThis as ServiceWorkerGlobalLike;

export function isPublicPortalDetailAssetUrl(url: URL, origin = resolveWorkerOrigin()): boolean {
  return url.origin === origin && PUBLIC_DETAIL_ASSET_SUFFIXES.some((suffix) => url.pathname.endsWith(suffix));
}

export function isPrivateWalletUrl(url: URL): boolean {
  if (hasPrivateQuery(url)) return true;

  const segments = url.pathname
    .split("/")
    .map((segment) => segment.trim().toLowerCase())
    .filter(Boolean);
  return segments.some((segment) => PRIVATE_API_SEGMENTS.has(segment));
}

export function shouldHandlePortalRequest(request: Request, origin = resolveWorkerOrigin()): boolean {
  if (request.method !== "GET") return false;
  const url = new URL(request.url);
  if (url.origin !== origin) return false;

  if (isAppShellNavigation(request, url, origin)) {
    return !isPrivateApiPath(url.pathname);
  }

  if (hasPrivateRequestSignal(request, url)) return false;

  return isPublicPortalDetailAssetUrl(url, origin) || isStaticAppShellAsset(request, url);
}

export function extractShellAssetUrls(html: string, shellUrl = getAppShellUrl()): string[] {
  const origin = new URL(shellUrl).origin;
  const assetUrls = new Set<string>();
  let match: RegExpExecArray | null;

  while ((match = SHELL_ASSET_ATTRIBUTE_PATTERN.exec(html))) {
    const rawUrl = match[1];
    if (!rawUrl || rawUrl.startsWith("data:") || rawUrl.startsWith("#")) continue;

    try {
      const assetUrl = new URL(rawUrl, shellUrl);
      if (assetUrl.origin !== origin) continue;
      if (!isStaticAppShellAsset(new Request(assetUrl.toString()), assetUrl)) continue;
      assetUrls.add(assetUrl.toString());
    } catch {
      // Ignore malformed attributes; the browser will handle them normally online.
    }
  }

  return [...assetUrls];
}

function installPortalServiceWorker(): void {
  workerGlobal.addEventListener("install", (event) => {
    (event as ExtendableEventLike).waitUntil(
      precacheShellAssets()
        .catch(() => undefined)
        .then(() => workerGlobal.skipWaiting?.()),
    );
  });

  workerGlobal.addEventListener("activate", (event) => {
    (event as ExtendableEventLike).waitUntil(
      cleanupOldCaches()
        .catch(() => undefined)
        .then(() => workerGlobal.clients?.claim()),
    );
  });

  workerGlobal.addEventListener("fetch", (event) => {
    const fetchEvent = event as FetchEventLike;
    const request = fetchEvent.request;
    const url = new URL(request.url);
    const origin = resolveWorkerOrigin();

    if (!shouldHandlePortalRequest(request, origin)) return;

    if (isAppShellNavigation(request, url, origin)) {
      fetchEvent.respondWith(handleNavigationRequest(request));
      return;
    }

    if (isPublicPortalDetailAssetUrl(url, origin)) {
      fetchEvent.respondWith(staleWhileRevalidate(PORTAL_PUBLIC_DETAIL_CACHE, request));
      return;
    }

    fetchEvent.respondWith(cacheFirst(PORTAL_SHELL_CACHE, request));
  });
}

async function precacheShellAssets(): Promise<void> {
  const cache = await caches.open(PORTAL_SHELL_CACHE);
  const shellUrl = getAppShellUrl();
  const fallbackAssetUrls = [new URL("manifest.webmanifest", getWorkerScope()).toString()];

  try {
    const response = await fetch(new Request(shellUrl, { cache: "reload" }));
    if (isCacheableResponse(response)) {
      await cache.put(new Request(shellUrl), response.clone());
      const linkedAssetUrls = extractShellAssetUrls(await response.clone().text(), shellUrl);
      await precacheUrls(cache, [...linkedAssetUrls, ...fallbackAssetUrls]);
      return;
    }
  } catch {
    // Runtime cache population still covers the shell after the first online load.
  }

  await precacheUrls(cache, fallbackAssetUrls);
}

async function precacheUrls(cache: Cache, urls: string[]): Promise<void> {
  await Promise.all(
    [...new Set(urls)].map(async (assetUrl) => {
      try {
        const response = await fetch(new Request(assetUrl, { cache: "reload" }));
        if (isCacheableResponse(response)) {
          await cache.put(new Request(assetUrl), response.clone());
        }
      } catch {
        // Individual optional assets should not block service worker installation.
      }
    }),
  );
}

async function cleanupOldCaches(): Promise<void> {
  const cacheNames = await caches.keys();
  await Promise.all(
    cacheNames.map((cacheName) =>
      cacheName.startsWith(CACHE_PREFIX) && !ACTIVE_CACHES.has(cacheName)
        ? caches.delete(cacheName)
        : Promise.resolve(false),
    ),
  );
}

async function handleNavigationRequest(request: Request): Promise<Response> {
  const cache = await caches.open(PORTAL_SHELL_CACHE);
  const shellRequest = new Request(getAppShellUrl());

  try {
    const response = await fetch(request);
    if (isCacheableResponse(response)) {
      await cache.put(shellRequest, response.clone());
    }
    return response;
  } catch {
    const cached = await cache.match(shellRequest);
    return cached ?? offlineShellResponse();
  }
}

async function cacheFirst(cacheName: string, request: Request): Promise<Response> {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);
  if (cached) return cached;

  const response = await fetch(request);
  if (isCacheableResponse(response)) {
    await cache.put(request, response.clone());
  }
  return response;
}

async function staleWhileRevalidate(cacheName: string, request: Request): Promise<Response> {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);
  const refresh = fetch(request)
    .then(async (response) => {
      if (isCacheableResponse(response)) {
        await cache.put(request, response.clone());
      }
      return response;
    })
    .catch(() => undefined);

  return cached ?? (await refresh) ?? offlineJsonResponse(request.url);
}

function isAppShellNavigation(request: Request, url: URL, origin = resolveWorkerOrigin()): boolean {
  if (url.origin !== origin) return false;
  if (!isAppShellPath(url.pathname)) return false;
  return request.mode === "navigate" || request.destination === "document" || acceptsHtml(request);
}

function isAppShellPath(pathname: string): boolean {
  if (isPrivateApiPath(pathname)) return false;

  const normalizedPath = pathname.endsWith("/") ? pathname : `${pathname}/`;
  const scopePath = new URL(getWorkerScope()).pathname;
  if (!normalizedPath.startsWith(scopePath.endsWith("/") ? scopePath : `${scopePath}/`)) return false;

  const pathParts = pathname.split("/").filter(Boolean);
  const leaf = pathParts[pathParts.length - 1] ?? "";
  return leaf === "" || leaf === "index.html" || !leaf.includes(".");
}

function isPrivateApiPath(pathname: string): boolean {
  const segments = pathname
    .split("/")
    .map((segment) => segment.trim().toLowerCase())
    .filter(Boolean);
  return segments.some((segment) => PRIVATE_API_SEGMENTS.has(segment));
}

function isStaticAppShellAsset(request: Request, url: URL): boolean {
  if (STATIC_DESTINATIONS.has(request.destination)) return true;
  if (url.pathname.includes("/assets/")) {
    return STATIC_EXTENSIONS.some((extension) => url.pathname.toLowerCase().endsWith(extension));
  }
  return url.pathname.endsWith("/manifest.webmanifest");
}

function hasPrivateRequestSignal(request: Request, url: URL): boolean {
  return Boolean(request.headers.get("authorization")) || isPrivateWalletUrl(url);
}

function hasPrivateQuery(url: URL): boolean {
  for (const key of url.searchParams.keys()) {
    if (PRIVATE_QUERY_KEYS.has(key.toLowerCase())) return true;
  }
  return false;
}

function acceptsHtml(request: Request): boolean {
  return request.headers.get("accept")?.toLowerCase().includes("text/html") ?? false;
}

function isCacheableResponse(response: Response): boolean {
  if (!response.ok) return false;
  const cacheControl = response.headers.get("cache-control")?.toLowerCase() ?? "";
  return !cacheControl.includes("no-store") && !cacheControl.includes("private");
}

function getAppShellUrl(): string {
  return new URL("./", getWorkerScope()).toString();
}

function getWorkerScope(): string {
  return workerGlobal.registration?.scope ?? `${resolveWorkerOrigin()}/`;
}

function resolveWorkerOrigin(): string {
  return workerGlobal.location?.origin ?? "http://localhost";
}

function offlineShellResponse(): Response {
  return new Response(
    `<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Abby Offline</title>
  </head>
  <body>
    <main>
      <h1>Abby is offline</h1>
      <p>The app shell has not been cached on this device yet. Reopen Abby while online to enable offline service details.</p>
    </main>
  </body>
</html>`,
    {
      headers: {
        "cache-control": "no-store",
        "content-type": "text/html; charset=utf-8",
      },
      status: 503,
    },
  );
}

function offlineJsonResponse(url: string): Response {
  return new Response(
    JSON.stringify({
      error: "offline",
      message: "This public 211 detail artifact is not cached yet.",
      url,
    }),
    {
      headers: {
        "cache-control": "no-store",
        "content-type": "application/json; charset=utf-8",
      },
      status: 503,
    },
  );
}

if (workerGlobal.registration?.scope && workerGlobal.skipWaiting && workerGlobal.clients?.claim) {
  installPortalServiceWorker();
}
