# Voice Action DAG × Abby Dataset Task Board

Executable projection of `voice_action_dag_abby.objectives.md` for
`ipfs_accelerate_py.agent_supervisor`.

Program invariants:

- Board namespace is `voice-action-dag-abby-v1`; task identities are stable.
- Abby content never embeds executables, URLs, import paths, credentials, or argv.
- Retrieval may propose catalog logical actions only.
- Mutations fail closed without policy, confirmation, and (when required) auth.
- Autonomous workers use fake/local transports only.
- Symbolic checks precede bounded LLM repair.
- Completion requires current-tree validation evidence.

## VOICE-ACTION-001 Bootstrap supervisor control and protected plan namespace

- Status: completed
- Completion: manual
- Priority: P0
- Track: operations
- Depends on:
- Goal id: VOICE-ACTION-G150
- Outputs: docs/voice_action_dag/AGENT_SUPERVISOR_STATE.md, docs/voice_action_dag/runtime-policy.json, scripts/voice_action_dag/supervisor_control.py, tests/voice_action_dag/test_supervisor_control.py
- Validation: python scripts/validate_voice_action_dag_abby_plan.py && python scripts/voice_action_dag/supervisor_control.py validate-config
- Board namespace: voice-action-dag-abby-v1
- Bundle: voice-action/operations
- Parallel lane: wave-00-control
- Resource class: cpu-small
- Predicted files: docs/voice_action_dag/AGENT_SUPERVISOR_STATE.md, docs/voice_action_dag/runtime-policy.json, scripts/voice_action_dag/supervisor_control.py, tests/voice_action_dag/test_supervisor_control.py
- Conflict policy: Exclusive owner of supervisor launch policy and protected-path configuration for this board.
- Symbolic first: true
- LLM context budget bytes: 12288
- Acceptance: Preflight validates objectives and this board; merge target `agent/voice-action-dag-abby` is created only from the pinned base; four shards start with one refill owner; plan files are protected; publication and credentials remain disabled by default.

## VOICE-ACTION-002 Inventory Abby DAG, audio, action_runtime, UI tools, and handoff gaps

- Status: completed
- Completion: manual
- Priority: P0
- Track: architecture
- Depends on: VOICE-ACTION-001
- Goal id: VOICE-ACTION-G010
- Outputs: scripts/voice_action_dag/audit_baseline.py, data/voice_action_dag/baseline/component-inventory.json, data/voice_action_dag/baseline/route-gap-matrix.json, docs/voice_action_dag/BASELINE_INVENTORY.md
- Validation: python scripts/voice_action_dag/audit_baseline.py --check
- Board namespace: voice-action-dag-abby-v1
- Bundle: voice-action/doctrine
- Parallel lane: wave-01-inventory
- Resource class: io-medium
- Predicted files: scripts/voice_action_dag/audit_baseline.py, data/voice_action_dag/baseline/component-inventory.json, data/voice_action_dag/baseline/route-gap-matrix.json, docs/voice_action_dag/BASELINE_INVENTORY.md
- Conflict policy: Owns baseline reports only; must not modify runtime modules.
- Symbolic first: true
- LLM context budget bytes: 16384
- Acceptance: Route census matches slotted DAG; each route is content-only, proposal-eligible, or safety-overlay; inventory binds repo revisions and AST symbols for voice_router, action_runtime, GraphRAG, UI tools, service actions, and handoff.

## VOICE-ACTION-003 Freeze dual-plane integration doctrine and ownership map

- Status: completed
- Completion: manual
- Priority: P0
- Track: architecture
- Depends on: VOICE-ACTION-002
- Goal id: VOICE-ACTION-G010
- Outputs: docs/voice_action_dag/INTEGRATION_DOCTRINE.md, docs/voice_action_dag/schemas/assurance-verdict-v1.schema.json, tests/voice_action_dag/test_doctrine_invariants.py
- Validation: python -m pytest -q tests/voice_action_dag/test_doctrine_invariants.py
- Board namespace: voice-action-dag-abby-v1
- Bundle: voice-action/doctrine
- Parallel lane: wave-01-doctrine
- Resource class: cpu-small
- Predicted files: docs/voice_action_dag/INTEGRATION_DOCTRINE.md, docs/voice_action_dag/schemas/assurance-verdict-v1.schema.json, tests/voice_action_dag/test_doctrine_invariants.py
- Conflict policy: Owns normative doctrine vocabulary for this program.
- Symbolic first: true
- LLM context budget bytes: 16384
- Acceptance: Doctrine states content vs authority planes; lists package ownership; forbids content executables; defines confirmation and handoff truthfulness rules; tests encode non-negotiable invariants as assertions.

## VOICE-ACTION-004 Define Abby content→logical-action link schema

- Status: completed
- Completion: manual
- Priority: P0
- Track: content-links
- Depends on: VOICE-ACTION-003
- Goal id: VOICE-ACTION-G020
- Outputs: ipfs_datasets_py/ipfs_datasets_py/voice/action_links.py, ipfs_datasets_py/tests/unit/voice/test_action_links.py, docs/voice_action_dag/schemas/action-link-v1.md
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/voice/test_action_links.py
- Board namespace: voice-action-dag-abby-v1
- Bundle: voice-action/content
- Parallel lane: wave-02-content-schema
- Resource class: cpu-medium
- Predicted files: ipfs_datasets_py/ipfs_datasets_py/voice/action_links.py, ipfs_datasets_py/tests/unit/voice/test_action_links.py, docs/voice_action_dag/schemas/action-link-v1.md
- Conflict policy: Owns action-link schema; consumers extend via versions.
- Symbolic first: true
- LLM context budget bytes: 20480
- Acceptance: Schema supports route→logical_action, confirmation_frame_id, outcome_frame_ids; rejects command/argv/url/import/env fields; golden vectors are deterministic.

## VOICE-ACTION-005 Build deterministic slotted DAG action-link projection

- Status: completed
- Completion: manual
- Priority: P0
- Track: content-links
- Depends on: VOICE-ACTION-004
- Goal id: VOICE-ACTION-G020
- Outputs: scripts/build_slotted_response_action_links.py, docs/phone_dialog_generation/slotted_response_action_links.json, tests/test_build_slotted_response_action_links.py
- Validation: python scripts/build_slotted_response_action_links.py --check && python -m pytest -q tests/test_build_slotted_response_action_links.py
- Board namespace: voice-action-dag-abby-v1
- Bundle: voice-action/content
- Parallel lane: wave-02-content-build
- Resource class: cpu-medium
- Predicted files: scripts/build_slotted_response_action_links.py, docs/phone_dialog_generation/slotted_response_action_links.json, tests/test_build_slotted_response_action_links.py
- Conflict policy: Owns generation of action-link projection only.
- Symbolic first: true
- LLM context budget bytes: 16384
- Acceptance: All 12 routes appear; tool-adjacent routes map to pilot logical actions; content-only routes map to no_action; rebuild is byte-stable given fixed inputs.

## VOICE-ACTION-006 Publish 211-AI pilot ActionDescriptor catalog

- Status: completed
- Completion: manual
- Priority: P0
- Track: catalog
- Depends on: VOICE-ACTION-003
- Goal id: VOICE-ACTION-G030
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/catalog_211ai.py, data/voice_action_dag/catalog/211ai-pilot-v1.json, ipfs_accelerate_py/test/test_action_catalog_211ai.py
- Validation: python -m pytest -q ipfs_accelerate_py/test/test_action_catalog_211ai.py
- Board namespace: voice-action-dag-abby-v1
- Bundle: voice-action/catalog
- Parallel lane: wave-02-catalog
- Resource class: cpu-small
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/catalog_211ai.py, data/voice_action_dag/catalog/211ai-pilot-v1.json, ipfs_accelerate_py/test/test_action_catalog_211ai.py
- Conflict policy: Exclusive owner of pilot catalog identifiers for this board.
- Symbolic first: true
- LLM context budget bytes: 16384
- Acceptance: Descriptors exist for handoff_live_agent, open_app_surface, open_wallet_documents, read_calendar, create_calendar_reminder, read_provider_messages, leave_provider_message, open_service_detail, schedule_service_callback, escalate_safety; digest stable; no executable locators in JSON.

## VOICE-ACTION-007 Expand policy matrix for read/write/human/safety classes

- Status: completed
- Completion: manual
- Priority: P0
- Track: policy
- Depends on: VOICE-ACTION-006
- Goal id: VOICE-ACTION-G040
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/policy_pilot.py, docs/voice_action_dag/POLICY_MATRIX.md, ipfs_accelerate_py/test/test_action_policy_pilot.py
- Validation: python -m pytest -q ipfs_accelerate_py/test/test_action_policy_pilot.py
- Board namespace: voice-action-dag-abby-v1
- Bundle: voice-action/policy
- Parallel lane: wave-02-policy
- Resource class: cpu-small
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/policy_pilot.py, docs/voice_action_dag/POLICY_MATRIX.md, ipfs_accelerate_py/test/test_action_policy_pilot.py
- Conflict policy: Owns pilot policy predicates; adapters consume decisions only.
- Symbolic first: true
- LLM context budget bytes: 16384
- Acceptance: Tests prove default deny, confirm for read, auth+confirm for write, handoff policy path, safety overlay cannot widen to arbitrary descriptors, and confidence cannot upgrade authority.

## VOICE-ACTION-008 Implement Abby-aware action proposal retrieval

- Status: completed
- Completion: manual
- Priority: P0
- Track: retrieval
- Depends on: VOICE-ACTION-005, VOICE-ACTION-006
- Goal id: VOICE-ACTION-G050
- Outputs: ipfs_datasets_py/ipfs_datasets_py/voice/action_retrieval.py, ipfs_datasets_py/tests/unit/voice/test_action_retrieval.py, docs/voice_action_dag/RETRIEVAL.md
- Validation: python -m pytest -q ipfs_datasets_py/tests/unit/voice/test_action_retrieval.py
- Board namespace: voice-action-dag-abby-v1
- Bundle: voice-action/retrieval
- Parallel lane: wave-03-retrieval
- Resource class: cpu-medium
- Predicted files: ipfs_datasets_py/ipfs_datasets_py/voice/action_retrieval.py, ipfs_datasets_py/tests/unit/voice/test_action_retrieval.py, docs/voice_action_dag/RETRIEVAL.md
- Conflict policy: Owns retrieval projection; does not execute adapters.
- Symbolic first: true
- LLM context budget bytes: 24576
- Acceptance: Route samples from slotted DAG produce catalog-valid proposals or no_action; adversarial transcripts cannot invent descriptors; evidence and template ids are attached.

## VOICE-ACTION-009 Upgrade voice_bridge to catalog-validated multi-route proposals

- Status: completed
- Completion: manual
- Priority: P0
- Track: retrieval
- Depends on: VOICE-ACTION-008
- Goal id: VOICE-ACTION-G050
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/voice_bridge.py, ipfs_accelerate_py/test/test_voice_action_bridge_routes.py
- Validation: python -m pytest -q ipfs_accelerate_py/test/test_voice_action_bridge_routes.py
- Board namespace: voice-action-dag-abby-v1
- Bundle: voice-action/retrieval
- Parallel lane: wave-03-bridge
- Resource class: cpu-small
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/voice_bridge.py, ipfs_accelerate_py/test/test_voice_action_bridge_routes.py
- Conflict policy: Owns voice_bridge mapping tables and proposal factory.
- Symbolic first: true
- LLM context budget bytes: 12288
- Acceptance: All 12 routes classified; tool-adjacent routes require catalog presence when require_catalog_entry=true; no executable arguments accepted.

## VOICE-ACTION-010 Attach proposals on process_voice_turn provenance metadata

- Status: todo
- Completion: manual
- Priority: P0
- Track: voice-integration
- Depends on: VOICE-ACTION-009, VOICE-ACTION-007
- Goal id: VOICE-ACTION-G060
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/voice_router.py, ipfs_accelerate_py/test/test_voice_router_action_attach.py
- Validation: python -m pytest -q ipfs_accelerate_py/test/test_voice_router_action_attach.py
- Board namespace: voice-action-dag-abby-v1
- Bundle: voice-action/voice-path
- Parallel lane: wave-03-router
- Resource class: cpu-medium
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/voice_router.py, ipfs_accelerate_py/test/test_voice_router_action_attach.py
- Conflict policy: Additive attach only; preserve existing STT/TTS contracts.
- Symbolic first: true
- LLM context budget bytes: 24576
- Acceptance: When template metadata includes route, result provenance metadata exposes action candidates; no adapter runs inside process_voice_turn.

## VOICE-ACTION-011 Harden wallet action surface for multi-descriptor pilot catalog

- Status: completed
- Completion: manual
- Priority: P0
- Track: voice-integration
- Depends on: VOICE-ACTION-006, VOICE-ACTION-007
- Goal id: VOICE-ACTION-G060
- Outputs: wallet_interface/helpers/_voice_action_surface.py, wallet_interface/tests/test_voice_router_adapter.py
- Validation: python -m pytest -q wallet_interface/tests/test_voice_router_adapter.py
- Board namespace: voice-action-dag-abby-v1
- Bundle: voice-action/voice-path
- Parallel lane: wave-03-wallet
- Resource class: cpu-small
- Predicted files: wallet_interface/helpers/_voice_action_surface.py, wallet_interface/tests/test_voice_router_adapter.py
- Conflict policy: Owns wallet action surface wiring; no UI redesign beyond receipt fields.
- Symbolic first: true
- LLM context budget bytes: 16384
- Acceptance: Default stack loads pilot catalog; confirm without execute flag never runs; all pilot routes covered by unit cases.

## VOICE-ACTION-012 Pass route from GraphRAG/template metadata through AI infer API

- Status: todo
- Completion: manual
- Priority: P0
- Track: voice-integration
- Depends on: VOICE-ACTION-010, VOICE-ACTION-011
- Goal id: VOICE-ACTION-G060
- Outputs: wallet_interface/routes/ai_router.py, wallet_interface/tests/test_ai_router_voice_action.py
- Validation: python -m pytest -q wallet_interface/tests/test_ai_router_voice_action.py
- Board namespace: voice-action-dag-abby-v1
- Bundle: voice-action/voice-path
- Parallel lane: wave-03-api
- Resource class: cpu-small
- Predicted files: wallet_interface/routes/ai_router.py, wallet_interface/tests/test_ai_router_voice_action.py
- Conflict policy: Owns infer form fields for route/confirm only.
- Symbolic first: true
- LLM context budget bytes: 12288
- Acceptance: Unified router path returns action surface; legacy path unchanged when flag off; confirm_action dual-gate preserved.

## VOICE-ACTION-013 Implement app tool adapter for navigation and wallet documents

