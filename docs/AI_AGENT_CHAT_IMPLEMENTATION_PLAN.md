# AI Agent Chat Implementation Plan

## Goal

Build an interactive Abby chat agent that can answer questions over the 211
GraphRAG corpus and operate every normal user-facing app surface through the
same typed actions used by the GUI.

The chatbot should not be a separate demo path. It should be another controller
for the app:

- Users can ask for service-navigation help grounded in the 211 corpus.
- Users can ask Abby to navigate the app, update forms, save services, create
  service plans, manage recipients, prepare proofs, review audit history, and
  start export/sharing workflows.
- GUI clicks and chat tool calls use shared operation contracts so behavior,
  validation, audit, and wallet persistence stay consistent.
- Private wallet data is only included in model prompts or tool inputs after
  explicit user intent and the relevant wallet/consent gate.

## Source Code To Reuse

Reviewed source:

- Portland Laws `src/lib`:
  `https://github.com/portland-laws/portland-laws.github.io/tree/main/src/lib`
- Existing 211 port plan:
  `docs/PORTLAND_LAWS_WEBGPU_GRAPHRAG_PORT_PLAN.md`
- Existing portal product plan:
  `docs/211_SERVICE_NAVIGATION_PORTAL_PLAN.md`

### Already Reused In This Repo

The core browser GraphRAG and client inference path is already present.

- Browser GraphRAG runtime:
  `wallet_interface/ui/src/lib/graphrag/*`
- GraphRAG service wrapper:
  `wallet_interface/ui/src/services/graphRagService.ts`
- Search worker:
  `wallet_interface/ui/src/workers/ragSearchWorker.ts`
- Embedding worker:
  `wallet_interface/ui/src/workers/embeddingWorker.ts`
- Client LLM worker:
  `wallet_interface/ui/src/workers/clientLLMWorker.ts`
- Backend detection:
  `wallet_interface/ui/src/lib/backendDetection.ts`
- LLM model config:
  `wallet_interface/ui/src/lib/llmConfig.ts`
- Static browser corpus:
  `wallet_interface/ui/public/corpus/211-info/current`

The chat implementation should build on these files rather than introduce a
new retrieval stack.

### Portland Patterns Still Worth Adapting

`clientConversation.ts`

- Reuse the idea of a small conversation-context builder that combines identity,
  goals, history, memories, and the current counterparty.
- Adapt it into an Abby-specific `agentConversation.ts` that builds prompts from
  user intent, current route, selected records, service evidence, wallet-safe
  context, and pending tool confirmations.
- Do not reuse the AI Town character/player concepts directly.

`staticAgentSimulation.ts`

- Reuse the decision-loop shape: observe state, evaluate possible actions, pick
  the highest-value next action, execute it, then emit an update.
- Adapt it into a deterministic agent planner for app tasks, not a simulated
  NPC world. The planner should rank actions such as "search services",
  "ask a clarifying question", "open detail", "save service", "create plan",
  "request confirmation", or "navigate to proof center".
- Keep fallback deterministic when the local LLM is unavailable.

`staticApi.ts` and `staticTypes.ts`

- Reuse the "static API replacement" pattern as a facade layer. The app should
  expose route/surface operations through a stable object instead of letting
  the chat system reach into React component internals.
- Adapt it into `agentSurfaceApi.ts`, where every operation has a typed input,
  validation result, audit policy, and execution result.

`staticDb.ts` and `worldPersistence.ts`

- Reuse the persistence abstraction pattern only for public, non-sensitive
  session data and tests.
- Do not store private wallet state in localStorage. Private chat memory,
  saved services, notes, plans, grants, and interactions must remain encrypted
  wallet records or API-backed wallet state.

`clientLLM.ts` / `clientLLMWorkerService.ts`

- The current 211 app already uses the worker-service version. Extend that path
  with structured response parsing and tool-call generation, while retaining
  deterministic fallbacks.
- Avoid requiring large WebGPU models for core workflows.

`warningSuppressionUtils.ts`

- Optional polish for noisy browser ML warnings. This should not block the
  agent architecture.

## Current App Surfaces

The current route model is in `wallet_interface/ui/src/models/abby.ts`.

Primary routes:

- `home`
- `register`
- `check-in`
- `contacts`
- `sharing-rules`
- `uploads`
- `social-services`
- `shelter`

Secondary routes:

- `recipient-access`
- `benefits-protection`
- `analytics`
- `proof-center`
- `exports`
- `security`
- `audit`

