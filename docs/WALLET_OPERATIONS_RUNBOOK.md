# Wallet Operations Runbook

This runbook covers the 211-AI wallet API backed by `ipfs_datasets_py.wallet`.
It assumes the API is deployed with durable wallet snapshots and encrypted blob
storage.

Use `docs/WALLET_OPERATOR_INTEGRATOR_REFERENCE.md` for the stable API endpoint,
CLI command, MCP tool, environment, and release-check reference.
Use `docs/WALLET_RETENTION_POLICY.md` and
`docs/WALLET_TARGET_PRODUCTION_SIGNOFF.md` to map target datastore, storage,
backup, log, alert, and deletion-retention controls before launch.

## Baseline

Required environment:

- `WALLET_REPOSITORY_ROOT` points to durable wallet metadata snapshots.
- `WALLET_STORAGE_CONFIG` points to encrypted blob storage with production
  replicas.
- `WALLET_PROOF_MODE=production`.
- `WALLET_PROOF_BACKEND` points to the active verifier backend.
- When using the HTTP verifier adapter, set `WALLET_PROOF_SERVICE_URL`,
  `WALLET_PROOF_VERIFIER_ID`, `WALLET_PROOF_SYSTEM`, and verifier auth
  credentials.
- `WALLET_AUTO_LOAD_REPOSITORY=true`.
- `WALLET_AUTO_PERSIST=true`.

Health checks:

```bash
curl -fsS http://localhost:8000/health
curl -fsS \
  -H "authorization: Bearer ${WALLET_OPS_HEALTH_SHARED_SECRET}" \
  "http://localhost:8000/ops/health?verify_storage=true"
python -m wallet_interface.ops --max-runs 1 --fail-on-error
python -m wallet_interface.ops --validate-proof-contract --fail-on-error
python -m wallet_interface.ops --validate-distance-proof-contract --fail-on-error
python -m wallet_interface.ops --validate-production-readiness
python -m wallet_interface.ops \
  --validate-target-signoff-packet /path/to/target-signoff.json \
  --fail-on-error
```

The ops-health report checks repository state, encrypted storage availability,
proof mode, external verifier health when configured, revocation propagation,
and privacy-budget ledger readability. Each run writes an `ops/health` audit
event for every loaded wallet.

Run `--validate-production-readiness` in staging before launch and after secret
rotation. It fails if durable repository/storage env vars, production proof
mode, external verifier credentials, ops-health auth, alert routing, ops health,
or the verifier prove/verify contract are missing or unsafe placeholders. The
report shows only whether secret values are configured, not the values. Archive
the passing report with the completed target production signoff packet. The
readiness gate also requires secret-manager reference environment variables for
ops-health, alert, proof-verifier, and storage credentials; record the same
references in the target signoff JSON packet.

Optional alert routing:

- `WALLET_OPS_ALERT_WEBHOOK_URL`
- `WALLET_OPS_ALERT_ON=warning|error`
- `WALLET_OPS_ALERT_BEARER_TOKEN`
- `WALLET_OPS_ALERT_HEADER_NAME`
- `WALLET_OPS_ALERT_HEADER_VALUE`

When configured, `python -m wallet_interface.ops` sends a JSON webhook for each
matching report. This is the reference integration point for Slack, PagerDuty,
incident routers, or internal alert collectors.

Secret management templates:

- `wallet_interface/deploy/env.production.example` is the compose/Worker env
  template; copy it to an ignored local path before adding real values.
- `wallet_interface/deploy/kubernetes/secrets.example.yaml` is the direct
  Kubernetes Secret shape.
- `wallet_interface/deploy/kubernetes/externalsecret.example.yaml` maps the
  same keys from an external secret manager through External Secrets Operator.

CI blackbox staging harness:

```bash
python scripts/run_wallet_release_checks.py --dry-run
python scripts/run_wallet_release_checks.py --playwright-port 5185
```

The release-check runner prints or runs the backend pytest slice, wallet
`compileall`, UI build, and live full-stack Playwright checks in the documented
order. To run the same checks manually:

