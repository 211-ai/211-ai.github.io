# Voice Action DAG × Abby — Safety Overlay Policy (`escalate_safety`)

Program: `voice-action-dag-abby-v1`  
Goal: `VOICE-ACTION-G110`  
Task: `VOICE-ACTION-023`  
Board namespace: `voice-action-dag-abby-v1`  
Policy revision: `pilot-policy-matrix-v1` (safety overlay slice)  
Implementation:

* `ipfs_accelerate_py.action_runtime.policy_pilot` — admission predicates
* `ipfs_accelerate_py.action_runtime.voice_bridge` — route classification / proposal
* `ipfs_accelerate_py.action_runtime.catalog_211ai` — reviewed descriptor binding
* `ipfs_accelerate_py.action_runtime.contracts` — locator-free proposal contract

This document freezes the **safety overlay policy** for the
`safety_guardrail_support` content route and the reviewed `escalate_safety`
logical action. Under policy the overlay may **force handoff / escalate** for
that descriptor only. It **cannot** open calendar, messaging, app surfaces, or
any other arbitrary tool. Emergency destinations and queues are
**deployment-config-bound**, never model- or transcript-bound.

Validated by:

```bash
python -m pytest -q ipfs_accelerate_py/test/test_action_safety_overlay.py
```

Companion doctrine: `docs/voice_action_dag/INTEGRATION_DOCTRINE.md` §4–5.  
Policy matrix: `docs/voice_action_dag/POLICY_MATRIX.md` §5.  
Handoff adapter boundary: `docs/voice_action_dag/HANDOFF.md`.

## 1. Dual-plane boundary

```text
content plane (Abby / safety_guardrail_support / crisis wording)
  -> route classification = safety-overlay
  -> logical ActionProposal only (escalate_safety)
  -> spoken safety scripts remain advisory
  -> never embeds executables, URLs, phone endpoints, or credentials

authority plane (catalog / pilot policy / handoff adapter)
  -> PilotAdmissionContext.safety_overlay = true
  -> ActionDecisionKind.HANDOFF (safety_overlay_force_escalate)
  -> destination / queue / emergency binding from deployment config
  -> receipted request path; spoken transfer success only with provider confirm
```

Content-plane crisis wording may advise a caller to seek immediate help. That
speech is **not** authority to dial, transfer, open tools, or invent endpoints.

## 2. Route and catalog binding

| Layer | Value |
| --- | --- |
| Slotted-DAG route | `safety_guardrail_support` |
| Route classification | `safety-overlay` (`ROUTE_CLASSIFICATION_SAFETY_OVERLAY`) |
| Logical action | `escalate_safety` |
| Pilot descriptor id | `voice.human.escalate_safety.v1` |
| Adapter family | `human` |
| Risk class | `human` |
| Side effect | `network` |
| Confirmation mode | `policy_driven` |
| Family metadata | `safety` |

Default bridge map (deployment-owned, not pack-owned):

```text
safety_guardrail_support  ->  escalate_safety
```

Pilot catalog registration (`catalog_211ai` / `211ai-pilot-v1`) pins
`voice.human.escalate_safety.v1`. Domain packs and Abby exemplars may
**reference** this logical action; they cannot widen the catalog or embed
locators.

Related human path (not tool widening):

| logical_action | When admitted |
| --- | --- |
| `escalate_safety` | Safety overlay force path, or policy-driven auto-handoff |
| `handoff_live_agent` | Handoff policy path (`handoff_policy_request` / confirmed) |

Both emit `ActionDecisionKind.HANDOFF` with `permits_execution == false`.
Neither is a calendar, messaging, or app-surface permit.

## 3. Policy matrix (safety slice)

Admission facts come only from `PilotAdmissionContext` (authority plane):

| Field | Safety meaning |
| --- | --- |
| `safety_overlay` | Crisis / safety overlay active for this turn |
| `confirmed` | Explicit confirm (used when auto-handoff is disabled) |
| `authenticated` | Not required for safety handoff request creation |
| `session_tenant_id` | Tenant binding when present |

