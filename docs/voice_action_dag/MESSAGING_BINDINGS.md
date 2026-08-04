# Voice Action DAG × Abby — Messaging Adapter Bindings

Program: `voice-action-dag-abby-v1`  
Goal: `VOICE-ACTION-G090`  
Task: `VOICE-ACTION-017`  
Board namespace: `voice-action-dag-abby-v1`  
Implementation: `ipfs_accelerate_py.action_runtime.adapters.messaging`

This document freezes the **authority-plane messaging adapter** bindings for
reading a tenant-scoped provider inbox and leaving a message with a service
provider. Downstream wallet bindings (VOICE-ACTION-018) inject a product store;
this module owns fail-closed admission checks, body bounds, and receipt
redaction.

Validated by:

```bash
python -m pytest -q ipfs_accelerate_py/test/test_action_messaging_adapter.py
```

## 1. Dual-plane boundary

```text
content plane (Abby / GraphRAG / slotted DAG)
  -> logical ActionProposal only
     (read_provider_messages | leave_provider_message)
authority plane (catalog / pilot policy / messaging adapter)
  -> ActionDecision + ActionReceipt (bodies redacted by default)
```

Spoken Abby scripts for `provider_contact_support` remain **content-only**.
They never send SMS, invent descriptors, or widen tenant scope.

## 2. Catalog bindings

Pilot descriptors from `catalog_211ai` / `211ai-pilot-v1`:

| logical_action | descriptor_id | Risk | Side effect | Confirm | Auth |
| --- | --- | --- | --- | --- | --- |
| `read_provider_messages` | `voice.python.read_provider_messages.v1` | read | local_read | yes | **yes** |
| `leave_provider_message` | `voice.python.leave_provider_message.v1` | write | external_mutation | yes | **yes** |

Default registrations: `default_messaging_registrations()`.

Policy matrix (VOICE-ACTION-007): both actions require confirmation; both
require an authenticated tenant session before `permit_read` /
`permit_execute`. See `docs/voice_action_dag/POLICY_MATRIX.md`.

## 3. Adapter surface

```python
from ipfs_accelerate_py.action_runtime.adapters.messaging import (
    InMemoryProviderMessageStore,
    MessagingActionAdapter,
    MessagingInvocationContext,
    default_messaging_registrations,
)

store = InMemoryProviderMessageStore()
adapter = MessagingActionAdapter(default_messaging_registrations(), store=store)

receipt = adapter.invoke(
    proposal=proposal,
    decision=decision,  # must permit_execution
    context=MessagingInvocationContext(
        confirmed=True,
        authenticated=True,
        session_tenant_id="tenant-a",
    ),
)
```

### 3.1 Invocation context (adapter re-check)

| Field | Meaning |
| --- | --- |
| `confirmed` | Explicit confirm recorded by UI / operator / authority path |
| `authenticated` | Tenant session passed auth / step-up |
| `session_tenant_id` | Authenticated tenant identity (must match proposal tenant) |

A forged `ActionDecision` with `permits_execution=true` is **not** sufficient:
the adapter re-checks confirm + auth and tenant binding before any store I/O.

### 3.2 Store protocol

`ProviderMessageStore` is injected:

| Method | Behavior |
| --- | --- |
| `list_messages(tenant_id=…)` | Return only rows for that tenant |
| `leave_message(tenant_id=…)` | Persist outbound client→provider message |

`InMemoryProviderMessageStore` is the offline fake for unit tests and wallet
binding fakes. Production wallet surfaces supply their own store in
VOICE-ACTION-018.

## 4. Argument slots

### 4.1 `read_provider_messages`

| Argument | Required | Notes |
| --- | --- | --- |
| `provider_id` | no | Optional filter; safe id charset |
| `client_id` | no | Optional filter; safe id charset |
| `limit` | no | Capped by `MessagingSandboxPolicy.max_messages_returned` (default 50) |

Unexpected keys fail closed.

### 4.2 `leave_provider_message`

