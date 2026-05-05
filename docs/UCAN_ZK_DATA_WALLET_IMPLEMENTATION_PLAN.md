# UCAN and ZK User Data Wallet Implementation Plan

Last updated: 2026-05-05

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

## Current Implementation Status

The canonical wallet implementation now lives in `ipfs_datasets_py.wallet`.
The older package-level `data_wallet` and `document_wallet` modules were
removed after migration. `211-AI` should treat `wallet_interface/` as the app
and UI layer over that package.

Implemented foundations:

- Generic encrypted wallet records for documents, location data, derived
  artifacts, proof receipts, grants, invocations, threshold approvals, access
  requests, analytics consents, analytics contributions, and audit events.
- Local, IPFS, S3, Filecoin-style, and replicated encrypted blob-store
  adapters with record-level verification/repair hooks and wallet-level
  encrypted replica health summaries/repair.
- UCAN-style grants and invocations for decrypt, analyze, coarse-location,
  proof, service-match, and encrypted export flows.
- Common wallet UCAN caveat enforcement for not-before, record IDs, data
  types, output attenuation, user presence, purpose-bound invocations, and
  delegated caveat preservation. Decrypt, summary, redacted analysis, vector
  profile, and encrypted export operations assert concrete output types before
  using delegated grants, and API invocation routes carry user-presence, purpose,
  and output caveats into signed `wallet-ucan-v1` tokens.
- Threshold approval support for high-impact capabilities such as
  `export/create`, with API and UI hooks for multi-controller approval.
- Location records with precise encrypted coordinates, coarse claims, delegated
  service matching, and simulated location-region proof receipts.
- Encrypted document records and delegated analysis workflows.
- Analytics templates, user consent, contribution nullifiers, simulated proof
  receipts, k-threshold suppression, differential privacy metadata, query
  budget accounting, and aggregate audit events.
- Encrypted export grants, signed invocation tokens, deterministic export
  bundles, bundle hash verification, encrypted descriptor import, and storage
  availability checks.
- `wallet_interface.api` FastAPI endpoints for the above workflows.
- `wallet_interface/ui` screens for registration, uploads, sharing,
  recipient-access review, analytics consent, proof center, exports, security,
  shelter workflows, service matching, and audit. The recipient-access screen
  can invoke attenuated delegated grants from share-capable receipts, and the
  security screen can perform wallet-level encrypted storage checks/repairs and
  threshold-approved emergency revocation with wallet-wide grant revocation and
  key rotation.

Remaining target-production gates:

- Provision real external verifier credentials in the selected secret manager
  and expose only the corresponding secret-manager reference env vars
  (`WALLET_OPS_HEALTH_SECRET_REF`, `WALLET_OPS_ALERT_SECRET_REF`,
  `WALLET_PROOF_CREDENTIAL_SECRET_REF`, and
  `WALLET_STORAGE_CREDENTIAL_SECRET_REF`) to the readiness report.
- Run `python -m wallet_interface.ops --validate-production-readiness` in the
  target staging environment until the report is `status=ok`; this now includes
  external `location_region` and `location_distance` verifier contract checks.
- Complete and archive a target-environment signoff packet using
  `docs/WALLET_TARGET_PRODUCTION_SIGNOFF.md`, with retention mapping from
  `docs/WALLET_RETENTION_POLICY.md` and supporting evidence from
  `docs/WALLET_SECURITY_ARCHITECTURE_ADR.md`,
  `docs/WALLET_PRODUCTION_DECISIONS_ADR.md`,
  `docs/WALLET_UCAN_PROFILE.md`,
  `docs/WALLET_OPERATIONS_RUNBOOK.md`, and
  `docs/WALLET_OPERATOR_INTEGRATOR_REFERENCE.md`. Use
  `docs/WALLET_TARGET_PRODUCTION_SIGNOFF_PACKET.template.json` for the
  machine-readable packet and validate it with
  `python -m wallet_interface.ops --validate-target-signoff-packet`.

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
  has storage enums and manager concepts. The wallet package now supplies
  wallet-specific encrypted local, IPFS, S3, Filecoin-style, and replicated
  storage adapters over those concepts.
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
    models ZK proof evidence as a UCAN caveat. The wallet boundary now adds
    proof-mode configuration, non-simulated backend selection, verifier
    metadata, public-input safety checks, and production fail-closed behavior.
  - `ipfs_datasets_py/ipfs_datasets_py/mcp_server/tools/pdf_tools/pdf_generate_zkp_certificate.py`
    demonstrates form-completion proofs without exposing private form values.
- Documents and analysis:
  - PDF, OCR, form, GraphRAG, vector, and knowledge-graph processors exist under
    `ipfs_datasets_py/ipfs_datasets_py/processors/`, `embeddings/`,
    `vector_stores/`, and `knowledge_graphs/`.
- Location and spatial analysis:
  - `ipfs_datasets_py/ipfs_datasets_py/processors/domains/geospatial/geospatial_analysis.py`
    provides reusable geospatial extraction/query logic. Wallet service
    matching now wraps location use with coarse claims, proof receipts, UCAN
    caveats, and audit controls.
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
- Allowed output types: plaintext, summary, redacted derived output, vector
  profile, encrypted export bundle, eligibility facts, geohash prefix, census
  tract, proof only, aggregate only.
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

