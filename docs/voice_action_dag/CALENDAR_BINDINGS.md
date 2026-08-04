# Voice Action DAG × Abby — Calendar Adapter Bindings

Program: `voice-action-dag-abby-v1`  
Goal: `VOICE-ACTION-G080`  
Task: `VOICE-ACTION-015`  
Board namespace: `voice-action-dag-abby-v1`  
Implementation: `ipfs_accelerate_py.action_runtime.adapters.calendar`

This document freezes the **authority-plane calendar adapter** for
`read_calendar` and `create_calendar_reminder`. Reads return **redacted
summaries** only. Writes require **confirmation and an authenticated tenant
session**. Arguments are **structured slots only** — raw ICS / free-text calendar
blobs are rejected.

Validated by:

```bash
python -m pytest -q ipfs_accelerate_py/test/test_action_calendar_adapter.py
```

Companion doctrine: `docs/voice_action_dag/INTEGRATION_DOCTRINE.md`.  
Policy boundary: `docs/voice_action_dag/POLICY_MATRIX.md` §3–4.

## 1. Dual-plane boundary

```text
content plane (Abby / calendar_event_support route / slotted DAG)
  -> logical ActionProposal only (read_calendar | create_calendar_reminder)
  -> spoken frames remain advisory
authority plane (catalog / pilot policy / calendar adapter)
  -> ActionDecisionKind.PERMIT_READ | PERMIT_EXECUTE
  -> tenant-scoped CalendarEventStore + ActionReceipt
  -> redacted public_result (no notes/ICS dump)
```

Spoken Abby scripts for calendar remain **content-only**. They never invent
descriptors, never inject raw ICS from model text, and never claim a reminder
was created without a `succeeded` receipt.

## 2. Catalog binding

Pilot descriptors from `catalog_211ai` / `211ai-pilot-v1`:

| logical_action | descriptor_id | Risk | Side effect | Confirm | Auth |
| --- | --- | --- | --- | --- | --- |
| `read_calendar` | `voice.python.read_calendar.v1` | read | local_read | yes (explicit) | no |
| `create_calendar_reminder` | `voice.python.create_calendar_reminder.v1` | write | local_write | yes (explicit_plus_auth) | **yes** |

Default registration: `default_calendar_registrations()`.

Policy matrix (VOICE-ACTION-007):

| Action | Unconfirmed | Confirmed, no auth | Confirmed + auth |
| --- | --- | --- | --- |
| `read_calendar` | `confirm` | `permit_read` | `permit_read` |
| `create_calendar_reminder` | `confirm` | `deny` (`auth_required`) | `permit_execute` |

## 3. Adapter surface

```python
from ipfs_accelerate_py.action_runtime.adapters.calendar import (
    CalendarActionAdapter,
    CalendarInvocationContext,
    InMemoryCalendarEventStore,
    default_calendar_registrations,
)

store = InMemoryCalendarEventStore()
adapter = CalendarActionAdapter(default_calendar_registrations(), store=store)

# Read: PERMIT_READ after confirm (auth optional under pilot catalog).
read_receipt = adapter.invoke(
    proposal=read_proposal,
    decision=read_decision,  # kind == PERMIT_READ
    context=CalendarInvocationContext(
        confirmed=True,
        session_tenant_id="tenant-a",
    ),
)
assert read_receipt.status.value == "succeeded"
assert read_receipt.public_result["summaries_redacted"] == "true"
assert "notes" not in read_receipt.public_result

# Create: PERMIT_EXECUTE after confirm + auth.
create_receipt = adapter.invoke(
    proposal=create_proposal,
    decision=create_decision,  # kind == PERMIT_EXECUTE
    context=CalendarInvocationContext(
        confirmed=True,
        authenticated=True,
        session_tenant_id="tenant-a",
    ),
)
assert create_receipt.status.value == "succeeded"
assert create_receipt.public_result["notes_redacted"] == "true"
```

### 3.1 Admission rule (fail closed)

| Decision kind | `read_calendar` | `create_calendar_reminder` |
| --- | --- | --- |
| `permit_read` | Allowed (after confirm re-check) | **Rejected** (`create_requires_permit_execute`) |
| `permit_execute` | Allowed (elevated) | Allowed (after confirm + auth re-check) |
| `deny` / `confirm` / `handoff` / `clarify` | Receipt `denied` (`decision_does_not_permit_execution`) | same |

Before store I/O the adapter also verifies proposal/decision binding
(proposal id, descriptor id, arguments digest, expiry) and registration
presence.

### 3.2 Adapter-boundary re-checks

| Gate | `read_calendar` (default sandbox) | `create_calendar_reminder` |
| --- | --- | --- |
| `confirmed` | required | required |
| `authenticated` | not required | required |
| Decision kind | `permit_read` or `permit_execute` | `permit_execute` only |
| Tenant | session/proposal required; mismatch fails closed | same |

## 4. Structured argument slots