| Argument | Required | Notes |
| --- | --- | --- |
| `provider_id` | **yes** | Safe id charset |
| `body` | **yes** | Non-empty; length ≤ `max_body_chars` (default **2000**) |
| `client_id` | no | Defaults to session/tenant id |
| `channel` | no | One of `in_app`, `sms`, `email` (default `in_app`) |
| `subject` | no | Length ≤ `max_subject_chars` (default 200) |

**Body bound:** default `DEFAULT_MAX_BODY_CHARS = 2000` (hard ceiling 16384 on
policy construction). Oversize or empty bodies yield
`messaging_rejected:body_exceeds_max_chars:…` / non-empty errors — no store
write.

**Not treated as SMS send authority:** channel `sms` only labels the store
record. Live carrier delivery requires a separate reviewed descriptor and
transport outside this adapter.

## 5. Tenant isolation

1. Effective tenant = `session_tenant_id` or `proposal.tenant_id`.
2. If both are set and differ → `tenant_session_mismatch` (fail closed).
3. If neither is set → `tenant_required`.
4. Reads filter store rows by effective tenant only.
5. Adapter drops any store row whose `tenant_id` does not match (defense in
   depth).
6. Leave stamps the stored record with the effective tenant; store returning a
   different tenant fails closed.

Cross-tenant dumps are never present in receipts.

## 6. Receipt redaction (default)

`MessagingSandboxPolicy.redact_bodies_in_receipts = True` by default.

| Receipt field | Leave | Read |
| --- | --- | --- |
| Raw `body` | **omitted** | **omitted** |
| Full subject list | omitted | omitted (`subjects_redacted=true`) |
| `body_digest` / `body_digests` | present | present |
| `message_id` / `message_ids` | present | present |
| `message_count` | n/a | present |
| `tenant_id`, `provider_id`, `status` | present | present |
| `bodies_redacted` | `"true"` | `"true"` |

Voice / UI layers must not re-hydrate bodies from digests without a separate
authorized product surface. Spoken Abby outcome frames remain content-plane.

## 7. Decision binding checks

Before store I/O the adapter verifies:

| Check | Error |
| --- | --- |
| `decision.permits_execution` | `DENIED` + `decision_does_not_permit_execution:…` |
| proposal/decision id match | `proposal_decision_mismatch` |
| descriptor match | `descriptor_decision_mismatch` |
| `arguments_digest` match | `arguments_digest_mismatch` |
| decision not expired | `decision_expired` |
| registration exists | `no_messaging_registration` |
| leave decision kind | must be `permit_execute` |
| read decision kind | `permit_read` or `permit_execute` |

## 8. Pilot policy integration examples

| Context | `leave_provider_message` | Adapter outcome |
| --- | --- | --- |
| unconfirmed | policy → `confirm` | adapter `DENIED` (no permit) |
| confirmed, unauthenticated | policy → `deny` (`auth_required`) | no permit |
| confirmed + auth | policy → `permit_execute` | leave succeeds; body redacted |
| confirmed + auth, body > max | policy → `permit_execute` | adapter `FAILED` body bound |

| Context | `read_provider_messages` | Adapter outcome |
| --- | --- | --- |
| unconfirmed | policy → `confirm` | no permit |
| confirmed, unauthenticated | policy → `deny` (`auth_required`) | no permit |
| confirmed + auth | policy → `permit_read` | tenant-scoped list; bodies redacted |

## 9. Ownership

| Owner | Owns |
| --- | --- |
| `adapters/messaging.py` | Adapter, sandbox policy, in-memory store, redaction |
| `MESSAGING_BINDINGS.md` | This freeze document |
| `test_action_messaging_adapter.py` | Confirm+auth, body bounds, redaction, tenant isolation |
| Wallet VOICE-ACTION-018 | Product store binding / UI surfaces |
| Abby content / retrieval | Spoken scripts and logical proposals only |

## 10. Non-goals

- Live SMS/email carrier delivery or telephony transfer
- Treating spoken phone numbers as executable sends
- Returning raw message bodies on voice receipts by default
- Cross-tenant inbox dumps for operators without a separate admin path
- Widening catalog descriptors from content-plane packs