```bash
PYTHONPATH=/path/to/211-AI:/path/to/211-AI/ipfs_datasets_py \
IPFS_DATASETS_AUTO_INSTALL=false \
IPFS_AUTO_INSTALL=false \
IPFS_DATASETS_PY_MINIMAL_IMPORTS=1 \
python -m pytest \
  ipfs_datasets_py/tests/unit/test_data_wallet.py \
  ipfs_datasets_py/tests/mcp/test_wallet_tools.py \
  ipfs_datasets_py/tests/mcp/unit/test_hierarchical_tool_manager.py \
  tests/test_wallet_interface_api.py \
  tests/test_wallet_interface_ops.py \
  tests/test_wallet_interface_deploy.py \
  tests/test_wallet_implementation_plan_docs.py \
  tests/test_wallet_release_check_runner.py \
  tests/test_wallet_production_handoff_blackbox.py -q

python -m compileall -q wallet_interface ipfs_datasets_py/ipfs_datasets_py/wallet
cd wallet_interface/ui && PLAYWRIGHT_PORT=5185 npm run test:fullstack
```

This test starts a local HTTP verifier stub, runs
`python -m wallet_interface.ops --validate-production-readiness` through a real
subprocess with production-mode env vars, launches the wallet API with
`uvicorn`, drives public wallet/document/location/proof/redaction/analytics/ops
HTTP endpoints, exercises delegate UCAN decrypt/export grants, signed
invocations, encrypted export hash/schema verification/import/storage checks,
grant revocation, post-restart grant receipt/audit persistence, runs the wallet
CLI through separate subprocesses for the same sharing/export/analytics
persistence path, validates a completed signoff JSON packet, and verifies that a
verifier returning witness data fails the release gate.
The full-stack Playwright test starts a live wallet API with local durable
storage, seeds wallet records over HTTP, and drives the 211-AI export UI through
grant, invocation, encrypted bundle creation, verification, storage status,
descriptor import, and audit confirmation from desktop and mobile browser
projects.

## WALLET-210 Service Partner Pilot Drill

Run this drill in target staging before a 211 service-partner pilot, after
verifier or storage changes, and after analytics-template changes. Use
synthetic wallet data only. The drill proves that the UI and API can complete a
partner workflow backed by `ipfs_datasets_py.wallet` without leaking private
document text, precise coordinates, proof witnesses, or credential values.

Preflight gates:

- `python -m wallet_interface.ops --validate-production-readiness` passes for
  the staging deployment.
- The completed target signoff packet references the WALLET-180 verifier
  cutover packet, WALLET-190 retention/deletion dry-run evidence, and WALLET-200
  approved analytics template review.
- Browser origin, API origin, wallet repository, encrypted storage, verifier,
  ops-health secret, alert route, and secret-manager references match the
  staging environment under review.

Local automation:

```bash
pytest tests/test_wallet_interface_api.py tests/test_wallet_third_party_blackbox.py -q
npm --prefix wallet_interface/ui run build
npm --prefix wallet_interface/ui test -- tests/fullstack-wallet.spec.ts
```

Manual staging drill:

1. Create a synthetic wallet and sign in to the staging UI with that wallet ID,
   owner DID, and owner test key.
2. Add a document from the Uploads screen. Confirm the API audit has
   `record/add` and storage verification returns only ciphertext hashes/status.
3. Add a precise location through the wallet API. Do not paste the coordinates
   into screenshots, tickets, or shared logs.
4. Create a partner access request for the document with a named purpose, then
   approve it from Recipient Access. Confirm the grant receipt shows active
   status and the purpose caveat in API evidence.
5. Sign in as the partner and run the allowed analysis from Recipient Access.
   Confirm the result is a derived artifact and does not show disallowed
   plaintext.
6. Run service matching from the location record using owner access or a
   coarse-location invocation. Confirm response JSON contains service IDs,
   coarse reasons, and no latitude/longitude values.
7. Create a location-region proof from Proof Center. Confirm public inputs
   contain the service-region claim and policy hash, and no precise
   coordinates, witness payload, verifier credential, or address.
