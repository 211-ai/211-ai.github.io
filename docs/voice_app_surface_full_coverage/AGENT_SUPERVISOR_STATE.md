# Voice × App-Surface Full Coverage — Supervisor State Layout (v2)

Program: `voice-app-surface-full-coverage-v2`  
Board namespace: `voice-app-surface-full-coverage-v2`  
Task: `VAS2-001`

## External state root

Required. Set before starting shards:

```bash
export VOICE_APP_SURFACE_FULL_COVERAGE_SUPERVISOR_STATE_ROOT=/var/lib/vas2-supervisor
# or a workspace path, e.g.
# export VOICE_APP_SURFACE_FULL_COVERAGE_SUPERVISOR_STATE_ROOT="$PWD/data/voice_app_surface_full_coverage/agent_supervisor"
```

Layout under the state root (created by control wrapper):

```text
$VOICE_APP_SURFACE_FULL_COVERAGE_SUPERVISOR_STATE_ROOT/
  worktrees/           # per-task worktrees
  lanes/               # per-lane state
  logs/                # supervisor + daemon logs
  projection/          # control-status projections
  merge-queue/         # shared FF-only merge train
  discovery/           # optional shard discovery notes
```

Secrets must never appear in argv. Network, credentials, HF publish, live TTS,
and live telephony are **deny** by default (see `runtime-policy.json`).

## Merge target

Branch: `agent/voice-app-surface-full-coverage-v2`  
Base: `origin/main` at the pinned commit in
`docs/planning/voice_app_surface_full_coverage.supervisor.json`
(`merge_target_creation.expected_base_commit`).

Rules:

- Create only from the pinned base.
- Fast-forward merges only.
- Require clean recursive tree before worker start (operator may allow dirty
  plan-only untracked files during bootstrap).

## Submodule pins (VAS2-002)

Receipt: `data/voice_app_surface_full_coverage/baseline/submodule-pins.json`  
Voice module probe: `data/voice_app_surface_full_coverage/baseline/voice-module-probe.json`

Safety branches (local):

- `ipfs_accelerate_py`: `safety/pre-vas2-002-accelerate`
- `ipfs_datasets_py`: `safety/pre-vas2-002-datasets`

When `origin/main` lacks required voice modules, **retain working pins** and
document `origin_main_sha` for a later integration task.

## Lanes

| lane_id | provider | shard | refill |
| --- | --- | --- | --- |
| `vas2-grok-0` | grok-build | 0 | objective + codebase + git gc |
| `vas2-codex-1` | codex | 1 | no |
| `vas2-grok-2` | grok-build | 2 | no |
| `vas2-codex-3` | codex | 3 | no |

## Control commands

```bash
python scripts/voice_app_surface_full_coverage/supervisor_control.py validate
python scripts/voice_app_surface_full_coverage/supervisor_control.py lane-plan
python scripts/validate_voice_app_surface_full_coverage_plan.py
```

## Human-gated tasks

| Task | Gate |
| --- | --- |
| VAS2-002 | git fetch submodules |
| VAS2-027 | live IndexTTS Space + network |
| VAS2-028 | network (Whisper models if needed) |
