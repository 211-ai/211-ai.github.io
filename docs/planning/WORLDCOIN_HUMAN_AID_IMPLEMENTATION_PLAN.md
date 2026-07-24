# Worldcoin Human-Aid Verification and WLD Disbursement Implementation Plan

Last reviewed: 2026-07-24

Status: proposed implementation architecture

## Executive Objective

Complete the existing World integration so 211-AI can support a
privacy-preserving aid workflow in which:

1. a person proves control of a recipient wallet;
2. the person may optionally present a World ID proof-of-human signal;
3. authorized issuers place document-derived credentials in the person's
   encrypted document wallet;
4. the wallet proves, in zero knowledge, that those credentials satisfy a
   versioned aid-program policy;
5. an authorized provider makes and records the actual eligibility decision;
6. an authorized provider treasury sends WLD on World Chain; and
7. 211-AI reconciles the transfer to finality without publishing documents,
   sensitive eligibility facts, or a label that the recipient is experiencing
   homelessness.

The five assurance domains are deliberately independent:

| Domain | What it proves | What it does not prove |
| --- | --- | --- |
| Wallet authentication | Control of a World Chain address, using SIWE | Humanity, legal identity, or eligibility |
| Optional World ID | A valid World ID credential for the configured action and relying party | Wallet control, homelessness, legal identity, or aid eligibility |
| Document credential trust | An authorized issuer attested to selected claims and the credential is current | That a program should approve the person |
| Eligibility ZKP | Committed, non-revoked claims satisfy a specific versioned policy | The public identity of the claimant or an autonomous final adverse decision |
| Provider and treasury authorization | An accountable provider approved a bounded payout and the treasury submitted it | The contents of the recipient's private documents |

World ID is optional anti-abuse evidence. It is not authentication and it is
not the eligibility engine. The eligibility proof is owned by 211-AI and its
program partners, not by World. The payout is owned by an authorized provider
treasury, not by the recipient's World App.

## Companion Artifacts

This plan defines the architecture and safety invariants. Execution is split
into the following companion artifacts:

- Source objective heap:
  `docs/planning/WORLDCOIN_HUMAN_AID_OBJECTIVE_HEAP.md`
- Agent-supervisor operating procedure:
  `docs/planning/WORLDCOIN_HUMAN_AID_AGENT_SUPERVISOR_RUNBOOK.md`
- Generated, runtime taskboard:
  `data/worldcoin_human_aid/agent_supervisor/WORLDCOIN_HUMAN_AID_TODO.md`

The objective heap is the reviewable source of truth. The runtime taskboard is
generated state and must not silently weaken the invariants in this plan.

## Non-Negotiable Safety Invariants

1. World ID proof-of-human is optional for access to essential services. A
   person without World App, a smartphone, an Orb credential, reliable
   connectivity, or an accessible biometric flow must have a documented manual
   path.
2. World ID must never be treated as a login token. Wallet ownership is proven
   separately with MiniKit wallet authentication/SIWE or another approved
   controller proof.
3. A World ID proof must never be treated as proof of homelessness, income,
   residency, disability, benefit eligibility, or ownership of a document in
   the 211-AI wallet.
4. A document-profile proof is not an eligibility proof. In particular, the
   existing simulated `document_privacy_profile` receipt must be rejected as
   money authorization in every non-test environment.
5. A failed, missing, expired, or unsupported proof routes to human review or a
   manual evidence path. It must not autonomously deny housing, food, health,
   cash assistance, or another essential service.
6. Raw documents, extracted document text, homelessness status, exact
   eligibility reasons, World ID nullifiers, and wallet-to-person mappings must
   not be written to World Chain, a public event, a public IPFS object, a public
   QR bundle, or an unredacted metric or log.
7. A WLD transfer must not be submitted unless wallet ownership, provider
   authority, policy version, proof result, payout terms, replay protection, and
   human approval have been bound into one server-issued claim commitment.
8. A transaction is not complete when it is submitted. Completion requires a
   successful receipt, the expected WLD `Transfer` event, the expected chain,
   token, sender, recipient, and amount, and the configured named settlement
   state; an operational block-depth threshold alone is never called finality.
9. Treasury keys must not be stored in source, browser code, ordinary process
   environment files, or the document wallet. Use a Safe, HSM, MPC signer, or
   an equivalently reviewed custody boundary with limits and dual control.
10. Public and provider-facing language must not overclaim. Use phrases such as
    "wallet control verified," "optional proof-of-human verified," "eligibility
    proof verified," and "provider approved" as separate statuses.

## Official World Platform Facts and Version Baseline

The implementation must be checked against official documentation again at
each deployment gate. The following baseline was current when this plan was
reviewed on 2026-07-23.

### World ID 4

- The supported integration target is IDKit 4.x.
- The backend holds `app_id`, `rp_id`, and the RP `signing_key`; the signing key
  is never sent to browser code.
- The browser obtains a short-lived signed RP context, invokes IDKit, and
  forwards the returned IDKit response unchanged to the 211-AI backend.
- The backend verifies that response through
  `POST https://developer.world.org/api/v4/verify/{rp_id}` and then enforces its
  own stored action, signal, credential, expiry, and replay policy.
- In World ID 4, uniqueness and session continuity are different concerns.
  A uniqueness nullifier is stable for a person, RP, and action and must be
  consumed once; a session proof uses `session_id` for continuity and a fresh
  `session_nullifier` for replay control. `session_id` is private, linkable
  security data. Each action must declare which proof mode it uses.
- A uniqueness nullifier is returned as a `0x`-prefixed 256-bit integer. Parse
  it once, reject malformed, negative, or out-of-range values, and encode the
  unsigned value canonically before indexing or applying an HMAC. Never use
  caller spelling, hex casing, or leading-zero variants as distinct replay
  keys.
- The World ID 4 migration transition is documented as running from
  2026-06-01 through 2027-03-31. World documents schedule v3 proof generation
  to end on 2027-04-01. On the review date, 211-AI is inside that transition.
  All new work must generate and verify v4 proofs. Legacy acceptance, if
  temporarily required, must be an explicit, metered, fail-closed compatibility
  path with a removal deadline no later than 2027-03-31. The new aid flow
  defaults `allow_legacy_proofs` to false. Any accepted legacy evidence keeps
  its actual protocol/circuit label and can never be recorded as v4.
- `proofOfHuman` is the current proof-of-human credential. Passport credentials
  and Identity Check can attest selected document-derived properties, but they
  are not a general verifier for arbitrary 211-AI document-wallet contents.
- Identity Check remains a separately reviewed/preview capability. A feasibility
  task may contact World about age, document type, issuing country, or
  nationality attestations, but production eligibility must not depend on it.
- `require_user_presence` can request fresh presence when a risk policy
  requires it; it is not legal identity or eligibility evidence.

Official references:

- `https://docs.world.org/world-id/idkit/integrate`
- `https://docs.world.org/world-id/idkit/signatures`
- `https://docs.world.org/api-reference/developer-portal/verify`
- `https://docs.world.org/world-id/4-0-migration`
- `https://docs.world.org/world-id/idkit/credentials`
- `https://docs.world.org/world-id/credentials/9303`

### Wallet Authentication and MiniKit

- World explicitly distinguishes World ID from authentication. For World App
  users, use `MiniKit.walletAuth()` and verify the returned SIWE message on the
  backend with the official verification helper.
- World documents a minimum of eight alphanumeric characters for a SIWE nonce.
  This financial workflow raises that floor: generate at least 128 bits of
  cryptographic entropy in an alphanumeric-compatible, single-use, expiring
  value. The server, not the client, controls the expected domain, URI, chain,
  nonce, issued-at time, expiration time, and request ID.
- `MiniKit.pay()` asks the current user to pay a recipient. It is useful for
  incoming payments but is not a service-provider treasury disbursement API.
- `MiniKit.sendTransaction()` can support an interactive provider approval
  transaction. It returns a `userOpHash`; the backend resolves it through
  `GET /api/v2/minikit/userop/{user_op_hash}`.
- Current World Mini Apps documentation uses World Chain mainnet (`480`) for
  `sendTransaction`, and the official FAQ says Mini App transaction testing
  is not supported on testnet. Keep this adapter fixture-only during the
  Sepolia phase. Recheck the documentation at the release gate before a
  separately approved, tiny mainnet canary.
- MiniKit payment transactions are verified through
  `GET /api/v2/minikit/transaction/{transaction_id}?app_id=...&type=payment`
  with a backend Developer Portal API key.
- MiniKit v2 removed SignatureTransfer. Any interactive token approval path must
  use a reviewed allowance/approve flow and an allowlisted contract.

Official references:

- `https://docs.world.org/mini-apps/commands/wallet-auth`
- `https://docs.world.org/mini-apps/commands/pay`
- `https://docs.world.org/mini-apps/commands/send-transaction`
- `https://docs.world.org/mini-apps/more/faq`
- `https://docs.world.org/api-reference/developer-portal/get-transaction`
- `https://docs.world.org/api-reference/developer-portal/get-user-operation`

### World Chain and WLD

| Environment | Chain ID | Hex chain ID | WLD contract |
| --- | ---: | --- | --- |
| World Chain mainnet | `480` | `0x1e0` | `0x2cfc85d8e48f8eab294be644d9e25c3030863003` |
| World Chain Sepolia | `4801` | `0x12c1` | Resolve from the reviewed deployment manifest; never substitute the mainnet address |

World Chain targets approximately two-second blocks. Chain ID, token address,
token decimals, RPC endpoints, explorer URLs, confirmation depth, and contract
code hash must be environment-scoped configuration. At startup, the payout
worker must check the configured chain ID and token bytecode and fail closed on
a mismatch.