8. Submit one analytics contribution against an approved template and run the
   approved aggregate release endpoint. Confirm the template ID, consent ID,
   contribution ID, nullifier policy, k-threshold, epsilon spend, and result ID
   are captured without wallet identifiers in released aggregate output.
9. Revoke the partner access from Recipient Access, then retry the partner
   analysis, coarse-location, proof, and export paths that depended on the
   revoked grant or invocation. Each retry must fail closed.
10. Open Audit and verify the timeline includes the full workflow:
   `record/add`, `grant/create`, `access/approve`, `record/analyze`,
   `location/read_coarse`, `proof/create`, `analytics/consent_create`,
   `analytics/contribute`, `analytics/query`, `grant/revoke`, and
   `access/revoke` where those actions were used.

Pass criteria:

- UI screenshots show document upload, partner access, proof receipt, analytics
  choice or contribution evidence, revocation, and audit timeline.
- API evidence shows wallet-backed records, grants, proofs, analytics
  contributions, aggregate releases, revocations, and audit events.
- Evidence contains no raw document text, names, emails, phone numbers, SSNs,
  exact coordinates, addresses, proof witnesses, bearer tokens, header values,
  secret-manager resolved values, key material, or decrypted wallet payloads.
- Revoked grants and invocations fail on re-use.
- Operators can identify the rollback step, affected route, and responsible
  partner contact from the archived pilot ticket.

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

If using the HTTP verifier adapter:

5. Check connectivity and credentials for `WALLET_PROOF_SERVICE_URL`.
6. Confirm the verifier returns the expected `verifier_id`, `proof_system`, and
   circuit metadata for location-region proofs.
7. Treat `/ops/health` `proof_registry=error` as a production outage for new
   proof creation.
8. Run `python -m wallet_interface.ops --validate-proof-contract --fail-on-error`
   after credential rotation or verifier deployment.
9. Before enabling location-distance proof UI, run
   `python -m wallet_interface.ops --validate-distance-proof-contract --fail-on-error`
   in staging and confirm no wallet or target coordinates appear in receipts,
   public inputs, verifier logs, or errors.

The verifier request/response contract is documented in
`docs/WALLET_PROOF_VERIFIER_CONTRACT.md`.

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

## Target Storage Operations

Use `wallet_interface/deploy/storage-retention.example.json` as the target
storage checklist. Replace placeholder provider names, bucket names, secret
paths, lifecycle IDs, deal policy IDs, and evidence references in the target
evidence system; do not commit the completed file with live environment details.

Target storage credential requirements:

- `WALLET_STORAGE_CREDENTIAL_SECRET_REF` must point to the selected
  secret-manager entry for IPFS, Filecoin, S3, and local-replica credentials.
- `WALLET_STORAGE_CONFIG` must describe the encrypted primary and mirror
  topology. Example production shapes include a durable local primary with IPFS
  pin, S3 object, and Filecoin archival mirrors, or an S3 primary with IPFS and
  Filecoin mirrors when the S3 lifecycle policy is the primary retention
  control.
- Operators may record CIDs, S3 object keys, bucket policy IDs, Filecoin deal
  policy IDs, and ciphertext hashes in tickets. They must not paste wallet
  plaintext, proof witnesses, precise coordinates, key material, or secret
  values into tickets, logs, alert payloads, or signoff packets.

Storage repair validation:

```bash
curl -fsS \
  -H "authorization: Bearer ${WALLET_OPS_HEALTH_SHARED_SECRET}" \
  "${WALLET_API_ORIGIN}/ops/health?verify_storage=true"

curl -fsS -X POST \
  -H "content-type: application/json" \
  -H "authorization: Bearer ${WALLET_OPS_HEALTH_SHARED_SECRET}" \
  -d "{\"actor_did\":\"${WALLET_OWNER_DID}\"}" \
  "${WALLET_API_ORIGIN}/wallets/${WALLET_ID}/storage/repair"

python -m wallet_interface.ops --validate-production-readiness
```

The repair response should show `failed_replica_count=0` after repair and may
show `repaired_replica_count` for S3/IPFS/Filecoin mirrors. The report verifies
encrypted bytes and stored hashes only; if a repair run or alert contains raw
document text, precise location values, proof witnesses, or credential values,
treat it as a privacy incident.

