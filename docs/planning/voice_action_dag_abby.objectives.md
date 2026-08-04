# Voice Action DAG × Abby Dataset Objective Heap

Durable intent heap for connecting the existing Abby slotted response DAG and
precomputed voice library to governed program actions. Companion task board:
`docs/planning/voice_action_dag_abby.todo.md`.

Task completion alone never completes an objective. Objective completion
requires fresh, content-bound evidence for the Abby dataset revision, catalog
digest, adapter identity, and acceptance criterion under review.

Program invariants:

- Board namespace: `voice-action-dag-abby-v1`.
- Content plane (Abby DAG/audio) never embeds executables, URLs, import paths,
  credentials, or raw argv.
- Retrieval may propose only catalog logical actions.
- Execution requires policy + confirmation (or a documented safety-auto path
  for emergency/handoff only) and a deployment-owned binding.
- Fake/local transports in autonomous workers; no live telephony or SMS from
  CI or unsupervised lanes.

## VOICE-ACTION-G000 Deliver Abby voice action DAG integration

- Status: active
- Parent:
- Fib priority: 1
- Track: program
- Priority: P0
- Bundle: voice-action/root
- Goal: Make the existing Abby voice response library and slotted DAG drive governed program actions—live-agent handoff, app navigation, calendar, messaging, and service interactions—without giving retrieval execution authority.
- Evidence: voice-action/program-release-root@1, voice-action/route-coverage-matrix@1, voice-action/e2e-pilot-receipt@1
- Outputs: docs/planning/VOICE_ACTION_DAG_ABBY_INTEGRATION_PLAN.md, docs/planning/voice_action_dag_abby.objectives.md, docs/planning/voice_action_dag_abby.todo.md, docs/planning/voice_action_dag_abby.supervisor.json, scripts/validate_voice_action_dag_abby_plan.py
- Validation: python scripts/validate_voice_action_dag_abby_plan.py
- Acceptance: All direct children have criterion-level evidence; every tool-adjacent route is classified; pilot actions execute only through admitted adapters; Abby audio continuity exists for confirmation and outcomes; live_agent never claims unverified transfer success.
- Gap task: Refill the highest-priority uncovered child criterion with one bounded task and an explicit evidence contract.
- Refinement: Keep content, catalog, retrieval, adapters, audio, handoff, and e2e in independent lanes.
- Embedding query: abby voice action DAG slotted response live agent calendar messages handoff
- AST query: process_voice_turn ActionProposal VoiceActionBridge slotted_response_dag

## VOICE-ACTION-G010 Inventory baseline and freeze integration doctrine

- Status: active
- Parent: VOICE-ACTION-G000
- Fib priority: 2
- Track: architecture
- Priority: P0
- Bundle: voice-action/doctrine
- Goal: Inventory current Abby DAG routes, audio resolver coverage, action_runtime surface, UI tools, service actions, and handoff gaps; freeze dual-plane doctrine and package ownership for this integration.
- Evidence: voice-action/baseline-inventory@1, voice-action/doctrine-adr@1, voice-action/gap-matrix@1
- Outputs: docs/voice_action_dag/BASELINE_INVENTORY.md, docs/voice_action_dag/INTEGRATION_DOCTRINE.md, data/voice_action_dag/baseline/route-gap-matrix.json
- Validation: python scripts/voice_action_dag/audit_baseline.py --check
- Acceptance: Route census matches slotted DAG summary; each route classified as content-only, proposal-eligible, or safety-overlay; package boundaries forbid content→executable edges; gap matrix lists missing catalog, adapter, audio, and e2e items.
- Gap task: Add one missing inventory symbol, route classification, or ownership rule.
- Refinement: Prefer AST and file digests over narrative claims.
- Embedding query: inventory abby route gap matrix doctrine dual plane content authority
- AST query: build_slotted_response_dag ActionCatalog VoiceActionBridge toolExecutor

## VOICE-ACTION-G020 Bind Abby content routes to logical actions

