# AI Agent Chat Implementation Todo

This backlog is the executable implementation queue for
`docs/AI_AGENT_CHAT_IMPLEMENTATION_PLAN.md`.

The implementation daemon parses tasks with the heading format `## AGENT-...`
and the metadata bullets directly below each heading.

Priority guide:

- `P0`: foundation or blocker work
- `P1`: user-visible core path work
- `P2`: adjacent capability or hardening work
- `P3`: polish or optional production refinement

Track guide:

- `platform`: shared state, contracts, daemon/supervisor, tests
- `agent`: planner, prompt building, tools, executor, memory
- `graphrag`: 211 corpus search, evidence, citations, service actions
- `ui`: chat drawer, confirmation cards, app integration
- `wallet`: private state, permissions, grants, audit, API
- `privacy`: redaction, consent, safety policies, threat model
- `ops`: validation, runbooks, production readiness

## AGENT-000 Agent Chat Control Plane
- Status: todo
- Completion: artifact
- Priority: P0
- Track: platform
- Depends on: none
- Outputs: docs/AI_AGENT_CHAT_IMPLEMENTATION_PLAN.md, docs/AI_AGENT_CHAT_IMPLEMENTATION_TODO.md, scripts/agent_chat_implementation_daemon.py, scripts/agent_chat_implementation_supervisor.py, scripts/portal_implementation_daemon.py, scripts/portal_implementation_supervisor.py, tests/test_portal_implementation_daemon.py
- Validation: python scripts/agent_chat_implementation_daemon.py --once --no-implement; python scripts/agent_chat_implementation_supervisor.py --once --no-implement; pytest tests/test_portal_implementation_daemon.py -q
- Acceptance: The agent-chat backlog can be parsed, durable state is written, a next AGENT task is selected, and the supervisor can rewrite strategy without mutating source code.

## AGENT-010 Shared Agent Type Contracts
- Status: todo
- Completion: artifact
- Priority: P0
- Track: platform
- Depends on: AGENT-000
- Outputs: wallet_interface/ui/src/agent/types.ts, wallet_interface/ui/src/agent/commandSchemas.ts, wallet_interface/ui/src/agent/surfaceRegistry.ts
- Validation: npm --prefix wallet_interface/ui run build
- Acceptance: Agent messages, sessions, intents, plans, tool definitions, tool calls, tool results, permission levels, confirmations, surface context, and evidence bundles have typed contracts and runtime guards.

## AGENT-011 App State Extraction
- Status: todo
- Completion: artifact
- Priority: P0
- Track: platform
- Depends on: AGENT-010
- Outputs: wallet_interface/ui/src/app/appState.ts, wallet_interface/ui/src/app/App.tsx
- Validation: npm --prefix wallet_interface/ui run build
- Acceptance: Persisted Abby app state, defaults, and route helpers are available outside `App.tsx` without changing current GUI behavior.

## AGENT-012 Shared App Action Facade
- Status: todo
- Completion: artifact
- Priority: P0
- Track: platform
- Depends on: AGENT-011
- Outputs: wallet_interface/ui/src/app/appActions.ts, wallet_interface/ui/src/agent/surfaceApi.ts
- Validation: npm --prefix wallet_interface/ui run build
- Acceptance: High-value GUI actions can be invoked through shared typed operations that return action results and confirmation metadata.

## AGENT-013 GUI Action Convergence Tests
- Status: completed
- Completion: artifact
- Priority: P0
- Track: platform
- Depends on: AGENT-012
- Outputs: wallet_interface/ui/tests/agent-action-convergence.spec.ts
- Validation: npm --prefix wallet_interface/ui test -- tests/agent-action-convergence.spec.ts
- Acceptance: Representative GUI flows and agent tool flows produce equivalent state changes for navigation, check-in draft updates, service search, proof creation staging, and access-request decisions.