- Status: completed
- Completion: manual
- Priority: P0
- Track: adapters-app
- Depends on: VOICE-ACTION-006, VOICE-ACTION-007
- Goal id: VOICE-ACTION-G070
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/adapters/app_tool.py, ipfs_accelerate_py/test/test_action_app_tool_adapter.py, docs/voice_action_dag/APP_TOOL_BINDINGS.md
- Validation: python -m pytest -q ipfs_accelerate_py/test/test_action_app_tool_adapter.py
- Board namespace: voice-action-dag-abby-v1
- Bundle: voice-action/adapters-app
- Parallel lane: wave-04-app
- Resource class: cpu-medium
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/adapters/app_tool.py, ipfs_accelerate_py/test/test_action_app_tool_adapter.py, docs/voice_action_dag/APP_TOOL_BINDINGS.md
- Conflict policy: Exclusive owner of app_tool adapter module.
- Symbolic first: true
- LLM context budget bytes: 20480
- Acceptance: open_app_surface and open_wallet_documents succeed under permit with fake surface API; unknown surface denies; receipts omit private filesystem paths; no shell.

## VOICE-ACTION-014 Wire UI navigation/document tools as admitted backends for app adapter

- Status: todo
- Completion: manual
- Priority: P0
- Track: adapters-app
- Depends on: VOICE-ACTION-013
- Goal id: VOICE-ACTION-G070
- Outputs: wallet_interface/helpers/_voice_app_action_binding.py, wallet_interface/tests/test_voice_app_action_binding.py
- Validation: python -m pytest -q wallet_interface/tests/test_voice_app_action_binding.py
- Board namespace: voice-action-dag-abby-v1
- Bundle: voice-action/adapters-app
- Parallel lane: wave-04-app-ui
- Resource class: cpu-medium
- Predicted files: wallet_interface/helpers/_voice_app_action_binding.py, wallet_interface/tests/test_voice_app_action_binding.py
- Conflict policy: Binding layer only; do not rewrite navigationTools contracts.
- Symbolic first: true
- LLM context budget bytes: 16384
- Acceptance: Allowlisted surfaces from navigationTools/registry can be opened after server permit; non-allowlisted routes fail closed.

## VOICE-ACTION-015 Implement calendar adapter (read + create reminder)

- Status: todo
- Completion: manual
- Priority: P0
- Track: adapters-calendar
- Depends on: VOICE-ACTION-006, VOICE-ACTION-007
- Goal id: VOICE-ACTION-G080
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/adapters/calendar.py, ipfs_accelerate_py/test/test_action_calendar_adapter.py, docs/voice_action_dag/CALENDAR_BINDINGS.md
- Validation: python -m pytest -q ipfs_accelerate_py/test/test_action_calendar_adapter.py
- Board namespace: voice-action-dag-abby-v1
- Bundle: voice-action/adapters-calendar
- Parallel lane: wave-04-calendar
- Resource class: cpu-medium
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/adapters/calendar.py, ipfs_accelerate_py/test/test_action_calendar_adapter.py, docs/voice_action_dag/CALENDAR_BINDINGS.md
- Conflict policy: Exclusive owner of calendar adapter module.
- Symbolic first: true
- LLM context budget bytes: 20480
- Acceptance: read_calendar returns redacted summaries; create_calendar_reminder requires auth+confirm; tenant isolation tests pass; structured slots only.

## VOICE-ACTION-016 Bind calendar adapter to wallet calendar service with fake transport

- Status: todo
- Completion: manual
- Priority: P0
- Track: adapters-calendar
- Depends on: VOICE-ACTION-015
- Goal id: VOICE-ACTION-G080
- Outputs: wallet_interface/helpers/_voice_calendar_action_binding.py, wallet_interface/tests/test_voice_calendar_action_binding.py
- Validation: python -m pytest -q wallet_interface/tests/test_voice_calendar_action_binding.py
- Board namespace: voice-action-dag-abby-v1
- Bundle: voice-action/adapters-calendar
- Parallel lane: wave-04-calendar-ui
- Resource class: cpu-medium
- Predicted files: wallet_interface/helpers/_voice_calendar_action_binding.py, wallet_interface/tests/test_voice_calendar_action_binding.py
- Conflict policy: Binding only; calendar UI feature code remains authoritative for storage schema.
- Symbolic first: true
- LLM context budget bytes: 16384
- Acceptance: Offline fake calendar store supports read/create under permit; unauthenticated write denies.

## VOICE-ACTION-017 Implement messaging adapter (read + leave provider message)

- Status: completed
- Completion: manual
- Priority: P0
- Track: adapters-messages
- Depends on: VOICE-ACTION-006, VOICE-ACTION-007
- Goal id: VOICE-ACTION-G090
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/adapters/messaging.py, ipfs_accelerate_py/test/test_action_messaging_adapter.py, docs/voice_action_dag/MESSAGING_BINDINGS.md
- Validation: python -m pytest -q ipfs_accelerate_py/test/test_action_messaging_adapter.py
- Board namespace: voice-action-dag-abby-v1
- Bundle: voice-action/adapters-messages
- Parallel lane: wave-04-messages
- Resource class: cpu-medium
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/adapters/messaging.py, ipfs_accelerate_py/test/test_action_messaging_adapter.py, docs/voice_action_dag/MESSAGING_BINDINGS.md
- Conflict policy: Exclusive owner of messaging adapter module.
- Symbolic first: true
- LLM context budget bytes: 20480
- Acceptance: leave_provider_message requires confirm+auth; body length bounded; receipts redact message bodies by default; read is tenant-scoped.

## VOICE-ACTION-018 Bind messaging adapter to wallet provider-message surfaces

- Status: todo
- Completion: manual
- Priority: P0
- Track: adapters-messages
- Depends on: VOICE-ACTION-017
- Goal id: VOICE-ACTION-G090
- Outputs: wallet_interface/helpers/_voice_messaging_action_binding.py, wallet_interface/tests/test_voice_messaging_action_binding.py
- Validation: python -m pytest -q wallet_interface/tests/test_voice_messaging_action_binding.py
- Board namespace: voice-action-dag-abby-v1
- Bundle: voice-action/adapters-messages
- Parallel lane: wave-04-messages-ui
- Resource class: cpu-medium
- Predicted files: wallet_interface/helpers/_voice_messaging_action_binding.py, wallet_interface/tests/test_voice_messaging_action_binding.py
- Conflict policy: Binding only; does not redesign message UX.
- Symbolic first: true
- LLM context budget bytes: 16384
- Acceptance: Fake inbox/outbox works under permit; cross-tenant read denies; provider id must be grounded.

## VOICE-ACTION-019 Implement service interaction / callback adapter

- Status: todo
- Completion: manual
- Priority: P0
- Track: adapters-service
- Depends on: VOICE-ACTION-006, VOICE-ACTION-007
- Goal id: VOICE-ACTION-G100
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/adapters/service_interaction.py, ipfs_accelerate_py/test/test_action_service_interaction_adapter.py, docs/voice_action_dag/SERVICE_INTERACTION_BINDINGS.md
- Validation: python -m pytest -q ipfs_accelerate_py/test/test_action_service_interaction_adapter.py
- Board namespace: voice-action-dag-abby-v1
- Bundle: voice-action/adapters-service
- Parallel lane: wave-04-service
- Resource class: cpu-medium
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/adapters/service_interaction.py, ipfs_accelerate_py/test/test_action_service_interaction_adapter.py, docs/voice_action_dag/SERVICE_INTERACTION_BINDINGS.md
- Conflict policy: Exclusive owner of service_interaction adapter module.
- Symbolic first: true
- LLM context budget bytes: 20480
- Acceptance: schedule_service_callback is idempotent on proposal digest; service_id required from grounded evidence; unconfirmed path no-ops.

## VOICE-ACTION-020 Bind service adapter to serviceActionService / interaction models

- Status: todo
- Completion: manual
- Priority: P0
- Track: adapters-service
- Depends on: VOICE-ACTION-019
- Goal id: VOICE-ACTION-G100
- Outputs: wallet_interface/helpers/_voice_service_action_binding.py, wallet_interface/tests/test_voice_service_action_binding.py
- Validation: python -m pytest -q wallet_interface/tests/test_voice_service_action_binding.py
- Board namespace: voice-action-dag-abby-v1
- Bundle: voice-action/adapters-service
- Parallel lane: wave-04-service-ui
- Resource class: cpu-medium
- Predicted files: wallet_interface/helpers/_voice_service_action_binding.py, wallet_interface/tests/test_voice_service_action_binding.py
- Conflict policy: Binding only; service navigation models remain authoritative.
- Symbolic first: true
- LLM context budget bytes: 16384
- Acceptance: Offline fake service interaction log records callbacks under permit only.

## VOICE-ACTION-021 Implement human handoff adapter and HandoffRequest receipts

- Status: completed
- Completion: manual
- Priority: P0
- Track: adapters-handoff
- Depends on: VOICE-ACTION-006, VOICE-ACTION-007
- Goal id: VOICE-ACTION-G110
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/adapters/human_handoff.py, ipfs_accelerate_py/test/test_action_human_handoff_adapter.py, docs/voice_action_dag/HANDOFF.md
- Validation: python -m pytest -q ipfs_accelerate_py/test/test_action_human_handoff_adapter.py
- Board namespace: voice-action-dag-abby-v1
- Bundle: voice-action/adapters-handoff
- Parallel lane: wave-04-handoff
- Resource class: cpu-medium
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/adapters/human_handoff.py, ipfs_accelerate_py/test/test_action_human_handoff_adapter.py, docs/voice_action_dag/HANDOFF.md
- Conflict policy: Exclusive owner of human_handoff adapter.
- Symbolic first: true
- LLM context budget bytes: 20480
- Acceptance: handoff_live_agent creates durable HandoffRequest; statuses distinguish accepted/started/succeeded/unknown/failed; spoken success forbidden without succeeded receipt.

## VOICE-ACTION-022 Integrate handoff with telephone turn escalation path

- Status: todo
- Completion: manual
- Priority: P0
- Track: adapters-handoff
- Depends on: VOICE-ACTION-021, VOICE-ACTION-010
- Goal id: VOICE-ACTION-G110
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/voice_router.py, ipfs_accelerate_py/test/test_telephone_handoff_action.py
- Validation: python -m pytest -q ipfs_accelerate_py/test/test_telephone_handoff_action.py
- Board namespace: voice-action-dag-abby-v1
- Bundle: voice-action/adapters-handoff
- Parallel lane: wave-04-handoff-tel
- Resource class: cpu-medium
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/voice_router.py, ipfs_accelerate_py/test/test_telephone_handoff_action.py
- Conflict policy: Additive telephony metadata only; no real carrier calls in tests.
- Symbolic first: true
- LLM context budget bytes: 20480
- Acceptance: process_telephone_turn with live_agent route yields handoff proposal/receipt fields; fake telephony adapter can mark unknown without claiming success.

## VOICE-ACTION-023 Implement safety overlay policy for escalate_safety

- Status: todo
- Completion: manual
- Priority: P0
- Track: adapters-handoff
- Depends on: VOICE-ACTION-007, VOICE-ACTION-021
- Goal id: VOICE-ACTION-G110
- Outputs: docs/voice_action_dag/SAFETY_OVERLAY.md, ipfs_accelerate_py/test/test_action_safety_overlay.py
- Validation: python -m pytest -q ipfs_accelerate_py/test/test_action_safety_overlay.py
- Board namespace: voice-action-dag-abby-v1
- Bundle: voice-action/adapters-handoff
- Parallel lane: wave-04-safety
- Resource class: cpu-small
- Predicted files: docs/voice_action_dag/SAFETY_OVERLAY.md, ipfs_accelerate_py/test/test_action_safety_overlay.py
- Conflict policy: Owns safety overlay rules; cannot grant arbitrary tool access.
- Symbolic first: true
- LLM context budget bytes: 12288
- Acceptance: safety_guardrail_support can force escalate_safety/handoff under policy; cannot open calendar/messages; emergency destinations are config-bound not model-bound.

## VOICE-ACTION-024 Author Abby confirmation and outcome speech frames for pilot actions

- Status: completed
- Completion: manual
- Priority: P0
- Track: abby-audio
- Depends on: VOICE-ACTION-005, VOICE-ACTION-006
- Goal id: VOICE-ACTION-G120
- Outputs: scripts/build_abby_action_speech_frames.py, docs/phone_dialog_generation/action_speech_frames.jsonl, tests/voice/test_abby_action_speech_frames.py
- Validation: python -m pytest -q tests/voice/test_abby_action_speech_frames.py && python scripts/build_abby_action_speech_frames.py --check
- Board namespace: voice-action-dag-abby-v1
- Bundle: voice-action/audio
- Parallel lane: wave-05-frames
- Resource class: cpu-medium
- Predicted files: scripts/build_abby_action_speech_frames.py, docs/phone_dialog_generation/action_speech_frames.jsonl, tests/voice/test_abby_action_speech_frames.py
- Conflict policy: Owns action speech frame corpus generation.
- Symbolic first: true
- LLM context budget bytes: 16384
- Acceptance: Each pilot logical action has confirm/success/deny/fail texts; texts are slot-safe; no executable content; coverage report emitted.

## VOICE-ACTION-025 Stage or generate precomputed audio for action speech frames

- Status: completed
- Completion: manual
- Priority: P0
- Track: abby-audio
- Depends on: VOICE-ACTION-024
- Goal id: VOICE-ACTION-G120
- Outputs: scripts/stage_abby_action_audio.py, tests/voice/test_abby_action_audio_resolver.py
- Validation: python scripts/stage_abby_action_audio.py --smoke && python -m pytest -q tests/voice/test_abby_action_audio_resolver.py
- Board namespace: voice-action-dag-abby-v1
- Bundle: voice-action/audio
- Parallel lane: wave-05-audio
- Resource class: io-medium
- Predicted files: scripts/stage_abby_action_audio.py, tests/voice/test_abby_action_audio_resolver.py
- Conflict policy: Owns staging of action audio fixtures; production HF publish remains separate gated task.
- Symbolic first: true
- LLM context budget bytes: 12288
- Acceptance: Smoke stage produces resolver rows for pilot confirm/outcome frames; offline resolver exact-match succeeds for staged rows.

## VOICE-ACTION-026 Speak action outcomes via precomputed audio when available

- Status: todo
- Completion: manual
- Priority: P0
- Track: abby-audio
- Depends on: VOICE-ACTION-025, VOICE-ACTION-010
- Goal id: VOICE-ACTION-G120
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/outcome_speech.py, ipfs_accelerate_py/test/test_voice_action_outcome_speech.py
- Validation: python -m pytest -q ipfs_accelerate_py/test/test_voice_action_outcome_speech.py
- Board namespace: voice-action-dag-abby-v1
- Bundle: voice-action/audio
- Parallel lane: wave-05-speak
- Resource class: cpu-medium
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/outcome_speech.py, ipfs_accelerate_py/test/test_voice_action_outcome_speech.py
- Conflict policy: Owns outcome speech selection helper.
- Symbolic first: true
- LLM context budget bytes: 16384
- Acceptance: After execute/deny, spoken text prefers library outcome frame; falls back safely; never invents transfer success.

