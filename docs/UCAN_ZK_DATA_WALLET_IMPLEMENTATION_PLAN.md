# UCAN and ZK User Data Wallet Implementation Plan

Last updated: 2026-05-02

## Goal

Build a user-controlled data wallet that lets people share personal data with
third parties through UCAN capability delegations while keeping raw data private.
The wallet must support documents, location information, profile attributes,
service needs, derived facts, and future data types. It must also support
privacy-preserving aggregate analysis so 211-AI can understand user needs and
service gaps without exposing individuals.

The durable core belongs in `ipfs_datasets_py`. The `211-AI` repository should
provide the UI/UX, product workflows, and service-matching experience around
that core.

This plan extends `docs/DOCUMENT_WALLET_IMPLEMENTATION_PLAN.md` from a document
vault into a broader personal data wallet and analytics system.

## Design Principles

- User control is the root authority. A wallet owner or delegated device issues
  every meaningful access grant.
- UCAN controls authorization, not confidentiality. A valid UCAN decides whether
  an actor may perform an operation; encryption and key wrapping decide whether
  that actor can see plaintext.
- Hidden CIDs, filenames, S3 ACLs, or unguessable URLs are not privacy controls.
- Location is high-risk data. Store precise location encrypted, share coarse or
  derived claims by default, and use proof-based claims where possible.
- ZK proofs prove statements about data; they do not automatically make
  aggregate analytics non-identifying. Bulk analytics also need cohort
  thresholds, query budgets, differential privacy, and audit controls.
- The UI should ask users about people, organizations, purposes, expiration, and
  outputs. Protocol details belong in advanced views.

## Current Code Reuse Map

Use these existing `ipfs_datasets_py` pieces instead of rebuilding them in
`211-AI`:

- IPFS storage: `ipfs_datasets_py/ipfs_datasets_py/ipfs_backend_router.py`
  already exposes a pluggable IPFS backend with Kubo CLI and optional provider
  hooks.
- General storage concepts: `ipfs_datasets_py/ipfs_datasets_py/storage/storage_engine.py`
  has storage enums and manager concepts, but needs real wallet storage adapters.
- UCAN foundations:
  - `ipfs_datasets_py/ipfs_datasets_py/processors/auth/ucan.py` is a mock UCAN
    manager and key delegation demo.
  - `ipfs_datasets_py/ipfs_datasets_py/mcp_server/ucan_delegation.py` has a
    stronger capability/delegation-chain model with expiry, revocation, stores,
    and evaluator hooks.
  - `ipfs_datasets_py/ipfs_datasets_py/logic/integration/ucan_policy_bridge.py`
    can help translate higher-level policy into UCAN-like checks.
- ZK foundations:
  - `ipfs_datasets_py/ipfs_datasets_py/logic/zkp/` provides prover/verifier
    abstractions, canonicalization, witness management, simulated and Groth16
    backends, and a UCAN/ZKP bridge.
  - `ipfs_datasets_py/ipfs_datasets_py/logic/zkp/ucan_zkp_bridge.py` already
    models ZK proof evidence as a UCAN caveat, but it is simulation-oriented by
    default and must be made production-safe for wallet use.
  - `ipfs_datasets_py/ipfs_datasets_py/mcp_server/tools/pdf_tools/pdf_generate_zkp_certificate.py`
    demonstrates form-completion proofs without exposing private form values.
- Documents and analysis:
  - PDF, OCR, form, GraphRAG, vector, and knowledge-graph processors exist under
    `ipfs_datasets_py/ipfs_datasets_py/processors/`, `embeddings/`,
    `vector_stores/`, and `knowledge_graphs/`.
- Location and spatial analysis:
  - `ipfs_datasets_py/ipfs_datasets_py/processors/domains/geospatial/geospatial_analysis.py`
    provides reusable geospatial extraction/query logic, but it is currently
    lightweight and should be wrapped by wallet-aware privacy controls.
- Audit/provenance:
  - `ipfs_datasets_py/ipfs_datasets_py/audit/` and
    `ipfs_datasets_py/ipfs_datasets_py/analytics/data_provenance*.py` provide
    audit/provenance concepts that can be reused for wallet event logs, consent
    receipts, and aggregate-analysis lineage.
- 211-AI interface:
  - Existing scraper and daemon outputs provide service-directory data.
  - The top-level `wallet_interface/` directory is the natural place for
    app/API/UI orchestration.

