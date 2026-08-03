# VOICE-CARE-AUTO-023 Objective Goal Gap

Date: 2026-08-03
Fingerprint: b57ab3d408eaa67e53e3a9de4b5f97dd395db236
Goal id: VOICE-CARE-G021
Goal title: Build the reusable portal shell and operator console
Objective heap: docs/planning/VOICE_CUSTOMER_CARE_OBJECTIVE_HEAP.md
Priority: P1
Track: portal
Status: todo
Schedulable: true
Review only: false
Parent goals: VOICE-CARE-G001
Graph depth: 1
Objective heap index: 23
Bundle: voice-care/portal
Parallel lane: voice-care-portal
Bundle strategy: explicit
Goal packet: none
Goal packet role: none
Goal packet goals: none
Goal packet task count: 0
Goal packet work item count: 0
Evidence methods: embedding
Embedding query: reusable customer portal operator console intake grounded answer action confirmation workflow handoff disposition
AST query: CustomerCareScreen, CustomerCareOperatorScreen, ActionTimeline, HandoffQueuePanel
Conflict policy: UI receives public presentation data and authorized private projections only; it never executes tools directly or stores secrets/private case plaintext in public caches
Predicted files: wallet_interface/ui/src/customer_care, wallet_interface/ui/src/app/CustomerCareScreen.tsx, wallet_interface/ui/src/app/CustomerCareOperatorScreen.tsx, wallet_interface/ui/tests/customer-care.spec.ts
AST symbols: CustomerCareScreen, CustomerCareOperatorScreen, ActionTimeline, HandoffQueuePanel
Interfaces: customer-care gateway, wallet grants, domain-pack presentation
Submodules: ipfs_accelerate_py
Generated artifacts: none
Allow concurrent with: none
Semantic identity: objective-evidence-obligation/v1/def9cb2f6ffa3225e32c18ee2f39c36f84d47d3a7a45e63a2d26aecefd8ef316
Acceptance subset: domain-pack presentation adapter, accessibility/mobile/offline tests
Preconditions: objective goal VOICE-CARE-G021 is schedulable
Effects: satisfy evidence requirement: domain-pack presentation adapter, satisfy evidence requirement: accessibility/mobile/offline tests
Evidence subset: domain-pack presentation adapter, accessibility/mobile/offline tests
Dependencies: VOICE-CARE-G019, VOICE-CARE-G020
Resource class: cpu-medium
Token class: medium
Estimated tokens: 0
Resources: cpu-medium
Merge fate: objective/VOICE-CARE-G021
Rejection reasons: none (accepted)

## Goal

Build a configuration-driven customer portal and human-agent console for intake, grounded answers, action confirmation/status, plans, follow-up, handoff queue, redacted context, and disposition.

## Missing Evidence

- domain-pack presentation adapter
- accessibility/mobile/offline tests

## Present Evidence

- reusable route/component package: ipfs_accelerate_py/test/test_hf_space_inference.py (embedding:0.40), ipfs_datasets_py/benchmarks/logic_pipeline/__init__.py (embedding:0.32), ipfs_datasets_py/ipfs_datasets_py/mcp_server/docs/README.md (embedding:0.34)
- action timeline: ipfs_datasets_py/.github/workflows/COMPREHENSIVE_IMPROVEMENT_PLAN_2026.md (embedding:0.31), ipfs_datasets_py/.github/workflows/COMPREHENSIVE_IMPROVEMENT_PLAN_2026_02_16.md (embedding:0.37), ipfs_datasets_py/.github/workflows/COMPREHENSIVE_IMPROVEMENT_PLAN_V4_2026_02_16.md (embedding:0.33)
- operator queue: ipfs_datasets_py/docs/LEGAL_IR_HAMMER_LEANSTRAL_AGENT_TODOS.md (embedding:0.38)
- redaction and grant enforcement: docs/specs/211_SERVICE_NAVIGATION_PORTAL_THREAT_MODEL.md (embedding:0.35), docs/specs/PROVEKIT_ZKP_SECURITY_NOTES.md (embedding:0.33), docs/specs/WORLD_AID_GATE_FIRST_LAUNCHER.md (embedding:0.38)

## Suggested Handling

Factor a reusable shell from the existing 211 portal and add explicit action/handoff lifecycle UI.
