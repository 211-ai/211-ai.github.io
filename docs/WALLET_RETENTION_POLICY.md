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

## Target Storage Retention Mapping

Target deployments must convert the default schedule above into concrete
provider controls before live wallet data is stored. The approved mapping belongs
in the completed signoff packet and must use secret-manager references rather
than credential values.

| Control | Required Mapping |
| --- | --- |
| Storage credentials | `WALLET_STORAGE_CREDENTIAL_SECRET_REF` names the secret-manager entry that provisions IPFS, Filecoin, S3, and any local-replica credentials. Readiness and signoff evidence may include the reference only, never the secret value. |
| Encrypted replica set | `WALLET_STORAGE_CONFIG` names one primary encrypted store and the target mirror set. Production storage should use client-side encrypted replicas; S3 server-side encryption or private IPFS gateways are defense-in-depth, not the confidentiality boundary. |
| IPFS pinning | Pin encrypted payload and metadata blocks only in the approved private pinset while the source wallet record version is retained. On deletion, key rotation, account closure, or retention expiry, remove wallet manifest references and unpin the associated CIDs. Record the pinset policy ID and unpin evidence in the signoff packet. |
| Filecoin deal expiration | Filecoin deals for wallet ciphertext must not outlive the approved source-record retention period plus any legal hold. Renew deals only for active retained encrypted replicas. On deletion or expiry, let deals expire or issue provider-supported removal/renewal-blocking controls, and record deal IDs or policy references without plaintext. |
| S3 lifecycle | S3 buckets or prefixes that hold wallet ciphertext must have lifecycle rules covering current object deletion, noncurrent-version expiration, incomplete multipart upload cleanup, and legal-hold exceptions. The lifecycle policy ID is recorded separately from `WALLET_STORAGE_CONFIG` so reviewers can verify object retention and backup purge behavior. |
| Backup purge | Wallet repository backups and encrypted blob backups must purge deleted or expired records under the approved `backup_purge_sla`, unless a legal hold is active. Backup evidence must show ciphertext/object IDs only. |
| Alert retention | Ops-health JSONL, alert-router payloads, incident tickets, and notification delivery logs default to 90 days. Incident-attached alerts follow the incident-retention period. Alert payloads must include status metadata only and must not include wallet plaintext, precise coordinates, proof witnesses, verifier tokens, or storage credentials. |
| Repair evidence | Storage health and repair reports must prove encrypted replica availability with ciphertext hashes and storage-type statuses. They must not decrypt payloads for operators or include plaintext in report bodies, logs, alerts, or tickets. |

## WALLET-190 Staging Dry-Run Evidence

Before a target environment can be signed off, operators must run one
production-like storage retention and deletion dry run against synthetic staging
wallet data. The dry run demonstrates the retention controls below and archives
the evidence artifact IDs in `docs/WALLET_TARGET_PRODUCTION_SIGNOFF.md`.

| Control | Required Dry-Run Evidence |
| --- | --- |
| Encrypted replica creation | Create or upload at least one synthetic wallet record with the target `WALLET_STORAGE_CONFIG`. Evidence includes the primary encrypted storage ref, mirror refs, `storage_type`, `size_bytes`, and `sha256` values only. |
| Replica health checks | Run record-level wallet storage verification and `GET /ops/health?verify_storage=true`. Evidence includes `record_count`, `replica_count`, `failed_replica_count=0`, and the storage-type summary. |
| Repair | Remove or invalidate one non-production staging replica, run the record or wallet repair control, and archive the repair report showing `ok=true` and the repaired replica count or per-record repaired status. |
| Grant revocation | Revoke a delegated grant that can access the synthetic record, then prove descendant grants and delegated key wraps no longer permit decrypt, analysis, or export access. |
| Key rotation | Rotate the retained synthetic record key after revocation and archive only the new version ID, key-wrap status counts, and audit event IDs. |
| Record deletion | Delete one synthetic staging record through the approved record deletion control, remove manifest references and dependent key wraps, and record tombstone, unpin/delete, and backup-purge ticket IDs. A dry run is not complete if record deletion is only marked as future work. |
| Analytics-consent withdrawal | Withdraw one analytics consent, show future contributions are blocked, and retain only the consent withdrawal, nullifier, query-budget, and aggregate-release audit records required by this policy. |
| Export-bundle retention | Create, verify, storage-check, and expire or retain one encrypted export bundle according to the approved export retention decision. Evidence includes bundle hash, record count, storage status, and retention ticket IDs only. |
| Purge/audit evidence | Archive provider purge, backup purge, audit timeline, and reviewer evidence. The evidence must contain no plaintext wallet data, proof witnesses, precise coordinates, key material, bearer tokens, webhook credentials, or secret values. |

