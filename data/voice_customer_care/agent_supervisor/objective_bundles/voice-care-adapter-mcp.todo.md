# Objective Bundle: voice-care/adapter-mcp

Source todo: data/voice_customer_care/agent_supervisor/VOICE_CUSTOMER_CARE_TODO.md
Purpose: bundle objective-generated tasks so parallel daemons can work one lane at a time.
Conflict policy: keep edits inside this bundle when possible; use the LLM merge resolver for semantic conflicts.

## VOICE-CARE-AUTO-010 Implement reusable voice customer-care objective: Implement the MCP and MCP++ action adapter

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: adapters
- Depends on: VOICE-CARE-G007, VOICE-CARE-AUTO-007, VOICE-CARE-AUTO-008
- Outputs: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/adapters/mcp.py, ipfs_accelerate_py/test/test_action_mcp_adapter.py
- Validation: python -m pytest -q ipfs_accelerate_py/test/test_action_mcp_adapter.py ipfs_accelerate_py/mcp/tests/test_mcp_server_mcplusplus_idl.py
- Board namespace: VOICE_CUSTOMER_CARE_TODO.md
- Evidence inputs: data/voice_customer_care/agent_supervisor/discovery
- Discovery evidence: /home/barberb/211-AI/211-AI/data/voice_customer_care/agent_supervisor/discovery/2026-08-03-voice-care-auto-010-objective-gap-36954e05f4b3.md
- Bundle: voice-care/adapter-mcp
- Bundle shard: data/voice_customer_care/agent_supervisor/objective_bundles/voice-care-adapter-mcp.todo.md
- Bundle strategy: explicit
- Graph parents: VOICE-CARE-G001
- Graph depth: 1
- Objective heap index: 10
- Parallel lane: voice-care-adapters
- Conflict policy: use canonical mcp_server surfaces; do not add a second dispatcher or bypass IDL and policy checks
- Predicted files: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/adapters/mcp.py, ipfs_accelerate_py/test/test_action_mcp_adapter.py
- Changed paths:
- Context paths: ipfs_accelerate_py/ipfs_accelerate_py/action_runtime/adapters/mcp.py, ipfs_accelerate_py/test/test_action_mcp_adapter.py
- AST symbols: MCPActionAdapter, MCPPlusPlusActionAdapter, MCPInterfaceBinding
- Interfaces: unified MCP tools_dispatch, IDL registry, UCAN delegation, temporal policy
- Submodules: ipfs_accelerate_py
- Generated artifacts:
- Allow concurrent with:
- Goal id: VOICE-CARE-G011
- Completion authority: local
- External authority blockers:
- Canonical task key: task/v1/34b8f2b2738889cd5a13d26416b9a0d3e41b29e278c925a505654228a2840674
- Canonical task CID: baguqeerags4pfmttrce42wqt2jsbnona2psbwkpcpdesljifmvbcriueaz2a
- Semantic identity: objective-evidence-obligation/v1/89466396c296eba98855f21bb5d10d1568918a07aa20431136c2e0d9afc7e276
- Acceptance subset: fake server tests
- Preconditions: objective goal VOICE-CARE-G011 is schedulable
- Effects: satisfy evidence requirement: fake server tests
- Evidence subset: fake server tests
- Resource class: cpu-medium
- Token class: medium
- Estimated tokens: 0
- Context budget tokens: 4096
- Provider role: grok, codex-review
- Resources: cpu-medium
- Merge fate: objective/VOICE-CARE-G011
- Rejection reasons: none (accepted)
- Evidence obligation key: objective-evidence-obligation/v1/89466396c296eba98855f21bb5d10d1568918a07aa20431136c2e0d9afc7e276
- Missing evidence: fake server tests
- Embedding query: MCP MCP++ action adapter dispatch IDL UCAN temporal policy CID artifact event DAG
- AST query: MCPActionAdapter, MCPPlusPlusActionAdapter, MCPInterfaceBinding
- Surplus group: objective/VOICE-CARE-G011
- Merge key: 6afc8927119c3c3a
- Merge family: objective/VOICE-CARE-G011
- Merge role: aggregate
- Work item count: 1
- Work scope: goal_subgoal_multi_evidence_batch
- Goal packet:
- Goal packet role:
- Goal packet goals:
- Goal packet task count: 0
- Goal packet work item count: 0
- Completion goal bindings: {}
- Completion task bindings:
- Candidate kind: aggregate
- Todo vector key: 38a58d3707ca4eac
- Acceptance: Objective scan filed this gap for VOICE-CARE-G011. Use evidence in /home/barberb/211-AI/211-AI/data/voice_customer_care/agent_supervisor/discovery/2026-08-03-voice-care-auto-010-objective-gap-36954e05f4b3.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (fake server tests), and keep the supervisor-fed backlog aligned with the objective heap.  Refine the objective heap if the gap needs smaller child goals.
