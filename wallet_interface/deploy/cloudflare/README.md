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

Origin API env:

- `WALLET_OPS_HEALTH_SHARED_SECRET`: should match
  `OPS_HEALTH_SHARED_SECRET`

## Deploy

```bash
cd wallet_interface/deploy/cloudflare
wrangler secret put OPS_HEALTH_SHARED_SECRET
wrangler deploy
```

## Scheduled checks

The cron trigger calls:

```text
GET {ORIGIN_API_BASE_URL}/ops/health?verify_storage=true
```

with:

```text
authorization: Bearer {OPS_HEALTH_SHARED_SECRET}
x-wallet-ops-scheduled: true
```

The origin deployment must validate this secret before exposing the route
publicly. If the API stays private behind Cloudflare Access or a tunnel, adapt
the Worker headers to that environment.