- Development mode: local derived facts plus simulated ZK in development,
  clearly marked as non-production.
- Production mode: enable only reviewed non-simulated verifier backends with
  configured verifier credentials and registry metadata. Fail closed if proof
  generation or verification is unavailable.
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

The phase list below is the implementation contract. Each phase has working
package/API/UI coverage in this repository. Remaining gates are target
environment, governance, or future-compatibility items rather than missing
in-repo functionality.

| Phase | Status | Remaining Gate |
| --- | --- | --- |
| 0. Architecture and threat model | implementation complete | target signoff packet security/privacy/legal approval |
| 1. Generic data wallet core | implementation complete | target retention-policy mapping and datastore lifecycle approval |
| 2. Storage integration | implementation complete | target storage credentials and deployment verification |
| 3. UCAN wallet authorization | implementation complete | `wallet-ucan-v1` profile and conformance fixtures documented; external byte-level `ucanto`/w3up adapter remains target-specific |
| 4. Location claims and service matching | implementation complete | `location_distance` contract implemented; target verifier staging validation before live UI exposure |
| 5. Proof system integration | implementation complete | real target verifier credentials and staging contract pass |
| 6. Privacy-preserving analytics | implementation complete | organization privacy review for each approved template |
| 7. Document and derived analysis | implementation complete | first production uses `wallet-local-redacted-graphrag-v1`; model-backed GraphRAG requires separate target privacy/model review |
| 8. 211-AI product UI | implementation complete | live auth/accessibility/usability approval in target signoff packet |
| 9. API, MCP, CLI, and operations | implementation complete | target-environment secret provisioning and production-readiness report |

### Phase 0: Architecture and Threat Model

Deliverables:

- Threat model covering documents, precise location, derived facts, analytics,
  third-party delegates, storage providers, and administrators.
- UCAN interop decision: keep the documented `wallet-ucan-v1` profile for first
  production, with conformance fixtures for external `ucanto`/w3up adapters.
- ZK production decision: confirm Groth16 backend build, artifact management,
  verifier registry, and fail-closed behavior.
- Analytics privacy policy: cohort thresholds, DP defaults, query budget model,
  and restricted query templates.

Acceptance:

- Written security ADR.
- Crypto round-trip test vectors.
- One UCAN delegation-chain test.
- One simulated proof test and one fail-closed production-proof test.

Current implementation evidence:

| Requirement | Evidence |
| --- | --- |
| Written security ADR | `docs/WALLET_SECURITY_ARCHITECTURE_ADR.md` records the wallet security boundary, threat model, proof-mode decision, analytics privacy review process, and production signoff gate. `docs/WALLET_PRODUCTION_DECISIONS_ADR.md` records the production choices for UCAN interop, proof backend sequencing, DP defaults, analytics execution, and passkey/device UX. `docs/WALLET_UCAN_PROFILE.md` documents the `wallet-ucan-v1` token and interop envelope. `docs/WALLET_RETENTION_POLICY.md` and `docs/WALLET_TARGET_PRODUCTION_SIGNOFF.md` define the target-environment retention and governance evidence required before live data. |
| Crypto round-trip test vectors | Wallet unit and API tests cover encrypted record ingest, authorized decrypt, unauthorized decrypt rejection, encrypted exports, storage verification, and key rotation/re-wrapping. |
| UCAN delegation-chain test | Wallet unit/API/UI tests cover delegated grants, caveat preservation, attenuation, user-presence invocations, revocation, and child delegation from share-capable receipts. |
| Simulated and fail-closed proof tests | Wallet/API/proof-backend tests cover simulated development receipts, production-mode rejection of simulated proofs, deterministic non-simulated backend success, HTTP verifier contract validation, and public-input no-leak checks. |
| Privacy review process | Analytics template status gates, consent withdrawal, sparse-cell suppression, DP budget accounting, and `docs/WALLET_SECURITY_ARCHITECTURE_ADR.md` define the template approval process. |

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
- Record ID, not-before, data-type, output, and user-presence caveats fail
  closed when a grant or delegated child exceeds the parent policy.
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

Current implementation status:

- `ipfs_datasets_py.wallet` supports approved analytics templates, template
  status/expiry checks, consent constrained by template policy, per-template
  nullifiers, simulated proof receipts for contributions, duplicate prevention,
  k-threshold suppression, optional Laplace noisy count release, exact
  count/cohort suppression for private releases, and per-budget-key epsilon
  accounting. Aggregate query/release decisions are audited against consenting
  wallets without logging raw contribution fields.