### 3.1 Force escalate under overlay

| Proposal | Context | Decision | Reason |
| --- | --- | --- | --- |
| `escalate_safety` | `safety_overlay=true` | `handoff` | `safety_overlay_force_escalate` |
| `escalate_safety` | overlay off, `safety_policy_auto_handoff=true` (default) | `handoff` | `safety_policy_handoff` |
| `escalate_safety` | overlay off, auto-handoff disabled, unconfirmed | `confirm` | `confirmation_required` |
| `escalate_safety` | overlay off, auto-handoff disabled, confirmed | `handoff` | `safety_confirmed_handoff` |
| `handoff_live_agent` | handoff auto-request (default) | `handoff` | `handoff_policy_request` |

`handoff` admits **request creation only**. It does not claim telephony transfer
success, does not set `permits_execution`, and does not open tools.

### 3.2 Isolation — no calendar / messages / tool widening

When `safety_overlay=true`, policy **never** auto-permits non-safety
descriptors. Normal class gates still apply:

| Target under active overlay | Expected kind (unconfirmed) | Notes |
| --- | --- | --- |
| `read_calendar` | `confirm` | No `permit_read` from overlay alone |
| `create_calendar_reminder` | `confirm` | Write still needs confirm + auth |
| `read_provider_messages` | `confirm` | Messaging not opened by overlay |
| `leave_provider_message` | `confirm` | Messaging write not opened by overlay |
| `open_app_surface` / `open_wallet_documents` / `open_service_detail` | `confirm` | Surfaces not widened |
| `schedule_service_callback` | `confirm` | Service write not widened |
| `escalate_safety` | `handoff` | **Only** reviewed safety descriptor forced |

Even with overlay + confirm, writes still require auth (`deny` /
`auth_required`). Overlay cannot reclassify risk or invent descriptors.

### 3.3 Confidence non-authority

`ActionProposal.confidence` is never consulted. High retrieval confidence
cannot:

* upgrade a non-safety tool into `handoff` or `permit_*`;
* invent a destination or adapter binding;
* bypass confirm/auth for calendar or messages.

## 4. Emergency destinations are config-bound

### 4.1 Rule

**Models, transcripts, GraphRAG evidence, and free-text slots do not choose
emergency destinations.** Operational destinations (queues, emergency routing
profiles, reviewed endpoint bindings, spoken destination labels used by
adapters) are owned by deployment configuration and reviewed catalog/policy
artifacts.

| Source | May choose destination? |
| --- | --- |
| Model / LLM free text | **No** |
| Transcript / STT | **No** |
| GraphRAG evidence CIDs | **No** |
| Content-plane spoken scripts | Advisory only; not authority |
| Reviewed catalog descriptor | Logical action only; no locator keys |
| Deployment config (sandbox policy, queue defaults, operator profile) | **Yes** |
| Provider / telephony backend after admitted handoff | **Yes** (receipted) |

### 4.2 Hard denials that keep destinations non-model-bound

1. **Proposal contract** (`ActionProposal`) rejects argument keys:
   `command`, `argv`, `executable`, `cwd`, `env`, `shell`, `import_path`,
   `url`, and any `*_path` key.
2. **Voice bridge** rejects the same locator classes (plus `credentials`,
   `secret`, `webhook`) before a proposal is emitted.
3. **Pilot catalog** forbids locator keys in descriptor metadata
   (`FORBIDDEN_LOCATOR_KEYS`: `url`, `webhook`, `host`, `port`, …).
4. Free-text transcript passed to `propose_from_voice_route` never invents
   descriptors or destinations; only the deployment route → logical map binds
   `safety_guardrail_support` → `escalate_safety`.
5. Handoff routing slots that *are* allowed (`queue`, `priority`, `reason`,
   `summary`, `preferred_channel`) are constrained ids / bounded text. Default
   queue / priority come from `HandoffSandboxPolicy` (deployment config), not
   from model-authored endpoint URLs.

