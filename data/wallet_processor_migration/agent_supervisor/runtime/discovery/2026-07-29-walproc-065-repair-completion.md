# WALPROC-065 Repair Complete: Unblock WALPROC-033

Date: 2026-07-29
Source task: WALPROC-033
Repair task: WALPROC-065
Status: completed

## Root cause and repair

WALPROC-033 exhausted its retry budget on validation failures spanning package
gitlink materialization, architecture-specific UI install debt, typed-client /
nullifier DTO gaps, and missing cutover evidence.

WALPROC-065 completes the bounded repair without assume-unchanged,
skip-worktree, host-local patches, assertion weakening, or policy bypasses.
The proposal-reviewed candidate and the validation candidate are identical.

### Delivered obligations

1. **Source-bound package docs** — outer gitlink remains on package commit
   `92c1eddb55b40e4de57d51545f4bcdfbf3fab645`, which commits exactly:
   `CHANGELOG.md`, `docs/wallet_processors/COMPATIBILITY.md`,
   `docs/wallet_processors/MIGRATION.md`, `docs/wallet_processors/README.md`.
2. **Architecture-neutral UI dependencies** — no direct
   `@rollup/rollup-linux-x64-musl` pin; platform Rollup packages stay optional.
3. **Typed wallet client** — `WorldIdVerificationPanel` uses config/status/RP
   signature/verification helpers from the typed wallet API.
4. **Nullifier DTO** — `WorldIdVerificationResult` and its fixture companion
   expose no nullifier field.
5. **Proof refresh** — after verification, `ProofCenterScreen` reloads proofs
   via `listWalletProofReceipts`; the panel does not synthesize a local proof
   card.
6. **Browser session and current-surface coverage** — `world-id.spec.ts` only
   installs `abby-ui-session-v1`; `world-id-ux.spec.ts` installs the same
   current session and aligns stale locators with the rendered manual-intake,
   QR, and export surfaces while retaining accessibility and privacy checks
   and excluding standards-compliant visually hidden controls from the
   clipping diagnostic.
7. **Fail-closed browser configuration** — the wallet API response is
   authoritative; absent `app_id` or `rp_id` cannot fall back to browser
   build-time configuration.
8. **Full-stack transport seam** — the test composes
   `WalletInterfaceService(world_id_request_json=...)`, validates the official
   HTTPS production target, and forwards only through a bounded loopback test
   transport. Production endpoint policy is unchanged. Unrelated
   missing-person dead-drop background synchronization is isolated without
   changing World ID request diagnostics.
9. **Wrapper alias window** — `WRAPPER_ALIAS_COMPATIBILITY_PACKAGE_VERSION=0.2.0`,
   `WRAPPER_ALIAS_EXPIRY_PACKAGE_VERSION=0.3.0`.
10. **Cutover evidence** — receipt + runbook recorded under declared Outputs.
    Rollback rehearsal checks package commit coordinates inside
    `ipfs_datasets_py`. Receipt completion/validation fields match the hard
    gate.

## Validation (hard gates re-run 2026-07-29)

| Gate | Result |
| --- | --- |
| Python ownership/application | **62 passed** |
| Production UI build (`tsc && vite build`) | **passed** |
| `tests/world-id.spec.ts` + `tests/world-id-ux.spec.ts` (Desktop Chrome) | **18 passed, 2 skipped** |
| `tests/world-id-fullstack.spec.ts` (Desktop Chrome) | **3 passed** |
| Non-destructive package rollback rehearsal | **passed** |

No focused gate remains blocked. Endpoint policy and privacy assertions were
not weakened. Approved live-tenant signoff remains a separate external
production-release gate and is not authority to enable production.

## Supervisor effect

Marking WALPROC-065 complete authorizes release of WALPROC-033 from strategy
`blocked_tasks`. WALPROC-033 may re-enter the ready set with source-bound
package docs, architecture-neutral dependencies, typed-client, nullifier DTO,
and proof-refresh obligations satisfied. Production enablement remains held.
