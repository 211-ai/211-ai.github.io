# Voice Action DAG × Abby — agent supervisor state

External state root for program `voice-action-dag-abby-v1`.

Set:

```bash
export VOICE_ACTION_DAG_SUPERVISOR_STATE_ROOT=/absolute/path/to/state
```

Expected layout (created by control scripts, not committed):

```text
$VOICE_ACTION_DAG_SUPERVISOR_STATE_ROOT/
  worktrees/
  lanes/
  logs/
  projection/
  merge-queue/
```

Plan artifacts (protected, in repo):

- `docs/planning/VOICE_ACTION_DAG_ABBY_INTEGRATION_PLAN.md`
- `docs/planning/voice_action_dag_abby.objectives.md`
- `docs/planning/voice_action_dag_abby.todo.md`
- `docs/planning/voice_action_dag_abby.supervisor.json`
- `scripts/validate_voice_action_dag_abby_plan.py`

Preflight:

```bash
python scripts/validate_voice_action_dag_abby_plan.py
```

Default worker constraints: no network credentials, no live telephony/SMS, fake
adapters only, Abby dataset read allowed, smoke tmp_assets writes allowed.
