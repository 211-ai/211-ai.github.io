# World-aid Gate-first launcher

Status: repository-side reference implementation; not deployed and not an
approval.

## Purpose and authority boundary

`scripts/world_aid_gate_first_launcher.py` implements the verify-only portion
of an operator-controlled bootstrap boundary for WORLDCOIN-G038, G039, and
G040. Its presence in the repository does not make it trusted. Repository
authors, agents, tests, task metadata, environment variables, and supervisor
lanes cannot grant it authority.

An authoritative installation requires all of the following:

1. An exact reviewed copy at
   `/usr/local/libexec/world-aid-gate-first-launcher`, owned by uid 0,
   non-writable, and below non-writable uid-0-owned directories.
2. A completed policy at `/etc/world-aid/gate-first-policy.json`, owned by uid
   0, read-only, single-linked, and below non-writable uid-0-owned directories.
   The template in `docs/governance/templates` is deliberately incomplete and
   must not be installed as policy.
3. Exact policy-bound digests for the launcher, a non-symlink isolated Python
   interpreter, `ssh-keygen`, Gate verifier, both restricted profile files, and
   both allowed-signers stores.
4. Invocation as `python -I -S -B` with effective uid 0 and exactly this
   environment:

   ```text
   LANG=C.UTF-8
   LC_ALL=C.UTF-8
   PATH=/usr/bin:/bin
   TZ=UTC
   ```

5. External network/process enforcement. The names of the reviewed AppArmor
   profile and network namespace are policy-bound. Merely setting environment
   flags with similar names is never evidence of enforcement.

The service definition, completed policy, trust stores, launcher attestation
private key, AppArmor profile, and network-namespace configuration are operator
assets and must not live in the agent-writable repository.

## Supported command

The launcher exposes only:

```text
world-aid-gate-first-launcher --verify-only
```

There are no command, goal, repository, policy, trust-store, profile, or runner
path CLI overrides. Unknown arguments, including `--run-selection`, fail.

The source copy normally fails even for `--verify-only`: its path differs from
the policy-attested external installation, it is not root-owned and
non-writable, and a development shell does not have the required interpreter
flags or clean environment. This refusal is intentional.

## Verify-only sequence

The installed launcher performs the following fail-closed sequence:

1. Validate its own `-I -S -B` flags, effective uid, and exact minimal
   environment before consulting repository state.
2. Read the fixed operator policy without following symlinks. Reject duplicate
   JSON keys, unknown fields, invalid paths, unsafe ownership or modes, hard
   links, and incomplete digests.
3. Verify the installed launcher, interpreter, `ssh-keygen`, Gate trust store,
   and their policy-bound digests through the operator filesystem boundary.
4. Open the fixed repository root without following any path-component
   symlinks. Capture the exact Gate verifier, selection approval, profile JSON,
   and profile DuckDB files through descriptor-relative `openat` operations.
5. Copy each input into a sealed Linux memfd. Validate the approval's exact
   G038-G040 scope, trust-store digest, and restricted profile pair before any
   captured repository Python executes.
6. Invoke the policy-bound interpreter with `-I -S -B` and the minimal
   environment. The child compiles the captured Gate verifier bytes and passes
   the captured approval bytes to `verify_approval`; it does not import the
   verifier by repository path. Stdout and stderr are drained incrementally
   under one aggregate policy byte limit; either overflow or timeout kills the
   entire child process group.
7. Require a strict Gate selection summary and revalidate every named
   repository input after verification.
8. Return a verify-only summary with
   `run_selection_authorized=false`,
   `live_actions_authorized=false`, and `offline=true`.

Verification does not toggle the old pytest fences, schedule a supervisor
lane, create a receipt, install a dependency, execute a runner, or authorize a
live World API or token action.

## Why run-selection remains disabled

The repository now provides reviewable runner implementations for all three
goals:

```text
scripts/run_world_aid_siwe_bootstrap.py
scripts/run_world_aid_zkp_bootstrap.py
scripts/run_world_aid_duckdb_bootstrap.py
```

Each runner pins immutable inputs, applies process/resource/output bounds,
cleans its temporary workspace, and publishes a no-replace result. They are
repository-side reference code, not an operator deployment, and this launcher
does not yet orchestrate them into one signed atomic run.