### 4.3 What content may say

Spoken Abby safety frames may include public crisis guidance (for example
“If danger is immediate, call nine one one now.”). That is **content-plane
speech**. It does not:

* inject a dialable endpoint into an `ActionProposal`;
* authorize PSTN/SIP transfer;
* open calendar or messages;
* override deployment emergency routing config.

## 5. End-to-end authority path

```text
safety_guardrail_support (content route)
  -> VoiceActionBridge / propose_from_voice_route
       classification = safety-overlay
       logical_action  = escalate_safety
       arguments       = {}  (no locators)
  -> PilotPolicy.decide(..., PilotAdmissionContext(safety_overlay=True))
       kind   = handoff
       reason = safety_overlay_force_escalate
       permits_execution = false
  -> human / emergency handoff adapter (request creation only)
       durable HandoffRequest | safety request receipt
       destination / queue from deployment config
  -> spoken outcome frames
       success only when provider-confirmed succeeded receipt exists
```

## 6. API surface (evaluation)

```python
from ipfs_accelerate_py.action_runtime.catalog_211ai import (
    build_pilot_catalog,
    logical_action_to_descriptor_id,
)
from ipfs_accelerate_py.action_runtime.policy_pilot import (
    PilotAdmissionContext,
    build_pilot_policy,
)
from ipfs_accelerate_py.action_runtime.voice_bridge import (
    ROUTE_CLASSIFICATION_SAFETY_OVERLAY,
    VoiceActionBridge,
)

catalog = build_pilot_catalog()
bridge = VoiceActionBridge(
    catalog=catalog,
    route_map={"safety_guardrail_support": "escalate_safety"},
    descriptor_map=dict(logical_action_to_descriptor_id()),
)
proposal = bridge.propose(route="safety_guardrail_support")
assert proposal is not None
assert proposal.logical_action == "escalate_safety"
assert proposal.metadata.get("route_classification") == ROUTE_CLASSIFICATION_SAFETY_OVERLAY

policy = build_pilot_policy(catalog)
decision = policy.decide(
    proposal,
    PilotAdmissionContext(safety_overlay=True),
)
assert decision.kind.value == "handoff"
assert decision.reason == "safety_overlay_force_escalate"
assert not decision.permits_execution
```

## 7. Ownership

| Owner | Owns |
| --- | --- |
| `policy_pilot.py` | `safety_overlay` force-escalate predicate; isolation from other classes |
| `voice_bridge.py` | `safety-overlay` classification; route → `escalate_safety` map |
| `catalog_211ai.py` | Reviewed `escalate_safety` descriptor; locator-free metadata |
| `contracts.py` | Proposal argument bans (no model-bound destinations) |
| `SAFETY_OVERLAY.md` | This freeze document |
| `test_action_safety_overlay.py` | Force escalate, calendar/messages deny, config-bound destinations |
| Content / Abby library | Safety wording and outcome frames only |
| Deployment operators | Emergency destination / queue / provider profile config |

## 8. Non-goals

* Opening calendar, messages, wallet documents, or app surfaces under safety overlay
* Letting models or transcripts supply emergency phone numbers, URLs, or webhooks as proposal arguments
* Claiming warm-transfer or emergency-connect success without a provider-confirmed receipt
* Widening catalog descriptors from content-plane packs
* Auto-executing CLI/MCP tools because a safety route fired
* Replacing live emergency services with model-invented destinations

## 9. Acceptance checklist (VOICE-ACTION-023)

| Criterion | Evidence |
| --- | --- |
| `safety_guardrail_support` can force `escalate_safety` / handoff under policy | Route → proposal → `safety_overlay_force_escalate` / `safety_policy_handoff` |
| Cannot open calendar / messages | Overlay leaves calendar + messaging behind normal confirm/auth gates |
| Emergency destinations are config-bound, not model-bound | Locator bans + catalog forbid + empty default arguments + deployment queue defaults |
