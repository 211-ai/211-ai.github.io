#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ACCELERATE_ROOT="${IPFS_ACCELERATE_SOURCE_ROOT:-${REPO_ROOT}/ipfs_accelerate_py}"
PYTHON_BIN="${WALLET_PROCESSOR_PYTHON:-python3}"
CODEX_BIN="${WALLET_PROCESSOR_CODEX_BIN:-/usr/local/bin/codex}"
GROK_BIN="${WALLET_PROCESSOR_GROK_BIN:-/home/barberb/.local/bin/grok}"
GROK_MODEL="${WALLET_PROCESSOR_GROK_MODEL:-grok-4.5}"

PROGRAM_ROOT="${REPO_ROOT}/data/wallet_processor_migration/agent_supervisor"
OBJECTIVE_PATH="${REPO_ROOT}/docs/planning/WALLET_PROCESSORS_OBJECTIVES.md"
PLAN_PATH="${REPO_ROOT}/docs/planning/WALLET_PROCESSORS_MIGRATION_PLAN.md"
TODO_PATH="${REPO_ROOT}/docs/planning/WALLET_PROCESSORS_TODO.md"
DISCOVERY_DIR="${PROGRAM_ROOT}/discovery"
BUNDLE_DIR="${PROGRAM_ROOT}/bundles"
DATASET_DIR="${PROGRAM_ROOT}/datasets"
GRAPH_PATH="${PROGRAM_ROOT}/objective_graph.json"
VECTOR_PATH="${BUNDLE_DIR}/todo_vector_index.json"
GENERATION_PATH="${PROGRAM_ROOT}/objective_generation.json"
PLAN_EVALUATION_PATH="${PROGRAM_ROOT}/plan_evaluations.json"
ANALYSIS_ESCALATION_PATH="${PROGRAM_ROOT}/analysis_escalation.json"
RUNTIME_ROOT="${PROGRAM_ROOT}/runtime"
WORKTREE_ROOT="${PROGRAM_ROOT}/worktrees"
MERGE_QUEUE_DIR="${RUNTIME_ROOT}/merge_queue"
LOG_DIR="${RUNTIME_ROOT}/logs"

CODEX_STATE_DIR="${RUNTIME_ROOT}/codex"
GROK_STATE_DIR="${RUNTIME_ROOT}/grok"
CODEX_STATE_PREFIX="wallet_processors_codex"
GROK_STATE_PREFIX="wallet_processors_grok"
CODEX_LOG="${LOG_DIR}/codex-supervisor.log"
GROK_LOG="${LOG_DIR}/grok-supervisor.log"

TASK_HEADER_PREFIX="## WALPROC-"
TASK_ID_PREFIX="WALPROC-"
MERGE_TARGET_BRANCH="codex/wallet-processors-migration"

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

prepare_runtime() {
  require_file "${OBJECTIVE_PATH}"
  require_file "${PLAN_PATH}"
  require_file "${TODO_PATH}"
  require_file "${ACCELERATE_ROOT}/ipfs_accelerate_py/agent_supervisor/objective_daemon.py"
  mkdir -p \
    "${DISCOVERY_DIR}" \
    "${BUNDLE_DIR}" \
    "${DATASET_DIR}" \
    "${CODEX_STATE_DIR}" \
    "${GROK_STATE_DIR}" \
    "${WORKTREE_ROOT}/codex" \
    "${WORKTREE_ROOT}/grok" \
    "${MERGE_QUEUE_DIR}" \
    "${LOG_DIR}"
}

pid_file_for() {
  local state_dir="$1"
  local state_prefix="$2"
  printf '%s/%s_supervisor.pid\n' "${state_dir}" "${state_prefix}"
}

daemon_pid_file_for() {
  local state_dir="$1"
  local state_prefix="$2"
  printf '%s/%s_managed_daemon.pid\n' "${state_dir}" "${state_prefix}"
}

supervisor_status_file_for() {
  local state_dir="$1"
  local state_prefix="$2"
  printf '%s/%s_supervisor_status.json\n' "${state_dir}" "${state_prefix}"
}