The archived dry-run evidence bundle must use an allow-list envelope. Required
fields are the staging environment ID, `retention_policy_version`, storage
topology ID, storage policy references, synthetic wallet ID, synthetic record
IDs, storage types, ciphertext refs, `size_bytes`, `sha256`, replica counts,
health and repair statuses, revoked grant IDs, rotated version IDs, analytics
consent and withdrawal IDs, export bundle hash, tombstone ID, purge ticket IDs,
backup purge ticket ID, audit event IDs, reviewer name or role, review date,
and leak-review decision.

Forbidden fields and values are wallet plaintext, document bodies, extracted
form values, precise coordinates, proof witnesses, decrypted export bundle
contents, raw contribution values, private keys, key-encryption keys, bearer
tokens, webhook credentials, resolved secret-manager payloads, process
environment dumps, and provider credential values. If any forbidden value is
present, the dry run fails even when the storage operation itself succeeded.

The privacy reviewer or operations reviewer must inspect the dry-run artifact for
leaks before approving the retention mapping. A dry-run artifact that reveals
plaintext or secret values fails the target environment signoff even when all
storage and deletion actions succeeded.

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

Each analytics template must carry a retention decision before approval, and the
decision must be copied into the completed target signoff packet. The template
definition, purpose, user-facing consent language, data-field review, cohort
threshold, privacy budget, sparse-cell risk review, retention mapping, reviewer
decision, withdrawal plan, and audit plan are retained together as the
production analytics review packet.

Production analytics must not be approved as arbitrary raw queries. The retained
review packet is the release record for each approved template ID and must name
the approved consent copy, allowed record types, allowed derived fields, allowed
aggregation dimensions, public proof statements, nullifier policy, k-threshold,
privacy budget, reviewer name or role, and withdrawal handling. If any of those
fields changes, the prior packet remains audit evidence and the replacement
template requires a new retention mapping before it can run.

A target signoff packet is incomplete when an approved production template is
missing any WALLET-160 review component: documented purpose, data fields,
consent language, retention mapping, cohort threshold, privacy budget,
sparse-cell risk review, reviewer decision, or withdrawal and audit handling
plan. Retain those components as one packet so reviewers can reconstruct the
approved question, authorized fields, privacy controls, release decision, and
withdrawal behavior without reading source code, ad hoc queries, or raw wallet
payloads.

