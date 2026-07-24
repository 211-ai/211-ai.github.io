# World Human-Aid Integration Audit

Audit ID: `WORLDCOIN-AUTO-001`  
Objective: `WORLDCOIN-G002`  
Audit date: 2026-07-24  
Disposition: compatibility boundaries frozen; production human-aid enablement blocked

## Scope, method, and evidence rules

This is a static, repository-source audit of the World ID, document-wallet,
proof, provider, persistence, UI, payout, and reconciliation boundaries named
by `WORLDCOIN-G002`. The goal and exact acceptance gate are defined at
`docs/planning/WORLDCOIN_HUMAN_AID_OBJECTIVE_HEAP.md::WORLDCOIN-G002`.

Every factual finding below cites `path::symbol` (or a manifest/artifact key).
An absence finding cites both the searched integration surface and the child
goal that owns the missing boundary. Forward-looking deductions are prefixed
**Speculation** and are not treated as observed fact.

The audit inspected files only. It did not call World or any other network,
look up a secret, download or install a package, pull or start a container,
execute a ZKP/database/npm toolchain, or initialize package core. The
machine-readable record of that constraint is
`data/worldcoin_human_aid/audit/offline-bootstrap-proposal.json::audit_observation`;
the contract is a data/source parser only at
`tests/world_aid/test_integration_audit_contract.py`.

## Executive result

The existing World integration is a useful wallet-binding prototype, but it is
not a human-aid eligibility or payment system. Server-side configuration, RP
signing, Developer Portal verification, a durable binding model, proof-center
receipts, and an IDKit 4.1.8 UI are present
(`wallet_interface/world_id.py::WorldIdConfig`;
`wallet_interface/app_service.py::register_world_id_verification`;
`ipfs_datasets_py/ipfs_datasets_py/wallet/models.py::WorldIdBinding`;
`wallet_interface/ui/package-lock.json::node_modules/@worldcoin/idkit`).
The frozen external compatibility label is **World Developer Portal verify API
v4**, represented by the default `/api/v4/verify/{rp_id}` URL construction
(`wallet_interface/world_id.py::verify_world_id_proof`).

Production promotion is blocked by unsafe compatibility behavior and missing
trust domains. In particular, the simulated profile receipt is **not
eligibility**, and provider signal context is **unenforced**
(`ipfs_datasets_py/ipfs_datasets_py/wallet/service.py::create_document_profile_proof`;
`wallet_interface/app_service.py::create_provider_staff_world_id_rp_signature`;
`wallet_interface/app_service.py::register_world_id_verification`).

The frozen machine ownership and conflict map is
`data/worldcoin_human_aid/audit/component-map.json::components`. It is the
authoritative audit inventory, not a runtime registry.

## Capability and compatibility matrix

