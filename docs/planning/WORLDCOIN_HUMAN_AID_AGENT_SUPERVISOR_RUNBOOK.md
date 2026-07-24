# Worldcoin Human-Aid Agent-Supervisor Runbook

## Purpose

This runbook turns
`docs/planning/WORLDCOIN_HUMAN_AID_OBJECTIVE_HEAP.md` into isolated,
dependency-aware implementation lanes for the `ipfs_accelerate_py` agent
supervisor.

The intended system keeps five decisions separate:

1. wallet ownership and authentication;
2. optional World ID proof of human;
3. document-issuer trust and private document claims;
4. program-specific eligibility proven with a zero-knowledge proof; and
5. provider authorization, WLD disbursement, and World Chain finality.

World ID is optional anti-abuse evidence. It is not login, document
verification, program eligibility, or authority to transfer funds. Wallet
ownership must use a separately verified wallet-authentication flow. Eligibility
must be evaluated against an application-owned, versioned policy and proven
without disclosing the source documents.

## Start only the reviewed wave

Do **not** run the full implementation launch until humans have reviewed:

- the implementation plan and objective heap;
- the generated todo board and every dependency;
- the deterministic preflight output;
- the bundle conflict surfaces and validation commands;
- privacy, security, accessibility, legal, and program-policy boundaries; and
- the human approval gates in this runbook.

Generating a board and running a non-starting bundle dry run are safe planning
actions. The separately named Gate 0A bootstrap-audit wave may be launched
before offline dependencies exist because it contains exactly G002, is
read-only with respect to existing application code and external state, and is
mechanically limited to an audit report, two machine-readable audit artifacts,
and its contract test. It may not install packages, run a ZKP toolchain, start
or pull a database/container, or execute an external adapter.

A command containing `--start` launches lane processes. A command containing
both `--start` and `--implement` authorizes only the repository work on that
reviewed board; it never authorizes a World API call, a chain broadcast, or a
token transfer. The Gate 0A and Gate 0B boards use different task prefixes,
state databases, logs, manifests, and worktrees.

## Non-negotiable safety boundaries

Autonomous lanes must obey all of the following:

- World ID proof of human remains optional. A person who cannot or chooses not
  to use it must have a documented, accessible human-review path.
- World ID must not be used as a login substitute or as proof of benefit
  eligibility. Wallet ownership is verified separately.
- No autonomous decision may deny essential services, housing, public benefits,
  or an appeal. The software may validate a proof or route a case to review; a
  responsible human owns adverse decisions and overrides.
- Raw documents, document images, extracted PII, exact eligibility reasons,
  homelessness status, World ID proof payloads, nullifiers, session identifiers,
  wallet-to-person mappings, and provider notes must not be placed on-chain,
  written to public IPFS, included in fixtures, or exposed in logs.
- A document-profile or simulated proof receipt is never sufficient to
  authorize funds. Money-moving code must accept only the production eligibility
  proof type, policy version, trusted issuer set, current revocation root,
  recipient-wallet binding, and freshness window required by the reviewed
  protocol.
- Public/on-chain data is limited to the WLD transfer and, only if required by
  the reviewed protocol, an opaque, randomized claim commitment. Do not label a
  recipient as homeless or encode a document hash on-chain.
- RP signing keys, API keys, treasury keys, and private wallet keys remain
  backend-only. They must come from approved secret references or managed
  HSM/MPC/multisig custody, never source control, generated artifacts, prompts,
  frontend variables, or supervisor logs.
- Tests use deterministic fixtures, fake transports, a local chain, and
  synthetic identities. Tests must not call World staging, World production,
  a public RPC, a block explorer, or a live indexer.
- `WORLD_ID_ENABLED=0` is the existing default for World ID. New disbursement
  work must add and test fail-closed `WORLD_AID_EXTERNAL_CALLS_ENABLED=0` and
  `WORLD_AID_WLD_TRANSFERS_ENABLED=0` controls before any adapter can make a
  remote call or sign/broadcast a transaction.
- Those environment controls are application feature flags, not a network
  sandbox. They do not prevent DNS resolution, socket creation, subprocess
  egress, or direct use of an unguarded client.
- Before Gate 0A or Gate 0B, the implementation host or container must apply a reviewed,
  default-deny egress policy. Its narrow allowlist may contain only the exact
  implementation-provider control-plane destinations and local fixture
  endpoints required for the run; World endpoints, public RPCs, block
  explorers, live indexers, remote IPFS gateways, Hugging Face, and treasury
  infrastructure remain denied.
- Before Gate 0A or Gate 0B, a deterministic network-spy/deny fixture must fail tests on
  unexpected DNS, socket, HTTP, WebSocket, RPC, IPFS, or transaction-submission
  attempts. The launch environment must contain no live World, wallet, issuer,
  recipient, provider, RPC, indexer, IPFS, Hugging Face, treasury, HSM, MPC, or
  signing credentials.
- The transfer control must default to disabled when absent, malformed, or
  contradictory. Enabling external reads must not implicitly enable writes.
- No task may turn either live-action control on, populate a live secret, fund
  an account, approve a token allowance, deploy a contract, or broadcast a
  transaction.
- Staging and production actions require the explicit, recorded human gates
  below. Testnet tokens are still transfers and require the staging transfer
  gate.
- Every payout intent is idempotent and binds provider, program, benefit period,
  policy, eligibility nullifier/commitment, recipient address, chain, token,
  exact base-unit amount, and nonce. Reconciliation must verify the successful
  receipt and matching ERC-20 `Transfer` log, not merely a submitted hash.
- A reorg, timeout, provider error, ambiguous receipt, stale eligibility proof,
  expired credential, or revocation uncertainty fails closed and enters human
  review. It must not trigger an automatic duplicate payment.
- Preserve a non-digital/manual path for people without a compatible phone,
  World App, stable connectivity, or accessible biometric enrollment.

## Human-owned approval gates

Supervisor agents may prepare evidence for a gate. They may not grant, forge,
infer, or self-approve one.

### Gate 0A: bootstrap-audit approval

This is the only implementation wave allowed before dependencies are reviewed
and pre-staged. It contains exactly `WORLDCOIN-G002`. Required before its
command containing `--start`:

- the product owner/repository maintainer approves G002's report, artifact, and
  test paths and confirms unrelated dirty work is preserved;
- deterministic generation produces exactly one task whose `Goal id` is
  `WORLDCOIN-G002`, and its TODO, DAG, and bundle CID sets agree;
- the G002 acceptance text prohibiting downloads, network calls, installs,
  container activity, toolchain execution, secret lookup, and application-code
  mutation is present in the generated task;
- the implementation environment has no World, wallet, recipient, provider,
  RPC, treasury, HSM/MPC, signing, IPFS, Hugging Face, npm-registry, container
  registry, or package-index credentials;
- the reviewed egress boundary permits only the implementation-provider
  control plane and denies World, RPC, registry, indexer, IPFS, and Hugging
  Face destinations;
- the one-task deterministic preflight and no-start dry run pass; and
- the launch uses one lane, one restart at most, the live-feature-disabled
  environment, and the dedicated `WORLDCOIN-BOOTSTRAP-` state paths below.

G002 may inventory existing files, installed commands, images, and caches
without mutating them. Its `offline-bootstrap-proposal.json` is advisory and
cannot approve a package, image, binary, license, or vulnerability exception.

### Gate 0B: two-phase offline selection and implementation-board approval

Gate 0B is deliberately split so agents can prepare and execute verifiers
without circularly approving their own inputs.

#### Gate 0B preparation

Before any Gate 0B signature, a separately reviewed preparation board may
contain the read-only G002 audit root plus only G037, G041, and G042. The
preparation goals create non-executing SIWE, ZKP, and DuckDB proposals and
fail-closed verifier code. Their validation may read
repository text and installed distribution metadata, but it may not install or
execute packages/toolchains, import DuckDB, create a database, build a circuit,
start a container, access a registry, mutate a cache, or claim approval.

#### Gate 0B-selection

The current blocked G038-G040 review profile is intentionally non-signable.
The selection verifier requires a nonempty execution profile containing the
exact selected goals and therefore must reject this empty review profile. Do
not create or sign a Gate 0B-selection record against it.

Before a future detached-signature-verified selection record may be created,
humans must accept an operator-controlled Gate-first launcher, governance must
transition the exact goals out of `blocked`, and the board, profiles, and
preflight receipt must be freshly regenerated and reviewed. That future record
must bind:

- product-owner approval of preparation scope and priority;
- security/privacy approval of data boundaries and the threat model;
- program-policy confirmation that optional proof of human remains separate
  from eligibility;
- accessibility confirmation of the manual and non-World-ID fallback;
- repository-maintainer approval of the preparation board, DAG, conflict plan,
  verifier code, and worktree surfaces;
- exact npm versions, integrity values, lifecycle scripts, licenses,
  provenance, transitive SBOM, vulnerability dispositions, human-produced
  lockfile, and read-only pre-staged tarball closure;
- the selected native ZKP backend, architecture, version, checksum-pinned
  binary/container, licenses, provenance, SBOM, locked smoke inputs,
  deterministic flags, resource bounds, and explicit statement that smoke or
  developer-generated setup material is not production trust;
- exact Python and DuckDB wheel names, hashes, CPython ABI/platform, licenses,
  provenance, SBOM, vulnerability dispositions, and read-only wheelhouse;
- the DuckDB single-host, exactly-one-writer service topology from
  `docs/adr/WORLD_AID_DUCKDB_STORAGE_ADR.md`, including authenticated local
  clients, local filesystem paths, extension autoinstall/autoload and external
  access disabled, application-layer envelope encryption, encrypted volume,
  backup/restore, and the prohibition on direct, multi-process, multi-host, or
  shared-filesystem writers;
- the externally enforced OS/container default-deny egress policy and its exact
  implementation-control-plane/local-fixture allowlist; and
- verification that the restricted worker environment has no live secrets,
  signing material, production credentials, or treasury access.

Gate 0B-selection authorizes only the exact future isolated, offline
G038-G040 execution profile it binds. It never authorizes the current blocked
review profile or the full implementation board. The current review-only
profile can never be promoted, edited in place, or used as a signature target.

#### Gate 0B-launch

Required before the full implementation command containing `--start`:

- the future launcher/governance transition/regeneration workflow for
  G038-G040 has completed and the current blocked review profile has not been
  reused or edited;
- every product, security/privacy, program-policy, accessibility, dependency,
  and repository-maintainer decision above remains current;
- successful immutable G038, G039, and G040 receipts match the selection
  record exactly;
- the deterministic network-spy/deny fixture passes and its deliberate egress
  canary proves that an unexpected request is blocked and reported;
- security verifies the externally enforced egress receipt and absence of live
  secrets again for the launch environment;
- the repository maintainer approves the final generated board, dependency
  DAG, conflict plan, validation commands, and worktree surfaces; and
- the standalone generated-board verifier, deterministic preflight, and
  non-starting bundle dry run pass against the exact immutable generated root.

Store actual human records only under
`data/worldcoin_human_aid/approvals/gate-0b-selection/` and
`data/worldcoin_human_aid/approvals/gate-0b-launch/`, outside generated
supervisor state. Each record and detached signature must bind approver
identity, UTC time, reviewed root and submodule commits, objective-heap,
implementation-plan, runbook, generated-board, graph, bundle-index and
preflight digests, exact scope, allowed writes/destinations, disabled live
features, exceptions, trust-store digest, and expiration. Gate 0B-launch also
binds Gate 0B-selection and all offline, egress, no-secret, preflight, and dry
run receipts.

Templates under `docs/governance/templates/` are intentionally unsigned and
invalid as approval. Verify completed records and their detached OpenSSH
signatures with `scripts/verify_world_aid_gate_0b.py`; an agent-created record,
identity string, template, fixture, or passing technical test is never human
authorization. Do not place secrets or recipient data in a record or receipt.

The operator must supply a reviewed, read-only OpenSSH `allowed_signers` file
outside generated supervisor state. Verify each phase from the repository root;
both commands are offline and fail closed on an absent record, an untrusted or
missing role, a stale approval, digest drift, an unsafe DuckDB topology, or
scope drift:

```bash
test -n "${WORLD_AID_ALLOWED_SIGNERS:-}"
test -f "$WORLD_AID_ALLOWED_SIGNERS"

PYTHONDONTWRITEBYTECODE=1 \
python scripts/verify_world_aid_gate_0b.py \
  --phase selection \
  --approval data/worldcoin_human_aid/approvals/gate-0b-selection/approval.json \
  --allowed-signers "$WORLD_AID_ALLOWED_SIGNERS" \
  --repo-root . \
  --offline

PYTHONDONTWRITEBYTECODE=1 \
python scripts/verify_world_aid_gate_0b.py \
  --phase launch \
  --approval data/worldcoin_human_aid/approvals/gate-0b-launch/approval.json \
  --allowed-signers "$WORLD_AID_ALLOWED_SIGNERS" \
  --repo-root . \
  --offline
```

Do not run the selection verifier against the current G038/G039/G040 blocked
projection except as a negative test: it must reject that empty execution
profile. There is no restricted execution wave in the current profiles. A
future wave requires the launcher, governance transition, fresh regeneration,
and fresh signatures described above. Run the launch verifier immediately
before any full-board command containing `--start`; launch verification also
re-verifies the exact selection record it binds.

Generate each phase's bounded network-deny receipt inside the reviewed
AppArmor profile and a fresh, loopback-only network namespace. Capture the host
namespace before `unshare`; the receipt fails unless the inner namespace is
different, has no external route, and the single RFC 5737 TEST-NET connection
is denied with a policy-consistent error. Set `WORLD_AID_GATE_PHASE` to exactly
`selection` or `launch`; the tool refuses to overwrite earlier evidence:

```bash
set -euo pipefail
case "${WORLD_AID_GATE_PHASE:?set selection or launch}" in
  selection|launch) ;;
  *) echo "WORLD_AID_GATE_PHASE must be selection or launch" >&2; exit 1 ;;
esac

REPOSITORY_ROOT="$(git rev-parse --show-toplevel)"
WORLD_AID_HOST_NETNS="$(readlink /proc/self/ns/net)"
WORLD_AID_CANARY_RECEIPT="$REPOSITORY_ROOT/data/worldcoin_human_aid/gate_evidence/gate-0b-$WORLD_AID_GATE_PHASE/network-deny-canary.json"
test ! -e "$WORLD_AID_CANARY_RECEIPT"

aa-exec -p linux-sandbox -- unshare -Urn \
env -i \
  PATH=/usr/bin:/bin \
  PYTHONDONTWRITEBYTECODE=1 \
  WORLD_ID_ENABLED=0 \
  WORLD_AID_EXTERNAL_CALLS_ENABLED=0 \
  WORLD_AID_WLD_TRANSFERS_ENABLED=0 \
  REPOSITORY_ROOT="$REPOSITORY_ROOT" \
  WORLD_AID_CANARY_RECEIPT="$WORLD_AID_CANARY_RECEIPT" \
  WORLD_AID_HOST_NETNS="$WORLD_AID_HOST_NETNS" \
/bin/bash -ceu '
  WORLD_AID_REVIEWED_NETNS="$(readlink /proc/self/ns/net)"
  exec /usr/bin/python3 "$REPOSITORY_ROOT/scripts/run_world_aid_egress_canary.py" \
    --receipt "$WORLD_AID_CANARY_RECEIPT" \
    --inside-reviewed-deny-sandbox \
    --offline \
    --expected-apparmor-profile linux-sandbox \
    --expected-network-namespace "$WORLD_AID_REVIEWED_NETNS" \
    --host-network-namespace "$WORLD_AID_HOST_NETNS"
'
```

This receipt is technical evidence, not approval. The phase still requires
the separate externally produced egress-policy and no-live-secrets
attestations named by its Gate 0B template.

### Gate 1: World staging API approval

Required before the first call to a World staging API:

- Gate 0B-launch is current;
- a security reviewer has approved the exact app ID, RP ID, action allowlist,
  signal/claim-binding format, redirect/origin allowlist, secret references,
  retention policy, replay controls, and redacted telemetry;
- a privacy reviewer has approved the synthetic/test-person data set;
- an operator has confirmed staging-only endpoints and test accounts; and
- the task is run manually with a bounded request count and archived redacted
  receipts.

The autonomous supervisor remains stopped during this exercise. Agents may
consume the redacted result afterward.

### Gate 2: World Chain Sepolia or test-token transfer approval

Required before any testnet contract deployment, allowance, transaction, or WLD
test-token transfer:

- Gate 1 is current when World staging evidence is part of the test;
- treasury/security reviewers approve the exact chain ID, token contract,
  sender, recipient allowlist, maximum test amount, gas ceiling, and signer;
- an operator confirms that no mainnet key or mainnet asset is accessible;
- idempotency, replay, receipt/log reconciliation, reorg, and duplicate-payment
  tests pass locally; and
- a named human submits the bounded test transaction and records a redacted
  receipt.

Testnet activity is not an autonomous-agent validation command.

### Gate 3: production World verification approval

Required before production World ID, wallet-auth, Developer Portal, or related
API use:

- privacy, security, accessibility, legal/compliance, support, product, and
  program-policy reviews are signed;
- data minimization, retention/deletion, incident response, appeal, manual
  fallback, and account-recovery procedures are operational;
- RP/action configuration and wallet binding have independent security test
  evidence;
- legacy/migration behavior and replay semantics match the reviewed World API
  version; and
- a human change owner performs a bounded canary with rollback criteria.

Enabling production World verification does not authorize a token transfer.

### Gate 4: production WLD disbursement approval

Required for every production rollout and for each transfer policy:

- Gate 3 is current only when optional proof of human is used;
- the program owner approves the eligibility policy version, issuer trust list,
  revocation/freshness policy, benefit period, amount rule, and appeal path;
- legal/compliance reviewers approve the applicable geography, asset,
  disclosures, sanctions controls, tax/benefit interaction, and recordkeeping
  procedure;
- security and treasury owners approve audited code, chain ID, WLD contract,
  multisig/MPC/HSM policy, signer quorum, spend caps, recipient-binding checks,
  pause procedure, monitoring, and reconciliation;
- a human reviewer confirms the eligibility proof, recipient wallet ownership,
  provider authority, amount, and idempotency key;
- two authorized humans approve and submit according to the treasury policy;
  and
- the autonomous supervisor is not a signer and cannot access signing material.

Production transfer commands are intentionally not included in this runbook.

## Generated artifact layout

Objective-generation outputs use an immutable directory below this
repository-local root:

```text
data/worldcoin_human_aid/agent_supervisor/regenerations/<review-id>/
```

The selected directory is exported as `WORLD_AID_GENERATED_ROOT`. Expected
paths relative to it are:

| Path | Purpose |
| --- | --- |
| `WORLDCOIN_HUMAN_AID_TODO.md` | Generated supervisor taskboard |
| `discovery/` | Gap evidence and discovery receipts |
| `objective_bundles/index.json` | Canonical bundle/dependency/conflict index |
| `objective_bundles/index.duckdb` | Queryable projection of bundle planning data |
| `objective_bundles/*.todo.md` | Bundle-local task shards |
| `objective_bundles/todo_vector_index.json` | Task/vector/AST planning index |
| `objective_datasets/` | Persisted objective/AST planning datasets |
| `objective_graph.json` | Goal graph and heap schedule |
| `plan_evaluations.json` | Deterministic plan-selection evidence |
| `analysis_escalation.json` | Bounded-analysis escalation evidence |
| `objective_generation.json` | Bounded-work generation receipt |
| `lane_state/` | Per-lane durable state, operational taskboard copies, and source-digest bindings |
| `logs/` | Redacted supervisor/lane logs |
| `lane-manifest.json` | Planned or live lane projection |
| `scheduler-metrics.json` | Scheduler metrics projection |
| `coordination.duckdb` | Durable supervisor claims, leases, and reconciliation state |

Generated planning artifacts must not contain World secrets, recipient data,
raw proof payloads, private document data, or treasury material. Human-authored
approval records live outside this generated root under
`data/worldcoin_human_aid/approvals/`. That directory is a reference/evidence
location, not an authorization mechanism by itself.

The supervisor's `coordination.duckdb` is operational scheduler state. It is
not the World human-aid financial store and does not satisfy G033 or G040.
Those goals use the independently reviewed single-writer security boundary in
`docs/adr/WORLD_AID_DUCKDB_STORAGE_ADR.md`.

Bundle shards and the canonical generated TODO are immutable planning inputs.
Before a worker starts, the bundle supervisor verifies the planned shard
SHA-256 and copies it into that lane's state directory. Completion and
dependency-ready status transitions may update only this operational copy.
The adjacent `*_taskboard_input.json` record binds its source path and digest
to the runtime path; a missing, malformed, or mismatched binding is a hard
stop, and a restart must reuse rather than overwrite a bound runtime copy.

The first full objective/AST scan can be expensive and can materialize
multi-gigabyte snapshots; approximately 2.5 GB was observed during one scan of
this repository, but the size and runtime vary with the checked-out tree,
submodules, optional dataset backend, and prior cache. Before generation, check
available storage and review these cache paths rather than assuming an exact
cost:

```text
data/worldcoin_human_aid/agent_supervisor/objective_datasets/worldcoin-auto-objective-ast.jsonl
data/worldcoin_human_aid/agent_supervisor/objective_datasets/worldcoin-auto-objective-ast.manifest.json
data/worldcoin_human_aid/agent_supervisor/objective_datasets/worldcoin-auto-objective-ast.parquet
```

The JSONL snapshot is the authoritative fallback; parquet is optional. Preserve
and review a complete existing snapshot so unchanged records can be reused by
blob/source hash. After each generation, inspect the manifest's parsed, reused,
deleted, invalidated, elapsed-time, and backend fields and confirm that its
paths belong to this board. Do not delete or substitute a cache merely to make
a scan appear faster, and do not treat a stale or partial cache as acceptance
evidence.

## Generate the objective taskboard

Run this from the repository root only after reviewing the source objective
heap. This uses the daemon's deterministic planner: it does not request
LLM-generated plan branches, submit bundles, or start workers.

First run the static heap/runbook and offline verifier contracts. These tests
are mandatory: they pin the exact 42-goal heap, 37 schedulable goals, blocked
G035/G036 human gates, blocked Gate-first execution goals G038-G040, force
list, and receipt/verifier behavior before an expensive scan begins.

```bash
env \
  PYTHONDONTWRITEBYTECODE=1 \
  PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
  IPFS_ACCEL_SKIP_CORE=1 \
  IPFS_KIT_DISABLE=1 \
python -m pytest -q -s -p no:cacheprovider -c /dev/null \
  tests/test_worldcoin_human_aid_taskboard.py \
  tests/world_aid/test_generated_board_verifier.py \
  tests/world_aid/test_preflight_receipt.py
```

The daemon appends to an existing taskboard. Never regenerate into the
canonical or previously approved directory. Create a fresh immutable
repository-local root, do not seed it with old discovery files, and keep that
exact path for review and launch because discovery evidence records absolute
paths:

```bash
set -euo pipefail
REPOSITORY_ROOT="$(git rev-parse --show-toplevel)"
test "$PWD" = "$REPOSITORY_ROOT" || {
  echo "run from the reviewed repository root: $REPOSITORY_ROOT" >&2
  exit 1
}
test -z "$(git status --porcelain=v1 --untracked-files=all)" || {
  echo "refusing to generate from a dirty or partially untracked review tree" >&2
  exit 1
}
git diff --check
if git submodule status | grep -Eq '^-'; then
  echo "refusing to generate with an uninitialized top-level submodule" >&2
  exit 1
fi
if git submodule status --recursive | grep -Eq '^[+U]'; then
  echo "refusing to generate with a drifted or conflicted submodule" >&2
  exit 1
fi
git submodule foreach --recursive '
  test -z "$(git status --porcelain=v1 --untracked-files=all)" || {
    echo "refusing to generate with dirty submodule $displaypath" >&2
    exit 1
  }
'

mkdir -p "$REPOSITORY_ROOT/data/worldcoin_human_aid/agent_supervisor/regenerations"
umask 077
WORLD_AID_GENERATED_ROOT="$(
  mktemp -d \
    "$REPOSITORY_ROOT/data/worldcoin_human_aid/agent_supervisor/regenerations/duckdb-v1.XXXXXX"
)"
WORLD_AID_MERGE_TARGET_BRANCH="$(git branch --show-current)"
test -n "$WORLD_AID_MERGE_TARGET_BRANCH" || {
  echo "refusing to launch from a detached HEAD; create a reviewed execution branch" >&2
  exit 1
}
IPFS_ACCELERATE_DUCKDB_ONLY=1
export WORLD_AID_GENERATED_ROOT
export WORLD_AID_MERGE_TARGET_BRANCH
export IPFS_ACCELERATE_DUCKDB_ONLY
```

Keep `IPFS_ACCELERATE_DUCKDB_ONLY=1` exported for every generation, dry-run,
launch, inspection, and resume command in this runbook. It makes DuckDB the
only supervisor state backend and disables legacy SQLite discovery and
migration; this workflow has no PostgreSQL state dependency.

```bash
set -euo pipefail
: "${WORLD_AID_GENERATED_ROOT:?create and export a fresh regeneration root first}"
PYTHONDONTWRITEBYTECODE=1 python - <<'PY'
from pathlib import Path
import os

repo_root = Path.cwd().resolve()
allowed_parent = (
    repo_root / "data/worldcoin_human_aid/agent_supervisor/regenerations"
).resolve()
generated_root = Path(os.environ["WORLD_AID_GENERATED_ROOT"])
if generated_root.is_symlink():
    raise SystemExit("generated root must not be a symlink")
generated_root = generated_root.resolve()
if generated_root.parent != allowed_parent:
    raise SystemExit(
        f"generated root must be one direct child of {allowed_parent}: "
        f"{generated_root}"
    )
if not generated_root.is_dir():
    raise SystemExit(f"generated root is not a directory: {generated_root}")
if any(generated_root.iterdir()):
    raise SystemExit(f"generated root is not empty: {generated_root}")
PY

env \
  PYTHONDONTWRITEBYTECODE=1 \
  PYTHONHASHSEED=0 \
  LC_ALL=C.UTF-8 \
  TZ=UTC \
  IPFS_ACCEL_SKIP_CORE=1 \
  IPFS_KIT_DISABLE=1 \
  HF_HUB_OFFLINE=1 \
  HF_DATASETS_OFFLINE=1 \
  TRANSFORMERS_OFFLINE=1 \
  PYTHONPATH=ipfs_accelerate_py \
python -m ipfs_accelerate_py.agent_supervisor.objective_daemon \
  --repo-root . \
  --objective-path docs/planning/WORLDCOIN_HUMAN_AID_OBJECTIVE_HEAP.md \
  --todo-path "$WORLD_AID_GENERATED_ROOT/WORLDCOIN_HUMAN_AID_TODO.md" \
  --discovery-dir "$WORLD_AID_GENERATED_ROOT/discovery" \
  --bundle-dir "$WORLD_AID_GENERATED_ROOT/objective_bundles" \
  --dataset-dir "$WORLD_AID_GENERATED_ROOT/objective_datasets" \
  --graph-path "$WORLD_AID_GENERATED_ROOT/objective_graph.json" \
  --task-prefix WORLDCOIN-AUTO- \
  --objective-summary-prefix "Implement Worldcoin human-aid objective" \
  --discovery-output-path "$WORLD_AID_GENERATED_ROOT/discovery" \
  --plan-evaluation-path "$WORLD_AID_GENERATED_ROOT/plan_evaluations.json" \
  --analysis-escalation-path "$WORLD_AID_GENERATED_ROOT/analysis_escalation.json" \
  --objective-generation-path "$WORLD_AID_GENERATED_ROOT/objective_generation.json" \
  --max-findings 42 \
  --surplus-findings-per-goal 1 \
  --force-goal-id WORLDCOIN-G001 \
  --force-goal-id WORLDCOIN-G002 \
  --force-goal-id WORLDCOIN-G003 \
  --force-goal-id WORLDCOIN-G004 \
  --force-goal-id WORLDCOIN-G005 \
  --force-goal-id WORLDCOIN-G006 \
  --force-goal-id WORLDCOIN-G007 \
  --force-goal-id WORLDCOIN-G008 \
  --force-goal-id WORLDCOIN-G009 \
  --force-goal-id WORLDCOIN-G010 \
  --force-goal-id WORLDCOIN-G011 \
  --force-goal-id WORLDCOIN-G012 \
  --force-goal-id WORLDCOIN-G013 \
  --force-goal-id WORLDCOIN-G014 \
  --force-goal-id WORLDCOIN-G015 \
  --force-goal-id WORLDCOIN-G016 \
  --force-goal-id WORLDCOIN-G017 \
  --force-goal-id WORLDCOIN-G018 \
  --force-goal-id WORLDCOIN-G019 \
  --force-goal-id WORLDCOIN-G020 \
  --force-goal-id WORLDCOIN-G021 \
  --force-goal-id WORLDCOIN-G022 \
  --force-goal-id WORLDCOIN-G023 \
  --force-goal-id WORLDCOIN-G024 \
  --force-goal-id WORLDCOIN-G025 \
  --force-goal-id WORLDCOIN-G026 \
  --force-goal-id WORLDCOIN-G027 \
  --force-goal-id WORLDCOIN-G028 \
  --force-goal-id WORLDCOIN-G029 \
  --force-goal-id WORLDCOIN-G030 \
  --force-goal-id WORLDCOIN-G031 \
  --force-goal-id WORLDCOIN-G032 \
  --force-goal-id WORLDCOIN-G033 \
  --force-goal-id WORLDCOIN-G034 \
  --force-goal-id WORLDCOIN-G037 \
  --force-goal-id WORLDCOIN-G038 \
  --force-goal-id WORLDCOIN-G039 \
  --force-goal-id WORLDCOIN-G040 \
  --force-goal-id WORLDCOIN-G041 \
  --force-goal-id WORLDCOIN-G042 \
  --no-reconcile-goal-completion
```

