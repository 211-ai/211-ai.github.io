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
WALLET_OPS_HEALTH_SECRET_REF=secret-manager://wallet/prod/ops-health
WALLET_OPS_ALERT_SECRET_REF=secret-manager://wallet/prod/ops-alert
WALLET_PROOF_CREDENTIAL_SECRET_REF=secret-manager://wallet/prod/proof-verifier
WALLET_STORAGE_CREDENTIAL_SECRET_REF=secret-manager://wallet/prod/storage
WALLET_STORAGE_IPFS_PINNING_POLICY_REF=policy://wallet/prod/ipfs-pinset
WALLET_STORAGE_FILECOIN_DEAL_POLICY_REF=policy://wallet/prod/filecoin-deals
WALLET_STORAGE_S3_LIFECYCLE_POLICY_REF=policy://wallet/prod/s3-lifecycle
WALLET_BACKUP_PURGE_POLICY_REF=policy://wallet/prod/backup-purge
WALLET_ALERT_RETENTION_POLICY_REF=policy://wallet/prod/alert-retention
WALLET_API_CORS_ORIGINS=https://wallet-ui.example.com
```

Optional production settings:

- `WALLET_STORAGE_ROOT`, `WALLET_STORAGE_BUCKET`, `WALLET_STORAGE_PREFIX`,
  `WALLET_STORAGE_PIN`, and `WALLET_STORAGE_MIRRORS` can build
  `WALLET_STORAGE_CONFIG` from individual environment variables.
- `WALLET_SERVICES_JSONL` points the ASGI API at a JSONL service directory.
  Each row should match the public service record fields used by
  `/wallets/{wallet_id}/services/match`: `id`, `name`, `description`,
  `categories`, `city`, `state`, `zip`, `phone`, `website`, and `source_url`.
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
- `WALLET_API_CORS_ORIGINS` is a comma-separated allow-list for browser clients.
  Leave it unset behind same-origin gateways; set it explicitly for split
  API/UI origins.
- The `*_SECRET_REF` variables are not secrets. They are secret-manager paths
  included in readiness and signoff evidence so operators can prove real
  verifier, storage, ops-health, and alert credentials are provisioned without
  printing credential values.
- The storage and alert `*_POLICY_REF` variables are not secrets. Use them to
  connect the deployed encrypted replica topology to IPFS pinning, Filecoin
  deal expiration, S3 lifecycle, backup purge, and alert-retention evidence.
  The target mapping template is
  `wallet_interface/deploy/storage-retention.example.json`.

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
Use `python -m wallet_interface.ops --validate-target-signoff-packet` against a
completed `docs/WALLET_TARGET_PRODUCTION_SIGNOFF_PACKET.template.json` copy to
validate retention, organization review, and staging evidence before launch.

The wallet UCAN invocation profile and UCAN-compatible inspection envelope are
documented in `docs/WALLET_UCAN_PROFILE.md`.

## Verifier Cutover Packet

Operators must complete a WALLET-180 non-simulated verifier cutover packet
before exposing any user-facing proof creation path backed by the selected HTTP
verifier. The packet is the launch evidence for replacing simulated development
proofs with a target verifier. It belongs in the approved evidence system next
to the target signoff packet and should contain references only, never secret
or witness values.

Cutover sequence:

1. Confirm the target deployment is using `WALLET_PROOF_MODE=production`,
   `WALLET_ALLOW_SIMULATED_PROOFS=false`, and
   `WALLET_PROOF_BACKEND=http-location-region`.
2. Confirm the verifier credential is injected at runtime from
   `WALLET_PROOF_CREDENTIAL_SECRET_REF` or the provider equivalent. Do not
   archive process env dumps, bearer tokens, custom header values, Kubernetes
   Secret payloads, or ExternalSecret resolved values.
3. Run and archive the target-staging outputs for
   `python -m wallet_interface.ops --validate-proof-contract --fail-on-error`,
   `python -m wallet_interface.ops --validate-distance-proof-contract --fail-on-error`,
   and `python -m wallet_interface.ops --validate-production-readiness`.
4. For both `location_region` and `location_distance`, verify the archived JSON
   shows `health`, `prove`, `public_input_safety`, and `verify` checks with
   `status=ok`, an expected `verifier_id` and `proof_system`,
   `is_simulated=false`, and no witness or credential values.
5. Run a failure-mode drill in target staging. Use an invalid credential,
   unhealthy verifier, rejected prove response, out-of-policy distance response,
   or `verify=false` response and archive that validation fails closed with no
   stored proof receipt and no witness or secret values in output or logs.
6. Run a rollback drill. Archive the previous deployment reference, credential
   rollback or revocation step, API/UI/ops worker rollback command, named
   operator, expected rollback time, and post-rollback proof behavior. Keep
   production proof mode enabled so simulated receipts remain rejected.
7. Record the cutover packet artifact ID in
   `docs/WALLET_TARGET_PRODUCTION_SIGNOFF.md` and in the completed target
   signoff JSON packet evidence repository record.

`location_distance` remains hidden from live Proof Center creation and display
until its distance contract report, failure-mode evidence, rollback evidence,
and security/privacy/ops/product approvals are archived. A `mode=local_self_check`
report is acceptable for repository automation only and must not be used as
target launch evidence.

## Analytics Governance Release Workflow

Production analytics is template-bound. Operators and integrators must not run
ad hoc SQL, notebook filters, GraphRAG prompts, export jobs, or other arbitrary
raw queries over wallet records, contribution payloads, precise locations,
plaintext documents, or direct identifiers. The production API surface releases
aggregates only through approved template IDs via `/analytics/{template_id}/count`
and `/analytics/{template_id}/count-by-fields`.

Before setting an analytics template to `approved` or allowing it to remain live
in a target environment:

1. Register or reconcile the template definition with the wallet service. The
   template must name its purpose, allowed record types, allowed derived fields,
   allowed aggregation dimensions, minimum cohort size, and epsilon budget.
2. Archive user-facing consent copy that describes the template purpose, data
   categories, derived fields, aggregation behavior, retention summary,
   withdrawal behavior, and support path.
3. Record public proof statements for `analytics_contribution`, including the
   approved public inputs and verifier or proof mode. Public inputs must not
   contain raw payloads, precise coordinates, plaintext document fields, or
   direct identifiers.
4. Record the nullifier policy: scope, duplicate-rejection rule, retention
   period, withdrawal handling, and assurance that nullifiers are not exported
   as wallet identifiers.
5. Record the k-threshold and privacy budget: `min_cohort_size`, `k_threshold`,
   epsilon budget, per-query epsilon, sensitivity, budget key, budget limit,
   budget-exhaustion behavior, and reviewer rationale.
6. Map template definition, consent copy, consents and withdrawals,
   contributions, nullifiers, query-budget ledger, released aggregates, and
   audit events to `docs/WALLET_RETENTION_POLICY.md` in the target signoff
   packet.
7. Record reviewer names or accountable reviewer roles, decision date, evidence
   ID, withdrawal behavior, and any tracked exceptions in
   `analytics_privacy_review.approved_templates[]`.

Run the release gate after any template addition, field expansion, proof
statement change, consent copy change, lower k-threshold, higher epsilon,
retention change, reviewer exception, or transition from `paused`/`retired` back
to `approved`:

```bash
python -m wallet_interface.ops \
  --validate-target-signoff-packet /path/to/target-signoff.json \
  --fail-on-error
