# Wallet Production Decisions ADR

Status: accepted for first production deployment.

Date: 2026-05-05

## Context

`docs/UCAN_ZK_DATA_WALLET_IMPLEMENTATION_PLAN.md` tracked several decisions that
were intentionally left open while the wallet MVP stabilized: external UCAN
compatibility, polygon/distance proof direction, differential privacy defaults,
analytics execution model, and passkey/device-key UX.

The integrated implementation now has working wallet snapshots, encrypted
storage configuration, UCAN-style grants and invocations, recovery/device
management, analytics budget ledgers, proof backends, API/UI surfaces, and ops
readiness checks. The remaining choices should be explicit so production
readiness is not blocked by ambiguous design language.

## Decisions

| Decision | First Production Choice | Rationale |
| --- | --- | --- |
| UCAN encoding | Use the current signed `wallet-ucan-v1` invocation token profile for first production; keep the wallet authorization vocabulary compatible with future `ucanto`/w3up adapters. `docs/WALLET_UCAN_PROFILE.md` is the binding profile reference. | The wallet package already enforces resource, ability, caveat, attenuation, expiry, revocation, and threshold-approval semantics. Shipping behind a stable internal profile avoids coupling production readiness to a JavaScript token stack while preserving an interop track. |
| External UCAN interop | Add conformance fixtures later instead of making `ucanto`/w3up wire compatibility a launch blocker. | External interop affects ecosystem compatibility, not the core confidentiality boundary. The product API should not expose token internals. |
| Next proof backend | Keep `location_region` as the first production verifier boundary. Add `location_distance` next through the same HTTP verifier contract shape, then polygon proofs after a reviewed circuit/verifier service is available. | Distance eligibility maps directly to 211 service matching and can use the same safe-public-input discipline. Arbitrary polygon support has higher circuit and policy complexity. |
| Differential privacy defaults | Keep default `min_cohort_size=10` and `epsilon_budget=1.0` for new templates. Require explicit privacy review for lower cohort thresholds, higher epsilon, new dimensions, joins, or rare-condition cohorts. | These are conservative product defaults already reflected in the API layer. Smaller regional cohorts need human review because DP alone does not prevent re-identification. |
| Analytics execution model | Run first production aggregation in the trusted wallet analytics service with template approval, nullifiers, k-thresholds, sparse-cell suppression, DP metadata, query budgets, and audit events. Evaluate MPC/TEE/FHE only for high-risk studies that cannot be safely handled by this model. | The current service model is testable and auditable. Advanced private computation adds operational complexity and should be reserved for concrete high-risk use cases. |
| Passkey UX | Treat passkeys as the preferred human authentication UX over wallet device keys, not as a replacement for wallet controller/recovery governance. Device DIDs and recovery contacts remain the wallet authority model. | This lets the UI adopt WebAuthn/passkeys without changing the core grant, key-wrap, controller, recovery, and audit semantics. |
| Production signoff | Use `python -m wallet_interface.ops --validate-production-readiness` as the in-repo technical gate, then require organization-level security/privacy/legal/accessibility/retention signoff through `docs/WALLET_TARGET_PRODUCTION_SIGNOFF.md` and `docs/WALLET_RETENTION_POLICY.md`. | The repo can validate configuration, health, and verifier contract behavior. It cannot provision real secrets or approve policy. |

## Follow-Up Work

- Add optional `ucanto`/w3up fixture tests after selecting an interop library or
  gateway, using `docs/WALLET_UCAN_PROFILE.md` as the comparison profile.
- Extend the HTTP proof verifier contract with `location_distance` request and
  receipt shapes before implementing distance proof UI.
- Keep analytics template approval records tied to reviewer identity and the
  approved `docs/WALLET_RETENTION_POLICY.md` mapping in the production
  datastore.
- Add passkey enrollment and recovery UX over the existing controller/device API
  once app authentication is selected.

## Consequences

- First production can proceed with `wallet-ucan-v1` as long as the readiness
  gate and organizational signoff pass.
- Advanced proof and UCAN interop work becomes a compatibility roadmap, not a
  prerequisite for deploying the current wallet.
- The plan can treat current in-repo implementation phases as complete while
  preserving explicit target-environment gates.
