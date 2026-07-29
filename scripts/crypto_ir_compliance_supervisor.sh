#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ACCELERATE_ROOT="${IPFS_ACCELERATE_SOURCE_ROOT:-${REPO_ROOT}/ipfs_accelerate_py}"
PYTHON_BIN="${CRYPTO_IR_COMPLIANCE_PYTHON:-python3}"
CODEX_BIN="${CRYPTO_IR_COMPLIANCE_CODEX_BIN:-/usr/local/bin/codex}"
GROK_BIN="${CRYPTO_IR_COMPLIANCE_GROK_BIN:-/home/barberb/.local/bin/grok}"
GROK_MODEL="${CRYPTO_IR_COMPLIANCE_GROK_MODEL:-grok-4.5}"

PROGRAM_ROOT="${REPO_ROOT}/data/crypto_ir_compliance/agent_supervisor"
OBJECTIVE_PATH="${REPO_ROOT}/docs/planning/CRYPTO_IR_COMPLIANCE_OBJECTIVES.md"
PLAN_PATH="${REPO_ROOT}/docs/planning/CRYPTO_IR_COMPLIANCE_PLAN.md"
TODO_PATH="${REPO_ROOT}/docs/planning/CRYPTO_IR_COMPLIANCE_TODO.md"
DISCOVERY_DIR="${PROGRAM_ROOT}/discovery"
BUNDLE_DIR="${PROGRAM_ROOT}/bundles"
DATASET_DIR="${PROGRAM_ROOT}/datasets"
GRAPH_PATH="${PROGRAM_ROOT}/objective_graph.json"
VECTOR_PATH="${BUNDLE_DIR}/todo_vector_index.json"
GENERATION_PATH="${PROGRAM_ROOT}/objective_generation.json"
PLAN_EVALUATION_PATH="${PROGRAM_ROOT}/plan_evaluations.json"
ANALYSIS_ESCALATION_PATH="${PROGRAM_ROOT}/analysis_escalation.json"
GOAL_QUALITY_PATH="${PROGRAM_ROOT}/goal-quality.json"
REQUIRE_TYPED_GOALS="${CRYPTO_IR_COMPLIANCE_REQUIRE_TYPED_GOALS:-0}"

RUNTIME_ROOT="${PROGRAM_ROOT}/runtime"
LIFECYCLE_DIR="${RUNTIME_ROOT}/lifecycle"
STATE_ROOT="${RUNTIME_ROOT}/state"
WORKTREE_ROOT="${RUNTIME_ROOT}/worktrees"
MERGE_QUEUE_DIR="${RUNTIME_ROOT}/merge_queue"
LOG_DIR="${RUNTIME_ROOT}/logs"
LIFECYCLE_LOCK="${LIFECYCLE_DIR}/launcher.lock"

CODEX_STATE_DIR="${STATE_ROOT}/codex"
GROK_STATE_DIR="${STATE_ROOT}/grok"
CODEX_STATE_PREFIX="crypto_ir_compliance_codex"
GROK_STATE_PREFIX="crypto_ir_compliance_grok"
CODEX_LOG="${LOG_DIR}/codex-supervisor.log"
GROK_LOG="${LOG_DIR}/grok-supervisor.log"

TASK_HEADER_PREFIX="## CRYPTOIR-"
TASK_ID_PREFIX="CRYPTOIR-"
GOAL_ID_PREFIX="CRYPTOIR-G"
MERGE_TARGET_BRANCH="codex/crypto-ir-contract-compliance"

export PYTHONPATH="${ACCELERATE_ROOT}${PYTHONPATH:+:${PYTHONPATH}}"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONHASHSEED=0
export IPFS_ACCELERATE_DUCKDB_ONLY=1
export IPFS_ACCEL_SKIP_CORE=1
export IPFS_KIT_DISABLE=1
export IPFS_DATASETS_AUTO_INSTALL=false
export IPFS_AUTO_INSTALL=false
export IPFS_DATASETS_PY_MINIMAL_IMPORTS=1

require_file() {
  local path="$1"
  if [[ ! -f "${path}" ]]; then
    echo "required file is missing: ${path}" >&2
    exit 2
  fi
}

require_executable() {
  local path="$1"
  if [[ ! -x "${path}" ]]; then
    echo "required executable is missing: ${path}" >&2
    exit 2
  fi
}

