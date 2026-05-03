# Document Wallet Implementation Plan

Last updated: 2026-05-02

> Superseded namespace note: new wallet implementation work should use
> `ipfs_datasets_py.wallet`. The older package-level `data_wallet` and
> `document_wallet` namespaces, plus `ipfs_datasets_py.wallet.document`, were
> removed after migration.

## Goal

Build a document wallet for users to keep important personal documents and derived structured information under user-controlled access. The core implementation should live in `ipfs_datasets_py`; this repository should provide the product workflow and UI/UX shell around that package.

The wallet must support:

- Client-side encryption before content leaves the user's trusted environment.
- Storage replication to IPFS, Filecoin, and optionally S3-compatible object storage.
- Multi-sig or threshold-governed administration for sensitive operations.
- UCAN-style delegated authorization for people, services, and agents that need to view or analyze specific documents.
- Auditable document analysis flows that minimize raw document exposure.

## Current Repo Fit

This workspace already contains useful foundations:

- `ipfs_datasets_py/ipfs_datasets_py/ipfs_backend_router.py` provides a pluggable IPFS backend with Kubo CLI, `ipfs_kit_py`, and other provider hooks.
- `ipfs_datasets_py/ipfs_datasets_py/storage/storage_engine.py` defines storage concepts but is currently mock-oriented for this use case.
- `ipfs_datasets_py/ipfs_datasets_py/processors/auth/ucan.py` contains a mock UCAN manager focused on key delegation.
- `ipfs_datasets_py/ipfs_datasets_py/mcp_server/ucan_delegation.py` contains capability/delegation chain evaluation, revocation, and delegation-store concepts.
- `ipfs_datasets_py/ipfs_datasets_py/logic/integration/ucan_policy_bridge.py` bridges natural-language policy to UCAN-like delegation evaluation.
- `ipfs_datasets_py/ipfs_datasets_py/mcp_server/tools/pdf_tools/` and related GraphRAG/vector/knowledge-graph modules already provide document analysis primitives.
- Top-level `wallet_interface/` is the 211-AI UI/app orchestration layer around the canonical wallet package.

## External Technical Assumptions

These assumptions should be treated as design constraints, not marketing claims:

- IPFS uses content addressing through CIDs. A CID identifies content by cryptographic hash, but does not guarantee persistence by itself. Persistence requires pinning, provider retention, or another storage commitment. See [IPFS content addressing](https://docs.ipfs.tech/concepts/content-addressing/).
- Filecoin storage/retrieval is provider-backed. Retrieval depends on provider discovery and supported retrieval protocols; public Filecoin data can be found through IPNI when advertised. See [Filecoin deals](https://docs.filecoin.io/storage-providers/filecoin-deals) and [Filecoin retrieval](https://docs.filecoin.io/basics/how-retrieval-works/serving-retrievals).
- UCAN is a capability delegation system. It authorizes who can do what, with attenuated delegation chains and revocation, but it does not automatically decrypt private data. See [UCAN specification](https://ucan.xyz/specification/), [UCAN delegation](https://ucan.xyz/delegation/), and [UCAN revocation](https://ucan.xyz/revocation/).
- Web3.Storage/w3up is a practical UCAN-based storage reference. Its delegation model is relevant even if we do not bind the first version to that service. See [w3up UCAN docs](https://docs-beta.web3.storage/concepts/ucan/) and [w3up delegation docs](https://docs-beta.web3.storage/concepts/ucan/delegation/).
- S3 encrypts new objects at rest by default with SSE-S3, but wallet privacy should still rely on client-side encryption because S3 server-side encryption does not prevent the storage service or account operators from seeing plaintext if uploads are not pre-encrypted. See [Amazon S3 server-side encryption](https://docs.aws.amazon.com/AmazonS3/latest/userguide/UsingServerSideEncryption.html).

## Product Model

The wallet is a user's private document vault plus a delegated analysis surface.

Primary users:

- A person seeking services who needs a durable place for identity, benefits, medical, legal, housing, financial, employment, immigration, and eligibility documents.
- A trusted advocate, case worker, lawyer, clinician, family member, or AI agent who needs narrowly scoped access to help that user.
- An organization that may host UI, indexing, analysis, or backup infrastructure without becoming the ultimate authority over the user's data.

Core promise:

- The user owns the root wallet authority.
- Stored documents are encrypted before upload.
- Storage providers see encrypted blobs and public metadata only.
- Delegates get only the capabilities, documents, fields, time window, and analysis mode they were granted.
- Every grant, view, export, analysis, revocation, and key rotation is auditable.

## High-Level Architecture

### Layer 1: `ipfs_datasets_py` Core

Add a new package:

```text
ipfs_datasets_py/ipfs_datasets_py/wallet/
  __init__.py
  models.py
  crypto.py
  identity.py
  manifest.py
  storage.py
  ucan.py
  multisig.py
  analysis.py
  audit.py
  service.py
  exceptions.py
```

Responsibilities:

- Define wallet, document, manifest, grant, access request, and audit models.
- Encrypt/decrypt documents and metadata.
- Store encrypted payloads and manifests through IPFS/Filecoin/S3 adapters.
- Generate and verify UCAN delegations and invocations.
- Enforce access policies before decrypting, exporting, indexing, or analyzing content.
- Wrap existing PDF, file conversion, vector, GraphRAG, and knowledge-graph tools behind wallet-aware authorization checks.
- Expose a stable Python API and MCP tools.

Current UCAN-style core status:

- `Grant` represents delegated capabilities with resources, abilities, caveats, expiry, and revocation status.
- `WalletInvocation` represents a signed local invocation of one grant capability.
- `DataWalletService.issue_invocation` creates signed invocations using the actor's wallet secret.
- `DataWalletService.verify_invocation` checks audience, resource, ability, grant status, expiry, and invocation signature.
- Invocation-backed helpers exist for record analysis, record decrypt, and coarse location claims.

### Layer 2: App/API Service

Add app/API work inside `wallet_interface/` or a later app package:

```text
wallet_interface/
  api/
  ui/
  README.md
```

Responsibilities:

- User onboarding, wallet creation, and recovery UX.
- Document upload and categorization.
- Sharing workflows.
- Delegate acceptance and analysis request flows.
- Human-readable audit timeline.
- Integrations with 211-AI service matching and advocacy workflows.

This layer should call `ipfs_datasets_py.wallet` APIs. It should not implement its own encryption, UCAN verification, storage writes, or policy evaluation.

### Layer 3: Storage and Network Providers

Storage adapters should be pluggable:

- IPFS: add encrypted payloads and manifests through `ipfs_backend_router`.
- Filecoin: submit CAR files or provider deals through a backend abstraction.
- S3: store encrypted payloads and manifest mirrors in a configured bucket.
- Local dev: filesystem-backed encrypted blob store for tests and offline mode.

Current core status:

- `LocalEncryptedBlobStore` supports in-memory and filesystem encrypted blobs.
- `IPFSEncryptedBlobStore` stores encrypted bytes through an IPFS backend.
- `S3EncryptedBlobStore` stores encrypted bytes through a boto3-compatible client.
- `FilecoinEncryptedBlobStore` stores encrypted bytes through a small Filecoin-capable backend contract.
- `ReplicatedEncryptedBlobStore` writes to a primary store plus mirrors and records mirror refs in wallet manifests.
- `DataWalletService.verify_record_storage` reports encrypted primary/mirror integrity without decrypting payloads.
- `DataWalletService.repair_record_storage` restores missing or tampered encrypted replicas from any valid encrypted source and emits audit events.

## Security Architecture

### Principle

Authorization and encryption are separate controls:

- UCAN answers: "Is this principal allowed to perform this action on this resource now?"
- Encryption answers: "Can this principal actually obtain plaintext?"
- Storage answers: "Where are the encrypted bytes and manifests replicated?"

Never rely on storage-layer ACLs or hidden CIDs as the privacy boundary.

### Data Encryption

Use envelope encryption:

1. Generate a random document encryption key per document version.
2. Encrypt file bytes with an AEAD cipher such as AES-256-GCM or XChaCha20-Poly1305.
3. Derive authenticated additional data from wallet ID, document ID, version ID, content CID, and manifest CID.
4. Store encrypted bytes on IPFS/Filecoin/S3.
5. Store encrypted or redacted metadata separately from public routing metadata.
6. Wrap the document key for each authorized principal or service using their public encryption key.

Recommended key hierarchy:

- Wallet root signing key: controls wallet authority and can issue administrative delegations.
- Device signing keys: issue daily-use invocations under root delegation.
- Device encryption keys: unwrap document keys locally.
- Recovery keys or shares: used only for recovery and rotation.
- Service keys: used for delegated analysis services, tightly scoped and time-bounded.

### Metadata Privacy

Avoid leaking sensitive details through filenames, tags, or manifest fields.

Public manifest fields should be limited to:

- Wallet manifest version.
- Document ID or opaque resource ID.
- Encrypted payload CID or object locator.
- Encrypted metadata CID or object locator.
- Byte size, content type family if necessary, and creation/update timestamps rounded if privacy-sensitive.
- Encryption suite and key-wrap references.
- Integrity hashes.

Private metadata should be encrypted:

- Original filename.
- Document title.
- Category.
- Issuer.
- Person names.
- Dates of birth.
- Benefit IDs.
- Address.
- Extracted entities.
- Embeddings and summaries when sensitive.

### Key Delegation

A UCAN grant should not directly contain raw document keys. It should authorize one of these flows:

- Recipient public-key wrapping: owner or authorized service wraps a document key to the recipient.
- Analysis-only service grant: service decrypts in a controlled environment and returns derived output permitted by the grant.
- Field-level derived grant: service returns only redacted fields, summaries, eligibility facts, or embeddings.
- Re-encryption grant: authorized service rotates or rewraps keys without exposing content to unrelated parties.

### Multi-Sig Governance

Use multi-sig for high-impact administration, not for every document view.

Recommended version 1:

- Represent the wallet owner authority as a DID controlled by one or more signing keys.
- Support threshold approval for these operations:
  - Add or remove recovery keys.
  - Rotate wallet root authority.
  - Grant full-wallet access.
  - Export all documents.
  - Delete or tombstone wallet manifests.
  - Add long-lived service access.
- Integrate with Safe smart accounts for EVM users where appropriate, but keep the wallet core chain-agnostic.

Implementation options:

- Off-chain threshold signatures for DID-controlled wallet roots.
- Safe smart account signature verification for administrative grants.
- Shamir secret sharing for recovery of a wallet master secret, if we introduce one.
- Passkeys/device keys for practical user login, delegated from the wallet root.

The simplest robust first version is: multi-sig governs UCAN issuance and root key rotation; document keys are still wrapped per recipient/device.

### Revocation

Revocation has two layers:

- Authorization revocation: append a UCAN revocation record and reject future invocations.
- Cryptographic revocation: rotate or re-encrypt document keys when prior recipients must lose future access.

Revocation cannot make already-downloaded plaintext disappear. The UI must make this clear without undermining the normal workflow.

## Capability Model

Define wallet-specific UCAN resources and abilities.

Resource URI examples:

```text
wallet://{wallet_id}
wallet://{wallet_id}/documents
wallet://{wallet_id}/documents/{document_id}
wallet://{wallet_id}/documents/{document_id}/versions/{version_id}
wallet://{wallet_id}/derived/{document_id}/summary
wallet://{wallet_id}/derived/{document_id}/eligibility_facts
wallet://{wallet_id}/grants/{grant_id}
```

Abilities:

```text
wallet/read
wallet/admin
document/add
document/read
document/decrypt
document/analyze
document/share
document/delete
metadata/read
metadata/write
derived/read
key/rewrap
grant/create
grant/revoke
audit/read
export/create
```

Standard caveats:

- Expiration and not-before.
- Maximum delegation depth.
- Allowed document IDs.
- Allowed document categories.
- Allowed output types: plaintext, redacted_text, summary, fields, embeddings, eligibility_facts.
- Purpose: service_matching, legal_help, benefits_application, medical_casework, user_export.
- Delegate must present DID proof.
- User presence required.
- Multi-sig approval reference.
- Rate limit.
- Geographical or organizational scope, if needed.

## Core Data Models

### Wallet

Fields:

- `wallet_id`
- `owner_did`
- `controller_dids`
- `recovery_policy`
- `storage_policy`
- `default_access_policy`
- `manifest_head`
- `created_at`
- `updated_at`

### Document

Fields:

- `document_id`
- `wallet_id`
- `current_version_id`
- `encrypted_metadata_ref`
- `public_descriptor`
- `created_at`
- `updated_at`
- `status`

### Document Version

Fields:

- `version_id`
- `document_id`
- `encrypted_payload_refs`
- `encrypted_metadata_ref`
- `content_hash_plaintext`
- `content_hash_ciphertext`
- `encryption_suite`
- `key_wrap_refs`
- `analysis_refs`
- `created_at`

Plaintext hash should be optional and privacy-reviewed. It helps deduplication and integrity, but it can leak whether a common document is present.

### Key Wrap

Fields:

- `wrap_id`
- `document_id`
- `version_id`
- `recipient_did`
- `recipient_key_id`
- `wrapped_dek`
- `wrap_algorithm`
- `grant_cid`
- `created_at`
- `expires_at`
- `status`

### Grant

Fields:

- `grant_id`
- `ucan_cid`
- `issuer_did`
- `audience_did`
- `resources`
- `abilities`
- `caveats`
- `proof_chain`
- `revocation_ref`
- `created_at`
- `expires_at`
- `status`

### Audit Event

Fields:

- `event_id`
- `wallet_id`
- `actor_did`
- `action`
- `resource`
- `decision`
- `grant_id`
- `request_id`
- `hash_prev`
- `created_at`
- `details_encrypted_ref`

Use an append-only hash chain for wallet audit logs. Store detailed audit payloads encrypted, with a minimal public event index.

## API Surface in `ipfs_datasets_py`

Primary Python API:

```python
from ipfs_datasets_py.wallet import WalletService

service = WalletService(...)

wallet = service.create_wallet(owner_did=owner_did, recovery_policy=policy)
record = service.add_record(
    wallet.wallet_id,
    data_type="document",
    plaintext=document_bytes,
    actor_did=owner_did,
    actor_secret=owner_key,
    private_metadata={"filename": "id.pdf", ...},
)
grant = service.create_grant(
    wallet_id=wallet.wallet_id,
    audience_did=case_worker_did,
    resources=[f"wallet://{wallet.wallet_id}/records/{record.record_id}"],
    abilities=["record/analyze", "derived/read"],
    caveats={"expires_at": "...", "output_types": ["summary", "eligibility_facts"]},
)
result = service.analyze_record_summary(
    wallet_id=wallet.wallet_id,
    record_id=record.record_id,
    invocation=ucan_invocation,
    analysis_type="eligibility_facts",
)
```

Service methods:

- `create_wallet`
- `load_wallet`
- `rotate_wallet_keys`
- `add_document`
- `update_document`
- `get_document_manifest`
- `decrypt_document`
- `create_grant`
- `accept_grant`
- `invoke_grant`
- `revoke_grant`
- `rewrap_document_key`
- `rotate_document_key`
- `analyze_document`
- `list_documents`
- `search_documents`
- `export_wallet`
- `verify_wallet_integrity`
- `get_audit_log`

MCP tools:

- `wallet_create`
- `wallet_add_record`
- `wallet_list_records`
- `wallet_create_grant`
- `wallet_revoke_grant`
- `wallet_analyze_record`
- `wallet_verify_access`
- `wallet_export`
- `wallet_audit_log`

CLI:

```bash
ipfs-datasets wallet create
ipfs-datasets wallet add ./file.pdf --category benefits
ipfs-datasets wallet share --record-id <id> --audience-did did:key:... --can record/analyze --issue-invocation
ipfs-datasets wallet issue-invocation --record-id <id> --grant-id <id> --ability record/analyze
ipfs-datasets wallet analyze-invocation --record-id <id> --invocation-token <token>
ipfs-datasets wallet verify-storage --record-id <id>
ipfs-datasets wallet repair-storage --record-id <id> --actor-did did:key:...
ipfs-datasets wallet revoke --grant <id>
ipfs-datasets wallet audit
```

## Storage Design

### Manifest Strategy

Use content-addressed manifests:

- Each document version has an immutable manifest.
- The wallet has a mutable head pointer to the latest wallet manifest.
- The latest head can be stored in:
  - Local profile state.
  - IPNS or DNSLink where appropriate.
  - S3 object key for app-managed users.
  - A Filecoin/IPFS pinned "latest pointer" object.

Manifests should be canonical JSON or DAG-CBOR with deterministic serialization.

### Payload Strategy

For each document version:

1. Encrypt plaintext to ciphertext.
2. Add ciphertext to IPFS and pin.
3. Optionally pack as CAR for Filecoin.
4. Optionally mirror ciphertext to S3.
5. Write storage receipts into the document manifest.

Storage receipts:

- IPFS CID and pin status.
- Filecoin deal ID/provider/status where available.
- S3 bucket/key/version/ETag where available.
- Created time and last verified time.

### Availability Policy

Default replication:

- Local encrypted cache: enabled.
- IPFS pin: enabled.
- S3 mirror: optional.
- Filecoin archival: optional for production or high-value records.

Add a background verifier:

- Checks CID retrievability.
- Checks S3 object existence.
- Checks Filecoin deal status where supported.
- Emits audit events and repair jobs.

## Analysis Design

Document analysis must always run behind access checks.

Analysis modes:

- `local_only`: decrypt and analyze on user's device.
- `trusted_service`: decrypt in a controlled service authorized by UCAN.
- `derived_only`: recipient never receives plaintext; they receive specific outputs.
- `zero_knowledge_or_attested`: future mode for proofs or enclave-backed analysis.

Outputs:

- Extracted text.
- OCR text.
- Document type classification.
- Key fields.
- Eligibility facts.
- Redacted summary.
- Embeddings.
- Knowledge graph entities/relationships.
- Cross-document consistency checks.

Access policy examples:

- A case worker can view a Medicaid approval letter until a specific date.
- An AI advocate can analyze documents for housing eligibility but cannot export plaintext.
- A lawyer can view legal documents and derived timelines, but not medical records.
- A family member can upload documents but cannot read existing documents.

## UI/UX Plan in This Project

The UI should be workflow-first, not protocol-first.

Core screens:

- Wallet home: document list, status, recent activity, storage health.
- Add document: upload, scan, classify, metadata, encryption/storage progress.
- Document detail: preview when allowed, versions, metadata, derived facts, grants, audit trail.
- Share/access: recipient, purpose, documents, allowed actions, expiration, review, confirm.
- Access requests: inbound requests from advocates/services with approve/deny/edit.
- Delegate view: documents and outputs shared with the current actor.
- Analysis workspace: ask questions, generate forms/checklists, produce service eligibility packets.
- Recovery/security: devices, signers, recovery contacts, key rotation, emergency revoke.
- Audit: timeline filtered by actor, document, action, grant, decision.

UX principles:

- Users should choose people and purposes, not raw capabilities.
- The UI should translate purposes into a capability preview before confirmation.
- Show expiration and revocation clearly.
- Make "view document" distinct from "analyze document" and "export document".
- Explain recovery setup before users rely on the wallet for critical records.
- Avoid exposing CIDs, DIDs, UCANs, and Filecoin details unless the user opens advanced details.

## Implementation Phases

### Phase 0: Architecture Spike

Deliverables:

- Confirm target UCAN implementation library for Python and/or define interop with `ucanto`/w3up where Python support is weak.
- Decide manifest encoding: canonical JSON first or DAG-CBOR first.
- Decide encryption suite and key representation.
- Decide initial storage providers: local + IPFS first, S3 second, Filecoin third.
- Write threat model and test vectors.

Acceptance:

- A one-page security architecture decision record.
- Passing crypto round-trip test vectors.
- A minimal UCAN delegation chain verified in tests.

### Phase 1: Core Wallet Models and Local Encryption

Deliverables in `ipfs_datasets_py`:

- `wallet.models`
- `wallet.crypto`
- `wallet.manifest`
- Local encrypted storage backend.
- Unit tests for wallet/document/version/key-wrap/audit models.

Acceptance:

- Create wallet.
- Add document.
- Encrypt bytes.
- Decrypt bytes with authorized local device key.
- Fail decrypt with unauthorized key.
- Serialize and verify manifest deterministically.

### Phase 2: IPFS Storage Integration

Deliverables:

- `wallet.storage` adapter using `ipfs_backend_router`.
- Add encrypted payloads to IPFS.
- Pin encrypted payloads.
- Retrieve by CID and decrypt.
- Store wallet/document manifests as IPFS objects.

Acceptance:

- Add document to wallet and get CID-backed encrypted payload.
- Retrieve through IPFS backend and decrypt locally.
- Verify content hash and AEAD authentication.
- Tests run with a fake backend and optionally Kubo integration tests.

### Phase 3: UCAN Authorization and Delegation

Deliverables:

- Harden or replace mock UCAN code with spec-compatible delegation/invocation structures. The current core has a local signed invocation model; full external UCAN interop remains isolated behind `wallet.ucan`.
- Wallet-specific capability vocabulary.
- Delegation store and revocation store.
- Access-check middleware for decrypt/analyze/export operations.
- Key wrapping to grant actual decrypt capability only where intended.

Acceptance:

- Owner grants `document/analyze` without `document/decrypt`.
- Owner grants `document/read` with wrapped key.
- Delegate invocation succeeds only within resource, ability, time, and caveat bounds.
- Revoked grant fails.
- Expired grant fails.
- Delegation attenuation prevents a delegate from granting more than they received.

### Phase 4: Multi-Sig and Recovery

Deliverables:

- `wallet.multisig` approval abstraction.
- Threshold approval records.
- Root key rotation flow.
- Recovery-contact or recovery-share flow.
- Optional Safe smart account verifier adapter.

Acceptance:

- Administrative grant requires threshold approval when policy says so.
- Root rotation invalidates old admin path while preserving document access for approved devices.
- Recovery flow can restore wallet access in test fixtures.
- Failed or partial approvals do not mutate wallet state.

### Phase 5: Analysis Gateways

Deliverables:

- Wallet-aware wrappers around existing PDF/file conversion/GraphRAG/vector tools.
- Analysis policies that restrict output type.
- Redaction pipeline for derived outputs.
- Encrypted derived-output storage.

Acceptance:

- `document/analyze` can return a summary without plaintext export.
- `derived/read` can retrieve only permitted derived artifacts.
- Analysis invocation emits audit records.
- Cross-document analysis respects document subset restrictions.

### Phase 6: S3 and Filecoin Replication

Deliverables:

- S3 encrypted object mirror backend.
- Filecoin archival backend abstraction.
- Storage receipt model.
- Availability verifier and repair job interface. The core service now exposes synchronous verify/repair methods; scheduled background repair can build on the same API.

Acceptance:

- Same encrypted payload can be mirrored to IPFS and S3.
- Storage receipts are attached to document version manifests.
- Verifier reports missing/unpinned/unavailable replicas.
- Repair restores missing/tampered mirrors from a valid encrypted replica without exposing plaintext.
- Filecoin integration can be mocked in CI and enabled in production.

### Phase 7: API, MCP, and CLI

Deliverables:

- Python service API stabilization.
- MCP tools for wallet workflows.
- CLI commands under `ipfs-datasets wallet`.
- API documentation and examples.

Acceptance:

- CLI can create wallet, add document, share, issue/use invocation tokens, analyze, verify/repair encrypted storage, revoke, audit.
- MCP tools enforce the same authorization path as Python APIs.
- Docs include end-to-end examples.

### Phase 8: UI/UX in `wallet_interface`

Deliverables:

- App shell and API client.
- Upload/encryption/storage progress UI.
- Share/access request workflow.
- Delegate analysis workspace.
- Audit and security settings.

Acceptance:

- Non-technical user can add a document and share it with an advocate.
- Advocate can accept grant and run permitted analysis.
- User can revoke the grant and see future access denied.
- UI hides protocol detail by default but exposes advanced proof/storage receipts.

## Testing Strategy

Required test categories:

- Crypto test vectors.
- Manifest deterministic serialization.
- Storage adapter contract tests.
- UCAN delegation chain tests.
- Revocation tests.
- Multi-sig threshold tests.
- Access-control matrix tests.
- Analysis output policy tests.
- Audit hash-chain tests.
- End-to-end wallet workflow tests.

Representative access matrix:

| Grant | Plaintext | Summary | Fields | Embeddings | Re-share | Export |
| --- | --- | --- | --- | --- | --- | --- |
| `document/read` | yes | optional | optional | no | no | no |
| `document/analyze` + `derived/read` | no | yes | yes | optional | no | no |
| `document/share` | no | no | no | no | yes, bounded | no |
| `export/create` | yes | yes | yes | yes | no | yes |
| `wallet/admin` | policy-dependent | policy-dependent | policy-dependent | policy-dependent | yes | policy-dependent |

## Operational Risks and Mitigations

- Lost keys: implement recovery before production use with critical records.
- Overbroad grants: use purpose presets, short expirations, and capability previews.
- Metadata leakage: encrypt private metadata and avoid meaningful public names.
- Revocation misunderstanding: distinguish future denial from already-seen data.
- Storage unavailability: replicate and verify.
- UCAN ecosystem mismatch: isolate UCAN implementation behind interfaces and keep interop tests.
- S3 misconfiguration: treat S3 as an encrypted blob mirror only.
- Filecoin retrieval latency: use Filecoin for archival durability, not primary UX.
- AI analysis privacy: default to derived-only outputs and local analysis where possible.

## First Milestone Recommendation

Build a narrow vertical slice:

1. Create wallet.
2. Add one PDF.
3. Encrypt locally.
4. Store encrypted payload through IPFS backend and local mirror.
5. Create manifest.
6. Grant `document/analyze` to a delegate DID for one document.
7. Run a wallet-aware summary extraction that returns derived output without plaintext export.
8. Revoke the grant.
9. Verify subsequent access fails.
10. Show the workflow through a minimal UI screen or CLI demo.

This milestone proves the hard boundaries: encryption, storage, delegation, analysis gating, revocation, and audit. S3, Filecoin, Safe integration, advanced recovery, and richer UI should follow after that path is solid.

## Proposed Issue Breakdown

- Create `ipfs_datasets_py.wallet` package skeleton.
- Implement wallet/document/version/key-wrap/grant/audit models.
- Implement deterministic manifest serializer.
- Implement envelope encryption helper and test vectors.
- Implement local encrypted blob store.
- Implement IPFS storage adapter.
- Implement wallet capability vocabulary.
- Replace or wrap mock UCAN manager with wallet-specific delegation verifier.
- Implement revocation store.
- Implement wallet access guard.
- Implement wallet-aware PDF summary analysis.
- Implement audit hash chain.
- Implement CLI vertical slice.
- Implement MCP wallet tools.
- Implement S3 mirror backend.
- Implement Filecoin archival backend interface.
- Implement multi-sig approval abstraction.
- Implement Safe verifier adapter.
- Build `wallet_interface` UI upload flow.
- Build share/access request flow.
- Build delegate analysis workspace.
- Build audit/security settings screens.
