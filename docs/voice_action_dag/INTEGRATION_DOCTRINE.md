# Voice Action DAG × Abby — Integration Doctrine

Program: `voice-action-dag-abby-v1`  
Goal: `VOICE-ACTION-G010`  
Task: `VOICE-ACTION-003`  
Board namespace: `voice-action-dag-abby-v1`  
Freeze status: `frozen`  
Schema: `voice-action/integration-doctrine@1`  
Companion verdict schema: `docs/voice_action_dag/schemas/assurance-verdict-v1.schema.json`

This document freezes the **dual-plane integration doctrine** and **package
ownership map** for connecting the Abby slotted response DAG and precomputed
audio library to governed program actions. Downstream tasks consume this
vocabulary; they must not redefine plane boundaries, ownership, or the
non-negotiable invariants below.

It is validated by:

```bash
python -m pytest -q tests/voice_action_dag/test_doctrine_invariants.py
```

## 1. Dual-plane model

This integration uses exactly two normative planes. Content and authority are
never collapsed into a single graph or a single trust class.

### 1.1 Content plane

The **content plane** owns grounded, caller-visible material and retrieval
evidence. It includes:

| Asset class | Examples |
| --- | --- |
| Slotted response DAG | `docs/phone_dialog_generation/slotted_response_dag.json` routes, frames, exemplars |
| GraphRAG / templates | `ipfs_datasets_py.voice.graphrag` matches, evidence CIDs, response plans |
| Audio library | Precomputed IndexTTS / Whisper-validated rows; confirmation and outcome frames |
| Spoken text | Grounded answers, clarification, safety wording, action prompt/outcome speech |

Content plane outputs may:

- select a **route** and grounded **response frame**;
- emit zero-or-more **logical action proposals** (catalog names only);
- cite **evidence CIDs** and library audio digests;
- attach optional **confirmation / outcome frame IDs** that still resolve only
  to content artifacts.

Content plane outputs must **never**:

- choose executables, shell commands, raw `argv`, import paths, network
  endpoints, credentials, secret references, or deployment bindings;
- increase policy authority, widen tenant scope, or bypass confirmation;
- claim that a side effect completed without an authority-plane receipt.

### 1.2 Authority plane

The **authority plane** owns admission, binding, and execution. It includes:

| Asset class | Examples |
| --- | --- |
| Action catalog | Operator-reviewed `ActionDescriptor` rows (`logical_action` → adapter family) |
| Policy engine | Fail-closed confirmation, auth, channel, and tenant gates |
| Confirmation | Explicit caller/operator confirm, or a documented safety-auto path only |
| Deployment binding | Catalog → admitted adapter (app tool, calendar, messaging, service, handoff, CLI, MCP) |
| Receipts | `ActionDecision`, `ActionReceipt`, handoff/transfer provider receipts |

Only the authority plane may:

- bind a logical action to an executable adapter identity;
- permit, deny, clarify, confirm, or hand off a proposal;
- start side effects through an admitted adapter;
- assert transfer success, write success, or external mutation completion.

### 1.3 Normative pipeline

```text
channel input
  -> STT / transcript
  -> Abby GraphRAG + slotted DAG route          [content plane]
  -> grounded spoken response (+ library audio) [content plane]
  -> logical ActionProposal (no executables)    [content plane emit]
  -> fail-closed policy / consent / confirmation [authority plane]
  -> deployment-owned catalog binding            [authority plane]
  -> admitted adapter                            [authority plane]
  -> ActionReceipt                               [authority plane]
  -> spoken outcome from Abby library or safe fallback [content plane]
```

**Authority monotonicity:** retrieval confidence, model output, and content
artifacts may reduce confidence, request clarification, or propose an
allowlisted logical action. They can **never** increase authority.

### 1.4 Dual-plane rule (frozen)

```text
content plane (Abby DAG / GraphRAG / audio)
  -> logical ActionProposal only
authority plane (catalog / policy / confirmation / adapter)
  -> ActionReceipt + spoken outcome
```

