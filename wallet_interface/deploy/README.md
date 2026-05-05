# Wallet Deployment

This directory contains reference deployment assets for the 211-AI wallet API,
wallet UI, and ops-health worker.

For the stable API, CLI, MCP, and release-check reference, see
`docs/WALLET_OPERATOR_INTEGRATOR_REFERENCE.md`. For the external proof verifier
HTTP contract, see `docs/WALLET_PROOF_VERIFIER_CONTRACT.md`.

Build context is the repository root:

```bash
docker compose -f wallet_interface/deploy/docker-compose.wallet.yml up --build
```

For environment-specific secrets, copy
`wallet_interface/deploy/env.production.example` to an ignored local file and
run compose with `--env-file`. Do not commit the populated file.

When using the compose file for anything beyond local integration, export:

```bash
export WALLET_OPS_HEALTH_SHARED_SECRET=replace-me
export WALLET_OPS_ALERT_WEBHOOK_URL=https://ops.example.com/hooks/211-wallet
export WALLET_OPS_ALERT_ON=error
export WALLET_OPS_ALERT_BEARER_TOKEN=replace-me
export WALLET_OPS_ALERT_HEADER_NAME=x-wallet-alert-key
export WALLET_OPS_ALERT_HEADER_VALUE=replace-me
export WALLET_OPS_HEALTH_SECRET_REF=secret-manager://replace-me
export WALLET_OPS_ALERT_SECRET_REF=secret-manager://replace-me
export WALLET_STORAGE_CREDENTIAL_SECRET_REF=secret-manager://replace-me
export WALLET_PROOF_BACKEND=http-location-region
export WALLET_PROOF_SERVICE_URL=https://verifier.example.com
export WALLET_PROOF_VERIFIER_ID=verifier-http-v1
export WALLET_PROOF_SYSTEM=groth16
export WALLET_PROOF_CIRCUIT_ID=location-region-v1
export WALLET_PROOF_DISTANCE_PROVE_PATH=/prove/location-distance
export WALLET_PROOF_BEARER_TOKEN=replace-me
export WALLET_PROOF_CREDENTIAL_SECRET_REF=secret-manager://replace-me
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
origin API, supports Cloudflare Access/custom origin-auth headers, rejects
non-health routes at the edge, and can run scheduled ops-health checks.

Required production environment:

- `WALLET_REPOSITORY_ROOT`: durable wallet metadata, audit, grant, revocation,
  and analytics ledger snapshots.
- `WALLET_STORAGE_CONFIG`: encrypted blob storage config. Use replicated
  storage for production, for example local primary plus S3/IPFS/Filecoin
  mirrors.
- `WALLET_PROOF_MODE=production`: disables simulated proof acceptance.
- `WALLET_PROOF_BACKEND`: production verifier backend selection. Supported
  values now include `http-location-region` for an external verifier service.
- `WALLET_PROOF_SERVICE_URL`: required when
  `WALLET_PROOF_BACKEND=http-location-region`.
- `WALLET_PROOF_VERIFIER_ID`, `WALLET_PROOF_SYSTEM`,
  `WALLET_PROOF_CIRCUIT_ID`: verifier metadata for the HTTP backend.
- `WALLET_PROOF_PROVE_PATH`, `WALLET_PROOF_DISTANCE_PROVE_PATH`,
  `WALLET_PROOF_VERIFY_PATH`: optional HTTP backend endpoint overrides.
- `WALLET_PROOF_BEARER_TOKEN`: optional bearer token for the proof service.
- `WALLET_PROOF_HTTP_HEADER_NAME` / `WALLET_PROOF_HTTP_HEADER_VALUE`: optional
  custom header pair for the proof service.
- `WALLET_PROOF_TIMEOUT_SECONDS`: optional proof backend timeout.
- `WALLET_AUTO_LOAD_REPOSITORY=true`: loads wallet snapshots on API/worker
  start.
- `WALLET_AUTO_PERSIST=true`: persists snapshots after state-changing wallet
  operations, including ops-health audit events.
- `WALLET_OPS_HEALTH_SHARED_SECRET`: when set, `/ops/health` requires either
  `Authorization: Bearer ...` or `X-Wallet-Ops-Shared-Secret`.
- `WALLET_API_CORS_ORIGINS`: comma-separated browser origin allow-list for
  split API/UI deployments. Leave unset when a same-origin gateway fronts both.
- `WALLET_OPS_ALERT_WEBHOOK_URL`: optional webhook target for warning/error
  ops-health alerts emitted by `python -m wallet_interface.ops`.
- `WALLET_OPS_ALERT_ON`: optional minimum alert severity, `warning` or `error`.
- `WALLET_OPS_ALERT_BEARER_TOKEN`: optional bearer token for the alert webhook.
- `WALLET_OPS_ALERT_HEADER_NAME` / `WALLET_OPS_ALERT_HEADER_VALUE`: optional
  custom header pair for receivers that do not use bearer auth.
- `WALLET_OPS_HEALTH_SECRET_REF`, `WALLET_OPS_ALERT_SECRET_REF`,
  `WALLET_PROOF_CREDENTIAL_SECRET_REF`, and
  `WALLET_STORAGE_CREDENTIAL_SECRET_REF`: non-secret secret-manager reference
  paths required by the production readiness report and target signoff packet.

The included compose file uses local volumes and defaults to the deterministic
location-region proof backend as an integration-safe production-mode stand-in.
Switch `WALLET_PROOF_BACKEND` to `http-location-region` and provide the proof
service vars before handling real user data. `GET /ops/health` will actively
probe that verifier backend when configured.

Before promoting a verifier-backed environment, run:

```bash
python -m wallet_interface.ops --validate-proof-contract --fail-on-error
python -m wallet_interface.ops --validate-distance-proof-contract --fail-on-error
python -m wallet_interface.ops --validate-production-readiness --fail-on-error
python -m wallet_interface.ops \
  --validate-target-signoff-packet /path/to/target-signoff.json \
  --fail-on-error
```

from the API/ops worker environment. This checks the external verifier health,
prove, verify, and no-witness-leak contract using synthetic witnesses, then
checks the completed retention, credential-reference, staging-artifact, and
organization-review packet.

The Cloudflare Worker assets are reference glue only. They do not replace the
Python API or local `wallet_interface.ops` worker; they front or trigger those
services.
