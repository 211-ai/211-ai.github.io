# Wallet Operator and Integrator Reference

This reference covers the 211-AI wallet API, local `ipfs-datasets wallet` CLI,
and wallet MCP tools backed by `ipfs_datasets_py.wallet`.

The wallet core owns encryption, UCAN-style authorization, proof receipt
verification, redaction, analytics privacy checks, exports, storage repair, and
audit events. `wallet_interface/` is the app/API/UI layer around that core.

## Production Boundary

- Raw record payloads and private metadata stay encrypted in wallet storage.
- Delegated access requires a grant or signed `wallet-ucan-v1` invocation token.
- `record/analyze` does not grant plaintext decrypt.
- Location workflows should prefer coarse claims or proofs over precise
  coordinates.
- Redacted document outputs must not include extracted entity text, document
  text, emails, phone numbers, SSNs, or street addresses.
- Analytics releases require template approval, consent, nullifier checks,
  k-thresholds, suppression, query-budget accounting, and audit events.
- Production proof mode must fail closed if a non-simulated backend is missing
  or unhealthy.

## Runtime Configuration

Minimum production API/worker environment:

```bash
WALLET_REPOSITORY_ROOT=/var/lib/211-ai/wallet-repository
WALLET_STORAGE_CONFIG='{"primary":{"type":"local","root":"/var/lib/211-ai/wallet-blobs"}}'
WALLET_AUTO_LOAD_REPOSITORY=true
WALLET_AUTO_PERSIST=true
WALLET_PROOF_MODE=production
WALLET_PROOF_BACKEND=http-location-region
WALLET_PROOF_SERVICE_URL=https://verifier.example.com
WALLET_PROOF_VERIFIER_ID=verifier-http-v1
WALLET_PROOF_SYSTEM=groth16
WALLET_PROOF_CIRCUIT_ID=location-region-v1
WALLET_OPS_HEALTH_SHARED_SECRET=replace-me
```

Optional production settings:

- `WALLET_STORAGE_ROOT`, `WALLET_STORAGE_BUCKET`, `WALLET_STORAGE_PREFIX`,
  `WALLET_STORAGE_PIN`, and `WALLET_STORAGE_MIRRORS` can build
  `WALLET_STORAGE_CONFIG` from individual environment variables.
- `WALLET_PROOF_PROVE_PATH`, `WALLET_PROOF_DISTANCE_PROVE_PATH`, and
  `WALLET_PROOF_VERIFY_PATH` override the HTTP proof backend endpoints.
- `WALLET_PROOF_BEARER_TOKEN` or
  `WALLET_PROOF_HTTP_HEADER_NAME` / `WALLET_PROOF_HTTP_HEADER_VALUE` add proof
  service authentication.
- `WALLET_PROOF_TIMEOUT_SECONDS` controls proof backend timeout.
- `WALLET_OPS_ALERT_WEBHOOK_URL`, `WALLET_OPS_ALERT_ON`,
  `WALLET_OPS_ALERT_BEARER_TOKEN`, and
  `WALLET_OPS_ALERT_HEADER_NAME` / `WALLET_OPS_ALERT_HEADER_VALUE` configure
  worker alert delivery.

Secret templates live at:

- `wallet_interface/deploy/env.production.example`
- `wallet_interface/deploy/kubernetes/secrets.example.yaml`
- `wallet_interface/deploy/kubernetes/externalsecret.example.yaml`

The external location proof verifier contract is documented in
`docs/WALLET_PROOF_VERIFIER_CONTRACT.md`. Use
`python -m wallet_interface.ops --validate-proof-contract` for
`location_region` and
`python -m wallet_interface.ops --validate-distance-proof-contract` before
exposing live `location_distance` proof UI.

The wallet UCAN invocation profile and UCAN-compatible inspection envelope are
documented in `docs/WALLET_UCAN_PROFILE.md`.

## API Reference

