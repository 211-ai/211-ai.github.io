export interface Env {
  ORIGIN_API_BASE_URL: string;
  OPS_HEALTH_SHARED_SECRET: string;
  OPS_HEALTH_VERIFY_STORAGE?: string;
  ORIGIN_AUTH_BEARER_TOKEN?: string;
  ORIGIN_AUTH_HEADER_NAME?: string;
  ORIGIN_AUTH_HEADER_VALUE?: string;
  CF_ACCESS_CLIENT_ID?: string;
  CF_ACCESS_CLIENT_SECRET?: string;
}

function normalizeBaseUrl(value: string): string {
  return value.endsWith("/") ? value.slice(0, -1) : value;
}

function verifyStorageEnabled(env: Env): string {
  const raw = `${env.OPS_HEALTH_VERIFY_STORAGE ?? "true"}`.trim().toLowerCase();
  return raw === "false" ? "false" : "true";
}

function buildUrl(env: Env, path: string, search: URLSearchParams): string {
  const url = new URL(`${normalizeBaseUrl(env.ORIGIN_API_BASE_URL)}${path}`);
  for (const [key, value] of search.entries()) {
    url.searchParams.set(key, value);
  }
  return url.toString();
}

function filteredHeaders(request: Request, env: Env): Headers {
  const headers = new Headers();
  const forwarded = ["accept", "content-type", "user-agent"];
  for (const name of forwarded) {
    const value = request.headers.get(name);
    if (value) {
      headers.set(name, value);
    }
  }
  headers.set("authorization", `Bearer ${env.OPS_HEALTH_SHARED_SECRET}`);
  headers.set("x-wallet-edge-proxy", "cloudflare-worker");
  applyOriginAuthHeaders(headers, env);
  return headers;
}

function applyOriginAuthHeaders(headers: Headers, env: Env): void {
  if (env.ORIGIN_AUTH_BEARER_TOKEN) {
    headers.set("x-wallet-origin-authorization", `Bearer ${env.ORIGIN_AUTH_BEARER_TOKEN}`);
  }
  if (env.ORIGIN_AUTH_HEADER_NAME && env.ORIGIN_AUTH_HEADER_VALUE) {
    headers.set(env.ORIGIN_AUTH_HEADER_NAME, env.ORIGIN_AUTH_HEADER_VALUE);
  }
  if (env.CF_ACCESS_CLIENT_ID && env.CF_ACCESS_CLIENT_SECRET) {
    headers.set("CF-Access-Client-Id", env.CF_ACCESS_CLIENT_ID);
    headers.set("CF-Access-Client-Secret", env.CF_ACCESS_CLIENT_SECRET);
  }
}

function methodAllowed(method: string): boolean {
  return method === "GET" || method === "HEAD";
}

async function proxy(request: Request, env: Env): Promise<Response> {
  const incoming = new URL(request.url);
  const target = buildUrl(env, incoming.pathname, incoming.searchParams);
  const response = await fetch(target, {
    method: request.method,
    headers: filteredHeaders(request, env),
    body: request.method === "GET" || request.method === "HEAD" ? undefined : request.body,
  });
  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers: response.headers,
  });
}

async function runScheduledHealth(env: Env): Promise<void> {
  const search = new URLSearchParams({
    verify_storage: verifyStorageEnabled(env),
  });
  const target = buildUrl(env, "/ops/health", search);
  const headers = new Headers({
    authorization: `Bearer ${env.OPS_HEALTH_SHARED_SECRET}`,
    "x-wallet-ops-scheduled": "true",
    "x-wallet-edge-proxy": "cloudflare-worker",
  });
  applyOriginAuthHeaders(headers, env);
  const response = await fetch(target, {
    method: "GET",
    headers,
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`Scheduled ops health failed: ${response.status} ${body}`);
  }
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    if (url.pathname === "/health" || url.pathname === "/ops/health") {
      if (!methodAllowed(request.method)) {
        return new Response("Method not allowed", {
          status: 405,
          headers: { allow: "GET, HEAD" },
        });
      }
      return proxy(request, env);
    }
    return new Response("Not found", { status: 404 });
  },

  async scheduled(_controller: ScheduledController, env: Env): Promise<void> {
    await runScheduledHealth(env);
  },
};