- Status: active
- Parent: VOICE-ACTION-G000
- Fib priority: 3
- Track: content-links
- Priority: P0
- Bundle: voice-action/content
- Goal: Extend the Abby slotted DAG / GraphRAG content model with optional logical-action links, confirmation frames, and outcome frames without embedding executables in content.
- Evidence: voice-action/content-link-schema@1, voice-action/dag-rebuild-receipt@1, voice-action/migration-vectors@1
- Outputs: ipfs_datasets_py/ipfs_datasets_py/voice/action_links.py, docs/phone_dialog_generation/slotted_response_action_links.json, scripts/build_slotted_response_action_links.py, ipfs_datasets_py/tests/unit/voice/test_action_links.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/voice/test_action_links.py && python scripts/build_slotted_response_action_links.py --check
- Acceptance: All 12 routes have explicit mapping or `no_action`; content artifacts reject command/argv/url/import fields; rebuild is deterministic; links reference only logical_action_ids from the catalog namespace.
- Gap task: Add one route mapping, schema check, or rebuild invariant.
- Refinement: Keep generation scripts pure and offline.
- Embedding query: slotted response action link logical_action confirmation frame outcome frame
- AST query: slotted_response_dag uniqueExemplars responseFrames route

## VOICE-ACTION-G030 Publish the deployment-owned action catalog for 211-AI pilot actions

- Status: active
- Parent: VOICE-ACTION-G000
- Fib priority: 3
- Track: catalog
- Priority: P0
- Bundle: voice-action/catalog
- Goal: Define and pin reviewed ActionDescriptors for live-agent handoff, app surfaces, calendar, messaging, service interaction, and safety escalation with risk, confirm, and channel constraints.
- Evidence: voice-action/catalog-digest@1, voice-action/descriptor-golden@1, voice-action/catalog-reject-malformed@1
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/catalog_211ai.py, data/voice_action_dag/catalog/211ai-pilot-v1.json, ipfs_accelerate_py/test/test_action_catalog_211ai.py
- Validation: python -m pytest -q ipfs_accelerate_py/test/test_action_catalog_211ai.py
- Acceptance: Pilot descriptors cover the target logical actions; unknown ids fail closed; descriptors contain no raw executable locators; digest is stable under key reordering.
- Gap task: Add or correct one descriptor field or rejection test.
- Refinement: Catalog is deployment-owned and versioned independently of Abby content CIDs.
- Embedding query: action catalog descriptor live agent calendar messaging risk confirmation
- AST query: ActionDescriptor ActionCatalog RiskClass SideEffectClass

## VOICE-ACTION-G040 Expand fail-closed policy for pilot risk classes

- Status: active
- Parent: VOICE-ACTION-G000
- Fib priority: 5
- Track: policy
- Priority: P0
- Bundle: voice-action/policy
- Goal: Extend policy so read actions require confirmation, write actions require confirmation plus authenticated tenant session, human handoff follows handoff policy, and safety overlay can force escalate without tool smuggling.
- Evidence: voice-action/policy-matrix@1, voice-action/confused-deputy@1, voice-action/confirm-gate@1
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/policy_pilot.py, docs/voice_action_dag/POLICY_MATRIX.md, ipfs_accelerate_py/test/test_action_policy_pilot.py
- Validation: python -m pytest -q ipfs_accelerate_py/test/test_action_policy_pilot.py
- Acceptance: Default deny remains; grants cannot widen descriptor risk; write without auth denies; retrieval confidence never upgrades decision; safety escalation cannot invoke arbitrary adapters.
- Gap task: Add the highest-risk missing predicate test.
- Refinement: Keep policy pure and free of I/O.
- Embedding query: fail closed policy confirmation authentication handoff safety escalation
- AST query: FailClosedPolicy ActionDecisionKind grant decide

## VOICE-ACTION-G050 Retrieve action proposals from Abby GraphRAG and the slotted DAG

