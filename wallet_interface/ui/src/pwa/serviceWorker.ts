export const PORTAL_SERVICE_WORKER_VERSION = "portal-offline-shell-v1";
export const PORTAL_APP_SHELL_CACHE = `${PORTAL_SERVICE_WORKER_VERSION}:app-shell`;
export const PORTAL_PUBLIC_RUNTIME_CACHE = `${PORTAL_SERVICE_WORKER_VERSION}:public-runtime`;

export const SENSITIVE_CACHE_QUERY_PARAMS = [
  "actorDid",
  "actorKeyHex",
  "actor_key_hex",
  "audienceKeyHex",
  "audience_key_hex",
  "issuerKeyHex",
  "issuer_key_hex",
  "key_hex",
  "walletApiBaseUrl",
  "walletId"
];

const STATIC_PRECACHE_PATHS = ["manifest.webmanifest", "assets/abby-logo.png"];
const PUBLIC_CORPUS_PREFIX = "corpus/211-info/current/";
const PUBLIC_CACHE_PREFIXES = ["assets/", PUBLIC_CORPUS_PREFIX];
const PRIVATE_PATH_SEGMENTS = new Set([
  "access-requests",
  "analytics",
  "approvals",
  "controllers",
  "devices",
  "documents",
  "exports",
  "grant-receipts",
  "locations",
  "portal",
  "proofs",
  "records",
  "recovery-policy",
  "snapshot",
  "storage",
  "wallets"
]);

type PwaExtendableEvent = Event & {
  waitUntil(promise: Promise<unknown>): void;
};

type PwaFetchEvent = Event & {
  request: Request;
  respondWith(response: Promise<Response> | Response): void;
};

type PwaServiceWorkerGlobal = {
  caches: CacheStorage;
  registration: {
    scope: string;
  };
  addEventListener(type: "activate" | "install", listener: (event: PwaExtendableEvent) => void): void;
  addEventListener(type: "fetch", listener: (event: PwaFetchEvent) => void): void;
};

const serviceWorker = getServiceWorkerGlobal();

if (serviceWorker) {
  serviceWorker.addEventListener("install", (event) => {
    event.waitUntil(cacheOfflineShell(serviceWorker));
  });

  serviceWorker.addEventListener("activate", (event) => {
    event.waitUntil(deleteOldPortalCaches(serviceWorker));
  });

  serviceWorker.addEventListener("fetch", (event) => {
    const request = event.request;
    if (request.method !== "GET") return;

    const url = new URL(request.url);
    if (request.mode === "navigate") {
      if (isPrivateWalletRequest(url)) return;
      event.respondWith(handleNavigationRequest(serviceWorker));
      return;
    }

    if (shouldBypassRuntimeCache(request, url, serviceWorker.registration.scope)) return;

    if (isPublicCorpusRequest(url, serviceWorker.registration.scope)) {
      event.respondWith(networkFirstPublicRequest(serviceWorker, request));
      return;
    }

    if (isPublicOfflineAssetRequest(url, serviceWorker.registration.scope)) {
      event.respondWith(cacheFirstPublicRequest(serviceWorker, request, PORTAL_APP_SHELL_CACHE));
    }
  });
}

export function isPrivateWalletRequest(input: string | URL): boolean {
  const url = toUrl(input);
  if (hasSensitiveCacheQuery(url)) return true;
  return url.pathname.split("/").filter(Boolean).some((segment) => PRIVATE_PATH_SEGMENTS.has(segment));
}

export function isPublicOfflineAssetRequest(input: string | URL, scopeUrl = defaultScopeUrl()): boolean {
  const url = toUrl(input);
  const scope = toUrl(scopeUrl);
  if (url.origin !== scope.origin || hasSensitiveCacheQuery(url) || isPrivateWalletRequest(url)) return false;

  const relativePath = relativeScopedPath(url, scope);
  if (relativePath === "" || relativePath === "index.html" || STATIC_PRECACHE_PATHS.includes(relativePath)) {
    return true;
  }

  return PUBLIC_CACHE_PREFIXES.some((prefix) => relativePath.startsWith(prefix));
}

export function hasSensitiveCacheQuery(url: URL): boolean {
  return SENSITIVE_CACHE_QUERY_PARAMS.some((param) => url.searchParams.has(param));
}

async function cacheOfflineShell(worker: PwaServiceWorkerGlobal): Promise<void> {
  const cache = await worker.caches.open(PORTAL_APP_SHELL_CACHE);
  const scopeUrl = worker.registration.scope;
  const shellUrl = appShellUrl(scopeUrl);

  const shellResponse = await fetchAndCache(cache, shellUrl);
  const shellHtml = shellResponse ? await shellResponse.clone().text().catch(() => "") : "";
  const shellAssets = shellHtml ? extractShellAssetUrls(shellHtml, scopeUrl) : [];
  const staticAssets = STATIC_PRECACHE_PATHS.map((path) => new URL(path, scopeUrl).toString());
  const urls = [...new Set([...staticAssets, ...shellAssets])].filter((url) =>
    isPublicOfflineAssetRequest(url, scopeUrl)
  );

  await Promise.allSettled(urls.map((url) => fetchAndCache(cache, url)));
}

async function deleteOldPortalCaches(worker: PwaServiceWorkerGlobal): Promise<void> {
  const keepCaches = new Set([PORTAL_APP_SHELL_CACHE, PORTAL_PUBLIC_RUNTIME_CACHE]);
  const cacheNames = await worker.caches.keys();
  await Promise.all(
    cacheNames
      .filter((cacheName) => cacheName.startsWith("portal-offline-shell-") && !keepCaches.has(cacheName))
      .map((cacheName) => worker.caches.delete(cacheName))
  );
}

async function handleNavigationRequest(worker: PwaServiceWorkerGlobal): Promise<Response> {
  const cache = await worker.caches.open(PORTAL_APP_SHELL_CACHE);
  const shellUrl = appShellUrl(worker.registration.scope);

  try {
    const response = await fetch(new Request(shellUrl, { cache: "reload", credentials: "same-origin" }));
    if (isCacheableResponse(response)) {
      await cache.put(shellUrl, response.clone());
    }
    return response;
  } catch {
    const cachedShell = await cache.match(shellUrl);
    return cachedShell ?? offlineFallbackResponse();
  }
}

async function cacheFirstPublicRequest(
  worker: PwaServiceWorkerGlobal,
  request: Request,
  cacheName: string
): Promise<Response> {
  const cache = await worker.caches.open(cacheName);
  const cacheKey = publicCacheKey(request);
  const cached = await cache.match(cacheKey);
  if (cached) return cached;
  return (await fetchAndCache(cache, request, cacheKey)) ?? fetch(request);
}

async function networkFirstPublicRequest(worker: PwaServiceWorkerGlobal, request: Request): Promise<Response> {
  const cache = await worker.caches.open(PORTAL_PUBLIC_RUNTIME_CACHE);
  const cacheKey = publicCacheKey(request);

  try {
    const response = await fetch(request);
    if (isCacheableResponse(response)) {
      await cache.put(cacheKey, response.clone());
    }
    return response;
  } catch {
    const cached = await cache.match(cacheKey);
    if (cached) return cached;
    throw new Error(`Public offline asset is not cached: ${request.url}`);
  }
}

async function fetchAndCache(cache: Cache, input: RequestInfo | URL, cacheKey?: RequestInfo): Promise<Response | null> {
  const requestInfo = input instanceof URL ? input.toString() : input;
  try {
    const response = await fetch(new Request(requestInfo, { cache: "reload", credentials: "same-origin" }));
    if (isCacheableResponse(response)) {
      await cache.put(cacheKey ?? requestInfo, response.clone());
    }
    return response;
  } catch {
    return null;
  }
}

function shouldBypassRuntimeCache(request: Request, url: URL, scopeUrl: string): boolean {
  if (url.origin !== new URL(scopeUrl).origin) return true;
  if (request.headers.has("authorization")) return true;
  if (hasSensitiveCacheQuery(url)) return true;
  if (isPrivateWalletRequest(url)) return true;
  return !isPublicOfflineAssetRequest(url, scopeUrl);
}

function isPublicCorpusRequest(url: URL, scopeUrl: string): boolean {
  return relativeScopedPath(url, toUrl(scopeUrl)).startsWith(PUBLIC_CORPUS_PREFIX);
}

function extractShellAssetUrls(html: string, scopeUrl: string): string[] {
  const urls: string[] = [];
  const attributePattern = /\b(?:href|src)="([^"]+)"/g;
  let match: RegExpExecArray | null;

  while ((match = attributePattern.exec(html))) {
    const value = match[1];
    if (!value || value.startsWith("data:") || value.startsWith("#")) continue;
    urls.push(new URL(value, scopeUrl).toString());
  }

  return urls;
}

function publicCacheKey(request: Request): Request {
  return new Request(request.url, { credentials: "same-origin" });
}

function appShellUrl(scopeUrl: string): string {
  return new URL("./", scopeUrl).toString();
}

function relativeScopedPath(url: URL, scope: URL): string {
  const scopePath = scope.pathname.endsWith("/") ? scope.pathname : `${scope.pathname}/`;
  if (!url.pathname.startsWith(scopePath)) return "";
  return url.pathname.slice(scopePath.length).replace(/^\/+/, "");
}

function isCacheableResponse(response: Response): boolean {
  return response.ok && (response.type === "basic" || response.type === "default");
}

function offlineFallbackResponse(): Response {
  return new Response(
    [
      "<!doctype html>",
      '<html lang="en">',
      "<head>",
      '<meta charset="UTF-8" />',
      '<meta name="viewport" content="width=device-width, initial-scale=1.0" />',
      "<title>Abby offline</title>",
      "</head>",
      "<body>",
      "<main>",
      "<h1>Abby is offline</h1>",
      "<p>The service shell is not cached on this device yet.</p>",
      "</main>",
      "</body>",
      "</html>"
    ].join(""),
    {
      headers: {
        "Cache-Control": "no-store",
        "Content-Type": "text/html; charset=utf-8"
      },
      status: 503
    }
  );
}

function hasServiceWorkerShape(value: unknown): value is PwaServiceWorkerGlobal {
  const candidate = value as Partial<PwaServiceWorkerGlobal> | undefined;
  return Boolean(candidate?.registration?.scope && candidate.caches && candidate.addEventListener);
}

function getServiceWorkerGlobal(): PwaServiceWorkerGlobal | null {
  const candidate: unknown = globalThis;
  return hasServiceWorkerShape(candidate) ? candidate : null;
}

function defaultScopeUrl(): string {
  return getServiceWorkerGlobal()?.registration.scope ?? "http://localhost/";
}

function toUrl(input: string | URL): URL {
  return input instanceof URL ? input : new URL(input, defaultScopeUrl());
}