Run the API with:

```bash
uvicorn wallet_interface.asgi:app --host 0.0.0.0 --port 8000
```

FastAPI publishes full request/response schemas at `/openapi.json` and Swagger
UI at `/docs` when the deployment allows those routes.

### Health and Snapshots

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Basic API liveness. |
| `GET` | `/ops/health` | Repository, storage, proof, revocation, and privacy-budget health; accepts `verify_storage=true`. |
| `GET` | `/wallets/snapshots` | List wallet snapshots known to the repository. |
| `POST` | `/wallets/snapshots/save-all` | Persist all loaded wallet snapshots. |
| `POST` | `/wallets/snapshots/load-all` | Load all repository wallet snapshots. |
| `POST` | `/wallets/{wallet_id}/snapshot` | Save one wallet snapshot. |
| `GET` | `/wallets/{wallet_id}/snapshot` | Export one wallet snapshot. |
| `POST` | `/wallets/{wallet_id}/snapshot/load` | Import one wallet snapshot. |

Protect `/ops/health` in production with `WALLET_OPS_HEALTH_SHARED_SECRET`.
The client can send either `Authorization: Bearer <secret>` or
`X-Wallet-Ops-Shared-Secret: <secret>`.

### Wallet Authority

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/wallets` | Create a wallet with owner/controller policy. |
| `GET` | `/wallets/{wallet_id}` | Fetch wallet descriptor, policy, controllers, and devices. |
| `POST` | `/wallets/{wallet_id}/controllers` | Add a controller, subject to wallet governance. |
| `POST` | `/wallets/{wallet_id}/controllers/remove` | Remove a controller. |
| `POST` | `/wallets/{wallet_id}/devices` | Add a device key. |
| `POST` | `/wallets/{wallet_id}/devices/revoke` | Revoke a device key. |
| `POST` | `/wallets/{wallet_id}/recovery-policy` | Set recovery contacts and threshold. |
| `POST` | `/wallets/{wallet_id}/controllers/recover` | Recover controller authority from recovery-contact approvals. |
| `POST` | `/wallets/{wallet_id}/approvals` | Request threshold approval for sensitive operations. |
| `GET` | `/wallets/{wallet_id}/approvals` | List approval requests. |
| `POST` | `/wallets/{wallet_id}/approvals/{approval_id}/approve` | Add an approver to a threshold approval request. |
| `POST` | `/wallets/{wallet_id}/emergency-revoke` | Revoke non-owner grants and optionally rotate keys. |

### Records and Storage

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/wallets/{wallet_id}/documents/text` | Add an encrypted text document. |
| `POST` | `/wallets/{wallet_id}/documents` | Add an encrypted uploaded document. |
| `POST` | `/wallets/{wallet_id}/locations` | Add encrypted precise location data. |
| `GET` | `/wallets/{wallet_id}/records` | List wallet records without plaintext. |
| `POST` | `/wallets/{wallet_id}/records/{record_id}/decrypt` | Decrypt when actor has `record/decrypt` or a valid invocation. |
| `POST` | `/wallets/{wallet_id}/records/{record_id}/rotate-key` | Rotate the active record key and re-wrap authorized recipients. |
| `GET` | `/wallets/{wallet_id}/records/{record_id}/storage` | Verify encrypted storage for one record. |
| `GET` | `/wallets/{wallet_id}/storage` | Verify wallet-level encrypted storage. |
| `POST` | `/wallets/{wallet_id}/storage/repair` | Repair wallet-level encrypted storage replicas. |
| `POST` | `/wallets/{wallet_id}/records/{record_id}/storage/repair` | Repair encrypted storage for one record. |

