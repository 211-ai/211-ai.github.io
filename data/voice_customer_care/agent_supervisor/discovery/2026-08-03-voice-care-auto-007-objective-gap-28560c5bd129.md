# VOICE-CARE-AUTO-007 Objective Goal Gap

Date: 2026-08-03
Fingerprint: 28560c5bd129bbf03e5c244227425143672a77b2
Goal id: VOICE-CARE-G008
Goal title: Enforce policy capability consent and confirmation before execution
Objective heap: docs/planning/VOICE_CUSTOMER_CARE_OBJECTIVE_HEAP.md
Priority: P0
Track: security
Status: todo
Schedulable: true
Review only: false
Parent goals: VOICE-CARE-G001
Graph depth: 1
Objective heap index: 7
Bundle: voice-care/action-policy
Parallel lane: voice-care-security
Bundle strategy: explicit
Goal packet: none
Goal packet role: none
Goal packet goals: none
Goal packet task count: 0
Goal packet work item count: 0
Evidence methods: ast, embedding, exact
Embedding query: action policy capability consent confirmation risk side effect tenant channel temporal decision
AST query: ActionPolicy, ActionRisk, SideEffectClass, ConsentReceipt, ConfirmationReceipt, ActionIntentIRAdapter, evaluate_action
Conflict policy: reuse and preserve the existing Intent IR pre-dispatch envelope; domain and request policy can only narrow deployment authority; retrieval confidence never substitutes for consent or capability
Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/policy.py, ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/intent_ir.py, ipfs_accelerate_py/test/test_action_policy.py, docs/specs/VOICE_CUSTOMER_CARE_ACTION_POLICY.md
AST symbols: ActionPolicy, ActionRisk, SideEffectClass, ConsentReceipt, ConfirmationReceipt, ActionIntentIRAdapter, evaluate_action
Interfaces: ipfs_datasets_py logic Intent IR, MCP++ UCAN, temporal policy, wallet grants, domain policy overlay
Submodules: ipfs_accelerate_py
Generated artifacts: none
Allow concurrent with: none
Semantic identity: objective-evidence-obligation/v1/4c5fd5000d862123f12eca1caff7e52072f8a1eb8fd22f46ff20e70be8d383f2
Acceptance subset: temporal expiry, policy-narrowing tests, emergency and code-change gates
Preconditions: objective goal VOICE-CARE-G008 is schedulable
Effects: satisfy evidence requirement: temporal expiry, satisfy evidence requirement: policy-narrowing tests, satisfy evidence requirement: emergency and code-change gates
Evidence subset: temporal expiry, policy-narrowing tests, emergency and code-change gates
Dependencies: VOICE-CARE-G006, VOICE-CARE-G007
Resource class: cpu-medium
Token class: medium
Estimated tokens: 0
Resources: cpu-medium
Merge fate: objective/VOICE-CARE-G008
Rejection reasons: none (accepted)

## Goal

Produce deterministic deny, clarify, confirm, handoff, permit-read, or permit-execute decisions from deployment policy, descriptor risk, actor capability, consent, channel, tenant, and grounded arguments.

## Missing Evidence

- temporal expiry
- policy-narrowing tests
- emergency and code-change gates

## Present Evidence

- policy engine: ipfs_accelerate_py/docs/formal_verification_tactician.md (exact), ipfs_accelerate_py/ipfs_accelerate_py/mcp_server/mcplusplus/__init__.py (ast), ipfs_accelerate_py/ipfs_accelerate_py/mcp_server/temporal_policy.py (exact)
- adapter into the existing ipfs_datasets_py Intent IR pre-dispatch envelope: docs/architecture/ABBY_VOICE_ROUTER_ARCHITECTURE.md (embedding:0.48), docs/specs/PROVEKIT_ZKP_SECURITY_NOTES.md (embedding:0.42), ipfs_accelerate_py/docs/architecture/AGENT_SUPERVISOR_PROOF_DIRECTED_RUNTIME_REVIEW.md (embedding:0.55)
- risk and side-effect taxonomy: ipfs_accelerate_py/docs/architecture/AI_SERVICE_CATALOG.md (embedding:0.35), ipfs_accelerate_py/ipfs_accelerate_py/mcp/tests/test_mcp_transport_process_level.py (embedding:0.40), ipfs_datasets_py/docs/guides/IR_FAMILY_OPERATIONS.md (embedding:0.35)
- consent/confirmation receipts: ipfs_datasets_py/ipfs_datasets_py/voice/audio_quality.py (embedding:0.31)

## Suggested Handling

Implement the single policy gate used by all transports.
