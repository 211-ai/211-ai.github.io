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

### Gate 0B: full implementation-board and offline-dependency approval

Required before the full implementation command containing `--start`:

- product owner approves the scope and priority;
- security/privacy reviewer approves the data boundaries and threat model;
- program-policy owner confirms that optional proof of human is separate from
  eligibility;
- accessibility reviewer confirms the manual and non-World-ID fallback;
- repository maintainer approves the generated board, dependency DAG, conflict
  plan, and worktree surfaces;
- maintainers review required npm package versions, integrity checks, licenses,
  provenance, transitive SBOM, and vulnerability findings, then preload the
  exact approved tarballs and a human-produced lockfile in an offline
  cache/internal mirror and demonstrate a verifier-boundary smoke install with
  `npm ci --offline`; the G006 package files may later be rendered only from
  that reviewed input and workers may not open registry egress;
- maintainers inventory required ZKP toolchains (for example Nargo, ProveKit,
  or `bb`), select the reviewed backend, and pre-stage checksum-pinned
  binaries/containers plus licenses and provenance; a reviewed smoke circuit
  must build offline before launch, while the G012 eligibility circuit remains
  a later task output;
- maintainers review and pre-stage checksum-pinned Python wheels for the
  PostgreSQL driver/migration/test boundary and an exact PostgreSQL
  image/binary with digest, license, SBOM, and provenance, then demonstrate
  that an ephemeral local database starts and accepts a smoke transaction with
  all package and container registries denied;
- security reviewer verifies the externally enforced OS/container default-deny
  egress policy and its exact control-plane/local-fixture allowlist;
- security reviewer verifies that the worker environment has no live secrets,
  signing material, production credentials, or treasury access;
- the deterministic network-spy/deny fixture passes and its deliberate egress
  canary proves that an unexpected request is blocked and reported; and
- deterministic preflight and bundle dry run pass.

Record each Gate 0A or Gate 0B decision outside generated task data, with
approver identity, UTC time, reviewed commit, reviewed objective-heap digest,
generated-board digest, scope, and expiration. Gate 0B additionally binds the
human-authored offline-bootstrap manifest and lock/image/toolchain digests. Do
not place secrets or recipient data in either record.

### Gate 1: World staging API approval

Required before the first call to a World staging API:

- Gate 0B is current;
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

All objective-generation outputs use this repository-local root:

```text
data/worldcoin_human_aid/agent_supervisor/
```

Expected paths are:

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
| `lane_state/` | Per-lane durable state |
| `logs/` | Redacted supervisor/lane logs |
| `lane-manifest.json` | Planned or live lane projection |
| `scheduler-metrics.json` | Scheduler metrics projection |
| `coordination.duckdb` | Durable claims, leases, and reconciliation state |
| `approvals/` | Human-authored, non-secret approval references |

Generated planning artifacts must not contain World secrets, recipient data,
raw proof payloads, private document data, or treasury material. The
`approvals/` directory is a reference/evidence location, not an authorization
mechanism by itself.

The first full objective/AST scan can be expensive and can materialize
multi-gigabyte snapshots; approximately 2.5 GB was observed during one scan of
this repository, but the size and runtime vary with the checked-out tree,
submodules, optional dataset backend, and prior cache. Before generation, check
available storage and review these cache paths rather than assuming an exact
cost:

```text
data/worldcoin_human_aid/agent_supervisor/objective_datasets/objective-ast.jsonl
data/worldcoin_human_aid/agent_supervisor/objective_datasets/objective-ast.manifest.json
data/worldcoin_human_aid/agent_supervisor/objective_datasets/objective-ast.parquet
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

```bash
env \
  IPFS_ACCEL_SKIP_CORE=1 \
  IPFS_KIT_DISABLE=1 \
  HF_HUB_OFFLINE=1 \
  HF_DATASETS_OFFLINE=1 \
  TRANSFORMERS_OFFLINE=1 \
  PYTHONPATH=ipfs_accelerate_py \