- Status: active
- Parent: VOICE-ACTION-G000
- Fib priority: 5
- Track: retrieval
- Priority: P0
- Bundle: voice-action/retrieval
- Goal: Make GraphRAG and route classification emit ActionProposal candidates alongside grounded response plans using Abby evidence, without authority.
- Evidence: voice-action/proposal-retrieval@1, voice-action/authority-noninterference@1, voice-action/route-proposal-samples@1
- Outputs: ipfs_datasets_py/ipfs_datasets_py/voice/action_retrieval.py, ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/voice_bridge.py, ipfs_datasets_py/tests/unit/voice/test_action_retrieval.py
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/voice/test_action_retrieval.py ipfs_accelerate_py/test/test_action_cli_adapter.py
- Acceptance: Sampling each tool-adjacent route yields a catalog-valid proposal or explicit no_action; injection of command-like text cannot create new descriptors; proposals include route, template, and evidence digests only.
- Gap task: Add one retrieval fixture or injection denial.
- Refinement: Symbolic route map is default; embeddings optional and non-authoritative.
- Embedding query: GraphRAG action proposal slotted route evidence noninterference
- AST query: GraphRAGVoiceTemplateProvider propose_from_voice_route ActionProposal

## VOICE-ACTION-G060 Attach proposals to voice_router and wallet receipts end to end

- Status: active
- Parent: VOICE-ACTION-G000
- Fib priority: 5
- Track: voice-integration
- Priority: P0
- Bundle: voice-action/voice-path
- Goal: Ensure process_voice_turn / process_telephone_turn / wallet proxy always surface action proposals when eligible and never auto-execute without dual gates.
- Evidence: voice-action/router-attach@1, voice-action/wallet-surface@1, voice-action/telephone-surface@1
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/voice_router.py, wallet_interface/helpers/_voice_action_surface.py, wallet_interface/routes/ai_router.py, tests covering attach paths
- Validation: python -m pytest -q wallet_interface/tests/test_voice_router_adapter.py ipfs_accelerate_py/test/test_voice_router_contracts.py
- Acceptance: Completed turns with tool routes include action.proposal/decision; confirm without execute flag does not run adapters; telephone turns preserve privacy-safe handoff metadata.
- Gap task: Fix one missing attach path or receipt field.
- Refinement: Additive wire fields only; legacy clients ignore unknown keys.
- Embedding query: voice router wallet action surface confirm_action telephone handoff metadata
- AST query: process_voice_turn process_wallet_voice_turn attach_action_surface process_telephone_turn

## VOICE-ACTION-G070 Implement app-surface and wallet-document adapters

- Status: active
- Parent: VOICE-ACTION-G000
- Fib priority: 8
- Track: adapters-app
- Priority: P0
- Bundle: voice-action/adapters-app
- Goal: Bind open_app_surface and open_wallet_documents to the existing agent navigation/document tools through a server-mediated or UI-mediated admitted adapter with receipts.
- Evidence: voice-action/app-surface-receipt@1, voice-action/wallet-docs-receipt@1, voice-action/app-adapter-deny@1
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/adapters/app_tool.py, wallet_interface bindings, tests
- Validation: python -m pytest -q ipfs_accelerate_py/test/test_action_app_tool_adapter.py
- Acceptance: Navigation and document open succeed only after permit; unknown surfaces deny; no shell/CLI escape; receipts redact private paths.
- Gap task: Add one surface allowlist entry test or denial case.
- Refinement: Prefer reusing navigationTools/uploadTools contracts over new side channels.
- Embedding query: app surface navigation wallet documents adapter receipt allowlist
- AST query: navigationTools uploadTools surfaceRegistry ActionReceipt

## VOICE-ACTION-G080 Implement calendar read and reminder adapters

- Status: active
- Parent: VOICE-ACTION-G000
- Fib priority: 8
- Track: adapters-calendar
- Priority: P0
- Bundle: voice-action/adapters-calendar
- Goal: Enable voice-proposed calendar_event_support flows to read schedule context and create reminders only with confirmation and authenticated session scope.
- Evidence: voice-action/calendar-read@1, voice-action/calendar-write-confirm@1, voice-action/calendar-tenant-isolation@1
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/adapters/calendar.py, wallet calendar service binding, tests
- Validation: python -m pytest -q ipfs_accelerate_py/test/test_action_calendar_adapter.py
- Acceptance: Read returns redacted event summaries; write requires auth+confirm; cross-tenant access denies; voice library route samples produce proposals that bind to these descriptors.
- Gap task: Add one isolation or confirmation test.
- Refinement: No raw ICS injection from model text; structured slots only.
- Embedding query: calendar read create reminder voice confirmation tenant isolation
- AST query: CalendarScreen create_calendar_reminder read_calendar ActionProposal

