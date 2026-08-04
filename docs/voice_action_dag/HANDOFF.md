# Voice Action DAG × Abby — Human Handoff Adapter

Program: `voice-action-dag-abby-v1`  
Goal: `VOICE-ACTION-G110`  
Task: `VOICE-ACTION-021`  
Board namespace: `voice-action-dag-abby-v1`  
Implementation: `ipfs_accelerate_py.action_runtime.adapters.human_handoff`

This document freezes the **authority-plane human handoff adapter** for
`handoff_live_agent`. It creates durable `HandoffRequest` records and transfer
receipts whose statuses distinguish **accepted / started / succeeded / unknown /
failed**. Spoken transfer success is forbidden unless the receipt status is
`succeeded` with provider confirmation.

Validated by:

```bash
python -m pytest -q ipfs_accelerate_py/test/test_action_human_handoff_adapter.py
```

Companion doctrine: `docs/voice_action_dag/INTEGRATION_DOCTRINE.md` §5
(Handoff truthfulness). Policy boundary: `docs/voice_action_dag/POLICY_MATRIX.md` §6.

## 1. Dual-plane boundary

```text
content plane (Abby / live_agent route / slotted DAG)
  -> logical ActionProposal only (handoff_live_agent)
  -> spoken frames remain advisory
authority plane (catalog / pilot policy / human_handoff adapter)
  -> ActionDecisionKind.HANDOFF admits request creation
  -> durable HandoffRequest + ActionReceipt statuses
  -> spoken success only when receipt status == succeeded
```

Spoken Abby scripts for `live_agent` remain **content-only**. They never invent
descriptors, never open arbitrary tools, and never assert that a warm transfer
completed without a provider-confirmed `succeeded` receipt.

## 2. Catalog binding

Pilot descriptor from `catalog_211ai` / `211ai-pilot-v1`:

| logical_action | descriptor_id | Risk | Side effect | Confirm | Auth |
| --- | --- | --- | --- | --- | --- |
| `handoff_live_agent` | `voice.human.handoff_live_agent.v1` | human | network | yes / auto under policy | no |

Default registration: `default_handoff_registrations()`.

Policy matrix (VOICE-ACTION-007):

* Unconfirmed: `handoff` with reason `handoff_policy_request` when
  `handoff_auto_request=true` (default), else `confirm`.
* Confirmed: `handoff` with reason `handoff_confirmed_request`.
* `permits_execution` is **false** for `handoff` — request creation is not
  execute-class adapter smuggling.

## 3. Adapter surface

```python
from ipfs_accelerate_py.action_runtime.adapters.human_handoff import (
    HumanHandoffActionAdapter,
    HandoffInvocationContext,
    InMemoryHandoffRequestStore,
    allows_spoken_success,
    default_handoff_registrations,
    spoken_outcome_role,
)

store = InMemoryHandoffRequestStore()
adapter = HumanHandoffActionAdapter(default_handoff_registrations(), store=store)

# Policy emits ActionDecisionKind.HANDOFF (not permit_execute).
receipt = adapter.invoke(
    proposal=proposal,
    decision=decision,  # kind == HANDOFF
    context=HandoffInvocationContext(session_tenant_id="tenant-a"),
)
assert receipt.status.value == "accepted"
assert allows_spoken_success(receipt) is False

request_id = receipt.public_result["request_id"]
adapter.mark_started(request_id)
# Fake telephony may mark unknown without claiming success:
adapter.record_provider_outcome(request_id, status="unknown")
# Provider-confirmed transfer only:
adapter.record_provider_outcome(
    request_id,
    status="succeeded",
    provider_confirmation="pstn-confirm-…",  # required for succeeded
)
```

### 3.1 Admission rule (fail closed)

| Decision kind | Adapter behavior |
| --- | --- |
| `handoff` | Create durable `HandoffRequest` → receipt `accepted` |
| `deny` | Receipt `denied`; no store write |
| `confirm` | Receipt `denied` (`decision_does_not_admit_handoff`); no store write |
| `permit_execute` / `permit_read` | **Rejected** — handoff request creation is not smuggled via permit |

Before store I/O the adapter also verifies proposal/decision binding
(proposal id, descriptor id, arguments digest, expiry) and registration
presence.

### 3.2 Argument slots

| Argument | Required | Notes |
| --- | --- | --- |
| `reason` | no | Defaults to decision reason or `live_agent_requested`; ≤ `max_reason_chars` (200) |
| `priority` | no | One of `low`, `normal`, `high`, `urgent` (default `normal`) |
| `queue` | no | Safe id charset; default `live_agent` |
| `summary` | no | Privacy-safe free text; ≤ `max_summary_chars` (500); redacted in receipts |
| `preferred_channel` | no | One of `voice`, `chat`, `test`, `telephone`, `sms` |

Unexpected keys fail closed.

## 4. Durable `HandoffRequest`

Creating a request is **request admission**, not transfer success.

| Field | Meaning |
| --- | --- |
| `request_id` | Stable id (`hoff-…`) |
| `status` | `accepted` \| `started` \| `succeeded` \| `unknown` \| `failed` (plus denied/cancelled on receipts) |
| `proposal_id` / `decision_id` / `descriptor_id` | Bound authority identities |
| `queue` / `priority` / `reason` | Routing metadata |
| `summary` / `summary_digest` | Optional privacy-safe context (digest always public) |
| `provider_confirmation` | Provider-native confirmation token (required for `succeeded`) |
| `tenant_id` / `session_id` / `channel` | Session binding |

Stores:

| Store | Role |
| --- | --- |
| `InMemoryHandoffRequestStore` | Process-local durable fake (survives across invokes) |
| `FileHandoffRequestStore` | Directory-backed JSON files (survives process restart) |

`HandoffRequestStore` is injected for product backends (CRM / queue / telephony
bridge) in later tasks (VOICE-ACTION-022).

## 5. Status lifecycle

```text
[policy HANDOFF]
      |
      v
  accepted  --mark_started-->  started
      |                           |
      +------- record_provider_outcome ------+
                                             |
                    +----------+-------------+------------+
                    v          v             v            v
               succeeded    failed        unknown     cancelled
```

| Status | Meaning | Spoken transfer success? |
| --- | --- | --- |
| `accepted` | Durable request created / queued | **No** |
| `started` | Transfer / bridge attempt begun | **No** |
| `succeeded` | Provider confirmed live connection | **Yes** (only this) |
| `unknown` | Indeterminate / no provider ack | **No** |
| `failed` | Transfer or queue failure | **No** |
| `cancelled` | Caller/operator cancelled | **No** |

Rules:

1. Request creation **always** yields `accepted`, never `succeeded`.
2. `record_provider_outcome(status=succeeded)` **requires**
   `provider_confirmation` (non-empty). Missing confirmation raises and leaves
   the stored request unchanged.
3. Fake telephony adapters may mark `unknown` without claiming success
   (supports VOICE-ACTION-022 telephone path).
4. Status regressions (e.g. `succeeded` → `started`) fail closed.
5. Idempotent re-apply of the same status re-emits the current receipt.

## 6. Spoken success gate

```python
from ipfs_accelerate_py.action_runtime.adapters.human_handoff import (
    allows_spoken_success,
    spoken_outcome_role,
)

allows_spoken_success(receipt)   # True only if status == succeeded
spoken_outcome_role(receipt)     # success | denied | failed | cancelled | unknown
```

| Receipt status | `allows_spoken_success` | Outcome frame role |
| --- | --- | --- |
| `succeeded` | `true` | `success` |
| `accepted` / `started` / `unknown` | `false` | `unknown` |
| `failed` | `false` | `failed` |
| `denied` | `false` | `denied` |
| `cancelled` | `false` | `cancelled` |
| missing / `None` | `false` | `unknown` |

Receipts also carry:

* `public_result["spoken_success_allowed"]` — `"true"` \| `"false"`
* `metadata["spoken_success_allowed"]` — same
* `public_result["is_transfer_complete"]` — `"true"` only for `succeeded`

Voice / UI layers **must** consult this gate (or the receipt status directly)
before playing Abby transfer-complete wording. Content-plane `live_agent`
guidance remains advisory when the receipt is anything other than `succeeded`.

## 7. Receipt redaction (default)

`HandoffSandboxPolicy.redact_summary_in_receipts = True` by default.

| Field | In public receipt |
| --- | --- |
| Raw `summary` | **omitted** (`summary_redacted=true`, `summary_present=…`) |
| `summary_digest` | present |
| `request_id`, `queue`, `priority`, `reason` | present |
| `provider_confirmation` | present when set |
| `handoff_status` / `phase` | present |

Durable store may retain the summary for human agents; voice receipts do not
echo it by default.

## 8. Tenant binding

1. Effective tenant = `session_tenant_id` or `proposal.tenant_id`.
2. If both are set and differ → `tenant_session_mismatch` (fail closed).
3. Tenant is optional for anonymous voice handoff; when present it scopes
   `list_requests(tenant_id=…)`.

## 9. Ownership

| Owner | Owns |
| --- | --- |
| `adapters/human_handoff.py` | Adapter, stores, spoken-success gate, registrations |
| `HANDOFF.md` | This freeze document |
| `test_action_human_handoff_adapter.py` | Durability, status distinctions, spoken-success forbid |
| VOICE-ACTION-022 | Telephone turn integration / fake telephony unknown |
| VOICE-ACTION-023 | Safety overlay policy for `escalate_safety` |
| Abby content / retrieval | Spoken scripts and logical proposals only |

## 10. Non-goals

* Live carrier / PSTN transfer execution inside this module
* Claiming warm-transfer success from content-plane `live_agent` frames alone
* Treating text-only `human_handoff` metadata as `succeeded`
* Opening arbitrary tools under safety overlay (see VOICE-ACTION-023)
* Widening catalog descriptors from content-plane packs
* Returning free-text summaries on voice receipts by default