## AGENT-020 Read-Only Chat Drawer Shell
- Status: todo
- Completion: artifact
- Priority: P1
- Track: ui
- Depends on: AGENT-010
- Outputs: wallet_interface/ui/src/components/agent/AgentChatDrawer.tsx, wallet_interface/ui/src/components/agent/AgentMessageList.tsx, wallet_interface/ui/src/components/agent/AgentComposer.tsx, wallet_interface/ui/src/app/App.tsx
- Validation: npm --prefix wallet_interface/ui run build
- Acceptance: Users can open a persistent assistant drawer from any current route, send a message, see assistant responses, and continue using the GUI.

## AGENT-021 Mobile Chat Bottom Sheet
- Status: todo
- Completion: artifact
- Priority: P2
- Track: ui
- Depends on: AGENT-020
- Outputs: wallet_interface/ui/src/components/agent/AgentChatBottomSheet.tsx, wallet_interface/ui/src/styles/global.css
- Validation: npm --prefix wallet_interface/ui test -- tests/smoke.spec.ts
- Acceptance: The assistant adapts to mobile as an expandable bottom sheet without obscuring required app controls.

## AGENT-022 Confirmation Card UI
- Status: todo
- Completion: artifact
- Priority: P1
- Track: ui
- Depends on: AGENT-020, AGENT-012
- Outputs: wallet_interface/ui/src/components/agent/AgentConfirmationCard.tsx, wallet_interface/ui/src/components/agent/AgentToolResultCard.tsx
- Validation: npm --prefix wallet_interface/ui run build
- Acceptance: Pending high-risk tool calls render as explicit confirm/cancel cards with concise before/after summaries.

## AGENT-030 Chat Controller Service
- Status: todo
- Completion: artifact
- Priority: P0
- Track: agent
- Depends on: AGENT-010, AGENT-020
- Outputs: wallet_interface/ui/src/services/agentChatService.ts, wallet_interface/ui/src/agent/chatController.ts
- Validation: npm --prefix wallet_interface/ui run build
- Acceptance: React components can send messages, receive progress updates, manage pending confirmations, recover from errors, and retry without reaching into planner internals.

## AGENT-031 Abby Conversation Prompt Builder
- Status: todo
- Completion: artifact
- Priority: P0
- Track: agent
- Depends on: AGENT-030
- Outputs: wallet_interface/ui/src/agent/agentConversation.ts
- Validation: npm --prefix wallet_interface/ui run build
- Acceptance: The prompt builder adapts the Portland `clientConversation.ts` pattern for Abby, using safe route context, conversation history, user goal, registered tools, evidence, and pending confirmations.

## AGENT-032 Deterministic Planner
- Status: todo
- Completion: artifact
- Priority: P0
- Track: agent
- Depends on: AGENT-031, AGENT-012
- Outputs: wallet_interface/ui/src/agent/agentPlanner.ts
- Validation: npm --prefix wallet_interface/ui run build
- Acceptance: The planner routes common intents for "go to", "what can I do here", service questions, save/plan requests, confirmation responses, and audit/proof/export navigation without requiring a local LLM.

## AGENT-033 Local LLM Tool Selection Adapter
- Status: todo
- Completion: artifact
- Priority: P2
- Track: agent
- Depends on: AGENT-032
- Outputs: wallet_interface/ui/src/agent/localLlmToolSelector.ts, wallet_interface/ui/src/lib/clientLLMWorkerService.ts
- Validation: npm --prefix wallet_interface/ui run build
- Acceptance: Local model output can optionally choose from registered tools, with deterministic fallback when structured output is invalid or unavailable.

## AGENT-034 Tool Executor
- Status: todo
- Completion: artifact
- Priority: P0
- Track: agent
- Depends on: AGENT-012, AGENT-032
- Outputs: wallet_interface/ui/src/agent/toolExecutor.ts
- Validation: npm --prefix wallet_interface/ui run build
- Acceptance: Tool execution validates input, checks permissions, requests confirmation when needed, executes through `surfaceApi`, and emits typed results.

