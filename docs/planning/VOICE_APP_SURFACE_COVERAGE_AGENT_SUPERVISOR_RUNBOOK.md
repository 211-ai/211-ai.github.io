# Voice × App-Surface Coverage — Agent Supervisor Runbook

Program: `voice-app-surface-coverage-v1`  
Board namespace: `voice-app-surface-coverage-v1`  
Merge target: `agent/voice-app-surface-coverage`  
Goal root: `VAS-G000`

This runbook is the operator control surface for examining the full 211-AI app
surface, exposing voice/phone-amenable parts, expanding the Abby DAG under many
request variants, and regenerating audio coverage.

## Companion artifacts

| Artifact | Path |
| --- | --- |
| Integration plan | `docs/planning/VOICE_APP_SURFACE_COVERAGE_PLAN.md` |
| Goal heap | `docs/planning/voice_app_surface_coverage.objectives.md` |
| Task board | `docs/planning/voice_app_surface_coverage.todo.md` |
| Launch profile | `docs/planning/voice_app_surface_coverage.supervisor.json` |
| Preflight | `scripts/validate_voice_app_surface_coverage_plan.py` |
| Prior action plane | `docs/planning/VOICE_ACTION_DAG_ABBY_INTEGRATION_PLAN.md` |

## 0. Preflight (always)

```bash
cd /path/to/211-AI/211-AI   # monorepo root
python scripts/validate_voice_app_surface_coverage_plan.py
```

Fail closed on cycles, missing fields, profile drift, or pin mismatch.

## 1. Pull submodules from origin/main (VAS-002)

Do this **before** parallel implementation lanes touch accelerate/datasets:

```bash
git -C ipfs_accelerate_py fetch origin
git -C ipfs_accelerate_py checkout main
git -C ipfs_accelerate_py pull --ff-only origin main

git -C ipfs_datasets_py fetch origin
git -C ipfs_datasets_py checkout main
git -C ipfs_datasets_py pull --ff-only origin main

# After review, update monorepo gitlinks + pin receipt
python scripts/voice_app_surface_coverage/record_submodule_pins.py --write
```

Then re-pin the launch profile base if monorepo `origin/main` moved (VAS-003).

**Do not** discard unexpected dirty content in submodules.

## 2. Dual-plane + exposure reminder

```text
many phrasings
  -> STT / transcript
  -> Abby GraphRAG + slotted DAG                 [content]
  -> grounded speech (+ library audio)           [content]
  -> ActionProposal (catalog id only)            [content emit]
  -> policy / confirm / auth                     [authority]
  -> surface allowlist + adapter                 [authority]
  -> ActionReceipt                               [authority]
  -> confirm/outcome audio from Abby library     [content]
```

Exposure classes (matrix is authority for opens):

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
| `VAS-002` | git fetch of submodules |
| `VAS-023` | live TTS Space + network for IndexTTS batch |

Product flags (independent; not flipped by workers):

- `WALLET_VOICE_UNIFIED_ROUTER_ENABLED`
- `WALLET_VOICE_ACTION_EXECUTE_ENABLED`

## 4. Four-shard layout

| Lane | Provider | Shard | Special |
| --- | --- | --- | --- |
| `vas-grok-0` | grok-build | 0 | refill + gc owner |
| `vas-codex-1` | codex | 1 | implement |
| `vas-grok-2` | grok-build | 2 | implement |
| `vas-codex-3` | codex | 3 | implement |

External state root env:

```bash
export VOICE_APP_SURFACE_COVERAGE_SUPERVISOR_STATE_ROOT=/var/lib/vas-supervisor
```

Tasks shard by stable id modulo 4 (same pattern as voice-action program).

## 5. Parallel waves (operator view)

1. **wave-00** — control, submodule pull, re-pin  
2. **wave-01** — inventory + exposure matrix (parallel UI/tools)  
3. **wave-02** — catalog, policy, bindings, adapters  
4. **wave-03** — variant lattices + DAG density (sharded by surface family) + retrieval  
5. **wave-04** — speech frames → stage → human TTS → Whisper coverage  
6. **wave-05** — e2e matrix, adversarial, ops signoff  

Conflict policy: each task lists exclusive predicted files; DAG rebuilds serialize
on action-link projection (`VAS-018`).

## 6. Variant floors (defaults)

| Priority | Unique user texts / surface |
| --- | --- |
| P0 | ≥ 200 |
| P1 | ≥ 50 |
| E2E paraphrases / P0 surface | ≥ 5 |

P0 client surfaces (profile): home, check-in, calendar, messages, contacts,
social-services, interactions, uploads, settings.

## 7. Audio regeneration policy

1. Text frames first (`VAS-021`) — offline, banlist clean.  
2. Stage fixtures (`VAS-022`) — no publish.  
3. Human enables Space for `VAS-023` only.  
4. Whisper gate + coverage receipt (`VAS-024`).  
5. E2E may use staged fixtures offline; production promote is separate.

## 8. Success gate (program)

- Submodule pins present  
- 100% surfaces classified  
- P0 surfaces: catalog + density + speech + e2e green  
- never_voice/staff_only denied on client channel  
- Audio coverage receipt for P0  
- Preflight green  

## 9. Relationship to voice-action-dag-abby

Do not fork `action_runtime` contracts needlessly. Prefer additive catalog
descriptors and density expansion. Reuse offline e2e fake stack patterns from
`tests/e2e/voice_action_dag/`.


## 10. Enablement checklist

See `docs/voice_app_surface_coverage/ENABLEMENT_CHECKLIST.md` (updated 2026-08-05T18:31:00.321152+00:00).