The initial chat scope is every route above. Future service-detail routes from
`docs/211_SERVICE_NAVIGATION_PORTAL_PLAN.md` should join the same surface
registry when implemented:

- `services/:docId`
- `services/:docId/plan`
- `interactions`

## Architecture

### Core Principle

Every meaningful GUI operation becomes a typed command. The GUI and chat both
call that command. The command owns validation, side effects, wallet writes,
audit metadata, and user-visible result text.

Bad target shape:

- Button mutates local React state directly.
- Chat mutates similar state through a second path.
- Wallet persistence and audit behavior diverge.

Target shape:

- Button calls `appActions.createProof(input)`.
- Chat tool call invokes `create_proof` with the same input.
- The same validator, wallet API, audit hook, and reducer run in both cases.

### Proposed Modules

Create these modules under `wallet_interface/ui/src/agent`.

- `types.ts`
  - `AgentMessage`
  - `AgentSession`
  - `AgentIntent`
  - `AgentPlan`
  - `AgentToolDefinition`
  - `AgentToolCall`
  - `AgentToolResult`
  - `AgentPermissionLevel`
  - `AgentConfirmationRequest`
  - `SurfaceContext`
  - `EvidenceBundle`

- `surfaceRegistry.ts`
  - Registers routes, readable context providers, and executable tools.
  - Defines which tools require confirmation, wallet auth, user presence, or
    explicit private-context opt-in.

- `surfaceApi.ts`
  - Stable app-facing operation facade.
  - Wraps app reducers/state setters and wallet API calls.
  - Returns typed success/failure results with user-facing summaries.

- `commandSchemas.ts`
  - TypeScript schemas for each command input/output.
  - Start with handwritten type guards to avoid adding a runtime schema
    dependency. Move to Zod or Valibot later only if validation complexity
    warrants it.

- `agentConversation.ts`
  - Abby persona and policy prompt builder.
  - Conversation history compaction.
  - Prompt construction for app-control, service navigation, and mixed tasks.
  - Adapted from the Portland `clientConversation.ts` pattern.

- `agentPlanner.ts`
  - Intent classifier and next-action planner.
  - Uses deterministic rules first; optionally asks the local LLM to choose
    from registered tools.
  - Adapted from the Portland `staticAgentSimulation.ts` decision-loop shape.

- `toolExecutor.ts`
  - Validates tool input.
  - Checks policy gates.
  - Requests user confirmation when required.
  - Executes through `surfaceApi`.
  - Emits audit/interaction records as configured.

- `chatController.ts`
  - React-facing orchestration service.
  - Owns session state, streaming/progress events, pending confirmations,
    errors, and retry.

- `promptGuards.ts`
  - Redacts private wallet context unless explicitly allowed.
  - Filters tool descriptions and state summaries by permission level.
  - Enforces citation and "do not invent service facts" rules for GraphRAG.

- `serviceNavigationAgent.ts`
  - Integrates `answer211InfoQuestion`, `build211InfoEvidence`, and
    `search211Info`.
  - Produces cited answers and actionable next steps.
  - Can invoke service tools such as save, plan, call-intent, share, and open
    detail after confirmation.

- `agentMemory.ts`
  - Ephemeral chat memory by default.
  - Wallet-backed private memory only after explicit user opt-in.
  - No raw query logging by default.

Create these support modules under `wallet_interface/ui/src/services`.

- `agentChatService.ts`
  - Public API used by React components.
  - Hides planner/executor internals.

- `serviceActionService.ts`
  - Call, text, email, maps, share, and ICS helpers from the portal plan.
  - Tool-executable and GUI-executable.

## Surface Tool Inventory

### Global Tools

- `navigate`
  - Inputs: `route`, optional route params.
  - Confirmation: no.
  - Audit: no, except sensitive route entry can be recorded locally if needed.

- `summarize_current_screen`
  - Inputs: none.
  - Confirmation: no.
  - Reads only the current route's safe context provider.

- `explain_next_steps`
  - Inputs: optional goal.
  - Confirmation: no.
  - Produces deterministic guidance over registered capabilities.

### Registration

- `update_registration_profile`
  - Updates draft fields such as preferred name, contact info, shelter
    affiliation, needs, and preferred check-in channels.
  - Confirmation required before high-impact identity fields are committed.

- `attach_profile_photo`
  - User-file initiated only. Chat can explain and navigate, but cannot choose a
    file silently.

