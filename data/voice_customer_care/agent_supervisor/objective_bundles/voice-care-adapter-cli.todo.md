# Objective Bundle: voice-care/adapter-cli

Source todo: data/voice_customer_care/agent_supervisor/VOICE_CUSTOMER_CARE_TODO.md
Purpose: bundle objective-generated tasks so parallel daemons can work one lane at a time.
Conflict policy: keep edits inside this bundle when possible; use the LLM merge resolver for semantic conflicts.

## VOICE-CARE-AUTO-011 Implement reusable voice customer-care objective: Implement the sandboxed CLI action adapter

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: adapters
- Depends on: VOICE-CARE-G007, VOICE-CARE-AUTO-007, VOICE-CARE-AUTO-008
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/adapters/cli.py, ipfs_accelerate_py/test/test_action_cli_adapter.py
- Validation: python -m pytest -q ipfs_accelerate_py/test/test_action_cli_adapter.py
- Board namespace: VOICE_CUSTOMER_CARE_TODO.md
- Evidence inputs: data/voice_customer_care/agent_supervisor/discovery
- Discovery evidence: /home/barberb/211-AI/211-AI/data/voice_customer_care/agent_supervisor/discovery/2026-08-03-voice-care-auto-011-objective-gap-537d667a967b.md
- Bundle: voice-care/adapter-cli
- Bundle shard: data/voice_customer_care/agent_supervisor/objective_bundles/voice-care-adapter-cli.todo.md
- Bundle strategy: explicit
- Graph parents: VOICE-CARE-G001
- Graph depth: 1
- Objective heap index: 11
- Parallel lane: voice-care-adapters
- Conflict policy: never use shell expansion, shell=True, caller-controlled cwd, arbitrary environment inheritance, or pack-defined executable paths
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/adapters/cli.py, ipfs_accelerate_py/test/test_action_cli_adapter.py
- Changed paths:
- Context paths: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/adapters/cli.py, ipfs_accelerate_py/test/test_action_cli_adapter.py
- AST symbols: CLIActionAdapter, CLIActionRegistration, build_argv, CLISandboxPolicy
- Interfaces: native CLI MCP tools, subprocess execution policy
- Submodules: ipfs_accelerate_py
- Generated artifacts:
- Allow concurrent with:
- Goal id: VOICE-CARE-G012
- Completion authority: local
- External authority blockers:
- Canonical task key: task/v1/34ff85b043826f62f6c98db67f78365f990bcaacd481da68b15f460b3f2cb769
- Canonical task CID: baguqeeragt7ylmcdqjxwf5wjrw3h66bwl6mqxsvm2sa5u2frl5dawpzmw5uq
- Semantic identity: objective-evidence-obligation/v1/715f652fc559f678e3288e2b5720c275b642390418da3672cbd9d659e413d837
- Acceptance subset: sandbox/resource policy, injection and environment-leak tests
- Preconditions: objective goal VOICE-CARE-G012 is schedulable
- Effects: satisfy evidence requirement: sandbox/resource policy, satisfy evidence requirement: injection and environment-leak tests
- Evidence subset: sandbox/resource policy, injection and environment-leak tests
- Resource class: cpu-medium
- Token class: medium
- Estimated tokens: 0
- Context budget tokens: 4096
- Provider role: grok, codex-review
- Resources: cpu-medium
- Merge fate: objective/VOICE-CARE-G012
- Rejection reasons: none (accepted)
- Evidence obligation key: objective-evidence-obligation/v1/715f652fc559f678e3288e2b5720c275b642390418da3672cbd9d659e413d837
- Missing evidence: sandbox/resource policy, injection and environment-leak tests
- Embedding query: sandbox CLI action adapter argv allowlist executable identity timeout resource output redaction injection
- AST query: CLIActionAdapter, CLIActionRegistration, build_argv, CLISandboxPolicy
- Surplus group: objective/VOICE-CARE-G012
- Merge key: 9a9cdfc41a740d02
- Merge family: objective/VOICE-CARE-G012
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
- Todo vector key: a0bb7f5b46d7ec43
- Acceptance: Objective scan filed this gap for VOICE-CARE-G012. Use evidence in /home/barberb/211-AI/211-AI/data/voice_customer_care/agent_supervisor/discovery/2026-08-03-voice-care-auto-011-objective-gap-537d667a967b.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (sandbox/resource policy, injection and environment-leak tests), and keep the supervisor-fed backlog aligned with the objective heap.  Refine the objective heap if the gap needs smaller child goals.