- `ipfs-datasets wallet` exposes an analytics CLI flow for registering
  templates, creating consent, submitting derived-field contributions, and
  running private aggregate counts across local wallet snapshots. It also
  exposes bounded encrypted export grant, invocation, and bundle commands for
  `export/create` capabilities. `export/create` is treated as a sensitive
  capability and participates in threshold approval before grant issuance when
  wallet governance requires multi-controller review. Export grants default to
  the `encrypted_export_bundle` output type, and export creation checks that
  caveat before building the bundle. Export bundles include a deterministic
  `bundle_hash` and `bundle_id` so recipients can detect tampering independent
  of JSON key order. Bundle receipt verification is exposed through both CLI and
  the 211-AI API, validates both the deterministic hash and required encrypted
  descriptor schema, and verified bundles can be imported as encrypted
  descriptors without granting plaintext access. Import validates the expected
  bundle type and required record/version sections after hash verification.
  Storage availability checks report whether referenced encrypted blobs are
  locally retrievable without decrypting them.
- `wallet_interface.api` exposes an initial FastAPI surface for wallet
  creation, analytics templates, consent, derived-field contributions, private
  aggregate counts, encrypted location creation, wallet-backed service matching
  from coarse location claims, coarse-location grant/invocation workflows for
  delegated service matching, location-region proof grant/proof workflows,
  encrypted text document creation, analysis grant/invocation workflows,
  encrypted export grant/invocation/bundle workflows, encrypted storage health
  verification/repair, derived service matching, proof receipt listing for
  proof-center views, and audit timelines.
- Differential privacy noise uses system randomness by default, with
  deterministic test seeding available only for local reproducible tests.
  Durable analyst/study ledgers and privacy review gates are implemented
  through the repository analytics ledger and template status workflow.

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

Current implementation status:

- `WalletService.analyze_document_with_redaction` now creates encrypted derived
  artifacts for document analysis with a `redacted_derived_only` output policy.
  The returned safe output masks common direct identifiers such as email
  addresses, phone numbers, SSNs, and street addresses, emits derived need
  categories, enforces matching output-type caveats on delegated grants, and
  audits `record/analyze_redacted`.
- `ipfs_datasets_py.mcp_server.tools.wallet_tools.wallet_analyze_document_redacted`
  exposes that flow through MCP using the same wallet snapshot/blob persistence
  path as the wallet CLI and other wallet MCP tools.
- `WalletService.extract_document_text_with_redaction` now wraps the existing
  `processors.multimedia.attachment_text_extractor` inside the wallet boundary
  for text/PDF/image/OCR-capable records. Decrypted bytes are written only to a
  short-lived service-local temporary file for extraction, returned text is
  redacted before leaving the service, the redacted result is stored as an
  encrypted `redacted_document_text_extraction` artifact, and delegated use must
  carry the `redacted_extracted_text` output type. `wallet_extract_document_text_redacted`
  exposes the same flow through MCP.
- `WalletService.analyze_document_form_with_redaction` now wraps the existing
  PDF form analyzer/classifier inside the wallet boundary when a PDF record is
  available, with a text-extraction fallback for minimal environments and
  non-PDF form-like documents. Returned output contains redacted field metadata,
  form statistics, field type counts, and dependency summaries, stores an
  encrypted `redacted_document_form_analysis` artifact, and delegated use must
  carry the `redacted_form_analysis` output type.
  `wallet_analyze_document_form_redacted` exposes the same flow through MCP.
- `WalletService.create_document_vector_profile` now creates encrypted
  redacted document vector-profile artifacts for privacy-preserving retrieval
  and analytics features. The returned profile contains only redaction counts,
  category-level feature counts, document stats, and hashes of redacted
  per-chunk feature signatures; arbitrary extracted tokens and plaintext stay
  inside the encrypted artifact boundary. `wallet_create_document_vector_profile`
  exposes the same flow through MCP.
- `WalletService.analyze_documents_with_redaction` now performs cross-record
  redacted analysis over an explicit authorized record set. It verifies
  `record/analyze` for each document before decrypting inside the wallet service
  boundary, returns aggregate-safe need categories/redaction counts/per-record
  derived facts without document text, stores an encrypted
  `redacted_cross_document_analysis` artifact, and audits
  `record/analyze_redacted_batch`. `wallet_analyze_documents_redacted` exposes
  the same flow through MCP.
- `WalletService.create_redacted_graphrag` now creates encrypted redacted
  GraphRAG artifacts from authorized document records. It reuses the legacy
  document-centric GraphRAG entity extractor inside the wallet boundary, then
  collapses extracted entities to entity-type counts and graph edges over
  record, need-category, redaction-type, and entity-type nodes without returning
  entity strings or document text. Delegated use must carry the
  `redacted_graphrag` output type. `wallet_create_redacted_graphrag` exposes the
  same flow through MCP.
- The selected first-production GraphRAG backend is
  `wallet-local-redacted-graphrag-v1`: wallet-local execution, no model-backed
  entity extraction, legacy compatibility extractor over redacted text, and
  entity-type-count-only output. Advanced model-backed GraphRAG remains blocked
  until a separate target privacy/model review approves the model, prompt/data
  handling policy, output contract, and retention mapping.
- `wallet_interface.api` exposes redacted text extraction, form analysis,
  document analysis, vector profile, cross-record redacted analysis, and
  redacted GraphRAG endpoints so the 211-AI project can call these package
  capabilities without reaching into `WalletService` internals. The recipient UI now surfaces
  redacted document analysis and vector-profile actions for active
  `record/analyze` receipts when output caveats allow them, and displays the
  encrypted artifact descriptor plus redacted safe output.
