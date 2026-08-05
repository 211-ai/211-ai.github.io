# Voice × App-Surface Coverage Task Board

Executable projection of `voice_app_surface_coverage.objectives.md` for
`ipfs_accelerate_py.agent_supervisor`.

Program invariants:

- Board namespace is `voice-app-surface-coverage-v1`; task identities are stable.
- Pull `ipfs_accelerate_py` and `ipfs_datasets_py` from `origin/main` before
  implementation waves that edit those trees.
- Content never embeds executables, URLs, import paths, credentials, or argv.
- Retrieval proposes catalog logical actions only.
- Mutations fail closed without policy, confirmation, and (when required) auth.
- Autonomous workers use fake/local transports only; live TTS/HF publish is
  human-gated.
- Symbolic checks precede bounded LLM repair.
- Completion requires current-tree validation evidence.

## VAS-001 Bootstrap supervisor control and protected plan namespace

- Status: completed
- Completion: manual
- Priority: P0
- Track: operations
- Depends on:
- Goal id: VAS-G010
- Outputs: docs/voice_app_surface_coverage/AGENT_SUPERVISOR_STATE.md, docs/voice_app_surface_coverage/runtime-policy.json, scripts/voice_app_surface_coverage/supervisor_control.py, tests/voice_app_surface_coverage/test_supervisor_control.py
- Validation: python scripts/validate_voice_app_surface_coverage_plan.py
- Board namespace: voice-app-surface-coverage-v1
- Bundle: vas/ops-bootstrap
- Parallel lane: wave-00-control
- Resource class: cpu-small
- Predicted files: docs/voice_app_surface_coverage/AGENT_SUPERVISOR_STATE.md, docs/voice_app_surface_coverage/runtime-policy.json, scripts/voice_app_surface_coverage/supervisor_control.py, tests/voice_app_surface_coverage/test_supervisor_control.py
- Conflict policy: Exclusive owner of supervisor launch policy and protected-path configuration for this board.
- Symbolic first: true
- LLM context budget bytes: 12288
- Acceptance: Preflight validates objectives and this board; merge target `agent/voice-app-surface-coverage` rules are explicit; four shards defined; plan files protected; publication and credentials remain disabled by default.

## VAS-002 Pull ipfs_accelerate_py and ipfs_datasets_py from origin/main

- Status: completed
- Completion: manual
- Priority: P0
- Track: operations
- Depends on: VAS-001
- Goal id: VAS-G010
- Outputs: data/voice_app_surface_coverage/baseline/submodule-pins.json, scripts/voice_app_surface_coverage/record_submodule_pins.py
- Validation: python scripts/voice_app_surface_coverage/record_submodule_pins.py --check
- Board namespace: voice-app-surface-coverage-v1
- Bundle: vas/ops-bootstrap
- Parallel lane: wave-00-submodules
- Resource class: io-medium
- Predicted files: data/voice_app_surface_coverage/baseline/submodule-pins.json, scripts/voice_app_surface_coverage/record_submodule_pins.py, ipfs_accelerate_py, ipfs_datasets_py
- Conflict policy: Human-gated submodule pointer update only; never force-push submodule remotes; record SHAs before and after pull.
- Symbolic first: true
- LLM context budget bytes: 8192
- Acceptance: Both submodules are fast-forwarded to their origin/main tips (or documented pin if main unavailable); pin JSON includes remote URLs, SHAs, fetch time, and operator note; monorepo submodule gitlinks updated only with explicit review; dirty unrelated submodule content is not discarded.

## VAS-003 Re-pin merge base after submodule sync

- Status: completed
- Completion: manual
- Priority: P0
- Track: operations
- Depends on: VAS-002
- Goal id: VAS-G010
- Outputs: docs/planning/voice_app_surface_coverage.supervisor.json, data/voice_app_surface_coverage/baseline/merge-base-receipt.json
- Validation: python scripts/validate_voice_app_surface_coverage_plan.py
- Board namespace: voice-app-surface-coverage-v1
- Bundle: vas/ops-bootstrap
- Parallel lane: wave-00-repin
- Resource class: cpu-small
- Predicted files: docs/planning/voice_app_surface_coverage.supervisor.json, data/voice_app_surface_coverage/baseline/merge-base-receipt.json
- Conflict policy: Sole owner of expected_base_commit field for this board during bootstrap.
- Symbolic first: true
- LLM context budget bytes: 8192
- Acceptance: Launch profile expected_base_commit matches monorepo origin/main after submodule pointer commit (or documents intentional lag); merge target creation remains FF-only from that base; receipt records old→new base.

## VAS-004 Inventory all RouteIds, screens, and navigation allowlists