`--no-reconcile-goal-completion` prevents a new, cross-submodule safety program
from being closed by weak textual similarity to existing World ID code. Do not
add `--submit-bundles` during planning.

The objective daemon defines `--force-goal-id` with repeatable append semantics.
These explicit flags are required here because broad evidence matches can
otherwise suppress every finding and produce a zero-task board even though the
goals remain active. Whenever an active goal is added, add its exact ID to this
list before regenerating. A forced rescan does not weaken acceptance criteria,
grant a human gate, submit a bundle, or start a worker. Never add
`--repeat-existing`, `--submit-bundles`, `--generate-plan-branches`, or
`--start` to this generation command.

The forced list intentionally omits G035 and G036, which are
supervisor-terminal `blocked` human gates. It includes G038, G039, and G040
only so the no-submit, no-start planning command can materialize the exact
selection-review profiles; those three runtime goals remain terminally
`blocked` and unschedulable. A signed approval or repository-controlled
environment flag is necessary but cannot open their literal-false runtime
fences. Each runtime requires an operator-controlled Gate-first supervisor
launcher that authenticates the exact selection-bound entrypoint and verifier
before repository Python runs, enforces descriptor-backed immutable inputs,
network and registry denial, bounded process groups and output, and atomic
no-follow receipts. Only the named governance process may transition a blocked
goal after independently produced external evidence is reviewed; an
agent-created approval/evidence file, textual match, or completed dependency
cannot reopen one.

## Review the generated board

At minimum, inspect:

```text
docs/planning/WORLDCOIN_HUMAN_AID_OBJECTIVE_HEAP.md
$WORLD_AID_GENERATED_ROOT/WORLDCOIN_HUMAN_AID_TODO.md
$WORLD_AID_GENERATED_ROOT/objective_graph.json
$WORLD_AID_GENERATED_ROOT/objective_bundles/index.json
$WORLD_AID_GENERATED_ROOT/objective_bundles/todo_vector_index.json
$WORLD_AID_GENERATED_ROOT/objective_bundles/*.todo.md
$WORLD_AID_GENERATED_ROOT/discovery/
```

The review must confirm:

- all generated headers use `WORLDCOIN-AUTO-`;
- every task has bounded outputs, deterministic validation, and acceptance
  criteria;
- every source goal has nonempty `Acceptance criteria` and `Refinement`
  metadata, and every generated task has an explicit source `Goal id` whose
  complete source acceptance-criteria text is retained in generated
  `Acceptance` (case and whitespace formatting may normalize, but no criterion
  may be dropped);
- generated task, dependency-DAG, and bundle task ID/CID sets are identical;
  blocked human gates G035 and G036 appear in none of them, while G038-G040
  appear only as `blocked` review records and never as claimable work;
- dependency direction matches the objective heap;
- live World calls, chain broadcasts, contract deployment, allowance changes,
  and transfers are not validation commands;
- staging/production tasks are explicitly human-gated and cannot become
  claimable from a code-only dependency;
- test tasks use injected transports, synthetic identities, and local-chain
  fixtures;
- money-moving adapters depend on the fail-closed controls, production
  eligibility verifier, wallet binding, idempotency, custody, and reconciliation
  tasks;
- simulated proof receipts cannot satisfy a payout dependency;
- no task asks an agent to determine homelessness or make an adverse eligibility
  decision;
- conflict surfaces include the parent wallet code plus both
  `ipfs_accelerate_py` and `ipfs_datasets_py` where applicable; and
- generated artifacts contain no secret or private-data values.

## Deterministic dependency preflight

The following preflight is read-only, makes no network calls, and fails on
missing artifacts, malformed source goals or generated task blocks, lost
acceptance criteria, missing review-board records, review-only status or
scheduling-flag drift, claimable blocked tasks, malformed bundle entries,
dangling dependency CIDs, self-dependencies, dependency cycles, bundle tasks
absent from the dependency graph, or any CID the planner has classified as
invalid.

```bash
env \
  PYTHONDONTWRITEBYTECODE=1 \
  IPFS_ACCEL_SKIP_CORE=1 \
  IPFS_KIT_DISABLE=1 \
  HF_HUB_OFFLINE=1 \
  HF_DATASETS_OFFLINE=1 \
  TRANSFORMERS_OFFLINE=1 \
  PYTHONPATH=ipfs_accelerate_py \
python - <<'PY'
from collections import defaultdict, deque
from pathlib import Path
import json
import os
import re
import sys

from ipfs_accelerate_py.agent_supervisor.objective_graph import parse_goal_heap
from ipfs_accelerate_py.agent_supervisor.todo_vector_index import parse_todo_blocks

root = Path.cwd().resolve()
generated_root = os.environ.get("WORLD_AID_GENERATED_ROOT")
if not generated_root:
    raise SystemExit("WORLD_AID_GENERATED_ROOT must name the immutable reviewed root")
base = Path(generated_root).resolve()
allowed_parent = root / "data/worldcoin_human_aid/agent_supervisor/regenerations"
if allowed_parent not in base.parents:
    raise SystemExit(f"generated root escapes the approved regeneration parent: {base}")
objective_path = root / "docs/planning/WORLDCOIN_HUMAN_AID_OBJECTIVE_HEAP.md"
todo_path = base / "WORLDCOIN_HUMAN_AID_TODO.md"
graph_path = base / "objective_graph.json"
index_path = base / "objective_bundles/index.json"
required = [
    objective_path,
    todo_path,
    graph_path,
    index_path,
    base / "objective_bundles/todo_vector_index.json",
]
problems = [f"missing required artifact: {path.relative_to(root)}"
            for path in required if not path.is_file()]
if problems:
    print("\n".join(problems), file=sys.stderr)
    raise SystemExit(1)

def load_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"invalid JSON {path.relative_to(root)}: {exc}", file=sys.stderr)
        raise SystemExit(1)

source_goals = parse_goal_heap(objective_path.read_text(encoding="utf-8"))
if not source_goals:
    problems.append("objective heap contains no parseable source goals")

source_goals_by_id = {}
source_acceptance = {}
schedulable_goal_ids = set()
blocked_goal_ids = set()
for goal in source_goals:
    if goal.goal_id in source_goals_by_id:
        problems.append(f"objective heap has duplicate goal ID {goal.goal_id!r}")
    source_goals_by_id[goal.goal_id] = goal

    acceptance_criteria = str(
        goal.fields.get("acceptance_criteria") or ""
    ).strip()
    refinement = str(goal.fields.get("refinement") or "").strip()
    if not acceptance_criteria:
        problems.append(
            f"source goal {goal.goal_id!r} has empty Acceptance criteria"
        )
    else:
        source_acceptance[goal.goal_id] = acceptance_criteria
    if not refinement:
        problems.append(f"source goal {goal.goal_id!r} has empty Refinement")
    if goal.is_schedulable:
        schedulable_goal_ids.add(goal.goal_id)
    if goal.status == "blocked":
        blocked_goal_ids.add(goal.goal_id)

never_materialized_goal_ids = {"WORLDCOIN-G035", "WORLDCOIN-G036"}
review_only_goal_ids = {
    "WORLDCOIN-G038",
    "WORLDCOIN-G039",
    "WORLDCOIN-G040",
}
expected_blocked_goal_ids = never_materialized_goal_ids | review_only_goal_ids
if blocked_goal_ids != expected_blocked_goal_ids:
    problems.append(
        "source blocked-goal set differs from the reviewed human/review gates: "
        f"expected={sorted(expected_blocked_goal_ids)}, "
        f"actual={sorted(blocked_goal_ids)}"
    )
review_board_goal_ids = schedulable_goal_ids | review_only_goal_ids
if len(schedulable_goal_ids) != 37 or len(review_board_goal_ids) != 40:
    problems.append(
        "reviewed goal counts drifted: "
        f"schedulable={len(schedulable_goal_ids)}, "
        f"review_board={len(review_board_goal_ids)}"
    )

def normalized_acceptance(value):
    return " ".join(str(value or "").split()).casefold()

def check_review_flags(record, location, *, json_booleans):
    for field, expected in (("is_schedulable", False), ("review_only", True)):
        if field not in record:
            problems.append(f"{location} is missing review-only flag {field!r}")
            continue
        value = record[field]
        if json_booleans:
            valid = isinstance(value, bool) and value is expected
        else:
            valid = (
                isinstance(value, str)
                and value.strip().casefold() == str(expected).lower()
            )
        if not valid:
            problems.append(
                f"{location} has invalid review-only flag {field!r}: {value!r}"
            )

todo_text = todo_path.read_text(encoding="utf-8")
headers = re.findall(r"^## (WORLDCOIN-AUTO-[A-Za-z0-9._-]+)\b",
                     todo_text, flags=re.MULTILINE)
if not headers:
    problems.append("generated todo has no WORLDCOIN-AUTO- task headers")
if len(headers) != len(set(headers)):
    problems.append("generated todo has duplicate task IDs")

task_blocks = parse_todo_blocks(
    todo_text,
    task_header_prefix="WORLDCOIN-AUTO-",
)
if len(task_blocks) != len(headers):
    problems.append(
        "not every WORLDCOIN-AUTO header parsed as exactly one generated task "
        f"block: {len(headers)} headers, {len(task_blocks)} blocks"
    )
if len(task_blocks) != 40:
    problems.append(
        f"canonical review board must contain exactly 40 records, got {len(task_blocks)}"
    )

generated_goal_ids = set()
todo_task_ids = set()
todo_task_cids = set()
review_only_task_cids = set()
for task_id, _title, source_line, fields in task_blocks:
    goal_id = str(fields.get("goal_id") or "").strip()
    task_status = str(fields.get("status") or "").strip().lower().replace("-", "_")
    acceptance = str(fields.get("acceptance") or "").strip()
    location = f"{task_id} at generated todo line {source_line}"
    todo_task_ids.add(task_id)
    task_cid = str(fields.get("canonical_task_cid") or fields.get("task_cid") or "").strip()
    if not task_cid:
        problems.append(f"{location} has empty canonical task CID")
    else:
        todo_task_cids.add(task_cid)
    if not acceptance:
        problems.append(f"{location} has empty - Acceptance metadata")
    if not goal_id:
        problems.append(f"{location} has empty - Goal id metadata")
        continue
    if not re.fullmatch(r"WORLDCOIN-G[0-9]{3}", goal_id):
        problems.append(f"{location} has malformed - Goal id {goal_id!r}")
        continue
    if goal_id not in source_goals_by_id:
        problems.append(f"{location} references unknown source goal {goal_id!r}")
        continue
    if goal_id in never_materialized_goal_ids:
        problems.append(
            f"{location} illegally materializes blocked human gate {goal_id!r}"
        )
        continue
    if goal_id in review_only_goal_ids:
        if task_status != "blocked":
            problems.append(
                f"{location} review-only task is not status blocked: "
                f"{task_status!r}"
            )
        check_review_flags(fields, location, json_booleans=False)
        if task_cid:
            review_only_task_cids.add(task_cid)

    generated_goal_ids.add(goal_id)
    exact_criteria = source_acceptance.get(goal_id, "")
    if (
        exact_criteria
        and normalized_acceptance(exact_criteria)
        not in normalized_acceptance(acceptance)
    ):
        problems.append(
            f"{location} does not carry the complete {goal_id} source "
            "Acceptance criteria text in its - Acceptance metadata after "
            "case/whitespace normalization"
        )

missing_review_goal_tasks = sorted(review_board_goal_ids - generated_goal_ids)
if missing_review_goal_tasks:
    problems.append(
        "review-board source goals have no generated task blocks: "
        f"{missing_review_goal_tasks}"
    )
unexpected_goal_tasks = sorted(generated_goal_ids - review_board_goal_ids)
if unexpected_goal_tasks:
    problems.append(
        "generated task blocks reference goals outside the 40-record review universe: "
        f"{unexpected_goal_tasks}"
    )

objective_graph = load_json(graph_path)
if objective_graph.get("schema") != "ipfs_accelerate_py.agent_supervisor.objective_graph":
    problems.append("unexpected objective graph schema")
if not objective_graph.get("goals"):
    problems.append("objective graph contains no goals")

index = load_json(index_path)
bundles = index.get("bundles")
if not isinstance(bundles, dict) or not bundles:
    problems.append("bundle index contains no bundles")
    bundles = {}

planning = index.get("task_planning_graph") or {}
dag_candidates = {
    "dependency_dag": index.get("dependency_dag"),
    "task_dependency_graph": index.get("task_dependency_graph"),
    "task_planning_graph.task_dependency_graph":
        planning.get("task_dependency_graph") if isinstance(planning, dict) else None,
}
dags = {name: dag for name, dag in dag_candidates.items()
        if isinstance(dag, dict)}
if not dags:
    problems.append("bundle index contains no dependency DAG")

canonical_nodes = set()
canonical_dag_task_ids = set()
for name, dag in dags.items():
    nodes_map = dag.get("nodes")
    if not isinstance(nodes_map, dict) or not nodes_map:
        problems.append(f"{name} contains no nodes")
        continue
    nodes = set(nodes_map)
    if not canonical_nodes:
        canonical_nodes = nodes
        canonical_dag_task_ids = {
            str(record.get("task_id") or "")
            for record in nodes_map.values()
            if isinstance(record, dict) and str(record.get("task_id") or "")
        }
    elif nodes != canonical_nodes:
        problems.append(
            f"{name} node CIDs differ from the canonical DAG projection: "
            f"missing={sorted(canonical_nodes - nodes)}, "
            f"extra={sorted(nodes - canonical_nodes)}"
        )

    for cid, record in nodes_map.items():
        if not isinstance(record, dict):
            continue
        node_goal_id = str(record.get("goal_id") or "").strip()
        node_status = str(record.get("status") or "").strip().lower().replace("-", "_")
        if node_goal_id in never_materialized_goal_ids:
            problems.append(
                f"{name} node {cid!r} illegally references blocked human gate "
                f"{node_goal_id!r}"
            )
        if node_goal_id in review_only_goal_ids and node_status != "blocked":
            problems.append(
                f"{name} node {cid!r} review-only status is not blocked: "
                f"{node_status!r}"
            )
        if node_goal_id in review_only_goal_ids:
            metadata = record.get("metadata")
            if isinstance(metadata, dict):
                check_review_flags(
                    metadata,
                    f"{name} node {cid!r} metadata",
                    json_booleans=True,
                )
            else:
                problems.append(
                    f"{name} node {cid!r} has no review-only metadata object"
                )

    invalid = sorted(set(dag.get("invalid_task_cids") or []))
    if invalid:
        problems.append(f"{name} has invalid dependency CIDs: {invalid}")

    adjacency = defaultdict(set)
    indegree = {cid: 0 for cid in nodes}
    for position, edge in enumerate(dag.get("edges") or []):
        if not isinstance(edge, dict):
            problems.append(f"{name} edge {position} is not an object")
            continue
        source = str(edge.get("source_task_cid") or "")
        target = str(edge.get("target_task_cid") or "")
        if source not in nodes:
            problems.append(f"{name} edge {position} has dangling source CID {source!r}")
        if target not in nodes:
            problems.append(f"{name} edge {position} has dangling target CID {target!r}")
        if source and source == target:
            problems.append(f"{name} edge {position} is a self-dependency: {source}")
        if source in nodes and target in nodes and target not in adjacency[source]:
            adjacency[source].add(target)
            indegree[target] += 1

    ready = deque(sorted(cid for cid, degree in indegree.items() if degree == 0))
    visited = 0
    while ready:
        cid = ready.popleft()
        visited += 1
        for target in sorted(adjacency[cid]):
            indegree[target] -= 1
            if indegree[target] == 0:
                ready.append(target)
    if visited != len(nodes):
        cyclic = sorted(cid for cid, degree in indegree.items() if degree > 0)
        problems.append(f"{name} contains a dependency cycle involving {cyclic}")

    declared_claimable = set(dag.get("claimable_task_cids") or [])
    unknown_claimable = sorted(declared_claimable - nodes)
    if unknown_claimable:
        problems.append(f"{name} has unknown claimable CIDs: {unknown_claimable}")
    blocked_claimable = sorted(declared_claimable & review_only_task_cids)
    if blocked_claimable:
        problems.append(
            f"{name} makes blocked review-only CIDs claimable: {blocked_claimable}"
        )

bundle_task_ids = set()
bundle_task_cids = set()
for bundle_key, bundle in sorted(bundles.items()):
    if not isinstance(bundle, dict):
        problems.append(f"bundle {bundle_key!r} is not an object")
        continue
    shard = str(bundle.get("shard_path") or "")
    shard_path = root / shard
    if not shard or not shard_path.is_file():
        problems.append(f"bundle {bundle_key!r} has missing shard {shard!r}")
    tasks = bundle.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        problems.append(f"bundle {bundle_key!r} contains no tasks")
        continue
    contains_review_only = any(
        isinstance(task, dict)
        and str(task.get("goal_id") or "").strip() in review_only_goal_ids
        for task in tasks
    )
    if contains_review_only:
        check_review_flags(
            bundle,
            f"bundle {bundle_key!r}",
            json_booleans=True,
        )
    for task in tasks:
        if not isinstance(task, dict):
            problems.append(f"bundle {bundle_key!r} contains a malformed task")
            continue
        cid = str(task.get("canonical_task_cid") or task.get("task_cid") or "")
        task_id = str(task.get("task_id") or "")
        goal_id = str(task.get("goal_id") or "").strip()
        task_status = str(task.get("status") or "").strip().lower().replace("-", "_")
        if task_id:
            bundle_task_ids.add(task_id)
        if cid:
            bundle_task_cids.add(cid)
        if goal_id in never_materialized_goal_ids:
            problems.append(
                f"bundle {bundle_key!r} task {task_id!r} illegally references "
                f"blocked human gate {goal_id!r}"
            )
        if goal_id in review_only_goal_ids:
            if task_status != "blocked":
                problems.append(
                    f"bundle {bundle_key!r} review-only task {task_id!r} is not "
                    f"status blocked: {task_status!r}"
                )
            check_review_flags(
                task,
                f"bundle {bundle_key!r} review-only task {task_id!r}",
                json_booleans=True,
            )
        if not cid:
            problems.append(f"bundle {bundle_key!r} task {task_id!r} has no CID")
        elif cid not in canonical_nodes:
            problems.append(
                f"bundle {bundle_key!r} task {task_id!r} has unknown CID {cid}"
            )

if todo_task_cids != canonical_nodes:
    problems.append(
        "generated TODO CIDs and DAG node CIDs differ: "
        f"todo_only={sorted(todo_task_cids - canonical_nodes)}, "
        f"dag_only={sorted(canonical_nodes - todo_task_cids)}"
    )
if bundle_task_cids != canonical_nodes:
    problems.append(
        "bundle task CIDs and DAG node CIDs differ: "
        f"bundle_only={sorted(bundle_task_cids - canonical_nodes)}, "
        f"dag_only={sorted(canonical_nodes - bundle_task_cids)}"
    )
if bundle_task_ids != todo_task_ids:
    problems.append(
        "bundle task IDs and generated TODO task IDs differ: "
        f"bundle_only={sorted(bundle_task_ids - todo_task_ids)}, "
        f"todo_only={sorted(todo_task_ids - bundle_task_ids)}"
    )
if canonical_dag_task_ids and canonical_dag_task_ids != todo_task_ids:
    problems.append(
        "DAG task IDs and generated TODO task IDs differ: "
        f"dag_only={sorted(canonical_dag_task_ids - todo_task_ids)}, "
        f"todo_only={sorted(todo_task_ids - canonical_dag_task_ids)}"
    )

if problems:
    print("WORLDCOIN supervisor preflight FAILED:", file=sys.stderr)
    for problem in problems:
        print(f" - {problem}", file=sys.stderr)
    raise SystemExit(1)

claimable = set()
for dag in dags.values():
    claimable.update(dag.get("claimable_task_cids") or [])
if claimable & review_only_task_cids:
    raise SystemExit("blocked review-only tasks unexpectedly became claimable")
print(
    "WORLDCOIN supervisor preflight passed: "
    f"{len(source_goals)} source goals, {len(schedulable_goal_ids)} schedulable, "
    f"{len(headers)} review-board tasks, "
    f"{len(bundles)} bundles, "
    f"{len(canonical_nodes)} dependency nodes, {len(claimable)} claimable roots, "
    "0 invalid dependency CIDs"
)
PY
```

