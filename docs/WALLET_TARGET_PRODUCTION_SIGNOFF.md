# Wallet Target Production Signoff

Status: required checklist for each production-like environment.

Date: 2026-05-05

## Use

Create one completed copy of this checklist for every staging, pilot, and
production environment that handles live wallet data. Store the completed packet
in the organization's approved evidence system.

Do not paste secret values into this document. Record secret-manager paths,
configuration IDs, report artifact IDs, and reviewer names only.

For CI or release gates, copy
`docs/WALLET_TARGET_PRODUCTION_SIGNOFF_PACKET.template.json` into the target
evidence repository, replace every placeholder with target evidence references,
and validate it with:

```bash
python -m wallet_interface.ops \
  --validate-target-signoff-packet /path/to/target-signoff.json \
  --fail-on-error
```

The JSON packet is the machine-readable completion record for retention,
secret-manager references, staging readiness artifacts, analytics privacy
review, organization review, and the launch decision. The Markdown checklist
remains the human-readable reviewer guide. The packet validator requires the
environment record to include the approved `retention_policy_version` that
matches the target retention mapping.

Running `python -m wallet_interface.ops --validate-target-signoff-packet`
without a packet path validates the committed JSON template shape only. A
launch decision still requires validating the completed target packet path.

## Environment Record

| Field | Value |
| --- | --- |
| Environment name |  |
| Deployment owner |  |
| Review date |  |
| Wallet API origin |  |
| Wallet UI origin |  |
| Repository configuration ID |  |
| Encrypted storage configuration ID |  |
| Secret-manager path for ops-health secret |  |
| Secret-manager path for alert credentials |  |
| Secret-manager path for proof verifier credentials |  |
| Proof backend |  |
| Proof verifier service URL or private service name |  |
| Proof verifier ID |  |
| Proof system |  |
| Secret-manager reference used for verifier credential injection |  |
| Release-check evidence artifact |  |
| Readiness report artifact |  |
| Ops-health report artifact |  |
| Location-region proof contract report artifact |  |
| Location-distance proof contract report artifact |  |
| Non-simulated verifier cutover packet artifact |  |
| Location-region verifier failure-mode artifact |  |
| Location-distance verifier failure-mode artifact |  |
| Verifier rollback drill artifact |  |
| Storage retention/deletion dry-run evidence artifact |  |
| Storage repair evidence artifact |  |
| Deletion purge/audit evidence artifact |  |
| Proof Center `location_distance` exposure decision | hidden until archived validation and approval |
| Retention policy version |  |
| S3 lifecycle policy ID |  |
| IPFS pinset policy ID |  |
| Filecoin deal policy ID or not-used decision |  |
| Backup purge policy ID |  |
| Alert retention policy ID |  |
| Incident-response contact path |  |

## Verifier Credential Handoff

Complete this section for the target staging environment before launch review.
The credential owner and deployment owner should verify the actual verifier
credential directly in the selected secret manager or deployment platform. This
checklist records references and evidence IDs only.

| Handoff Check | Required Evidence | Status |
| --- | --- | --- |
| Credential provisioned | Verifier bearer token or custom header credential exists in the selected secret manager and has an owner, rotation path, and least-privilege access policy |  |
| Reference only in repo and packets | `WALLET_PROOF_CREDENTIAL_SECRET_REF` or the equivalent provider reference is recorded; no bearer token, header value, proving key, verifier key, or rendered secret payload is present in repo docs, signoff packets, readiness reports, logs, or tickets |  |
| Runtime injection | Wallet API and ops worker receive verifier auth material from the secret-manager integration at runtime, and no process env dump is archived |  |
| Rotation dry run | Staging credential rotation was exercised or explicitly scheduled with rollback owner and artifact ID |  |
| Staging contract archive | Region and distance contract reports are archived from target staging with `status=ok` and no leaked witness or secret values |  |

