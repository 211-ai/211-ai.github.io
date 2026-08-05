# Voice × App-Surface Coverage Objective Heap

Durable intent heap for examining the full 211-AI app surface, exposing
voice/phone-amenable surfaces, expanding the Abby slotted DAG under many
request variants, and regenerating audio coverage.

Companion task board: `docs/planning/voice_app_surface_coverage.todo.md`.

Task completion alone never completes an objective. Objective completion
requires fresh, content-bound evidence for the surface matrix revision, DAG
variant digests, catalog digest, audio coverage receipt, and acceptance
criterion under review.

Program invariants:

- Board namespace: `voice-app-surface-coverage-v1`.
- Content plane never embeds executables, URLs, import paths, credentials, or argv.
- Retrieval proposes catalog logical actions only.
- Surface opens and mutations require policy + confirmation (and auth when write).
- `never_voice` / `staff_only` surfaces fail closed on client voice/phone channels.
- Autonomous workers use fake/local transports; live TTS/HF publish is human-gated.
- Pull `ipfs_accelerate_py` and `ipfs_datasets_py` from `origin/main` before
  parallel implementation waves.

## VAS-G000 Deliver voice coverage of the 211-AI app surface

- Status: active
- Parent:
- Fib priority: 1
- Track: program
- Priority: P0
- Bundle: vas/root
- Goal: Make every voice-amenable part of the 211-AI app surface reliably reachable from phone/voice under a large paraphrase lattice, with governed actions and precomputed Abby audio for confirmation and outcomes.
- Evidence: vas/program-release-root@1, vas/surface-coverage-matrix@1, vas/dag-variant-reliability@1, vas/audio-coverage@1, vas/e2e-surface-matrix@1
- Outputs: docs/planning/VOICE_APP_SURFACE_COVERAGE_PLAN.md, docs/planning/voice_app_surface_coverage.objectives.md, docs/planning/voice_app_surface_coverage.todo.md, docs/planning/voice_app_surface_coverage.supervisor.json, scripts/validate_voice_app_surface_coverage_plan.py
- Validation: python scripts/validate_voice_app_surface_coverage_plan.py
- Acceptance: All RouteIds classified; every voice_navigable/voice_actionable client surface has catalog binding, DAG paraphrase floor, speech frames, and offline e2e green; never_voice surfaces denied on client channel; audio coverage receipt published for P0 set.
- Gap task: Refill the highest-priority uncovered surface criterion with one bounded task and an explicit evidence contract.
- Refinement: Keep inventory, catalog, DAG variants, audio, and e2e in independent lanes after submodule sync.
- Embedding query: 211-AI app surface voice phone calendar messages wallet DAG audio coverage
- AST query: RouteId NAVIGATION_SURFACE_IDS slotted_response_dag open_app_surface VoiceActionBridge

## VAS-G010 Sync submodules and freeze supervisor control plane

- Status: active
- Parent: VAS-G000
- Fib priority: 1
- Track: operations
- Priority: P0
- Bundle: vas/ops-bootstrap
- Goal: Pull ipfs_accelerate_py and ipfs_datasets_py from origin/main, pin SHAs, create merge target, and make preflight/supervisor control fail-closed for this board.
- Evidence: vas/submodule-pins@1, vas/supervisor-preflight@1, vas/merge-target@1
- Outputs: data/voice_app_surface_coverage/baseline/submodule-pins.json, docs/planning/voice_app_surface_coverage.supervisor.json, scripts/validate_voice_app_surface_coverage_plan.py, docs/voice_app_surface_coverage/AGENT_SUPERVISOR_STATE.md
- Validation: python scripts/validate_voice_app_surface_coverage_plan.py
- Acceptance: Pin receipt records accelerate + datasets SHAs from origin/main; protected plan paths listed; four shards defined; merge target rules explicit; workers cannot edit plan board.
- Gap task: Repair one pin, protected path, or preflight invariant.
- Refinement: Human reviews submodule pointer commits before enabling refill.
- Embedding query: submodule origin main pin supervisor merge target preflight
- AST query: parse_goal_heap parse_task_file materialize_task_dependency_dag

## VAS-G020 Inventory the entire app surface and tool plane