The legacy preflight above validates the planner's dependency projections. Run
the stricter source/shard alignment verifier as a second, mandatory check:

```bash
PYTHONDONTWRITEBYTECODE=1 \
python scripts/verify_world_aid_generated_board.py \
  --repo-root . \
  --objective-path docs/planning/WORLDCOIN_HUMAN_AID_OBJECTIVE_HEAP.md \
  --generated-root "$WORLD_AID_GENERATED_ROOT"
```

It fails on stale validation commands, parent/output drift, duplicate or
missing schedulable goals, missing/mutable blocked review records, missing or
permissive review-only scheduling flags, claimable blocked tasks,
TODO/index/DAG/CID disagreement, invalid CIDs, and shard bodies that do not
exactly match the canonical generated task.

Any non-empty `invalid_task_cids` value is a hard stop. Do not assume the
scheduler will repair a semantic cycle safely. Correct the source objective
parents/dependencies, regenerate, review the diff, and rerun the preflight.

Also inspect the working tree without changing it:

```bash
git status --short
git diff --check
git submodule status --recursive
```

Unrelated user changes must be preserved. Do not launch if a generated lane is
predicted to overwrite an unreviewed dirty path.

## Derive immutable stage execution and review indexes

The canonical index remains the reviewed source. The scheduler has no
goal/bundle include flag, and `--max-lanes` limits concurrency rather than
scope. Create four paired JSON/DuckDB indexes with native
`excluded_bundle_keys` fences:

- Gate 0A permits only G002;
- Gate 0B preparation permits only G037, G041, and G042 after a reviewed G002
  completion receipt;
- Gate 0B restricted review projects blocked G038, G039, and G040 records after
  reviewed G002/G037/G041/G042 completion receipts, with an empty execution
  allowlist and every bundle excluded; and
- implementation excludes G002 and G037-G042. The current profile records only
  the four preparation predecessors as receipt-backed placeholders; a future
  governance transition and regeneration must bind the later G038-G040
  receipts before implementation launch.

Every paired profile retains the canonical 40-record review universe in its
bundle payload: 37 schedulable goals plus blocked G038-G040. G035 and G036 are
absent. `execution_goal_ids`, `execution_allowlist`, and
`excluded_bundle_keys` are the only execution projection; the presence of a
blocked review record in a profile is never launch authority.

The completed statuses below are predeclared receipt adapters, not completion
evidence. The G038-G040 records stay blocked in every current profile and are
never converted to completed placeholders. Never use a later-stage profile
until its
`receipt_backed_completed_goal_ids` have matching immutable successful-merge
receipts and the applicable human gate binds those receipts. Never hand-edit
only the JSON representation.

Although the current implementation profile exposes the future 33-goal
execution projection for review, it is deliberately incomplete and
non-signable: its four completed-prerequisite placeholders cannot satisfy the
strict launch verifier's seven-prerequisite contract. A replacement profile
must be freshly derived only after future G038-G040 execution receipts exist.