## 2. Package ownership map

| Owner | Plane focus | Owns | Must not own |
| --- | --- | --- | --- |
| `ipfs_datasets_py` | content | Abby content→action **links** (logical IDs only), domain-pack slices, GraphRAG action **candidates**, audio frame indexes, response DAG append contracts | Catalog bindings, adapter executables, policy grants, live transports |
| `ipfs_accelerate_py` | authority + orchestration | `action_runtime` (contracts, catalog, policy, executor, adapters), voice_router integration hooks, handoff adapter surfaces, receipts | Abby slotted DAG rebuild authority; free-text executable injection from retrieval |
| parent `wallet_interface` | product / UI authority surface | UI confirm/execute UX, app tool bindings, calendar/messages/service surfaces, API envelope, `attach_action_surface` | Generic content library rebuild; unsupervised live telephony/SMS |
| parent `docs/phone_dialog_generation` | content generation outputs | Slotted DAG rebuild outputs and manifests **only** via generation scripts | Runtime policy, catalogs, adapters, credentials |

### 2.1 Ownership rules

1. **Content never embeds executables.** Abby rows, GraphRAG templates, and
   slotted DAG edges may reference `logical_action_id` values from the catalog
   namespace only.
2. **Catalog is deployment-owned.** Domain packs and voice libraries may
   *reference* descriptor IDs; they cannot widen the catalog or supply
   executable paths.
3. **UI tools are not content.** Browser agent tools and service action
   services remain product surfaces; they become voice-admitted only through
   authority-plane catalog + policy + confirmation.
4. **Generation scripts stay offline and pure** for content rebuilds; they do
   not call live adapters.

## 3. Forbidden content executables

Content artifacts (slotted DAG nodes/edges, exemplars, GraphRAG templates,
action-link records, confirmation/outcome frames, and proposal argument maps
emitted from retrieval) **forbid** the following field names and value classes:

| Forbidden class | Examples |
| --- | --- |
| Shell / process | `command`, `argv`, `executable`, `shell`, `cwd` |
| Environment secrets | `env`, credentials, API keys, tokens, secret refs as free text |
| Code locators | `import_path`, Python dotted path as executable target, module loaders |
| Network locators | raw `url`, webhook endpoint, host:port as adapter target |
| Path smuggling | keys ending in `_path` used as executable or filesystem write targets |
| Deployment smuggling | adapter binary digests, MCP server URLs, supervisor mutation payloads |

Proposals carry only:

- `logical_action` (catalog name);
- string-to-string **non-locator** arguments;
- route, evidence, confidence, tenant/session/channel metadata when known.

`ActionProposal` validation in `action_runtime.contracts` already rejects
banned argument keys; content schemas and link builders must match that ban
list.

## 4. Confirmation rules

| Risk / class | Confirmation requirement |
| --- | --- |
| Read side effects (`RiskClass.READ`) | Explicit confirmation (or UI confirm) before execute; no silent run from retrieval alone |
| Write / external mutation | Confirmation **and** authenticated tenant session (or equivalent step-up) |
| Admin | Confirmation + elevated grant; default deny in autonomous workers |
| Human handoff | Handoff policy: may auto-admit **request creation** under policy, never auto-claim transfer completion |
| Safety overlay (`escalate_safety`) | Policy-driven escalate path may force handoff/emergency overlay **without** tool smuggling; still cannot invent executables |

### 4.1 Confirmation invariants

1. **Retrieval alone never executes.** GraphRAG / route classification may emit
   proposals; execute requires policy decision + confirmation (except the
   documented safety-auto escalate/handoff-request path).
2. **Deny without confirm.** Offline and product paths must prove that a
   proposal is denied when confirmation is absent.
3. **Descriptor flag is normative.** Catalog descriptors set
   `requires_confirmation`; policy must honor it fail-closed.
4. **Spoken confirmation is content, not authority.** Abby “confirm this
   action?” frames are content-plane utterances; the authority plane still
   records the confirm decision.

