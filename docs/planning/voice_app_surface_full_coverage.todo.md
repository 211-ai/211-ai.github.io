# Voice × App-Surface Full Coverage Task Board (v2)

Executable projection of `voice_app_surface_full_coverage.objectives.md` for
`ipfs_accelerate_py.agent_supervisor`.

Program invariants:

- Board namespace is `voice-app-surface-full-coverage-v2`; task identities are stable.
- Pull `ipfs_accelerate_py` and `ipfs_datasets_py` from `origin/main` before
  implementation waves that edit those trees.
- Content never embeds executables, URLs, import paths, credentials, or argv.
- Retrieval proposes catalog logical actions only.
- Mutations fail closed without policy, confirmation, and (when required) auth.
- Autonomous workers use fake/local transports only; live TTS/HF publish is
  human-gated.
- Symbolic checks precede bounded LLM repair.
- Completion requires current-tree validation evidence.
- Prerequisite board `voice-app-surface-coverage-v1` is completed; reuse
  baseline digests via VAS2-004.

## VAS2-001 Bootstrap supervisor control and protected plan namespace

- Status: completed
- Completion: manual
- Priority: P0
- Track: operations
- Depends on: 
- Goal id: VAS2-G010
- Outputs: docs/voice_app_surface_full_coverage/AGENT_SUPERVISOR_STATE.md, docs/voice_app_surface_full_coverage/runtime-policy.json, scripts/voice_app_surface_full_coverage/supervisor_control.py
- Validation: python scripts/validate_voice_app_surface_full_coverage_plan.py
- Board namespace: voice-app-surface-full-coverage-v2
- Bundle: vas2/ops-bootstrap
- Parallel lane: wave-00-control
- Resource class: cpu-small
- Predicted files: docs/voice_app_surface_full_coverage/AGENT_SUPERVISOR_STATE.md, docs/voice_app_surface_full_coverage/runtime-policy.json, scripts/voice_app_surface_full_coverage/supervisor_control.py
- Conflict policy: Exclusive owner of supervisor launch policy and protected-path configuration for this board.
- Symbolic first: true
- LLM context budget bytes: 12288
- Acceptance: Preflight validates objectives and board; merge target rules explicit; four shards; plan files protected; publication/credentials disabled by default.

## VAS2-002 Pull ipfs_accelerate_py and ipfs_datasets_py from origin/main

- Status: completed
- Completion: manual
- Priority: P0
- Track: operations
- Depends on: VAS2-001
- Goal id: VAS2-G010
- Outputs: data/voice_app_surface_full_coverage/baseline/submodule-pins.json, scripts/voice_app_surface_full_coverage/record_submodule_pins.py, data/voice_app_surface_full_coverage/baseline/voice-module-probe.json
- Validation: python scripts/voice_app_surface_full_coverage/record_submodule_pins.py --check
- Board namespace: voice-app-surface-full-coverage-v2
- Bundle: vas2/ops-bootstrap
- Parallel lane: wave-00-submodules
- Resource class: io-medium
- Predicted files: data/voice_app_surface_full_coverage/baseline/submodule-pins.json, scripts/voice_app_surface_full_coverage/record_submodule_pins.py, data/voice_app_surface_full_coverage/baseline/voice-module-probe.json
- Conflict policy: Human-gated submodule pointer update only; never force-push submodule remotes; record SHAs before/after pull; verify voice modules on origin/main.
- Symbolic first: true
- LLM context budget bytes: 8192
- Acceptance: Both submodules FF to origin/main tips (or documented pin if unsafe); pin JSON includes URLs, SHAs, fetch time; voice module probe green; monorepo gitlinks only with review.

## VAS2-003 Re-pin merge base after submodule sync

- Status: completed
- Completion: manual
- Priority: P0
- Track: operations
- Depends on: VAS2-002
- Goal id: VAS2-G010
- Outputs: docs/planning/voice_app_surface_full_coverage.supervisor.json, data/voice_app_surface_full_coverage/baseline/merge-base-receipt.json
- Validation: python scripts/validate_voice_app_surface_full_coverage_plan.py
- Board namespace: voice-app-surface-full-coverage-v2
- Bundle: vas2/ops-bootstrap
- Parallel lane: wave-00-repin
- Resource class: cpu-small
- Predicted files: docs/planning/voice_app_surface_full_coverage.supervisor.json, data/voice_app_surface_full_coverage/baseline/merge-base-receipt.json
- Conflict policy: Sole owner of expected_base_commit for this board during bootstrap.
- Symbolic first: true
- LLM context budget bytes: 8192
- Acceptance: expected_base_commit matches monorepo origin/main after pin commit (or documents lag); merge target FF-only; receipt records old→new base.

## VAS2-004 Import v1 baseline digests and residual gap list

