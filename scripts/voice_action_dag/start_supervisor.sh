#!/usr/bin/env bash
# Start 4-shard ipfs_accelerate_py implementation supervisors for the
# voice-action-dag-abby-v1 plan board.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

STATE_ROOT="${VOICE_ACTION_DAG_SUPERVISOR_STATE_ROOT:-$ROOT/data/voice_action_dag/agent_supervisor}"
TODO_PATH="$ROOT/docs/planning/voice_action_dag_abby.todo.md"
OBJ_PATH="$ROOT/docs/planning/voice_action_dag_abby.objectives.md"
MERGE_BRANCH="${VOICE_ACTION_MERGE_BRANCH:-agent/voice-action-dag-abby}"

export VOICE_ACTION_DAG_SUPERVISOR_STATE_ROOT="$STATE_ROOT"
export IPFS_ACCELERATE_AGENT_IMPLEMENTATION_PROVIDER="${IPFS_ACCELERATE_AGENT_IMPLEMENTATION_PROVIDER:-auto}"
export IPFS_ACCELERATE_AGENT_GROK_MODEL="${IPFS_ACCELERATE_AGENT_GROK_MODEL:-grok-4.5}"
export IPFS_ACCELERATE_AGENT_CODEX_MODEL="${IPFS_ACCELERATE_AGENT_CODEX_MODEL:-gpt-5.6-terra}"
export PYTHONPATH="$ROOT/ipfs_accelerate_py:$ROOT/ipfs_datasets_py:$ROOT${PYTHONPATH:+:$PYTHONPATH}"

# Reuse host Playwright browser bundles for private validation homes so UI
# tasks do not fail preflight only because the temp XDG cache is empty.
if [[ -z "${IPFS_ACCELERATE_AGENT_VALIDATION_PLAYWRIGHT_BROWSERS_PATH:-}" ]]; then
  _pw_default="${HOME}/.cache/ms-playwright"
  if [[ -d "${_pw_default}" ]]; then
    export IPFS_ACCELERATE_AGENT_VALIDATION_PLAYWRIGHT_BROWSERS_PATH="${_pw_default}"
  fi
  unset _pw_default
fi

mkdir -p \
  "$STATE_ROOT/logs" \
  "$STATE_ROOT/merge-queue" \
  "$STATE_ROOT/discovery" \
  "$STATE_ROOT/objective_bundles" \
  "$STATE_ROOT/objective_datasets" \
  "$STATE_ROOT/projection"

for i in 0 1 2 3; do
  mkdir -p "$STATE_ROOT/shards/$i/state" "$STATE_ROOT/shards/$i/worktrees"
done

if ! git show-ref --verify --quiet "refs/heads/${MERGE_BRANCH}"; then
  git branch "${MERGE_BRANCH}" HEAD
  echo "created merge target ${MERGE_BRANCH} at $(git rev-parse HEAD)"
fi

python3 scripts/validate_voice_action_dag_abby_plan.py | tee "$STATE_ROOT/logs/preflight.json"

for i in 0 1 2 3; do
  if pgrep -f "implementation_supervisor .*voice_action_${i}" >/dev/null 2>&1; then
    echo "shard $i already running"
    continue
  fi
  LOG="$STATE_ROOT/logs/supervisor-shard-$i.log"
  nohup python3 -m ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_supervisor \
    --todo-path "$TODO_PATH" \
    --state-dir "$STATE_ROOT/shards/$i/state" \
    --stale-seconds 1800 \
    --check-interval 30 \
    --watchdog-startup-grace-seconds 300 \
    --max-restarts 3 \
    --max-task-attempts 5 \
    --daemon-interval 60 \
    --task-prefix "VOICE-ACTION-" \
    --state-prefix "voice_action_${i}" \
    --implement \
    --implementation-timeout 7200 \
    --implementation-max-timeout 7200 \
    --implementation-log-stall-seconds 900 \
    --worktree-root "$STATE_ROOT/shards/$i/worktrees" \
    --merge-target-branch "$MERGE_BRANCH" \
    --merge-queue-dir "$STATE_ROOT/merge-queue" \
    --merge-reconciliation-max-merges 1 \
    --task-shard-count 4 \
    --task-shard-index "$i" \
    --strict-task-sharding \
    --worktree-submodule-path ipfs_accelerate_py \
    --worktree-submodule-path ipfs_datasets_py \
    --worktree-submodule-path ipfs_kit_py \
    --implementation-protected-path docs/planning/VOICE_ACTION_DAG_ABBY_INTEGRATION_PLAN.md \
    --implementation-protected-path docs/planning/voice_action_dag_abby.objectives.md \
    --implementation-protected-path docs/planning/voice_action_dag_abby.todo.md \
    --implementation-protected-path docs/planning/voice_action_dag_abby.supervisor.json \
    --implementation-protected-path scripts/validate_voice_action_dag_abby_plan.py \
    --objective-path "$OBJ_PATH" \
    --objective-graph-path "$STATE_ROOT/objective_graph.json" \
    --objective-bundle-dir "$STATE_ROOT/objective_bundles" \
    --objective-dataset-dir "$STATE_ROOT/objective_datasets" \
    --objective-discovery-dir "$STATE_ROOT/discovery" \
    --objective-discovery-output-path "$STATE_ROOT/discovery" \
    --no-objective-task-janitor \
    --no-objective-goal-migration \
    >"$LOG" 2>&1 &
  echo "started shard $i pid=$! log=$LOG"
done

echo "status: pgrep -af 'implementation_supervisor.*voice_action|implementation_daemon.*voice_action'"
pgrep -af 'implementation_supervisor.*voice_action|implementation_daemon.*voice_action' || true
