# Voice Action DAG × Abby — Pilot Policy Matrix

Program: `voice-action-dag-abby-v1`  
Goal: `VOICE-ACTION-G040`  
Task: `VOICE-ACTION-007`  
Board namespace: `voice-action-dag-abby-v1`  
Policy revision: `pilot-policy-matrix-v1`  
Implementation: `ipfs_accelerate_py.action_runtime.policy_pilot`

This document freezes the **pilot admission matrix** for read, write, human
handoff, and safety overlay classes. Downstream adapters consume
`ActionDecision` outcomes only; they must not re-interpret risk or invent
executables.

Validated by:

```bash
python -m pytest -q ipfs_accelerate_py/test/test_action_policy_pilot.py
```

## 1. Non-negotiable invariants

| Invariant | Rule |
| --- | --- |
| Default deny | Unknown descriptors, channel/tenant mismatches, and unmapped human classes are `deny`. Execution is never silent. |
| Confirm for read | `RiskClass.READ` yields `confirm` until the authority plane records confirmation; only then `permit_read`. |
| Auth + confirm for write | `RiskClass.WRITE` requires confirmation **and** an authenticated tenant session before `permit_execute`. Confirmed-but-unauthenticated writes are `deny` (`auth_required`). |
| Handoff policy path | `handoff_live_agent` admits `handoff` (request creation) under policy or after confirm. Handoff never means verified transfer success. |
| Safety overlay isolation | An active safety overlay may force `handoff` **only** for the reviewed `escalate_safety` descriptor. It cannot widen to arbitrary descriptors or adapters. |
| Confidence non-authority | `ActionProposal.confidence` is never consulted. High retrieval confidence cannot upgrade deny/confirm into permit. |
| Risk class immutability | Decision `risk_class` is bound to the catalog descriptor. Context cannot reclassify or widen risk. |
| Pure policy | Policy evaluation performs no I/O, network, or process spawning. |

Companion doctrine: `docs/voice_action_dag/INTEGRATION_DOCTRINE.md` §4–5.

## 2. Admission context (authority plane)

Callers pass facts through `PilotAdmissionContext` (not through retrieval
metadata):

| Field | Meaning |
| --- | --- |
| `confirmed` | Explicit confirm recorded by UI / operator / authority path |
| `authenticated` | Tenant session passed auth / step-up |
| `session_tenant_id` | Authenticated tenant identity (must match proposal tenant when both set) |
| `safety_overlay` | Safety/crisis overlay active for this turn |
| `elevated_admin_grant` | Explicit elevated grant for admin-class actions |

Retrieval may populate `ActionProposal` fields such as `route`, `evidence`, and
`confidence`, but those fields never grant authority.

## 3. Class matrix

| Risk / family | Unconfirmed | Confirmed, no auth | Confirmed + auth | Safety overlay active |
| --- | --- | --- | --- | --- |
| **READ** (e.g. `open_app_surface`, `read_calendar`, `open_wallet_documents`, `open_service_detail`) | `confirm` | `permit_read` | `permit_read` | No widening; normal gates apply |
| **READ + auth** (e.g. `read_provider_messages`, metadata `auth_required=true`) | `confirm` | `deny` (`auth_required`) | `permit_read` | No widening |
| **WRITE** (e.g. `create_calendar_reminder`, `leave_provider_message`, `schedule_service_callback`) | `confirm` | `deny` (`auth_required`) | `permit_execute` | No widening |
| **ADMIN** | `deny` (`admin_default_deny`) unless elevated grant → then `confirm` | `deny` without auth | `permit_execute` with elevated + confirm + auth | No widening |
| **HUMAN / handoff** (`handoff_live_agent`) | `handoff` request under policy (`handoff_policy_request`) or `confirm` if auto-request disabled | `handoff` (`handoff_confirmed_request`) | `handoff` | No widening to non-handoff tools |
| **HUMAN / safety** (`escalate_safety`) | `handoff` via policy-driven path (`safety_policy_handoff`) | `handoff` | `handoff` | `handoff` (`safety_overlay_force_escalate`) **only** for this descriptor |

### 3.1 Decision kinds and execution

| Kind | `permits_execution` | Meaning |
| --- | --- | --- |
| `deny` | no | Hard reject |
| `confirm` | no | Awaiting authority-plane confirmation |
| `clarify` | no | Reserved; not used by the pilot matrix defaults |
| `handoff` | no | Admit **request creation** for human/safety path; not transfer success |
| `permit_read` | yes | Admitted read-class adapter invoke |
| `permit_execute` | yes | Admitted write/admin adapter invoke |

## 4. Pilot catalog binding

Logical actions from `catalog_211ai` / `211ai-pilot-v1`:

| logical_action | Risk | Auth required | Confirmation mode |
| --- | --- | --- | --- |
| `open_app_surface` | read | no | explicit |
| `open_wallet_documents` | read | no | explicit |
| `read_calendar` | read | no | explicit |
| `open_service_detail` | read | no | explicit |
| `read_provider_messages` | read | **yes** | explicit_plus_auth |
| `create_calendar_reminder` | write | **yes** | explicit_plus_auth |
| `leave_provider_message` | write | **yes** | explicit_plus_auth |
| `schedule_service_callback` | write | **yes** | explicit_plus_auth |
| `handoff_live_agent` | human | no | explicit_or_policy |
| `escalate_safety` | human | no | policy_driven |

## 5. Safety overlay (confused-deputy prevention)

1. When `safety_overlay=true` and the proposal targets `escalate_safety`, policy
   returns `handoff` with reason `safety_overlay_force_escalate`.
2. When `safety_overlay=true` and the proposal targets **any other** descriptor
   (including writes and app surfaces), the overlay **does not** permit that
   action. Normal class gates still apply.
3. Safety admission never invents adapter bindings, executables, or descriptor
   IDs outside the catalog.
4. Spoken safety wording remains content-plane; it is not authority.

## 6. Handoff truthfulness (policy boundary)

Policy may emit `ActionDecisionKind.HANDOFF` to admit a **handoff request**.
That decision:

- does **not** set `permits_execution`;
- does **not** assert telephony transfer completion;
- is distinct from a later adapter receipt with `ActionStatus.SUCCEEDED`.

See doctrine §5 for spoken/UI truthfulness rules.

## 7. Confidence non-upgrade examples

| Proposal confidence | Context | Outcome |
| --- | ---: | --- |
| `0.99` | unconfirmed read | `confirm` |
| `1.0` | unconfirmed write | `confirm` |
| `1.0` | confirmed write, unauthenticated | `deny` (`auth_required`) |
| `0.0` | confirmed read | `permit_read` |
| `0.0` | safety overlay + `escalate_safety` | `handoff` |
| `1.0` | safety overlay + `create_calendar_reminder` | `confirm` / normal write gates (not auto-permit) |

## 8. API surface

```python
from ipfs_accelerate_py.action_runtime.policy_pilot import (
    PilotAdmissionContext,
    PilotPolicy,
    build_pilot_policy,
)

policy = build_pilot_policy()  # uses 211-AI pilot catalog
decision = policy.decide(
    proposal,
    PilotAdmissionContext(
        confirmed=True,
        authenticated=True,
        session_tenant_id="211-ai",
    ),
)
```

## 9. Ownership

| Owner | Owns |
| --- | --- |
| `policy_pilot.py` | Pilot predicates and matrix evaluation |
| `POLICY_MATRIX.md` | This freeze document |
| `test_action_policy_pilot.py` | Default deny, confirm/auth gates, handoff, safety isolation, confidence non-upgrade |
| Adapters / executor | Consume decisions only; no policy re-interpretation |