- Status: completed
- Completion: manual
- Priority: P0
- Track: operations
- Depends on: VAS2-001
- Goal id: VAS2-G010
- Outputs: data/voice_app_surface_full_coverage/baseline/v1-import-receipt.json, docs/voice_app_surface_full_coverage/V1_BASELINE.md
- Validation: test -f data/voice_app_surface_full_coverage/baseline/v1-import-receipt.json
- Board namespace: voice-app-surface-full-coverage-v2
- Bundle: vas2/ops-bootstrap
- Parallel lane: wave-00-baseline-import
- Resource class: cpu-small
- Predicted files: data/voice_app_surface_full_coverage/baseline/v1-import-receipt.json, docs/voice_app_surface_full_coverage/V1_BASELINE.md
- Conflict policy: Read-only import of v1 digests; must not delete v1 artifacts.
- Symbolic first: true
- LLM context budget bytes: 8192
- Acceptance: Receipt lists v1 inventory/exposure/DAG/audio digests reused as baseline; gaps vs v2 floors listed.

## VAS2-005 Inventory all RouteIds, screens, and navigation allowlists

- Status: completed
- Completion: manual
- Priority: P0
- Track: inventory
- Depends on: VAS2-002
- Goal id: VAS2-G020
- Outputs: scripts/voice_app_surface_full_coverage/audit_app_surface.py, data/voice_app_surface_full_coverage/baseline/app-surface-inventory.json, docs/voice_app_surface_full_coverage/APP_SURFACE_INVENTORY.md
- Validation: python scripts/voice_app_surface_full_coverage/audit_app_surface.py --check
- Board namespace: voice-app-surface-full-coverage-v2
- Bundle: vas2/inventory
- Parallel lane: wave-01-inventory-ui
- Resource class: cpu-medium
- Predicted files: scripts/voice_app_surface_full_coverage/audit_app_surface.py, data/voice_app_surface_full_coverage/baseline/app-surface-inventory.json, docs/voice_app_surface_full_coverage/APP_SURFACE_INVENTORY.md
- Conflict policy: Owns baseline inventory reports; no runtime UI edits except later tasks.
- Symbolic first: true
- LLM context budget bytes: 20480
- Acceptance: Census includes every primary/secondary/provider route and audit; module path + label + flags; NAVIGATION_SURFACE_IDS vs RouteId mismatches explicit.

## VAS2-006 Inventory agent tools, service actions, and voice bindings

- Status: completed
- Completion: manual
- Priority: P0
- Track: inventory
- Depends on: VAS2-002
- Goal id: VAS2-G020
- Outputs: data/voice_app_surface_full_coverage/baseline/tool-inventory.json, data/voice_app_surface_full_coverage/baseline/binding-inventory.json
- Validation: python scripts/voice_app_surface_full_coverage/audit_app_surface.py --check-tools
- Board namespace: voice-app-surface-full-coverage-v2
- Bundle: vas2/inventory
- Parallel lane: wave-01-inventory-tools
- Resource class: cpu-medium
- Predicted files: data/voice_app_surface_full_coverage/baseline/tool-inventory.json, data/voice_app_surface_full_coverage/baseline/binding-inventory.json
- Conflict policy: Additive inventory JSON only.
- Symbolic first: true
- LLM context budget bytes: 20480
- Acceptance: All agent tool modules listed; logical actions mapped; unbound tools flagged; adapters listed with package paths.

## VAS2-007 Diff app-surface inventory against v1 baseline

- Status: completed
- Completion: manual
- Priority: P1
- Track: inventory
- Depends on: VAS2-005, VAS2-004
- Goal id: VAS2-G020
- Outputs: data/voice_app_surface_full_coverage/baseline/inventory-diff-v1.json
- Validation: python scripts/voice_app_surface_full_coverage/audit_app_surface.py --check-diff-v1
- Board namespace: voice-app-surface-full-coverage-v2
- Bundle: vas2/inventory
- Parallel lane: wave-01-inventory-diff
- Resource class: cpu-small
- Predicted files: data/voice_app_surface_full_coverage/baseline/inventory-diff-v1.json
- Conflict policy: Diff report only.
- Symbolic first: true
- LLM context budget bytes: 12288
- Acceptance: Added/removed/changed surfaces and tools vs v1 listed with digests.

## VAS2-008 Classify voice/phone amenability for every surface

- Status: completed
- Completion: manual
- Priority: P0
- Track: exposure
- Depends on: VAS2-005, VAS2-006
- Goal id: VAS2-G030
- Outputs: data/voice_app_surface_full_coverage/baseline/voice-exposure-matrix.json, docs/voice_app_surface_full_coverage/VOICE_EXPOSURE_DOCTRINE.md, scripts/voice_app_surface_full_coverage/audit_voice_exposure.py
- Validation: python scripts/voice_app_surface_full_coverage/audit_voice_exposure.py --check
- Board namespace: voice-app-surface-full-coverage-v2
- Bundle: vas2/exposure
- Parallel lane: wave-01-exposure
- Resource class: cpu-medium
- Predicted files: data/voice_app_surface_full_coverage/baseline/voice-exposure-matrix.json, docs/voice_app_surface_full_coverage/VOICE_EXPOSURE_DOCTRINE.md, scripts/voice_app_surface_full_coverage/audit_voice_exposure.py
- Conflict policy: Owns exposure matrix vocabulary and classifications.
- Symbolic first: true
- LLM context budget bytes: 20480
- Acceptance: Every inventory surface classified; security/exports default never_voice; rationale+risk+channels recorded.