## VOICE-ACTION-G090 Implement provider messaging adapters

- Status: active
- Parent: VOICE-ACTION-G000
- Fib priority: 8
- Track: adapters-messages
- Priority: P0
- Bundle: voice-action/adapters-messages
- Goal: Support reading client/provider messages and leaving a message with a service provider through admitted adapters driven by provider_contact_support proposals.
- Evidence: voice-action/message-read@1, voice-action/message-leave@1, voice-action/message-policy@1
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/adapters/messaging.py, wallet messaging bindings, tests
- Validation: python -m pytest -q ipfs_accelerate_py/test/test_action_messaging_adapter.py
- Acceptance: Leave-message requires confirm+auth; message body is size-bounded and redacted in receipts; read cannot dump unrelated tenants; spoken scripts from Abby remain content-only.
- Gap task: Add one redaction or quota test.
- Refinement: Never treat spoken phone numbers as executable SMS sends without a separate descriptor.
- Embedding query: provider message leave read inbox voice adapter redaction
- AST query: leave_provider_message read_provider_messages provider_contact_support

## VOICE-ACTION-G100 Implement service interaction and callback adapters

- Status: active
- Parent: VOICE-ACTION-G000
- Fib priority: 8
- Track: adapters-service
- Priority: P0
- Bundle: voice-action/adapters-service
- Goal: Connect service_interaction_support routes to serviceActionService / serviceInteractionService capabilities for callback requests and interaction logging with receipts.
- Evidence: voice-action/service-callback@1, voice-action/service-interaction-receipt@1
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/adapters/service_interaction.py, parent service bindings, tests
- Validation: python -m pytest -q ipfs_accelerate_py/test/test_action_service_interaction_adapter.py
- Acceptance: Callback scheduling is idempotent under proposal digest; unconfirmed proposals never mutate; service IDs must come from grounded evidence, not free text alone.
- Gap task: Add one idempotency or grounding requirement test.
- Refinement: Reuse existing service interaction models.
- Embedding query: service interaction callback intake follow-up grounded service id
- AST query: serviceActionService serviceInteractionService service_interaction_support

## VOICE-ACTION-G110 Implement live-agent handoff and safety escalation

- Status: active
- Parent: VOICE-ACTION-G000
- Fib priority: 8
- Track: adapters-handoff
- Priority: P0
- Bundle: voice-action/adapters-handoff
- Goal: Turn live_agent and safety_guardrail_support into receipted human handoff / emergency overlay flows that never claim completed transfer without provider confirmation.
- Evidence: voice-action/handoff-request@1, voice-action/transfer-unknown@1, voice-action/safety-overlay@1
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/adapters/human_handoff.py, telephony bridge hooks, tests
- Validation: python -m pytest -q ipfs_accelerate_py/test/test_action_human_handoff_adapter.py
- Acceptance: HandoffRequest is durable; telephony adapter returns accepted/started/unknown/succeeded distinctly; spoken Abby live_agent frames remain advisory unless receipt status is succeeded; safety overlay cannot open arbitrary tools.
- Gap task: Add one outcome_unknown or spoofed-callback denial test.
- Refinement: Prefer queueing over false warmth.
- Embedding query: live agent handoff warm transfer safety escalation outcome unknown
- AST query: process_telephone_turn HandoffRequest live_agent safety_guardrail_support

## VOICE-ACTION-G120 Extend Abby audio library for action confirmation and outcomes