python -m ipfs_accelerate_py.agent_supervisor.objective_daemon \
  --repo-root . \
  --objective-path docs/planning/WORLDCOIN_HUMAN_AID_OBJECTIVE_HEAP.md \
  --todo-path data/worldcoin_human_aid/agent_supervisor/WORLDCOIN_HUMAN_AID_TODO.md \
  --discovery-dir data/worldcoin_human_aid/agent_supervisor/discovery \
  --bundle-dir data/worldcoin_human_aid/agent_supervisor/objective_bundles \
  --dataset-dir data/worldcoin_human_aid/agent_supervisor/objective_datasets \
  --graph-path data/worldcoin_human_aid/agent_supervisor/objective_graph.json \
  --task-prefix WORLDCOIN-AUTO- \
  --objective-summary-prefix "Implement Worldcoin human-aid objective" \
  --discovery-output-path data/worldcoin_human_aid/agent_supervisor/discovery \
  --plan-evaluation-path data/worldcoin_human_aid/agent_supervisor/plan_evaluations.json \
  --analysis-escalation-path data/worldcoin_human_aid/agent_supervisor/analysis_escalation.json \
  --objective-generation-path data/worldcoin_human_aid/agent_supervisor/objective_generation.json \
  --max-findings 40 \
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
grant a human gate, submit a bundle, or start a worker.

The forced list intentionally omits only G035 and G036, which are
supervisor-terminal `blocked` human gates, and then includes the executable
offline-bootstrap goals G037 through G040. Only the named governance process
may transition G035 or G036 to `reopened` after independently produced
external evidence is reviewed. An agent-created approval/evidence file,
textual match, or completed dependency cannot reopen either goal.

## Review the generated board

At minimum, inspect:

```text
docs/planning/WORLDCOIN_HUMAN_AID_OBJECTIVE_HEAP.md
data/worldcoin_human_aid/agent_supervisor/WORLDCOIN_HUMAN_AID_TODO.md
data/worldcoin_human_aid/agent_supervisor/objective_graph.json
data/worldcoin_human_aid/agent_supervisor/objective_bundles/index.json
data/worldcoin_human_aid/agent_supervisor/objective_bundles/todo_vector_index.json
data/worldcoin_human_aid/agent_supervisor/objective_bundles/*.todo.md
data/worldcoin_human_aid/agent_supervisor/discovery/
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
- generated task, dependency-DAG, and bundle task ID/CID sets are identical,
  and neither blocked goal G035 nor G036 appears in any of them;
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
acceptance criteria, missing active-goal tasks, malformed bundle entries,
dangling dependency CIDs, self-dependencies, dependency cycles, bundle tasks
absent from the dependency graph, or any CID the planner has classified as
invalid.

```bash
env \
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
import re
import sys

from ipfs_accelerate_py.agent_supervisor.objective_graph import parse_goal_heap
from ipfs_accelerate_py.agent_supervisor.todo_vector_index import parse_todo_blocks

root = Path.cwd().resolve()
base = root / "data/worldcoin_human_aid/agent_supervisor"
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
active_goal_ids = set()
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
        active_goal_ids.add(goal.goal_id)
    if goal.status == "blocked":
        blocked_goal_ids.add(goal.goal_id)

expected_blocked_goal_ids = {"WORLDCOIN-G035", "WORLDCOIN-G036"}
if blocked_goal_ids != expected_blocked_goal_ids:
    problems.append(
        "source blocked-goal set differs from the reviewed human gates: "
        f"expected={sorted(expected_blocked_goal_ids)}, "
        f"actual={sorted(blocked_goal_ids)}"
    )

def normalized_acceptance(value):
    return " ".join(str(value or "").split()).casefold()

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

generated_goal_ids = set()
todo_task_ids = set()
todo_task_cids = set()
for task_id, _title, source_line, fields in task_blocks:
    goal_id = str(fields.get("goal_id") or "").strip()
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
    if goal_id in blocked_goal_ids:
        problems.append(f"{location} illegally materializes blocked source goal {goal_id!r}")
        continue

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

missing_active_goal_tasks = sorted(active_goal_ids - generated_goal_ids)
if missing_active_goal_tasks:
    problems.append(
        "active source goals have no generated task blocks: "
        f"{missing_active_goal_tasks}"
    )
