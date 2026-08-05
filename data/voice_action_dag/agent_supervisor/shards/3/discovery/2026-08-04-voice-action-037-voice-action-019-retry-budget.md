# VOICE-ACTION-037 — Retry-budget repair for VOICE-ACTION-019

- **Repair task:** `VOICE-ACTION-037`
- **Source task:** `VOICE-ACTION-019` (validation retry budget exhausted)
- **Failure kind:** `validation`
- **Date:** 2026-08-04 / repair attempt 2026-08-05
- **Validation target:** `ipfs_accelerate_py/test/test_action_service_interaction_adapter.py`

## 1. Failure evidence (pre-repair)

VOICE-ACTION-019 repeatedly failed its declared gate:

```bash
PYTHONPATH=ipfs_accelerate_py:ipfs_datasets_py:ipfs_kit_py \
  python -m pytest -q ipfs_accelerate_py/test/test_action_service_interaction_adapter.py
```

Root cause classification: **task-owned incomplete implementation** (not inherited
validation debt, not assertion over-strength).

| Expected output | Pre-repair state |
| --- | --- |
| `ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/adapters/service_interaction.py` | **Missing** |
| `ipfs_accelerate_py/test/test_action_service_interaction_adapter.py` | **Missing** |
| `docs/voice_action_dag/SERVICE_INTERACTION_BINDINGS.md` | **Missing** |

Pytest collection failed because the declared test module did not exist. No
production policy or catalog assertions needed weakening.

## 2. Acceptance criteria restored (VOICE-ACTION-019 / G100)

| Criterion | Repair behavior |
| --- | --- |
| `schedule_service_callback` idempotent on proposal digest | `proposal_idempotency_digest()` + store de-dupe; replay sets `idempotent_replay=true` without a second row |
| `service_id` required from grounded evidence | `require_grounded_service_id()`; empty evidence / free-text-only fails closed |
| Unconfirmed path no-ops | Non-permitting decisions → `DENIED`; missing confirm/auth → `FAILED` with **zero** store writes |

## 3. Repair actions

1. Implemented `ServiceInteractionActionAdapter` with:
   - `open_service_detail` (confirm, no auth)
   - `schedule_service_callback` (confirm + auth, digest-idempotent)
2. Added unit suite covering grounding, idempotency, no-ops, tenant isolation,
   redaction, pilot-policy e2e.
3. Froze bindings in `docs/voice_action_dag/SERVICE_INTERACTION_BINDINGS.md`.
4. Did **not** weaken pilot policy, catalog descriptors, or correct assertions.

## 4. Validation command (authoritative)

```bash
PYTHONPATH=ipfs_accelerate_py:ipfs_datasets_py:ipfs_kit_py \
  python -m pytest -q ipfs_accelerate_py/test/test_action_service_interaction_adapter.py
```

## 5. Completion

When the gate above is green, mark VOICE-ACTION-037 completed so the supervisor
can release VOICE-ACTION-019 from strategy `blocked_tasks`.

Changed files (declared outputs only):

- `ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/adapters/service_interaction.py`
- `ipfs_accelerate_py/test/test_action_service_interaction_adapter.py`
- `docs/voice_action_dag/SERVICE_INTERACTION_BINDINGS.md`
- `data/voice_action_dag/agent_supervisor/shards/3/discovery/2026-08-04-voice-action-037-voice-action-019-retry-budget.md`