- Status: completed
- Completion: manual
- Priority: P0
- Track: inventory
- Depends on: VAS-002
- Goal id: VAS-G020
- Outputs: scripts/voice_app_surface_coverage/audit_app_surface.py, data/voice_app_surface_coverage/baseline/app-surface-inventory.json, docs/voice_app_surface_coverage/APP_SURFACE_INVENTORY.md
- Validation: python scripts/voice_app_surface_coverage/audit_app_surface.py --check
- Board namespace: voice-app-surface-coverage-v1
- Bundle: vas/inventory
- Parallel lane: wave-01-inventory-ui
- Resource class: cpu-medium
- Predicted files: scripts/voice_app_surface_coverage/audit_app_surface.py, data/voice_app_surface_coverage/baseline/app-surface-inventory.json, docs/voice_app_surface_coverage/APP_SURFACE_INVENTORY.md
- Conflict policy: Owns baseline inventory reports only; must not modify runtime UI modules except via later tasks.
- Symbolic first: true
- LLM context budget bytes: 20480
- Acceptance: Census includes every primary/secondary/provider route and audit; each entry records module path, label, primary vs secondary, provider flag, and hash route; diffs NAVIGATION_SURFACE_IDS vs UI RouteId set with explicit mismatches.

## VAS-005 Inventory agent tools, service actions, and voice bindings

- Status: completed
- Completion: manual
- Priority: P0
- Track: inventory
- Depends on: VAS-002
- Goal id: VAS-G020
- Outputs: data/voice_app_surface_coverage/baseline/tool-inventory.json, data/voice_app_surface_coverage/baseline/binding-inventory.json
- Validation: python scripts/voice_app_surface_coverage/audit_app_surface.py --check-tools
- Board namespace: voice-app-surface-coverage-v1
- Bundle: vas/inventory
- Parallel lane: wave-01-inventory-tools
- Resource class: cpu-medium
- Predicted files: data/voice_app_surface_coverage/baseline/tool-inventory.json, data/voice_app_surface_coverage/baseline/binding-inventory.json, scripts/voice_app_surface_coverage/audit_app_surface.py
- Conflict policy: Additive inventory JSON only; shared audit script coordinates with VAS-004 via non-overlapping report files.
- Symbolic first: true
- LLM context budget bytes: 20480
- Acceptance: All agent tool modules listed with exports; pilot logical actions mapped to bindings; unbound tools flagged; action_runtime adapters listed with package paths.

## VAS-006 Classify voice/phone amenability for every surface

- Status: completed
- Completion: manual
- Priority: P0
- Track: exposure
- Depends on: VAS-004, VAS-005
- Goal id: VAS-G030
- Outputs: data/voice_app_surface_coverage/baseline/voice-exposure-matrix.json, docs/voice_app_surface_coverage/VOICE_EXPOSURE_DOCTRINE.md, scripts/voice_app_surface_coverage/audit_voice_exposure.py
- Validation: python scripts/voice_app_surface_coverage/audit_voice_exposure.py --check
- Board namespace: voice-app-surface-coverage-v1
- Bundle: vas/exposure
- Parallel lane: wave-01-exposure
- Resource class: cpu-medium
- Predicted files: data/voice_app_surface_coverage/baseline/voice-exposure-matrix.json, docs/voice_app_surface_coverage/VOICE_EXPOSURE_DOCTRINE.md, scripts/voice_app_surface_coverage/audit_voice_exposure.py
- Conflict policy: Owns exposure matrix vocabulary and classifications.
- Symbolic first: true
- LLM context budget bytes: 20480
- Acceptance: Every inventory surface has class in {voice_navigable, voice_actionable, voice_read_only, phone_handoff, staff_only, never_voice}; security/exports-like risks default never_voice; rationale + risk_class + allowed_channels recorded; unknown defaults never_voice.

## VAS-007 Publish coverage gap matrix against DAG, catalog, audio, e2e

- Status: completed
- Completion: manual
- Priority: P0
- Track: exposure
- Depends on: VAS-006
- Goal id: VAS-G030
- Outputs: data/voice_app_surface_coverage/baseline/coverage-gap-matrix.json, docs/voice_app_surface_coverage/COVERAGE_GAPS.md
- Validation: python scripts/voice_app_surface_coverage/audit_voice_exposure.py --check-gaps
- Board namespace: voice-app-surface-coverage-v1
- Bundle: vas/exposure
- Parallel lane: wave-01-gaps
- Resource class: cpu-medium
- Predicted files: data/voice_app_surface_coverage/baseline/coverage-gap-matrix.json, docs/voice_app_surface_coverage/COVERAGE_GAPS.md
- Conflict policy: Owns gap report only.
- Symbolic first: true
- LLM context budget bytes: 16384
- Acceptance: For each surface, report DAG edge count (or none), catalog actions, adapter presence, speech-frame presence, audio status, e2e presence; P0 holes prioritized.

