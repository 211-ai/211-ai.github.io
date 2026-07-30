# Reusable Voice Workflow DAG Client Intake and Customer Care Plan

## Outcome

Turn the existing content-addressed Abby voice response DAG and GraphRAG
retrieval system into a reusable, tenant-swappable client-intake and
customer-care framework. The framework must support website chat, browser
voice, telephone, SIP/WebRTC, and operator-assisted sessions while safely
linking a conversation to:

- a grounded response;
- a declarative workflow;
- an MCP++ or conventional MCP tool;
- a fixed CLI capability;
- an injected Python class method;
- an HTTP/webhook capability;
- a narrowly scoped `ipfs_accelerate_py` agent-supervisor operation; or
- a real human, callback queue, or warm transfer.

The same core runtime must serve 211-AI and a second unrelated reference
domain without source changes. Domain behavior belongs in signed,
content-addressed profile packs, not in hard-coded routing branches.

The durable goal heap is
`docs/planning/reusable_voice_workflow_dag_client_care.objectives.md`. The
executable task board is
`docs/planning/reusable_voice_workflow_dag_client_care.todo.md`.

## Starting point

The plan extends these shipped surfaces rather than replacing them:

- `ipfs_datasets_py/ipfs_datasets_py/voice/graphrag.py` provides deterministic
  template/evidence graphs, hybrid retrieval, CIDs, and a router-compatible
  template provider.
- `ipfs_datasets_py/ipfs_datasets_py/voice/response_dag.py` appends validated,
  privacy-safe response/audio candidates.
- `ipfs_accelerate_py/ipfs_accelerate_py/voice_router.py` defines voice-turn,
  telephone-turn, grounded-plan, stage-trace, provider, and provenance
  contracts.
- `ipfs_accelerate_py/ipfs_accelerate_py/voice_response_dag_sink.py` validates
  and queues cache-miss response-DAG candidates.
- `wallet_interface/helpers/_voice_router_adapter.py` is the current
  feature-gated wallet adoption boundary.
- `wallet_interface/ui/src/agent` already has typed tools, confirmation,
  permission, prompt-redaction, service-navigation, and shared GUI/action
  surfaces.
- `wallet_interface/ui/src/services/serviceActionService.ts` and
  `serviceInteractionService.ts` already model browser-initiated service
  actions and interaction intent.
- `docs/planning/211_SERVICE_NAVIGATION_PORTAL_PLAN.md` and
  `docs/planning/AI_AGENT_CHAT_IMPLEMENTATION_PLAN.md` define completed 211
  portal and agent-chat foundations.

The current response DAG is a content and audio lineage graph. It must not be
silently reinterpreted as an executable workflow graph. Compatibility adapters
may connect the two, but their schemas, authority, state machines, and receipts
remain separate.

The initial drift inventory must explicitly reconcile:

- the canonical Python GraphRAG with the generated/browser slotted DAG and
  duplicated TypeScript GraphRAG wrappers;
- Abby-specific response contracts with domain-neutral contracts and explicit
  version converters;
- route strings such as `live_agent` with typed workflow/action semantics;
- the current advisory-only handoff flag with a real, receipted provider
  adapter;
- the browser permission/action model with the backend policy gateway; and
- the generic MCP registry, MCP++ workflow engine, and agent-supervisor native
  tool catalog, whose current trust and authorization strengths differ.

Version negotiation and compatibility converters must replace these parallel
contracts; the program must not introduce a third unowned representation.

## Architectural rule

GraphRAG, a transcript, retrieved text, a response template, or an LLM may
propose an allowlisted logical action. None of them may directly choose an
executable path, shell command, import path, network endpoint, credential, MCP
server, or supervisor mutation.

The trusted execution path is:

```text
channel input
  -> VoiceTurnRequest / STT
  -> tenant and active profile snapshot
  -> grounded GraphRAG response and logical-action candidates
  -> deterministic ActionProposal validation
  -> slot, confidence, risk, consent, authentication, and policy gates
  -> durable workflow transition and fenced execution lease
  -> trusted deployment binding
  -> admitted adapter
  -> normalized result or outcome_unknown
  -> content-addressed action and interaction receipts
  -> grounded response / TTS / portal update / human handoff
```

