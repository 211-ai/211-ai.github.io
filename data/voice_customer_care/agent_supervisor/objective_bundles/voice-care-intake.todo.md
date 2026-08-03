# Objective Bundle: voice-care/intake

Source todo: data/voice_customer_care/agent_supervisor/VOICE_CUSTOMER_CARE_TODO.md
Purpose: bundle objective-generated tasks so parallel daemons can work one lane at a time.
Conflict policy: keep edits inside this bundle when possible; use the LLM merge resolver for semantic conflicts.

## VOICE-CARE-AUTO-015 Implement reusable voice customer-care objective: Define reusable intake forms and case lifecycle

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P1
- Track: intake
- Depends on: VOICE-CARE-AUTO-002, VOICE-CARE-AUTO-009
- Outputs: ipfs_datasets_py/ipfs_datasets_py/conversation/forms.py, ipfs_accelerate_py/ipfs_accelerate_py/conversation_runtime/intake.py, tests/customer_care/test_intake_forms.py
- Validation: python -m pytest -q tests/customer_care/test_intake_forms.py
- Board namespace: VOICE_CUSTOMER_CARE_TODO.md
- Evidence inputs: data/voice_customer_care/agent_supervisor/discovery
- Discovery evidence: /home/barberb/211-AI/211-AI/data/voice_customer_care/agent_supervisor/discovery/2026-08-03-voice-care-auto-015-objective-gap-3b160e7741c6.md
- Bundle: voice-care/intake
- Bundle shard: data/voice_customer_care/agent_supervisor/objective_bundles/voice-care-intake.todo.md
- Bundle strategy: explicit
- Graph parents: VOICE-CARE-G001
- Graph depth: 1
- Objective heap index: 15
- Parallel lane: voice-care-portal
- Conflict policy: collect the minimum required data progressively; application packs define labels but cannot weaken data classification or consent
- Predicted files: ipfs_datasets_py/ipfs_datasets_py/conversation/forms.py, ipfs_accelerate_py/ipfs_accelerate_py/conversation_runtime/intake.py, tests/customer_care/test_intake_forms.py
- Changed paths:
- Context paths: ipfs_datasets_py/ipfs_datasets_py/conversation/forms.py, ipfs_accelerate_py/ipfs_accelerate_py/conversation_runtime/intake.py, tests/customer_care/test_intake_forms.py
- AST symbols: IntakeForm, IntakeField, IntakeSession, CaseLifecycle
- Interfaces: domain pack forms, SessionState, CaseStore, wallet/HMIS consent
- Submodules: ipfs_datasets_py, ipfs_accelerate_py
- Generated artifacts:
- Allow concurrent with:
- Goal id: VOICE-CARE-G019
- Completion authority: local
- External authority blockers:
- Canonical task key: task/v1/ec9f78bc4359af06e549fd52596c9a9b1a2201da5754cf41f90731f96c0c16c5
- Canonical task CID: baguqeera5spxrpcdlgxqnzkj7vjfs3e2tmnceao2k5km6qpza4y7s3amc3cq
- Semantic identity: objective-evidence-obligation/v1/43325848d0233b17d9d0220fd413a24b357b1540042d5c86245cacf92cbdde5c
- Acceptance subset: web form projection, synthetic accessibility and privacy tests
- Preconditions: objective goal VOICE-CARE-G019 is schedulable
- Effects: satisfy evidence requirement: web form projection, satisfy evidence requirement: synthetic accessibility and privacy tests
- Evidence subset: web form projection, synthetic accessibility and privacy tests
- Resource class: cpu-medium
- Token class: medium
- Estimated tokens: 0
- Context budget tokens: 4096
- Provider role: grok, codex-review
- Resources: cpu-medium
- Merge fate: objective/VOICE-CARE-G019
- Rejection reasons: none (accepted)
- Evidence obligation key: objective-evidence-obligation/v1/43325848d0233b17d9d0220fd413a24b357b1540042d5c86245cacf92cbdde5c
- Missing evidence: web form projection, synthetic accessibility and privacy tests
- Embedding query: reusable client intake dynamic forms voice web consent disclosure case lifecycle follow up disposition
- AST query: IntakeForm, IntakeField, IntakeSession, CaseLifecycle
- Surplus group: objective/VOICE-CARE-G019
- Merge key: f18cf313ff427d01
- Merge family: objective/VOICE-CARE-G019
- Merge role: aggregate
- Work item count: 2
- Work scope: goal_subgoal_multi_evidence_batch
- Goal packet:
- Goal packet role:
- Goal packet goals:
- Goal packet task count: 0
- Goal packet work item count: 0
- Completion goal bindings: {}
- Completion task bindings:
- Candidate kind: aggregate
- Todo vector key: 4cca318af2e4f9eb
- Acceptance: Objective scan filed this gap for VOICE-CARE-G019. Use evidence in /home/barberb/211-AI/211-AI/data/voice_customer_care/agent_supervisor/discovery/2026-08-03-voice-care-auto-015-objective-gap-3b160e7741c6.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (web form projection, synthetic accessibility and privacy tests), and keep the supervisor-fed backlog aligned with the objective heap.  Refine the objective heap if the gap needs smaller child goals.