## VAS2-009 Publish coverage gap matrix against DAG, catalog, audio, e2e

- Status: completed
- Completion: manual
- Priority: P0
- Track: exposure
- Depends on: VAS2-008
- Goal id: VAS2-G030
- Outputs: data/voice_app_surface_full_coverage/baseline/coverage-gap-matrix.json, docs/voice_app_surface_full_coverage/COVERAGE_GAPS.md
- Validation: python scripts/voice_app_surface_full_coverage/audit_voice_exposure.py --check-gaps
- Board namespace: voice-app-surface-full-coverage-v2
- Bundle: vas2/exposure
- Parallel lane: wave-01-gaps
- Resource class: cpu-medium
- Predicted files: data/voice_app_surface_full_coverage/baseline/coverage-gap-matrix.json, docs/voice_app_surface_full_coverage/COVERAGE_GAPS.md
- Conflict policy: Owns gap matrix only.
- Symbolic first: true
- LLM context budget bytes: 16384
- Acceptance: Per-surface gaps for DAG density, catalog, adapter, audio, e2e; prioritized work queue for later waves.

## VAS2-010 Expand action catalog for all exposed surfaces

- Status: todo
- Completion: manual
- Priority: P0
- Track: catalog-policy
- Depends on: VAS2-008, VAS2-002
- Goal id: VAS2-G040
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/catalog_211ai.py, data/voice_app_surface_full_coverage/catalog/surface-catalog-delta.json, docs/voice_app_surface_full_coverage/CATALOG_SURFACE_DELTA.md
- Validation: python -m pytest -q ipfs_accelerate_py/test/test_action_catalog_211ai.py
- Board namespace: voice-app-surface-full-coverage-v2
- Bundle: vas2/catalog
- Parallel lane: wave-02-catalog
- Resource class: cpu-medium
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/catalog_211ai.py, data/voice_app_surface_full_coverage/catalog/surface-catalog-delta.json, docs/voice_app_surface_full_coverage/CATALOG_SURFACE_DELTA.md
- Conflict policy: Catalog owner for 211ai pilot/surface slice; no executable locators.
- Symbolic first: true
- LLM context budget bytes: 20480
- Acceptance: Descriptors cover all exposed P0+P1 surfaces/actions; delta receipt vs v1; golden tests pass.

## VAS2-011 Expand fail-closed policy matrix for exposure classes

- Status: todo
- Completion: manual
- Priority: P0
- Track: catalog-policy
- Depends on: VAS2-010
- Goal id: VAS2-G040
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/policy_pilot.py, docs/voice_app_surface_full_coverage/POLICY_SURFACE_MATRIX.md, ipfs_accelerate_py/test/test_action_policy_pilot.py
- Validation: python -m pytest -q ipfs_accelerate_py/test/test_action_policy_pilot.py
- Board namespace: voice-app-surface-full-coverage-v2
- Bundle: vas2/catalog
- Parallel lane: wave-02-policy
- Resource class: cpu-medium
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/policy_pilot.py, docs/voice_app_surface_full_coverage/POLICY_SURFACE_MATRIX.md, ipfs_accelerate_py/test/test_action_policy_pilot.py
- Conflict policy: Policy matrix owner; fail-closed predicates only.
- Symbolic first: true
- LLM context budget bytes: 16384
- Acceptance: Confirm/auth/channel predicates for each exposure class; staff_only/never_voice deny on client channel.

## VAS2-012 Bind app-surface allowlists and exposure gates

- Status: todo
- Completion: manual
- Priority: P0
- Track: adapters
- Depends on: VAS2-008, VAS2-010
- Goal id: VAS2-G050
- Outputs: wallet_interface/helpers/_voice_surface_exposure.py, wallet_interface/helpers/_voice_app_action_binding.py, docs/voice_app_surface_full_coverage/SURFACE_BINDINGS.md
- Validation: python -m pytest -q wallet_interface/tests -k surface_or_voice
- Board namespace: voice-app-surface-full-coverage-v2
- Bundle: vas2/adapters
- Parallel lane: wave-02-binding
- Resource class: cpu-medium
- Predicted files: wallet_interface/helpers/_voice_surface_exposure.py, wallet_interface/helpers/_voice_app_action_binding.py, docs/voice_app_surface_full_coverage/SURFACE_BINDINGS.md
- Conflict policy: Owns client binding/allowlist alignment with exposure matrix.
- Symbolic first: true
- LLM context budget bytes: 16384
- Acceptance: Allowlist matches voice_navigable set; deny tests for never_voice; aliases documented.

## VAS2-013 Wire offline adapters for exposed surface actions

