# Voice Customer-Care Agent-Supervisor Runbook

## Program inputs and outputs

The durable goal heap is:

`docs/planning/VOICE_CUSTOMER_CARE_OBJECTIVE_HEAP.md`

The expected generated control state is:

```text
data/voice_customer_care/agent_supervisor/
  VOICE_CUSTOMER_CARE_TODO.md
  discovery/
  objective_bundles/
    index.json
    todo_vector_index.json
    *.todo.md
  objective_datasets/          # optional bounded offline cache, not first-pass state
  objective_graph.json
  objective_generation.json
  plan_evaluations.json
  analysis_escalation.json
  lane_state/
  logs/
  lane-manifest.json
```

The heap uses `VOICE-CARE-G###` goal IDs. Generated implementation tasks use
`VOICE-CARE-AUTO-###`.

## Safety defaults

Autonomous lanes:

- use synthetic/public fixtures and fake/local transports;
- never place a real call, send a message, transfer a caller, mutate a remote
  system, publish a dataset, or start production implementation agents;
- never load production credentials or private caller/case data;
- treat GraphRAG output as a proposal, never execution authority;
- preserve existing Abby voice and 211 portal APIs and tests;
- keep `ipfs_datasets_py` independent of `ipfs_accelerate_py`;
- use canonical MCP/MCP++ and supervisor control surfaces instead of adding a
  second dispatcher;
- stop at a dry-run or explicit blocked state for externally consequential
  operations.

## Validate the heap before generation

From `/home/barberb/211-AI/211-AI`:

```bash
PYTHONPATH=ipfs_accelerate_py python - <<'PY'
from pathlib import Path
from ipfs_accelerate_py.agent_supervisor.objectives.objective_graph import (
    goal_graph,
    parse_goal_heap,
)

path = Path("docs/planning/VOICE_CUSTOMER_CARE_OBJECTIVE_HEAP.md")
goals = parse_goal_heap(path.read_text(encoding="utf-8"))
assert goals
goal_ids = {goal.goal_id for goal in goals}
assert len(goal_ids) == len(goals)
assert all(goal.goal_id.startswith("VOICE-CARE-G") for goal in goals)
assert all(
    parent in goal_ids
    for goal in goals
    for parent in goal.parent_goal_ids
)
assert all(
    dependency in goal_ids
    for goal in goals
    for dependency in goal.dependencies
)
graph = goal_graph(goals)
assert graph["roots"] == ["VOICE-CARE-G001"]
print({"goals": len(goals), "graph_nodes": len(graph["nodes"])})
PY
```

Also review every `Outputs`, `Validation`, `Depends on`, `Parallel lane`, and
`Conflict policy` field. Goal dependencies should be contract dependencies,
not a reason to serialize unrelated data, adapter, portal, or evaluation work.

## Generate goals into subgoals and tasks

The current package layout owns the daemon at
`agent_supervisor.objectives.objective_daemon`. Use the module form below so
the command works even when console entry points have not been installed.

```bash
PYTHONPATH=ipfs_accelerate_py \
python -m ipfs_accelerate_py.agent_supervisor.objectives.objective_daemon \
  --repo-root . \
  --objective-path docs/planning/VOICE_CUSTOMER_CARE_OBJECTIVE_HEAP.md \
  --todo-path data/voice_customer_care/agent_supervisor/VOICE_CUSTOMER_CARE_TODO.md \
  --discovery-dir data/voice_customer_care/agent_supervisor/discovery \
  --bundle-dir data/voice_customer_care/agent_supervisor/objective_bundles \
  --dataset-dir data/voice_customer_care/agent_supervisor/objective_datasets \
  --graph-path data/voice_customer_care/agent_supervisor/objective_graph.json \
  --task-prefix VOICE-CARE-AUTO- \
  --objective-summary-prefix "Implement reusable voice customer-care objective" \
  --discovery-output-path data/voice_customer_care/agent_supervisor/discovery \
  --plan-evaluation-path data/voice_customer_care/agent_supervisor/plan_evaluations.json \
  --analysis-escalation-path data/voice_customer_care/agent_supervisor/analysis_escalation.json \
  --objective-generation-path data/voice_customer_care/agent_supervisor/objective_generation.json \
  --todo-vector-index-path data/voice_customer_care/agent_supervisor/objective_bundles/todo_vector_index.json \
  --protected-output-path docs/planning/VOICE_CUSTOMER_CARE_OBJECTIVE_HEAP.md \
  --protected-output-path docs/planning/VOICE_CUSTOMER_CARE_AGENT_SUPERVISOR_RUNBOOK.md \
  --protected-output-path data/voice_customer_care/agent_supervisor/VOICE_CUSTOMER_CARE_TODO.md \
  --max-findings 40 \
  --surplus-findings-per-goal 1 \
  --no-persist-ast-dataset \
  --objective-generation-max-depth 4 \
  --objective-generation-max-breadth 4 \
  --objective-generation-max-new-work 40 \
  --objective-generation-max-open-work 80 \
  --no-reconcile-goal-completion
```