## VAS-008 Expand pilot catalog for P0 navigable and actionable surfaces

- Status: todo
- Completion: manual
- Priority: P0
- Track: catalog-policy
- Depends on: VAS-006, VAS-002
- Goal id: VAS-G040
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/catalog_211ai.py, data/voice_action_dag/catalog/211ai-pilot-v1.json, ipfs_accelerate_py/test/test_action_catalog_211ai.py, docs/voice_app_surface_coverage/CATALOG_SURFACE_DELTA.md
- Validation: PYTHONPATH=ipfs_accelerate_py:ipfs_datasets_py:ipfs_kit_py python -m pytest -q ipfs_accelerate_py/test/test_action_catalog_211ai.py
- Board namespace: voice-app-surface-coverage-v1
- Bundle: vas/catalog
- Parallel lane: wave-02-catalog
- Resource class: cpu-medium
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/catalog_211ai.py, data/voice_action_dag/catalog/211ai-pilot-v1.json, ipfs_accelerate_py/test/test_action_catalog_211ai.py, docs/voice_app_surface_coverage/CATALOG_SURFACE_DELTA.md
- Conflict policy: Exclusive owner of pilot catalog identifiers for this board wave; coordinate additive descriptor ids only.
- Symbolic first: true
- LLM context budget bytes: 20480
- Acceptance: Catalog covers open/read/write needs for all P0 exposed surfaces; digest stable; no executable locators; staff_only actions marked with channel constraints.

## VAS-009 Extend policy matrix for surface roles and channels

- Status: todo
- Completion: manual
- Priority: P0
- Track: catalog-policy
- Depends on: VAS-008
- Goal id: VAS-G040
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/policy_pilot.py, docs/voice_app_surface_coverage/POLICY_SURFACE_MATRIX.md, ipfs_accelerate_py/test/test_action_policy_pilot.py
- Validation: PYTHONPATH=ipfs_accelerate_py:ipfs_datasets_py:ipfs_kit_py python -m pytest -q ipfs_accelerate_py/test/test_action_policy_pilot.py
- Board namespace: voice-app-surface-coverage-v1
- Bundle: vas/catalog
- Parallel lane: wave-02-policy
- Resource class: cpu-medium
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/policy_pilot.py, docs/voice_app_surface_coverage/POLICY_SURFACE_MATRIX.md, ipfs_accelerate_py/test/test_action_policy_pilot.py
- Conflict policy: Owns pilot policy predicates for surface/channel grants.
- Symbolic first: true
- LLM context budget bytes: 16384
- Acceptance: Tests prove client channel cannot open staff_only; never_voice always deny; reads confirm; writes confirm+auth; confidence cannot upgrade authority.

## VAS-010 Expand app-surface binding allowlist and aliases

- Status: todo
- Completion: manual
- Priority: P0
- Track: adapters
- Depends on: VAS-006, VAS-008
- Goal id: VAS-G050
- Outputs: wallet_interface/helpers/_voice_app_action_binding.py, docs/voice_app_surface_coverage/SURFACE_BINDINGS.md, wallet_interface/tests/test_voice_app_action_binding_surfaces.py
- Validation: python -m pytest -q wallet_interface/tests/test_voice_app_action_binding_surfaces.py
- Board namespace: voice-app-surface-coverage-v1
- Bundle: vas/adapters
- Parallel lane: wave-02-binding
- Resource class: cpu-medium
- Predicted files: wallet_interface/helpers/_voice_app_action_binding.py, docs/voice_app_surface_coverage/SURFACE_BINDINGS.md, wallet_interface/tests/test_voice_app_action_binding_surfaces.py
- Conflict policy: Exclusive owner of NAVIGATION_SURFACE_IDS / alias maps for this program.
- Symbolic first: true
- LLM context budget bytes: 16384
- Acceptance: Allowlist matches inventory; aliases cover natural phrases (calendar, wallet, messages, services); never_voice ids reject; fake API records opens offline.

## VAS-011 Wire missing adapters for newly exposed actionable surfaces

