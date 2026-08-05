# Voice Action DAG × Abby — Agent Supervisor Runbook

Program: `voice-action-dag-abby-v1`  
Board namespace: `voice-action-dag-abby-v1`  
Goal: `VOICE-ACTION-G150`  
Task: `VOICE-ACTION-031`  
Track: operations

This runbook is the **operator control surface** for the Abby voice action DAG
integration. It documents product enablement flags, fake versus live transport
policy, handoff truthfulness rules, parallel lane ownership, and the fail-closed
supervisor bootstrap used by autonomous workers.

Companion artifacts:

| Artifact | Path |
| --- | --- |
| Integration plan | `docs/planning/VOICE_ACTION_DAG_ABBY_INTEGRATION_PLAN.md` |
| Goal heap | `docs/planning/voice_action_dag_abby.objectives.md` |
| Task board | `docs/planning/voice_action_dag_abby.todo.md` |
| Launch profile | `docs/planning/voice_action_dag_abby.supervisor.json` |
| Runtime policy | `docs/voice_action_dag/runtime-policy.json` |
| Supervisor state layout | `docs/voice_action_dag/AGENT_SUPERVISOR_STATE.md` |
| Integration doctrine | `docs/voice_action_dag/INTEGRATION_DOCTRINE.md` |
| Handoff freeze | `docs/voice_action_dag/HANDOFF.md` |
| Deployment binding | `docs/voice_action_dag/DEPLOYMENT_BINDING.md` |
| E2E pilot matrix | `docs/voice_action_dag/E2E_PILOT.md` |
| Enablement checklist | `docs/voice_action_dag/ENABLEMENT_CHECKLIST.md` |
| Unified router rollout | `docs/runbooks/ABBY_VOICE_ROUTER_ROLLOUT.md` |

Preflight (always run before worker start or production flag flips):

```bash
python scripts/validate_voice_action_dag_abby_plan.py
```

## 1. Purpose and dual-plane reminder

The program connects the **Abby slotted response DAG** and precomputed audio
library to a **governed action plane** so voice turns can propose catalog-bound
logical actions, require confirmation, and execute only through reviewed
adapters.

```text
channel input
  -> STT / transcript
  -> Abby GraphRAG + slotted DAG route          [content plane]
  -> grounded spoken response (+ library audio) [content plane]
  -> logical ActionProposal (no executables)    [content plane emit]
  -> fail-closed policy / consent / confirmation [authority plane]
  -> deployment-owned catalog binding            [authority plane]
  -> admitted adapter                            [authority plane]
  -> ActionReceipt                               [authority plane]
  -> spoken outcome from Abby library or safe fallback [content plane]
```

**Non-negotiable:** GraphRAG, exemplars, and models never choose executables,
URLs, import paths, or credentials. They may only name logical capabilities
already declared in a signed catalog.

## 2. Operator feature flags

Two independent wallet environment flags gate product behavior. Both default
**off**. Enabling either flag is a human operator action; autonomous supervisor
workers must never set them.

### 2.1 `WALLET_VOICE_UNIFIED_ROUTER_ENABLED`

| Property | Value |
| --- | --- |
| Constant | `wallet_interface.helpers._voice_router_adapter.UNIFIED_VOICE_ROUTER_FLAG` |
| Default | off (`0` / unset) |
| Scope | Wallet adoption of the shared Abby voice-turn router |
| Truthy values | `1`, `true`, `yes`, `on` (case-insensitive) |

When **off**, the wallet proxy continues its legacy STT / TTS path. Browser
SpeechRecognition, local WebGPU audio, and browser speech-synthesis fallbacks
remain available.

When **on**, `wallet_interface.helpers._voice_router_adapter` lazily delegates
to `ipfs_accelerate_py.voice_router.process_voice_turn` and returns a canonical
`VoiceTurnResult` receipt (transcript, spoken text, provenance, stage traces,
optional base64 audio). Raw input audio must not appear in ordinary logs or
persisted metrics.

Staged enablement and rollback for this flag are detailed in
`docs/runbooks/ABBY_VOICE_ROUTER_ROLLOUT.md`. Summary:

```bash
# Safe default / rollback
export WALLET_VOICE_UNIFIED_ROUTER_ENABLED=0

# Canary / staged enable (after offline + deployed-like checks)
export WALLET_VOICE_UNIFIED_ROUTER_ENABLED=1
```