require_target_checkout() {
  local current_branch=""
  current_branch="$(git -C "${REPO_ROOT}" branch --show-current)"
  if [[ "${current_branch}" != "${MERGE_TARGET_BRANCH}" ]]; then
    echo "launcher must run from ${MERGE_TARGET_BRANCH}; current branch is ${current_branch:-detached}" >&2
    return 2
  fi
}

validate_objective_control_plane() {
  "${PYTHON_BIN}" - \
    "${OBJECTIVE_PATH}" "${GOAL_QUALITY_PATH}" "${REQUIRE_TYPED_GOALS}" <<'PY'
import collections
import json
import pathlib
import sys

from ipfs_accelerate_py.agent_supervisor.goal_quality import (
    lint_objective_markdown,
)
from ipfs_accelerate_py.agent_supervisor.objective_graph import (
    _strict_goal_hierarchy_errors,
    parse_goal_heap,
)
from ipfs_accelerate_py.agent_supervisor.objective_tracker import (
    write_objective_goal_quality_report,
)

objective_path = pathlib.Path(sys.argv[1])
quality_path = pathlib.Path(sys.argv[2])
require_typed = sys.argv[3].strip().lower() in {"1", "true", "yes", "on"}
text = objective_path.read_text(encoding="utf-8")
goals = parse_goal_heap(text)
by_id = {goal.goal_id: goal for goal in goals}
errors = list(_strict_goal_hierarchy_errors(goals))

roots = sorted(
    goal.goal_id for goal in goals if not goal.parent_goal_ids
)
if roots != ["CRYPTOIR-G000"]:
    errors.append(f"expected sole CRYPTOIR-G000 root, found {roots!r}")
root = by_id.get("CRYPTOIR-G000")
if root is None:
    errors.append("CRYPTOIR-G000 is missing")
elif root.lifecycle_state_value != "blocked":
    errors.append(
        "CRYPTOIR-G000 must remain blocked/review-only, found "
        f"{root.lifecycle_state_value!r}"
    )

missing_dependencies = sorted(
    {
        f"{goal.goal_id}->{dependency}"
        for goal in goals
        for dependency in goal.dependencies
        if dependency and dependency not in by_id
    }
)
if missing_dependencies:
    errors.append(
        "unresolved dependency edges: " + ", ".join(missing_dependencies)
    )

dependency_state: dict[str, int] = {}
dependency_stack: list[str] = []

def visit(goal_id: str) -> None:
    state = dependency_state.get(goal_id, 0)
    if state == 2:
        return
    if state == 1:
        start = (
            dependency_stack.index(goal_id)
            if goal_id in dependency_stack
            else 0
        )
        cycle = dependency_stack[start:] + [goal_id]
        errors.append("dependency cycle: " + " -> ".join(cycle))
        return
    dependency_state[goal_id] = 1
    dependency_stack.append(goal_id)
    for dependency in by_id[goal_id].dependencies:
        if dependency in by_id:
            visit(dependency)
    dependency_stack.pop()
    dependency_state[goal_id] = 2

for goal_id in sorted(by_id):
    visit(goal_id)

if errors:
    for error in sorted(set(errors)):
        print(f"objective control-plane error: {error}", file=sys.stderr)
    raise SystemExit(2)

quality_path.parent.mkdir(parents=True, exist_ok=True)
compatibility = write_objective_goal_quality_report(
    objective_path,
    quality_path,
)
typed = lint_objective_markdown(text)
typed_accepted = sum(report.accepted for report in typed)
typed_rejected = len(typed) - typed_accepted
debt_counts: collections.Counter[str] = collections.Counter(
    debt.code.value
    for report in typed
    for debt in report.debt
)
print(
    json.dumps(
        {
            "goal_count": len(goals),
            "root_goal_id": roots[0],
            "legacy_structure_accepted": True,
            "compatibility_report_id": compatibility.content_id,
            "strict_typed_accepted": typed_accepted,
            "strict_typed_rejected": typed_rejected,
            "strict_typed_debt": dict(sorted(debt_counts.items())),
            "strict_typed_required": require_typed,
        },
        sort_keys=True,
    )
)
if require_typed and typed_rejected:
    print(
        "strict typed-goal admission is required but the current heap has "
        f"{typed_rejected} rejected goals",
        file=sys.stderr,
    )
    raise SystemExit(2)
PY
}

