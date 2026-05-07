/// <reference lib="webworker" />

const serviceWorker = self as unknown as ServiceWorkerGlobalScope;

const CACHE_VERSION = "portal-070-v1";
const CACHE_PREFIX = "abby-portal";
const SHELL_CACHE = `${CACHE_PREFIX}-shell-${CACHE_VERSION}`;
const ASSET_CACHE = `${CACHE_PREFIX}-assets-${CACHE_VERSION}`;
const PUBLIC_SERVICE_CACHE = `${CACHE_PREFIX}-public-services-${CACHE_VERSION}`;
const KNOWN_CACHES = new Set([SHELL_CACHE, ASSET_CACHE, PUBLIC_SERVICE_CACHE]);

const PUBLIC_SERVICE_DETAIL_PATHS = new Set([
  "/corpus/211-info/current/artifacts.manifest.json",
  "/corpus/211-info/current/generated/documents.json",
  "/corpus/211-info/current/generated/generated-manifest.json",
]);
const PUBLIC_SERVICE_SEED_PATHS = [
  "/corpus/211-info/current/artifacts.manifest.json",
  "/corpus/211-info/current/generated/generated-manifest.json",
];

const PRIVATE_PATH_PREFIXES = [
  "/api/",
  "/audit",
  "/exports",
  "/portal/saved-services",
  "/proof",
  "/recipient-access",
  "/records",
  "/service-interactions",
  "/service-plans",
  "/uploads",
  "/wallets/",
];

const SENSITIVE_QUERY_KEYS = [
  "actor",
  "audience",
  "auth",
  "decrypt",
  "grant",
  "issuer",
  "key",
  "note",
  "password",
  "private",
  "record",
  "secret",
  "token",
  "wallet",
];

const SHELL_PATHS = ["./", "./manifest.webmanifest", "./assets/abby-logo.png"];

serviceWorker.addEventListener("install", (event) => {
  event.waitUntil(
    (async () => {
      await Promise.allSettled([cacheAppShell(), seedPublicServiceDetailCache()]);
      await serviceWorker.skipWaiting();
    })(),
  );
});

serviceWorker.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      const cacheNames = await caches.keys();
      await Promise.all(
        cacheNames
          .filter((cacheName) => cacheName.startsWith(CACHE_PREFIX) && !KNOWN_CACHES.has(cacheName))
          .map((cacheName) => caches.delete(cacheName)),
      );
      await serviceWorker.clients.claim();
    })(),
  );
});

serviceWorker.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  if (!isSameOrigin(url)) return;

  if (request.mode === "navigate") {
    event.respondWith(handleNavigation(request));
    return;
  }

  if (isPrivateRequest(request, url)) return;

  if (isPublicServiceDetailRequest(url)) {
    event.respondWith(staleWhileRevalidate(request, PUBLIC_SERVICE_CACHE));
    return;
  }

  if (isAppShellAssetRequest(url)) {
    event.respondWith(cacheFirst(request, ASSET_CACHE));
  }
});

async function cacheAppShell(): Promise<void> {
  const cache = await caches.open(SHELL_CACHE);
  const shellUrl = scopedUrl("./");
  const shellResponse = await fetch(shellUrl, { cache: "reload", credentials: "same-origin" });
  if (isCacheableResponse(shellResponse)) {
    const shellClone = shellResponse.clone();
    await cache.put(shellUrl, shellResponse);
    await cacheLinkedShellAssets(shellClone);
  }

  await Promise.allSettled(
    SHELL_PATHS.slice(1).map(async (path) => {
      const url = scopedUrl(path);
      const response = await fetch(url, { cache: "reload", credentials: "same-origin" });
      if (isCacheableResponse(response)) {
        await cache.put(url, response);
      }
    }),
  );
}

async function cacheLinkedShellAssets(response: Response): Promise<void> {
  const html = await response.text().catch(() => "");
  if (!html) return;

  const assetUrls = extractSameOriginAssetUrls(html).filter(isAppShellAssetRequest);
  if (!assetUrls.length) return;

  const cache = await caches.open(ASSET_CACHE);
  await Promise.allSettled(
    assetUrls.map(async (url) => {
      const response = await fetch(url.toString(), { cache: "reload", credentials: "same-origin" });
      if (isCacheableResponse(response)) {
        await cache.put(url.toString(), response);
      }
    }),
  );
}

async function seedPublicServiceDetailCache(): Promise<void> {
  const cache = await caches.open(PUBLIC_SERVICE_CACHE);
  await Promise.allSettled(
    PUBLIC_SERVICE_SEED_PATHS.map(async (path) => {
      const response = await fetch(scopedUrl(`.${path}`), { cache: "reload", credentials: "same-origin" });
      if (isCacheableResponse(response)) {
        await cache.put(scopedUrl(`.${path}`), response);
      }
    }),
  );
}