Retrieval can reduce confidence, ask for clarification, or propose an
allowlisted action. It can never increase authority.

## Four-plane model

### Content plane

Public or tenant-approved facts, intents, response templates, evidence,
citations, locale data, and precomputed audio. This plane is indexed by
`ipfs_datasets_py` and addressed by canonical CIDs.

### Workflow plane

Declarative, finite workflow definitions made from closed node and edge
vocabularies. This plane describes what may happen and under which predicates;
it contains no credentials or arbitrary executable code.

### Authority plane

Operator-signed policies, capability bindings, tenant scopes, consent,
authentication, risk classes, resource limits, and revocation state. Only this
plane can bind a logical action to an executable adapter.

### Session plane

Private caller state, collected fields, conversation turns, workflow
instances, interaction records, handoff context, and grants. It is encrypted,
tenant-isolated, retention-bound, and excluded from public IPFS objects and
public GraphRAG indexes.

## Reusable package boundaries

### `ipfs_datasets_py`

Own domain-neutral data contracts and deterministic indexing:

- `ipfs_datasets_py.voice_workflows.records`
- `ipfs_datasets_py.voice_workflows.content_addressing`
- `ipfs_datasets_py.voice_workflows.profile`
- `ipfs_datasets_py.voice_workflows.compiler`
- `ipfs_datasets_py.voice_workflows.graphrag`
- `ipfs_datasets_py.voice_workflows.authoring`

Responsibilities include profile-pack schemas, canonical DAG-JSON identities,
GraphRAG nodes/edges, pack compilation, compatibility import from Abby rows,
release validation, and public/private index separation.

### `ipfs_accelerate_py`

Own execution, policy, adapters, orchestration, and receipts:

- `ipfs_accelerate_py.voice_workflows.contracts`
- `ipfs_accelerate_py.voice_workflows.engine`
- `ipfs_accelerate_py.voice_workflows.policy`
- `ipfs_accelerate_py.voice_workflows.state`
- `ipfs_accelerate_py.voice_workflows.receipts`
- `ipfs_accelerate_py.voice_workflows.handoff`
- `ipfs_accelerate_py.voice_workflows.adapters`
- `ipfs_accelerate_py.voice_workflows.channels`

The existing voice router remains backward compatible. It gains an optional
workflow collaborator instead of absorbing the workflow engine.

### `ipfs_kit_py`

Provide an optional storage and transport profile for encrypted session state,
append-only event/outbox records, CID artifacts, pins, and replay. The generic
interfaces must also have a dependency-light local implementation so
`ipfs_kit_py` is not a mandatory import for every client.

### 211-AI

Own product-specific profiles and user/operator surfaces:

- `profiles/voice_workflows/211-ai/`
- wallet-backed intake/session APIs;
- customer action, consent, workflow, callback, and handoff UI;
- operator queue and workflow diagnostics;
- 211 service/action mappings; and
- 211-specific evaluations and rollout policy.

No 211 service taxonomy, wallet route, Abby persona string, or service-worker
field may be required by the generic packages.

## Domain profile model

A `DomainProfileManifest@1` pins:

- tenant-neutral profile ID and semantic version;
- content-pack CID;
- action-pack CID;
- workflow-pack CID;
- policy-pack CID;
- locale/voice-pack CIDs;
- optional UI-pack CID;
- supported schema versions;
- compatibility and migration metadata;
- signer identities and signatures; and
- the minimum runtime capability profile.

The profile pack is divided into three trust classes:

1. A public content pack contains documents, intents, response templates,
   public action descriptions, locale data, and public evidence.
2. An operator-signed control pack contains logical actions, workflows, input
   and output schemas, risk classes, consent rules, and capability
   requirements. It contains no credentials or executable locators.
3. Private tenant/session state contains caller data, forms, grants,
   transcripts, workflow instances, and handoff records.