python scripts/run_wallet_release_checks.py --dry-run
```

If no production analytics templates are live, set
`analytics_privacy_review.no_live_analytics_templates=true` in the completed
packet and keep `/analytics/templates` free of approved production templates for
that environment.

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

For deployed ASGI instances, set `WALLET_SERVICES_JSONL` to load the service
directory used by the matching endpoints. The matching API accepts wallet
location records only through owner access, scoped coarse-location grants, or
signed coarse-location invocation tokens; it rejects precise caller-provided
coordinates on `/services/match-derived`.

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

## 211 Service Partner Pilot Reference

WALLET-210 pilot staging uses the browser UI for user-visible document upload,
recipient access review, proof-center review, analytics choice review, and audit
review. Location capture, partner grants, service matching, analytics
contribution, and revocation use the public wallet API endpoints above. All
wallet records, grants, proofs, analytics ledgers, and audit events remain
backed by `ipfs_datasets_py.wallet`; the UI must not create local-only pilot
state for these checks.

Minimum pilot setup:

- Start the API with durable staging `WALLET_REPOSITORY_ROOT`,
  `WALLET_STORAGE_CONFIG`, `WALLET_AUTO_LOAD_REPOSITORY=true`,
  `WALLET_AUTO_PERSIST=true`, and `WALLET_SERVICES_JSONL` pointing at the 211
  service directory for the pilot region.
- Use development proof mode only for synthetic local rehearsals. Target
  staging that represents launch readiness must have the WALLET-180 verifier
  cutover packet archived before exposing live proof creation.
- Use an approved analytics template from the WALLET-200 governance packet.
  The template fields for the pilot must be coarse or derived fields such as
  `county` and `need_category`, not direct identifiers, plaintext document
  fields, precise coordinates, or free-form raw query fields.

Pilot demonstration sequence:

1. Open `/#/uploads` with `walletApiBaseUrl`, `walletId`, `actorDid`, and
   `issuerKeyHex` query parameters. Upload a synthetic intake document and
   confirm `GET /wallets/{wallet_id}/records?data_type=document` lists the new
   encrypted document record.
2. Add a synthetic location with `POST /wallets/{wallet_id}/locations`. Treat
   this as private witness data; do not show or archive the precise coordinates
   after creation.
3. Create a purpose-bound partner grant with
   `POST /wallets/{wallet_id}/records/{record_id}/grants`, using
   `abilities=["record/analyze"]`, an explicit partner audience DID,
   `purpose`, and output types such as `redacted_derived_only`. The recipient
   UI at `/#/recipient-access` must show an active shared receipt for the
   partner.
4. Issue and verify a partner invocation, run redacted analysis, and confirm the
   response excludes person-name strings, email addresses, phone numbers, SSNs,
   plaintext document text, and unapproved output types.
