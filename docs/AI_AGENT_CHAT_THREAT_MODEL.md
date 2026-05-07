# AI Agent Chat Threat Model

Status: operational guidance for AGENT-083. This document applies to the Abby
agent chat surfaces described in `docs/AI_AGENT_CHAT_IMPLEMENTATION_PLAN.md`.

## Scope

The agent is another controller for the 211 service-navigation portal and
wallet UI. It may answer public 211 corpus questions, navigate app routes,
stage typed app actions, and execute confirmed operations through the same
surface API used by GUI workflows.

In scope:

- Browser GraphRAG over `wallet_interface/ui/public/corpus/211-info/current`.
- Local client LLM worker and deterministic planner fallback.
- Agent prompt construction, prompt guards, tool registry, permission policy,
  tool executor, confirmation cards, and audit metadata.
- Wallet-backed private records, grants, proofs, exports, analytics consent,
  saved services, service plans, and service interactions when exposed as tools.

Out of scope:

- Replacing wallet cryptography, UCAN authorization, proof validation, encrypted
  storage, or audit semantics. Those remain owned by the wallet layer and the
  wallet runbooks.
- Letting the model bypass typed command schemas or mutate React state directly.
- Treating public 211 corpus evidence as private. User interactions with that
  corpus are private.

## Trust Boundaries

| Boundary | Trusted component | Untrusted or constrained component | Required control |
| --- | --- | --- | --- |
| Public retrieval | Static 211 corpus, citation metadata, GraphRAG service wrapper | User prompt and generated prose | Cite public facts, mark missing facts, never invent phone, address, hours, eligibility, proof, grant, or audit facts. |
| Prompt building | `agentConversation.ts` and `promptGuards.ts` | Conversation history, tool outputs, raw query history, screen metadata | Redact private categories by default and compact history before model use. |
| Tool choice | Deterministic planner, registered tool definitions, command schemas | Local LLM output | Treat model output as a proposal only; validate schema and permission policy before execution. |
| Tool execution | `toolExecutor.ts`, `surfaceApi.ts`, app actions, wallet API | Model-generated arguments | Enforce permission gate, wallet unlock, user presence, private-context opt-in, confirmation, and audit requirements. |
| Wallet records | Wallet API and encrypted wallet storage | Chat transcript, model prompt, browser cache, localStorage | Keep private state encrypted; do not persist raw transcripts by default. |
| Disclosure | Wallet grant/proof/export/analytics APIs | Recipient, provider, remote service, downloaded export | Require explicit confirmation, scope summary, audit event, and existing wallet authorization checks. |
| Model runtime | Local browser worker by default | WebGPU model, future server-side model | Keep private context inside the approved execution boundary; server-side private-context mode requires separate review. |

## Data Classification

Public data:

- 211 scraped service text, provider/program details, source URLs, CIDs,
  provenance, and public service contact/location fields.

Private wallet data:

- Saved services, service plans, notes, reminders, documents, precise location,
  check-in history, worker assignments, calls/text intents, provider
  interactions, recipients, grants, revocations, proof witnesses, export bundle
  contents, analytics consent, and audit details tied to a wallet.

Sensitive prompt categories redacted by default:

- Private wallet context.
- Precise location.
- Private notes.
- Document contents or OCR text.
- Provider conversations or message transcripts.
- Raw query history.

## Model Boundaries

The model is not an authority boundary. It can help summarize evidence and
propose the next typed command, but it cannot grant itself permission or execute
state changes.

Required model boundaries:

- Core workflows must remain usable without a local LLM. Deterministic routing
  handles public service questions, route navigation, current-screen summaries,
  confirmation responses, and common wallet-action staging.
- Local LLM output must be parsed as advisory text or a candidate tool call.
  The executor must validate the command name, input schema, route surface, and
  permission policy before anything runs.
- Public GraphRAG answers must be source-grounded. If retrieved evidence lacks a
  fact, the answer says the fact is missing and suggests contacting 211 or the
  provider.
- Private context can enter a prompt only after explicit user intent, a matching
  private-context allowance, wallet unlock when required, and the minimum
  scoped data retrieval needed for the request.
- Server-side model processing of private wallet context is not approved by this
  runbook unless a target deployment records the execution boundary, retention
  policy, vendor/data-processing terms, redaction rules, and rollback plan.

## Confirmation Policy

Every tool definition must declare its permission level and confirmation
metadata. The policy from AGENT-051 is the operational source of truth.

| Permission level | Examples | Confirmation | Audit |
| --- | --- | --- | --- |
| `read_public` | Search 211 services, answer public corpus questions, navigate routes, read public capability text | Not required | Not required |
| `read_wallet_summary` | Read record labels, grant labels, proof receipt metadata, audit summaries | Not required unless the surface marks it higher risk | Audit only when the wallet API requires it |
| `write_wallet` | Save service, create plan, update check-in policy, create/import export bundle, save/restore snapshot, submit analytics consent | Required before execution | Required for wallet writes |
| `share_or_disclose` | Add or edit recipients, change scopes, approve/reject/revoke access, delegate grants, create proofs, create export bundles, provider contact requests | Required before execution | Required |

Hard rules:

- No destructive, disclosure, location-use, outbound-contact, proof, export,
  analytics-consent, grant, scope-expansion, or wallet-write action executes
  from a single model response.
- A confirmation card must show the command, affected record/service/recipient
  labels when safe, before/after or scope summary, risk level, audit behavior,
  and whether private context will be used.
- Confirmation approval is single-use. Editing tool input, route, target
  wallet, recipient, grant, proof witness, export scope, or analytics study
  requires a new confirmation.
- Denied, expired, or canceled confirmations must leave the tool call canceled
  and must not execute partial writes.
- Restore, export, grant delegation, disclosure-scope expansion, and proof
  creation are restricted operations. The UI should use the strongest warning
  copy available for the route and require visible user presence.

## Private-Context Handling

Private context is opt-in per task, not a blanket session default. The agent may
ask for permission when private data would materially improve the answer.

Required handling:

- Use public 211 retrieval first for mixed public/private questions.
- Ask whether Abby may use specific private context, such as saved services,
  uploaded document summaries, eligibility notes, location, recipients, grants,
  or proof metadata.
- Retrieve the minimum scoped fields needed for the current task. Prefer labels,
  status, coarse location, proof receipt metadata, and derived summaries over
  raw payloads.
- Keep public service evidence and private wallet facts distinct in responses.
- Store private notes, plans, interactions, memory, and saved services as
  encrypted wallet records or API-backed wallet state. Do not store them in
  localStorage.
- Do not persist raw chat transcripts by default. Optional memory requires an
  explicit opt-in, wallet-backed encrypted storage, and a delete/revoke path.
- Do not mirror private notes, precise location, document text, provider
  conversations, or raw query history into public audit logs, telemetry, console
  logs, browser cache, screenshots, or test snapshots.
- Revoked grants cannot be used by chat tools, even if prior chat state still
  references their labels.

## Threats And Mitigations

| Threat | Mitigation |
| --- | --- |
| Prompt injection in 211 corpus text or user messages tells Abby to ignore policy | Treat retrieval text and user text as data, keep policy outside evidence, validate all tool calls through schemas and `permissionPolicy.ts`. |
| Model invents service details | Require cited GraphRAG evidence for public service facts and explicitly state missing fields. |
| Model selects a high-risk tool without user awareness | Tool executor stages the call and renders a confirmation card for `write_wallet` and `share_or_disclose`. |
| Prompt includes private notes, location, document text, provider messages, or raw query history by default | `promptGuards.ts` redacts sensitive categories unless explicit allowances and context gates are present. |
| LLM output bypasses GUI validation | GUI and chat both execute through shared app actions and `surfaceApi.ts`; direct state mutation from chat is disallowed. |
| Disclosure scope is broader than the user expected | Confirmation card summarizes recipients, abilities, resources, purpose, expiration, and output types before grant/export/share actions. |
| Revoked or expired grants are reused | Permission policy and wallet APIs check active grant status and caveats at execution time, not only at planning time. |
| Server-side model receives private context without approval | Server-side private-context mode is release-blocked until separate target review and signoff are recorded. |
| Chat transcript leaks through persistence or telemetry | Raw transcripts are ephemeral by default; logs and audit records use action metadata rather than full prompt/response text. |
| Browser/PWA cache stores private plaintext | Cache only public shell and public service artifacts; wallet-private state remains encrypted wallet storage. |
| Proof or export workflow exposes witness data | Reuse wallet proof/export contracts, show only audit-safe summaries, and validate proof/export tests before release. |
| Emergency, medical, legal, or benefits advice is overconfident | Responses include uncertainty and recommend verification with 211, the listed provider, or qualified professionals. |

## Security Review Checklist

Before a new agent tool ships:

- The tool is registered with command schema, permission level, allowed routes,
  confirmation requirement, wallet unlock requirement, private-context opt-in
  flag, and audit event type where applicable.
- Unit tests cover valid input, invalid input, denied permission, confirmation
  required, canceled confirmation, and successful execution.
- Privacy tests prove sensitive prompt categories are absent unless explicitly
  allowed.
- The confirmation card copy includes safe target labels and no raw private
  payload.
- Wallet writes and disclosures reuse wallet API authorization and audit checks.
- Public responses include citations or missing-fact language.
- The release gate in `docs/AI_AGENT_CHAT_RUNBOOK.md` passes.