A deployment binding maps a logical capability such as
`customer.callback.schedule@1` to a trusted adapter registration. Profile data
cannot provide a Python dotted path, raw command, arbitrary URL, or unapproved
MCP server identity.

Profile activation is transactional:

1. fetch or load every referenced object;
2. validate canonical identities and signatures;
3. validate schema compatibility and migrations;
4. compile workflow and GraphRAG indexes;
5. probe required adapter capabilities without invoking mutations;
6. publish a profile-activation receipt;
7. atomically change the tenant's active profile pointer; and
8. retain a bounded rollback pointer.

All pure compilation, retrieval, and policy-decision cache keys include tenant
namespace, active profile root CID, policy CID, schema versions, and relevant
adapter capability snapshot. Mutation outcomes are never served from a generic
result cache; an idempotency receipt ledger may return the prior receipt only
for the same admitted key and payload commitment. Profile activation cannot
reuse a stale result from another profile or tenant.

## Workflow DAG contract

### Node vocabulary

The first version supports only these closed node kinds:

- `start`
- `retrieve`
- `respond`
- `collect`
- `validate`
- `clarify`
- `branch`
- `consent`
- `confirm`
- `action_proposal`
- `action_execute`
- `wait`
- `human_handoff`
- `subworkflow`
- `compensate`
- `end`

No node evaluates arbitrary source or expression text. Conditions compile from
a small typed predicate language over declared state fields, confidence,
adapter capability, authorization facts, and prior receipt status.

### Edge vocabulary

Graph edges include:

- `NEXT`
- `NEXT_ON_TRUE`
- `NEXT_ON_FALSE`
- `NEXT_ON_SUCCESS`
- `NEXT_ON_FAILURE`
- `NEXT_ON_TIMEOUT`
- `NEXT_ON_UNKNOWN`
- `REQUIRES_SLOT`
- `REQUIRES_CAPABILITY`
- `REQUIRES_CONSENT`
- `SUGGESTS_ACTION`
- `COMPENSATES`
- `ESCALATES_TO`
- `CITES`

The compiler rejects duplicate IDs, missing targets, unreachable required
nodes, unbounded cycles, cycles without progress/budget conditions, ambiguous
terminal outcomes, compensation cycles, unsafe mutations without policy
references, and branches whose predicates cannot be evaluated by the closed
runtime.

### Conversation and execution state

Conversation state and action execution state are related but distinct. A
conversation can be closed while an external callback remains pending, and a
workflow can be resumed through a different channel.

The action state machine is:

```text
proposed -> validated
validated -> awaiting_confirmation | authorized | cancelled | expired
awaiting_confirmation -> authorized | cancelled | expired
authorized -> leased | cancelled | expired
leased -> executing | cancelled | expired
executing -> succeeded | failed | outcome_unknown
failed -> failed_uncompensated | compensating
compensating -> compensated | compensation_failed | escalated
outcome_unknown -> reconciling
reconciling -> succeeded | failed | escalated | outcome_unknown
```

`succeeded`, `failed_uncompensated`, `compensated`, `compensation_failed`,
`escalated`, pre-dispatch `cancelled`, and pre-dispatch `expired` are
conclusive terminal outcomes. `outcome_unknown` is a first-class
non-conclusive reconciliation hold and never aliases success. A dispatch
attempt itself closes immutably as confirmed success, confirmed failure, or
unresolved unknown. Later provider evidence appends a reconciliation receipt
and may move the workflow action from the hold to one conclusive outcome; it
never rewrites the original attempt.
The system must not claim exactly-once delivery for an arbitrary external
provider. It uses deterministic idempotency keys, transactional outbox
records, leases, fencing, adapter idempotency, and reconciliation. If a
provider cannot establish its outcome, automatic retries stop.

## Canonical contracts

Implement versioned, closed, size-bounded contracts for:

- `DomainProfileManifest`
- `ContentPackManifest`
- `ActionPackManifest`
- `WorkflowPackManifest`
- `PolicyPackManifest`
- `ActionDefinition`
- `WorkflowDefinition`
- `WorkflowNode`
- `WorkflowEdge`
- `ConversationSession`
- `ConversationTurn`
- `CollectedField`
- `ActionProposal`
- `InvocationIntent`
- `AuthorizationDecision`
- `ConsentReceipt`
- `ConfirmationReceipt`
- `ExecutionLease`
- `AdapterCapabilityReceipt`
- `ActionReceipt`
- `HumanHandoffRequest`
- `HumanHandoffResolution`
- `InteractionEvent`
- `ProfileActivationReceipt`

Canonical serialization uses strict DAG-JSON-compatible values and the
repository's admitted CIDv1/multihash profile. Raw audio, secrets, tokens,
precise location, unredacted transcripts, and low-entropy PII are not placed in
public receipts. Low-entropy private values require encryption and keyed
commitments; a bare digest is not adequate privacy.

Artifact type determines the complete CID profile. Existing voice GraphRAG
objects that use CIDv1 with the `raw` codec and `sha2-256` remain valid and
retain their identity. New DAG-JSON objects pin their codec, multibase,
multihash, and schema version explicitly. Compatibility records link the two;
the compiler never treats equal JSON bytes under different codecs as the same
CID.

## Action definition and policy

Every `ActionDefinition` declares:

- stable logical action ID and version;
- human-facing description;
- input and output schema CIDs;
- side-effect class;
- required collected fields;
- evidence and confidence requirements;
- authentication strength;
- capability and tenant scopes;
- confirmation or standing-consent policy;
- disclosure fields;
- idempotency dimensions;
- timeout, retry, concurrency, and cost budgets;
- compensation action when supported;
- audit and redaction profile; and
- allowed terminal/result mappings.

Side-effect classes are:

- `read_public`
- `read_private`
- `draft`
- `mutate_low_risk`
- `mutate_high_risk`
- `disclose`
- `destructive`
- `supervisor_control`
- `human_handoff`

Unknown classes fail closed. Mutation, disclosure, destructive operations,
supervisor control, and human handoff always pass through the same policy
gateway even when an adapter also implements its own authorization.

## Adapter SDK

Every adapter implements a common protocol:

- capability discovery;
- deterministic preflight;
- input schema validation;
- invocation with an execution lease and idempotency key;
- cancellation where supported;
- reconciliation;
- normalized error/result mapping;
- redacted health reporting; and
- content-addressed receipt generation.

An adapter cannot bypass the policy gateway. The conformance harness runs the
same authorization, timeout, replay, idempotency, cancellation, redaction, and
receipt tests against every adapter.

### MCP++ adapter

Bind a logical action to a reviewed server identity, negotiated MCP++ profile,
tool name, input/output schemas, and capability/UCAN policy. Record
`tools/list`, negotiation, authorization, `tools/call` or `mcp++/execute`, and
result mapping as one causal receipt chain. The workflow gateway must deny
missing policy or delegation independently of compatibility behavior in a
specific MCP server. The adapter must exercise the shipped `TrioMCPClient`
surface and force transport retry off for mutations unless the provider
contract explicitly declares idempotency and propagates the canonical key.

### Conventional MCP adapter

Use the same outer policy gateway, explicit server identity, exact tool schema,
timeout, and result mapping. Conventional MCP transport does not grant
authority by itself.

### CLI adapter

Only operator-registered executables and fixed argument templates are allowed.
Use argv arrays without a shell, a bounded working directory, an environment
allowlist, secret references, resource/time limits, output bounds, and an
egress policy. User text and profile data cannot become an executable or raw
command string.

### Python method adapter

Use an injected registry of callable objects. A profile may name a logical
capability but cannot import a dotted path. Validate signatures at
registration, isolate blocking/unsafe calls as policy requires, and normalize
sync/async results.

### HTTP/webhook adapter

Use operator-registered destinations, TLS and hostname policy, request/response
schemas, bounded redirects, SSRF protection, signature verification, and
idempotency headers. Profile or caller input cannot select the destination.

### Agent-supervisor adapter

Expose only narrow operations such as:

- validate a proposed goal packet;
- submit an approved goal or task packet;
- query status by opaque ID;
- request bounded cancellation; and
- request a human-reviewed refill scan.