unexpected_goal_tasks = sorted(generated_goal_ids - active_goal_ids)
if unexpected_goal_tasks:
    problems.append(
        "generated task blocks reference non-schedulable goals: "
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
        if node_goal_id in blocked_goal_ids:
            problems.append(
                f"{name} node {cid!r} illegally references blocked goal "
                f"{node_goal_id!r}"
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

    unknown_claimable = sorted(
        set(dag.get("claimable_task_cids") or []) - nodes
    )
    if unknown_claimable:
        problems.append(f"{name} has unknown claimable CIDs: {unknown_claimable}")

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
    for task in tasks:
        if not isinstance(task, dict):
            problems.append(f"bundle {bundle_key!r} contains a malformed task")
            continue
        cid = str(task.get("canonical_task_cid") or task.get("task_cid") or "")
        task_id = str(task.get("task_id") or "")
        goal_id = str(task.get("goal_id") or "").strip()
        if task_id:
            bundle_task_ids.add(task_id)
        if cid:
            bundle_task_cids.add(cid)
        if goal_id in blocked_goal_ids:
            problems.append(
                f"bundle {bundle_key!r} task {task_id!r} illegally references "
                f"blocked goal {goal_id!r}"
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
print(
    "WORLDCOIN supervisor preflight passed: "
    f"{len(source_goals)} source goals, {len(headers)} tasks, "
    f"{len(bundles)} bundles, "
    f"{len(canonical_nodes)} dependency nodes, {len(claimable)} claimable roots, "
    "0 invalid dependency CIDs"
)
PY
```

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

## Derive the Gate 0A G002-only execution index

The canonical index remains the reviewed source. The scheduler has no
goal/bundle include flag, and `--max-lanes` limits concurrency rather than
scope. Create a new paired JSON/DuckDB index whose native
`excluded_bundle_keys` fence leaves only the G002 integration-audit bundle.
Never hand-edit only the JSON representation.

```bash
env \
  IPFS_ACCEL_SKIP_CORE=1 \
  IPFS_KIT_DISABLE=1 \
  PYTHONPATH=ipfs_accelerate_py \
python - <<'PY'
from pathlib import Path

from ipfs_accelerate_py.agent_supervisor.artifact_store import (
    read_bundle_index_artifact,
    write_bundle_index_artifact,
)

source = Path(
    "data/worldcoin_human_aid/agent_supervisor/objective_bundles/index.json"
)
destination = Path(
    "data/worldcoin_human_aid/agent_supervisor/"
    "launch_profiles/g002-only.index.json"
)
allowed = {"worldcoin-human-aid/integration-audit"}
payload = read_bundle_index_artifact(source)
known = set(payload.get("bundles") or {})
missing = allowed - known
if missing:
    raise SystemExit(f"missing allowed bundles: {sorted(missing)}")
payload["derived_from_bundle_index"] = str(source)
payload["execution_allowlist"] = sorted(allowed)
payload["excluded_bundle_keys"] = sorted(known - allowed)
write_bundle_index_artifact(destination, payload)

rendered = read_bundle_index_artifact(destination)
if set(rendered.get("excluded_bundle_keys") or ()) != known - allowed:
    raise SystemExit("derived index lost its native exclusion fence")
print({
    "allowed": sorted(allowed),
    "excluded_count": len(known - allowed),
    "index": str(destination),
    "duckdb": str(destination.with_suffix(".duckdb")),
})
PY
```

Then ask the actual lane planner, rather than a hand-written JSON check, to
prove that the execution projection contains exactly G002:

```bash
env \
  IPFS_ACCEL_SKIP_CORE=1 \
  IPFS_KIT_DISABLE=1 \
  PYTHONPATH=ipfs_accelerate_py \
python - <<'PY'
from pathlib import Path

from ipfs_accelerate_py.agent_supervisor.bundle_supervisor import plan_bundle_lanes

index_path = Path(
    "data/worldcoin_human_aid/agent_supervisor/"
    "launch_profiles/g002-only.index.json"
).resolve()
lanes = plan_bundle_lanes(
    bundle_index_path=index_path,
    repo_root=Path.cwd(),
    state_root=Path(
        "data/worldcoin_human_aid/agent_supervisor/lane_state"
    ).resolve(),
    worktree_root=Path("/tmp/worldcoin-human-aid-agent-worktrees"),
    log_dir=Path(
        "data/worldcoin_human_aid/agent_supervisor/logs"
    ).resolve(),
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
print({
    "bundle": lanes[0].bundle_key,
    "task_ids": lanes[0].task_ids,
    "claimable": lanes[0].claimable,
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
  --bundle-index-path data/worldcoin_human_aid/agent_supervisor/launch_profiles/g002-only.index.json \
  --state-root data/worldcoin_human_aid/agent_supervisor/lane_state \
  --worktree-root /tmp/worldcoin-human-aid-agent-worktrees \
  --log-dir data/worldcoin_human_aid/agent_supervisor/logs \
  --manifest-path data/worldcoin_human_aid/agent_supervisor/g002-only-manifest.json \
  --metrics-path data/worldcoin_human_aid/agent_supervisor/g002-only-metrics.json \
  --coordination-path data/worldcoin_human_aid/agent_supervisor/coordination.duckdb \
  --task-prefix WORLDCOIN-AUTO- \
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

```bash
env \
  WORLD_ID_ENABLED=0 \
  WORLD_AID_EXTERNAL_CALLS_ENABLED=0 \
  WORLD_AID_WLD_TRANSFERS_ENABLED=0 \
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
  --bundle-index-path data/worldcoin_human_aid/agent_supervisor/launch_profiles/g002-only.index.json \
  --state-root data/worldcoin_human_aid/agent_supervisor/lane_state \
  --worktree-root /tmp/worldcoin-human-aid-agent-worktrees \
  --log-dir data/worldcoin_human_aid/agent_supervisor/logs \
  --manifest-path data/worldcoin_human_aid/agent_supervisor/g002-only-manifest.json \
  --metrics-path data/worldcoin_human_aid/agent_supervisor/g002-only-metrics.json \
  --coordination-path data/worldcoin_human_aid/agent_supervisor/coordination.duckdb \
  --task-prefix WORLDCOIN-AUTO- \
  --worktree-submodule-path ipfs_accelerate_py \
  --worktree-submodule-path ipfs_datasets_py \
  --implementation-command 'codex --ask-for-approval never --disable apps --disable browser_use --disable browser_use_external --disable browser_use_full_cdp_access --disable in_app_browser --disable multi_agent --disable multi_agent_v2 -c web_search=\"disabled\" exec --ephemeral --sandbox workspace-write -' \
  --poll-interval 15 \
  --daemon-interval 15 \
  --check-interval 15 \
  --lease-ms 300000 \
  --heartbeat-interval 5 \
  --implementation-timeout 3600 \
  --max-restarts 0 \
  --max-lanes 1 \
  --implement \
  --start
```

Do not add `--once`: the scheduler can exit after one reconciliation cycle
while leaving a spawned child alive. Keep this foreground process available
for graceful stop. After G002 settles, stop and review its canonical successful
bundle receipt and offline-bootstrap proposal before deriving a wider immutable
launch profile. Do not mutate a live derived index in place.

## Bundle-supervisor dry run

This command plans lanes and writes a manifest. It does not contain `--start`
and therefore starts no workers.

```bash
env \
  IPFS_ACCEL_SKIP_CORE=1 \
  IPFS_KIT_DISABLE=1 \
  HF_HUB_OFFLINE=1 \
  HF_DATASETS_OFFLINE=1 \
  TRANSFORMERS_OFFLINE=1 \
  PYTHONPATH=ipfs_accelerate_py \
python -m ipfs_accelerate_py.agent_supervisor.bundle_supervisor \
  --repo-root . \
  --bundle-index-path data/worldcoin_human_aid/agent_supervisor/objective_bundles/index.json \
  --state-root data/worldcoin_human_aid/agent_supervisor/lane_state \
  --worktree-root /tmp/worldcoin-human-aid-agent-worktrees \
  --log-dir data/worldcoin_human_aid/agent_supervisor/logs \
  --manifest-path data/worldcoin_human_aid/agent_supervisor/lane-manifest.json \
  --metrics-path data/worldcoin_human_aid/agent_supervisor/scheduler-metrics.json \
  --coordination-path data/worldcoin_human_aid/agent_supervisor/coordination.duckdb \
  --task-prefix WORLDCOIN-AUTO- \
  --worktree-submodule-path ipfs_accelerate_py \
  --worktree-submodule-path ipfs_datasets_py \
  --max-lanes 2 \
  --no-implement \
  --once
```

Confirm that the dry run started nothing:

```bash
python - <<'PY'
from pathlib import Path
import json

path = Path("data/worldcoin_human_aid/agent_supervisor/lane-manifest.json")
manifest = json.loads(path.read_text(encoding="utf-8"))
schemas = {
    "ipfs_accelerate_py.agent_supervisor.bundle_supervisor",
    "ipfs_accelerate_py.agent_supervisor.dynamic_bundle_scheduler@1",
}
assert manifest.get("schema") in schemas
assert int(manifest.get("planned_count") or 0) > 0
assert int(manifest.get("started_count") or 0) == 0
assert int(manifest.get("running_count") or 0) == 0
assert int(manifest.get("active_worker_count") or 0) == 0
assert not (manifest.get("started") or [])
assert not (manifest.get("launched_task_cids") or [])
assert not (manifest.get("active_worker_pids") or [])
ready = manifest.get("claimable_count")
if ready is None:
    ready = manifest.get("ready_count", 0)
print({
    "schema": manifest["schema"],
    "planned": manifest["planned_count"],
    "claimable_or_ready": ready,
    "dependency_blocked": manifest.get("blocked_count", 0),
    "started": manifest.get("started_count", 0),
    "running": manifest.get("running_count", 0),
    "active_worker_pids": manifest.get("active_worker_pids", []),
    "launched_task_cids": manifest.get("launched_task_cids", []),
})
PY
```

Dependency-blocked lanes are expected in a valid DAG. Invalid CIDs and cycles
are not; those are rejected by the earlier preflight.

## Live-feature-disabled implementation launch

Use this only after Gate 0B is recorded and all earlier review/preflight steps
pass. The environment deliberately disables World integration and WLD
transfers. It permits agents to edit code and run deterministic tests, but it
does not authorize live integration testing.

The two `WORLD_AID_*` controls are required implementation contracts, while
the `HF_*_OFFLINE` and `TRANSFORMERS_OFFLINE` values are library behavior
hints. None of these variables blocks sockets. Run this command only inside the
Gate 0B-reviewed OS/container default-deny egress policy, with the approved
implementation-provider/local-fixture allowlist, no live secrets, and the
network-spy/deny fixture enabled in every validation process. Until the new
guards have fail-closed tests, the existing `WORLD_ID_ENABLED=0`, external
egress enforcement, absent live secrets, and the taskboard prohibition on
remote validations are all required boundaries.

```bash
env \
  WORLD_ID_ENABLED=0 \
  WORLD_AID_EXTERNAL_CALLS_ENABLED=0 \
  WORLD_AID_WLD_TRANSFERS_ENABLED=0 \
  IPFS_ACCEL_SKIP_CORE=1 \
  IPFS_KIT_DISABLE=1 \
  HF_HUB_OFFLINE=1 \
  HF_DATASETS_OFFLINE=1 \
  TRANSFORMERS_OFFLINE=1 \
  PYTHONPATH=ipfs_accelerate_py \
python -m ipfs_accelerate_py.agent_supervisor.bundle_supervisor \
  --repo-root . \
  --bundle-index-path data/worldcoin_human_aid/agent_supervisor/objective_bundles/index.json \
  --state-root data/worldcoin_human_aid/agent_supervisor/lane_state \
  --worktree-root /tmp/worldcoin-human-aid-agent-worktrees \
  --log-dir data/worldcoin_human_aid/agent_supervisor/logs \
  --manifest-path data/worldcoin_human_aid/agent_supervisor/lane-manifest.json \
  --metrics-path data/worldcoin_human_aid/agent_supervisor/scheduler-metrics.json \
  --coordination-path data/worldcoin_human_aid/agent_supervisor/coordination.duckdb \
  --task-prefix WORLDCOIN-AUTO- \
  --worktree-submodule-path ipfs_accelerate_py \
  --worktree-submodule-path ipfs_datasets_py \
  --lease-ms 300000 \
  --heartbeat-interval 5 \
  --implementation-timeout 3600 \
  --max-restarts 1 \
  --max-lanes 2 \
  --implement \
  --start
```

This command runs in the foreground. Keep its terminal available for a graceful
stop. `--max-restarts 1` bounds automatic retries; repeated failure is evidence
to inspect, not a reason to raise the limit blindly.

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

`--max-restarts 1` intentionally stops a restart loop from consuming unlimited
provider capacity. Inspect the task validation command, latest lane log,
heartbeat age, implementation-provider quota/capacity telemetry, dirty
worktree, merge conflicts, and task acceptance evidence. Fix the underlying
cause, run the task's deterministic tests directly, then resume. A token limit,
rate limit, provider outage, test failure, merge conflict, and human gate are
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