World Chain is an OP Stack L2 with Ethereum (or Ethereum Sepolia) as settlement
and data-availability layer. The reconciler must distinguish an L2 receipt and
block count from the RPC's safe/finalized view and any program-required L1
settlement checkpoint. The exact accounting threshold is a versioned policy,
not a hard-coded claim that a fixed number of two-second blocks is final.

Direct treasury transactions are tracked through World Chain RPC receipts and
WLD ERC-20 `Transfer` logs, or through an independently reviewed indexer. The
MiniKit transaction-status API is not the source of truth for a transaction
signed by the provider treasury.

Official references:

- `https://docs.world.org/world-chain/quick-start/info`
- `https://docs.world.org/world-chain/reference/useful-contracts`
- `https://docs.world.org/world-chain/providers/data`

World ID also documents an on-chain `WorldIDVerifier` v4 proxy at
`0x00000000009E00F9FE82CfeeBB4556686da094d7` for production and
`0x703a6316c975DEabF30b637c155edD53e24657DB` for staging. These addresses must
be revalidated before use. The recommended MVP remains backend `/v4/verify`;
on-chain verification is justified only when a contract must enforce the proof.
Any application contract must maintain its own consumed-nullifier protection.

Reference:
`https://docs.world.org/world-id/idkit/onchain-verification`

## Current Repository Audit

### Capabilities already present

The existing integration is a useful foundation:

- `wallet_interface/world_id.py` parses current IDKit responses, generates RP
  signatures, and calls the World Developer Portal verifier.
- `wallet_interface/routes/world_id.py` exposes configuration, status, RP
  signature, provider-staff signature, registration, and revoke routes.
- `wallet_interface/app_service.py` implements
  `create_world_id_rp_signature`,
  `create_provider_staff_world_id_rp_signature`, and
  `register_world_id_verification`.
- `wallet_interface/ui/src/shared/components/WorldIdVerificationPanel.tsx`
  provides an IDKit UI surface using `@worldcoin/idkit` 4.x.
- `WorldIdBinding` and `ProofReceipt` in
  `ipfs_datasets_py/ipfs_datasets_py/wallet/models.py` give the durable wallet
  model a place for private binding state and sanitized receipts.
- `ipfs_datasets_py/ipfs_datasets_py/logic/zkp/` contains backend-neutral ZKP
  infrastructure, ProveKit and Groth16 work, verifier registries, witness
  handling, and on-chain support.
- UCAN grants, encrypted document records, snapshots, audit events, export
  bundles, and proof-center UI are already available.
- The prior implementation plans
  `docs/planning/WORLD_ID_IDKIT_WALLET_IMPLEMENTATION_PLAN.md` and
  `docs/planning/PROVEKIT_ZKP_LOGIC_IMPLEMENTATION_PLAN.md` define much of the
  completed foundation.

### Gaps that block a safe aid payout

1. The provider-staff RP-signature response includes provider identifiers and a
   `signal_context`, but those values are not yet demonstrably bound as the
   server's expected signal in the proof that is later verified.
2. Wallet World ID registration records a signal reference but does not provide
   the full, server-stored expected-signal ceremony needed to bind the proof to
   the wallet, claim, provider, program, and expiry.
3. The registration route accepts a caller-supplied `actor_did`; the request
   model drops the UI's action/signal fields; and status can return bindings
   without an authenticated principal. Those existing routes are not an
   authorization boundary for a financial workflow. In addition, the current
   World configuration defaults legacy proof acceptance on, while the wallet
   receipt labels the circuit `world-id-idkit-v4-developer-portal` regardless
   of the accepted protocol version. That can misrepresent v3 evidence as v4
   and is prohibited in the new aid flow.
4. World replay protection is process-local. The configured
   `WORLD_ID_NULLIFIER_HMAC_KEY` is not used by the binding path, the raw
   nullifier index is not restored from snapshots, and no transactional
   cross-worker uniqueness constraint survives restart.
5. `LocalWalletRepository` is explicitly a local-development repository, but
   it writes `export_wallet_snapshot()` as plaintext JSON. That snapshot
   includes hex-encoded `principal_secrets` and serialized `WorldIdBinding`
   values such as `session_id`, actor, references, and metadata. It is
   prohibited for this production workflow until an encrypted, transactional
   store and migration exist.
6. The current World ID status route permits an omitted `actor_did` and returns
   complete binding dictionaries; the proof receipt also includes internal
   wallet and binding references. Neither response is an acceptable public or
   unauthenticated projection.
7. Binding expiry is not enforced at use time, and revoking a binding does not
   invalidate its existing proof receipt. Provider-staff setup currently checks
   only non-empty identifiers rather than an organization, role, and program
   authorization policy.
8. There is no MiniKit wallet-auth/SIWE ceremony binding the recipient's World
   Chain address to the claim.
9. The Python backend has no pinned, EIP-1271-capable World wallet-auth
   verification boundary, and the UI does not currently depend on
   `@worldcoin/minikit-js`. A simple Python ECDSA recovery check would not be
   sufficient for World App smart accounts.
10. There is no issuer trust registry, credential schema/version policy,
   revocation-root protocol, or program-policy compiler for document-derived
   eligibility.
11. There is also no issuer enrollment, subject-binding, issuance/import,
    revocation-witness refresh, correction, or reissuance API that can put a
    trusted signed eligibility credential into the document wallet.
12. `create_document_profile_proof` in
   `ipfs_datasets_py/ipfs_datasets_py/wallet/service.py` creates a simulated
   `document_privacy_profile` receipt. It demonstrates a privacy boundary; it
   does not prove an aid eligibility predicate and must not authorize money.
13. `wallet_interface/proof_backends.py` currently contains a
   location-specific HTTP proof adapter. It is not a generic, production
   eligibility-proof verifier.
14. There is no durable eligibility case, payout intent, treasury authorization,
   idempotency, WLD transfer, finality, reorg, or reconciliation model.
15. There is no World Chain client, provider signer boundary, MiniKit provider
   transaction adapter, direct treasury adapter, or independent receipt
   watcher.
16. Existing Chainlink/consensus features are advisory data sources and do not
   authorize or prove a WLD payment.
17. Current UI proof labels do not yet force users and providers to distinguish
    wallet control, humanity, credential validity, proof verification, human
    approval, submission, and final settlement.

The implementation must close these gaps without weakening the completed
wallet, World ID, UCAN, and ZKP security boundaries.

## Scope

### MVP

- World Chain address ownership through SIWE.
- Optional World ID 4 proof-of-human, correctly bound to an aid claim.
- Authorized issuer credentials derived from encrypted wallet documents.
- A production, fail-closed eligibility ZKP for a small, versioned policy
  subset.
- Provider review and explicit approval with role, delegation, spend limits,
  and dual control.
- Direct WLD transfer from a controlled provider treasury on World Chain
  Sepolia, then a tightly capped mainnet pilot.
- Independent receipt, event, confirmation, reorg, and ledger reconciliation.
- Private receipts for the recipient and provider; a minimal public receipt
  containing no sensitive status.
- Manual evidence, non-digital enrollment, accessibility, and appeal paths.

### Post-MVP

- Interactive provider approval with MiniKit `sendTransaction`.
- Multiple credential issuers and policy families.
- Stablecoin-denominated aid alongside WLD where program rules allow it.
- Optional atomic payout authorization contract after independent audit.
- Privacy-preserving aggregate impact reporting with minimum cohort sizes.
- Carefully reviewed World Identity Check attributes.

### Non-goals

- Determining whether a person is homeless from World ID.
- Uploading documents to World, World Chain, or a public IPFS gateway.
- Making World ID mandatory for emergency or essential services.
- Treating a ZKP engine as the legal or policy decision-maker.
- Implementing a speculative aid token or custodial exchange.
- Storing WLD for recipients or controlling a recipient's wallet.
- Publishing a registry of aid recipients, wallet addresses, or benefit
  histories.
- Deploying unaudited smart contracts that can move production funds.

## Actors and Trust Boundaries

| Actor/component | Trusted for | Not trusted for |
| --- | --- | --- |
| Recipient/client | Consent, possession of wallet/document secrets | Self-asserted eligibility without issuer evidence |
| World App/IDKit | Returning a payload to be server-verified | Application authorization, wallet-session state, eligibility |
| World Developer Portal verifier | World credential verification result | 211-AI policy, document credentials, provider authority |
| Credential issuer | Signed claims within its approved schema and scope | Other issuers' claims or final program decisions |
| `ipfs_datasets_py` wallet | Encrypted records, grants, proof receipts, private audit state | Treasury signing |
| Eligibility prover | Producing a proof from a private witness | Deciding policy or approving a payout |
| Eligibility verifier | Checking a registered circuit and public inputs | Reading hidden evidence or making an adverse decision |
| Provider reviewer | Program decision within delegated authority | Treasury execution outside limits |
| Treasury signer/Safe | Signing bounded transactions after approval | Eligibility adjudication |
| World Chain RPC/indexer | Chain data subject to independent cross-checks | Application approval state or private identity |
| Supervisor agents | Implementing reviewed objectives and tests | Altering policy, signing funds, or bypassing approval gates |

No single actor should be able to assert eligibility, approve it, and move funds
without an independently auditable boundary.

## Target Component Architecture

### `ipfs_datasets_py`

Keep sensitive wallet and proof primitives in this submodule:

- credential envelope, issuer reference, schema version, validity interval, and
  revocation witness;
