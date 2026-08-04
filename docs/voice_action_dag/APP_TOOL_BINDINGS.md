# Voice Action DAG × Abby — App Tool Bindings

Program: `voice-action-dag-abby-v1`  
Goal: `VOICE-ACTION-G070`  
Task: `VOICE-ACTION-013`  
Board namespace: `voice-action-dag-abby-v1`  
Adapter: `ipfs_accelerate_py.action_runtime.adapters.app_tool`  
Schema: `voice-action/app-tool-bindings@1`

This document freezes the **authority-plane app tool adapter** bindings for
navigation and wallet document open. Content-plane routes may only *propose*
the logical actions below; they never choose surfaces outside the reviewed
allowlist, never supply filesystem paths, and never spawn a shell.

Validated by:

```bash
python -m pytest -q ipfs_accelerate_py/test/test_action_app_tool_adapter.py
```

## 1. Scope

| Item | Binding |
| --- | --- |
| Adapter family | `app_tool` (catalog adapter field: `python`) |
| Logical actions | `open_app_surface`, `open_wallet_documents` |
| Pilot descriptors | `voice.python.open_app_surface.v1`, `voice.python.open_wallet_documents.v1` |
| Surface API | Injected `AppSurfaceAPI` (UI/server-mediated); tests use `FakeAppSurfaceAPI` |
| Shell / process | **Forbidden.** No `subprocess`, `shell=True`, or ambient executable paths |

Companion doctrine: `docs/voice_action_dag/INTEGRATION_DOCTRINE.md` §1–3.  
Pilot policy: `docs/voice_action_dag/POLICY_MATRIX.md` (READ → confirm → `permit_read`).

## 2. Dual-plane contract

```text
content plane  -> ActionProposal(logical_action, arguments.surface?)
authority plane
  -> FailClosed / pilot policy decision
  -> AppToolAdapter.invoke (only if permits_execution)
  -> AppSurfaceAPI.open_surface (allowlisted surface only)
  -> ActionReceipt (paths redacted)
```

**Authority monotonicity:** retrieval confidence and spoken frames cannot open a
surface. Only a permitting `ActionDecision` bound to the exact proposal
(`proposal_id`, `descriptor_id`, `arguments_digest`) may invoke the adapter.

## 3. Logical action bindings

| logical_action | Default surface | Allowed surfaces | Proposal argument |
| --- | --- | --- | --- |
| `open_app_surface` | `home` | Reviewed product `RouteId` set (see §4) | optional `surface` |
| `open_wallet_documents` | `uploads` | `{uploads}` only | optional `surface` (must be `uploads` if set) |

### 3.1 Argument rules

- Arguments are string-to-string and **non-locator** (see contracts ban list:
  no `command`, `argv`, `executable`, `cwd`, `env`, `shell`, `import_path`,
  `url`, or keys ending in `_path`).
- The only admitted slot for this adapter is `surface` (route id style:
  `^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$`).
- Path-like values (`..`, `/`, `\`) are rejected at resolve time.
- Unexpected argument keys fail closed.

### 3.2 Decision requirements

| Decision | Adapter behavior |
| --- | --- |
| `deny` / `confirm` / `clarify` / `handoff` | Receipt `denied`; surface API **not** called |
| `permit_read` / `permit_execute` | Resolve surface; call surface API; emit receipt |

Mismatch between decision and proposal (id, descriptor, arguments digest, or
expiry) yields `failed` without opening a surface.

## 4. Surface allowlist

Aligned with wallet `surfaceRegistry` / navigation tools `RouteId` values:

`home`, `register`, `check-in`, `calendar`, `messages`, `contacts`,
`sharing-rules`, `uploads`, `settings`, `social-services`, `interactions`,
`shelter`, `provider-clients`, `provider-cases`, `provider-messages`,
`provider-analytics`, `provider-proofs`, `provider-operations`,
`recipient-access`, `benefits-protection`, `analytics`, `proof-center`,
`exports`, `security`, `audit`.

| Rule | Effect |
| --- | --- |
| Surface not in registration allowlist | Receipt `denied`, error `unknown_surface:<id>` |
| Surface unknown to injected API | Receipt `denied` (`unknown_surface`) |
| Wallet docs targeting non-`uploads` | Receipt `denied` |

Product wiring of real navigate/upload tools is **VOICE-ACTION-014**
(`wallet_interface` binding layer). This adapter only defines the admitted
Python interface and offline fake.

## 5. Receipt redaction

Receipts must never expose private filesystem locations:

1. Keys that are path-shaped (`path`, `file_path`, `local_path`, `cwd`, any
   `*_path`, etc.) are **dropped** from `public_result`.
2. Remaining string values pass through `redact_private_paths`, which replaces
   absolute/home/Windows path substrings with `[redacted-path]`.
3. `error` strings are redacted the same way.
4. Success receipts may include digests of the **already redacted** public
   result (`stdout_digest`) for auditability; raw surface payloads and local
   paths never leave the adapter.

## 6. Implementation map

| Symbol | Role |
| --- | --- |
| `AppToolRegistration` | Reviewed descriptor → allowlist + default surface |
| `default_app_tool_registrations()` | Pilot descriptor defaults |
| `AppSurfaceAPI` / `FakeAppSurfaceAPI` | Injected opener / offline fake |
| `AppToolAdapter.invoke` | Fail-closed invoke after permit |
| `resolve_surface` | Argument + allowlist resolution |
| `redact_private_paths` / `redact_public_fields` | Receipt hygiene |

## 7. Non-goals

- Spawning CLI probes (`/usr/bin/true`) for app navigation (CLI remains ops-only).
- Widening allowlists from content packs or GraphRAG templates.
- Claiming document content was read or exported; this adapter only **opens**
  the admitted surface after permit.
- Mutating wallet records, uploads, or sharing rules (write-class tools stay on
  other adapters with auth+confirm).

## 8. Downstream binding (preview)

VOICE-ACTION-014 attaches a real `AppSurfaceAPI` implementation that calls
wallet navigation / document UI tools after server-side permit. That binding
must:

- reuse the same allowlist vocabulary;
- keep path redaction at the receipt boundary;
- never accept surface ids from untrusted free text outside the allowlist.
