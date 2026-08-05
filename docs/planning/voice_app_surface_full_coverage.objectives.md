# Voice × App-Surface Full Coverage Objective Heap (v2)

Durable intent heap for full 211-AI app-surface voice coverage under large
paraphrase lattices with production audio. Companion task board:
`docs/planning/voice_app_surface_full_coverage.todo.md`.

Task completion alone never completes an objective. Objective completion
requires fresh, content-bound evidence.

Program invariants:

- Board namespace: `voice-app-surface-full-coverage-v2`.
- Content plane never embeds executables, URLs, import paths, credentials, or argv.
- Retrieval proposes catalog logical actions only.
- Surface opens/mutations require policy + confirmation (and auth when write).
- never_voice / staff_only fail closed on client voice/phone channels.
- Autonomous workers use fake/local transports; live TTS/HF publish is human-gated.
- Pull ipfs_accelerate_py and ipfs_datasets_py from origin/main before parallel waves.
- Prerequisite: voice-app-surface-coverage-v1 completed (baseline inventories reusable).

## VAS2-G000 Deliver full voice coverage of the 211-AI app surface

- Status: active
- Parent: 
- Fib priority: 1
- Track: program
- Priority: P0
- Bundle: vas2/root
- Goal: Make every voice-amenable part of the 211-AI app surface reliably reachable from phone/voice under a large paraphrase lattice, with governed actions and production Abby audio for confirm/outcome and high-traffic DAG frames.
- Evidence: vas2/program-release@1, vas2/surface-coverage-matrix@1, vas2/dag-variant-reliability@1, vas2/audio-coverage@1, vas2/e2e-surface-matrix@1
- Outputs: docs/planning/VOICE_APP_SURFACE_FULL_COVERAGE_PLAN.md, docs/planning/voice_app_surface_full_coverage.objectives.md, docs/planning/voice_app_surface_full_coverage.todo.md, docs/planning/voice_app_surface_full_coverage.supervisor.json, scripts/validate_voice_app_surface_full_coverage_plan.py
- Validation: python scripts/validate_voice_app_surface_full_coverage_plan.py
- Acceptance: All RouteIds classified; P0+P1 voice_navigable/voice_actionable surfaces meet raised floors; production audio+Whisper for speech corpus; never_voice denied; e2e green; release evidence published.
- Gap task: Refill the highest-priority uncovered surface criterion with one bounded task and explicit evidence contract.
- Refinement: Keep inventory, catalog, variants, DAG, audio, and e2e in independent lanes after submodule sync.
- Embedding query: 211-AI full app surface voice phone DAG audio coverage v2
- AST query: RouteId NAVIGATION_SURFACE_IDS slotted_response_dag open_app_surface VoiceActionBridge

## VAS2-G010 Sync submodules and freeze supervisor control plane

- Status: active
- Parent: VAS2-G000
- Fib priority: 1
- Track: operations
- Priority: P0
- Bundle: vas2/ops-bootstrap
- Goal: Pull ipfs_accelerate_py and ipfs_datasets_py from origin/main, verify voice modules, pin SHAs, create merge target, and freeze preflight/supervisor control for this board.
- Evidence: vas2/submodule-pins@1, vas2/voice-module-probe@1, vas2/supervisor-preflight@1, vas2/merge-target@1
- Outputs: data/voice_app_surface_full_coverage/baseline/submodule-pins.json, docs/planning/voice_app_surface_full_coverage.supervisor.json, scripts/validate_voice_app_surface_full_coverage_plan.py
- Validation: python scripts/validate_voice_app_surface_full_coverage_plan.py
- Acceptance: Pin receipt records accelerate+datasets origin/main SHAs; voice modules import; protected paths listed; four shards; workers cannot edit plan board.
- Gap task: Repair one pin, probe, protected path, or preflight invariant.
- Refinement: Human reviews submodule pointer commits before enabling refill.
- Embedding query: submodule origin main pin supervisor merge target preflight voice modules
- AST query: action_runtime action_links action_retrieval record_submodule_pins

## VAS2-G020 Inventory the entire app surface and tool plane

- Status: active
- Parent: VAS2-G000
- Fib priority: 2
- Track: inventory
- Priority: P0
- Bundle: vas2/inventory
- Goal: Re-census every RouteId, screen module, agent tool, deep-link, and voice/action binding against the current monorepo; diff vs v1 baseline.
- Evidence: vas2/app-surface-inventory@1, vas2/tool-inventory@1, vas2/binding-inventory@1, vas2/inventory-diff-v1@1
- Outputs: data/voice_app_surface_full_coverage/baseline/app-surface-inventory.json, data/voice_app_surface_full_coverage/baseline/tool-inventory.json, docs/voice_app_surface_full_coverage/APP_SURFACE_INVENTORY.md
- Validation: python scripts/voice_app_surface_full_coverage/audit_app_surface.py --check
- Acceptance: Inventory complete with symbol evidence; mismatches vs UI RouteId and NAVIGATION_SURFACE_IDS explicit; v1 delta report published.
- Gap task: Add one missing screen or tool symbol.
- Refinement: Prefer AST/static tables over narrative claims; reuse v1 auditors where safe.
- Embedding query: inventory RouteId navigationTools agent tools surface registry diff v1
- AST query: primaryRoutes secondaryRoutes NAVIGATION_SURFACE_IDS

## VAS2-G030 Classify voice/phone amenability for every surface

- Status: active
- Parent: VAS2-G000
- Fib priority: 3
- Track: exposure
- Priority: P0
- Bundle: vas2/exposure
- Goal: Assign every surface an exposure class with risk/channel/role/rationale; freeze matrix as authority for later waves; publish full gap matrix.
- Evidence: vas2/voice-exposure-matrix@1, vas2/exposure-doctrine@1, vas2/coverage-gap-matrix@1
- Outputs: data/voice_app_surface_full_coverage/baseline/voice-exposure-matrix.json, data/voice_app_surface_full_coverage/baseline/coverage-gap-matrix.json, docs/voice_app_surface_full_coverage/VOICE_EXPOSURE_DOCTRINE.md
- Validation: python scripts/voice_app_surface_full_coverage/audit_voice_exposure.py --check
- Acceptance: 100% surfaces classified; never_voice defaults for security/export risks; gap matrix lists DAG/catalog/audio/e2e holes per surface.
- Gap task: Reclassify one contested surface with written rationale.
- Refinement: Conservative default: unknown → never_voice.
- Embedding query: voice exposure matrix never_voice staff_only navigable
- AST query: voice_navigable never_voice staff_only voice-exposure-matrix

## VAS2-G040 Expand catalog and policy for exposed surfaces

- Status: active
- Parent: VAS2-G000
- Fib priority: 5
- Track: catalog-policy
- Priority: P0
- Bundle: vas2/catalog
- Goal: Extend deployment-owned catalog and fail-closed policy so every exposed client surface maps to reviewed descriptors with confirm/auth/channel constraints.
- Evidence: vas2/catalog-digest@1, vas2/policy-matrix@1, vas2/descriptor-golden@1
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/catalog_211ai.py, docs/voice_app_surface_full_coverage/POLICY_SURFACE_MATRIX.md, tests under action_runtime
- Validation: python -m pytest -q ipfs_accelerate_py/test/test_action_catalog_211ai.py ipfs_accelerate_py/test/test_action_policy_pilot.py
- Acceptance: P0+P1 surfaces have required descriptors; unknown ids fail closed; staff_only rejects client channel; no executable locators.
- Gap task: Add or correct one descriptor or policy predicate.
- Refinement: Prefer additive catalog versioning.
- Embedding query: ActionDescriptor open_app_surface policy confirm auth
- AST query: build_pilot_catalog PilotPolicy RiskClass

## VAS2-G050 Bind adapters and app-surface allowlists

- Status: active
- Parent: VAS2-G000
- Fib priority: 5
- Track: adapters
- Priority: P0
- Bundle: vas2/adapters
- Goal: Bind adapters and app-surface allowlists to the exposure matrix; deny never_voice/staff_only on client channel; privacy-safe receipts.
- Evidence: vas2/surface-binding@1, vas2/adapter-deny@1, vas2/receipt-redaction@1
- Outputs: wallet_interface/helpers/_voice_surface_exposure.py, wallet_interface/helpers/_voice_app_action_binding.py, docs/voice_app_surface_full_coverage/SURFACE_BINDINGS.md
- Validation: python -m pytest -q wallet_interface/tests -k voice_or_surface
- Acceptance: Each voice_navigable surface resolves; never_voice denies without mutation; fake surface API covers offline e2e.
- Gap task: Add one deny or alias resolution test.
- Refinement: Keep navigation allowlist in lockstep with UI RouteId set.
- Embedding query: NAVIGATION_SURFACE_IDS resolve_navigation_surface deny
- AST query: resolve_navigation_surface InMemoryAppSurfaceApi

## VAS2-G060 Build large per-surface request variant lattices

- Status: active
- Parent: VAS2-G000
- Fib priority: 5
- Track: variants
- Priority: P0
- Bundle: vas2/variants
- Goal: Build large per-surface request variant lattices meeting raised floors (P0≥500, P1≥150, P2≥80) across paraphrase/dialect/slot/multi-turn/noise/negative axes.
- Evidence: vas2/variant-lattice@1, vas2/variant-digest@1, vas2/variant-floors@1
- Outputs: data/voice_app_surface_full_coverage/variants/, scripts/voice_app_surface_full_coverage/build_surface_variant_lattice.py, docs/voice_app_surface_full_coverage/VARIANT_LATTICE.md
- Validation: python scripts/voice_app_surface_full_coverage/build_surface_variant_lattice.py --check
- Acceptance: All exposed P0/P1 surfaces meet floors; variants tagged surface_id + logical_action/no_action + axes; content ban list enforced.
- Gap task: Add one surface lattice below floor.
- Refinement: Deterministic generation preferred; LLM fill only behind symbolic schema.
- Embedding query: paraphrase lattice calendar variants STT noise 500
- AST query: variant_lattice surface_id paraphrase axes

## VAS2-G070 Expand and fold slotted DAG for surface reachability

- Status: active
- Parent: VAS2-G000
- Fib priority: 8
- Track: dag
- Priority: P0
- Bundle: vas2/dag
- Goal: Expand and fold slotted DAG sections so exposed surfaces are densely reachable; rebalance away from live_agent monopolization; rebuild action links.
- Evidence: vas2/dag-density@1, vas2/dag-fold-receipt@1, vas2/action-links@1
- Outputs: docs/phone_dialog_generation/slotted_response_dag.json, docs/phone_dialog_generation/surface_expansion_edges.jsonl, docs/phone_dialog_generation/slotted_response_action_links.json, data/voice_app_surface_full_coverage/reports/dag-fold-receipt.json
- Validation: python scripts/voice_app_surface_full_coverage/project_dag_expansion.py --check && python scripts/voice_app_surface_full_coverage/fold_surface_expansion_into_dag.py --check
- Acceptance: P0 surfaces meet DAG exemplar floors after fold; action links cover new routes; fold receipt digests published.
- Gap task: Add one under-covered surface pack and re-fold.
- Refinement: Prefer additive shards + deterministic fold over ad-hoc DAG edits.
- Embedding query: slotted_response_dag surface_expansion fold density
- AST query: intent_to_response_frame surface_expansion_edges

## VAS2-G080 Prove retrieval reliability across the variant lattice

- Status: active
- Parent: VAS2-G000
- Fib priority: 8
- Track: retrieval
- Priority: P0
- Bundle: vas2/retrieval
- Goal: Prove offline retrieval reliability over the full variant lattice; repair failures until thresholds met.
- Evidence: vas2/retrieval-reliability@1, vas2/retrieval-repair@1
- Outputs: data/voice_app_surface_full_coverage/reports/retrieval-reliability.json, scripts/voice_app_surface_full_coverage/eval_variant_retrieval.py
- Validation: python scripts/voice_app_surface_full_coverage/eval_variant_retrieval.py --check
- Acceptance: Top-1/top-3 hit rates meet program thresholds on P0 lattice; repair changelog for misses.
- Gap task: Repair one failing surface family.
- Refinement: Symbolic BM25/embedding eval before any model change.
- Embedding query: retrieval reliability paraphrase top-1 top-3 lattice
- AST query: eval_variant_retrieval canonicalQueryTemplate

## VAS2-G090 Author speech frames for surfaces and actions

- Status: active
- Parent: VAS2-G000
- Fib priority: 8
- Track: speech
- Priority: P0
- Bundle: vas2/speech
- Goal: Author speech frames for every exposed logical action and navigable surface (confirm/success/deny/fail) without secrets or executables.
- Evidence: vas2/speech-frames@1, vas2/speech-corpus-digest@1
- Outputs: docs/phone_dialog_generation/action_speech_frames.jsonl, docs/phone_dialog_generation/surface_navigation_speech_frames.jsonl, docs/phone_dialog_generation/dag_high_traffic_speech_frames.jsonl
- Validation: python scripts/voice_app_surface_full_coverage/audit_speech_frames.py --check
- Acceptance: Full role coverage for exposed actions/surfaces; high-traffic DAG exemplar frames budgeted; ban list clean.
- Gap task: Add frames for one missing action or surface.
- Refinement: Reuse shared templates only when slot-safe.
- Embedding query: action speech frames confirm outcome surface navigation
- AST query: action_speech_frames surface_navigation_speech_frames

## VAS2-G100 Regenerate and validate production audio coverage

- Status: active
- Parent: VAS2-G000
- Fib priority: 13
- Track: audio
- Priority: P0
- Bundle: vas2/audio
- Goal: Regenerate production IndexTTS for the full speech corpus and budgeted DAG exemplars; Whisper-adjudicate; promote manifests; fail closed on quality gates.
- Evidence: vas2/audio-regen-batch@1, vas2/whisper-adjudication@1, vas2/audio-coverage@1
- Outputs: data/voice_app_surface_full_coverage/audio/, data/voice_app_surface_full_coverage/reports/audio-regen-batch.json, data/voice_app_surface_full_coverage/reports/whisper-adjudication.json
- Validation: python scripts/voice_app_surface_full_coverage/audit_audio_coverage.py --check
- Acceptance: generate_required rows for speech corpus are production-staged; Whisper metrics recorded; smoke fixtures not claimed as production.
- Gap task: Re-run one failed batch chunk or Whisper subset.
- Refinement: Live TTS is human-gated; workers stage offline first.
- Embedding query: IndexTTS Whisper production audio full surface coverage
- AST query: precompute_indextts_responses validate_abby_regeneration_whisper

## VAS2-G110 Prove offline e2e reachability of the app surface

- Status: active
- Parent: VAS2-G000
- Fib priority: 8
- Track: e2e
- Priority: P0
- Bundle: vas2/e2e
- Goal: Prove offline e2e reachability: variant→route→proposal→confirm→fake adapter→speak for P0+P1; adversarial never_voice/staff_only denies.
- Evidence: vas2/e2e-matrix@1, vas2/e2e-adversarial@1, vas2/e2e-dag-sim@1
- Outputs: tests/e2e/voice_app_surface_full_coverage/, data/voice_app_surface_full_coverage/reports/e2e-*.json
- Validation: python -m pytest -q tests/e2e/voice_app_surface_full_coverage
- Acceptance: Matrix green for P0+P1; adversarial denies hold; DAG sample sims green.
- Gap task: Add one failing surface case.
- Refinement: Fake transports only; no live network in e2e workers.
- Embedding query: e2e voice surface matrix adversarial fake adapter
- AST query: test_surface_matrix test_adversarial

## VAS2-G120 Operate program enablement and supervisor lanes

- Status: active
- Parent: VAS2-G000
- Fib priority: 5
- Track: operations
- Priority: P0
- Bundle: vas2/ops
- Goal: Operate enablement: runbook, checklist, coverage projection, release evidence bundle for parallel supervisor execution.
- Evidence: vas2/enablement@1, vas2/projection@1, vas2/program-release@1
- Outputs: docs/planning/VOICE_APP_SURFACE_FULL_COVERAGE_AGENT_SUPERVISOR_RUNBOOK.md, docs/voice_app_surface_full_coverage/ENABLEMENT_CHECKLIST.md, data/voice_app_surface_full_coverage/projection/control-status.json, data/voice_app_surface_full_coverage/reports/program-release-evidence.json
- Validation: python scripts/voice_app_surface_full_coverage/project_coverage_status.py --check-release
- Acceptance: Runbook covers submodule pull, shards, gates; projection summarizes floors; release evidence binds digests.
- Gap task: Repair one missing evidence binding.
- Refinement: Sole owner of projection/signoff aggregation.
- Embedding query: enablement checklist supervisor projection release evidence
- AST query: project_coverage_status program-release-evidence