- Status: todo
- Completion: manual
- Priority: P0
- Track: adapters
- Depends on: VAS2-012, VAS2-010
- Goal id: VAS2-G050
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/adapters/, tests for surface adapters, data/voice_app_surface_full_coverage/reports/adapter-coverage.json
- Validation: python -m pytest -q ipfs_accelerate_py/test -k action_runtime
- Board namespace: voice-app-surface-full-coverage-v2
- Bundle: vas2/adapters
- Parallel lane: wave-02-adapters
- Resource class: cpu-medium
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/adapters/, tests for surface adapters, data/voice_app_surface_full_coverage/reports/adapter-coverage.json
- Conflict policy: Adapter implementations offline-safe; no live network.
- Symbolic first: true
- LLM context budget bytes: 20480
- Acceptance: Fake adapters cover exposed actions; receipts redact secrets; coverage report lists bound surfaces.

## VAS2-014 Define variant lattice schema and raised floors

- Status: todo
- Completion: manual
- Priority: P0
- Track: variants
- Depends on: VAS2-008
- Goal id: VAS2-G060
- Outputs: scripts/voice_app_surface_full_coverage/build_surface_variant_lattice.py, docs/voice_app_surface_full_coverage/VARIANT_LATTICE.md, data/voice_app_surface_full_coverage/variants/schema.json
- Validation: python scripts/voice_app_surface_full_coverage/build_surface_variant_lattice.py --check-schema
- Board namespace: voice-app-surface-full-coverage-v2
- Bundle: vas2/variants
- Parallel lane: wave-03-variant-schema
- Resource class: cpu-small
- Predicted files: scripts/voice_app_surface_full_coverage/build_surface_variant_lattice.py, docs/voice_app_surface_full_coverage/VARIANT_LATTICE.md, data/voice_app_surface_full_coverage/variants/schema.json
- Conflict policy: Owns variant schema and floors config.
- Symbolic first: true
- LLM context budget bytes: 12288
- Acceptance: Schema encodes axes, floors (P0=500,P1=150,P2=80), ban list; --check-schema green.

## VAS2-015 Generate P0 variant lattices (≥500 unique paraphrases)

- Status: todo
- Completion: manual
- Priority: P0
- Track: variants
- Depends on: VAS2-014
- Goal id: VAS2-G060
- Outputs: data/voice_app_surface_full_coverage/variants/p0/, data/voice_app_surface_full_coverage/reports/variant-floors-p0.json
- Validation: python scripts/voice_app_surface_full_coverage/build_surface_variant_lattice.py --check --tier P0
- Board namespace: voice-app-surface-full-coverage-v2
- Bundle: vas2/variants
- Parallel lane: wave-03-variants-p0
- Resource class: cpu-large
- Predicted files: data/voice_app_surface_full_coverage/variants/p0/, data/voice_app_surface_full_coverage/reports/variant-floors-p0.json
- Conflict policy: Owns P0 surface lattices only.
- Symbolic first: true
- LLM context budget bytes: 24576
- Acceptance: Each P0 surface ≥500 unique user texts; axes coverage recorded; ban list clean.

## VAS2-016 Generate P1 variant lattices (≥150 unique paraphrases)

- Status: todo
- Completion: manual
- Priority: P0
- Track: variants
- Depends on: VAS2-014
- Goal id: VAS2-G060
- Outputs: data/voice_app_surface_full_coverage/variants/p1/, data/voice_app_surface_full_coverage/reports/variant-floors-p1.json
- Validation: python scripts/voice_app_surface_full_coverage/build_surface_variant_lattice.py --check --tier P1
- Board namespace: voice-app-surface-full-coverage-v2
- Bundle: vas2/variants
- Parallel lane: wave-03-variants-p1
- Resource class: cpu-large
- Predicted files: data/voice_app_surface_full_coverage/variants/p1/, data/voice_app_surface_full_coverage/reports/variant-floors-p1.json
- Conflict policy: Owns P1 lattices only.
- Symbolic first: true
- LLM context budget bytes: 20480
- Acceptance: Each exposed P1 surface ≥150 unique user texts.

## VAS2-017 Generate P2 secondary variant lattices (≥80 where exposed)

- Status: todo
- Completion: manual
- Priority: P1
- Track: variants
- Depends on: VAS2-014, VAS2-008
- Goal id: VAS2-G060
- Outputs: data/voice_app_surface_full_coverage/variants/p2/, data/voice_app_surface_full_coverage/reports/variant-floors-p2.json
- Validation: python scripts/voice_app_surface_full_coverage/build_surface_variant_lattice.py --check --tier P2
- Board namespace: voice-app-surface-full-coverage-v2
- Bundle: vas2/variants
- Parallel lane: wave-03-variants-p2
- Resource class: cpu-medium
- Predicted files: data/voice_app_surface_full_coverage/variants/p2/, data/voice_app_surface_full_coverage/reports/variant-floors-p2.json
- Conflict policy: Owns P2 secondary lattices only when exposure allows.
- Symbolic first: true
- LLM context budget bytes: 16384
- Acceptance: Each exposed P2 surface ≥80 unique user texts or explicit never_voice skip receipt.