## Standards and External Assumptions

- UCAN uses DIDs, commands/capabilities, policies, proof chains, expiry, and
  validation at invocation time. See `https://ucan.xyz/delegation/`.
- IPFS CIDs identify content by content-derived addresses but do not say where
  the content is stored or guarantee persistence. See
  `https://docs.ipfs.tech/concepts/content-addressing/`.
- Privacy-enhancing computation is broader than ZK. NIST lists ZK, MPC, PSI,
  PIR, FHE, structured encryption, and threshold schemes as relevant tools. See
  `https://csrc.nist.gov/Projects/pec/pec-tools`.

## Target Architecture

```text
211-AI
  wallet_interface/
    api.py                # FastAPI app-facing API
    ui/                   # wallet UX, sharing flows, analytics consent
    service_matching.py   # 211-aware workflows using wallet-derived facts

ipfs_datasets_py
  ipfs_datasets_py/wallet/
    models.py             # wallet, data records, grants, proofs, cohorts
    crypto.py             # envelope encryption and key wrapping
    identity.py           # DID/device/passkey identity abstraction
    manifest.py           # deterministic wallet/data manifests
    storage.py            # local/IPFS/S3/Filecoin encrypted storage adapters
    ucan.py               # wallet capability vocabulary and verifier wrapper
    proofs.py             # proof requests, verifier registry, proof receipts
    location.py           # precise/coarse/derived location claim handling
    analytics.py          # consented aggregate contribution pipeline
    privacy.py            # k-anonymity, DP budgets, redaction policies
    audit.py              # hash-chained consent/access/analysis logs
    service.py            # stable Python service API
    exceptions.py
```

`211-AI` should never implement its own cryptography, proof verification, or
UCAN chain semantics. It should call `ipfs_datasets_py.wallet` APIs.

## Data Model

Generalize from documents to typed data records.

```text
Wallet
  wallet_id
  owner_did
  controller_dids
  device_dids
  recovery_policy
  default_privacy_policy
  manifest_head

DataRecord
  record_id
  wallet_id
  data_type              # document, location, profile, need, benefit, form, note
  sensitivity            # low, moderate, high, restricted
  public_descriptor      # opaque, non-identifying
  encrypted_metadata_ref
  current_version_id
  status

DataVersion
  version_id
  record_id
  encrypted_payload_refs
  encrypted_metadata_ref
  plaintext_commitment   # optional, salted; avoid global hashes for common docs
  ciphertext_hash
  key_wrap_refs
  derived_artifact_refs
  proof_receipt_refs

DerivedArtifact
  artifact_id
  record_ids
  artifact_type          # summary, facts, embedding, eligibility, coarse_location
  output_policy          # plaintext, redacted, aggregate_only, proof_only
  encrypted_payload_ref
  public_commitment

ProofReceipt
  proof_id
  proof_type             # range, membership, form_validity, location_region, aggregate
  statement
  verifier_id
  public_inputs
  proof_ref
  witness_record_refs
  issued_at
  expires_at

AnalyticsConsent
  consent_id
  wallet_id
  study_or_query_id
  allowed_record_types
  allowed_derived_fields
  aggregation_policy
  expires_at
  revoked_at
```

## UCAN Capability Model

Define wallet resources as URI-like strings:

```text
wallet://{wallet_id}
wallet://{wallet_id}/records/{record_id}
wallet://{wallet_id}/records/{record_id}/versions/{version_id}
wallet://{wallet_id}/derived/{artifact_id}
wallet://{wallet_id}/proofs/{proof_id}
wallet://{wallet_id}/analytics/{consent_id}
wallet://{wallet_id}/location/{record_id}
```

Abilities:

```text
wallet/read
wallet/admin
record/add
record/read
record/decrypt
record/analyze
record/share
record/delete
metadata/read
metadata/write
derived/read
derived/create
location/read_precise
location/read_coarse
location/prove_region
location/prove_distance
proof/create
proof/verify
analytics/contribute
analytics/query
analytics/read_result
key/rewrap
grant/create
grant/revoke
audit/read
export/create
```

Common caveats:

- Expiration and not-before.
- Allowed record IDs and data types.
- Allowed output types: plaintext, redacted fields, summary, eligibility facts,
  geohash prefix, census tract, proof only, aggregate only.