- versioned program-policy canonicalization;
- eligibility witness construction with memory/temp-file hygiene;
- production ZKP generation and verification;
- verifier/artifact registry and key rotation;
- eligibility proof receipt with public/private views;
- UCAN-scoped consent and witness-use grants;
- durable eligibility case and payout receipt records where they belong to the
  person's wallet.

No payout adapter or treasury secret belongs in this package.

Zero knowledge protects claims from the verifier and public proof consumer; it
does not hide the witness from the component that constructs and proves it. For
an initial server-side prover, treat the witness builder as a highly sensitive
data processor: require a narrowly scoped consent grant, decrypt only selected
fields, use isolated workers, bound memory, disable core dumps and swap, avoid
plaintext temp files, scrub buffers where practical, prohibit telemetry, and
destroy the witness immediately after a receipt is committed. Evaluate
client-side proving or a reviewed confidential-compute/TEE design as a later
privacy improvement, but do not claim either is safe until benchmarked and
threat-modeled.

### `wallet_interface`

Keep product/API orchestration here:

- SIWE nonce and wallet ownership ceremony;
- claim-intent creation and claim commitment;
- optional World ID RP signature and verification bound to that commitment;
- credential selection consent;
- proof request/verification;
- provider review and appeal APIs;
- payout intent, approval, submission, and status APIs;
- recipient and provider UI;
- sanitized QR/export views.

Use a concrete World-wallet authentication verifier rather than assuming an
externally owned account. The preferred first implementation is a small,
pinned Node verification boundary using the official
`@worldcoin/minikit-js` `verifySiweMessage` helper, with an injected World
Chain client for smart-account/EIP-1271 verification. The Python service sends
it a bounded SIWE envelope over a local authenticated interface and receives a
typed verification result. Pin the package and lockfile, inventory it in the
SBOM, reject any unconfigured RPC, and exercise both EOA and EIP-1271 fixtures.
An audited Python implementation is acceptable only if it demonstrates
protocol and EIP-1271 parity. The browser must also explicitly add and pin the
MiniKit dependency used to call `walletAuth`; IDKit alone does not provide
wallet authentication.

Dependency acquisition is a human-reviewed supply-chain step before the
default-deny implementation run: record package/version/integrity checksum,
license, transitive SBOM, provenance, and vulnerability review; place the exact
tarballs in an approved offline npm cache or internal mirror; then prove
`npm ci --offline` succeeds. An agent must not open general npm-registry egress
ad hoc to make G006 pass.

### Issuer credential gateway

Add a narrow issuer-to-wallet lifecycle spanning `wallet_interface` and
`ipfs_datasets_py`:

- enroll an issuer organization, authorized keys, schemas, programs, and
  suspension/revocation authority through a human-approved registry;
- obtain separate, purpose-bound consent to inspect source evidence and to
  issue selected claims;
- bind a holder-generated subject commitment to the authenticated wallet
  ceremony without giving the issuer or provider the holder secret;
- issue or import a signed, schema-versioned credential into encrypted wallet
  storage only after registry, signature, subject, scope, validity, and
  duplicate checks;
- refresh privacy-preserving revocation witnesses;
- request correction and perform reissuance while preserving the stable
  credential-subject commitment used for one-benefit protection; and
- retain issuer audit evidence without placing source documents, unrestricted
  OCR, or eligibility reasons in an API response.

Self-uploaded documents remain evidence for an issuer or human reviewer. They
must never become self-issued eligibility credentials.

### Production state and secret storage

`LocalWalletRepository` and raw exported snapshots are development-only; they
are neither a production database nor an acceptable portable production
backup. Any portable backup for staging/production must be authenticated,
envelope-encrypted, access-controlled, retention-bound, and restore-tested.
Before any staging identity or financial workflow, implement PostgreSQL as the
reference production transaction store with a versioned migration chain.
SQLite, DuckDB, in-memory repositories, and raw snapshots may support bounded
local tests, but they cannot satisfy staging or production persistence
acceptance. The PostgreSQL boundary must provide:

- envelope encryption through KMS/HSM-managed key references and explicit
  separation between wallet data, subject secrets, World proof evidence,
  reviewer data, and treasury records;
- database-level unique indexes for SIWE nonces, scoped World replay keys,
  eligibility-scope nullifiers, payout idempotency keys, transaction hashes,
  and event identities;
- compare-and-swap state transitions and an atomic outbox for signer,
  reconciliation, revocation, and audit work;
- authenticated, minimum-necessary projections instead of serializing
  `WorldIdBinding.to_dict()` or a wallet snapshot;
- encrypted backups, tested restore, key rotation, retention/deletion,
  disaster recovery, and audit access;
- a recoverable import/cutover workflow that inventories eligible source
  snapshots, migrates synthetic copies first, and keeps the source recoverable
  until encrypted authenticated backup/restore has been independently tested;
  and
- explicit development-only guards that reject `LocalWalletRepository` in
  staging or production.

No migration may log or copy `principal_secrets`, raw nullifiers, session IDs,
proof payloads, or source documents into task artifacts. The status API must
never serve a raw durable model. Supervisor agents may implement migrations and
exercise them against synthetic copies; retiring or overwriting any real
plaintext source is a separate, recorded human operation after backup/restore,
retention/deletion, key-rotation, and rollback checks pass.

### World Chain integration service

Create a narrow service boundary, either under `wallet_interface/services/` for
the first pilot or as a separately deployable worker when transaction volume
requires it:

- environment-pinned chain/token registry;
- Safe/HSM/MPC signer client;
- transaction construction and simulation;
- nonce and replacement policy;
- submission adapter;
- RPC/indexer receipt watcher;
- WLD `Transfer` event reconciliation;
- reorg recovery;
- append-only payout ledger and accounting export.

This service receives a signed payout authorization, never raw documents or a
ZKP witness.

### Proposed fail-closed release guards

The following are new configuration contracts to implement and test; this plan
does not assume they exist in the current repository:

- `WORLD_ID_ENABLED=0` keeps the existing World ID integration disabled unless
  its environment has been deliberately configured.
- `WORLD_AID_EXTERNAL_CALLS_ENABLED=0` prevents World Developer Portal, World
  Chain RPC/indexer, price-source, issuer-registry, and other non-local network
  calls from this feature. Local deterministic fixtures remain available.
- `WORLD_AID_WLD_TRANSFERS_ENABLED=0` prevents transaction signing and
  submission even when read-only external calls are enabled.

All three default to disabled when absent or malformed. Enabling transfers
requires all applicable outer guards, an environment-pinned chain/token
manifest, healthy signer policy, and an approved deployment record. Disabling
transfers must stop new submissions without stopping receipt monitoring and
reconciliation for transactions already submitted. Unit, API, supervisor, and
deployment-smoke tests must name these contracts and prove that no permissive
fallback exists.

## Canonical Domain Models

Use explicit models rather than adding ambiguous fields to `ProofReceipt`.

### `WalletOwnershipBinding`

- `binding_id`
- `wallet_id`
- `world_chain_address`
- `chain_id`
- `siwe_domain`
- `siwe_nonce_digest`
- `issued_at`
- `verified_at`
- `expires_at`
- `controller_ref`
- `status`

Store the checksum address privately. Public views use a recipient-address
commitment or a deliberately shortened display value.

### `HumanProofBinding`

- `binding_id`
- `wallet_id`
- `authenticated_principal_binding`
- `humanity_binding_commitment`
- `world_action`
- `app_id`
- `rp_id`
- `proof_mode` (`uniqueness` or `session`)
- `credential_policy`
- `verification_environment`
- `nullifier_hmac`
- `nullifier_hmac_key_id`
- `session_id_hmac`
- `session_id_hmac_key_id`
- `verification_result_hash`
- `verified_at`
- `expires_at`
- `revoked_at`
- `status`

After verification and durable replay-key insertion, discard the raw World
response, proof, nullifier, and session identifiers by default. Durable state
is the sanitized verifier-result hash, scoped versioned HMAC replay keys, proof
mode, policy metadata, and timestamps. Retain an encrypted raw payload only
when a documented legal/audit requirement names the purpose, authorized roles,
and short TTL; deletion is verified and auditable.

HMAC rotation must not reset replay history. During a bounded rotation window,
lookup computes pseudonyms with the active and every retained lookup key,
under one database transaction, or atomically rekeys all live rows before the
old key is retired. Every row carries its non-secret key ID. A missing key,
partial migration, duplicate found under any retained key, or ambiguous result
fails closed. Retire old key material only after the longest replay/binding
retention window and a verified migration receipt.

### `IssuerCredentialEnvelope`

- `credential_id`
- `wallet_id`
- `issuer_registry_ref`
- `issuer_key_id`
- `schema_id` and `schema_version`
- `subject_binding_commitment`
- `subject_binding_version`
- `subject_binding_domain`
- `encrypted_claims_ref`
- `issued_at`
- `not_before`
- `expires_at`
- `revocation_registry_ref`
- `credential_commitment`
- `signature`
- `status`

The envelope must support selective claim disclosure to the witness builder,
not to the provider API or logs. Each subject binding is an issuer/domain-scoped
blinded commitment to the same holder-generated stable secret; it is not a
globally reusable public identifier. It is independent of a wallet address,
SIWE key, controller recovery, case, and claim nonce. Reissuance preserves the
hidden-secret relation, and a multi-credential circuit proves equal hidden
subject secret without exposing linkable cross-issuer commitments.

### `ProgramPolicy`

- `policy_id`
- `policy_version`
- `eligibility_uniqueness_scope_id`
- `disbursement_scope_id_immutable`
- `provider_id_immutable`
- `program_id_immutable`
- `benefit_period_id`
- `program_public_alias`
- `canonical_policy_hash`
- `circuit_ref`
- `verifier_key_ref`
- `accepted_issuer_registry_root`
- `accepted_schema_versions`
- `revocation_epoch_policy`
- `benefit_period_definition`
- `amount_rule`
- `currency_quote_rule`
- `effective_at`
- `expires_at`
- `approved_by`
- `status`

Policy publication is a controlled release. An active case retains the exact
policy version; a later edit cannot change an already approved claim.
`disbursement_scope_id_immutable` names the coordinated entitlement namespace
and may span multiple service providers administering the same fund/program.
`eligibility_uniqueness_scope_id` is its separately reviewed one-benefit rule.
Policy revisions and provider handoffs that still represent the same
fund/program/benefit-period entitlement must retain those IDs so a version
bump or different provider cannot create another payout opportunity. A
provider-specific benefit gets a distinct scope only through explicit policy
review. Human-readable aliases are separately versioned display mappings;
renaming one never changes a nullifier or idempotency key.

### `EligibilityProof`

- `proof_id`
- `case_id`
- `proof_system`
- `circuit_ref` and version
- `verifier_key_ref` and hash
- `claim_commitment`
- `policy_hash`
- `issuer_registry_root`
- `revocation_root` and epoch
- `eligibility_scope_nullifier`
- private `subject_binding_proof_ref`
- `proof_bytes_ref`
- `public_inputs`
- `verified_at`
- `expires_at`
- `verification_status`
- `simulation`

`simulation=true`, an unregistered verifier, a stale revocation epoch, an
artifact mismatch, an unsupported circuit, or a verifier exception is always
non-authorizing.

### `EligibilityCase`

- `case_id`
- `private_wallet_ref`
- `provider_id`
- `program_id`
- `benefit_period`
- `policy_id` and version
- `eligibility_uniqueness_scope_id`
- `recipient_address_commitment`
- `human_proof_requirement` (`optional`, `risk_step_up`, or
  `not_permitted_for_decision`)
- `document_consent_grant_id`
- `proof_id`
- `review_state`
- `reviewer_decision`
- `reason_code_private`
- `appeal_state`
- `approved_at`
- `expires_at`

### `PayoutIntent`

- `payout_id`
- `case_id`
- `provider_id`
- `treasury_id`
- `chain_id`
- `token_contract`
- `recipient_subject_binding_scope_commitment`
- `recipient_address`
- `amount_base_units`
- optional private `fiat_quote`, `price_source`, `quoted_at`, and
  `quote_expires_at`
- `claim_commitment`
- `eligibility_scope_nullifier`
- `payout_payload_hash`
- `payout_idempotency_key`
- `approval_set`
- `state`
- `transaction_hash`
- `user_operation_hash`
- `submitted_at`
- `mined_at`
- `confirmed_at`
- `failure_code`

The recipient address is required for transfer execution but remains private
application data. It must not appear in public 211-AI views even though the
transfer itself is visible on the public chain.

### `SubmissionAttempt`

- `attempt_id`
- `payout_id` and `payout_idempotency_key`
- `payout_payload_hash`
- `custody_adapter` and `treasury_account`
- `reserved_nonce`
- `unsigned_envelope_hash`
- `signer_request_id`
- optional encrypted `signed_envelope_ref`
- optional `transaction_hash`, `safe_transaction_hash`, or `user_operation_hash`
- `broadcast_state`
- `ambiguity_reason`
- `created_at`, `submitted_at`, and `resolved_at`

The attempt is durably written before an external signing/broadcast action.
One payout may have linked replacement attempts, but never two independently
authorized payloads or uncoordinated nonces.

### `PayoutReconciliation`

- `payout_id`
- `rpc_chain_id`
- `receipt_status`
- `block_number` and `block_hash`
- `transaction_index`
- `transfer_log_index`
- `observed_token`
- `observed_sender`
- `observed_recipient`
- `observed_amount`
- `confirmations`
- `canonical_block`
- `l2_settlement_state` (`included`, `safe`, or `finalized`)
- optional `l1_settlement_reference`
- `checked_at`
- `reconciliation_status`

## Claim Composition Protocol

Every proof and payout uses a server-issued claim commitment. Use a stable,
test-vectored canonical encoding such as RFC 8785 JSON canonicalization and a
domain-separated cryptographic hash:

```text
domain = "211-ai.worldcoin-human-aid.claim.v1"

claim_intent = {
  schema_version,
  provider_id_immutable,
  program_id_immutable,
  benefit_period_id,
  disbursement_scope_id_immutable,
  eligibility_uniqueness_scope_id,
  policy_id,
  policy_version,
  policy_hash,
  wallet_ownership_binding_hash,
  optional_human_proof_binding_hash,
  recipient_world_chain_address,
  chain_id,
  token_contract,
  amount_base_units,
  payout_expiry,
  server_nonce
}

claim_commitment = H(domain || JCS(claim_intent))
```

These immutable identifiers are opaque internal values. Human-readable
provider/program aliases are versioned mappings and never cryptographic keys.
Do not put the words `homeless`, `homelessness`, a diagnosis, a shelter name,
or an exact benefit category into a public commitment preimage whose contents
are later disclosed.

The same claim commitment must be:

- stored with the SIWE challenge and checked against the verified address;
- included in eligibility ZKP public inputs;
- attached to the provider review;
- included in the payout authorization signed by the provider service; and
- retained in the private reconciliation record.

World ID has a separate, explicit proof-mode contract:

- For a one-time uniqueness action, the server creates a stable
  `humanity_binding_commitment` from the authenticated principal binding, RP,
  action, environment, and a high-entropy server value. That commitment, not a
  mutable payout claim, is the World signal. A successful proof creates one
  reusable, expiring `HumanProofBinding`; later claim corrections reference
  its verification hash. The same RP/action uniqueness proof cannot be
  silently regenerated.
- For an explicitly approved session action, the server may bind a fresh claim
  commitment as signal, but it must verify the expected `session_id` and
  atomically consume each `session_nullifier`. The stable session identifier
  remains private and is never treated as login or eligibility.
- A duplicate uniqueness nullifier may resolve only to the existing binding
  for the same authenticated principal under a documented recovery rule. It
  must never attach personhood to another principal, and an expired/revoked
  binding routes to a new approved action/session ceremony or manual review.

This avoids a contradiction in which correcting an amount or address would
require a fresh claim-bound World uniqueness proof that the replay ledger must
reject.

The commitment alone is not authorization. It is useful only with current
proof, approval, idempotency, expiry, and treasury policy.

### Replay and double-disbursement protection

Derive an eligibility-scope nullifier from a hidden holder secret and only the
reviewed one-benefit scope:

```text
eligibility_scope = {
  disbursement_scope_id_immutable,
  benefit_period_id,
  eligibility_uniqueness_scope_id
}

eligibility_scope_nullifier =
  PRF(holder_secret,
      "211-ai.worldcoin-human-aid.eligibility-scope.v1" ||
      JCS(eligibility_scope))
```

`holder_secret` is a holder-generated, stable credential-subject secret. An
authorized issuer attests an issuer/domain-scoped blinded commitment, and the
eligibility circuit proves that the private credential commitments open to the
same hidden secret. The secret must survive wallet address/key rotation,
controller recovery, a new case, and credential correction or reissuance. It
must not be derived from the current SIWE key, wallet address, case nonce, or
the existing exportable `principal_secrets` map. Neither the secret nor a
globally stable subject commitment is exposed to issuers, providers, public
receipts, or other programs. Recovery or reissuance that cannot preserve the
hidden-subject relation requires issuer/provider duplicate-risk review; it
must not mint a fresh one-benefit identity by default.

The nullifier must remain identical across retries, replacement proofs, and new
case or claim nonces for the same holder and reviewed scope. It deliberately
excludes `claim_commitment`, `server_nonce`, case ID, recipient address, amount,
token, and chain. Otherwise a caller could vary one of those fields and obtain
a second one-per-period payout. A genuinely different reviewed benefit scope
uses a different `eligibility_uniqueness_scope_id`; an ordinary policy-version
edit or display-alias rename for the same benefit scope does not.

This is uniqueness for the same cryptographic holder/credential-subject
binding, not proof that two different credentials or wallets belong to the
same real-world person. When optional World ID is not used, duplicate-person
risk still requires issuer subject-binding rules, provider case management,
and an accessible manual review process. The UI and audit receipt must not
describe the eligibility-scope nullifier as global proof of one human.

Separately compute an immutable hash of the concrete payout payload:

```text
payout_payload = {
  recipient_subject_binding_scope_commitment,
  recipient_world_chain_address,
  amount_base_units,
  token_contract,
  chain_id
}

payout_payload_hash =
  H("211-ai.worldcoin-human-aid.payout-payload.v1" ||
    JCS(payout_payload))
```

The payout idempotency key is stable for the entitlement scope and does not
change when a caller changes payout fields:

```text
payout_idempotency_key =
  H("211-ai.worldcoin-human-aid.payout-idempotency.v1" ||
    eligibility_scope_nullifier ||
    JCS(eligibility_scope))
```

At first payout authorization, atomically store the unique
`payout_idempotency_key` together with `payout_payload_hash`. Every retry,
replacement proof, resumed case, and signer request must look up that same key
and compare the exact payload hash. A mismatch is a hard
`payout_payload_conflict`, not a new idempotency key and not a second payout.
Changing the recipient binding, address, amount, token, or chain requires an
explicit audited correction workflow; it can never be smuggled through a
retry.

The claim commitment remains a fresh proof-binding input that binds the current
SIWE and eligibility-proof ceremony, the optional existing human-proof binding,
and the exact payout terms and expiry. It is not the one-per-period uniqueness
key. A new claim nonce may produce a new claim commitment and eligibility
proof, but it resolves to the same eligibility-scope nullifier and payout
idempotency record. It does not imply that a new World uniqueness proof can be
created. Enforce both unique keys at the database layer and again at the signer
boundary. World ID nullifiers do not replace this application-level
protection.

## End-to-End Protocol

### 1. Start a case and prove wallet ownership

1. An authenticated wallet controller or authorized assisted-enrollment worker
   starts a case.
2. The backend creates the preliminary claim intent and a single-use SIWE
   challenge bound to domain, URI, World Chain ID, address, request ID, issued
   time, and expiry.
3. The client calls `MiniKit.walletAuth()` or the approved non-World-App wallet
   signing flow.
4. The backend verifies the SIWE message and signature, consumes the nonce, and
   records a short-lived `WalletOwnershipBinding`.
5. Changing the address, amount, program, policy, period, token, or chain
   invalidates the binding and creates a new claim commitment. If the
   entitlement scope already has a pinned payout payload, changing address,
   amount, token, or chain also produces `payout_payload_conflict`; it does not
   generate a different one-per-period idempotency key.

### 2. Optionally verify proof-of-human

1. The backend decides whether the program offers optional proof-of-human or a
   separately approved fraud-risk step-up. Essential access never depends on
   this alone.
2. The backend selects the reviewed proof mode for the action. A uniqueness
   action stores a stable humanity-binding signal; a session action may store
   a fresh claim-bound signal plus the expected private session continuity
   record. The request also fixes RP, environment, credential policy, expiry,
   and authenticated-principal reference.
3. The browser receives only the RP context and non-secret configuration, then
   invokes IDKit 4.
4. The browser forwards the result unchanged.
5. The backend calls `/api/v4/verify/{rp_id}` and checks the stored request,
   action, signal, environment, credential policy, result status, expiry, and
   replay state.
6. Before HMAC/indexing, the backend parses each uniqueness nullifier as an
   unsigned 256-bit integer and canonicalizes it to exactly 32 bytes. It then
   atomically consumes the scoped uniqueness or session nullifier, stores
   private versioned HMAC commitments, and emits a sanitized receipt.
7. A valid uniqueness binding is reused across corrected claims until its
   reviewed expiry. The service does not request another uniqueness proof for
   each payout retry or silently attach a duplicate nullifier to a different
   principal.
8. If World ID is unavailable or fails, the user may continue through the
   program's manual/alternate path unless a documented, reviewed risk step-up
   specifically applies.

### 3. Acquire document-derived credentials

1. An approved issuer examines source documents under its own legal and
   professional authority.
2. The issuer emits a signed credential containing only the claims needed by a
   supported policy, a commitment to the holder's stable subject secret, plus
   schema, validity, and revocation metadata.
3. The wallet encrypts the credential and source documents separately. The
   credential does not contain raw document images or unrestricted OCR text.
4. Import verifies the issuer registry, key, schema, subject-binding ceremony,
   validity, scope, and signature before the credential becomes selectable.
5. A provider request uses a scoped, expiring UCAN grant for selected credential
   predicates. It does not grant source-document export.
6. The issuer updates a privacy-preserving revocation registry. Wallets can
   obtain a current witness without disclosing the subject to a public service.
7. Correction or reissuance preserves the subject commitment, records the
   predecessor, and revokes or supersedes the old credential.

Self-uploaded documents are evidence for issuer/manual review, not
self-authenticating credentials.

### 4. Generate and verify eligibility proof

The production circuit proves all of the following:

- the prover knows one or more credentials with valid signatures from keys in
  the accepted issuer-registry root;
- credential schemas and versions are accepted by the exact policy version;
- the hidden claims satisfy the policy predicate;
- credentials are within their validity interval and not revoked at the
  required epoch;
- the credential subject is bound to the issuer-attested stable holder-secret
  commitment, while the current recipient address is separately SIWE-bound;
- the proof is bound to the claim commitment, recipient-address commitment,
  policy, immutable program/period/scope identifiers, chain, token, amount, and
  expiry;
- the stable eligibility-scope nullifier is correctly derived only from the
  hidden holder secret, coordinated disbursement scope, benefit period, and
  reviewed uniqueness rule; and
- the public result is the narrowly stated predicate `eligible = true`.

The circuit must not expose raw claims or distinguish which failing predicate
caused a proof not to verify.

The verifier must:

- load only approved circuit and verifier-key hashes from the registry;
- reject simulated backends and the existing document-profile proof type;
- reject expired policies, credentials, proofs, or revocation epochs;
- verify public inputs exactly against the server's case record;
- atomically reserve or resolve the stable eligibility-scope nullifier;
- attach retries/new proofs for that scope to the existing reservation and
  reject a different payout payload hash;
- return `verified`, `not_verified`, or `manual_review_required`, never an
  autonomous human-facing denial.

Use the existing backend-neutral ZKP boundary. ProveKit/WHIR can be the
off-chain production proof where its reviewed circuit and artifacts fit.
Groth16 or a reviewed recursive wrapper is needed only when a compact/on-chain
verifier is justified. No backend name is sufficient by itself: authorization
requires a registered circuit, pinned artifacts, deterministic test vectors,
and independent verification.

The eligibility circuit is also a supply-chain boundary. Before an autonomous
lane builds it, maintainers must select the backend and review a manifest that
pins toolchain name/version, checksums, licenses, provenance, compiler flags,
container or binary identity, circuit lockfile, public-input schema, and
expected artifact hashes. The approved binary or container must be pre-staged
and the build must run reproducibly without registry or package-network egress.
The circuit itself must constrain issuer signatures, equality of the hidden
credential subject, claim predicates, validity/revocation state, canonical
public inputs, and scope-nullifier derivation. A Groth16 production choice
requires a separately approved ceremony record; developer-generated parameters
cannot satisfy production acceptance.

### 5. Provider review, decision, and appeal

1. The provider sees separate wallet-control, optional-human, credential,
   eligibility-proof, and fraud-risk statuses.
2. A trained reviewer applies program policy, records a structured private
   reason code, and approves, requests information, or sends the case to manual
   review.
3. Adverse decisions require an accountable reviewer, notice appropriate to
   the program, a correction path, and an appeal path. ZKP failure details are
   not presented as proof that the person is ineligible or deceptive.
4. High-value or unusual payouts require a second authorized approver.
5. Approval signs a bounded authorization over the immutable claim commitment,
   payout payload hash, amount, recipient, token, chain, expiry, stable
   eligibility-scope nullifier, and payout idempotency key.

### 6. Submit WLD

The default MVP uses a controlled treasury:

1. The payout service rechecks case approval, proof freshness, address binding,
   benefit-period uniqueness, sanctions/compliance policy where legally
   required, spend cap, approval threshold, and payout expiry.
2. It derives the stable payout idempotency key, loads its previously pinned
   payout payload hash, and rejects any mismatch before signing.
3. It simulates an ERC-20 WLD transfer against the configured World Chain
   environment.
4. In one database transaction, it reserves the treasury account and nonce and
   persists a write-ahead `SubmissionAttempt` containing the payout
   idempotency key, payload hash, canonical unsigned transaction/envelope hash,
   custody adapter, and a stable signer request ID.
5. A Safe, HSM, MPC signer, or reviewed delegated signer signs only that exact
   request. For a raw signed transaction, persist the signed envelope and
   precomputable transaction hash before broadcast. For a Safe or custody API,
   persist its stable Safe transaction hash, user-operation ID, or
   idempotency/request handle before asking it to submit. Raw private keys
   never enter application memory.
6. Broadcast is an outbox action. A timeout or lost response is an
   `submission_ambiguous` state: query the chain, custody adapter, account
   nonce, known hashes, and signer request before any retry. Never allocate a
   new nonce or create a second signed envelope merely because the first call
   returned no response.
7. A separate watcher observes every attempt and the expected `Transfer`
   event, then links replacement hashes to the original attempt.

An optional interactive provider flow may use MiniKit `sendTransaction`, with
Developer Portal allowlisting and backend `userOpHash` resolution. It must
produce the same internal authorization and reconciliation records.
`MiniKit.pay()` must not be used for outbound aid because it asks the current
user to pay.

### 7. Reconcile and notify

The watcher verifies:

- chain ID is exactly the configured environment;
- receipt status is successful;
- the custody envelope is the approved shape: direct transactions target WLD;
  Safe/module executions decode to the approved inner WLD call and authorized
  Safe; account-abstraction operations resolve through the expected entry
  point/account to the same call;
- the WLD contract address matches configuration;
- a `Transfer` event has the approved treasury sender, recipient, amount, and
  unique log index;
- the L2 block is canonical and has reached the configured operational
  confirmation depth;
- World Chain is an OP Stack L2 settling to Ethereum, so `included`, `safe`,
  `finalized`, and any program-required L1 settlement checkpoint remain
  distinct states; a plain block-count threshold is not called finality;
- the unique payout idempotency record still contains this exact payout payload
  hash; and
- no other payout has consumed the stable eligibility-scope nullifier.

Only then transition to the policy's named settlement state. Recipient UX may
show an earlier `included` or `safe` status, but accounting uses the configured
`finalized`/L1-settlement rule. A reorg or safe/finalized regression returns the
payout to a non-terminal reconciliation state. A replacement transaction is
linked to the same payout, attempt, and nonce; it does not create a second
authorization.

The recipient gets a private receipt with amount, token, network, transaction
hash, date, and support/appeal information. Public impact data is aggregated
and thresholded; it must not expose the recipient address-to-wallet mapping or
eligibility category.

## State Machines

### Case state

```text
draft
  -> awaiting_wallet_ownership
  -> awaiting_credentials
  -> awaiting_proof
  -> proof_verified
  -> review_required
  -> approved
```

Additional controlled states:

- `manual_review`
- `information_requested`
- `appealed`
- `appeal_resolved`
- `expired`
- `cancelled`
- `revoked`
- `closed_not_approved` only after an authorized reviewer decision

Proof generation or verification failure transitions to `manual_review`; it
does not transition directly to `closed_not_approved`.

### Payout state

```text
draft
  -> authorized
  -> submitting
  -> submitted
  -> mined
  -> confirming
  -> confirmed
```

Additional controlled states:

- `simulation_failed`
- `submission_failed`
- `payout_payload_conflict`
- `replaced`
- `reorged`
- `reconciliation_failed`
- `expired`
- `cancelled`
- `reversed` only when an actual compensating transaction is confirmed

Every transition is monotonic where possible, compare-and-swap protected,
idempotent, timestamped, and attributed to an actor. `failed` is not a terminal
catch-all: retryable RPC failure, rejected signature, reverted execution,
missing event, and policy rejection need separate codes.

## API Surface

Use versioned request/response models and deny unknown security-critical
fields. Candidate endpoints:

### Case lifecycle

- `POST /world-aid/cases`
- `GET /world-aid/cases/{case_id}`
- `POST /world-aid/cases/{case_id}/cancel`
- `GET /world-aid/cases/{case_id}/timeline`

Case creation resolves immutable provider, program, benefit-period, and
uniqueness-scope IDs from server policy. The client cannot mint or rename an
entitlement scope.

### Wallet ownership

- `POST /world-aid/siwe/challenges`
- `POST /world-aid/siwe/verify`
- `GET /world-aid/cases/{case_id}/wallet-ownership`

### Optional World ID

- `POST /world-aid/cases/{case_id}/world-id/rp-signatures`
- `POST /world-aid/cases/{case_id}/world-id/verifications`
- `DELETE /world-aid/cases/{case_id}/world-id/binding`

The backend derives proof mode, signal, action, RP, and principal binding from
stored server policy; it never accepts the client's desired expected signal or
session as authoritative.

### Credentials and eligibility

- `POST /world-aid/issuers/enrollment-requests`
- `POST /world-aid/issuers/{issuer_id}/keys` through a human approval workflow
- `POST /world-aid/cases/{case_id}/credential-issuance-consents`
- `POST /world-aid/cases/{case_id}/credential-issuance-requests`
- `POST /world-aid/wallets/{wallet_id}/credentials/import`
- `GET /world-aid/wallets/{wallet_id}/credentials/{credential_id}`
- `POST /world-aid/wallets/{wallet_id}/credentials/{credential_id}/refresh-revocation-witness`
- `POST /world-aid/wallets/{wallet_id}/credentials/{credential_id}/corrections`
- `POST /world-aid/cases/{case_id}/credential-grants`
- `POST /world-aid/cases/{case_id}/proof-requests`
- `POST /world-aid/cases/{case_id}/proofs`
- `GET /world-aid/cases/{case_id}/proof-status`
- `POST /world-aid/cases/{case_id}/manual-evidence`

### Provider decision and appeal

- `POST /world-aid/cases/{case_id}/reviews`
- `POST /world-aid/cases/{case_id}/approvals`
- `POST /world-aid/cases/{case_id}/appeals`
- `POST /world-aid/cases/{case_id}/appeal-decisions`

### Payout and reconciliation

- `POST /world-aid/cases/{case_id}/payout-intents`
- `POST /world-aid/payouts/{payout_id}/approvals`
- `POST /world-aid/payouts/{payout_id}/submit`
- `GET /world-aid/payouts/{payout_id}`
- `GET /world-aid/payouts/{payout_id}/receipt`
- `POST /world-aid/payouts/{payout_id}/reconcile` for privileged repair only

Submission returns an accepted operation with a status URL; it does not report
success before chain confirmation. The public API never accepts a transaction
hash as proof of payment without independent reconciliation.

Every route derives the authenticated principal and tenant from server
middleware. No route accepts `actor_did`, issuer role, provider role, wallet
ownership, or reviewer authority as a caller-asserted authorization fact.

## Privacy and Data Placement

### Encrypted/private only

- raw documents, OCR, extracted fields, and document CIDs;
- exact homelessness, housing, income, disability, immigration, medical, and
  benefit facts;
- credential subject identifiers and wallet-to-person mapping;
- World ID raw payloads, proofs, nullifiers, session IDs, and verifier response;
- full recipient address in application views;
- issuer/reviewer notes and adverse-decision reasons;
- Fiat/WLD quote rationale where it could reveal the benefit;
- ZKP witnesses and intermediate prover files.

### Sanitized wallet receipt

- proof/receipt type and schema version;
- opaque policy alias/version and circuit reference;
- proof-system/verifier artifact hash;
- claim commitment;
- verification status and time;
- expiry and revocation epoch;
- optional-human status as a distinct field;
- provider approval status as a distinct field;
- transaction hash and settlement status for the private recipient/provider
  view.

### Public chain

For the direct-transfer MVP, only the unavoidable ERC-20 transfer data is
public: treasury address, recipient address, token, amount, transaction, block,
and event. Do not add memo text, document hashes, a case ID, a wallet ID,
homelessness status, benefit reason, World nullifier, or a reversible
application identifier.

This is data minimization, not transfer privacy. A recognizable aid/provider
treasury, recipient address, amount, and timing are permanently graph-linkable,
and analytics may infer that an address received aid. ZK does not hide this
transfer graph. Consent copy must explain that residual risk, warn against
address reuse, avoid publishing explorer links by default, and offer a
reviewed non-crypto or privacy-preserving partner disbursement path when the
risk is unacceptable. Do not advertise the direct ERC-20 path as anonymous.

An optional future authorization contract may emit only a randomized,
domain-separated claim commitment after privacy review. An opaque hash can
still enable correlation or dictionary attacks if its preimage is predictable;
use high-entropy nonces and do not publish its sensitive preimage.

### IPFS

Public IPFS is not private because content encryption does not hide access
patterns or all metadata. Raw documents and credentials require encryption,
capability-gated keys, retention limits, and non-public discovery. A CID must
not be placed on-chain merely to claim auditability. Prefer a private,
salted commitment and an encrypted, access-controlled audit bundle.

## Policy, Currency, and Accounting

Each program must explicitly decide whether the award is:

- a fixed quantity of WLD;
- a fiat-denominated amount converted to WLD at approval or submission; or
- a stablecoin amount on World Chain.

For fiat-quoted WLD, pin the approved price source, quote timestamp, expiry,
rounding method, slippage/tolerance, and maximum WLD. Store token amounts as
integer base units; never use binary floating point. Present WLD volatility,
network finality, and recipient control risks in plain language.

Before a production transfer, counsel and program owners must review applicable
money-transmission, custody, sanctions, tax/reporting, consumer protection,
benefit interaction, geography, privacy, biometric, accessibility, and
record-retention obligations. This plan is technical architecture, not legal
advice.

## Authorization and Key Management

- Provider staff authenticate independently of World ID and receive explicit
  tenant/program roles.
- A provider World ID proof may be an optional step-up but cannot grant a role.
- Delegations have provider, program, action, amount, time, and environment
  scopes.
- Payouts use per-program and per-period caps, velocity limits, and dual
  approval above a reviewed threshold.
- Treasury policy reserves both WLD and native gas/fee budget, binds account
  nonce and a replacement ceiling, alerts before gas exhaustion, and never
  frees the recipient's entitlement merely because the treasury lacks gas.
- Program UX/support explains whether the recipient needs native gas to use,
  transfer, or off-ramp WLD and offers an accessible alternative when the
  wallet, gas, volatility, exchange, or off-ramp path is unsuitable.
- Production keys live in Safe/HSM/MPC custody. Signing policies accept a
  canonical transaction digest, not arbitrary calldata.
- Developer Portal RP signing keys, API keys, World nullifier HMAC keys,
  credential issuer keys, ZKP proving keys, verifier manifests, database
  encryption keys, and treasury signers have separate ownership and rotation.
- Rotation preserves verifier history for existing receipts but prevents new
  claims with revoked keys.
- Break-glass access is time-limited, multi-party approved, and tested in an
  incident exercise.

## Threat Model and Required Controls

| Threat | Required controls |
| --- | --- |
| Client substitutes action or signal | Server-stored World request; RP signature; exact post-verification comparison; one-time expiry |
| World proof replay | Canonical uint256 parsing; consumed uniqueness/session nullifier; action/RP/environment/proof-mode scope; stable humanity binding for uniqueness or reviewed claim-bound session signal |
| World ID used as login | Separate SIWE ceremony and session; no nullifier lookup login |
| Smart-account signature accepted incorrectly | Official or parity-reviewed SIWE verifier with EIP-1271 and pinned World Chain client; EOA and contract-wallet vectors |
| Address substitution | SIWE-bound address in immutable claim commitment and ZKP public inputs |
| Stolen/shared wallet | Fresh SIWE, optional user-presence/risk review, change-of-address invalidation, manual recovery |
| Fake/self-issued document | Authorized issuer registry, signature verification, schema allowlist, audit |
| Revoked or stale credential | Revocation-root epoch and validity constraints inside proof; freshness gate |
| Simulated proof authorizes funds | Production environment rejects `simulation`, simulated backend IDs, and `document_privacy_profile` proof type |
| Proof artifact substitution | Pinned circuit/verifier hashes, signed manifest, registry status, reproducible vectors |
| Cross-program or cross-issuer correlation | Domain-separated disbursement-scope/period/rule nullifiers; issuer/domain-blinded subject commitments; equal hidden subject proved inside ZK; private World identifiers; no public case IDs |
| New nonce, alias, wallet key, provider, or case bypasses one-per-period rule | Stable hidden holder secret and immutable coordinated disbursement-scope/period/rule IDs; nullifier excludes provider, claim/case nonce, display aliases, wallet address, and payout fields |
| Changed recipient, address, amount, token, or chain creates a new payout key | Stable scope-derived idempotency key; immutable payout payload hash; mismatched retry rejected before signing |
| Duplicate payout/race | Database uniqueness, compare-and-swap transitions, signer idempotency ledger, stable scope-nullifier reservation |
| Provider insider fraud | RBAC, dual approval, spend/velocity caps, immutable audit, treasury separation |
| Treasury compromise | Safe/HSM/MPC, least privilege, allowlisted WLD/token/chain/recipient transaction shape, pause switch |
| RPC lies or is unavailable | Multiple independent providers, chain-ID/code checks, receipt and event reconciliation |
| Reorg causes false completion | Operational depth plus canonical/safe/finalized and required L1-settlement checks, explicit reorg state, and re-reconciliation |
| Transaction hash spoofing | Never trust client hash; fetch receipt; validate event sender/recipient/token/amount |
| Public deanonymization | No sensitive memo/event, private mapping, retention/deletion, aggregate thresholds |
| Plaintext snapshots or overbroad status leak secrets | Development-only local repository guard; encrypted transactional store; KMS envelope keys; authenticated projections; migration and secret-scan gates |
| Supervisor bypasses policy | Objective acceptance tests, protected safety tests, no production credentials or signer access |
| Automated adverse decision | Manual-review default, accountable reviewer, notice, correction, appeal |

## Accessibility, Manual Fallback, and Appeals

Every program must publish and test:

- assisted enrollment that does not require personal device ownership;
- a non-World-ID route with comparable service access;
- a non-biometric/manual route;
- support for limited connectivity and interrupted proof generation;
- screen-reader, keyboard, contrast, cognitive-load, language, and plain-copy
  requirements;
- safe shared-device behavior and automatic sensitive-data clearing;
- a way to correct issuer data or replace an expired/revoked credential;
- a human review channel when a proof cannot be generated or verified;
- an appeal flow with status, deadlines, reviewer attribution, and notification;
- a non-crypto or custodial-partner alternative where receiving WLD would be
  unsafe, inaccessible, or legally inappropriate.

Do not call a person "unverified" as a synonym for ineligible. UI copy must say
which technical step is incomplete and how to continue.

## Testing Strategy

### Unit and property tests

- RFC 8785 claim canonicalization and cross-language golden vectors.
- Address checksum/normalization without changing signed SIWE meaning.
- SIWE nonce uniqueness, expiration, domain/URI/chain mismatch, EOA and
  EIP-1271 verification, and replay.
- World action/proof-mode/signal/RP/environment/credential mismatch and replay.
- World nullifier parsing rejects malformed, signed, overflow, and
  non-canonical aliases before canonical 32-byte HMAC input.
- Uniqueness actions reuse only the original authenticated
  `HumanProofBinding`; corrected claims do not request a fresh uniqueness proof.
  Session actions preserve `session_id` continuity and reject a repeated
  `session_nullifier`.
- HMAC rotation performs dual-key lookup or atomic rekey and cannot make an old
  uniqueness/session replay acceptable.
- Eligibility-scope nullifier stability across retries, replacement proofs,
  fresh case/claim/server nonces, and changes to recipient or amount.
- Eligibility-scope nullifier stability across different providers that share
  one coordinated entitlement, and separation across different holders,
  disbursement scopes, benefit periods, and reviewed uniqueness rules.
- Policy-version updates for the same reviewed benefit scope retain the same
  uniqueness scope and nullifier; provider/program alias renames do the same.
- Subject-secret continuity survives wallet address/key rotation, controller
  recovery, correction, and credential reissuance; a changed subject
  commitment routes to duplicate-risk review.
- Credential signature, schema, validity, revocation, and issuer-root checks.
- Issuer enrollment, scoped issuance consent, subject binding, credential
  import, revocation-witness refresh, correction, and supersession.
- Policy canonicalization and deterministic circuit public inputs.
- Amount base-unit arithmetic, fiat quote expiry, and rounding boundaries.
- Payout idempotency under concurrent approval/submission.
- A changed recipient binding, address, amount, token, or chain changes
  `payout_payload_hash` but never `payout_idempotency_key`, and is rejected as
  `payout_payload_conflict` on retry rather than creating a new payout.
- A fresh claim commitment for an otherwise identical retry remains
  proof-bound while resolving to the original scope nullifier, payload hash,
  and idempotency record.
- State-machine transition and retry invariants.
- Receipt/log reconciliation, replacement, and reorg properties.

### ZKP conformance tests

- Positive vectors for every supported policy/circuit version.
- Boundary-value and negative witnesses for each predicate.
- Invalid issuer, revoked credential, stale root, wrong subject, wrong claim,
  wrong amount/address/chain/token, malformed proof, and artifact mismatch.
- Cross-backend verification where the circuit family supports it.
- Explicit production rejection of simulated ZKP, mock verifier,
  `document_privacy_profile`, and test artifacts.
- Witness redaction tests for logs, errors, caches, IPFS, QR, export, metrics,
  traces, and crash dumps.
- Server-side prover tests for least-privilege field selection, memory/temp-file
  hygiene, disabled core dumps/swap policy, cleanup on success/failure/timeout,
  worker isolation, and consent revocation.

### API and integration tests

- Full wallet-auth -> optional World ID -> credential grant -> proof -> review
  -> approval -> payout -> confirmation flow.
- The same flow without World ID.
- Manual evidence and assisted-enrollment flow.
- Provider tenant isolation and authorization boundaries.
- Duplicate requests, stale sessions, expired claims, and concurrent workers.
- Developer Portal/RPC timeouts, rate limits, malformed responses, and failover.
- PostgreSQL production-store migrations, encryption/KMS boundary, unique
  indexes, transactional outbox, real-database concurrency/crash recovery,
  backup/restore, and rejection of the plaintext local repository and
  non-PostgreSQL substitutes outside development.
- Sepolia transfers of the reviewed test token, with independently asserted
  receipt/event fields and no assumption that the mainnet WLD address applies.
- MiniKit `sendTransaction` remains an injected fixture in Sepolia tests; no
  test assumes World App supports a testnet transaction.
- Reorg and dropped/replaced transaction fixtures.

### UI and accessibility tests

- Distinct labels for all five assurance domains.
- No overclaiming from proof-of-human or proof verification.
- Human-review, correction, appeal, no-device, no-World-App, no-connectivity,
  and declined-consent paths.
- Desktop/mobile Playwright flows and automated accessibility checks.
- No raw document, nullifier, session ID, private address mapping, or sensitive
  reason in browser logs, analytics, QR, export, or public screens.
- Clear consent copy for public transfer-graph linkability, address-reuse risk,
  and the alternative disbursement path; no claim that ZK makes ERC-20
  transfers anonymous.

### Security tests

- RP/signing-key and treasury-secret leak scanning.
- API fuzzing and strict-schema tests.
- Cross-tenant IDOR, replay, confused-deputy, CSRF, SSRF, and webhook spoofing.
- Transaction calldata allowlist bypass and signer policy tests.
- Dependency/SBOM review for IDKit, MiniKit, World Chain, SIWE, and ZKP code.
- External review of production eligibility circuits and any payout contract.

## Observability and Operations

Metrics should use opaque, rotating service identifiers rather than addresses,
case IDs, World nullifiers, or program-sensitive labels.

Required operational views:

- SIWE and World verification success/failure by coarse error class;
- optional World ID bypass/manual-path availability;
- proof generation/verification duration and registered-artifact failures;
- cases awaiting human review or appeal without exposing reasons;
- payout authorization, queue age, submission, mined, confirmation, retry,
  reorg, and reconciliation counts;
- treasury balance, per-program caps, signer health, RPC divergence, and
  provider latency;
- duplicate/nullifier/idempotency conflicts;
- v3 compatibility traffic trending to zero before 2027-03-31.

Required alerts:

- any attempted simulated-proof authorization;
- chain ID, token code, or verifier-artifact mismatch;
- unexpected token/recipient/amount or missing `Transfer` event;
- repeated duplicate payout attempts;
- treasury/signing-policy failure or anomalous velocity;
- confirmation regression/reorg above threshold;
- World API or RPC provider outage with no healthy fallback;
- private-field detection in logs or public payloads.

The runbook must cover pause, resume, replay-safe retry, signer/RP/API-key
rotation, stuck/replaced transactions, reorgs, issuer/verifier revocation,
incorrect approval, data incident, recipient support, appeals, and accounting
reconciliation.

## Rollout Plan and Gates

### Phase 0: policy and architecture

- Approve assurance-domain separation, data classification, retention,
  accessibility, manual route, appeals, and program decision ownership.
- Define the first issuer, credential schema, policy, benefit period, payout
  unit, and accounting rule.
- Threat-model the existing code and approve the objective heap.

Exit gate: security, privacy, program, accessibility, treasury, and legal owners
accept the written invariants. No funds move.

### Phase 1: deterministic local implementation

- Implement canonical models, commitments, SIWE, expected-signal enforcement,
  issuer/policy registries, a minimal real eligibility circuit, state machines,
  and fake chain/signer adapters.
- Implement the pinned EIP-1271-capable SIWE verification boundary, issuer
  enrollment/issuance/import/correction lifecycle, and encrypted transactional
  PostgreSQL production store before integrating their APIs.
