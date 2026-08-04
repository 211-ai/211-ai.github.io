# Voice Action DAG × Abby Voice Dataset Integration Plan

## Outcome

Connect the **existing slotted Abby voice response DAG** and **Abby precomputed
audio library** to a **governed action plane** so that voice turns can:

1. ground a caller-visible response in the Abby content library;
2. propose a **logical** program action from the same route/evidence graph;
3. obtain policy, consent, and explicit confirmation;
4. execute only through reviewed adapters (app tools, calendar, messaging,
   service interactions, human handoff / live agent, CLI/MCP when admitted);
5. speak a content-addressed confirmation or failure utterance from the Abby
   library whenever possible.

This program does **not** replace the reusable voice-care platform plan
(`REUSABLE_VOICE_WORKFLOW_DAG_CLIENT_CARE_PLAN.md`). It is a **focused
integration program** that ships the shortest safe path from the assets we
already have to real product actions, while remaining compatible with that
larger architecture.

Durable goal heap:
`docs/planning/voice_action_dag_abby.objectives.md`

Executable task board:
`docs/planning/voice_action_dag_abby.todo.md`

Supervisor launch profile:
`docs/planning/voice_action_dag_abby.supervisor.json`

Preflight:
`python scripts/validate_voice_action_dag_abby_plan.py`

## Starting inventory (shipped baseline)

### Content plane (Abby)

| Asset | Location | Role |
| --- | --- | --- |
| Slotted response DAG | `docs/phone_dialog_generation/slotted_response_dag.json` | Intent → response frame graph (~13.6k edges, 12 routes) |
| Unique exemplars | same file `nodes.uniqueExemplars` | Route-tagged query/response pairs |
| GraphRAG templates | `ipfs_datasets_py.voice.graphrag` | Deterministic grounded retrieval |
| Response DAG append | `ipfs_datasets_py.voice.response_dag` | Validated audio lineage |
| Precomputed audio resolver | Abby TTS resolver rows / HF releases | Exact-match spoken audio |
| Voice router | `ipfs_accelerate_py.voice_router` | STT → retrieval → TTS receipt |
| Wallet adoption | `wallet_interface.helpers._voice_router_adapter` | Unified proxy receipt |

### Route census (content only today)

| Route | Approx edges | Today | Target action class |
| --- | --- | --- | --- |
| `live_agent` | ~6988 | Spoken handoff guidance | Human queue / warm transfer |
| `grounded_211_answer` | ~2143 | Grounded resource answer | Optional service open / cite |
| `repeat_or_restate` | ~2189 | Repeat frame | No side effect |
| `speech_unclear_clarification` | ~632 | Clarification | No side effect |
| `safety_guardrail_support` | ~563 | Safety wording | Emergency/handoff policy overlay |
| `calendar_event_support` | ~290 | Spoken appointment guidance | Calendar read/create (confirmed) |
| `wallet_document_support` | ~246 | Spoken document list | Open wallet docs surface |
| `provider_contact_support` | ~226 | Spoken phone scripts | Leave/read provider messages |
| `app_surface_navigation` | ~113 | Spoken navigation | Navigate app surface |
| `service_interaction_support` | ~82 | Spoken follow-up | Service interaction / callback |
| `template_guided_fallback` | ~86 | Safe fallback | No side effect |
| `clarifying_prompt` | ~65 | Clarifying question | Slot collection only |

### Action plane (partial)

| Asset | Status |
| --- | --- |
| `ipfs_accelerate_py.action_runtime` contracts/catalog/policy/CLI | Minimal fail-closed slice shipped; CLI pins `/usr/bin/true` only |
| `voice_bridge` route → logical action map | 5 tool-adjacent routes mapped; not GraphRAG-driven |
| Wallet `attach_action_surface` + UI Confirm | Proposal/confirm wired; execute dual-gated |
| UI agent tools (navigation, calendar surface, messages, service plans) | Exist in browser agent; **not** bound to voice DAG routes |
| Service action / interaction services | Exist; not receipted from voice admission |
| Human handoff / telephony transfer | Metadata-only escalation; no verified transfer |
| Domain pack binding Abby rows → action descriptors | Missing |
| Abby audio for “confirm this action?” / “action completed” | Missing as first-class frames |

## Architectural rule (non-negotiable)

```text
channel input
  -> STT / transcript
  -> Abby GraphRAG + slotted DAG route (content plane)
  -> grounded spoken response (+ precomputed audio when possible)
  -> logical ActionProposal (no executable locators)
  -> fail-closed policy / consent / confirmation
  -> deployment-owned catalog binding
  -> admitted adapter (app tool | calendar | messaging | handoff | CLI | MCP)
  -> ActionReceipt
  -> spoken outcome from Abby library or safe fallback
```

GraphRAG, exemplars, and models **never** choose executables, URLs, import
paths, or credentials. They may only name logical capabilities already declared
in a signed catalog.