async function handleNavigation(request: Request): Promise<Response> {
  const shellUrl = scopedUrl("./");
  const url = new URL(request.url);
  const shellCache = await caches.open(SHELL_CACHE);

  try {
    const response = await fetch(request);
    if (isCacheableResponse(response) && !hasSearchParams(url)) {
      const responseClone = response.clone();
      await shellCache.put(shellUrl, responseClone);
      await cacheLinkedShellAssets(response.clone());
    }
    return response;
  } catch {
    const cachedShell = await shellCache.match(shellUrl);
    return cachedShell ?? offlineShellResponse();
  }
}

async function staleWhileRevalidate(request: Request, cacheName: string): Promise<Response> {
  const cache = await caches.open(cacheName);
  const cacheKey = cacheKeyFor(request);
  const cachedResponse = await cache.match(cacheKey);
  const networkFetch = fetch(request)
    .then(async (response) => {
      if (isCacheableResponse(response)) {
        await cache.put(cacheKey, response.clone());
      }
      return response;
    })
    .catch(() => undefined);

  return cachedResponse ?? (await networkFetch) ?? offlineServiceResponse();
}

async function cacheFirst(request: Request, cacheName: string): Promise<Response> {
  const cache = await caches.open(cacheName);
  const cachedResponse = await cache.match(cacheKeyFor(request));
  if (cachedResponse) return cachedResponse;

  const response = await fetch(request);
  if (isCacheableResponse(response)) {
    await cache.put(cacheKeyFor(request), response.clone());
  }
  return response;
}

function cacheKeyFor(request: Request): Request {
  const url = new URL(request.url);
  url.search = "";
  return new Request(url.toString(), {
    credentials: "same-origin",
    headers: { Accept: request.headers.get("Accept") || "*/*" },
    method: "GET",
  });
}

function extractSameOriginAssetUrls(html: string): URL[] {
  const urls: URL[] = [];
  const attributePattern = /\s(?:href|src)=["']([^"']+)["']/g;
  let match = attributePattern.exec(html);
  while (match) {
    const value = match[1];
    if (value && !value.startsWith("data:")) {
      const url = new URL(value, serviceWorker.registration.scope);
      if (isSameOrigin(url) && !hasSearchParams(url)) {
        urls.push(url);
      }
    }
    match = attributePattern.exec(html);
  }
  return urls;
}

function isPublicServiceDetailRequest(url: URL): boolean {
  return PUBLIC_SERVICE_DETAIL_PATHS.has(toScopeRelativePath(url.pathname));
}

function isAppShellAssetRequest(url: URL): boolean {
  if (hasSearchParams(url)) return false;
  const path = toScopeRelativePath(url.pathname);
  return (
    path === "/manifest.webmanifest" ||
    path.startsWith("/assets/") ||
    /\.(?:css|html|ico|js|json|png|svg|wasm|webp|woff2?)$/i.test(path)
  );
}

function isPrivateRequest(request: Request, url: URL): boolean {
  if (request.headers.has("Authorization")) return true;
  if (hasSensitiveQuery(url)) return true;

  const path = toScopeRelativePath(url.pathname);
  return PRIVATE_PATH_PREFIXES.some((prefix) => path === prefix || path.startsWith(prefix));
}

function hasSensitiveQuery(url: URL): boolean {
  for (const key of url.searchParams.keys()) {
    const normalizedKey = key.toLowerCase();
    if (SENSITIVE_QUERY_KEYS.some((sensitiveKey) => normalizedKey.includes(sensitiveKey))) {
      return true;
    }
  }
  return false;
}

function hasSearchParams(url: URL): boolean {
  return url.search.length > 0;
}

function isSameOrigin(url: URL): boolean {
  return url.origin === serviceWorker.location.origin;
}

function isCacheableResponse(response: Response): boolean {
  return response.ok && (response.type === "basic" || response.type === "default");
}

function toScopeRelativePath(pathname: string): string {
  const scopePath = new URL(serviceWorker.registration.scope).pathname;
  if (scopePath !== "/" && pathname.startsWith(scopePath)) {
    return `/${pathname.slice(scopePath.length)}`;
  }
  return pathname;
}

function scopedUrl(path: string): string {
  return new URL(path, serviceWorker.registration.scope).toString();
}

function offlineServiceResponse(): Response {
  return new Response(JSON.stringify({ error: "Public service detail is unavailable offline until it has been cached." }), {
    headers: { "Content-Type": "application/json; charset=utf-8" },
    status: 503,
  });
}

function offlineShellResponse(): Response {
  return new Response(
    "<!doctype html><title>Abby offline</title><main><h1>Abby is offline</h1><p>Reconnect once to cache the app shell.</p></main>",
    {
      headers: { "Content-Type": "text/html; charset=utf-8" },
      status: 503,
    },
  );
}

export {};