- Wallet and MCP tests assert that obvious sensitive fields are not present in
  the returned redacted text extraction, form analysis, redacted analysis,
  cross-record analysis, GraphRAG, or vector-profile output and that the
  encrypted derived artifact descriptor is persisted.

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
- Export center for creating UCAN-scoped encrypted bundles, verifying bundle
  hashes/storage, and importing encrypted descriptors when the full bundle is
  present.

Acceptance:

- User adds a document and location.
- User matches services using derived/coarse data.
- User shares analysis-only access with a third party.
- User consents to one aggregate analytics template.
- User revokes grant and future access fails.
- User creates an encrypted export bundle for selected record IDs and a
  recipient DID.
- Recipient-side UI imports only encrypted descriptors after bundle hash
  verification, without receiving plaintext.

### Phase 9: API, MCP, CLI, and Operations

Current implementation status:

- `wallet_interface.api` now exposes the integrated wallet, proof, analytics,
  export, storage-repair, recovery, and ops-health surface used by the 211-AI
  UI.
- `ipfs_datasets_py.wallet.cli` provides local wallet creation, record ingest,
  bounded sharing, proof generation, export, analytics, approval, and audit
  flows.
- `ipfs_datasets_py.mcp_server.tools.wallet_tools` now adds hierarchical MCP
  tools for wallet creation, encrypted document/location ingest, location-region
  proof creation, record listing, analytics template/consent/contribution
  workflows, and private aggregate counts.
- Deployment and operator support now include the bounded/watch-mode ops worker,
  authenticated webhook alerts, reference Docker/Compose/Kubernetes/Cloudflare
  assets, and the wallet operations runbook.

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

## Next Execution Milestones

### Milestone A: Production-Ready Sharing Semantics

Status: implementation-complete as of 2026-05-03. The implementation now has bounded
UCAN-style sharing flows, capability previews, revocation behavior, threshold
approval references, and snapshot-backed durable wallet state. Remaining
production hardening for external UCAN interoperability and production
datastore operations is tracked below in Milestone E and the production gaps
above.

Implemented scope:

- The first-production `wallet-ucan-v1` token profile and conformance fixtures
  are documented, and external byte-level `ucanto`/w3up compatibility remains a
  target-specific adapter track.
- Conformance tests cover delegation chains, caveat attenuation, expiry,
  revocation, and threshold approval references.
- Capability previews in `211-AI` show users exactly what the grant
  permits: records, outputs, purpose, expiration, re-delegation, and revocation
  limits.
- Wallet snapshots persist access requests, grants, revocations, approvals, and
  grant receipts in a durable store.

Exit criteria:

- A third-party recipient can request access, receive approval, invoke a bounded
  capability, and later fail after revocation.
- `record/analyze`, `record/decrypt`, `location/read_coarse`,
  `location/read_precise`, `location/prove_region`, `analytics/contribute`, and
  `export/create` have explicit tests proving separation.

Completion evidence:

| Requirement | Evidence |
| --- | --- |
| UCAN token profile | `wallet-ucan-v1` invocation tokens are issued and accepted by `wallet_interface.api`, with issuer, audience, grant ID, wallet resource, ability, caveats, and expiration carried in signed wallet invocations. `docs/WALLET_UCAN_PROFILE.md` documents the profile, CLI adapter-validation commands, and conformance fixture contract. Wallet tests cover issuer-preserving tokens, the UCAN-compatible inspection envelope, complete conformance fixture validation, CLI fixture round-trip validation, legacy no-issuer token compatibility, and issuer mismatch rejection. External byte-level `ucanto`/w3up compatibility remains a target-specific adapter track. |
| Delegated request, approval, invocation, and revocation | `tests/test_wallet_interface_api.py` covers third-party access requests, owner approval, bounded invocation, listed revoked requests, and later invocation failure after revocation. |
| Capability separation | `ipfs_datasets_py/tests/unit/test_data_wallet.py` covers `record/analyze` without decrypt, `record/decrypt` key wrapping, coarse/proven location grants, analytics consent/contribution controls, export grants, wrong-ability rejection, tampered invocation rejection, and revoked grant rejection. |
| Caveat enforcement | Wallet service tests cover record-ID constrained wildcard grants, not-before caveats, concrete output-type checks for document/export operations, delegated grants preserving parent record restrictions, and `location_distance` target/threshold caveat enforcement. API tests cover user-presence-required grants failing direct use and succeeding only through a signed invocation carrying `user_present`. |
| Threshold approval references | Wallet unit tests and API tests cover sensitive decrypt and `export/create` grants requiring configured controller thresholds before issuance. |
| Durable wallet state | Wallet snapshots persist access requests, grants, revocations, approvals, grant receipts, analytics state, proof receipts, exports, audit events, and encrypted record descriptors. The CLI repository persists snapshots for local operation; target production repository and storage configuration are covered by Milestone E and the readiness gate. |
| 211-AI capability previews | `wallet_interface/ui` now previews abilities, records/resources, outputs, purpose, expiration/status, approval readiness, revocation state, and non-granted sensitive capabilities across sharing rules, recipient access, grant receipts, analytics, proof center, benefits, uploads, and exports. |
| UI regression coverage | `wallet_interface/ui/tests/smoke.spec.ts` covers capability previews for analytics, benefits, sharing, proofs, exports, recipient access approval/revocation, upload repair, delegated analysis artifacts, and audit events. |

