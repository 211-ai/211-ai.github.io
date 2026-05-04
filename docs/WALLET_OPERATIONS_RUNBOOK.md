# Wallet Operations Runbook

This runbook covers the 211-AI wallet API backed by `ipfs_datasets_py.wallet`.
It assumes the API is deployed with durable wallet snapshots and encrypted blob
storage.

## Baseline

Required environment:

- `WALLET_REPOSITORY_ROOT` points to durable wallet metadata snapshots.
- `WALLET_STORAGE_CONFIG` points to encrypted blob storage with production
  replicas.
- `WALLET_PROOF_MODE=production`.
- `WALLET_PROOF_BACKEND` points to the active verifier backend.
- `WALLET_AUTO_LOAD_REPOSITORY=true`.
- `WALLET_AUTO_PERSIST=true`.

Health checks:

```bash
curl -fsS http://localhost:8000/health
curl -fsS \
  -H "authorization: Bearer ${WALLET_OPS_HEALTH_SHARED_SECRET}" \
  "http://localhost:8000/ops/health?verify_storage=true"
python -m wallet_interface.ops --max-runs 1 --fail-on-error
```

The ops-health report checks repository state, encrypted storage availability,
proof mode, revocation propagation, and privacy-budget ledger readability. Each
run writes an `ops/health` audit event for every loaded wallet.

## Lost Key Or Device

1. Identify the wallet ID and current controller DID from the Security screen or
   `GET /wallets/{wallet_id}`.
2. If the user still controls a valid controller, request the needed
   `wallet/admin` approval from the Security screen.
3. Revoke the lost device with `POST /wallets/{wallet_id}/devices/revoke`.
4. Rotate affected record keys from the UI or with
   `POST /wallets/{wallet_id}/records/{record_id}/rotate-key`.
5. Run ops health with storage verification and confirm `revocation_propagation`
   and `storage_availability` are not `error`.

If the user lost controller authority, use configured recovery contacts:

1. Confirm `governance_policy.recovery_policy.status` is `active`.
2. Have a recovery contact request `wallet/controller_recover` approval.
3. Collect the configured recovery threshold from recovery contacts.
4. Recover a new controller with `POST /wallets/{wallet_id}/controllers/recover`.
5. Rotate keys for sensitive records and save a fresh wallet snapshot.

## Revoked Grants

1. Revoke the grant from the Security or recipient-access workflow, or call
   `POST /wallets/{wallet_id}/grants/{grant_id}/revoke`.
2. Confirm descendant grants, grant receipts, access requests, and delegated key
   wraps are revoked.
3. Run:

   ```bash
   curl -fsS "http://localhost:8000/ops/health?verify_storage=false"
   ```

4. Treat `revocation_propagation=error` as urgent. Inspect the report's
   `dangling_key_wraps` list, then rotate the listed records.

## Proof Backend Failure

1. Check `proof_registry` in `/ops/health`.
2. If simulated proofs are enabled in production, set
   `WALLET_PROOF_MODE=production` and configure `WALLET_PROOF_BACKEND`.
3. Pause workflows that create new proof receipts until the verifier backend is
   healthy.
4. Existing proof receipts remain auditable by receipt hash and verifier
   metadata; do not expose witness data while debugging.

## Storage Outage

1. Run `/ops/health?verify_storage=true`.
2. For any record listed under `storage_availability.failures`, run the record
   storage repair endpoint:

   ```bash
   curl -X POST \
     -H "content-type: application/json" \
     -d '{"actor_did":"did:key:owner"}' \
     http://localhost:8000/wallets/{wallet_id}/records/{record_id}/storage/repair
   ```

3. Re-run ops health and verify the failed replica count is zero.
4. If the primary encrypted blob store is unavailable, restore from a mirror
   before accepting new uploads.

## Privacy Incident

1. Pause affected analytics templates by changing their status to `paused` or
   `retired`.
2. Stop new contributions for affected templates.
3. Inspect `/ops/health` for `privacy_budget=error`.
4. Export the affected wallet audit logs and analytics ledger snapshot.
5. Do not delete released aggregate history; preserve it for audit.
6. Resume analytics only after cohort thresholds, sparse-cell suppression, and
   epsilon budgets have been reviewed.

## Scheduled Worker

Run the worker as a sidecar or cron job:

```bash
python -m wallet_interface.ops \
  --watch \
  --interval-seconds 300 \
  --fail-on-error \
  --output-jsonl /var/log/211-ai/wallet-ops-health.jsonl
```

For cron, prefer a bounded run:

```bash
*/5 * * * * cd /srv/211-AI && python -m wallet_interface.ops --max-runs 1 --fail-on-error --output-jsonl /var/log/211-ai/wallet-ops-health.jsonl
```

## Kubernetes Reference

Reference manifests are under `wallet_interface/deploy/kubernetes/`.

Apply them in order:

```bash
kubectl apply -f wallet_interface/deploy/kubernetes/namespace.yaml
kubectl apply -f wallet_interface/deploy/kubernetes/configmap.yaml
kubectl apply -f wallet_interface/deploy/kubernetes/pvc.yaml
kubectl apply -f wallet_interface/deploy/kubernetes/api-deployment.yaml
kubectl apply -f wallet_interface/deploy/kubernetes/ops-deployment.yaml
kubectl apply -f wallet_interface/deploy/kubernetes/ui-deployment.yaml
kubectl apply -f wallet_interface/deploy/kubernetes/services.yaml
kubectl apply -f wallet_interface/deploy/kubernetes/ingress.yaml
```

Replace the example image tags, ingress hostname, storage config, and proof
backend before use on a real cluster.

## Cloudflare Reference Edge

Reference Worker assets are under `wallet_interface/deploy/cloudflare/`.

Use them when Cloudflare sits in front of the wallet API and you want:

- edge `/health` and `/ops/health` proxying
- a scheduled Cloudflare cron trigger for `/ops/health`

Required Worker configuration:

- `ORIGIN_API_BASE_URL`
- `OPS_HEALTH_SHARED_SECRET`
- optional `OPS_HEALTH_VERIFY_STORAGE`

Required origin API configuration when the route is protected:

- `WALLET_OPS_HEALTH_SHARED_SECRET`

The Worker reuses the existing Cloudflare account/token naming conventions from
`ipfs_datasets_py` documentation (`CLOUDFLARE_ACCOUNT_ID`,
`CLOUDFLARE_API_TOKEN`), but the wallet API still needs its own origin auth and
network controls. Do not expose `/ops/health` publicly without validating the
shared secret or equivalent edge identity.