- Status: todo
- Completion: manual
- Priority: P0
- Track: adapters
- Depends on: VAS-009, VAS-010
- Goal id: VAS-G050
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/adapters, ipfs_accelerate_py/test, docs/voice_app_surface_coverage/ADAPTER_SURFACE_DELTA.md
- Validation: PYTHONPATH=ipfs_accelerate_py:ipfs_datasets_py:ipfs_kit_py python -m pytest -q ipfs_accelerate_py/test/ -k adapter
- Board namespace: voice-app-surface-coverage-v1
- Bundle: vas/adapters
- Parallel lane: wave-02-adapters
- Resource class: cpu-medium
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/adapters, ipfs_accelerate_py/test, docs/voice_app_surface_coverage/ADAPTER_SURFACE_DELTA.md
- Conflict policy: One adapter module family per PR; no live network.
- Symbolic first: true
- LLM context budget bytes: 24576
- Acceptance: Every voice_actionable P0 surface has offline adapter path or documented reuse of existing adapter; receipts redact secrets; denies without permit.

## VAS-012 Build variant lattice schema and generator

- Status: todo
- Completion: manual
- Priority: P0
- Track: variants
- Depends on: VAS-006
- Goal id: VAS-G060
- Outputs: scripts/voice_app_surface_coverage/build_surface_variant_lattice.py, docs/voice_app_surface_coverage/VARIANT_LATTICE.md, data/voice_app_surface_coverage/variants/schema.json
- Validation: python scripts/voice_app_surface_coverage/build_surface_variant_lattice.py --check-schema
- Board namespace: voice-app-surface-coverage-v1
- Bundle: vas/variants
- Parallel lane: wave-03-variant-schema
- Resource class: cpu-small
- Predicted files: scripts/voice_app_surface_coverage/build_surface_variant_lattice.py, docs/voice_app_surface_coverage/VARIANT_LATTICE.md, data/voice_app_surface_coverage/variants/schema.json
- Conflict policy: Owns variant schema and generator CLI.
- Symbolic first: true
- LLM context budget bytes: 16384
- Acceptance: Schema includes surface_id, user_text, axes, logical_action or no_action, negative flags; banlist rejects locator fields; floors configurable per priority.

## VAS-013 Generate P0 client-core surface variant lattices

- Status: todo
- Completion: manual
- Priority: P0
- Track: variants
- Depends on: VAS-012
- Goal id: VAS-G060
- Outputs: data/voice_app_surface_coverage/variants/home.jsonl, data/voice_app_surface_coverage/variants/calendar.jsonl, data/voice_app_surface_coverage/variants/messages.jsonl, data/voice_app_surface_coverage/variants/uploads.jsonl, data/voice_app_surface_coverage/variants/social-services.jsonl, data/voice_app_surface_coverage/variants/check-in.jsonl, data/voice_app_surface_coverage/variants/contacts.jsonl, data/voice_app_surface_coverage/variants/interactions.jsonl, data/voice_app_surface_coverage/variants/settings.jsonl
- Validation: python scripts/voice_app_surface_coverage/build_surface_variant_lattice.py --check --priority P0
- Board namespace: voice-app-surface-coverage-v1
- Bundle: vas/variants
- Parallel lane: wave-03-variants-p0
- Resource class: cpu-medium
- Predicted files: data/voice_app_surface_coverage/variants/home.jsonl, data/voice_app_surface_coverage/variants/calendar.jsonl, data/voice_app_surface_coverage/variants/messages.jsonl, data/voice_app_surface_coverage/variants/uploads.jsonl, data/voice_app_surface_coverage/variants/social-services.jsonl, data/voice_app_surface_coverage/variants/check-in.jsonl, data/voice_app_surface_coverage/variants/contacts.jsonl, data/voice_app_surface_coverage/variants/interactions.jsonl, data/voice_app_surface_coverage/variants/settings.jsonl
- Conflict policy: Owns P0 variant JSONL files; non-overlapping surface filenames.
- Symbolic first: true
- LLM context budget bytes: 24576
- Acceptance: Each P0 surface file has ≥200 unique user_text strings (or documented exception); axes cover paraphrase, slot, noise, negative; content banlist clean; includes calendar phrases like “what is on my calendar”.

## VAS-014 Generate P1 and staff_only negative variant lattices

- Status: todo
- Completion: manual
- Priority: P1
- Track: variants
- Depends on: VAS-012, VAS-006
- Goal id: VAS-G060
- Outputs: data/voice_app_surface_coverage/variants/p1/, data/voice_app_surface_coverage/variants/negatives-staff-never.jsonl
- Validation: python scripts/voice_app_surface_coverage/build_surface_variant_lattice.py --check --priority P1
- Board namespace: voice-app-surface-coverage-v1
- Bundle: vas/variants
- Parallel lane: wave-03-variants-p1
- Resource class: cpu-medium
- Predicted files: data/voice_app_surface_coverage/variants/p1/, data/voice_app_surface_coverage/variants/negatives-staff-never.jsonl
- Conflict policy: Owns P1/negative lattices only.
- Symbolic first: true
- LLM context budget bytes: 16384
- Acceptance: P1 surfaces ≥50 paraphrases; negatives assert staff_only/never_voice intended deny; no executable content.