prepare_runtime() {
  require_file "${OBJECTIVE_PATH}"
  require_file "${PLAN_PATH}"
  require_file "${TODO_PATH}"
  require_file "${ACCELERATE_ROOT}/ipfs_accelerate_py/agent_supervisor/objective_daemon.py"
  require_file "${ACCELERATE_ROOT}/ipfs_accelerate_py/agent_supervisor/todo_daemon/implementation_supervisor.py"
  mkdir -p \
    "${DISCOVERY_DIR}" \
    "${BUNDLE_DIR}" \
    "${DATASET_DIR}" \
    "${LIFECYCLE_DIR}" \
    "${CODEX_STATE_DIR}" \
    "${GROK_STATE_DIR}" \
    "${WORKTREE_ROOT}/codex" \
    "${WORKTREE_ROOT}/grok" \
    "${MERGE_QUEUE_DIR}" \
    "${LOG_DIR}"
}

pid_file_for() {
  printf '%s/%s_supervisor.pid\n' "$1" "$2"
}

daemon_pid_file_for() {
  printf '%s/%s_managed_daemon.pid\n' "$1" "$2"
}

supervisor_status_file_for() {
  printf '%s/%s_supervisor_status.json\n' "$1" "$2"
}

read_live_pid() {
  local path="$1"
  local pid=""
  if [[ -f "${path}" ]]; then
    pid="$(tr -cd '0-9' <"${path}")"
  fi
  if [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null; then
    printf '%s\n' "${pid}"
    return 0
  fi
  return 1
}

read_live_supervisor_pid() {
  local state_dir="$1"
  local state_prefix="$2"
  local pid=""
  if pid="$(read_live_pid "$(pid_file_for "${state_dir}" "${state_prefix}")")"; then
    printf '%s\n' "${pid}"
    return 0
  fi
  if [[ -f "$(supervisor_status_file_for "${state_dir}" "${state_prefix}")" ]]; then
    pid="$(
      sed -n \
        's/^[[:space:]]*"supervisor_pid":[[:space:]]*\([0-9][0-9]*\),\{0,1\}[[:space:]]*$/\1/p' \
        "$(supervisor_status_file_for "${state_dir}" "${state_prefix}")" | head -n 1
    )"
  fi
  if [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null; then
    printf '%s\n' "${pid}"
    return 0
  fi
  return 1
}

lane_fully_running() {
  local state_dir="$1"
  local state_prefix="$2"
  read_live_supervisor_pid "${state_dir}" "${state_prefix}" >/dev/null \
    && read_live_pid "$(daemon_pid_file_for "${state_dir}" "${state_prefix}")" >/dev/null
}

any_lane_process_running() {
  read_live_supervisor_pid "${CODEX_STATE_DIR}" "${CODEX_STATE_PREFIX}" >/dev/null \
    || read_live_pid "$(daemon_pid_file_for "${CODEX_STATE_DIR}" "${CODEX_STATE_PREFIX}")" >/dev/null \
    || read_live_supervisor_pid "${GROK_STATE_DIR}" "${GROK_STATE_PREFIX}" >/dev/null \
    || read_live_pid "$(daemon_pid_file_for "${GROK_STATE_DIR}" "${GROK_STATE_PREFIX}")" >/dev/null
}

require_supervisors_stopped() {
  if any_lane_process_running; then
    echo "this operation requires both supervisors and managed daemons to be stopped" >&2
    echo "run '$0 stop', wait for both lanes to exit, then retry" >&2
    return 1
  fi
}

with_lifecycle_lock() {
  local lifecycle_fd
  local status=0
  mkdir -p "${LIFECYCLE_DIR}"
  require_executable "$(command -v flock || true)"
  exec {lifecycle_fd}>"${LIFECYCLE_LOCK}"
  if ! flock -w 60 "${lifecycle_fd}"; then
    echo "timed out waiting for supervisor lifecycle lock: ${LIFECYCLE_LOCK}" >&2
    exec {lifecycle_fd}>&-
    return 1
  fi
  "$@" || status=$?
  flock -u "${lifecycle_fd}"
  exec {lifecycle_fd}>&-
  return "${status}"
}

read_nonempty_json_field() {
  "${PYTHON_BIN}" -c \
    'import json, pathlib, sys
try:
    value = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")).get(sys.argv[2])
except (OSError, ValueError, TypeError):
    raise SystemExit(1)
if value in (None, "", [], {}):
    raise SystemExit(1)
print(json.dumps(value, sort_keys=True))' \
    "$1" "$2"
}

seed_objectives() {
  local force_existing_goals="${1:-true}"
  local -a forced_goal_args=()
  prepare_runtime
  require_target_checkout
  require_supervisors_stopped
  validate_objective_control_plane
  if [[ "${force_existing_goals}" == "true" ]]; then
    while IFS= read -r goal_id; do
      if [[ "${goal_id}" != "CRYPTOIR-G000" ]]; then
        forced_goal_args+=(--force-goal-id "${goal_id}")
      fi
    done < <(
      awk '$1 == "##" && $2 ~ /^CRYPTOIR-G[0-9]+$/ {print $2}' "${OBJECTIVE_PATH}"
    )
  fi
  (
    cd "${REPO_ROOT}"
    # No --generate-plan-branches or --escalate-low-backlog-analysis:
    # seeding/refill is deterministic and never calls an LLM.
    "${PYTHON_BIN}" -m ipfs_accelerate_py.agent_supervisor.objective_daemon \
      --repo-root "${REPO_ROOT}" \
      --objective-path "${OBJECTIVE_PATH}" \
      --todo-path "${TODO_PATH}" \
      --discovery-dir "${DISCOVERY_DIR}" \
      --bundle-dir "${BUNDLE_DIR}" \
      --dataset-dir "${DATASET_DIR}" \
      --graph-path "${GRAPH_PATH}" \
      --todo-vector-index-path "${VECTOR_PATH}" \
      --objective-generation-path "${GENERATION_PATH}" \
      --plan-evaluation-path "${PLAN_EVALUATION_PATH}" \
      --analysis-escalation-path "${ANALYSIS_ESCALATION_PATH}" \
      --scan-exclude-path data \
      --scan-exclude-path artifacts \
      --scan-exclude-path ipfs_accelerate_py/data \
      --scan-exclude-path ipfs_datasets_py/archive \
      --scan-exclude-path ipfs_datasets_py/workspace \
      --task-prefix "${TASK_ID_PREFIX}" \
      --goal-prefix "${GOAL_ID_PREFIX}" \
      --objective-summary-prefix "Implement Crypto IR compliance objective" \
      --discovery-output-path data/crypto_ir_compliance/agent_supervisor/discovery \
      --max-findings 128 \
      --surplus-findings-per-goal 1 \
      --surplus-min-terms-per-todo 2 \
      --max-refinement-children 4 \
      --max-refinement-depth 5 \
      --no-reconcile-goal-completion \
      --no-persist-ast-dataset \
      --objective-generation-max-depth 4 \
      --objective-generation-max-breadth 4 \
      --objective-generation-max-new-work 24 \
      --objective-generation-max-open-work 96 \
      --objective-generation-token-budget 4096 \
      --objective-generation-max-retries 1 \
      "${forced_goal_args[@]}" \
      --log-level INFO
  )
}

common_supervisor_args() {
  local state_dir="$1"
  local state_prefix="$2"
  local shard_index="$3"
  local worktree_dir="$4"
  printf '%s\0' \
    --todo-path "${TODO_PATH}" \
    --state-dir "${state_dir}" \
    --state-prefix "${state_prefix}" \
    --task-prefix "${TASK_HEADER_PREFIX}" \
    --implement \
    --task-shard-count 2 \
    --task-shard-index "${shard_index}" \
    --max-task-attempts 3 \
    --implementation-retry-budget 3 \
    --validation-retry-budget 3 \
    --merge-retry-budget 3 \
    --implementation-timeout 3600 \
    --implementation-max-timeout 7200 \
    --implementation-log-stall-seconds 1200 \
    --daemon-interval 60 \
    --check-interval 30 \
    --stale-seconds 1800 \
    --watchdog-startup-grace-seconds 300 \
    --worktree-root "${worktree_dir}" \
    --worktree-submodule-path ipfs_datasets_py \
    --merge-target-branch "${MERGE_TARGET_BRANCH}" \
    --merge-queue-dir "${MERGE_QUEUE_DIR}" \
    --implementation-protected-path docs/planning/CRYPTO_IR_COMPLIANCE_PLAN.md \
    --implementation-protected-path docs/planning/CRYPTO_IR_COMPLIANCE_OBJECTIVES.md \
    --implementation-protected-path docs/planning/CRYPTO_IR_COMPLIANCE_TODO.md \
    --log-level INFO
}

reconcile_lane() {
  local label="$1"
  local state_dir="$2"
  local state_prefix="$3"
  local shard_index="$4"
  local worktree_dir="$5"
  local -a args=(
    --once
    --reconciliation-only
    --fail-on-reconciliation-error
    --todo-path "${TODO_PATH}"
    --state-dir "${state_dir}"
    --state-prefix "${state_prefix}"
    --task-prefix "${TASK_HEADER_PREFIX}"
    --task-shard-count 2
    --task-shard-index "${shard_index}"
    --worktree-root "${worktree_dir}"
    --worktree-submodule-path ipfs_datasets_py
    --merge-target-branch "${MERGE_TARGET_BRANCH}"
    --merge-queue-dir "${MERGE_QUEUE_DIR}"
    --worktree-reconciliation-max-merges 1
    --implementation-protected-path docs/planning/CRYPTO_IR_COMPLIANCE_PLAN.md
    --implementation-protected-path docs/planning/CRYPTO_IR_COMPLIANCE_OBJECTIVES.md
    --implementation-protected-path docs/planning/CRYPTO_IR_COMPLIANCE_TODO.md
    --no-objective-task-janitor
    --no-objective-goal-refinement
    --no-objective-goal-migration
    --log-level INFO
  )
  echo "Running strict ${label} reconciliation preflight."
  (
    cd "${REPO_ROOT}"
    "${PYTHON_BIN}" \
      -m ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_supervisor \
      "${args[@]}"
  )
}

run_reconciliation_preflight() {
  prepare_runtime
  require_target_checkout
  require_supervisors_stopped
  validate_objective_control_plane
  reconcile_lane "Codex" "${CODEX_STATE_DIR}" "${CODEX_STATE_PREFIX}" 0 "${WORKTREE_ROOT}/codex"
  reconcile_lane "Grok" "${GROK_STATE_DIR}" "${GROK_STATE_PREFIX}" 1 "${WORKTREE_ROOT}/grok"
}

start_codex_lane() {
  local -a args
  mapfile -d '' -t args < <(
    common_supervisor_args "${CODEX_STATE_DIR}" "${CODEX_STATE_PREFIX}" 0 "${WORKTREE_ROOT}/codex"
  )
  args+=(
    --implementation-command
    "${CODEX_BIN} exec --dangerously-bypass-approvals-and-sandbox --ephemeral -C . -"
    --objective-refill-scan
    --objective-path "${OBJECTIVE_PATH}"
    --objective-graph-path "${GRAPH_PATH}"
    --objective-bundle-dir "${BUNDLE_DIR}"
    --objective-dataset-dir "${DATASET_DIR}"
    --objective-discovery-dir "${DISCOVERY_DIR}"
    --objective-discovery-output-path data/crypto_ir_compliance/agent_supervisor/discovery
    --objective-summary-prefix "Implement Crypto IR compliance objective"
    --objective-goal-prefix "${GOAL_ID_PREFIX}"
    --objective-root-goal-id CRYPTOIR-G000
    --objective-root-goal-title "Deliver Crypto IR contract assurance and transaction compliance"
    --objective-tracking-document-title "Crypto IR, Smart-Contract Assurance, and Transaction Compliance Objective Heap"
    --objective-mission-term "crypto,wallet,contract,proof,security,sanctions,compliance,knowledge-graph,transaction"
    --objective-scan-min-open-tasks 4
    --objective-scan-max-findings 16
    --objective-scan-cooldown-seconds 300
    --objective-refill-timeout-seconds 900
    --objective-max-refinement-children 4
    --objective-max-refinement-depth 5
    --objective-surplus-findings-per-goal 2
    --objective-surplus-min-terms-per-todo 2
    --objective-todo-vector-index-path "${VECTOR_PATH}"
    --no-objective-ast-dataset
    --no-objective-goal-completion-reconcile
    --no-objective-goal-migration
    --auto-commit-generated-dirty
    --generated-dirty-path docs/planning/CRYPTO_IR_COMPLIANCE_OBJECTIVES.md
    --generated-dirty-path docs/planning/CRYPTO_IR_COMPLIANCE_TODO.md
    --generated-dirty-path data/crypto_ir_compliance/agent_supervisor
  )
  (
    cd "${REPO_ROOT}"
    nohup setsid --fork "${PYTHON_BIN}" \
      -m ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_supervisor \
      "${args[@]}" </dev/null >>"${CODEX_LOG}" 2>&1 &
  )
}

start_grok_lane() {
  local -a args
  mapfile -d '' -t args < <(
    common_supervisor_args "${GROK_STATE_DIR}" "${GROK_STATE_PREFIX}" 1 "${WORKTREE_ROOT}/grok"
  )
  args+=(
    --no-objective-task-janitor
    --no-objective-goal-refinement
    --no-objective-goal-migration
  )
  (
    cd "${REPO_ROOT}"
    IPFS_ACCELERATE_AGENT_IMPLEMENTATION_PROVIDER=grok-build \
    IPFS_ACCELERATE_AGENT_GROK_BIN="${GROK_BIN}" \
    IPFS_ACCELERATE_AGENT_GROK_MODEL="${GROK_MODEL}" \
    nohup setsid --fork "${PYTHON_BIN}" \
      -m ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_supervisor \
      "${args[@]}" </dev/null >>"${GROK_LOG}" 2>&1 &
  )
}

wait_for_lane() {
  local label="$1"
  local state_dir="$2"
  local state_prefix="$3"
  local attempt
  for attempt in {1..60}; do
    if lane_fully_running "${state_dir}" "${state_prefix}"; then
      echo "${label} supervisor started with pid $(read_live_supervisor_pid "${state_dir}" "${state_prefix}") and managed daemon pid $(read_live_pid "$(daemon_pid_file_for "${state_dir}" "${state_prefix}")")."
      return 0
    fi
    sleep 1
  done
  echo "${label} supervisor and managed daemon did not both become live within 60 seconds." >&2
  return 1
}

start_supervisors() {
  prepare_runtime
  require_target_checkout
  require_executable "${CODEX_BIN}"
  require_executable "${GROK_BIN}"
  if lane_fully_running "${CODEX_STATE_DIR}" "${CODEX_STATE_PREFIX}" \
    && lane_fully_running "${GROK_STATE_DIR}" "${GROK_STATE_PREFIX}"; then
    echo "Both supervisors are already running."
    show_status
    return
  fi
  if any_lane_process_running; then
    echo "refusing to start from a partial lane state; run '$0 stop' and retry" >&2
    return 1
  fi
  if [[ ! -f "${GRAPH_PATH}" || ! -f "${BUNDLE_DIR}/index.json" ]]; then
    echo "objective artifacts are absent; run '$0 seed', review and commit the generated control plane, then retry start" >&2
    return 1
  fi
  run_reconciliation_preflight
  start_codex_lane
  start_grok_lane
  wait_for_lane "Codex" "${CODEX_STATE_DIR}" "${CODEX_STATE_PREFIX}"
  wait_for_lane "Grok" "${GROK_STATE_DIR}" "${GROK_STATE_PREFIX}"
  show_status
}

show_lane_status() {
  local label="$1"
  local state_dir="$2"
  local state_prefix="$3"
  local failed=0
  local status_path
  local incident_path="${state_dir}/implementation-protected-path-incident.json"
  local maintenance_error=""
  local supervisor_pid=""
  local daemon_pid=""
  status_path="$(supervisor_status_file_for "${state_dir}" "${state_prefix}")"
  if supervisor_pid="$(read_live_supervisor_pid "${state_dir}" "${state_prefix}")"; then
    echo "${label} supervisor: running (pid ${supervisor_pid})"
    ps -p "${supervisor_pid}" -o pid=,etime=,stat=,args=
  else
    echo "${label} supervisor: stopped"
    return 1
  fi
  if daemon_pid="$(read_live_pid "$(daemon_pid_file_for "${state_dir}" "${state_prefix}")")"; then
    echo "${label} daemon: running (pid ${daemon_pid})"
    ps -p "${daemon_pid}" -o pid=,etime=,stat=,args=
  else
    echo "${label} daemon: starting or stopped"
    failed=1
  fi
  if [[ -f "${incident_path}" ]]; then
    echo "${label} protected-path incident: ${incident_path}"
    failed=1
  fi
  if [[ -f "${status_path}" ]] \
    && maintenance_error="$(read_nonempty_json_field "${status_path}" "last_agentic_maintenance_error" 2>/dev/null)"; then
    echo "${label} maintenance error: ${maintenance_error}"
    failed=1
  fi
  if [[ -f "${state_dir}/${state_prefix}_supervisor_events.jsonl" ]]; then
    echo "${label} last supervisor event:"
    tail -n 1 "${state_dir}/${state_prefix}_supervisor_events.jsonl"
  fi
  return "${failed}"
}

write_health_snapshot() {
  local healthy="$1"
  local codex_supervisor_pid="null"
  local codex_daemon_pid="null"
  local grok_supervisor_pid="null"
  local grok_daemon_pid="null"
  local repository_commit=""
  local datasets_commit=""
  local pid=""
  local tmp_path="${RUNTIME_ROOT}/supervisor-health.json.tmp.$$"
  if pid="$(read_live_supervisor_pid "${CODEX_STATE_DIR}" "${CODEX_STATE_PREFIX}")"; then
    codex_supervisor_pid="${pid}"
  fi
  if pid="$(read_live_pid "$(daemon_pid_file_for "${CODEX_STATE_DIR}" "${CODEX_STATE_PREFIX}")")"; then
    codex_daemon_pid="${pid}"
  fi
  if pid="$(read_live_supervisor_pid "${GROK_STATE_DIR}" "${GROK_STATE_PREFIX}")"; then
    grok_supervisor_pid="${pid}"
  fi
  if pid="$(read_live_pid "$(daemon_pid_file_for "${GROK_STATE_DIR}" "${GROK_STATE_PREFIX}")")"; then
    grok_daemon_pid="${pid}"
  fi
  repository_commit="$(git -C "${REPO_ROOT}" rev-parse HEAD 2>/dev/null || true)"
  datasets_commit="$(git -C "${REPO_ROOT}/ipfs_datasets_py" rev-parse HEAD 2>/dev/null || true)"
  "${PYTHON_BIN}" - \
    "${tmp_path}" "${healthy}" "${MERGE_TARGET_BRANCH}" \
    "${TODO_PATH#${REPO_ROOT}/}" "${GRAPH_PATH#${REPO_ROOT}/}" \
    "${repository_commit}" "${datasets_commit}" \
    "${codex_supervisor_pid}" "${codex_daemon_pid}" "${grok_supervisor_pid}" "${grok_daemon_pid}" \
    "$([[ -f "${CODEX_STATE_DIR}/implementation-protected-path-incident.json" ]] && echo true || echo false)" \
    "$([[ -f "${GROK_STATE_DIR}/implementation-protected-path-incident.json" ]] && echo true || echo false)" <<'PY'
import json
import pathlib
import sys
from datetime import datetime, timezone

(
    output, healthy, branch, board, graph, repository_commit, datasets_commit,
    codex_supervisor, codex_daemon, grok_supervisor, grok_daemon,
    codex_incident, grok_incident,
) = sys.argv[1:]

def pid(value):
    return None if value == "null" else int(value)

payload = {
    "schema": "crypto-ir-contract-compliance-supervisor-health/v1",
    "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "healthy": healthy == "true",
    "merge_target_branch": branch,
    "task_board": board,
    "objective_graph": graph,
    "source": {
        "repository_commit": repository_commit or None,
        "ipfs_datasets_py_commit": datasets_commit or None,
    },
    "codex": {
        "provider": "chatgpt-codex",
        "role": "refill-and-execution-owner",
        "supervisor_pid": pid(codex_supervisor),
        "daemon_pid": pid(codex_daemon),
        "protected_path_incident": codex_incident == "true",
    },
    "grok": {
        "provider": "grok-build",
        "role": "execution-only",
        "supervisor_pid": pid(grok_supervisor),
        "daemon_pid": pid(grok_daemon),
        "protected_path_incident": grok_incident == "true",
    },
}
pathlib.Path(output).write_text(
    json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
    encoding="utf-8",
)
PY
  mv "${tmp_path}" "${RUNTIME_ROOT}/supervisor-health.json"
}

show_status() {
  local failed=0
  local healthy=true
  prepare_runtime
  show_lane_status "Codex" "${CODEX_STATE_DIR}" "${CODEX_STATE_PREFIX}" || failed=1
  show_lane_status "Grok" "${GROK_STATE_DIR}" "${GROK_STATE_PREFIX}" || failed=1
  if [[ "${failed}" -ne 0 ]]; then
    healthy=false
  fi
  write_health_snapshot "${healthy}"
  echo "Objective graph: ${GRAPH_PATH}"
  echo "Bundle index: ${BUNDLE_DIR}/index.json"
  echo "Task board: ${TODO_PATH}"
  echo "Goal quality: ${GOAL_QUALITY_PATH}"
  echo "Health snapshot: ${RUNTIME_ROOT}/supervisor-health.json"
  return "${failed}"
}

request_lane_stop() {
  local label="$1"
  local state_dir="$2"
  local state_prefix="$3"
  local pid=""
  if pid="$(read_live_supervisor_pid "${state_dir}" "${state_prefix}")"; then
    echo "Stopping ${label} supervisor ${pid}."
    kill "${pid}"
    return 0
  fi
  if pid="$(read_live_pid "$(daemon_pid_file_for "${state_dir}" "${state_prefix}")")"; then
    echo "${label} daemon ${pid} is live without its owner; refusing a race-prone direct stop." >&2
    return 1
  fi
  echo "${label} supervisor is already stopped."
}

wait_for_lane_stop() {
  local label="$1"
  local state_dir="$2"
  local state_prefix="$3"
  local state_path="${state_dir}/${state_prefix}_task_state.json"
  local attempt
  local daemon_pid=""
  local supervisor_pid=""
  for attempt in {1..30}; do
    supervisor_pid="$(read_live_supervisor_pid "${state_dir}" "${state_prefix}" 2>/dev/null || true)"
    daemon_pid="$(read_live_pid "$(daemon_pid_file_for "${state_dir}" "${state_prefix}")" 2>/dev/null || true)"
    if [[ -z "${supervisor_pid}" && -z "${daemon_pid}" ]]; then
      break
    fi
    sleep 1
  done
  supervisor_pid="$(read_live_supervisor_pid "${state_dir}" "${state_prefix}" 2>/dev/null || true)"
  daemon_pid="$(read_live_pid "$(daemon_pid_file_for "${state_dir}" "${state_prefix}")" 2>/dev/null || true)"
  if [[ -n "${supervisor_pid}" || -n "${daemon_pid}" ]]; then
    echo "${label} shutdown did not quiesce within 30 seconds." >&2
    return 1
  fi
  if [[ -f "${state_dir}/implementation-protected-path-incident.json" ]]; then
    echo "${label} shutdown preserved a protected-path incident requiring reviewed clearance." >&2
    return 1
  fi
  if [[ -f "${state_dir}/implementation-protected-path-active.json" ]]; then
    echo "${label} shutdown left an active protected-path snapshot." >&2
    return 1
  fi
  if [[ -f "${state_path}" ]] && "${PYTHON_BIN}" -c \
    'import json, pathlib, sys
payload = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
raise SystemExit(0 if payload.get("implementation_in_progress") is True else 1)' \
    "${state_path}"; then
    echo "${label} shutdown left implementation_in_progress=true." >&2
    return 1
  fi
  echo "${label} supervisor and daemon stopped with no active implementation fence."
}

stop_supervisors() {
  local failed=0
  prepare_runtime
  request_lane_stop "Codex" "${CODEX_STATE_DIR}" "${CODEX_STATE_PREFIX}" || failed=1
  request_lane_stop "Grok" "${GROK_STATE_DIR}" "${GROK_STATE_PREFIX}" || failed=1
  wait_for_lane_stop "Codex" "${CODEX_STATE_DIR}" "${CODEX_STATE_PREFIX}" || failed=1
  wait_for_lane_stop "Grok" "${GROK_STATE_DIR}" "${GROK_STATE_PREFIX}" || failed=1
  write_health_snapshot false
  return "${failed}"
}

usage() {
  echo "Usage: $0 {seed|refill|doctor|start|status|stop}"
}

case "${1:-}" in
  seed)
    with_lifecycle_lock seed_objectives true
    ;;
  refill)
    with_lifecycle_lock seed_objectives false
    ;;
  doctor)
    with_lifecycle_lock run_reconciliation_preflight
    ;;
  start)
    with_lifecycle_lock start_supervisors
    ;;
  status)
    show_status
    ;;
  stop)
    with_lifecycle_lock stop_supervisors
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac
