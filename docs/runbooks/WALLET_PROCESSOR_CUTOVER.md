# Wallet Processor Cutover and Rollback

Status: WALPROC-065 retry repair complete; production enablement remains held.

This runbook binds the WALPROC-033 cutover evidence to package source commit
`92c1eddb55b40e4de57d51545f4bcdfbf3fab645`. It does not authorize publishing
the package, enabling World ID, or using production credentials.

## Release coordinates

| Coordinate | Value |
| --- | --- |
| Package | `ipfs_datasets_py==0.2.0` |
| Source-bound package commit | `92c1eddb55b40e4de57d51545f4bcdfbf3fab645` |
| Documentation parent | `422308477058a9a82a1f6bbeacd1914fa3d9691e` |
| Pre-cutover rollback pin | `9f82fa0d078f15fd8b1241b2bbe78c41d7257d39` |
| Wrapper compatibility | `0.2.0` inclusive |
| Wrapper expiry begins | `0.3.0` |
| Ledger/export schema majors | v1 / v1 |

The source-bound commit changes exactly these package-owned release documents:

- `CHANGELOG.md`
- `docs/wallet_processors/COMPATIBILITY.md`
- `docs/wallet_processors/MIGRATION.md`
- `docs/wallet_processors/README.md`

The matching receipt is
[`data/wallet_processor_migration/release/cutover-receipt.json`](../../data/wallet_processor_migration/release/cutover-receipt.json).

## Ownership and safety boundaries

- `ipfs_datasets_py.processors.wallets.worldcoin` owns reusable World ID
  configuration, signing primitives, parsing, verification transport,
  redaction, binding, and proof behavior.
- `wallet_interface.world_id` remains a thin compatibility re-export with
  machine-readable alias-window constants.
- The application retains actor authorization, persistence, routing, audit
  policy, readiness composition, and browser-safe response shaping.
- Public UI types may contain opaque references and commitments, but never raw
  nullifiers, proofs, RP signatures, or Developer Portal responses.
- After verification, proof receipts refresh through `ProofCenterScreen` and
  the typed wallet API (`listWalletProofReceipts`). The verification panel
  must not synthesize a duplicate local proof card.
- Wallet processors do not gain custody, transaction signing, or broadcast
  authority during cutover.

## Preconditions

Before deployment:

1. Verify the outer gitlink and submodule source:

   ```bash
   test "$(git rev-parse HEAD:ipfs_datasets_py)" = \
     "92c1eddb55b40e4de57d51545f4bcdfbf3fab645"
   test "$(git -C ipfs_datasets_py rev-parse HEAD)" = \
     "$(git rev-parse HEAD:ipfs_datasets_py)"
   test -z "$(git -C ipfs_datasets_py status --porcelain)"
   ```

2. Verify the four files are committed by that package commit:

   ```bash
   git -C ipfs_datasets_py diff-tree --no-commit-id --name-only -r \
     92c1eddb55b40e4de57d51545f4bcdfbf3fab645
   ```

3. Install UI dependencies normally. Do not use `--force`, architecture
   overrides, or a committed platform-specific Rollup package:

   ```bash
   npm --prefix wallet_interface/ui ci
   npm --prefix wallet_interface/ui ls esbuild --depth=1
   ```

4. Capture a read-only dataset inventory and immutable backup reference in the
   restricted operator change record.
5. Keep World ID disabled until all offline, browser, and approved live-tenant
   gates pass.

## Validation

Run the hard task gate against the unchanged candidate (proposal-reviewed and
validation candidates must be identical):

```bash
python -m pytest -q \
  tests/test_world_id_wrapper_ownership.py \
  tests/test_world_id_wallet.py \
  tests/test_world_id_wallet_api.py &&
npm --prefix wallet_interface/ui run build &&
PLAYWRIGHT_PORT=5175 npm --prefix wallet_interface/ui test -- \
  tests/world-id.spec.ts tests/world-id-ux.spec.ts \
  --project="Desktop Chrome" &&
PLAYWRIGHT_PORT=5176 npm --prefix wallet_interface/ui test -- \
  tests/world-id-fullstack.spec.ts \
  --project="Desktop Chrome"
```

Also verify receipt integrity:

```bash
python -m json.tool \
  data/wallet_processor_migration/release/cutover-receipt.json >/dev/null
git diff --check
```

The retry repair resolves the task-owned architecture/install and typed-client
gaps:

- Normal Linux/arm64 install selects optional arm64 Rollup packages; Vite
  provides `esbuild`. No direct `@rollup/rollup-linux-x64-musl` pin.
- `WorldIdVerificationPanel` routes config, status, RP signature, and
  verification through the typed wallet client.
- Wallet API public configuration is authoritative in the panel; missing
  `app_id` or `rp_id` fails closed without a browser runtime fallback.
- `WorldIdVerificationResult` and its fixture companion expose no nullifier
  field.
- Proof receipts refresh via `ProofCenterScreen` + `listWalletProofReceipts`
  after verification.
- `world-id.spec.ts` may only install `abby-ui-session-v1` before navigation;
  assertions and endpoint/privacy expectations stay unchanged.
- `world-id-ux.spec.ts` installs the same current session and checks the
  rendered manual-intake, wallet-proof QR, and export surfaces while retaining
  accessibility and private-token leakage assertions.
- `world-id-fullstack.spec.ts` injects a test-only
  `WalletInterfaceService.world_id_request_json` transport. It first verifies
  the production request targets `https://developer.world.org`, then uses a
  byte- and time-bounded loopback fixture. Production endpoint policy is not
  changed or bypassed.

Failures outside the focused World ID Playwright specs in the inherited full
UI suite are release debt and do not authorize edits outside declared Outputs.
Do not weaken endpoint policy or privacy assertions. Live-tenant signoff
remains an external release gate. A blocker is not production signoff.

## Alias window

Compatibility aliases remain supported through `0.2.0` inclusive. Removal may
begin at `0.3.0`, exposed by
`WRAPPER_ALIAS_COMPATIBILITY_PACKAGE_VERSION` and
`WRAPPER_ALIAS_EXPIRY_PACKAGE_VERSION`. Migrate callers before removing
aliases; never restore the old duplicate implementation.

## Non-destructive rollback rehearsal

Verify objects without modifying the active checkout or dataset paths:

```bash
git -C ipfs_datasets_py cat-file -e \
  9f82fa0d078f15fd8b1241b2bbe78c41d7257d39^{commit}
git -C ipfs_datasets_py cat-file -e \
  422308477058a9a82a1f6bbeacd1914fa3d9691e^{commit}
git -C ipfs_datasets_py cat-file -e \
  92c1eddb55b40e4de57d51545f4bcdfbf3fab645^{commit}
test "$(git rev-parse HEAD:ipfs_datasets_py)" = \
  "92c1eddb55b40e4de57d51545f4bcdfbf3fab645"
```

Compare the dataset inventory before and after. It must be identical because
the rehearsal does not address dataset paths.

## Deployment rollback

Rollback if ownership, redaction, provider bounds, snapshot/import, or
readiness gates regress:

1. Disable World ID before changing code or pins.
2. Restore the recorded prior outer release and matching package gitlink.
3. Restore the matching thin wrapper; do not revive duplicate protocol code.
4. Re-run ownership, application, package, manifest, and UI gates.
5. Compare dataset and snapshot sentinels. Never delete, downgrade, or rewrite
   historical wallet datasets.
6. Record the incident, restored coordinates, and validation results in a new
   receipt.

Production enablement still requires separate operator authority and approved
live-tenant signoff.