## VAS2-018 Project variant lattices into DAG expansion packs

- Status: todo
- Completion: manual
- Priority: P0
- Track: dag
- Depends on: VAS2-015, VAS2-016
- Goal id: VAS2-G070
- Outputs: scripts/voice_app_surface_full_coverage/project_dag_expansion.py, data/voice_app_surface_full_coverage/dag_expansion/, docs/phone_dialog_generation/surface_expansion_edges_v2.jsonl
- Validation: python scripts/voice_app_surface_full_coverage/project_dag_expansion.py --check
- Board namespace: voice-app-surface-full-coverage-v2
- Bundle: vas2/dag
- Parallel lane: wave-04-dag-project
- Resource class: cpu-large
- Predicted files: scripts/voice_app_surface_full_coverage/project_dag_expansion.py, data/voice_app_surface_full_coverage/dag_expansion/, docs/phone_dialog_generation/surface_expansion_edges_v2.jsonl
- Conflict policy: Owns expansion packs + sidecar edges for v2 lattices.
- Symbolic first: true
- LLM context budget bytes: 20480
- Acceptance: Projected edges cover all P0/P1 lattices; P0 floor met per surface; digests recorded.

## VAS2-019 Fold surface expansion edges into slotted_response_dag

- Status: todo
- Completion: manual
- Priority: P0
- Track: dag
- Depends on: VAS2-018
- Goal id: VAS2-G070
- Outputs: scripts/voice_app_surface_full_coverage/fold_surface_expansion_into_dag.py, docs/phone_dialog_generation/slotted_response_dag.json, data/voice_app_surface_full_coverage/reports/dag-fold-receipt.json
- Validation: python scripts/voice_app_surface_full_coverage/fold_surface_expansion_into_dag.py --check
- Board namespace: voice-app-surface-full-coverage-v2
- Bundle: vas2/dag
- Parallel lane: wave-04-dag-fold
- Resource class: cpu-large
- Predicted files: scripts/voice_app_surface_full_coverage/fold_surface_expansion_into_dag.py, docs/phone_dialog_generation/slotted_response_dag.json, data/voice_app_surface_full_coverage/reports/dag-fold-receipt.json
- Conflict policy: Sole writer of slotted_response_dag fold for this program wave; pause thrashing supervisors first.
- Symbolic first: true
- LLM context budget bytes: 16384
- Acceptance: Fold applied with receipt digests; edge counts increase by projected amount; intents carry sparse embeddings.

## VAS2-020 Rebuild slotted_response_action_links for new routes

- Status: todo
- Completion: manual
- Priority: P0
- Track: dag
- Depends on: VAS2-019
- Goal id: VAS2-G070
- Outputs: docs/phone_dialog_generation/slotted_response_action_links.json, data/voice_app_surface_full_coverage/reports/action-link-rebuild-receipt.json
- Validation: python scripts/voice_app_surface_full_coverage/rebuild_action_links.py --check
- Board namespace: voice-app-surface-full-coverage-v2
- Bundle: vas2/dag
- Parallel lane: wave-04-action-links
- Resource class: cpu-medium
- Predicted files: docs/phone_dialog_generation/slotted_response_action_links.json, data/voice_app_surface_full_coverage/reports/action-link-rebuild-receipt.json
- Conflict policy: Owns action-link projection only.
- Symbolic first: true
- LLM context budget bytes: 12288
- Acceptance: All tool-adjacent routes map to catalog logical actions or explicit no_action; ban list clean.

## VAS2-021 Evaluate retrieval reliability on full variant lattice

- Status: todo
- Completion: manual
- Priority: P0
- Track: retrieval
- Depends on: VAS2-019, VAS2-015
- Goal id: VAS2-G080
- Outputs: scripts/voice_app_surface_full_coverage/eval_variant_retrieval.py, data/voice_app_surface_full_coverage/reports/retrieval-reliability.json
- Validation: python scripts/voice_app_surface_full_coverage/eval_variant_retrieval.py --check
- Board namespace: voice-app-surface-full-coverage-v2
- Bundle: vas2/retrieval
- Parallel lane: wave-04-retrieval-eval
- Resource class: cpu-large
- Predicted files: scripts/voice_app_surface_full_coverage/eval_variant_retrieval.py, data/voice_app_surface_full_coverage/reports/retrieval-reliability.json
- Conflict policy: Read-only over DAG; write report only.
- Symbolic first: true
- LLM context budget bytes: 20480
- Acceptance: Top-1/top-3 rates meet thresholds on P0 lattice; per-surface breakdown published.

## VAS2-022 Repair retrieval misses until thresholds pass