Reload the proxy process after changing the value so the process re-reads the
environment.

### 2.2 `WALLET_VOICE_ACTION_EXECUTE_ENABLED`

| Property | Value |
| --- | --- |
| Constant | `wallet_interface.helpers._voice_action_surface.VOICE_ACTION_EXECUTE_FLAG` |
| Default | off (`0` / unset) |
| Scope | Authority-plane adapter **execution** after explicit confirm |
| Truthy values | `1`, `true`, `yes`, `on` (case-insensitive) |

This flag is **independent** of the unified router flag. With execute off:

* route → logical action **proposals** still attach to voice receipts;
* policy still emits `confirm` / `deny` / `handoff` decisions;
* explicit `confirm_action` / `action_confirm` **never** starts adapters.

Execution requires **both** gates:

1. Operator flag `WALLET_VOICE_ACTION_EXECUTE_ENABLED=1`.
2. Explicit per-request confirmation (`confirm_action` / `action_confirm`).

Confirm without the operator flag never executes. The operator flag without
per-request confirm never executes. Production execute additionally requires a
matching **signed deployment binding** (catalog digest + adapter identities);
confirmation cannot override a binding mismatch
(`docs/voice_action_dag/DEPLOYMENT_BINDING.md`).

```bash
# Safe default / kill switch (proposals and confirm UX remain available)
export WALLET_VOICE_ACTION_EXECUTE_ENABLED=0

# Enable execute only after checklist signoff (see ENABLEMENT_CHECKLIST.md)
export WALLET_VOICE_ACTION_EXECUTE_ENABLED=1
```

### 2.3 Flag interaction matrix

| `UNIFIED_ROUTER` | `ACTION_EXECUTE` | Product behavior |
| --- | --- | --- |
| off | off | Legacy voice path; no unified receipt; no adapter execute |
| on | off | Unified voice receipt + action **proposal/confirm** surface; no execute |
| off | on | Legacy voice path; action surface may still attach if wired; execute dual-gated |
| on | on | Unified receipt + dual-gated execute (still needs confirm + binding) |

Recommended rollout order:

1. Ship code with both flags off.
2. Enable `WALLET_VOICE_UNIFIED_ROUTER_ENABLED` for a canary slice; prove
   receipts and fallbacks.
3. Exercise proposal + confirm with execute still off.
4. Enable `WALLET_VOICE_ACTION_EXECUTE_ENABLED` only after offline matrix,
   adversarial tests, signed binding, and the enablement checklist pass.

## 3. Fake vs live transports

### 3.1 Autonomous / CI / supervisor default (fake only)

Supervisor workers and offline proofs **must** use fake, process-local
transports. Runtime policy (`docs/voice_action_dag/runtime-policy.json`)
defaults:

| Constraint | Value |
| --- | --- |
| network | deny |
| credentials | deny |
| publication | deny |
| live telephony | deny |
| live SMS | deny |
| HF publish | deny |
| require fake adapters | true |
| live_transports_enabled | false |

Offline fake backends used by the pilot matrix and unit suites:

| Family | Fake backend | Module |
| --- | --- | --- |
| App / wallet surfaces | `InMemoryAppSurfaceApi` | `wallet_interface.helpers._voice_app_action_binding` |
| Calendar | `InMemoryCalendarEventStore` | `action_runtime.adapters.calendar` |
| Messaging | `InMemoryProviderMessageStore` | `action_runtime.adapters.messaging` |
| Service interaction | `InMemoryServiceInteractionStore` | `action_runtime.adapters.service_interaction` |
| Human handoff | `InMemoryHandoffRequestStore` | `action_runtime.adapters.human_handoff` |
| Policy / catalog | `PilotPolicy` + `211ai-pilot-v1` | `action_runtime.policy_pilot` / `catalog_211ai` |

Fakes are process-local. Socket-deny fixtures fail closed on accidental network
use. Fake telephony may mark handoff outcomes as `unknown` without claiming
transfer success.

### 3.2 Live transports (human-gated only)

Live PSTN warm transfer, SMS, paid STT/TTS endpoints, Hugging Face publish, and
production credentials are **outside** autonomous worker authority. Enabling
them requires:

* explicit human approval recorded outside this board;
* product deployment configuration (not content-plane artifacts);
* matching signed deployment binding for production execute;
* kill switches that return both flags (and any live transport env) to off.

This program does **not** claim exactly-once semantics for external telephony
or SMS providers. Ambiguous provider outcomes must surface as `unknown` or
`failed`, never as silent success.

### 3.3 What workers may read/write

Allowed under default runtime policy:

* Abby dataset / library **reads**;
* smoke writes under `tmp_assets` when explicitly permitted;
* offline fixtures and in-memory stores.

Forbidden for autonomous workers:

* turning on `WALLET_VOICE_UNIFIED_ROUTER_ENABLED` or
  `WALLET_VOICE_ACTION_EXECUTE_ENABLED` in shared environments;
* loading production credentials or secret manager material;
* real carrier calls, SMS, or remote HF publication;
* editing protected plan artifacts (see §6).

## 4. Handoff truthfulness

These rules apply to `live_agent`, `handoff_live_agent`, safety escalate, and
any human/telephony transfer path. They are frozen in
`docs/voice_action_dag/INTEGRATION_DOCTRINE.md` §5 and implemented by
`docs/voice_action_dag/HANDOFF.md`.

1. **Never claim unverified transfer success.** Spoken text, UI copy, and
   receipts must not assert that a warm transfer or live-agent connection
   completed unless a **provider confirmation receipt** exists.
2. **Metadata-only escalation is not success.** Text-only `human_handoff`
   provider metadata or advisory flags are **request / escalate** states, not
   completed transfers.
3. **Receipted request vs completed transfer.** Creating a handoff **request**
   (`ActionDecisionKind.HANDOFF` / receipt status `accepted`) is distinct from
   transfer completion (`succeeded` with `provider_confirmation`).
4. **Outcome speech must match receipt.** Success outcome frames may play only
   after a verified `succeeded` receipt; otherwise use deny, cancelled,
   failure, or unknown frames.
5. **No silent success from content.** The `live_agent` route’s spoken guidance
   remains content-plane; it does not imply authority-plane transfer completion.

### 4.1 Status → spoken success gate

| Receipt status | Meaning | Spoken transfer success? |
| --- | --- | --- |
| `accepted` | Durable request created / queued | **No** |
| `started` | Transfer / bridge attempt begun | **No** |
| `succeeded` | Provider confirmed live connection | **Yes** (only this) |
| `unknown` | Indeterminate / no provider ack | **No** |
| `failed` | Transfer or queue failure | **No** |
| `cancelled` | Caller/operator cancelled | **No** |

Code gate: `allows_spoken_success(receipt)` is true only when status is
`succeeded`. Voice and UI layers must consult this gate (or the receipt status
directly) before playing Abby transfer-complete wording.

### 4.2 Operator checks

Before enabling live handoff in any environment:

* [ ] Offline handoff adapter tests pass
  (`python -m pytest -q ipfs_accelerate_py/test/test_action_human_handoff_adapter.py`).
* [ ] E2E pilot matrix asserts `live_agent` handoff receipt semantics with
  `spoken_success_allowed=false` until provider confirmation.
* [ ] Product UI never labels a handoff as complete on `accepted` / `started` /
  `unknown`.
* [ ] Safety overlay can force escalate/handoff **request** without smuggling
  unrelated write tools.

## 5. Parallel lane ownership

### 5.1 Supervisor shard lanes (runtime workers)

Four deterministic shards from the launch profile. **Only**
`voice-action-grok-0` owns objective/codebase refill and repo git GC.

| Lane | Provider | Shard | Refill owner | Git GC owner |
| --- | --- | --- | --- | --- |
| `voice-action-grok-0` | grok-build | 0 | **yes** | **yes** |
| `voice-action-codex-1` | codex | 1 | no | no |
| `voice-action-grok-2` | grok-build | 2 | no | no |
| `voice-action-codex-3` | codex | 3 | no | no |

Merge target branch: `agent/voice-action-dag-abby`  
Pinned base: `origin/main` @ `12a7ef36645bf597de329dbfabe0ce5b2e0c4df9`  
Fast-forward merges only. Recursive tree must be clean before creation/start.

Refill remains disabled until after `VOICE-ACTION-001` and these bootstrap
receipts exist:

1. `protected-path-policy`
2. `semantic-deduplication`
3. `bounded-refill-budget`
4. `sole-refill-owner`