Provider retention checks:

- IPFS: confirm encrypted CIDs are in the approved private pinset while active,
  and that deletion tickets remove pins after manifest references and key wraps
  are revoked.
- Filecoin: confirm new deals use the approved maximum expiration window and
  that renewal is blocked for deleted or expired wallet records.
- S3: confirm lifecycle rules cover the wallet prefix, current and noncurrent
  encrypted objects, incomplete multipart uploads, backup buckets, and legal
  hold exceptions.
- Backups: confirm wallet repository backups and encrypted blob backups purge
  under the approved SLA, with evidence that references ciphertext IDs only.
- Alerts: confirm alert-router retention matches the approved alert-retention
  period and that webhook payloads contain status metadata only.

## WALLET-190 Staging Retention And Deletion Dry Run

Run this dry run in target staging before launch, after storage-provider
changes, and after retention-policy changes. Use synthetic wallet data only.
Archive command output as evidence after redacting environment-specific hostnames
when needed; do not redact status fields, ciphertext hashes, storage types,
bundle hashes, tombstone IDs, or ticket IDs.

Required setup:

- Target staging uses the production-like `WALLET_REPOSITORY_ROOT`,
  `WALLET_STORAGE_CONFIG`, lifecycle policies, alert retention, and secret
  manager references that will be used at launch.
- The synthetic wallet has one owner DID, one delegate DID, one encrypted record,
  one analytics template and consent, and one export grant.
- The evidence ticket names the approved `retention_policy_version`,
  `backup_purge_sla`, IPFS pinset policy, Filecoin deal policy or not-used
  decision, S3 lifecycle policy, and alert-retention policy.

Dry-run sequence:

1. Create an encrypted record and confirm replica creation.

   ```bash
   curl -fsS \
     -H "authorization: Bearer ${WALLET_OPS_HEALTH_SHARED_SECRET}" \
     "${WALLET_API_ORIGIN}/wallets/${WALLET_ID}/records/${RECORD_ID}/storage"
   ```

   Evidence must show primary and mirror refs with `storage_type`, `size_bytes`,
   and `sha256` only. Plaintext record values, decrypted metadata, key material,
   and storage credentials are not allowed in the artifact.

2. Run replica health checks.

   ```bash
   curl -fsS \
     -H "authorization: Bearer ${WALLET_OPS_HEALTH_SHARED_SECRET}" \
     "${WALLET_API_ORIGIN}/wallets/${WALLET_ID}/storage"

   curl -fsS \
     -H "authorization: Bearer ${WALLET_OPS_HEALTH_SHARED_SECRET}" \
     "${WALLET_API_ORIGIN}/ops/health?verify_storage=true"
   ```

   Pass criteria: `failed_replica_count=0`, `storage_availability` is not
   `error`, and storage evidence contains ciphertext hashes/statuses only.

3. Rehearse repair.

   Remove or invalidate one non-production staging mirror replica through the
   provider console or test fixture, then run:

   ```bash
   curl -fsS -X POST \
     -H "content-type: application/json" \
     -H "authorization: Bearer ${WALLET_OPS_HEALTH_SHARED_SECRET}" \
     -d "{\"actor_did\":\"${WALLET_OWNER_DID}\"}" \
     "${WALLET_API_ORIGIN}/wallets/${WALLET_ID}/storage/repair"
   ```

   Pass criteria: the repair report returns `ok=true` and either
   `repaired_replica_count` or the per-record `repaired` status shows the mirror
   was restored.

4. Revoke the delegate grant and rotate the retained record key.

   ```bash
   curl -fsS -X POST \
     -H "content-type: application/json" \
     -d "{\"actor_did\":\"${WALLET_OWNER_DID}\"}" \
     "${WALLET_API_ORIGIN}/wallets/${WALLET_ID}/grants/${GRANT_ID}/revoke"

   curl -fsS -X POST \
     -H "content-type: application/json" \
     -d "{\"actor_did\":\"${WALLET_OWNER_DID}\"}" \
     "${WALLET_API_ORIGIN}/wallets/${WALLET_ID}/records/${RECORD_ID}/rotate-key"
   ```

   Then prove the revoked grant cannot decrypt, analyze, or export the record,
   and confirm `revocation_propagation` in `/ops/health` is not `error`.