## AGENT-035 Agent Session Memory
- Status: todo
- Completion: artifact
- Priority: P1
- Track: agent
- Depends on: AGENT-030, AGENT-050
- Outputs: wallet_interface/ui/src/agent/agentMemory.ts
- Validation: npm --prefix wallet_interface/ui run build
- Acceptance: Chat memory is ephemeral by default, optional wallet-backed memory requires opt-in, and raw chat transcripts are not persisted by default.

## AGENT-040 211 Service Navigation Agent
- Status: todo
- Completion: artifact
- Priority: P0
- Track: graphrag
- Depends on: AGENT-030
- Outputs: wallet_interface/ui/src/agent/serviceNavigationAgent.ts, wallet_interface/ui/src/services/graphRagService.ts
- Validation: npm --prefix wallet_interface/ui run build
- Acceptance: Chat can call the existing 211 GraphRAG service to answer public service questions with cited evidence and deterministic fallback summaries.

## AGENT-041 Evidence-To-Action Mapper
- Status: todo
- Completion: artifact
- Priority: P1
- Track: graphrag
- Depends on: AGENT-040, AGENT-034
- Outputs: wallet_interface/ui/src/agent/evidenceActions.ts
- Validation: npm --prefix wallet_interface/ui run build
- Acceptance: Retrieved service records can produce available actions such as open detail, save, create plan, call script, provider questions, map, share, and reminder when backing data exists.

## AGENT-042 Service Action Service
- Status: todo
- Completion: artifact
- Priority: P1
- Track: graphrag
- Depends on: AGENT-041
- Outputs: wallet_interface/ui/src/services/serviceActionService.ts, wallet_interface/ui/src/lib/calendar/ics.ts
- Validation: npm --prefix wallet_interface/ui run build
- Acceptance: Call, text, email, map, share, and calendar helpers can be invoked by both GUI and chat and do not record outcomes the browser cannot observe.

## AGENT-043 Citation Rendering And Navigation
- Status: todo
- Completion: artifact
- Priority: P1
- Track: graphrag
- Depends on: AGENT-020, AGENT-040
- Outputs: wallet_interface/ui/src/components/agent/AgentEvidencePanel.tsx, wallet_interface/ui/src/components/agent/AgentCitationLink.tsx
- Validation: npm --prefix wallet_interface/ui run build
- Acceptance: GraphRAG citations in chat render as inspectable evidence with source URLs, CIDs, and route hooks for service detail when available.

## AGENT-050 Prompt Redaction Guards
- Status: todo
- Completion: artifact
- Priority: P0
- Track: privacy
- Depends on: AGENT-031
- Outputs: wallet_interface/ui/src/agent/promptGuards.ts
- Validation: npm --prefix wallet_interface/ui run build
- Acceptance: Private wallet context, precise location, private notes, document contents, provider conversations, and raw query history are excluded from prompts unless explicitly allowed.

## AGENT-051 Permission Gate Matrix
- Status: todo
- Completion: artifact
- Priority: P0
- Track: privacy
- Depends on: AGENT-034, AGENT-050
- Outputs: wallet_interface/ui/src/agent/permissionPolicy.ts
- Validation: npm --prefix wallet_interface/ui run build
- Acceptance: Tool execution enforces `read_public`, `read_wallet_summary`, `write_wallet`, and `share_or_disclose` levels with confirmation and audit requirements.

## AGENT-052 Private Context Consent UI
- Status: todo
- Completion: artifact
- Priority: P1
- Track: privacy
- Depends on: AGENT-022, AGENT-051
- Outputs: wallet_interface/ui/src/components/agent/PrivateContextConsentCard.tsx
- Validation: npm --prefix wallet_interface/ui run build
- Acceptance: Abby asks before using private wallet summaries, saved services, uploaded document summaries, eligibility notes, location, or recipients in a response.

## AGENT-053 Agent Privacy Tests
- Status: todo
- Completion: artifact
- Priority: P0
- Track: privacy
- Depends on: AGENT-050, AGENT-051
- Outputs: wallet_interface/ui/tests/agent-privacy.spec.ts
- Validation: npm --prefix wallet_interface/ui test -- tests/agent-privacy.spec.ts
- Acceptance: Tests prove private notes, precise location, document text, raw query history, and revoked grants are unavailable to prompts/tools unless policy allows them.

