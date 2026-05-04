# Wallet Deployment

This directory contains reference deployment assets for the 211-AI wallet API,
wallet UI, and ops-health worker.

Build context is the repository root:

```bash
docker compose -f wallet_interface/deploy/docker-compose.wallet.yml up --build
```

Services:

- `wallet-api`: runs `uvicorn wallet_interface.asgi:app` on port `8000`.
- `wallet-ops`: runs `python -m wallet_interface.ops --watch` every 300 seconds
  and appends JSONL reports under `/var/log/211-ai`.
- `wallet-ui`: serves the built React UI on port `8080`.

Kubernetes reference manifests live in `wallet_interface/deploy/kubernetes/`.
They cover namespace, config, persistent state, API, UI, ops worker, services,
and ingress.

Cloudflare reference edge assets live in `wallet_interface/deploy/cloudflare/`.
They provide a narrow Worker that proxies `/health` and `/ops/health` to the
origin API and can run scheduled ops-health checks from the edge.

Required production environment:

- `WALLET_REPOSITORY_ROOT`: durable wallet metadata, audit, grant, revocation,
  and analytics ledger snapshots.
- `WALLET_STORAGE_CONFIG`: encrypted blob storage config. Use replicated
  storage for production, for example local primary plus S3/IPFS/Filecoin
  mirrors.
- `WALLET_PROOF_MODE=production`: disables simulated proof acceptance.
- `WALLET_PROOF_BACKEND`: production verifier backend selection.
- `WALLET_AUTO_LOAD_REPOSITORY=true`: loads wallet snapshots on API/worker
  start.
- `WALLET_AUTO_PERSIST=true`: persists snapshots after state-changing wallet
  operations, including ops-health audit events.
- `WALLET_OPS_HEALTH_SHARED_SECRET`: when set, `/ops/health` requires either
  `Authorization: Bearer ...` or `X-Wallet-Ops-Shared-Secret`.

The included compose file uses local volumes and the deterministic
location-region proof backend as an integration-safe production-mode stand-in.
Replace storage and proof settings before handling real user data.

The Cloudflare Worker assets are reference glue only. They do not replace the
Python API or local `wallet_interface.ops` worker; they front or trigger those
services.