```bash
env \
  PYTHONDONTWRITEBYTECODE=1 \
  IPFS_ACCEL_SKIP_CORE=1 \
  IPFS_KIT_DISABLE=1 \
  PYTHONPATH=ipfs_accelerate_py \
python - <<'PY'
from copy import deepcopy
from pathlib import Path
import os

from ipfs_accelerate_py.agent_supervisor.artifact_store import (
    read_bundle_index_artifact,
    write_bundle_index_artifact,
)

base = Path(os.environ["WORLD_AID_GENERATED_ROOT"]).resolve()
source = base / "objective_bundles/index.json"
source_relative = source.relative_to(Path.cwd().resolve()).as_posix()
profile_dir = base / "launch_profiles"
profile_dir.mkdir(parents=True, exist_ok=False)
canonical = read_bundle_index_artifact(source)
bundles = canonical.get("bundles")
if not isinstance(bundles, dict) or not bundles:
    raise SystemExit("canonical bundle index contains no bundles")

goal_to_task = {}
goal_to_bundle = {}
goal_to_status = {}
for bundle_key, bundle in bundles.items():
    tasks = bundle.get("tasks") if isinstance(bundle, dict) else None
    if not isinstance(tasks, list) or not tasks:
        raise SystemExit(f"bundle has no tasks: {bundle_key}")
    for task in tasks:
        goal_id = str(task.get("goal_id") or "")
        task_id = str(task.get("task_id") or "")
        task_cid = str(
            task.get("canonical_task_cid") or task.get("task_cid") or ""
        )
        if not goal_id or not task_id or not task_cid or goal_id in goal_to_task:
            raise SystemExit(f"invalid or duplicate goal/task identity: {goal_id!r}")
        goal_to_task[goal_id] = (task_id, task_cid)
        goal_to_bundle[goal_id] = str(bundle_key)
        goal_to_status[goal_id] = (
            str(task.get("status") or "").strip().lower().replace("-", "_")
        )

never_materialized = {"WORLDCOIN-G035", "WORLDCOIN-G036"}
review_only = {"WORLDCOIN-G038", "WORLDCOIN-G039", "WORLDCOIN-G040"}
blocked = never_materialized | review_only
schedulable = {
    f"WORLDCOIN-G{number:03d}" for number in range(1, 43)
} - blocked
review_universe = schedulable | review_only
if len(schedulable) != 37 or len(review_universe) != 40:
    raise SystemExit("reviewed schedulable/review-universe counts drifted")
if set(goal_to_task) != review_universe:
    raise SystemExit(
        "canonical bundle goal set differs from the 40-record review universe: "
        f"missing={sorted(review_universe - set(goal_to_task))}, "
        f"unexpected={sorted(set(goal_to_task) - review_universe)}"
    )
for goal_id in review_only:
    if goal_to_status[goal_id] != "blocked":
        raise SystemExit(
            f"canonical review-only task is not status blocked: {goal_id}"
        )

bootstrap_predecessors = {
    "WORLDCOIN-G002",
    "WORLDCOIN-G037",
    "WORLDCOIN-G038",
    "WORLDCOIN-G039",
    "WORLDCOIN-G040",
    "WORLDCOIN-G041",
    "WORLDCOIN-G042",
}
preparation_predecessors = {
    "WORLDCOIN-G002",
    "WORLDCOIN-G037",
    "WORLDCOIN-G041",
    "WORLDCOIN-G042",
}
specifications = {
    "g002-only.index.json": (
        {"WORLDCOIN-G002"},
        set(),
        set(),
    ),
    "gate0b-preparation.index.json": (
        {"WORLDCOIN-G037", "WORLDCOIN-G041", "WORLDCOIN-G042"},
        {"WORLDCOIN-G002"},
        set(),
    ),
    "g038-g040.index.json": (
        set(),
        preparation_predecessors,
        review_only,
    ),
    "implementation.index.json": (
        schedulable - bootstrap_predecessors,
        preparation_predecessors,
        set(),
    ),
}

for filename, (
    allowed_goal_ids,
    completed_goal_ids,
    projected_review_goal_ids,
) in specifications.items():
    if not completed_goal_ids.isdisjoint(allowed_goal_ids):
        raise SystemExit(f"profile completes an allowed goal: {filename}")
    if not projected_review_goal_ids <= review_only:
        raise SystemExit(f"profile projects a non-review goal: {filename}")
    allowed_bundles = {goal_to_bundle[goal_id] for goal_id in allowed_goal_ids}
    review_bundles = {goal_to_bundle[goal_id] for goal_id in review_only}
    if allowed_bundles & review_bundles:
        raise SystemExit(f"{filename} allows a bundle containing blocked review work")
    completed_task_ids = {
        goal_to_task[goal_id][0] for goal_id in completed_goal_ids
    }
    completed_task_cids = {
        goal_to_task[goal_id][1] for goal_id in completed_goal_ids
    }
    profile = deepcopy(canonical)
    profile_bundles = profile["bundles"]
    for bundle in profile_bundles.values():
        for task in bundle.get("tasks") or ():
            if str(task.get("goal_id") or "") in completed_goal_ids:
                task["status"] = "completed"
    profile["profile_id"] = filename.removesuffix(".index.json")
    profile["derived_from_bundle_index"] = source_relative
    profile["execution_goal_ids"] = sorted(allowed_goal_ids)
    profile["review_only_goal_ids"] = sorted(review_only)
    profile["review_projection_goal_ids"] = sorted(projected_review_goal_ids)
    profile["completed_prerequisite_goal_ids"] = sorted(completed_goal_ids)
    profile["execution_allowlist"] = sorted(allowed_bundles)
    profile["excluded_bundle_keys"] = sorted(set(profile_bundles) - allowed_bundles)
    profile["receipt_backed_completed_goal_ids"] = sorted(completed_goal_ids)
    profile["receipt_backed_completed_task_ids"] = sorted(completed_task_ids)
    profile["receipt_backed_completed_task_cids"] = sorted(completed_task_cids)

    destination = profile_dir / filename
    if destination.exists() or destination.with_suffix(".duckdb").exists():
        raise SystemExit(f"refusing to replace stage profile: {destination}")
    write_bundle_index_artifact(destination, profile)
    rendered = read_bundle_index_artifact(destination)
    if set(rendered.get("execution_allowlist") or ()) != allowed_bundles:
        raise SystemExit(f"{filename} lost its execution allowlist")
    if rendered.get("execution_goal_ids") != sorted(allowed_goal_ids):
        raise SystemExit(f"{filename} lost its execution goal set")
    if rendered.get("review_only_goal_ids") != sorted(review_only):
        raise SystemExit(f"{filename} lost the blocked review-only goal set")
    if rendered.get("review_projection_goal_ids") != sorted(projected_review_goal_ids):
        raise SystemExit(f"{filename} lost its review projection goal set")
    if rendered.get("completed_prerequisite_goal_ids") != sorted(completed_goal_ids):
        raise SystemExit(f"{filename} lost its completed prerequisite set")
    if set(rendered.get("excluded_bundle_keys") or ()) != set(profile_bundles) - allowed_bundles:
        raise SystemExit(f"{filename} lost its native exclusion fence")
    if set(rendered.get("receipt_backed_completed_task_ids") or ()) != completed_task_ids:
        raise SystemExit(f"{filename} lost its receipt-backed task set")
    rendered_review_status = {
        str(task.get("goal_id") or ""): (
            str(task.get("status") or "").strip().lower().replace("-", "_")
        )
        for bundle in (rendered.get("bundles") or {}).values()
        for task in bundle.get("tasks") or ()
        if str(task.get("goal_id") or "") in review_only
    }
    if rendered_review_status != {goal_id: "blocked" for goal_id in review_only}:
        raise SystemExit(f"{filename} mutated a blocked review-only task")
    if projected_review_goal_ids and (
        allowed_goal_ids
        or allowed_bundles
        or set(rendered.get("excluded_bundle_keys") or ()) != set(profile_bundles)
    ):
        raise SystemExit(f"{filename} review projection is executable")
    if not destination.with_suffix(".duckdb").is_file():
        raise SystemExit(f"{filename} has no paired DuckDB artifact")
    print({
        "profile": filename,
        "allowed_goal_ids": sorted(allowed_goal_ids),
        "review_projection_goal_ids": sorted(projected_review_goal_ids),
        "receipt_backed_completed_goal_ids": sorted(completed_goal_ids),
        "excluded_count": len(set(profile_bundles) - allowed_bundles),
    })
PY
```

Verify every canonical/profile JSON-DuckDB pair through a read-only DuckDB
connection before binding it. This compares content hashes, not only file size
and modification time:

```bash
env \
  PYTHONDONTWRITEBYTECODE=1 \
  IPFS_ACCEL_SKIP_CORE=1 \
  IPFS_KIT_DISABLE=1 \
python - <<'PY'
from pathlib import Path
import hashlib
import json
import os

import duckdb

base = Path(os.environ["WORLD_AID_GENERATED_ROOT"]).resolve()
json_paths = [
    base / "objective_bundles/index.json",
    base / "launch_profiles/g002-only.index.json",
    base / "launch_profiles/gate0b-preparation.index.json",
    base / "launch_profiles/g038-g040.index.json",
    base / "launch_profiles/implementation.index.json",
]
for json_path in json_paths:
    duckdb_path = json_path.with_suffix(".duckdb")
    raw = json_path.read_bytes()
    payload = json.loads(raw)
    source_sha256 = hashlib.sha256(raw).hexdigest()
    canonical_payload = json.dumps(
        payload, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    database_payload_sha256 = hashlib.sha256(canonical_payload).hexdigest()
    connection = duckdb.connect(str(duckdb_path), read_only=True)
    try:
        rows = connection.execute(
            "SELECT artifact_kind, schema_version, source_path, "
            "source_sha256, database_payload_sha256, source_size, "
            "source_mtime_ns FROM artifact_catalog"
        ).fetchall()
    finally:
        connection.close()
    if len(rows) != 1:
        raise SystemExit(f"invalid artifact_catalog row count: {duckdb_path}")
    (
        kind,
        schema,
        source_path,
        observed_source_sha256,
        observed_payload_sha256,
        source_size,
        source_mtime_ns,
    ) = rows[0]
    stat = json_path.stat()
    expected = (
        "bundle_planning_index",
        "ipfs_accelerate_py.agent_supervisor.queryable_artifact@2",
        json_path.resolve(),
        source_sha256,
        database_payload_sha256,
        stat.st_size,
        stat.st_mtime_ns,
    )
    observed = (
        str(kind),
        str(schema),
        Path(str(source_path)).resolve(),
        str(observed_source_sha256),
        str(observed_payload_sha256),
        int(source_size),
        int(source_mtime_ns),
    )
    if observed != expected:
        raise SystemExit(
            f"stale or mismatched JSON/DuckDB pair: {json_path}"
        )
    print({"json": str(json_path), "duckdb": str(duckdb_path), "sha256": source_sha256})
PY
```

Create the deterministic preflight receipt only after the canonical board and
all four stage profiles pass. Creation refuses to overwrite an existing
receipt. Verification recomputes the complete manifest without writing and
binds the full board, graph, canonical JSON/DuckDB index, vector index, every
bundle shard, discovery evidence, planning receipts, dataset manifests, all
four paired launch profiles, and both verifier implementations:

```bash
PYTHONDONTWRITEBYTECODE=1 \
python scripts/verify_world_aid_preflight_receipt.py \
  --create \
  --repo-root . \
  --objective-path docs/planning/WORLDCOIN_HUMAN_AID_OBJECTIVE_HEAP.md \
  --generated-root "$WORLD_AID_GENERATED_ROOT" \
  --receipt "$WORLD_AID_GENERATED_ROOT/preflight-receipt.json"

PYTHONDONTWRITEBYTECODE=1 \
python scripts/verify_world_aid_preflight_receipt.py \
  --verify \
  --repo-root . \
  --objective-path docs/planning/WORLDCOIN_HUMAN_AID_OBJECTIVE_HEAP.md \
  --generated-root "$WORLD_AID_GENERATED_ROOT" \
  --receipt "$WORLD_AID_GENERATED_ROOT/preflight-receipt.json"
```

Then ask the actual lane planner, rather than a hand-written JSON check, to
prove that the execution projection contains exactly G002:

```bash
env \
  PYTHONDONTWRITEBYTECODE=1 \
  IPFS_ACCEL_SKIP_CORE=1 \
  IPFS_KIT_DISABLE=1 \
  PYTHONPATH=ipfs_accelerate_py \
python - <<'PY'
from pathlib import Path
import hashlib
import os

from ipfs_accelerate_py.agent_supervisor.bundle_supervisor import plan_bundle_lanes

base = Path(os.environ["WORLD_AID_GENERATED_ROOT"]).resolve()
repo_root = Path.cwd().resolve()
index_path = base / "launch_profiles/g002-only.index.duckdb"
lanes = plan_bundle_lanes(
    bundle_index_path=index_path,
    repo_root=repo_root,
    state_root=base / "gate0a/lane_state",
    worktree_root=base / "gate0a/worktrees",
    log_dir=base / "gate0a/logs",
    task_prefix="WORLDCOIN-AUTO-",
    implement=False,
    max_lanes=None,
)
assert [lane.bundle_key for lane in lanes] == [
    "worldcoin-human-aid/integration-audit"
]
payload = lanes[0].queue_payload or {}
assert {
    str(task.get("goal_id") or "")
    for task in payload.get("tasks") or ()
} == {"WORLDCOIN-G002"}
assert lanes[0].claimable and lanes[0].task_ids
assert lanes[0].runtime_todo_path is not None
assert lanes[0].runtime_todo_path.parent == lanes[0].state_dir
assert lanes[0].source_todo_sha256 == hashlib.sha256(
    lanes[0].todo_path.read_bytes()
).hexdigest()
assert lanes[0].command[
    lanes[0].command.index("--todo-path") + 1
] == str(lanes[0].runtime_todo_path)
for disabled_writer in (
    "--no-retry-budget-guardrail",
    "--no-dependency-guardrail",
    "--no-reconciliation-guardrail",
    "--no-objective-task-janitor",
    "--no-objective-goal-migration",
):
    assert disabled_writer in lanes[0].command
assert "--auto-commit-generated-dirty" not in lanes[0].command
print({
    "bundle": lanes[0].bundle_key,
    "task_ids": lanes[0].task_ids,
    "claimable": lanes[0].claimable,
    "source_todo_sha256": lanes[0].source_todo_sha256,
    "runtime_todo_path": lanes[0].runtime_todo_path.relative_to(repo_root).as_posix(),
})
PY
```

Assert the remaining three stage profiles through the real lane planner. This
also proves that the completed-prerequisite statuses were available before the
native exclusion fence removed their bundles and that the G038-G040 review
profile plans zero lanes. The current implementation-profile result is only a
future-projection review; it is not a signable launch plan because three
required bootstrap receipts do not yet exist:

```bash
env \
  PYTHONDONTWRITEBYTECODE=1 \
  IPFS_ACCEL_SKIP_CORE=1 \
  IPFS_KIT_DISABLE=1 \
  PYTHONPATH=ipfs_accelerate_py \
python - <<'PY'
from pathlib import Path
import os

from ipfs_accelerate_py.agent_supervisor.artifact_store import (
    read_bundle_index_artifact,
)
from ipfs_accelerate_py.agent_supervisor.bundle_supervisor import plan_bundle_lanes

base = Path(os.environ["WORLD_AID_GENERATED_ROOT"]).resolve()
repo_root = Path.cwd().resolve()
review_only = {"WORLDCOIN-G038", "WORLDCOIN-G039", "WORLDCOIN-G040"}
blocked = {"WORLDCOIN-G035", "WORLDCOIN-G036"} | review_only
schedulable = {
    f"WORLDCOIN-G{number:03d}" for number in range(1, 43)
} - blocked
assert len(schedulable) == 37
bootstrap = {
    "WORLDCOIN-G002",
    "WORLDCOIN-G037",
    "WORLDCOIN-G038",
    "WORLDCOIN-G039",
    "WORLDCOIN-G040",
    "WORLDCOIN-G041",
    "WORLDCOIN-G042",
}
profiles = {
    "gate0b-preparation.index.duckdb": (
        {"WORLDCOIN-G037", "WORLDCOIN-G041", "WORLDCOIN-G042"},
        set(),
    ),
    "g038-g040.index.duckdb": (set(), review_only),
    "implementation.index.duckdb": (schedulable - bootstrap, set()),
}
for filename, (expected_goals, expected_review_goals) in profiles.items():
    index_path = base / "launch_profiles" / filename
    profile = read_bundle_index_artifact(index_path)
    if set(profile.get("execution_goal_ids") or ()) != expected_goals:
        raise SystemExit(f"{filename} execution metadata drifted")
    if set(profile.get("review_projection_goal_ids") or ()) != expected_review_goals:
        raise SystemExit(f"{filename} review metadata drifted")
    if set(profile.get("review_only_goal_ids") or ()) != review_only:
        raise SystemExit(f"{filename} lost the global blocked review set")
    review_status = {
        str(task.get("goal_id") or ""): (
            str(task.get("status") or "").strip().lower().replace("-", "_")
        )
        for bundle in (profile.get("bundles") or {}).values()
        for task in bundle.get("tasks") or ()
        if str(task.get("goal_id") or "") in review_only
    }
    if review_status != {goal_id: "blocked" for goal_id in review_only}:
        raise SystemExit(f"{filename} contains a non-blocked review task")
    lanes = plan_bundle_lanes(
        bundle_index_path=index_path,
        repo_root=repo_root,
        state_root=base / "profile_assertions" / filename / "lane_state",
        worktree_root=base / "profile_assertions" / filename / "worktrees",
        log_dir=base / "profile_assertions" / filename / "logs",
        task_prefix="WORLDCOIN-AUTO-",
        implement=False,
        max_lanes=None,
    )
    observed_goals = {
        str(task.get("goal_id") or "")
        for lane in lanes
        for task in (lane.queue_payload or {}).get("tasks") or ()
    }
    observed_bundles = {lane.bundle_key for lane in lanes}
    if observed_goals != expected_goals:
        raise SystemExit(
            f"{filename} lane goals differ: "
            f"missing={sorted(expected_goals - observed_goals)}, "
            f"unexpected={sorted(observed_goals - expected_goals)}"
        )
    if expected_review_goals:
        if lanes or profile.get("execution_allowlist"):
            raise SystemExit(f"{filename} blocked review profile planned execution")
    elif (
        len(observed_bundles) != len(lanes)
        or not lanes
        or not all(lane.task_ids for lane in lanes)
    ):
        raise SystemExit(f"{filename} has duplicate or empty lane projections")
    print({
        "profile": filename,
        "lane_count": len(lanes),
        "goal_ids": sorted(observed_goals),
        "claimable_count": sum(lane.claimable for lane in lanes),
    })
PY
```

