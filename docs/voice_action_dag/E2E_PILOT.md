# Voice Action DAG × Abby — Offline E2E Pilot Matrix

Program: `voice-action-dag-abby-v1`  
Goal: `VOICE-ACTION-G140`  
Task: `VOICE-ACTION-029`  
Board namespace: `voice-action-dag-abby-v1`  
Evidence: `voice-action/e2e-matrix@1`, `voice-action/e2e-live-agent@1`, `voice-action/e2e-calendar-messages@1`  
Harness: `tests/e2e/voice_action_dag/test_abby_pilot_matrix.py`  
Example receipt: `data/voice_action_dag/e2e/matrix-receipt.example.json`

This document freezes the **offline multi-route e2e pilot** that walks every
slotted-DAG route sample through proposal → confirm → execute → speak using
**deterministic fake adapters**. No network, no live HF Space, and no real
telephony / SMS transport.

Validated by:

```bash
python -m pytest -q tests/e2e/voice_action_dag/test_abby_pilot_matrix.py
```

Companion doctrine: `docs/voice_action_dag/INTEGRATION_DOCTRINE.md`.  
Policy boundary: `docs/voice_action_dag/POLICY_MATRIX.md`.  
Handoff truthfulness: `docs/voice_action_dag/HANDOFF.md`.

## 1. Dual-plane pipeline under test

```text
slotted DAG route sample (content plane)
  -> optional logical ActionProposal (catalog id only)
  -> PilotPolicy admission (confirm / handoff / permit_*)
  -> offline fake adapter (authority plane)
  -> ActionReceipt
  -> spoken outcome selection (library or safe fallback)
```

Content plane samples are **compact recipes** (one user/assistant exemplar per
route). The harness does **not** re-emit full multi-megabyte DAG edges. Route
census is asserted against `data/voice_action_dag/baseline/route-gap-matrix.json`
and the content-plane action-link projection
`docs/phone_dialog_generation/slotted_response_action_links.json`.

## 2. Twelve-route matrix

| Route | Classification | Pilot logical action(s) | E2E assertion |
| --- | --- | --- | --- |
| `app_surface_navigation` | proposal-eligible / **tool-adjacent** | `open_app_surface` | confirm → fake app open succeeds |
| `calendar_event_support` | proposal-eligible / **tool-adjacent** | `read_calendar`, `create_calendar_reminder` | confirm (+ auth for write) → fake calendar |
| `clarifying_prompt` | **content-only** | `no_action` | no proposal, no adapter |
| `grounded_211_answer` | proposal-eligible | `open_service_detail` | confirm → fake service open (grounded `service_id`) |
| `live_agent` | proposal-eligible | `handoff_live_agent` | handoff request `accepted`; spoken success blocked without provider `succeeded` |
| `provider_contact_support` | proposal-eligible / **tool-adjacent** | `read_provider_messages`, `leave_provider_message` | confirm + auth → fake messaging |
| `repeat_or_restate` | **content-only** | `no_action` | no proposal, no adapter |
| `safety_guardrail_support` | safety-overlay | `escalate_safety` | policy `handoff` only; cannot widen to writes |
| `service_interaction_support` | proposal-eligible / **tool-adjacent** | `open_service_detail`, `schedule_service_callback` | confirm (+ auth for callback) → fake service store |
| `speech_unclear_clarification` | **content-only** | `no_action` | no proposal, no adapter |
| `template_guided_fallback` | **content-only** | `no_action` | no proposal, no adapter |
| `wallet_document_support` | proposal-eligible / **tool-adjacent** | `open_wallet_documents` | confirm → fake wallet surface open |

### 2.1 Tool-adjacent set (historical five)

```text
app_surface_navigation
wallet_document_support
calendar_event_support
service_interaction_support
provider_contact_support
```

For each tool-adjacent route the matrix proves:

1. **Unconfirmed** → `ActionDecisionKind.CONFIRM` and adapter does not succeed.
2. **Confirmed** (and authenticated when the descriptor requires auth) →
   `permit_read` / `permit_execute` and offline fake adapter returns
   `ActionStatus.SUCCEEDED`.
3. Spoken outcome role is `success` only after a succeeded receipt.

### 2.2 Content-only set

```text
clarifying_prompt
repeat_or_restate
speech_unclear_clarification
template_guided_fallback
```

These routes assert explicit **`no_action`**:

* `VoiceActionBridge.propose(...)` returns `None`.
* No catalog descriptor is invoked.
* Matrix case status is `no_action` with null receipt.

### 2.3 live_agent handoff semantics

| Stage | Decision / receipt | Spoken transfer success |
| --- | --- | --- |
| Policy admit | `HANDOFF` (`permits_execution=false`) | forbidden |
| Request created | receipt `accepted` | forbidden (`spoken_success_allowed=false`) |
| Provider unknown | receipt `unknown` | forbidden |
| Provider confirmed | receipt `succeeded` + confirmation token | allowed |

The matrix never claims a warm transfer completed from retrieval confidence or
from request creation alone.

### 2.4 Safety overlay

`safety_guardrail_support` → `escalate_safety` admits `HANDOFF` under policy /
overlay. The overlay **cannot** auto-permit unrelated writes such as
`create_calendar_reminder`.

## 3. Offline fake transports

| Family | Fake backend | Module |
| --- | --- | --- |
| App / wallet surfaces | `InMemoryAppSurfaceApi` | `wallet_interface.helpers._voice_app_action_binding` |
| Calendar | `InMemoryCalendarEventStore` | `action_runtime.adapters.calendar` |
| Messaging | `InMemoryProviderMessageStore` | `action_runtime.adapters.messaging` |
| Service interaction | `InMemoryServiceInteractionStore` | `action_runtime.adapters.service_interaction` |
| Human handoff | `InMemoryHandoffRequestStore` | `action_runtime.adapters.human_handoff` |
| Policy | `PilotPolicy` + `211ai-pilot-v1` catalog | `action_runtime.policy_pilot` / `catalog_211ai` |

All fakes are process-local. The suite autouses a socket deny so accidental
network calls fail closed.

## 4. Matrix receipt shape

Schema id: `voice-action/e2e-matrix-receipt@1`

Compact case rows (not full proposal/decision/receipt envelopes) record:

* `route`, `classification`, `logical_action`, `adapter`
* `status` (`no_action` | `confirm_execute_ok` | `handoff_accepted` | `safety_handoff`)
* unconfirmed / confirmed decision kinds
* receipt status / id when present
* spoken outcome role + `spoken_success_allowed`
* `network: denied`

See `data/voice_action_dag/e2e/matrix-receipt.example.json` for a durable
example covering all 12 routes.

## 5. Explicit non-goals

* Live Hugging Face Space / IndexTTS generation during the matrix run.
* Real PSTN warm transfer or SMS provider calls.
* Loading the full multi-megabyte `slotted_response_dag.json` edge dump into
  the pytest process (census is asserted via the baseline route gap matrix).
* Production execute enablement flags (`WALLET_VOICE_ACTION_EXECUTE_ENABLED`) —
  those are operator gates outside this offline proof.

## 6. Ownership

| Owner | Owns |
| --- | --- |
| `tests/e2e/voice_action_dag/test_abby_pilot_matrix.py` | Offline matrix harness + assertions |
| `docs/voice_action_dag/E2E_PILOT.md` | This freeze document |
| `data/voice_action_dag/e2e/matrix-receipt.example.json` | Example compact matrix receipt |
| Adapters / policy / catalog | Shared authority plane (read-only for this task) |
