# Voice Action DAG × Abby — Baseline Inventory

Program: `voice-action-dag-abby-v1`  
Goal: `VOICE-ACTION-G010`  
Task: `VOICE-ACTION-002`  
Board namespace: `voice-action-dag-abby-v1`  
Generated: `2026-08-04T06:16:28Z`  
Repository HEAD: `f2febada0daeac6414bc6f5aa4468272556920c0`

This document freezes the starting inventory for dual-plane integration:
Abby slotted DAG + audio (content plane) versus governed program actions
(authority plane). It is validated by
`python scripts/voice_action_dag/audit_baseline.py --check`.

## Artifacts

| Artifact | Path |
| --- | --- |
| Component inventory | `data/voice_action_dag/baseline/component-inventory.json` |
| Route gap matrix | `data/voice_action_dag/baseline/route-gap-matrix.json` |
| Audit script | `scripts/voice_action_dag/audit_baseline.py` |
| Slotted response DAG | `docs/phone_dialog_generation/slotted_response_dag.json` |

## Route census (matches slotted DAG summary)

Total route edges: **13660** across **12** routes.

| Route | Edges | Classification | Target logical action | Voice bridge |
| --- | ---: | --- | --- | --- |
| `app_surface_navigation` | 113 | `proposal-eligible` | `open_app_surface` | yes |
| `calendar_event_support` | 290 | `proposal-eligible` | `open_calendar_support` | yes |
| `clarifying_prompt` | 65 | `content-only` | `—` | no |
| `grounded_211_answer` | 2145 | `proposal-eligible` | `open_service_detail` | no |
| `live_agent` | 6992 | `proposal-eligible` | `handoff_live_agent` | no |
| `provider_contact_support` | 226 | `proposal-eligible` | `provide_provider_contact` | yes |
| `repeat_or_restate` | 2220 | `content-only` | `—` | no |
| `safety_guardrail_support` | 563 | `safety-overlay` | `escalate_safety` | no |
| `service_interaction_support` | 82 | `proposal-eligible` | `review_service_interaction` | yes |
| `speech_unclear_clarification` | 632 | `content-only` | `—` | no |
| `template_guided_fallback` | 86 | `content-only` | `—` | no |
| `wallet_document_support` | 246 | `proposal-eligible` | `open_wallet_documents` | yes |

### Classification rules

- **content-only** — spoken response only; no side-effect proposal.
- **proposal-eligible** — may emit a catalog-bound logical action after policy/confirmation.
- **safety-overlay** — safety/crisis wording that overlays emergency/handoff policy;
  content still never embeds executables.

## Component inventory (repo revisions + AST symbols)

Each component binds one or more source paths with `sha256`, optional
`git_revision`, and extracted AST/export symbols. Required symbols are
asserted by the audit.

### `action_runtime`

- **Plane:** authority
- **Owner:** `ipfs_accelerate_py`
- **Role:** Fail-closed proposal → policy → catalog → adapter execution; voice_bridge maps 5 routes.
- **Modules:**
  - `ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/__init__.py` — sha256 `aa51990355f23997…` (39 lines, 0 symbols, rev `uncommitted/`)
  - `ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/contracts.py` — sha256 `8251e0be73495ac3…` (202 lines, 15 symbols, rev `uncommitted/`)
  - `ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/catalog.py` — sha256 `1a51fa7c93a41630…` (100 lines, 11 symbols, rev `uncommitted/`)
  - `ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/policy.py` — sha256 `3b6c51c9066d2144…` (172 lines, 6 symbols, rev `uncommitted/`)
  - `ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/executor.py` — sha256 `1d63f0e6b6a601ed…` (65 lines, 3 symbols, rev `uncommitted/`)
  - `ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/voice_bridge.py` — sha256 `6e76a87425dc2648…` (122 lines, 5 symbols, rev `uncommitted/`)
  - `ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/adapters/cli.py` — sha256 `e6ae5c9485abde09…` (364 lines, 14 symbols, rev `uncommitted/`)
  - `wallet_interface/helpers/_voice_action_surface.py` — sha256 `d2d83ed2473c2e8e…` (298 lines, 12 symbols, rev `36262022db92`)
- **Required AST symbols:**
  - `ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/contracts.py`: `ActionProposal`, `ActionDecision`, `ActionReceipt`, `RiskClass`, `SideEffectClass`
  - `ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/catalog.py`: `ActionCatalog`, `ActionDescriptor`
  - `ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/voice_bridge.py`: `VoiceActionBridge`, `propose_from_voice_route`, `DEFAULT_ROUTE_TO_LOGICAL_ACTION`
  - `ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/policy.py`: `FailClosedPolicy`, `ActionPolicyEngine`
  - `ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/executor.py`: `ActionExecutor`
  - `wallet_interface/helpers/_voice_action_surface.py`: `attach_action_surface`, `build_default_action_stack`, `extract_voice_route`, `is_voice_action_execute_enabled`