### Grants, Invocations, and Access Requests

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/wallets/{wallet_id}/records/{record_id}/analysis-grants` | Create a bounded `record/analyze` grant. |
| `POST` | `/wallets/{wallet_id}/records/{record_id}/grants` | Create a custom record grant with abilities/output caveats. |
| `POST` | `/wallets/{wallet_id}/records/{record_id}/analysis-invocations` | Issue a signed analysis invocation token. |
| `POST` | `/wallets/{wallet_id}/records/{record_id}/decrypt-invocations` | Issue a signed decrypt invocation token. |
| `POST` | `/wallets/{wallet_id}/grants/{parent_grant_id}/delegate` | Delegate attenuated child capabilities. |
| `POST` | `/wallets/{wallet_id}/grants/{grant_id}/revoke` | Revoke a grant and dependent access. |
| `GET` | `/wallets/{wallet_id}/grant-receipts` | List grant receipts visible to a recipient. |
| `POST` | `/wallets/{wallet_id}/access-requests` | Third party requests access to wallet records. |
| `GET` | `/wallets/{wallet_id}/access-requests` | List access requests. |
| `POST` | `/wallets/{wallet_id}/access-requests/{request_id}/approve` | Approve request and optionally issue invocation. |
| `POST` | `/wallets/{wallet_id}/access-requests/{request_id}/reject` | Reject request. |
| `POST` | `/wallets/{wallet_id}/access-requests/{request_id}/revoke` | Revoke an approved request. |

Invocation-enabled endpoints accept `invocation_token` in the request body. The
API verifies the token signature, grant, actor, resource, ability, expiration,
revocation state, purpose, user presence, and output-type caveats before
calling the wallet operation.

### Document Analysis

| Method | Path | Required output type | Purpose |
| --- | --- | --- | --- |
| `POST` | `/wallets/{wallet_id}/records/{record_id}/analyze` | `summary` | Derived summary artifact. |
| `POST` | `/wallets/{wallet_id}/records/{record_id}/analyze/redacted` | `redacted_derived_only` | Redacted derived facts and need categories. |
| `POST` | `/wallets/{wallet_id}/records/{record_id}/vector-profile` | `vector_profile` | Redacted lexical/vector profile metadata. |
| `POST` | `/wallets/{wallet_id}/records/{record_id}/extract-text/redacted` | `redacted_extracted_text` | Redacted extracted document text and extraction metadata. |
| `POST` | `/wallets/{wallet_id}/records/{record_id}/forms/analyze/redacted` | `redacted_form_analysis` | Redacted form fields and form stats. |
| `POST` | `/wallets/{wallet_id}/records/analyze/redacted` | `redacted_derived_only` | Cross-record redacted analysis over explicit record IDs. |
| `POST` | `/wallets/{wallet_id}/records/graphrag/redacted` | `redacted_graphrag` | Redacted GraphRAG graph over explicit document records. |

Redacted GraphRAG returns record/category/redaction/entity-type graph nodes and
edges. Entity strings and document text are not returned. First production uses
`wallet-local-redacted-graphrag-v1`: wallet-local execution, model-backed
extraction disabled, encrypted artifact storage, and entity-type-count-only
safe output.

### Location, Proofs, and Service Matching

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/wallets/{wallet_id}/locations/{location_record_id}/coarse-grants` | Grant coarse-location access. |
| `POST` | `/wallets/{wallet_id}/locations/{location_record_id}/coarse-invocations` | Issue coarse-location invocation token. |
| `POST` | `/wallets/{wallet_id}/locations/{location_record_id}/region-proof-grants` | Grant location-region proof creation. |
| `POST` | `/wallets/{wallet_id}/locations/{location_record_id}/region-proofs` | Create a proof receipt for service-area membership. |
| `POST` | `/wallets/{wallet_id}/locations/{location_record_id}/distance-proof-grants` | Grant location-distance proof creation for a target and threshold. |
| `POST` | `/wallets/{wallet_id}/locations/{location_record_id}/distance-proofs` | Create a proof receipt that a wallet location is within a target distance. |
| `GET` | `/wallets/{wallet_id}/proofs` | List proof receipts for proof-center views. |
| `POST` | `/wallets/{wallet_id}/services/match` | Match services using wallet coarse/proven data. |
| `POST` | `/services/match-derived` | Match services from caller-provided derived/coarse facts. |