### Gate 0A no-start dry run

This writes a manifest but starts no worker:

```bash
env \
  WORLD_ID_ENABLED=0 \
  WORLD_AID_EXTERNAL_CALLS_ENABLED=0 \
  WORLD_AID_WLD_TRANSFERS_ENABLED=0 \
  PYTHONDONTWRITEBYTECODE=1 \
  IPFS_ACCEL_SKIP_CORE=1 \
  IPFS_KIT_DISABLE=1 \
  HF_HUB_OFFLINE=1 \
  HF_DATASETS_OFFLINE=1 \
  TRANSFORMERS_OFFLINE=1 \
  NPM_CONFIG_OFFLINE=true \
  PIP_NO_INDEX=1 \
  CARGO_NET_OFFLINE=true \
  PYTHONPATH=ipfs_accelerate_py \
python -m ipfs_accelerate_py.agent_supervisor.bundle_supervisor \
  --repo-root . \
  --bundle-index-path "$WORLD_AID_GENERATED_ROOT/launch_profiles/g002-only.index.duckdb" \
  --state-root "$WORLD_AID_GENERATED_ROOT/gate0a/lane_state" \
  --worktree-root "$WORLD_AID_GENERATED_ROOT/gate0a/worktrees" \
  --log-dir "$WORLD_AID_GENERATED_ROOT/gate0a/logs" \
  --manifest-path "$WORLD_AID_GENERATED_ROOT/gate0a/g002-only-manifest.json" \
  --metrics-path "$WORLD_AID_GENERATED_ROOT/gate0a/g002-only-metrics.json" \
  --coordination-path "$WORLD_AID_GENERATED_ROOT/gate0a/coordination.duckdb" \
  --task-prefix WORLDCOIN-AUTO- \
  --merge-target-branch "$WORLD_AID_MERGE_TARGET_BRANCH" \
  --worktree-submodule-path ipfs_accelerate_py \
  --worktree-submodule-path ipfs_datasets_py \
  --max-restarts 0 \
  --max-lanes 1 \
  --no-implement \
  --once
```

### Gate 0A sandboxed launch

Use this only after the derived-index assertion and no-start dry run pass. The
implementation command deliberately replaces the supervisor's unsandboxed
default with an ephemeral `workspace-write` Codex sandbox whose command tools
have network access disabled. The Codex model control plane remains available;
World, RPC, package/container registries, and arbitrary command egress do not.
The command also disables Codex browser, app, and multi-agent surfaces and sets
`web_search="disabled"` because those surfaces are outside the command sandbox
and would violate G002's offline acceptance contract. Treat any attempted web
or browser tool call as a failed launch: stop the foreground supervisor, verify
that its isolated worktree is clean, terminate any orphaned implementation
child by its exact recorded PID, and relaunch from the immutable G002 index.
`IPFS_ACCELERATE_AGENT_DISABLE_SUBAGENTS=1` also makes the daemon emit explicit
single-agent guidance because noninteractive Codex sessions do not necessarily
have a registered collaboration thread.

On Ubuntu hosts where `kernel.apparmor_restrict_unprivileged_userns=1`, verify
the installed AppArmor sandbox profile before launch:

```bash
aa-exec -p linux-sandbox -- unshare -Urn /bin/true
```

The command must exit zero. The launch prefixes Codex with that profile so
Bubblewrap can create its restricted user/network namespaces. If the profile
is absent or the probe fails, do not switch to `danger-full-access`; have an
administrator install/review the profile or move the run to a compatible
isolated host.

```bash
env \
  WORLD_ID_ENABLED=0 \
  WORLD_AID_EXTERNAL_CALLS_ENABLED=0 \
  WORLD_AID_WLD_TRANSFERS_ENABLED=0 \
  IPFS_ACCELERATE_AGENT_DISABLE_SUBAGENTS=1 \
  IPFS_ACCEL_SKIP_CORE=1 \
  IPFS_KIT_DISABLE=1 \
  HF_HUB_OFFLINE=1 \
  HF_DATASETS_OFFLINE=1 \
  TRANSFORMERS_OFFLINE=1 \
  NPM_CONFIG_OFFLINE=true \
  PIP_NO_INDEX=1 \
  CARGO_NET_OFFLINE=true \
  GIT_TERMINAL_PROMPT=0 \
  PYTHONPATH=ipfs_accelerate_py \
python -m ipfs_accelerate_py.agent_supervisor.bundle_supervisor \
  --repo-root . \
  --bundle-index-path "$WORLD_AID_GENERATED_ROOT/launch_profiles/g002-only.index.duckdb" \
  --state-root "$WORLD_AID_GENERATED_ROOT/gate0a/lane_state" \
  --worktree-root "$WORLD_AID_GENERATED_ROOT/gate0a/worktrees" \
  --log-dir "$WORLD_AID_GENERATED_ROOT/gate0a/logs" \
  --manifest-path "$WORLD_AID_GENERATED_ROOT/gate0a/g002-only-manifest.json" \
  --metrics-path "$WORLD_AID_GENERATED_ROOT/gate0a/g002-only-metrics.json" \
  --coordination-path "$WORLD_AID_GENERATED_ROOT/gate0a/coordination.duckdb" \
  --task-prefix WORLDCOIN-AUTO- \
  --merge-target-branch "$WORLD_AID_MERGE_TARGET_BRANCH" \
  --worktree-submodule-path ipfs_accelerate_py \
  --worktree-submodule-path ipfs_datasets_py \
  --implementation-command 'aa-exec -p linux-sandbox -- codex --ask-for-approval never --disable apps --disable browser_use --disable browser_use_external --disable browser_use_full_cdp_access --disable in_app_browser --disable multi_agent --disable multi_agent_v2 -c web_search=\"disabled\" exec --ephemeral --sandbox workspace-write -' \
  --poll-interval 15 \
  --daemon-interval 15 \
  --check-interval 15 \
  --lease-ms 300000 \
  --heartbeat-interval 5 \
  --implementation-timeout 3600 \
  --max-restarts 1 \
  --max-task-attempts 1 \
  --max-lanes 1 \
  --implement \
  --start
```

Do not add `--once`: the scheduler can exit after one reconciliation cycle
while leaving a spawned child alive. Keep this foreground process available
for graceful stop. After G002 settles, stop and review its canonical successful
bundle receipt and offline-bootstrap proposal before deriving a wider immutable
launch profile. Do not mutate a live derived index in place.

## Gate 0B preparation no-start dry run

Do not use the preparation profile until the reviewed G002 receipt is available.
Re-verify the immutable preflight receipt, then make the actual supervisor
project the three preparation goals from the paired DuckDB index without
starting a worker:

```bash
PYTHONDONTWRITEBYTECODE=1 \
python scripts/verify_world_aid_preflight_receipt.py \
  --verify \
  --repo-root . \
  --objective-path docs/planning/WORLDCOIN_HUMAN_AID_OBJECTIVE_HEAP.md \
  --generated-root "$WORLD_AID_GENERATED_ROOT" \
  --receipt "$WORLD_AID_GENERATED_ROOT/preflight-receipt.json"

env \
  WORLD_ID_ENABLED=0 \
  WORLD_AID_EXTERNAL_CALLS_ENABLED=0 \
  WORLD_AID_WLD_TRANSFERS_ENABLED=0 \
  PYTHONDONTWRITEBYTECODE=1 \
  IPFS_ACCEL_SKIP_CORE=1 \
  IPFS_KIT_DISABLE=1 \
  HF_HUB_OFFLINE=1 \
  HF_DATASETS_OFFLINE=1 \
  TRANSFORMERS_OFFLINE=1 \
  NPM_CONFIG_OFFLINE=true \
  PIP_NO_INDEX=1 \
  CARGO_NET_OFFLINE=true \
  PYTHONPATH=ipfs_accelerate_py \
python -m ipfs_accelerate_py.agent_supervisor.bundle_supervisor \
  --repo-root . \
  --bundle-index-path "$WORLD_AID_GENERATED_ROOT/launch_profiles/gate0b-preparation.index.duckdb" \
  --state-root "$WORLD_AID_GENERATED_ROOT/gate0b-preparation/dry_run/lane_state" \
  --worktree-root "$WORLD_AID_GENERATED_ROOT/gate0b-preparation/dry_run/worktrees" \
  --log-dir "$WORLD_AID_GENERATED_ROOT/gate0b-preparation/dry_run/logs" \
  --manifest-path "$WORLD_AID_GENERATED_ROOT/gate0b-preparation/dry_run/lane-manifest.json" \
  --metrics-path "$WORLD_AID_GENERATED_ROOT/gate0b-preparation/dry_run/scheduler-metrics.json" \
  --coordination-path "$WORLD_AID_GENERATED_ROOT/gate0b-preparation/dry_run/coordination.duckdb" \
  --task-prefix WORLDCOIN-AUTO- \
  --merge-target-branch "$WORLD_AID_MERGE_TARGET_BRANCH" \
  --worktree-submodule-path ipfs_accelerate_py \
  --worktree-submodule-path ipfs_datasets_py \
  --max-restarts 0 \
  --no-implement \
  --once
```

The non-starting code path deliberately ignores `--max-lanes`; scope comes
from the profile's native exclusion fence. Prove the exact lane projection and
absence of worker activity:

```bash
python - <<'PY'
from pathlib import Path
import hashlib
import json
import os

repo_root = Path.cwd().resolve()
base = Path(os.environ["WORLD_AID_GENERATED_ROOT"]).resolve()
index_path = base / "launch_profiles/gate0b-preparation.index.duckdb"
manifest_path = base / "gate0b-preparation/dry_run/lane-manifest.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
expected_goals = {"WORLDCOIN-G037", "WORLDCOIN-G041", "WORLDCOIN-G042"}
lanes = manifest.get("lanes")
if not isinstance(lanes, list):
    raise SystemExit("preparation dry run omitted lanes")
observed_goals = {
    str(task.get("goal_id") or "")
    for lane in lanes
    for task in ((lane.get("queue_payload") or {}).get("tasks") or ())
    if isinstance(task, dict)
}
expected_index = index_path.relative_to(repo_root).as_posix()
assert manifest.get("schema") == "ipfs_accelerate_py.agent_supervisor.bundle_supervisor"
assert manifest.get("bundle_index_path") == expected_index
assert observed_goals == expected_goals
assert int(manifest.get("planned_count") or 0) == len(lanes) > 0
assert len({str(lane.get("bundle_key") or "") for lane in lanes}) == len(lanes)
for lane in lanes:
    source_path = repo_root / str(lane.get("todo_path") or "")
    runtime_path = repo_root / str(lane.get("runtime_todo_path") or "")
    state_dir = repo_root / str(lane.get("state_dir") or "")
    assert source_path.is_file()
    assert runtime_path.parent == state_dir
    assert str(lane.get("source_todo_sha256") or "") == hashlib.sha256(
        source_path.read_bytes()
    ).hexdigest()
    command = [str(item) for item in (lane.get("command") or [])]
    assert command[command.index("--todo-path") + 1] == str(runtime_path)
    assert "--no-objective-task-janitor" in command
    assert "--no-objective-goal-migration" in command
    assert "--auto-commit-generated-dirty" not in command
for key in ("started_count", "running_count", "active_worker_count"):
    assert int(manifest.get(key) or 0) == 0
for key in ("started", "launched_task_cids", "active_worker_pids"):
    assert not (manifest.get(key) or [])
assert not any(lane.get("pid") for lane in lanes)
print({
    "profile": expected_index,
    "planned": len(lanes),
    "goal_ids": sorted(observed_goals),
    "started": 0,
})
PY
```

## Gate 0B preparation sandboxed launch

This preparation wave runs before Gate 0B-selection and may execute only G037,
G041, and G042. It must have the reviewed G002 completion receipt and the
passing no-start manifest above. Its workers may inspect repository files and
installed distribution metadata, but they must honor the preparation
prohibitions in the objective heap. Re-run the AppArmor probe described for
Gate 0A, then launch with the same browser, app, multi-agent, and command-egress
restrictions:

```bash
PYTHONDONTWRITEBYTECODE=1 \
python scripts/verify_world_aid_preflight_receipt.py \
  --verify \
  --repo-root . \
  --objective-path docs/planning/WORLDCOIN_HUMAN_AID_OBJECTIVE_HEAP.md \
  --generated-root "$WORLD_AID_GENERATED_ROOT" \
  --receipt "$WORLD_AID_GENERATED_ROOT/preflight-receipt.json"

aa-exec -p linux-sandbox -- unshare -Urn /bin/true

env \
  WORLD_ID_ENABLED=0 \
  WORLD_AID_EXTERNAL_CALLS_ENABLED=0 \
  WORLD_AID_WLD_TRANSFERS_ENABLED=0 \
  IPFS_ACCELERATE_AGENT_DISABLE_SUBAGENTS=1 \
  IPFS_ACCEL_SKIP_CORE=1 \
  IPFS_KIT_DISABLE=1 \
  HF_HUB_OFFLINE=1 \
  HF_DATASETS_OFFLINE=1 \
  TRANSFORMERS_OFFLINE=1 \
  NPM_CONFIG_OFFLINE=true \
  PIP_NO_INDEX=1 \
  CARGO_NET_OFFLINE=true \
  GIT_TERMINAL_PROMPT=0 \
  PYTHONPATH=ipfs_accelerate_py \
python -m ipfs_accelerate_py.agent_supervisor.bundle_supervisor \
  --repo-root . \
  --bundle-index-path "$WORLD_AID_GENERATED_ROOT/launch_profiles/gate0b-preparation.index.duckdb" \
  --state-root "$WORLD_AID_GENERATED_ROOT/gate0b-preparation/live/lane_state" \
  --worktree-root "$WORLD_AID_GENERATED_ROOT/gate0b-preparation/live/worktrees" \
  --log-dir "$WORLD_AID_GENERATED_ROOT/gate0b-preparation/live/logs" \
  --manifest-path "$WORLD_AID_GENERATED_ROOT/gate0b-preparation/live/lane-manifest.json" \
  --metrics-path "$WORLD_AID_GENERATED_ROOT/gate0b-preparation/live/scheduler-metrics.json" \
  --coordination-path "$WORLD_AID_GENERATED_ROOT/gate0b-preparation/live/coordination.duckdb" \
  --task-prefix WORLDCOIN-AUTO- \
  --merge-target-branch "$WORLD_AID_MERGE_TARGET_BRANCH" \
  --worktree-submodule-path ipfs_accelerate_py \
  --worktree-submodule-path ipfs_datasets_py \
  --implementation-command 'aa-exec -p linux-sandbox -- codex --ask-for-approval never --disable apps --disable browser_use --disable browser_use_external --disable browser_use_full_cdp_access --disable in_app_browser --disable multi_agent --disable multi_agent_v2 -c web_search=\"disabled\" exec --ephemeral --sandbox workspace-write -' \
  --poll-interval 15 \
  --daemon-interval 15 \
  --check-interval 15 \
  --lease-ms 300000 \
  --heartbeat-interval 5 \
  --implementation-timeout 3600 \
  --max-restarts 1 \
  --max-task-attempts 1 \
  --max-lanes 1 \
  --implement \
  --start
```

Stop the foreground supervisor after all three preparation receipts settle.
Review those receipts and their generated verifier/proposal files before human
reviewers decide whether to begin the separate launcher/governance-transition
work required for a future Gate 0B-selection. The current blocked profile is
non-signable, and a preparation worker cannot create or satisfy that approval.

## Gate 0B blocked review-profile no-start proof

The current G038-G040 profile is a non-signable review artifact, not an
execution profile. The existing Gate 0B-selection verifier must reject it
because it has no execution goals or allowlist. Verify the immutable preflight
receipt, then prove that the paired profile plans zero lanes:

```bash
PYTHONDONTWRITEBYTECODE=1 \
python scripts/verify_world_aid_preflight_receipt.py \
  --verify \
  --repo-root . \
  --objective-path docs/planning/WORLDCOIN_HUMAN_AID_OBJECTIVE_HEAP.md \
  --generated-root "$WORLD_AID_GENERATED_ROOT" \
  --receipt "$WORLD_AID_GENERATED_ROOT/preflight-receipt.json"

env \
  WORLD_ID_ENABLED=0 \
  WORLD_AID_EXTERNAL_CALLS_ENABLED=0 \
  WORLD_AID_WLD_TRANSFERS_ENABLED=0 \
  PYTHONDONTWRITEBYTECODE=1 \
  IPFS_ACCEL_SKIP_CORE=1 \
  IPFS_KIT_DISABLE=1 \
  HF_HUB_OFFLINE=1 \
  HF_DATASETS_OFFLINE=1 \
  TRANSFORMERS_OFFLINE=1 \
  NPM_CONFIG_OFFLINE=true \
  PIP_NO_INDEX=1 \
  CARGO_NET_OFFLINE=true \
  PYTHONPATH=ipfs_accelerate_py \
python -m ipfs_accelerate_py.agent_supervisor.bundle_supervisor \
  --repo-root . \
  --bundle-index-path "$WORLD_AID_GENERATED_ROOT/launch_profiles/g038-g040.index.duckdb" \
  --state-root "$WORLD_AID_GENERATED_ROOT/gate0b-restricted/dry_run/lane_state" \
  --worktree-root "$WORLD_AID_GENERATED_ROOT/gate0b-restricted/dry_run/worktrees" \
  --log-dir "$WORLD_AID_GENERATED_ROOT/gate0b-restricted/dry_run/logs" \
  --manifest-path "$WORLD_AID_GENERATED_ROOT/gate0b-restricted/dry_run/lane-manifest.json" \
  --metrics-path "$WORLD_AID_GENERATED_ROOT/gate0b-restricted/dry_run/scheduler-metrics.json" \
  --coordination-path "$WORLD_AID_GENERATED_ROOT/gate0b-restricted/dry_run/coordination.duckdb" \
  --task-prefix WORLDCOIN-AUTO- \
  --merge-target-branch "$WORLD_AID_MERGE_TARGET_BRANCH" \
  --worktree-submodule-path ipfs_accelerate_py \
  --worktree-submodule-path ipfs_datasets_py \
  --max-restarts 0 \
  --no-implement \
  --once
```

```bash
python - <<'PY'
from pathlib import Path
import json
import os

repo_root = Path.cwd().resolve()
base = Path(os.environ["WORLD_AID_GENERATED_ROOT"]).resolve()
index_path = base / "launch_profiles/g038-g040.index.duckdb"
profile_path = base / "launch_profiles/g038-g040.index.json"
manifest_path = base / "gate0b-restricted/dry_run/lane-manifest.json"
profile = json.loads(profile_path.read_text(encoding="utf-8"))
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
expected_review_goals = {"WORLDCOIN-G038", "WORLDCOIN-G039", "WORLDCOIN-G040"}
lanes = manifest.get("lanes")
if not isinstance(lanes, list):
    raise SystemExit("restricted dry run omitted lanes")
observed_goals = {
    str(task.get("goal_id") or "")
    for lane in lanes
    for task in ((lane.get("queue_payload") or {}).get("tasks") or ())
    if isinstance(task, dict)
}
expected_index = index_path.relative_to(repo_root).as_posix()
assert manifest.get("schema") == "ipfs_accelerate_py.agent_supervisor.bundle_supervisor"
assert manifest.get("bundle_index_path") == expected_index
assert set(profile.get("execution_goal_ids") or ()) == set()
assert set(profile.get("execution_allowlist") or ()) == set()
assert set(profile.get("review_projection_goal_ids") or ()) == expected_review_goals
assert set(profile.get("excluded_bundle_keys") or ()) == set(
    (profile.get("bundles") or {}).keys()
)
review_status = {
    str(task.get("goal_id") or ""): (
        str(task.get("status") or "").strip().lower().replace("-", "_")
    )
    for bundle in (profile.get("bundles") or {}).values()
    for task in bundle.get("tasks") or ()
    if str(task.get("goal_id") or "") in expected_review_goals
}
assert review_status == {goal_id: "blocked" for goal_id in expected_review_goals}
assert observed_goals == set()
assert int(manifest.get("planned_count") or 0) == len(lanes) == 0
assert int(manifest.get("claimable_count") or 0) == 0
assert int(manifest.get("ready_count") or 0) == 0
for key in ("started_count", "running_count", "active_worker_count"):
    assert int(manifest.get(key) or 0) == 0
for key in ("started", "launched_task_cids", "active_worker_pids"):
    assert not (manifest.get(key) or [])
assert not any(lane.get("pid") for lane in lanes)
print({
    "profile": expected_index,
    "planned": 0,
    "review_goal_ids": sorted(expected_review_goals),
    "execution_goal_ids": [],
    "started": 0,
})
PY
```

## No current G038-G040 launch

Do not add `--start`, `--implement`, an execution allowlist, or ready status to
the blocked review profile. A selection signature, environment flag, or
agent-authored receipt cannot open it. There is intentionally no launch command
for G038-G040 in this runbook.

A future execution workflow requires all of the following as new, reviewable
artifacts: an operator-controlled Gate-first launcher that authenticates the
exact entrypoint before repository code runs; governance approval to transition
G038-G040 from `blocked`; a fresh objective heap, TODO/index/DAG, profiles, and
preflight receipt generated after that transition; and new human signatures
binding the launcher and regenerated artifacts. The future execution profile
must retain the selected offline tool digests, default-deny egress, no-live-
secret evidence, descriptor-backed inputs, process/resource/output bounds, and
atomic no-follow receipts. Never edit or promote the current review profile.

## Current implementation-projection review-only dry run

The current `implementation.index` pair is a future-incomplete review artifact.
It intentionally records only G002/G037/G041/G042 as receipt-backed completed
prerequisites and retains G038-G040 as blocked review records. The strict Gate
0B-launch verifier requires all seven G002/G037-G042 prerequisites to be
receipt-backed and completed. It must therefore reject this profile and every
manifest derived from it.

The command below is an optional no-start inspection of the current 33-goal
projection. It plans lanes and writes a manifest, but it does not contain
`--start` and starts no workers. Its output is non-signable review evidence,
not a Gate 0B-launch receipt. Never add `--start` or reuse this manifest.

```bash
env \
  WORLD_ID_ENABLED=0 \
  WORLD_AID_EXTERNAL_CALLS_ENABLED=0 \
  WORLD_AID_WLD_TRANSFERS_ENABLED=0 \
  PYTHONDONTWRITEBYTECODE=1 \
  IPFS_ACCEL_SKIP_CORE=1 \
  IPFS_KIT_DISABLE=1 \
  HF_HUB_OFFLINE=1 \
  HF_DATASETS_OFFLINE=1 \
  TRANSFORMERS_OFFLINE=1 \
  NPM_CONFIG_OFFLINE=true \
  PIP_NO_INDEX=1 \
  CARGO_NET_OFFLINE=true \
  PYTHONPATH=ipfs_accelerate_py \
python -m ipfs_accelerate_py.agent_supervisor.bundle_supervisor \
  --repo-root . \
  --bundle-index-path "$WORLD_AID_GENERATED_ROOT/launch_profiles/implementation.index.duckdb" \
  --state-root "$WORLD_AID_GENERATED_ROOT/dry_run/lane_state" \
  --worktree-root "$WORLD_AID_GENERATED_ROOT/dry_run/worktrees" \
  --log-dir "$WORLD_AID_GENERATED_ROOT/dry_run/logs" \
  --manifest-path "$WORLD_AID_GENERATED_ROOT/dry_run/lane-manifest.json" \
  --metrics-path "$WORLD_AID_GENERATED_ROOT/dry_run/scheduler-metrics.json" \
  --coordination-path "$WORLD_AID_GENERATED_ROOT/dry_run/coordination.duckdb" \
  --task-prefix WORLDCOIN-AUTO- \
  --merge-target-branch "$WORLD_AID_MERGE_TARGET_BRANCH" \
  --worktree-submodule-path ipfs_accelerate_py \
  --worktree-submodule-path ipfs_datasets_py \
  --max-restarts 0 \
  --no-implement \
  --once
```

Confirm the exact implementation goal/CID/bundle projection and prove that the
review-only dry run started nothing:

```bash
python - <<'PY'
import json
import os
from pathlib import Path

repo_root = Path.cwd().resolve()
base = Path(os.environ["WORLD_AID_GENERATED_ROOT"]).resolve()
profile_path = base / "launch_profiles/implementation.index.json"
index_path = profile_path.with_suffix(".duckdb")
manifest_path = base / "dry_run/lane-manifest.json"
profile = json.loads(profile_path.read_text(encoding="utf-8"))
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

review_only = {"WORLDCOIN-G038", "WORLDCOIN-G039", "WORLDCOIN-G040"}
blocked = {"WORLDCOIN-G035", "WORLDCOIN-G036"} | review_only
schedulable = {
    f"WORLDCOIN-G{number:03d}" for number in range(1, 43)
} - blocked
assert len(schedulable) == 37
bootstrap = {
    "WORLDCOIN-G002",
    "WORLDCOIN-G037",
    "WORLDCOIN-G038",
    "WORLDCOIN-G039",
    "WORLDCOIN-G040",
    "WORLDCOIN-G041",
    "WORLDCOIN-G042",
}
preparation_predecessors = {
    "WORLDCOIN-G002",
    "WORLDCOIN-G037",
    "WORLDCOIN-G041",
    "WORLDCOIN-G042",
}
expected_goals = schedulable - bootstrap
assert len(expected_goals) == 33
if set(profile.get("execution_goal_ids") or ()) != expected_goals:
    raise SystemExit("implementation profile goal metadata drifted")
completed_prerequisites = set(
    profile.get("receipt_backed_completed_goal_ids") or ()
)
if completed_prerequisites != preparation_predecessors:
    raise SystemExit("current profile prerequisite review metadata drifted")
if bootstrap <= completed_prerequisites:
    raise SystemExit("current review profile unexpectedly claims launch readiness")
if set(profile.get("review_only_goal_ids") or ()) != review_only:
    raise SystemExit("implementation profile lost the blocked review-only set")
if profile.get("review_projection_goal_ids"):
    raise SystemExit("implementation profile projects blocked review-only work")
review_status = {
    str(task.get("goal_id") or ""): (
        str(task.get("status") or "").strip().lower().replace("-", "_")
    )
    for bundle in (profile.get("bundles") or {}).values()
    for task in bundle.get("tasks") or ()
    if str(task.get("goal_id") or "") in review_only
}
if review_status != {goal_id: "blocked" for goal_id in review_only}:
    raise SystemExit("implementation profile mutated a blocked review-only task")
expected_bundles = set(profile.get("execution_allowlist") or ())
expected_records = {
    (
        str(bundle_key),
        str(task.get("goal_id") or ""),
        str(task.get("task_id") or ""),
        str(task.get("canonical_task_cid") or task.get("task_cid") or ""),
    )
    for bundle_key, bundle in (profile.get("bundles") or {}).items()
    for task in bundle.get("tasks") or ()
    if str(task.get("goal_id") or "") in expected_goals
}
if (
    {record[1] for record in expected_records} != expected_goals
    or not all(record[2] and record[3] for record in expected_records)
):
    raise SystemExit("implementation profile task identity is incomplete")

lanes = manifest.get("lanes")
if not isinstance(lanes, list):
    raise SystemExit("implementation dry run omitted lanes")
observed_bundles = {str(lane.get("bundle_key") or "") for lane in lanes}
observed_records = {
    (
        str(lane.get("bundle_key") or ""),
        str(task.get("goal_id") or ""),
        str(task.get("task_id") or ""),
        str(task.get("canonical_task_cid") or task.get("task_cid") or ""),
    )
    for lane in lanes
    for task in ((lane.get("queue_payload") or {}).get("tasks") or ())
    if isinstance(task, dict)
}
expected_index = index_path.relative_to(repo_root).as_posix()
assert manifest.get("schema") == "ipfs_accelerate_py.agent_supervisor.bundle_supervisor"
assert manifest.get("bundle_index_path") == expected_index
assert observed_bundles == expected_bundles
assert observed_records == expected_records
assert int(manifest.get("planned_count") or 0) == len(lanes) == len(expected_bundles)
assert len(observed_bundles) == len(lanes) > 0
for key in ("started_count", "running_count", "active_worker_count"):
    assert int(manifest.get(key) or 0) == 0
for key in ("started", "launched_task_cids", "active_worker_pids"):
    assert not (manifest.get(key) or [])
assert not any(lane.get("pid") for lane in lanes)
ready = manifest.get("claimable_count")
if ready is None:
    ready = manifest.get("ready_count", 0)
print({
    "schema": manifest["schema"],
    "profile": expected_index,
    "planned": manifest["planned_count"],
    "goal_count": len(expected_goals),
    "claimable_or_ready": ready,
    "dependency_blocked": manifest.get("blocked_count", 0),
    "launch_signable": False,
    "missing_launch_prerequisites": sorted(bootstrap - completed_prerequisites),
    "started": 0,
})
PY
```