### `graphrag`

- **Plane:** content
- **Owner:** `ipfs_datasets_py`
- **Role:** Deterministic grounded retrieval over Abby templates/slotted DAG; content plane only.
- **Modules:**
  - `ipfs_datasets_py/ipfs_datasets_py/voice/graphrag.py` — sha256 `6a47fb993aaa75b4…` (1727 lines, 75 symbols, rev `uncommitted/`)
  - `ipfs_datasets_py/ipfs_datasets_py/voice/response_dag.py` — sha256 `959d9d167eb30860…` (671 lines, 28 symbols, rev `uncommitted/`)
  - `docs/phone_dialog_generation/slotted_response_dag.json` — sha256 `89ddb937155efa86…` (1171787 lines, 0 symbols, rev `173e2c2b2d2c`)
- **Required AST symbols:**
  - `ipfs_datasets_py/ipfs_datasets_py/voice/graphrag.py`: `GraphRAGVoiceTemplateProvider`, `SlottedResponseIndex`, `EvidenceRecord`, `TemplateMatch`, `TemplateGraphSnapshot`
  - `ipfs_datasets_py/ipfs_datasets_py/voice/response_dag.py`: `ResponseDAGAppendCandidate`, `append_response_dag_candidate`

### `handoff`

- **Plane:** authority+channel
- **Owner:** `ipfs_accelerate_py + wallet_interface`
- **Role:** Human handoff / live_agent is metadata-only escalation today; ActionDecisionKind.HANDOFF exists but no verified transfer adapter.
- **Modules:**
  - `ipfs_accelerate_py/ipfs_accelerate_py/voice_router.py` — sha256 `15aab6b0d9e9d61f…` (7283 lines, 202 symbols, rev `uncommitted/`)
  - `ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/contracts.py` — sha256 `8251e0be73495ac3…` (202 lines, 15 symbols, rev `uncommitted/`)
  - `wallet_interface/helpers/_voice_action_surface.py` — sha256 `d2d83ed2473c2e8e…` (298 lines, 12 symbols, rev `36262022db92`)
- **Required AST symbols:**
  - `ipfs_accelerate_py/ipfs_accelerate_py/voice_router.py`: `process_voice_turn`, `TelephoneTurnState`
  - `ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/contracts.py`: `ActionDecisionKind`
  - `wallet_interface/helpers/_voice_action_surface.py`: `attach_action_surface`
- Note: voice_router telephone path degrades to text-only human_handoff provider metadata
- Note: live_agent route is not in DEFAULT_ROUTE_TO_LOGICAL_ACTION
- Note: No telephony transfer receipt; never claim unverified success

### `service_actions`

- **Plane:** product/UI
- **Owner:** `wallet_interface`
- **Role:** Browser service handoffs (call/text/email/map/share/calendar) with observed-status only; not voice-admitted.
- **Modules:**
  - `wallet_interface/ui/src/features/service-navigation/lib/serviceActionService.ts` — sha256 `ccd1b03517c71314…` (596 lines, 29 symbols, rev `d7346de0ce13`)
  - `wallet_interface/ui/src/features/service-navigation/lib/serviceInteractionService.ts` — sha256 `cd9a6f2740dde7d3…` (430 lines, 15 symbols, rev `316def0c9c48`)
- **Required AST symbols:**
  - `wallet_interface/ui/src/features/service-navigation/lib/serviceActionService.ts`: `buildCallAction`, `buildCalendarAction`, `buildShareAction`, `invokeLinkAction`, `ServiceActionDescriptor`
  - `wallet_interface/ui/src/features/service-navigation/lib/serviceInteractionService.ts`: `buildServiceInteractionIntent`, `emitWalletServiceInteractionIntent`, `ServiceInteractionIntent`

### `ui_tools`