| Capability | Classification | Observed boundary | Frozen disposition |
|---|---|---|---|
| World configuration and RP signatures | Partial | Configuration validates environment, IDs, actions, signing material, TTL, and verify URL; secrets are omitted from the public projection (`wallet_interface/world_id.py::load_world_id_config`; `wallet_interface/world_id.py::WorldIdConfig.public_dict`). | Preserve the current API through an additive G004 adapter; do not broaden remote I/O. |
| IDKit parsing and verification | Partial | Both protocol `3.0` and `4.0` are normalized and sent to the Developer Portal verifier (`wallet_interface/world_id.py::normalize_idkit_response`; `wallet_interface/world_id.py::verify_world_id_proof`). | G004 must default legacy off and define a v3 sunset without silently changing old wallet consumers. |
| Wallet binding | Unsafe to reuse | A verified result becomes a durable `WorldIdBinding` plus proof receipt (`wallet_interface/app_service.py::register_world_id_verification`; `ipfs_datasets_py/ipfs_datasets_py/wallet/service.py::add_world_id_binding`). | G006 owns a private/public adapter, accurate protocol labels, signal binding, expiry, and revocation semantics. |
| World status API | Unsafe to reuse | The optional `actor_did` permits unauthenticated status, and status returns all serialized bindings (`wallet_interface/routes/world_id.py::get_world_id_status`; `wallet_interface/app_service.py::get_world_id_status`). | Preserve route shape only until G006/G008 provide authenticated summary and privileged detail projections. |
| Local wallet snapshots | Unsafe to reuse | Snapshots are JSON files containing hex principal secrets and raw serialized World binding objects (`ipfs_datasets_py/ipfs_datasets_py/wallet/repository.py::LocalWalletRepository._save_wallet_snapshot`; `ipfs_datasets_py/ipfs_datasets_py/wallet/service.py::export_wallet_snapshot`). | Local development only; G007 owns encrypted transactional replacement and migration. |
| Document privacy profile | Simulated | `create_document_profile_proof` always calls `create_simulated_proof_receipt` with type `document_privacy_profile` (`ipfs_datasets_py/ipfs_datasets_py/wallet/service.py::create_document_profile_proof`; `ipfs_datasets_py/ipfs_datasets_py/wallet/proofs.py::create_simulated_proof_receipt`). | Never accept as program eligibility. G012/G016 own the eligibility statement and production verifier. |
| Location HTTP proof backend | Partial | The backend transmits statement, public inputs, and witness to an injected HTTP prover (`wallet_interface/proof_backends.py::HttpLocationRegionProofBackend.prove_location_region`). | Preserve only as an isolated proof adapter; it does not establish program eligibility. |
| Provider staff context | Partial | The RP-signature response adds provider and staff IDs plus `signal_context`, while registration validates action and proof without comparing those response annotations (`wallet_interface/app_service.py::create_provider_staff_world_id_rp_signature`; `wallet_interface/app_service.py::register_world_id_verification`). | Do not treat it as provider approval. G021/G022 own registry-backed authorization and claim-context binding. |
| IDKit UI | Implemented | The UI requests a signature, opens `IDKitRequestWidget`, posts the result, refreshes status, and presents non-claim/private-field messaging (`wallet_interface/ui/src/shared/components/WorldIdVerificationPanel.tsx::WorldIdVerificationPanel`). | Preserve cancellation, disabled, manual-path, accessibility, and privacy messages while APIs migrate. |
| Issuer lifecycle | Missing | `WorldIdBinding` stores issuer schema IDs, but the audited integration exposes no aid-issuer issuance/rotation/suspension/revocation verifier (`ipfs_datasets_py/ipfs_datasets_py/wallet/models.py::WorldIdBinding.issuer_schema_ids`; `docs/planning/WORLDCOIN_HUMAN_AID_OBJECTIVE_HEAP.md::WORLDCOIN-G010`). | G010/G011 must define issuer and policy registries before eligibility verification. |
| WLD payout and chain reconciliation | Missing | The heap assigns payout intent, treasury/chain submission, and reconciliation to G023–G026 rather than an existing audited World wallet symbol (`docs/planning/WORLDCOIN_HUMAN_AID_OBJECTIVE_HEAP.md::WORLDCOIN-G023`; `docs/planning/WORLDCOIN_HUMAN_AID_OBJECTIVE_HEAP.md::WORLDCOIN-G026`). | No signing, broadcast, payout, or settlement claim may be inferred from current World verification. |

## Confirmed unsafe findings

### A-01 — simulated profile receipt is not eligibility

`DataWalletService.create_document_profile_proof` creates a simulated
`document_privacy_profile` receipt whose statement says a document was
profiled with redacted metadata. It does not evaluate a program, benefit
period, issuer, policy, eligibility predicate, or decision
(`ipfs_datasets_py/ipfs_datasets_py/wallet/service.py::create_document_profile_proof`).
The helper explicitly sets `is_simulated=True` and
`proof_system="simulated"`
(`ipfs_datasets_py/ipfs_datasets_py/wallet/proofs.py::create_simulated_proof_receipt`).
Therefore the simulated profile receipt is **not eligibility** and must fail
closed if presented to an eligibility or payout verifier
(`data/worldcoin_human_aid/audit/component-map.json::document-profile-receipt`).

### A-02 — provider signal context is unenforced