## VAS-015 Expand slotted DAG density for calendar and app navigation

- Status: todo
- Completion: manual
- Priority: P0
- Track: dag
- Depends on: VAS-013, VAS-002
- Goal id: VAS-G070
- Outputs: scripts/voice_app_surface_coverage/audit_dag_surface_density.py, data/voice_app_surface_coverage/reports/dag-density-calendar-nav.json, docs/phone_dialog_generation/surface_expansion_calendar_nav.md
- Validation: python scripts/voice_app_surface_coverage/audit_dag_surface_density.py --check --routes calendar_event_support,app_surface_navigation
- Board namespace: voice-app-surface-coverage-v1
- Bundle: vas/dag
- Parallel lane: wave-03-dag-calendar-nav
- Resource class: cpu-large
- Predicted files: scripts/voice_app_surface_coverage/audit_dag_surface_density.py, data/voice_app_surface_coverage/reports/dag-density-calendar-nav.json, docs/phone_dialog_generation/surface_expansion_calendar_nav.md
- Conflict policy: Owns calendar + app_surface_navigation DAG expansion inputs; coordinate rebuild locks.
- Symbolic first: true
- LLM context budget bytes: 24576
- Acceptance: Density floors met for these routes relative to program thresholds; exemplars include high-variance calendar reads and surface opens; deterministic rebuild path documented.

## VAS-016 Expand slotted DAG density for messages, wallet, services

- Status: todo
- Completion: manual
- Priority: P0
- Track: dag
- Depends on: VAS-013, VAS-002
- Goal id: VAS-G070
- Outputs: data/voice_app_surface_coverage/reports/dag-density-messages-wallet-services.json, docs/phone_dialog_generation/surface_expansion_messages_wallet_services.md
- Validation: python scripts/voice_app_surface_coverage/audit_dag_surface_density.py --check --routes provider_contact_support,wallet_document_support,grounded_211_answer,service_interaction_support
- Board namespace: voice-app-surface-coverage-v1
- Bundle: vas/dag
- Parallel lane: wave-03-dag-msg-wallet-svc
- Resource class: cpu-large
- Predicted files: data/voice_app_surface_coverage/reports/dag-density-messages-wallet-services.json, docs/phone_dialog_generation/surface_expansion_messages_wallet_services.md
- Conflict policy: Owns these route families only; do not expand live_agent without quota task.
- Symbolic first: true
- LLM context budget bytes: 24576
- Acceptance: Density floors met; service exemplars remain grounded-evidence friendly; action links still valid.

## VAS-017 Expand slotted DAG density for remaining P0 surfaces and check-in

- Status: todo
- Completion: manual
- Priority: P0
- Track: dag
- Depends on: VAS-013
- Goal id: VAS-G070
- Outputs: data/voice_app_surface_coverage/reports/dag-density-p0-remaining.json, docs/phone_dialog_generation/surface_expansion_p0_remaining.md
- Validation: python scripts/voice_app_surface_coverage/audit_dag_surface_density.py --check --priority P0
- Board namespace: voice-app-surface-coverage-v1
- Bundle: vas/dag
- Parallel lane: wave-03-dag-remaining-p0
- Resource class: cpu-large
- Predicted files: data/voice_app_surface_coverage/reports/dag-density-p0-remaining.json, docs/phone_dialog_generation/surface_expansion_p0_remaining.md
- Conflict policy: Owns remaining P0 navigable surfaces; may introduce new route names only with action-link + doctrine update.
- Symbolic first: true
- LLM context budget bytes: 24576
- Acceptance: All P0 surfaces meet floors either via existing routes or approved new routes; census updated.

## VAS-018 Rebuild action-link projection after DAG expansion

- Status: todo
- Completion: manual
- Priority: P0
- Track: dag
- Depends on: VAS-015, VAS-016, VAS-017
- Goal id: VAS-G070
- Outputs: docs/phone_dialog_generation/slotted_response_action_links.json, scripts/build_slotted_response_action_links.py, tests/test_build_slotted_response_action_links.py
- Validation: python scripts/build_slotted_response_action_links.py --check && python -m pytest -q tests/test_build_slotted_response_action_links.py
- Board namespace: voice-app-surface-coverage-v1
- Bundle: vas/dag
- Parallel lane: wave-03-action-links
- Resource class: cpu-medium
- Predicted files: docs/phone_dialog_generation/slotted_response_action_links.json, scripts/build_slotted_response_action_links.py, tests/test_build_slotted_response_action_links.py
- Conflict policy: Sole rebuild owner for action-link projection in this program wave.
- Symbolic first: true
- LLM context budget bytes: 12288
- Acceptance: All routes (including any new ones) appear; content-only remain no_action; tool-adjacent map to pilot actions; rebuild byte-stable.

## VAS-019 Evaluate offline retrieval reliability on variant lattice

- Status: todo
- Completion: manual
- Priority: P0
- Track: retrieval
- Depends on: VAS-018, VAS-013, VAS-008
- Goal id: VAS-G080
- Outputs: scripts/voice_app_surface_coverage/eval_variant_retrieval.py, data/voice_app_surface_coverage/reports/retrieval-reliability.json, docs/voice_app_surface_coverage/RETRIEVAL_RELIABILITY.md
- Validation: python scripts/voice_app_surface_coverage/eval_variant_retrieval.py --check
- Board namespace: voice-app-surface-coverage-v1
- Bundle: vas/retrieval
- Parallel lane: wave-03-retrieval-eval
- Resource class: cpu-large
- Predicted files: scripts/voice_app_surface_coverage/eval_variant_retrieval.py, data/voice_app_surface_coverage/reports/retrieval-reliability.json, docs/voice_app_surface_coverage/RETRIEVAL_RELIABILITY.md
- Conflict policy: Owns evaluation harness and report; may not silently lower thresholds.
- Symbolic first: true
- LLM context budget bytes: 20480
- Acceptance: Publishes top-1/top-3 hit rates per surface; fails if P0 below thresholds defined in VARIANT_LATTICE.md; confusion matrix written; injection suite denies new descriptors.

## VAS-020 Repair lowest-scoring surface confusions

- Status: todo
- Completion: manual
- Priority: P0
- Track: retrieval
- Depends on: VAS-019
- Goal id: VAS-G080
- Outputs: data/voice_app_surface_coverage/reports/retrieval-reliability-after-repair.json, data/voice_app_surface_coverage/reports/retrieval-repair-changelog.md, ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/voice_bridge.py
- Validation: python scripts/voice_app_surface_coverage/eval_variant_retrieval.py --check
- Board namespace: voice-app-surface-coverage-v1
- Bundle: vas/retrieval
- Parallel lane: wave-03-retrieval-repair
- Resource class: cpu-medium
- Predicted files: data/voice_app_surface_coverage/reports/retrieval-reliability-after-repair.json, data/voice_app_surface_coverage/reports/retrieval-repair-changelog.md, ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/voice_bridge.py
- Conflict policy: Bounded repair of worst N confusions only; no policy weakening.
- Symbolic first: true
- LLM context budget bytes: 20480
- Acceptance: Worst P0 pairs improve past threshold; re-eval green; changelog of repairs recorded.

## VAS-021 Expand speech frames for all P0 surfaces and actions

- Status: todo
- Completion: manual
- Priority: P0
- Track: speech
- Depends on: VAS-008, VAS-018
- Goal id: VAS-G090
- Outputs: docs/phone_dialog_generation/action_speech_frames.jsonl, docs/phone_dialog_generation/surface_navigation_speech_frames.jsonl, scripts/build_abby_action_speech_frames.py, tests/voice/test_abby_action_speech_frames.py
- Validation: python scripts/build_abby_action_speech_frames.py --check
- Board namespace: voice-app-surface-coverage-v1
- Bundle: vas/speech
- Parallel lane: wave-04-speech
- Resource class: cpu-medium
- Predicted files: docs/phone_dialog_generation/action_speech_frames.jsonl, docs/phone_dialog_generation/surface_navigation_speech_frames.jsonl, scripts/build_abby_action_speech_frames.py, tests/voice/test_abby_action_speech_frames.py
- Conflict policy: Owns speech frame corpora for this program.
- Symbolic first: true
- LLM context budget bytes: 20480
- Acceptance: confirm/success/deny/fail for each P0 logical action; navigation frames for each P0 surface or safe shared template with surface_label; banlist clean.

## VAS-022 Stage offline audio fixtures for speech frames

- Status: todo
- Completion: manual
- Priority: P0
- Track: audio
- Depends on: VAS-021
- Goal id: VAS-G100
- Outputs: scripts/stage_abby_action_audio.py, data/voice_app_surface_coverage/reports/audio-stage-receipt.json, data/voice_app_surface_coverage/audio/stage/README.md
- Validation: python scripts/voice_app_surface_coverage/audit_audio_coverage.py --check-stage
- Board namespace: voice-app-surface-coverage-v1
- Bundle: vas/audio
- Parallel lane: wave-04-audio-stage
- Resource class: gpu-or-cpu-large
- Predicted files: scripts/stage_abby_action_audio.py, data/voice_app_surface_coverage/reports/audio-stage-receipt.json, data/voice_app_surface_coverage/audio/stage/README.md
- Conflict policy: Staging only; no HF publish; exclusive stage directory for this board.
- Symbolic first: true
- LLM context budget bytes: 12288
- Acceptance: P0 frames staged or marked generate_required with budget; manifests list digests; offline paths only.