The policy template therefore has
`execution.run_selection_enabled=false` and an empty runner array. The policy
parser will not accept an enabled configuration unless it binds exactly those
three goals, paths, digests, `sealed-fd-json/v1` inputs, and
`stdout-json/v1` outputs. Even then, this revision has no run-selection CLI;
execution requires a separately reviewed implementation of sandbox setup,
cgroup/process-group cleanup, immutable snapshot injection, transactional
aggregate publication, signing, and complete partial-failure cleanup.

The generic `bundle_supervisor` is not a substitute. It imports repository
modules before Gate verification, inherits ambient environment state, rereads
mutable profiles, and executes implementation commands. G038-G040 must remain
outside its normal execution lanes.

## Immutable run receipts

`scripts/verify_world_aid_gate_first_receipt.py` defines the consumer-side
contract for a future external runner. A successful run is one direct child of
the policy-fixed receipt root:

```text
<receipt-root>/<run-id>/
  receipt.json
  receipt.sshsig
  goals/WORLDCOIN-G038.json
  goals/WORLDCOIN-G039.json
  goals/WORLDCOIN-G040.json
```

Every JSON file uses canonical, sorted, compact UTF-8 JSON ending in one
newline. Files and directories are uid-0 owned, non-writable, non-symlink, and
single-linked where applicable. Publication must construct a fresh staging
directory, fsync its files and directories, and atomically rename it to a
previously absent run id only after all three goals pass.

Each common goal-result file contains an exact four-field evidence envelope:
the native runner receipt, its canonical SHA-256 digest, the launcher-bound
execution-plan digest, and the external network-boundary-attestation digest.
The receipt verifier applies a goal-specific strict schema to the native
receipt. It rejects generic nonempty evidence, schema or authorization drift,
non-reproducible ZKP output, incomplete SIWE dual-path evidence, incomplete
DuckDB checks/cleanup/deny settings, and plan or boundary drift. G038's legacy
v2 native receipt does not contain plan and attestation fields; those two
values remain separately bound by the launcher-signed common envelope so that
the Gate-compatible native schema is not silently changed.

The aggregate `world-aid-gate-first-run-receipt/v1` binds:

- the exact selection approval digest, record id, and reviewed root commit;
- launcher, policy, Python, and Gate-verifier digests;
- the reviewed AppArmor profile, network namespace, clean environment, and
  offline boundary result;
- all three ordered goal ids, exact runner digests, result paths, and result
  digests; and
- start/completion timestamps and the absence of live-action authority.

The aggregate bytes are signed using OpenSSH namespace
`world-aid-gate-first-launch-v1`. The verifier reduces the policy-fixed
allowed-signers store to the one exact identity, Ed25519 key, and SHA256
fingerprint before calling the policy-bound `ssh-keygen`. A valid signature
from another key listed for the identity is insufficient.

The verifier rejects a passed receipt while
`run_selection_enabled=false`. This prevents synthetic or prematurely created
receipts from unblocking supervisor dependencies.

## Operator deployment review

Before any deployment proposal can be approved, operators must separately
review and record:

- immutable installation and package provenance for the launcher and Python;
- exact Gate and receipt signer public keys and private-key custody;
- dedicated G038-G040 runner protocols and their policy digests;
- AppArmor, mount, user, cgroup, resource, output, timeout, and offline network
  enforcement;
- atomic receipt publication and launcher-held signing credentials;
- receipt replay/run-id handling and supervisor-side external-authority task
  settlement; and
- adversarial tests for symlink/hard-link replacement, verifier and approval
  swaps, environment injection, wrong-key signatures, child/grandchild escape,
  partial failure, concurrent publication, and receipt tampering.

The independently administered deployment record uses
`world-aid-gate-first-deployment-conformance-attestation/v1`. Its schema and
deliberately non-conformant pending template live under
`docs/schemas/world_aid/` and `docs/governance/templates/`. A completed
attestation is stored at the canonical Gate-evidence path and becomes
authoritative only when its exact digest is bound by the independent
operator's signature on the Gate 0B transition record.

Completing those reviews requires a new human-signed Gate record. This
reference implementation neither supplies nor implies that approval.

Gate 0B selection and launch approvals use their v2 schemas and v2 OpenSSH
namespaces. The signed `execution_boundary` binds the external operator-policy
and deployment-attestation digests plus the exact reviewed launcher, Gate
verifier, receipt verifier, selection-profile builder, and runner digests. A
v1 approval cannot authorize this protocol.