5. Withdraw analytics consent.

   ```bash
   curl -fsS -X POST \
     -H "content-type: application/json" \
     -d "{\"actor_did\":\"${WALLET_OWNER_DID}\"}" \
     "${WALLET_API_ORIGIN}/wallets/${WALLET_ID}/analytics/consents/${CONSENT_ID}/revoke"
   ```

   Pass criteria: future contributions for that consent are rejected, and the
   retained evidence contains only consent ID, template ID, nullifier or ledger
   IDs, query-budget status, and audit event IDs.

6. Verify export-bundle retention behavior.

   Create the encrypted export bundle through the approved export workflow, then
   run:

   ```bash
   curl -fsS -X POST \
     -H "content-type: application/json" \
     -d @/path/to/redacted-export-bundle-request.json \
     "${WALLET_API_ORIGIN}/exports/verify"

   curl -fsS -X POST \
     -H "content-type: application/json" \
     -d @/path/to/redacted-export-bundle-request.json \
     "${WALLET_API_ORIGIN}/exports/storage"
   ```

   Record the bundle hash, record count, storage status, owner-copy retention
   decision, recipient retention terms, and expiration or purge ticket. Do not
   archive bundle plaintext or recipient secrets.

7. Delete one synthetic staging record and collect purge/audit evidence.

   Use the target deployment's approved record deletion control, whether it is
   an API route, CLI command, or scheduled purge job. The dry run is not
   complete until evidence shows manifest references and dependent key wraps are
   removed, encrypted storage unpin/delete actions are submitted, backup purge
   tracking is opened under the approved SLA, and a tombstone/audit event exists
   without plaintext. If the target has no record deletion control, record this
   as a launch blocker rather than approving the environment.

8. Run final readiness.

   ```bash
   python -m wallet_interface.ops --validate-production-readiness
   python scripts/run_wallet_release_checks.py --dry-run
   ```

   Attach the passing readiness report, release-check dry-run manifest,
   provider purge tickets, backup purge ticket, audit timeline, and reviewer
   leak-check result to the WALLET-190 evidence artifact.

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
  --alert-webhook-url https://ops.example.com/hooks/211-wallet \
  --alert-on error \
  --alert-bearer-token "${WALLET_OPS_ALERT_BEARER_TOKEN}" \
  --output-jsonl /var/log/211-ai/wallet-ops-health.jsonl
```

For cron, prefer a bounded run:

```bash
*/5 * * * * cd /srv/211-AI && python -m wallet_interface.ops --max-runs 1 --fail-on-error --alert-webhook-url https://ops.example.com/hooks/211-wallet --alert-on error --alert-bearer-token "${WALLET_OPS_ALERT_BEARER_TOKEN}" --output-jsonl /var/log/211-ai/wallet-ops-health.jsonl
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
- optional `CF_ACCESS_CLIENT_ID` and `CF_ACCESS_CLIENT_SECRET` for Cloudflare
  Access service-token protected origins
- optional `ORIGIN_AUTH_HEADER_NAME` and `ORIGIN_AUTH_HEADER_VALUE` for
  environment-specific origin gateways
- optional `ORIGIN_AUTH_BEARER_TOKEN` for a bearer-like origin gateway token
  sent outside the API route's own `Authorization` header

Required origin API configuration when the route is protected:

- `WALLET_OPS_HEALTH_SHARED_SECRET`

The Worker reuses the existing Cloudflare account/token naming conventions from
`ipfs_datasets_py` documentation (`CLOUDFLARE_ACCOUNT_ID`,
`CLOUDFLARE_API_TOKEN`), but the wallet API still needs its own origin auth and
network controls. Do not expose `/ops/health` publicly without validating the
shared secret or equivalent edge identity. The Worker rejects non-GET/HEAD
methods and only proxies `/health` and `/ops/health`.