- Purpose: service matching, emergency support, case work, legal help, research,
  operations analytics, user export.
- Maximum delegation depth.
- Multi-sig approval reference for high-impact grants.
- User presence requirement for precise location, plaintext export, and
  full-wallet grants.
- Minimum cohort size and privacy budget for analytics.
- Revocation reference.

## Location Privacy Plan

Represent location as first-class wallet data, not metadata attached casually to
other records.

Data forms:

- Precise point: encrypted latitude/longitude, timestamp, source, accuracy.
- Address: encrypted normalized address and geocoding receipt.
- Coarse location: derived geohash prefix, ZIP, county, service region, or
  census tract where appropriate.
- Movement history: high-risk; disabled by default and requires separate consent.
- Need-location link: a record that says a service need applies to a location
  without exposing that location to all services.

Default sharing behavior:

- Share coarse service area for search and matching.
- Use `location/prove_region` to prove "user is in this service area" without
  revealing exact coordinates.
- Use `location/prove_distance` to prove "user is within N miles of provider"
  when exact address is not required.
- Require explicit user confirmation for `location/read_precise`.
- Round timestamps or remove them from shared derived artifacts unless needed.

Implementation:

- `wallet.location` owns location record schemas, geohash/coarsening,
  region membership, distance claims, and proof request generation.
- Existing geospatial tools can process public service-directory locations and
  wallet-derived coarse facts, but must not receive raw user coordinates unless
  authorized by UCAN and key wrapping.

## ZK and Privacy-Preserving Analytics Plan

### What ZK Should Prove

Initial proof families:

- Attribute range: income is below a threshold; age is above a threshold.
- Attribute membership: household is in an allowed ZIP/county/service region.
- Location relation: committed precise location is inside a public polygon or
  within a distance threshold.
- Document/form validity: a form or document-derived fact satisfies a rule set
  without exposing private fields.
- Aggregate contribution validity: an encrypted analytics contribution was
  computed from wallet records matching the user's consent and schema.
- Anti-duplication: a per-study nullifier proves one contribution per wallet
  without revealing wallet identity.

### What ZK Should Not Claim Alone

Do not describe bulk analytics as private just because each contribution has a
proof. A query like "count users with rare condition in tiny ZIP" can still
identify people. The analytics layer must enforce:

- Minimum cohort size before releasing results.
- Differential privacy noise for counts and rates.
- Query budget per analyst/study.
- Suppression of sparse cells and risky joins.
- Purpose-bound consent and audit logs.
- Manual review for new high-risk analytics templates.

### Analytics Flow

1. Analyst creates an analytics template, not an arbitrary raw query.
2. Template declares data types, derived fields, cohort dimensions, privacy
   parameters, and public proof statements.
3. Wallet UI presents a readable consent prompt.
4. Wallet produces an encrypted contribution from derived fields only.
5. Wallet generates a proof that the contribution follows the template and
   consent policy.
6. Wallet includes a per-template nullifier to prevent duplicate counting.
7. Aggregator verifies UCAN, consent, proof, schema, and nullifier.
8. Aggregator computes only approved statistics.
9. Privacy engine applies k-thresholds, DP noise, and suppression.
10. Result, proof receipts, query budget use, and release decision are audited.

### Implementation Modes

- MVP mode: local derived facts plus simulated ZK in development, clearly marked
  as non-production.
- Production mode: enable Groth16 only when the Rust backend, proving keys, and
  verifier registry are present. Fail closed if proof generation or verification
  is unavailable.
- Future mode: evaluate MPC/PSI/FHE for analytics where ZK proofs alone are a
  poor fit.

## Security Architecture

Use envelope encryption for every record version:

1. Generate a random data encryption key per record version.
2. Encrypt payload and private metadata with AEAD.
3. Store encrypted payloads through local/IPFS/S3/Filecoin adapters.
4. Store deterministic manifests as canonical JSON or DAG-CBOR.
5. Wrap data keys only for authorized devices, people, or services.
6. Record every grant, access, proof, contribution, result release, revocation,
   and key rotation in an append-only audit hash chain.

Revocation:

- UCAN revocation stops future invocations.
- Key rotation stops future access to rotated versions.
- Previously downloaded plaintext cannot be clawed back; the UI should say this
  plainly during revocation.

High-impact operations requiring threshold approval:

- Full-wallet export.
- Precise location sharing longer than a short window.
- Full-document plaintext sharing.
- Root authority rotation.
- Recovery policy changes.
- Long-lived service or analytics grants.

## `ipfs_datasets_py` Service API

Target Python API:

```python
from ipfs_datasets_py.wallet import WalletService

service = WalletService(...)

wallet = service.create_wallet(owner_did=owner_did)
location = service.add_location(wallet.wallet_id, lat=45.5152, lon=-122.6784)
document = service.add_document(wallet.wallet_id, path="benefits.pdf")

grant = service.create_grant(
    wallet_id=wallet.wallet_id,
    audience_did="did:key:case-worker",
    resources=[f"wallet://{wallet.wallet_id}/records/{document.record_id}"],
    abilities=["record/analyze", "derived/read"],
    caveats={"purpose": "benefits_application", "expires_at": "..."},
)

proof = service.create_proof(
    wallet_id=wallet.wallet_id,
    proof_type="location_region",
    witness_records=[location.record_id],
    public_statement={"region_id": "multnomah_county"},
)

contribution = service.create_analytics_contribution(
    wallet_id=wallet.wallet_id,
    consent_id=consent.consent_id,
    template_id="housing_needs_by_county_v1",
)
```

Core methods:

- `create_wallet`, `load_wallet`, `rotate_wallet_keys`
- `add_record`, `add_document`, `add_location`, `add_profile_attribute`
- `list_records`, `search_records`, `get_record_manifest`
- `create_derived_artifact`, `analyze_record`, `service_match`
- `create_grant`, `invoke_grant`, `revoke_grant`, `verify_access`
- `create_proof`, `verify_proof`, `list_proof_receipts`
- `create_analytics_consent`, `revoke_analytics_consent`
- `create_analytics_contribution`, `verify_analytics_contribution`
- `run_aggregate_query`, `release_aggregate_result`
- `export_wallet`, `get_audit_log`, `verify_wallet_integrity`

## 211-AI UI/UX Plan

Build the UI around real user workflows:

- Wallet home: documents, location cards, service needs, recent activity,
  storage/proof health.
- Add data: upload document, add address/location, import form, enter profile
  facts, scan and classify.
- Share with advocate: choose recipient, purpose, records, precise vs derived
  outputs, expiration, review, confirm.
- Service matching: use coarse location and derived eligibility facts to match
  211 services without exposing raw wallet data unnecessarily.
- Proof center: show human-readable claims like "in service area" or "income
  threshold met"; hide circuit/proof details unless expanded.
- Analytics consent: explain study purpose, fields used, privacy protections,
  expiration, and withdrawal.
- Delegate workspace: third parties see only records, derived outputs, and
  actions granted to them.
- Audit timeline: readable record of who asked, what was shared, what was
  proven, what analysis ran, and when access was revoked.
- Security/recovery: devices, recovery contacts, key rotation, emergency revoke,
  export.

UI rule: users choose purposes and outputs; the app translates those into UCAN
abilities and caveats using `ipfs_datasets_py`.

## Implementation Phases

### Phase 0: Architecture and Threat Model

Deliverables:

- Threat model covering documents, precise location, derived facts, analytics,
  third-party delegates, storage providers, and administrators.
- UCAN interop decision: keep internal wrapper around current delegation code,
  then add spec-compatible token encoding and interop tests.
- ZK production decision: confirm Groth16 backend build, artifact management,
  verifier registry, and fail-closed behavior.
- Analytics privacy policy: cohort thresholds, DP defaults, query budget model,
  and restricted query templates.

Acceptance:

- Written security ADR.
- Crypto round-trip test vectors.
- One UCAN delegation-chain test.
- One simulated proof test and one fail-closed production-proof test.

### Phase 1: Generic Data Wallet Core

Deliverables:

- `ipfs_datasets_py.wallet` package skeleton.
- Wallet, data record, version, derived artifact, proof receipt, grant, consent,
  and audit models.
- Deterministic manifest serializer.
- Local encrypted blob store.

Acceptance:

- Create wallet.
- Add document and location records.
- Encrypt/decrypt through authorized local device key.
- Unauthorized decrypt fails.
- Manifests serialize deterministically.

### Phase 2: Storage Integration

Deliverables:

- Storage adapter using `ipfs_backend_router`.
- Local encrypted cache.
- IPFS encrypted payload and manifest writes.
- Storage receipt model.
- Optional S3/Filecoin adapter interfaces.

Acceptance:

- Store encrypted document and location records.
- Retrieve by CID through fake backend and decrypt locally.
- Verify ciphertext hash and AEAD authentication.
- Tests do not require live IPFS by default.

### Phase 3: UCAN Wallet Authorization

Deliverables:

- Wallet-specific capability vocabulary.
- Wrapper around `mcp_server.ucan_delegation` with wallet caveat evaluation.
- Revocation store.
- Access guard for decrypt/analyze/prove/share/export.
- Key wrapping flow tied to grants.

Acceptance:

- `record/analyze` does not imply `record/decrypt`.
- `location/read_coarse` does not imply `location/read_precise`.
- Delegation attenuation prevents re-sharing broader authority.
- Expired and revoked grants fail.

### Phase 4: Location Claims and Service Matching

Deliverables:

- `wallet.location` schemas and coarsening utilities.
- Region membership and distance proof request models.
- 211 service matching using coarse location and derived eligibility facts.
- UI flow for precise vs coarse location sharing.

Acceptance:

- User can match services with coarse location.
- User can prove service-area membership without exposing exact coordinates in
  the result object.
- Precise location requires explicit capability and audit event.

### Phase 5: Proof System Integration

Deliverables:

- `wallet.proofs` proof registry and verifier registry.
- Integration with existing `logic/zkp` prover/verifier APIs.
- UCAN caveat support for proof receipts.
- Form/document proof adapters.

Acceptance:

- Generate a simulated proof in dev with explicit non-production marking.
- Production mode fails closed when Groth16 backend or artifacts are missing.
- Verify proof receipts before accepting derived claims.
- Proof public inputs contain no raw private witness values.

### Phase 6: Privacy-Preserving Analytics

Current MVP status:

- `ipfs_datasets_py.wallet` supports approved analytics templates, template
  status/expiry checks, consent constrained by template policy, per-template
  nullifiers, simulated proof receipts for contributions, duplicate prevention,
  k-threshold suppression, optional Laplace noisy count release, exact
  count/cohort suppression for private releases, and per-budget-key epsilon
  accounting. Aggregate query/release decisions are audited against consenting
  wallets without logging raw contribution fields.
- `ipfs-datasets wallet` exposes an MVP analytics CLI flow for registering
  templates, creating consent, submitting derived-field contributions, and
  running private aggregate counts across local wallet snapshots.
- `wallet_interface.api` exposes an initial FastAPI surface for wallet
  creation, analytics templates, consent, derived-field contributions, private
  aggregate counts, encrypted location creation, wallet-backed service matching
  from coarse location claims, coarse-location grant/invocation workflows for
  delegated service matching, location-region proof grant/proof workflows,
  encrypted text document creation, analysis grant/invocation workflows,
  encrypted storage health verification/repair, derived service matching, and
  proof receipt listing for proof-center views, and audit timelines.
- The current DP implementation is deterministic for local reproducible tests.
  Production deployments must replace this with reviewed randomness, durable
  analyst/study ledgers, and privacy review for each analytics template.

Deliverables:

- Analytics template model.
- Consent model and UI flow.
- Contribution generation with nullifiers.
- Proof-backed contribution verification.
- Aggregation privacy engine: k-thresholds, suppression, DP noise, query budget.
- Aggregate audit/provenance records.

Acceptance:

- User can opt into one analytics template.
- Aggregator verifies UCAN, consent, proof, schema, and nullifier.
- Duplicate contribution is rejected.
- Sparse cohort result is suppressed.
- Released aggregate result includes privacy metadata and audit trail.

### Phase 7: Document and Derived Data Analysis

Deliverables:

- Wallet-aware wrappers around PDF/OCR/form/GraphRAG/vector tools.
- Derived artifacts stored encrypted.
- Redaction and output policy enforcement.
- Cross-record analysis scoped to authorized record IDs.

Acceptance:

- Delegate can receive summary or eligibility facts without plaintext export.
- Embeddings and summaries are treated as sensitive unless policy says otherwise.
- Analysis emits audit events and provenance records.

### Phase 8: 211-AI Product UI

Deliverables:

- `wallet_interface/api` app layer.
- `wallet_interface/ui` wallet, share, proof, analytics, audit, and service-match
  screens.