`create_provider_staff_world_id_rp_signature` returns `provider_id`,
`provider_staff_id`, and the literal
`signal_context="provider_staff_verification"`
(`wallet_interface/app_service.py::create_provider_staff_world_id_rp_signature`).
Those values are not fields in
`ProviderStaffWorldIdRpSignatureRequest`'s downstream verification request,
whose payload model contains only `actor_did` and `idkit_payload`
(`wallet_interface/routes/world_id.py::WorldIdVerificationRequest`).
`register_world_id_verification` records normalized signal hashes but does not
compare them with a canonical provider/program/claim context
(`wallet_interface/app_service.py::register_world_id_verification`).
Provider signal context is therefore **unenforced**, and the current response
annotation is not provider authorization or payout approval.

### A-03 — plaintext secrets and raw bindings in LocalWalletRepository

`LocalWalletRepository._save_wallet_snapshot` writes canonical JSON directly
to a filesystem path; its envelope hash detects content change but does not
encrypt the snapshot
(`ipfs_datasets_py/ipfs_datasets_py/wallet/repository.py::LocalWalletRepository._save_wallet_snapshot`).
`DataWalletService.export_wallet_snapshot` emits `principal_secrets` as hex
strings and emits each complete, raw `WorldIdBinding.to_dict()` object
(`ipfs_datasets_py/ipfs_datasets_py/wallet/service.py::export_wallet_snapshot`).
Thus `LocalWalletRepository` snapshots plaintext principal secrets and raw
World bindings. It is explicitly frozen as local-development-only rather than
production encrypted transactional storage
(`data/worldcoin_human_aid/audit/component-map.json::local-wallet-repository`).

### A-04 — unauthenticated status returns full bindings

The HTTP route declares `actor_did: str | None = None`
(`wallet_interface/routes/world_id.py::get_world_id_status`).
The service checks authorization only when that value is present, then returns
`binding.to_dict()` for every wallet binding, including actor, RP/app/action,
protocol, nullifier reference, credential identifiers, issuer schema IDs,
session presence data, status, timestamps, and metadata
(`wallet_interface/app_service.py::get_world_id_status`;
`ipfs_datasets_py/ipfs_datasets_py/wallet/models.py::WorldIdBinding`).
Therefore unauthenticated status returns full bindings. G006/G008 must add an
authenticated projection without deleting the response contract before UI
migration tests exist
(`wallet_interface/ui/src/features/wallet/lib/walletApi.ts::WorldIdWalletStatus`).

### A-05 — legacy acceptance defaults on

`WorldIdConfig.allow_legacy_proofs` defaults to `True`, and
`load_world_id_config` uses `default=True` for
`WORLD_ID_ALLOW_LEGACY_PROOFS`
(`wallet_interface/world_id.py::WorldIdConfig`;
`wallet_interface/world_id.py::load_world_id_config`).
The UI forwards that value to `IDKitRequestWidget`
(`wallet_interface/ui/src/shared/components/WorldIdVerificationPanel.tsx::WorldIdVerificationPanel`).
Legacy acceptance therefore defaults on in the audited wallet integration.
G004 owns the human-aid default-off and explicit migration policy.

### A-06 — accepted v3 evidence can be mislabeled v4

The normalizer accepts protocol `3.0`, and registration stores that exact
protocol on the binding
(`wallet_interface/world_id.py::normalize_idkit_response`;
`wallet_interface/app_service.py::register_world_id_verification`).
Receipt construction nevertheless uses the constant
`WORLD_ID_PROOF_SYSTEM="world_id_idkit_v4"` and the circuit ID
`world-id-idkit-v4-developer-portal` for every binding, while separately
putting the binding's protocol version into the statement
(`ipfs_datasets_py/ipfs_datasets_py/wallet/service.py::WORLD_ID_PROOF_SYSTEM`;
`ipfs_datasets_py/ipfs_datasets_py/wallet/service.py::_create_world_id_proof_receipt`).
Receipts can therefore mislabel accepted v3 evidence as v4. Existing receipts
must not be rewritten in place; G004/G006 must introduce protocol-accurate
labels plus a migration adapter and tests.

### A-07 — raw nullifier durability is a distinct private risk

