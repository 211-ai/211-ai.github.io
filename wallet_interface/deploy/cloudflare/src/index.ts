export interface Env {
  ORIGIN_API_BASE_URL: string;
  OPS_HEALTH_SHARED_SECRET: string;
  OPS_HEALTH_VERIFY_STORAGE?: string;
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
  return headers;
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
  const response = await fetch(target, {
    method: "GET",
    headers: {
      authorization: `Bearer ${env.OPS_HEALTH_SHARED_SECRET}`,
      "x-wallet-ops-scheduled": "true",
      "x-wallet-edge-proxy": "cloudflare-worker",
    },
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
      return proxy(request, env);
    }
    return new Response("Not found", { status: 404 });
  },

  async scheduled(_controller: ScheduledController, env: Env): Promise<void> {
    await runScheduledHealth(env);
  },
};
