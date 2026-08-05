# Voice × App-Surface Full Coverage Plan (v2)

**Program id:** `voice-app-surface-full-coverage-v2`  
**Board namespace:** `voice-app-surface-full-coverage-v2`  
**Merge target:** `agent/voice-app-surface-full-coverage-v2`  
**Frozen base (plan land):** `37a362fb832e2ec38a87d4e37fb26a86348778c0`  
**Prerequisite program:** `voice-app-surface-coverage-v1` (VAS-001…VAS-030 completed)

## Outcome

Examine the **entire 211-AI app surface**, freeze which parts are safe for the
**voice / phone system**, expand the **Abby slotted response DAG** so those
surfaces are reachable under a **large vocabulary of request variants**, and
**regenerate IndexTTS + Whisper-gated audio** so the content plane covers the
full surface × DAG matrix—not only the pilot P0 smoke set.

```text
large paraphrase lattice (STT noise, dialect, multi-turn)
  → reliable DAG route / surface selection
  → catalog-bound ActionProposal
  → confirm / auth / handoff (authority plane)
  → app surface or tool adapter
  → Abby library audio for confirm + outcome + high-traffic DAG frames
```

## Why v2 (after v1)

v1 delivered inventory, exposure classes, P0 floors (≥200 paraphrases),
sidecar→DAG fold (2288 edges), pilot speech frames, and **76 production
IndexTTS clips**. Remaining product gaps for full surface reliability:

| Gap | v1 state | v2 target |
| --- | --- | --- |
| Variant density | P0 ≥200, P1 ≥50 | P0 ≥**500**, P1 ≥**150**, P2 secondary ≥**80** |
| Surface depth | client-core focused | **all** voice_navigable / voice_actionable + reviewed P2 secondary |
| DAG absorption | fold applied once | continuous fold + route rebalance; tool-adjacent routes ≥ floor |
| Audio | 76 pilot frames | **full speech corpus** for exposed actions/surfaces + budgeted high-traffic DAG exemplars + Whisper gate |
| Catalog | pilot descriptors | surface-complete catalog slice + deny tests for never_voice/staff_only |
| E2E | matrix green for P0 | matrix green for P0+P1; adversarial on full never_voice set |
| Submodules | pinned at voice merge | **re-sync to origin/main** before parallel waves |

## Companion artifacts

| Artifact | Path |
| --- | --- |
| Goal heap | `docs/planning/voice_app_surface_full_coverage.objectives.md` |
| Task board | `docs/planning/voice_app_surface_full_coverage.todo.md` |
| Launch profile | `docs/planning/voice_app_surface_full_coverage.supervisor.json` |
| Preflight | `scripts/validate_voice_app_surface_full_coverage_plan.py` |
| Runbook | `docs/planning/VOICE_APP_SURFACE_FULL_COVERAGE_AGENT_SUPERVISOR_RUNBOOK.md` |
| v1 baseline (read) | `docs/voice_app_surface_coverage/`, `data/voice_app_surface_coverage/` |

Preflight:

```bash
python scripts/validate_voice_app_surface_full_coverage_plan.py
```

## Prerequisites (wave 0) — required before parallel work

1. **Pull submodules from origin/main** (human-gated VAS2-002):
   - `ipfs_accelerate_py` → `origin/main`
   - `ipfs_datasets_py` → `origin/main`
2. Verify required voice modules still import (`action_runtime`, `voice/action_links`, `voice/action_retrieval`).
3. Record pins: `data/voice_app_surface_full_coverage/baseline/submodule-pins.json`.
4. Create merge target `agent/voice-app-surface-full-coverage-v2` from monorepo `origin/main` (re-pin `expected_base_commit` after pointer commits).
5. Import v1 digests as baseline (do not delete v1 artifacts).

Autonomous workers must **not** force-push, publish HF audio, or flip product
execute flags. Live IndexTTS is **human-gated** (VAS2-030 / VAS2-031).

## Architectural rules (non-negotiable)

1. **Dual plane** — DAG/audio never embeds executables, URLs, argv, secrets, or import paths.
2. **Catalog only** — retrieval proposes reviewed logical actions only.
3. **Fail closed** — reads confirm; writes confirm+auth; handoff never claims success without provider receipt.
4. **Surface allowlist** — open only `voice_navigable` / `voice_actionable` for active role/channel.
5. **Fake transports in workers** — no live telephony/SMS/HF publish from autonomous lanes.
6. **Audio content-addressed** — stage → IndexTTS → Whisper → promote; no coverage claims from smoke fixtures alone.

## Exposure classes (authoritative)

