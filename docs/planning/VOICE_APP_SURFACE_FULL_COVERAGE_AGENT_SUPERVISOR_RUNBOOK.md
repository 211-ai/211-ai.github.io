# Voice × App-Surface Full Coverage — Agent Supervisor Runbook (v2)

Program: `voice-app-surface-full-coverage-v2`  
Board namespace: `voice-app-surface-full-coverage-v2`  
Merge target: `agent/voice-app-surface-full-coverage-v2`  
Goal root: `VAS2-G000`  
Prerequisite: `voice-app-surface-coverage-v1` (completed)

This runbook is the operator control surface for **full** 211-AI app-surface
voice coverage: re-inventory, exposure freeze, raised paraphrase floors,
DAG fold, and production IndexTTS + Whisper for the entire speech corpus.

## Companion artifacts

| Artifact | Path |
| --- | --- |
| Integration plan | `docs/planning/VOICE_APP_SURFACE_FULL_COVERAGE_PLAN.md` |
| Goal heap | `docs/planning/voice_app_surface_full_coverage.objectives.md` |
| Task board | `docs/planning/voice_app_surface_full_coverage.todo.md` |
| Launch profile | `docs/planning/voice_app_surface_full_coverage.supervisor.json` |
| Preflight | `scripts/validate_voice_app_surface_full_coverage_plan.py` |
| v1 baseline (read-only) | `docs/voice_app_surface_coverage/`, `data/voice_app_surface_coverage/` |

## Floors (v2)

| Tier | Unique user paraphrases | E2E paraphrases / surface |
| --- | ---: | ---: |
| P0 client core | **500** | 8 |
| P1 | **150** | 5 |
| P2 secondary (if exposed) | **80** | 3 |

## 0. Preflight (always)

```bash
cd /path/to/211-AI/211-AI
python scripts/validate_voice_app_surface_full_coverage_plan.py
# or:
python scripts/voice_app_surface_full_coverage/supervisor_control.py preflight
```

**Automatic merge-base housekeeping** (default on): when `origin/main`
advances as a pure fast-forward of the previous pin, preflight:

1. Re-pins `merge_target_creation.expected_base_commit` in the launch profile
2. Rewrites the companion `PINNED_BASE_COMMIT` constant in this validator
3. Fast-forwards lagging `agent/voice-app-surface-full-coverage-v2` when the
   branch tip is an ancestor of the new pin (no unique unmerged commits)
4. Writes `data/voice_app_surface_full_coverage/baseline/merge-base-receipt.json`

Implementation:
`ipfs_accelerate_py.agent_supervisor.control.launch_profile_housekeeping`.

```bash
# Opt out (fail closed on pin drift instead of auto-fixing)
python scripts/validate_voice_app_surface_full_coverage_plan.py --no-housekeep

# Explicit housekeep only
python scripts/voice_app_surface_full_coverage/supervisor_control.py housekeep-merge-base
python -m ipfs_accelerate_py.agent_supervisor.control.launch_profile_housekeeping \
  --repo-root . \
  --profile docs/planning/voice_app_surface_full_coverage.supervisor.json \
  --companion-pin scripts/validate_voice_app_surface_full_coverage_plan.py \
  --receipt data/voice_app_surface_full_coverage/baseline/merge-base-receipt.json
```

Fail closed on cycles, missing fields, history rewrite / non-FF base drift,
or diverged merge targets.

## 1. Pull submodules from origin/main (VAS2-002) — before parallel work

```bash
git -C ipfs_accelerate_py fetch origin
git -C ipfs_accelerate_py checkout main
git -C ipfs_accelerate_py pull --ff-only origin main

git -C ipfs_datasets_py fetch origin
git -C ipfs_datasets_py checkout main
git -C ipfs_datasets_py pull --ff-only origin main

# Probe voice modules still present on main
python - <<'PY'
from pathlib import Path
acc = Path('ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/catalog_211ai.py')
ds = Path('ipfs_datasets_py/ipfs_datasets_py/voice/action_links.py')
assert acc.is_file(), acc
assert ds.is_file(), ds
print('voice modules OK', acc, ds)
PY

# After human review: update monorepo gitlinks + pin receipt
python scripts/voice_app_surface_full_coverage/record_submodule_pins.py --write  # created by VAS2-002
```

Re-pin of the launch profile base when monorepo `origin/main` moves is now
**automatic** on preflight (VAS2-003 housekeep). Manual re-pin is only needed
when housekeeping fails closed (non-FF / diverged merge target).

**Do not** discard unexpected dirty content in submodules.

## 2. Dual-plane + exposure reminder

```text
large paraphrase lattice
  -> STT / transcript
  -> Abby GraphRAG + slotted DAG                 [content]
  -> grounded speech (+ library audio)           [content]
  -> ActionProposal (catalog id only)            [content emit]
  -> policy / confirm / auth                     [authority]
  -> surface allowlist + adapter                 [authority]
  -> ActionReceipt                               [authority]
  -> confirm/outcome audio from Abby library     [content]
```

| Class | Client voice/phone |
| --- | --- |
| `voice_navigable` | open after confirm |
| `voice_actionable` | tool after confirm (+auth if write) |
| `voice_read_only` | speak only |
| `phone_handoff` | handoff path |
| `staff_only` | **deny** on client channel |
| `never_voice` | **deny** |