Milestone A is therefore closed for the integrated implementation. Do not reopen it for
production datastore, passkey recovery, real ZK circuits, or external UCAN
interop; those are tracked by Milestones B, D, and E.

### Milestone B: Real Proof Backend for One Claim Family

Status: complete for the integrated `location_region` proof interface as of
2026-05-03. `location_region` proofs route through a configurable wallet proof
backend, simulated receipts carry verifier metadata, and production-style
services fail closed when simulated proofs are disabled. The 211-AI API can run
with simulated proofs disabled through service configuration or
`WALLET_PROOF_MODE=production`, and the UI API client maps proof receipt
verification metadata. A deterministic non-simulated location-region backend is
available for integration testing through
`WALLET_PROOF_BACKEND=deterministic-location-region`. The 211-AI Proof Center
loads wallet proof receipts from the API when a wallet API config is present,
retains demo receipts as fallback, and can request new `location/prove_region`
receipts through the wallet API.

Completion note: the deterministic backend is intentionally not a cryptographic
ZK circuit. Milestone B is closed because the wallet/API/UI proof boundary,
receipt schema, fail-closed behavior, verifier metadata, public-input safety,
and non-simulated verifier path are implemented and tested. Replacing the
deterministic backend with a reviewed circuit/verifier artifact is now a backend
drop-in task, not a 211-AI product-flow blocker.

Implemented scope:

- `location_region` is the first production proof-family boundary because it
  maps directly to 211 service eligibility.
- Witness schema, public inputs, circuit artifact storage, verifier ID, and
  proof receipt format are defined.
- `wallet.proofs` is wired to the existing `logic/zkp` verifier registry with a
  production-mode fail-closed flag.
- Simulated receipts remain available only under a development flag and are
  labeled in the UI.

Exit criteria:

- A proof receipt can be generated and verified without exposing precise
  coordinates or private attributes.
- Production mode refuses to accept a simulated proof.
- Public proof inputs are safe to display in the Proof Center.

Implemented contract:

| Layer | Work |
| --- | --- |
| `ipfs_datasets_py.wallet.proofs` | Provides a proof backend interface with `prove_location_region(witness, public_inputs)`, `verify(receipt)`, `verifier_id`, and `mode` fields. The development helper remains `SimulatedProofBackend`. |
| Wallet service | Provides `proof_backend` and `allow_simulated_proofs` configuration. In development mode, simulated receipts remain available. In production mode, the service fails closed unless a non-simulated backend is configured and verification succeeds before the receipt is stored. |
| Proof receipt schema | Includes `proof_system`, `circuit_id`, `verifier_digest`, `proof_artifact_ref`, and `verification_status`, while keeping `statement`, `public_inputs`, `witness_record_ids`, `proof_hash`, and `is_simulated` for backward-compatible imports. |
| Location witness schema | Decrypts precise coordinates only inside the wallet service, constructs a witness containing lat/lon plus wallet-local nonce, and exposes only `region_id`, `claim`, `region_policy_hash`, and optional coarse service area metadata as public inputs. |
| Verifier registry | Provides a registry keyed by `proof_type` and `verifier_id`. The default registered backends are `location_region:simulated-wallet-zkp-v0.1` for development and explicitly configured non-simulated backends for production-like environments. |
| API | Uses request flags and environment configuration to make simulated proofs visible as development artifacts. API responses include `is_simulated`, `proof_system`, `verifier_id`, `verification_status`, and safe `public_inputs`. |
| 211-AI UI | Labels simulated receipts clearly, shows production verification status, and never shows private witness data. The Proof Center displays only public inputs, verifier ID, receipt hash, and which wallet record was used. |
| Tests | Cover simulated development success, production fail-closed without backend, production success with a fake non-simulated backend, verification failure rejection, receipt import compatibility, and API/UI display of safe public inputs only. |

Completion evidence:

| Requirement | Evidence |
| --- | --- |
| Backend abstraction | `ipfs_datasets_py.wallet.proofs` exposes `ProofBackend`, `ProofBackendRegistry`, `SimulatedProofBackend`, and `DeterministicLocationRegionProofBackend`. |
| Wallet fail-closed mode | `WalletService(..., allow_simulated_proofs=False)` rejects simulated receipts and stores no proof on failure. |
| Non-simulated verification path | The deterministic location-region backend produces non-simulated receipts with verifier digest, circuit ID, artifact ref, and verification status, and `WalletService` verifies receipts before storage. |
| Backward-compatible receipts | Wallet snapshot import accepts legacy proof receipts that do not yet contain the new verifier metadata fields. |
| API proof mode | `WalletInterfaceService` supports explicit proof backend injection and env selection with `WALLET_PROOF_MODE=production` plus `WALLET_PROOF_BACKEND=deterministic-location-region`. |
| 211-AI Proof Center | Proof Center loads API-backed proof receipts, labels simulated vs verified receipts, displays safe public inputs and verifier metadata, and can create `location/prove_region` receipts through the API. A regression guard keeps `location_distance` out of the visible Proof Center until `--validate-distance-proof-contract` passes in target staging. |
| Public-input safety | Wallet, API, and UI tests assert precise coordinates and witness keys are not present in displayed/public proof inputs. |