Voice input alone cannot start arbitrary implementation, change write roots,
approve completion, merge code, push refs, expand resource limits, or select a
raw implementation command. Mutating supervisor operations require operator
delegation, a validated formal plan, quotas, confirmation, and isolated
worktree policy.

## GraphRAG action routing

Extend the graph with domain-neutral nodes for intent, required field,
logical action, workflow, capability, consent policy, response template, and
human queue. Retrieval returns ranked `ActionProposal` candidates containing
logical IDs and evidence, never executable bindings.

The deterministic router then:

1. checks the active profile and tenant;
2. filters unavailable or unauthorized logical actions;
3. checks required fields and evidence freshness;
4. applies minimum confidence and ambiguity margins;
5. asks for clarification when candidates are too close;
6. chooses a response-only path when no action is safe;
7. asks for confirmation or step-up authentication when required; and
8. submits only a validated proposal to the workflow engine.

Historical response text is not current factual evidence. Retrieved documents
and prompts cannot create a capability, standing consent, or executable
binding.

## Intake and multi-channel sessions

Schema-driven intake forms and voice slot collection use the same field
contracts. Each field declares:

- type and validation schema;
- sensitivity and retention class;
- source and confidence;
- correction history;
- whether confirmation is required;
- disclosure scope; and
- whether it is optional, required, or conditionally required.

Sessions are resumable across portal, chat, telephone, and human care through
an opaque session reference. Cross-channel resume requires authentication
appropriate to the private state involved. The public voice graph never stores
private session state.

## Human handoff

Human care is an adapter with richer lifecycle contracts, not a fallback text
string. It supports:

- skill/queue discovery;
- operating hours and capacity;
- consented context minimization;
- callback request;
- warm transfer;
- cold transfer with secure case link;
- operator acceptance;
- caller abandonment;
- timeout and alternate queue;
- resolution and follow-up;
- revocation and retention; and
- emergency/safety policies that do not promise unavailable services.

A `HumanHandoffRequest` contains only fields allowed by the caller's grant and
the destination queue schema. The receiving worker uses an opaque, expiring,
revocable case link for additional context.

## Telephony and channel adapters

The generic channel contract supports PSTN provider webhooks, SIP, WebRTC,
browser voice, text chat, and portal forms. Provider-specific adapters handle
signature validation and transport, then emit the same channel events.

Telephone requirements include:

- webhook signature and replay validation;
- privacy-safe call identity;
- turn, duration, and cost budgets;
- DTMF and speech input;
- interruption/barge-in;
- partial STT and silence handling;
- callback and transfer status;
- recording/transcript consent;
- provider retry deduplication;
- hangup/cancellation propagation; and
- degraded prompts when retrieval, TTS, or action services are unavailable.

The system records an attempted transfer separately from a connected human.

## Portal surfaces

### Customer portal

- conversation and intake timeline;
- schema-driven forms;
- cited response/evidence panel;
- collected-field review and correction;
- proposed and pending actions;
- confirmation and consent cards;
- workflow progress;
- callback and handoff status;
- interaction history;
- privacy, export, deletion, and retention controls; and
- accessible keyboard, screen-reader, mobile, and low-bandwidth modes.

### Human care workspace

- queue and skill filters;
- minimal consented case summary;
- acceptance and ownership;
- conversation/action history within grant;
- secure request for more context;
- notes with explicit privacy class;
- disposition and follow-up;
- callback outcome; and
- handback to automation.

### Operator workspace

- profile validation, activation, canary, and rollback;
- action/deployment binding management;
- adapter capability and health;
- workflow instance diagnostics;
- `outcome_unknown` reconciliation;
- policy-denial and ambiguity review;
- redacted metrics and traces; and
- signed release/conformance receipts.

Portal components consume generic schemas. The 211 profile supplies labels,
forms, service taxonomy, branding, and action mappings.

## Security and privacy release gates

Mutation support remains disabled until these hold:

- deny by default when a policy, capability, tenant binding, or delegation is
  absent;
- re-evaluate authorization after acquiring an execution lease;
- bind authorization to tenant, principal, action CID, resource/field scope,
  expiry, call budget, policy CID, and active profile CID;