- Status: active
- Parent: VAS-G000
- Fib priority: 2
- Track: inventory
- Priority: P0
- Bundle: vas/inventory
- Goal: Produce a machine-readable census of every RouteId, screen module, agent tool, deep-link hash, and existing voice/action binding with AST-backed evidence.
- Evidence: vas/app-surface-inventory@1, vas/tool-inventory@1, vas/binding-inventory@1
- Outputs: scripts/voice_app_surface_coverage/audit_app_surface.py, data/voice_app_surface_coverage/baseline/app-surface-inventory.json, docs/voice_app_surface_coverage/APP_SURFACE_INVENTORY.md
- Validation: python scripts/voice_app_surface_coverage/audit_app_surface.py --check
- Acceptance: Inventory lists all primary/secondary/provider routes plus audit; each entry binds file path + export symbol; navigation allowlist and UI RouteId sets are diffed; missing bindings flagged.
- Gap task: Add one missing screen or tool symbol to the census.
- Refinement: Prefer AST and static tables over narrative claims.
- Embedding query: inventory RouteId navigationTools screen agent tools surface registry
- AST query: primaryRoutes secondaryRoutes NAVIGATION_SURFACE_IDS navigationTools

## VAS-G030 Classify voice/phone amenability for every surface

- Status: active
- Parent: VAS-G000
- Fib priority: 3
- Track: exposure
- Priority: P0
- Bundle: vas/exposure
- Goal: Assign each surface an exposure class (voice_navigable, voice_actionable, voice_read_only, phone_handoff, staff_only, never_voice) with risk, channel, role, and rationale; freeze the matrix as the authority for later waves.
- Evidence: vas/voice-exposure-matrix@1, vas/exposure-doctrine@1, vas/coverage-gap-matrix@1
- Outputs: data/voice_app_surface_coverage/baseline/voice-exposure-matrix.json, data/voice_app_surface_coverage/baseline/coverage-gap-matrix.json, docs/voice_app_surface_coverage/VOICE_EXPOSURE_DOCTRINE.md
- Validation: python scripts/voice_app_surface_coverage/audit_voice_exposure.py --check
- Acceptance: 100% of inventory surfaces classified; never_voice includes security/export-like risks by default unless human override receipt exists; gap matrix lists DAG density, catalog, adapter, audio, and e2e holes per surface.
- Gap task: Reclassify one contested surface with written rationale.
- Refinement: Conservative default: unknown → never_voice until reviewed.
- Embedding query: voice exposure matrix never_voice staff_only navigable calendar messages
- AST query: voice_navigable never_voice staff_only voice-exposure-matrix

## VAS-G040 Expand catalog and policy for exposed surfaces

- Status: active
- Parent: VAS-G000
- Fib priority: 5
- Track: catalog-policy
- Priority: P0
- Bundle: vas/catalog
- Goal: Extend the deployment-owned action catalog and fail-closed policy so every voice_navigable/voice_actionable client surface maps to reviewed descriptors with confirm/auth/channel constraints.
- Evidence: vas/catalog-digest@1, vas/policy-matrix@1, vas/descriptor-golden@1
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/catalog_211ai.py, data/voice_action_dag/catalog/211ai-pilot-v1.json or additive vas catalog slice, policy tests, docs/voice_app_surface_coverage/POLICY_SURFACE_MATRIX.md
- Validation: python -m pytest -q ipfs_accelerate_py/test/test_action_catalog_211ai.py ipfs_accelerate_py/test/test_action_policy_pilot.py
- Acceptance: P0 surfaces have open/read/write descriptors as required by exposure class; unknown ids fail closed; no executable locators; staff_only descriptors reject client channel.
- Gap task: Add or correct one descriptor or policy predicate.
- Refinement: Prefer additive catalog versioning over silent renames.
- Embedding query: ActionDescriptor open_app_surface surface_id policy confirm auth staff_only
- AST query: build_pilot_catalog PilotPolicy RiskClass open_app_surface

## VAS-G050 Bind adapters and app-surface allowlists to the exposure matrix

- Status: active
- Parent: VAS-G000
- Fib priority: 5
- Track: adapters
- Priority: P0
- Bundle: vas/adapters
- Goal: Ensure offline-safe adapters and wallet app bindings can open or act on every exposed surface, deny never_voice/staff_only on client channel, and emit privacy-safe receipts.
- Evidence: vas/surface-binding@1, vas/adapter-deny@1, vas/receipt-redaction@1
- Outputs: wallet_interface/helpers/_voice_app_action_binding.py, adapter modules as needed, docs/voice_app_surface_coverage/SURFACE_BINDINGS.md, unit tests
- Validation: python -m pytest -q wallet_interface/tests tests related to app binding and surface adapters
- Acceptance: Each voice_navigable surface resolves via allowlist; never_voice denies without mutation; receipts redact secrets; fake surface API covers offline e2e.
- Gap task: Add one deny or alias resolution test.
- Refinement: Keep navigation allowlist in lockstep with UI RouteId set.
- Embedding query: NAVIGATION_SURFACE_IDS resolve_navigation_surface open_app_surface deny
- AST query: resolve_navigation_surface InMemoryAppSurfaceApi WalletAppSession