Non-goals for this milestone:

- Do not build every proof family yet.
- Do not expose raw coordinates, exact addresses, witness nonces, or decrypted
  document contents to 211-AI.
- Do not rely on deterministic fake proofs in production mode.
- Do not mix aggregate analytics privacy guarantees with ZK proof verification;
  analytics hardening remains Milestone C.

### Milestone C: Analytics Hardening

Status: complete for the integrated wallet/API/UI analytics-hardening path as of
2026-05-04. Analytics templates now support the review states
`draft`, `approved`, `paused`, and `retired`; only approved templates are
listed by default; and non-approved templates block consent creation,
contribution creation, and aggregate queries. Consent withdrawal now has a
regression test proving future contributions are blocked while already released
aggregate result and audit history are preserved. Differentially private count
noise now uses system randomness by default, while deterministic noise remains
available only through an explicit test seed. Multi-dimensional count queries
now suppress sparse cohort cells without exposing the suppressed field values.
Analytics templates, consents, contributions, released aggregates, and query
budget spend now persist through a repository-level analytics ledger instead of
only duplicated wallet snapshots. The 211-AI Analytics screen now loads
API-backed templates and consents, shows template status, fields used, consent
expiration, and supports consent creation and withdrawal.

Implemented scope:

- Analytics templates, consents, contributions, nullifiers, query-budget spend,
  and aggregate releases persist durably.
- Differential privacy count noise uses reviewed system randomness by default,
  with deterministic noise limited to explicit test seeds.
- Analytics template review states include draft, approved, paused, and retired.
- UI controls cover consent expiration, withdrawal, and fields used.
- Sparse-cell suppression tests cover multi-dimensional cohorts.

Exit criteria:

- Duplicate wallet contributions are rejected by nullifier.
- Sparse cohorts are suppressed.
- Released counts include privacy metadata, epsilon spend, cohort size, and
  audit references.
- Withdrawing consent prevents future contribution but preserves already
  released aggregate audit history.

Current implementation evidence:

| Requirement | Evidence |
| --- | --- |
| Template review states | `WalletService.create_analytics_template(..., status=...)` normalizes `draft`, `approved`, `paused`, and `retired`, while preserving `active` as a legacy alias for `approved`. |
| Template gates | Wallet and API tests cover draft templates being hidden from active listings and rejected for consent, and paused templates being rejected for new contributions and aggregate queries. |
| Consent withdrawal | Wallet tests cover revoked analytics consent blocking future contribution while preserving the stored aggregate release and `analytics/query` audit reference. |
| DP noise source | Aggregate DP count no longer derives noise from deterministic template/nullifier seed material; tests assert the wallet aggregate path calls unseeded system-random noise. |
| Multi-dimensional sparse suppression | `run_aggregate_count_by_fields` and `/analytics/{template_id}/count-by-fields` release only cells meeting the cohort threshold and record suppressed-cell counts without leaking suppressed labels. |
| Durable analytics ledger | `LocalWalletRepository` writes `analytics-ledger.json` with templates, consents, contributions, aggregate releases, and query-budget spend, and `WalletInterfaceService` auto-loads that ledger on startup. |
| 211-AI consent controls | The Analytics screen displays API-backed template status, fields used, consent expiration, active consent IDs, and calls wallet API endpoints to create or withdraw consent. |
| Nullifiers and sparse cohorts | Existing wallet tests reject duplicate nullifiers, suppress single-count sparse cohorts, and verify released counts include privacy budget and cohort metadata. |

### Milestone D: Wallet Recovery and Device Trust

Status: complete for the integrated wallet/API device trust and recovery path
as of 2026-05-04. The canonical `ipfs_datasets_py.wallet` service now supports
controller and device management, governance-threshold approvals for wallet
admin changes, active-record key rotation/re-wrapping, emergency revoke of
non-owner grants, and recovery-contact threshold approval for adding a
controller when wallet authority needs to be restored. The 211-AI API exposes
the recovery policy and recovery-controller flows alongside the existing
controller, device, approval, and emergency revoke routes, and the Security
screen can drive recovery-policy and controller-recovery actions.

Implemented scope:

- Wallet controller and device authority provide the abstraction for live
  passkey or device-key authentication.
- Key rotation and re-wrapping are implemented for active records.
- Recovery contacts and recovery policy support threshold approval for root
  authority changes.
- Emergency revoke covers all active non-owner grants.

Exit criteria:

- A user can add/remove a device without losing existing encrypted records.
- A compromised delegate can be revoked and cannot invoke new access.
- Recovery changes are audited and require the configured governance threshold.

Current implementation evidence:

| Requirement | Evidence |
| --- | --- |
| Controller/device trust | `WalletService.add_controller`, `remove_controller`, `add_device`, and `revoke_device` update wallet authority and audit `wallet/controller_*` and `wallet/device_*` events. |
| Threshold admin changes | `wallet/admin` operations use approval requests and threshold approvers before sensitive controller, device, recovery-policy, decrypt, export, or emergency operations proceed. |
| Key rotation/re-wrapping | `WalletService.rotate_record_key` creates a fresh encrypted version and re-wraps active authorized recipients while revoking old active wraps. |
| Emergency revoke | `WalletService.emergency_revoke` revokes active non-owner grants, delegated wraps, receipts, and access requests, and can rotate active record keys. |
| Recovery policy | `WalletService.set_recovery_policy` stores active recovery contacts and requires the configured wallet governance threshold. |
| Recovery authority change | `WalletService.recover_controller` accepts only recovery-contact approvals for `wallet/controller_recover`, adds the recovered controller, syncs governance approvers, and audits `wallet/controller_recover`. |
| 211-AI coverage | 211-AI exposes `POST /wallets/{wallet_id}/recovery-policy` and `POST /wallets/{wallet_id}/controllers/recover`. The Security screen includes recovery policy and controller recovery controls, and wallet/API/UI tests cover the integrated surface. |

### Milestone E: Deployment and Operations

Status: implementation-complete for the in-repo production-ops path as of
2026-05-05.
Production persistence is available through `LocalWalletRepository` and
environment-driven wallet storage/proof configuration. The API-level operations
health report checks repository persistence, encrypted storage availability,
proof mode, revocation propagation, and privacy-budget ledger readability, and
writes durable `ops/health` audit events for wallet operators. The 211-AI
Security screen can run the ops-health check and display per-check status. A
bounded/watch-mode ops worker, reference Docker/Compose deployment, and operator
runbook now cover the initial deployment and incident-response path. The ops
worker can emit authenticated webhook alerts, the deployment assets carry the
alert and proof-service env surface, the HTTP proof backend can probe a remote
verifier service, and the Security screen now surfaces verifier metadata and
live proof-backend health. The remaining work is target-environment
provisioning: loading real verifier credentials into the selected secret
manager and running the documented staging proof workflow.

Implemented scope:

- Production persistence is selected and configurable for wallet metadata,
  audit events, revocation state, privacy budgets, and encrypted blob
  references.
- Background ops checks cover storage availability, proof registry health,
  revocation propagation, and privacy-budget reconciliation.
- Deployment configuration covers `wallet_interface.api` and
  `wallet_interface/ui`.
- Operator runbooks cover lost keys, revoked grants, failed proof registry,
  storage outage, and privacy incident response.

Exit criteria:

- API restarts do not lose wallet state, grants, consents, budgets, or audit
  history.
- Storage and proof health checks produce actionable audit/ops events.
- A production environment can run without demo-only env vars.

Current implementation evidence:

| Requirement | Evidence |
| --- | --- |
| Durable state | `LocalWalletRepository` persists wallet snapshots plus the shared analytics ledger; `WalletInterfaceService` can auto-load and auto-persist through `WALLET_REPOSITORY_ROOT`. |
| Storage configuration | `WalletInterfaceService` reads `WALLET_STORAGE_CONFIG`, `WALLET_STORAGE_TYPE`, and mirror-specific env vars to build local/IPFS/S3/Filecoin-backed encrypted storage. |
| Proof configuration | `WALLET_PROOF_MODE`, `WALLET_PROOF_BACKEND`, and `WALLET_ALLOW_SIMULATED_PROOFS` control whether simulated proofs are allowed, and `http-location-region` now supports an external verifier service through `WALLET_PROOF_SERVICE_URL` plus verifier metadata/auth env vars. |
| Ops health endpoint | `GET /ops/health?verify_storage=true` reports repository, storage, proof registry, revocation propagation, and privacy-budget checks, can be protected with `WALLET_OPS_HEALTH_SHARED_SECRET`, and actively probes the external HTTP verifier when that backend is configured. |
| Actionable audit events | Ops health appends `ops/health` audit events to each loaded wallet with per-check statuses. |
| 211-AI ops UI | The Security screen runs `/ops/health`, shows overall status, per-check summaries, proof verifier metadata, live verifier health, and refreshes wallet audit events after the check. |
| Scheduled worker | `python -m wallet_interface.ops` runs bounded or watch-mode ops checks, emits JSONL, can fail on warnings or errors for cron/sidecar integration, and can POST warning/error alerts to an operator webhook with bearer or custom-header authentication. |
| Deployment config | `wallet_interface/deploy/docker-compose.wallet.yml` runs API, UI, and ops worker services with durable volumes and production-mode proof settings, `wallet_interface/deploy/kubernetes/` provides the parallel namespace/config/API/UI/ops/ingress reference manifests, and `wallet_interface/deploy/cloudflare/` adds edge proxy plus scheduled ops-health Worker glue. |
| Cloudflare origin hardening | `wallet_interface/deploy/cloudflare/src/index.ts` limits the Worker to `GET`/`HEAD` health routes, forwards the wallet ops secret, and supports Cloudflare Access service-token headers plus custom origin-auth headers for environment-specific gateways. |
| Secret and alert wiring | `wallet_interface/deploy/env.production.example`, `wallet_interface/deploy/kubernetes/secrets.example.yaml`, and `wallet_interface/deploy/kubernetes/externalsecret.example.yaml` define the production secret/env surface for ops-health auth, alert webhooks, proof-service credentials, storage config, and Cloudflare origin auth. |
| Operator runbook | `docs/WALLET_OPERATIONS_RUNBOOK.md` covers lost keys, revoked grants, proof backend failure, storage outage, privacy incidents, and scheduled worker setup. |
| Operator/integrator reference | `docs/WALLET_OPERATOR_INTEGRATOR_REFERENCE.md` publishes the stable wallet API endpoint groups, CLI command list, MCP wallet tools, runtime env surface, privacy boundaries, and release checks. |
| External verifier contract | `docs/WALLET_PROOF_VERIFIER_CONTRACT.md` defines the HTTP `location_region` and `location_distance` proof verifier health/prove/verify contracts, authentication headers, safe receipt fields, ops validation, and no-witness-leak requirements. `python -m wallet_interface.ops --validate-proof-contract --fail-on-error` and `python -m wallet_interface.ops --validate-distance-proof-contract --fail-on-error` run staging health/prove/verify/no-leak checks against the configured HTTP verifier with synthetic witnesses. |
| Blackbox staging harness | `tests/test_wallet_production_handoff_blackbox.py` starts a local HTTP verifier stub, runs the production-readiness CLI through a subprocess with production-mode env vars, launches the wallet API with `uvicorn`, drives public wallet/document/location/proof/redaction/analytics/ops HTTP endpoints, exercises delegate UCAN decrypt/export grants, signed invocations, encrypted export hash/schema verification/import/storage checks, grant revocation, post-restart grant receipt/audit persistence, runs matching wallet CLI subprocess flows for sharing, export, analytics, import merge, and revocation, validates a completed signoff packet, confirms redacted analysis does not leak email, phone, SSN, precise coordinates, or person-name strings, and proves that a verifier leaking witness data fails the release gate. MCP wallet tests cover the same share/export/import/revoke path through tool wrappers and dynamic manager discovery. |