- require confirmation or valid standing consent for mutations;
- require step-up authentication or human approval for high-risk operations;
- resolve credentials only from server-side opaque secret references;
- keep persisted/shared prompts, profiles, DAGs, logs, metrics, and public
  receipts secret-free;
- allow private inference only at an explicitly admitted tenant-isolated
  boundary with minimum-field disclosure, provider/retention policy, no
  cross-tenant cache reuse, and a receipt for the disclosure decision;
- isolate private embeddings per tenant and make them deletable/rebuildable;
- minimize handoff fields to the active grant;
- prevent prompt/tool injection, schema smuggling, command injection, SSRF,
  path escape, confused-deputy calls, replay, and cross-tenant cache reuse;
- use audited asymmetric signing for production authority receipts; and
- retain a tested kill switch that disables action execution while preserving
  response-only and human-care paths.

This framework provides technical controls and evidence. A deployment must
perform its own legal, safety, accessibility, retention, and regulated-data
review; the framework does not claim regulatory compliance by itself.

## Formal invariants

The assurance lane encodes and tests at least:

1. `Executed(i) -> SignedProfile(action(i)) and SchemaValid(i) and
   Authorized(i) and LeaseValid(i) and IdempotencyBound(i)`.
2. `Mutating(i) -> Confirmed(i) or ValidStandingConsent(i)`.
3. `Tenant(invocation) = Tenant(session) = Tenant(profile) =
   Tenant(receipt)`.
4. Replaying the same idempotency key and payload returns the prior receipt;
   changing the payload yields an idempotency conflict.
5. A workflow instance has at most one conclusive terminal outcome, while
   `outcome_unknown` remains explicit.
6. Every domain, action, eligibility, availability, or system-status claim
   spoken by the system cites current evidence under the active profile CID;
   caller-supplied assertions cite their private session records and are not
   promoted to verified external facts.
7. Private data never flows to a public index, public receipt, shared prompt,
   metric, or public IPFS object; any admitted private-inference disclosure is
   a minimum-field subset of an active tenant policy and grant.
8. Handoff fields are a subset of the active grant and destination schema.
9. Retrieval or model output cannot increase authority.
10. Supervisor mutation requires operator delegation, validated plan, quotas,
    and isolated worktree policy.

Formal-plan consistency, runtime conformance, and ZK trace attestation are
different claims. Begin with deterministic checks, property/state-machine
tests, counterexamples, and signed content-addressed receipts. An optional ZK
phase may later attest supported statements about profile membership, required
field presence, consent validity, or policy evaluation over commitments. It
must not be called end-to-end semantic proof.

## Content addressing and receipts

Every authoritative receipt binds:

- tenant namespace;
- active profile and component CIDs;
- workflow/action definition CIDs;
- policy and deployment-binding CIDs;
- request/session/action identities;
- normalized input commitment and private-field redaction profile;
- adapter capability snapshot;
- authorization, consent, confirmation, lease, and idempotency identities;
- result or explicit unknown/failure state;
- runtime and schema versions;
- causal predecessor receipt IDs; and
- timestamp/expiry under a declared clock policy.

Large bodies remain encrypted or in immutable artifacts. Prompts and supervisor
tasks receive small CID-addressed slices, not complete transcripts, corpora, or
repositories.

## Parallel implementation program

### Gate 0: freeze contracts

The contracts lane owns architecture decisions, canonical schemas, state
machines, trust boundaries, and compatibility fixtures. Runtime and data lanes
may build fakes in parallel, but shared public contracts land through this
gate.

### Wave 1: independent foundations

After contract freeze, run concurrently:

- domain-profile and GraphRAG generalization in `ipfs_datasets_py`;
- workflow runtime and durable state in `ipfs_accelerate_py`;
- policy/formal assurance;
- adapter conformance harness; and
- portal schema prototypes against fakes.

### Wave 2: adapter and channel shards

Run MCP++, MCP, CLI, Python, HTTP, supervisor, telephony, and human-handoff
adapters in separate worktrees with disjoint modules and focused tests.

