# Git Migration Review 2026-05-07

This directory captures the current local Git state for migration to `https://github.com/211-ai/211-ai.github.io`.

## Current findings

- `origin` and `upstream` both point to `https://github.com/211-ai/211-ai.github.io`.
- The new origin currently exposes only `main` and `copilot/211-ai-pull-changes`.
- Local `main` is ahead of `origin/main` and includes the WALLET-210 readiness merge at `141580cf`.
- A push to the new origin is currently blocked by GitHub permission errors for the configured credentials.
- Fourteen attached implementation worktrees still contain uncommitted changes. Those edits are not preserved by branch pushes and were exported as patch files here.

## Preserved artifacts

- `211-AI-all-refs-20260507.bundle`: offline bundle containing all committed refs.
- `branch-inventory.txt`: local and remote refs with tip SHAs and subjects.
- `origin-heads.txt`: branch heads currently visible on the new origin.
- `worktree-list.txt`: registered worktrees.
- `worktree-patch-summary.txt`: dirty worktrees with exported patch file paths.
- `worktree-patches/`: per-worktree patch exports, excluding `wallet_interface/ui/node_modules`.

## High-level branch groups

- `implementation/*`: attached ephemeral worktree branches. Their committed tips are already reachable from `main`, but many still have uncommitted edits in their worktrees.
- `rescue/wallet-210-*`: failed-validation snapshots. Attempt 19 was merged into local `main`; earlier attempts remain as historical refs.
- `rescue/portal-*`, `rescue/agent-071`, `rescue/graphrag-021`, `rescue/mixed-daemon`, `rescue/abby-ui-style-in-progress`: local rescue branches with unique commits not present on local `main`.
- `backup/pre-merge-*`: local backup refs. `backup/pre-merge-20260504-0003` still has one unique commit not on local `main`.
- `merge/pr2-ready-20260507` and `pr/endomorphosis/2`: preserved PR-era refs pointing at `a67efc93`.

## To complete migration after credentials are fixed

1. Push committed refs: `git -C /home/barberb/211-AI push origin --all`
2. Push tags if needed: `git -C /home/barberb/211-AI push origin --tags`
3. Review `worktree-patch-summary.txt` and either commit those patches onto archival branches or apply them to new branches before pushing.
4. Remove stale temporary worktrees only after any wanted patches have been committed or separately archived.