- Run the G002-only bootstrap audit first. Humans then review and pre-stage the
  exact npm tarballs/lock, native ZKP toolchain, Python wheelhouse, and
  PostgreSQL image or binary. G037 through G040 turn those external choices
  into deterministic offline evidence before G006, G012, or G033 can run.
- Prove the checksum-pinned eligibility-circuit toolchain's locked smoke build
  is reproducible and offline before assigning the circuit implementation
  lane.
- Migrate only synthetic fixtures first and prove that staging/production
  reject plaintext local-wallet repositories and raw durable-model status
  projections.
- Implement and property-test the stable eligibility-scope nullifier,
  scope-derived payout idempotency key, and immutable payout payload hash,
  including conflict rejection across new cases and claim nonces.
- Add all negative and no-leak tests.
- Generate the supervisor runtime taskboard from the reviewed objective heap.

Exit gate: test suite proves simulated/profile proofs cannot authorize payout
and all adverse proof outcomes route to manual review.

### Phase 2: World Chain Sepolia

- Configure a separate World Developer Portal staging app/RP/actions.
- Use only synthetic credentials and test wallets.
- Exercise the direct treasury path with a reviewed test ERC-20 standing in for
  WLD, or with a separately verified official
  testnet WLD deployment if one exists at pilot time. Never substitute the
  mainnet WLD address. The MiniKit provider transaction path remains
  fixture-only because current Mini App documentation does not support testnet
  transaction testing. Cover direct-treasury receipt/event checks, retries,
  replacement, reorg fixtures, and accounting export.
- Complete accessibility and assisted-enrollment rehearsals.

Exit gate: zero unexplained ledger differences, no sensitive public data, and a
successful incident/pause/recovery exercise.

### Phase 3: closed mainnet pilot

- Use a Safe/HSM/MPC treasury with a deliberately small balance.
- Limit providers, programs, recipients, daily value, and geographic scope.
- Require dual approval for every transaction.
- Reconcile automatically and manually each day.
- Provide staffed support, correction, fallback, and appeal paths.
- If the optional MiniKit provider path is still desired and official support
  remains mainnet-only, run it only as a separate human-approved, allowlisted,
  minimum-value canary after its fixture suite, dependency/SBOM review, and
  transaction-shape review pass. It is not a Sepolia gate or MVP dependency.

Exit gate: independent security/circuit review, privacy/legal signoff, treasury
owner approval, sustained reconciliation, and documented participant feedback.

### Phase 4: canary expansion

- Increase caps and provider count gradually.
- Monitor proof failures, manual-path outcomes, appeals, World/RPC reliability,
  volatility effects, support load, and demographic/accessibility disparities.
- Stop or roll back on reconciliation drift, privacy leakage, inaccessible
  fallback, anomalous denial patterns, or treasury control failure.

### Phase 5: optional on-chain authorization

Only after the off-chain flow is stable, decide whether atomic proof-and-payout
enforcement materially reduces risk. If it does:

- specify minimal contract semantics and upgrade/pause governance;
- avoid sensitive events and reusable identifiers;
- implement consumed-nullifier/idempotency protection;
- use the revalidated WorldIDVerifier v4 only if contract-level World proof is
  actually required;
- complete independent audits and public testnet review; and
- preserve the provider's accountable decision and manual route.

This phase is not an MVP dependency.

## Supervisor Execution Model

The agent supervisor may autonomously implement bounded objectives, tests,
documentation, and non-production fixtures. It must not:

- create or rotate production Developer Portal credentials;
- access raw production documents or ZKP witnesses;
- make an eligibility or appeal decision;
- deploy an unaudited production contract;
- sign, submit, replace, or reverse a production WLD transaction;
- weaken a no-leak, manual-review, or simulated-proof rejection test; or
- mark a governance/signoff objective complete without the named human owner.

Every generated task must contain:

- stable objective ID and track;
- dependencies and conflict-safe predicted files;
- explicit outputs;
- commands or evidence for validation;
- acceptance criteria tied to this plan;
- whether human governance approval is required; and
- a rollback or fail-closed expectation for security-critical changes.

The supervisor should parallelize independent UI, model, documentation, ZKP,
and chain-fixture work, but serialize changes to canonical schemas, policy
hashing, signer interfaces, and migration files. Generated tasks remain
`blocked` when a production credential, treasury signer, legal decision,
external audit, or named-owner signoff is required.

The source heap currently contains 38 schedulable implementation goals:
`WORLDCOIN-G001` through `WORLDCOIN-G034` plus the four offline-bootstrap
objectives `WORLDCOIN-G037` through `WORLDCOIN-G040`. Two goals are deliberately
terminal human gates: `WORLDCOIN-G035` for an externally authorized Sepolia
evidence record and `WORLDCOIN-G036` for the production canary. The supervisor
must not materialize, claim, or infer completion of either blocked goal.

The first executable profile is mechanically fenced to G002. Wider immutable
profiles may be derived only after reviewing successful predecessor receipts.
G037 prepares a non-executing SIWE lock proposal; G038 verifies the
human-approved npm set offline; G039 verifies the human-approved native ZKP
toolchain; and G040 verifies the human-approved Python/PostgreSQL runtime. A
missing approval or pre-staged artifact blocks its lane and all dependent work
without being converted into an agent-generated substitute.

## Definition of Done

The integration is complete only when:

1. wallet ownership is independently verified and bound to every payout;
2. EOA and World smart-account ownership use a pinned, EIP-1271-capable SIWE
   verifier with single-use server challenges;
3. World ID 4 is current, optional, correctly proof-mode/signal-bound,
   replay-protected, and accurately labeled;
4. issuer enrollment, scoped issuance consent, stable subject binding,
   credential import, revocation refresh, correction, and reissuance work
   without exposing source documents;
5. a real registered eligibility circuit verifies authorized, current,
   non-revoked credential predicates without leaking source claims;
6. simulated and document-profile proofs are mechanically incapable of
   authorizing money;
7. provider roles, review, reason, appeal, limits, and dual control are audited;
8. the treasury signer accepts only the exact reviewed transaction shape;
9. every payout uses a stable hidden credential-subject secret plus immutable
   coordinated disbursement-scope/period/rule identifiers to derive a nullifier
   that is stable across cases and claim nonces, a scope-derived idempotency key,
   and an immutable payout payload hash that rejects changed-payload retries;
10. every payout is independently reconciled through a canonical receipt and WLD
   `Transfer` event to the required finality;
11. reorg, retry, replacement, revocation, pause, and incident paths are tested;
12. PostgreSQL-backed encrypted transactional storage, versioned migrations,
    unique indexes, atomic outbox, real-database concurrency/crash tests,
    restore, retention, and minimum-necessary API projections pass their gates;
13. raw documents, homelessness status, World identifiers, exact eligibility
   reasons, and private mappings do not appear on-chain or in public artifacts;
14. no-device, no-World-ID, accessibility, manual evidence, and appeal paths
    work end to end;
15. Sepolia and capped mainnet evidence meet the rollout gates; and
16. the objective heap, generated supervisor board, operating runbook, tests,
    deployment manifest, and signoff evidence agree on the same policy and
    artifact versions.

## Related Repository Documents

- `docs/planning/WORLD_ID_IDKIT_WALLET_IMPLEMENTATION_PLAN.md`
- `docs/planning/WORLD_ID_IDKIT_WALLET_TODO.md`
- `docs/specs/WORLD_ID_IDKIT_AGENT_COORDINATION.md`
- `docs/specs/WALLET_PROOF_VERIFIER_CONTRACT.md`
- `docs/planning/PROVEKIT_ZKP_LOGIC_IMPLEMENTATION_PLAN.md`
- `docs/planning/PROVEKIT_ZKP_LOGIC_TODO.md`
- `docs/planning/WORLDCOIN_HUMAN_AID_OBJECTIVE_HEAP.md`
- `docs/planning/WORLDCOIN_HUMAN_AID_AGENT_SUPERVISOR_RUNBOOK.md`
- `data/worldcoin_human_aid/agent_supervisor/WORLDCOIN_HUMAN_AID_TODO.md`

## Official External References

- World ID integration:
  `https://docs.world.org/world-id/idkit/integrate`
- RP signatures:
  `https://docs.world.org/world-id/idkit/signatures`
- Developer Portal proof verification:
  `https://docs.world.org/api-reference/developer-portal/verify`
- World ID 4 migration:
  `https://docs.world.org/world-id/4-0-migration`
- World ID credentials:
  `https://docs.world.org/world-id/idkit/credentials`
- MiniKit wallet authentication:
  `https://docs.world.org/mini-apps/commands/wallet-auth`
- MiniKit payments:
  `https://docs.world.org/mini-apps/commands/pay`
- MiniKit transactions:
  `https://docs.world.org/mini-apps/commands/send-transaction`
- MiniKit transaction lookup:
  `https://docs.world.org/api-reference/developer-portal/get-transaction`
- MiniKit user-operation lookup:
  `https://docs.world.org/api-reference/developer-portal/get-user-operation`
- World Chain network information:
  `https://docs.world.org/world-chain/quick-start/info`
- World Chain OP Stack and settlement features:
  `https://docs.world.org/world-chain/quick-start/features`
- World Chain useful contracts:
  `https://docs.world.org/world-chain/reference/useful-contracts`
- World Chain data providers:
  `https://docs.world.org/world-chain/providers/data`
- On-chain World ID verification:
  `https://docs.world.org/world-id/idkit/onchain-verification`
- World Mini App policy:
  `https://docs.world.org/mini-apps/guidelines/policy`
