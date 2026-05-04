# 211-AI Wallet Interface

This package is the 211-AI application layer for the wallet work. It should stay
thin: encryption, UCAN-style grant evaluation, key wrapping, proof receipts,
analytics consent, and audit logging live in `ipfs_datasets_py.wallet`.

## Current Scope

- Load 211 service records from processed JSONL.
- Match services from wallet-derived need terms and coarse location claims.
- Create wallet/location records through `WalletService`.
- Let delegated actors match services only when the wallet core authorizes the
  coarse location claim.
- Register analytics templates, create consent from approved templates, submit
  derived/coarse analytics facts, and request privacy-preserving aggregate
  counts through `ipfs_datasets_py.wallet`.
- Create UCAN-scoped encrypted export grants, issue signed export invocation
  tokens, and build bounded export bundles without plaintext document contents
  or precise coordinates. Export grants use the wallet threshold-approval path
  when governance marks `export/create` as sensitive. Export bundles include a
  deterministic `bundle_hash` and `bundle_id` receipt for tamper checks.
- Expose an initial FastAPI surface through `wallet_interface.create_app()`.

## Development Import

During local development, this package uses the vendored checkout at
`ipfs_datasets_py/` if `ipfs_datasets_py` is not installed. Production should
install `ipfs_datasets_py` normally and should not depend on path mutation.

## Example

```python
from wallet_interface import WalletInterfaceService

app = WalletInterfaceService.from_services_jsonl("data/live/processed/services_agentic.jsonl")
wallet = app.create_wallet("did:key:owner")
location = app.add_location(wallet.wallet_id, actor_did="did:key:owner", lat=45.5152, lon=-122.6784)
document = app.add_document(wallet.wallet_id, "benefits.txt", actor_did="did:key:owner")

matches = app.match_services_for_wallet(
    wallet.wallet_id,
    location.record_id,
    actor_did="did:key:owner",
    need_terms=["housing", "rent"],
)
```

The matching layer intentionally accepts coarse/derived location claims, not raw
precise coordinates.

## Analytics Example

```python
app.create_analytics_template(
    template_id="housing_service_gap_v1",
    title="Housing service gaps",
    purpose="County-level housing planning",
    allowed_record_types=["location", "need"],
    allowed_derived_fields=["county", "need_category"],
    min_cohort_size=10,
    epsilon_budget=1.0,
    created_by="did:key:analyst",
)

consent = app.create_analytics_consent_from_template(
    wallet.wallet_id,
    actor_did="did:key:owner",
    template_id="housing_service_gap_v1",
)

app.contribute_analytics_facts(
    wallet.wallet_id,
    actor_did="did:key:owner",
    consent_id=consent.consent_id,
    template_id="housing_service_gap_v1",
    fields={"county": "Multnomah", "need_category": "housing"},
)

result = app.run_private_aggregate_count("housing_service_gap_v1", epsilon=0.25)
```

The interface rejects precise coordinate fields before contribution. The wallet
core enforces consented fields, nullifier duplicate prevention, k-thresholds,
differential privacy metadata, query-budget accounting, and aggregate query
audit events for consenting wallets. Use `summarize_aggregate_result()` before
returning results to UI/API clients.

The same MVP flow is available in the package CLI through:

- `ipfs-datasets wallet analytics-template`
- `ipfs-datasets wallet analytics-consent`
- `ipfs-datasets wallet analytics-contribute`
- `ipfs-datasets wallet analytics-count`
- `ipfs-datasets wallet export-grant`
- `ipfs-datasets wallet export-invocation`
- `ipfs-datasets wallet export-bundle`
- `ipfs-datasets wallet verify-export-bundle`
- `ipfs-datasets wallet import-export-bundle`
- `ipfs-datasets wallet export-bundle-storage`

## API Example

```python
from wallet_interface import create_app

api = create_app()
```