## 3. Worker constraints (default deny)

From launch profile `default_worker_constraints`:

- network deny
- credentials deny
- publication deny
- live telephony / SMS deny
- HF publish deny
- live TTS Space deny
- require fake adapters

**Human-gated exceptions**

| Task | Allowed |
| --- | --- |
| `VAS2-002` | git fetch of submodules |
| `VAS2-027` | live TTS Space + network for IndexTTS batch |
| `VAS2-028` | network for Whisper model fetch if needed |

Product flags (independent; not flipped by workers):

- `WALLET_VOICE_UNIFIED_ROUTER_ENABLED`
- `WALLET_VOICE_ACTION_EXECUTE_ENABLED`

## 4. Merge target + shards

```bash
# Create merge target once (FF-only from pinned base)
git fetch origin
git checkout -B agent/voice-app-surface-full-coverage-v2 origin/main

# External state root (required)
export VOICE_APP_SURFACE_FULL_COVERAGE_SUPERVISOR_STATE_ROOT=/path/to/external/vas2-state
mkdir -p "$VOICE_APP_SURFACE_FULL_COVERAGE_SUPERVISOR_STATE_ROOT"/{worktrees,lanes,logs,projection,merge-queue}
```

Launch four shards (`task_shard_count: 4`) with the same pattern as
`voice-action-dag-abby-v1` / v1 surface coverage:

- `task_prefix`: `## VAS2-`
- `merge_target_branch`: `agent/voice-app-surface-full-coverage-v2`
- `worktree_submodule_paths`: accelerate, datasets, kit
- protected plan paths as in `voice_app_surface_full_coverage.supervisor.json`

Shard assignment: task numeric id modulo 4 (VAS2-001 → shard 1, etc.—confirm
against supervisor parser: typically the trailing digits).

## 5. Wave execution order

| Wave | Tasks | Parallelism |
| --- | --- | --- |
| 00 | VAS2-001…004 | control then submodules (human), then repin + import |
| 01 | VAS2-005…009 | inventory UI ∥ tools; then exposure → gaps |
| 02 | VAS2-010…013 | catalog ∥ binding after exposure; adapters after catalog |
| 03 | VAS2-014…017 | schema first; P0 ∥ P1 ∥ P2 lattices |
| 04 | VAS2-018…022 | project → fold (serial) → links; eval → repair |
| 05 | VAS2-023…029 | speech ∥; stage offline; **human-gated** regen + whisper; promote |
| 06 | VAS2-030…035 | e2e matrix ∥ adversarial; ops; signoff last |

**Pause thrashing supervisors** before VAS2-019 (DAG fold) and VAS2-027…029
(audio) so dirty trees are not reset mid-write.

## 6. Audio pipeline (Phase F)

```bash
# Offline stage (workers)
# VAS2-026

# Human-gated production IndexTTS (VAS2-027)
export HF_TOKEN="$(cat ~/.cache/huggingface/token)"  # never argv
export HUGGINGFACE_HUB_TOKEN="$HF_TOKEN"
python scripts/precompute_indextts_responses.py \
  --response-manifest data/voice_app_surface_full_coverage/audio/production/response-manifest.json \
  --reference-audio tmp_assets/abby-reference.wav \
  --space-url https://publicus-indextts-2-demo.hf.space \
  --remote-batch-size 4 \
  --allow-single-fallback \
  --no-mp3 \
  --output-dir data/voice_app_surface_full_coverage/audio/production/indextts \
  --manifest data/voice_app_surface_full_coverage/audio/production/indextts-manifest.json

# Whisper (VAS2-028) then promote (VAS2-029)
```

Coverage claims require production IndexTTS (or explicit residual budget)—not
smoke fixtures alone.

## 7. Validation commands (common)

```bash
python scripts/validate_voice_app_surface_full_coverage_plan.py
python scripts/voice_app_surface_full_coverage/audit_app_surface.py --check
python scripts/voice_app_surface_full_coverage/audit_voice_exposure.py --check
python scripts/voice_app_surface_full_coverage/build_surface_variant_lattice.py --check
python scripts/voice_app_surface_full_coverage/eval_variant_retrieval.py --check
python scripts/voice_app_surface_full_coverage/audit_audio_coverage.py --check
python -m pytest -q tests/e2e/voice_app_surface_full_coverage
```

(Scripts materialize as tasks complete; preflight only requires plan package.)

## 8. Relationship to v1

| v1 | v2 |
| --- | --- |
| Floors 200/50 | Floors **500/150/80** |
| 76 production clips | Full speech corpus + DAG high-traffic budget |
| Board completed | New board `VAS2-*`, all `todo` at land |
| data under `voice_app_surface_coverage/` | New tree `voice_app_surface_full_coverage/` + read v1 |

Do not reopen v1 tasks; import digests via VAS2-004.

## 9. Signoff

VAS2-035 publishes `program-release-evidence.json` and
`docs/voice_app_surface_full_coverage/PROGRAM_SIGNOFF.md` binding pins,
exposure, DAG, retrieval, audio+Whisper, and e2e.
