# Wallet Retention Policy

Status: baseline policy template; target deployment signoff required.

Date: 2026-05-05

## Purpose

This policy defines how the 211-AI data wallet should retain, delete, and audit
wallet data across `ipfs_datasets_py.wallet`, `wallet_interface.api`, storage
replicas, proof systems, analytics, exports, and operations logs.

The policy is intentionally conservative because wallet records can include
documents, precise location, benefits information, identity facts, derived
eligibility claims, and analytics contributions. A production deployment must
map this policy to its datastore lifecycle rules, storage-provider contracts,
backup schedules, and legal obligations before processing live user data.

## Scope

Covered data includes:

- Wallet manifests, encrypted data records, encrypted record versions, encrypted
  metadata, and key-wrap descriptors.
- Local, IPFS, S3, Filecoin-style, and replicated encrypted blob storage.
- UCAN grants, invocations, revocations, threshold approvals, and access
  requests.
- Proof requests, proof receipts, public inputs, verifier metadata, and proof
  contract reports.
- Analytics templates, consents, contributions, nullifiers, private aggregate
  results, query-budget ledgers, and review records.
- Audit hash-chain events, ops-health reports, scheduled worker JSONL output,
  alert webhook payloads, and incident-response exports.
- Temporary extraction files, generated redacted artifacts, export bundles,
  import descriptors, and UI/browser caches.

## Principles

- Retain plaintext only inside the wallet service boundary and only for the
  duration of the authorized operation.
- Store wallet payloads and sensitive metadata encrypted at rest, including
  replicas and backups.
- Prefer deletion or key rotation when retention is not required for user
  recovery, security audit, legal hold, or active service delivery.
- Preserve enough audit history to explain access, revocation, proof creation,
  analytics release, and incident response decisions.
- Do not use IPFS CIDs, S3 object names, Filecoin deal IDs, filenames, or hidden
  URLs as privacy controls.
- Record retention choices in the target production signoff packet before
  launch.

## Default Retention Schedule

These values are defaults for first production planning. The deployment owner
must replace or confirm them during target-environment signoff.

| Data Class | Default Retention | Required Control |
| --- | --- | --- |
| Current wallet manifest and encrypted record payloads | Until user deletion, account closure, legal retention requirement, or explicit service-delivery need ends | Durable repository lifecycle and encrypted blob-store lifecycle must match the approved policy. |
| Superseded encrypted record versions | Retain with the wallet by default; optionally expire after the approved recovery window | Version history deletion must remove manifests, blob references, and key wraps where supported. |
| Deleted record tombstones | Minimum audit-retention period approved by legal/privacy reviewers | Tombstones should identify the deleted record ID and deletion time without retaining plaintext. |
| UCAN grants, invocations, revocations, access requests, and threshold approvals | Minimum audit-retention period approved by legal/privacy reviewers | Retain enough detail to prove who authorized what, when, for what purpose, and when it was revoked. |
| Key-wrap descriptors for active versions | Same as the encrypted record version | Revoke stale wraps and rotate keys after device loss, grant compromise, or emergency revoke. |
| Proof receipts and public inputs | Same as the grant, consent, or record audit trail that required the proof | Public inputs must not contain raw witness values; witness material is not retained. |
| Proof witnesses and temporary proof inputs | No retention after proof generation or verification | Delete immediately after the operation; periodic temp cleanup should enforce a maximum age of 24 hours. |
| Analytics templates and reviewer approvals | While the template is active plus the approved audit-retention period | Review records must include cohort threshold, epsilon budget, allowed dimensions, and reviewer identity. |
| Analytics consents, withdrawals, contributions, nullifiers, and query-budget ledgers | Consent lifetime plus the approved audit-retention period | Withdrawals stop future contribution use but preserve the audit trail needed to explain prior releases. |
| Released aggregate results | Approved study retention period | Store privacy metadata, suppression decisions, budget use, and release audit events with the result. |
| Wallet audit hash-chain events | Approved audit-retention period | Audit deletion or archival must preserve chain integrity for the retained window. |
| Ops-health reports and scheduled worker JSONL | 90 days by default, longer during incidents or legal hold | Reports must not contain secret values or plaintext wallet data. |
| Alert webhook delivery payloads | 90 days by default, or incident-retention period when attached to an incident | Alert payloads should contain status metadata only. |
| Incident-response exports | Incident-retention period approved by security/legal reviewers | Exports must be encrypted and access-limited. |
| Redacted derived artifacts | Same as the source record unless a shorter derived-artifact policy is approved | Derived facts, summaries, embeddings, and GraphRAG profiles are sensitive and stay encrypted. |
| Encrypted export bundles | Owner-controlled while stored by the wallet; recipient copies follow recipient agreement and grant terms | Revocation stops future access but cannot claw back already downloaded plaintext. |
| Import descriptors | Same as imported wallet descriptor policy | Import must validate bundle hash/schema and store descriptors encrypted. |
| UI/browser cache and local session state | Session only unless explicitly approved | Do not store raw wallet plaintext, verifier secrets, or long-lived invocation tokens in browser storage. |
| Backups and replicas | Same retention as source data, with backup purge SLA recorded in signoff | S3 lifecycle, local backup rotation, IPFS pinning, and Filecoin deal expiration must be aligned. |