The public binding stores a keyed `nullifier_ref`, but
`DataWalletService._store_world_id_private_nullifier` separately retains the
raw nullifier and a replay commitment in service memory
(`ipfs_datasets_py/ipfs_datasets_py/wallet/service.py::_store_world_id_private_nullifier`).
The snapshot exports raw binding objects and principal secrets but no
`world_id_private_nullifiers` map, and snapshot import restores bindings
without calling `_store_world_id_private_nullifier`
(`ipfs_datasets_py/ipfs_datasets_py/wallet/service.py::export_wallet_snapshot`;
`ipfs_datasets_py/ipfs_datasets_py/wallet/service.py::import_wallet_snapshot`).
G006/G007 must explicitly define private nullifier retention, uniqueness,
encryption, deletion, and migration rather than relying on incidental snapshot
behavior.

## Missing trust boundaries

The following are missing from the audited integration and are not implied by
World proof-of-human:

1. **EIP-1271 SIWE.** Current authorization checks membership of a supplied
   `actor_did`; it is not an EIP-4361 session and exposes no EIP-1271
   contract-wallet signature verifier
   (`wallet_interface/app_service.py::_require_portal_actor`;
   `docs/planning/WORLDCOIN_HUMAN_AID_OBJECTIVE_HEAP.md::WORLDCOIN-G008`).

2. **Issuer credential lifecycle.** A binding can carry
   `issuer_schema_ids`, but no aid issuer registry provides issuance,
   rotation, expiry, suspension, revocation, or status evidence
   (`ipfs_datasets_py/ipfs_datasets_py/wallet/models.py::WorldIdBinding`;
   `docs/planning/WORLDCOIN_HUMAN_AID_OBJECTIVE_HEAP.md::WORLDCOIN-G010`).

3. **Encrypted transactional storage.** The local repository writes one
   plaintext JSON snapshot through a temporary-file replacement; it is not an
   encrypted multi-record transaction, row-locking, migration, backup, or
   recovery boundary
   (`ipfs_datasets_py/ipfs_datasets_py/wallet/repository.py::LocalWalletRepository`;
   `docs/planning/WORLDCOIN_HUMAN_AID_OBJECTIVE_HEAP.md::WORLDCOIN-G007`).

4. **Payout.** No current audited World binding function creates an idempotent
   payout intent, validates WLD amount/recipient/chain, obtains treasury
   approval, signs, or broadcasts; those interfaces are assigned to G023–G025
   (`data/worldcoin_human_aid/audit/component-map.json::payout-reconciliation`;
   `docs/planning/WORLDCOIN_HUMAN_AID_OBJECTIVE_HEAP.md::WORLDCOIN-G023`).

5. **Reconciliation.** No current audited World binding function tracks
   pending/final/reverted/replaced transactions, confirmation policy,
   reorganization, or accounting settlement; G026 owns that boundary
   (`data/worldcoin_human_aid/audit/component-map.json::payout-reconciliation`;
   `docs/planning/WORLDCOIN_HUMAN_AID_OBJECTIVE_HEAP.md::WORLDCOIN-G026`).

6. **Eligibility composition.** World proof-of-human, a document privacy
   profile, an aid issuer credential, a policy decision, provider approval,
   and payout settlement are separate trust states; the canonical composition
   is assigned to G005/G022 rather than the present binding model
   (`docs/planning/WORLDCOIN_HUMAN_AID_OBJECTIVE_HEAP.md::WORLDCOIN-G005`;
   `docs/planning/WORLDCOIN_HUMAN_AID_OBJECTIVE_HEAP.md::WORLDCOIN-G022`).

## Compatibility boundary freeze

The following interfaces are deletion-prohibited until the owning goal ships
an additive adapter, fixtures for old and new representations, consumer
migration, and an explicit retirement record
(`data/worldcoin_human_aid/audit/component-map.json::compatibility_policy`):

- World configuration and signature fields returned by
  `WorldIdConfig.public_dict`
  (`wallet_interface/world_id.py::WorldIdConfig.public_dict`).
- The World ID route paths and request shapes
  (`wallet_interface/routes/world_id.py::create_router`).
- `WorldIdBinding` serialization and old snapshot v1 import
  (`ipfs_datasets_py/ipfs_datasets_py/wallet/models.py::WorldIdBinding.to_dict`;
  `ipfs_datasets_py/ipfs_datasets_py/wallet/repository.py::LocalWalletRepository._snapshot_from_payload`).