## VAS-023 Human-gated IndexTTS regeneration batch for P0 coverage

- Status: todo
- Completion: manual
- Priority: P0
- Track: audio
- Depends on: VAS-022
- Goal id: VAS-G100
- Outputs: data/voice_app_surface_coverage/reports/audio-regen-batch-p0.json, data/voice_app_surface_coverage/reports/audio-regen-operator-notes.md
- Validation: python scripts/voice_app_surface_coverage/audit_audio_coverage.py --check-regen-receipt
- Board namespace: voice-app-surface-coverage-v1
- Bundle: vas/audio
- Parallel lane: wave-04-audio-regen
- Resource class: gpu-large
- Predicted files: data/voice_app_surface_coverage/reports/audio-regen-batch-p0.json, data/voice_app_surface_coverage/reports/audio-regen-operator-notes.md
- Conflict policy: Human-gated live TTS Space only; credentials not in argv; sole batch owner for P0.
- Symbolic first: true
- LLM context budget bytes: 8192
- Acceptance: Operator enables Space/network explicitly; batch covers P0 generate_required set or documents partial budget; no autonomous credential use.

## VAS-024 Whisper-adjudicate and publish audio coverage receipt

- Status: todo
- Completion: manual
- Priority: P0
- Track: audio
- Depends on: VAS-023
- Goal id: VAS-G100
- Outputs: data/voice_app_surface_coverage/reports/audio-coverage.json, data/voice_app_surface_coverage/reports/whisper-adjudication-p0.json, data/voice_app_surface_coverage/reports/resolver-offline-smoke.json
- Validation: python scripts/voice_app_surface_coverage/audit_audio_coverage.py --check
- Board namespace: voice-app-surface-coverage-v1
- Bundle: vas/audio
- Parallel lane: wave-04-audio-validate
- Resource class: cpu-large
- Predicted files: data/voice_app_surface_coverage/reports/audio-coverage.json, data/voice_app_surface_coverage/reports/whisper-adjudication-p0.json, data/voice_app_surface_coverage/reports/resolver-offline-smoke.json
- Conflict policy: Owns coverage receipt; fail closed on whisper gate regressions for P0.
- Symbolic first: true
- LLM context budget bytes: 12288
- Acceptance: Coverage JSON lists each P0 frame audio status validated|generate_required|failed; resolver offline smoke green for validated rows; failures ticketed.

## VAS-025 Offline e2e surface matrix from variants through adapters

- Status: todo
- Completion: manual
- Priority: P0
- Track: e2e
- Depends on: VAS-011, VAS-019, VAS-021
- Goal id: VAS-G110
- Outputs: tests/e2e/voice_app_surface_coverage/test_surface_matrix.py, docs/voice_app_surface_coverage/E2E_SURFACE_MATRIX.md
- Validation: python -m pytest -q tests/e2e/voice_app_surface_coverage/test_surface_matrix.py
- Board namespace: voice-app-surface-coverage-v1
- Bundle: vas/e2e
- Parallel lane: wave-05-e2e-matrix
- Resource class: cpu-medium
- Predicted files: tests/e2e/voice_app_surface_coverage/test_surface_matrix.py, docs/voice_app_surface_coverage/E2E_SURFACE_MATRIX.md
- Conflict policy: Owns e2e matrix harness.
- Symbolic first: true
- LLM context budget bytes: 24576
- Acceptance: Every P0 voice_navigable surface reached by ≥5 paraphrases end-to-end offline; actionable paths confirm→execute; calendar “what is on my calendar” included; no network.

## VAS-026 Adversarial e2e for never_voice and staff_only denies

- Status: todo
- Completion: manual
- Priority: P0
- Track: e2e
- Depends on: VAS-009, VAS-010, VAS-014
- Goal id: VAS-G110
- Outputs: tests/e2e/voice_app_surface_coverage/test_surface_adversarial.py
- Validation: python -m pytest -q tests/e2e/voice_app_surface_coverage/test_surface_adversarial.py
- Board namespace: voice-app-surface-coverage-v1
- Bundle: vas/e2e
- Parallel lane: wave-05-e2e-adv
- Resource class: cpu-medium
- Predicted files: tests/e2e/voice_app_surface_coverage/test_surface_adversarial.py
- Conflict policy: Owns adversarial suite.
- Symbolic first: true
- LLM context budget bytes: 16384
- Acceptance: never_voice and staff_only client-channel attempts deny without surface mutation; injection cannot invent descriptors; secrets never appear in receipts/speech.