- `submit_registration`
  - Confirmation required.
  - Wallet write and audit required.

### Check-In

- `update_check_in_policy`
  - Inputs: interval, channels, grace period, escalation enabled.
  - Confirmation required if escalation settings change.

- `submit_check_in`
  - Inputs: channel, optional note.
  - Confirmation required.
  - Wallet/audit event required.

### Contacts And Sharing Rules

- `add_recipient`
- `edit_recipient`
- `remove_recipient`
- `update_recipient_scopes`
- `preview_sharing_capabilities`
- `request_shelter_contact`
- `approve_shelter_contact_request`
- `deny_shelter_contact_request`

Confirmation is required for recipient deletion, scope expansion, and contact
approval. Audit is required for all grant/scope changes.

### Uploads

- `summarize_upload_requirements`
- `classify_uploaded_document`
- `repair_upload_storage`
- `toggle_upload_shared`

The chat can guide file selection and process files after the user chooses
them. It cannot read local files without a user-triggered upload event.

### Social Services

- `search_211_services`
- `answer_211_question`
- `build_211_evidence`
- `open_service_detail`
- `save_service`
- `create_service_plan`
- `record_service_interaction`
- `prepare_service_share`
- `generate_call_script`
- `generate_provider_questions`

Search and answers use public 211 corpus data. Saving, planning, notes,
location, and interaction history are wallet-private.

### Shelter

- `create_managed_user_account`
- `create_shelter_staff_account`
- `send_shelter_nudge`
- `approve_user_shelter_request`
- `deny_user_shelter_request`
- `add_shelter_as_recipient`

These tools require explicit confirmation because they affect contact flows and
potential third-party access.

### Recipient Access

- `record_controller_approval`
- `approve_access_request`
- `reject_access_request`
- `revoke_access_request`
- `analyze_granted_record`
- `view_granted_record`
- `delegate_grant`

This is a high-risk surface. Tool execution must enforce the same checks as the
GUI:

- threshold approval requirements
- active grant status
- allowed abilities
- allowed output types
- user-presence requirements
- audit event creation

### Benefits Protection

- `set_benefits_protection_opt_in`
- `explain_benefits_privacy_tradeoff`

Opt-in changes require confirmation.

### Analytics

- `select_analytics_study`
- `unselect_analytics_study`
- `explain_analytics_privacy_budget`
- `submit_analytics_consent`

Consent submission requires confirmation and must not include raw document
contents in prompts.

### Proof Center

- `create_proof`
- `explain_proof_receipt`
- `verify_proof_status`

Proof creation requires explicit claim, verifier, witness label, and
confirmation.

### Exports

- `create_export_bundle`
- `import_export_bundle`
- `explain_export_contents`

Export creation and import require confirmation and audit.

### Security

- `show_wallet_snapshot_status`
- `save_wallet_snapshot`
- `restore_wallet_snapshot`
- `explain_recovery_policy`

Snapshot mutation requires confirmation. Restore should include a stronger
warning because it can replace visible state.

### Audit

- `search_audit_events`
- `summarize_audit_events`
- `explain_audit_event`

Read-only by default.

## GraphRAG Integration

The agent should use the existing 211 GraphRAG service as one of its tools.

Flow for service questions:

1. Classify the message as public service-navigation intent.
2. Call `build211InfoEvidence` or `answer211InfoQuestion`.
3. Return a cited answer with source numbers.
4. Offer actions based on retrieved service records:
   - open detail
   - save service
   - create plan
   - call or prepare call script
   - map/directions
   - share with recipient
   - create reminder
5. Require confirmation before any wallet write, share, location use, or
   outbound action intent is recorded.

Flow for mixed public/private questions:

1. Use public 211 retrieval first.
2. Ask whether Abby may use private wallet context such as uploaded documents,
   saved services, recipient list, eligibility notes, or location.
3. If allowed, retrieve only the minimum scoped private context.
4. Keep private context inside the permitted local or server execution boundary.
5. Cite public 211 facts separately from private wallet facts.

The model should never invent:

- phone numbers
- hours
- addresses
- eligibility rules
- required documents
- grant status
- proof status
- audit events

When evidence is missing, the response should say what is missing and suggest
contacting 211 or the listed provider.

## Agent Prompt Shape

The prompt builder should produce compact sections:

- role and product policy
- current route and safe screen state
- user goal
- registered tools available for the current permission level
- public GraphRAG evidence, if any
- private wallet context, only after explicit opt-in
- pending confirmations
- required output format