## WALLET-180 Non-Simulated Verifier Cutover Packet

Complete this packet after WALLET-140 verifier credential handoff and before
any non-simulated proof creation path is exposed to users. The same selected
verifier backend must have evidence for both `location_region` and
`location_distance`. A repo-local `mode=local_self_check` report is not launch
evidence.

Record only artifact references, reviewer names, deployment IDs, secret-manager
references, and rollback owners. Do not attach bearer tokens, custom header
values, proving keys, verifier keys, witness payloads, precise wallet
coordinates, target coordinates, exact addresses, nonces, process env dumps, or
resolved secret-manager payloads.

| Cutover Field | Required Value | Status |
| --- | --- | --- |
| Selected verifier backend | Service URL or private service name, deployment artifact or image digest, verifier owner, and on-call path |  |
| Verifier metadata | `proof_backend`, `proof_verifier_id`, `proof_system`, region circuit ID, distance circuit ID, endpoint paths, and version |  |
| Credential reference | `WALLET_PROOF_CREDENTIAL_SECRET_REF` or provider equivalent plus rotation owner and latest rotation artifact |  |
| Exposure scope | Which API/UI paths become available at cutover, with `location_distance` still hidden unless separately approved |  |
| Rollback owner | Named operator, incident channel, previous deployment reference, and expected rollback time |  |

Required evidence matrix:

| Proof Family | Evidence Gate | Required Artifact | Status |
| --- | --- | --- | --- |
| `location_region` | Staging health | Archived `--validate-proof-contract` JSON showing `checks.health.status=ok` for the selected verifier |  |
| `location_region` | Prove | Same artifact showing `checks.prove.status=ok`, `proof_type=location_region`, `is_simulated=false`, expected verifier metadata, and no stored receipt on failed prove |  |
| `location_region` | Verify | Same artifact showing `checks.verify.status=ok` for the returned receipt |  |
| `location_region` | No-leak | Same artifact showing `checks.public_input_safety.status=ok` plus API/verifier log-review artifact with no witness keys, coordinates, addresses, nonces, or secret values |  |
| `location_region` | Credential reference | Readiness/signoff evidence shows only the secret-manager reference and no rendered credential material |  |
| `location_region` | Failure mode | Target-staging drill with invalid credential, unhealthy verifier, rejected prove, or `verify=false` causes nonzero validation/readiness output, `status=error`, no stored proof receipt, and no witness or secret values in archived output |  |
| `location_region` | Rollback | Drill artifact proves the operator can revert API/UI/ops/verifier deployment or disable proof creation while keeping production proof mode fail-closed against simulated receipts |  |
| `location_distance` | Staging health | Archived `--validate-distance-proof-contract` JSON showing `checks.health.status=ok` for the selected verifier |  |
| `location_distance` | Prove | Same artifact showing `checks.prove.status=ok`, `proof_type=location_distance`, `is_simulated=false`, expected verifier metadata, and no stored receipt on failed prove |  |
| `location_distance` | Verify | Same artifact showing `checks.verify.status=ok` for the returned receipt |  |
| `location_distance` | No-leak | Same artifact showing `checks.public_input_safety.status=ok` plus API/verifier log-review artifact with no wallet coordinates, target coordinates, addresses, nonces, or secret values |  |
| `location_distance` | Credential reference | Readiness/signoff evidence shows only the secret-manager reference and no rendered credential material |  |
| `location_distance` | Failure mode | Target-staging drill with invalid credential, unhealthy verifier, rejected prove, out-of-policy distance response, or `verify=false` causes nonzero validation/readiness output, `status=error`, no stored proof receipt, and no witness or secret values in archived output |  |
| `location_distance` | Rollback | Drill artifact proves the live Proof Center keeps distance proof creation and display hidden until the distance cutover is approved |  |