Target-environment handoff:

- Provision real external verifier service credentials in the target secret
  manager and run the verifier contract command in the target staging
  environment.
- Complete `docs/WALLET_TARGET_PRODUCTION_SIGNOFF.md` for the target
  environment, including the `docs/WALLET_RETENTION_POLICY.md` mapping to
  repository lifecycle, encrypted storage lifecycle, backup purge, IPFS pinning,
  Filecoin deal expiration, log retention, and alert retention controls.
- The in-repo gate for that handoff is
  `python -m wallet_interface.ops --validate-production-readiness`, which fails
  until durable repository/storage env vars, production proof mode, verifier
  credentials, secret-manager references, ops-health auth, alert routing, ops
  health, and the external region and distance verifier health/prove/verify
  contracts all pass without placeholder secrets.
- The governance gate is a completed JSON packet copied from
  `docs/WALLET_TARGET_PRODUCTION_SIGNOFF_PACKET.template.json` and validated by
  `python -m wallet_interface.ops --validate-target-signoff-packet`. It records
  retention mapping, staging artifacts, analytics privacy review, organization
  reviewer decisions, launch timing, and post-launch audit timing without
  storing secret values.

## Resolved Decisions

| Decision | Resolution |
| --- | --- |
| Public wallet package | `ipfs_datasets_py.wallet` is canonical. The older package-level `data_wallet` and `document_wallet` names, plus `ipfs_datasets_py.wallet.document`, were removed after migration. |
| First production UCAN encoding | Use signed `wallet-ucan-v1` invocation tokens for first production; `docs/WALLET_UCAN_PROFILE.md` defines the profile, UCAN-compatible inspection envelope, and conformance fixtures for external adapters. |
| Next proof backend | Keep `location_region` as the first production verifier boundary. `location_distance` now uses the same wallet proof receipt path and HTTP verifier contract pattern; run target verifier validation before live UI exposure. Add polygon proofs only after reviewed circuit/verifier artifacts are available. |
| DP defaults for small regional cohorts | Keep default `min_cohort_size=10` and `epsilon_budget=1.0`; require explicit privacy review for lower thresholds, higher epsilon, new dimensions, joins, or rare-condition cohorts. |
| Analytics execution model | Run first production analytics in the trusted wallet analytics service with template approval, nullifiers, k-thresholds, sparse-cell suppression, DP metadata, budget ledgers, and audit; evaluate MPC/TEE/FHE only for high-risk studies that need it. |
| GraphRAG backend | Use `wallet-local-redacted-graphrag-v1` for first production. It runs inside the wallet service, disables model-backed extraction, stores encrypted artifacts, and returns only record/category/redaction/entity-type graph metadata. |
| Passkey/device UX | Use passkeys as the preferred human authentication UX over wallet device keys when live auth is selected. Device DIDs, controllers, and recovery contacts remain the wallet authority model. |

The binding rationale for these decisions is in
`docs/WALLET_PRODUCTION_DECISIONS_ADR.md`.

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