## VOICE-ACTION-027 Complete AgentAudioChatSurface confirm UX for all pilot statuses

- Status: todo
- Completion: manual
- Priority: P0
- Track: ui
- Depends on: VOICE-ACTION-011
- Goal id: VOICE-ACTION-G130
- Outputs: wallet_interface/ui/src/features/agent/components/AgentAudioChatSurface.tsx, wallet_interface/ui/tests/agent-voice-router.spec.ts
- Validation: npm --prefix wallet_interface/ui test -- tests/agent-voice-router.spec.ts
- Board namespace: voice-action-dag-abby-v1
- Bundle: voice-action/ui
- Parallel lane: wave-05-ui
- Resource class: cpu-small
- Predicted files: wallet_interface/ui/src/features/agent/components/AgentAudioChatSurface.tsx, wallet_interface/ui/tests/agent-voice-router.spec.ts
- Conflict policy: Voice surface UX only; do not rewrite unrelated agent chat.
- Symbolic first: true
- LLM context budget bytes: 16384
- Acceptance: Confirm/dismiss/executed/failed/disabled states are covered; a11y labels present; client cannot bypass server gates.

## VOICE-ACTION-028 Propagate route from agent planner/tool selector into voice-reply requests

- Status: todo
- Completion: manual
- Priority: P0
- Track: ui
- Depends on: VOICE-ACTION-027, VOICE-ACTION-008
- Goal id: VOICE-ACTION-G130
- Outputs: wallet_interface/ui/src/features/agent/lib/voiceGraphRagPrompt.ts, wallet_interface/ui/src/features/agent/lib/clientAudioReplyService.ts, wallet_interface/ui/tests/agent-voice-router.spec.ts
- Validation: npm --prefix wallet_interface/ui test -- tests/agent-voice-router.spec.ts
- Board namespace: voice-action-dag-abby-v1
- Bundle: voice-action/ui
- Parallel lane: wave-05-ui-route
- Resource class: cpu-small
- Predicted files: wallet_interface/ui/src/features/agent/lib/voiceGraphRagPrompt.ts, wallet_interface/ui/src/features/agent/lib/clientAudioReplyService.ts, wallet_interface/ui/tests/agent-voice-router.spec.ts
- Conflict policy: Additive route field plumbing only.
- Symbolic first: true
- LLM context budget bytes: 12288
- Acceptance: When graph/tool layer knows a route, voice-reply FormData includes route; missing route still safe.

## VOICE-ACTION-029 Build offline e2e pilot matrix over slotted DAG samples

- Status: todo
- Completion: manual
- Priority: P0
- Track: e2e
- Depends on: VOICE-ACTION-013, VOICE-ACTION-015, VOICE-ACTION-017, VOICE-ACTION-019, VOICE-ACTION-021, VOICE-ACTION-025, VOICE-ACTION-010
- Goal id: VOICE-ACTION-G140
- Outputs: tests/e2e/voice_action_dag/test_abby_pilot_matrix.py, docs/voice_action_dag/E2E_PILOT.md, data/voice_action_dag/e2e/matrix-receipt.example.json
- Validation: python -m pytest -q tests/e2e/voice_action_dag/test_abby_pilot_matrix.py
- Board namespace: voice-action-dag-abby-v1
- Bundle: voice-action/e2e
- Parallel lane: wave-06-e2e
- Resource class: cpu-medium
- Predicted files: tests/e2e/voice_action_dag/test_abby_pilot_matrix.py, docs/voice_action_dag/E2E_PILOT.md, data/voice_action_dag/e2e/matrix-receipt.example.json
- Conflict policy: Owns e2e matrix harness; uses fakes for all adapters.
- Symbolic first: true
- LLM context budget bytes: 24576
- Acceptance: All 12 routes covered; tool-adjacent routes confirm+execute with fakes; content-only routes assert no_action; live_agent asserts handoff semantics; no network.

## VOICE-ACTION-030 Add adversarial suite: injection, auto-exec, false transfer claims

- Status: todo
- Completion: manual
- Priority: P0
- Track: e2e
- Depends on: VOICE-ACTION-029
- Goal id: VOICE-ACTION-G140
- Outputs: tests/e2e/voice_action_dag/test_abby_adversarial.py
- Validation: python -m pytest -q tests/e2e/voice_action_dag/test_abby_adversarial.py
- Board namespace: voice-action-dag-abby-v1
- Bundle: voice-action/e2e
- Parallel lane: wave-06-adversarial
- Resource class: cpu-small
- Predicted files: tests/e2e/voice_action_dag/test_abby_adversarial.py
- Conflict policy: Owns adversarial cases only.
- Symbolic first: true
- LLM context budget bytes: 16384
- Acceptance: Command-like user text cannot create descriptors; missing confirm never executes; live_agent success speech blocked without succeeded receipt; secret env not leaked via CLI path.