The cutover decision is blocked until every row above is complete, both direct
contract reports and the full readiness report show `status=ok`, the packet has
security, privacy, operations, and product approval, and rollback evidence has
been archived. Do not enable a non-simulated user proof path as an exception to
this packet.

## Required Evidence

| Gate | Required Evidence | Status |
| --- | --- | --- |
| Production readiness | `python -m wallet_interface.ops --validate-production-readiness` returns `status=ok` in the target environment |  |
| Release-check archive | `python scripts/run_wallet_release_checks.py --playwright-port 5185` passes and its evidence bundle is archived |  |
| Durable wallet repository | `WALLET_REPOSITORY_ROOT` or equivalent managed datastore is configured, backed up, and covered by lifecycle policy |  |
| Encrypted storage replicas | `WALLET_STORAGE_CONFIG` and provider credentials are configured without placeholder values |  |
| WALLET-190 dry run | Target staging demonstrates encrypted replica creation, replica health checks, repair, grant revocation, key rotation, record deletion, analytics-consent withdrawal, export-bundle retention, and purge/audit evidence |  |
| Storage repair | `/ops/health?verify_storage=true` plus wallet or record storage repair checks pass with ciphertext/hash evidence only |  |
| External location-region verifier | `python -m wallet_interface.ops --validate-proof-contract --fail-on-error` passes in target staging with real runtime-injected credentials and archived JSON evidence |  |
| External location-distance verifier | `python -m wallet_interface.ops --validate-distance-proof-contract --fail-on-error` passes in target staging with real runtime-injected credentials and archived JSON evidence |  |
| WALLET-180 verifier cutover | Non-simulated verifier cutover packet archives health, prove, verify, no-leak, credential-reference, failure-mode, and rollback evidence for `location_region` and `location_distance` |  |
| Proof Center distance exposure | Live Proof Center creation and display surfaces keep `location_distance` hidden until the distance verifier report is archived and security, privacy, ops, and product reviewers approve exposure |  |
| Secret management | Ops-health, alert, storage, and verifier credentials live in the selected secret manager and are not committed to the repo |  |
| Alert routing | Warning/error reports reach the approved incident router with authenticated delivery |  |
| Security architecture | `docs/WALLET_SECURITY_ARCHITECTURE_ADR.md` reviewed for the target deployment boundary |  |
| UCAN profile | `docs/WALLET_UCAN_PROFILE.md` reviewed for the target delegation boundary and future interop expectations |  |
| Production decisions | `docs/WALLET_PRODUCTION_DECISIONS_ADR.md` accepted or amended for this deployment |  |
| Retention policy | `docs/WALLET_RETENTION_POLICY.md` mapped to datastore lifecycle, backup purge, IPFS pinning, Filecoin deal, S3 lifecycle, log, and alert retention settings |  |
| Privacy review | Approved analytics templates have cohort thresholds, epsilon budgets, allowed dimensions, nullifier handling, withdrawal behavior, and reviewer identity |  |
| Legal/policy review | User consent language, delegate terms, export behavior, revocation limits, and data-sharing obligations are approved |  |
| Accessibility/usability review | Live UI auth, registration, sharing, recipient access, consent, proof center, export, and emergency revoke flows pass the target accessibility and usability standard |  |
| Incident response | `docs/WALLET_OPERATIONS_RUNBOOK.md` is linked from the on-call system and the team has tested proof-backend, storage-outage, revoked-grant, lost-key, and privacy-incident paths |  |
| Operator reference | `docs/WALLET_OPERATOR_INTEGRATOR_REFERENCE.md` matches the deployed API, CLI, MCP, env, and release-check surface |  |
| Backup and restore | Wallet repository and encrypted storage restore tests pass without exposing plaintext outside the wallet service boundary |  |
| Deletion and purge | Record deletion, grant revocation, storage unpin/delete, backup purge tracking, and tombstone audit behavior are validated |  |
| Browser/session storage | UI stores no raw wallet plaintext, verifier secrets, or long-lived invocation tokens in browser storage |  |
| Rollback plan | API/UI/ops worker rollback path is documented and tested for the target environment |  |