For local LLMs that cannot reliably emit JSON, the planner should default to a
deterministic command grammar:

```text
ACTION: answer_user
MESSAGE: ...
```

or:

```text
ACTION: request_confirmation
TOOL: save_service
SUMMARY: Save Central City Concern emergency shelter sign-up?
```

Only move to JSON tool calls when tests show the selected model can produce
valid structured output consistently.

## UI Design

Add a persistent assistant entry point to the app shell:

- Desktop: right-side drawer with conversation, current task, evidence, and
  pending confirmations.
- Mobile: bottom sheet that can expand to full screen.
- Every pending tool call should render as a clear confirmation card.
- Evidence citations should be clickable and navigate to service detail or
  source/provenance once those routes exist.
- The assistant should show "I can do this" actions as buttons only when they
  map to registered tools.

Do not hide the app behind the chat. The user should be able to continue using
the GUI while the chat remains open.

## State Refactor Plan

`wallet_interface/ui/src/app/App.tsx` currently owns route state, screen state,
and many screen-specific handlers in one file. Before full agent control, split
state and operations into shared units.

Recommended extraction order:

1. Create `src/app/appState.ts`.
   - Move persisted state shape and defaults.
   - Keep route state in the shell.

2. Create `src/app/appActions.ts`.
   - Move operations currently embedded in screens.
   - Operations receive current state and dispatch/setter functions.
   - Return `ActionResult`.

3. Create `src/agent/surfaceApi.ts`.
   - Wrap `appActions` as tool-executable operations.
   - Add validation and confirmation metadata.

4. Update GUI screens.
   - Replace direct state mutation with calls to `appActions`.
   - Keep presentational components simple.

5. Add chat controller.
   - Use the same `surfaceApi`.
   - Add telemetry/audit hooks only through command execution, not from chat UI.

This refactor should be incremental. Start with Social Services, Check-In,
Contacts, Proof Center, Recipient Access, and Exports because they provide the
highest value for an agent workflow.

## Permission And Safety Model

Define four execution levels:

- `read_public`
  - Public 211 corpus, route names, app capability descriptions.

- `read_wallet_summary`
  - Non-sensitive wallet summaries such as record labels, grant labels, and
    proof receipt metadata.
  - Requires active wallet context.

- `write_wallet`
  - Saved services, plans, check-ins, notes, proofs, access decisions, exports.
  - Requires explicit user confirmation.

- `share_or_disclose`
  - Scope expansion, recipient sharing, grant delegation, export, analytics
    consent, disclosure-related operations.
  - Requires explicit confirmation and audit.

Hard rules:

- Do not execute destructive or disclosure actions from a single model output.
  Always show a confirmation card.
- Do not include precise location, document contents, private notes, provider
  conversation contents, or raw query history in prompts by default.
- Do not persist raw chat transcripts as wallet records unless the user opts in.
- Store private notes and service plans as wallet records, not localStorage.
- Public corpus answers must remain cited and source-grounded.
- Emergency, medical, legal, and benefits eligibility answers must include
  appropriate uncertainty and provider/211 verification guidance.

## Backend And Wallet API Work

The first UI version can execute many operations in local React state and the
existing wallet API client. Production-grade agent control needs wallet-backed
endpoints for service plans, saved services, and interactions from
`docs/211_SERVICE_NAVIGATION_PORTAL_PLAN.md`.

Add or wrap API methods for:

- saved services
- service plans
- service interactions
- private notes
- service-plan sharing grants
- audit-safe action metadata

The agent tool executor should call the same API functions as the GUI. It
should not create a second API client.

## Testing Strategy

Unit tests:

- command schema validation
- permission gates
- confirmation requirements
- prompt redaction
- deterministic planner routing
- GraphRAG evidence-to-action mapping
- service action URL and ICS generation

React/component tests:

- chat drawer opens and sends messages
- pending confirmation card executes or cancels a tool call
- GUI and chat produce the same state changes for selected actions
- GraphRAG citations render and link correctly

Playwright smoke tests:

- ask "food pantry near Portland" and receive cited 211 evidence
- ask "save the first result" and verify confirmation is required
- confirm save and verify saved service appears in the UI
- ask "set my check-in interval to 3 days" and verify confirmation/state
- ask "show audit history" and navigate to audit
- reject a recipient-access request through chat and verify audit entry

Privacy tests:

- private notes are absent from prompts unless explicitly enabled
- raw query text is not persisted by default
- share/grant/export tools require confirmation
- revoked grants cannot be used by chat tools

Build checks:

- `npm run build` from `wallet_interface/ui`
- `npm run test:smoke` from `wallet_interface/ui`
- Python wallet/API tests for any new endpoints

## Implementation Phases

### Phase 1: Agent Contracts And Read-Only Chat

Deliverables:

- `src/agent/types.ts`
- `src/agent/surfaceRegistry.ts`
- `src/agent/agentConversation.ts`
- `src/agent/serviceNavigationAgent.ts`
- `src/services/agentChatService.ts`
- Chat drawer UI shell.

Scope:

- Answer public 211 questions.
- Summarize current screen.
- Navigate between routes.
- Explain available actions.
- No wallet writes.

Acceptance criteria:

- User can open chat from any route.
- User can ask service questions and receive cited GraphRAG answers.
- User can ask Abby to navigate to any existing route.
- No private wallet data enters prompts unless enabled in a test-only fixture.

### Phase 2: Shared Action Facade

Deliverables:

- `src/app/appActions.ts`
- `src/agent/surfaceApi.ts`
- command schemas for high-value routes.
- GUI refactor for Social Services, Check-In, Contacts, Proof Center, Recipient
  Access, and Exports.

Scope:

- GUI and chat use the same operations.
- Tool calls can stage changes and ask for confirmation.

Acceptance criteria:

- Existing GUI behavior remains unchanged.
- Tool executor can run read-only tools and staged write tools.
- Unit tests prove GUI action and chat action converge on the same state.

### Phase 3: Service Navigation Agent Actions

Deliverables:

- `serviceActionService.ts`
- service search/open/save/plan/interaction tools.
- cited evidence panel in chat.
- generated call script and provider-question helpers.

Scope:

- Search 211 corpus.
- Save a service.
- Create a basic service plan.
- Record action intent for call/map/share/calendar.

Acceptance criteria:

- Saving and planning require confirmation.
- Saved service and plan persist through the wallet path available at that
  milestone.
- All service facts shown by chat are cited or marked missing.

### Phase 4: Wallet And Disclosure Tools

Deliverables:

- recipient, grant, proof, export, analytics, and audit tools.
- permission gates for each high-risk operation.
- confirmation cards with before/after summaries.

Scope:

- Manage recipients and scopes.
- Approve/reject/revoke access requests.
- Create proofs.
- Create export bundles.
- Explain audit history.

Acceptance criteria:

- No disclosure operation executes without explicit confirmation.
- Existing wallet authorization checks are reused.
- Audit events are generated for sensitive actions.

### Phase 5: Memory, Personalization, And Private Context

Deliverables:

- `agentMemory.ts`
- wallet-backed optional memory records.
- private-context consent UI.
- prompt redaction tests.

Scope:

- Remember user preferences only after opt-in.
- Use saved services and plans in responses after permission.
- Keep public service evidence and private wallet facts distinct.

Acceptance criteria:

- User can turn memory on/off.
- Private memory is encrypted wallet state.
- Deleting/revoking memory removes it from future prompts.

### Phase 6: Production Hardening

Deliverables:

- model/tool-call reliability benchmarks.
- accessibility review.
- mobile chat drawer tests.
- privacy/threat-model update.
- operations runbook update.

Acceptance criteria:

- Chat remains usable without local LLM support.
- WebGPU models improve quality but are not required.
- All high-risk actions are confirmed, audited, and test-covered.

## First Implementation Slice

The smallest useful slice should be:

1. Add read-only chat drawer.
2. Add route navigation tool.
3. Add 211 GraphRAG question-answer tool.
4. Add deterministic planner rules for:
   - service search questions
   - "go to ..."
   - "what can I do here?"
5. Add tests that prove no private state is sent to the prompt.

This creates the base agent UX without touching the most sensitive wallet
mutation surfaces. After that, add shared action contracts and confirmation
cards before enabling write tools.

## Open Decisions

- Whether local LLM tool selection is good enough for production, or whether
  the first production release should use deterministic intent routing plus
  LLM-generated prose only.
- Whether to introduce a runtime schema library for tool inputs.
- Which wallet API endpoints should be added before service-plan UI work.
- Whether chat transcripts are ephemeral only, wallet-encrypted, or exportable
  under user control.
- Whether server-side LLM mode is allowed for private wallet context, and under
  what deployment/privacy policy.

