# Submodule pin policy (voice-app-surface-coverage residual)

Program: `voice-app-surface-coverage-v1`

## Current monorepo pins

| Submodule | Working pin | Published remote ref for CI |
| --- | --- | --- |
| `ipfs_accelerate_py` | `071b71f73` | `origin/ci/monorepo-pin-071b71f73` |
| `ipfs_datasets_py` | `29b475858` | `origin/ci/monorepo-pin-29b475858` |
| `ipfs_kit_py` | `80afdad2` | matches `origin/main` |

These accelerate/datasets SHAs include **voice-action** modules required by the
monorepo (`action_runtime`, `voice/action_links`, `voice/action_retrieval`).

## Why not `origin/main` of the submodules

| Submodule | Issue |
| --- | --- |
| `ipfs_accelerate_py` | Diverged (local voice-action history ahead; remote main far ahead) |
| `ipfs_datasets_py` | Remote `main` **lacks** `voice/action_links.py` and `voice/action_retrieval.py` |

Blind FF to submodule `origin/main` breaks Abby voice-action imports.

## CI requirement

GitHub Actions `actions/checkout` with `submodules: true` must be able to
**fetch the exact pin SHA**. Publishing a branch/tag that contains the pin is
sufficient:

```bash
git -C ipfs_accelerate_py push origin HEAD:refs/heads/ci/monorepo-pin-<sha7>
git -C ipfs_datasets_py push origin HEAD:refs/heads/ci/monorepo-pin-<sha7>
```

## Integration path (future)

1. Merge voice-action commits into each submodule's `main` (or rebase onto remote main).
2. Fast-forward monorepo gitlinks to those tips.
3. Re-run `scripts/voice_app_surface_coverage/record_submodule_pins.py --write --check`.
4. Delete temporary `ci/monorepo-pin-*` branches after monorepo tracks published main.

## Receipt

`data/voice_app_surface_coverage/baseline/submodule-pins.json`