Dependency-blocked lanes are expected in a valid DAG. Invalid CIDs and cycles
are not; those are rejected by the earlier preflight.

After the future operator-controlled G038-G040 execution succeeds, preserve its
three immutable receipts, freshly regenerate the objective board and profiles,
and derive a replacement implementation profile that records all seven
G002/G037-G042 prerequisites as receipt-backed completed. Run a new no-start
dry run against that fresh profile. Only that new profile, preflight receipt,
and dry-run manifest may be submitted to the strict Gate 0B-launch verifier;
none of the current artifacts may be edited, promoted, or reused.

## Future live-feature-disabled implementation launch

There is no implementation launch for the current generated root. The command
in this section is a future template only. Use it only after a fresh,
post-G038-G040 implementation profile and dry-run manifest pass the strict Gate
0B-launch verifier and all earlier review/preflight steps. The environment
deliberately disables World integration and WLD transfers. It permits agents to
edit code and run deterministic tests, but it does not authorize live
integration testing.

The two `WORLD_AID_*` controls are required implementation contracts, while
the `HF_*_OFFLINE` and `TRANSFORMERS_OFFLINE` values are library behavior
hints. None of these variables blocks sockets. Run this command only inside the
Gate 0B-reviewed OS/container default-deny egress policy, with the approved
implementation-provider/local-fixture allowlist, no live secrets, and the
network-spy/deny fixture enabled in every validation process. Until the new
guards have fail-closed tests, the existing `WORLD_ID_ENABLED=0`, external
egress enforcement, absent live secrets, and the taskboard prohibition on
remote validations are all required boundaries.

Immediately before launch, verify the signed launch record, its bound
selection record, the implementation dry-run manifest, and the immutable
preflight receipt. Re-run the AppArmor namespace probe in the same host
environment. Any failure is a hard stop:

```bash
test -n "${WORLD_AID_ALLOWED_SIGNERS:-}"
test -f "$WORLD_AID_ALLOWED_SIGNERS"

PYTHONDONTWRITEBYTECODE=1 \
python scripts/verify_world_aid_gate_0b.py \
  --phase launch \
  --approval data/worldcoin_human_aid/approvals/gate-0b-launch/approval.json \
  --allowed-signers "$WORLD_AID_ALLOWED_SIGNERS" \
  --repo-root . \
  --offline

PYTHONDONTWRITEBYTECODE=1 \
python scripts/verify_world_aid_preflight_receipt.py \
  --verify \
  --repo-root . \
  --objective-path docs/planning/WORLDCOIN_HUMAN_AID_OBJECTIVE_HEAP.md \
  --generated-root "$WORLD_AID_GENERATED_ROOT" \
  --receipt "$WORLD_AID_GENERATED_ROOT/preflight-receipt.json"

aa-exec -p linux-sandbox -- unshare -Urn /bin/true

env \
  WORLD_ID_ENABLED=0 \
  WORLD_AID_EXTERNAL_CALLS_ENABLED=0 \
  WORLD_AID_WLD_TRANSFERS_ENABLED=0 \
  IPFS_ACCELERATE_AGENT_DISABLE_SUBAGENTS=1 \
  IPFS_ACCEL_SKIP_CORE=1 \
  IPFS_KIT_DISABLE=1 \
  HF_HUB_OFFLINE=1 \
  HF_DATASETS_OFFLINE=1 \
  TRANSFORMERS_OFFLINE=1 \
  NPM_CONFIG_OFFLINE=true \
  PIP_NO_INDEX=1 \
  CARGO_NET_OFFLINE=true \
  GIT_TERMINAL_PROMPT=0 \
  PYTHONPATH=ipfs_accelerate_py \
python -m ipfs_accelerate_py.agent_supervisor.bundle_supervisor \
  --repo-root . \
  --bundle-index-path "$WORLD_AID_GENERATED_ROOT/launch_profiles/implementation.index.duckdb" \
  --state-root data/worldcoin_human_aid/agent_supervisor/lane_state \
  --worktree-root /tmp/worldcoin-human-aid-agent-worktrees \
  --log-dir data/worldcoin_human_aid/agent_supervisor/logs \
  --manifest-path data/worldcoin_human_aid/agent_supervisor/lane-manifest.json \
  --metrics-path data/worldcoin_human_aid/agent_supervisor/scheduler-metrics.json \
  --coordination-path data/worldcoin_human_aid/agent_supervisor/coordination.duckdb \
  --task-prefix WORLDCOIN-AUTO- \
  --merge-target-branch "$WORLD_AID_MERGE_TARGET_BRANCH" \
  --worktree-submodule-path ipfs_accelerate_py \
  --worktree-submodule-path ipfs_datasets_py \
  --implementation-command 'aa-exec -p linux-sandbox -- codex --ask-for-approval never --disable apps --disable browser_use --disable browser_use_external --disable browser_use_full_cdp_access --disable in_app_browser --disable multi_agent --disable multi_agent_v2 -c web_search=\"disabled\" exec --ephemeral --sandbox workspace-write -' \
  --lease-ms 300000 \
  --heartbeat-interval 5 \
  --implementation-timeout 3600 \
  --max-restarts 1 \
  --max-task-attempts 1 \
  --max-lanes 2 \
  --implement \
  --start
```

This command runs in the foreground. Keep its terminal available for a graceful
stop. The initial launch disables automatic retries. Inspect and preserve the
first failure receipt before a separately reviewed relaunch; do not increase
the retry limit blindly.

The live-feature-disabled profile applies to World/Hugging Face/model-data
integrations inside the implementation and tests. The agent implementation
provider may require its configured control-plane network, so allow only its
reviewed exact destinations outside this CLI. The network-spy/deny fixture does
not replace the OS/container egress boundary, and the egress boundary does not
replace adapter-level fail-closed tests. Any unexpected egress attempt or
policy-deny event is a hard stop: terminate the run gracefully, preserve
redacted evidence, and follow the recovery procedure below.

Do not create a staging or production variant of this command by flipping the
environment variables. Live actions are short, bounded, human-operated
procedures performed only after the corresponding gate; they are not
long-running supervisor lanes.

## Status

The current CLI has no `status` subcommand. Read the authoritative manifest and
per-lane status files instead:

```bash
python - <<'PY'
from pathlib import Path
import json

base = Path("data/worldcoin_human_aid/agent_supervisor")
manifest_path = base / "lane-manifest.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
summary_keys = (
    "generated_at",
    "scheduler_state",
    "cycle",
    "planned_count",
    "ready_count",
    "blocked_count",
    "running_count",
    "completed_count",
    "started_count",
    "active_worker_pids",
    "backpressure_reasons",
)
print({key: manifest.get(key) for key in summary_keys if key in manifest})

for path in sorted((base / "lane_state").glob("*/state/*_supervisor_status.json")):
    try:
        status = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print({"path": str(path), "error": str(exc)})
        continue
    print({
        "path": str(path),
        "status": status.get("status"),
        "active_task_id": status.get("active_task_id"),
        "last_heartbeat_at": status.get("last_heartbeat_at"),
        "last_error": status.get("last_error"),
    })
PY
```

Confirm the exact process before sending it a signal:

```bash
pgrep -af 'ipfs_accelerate_py.agent_supervisor.bundle_supervisor.*worldcoin_human_aid'
```

An empty queue does not terminate the dynamic scheduler; a running process with
zero ready lanes can be healthy. Use the manifest's backpressure, blocked,
lease, and heartbeat evidence before diagnosing a stall.

## Stop

The current CLI has no `stop` subcommand. For the foreground launch, press
`Ctrl-C`. The scheduler handles `SIGINT`/`SIGTERM`, terminates its owned lane
processes, releases leases that are still fenced to it, and updates the
manifest.

If the process was deliberately managed in another terminal, first use the
`pgrep -af` command above, visually confirm the single exact PID and command,
then request a graceful stop:

```bash
kill -TERM <confirmed-bundle-supervisor-pid>
```

Do not use a broad `pkill`, delete worktrees, or delete
`coordination.duckdb`. If the process does not stop, inspect the manifest, lane
PID files, and logs before escalating. Never kill an unconfirmed PID.

## Resume

The current CLI has no `resume` flag. Resume by rerunning the exact
live-feature-disabled implementation launch command with the same bundle index,
state root, worktree root, manifest, coordination database, task prefix, and
safety environment. Durable coordination state lets the scheduler reconcile
completed work, reap stale ownership, and claim remaining ready work.

Before resuming:

1. verify the prior supervisor process is no longer running;
2. rerun deterministic dependency preflight;
3. inspect `git status --short`, the parent worktree, and nested submodules;
4. inspect the last manifest, per-lane status, and logs;
5. resolve the cause of any repeated restart or timeout;
6. confirm both live-action controls remain `0`; and
7. rerun the non-starting bundle dry run.

Do not reset the board, remove status files, or recreate the coordination
database merely to make blocked work appear ready.

## Recovery

### Invalid dependency CIDs or a cycle

Treat this as a planning error:

1. stop before launch;
2. use `repair_evidence` in the dependency DAG to locate the source goal/task;
3. correct parent/dependency metadata in the reviewed objective heap;
4. preserve the failed generated artifacts for comparison;
5. rerun objective generation with `--repeat-existing` added to the generation
   command only when intentionally rescanning the same discovery fingerprints;
6. review the complete diff; and
7. rerun deterministic preflight and the non-starting dry run.

Never hand-edit CID values. They are content-derived identifiers.

### Abrupt supervisor exit or stale lease

Do not delete the coordination database. Confirm no old scheduler or lane PID is
alive, inspect lease/heartbeat evidence, then resume with the same launch
command. The dynamic scheduler's normal reconciliation is the supported
recovery mechanism.

If coordination data appears corrupt, stop and preserve:

```text
data/worldcoin_human_aid/agent_supervisor/coordination.duckdb
data/worldcoin_human_aid/agent_supervisor/lane-manifest.json
data/worldcoin_human_aid/agent_supervisor/scheduler-metrics.json
data/worldcoin_human_aid/agent_supervisor/lane_state/
data/worldcoin_human_aid/agent_supervisor/logs/
```

Escalate to a maintainer before creating a new coordination database. A fresh
database can lose lease and idempotency evidence.

### Repeated worker restart or timeout

The live launch commands use `--max-restarts 1` to bound each managed
child-loop cycle and `--max-task-attempts 1` to prevent a failed canonical task
from invoking the implementation model again. The outer supervisor may still
run recovery maintenance and open a new child-loop cycle; the durable
canonical-task attempt limit is the control that prevents repeated model
spend. The current supervisor treats `--max-restarts 0` as unbounded, so zero
is not a safe finite-restart setting. Inspect the task
validation command, latest lane log, heartbeat age, implementation-provider
quota/capacity telemetry, dirty worktree, merge conflicts, and task acceptance
evidence. Fix the underlying cause, run the task's deterministic tests
directly, then perform a separately reviewed relaunch. A token limit, rate
limit, provider outage, test failure, merge conflict, and human gate are
different conditions and must not be collapsed into a generic retry.

### Dirty or divergent worktree

Preserve user work. Inspect the parent repository and each configured submodule.
Commit only reviewed lane-owned changes through the normal lane reconciliation
flow. Do not run destructive reset/checkout commands and do not auto-commit
unrelated paths. If ownership is ambiguous, stop and ask the repository owner.

### Human-gated task became claimable

Stop the supervisor. Mark the task blocked in the reviewed taskboard with a
specific missing-approval reason, inspect its dependencies, and regenerate the
bundle index. An agent-created file in `approvals/` is not valid approval.

### Unexpected external request or transaction attempt

This is a hard stop even when the external policy successfully denied the
attempt. Stop immediately, preserve redacted spy/deny and egress-policy
evidence, rotate any exposed credential, verify no transaction was submitted,
inspect chain/provider receipts if submission is ambiguous, and invoke the
security/treasury incident process. Do not retry automatically.

## Completion criteria

Autonomous implementation is complete only when:

- all non-live tasks have deterministic passing tests and reviewed changes;
- proof-of-human, wallet ownership, eligibility, provider authorization, and
  payout status remain separate in the model and APIs;
- simulated proofs are rejected by all money-moving paths;
- privacy/redaction tests show private documents and World identifiers do not
  escape;
- local-chain tests cover replay, duplicate submission, failed receipt,
  mismatched transfer log, reorg, timeout, pause, and reconciliation;
- accessibility and manual-review fallbacks work without World ID;
- no staging or production evidence was fabricated by an agent;
- each real-world gate was performed and signed by its named human owners; and
- production release and every production WLD disbursement remain under the
  reviewed human and treasury approval policy.
