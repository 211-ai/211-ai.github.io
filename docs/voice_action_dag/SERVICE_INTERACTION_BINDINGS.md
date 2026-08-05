# Voice Action DAG × Abby — Service Interaction Adapter Bindings

Program: `voice-action-dag-abby-v1`  
Goal: `VOICE-ACTION-G100`  
Task: `VOICE-ACTION-019`  
Board namespace: `voice-action-dag-abby-v1`  
Implementation: `ipfs_accelerate_py.action_runtime.adapters.service_interaction`

This document freezes the **authority-plane service interaction adapter** for
`open_service_detail` and `schedule_service_callback`. Callback scheduling is
**idempotent on the proposal digest**. `service_id` must come from **grounded
evidence** (not free text alone). Unconfirmed / non-permitting decisions
**no-op** (no store mutation).

Validated by:

```bash
PYTHONPATH=ipfs_accelerate_py:ipfs_datasets_py:ipfs_kit_py \
  python -m pytest -q ipfs_accelerate_py/test/test_action_service_interaction_adapter.py
```

Companion doctrine: `docs/voice_action_dag/INTEGRATION_DOCTRINE.md`.  
Policy boundary: `docs/voice_action_dag/POLICY_MATRIX.md` §3–4.

## 1. Dual-plane boundary

```text
content plane (Abby / service_interaction_support | grounded_211_answer)
  -> logical ActionProposal only (open_service_detail | schedule_service_callback)
  -> evidence CIDs / service_id tokens remain content-plane grounding
  -> spoken frames remain advisory
authority plane (catalog / pilot policy / service_interaction adapter)
  -> ActionDecisionKind.PERMIT_READ | PERMIT_EXECUTE
  -> tenant-scoped ServiceInteractionStore + ActionReceipt
  -> redacted public_result (no notes dump; grounded service_id only)
```

Spoken Abby scripts for service interaction remain **content-only**. They never
invent descriptors, never invent a service target without evidence, and never
claim a callback was scheduled without a `succeeded` receipt.

## 2. Catalog binding

Pilot descriptors from `catalog_211ai` / `211ai-pilot-v1`:

| logical_action | descriptor_id | Risk | Side effect | Confirm | Auth |
| --- | --- | --- | --- | --- | --- |
| `open_service_detail` | `voice.python.open_service_detail.v1` | read | local_read | yes (explicit) | no |
| `schedule_service_callback` | `voice.workflow.schedule_service_callback.v1` | write | external_mutation | yes (explicit_plus_auth) | **yes** |

Default registration: `default_service_interaction_registrations()`.

Policy matrix (VOICE-ACTION-007):

| Action | Unconfirmed | Confirmed, no auth | Confirmed + auth |
| --- | --- | --- | --- |
| `open_service_detail` | `confirm` | `permit_read` | `permit_read` |
| `schedule_service_callback` | `confirm` | `deny` (`auth_required`) | `permit_execute` |

## 3. Adapter surface

```python
from ipfs_accelerate_py.action_runtime.adapters.service_interaction import (
    ServiceInteractionActionAdapter,
    ServiceInteractionInvocationContext,
    InMemoryServiceInteractionStore,
    default_service_interaction_registrations,
)

store = InMemoryServiceInteractionStore()
adapter = ServiceInteractionActionAdapter(
    default_service_interaction_registrations(), store=store
)

# Open: PERMIT_READ after confirm (auth optional under pilot catalog).
open_receipt = adapter.invoke(
    proposal=open_proposal,  # arguments.service_id in proposal.evidence
    decision=open_decision,  # kind == PERMIT_READ
    context=ServiceInteractionInvocationContext(
        confirmed=True,
        session_tenant_id="tenant-a",
    ),
)
assert open_receipt.status.value == "succeeded"
assert open_receipt.public_result["summary_redacted"] == "true"

# Schedule: PERMIT_EXECUTE after confirm + auth; idempotent on proposal digest.
schedule_receipt = adapter.invoke(
    proposal=schedule_proposal,
    decision=schedule_decision,  # kind == PERMIT_EXECUTE
    context=ServiceInteractionInvocationContext(
        confirmed=True,
        authenticated=True,
        session_tenant_id="tenant-a",
    ),
)
assert schedule_receipt.status.value == "succeeded"
assert schedule_receipt.public_result["idempotent_replay"] == "false"
```

### 3.1 Admission rule (fail closed)

| Decision kind | `open_service_detail` | `schedule_service_callback` |
| --- | --- | --- |
| `permit_read` | Allowed (after confirm re-check) | **Rejected** (`schedule_requires_permit_execute`) |
| `permit_execute` | Allowed (elevated) | Allowed (after confirm + auth re-check) |
| `deny` / `confirm` / `handoff` / `clarify` | Receipt `denied` (`decision_does_not_permit_execution`) — **no store write** | same |

Before store I/O the adapter also verifies proposal/decision binding
(proposal id, descriptor id, arguments digest, expiry) and registration
presence.

### 3.2 Adapter-boundary re-checks

| Gate | `open_service_detail` (default sandbox) | `schedule_service_callback` |
| --- | --- | --- |
| `confirmed` | required | required |
| `authenticated` | not required | required |
| Decision kind | `permit_read` or `permit_execute` | `permit_execute` only |
| Tenant | session/proposal required; mismatch fails closed | same |
| `service_id` | required + grounded in `proposal.evidence` | same |

## 4. Grounded `service_id` (non-negotiable)

Acceptance (VOICE-ACTION-019 / G100): **service IDs must come from grounded
evidence, not free text alone.**