### Exports

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/wallets/{wallet_id}/exports/grants` | Create bounded `export/create` grant. |
| `POST` | `/wallets/{wallet_id}/exports/invocations` | Issue signed export invocation token. |
| `POST` | `/wallets/{wallet_id}/exports` | Create encrypted export bundle. |
| `POST` | `/exports/verify` | Verify export bundle hash and schema. |
| `POST` | `/exports/import` | Import encrypted descriptors from a verified bundle. |
| `POST` | `/exports/storage` | Verify encrypted blob availability for a bundle. |

### Analytics

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/analytics/templates` | Register an analytics template. |
| `GET` | `/analytics/templates` | List approved templates by default. |
| `GET` | `/wallets/{wallet_id}/analytics/consents` | List wallet consents. |
| `POST` | `/wallets/{wallet_id}/analytics/consents/from-template` | Create consent from an approved template. |
| `POST` | `/wallets/{wallet_id}/analytics/consents/{consent_id}/revoke` | Withdraw consent for future contributions. |
| `POST` | `/wallets/{wallet_id}/analytics/contributions` | Submit derived-field contribution with nullifier/proof receipt. |
| `POST` | `/analytics/{template_id}/count` | Release private aggregate count when policy allows. |
| `POST` | `/analytics/{template_id}/count-by-fields` | Release sparse-cell-safe grouped counts. |

### Audit

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/wallets/{wallet_id}/audit` | Return wallet audit timeline. |

Audit events are append-only hash-linked records. They should be exported for
incident response and retained according to the deployment retention policy in
`docs/WALLET_RETENTION_POLICY.md`.

## CLI Reference

The local CLI persists snapshots under `~/.ipfs_datasets/wallet/manifests` and
encrypted blobs under `~/.ipfs_datasets/wallet/blobs` unless overridden:

```bash
ipfs-datasets wallet --wallet-dir ./wallets --blob-dir ./wallet-blobs --json <command>
```

Common commands:

| Command | Purpose |
| --- | --- |
| `generate-key` | Generate a 32-byte local key. |
| `create` | Create a wallet manifest. |
| `add` | Encrypt and add a document record from a local file. |
| `list` | List wallet records without plaintext. |
| `share` | Create a simple analyze/decrypt record grant. |
| `grant` | Create a custom record grant with abilities/output caveats. |
| `issue-invocation` | Issue a signed invocation token for a record grant. |
| `analyze` | Run derived summary analysis with direct grant/owner access. |
| `analyze-invocation` | Run summary analysis with an invocation token. |
| `decrypt` | Decrypt a record to a local file with direct grant/owner access. |
| `decrypt-invocation` | Decrypt a record with an invocation token. |
| `revoke` | Revoke a grant. |
| `grant-receipts` | List grant receipts. |
| `request-access` | Create a third-party access request. |
| `access-requests` | List access requests. |
| `approve-access` | Approve access and optionally issue invocation. |
| `reject-access` | Reject an access request. |
| `revoke-access` | Revoke an approved access request. |
| `request-approval` | Request threshold approval. |
| `approve-approval` | Approve a threshold request. |
| `export-grant` | Grant bounded encrypted export access. |
| `export-invocation` | Issue signed export invocation token. |
| `export-bundle` | Create an encrypted export bundle. |
| `verify-export-bundle` | Verify bundle hash/schema. |
| `import-export-bundle` | Import encrypted descriptors from a verified bundle. |
| `export-bundle-storage` | Verify encrypted blob availability for a bundle. |
| `verify-storage` | Verify encrypted record storage replicas. |
| `repair-storage` | Repair encrypted record storage replicas. |
| `analytics-template` | Register an aggregate analytics template. |
| `analytics-templates` | List analytics templates. |
| `analytics-consent` | Create consent from a template. |
| `analytics-contribute` | Submit derived analytics fields as `KEY=VALUE`. |
| `analytics-count` | Run a private aggregate count. |
| `audit` | Show wallet audit event count and hash head. |

Example analysis-only share:

```bash
OWNER_KEY=$(ipfs-datasets wallet --json generate-key | jq -r .key_hex)
DELEGATE_KEY=$(ipfs-datasets wallet --json generate-key | jq -r .key_hex)
ipfs-datasets wallet --json create --owner-did did:key:owner
ipfs-datasets wallet --json add \
  --wallet-id wallet-... \
  --actor-did did:key:owner \
  --key-hex "${OWNER_KEY}" \
  --path ./intake.pdf