5. Create a coarse-location grant and invocation, then call
   `POST /wallets/{wallet_id}/services/match` for the partner navigator. The
   service-match response may contain coarse city/state/zip reasons and service
   IDs, but must not contain exact latitude or longitude values.
6. Open `/#/proof-center`, create a `location_region` proof for the location
   record, and confirm the visible public inputs include the region claim and
   policy hash without `lat`, `lon`, target coordinates, or witness values.
7. Create consent from the approved analytics template and submit one
   contribution through
   `POST /wallets/{wallet_id}/analytics/contributions` using only approved
   derived/coarse fields. If the pilot releases an aggregate, use the approved
   `/analytics/{template_id}/count` or `/count-by-fields` endpoint with the
   configured k-threshold and privacy budget.
8. Revoke partner grants with
   `POST /wallets/{wallet_id}/grants/{grant_id}/revoke`. Re-run a previously
   valid invocation and confirm it fails. The recipient-access UI must show the
   receipt as revoked.
9. Open `/#/audit` and confirm the timeline includes `record/add`,
   `grant/create`, `invocation/issue`, `invocation/verify`,
   `record/analyze_redacted`, `location/read_coarse`, `proof/create`,
   `analytics/consent_create`, `analytics/contribute`, optional
   `analytics/query`, and `grant/revoke`.

Repository validation for this sequence is:

```bash
pytest tests/test_wallet_interface_api.py tests/test_wallet_third_party_blackbox.py -q
npm --prefix wallet_interface/ui run build
npm --prefix wallet_interface/ui test -- tests/fullstack-wallet.spec.ts
```

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
| `wallet_create_record_grant` | Create a bounded record grant. |
| `wallet_issue_record_invocation` | Issue a signed record invocation token. |
| `wallet_decrypt_document` | Decrypt a document with owner, grant, or invocation access. |
| `wallet_grant_receipts` | List grant receipts. |
| `wallet_revoke_grant` | Revoke a grant and dependent access. |
| `wallet_create_export_grant` | Create a bounded encrypted export grant. |
| `wallet_issue_export_invocation` | Issue a signed export invocation token. |
| `wallet_create_export_bundle` | Create an encrypted export bundle. |
| `wallet_verify_export_bundle` | Verify export bundle hash/schema. |
| `wallet_import_export_bundle` | Import encrypted descriptors from a verified bundle. |
| `wallet_export_bundle_storage` | Verify encrypted blob availability for a bundle. |
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
python scripts/run_wallet_release_checks.py --dry-run
python scripts/run_wallet_release_checks.py --playwright-port 5185
```

The runner executes the documented backend pytest slice, wallet compile check,
UI build, and live full-stack Playwright checks. Expanded manual form:

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
cd wallet_interface/ui && npm run build
PLAYWRIGHT_PORT=5185 npm run test:fullstack
```

The runner executes the backend wallet pytest targets, compileall, UI build,
and live full-stack Playwright checks in order. Non-dry runs write a
manifest/results evidence bundle under `artifacts/wallet-release-checks/` by
default; archive that bundle with the target signoff packet.

The blackbox suite runs the wallet API through `uvicorn` and covers production
readiness, target signoff packet validation, external verifier no-witness-leak
checks, UCAN delegate decrypt/export grants, signed invocations, encrypted
export hash/schema verification/import/storage checks, grant revocation,
analytics, ops health, repository reload after restart, and matching wallet CLI
subprocess flows for sharing, export, analytics, import merge, and revocation.
`tests/test_wallet_third_party_blackbox.py` is the focused third-party sharing
harness. It runs only through public API endpoints, seeds service matching via
`WALLET_SERVICES_JSONL`, and exercises scoped UCAN grants for document-derived
analysis, coarse-location matching, proof-only location claims, encrypted
export bundles, and revocation blocking.
`ipfs_datasets_py/tests/mcp/test_wallet_tools.py` covers the same
share/export/import/revoke path and redacted analysis/form/extraction/vector/
GraphRAG path plus analytics template/consent/contribution/private-count
workflows through MCP wallet tools, dynamic manager discovery, and manager
dispatch.
`wallet_interface/ui/tests/smoke.spec.ts` covers the browser export center for
API-backed export grant, invocation, bundle creation, hash/schema verification,
storage status, and descriptor import, and covers recipient delegated document
analysis for safe summaries, redacted analysis, extraction, form analysis,
vector profiles, and GraphRAG.
`wallet_interface/ui/tests/fullstack-wallet.spec.ts` starts a real wallet API
with local repository/blob storage, seeds wallet records through HTTP, and
drives the 211-AI export center and recipient delegated analysis workflows
against that live API from desktop and mobile browser projects.

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

If no target `WALLET_*` readiness variables are configured,
`python -m wallet_interface.ops --validate-production-readiness` runs a local
synthetic verifier self-check so CI can exercise the release-gate code path.
Any configured target readiness variables switch the command back to strict
target validation. Running `--validate-target-signoff-packet` without a path
validates the committed packet template shape; a human launch decision requires
the completed packet path form shown above.