1. Argument slot `service_id` is **required** for both logical actions.
2. `proposal.evidence` must be non-empty.
3. The service id must appear as an evidence token, either:
   - bare token equal to `service_id`, or
   - prefixed form: `service_id:…`, `service:…`, `service_doc_id:…`, `svc:…`.
4. Empty evidence → `service_id_requires_grounded_evidence` (no mutation).
5. Evidence present but id absent → `service_id_not_in_grounded_evidence`.

Helpers: `require_grounded_service_id()`, `grounded_service_tokens()`.

## 5. Idempotency on proposal digest

Acceptance: **`schedule_service_callback` is idempotent on proposal digest.**

```text
proposal_digest = content_digest({
  logical_action, descriptor_id, arguments_digest, tenant_id, evidence
})
```

| Event | Behavior |
| --- | --- |
| First admit for digest | Create callback; `idempotent_replay=false` |
| Replay same digest (same tenant) | Return existing `callback_id`; **no second row**; `idempotent_replay=true` |
| Different arguments / evidence / tenant | New digest → new callback |

Store API: `get_callback_by_digest(tenant_id, proposal_digest)` and
`schedule_callback(...)` (in-memory fake also de-dupes on digest).

## 6. Structured argument slots

Unexpected keys fail closed. Forbidden carriers (`url`, `body`, `command`,
`*_path`, `*_url`, etc.) are rejected.

### 6.1 `open_service_detail`

| Argument | Required | Notes |
| --- | --- | --- |
| `service_id` | **yes** | Safe id charset; must be grounded in evidence |
| `provider_id` | no | Optional safe id filter metadata |

### 6.2 `schedule_service_callback`

| Argument | Required | Notes |
| --- | --- | --- |
| `service_id` | **yes** | Grounded; see §4 |
| `callback_at` | no | ISO-8601 date/datetime when provided |
| `channel` | no | `phone` (default), `sms`, `email`, `voice`, `in_app`, `chat` |
| `client_id` | no | Safe id; defaults to session/tenant |
| `notes` | no | ≤ `max_notes_chars` (2000); redacted in receipts by default |
| `contact_preference` | no | Short free-text preference (≤ 64 chars) |
| `provider_id` | no | Optional safe id |

## 7. Tenant isolation

1. Effective tenant = `session_tenant_id` or `proposal.tenant_id` (session wins
   when both set and equal).
2. Mismatch → `service_interaction_rejected:tenant_session_mismatch` (no store
   write that could leak).
3. Missing tenant → `tenant_required`.
4. Callbacks are always listed/stored under the resolved tenant.
5. Tenant-scoped catalog rows (`ServiceDetailRecord.tenant_id`) are invisible
   to other tenants (`found=false`, no summary leak).

## 8. Redacted public receipts

### 8.1 `open_service_detail` success `public_result`

| Field | Meaning |
| --- | --- |
| `ok` / `found` | Status flags |
| `tenant_id` / `service_id` | Scoped identity |
| `title` / `provider_name` / `program_name` / `status` | Non-secret labels |
| `title_digest` / `summary_digest` | Content digests |
| `redacted_summary` | `service_id \| title_preview \| provider` |
| `summary_redacted` | `"true"` under default sandbox |

Default sandbox **never** puts raw `summary` into the public receipt.

### 8.2 `schedule_service_callback` success `public_result`

| Field | Meaning |
| --- | --- |
| `ok` | `"true"` |
| `callback_id` | New or replayed id (`cb-…`) |
| `tenant_id` / `service_id` / `channel` / `callback_at` / `client_id` / `status` | Structured fields |
| `proposal_digest` | Idempotency key |
| `idempotent_replay` | `"true"` on digest replay |
| `notes_digest` | Digest of private notes |
| `notes_redacted` / `notes_present` / `notes_chars` | Presence metadata only |
| `interaction_type` | `"callback_requested"` |

## 9. Stores

| Store | Role |
| --- | --- |
| `InMemoryServiceInteractionStore` | Process-local fake for unit tests and offline fakes |
| `ServiceInteractionStore` (protocol) | Injected product backend (wallet service interaction binding in VOICE-ACTION-020) |

No network, no telephony carrier calls, and no process spawning in this adapter.

## 10. Sandbox defaults

| Policy field | Default |
| --- | --- |
| `max_notes_chars` | 2000 |
| `max_title_chars` | 200 |
| `max_services_returned` | 50 |
| `redact_notes_in_receipts` | `true` |
| `require_confirm_for_schedule` | `true` |
| `require_auth_for_schedule` | `true` |
| `require_confirm_for_open` | `true` |
| `require_auth_for_open` | `false` |

## 11. Ownership

| Owner | Owns |
| --- | --- |
| `adapters/service_interaction.py` | Service interaction adapter, sandbox, fake store, grounding, idempotency |
| `SERVICE_INTERACTION_BINDINGS.md` | This freeze document |
| `test_action_service_interaction_adapter.py` | Idempotency, grounding, auth+confirm, no-op, tenant isolation |
| Wallet binding (VOICE-ACTION-020) | Product `serviceActionService` / `serviceInteractionService` transport |
| Pilot policy / catalog | Decision kinds; not adapter re-interpretation |

## 12. Non-goals (this task)

* Live telephony / SMS carrier side effects
* Product wallet API wiring (VOICE-ACTION-020)
* Widening the pilot catalog or policy matrix
* Treating spoken free text as a service identifier without evidence
* Exactly-once guarantees across external provider systems