## VAS-G060 Build per-surface request variant lattices

- Status: active
- Parent: VAS-G000
- Fib priority: 5
- Track: variants
- Priority: P0
- Bundle: vas/variants
- Goal: For each exposed surface/action, generate a large structured set of request paraphrases and multi-turn shells covering dialect, slots, noise, and negatives—without embedding executables.
- Evidence: vas/variant-lattice@1, vas/variant-digest@1, vas/variant-floors@1
- Outputs: data/voice_app_surface_coverage/variants/, scripts/voice_app_surface_coverage/build_surface_variant_lattice.py, docs/voice_app_surface_coverage/VARIANT_LATTICE.md
- Validation: python scripts/voice_app_surface_coverage/build_surface_variant_lattice.py --check
- Acceptance: P0 client surfaces meet paraphrase floor (≥200 unique user strings default); P1 ≥50; each variant tagged with surface_id, logical_action or no_action, and axis labels; content ban list enforced.
- Gap task: Add one surface lattice below floor.
- Refinement: Deterministic generation preferred; LLM fill only behind symbolic schema.
- Embedding query: paraphrase lattice calendar what is on my calendar variants STT noise
- AST query: variant_lattice surface_id paraphrase axes

## VAS-G070 Expand slotted DAG sections for reliable surface reachability

- Status: active
- Parent: VAS-G000
- Fib priority: 8
- Track: dag
- Priority: P0
- Bundle: vas/dag
- Goal: Project variant lattices into slotted response DAG edges/exemplars (or additive shards) so GraphRAG/route classification reaches the correct surface under many phrasings.
- Evidence: vas/dag-expansion-receipt@1, vas/route-density@1, vas/action-link-rebuild@1
- Outputs: scripts/build_slotted_response_dag.py usage receipts, docs/phone_dialog_generation shards or rebuild inputs, slotted_response_action_links.json updates, tests
- Validation: python scripts/build_slotted_response_action_links.py --check && python scripts/voice_app_surface_coverage/audit_dag_surface_density.py --check
- Acceptance: Density floors met for P0 surfaces; action links cover new routes; rebuild deterministic; live_agent not expanded without quota justification.
- Gap task: Raise density for the lowest covered P0 surface.
- Refinement: Prefer balanced tool-adjacent growth over mega-handoff dumps.
- Embedding query: slotted_response_dag edge exemplar calendar_event_support app_surface_navigation density
- AST query: build_slotted_response_dag uniqueExemplars routeCounts action_links

## VAS-G080 Prove retrieval reliability across the variant lattice

- Status: active
- Parent: VAS-G000
- Fib priority: 8
- Track: retrieval
- Priority: P0
- Bundle: vas/retrieval
- Goal: Measure and raise offline top-1/top-3 routing accuracy from variants to the intended surface/logical action without authority leakage.
- Evidence: vas/retrieval-reliability@1, vas/confusion-matrix@1, vas/injection-denial@1
- Outputs: scripts/voice_app_surface_coverage/eval_variant_retrieval.py, data/voice_app_surface_coverage/reports/retrieval-reliability.json, tests
- Validation: python scripts/voice_app_surface_coverage/eval_variant_retrieval.py --check
- Acceptance: P0 surfaces meet published hit-rate thresholds; confusion matrix reviewed; adversarial strings cannot invent descriptors; content-only negatives stay no_action.
- Gap task: Fix the worst confused surface pair with exemplars or map rules.
- Refinement: Symbolic route map remains default authority over embeddings.
- Embedding query: retrieval reliability top-1 top-3 confusion matrix action proposal
- AST query: VoiceActionBridge propose ActionProposal action_retrieval

## VAS-G090 Author speech frames for surfaces and actions