## AGENT-060 Route Navigation Tools
- Status: todo
- Completion: artifact
- Priority: P0
- Track: agent
- Depends on: AGENT-034
- Outputs: wallet_interface/ui/src/agent/tools/navigationTools.ts
- Validation: npm --prefix wallet_interface/ui run build
- Acceptance: Chat can navigate to all current `RouteId` surfaces and summarize the current screen through safe surface context.

## AGENT-061 Registration And Check-In Tools
- Status: todo
- Completion: artifact
- Priority: P1
- Track: agent
- Depends on: AGENT-034, AGENT-051
- Outputs: wallet_interface/ui/src/agent/tools/registrationTools.ts, wallet_interface/ui/src/agent/tools/checkInTools.ts
- Validation: npm --prefix wallet_interface/ui run build
- Acceptance: Chat can update registration/check-in drafts and submit high-impact changes only after explicit confirmation.

## AGENT-062 Contacts And Sharing Rules Tools
- Status: todo
- Completion: artifact
- Priority: P1
- Track: wallet
- Depends on: AGENT-034, AGENT-051
- Outputs: wallet_interface/ui/src/agent/tools/contactTools.ts, wallet_interface/ui/src/agent/tools/sharingRuleTools.ts
- Validation: npm --prefix wallet_interface/ui run build
- Acceptance: Chat can add/edit recipients, preview scopes, and stage scope changes while requiring confirmation for deletion, expansion, or disclosure.

## AGENT-063 Upload Guidance Tools
- Status: todo
- Completion: artifact
- Priority: P1
- Track: wallet
- Depends on: AGENT-034, AGENT-051
- Outputs: wallet_interface/ui/src/agent/tools/uploadTools.ts
- Validation: npm --prefix wallet_interface/ui run build
- Acceptance: Chat can guide uploads, classify user-selected files, and repair storage without silently reading local files.

## AGENT-064 Shelter Tools
- Status: todo
- Completion: artifact
- Priority: P2
- Track: wallet
- Depends on: AGENT-034, AGENT-051
- Outputs: wallet_interface/ui/src/agent/tools/shelterTools.ts
- Validation: npm --prefix wallet_interface/ui run build
- Acceptance: Shelter account and contact-request actions are staged with confirmation and reuse existing shelter UI state/action contracts.

## AGENT-065 Recipient Access Tools
- Status: todo
- Completion: artifact
- Priority: P0
- Track: wallet
- Depends on: AGENT-034, AGENT-051
- Outputs: wallet_interface/ui/src/agent/tools/recipientAccessTools.ts
- Validation: npm --prefix wallet_interface/ui run build
- Acceptance: Chat can approve, reject, revoke, view, analyze, and delegate only when active grants, abilities, threshold approvals, output policies, and user-presence checks allow it.

## AGENT-066 Proof Center Tools
- Status: todo
- Completion: artifact
- Priority: P1
- Track: wallet
- Depends on: AGENT-034, AGENT-051
- Outputs: wallet_interface/ui/src/agent/tools/proofTools.ts
- Validation: npm --prefix wallet_interface/ui run build
- Acceptance: Chat can explain proof receipts and stage proof creation with explicit claim, verifier, witness label, confirmation, and audit behavior.

## AGENT-067 Export And Security Tools
- Status: todo
- Completion: artifact
- Priority: P1
- Track: wallet
- Depends on: AGENT-034, AGENT-051
- Outputs: wallet_interface/ui/src/agent/tools/exportTools.ts, wallet_interface/ui/src/agent/tools/securityTools.ts
- Validation: npm --prefix wallet_interface/ui run build
- Acceptance: Chat can stage export bundle creation/import and wallet snapshot save/restore with high-risk confirmation and audit-safe summaries.