`--no-reconcile-goal-completion` is required on the first pass. The new goals
must not be closed by token similarity to existing Abby, MCP, portal, or
supervisor code. Completion later requires defining/asserting paths, focused
validation, and typed evidence.

Do not pass `--submit-bundles` during plan generation.

The first pass deliberately uses the scanner's streaming AST/symbol path rather
than persisting a full-checkout AST dataset. The latter can expand Python ASTs
far beyond source size in this composite repository. A persistent
content-addressed AST cache is an optimization to add only after it is sharded,
size-bounded, excludes generated/control state, and can be reproduced from the
same repository and recursive-gitlink identity.

## Review the generated plan

Inspect:

```bash
git diff -- \
  docs/architecture/VOICE_CUSTOMER_CARE_PLATFORM_ARCHITECTURE.md \
  docs/planning/VOICE_CUSTOMER_CARE_OBJECTIVE_HEAP.md \
  docs/planning/VOICE_CUSTOMER_CARE_AGENT_SUPERVISOR_RUNBOOK.md \
  data/voice_customer_care/agent_supervisor

jq '.goals | length' \
  data/voice_customer_care/agent_supervisor/objective_graph.json

jq '.bundles | length' \
  data/voice_customer_care/agent_supervisor/objective_bundles/index.json
```

Review these conditions before implementation:

1. No task authorizes live telephony, paid providers, remote publication, or
   production mutation.
2. Tasks that touch the same public contracts or files are serialized.
3. Dataset/compiler, independent adapter, portal, pack, and evaluation bundles
   retain useful parallel width.
4. Every task has a focused validation command and bounded predicted paths.
5. Cross-submodule tasks name both submodules and have an integration owner.
6. No generated task treats a domain pack as permission to register or execute
   arbitrary code.
7. Generated completion claims cite defining code and focused assertions rather
   than unrelated artifacts containing similar words.
8. Generated model-assisted tasks say `Provider role: grok, codex-review`;
   `grok-implement` would pin the provider and defeat Codex fallback.

## Plan lanes without starting them

The console script may not be installed in a source checkout. This module form
is equivalent:

```bash
PYTHONPATH=ipfs_accelerate_py \
python -m ipfs_accelerate_py.agent_supervisor.objectives.bundle_supervisor \
  --repo-root . \
  --bundle-index-path data/voice_customer_care/agent_supervisor/objective_bundles/index.json \
  --state-root data/voice_customer_care/agent_supervisor/lane_state \
  --worktree-root /tmp/voice-care-agent-worktrees \
  --log-dir data/voice_customer_care/agent_supervisor/logs \
  --manifest-path data/voice_customer_care/agent_supervisor/lane-manifest.json \
  --task-prefix VOICE-CARE-AUTO- \
  --worktree-submodule-path ipfs_accelerate_py \
  --worktree-submodule-path ipfs_datasets_py \
  --worktree-submodule-path ipfs_kit_py \
  --allow-disjoint-submodule-concurrency \
  --max-lanes 6 \
  --no-implement
```

The initial lane families are:

| Lane family | Primary goals | Can begin in parallel |
| --- | --- | --- |
| data/contracts | G002-G005 | Pack schema, graph schema, compiler, then retrieval |
| runtime/security | G006-G010 | Action contracts, catalog, policy, receipts, privacy |
| adapters | G011-G015 | MCP, CLI, Python, workflow, and supervisor after shared gates |
| human/telephony | G016-G017 | Handoff then provider-neutral call control |
| orchestration/API | G018-G020 | Composition, intake, and gateway as dependencies land |
| portal/reference packs | G021-G023 | UI shell plus 211 and non-211 packs |
| assurance/operations | G024-G025 | Formal/adversarial gates and production controls |
| integration/control | G026-G027 | End-to-end proof and supervisor refill |

Shared contracts are intentional serialization points. Adapter implementations
should otherwise remain file-disjoint.

## Provider selection

Use the Grok-first automatic selector for each supervisor process:

```bash
export IPFS_ACCELERATE_AGENT_IMPLEMENTATION_PROVIDER=auto
export IPFS_ACCELERATE_AGENT_GROK_MODEL=grok-4.5
export IPFS_ACCELERATE_AGENT_CODEX_MODEL=gpt-5.6-terra
```

`auto` is the actual Grok-first policy: an authenticated, dispatch-ready Grok
CLI is selected first; Codex is selected when Grok is unavailable before
dispatch. The generated soft role `grok, codex-review` preserves that behavior.
Do not set the provider to `grok` for this program unless you intentionally want
to force Grok and disable fallback.

Fallback is never attempted after a Grok process has started. Quota exhaustion,
runtime failure, policy rejection, validation failure, or a dirty candidate
must defer or fail through the normal gates; the supervisor must not hand a
possibly mutated worktree to Codex. An operator can explicitly force
`codex`/`openai`, but that is an override rather than the default.

Provider selection does not change task authority, protected paths, validation,
leases, or merge gates. If separate forced-provider supervisors are run
concurrently, give them disjoint bundle indexes or exhaustive complementary
exclusion lists and a shared coordination store. Do not let both claim the same
canonical task or edit the same contract surface.

## Start reviewed autonomous lanes