read_live_pid() {
  local path="$1"
  local pid=""
  if [[ -f "${path}" ]]; then
    pid="$(tr -cd '0-9' < "${path}")"
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
  local pid_path
  local status_path
  local pid=""

  pid_path="$(pid_file_for "${state_dir}" "${state_prefix}")"
  if pid="$(read_live_pid "${pid_path}")"; then
    printf '%s\n' "${pid}"
    return 0
  fi

  status_path="$(supervisor_status_file_for "${state_dir}" "${state_prefix}")"
  if [[ -f "${status_path}" ]]; then
    pid="$(
      sed -n \
        's/^[[:space:]]*"supervisor_pid":[[:space:]]*\([0-9][0-9]*\),\{0,1\}[[:space:]]*$/\1/p' \
        "${status_path}" | head -n 1
    )"
  fi
  if [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null; then
    printf '%s\n' "${pid}"
    return 0
  fi
  return 1
}

any_supervisor_running() {
  read_live_supervisor_pid "${CODEX_STATE_DIR}" "${CODEX_STATE_PREFIX}" >/dev/null \
    || read_live_supervisor_pid "${GROK_STATE_DIR}" "${GROK_STATE_PREFIX}" >/dev/null
}

require_supervisors_stopped() {
  if any_supervisor_running; then
    echo "objective generation requires both implementation supervisors to be stopped" >&2
    echo "run '$0 stop', wait for both lanes to exit, then retry" >&2
    return 1
  fi
}

read_nonempty_json_field() {
  local path="$1"
  local field="$2"
  "${PYTHON_BIN}" -c \
    'import json, pathlib, sys
path = pathlib.Path(sys.argv[1])
field = sys.argv[2]
try:
    value = json.loads(path.read_text(encoding="utf-8")).get(field)
except (OSError, ValueError, TypeError):
    raise SystemExit(1)
if value in (None, "", [], {}):
    raise SystemExit(1)
print(json.dumps(value, sort_keys=True))' \
    "${path}" "${field}"
}