- **Plane:** product/UI
- **Owner:** `wallet_interface`
- **Role:** Browser agent tools (navigate, calendar, messages, service plans) exist but are not bound to voice DAG routes.
- **Modules:**
  - `wallet_interface/ui/src/features/agent/lib/toolExecutor.ts` — sha256 `17d0d39736ef3edf…` (586 lines, 14 symbols, rev `b3377b46e1ed`)
  - `wallet_interface/ui/src/features/agent/lib/surfaceRegistry.ts` — sha256 `25ed963c78cdcef5…` (943 lines, 17 symbols, rev `b3377b46e1ed`)
  - `wallet_interface/ui/src/features/agent/lib/tools/navigationTools.ts` — sha256 `d004de7b57fd0b18…` (502 lines, 12 symbols, rev `b3377b46e1ed`)
  - `wallet_interface/ui/src/features/agent/lib/tools/servicePlanTools.ts` — sha256 `96d605f3d78b7bf7…` (516 lines, 5 symbols, rev `b3377b46e1ed`)
  - `wallet_interface/ui/src/features/agent/lib/tools/contactTools.ts` — sha256 `0f0da56b7a5245fe…` (374 lines, 6 symbols, rev `b3377b46e1ed`)
  - `wallet_interface/ui/src/features/calendar/lib/ics.ts` — sha256 `4cf54b99fa64f2d2…` (206 lines, 8 symbols, rev `d7346de0ce13`)
  - `wallet_interface/ui/src/features/agent/lib/voiceTurnResult.ts` — sha256 `4af394f48a86d7e3…` (403 lines, 24 symbols, rev `65d87e2ec27e`)
- **Required AST symbols:**
  - `wallet_interface/ui/src/features/agent/lib/toolExecutor.ts`: `createAgentToolExecutor`, `AgentToolExecutor`
  - `wallet_interface/ui/src/features/agent/lib/surfaceRegistry.ts`: `SURFACE_CONTEXT_SCOPES`
  - `wallet_interface/ui/src/features/agent/lib/tools/navigationTools.ts`: `NavigationSurface`
  - `wallet_interface/ui/src/features/calendar/lib/ics.ts`: `buildIcsCalendar`
  - `wallet_interface/ui/src/features/agent/lib/voiceTurnResult.ts`: `VoiceActionSurface`, `parseVoiceTurnResult`

### `voice_router`

- **Plane:** content+orchestration
- **Owner:** `ipfs_accelerate_py`
- **Role:** STT → GraphRAG/template retrieval → TTS/precomputed audio receipt; wallet adapter adoption.
- **Modules:**
  - `ipfs_accelerate_py/ipfs_accelerate_py/voice_router.py` — sha256 `15aab6b0d9e9d61f…` (7283 lines, 202 symbols, rev `uncommitted/`)
  - `wallet_interface/helpers/_voice_router_adapter.py` — sha256 `e8cc47c2e1c7a393…` (633 lines, 40 symbols, rev `36262022db92`)
- **Required AST symbols:**
  - `ipfs_accelerate_py/ipfs_accelerate_py/voice_router.py`: `process_voice_turn`, `VoiceTurnRequest`, `VoiceTurnResult`, `VoiceResponsePlan`, `speech_to_text`, `text_to_speech`
  - `wallet_interface/helpers/_voice_router_adapter.py`: `WalletVoiceRouterAdapter`, `process_wallet_voice_turn`, `is_unified_voice_router_enabled`, `serialize_voice_turn_result`

## Gap matrix highlights

Program-level gaps (see `route-gap-matrix.json` for full detail):

| ID | Title | Status |
| --- | --- | --- |
| G1 | Dual-plane schema for Abby library | `open` |
| G2 | Catalog of program actions | `partial` |
| G3 | Retrieval that proposes actions without authority | `open` |
| G4 | Real adapters (not /usr/bin/true) | `open` |
| G5 | Abby audio continuity for actions | `open` |
| G6 | End-to-end proofs with the real dataset | `open` |
| G7 | Parallel supervisor program | `partial` |

Routes with outstanding gaps: **8** / 12.

### Handoff truthfulness

- `live_agent` is proposal-eligible for `handoff_live_agent` but **not**
  mapped in `DEFAULT_ROUTE_TO_LOGICAL_ACTION` today.
- Telephone path in `voice_router` can degrade to text-only
  `human_handoff` metadata; it must never claim an unverified transfer.
- `ActionDecisionKind.HANDOFF` exists in contracts; no verified telephony
  adapter is admitted yet.

### Dual-plane rule (preview; doctrine freezes in VOICE-ACTION-003)

```text
content plane (Abby DAG / GraphRAG / audio)
  -> logical ActionProposal only
authority plane (catalog / policy / confirmation / adapter)
  -> ActionReceipt + spoken outcome
```

Content artifacts must never embed executables, URLs, import paths,
credentials, or raw argv.

## Validation

```bash
python scripts/voice_action_dag/audit_baseline.py --check
```

The audit fails closed when:

1. route census diverges from `summary.routeCounts` in the slotted DAG;
2. any route lacks a classification in
   `{content-only, proposal-eligible, safety-overlay}`;
3. a required component path or AST symbol is missing;
4. inventory digests no longer match the bound source files.