- Status: todo
- Completion: manual
- Priority: P0
- Track: retrieval
- Depends on: VAS2-021
- Goal id: VAS2-G080
- Outputs: data/voice_app_surface_full_coverage/reports/retrieval-repair-changelog.md, data/voice_app_surface_full_coverage/reports/retrieval-reliability-after-repair.json
- Validation: python scripts/voice_app_surface_full_coverage/eval_variant_retrieval.py --check --after-repair
- Board namespace: voice-app-surface-full-coverage-v2
- Bundle: vas2/retrieval
- Parallel lane: wave-04-retrieval-repair
- Resource class: cpu-large
- Predicted files: data/voice_app_surface_full_coverage/reports/retrieval-repair-changelog.md, data/voice_app_surface_full_coverage/reports/retrieval-reliability-after-repair.json
- Conflict policy: May add exemplars/edges only via documented repair; no policy weakening.
- Symbolic first: true
- LLM context budget bytes: 20480
- Acceptance: Post-repair thresholds green; changelog lists each fix with evidence.

## VAS2-023 Author action speech frames for exposed logical actions

- Status: todo
- Completion: manual
- Priority: P0
- Track: speech
- Depends on: VAS2-010, VAS2-008
- Goal id: VAS2-G090
- Outputs: docs/phone_dialog_generation/action_speech_frames.jsonl, scripts/voice_app_surface_full_coverage/audit_speech_frames.py
- Validation: python scripts/voice_app_surface_full_coverage/audit_speech_frames.py --check-actions
- Board namespace: voice-app-surface-full-coverage-v2
- Bundle: vas2/speech
- Parallel lane: wave-05-speech-actions
- Resource class: cpu-medium
- Predicted files: docs/phone_dialog_generation/action_speech_frames.jsonl, scripts/voice_app_surface_full_coverage/audit_speech_frames.py
- Conflict policy: Owns action speech frames corpus.
- Symbolic first: true
- LLM context budget bytes: 16384
- Acceptance: confirm/success/deny/fail for every exposed logical action; no secrets/URLs.

## VAS2-024 Author surface navigation speech frames

- Status: todo
- Completion: manual
- Priority: P0
- Track: speech
- Depends on: VAS2-008
- Goal id: VAS2-G090
- Outputs: docs/phone_dialog_generation/surface_navigation_speech_frames.jsonl
- Validation: python scripts/voice_app_surface_full_coverage/audit_speech_frames.py --check-surfaces
- Board namespace: voice-app-surface-full-coverage-v2
- Bundle: vas2/speech
- Parallel lane: wave-05-speech-surfaces
- Resource class: cpu-medium
- Predicted files: docs/phone_dialog_generation/surface_navigation_speech_frames.jsonl
- Conflict policy: Owns surface navigation speech frames.
- Symbolic first: true
- LLM context budget bytes: 16384
- Acceptance: confirm/success/deny/fail (or shared templates) for every voice_navigable surface.

## VAS2-025 Select and frame high-traffic DAG exemplars for audio

- Status: todo
- Completion: manual
- Priority: P1
- Track: speech
- Depends on: VAS2-019, VAS2-023
- Goal id: VAS2-G090
- Outputs: docs/phone_dialog_generation/dag_high_traffic_speech_frames.jsonl, data/voice_app_surface_full_coverage/reports/dag-speech-budget.json
- Validation: python scripts/voice_app_surface_full_coverage/audit_speech_frames.py --check-dag-budget
- Board namespace: voice-app-surface-full-coverage-v2
- Bundle: vas2/speech
- Parallel lane: wave-05-speech-dag
- Resource class: cpu-medium
- Predicted files: docs/phone_dialog_generation/dag_high_traffic_speech_frames.jsonl, data/voice_app_surface_full_coverage/reports/dag-speech-budget.json
- Conflict policy: Owns high-traffic DAG speech budget only.
- Symbolic first: true
- LLM context budget bytes: 16384
- Acceptance: Budget receipt lists top-N DAG response frames selected for audio; generate_required counts explicit.

## VAS2-026 Stage offline audio scaffolding for full speech corpus

- Status: todo
- Completion: manual
- Priority: P0
- Track: audio
- Depends on: VAS2-023, VAS2-024
- Goal id: VAS2-G100
- Outputs: data/voice_app_surface_full_coverage/audio/stage/, data/voice_app_surface_full_coverage/reports/audio-stage-receipt.json
- Validation: python scripts/voice_app_surface_full_coverage/audit_audio_coverage.py --check-stage
- Board namespace: voice-app-surface-full-coverage-v2
- Bundle: vas2/audio
- Parallel lane: wave-05-audio-stage
- Resource class: cpu-medium
- Predicted files: data/voice_app_surface_full_coverage/audio/stage/, data/voice_app_surface_full_coverage/reports/audio-stage-receipt.json
- Conflict policy: Offline stage only; no live TTS.
- Symbolic first: true
- LLM context budget bytes: 12288
- Acceptance: All speech frames staged offline or marked generate_required with counts; resolver scaffolding ready.

## VAS2-027 Run production IndexTTS regen for full generate_required set