The API exposes wallet creation, analytics template registration, template-based
consent, derived-field contribution, private aggregate count, and derived
service matching endpoints. It also exposes encrypted location creation,
coarse-location grant/invocation workflows for delegated service matching,
location-region proof grant/proof workflows,
encrypted text document creation, analysis grant/invocation workflows,
encrypted export grant/invocation/bundle workflows, encrypted storage health
verification/repair, wallet-backed service matching from coarse location claims,
proof receipt listing for proof-center views, and wallet audit timelines. The
route handlers call `WalletInterfaceService` and return sanitized aggregate
summaries, derived artifacts, or encrypted export manifests for UI/API clients.
`POST /exports/verify` validates an export bundle receipt by recomputing its
canonical hash. `POST /exports/import` validates the same receipt and registers
the encrypted descriptors without granting plaintext access. Import also checks
the expected `wallet_export_v1` type and required bundle sections.
`POST /exports/storage` reports encrypted blob availability for records
referenced by a verified export bundle.

## Wallet Storage Configuration

`WalletInterfaceService` builds the core `ipfs_datasets_py.wallet` storage
adapter from `storage_config` or environment variables. The default is in-memory
encrypted blob storage for tests and demos.

Programmatic example:

```python
app = WalletInterfaceService(
    storage_config={
        "primary": {"type": "local", "root": "/var/lib/211-ai/wallet-blobs"},
        "mirrors": [{"type": "s3", "bucket": "encrypted-wallet-backup"}],
    }
)
```

Environment options:

- `WALLET_STORAGE_CONFIG`: JSON string or object config for the core wallet
  storage factory.
- `WALLET_STORAGE_TYPE`: `memory`, `local`, `ipfs`, `s3`, or `filecoin`.
- `WALLET_STORAGE_ROOT`: local filesystem root for `local`.
- `WALLET_STORAGE_BUCKET` and `WALLET_STORAGE_PREFIX`: S3 target settings.
- `WALLET_STORAGE_MIRRORS`: JSON list of mirror backend configs.
- `WALLET_REPOSITORY_ROOT`: local JSON snapshot directory for wallet metadata.
- `WALLET_AUTO_LOAD_REPOSITORY`: load all snapshots at service startup
  (default `true` when a repository root is configured).
- `WALLET_AUTO_PERSIST`: save a wallet snapshot after state-changing wallet
  operations (default `true` when a repository root is configured).

Encrypted blob storage and wallet metadata are separate. The repository
snapshot stores wallet manifests, grants, audit events, and encrypted blob
references; plaintext document bytes remain only in the configured encrypted
blob store.

Repository API endpoints:

- `GET /wallets/snapshots`
- `POST /wallets/snapshots/save-all`
- `POST /wallets/snapshots/load-all`
- `GET /wallets/{wallet_id}/snapshot`
- `POST /wallets/{wallet_id}/snapshot`
- `POST /wallets/{wallet_id}/snapshot/load`

## UI Export Wiring

The React UI keeps static demo export cards when no backend is configured. To
hydrate the Exports screen from a real wallet export bundle, set:

- `VITE_WALLET_API_BASE_URL` to the FastAPI base URL
- `VITE_DEMO_WALLET_ID` to the active wallet ID
- `VITE_DEMO_EXPORT_BUNDLE_JSON` to a JSON-encoded `wallet_export_v1` bundle
- `VITE_DEMO_EXPORT_AUDIENCE_NAME` optionally, for the card title

The UI calls `POST /exports/verify` and `POST /exports/storage` to show the
bundle hash and storage status. It does not call `POST /exports/import`
automatically because import mutates backend wallet state.

When the API environment is present, the Exports screen can also create a live
bundle from recipient DID and record IDs. That flow calls:

1. `POST /wallets/{wallet_id}/exports/grants`
2. `POST /wallets/{wallet_id}/exports/invocations`
3. `POST /wallets/{wallet_id}/exports`
4. `POST /exports/verify` and `POST /exports/storage`

Set `VITE_DEMO_ACTOR_DID` for the issuer/controller DID. Set
`VITE_DEMO_ISSUER_KEY_HEX` and `VITE_DEMO_AUDIENCE_KEY_HEX` when the backend
requires signed UCAN grants or invocations.