### 5.2 Task parallel lanes (work ownership)

Tasks declare a `Parallel lane` field so independent ownership domains can
progress without thrashing the same files. Waves from the integration plan:

```text
wave-00 ops/bootstrap
  -> wave-01 inventory + doctrine (parallel)
  -> wave-02 abby content links + catalog + policy (parallel)
  -> wave-03 graphrag proposals + voice_router attach (parallel)
  -> wave-04 adapters: app / calendar / messages / service / handoff (parallel)
  -> wave-05 abby audio frames for action prompts/outcomes
  -> wave-06 e2e + release gates
```

| Parallel lane family | Owns | Must not own |
| --- | --- | --- |
| `wave-00-control` | Supervisor launch policy, runtime policy, protected paths | Product adapters, content library rebuild |
| `wave-01-inventory` / `wave-01-doctrine` | Baseline reports; dual-plane doctrine vocabulary | Runtime modules; executable injection |
| `wave-02-content-*` | Action-link schema and projections | Catalog bindings, adapters |
| `wave-02-catalog` / `wave-02-policy` | Pilot catalog IDs; policy predicates | Content DAG rebuild; live transports |
| `wave-03-retrieval` / `wave-03-bridge` / `wave-03-router` | GraphRAG candidates; voice_bridge; router attach | Adapter execute; UI redesign |
| `wave-03-wallet` / `wave-03-api` | Wallet action surface + confirm plumbing | Unrelated agent chat redesign |
| `wave-04-app` / `calendar` / `messages` / `service` / `handoff` | Exclusive adapter modules and bindings | Cross-adapter rewrites; real carrier calls in tests |
| `wave-04-safety` | Safety overlay rules | Arbitrary tool grants |
| `wave-05-*` | Action speech frames, audio fixtures, outcome speech, UI surface | Production HF publish (separate gated path) |
| `wave-06-e2e` / `wave-06-adversarial` | Offline matrix and adversarial cases (fakes only) | Live network proofs |
| `wave-06-docs` | Operator runbook + enablement checklist (this task) | Runtime code |
| `wave-06-binding` | Signed deployment binding gate | Content-plane widening |

Conflict policies on each task board entry are authoritative: exclusive owners
serialize on shared modules; binding/UI tasks remain additive; documentation
lanes do not claim runtime ownership.

### 5.3 Package ownership (cross-cutting)

| Owner | Owns |
| --- | --- |
| `ipfs_datasets_py` | Abby content→action links, domain-pack slices, GraphRAG candidates, audio frame indexes |
| `ipfs_accelerate_py` | `action_runtime`, adapters, policy, orchestration, voice_router integration |
| parent `wallet_interface` | UI confirm/execute UX, app tool bindings, calendar/messages/service surfaces, API envelope |
| parent `docs/phone_dialog_generation` | Slotted DAG rebuild outputs and manifests only via generation scripts |

## 6. Protected plan namespace

Workers and implementation agents must **not** create, modify, rename, delete,
replace, or regenerate:

* `docs/planning/VOICE_ACTION_DAG_ABBY_INTEGRATION_PLAN.md`
* `docs/planning/voice_action_dag_abby.objectives.md`
* `docs/planning/voice_action_dag_abby.todo.md`
* `docs/planning/voice_action_dag_abby.supervisor.json`
* `scripts/validate_voice_action_dag_abby_plan.py`

These paths are listed in the launch profile and runtime policy. Plan edits
require human operators outside autonomous lanes.

## 7. Supervisor control commands

External state root (required before worker start):

```bash
export VOICE_ACTION_DAG_SUPERVISOR_STATE_ROOT=/absolute/path/to/state
```

```bash
# Fail-closed preflight of objectives, board, profile, and runtime policy
python scripts/validate_voice_action_dag_abby_plan.py
python scripts/voice_action_dag/supervisor_control.py validate-config

# Create merge target only from the pinned reviewed base when absent
python scripts/voice_action_dag/supervisor_control.py ensure-merge-target

# Admit four deterministic shards (sole refill owner: voice-action-grok-0)
python scripts/voice_action_dag/supervisor_control.py start
python scripts/voice_action_dag/supervisor_control.py status
python scripts/voice_action_dag/supervisor_control.py stop
```