## VAS-027 DAG-sample simulation suite for real slotted exemplars

- Status: todo
- Completion: manual
- Priority: P1
- Track: e2e
- Depends on: VAS-018, VAS-025
- Goal id: VAS-G110
- Outputs: tests/e2e/voice_app_surface_coverage/test_dag_chat_simulation.py, data/voice_app_surface_coverage/reports/dag-chat-sim-receipt.json
- Validation: python -m pytest -q tests/e2e/voice_app_surface_coverage/test_dag_chat_simulation.py
- Board namespace: voice-app-surface-coverage-v1
- Bundle: vas/e2e
- Parallel lane: wave-05-e2e-dag-sim
- Resource class: cpu-large
- Predicted files: tests/e2e/voice_app_surface_coverage/test_dag_chat_simulation.py, data/voice_app_surface_coverage/reports/dag-chat-sim-receipt.json
- Conflict policy: Read-only over large DAG; write only report.
- Symbolic first: true
- LLM context budget bytes: 16384
- Acceptance: Samples real DAG chats per tool-adjacent route; asserts proposal→policy→adapter path; content-only remain no_action.

## VAS-028 Operator runbook and enablement checklist

- Status: todo
- Completion: manual
- Priority: P0
- Track: operations
- Depends on: VAS-001, VAS-024, VAS-025
- Goal id: VAS-G120
- Outputs: docs/planning/VOICE_APP_SURFACE_COVERAGE_AGENT_SUPERVISOR_RUNBOOK.md, docs/voice_app_surface_coverage/ENABLEMENT_CHECKLIST.md
- Validation: test -f docs/planning/VOICE_APP_SURFACE_COVERAGE_AGENT_SUPERVISOR_RUNBOOK.md && test -f docs/voice_app_surface_coverage/ENABLEMENT_CHECKLIST.md
- Board namespace: voice-app-surface-coverage-v1
- Bundle: vas/ops
- Parallel lane: wave-05-ops
- Resource class: cpu-small
- Predicted files: docs/planning/VOICE_APP_SURFACE_COVERAGE_AGENT_SUPERVISOR_RUNBOOK.md, docs/voice_app_surface_coverage/ENABLEMENT_CHECKLIST.md
- Conflict policy: Owns operator docs for this program.
- Symbolic first: true
- LLM context budget bytes: 12288
- Acceptance: Runbook covers submodule pull, shard start, fake transports, audio human gates, product flags; checklist maps evidence artifacts to goals G010–G110.

## VAS-029 Coverage dashboard projection for supervisor status

- Status: todo
- Completion: manual
- Priority: P1
- Track: operations
- Depends on: VAS-007, VAS-019, VAS-024, VAS-025
- Goal id: VAS-G120
- Outputs: scripts/voice_app_surface_coverage/project_coverage_status.py, data/voice_app_surface_coverage/projection/control-status.json
- Validation: python scripts/voice_app_surface_coverage/project_coverage_status.py --check
- Board namespace: voice-app-surface-coverage-v1
- Bundle: vas/ops
- Parallel lane: wave-05-projection
- Resource class: cpu-small
- Predicted files: scripts/voice_app_surface_coverage/project_coverage_status.py, data/voice_app_surface_coverage/projection/control-status.json
- Conflict policy: Owns projection JSON only.
- Symbolic first: true
- LLM context budget bytes: 8192
- Acceptance: Projection summarizes inventory %, density floors, retrieval rates, audio %, e2e green/red; suitable for supervisor control status.

## VAS-030 Program release evidence bundle

- Status: todo
- Completion: manual
- Priority: P0
- Track: e2e
- Depends on: VAS-025, VAS-026, VAS-024, VAS-003
- Goal id: VAS-G000
- Outputs: data/voice_app_surface_coverage/reports/program-release-evidence.json, docs/voice_app_surface_coverage/PROGRAM_SIGNOFF.md
- Validation: python scripts/voice_app_surface_coverage/project_coverage_status.py --check-release
- Board namespace: voice-app-surface-coverage-v1
- Bundle: vas/root
- Parallel lane: wave-05-signoff
- Resource class: cpu-small
- Predicted files: data/voice_app_surface_coverage/reports/program-release-evidence.json, docs/voice_app_surface_coverage/PROGRAM_SIGNOFF.md
- Conflict policy: Aggregates digests only; does not mutate product flags.
- Symbolic first: true
- LLM context budget bytes: 8192
- Acceptance: Evidence binds submodule pins, exposure matrix digest, DAG density, retrieval rates, audio coverage, e2e results; signoff lists residual generate_required budgets.
