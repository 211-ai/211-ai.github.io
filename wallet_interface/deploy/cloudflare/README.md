# Cloudflare Wallet Edge

This directory contains reference Cloudflare deployment assets for the
211-AI wallet interface.

The Worker is intentionally narrow:

- proxies `/health` to the origin wallet API
- proxies `/ops/health` to the origin wallet API
- runs a scheduled trigger that calls the origin `/ops/health` endpoint with
  storage verification enabled

This is edge/runtime glue, not a replacement for the wallet API. The Python
API, repository persistence, encrypted storage, and wallet ops worker remain
the system of record.

## Files

- `wrangler.toml`: Worker configuration and cron trigger.
- `src/index.ts`: request proxy and scheduled health trigger.

## Required secrets and vars

Reuse the existing Cloudflare environment naming conventions already used in
`ipfs_datasets_py` where possible:

- `CLOUDFLARE_ACCOUNT_ID`
- `CLOUDFLARE_API_TOKEN`

Worker-specific vars:

- `ORIGIN_API_BASE_URL`: wallet API origin, for example
  `https://wallet-api.internal.example.com`
- `OPS_HEALTH_SHARED_SECRET`: bearer secret for scheduled ops checks
- `OPS_HEALTH_VERIFY_STORAGE`: optional, defaults to `true`

Optional origin auth:

- `CF_ACCESS_CLIENT_ID` and `CF_ACCESS_CLIENT_SECRET`: sent as
  `CF-Access-Client-Id` and `CF-Access-Client-Secret` for origins protected by
  Cloudflare Access service tokens.
- `ORIGIN_AUTH_HEADER_NAME` and `ORIGIN_AUTH_HEADER_VALUE`: sent as a custom
  origin-auth header pair for tunnel gateways, internal load balancers, or
  zero-trust proxies.
- `ORIGIN_AUTH_BEARER_TOKEN`: sent as `X-Wallet-Origin-Authorization:
  Bearer ...` when the origin gateway expects a bearer-like token outside the
  API route's own `Authorization` header.

Keep `OPS_HEALTH_SHARED_SECRET` even when origin auth is enabled so
`/ops/health` stays independently protected at the application layer.

Origin API env:

- `WALLET_OPS_HEALTH_SHARED_SECRET`: should match
  `OPS_HEALTH_SHARED_SECRET`

## Deploy

```bash
cd wallet_interface/deploy/cloudflare
wrangler secret put ORIGIN_API_BASE_URL
wrangler secret put OPS_HEALTH_SHARED_SECRET
wrangler secret put CF_ACCESS_CLIENT_ID
wrangler secret put CF_ACCESS_CLIENT_SECRET
wrangler deploy
```

Use only the secrets that apply to the target environment. For non-Cloudflare
Access origins, set `ORIGIN_AUTH_HEADER_NAME` and `ORIGIN_AUTH_HEADER_VALUE`
instead of the `CF_ACCESS_*` secrets.

## Scheduled checks

The cron trigger calls:

```text
GET {ORIGIN_API_BASE_URL}/ops/health?verify_storage=true
```

with:

```text
authorization: Bearer {OPS_HEALTH_SHARED_SECRET}
x-wallet-ops-scheduled: true
x-wallet-edge-proxy: cloudflare-worker
```

The origin deployment must validate this secret before exposing the route
publicly. If the API stays private behind Cloudflare Access or a tunnel, adapt
the Worker secrets to that environment. The Worker only proxies `GET` and
`HEAD` for `/health` and `/ops/health`; all other paths and methods are
rejected at the edge.
