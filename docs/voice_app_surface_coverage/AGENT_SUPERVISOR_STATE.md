# Voice × App-Surface Coverage — Supervisor State Layout

Program: `voice-app-surface-coverage-v1`  
Board namespace: `voice-app-surface-coverage-v1`  
Task: `VAS-001`

## External state root

Required. Set before starting shards:

```bash
export VOICE_APP_SURFACE_COVERAGE_SUPERVISOR_STATE_ROOT=/var/lib/vas-supervisor
# or a workspace path, e.g.
# export VOICE_APP_SURFACE_COVERAGE_SUPERVISOR_STATE_ROOT="$PWD/data/voice_app_surface_coverage/agent_supervisor"
```

Layout under the state root (created by control wrapper):

```text
$VOICE_APP_SURFACE_COVERAGE_SUPERVISOR_STATE_ROOT/
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

Branch: `agent/voice-app-surface-coverage`  
Base: `origin/main` at the pinned commit in
`docs/planning/voice_app_surface_coverage.supervisor.json`
(`merge_target_creation.expected_base_commit`).

Rules:

- Create only from the pinned base.
- Fast-forward merges only.
- Require clean recursive tree before worker start (operator may allow dirty
  plan-only untracked files during bootstrap).

## Submodule pins (VAS-002)

Receipt: `data/voice_app_surface_coverage/baseline/submodule-pins.json`

Safety branches (local):

- `ipfs_accelerate_py`: `safety/pre-vas-002-accelerate`
- `ipfs_datasets_py`: `safety/pre-vas-002-datasets`

When `origin/main` diverges or lacks required voice modules, **retain working
pins** and document `origin_main_sha` for a later integration task.

## Lanes

| lane_id | provider | shard | refill |
| --- | --- | --- | --- |
| vas-grok-0 | grok-build | 0 | yes |
| vas-codex-1 | codex | 1 | no |
| vas-grok-2 | grok-build | 2 | no |
| vas-codex-3 | codex | 3 | no |

Refill remains disabled until bootstrap receipts exist (including
`submodule-pins`).

## Control commands

```bash
python scripts/validate_voice_app_surface_coverage_plan.py
python scripts/voice_app_surface_coverage/record_submodule_pins.py --write --check
python scripts/voice_app_surface_coverage/supervisor_control.py validate-config
python scripts/voice_app_surface_coverage/supervisor_control.py print-lane-plan
```