## Deletion Workflow

When a user deletes a record, closes a wallet, withdraws an analytics consent, or
an operator executes approved incident cleanup:

1. Verify the actor has the required wallet authority and threshold approvals.
2. Revoke active grants, descendant grants, invocation receipts, and delegated
   key wraps that depend on the deleted or withdrawn data.
3. Rotate affected record keys when revocation or compromise requires it.
4. Write an audit event or tombstone that records the action without retaining
   plaintext.
5. Remove wallet manifest references and encrypted blobs from the durable
   repository and configured replica stores where the providers support
   deletion.
6. Unpin IPFS content and expire Filecoin deals according to provider controls.
   Operators must document that content-addressed networks cannot guarantee
   deletion from every node that may have cached a block.
7. Track backup and replica purge completion under the approved purge SLA.
8. Run `GET /ops/health?verify_storage=true` and, when required, the production
   readiness command before closing the deletion ticket.

## Analytics Retention

Each analytics template must carry a retention decision before approval:

- Approved derived fields and dimensions.
- Minimum cohort size and epsilon budget.
- Whether released results can be retained after the study ends.
- Nullifier retention period needed to prevent duplicate counting.
- Withdrawal behavior for future contributions.
- Reviewer identity and approval date.

Sparse-cell suppression, budget exhaustion, rejected proof receipts, and denied
template changes are audit events. They should not retain raw contribution
values beyond the operation needed to make the decision.

## Operational Requirements

Production deployments must configure retention in the systems that actually
hold data:

- `WALLET_REPOSITORY_ROOT` durable repository lifecycle and backup policy.
- `WALLET_STORAGE_CONFIG` local/IPFS/S3/Filecoin encrypted blob lifecycle.
- Secret-manager rotation and audit retention for wallet/proof/alert secrets.
- Ops worker JSONL/log retention and alert-router retention.
- Browser/session cache behavior in the deployed UI.
- Incident-response export storage and access review.

The technical gate is:

```bash
python -m wallet_interface.ops --validate-production-readiness
```

The governance gate is a completed
`docs/WALLET_TARGET_PRODUCTION_SIGNOFF.md` packet that names the approved
retention schedule, storage lifecycle controls, backup purge SLA, and reviewers.
Use `docs/WALLET_TARGET_PRODUCTION_SIGNOFF_PACKET.template.json` for the
machine-readable retention mapping, then validate the completed packet with:

```bash
python -m wallet_interface.ops \
  --validate-target-signoff-packet /path/to/target-signoff.json
```