- Existing proof receipt serialization, while preventing simulated and
  mislabeled receipts from entering the new aid verifier
  (`ipfs_datasets_py/ipfs_datasets_py/wallet/models.py::ProofReceipt`;
  `ipfs_datasets_py/ipfs_datasets_py/wallet/service.py::_create_world_id_proof_receipt`).
- UI disabled/cancelled/non-claim behavior and API type consumers
  (`wallet_interface/ui/src/shared/components/WorldIdVerificationPanel.tsx::WorldIdVerificationPanel`;
  `wallet_interface/ui/src/app/components/WorldIdSurfaceStatus.tsx::WorldIdSurfaceStatus`;
  `wallet_interface/ui/src/features/wallet/lib/walletApi.ts::WorldIdWalletStatus`).
- The `ProofBackend` adapter seam, while forbidding current location or
  simulated semantics from being renamed as eligibility
  (`wallet_interface/proof_backends.py::HttpLocationRegionProofBackend`;
  `ipfs_datasets_py/ipfs_datasets_py/wallet/proofs.py::ProofBackend`).

Unsafe behavior is frozen as an input to migration, not approved for reuse.
Specifically, plaintext secrets, unauthenticated full status, default-on
legacy evidence, v3-as-v4 labels, and unenforced provider context must be
blocked at the new human-aid boundary
(`data/worldcoin_human_aid/audit/component-map.json::components`).

## Offline bootstrap decision record

The source inventory records locked IDKit npm packages; declared Python and
FastAPI inputs; absent SIWE/EIP-1271, chain, PostgreSQL, driver, and migration
inputs; and present versus operator-provided ZKP inputs
(`data/worldcoin_human_aid/audit/offline-bootstrap-proposal.json::inventory`).
The proposal does not choose or approve dependencies. It asks humans to select
exact versions, checksums, licenses, provenance, SBOM policy, cache/image/key
locations, and smoke tests before any acquisition or execution
(`data/worldcoin_human_aid/audit/offline-bootstrap-proposal.json::human_approval_questions`;
`data/worldcoin_human_aid/audit/offline-bootstrap-proposal.json::approval_gate`).

## Speculation register

- **Speculation — traffic exposure:** if wallet identifiers are guessable or
  leak through another surface, unauthenticated full-binding status could
  permit correlation. This impact was not exercised; the observed prerequisite
  is only the optional actor and full response
  (`wallet_interface/routes/world_id.py::get_world_id_status`;
  `wallet_interface/app_service.py::get_world_id_status`).
- **Speculation — label consumers:** downstream consumers may trust the
  `world_id_idkit_v4` label without checking `statement.protocol_version`.
  No such production consumer was demonstrated; the contradictory fields are
  observed in receipt construction
  (`ipfs_datasets_py/ipfs_datasets_py/wallet/service.py::_create_world_id_proof_receipt`).
- **Speculation — snapshot compromise:** filesystem disclosure could expose
  controller/device grant secrets and enable unauthorized wallet operations.
  No compromise was performed; plaintext hex serialization is observed
  (`ipfs_datasets_py/ipfs_datasets_py/wallet/service.py::export_wallet_snapshot`).

## Acceptance trace

| G002 gate | Evidence |
|---|---|
| Claims cite source/contract and speculation is labeled | This report's evidence rule, finding citations, and speculation register |
| Exact unsafe facts recorded | Findings A-01 through A-06 |
| Missing trust domains and stable machine ownership | “Missing trust boundaries” and `data/worldcoin_human_aid/audit/component-map.json` |
| Offline installed/missing inventory and human questions | `data/worldcoin_human_aid/audit/offline-bootstrap-proposal.json` |
| Contract causes no prohibited integration action | `tests/world_aid/test_integration_audit_contract.py` and proposal `audit_observation` |

The objective-validation repair is recorded at
`data/worldcoin_human_aid/agent_supervisor/discovery/2026-07-24-worldcoin-auto-001-integration-audit.md`
and aligned back to
`docs/planning/WORLDCOIN_HUMAN_AID_OBJECTIVE_HEAP.md::WORLDCOIN-G002`.