- API client that calls `ipfs_datasets_py.wallet`.
- Demo workflow using existing 211 service data.

Acceptance:

- User adds a document and location.
- User matches services using derived/coarse data.
- User shares analysis-only access with a third party.
- User consents to one aggregate analytics template.
- User revokes grant and future access fails.

### Phase 9: API, MCP, CLI, and Operations

Deliverables:

- Stable Python API docs.
- MCP tools for wallet and analytics workflows.
- CLI commands under `ipfs-datasets wallet`.
- Background verifier for storage availability, proof registry health, and
  privacy-budget accounting.

Acceptance:

- CLI can create wallet, add data, share, prove, contribute, revoke, audit.
- MCP tools enforce the same access guard as Python API.
- Operational checks produce audit events and repair jobs.

## Test Plan

Required test groups:

- Envelope encryption and key wrapping.
- Deterministic manifests.
- Storage adapter contract tests.
- UCAN chain, caveat, attenuation, expiry, and revocation tests.
- Location coarsening and region/distance claim tests.
- Proof generation and verification tests, including fail-closed production mode.
- Analytics consent, nullifier, duplicate prevention, cohort suppression,
  differential privacy, and query-budget tests.
- Access-control matrix tests across documents, location, derived artifacts,
  proofs, analytics, and export.
- Audit hash-chain and provenance tests.
- End-to-end 211-AI workflow tests.

Representative access matrix:

| Grant | Precise Location | Coarse Location | Document Plaintext | Derived Facts | Proofs | Analytics |
| --- | --- | --- | --- | --- | --- | --- |
| `location/read_coarse` | no | yes | no | optional | no | no |
| `location/prove_region` | no | no | no | no | yes | no |
| `record/analyze` + `derived/read` | no | optional | no | yes | optional | no |
| `record/decrypt` | optional | optional | yes | yes | optional | no |
| `analytics/contribute` | no | aggregate only | no | aggregate only | yes | yes |
| `export/create` | yes | yes | yes | yes | yes | no |
| `wallet/admin` | policy-dependent | policy-dependent | policy-dependent | policy-dependent | policy-dependent | policy-dependent |

## First Vertical Slice

Build this before expanding:

1. Create a wallet.
2. Add one PDF and one location record.
3. Encrypt both locally.
4. Store encrypted payloads through local and fake IPFS adapters.
5. Create deterministic manifests.
6. Grant a delegate `record/analyze` and `location/prove_region`, but not
   plaintext decrypt or precise location read.
7. Produce a derived eligibility summary from the PDF.
8. Produce a service-area membership proof from location.
9. Run 211 service matching from coarse/proven data.
10. Revoke the grant and verify later access fails.
11. Show this in a minimal 211-AI UI or CLI demo with audit events.

This proves the key boundaries: encryption, UCAN, location privacy, derived-only
sharing, proof receipts, service matching, revocation, and audit.

## Open Decisions

- The public wallet package is `ipfs_datasets_py.wallet`. The older
  package-level `data_wallet` and `document_wallet` names, plus
  `ipfs_datasets_py.wallet.document`, were removed after migration.
- Whether first production UCAN encoding should interoperate directly with
  JavaScript `ucanto`/w3up or begin with a Python-internal verifier and add
  interop tests later.
- Which location proof backend to use for polygons and distance proofs beyond
  simple range/membership circuits.
- Differential privacy defaults for small regional cohorts.
- Whether analytics aggregation should run in a trusted service first, or use
  MPC/TEE/FHE for specific high-risk studies later.
- Whether passkeys should be the primary UX for device keys from milestone one.

## Risks and Mitigations

- Metadata leakage: encrypt filenames, addresses, tags, extracted entities, and
  sensitive summaries.
- Location re-identification: default to coarse location, suppress sparse
  analytics, and require explicit grants for precise data.
- Overbroad sharing: use purpose presets, short expirations, and capability
  previews.
- ZK overclaiming: label simulated proofs clearly and fail closed in production.
- Analytics doxxing: enforce k-thresholds, DP, query budgets, and review for new
  templates.
- Lost keys: implement recovery before production use with critical records.
- Revocation misunderstanding: distinguish future access denial from already
  downloaded data.
- Storage unavailability: replicate encrypted payloads and verify receipts.
- UCAN library mismatch: hide implementation behind `wallet.ucan` and keep
  interop tests.