## WALLET-190 Evidence Checklist

Complete this checklist with synthetic target-staging data and archive the
evidence bundle ID in the environment record. The evidence must be reviewed
before launch and must not reveal plaintext wallet data, proof witnesses,
precise coordinates, key material, bearer tokens, webhook credentials, or secret
values.

| Dry-Run Step | Required Evidence | Status |
| --- | --- | --- |
| Encrypted replica creation | Record creation or upload produced encrypted primary and mirror refs with `storage_type`, `size_bytes`, and `sha256` only |  |
| Replica health checks | Record or wallet storage verification and `/ops/health?verify_storage=true` returned `failed_replica_count=0` or no storage errors |  |
| Repair | A staging replica was removed or invalidated, repair was run, and the report showed `ok=true` with repaired-replica evidence |  |
| Grant revocation | Delegate grant was revoked, descendant access failed, delegated key wraps were revoked, and `revocation_propagation` was not `error` |  |
| Key rotation | Retained synthetic record key was rotated after revocation and only version ID, key-wrap status counts, and audit event IDs were archived |  |
| Record deletion | Synthetic record deletion removed manifest references and dependent key wraps, opened provider unpin/delete actions, created a tombstone, and started backup purge tracking |  |
| Analytics-consent withdrawal | Consent was revoked, future contributions were blocked, and withdrawal/nullifier/query-budget audit evidence was retained |  |
| Export-bundle retention | Encrypted export bundle create/verify/storage checks passed and bundle retention or purge disposition was recorded by bundle hash and ticket ID |  |
| Purge/audit evidence | IPFS, Filecoin, S3, backup, alert/log retention, tombstone, and audit evidence was reviewed for absence of plaintext and secret values |  |

## Required Commands

Run these commands from the target deployment context or CI job that has access
to the target environment variables and verifier service:

```bash
curl -fsS "${WALLET_API_ORIGIN}/health"
curl -fsS \
  -H "authorization: Bearer ${WALLET_OPS_HEALTH_SHARED_SECRET}" \
  "${WALLET_API_ORIGIN}/ops/health?verify_storage=true"
python -m wallet_interface.ops --validate-proof-contract --fail-on-error
python -m wallet_interface.ops --validate-distance-proof-contract --fail-on-error
python -m wallet_interface.ops --validate-production-readiness
python -m wallet_interface.ops \
  --validate-target-signoff-packet /path/to/target-signoff.json \
  --fail-on-error
```

The readiness report must not include secret values. A report that passes only
with `--skip-proof-contract` is not sufficient for production launch.
The direct proof-contract commands may report `mode=local_self_check` only in
repo-local automation without target verifier env vars; launch evidence must be
from the target staging environment and must not use the local self-check mode.
Archive the WALLET-180 failure-mode and rollback drill outputs beside the
passing contract reports; launch evidence is incomplete without both proof
families and both drill types.

## Reviewer Signoff

| Review Area | Reviewer | Decision | Date | Evidence |
| --- | --- | --- | --- | --- |
| Security |  |  |  |  |
| Privacy |  |  |  |  |
| Legal/policy |  |  |  |  |
| Accessibility/usability |  |  |  |  |
| Operations/on-call |  |  |  |  |
| Product owner |  |  |  |  |

Allowed decisions are `approved`, `approved with tracked exception`, or
`deferred`. A production launch requires no `deferred` decisions.

## Launch Decision

| Field | Value |
| --- | --- |
| Launch decision |  |
| Approved launch window |  |
| Required exceptions |  |
| First post-launch readiness run |  |
| First post-launch retention audit |  |

Re-run this checklist after verifier credential rotation, storage-provider
changes, analytics template expansion, auth-provider changes, or any incident
that affects wallet confidentiality, availability, auditability, or deletion.