| Class | Client voice/phone |
| --- | --- |
| `voice_navigable` | open after confirm |
| `voice_actionable` | tool after confirm (+auth if write) |
| `voice_read_only` | speak grounded info only |
| `phone_handoff` | handoff / safety path |
| `staff_only` | **deny** on client channel |
| `never_voice` | **deny** |

Unknown → `never_voice` until reviewed.

## Program phases

### Phase A — Submodule sync + control plane
Pull origin/main, pins, merge target, protected paths, import v1 baseline.

### Phase B — Full app-surface re-examination
Refresh inventory (RouteIds, tools, deep links, bindings) against current UI;
diff vs v1; reclassify exposure; publish gap matrix (DAG density, catalog, audio, e2e).

### Phase C — Authority expansion
Catalog + policy + bindings + offline adapters for every exposed surface;
deny paths for staff_only/never_voice; unit tests.

### Phase D — Variant lattices at scale
Per-surface lattices with raised floors; axes: paraphrase, dialect, slots,
multi-turn, STT noise, negatives; symbolic schema before any LLM fill.

### Phase E — DAG expansion + fold
Project exemplars → edges; fold into `slotted_response_dag.json` (or shards);
rebuild action links; retrieval reliability ≥ thresholds on full lattice.

### Phase F — Speech frames + full audio regen
Author/expand speech frames for all exposed actions/surfaces; IndexTTS batch
for full generate_required set; Whisper adjudication; resolver offline smoke.

### Phase G — E2E proof + signoff
Offline matrix, adversarial, DAG sims, enablement checklist, release evidence.

## Parallel lane map

| Wave | Lanes | Owns |
| --- | --- | --- |
| 00 | control, submodules, repin, baseline-import | pins, merge target, preflight |
| 01 | inventory-ui, inventory-tools, exposure, gaps | census + amenability |
| 02 | catalog, policy, binding, adapters | authority plane |
| 03 | variant-schema, variants-p0, variants-p1, variants-p2 | paraphrase density |
| 04 | dag-project, dag-fold, action-links, retrieval, retrieval-repair | content density |
| 05 | speech, audio-stage, audio-regen, whisper, audio-promote | audio plane |
| 06 | e2e-matrix, e2e-adv, e2e-dag, ops, projection, signoff | proof |

Four supervisor shards (`task_shard_count: 4`) assign tasks by id modulo shard.

## Success criteria

1. Submodules on reviewed `origin/main` with pin receipt + voice module probe green.
2. 100% of RouteIds classified with evidence; human overrides receipted.
3. Every `voice_navigable` / `voice_actionable` client surface (P0+P1) has catalog binding, variant floor, speech frames, offline e2e green.
4. P0 paraphrase floor ≥500 unique user texts; P1 ≥150; P2 secondary ≥80 where exposed.
5. Retrieval top-1 / top-3 meet program thresholds on the full lattice.
6. Audio: production IndexTTS + Whisper for full speech corpus; high-traffic DAG exemplar budget receipt; no smoke-only coverage claims.
7. never_voice / staff_only denied on client channel in adversarial tests.
8. Preflight green; FF-only merges onto `agent/voice-app-surface-full-coverage-v2`.

## Floors (normative defaults)

| Class | Unique user paraphrases | E2E paraphrases / surface |
| --- | --- | --- |
| P0 client core | 500 | 8 |
| P1 client core residual | 150 | 5 |
| P2 secondary client (if exposed) | 80 | 3 |

P0 surfaces (default): home, check-in, calendar, messages, contacts,
social-services, interactions, uploads, settings.

## Out of scope

- Replacing GraphRAG / IndexTTS stack
- Live production telephony cutover
- Provider portal UX redesign
- Unbounded LLM generation without symbolic floors
- Weakening dual-gate execute flags

## Operator bootstrap

```bash
cd /path/to/211-AI/211-AI
python scripts/validate_voice_app_surface_full_coverage_plan.py

# Wave 0 — human / VAS2-002
git -C ipfs_accelerate_py fetch origin && git -C ipfs_accelerate_py checkout main
git -C ipfs_accelerate_py pull --ff-only origin main
git -C ipfs_datasets_py fetch origin && git -C ipfs_datasets_py checkout main
git -C ipfs_datasets_py pull --ff-only origin main
# then pin receipt + monorepo gitlink PR (human review)

# Start 4-shard supervisor (external state root) — see runbook
```

## Relationship

| Program | Relationship |
| --- | --- |
| `voice-action-dag-abby-v1` | Action plane contracts; reuse |
| `voice-app-surface-coverage-v1` | Prerequisite baseline; v2 raises floors and completes audio/DAG depth |
| Abby TTS pipelines | Reused for Phase F |
