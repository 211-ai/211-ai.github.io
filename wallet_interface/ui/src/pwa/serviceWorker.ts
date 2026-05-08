const CACHE_VERSION = "portal-071-v1";
const SHELL_CACHE = `abby-shell-${CACHE_VERSION}`;
const PUBLIC_SERVICE_CACHE = `abby-public-service-detail-${CACHE_VERSION}`;
const APP_CACHE_PREFIX = "abby-";

const PUBLIC_SERVICE_DETAIL_ASSETS = new Set([
  "corpus/211-info/current/artifacts.manifest.json",
  "corpus/211-info/current/generated/generated-manifest.json",
  "corpus/211-info/current/generated/documents.json"
]);

const PRIVATE_QUERY_KEYS = new Set([
  "actorDid",
  "audienceKeyHex",
  "issuerKeyHex",
  "walletApiBaseUrl",
  "walletId"
]);

type ServiceWorkerLifecycleEvent = Event & {
  waitUntil(promise: Promise<unknown>): void;
};

type ServiceWorkerFetchEvent = Event & {
  request: Request;
  respondWith(response: Promise<Response> | Response): void;
};

type ServiceWorkerMessageEvent = MessageEvent & {
  data?: { type?: string };
  waitUntil(promise: Promise<unknown>): void;
};

type ServiceWorkerGlobal = typeof globalThis & {
  clients: {
    claim(): Promise<void>;
  };
  registration: {
    scope: string;
  };
  skipWaiting(): Promise<void>;
  addEventListener(type: "activate", listener: (event: ServiceWorkerLifecycleEvent) => void): void;
  addEventListener(type: "fetch", listener: (event: ServiceWorkerFetchEvent) => void): void;
  addEventListener(type: "install", listener: (event: ServiceWorkerLifecycleEvent) => void): void;
  addEventListener(type: "message", listener: (event: ServiceWorkerMessageEvent) => void): void;
};

const sw = self as unknown as ServiceWorkerGlobal;

sw.addEventListener("install", (event) => {
  event.waitUntil(
    precacheShell().then(() => sw.skipWaiting())
  );
});

sw.addEventListener("activate", (event) => {
  event.waitUntil(
    deleteOldCaches().then(() => sw.clients.claim())
  );
});

sw.addEventListener("message", (event) => {
  if (event.data?.type === "SKIP_WAITING") {
    event.waitUntil(sw.skipWaiting());
  }
});

sw.addEventListener("fetch", (event) => {
  const request = event.request;
  if (!isHttpRequest(request)) return;

  if (isNavigationRequest(request)) {
    event.respondWith(handleNavigation(request));
    return;
  }

  if (shouldBypassCache(request)) {
    event.respondWith(fetchWithoutBrowserCache(request));
    return;
  }

  if (isPublicServiceDetailAsset(request)) {
    event.respondWith(cacheFirst(request, PUBLIC_SERVICE_CACHE));
    return;
  }

  if (isPublicShellAsset(request)) {
    event.respondWith(cacheFirst(request, SHELL_CACHE));
  }
});

async function precacheShell(): Promise<void> {
  const cache = await caches.open(SHELL_CACHE);
  const shellUrl = scopedUrl("index.html");
  const rootUrl = scopedUrl("");
  const manifestUrl = scopedUrl("manifest.webmanifest");
  const iconUrl = scopedUrl("assets/abby-logo.png");

  try {
    const shellResponse = await fetch(new Request(shellUrl, { cache: "reload" }));
    if (isCacheableResponse(shellResponse)) {
      await cache.put(new Request(shellUrl), shellResponse.clone());
      await cache.put(new Request(rootUrl), shellResponse.clone());
      const html = await shellResponse.text();
      const assetUrls = extractShellAssetUrls(html);
      await Promise.allSettled(
        [manifestUrl, iconUrl, ...assetUrls].map((url) => cache.add(new Request(url, { cache: "reload" })))
      );
      return;
    }
  } catch {
    // Runtime navigation fallback will use any previously cached shell.
  }

  await Promise.allSettled([rootUrl, shellUrl, manifestUrl, iconUrl].map((url) => cache.add(url)));
}

async function deleteOldCaches(): Promise<void> {
  const currentCaches = new Set([SHELL_CACHE, PUBLIC_SERVICE_CACHE]);
  const keys = await caches.keys();
  await Promise.all(
    keys
      .filter((key) => key.startsWith(APP_CACHE_PREFIX) && !currentCaches.has(key))
      .map((key) => caches.delete(key))
  );
}