seed_objectives() {
  local force_existing_goals="${1:-true}"
  local -a forced_goal_args=()
  prepare_runtime
  require_supervisors_stopped
  if [[ "${force_existing_goals}" == "true" ]]; then
    while IFS= read -r goal_id; do
      forced_goal_args+=(--force-goal-id "${goal_id}")
    done < <(
      awk '$1 == "##" && $2 ~ /^WALPROC-G[0-9]+$/ {print $2}' \
        "${OBJECTIVE_PATH}"
    )
  fi
  (
    cd "${REPO_ROOT}"
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
      --scan-exclude-path state \
      --scan-exclude-path tmp_assets \
      --scan-exclude-path ipfs_accelerate_py \
      --scan-exclude-path ipfs_kit_py \
      --scan-exclude-path chainlink \
      --scan-exclude-path scraper \
      --scan-exclude-path docs/large_artifact_shards \
      --scan-exclude-path docs/phone_dialog_generation \
      --scan-exclude-path wallet_interface/ui/public \
      --scan-exclude-path wallet_interface/ui/artifacts \
      --scan-exclude-path ipfs_datasets_py/archive \
      --scan-exclude-path ipfs_datasets_py/workspace \
      --scan-exclude-path ipfs_datasets_py/benchmarks \
      --task-prefix "${TASK_ID_PREFIX}" \
      --goal-prefix WALPROC-G \
      --objective-summary-prefix "Implement wallet processor migration objective" \
      --discovery-output-path data/wallet_processor_migration/agent_supervisor/discovery \
      --max-findings 64 \
      --surplus-findings-per-goal 1 \
      --surplus-min-terms-per-todo 2 \
      --max-refinement-children 3 \
      --max-refinement-depth 4 \
      --no-reconcile-goal-completion \
      --objective-generation-max-depth 3 \
      --objective-generation-max-breadth 4 \
      --objective-generation-max-new-work 16 \
      --objective-generation-max-open-work 64 \
      --objective-generation-token-budget 8192 \
      --objective-generation-max-retries 2 \
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
    --implementation-protected-path docs/planning/WALLET_PROCESSORS_MIGRATION_PLAN.md \
    --implementation-protected-path docs/planning/WALLET_PROCESSORS_OBJECTIVES.md \
    --implementation-protected-path docs/planning/WALLET_PROCESSORS_TODO.md \
    --no-objective-task-janitor \
    --no-objective-goal-refinement \
    --no-objective-goal-migration \
    --log-level INFO
}

run_reconciliation_preflight() {
  local -a args=()
  prepare_runtime
  require_supervisors_stopped
  args=(
    --once
    --reconciliation-only
    --todo-path "${TODO_PATH}"
    --state-dir "${CODEX_STATE_DIR}"
    --state-prefix "${CODEX_STATE_PREFIX}"
    --task-prefix "${TASK_HEADER_PREFIX}"
    --implementation-protected-path docs/planning/WALLET_PROCESSORS_MIGRATION_PLAN.md
    --implementation-protected-path docs/planning/WALLET_PROCESSORS_OBJECTIVES.md
    --implementation-protected-path docs/planning/WALLET_PROCESSORS_TODO.md
    --no-worktree-reconciliation
    --no-objective-task-janitor
    --no-objective-goal-refinement
    --no-objective-goal-migration
    --log-level INFO
  )
  (
    cd "${REPO_ROOT}"
    "${PYTHON_BIN}" \
      -m ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_supervisor \
      "${args[@]}"
  )
}

start_codex_lane() {
  local -a args
  if read_live_supervisor_pid "${CODEX_STATE_DIR}" "${CODEX_STATE_PREFIX}" >/dev/null; then
    echo "Codex supervisor is already running (pid $(read_live_supervisor_pid "${CODEX_STATE_DIR}" "${CODEX_STATE_PREFIX}"))."
    return 0
  fi
  require_executable "${CODEX_BIN}"
  mapfile -d '' -t args < <(
    common_supervisor_args \
      "${CODEX_STATE_DIR}" \
      "${CODEX_STATE_PREFIX}" \
      0 \
      "${WORKTREE_ROOT}/codex"
  )
  args+=(
    --implementation-command
    "${CODEX_BIN} exec --dangerously-bypass-approvals-and-sandbox --ephemeral -C . -"
    --auto-commit-generated-dirty
    --generated-dirty-path docs/planning/WALLET_PROCESSORS_OBJECTIVES.md
    --generated-dirty-path docs/planning/WALLET_PROCESSORS_TODO.md
    --generated-dirty-path data/wallet_processor_migration/agent_supervisor
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
  if read_live_supervisor_pid "${GROK_STATE_DIR}" "${GROK_STATE_PREFIX}" >/dev/null; then
    echo "Grok supervisor is already running (pid $(read_live_supervisor_pid "${GROK_STATE_DIR}" "${GROK_STATE_PREFIX}"))."
    return 0
  fi
  require_executable "${GROK_BIN}"
  mapfile -d '' -t args < <(
    common_supervisor_args \
      "${GROK_STATE_DIR}" \
      "${GROK_STATE_PREFIX}" \
      1 \
      "${WORKTREE_ROOT}/grok"
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
  local daemon_pid_path
  local attempt
  daemon_pid_path="$(daemon_pid_file_for "${state_dir}" "${state_prefix}")"
  for attempt in {1..60}; do
    if read_live_supervisor_pid "${state_dir}" "${state_prefix}" >/dev/null \
      && read_live_pid "${daemon_pid_path}" >/dev/null; then
      echo "${label} supervisor started with pid $(read_live_supervisor_pid "${state_dir}" "${state_prefix}") and managed daemon pid $(read_live_pid "${daemon_pid_path}")."
      return 0
    fi
    sleep 1
  done
  echo "${label} supervisor and managed daemon did not both become live within 60 seconds." >&2
  return 1
}

start_supervisors() {
  prepare_runtime
  if [[ ! -f "${GRAPH_PATH}" || ! -f "${BUNDLE_DIR}/index.json" ]]; then
    seed_objectives true
  fi
  if ! any_supervisor_running; then
    run_reconciliation_preflight
  fi
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
  local daemon_pid_path
  local incident_path="${state_dir}/implementation-protected-path-incident.json"
  local status_path
  local maintenance_error=""
  local supervisor_pid=""
  local daemon_pid=""
  status_path="$(supervisor_status_file_for "${state_dir}" "${state_prefix}")"
  daemon_pid_path="$(daemon_pid_file_for "${state_dir}" "${state_prefix}")"
  if supervisor_pid="$(read_live_supervisor_pid "${state_dir}" "${state_prefix}")"; then
    echo "${label} supervisor: running (pid ${supervisor_pid})"
    ps -p "${supervisor_pid}" -o pid=,etime=,stat=,args=
  else
    echo "${label} supervisor: stopped"
    return 1
  fi
  if daemon_pid="$(read_live_pid "${daemon_pid_path}")"; then
    echo "${label} daemon: running (pid ${daemon_pid})"
    ps -p "${daemon_pid}" -o pid=,etime=,stat=,args=
  else
    echo "${label} daemon: starting or stopped"
    failed=1
  fi
  if [[ -f "${incident_path}" ]]; then
    echo "${label} protected-path incident: ${incident_path}"
    echo "${label} health is blocked pending proof-checked operator clearance."
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
  local codex_protected_path_incident=false
  local grok_protected_path_incident=false
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
  if [[ -f "${CODEX_STATE_DIR}/implementation-protected-path-incident.json" ]]; then
    codex_protected_path_incident=true
  fi
  if [[ -f "${GROK_STATE_DIR}/implementation-protected-path-incident.json" ]]; then
    grok_protected_path_incident=true
  fi

  printf \
    '{"schema":"wallet-processor-migration-supervisor-health/v1","updated_at":"%s","healthy":%s,"merge_target_branch":"%s","task_board":"%s","objective_graph":"%s","codex":{"provider":"chatgpt-codex","supervisor_pid":%s,"daemon_pid":%s,"protected_path_incident":%s},"grok":{"provider":"grok-build","supervisor_pid":%s,"daemon_pid":%s,"protected_path_incident":%s}}\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    "${healthy}" \
    "${MERGE_TARGET_BRANCH}" \
    "${TODO_PATH#${REPO_ROOT}/}" \
    "${GRAPH_PATH#${REPO_ROOT}/}" \
    "${codex_supervisor_pid}" \
    "${codex_daemon_pid}" \
    "${codex_protected_path_incident}" \
    "${grok_supervisor_pid}" \
    "${grok_daemon_pid}" \
    "${grok_protected_path_incident}" >"${tmp_path}"
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
    echo "${label} daemon ${pid} is live without its owning supervisor; refusing a race-prone direct stop." >&2
    return 1
  fi
  echo "${label} supervisor is already stopped."
}

wait_for_lane_stop() {
  local label="$1"
  local state_dir="$2"
  local state_prefix="$3"
  local active_snapshot="${state_dir}/implementation-protected-path-active.json"
  local incident="${state_dir}/implementation-protected-path-incident.json"
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
    echo "${label} shutdown did not quiesce its supervisor and daemon within 30 seconds." >&2
    return 1
  fi
  if [[ -f "${incident}" ]]; then
    echo "${label} shutdown preserved a protected-path incident requiring proof-checked clearance: ${incident}" >&2
    return 1
  fi
  if [[ -f "${active_snapshot}" ]]; then
    echo "${label} shutdown left an active protected-path snapshot: ${active_snapshot}" >&2
    return 1
  fi
  if [[ -f "${state_path}" ]] && "${PYTHON_BIN}" -c \
    'import json, pathlib, sys
payload = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
raise SystemExit(0 if payload.get("implementation_in_progress") is True else 1)' \
    "${state_path}"; then
    echo "${label} shutdown left implementation_in_progress=true in ${state_path}." >&2
    return 1
  fi
  echo "${label} supervisor and daemon stopped with no active implementation fence."
}

stop_supervisors() {
  local failed=0
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
    seed_objectives true
    ;;
  refill)
    seed_objectives false
    ;;
  doctor)
    run_reconciliation_preflight
    ;;
  start)
    start_supervisors
    ;;
  status)
    show_status
    ;;
  stop)
    stop_supervisors
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac
