# VOICE-CARE-AUTO-015 Objective Goal Gap

Date: 2026-08-03
Fingerprint: 3b160e7741c6ce0e1c10fc3d862a07e759c013d9
Goal id: VOICE-CARE-G019
Goal title: Define reusable intake forms and case lifecycle
Objective heap: docs/planning/VOICE_CUSTOMER_CARE_OBJECTIVE_HEAP.md
Priority: P1
Track: intake
Status: todo
Schedulable: true
Review only: false
Parent goals: VOICE-CARE-G001
Graph depth: 1
Objective heap index: 15
Bundle: voice-care/intake
Parallel lane: voice-care-portal
Bundle strategy: explicit
Goal packet: none
Goal packet role: none
Goal packet goals: none
Goal packet task count: 0
Goal packet work item count: 0
Evidence methods: embedding, exact
Embedding query: reusable client intake dynamic forms voice web consent disclosure case lifecycle follow up disposition
AST query: IntakeForm, IntakeField, IntakeSession, CaseLifecycle
Conflict policy: collect the minimum required data progressively; application packs define labels but cannot weaken data classification or consent
Predicted files: ipfs_datasets_py/ipfs_datasets_py/conversation/forms.py, ipfs_accelerate_py/ipfs_accelerate_py/conversation_runtime/intake.py, tests/customer_care/test_intake_forms.py
AST symbols: IntakeForm, IntakeField, IntakeSession, CaseLifecycle
Interfaces: domain pack forms, SessionState, CaseStore, wallet/HMIS consent
Submodules: ipfs_datasets_py, ipfs_accelerate_py
Generated artifacts: none
Allow concurrent with: none
Semantic identity: objective-evidence-obligation/v1/43325848d0233b17d9d0220fd413a24b357b1540042d5c86245cacf92cbdde5c
Acceptance subset: web form projection, synthetic accessibility and privacy tests
Preconditions: objective goal VOICE-CARE-G019 is schedulable
Effects: satisfy evidence requirement: web form projection, satisfy evidence requirement: synthetic accessibility and privacy tests
Evidence subset: web form projection, synthetic accessibility and privacy tests
Dependencies: VOICE-CARE-G002, VOICE-CARE-G010
Resource class: cpu-medium
Token class: medium
Estimated tokens: 0
Resources: cpu-medium
Merge fate: objective/VOICE-CARE-G019
Rejection reasons: none (accepted)

## Goal

Render and validate domain-pack forms for intake, disclosures, consent, eligibility hints, contact preference, case creation, follow-up, and disposition across voice and web channels.

## Missing Evidence

- web form projection
- synthetic accessibility and privacy tests

## Present Evidence

- form schema and validator: docs/specs/WORLD_AID_GATE_FIRST_EXECUTION_PLAN_V2.md (embedding:0.31), docs/specs/WORLD_ID_IDKIT_UI_WORKFLOW_MATRIX.md (embedding:0.31), ipfs_accelerate_py/CONTRIBUTING.md (embedding:0.32)
- voice prompt projection: ipfs_accelerate_py/test/ipfs_accelerate_js/src/api_backends/openai/types.ts (embedding:0.64), ipfs_accelerate_py/test/ipfs_accelerate_js/src/api_backends/openai_mini/types.ts (embedding:0.65)
- progressive disclosure: docs/specs/ABBY_PRODUCT_IA_AND_WIREFRAMES.md (exact)
- case lifecycle: ipfs_datasets_py/ipfs_datasets_py/processors/multimedia/omni_converter_mk2/TESTING.md (embedding:0.52)

## Suggested Handling

Create one canonical form contract with channel-specific projections.
