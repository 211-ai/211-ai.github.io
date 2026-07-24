# WORLDCOIN-AUTO-005 SIWE dependency preparation evidence

Date: 2026-07-24

Authority: discovery and unapproved preparation only. This document is not a
Gate 0B selection and does not authorize package installation or execution.

## Primary-source findings

- World documents the server import as
  `@worldcoin/minikit-js/siwe`, including `parseSiweMessage` and
  `verifySiweMessage`.
- The immutable `@worldcoin/minikit-js` 2.0.3 source manifest at commit
  `440f35ca0184e24e8d04886f4b45158bb1d0f345` declares Node 16+, MIT,
  `abitype ^1.2.3`, a required React peer, and optional `viem`, `siwe`, and
  `wagmi` peers.
- The `/siwe` source imports `viem` and `viem/chains`, making viem necessary
  for this entrypoint even though the package manifest labels it optional.
- MiniKit first attempts local EOA signature recovery. Its EIP-1271 fallback
  creates a public World Chain client only when no client is supplied. The
  repository adapter therefore requires an explicitly injected client; G038
  additionally requires OS-level egress denial and injects a local mock.
- Historical MiniKit 1.8.0 lacks the current `/siwe` export and was rejected
  as the basis for this proposal.

Primary sources:

- https://docs.world.org/mini-apps/commands/wallet-auth
- https://github.com/worldcoin/minikit-js/blob/440f35ca0184e24e8d04886f4b45158bb1d0f345/packages/core/package.json
- https://github.com/worldcoin/minikit-js/blob/440f35ca0184e24e8d04886f4b45158bb1d0f345/packages/core/src/siwe-exports.ts
- https://github.com/worldcoin/minikit-js/blob/440f35ca0184e24e8d04886f4b45158bb1d0f345/packages/core/src/commands/wallet-auth/siwe.ts

## Controlled proposal generation

Official npm registry metadata was read with npm 10.9.8 and Node 22.23.1 on
Linux x64. `npm install --package-lock-only --ignore-scripts --audit=false
--fund=false` ran with isolated ephemeral `mktemp` caches. It created the
unapproved npm-v3 lock proposal only: no `node_modules`, lifecycle script,
package code, or package tarball was installed or executed. Static validation
does not repeat that acquisition and performs no npm, Node, network, or cache
operation.

A prior rejected draft ran read-only `npm cache ls`, found no MiniKit basis,
and was stopped before validation, commit, or DuckDB enqueue.

## Human Gate 0B decisions still required

The exact MiniKit 2.0.3, viem 2.45.3, React 18.3.1 peer satisfaction, direct
abitype 1.2.3 pin, and all 17 resolved packages remain proposals. Human
reviewers must stage and independently verify every exact tarball against both
the signed SHA-256 artifact record and lock SHA-512 SRI, review package
contents and lifecycle scripts, licenses, provenance/attestations, SBOM, and
vulnerability evidence, then sign the canonical Gate 0B selection with the
required external trust store. Cache presence alone is not trust.

The selection must also bind one reviewed, symlink-free, hermetic Linux
x86-64 Node 22.23.1 distribution archive and the exact Node and npm 10.9.8
member paths and digests. The approved verifier additionally requires an
operator-supplied SHA-256 trust anchor for the canonical Gate verifier and
verifies the exact captured approval bytes. This pins the Gate source bytes
used by an already-authenticated caller and closes approval-file swap races;
it does not authenticate the executing SIWE entrypoint or ambient Python
imports. G038 therefore remains explicitly fenced until an operator-controlled
Gate-first supervisor launcher authenticates the Gate, SIWE verifier, and
runtime entrypoint before any repository Python executes.

The future G038 contract creates and removes only its own child beneath an
operator-owned sandbox parent. It reuses the signed network namespace,
AppArmor, and egress-policy evidence before and after execution. Its receipt
does not claim that no socket syscall was attempted because no syscall monitor
is configured; it records that limitation and proves instead that no external
network route or successful external network action was available.