Expected external layout (created by control scripts, not committed):

```text
$VOICE_ACTION_DAG_SUPERVISOR_STATE_ROOT/
  worktrees/
  lanes/
  logs/
  projection/
  merge-queue/
  runtime/
```

Secrets must never appear in process argv.

## 8. Validation gates (offline)

Run from repository root before any production flag enablement:

```bash
# Plan / board / profile integrity
python scripts/validate_voice_action_dag_abby_plan.py

# Doctrine invariants
python -m pytest -q tests/voice_action_dag/test_doctrine_invariants.py

# Deployment binding (confirm cannot override digest mismatch)
python -m pytest -q ipfs_accelerate_py/test/test_action_deployment_binding.py

# Handoff truthfulness
python -m pytest -q ipfs_accelerate_py/test/test_action_human_handoff_adapter.py

# Offline 12-route pilot matrix (fake adapters, network denied)
python -m pytest -q tests/e2e/voice_action_dag/test_abby_pilot_matrix.py

# Wallet dual-gate action surface
python -m pytest -q wallet_interface/tests/test_ai_router_voice_action.py
python -m pytest -q wallet_interface/tests/test_voice_router_adapter.py
```

Optional unified-router UI gate (when enabling `WALLET_VOICE_UNIFIED_ROUTER_ENABLED`):

```bash
npm --prefix wallet_interface/ui test -- tests/agent-voice-router.spec.ts
```

## 9. Production enablement sequence

Use `docs/voice_action_dag/ENABLEMENT_CHECKLIST.md` as the signed checklist.
High-level order:

1. Preflight plan validator green; protected paths intact.
2. Offline matrix + adversarial + handoff + binding tests green.
3. Deploy code with **both** flags off; verify legacy voice path.
4. Canary `WALLET_VOICE_UNIFIED_ROUTER_ENABLED=1`; collect successful, degraded,
   and text-only receipts; prove rollback to `0`.
5. Confirm action proposal/confirm UX with execute still off.
6. Install operator-signed deployment binding for the target catalog digest and
   adapter identities.
7. Canary `WALLET_VOICE_ACTION_EXECUTE_ENABLED=1` for a single internal tenant
   or synthetic session; exercise one read action and one denied-without-confirm
   path.
8. Verify handoff never speaks transfer-complete without provider confirmation.
9. Expand slice only while metrics (deny rate, unknown outcomes, fallback rate,
   p95 latency) stay within existing SLOs.
10. Keep dual kill switches ready: set both flags to `0` and reload.

## 10. Rollback and incident response

| Symptom | Immediate action |
| --- | --- |
| Unexpected adapter side effects | `WALLET_VOICE_ACTION_EXECUTE_ENABLED=0`; reload proxy |
| Unified receipt parse failures / audio regressions | `WALLET_VOICE_UNIFIED_ROUTER_ENABLED=0`; reload proxy |
| False “transfer complete” speech | Disable execute; quarantine handoff adapter; verify `allows_spoken_success` gate |
| Catalog / adapter identity drift | Binding gate denies execute; do **not** bypass with confirm; re-sign binding after review |
| Supervisor lane thrash on protected paths | `supervisor_control.py stop`; investigate without editing protected plan files |

Preserve failed receipt IDs, stage errors, endpoint role, and deployment
revision for incident review. Redact audio, credentials, prompts, local paths,
and source documents from shared logs.

## 11. Explicit non-goals

* Replacing Abby TTS generation infrastructure.
* Full multi-tenant profile-pack platform (see reusable voice-care plan).
* Unsupervised production execute with credentials enabled by default.
* Claiming exactly-once semantics for external telephony or SMS providers.
* Autonomous workers enabling product flags or live transports.

## 12. Related code entry points

| Concern | Entry point |
| --- | --- |
| Unified router flag | `wallet_interface/helpers/_voice_router_adapter.py` |
| Action execute flag + dual gate | `wallet_interface/helpers/_voice_action_surface.py` |
| AI router confirm wiring | `wallet_interface/routes/ai_router.py` |
| Human handoff adapter | `ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/adapters/human_handoff.py` |
| Production binding gate | `ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/deployment_binding.py` |
| Supervisor control | `scripts/voice_action_dag/supervisor_control.py` |
| Plan preflight | `scripts/validate_voice_action_dag_abby_plan.py` |