- Status: todo
- Completion: manual
- Priority: P0
- Track: audio
- Depends on: VAS2-026
- Goal id: VAS2-G100
- Outputs: data/voice_app_surface_full_coverage/audio/production/, data/voice_app_surface_full_coverage/reports/audio-regen-batch.json, data/voice_app_surface_full_coverage/audio/production/response-manifest.json
- Validation: python scripts/voice_app_surface_full_coverage/audit_audio_coverage.py --check-regen
- Board namespace: voice-app-surface-full-coverage-v2
- Bundle: vas2/audio
- Parallel lane: wave-05-audio-regen
- Resource class: gpu-or-remote-tts
- Predicted files: data/voice_app_surface_full_coverage/audio/production/, data/voice_app_surface_full_coverage/reports/audio-regen-batch.json, data/voice_app_surface_full_coverage/audio/production/response-manifest.json
- Conflict policy: Human-gated live IndexTTS; sole owner of production audio tree for this batch; pause thrashers.
- Symbolic first: true
- LLM context budget bytes: 8192
- Acceptance: IndexTTS completes for full generate_required speech corpus; batch digest recorded; status completed or partial with residual budget.

## VAS2-028 Whisper-adjudicate production audio batch

- Status: todo
- Completion: manual
- Priority: P0
- Track: audio
- Depends on: VAS2-027
- Goal id: VAS2-G100
- Outputs: data/voice_app_surface_full_coverage/reports/whisper-adjudication.json
- Validation: python scripts/validate_abby_regeneration_whisper.py --check || python scripts/voice_app_surface_full_coverage/audit_audio_coverage.py --check-whisper
- Board namespace: voice-app-surface-full-coverage-v2
- Bundle: vas2/audio
- Parallel lane: wave-05-whisper
- Resource class: gpu-or-cpu-large
- Predicted files: data/voice_app_surface_full_coverage/reports/whisper-adjudication.json
- Conflict policy: Owns Whisper adjudication report for this program.
- Symbolic first: true
- LLM context budget bytes: 8192
- Acceptance: Whisper metrics for production set recorded; failures listed for re-render; gate thresholds explicit.

## VAS2-029 Promote audio manifests and publish coverage receipt

- Status: todo
- Completion: manual
- Priority: P0
- Track: audio
- Depends on: VAS2-028, VAS2-025
- Goal id: VAS2-G100
- Outputs: data/voice_app_surface_full_coverage/reports/audio-coverage.json, data/voice_app_surface_full_coverage/audio/stage/production/metadata/
- Validation: python scripts/voice_app_surface_full_coverage/audit_audio_coverage.py --check
- Board namespace: voice-app-surface-full-coverage-v2
- Bundle: vas2/audio
- Parallel lane: wave-05-audio-promote
- Resource class: cpu-medium
- Predicted files: data/voice_app_surface_full_coverage/reports/audio-coverage.json, data/voice_app_surface_full_coverage/audio/stage/production/metadata/
- Conflict policy: Promotion of manifests/resolver only after Whisper gate.
- Symbolic first: true
- LLM context budget bytes: 12288
- Acceptance: Coverage report shows production_indextts for speech corpus; high-traffic DAG budget tracked; smoke not claimed as production.

## VAS2-030 Offline e2e surface matrix for P0+P1 paraphrases

- Status: todo
- Completion: manual
- Priority: P0
- Track: e2e
- Depends on: VAS2-012, VAS2-022, VAS2-029
- Goal id: VAS2-G110
- Outputs: tests/e2e/voice_app_surface_full_coverage/test_surface_matrix.py, data/voice_app_surface_full_coverage/reports/e2e-surface-matrix.json
- Validation: python -m pytest -q tests/e2e/voice_app_surface_full_coverage/test_surface_matrix.py
- Board namespace: voice-app-surface-full-coverage-v2
- Bundle: vas2/e2e
- Parallel lane: wave-06-e2e-matrix
- Resource class: cpu-large
- Predicted files: tests/e2e/voice_app_surface_full_coverage/test_surface_matrix.py, data/voice_app_surface_full_coverage/reports/e2e-surface-matrix.json
- Conflict policy: E2E matrix owner; fake transports only.
- Symbolic first: true
- LLM context budget bytes: 20480
- Acceptance: P0+P1 surfaces open via ≥ floor paraphrases; confirm→adapter→receipt path green.

## VAS2-031 Adversarial e2e for never_voice and staff_only denies

- Status: todo
- Completion: manual
- Priority: P0
- Track: e2e
- Depends on: VAS2-012, VAS2-008
- Goal id: VAS2-G110
- Outputs: tests/e2e/voice_app_surface_full_coverage/test_adversarial.py, data/voice_app_surface_full_coverage/reports/e2e-adversarial.json
- Validation: python -m pytest -q tests/e2e/voice_app_surface_full_coverage/test_adversarial.py
- Board namespace: voice-app-surface-full-coverage-v2
- Bundle: vas2/e2e
- Parallel lane: wave-06-e2e-adv
- Resource class: cpu-medium
- Predicted files: tests/e2e/voice_app_surface_full_coverage/test_adversarial.py, data/voice_app_surface_full_coverage/reports/e2e-adversarial.json
- Conflict policy: Adversarial suite owner.
- Symbolic first: true
- LLM context budget bytes: 16384
- Acceptance: never_voice and staff_only denied on client channel; injection cannot invent descriptors.