## Gap matrix (what must be filled)

### G1 — Dual-plane schema for Abby library

The slotted DAG is a **content** DAG. It must gain optional, versioned links:

- `route` → `logical_action_id` (deployment map, not free text in content);
- `response_frame` → optional `action_prompt_frame` (confirmation wording);
- `response_frame` → optional `action_outcome_frame` (success/deny/fail speech);
- evidence CIDs remain content-only.

### G2 — Catalog of program actions

Operator-owned descriptors for at least:

| logical_action | Adapter family | Risk | Confirm |
| --- | --- | --- | --- |
| `handoff_live_agent` | human / telephony | human | yes / auto under policy |
| `open_app_surface` | python/UI tool | read | yes |
| `open_wallet_documents` | python/UI tool | read | yes |
| `read_calendar` | python/UI tool | read | yes |
| `create_calendar_reminder` | python/UI tool | write | yes + auth |
| `read_provider_messages` | python/UI tool | read | yes + auth |
| `leave_provider_message` | python/UI tool | write | yes + auth |
| `open_service_detail` | python/UI tool | read | yes |
| `schedule_service_callback` | service action | write | yes + auth |
| `escalate_safety` | human / emergency overlay | human | policy-driven |

### G3 — Retrieval that proposes actions without authority

GraphRAG returns `GroundedResponseCandidate` **and** zero-or-more
`ActionProposalCandidate`s ranked with evidence. Route strings from the slotted
DAG are inputs, not authority.

### G4 — Real adapters (not `/usr/bin/true`)

Replace probe CLI with:

1. **App tool adapter** over existing UI tool registry / surface API (server
   mediated where needed);
2. **Calendar adapter** for read/list/create reminder with tenant scope;
3. **Messaging adapter** for read inbox / leave provider message;
4. **Service interaction adapter** for callback / intake follow-up;
5. **Human handoff adapter** with queue + telephony transfer receipts;
6. Keep **CLI/MCP** for ops-only capabilities, still sandboxed.

### G5 — Abby audio continuity for actions

For each logical action, ensure library coverage for:

- proposal/confirmation prompt (“I can open your calendar—say yes to continue”);
- success outcome;
- denial / cancelled;
- failure / unknown.

Prefer precomputed IndexTTS rows linked by CID; generate only via the existing
Abby regeneration pipeline with Whisper validation.

### G6 — End-to-end proofs with the real dataset

Offline suites that:

- sample each route from `slotted_response_dag.json`;
- resolve library response + audio when present;
- emit proposal;
- deny without confirm;
- permit with fake adapter and assert receipt;
- prove live_agent never silently claims transfer success;
- prove calendar/message tools cannot run from retrieval alone.

### G7 — Parallel supervisor program

Goals/subgoals/tasks with:

- stable IDs and board namespace `voice-action-dag-abby-v1`;
- parallel lanes by ownership (content, catalog, retrieval, adapters, audio,
  handoff, e2e, ops);
- conflict policies so workers do not thrash the same files;
- symbolic-first validation before LLM repair.

## Package ownership

| Owner | Owns |
| --- | --- |
| `ipfs_datasets_py` | Abby migration of content→action links, domain-pack slices, GraphRAG action candidates, audio frame indexes |
| `ipfs_accelerate_py` | action_runtime expansion, adapters, policy, orchestration hooks, voice_router integration |
| parent `wallet_interface` | UI confirm/execute UX, app tool bindings, calendar/messages/service surfaces, API envelope |
| parent `docs/phone_dialog_generation` | slotted DAG rebuild outputs and manifests only via generation scripts |

## Parallel work graph (waves)

```text
wave-00 ops/bootstrap
  -> wave-01 inventory + doctrine (parallel)
  -> wave-02 abby content links + catalog + policy (parallel)
  -> wave-03 graphrag proposals + voice_router attach (parallel)
  -> wave-04 adapters: app / calendar / messages / service / handoff (parallel)
  -> wave-05 abby audio frames for action prompts/outcomes
  -> wave-06 e2e + release gates
```

## Explicit non-goals (this program)

- Replacing Abby TTS generation infrastructure.
- Full multi-tenant profile pack platform (see reusable voice-care plan).
- Unsupervised production execute with credentials enabled by default.
- Claiming exactly-once semantics for external telephony or SMS providers.

## Success criteria

1. Every tool-adjacent slotted route maps to a catalog logical action or an
   explicit `no_action` classification.
2. `live_agent` creates a receipted handoff request; spoken text never asserts
   completed transfer without provider confirmation.
3. Calendar read, message leave/read, app navigation, and service callback each
   have offline fake-adapter tests and at least one library-backed spoken path.
4. Abby precomputed audio resolver can hit confirmation and outcome frames for
   the pilot action set.
5. Supervisor preflight validates goals/tasks/profile and workers can run four
   parallel lanes without protected-path conflicts.
