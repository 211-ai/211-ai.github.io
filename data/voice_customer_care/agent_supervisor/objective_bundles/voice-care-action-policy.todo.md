# Objective Bundle: voice-care/action-policy

Source todo: data/voice_customer_care/agent_supervisor/VOICE_CUSTOMER_CARE_TODO.md
Purpose: bundle objective-generated tasks so parallel daemons can work one lane at a time.
Conflict policy: keep edits inside this bundle when possible; use the LLM merge resolver for semantic conflicts.

## VOICE-CARE-AUTO-007 Implement reusable voice customer-care objective: Enforce policy capability consent and confirmation before execution

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: security
- Depends on: VOICE-CARE-AUTO-005, VOICE-CARE-G007
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/policy.py, ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/intent_ir.py, ipfs_accelerate_py/test/test_action_policy.py, docs/specs/VOICE_CUSTOMER_CARE_ACTION_POLICY.md
- Validation: python -m pytest -q ipfs_accelerate_py/test/test_action_policy.py
- Board namespace: VOICE_CUSTOMER_CARE_TODO.md
- Evidence inputs: data/voice_customer_care/agent_supervisor/discovery
- Discovery evidence: /home/barberb/211-AI/211-AI/data/voice_customer_care/agent_supervisor/discovery/2026-08-03-voice-care-auto-007-objective-gap-28560c5bd129.md
- Bundle: voice-care/action-policy
- Bundle shard: data/voice_customer_care/agent_supervisor/objective_bundles/voice-care-action-policy.todo.md
- Bundle strategy: explicit
- Graph parents: VOICE-CARE-G001
- Graph depth: 1
- Objective heap index: 7
- Parallel lane: voice-care-security
- Conflict policy: reuse and preserve the existing Intent IR pre-dispatch envelope; domain and request policy can only narrow deployment authority; retrieval confidence never substitutes for consent or capability
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/policy.py, ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/intent_ir.py, ipfs_accelerate_py/test/test_action_policy.py, docs/specs/VOICE_CUSTOMER_CARE_ACTION_POLICY.md
- Changed paths:
- Context paths: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/policy.py, ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/intent_ir.py, ipfs_accelerate_py/test/test_action_policy.py, docs/specs/VOICE_CUSTOMER_CARE_ACTION_POLICY.md
- AST symbols: ActionPolicy, ActionRisk, SideEffectClass, ConsentReceipt, ConfirmationReceipt, ActionIntentIRAdapter, evaluate_action
- Interfaces: ipfs_datasets_py logic Intent IR, MCP++ UCAN, temporal policy, wallet grants, domain policy overlay
- Submodules: ipfs_accelerate_py
- Generated artifacts:
- Allow concurrent with:
- Goal id: VOICE-CARE-G008
- Completion authority: local
- External authority blockers:
- Canonical task key: task/v1/f85317f11bad3f410c4c9d6931ee80aaf0588f483c4c5862078e7c9129e751da
- Canonical task CID: baguqeera7bjrp4i3vu7ucdcmtvutd3uavlyfrd2ihrgfqyqhrz6jckphkhna
- Semantic identity: objective-evidence-obligation/v1/4c5fd5000d862123f12eca1caff7e52072f8a1eb8fd22f46ff20e70be8d383f2
- Acceptance subset: temporal expiry, policy-narrowing tests, emergency and code-change gates
- Preconditions: objective goal VOICE-CARE-G008 is schedulable
- Effects: satisfy evidence requirement: temporal expiry, satisfy evidence requirement: policy-narrowing tests, satisfy evidence requirement: emergency and code-change gates
- Evidence subset: temporal expiry, policy-narrowing tests, emergency and code-change gates
- Resource class: cpu-medium
- Token class: medium
- Estimated tokens: 0
- Context budget tokens: 4096
- Provider role: grok, codex-review
- Resources: cpu-medium
- Merge fate: objective/VOICE-CARE-G008
- Rejection reasons: none (accepted)
- Evidence obligation key: objective-evidence-obligation/v1/4c5fd5000d862123f12eca1caff7e52072f8a1eb8fd22f46ff20e70be8d383f2
- Missing evidence: temporal expiry, policy-narrowing tests, emergency and code-change gates
- Embedding query: action policy capability consent confirmation risk side effect tenant channel temporal decision
- AST query: ActionPolicy, ActionRisk, SideEffectClass, ConsentReceipt, ConfirmationReceipt, ActionIntentIRAdapter, evaluate_action
- Surplus group: objective/VOICE-CARE-G008
- Merge key: e547736c2a19157d
- Merge family: objective/VOICE-CARE-G008
- Merge role: aggregate
- Work item count: 3
- Work scope: goal_subgoal_multi_evidence_batch
- Goal packet:
- Goal packet role:
- Goal packet goals:
- Goal packet task count: 0
- Goal packet work item count: 0
- Completion goal bindings: {}
- Completion task bindings:
- Candidate kind: aggregate
- Todo vector key: 64cf896dfa94a6cf
- Acceptance: Objective scan filed this gap for VOICE-CARE-G008. Use evidence in /home/barberb/211-AI/211-AI/data/voice_customer_care/agent_supervisor/discovery/2026-08-03-voice-care-auto-007-objective-gap-28560c5bd129.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (temporal expiry, policy-narrowing tests, emergency and code-change gates), and keep the supervisor-fed backlog aligned with the objective heap.  Refine the objective heap if the gap needs smaller child goals.