### Wave 3: reusable integration

Integrate action-aware retrieval, workflow execution, session resume, portal
APIs/UI, profile activation, and operator diagnostics. Use synthetic adapters
before any real mutation.

### Wave 4: two-profile proof

Build the 211-AI profile and an unrelated IT-helpdesk reference profile in
separate lanes. Both must pass the same unmodified compiler, adapter, portal,
security, and end-to-end conformance suites.

### Wave 5: canary and release

Progress through:

1. offline fixtures;
2. shadow proposal-only mode;
3. response-only/read-only mode;
4. human-handoff mode;
5. consented low-risk actions;
6. selected high-risk actions with operator approval; and
7. general availability after release gates.

## Conflict ownership

- Contract lane owns shared schemas and package exports.
- Data lane owns `ipfs_datasets_py.voice_workflows`.
- Runtime lane owns engine, state, policy interfaces, and receipts.
- Each adapter lane owns one adapter module and its focused tests.
- Channel lane owns provider-neutral channel contracts and channel adapters.
- Portal lane owns generic API/UI surfaces.
- 211 profile lane owns only 211 profile data, bindings, fixtures, and labels.
- Reference-profile lane owns only the unrelated example profile.
- Assurance lane owns formal models, adversarial fixtures, and conformance
  reports.
- Operations lane owns launch control, observability, runbooks, and release
  receipts.

Edits to shared package exports, central registries, root UI routing, or common
test fixtures require an explicit integration task. `VOICE-CARE-049` through
`VOICE-CARE-052` own datasets exports, accelerator adoption, backend API
registration, and portal routing respectively. Parallel leaf tasks must not
opportunistically modify those files.

## Supervisor execution and refill policy

The task board uses `## VOICE-CARE-...` headings and the current
`ipfs_accelerate_py` goal/task metadata fields. Every task includes a goal ID,
dependency list, output ownership, validation command, parallel lane, resource
class, conflict policy, symbolic-first flag, and small LLM context budget.

The validated launch profile is
`docs/planning/reusable_voice_workflow_dag_client_care.supervisor.json`, and
`scripts/validate_voice_workflow_dag_client_care_plan.py` is its fail-closed
preflight. The profile alternates Grok and Codex across four isolated lanes.
Task locality uses the supervisor's current rule:
`numeric_task_suffix % 4 == shard_index`. Shards may claim other ready work
only through the supervisor's normal locks.

`voice-care-grok-0` is the sole objective/codebase refill and repository Git-GC
owner. Other lanes may report content-addressed findings but cannot mutate the
goal heap or board. Refill authority does not transfer merely because that
provider is unavailable.

The JSON is deliberately a validated input for the control wrapper planned
under `VOICE-CARE-G130`; it does not by itself claim that a daemon has been
started. The wrapper must provide idempotent preflight/start/status/stop,
external state, isolated worktrees and logs, provider probes, a serialized
merge queue, protected planning paths, and no secrets in process arguments
before execution is enabled. Because the configured merge target is initially
absent, preflight must create it only from the pinned reviewed base commit and
must reject a dirty recursive tree, missing base, or mismatched target before
starting a worker.

Bootstrap order:

1. run the planning-package validator;
2. give only `VOICE-CARE-001` to an existing bounded implementation lane or a
   directly supervised agent;
3. run its independent preflight/start/status/stop tests;
4. create or verify the pinned merge target and run one non-implementing
   reconciliation pass;
5. start the four configured lanes; and
6. leave objective/codebase refill disabled until the protected-path,
   deduplication, budget, and sole-owner receipts pass.

A discovered task is admitted only when it has:

- a deterministic finding identity and content CID;
- one owning parent goal;
- a bounded output set;
- an affected contract or invariant;
- a focused validation command;
- explicit evidence required for completion;
- a conflict domain and dependency set;
- no semantic duplicate in open/completed tasks; and
- a refinement depth and child-count within policy.

Refill never changes the root goal, write authority, provider shards,
completion authority, security policy, or resource ceiling. Generated child
tasks cannot automatically complete a parent. Retry exhaustion, merge
conflict, unsupported semantics, and inconclusive proof become bounded review
tasks instead of silent success.

