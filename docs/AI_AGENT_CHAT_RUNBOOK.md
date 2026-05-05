# AI Agent Chat Runbook

This runbook covers operating, validating, troubleshooting, and releasing the
Abby agent chat described in `docs/AI_AGENT_CHAT_IMPLEMENTATION_PLAN.md` and
`docs/AI_AGENT_CHAT_THREAT_MODEL.md`.

## Baseline

The agent must run as a controlled app surface, not as an independent data path.

Required baseline:

- Public 211 search and answers use the existing browser GraphRAG path:
  `wallet_interface/ui/src/services/graphRagService.ts` and
  `wallet_interface/ui/public/corpus/211-info/current`.
- App-control operations use typed commands, `surfaceRegistry.ts`,
  `surfaceApi.ts`, app actions, and `toolExecutor.ts`.
- Permission gates come from `permissionPolicy.ts`:
  `read_public`, `read_wallet_summary`, `write_wallet`, and
  `share_or_disclose`.
- Prompt construction uses `agentConversation.ts` and `promptGuards.ts`.
- Private context is disabled by default. The UI must show a consent request
  before using private wallet summaries, saved services, uploaded document
  summaries, eligibility notes, location, recipients, grants, or proof metadata.
- Raw chat transcripts are not persisted by default.
- Wallet writes, disclosure, grant, proof, export, analytics-consent,
  location-use, outbound-contact, and destructive operations require explicit
  confirmation before execution.

## Standard Validation

Run the task-level validation before merging AGENT-083 changes:

```bash
pytest tests/test_portal_implementation_daemon.py -q
```

Run the broader agent validation before release or after changing agent policy,
prompting, tools, or wallet integrations:

```bash
npm --prefix wallet_interface/ui run build
npm --prefix wallet_interface/ui test -- tests/agent-unit.spec.ts
npm --prefix wallet_interface/ui test -- tests/agent-privacy.spec.ts
npm --prefix wallet_interface/ui test -- tests/agent-action-convergence.spec.ts
npm --prefix wallet_interface/ui test -- tests/agent-chat-smoke.spec.ts
```

Run wallet/API validation when a change touches wallet-backed records, grants,
proofs, exports, analytics consent, audit, or storage behavior:

```bash
pytest tests/test_wallet_interface_api.py tests/test_wallet_interface_ops.py tests/test_wallet_interface_proof_backends.py -q
python -m wallet_interface.ops --validate-production-readiness
```

## Release Gates

Do not release agent chat unless every gate below passes in the target
environment or has an approved launch exception.

1. Build and tests pass:
   - UI build.
   - Agent unit tests.
   - Agent privacy tests from AGENT-053.
   - Agent action-convergence tests.
   - Agent chat smoke tests.
   - Wallet/API tests for any wallet-backed change.
2. Deterministic fallback is usable:
   - Chat opens without a local LLM.
   - Public service questions return cited 211 evidence or missing-fact
     guidance.
   - Route navigation works from chat.
   - Confirmation responses execute or cancel staged calls deterministically.
3. Confirmation gates are active:
   - `write_wallet` and `share_or_disclose` tools render confirmation cards.
   - Confirmations show safe summaries of target, scope, risk, and audit
     behavior.
   - Denied, expired, or canceled confirmations do not execute the tool.
4. Private-context controls are active:
   - Private context is absent from prompts by default.
   - Prompt guards redact private notes, precise location, document text,
     provider conversations, and raw query history unless explicitly allowed.
   - Optional private memory is wallet-backed and can be disabled or deleted.
5. Wallet and disclosure checks are reused:
   - Tools do not bypass wallet authorization, grant caveats, proof contracts,
     export controls, analytics consent, or audit creation.
   - Revoked or expired grants fail at execution time.
6. Operational docs are current:
   - This runbook and `docs/AI_AGENT_CHAT_THREAT_MODEL.md` describe new tools,
     model boundaries, private-context handling, and release gates.
   - Wallet-specific launch evidence follows `docs/WALLET_OPERATIONS_RUNBOOK.md`
     and `docs/WALLET_TARGET_PRODUCTION_SIGNOFF.md`.

## Troubleshooting

### Chat Drawer Does Not Open

1. Run `npm --prefix wallet_interface/ui run build`.
2. Check that the chat component imports `agentChatService.ts` rather than
   planner or executor internals.
3. Verify route state is available from `wallet_interface/ui/src/app/appState.ts`
   and route IDs match `wallet_interface/ui/src/models/abby.ts`.
4. Check browser console errors for component import, provider, or CSS failures.

### Public 211 Answer Has No Citations

1. Confirm the corpus exists under
   `wallet_interface/ui/public/corpus/211-info/current`.
2. Run the browser GraphRAG or smoke test that asks a public service question.
3. Confirm the agent used `build211InfoEvidence` or `answer211InfoQuestion`.
4. If evidence is missing, the response must say which fact is missing and
   recommend verification with 211 or the provider. Do not patch around this by
   adding uncited model prose.

### Model Is Unavailable Or WebGPU Fails

1. Confirm the deterministic planner still handles route navigation, public
   service questions, current-screen summaries, and confirmation responses.
2. Treat local LLM failure as quality degradation, not a production outage, for
   core workflows.
3. Inspect worker initialization errors in `clientLLMWorker.ts`,
   `clientLLMWorkerService.ts`, and backend detection logs.
4. Do not enable server-side private-context processing as a quick workaround.
   It requires target review and release signoff.

### Tool Call Is Rejected

1. Check the tool name is registered in `commandSchemas.ts` and
   `surfaceRegistry.ts`.
2. Validate input shape against the command schema.
3. Check `permissionPolicy.ts` for required permission, wallet unlock,
   user-presence, private-context opt-in, confirmation, and audit flags.
4. Confirm the current route is in the tool's allowed surfaces.
5. If the rejection is correct, show the policy message to the user and offer a
   lower-risk alternative, such as reading public service evidence first.

### Confirmation Card Does Not Appear

1. Verify the tool definition has `requiresConfirmation=true` for
   `write_wallet` or `share_or_disclose`.
2. Check that `toolExecutor.ts` returns a pending confirmation rather than
   executing immediately.
3. Confirm the chat controller stores the pending confirmation and the UI renders
   `AgentConfirmationCard`.
4. Run:

   ```bash
   npm --prefix wallet_interface/ui test -- tests/agent-unit.spec.ts
   npm --prefix wallet_interface/ui test -- tests/agent-action-convergence.spec.ts
   ```

### Private Context Appears In A Prompt

Treat this as a privacy incident until proven to be a test-only fixture.

1. Stop release rollout for the affected build.
2. Capture the failing prompt in a secure development artifact. Do not paste it
   into public issue trackers, logs, or chat.
3. Identify the category: private wallet context, precise location, private
   notes, document contents, provider conversations, or raw query history.
4. Check `promptGuards.ts` allowances and the call site options passed to
   `buildAgentConversationPrompt`.
5. Add or update AGENT-053 privacy coverage:

   ```bash
   npm --prefix wallet_interface/ui test -- tests/agent-privacy.spec.ts
   ```

6. Confirm raw transcripts, screenshots, browser cache, and telemetry did not
   retain the sensitive content.
7. If a wallet record, grant, proof, export, or analytics consent was affected,
   follow `docs/WALLET_OPERATIONS_RUNBOOK.md` privacy incident guidance.

### Wallet Write Or Disclosure Runs Without Confirmation

Treat this as a release blocker.

1. Disable the affected tool registration or hide the affected chat action.
2. Add a regression test that stages the operation and expects a pending
   confirmation.
3. Verify the tool's policy gate is `write_wallet` or `share_or_disclose`.
4. Check the executor path for direct `surfaceApi` calls that skip confirmation.
5. Re-run agent unit, privacy, action-convergence, and smoke tests.
6. Review audit events for unintended writes or disclosures and follow the
   wallet runbook for revocation, export, proof, or analytics impact.

### Saved Services, Plans, Or Interactions Do Not Persist

1. Confirm the GUI and chat both call the same app action or wallet API method.
2. Check whether the current milestone uses local UI state or wallet-backed
   endpoints from `docs/211_SERVICE_NAVIGATION_PORTAL_PLAN.md`.
3. For production readiness, private service state must persist through
   encrypted wallet records or API-backed wallet state, not localStorage.
4. Re-run action-convergence tests for the affected workflow.

## Incident Severity

| Severity | Examples | Immediate action |
| --- | --- | --- |
| P0 | Private context sent to an unapproved server-side model, disclosure executes without confirmation, export/proof leaks witness or raw document data | Stop rollout, disable affected tool, preserve secure evidence, follow wallet incident procedures. |
| P1 | Prompt redaction regression in local-only path, revoked grant selectable by chat, confirmation card missing risk/scope summary | Block release, patch policy/tests, re-run release gates. |
| P2 | Local LLM unavailable but deterministic fallback works, citation panel rendering issue with evidence still present | Keep fallback active, fix before next release if user impact is material. |
| P3 | Non-sensitive copy, layout, or troubleshooting doc issue | Patch through normal review. |

## Operational Logs And Audit

Do log:

- Tool name, status, confirmation ID/status, permission gate, safe target labels,
  route, audit event ID, and error code.
- GraphRAG corpus version or content CID for public evidence.
- Redaction categories and counts, without redacted values.

Do not log:

- Raw prompts or full chat transcripts.
- Private notes, document text, OCR output, precise location, provider
  conversations, wallet secrets, proof witnesses, export contents, or raw query
  history.
- Grant tokens, decrypted records, API credentials, or storage URLs containing
  secrets.

## Rollback

Use the smallest rollback that restores policy compliance:

1. Disable the affected tool in `surfaceRegistry.ts` or remove it from available
   tools for the route.
2. Fall back to deterministic read-only chat if model/tool-call reliability is
   the issue.
3. Disable private-context allowances while keeping public 211 answers and route
   navigation available.
4. If wallet writes or disclosures are affected, pause the relevant GUI and chat
   workflow together because they should share the same action contract.
5. Re-run validation before re-enabling the tool.

## Launch Checklist

Before marking an agent release ready:

- `docs/AI_AGENT_CHAT_THREAT_MODEL.md` matches implemented tools and model
  deployment mode.
- Confirmation and private-context copy has been reviewed for high-risk tools.
- AGENT-051 permission gates and AGENT-053 privacy tests are passing.
- Accessibility and mobile review has no P0/P1 blockers for chat drawer,
  bottom sheet, confirmation cards, and consent cards.
- Wallet production readiness is complete for any wallet-backed release.
- On-call or support staff can find this runbook, the wallet runbook, validation
  commands, rollback instructions, and privacy incident steps.