## VAS2-032 DAG-sample simulation suite for real slotted exemplars

- Status: todo
- Completion: manual
- Priority: P1
- Track: e2e
- Depends on: VAS2-019, VAS2-030
- Goal id: VAS2-G110
- Outputs: tests/e2e/voice_app_surface_full_coverage/test_dag_chat_simulation.py, data/voice_app_surface_full_coverage/reports/e2e-dag-sim.json
- Validation: python -m pytest -q tests/e2e/voice_app_surface_full_coverage/test_dag_chat_simulation.py
- Board namespace: voice-app-surface-full-coverage-v2
- Bundle: vas2/e2e
- Parallel lane: wave-06-e2e-dag
- Resource class: cpu-large
- Predicted files: tests/e2e/voice_app_surface_full_coverage/test_dag_chat_simulation.py, data/voice_app_surface_full_coverage/reports/e2e-dag-sim.json
- Conflict policy: Read-only over DAG; write report only.
- Symbolic first: true
- LLM context budget bytes: 16384
- Acceptance: Samples real DAG chats per tool-adjacent route; proposal→policy→adapter path asserts.

## VAS2-033 Operator runbook and enablement checklist

- Status: todo
- Completion: manual
- Priority: P0
- Track: operations
- Depends on: VAS2-001, VAS2-029, VAS2-030
- Goal id: VAS2-G120
- Outputs: docs/planning/VOICE_APP_SURFACE_FULL_COVERAGE_AGENT_SUPERVISOR_RUNBOOK.md, docs/voice_app_surface_full_coverage/ENABLEMENT_CHECKLIST.md
- Validation: test -f docs/planning/VOICE_APP_SURFACE_FULL_COVERAGE_AGENT_SUPERVISOR_RUNBOOK.md && test -f docs/voice_app_surface_full_coverage/ENABLEMENT_CHECKLIST.md
- Board namespace: voice-app-surface-full-coverage-v2
- Bundle: vas2/ops
- Parallel lane: wave-06-ops
- Resource class: cpu-small
- Predicted files: docs/planning/VOICE_APP_SURFACE_FULL_COVERAGE_AGENT_SUPERVISOR_RUNBOOK.md, docs/voice_app_surface_full_coverage/ENABLEMENT_CHECKLIST.md
- Conflict policy: Owns operator docs for this program.
- Symbolic first: true
- LLM context budget bytes: 12288
- Acceptance: Runbook covers submodule pull, shards, fake transports, audio gates, product flags; checklist maps evidence to goals.

## VAS2-034 Coverage dashboard projection for supervisor status

- Status: todo
- Completion: manual
- Priority: P1
- Track: operations
- Depends on: VAS2-009, VAS2-021, VAS2-029, VAS2-030
- Goal id: VAS2-G120
- Outputs: scripts/voice_app_surface_full_coverage/project_coverage_status.py, data/voice_app_surface_full_coverage/projection/control-status.json
- Validation: python scripts/voice_app_surface_full_coverage/project_coverage_status.py --check
- Board namespace: voice-app-surface-full-coverage-v2
- Bundle: vas2/ops
- Parallel lane: wave-06-projection
- Resource class: cpu-small
- Predicted files: scripts/voice_app_surface_full_coverage/project_coverage_status.py, data/voice_app_surface_full_coverage/projection/control-status.json
- Conflict policy: Owns projection JSON only.
- Symbolic first: true
- LLM context budget bytes: 8192
- Acceptance: Projection summarizes inventory %, density floors, retrieval rates, audio %, e2e green/red.

## VAS2-035 Program release evidence bundle and signoff

- Status: todo
- Completion: manual
- Priority: P0
- Track: e2e
- Depends on: VAS2-030, VAS2-031, VAS2-028, VAS2-003
- Goal id: VAS2-G000
- Outputs: data/voice_app_surface_full_coverage/reports/program-release-evidence.json, docs/voice_app_surface_full_coverage/PROGRAM_SIGNOFF.md
- Validation: python scripts/voice_app_surface_full_coverage/project_coverage_status.py --check-release
- Board namespace: voice-app-surface-full-coverage-v2
- Bundle: vas2/root
- Parallel lane: wave-06-signoff
- Resource class: cpu-small
- Predicted files: data/voice_app_surface_full_coverage/reports/program-release-evidence.json, docs/voice_app_surface_full_coverage/PROGRAM_SIGNOFF.md
- Conflict policy: Aggregates digests only; does not mutate product flags.
- Symbolic first: true
- LLM context budget bytes: 8192
- Acceptance: Evidence binds submodule pins, exposure matrix, DAG density, retrieval rates, audio+Whisper, e2e; signoff lists residuals.