## VOICE-ACTION-031 Publish operator runbook and enablement checklist

- Status: todo
- Completion: manual
- Priority: P1
- Track: operations
- Depends on: VOICE-ACTION-029, VOICE-ACTION-001
- Goal id: VOICE-ACTION-G150
- Outputs: docs/planning/VOICE_ACTION_DAG_ABBY_AGENT_SUPERVISOR_RUNBOOK.md, docs/voice_action_dag/ENABLEMENT_CHECKLIST.md
- Validation: python scripts/validate_voice_action_dag_abby_plan.py
- Board namespace: voice-action-dag-abby-v1
- Bundle: voice-action/operations
- Parallel lane: wave-06-docs
- Resource class: cpu-small
- Predicted files: docs/planning/VOICE_ACTION_DAG_ABBY_AGENT_SUPERVISOR_RUNBOOK.md, docs/voice_action_dag/ENABLEMENT_CHECKLIST.md
- Conflict policy: Documentation only for ops enablement.
- Symbolic first: true
- LLM context budget bytes: 12288
- Acceptance: Runbook documents flags (WALLET_VOICE_UNIFIED_ROUTER_ENABLED, WALLET_VOICE_ACTION_EXECUTE_ENABLED), fake vs live transports, handoff truthfulness, and parallel lane ownership.

## VOICE-ACTION-032 Gate production execute behind signed deployment binding

- Status: todo
- Completion: manual
- Priority: P1
- Track: operations
- Depends on: VOICE-ACTION-029, VOICE-ACTION-007
- Goal id: VOICE-ACTION-G040
- Outputs: docs/voice_action_dag/DEPLOYMENT_BINDING.md, ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/deployment_binding.py, ipfs_accelerate_py/test/test_action_deployment_binding.py
- Validation: python -m pytest -q ipfs_accelerate_py/test/test_action_deployment_binding.py
- Board namespace: voice-action-dag-abby-v1
- Bundle: voice-action/policy
- Parallel lane: wave-06-binding
- Resource class: cpu-small
- Predicted files: docs/voice_action_dag/DEPLOYMENT_BINDING.md, ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/deployment_binding.py, ipfs_accelerate_py/test/test_action_deployment_binding.py
- Conflict policy: Owns deployment binding checks.
- Symbolic first: true
- LLM context budget bytes: 12288
- Acceptance: Catalog digest + adapter identities must match signed deployment binding; mismatch denies execute even if confirm flag is set.

## VOICE-ACTION-033 Resolve dirty main checkout blocking 1 worktree merges

- Status: blocked
- Completion: manual
- Is schedulable: false
- Review only: true
- Blocked reason: operator_reconciliation_required
- Priority: P1
- Track: ops
- Generated by: ipfs_accelerate_py.agent_supervisor.reconciliation-guardrail@1
- Reconciliation kind: main_checkout_dirty
- Reconciliation reason: main_checkout_dirty
- Reconciliation fingerprint: 62ae704a39fb96ac11bad59f4bc16df2caba0d12
- Reconciliation discovery: /home/barberb/211-AI/211-AI/data/voice_action_dag/agent_supervisor/shards/1/discovery/2026-08-04-voice-action-033-reconciliation-62ae704a39fb.md
- Canonical board task: false
- Fingerprint: 62ae704a39fb96ac11bad59f4bc16df2caba0d12
- Dedupe key: reconciliation_guardrail:main_checkout_dirty
- Depends on:
- Outputs: data/voice_action_dag/agent_supervisor/shards/1/discovery, docs/planning/voice_action_dag_abby.todo.md
- Board namespace: voice-action-dag-abby-v1
- Goal id: VOICE-ACTION-G040
- Bundle: voice-action/policy
- Parallel lane: wave-06-binding
- Resource class: cpu-small
- Predicted files: data/voice_action_dag/agent_supervisor/shards/1/discovery, docs/planning/voice_action_dag_abby.todo.md
- Conflict policy: Operator-only reconciliation of dirty worktrees; never auto-commit, stash, or discard unknown checkout content.
- Symbolic first: true
- LLM context budget bytes: 4096
- Validation: test -f /home/barberb/211-AI/211-AI/data/voice_action_dag/agent_supervisor/shards/1/discovery/2026-08-04-voice-action-033-reconciliation-62ae704a39fb.md
- Acceptance: Reconciliation guardrail filed this because 1 branch or worktree cleanup candidates are blocked by main_checkout_dirty. Use evidence and the machine-readable reconciliation plan in /home/barberb/211-AI/211-AI/data/voice_action_dag/agent_supervisor/shards/1/discovery/2026-08-04-voice-action-033-reconciliation-62ae704a39fb.md, reconcile the dirty checkout or dirty worktree group deliberately, then rerun the supervisor cleanup/reconciliation pass and confirm that the blocked candidate count decreases.