Unexpected keys fail closed. Forbidden carriers (`ics`, `raw_ics`, `vevent`,
`body`, `*_path`, etc.) are rejected. Values containing ICS markers
(`BEGIN:VCALENDAR`, `BEGIN:VEVENT`, …) are rejected.

### 4.1 `read_calendar`

| Argument | Required | Notes |
| --- | --- | --- |
| `limit` | no | Integer ≥ 1; capped by `max_events_returned` (default 50) |
| `starts_after` | no | ISO-8601 date/datetime lower bound (inclusive) |
| `ends_before` | no | ISO-8601 date/datetime upper bound (inclusive) |
| `event_id` | no | Safe id charset; tenant-scoped lookup only |

### 4.2 `create_calendar_reminder`

| Argument | Required | Notes |
| --- | --- | --- |
| `title` | **yes** | Non-empty; ≤ `max_title_chars` (200); no ICS markers |
| `starts_at` | **yes** | ISO-8601 date or datetime |
| `ends_at` | no | ISO-8601; if omitted, uses `duration_minutes` or equals `starts_at` |
| `duration_minutes` | no | Non-negative integer; used when `ends_at` omitted |
| `notes` | no | ≤ `max_notes_chars` (2000); redacted in receipts by default |
| `location` | no | ≤ `max_location_chars` (200); presence-only in redacted receipts |
| `all_day` | no | `true` / `false` (default false) |
| `reminder_minutes_before` | no | Non-negative integer; capped by sandbox (default max 30 days) |

**No raw ICS injection from model text.** Product UI may later render `.ics`
downloads from structured fields (VOICE-ACTION-016 wallet binding); the voice
adapter never accepts ICS blobs as proposal arguments.

## 5. Tenant isolation

1. Effective tenant = `session_tenant_id` or `proposal.tenant_id` (session wins
   when both set and equal).
2. Mismatch → `calendar_rejected:tenant_session_mismatch` (no store I/O that
   could leak).
3. Missing tenant → `tenant_required`.
4. `list_events` / `create_reminder` are always called with the resolved tenant.
5. Read results are re-filtered so a buggy store cannot return other tenants.
6. Cross-tenant `event_id` lookups return empty for the caller’s tenant (not a
   leak of existence details beyond “not in your calendar”).

## 6. Redacted summaries (public receipts)

### 6.1 `read_calendar` success `public_result`

| Field | Meaning |
| --- | --- |
| `ok` | `"true"` |
| `tenant_id` | Scoped tenant |
| `event_count` | Number of events returned |
| `event_ids` | Comma-joined event ids |
| `title_digests` / `notes_digests` | Content digests (not plaintext notes) |
| `starts_at` | Comma-joined structured start times |
| `redacted_summaries` | `starts_at \| title_preview` lines (notes omitted) |
| `summaries_redacted` / `notes_redacted` | `"true"` under default sandbox |

Default sandbox **never** puts `notes` or full locations into the public
receipt. Private notes remain in the injected store for product backends only.

### 6.2 `create_calendar_reminder` success `public_result`

| Field | Meaning |
| --- | --- |
| `ok` | `"true"` |
| `event_id` | New id (`evt-…`) |
| `tenant_id` / `title` / `starts_at` / `ends_at` | Structured non-secret fields |
| `all_day` / `reminder_minutes_before` / `status` | Structured flags |
| `notes_digest` / `title_digest` | Digests |
| `notes_redacted` | `"true"` by default |
| `notes_present` / `location_present` / `notes_chars` | Presence metadata only |
| `redacted_summary` | One-line privacy-safe summary |

## 7. Stores

| Store | Role |
| --- | --- |
| `InMemoryCalendarEventStore` | Process-local fake for unit tests and offline fakes |
| `CalendarEventStore` (protocol) | Injected product backend (wallet calendar service in VOICE-ACTION-016) |

No network, no filesystem calendar I/O, and no process spawning in this adapter.

## 8. Sandbox defaults

| Policy field | Default |
| --- | --- |
| `max_title_chars` | 200 |
| `max_notes_chars` | 2000 |
| `max_location_chars` | 200 |
| `max_events_returned` | 50 |
| `max_reminder_minutes_before` | 43200 (30 days) |
| `redact_notes_in_receipts` | `true` |
| `require_confirm_for_create` | `true` |
| `require_auth_for_create` | `true` |
| `require_confirm_for_read` | `true` |
| `require_auth_for_read` | `false` |

## 9. Ownership

| Owner | Owns |
| --- | --- |
| `adapters/calendar.py` | Calendar adapter, sandbox, fake store, redaction |
| `CALENDAR_BINDINGS.md` | This freeze document |
| `test_action_calendar_adapter.py` | Redaction, auth+confirm, tenant isolation, structured slots |
| Wallet binding (VOICE-ACTION-016) | Product calendar service + fake transport |
| Pilot policy / catalog | Decision kinds; not adapter re-interpretation |

## 10. Non-goals (this task)

* Live Google/Outlook/Apple Calendar network APIs
* Browser `.ics` download UX (wallet UI / later binding)
* Widening the pilot catalog or policy matrix
* Treating spoken free text as an executable ICS payload
