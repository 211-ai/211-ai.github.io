# Voice Action DAG × Abby — agent supervisor state

External state root for program `voice-action-dag-abby-v1`.

## Environment

```bash
export VOICE_ACTION_DAG_SUPERVISOR_STATE_ROOT=/absolute/path/to/state
```

The control wrapper refuses worker start when this variable is unset or not an
absolute directory path. Secrets must never appear in process argv.

## Expected layout (created by control scripts, not committed)

```text
$VOICE_ACTION_DAG_SUPERVISOR_STATE_ROOT/
  worktrees/
    voice-action-grok-0/
    voice-action-codex-1/
    voice-action-grok-2/
    voice-action-codex-3/
  lanes/
    voice-action-grok-0/
    voice-action-codex-1/
    voice-action-grok-2/
    voice-action-codex-3/
  logs/
  projection/
    lane-plan.json
    bootstrap-receipts.json
    control-status.json
  merge-queue/
  runtime/
    <lane_id>_supervisor.pid   # only when workers are launched
```

## Plan artifacts (protected, in repo)

Workers and implementation agents must not create, modify, rename, delete,
replace, or regenerate these paths:

- `docs/planning/VOICE_ACTION_DAG_ABBY_INTEGRATION_PLAN.md`
- `docs/planning/voice_action_dag_abby.objectives.md`
- `docs/planning/voice_action_dag_abby.todo.md`
- `docs/planning/voice_action_dag_abby.supervisor.json`
- `scripts/validate_voice_action_dag_abby_plan.py`

## Control surface

Launch profile:

`docs/planning/voice_action_dag_abby.supervisor.json`

Runtime policy:

`docs/voice_action_dag/runtime-policy.json`

Control wrapper:

```bash
# Fail-closed preflight of objectives, board, profile, and runtime policy
python scripts/validate_voice_action_dag_abby_plan.py
python scripts/voice_action_dag/supervisor_control.py validate-config

# Create merge target only from the pinned reviewed base when absent
python scripts/voice_action_dag/supervisor_control.py ensure-merge-target

# Admit four deterministic shards (sole refill owner: voice-action-grok-0)
python scripts/voice_action_dag/supervisor_control.py start
python scripts/voice_action_dag/supervisor_control.py status
python scripts/voice_action_dag/supervisor_control.py stop
```

## Lane topology

| Lane | Provider | Shard | Refill owner | Git GC owner |
| --- | --- | --- | --- | --- |
| `voice-action-grok-0` | grok-build | 0 | yes | yes |
| `voice-action-codex-1` | codex | 1 | no | no |
| `voice-action-grok-2` | grok-build | 2 | no | no |
| `voice-action-codex-3` | codex | 3 | no | no |

Merge target branch: `agent/voice-action-dag-abby`  
Pinned base: `origin/main` @ `12a7ef36645bf597de329dbfabe0ce5b2e0c4df9`  
Fast-forward merges only. Recursive tree must be clean before creation/start.

## Bootstrap receipts (required before refill)

Refill remains disabled until after `VOICE-ACTION-001` and these receipts exist:

1. `protected-path-policy`
2. `semantic-deduplication`
3. `bounded-refill-budget`
4. `sole-refill-owner`

## Default worker constraints

From `runtime-policy.json` / launch profile (fail closed):

- network: deny
- credentials: deny
- publication: deny
- live telephony / SMS / HF publish: deny
- require fake adapters: true
- Abby dataset read: allowed
- smoke `tmp_assets` writes: allowed

Publication and credentials remain disabled by default. Live transports are
never enabled by autonomous workers.