Default limits:

- four deterministic task shards;
- one refill owner;
- three children per refinement;
- four refinement levels;
- two surplus findings per goal;
- eight objective findings and five codebase findings per scan;
- a one-hour objective and six-hour codebase refill cooldown;
- 900-second objective and 600-second codebase refill timeouts;
- 16 KiB ordinary LLM context per task;
- 32 KiB maximum for an integration task; and
- content-addressed evidence slices preferred over copied source.

## Validation strategy

### Contract tests

- canonical round trips and cross-process identity;
- malformed, unknown, oversized, cyclic, and conflicting records;
- compatibility with current voice-turn and Abby response-DAG contracts;
- profile migration and rollback;
- task/goal graph preflight.

### Property and model tests

- workflow transition safety;
- single conclusive terminal outcome;
- confirmation and authorization invariants;
- tenant/profile/cache isolation;
- idempotent replay and payload conflict;
- cancellation, compensation, lease expiry, and fencing.

### Adapter conformance

- missing policy/delegation;
- invalid schema;
- timeout and cancellation;
- duplicate delivery;
- retry after crash;
- provider without idempotency;
- redaction and output bounds;
- normalized errors and `outcome_unknown`.

### Security tests

- prompt and retrieved-document injection;
- forged logical action IDs;
- schema smuggling;
- MCP server/tool substitution;
- raw CLI command and argument injection;
- unregistered Python import;
- webhook SSRF/redirect abuse;
- replay and stale consent;
- confused deputy;
- cross-tenant state/index/cache access;
- secrets in receipts/logs/prompts;
- unauthorized supervisor control.

### End-to-end tests

- browser voice and text;
- synthetic PSTN/SIP callback and warm transfer;
- low-confidence clarification;
- response-only fallback;
- read-only MCP action;
- consented low-risk mutation;
- failed/unknown external outcome and reconciliation;
- human handoff and revocation;
- profile activation/rollback;
- identical runtime against 211 and IT-helpdesk profiles.

## Quality and operating targets

Targets are measured in hermetic tests and then calibrated in canary:

- zero unauthorized or unconfirmed mutations in the acceptance corpus;
- zero cross-tenant cache or state reuse;
- zero secret/raw-audio leakage into public receipts;
- 100% action receipts linked to active profile, policy, and adapter identity;
- 100% system-authored domain/action/status claims linked to current evidence,
  with caller assertions attributed to private session records;
- deterministic workflow/profile identities across supported runtimes;
- bounded latency budgets per stage with explicit degradation;
- visible `outcome_unknown` reconciliation;
- accessible customer confirmation and handoff flows; and
- successful profile swap without core source edits.

## Non-goals for the first release

- letting free-form model output execute arbitrary tools;
- arbitrary Python imports or shell execution;
- claiming exactly-once effects for an uncooperative external system;
- putting private transcripts or caller data on public IPFS;
- automatic high-risk supervisor or service mutations from voice alone;
- replacing human crisis/emergency judgment;
- claiming legal/regulatory compliance from technical controls; or
- claiming ZK proof of arbitrary program semantics.

## Definition of done

The program is complete when:

- generic profile, action, workflow, session, policy, adapter, handoff, and
  receipt contracts are stable and content addressed;
- GraphRAG proposes logical actions without gaining execution authority;
- every adapter passes one reusable conformance harness;
- the workflow runtime survives replay, crash, timeout, cancellation, and
  unknown outcomes without unsafe duplicate effects;
- portal, voice, telephone, and human-care channels share the same workflow and
  action contracts;
- private state is encrypted, tenant-isolated, retention-bound, and absent from
  public graphs/receipts;
- 211-AI works as a profile rather than a fork;
- a second unrelated profile passes the same suite without core edits;
- formal and runtime evidence support the stated invariants without
  overclaiming;
- shadow, read-only, handoff, and consented-action canaries pass; and
- operations, rollback, incident, key-rotation, and profile-authoring
  documentation are complete.