## 5. Handoff truthfulness rules

These rules apply to `live_agent`, `handoff_live_agent`, safety escalate, and
any human/telephony transfer path.

1. **Never claim unverified transfer success.** Spoken text, UI copy, and
   receipts must not assert that a warm transfer or live-agent connection
   completed unless a **provider confirmation receipt** exists.
2. **Metadata-only escalation is not success.** Text-only `human_handoff`
   provider metadata or advisory flags are **request / escalate** states, not
   completed transfers.
3. **Receipted request vs completed transfer.** Creating a handoff **request**
   (`ActionDecisionKind.HANDOFF` / request receipt) is distinct from
   `ActionStatus.SUCCEEDED` on a verified telephony adapter.
4. **Outcome speech must match receipt.** Success outcome frames may play only
   after a verified receipt; otherwise use deny, cancelled, failure, or
   unknown frames.
5. **No silent success from content.** The `live_agent` route’s spoken guidance
   remains content; it does not imply authority-plane transfer completion.

## 6. Route classification (content → proposal eligibility)

Inherited from the baseline inventory; doctrine freezes the meanings:

| Classification | Meaning |
| --- | --- |
| `content-only` | Spoken response only; no side-effect proposal |
| `proposal-eligible` | May emit a catalog-bound logical action after policy/confirmation |
| `safety-overlay` | Safety/crisis wording overlays emergency/handoff policy; content still never embeds executables |

Every tool-adjacent route maps to a catalog logical action **or** an explicit
`no_action` classification. Missing maps fail closed as `no_action` / deny.

## 7. Assurance verdict

Conformance checks emit a machine-readable **assurance verdict** matching
`docs/voice_action_dag/schemas/assurance-verdict-v1.schema.json`.

A passing verdict must bind:

- program and doctrine identity;
- content-plane vs authority-plane separation;
- package ownership map digest or explicit owner list;
- forbidden content-executable ban list;
- confirmation rule coverage;
- handoff truthfulness rule coverage;
- overall `verdict` in `{pass, fail, unknown}` with fail-closed semantics for
  partial or stale evidence (`unknown` and `fail` never grant execute).

## 8. Non-negotiable invariants (summary)

| ID | Invariant |
| --- | --- |
| INV-PLANE-001 | Content plane and authority plane are distinct; content cannot execute |
| INV-OWN-001 | Package ownership is `ipfs_datasets_py`, `ipfs_accelerate_py`, `wallet_interface`, `docs/phone_dialog_generation` as mapped above |
| INV-CONTENT-001 | Content forbids command/argv/executable/shell/cwd/env/import_path/url and executable `_path` keys |
| INV-PROP-001 | Retrieval may propose catalog `logical_action` values only |
| INV-CONF-001 | Execute requires policy + confirmation (or documented safety-auto escalate/handoff-request only) |
| INV-AUTH-001 | Retrieval/model confidence never increases authority |
| INV-HAND-001 | Handoff never claims completed transfer without provider confirmation |
| INV-RCPT-001 | Side-effect success claims require an authority-plane `ActionReceipt` |

## 9. Explicit non-goals (doctrine scope)

- Replacing Abby TTS generation infrastructure.
- Full multi-tenant profile-pack platform (see reusable voice-care plan).
- Unsupervised production execute with credentials enabled by default.
- Claiming exactly-once semantics for external telephony or SMS providers.

## 10. Related artifacts

| Artifact | Path |
| --- | --- |
| Integration plan | `docs/planning/VOICE_ACTION_DAG_ABBY_INTEGRATION_PLAN.md` |
| Baseline inventory | `docs/voice_action_dag/BASELINE_INVENTORY.md` |
| Assurance verdict schema | `docs/voice_action_dag/schemas/assurance-verdict-v1.schema.json` |
| Doctrine invariant tests | `tests/voice_action_dag/test_doctrine_invariants.py` |
| Runtime policy | `docs/voice_action_dag/runtime-policy.json` |
