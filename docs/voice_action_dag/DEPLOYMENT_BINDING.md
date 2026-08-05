# Voice Action DAG × Abby — Signed Deployment Binding

Program: `voice-action-dag-abby-v1`  
Goal: `VOICE-ACTION-G040`  
Task: `VOICE-ACTION-032`  
Board namespace: `voice-action-dag-abby-v1`  
Schema: `voice-action/deployment-binding@1`  
Implementation: `ipfs_accelerate_py.action_runtime.deployment_binding`

This document freezes the **authority-plane signed deployment binding** that
gates **production execute**. Live catalog digest and adapter identities must
match an operator-signed binding. A **confirm flag cannot override** a digest
or identity mismatch.

Validated by:

```bash
python -m pytest -q ipfs_accelerate_py/test/test_action_deployment_binding.py
```

Companion doctrine: `docs/voice_action_dag/INTEGRATION_DOCTRINE.md` §1.2  
Policy boundary: `docs/voice_action_dag/POLICY_MATRIX.md` (confirm/auth remain
necessary but not sufficient for production execute).

## 1. Dual-plane boundary

```text
content plane (Abby / GraphRAG / slotted DAG)
  -> logical ActionProposal only
  -> never carries binding payloads, operator keys, or adapter locators
authority plane (catalog / policy / confirmation / deployment binding)
  -> signed DeploymentBinding pins catalog_digest + adapter identities
  -> gate_production_execute admits or denies before adapter side effects
  -> mismatch => deny even when confirmed=true
```

Spoken Abby scripts remain content-only. They may request confirmation frames;
they never mint, widen, or bypass a deployment binding.

## 2. What the binding pins

A `SignedDeploymentBinding` is an operator-signed, content-addressable pin of:

| Field | Meaning |
| --- | --- |
| `binding_id` | Stable operator label for this pin |
| `catalog_id` | Reviewed catalog namespace (e.g. `211ai-pilot-v1`) |
| `catalog_digest` | SHA-256 digest of the reviewed catalog export |
| `adapter_identities` | One row per admitted descriptor |
| `environment` | Must be `production` for production execute |
| `signature` | HMAC-SHA256 over the canonical unsigned payload |
| `issuer` / `nonce` | Operator identity + anti-replay material |
| `issued_at_epoch_s` / `expires_at_epoch_s` | Optional validity window |

### 2.1 Adapter identity row

| Field | Meaning |
| --- | --- |
| `descriptor_id` | Catalog descriptor id (e.g. `voice.python.read_calendar.v1`) |
| `logical_action` | Logical action name (e.g. `read_calendar`) |
| `adapter` | Catalog adapter family (`python`, `workflow`, `human`, …) |
| `interface_identity` | Stable handle adapters publish on receipts |

Interface identities contain **no** executable paths, argv, import paths,
credentials, or network endpoints. Offline pilot defaults use:

```text
{family}:{logical_action}:{descriptor_id}
```

Examples:

| logical_action | interface_identity |
| --- | --- |
| `read_calendar` | `calendar:read_calendar:voice.python.read_calendar.v1` |
| `schedule_service_callback` | `service_interaction:schedule_service_callback:voice.workflow.schedule_service_callback.v1` |
| `handoff_live_agent` | `human_handoff:handoff_live_agent:voice.human.handoff_live_agent.v1` |

Product/wallet surfaces may pin different `interface_identity` strings; the
**signed binding** is the execute-time source of truth.

## 3. Gate semantics (fail closed)

```python
from ipfs_accelerate_py.action_runtime.deployment_binding import (
    build_signed_pilot_binding,
    gate_production_execute,
    pilot_adapter_identities,
)
from ipfs_accelerate_py.action_runtime.catalog_211ai import catalog_digest

operator_key = b"operator-reviewed-binding-key"
binding = build_signed_pilot_binding(operator_key)

verdict = gate_production_execute(
    binding,
    operator_key=operator_key,
    runtime_catalog_digest=catalog_digest(),
    runtime_adapter_identities=pilot_adapter_identities(),
    confirmed=True,  # still insufficient if digests diverge
)
assert verdict.permits_execution is True
```