| Review Packet Component | Retention Mapping | Withdrawal and Purge Handling |
| --- | --- | --- |
| Template definition, purpose, approved record types, approved derived fields, approved dimensions, and rejected data fields | Retain while the template is active plus the approved audit-retention period. Map this to `analytics_privacy_review.approved_templates[]` and the target `retention_mapping.policy_version`. | Template changes that add fields, dimensions, joins, or raw-query access require a new review packet. Paused or retired templates block new consent, contribution, and aggregate query creation while preserving prior audit history. |
| Consent language and copy artifact | Retain the approved consent copy/version for the consent lifetime plus the audit-retention period so users and reviewers can reconstruct what was authorized. | Consent withdrawal must preserve the consent copy, withdrawal time, actor, and support path without retaining raw contribution values. |
| Public proof statements and verifier or proof-mode decision | Retain with the template approval record and contribution proof audit trail. The retained statement must describe the approved `analytics_contribution` public inputs and confirm that proof public inputs do not include raw record payloads, precise location, plaintext document fields, or direct identifiers. | If proof semantics change, retire or pause the template until reviewers approve a new statement and retention mapping. Rejected or failed proof receipts are audit events and should not retain witness material. |
| Nullifier policy and duplicate-rejection evidence | Retain the nullifier scope, duplicate-rejection rule, nullifier retention period, and regression evidence with the template packet and released aggregate audit trail. | Consent withdrawal blocks future contributions but retains nullifier evidence only as long as needed to prevent duplicate counting and explain prior releases. Nullifiers must not be exported as wallet identifiers. |
| Cohort threshold, privacy budget, budget key, and allowed aggregation dimensions | Retain with the template approval record and released aggregate audit trail. The mapping must name the minimum cohort size, epsilon budget, per-query epsilon where applicable, and query-budget ledger scope. | Budget exhaustion, threshold failures, and reviewer-approved exceptions are audit events. They must not expose suppressed cell labels, raw derived values, or wallet identifiers outside the approved audit boundary. |
| Sparse-cell risk review, suppression evidence, and duplicate-nullifier evidence | Retain sparse-cell review evidence for the template lifetime plus audit-retention period, and retain release-specific suppression metadata with each aggregate result. | Suppressed cells must remain suppressed in exports, reports, tickets, and alerts. Regression evidence should show counts of suppressed cells without retaining the suppressed labels when those labels would identify a rare cohort. |
| Analytics consents, withdrawals, contribution nullifiers, and query-budget ledgers | Retain for the consent lifetime plus the approved audit-retention period. Nullifier retention must be long enough to prevent duplicate counting for the approved study window. | Withdrawal blocks future contribution use. Prior released aggregate audit history, nullifiers, and budget-spend records are retained only as needed to explain releases and prevent duplicate counting. |
| Released aggregate results and privacy metadata | Retain for the approved study-retention period. Store result ID, template ID, privacy notes, suppression counts, noisy/exact count policy, budget spend, and reviewer evidence. | At study close, delete or archive aggregate results according to the approved retention decision. Exported aggregate reports must not contain sparse suppressed labels or raw contribution values. |
| Reviewer decision, exception record, and audit handling plan | Retain for the approved audit-retention period with reviewer name or role, decision date, decision, evidence ID, and tracked exceptions. | A `deferred` decision blocks production approval. Exception expiry or policy change requires re-review before the template continues running. |

The per-template `analytics_privacy_review.approved_templates[].retention_mapping`
object in the completed signoff packet must map at least these controls to the
target policy version: `template_definition`, `consent_copy`,
`consents_withdrawals`, `contributions`, `nullifiers`,
`query_budget_ledger`, `released_aggregates`, and `audit_events`.

Sparse-cell suppression, budget exhaustion, rejected proof receipts, denied
template changes, consent withdrawals, and template pause or retirement are
audit events. They should not retain raw contribution values beyond the
operation needed to make the decision.

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

That gate must report `storage_retention_controls=ok` for the target
IPFS-pinning, Filecoin-deal, S3-lifecycle, backup-purge, and alert-retention
policy references, and `storage_repair_safety=ok` for metadata-only encrypted
replica repair reporting.

The governance gate is a completed
`docs/WALLET_TARGET_PRODUCTION_SIGNOFF.md` packet that names the approved
retention schedule, storage lifecycle controls, backup purge SLA, and reviewers.
Use `docs/WALLET_TARGET_PRODUCTION_SIGNOFF_PACKET.template.json` for the
machine-readable retention mapping, then validate the completed packet with:

```bash
python -m wallet_interface.ops \
  --validate-target-signoff-packet /path/to/target-signoff.json
```
