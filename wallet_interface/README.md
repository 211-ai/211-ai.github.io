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
encrypted storage health verification/repair, wallet-backed service matching
from coarse location claims, proof receipt listing for proof-center views, and
wallet audit timelines. The route handlers call `WalletInterfaceService` and
return sanitized aggregate summaries or derived artifacts for UI/API clients.