### 3.1 Admission matrix

| Condition | `confirmed` | Result | Reason |
| --- | --- | --- | --- |
| Signature missing/invalid | any | **deny** | `invalid_or_missing_binding_signature` |
| Environment ≠ `production` | any | **deny** | `binding_environment_not_production` |
| Binding expired | any | **deny** | `binding_expired` |
| Runtime catalog digest ≠ binding | any (incl. `true`) | **deny** | `catalog_digest_mismatch` |
| Adapter identity set/row mismatch | any (incl. `true`) | **deny** | `adapter_identity_*` |
| Signature valid + digests match | `false` or `true` | **admit** | `binding_match` / `binding_match_confirmed` |

**Non-negotiable:** confirmation is authority-plane evidence for *policy*
admission (VOICE-ACTION-007). It is **not** a bypass for deployment binding
pins. Mismatch always denies execute.

### 3.2 Ordering relative to policy

```text
ActionProposal
  -> PilotPolicy.decide (confirm / auth / safety)     [VOICE-ACTION-007]
  -> gate_production_execute (signed binding match)   [VOICE-ACTION-032]
  -> admitted adapter.invoke
  -> ActionReceipt
```

A `permit_execute` decision without a matching signed binding must not start
side effects in production. Conversely, a valid binding never widens risk class
or skips confirm/auth required by the policy matrix.

## 4. Signing

- Algorithm: `hmac-sha256` (hex digest, 64 lowercase chars)
- Payload: canonical JSON of every public field except `signature`
  (`sort_keys=True`, compact separators, UTF-8)
- Verification: `hmac.compare_digest`
- Operator keys are deployment secrets; they never appear in content-plane
  artifacts, catalog JSON, or spoken frames

```python
from ipfs_accelerate_py.action_runtime.deployment_binding import (
    SignedDeploymentBinding,
    sign_deployment_binding,
    verify_deployment_binding_signature,
)

unsigned = SignedDeploymentBinding(
    binding_id="prod-211ai-v1",
    catalog_id="211ai-pilot-v1",
    catalog_digest=catalog_digest(),
    adapter_identities=pilot_adapter_identities(),
    environment="production",
)
signed = sign_deployment_binding(unsigned, operator_key)
assert verify_deployment_binding_signature(signed, operator_key)
```

## 5. Explicit non-goals

* Content-plane or profile-pack supplied bindings
* Binding payloads that embed executables, argv, import paths, or credentials
* Using confirm / elevated grants to override catalog or adapter identity pins
* Unsupervised production execute with credentials enabled by default
* Claiming that a valid binding replaces tenant auth or safety overlay policy

## 6. Ownership

| Owner | Owns |
| --- | --- |
| `ipfs_accelerate_py.action_runtime.deployment_binding` | Signed binding types, HMAC verify, production execute gate |
| `docs/voice_action_dag/DEPLOYMENT_BINDING.md` | This freeze document |
| `ipfs_accelerate_py/test/test_action_deployment_binding.py` | Mismatch + confirm non-bypass coverage |
| Catalog / adapters | Provide digest and interface identities consumed by the gate |

## 7. Invariants (frozen)

1. **Catalog pin:** production execute requires `runtime_catalog_digest == binding.catalog_digest`.
2. **Adapter pin:** every runtime adapter identity row must equal the signed set
   (descriptor_id, logical_action, adapter, interface_identity).
3. **Confirm non-authority for binding:** `confirmed=True` never upgrades a
   mismatch into admit.
4. **Signature required:** unsigned or wrong-key bindings deny.
5. **Fail closed:** missing fields, expired windows, and non-production
   environments deny production execute.
6. **No content-plane widening:** Abby rows and GraphRAG templates cannot
   supply or mutate binding material.