ipfs-datasets wallet --json share \
  --wallet-id wallet-... \
  --record-id record-... \
  --issuer-did did:key:owner \
  --audience-did did:key:delegate \
  --issuer-key-hex "${OWNER_KEY}" \
  --recipient-key-hex "${DELEGATE_KEY}" \
  --can record/analyze \
  --output-type summary \
  --issue-invocation
```

## MCP Wallet Tools

Wallet MCP tools are thin wrappers around `ipfs_datasets_py.wallet` and use the
same local snapshot/blob persistence conventions as the CLI.

| Tool | Purpose |
| --- | --- |
| `wallet_create` | Create a wallet. |
| `wallet_add_document` | Add an encrypted document. |
| `wallet_add_location` | Add encrypted location data. |
| `wallet_list_records` | List wallet records. |
| `wallet_create_location_region_proof` | Create a location-region proof receipt. |
| `wallet_analyze_document_redacted` | Run redacted document analysis. |
| `wallet_extract_document_text_redacted` | Extract redacted document text. |
| `wallet_analyze_document_form_redacted` | Analyze redacted form fields/stats. |
| `wallet_create_document_vector_profile` | Create redacted vector-profile artifact. |
| `wallet_analyze_documents_redacted` | Run cross-record redacted analysis. |
| `wallet_create_redacted_graphrag` | Create redacted GraphRAG artifact. |
| `wallet_analytics_create_template` | Register analytics template. |
| `wallet_analytics_create_consent` | Create analytics consent. |
| `wallet_analytics_contribute` | Submit analytics contribution. |
| `wallet_analytics_private_count` | Run private aggregate count. |

MCP tools must enforce the same grants, invocation caveats, storage rules,
redaction policies, and audit boundaries as the Python service API.

## Release Checks

Before a production release:

```bash
PYTHONPATH=/path/to/211-AI/ipfs_datasets_py \
IPFS_DATASETS_AUTO_INSTALL=false \
IPFS_AUTO_INSTALL=false \
IPFS_DATASETS_PY_MINIMAL_IMPORTS=1 \
python -m pytest \
  ipfs_datasets_py/tests/unit/test_data_wallet.py \
  ipfs_datasets_py/tests/mcp/test_wallet_tools.py \
  ipfs_datasets_py/tests/mcp/unit/test_hierarchical_tool_manager.py \
  tests/test_wallet_interface_api.py -q

python -m compileall -q wallet_interface ipfs_datasets_py/ipfs_datasets_py/wallet
cd wallet_interface/ui && npm run build
```

Also run `GET /ops/health?verify_storage=true` against the target environment
after deployment and confirm no check has `status=error`. When
`WALLET_PROOF_BACKEND=http-location-region`, also run:

```bash
python -m wallet_interface.ops --validate-proof-contract --fail-on-error
python -m wallet_interface.ops --validate-distance-proof-contract --fail-on-error
python -m wallet_interface.ops --validate-production-readiness
python -m wallet_interface.ops \
  --validate-target-signoff-packet /path/to/target-signoff.json
```