- Status: active
- Parent: VOICE-ACTION-G000
- Fib priority: 8
- Track: abby-audio
- Priority: P0
- Bundle: voice-action/audio
- Goal: Ensure pilot logical actions have library-backed confirmation and outcome utterances with precomputed audio rows validated by the Abby pipeline.
- Evidence: voice-action/audio-coverage@1, voice-action/whisper-validation@1, voice-action/resolver-hits@1
- Outputs: scripts/build_abby_action_speech_frames.py, docs/phone_dialog_generation/action_speech_frames.jsonl, resolver integration, tests
- Validation: python -m pytest -q tests/voice/test_abby_action_speech_frames.py
- Acceptance: Each pilot action has confirm/success/deny/fail text frames; audio rows exist or are explicitly marked generate-required; resolver exact-match works offline for staged fixtures.
- Gap task: Add missing frame for one action/status pair.
- Refinement: Reuse IndexTTS + Whisper gates; no ad-hoc TTS in request path.
- Embedding query: abby precomputed audio confirmation outcome whisper resolver
- AST query: PrecomputedVoiceAudioResolver abby_tts_precomputed_audio_resolver spoken_text

## VOICE-ACTION-G130 Ship UI confirmation and action status in voice chat

- Status: active
- Parent: VOICE-ACTION-G000
- Fib priority: 5
- Track: ui
- Priority: P0
- Bundle: voice-action/ui
- Goal: Complete accessible UI for viewing proposed actions, confirming, dismissing, and showing receipt status in AgentAudioChatSurface and agent chat.
- Evidence: voice-action/ui-confirm@1, voice-action/ui-a11y@1, voice-action/ui-no-autoexec@1
- Outputs: wallet_interface/ui voice action components/tests
- Validation: npm --prefix wallet_interface/ui test -- tests/agent-voice-router.spec.ts
- Acceptance: Confirm button only appears for confirm decisions; dismiss clears pending; executed/failed states are announced; no client-side adapter execution bypassing server gates.
- Gap task: Add one a11y or status rendering test.
- Refinement: Keep dual-gate server enforcement even if UI is compromised.
- Embedding query: voice ui confirm action surface accessibility receipt status
- AST query: AgentAudioChatSurface confirmPendingVoiceAction voiceActionNeedsConfirmation

## VOICE-ACTION-G140 Prove end-to-end offline pilot with Abby dataset samples

- Status: active
- Parent: VOICE-ACTION-G000
- Fib priority: 13
- Track: e2e
- Priority: P0
- Bundle: voice-action/e2e
- Goal: Run offline multi-route e2e using slotted DAG exemplars, fake adapters, and staged Abby audio to prove proposal→confirm→execute→speak for the pilot set.
- Evidence: voice-action/e2e-matrix@1, voice-action/e2e-live-agent@1, voice-action/e2e-calendar-messages@1
- Outputs: tests/e2e/voice_action_dag/test_abby_pilot_matrix.py, docs/voice_action_dag/E2E_PILOT.md
- Validation: python -m pytest -q tests/e2e/voice_action_dag/test_abby_pilot_matrix.py
- Acceptance: Matrix covers all 12 routes; tool-adjacent routes exercise adapters under confirm; content-only routes assert no_action; live_agent asserts handoff receipt semantics; no network.
- Gap task: Add one failing route fixture until green.
- Refinement: Prefer deterministic fakes over live HF/Space calls.
- Embedding query: e2e abby pilot matrix route confirm execute handoff calendar messages
- AST query: slotted_response_dag process_voice_turn ActionExecutor

## VOICE-ACTION-G150 Operate supervisor lanes and protected plan namespace

- Status: active
- Parent: VOICE-ACTION-G000
- Fib priority: 2
- Track: operations
- Priority: P0
- Bundle: voice-action/operations
- Goal: Bootstrap agent_supervisor control for this board with four parallel shards, protected plan paths, and fail-closed preflight.
- Evidence: voice-action/supervisor-preflight@1, voice-action/lane-start@1, voice-action/protected-paths@1
- Outputs: docs/planning/voice_action_dag_abby.supervisor.json, scripts/validate_voice_action_dag_abby_plan.py, docs/voice_action_dag/AGENT_SUPERVISOR_STATE.md
- Validation: python scripts/validate_voice_action_dag_abby_plan.py
- Acceptance: Preflight parses goals/tasks without cycles; merge target rules are explicit; protected paths include plan artifacts; workers cannot edit the plan board.
- Gap task: Repair one preflight invariant.
- Refinement: Refill disabled until bootstrap task completes.
- Embedding query: agent supervisor lanes protected paths voice action board preflight
- AST query: parse_goal_heap parse_task_file materialize_task_dependency_dag
