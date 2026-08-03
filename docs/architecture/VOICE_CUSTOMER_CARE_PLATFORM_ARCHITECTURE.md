# Reusable Voice Customer-Care Platform Architecture

## Outcome

Build a reusable client-intake and customer-care framework on top of the
existing voice router, response DAG, and GraphRAG implementation. A deployment
loads an immutable domain pack instead of embedding 211-specific knowledge or
routes in the engine. The same runtime must support a 211 navigator, a general
help desk, an appointment line, an internal operations assistant, or another
reviewed use case without forking the orchestration code.

The platform accepts voice, chat, web-form, or operator input; advances a typed
conversation state; retrieves grounded knowledge and response frames; proposes
zero or more actions; obtains required authorization or confirmation; invokes
an allowlisted adapter; and returns a content-addressed receipt. Supported
action targets include:

- MCP or MCP++ tools;
- argv-based CLI tools;
- registered Python functions or class methods;
- durable local or P2P workflows;
- `ipfs_accelerate_py.agent_supervisor` control operations;
- a real-human queue or telephone transfer.

Graph retrieval is never execution authority. Retrieved text, examples, and
domain-pack content can identify an action descriptor, but cannot introduce an
executable command, import path, credential, or permission.

The existing `ipfs_datasets_py.logic.intent_ir` invocation envelope is the
preferred pre-dispatch authority boundary. The generic action proposal is
adapted into Intent IR with tenant, actor, audience, tool/schema identity,
argument commitment, scopes, rollback, verification, nonce, deadline, and
trace bindings. The action runtime does not invent a second, weaker
authorization envelope.

## Existing foundation and gaps

| Existing asset | Reuse | Gap to close |
| --- | --- | --- |
| `ipfs_accelerate_py/ipfs_accelerate_py/voice_router.py` | Typed STT, GraphRAG retrieval, grounded rendering, TTS, provider fallback, `TelephoneTurnState`, and `process_telephone_turn` | Telephone escalation currently produces metadata; it does not perform or verify a human transfer |
| `ipfs_datasets_py/ipfs_datasets_py/voice/graphrag.py` | Content-addressed graph snapshots, hybrid retrieval, CID-bearing evidence, templates, slots, and safe binding | Public contracts and schema-version names are Abby-specific; there is no generic action node or action-candidate contract |
| `ipfs_datasets_py/ipfs_datasets_py/voice/response_dag.py` | Deterministic append candidates and immutable DAG release artifacts | Node kinds are limited to audio, response, template, and vocabulary |
| `docs/phone_dialog_generation/slotted_response_dag.json` and `docs/211_conversation_dag_shards/` | Intent-to-response examples, grounded-answer, clarification, and live-agent routes | Routes are data-specific and cannot bind reviewed tools or workflows |
| Unified MCP/MCP++ server | IDL descriptors, UCAN delegation, temporal policy, CID artifacts, event DAGs, workflow tools, CLI tools, and supervisor tools | No voice/customer-care action catalog maps graph references to these capabilities |
| Agent supervisor | Goal/task projection, content-addressed task identity, isolated lanes, validation, proof adapters, and refill | No customer-care program heap or action-runtime contract checks |
| 211 service-navigation portal and wallet | Search, service details, mobile handoffs, plans, interactions, grants, redaction, audit, and offline shell | No shared conversational intake runtime, executable workflow panel, or human-agent console |

## Package ownership

The implementation must keep dependency direction explicit.

| Owner | Responsibility |
| --- | --- |
| `ipfs_datasets_py` | Generic domain-pack schemas, deterministic compiler, conversation/action graph, GraphRAG indexes, evidence and slot binding, pack validation, and migration adapters from Abby/211 rows |
| `ipfs_accelerate_py` | Action contracts, action catalog, policy and consent gates, adapters, durable invocation, idempotency, receipts, dialogue/action orchestration, telephony bridge, and supervisor bridge |
| `ipfs_kit_py` | Optional content-addressed artifact storage, pinning, VFS-backed private/session storage adapters, and CID verification; core imports remain optional |
| 211-AI / `wallet_interface` | Reusable portal shell, intake forms, operator console, wallet-private case state, and the 211 reference domain pack |
| Domain pack | Knowledge sources, ontology, intents, response frames, forms, action references, policy overlays, evaluations, localization, and branding; never executable implementation |

`ipfs_datasets_py` must not import `ipfs_accelerate_py`. The accelerator consumes
datasets contracts through small protocols and lazy adapters. Portal code talks
to a transport-neutral service boundary rather than importing provider
implementations.

## Runtime flow

```text
channel adapter (telephone, web, chat, operator)
  -> InteractionRequest + SessionState
  -> STT when input is audio
  -> domain-pack GraphRAG retrieval
  -> grounded response candidate + action proposals
  -> deterministic graph/slot/guard validation
  -> policy + capability + consent decision
       -> ask a clarifying question
       -> request explicit confirmation
       -> invoke an action adapter
       -> create a human handoff
       -> deny and provide a safe explanation
  -> action result/evidence updates conversation state
  -> grounded spoken/display response
  -> TTS when the channel needs audio
  -> InteractionReceipt + ActionReceipt(s) + next immutable state
```

The retrieval and execution portions are separated by an explicit proposal
boundary. No adapter is called while parsing a domain pack or retrieving a
GraphRAG result.

## Domain-pack contract

`DomainPackManifestV1` is canonical JSON whose CID covers every referenced
artifact. It contains:

- `pack_id`, semantic version, schema version, build identity, and root CID;
- supported locales, channels, accessibility metadata, and presentation
  configuration;
- knowledge-source manifests and freshness policies;
- ontology, intent, entity, response-frame, and form-schema artifacts;
- compiled conversation/action graph and retrieval indexes;
- action references to catalog descriptors by stable ID and descriptor CID;
- policy overlays that may only narrow deployment policy;
- synthetic/public evaluation fixtures and expected outcomes;
- migration and compatibility metadata.

Swapping data means selecting another pinned domain-pack CID. It does not mean
changing Python imports, tool registration, or deployment secrets. A pack may
refer only to action IDs present in the deployment action catalog. A pack
cannot define raw shell commands, Python import paths, MCP endpoints, bearer
tokens, or environment variables.

Builds are deterministic. The same normalized inputs, compiler version, and
policy profile must yield byte-identical artifacts and the same root CID.
Unknown schema versions, dangling edges, duplicate IDs, unbounded cycles,
unbound required slots, missing evidence, and unknown action references fail
closed.

## Conversation/action graph

The generic graph supports these node kinds:

- `intent`: classified caller or operator purpose;
- `evidence_query`: a bounded retrieval operation;
- `response_frame`: grounded text/display plan;
- `form`: typed intake fields, validation, consent, and disclosure copy;
- `decision`: a deterministic guard over typed session facts;
- `action_ref`: reference to a registered action descriptor;
- `confirmation`: channel-appropriate explicit-confirmation prompt;
- `handoff`: human queue or transfer request;
- `terminal`: completed, safely denied, abandoned, or failed outcome.

Edges contain a stable ID, source, target, edge kind, priority, and a typed,
side-effect-free guard AST. Arbitrary Python, JavaScript, template evaluation,
or shell expansion is prohibited. The compiler proves that required slots are
defined on every admitted path, action nodes are reachable only after their
policy prerequisites, and terminal or handoff behavior exists for failure and
timeout paths.

The persisted content graph remains acyclic. Repeated dialogue is represented
by immutable per-turn state transitions or a bounded loop primitive expanded
by the compiler. This keeps graph proofs and replay finite.

## Action contracts

### ActionDescriptor

An action descriptor declares:

- stable `action_id`, version, descriptor CID, owner, and transport kind;
- input and output JSON Schema CIDs;
- exact MCP IDL/tool identity, argv executable identity, callable registration
  key, workflow identity, supervisor operation, or human queue identity;
- capability requirements and tenant/channel allowlists;
- risk class, side-effect class, consent and confirmation requirements;
- timeout, retry, idempotency, concurrency, and rate policies;
- optional compensation action;
- redaction, retention, audit, and user-facing status metadata.

The catalog is deployment-owned and allowlisted. Domain packs can reference but
cannot widen it.

### ActionProposal

GraphRAG and the deterministic router may emit an `ActionProposal` containing:

- descriptor ID and CID;
- source graph/pack/node identities;
- proposed arguments with per-field provenance;
- confidence, intent, evidence CIDs, and missing fields;
- actor, tenant, session, channel, and correlation identities;
- requested deadline and a content-derived idempotency key.

The proposal contains no credentials and grants no authority.

### ActionDecision

The policy engine returns one of:

- `deny`;
- `clarify`;
- `confirm`;
- `handoff`;
- `permit_read`;
- `permit_execute`.

The decision binds the exact descriptor CID, normalized arguments hash,
capabilities, consent receipt, policy revision, risk class, expiry, and
decision reason. A stale decision cannot authorize a changed descriptor or
argument set. Where `ipfs_datasets_py.logic.intent_ir` is available, admission
must validate and preserve its pre-dispatch envelope and receipt rather than
dispatching by a bare tool name.

### ActionInvocation and ActionReceipt

An invocation is created only from a valid permit. The receipt records:

- proposal, decision, descriptor, pack, session, and parent receipt CIDs;
- selected adapter and exact interface identity;
- started/completed times and normalized terminal status;
- redacted input/output hashes and approved public result fields;
- attempt, timeout, retry, idempotency, and compensation information;
- provider-native receipt or transfer confirmation when available;
- event-DAG parent identities and a receipt CID.

Receipt status distinguishes `accepted`, `started`, `succeeded`, `failed`,
`timed_out`, `cancelled`, `unknown`, and `compensated`. The UI and voice layer
must never translate an accepted handoff or OS-level intent into a completed
external outcome.

## Adapter boundaries

### MCP and MCP++

Discover capabilities and retrieve the canonical interface descriptor before
admission. Bind the action descriptor to the MCP tool name, input/output
schemas, server identity, profile, and IDL CID. MCP++ execution uses existing
UCAN, temporal-policy, artifact, and event-DAG controls. Descriptor drift,
profile downgrade, or an incompatible output is a typed failure.

### CLI

Resolve a registered executable to an absolute reviewed path and construct an
argv vector. Never use `shell=True`, string interpolation, inherited arbitrary
environment variables, or a caller-controlled working directory. Apply
resource limits, a sandbox profile, output bounds, timeout, and redaction.
Mutating CLI actions require explicit idempotency and compensation policy.

### Python function or class method

Resolve a registration key from an in-memory catalog. Do not import a
caller-supplied module, evaluate source, or use arbitrary attribute traversal.
Validate arguments and results, inject reviewed dependencies, and enforce
timeout/cancellation. Methods with hidden global side effects are not
registrable until wrapped by a typed adapter.

### Durable workflow

Submit a versioned workflow descriptor to the existing local/P2P workflow
surface. Return a durable workflow identity immediately, correlate later
events, and project terminal state into an action receipt. Workflow retries
must preserve the original idempotency key.

### Agent supervisor

Expose a narrow adapter over `SupervisorControlService`. Initially allow
read-only discovery/status plus explicitly reviewed objective-refine,
backlog-refill, start, pause, resume, drain, retry, and validation-replay
operations. Starting implementation work is high risk: it requires a pinned
objective/task identity, repository scope, capacity admission, and explicit
operator or policy authority. Voice input alone cannot authorize code changes.

Program implementation lanes use the supervisor's `auto` provider policy:
dispatch-ready Grok is preferred and Codex is the pre-dispatch fallback.
Generated tasks use the soft `grok, codex-review` role; the hard
`grok-implement` role is reserved for deliberately pinned work. Once a provider
starts, failures return through retry, validation, and admission gates rather
than cascading into a second model in the same mutable worktree.

### Human handoff and telephone transfer

Create a `HandoffRequest` with reason, priority, skills/queue, safe summary,
consent scope, preferred channel, session receipt CID, and expiry. A telephone
adapter may enqueue, bridge, or transfer the call, but reports success only
after a provider-native confirmation. If transfer is unavailable, preserve the
queue request and tell the caller the precise degraded state. Crisis and
emergency behavior is a separately reviewed policy overlay.

## Session, intake, and case state

The engine owns a minimal `SessionState`: pinned domain-pack CID, channel,
locale, current graph node, turn index, collected typed slots, consent
receipts, action receipts, handoff status, and privacy-safe hashes. It does not
store raw audio by default.

Private customer-care state belongs behind a `CaseStore` protocol. The 211
reference deployment can adapt this to the wallet models already used for
saved services, plans, interactions, grants, and HMIS consent. A different
deployment may use an encrypted database or an external CRM adapter. Public
GraphRAG indexes and domain packs must never contain private intake answers,
transcripts, precise location, case notes, credentials, or action outputs.

Form fields declare data class, purpose, necessity, retention, validation,
disclosure, and whether collection is optional. Sensitive fields are requested
only when an admitted workflow requires them. Session receipts store hashes or
approved projections; private values remain in the selected case store.

## Policy and safety invariants

- Retrieval never grants execution authority.
- Data packs may narrow but never widen deployment policy.
- Every action argument is schema-valid and provenance-bound.
- Missing or stale capabilities, consent, confirmation, or descriptor identity
  fails closed.
- Read-only, reversible, irreversible, financial, identity, code-changing, and
  emergency actions have distinct risk classes.
- Irreversible or externally consequential actions require explicit
  confirmation unless a reviewed non-interactive policy says otherwise.
- Prompt injection in retrieved documents cannot select a raw tool, command,
  callable, policy, or credential.
- Secrets are resolved inside adapters and excluded from graphs, prompts,
  sessions, logs, errors, receipts, and analytics.
- Tenant, domain-pack, case, and session identities participate in cache and
  idempotency keys.
- Replays cannot repeat a non-idempotent side effect.
- Every failure path has a truthful user-facing state and a safe handoff or
  terminal route.
- Private voice audio and transcripts are ephemeral unless explicit consent
  and a reviewed retention policy authorize storage.

## Portal surfaces

The reusable portal shell provides:

- channel and domain-pack bootstrap;
- conversational intake and typed dynamic forms;
- grounded answer/provenance display;
- pending-action review and explicit confirmation;
- action/workflow status timeline;
- saved case/service plans and follow-up tasks;
- human handoff request and queue status;
- operator console with redacted context and disposition;
- accessibility, localization, mobile, and offline-safe public shell behavior.

Branding, navigation labels, form definitions, response frames, knowledge,
actions visible to users, and evaluation fixtures come from the selected
domain pack. Authorization, adapter registration, secrets, and risk ceilings
remain deployment configuration.

## Verification strategy

Validation is layered:

1. Schema and compiler tests prove canonicalization, CID stability, graph
   integrity, data-pack isolation, and migration compatibility.
2. Adapter contract tests use fake MCP, CLI, callable, workflow, supervisor,
   telephony, and human-queue transports.
3. Property and state-machine tests prove no execution before permit, no
   changed-argument replay, bounded retries, truthful status, and compensation
   behavior.
4. Formal checks encode graph reachability, consent-before-side-effect,
   confirmation-before-high-risk-action, tenant non-interference, and terminal
   failure paths for the available `ipfs_datasets_py.logic` providers. Intent
   IR conformance is a focused gate for every executable binding.
5. Security tests cover prompt injection, confused deputy, argument injection,
   command injection, SSRF, secret leakage, replay, cross-tenant cache
   poisoning, stale IDL, and malicious domain packs.
6. Two end-to-end domain packs—211 and a small non-211 fixture—run the same
   engine without conditional application code.
7. Telephone tests distinguish request, queue acceptance, provider transfer,
   connected human, failure, and unknown outcomes.

## Migration and compatibility

Migration is additive:

1. Freeze existing Abby voice, GraphRAG, response-DAG, wallet voice adapter,
   and portal tests as compatibility gates.
2. Introduce generic contracts beside existing Abby-named contracts.
3. Add lossless adapters from Abby voice rows and the current 211 DAG into a
   `211-ai` domain pack.
4. Route `process_voice_turn` and `process_telephone_turn` through the generic
   orchestrator only behind an explicit feature flag.
5. Compare old/new response text, provenance, fallback, cache, and audio
   behavior offline.
6. Canary read-only and human-handoff routes before enabling tool execution.
7. Enable each mutating action descriptor independently with rollback to
   response-only behavior.

No migration step may require a mutable remote dataset reference or silently
persist caller media.