async function handleNavigation(request: Request): Promise<Response> {
  const cache = await caches.open(SHELL_CACHE);
  const shellRequest = new Request(scopedUrl("index.html"));
  const rootRequest = new Request(scopedUrl(""));
  const hasPrivateUrl = hasPrivateWalletUrl(request.url);

  try {
    const response = await fetch(requestWithCacheMode(request, hasPrivateUrl ? "no-store" : "default"));
    if (!hasPrivateUrl && isCacheableResponse(response)) {
      await cache.put(shellRequest, response.clone());
      await cache.put(rootRequest, response.clone());
    }
    return response;
  } catch {
    return (
      (await cache.match(shellRequest)) ??
      (await cache.match(rootRequest)) ??
      new Response("Abby is offline and the app shell is not cached yet.", {
        headers: { "Content-Type": "text/plain; charset=utf-8" },
        status: 503,
        statusText: "Offline"
      })
    );
  }
}

async function fetchWithoutBrowserCache(request: Request): Promise<Response> {
  return fetch(requestWithCacheMode(request, "no-store"));
}

async function cacheFirst(request: Request, cacheName: string): Promise<Response> {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request, { ignoreSearch: false });
  if (cached) return cached;

  const response = await fetch(request);
  if (isCacheableResponse(response)) {
    await cache.put(request, response.clone());
  }
  return response;
}

function isHttpRequest(request: Request): boolean {
  return request.url.startsWith("http://") || request.url.startsWith("https://");
}

function isNavigationRequest(request: Request): boolean {
  return request.mode === "navigate" || request.destination === "document";
}

function shouldBypassCache(request: Request): boolean {
  if (request.method !== "GET") return true;
  if (hasPrivateWalletUrl(request.url)) return true;

  const url = new URL(request.url);
  if (!isSameOrigin(url)) return request.destination === "";
  if (isPublicServiceDetailAsset(request) || isPublicShellAsset(request)) return false;

  return request.destination === "";
}

function isPublicServiceDetailAsset(request: Request): boolean {
  if (request.method !== "GET") return false;
  const url = new URL(request.url);
  return isSameOrigin(url) && PUBLIC_SERVICE_DETAIL_ASSETS.has(scopeRelativePath(url));
}

function isPublicShellAsset(request: Request): boolean {
  if (request.method !== "GET") return false;
  const url = new URL(request.url);
  if (!isSameOrigin(url)) return false;

  const relativePath = scopeRelativePath(url);
  if (relativePath === "" || relativePath === "index.html") return true;
  if (relativePath === "manifest.webmanifest" || relativePath === "assets/abby-logo.png") return true;

  return (
    relativePath.startsWith("assets/") &&
    /\.(?:css|gif|ico|jpe?g|js|mjs|png|svg|wasm|webp|woff2?)$/i.test(relativePath)
  );
}

function hasPrivateWalletUrl(rawUrl: string): boolean {
  const url = new URL(rawUrl);
  if ([...PRIVATE_QUERY_KEYS].some((key) => url.searchParams.has(key))) return true;

  const normalizedPath = url.pathname.replace(/\/{2,}/g, "/");
  return (
    /(^|\/)wallets(\/|$)/.test(normalizedPath) ||
    /(^|\/)wallet(\/|$)/.test(normalizedPath) ||
    /(^|\/)records(\/|$)/.test(normalizedPath) ||
    /(^|\/)grants(\/|$)/.test(normalizedPath) ||
    /(^|\/)proofs(\/|$)/.test(normalizedPath)
  );
}

function isSameOrigin(url: URL): boolean {
  return url.origin === new URL(sw.registration.scope).origin;
}

function scopeRelativePath(url: URL): string {
  const scopePath = new URL(sw.registration.scope).pathname;
  const normalizedScope = scopePath.endsWith("/") ? scopePath : `${scopePath}/`;
  const path = decodeURIComponent(url.pathname);
  if (!path.startsWith(normalizedScope)) return path.replace(/^\/+/, "");
  return path.slice(normalizedScope.length).replace(/^\/+/, "");
}

function scopedUrl(path: string): URL {
  return new URL(path, sw.registration.scope);
}

function requestWithCacheMode(request: Request, cacheMode: RequestCache): Request {
  try {
    return new Request(request, { cache: cacheMode });
  } catch {
    return request;
  }
}

function isCacheableResponse(response: Response): boolean {
  return response.ok && (response.type === "basic" || response.type === "default");
}

function extractShellAssetUrls(html: string): URL[] {
  const urls = new Map<string, URL>();
  const attributePattern = /\b(?:href|src)=["']([^"']+)["']/gi;
  let match: RegExpExecArray | null;

  while ((match = attributePattern.exec(html))) {
    const value = match[1];
    if (!value || value.startsWith("data:") || value.startsWith("blob:")) continue;

    const url = new URL(value, sw.registration.scope);
    const relativePath = scopeRelativePath(url);
    if (isSameOrigin(url) && (relativePath.startsWith("assets/") || relativePath === "manifest.webmanifest")) {
      urls.set(url.href, url);
    }
  }

  return [...urls.values()];
}

export {
  PUBLIC_SERVICE_DETAIL_ASSETS,
  hasPrivateWalletUrl,
  isPublicServiceDetailAsset,
  isPublicShellAsset,
  shouldBypassCache
};