- Status: active
- Parent: VAS-G000
- Fib priority: 5
- Track: speech
- Priority: P0
- Bundle: vas/speech
- Goal: Ensure every exposed logical action and P0 navigation surface has slot-safe confirm/success/deny/fail (or shared navigation template) speech frames free of locator content.
- Evidence: vas/speech-frame-coverage@1, vas/speech-banlist@1
- Outputs: docs/phone_dialog_generation/action_speech_frames.jsonl, surface navigation frames artifact, scripts/build_abby_action_speech_frames.py extensions, tests
- Validation: python scripts/build_abby_action_speech_frames.py --check
- Acceptance: Frame inventory covers P0 logical actions and surfaces; banlist clean; digests stable.
- Gap task: Add missing confirm/outcome frame for one action.
- Refinement: Reuse templates with surface_label slots when safe.
- Embedding query: action speech frame confirm success deny fail surface open
- AST query: action_speech_frames frame.action.confirm build_abby_action_speech_frames

## VAS-G100 Regenerate and validate audio for surface × DAG coverage

- Status: active
- Parent: VAS-G000
- Fib priority: 13
- Track: audio
- Priority: P0
- Bundle: vas/audio
- Goal: Stage/precompute IndexTTS (or current Abby TTS pipeline) audio for speech frames and high-priority DAG response texts; Whisper-adjudicate; publish coverage receipt.
- Evidence: vas/audio-stage@1, vas/whisper-gate@1, vas/audio-coverage-receipt@1
- Outputs: scripts/stage_abby_action_audio.py receipts, manifests, data/voice_app_surface_coverage/reports/audio-coverage.json, offline resolver smoke tests
- Validation: python scripts/voice_app_surface_coverage/audit_audio_coverage.py --check
- Acceptance: P0 frames either have validated audio rows or budgeted generate_required entries; Whisper gates documented; no live publish from autonomous workers; offline resolver hits for staged fixtures.
- Gap task: Stage audio for the largest remaining generate_required bucket.
- Refinement: Batch by surface family; human-gate live Space runs.
- Embedding query: IndexTTS Whisper precomputed audio stage abby resolver coverage
- AST query: stage_abby_action_audio PrecomputedVoiceAudioResolver whisper

## VAS-G110 Prove offline e2e reachability of the app surface

- Status: active
- Parent: VAS-G000
- Fib priority: 13
- Track: e2e
- Priority: P0
- Bundle: vas/e2e
- Goal: Offline multi-surface e2e from real variants through proposal, confirm, fake adapter, and spoken outcome—including denies for never_voice.
- Evidence: vas/e2e-surface-matrix@1, vas/e2e-adversarial@1, vas/e2e-calendar-messages-surfaces@1
- Outputs: tests/e2e/voice_app_surface_coverage/, docs/voice_app_surface_coverage/E2E_SURFACE_MATRIX.md
- Validation: python -m pytest -q tests/e2e/voice_app_surface_coverage/
- Acceptance: Every P0 voice_navigable surface opened via ≥N paraphrases; actionable paths confirm→execute; never_voice denied; no network.
- Gap task: Add one failing surface case until green.
- Refinement: Reuse pilot fake stack patterns from voice-action e2e.
- Embedding query: e2e surface matrix paraphrase confirm execute never_voice
- AST query: test_surface_matrix PilotFakeStack read_calendar open_app_surface

## VAS-G120 Operate program enablement and supervisor lanes

- Status: active
- Parent: VAS-G000
- Fib priority: 2
- Track: operations
- Priority: P0
- Bundle: vas/ops
- Goal: Keep four parallel supervisor shards healthy, document enablement flags, and ship an operator checklist for staged audio and product flags.
- Evidence: vas/runbook@1, vas/enablement-checklist@1, vas/lane-health@1
- Outputs: docs/planning/VOICE_APP_SURFACE_COVERAGE_AGENT_SUPERVISOR_RUNBOOK.md, docs/voice_app_surface_coverage/ENABLEMENT_CHECKLIST.md, runtime-policy.json
- Validation: python scripts/validate_voice_app_surface_coverage_plan.py
- Acceptance: Runbook lists submodule pull, fake transport, audio gates, and product flags; checklist maps evidence to goals; refill remains sole-owner.
- Gap task: Fix one runbook gap that blocked a worker.
- Refinement: Prefer control-wrapper scripts over ad-hoc shell.
- Embedding query: supervisor runbook enablement checklist fake adapters audio gate
- AST query: supervisor_control runtime-policy voice-app-surface-coverage