Only after the generated diff and dry-run manifest are reviewed:

```bash
PYTHONPATH=ipfs_accelerate_py \
python -m ipfs_accelerate_py.agent_supervisor.objectives.bundle_supervisor \
  --repo-root . \
  --bundle-index-path data/voice_customer_care/agent_supervisor/objective_bundles/index.json \
  --state-root data/voice_customer_care/agent_supervisor/lane_state \
  --worktree-root /tmp/voice-care-agent-worktrees \
  --log-dir data/voice_customer_care/agent_supervisor/logs \
  --manifest-path data/voice_customer_care/agent_supervisor/lane-manifest.json \
  --task-prefix VOICE-CARE-AUTO- \
  --worktree-submodule-path ipfs_accelerate_py \
  --worktree-submodule-path ipfs_datasets_py \
  --worktree-submodule-path ipfs_kit_py \
  --allow-disjoint-submodule-concurrency \
  --merge-target-branch main \
  --lease-ms 300000 \
  --heartbeat-interval 5 \
  --implementation-timeout 3600 \
  --max-restarts 3 \
  --max-task-attempts 3 \
  --max-lanes 6 \
  --implement \
  --start
```

Use an integration branch instead of `main` when repository policy requires
review before landing. Never enable generated-dirty auto-commit until its exact
path allowlist has been reviewed.

## Bounded refill

Refill is evidence-driven. Run another objective pass only when one of these
changes:

- a goal or child goal reaches a new lifecycle state;
- focused validation or proof evidence lands;
- AST/contract/security analysis emits a novel finding;
- an interface descriptor, domain-pack schema, or action contract changes;
- the healthy backlog falls below the configured target.

For a targeted rescan, repeat `--scope-goal-id`:

```bash
PYTHONPATH=ipfs_accelerate_py \
python -m ipfs_accelerate_py.agent_supervisor.objectives.objective_daemon \
  --repo-root . \
  --objective-path docs/planning/VOICE_CUSTOMER_CARE_OBJECTIVE_HEAP.md \
  --todo-path data/voice_customer_care/agent_supervisor/VOICE_CUSTOMER_CARE_TODO.md \
  --discovery-dir data/voice_customer_care/agent_supervisor/discovery \
  --bundle-dir data/voice_customer_care/agent_supervisor/objective_bundles \
  --dataset-dir data/voice_customer_care/agent_supervisor/objective_datasets \
  --graph-path data/voice_customer_care/agent_supervisor/objective_graph.json \
  --task-prefix VOICE-CARE-AUTO- \
  --objective-summary-prefix "Implement reusable voice customer-care objective" \
  --discovery-output-path data/voice_customer_care/agent_supervisor/discovery \
  --objective-generation-path data/voice_customer_care/agent_supervisor/objective_generation.json \
  --todo-vector-index-path data/voice_customer_care/agent_supervisor/objective_bundles/todo_vector_index.json \
  --protected-output-path docs/planning/VOICE_CUSTOMER_CARE_OBJECTIVE_HEAP.md \
  --protected-output-path docs/planning/VOICE_CUSTOMER_CARE_AGENT_SUPERVISOR_RUNBOOK.md \
  --protected-output-path data/voice_customer_care/agent_supervisor/VOICE_CUSTOMER_CARE_TODO.md \
  --scope-goal-id VOICE-CARE-G024 \
  --scope-goal-id VOICE-CARE-G027 \
  --max-findings 8 \
  --surplus-findings-per-goal 1 \
  --no-persist-ast-dataset
```

Use `--force-goal-id` only to intentionally bypass an existing discovery
fingerprint. Use `--repeat-existing` only during a controlled deduplication
test.

When a gap is too broad, enable bounded heap refinement with conservative
limits:

```text
--refine-objective-heap
--max-refinement-children 4
--max-refinement-depth 4
--objective-generation-max-new-work 12
--objective-generation-max-open-work 80
```

New child goals must preserve the parent safety policy, receive their own
focused validation, and avoid duplicating an existing evidence owner.

## Analyzer-fed targeted repair

Static analyzers, MCP contract parity, formal proof counterexamples, dependency
scanners, and security tools should emit compact findings containing:

- canonical finding identity and content CID;
- affected goal, contract, descriptor, path, and symbol;
- expected and observed behavior;
- evidence/proof/counterexample kind;
- severity, confidence, and exploitability where applicable;
- exact bounded acceptance and validation commands;
- proposed bundle/conflict surface;
- no source-body dump unless the focused implementation task requires it.

The supervisor should deduplicate findings by semantic and content identity,
project them into the owning goal/bundle, and send the implementation provider
only the contract, counterexample, relevant symbol slice, and validation. The
LLM does not need the full repository or conversation history.

## Completion policy

A goal is complete only when:

- its required implementation and focused tests exist;
- validation passes on the exact repository and recursive gitlink identities;
- required contract/proof/security evidence is typed correctly;
- no open child goal owns a required acceptance term;
- cross-submodule compatibility is verified;
- operational or externally consequential work has its required human
  authority.

Textual similarity, an importable symbol, a generated plan, a dry-run lane, or
an unverified solver candidate is not completion evidence.