## AGENT-068 Analytics And Audit Tools
- Status: todo
- Completion: artifact
- Priority: P1
- Track: wallet
- Depends on: AGENT-034, AGENT-051
- Outputs: wallet_interface/ui/src/agent/tools/analyticsTools.ts, wallet_interface/ui/src/agent/tools/auditTools.ts
- Validation: npm --prefix wallet_interface/ui run build
- Acceptance: Chat can explain privacy budgets, stage analytics consent, search audit events, and summarize audit history without exposing private notes.

## AGENT-070 Saved Service And Plan Tools
- Status: todo
- Completion: artifact
- Priority: P1
- Track: graphrag
- Depends on: AGENT-041, AGENT-051
- Outputs: wallet_interface/ui/src/agent/tools/servicePlanTools.ts
- Validation: npm --prefix wallet_interface/ui run build
- Acceptance: Chat can save a service, create a plan, add checklist items, set reminders, and record service interactions through wallet-backed operations after confirmation.

## AGENT-071 Service Detail Route Integration
- Status: todo
- Completion: artifact
- Priority: P2
- Track: graphrag
- Depends on: AGENT-043
- Outputs: wallet_interface/ui/src/agent/tools/serviceDetailTools.ts
- Validation: npm --prefix wallet_interface/ui run build
- Acceptance: When service detail routes exist, chat citations and open-detail actions navigate to the canonical route instead of duplicating detail rendering.

## AGENT-080 Agent Unit Tests
- Status: todo
- Completion: artifact
- Priority: P0
- Track: ops
- Depends on: AGENT-034, AGENT-050, AGENT-051
- Outputs: wallet_interface/ui/tests/agent-unit.spec.ts
- Validation: npm --prefix wallet_interface/ui test -- tests/agent-unit.spec.ts
- Acceptance: Unit tests cover schema validation, deterministic planner routing, permission gates, confirmation requirements, prompt redaction, and GraphRAG evidence-to-action mapping.

## AGENT-081 Agent Smoke Tests
- Status: todo
- Completion: artifact
- Priority: P1
- Track: ops
- Depends on: AGENT-020, AGENT-040, AGENT-060
- Outputs: wallet_interface/ui/tests/agent-chat-smoke.spec.ts
- Validation: npm --prefix wallet_interface/ui test -- tests/agent-chat-smoke.spec.ts
- Acceptance: Playwright verifies opening chat, asking for food pantry evidence, navigating by chat, and requiring confirmation before saving the first result.

## AGENT-082 Accessibility And Mobile Review
- Status: todo
- Completion: artifact
- Priority: P2
- Track: ops
- Depends on: AGENT-021, AGENT-022
- Outputs: docs/AI_AGENT_CHAT_ACCESSIBILITY_REVIEW.md
- Validation: npm --prefix wallet_interface/ui test -- tests/smoke.spec.ts
- Acceptance: Keyboard, focus, screen-reader, reduced-motion, and mobile viewport behavior for chat drawer/bottom sheet and confirmation cards are reviewed.

## AGENT-083 Agent Threat Model And Runbook
- Status: todo
- Completion: artifact
- Priority: P1
- Track: ops
- Depends on: AGENT-051, AGENT-053
- Outputs: docs/AI_AGENT_CHAT_THREAT_MODEL.md, docs/AI_AGENT_CHAT_RUNBOOK.md
- Validation: pytest tests/test_portal_implementation_daemon.py -q
- Acceptance: Operational guidance documents model boundaries, confirmation policy, private-context handling, troubleshooting, validation commands, and release gates.

## AGENT-090 Production Readiness
- Status: todo
- Completion: artifact
- Priority: P1
- Track: ops
- Depends on: AGENT-080, AGENT-081, AGENT-082, AGENT-083
- Outputs: data/agent_chat_implementation/release_checklist.json
- Validation: npm --prefix wallet_interface/ui run build; npm --prefix wallet_interface/ui test -- tests/agent-chat-smoke.spec.ts
- Acceptance: Agent chat can ship with deterministic fallback, public GraphRAG answers, route navigation, confirmation-gated write tools, privacy tests, and documented operating procedures.
